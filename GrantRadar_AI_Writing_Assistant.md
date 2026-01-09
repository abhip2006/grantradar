# GrantRadar AI Grant Writing Assistant
## Comprehensive Technical Specification

---

# Executive Summary

The AI Grant Writing Assistant transforms GrantRadar from a productivity tool into an intelligent co-author for grant applications. Unlike the basic AI-Assisted Drafting (F2.2) which handles only boilerplate sections, the Writing Assistant helps PIs with the core intellectual content that consumes 60-80 hours per major application.

**Key Differentiator:** We're not replacing the PI's scientific expertise — we're amplifying it by handling the *craft* of grant writing while the PI focuses on the *science*.

---

# 1. Product Philosophy

## 1.1 What We Do

| Capability | Description |
|------------|-------------|
| Structure | Guide optimal organization for each section |
| Clarity | Transform complex ideas into reviewer-friendly prose |
| Completeness | Ensure all required elements are present |
| Alignment | Optimize for funder priorities and review criteria |
| Iteration | Provide revision suggestions from reviewer perspective |

## 1.2 What We Don't Do

| Boundary | Rationale |
|----------|-----------|
| Generate scientific hypotheses | PI's domain expertise required |
| Fabricate preliminary data | Integrity violation |
| Write complete proposals from scratch | Quality/authenticity concerns |
| Guarantee funding | No AI can predict reviewer behavior |

## 1.3 Interaction Model

The assistant operates as a **sophisticated editor and writing coach**, not a ghostwriter:

1. PI provides scientific content (ideas, data, methods)
2. AI helps structure, refine, and strengthen the writing
3. PI reviews, edits, and owns final output
4. System learns from PI's preferences over time

---

# 2. Feature Overview

## 2.1 Feature Map

```
AI Grant Writing Assistant
├── F4.1: Specific Aims Composer
│   ├── Structure wizard
│   ├── Real-time feedback
│   ├── Aim optimization
│   └── Impact framing
│
├── F4.2: Research Strategy Builder
│   ├── Significance helper
│   ├── Innovation framer
│   ├── Approach architect
│   └── Rigor & reproducibility
│
├── F4.3: Writing Enhancement Engine
│   ├── Clarity optimizer
│   ├── Conciseness editor
│   ├── Tone calibrator
│   └── Flow improver
│
├── F4.4: Literature & Context Assistant
│   ├── Gap identification
│   ├── Citation suggester
│   ├── Competitor analysis
│   └── Field positioning
│
├── F4.5: Reviewer Simulation
│   ├── Critique prediction
│   ├── Weakness identification
│   ├── Score estimation
│   └── Revision prioritization
│
└── F4.6: Adaptive Learning
    ├── PI style learning
    ├── Success pattern analysis
    └── Personalized suggestions
```

## 2.2 Development Priority

| Feature | Priority | Engineering | Value |
|---------|----------|-------------|-------|
| F4.1 Specific Aims Composer | P0 | 4 weeks | Critical - gate to funding |
| F4.3 Writing Enhancement | P0 | 3 weeks | Universal applicability |
| F4.2 Research Strategy Builder | P1 | 5 weeks | High time savings |
| F4.5 Reviewer Simulation | P1 | 4 weeks | Unique differentiation |
| F4.4 Literature Assistant | P2 | 3 weeks | Nice to have |
| F4.6 Adaptive Learning | P2 | 4 weeks | Long-term retention |

---

# 3. F4.1: Specific Aims Composer

## 3.1 Overview

**Purpose:** Guide PIs through creating compelling Specific Aims pages with real-time AI assistance

**User Value:** Reduce Specific Aims drafting from 15-20 hours to 4-6 hours while improving quality

**Engineering Estimate:** 4 weeks

## 3.2 The Specific Aims Formula

The assistant guides users through the proven structure:

```
┌─────────────────────────────────────────────────────────┐
│ OPENING HOOK (2-3 sentences)                            │
│ "The problem is urgent because..."                      │
├─────────────────────────────────────────────────────────┤
│ KNOWLEDGE GAP (2-3 sentences)                           │
│ "What remains unknown is..."                            │
├─────────────────────────────────────────────────────────┤
│ LONG-TERM GOAL (1 sentence)                             │
│ "The long-term goal of this research program is..."     │
├─────────────────────────────────────────────────────────┤
│ OVERALL OBJECTIVE (1-2 sentences)                       │
│ "The objective of this application is..."               │
├─────────────────────────────────────────────────────────┤
│ CENTRAL HYPOTHESIS (1-2 sentences)                      │
│ "Our central hypothesis is that..."                     │
├─────────────────────────────────────────────────────────┤
│ RATIONALE (2-3 sentences)                               │
│ "This hypothesis is supported by our preliminary        │
│  data showing..."                                       │
├─────────────────────────────────────────────────────────┤
│ AIMS (3-5 sentences each)                               │
│ Aim 1: [Verb] [specific objective] [approach summary]   │
│ Aim 2: [Verb] [specific objective] [approach summary]   │
│ Aim 3: [Verb] [specific objective] [approach summary]   │
├─────────────────────────────────────────────────────────┤
│ EXPECTED OUTCOMES (2-3 sentences)                       │
│ "Upon completion, we will have..."                      │
├─────────────────────────────────────────────────────────┤
│ IMPACT STATEMENT (2-3 sentences)                        │
│ "This work is significant because it will..."           │
└─────────────────────────────────────────────────────────┘
```

## 3.3 Functional Requirements

### FR-4.1.1: Guided Composition Mode

**Step 1: Project Context Collection**
```
Inputs collected:
- Research area/field (dropdown + free text)
- Target funder and mechanism
- 2-3 sentence description of what you're proposing
- Key preliminary findings (bullets or paragraph)
- Target study section (if known)
```

**Step 2: Section-by-Section Building**

For each section, the system:
1. Explains what the section should accomplish
2. Shows 2-3 examples from successful grants (anonymized)
3. Provides a structured input form or free-text area
4. Generates AI-enhanced draft based on input
5. Offers refinement suggestions

**Step 3: Integration & Polish**
- Combines sections into full page
- Checks flow and transitions
- Validates page limit
- Suggests final refinements

### FR-4.1.2: Real-Time Feedback Panel

As the user writes, a sidebar displays:

```
┌─────────────────────────────────┐
│ STRUCTURE CHECK                 │
│ ✓ Hook present                  │
│ ✓ Gap clearly stated            │
│ ⚠ Hypothesis could be stronger  │
│ ✓ 3 aims defined                │
│ ✗ Impact statement missing      │
├─────────────────────────────────┤
│ WRITING QUALITY                 │
│ Clarity: 78/100                 │
│ Conciseness: 82/100             │
│ Reviewer-friendliness: 71/100   │
├─────────────────────────────────┤
│ AIM ANALYSIS                    │
│ Aim 1: Independent ✓            │
│ Aim 2: Depends on Aim 1 ⚠       │
│ Aim 3: Independent ✓            │
├─────────────────────────────────┤
│ PAGE STATUS                     │
│ Current: 0.87 pages             │
│ Target: 1.0 page                │
│ Room for: ~150 more words       │
└─────────────────────────────────┘
```

### FR-4.1.3: Hook Generator

**Input Form:**
```
1. What disease/problem does your research address?
   [Cancer, Alzheimer's, Climate, etc.]

2. What is the current burden? (statistics, impact)
   [e.g., "500,000 deaths annually", "costs $300B/year"]

3. Why is the current approach insufficient?
   [e.g., "Current therapies fail in 60% of patients"]

4. What makes this moment opportune?
   [e.g., "Recent discoveries in X enable new approaches"]
```

**AI Output Options:**
```
Option A (Urgency-focused):
"Pancreatic cancer kills 47,000 Americans annually with a 
5-year survival rate of just 11%—the lowest of any major 
cancer. Despite decades of research, no targeted therapy 
has significantly improved outcomes, largely because..."

Option B (Discovery-focused):
"The recent identification of KRAS G12C inhibitors has 
revolutionized treatment of KRAS-mutant lung cancers, yet 
pancreatic cancer—where KRAS mutations occur in >90% of 
cases—remains stubbornly resistant to these approaches..."

Option C (Impact-focused):
"Pancreatic cancer will surpass breast and colorectal 
cancer to become the second leading cause of cancer death 
by 2030. This trajectory is not inevitable: our preliminary 
data suggest a fundamentally new therapeutic strategy..."
```

### FR-4.1.4: Hypothesis Strengthener

Analyzes hypothesis and suggests improvements:

**Input:**
```
"We think that inhibiting protein X will reduce tumor growth"
```

**AI Analysis:**
```
Issues detected:
- Weak verb ("think" → "hypothesize")
- Lacks specificity (which tumors? by how much?)
- Missing mechanism (why would this work?)
- No testability criteria

Suggested revision:
"We hypothesize that pharmacological inhibition of protein X 
will reduce pancreatic tumor growth by >50% through disruption 
of the X-Y signaling axis, which our preliminary data show is 
hyperactivated in 78% of patient samples."

Strengthening elements added:
✓ Quantifiable outcome (>50%)
✓ Specific mechanism (X-Y signaling)
✓ Preliminary data reference (78% of samples)
✓ Testable prediction
```

### FR-4.1.5: Aim Independence Analyzer

```
Aim 1: Determine the mechanism by which X activates Y
Aim 2: Test whether blocking Y reduces tumor growth
Aim 3: Develop biomarkers of Y pathway activation

Analysis:
┌─────────────────────────────────────────────────────────┐
│ DEPENDENCY MATRIX                                       │
│                                                         │
│              Aim 1    Aim 2    Aim 3                    │
│ Aim 1         -       feeds    feeds                    │
│ Aim 2       needs       -      parallel                 │
│ Aim 3       needs    parallel    -                      │
│                                                         │
│ ⚠ WARNING: Aims 2 and 3 depend on Aim 1 succeeding     │
│                                                         │
│ RISK: If Aim 1 fails to identify mechanism, Aims 2-3   │
│ lose rationale. Consider:                               │
│                                                         │
│ Option A: Reframe Aim 1 as "characterize" rather than  │
│ "determine" - allows partial success                    │
│                                                         │
│ Option B: Add alternative approach to Aim 2 that works │
│ even if mechanism is unclear                            │
│                                                         │
│ Option C: Make Aim 3 independent by focusing on        │
│ clinical correlation rather than mechanistic biomarker │
└─────────────────────────────────────────────────────────┘
```

### FR-4.1.6: Impact Statement Generator

**Input:**
```
Field: Cancer biology
Specific area: Pancreatic cancer immunotherapy
Key innovation: Novel CAR-T target
Expected outcomes: Preclinical efficacy data
```

**Generated Options:**
```
Option A (Field advancement):
"This research will establish [target] as a validated 
therapeutic target in pancreatic cancer, opening new 
avenues for immunotherapy in a disease that has proven 
largely resistant to current immune-based approaches."

Option B (Clinical translation):
"Successful completion of these aims will provide the 
preclinical foundation for a first-in-human trial of 
[target]-directed CAR-T therapy, potentially offering 
a new treatment option for the 60,000 patients diagnosed 
with pancreatic cancer annually."

Option C (Mechanistic insight):
"Beyond its therapeutic implications, this work will 
reveal fundamental principles of immune evasion in 
pancreatic cancer that may apply broadly to other 
'cold' tumor types resistant to immunotherapy."
```

## 3.4 Data Model

```sql
CREATE TABLE aims_compositions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  document_id         UUID REFERENCES documents(id),
  
  -- Project context
  research_field      VARCHAR(255),
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  study_section       VARCHAR(100),
  project_summary     TEXT,
  preliminary_data    TEXT,
  
  -- Section content (user input + AI enhanced)
  sections            JSONB NOT NULL,
  -- {
  --   "hook": { 
  --     "user_input": "...", 
  --     "ai_enhanced": "...",
  --     "version": 3,
  --     "selected": "ai_enhanced"
  --   },
  --   "gap": { ... },
  --   "hypothesis": { ... },
  --   "aims": [
  --     { "title": "...", "description": "...", "approach": "..." }
  --   ],
  --   "impact": { ... }
  -- }
  
  -- Analysis results
  structure_score     INTEGER,
  quality_score       INTEGER,
  aim_dependency      JSONB,
  feedback_items      JSONB,
  
  -- Metadata
  current_version     INTEGER DEFAULT 1,
  status              VARCHAR(50) DEFAULT 'draft',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE aims_composition_versions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  composition_id      UUID NOT NULL REFERENCES aims_compositions(id),
  version_number      INTEGER NOT NULL,
  sections            JSONB NOT NULL,
  scores              JSONB,
  created_at          TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(composition_id, version_number)
);

CREATE TABLE aims_examples (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  funder              VARCHAR(100),
  mechanism           VARCHAR(100),
  research_field      VARCHAR(255),
  
  section_type        VARCHAR(50), -- 'hook', 'gap', 'hypothesis', 'aim', 'impact'
  content             TEXT NOT NULL,
  
  quality_score       INTEGER, -- expert rating
  source              VARCHAR(50), -- 'foia', 'contributed', 'expert'
  is_anonymized       BOOLEAN DEFAULT TRUE,
  
  created_at          TIMESTAMP DEFAULT NOW()
);
```

## 3.5 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/aims-composer | Create new composition |
| GET | /api/v1/aims-composer/:id | Get composition |
| PATCH | /api/v1/aims-composer/:id | Update sections |
| POST | /api/v1/aims-composer/:id/generate/:section | Generate section content |
| POST | /api/v1/aims-composer/:id/analyze | Run full analysis |
| GET | /api/v1/aims-composer/:id/feedback | Get real-time feedback |
| POST | /api/v1/aims-composer/:id/export | Export to document |
| GET | /api/v1/aims-examples | Get examples by field/funder |

## 3.6 AI Prompts

### Hook Generation Prompt

```
SYSTEM:
You are an expert NIH grant writer helping a researcher craft 
a compelling opening hook for their Specific Aims page. The hook 
must:
1. Immediately grab reviewer attention
2. Establish urgency or significance of the problem
3. Be 2-3 sentences (40-60 words)
4. Use concrete statistics or facts when available
5. Avoid jargon that might alienate non-specialist reviewers

Generate 3 distinct options with different rhetorical approaches:
- Option A: Lead with burden/urgency
- Option B: Lead with recent discovery/opportunity  
- Option C: Lead with gap/paradox

USER:
Research area: {field}
Problem/disease: {problem}
Current burden: {burden_statistics}
Why current approaches fail: {current_limitations}
What makes this moment opportune: {opportunity}

OUTPUT FORMAT:
Provide 3 options, each 2-3 sentences. After each, note the 
rhetorical strategy used.
```

### Hypothesis Strengthening Prompt

```
SYSTEM:
You are a grant writing expert analyzing a research hypothesis.
Evaluate it against these criteria:
1. Specificity: Does it name specific molecules, processes, outcomes?
2. Testability: Can it be proven or disproven with proposed experiments?
3. Mechanism: Does it explain WHY the predicted outcome will occur?
4. Quantifiability: Does it predict measurable outcomes?
5. Preliminary data: Does it connect to existing evidence?

Provide:
1. Score (1-10) on each criterion
2. Specific issues identified
3. Revised hypothesis incorporating improvements
4. Explanation of changes made

USER:
Original hypothesis: {hypothesis}
Research field: {field}
Preliminary data available: {prelim_data}

OUTPUT: JSON with scores, issues, revision, and explanation
```

## 3.7 UI Components

### Guided Wizard View
- Step-by-step section builder
- Progress indicator
- Context panel showing previous sections
- Example drawer (slide-out with relevant examples)

### Free-Form Editor View
- Full-page rich text editor
- Floating feedback panel
- Inline AI suggestions (like Grammarly)
- Section markers with quality indicators

### Analysis Dashboard
- Radar chart of scores
- Dependency diagram for aims
- Issue list with priority
- Comparison to successful proposals

## 3.8 Acceptance Criteria

- AC-1: Guided wizard produces complete Specific Aims in under 2 hours
- AC-2: AI-generated hooks rated 4+/5 by expert reviewers 70% of time
- AC-3: Hypothesis strengthener improves clarity score by 20%+ 
- AC-4: Aim dependency analysis correctly identifies issues 85% of time
- AC-5: Real-time feedback updates within 2 seconds of edit
- AC-6: System handles all NIH mechanisms (R01, R21, K-series, F-series)

---

# 4. F4.2: Research Strategy Builder

## 4.1 Overview

**Purpose:** Guide PIs through the 12-page Research Strategy with section-specific AI assistance

**User Value:** Reduce Research Strategy drafting from 40-60 hours to 15-25 hours

**Engineering Estimate:** 5 weeks

## 4.2 Section Architecture

### NIH Research Strategy Structure

```
RESEARCH STRATEGY (12 pages for R01)
├── A. SIGNIFICANCE (2-3 pages)
│   ├── Importance of the problem
│   ├── Scientific premise
│   ├── Current state of knowledge
│   └── How this addresses critical gaps
│
├── B. INNOVATION (1-2 pages)
│   ├── Conceptual innovation
│   ├── Technical innovation
│   └── Methodological innovation
│
└── C. APPROACH (7-9 pages)
    ├── Overview / preliminary data
    ├── Aim 1
    │   ├── Rationale
    │   ├── Experimental design
    │   ├── Methods
    │   ├── Expected outcomes
    │   └── Potential problems & alternatives
    ├── Aim 2 [same structure]
    ├── Aim 3 [same structure]
    ├── Timeline
    └── Rigor & reproducibility
```

## 4.3 Functional Requirements

### FR-4.2.1: Significance Section Helper

**Knowledge Gap Articulation**
```
Input form:
1. What do we currently know about this topic?
   [Key established facts]

2. What remains unknown or controversial?
   [The gap your research addresses]

3. What are the consequences of this gap?
   [Why it matters that we don't know this]

4. How does your work address this gap?
   [Your specific contribution]
```

**AI Output:**
```
"While significant progress has been made in understanding 
[known facts], a critical gap remains: [unknown]. This gap 
is consequential because [consequences]. The proposed 
research directly addresses this gap by [your contribution], 
which will [expected advance]."
```

**Scientific Premise Strengthener**
```
Analyzes cited literature to:
- Identify if premise is well-supported
- Flag papers that might contradict premise
- Suggest additional citations to strengthen
- Note any rigor concerns in foundational studies
```

### FR-4.2.2: Innovation Framer

Helps articulate innovation across three dimensions:

**Conceptual Innovation**
```
Prompts:
- What new way of thinking does this introduce?
- What existing paradigm does this challenge?
- What connection between fields does this create?

AI helps frame:
"This work is conceptually innovative because it challenges 
the prevailing view that [old paradigm] by proposing that 
[new paradigm], based on our observation that [evidence]."
```

**Technical Innovation**
```
Prompts:
- What new technique or technology do you use?
- How is it better than existing approaches?
- What does it enable that wasn't possible before?

AI helps frame:
"We have developed [technique] that provides [advantage] 
over existing methods. This enables, for the first time, 
the ability to [new capability]."
```

**Methodological Innovation**
```
Prompts:
- What new combination of methods do you use?
- What new model system do you employ?
- What new analytical approach do you take?
```

### FR-4.2.3: Approach Architect

For each aim, guides through:

**Rationale Builder**
```
Input:
- Link to hypothesis element this aim tests
- Key preliminary data supporting this aim
- Why this aim is necessary (can't skip it)

Output:
"[Aim 1] will test the hypothesis that [specific hypothesis 
element]. This aim is motivated by our preliminary data 
showing [key finding], which suggests [interpretation]. 
Completion of this aim is essential because [necessity]."
```

**Experimental Design Assistant**
```
Input form:
- Independent variable(s)
- Dependent variable(s)  
- Controls (positive and negative)
- Sample size / power considerations
- Replicates and statistical approach
- Blinding procedures

AI analysis:
- Identifies missing controls
- Flags potential confounds
- Suggests appropriate statistical tests
- Checks for adequate power
- Notes rigor considerations
```

**Methods Optimizer**
```
For each method:
- User describes protocol
- AI suggests clarifications reviewers might want
- AI notes if method is standard (cite) vs novel (detail)
- AI checks for consistency with preliminary data methods
```

**Alternative Approaches Generator**
```
Input:
- What could go wrong with primary approach?
- What result would indicate failure?

AI generates:
"If [primary approach] fails to [expected outcome], 
we will pursue [alternative]. This alternative is 
viable because [rationale]. Preliminary evidence 
supporting this backup includes [evidence]."
```

### FR-4.2.4: Rigor & Reproducibility Assistant

Auto-generates compliant rigor section:

```
Based on proposal content, generates:

SCIENTIFIC RIGOR:
- Premise rigor: [assessment of foundational literature]
- Design rigor: [randomization, blinding, controls]
- Methodology rigor: [validated methods, appropriate models]
- Analysis rigor: [statistical approach, multiple testing]

BIOLOGICAL VARIABLES:
- Sex as biological variable: [how addressed]
- Age considerations: [if applicable]
- Other relevant variables: [as needed]

AUTHENTICATION:
- Cell lines: [authentication plan]
- Antibodies: [validation approach]
- Other key resources: [as listed]

REPRODUCIBILITY:
- Data recording: [approach]
- Protocol documentation: [approach]
- Reagent sharing: [plan]
```

### FR-4.2.5: Timeline Generator

**Input:**
```
Project duration: 5 years
Aims: [from Specific Aims]
Key milestones: [user defined]
Personnel: [from budget]
```

**Output:**
```
Generates Gantt-style timeline table showing:
- Aim 1 activities by quarter
- Aim 2 activities by quarter  
- Aim 3 activities by quarter
- Milestones marked
- Go/no-go decision points
- Manuscript/publication targets
- Trainee graduation targets (if applicable)
```

## 4.4 Data Model

```sql
CREATE TABLE strategy_compositions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  aims_composition_id UUID REFERENCES aims_compositions(id),
  document_id         UUID REFERENCES documents(id),
  
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  -- Section content
  significance        JSONB,
  -- {
  --   "importance": { "user_input": "...", "ai_enhanced": "..." },
  --   "premise": { ... },
  --   "current_knowledge": { ... },
  --   "gap_addressed": { ... }
  -- }
  
  innovation          JSONB,
  -- {
  --   "conceptual": { ... },
  --   "technical": { ... },
  --   "methodological": { ... }
  -- }
  
  approach            JSONB,
  -- {
  --   "overview": { ... },
  --   "aims": [
  --     {
  --       "aim_id": 1,
  --       "rationale": { ... },
  --       "experimental_design": { ... },
  --       "methods": [{ ... }],
  --       "expected_outcomes": { ... },
  --       "alternatives": { ... }
  --     }
  --   ],
  --   "timeline": { ... },
  --   "rigor": { ... }
  -- }
  
  -- Analysis
  completeness_score  INTEGER,
  section_scores      JSONB,
  feedback_items      JSONB,
  
  current_version     INTEGER DEFAULT 1,
  status              VARCHAR(50) DEFAULT 'draft',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE experimental_designs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id         UUID NOT NULL REFERENCES strategy_compositions(id),
  aim_number          INTEGER NOT NULL,
  
  design_type         VARCHAR(100),
  independent_vars    JSONB,
  dependent_vars      JSONB,
  controls            JSONB,
  sample_size         INTEGER,
  power_analysis      JSONB,
  statistical_tests   JSONB,
  blinding            TEXT,
  randomization       TEXT,
  
  ai_analysis         JSONB, -- issues, suggestions
  
  created_at          TIMESTAMP DEFAULT NOW()
);
```

## 4.5 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/strategy-builder | Create new composition |
| GET | /api/v1/strategy-builder/:id | Get composition |
| PATCH | /api/v1/strategy-builder/:id/:section | Update section |
| POST | /api/v1/strategy-builder/:id/generate/significance | Generate significance |
| POST | /api/v1/strategy-builder/:id/generate/innovation | Generate innovation |
| POST | /api/v1/strategy-builder/:id/generate/rationale/:aim | Generate aim rationale |
| POST | /api/v1/strategy-builder/:id/analyze-design/:aim | Analyze experimental design |
| POST | /api/v1/strategy-builder/:id/generate/rigor | Generate rigor section |
| POST | /api/v1/strategy-builder/:id/generate/timeline | Generate timeline |
| GET | /api/v1/strategy-builder/:id/feedback | Get real-time feedback |

## 4.6 Acceptance Criteria

- AC-1: Significance section passes NIH criterion check 80% of time
- AC-2: Innovation framing rated as "clear" by reviewers 75% of time
- AC-3: Experimental design analysis catches 90% of missing controls
- AC-4: Rigor section meets NIH requirements 100% of time
- AC-5: Timeline generation produces valid Gantt in under 30 seconds
- AC-6: Full Research Strategy composition in under 10 hours (vs 40-60)

---

# 5. F4.3: Writing Enhancement Engine

## 5.1 Overview

**Purpose:** Real-time writing assistance that improves clarity, conciseness, and reviewer-friendliness

**User Value:** Transform good science into compelling prose without hiring editors

**Engineering Estimate:** 3 weeks

## 5.2 Enhancement Categories

### 5.2.1 Clarity Optimizer

**Jargon Detector**
```
Input: "We will utilize CRISPR-Cas9 to generate knockout 
mice for the RTK-PI3K-AKT-mTOR signaling axis components."

Analysis:
- "RTK-PI3K-AKT-mTOR" - complex acronym chain (expand first use)
- Assuming reviewer knows all pathway components

Suggestion: "We will use CRISPR-Cas9 to generate mice lacking 
key components of the RTK signaling pathway (specifically 
PI3K, AKT, and mTOR), which transmits growth signals from 
cell surface receptors to control cell survival."
```

**Sentence Complexity Reducer**
```
Input: "Given that the phosphorylation of AKT at S473 by 
mTORC2, which is itself activated by growth factor receptor 
signaling in a PI3K-dependent manner, is required for full 
AKT activity, we hypothesize that inhibiting mTORC2 will 
reduce tumor growth."

Analysis:
- 52 words, 3 embedded clauses
- Readability: Difficult

Suggestion (split into 3 sentences):
"AKT phosphorylation at S473 is required for full kinase 
activity. This phosphorylation is mediated by mTORC2, which 
is activated downstream of PI3K. We therefore hypothesize 
that mTORC2 inhibition will reduce tumor growth by 
preventing full AKT activation."
```

**Ambiguity Resolver**
```
Input: "We will treat the cells and measure the response."

Issues:
- "cells" - which cells?
- "treat" - with what?
- "response" - which response?

Prompts user:
- Specify cell type
- Specify treatment
- Specify outcome measure
```

### 5.2.2 Conciseness Editor

**Wordiness Reduction**
```
Wordy phrases → Concise alternatives:

"in order to" → "to"
"due to the fact that" → "because"
"it is important to note that" → [delete]
"a number of" → "several" or [specific number]
"has the ability to" → "can"
"at the present time" → "currently" or "now"
"in the event that" → "if"
"conduct an investigation of" → "investigate"
```

**Redundancy Eliminator**
```
Input: "We will determine whether or not the treatment 
is effective or not by measuring tumor size."

Issues:
- "whether or not" redundant
- "or not" at end redundant

Fixed: "We will determine whether the treatment is 
effective by measuring tumor size."
```

**Passive to Active Voice**
```
Input: "The cells were treated with the drug and 
viability was measured after 24 hours."

Suggestion: "We treated cells with the drug and 
measured viability after 24 hours."
```

### 5.2.3 Tone Calibrator

**Confidence Balancing**
```
Too weak:
"We hope to possibly show that X might be true."

Too strong:
"We will definitively prove that X is true."

Balanced:
"We will test whether X is true by [specific experiment]."
```

**Hedging Optimization**
```
Appropriate hedges for different contexts:

Preliminary data: "suggest," "indicate," "are consistent with"
Hypothesis: "hypothesize," "propose," "predict"
Expected results: "expect," "anticipate," "will likely"
Uncertain outcomes: "may," "might," "could potentially"
```

### 5.2.4 Flow Improver

**Transition Suggester**
```
Detects paragraph breaks without transitions.

Suggests appropriate connectors:
- Addition: "Furthermore," "Additionally," "Moreover,"
- Contrast: "However," "In contrast," "Alternatively,"
- Cause/effect: "Therefore," "Consequently," "Thus,"
- Sequence: "First," "Subsequently," "Finally,"
- Example: "For instance," "Specifically," "In particular,"
```

**Paragraph Coherence Checker**
```
Analyzes each paragraph for:
- Topic sentence present
- Supporting sentences relate to topic
- Logical progression
- Appropriate length (5-8 sentences ideal)

Flags:
- Paragraphs over 10 sentences
- Paragraphs with multiple topics
- Missing topic sentences
```

## 5.3 Implementation

### Real-Time Analysis Pipeline

```
User types → Debounce (500ms) → 
  Sentence extraction →
    Parallel analysis:
      - Clarity model
      - Conciseness rules
      - Tone classifier
      - Flow checker
  → Aggregate suggestions →
    Prioritize (severity + relevance) →
      Display inline + sidebar
```

### Suggestion Display

**Inline Mode (like Grammarly)**
```
Underlines with colors:
- Blue: Clarity suggestion
- Green: Conciseness suggestion  
- Purple: Tone suggestion
- Yellow: Flow suggestion

Hover shows suggestion with accept/dismiss
```

**Sidebar Mode**
```
Grouped by category
Sorted by severity
Click jumps to location
Bulk accept for rule-based fixes
```

## 5.4 Data Model

```sql
CREATE TABLE writing_sessions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  document_id         UUID REFERENCES documents(id),
  
  session_start       TIMESTAMP DEFAULT NOW(),
  session_end         TIMESTAMP,
  
  -- Metrics
  initial_word_count  INTEGER,
  final_word_count    INTEGER,
  suggestions_shown   INTEGER,
  suggestions_accepted INTEGER,
  suggestions_dismissed INTEGER,
  
  -- Scores over time
  score_history       JSONB
  -- [{ timestamp, clarity, conciseness, tone, flow }]
);

CREATE TABLE writing_suggestions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id          UUID NOT NULL REFERENCES writing_sessions(id),
  
  category            VARCHAR(50), -- 'clarity', 'conciseness', 'tone', 'flow'
  rule_id             VARCHAR(100),
  severity            VARCHAR(20), -- 'high', 'medium', 'low'
  
  original_text       TEXT,
  suggested_text      TEXT,
  explanation         TEXT,
  
  location_start      INTEGER, -- character offset
  location_end        INTEGER,
  
  status              VARCHAR(20), -- 'pending', 'accepted', 'dismissed'
  resolved_at         TIMESTAMP,
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_writing_preferences (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  -- Rule preferences
  disabled_rules      VARCHAR(100)[],
  severity_overrides  JSONB,
  
  -- Style preferences (learned)
  avg_sentence_length INTEGER,
  passive_voice_tolerance DECIMAL(3,2),
  jargon_level        VARCHAR(20), -- 'low', 'medium', 'high'
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);
```

## 5.5 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/writing/analyze | Analyze text block |
| POST | /api/v1/writing/enhance | Get enhanced version |
| GET | /api/v1/writing/suggestions | Get suggestions for text |
| POST | /api/v1/writing/suggestions/:id/accept | Accept suggestion |
| POST | /api/v1/writing/suggestions/:id/dismiss | Dismiss suggestion |
| GET | /api/v1/writing/preferences | Get user preferences |
| PATCH | /api/v1/writing/preferences | Update preferences |
| GET | /api/v1/writing/stats | Get writing statistics |

## 5.6 Acceptance Criteria

- AC-1: Real-time suggestions appear within 2 seconds of typing pause
- AC-2: Clarity score improves by 15%+ when suggestions accepted
- AC-3: False positive rate under 10% for rule-based suggestions
- AC-4: Users accept 40%+ of suggestions (indicating relevance)
- AC-5: System handles 50+ page documents without performance degradation
- AC-6: User can disable specific rules/categories

---

# 6. F4.4: Literature & Context Assistant

## 6.1 Overview

**Purpose:** Help PIs position their work within the scientific literature and identify gaps

**User Value:** Reduce literature review time from 10-15 hours to 3-5 hours

**Engineering Estimate:** 3 weeks

## 6.2 Capabilities

### 6.2.1 Gap Identification

**Input:**
- Research area description
- Key papers the PI knows about
- Proposed hypothesis

**Output:**
```
LITERATURE LANDSCAPE ANALYSIS

Key themes in recent literature (2020-2025):
1. [Theme A] - 47 papers
2. [Theme B] - 32 papers
3. [Theme C] - 28 papers

Identified gaps:
1. "Most studies focus on X, but Y remains unexplored"
   - Supporting evidence: [citations]
   - Relevance to your work: HIGH

2. "Conflicting results between [Lab A] and [Lab B] 
    regarding mechanism of..."
   - Opportunity: Resolve controversy
   - Relevance: MEDIUM

3. "Technical limitation in current approaches..."
   - If your method addresses this: HIGH
   
Your proposed work fills gap #1 most directly.
Recommend emphasizing this in Significance section.
```

### 6.2.2 Citation Suggester

**Context-Aware Recommendations**
```
When user writes: "Previous studies have shown that X 
activates Y through phosphorylation."

AI suggests:
"Consider citing:
- Smith et al., 2020 (first demonstration, 1,200 citations)
- Jones et al., 2022 (most recent, adds mechanism detail)
- Your own: [PI Name] et al., 2019 (establishes expertise)

Note: Avoid Chen et al., 2018 - later shown to have 
reproducibility issues (see Wang et al., 2021 retraction)."
```

**Citation Balance Analyzer**
```
Analyzes reference list for:
- Recency: % from last 5 years
- Self-citation rate
- Breadth: coverage of key labs in field
- Competitor inclusion: citing rival approaches
- Foundational: appropriate seminal papers

Flags:
⚠ 60% of citations >5 years old (field norm: 40%)
⚠ Missing citations from [Major Lab] who works on this
✓ Good balance of your prior work (12%)
⚠ No citations to [Alternative Approach] - reviewers may ask
```

### 6.2.3 Competitor Analysis

**Input:** Research area + specific aims

**Output:**
```
COMPETITIVE LANDSCAPE

Labs working on similar problems:
1. [Lab A, Institution] - Focus on [X approach]
   - Key papers: [list]
   - Strengths: [analysis]
   - How you differ: [suggestion]

2. [Lab B, Institution] - Focus on [Y approach]
   - Recently funded: [grant number if public]
   - Your advantage: [analysis]

Active clinical trials in this space:
- NCT123456: [description]
- NCT789012: [description]

Recent funding in this area:
- NIH: 23 R01s funded in last 3 years
- Key study sections: [list]
- Funding trends: [up/down/stable]

POSITIONING RECOMMENDATION:
Emphasize [differentiator] to stand out from 
[main competitor]. Your [unique asset] is not 
being pursued by others.
```

### 6.2.4 Field Positioning

**Helps articulate unique position:**
```
Based on your aims and preliminary data, your unique 
position in the field is:

"While [competitors] approach this problem through 
[their approach], our lab uniquely combines [your 
approach 1] with [your approach 2], enabling [unique 
capability]. This is supported by our preliminary data 
showing [key finding]."

This positions you as:
- Not duplicating existing work
- Building on but extending prior studies
- Bringing unique expertise/methods
```

## 6.3 Data Sources

| Source | Data | Update Frequency |
|--------|------|------------------|
| PubMed | Papers, abstracts, citations | Weekly |
| NIH RePORTER | Funded grants | Weekly |
| Semantic Scholar | Citation network, influence | Weekly |
| ClinicalTrials.gov | Active trials | Weekly |
| bioRxiv/medRxiv | Preprints | Daily |

## 6.4 Data Model

```sql
CREATE TABLE literature_analyses (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  composition_id      UUID REFERENCES aims_compositions(id),
  
  research_area       TEXT NOT NULL,
  key_papers          JSONB, -- user-provided
  hypothesis          TEXT,
  
  -- Analysis results
  landscape           JSONB,
  gaps_identified     JSONB,
  competitor_labs     JSONB,
  citation_suggestions JSONB,
  positioning         TEXT,
  
  -- Metadata
  papers_analyzed     INTEGER,
  analysis_date       TIMESTAMP DEFAULT NOW(),
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE paper_cache (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pmid                VARCHAR(20) UNIQUE,
  doi                 VARCHAR(255),
  
  title               TEXT,
  authors             JSONB,
  abstract            TEXT,
  journal             VARCHAR(500),
  year                INTEGER,
  
  citation_count      INTEGER,
  concepts            VARCHAR(255)[], -- extracted topics
  
  embedding           vector(1536), -- for similarity search
  
  fetched_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_paper_embedding ON paper_cache 
  USING ivfflat (embedding vector_cosine_ops);
```

## 6.5 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/literature/analyze | Full landscape analysis |
| POST | /api/v1/literature/gaps | Identify gaps |
| POST | /api/v1/literature/citations/suggest | Suggest citations |
| POST | /api/v1/literature/citations/analyze | Analyze reference list |
| POST | /api/v1/literature/competitors | Competitor analysis |
| POST | /api/v1/literature/position | Generate positioning |
| GET | /api/v1/literature/papers/search | Search paper cache |

## 6.6 Acceptance Criteria

- AC-1: Gap identification surfaces relevant gaps 75% of time
- AC-2: Citation suggestions include appropriate papers 80% of time
- AC-3: Competitor analysis identifies major labs 90% of time
- AC-4: Analysis completes in under 60 seconds
- AC-5: Paper database covers major biomedical journals
- AC-6: Recency weighting appropriate for field

---

# 7. F4.5: Reviewer Simulation

## 7.1 Overview

**Purpose:** Predict how reviewers will respond to the proposal and identify weaknesses

**User Value:** Get expert review feedback before submission, prioritize revisions

**Engineering Estimate:** 4 weeks

## 7.2 Simulation Approach

### 7.2.1 Reviewer Persona Generation

```
For a given proposal, generates 3 virtual reviewers:

REVIEWER 1: Domain Expert
- Deep expertise in [specific subfield]
- Focuses on: scientific rigor, methodology, feasibility
- Typical concerns: experimental design, controls, statistics
- Tone: Detailed, technical

REVIEWER 2: Adjacent Field Expert
- Expertise in [related field]
- Focuses on: significance, broader impact, clarity
- Typical concerns: jargon, assumptions, accessibility
- Tone: "What does this mean for the field?"

REVIEWER 3: Methods/Technology Expert
- Expertise in [key methods used]
- Focuses on: technical feasibility, innovation
- Typical concerns: method validation, preliminary data quality
- Tone: Practical, implementation-focused
```

### 7.2.2 Critique Generation

For each reviewer, generates critique in NIH format:

```
REVIEWER 1 CRITIQUE

Overall Impact Score: [1-9]
"[Overall assessment paragraph]"

SIGNIFICANCE
Strengths:
• [Specific strength with rationale]
• [Specific strength with rationale]

Weaknesses:
• [Specific weakness with rationale]
• [Specific weakness with rationale]

INNOVATION
Strengths:
• [...]

Weaknesses:
• [...]

APPROACH
Strengths:
• [...]

Weaknesses:
• [Major weakness - could affect score significantly]
• [Minor weakness - addressable]

INVESTIGATOR(S)
[Assessment of PI/team qualifications]

ENVIRONMENT
[Assessment of institutional support]
```

### 7.2.3 Score Prediction

```
SCORE PREDICTION

Component Scores (1-9 scale):
┌────────────────┬───────┬─────────────────────────────┐
│ Criterion      │ Score │ Rationale                   │
├────────────────┼───────┼─────────────────────────────┤
│ Significance   │ 2     │ Strong problem, clear gap   │
│ Innovation     │ 3     │ Good but not paradigm-shift │
│ Approach       │ 4     │ Some design concerns noted  │
│ Investigator   │ 2     │ Strong track record         │
│ Environment    │ 1     │ Excellent resources         │
└────────────────┴───────┴─────────────────────────────┘

Predicted Overall Impact: 3 (Very Good)
Confidence: Medium

Fundability Assessment:
Current state: BORDERLINE (scores 3-4 typically ~30% fund rate)

To improve to LIKELY FUNDABLE (score 2):
1. Address Approach weakness #1 (experimental design)
2. Strengthen innovation claim in Section B
3. Add [specific preliminary data]
```

### 7.2.4 Weakness Prioritization

```
REVISION PRIORITY LIST

CRITICAL (must fix before submission):
1. [Aim 2 experimental design lacks appropriate controls]
   - Impact: Could drop Approach score by 1-2 points
   - Fix: Add [specific control], justify sample size
   - Effort: 2 hours

2. [Hypothesis not clearly testable]
   - Impact: Undermines entire proposal logic
   - Fix: Reframe with specific predictions
   - Effort: 1 hour

HIGH (strongly recommended):
3. [Innovation section undersells novelty]
   - Current: Generic claim of "new approach"
   - Fix: Specify what's novel vs. existing methods
   - Effort: 30 minutes

4. [Missing alternative approach for Aim 3]
   - Reviewer concern: "What if primary method fails?"
   - Fix: Add paragraph with backup plan
   - Effort: 45 minutes

MEDIUM (if time permits):
5. [Significance could cite more recent work]
6. [Timeline ambitious for personnel listed]
7. [Budget justification thin for equipment]
```

## 7.3 Training Data

### Sources
- NIH summary statements (FOIA requests)
- User-contributed reviews (opt-in, anonymized)
- Grant writing guides with example critiques
- Published "how reviewers think" literature

### Annotation
- Expert annotators label critique quality
- Score calibration against actual funded/unfunded proposals
- Continuous learning from user feedback

## 7.4 Data Model

```sql
CREATE TABLE reviewer_simulations (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  aims_composition_id UUID REFERENCES aims_compositions(id),
  strategy_id         UUID REFERENCES strategy_compositions(id),
  
  -- Full proposal text analyzed
  proposal_text       TEXT NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  -- Generated reviewers
  reviewers           JSONB,
  -- [
  --   { persona: "Domain Expert", expertise: "...", focus: "..." },
  --   { persona: "Adjacent Field", expertise: "...", focus: "..." },
  --   { persona: "Methods Expert", expertise: "...", focus: "..." }
  -- ]
  
  -- Critiques
  critiques           JSONB,
  -- [
  --   { 
  --     reviewer: 1, 
  --     overall_impact: 3,
  --     significance: { score: 2, strengths: [...], weaknesses: [...] },
  --     innovation: { ... },
  --     approach: { ... }
  --   }
  -- ]
  
  -- Predictions
  predicted_score     INTEGER,
  score_confidence    VARCHAR(20),
  fundability         VARCHAR(50),
  
  -- Prioritized issues
  critical_issues     JSONB,
  high_issues         JSONB,
  medium_issues       JSONB,
  
  -- Model version
  model_version       VARCHAR(50),
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE simulation_feedback (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulation_id       UUID NOT NULL REFERENCES reviewer_simulations(id),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  -- User feedback
  critique_helpfulness INTEGER, -- 1-5
  score_accuracy       INTEGER, -- after actual review
  actual_score         INTEGER, -- if known
  
  issue_feedback      JSONB, -- per-issue helpful/not helpful
  
  created_at          TIMESTAMP DEFAULT NOW()
);
```

## 7.5 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/reviewer-sim/simulate | Run full simulation |
| GET | /api/v1/reviewer-sim/:id | Get simulation results |
| GET | /api/v1/reviewer-sim/:id/critiques | Get detailed critiques |
| GET | /api/v1/reviewer-sim/:id/priorities | Get prioritized issues |
| POST | /api/v1/reviewer-sim/:id/feedback | Submit feedback |
| GET | /api/v1/reviewer-sim/history | User's simulation history |

## 7.6 Acceptance Criteria

- AC-1: Simulated critiques rated "realistic" by PIs 70% of time
- AC-2: Score prediction within 1 point of actual 60% of time
- AC-3: Critical issues overlap with actual reviewer concerns 75% of time
- AC-4: Simulation completes in under 2 minutes
- AC-5: Distinct reviewer personas generate different concerns
- AC-6: Actionable fix suggestions for 80% of issues

---

# 8. F4.6: Adaptive Learning

## 8.1 Overview

**Purpose:** Learn PI's writing style and preferences to provide personalized assistance

**User Value:** System gets better over time, reduces friction

**Engineering Estimate:** 4 weeks

## 8.2 Learning Dimensions

### 8.2.1 Writing Style Profile

```
Learned over time:
- Average sentence length preference
- Paragraph length preference
- Passive vs active voice tendency
- Jargon level (field-specific terminology use)
- Hedging patterns ("may," "might," "could")
- Citation style (narrative vs parenthetical)
- First person usage ("We" vs "The investigators")
```

### 8.2.2 Preference Learning

```
From user interactions:
- Which suggestions are accepted vs dismissed
- Which rules are frequently disabled
- Editing patterns after AI suggestions
- Section ordering preferences
- Level of detail in methods
```

### 8.2.3 Success Pattern Analysis

```
From user-contributed successful proposals:
- Structural patterns that correlate with funding
- Writing characteristics of high-scoring proposals
- Funder-specific preferences
- Study section tendencies
```

## 8.3 Personalization

### Suggestion Calibration

```
New user: Show all suggestions, default severity

After 10 documents:
- Reduce suggestions for patterns user consistently ignores
- Increase severity for patterns user frequently fixes
- Adapt vocabulary to match user's field

After 25 documents:
- Highly personalized suggestion set
- User-specific style guide
- Predictive text matching user voice
```

### Field-Specific Adaptation

```
Learns user's field and adapts:
- Example: Cancer biology vs Neuroscience terminology
- Appropriate method descriptions for field
- Field-standard citation practices
- Reviewer expectation norms for field
```

## 8.4 Data Model

```sql
CREATE TABLE user_style_profiles (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id) UNIQUE,
  
  -- Writing metrics (averaged over documents)
  avg_sentence_length DECIMAL(5,2),
  avg_paragraph_length DECIMAL(5,2),
  passive_voice_rate  DECIMAL(3,2),
  jargon_density      DECIMAL(3,2),
  hedging_rate        DECIMAL(3,2),
  
  -- Preferences (learned from behavior)
  preferred_rules     VARCHAR(100)[],
  disabled_rules      VARCHAR(100)[],
  suggestion_threshold DECIMAL(3,2), -- confidence threshold
  
  -- Field detection
  primary_field       VARCHAR(255),
  subfields           VARCHAR(255)[],
  
  -- Engagement metrics
  documents_analyzed  INTEGER DEFAULT 0,
  suggestions_seen    INTEGER DEFAULT 0,
  suggestions_accepted INTEGER DEFAULT 0,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE style_samples (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  sample_type         VARCHAR(50), -- 'aims', 'significance', 'methods'
  content             TEXT NOT NULL,
  
  -- Extracted style features
  features            JSONB,
  
  -- Was this from a successful proposal?
  proposal_funded     BOOLEAN,
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE success_patterns (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  funder              VARCHAR(100),
  mechanism           VARCHAR(100),
  field               VARCHAR(255),
  study_section       VARCHAR(100),
  
  -- Aggregated patterns
  structural_patterns JSONB,
  writing_patterns    JSONB,
  common_elements     JSONB,
  
  sample_size         INTEGER,
  last_updated        TIMESTAMP DEFAULT NOW()
);
```

## 8.5 Privacy Considerations

```
User controls:
- Opt-in/out of style learning
- Opt-in/out of success pattern contribution
- Data deletion on request
- Anonymization for any shared learning

Data handling:
- Style profiles never shared
- Success patterns only aggregated, anonymized
- No proposal content stored for learning without consent
```

## 8.6 Acceptance Criteria

- AC-1: Suggestion acceptance rate improves 20% over first month
- AC-2: Field detection accurate 90% of time after 3 documents
- AC-3: Style profile stable after 10 documents
- AC-4: Users report "feels personalized" 70% of time after month 1
- AC-5: Privacy controls clearly accessible
- AC-6: Profile exports on user request

---

# 9. Integration Architecture

## 9.1 How Features Work Together

```
                    ┌─────────────────────────┐
                    │  LITERATURE ASSISTANT   │
                    │  (F4.4)                 │
                    │  - Gap identification   │
                    │  - Citation suggestions │
                    └───────────┬─────────────┘
                                │ informs
                                ▼
┌─────────────────────────────────────────────────────────┐
│                  SPECIFIC AIMS COMPOSER (F4.1)          │
│  - Structure wizard                                     │
│  - Hook/hypothesis generators                           │
│  - Aim optimization                                     │
└───────────────────────────┬─────────────────────────────┘
                            │ feeds into
                            ▼
┌─────────────────────────────────────────────────────────┐
│               RESEARCH STRATEGY BUILDER (F4.2)          │
│  - Significance from aims                               │
│  - Approach expands each aim                            │
│  - Innovation links to gaps identified                  │
└───────────────────────────┬─────────────────────────────┘
                            │ enhanced by
                            ▼
          ┌─────────────────────────────────────┐
          │    WRITING ENHANCEMENT (F4.3)       │
          │    - Real-time as user writes       │
          │    - Applied across all sections    │
          └─────────────────────────────────────┘
                            │ 
                            ▼ full draft
          ┌─────────────────────────────────────┐
          │     REVIEWER SIMULATION (F4.5)      │
          │     - Critiques full proposal       │
          │     - Prioritizes revisions         │
          └─────────────────────────────────────┘
                            │
                            ▼ user revises
          ┌─────────────────────────────────────┐
          │     ADAPTIVE LEARNING (F4.6)        │
          │     - Learns from all interactions  │
          │     - Improves future suggestions   │
          └─────────────────────────────────────┘
```

## 9.2 Unified Document Context

All features share a common context:

```typescript
interface ProposalContext {
  // Identifiers
  userId: string;
  proposalId: string;
  
  // Grant info
  funder: Funder;
  mechanism: string;
  studySection?: string;
  
  // Core content
  aims: AimsComposition;
  strategy?: StrategyComposition;
  
  // User profile
  styleProfile: UserStyleProfile;
  field: string;
  
  // Analysis results
  literatureAnalysis?: LiteratureAnalysis;
  reviewerSimulation?: ReviewerSimulation;
  
  // State
  currentSection: string;
  cursorPosition: number;
}
```

## 9.3 AI Model Strategy

| Feature | Primary Model | Fallback | Specialized |
|---------|--------------|----------|-------------|
| Aims Composer | GPT-4 | Claude | - |
| Strategy Builder | GPT-4 | Claude | - |
| Writing Enhancement | GPT-3.5 (speed) | GPT-4 | Rule-based for simple |
| Literature | Embeddings + GPT-4 | - | Semantic Scholar API |
| Reviewer Sim | Fine-tuned | GPT-4 | Custom critique model |
| Adaptive | User model | - | Per-user fine-tuning |

---

# 10. Updated Pricing Strategy

## 10.1 Revised Tiers

| Tier | Price | Includes |
|------|-------|----------|
| **Discovery** | $200/mo | Grant matching, alerts, basic deadline tracking |
| **Professional** | $500/mo | Discovery + Templates, Biosketch, Boilerplate, Compliance |
| **Writer** | $800/mo | Professional + AI Writing Assistant (all F4.x features) |
| **Lab Suite** | $1,200/mo | Writer for PI + 5 lab members, shared resources |
| **Department** | $6,000/mo | Lab Suite for 15 labs, analytics, admin tools |

## 10.2 Value Justification

**Writer tier at $800/mo:**
```
Time savings: 40+ hours per major proposal
Hourly value of PI time: $100-200/hour
Value per proposal: $4,000-8,000 saved

If PI submits 2 major proposals/year:
Annual value: $8,000-16,000
Annual cost: $9,600

ROI: Still positive if success rate improves even marginally

If success rate improves 10% (e.g., 20% → 22%):
Additional funding captured: ~$40,000/year average
ROI: 4x+
```

## 10.3 Usage Limits

| Feature | Professional | Writer | Lab Suite |
|---------|-------------|--------|-----------|
| AI generations/month | 50 | Unlimited | Unlimited |
| Reviewer simulations | 0 | 10/month | 25/month |
| Literature analyses | 5 | Unlimited | Unlimited |
| Document storage | 10 GB | 50 GB | 200 GB |

---

# 11. Updated Build Plan

## 11.1 Revised Timeline

```
Phase 1 (Weeks 1-12): Foundation
  - F1.1-F1.4 (existing plan)

Phase 2 (Weeks 13-24): Basic Intelligence  
  - F2.1 Compliance Checker (4 weeks)
  - F2.2 AI Drafting - Boilerplate (2 weeks)
  - F2.3 Collaborator Portal (3 weeks)
  - F4.3 Writing Enhancement (3 weeks) ← NEW

Phase 3 (Weeks 25-40): Advanced Writing
  - F4.1 Specific Aims Composer (4 weeks) ← NEW
  - F4.2 Research Strategy Builder (5 weeks) ← NEW  
  - F4.5 Reviewer Simulation (4 weeks) ← NEW
  - F3.1 Budget Builder (3 weeks)

Phase 4 (Weeks 41-52): Optimization
  - F4.4 Literature Assistant (3 weeks) ← NEW
  - F4.6 Adaptive Learning (4 weeks) ← NEW
  - F3.2 Aims Analyzer → merged into F4.1
  - F3.3 Resubmission Assistant (3 weeks)
  - Polish and integration (2 weeks)
```

## 11.2 Team Expansion

| Role | Phase 1-2 | Phase 3-4 |
|------|-----------|-----------|
| Backend | 2 | 3 |
| Frontend | 1.5 | 2 |
| AI/ML | 1 | 2 |
| Doc Specialist | 0.5 | 0.5 |
| QA | 0.5 | 1 |

---

# 12. Success Metrics

## 12.1 Product Metrics

| Metric | Month 6 | Month 12 | Month 18 |
|--------|---------|----------|----------|
| Writing Assistant MAU | 100 | 400 | 1,000 |
| Proposals started in system | 200 | 800 | 2,500 |
| Proposals completed in system | 50 | 300 | 1,000 |
| AI suggestions accepted rate | 35% | 45% | 50% |
| Reviewer sim usage rate | - | 60% | 75% |

## 12.2 Business Metrics

| Metric | Month 6 | Month 12 | Month 18 |
|--------|---------|----------|----------|
| Writer tier subscribers | 50 | 200 | 500 |
| ARPU | $450 | $600 | $750 |
| MRR | $100K | $250K | $500K |
| Churn rate | 4% | 3% | 2% |

## 12.3 Quality Metrics

| Metric | Target |
|--------|--------|
| User satisfaction with AI suggestions | 4.0/5.0 |
| Proposal submission rate (started → submitted) | 70% |
| User-reported success rate improvement | +15% |
| Time savings (user-reported) | 50% |

---

*END OF AI WRITING ASSISTANT SPECIFICATION*
