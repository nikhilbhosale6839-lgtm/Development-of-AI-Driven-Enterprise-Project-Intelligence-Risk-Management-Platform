from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from docx import Document


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".csv",
    ".txt",
}


def extract_text(file_path):
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(path))

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == ".docx":
        document = Document(str(path))

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        for table in document.tables:
            for row in table.rows:
                paragraphs.append(
                    " | ".join(
                        cell.text for cell in row.cells
                    )
                )

        return "\n".join(paragraphs)

    elif extension == ".csv":
        dataframe = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False
        )

        return dataframe.to_csv(index=False)

    elif extension == ".txt":
        return path.read_text(
            encoding="utf-8",
            errors="replace"
        )

    raise ValueError("Unsupported file format")


def chunk_text(text, chunk_size=800, overlap=100):
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(
            start + chunk_size,
            len(text)
        )

        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks
