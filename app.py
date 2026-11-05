import json
import uuid
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ingestion import (
    extract_text,
    chunk_text,
    SUPPORTED_EXTENSIONS,
)

from scope_agent import extract_scope
from risk_agent import detect_risks
from forecasting_agent import forecast_delivery
from blocker_agent import identify_blockers
from action_item_agent import identify_action_items
from health_score import calculate_health_score


# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = "milestone2-project-secret-key"

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
CHUNKS_FILE = DATA_DIR / "chunks.json"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

MAX_FILES_PER_UPLOAD = 50


# --------------------------------------------------
# SESSION CLEANUP
# --------------------------------------------------

def clear_previous_session():

    for file_path in UPLOAD_DIR.iterdir():

        if file_path.is_file():

            try:
                file_path.unlink()

            except OSError:
                app.logger.exception(
                    "Could not delete old upload"
                )

    CHUNKS_FILE.write_text(
        "[]",
        encoding="utf-8"
    )


# --------------------------------------------------
# CHUNK STORAGE
# --------------------------------------------------

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

    except Exception:
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


# --------------------------------------------------
# DOCUMENT RETRIEVAL
# --------------------------------------------------

def retrieve_documents(question, chunks, top_k=5):

    if not question.strip() or not chunks:
        return []

    valid_chunks = [
        item for item in chunks
        if item.get("text", "").strip()
    ]

    if not valid_chunks:
        return []

    texts = [
        item["text"]
        for item in valid_chunks
    ]

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english"
        )

        matrix = vectorizer.fit_transform(
            texts + [question]
        )

        scores = cosine_similarity(
            matrix[-1],
            matrix[:-1]
        ).flatten()

    except ValueError:
        return []

    ranked_indices = scores.argsort()[::-1][:top_k]

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

    return results


# --------------------------------------------------
# COMBINE DOCUMENT TEXT
# --------------------------------------------------

def combine_uploaded_text(chunks):

    combined = []

    for item in chunks:

        filename = item.get("filename", "Unknown")
        content = item.get("text", "").strip()

        if content:

            combined.append(
                f"\nDocument: {filename}\n{content}"
            )

    return "\n\n".join(combined)


# --------------------------------------------------
# MILESTONE 2 PROJECT ANALYSIS
# --------------------------------------------------

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
        "risks": risks,
        "forecast": forecast,
        "blockers": blockers,
        "action_items": action_items,
        "health": health
    }


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

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


# --------------------------------------------------
# DOCUMENT UPLOAD API
# --------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload():

    files = request.files.getlist("files")

    # Backward compatibility with the old form field.
    if not files:
        files = request.files.getlist("documents")

    files = [
        file for file in files
        if file and file.filename
    ]

    if not files:

        return jsonify({
            "success": False,
            "message": "Please select documents first."
        }), 400

    if len(files) > MAX_FILES_PER_UPLOAD:

        return jsonify({
            "success": False,
            "message": "Maximum 50 files allowed."
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

            chunks = chunk_text(document_text)

            if not chunks:

                failed_files.append(
                    original_filename + ": No chunks generated"
                )

                destination.unlink(missing_ok=True)

                continue

            for chunk in chunks:

                if isinstance(chunk, str):

                    text_value = chunk

                elif isinstance(chunk, dict):

                    text_value = chunk.get("text", "")

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
                "Upload failed: %s",
                original_filename
            )

            failed_files.append(
                original_filename + ": " + str(exc)
            )

            destination.unlink(missing_ok=True)

    if new_chunks:

        existing_chunks.extend(new_chunks)

        save_chunks(existing_chunks)

    if not successful_files:

        return jsonify({
            "success": False,
            "message": "No documents were processed successfully.",
            "failed_files": failed_files
        }), 400

    return jsonify({
        "success": True,
        "message": (
            f"Successfully uploaded {len(successful_files)} file(s)."
        ),
        "files": successful_files,
        "failed_files": failed_files
    })


# --------------------------------------------------
# COMPLETE ANALYSIS API
# --------------------------------------------------

@app.route("/api/analyze", methods=["GET"])
def api_analyze():

    chunks = load_chunks()

    document_text = combine_uploaded_text(chunks)

    if not document_text.strip():

        return jsonify({
            "success": False,
            "message": "Please upload project documents first."
        }), 400

    try:

        result = analyze_project(document_text)

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
            "Analysis failed"
        )

        return jsonify({
            "success": False,
            "message": "Project analysis failed.",
            "error": str(exc)
        }), 500


# --------------------------------------------------
# RISK API
# --------------------------------------------------

@app.route("/api/risks", methods=["GET"])
def api_risks():

    chunks = load_chunks()

    document_text = combine_uploaded_text(chunks)

    if not document_text.strip():

        return jsonify({
            "success": True,
            "risks": [],
            "total_risks": 0
        })

    risks = detect_risks(document_text)

    return jsonify({
        "success": True,
        "risks": risks,
        "total_risks": len(risks)
    })


# --------------------------------------------------
# AI PROJECT ASSISTANT
# --------------------------------------------------

@app.route("/ask", methods=["POST"])
def ask():

    if request.is_json:

        data = request.get_json(silent=True) or {}

        question = data.get("question", "").strip()

    else:

        question = request.form.get(
            "question",
            ""
        ).strip()

    if not question:

        return jsonify({
            "success": False,
            "answer": "Please enter a question.",
            "sources": []
        }), 400

    chunks = load_chunks()

    results = retrieve_documents(
        question,
        chunks,
        top_k=5
    )

    if not results:

        return jsonify({
            "success": True,
            "answer": (
                "No relevant information was found "
                "in the uploaded documents."
            ),
            "sources": []
        })

    answer_parts = []

    for item in results:

        answer_parts.append(
            f"Source: {item['filename']}\n"
            f"{item['text']}"
        )

    answer = (
        "Relevant information from uploaded documents:\n\n"
        + "\n\n---\n\n".join(answer_parts)
    )

    return jsonify({
        "success": True,
        "answer": answer,
        "sources": results
    })


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    clear_previous_session()

    print("\n===================================")
    print(" AI PROJECT INTELLIGENCE PLATFORM ")
    print(" MILESTONE 1 + MILESTONE 2")
    print("===================================")
    print("Dashboard: http://127.0.0.1:5000")
    print("===================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )
