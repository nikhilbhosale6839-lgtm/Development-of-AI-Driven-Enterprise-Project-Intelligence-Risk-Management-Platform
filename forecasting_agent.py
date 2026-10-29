```python
import re
from datetime import datetime, date


def parse_date(value):
    """Parse supported date formats."""

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d %B %Y",
        "%d %b %Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue

    return None


def extract_tasks(document_text):
    """
    Extract task information from simple text lines.

    Example:
    Task: RAG Pipeline | Status: In Progress |
    Due Date: 2026-11-15 | Dependency: API Access Pending
    """

    tasks = []

    if not document_text:
        return tasks

    for line in document_text.splitlines():
        line = line.strip()

        if not line:
            continue

        task_match = re.search(
            r"\bTask\s*:\s*(.*?)(?=\s*\|\s*Status\s*:|$)",
            line,
            re.IGNORECASE
        )

        status_match = re.search(
            r"\bStatus\s*:\s*([^|]+)",
            line,
            re.IGNORECASE
        )

        due_match = re.search(
            r"\b(?:Due Date|Deadline|Planned Completion)\s*:\s*([^|]+)",
            line,
            re.IGNORECASE
        )

        dependency_match = re.search(
            r"\bDependency\s*:\s*([^|]+)",
            line,
            re.IGNORECASE
        )

        if not task_match:
            continue

        task_name = task_match.group(1).strip()
        status = (
            status_match.group(1).strip()
            if status_match else "Unknown"
        )

        due_date_text = (
            due_match.group(1).strip()
            if due_match else None
        )

        dependency = (
            dependency_match.group(1).strip()
            if dependency_match else None
        )

        tasks.append({
            "task": task_name,
            "status": status,
            "due_date_text": due_date_text,
            "dependency": dependency
        })

    return tasks


def forecast_delivery(document_text, reference_date=None):
    """
    Assess potential delivery delays using task status,
    due dates, and dependency information.

    This is a rule-based risk assessment, not a trained
    predictive model.
    """

    if reference_date is None:
        reference_date = date.today()

    if isinstance(reference_date, str):
        reference_date = parse_date(reference_date)

    if reference_date is None:
        raise ValueError(
            "reference_date must be a valid date."
        )

    tasks = extract_tasks(document_text or "")
    forecasts = []

    for task in tasks:
        status = task["status"].lower()
        due_date_text = task["due_date_text"]
        dependency = task["dependency"]

        due_date = (
            parse_date(due_date_text)
            if due_date_text else None
        )

        risks = []
        recommendations = []

        completed_statuses = {
            "completed",
            "complete",
            "done",
            "closed"
        }

        pending_statuses = {
            "pending",
            "not started",
            "in progress",
            "blocked",
            "on hold",
            "delayed"
        }

        if status in completed_statuses:
            assessment = "Completed"

        else:
            if due_date and due_date < reference_date:
                if status in pending_statuses:
                    risks.append("Overdue task")
                    recommendations.append(
                        "Review the delay and agree on a revised "
                        "completion date."
                    )

            if status in {"blocked", "on hold", "delayed"}:
                risks.append("Task is blocked or delayed")
                recommendations.append(
                    "Identify the cause and assign corrective actions."
                )

            if dependency:
                dependency_lower = dependency.lower()

                if any(word in dependency_lower for word in [
                    "pending",
                    "blocked",
                    "unavailable",
                    "not completed"
                ]):
                    risks.append("Dependency may delay delivery")
                    recommendations.append(
                        "Resolve the dependency and confirm its "
                        "expected completion date."
                    )

            if due_date and due_date >= reference_date:
                if status in pending_statuses:
                    days_remaining = (
                        due_date - reference_date
                    ).days

                    if days_remaining <= 3:
                        risks.append(
                            "Upcoming deadline requires monitoring"
                        )
                        recommendations.append(
                            "Check progress and confirm whether the "
                            "remaining work can be completed on time."
                        )

            if risks:
                assessment = "Potential Delivery Risk"
            elif status in pending_statuses:
                assessment = "Monitor Progress"
            else:
                assessment = "Insufficient Status Information"

        forecasts.append({
            "task": task["task"],
            "status": task["status"],
            "due_date": due_date_text,
            "dependency": dependency,
            "assessment": assessment,
            "risk_indicators": risks,
            "recommendations": recommendations
        })

    risk_count = sum(
        1 for item in forecasts
        if item["assessment"] == "Potential Delivery Risk"
    )

    return {
        "success": True,
        "message": "Delivery assessment completed.",
        "reference_date": reference_date.isoformat(),
        "tasks_analyzed": len(forecasts),
        "tasks_with_potential_delivery_risk": risk_count,
        "forecasts": forecasts
    }


if __name__ == "__main__":
    import json

    sample_text = """
    Task: RAG Pipeline | Status: In Progress |
    Due Date: 2026-11-15 | Dependency: API Access Pending

    Task: Document Upload | Status: Completed |
    Due Date: 2026-10-20

    Task: System Testing | Status: Not Started |
    Due Date: 2026-10-30
    """

    result = forecast_delivery(
        sample_text,
        reference_date="2026-10-29"
    )

    print(json.dumps(result, indent=4, ensure_ascii=False))
```
