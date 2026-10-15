import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    request
)
from werkzeug.utils import secure_filename

from ingestion import SUPPORTED_EXTENSIONS
from rag_pipeline import process_document, ask_question


load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({
            "error": "No file was provided."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "error": "Please select a file."
        }), 400

    original_name = secure_filename(
        uploaded_file.filename
    )

    extension = Path(original_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        return jsonify({
            "error": (
                "Unsupported file format. "
                "Upload PDF, DOCX, CSV, or TXT."
            )
        }), 400

    unique_name = f"{uuid4().hex}_{original_name}"

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_name
    )

    uploaded_file.save(file_path)

    try:
        result = process_document(
            file_path,
            original_name
        )

        return jsonify({
            "message": "Document processed successfully.",
            "result": result
        }), 200

    except Exception as error:
        app.logger.exception(
            "Document processing failed."
        )

        return jsonify({
            "error": (
                "Document processing failed. "
                "Check the application logs."
            )
        }), 500


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}

    question = data.get(
        "question",
        ""
    )

    try:
        answer = ask_question(question)

        return jsonify({
            "question": question,
            "answer": answer
        }), 200

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception(
            "Question answering failed."
        )

        return jsonify({
            "error": (
                "Unable to generate an answer. "
                "Check the application logs."
            )
        }), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "File size must not exceed 10 MB."
    }), 413


if __name__ == "__main__":
    app.run(
        debug=os.getenv(
            "FLASK_DEBUG",
            "False"
        ).lower() == "true"
    )
