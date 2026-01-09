"""
Review Criteria Service
Extracts and maps review criteria from various funding agencies (NIH, NSF, etc.)
to help researchers write better grant applications.
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from backend.models.mechanisms import GrantMechanism
from backend.schemas.writing import (
    CriterionCategory,
    FundingAgency,
    MechanismCriteria,
    ReviewCriterion,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# NIH Standard Review Criteria
# Based on NIH peer review guidelines
# =============================================================================

NIH_CRITERIA: Dict[str, ReviewCriterion] = {
    "significance": ReviewCriterion(
        name="Significance",
        description="Does the project address an important problem or critical barrier to progress in the field? Is there a strong scientific premise for the project?",
        weight=0.25,
        category=CriterionCategory.SCIENTIFIC_MERIT,
        scoring_guidance="Scored 1-9 where 1 is exceptional. Focus on scientific and technical merit, not potential clinical impact alone.",
        common_weaknesses=[
            "Overstated impact without scientific justification",
            "Lack of clear gap in current knowledge",
            "Insufficient discussion of how findings would advance the field",
            "Poor articulation of the problem's importance",
        ],
        tips=[
            "Clearly articulate the gap in current knowledge",
            "Explain how solving this problem will enable future research",
            "Connect to broader scientific goals, not just clinical applications",
            "Use recent literature to support the significance",
        ],
    ),
    "investigators": ReviewCriterion(
        name="Investigator(s)",
        description="Are the PD/PIs, collaborators, and other researchers well suited to the project? Do they have appropriate experience and training?",
        weight=0.20,
        category=CriterionCategory.TEAM,
        scoring_guidance="Evaluate track record, expertise alignment with proposed work, and team composition.",
        common_weaknesses=[
            "Inadequate preliminary data showing feasibility",
            "Lack of key expertise on the team",
            "No evidence of prior collaboration for multi-PI projects",
            "Overly junior team without appropriate mentorship",
        ],
        tips=[
            "Highlight relevant publications and prior work",
            "Show preliminary data that demonstrates feasibility",
            "Address any gaps in expertise with collaborators",
            "For new investigators, emphasize training and mentorship",
        ],
    ),
    "innovation": ReviewCriterion(
        name="Innovation",
        description="Does the application challenge and seek to shift current research paradigms? Does it utilize novel concepts, approaches, methodologies, or technologies?",
        weight=0.15,
        category=CriterionCategory.INNOVATION,
        scoring_guidance="Novel approaches are valued, but innovation alone without feasibility is insufficient.",
        common_weaknesses=[
            "Claiming innovation without clearly explaining what's new",
            "Incremental advancement presented as breakthrough",
            "Novel approach without evidence it will work",
            "Innovation in methods but not in scientific questions",
        ],
        tips=[
            "Clearly state what is novel vs. established",
            "Explain why novel approaches are necessary",
            "Provide preliminary data supporting novel methods",
            "Balance innovation with feasibility",
        ],
    ),
    "approach": ReviewCriterion(
        name="Approach",
        description="Are the overall strategy, methodology, and analyses well-reasoned and appropriate to accomplish the specific aims?",
        weight=0.30,
        category=CriterionCategory.FEASIBILITY,
        scoring_guidance="This is typically the most heavily weighted criterion. Must be rigorous and well-designed.",
        common_weaknesses=[
            "Lack of statistical power analysis",
            "Insufficient detail on methods",
            "No alternative approaches if primary approach fails",
            "Timeline not realistic for proposed work",
            "Missing or weak preliminary data",
        ],
        tips=[
            "Include power calculations and justify sample sizes",
            "Provide detailed protocols for key experiments",
            "Address potential pitfalls and alternative approaches",
            "Show preliminary data demonstrating feasibility",
            "Create realistic, detailed timelines",
        ],
    ),
    "environment": ReviewCriterion(
        name="Environment",
        description="Will the scientific environment contribute to the probability of success? Are the institutional support, equipment, and resources adequate?",
        weight=0.10,
        category=CriterionCategory.RESOURCES,
        scoring_guidance="Evaluate institutional commitment, available resources, and collaborative opportunities.",
        common_weaknesses=[
            "Insufficient institutional support documentation",
            "Key equipment not available or accessible",
            "No evidence of collaborative environment",
            "Lack of protected time for research",
        ],
        tips=[
            "Obtain strong letters of institutional support",
            "Document access to specialized equipment",
            "Highlight collaborative relationships",
            "Show evidence of protected research time",
        ],
    ),
}


# =============================================================================
# NSF Standard Review Criteria
# Based on NSF merit review criteria
# =============================================================================

NSF_CRITERIA: Dict[str, ReviewCriterion] = {
    "intellectual_merit": ReviewCriterion(
        name="Intellectual Merit",
        description="The potential to advance knowledge within its own field or across different fields. How important is the proposed activity to advancing knowledge and understanding?",
        weight=0.50,
        category=CriterionCategory.SCIENTIFIC_MERIT,
        scoring_guidance="Equal weight with Broader Impacts. Focus on scientific advancement and discovery potential.",
        common_weaknesses=[
            "Unclear research questions or hypotheses",
            "Insufficient connection to theoretical framework",
            "Lack of transformative potential",
            "Methods not well matched to questions",
        ],
        tips=[
            "Clearly state research questions and hypotheses",
            "Connect to existing theoretical frameworks",
            "Explain potential for transformative discoveries",
            "Show how methods will answer research questions",
        ],
    ),
    "broader_impacts": ReviewCriterion(
        name="Broader Impacts",
        description="The potential to benefit society and contribute to the achievement of specific, desired societal outcomes. What may be the benefits to society?",
        weight=0.50,
        category=CriterionCategory.IMPACT,
        scoring_guidance="Equal weight with Intellectual Merit. Must be specific and actionable, not vague promises.",
        common_weaknesses=[
            "Generic or vague broader impacts",
            "No concrete plan for implementation",
            "Impacts not connected to the research",
            "Underserved communities not genuinely engaged",
        ],
        tips=[
            "Develop specific, measurable broader impacts activities",
            "Connect impacts to your research expertise",
            "Include genuine partnerships with underserved communities",
            "Budget appropriately for broader impacts activities",
        ],
    ),
}


# =============================================================================
# Mechanism-Specific Criteria Modifications
# =============================================================================

MECHANISM_OVERRIDES: Dict[str, Dict] = {
    # NIH Career Awards
    "K01": {
        "additional_criteria": {
            "career_development": ReviewCriterion(
                name="Career Development/Training Activities",
                description="Are the career development activities appropriate for the candidate? Will they contribute to the candidate's ability to develop into an independent researcher?",
                weight=0.25,
                category=CriterionCategory.TEAM,
                scoring_guidance="Evaluate mentoring plan, training goals, and career trajectory.",
                common_weaknesses=[
                    "Mentoring plan too vague",
                    "Training not aligned with career goals",
                    "Insufficient protected time",
                ],
                tips=[
                    "Detail specific skills to be acquired",
                    "Show clear path to independence",
                    "Demonstrate mentor qualifications and commitment",
                ],
            ),
            "mentor": ReviewCriterion(
                name="Mentor, Co-Mentor(s), Consultant(s), Collaborator(s)",
                description="Are the mentor and other advisors appropriate? Is there evidence of a productive mentor/mentee relationship?",
                weight=0.20,
                category=CriterionCategory.TEAM,
                scoring_guidance="Evaluate mentor track record and commitment to candidate's development.",
                common_weaknesses=[
                    "Mentor lacks K-award mentoring experience",
                    "No evidence of ongoing mentorship commitment",
                ],
                tips=[
                    "Include mentor's statement of commitment",
                    "Document mentor's track record with trainees",
                ],
            ),
        },
        "overall_guidance": "K01 applications must demonstrate a clear career development plan with strong mentorship. The research project should serve as a vehicle for training, not vice versa.",
    },
    "K99": {
        "additional_criteria": {
            "transition_plan": ReviewCriterion(
                name="Transition to Independence",
                description="Is there a clear and feasible plan for transitioning to an independent research position?",
                weight=0.25,
                category=CriterionCategory.FEASIBILITY,
                scoring_guidance="Evaluate timeline and milestones for achieving independence.",
                common_weaknesses=[
                    "No clear timeline for faculty position search",
                    "Research plan not appropriate for starting lab",
                ],
                tips=[
                    "Include specific milestones for each phase",
                    "Show research can be expanded independently",
                ],
            ),
        },
        "overall_guidance": "K99/R00 applications must show readiness for independence. Emphasize how you will transition the research program to your own lab.",
    },
    # NSF CAREER
    "CAREER": {
        "additional_criteria": {
            "education_integration": ReviewCriterion(
                name="Integration of Research and Education",
                description="How well does the proposal integrate the research and educational activities? Is the integration synergistic and meaningful?",
                weight=0.25,
                category=CriterionCategory.IMPACT,
                scoring_guidance="Education component must be substantial and genuinely integrated with research.",
                common_weaknesses=[
                    "Education activities feel tacked on",
                    "No genuine integration with research",
                    "Undergraduate research is the only education component",
                ],
                tips=[
                    "Design education activities that advance research goals",
                    "Include activities at multiple education levels",
                    "Show how research informs teaching and vice versa",
                ],
            ),
        },
        "overall_guidance": "CAREER proposals must demonstrate genuine integration of research and education. The education plan should be as thoughtfully designed as the research plan.",
        "page_limits": {
            "project_description": 15,
            "data_management": 2,
            "postdoc_mentoring": 1,
        },
    },
    # R01
    "R01": {
        "page_limits": {
            "specific_aims": 1,
            "research_strategy": 12,
            "authentication_of_key_resources": 1,
        },
        "overall_guidance": "R01 applications require strong preliminary data and a rigorous, well-designed approach. Budget should be realistic and well-justified.",
    },
    # R21
    "R21": {
        "page_limits": {
            "specific_aims": 1,
            "research_strategy": 6,
        },
        "overall_guidance": "R21 applications should focus on high-risk, high-reward exploratory research. Preliminary data is not required but can strengthen feasibility arguments.",
    },
}


# =============================================================================
# Review Criteria Service
# =============================================================================

class ReviewCriteriaService:
    """Service for managing and retrieving grant review criteria."""

    def get_agency_from_mechanism(self, mechanism_code: str) -> FundingAgency:
        """Determine the funding agency from the mechanism code."""
        mechanism_upper = mechanism_code.upper()

        # NIH mechanisms
        nih_patterns = ["R01", "R21", "R03", "R15", "K01", "K08", "K23", "K99", "F31", "F32", "U01", "P01", "P50"]
        if any(mechanism_upper.startswith(p) for p in nih_patterns):
            return FundingAgency.NIH

        # NSF mechanisms
        nsf_patterns = ["CAREER", "STANDARD", "SBIR", "STTR"]
        if mechanism_upper in nsf_patterns or mechanism_upper.startswith("NSF"):
            return FundingAgency.NSF

        # DOE mechanisms
        if mechanism_upper.startswith("DOE") or mechanism_upper.startswith("DE-"):
            return FundingAgency.DOE

        # DOD mechanisms
        if mechanism_upper.startswith("DOD") or mechanism_upper.startswith("W"):
            return FundingAgency.DOD

        return FundingAgency.OTHER

    def get_base_criteria(self, agency: FundingAgency) -> Dict[str, ReviewCriterion]:
        """Get base review criteria for an agency."""
        if agency == FundingAgency.NIH:
            return NIH_CRITERIA.copy()
        elif agency == FundingAgency.NSF:
            return NSF_CRITERIA.copy()
        else:
            # Default to NIH-style criteria for other agencies
            return NIH_CRITERIA.copy()

    def get_criteria_for_mechanism(self, mechanism_code: str) -> MechanismCriteria:
        """Get complete review criteria for a specific grant mechanism."""
        agency = self.get_agency_from_mechanism(mechanism_code)
        base_criteria = self.get_base_criteria(agency)

        # Apply mechanism-specific overrides
        mechanism_upper = mechanism_code.upper()
        overrides = MECHANISM_OVERRIDES.get(mechanism_upper, {})

        # Add any additional criteria
        if "additional_criteria" in overrides:
            base_criteria.update(overrides["additional_criteria"])

        # Build criteria list
        criteria_list = list(base_criteria.values())

        # Get mechanism name
        mechanism_names = {
            "R01": "Research Project Grant",
            "R21": "Exploratory/Developmental Research Grant",
            "R03": "Small Grant Program",
            "R15": "Academic Research Enhancement Award",
            "K01": "Mentored Research Scientist Development Award",
            "K08": "Mentored Clinical Scientist Development Award",
            "K23": "Mentored Patient-Oriented Research Career Development Award",
            "K99": "Pathway to Independence Award",
            "F31": "Predoctoral Individual NRSA",
            "F32": "Postdoctoral Individual NRSA",
            "CAREER": "Faculty Early Career Development Program",
            "STANDARD": "NSF Standard Research Grant",
        }
        mechanism_name = mechanism_names.get(mechanism_upper, mechanism_code)

        # Get overall guidance
        overall_guidance = overrides.get(
            "overall_guidance",
            self._get_default_guidance(agency)
        )

        # Get page limits
        page_limits = overrides.get("page_limits")

        return MechanismCriteria(
            mechanism_code=mechanism_upper,
            mechanism_name=mechanism_name,
            funding_agency=agency,
            criteria=criteria_list,
            overall_guidance=overall_guidance,
            page_limits=page_limits,
        )

    def _get_default_guidance(self, agency: FundingAgency) -> str:
        """Get default guidance for an agency."""
        if agency == FundingAgency.NIH:
            return "NIH applications are scored on Significance, Investigators, Innovation, Approach, and Environment. Approach typically carries the most weight. Strong preliminary data is essential."
        elif agency == FundingAgency.NSF:
            return "NSF applications are evaluated equally on Intellectual Merit and Broader Impacts. Both criteria must be addressed thoroughly. Broader impacts must be specific and actionable."
        else:
            return "Review the specific solicitation for evaluation criteria. Most agencies evaluate scientific merit, feasibility, team qualifications, and broader impact."

    async def get_criteria_from_db(
        self,
        db: AsyncSession,
        mechanism_code: str
    ) -> Optional[MechanismCriteria]:
        """
        Get criteria from database if available, with fallback to predefined criteria.
        Enriches with data from grant_mechanisms table if present.
        """
        # Try to get mechanism from database
        result = await db.execute(
            select(GrantMechanism).where(GrantMechanism.code == mechanism_code.upper())
        )
        db_mechanism = result.scalar_one_or_none()

        # Get predefined criteria
        criteria = self.get_criteria_for_mechanism(mechanism_code)

        # Enrich with database data if available
        if db_mechanism:
            # Update mechanism name from DB if available
            if db_mechanism.name:
                criteria.mechanism_name = db_mechanism.name

            # Merge review criteria from DB if available
            if db_mechanism.review_criteria:
                # DB review_criteria is a dict with criterion names and weights
                for name, weight_or_config in db_mechanism.review_criteria.items():
                    # Find matching criterion and update weight
                    for crit in criteria.criteria:
                        if crit.name.lower() == name.lower():
                            if isinstance(weight_or_config, (int, float)):
                                # Normalize weight (1-5 scale to 0-1)
                                normalized = 1.0 / max(1, weight_or_config)
                                crit.weight = min(1.0, normalized)
                            break

            # Add tips from DB
            if db_mechanism.tips:
                criteria.overall_guidance += f"\n\nTips: {'; '.join(db_mechanism.tips)}"

        return criteria

    def get_criteria_descriptions(self, mechanism_code: str) -> Dict[str, str]:
        """Get a simple mapping of criterion names to descriptions."""
        criteria = self.get_criteria_for_mechanism(mechanism_code)
        return {c.name: c.description for c in criteria.criteria}

    def get_criterion_tips(self, mechanism_code: str, criterion_name: str) -> List[str]:
        """Get tips for a specific criterion."""
        criteria = self.get_criteria_for_mechanism(mechanism_code)
        for c in criteria.criteria:
            if c.name.lower() == criterion_name.lower():
                return c.tips
        return []

    def get_common_weaknesses(self, mechanism_code: str) -> Dict[str, List[str]]:
        """Get common weaknesses for all criteria in a mechanism."""
        criteria = self.get_criteria_for_mechanism(mechanism_code)
        return {c.name: c.common_weaknesses for c in criteria.criteria}


# Singleton instance
review_criteria_service = ReviewCriteriaService()
