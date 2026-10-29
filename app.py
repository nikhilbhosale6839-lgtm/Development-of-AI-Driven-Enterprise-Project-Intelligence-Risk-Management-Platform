```python
import json
import uuid
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)

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


# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret"

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
CHUNKS_FILE = DATA_DIR / "chunks.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

MAX_FILES_PER_UPLOAD = 50


# --------------------------------------------------
# DATA STORAGE
# --------------------------------------------------

def load_chunks():
    """Load indexed document chunks from JSON."""

    if not CHUNKS_FILE.exists():
        return []

    try:
        with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_chunks(chunks):
    """Save indexed document chunks."""

    with open(CHUNKS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )


# --------------------------------------------------
# DOCUMENT SEARCH / RAG RETRIEVAL
# --------------------------------------------------

def retrieve_documents(question, chunks, top_k=5):
    """
    Retrieve relevant chunks using TF-IDF similarity.

    This is a lightweight retrieval implementation,
    not a generative LLM-based RAG pipeline.
    """

    if not question.strip() or not chunks:
        return []

    texts = [
        item.get("text", "")
        for item in chunks
        if item.get("text", "").strip()
    ]

    valid_chunks = [
        item for item in chunks
        if item.get("text", "").strip()
    ]

    if not texts:
        return []

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
            "filename": item.get(
                "filename",
                "Unknown document"
            ),
            "text": item.get("text", ""),
            "score": round(score, 4),
        })

    return results


# --------------------------------------------------
# PROJECT ANALYSIS
# --------------------------------------------------

def analyze_project(document_text):
    """Run all Milestone 2 agents on document text."""

    return {
        "scope": extract_scope(document_text),
        "risks": detect_risks(document_text),
        "forecast": forecast_delivery(document_text),
        "blockers": identify_blockers(document_text),
        "action_items": identify_action_items(document_text),
    }


def combine_uploaded_text(chunks):
    """Combine unique uploaded document text."""

    combined = []
    seen = set()

    for item in chunks:
        filename = item.get("filename", "")
        content = item.get("text", "").strip()

        if not content:
            continue

        key = (filename, content)

        if key in seen:
            continue

        seen.add(key)

        combined.append(
            f"\nDocument: {filename}\n{content}"
        )

    return "\n\n".join(combined)


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

    analysis = None

    if chunks:
        document_text = combine_uploaded_text(chunks)

        if document_text.strip():
            try:
                analysis = analyze_project(document_text)
            except Exception as exc:
                app.logger.exception(
                    "Project analysis failed"
                )
                flash(
                    f"Analysis error: {exc}",
                    "error"
                )

    return render_template(
        "index.html",
        filenames=filenames,
        chunk_count=len(chunks),
        analysis=analysis,
    )


# --------------------------------------------------
# DOCUMENT UPLOAD
# --------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("documents")

    files = [
        file for file in files
        if file and file.filename
    ]

    if not files:
        flash("Please select at least one document.", "error")
        return redirect(url_for("home"))

    if len(files) > MAX_FILES_PER_UPLOAD:
        flash(
            f"Maximum {MAX_FILES_PER_UPLOAD} files per upload.",
            "error"
        )
        return redirect(url_for("home"))

    existing_chunks = load_chunks()
    new_chunks = []
    successful_files = 0
    failed_files = []

    for file in files:
        original_filename = secure_filename(file.filename)

        extension = Path(original_filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            failed_files.append(
                f"{original_filename}: unsupported file type"
            )
            continue

        unique_name = (
            f"{uuid.uuid4().hex}_"
            f"{original_filename}"
        )

        destination = UPLOAD_DIR / unique_name

        try:
            file.save(destination)

            document_text = extract_text(str(destination))

            if not document_text or not document_text.strip():
                failed_files.append(
                    f"{original_filename}: no readable text found"
                )
                destination.unlink(missing_ok=True)
                continue

            chunks = chunk_text(document_text)

            if not chunks:
                failed_files.append(
                    f"{original_filename}: no chunks generated"
                )
                destination.unlink(missing_ok=True)
                continue

            for chunk in chunks:
                if isinstance(chunk, str):
                    chunk_text_value = chunk

                elif isinstance(chunk, dict):
                    chunk_text_value = chunk.get("text", "")

                else:
                    chunk_text_value = str(chunk)

                if chunk_text_value.strip():
                    new_chunks.append({
                        "id": uuid.uuid4().hex,
                        "filename": original_filename,
                        "text": chunk_text_value,
                    })

            successful_files += 1

        except Exception as exc:
            app.logger.exception(
                "Failed to process %s",
                original_filename
            )

            failed_files.append(
                f"{original_filename}: {str(exc)}"
            )

            if destination.exists():
                destination.unlink(missing_ok=True)

    if new_chunks:
        existing_chunks.extend(new_chunks)
        save_chunks(existing_chunks)

    if successful_files:
        flash(
            f"Successfully processed {successful_files} file(s).",
            "success"
        )

    if failed_files:
        flash(
            "Some files could not be processed: "
            + "; ".join(failed_files),
            "error"
        )

    return redirect(url_for("home"))


# --------------------------------------------------
# PROJECT ASSISTANT
# --------------------------------------------------

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()

    if not question:
        return jsonify({
            "success": False,
            "answer": "Please enter a question.",
            "sources": [],
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
                "No sufficiently relevant document text was found "
                "for this question."
            ),
            "sources": [],
        })

    answer_parts = [
        (
            f"Source: {item['filename']}\n"
            f"{item['text']}"
        )
        for item in results
    ]

    answer = (
        "Relevant information retrieved from your uploaded "
        "documents:\n\n"
        + "\n\n---\n\n".join(answer_parts)
    )

    return jsonify({
        "success": True,
        "answer": answer,
        "sources": [
            {
                "filename": item["filename"],
                "score": item["score"],
                "text": item["text"],
            }
            for item in results
        ],
    })


# --------------------------------------------------
# RISKS API
# --------------------------------------------------

@app.route("/api/risks", methods=["GET"])
def api_risks():
    chunks = load_chunks()
    document_text = combine_uploaded_text(chunks)

    if not document_text.strip():
        return jsonify({
            "success": True,
            "risks": [],
            "total_risks": 0,
        })

    result = detect_risks(document_text)

    return jsonify(result)


# --------------------------------------------------
# COMPLETE PROJECT ANALYSIS API
# --------------------------------------------------

@app.route("/api/analyze", methods=["GET"])
def api_analyze():
    chunks = load_chunks()
    document_text = combine_uploaded_text(chunks)

    if not document_text.strip():
        return jsonify({
            "success": False,
            "message": "Upload project documents first."
        }), 400

    try:
        result = analyze_project(document_text)

        return jsonify({
            "success": True,
            "analysis": result
        })

    except Exception as exc:
        app.logger.exception(
            "Project analysis API failed"
        )

        return jsonify({
            "success": False,
            "message": "Project analysis failed.",
            "error": str(exc)
        }), 500


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
```
