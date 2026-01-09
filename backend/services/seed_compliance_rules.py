"""
Seed Data for Compliance Rules
Pre-defined compliance rules for major funders (NIH, NSF).
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.compliance import ComplianceRule

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# NIH Compliance Rules
# =============================================================================

NIH_GENERAL_RULES: List[Dict[str, Any]] = [
    {
        "type": "font_size",
        "name": "NIH Font Size Requirement",
        "description": "NIH requires at least 11-point font for all text",
        "params": {
            "min_size": 11,
            "allowed_fonts": [
                "Arial",
                "Georgia",
                "Helvetica",
                "Palatino Linotype",
                "Times New Roman",
            ],
        },
        "severity": "error",
        "message": "NIH requires at least 11-point font (Arial, Georgia, Helvetica, Palatino Linotype, or Times New Roman)",
    },
    {
        "type": "margin",
        "name": "NIH Margin Requirement",
        "description": "NIH requires at least 0.5 inch margins on all sides",
        "params": {
            "min_margin": 0.5,
        },
        "severity": "error",
        "message": "NIH requires at least 0.5 inch margins on all sides",
    },
    {
        "type": "line_spacing",
        "name": "NIH Line Spacing Guideline",
        "description": "NIH recommends no more than 6 lines per vertical inch",
        "params": {
            "min_spacing": 1.0,
        },
        "severity": "warning",
        "message": "NIH recommends line spacing that results in no more than 6 lines per vertical inch",
    },
]

NIH_R01_RULES: List[Dict[str, Any]] = [
    {
        "type": "page_limit",
        "name": "R01 Research Strategy Page Limit",
        "description": "R01 research strategy is limited to 12 pages",
        "params": {
            "max_pages": 12,
        },
        "severity": "error",
        "message": "R01 Research Strategy section must not exceed 12 pages",
        "document_types": ["research_strategy"],
    },
    {
        "type": "page_limit",
        "name": "R01 Specific Aims Page Limit",
        "description": "Specific Aims is limited to 1 page",
        "params": {
            "max_pages": 1,
        },
        "severity": "error",
        "message": "Specific Aims section must not exceed 1 page",
        "document_types": ["specific_aims"],
    },
    {
        "type": "required_section",
        "name": "Specific Aims Required",
        "description": "Specific Aims section is required",
        "params": {
            "section_name": "Specific Aims",
            "patterns": ["Specific Aims", "SPECIFIC AIMS", "specific aims"],
        },
        "severity": "error",
        "document_types": ["specific_aims", "research_strategy"],
    },
    {
        "type": "required_section",
        "name": "Significance Required",
        "description": "Significance section is required in Research Strategy",
        "params": {
            "section_name": "Significance",
            "patterns": ["Significance", "SIGNIFICANCE", "1. Significance", "A. Significance"],
        },
        "severity": "error",
        "document_types": ["research_strategy"],
    },
    {
        "type": "required_section",
        "name": "Innovation Required",
        "description": "Innovation section is required in Research Strategy",
        "params": {
            "section_name": "Innovation",
            "patterns": ["Innovation", "INNOVATION", "2. Innovation", "B. Innovation"],
        },
        "severity": "error",
        "document_types": ["research_strategy"],
    },
    {
        "type": "required_section",
        "name": "Approach Required",
        "description": "Approach section is required in Research Strategy",
        "params": {
            "section_name": "Approach",
            "patterns": ["Approach", "APPROACH", "3. Approach", "C. Approach", "Research Design"],
        },
        "severity": "error",
        "document_types": ["research_strategy"],
    },
    {
        "type": "page_limit",
        "name": "R01 Biosketch Page Limit",
        "description": "Each biosketch is limited to 5 pages",
        "params": {
            "max_pages": 5,
        },
        "severity": "error",
        "message": "Biosketch must not exceed 5 pages",
        "document_types": ["biosketch"],
    },
    {
        "type": "budget_arithmetic",
        "name": "R01 Budget Validation",
        "description": "Budget totals must be arithmetically correct",
        "params": {
            "max_total": 500000,  # Direct costs per year limit for standard R01
            "modular_budget": False,
        },
        "severity": "error",
        "document_types": ["budget"],
    },
] + NIH_GENERAL_RULES

NIH_R21_RULES: List[Dict[str, Any]] = [
    {
        "type": "page_limit",
        "name": "R21 Research Strategy Page Limit",
        "description": "R21 research strategy is limited to 6 pages",
        "params": {
            "max_pages": 6,
        },
        "severity": "error",
        "message": "R21 Research Strategy section must not exceed 6 pages",
        "document_types": ["research_strategy"],
    },
    {
        "type": "page_limit",
        "name": "R21 Specific Aims Page Limit",
        "description": "Specific Aims is limited to 1 page",
        "params": {
            "max_pages": 1,
        },
        "severity": "error",
        "message": "Specific Aims section must not exceed 1 page",
        "document_types": ["specific_aims"],
    },
    {
        "type": "required_section",
        "name": "Specific Aims Required",
        "description": "Specific Aims section is required",
        "params": {
            "section_name": "Specific Aims",
            "patterns": ["Specific Aims", "SPECIFIC AIMS"],
        },
        "severity": "error",
        "document_types": ["specific_aims", "research_strategy"],
    },
    {
        "type": "budget_arithmetic",
        "name": "R21 Budget Validation",
        "description": "R21 is limited to $275,000 total over 2 years",
        "params": {
            "max_total": 275000,  # Total costs over 2-year period
        },
        "severity": "error",
        "document_types": ["budget"],
    },
    {
        "type": "page_limit",
        "name": "R21 Biosketch Page Limit",
        "description": "Each biosketch is limited to 5 pages",
        "params": {
            "max_pages": 5,
        },
        "severity": "error",
        "document_types": ["biosketch"],
    },
] + NIH_GENERAL_RULES

NIH_K99_R00_RULES: List[Dict[str, Any]] = [
    {
        "type": "page_limit",
        "name": "K99/R00 Research Strategy Page Limit",
        "description": "K99/R00 research strategy is limited to 12 pages",
        "params": {
            "max_pages": 12,
        },
        "severity": "error",
        "message": "K99/R00 Research Strategy section must not exceed 12 pages",
        "document_types": ["research_strategy"],
    },
    {
        "type": "page_limit",
        "name": "K99/R00 Specific Aims Page Limit",
        "description": "Specific Aims is limited to 1 page",
        "params": {
            "max_pages": 1,
        },
        "severity": "error",
        "document_types": ["specific_aims"],
    },
    {
        "type": "required_section",
        "name": "Career Development Plan Required",
        "description": "Career development/training plan is required",
        "params": {
            "section_name": "Career Development Plan",
            "patterns": [
                "Career Development",
                "Training Plan",
                "Career Goals",
                "Training Activities",
            ],
        },
        "severity": "error",
        "document_types": ["research_strategy"],
    },
    {
        "type": "page_limit",
        "name": "K99/R00 Biosketch Page Limit",
        "description": "Each biosketch is limited to 5 pages",
        "params": {
            "max_pages": 5,
        },
        "severity": "error",
        "document_types": ["biosketch"],
    },
] + NIH_GENERAL_RULES


# =============================================================================
# NSF Compliance Rules
# =============================================================================

NSF_GENERAL_RULES: List[Dict[str, Any]] = [
    {
        "type": "font_size",
        "name": "NSF Font Size Requirement",
        "description": "NSF requires at least 11-point font",
        "params": {
            "min_size": 11,
            "allowed_fonts": [
                "Arial",
                "Computer Modern",
                "Georgia",
                "Helvetica",
                "Palatino",
                "Times New Roman",
            ],
        },
        "severity": "error",
        "message": "NSF requires at least 11-point font for text in the proposal",
    },
    {
        "type": "margin",
        "name": "NSF Margin Requirement",
        "description": "NSF requires at least 1 inch margins on all sides",
        "params": {
            "min_margin": 1.0,
        },
        "severity": "error",
        "message": "NSF requires at least 1 inch margins on all sides",
    },
    {
        "type": "line_spacing",
        "name": "NSF Line Spacing Requirement",
        "description": "NSF requires no more than 6 lines per inch",
        "params": {
            "min_spacing": 1.0,
        },
        "severity": "warning",
        "message": "NSF requires spacing resulting in no more than 6 lines per inch",
    },
    {
        "type": "page_limit",
        "name": "NSF Biographical Sketch Page Limit",
        "description": "NSF biographical sketch is limited to 3 pages",
        "params": {
            "max_pages": 3,
        },
        "severity": "error",
        "message": "NSF Biographical Sketch must not exceed 3 pages",
        "document_types": ["biosketch"],
    },
]

NSF_STANDARD_RULES: List[Dict[str, Any]] = [
    {
        "type": "page_limit",
        "name": "NSF Project Description Page Limit",
        "description": "NSF project description is limited to 15 pages",
        "params": {
            "max_pages": 15,
        },
        "severity": "error",
        "message": "NSF Project Description must not exceed 15 pages",
        "document_types": ["research_strategy", "project_narrative"],
    },
    {
        "type": "page_limit",
        "name": "NSF Project Summary Page Limit",
        "description": "NSF project summary is limited to 1 page",
        "params": {
            "max_pages": 1,
        },
        "severity": "error",
        "message": "NSF Project Summary must not exceed 1 page",
        "document_types": ["abstract"],
    },
    {
        "type": "required_section",
        "name": "Intellectual Merit Required",
        "description": "Project description must address intellectual merit",
        "params": {
            "section_name": "Intellectual Merit",
            "patterns": ["Intellectual Merit", "INTELLECTUAL MERIT"],
        },
        "severity": "error",
        "document_types": ["research_strategy", "project_narrative", "abstract"],
    },
    {
        "type": "required_section",
        "name": "Broader Impacts Required",
        "description": "Project description must address broader impacts",
        "params": {
            "section_name": "Broader Impacts",
            "patterns": ["Broader Impacts", "BROADER IMPACTS", "Broader Impact"],
        },
        "severity": "error",
        "document_types": ["research_strategy", "project_narrative", "abstract"],
    },
    {
        "type": "page_limit",
        "name": "NSF Data Management Plan Page Limit",
        "description": "NSF data management plan is limited to 2 pages",
        "params": {
            "max_pages": 2,
        },
        "severity": "error",
        "message": "NSF Data Management Plan must not exceed 2 pages",
        "document_types": ["data_management"],
    },
    {
        "type": "page_limit",
        "name": "NSF References Page Limit",
        "description": "NSF references cited has no page limit but should be reasonable",
        "params": {
            "max_pages": 50,  # Soft limit as a sanity check
        },
        "severity": "warning",
        "document_types": ["bibliography"],
    },
    {
        "type": "budget_arithmetic",
        "name": "NSF Budget Validation",
        "description": "Budget totals must be arithmetically correct",
        "params": {},
        "severity": "error",
        "document_types": ["budget"],
    },
] + NSF_GENERAL_RULES

NSF_CAREER_RULES: List[Dict[str, Any]] = [
    {
        "type": "page_limit",
        "name": "CAREER Project Description Page Limit",
        "description": "CAREER project description is limited to 15 pages",
        "params": {
            "max_pages": 15,
        },
        "severity": "error",
        "message": "CAREER Project Description must not exceed 15 pages",
        "document_types": ["research_strategy", "project_narrative"],
    },
    {
        "type": "required_section",
        "name": "Education Plan Required",
        "description": "CAREER proposals must include an education plan",
        "params": {
            "section_name": "Education Plan",
            "patterns": [
                "Education Plan",
                "EDUCATION PLAN",
                "Educational Plan",
                "Education Component",
            ],
        },
        "severity": "error",
        "document_types": ["research_strategy", "project_narrative"],
    },
    {
        "type": "required_section",
        "name": "Integration Plan Required",
        "description": "CAREER proposals must integrate research and education",
        "params": {
            "section_name": "Integration",
            "patterns": [
                "Integration of Research and Education",
                "Research-Education Integration",
                "Integration Plan",
            ],
        },
        "severity": "warning",
        "document_types": ["research_strategy", "project_narrative"],
    },
] + NSF_GENERAL_RULES


# =============================================================================
# Seeding Functions
# =============================================================================

async def seed_compliance_rules(db: AsyncSession, force: bool = False) -> dict:
    """
    Seed the database with default compliance rules.

    Args:
        db: Database session
        force: If True, will update existing rules; if False, skip existing

    Returns:
        Dictionary with counts of created and skipped rules
    """
    results = {"created": 0, "skipped": 0, "updated": 0}

    rule_sets = [
        # NIH Rules
        {
            "funder": "NIH",
            "mechanism": None,
            "name": "NIH General Requirements",
            "description": "General formatting requirements for all NIH grant applications",
            "rules": NIH_GENERAL_RULES,
        },
        {
            "funder": "NIH",
            "mechanism": "R01",
            "name": "NIH R01 Requirements",
            "description": "Compliance requirements for NIH R01 grant applications",
            "rules": NIH_R01_RULES,
        },
        {
            "funder": "NIH",
            "mechanism": "R21",
            "name": "NIH R21 Requirements",
            "description": "Compliance requirements for NIH R21 exploratory/developmental grant applications",
            "rules": NIH_R21_RULES,
        },
        {
            "funder": "NIH",
            "mechanism": "K99/R00",
            "name": "NIH K99/R00 Requirements",
            "description": "Compliance requirements for NIH K99/R00 Pathway to Independence Award applications",
            "rules": NIH_K99_R00_RULES,
        },
        # NSF Rules
        {
            "funder": "NSF",
            "mechanism": None,
            "name": "NSF General Requirements",
            "description": "General formatting requirements for all NSF proposals",
            "rules": NSF_GENERAL_RULES,
        },
        {
            "funder": "NSF",
            "mechanism": "Standard",
            "name": "NSF Standard Grant Requirements",
            "description": "Compliance requirements for standard NSF research proposals",
            "rules": NSF_STANDARD_RULES,
        },
        {
            "funder": "NSF",
            "mechanism": "CAREER",
            "name": "NSF CAREER Award Requirements",
            "description": "Compliance requirements for NSF Faculty Early Career Development (CAREER) Program proposals",
            "rules": NSF_CAREER_RULES,
        },
    ]

    for rule_set_data in rule_sets:
        # Check if rule set already exists
        result = await db.execute(
            select(ComplianceRule).where(
                ComplianceRule.funder == rule_set_data["funder"],
                ComplianceRule.mechanism == rule_set_data["mechanism"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                # Update existing rule set
                existing.name = rule_set_data["name"]
                existing.description = rule_set_data["description"]
                existing.rules = rule_set_data["rules"]
                existing.updated_at = datetime.now(timezone.utc)
                results["updated"] += 1
                logger.info(
                    f"Updated rule set: {rule_set_data['funder']} / {rule_set_data['mechanism'] or 'General'}"
                )
            else:
                results["skipped"] += 1
                logger.info(
                    f"Skipped existing rule set: {rule_set_data['funder']} / {rule_set_data['mechanism'] or 'General'}"
                )
        else:
            # Create new rule set
            rule_set = ComplianceRule(
                id=uuid.uuid4(),
                funder=rule_set_data["funder"],
                mechanism=rule_set_data["mechanism"],
                name=rule_set_data["name"],
                description=rule_set_data["description"],
                rules=rule_set_data["rules"],
                is_active=True,
                is_system=True,
                created_by=None,
            )
            db.add(rule_set)
            results["created"] += 1
            logger.info(
                f"Created rule set: {rule_set_data['funder']} / {rule_set_data['mechanism'] or 'General'}"
            )

    await db.commit()
    logger.info(f"Compliance rules seeding complete: {results}")
    return results


async def get_all_funders_with_rules(db: AsyncSession) -> List[str]:
    """Get list of all funders that have compliance rules."""
    result = await db.execute(
        select(ComplianceRule.funder)
        .where(ComplianceRule.is_active == True)
        .distinct()
    )
    return [row[0] for row in result.fetchall()]


async def get_mechanisms_for_funder(db: AsyncSession, funder: str) -> List[str]:
    """Get list of all mechanisms for a specific funder."""
    result = await db.execute(
        select(ComplianceRule.mechanism)
        .where(
            ComplianceRule.funder == funder,
            ComplianceRule.is_active == True,
            ComplianceRule.mechanism.isnot(None),
        )
        .distinct()
    )
    return [row[0] for row in result.fetchall()]
