from risk_agent import analyze_risks
from scope_agent import extract_scope
from blocker_agent import identify_blockers


def generate_risk_register():
    risks = analyze_risks()

    return [
        {
            "risk_id": f"RISK-{index:03d}",
            "category": risk["category"],
            "source": risk["source"],
            "evidence": risk["evidence"],
            "recommended_action": risk["recommendation"],
            "status": "Needs Review"
        }
        for index, risk in enumerate(risks, start=1)
    ]


def generate_user_story(requirement):
    requirement = requirement.strip()

    if not requirement:
        raise ValueError(
            "Requirement cannot be empty."
        )

    return {
        "user_story": (
            f"As a project stakeholder, "
            f"I want {requirement}, "
            f"so that the project objective can be achieved."
        ),
        "acceptance_criteria": [
            "The requirement is documented.",
            "The responsible owner is identified.",
            "The outcome is reviewed and approved."
        ],
        "status": "Draft - Review Required"
    }


def generate_project_summary():
    return {
        "scope_findings": extract_scope(),
        "blockers": identify_blockers(),
        "risk_register": generate_risk_register()
    }
