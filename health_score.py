from risk_agent import analyze_risks
from blocker_agent import identify_blockers
from rag_pipeline import load_chunks


def calculate_health_score():
    if not load_chunks():
        return {
            "score": 0,
            "status": "No Data",
            "risk_count": 0,
            "blocker_count": 0
        }

    risks = analyze_risks()
    blockers = identify_blockers()

    score = max(
        0,
        100 - len(risks) * 10 - len(blockers) * 5
    )

    if score >= 80:
        status = "Healthy"
    elif score >= 50:
        status = "Needs Attention"
    else:
        status = "At Risk"

    return {
        "score": score,
        "status": status,
        "risk_count": len(risks),
        "blocker_count": len(blockers),
        "note": (
            "Heuristic score for demonstration only; "
            "not a validated project-health measurement."
        )
    }
