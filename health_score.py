import re
from datetime import datetime


# =========================================================
# 1. SAFE DATA EXTRACTION
# =========================================================

def extract_list(data, possible_keys=None):

    if possible_keys is None:
        possible_keys = [
            "risks",
            "blockers",
            "actions",
            "tasks",
            "data",
            "results",
            "items"
        ]

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):

            nested = extract_list(value, possible_keys)

            if nested:
                return nested

    return []


# =========================================================
# 2. NORMALIZE TEXT
# =========================================================

def normalize_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip().lower()


# =========================================================
# 3. EXTRACT SEVERITY
# =========================================================

def get_severity(item):

    if not isinstance(item, dict):
        return "medium"

    value = normalize_text(
        item.get("severity")
        or item.get("priority")
        or item.get("risk_level")
        or item.get("impact")
        or "medium"
    )

    if any(word in value for word in [
        "critical",
        "very high"
    ]):
        return "critical"

    if "high" in value:
        return "high"

    if "low" in value:
        return "low"

    return "medium"


# =========================================================
# 4. EXTRACT STATUS
# =========================================================

def get_status(item):

    if not isinstance(item, dict):
        return ""

    return normalize_text(
        item.get("status")
        or item.get("state")
        or item.get("progress")
        or ""
    )


# =========================================================
# 5. COUNT RISK LEVELS
# =========================================================

def calculate_risk_counts(risks):

    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "total": 0
    }

    for risk in risks:

        severity = get_severity(risk)

        counts[severity] += 1

        counts["total"] += 1

    return counts


# =========================================================
# 6. COUNT BLOCKERS
# =========================================================

def calculate_blocker_counts(blockers):

    counts = {
        "open": 0,
        "resolved": 0,
        "total": len(blockers)
    }

    for blocker in blockers:

        status = get_status(blocker)

        if any(word in status for word in [
            "resolved",
            "closed",
            "completed",
            "done"
        ]):
            counts["resolved"] += 1

        else:
            counts["open"] += 1

    return counts


# =========================================================
# 7. COUNT DELAYED TASKS
# =========================================================

def calculate_delayed_tasks(forecast):

    tasks = extract_list(
        forecast,
        [
            "tasks",
            "delayed_tasks",
            "records",
            "data",
            "items"
        ]
    )

    delayed = 0
    completed = 0
    total = len(tasks)

    for task in tasks:

        if not isinstance(task, dict):
            continue

        status = get_status(task)

        if any(word in status for word in [
            "completed",
            "complete",
            "done",
            "closed"
        ]):
            completed += 1

        elif any(word in status for word in [
            "delayed",
            "overdue",
            "at risk",
            "behind"
        ]):
            delayed += 1

    return {
        "total": total,
        "delayed": delayed,
        "completed": completed,
        "pending": max(0, total - delayed - completed)
    }


# =========================================================
# 8. CALCULATE HEALTH SCORE
# =========================================================

def calculate_health_score(
    risks,
    blockers,
    forecast
):

    risk_list = extract_list(risks)

    blocker_list = extract_list(
        blockers,
        [
            "blockers",
            "items",
            "data",
            "results"
        ]
    )

    risk_counts = calculate_risk_counts(
        risk_list
    )

    blocker_counts = calculate_blocker_counts(
        blocker_list
    )

    task_counts = calculate_delayed_tasks(
        forecast
    )

    # -----------------------------------------------------
    # HEALTH SCORE PENALTIES
    # -----------------------------------------------------

    score = 100

    penalties = {
        "critical_risk": 20,
        "high_risk": 15,
        "medium_risk": 8,
        "low_risk": 3,
        "open_blocker": 10,
        "delayed_task": 8
    }

    score -= (
        risk_counts["critical"]
        * penalties["critical_risk"]
    )

    score -= (
        risk_counts["high"]
        * penalties["high_risk"]
    )

    score -= (
        risk_counts["medium"]
        * penalties["medium_risk"]
    )

    score -= (
        risk_counts["low"]
        * penalties["low_risk"]
    )

    score -= (
        blocker_counts["open"]
        * penalties["open_blocker"]
    )

    score -= (
        task_counts["delayed"]
        * penalties["delayed_task"]
    )

    score = max(
        0,
        min(100, score)
    )

    # -----------------------------------------------------
    # HEALTH STATUS
    # -----------------------------------------------------

    if score >= 85:

        health_status = "Excellent"

    elif score >= 70:

        health_status = "Good"

    elif score >= 50:

        health_status = "Moderate"

    elif score >= 30:

        health_status = "At Risk"

    else:

        health_status = "Critical"

    # -----------------------------------------------------
    # HEALTH COLOR
    # -----------------------------------------------------

    if score >= 70:

        health_color = "green"

    elif score >= 50:

        health_color = "orange"

    else:

        health_color = "red"

    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    recommendations = []

    if risk_counts["critical"] > 0:

        recommendations.append(
            "Immediately address critical project risks."
        )

    if risk_counts["high"] > 0:

        recommendations.append(
            "Prepare mitigation plans for high-priority risks."
        )

    if blocker_counts["open"] > 0:

        recommendations.append(
            "Resolve open blockers to avoid project delays."
        )

    if task_counts["delayed"] > 0:

        recommendations.append(
            "Review delayed tasks and update the delivery schedule."
        )

    if not recommendations:

        recommendations.append(
            "Project health is stable. Continue regular monitoring."
        )

    # -----------------------------------------------------
    # FINAL RESULT
    # -----------------------------------------------------

    return {

        "success": True,

        "health_score": round(score, 2),

        "health_status": health_status,

        "health_color": health_color,

        "risk_counts": risk_counts,

        "blocker_counts": blocker_counts,

        "task_counts": task_counts,

        "penalties": penalties,

        "recommendations": recommendations,

        "analysis_date": datetime.now().isoformat()

    }


# =========================================================
# 9. ALTERNATIVE FUNCTION
# =========================================================

def analyze_project_health(
    risks,
    blockers,
    forecast
):

    return calculate_health_score(
        risks,
        blockers,
        forecast
    )


# =========================================================
# 10. TEST
# =========================================================

if __name__ == "__main__":

    sample_risks = {
        "risks": [
            {
                "severity": "High",
                "status": "Open"
            },
            {
                "severity": "Medium",
                "status": "Open"
            }
        ]
    }

    sample_blockers = {
        "blockers": [
            {
                "status": "Open"
            }
        ]
    }

    sample_forecast = {
        "tasks": [
            {
                "status": "Delayed"
            },
            {
                "status": "Completed"
            }
        ]
    }

    result = calculate_health_score(
        sample_risks,
        sample_blockers,
        sample_forecast
    )

    print("\nPROJECT HEALTH REPORT")
    print("=" * 40)

    print("Health Score:", result["health_score"])
    print("Health Status:", result["health_status"])
    print("Risk Counts:", result["risk_counts"])
    print("Blocker Counts:", result["blocker_counts"])
    print("Task Counts:", result["task_counts"])

    print("\nRecommendations:")

    for recommendation in result["recommendations"]:
        print("-", recommendation)
