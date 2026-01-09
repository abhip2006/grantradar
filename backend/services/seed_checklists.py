"""
Seed initial checklist templates for common funders.
Run this once during initial setup or migration.
"""
import asyncio
import logging
from uuid import uuid4

from backend.database import get_async_session
from backend.models.checklists import ChecklistTemplate

logger = logging.getLogger(__name__)


# NIH Checklist Templates
NIH_TEMPLATES = [
    {
        "funder": "NIH",
        "mechanism": "R01",
        "name": "NIH R01 Application Checklist",
        "description": "Comprehensive checklist for NIH R01 grant applications",
        "items": [
            # Administrative Items
            {
                "id": "nih-r01-001",
                "title": "Verify eRA Commons account is active",
                "description": "Ensure PI and all key personnel have active eRA Commons accounts",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": [],
            },
            {
                "id": "nih-r01-002",
                "title": "Obtain institutional signature approval",
                "description": "Get authorized organizational representative (AOR) approval",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": [],
            },
            {
                "id": "nih-r01-003",
                "title": "Confirm FOA requirements and deadline",
                "description": "Review Funding Opportunity Announcement for specific requirements",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": [],
            },
            # Scientific Documents
            {
                "id": "nih-r01-004",
                "title": "Complete Specific Aims page (1 page)",
                "description": "Draft specific aims with clear objectives and hypothesis",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nih-r01-003"],
            },
            {
                "id": "nih-r01-005",
                "title": "Complete Research Strategy - Significance",
                "description": "Write significance section explaining importance of the work",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nih-r01-004"],
            },
            {
                "id": "nih-r01-006",
                "title": "Complete Research Strategy - Innovation",
                "description": "Describe innovative aspects of the proposed research",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nih-r01-004"],
            },
            {
                "id": "nih-r01-007",
                "title": "Complete Research Strategy - Approach",
                "description": "Detail the research methodology and experimental design",
                "required": True,
                "weight": 3.0,
                "category": "scientific",
                "dependencies": ["nih-r01-004"],
            },
            {
                "id": "nih-r01-008",
                "title": "Verify Research Strategy page limit (12 pages)",
                "description": "Ensure combined Significance, Innovation, Approach is within limit",
                "required": True,
                "weight": 1.0,
                "category": "compliance",
                "dependencies": ["nih-r01-005", "nih-r01-006", "nih-r01-007"],
            },
            # Personnel Documents
            {
                "id": "nih-r01-009",
                "title": "Prepare NIH Biosketch for PI",
                "description": "Complete 5-page NIH format biosketch for principal investigator",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nih-r01-010",
                "title": "Prepare NIH Biosketches for Key Personnel",
                "description": "Collect biosketches from all co-investigators and key personnel",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nih-r01-011",
                "title": "Prepare Other Support documents",
                "description": "Complete current and pending support for PI and key personnel",
                "required": True,
                "weight": 1.0,
                "category": "personnel",
                "dependencies": [],
            },
            # Budget
            {
                "id": "nih-r01-012",
                "title": "Prepare detailed budget (Year 1)",
                "description": "Complete SF424 R&R budget form for first year",
                "required": True,
                "weight": 2.0,
                "category": "budget",
                "dependencies": [],
            },
            {
                "id": "nih-r01-013",
                "title": "Prepare budget for remaining years",
                "description": "Complete budget projections for years 2-5",
                "required": True,
                "weight": 1.5,
                "category": "budget",
                "dependencies": ["nih-r01-012"],
            },
            {
                "id": "nih-r01-014",
                "title": "Write budget justification",
                "description": "Provide detailed justification for all budget items",
                "required": True,
                "weight": 1.5,
                "category": "budget",
                "dependencies": ["nih-r01-012", "nih-r01-013"],
            },
            # Compliance Documents
            {
                "id": "nih-r01-015",
                "title": "Prepare Human Subjects section (if applicable)",
                "description": "Complete protection of human subjects documentation",
                "required": False,
                "weight": 1.5,
                "category": "compliance",
                "dependencies": [],
            },
            {
                "id": "nih-r01-016",
                "title": "Prepare Vertebrate Animals section (if applicable)",
                "description": "Complete vertebrate animals justification if using animals",
                "required": False,
                "weight": 1.5,
                "category": "compliance",
                "dependencies": [],
            },
            {
                "id": "nih-r01-017",
                "title": "Complete Resource Sharing Plan",
                "description": "Describe data and resource sharing plans",
                "required": True,
                "weight": 1.0,
                "category": "compliance",
                "dependencies": [],
            },
            {
                "id": "nih-r01-018",
                "title": "Complete Authentication of Key Biological Resources",
                "description": "Describe plans for authenticating biological resources",
                "required": True,
                "weight": 1.0,
                "category": "compliance",
                "dependencies": [],
            },
            # Supporting Documents
            {
                "id": "nih-r01-019",
                "title": "Prepare Facilities & Other Resources",
                "description": "Describe available facilities, equipment, and resources",
                "required": True,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nih-r01-020",
                "title": "Prepare Equipment document",
                "description": "List major equipment to be used",
                "required": True,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nih-r01-021",
                "title": "Obtain Letters of Support",
                "description": "Collect letters from collaborators and consultants",
                "required": False,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            # Review and Submit
            {
                "id": "nih-r01-022",
                "title": "Complete internal scientific review",
                "description": "Have colleagues review scientific content",
                "required": True,
                "weight": 2.0,
                "category": "review",
                "dependencies": ["nih-r01-004", "nih-r01-005", "nih-r01-006", "nih-r01-007"],
            },
            {
                "id": "nih-r01-023",
                "title": "Complete sponsored programs review",
                "description": "Submit to institutional grants office for review",
                "required": True,
                "weight": 1.5,
                "category": "review",
                "dependencies": ["nih-r01-014"],
            },
            {
                "id": "nih-r01-024",
                "title": "Address all internal review comments",
                "description": "Incorporate feedback from internal reviews",
                "required": True,
                "weight": 1.5,
                "category": "review",
                "dependencies": ["nih-r01-022", "nih-r01-023"],
            },
            {
                "id": "nih-r01-025",
                "title": "Final compliance check",
                "description": "Verify all documents meet NIH formatting requirements",
                "required": True,
                "weight": 1.0,
                "category": "compliance",
                "dependencies": ["nih-r01-024"],
            },
            {
                "id": "nih-r01-026",
                "title": "Submit application via Grants.gov",
                "description": "Submit final application package before deadline",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": ["nih-r01-025"],
            },
        ],
    },
    {
        "funder": "NIH",
        "mechanism": "R21",
        "name": "NIH R21 Exploratory Grant Checklist",
        "description": "Checklist for NIH R21 exploratory/developmental research grant",
        "items": [
            {
                "id": "nih-r21-001",
                "title": "Verify R21 eligibility",
                "description": "Confirm project is exploratory/developmental and doesn't require preliminary data",
                "required": True,
                "weight": 1.5,
                "category": "administrative",
                "dependencies": [],
            },
            {
                "id": "nih-r21-002",
                "title": "Complete Specific Aims page (1 page)",
                "description": "Draft specific aims focused on exploratory objectives",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nih-r21-001"],
            },
            {
                "id": "nih-r21-003",
                "title": "Complete Research Strategy (6 pages max)",
                "description": "Write Significance, Innovation, and Approach sections",
                "required": True,
                "weight": 3.0,
                "category": "scientific",
                "dependencies": ["nih-r21-002"],
            },
            {
                "id": "nih-r21-004",
                "title": "Prepare NIH Biosketch for PI",
                "description": "Complete 5-page NIH format biosketch",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nih-r21-005",
                "title": "Prepare detailed budget (2-year max)",
                "description": "Complete budget for up to 2 years ($275K max total)",
                "required": True,
                "weight": 2.0,
                "category": "budget",
                "dependencies": [],
            },
            {
                "id": "nih-r21-006",
                "title": "Write budget justification",
                "description": "Justify all proposed expenditures",
                "required": True,
                "weight": 1.5,
                "category": "budget",
                "dependencies": ["nih-r21-005"],
            },
            {
                "id": "nih-r21-007",
                "title": "Prepare Facilities & Other Resources",
                "description": "Describe available facilities and resources",
                "required": True,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nih-r21-008",
                "title": "Complete internal review",
                "description": "Have colleagues review application",
                "required": True,
                "weight": 2.0,
                "category": "review",
                "dependencies": ["nih-r21-003"],
            },
            {
                "id": "nih-r21-009",
                "title": "Submit via Grants.gov",
                "description": "Submit final application before deadline",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": ["nih-r21-008"],
            },
        ],
    },
]


# NSF Checklist Templates
NSF_TEMPLATES = [
    {
        "funder": "NSF",
        "mechanism": "Standard",
        "name": "NSF Standard Grant Checklist",
        "description": "Comprehensive checklist for NSF standard research grants",
        "items": [
            # Administrative
            {
                "id": "nsf-std-001",
                "title": "Verify NSF ID and institutional registration",
                "description": "Ensure PI has NSF ID and institution is registered in Research.gov",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": [],
            },
            {
                "id": "nsf-std-002",
                "title": "Review program solicitation requirements",
                "description": "Read program solicitation and NSF PAPPG for requirements",
                "required": True,
                "weight": 1.5,
                "category": "administrative",
                "dependencies": [],
            },
            # Scientific Documents
            {
                "id": "nsf-std-003",
                "title": "Complete Project Summary (1 page)",
                "description": "Write overview, intellectual merit, and broader impacts paragraphs",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nsf-std-002"],
            },
            {
                "id": "nsf-std-004",
                "title": "Complete Project Description (15 pages max)",
                "description": "Write comprehensive project description with all required elements",
                "required": True,
                "weight": 3.0,
                "category": "scientific",
                "dependencies": ["nsf-std-003"],
            },
            {
                "id": "nsf-std-005",
                "title": "Address Intellectual Merit criterion",
                "description": "Clearly articulate intellectual merit throughout proposal",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nsf-std-004"],
            },
            {
                "id": "nsf-std-006",
                "title": "Address Broader Impacts criterion",
                "description": "Describe broader impacts with specific, measurable activities",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nsf-std-004"],
            },
            {
                "id": "nsf-std-007",
                "title": "Prepare References Cited",
                "description": "Compile complete reference list (no page limit)",
                "required": True,
                "weight": 1.0,
                "category": "documents",
                "dependencies": ["nsf-std-004"],
            },
            # Personnel
            {
                "id": "nsf-std-008",
                "title": "Prepare Biographical Sketch for PI (3 pages)",
                "description": "Complete NSF format biosketch with required sections",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nsf-std-009",
                "title": "Prepare Biographical Sketches for Co-PIs",
                "description": "Collect biosketches from all co-principal investigators",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nsf-std-010",
                "title": "Complete Current and Pending Support",
                "description": "List all current and pending support using NSF format",
                "required": True,
                "weight": 1.0,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nsf-std-011",
                "title": "Complete Collaborators and Other Affiliations",
                "description": "List collaborators following NSF COA template",
                "required": True,
                "weight": 1.0,
                "category": "personnel",
                "dependencies": [],
            },
            # Budget
            {
                "id": "nsf-std-012",
                "title": "Prepare detailed budget",
                "description": "Complete budget using Research.gov budget module",
                "required": True,
                "weight": 2.0,
                "category": "budget",
                "dependencies": [],
            },
            {
                "id": "nsf-std-013",
                "title": "Write budget justification (5 pages max)",
                "description": "Justify all budget items in detail",
                "required": True,
                "weight": 1.5,
                "category": "budget",
                "dependencies": ["nsf-std-012"],
            },
            # Supporting Documents
            {
                "id": "nsf-std-014",
                "title": "Prepare Facilities, Equipment, and Other Resources",
                "description": "Describe institutional resources available for the project",
                "required": True,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nsf-std-015",
                "title": "Complete Data Management Plan (2 pages)",
                "description": "Describe how data will be managed and shared",
                "required": True,
                "weight": 1.5,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nsf-std-016",
                "title": "Complete Postdoctoral Mentoring Plan (if applicable)",
                "description": "Describe mentoring activities for postdocs",
                "required": False,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nsf-std-017",
                "title": "Obtain Letters of Collaboration (if applicable)",
                "description": "Collect letters from collaborators (single sentence format)",
                "required": False,
                "weight": 1.0,
                "category": "documents",
                "dependencies": [],
            },
            # Review and Submit
            {
                "id": "nsf-std-018",
                "title": "Conduct internal scientific review",
                "description": "Have colleagues review proposal against review criteria",
                "required": True,
                "weight": 2.0,
                "category": "review",
                "dependencies": ["nsf-std-004", "nsf-std-005", "nsf-std-006"],
            },
            {
                "id": "nsf-std-019",
                "title": "Complete sponsored programs review",
                "description": "Submit to institutional grants office",
                "required": True,
                "weight": 1.5,
                "category": "review",
                "dependencies": ["nsf-std-013"],
            },
            {
                "id": "nsf-std-020",
                "title": "Address review comments",
                "description": "Incorporate feedback from reviews",
                "required": True,
                "weight": 1.5,
                "category": "review",
                "dependencies": ["nsf-std-018", "nsf-std-019"],
            },
            {
                "id": "nsf-std-021",
                "title": "Final compliance check",
                "description": "Verify compliance with PAPPG formatting requirements",
                "required": True,
                "weight": 1.0,
                "category": "compliance",
                "dependencies": ["nsf-std-020"],
            },
            {
                "id": "nsf-std-022",
                "title": "Submit via Research.gov",
                "description": "Submit final proposal before deadline",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": ["nsf-std-021"],
            },
        ],
    },
    {
        "funder": "NSF",
        "mechanism": "CAREER",
        "name": "NSF CAREER Award Checklist",
        "description": "Checklist for NSF Faculty Early Career Development (CAREER) Program",
        "items": [
            {
                "id": "nsf-career-001",
                "title": "Verify CAREER eligibility",
                "description": "Confirm tenure-track status and no prior CAREER award",
                "required": True,
                "weight": 2.0,
                "category": "administrative",
                "dependencies": [],
            },
            {
                "id": "nsf-career-002",
                "title": "Obtain department head endorsement letter",
                "description": "Get required letter from department head/chair",
                "required": True,
                "weight": 1.5,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nsf-career-003",
                "title": "Complete Project Summary (1 page)",
                "description": "Summarize integrated research and education plan",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": [],
            },
            {
                "id": "nsf-career-004",
                "title": "Complete Project Description (15 pages)",
                "description": "Present integrated research and education plan",
                "required": True,
                "weight": 3.0,
                "category": "scientific",
                "dependencies": ["nsf-career-003"],
            },
            {
                "id": "nsf-career-005",
                "title": "Integrate research and education activities",
                "description": "Clearly show integration of research and education",
                "required": True,
                "weight": 2.5,
                "category": "scientific",
                "dependencies": ["nsf-career-004"],
            },
            {
                "id": "nsf-career-006",
                "title": "Present career development plan",
                "description": "Outline 5-year career development trajectory",
                "required": True,
                "weight": 2.0,
                "category": "scientific",
                "dependencies": ["nsf-career-004"],
            },
            {
                "id": "nsf-career-007",
                "title": "Complete Biographical Sketch (3 pages)",
                "description": "Prepare NSF format biosketch",
                "required": True,
                "weight": 1.5,
                "category": "personnel",
                "dependencies": [],
            },
            {
                "id": "nsf-career-008",
                "title": "Prepare 5-year budget",
                "description": "Complete budget for 5-year project ($400K-$500K minimum)",
                "required": True,
                "weight": 2.0,
                "category": "budget",
                "dependencies": [],
            },
            {
                "id": "nsf-career-009",
                "title": "Write budget justification",
                "description": "Justify all budget items",
                "required": True,
                "weight": 1.5,
                "category": "budget",
                "dependencies": ["nsf-career-008"],
            },
            {
                "id": "nsf-career-010",
                "title": "Complete Data Management Plan",
                "description": "Describe data management and sharing",
                "required": True,
                "weight": 1.5,
                "category": "documents",
                "dependencies": [],
            },
            {
                "id": "nsf-career-011",
                "title": "Conduct internal review",
                "description": "Have mentors and colleagues review proposal",
                "required": True,
                "weight": 2.0,
                "category": "review",
                "dependencies": ["nsf-career-004", "nsf-career-005", "nsf-career-006"],
            },
            {
                "id": "nsf-career-012",
                "title": "Submit via Research.gov",
                "description": "Submit by third Monday in July deadline",
                "required": True,
                "weight": 1.0,
                "category": "administrative",
                "dependencies": ["nsf-career-011"],
            },
        ],
    },
]


# All templates combined
ALL_TEMPLATES = NIH_TEMPLATES + NSF_TEMPLATES


async def seed_checklist_templates():
    """Seed initial checklist templates for common funders."""
    async with get_async_session() as session:
        # Check if templates already exist
        from sqlalchemy import select, func
        result = await session.execute(
            select(func.count()).select_from(ChecklistTemplate).where(
                ChecklistTemplate.is_system == True
            )
        )
        existing_count = result.scalar()

        if existing_count > 0:
            logger.info(f"Checklist templates already seeded ({existing_count} templates exist)")
            return

        # Create templates
        for template_data in ALL_TEMPLATES:
            template = ChecklistTemplate(
                id=uuid4(),
                funder=template_data["funder"],
                mechanism=template_data["mechanism"],
                name=template_data["name"],
                description=template_data["description"],
                items=template_data["items"],
                is_system=True,
                created_by=None,
            )
            session.add(template)

        await session.commit()
        logger.info(f"Seeded {len(ALL_TEMPLATES)} checklist templates")


async def reset_and_seed_checklist_templates():
    """Delete existing system templates and reseed."""
    async with get_async_session() as session:
        from sqlalchemy import delete

        # Delete existing system templates
        await session.execute(
            delete(ChecklistTemplate).where(ChecklistTemplate.is_system == True)
        )
        await session.commit()

        logger.info("Deleted existing system checklist templates")

    # Now seed fresh templates
    await seed_checklist_templates()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_checklist_templates())
