"""Specific Aims Analysis Service using OpenAI."""

import openai
import json
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.models import User, ChatSession, ChatMessage
from backend.schemas.aims import (
    GrantMechanism,
    ScopeStatus,
    IssueType,
    IssueSeverity,
    AimStructure,
    ScopeAssessment,
    DetectedIssue,
    ImprovementSuggestion,
    MechanismGuidelines,
    AimsAnalysisResponse,
    ScopeCheckResponse,
    MechanismTemplateResponse,
    FundedExampleSummary,
    CompareToFundedResponse,
    AimsFollowUpResponse,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Mechanism-Specific Guidelines
# =============================================================================

MECHANISM_GUIDELINES: Dict[GrantMechanism, MechanismGuidelines] = {
    GrantMechanism.R01: MechanismGuidelines(
        mechanism=GrantMechanism.R01,
        recommended_aims_count=3,
        min_aims=2,
        max_aims=4,
        focus_areas=[
            "Hypothesis-driven research",
            "Mechanistic understanding",
            "Rigorous experimental design",
            "Preliminary data supporting feasibility",
        ],
        key_requirements=[
            "Clear central hypothesis",
            "Aims should be related but not interdependent",
            "Each aim should be achievable independently",
            "Strong rationale connecting aims",
            "Preliminary data demonstrating feasibility",
        ],
        common_pitfalls=[
            "Aims that are too interdependent (if Aim 1 fails, Aim 2 cannot proceed)",
            "Overly ambitious scope for 4-5 year timeline",
            "Missing or weak hypothesis",
            "Lack of clear innovation",
            "Vague methodology descriptions",
        ],
        word_count_guidance="450-500 words (strict 1-page limit)",
        typical_structure=[
            "Opening paragraph: Gap in knowledge, long-term goal, overall objective",
            "Central hypothesis statement",
            "Rationale paragraph",
            "Aims 1-3 with brief approach for each",
            "Closing: Expected outcomes and impact",
        ],
    ),
    GrantMechanism.R21: MechanismGuidelines(
        mechanism=GrantMechanism.R21,
        recommended_aims_count=2,
        min_aims=1,
        max_aims=2,
        focus_areas=[
            "Exploratory/developmental research",
            "High-risk, high-reward approaches",
            "Novel concepts or methods",
            "Feasibility and proof-of-concept",
        ],
        key_requirements=[
            "Emphasis on innovation and novelty",
            "Feasibility focus (2-year timeline)",
            "Clear milestones for success",
            "Less emphasis on preliminary data",
            "High-risk tolerance acceptable",
        ],
        common_pitfalls=[
            "Proposing too much for R21 scope",
            "Not emphasizing the innovative aspects enough",
            "Making it sound like a small R01 instead of exploratory",
            "Missing feasibility milestones",
        ],
        word_count_guidance="400-450 words (1-page limit)",
        typical_structure=[
            "Opening: Innovation and gap in knowledge",
            "Objective and exploratory nature",
            "Aim 1: Primary exploratory aim",
            "Aim 2: Secondary/validation aim (if applicable)",
            "Feasibility statement and expected outcomes",
        ],
    ),
    GrantMechanism.K01: MechanismGuidelines(
        mechanism=GrantMechanism.K01,
        recommended_aims_count=2,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Career development integration",
            "Training objectives alignment",
            "Mentored research experience",
            "Building toward independence",
        ],
        key_requirements=[
            "Research aims must support career development",
            "Clear connection to training plan",
            "Appropriate scope for mentored environment",
            "Demonstrate potential for independence",
        ],
        common_pitfalls=[
            "Research too ambitious for training context",
            "Disconnect between research and career goals",
            "Not showing mentor involvement appropriately",
            "Scope appropriate for R01 rather than K award",
        ],
        word_count_guidance="400-450 words",
        typical_structure=[
            "Career development context",
            "Research objective aligned with training",
            "Aim 1: Primary research with training elements",
            "Aim 2: Complementary research building skills",
            "Career trajectory statement",
        ],
    ),
    GrantMechanism.K08: MechanismGuidelines(
        mechanism=GrantMechanism.K08,
        recommended_aims_count=2,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Clinical and translational research training",
            "Patient-oriented research skills",
            "Integration of clinical and research activities",
            "Path to research independence",
        ],
        key_requirements=[
            "Patient-oriented or translational focus",
            "Clinical relevance clear",
            "Balance of clinical and research time",
            "Appropriate mentorship structure",
        ],
        common_pitfalls=[
            "Too basic science, not enough clinical relevance",
            "Research overshadowing training goals",
            "Unclear path to independence",
        ],
        word_count_guidance="400-450 words",
        typical_structure=[
            "Clinical problem and significance",
            "Training and career development context",
            "Aim 1: Clinical/translational aim",
            "Aim 2: Mechanistic/supporting aim",
            "Impact on clinical practice",
        ],
    ),
    GrantMechanism.K23: MechanismGuidelines(
        mechanism=GrantMechanism.K23,
        recommended_aims_count=2,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Patient-oriented research",
            "Human subjects research experience",
            "Career development in clinical research",
            "Mentored research experience",
        ],
        key_requirements=[
            "Patient-oriented research focus",
            "Human subjects involvement",
            "Appropriate for clinical investigator development",
            "Protected time for research",
        ],
        common_pitfalls=[
            "Not enough patient-oriented focus",
            "Too ambitious for development award",
            "Missing clinical research training elements",
        ],
        word_count_guidance="400-450 words",
        typical_structure=[
            "Clinical significance and patient impact",
            "Training context for clinical research",
            "Aim 1: Patient-oriented research aim",
            "Aim 2: Supporting/validation aim",
            "Career development integration",
        ],
    ),
    GrantMechanism.K99: MechanismGuidelines(
        mechanism=GrantMechanism.K99,
        recommended_aims_count=3,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Transition to independence",
            "Postdoctoral to faculty trajectory",
            "Innovative research program",
            "Potential for R01-level research",
        ],
        key_requirements=[
            "Clear transition plan (K99 to R00 phase)",
            "Research independence trajectory",
            "Innovative research direction",
            "Strong publication record",
        ],
        common_pitfalls=[
            "Not clearly distinguishing K99 and R00 phases",
            "Research too similar to postdoc mentor's work",
            "Not demonstrating independence potential",
        ],
        word_count_guidance="450-500 words",
        typical_structure=[
            "Long-term research vision",
            "Objective for K99/R00 transition",
            "Aim 1: K99 phase research",
            "Aim 2: Transition aim (K99 to R00)",
            "Aim 3: R00 phase independence research",
            "Independence trajectory",
        ],
    ),
    GrantMechanism.F31: MechanismGuidelines(
        mechanism=GrantMechanism.F31,
        recommended_aims_count=2,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Predoctoral training",
            "Dissertation research",
            "Research skill development",
            "Career preparation",
        ],
        key_requirements=[
            "Appropriate scope for dissertation",
            "Training component emphasis",
            "Mentor and environment support",
            "Clear research training goals",
        ],
        common_pitfalls=[
            "Scope too large for predoctoral training",
            "Not enough emphasis on training aspects",
            "Missing dissertation committee input",
        ],
        word_count_guidance="350-400 words",
        typical_structure=[
            "Training context and research interest",
            "Dissertation objective",
            "Aim 1: Primary dissertation aim",
            "Aim 2: Secondary/supporting aim",
            "Training outcomes and career goals",
        ],
    ),
    GrantMechanism.F32: MechanismGuidelines(
        mechanism=GrantMechanism.F32,
        recommended_aims_count=2,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Postdoctoral training",
            "Advanced research skills",
            "Career development",
            "Research independence preparation",
        ],
        key_requirements=[
            "Postdoctoral level research",
            "Skill development focus",
            "Mentor and training environment",
            "Path toward independence",
        ],
        common_pitfalls=[
            "Too similar to doctoral research",
            "Not demonstrating new skill acquisition",
            "Missing career development focus",
        ],
        word_count_guidance="400-450 words",
        typical_structure=[
            "Research training objectives",
            "Skill development goals",
            "Aim 1: Primary research aim",
            "Aim 2: Complementary research aim",
            "Career development and independence goals",
        ],
    ),
    GrantMechanism.CAREER: MechanismGuidelines(
        mechanism=GrantMechanism.CAREER,
        recommended_aims_count=3,
        min_aims=2,
        max_aims=3,
        focus_areas=[
            "Integrated research and education",
            "Innovative research direction",
            "Broader impacts through education",
            "Early career faculty development",
        ],
        key_requirements=[
            "Explicit education integration",
            "Broader impacts clearly articulated",
            "Innovative research program",
            "Five-year research plan",
        ],
        common_pitfalls=[
            "Education component feels tacked on",
            "Not enough integration of research and education",
            "Missing broader impacts articulation",
            "Scope not appropriate for 5-year timeline",
        ],
        word_count_guidance="450-500 words (Project Summary style)",
        typical_structure=[
            "Research vision and innovation",
            "Central hypothesis or research question",
            "Aim 1: Primary research aim",
            "Aim 2: Research aim with education integration",
            "Aim 3: Education/outreach aim (integrated)",
            "Broader impacts statement",
        ],
    ),
    GrantMechanism.R03: MechanismGuidelines(
        mechanism=GrantMechanism.R03,
        recommended_aims_count=1,
        min_aims=1,
        max_aims=2,
        focus_areas=[
            "Small, discrete projects",
            "Pilot studies",
            "Secondary analysis",
            "Methodology development",
        ],
        key_requirements=[
            "Limited scope appropriate for small grant",
            "Clear, achievable objectives",
            "2-year timeline feasibility",
            "Modest budget requirements",
        ],
        common_pitfalls=[
            "Too ambitious for R03 scope",
            "Not enough focus on discrete project",
            "Overselling the impact",
        ],
        word_count_guidance="350-400 words",
        typical_structure=[
            "Focused objective",
            "Aim 1: Primary discrete aim",
            "Aim 2: Supporting aim (if applicable)",
            "Expected outcomes and next steps",
        ],
    ),
    GrantMechanism.OTHER: MechanismGuidelines(
        mechanism=GrantMechanism.OTHER,
        recommended_aims_count=3,
        min_aims=2,
        max_aims=4,
        focus_areas=[
            "Clear research objectives",
            "Logical aim structure",
            "Feasibility demonstration",
        ],
        key_requirements=[
            "Clear hypothesis or research question",
            "Well-structured aims",
            "Feasibility evidence",
        ],
        common_pitfalls=[
            "Vague objectives",
            "Overly ambitious scope",
            "Missing rationale",
        ],
        word_count_guidance="400-500 words",
        typical_structure=[
            "Background and gap",
            "Objective and hypothesis",
            "Aims with approaches",
            "Expected outcomes",
        ],
    ),
}


# =============================================================================
# Aims Templates Data
# =============================================================================

TEMPLATE_DATA = {
    "opening_hooks": [
        "A critical gap in knowledge is...",
        "Despite significant advances in..., the mechanisms underlying... remain poorly understood.",
        "Current treatments for... are limited by...",
        "The long-term goal of this research program is to...",
        "The inability to... represents a major barrier to...",
        "There is an urgent need to understand...",
    ],
    "hypothesis_formats": [
        "Our central hypothesis is that [mechanism/factor] [action] [outcome], which is supported by [evidence].",
        "We hypothesize that [specific mechanism], based on [preliminary data/literature].",
        "The working hypothesis, supported by our preliminary data, is that...",
        "We propose that [X] because [Y], which we will test by [Z].",
    ],
    "transition_phrases": [
        "Building on this foundation, Aim 2 will...",
        "The rationale for Aim X is that...",
        "These findings will directly inform...",
        "Complementing Aim 1, Aim 2 will address...",
        "Having established X in Aim 1, Aim 2 will determine...",
    ],
    "strong_action_verbs": [
        "determine",
        "establish",
        "identify",
        "characterize",
        "elucidate",
        "define",
        "demonstrate",
        "investigate",
        "test",
        "evaluate",
        "validate",
        "quantify",
        "assess",
        "analyze",
        "develop",
    ],
}


# =============================================================================
# Funded Grant Examples (Anonymized Patterns)
# =============================================================================

FUNDED_EXAMPLES: Dict[GrantMechanism, List[FundedExampleSummary]] = {
    GrantMechanism.R01: [
        FundedExampleSummary(
            mechanism=GrantMechanism.R01,
            research_area="Cancer Biology",
            aims_count=3,
            structure_summary="Classic hypothesis-driven structure with clear mechanistic aims",
            key_features=[
                "Strong opening hook about clinical significance",
                "Central hypothesis with preliminary data support",
                "Three independent but thematically related aims",
                "Each aim with clear expected outcomes",
            ],
            hypothesis_style="Mechanistic - 'We hypothesize that X acts through Y to regulate Z'",
        ),
        FundedExampleSummary(
            mechanism=GrantMechanism.R01,
            research_area="Neuroscience",
            aims_count=3,
            structure_summary="Circuit-level investigation with behavioral validation",
            key_features=[
                "Gap in knowledge clearly articulated",
                "Hypothesis grounded in preliminary data",
                "Progressive aims from mechanism to behavior",
                "Strong innovation statement",
            ],
            hypothesis_style="Functional - 'Our hypothesis is that the X circuit mediates Y behavior through Z mechanism'",
        ),
    ],
    GrantMechanism.R21: [
        FundedExampleSummary(
            mechanism=GrantMechanism.R21,
            research_area="Drug Development",
            aims_count=2,
            structure_summary="Proof-of-concept structure emphasizing innovation",
            key_features=[
                "Strong emphasis on novelty and innovation",
                "Clear feasibility milestones",
                "Two focused, achievable aims",
                "Explicit statement of exploratory nature",
            ],
            hypothesis_style="Exploratory - 'We will test the novel concept that...'",
        ),
    ],
    GrantMechanism.K01: [
        FundedExampleSummary(
            mechanism=GrantMechanism.K01,
            research_area="Immunology",
            aims_count=2,
            structure_summary="Training-integrated research structure",
            key_features=[
                "Clear connection to career development",
                "Mentor involvement evident",
                "Appropriate scope for training context",
                "Skills to be gained highlighted",
            ],
            hypothesis_style="Training-focused - 'Through this mentored research, I will test the hypothesis that...'",
        ),
    ],
    GrantMechanism.CAREER: [
        FundedExampleSummary(
            mechanism=GrantMechanism.CAREER,
            research_area="Biomedical Engineering",
            aims_count=3,
            structure_summary="Integrated research and education with clear broader impacts",
            key_features=[
                "Vision statement for research program",
                "Education naturally integrated into research",
                "Broader impacts explicitly stated",
                "Five-year progression evident",
            ],
            hypothesis_style="Vision-oriented - 'The overarching hypothesis driving this research program is...'",
        ),
    ],
}


class SpecificAimsAnalyzer:
    """Service to analyze and provide feedback on Specific Aims pages."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    # -------------------------------------------------------------------------
    # Main Analysis Functions
    # -------------------------------------------------------------------------

    async def analyze_aims_structure(
        self,
        db: AsyncSession,
        user: User,
        text: str,
        mechanism: GrantMechanism,
        research_area: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> AimsAnalysisResponse:
        """
        Parse and evaluate the structure of a Specific Aims page.

        Analyzes:
        - Number and structure of aims
        - Presence of hypothesis
        - Scope appropriateness
        - Common issues
        - Alignment with mechanism requirements
        """
        guidelines = MECHANISM_GUIDELINES.get(mechanism, MECHANISM_GUIDELINES[GrantMechanism.OTHER])

        # Build the analysis prompt
        prompt = self._build_analysis_prompt(text, mechanism, guidelines, research_area, additional_context)

        # Call OpenAI for analysis
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        result = self._parse_analysis_response(response.choices[0].message.content, text, mechanism, guidelines)

        # Create chat session for follow-up
        session = ChatSession(
            user_id=user.id,
            title=f"Aims Analysis: {mechanism.value}",
            session_type="aims_analysis",
            metadata_={
                "mechanism": mechanism.value,
                "overall_score": result.overall_score,
                "aims_count": result.detected_aims_count,
            },
        )
        db.add(session)
        await db.flush()

        # Save initial exchange
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=f"Analyze my Specific Aims for {mechanism.value}:\n\n{text[:500]}...",
        )
        assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=result.overall_assessment)
        db.add_all([user_msg, assistant_msg])
        await db.commit()
        await db.refresh(session)

        result.session_id = session.id
        return result

    async def check_aim_scope(
        self,
        aim_text: str,
        mechanism: GrantMechanism,
        aim_number: Optional[int] = None,
    ) -> ScopeCheckResponse:
        """
        Assess if a single aim is appropriately scoped for the mechanism.

        Returns assessment of whether aim is too broad, too narrow, or appropriate.
        """
        guidelines = MECHANISM_GUIDELINES.get(mechanism, MECHANISM_GUIDELINES[GrantMechanism.OTHER])

        prompt = self._build_scope_check_prompt(aim_text, mechanism, guidelines, aim_number)

        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_scope_response(response.choices[0].message.content, aim_text, mechanism, aim_number, guidelines)

    def detect_common_issues(self, aims_text: str) -> List[DetectedIssue]:
        """
        Find common issues in specific aims text.

        Detects:
        - Circular dependencies
        - Overlapping aims
        - Missing controls
        - Vague language
        - Missing hypothesis
        """
        issues = []

        # Check for vague language patterns
        vague_patterns = [
            (r"\bwill try to\b", "Vague language: 'will try to' suggests uncertainty"),
            (r"\bmay\b.*\bmay\b", "Multiple 'may' statements suggest lack of commitment"),
            (r"\bhopefully\b", "Vague language: 'hopefully' undermines confidence"),
            (r"\bpossibly\b", "Vague language: 'possibly' suggests uncertainty"),
            (r"\bwe believe\b", "Replace 'we believe' with hypothesis or data-driven statement"),
            (r"\bit is thought that\b", "Passive and vague - state the hypothesis directly"),
        ]

        for pattern, description in vague_patterns:
            if re.search(pattern, aims_text, re.IGNORECASE):
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.VAGUE_LANGUAGE,
                        severity=IssueSeverity.MINOR,
                        description=description,
                        location=None,
                        suggestion="Use confident, direct language with active voice",
                    )
                )

        # Check for missing hypothesis
        hypothesis_patterns = [
            r"hypothes[ie]s?\b",
            r"we propose that\b",
            r"we predict that\b",
            r"our central\b.*\bhypothes",
        ]
        has_hypothesis = any(re.search(p, aims_text, re.IGNORECASE) for p in hypothesis_patterns)
        if not has_hypothesis:
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.MISSING_HYPOTHESIS,
                    severity=IssueSeverity.MAJOR,
                    description="No clear hypothesis statement detected",
                    location=None,
                    suggestion="Include a clear, testable central hypothesis before listing the aims",
                )
            )

        # Check for interdependency language
        dependency_patterns = [
            r"aim \d.*will be used in aim \d",
            r"results from aim \d.*necessary for aim \d",
            r"depends on.*aim \d",
            r"before we can.*aim \d",
            r"if aim \d fails",
        ]
        for pattern in dependency_patterns:
            if re.search(pattern, aims_text, re.IGNORECASE):
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.INTERDEPENDENCY,
                        severity=IssueSeverity.MAJOR,
                        description="Aims appear to be interdependent - if one fails, others cannot proceed",
                        location=None,
                        suggestion="Restructure aims to be independent. Each aim should produce meaningful results even if other aims have unexpected outcomes.",
                    )
                )
                break

        # Check for overlap patterns
        overlap_indicators = [
            r"(aim \d).*\bsimilar\b.*(aim \d)",
            r"(aim \d).*\boverlap\b.*(aim \d)",
        ]
        for pattern in overlap_indicators:
            if re.search(pattern, aims_text, re.IGNORECASE):
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.OVERLAPPING_AIMS,
                        severity=IssueSeverity.MINOR,
                        description="Potential overlap between aims detected",
                        location=None,
                        suggestion="Ensure each aim addresses a distinct aspect of the research question",
                    )
                )
                break

        return issues

    def suggest_improvements(
        self,
        aims_text: str,
        mechanism: GrantMechanism,
        detected_issues: List[DetectedIssue],
    ) -> List[ImprovementSuggestion]:
        """Generate actionable recommendations based on analysis."""
        suggestions = []
        MECHANISM_GUIDELINES.get(mechanism, MECHANISM_GUIDELINES[GrantMechanism.OTHER])

        # Word count analysis
        word_count = len(aims_text.split())
        if word_count < 350:
            suggestions.append(
                ImprovementSuggestion(
                    category="length",
                    current_issue=f"Current word count ({word_count}) is below recommended minimum",
                    suggested_change="Expand the specific aims to include more detail on approach and expected outcomes",
                    priority=2,
                    example_text=None,
                )
            )
        elif word_count > 550:
            suggestions.append(
                ImprovementSuggestion(
                    category="length",
                    current_issue=f"Current word count ({word_count}) exceeds recommended maximum",
                    suggested_change="Trim redundant language and focus on essential elements",
                    priority=1,
                    example_text=None,
                )
            )

        # Issue-based suggestions
        for issue in detected_issues:
            if issue.issue_type == IssueType.MISSING_HYPOTHESIS:
                suggestions.append(
                    ImprovementSuggestion(
                        category="structure",
                        current_issue="Missing clear hypothesis",
                        suggested_change="Add a central hypothesis statement after the rationale",
                        priority=1,
                        example_text="Our central hypothesis is that [mechanism] leads to [outcome], supported by [evidence].",
                    )
                )
            elif issue.issue_type == IssueType.INTERDEPENDENCY:
                suggestions.append(
                    ImprovementSuggestion(
                        category="structure",
                        current_issue="Aims are interdependent",
                        suggested_change="Restructure aims so each can succeed independently",
                        priority=1,
                        example_text=None,
                    )
                )

        # Mechanism-specific suggestions
        if mechanism == GrantMechanism.CAREER:
            if "education" not in aims_text.lower() and "broader impact" not in aims_text.lower():
                suggestions.append(
                    ImprovementSuggestion(
                        category="mechanism-specific",
                        current_issue="Missing education/broader impacts integration",
                        suggested_change="Add explicit education component integrated with research aims",
                        priority=1,
                        example_text="Aim 3 will integrate research with education by...",
                    )
                )

        if mechanism in [GrantMechanism.K01, GrantMechanism.K08, GrantMechanism.K23]:
            if "training" not in aims_text.lower() and "career" not in aims_text.lower():
                suggestions.append(
                    ImprovementSuggestion(
                        category="mechanism-specific",
                        current_issue="Missing career development context",
                        suggested_change="Integrate training and career development language",
                        priority=2,
                        example_text=None,
                    )
                )

        return sorted(suggestions, key=lambda x: x.priority)

    async def compare_to_funded(
        self,
        aims_text: str,
        mechanism: GrantMechanism,
        research_area: Optional[str] = None,
    ) -> CompareToFundedResponse:
        """Compare structure to successful applications."""
        guidelines = MECHANISM_GUIDELINES.get(mechanism, MECHANISM_GUIDELINES[GrantMechanism.OTHER])
        examples = FUNDED_EXAMPLES.get(mechanism, [])

        prompt = self._build_comparison_prompt(aims_text, mechanism, guidelines, examples, research_area)

        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_comparison_response(response.choices[0].message.content, mechanism, examples)

    def get_mechanism_template(self, mechanism: GrantMechanism) -> MechanismTemplateResponse:
        """Get template structure for a specific mechanism."""
        guidelines = MECHANISM_GUIDELINES.get(mechanism, MECHANISM_GUIDELINES[GrantMechanism.OTHER])

        template_outline = self._generate_template_outline(mechanism, guidelines)

        return MechanismTemplateResponse(
            mechanism=mechanism,
            guidelines=guidelines,
            template_sections=guidelines.typical_structure,
            example_opening_hooks=TEMPLATE_DATA["opening_hooks"],
            example_hypothesis_formats=TEMPLATE_DATA["hypothesis_formats"],
            transition_phrases=TEMPLATE_DATA["transition_phrases"],
            strong_action_verbs=TEMPLATE_DATA["strong_action_verbs"],
            template_outline=template_outline,
        )

    def get_funded_examples(self, mechanism: GrantMechanism) -> List[FundedExampleSummary]:
        """Get example structures from funded grants."""
        return FUNDED_EXAMPLES.get(mechanism, [])

    async def follow_up(
        self,
        db: AsyncSession,
        user: User,
        session_id: UUID,
        message: str,
    ) -> AimsFollowUpResponse:
        """Handle follow-up questions about aims analysis."""
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise ValueError("Session not found")

        # Get conversation history
        messages_result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        )
        history = messages_result.scalars().all()

        # Build conversation for Claude
        claude_messages = []
        for msg in history:
            claude_messages.append({"role": msg.role if msg.role != "system" else "user", "content": msg.content})
        claude_messages.append({"role": "user", "content": message})

        mechanism = session.metadata_.get("mechanism", "R01") if session.metadata_ else "R01"

        system_prompt = f"""You are an expert grant writing advisor helping a researcher improve their Specific Aims page.

Mechanism: {mechanism}

Continue the conversation naturally, providing specific advice on:
- Structure and organization
- Clarity and impact
- Alignment with mechanism requirements
- Specific language improvements

Be constructive and provide actionable suggestions."""

        messages = [{"role": "system", "content": system_prompt}] + claude_messages
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=messages,
        )

        response_text = response.choices[0].message.content

        # Save messages
        user_msg = ChatMessage(session_id=session_id, role="user", content=message)
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=response_text)
        db.add_all([user_msg, assistant_msg])
        await db.commit()

        return AimsFollowUpResponse(
            session_id=session_id,
            response=response_text,
        )

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _build_analysis_prompt(
        self,
        text: str,
        mechanism: GrantMechanism,
        guidelines: MechanismGuidelines,
        research_area: Optional[str],
        additional_context: Optional[str],
    ) -> str:
        """Build the prompt for full aims analysis."""
        return f"""You are an expert NIH/NSF grant reviewer and writing consultant. Analyze the following Specific Aims page for a {mechanism.value} grant application.

SPECIFIC AIMS TEXT:
{text}

MECHANISM REQUIREMENTS ({mechanism.value}):
- Recommended aims: {guidelines.min_aims}-{guidelines.max_aims} (ideal: {guidelines.recommended_aims_count})
- Focus areas: {", ".join(guidelines.focus_areas)}
- Key requirements: {", ".join(guidelines.key_requirements)}
- Word count guidance: {guidelines.word_count_guidance}

{f"RESEARCH AREA: {research_area}" if research_area else ""}
{f"ADDITIONAL CONTEXT: {additional_context}" if additional_context else ""}

Provide your analysis in the following JSON format:
{{
    "overall_score": 0-100,
    "overall_assessment": "2-3 paragraph assessment of the Specific Aims",
    "detected_aims_count": N,
    "aims_structure": [
        {{
            "aim_number": 1,
            "aim_text": "text of the aim",
            "hypothesis": "hypothesis if present",
            "approach_summary": "brief approach description",
            "expected_outcomes": "expected outcomes if stated",
            "word_count": N,
            "has_hypothesis": true/false,
            "has_approach": true/false,
            "has_expected_outcome": true/false
        }}
    ],
    "scope_assessments": [
        {{
            "aim_number": 1,
            "status": "too_broad" | "too_narrow" | "appropriate" | "unclear",
            "explanation": "explanation",
            "confidence": 0.0-1.0,
            "suggestions": ["suggestion 1", "suggestion 2"]
        }}
    ],
    "issues": [
        {{
            "issue_type": "circular_logic" | "overlapping_aims" | "missing_controls" | "missing_hypothesis" | "interdependency" | "vague_language" | "feasibility_concern" | "methodology_gap" | "innovation_unclear" | "significance_weak",
            "severity": "critical" | "major" | "minor" | "suggestion",
            "description": "description of the issue",
            "location": "where in the text (optional)",
            "suggestion": "how to fix it"
        }}
    ],
    "suggestions": [
        {{
            "category": "structure | clarity | scope | innovation | significance",
            "current_issue": "what's wrong",
            "suggested_change": "what to do",
            "priority": 1-5,
            "example_text": "example if helpful"
        }}
    ],
    "strengths": ["strength 1", "strength 2"],
    "mechanism_specific_feedback": "Specific feedback about alignment with {mechanism.value} requirements"
}}

Be thorough but constructive. Focus on actionable improvements."""

    def _build_scope_check_prompt(
        self,
        aim_text: str,
        mechanism: GrantMechanism,
        guidelines: MechanismGuidelines,
        aim_number: Optional[int],
    ) -> str:
        """Build prompt for scope checking a single aim."""
        return f"""You are an expert grant reviewer. Assess whether this aim is appropriately scoped for a {mechanism.value} grant.

AIM TEXT:
{aim_text}

MECHANISM: {mechanism.value}
{f"AIM NUMBER: {aim_number}" if aim_number else ""}
TYPICAL SCOPE GUIDANCE: {guidelines.word_count_guidance}
KEY REQUIREMENTS: {", ".join(guidelines.key_requirements[:3])}

Provide your assessment in JSON format:
{{
    "scope_status": "too_broad" | "too_narrow" | "appropriate" | "unclear",
    "explanation": "detailed explanation of the scope assessment",
    "confidence": 0.0-1.0,
    "suggestions": ["specific suggestions for scope adjustment"],
    "recommended_scope": "description of appropriate scope for this mechanism"
}}"""

    def _build_comparison_prompt(
        self,
        aims_text: str,
        mechanism: GrantMechanism,
        guidelines: MechanismGuidelines,
        examples: List[FundedExampleSummary],
        research_area: Optional[str],
    ) -> str:
        """Build prompt for comparing to funded applications."""
        examples_text = (
            "\n".join([f"- {ex.research_area}: {ex.aims_count} aims, {ex.structure_summary}" for ex in examples])
            if examples
            else "No specific examples available for this mechanism."
        )

        return f"""Compare this Specific Aims page to successful funded {mechanism.value} applications.

AIMS TEXT:
{aims_text}

MECHANISM: {mechanism.value}
{f"RESEARCH AREA: {research_area}" if research_area else ""}

PATTERNS FROM FUNDED APPLICATIONS:
{examples_text}

TYPICAL STRUCTURE: {", ".join(guidelines.typical_structure)}

Provide your comparison in JSON format:
{{
    "similarity_score": 0-100,
    "structure_comparison": "how the structure compares to typical funded applications",
    "alignment_with_funded": ["ways this aligns with successful applications"],
    "deviations_from_funded": ["ways this deviates from typical successful structure"],
    "recommendations": ["specific recommendations based on funded patterns"]
}}"""

    def _generate_template_outline(
        self,
        mechanism: GrantMechanism,
        guidelines: MechanismGuidelines,
    ) -> str:
        """Generate a template outline for the mechanism."""
        if mechanism == GrantMechanism.R01:
            return """SPECIFIC AIMS

[Opening paragraph - 3-4 sentences]
[Gap in knowledge and significance] [Long-term goal] [Overall objective of this application]

[Central hypothesis - 1-2 sentences]
Our central hypothesis is that [mechanism/factor] [action] [outcome]. This hypothesis is supported by [preliminary data/literature].

[Rationale paragraph - 2-3 sentences]
The rationale for the proposed research is that [expected outcome] will [impact/advance field]. [Why now is the right time]

Aim 1: [Action verb] [specific objective].
[Working hypothesis for Aim 1] [Brief approach - 2-3 sentences] [Expected outcome]

Aim 2: [Action verb] [specific objective].
[Working hypothesis for Aim 2] [Brief approach - 2-3 sentences] [Expected outcome]

Aim 3: [Action verb] [specific objective].
[Working hypothesis for Aim 3] [Brief approach - 2-3 sentences] [Expected outcome]

[Closing - 2-3 sentences]
[Expected outcomes and impact] [How this advances the field/leads to future research]"""

        elif mechanism == GrantMechanism.R21:
            return """SPECIFIC AIMS

[Innovation and gap - 2-3 sentences]
[Novel concept/approach being tested] [Why current approaches are insufficient]

[Objective - 1-2 sentences]
The objective of this exploratory R21 is to [test/develop/establish] [novel concept]. This project is innovative because [innovation statement].

Aim 1: [Action verb] [exploratory objective].
[Brief approach] [Feasibility milestones] [Expected outcome or decision point]

Aim 2: [Action verb] [validation/supporting objective].
[Brief approach] [How this supports or validates Aim 1 findings]

[Feasibility and outcomes - 2-3 sentences]
[Why this is feasible] [Expected outcomes] [Path to larger studies if successful]"""

        elif mechanism == GrantMechanism.CAREER:
            return """SPECIFIC AIMS

[Research vision - 2-3 sentences]
[Long-term research vision] [Significance to field]

[Central hypothesis/question - 1-2 sentences]
[Central hypothesis or overarching research question]

Aim 1: [Research aim with action verb].
[Approach and expected outcomes]

Aim 2: [Research aim integrated with education/training].
[Research approach] [How education is integrated]

Aim 3: [Education/outreach aim or integrated research-education aim].
[Educational activities] [Broader impacts]

[Impact statement - 2-3 sentences]
[Research impact] [Broader impacts for education and society]"""

        else:
            return """SPECIFIC AIMS

[Opening paragraph]
[Gap in knowledge] [Long-term goal] [Objective]

[Hypothesis statement]
[Central hypothesis or research question]

Aim 1: [Specific objective]
[Approach] [Expected outcome]

Aim 2: [Specific objective]
[Approach] [Expected outcome]

[Closing]
[Expected outcomes and significance]"""

    def _parse_analysis_response(
        self,
        response_text: str,
        original_text: str,
        mechanism: GrantMechanism,
        guidelines: MechanismGuidelines,
    ) -> AimsAnalysisResponse:
        """Parse Claude's analysis response into structured format."""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            # Parse aims structure
            aims_structure = [AimStructure(**aim) for aim in data.get("aims_structure", [])]

            # Parse scope assessments
            scope_assessments = [
                ScopeAssessment(
                    aim_number=sa["aim_number"],
                    status=ScopeStatus(sa["status"]),
                    explanation=sa["explanation"],
                    confidence=sa.get("confidence", 0.7),
                    suggestions=sa.get("suggestions", []),
                )
                for sa in data.get("scope_assessments", [])
            ]

            # Parse issues
            issues = [
                DetectedIssue(
                    issue_type=IssueType(issue["issue_type"]),
                    severity=IssueSeverity(issue["severity"]),
                    description=issue["description"],
                    location=issue.get("location"),
                    suggestion=issue["suggestion"],
                )
                for issue in data.get("issues", [])
            ]

            # Parse suggestions
            suggestions = [ImprovementSuggestion(**sugg) for sugg in data.get("suggestions", [])]

            # Word count analysis
            word_count = len(original_text.split())
            if word_count < 400:
                word_count_status = "too_short"
            elif word_count > 550:
                word_count_status = "too_long"
            else:
                word_count_status = "within_range"

            # Count issues by severity
            critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
            major_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)

            return AimsAnalysisResponse(
                overall_score=data.get("overall_score", 70.0),
                overall_assessment=data.get("overall_assessment", "Analysis complete."),
                mechanism=mechanism,
                detected_aims_count=data.get("detected_aims_count", len(aims_structure)),
                recommended_aims_count=guidelines.recommended_aims_count,
                aims_structure=aims_structure,
                scope_assessments=scope_assessments,
                issues=issues,
                critical_issues_count=critical_count,
                major_issues_count=major_count,
                suggestions=suggestions,
                total_word_count=word_count,
                word_count_status=word_count_status,
                strengths=data.get("strengths", []),
                mechanism_specific_feedback=data.get(
                    "mechanism_specific_feedback", f"Review alignment with {mechanism.value} requirements."
                ),
                analyzed_at=datetime.now(timezone.utc),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse aims analysis response", error=str(e))
            # Return a basic response on parse failure
            word_count = len(original_text.split())
            return AimsAnalysisResponse(
                overall_score=50.0,
                overall_assessment="Unable to fully parse the analysis. Please try again.",
                mechanism=mechanism,
                detected_aims_count=0,
                recommended_aims_count=guidelines.recommended_aims_count,
                aims_structure=[],
                scope_assessments=[],
                issues=[],
                critical_issues_count=0,
                major_issues_count=0,
                suggestions=[],
                total_word_count=word_count,
                word_count_status="within_range"
                if 400 <= word_count <= 550
                else "too_short"
                if word_count < 400
                else "too_long",
                strengths=[],
                mechanism_specific_feedback="Analysis incomplete - please retry.",
                analyzed_at=datetime.now(timezone.utc),
            )

    def _parse_scope_response(
        self,
        response_text: str,
        aim_text: str,
        mechanism: GrantMechanism,
        aim_number: Optional[int],
        guidelines: MechanismGuidelines,
    ) -> ScopeCheckResponse:
        """Parse scope check response."""
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            return ScopeCheckResponse(
                aim_number=aim_number,
                aim_text=aim_text,
                mechanism=mechanism,
                scope_status=ScopeStatus(data.get("scope_status", "unclear")),
                explanation=data.get("explanation", "Unable to determine scope."),
                confidence=data.get("confidence", 0.5),
                suggestions=data.get("suggestions", []),
                word_count=len(aim_text.split()),
                recommended_scope_for_mechanism=data.get(
                    "recommended_scope", f"Appropriate scope for {mechanism.value}"
                ),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse scope response", error=str(e))
            return ScopeCheckResponse(
                aim_number=aim_number,
                aim_text=aim_text,
                mechanism=mechanism,
                scope_status=ScopeStatus.UNCLEAR,
                explanation="Unable to parse scope assessment.",
                confidence=0.0,
                suggestions=[],
                word_count=len(aim_text.split()),
                recommended_scope_for_mechanism=f"See {mechanism.value} guidelines",
            )

    def _parse_comparison_response(
        self,
        response_text: str,
        mechanism: GrantMechanism,
        examples: List[FundedExampleSummary],
    ) -> CompareToFundedResponse:
        """Parse comparison response."""
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            return CompareToFundedResponse(
                mechanism=mechanism,
                similarity_score=data.get("similarity_score", 50.0),
                structure_comparison=data.get("structure_comparison", "Comparison unavailable."),
                alignment_with_funded=data.get("alignment_with_funded", []),
                deviations_from_funded=data.get("deviations_from_funded", []),
                funded_examples=examples,
                recommendations=data.get("recommendations", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse comparison response", error=str(e))
            return CompareToFundedResponse(
                mechanism=mechanism,
                similarity_score=50.0,
                structure_comparison="Unable to complete comparison.",
                alignment_with_funded=[],
                deviations_from_funded=[],
                funded_examples=examples,
                recommendations=["Please retry the comparison."],
            )


# =============================================================================
# Convenience Functions (for import into other modules)
# =============================================================================

_analyzer = None


def get_analyzer() -> SpecificAimsAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SpecificAimsAnalyzer()
    return _analyzer


async def analyze_aims_structure(
    db: AsyncSession,
    user: User,
    text: str,
    mechanism: GrantMechanism,
    research_area: Optional[str] = None,
    additional_context: Optional[str] = None,
) -> AimsAnalysisResponse:
    """Convenience function for aims analysis."""
    return await get_analyzer().analyze_aims_structure(db, user, text, mechanism, research_area, additional_context)


async def check_aim_scope(
    aim_text: str,
    mechanism: GrantMechanism,
    aim_number: Optional[int] = None,
) -> ScopeCheckResponse:
    """Convenience function for scope checking."""
    return await get_analyzer().check_aim_scope(aim_text, mechanism, aim_number)


def detect_common_issues(aims_text: str) -> List[DetectedIssue]:
    """Convenience function for issue detection."""
    return get_analyzer().detect_common_issues(aims_text)


def suggest_improvements(
    aims_text: str,
    mechanism: GrantMechanism,
    detected_issues: List[DetectedIssue],
) -> List[ImprovementSuggestion]:
    """Convenience function for generating suggestions."""
    return get_analyzer().suggest_improvements(aims_text, mechanism, detected_issues)


async def compare_to_funded(
    aims_text: str,
    mechanism: GrantMechanism,
    research_area: Optional[str] = None,
) -> CompareToFundedResponse:
    """Convenience function for comparison to funded grants."""
    return await get_analyzer().compare_to_funded(aims_text, mechanism, research_area)


def get_mechanism_template(mechanism: GrantMechanism) -> MechanismTemplateResponse:
    """Convenience function for getting mechanism template."""
    return get_analyzer().get_mechanism_template(mechanism)


def get_funded_examples(mechanism: GrantMechanism) -> List[FundedExampleSummary]:
    """Convenience function for getting funded examples."""
    return get_analyzer().get_funded_examples(mechanism)
