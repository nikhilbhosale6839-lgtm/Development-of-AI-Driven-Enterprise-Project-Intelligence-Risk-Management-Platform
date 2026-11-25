import re
import hashlib
from datetime import datetime


# =========================================================
# 1. ACTION KEYWORDS
# =========================================================

ACTION_KEYWORDS = [
    "will",
    "must",
    "should",
    "need to",
    "needs to",
    "required to",
    "responsible for",
    "assigned to",
    "complete",
    "develop",
    "implement",
    "prepare",
    "review",
    "test",
    "deploy",
    "configure",
    "resolve",
    "fix",
    "create",
    "update",
    "submit",
    "validate",
    "monitor",
    "coordinate",
    "investigate",
    "document",
    "deliver",
    "analyze",
    "design",
    "verify"
]


# =========================================================
# 2. PRIORITY KEYWORDS
# =========================================================

HIGH_PRIORITY_WORDS = [
    "critical",
    "urgent",
    "immediately",
    "high priority",
    "asap",
    "blocker"
]

MEDIUM_PRIORITY_WORDS = [
    "medium priority",
    "important",
    "should complete",
    "required"
]


# =========================================================
# 3. STATUS KEYWORDS
# =========================================================

STATUS_KEYWORDS = {
    "Completed": [
        "completed",
        "finished",
        "done",
        "closed",
        "resolved",
        "delivered"
    ],

    "In Progress": [
        "in progress",
        "ongoing",
        "working on",
        "started",
        "currently developing",
        "under development"
    ],

    "Blocked": [
        "blocked",
        "on hold",
        "unable to proceed",
        "waiting for"
    ],

    "Pending": [
        "pending",
        "not started",
        "yet to start",
        "planned"
    ]
}


# =========================================================
# 4. TEXT CLEANING
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
# 5. SENTENCE EXTRACTION
# =========================================================

def extract_sentences(text):

    text = clean_text(text)

    if not text:
        return []

    lines = re.split(
        r"\n+|(?<=[.!?])\s+",
        text
    )

    return [
        line.strip()
        for line in lines
        if len(line.strip()) >= 8
    ]


# =========================================================
# 6. ACTION VALIDATION
# =========================================================

def is_action_item(sentence):

    sentence_lower = sentence.lower()

    if sentence.endswith(":") and len(sentence.split()) <= 8:
        return False

    return any(
        keyword in sentence_lower
        for keyword in ACTION_KEYWORDS
    )


# =========================================================
# 7. ACTION DESCRIPTION CLEANING
# =========================================================

def clean_action_description(sentence):

    sentence = clean_text(sentence)

    sentence = re.sub(
        r"^(?:[-*•]|\d+[.)])\s*",
        "",
        sentence
    )

    sentence = re.sub(
        r"^(?:action item|task|action)\s*[:=-]\s*",
        "",
        sentence,
        flags=re.IGNORECASE
    )

    return sentence.strip()


# =========================================================
# 8. OWNER EXTRACTION
# =========================================================

def extract_owner(sentence):

    patterns = [
        r"(?:owner|assigned to|assignee|responsible)\s*[:=-]\s*([A-Za-z][A-Za-z ._-]{1,40})",
        r"(?:owned by|handled by|assigned to)\s+([A-Za-z][A-Za-z ._-]{1,40})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            sentence,
            re.IGNORECASE
        )

        if match:

            owner = match.group(1).strip()

            owner = re.split(
                r"\b(?:by|before|due|deadline|status|priority)\b",
                owner,
                flags=re.IGNORECASE
            )[0].strip()

            return owner[:60]

    return "Unassigned"


# =========================================================
# 9. DATE EXTRACTION
# =========================================================

def extract_due_date(sentence):

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(?:due date|deadline|due by|complete by)\s*[:=-]?\s*([A-Za-z0-9 ,/-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            sentence,
            re.IGNORECASE
        )

        if not match:
            continue

        date_value = (
            match.group(1)
            if match.lastindex
            else match.group(0)
        ).strip()

        date_value = date_value.rstrip(".,;")

        date_value = re.split(
            r"\b(?:status|owner|priority)\b",
            date_value,
            flags=re.IGNORECASE
        )[0].strip()

        return date_value[:50]

    return "Not Specified"


# =========================================================
# 10. STATUS EXTRACTION
# =========================================================

def extract_status(sentence):

    sentence_lower = sentence.lower()

    for status, keywords in STATUS_KEYWORDS.items():

        for keyword in keywords:

            if keyword in sentence_lower:
                return status

    return "Pending"


# =========================================================
# 11. PRIORITY EXTRACTION
# =========================================================

def extract_priority(sentence):

    sentence_lower = sentence.lower()

    for keyword in HIGH_PRIORITY_WORDS:

        if keyword in sentence_lower:
            return "High"

    for keyword in MEDIUM_PRIORITY_WORDS:

        if keyword in sentence_lower:
            return "Medium"

    return "Low"


# =========================================================
# 12. ACTION ID GENERATION
# =========================================================

def generate_action_id(sentence):

    digest = hashlib.md5(
        sentence.lower().encode("utf-8")
    ).hexdigest()[:8].upper()

    return "ACT-" + digest


# =========================================================
# 13. STRUCTURED RECORD EXTRACTION
# =========================================================

def prepare_records(text):

    records = []

    lines = clean_text(text).splitlines()

    current_record = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^(?:action item|task|action)\s*[:=-]\s*(.+)$",
            line,
            re.IGNORECASE
        )

        if match:

            if current_record:
                records.append(current_record)

            current_record = {
                "action_item": match.group(1).strip(),
                "owner": "Unassigned",
                "due_date": "Not Specified",
                "status": "Pending",
                "priority": "Low",
                "source_text": line
            }

            continue

        field_match = re.match(
            r"^(owner|assigned to|assignee|responsible|due date|deadline|due by|status|priority)\s*[:=-]\s*(.+)$",
            line,
            re.IGNORECASE
        )

        if field_match and current_record:

            field = field_match.group(1).lower()
            value = field_match.group(2).strip()

            if field in [
                "owner",
                "assigned to",
                "assignee",
                "responsible"
            ]:
                current_record["owner"] = value

            elif field in [
                "due date",
                "deadline",
                "due by"
            ]:
                current_record["due_date"] = value

            elif field == "status":
                current_record["status"] = value

            elif field == "priority":
                current_record["priority"] = value

            current_record["source_text"] += " | " + line

            continue

        if current_record:
            current_record["source_text"] += " " + line

    if current_record:
        records.append(current_record)

    return records


# =========================================================
# 14. DUPLICATE REMOVAL
# =========================================================

def remove_duplicate_actions(actions):

    unique_actions = {}

    for action in actions:

        key = re.sub(
            r"[^a-z0-9]",
            "",
            action["action_item"].lower()
        )

        if key and key not in unique_actions:
            unique_actions[key] = action

    return list(unique_actions.values())


# =========================================================
# 15. NORMALIZE STATUS AND PRIORITY
# =========================================================

def normalize_status(value):

    value = str(value).strip().lower()

    mapping = {
        "done": "Completed",
        "finished": "Completed",
        "closed": "Completed",
        "resolved": "Completed",
        "completed": "Completed",
        "in progress": "In Progress",
        "ongoing": "In Progress",
        "started": "In Progress",
        "blocked": "Blocked",
        "on hold": "Blocked",
        "pending": "Pending",
        "planned": "Pending",
        "not started": "Pending"
    }

    return mapping.get(value, "Pending")


def normalize_priority(value):

    value = str(value).strip().lower()

    if value in ["high", "critical", "urgent"]:
        return "High"

    if value in ["medium", "important"]:
        return "Medium"

    return "Low"


# =========================================================
# 16. MAIN ACTION ITEM IDENTIFICATION
# =========================================================

def identify_action_items(text):

    text = clean_text(text)

    if not text:

        return {
            "success": True,
            "message": "No document text available.",
            "total_action_items": 0,
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "blocked": 0,
            "high_priority": 0,
            "action_items": []
        }

    action_items = []

    # -----------------------------------------------------
    # A. STRUCTURED ACTION EXTRACTION
    # -----------------------------------------------------

    structured_records = prepare_records(text)

    for record in structured_records:

        description = clean_action_description(
            record["action_item"]
        )

        if not description:
            continue

        action_items.append({

            "action_id": generate_action_id(description),

            "action_item": description,

            "owner": record["owner"],

            "due_date": record["due_date"],

            "status": normalize_status(record["status"]),

            "priority": normalize_priority(record["priority"]),

            "source_text": record["source_text"]

        })

    # -----------------------------------------------------
    # B. NORMAL SENTENCE EXTRACTION
    # -----------------------------------------------------

    sentences = extract_sentences(text)

    for sentence in sentences:

        if not is_action_item(sentence):
            continue

        description = clean_action_description(sentence)

        if not description:
            continue

        action_items.append({

            "action_id": generate_action_id(description),

            "action_item": description,

            "owner": extract_owner(sentence),

            "due_date": extract_due_date(sentence),

            "status": extract_status(sentence),

            "priority": extract_priority(sentence),

            "source_text": sentence

        })

    # -----------------------------------------------------
    # C. DUPLICATE REMOVAL
    # -----------------------------------------------------

    action_items = remove_duplicate_actions(action_items)

    # -----------------------------------------------------
    # D. SUMMARY CALCULATION
    # -----------------------------------------------------

    total = len(action_items)

    completed = sum(
        1 for item in action_items
        if item["status"] == "Completed"
    )

    in_progress = sum(
        1 for item in action_items
        if item["status"] == "In Progress"
    )

    pending = sum(
        1 for item in action_items
        if item["status"] == "Pending"
    )

    blocked = sum(
        1 for item in action_items
        if item["status"] == "Blocked"
    )

    high_priority = sum(
        1 for item in action_items
        if item["priority"] == "High"
    )

    # -----------------------------------------------------
    # E. FINAL RESPONSE
    # -----------------------------------------------------

    return {

        "success": True,

        "message": (
            f"{total} action item(s) identified successfully."
            if total > 0
            else "No action items identified."
        ),

        "analysis_date": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "total_action_items": total,

        "completed": completed,

        "in_progress": in_progress,

        "pending": pending,

        "blocked": blocked,

        "high_priority": high_priority,

        "action_items": action_items,

        "source": "Rule-Based Action Item Extraction"

    }


# =========================================================
# 17. COMPATIBILITY FUNCTION
# =========================================================

def analyze_action_items(text):

    return identify_action_items(text)


# =========================================================
# 18. TESTING
# =========================================================

if __name__ == "__main__":

    import json

    sample_text = """
    PROJECT ALPHA - ACTION ITEMS

    Action: Complete requirement analysis
    Owner: Rahul
    Due Date: 2026-11-25
    Status: In Progress
    Priority: High

    Action: Prepare project documentation
    Owner: Priya
    Due Date: 2026-11-28
    Status: Pending
    Priority: Medium

    The development team must complete API integration.
    The testing team will validate all modules.
    The project manager should review the final report.
    """

    result = identify_action_items(sample_text)

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
