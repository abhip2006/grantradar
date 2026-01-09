# GrantRadar Application Suite
## Technical Specification Document v2.0

---

# Table of Contents

1. Executive Summary
2. System Architecture
3. Phase 1 Features (Detailed)
   - 3.1 Deadline Management System
   - 3.2 Funder-Specific Templates
   - 3.3 Biosketch Manager
   - 3.4 Boilerplate Library
4. Phase 2 Features (Detailed)
   - 4.1 Compliance Checker
   - 4.2 AI-Assisted Drafting
   - 4.3 Collaborator Portal
5. Phase 3 Features (Detailed)
   - 5.1 Budget Builder
   - 5.2 Specific Aims Analyzer
   - 5.3 Resubmission Assistant
6. Data Architecture
7. API Reference
8. Build Plan
9. Testing Strategy

---

# 1. Executive Summary

## 1.1 Vision
Transform GrantRadar from a grant discovery tool ($300/mo) into a comprehensive grant command center ($500-800/mo) that manages the complete proposal lifecycle.

## 1.2 Goals
- Reduce PI administrative time by 60% (80 hours → 30 hours per proposal)
- Achieve zero desk rejections for compliance-checked documents
- Increase average revenue per user from $300 to $600/month
- Build data moat through proposal flow-through

## 1.3 Scope
10 features across 3 phases over 40 weeks

---

# 2. System Architecture

## 2.1 New Services

| Service | Responsibility |
|---------|---------------|
| document-service | Template rendering, format conversion, compliance validation |
| profile-service | Biosketch management, ORCID/PubMed integration |
| collaboration-service | Collaborator invitations, document collection |
| budget-service | Budget calculations, institutional rates |
| ai-service | LLM orchestration, content generation |

## 2.2 Technology Stack

**Frontend:** React 18, TypeScript, TailwindCSS, React Query, Zustand

**Backend:** Node.js (Express) or Python (FastAPI), PostgreSQL, Redis

**Document Processing:** LibreOffice headless, Pandoc, docx-js, pdf-lib

**AI/ML:** OpenAI GPT-4, Anthropic Claude

**Infrastructure:** AWS (ECS, RDS, S3, SQS)

**External APIs:** ORCID, PubMed, NIH RePORTER, Google Calendar, Microsoft Graph

---

# 3. Phase 1 Features

## 3.1 Deadline Management System (F1.1)

### Overview
- **Purpose:** Track grant deadlines with reminders and calendar sync
- **User Value:** Eliminate missed deadlines, unified visibility
- **Engineering:** 3 weeks

### Functional Requirements

**FR-1.1.1: Deadline Creation**
- Manual creation with title, date, funder, mechanism, notes
- Auto-creation when user "tracks" grant from discovery feed
- Recurring deadline support (NIH cycles: Feb 5, Jun 5, Oct 5)
- CSV bulk import for migration

**FR-1.1.2: Deadline Attributes**
```
- title: string
- sponsor_deadline: datetime
- internal_deadline: datetime (5-10 days before sponsor)
- status: NOT_STARTED | DRAFTING | INTERNAL_REVIEW | SUBMITTED | UNDER_REVIEW | AWARDED | REJECTED
- priority: LOW | MEDIUM | HIGH | CRITICAL
- reminder_config: int[] (days before deadline)
- funder_id: FK to grants
- grant_id: FK to matched grants (optional)
```

**FR-1.1.3: Calendar Views**
- Monthly calendar view (color-coded by status)
- List view with sorting (date, priority, status)
- Kanban board by status
- Timeline/Gantt view

**FR-1.1.4: Reminder System**
- Default reminders: 30, 14, 7, 3, 1 days before
- User-configurable per deadline
- Channels: email, in-app, browser push
- Escalation if still NOT_STARTED at 14 days

**FR-1.1.5: Calendar Sync**
- Google Calendar (OAuth 2.0, calendar.events scope)
- Microsoft Outlook (Graph API, Calendars.ReadWrite)
- iCal export (.ics)
- Bidirectional sync, GrantRadar as source of truth

### Data Model

```sql
CREATE TABLE deadlines (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  lab_id              UUID REFERENCES labs(id),
  grant_id            UUID REFERENCES grants(id),
  
  title               VARCHAR(500) NOT NULL,
  description         TEXT,
  funder_name         VARCHAR(255),
  mechanism           VARCHAR(100),
  
  sponsor_deadline    TIMESTAMP WITH TIME ZONE NOT NULL,
  internal_deadline   TIMESTAMP WITH TIME ZONE,
  
  status              VARCHAR(50) DEFAULT 'NOT_STARTED',
  priority            VARCHAR(20) DEFAULT 'MEDIUM',
  
  reminder_config     JSONB DEFAULT '[30, 14, 7, 3, 1]',
  notes               TEXT,
  
  is_recurring        BOOLEAN DEFAULT FALSE,
  recurrence_rule     VARCHAR(255), -- RRULE format
  parent_deadline_id  UUID REFERENCES deadlines(id),
  
  external_calendar_id VARCHAR(255),
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deadlines_user_date ON deadlines(user_id, sponsor_deadline);
CREATE INDEX idx_deadlines_status ON deadlines(status);

CREATE TABLE deadline_status_history (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deadline_id         UUID NOT NULL REFERENCES deadlines(id),
  previous_status     VARCHAR(50),
  new_status          VARCHAR(50) NOT NULL,
  changed_by          UUID REFERENCES users(id),
  changed_at          TIMESTAMP DEFAULT NOW(),
  notes               TEXT
);

CREATE TABLE deadline_reminders (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deadline_id         UUID NOT NULL REFERENCES deadlines(id),
  remind_at           TIMESTAMP WITH TIME ZONE NOT NULL,
  channel             VARCHAR(20), -- 'email', 'push', 'in_app'
  status              VARCHAR(20) DEFAULT 'pending',
  sent_at             TIMESTAMP
);

CREATE INDEX idx_reminders_pending ON deadline_reminders(status, remind_at) 
  WHERE status = 'pending';
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/deadlines | List deadlines with filters |
| POST | /api/v1/deadlines | Create deadline |
| GET | /api/v1/deadlines/:id | Get deadline details |
| PATCH | /api/v1/deadlines/:id | Update deadline |
| DELETE | /api/v1/deadlines/:id | Delete deadline |
| POST | /api/v1/deadlines/:id/status | Change status |
| GET | /api/v1/deadlines/:id/history | Status history |
| POST | /api/v1/deadlines/import | Bulk CSV import |
| GET | /api/v1/deadlines/export.ics | iCal export |
| POST | /api/v1/deadlines/sync/google | Google Calendar sync |
| POST | /api/v1/deadlines/sync/outlook | Outlook sync |

### UI Components

**Calendar View**
- React Big Calendar or FullCalendar
- Color coding: gray (not started), blue (drafting), yellow (review), green (submitted)
- Click to open detail modal
- Drag-and-drop reschedule

**Dashboard Widget**
- Pipeline summary counts
- Upcoming 30 days list
- Overdue alerts
- Quick-add button

### Background Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| reminder_scheduler | Every 15 min | Queue due reminders |
| reminder_sender | Continuous | Send queued reminders |
| calendar_sync | Hourly | Reconcile external calendars |
| recurring_generator | Daily | Create recurring instances |
| overdue_checker | Daily | Flag overdue deadlines |

### Acceptance Criteria
- AC-1: Deadline visible in calendar within 2 seconds
- AC-2: Reminders sent within 5 minutes of scheduled time
- AC-3: Google sync within 1 minute
- AC-4: Status history with timestamps
- AC-5: Recurring deadlines generate 12 months ahead
- AC-6: CSV import handles 100+ deadlines in 30 seconds

---

## 3.2 Funder-Specific Templates (F1.2)

### Overview
- **Purpose:** Pre-configured document templates matching funder requirements
- **User Value:** Eliminate 10-20 hours formatting time per submission
- **Engineering:** 3 weeks

### Supported Templates at Launch

**NIH Templates**

| Mechanism | Page Limit | Font | Margins |
|-----------|------------|------|---------|
| R01 | 12 pages (Research Strategy) | Arial 11pt | 0.5" |
| R21 | 6 pages | Arial 11pt | 0.5" |
| R03 | 6 pages | Arial 11pt | 0.5" |
| K01/K08/K23 | 12 pages | Arial 11pt | 0.5" |
| F31/F32 | 6 pages | Arial 11pt | 0.5" |
| R35 (MIRA) | 5 pages | Arial 11pt | 0.5" |

**NSF Templates**

| Mechanism | Page Limit | Font | Margins |
|-----------|------------|------|---------|
| Standard Grant | 15 pages | 11pt min | 1" |
| CAREER | 15 pages | 11pt min | 1" |
| EAGER | 8 pages | 11pt min | 1" |
| RAPID | 5 pages | 11pt min | 1" |

**Foundation Templates (Top 20)**
- Howard Hughes Medical Institute
- Simons Foundation
- Gates Foundation
- American Cancer Society
- American Heart Association
- Burroughs Wellcome Fund
- (and 14 more)

### Functional Requirements

**FR-1.2.1: Template Selection**
- Browse by category (Federal, Foundation)
- Search by name/mechanism
- Preview showing sections
- "Use Template" creates new document

**FR-1.2.2: Template Structure**
```json
{
  "page_setup": {
    "size": "letter",
    "margins": { "top": 0.5, "right": 0.5, "bottom": 0.5, "left": 0.5 },
    "orientation": "portrait"
  },
  "typography": {
    "font_family": "Arial",
    "font_size": 11,
    "line_spacing": 1.0,
    "allowed_fonts": ["Arial", "Helvetica", "Georgia"]
  },
  "sections": [
    {
      "id": "specific_aims",
      "name": "Specific Aims",
      "page_limit": 1,
      "required": true
    },
    {
      "id": "research_strategy",
      "name": "Research Strategy",
      "page_limit": 12,
      "subsections": ["significance", "innovation", "approach"]
    }
  ]
}
```

**FR-1.2.3: Document Editor**
- Rich text editor (TipTap or Slate.js)
- Section navigation sidebar
- Live page/word count per section
- Warning at 90% limit (yellow), 100% (red)
- Auto-save every 30 seconds
- Version history

**FR-1.2.4: Export**
- .docx with exact formatting
- .pdf with embedded fonts
- .txt for portal copy-paste
- Batch export all sections

### Data Model

```sql
CREATE TABLE templates (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  name                VARCHAR(255) NOT NULL,
  description         TEXT,
  
  page_setup          JSONB NOT NULL,
  typography          JSONB NOT NULL,
  sections            JSONB NOT NULL,
  special_rules       JSONB,
  
  is_system           BOOLEAN DEFAULT TRUE,
  created_by          UUID REFERENCES users(id),
  parent_template_id  UUID REFERENCES templates(id),
  
  version             INTEGER DEFAULT 1,
  effective_date      DATE,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  template_id         UUID NOT NULL REFERENCES templates(id),
  deadline_id         UUID REFERENCES deadlines(id),
  
  title               VARCHAR(500) NOT NULL,
  content             JSONB NOT NULL,
  metadata            JSONB,
  status              VARCHAR(50) DEFAULT 'draft',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_versions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id         UUID NOT NULL REFERENCES documents(id),
  version_number      INTEGER NOT NULL,
  content             JSONB NOT NULL,
  created_at          TIMESTAMP DEFAULT NOW(),
  created_by          UUID REFERENCES users(id),
  notes               TEXT,
  
  UNIQUE(document_id, version_number)
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/templates | List templates |
| GET | /api/v1/templates/:id | Template details |
| POST | /api/v1/templates/:id/clone | Clone for customization |
| GET | /api/v1/documents | List user documents |
| POST | /api/v1/documents | Create from template |
| GET | /api/v1/documents/:id | Get with content |
| PATCH | /api/v1/documents/:id | Update content |
| POST | /api/v1/documents/:id/export | Export .docx/.pdf/.txt |
| GET | /api/v1/documents/:id/versions | Version history |
| POST | /api/v1/documents/:id/versions/:v/restore | Restore version |

### Document Processing

**Export Pipeline:**
1. Load document content from DB
2. Apply template page_setup and typography
3. Convert HTML sections to docx paragraphs
4. Insert section headers and page breaks
5. Generate .docx using docx-js
6. Convert to PDF via LibreOffice headless (if needed)
7. Validate output, return file

**Page Count Calculation:**
- Server-side: render to PDF, count pages (accurate)
- Client-side: chars / chars_per_page (fast estimate)
- Hybrid: client estimate + periodic server validation

### Acceptance Criteria
- AC-1: Exported .docx opens correctly in Word
- AC-2: Page counts match PDF export
- AC-3: 10 NIH + 4 NSF templates at launch
- AC-4: Auto-save within 30 seconds
- AC-5: 50+ versions per document
- AC-6: Export under 10 seconds for 20 pages

---

## 3.3 Biosketch Manager (F1.3)

### Overview
- **Purpose:** Centralized biosketch management with automated data integration
- **User Value:** Eliminate hours updating biosketches, always current
- **Engineering:** 3 weeks

### Data Sources

| Source | Data | Integration |
|--------|------|-------------|
| ORCID | Publications, employment | OAuth 2.0 |
| PubMed | Citation metadata, PMCID | E-utilities API |
| NIH RePORTER | Prior/current grants | REST API |
| Manual | Other contributions | User entry |

### NIH Biosketch Sections

- **Section A:** Personal Statement (4 paragraphs, 4 citations each)
- **Section B:** Positions, Appointments, Honors
- **Section C:** Contributions to Science (5 contributions, 4 citations each)
- **Section D:** Scholastic Performance (fellowships only)
- **Section E:** Research Support (current + last 3 years)

### Output Formats
- NIH Biosketch (current per NOT-OD-21-073)
- NSF Biographical Sketch (3 pages)
- Generic CV (no limits)

### Data Model

```sql
CREATE TABLE profiles (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  full_name           VARCHAR(255) NOT NULL,
  era_commons_id      VARCHAR(50),
  orcid_id            VARCHAR(50),
  email               VARCHAR(255),
  
  title               VARCHAR(255),
  department          VARCHAR(255),
  institution         VARCHAR(255),
  institution_address TEXT,
  
  personal_statement  JSONB,
  
  orcid_token         TEXT, -- encrypted
  orcid_last_sync     TIMESTAMP,
  pubmed_last_sync    TIMESTAMP,
  reporter_last_sync  TIMESTAMP,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE profile_positions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id          UUID NOT NULL REFERENCES profiles(id),
  
  position_type       VARCHAR(50), -- 'position', 'appointment', 'honor'
  title               VARCHAR(255) NOT NULL,
  organization        VARCHAR(255),
  location            VARCHAR(255),
  start_date          DATE,
  end_date            DATE,
  description         TEXT,
  
  display_order       INTEGER,
  is_included         BOOLEAN DEFAULT TRUE,
  source              VARCHAR(50), -- 'manual', 'orcid'
  external_id         VARCHAR(255),
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE profile_publications (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id          UUID NOT NULL REFERENCES profiles(id),
  
  pmid                VARCHAR(20),
  pmcid               VARCHAR(20),
  doi                 VARCHAR(255),
  orcid_put_code      VARCHAR(50),
  
  title               TEXT NOT NULL,
  authors             TEXT,
  author_list         JSONB,
  journal             VARCHAR(500),
  year                INTEGER,
  volume              VARCHAR(50),
  issue               VARCHAR(50),
  pages               VARCHAR(50),
  
  publication_type    VARCHAR(50),
  citation_count      INTEGER,
  
  is_included         BOOLEAN DEFAULT TRUE,
  contribution_id     UUID REFERENCES profile_contributions(id),
  source              VARCHAR(50),
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(profile_id, pmid) WHERE pmid IS NOT NULL,
  UNIQUE(profile_id, doi) WHERE doi IS NOT NULL
);

CREATE TABLE profile_contributions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id          UUID NOT NULL REFERENCES profiles(id),
  
  title               VARCHAR(500) NOT NULL,
  description         TEXT NOT NULL,
  display_order       INTEGER,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE profile_grants (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id          UUID NOT NULL REFERENCES profiles(id),
  
  title               TEXT NOT NULL,
  grant_number        VARCHAR(100),
  funder              VARCHAR(255),
  role                VARCHAR(100), -- 'PI', 'Co-PI', 'Co-I'
  
  start_date          DATE,
  end_date            DATE,
  total_award         DECIMAL(12,2),
  annual_direct       DECIMAL(12,2),
  
  status              VARCHAR(50), -- 'active', 'completed', 'pending'
  is_included         BOOLEAN DEFAULT TRUE,
  
  source              VARCHAR(50),
  reporter_project_id VARCHAR(50),
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE lab_members (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lab_id              UUID NOT NULL REFERENCES labs(id),
  profile_id          UUID NOT NULL REFERENCES profiles(id),
  role                VARCHAR(50),
  joined_at           TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(lab_id, profile_id)
);
```

### External API Integration

**ORCID API**
```
OAuth 2.0: /authenticate scope
Endpoints:
  GET /v3.0/{orcid}/works
  GET /v3.0/{orcid}/employments
Rate limit: 24 req/sec
Store refresh token for background sync
```

**PubMed E-utilities**
```
esearch.fcgi: Search by author
efetch.fcgi: Get full citation
Rate limit: 3 req/sec (10 with API key)
Query: author[au] AND affiliation[ad]
```

**NIH RePORTER**
```
POST /v2/projects/search
Search by PI name
Rate limit: Conservative backoff
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/profiles/me | Get profile |
| PATCH | /api/v1/profiles/me | Update profile |
| POST | /api/v1/profiles/me/connect/orcid | ORCID OAuth |
| POST | /api/v1/profiles/me/sync | Trigger sync |
| GET | /api/v1/profiles/me/publications | List publications |
| POST | /api/v1/profiles/me/publications | Add manual |
| PATCH | /api/v1/profiles/me/publications/:id | Update |
| GET | /api/v1/profiles/me/grants | List grants |
| POST | /api/v1/profiles/me/biosketch/export | Export |
| GET | /api/v1/labs/:id/members | Lab members |
| POST | /api/v1/labs/:id/members/invite | Invite |

### Background Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| orcid_sync | Weekly | Sync publications |
| pubmed_sync | Weekly | Search new pubs |
| reporter_sync | Weekly | Grant status |
| stale_alert | Weekly | Flag 180+ day stale |
| citation_update | Monthly | Update counts |

### Acceptance Criteria
- AC-1: ORCID OAuth imports in 30 seconds
- AC-2: PubMed finds 95% of faculty
- AC-3: Biosketch matches NIH format
- AC-4: Auto-sync within 7 days of PubMed indexing
- AC-5: Lab dashboard shows all members
- AC-6: SciENcv export validates

---

## 3.4 Boilerplate Library (F1.4)

### Overview
- **Purpose:** Reusable document components with variable substitution
- **User Value:** Eliminate rewriting standard sections
- **Engineering:** 2 weeks

### Section Categories

- Facilities and Equipment
- Data Management Plans
- Resource Sharing Plans
- Authentication of Key Biological Resources
- Budget Justifications
- Vertebrate Animals
- Human Subjects
- Letters of Support
- Consortium Agreements

### Variable Substitution

**Standard Variables:**
```
{{PI_NAME}}, {{PI_TITLE}}, {{PI_EMAIL}}
{{INSTITUTION}}, {{DEPARTMENT}}, {{INSTITUTION_ADDRESS}}
{{PROJECT_TITLE}}, {{GRANT_NUMBER}}, {{FUNDER}}
{{START_DATE}}, {{END_DATE}}, {{TOTAL_BUDGET}}
{{COLLABORATOR_NAME}}, {{COLLABORATOR_INSTITUTION}}
```

**Advanced:**
- Custom user-defined variables
- Conditionals: `{{#if VARIABLE}}...{{/if}}`
- Date formatting: `{{START_DATE|format:MMMM YYYY}}`

### Data Model

```sql
CREATE TABLE boilerplates (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES users(id),
  lab_id              UUID REFERENCES labs(id),
  org_id              UUID REFERENCES organizations(id),
  
  title               VARCHAR(500) NOT NULL,
  category            VARCHAR(100) NOT NULL,
  tags                VARCHAR(255)[],
  
  content             TEXT NOT NULL, -- HTML with {{variables}}
  variables_used      VARCHAR(100)[],
  
  is_system           BOOLEAN DEFAULT FALSE,
  is_shared           BOOLEAN DEFAULT FALSE,
  share_level         VARCHAR(20), -- 'private', 'lab', 'department', 'institution'
  
  current_version     INTEGER DEFAULT 1,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_boilerplates_search ON boilerplates 
  USING gin(to_tsvector('english', content));

CREATE TABLE boilerplate_versions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  boilerplate_id      UUID NOT NULL REFERENCES boilerplates(id),
  version_number      INTEGER NOT NULL,
  version_name        VARCHAR(255),
  content             TEXT NOT NULL,
  created_at          TIMESTAMP DEFAULT NOW(),
  created_by          UUID REFERENCES users(id),
  
  UNIQUE(boilerplate_id, version_number)
);

CREATE TABLE custom_variables (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  variable_name       VARCHAR(100) NOT NULL,
  variable_value      TEXT NOT NULL,
  description         TEXT,
  
  UNIQUE(user_id, variable_name)
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/boilerplates | List with filters |
| POST | /api/v1/boilerplates | Create |
| GET | /api/v1/boilerplates/:id | Get content |
| PATCH | /api/v1/boilerplates/:id | Update |
| DELETE | /api/v1/boilerplates/:id | Delete |
| POST | /api/v1/boilerplates/:id/clone | Clone |
| GET | /api/v1/boilerplates/:id/versions | Versions |
| POST | /api/v1/boilerplates/:id/render | Render with variables |
| GET | /api/v1/variables | List custom variables |
| POST | /api/v1/variables | Create variable |

### Acceptance Criteria
- AC-1: 50+ system templates at launch
- AC-2: Variable substitution under 500ms
- AC-3: Full-text search under 1 second
- AC-4: 100+ versions maintained
- AC-5: Shared visible within 30 seconds
- AC-6: .docx import with 95% fidelity

---

# 4. Phase 2 Features

## 4.1 Compliance Checker (F2.1)

### Overview
- **Purpose:** Automated validation against funder requirements
- **User Value:** Zero desk rejections for formatting
- **Engineering:** 4 weeks

### Validation Rules

**Core Categories:**
- Page limits (total, per-section)
- Typography (font family, size, spacing)
- Margins (all four, within tolerance)
- Section structure (required present, order)
- File format (type, PDF/A if required)
- Figures/tables (resolution, placement)
- References (format, page limit inclusion)

**NIH-Specific:**
- Font: Arial, Helvetica, Palatino, Georgia (11pt min)
- Margins: 0.5" minimum
- Specific Aims: 1 page
- Research Strategy: 12 pages (R01)
- Biosketch: 5 pages
- References: excluded from limit
- Figures: 300 DPI minimum

**NSF-Specific:**
- Font: 11pt minimum
- Margins: 1" all sides
- Project Description: 15 pages
- References: separate, no limit
- Bio Sketch: 3 pages
- Data Management: 2 pages

### Data Model

```sql
CREATE TABLE compliance_rules (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  foa_number          VARCHAR(100),
  
  rule_category       VARCHAR(50) NOT NULL,
  rule_type           VARCHAR(50) NOT NULL,
  rule_config         JSONB NOT NULL,
  
  severity            VARCHAR(20) DEFAULT 'error',
  message_template    TEXT NOT NULL,
  fix_guidance        TEXT,
  is_auto_fixable     BOOLEAN DEFAULT FALSE,
  
  effective_date      DATE,
  deprecated_date     DATE,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE compliance_checks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  document_id         UUID REFERENCES documents(id),
  
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  uploaded_file_name  VARCHAR(500),
  uploaded_file_path  VARCHAR(1000),
  
  status              VARCHAR(50),
  overall_result      VARCHAR(20),
  
  error_count         INTEGER DEFAULT 0,
  warning_count       INTEGER DEFAULT 0,
  info_count          INTEGER DEFAULT 0,
  
  processing_time_ms  INTEGER,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  completed_at        TIMESTAMP
);

CREATE TABLE compliance_issues (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  check_id            UUID NOT NULL REFERENCES compliance_checks(id),
  rule_id             UUID NOT NULL REFERENCES compliance_rules(id),
  
  severity            VARCHAR(20) NOT NULL,
  message             TEXT NOT NULL,
  location            JSONB,
  
  found_value         VARCHAR(255),
  required_value      VARCHAR(255),
  
  is_auto_fixed       BOOLEAN DEFAULT FALSE,
  fixed_at            TIMESTAMP
);
```

### Document Parsing

**PDF Processing:**
- pdf-lib for reading
- pdf.js for rendering
- Tesseract OCR fallback
- Font analysis from /Resources/Font
- Image resolution extraction

**DOCX Processing:**
- mammoth.js for content
- JSZip for raw XML
- Parse document.xml, styles.xml
- Convert to PDF for page count

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/compliance/check | Upload and check |
| GET | /api/v1/compliance/checks/:id | Status and results |
| GET | /api/v1/compliance/checks/:id/issues | All issues |
| POST | /api/v1/compliance/checks/:id/autofix | Apply fixes |
| GET | /api/v1/compliance/checks/:id/report | PDF report |
| GET | /api/v1/compliance/rules | Rules for funder |
| GET | /api/v1/compliance/history | User history |

### Acceptance Criteria
- AC-1: 95% violation detection accuracy
- AC-2: 30 seconds for 50-page document
- AC-3: Zero false negatives on critical rules
- AC-4: Auto-fix produces valid documents
- AC-5: All NIH/NSF mechanisms covered
- AC-6: 12-month history retention

---

## 4.2 AI-Assisted Drafting (F2.2)

### Overview
- **Purpose:** LLM-generated first drafts for administrative sections
- **User Value:** 10-15 hours → 1-2 hours on boilerplate
- **Engineering:** 3 weeks

### Supported Sections

**Budget Justification**
- Input: structured budget data, timeline, activities
- Output: personnel, equipment, supplies, travel justifications

**Facilities & Equipment**
- Input: institution, department, cores, equipment
- Output: research environment narrative

**Data Management Plan**
- Input: data types, volume, sharing requirements
- Output: storage, preservation, sharing plan

**NOT Supported:**
- Specific Aims (core scientific)
- Research Strategy (intellectual content)
- Significance/Innovation (domain expertise)

### Data Model

```sql
CREATE TABLE ai_drafts (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  
  section_type        VARCHAR(100) NOT NULL,
  input_data          JSONB NOT NULL,
  
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  generated_content   TEXT,
  edited_content      TEXT,
  
  model_used          VARCHAR(100),
  prompt_version      VARCHAR(50),
  generation_time_ms  INTEGER,
  token_count         INTEGER,
  
  status              VARCHAR(50),
  
  saved_to_boilerplate_id  UUID REFERENCES boilerplates(id),
  inserted_to_document_id  UUID REFERENCES documents(id),
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ai_prompt_templates (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  section_type        VARCHAR(100) NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  
  system_prompt       TEXT NOT NULL,
  user_prompt_template TEXT NOT NULL,
  few_shot_examples   JSONB,
  
  model_preference    VARCHAR(100),
  max_tokens          INTEGER,
  temperature         DECIMAL(3,2),
  
  version             INTEGER DEFAULT 1,
  is_active           BOOLEAN DEFAULT TRUE,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/ai/sections | List section types |
| GET | /api/v1/ai/sections/:type/schema | Input schema |
| POST | /api/v1/ai/generate | Generate (streaming) |
| POST | /api/v1/ai/drafts/:id/regenerate | Regenerate |
| POST | /api/v1/ai/drafts/:id/refine | Refine with instructions |
| PATCH | /api/v1/ai/drafts/:id | Save edits |
| POST | /api/v1/ai/drafts/:id/save-boilerplate | Save to library |
| GET | /api/v1/ai/drafts | Draft history |

### Acceptance Criteria
- AC-1: Budget justifications pass review 80%
- AC-2: Generation under 60 seconds
- AC-3: Streaming starts within 3 seconds
- AC-4: Matches funder style
- AC-5: No hallucinated facts
- AC-6: Natural language refinement works

---

## 4.3 Collaborator Portal (F2.3)

### Overview
- **Purpose:** Collect documents from multi-PI proposal collaborators
- **User Value:** 8-12 hours → 2-3 hours coordination
- **Engineering:** 3 weeks

### Document Request Types
- Biosketch (NIH/NSF format)
- Letter of Support
- Current & Pending Support
- Facilities & Equipment
- Budget & Budget Justification
- Collaboration Statement
- Custom

### Workflow

1. PI adds collaborator (email, name, institution, role)
2. PI creates document requests with due dates
3. System sends invitation email with magic link
4. Collaborator uploads (no account needed)
5. PI reviews and approves/requests revision
6. Automatic reminders at intervals

### Data Model

```sql
CREATE TABLE proposals (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  deadline_id         UUID REFERENCES deadlines(id),
  
  title               VARCHAR(500) NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  submission_date     DATE,
  
  status              VARCHAR(50) DEFAULT 'draft',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE collaborators (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id         UUID NOT NULL REFERENCES proposals(id),
  
  email               VARCHAR(255) NOT NULL,
  name                VARCHAR(255),
  institution         VARCHAR(255),
  role                VARCHAR(100),
  
  user_id             UUID REFERENCES users(id),
  
  access_token        VARCHAR(255) NOT NULL,
  token_expires_at    TIMESTAMP,
  
  invited_at          TIMESTAMP,
  last_accessed_at    TIMESTAMP,
  
  UNIQUE(proposal_id, email)
);

CREATE TABLE document_requests (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id         UUID NOT NULL REFERENCES proposals(id),
  collaborator_id     UUID NOT NULL REFERENCES collaborators(id),
  
  document_type       VARCHAR(100) NOT NULL,
  title               VARCHAR(255) NOT NULL,
  instructions        TEXT,
  template_file_path  VARCHAR(1000),
  
  due_date            DATE,
  is_required         BOOLEAN DEFAULT TRUE,
  
  status              VARCHAR(50) DEFAULT 'not_sent',
  
  reminder_config     JSONB DEFAULT '{"enabled": true}',
  last_reminder_sent  TIMESTAMP,
  reminder_count      INTEGER DEFAULT 0,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE uploaded_documents (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id          UUID NOT NULL REFERENCES document_requests(id),
  
  file_name           VARCHAR(500) NOT NULL,
  file_path           VARCHAR(1000) NOT NULL,
  file_size           INTEGER,
  mime_type           VARCHAR(100),
  
  version             INTEGER DEFAULT 1,
  is_current          BOOLEAN DEFAULT TRUE,
  
  uploaded_at         TIMESTAMP DEFAULT NOW(),
  uploaded_by_email   VARCHAR(255),
  
  review_status       VARCHAR(50) DEFAULT 'pending',
  review_notes        TEXT,
  reviewed_at         TIMESTAMP,
  reviewed_by         UUID REFERENCES users(id)
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/proposals | Create proposal |
| GET | /api/v1/proposals/:id/collaborators | List collaborators |
| POST | /api/v1/proposals/:id/collaborators | Add collaborator |
| POST | /api/v1/collaborators/:id/requests | Create request |
| POST | /api/v1/collaborators/:id/invite | Send invitation |
| POST | /api/v1/requests/:id/remind | Manual reminder |
| GET | /api/v1/portal/:token | Collaborator portal |
| POST | /api/v1/portal/:token/upload | Upload (no auth) |
| POST | /api/v1/documents/:id/review | Approve/revise |
| GET | /api/v1/proposals/:id/documents/download | Batch ZIP |

### Acceptance Criteria
- AC-1: Upload without account
- AC-2: Email within 1 minute
- AC-3: Automatic reminders work
- AC-4: PI notified within 5 minutes of upload
- AC-5: Valid ZIP download
- AC-6: Invalid file types rejected

---

# 5. Phase 3 Features

## 5.1 Budget Builder (F3.1)

### Overview
- **Purpose:** Intelligent budget construction with institutional rates
- **User Value:** 15-25 hours → 3-5 hours
- **Engineering:** 5 weeks

### Budget Categories

**Personnel:**
- Roles: PI, Co-I, Postdoc, Grad Student, Staff
- Effort: % or person-months
- Salary: annual or institutional base
- NIH cap: $221,900 (FY2024)
- Fringe: institution-specific rates
- Multi-year: annual raises (3% default)

**Non-Personnel:**
- Equipment (>$5K, >1 year life)
- Supplies (lab, office, computing)
- Travel (domestic, international)
- Participant costs
- Other (publication, consultants)
- Subcontracts/consortium

**Indirect Costs:**
- MTDC base calculation
- Exclusions: equipment, participants, subawards >$25K, tuition
- Rate: institution negotiated rate

### Data Model

```sql
CREATE TABLE budgets (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  proposal_id         UUID REFERENCES proposals(id),
  document_id         UUID REFERENCES documents(id),
  
  title               VARCHAR(500) NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  budget_type         VARCHAR(50),
  
  start_date          DATE,
  end_date            DATE,
  num_years           INTEGER,
  
  institution_id      UUID REFERENCES institutions(id),
  fa_rate             DECIMAL(5,2),
  
  inflation_rate      DECIMAL(4,2) DEFAULT 3.00,
  
  status              VARCHAR(50) DEFAULT 'draft',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE budget_personnel (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  budget_id           UUID NOT NULL REFERENCES budgets(id),
  
  name                VARCHAR(255),
  role                VARCHAR(100) NOT NULL,
  
  base_salary         DECIMAL(12,2),
  salary_cap_applied  BOOLEAN DEFAULT FALSE,
  
  fringe_rate         DECIMAL(5,2),
  
  year_details        JSONB NOT NULL,
  justification       TEXT,
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE budget_items (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  budget_id           UUID NOT NULL REFERENCES budgets(id),
  
  category            VARCHAR(50) NOT NULL,
  subcategory         VARCHAR(100),
  description         TEXT NOT NULL,
  
  year_costs          JSONB NOT NULL,
  
  is_fa_excluded      BOOLEAN DEFAULT FALSE,
  justification       TEXT,
  
  subaward_institution VARCHAR(255),
  subaward_pi         VARCHAR(255),
  subaward_direct     DECIMAL(12,2),
  
  created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE institutions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                VARCHAR(255) NOT NULL,
  short_name          VARCHAR(50),
  
  fa_rate_on_campus   DECIMAL(5,2),
  fa_rate_off_campus  DECIMAL(5,2),
  fa_rate_effective   DATE,
  
  fringe_rates        JSONB,
  
  address             TEXT,
  duns_number         VARCHAR(20),
  cage_code           VARCHAR(10),
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);
```

### Calculation Logic

```javascript
function calculatePersonnelCost(person, year, institution) {
  let salary = person.base_salary * Math.pow(1 + inflation_rate, year - 1);
  
  if (salary > NIH_SALARY_CAP && funder === 'NIH') {
    salary = NIH_SALARY_CAP;
    person.salary_cap_applied = true;
  }
  
  const effort_cost = salary * (person.effort_percent / 100);
  const fringe = effort_cost * (person.fringe_rate / 100);
  
  return { salary: effort_cost, fringe, total: effort_cost + fringe };
}

function calculateIndirectCosts(budget, year) {
  let mtdc_base = sumAllCategories(budget, year);
  
  mtdc_base -= budget.equipment[year];
  mtdc_base -= budget.participant_costs[year];
  mtdc_base -= budget.tuition_remission[year];
  
  for (const sub of budget.subawards) {
    const sub_total = sub.year_costs[year];
    const sub_in_mtdc = Math.min(sub_total, 25000);
    mtdc_base -= (sub_total - sub_in_mtdc);
  }
  
  const fa_rate = budget.fa_rate || institution.fa_rate_on_campus;
  return mtdc_base * (fa_rate / 100);
}
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/budgets | Create budget |
| GET | /api/v1/budgets/:id | Get with calculations |
| PATCH | /api/v1/budgets/:id | Update settings |
| POST | /api/v1/budgets/:id/personnel | Add personnel |
| POST | /api/v1/budgets/:id/items | Add item |
| GET | /api/v1/budgets/:id/summary | Calculated totals |
| POST | /api/v1/budgets/:id/export | Export forms |
| GET | /api/v1/institutions | Search institutions |
| GET | /api/v1/institutions/:id/rates | Get rates |

### Acceptance Criteria
- AC-1: Calculations within $1 of manual
- AC-2: NIH salary cap applied correctly
- AC-3: Top 200 institutions rates available
- AC-4: NIH forms pass Grants.gov validation
- AC-5: Multi-year inflation correct
- AC-6: MTDC exclusions applied correctly

---

## 5.2 Specific Aims Analyzer (F3.2)

### Overview
- **Purpose:** AI feedback on specific aims structure and quality
- **User Value:** Expert-level feedback without consultants
- **Engineering:** 5 weeks

### Analysis Dimensions

**Structural Completeness:**
- Opening hook
- Knowledge gap
- Long-term goal
- Central hypothesis
- Rationale/preliminary data
- Aims (2-3)
- Expected outcomes
- Impact statement

**Aim Quality (per aim):**
- Specificity
- Independence
- Feasibility
- Innovation
- Hypothesis alignment

**Writing Quality:**
- Clarity
- Concision
- Active voice
- Jargon appropriateness
- Logical flow

**Funder Alignment:**
- Mission fit
- Mechanism scope
- Review criteria coverage

### Data Model

```sql
CREATE TABLE aims_analyses (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  document_id         UUID REFERENCES documents(id),
  
  input_text          TEXT NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  overall_score       INTEGER, -- 1-100
  structural_score    INTEGER,
  aim_quality_score   INTEGER,
  writing_score       INTEGER,
  alignment_score     INTEGER,
  
  analysis_result     JSONB NOT NULL,
  
  model_version       VARCHAR(50),
  processing_time_ms  INTEGER,
  
  created_at          TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/aims/analyze | Submit for analysis |
| GET | /api/v1/aims/analyses/:id | Get results |
| GET | /api/v1/aims/analyses/:id/report | PDF report |
| GET | /api/v1/aims/history | Analysis history |
| POST | /api/v1/aims/contribute | Contribute (opt-in) |

### Acceptance Criteria
- AC-1: Analysis under 60 seconds
- AC-2: Section detection 90% accuracy
- AC-3: 80% user satisfaction rating
- AC-4: Score correlates with expert (r > 0.7)
- AC-5: Handles various formatting

---

## 5.3 Resubmission Assistant (F3.3)

### Overview
- **Purpose:** Systematically address reviewer critiques
- **User Value:** Ensure all critiques addressed, organized response
- **Engineering:** 4 weeks

### Workflow

1. Upload summary statement
2. AI extracts individual critiques
3. PI assigns response strategy per critique
4. Track changes linked to critiques
5. Generate response document

### Data Model

```sql
CREATE TABLE resubmissions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  original_deadline_id UUID REFERENCES deadlines(id),
  
  title               VARCHAR(500) NOT NULL,
  funder_id           UUID REFERENCES funders(id),
  mechanism           VARCHAR(100),
  
  original_proposal_id UUID REFERENCES documents(id),
  revised_proposal_id  UUID REFERENCES documents(id),
  
  summary_statement   TEXT,
  summary_file_path   VARCHAR(1000),
  
  overall_impact_score VARCHAR(20),
  
  status              VARCHAR(50) DEFAULT 'planning',
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE review_critiques (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resubmission_id     UUID NOT NULL REFERENCES resubmissions(id),
  
  reviewer_source     VARCHAR(100),
  category            VARCHAR(100),
  severity            VARCHAR(50),
  
  critique_text       TEXT NOT NULL,
  
  response_strategy   VARCHAR(50),
  response_text       TEXT,
  section_reference   VARCHAR(255),
  
  priority            INTEGER,
  status              VARCHAR(50) DEFAULT 'not_addressed',
  
  notes               TEXT,
  display_order       INTEGER,
  
  created_at          TIMESTAMP DEFAULT NOW(),
  updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE critique_changes (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  critique_id         UUID NOT NULL REFERENCES review_critiques(id),
  
  change_description  TEXT NOT NULL,
  original_text       TEXT,
  revised_text        TEXT,
  
  location            VARCHAR(255),
  
  created_at          TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/resubmissions | Create project |
| POST | /api/v1/resubmissions/:id/parse | Parse statement |
| GET | /api/v1/resubmissions/:id/critiques | List critiques |
| PATCH | /api/v1/critiques/:id | Update response |
| POST | /api/v1/resubmissions/:id/diff | Generate diff |
| POST | /api/v1/resubmissions/:id/response-doc | Generate response |
| GET | /api/v1/resubmissions/:id/progress | Completion status |

### Acceptance Criteria
- AC-1: 90% critique extraction accuracy
- AC-2: 85% severity classification accuracy
- AC-3: NIH format response document
- AC-4: Diff highlights meaningful changes
- AC-5: Progress tracking accurate

---

# 6. Data Architecture

## 6.1 Entity Relationships

```
Users ─┬─ Profiles ─┬─ Publications
       │            ├─ Grants
       │            └─ Positions
       │
       ├─ Deadlines
       │
       ├─ Documents ─── Templates
       │
       ├─ Budgets ─┬─ Personnel
       │           └─ Items
       │
       └─ Proposals ─── Collaborators ─── Document Requests ─── Uploaded Documents
```

## 6.2 Storage

| Type | Technology | Purpose |
|------|------------|---------|
| Relational | PostgreSQL | All entity data |
| Cache | Redis | Sessions, queues, rate limits |
| Object | S3 | Documents, uploads, exports |
| Search | Elasticsearch | Full-text (optional) |

## 6.3 Retention

- Active data: indefinite
- Compliance history: 12 months
- Document versions: 50 per document
- AI drafts: 90 days
- Deleted users: purged after 30 days

## 6.4 Security

- Encryption at rest: AES-256
- Encryption in transit: TLS 1.3
- PII: user-specific keys
- Access: row-level security
- Audit: all sensitive access logged

---

# 7. API Reference

## 7.1 Design Principles

- RESTful resource-oriented
- Versioning: /api/v1/
- Auth: JWT tokens
- Rate limiting: 1000 req/hour
- Pagination: cursor-based
- Errors: RFC 7807

## 7.2 Response Formats

**Success:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-15T10:30:00Z"
  }
}
```

**Error:**
```json
{
  "error": {
    "type": "validation_error",
    "title": "Invalid request",
    "detail": "Field 'due_date' must be future",
    "errors": [{ "field": "due_date", "message": "..." }]
  }
}
```

**Paginated:**
```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTIzfQ==",
    "has_more": true,
    "total_count": 150
  }
}
```

## 7.3 Webhooks

| Event | Trigger |
|-------|---------|
| deadline.approaching | 7 days before |
| deadline.status_changed | Status change |
| document.uploaded | Collaborator upload |
| compliance.completed | Check finished |
| budget.exported | Forms generated |

---

# 8. Build Plan

## 8.1 Team

| Role | Count | Responsibilities |
|------|-------|------------------|
| Backend | 2 | APIs, integrations, jobs |
| Frontend | 1-2 | UI, editor, dashboards |
| AI/ML | 1 | LLM, prompts, models |
| Doc Specialist | 0.5 | Templates, rules |
| QA | 0.5 | Testing, validation |

## 8.2 Timeline

**Phase 1 (Weeks 1-12):**
- Week 1-4: Deadline Management
- Week 5-8: Templates & Editor
- Week 9-11: Biosketch Manager
- Week 12: Boilerplate Library

**Phase 2 (Weeks 13-24):**
- Week 13-18: Compliance Checker
- Week 19-21: AI Drafting
- Week 22-24: Collaborator Portal

**Phase 3 (Weeks 25-40):**
- Week 25-31: Budget Builder
- Week 32-36: Aims Analyzer
- Week 37-40: Resubmission Assistant

## 8.3 Milestones

| Milestone | Week | Criteria |
|-----------|------|----------|
| Phase 1 Beta | 10 | 10 test users |
| Phase 1 Launch | 12 | 50 users |
| Phase 2 Beta | 22 | 20 test users |
| Phase 2 Launch | 24 | 150 users |
| Phase 3 Beta | 38 | 30 test users |
| Phase 3 Launch | 40 | 300 users |

---

# 9. Testing Strategy

## 9.1 Levels

| Level | Coverage | Framework |
|-------|----------|-----------|
| Unit | 80% business logic | Jest/pytest |
| Integration | API + DB | Supertest |
| E2E | Critical flows | Playwright |
| Document | Export validation | Custom |

## 9.2 Performance Targets

| Operation | Target |
|-----------|--------|
| Page load | < 2s |
| Document export | < 10s |
| Compliance check | < 30s |
| AI generation | < 60s |
| Biosketch gen | < 15s |
| Calendar sync | < 5s |

---

*END OF TECHNICAL SPECIFICATION*
