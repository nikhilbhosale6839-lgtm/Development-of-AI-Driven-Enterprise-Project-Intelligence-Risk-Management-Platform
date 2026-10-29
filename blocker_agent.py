```python
import re


def identify_blockers(document_text):
    """
    Blocker Identification Agent.

    Identifies possible blockers and unresolved issues
    from project documents using configurable text rules.
    """

    if not document_text or not document_text.strip():
        return {
            "success": False,
            "message": "No document text provided.",
            "total_blockers": 0,
            "blockers": []
        }

    rules = [
        {
            "keywords": [
                "blocked",
                "work is blocked",
                "task is blocked",
                "blocking issue"
            ],
            "type": "Blocked Task",
            "impact": "Potential work delay",
            "recommendation": (
                "Identify the root cause, responsible owner, "
                "and expected resolution date."
            )
        },
        {
            "keywords": [
                "api access pending",
                "access pending",
                "waiting for access",
                "access not granted"
            ],
            "type": "Access Blocker",
            "impact": "Development or integration may be delayed",
            "recommendation": (
                "Contact the access-providing team and "
                "confirm when access will be available."
            )
        },
        {
            "keywords": [
                "approval pending",
                "awaiting approval",
                "approval not received"
            ],
            "type": "Approval Blocker",
            "impact": "Dependent work may not proceed",
            "recommendation": (
                "Follow up with the approver and document "
                "the expected approval date."
            )
        },
        {
            "keywords": [
                "dependency pending",
                "dependency blocked",
                "waiting for dependency",
                "dependent task incomplete"
            ],
            "type": "Dependency Blocker",
            "impact": "Downstream tasks may be delayed",
            "recommendation": (
                "Contact the dependency owner and update "
                "the dependent task plan."
            )
        },
        {
            "keywords": [
                "integration failed",
                "build failed",
                "deployment failed",
                "system failure"
            ],
            "type": "Technical Blocker",
            "impact": "Testing or delivery may be affected",
            "recommendation": (
                "Investigate the error, assign an owner, "
                "and track the resolution."
            )
        },
        {
            "keywords": [
                "decision pending",
                "decision not finalized",
                "awaiting decision",
                "unresolved decision"
            ],
            "type": "Pending Decision",
            "impact": "Implementation may be delayed",
            "recommendation": (
                "Arrange a discussion with the decision-maker "
                "and record the agreed outcome."
            )
        },
        {
            "keywords": [
                "waiting for test data",
                "test data unavailable",
                "test environment unavailable"
            ],
            "type": "Testing Blocker",
            "impact": "Testing activities may be delayed",
            "recommendation": (
                "Arrange test data and confirm environment readiness."
            )
        }
    ]

    blockers = []
    seen = set()

    for line in document_text.splitlines():
        line = line.strip()

        if not line:
            continue

        normalized_line = line.lower()

        for rule in rules:
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

            if not matched_keyword:
                continue

            # Avoid duplicate entries for the same rule and evidence.
            key = (rule["type"], line)

            if key in seen:
                continue

            blockers.append({
                "blocker_type": rule["type"],
                "description": line,
                "matched_keyword": matched_keyword,
                "potential_impact": rule["impact"],
                "recommended_action": rule["recommendation"],
                "status": "Needs Review",
                "owner": None,
                "resolution_date": None
            })

            seen.add(key)

    return {
        "success": True,
        "message": (
            "Blocker identification completed."
            if blockers
            else "No configured blocker indicators were found."
        ),
        "total_blockers": len(blockers),
        "blockers": blockers
    }


if __name__ == "__main__":
    import json

    sample_text = """
    Project Meeting Notes:

    The RAG pipeline is blocked because API access is pending.
    The integration failed during the latest build.
    Dashboard development is waiting for approval.
    The team completed document upload testing.
    """

    result = identify_blockers(sample_text)

    print(json.dumps(result, indent=4, ensure_ascii=False))
```
