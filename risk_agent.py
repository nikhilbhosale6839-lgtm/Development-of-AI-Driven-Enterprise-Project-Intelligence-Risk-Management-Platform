from rag_pipeline import load_chunks


RISK_CATEGORIES = {
    "Schedule Risk": [
        "delay",
        "deadline missed",
        "overdue",
        "behind schedule",
        "late delivery"
    ],
    "Dependency Risk": [
        "blocked",
        "dependency",
        "pending approval",
        "waiting for approval"
    ],
    "Scope Risk": [
        "scope change",
        "unclear requirements",
        "requirement change",
        "out of scope"
    ],
    "Quality Risk": [
        "bug",
        "defect",
        "failed testing",
        "test failure"
    ],
    "Resource Risk": [
        "resource shortage",
        "unavailable resource",
        "insufficient staff"
    ]
}


def analyze_risks():
    chunks = load_chunks()

    if not chunks:
        return []

    risks = []

    for category, keywords in RISK_CATEGORIES.items():
        for chunk in chunks:
            text = chunk.get("text", "").lower()

            matches = [
                keyword
                for keyword in keywords
                if keyword in text
            ]

            if matches:
                risks.append({
                    "category": category,
                    "source": chunk.get(
                        "source", "Unknown"
                    ),
                    "evidence": chunk.get("text", "")[:500],
                    "keywords": matches,
                    "recommendation": (
                        "Review the evidence, confirm the risk "
                        "with the project owner, and assign "
                        "a mitigation action."
                    )
                })

    return risks
