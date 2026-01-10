"""Funding alerts service for personalized email newsletters."""

import anthropic
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.models import User, Grant, Match, Deadline, FundingAlertPreference, LabProfile
from backend.schemas.alerts import (
    AlertFrequency,
    AlertGrantSummary,
    AlertDeadlineSummary,
    FundingAlertPreview,
)

logger = structlog.get_logger(__name__)


class FundingAlertsService:
    """Service for generating and sending funding alert emails."""

    def __init__(self):
        if settings.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            self.client = None

    async def get_or_create_preferences(self, db: AsyncSession, user_id: UUID) -> FundingAlertPreference:
        """Get or create funding alert preferences for a user."""
        result = await db.execute(select(FundingAlertPreference).where(FundingAlertPreference.user_id == user_id))
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = FundingAlertPreference(user_id=user_id)
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)

        return prefs

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: UUID,
        enabled: Optional[bool] = None,
        frequency: Optional[AlertFrequency] = None,
        min_match_score: Optional[int] = None,
        include_deadlines: Optional[bool] = None,
        include_new_grants: Optional[bool] = None,
        include_insights: Optional[bool] = None,
        preferred_funders: Optional[List[str]] = None,
    ) -> FundingAlertPreference:
        """Update funding alert preferences."""
        prefs = await self.get_or_create_preferences(db, user_id)

        if enabled is not None:
            prefs.enabled = enabled
        if frequency is not None:
            prefs.frequency = frequency.value
        if min_match_score is not None:
            prefs.min_match_score = min_match_score
        if include_deadlines is not None:
            prefs.include_deadlines = include_deadlines
        if include_new_grants is not None:
            prefs.include_new_grants = include_new_grants
        if include_insights is not None:
            prefs.include_insights = include_insights
        if preferred_funders is not None:
            prefs.preferred_funders = preferred_funders

        await db.commit()
        await db.refresh(prefs)
        return prefs

    async def preview_alert(self, db: AsyncSession, user: User) -> FundingAlertPreview:
        """Generate a preview of what the alert email would contain."""
        prefs = await self.get_or_create_preferences(db, user.id)

        if not prefs.enabled:
            return FundingAlertPreview(
                new_grants=[],
                upcoming_deadlines=[],
                personalized_insights=None,
                would_send=False,
                reason="Alerts are disabled",
            )

        # Get new matching grants
        new_grants = await self._get_new_grants(db, user, prefs)

        # Get upcoming deadlines
        deadlines = await self._get_upcoming_deadlines(db, user, prefs)

        # Generate personalized insights
        insights = None
        if prefs.include_insights and (new_grants or deadlines):
            insights = await self._generate_insights(db, user, new_grants, deadlines)

        would_send = bool(new_grants or deadlines)
        reason = None if would_send else "No new grants or upcoming deadlines"

        return FundingAlertPreview(
            new_grants=new_grants,
            upcoming_deadlines=deadlines,
            personalized_insights=insights,
            would_send=would_send,
            reason=reason,
        )

    async def _get_new_grants(
        self, db: AsyncSession, user: User, prefs: FundingAlertPreference
    ) -> List[AlertGrantSummary]:
        """Get new matching grants since last alert."""
        if not prefs.include_new_grants:
            return []

        since = prefs.last_sent_at or (datetime.now(timezone.utc) - timedelta(days=7))

        # Convert min_match_score (0-100) to match_score (0-1) for comparison
        min_score = prefs.min_match_score / 100.0

        # Get matches above threshold
        query = (
            select(Match, Grant)
            .join(Grant, Match.grant_id == Grant.id)
            .where(Match.user_id == user.id)
            .where(Match.match_score >= min_score)
            .where(Match.created_at > since)
            .order_by(Match.match_score.desc())
            .limit(10)
        )

        if prefs.preferred_funders:
            query = query.where(Grant.agency.in_(prefs.preferred_funders))

        result = await db.execute(query)
        matches = result.all()

        return [
            AlertGrantSummary(
                id=grant.id,
                title=grant.title,
                funder=grant.agency or "Unknown",
                mechanism=None,  # Grant model doesn't have mechanism field
                amount_max=grant.amount_max,
                deadline=grant.deadline,
                match_score=int(match.match_score * 100),
                match_reason=match.reasoning or "Strong alignment with your research",
            )
            for match, grant in matches
        ]

    async def _get_upcoming_deadlines(
        self, db: AsyncSession, user: User, prefs: FundingAlertPreference
    ) -> List[AlertDeadlineSummary]:
        """Get upcoming deadlines within the next 30 days."""
        if not prefs.include_deadlines:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=30)

        result = await db.execute(
            select(Deadline)
            .where(Deadline.user_id == user.id)
            .where(Deadline.status == "active")
            .where(Deadline.sponsor_deadline >= now)
            .where(Deadline.sponsor_deadline <= cutoff)
            .order_by(Deadline.sponsor_deadline)
            .limit(10)
        )
        deadlines = result.scalars().all()

        return [
            AlertDeadlineSummary(
                id=d.id,
                title=d.title,
                funder=d.funder,
                sponsor_deadline=d.sponsor_deadline,
                days_until=(d.sponsor_deadline - now).days,
                priority=d.priority,
            )
            for d in deadlines
        ]

    async def _generate_insights(
        self,
        db: AsyncSession,
        user: User,
        grants: List[AlertGrantSummary],
        deadlines: List[AlertDeadlineSummary],
    ) -> Optional[str]:
        """Generate personalized insights using Claude."""
        if not self.client:
            logger.warning("Anthropic client not configured, skipping insights generation")
            return None

        # Get user's research profile
        profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        profile_context = ""
        if profile:
            areas = ", ".join(profile.research_areas or [])
            profile_context = f"Research areas: {areas}. Career stage: {profile.career_stage or 'Unknown'}"

        grants_context = "\n".join(
            [f"- {g.title} ({g.funder}, {g.match_score}% match, deadline: {g.deadline})" for g in grants[:5]]
        )

        deadlines_context = "\n".join([f"- {d.title} ({d.funder}, {d.days_until} days)" for d in deadlines[:5]])

        prompt = f"""You are a grant advisor helping a researcher. Generate 2-3 personalized insights (max 150 words total) based on their current opportunities.

Researcher: {user.name or user.email}
{profile_context}

New Matching Grants:
{grants_context or "No new grants this period"}

Upcoming Deadlines:
{deadlines_context or "No upcoming deadlines"}

Provide actionable insights like:
- Which opportunity to prioritize
- Deadline warnings
- Funding trends in their area
- Strategic advice

Keep it concise and actionable."""

        try:
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error("Failed to generate insights", error=str(e))
            return None

    def generate_email_html(self, user: User, preview: FundingAlertPreview) -> str:
        """Generate HTML email content."""
        # Build grants section
        grants_html = ""
        if preview.new_grants:
            grants_html = "<h2>New Grant Matches</h2><ul>"
            for g in preview.new_grants:
                deadline_str = g.deadline.strftime("%b %d, %Y") if g.deadline else "Open"
                amount_str = f"${g.amount_max:,}" if g.amount_max else "Varies"
                grants_html += f"""
                <li style="margin-bottom: 15px;">
                    <strong>{g.title}</strong><br>
                    <span style="color: #666;">{g.funder} | {g.mechanism or "Various"}</span><br>
                    <span style="color: #2563eb;">Match Score: {g.match_score}%</span> |
                    Funding: {amount_str} | Deadline: {deadline_str}
                </li>"""
            grants_html += "</ul>"

        # Build deadlines section
        deadlines_html = ""
        if preview.upcoming_deadlines:
            deadlines_html = "<h2>Upcoming Deadlines</h2><ul>"
            for d in preview.upcoming_deadlines:
                color = "#dc2626" if d.days_until <= 7 else "#f59e0b" if d.days_until <= 14 else "#16a34a"
                deadlines_html += f"""
                <li style="margin-bottom: 10px;">
                    <strong>{d.title}</strong><br>
                    <span style="color: {color};">{d.days_until} days remaining</span> -
                    {d.sponsor_deadline.strftime("%b %d, %Y")}
                </li>"""
            deadlines_html += "</ul>"

        # Build insights section
        insights_html = ""
        if preview.personalized_insights:
            insights_html = f"""
            <h2>Your Personalized Insights</h2>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
                {preview.personalized_insights}
            </div>"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; }}
                h1 {{ color: #1e40af; }}
                h2 {{ color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
            </style>
        </head>
        <body>
            <h1>GrantRadar Funding Alert</h1>
            <p>Hi {user.name or "Researcher"},</p>
            <p>Here's your personalized funding update:</p>

            {grants_html}
            {deadlines_html}
            {insights_html}

            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #6b7280; font-size: 14px;">
                <a href="{settings.frontend_url}/settings">Manage alert preferences</a> |
                <a href="{settings.frontend_url}/dashboard">View Dashboard</a>
            </p>
        </body>
        </html>
        """
