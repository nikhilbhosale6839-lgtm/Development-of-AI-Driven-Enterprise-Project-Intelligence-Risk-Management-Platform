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


app = Flask(__name__)
app.secret_key = "development-only-key"

app.config["MAX_CONTENT_LENGTH"] = (
    100 * 1024 * 1024
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
INDEX_FILE = DATA_DIR / "chunks.json"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def load_chunks():
    if not INDEX_FILE.exists():
        return []

    try:
        with open(
            INDEX_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


def save_chunks(chunks):
    with open(
        INDEX_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )


def retrieve_documents(question, top_k=4):
    chunks = load_chunks()

    if not chunks:
        return []

    documents = [
        item["text"] for item in chunks
    ]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    matrix = vectorizer.fit_transform(
        documents + [question]
    )

    scores = cosine_similarity(
        matrix[-1],
        matrix[:-1]
    ).flatten()

    indices = scores.argsort()[::-1]

    results = []

    for index in indices:
        if scores[index] <= 0:
            continue

        result = dict(chunks[index])
        result["score"] = float(scores[index])

        results.append(result)

        if len(results) >= top_k:
            break

    return results


def analyze_risks():
    chunks = load_chunks()

    if not chunks:
        return [
            "Upload project documents to begin risk analysis."
        ]

    text = " ".join(
        item["text"].lower()
        for item in chunks
    )

    risk_categories = {
        "Schedule Risk": [
            "delay",
            "deadline missed",
            "overdue",
            "behind schedule",
        ],
        "Dependency Risk": [
            "blocked",
            "dependency",
            "pending approval",
        ],
        "Scope Risk": [
            "scope change",
            "unclear requirements",
            "requirement change",
        ],
        "Quality Risk": [
            "bug",
            "defect",
            "failed testing",
        ],
        "Resource Risk": [
            "resource shortage",
            "unavailable resource",
        ],
    }

    detected_risks = []

    for category, keywords in risk_categories.items():
        matches = [
            keyword
            for keyword in keywords
            if keyword in text
        ]

        if matches:
            detected_risks.append({
                "category": category,
                "evidence_keywords": matches,
                "recommendation": (
                    "Review the matching project documents "
                    "and confirm the issue with the project owner."
                )
            })

    if not detected_risks:
        detected_risks.append({
            "category": "Manual Review Recommended",
            "evidence_keywords": [],
            "recommendation": (
                "No configured risk keywords were detected. "
                "Review the project documents for other risks."
            )
        })

    return detected_risks


def calculate_health_score():
    risks = analyze_risks()

    if not load_chunks():
        return 0

    actual_risks = [
        risk for risk in risks
        if risk["category"] != "Manual Review Recommended"
    ]

    # Demonstration heuristic, not a validated forecast.
    score = max(
        20,
        100 - len(actual_risks) * 15
    )

    return score


@app.route("/")
def home():
    chunks = load_chunks()

    sources = sorted({
        item["source"]
        for item in chunks
    })

    risks = analyze_risks()
    health = calculate_health_score()

    return render_template(
        "index.html",
        sources=sources,
        chunk_count=len(chunks),
        risks=risks,
        health=health,
    )


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("documents")

    if len(files) > 50:
        flash(
            "Maximum 50 files per upload request.",
            "error"
        )
        return redirect(url_for("home"))

    chunks = load_chunks()
    processed = 0

    for file in files:
        if not file.filename:
            continue

        filename = secure_filename(file.filename)
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            flash(
                f"Unsupported file format: {filename}",
                "error"
            )
            continue

        unique_name = (
            f"{uuid.uuid4().hex[:8]}_{filename}"
        )

        destination = UPLOAD_DIR / unique_name

        try:
            file.save(destination)

            text = extract_text(destination)

            if not text.strip():
                flash(
                    f"No readable text found: {filename}",
                    "error"
                )
                continue

            pieces = chunk_text(text)

            for number, piece in enumerate(
                pieces,
                start=1
            ):
                chunks.append({
                    "source": filename,
                    "chunk_number": number,
                    "text": piece,
                })

            processed += 1

        except Exception as error:
            flash(
                f"Could not process {filename}: {error}",
                "error"
            )

    save_chunks(chunks)

    if processed:
        flash(
            f"Successfully processed {processed} file(s).",
            "success"
        )

    return redirect(url_for("home"))


@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get(
        "question",
        ""
    ).strip()

    if not question:
        return jsonify({
            "answer": "Please enter a question.",
            "sources": []
        }), 400

    results = retrieve_documents(question)

    if not results:
        return jsonify({
            "answer": (
                "No relevant information was found. "
                "Upload documents or try another question."
            ),
            "sources": []
        })

    answer_parts = []

    for result in results:
        answer_parts.append(
            f"Source: {result['source']}\n"
            f"{result['text']}"
        )

    return jsonify({
        "answer": (
            "Relevant information from your documents:\n\n"
            + "\n\n".join(answer_parts)
        ),
        "sources": [
            result["source"]
            for result in results
        ]
    })


@app.route("/api/risks")
def api_risks():
    return jsonify({
        "risks": analyze_risks(),
        "health_score": calculate_health_score()
    })


if __name__ == "__main__":
    app.run(debug=True)
