"""
Seed initial template categories and system templates.
Run this once during initial setup.
"""
import asyncio
import logging
from uuid import uuid4

from backend.database import get_async_session
from backend.models import Template, TemplateCategory

logger = logging.getLogger(__name__)

# Initial categories
CATEGORIES = [
    {"name": "Specific Aims", "description": "Templates for specific aims pages", "display_order": 1},
    {"name": "Significance", "description": "Templates for significance sections", "display_order": 2},
    {"name": "Innovation", "description": "Templates for innovation sections", "display_order": 3},
    {"name": "Approach", "description": "Templates for research approach sections", "display_order": 4},
    {"name": "Abstract", "description": "Templates for project abstracts", "display_order": 5},
    {"name": "Budget Justification", "description": "Templates for budget narratives", "display_order": 6},
    {"name": "Biographical Sketch", "description": "Templates for biosketch sections", "display_order": 7},
    {"name": "Letters", "description": "Templates for support letters and collaboration letters", "display_order": 8},
]

# System templates
SYSTEM_TEMPLATES = [
    {
        "category": "Specific Aims",
        "title": "NIH R01 Specific Aims",
        "description": "Standard format for NIH R01 specific aims page",
        "content": """{{project_title}}

SPECIFIC AIMS

{{background_paragraph}}

The long-term goal of our research is {{long_term_goal}}. The objective of this application is {{objective}}. Our central hypothesis is {{central_hypothesis}}. The rationale for the proposed research is {{rationale}}.

We will test our central hypothesis by pursuing the following specific aims:

Aim 1: {{aim1_title}}
{{aim1_description}}

Aim 2: {{aim2_title}}
{{aim2_description}}

Aim 3: {{aim3_title}}
{{aim3_description}}

The expected outcomes of this research are {{expected_outcomes}}. The results will have a positive impact by {{positive_impact}}.
""",
        "variables": [
            {"name": "project_title", "type": "text", "description": "Title of the project"},
            {"name": "background_paragraph", "type": "text", "description": "Background context paragraph"},
            {"name": "long_term_goal", "type": "text", "description": "Long-term research goal"},
            {"name": "objective", "type": "text", "description": "Specific objective of this application"},
            {"name": "central_hypothesis", "type": "text", "description": "Central hypothesis statement"},
            {"name": "rationale", "type": "text", "description": "Rationale for the research"},
            {"name": "aim1_title", "type": "text", "description": "Title for Aim 1"},
            {"name": "aim1_description", "type": "text", "description": "Description of Aim 1"},
            {"name": "aim2_title", "type": "text", "description": "Title for Aim 2"},
            {"name": "aim2_description", "type": "text", "description": "Description of Aim 2"},
            {"name": "aim3_title", "type": "text", "description": "Title for Aim 3"},
            {"name": "aim3_description", "type": "text", "description": "Description of Aim 3"},
            {"name": "expected_outcomes", "type": "text", "description": "Expected outcomes"},
            {"name": "positive_impact", "type": "text", "description": "Positive impact statement"},
        ],
    },
    {
        "category": "Abstract",
        "title": "NIH Project Summary/Abstract",
        "description": "Standard NIH project summary format",
        "content": """PROJECT SUMMARY/ABSTRACT

{{background_significance}}

The objective of this {{grant_type}} application is {{objective}}. Our central hypothesis is {{hypothesis}}, based on {{preliminary_data}}.

In Aim 1, we will {{aim1_summary}}. In Aim 2, we will {{aim2_summary}}. {{aim3_summary}}

This research is innovative because {{innovation}}. The proposed research is significant because {{significance}}.

At the completion of this project, we expect {{expected_outcomes}}. These results will {{impact_statement}}.
""",
        "variables": [
            {"name": "background_significance", "type": "text", "description": "Background and significance"},
            {"name": "grant_type", "type": "text", "description": "Type of grant (e.g., R01, R21)"},
            {"name": "objective", "type": "text", "description": "Main objective"},
            {"name": "hypothesis", "type": "text", "description": "Central hypothesis"},
            {"name": "preliminary_data", "type": "text", "description": "Basis for hypothesis"},
            {"name": "aim1_summary", "type": "text", "description": "Brief Aim 1 summary"},
            {"name": "aim2_summary", "type": "text", "description": "Brief Aim 2 summary"},
            {"name": "aim3_summary", "type": "text", "description": "Brief Aim 3 summary (optional)"},
            {"name": "innovation", "type": "text", "description": "Innovation statement"},
            {"name": "significance", "type": "text", "description": "Significance statement"},
            {"name": "expected_outcomes", "type": "text", "description": "Expected outcomes"},
            {"name": "impact_statement", "type": "text", "description": "Impact statement"},
        ],
    },
    {
        "category": "Budget Justification",
        "title": "Personnel Budget Justification",
        "description": "Template for personnel budget narrative",
        "content": """BUDGET JUSTIFICATION - PERSONNEL

Principal Investigator: {{pi_name}} ({{pi_effort}}% effort, {{pi_months}} calendar months)
{{pi_role_description}}

Co-Investigator: {{coi_name}} ({{coi_effort}}% effort, {{coi_months}} calendar months)
{{coi_role_description}}

Research Scientist/Postdoctoral Fellow: {{postdoc_name}} ({{postdoc_effort}}% effort)
{{postdoc_role_description}}

Graduate Research Assistant: {{gra_name}} ({{gra_effort}}% effort)
{{gra_role_description}}

Research Technician: {{tech_name}} ({{tech_effort}}% effort)
{{tech_role_description}}
""",
        "variables": [
            {"name": "pi_name", "type": "text", "description": "PI name"},
            {"name": "pi_effort", "type": "number", "description": "PI effort percentage"},
            {"name": "pi_months", "type": "number", "description": "PI calendar months"},
            {"name": "pi_role_description", "type": "text", "description": "PI role description"},
            {"name": "coi_name", "type": "text", "description": "Co-I name"},
            {"name": "coi_effort", "type": "number", "description": "Co-I effort percentage"},
            {"name": "coi_months", "type": "number", "description": "Co-I calendar months"},
            {"name": "coi_role_description", "type": "text", "description": "Co-I role description"},
            {"name": "postdoc_name", "type": "text", "description": "Postdoc name or TBN"},
            {"name": "postdoc_effort", "type": "number", "description": "Postdoc effort percentage"},
            {"name": "postdoc_role_description", "type": "text", "description": "Postdoc role description"},
            {"name": "gra_name", "type": "text", "description": "GRA name or TBN"},
            {"name": "gra_effort", "type": "number", "description": "GRA effort percentage"},
            {"name": "gra_role_description", "type": "text", "description": "GRA role description"},
            {"name": "tech_name", "type": "text", "description": "Technician name or TBN"},
            {"name": "tech_effort", "type": "number", "description": "Technician effort percentage"},
            {"name": "tech_role_description", "type": "text", "description": "Technician role description"},
        ],
    },
    {
        "category": "Letters",
        "title": "Letter of Support",
        "description": "Template for letters of support from collaborators",
        "content": """{{date}}

{{recipient_name}}
{{recipient_title}}
{{recipient_organization}}
{{recipient_address}}

RE: Letter of Support for {{project_title}}

Dear {{recipient_salutation}},

I am writing to express my strong support for {{pi_name}}'s proposed project titled "{{project_title}}."

{{collaboration_description}}

Our {{organization_name}} is committed to supporting this research by {{support_details}}. This collaboration will {{collaboration_benefits}}.

{{pi_name}} has demonstrated {{pi_qualifications}}. I am confident that this project will {{expected_impact}}.

I enthusiastically support this application and look forward to our continued collaboration.

Sincerely,

{{signer_name}}
{{signer_title}}
{{signer_organization}}
""",
        "variables": [
            {"name": "date", "type": "date", "description": "Date of the letter"},
            {"name": "recipient_name", "type": "text", "description": "Recipient's full name"},
            {"name": "recipient_title", "type": "text", "description": "Recipient's title"},
            {"name": "recipient_organization", "type": "text", "description": "Recipient's organization"},
            {"name": "recipient_address", "type": "text", "description": "Recipient's address"},
            {"name": "project_title", "type": "text", "description": "Title of the project"},
            {"name": "recipient_salutation", "type": "text", "description": "Salutation (e.g., Dr. Smith)"},
            {"name": "pi_name", "type": "text", "description": "Principal Investigator's name"},
            {"name": "collaboration_description", "type": "text", "description": "Description of the collaboration"},
            {"name": "organization_name", "type": "text", "description": "Your organization's name"},
            {"name": "support_details", "type": "text", "description": "Details of support being provided"},
            {"name": "collaboration_benefits", "type": "text", "description": "Benefits of the collaboration"},
            {"name": "pi_qualifications", "type": "text", "description": "PI's qualifications"},
            {"name": "expected_impact", "type": "text", "description": "Expected impact of the project"},
            {"name": "signer_name", "type": "text", "description": "Your name"},
            {"name": "signer_title", "type": "text", "description": "Your title"},
            {"name": "signer_organization", "type": "text", "description": "Your organization"},
        ],
    },
    {
        "category": "Significance",
        "title": "NIH Significance Section",
        "description": "Template for NIH grant significance section",
        "content": """SIGNIFICANCE

{{opening_statement}}

Importance of the Problem
{{problem_importance}}

Current State of Knowledge
{{current_knowledge}}

Gaps in Knowledge
{{knowledge_gaps}}

How This Project Addresses the Gap
{{addressing_gaps}}

Impact on the Field
{{field_impact}}

Public Health Relevance
{{public_health_relevance}}
""",
        "variables": [
            {"name": "opening_statement", "type": "text", "description": "Opening statement about significance"},
            {"name": "problem_importance", "type": "text", "description": "Why the problem is important"},
            {"name": "current_knowledge", "type": "text", "description": "Current state of knowledge"},
            {"name": "knowledge_gaps", "type": "text", "description": "Gaps in current knowledge"},
            {"name": "addressing_gaps", "type": "text", "description": "How project addresses gaps"},
            {"name": "field_impact", "type": "text", "description": "Impact on the field"},
            {"name": "public_health_relevance", "type": "text", "description": "Relevance to public health"},
        ],
    },
    {
        "category": "Innovation",
        "title": "NIH Innovation Section",
        "description": "Template for NIH grant innovation section",
        "content": """INNOVATION

{{innovation_overview}}

Conceptual Innovation
{{conceptual_innovation}}

Technical Innovation
{{technical_innovation}}

Methodological Innovation
{{methodological_innovation}}

Advantages Over Current Approaches
{{advantages}}

Transformative Potential
{{transformative_potential}}
""",
        "variables": [
            {"name": "innovation_overview", "type": "text", "description": "Overview of innovation"},
            {"name": "conceptual_innovation", "type": "text", "description": "New concepts or theories"},
            {"name": "technical_innovation", "type": "text", "description": "Technical innovations"},
            {"name": "methodological_innovation", "type": "text", "description": "New methods or approaches"},
            {"name": "advantages", "type": "text", "description": "Advantages over existing approaches"},
            {"name": "transformative_potential", "type": "text", "description": "Potential to transform the field"},
        ],
    },
]


async def seed_templates():
    """Seed initial categories and system templates."""
    async with get_async_session() as session:
        # Create categories
        category_map = {}
        for cat_data in CATEGORIES:
            category = TemplateCategory(
                id=uuid4(),
                name=cat_data["name"],
                description=cat_data["description"],
                display_order=cat_data["display_order"],
            )
            session.add(category)
            category_map[cat_data["name"]] = category.id

        await session.flush()

        # Create system templates
        for tmpl_data in SYSTEM_TEMPLATES:
            template = Template(
                id=uuid4(),
                user_id=None,  # System templates have no user
                category_id=category_map.get(tmpl_data["category"]),
                title=tmpl_data["title"],
                description=tmpl_data["description"],
                content=tmpl_data["content"],
                variables=tmpl_data["variables"],
                is_public=True,
                is_system=True,
            )
            session.add(template)

        await session.commit()
        logger.info(f"Seeded {len(CATEGORIES)} categories and {len(SYSTEM_TEMPLATES)} system templates")


if __name__ == "__main__":
    asyncio.run(seed_templates())
