import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from docx import Document


# =====================================================
# SUPPORTED FILE FORMATS
# =====================================================

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".csv",
    ".txt"
}


# =====================================================
# TEXT CLEANING
# =====================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    # Remove null characters
    text = text.replace("\x00", " ")

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove unwanted control characters
    text = re.sub(
        r"[\x01-\x08\x0b\x0c\x0e-\x1f]",
        " ",
        text
    )

    # Normalize spaces and tabs
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # Clean each line without removing line breaks
    lines = [
        line.strip()
        for line in text.split("\n")
    ]

    text = "\n".join(lines)

    return text.strip()


# =====================================================
# PDF TEXT EXTRACTION
# =====================================================

def extract_pdf_text(file_path):

    extracted_pages = []

    reader = PdfReader(file_path)

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            page_text = page.extract_text()

            if page_text:

                extracted_pages.append(

                    f"\n--- PAGE {page_number} ---\n"
                    f"{page_text}"

                )

        except Exception as error:

            print(
                f"PDF page {page_number} extraction error: {error}"
            )

    return "\n".join(
        extracted_pages
    )


# =====================================================
# DOCX TEXT EXTRACTION
# =====================================================

def extract_docx_text(file_path):

    document = Document(file_path)

    extracted_content = []

    # Extract paragraphs
    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:

            extracted_content.append(text)

    # Extract tables
    for table_number, table in enumerate(
        document.tables,
        start=1
    ):

        extracted_content.append(
            f"\n--- TABLE {table_number} ---"
        )

        for row in table.rows:

            row_data = []

            for cell in row.cells:

                cell_text = cell.text.strip()

                row_data.append(
                    cell_text
                )

            extracted_content.append(
                " | ".join(row_data)
            )

    return "\n".join(
        extracted_content
    )


# =====================================================
# CSV TEXT EXTRACTION
# =====================================================

def extract_csv_text(file_path):

    try:

        dataframe = pd.read_csv(

            file_path,

            dtype=str,

            keep_default_na=False

        )

    except UnicodeDecodeError:

        dataframe = pd.read_csv(

            file_path,

            dtype=str,

            keep_default_na=False,

            encoding="latin-1"

        )

    except Exception:

        dataframe = pd.read_csv(

            file_path,

            dtype=str,

            keep_default_na=False,

            engine="python",

            on_bad_lines="skip"

        )

    if dataframe.empty:

        return ""

    extracted_content = []

    # Column headings
    columns = list(
        dataframe.columns
    )

    extracted_content.append(
        "COLUMNS: " + " | ".join(columns)
    )

    # Extract rows
    for index, row in dataframe.iterrows():

        extracted_content.append(
            f"\nRECORD {index + 1}"
        )

        for column in columns:

            value = str(
                row[column]
            ).strip()

            if value:

                extracted_content.append(
                    f"{column}: {value}"
                )

    return "\n".join(
        extracted_content
    )


# =====================================================
# TXT TEXT EXTRACTION
# =====================================================

def extract_txt_text(file_path):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1"
    ]

    for encoding in encodings:

        try:

            with open(
                file_path,
                "r",
                encoding=encoding
            ) as file:

                return file.read()

        except UnicodeDecodeError:

            continue

    raise ValueError(
        "Unable to decode TXT file."
    )


# =====================================================
# MAIN TEXT EXTRACTION FUNCTION
# =====================================================

def extract_text(file_path):

    file_path = Path(file_path)

    if not file_path.exists():

        raise FileNotFoundError(
            "Document file not found."
        )

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:

        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    try:

        if extension == ".pdf":

            text = extract_pdf_text(
                str(file_path)
            )

        elif extension == ".docx":

            text = extract_docx_text(
                str(file_path)
            )

        elif extension == ".csv":

            text = extract_csv_text(
                str(file_path)
            )

        elif extension == ".txt":

            text = extract_txt_text(
                str(file_path)
            )

        else:

            raise ValueError(
                "Unsupported document format."
            )

        text = clean_text(
            text
        )

        if not text:

            raise ValueError(
                "No readable text found in document. Scanned PDFs may require OCR."
            )

        return text

    except Exception as error:

        raise RuntimeError(
            f"Document extraction failed: {error}"
        ) from error


# =====================================================
# SMART TEXT CHUNKING
# =====================================================

def chunk_text(
    text,
    chunk_size=800,
    overlap=100
):

    if not text:

        return []

    if chunk_size <= 0:

        raise ValueError(
            "Chunk size must be greater than zero."
        )

    if overlap < 0 or overlap >= chunk_size:

        raise ValueError(
            "Overlap must be smaller than chunk size."
        )

    text = clean_text(
        text
    )

    if not text:

        return []

    chunks = []

    start = 0

    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        # Try to end at a line boundary
        if end < text_length:

            newline_position = text.rfind(
                "\n",
                start,
                end
            )

            if (
                newline_position > start + chunk_size * 0.5
            ):

                end = newline_position

            else:

                # Try sentence boundary
                sentence_position = max(

                    text.rfind(
                        ". ",
                        start,
                        end
                    ),

                    text.rfind(
                        "? ",
                        start,
                        end
                    ),

                    text.rfind(
                        "! ",
                        start,
                        end
                    )

                )

                if sentence_position > start + chunk_size * 0.5:

                    end = sentence_position + 1

        chunk = text[start:end].strip()

        if chunk:

            chunks.append(
                chunk
            )

        if end >= text_length:

            break

        next_start = end - overlap

        if next_start <= start:

            next_start = end

        start = next_start

    return chunks


# =====================================================
# DOCUMENT PROCESSING
# =====================================================

def process_document(
    file_path,
    chunk_size=800,
    overlap=100
):

    file_path = Path(file_path)

    extracted_text = extract_text(
        str(file_path)
    )

    chunks = chunk_text(

        extracted_text,

        chunk_size=chunk_size,

        overlap=overlap

    )

    return {

        "filename": file_path.name,

        "total_characters": len(
            extracted_text
        ),

        "total_chunks": len(
            chunks
        ),

        "text": extracted_text,

        "chunks": chunks,

        "success": True

    }


# =====================================================
# VALIDATE DOCUMENT
# =====================================================

def validate_document(file_path):

    file_path = Path(file_path)

    if not file_path.exists():

        return {

            "valid": False,

            "message": "File does not exist."

        }

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:

        return {

            "valid": False,

            "message": "Unsupported file format."

        }

    if file_path.stat().st_size == 0:

        return {

            "valid": False,

            "message": "File is empty."

        }

    return {

        "valid": True,

        "message": "Document is valid."

    }
