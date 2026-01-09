# AI Grant Insights Feature

## Overview
Add AI-powered insights to the grant detail page that generate **Eligibility Analysis** and **Writing Tips** when a user views a grant. Insights stream in real-time using Server-Sent Events (SSE) for a responsive experience.

**User Flow:**
1. User clicks on a grant from Dashboard
2. Grant detail page loads with new "AI Grant Insights" section
3. User clicks "Generate Insights" button
4. AI analyzes their profile against grant requirements
5. Two insights stream progressively: Eligibility Analysis & Writing Tips

---

## Architecture

```
User clicks "Generate Insights"
         │
         ▼
Frontend ──────► GET /api/insights/grant/{id}/stream
                         │
                         ▼
              ┌──────────────────────┐
              │  GrantInsightsService │
              │  ─────────────────── │
              │  • Fetch grant data  │
              │  • Fetch user profile│
              │  • Build prompts     │
              │  • Stream via Claude │
              └──────────────────────┘
                         │
                         ▼
              SSE Events stream back:
              ─────────────────────────
              event: eligibility_start
              event: eligibility_chunk → data: {"content": "..."}
              event: eligibility_end
              event: writing_start
              event: writing_chunk → data: {"content": "..."}
              event: writing_end
```

---

## Files Created

### 1. Backend Service: `backend/services/grant_insights.py`

Core service for AI insight generation with streaming.

```python
class GrantInsightsService:
    async def stream_eligibility_analysis(db, user, grant_id) -> AsyncGenerator[str]
    async def stream_writing_tips(db, user, grant_id) -> AsyncGenerator[str]
    def _build_researcher_context(user, lab_profile) -> str
    def _build_grant_context(grant, match) -> str
```

**Key Implementation Details:**
- Use `anthropic.Anthropic()` client with `stream=True`
- Model: `settings.llm_model` (claude-sonnet-4-20250514)
- Max tokens: 2048 per insight
- Include user's lab_profile (research_areas, career_stage, past_grants)
- Include grant's eligibility JSONB, categories, funding range, deadline

### 2. Backend API: `backend/api/insights.py`

SSE streaming endpoint.

```python
@router.get("/grant/{grant_id}/stream")
async def stream_grant_insights(
    grant_id: UUID,
    insight_type: Literal["eligibility", "writing_tips", "both"] = "both",
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> StreamingResponse
```

### 3. Frontend Component: `frontend/src/components/GrantInsights.tsx`

Main UI component with streaming display and tabs for Eligibility Analysis and Writing Tips.

---

## Prompt Engineering

### Eligibility Analysis Prompt
```
You are an expert grant eligibility advisor. Analyze whether this researcher qualifies.

RESEARCHER PROFILE:
- Research Areas: {research_areas}
- Career Stage: {career_stage}
- Institution: {institution}
- Past Grants: {past_grants_summary}

GRANT REQUIREMENTS:
- Title: {grant_title}
- Agency: {agency}
- Eligibility Criteria: {eligibility_json}
- Focus Areas: {categories}
- Funding: ${amount_min} - ${amount_max}

Provide:
1. **Overall Assessment** - Verdict with confidence (Eligible/Likely Eligible/Uncertain/Not Eligible)
2. **Requirements Check** - Systematic review of each criterion
3. **Gaps Identified** - Missing qualifications or concerns
4. **Action Items** - Steps to confirm eligibility or address gaps
```

### Writing Tips Prompt
```
You are a grant writing consultant with expertise in {agency} funding priorities.

Provide actionable writing tips:
1. **Key Themes to Emphasize** - Based on funder priorities
2. **Research Alignment** - How to position their work
3. **Methodology Suggestions** - Technical approach tips
4. **Broader Impacts** - Relevant impact areas
5. **Common Pitfalls** - What to avoid
```

---

## Status: Implemented in Phase 3
