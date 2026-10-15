from rag_pipeline import load_chunks


SCOPE_KEYWORDS = [
    "project objective",
    "requirement",
    "deliverable",
    "scope",
    "acceptance criteria",
    "functional requirement",
    "milestone"
]


def extract_scope():
    chunks = load_chunks()
    results = []

    for chunk in chunks:
        text = chunk.get("text", "")
        lower_text = text.lower()

        matches = [
            keyword
            for keyword in SCOPE_KEYWORDS
            if keyword in lower_text
        ]

        if matches:
            results.append({
                "source": chunk.get(
                    "source", "Unknown"
                ),
                "matched_terms": matches,
                "content": text[:1000]
            })

    return results
