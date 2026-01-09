"""
Writing Assistant Service
AI-powered analysis and feedback for grant application drafts.
Focuses on structure and completeness rather than content quality.
"""
import json
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional
from uuid import UUID

import anthropic
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.models import Grant
from backend.schemas.writing import (
    AnalyzeResponse,
    CriterionCategory,
    FeedbackResponse,
    SectionScore,
    SuggestionType,
    SuggestionsResponse,
    WritingAnalysis,
    WritingSuggestion,
)
from backend.services.review_criteria import review_criteria_service

logger = structlog.get_logger(__name__)


# =============================================================================
# Section Type Mappings
# =============================================================================

SECTION_CRITERIA_MAP = {
    # NIH section types
    "specific_aims": ["significance", "innovation", "approach"],
    "significance": ["significance"],
    "innovation": ["innovation"],
    "approach": ["approach", "environment"],
    "investigators": ["investigators"],
    "environment": ["environment"],
    "research_strategy": ["significance", "innovation", "approach"],
    # NSF section types
    "project_description": ["intellectual_merit", "broader_impacts"],
    "broader_impacts": ["broader_impacts"],
    "intellectual_merit": ["intellectual_merit"],
    # Career development
    "career_development": ["career_development", "mentor"],
    "mentoring_plan": ["mentor"],
    "transition_plan": ["transition_plan"],
    # Generic
    "abstract": ["significance", "innovation"],
    "budget_justification": ["approach", "environment"],
}


def get_score_label(score: float) -> str:
    """Convert numeric score to label."""
    if score >= 8.5:
        return "Exceptional"
    elif score >= 7.0:
        return "Strong"
    elif score >= 5.5:
        return "Moderate"
    elif score >= 4.0:
        return "Needs Improvement"
    else:
        return "Weak"


class WritingAssistantService:
    """Service for analyzing and providing feedback on grant writing."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def analyze_text(
        self,
        db: AsyncSession,
        text: str,
        mechanism: str,
        section_type: Optional[str] = None,
        grant_id: Optional[UUID] = None,
    ) -> AnalyzeResponse:
        """
        Analyze draft text against review criteria.

        Focuses on structural analysis and completeness rather than
        subjective content quality assessment.
        """
        # Get review criteria for the mechanism
        criteria = await review_criteria_service.get_criteria_from_db(db, mechanism)
        if not criteria:
            criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)

        # Get grant context if available
        grant_context = ""
        if grant_id:
            grant = await db.get(Grant, grant_id)
            if grant:
                grant_context = f"\nGrant Context: {grant.title}\nAgency: {grant.agency or 'Unknown'}"

        # Determine which criteria to focus on
        relevant_criteria = criteria.criteria
        if section_type and section_type.lower() in SECTION_CRITERIA_MAP:
            criteria_names = SECTION_CRITERIA_MAP[section_type.lower()]
            relevant_criteria = [
                c for c in criteria.criteria
                if c.name.lower() in [n.lower() for n in criteria_names]
            ]
            # If no matches, use all criteria
            if not relevant_criteria:
                relevant_criteria = criteria.criteria

        # Build analysis prompt
        criteria_desc = "\n".join([
            f"- {c.name}: {c.description}" for c in relevant_criteria
        ])

        prompt = self._build_analysis_prompt(
            text=text,
            mechanism=mechanism,
            criteria_desc=criteria_desc,
            section_type=section_type,
            grant_context=grant_context,
        )

        # Call Claude for analysis
        try:
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            result = self._parse_analysis_response(
                response.content[0].text,
                text,
                relevant_criteria
            )
        except Exception as e:
            logger.error("Failed to analyze text", error=str(e))
            # Return a basic analysis on error
            result = self._create_fallback_analysis(text, relevant_criteria)

        criteria_names = [c.name for c in relevant_criteria]

        # Generate top recommendations
        recommendations = self._generate_recommendations(result.section_scores)

        return AnalyzeResponse(
            analysis=result,
            criteria_used=criteria_names,
            recommendations=recommendations,
        )

    def _build_analysis_prompt(
        self,
        text: str,
        mechanism: str,
        criteria_desc: str,
        section_type: Optional[str],
        grant_context: str,
    ) -> str:
        """Build the prompt for text analysis."""
        section_info = f"Section Type: {section_type}" if section_type else "Section Type: Not specified"

        return f"""You are an expert grant writing consultant analyzing a draft section for a {mechanism} grant application.

{section_info}
{grant_context}

REVIEW CRITERIA TO EVALUATE:
{criteria_desc}

DRAFT TEXT TO ANALYZE:
---
{text}
---

Analyze this draft focusing on STRUCTURE and COMPLETENESS, not subjective content quality.
Evaluate how well each criterion is addressed and identify gaps.

Provide your analysis in the following JSON format:
{{
    "overall_score": 7.5,
    "structure_feedback": "Overall assessment of structure and organization",
    "clarity_score": 7.0,
    "completeness_score": 6.5,
    "section_scores": [
        {{
            "criterion_name": "Significance",
            "score": 7.5,
            "coverage": 0.8,
            "strengths": ["Clear problem statement", "Good literature support"],
            "gaps": ["Missing discussion of broader impact"],
            "suggestions": ["Add paragraph on field advancement"]
        }}
    ]
}}

SCORING GUIDELINES:
- Scores are 1-10 where 10 is exceptional
- Coverage is 0.0-1.0 where 1.0 means criterion is fully addressed
- Focus on what IS present vs. what SHOULD be present
- Be specific about gaps and suggestions
- Do not evaluate writing style or grammar"""

    def _parse_analysis_response(
        self,
        response_text: str,
        original_text: str,
        criteria
    ) -> WritingAnalysis:
        """Parse Claude's response into structured format."""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            section_scores = []
            for score_data in data.get("section_scores", []):
                score = SectionScore(
                    criterion_name=score_data.get("criterion_name", "Unknown"),
                    score=float(score_data.get("score", 5.0)),
                    score_label=get_score_label(float(score_data.get("score", 5.0))),
                    coverage=float(score_data.get("coverage", 0.5)),
                    strengths=score_data.get("strengths", []),
                    gaps=score_data.get("gaps", []),
                    suggestions=score_data.get("suggestions", []),
                )
                section_scores.append(score)

            overall_score = float(data.get("overall_score", 5.0))

            return WritingAnalysis(
                overall_score=overall_score,
                overall_label=get_score_label(overall_score),
                section_scores=section_scores,
                structure_feedback=data.get("structure_feedback", "Analysis complete."),
                clarity_score=float(data.get("clarity_score", 5.0)),
                completeness_score=float(data.get("completeness_score", 5.0)),
                word_count=len(original_text.split()),
                analyzed_at=datetime.now(timezone.utc),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse analysis response", error=str(e))
            return self._create_fallback_analysis(original_text, criteria)

    def _create_fallback_analysis(self, text: str, criteria) -> WritingAnalysis:
        """Create a basic analysis when AI parsing fails."""
        word_count = len(text.split())

        # Basic heuristic scoring based on word count and structure
        base_score = min(10.0, max(3.0, word_count / 100))

        section_scores = []
        for c in criteria:
            # Check if criterion name appears in text
            coverage = 0.5
            if c.name.lower() in text.lower():
                coverage = 0.7

            section_scores.append(SectionScore(
                criterion_name=c.name,
                score=base_score,
                score_label=get_score_label(base_score),
                coverage=coverage,
                strengths=[],
                gaps=["Unable to perform detailed analysis"],
                suggestions=["Consider reviewing " + c.name + " section"],
            ))

        return WritingAnalysis(
            overall_score=base_score,
            overall_label=get_score_label(base_score),
            section_scores=section_scores,
            structure_feedback="Basic analysis performed. Please try again for detailed feedback.",
            clarity_score=base_score,
            completeness_score=base_score,
            word_count=word_count,
            analyzed_at=datetime.now(timezone.utc),
        )

    def _generate_recommendations(self, section_scores: List[SectionScore]) -> List[str]:
        """Generate top recommendations from section scores."""
        recommendations = []

        # Sort by score (lowest first) to prioritize areas needing improvement
        sorted_scores = sorted(section_scores, key=lambda x: x.score)

        for score in sorted_scores[:3]:  # Top 3 areas needing work
            if score.gaps:
                for gap in score.gaps[:2]:
                    recommendations.append(f"{score.criterion_name}: {gap}")
            if score.suggestions:
                for suggestion in score.suggestions[:1]:
                    recommendations.append(f"{score.criterion_name}: {suggestion}")

        # Limit to 5 recommendations
        return recommendations[:5]

    async def suggest_improvements(
        self,
        db: AsyncSession,
        text: str,
        mechanism: str,
        section_type: str,
        max_suggestions: int = 10,
    ) -> SuggestionsResponse:
        """
        Suggest specific improvements based on criteria gaps.
        """
        # Get criteria
        criteria = await review_criteria_service.get_criteria_from_db(db, mechanism)
        if not criteria:
            criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)

        # Get relevant criteria for section
        relevant_criteria = criteria.criteria
        if section_type.lower() in SECTION_CRITERIA_MAP:
            criteria_names = SECTION_CRITERIA_MAP[section_type.lower()]
            relevant_criteria = [
                c for c in criteria.criteria
                if c.name.lower() in [n.lower() for n in criteria_names]
            ]
            if not relevant_criteria:
                relevant_criteria = criteria.criteria

        # Build prompt for suggestions
        criteria_info = "\n".join([
            f"- {c.name}: {c.description}\n  Common weaknesses: {', '.join(c.common_weaknesses[:2])}"
            for c in relevant_criteria
        ])

        prompt = f"""You are an expert grant writing consultant. Analyze this {section_type} section for a {mechanism} grant and suggest specific improvements.

REVIEW CRITERIA:
{criteria_info}

DRAFT TEXT:
---
{text}
---

Identify gaps in coverage and suggest specific improvements. Return JSON:
{{
    "gaps_identified": ["list of gaps in criterion coverage"],
    "criteria_coverage": {{"criterion_name": 0.8}},
    "suggestions": [
        {{
            "type": "add_content|remove_content|restructure|clarify|strengthen",
            "criterion": "Related criterion name",
            "priority": "high|medium|low",
            "description": "What should be changed",
            "rationale": "Why this change would help",
            "example": "Optional example of improved text"
        }}
    ]
}}

Focus on structure and completeness, not writing style. Limit to {max_suggestions} suggestions."""

        try:
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_suggestions_response(response.content[0].text, relevant_criteria)
        except Exception as e:
            logger.error("Failed to generate suggestions", error=str(e))
            return self._create_fallback_suggestions(relevant_criteria)

    def _parse_suggestions_response(
        self,
        response_text: str,
        criteria
    ) -> SuggestionsResponse:
        """Parse suggestions response."""
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            suggestions = []
            for s in data.get("suggestions", []):
                suggestion_type = s.get("type", "clarify")
                try:
                    stype = SuggestionType(suggestion_type)
                except ValueError:
                    stype = SuggestionType.CLARIFY

                suggestions.append(WritingSuggestion(
                    type=stype,
                    criterion=s.get("criterion", "General"),
                    priority=s.get("priority", "medium"),
                    description=s.get("description", ""),
                    rationale=s.get("rationale", ""),
                    example=s.get("example"),
                ))

            criteria_coverage = data.get("criteria_coverage", {})
            # Ensure all criteria have coverage scores
            for c in criteria:
                if c.name not in criteria_coverage:
                    criteria_coverage[c.name] = 0.5

            return SuggestionsResponse(
                suggestions=suggestions,
                gaps_identified=data.get("gaps_identified", []),
                criteria_coverage=criteria_coverage,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse suggestions", error=str(e))
            return self._create_fallback_suggestions(criteria)

    def _create_fallback_suggestions(self, criteria) -> SuggestionsResponse:
        """Create fallback suggestions when AI fails."""
        suggestions = []
        coverage = {}

        for c in criteria:
            coverage[c.name] = 0.5
            if c.tips:
                suggestions.append(WritingSuggestion(
                    type=SuggestionType.STRENGTHEN,
                    criterion=c.name,
                    priority="medium",
                    description=c.tips[0] if c.tips else f"Review {c.name} section",
                    rationale=c.description,
                    example=None,
                ))

        return SuggestionsResponse(
            suggestions=suggestions[:5],
            gaps_identified=["Unable to perform detailed analysis"],
            criteria_coverage=coverage,
        )

    async def get_feedback(
        self,
        db: AsyncSession,
        text: str,
        mechanism: str,
        section_type: str,
        focus_areas: Optional[List[str]] = None,
        grant_id: Optional[UUID] = None,
    ) -> FeedbackResponse:
        """
        Get AI-powered feedback on a draft section.

        Provides structured feedback mapped to review criteria.
        """
        # Get criteria
        criteria = await review_criteria_service.get_criteria_from_db(db, mechanism)
        if not criteria:
            criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)

        # Get grant context
        grant_context = ""
        if grant_id:
            grant = await db.get(Grant, grant_id)
            if grant:
                grant_context = f"Grant: {grant.title}\nAgency: {grant.agency or 'Unknown'}\n"

        # Build criteria focus
        criteria_focus = "\n".join([
            f"- {c.name}: {c.description}" for c in criteria.criteria
        ])

        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\nPay special attention to these areas: {', '.join(focus_areas)}"

        prompt = f"""You are an expert grant writing consultant reviewing a {section_type} section for a {mechanism} grant.

{grant_context}

REVIEW CRITERIA:
{criteria_focus}
{focus_instruction}

DRAFT TEXT:
---
{text}
---

Provide structured feedback. Return JSON:
{{
    "overall_assessment": "2-3 sentence overall assessment",
    "criterion_feedback": {{
        "Criterion Name": "Specific feedback for this criterion"
    }},
    "structural_suggestions": ["List of structural improvements"],
    "content_gaps": ["Missing content that should be addressed"],
    "specific_improvements": [
        {{"location": "where in text", "issue": "what's wrong", "suggestion": "how to fix"}}
    ],
    "strengths": ["What's working well"],
    "priority_actions": ["Top 3 priority actions to improve"]
}}

Focus on structure, completeness, and alignment with review criteria. Do not critique writing style."""

        try:
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_feedback_response(response.content[0].text, criteria.criteria)
        except Exception as e:
            logger.error("Failed to generate feedback", error=str(e))
            return self._create_fallback_feedback(criteria.criteria)

    def _parse_feedback_response(
        self,
        response_text: str,
        criteria
    ) -> FeedbackResponse:
        """Parse feedback response."""
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            return FeedbackResponse(
                overall_assessment=data.get("overall_assessment", "Feedback generated."),
                criterion_feedback=data.get("criterion_feedback", {}),
                structural_suggestions=data.get("structural_suggestions", []),
                content_gaps=data.get("content_gaps", []),
                specific_improvements=data.get("specific_improvements", []),
                strengths=data.get("strengths", []),
                priority_actions=data.get("priority_actions", []),
                generated_at=datetime.now(timezone.utc),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse feedback", error=str(e))
            return self._create_fallback_feedback(criteria)

    def _create_fallback_feedback(self, criteria) -> FeedbackResponse:
        """Create fallback feedback when AI fails."""
        criterion_feedback = {
            c.name: f"Review this section against {c.name} criterion: {c.description}"
            for c in criteria
        }

        return FeedbackResponse(
            overall_assessment="Unable to generate detailed feedback. Please try again.",
            criterion_feedback=criterion_feedback,
            structural_suggestions=["Review overall structure and organization"],
            content_gaps=["Unable to identify specific gaps"],
            specific_improvements=[],
            strengths=[],
            priority_actions=["Retry feedback generation"],
            generated_at=datetime.now(timezone.utc),
        )

    async def score_against_criteria(
        self,
        db: AsyncSession,
        text: str,
        mechanism: str,
    ) -> Dict[str, float]:
        """
        Score draft sections against each review criterion.
        Returns a dictionary of criterion names to scores (0-10).
        """
        # Get analysis
        analysis_response = await self.analyze_text(db, text, mechanism)

        # Extract scores
        scores = {}
        for section_score in analysis_response.analysis.section_scores:
            scores[section_score.criterion_name] = section_score.score

        return scores

    async def stream_feedback(
        self,
        db: AsyncSession,
        text: str,
        mechanism: str,
        section_type: str,
        focus_areas: Optional[List[str]] = None,
        grant_id: Optional[UUID] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI-powered feedback on a draft section using SSE events.

        Yields SSE-formatted events as feedback is generated:
        - event: feedback_start, data: {}
        - event: feedback_chunk, data: {"content": "..."}
        - event: feedback_end, data: {}

        Args:
            db: Database session
            text: Draft text to get feedback on
            mechanism: Grant mechanism code (e.g., R01, CAREER)
            section_type: Type of section being reviewed
            focus_areas: Optional list of areas to focus on
            grant_id: Optional grant ID for additional context

        Yields:
            SSE-formatted event strings
        """
        # Get criteria
        criteria = await review_criteria_service.get_criteria_from_db(db, mechanism)
        if not criteria:
            criteria = review_criteria_service.get_criteria_for_mechanism(mechanism)

        # Get grant context
        grant_context = ""
        if grant_id:
            grant = await db.get(Grant, grant_id)
            if grant:
                grant_context = f"Grant: {grant.title}\nAgency: {grant.agency or 'Unknown'}\n"

        # Build criteria focus
        criteria_focus = "\n".join([
            f"- {c.name}: {c.description}" for c in criteria.criteria
        ])

        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\nPay special attention to these areas: {', '.join(focus_areas)}"

        prompt = f"""You are an expert grant writing consultant reviewing a {section_type} section for a {mechanism} grant.

{grant_context}

REVIEW CRITERIA:
{criteria_focus}
{focus_instruction}

DRAFT TEXT:
---
{text}
---

Provide structured feedback on this draft. Focus on:

1. **Overall Assessment**: Start with a 2-3 sentence overall assessment.

2. **Criterion-by-Criterion Feedback**: For each relevant criterion, provide specific feedback.

3. **Structural Suggestions**: List any structural improvements needed.

4. **Content Gaps**: Identify missing content that should be addressed.

5. **Strengths**: Highlight what's working well.

6. **Priority Actions**: End with the top 3 priority actions to improve this draft.

Focus on structure, completeness, and alignment with review criteria. Do not critique writing style.

Write your feedback in a clear, readable format using markdown for structure."""

        # Emit start event
        yield self._format_sse_event("feedback_start", {})

        try:
            # Use streaming with the Anthropic client
            with self.client.messages.stream(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text_chunk in stream.text_stream:
                    if text_chunk:
                        yield self._format_sse_event("feedback_chunk", {"content": text_chunk})

            # Emit end event
            yield self._format_sse_event("feedback_end", {})

        except Exception as e:
            logger.error("Failed to stream feedback", error=str(e))
            # Emit error in the stream
            yield self._format_sse_event("feedback_error", {"error": str(e)})
            yield self._format_sse_event("feedback_end", {})

    def _format_sse_event(self, event_type: str, data: dict) -> str:
        """
        Format data as a Server-Sent Event (SSE).

        Args:
            event_type: The event type (e.g., 'feedback_start', 'feedback_chunk')
            data: The data payload to send

        Returns:
            SSE-formatted string
        """
        json_data = json.dumps(data)
        return f"event: {event_type}\ndata: {json_data}\n\n"


# Singleton instance
writing_assistant = WritingAssistantService()
