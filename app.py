import json
import uuid
import hashlib
import time

from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from ingestion import (
    extract_text,
    chunk_text,
    SUPPORTED_EXTENSIONS
)

from scope_agent import extract_scope
from risk_agent import detect_risks
from forecasting_agent import forecast_delivery
from blocker_agent import identify_blockers
from action_item_agent import identify_action_items
from health_score import calculate_health_score


# ==================================================
# FLASK CONFIGURATION
# ==================================================

app = Flask(__name__)

app.secret_key = "milestone2-project-secret-key"

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = DATA_DIR / "archive"

CHUNKS_FILE = DATA_DIR / "chunks.json"
ACTIVE_SESSION_FILE = DATA_DIR / "active_session.json"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

MAX_FILES_PER_UPLOAD = 10


# ==================================================
# LOCKS
# ==================================================

analysis_lock = Lock()
session_lock = Lock()

analysis_cache = None
analysis_cache_key = None


# ==================================================
# ANALYSIS CACHE
# ==================================================

def clear_analysis_cache():

    global analysis_cache
    global analysis_cache_key

    with analysis_lock:

        analysis_cache = None
        analysis_cache_key = None


# ==================================================
# CHUNK STORAGE
# ==================================================

def load_chunks():

    if not CHUNKS_FILE.exists():
        return []

    try:

        with open(
            CHUNKS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):

        app.logger.exception("Unable to load chunks")

        return []


def save_chunks(chunks):

    temp_file = DATA_DIR / "chunks_temp.json"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )

    temp_file.replace(CHUNKS_FILE)


# ==================================================
# SESSION INFORMATION
# ==================================================

def load_active_session():

    if not ACTIVE_SESSION_FILE.exists():
        return {}

    try:

        with open(
            ACTIVE_SESSION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return {}


def save_active_session(session_info):

    temp_file = DATA_DIR / "active_session_temp.json"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            session_info,
            file,
            indent=2,
            ensure_ascii=False
        )

    temp_file.replace(ACTIVE_SESSION_FILE)


# ==================================================
# ARCHIVE PREVIOUS SESSION
# ==================================================

def archive_previous_session():

    old_chunks = load_chunks()

    if not old_chunks:
        return

    old_session = load_active_session()

    session_id = old_session.get(
        "session_id",
        uuid.uuid4().hex
    )

    archive_name = (
        "session_"
        + session_id
        + "_"
        + time.strftime("%Y%m%d_%H%M%S")
        + ".json"
    )

    archive_path = ARCHIVE_DIR / archive_name

    with open(
        archive_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "session": old_session,
                "chunks": old_chunks
            },
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nPrevious session archived:", archive_name)


# ==================================================
# CREATE NEW SESSION
# ==================================================

def create_new_session(new_chunks):

    with session_lock:

        session_id = uuid.uuid4().hex

        # Archive previous session first
        archive_previous_session()

        # Assign new session ID
        for chunk in new_chunks:

            chunk["session_id"] = session_id

        # Replace old active chunks
        save_chunks(new_chunks)

        session_info = {

            "session_id": session_id,

            "created_at": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "files": sorted({
                item.get("filename", "Unknown")
                for item in new_chunks
            }),

            "total_chunks": len(new_chunks)

        }

        save_active_session(session_info)

        clear_analysis_cache()

        print("\n========== NEW SESSION CREATED ==========")

        print("Session ID:", session_id)

        print("Files:", session_info["files"])

        print("Total Chunks:", len(new_chunks))

        print("=========================================\n")

        return session_info


# ==================================================
# COMBINE DOCUMENT TEXT
# ==================================================

def combine_uploaded_text(chunks):

    documents = {}

    for item in chunks:

        filename = item.get(
            "filename",
            "Unknown"
        )

        content = item.get(
            "text",
            ""
        ).strip()

        if not content:
            continue

        documents.setdefault(
            filename,
            []
        ).append(content)

    combined = []

    for filename, contents in documents.items():

        combined.append(
            f"Document: {filename}\n"
            + "\n".join(contents)
        )

    return "\n\n".join(combined)


# ==================================================
# MILESTONE 2 ANALYSIS
# ==================================================

def analyze_project(document_text):

    total_start = time.perf_counter()

    print("\n========== MILESTONE 2 ANALYSIS ==========")

    with ThreadPoolExecutor(max_workers=5) as executor:

        futures = {

            "scope": executor.submit(
                extract_scope,
                document_text
            ),

            "risk": executor.submit(
                detect_risks,
                document_text
            ),

            "forecast": executor.submit(
                forecast_delivery,
                document_text
            ),

            "blocker": executor.submit(
                identify_blockers,
                document_text
            ),

            "action": executor.submit(
                identify_action_items,
                document_text
            )

        }

        scope = futures["scope"].result()

        risk_result = futures["risk"].result()

        forecast = futures["forecast"].result()

        blocker_result = futures["blocker"].result()

        action_result = futures["action"].result()


    # ------------------------------------------
    # NORMALIZE AGENT OUTPUTS
    # ------------------------------------------

    risks = (
        risk_result.get("risks", [])
        if isinstance(risk_result, dict)
        else risk_result
    )

    blockers = (
        blocker_result.get("blockers", [])
        if isinstance(blocker_result, dict)
        else blocker_result
    )

    action_items = (
        action_result.get("action_items", [])
        if isinstance(action_result, dict)
        else action_result
    )

    if not isinstance(risks, list):
        risks = []

    if not isinstance(blockers, list):
        blockers = []

    if not isinstance(action_items, list):
        action_items = []

    if not isinstance(forecast, dict):
        forecast = {}


    # ------------------------------------------
    # HEALTH SCORE
    # ------------------------------------------

    health = calculate_health_score(
        risks,
        blockers,
        forecast
    )

    total_time = time.perf_counter() - total_start

    print("------------------------------------------")

    print("Scope Analysis Completed")

    print("Risks Detected:", len(risks))

    print("Blockers Detected:", len(blockers))

    print("Action Items:", len(action_items))

    print(
        "Health Score:",
        health.get("health_score")
    )

    print(
        "Analysis Time:",
        round(total_time, 2),
        "seconds"
    )

    print("==========================================\n")

    return {

        "scope": scope,

        "health": health,

        "risks": risks,

        "risk_summary": (
            risk_result
            if isinstance(risk_result, dict)
            else {}
        ),

        "forecast": forecast,

        "blockers": blockers,

        "action_items": action_items

    }


# ==================================================
# CACHED ANALYSIS
# ==================================================

def get_cached_analysis(document_text):

    global analysis_cache
    global analysis_cache_key

    current_key = hashlib.md5(
        document_text.encode("utf-8")
    ).hexdigest()

    with analysis_lock:

        if (
            analysis_cache is not None
            and analysis_cache_key == current_key
        ):

            print("Using Cached Analysis Result")

            return analysis_cache

    result = analyze_project(document_text)

    with analysis_lock:

        analysis_cache = result

        analysis_cache_key = current_key

    return result


# ==================================================
# HOME DASHBOARD
# ==================================================

@app.route("/", methods=["GET"])
def home():

    chunks = load_chunks()

    session_info = load_active_session()

    filenames = sorted({
        item.get("filename", "Unknown")
        for item in chunks
    })

    return render_template(

        "index.html",

        filenames=filenames,

        chunk_count=len(chunks),

        session_info=session_info

    )


# ==================================================
# DOCUMENT UPLOAD
# NEW UPLOAD = NEW SESSION
# ==================================================

@app.route("/upload", methods=["POST"])
def upload():

    files = request.files.getlist("files")

    if not files:

        files = request.files.getlist("documents")

    files = [
        file for file in files
        if file and file.filename
    ]

    if not files:

        return jsonify({

            "success": False,

            "message": "Please select documents."

        }), 400


    if len(files) > MAX_FILES_PER_UPLOAD:

        return jsonify({

            "success": False,

            "message": "Maximum 10 files allowed."

        }), 400


    new_chunks = []

    successful_files = []

    failed_files = []


    for file in files:

        original_filename = secure_filename(
            file.filename
        )

        extension = Path(
            original_filename
        ).suffix.lower()


        # Check supported extensions

        if extension not in SUPPORTED_EXTENSIONS:

            failed_files.append(
                original_filename
                + ": Unsupported file type"
            )

            continue


        unique_name = (

            uuid.uuid4().hex

            + "_"

            + original_filename

        )

        destination = UPLOAD_DIR / unique_name


        try:

            file.save(destination)


            # TEXT EXTRACTION

            extraction_start = time.perf_counter()

            document_text = extract_text(
                str(destination)
            )

            extraction_time = (
                time.perf_counter()
                - extraction_start
            )

            print(

                f"Text Extraction: {original_filename} - "

                f"{extraction_time:.2f} seconds"

            )


            if (
                not document_text
                or not document_text.strip()
            ):

                failed_files.append(

                    original_filename
                    + ": No readable text"

                )

                destination.unlink(
                    missing_ok=True
                )

                continue


            # CHUNKING

            chunk_start = time.perf_counter()

            document_chunks = chunk_text(
                document_text
            )

            chunk_time = (
                time.perf_counter()
                - chunk_start
            )

            print(

                f"Chunking: {original_filename} - "

                f"{chunk_time:.2f} seconds"

            )


            if not document_chunks:

                failed_files.append(

                    original_filename
                    + ": No chunks generated"

                )

                destination.unlink(
                    missing_ok=True
                )

                continue


            # STORE NEW CHUNKS

            for chunk in document_chunks:

                if isinstance(chunk, str):

                    text_value = chunk

                elif isinstance(chunk, dict):

                    text_value = chunk.get(
                        "text",
                        ""
                    )

                else:

                    text_value = str(chunk)


                if text_value.strip():

                    new_chunks.append({

                        "id": uuid.uuid4().hex,

                        "filename": original_filename,

                        "text": text_value

                    })


            successful_files.append(
                original_filename
            )


        except Exception as exc:

            app.logger.exception(
                "Document processing failed"
            )

            failed_files.append(

                original_filename
                + ": "
                + str(exc)

            )

            destination.unlink(
                missing_ok=True
            )


    # ------------------------------------------
    # CHECK UPLOAD RESULT
    # ------------------------------------------

    if not successful_files or not new_chunks:

        return jsonify({

            "success": False,

            "message": (
                "No documents uploaded successfully."
            ),

            "failed_files": failed_files

        }), 400


    # ------------------------------------------
    # CREATE NEW ANALYSIS SESSION
    # ------------------------------------------

    try:

        session_info = create_new_session(
            new_chunks
        )

    except Exception as exc:

        app.logger.exception(
            "Unable to create new session"
        )

        return jsonify({

            "success": False,

            "message": "Unable to create new session.",

            "error": str(exc)

        }), 500


    return jsonify({

        "success": True,

        "message": (
            "New project analysis session created successfully."
        ),

        "session_id": session_info["session_id"],

        "files": successful_files,

        "failed_files": failed_files,

        "total_chunks": len(new_chunks)

    })


# ==================================================
# PROJECT ANALYSIS API
# ==================================================

@app.route("/api/analyze", methods=["GET"])
def api_analyze():

    api_start = time.perf_counter()

    chunks = load_chunks()

    document_text = combine_uploaded_text(
        chunks
    )


    if not document_text.strip():

        return jsonify({

            "success": False,

            "message": "Upload project documents first."

        }), 400


    try:

        result = get_cached_analysis(
            document_text
        )

        api_time = (
            time.perf_counter()
            - api_start
        )

        session_info = load_active_session()

        print(

            "Analysis API Response Time:",

            round(api_time, 2),

            "seconds"

        )


        return jsonify({

            "success": True,

            "session": session_info,

            "scope": result["scope"],

            "health": result["health"],

            "risks": result["risks"],

            "risk_summary": result["risk_summary"],

            "forecast": result["forecast"],

            "blockers": result["blockers"],

            "action_items": result["action_items"],

            "uploaded_files": sorted({

                item.get("filename", "Unknown")

                for item in chunks

            })

        })


    except Exception as exc:

        app.logger.exception(
            "Project analysis failed"
        )

        return jsonify({

            "success": False,

            "message": "Project analysis failed.",

            "error": str(exc)

        }), 500


# ==================================================
# RISK API
# ==================================================

@app.route("/api/risks", methods=["GET"])
def api_risks():

    chunks = load_chunks()

    document_text = combine_uploaded_text(
        chunks
    )


    if not document_text.strip():

        return jsonify({

            "success": True,

            "risks": [],

            "total_risks": 0

        })


    try:

        result = get_cached_analysis(
            document_text
        )

        return jsonify({

            "success": True,

            "risks": result["risks"],

            "total_risks": len(
                result["risks"]
            )

        })


    except Exception as exc:

        app.logger.exception(
            "Risk API failed"
        )

        return jsonify({

            "success": False,

            "message": str(exc),

            "risks": [],

            "total_risks": 0

        }), 500


# ==================================================
# AI DOCUMENT ASSISTANT
# ONLY ACTIVE SESSION DATA
# ==================================================

@app.route("/ask", methods=["POST"])
def ask():

    if request.is_json:

        data = request.get_json(
            silent=True
        ) or {}

        question = data.get(
            "question",
            ""
        ).strip()

    else:

        question = request.form.get(
            "question",
            ""
        ).strip()


    if not question:

        return jsonify({

            "success": False,

            "answer": "Please enter your question.",

            "sources": []

        }), 400


    # Only active session chunks

    chunks = load_chunks()


    if not chunks:

        return jsonify({

            "success": True,

            "answer": "Please upload documents first.",

            "sources": []

        })


    try:

        from sklearn.feature_extraction.text import TfidfVectorizer

        from sklearn.metrics.pairwise import cosine_similarity


        valid_chunks = [

            item for item in chunks

            if item.get("text", "").strip()

        ]


        if not valid_chunks:

            return jsonify({

                "success": True,

                "answer": (
                    "No readable document content found."
                ),

                "sources": []

            })


        texts = [

            item["text"]

            for item in valid_chunks

        ]


        vectorizer = TfidfVectorizer(

            stop_words="english",

            max_features=3000

        )


        matrix = vectorizer.fit_transform(

            texts + [question]

        )


        scores = cosine_similarity(

            matrix[-1],

            matrix[:-1]

        ).flatten()


        ranked_indices = scores.argsort()[::-1][:5]


        results = []


        for index in ranked_indices:

            score = float(scores[index])

            if score <= 0:
                continue

            item = valid_chunks[index]

            results.append({

                "filename": item.get(
                    "filename",
                    "Unknown"
                ),

                "text": item.get(
                    "text",
                    ""
                ),

                "score": round(score, 4)

            })


        if not results:

            answer = (

                "No relevant information found "

                "in the currently uploaded documents."

            )

        else:

            answer = (

                "Relevant information from the current "

                "project upload:\n\n"

                + "\n\n---\n\n".join([

                    f"Source: {item['filename']}\n"

                    f"{item['text']}"

                    for item in results

                ])

            )


        return jsonify({

            "success": True,

            "answer": answer,

            "sources": results

        })


    except Exception as exc:

        app.logger.exception(
            "Assistant failed"
        )

        return jsonify({

            "success": False,

            "answer": "Unable to process your question.",

            "error": str(exc),

            "sources": []

        }), 500


# ==================================================
# ACTIVE SESSION API
# ==================================================

@app.route("/api/session", methods=["GET"])
def api_session():

    session_info = load_active_session()

    chunks = load_chunks()

    return jsonify({

        "success": True,

        "session": session_info,

        "uploaded_files": sorted({

            item.get("filename", "Unknown")

            for item in chunks

        }),

        "total_chunks": len(chunks)

    })


# ==================================================
# APPLICATION START
# ==================================================

if __name__ == "__main__":

    print("\n======================================")

    print(" AI PROJECT INTELLIGENCE PLATFORM")

    print(" MILESTONE 1 + MILESTONE 2")

    print(" NEW UPLOAD = NEW ANALYSIS SESSION")

    print("======================================")

    print("Server: http://127.0.0.1:5000")

    print("Archive:", ARCHIVE_DIR)

    print("======================================\n")


    app.run(

        host="127.0.0.1",

        port=5000,

        debug=False,

        use_reloader=False,

        threaded=True

    )
