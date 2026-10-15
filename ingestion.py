from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".csv", ".txt"}


def extract_text(file_path):
    """
    Extract text from supported document formats.
    """

    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    if extension == ".pdf":
        reader = PdfReader(str(path))

        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == ".docx":
        document = Document(str(path))

        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    elif extension == ".csv":
        dataframe = pd.read_csv(path)

        text = dataframe.to_string(index=False)

    elif extension == ".txt":
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

    else:
        raise ValueError("Unsupported file format.")

    if not text.strip():
        raise ValueError(
            "No readable text found in the document."
        )

    return text
