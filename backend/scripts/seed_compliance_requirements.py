"""
Seed Compliance Requirements Data

Populates the funder_requirements and compliance_templates tables with
common NIH, NSF, and foundation compliance requirements.

This script seeds realistic compliance requirements that researchers
need to track after receiving grant awards.

Usage:
    python -m backend.scripts.seed_compliance_requirements
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

# =============================================================================
# NIH Requirements
# =============================================================================

NIH_REQUIREMENTS = [
    # Progress Reports
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Research Performance Progress Report (RPPR) - Annual progress report required for all multi-year grants",
        "frequency": "annual",
        "deadline_offset_days": 45,  # Due 45 days before anniversary
        "mechanism": None,  # Applies to all mechanisms
        "notes": "Submit via eRA Commons. Includes accomplishments, products, participants, impact, and changes.",
    },
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Final Research Performance Progress Report (Final RPPR) - Required within 120 days of project end",
        "frequency": "final",
        "deadline_offset_days": 120,
        "mechanism": None,
        "notes": "Comprehensive final report covering entire project period.",
    },
    # Financial Reports
    {
        "funder_name": "NIH",
        "requirement_type": "financial",
        "requirement_text": "Federal Financial Report (FFR/SF-425) - Quarterly or Annual financial status report",
        "frequency": "quarterly",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Report expenditures and unobligated balance. Due 30 days after each quarter.",
    },
    {
        "funder_name": "NIH",
        "requirement_type": "financial",
        "requirement_text": "Final Federal Financial Report (Final FFR) - Due 120 days after project end",
        "frequency": "final",
        "deadline_offset_days": 120,
        "mechanism": None,
        "notes": "Final accounting of all grant expenditures.",
    },
    # Data Management
    {
        "funder_name": "NIH",
        "requirement_type": "data_management",
        "requirement_text": "Data Management and Sharing Plan (DMS) - Required for all research generating scientific data",
        "frequency": "one_time",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "As of January 2023, all NIH-funded research must have a DMS plan. Update as needed.",
    },
    {
        "funder_name": "NIH",
        "requirement_type": "data_management",
        "requirement_text": "ClinicalTrials.gov Registration - Required for clinical trials",
        "frequency": "one_time",
        "deadline_offset_days": 21,  # Within 21 days of first enrollment
        "mechanism": None,
        "notes": "Register trial before first patient enrollment. Update results within 12 months of completion.",
    },
    # Invention Reports
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Invention Report (iEdison) - Report any inventions conceived or reduced to practice",
        "frequency": "annual",
        "deadline_offset_days": 60,
        "mechanism": None,
        "notes": "Report within 60 days of invention disclosure. Submit via iEdison system.",
    },
    # Ethical Requirements
    {
        "funder_name": "NIH",
        "requirement_type": "ethical",
        "requirement_text": "IRB Approval Renewal - Maintain current IRB approval for human subjects research",
        "frequency": "annual",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "Submit renewal before expiration. Grant funds cannot be used after IRB expires.",
    },
    {
        "funder_name": "NIH",
        "requirement_type": "ethical",
        "requirement_text": "IACUC Approval Renewal - Maintain current IACUC approval for animal research",
        "frequency": "annual",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "Protocol must remain active. Annual continuing review required.",
    },
    # K Award Specific
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Career Development Progress Report - Document mentoring and career development activities",
        "frequency": "annual",
        "deadline_offset_days": 45,
        "mechanism": "K",  # Applies to all K awards
        "notes": "Include mentor meetings, training activities, protected time verification.",
    },
    # Training Grant Specific
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Trainee Appointment Forms (PHS 2271) - Required for each trainee",
        "frequency": "one_time",
        "deadline_offset_days": 30,
        "mechanism": "T32",
        "notes": "Submit within 30 days of trainee appointment.",
    },
    {
        "funder_name": "NIH",
        "requirement_type": "reporting",
        "requirement_text": "Trainee Termination Notice (PHS 416-7) - Required when trainee leaves",
        "frequency": "one_time",
        "deadline_offset_days": 30,
        "mechanism": "T32",
        "notes": "Submit within 30 days of trainee termination.",
    },
]

# =============================================================================
# NSF Requirements
# =============================================================================

NSF_REQUIREMENTS = [
    # Progress Reports
    {
        "funder_name": "NSF",
        "requirement_type": "reporting",
        "requirement_text": "Annual Project Report - Required 90 days before each anniversary date",
        "frequency": "annual",
        "deadline_offset_days": 90,
        "mechanism": None,
        "notes": "Submit via Research.gov. Include accomplishments, participants, publications, and activities.",
    },
    {
        "funder_name": "NSF",
        "requirement_type": "reporting",
        "requirement_text": "Final Project Report - Required within 120 days of project end",
        "frequency": "final",
        "deadline_offset_days": 120,
        "mechanism": None,
        "notes": "Comprehensive final report. Future funding may depend on timely submission.",
    },
    {
        "funder_name": "NSF",
        "requirement_type": "reporting",
        "requirement_text": "Project Outcomes Report - Public summary for non-scientists due within 120 days",
        "frequency": "final",
        "deadline_offset_days": 120,
        "mechanism": None,
        "notes": "Written for general public. Posted on NSF website. Required by America COMPETES Act.",
    },
    # Financial Reports
    {
        "funder_name": "NSF",
        "requirement_type": "financial",
        "requirement_text": "Federal Financial Report (FFR) - Quarterly financial report",
        "frequency": "quarterly",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Due 30 days after quarter end. Report via Research.gov.",
    },
    {
        "funder_name": "NSF",
        "requirement_type": "financial",
        "requirement_text": "Final Financial Report - Due 120 days after project end",
        "frequency": "final",
        "deadline_offset_days": 120,
        "mechanism": None,
        "notes": "Final accounting of all expenditures.",
    },
    # Data Management
    {
        "funder_name": "NSF",
        "requirement_type": "data_management",
        "requirement_text": "Data Management Plan Implementation - Execute DMP as proposed",
        "frequency": "one_time",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "Make data available as described in approved DMP. Report in annual reports.",
    },
    # Ethical Requirements
    {
        "funder_name": "NSF",
        "requirement_type": "ethical",
        "requirement_text": "Responsible Conduct of Research (RCR) Training - Required for all participants",
        "frequency": "one_time",
        "deadline_offset_days": 90,
        "mechanism": None,
        "notes": "All undergraduate students, graduate students, and postdocs must complete RCR training.",
    },
    # CAREER Award Specific
    {
        "funder_name": "NSF",
        "requirement_type": "reporting",
        "requirement_text": "CAREER Education Plan Report - Document educational activities",
        "frequency": "annual",
        "deadline_offset_days": 90,
        "mechanism": "CAREER",
        "notes": "Detail progress on educational component of CAREER award.",
    },
]

# =============================================================================
# Foundation Requirements (Gates, Ford, etc.)
# =============================================================================

FOUNDATION_REQUIREMENTS = [
    # Gates Foundation
    {
        "funder_name": "Bill & Melinda Gates Foundation",
        "requirement_type": "reporting",
        "requirement_text": "Progress Report - Semi-annual or annual depending on grant",
        "frequency": "annual",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Submit via Gates Foundation portal. Include narrative and financial sections.",
    },
    {
        "funder_name": "Bill & Melinda Gates Foundation",
        "requirement_type": "financial",
        "requirement_text": "Financial Report - Report expenditures against budget",
        "frequency": "annual",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Include budget vs actual comparison. Explain variances > 10%.",
    },
    {
        "funder_name": "Bill & Melinda Gates Foundation",
        "requirement_type": "data_management",
        "requirement_text": "Open Access Publication - All publications must be open access",
        "frequency": "one_time",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "CC BY 4.0 license required. Data underlying publications must be accessible.",
    },
    # Wellcome Trust
    {
        "funder_name": "Wellcome Trust",
        "requirement_type": "reporting",
        "requirement_text": "Annual Report - Progress update required annually",
        "frequency": "annual",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Submit via Wellcome grant management system.",
    },
    {
        "funder_name": "Wellcome Trust",
        "requirement_type": "financial",
        "requirement_text": "Statement of Expenditure - Annual financial report",
        "frequency": "annual",
        "deadline_offset_days": 60,
        "mechanism": None,
        "notes": "Certified statement of grant expenditures.",
    },
    {
        "funder_name": "Wellcome Trust",
        "requirement_type": "data_management",
        "requirement_text": "Open Access Compliance - All outputs must be openly accessible",
        "frequency": "one_time",
        "deadline_offset_days": 0,
        "mechanism": None,
        "notes": "Open access requirement for publications and underlying data.",
    },
    # Howard Hughes Medical Institute
    {
        "funder_name": "HHMI",
        "requirement_type": "reporting",
        "requirement_text": "Scientific Report - Annual progress report",
        "frequency": "annual",
        "deadline_offset_days": 60,
        "mechanism": None,
        "notes": "Describe research progress, publications, and future directions.",
    },
    # Robert Wood Johnson Foundation
    {
        "funder_name": "Robert Wood Johnson Foundation",
        "requirement_type": "reporting",
        "requirement_text": "Progress Report - Quarterly or semi-annual depending on grant",
        "frequency": "quarterly",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Include narrative and financial components.",
    },
    {
        "funder_name": "Robert Wood Johnson Foundation",
        "requirement_type": "financial",
        "requirement_text": "Financial Status Report - Report expenditures",
        "frequency": "quarterly",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Detailed breakdown of grant expenditures.",
    },
]

# =============================================================================
# DOE Requirements
# =============================================================================

DOE_REQUIREMENTS = [
    {
        "funder_name": "DOE",
        "requirement_type": "reporting",
        "requirement_text": "Annual Progress Report - Technical progress report",
        "frequency": "annual",
        "deadline_offset_days": 60,
        "mechanism": None,
        "notes": "Submit via DOE portfolio management system.",
    },
    {
        "funder_name": "DOE",
        "requirement_type": "financial",
        "requirement_text": "Federal Financial Report (SF-425) - Quarterly financial status",
        "frequency": "quarterly",
        "deadline_offset_days": 30,
        "mechanism": None,
        "notes": "Due 30 days after quarter end.",
    },
    {
        "funder_name": "DOE",
        "requirement_type": "reporting",
        "requirement_text": "Final Technical Report - Comprehensive final report",
        "frequency": "final",
        "deadline_offset_days": 90,
        "mechanism": None,
        "notes": "Due 90 days after project end. Submit to OSTI.",
    },
    {
        "funder_name": "DOE",
        "requirement_type": "reporting",
        "requirement_text": "Invention Disclosure - Report inventions via iEdison",
        "frequency": "annual",
        "deadline_offset_days": 60,
        "mechanism": None,
        "notes": "Report any inventions within 60 days of disclosure.",
    },
]

# =============================================================================
# Compliance Templates
# =============================================================================

COMPLIANCE_TEMPLATES = [
    # NIH Progress Report Template
    {
        "funder_name": "NIH",
        "mechanism": None,
        "template_name": "NIH RPPR Template",
        "template_type": "progress_report",
        "description": "Template for NIH Research Performance Progress Report",
        "template_content": {
            "sections": [
                {
                    "name": "Accomplishments",
                    "description": "What are the major goals of the project?",
                    "required": True,
                    "fields": [
                        {"name": "major_goals", "type": "textarea", "label": "Major Goals"},
                        {"name": "accomplishments", "type": "textarea", "label": "Significant Accomplishments"},
                    ],
                },
                {
                    "name": "Products",
                    "description": "Publications, data, and other products",
                    "required": True,
                    "fields": [
                        {"name": "publications", "type": "list", "label": "Publications"},
                        {"name": "datasets", "type": "list", "label": "Datasets"},
                        {"name": "patents", "type": "list", "label": "Patents/Inventions"},
                    ],
                },
                {
                    "name": "Participants",
                    "description": "Personnel and collaborators",
                    "required": True,
                    "fields": [
                        {"name": "key_personnel", "type": "list", "label": "Key Personnel"},
                        {"name": "trainees", "type": "list", "label": "Trainees"},
                    ],
                },
                {
                    "name": "Impact",
                    "description": "What is the impact of the project?",
                    "required": False,
                    "fields": [
                        {"name": "scientific_impact", "type": "textarea", "label": "Scientific Impact"},
                        {"name": "broader_impacts", "type": "textarea", "label": "Broader Impacts"},
                    ],
                },
                {
                    "name": "Changes",
                    "description": "Changes in approach or personnel",
                    "required": True,
                    "fields": [
                        {"name": "changes_problems", "type": "textarea", "label": "Changes/Problems"},
                        {"name": "budget_changes", "type": "textarea", "label": "Budget Changes"},
                    ],
                },
            ]
        },
    },
    # NIH Data Management Plan Template
    {
        "funder_name": "NIH",
        "mechanism": None,
        "template_name": "NIH Data Management Plan Template",
        "template_type": "data_plan",
        "description": "Template for NIH Data Management and Sharing Plan",
        "template_content": {
            "sections": [
                {
                    "name": "Data Types",
                    "required": True,
                    "fields": [
                        {"name": "data_types", "type": "textarea", "label": "Types and amount of data"},
                        {"name": "data_formats", "type": "text", "label": "Data formats"},
                    ],
                },
                {
                    "name": "Tools and Software",
                    "required": True,
                    "fields": [
                        {"name": "tools", "type": "textarea", "label": "Tools/software needed to access data"},
                    ],
                },
                {
                    "name": "Standards",
                    "required": True,
                    "fields": [
                        {"name": "standards", "type": "textarea", "label": "Data standards applied"},
                    ],
                },
                {
                    "name": "Repository",
                    "required": True,
                    "fields": [
                        {"name": "repository", "type": "text", "label": "Repository name"},
                        {"name": "persistent_id", "type": "text", "label": "Persistent unique identifier plan"},
                    ],
                },
                {
                    "name": "Access and Preservation",
                    "required": True,
                    "fields": [
                        {"name": "access_timeline", "type": "text", "label": "When data will be available"},
                        {"name": "access_restrictions", "type": "textarea", "label": "Access restrictions"},
                        {"name": "preservation_period", "type": "text", "label": "Preservation period"},
                    ],
                },
            ]
        },
    },
    # NSF Annual Report Template
    {
        "funder_name": "NSF",
        "mechanism": None,
        "template_name": "NSF Annual Project Report Template",
        "template_type": "progress_report",
        "description": "Template for NSF Annual Project Report",
        "template_content": {
            "sections": [
                {
                    "name": "Accomplishments",
                    "required": True,
                    "fields": [
                        {"name": "major_goals", "type": "textarea", "label": "Major Goals"},
                        {"name": "major_activities", "type": "textarea", "label": "Major Activities"},
                        {"name": "specific_objectives", "type": "textarea", "label": "Specific Objectives"},
                        {"name": "significant_results", "type": "textarea", "label": "Significant Results"},
                    ],
                },
                {
                    "name": "Products",
                    "required": True,
                    "fields": [
                        {"name": "publications", "type": "list", "label": "Publications"},
                        {"name": "websites", "type": "list", "label": "Websites"},
                        {"name": "other_products", "type": "textarea", "label": "Other Products"},
                    ],
                },
                {
                    "name": "Participants",
                    "required": True,
                    "fields": [
                        {"name": "senior_personnel", "type": "list", "label": "Senior Personnel"},
                        {"name": "postdocs", "type": "list", "label": "Postdoctoral Researchers"},
                        {"name": "graduate_students", "type": "list", "label": "Graduate Students"},
                        {"name": "undergraduates", "type": "list", "label": "Undergraduate Students"},
                    ],
                },
                {
                    "name": "Impacts",
                    "required": True,
                    "fields": [
                        {
                            "name": "scientific_impact",
                            "type": "textarea",
                            "label": "What is the impact on the development of the principal discipline(s)?",
                        },
                        {
                            "name": "other_disciplines",
                            "type": "textarea",
                            "label": "What is the impact on other disciplines?",
                        },
                        {
                            "name": "human_resources",
                            "type": "textarea",
                            "label": "What is the impact on human resource development?",
                        },
                        {
                            "name": "physical_resources",
                            "type": "textarea",
                            "label": "What is the impact on physical resources?",
                        },
                        {
                            "name": "society_impact",
                            "type": "textarea",
                            "label": "What is the impact on society beyond science and technology?",
                        },
                    ],
                },
                {
                    "name": "Changes",
                    "required": True,
                    "fields": [
                        {
                            "name": "changes_problems",
                            "type": "textarea",
                            "label": "Changes in approach or reasons for change",
                        },
                        {
                            "name": "opportunities",
                            "type": "textarea",
                            "label": "Opportunities for training and professional development",
                        },
                        {"name": "dissemination", "type": "textarea", "label": "How have results been disseminated?"},
                    ],
                },
            ]
        },
    },
]


async def seed_compliance_requirements():
    """Seed the compliance requirements tables."""
    from backend.database import get_async_session
    from sqlalchemy import text

    async with get_async_session() as session:
        try:
            # Combine all requirements
            all_requirements = NIH_REQUIREMENTS + NSF_REQUIREMENTS + FOUNDATION_REQUIREMENTS + DOE_REQUIREMENTS

            requirements_inserted = 0
            now = datetime.now(timezone.utc)

            for req in all_requirements:
                # Check if already exists
                result = await session.execute(
                    text("""
                        SELECT id FROM funder_requirements
                        WHERE funder_name = :funder_name
                        AND requirement_type = :requirement_type
                        AND requirement_text = :requirement_text
                    """),
                    {
                        "funder_name": req["funder_name"],
                        "requirement_type": req["requirement_type"],
                        "requirement_text": req["requirement_text"],
                    },
                )
                existing = result.fetchone()

                if existing:
                    print(f"Requirement already exists: {req['funder_name']} - {req['requirement_type'][:30]}...")
                    continue

                # Insert new requirement
                req_id = uuid.uuid4()
                await session.execute(
                    text("""
                        INSERT INTO funder_requirements (
                            id, funder_name, requirement_type, requirement_text,
                            frequency, deadline_offset_days, mechanism, notes,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :id, :funder_name, :requirement_type, :requirement_text,
                            :frequency, :deadline_offset_days, :mechanism, :notes,
                            :is_active, :created_at, :updated_at
                        )
                    """),
                    {
                        "id": req_id,
                        "funder_name": req["funder_name"],
                        "requirement_type": req["requirement_type"],
                        "requirement_text": req["requirement_text"],
                        "frequency": req["frequency"],
                        "deadline_offset_days": req.get("deadline_offset_days"),
                        "mechanism": req.get("mechanism"),
                        "notes": req.get("notes"),
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                requirements_inserted += 1
                print(f"Inserted: {req['funder_name']} - {req['requirement_text'][:50]}...")

            print(f"\nInserted {requirements_inserted} requirements.")

            # Seed compliance templates
            templates_inserted = 0

            for template in COMPLIANCE_TEMPLATES:
                # Check if already exists
                result = await session.execute(
                    text("""
                        SELECT id FROM compliance_templates
                        WHERE funder_name = :funder_name
                        AND template_name = :template_name
                    """),
                    {
                        "funder_name": template["funder_name"],
                        "template_name": template["template_name"],
                    },
                )
                existing = result.fetchone()

                if existing:
                    print(f"Template already exists: {template['template_name']}")
                    continue

                # Insert new template
                template_id = uuid.uuid4()
                await session.execute(
                    text("""
                        INSERT INTO compliance_templates (
                            id, funder_name, mechanism, template_name,
                            template_type, template_content, description,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :id, :funder_name, :mechanism, :template_name,
                            :template_type, :template_content, :description,
                            :is_active, :created_at, :updated_at
                        )
                    """),
                    {
                        "id": template_id,
                        "funder_name": template["funder_name"],
                        "mechanism": template.get("mechanism"),
                        "template_name": template["template_name"],
                        "template_type": template["template_type"],
                        "template_content": json.dumps(template["template_content"]),
                        "description": template.get("description"),
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                templates_inserted += 1
                print(f"Inserted template: {template['template_name']}")

            await session.commit()
            print("\nSeed complete!")
            print(f"  - Requirements inserted: {requirements_inserted}")
            print(f"  - Templates inserted: {templates_inserted}")

        except Exception as e:
            await session.rollback()
            print(f"Error seeding compliance requirements: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_compliance_requirements())
