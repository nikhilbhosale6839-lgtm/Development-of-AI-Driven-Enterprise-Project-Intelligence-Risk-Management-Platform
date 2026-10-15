from rag_pipeline import load_chunks


BLOCKER_KEYWORDS = [
    "blocked",
    "blocker",
    "pending",
    "waiting for",
    "dependency",
    "action item",
    "not completed",
    "on hold"
]


def identify_blockers():
    chunks = load_chunks()
    blockers = []

    for chunk in chunks:
        text = chunk.get("text", "")

        matches = [
            keyword
            for keyword in BLOCKER_KEYWORDS
            if keyword in text.lower()
        ]

        if matches:
            blockers.append({
                "source": chunk.get(
                    "source", "Unknown"
                ),
                "matched_terms": matches,
                "description": text[:1000],
                "suggested_action": (
                    "Confirm the blocker, identify its owner, "
                    "and agree on a resolution date."
                )
            })

    return blockers
