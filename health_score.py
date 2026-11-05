def calculate_health_score(risks, blockers, forecast):

    risk_count = len(risks)
    blocker_count = len(blockers)

    score = 100

    # Risk penalty
    for risk in risks:
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
    ).lower()

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
