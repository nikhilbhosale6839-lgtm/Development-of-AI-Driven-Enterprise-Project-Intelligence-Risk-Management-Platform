def calculate_health_score(risks, blockers, forecast):

    # Convert agent dictionary outputs into lists
    if isinstance(risks, dict):
        risks = risks.get("risks", [])

    if isinstance(blockers, dict):
        blockers = blockers.get("blockers", [])

    if not isinstance(risks, list):
        risks = []

    if not isinstance(blockers, list):
        blockers = []

    if not isinstance(forecast, dict):
        forecast = {}

    risk_count = len(risks)
    blocker_count = len(blockers)

    score = 100

    # Risk penalty
    for risk in risks:

        if not isinstance(risk, dict):
            continue

        severity = risk.get("severity", "").lower()

        if severity == "high":
            score -= 15
        elif severity == "medium":
            score -= 8
        else:
            score -= 3

    # Blocker penalty
    score -= blocker_count * 10

    # Forecast penalty
    delivery_status = forecast.get(
        "delivery_status", ""
    )

    delivery_status = str(delivery_status).lower()

    if "delayed" in delivery_status or "at risk" in delivery_status:
        score -= 15

    score = max(0, min(100, score))

    if score >= 80:
        status = "Healthy"
    elif score >= 50:
        status = "At Risk"
    else:
        status = "Critical"

    return {
        "health_score": score,
        "health_status": status,
        "risk_count": risk_count,
        "blocker_count": blocker_count
    }
