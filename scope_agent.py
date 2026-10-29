```python
import re
from datetime import datetime


def clean_text(text):
    """Remove extra spaces and normalize document text."""

    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_section(text, keywords):
    """
    Extract lines or paragraphs containing relevant keywords.
    """

    results = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        for keyword in keywords:
            if re.search(
                rf"\b{re.escape(keyword)}\b",
                line,
                re.IGNORECASE
            ):
                if line not in results:
                    results.append(line)
                break

    return results


def extract_project_name(text):
    """Extract project name from common project title labels."""

    patterns = [
        r"(?im)^\s*project\s*name\s*[:\-]\s*(.+)$",
        r"(?im)^\s*project\s*title\s*[:\-]\s*(.+)$",
        r"(?im)^\s*title\s*[:\-]\s*(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1).strip()

    # Use a document heading only if a labeled title is unavailable.
    for line in text.splitlines():
        line = line.strip()

        if line.startswith("#"):
            title = line.lstrip("#").strip()

            if title:
                return title

    return "Not explicitly mentioned"


def extract_dates(text):
    """Extract common date formats without inventing dates."""

    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b",
    ]

    dates = []

    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(0).strip()

            if value not in dates:
                dates.append(value)

    return dates


def extract_scope(document_text):
    """
    Scope and Deliverable Extraction Agent.

    Input:
        document_text: Text extracted from uploaded documents.

    Output:
        Dictionary containing project scope information.
    """

    text = clean_text(document_text)

    if not text:
        return {
            "success": False,
            "message": "No document text was provided.",
            "project_name": None,
            "goals": [],
            "requirements": [],
            "milestones": [],
            "deliverables": [],
            "responsibilities": [],
            "deadlines": [],
            "source": "No text available"
        }

    goals = extract_section(
        text,
        [
            "objective",
            "objectives",
            "goal",
            "goals",
            "aim",
            "purpose"
        ]
    )

    requirements = extract_section(
        text,
        [
            "requirement",
            "requirements",
            "functional requirement",
            "non-functional requirement"
        ]
    )

    milestones = extract_section(
        text,
        [
            "milestone",
            "sprint",
            "phase"
        ]
    )

    deliverables = extract_section(
        text,
        [
            "deliverable",
            "deliverables",
            "output",
            "outputs"
        ]
    )

    responsibilities = extract_section(
        text,
        [
            "assigned to",
            "owner",
            "responsible",
            "responsibility",
            "team member",
            "assignee"
        ]
    )

    deadlines = extract_section(
        text,
        [
            "deadline",
            "due date",
            "target date",
            "completion date",
            "end date",
            "delivery date"
        ]
    )

    extracted_dates = extract_dates(text)

    # Include explicit dates found in the document.
    for date in extracted_dates:
        if date not in deadlines:
            deadlines.append(date)

    return {
        "success": True,
        "message": "Scope extraction completed.",
        "project_name": extract_project_name(text),
        "goals": goals,
        "requirements": requirements,
        "milestones": milestones,
        "deliverables": deliverables,
        "responsibilities": responsibilities,
        "deadlines": deadlines,
        "source": "Uploaded document text"
    }


if __name__ == "__main__":

    sample_text = """
    Project Name: AI Project Intelligence Platform

    Objective: Build an AI-powered project management assistant.

    Goals:
    - Identify project risks.
    - Extract project requirements.

    Deliverables:
    - Document Upload Module
    - Risk Detection Module
    - Project Dashboard

    Milestone 1: Document Ingestion
    Milestone 2: Risk Detection

    Requirement: The system must accept PDF documents.

    Responsible: Nikhil

    Deadline: 30 November 2026
    """

    result = extract_scope(sample_text)

    import json

    print(json.dumps(result, indent=4, ensure_ascii=False))
```
