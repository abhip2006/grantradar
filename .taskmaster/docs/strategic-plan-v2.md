# GrantRadar Strategic Plan v2: Research Funding Operating System

## Executive Summary

Transform GrantRadar from a "grant search engine" into a "research funding operating system" that owns the complete workflow from discovery to submission, creating data network effects competitors cannot replicate.

---

## Core Strategic Insight

Every grant platform (including competitors like Atom Grants) treats grants as a **search problem**. This is fundamentally wrong.

**The real problem isn't discovery—it's decision-making under uncertainty.**

Researchers don't want to "find grants." They want to:
1. Know which grants they can realistically win
2. Understand the effort/reward tradeoff before investing weeks in an application
3. Time their applications to maximize success probability
4. Build a sustainable funding pipeline, not chase individual opportunities

---

## Strategic Pillars

### Pillar 1: Win Probability Engine

**Current state**: Match scores based on keyword/semantic similarity.

**Target state**: Genuine win probability predictions.

#### Components:
- Historical win rate data by funding agency, grant type, career stage, institution tier
- Competition intensity signals: How many researchers match this grant? Typical applicant pool?
- Timing patterns: Some grants have implicit quotas by region/institution type
- Track record analysis: First-time applicants vs. renewals vs. established PIs success rates

#### Value Proposition:
Transform from "this grant matches your profile" to "you have a 23% chance of winning this $500K grant based on 847 similar applications."

#### Data Sources:
- NIH Reporter (publicly available funded project data)
- NSF Award Search
- User outcome tracking (did they apply? did they win?)

---

### Pillar 2: Application Portfolio Optimization

**Concept**: Researchers should think in portfolios, not individual grants.

#### Key Question to Answer:
"Given 40 hours/month for grant writing, what's the optimal portfolio of 3-5 applications that maximizes expected funding over the next 18 months?"

#### Components:
- Time-to-apply estimates by grant type
- Deadline clustering analysis (avoid burnout from overlapping deadlines)
- Correlation modeling (don't apply to 5 NIH R01s simultaneously—review panels overlap)
- Career stage progression modeling (when to chase big grants vs. build track record)

#### Implementation:
- Portfolio view showing all saved/tracked grants with timeline
- Optimization algorithm suggesting portfolio adjustments
- Effort estimation per grant mechanism

---

### Pillar 3: Grant Intelligence Graph

**Concept**: Knowledge graph connecting grants, funded projects, review criteria, and success patterns.

#### Entities:
- **Grants** ↔ **Funded Projects** (what actually gets funded?)
- **Grants** ↔ **Review Criteria** (extracted from review guidelines, program announcements)
- **Grants** ↔ **Program Officers** (who decides, what are their stated priorities?)
- **Researchers** ↔ **Success Patterns** (de-identified: what profile features correlate with wins?)

#### Enabled Features:
- "Grants like yours that were funded typically emphasized X"
- "This program officer has funded 60% translational research, 40% basic science"
- "Successful applicants to this mechanism average 12 publications and 2 prior grants"

---

### Pillar 4: Grant Writing Copilot

**Current state**: Basic AI chat about grants.

**Target state**: Deep integration into the writing process.

#### Components:
- **Specific Aims Analyzer**: "Your aims are too broad for an R21. Scope recommendation: focus on Aim 2."
- **Budget Validator**: "Your personnel costs are 15% above typical awards for this mechanism."
- **Review Criteria Mapper**: Maps draft sections to explicit review criteria, highlights gaps
- **Preliminary Data Assessor**: "Strong applicants typically include 3-5 figures of preliminary data. You have 2."

#### Switching Cost: Researchers who've built applications in our system won't leave.

---

### Pillar 5: Institutional Intelligence Layer

**Target customers**: Research offices, not just individual researchers.

#### Features:
- Portfolio view across all faculty
- Deadline coordination to avoid internal competition
- Institutional success rate benchmarking
- Compliance requirement tracking by funding source

#### Revenue model: B2B enterprise tier with institutional lock-in.

---

## Data Network Effects (The Moat)

```
More users → More application data → Better win probability models
     ↓                                           ↓
Better recommendations ← More value ← Higher success rates
```

### Data to Collect:
1. Which matches led to applications (implicit relevance signal)
2. Application outcomes (win/lose/revised)
3. User profiles correlated with outcomes
4. De-identified benchmark datasets

**Timeline**: Within 2 years, this data becomes impossible to replicate.

---

## Complete Product Vision: 7-Stage Workflow

1. **Profile** → Continuous learning from publications, funded work
2. **Discovery** → Proactive, personalized, with win probability
3. **Decision** → Portfolio optimization with time/effort modeling
4. **Writing** → Deep copilot integration with review criteria mapping
5. **Submission** → Deadline management, compliance checking, institutional coordination
6. **Tracking** → Post-submission status, revision recommendations
7. **Learning** → Outcome feedback improving all models

**Competitive position**: Atom Grants and others stuck at stages 1-2. Owning stages 3-7 creates massive differentiation.

---

## Implementation Priorities

### Phase 1: Foundation (Current Sprint)
1. **Outcome Tracking** - Add "Did you apply?" and "Application result" tracking to matches
2. **Portfolio View** - Dashboard showing all saved grants with timeline visualization
3. **Win Probability v1** - Simple model using NIH Reporter success rates by mechanism

### Phase 2: Intelligence Layer
4. **Grant Intelligence Graph** - Begin indexing funded projects and review criteria
5. **Competition Intensity** - Show estimated applicant pool per grant
6. **Time Estimation** - Add effort estimates per grant mechanism

### Phase 3: Copilot Integration
7. **Writing Assistant v1** - Review criteria extraction and mapping
8. **Budget Templates** - Pre-filled budgets based on mechanism averages
9. **Specific Aims Analysis** - AI feedback on scope and structure

### Phase 4: Enterprise Features
10. **Institutional Dashboard** - Multi-user portfolio views
11. **Compliance Engine** - Track requirements by funder
12. **Team Collaboration** - Shared grant tracking and assignment

---

## Success Metrics

### User Engagement
- % of matches with outcome tracking completed
- Time spent in portfolio view
- Return visit frequency

### Model Quality
- Win probability calibration (predicted vs actual success rates)
- User feedback on predictions

### Business Metrics
- User retention (30/60/90 day)
- Conversion to premium features
- Institutional accounts

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Win probability accuracy | Start with mechanism-level averages, refine with user data |
| Data collection resistance | Make tracking effortless, show immediate value |
| Competitive response | Move fast, build data moat early |
| Engineering complexity | Modular implementation, validate each piece |

---

## Next Actions

1. Design outcome tracking UI/UX
2. Create grant portfolio dashboard component
3. Integrate NIH Reporter API for success rate data
4. Build win probability model v1
5. Design grant intelligence graph schema

---

*Document created: January 8, 2026*
*Version: 2.0*
