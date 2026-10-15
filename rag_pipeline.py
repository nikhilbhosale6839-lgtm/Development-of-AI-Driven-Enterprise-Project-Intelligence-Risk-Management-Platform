import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "data" / "chunks.json"


def load_chunks():
    if not INDEX_FILE.exists():
        return []

    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def retrieve_documents(question, top_k=5):
    chunks = load_chunks()

    if not chunks:
        return []

    documents = [
        item.get("text", "")
        for item in chunks
    ]

    documents = [
        document for document in documents
        if document.strip()
    ]

    if not documents:
        return []

    try:
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

    except ValueError:
        return []

    results = []

    for index in scores.argsort()[::-1]:
        if scores[index] <= 0:
            continue

        results.append({
            "source": chunks[index].get(
                "source", "Unknown"
            ),
            "chunk_number": chunks[index].get(
                "chunk_number", 0
            ),
            "text": documents[index],
            "score": float(scores[index])
        })

        if len(results) >= top_k:
            break

    return results
