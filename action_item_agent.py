```python
import re


def identify_action_items(document_text):
    """
    Action Item Identification Agent.

    Extracts action-oriented lines and attempts to identify
    owner, due date, and status.

    Supports simple formats such as:
    Nikhil will complete the RAG pipeline by 25 October 2026.
    Owner: Nikhil | Action: Prepare test cases |
    Due Date: 2026-10-25 | Status: Pending
    """

    if not document_text or not document_text.strip():
        return {
            "success": False,
            "message": "No document text provided.",
            "total_action_items": 0,
            "action_items": []
        }

    action_items = []
    seen = set()

    # Phrases indicating a task or action.
    action_patterns = [
        r"\bwill\b",
        r"\bmust\b",
        r"\bneed to\b",
        r"\bneeds to\b",
        r"\bshould\b",
        r"\baction item\b",
        r"\baction required\b",
        r"\bassigned to\b",
        r"\bfollow up\b",
        r"\bcomplete\b",
        r"\bprepare\b",
        r"\breview\b",
        r"\bresolve\b",
        r"\bupdate\b",
        r"\bsubmit\b",
        r"\bimplement\b",
        r"\btest\b",
        r"\binvestigate\b",
        r"\bdeliver\b",
        r"\bconfirm\b"
    ]

    # Common date formats.
    date_pattern = (
        r"\b(?:"
        r"\d{4}-\d{2}-\d{2}"
        r"|\d{1,2}[/-]\d{1,2}[/-]\d{4}"
        r"|\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}"
        r"|(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}"
        r")\b"
    )

    for line in document_text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Support structured task records.
        if "|" in line and re.search(
            r"\b(?:Action|Task)\s*:",
            line,
            re.IGNORECASE
        ):
            structured = re.search(
                r"\b(?:Action|Task)\s*:\s*([^|]+)",
                line,
                re.IGNORECASE
            )

            if structured:
                description = structured.group(1).strip()
            else:
                description = line
        else:
            description = line

        is_action = any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in action_patterns
        )

        # Structured records with an explicit task label are actions.
        if re.search(
            r"\b(?:Action|Task)\s*:",
            line,
            re.IGNORECASE
        ):
            is_action = True

        if not is_action:
            continue

        owner = None
        due_date = None
        status = "Not Specified"

        # Extract owner from structured fields.
        owner_match = re.search(
            r"\b(?:Owner|Assigned To|Assignee|Responsible)\s*:\s*"
            r"([^|,;]+)",
            line,
            re.IGNORECASE
        )

        if owner_match:
            owner = owner_match.group(1).strip()

        # Extract owner from simple natural-language sentences.
        if not owner:
            owner_match = re.search(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
                r"\s+will\b",
                line
            )

            if owner_match:
                owner = owner_match.group(1).strip()

        # Extract due date from labeled fields first.
        due_match = re.search(
            r"\b(?:Due Date|Deadline|Due By)\s*:\s*"
            r"([^|,;]+)",
            line,
            re.IGNORECASE
        )

        if due_match:
            due_date = due_match.group(1).strip()
        else:
            date_match = re.search(date_pattern, line, re.IGNORECASE)

            if date_match:
                due_date = date_match.group(0).strip()

        status_match = re.search(
            r"\bStatus\s*:\s*([^|,;]+)",
            line,
            re.IGNORECASE
        )

        if status_match:
            status = status_match.group(1).strip()

        elif re.search(r"\b(completed|done|closed)\b", line, re.I):
            status = "Completed"

        elif re.search(r"\b(blocked|delayed|overdue)\b", line, re.I):
            status = "Needs Review"

        elif re.search(r"\b(pending|not started)\b", line, re.I):
            status = "Pending"

        elif re.search(r"\bin progress\b", line, re.I):
            status = "In Progress"

        key = (description, owner, due_date)

        if key in seen:
            continue

        action_items.append({
            "action_item": description,
            "owner": owner,
            "due_date": due_date,
            "status": status,
            "source_text": line
        })

        seen.add(key)

    return {
        "success": True,
        "message": (
            "Action item extraction completed."
            if action_items
            else "No action items were identified using the configured rules."
        ),
        "total_action_items": len(action_items),
        "action_items": action_items
    }


if __name__ == "__main__":
    import json

    sample_text = """
    Meeting Date: 20 October 2026

    Nikhil will complete the RAG pipeline by 25 October 2026.
    Keshav will prepare the test cases by 22 October 2026.
    The team must resolve the API access issue.
    Owner: Priya | Action: Review dashboard |
    Due Date: 2026-10-28 | Status: Pending
    """

    result = identify_action_items(sample_text)

    print(json.dumps(result, indent=4, ensure_ascii=False))
```

