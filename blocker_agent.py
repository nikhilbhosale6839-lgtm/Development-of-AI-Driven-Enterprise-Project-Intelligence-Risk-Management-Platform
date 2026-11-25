import re
from datetime import datetime


# =========================================================
# 1. TEXT CLEANING
# =========================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")
    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================================================
# 2. EXTRACT SENTENCES
# =========================================================

def extract_sentences(text):

    text = clean_text(text)

    if not text:
        return []

    lines = re.split(r"[\n]+", text)

    sentences = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        line = re.sub(r"^[\d.\-*•▪]+\s*", "", line)

        if len(line) >= 5:
            sentences.append(line)

    return sentences


# =========================================================
# 3. BLOCKER KEYWORDS
# =========================================================

BLOCKER_KEYWORDS = [

    "blocked",
    "blocker",
    "blocked by",
    "blocking",
    "cannot proceed",
    "unable to proceed",
    "waiting for",
    "pending approval",
    "dependency issue",
    "access denied",
    "access issue",
    "resource unavailable",
    "resource shortage",
    "environment issue",
    "technical issue",
    "integration issue",
    "deployment issue",
    "server unavailable",
    "delayed due to",
    "dependency pending",
    "on hold",
    "not available",
    "issue preventing",
    "impediment"

]


# =========================================================
# 4. PRIORITY DETECTION
# =========================================================

def extract_priority(text):

    text = clean_text(text).lower()

    if any(word in text for word in [
        "critical",
        "urgent",
        "severe",
        "production down"
    ]):

        return "Critical"

    if any(word in text for word in [
        "high",
        "major",
        "immediately"
    ]):

        return "High"

    if any(word in text for word in [
        "low",
        "minor"
    ]):

        return "Low"

    return "Medium"


# =========================================================
# 5. STATUS DETECTION
# =========================================================

def extract_status(text):

    text = clean_text(text).lower()

    if any(word in text for word in [
        "resolved",
        "fixed",
        "completed",
        "closed"
    ]):

        return "Resolved"

    if any(word in text for word in [
        "in progress",
        "working on",
        "being addressed"
    ]):

        return "In Progress"

    if any(word in text for word in [
        "on hold",
        "waiting",
        "pending"
    ]):

        return "Pending"

    return "Open"


# =========================================================
# 6. OWNER EXTRACTION
# =========================================================

def extract_owner(text):

    patterns = [

        r"(?:owner|assigned to|assignee|responsible)\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{1,40})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

    return "Not Assigned"


# =========================================================
# 7. DATE EXTRACTION
# =========================================================

def extract_date(text):

    patterns = [

        r"\b\d{4}-\d{2}-\d{2}\b",

        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",

        r"\b\d{1,2}\s+"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[a-z]*\s+\d{4}\b"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0)

    return "Not Specified"


# =========================================================
# 8. BLOCKER VALIDATION
# =========================================================

def is_blocker(sentence):

    normalized = sentence.lower()

    return any(
        keyword in normalized
        for keyword in BLOCKER_KEYWORDS
    )


# =========================================================
# 9. CLEAN DESCRIPTION
# =========================================================

def clean_description(text):

    text = clean_text(text)

    text = re.sub(
        r"^[\d.\-*•▪]+\s*",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip(" -:;,.•")


# =========================================================
# 10. DUPLICATE REMOVAL
# =========================================================

def remove_duplicates(blockers):

    unique = []

    seen = set()

    for blocker in blockers:

        description = blocker["description"]

        key = description.lower()

        if key not in seen:

            seen.add(key)

            unique.append(blocker)

    return unique


# =========================================================
# 11. CREATE BLOCKER RECORD
# =========================================================

def create_blocker(sentence, index):

    description = clean_description(sentence)

    return {

        "id": f"BLK-{index:03d}",

        "title": description[:100],

        "description": description,

        "priority": extract_priority(description),

        "severity": extract_priority(description),

        "status": extract_status(description),

        "owner": extract_owner(description),

        "due_date": extract_date(description),

        "source": "Uploaded Document",

        "created_at": datetime.now().isoformat()

    }


# =========================================================
# 12. MAIN BLOCKER IDENTIFICATION
# =========================================================

def identify_blockers(text):

    text = clean_text(text)

    if not text:

        return {

            "success": False,

            "message": "No document text available.",

            "blockers": [],

            "total_blockers": 0,

            "analysis_date": datetime.now().isoformat()

        }

    sentences = extract_sentences(text)

    blockers = []

    for sentence in sentences:

        if is_blocker(sentence):

            blockers.append(
                create_blocker(
                    sentence,
                    len(blockers) + 1
                )
            )

    blockers = remove_duplicates(blockers)

    # Reassign IDs after duplicate removal
    for index, blocker in enumerate(blockers, start=1):

        blocker["id"] = f"BLK-{index:03d}"

    return {

        "success": True,

        "message": "Blocker identification completed.",

        "blockers": blockers,

        "total_blockers": len(blockers),

        "open_blockers": sum(
            1 for item in blockers
            if item["status"] == "Open"
        ),

        "resolved_blockers": sum(
            1 for item in blockers
            if item["status"] == "Resolved"
        ),

        "analysis_date": datetime.now().isoformat()

    }


# =========================================================
# 13. APP.PY COMPATIBILITY FUNCTION
# =========================================================

def detect_blockers(text):

    return identify_blockers(text)


def analyze_blockers(text):

    return identify_blockers(text)


# =========================================================
# 14. TEST
# =========================================================

if __name__ == "__main__":

    sample_text = """

    Project Blocker Report

    1. Development is blocked by pending API approval.
    2. Testing cannot proceed because server is unavailable.
    3. Database integration issue is waiting for resolution.
    4. UI development completed successfully.

    """

    result = identify_blockers(sample_text)

    import json

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
