import re


# =====================================================
# RISK KEYWORDS
# =====================================================

RISK_PATTERNS = {

    "Schedule Risk": [
        "project delay",
        "schedule delay",
        "delayed",
        "behind schedule",
        "missed deadline",
        "timeline risk",
        "deadline risk",
        "time constraint",
        "delivery delay"
    ],

    "Budget Risk": [
        "budget overrun",
        "cost overrun",
        "financial risk",
        "insufficient budget",
        "budget constraint",
        "cost escalation",
        "funding issue"
    ],

    "Technical Risk": [
        "technical issue",
        "technical challenge",
        "system failure",
        "integration issue",
        "compatibility issue",
        "performance issue",
        "technical dependency",
        "technology limitation"
    ],

    "Resource Risk": [
        "resource shortage",
        "staff shortage",
        "lack of resources",
        "insufficient manpower",
        "skill gap",
        "resource constraint",
        "employee unavailability"
    ],

    "Security Risk": [
        "security vulnerability",
        "data breach",
        "unauthorized access",
        "cyber attack",
        "data leakage",
        "privacy risk",
        "security threat"
    ],

    "Quality Risk": [
        "quality issue",
        "testing failure",
        "defect",
        "bug",
        "incomplete testing",
        "quality concern",
        "validation failure"
    ],

    "Dependency Risk": [
        "external dependency",
        "vendor dependency",
        "third party dependency",
        "dependency delay",
        "blocked by dependency",
        "supplier delay"
    ],

    "Operational Risk": [
        "operational failure",
        "process failure",
        "service disruption",
        "infrastructure failure",
        "business interruption",
        "system downtime"
    ]

}


# =====================================================
# RISK MITIGATION RECOMMENDATIONS
# =====================================================

MITIGATION_RECOMMENDATIONS = {

    "Schedule Risk":
        "Review the project timeline, monitor milestones, "
        "and prepare a recovery plan.",

    "Budget Risk":
        "Monitor project expenditure, review cost estimates, "
        "and maintain a contingency budget.",

    "Technical Risk":
        "Perform technical assessments, conduct integration "
        "testing, and involve technical experts.",

    "Resource Risk":
        "Review resource allocation, identify skill gaps, "
        "and arrange additional resources or training.",

    "Security Risk":
        "Perform security assessments, enforce access controls, "
        "and follow security best practices.",

    "Quality Risk":
        "Improve testing coverage, conduct quality reviews, "
        "and resolve defects before release.",

    "Dependency Risk":
        "Monitor external dependencies, communicate with vendors, "
        "and identify alternative solutions.",

    "Operational Risk":
        "Establish operational monitoring, backup procedures, "
        "and incident response plans.",

    "General Risk":
        "Review the identified risk regularly and assign an owner "
        "for mitigation."
}


# =====================================================
# TEXT CLEANING
# =====================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")

    text = text.replace("\r\n", "\n")

    text = text.replace("\r", "\n")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =====================================================
# RISK CATEGORY IDENTIFICATION
# =====================================================

def identify_risk_category(sentence):

    normalized = sentence.lower()

    for category, keywords in RISK_PATTERNS.items():

        for keyword in keywords:

            if keyword in normalized:

                return category

    return "General Risk"


# =====================================================
# RISK SEVERITY
# =====================================================

def calculate_severity(sentence, category):

    text = sentence.lower()

    high_indicators = [

        "critical",
        "severe",
        "major",
        "high risk",
        "project failure",
        "data breach",
        "system failure",
        "business interruption",
        "missed deadline",
        "security vulnerability",
        "budget overrun"

    ]

    medium_indicators = [

        "moderate",
        "potential",
        "possible",
        "delay",
        "issue",
        "challenge",
        "dependency",
        "constraint",
        "concern"

    ]

    if any(
        keyword in text
        for keyword in high_indicators
    ):

        return "High"

    if any(
        keyword in text
        for keyword in medium_indicators
    ):

        return "Medium"

    if category != "General Risk":

        return "Medium"

    return "Low"


# =====================================================
# PROBABILITY ASSESSMENT
# =====================================================

def calculate_probability(sentence):

    text = sentence.lower()

    high_words = [

        "high probability",
        "high likelihood",
        "very likely",
        "almost certain",
        "frequent",
        "repeatedly"

    ]

    low_words = [

        "unlikely",
        "rare",
        "low probability",
        "low likelihood",
        "remote possibility"

    ]

    if any(
        word in text
        for word in high_words
    ):

        return "High"

    if any(
        word in text
        for word in low_words
    ):

        return "Low"

    return "Medium"


# =====================================================
# IMPACT ASSESSMENT
# =====================================================

def calculate_impact(sentence, severity):

    text = sentence.lower()

    high_impact_words = [

        "project failure",
        "critical failure",
        "business interruption",
        "data breach",
        "major financial loss",
        "missed deadline",
        "production failure",
        "system failure"

    ]

    low_impact_words = [

        "minor",
        "small impact",
        "limited impact",
        "temporary issue"

    ]

    if any(
        word in text
        for word in high_impact_words
    ):

        return "High"

    if any(
        word in text
        for word in low_impact_words
    ):

        return "Low"

    return severity


# =====================================================
# RISK PRIORITY
# =====================================================

def calculate_priority(
    probability,
    impact
):

    score_mapping = {

        "Low": 1,

        "Medium": 2,

        "High": 3

    }

    probability_score = score_mapping.get(
        probability,
        2
    )

    impact_score = score_mapping.get(
        impact,
        2
    )

    total_score = (
        probability_score * impact_score
    )

    if total_score >= 6:

        return "High"

    elif total_score >= 3:

        return "Medium"

    return "Low"


# =====================================================
# SENTENCE EXTRACTION
# =====================================================

def extract_sentences(text):

    lines = text.split("\n")

    sentences = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        parts = re.split(
            r"(?<=[.!?])\s+",
            line
        )

        for part in parts:

            part = part.strip()

            if len(part) >= 10:

                sentences.append(part)

    return sentences


# =====================================================
# RISK DESCRIPTION VALIDATION
# =====================================================

def is_valid_risk(sentence):

    normalized = sentence.lower()

    risk_indicators = [

        "risk",

        "delay",

        "failure",

        "issue",

        "shortage",

        "vulnerability",

        "overrun",

        "constraint",

        "defect",

        "threat",

        "disruption",

        "dependency",

        "challenge",

        "unavailable",

        "breach"

    ]

    return any(
        word in normalized
        for word in risk_indicators
    )


# =====================================================
# RISK DESCRIPTION CLEANING
# =====================================================

def clean_risk_description(sentence):

    sentence = re.sub(
        r"^[-*•\d.)\s]+",
        "",
        sentence
    )

    sentence = sentence.strip()

    return sentence


# =====================================================
# DUPLICATE REMOVAL
# =====================================================

def remove_duplicate_risks(risks):

    unique_risks = []

    seen = set()

    for risk in risks:

        description = risk.get(
            "risk",
            ""
        )

        normalized = description.lower().strip()

        if normalized not in seen:

            seen.add(normalized)

            unique_risks.append(risk)

    return unique_risks


# =====================================================
# MAIN RISK DETECTION FUNCTION
# =====================================================

def detect_risks(text):

    text = clean_text(
        text
    )

    if not text:

        return {

            "success": False,

            "message": "No document text available.",

            "total_risks": 0,

            "risks": []

        }

    try:

        sentences = extract_sentences(
            text
        )

        identified_risks = []

        for sentence in sentences:

            if not is_valid_risk(sentence):

                continue

            description = clean_risk_description(
                sentence
            )

            category = identify_risk_category(
                description
            )

            severity = calculate_severity(
                description,
                category
            )

            probability = calculate_probability(
                description
            )

            impact = calculate_impact(
                description,
                severity
            )

            priority = calculate_priority(
                probability,
                impact
            )

            risk = {

                "risk_id": (
                    f"RISK-{len(identified_risks) + 1:03}"
                ),

                "risk": description,

                "description": description,

                "category": category,

                "severity": severity,

                "probability": probability,

                "impact": impact,

                "priority": priority,

                "mitigation": MITIGATION_RECOMMENDATIONS.get(
                    category,
                    MITIGATION_RECOMMENDATIONS["General Risk"]
                ),

                "owner": "Not Assigned",

                "status": "Open",

                "source": "Risk Agent"

            }

            identified_risks.append(
                risk
            )

        identified_risks = remove_duplicate_risks(
            identified_risks
        )

        # Reassign sequential IDs after duplicate removal
        for index, risk in enumerate(
            identified_risks,
            start=1
        ):

            risk["risk_id"] = (
                f"RISK-{index:03}"
            )

        high_count = sum(

            1

            for risk in identified_risks

            if risk["severity"] == "High"

        )

        medium_count = sum(

            1

            for risk in identified_risks

            if risk["severity"] == "Medium"

        )

        low_count = sum(

            1

            for risk in identified_risks

            if risk["severity"] == "Low"

        )

        return {

            "success": True,

            "message": "Risk identification completed successfully.",

            "total_risks": len(
                identified_risks
            ),

            "high_risks": high_count,

            "medium_risks": medium_count,

            "low_risks": low_count,

            "risks": identified_risks,

            "source": "Risk Agent"

        }

    except Exception as error:

        return {

            "success": False,

            "message": f"Risk identification failed: {str(error)}",

            "total_risks": 0,

            "risks": [],

            "source": "Risk Agent"

        }


# =====================================================
# TESTING
# =====================================================

if __name__ == "__main__":

    sample_text = """

    Project Risk Analysis

    The project may face significant schedule delay.

    There is a high probability of budget overrun.

    The system has a potential security vulnerability.

    Resource shortage may affect project delivery.

    Integration issues may cause technical challenges.

    """

    import json

    result = detect_risks(
        sample_text
    )

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
