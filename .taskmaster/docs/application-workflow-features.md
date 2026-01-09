# Application Workflow Management - Feature Plan

## Overview
Advanced features to enhance the grant application workflow management system. These features build on top of the existing Kanban board and deadline management system.

---

## Phase 1: Core Workflow Enhancements

### 1.1 Dynamic Checklists
**Priority: High | Complexity: Medium**

Auto-generated checklists based on funding opportunity requirements.

**Features:**
- Funder-specific checklist templates (NIH, NSF, DOE, DOD, foundations)
- Auto-detection of requirements from FOA text
- Progress tracking with weighted completion percentage
- Institution-specific requirements overlay
- Checklist item dependencies

**Database:**
```sql
CREATE TABLE checklist_templates (
    id UUID PRIMARY KEY,
    funder VARCHAR(100),
    mechanism VARCHAR(50),
    name VARCHAR(255),
    items JSONB,  -- [{id, title, description, required, weight, category}]
    created_at TIMESTAMP
);

CREATE TABLE application_checklists (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    template_id UUID REFERENCES checklist_templates(id),
    items JSONB,  -- [{item_id, completed, completed_at, completed_by, notes}]
    progress_percent FLOAT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**API Endpoints:**
- `GET /api/checklists/templates` - List available templates
- `GET /api/checklists/templates/{funder}` - Get funder-specific templates
- `POST /api/kanban/{card_id}/checklist` - Create checklist for application
- `PATCH /api/kanban/{card_id}/checklist/items/{item_id}` - Update item status
- `GET /api/kanban/{card_id}/checklist` - Get application checklist

---

### 1.2 Internal Review Workflow
**Priority: High | Complexity: High**

Multi-stage approval routing with role-based assignments.

**Features:**
- Configurable review stages (Draft Review → Dept Approval → College → Sponsored Programs)
- Role assignments (PI, Co-I, Grant Writer, Reviewer, Admin)
- Review comments and feedback collection
- Approval/rejection with digital signatures
- SLA tracking and escalation
- Email notifications at each stage

**Database:**
```sql
CREATE TABLE review_workflows (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    stages JSONB,  -- [{order, name, required_role, sla_hours, auto_escalate}]
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);

CREATE TABLE application_reviews (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    workflow_id UUID REFERENCES review_workflows(id),
    current_stage INT,
    status VARCHAR(50),  -- pending, in_review, approved, rejected, escalated
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE review_stage_actions (
    id UUID PRIMARY KEY,
    review_id UUID REFERENCES application_reviews(id),
    stage_order INT,
    reviewer_id UUID REFERENCES users(id),
    action VARCHAR(50),  -- approved, rejected, returned, commented
    comments TEXT,
    acted_at TIMESTAMP
);

CREATE TABLE application_team_members (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50),  -- pi, co_i, grant_writer, reviewer, admin
    permissions JSONB,  -- {can_edit, can_approve, can_submit, sections: [...]}
    added_at TIMESTAMP
);
```

**API Endpoints:**
- `GET /api/workflows` - List review workflows
- `POST /api/kanban/{card_id}/review` - Start review process
- `POST /api/kanban/{card_id}/review/action` - Submit review action
- `GET /api/kanban/{card_id}/review/history` - Get review history
- `POST /api/kanban/{card_id}/team` - Add team member
- `GET /api/kanban/{card_id}/team` - Get team members

---

### 1.3 Compliance Scanner
**Priority: High | Complexity: Medium**

Automated validation of application documents against funder requirements.

**Features:**
- Page/word limit validation
- Font and margin compliance checking
- Required section detection
- Budget arithmetic verification
- Citation format validation
- Biosketch completeness check

**Database:**
```sql
CREATE TABLE compliance_rules (
    id UUID PRIMARY KEY,
    funder VARCHAR(100),
    mechanism VARCHAR(50),
    rules JSONB,  -- [{type, name, params, severity}]
    created_at TIMESTAMP
);

CREATE TABLE compliance_scans (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    document_type VARCHAR(50),
    file_name VARCHAR(255),
    results JSONB,  -- [{rule_id, passed, message, location}]
    passed_count INT,
    failed_count INT,
    warning_count INT,
    scanned_at TIMESTAMP
);
```

**API Endpoints:**
- `POST /api/kanban/{card_id}/compliance/scan` - Run compliance scan
- `GET /api/kanban/{card_id}/compliance/results` - Get scan results
- `GET /api/compliance/rules/{funder}` - Get funder rules

---

## Phase 2: AI-Powered Features

### 2.1 Smart Drafting Assistant
**Priority: Medium | Complexity: High**

AI-powered writing assistance for grant sections.

**Features:**
- Section-specific prompts and guidance
- Auto-generate first drafts from outlines
- Improvement suggestions based on successful grants
- Tone and clarity analysis
- Budget justification generator

**API Endpoints:**
- `POST /api/ai/draft` - Generate draft for section
- `POST /api/ai/improve` - Get improvement suggestions
- `POST /api/ai/budget-justification` - Generate budget justification

---

### 2.2 Mock Review Simulation
**Priority: Medium | Complexity: High**

AI study section simulation with scored critiques.

**Features:**
- Simulated reviewer panels (3 reviewers)
- Scored critiques (1-9 scale, NIH style)
- Strength/weakness identification
- Suggested revisions
- Comparison to funded grants

**API Endpoints:**
- `POST /api/ai/mock-review` - Run mock review
- `GET /api/ai/mock-review/{id}` - Get review results
- `POST /api/ai/revision-suggestions` - Get revision suggestions

---

## Phase 3: Document Management

### 3.1 Component Library
**Priority: Medium | Complexity: Medium**

Reusable document components across applications.

**Features:**
- Facilities & equipment descriptions
- Biosketch management
- Boilerplate sections (human subjects, vertebrate animals)
- Institution descriptions
- Equipment lists

**Database:**
```sql
CREATE TABLE document_components (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    category VARCHAR(50),  -- facilities, equipment, biosketch, boilerplate
    name VARCHAR(255),
    content TEXT,
    metadata JSONB,
    version INT,
    is_current BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE component_usage (
    id UUID PRIMARY KEY,
    component_id UUID REFERENCES document_components(id),
    kanban_card_id UUID REFERENCES kanban_cards(id),
    section VARCHAR(100),
    used_at TIMESTAMP
);
```

---

### 3.2 Version Control
**Priority: Medium | Complexity: Medium**

Document versioning with diff viewing.

**Features:**
- Auto-save versions
- Named versions/snapshots
- Side-by-side diff comparison
- Restore previous versions
- Change attribution

**Database:**
```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    section VARCHAR(100),
    version_number INT,
    content TEXT,
    snapshot_name VARCHAR(255),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP
);
```

---

## Phase 4: Analytics & Intelligence

### 4.1 Success Prediction
**Priority: Low | Complexity: High**

ML-based scoring of application success likelihood.

**Features:**
- Historical data analysis
- Factor scoring (team, topic, timing, mechanism)
- Comparison to successful applications
- Improvement recommendations

---

### 4.2 Workflow Analytics
**Priority: Medium | Complexity: Medium**

Insights into application workflow efficiency.

**Features:**
- Time per stage tracking
- Bottleneck identification
- Team productivity metrics
- Deadline risk forecasting
- Success rate by workflow pattern

**Database:**
```sql
CREATE TABLE workflow_events (
    id UUID PRIMARY KEY,
    kanban_card_id UUID REFERENCES kanban_cards(id),
    event_type VARCHAR(50),  -- stage_enter, stage_exit, action, milestone
    stage VARCHAR(50),
    metadata JSONB,
    occurred_at TIMESTAMP
);

CREATE TABLE workflow_analytics (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    period_start DATE,
    period_end DATE,
    metrics JSONB,  -- {avg_time_per_stage, bottlenecks, completion_rate, ...}
    generated_at TIMESTAMP
);
```

---

## Phase 5: Integrations

### 5.1 Submission Integrations
**Priority: Low | Complexity: Very High**

Direct submission to funding portals.

**Features:**
- Grants.gov submission
- eRA Commons status sync
- Research.gov (NSF)
- Foundation portals

---

### 5.2 Collaboration Integrations
**Priority: Medium | Complexity: Medium**

Integration with collaboration tools.

**Features:**
- Slack notifications
- Microsoft Teams integration
- Email digest summaries
- Webhook support for custom integrations

---

## Implementation Order

### Sprint 1 (Week 1-2): Dynamic Checklists
- Database models and migrations
- Checklist template CRUD
- Application checklist management
- Frontend checklist component
- NIH/NSF default templates

### Sprint 2 (Week 3-4): Internal Review Workflow
- Review workflow models
- Team member management
- Review stage actions
- Notification system
- Frontend review UI

### Sprint 3 (Week 5-6): Compliance Scanner
- Compliance rules engine
- Document parsing
- Scan results storage
- Frontend compliance dashboard
- Default rule sets

### Sprint 4 (Week 7-8): Component Library
- Document components CRUD
- Version control system
- Component insertion UI
- Usage tracking

### Sprint 5 (Week 9-10): AI Features
- Drafting assistant
- Mock review simulation
- Integration with existing AI tools

### Sprint 6 (Week 11-12): Analytics
- Event tracking
- Analytics aggregation
- Dashboard visualizations
- Success prediction model

---

## Technical Notes

- All new features should be additive (new tables, new endpoints)
- Existing kanban_cards table extended via foreign key relationships
- Use feature flags for gradual rollout
- Maintain backward compatibility with existing API
- New components should follow existing UI patterns
