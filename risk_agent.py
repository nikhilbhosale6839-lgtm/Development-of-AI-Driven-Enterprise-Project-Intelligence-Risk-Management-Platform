```python
import re


def detect_risks(document_text):
    """
    Risk Detection Agent.

    Identifies potential project risks from document text.
    This is a rule-based baseline, not an AI prediction model.
    """

    if not document_text or not document_text.strip():
        return {
            "success": False,
            "message": "No document text provided.",
            "total_risks": 0,
            "risks": []
        }

    text = document_text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Risk indicators and their recommended actions.
    risk_rules = [
        {
            "keywords": [
                "blocked",
                "blocker",
                "blocked by",
                "dependency pending"
            ],
            "risk_type": "Dependency Blocker",
            "severity": "High",
            "recommendation": (
                "Identify the dependency owner, confirm the resolution "
                "date, and track the blocker."
            )
        },
        {
            "keywords": [
                "api access pending",
                "access pending",
                "waiting for access",
                "approval pending"
            ],
            "risk_type": "Access or Approval Delay",
            "severity": "High",
            "recommendation": (
                "Contact the responsible team and establish a target "
                "date for access or approval."
            )
        },
        {
            "keywords": [
                "testing not started",
                "testing pending",
                "test cases pending",
                "testing delayed"
            ],
            "risk_type": "Testing Delay",
            "severity": "Medium",
            "recommendation": (
                "Prepare test cases, confirm test data availability, "
                "and schedule testing."
            )
        },
        {
            "keywords": [
                "deadline missed",
                "overdue",
                "past due",
                "deadline exceeded"
            ],
            "risk_type": "Deadline Risk",
            "severity": "High",
            "recommendation": (
                "Review incomplete tasks, revise the delivery plan, "
                "and agree on recovery actions."
            )
        },
        {
            "keywords": [
                "resource unavailable",
                "staff shortage",
                "team member unavailable",
                "insufficient resources"
            ],
            "risk_type": "Resource Risk",
            "severity": "Medium",
            "recommendation": (
                "Review resource availability and reassign or reprioritize "
                "work where necessary."
            )
        },
        {
            "keywords": [
                "requirements unclear",
                "unclear requirements",
                "requirements not finalized",
                "scope unclear"
            ],
            "risk_type": "Requirements or Scope Risk",
            "severity": "Medium",
            "recommendation": (
                "Confirm requirements with stakeholders and document "
                "approved scope changes."
            )
        },
        {
            "keywords": [
                "integration failed",
                "integration failure",
                "deployment failed",
                "build failed"
            ],
            "risk_type": "Technical Integration Risk",
            "severity": "High",
            "recommendation": (
                "Investigate the failure, record its impact, and define "
                "corrective actions before delivery."
            )
        },
        {
            "keywords": [
                "no progress",
                "work stalled",
                "task delayed",
                "progress delayed"
            ],
            "risk_type": "Progress Risk",
            "severity": "Medium",
            "recommendation": (
                "Review task status, identify the cause of the delay, "
                "and agree on a recovery plan."
            )
        }
    ]

    detected_risks = []
    seen = set()

    for line in lines:
        normalized_line = line.lower()

        for rule in risk_rules:
            matched_keyword = next(
                (
                    keyword
                    for keyword in rule["keywords"]
                    if re.search(
                        r"\b" + re.escape(keyword) + r"\b",
                        normalized_line
                    )
                ),
                None
            )

            if matched_keyword:
                key = (rule["risk_type"], line)

                if key not in seen:
                    detected_risks.append({
                        "risk_type": rule["risk_type"],
                        "severity": rule["severity"],
                        "evidence": line,
                        "matched_keyword": matched_keyword,
                        "recommendation": rule["recommendation"],
                        "status": "Needs Review"
                    })

                    seen.add(key)

    return {
        "success": True,
        "message": (
            "Risk analysis completed."
            if detected_risks
            else "No configured risk indicators were found."
        ),
        "total_risks": len(detected_risks),
        "risks": detected_risks
    }


if __name__ == "__main__":
    import json

    sample_text = """
    Project Update:
    The RAG pipeline is blocked by pending API access.
    Testing has not started.
    The integration failed during the latest build.
    The team completed the documentation.
    """

    result = detect_risks(sample_text)

    print(json.dumps(result, indent=4, ensure_ascii=False))
```
