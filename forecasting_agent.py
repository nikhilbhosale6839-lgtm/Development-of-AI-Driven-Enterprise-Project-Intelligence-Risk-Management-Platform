from datetime import date


def forecast_task(
    start_date,
    due_date,
    progress_percent
):
    """
    Basic task schedule analysis.

    Dates must use YYYY-MM-DD format.
    Progress must be between 0 and 100.
    """

    start = date.fromisoformat(start_date)
    due = date.fromisoformat(due_date)
    today = date.today()

    progress = float(progress_percent)

    if not 0 <= progress <= 100:
        raise ValueError(
            "Progress must be between 0 and 100."
        )

    if due < start:
        raise ValueError(
            "Due date cannot be before start date."
        )

    if progress >= 100:
        status = "Completed"
    elif today > due:
        status = "Overdue"
    elif today >= start and progress == 0:
        status = "Not Started"
    else:
        status = "In Progress"

    return {
        "start_date": start.isoformat(),
        "due_date": due.isoformat(),
        "progress_percent": progress,
        "status": status,
        "days_until_deadline": (due - today).days,
        "note": (
            "This is a basic schedule assessment, "
            "not a validated delivery prediction."
        )
    }
