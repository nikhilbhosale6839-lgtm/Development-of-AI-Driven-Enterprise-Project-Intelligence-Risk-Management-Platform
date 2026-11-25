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
# 2. SENTENCE EXTRACTION
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
        line = line.strip()

        if len(line) >= 4:
            sentences.append(line)

    return sentences


# =========================================================
# 3. SECTION KEYWORDS
# =========================================================

IN_SCOPE_KEYWORDS = [
    "in scope",
    "in-scope",
    "project scope",
    "scope includes",
    "included in scope",
    "will include",
    "project activities",
    "functional requirements",
    "features included"
]

OUT_SCOPE_KEYWORDS = [
    "out of scope",
    "out-of-scope",
    "excluded from scope",
    "not included",
    "outside the scope",
    "scope exclusion",
    "excluded activities",
    "not part of this project"
]

DELIVERABLE_KEYWORDS = [
    "deliverable",
    "deliverables",
    "expected output",
    "project output",
    "final output",
    "will deliver",
    "to be delivered",
    "project outcome",
    "key outputs"
]


# =========================================================
# 4. SECTION DETECTION
# =========================================================

def detect_section_heading(line):

    normalized = clean_text(line).lower()

    normalized = normalized.strip(" :#-*0123456789.")

    if any(
        keyword in normalized
        for keyword in OUT_SCOPE_KEYWORDS
    ):
        return "out_of_scope"

    if any(
        keyword in normalized
        for keyword in DELIVERABLE_KEYWORDS
    ):
        return "deliverables"

    if any(
        keyword in normalized
        for keyword in IN_SCOPE_KEYWORDS
    ):
        return "in_scope"

    return None


# =========================================================
# 5. KEYWORD CHECK
# =========================================================

def contains_keyword(text, keywords):

    text = normalize_text(text)

    return any(
        keyword in text
        for keyword in keywords
    )


def normalize_text(text):

    return clean_text(text).lower()


# =========================================================
# 6. REMOVE UNWANTED SENTENCES
# =========================================================

def is_valid_item(text):

    text = clean_text(text)

    if len(text) < 5:
        return False

    invalid_phrases = [
        "table of contents",
        "page number",
        "confidential",
        "copyright",
        "prepared by",
        "version history",
        "document history"
    ]

    normalized = text.lower()

    if any(
        phrase in normalized
        for phrase in invalid_phrases
    ):
        return False

    return True


# =========================================================
# 7. CLEAN ITEM
# =========================================================

def clean_item(text):

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
# 8. DUPLICATE REMOVAL
# =========================================================

def remove_duplicates(items):

    unique_items = []

    seen = set()

    for item in items:

        cleaned = clean_item(item)

        key = cleaned.lower()

        if not is_valid_item(cleaned):
            continue

        if key not in seen:

            seen.add(key)

            unique_items.append(cleaned)

    return unique_items


# =========================================================
# 9. GENERATE ITEM ID
# =========================================================

def generate_item_id(prefix, index):

    return f"{prefix}-{index:03d}"


# =========================================================
# 10. CREATE STRUCTURED ITEMS
# =========================================================

def create_items(items, prefix):

    result = []

    for index, item in enumerate(items, start=1):

        result.append({

            "id": generate_item_id(
                prefix,
                index
            ),

            "description": item,

            "status": "Identified",

            "source": "Uploaded Document"

        })

    return result


# =========================================================
# 11. EXTRACT SECTION CONTENT
# =========================================================

def extract_by_sections(text):

    lines = clean_text(text).splitlines()

    sections = {

        "in_scope": [],

        "out_of_scope": [],

        "deliverables": []

    }

    current_section = None

    for line in lines:

        line = clean_text(line)

        if not line:
            continue

        detected = detect_section_heading(line)

        if detected:

            current_section = detected

            # Ignore heading itself
            continue

        # Collect only content under a recognized heading
        if current_section:

            if is_valid_item(line):

                sections[current_section].append(
                    clean_item(line)
                )

    return sections


# =========================================================
# 12. EXTRACT KEYWORD-BASED CONTENT
# =========================================================

def extract_by_keywords(text):

    sentences = extract_sentences(text)

    in_scope = []

    out_of_scope = []

    deliverables = []

    for sentence in sentences:

        normalized = sentence.lower()

        if contains_keyword(
            normalized,
            OUT_SCOPE_KEYWORDS
        ):

            out_of_scope.append(sentence)

        elif contains_keyword(
            normalized,
            DELIVERABLE_KEYWORDS
        ):

            deliverables.append(sentence)

        elif contains_keyword(
            normalized,
            IN_SCOPE_KEYWORDS
        ):

            in_scope.append(sentence)

    return {

        "in_scope": in_scope,

        "out_of_scope": out_of_scope,

        "deliverables": deliverables

    }


# =========================================================
# 13. MAIN SCOPE EXTRACTION
# =========================================================

def extract_project_scope(text):

    text = clean_text(text)

    if not text:

        return {

            "success": False,

            "message": "No document text available.",

            "analysis_date": datetime.now().isoformat(),

            "in_scope": [],

            "out_of_scope": [],

            "deliverables": [],

            "total_in_scope": 0,

            "total_out_of_scope": 0,

            "total_deliverables": 0

        }

    # Extract content from recognized sections
    section_data = extract_by_sections(text)

    # Extract content using keywords
    keyword_data = extract_by_keywords(text)

    # Merge section and keyword results
    in_scope = (
        section_data["in_scope"]
        + keyword_data["in_scope"]
    )

    out_of_scope = (
        section_data["out_of_scope"]
        + keyword_data["out_of_scope"]
    )

    deliverables = (
        section_data["deliverables"]
        + keyword_data["deliverables"]
    )

    # Remove duplicates
    in_scope = remove_duplicates(in_scope)

    out_of_scope = remove_duplicates(out_of_scope)

    deliverables = remove_duplicates(deliverables)

    # Do not invent out-of-scope information
    if not out_of_scope:

        out_of_scope_display = [
            {
                "id": "OOS-000",
                "description": "Not Specified in Document",
                "status": "Not Specified",
                "source": "Uploaded Document"
            }
        ]

    else:

        out_of_scope_display = create_items(
            out_of_scope,
            "OOS"
        )

    in_scope_items = create_items(
        in_scope,
        "INS"
    )

    deliverable_items = create_items(
        deliverables,
        "DEL"
    )

    return {

        "success": True,

        "message": "Project scope extraction completed.",

        "analysis_date": datetime.now().isoformat(),

        "in_scope": in_scope_items,

        "out_of_scope": out_of_scope_display,

        "deliverables": deliverable_items,

        "total_in_scope": len(in_scope_items),

        "total_out_of_scope": (
            len(out_of_scope)
        ),

        "total_deliverables": len(deliverable_items),

        "source": "Uploaded Documents"

    }


# =========================================================
# 14. ALTERNATIVE FUNCTION
# =========================================================

def analyze_scope(text):

    return extract_project_scope(text)


def extract_scope(text):

    return extract_project_scope(text)


def analyze_project_scope(text):

    return extract_project_scope(text)


# =========================================================
# 15. TEST
# =========================================================

if __name__ == "__main__":

    sample_text = """

    PROJECT SCOPE

    In Scope:
    - Develop project dashboard
    - Upload project documents
    - Identify project risks
    - Generate project reports

    Out of Scope:
    - Mobile application development
    - Third party payment integration

    Deliverables:
    - Project Risk Advisor Dashboard
    - Risk Analysis Report
    - Project Documentation
    - Final Project Report

    """

    result = extract_project_scope(
        sample_text
    )

    import json

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
