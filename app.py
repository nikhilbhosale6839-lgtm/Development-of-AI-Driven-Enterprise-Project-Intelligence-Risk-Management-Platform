import json
import uuid
from pathlib import Path

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

CHUNKS_FILE = DATA_DIR / "chunks.json"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

MAX_FILES_PER_UPLOAD = 10


# ==================================================
# ANALYSIS CACHE
# ==================================================

analysis_cache = None
analysis_cache_key = None


def clear_analysis_cache():

    global analysis_cache
    global analysis_cache_key

    analysis_cache = None
    analysis_cache_key = None


# ==================================================
# SESSION CLEANUP
# ==================================================

def clear_previous_session():

    for file_path in UPLOAD_DIR.iterdir():

        if file_path.is_file():

            try:
                file_path.unlink()

            except OSError:
                app.logger.exception(
                    "Unable to delete previous upload"
                )

    CHUNKS_FILE.write_text(
        "[]",
        encoding="utf-8"
    )

    clear_analysis_cache()


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

        return []


def save_chunks(chunks):

    with open(
        CHUNKS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )


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

    scope = extract_scope(document_text)

    risks = detect_risks(document_text)

    forecast = forecast_delivery(document_text)

    blockers = identify_blockers(document_text)

    action_items = identify_action_items(document_text)

    health = calculate_health_score(
        risks,
        blockers,
        forecast
    )

    return {
        "scope": scope,
        "health": health,
        "risks": risks,
        "forecast": forecast,
        "blockers": blockers,
        "action_items": action_items
    }


def get_cached_analysis(document_text):

    global analysis_cache
    global analysis_cache_key

    current_key = str(hash(document_text))

    if (
        analysis_cache is not None
        and analysis_cache_key == current_key
    ):

        return analysis_cache

    result = analyze_project(document_text)

    analysis_cache = result
    analysis_cache_key = current_key

    return result


# ==================================================
# HOME DASHBOARD
# ==================================================

@app.route("/", methods=["GET"])
def home():

    chunks = load_chunks()

    filenames = sorted({
        item.get("filename", "Unknown")
        for item in chunks
    })

    return render_template(
        "index.html",
        filenames=filenames,
        chunk_count=len(chunks)
    )


# ==================================================
# DOCUMENT UPLOAD
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

    existing_chunks = load_chunks()

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

        if extension not in SUPPORTED_EXTENSIONS:

            failed_files.append(
                original_filename + ": Unsupported file type"
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

            document_text = extract_text(
                str(destination)
            )

            if not document_text or not document_text.strip():

                failed_files.append(
                    original_filename + ": No readable text"
                )

                destination.unlink(missing_ok=True)

                continue

            document_chunks = chunk_text(
                document_text
            )

            if not document_chunks:

                failed_files.append(
                    original_filename + ": No chunks generated"
                )

                destination.unlink(missing_ok=True)

                continue

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
                original_filename + ": " + str(exc)
            )

            destination.unlink(missing_ok=True)

    if new_chunks:

        existing_chunks.extend(new_chunks)

        save_chunks(existing_chunks)

        clear_analysis_cache()

    if not successful_files:

        return jsonify({
            "success": False,
            "message": "No documents uploaded successfully.",
            "failed_files": failed_files
        }), 400

    return jsonify({
        "success": True,
        "message": (
            f"{len(successful_files)} document(s) uploaded successfully."
        ),
        "files": successful_files,
        "failed_files": failed_files
    })


# ==================================================
# PROJECT ANALYSIS API
# ==================================================

@app.route("/api/analyze", methods=["GET"])
def api_analyze():

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

        return jsonify({
            "success": True,
            "scope": result["scope"],
            "health": result["health"],
            "risks": result["risks"],
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

    result = get_cached_analysis(
        document_text
    )

    return jsonify({
        "success": True,
        "risks": result["risks"],
        "total_risks": len(result["risks"])
    })


# ==================================================
# AI DOCUMENT ASSISTANT
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

    chunks = load_chunks()

    if not chunks:

        return jsonify({
            "success": True,
            "answer": "Please upload documents first.",
            "sources": []
        })

    try:

        # Load sklearn only when the assistant is used.
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        valid_chunks = [
            item for item in chunks
            if item.get("text", "").strip()
        ]

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
                "filename": item.get("filename", "Unknown"),
                "text": item.get("text", ""),
                "score": round(score, 4)
            })

        if not results:

            answer = (
                "No relevant information found "
                "in the uploaded documents."
            )

        else:

            answer = (
                "Relevant information from uploaded documents:\n\n"
                + "\n\n---\n\n".join([
                    f"Source: {item['filename']}\n{item['text']}"
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
# APPLICATION START
# ==================================================

if __name__ == "__main__":

    clear_previous_session()

    print("\n======================================")
    print(" AI PROJECT INTELLIGENCE PLATFORM")
    print(" MILESTONE 1 + MILESTONE 2")
    print("======================================")
    print("Server: http://127.0.0.1:5000")
    print("======================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )
