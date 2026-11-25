import os
import re
import csv
import io
import json
import uuid
import shutil
import logging

from pathlib import Path
from datetime import datetime
from collections import Counter

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file
)

from werkzeug.utils import secure_filename


# ============================================================
# 1. OPTIONAL LIBRARIES
# ============================================================

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from openpyxl import Workbook, load_workbook
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle
    )
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    PDF_REPORT_AVAILABLE = True

except ImportError:
    PDF_REPORT_AVAILABLE = False


# ============================================================
# 2. FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_FOLDER = BASE_DIR / "uploads"
ARCHIVE_FOLDER = DATA_DIR / "archive"

CHUNKS_FILE = DATA_DIR / "chunks.json"
ANALYSIS_FILE = DATA_DIR / "analysis.json"
SESSION_FILE = DATA_DIR / "active_session.json"

MAX_CONTENT_LENGTH = 500 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

MAX_FILES_PER_UPLOAD = 10

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "txt", "md",
    "csv", "xlsx", "pptx"
}

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)


# ============================================================
# 3. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("ProjectRiskAdvisor")


# ============================================================
# 4. JSON HELPERS
# ============================================================

def save_json(path, data):

    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(".tmp")

    with open(temporary, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    temporary.replace(path)


def read_json(path, default=None):

    path = Path(path)

    if not path.exists():

        return default if default is not None else {}

    try:

        with open(path, "r", encoding="utf-8") as file:

            return json.load(file)

    except Exception as error:

        logger.error("JSON read error: %s", error)

        return default if default is not None else {}


# ============================================================
# 5. TEXT CLEANING
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")
    text = text.replace("\ufeff", "")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# 6. SESSION ARCHIVING
# ============================================================

def initialize_fresh_session():

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    archive_path = ARCHIVE_FOLDER / timestamp

    has_previous_data = (
        any(UPLOAD_FOLDER.iterdir())
        or CHUNKS_FILE.exists()
        or ANALYSIS_FILE.exists()
        or SESSION_FILE.exists()
    )

    if has_previous_data:

        archive_path.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copytree(
            UPLOAD_FOLDER,
            archive_path / "uploads",
            dirs_exist_ok=True
        )

        for source in [
            CHUNKS_FILE,
            ANALYSIS_FILE,
            SESSION_FILE
        ]:

            if source.exists():

                shutil.copy2(
                    source,
                    archive_path / source.name
                )

    for item in UPLOAD_FOLDER.iterdir():

        if item.is_file():
            item.unlink()

        elif item.is_dir():
            shutil.rmtree(item)

    save_json(CHUNKS_FILE, [])
    save_json(ANALYSIS_FILE, {})

    session = {

        "session_id": str(uuid.uuid4())[:12],

        "created_at": datetime.now().isoformat(),

        "document_count": 0,

        "documents": [],

        "analysis_status": "Not Analyzed",

        "last_updated": datetime.now().isoformat()

    }

    save_json(SESSION_FILE, session)

    logger.info(
        "Fresh session initialized: %s",
        session["session_id"]
    )


# ============================================================
# 7. FILE VALIDATION
# ============================================================

def allowed_file(filename):

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# 8. PDF EXTRACTION
# ============================================================

def extract_pdf(file_path):

    if not PDF_AVAILABLE:

        raise RuntimeError(
            "Install pypdf: pip install pypdf"
        )

    reader = PdfReader(str(file_path))

    pages = []

    for page in reader.pages:

        pages.append(
            page.extract_text() or ""
        )

    return "\n".join(pages)


# ============================================================
# 9. DOCX EXTRACTION
# ============================================================

def extract_docx(file_path):

    if not DOCX_AVAILABLE:

        raise RuntimeError(
            "Install python-docx"
        )

    document = Document(str(file_path))

    content = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():

            content.append(paragraph.text)

    for table in document.tables:

        for row in table.rows:

            content.append(
                " | ".join(
                    cell.text for cell in row.cells
                )
            )

    return "\n".join(content)


# ============================================================
# 10. TXT / MD EXTRACTION
# ============================================================

def extract_txt(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        return file.read()


# ============================================================
# 11. CSV EXTRACTION
# ============================================================

def extract_csv(file_path):

    content = []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline=""
    ) as file:

        reader = csv.reader(file)

        for row in reader:

            content.append(
                " | ".join(row)
            )

    return "\n".join(content)


# ============================================================
# 12. EXCEL EXTRACTION
# ============================================================

def extract_xlsx(file_path):

    if not EXCEL_AVAILABLE:

        raise RuntimeError(
            "Install openpyxl"
        )

    workbook = load_workbook(
        file_path,
        read_only=True,
        data_only=True
    )

    content = []

    try:

        for sheet in workbook.worksheets:

            content.append(
                "SHEET: " + sheet.title
            )

            for row in sheet.iter_rows(
                values_only=True
            ):

                values = [
                    str(value)
                    for value in row
                    if value is not None
                ]

                if values:

                    content.append(
                        " | ".join(values)
                    )

    finally:

        workbook.close()

    return "\n".join(content)


# ============================================================
# 13. POWERPOINT EXTRACTION
# ============================================================

def extract_pptx(file_path):

    if not PPTX_AVAILABLE:

        raise RuntimeError(
            "Install python-pptx"
        )

    presentation = Presentation(file_path)

    content = []

    for number, slide in enumerate(
        presentation.slides,
        start=1
    ):

        content.append(
            f"SLIDE {number}"
        )

        for shape in slide.shapes:

            if hasattr(shape, "text"):

                if shape.text.strip():

                    content.append(shape.text)

    return "\n".join(content)


# ============================================================
# 14. DOCUMENT EXTRACTION ROUTER
# ============================================================

def extract_document(file_path):

    extension = Path(file_path).suffix.lower()

    extractors = {

        ".pdf": extract_pdf,
        ".docx": extract_docx,
        ".txt": extract_txt,
        ".md": extract_txt,
        ".csv": extract_csv,
        ".xlsx": extract_xlsx,
        ".pptx": extract_pptx

    }

    extractor = extractors.get(extension)

    if not extractor:

        raise ValueError(
            "Unsupported document format."
        )

    return clean_text(
        extractor(file_path)
    )


# ============================================================
# 15. DOCUMENT CHUNKING
# ============================================================

def create_chunks(text, filename):

    text = clean_text(text)

    if not text:
        return []

    chunks = []

    start = 0

    index = 1

    while start < len(text):

        end = start + CHUNK_SIZE

        chunk_text = text[start:end].strip()

        if chunk_text:

            chunks.append({

                "chunk_id": (
                    f"{uuid.uuid4().hex[:8]}_{index}"
                ),

                "source": filename,

                "text": chunk_text,

                "created_at": datetime.now().isoformat()

            })

            index += 1

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


# ============================================================
# PART 2: DOCUMENT UPLOAD, SCOPE, RISKS, BLOCKERS,
# ACTION ITEMS AND USER STORIES
# ============================================================

import inspect


# ============================================================
# 1. GENERAL TEXT PROCESSING HELPERS
# ============================================================

def find_sentences(text):

    if not text:
        return []

    text = clean_text(text)

    sentences = re.split(
        r'(?<=[.!?])\s+|\n+',
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 10
    ]


def find_matching_sentences(text, keywords):

    sentences = find_sentences(text)

    matched = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(
            keyword.lower() in sentence_lower
            for keyword in keywords
        ):

            matched.append(sentence)

    return matched


def unique_items(items):

    result = []
    seen = set()

    for item in items:

        if isinstance(item, dict):

            key = json.dumps(
                item,
                sort_keys=True,
                default=str
            )

        else:

            key = str(item).strip().lower()

        if key and key not in seen:

            seen.add(key)
            result.append(item)

    return result


def extract_all_document_text():

    chunks = read_json(CHUNKS_FILE, [])

    if not isinstance(chunks, list):
        return ""

    text_parts = []

    for chunk in chunks:

        if isinstance(chunk, dict):

            content = (
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("chunk_text")
                or ""
            )

            if content:
                text_parts.append(str(content))

    return "\n".join(text_parts)


# ============================================================
# 2. DOCUMENT UPLOAD API
# ============================================================

@app.route("/upload", methods=["POST"])
def upload_documents():

    try:

        uploaded_files = []

        # Support multiple frontend field names
        for field_name in ["files", "documents", "file"]:

            files = request.files.getlist(field_name)

            for uploaded_file in files:

                if uploaded_file and uploaded_file.filename:

                    uploaded_files.append(uploaded_file)

        if not uploaded_files:

            return jsonify({
                "success": False,
                "message": "Please select at least one document."
            }), 400

        if len(uploaded_files) > MAX_FILES_PER_UPLOAD:

            return jsonify({
                "success": False,
                "message": (
                    f"Maximum {MAX_FILES_PER_UPLOAD} files "
                    "are allowed per upload."
                )
            }), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        existing_chunks = read_json(CHUNKS_FILE, [])

        if not isinstance(existing_chunks, list):
            existing_chunks = []

        session = read_json(SESSION_FILE, {})

        if not isinstance(session, dict):
            session = {}

        uploaded_document_details = []

        total_chunks_added = 0

        errors = []

        for uploaded_file in uploaded_files:

            original_filename = uploaded_file.filename

            if not allowed_file(original_filename):

                errors.append({
                    "filename": original_filename,
                    "error": "Unsupported file format."
                })

                continue

            safe_filename = secure_filename(original_filename)

            if not safe_filename:
                safe_filename = f"document_{uuid.uuid4().hex}.txt"

            extension = Path(safe_filename).suffix.lower()

            unique_filename = (
                f"{Path(safe_filename).stem}_"
                f"{uuid.uuid4().hex[:8]}"
                f"{extension}"
            )

            file_path = os.path.join(
                UPLOAD_FOLDER,
                unique_filename
            )

            try:

                uploaded_file.save(file_path)

                # Use the document extraction function
                # created in Part 1.
                extracted_text = extract_document(file_path)

                extracted_text = clean_text(extracted_text)

                if not extracted_text:

                    os.remove(file_path)

                    errors.append({
                        "filename": original_filename,
                        "error": "No readable text found in document."
                    })

                    continue

                # Generate chunks
                document_chunks = create_chunks(
                    extracted_text,
                    original_filename
                )

                if not isinstance(document_chunks, list):

                    document_chunks = []

                if not document_chunks:

                    os.remove(file_path)

                    errors.append({
                        "filename": original_filename,
                        "error": "Unable to generate document chunks."
                    })

                    continue

                # Add metadata to every chunk
                for index, chunk in enumerate(document_chunks):

                    if not isinstance(chunk, dict):

                        chunk = {
                            "text": str(chunk)
                        }

                        document_chunks[index] = chunk

                    chunk["document_id"] = unique_filename
                    chunk["filename"] = original_filename
                    chunk["chunk_index"] = index

                    if not chunk.get("id"):

                        chunk["id"] = str(uuid.uuid4())

                existing_chunks.extend(document_chunks)

                total_chunks_added += len(document_chunks)

                uploaded_document_details.append({

                    "id": unique_filename,

                    "filename": original_filename,

                    "stored_filename": unique_filename,

                    "file_type": extension,

                    "file_size": os.path.getsize(file_path),

                    "chunks": len(document_chunks),

                    "characters": len(extracted_text),

                    "uploaded_at": datetime.now().isoformat()

                })

            except Exception as file_error:

                if os.path.exists(file_path):

                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

                errors.append({

                    "filename": original_filename,

                    "error": str(file_error)

                })

                app.logger.exception(
                    "Document processing failed: %s",
                    original_filename
                )

        if not uploaded_document_details:

            return jsonify({

                "success": False,

                "message": "No documents could be processed.",

                "errors": errors

            }), 400

        # Save chunks
        save_json(CHUNKS_FILE, existing_chunks)

        # Update active session
        session_documents = session.get("documents", [])

        if not isinstance(session_documents, list):
            session_documents = []

        session_documents.extend(uploaded_document_details)

        session["documents"] = session_documents

        session["total_documents"] = len(session_documents)

        session["total_chunks"] = len(existing_chunks)

        session["last_upload"] = datetime.now().isoformat()

        session["updated_at"] = datetime.now().isoformat()

        save_json(SESSION_FILE, session)

        # Clear previous analysis after new upload
        save_json(ANALYSIS_FILE, {})

        return jsonify({

            "success": True,

            "message": (
                f"{len(uploaded_document_details)} document(s) "
                "uploaded and processed successfully."
            ),

            "uploaded_files": uploaded_document_details,

            "total_documents": len(session_documents),

            "total_chunks": len(existing_chunks),

            "new_chunks_added": total_chunks_added,

            "errors": errors

        }), 200

    except Exception as error:

        app.logger.exception("Upload API failed")

        return jsonify({

            "success": False,

            "message": "Document upload failed.",

            "error": str(error)

        }), 500


# ============================================================
# 3. PROJECT SCOPE EXTRACTION
# ============================================================

def extract_project_scope(text):

    sentences = find_sentences(text)

    in_scope_keywords = [

        "in scope",
        "included",
        "will include",
        "project includes",
        "shall include",
        "within scope",
        "requirement",
        "functionality",
        "feature",
        "implementation",
        "development",
        "integration",
        "deployment"

    ]

    out_scope_keywords = [

        "out of scope",
        "excluded",
        "not included",
        "will not include",
        "not part of",
        "outside scope",
        "not covered",
        "excluded from"

    ]

    deliverable_keywords = [

        "deliverable",
        "final report",
        "documentation",
        "application",
        "software",
        "system",
        "dashboard",
        "prototype",
        "deployment",
        "test report",
        "user manual",
        "training",
        "source code",
        "release"

    ]

    in_scope = []

    out_of_scope = []

    deliverables = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(
            keyword in sentence_lower
            for keyword in out_scope_keywords
        ):

            out_of_scope.append(sentence)

        elif any(
            keyword in sentence_lower
            for keyword in in_scope_keywords
        ):

            in_scope.append(sentence)

        if any(
            keyword in sentence_lower
            for keyword in deliverable_keywords
        ):

            deliverables.append(sentence)

    in_scope = unique_items(in_scope)

    out_of_scope = unique_items(out_of_scope)

    deliverables = unique_items(deliverables)

    return {

        "scope": {

            "total_scope_items": (
                len(in_scope) + len(out_of_scope)
            ),

            "summary": (
                f"Identified {len(in_scope)} in-scope "
                f"and {len(out_of_scope)} out-of-scope items."
            )

        },

        "in_scope": in_scope,

        "out_of_scope": out_of_scope,

        "deliverables": deliverables

    }


# ============================================================
# 4. RISK DETECTION
# ============================================================

def detect_risks(text):

    sentences = find_sentences(text)

    risk_patterns = {

        "High": [

            "critical risk",
            "project failure",
            "data breach",
            "security breach",
            "system failure",
            "major delay",
            "budget overrun",
            "severe impact",
            "production failure",
            "cannot deliver",
            "unavailable"

        ],

        "Medium": [

            "delay",
            "dependency",
            "resource shortage",
            "resource constraint",
            "integration issue",
            "technical issue",
            "performance issue",
            "cost increase",
            "schedule risk",
            "vendor dependency",
            "requirement change",
            "limited resources"

        ],

        "Low": [

            "minor issue",
            "documentation gap",
            "small change",
            "low priority",
            "review pending",
            "monitoring required",
            "training required"

        ]

    }

    risks = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        detected_severity = None

        detected_keywords = []

        for severity in ["High", "Medium", "Low"]:

            matches = [

                keyword
                for keyword in risk_patterns[severity]
                if keyword in sentence_lower

            ]

            if matches:

                detected_severity = severity

                detected_keywords = matches

                break

        if detected_severity:

            risks.append({

                "id": f"RISK-{uuid.uuid4().hex[:8].upper()}",

                "title": sentence[:150],

                "description": sentence,

                "severity": detected_severity,

                "category": "Project Risk",

                "keywords": detected_keywords,

                "status": "Open",

                "mitigation": (
                    "Review the risk, identify its root cause, "
                    "assign an owner and define mitigation actions."
                )

            })

    risks = unique_items(risks)

    return risks


# ============================================================
# 5. BLOCKER DETECTION
# ============================================================

def detect_blockers(text):

    blocker_keywords = [

        "blocked",
        "blocker",
        "blocking",
        "blocked by",
        "waiting for",
        "pending approval",
        "approval pending",
        "not available",
        "unable to proceed",
        "cannot proceed",
        "dependency unresolved",
        "access issue",
        "environment unavailable",
        "resource unavailable",
        "delayed due to",
        "work stopped"

    ]

    matched_sentences = find_matching_sentences(
        text,
        blocker_keywords
    )

    blockers = []

    for sentence in matched_sentences:

        blockers.append({

            "id": f"BLOCK-{uuid.uuid4().hex[:8].upper()}",

            "title": sentence[:150],

            "description": sentence,

            "severity": "High",

            "status": "Open",

            "owner": "Unassigned",

            "resolution": (
                "Investigate the blocker and coordinate "
                "with the responsible team."
            )

        })

    return unique_items(blockers)


# ============================================================
# 6. ACTION ITEM EXTRACTION
# ============================================================

def extract_action_items(text):

    sentences = find_sentences(text)

    action_keywords = [

        "action",
        "must",
        "should",
        "need to",
        "needs to",
        "required to",
        "will complete",
        "will prepare",
        "will review",
        "will implement",
        "assign",
        "resolve",
        "fix",
        "complete",
        "deliver",
        "follow up",
        "follow-up",
        "schedule",
        "verify",
        "validate",
        "test",
        "review",
        "coordinate",
        "prepare"

    ]

    actions = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(
            keyword in sentence_lower
            for keyword in action_keywords
        ):

            actions.append({

                "id": f"ACTION-{uuid.uuid4().hex[:8].upper()}",

                "title": sentence[:150],

                "description": sentence,

                "owner": "Unassigned",

                "priority": "Medium",

                "status": "Pending",

                "due_date": None

            })

    return unique_items(actions)


# ============================================================
# 7. USER STORY GENERATION
# ============================================================

def extract_user_stories(text):

    sentences = find_sentences(text)

    requirement_keywords = [

        "user",
        "customer",
        "admin",
        "administrator",
        "system",
        "application",
        "dashboard",
        "report",
        "upload",
        "download",
        "manage",
        "view",
        "generate",
        "create",
        "track",
        "monitor",
        "analyze",
        "access",
        "search",
        "notification",
        "authentication",
        "login"

    ]

    user_stories = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        matched = [

            keyword
            for keyword in requirement_keywords
            if keyword in sentence_lower

        ]

        if matched:

            user_stories.append({

                "id": (
                    f"US-{uuid.uuid4().hex[:8].upper()}"
                ),

                "title": sentence[:150],

                "user_story": (
                    f"As a user, I want {sentence.lower()} "
                    "so that the project requirement can be achieved."
                ),

                "description": sentence,

                "acceptance_criteria": [

                    "The functionality should work as described.",

                    "The output should be validated.",

                    "The feature should be tested successfully."

                ],

                "priority": "Medium",

                "status": "Draft"

            })

    return unique_items(user_stories)

# ============================================================
# PART 3: PROGRESS, HEALTH SCORE, FORECAST AND ANALYSIS
# ============================================================


# ============================================================
# 1. PROJECT PROGRESS CALCULATION
# ============================================================

def calculate_progress(text, actions=None):

    actions = actions or []

    sentences = find_sentences(text)

    completed_keywords = [
        "completed",
        "successfully completed",
        "finished",
        "implemented",
        "delivered",
        "approved",
        "closed",
        "resolved"
    ]

    pending_keywords = [
        "pending",
        "not started",
        "yet to start",
        "planned",
        "upcoming",
        "waiting",
        "in progress",
        "ongoing"
    ]

    completed_count = 0
    pending_count = 0

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(keyword in sentence_lower for keyword in completed_keywords):
            completed_count += 1

        elif any(keyword in sentence_lower for keyword in pending_keywords):
            pending_count += 1

    action_completed = sum(
        1 for action in actions
        if str(action.get("status", "")).lower()
        in ["completed", "closed", "done", "resolved"]
    )

    action_total = len(actions)

    action_pending = action_total - action_completed

    if action_total > 0:

        progress_percentage = round(
            (action_completed / action_total) * 100,
            2
        )

    elif completed_count + pending_count > 0:

        progress_percentage = round(
            completed_count /
            (completed_count + pending_count) * 100,
            2
        )

    else:

        progress_percentage = 0

    return {

        "percentage": progress_percentage,

        "completed": completed_count + action_completed,

        "pending": pending_count + action_pending,

        "total_actions": action_total,

        "status": (
            "Completed" if progress_percentage >= 100
            else "In Progress" if progress_percentage > 0
            else "Not Started"
        )

    }


# ============================================================
# 2. PROJECT HEALTH SCORE
# ============================================================

def calculate_health_score(
    risks,
    blockers,
    progress
):

    score = 100

    high_risks = sum(
        1 for risk in risks
        if risk.get("severity", "").lower() == "high"
    )

    medium_risks = sum(
        1 for risk in risks
        if risk.get("severity", "").lower() == "medium"
    )

    low_risks = sum(
        1 for risk in risks
        if risk.get("severity", "").lower() == "low"
    )

    score -= high_risks * 15

    score -= medium_risks * 8

    score -= low_risks * 3

    score -= len(blockers) * 10

    progress_percentage = progress.get("percentage", 0)

    if progress_percentage < 25:
        score -= 10

    elif progress_percentage < 50:
        score -= 5

    score = max(0, min(100, score))

    if score >= 85:

        status = "Healthy"
        condition = "Good"

    elif score >= 65:

        status = "Moderate"
        condition = "Needs Monitoring"

    elif score >= 40:

        status = "At Risk"
        condition = "Attention Required"

    else:

        status = "Critical"
        condition = "Immediate Action Required"

    return {

        "score": score,

        "status": status,

        "condition": condition,

        "high_risks": high_risks,

        "medium_risks": medium_risks,

        "low_risks": low_risks,

        "total_risks": len(risks),

        "total_blockers": len(blockers),

        "progress": progress_percentage

    }


# ============================================================
# 3. PROJECT FORECAST
# ============================================================

def generate_forecast(
    risks,
    blockers,
    actions,
    progress
):

    high_risks = sum(
        1 for risk in risks
        if risk.get("severity", "").lower() == "high"
    )

    medium_risks = sum(
        1 for risk in risks
        if risk.get("severity", "").lower() == "medium"
    )

    completed_actions = sum(
        1 for action in actions
        if str(action.get("status", "")).lower()
        in ["completed", "closed", "done", "resolved"]
    )

    pending_actions = [
        action for action in actions
        if str(action.get("status", "")).lower()
        not in ["completed", "closed", "done", "resolved"]
    ]

    total_actions = len(actions)

    pending_count = len(pending_actions)

    progress_percentage = progress.get("percentage", 0)

    if high_risks > 0 or len(blockers) > 2:

        delivery_status = "High Risk"

        prediction = (
            "Project delivery may be delayed due to "
            "high-severity risks or unresolved blockers."
        )

    elif medium_risks > 0 or len(blockers) > 0:

        delivery_status = "Moderate Risk"

        prediction = (
            "Project delivery requires monitoring. "
            "Resolve pending dependencies and medium risks."
        )

    else:

        delivery_status = "On Track"

        prediction = (
            "No major delivery threats were identified "
            "from the available project information."
        )

    if total_actions > 0:

        completion_rate = round(
            completed_actions / total_actions * 100,
            2
        )

    else:

        completion_rate = progress_percentage

    recommendations = []

    if high_risks:

        recommendations.append(
            "Prioritize mitigation of all high-severity risks."
        )

    if blockers:

        recommendations.append(
            "Assign owners and target dates to unresolved blockers."
        )

    if pending_count:

        recommendations.append(
            "Review and track all pending action items."
        )

    if progress_percentage < 50:

        recommendations.append(
            "Review project schedule and improve execution progress."
        )

    if not recommendations:

        recommendations.append(
            "Continue regular project monitoring and status reviews."
        )

    return {

        "delivery_status": delivery_status,

        "prediction": prediction,

        "completion_rate": completion_rate,

        "completed_actions": completed_actions,

        "pending_actions": pending_count,

        "total_actions": total_actions,

        "high_risks": high_risks,

        "medium_risks": medium_risks,

        "blockers": len(blockers),

        "recommendations": recommendations,

        "pending_action_details": pending_actions

    }


# ============================================================
# 4. PROJECT ANALYSIS ENGINE
# ============================================================

def perform_project_analysis():

    chunks = read_json(CHUNKS_FILE, [])

    session = read_json(SESSION_FILE, {})

    if not chunks:

        raise ValueError(
            "No document chunks found. Upload documents first."
        )

    if not isinstance(chunks, list):

        raise ValueError(
            "Invalid chunk data. Please upload documents again."
        )

    # Combine all uploaded document text
    document_text = "\n".join(

        str(chunk.get("text", ""))

        for chunk in chunks

        if isinstance(chunk, dict)

    )

    document_text = clean_text(document_text)

    if not document_text:

        raise ValueError(
            "No readable document content available for analysis."
        )

    # ----------------------------------------
    # SCOPE ANALYSIS
    # ----------------------------------------

    scope_result = extract_project_scope(document_text)

    # ----------------------------------------
    # RISK ANALYSIS
    # ----------------------------------------

    risks = detect_risks(document_text)

    # ----------------------------------------
    # BLOCKER ANALYSIS
    # ----------------------------------------

    blockers = detect_blockers(document_text)

    # ----------------------------------------
    # ACTION ITEM ANALYSIS
    # ----------------------------------------

    actions = extract_action_items(document_text)

    # ----------------------------------------
    # USER STORY GENERATION
    # ----------------------------------------

    user_stories = extract_user_stories(document_text)

    # ----------------------------------------
    # PROJECT PROGRESS
    # ----------------------------------------

    progress = calculate_progress(
        document_text,
        actions
    )

    # ----------------------------------------
    # HEALTH SCORE
    # ----------------------------------------

    health = calculate_health_score(
        risks,
        blockers,
        progress
    )

    # ----------------------------------------
    # PROJECT FORECAST
    # ----------------------------------------

    forecast = generate_forecast(
        risks,
        blockers,
        actions,
        progress
    )

    # ----------------------------------------
    # DOCUMENT SUMMARY
    # ----------------------------------------

    documents = session.get("documents", [])

    if not isinstance(documents, list):
        documents = []

    total_characters = len(document_text)

    total_words = len(document_text.split())

    # ----------------------------------------
    # ANALYSIS RESULT
    # ----------------------------------------

    result = {

        "success": True,

        "project_name": "Project Risk Advisor",

        "analysis_status": "Completed",

        "analyzed_at": datetime.now().isoformat(),

        "session_id": session.get("session_id"),

        "documents": documents,

        "document_summary": {

            "total_documents": len(documents),

            "total_chunks": len(chunks),

            "total_characters": total_characters,

            "total_words": total_words

        },

        "scope": scope_result.get("scope", {}),

        "in_scope": scope_result.get("in_scope", []),

        "out_of_scope": scope_result.get("out_of_scope", []),

        "deliverables": scope_result.get("deliverables", []),

        "risks": risks,

        "risk_summary": {

            "total": len(risks),

            "high": sum(
                1 for risk in risks
                if risk.get("severity") == "High"
            ),

            "medium": sum(
                1 for risk in risks
                if risk.get("severity") == "Medium"
            ),

            "low": sum(
                1 for risk in risks
                if risk.get("severity") == "Low"
            )

        },

        "blockers": blockers,

        "actions": actions,

        "user_stories": user_stories,

        "progress": progress,

        "health": health,

        "forecast": forecast,

        "statistics": {

            "total_scope_items": (
                len(scope_result.get("in_scope", []))
                + len(scope_result.get("out_of_scope", []))
            ),

            "total_deliverables": len(
                scope_result.get("deliverables", [])
            ),

            "total_risks": len(risks),

            "total_blockers": len(blockers),

            "total_actions": len(actions),

            "total_user_stories": len(user_stories)

        }

    }

    # Save analysis result
    save_json(ANALYSIS_FILE, result)

    # Update session metadata
    session["analysis_status"] = "Completed"

    session["last_analysis"] = datetime.now().isoformat()

    session["total_chunks"] = len(chunks)

    save_json(SESSION_FILE, session)

    return result


# ============================================================
# 5. ANALYZE PROJECT API
# ============================================================

@app.route("/api/analyze", methods=["POST"])
def analyze_project_api():

    try:

        chunks = read_json(CHUNKS_FILE, [])

        if not chunks:

            return jsonify({

                "success": False,

                "message": (
                    "No uploaded documents found. "
                    "Please upload documents before analysis."
                )

            }), 400

        result = perform_project_analysis()

        return jsonify({

            "success": True,

            "message": "Project analysis completed successfully.",

            "data": result

        }), 200

    except Exception as error:

        app.logger.exception(
            "Project analysis failed"
        )

        return jsonify({

            "success": False,

            "message": "Project analysis failed.",

            "error": str(error)

        }), 500


# ============================================================
# 6. DASHBOARD API
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard_api():

    try:

        analysis = read_json(ANALYSIS_FILE, {})

        session = read_json(SESSION_FILE, {})

        if not isinstance(analysis, dict):
            analysis = {}

        if not isinstance(session, dict):
            session = {}

        if not analysis:

            return jsonify({

                "success": True,

                "message": "Analysis is not available yet.",

                "data": {

                    "analysis_status": "Waiting for analysis",

                    "documents": session.get("documents", []),

                    "total_documents": len(
                        session.get("documents", [])
                    ),

                    "total_chunks": session.get(
                        "total_chunks", 0
                    ),

                    "risks": [],

                    "blockers": [],

                    "actions": [],

                    "user_stories": [],

                    "in_scope": [],

                    "out_of_scope": [],

                    "deliverables": [],

                    "health": {

                        "score": 0,

                        "status": "Not Analyzed",

                        "condition": "Upload documents and analyze."

                    },

                    "progress": {

                        "percentage": 0,

                        "completed": 0,

                        "pending": 0,

                        "status": "Not Started"

                    },

                    "forecast": {}

                }

            }), 200

        # Keep current session metadata
        analysis["documents"] = session.get(
            "documents",
            analysis.get("documents", [])
        )

        analysis["total_documents"] = len(
            analysis.get("documents", [])
        )

        analysis["total_chunks"] = session.get(
            "total_chunks",
            analysis.get("document_summary", {}).get(
                "total_chunks", 0
            )
        )

        return jsonify({

            "success": True,

            "data": analysis

        }), 200

    except Exception as error:

        app.logger.exception(
            "Dashboard API failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to load dashboard.",

            "error": str(error)

        }), 500


# ============================================================
# 7. INDIVIDUAL ANALYSIS APIs
# ============================================================

@app.route("/api/risks", methods=["GET"])
def get_risks_api():

    analysis = read_json(ANALYSIS_FILE, {})

    return jsonify({

        "success": True,

        "risks": analysis.get("risks", [])

    })


@app.route("/api/blockers", methods=["GET"])
def get_blockers_api():

    analysis = read_json(ANALYSIS_FILE, {})

    return jsonify({

        "success": True,

        "blockers": analysis.get("blockers", [])

    })


@app.route("/api/actions", methods=["GET"])
def get_actions_api():

    analysis = read_json(ANALYSIS_FILE, {})

    return jsonify({

        "success": True,

        "actions": analysis.get("actions", [])

    })


@app.route("/api/user-stories", methods=["GET"])
def get_user_stories_api():

    analysis = read_json(ANALYSIS_FILE, {})

    return jsonify({

        "success": True,

        "user_stories": analysis.get("user_stories", [])

    })

# ============================================================
# PART 4: RAG ASSISTANT, REPORTS, EXPORTS AND APP START
# ============================================================


# ============================================================
# 1. DOCUMENT RETRIEVAL ENGINE
# ============================================================

def retrieve_documents(query, top_k=None):

    chunks = read_json(CHUNKS_FILE, [])

    if not chunks:
        return []

    query_words = set(
        re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
    )

    if not query_words:
        return []

    scored_chunks = []

    for chunk in chunks:

        if not isinstance(chunk, dict):
            continue

        chunk_text = str(
            chunk.get("text", "")
        )

        if not chunk_text:
            continue

        chunk_words = set(
            re.findall(
                r'\b[a-zA-Z0-9]+\b',
                chunk_text.lower()
            )
        )

        matched_words = query_words.intersection(chunk_words)

        if not matched_words:
            continue

        score = len(matched_words) / max(
            len(query_words), 1
        )

        scored_chunks.append({

            "score": round(score, 4),

            "text": chunk_text,

            "filename": chunk.get(
                "filename", "Unknown Document"
            ),

            "chunk_id": chunk.get("id", "")

        })

    scored_chunks.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # Return all matching chunks if top_k is not specified.
    if top_k is not None:
        scored_chunks = scored_chunks[:max(1, int(top_k))]

    return scored_chunks


# ============================================================
# 2. RAG RESPONSE GENERATOR
# ============================================================

def generate_rag_response(query):

    retrieved_chunks = retrieve_documents(query)

    if not retrieved_chunks:

        return {

            "answer": (
                "I could not find relevant information "
                "in the uploaded project documents. "
                "Please try another question."
            ),

            "sources": [],

            "retrieved_chunks": 0

        }

    answer_parts = []

    sources = []

    for item in retrieved_chunks:

        answer_parts.append(item["text"])

        if item["filename"] not in sources:
            sources.append(item["filename"])

    answer = "\n\n".join(answer_parts)

    return {

        "answer": answer,

        "sources": sources,

        "retrieved_chunks": len(retrieved_chunks)

    }


# ============================================================
# 3. RAG CHAT API
# ============================================================

@app.route("/api/rag-chat", methods=["POST"])
def rag_chat_api():

    try:

        data = request.get_json(silent=True) or {}

        query = str(
            data.get("message")
            or data.get("query")
            or data.get("question")
            or ""
        ).strip()

        if not query:

            return jsonify({

                "success": False,

                "message": "Please enter your question."

            }), 400

        if not os.path.exists(CHUNKS_FILE):

            return jsonify({

                "success": False,

                "message": "Please upload project documents first."

            }), 400

        response = generate_rag_response(query)

        return jsonify({

            "success": True,

            "question": query,

            "answer": response["answer"],

            "sources": response["sources"],

            "retrieved_chunks": response["retrieved_chunks"]

        }), 200

    except Exception as error:

        app.logger.exception("RAG chat failed")

        return jsonify({

            "success": False,

            "message": "Unable to process your question.",

            "error": str(error)

        }), 500


# ============================================================
# 4. USER STORY CREATION API
# ============================================================

@app.route("/api/user-story", methods=["POST"])
def create_user_story_api():

    try:

        data = request.get_json(silent=True) or {}

        title = str(
            data.get("title", "")
        ).strip()

        description = str(
            data.get("description", "")
        ).strip()

        if not title and not description:

            return jsonify({

                "success": False,

                "message": "Enter a user story title or description."

            }), 400

        story = {

            "id": f"US-{uuid.uuid4().hex[:8].upper()}",

            "title": title or description[:150],

            "user_story": description or title,

            "description": description or title,

            "acceptance_criteria": data.get(
                "acceptance_criteria",
                []
            ),

            "priority": data.get(
                "priority",
                "Medium"
            ),

            "status": data.get(
                "status",
                "Draft"
            ),

            "created_at": datetime.now().isoformat()

        }

        analysis = read_json(ANALYSIS_FILE, {})

        if not isinstance(analysis, dict):
            analysis = {}

        stories = analysis.get("user_stories", [])

        if not isinstance(stories, list):
            stories = []

        stories.append(story)

        analysis["user_stories"] = stories

        analysis.setdefault("statistics", {})

        analysis["statistics"]["total_user_stories"] = len(stories)

        save_json(ANALYSIS_FILE, analysis)

        return jsonify({

            "success": True,

            "message": "User story created successfully.",

            "data": story

        }), 200

    except Exception as error:

        app.logger.exception("User story creation failed")

        return jsonify({

            "success": False,

            "message": "Unable to create user story.",

            "error": str(error)

        }), 500


# ============================================================
# 5. REPORT DATA HELPER
# ============================================================

def get_report_data():

    analysis = read_json(ANALYSIS_FILE, {})

    if not isinstance(analysis, dict) or not analysis:

        raise ValueError(
            "Please analyze the project before generating a report."
        )

    return analysis


# ============================================================
# 6. PDF REPORT GENERATION
# ============================================================

@app.route("/api/generate-report", methods=["GET", "POST"])
def generate_pdf_report():

    try:

        analysis = get_report_data()

        if not REPORTLAB_AVAILABLE:

            return jsonify({

                "success": False,

                "message": (
                    "PDF generation library is unavailable. "
                    "Install reportlab."
                )

            }), 500

        from reportlab.lib import colors

        from reportlab.lib.pagesizes import A4

        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle
        )

        from reportlab.lib.units import inch

        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak
        )

        buffer = io.BytesIO()

        document = SimpleDocTemplate(

            buffer,

            pagesize=A4,

            rightMargin=35,

            leftMargin=35,

            topMargin=40,

            bottomMargin=40

        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(

            "CustomTitle",

            parent=styles["Title"],

            fontSize=20,

            leading=25,

            textColor=colors.HexColor("#123B65"),

            spaceAfter=15

        )

        heading_style = ParagraphStyle(

            "CustomHeading",

            parent=styles["Heading2"],

            fontSize=13,

            leading=17,

            textColor=colors.HexColor("#1769AA"),

            spaceBefore=12,

            spaceAfter=8

        )

        normal_style = styles["BodyText"]

        story = []

        story.append(
            Paragraph(
                "PROJECT RISK ADVISOR",
                title_style
            )
        )

        story.append(
            Paragraph(
                "Enterprise Project Intelligence & Risk Management Report",
                normal_style
            )
        )

        story.append(Spacer(1, 15))

        story.append(
            Paragraph(
                "Generated: " + datetime.now().strftime(
                    "%d-%m-%Y %H:%M"
                ),
                normal_style
            )
        )

        story.append(Spacer(1, 15))

        # ----------------------------------------
        # PROJECT OVERVIEW
        # ----------------------------------------

        story.append(
            Paragraph("1. Project Overview", heading_style)
        )

        summary = analysis.get("document_summary", {})

        overview_data = [

            ["Metric", "Value"],

            [
                "Documents",
                str(summary.get("total_documents", 0))
            ],

            [
                "Chunks",
                str(summary.get("total_chunks", 0))
            ],

            [
                "Words",
                str(summary.get("total_words", 0))
            ],

            [
                "Characters",
                str(summary.get("total_characters", 0))
            ]

        ]

        overview_table = Table(
            overview_data,
            colWidths=[220, 250]
        )

        overview_table.setStyle(TableStyle([

            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#1769AA")),

            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

            ("PADDING", (0, 0), (-1, -1), 7),

            ("VALIGN", (0, 0), (-1, -1), "TOP")

        ]))

        story.append(overview_table)

        # ----------------------------------------
        # HEALTH SCORE
        # ----------------------------------------

        health = analysis.get("health", {})

        story.append(
            Paragraph("2. Project Health", heading_style)
        )

        story.append(
            Paragraph(
                "Health Score: "
                + str(health.get("score", 0))
                + "/100",
                normal_style
            )
        )

        story.append(
            Paragraph(
                "Status: "
                + str(health.get("status", "Unknown")),
                normal_style
            )
        )

        # ----------------------------------------
        # PROGRESS
        # ----------------------------------------

        progress = analysis.get("progress", {})

        story.append(
            Paragraph("3. Project Progress", heading_style)
        )

        story.append(
            Paragraph(
                "Progress: "
                + str(progress.get("percentage", 0))
                + "%",
                normal_style
            )
        )

        # ----------------------------------------
        # SCOPE
        # ----------------------------------------

        story.append(
            Paragraph("4. Project Scope", heading_style)
        )

        for label, key in [

            ("In Scope", "in_scope"),

            ("Out of Scope", "out_of_scope"),

            ("Deliverables", "deliverables")

        ]:

            story.append(
                Paragraph(label, styles["Heading3"])
            )

            items = analysis.get(key, [])

            if not items:

                story.append(
                    Paragraph("No information identified.", normal_style)
                )

            for item in items:

                story.append(
                    Paragraph(
                        "• " + str(item),
                        normal_style
                    )
                )

        # ----------------------------------------
        # RISKS
        # ----------------------------------------

        story.append(
            Paragraph("5. Risk Register", heading_style)
        )

        risks = analysis.get("risks", [])

        if risks:

            risk_data = [[
                "Risk ID",
                "Description",
                "Severity",
                "Status"
            ]]

            for risk in risks:

                risk_data.append([

                    str(risk.get("id", "")),

                    Paragraph(
                        str(risk.get("description", "")),
                        normal_style
                    ),

                    str(risk.get("severity", "")),

                    str(risk.get("status", ""))

                ])

            risk_table = Table(

                risk_data,

                repeatRows=1,

                colWidths=[65, 240, 70, 70]

            )

            risk_table.setStyle(TableStyle([

                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#1769AA")),

                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),

                ("VALIGN", (0, 0), (-1, -1), "TOP"),

                ("PADDING", (0, 0), (-1, -1), 5)

            ]))

            story.append(risk_table)

        else:

            story.append(
                Paragraph("No risks identified.", normal_style)
            )

        # ----------------------------------------
        # BLOCKERS
        # ----------------------------------------

        story.append(
            Paragraph("6. Blockers", heading_style)
        )

        blockers = analysis.get("blockers", [])

        for blocker in blockers:

            story.append(
                Paragraph(
                    "• " + str(blocker.get("description", "")),
                    normal_style
                )
            )

        if not blockers:

            story.append(
                Paragraph("No blockers identified.", normal_style)
            )

        # ----------------------------------------
        # ACTION ITEMS
        # ----------------------------------------

        story.append(
            Paragraph("7. Action Items", heading_style)
        )

        actions = analysis.get("actions", [])

        for action in actions:

            story.append(
                Paragraph(
                    "• "
                    + str(action.get("title", ""))
                    + " | Owner: "
                    + str(action.get("owner", "Unassigned"))
                    + " | Status: "
                    + str(action.get("status", "Pending")),
                    normal_style
                )
            )

        if not actions:

            story.append(
                Paragraph("No action items identified.", normal_style)
            )

        # ----------------------------------------
        # USER STORIES
        # ----------------------------------------

        story.append(
            Paragraph("8. User Stories", heading_style)
        )

        for user_story in analysis.get("user_stories", []):

            story.append(
                Paragraph(
                    "• " + str(
                        user_story.get("user_story", "")
                    ),
                    normal_style
                )
            )

        # ----------------------------------------
        # FORECAST
        # ----------------------------------------

        forecast = analysis.get("forecast", {})

        story.append(
            Paragraph("9. Project Forecast", heading_style)
        )

        story.append(
            Paragraph(
                "Delivery Status: "
                + str(
                    forecast.get("delivery_status", "Unknown")
                ),
                normal_style
            )
        )

        story.append(
            Paragraph(
                str(forecast.get("prediction", "")),
                normal_style
            )
        )

        story.append(
            Paragraph("Recommendations", styles["Heading3"])
        )

        for recommendation in forecast.get(
            "recommendations", []
        ):

            story.append(
                Paragraph(
                    "• " + str(recommendation),
                    normal_style
                )
            )

        document.build(story)

        buffer.seek(0)

        return send_file(

            buffer,

            as_attachment=True,

            download_name="Project_Risk_Advisor_Report.pdf",

            mimetype="application/pdf"

        )

    except Exception as error:

        app.logger.exception("PDF report generation failed")

        return jsonify({

            "success": False,

            "message": "Unable to generate PDF report.",

            "error": str(error)

        }), 500


# ============================================================
# 7. EXCEL REPORT GENERATION
# ============================================================

@app.route("/api/export-excel", methods=["GET", "POST"])
def export_excel_report():

    try:

        analysis = get_report_data()

        if not OPENPYXL_AVAILABLE:

            return jsonify({

                "success": False,

                "message": (
                    "Excel library is unavailable. "
                    "Install openpyxl."
                )

            }), 500

        from openpyxl import Workbook

        from openpyxl.styles import (
            Font,
            PatternFill,
            Alignment,
            Border,
            Side
        )

        from openpyxl.utils import get_column_letter

        workbook = Workbook()

        # ----------------------------------------
        # Dashboard Sheet
        # ----------------------------------------

        dashboard = workbook.active

        dashboard.title = "Dashboard"

        dashboard.append([
            "PROJECT RISK ADVISOR"
        ])

        dashboard.append([
            "Metric",
            "Value"
        ])

        summary = analysis.get("document_summary", {})

        health = analysis.get("health", {})

        progress = analysis.get("progress", {})

        forecast = analysis.get("forecast", {})

        dashboard_rows = [

            [
                "Total Documents",
                summary.get("total_documents", 0)
            ],

            [
                "Total Chunks",
                summary.get("total_chunks", 0)
            ],

            [
                "Health Score",
                health.get("score", 0)
            ],

            [
                "Health Status",
                health.get("status", "")
            ],

            [
                "Progress",
                progress.get("percentage", 0)
            ],

            [
                "Total Risks",
                len(analysis.get("risks", []))
            ],

            [
                "Total Blockers",
                len(analysis.get("blockers", []))
            ],

            [
                "Total Actions",
                len(analysis.get("actions", []))
            ],

            [
                "Total User Stories",
                len(analysis.get("user_stories", []))
            ],

            [
                "Delivery Forecast",
                forecast.get("delivery_status", "")
            ]

        ]

        for row in dashboard_rows:
            dashboard.append(row)

        # ----------------------------------------
        # Scope Sheet
        # ----------------------------------------

        scope_sheet = workbook.create_sheet("Project Scope")

        scope_sheet.append([
            "Category",
            "Description"
        ])

        for item in analysis.get("in_scope", []):

            scope_sheet.append([
                "In Scope",
                item
            ])

        for item in analysis.get("out_of_scope", []):

            scope_sheet.append([
                "Out of Scope",
                item
            ])

        for item in analysis.get("deliverables", []):

            scope_sheet.append([
                "Deliverable",
                item
            ])

        # ----------------------------------------
        # Risks Sheet
        # ----------------------------------------

        risk_sheet = workbook.create_sheet("Risk Register")

        risk_sheet.append([

            "Risk ID",

            "Title",

            "Description",

            "Severity",

            "Category",

            "Status",

            "Mitigation"

        ])

        for risk in analysis.get("risks", []):

            risk_sheet.append([

                risk.get("id", ""),

                risk.get("title", ""),

                risk.get("description", ""),

                risk.get("severity", ""),

                risk.get("category", ""),

                risk.get("status", ""),

                risk.get("mitigation", "")

            ])

        # ----------------------------------------
        # Blockers Sheet
        # ----------------------------------------

        blocker_sheet = workbook.create_sheet("Blockers")

        blocker_sheet.append([

            "Blocker ID",

            "Title",

            "Description",

            "Severity",

            "Owner",

            "Status",

            "Resolution"

        ])

        for blocker in analysis.get("blockers", []):

            blocker_sheet.append([

                blocker.get("id", ""),

                blocker.get("title", ""),

                blocker.get("description", ""),

                blocker.get("severity", ""),

                blocker.get("owner", ""),

                blocker.get("status", ""),

                blocker.get("resolution", "")

            ])

        # ----------------------------------------
        # Action Items Sheet
        # ----------------------------------------

        action_sheet = workbook.create_sheet("Action Items")

        action_sheet.append([

            "Action ID",

            "Title",

            "Description",

            "Owner",

            "Priority",

            "Status",

            "Due Date"

        ])

        for action in analysis.get("actions", []):

            action_sheet.append([

                action.get("id", ""),

                action.get("title", ""),

                action.get("description", ""),

                action.get("owner", ""),

                action.get("priority", ""),

                action.get("status", ""),

                action.get("due_date", "")

            ])

        # ----------------------------------------
        # User Stories Sheet
        # ----------------------------------------

        story_sheet = workbook.create_sheet("User Stories")

        story_sheet.append([

            "Story ID",

            "Title",

            "User Story",

            "Description",

            "Acceptance Criteria",

            "Priority",

            "Status"

        ])

        for user_story in analysis.get("user_stories", []):

            criteria = user_story.get(
                "acceptance_criteria", []
            )

            story_sheet.append([

                user_story.get("id", ""),

                user_story.get("title", ""),

                user_story.get("user_story", ""),

                user_story.get("description", ""),

                "\n".join(map(str, criteria)),

                user_story.get("priority", ""),

                user_story.get("status", "")

            ])

        # ----------------------------------------
        # Forecast Sheet
        # ----------------------------------------

        forecast_sheet = workbook.create_sheet("Forecast")

        forecast_sheet.append([
            "Metric",
            "Value"
        ])

        forecast_sheet.append([
            "Delivery Status",
            forecast.get("delivery_status", "")
        ])

        forecast_sheet.append([
            "Prediction",
            forecast.get("prediction", "")
        ])

        forecast_sheet.append([
            "Completion Rate",
            forecast.get("completion_rate", 0)
        ])

        for recommendation in forecast.get(
            "recommendations", []
        ):

            forecast_sheet.append([
                "Recommendation",
                recommendation
            ])

        # ----------------------------------------
        # Apply Formatting
        # ----------------------------------------

        header_fill = PatternFill(

            fill_type="solid",

            fgColor="1769AA"

        )

        header_font = Font(

            bold=True,

            color="FFFFFF"

        )

        thin_border = Border(

            bottom=Side(
                style="thin",
                color="D9E2F3"
            )

        )

        for worksheet in workbook.worksheets:

            worksheet.freeze_panes = "A2"

            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

            for cell in worksheet[1]:

                cell.fill = header_fill

                cell.font = header_font

                cell.alignment = Alignment(
                    vertical="center",
                    wrap_text=True
                )

            for row in worksheet.iter_rows():

                for cell in row:

                    cell.alignment = Alignment(
                        vertical="top",
                        wrap_text=True
                    )

                    cell.border = thin_border

            for column_cells in worksheet.columns:

                column_letter = get_column_letter(
                    column_cells[0].column
                )

                max_length = 0

                for cell in column_cells:

                    if cell.value is not None:

                        max_length = max(
                            max_length,
                            len(str(cell.value))
                        )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max(max_length + 3, 15),
                    60
                )

        buffer = io.BytesIO()

        workbook.save(buffer)

        buffer.seek(0)

        return send_file(

            buffer,

            as_attachment=True,

            download_name="Project_Risk_Advisor_Report.xlsx",

            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )

        )

    except Exception as error:

        app.logger.exception("Excel export failed")

        return jsonify({

            "success": False,

            "message": "Unable to export Excel report.",

            "error": str(error)

        }), 500


# ============================================================
# 8. HEALTH CHECK API
# ============================================================

@app.route("/health", methods=["GET"])
def health_check():

    return jsonify({

        "success": True,

        "application": "Project Risk Advisor",

        "status": "Running",

        "timestamp": datetime.now().isoformat(),

        "chunks_available": len(
            read_json(CHUNKS_FILE, [])
        ),

        "analysis_available": bool(
            read_json(ANALYSIS_FILE, {})
        )

    }), 200


# ============================================================
# 9. HOME PAGE
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return render_template("index.html")


# ============================================================
# 10. ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({

        "success": False,

        "message": (
            "Uploaded file is too large. "
            "Maximum request size is 500 MB."
        )

    }), 413


@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({

            "success": False,

            "message": "API endpoint not found."

        }), 404

    return "Page not found", 404


@app.errorhandler(500)
def internal_server_error(error):

    app.logger.exception("Internal server error")

    if request.path.startswith("/api/"):

        return jsonify({

            "success": False,

            "message": "Internal server error."

        }), 500

    return "Internal server error", 500


# ============================================================
# 11. APPLICATION INITIALIZATION
# ============================================================

if __name__ == "__main__":

    # Archive previous session and start a fresh session.
    initialize_fresh_session()

    print("\n" + "=" * 60)

    print(" PROJECT RISK ADVISOR")

    print(" Enterprise Project Intelligence Platform")

    print("=" * 60)

    print("Application: Running")

    print("URL: http://127.0.0.1:5000")

    print("Fresh session: Initialized")

    print("=" * 60 + "\n")

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True,

        use_reloader=False

    )


