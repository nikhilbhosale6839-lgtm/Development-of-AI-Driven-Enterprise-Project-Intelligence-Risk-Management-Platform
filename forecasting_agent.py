import re
import csv
import io
from datetime import datetime, date


# =========================================================
# 1. TEXT CLEANING
# =========================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)
    text = text.replace("\x00", " ")
    text = text.replace("\ufeff", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================================================
# 2. HEADER NORMALIZATION
# =========================================================

def normalize_header(header):

    header = clean_text(header).lower()

    header = re.sub(r"[^a-z0-9]+", "_", header)

    return header.strip("_")


# =========================================================
# 3. DATE PARSING
# =========================================================

def parse_date(value):

    if not value:
        return None

    value = clean_text(value)

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%b %d, %Y",
        "%B %d, %Y"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(value, fmt).date()

        except ValueError:
            continue

    return None


# =========================================================
# 4. PROGRESS EXTRACTION
# =========================================================

def extract_progress(value):

    if value is None:
        return None

    value = clean_text(value)

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)

    if match:
        return max(0, min(100, float(match.group(1))))

    try:
        number = float(value)

        if 0 <= number <= 100:
            return number

    except ValueError:
        pass

    return None


# =========================================================
# 5. STATUS NORMALIZATION
# =========================================================

def normalize_status(status, progress=None):

    status = clean_text(status).lower()

    if any(word in status for word in [
        "complete", "completed", "done", "closed"
    ]):
        return "Completed"

    if any(word in status for word in [
        "block", "blocked", "impediment"
    ]):
        return "Blocked"

    if any(word in status for word in [
        "progress", "ongoing", "working", "started"
    ]):
        return "In Progress"

    if any(word in status for word in [
        "delay", "delayed", "overdue"
    ]):
        return "Delayed"

    if any(word in status for word in [
        "pending", "not started", "todo", "to do"
    ]):
        return "Pending"

    if progress is not None:

        if progress >= 100:
            return "Completed"

        if progress > 0:
            return "In Progress"

    return "Pending"


# =========================================================
# 6. RECORD VALUE HELPER
# =========================================================

def get_record_value(record, possible_keys):

    if not isinstance(record, dict):
        return ""

    normalized_record = {
        normalize_header(key): value
        for key, value in record.items()
    }

    for key in possible_keys:

        normalized_key = normalize_header(key)

        if normalized_key in normalized_record:

            value = normalized_record[normalized_key]

            if value is not None:
                return value

    return ""


# =========================================================
# 7. TASK NORMALIZATION
# =========================================================

def normalize_task(record, index):

    if isinstance(record, str):

        record = {
            "task": record
        }

    task_name = get_record_value(
        record,
        [
            "task",
            "task_name",
            "task_description",
            "description",
            "activity",
            "title",
            "task_description_name"
        ]
    )

    if not task_name:
        return None

    task_name = clean_text(task_name)

    owner = get_record_value(
        record,
        [
            "owner",
            "assignee",
            "assigned_to",
            "team_member",
            "responsible_person"
        ]
    )

    start_date = get_record_value(
        record,
        [
            "start_date",
            "task_start_date",
            "planned_start_date"
        ]
    )

    due_date = get_record_value(
        record,
        [
            "due_date",
            "completion_date",
            "end_date",
            "task_completion_date",
            "target_date",
            "deadline"
        ]
    )

    status_value = get_record_value(
        record,
        [
            "status",
            "task_status"
        ]
    )

    progress_value = get_record_value(
        record,
        [
            "progress",
            "completion",
            "completion_percentage",
            "percent_complete"
        ]
    )

    priority = get_record_value(
        record,
        [
            "priority",
            "importance"
        ]
    )

    progress = extract_progress(progress_value)

    status = normalize_status(status_value, progress)

    if progress is None:

        progress_map = {
            "Completed": 100,
            "In Progress": 50,
            "Blocked": 0,
            "Delayed": 25,
            "Pending": 0
        }

        progress = progress_map.get(status, 0)

    progress = max(0, min(100, float(progress)))

    parsed_start = parse_date(start_date)
    parsed_due = parse_date(due_date)

    today = date.today()

    overdue = False

    if parsed_due and parsed_due < today and status != "Completed":
        overdue = True

        if status != "Blocked":
            status = "Delayed"

    if status == "Completed":
        progress = 100

    return {
        "task_id": f"TASK-{index:03d}",
        "task": task_name,
        "task_name": task_name,
        "owner": clean_text(owner) or "Not Assigned",
        "start_date": parsed_start.isoformat() if parsed_start else clean_text(start_date),
        "due_date": parsed_due.isoformat() if parsed_due else clean_text(due_date),
        "status": status,
        "progress": round(progress, 2),
        "priority": clean_text(priority).title() or "Medium",
        "overdue": overdue
    }


# =========================================================
# 8. MARKDOWN TABLE PARSER
# =========================================================

def parse_markdown_table(text):

    records = []

    lines = clean_text(text).splitlines()

    table_lines = [
        line.strip()
        for line in lines
        if "|" in line
    ]

    if len(table_lines) < 2:
        return records

    headers = [
        normalize_header(item)
        for item in table_lines[0].strip("|").split("|")
    ]

    for line in table_lines[1:]:

        if re.match(r"^\|?\s*:?-{2,}", line):
            continue

        values = [
            clean_text(item)
            for item in line.strip("|").split("|")
        ]

        if len(values) != len(headers):
            continue

        record = dict(zip(headers, values))

        records.append(record)

    return records


# =========================================================
# 9. CSV PARSER
# =========================================================

def parse_csv_records(text):

    records = []

    try:

        reader = csv.DictReader(io.StringIO(text))

        for row in reader:

            if row:
                records.append(row)

    except Exception:
        return []

    return records


# =========================================================
# 10. TEXT RECORD PARSER
# =========================================================

def parse_text_records(text):

    records = []

    lines = clean_text(text).splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^\s*(?:[-*•]|\d+[.)])\s*(.+)$",
            line
        )

        if match:
            line = match.group(1)

        records.append({
            "task": line
        })

    return records


# =========================================================
# 11. TASK EXTRACTION
# =========================================================

def extract_tasks(text):

    text = clean_text(text)

    if not text:
        return []

    records = []

    if "|" in text:

        records = parse_markdown_table(text)

    if not records and "," in text:

        records = parse_csv_records(text)

    if not records:

        records = parse_text_records(text)

    tasks = []

    for index, record in enumerate(records, start=1):

        task = normalize_task(record, index)

        if task:
            tasks.append(task)

    return tasks


# =========================================================
# 12. REMOVE DUPLICATE TASKS
# =========================================================

def remove_duplicate_tasks(tasks):

    unique_tasks = []

    seen = set()

    for task in tasks:

        key = re.sub(
            r"[^a-z0-9]+",
            "",
            task["task"].lower()
        )

        if key and key not in seen:

            seen.add(key)

            unique_tasks.append(task)

    return unique_tasks


# =========================================================
# 13. COMPLETION CALCULATION
# =========================================================

def calculate_completion(tasks):

    if not tasks:
        return 0

    total_progress = sum(
        task["progress"]
        for task in tasks
    )

    return round(total_progress / len(tasks), 2)


# =========================================================
# 14. TASK COUNTS
# =========================================================

def calculate_task_counts(tasks):

    counts = {
        "total": len(tasks),
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "blocked": 0,
        "delayed": 0,
        "overdue": 0
    }

    for task in tasks:

        status = task["status"]

        if status == "Completed":
            counts["completed"] += 1

        elif status == "In Progress":
            counts["in_progress"] += 1

        elif status == "Blocked":
            counts["blocked"] += 1

        elif status == "Delayed":
            counts["delayed"] += 1

        else:
            counts["pending"] += 1

        if task["overdue"]:
            counts["overdue"] += 1

    return counts


# =========================================================
# 15. DELAY PROBABILITY
# =========================================================

def calculate_delay_probability(tasks):

    if not tasks:
        return 0

    counts = calculate_task_counts(tasks)

    total = counts["total"]

    blocked_ratio = counts["blocked"] / total
    overdue_ratio = counts["overdue"] / total
    pending_ratio = counts["pending"] / total
    progress_ratio = counts["in_progress"] / total

    probability = (
        blocked_ratio * 40 +
        overdue_ratio * 35 +
        pending_ratio * 15 +
        progress_ratio * 5
    )

    return round(min(100, probability), 2)


# =========================================================
# 16. DELIVERY STATUS
# =========================================================

def calculate_delivery_status(
    completion,
    delay_probability,
    counts
):

    if counts["total"] == 0:
        return "No Data"

    if counts["blocked"] > 0 or delay_probability >= 70:
        return "At Risk"

    if counts["overdue"] > 0 or delay_probability >= 40:
        return "Delayed"

    if completion >= 100:
        return "Completed"

    return "On Track"


# =========================================================
# 17. REMAINING DAYS
# =========================================================

def calculate_remaining_days(tasks):

    today = date.today()

    due_dates = []

    for task in tasks:

        parsed_due = parse_date(task["due_date"])

        if parsed_due and task["status"] != "Completed":
            due_dates.append(parsed_due)

    if not due_dates:
        return None

    latest_due_date = max(due_dates)

    return (latest_due_date - today).days


# =========================================================
# 18. PUBLIC TASK DATA
# =========================================================

def prepare_public_tasks(tasks):

    public_tasks = []

    for task in tasks:

        item = dict(task)

        due = parse_date(item["due_date"])

        item["remaining_days"] = (
            (due - date.today()).days
            if due else None
        )

        public_tasks.append(item)

    return public_tasks


# =========================================================
# 19. MAIN FORECAST FUNCTION
# =========================================================

def forecast_delivery(text):

    try:

        text = clean_text(text)

        if not text:

            return {
                "success": False,
                "message": "No project task data provided.",
                "completion_percentage": 0,
                "delay_probability": 0,
                "remaining_days": None,
                "delivery_status": "No Data",
                "task_counts": calculate_task_counts([]),
                "tasks": []
            }

        tasks = extract_tasks(text)

        tasks = remove_duplicate_tasks(tasks)

        counts = calculate_task_counts(tasks)

        completion = calculate_completion(tasks)

        delay_probability = calculate_delay_probability(tasks)

        remaining_days = calculate_remaining_days(tasks)

        delivery_status = calculate_delivery_status(
            completion,
            delay_probability,
            counts
        )

        public_tasks = prepare_public_tasks(tasks)

        return {
            "success": True,
            "message": "Project delivery forecast generated successfully.",
            "analysis_date": datetime.now().isoformat(timespec="seconds"),
            "completion_percentage": completion,
            "delay_probability": delay_probability,
            "remaining_days": remaining_days,
            "delivery_status": delivery_status,
            "task_counts": counts,
            "total_tasks": counts["total"],
            "completed_tasks": counts["completed"],
            "in_progress_tasks": counts["in_progress"],
            "pending_tasks": counts["pending"],
            "blocked_tasks": counts["blocked"],
            "delayed_tasks": counts["delayed"],
            "overdue_tasks": counts["overdue"],
            "tasks": public_tasks
        }

    except Exception as error:

        return {
            "success": False,
            "message": f"Forecasting failed: {str(error)}",
            "completion_percentage": 0,
            "delay_probability": 0,
            "remaining_days": None,
            "delivery_status": "Error",
            "task_counts": calculate_task_counts([]),
            "tasks": []
        }


# =========================================================
# 20. TESTING
# =========================================================

if __name__ == "__main__":

    sample_text = """
    | Task ID | Task Description | Owner | Start Date | Due Date | Status | Progress |
    |---------|------------------|-------|------------|----------|--------|----------|
    | 1 | Requirement Analysis | Rahul | 2026-11-01 | 2026-11-05 | Completed | 100% |
    | 2 | Design Dashboard | Priya | 2026-11-05 | 2026-11-15 | In Progress | 60% |
    | 3 | Backend Development | Amit | 2026-11-10 | 2026-11-30 | Pending | 0% |
    """

    result = forecast_delivery(sample_text)

    import json

    print(json.dumps(result, indent=4))
