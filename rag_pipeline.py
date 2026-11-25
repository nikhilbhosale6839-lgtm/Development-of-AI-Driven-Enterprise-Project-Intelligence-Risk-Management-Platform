import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =====================================================
# 1. PROJECT PATH
# =====================================================

BASE_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = BASE_DIR / "data" / "chunks.json"


# =====================================================
# 2. LOAD DOCUMENT CHUNKS
# =====================================================

def load_chunks():

    if not CHUNKS_FILE.exists():
        return []

    try:

        with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except (json.JSONDecodeError, OSError) as error:

        print("Chunk loading error:", error)

        return []


# =====================================================
# 3. CLEAN QUESTION
# =====================================================

def clean_question(question):

    if question is None:
        return ""

    return str(question).strip()


# =====================================================
# 4. RETRIEVE RELEVANT DOCUMENTS
# =====================================================

def retrieve_documents(question, top_k=5):

    question = clean_question(question)

    if not question:
        return []

    chunks = load_chunks()

    if not chunks:
        return []

    # Remove invalid or empty chunks
    valid_chunks = []

    for item in chunks:

        if not isinstance(item, dict):
            continue

        text = item.get("text", "")

        if not isinstance(text, str):
            continue

        text = text.strip()

        if not text:
            continue

        valid_chunks.append(item)

    if not valid_chunks:
        return []

    documents = [
        item["text"]
        for item in valid_chunks
    ]

    # =================================================
    # TF-IDF VECTORIZATION
    # =================================================

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000
        )

        matrix = vectorizer.fit_transform(
            documents + [question]
        )

        # Question similarity with all document chunks
        scores = cosine_similarity(
            matrix[-1],
            matrix[:-1]
        ).flatten()

    except ValueError as error:

        print("Vectorization error:", error)

        return []

    # =================================================
    # RANK DOCUMENTS
    # =================================================

    ranked_indices = scores.argsort()[::-1]

    results = []

    for index in ranked_indices:

        score = float(scores[index])

        # Ignore irrelevant chunks
        if score <= 0:
            continue

        item = valid_chunks[index]

        result = {

            "source": item.get(
                "source",
                item.get("filename", "Unknown")
            ),

            "filename": item.get(
                "filename",
                item.get("source", "Unknown")
            ),

            "chunk_number": item.get(
                "chunk_number",
                item.get("chunk_index", 0)
            ),

            "text": item["text"],

            "score": round(score, 4)

        }

        results.append(result)

        if len(results) >= top_k:
            break

    return results


# =====================================================
# 5. GENERATE CONTEXT
# =====================================================

def generate_context(question, top_k=5):

    results = retrieve_documents(
        question,
        top_k
    )

    if not results:
        return {
            "question": question,
            "context": "",
            "sources": [],
            "results": []
        }

    context_parts = []

    sources = []

    for item in results:

        context_parts.append(
            item["text"]
        )

        sources.append({
            "filename": item["filename"],
            "chunk_number": item["chunk_number"],
            "score": item["score"]
        })

    context = "\n\n".join(context_parts)

    return {

        "question": question,

        "context": context,

        "sources": sources,

        "results": results

    }


# =====================================================
# 6. RAG SEARCH
# =====================================================

def rag_search(question, top_k=5):

    return generate_context(
        question,
        top_k
    )


# =====================================================
# 7. TEST
# =====================================================

if __name__ == "__main__":

    print("\nPROJECT RISK ADVISOR - RAG PIPELINE")

    question = input("\nEnter your question: ")

    results = retrieve_documents(question)

    if not results:

        print("\nNo relevant documents found.")

    else:

        print("\nRetrieved Documents:\n")

        for result in results:

            print("Source:", result["source"])

            print("Chunk:", result["chunk_number"])

            print("Similarity:", result["score"])

            print("Content:", result["text"][:500])

            print("-" * 60)
