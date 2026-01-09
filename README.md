# GrantRadar

AI-powered grant discovery platform for researchers and nonprofits. GrantRadar aggregates grants from NIH, NSF, and Grants.gov, then uses intelligent matching to surface opportunities that fit your organization's mission and eligibility.

## Features

- **Smart Grant Matching** - AI-powered matching scores grants against your organization profile
- **Multi-Source Aggregation** - Pulls from NIH Reporter, NSF Awards, and Grants.gov
- **Real-Time Alerts** - Email and SMS notifications for new high-scoring matches
- **Dashboard Analytics** - Track matches, saved grants, and upcoming deadlines
- **Daily Updates** - Grants indexed and updated every 24 hours

## Tech Stack

### Backend
- **FastAPI** - Async Python web framework
- **PostgreSQL** - Primary database with full-text search
- **Redis** - Caching and Celery message broker
- **Celery** - Background task processing
- **SQLAlchemy** - Async ORM with Alembic migrations

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first styling
- **React Query** - Server state management

### Infrastructure
- **Docker Compose** - Local development environment
- **WebSockets** - Real-time notifications via Socket.IO

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/abhip2006/grantradar.git
   cd grantradar
   ```

2. **Start infrastructure services**
   ```bash
   docker-compose up -d
   ```

3. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Seed the database** (optional but recommended)
   ```bash
   python -m backend.scripts.seed_all
   ```
   This populates the database with reference data including:
   - Grant mechanisms (NIH R01, R21, NSF CAREER, etc.)
   - Budget templates and guidelines
   - Compliance requirements and rules
   - Checklist templates
   - Document templates

   See [Database Seeding](#database-seeding) section below for more details.

7. **Start the backend**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

8. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

9. **Start the frontend**
   ```bash
   npm run dev
   ```

10. **Open the app**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
grantradar/
├── agents/                 # Grant discovery and matching agents
│   ├── discovery/          # NIH, NSF, Grants.gov scrapers
│   ├── matching/           # AI matching engine
│   ├── curation/           # Grant validation
│   ├── delivery/           # Alert notifications
│   └── orchestrator/       # Agent coordination
├── backend/                # FastAPI application
│   ├── api/                # API route handlers
│   ├── core/               # Configuration
│   ├── schemas/            # Pydantic models
│   └── tasks/              # Celery background tasks
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── contexts/       # React contexts
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript types
├── alembic/                # Database migrations
├── tests/                  # Test suite
└── docker-compose.yml      # Development services
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | Create new account |
| `POST /api/auth/login` | Login and get JWT |
| `GET /api/grants` | List grants with filters |
| `GET /api/grants/search` | Search grants by keyword |
| `GET /api/matches` | Get user's grant matches |
| `POST /api/matches/{id}/action` | Save/dismiss a match |
| `GET /api/stats` | Dashboard statistics |
| `GET /api/profile` | Get user profile |
| `POST /api/profile/onboarding` | Complete onboarding |
| `POST /api/contact` | Submit contact form |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `JWT_SECRET_KEY` | Secret for JWT signing | (required) |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | (optional) |
| `SENDGRID_API_KEY` | SendGrid for email alerts | (optional) |
| `TWILIO_*` | Twilio for SMS alerts | (optional) |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=agents

# Run specific test file
pytest tests/test_api.py -v
```

## Database Seeding

The seed script populates the database with reference data required for various grant management features.

### Running the Seed Script

```bash
# Basic seeding (idempotent - safe to run multiple times)
python -m backend.scripts.seed_all

# Preview what would be seeded without making changes
python -m backend.scripts.seed_all --dry-run

# Force re-seed (updates existing data where supported)
python -m backend.scripts.seed_all --force

# Skip database/migration checks (useful for CI)
python -m backend.scripts.seed_all --skip-check

# Verbose output
python -m backend.scripts.seed_all --verbose
```

### What Gets Seeded

| Data Type | Table | Records | Description |
|-----------|-------|---------|-------------|
| Grant Mechanisms | `grant_mechanisms` | 13 | NIH (R01, R21, K01, etc.) and NSF (CAREER, Standard) mechanisms with success rates |
| Budget Templates | `budget_templates` | 78 | Budget allocation guidelines by mechanism and category |
| Funder Requirements | `funder_requirements` | 33 | Compliance requirements for NIH, NSF, DOE, and foundations |
| Compliance Templates | `compliance_templates` | 3 | Report templates (RPPR, DMS plans, NSF reports) |
| Template Categories | `template_categories` | 8 | Categories for document templates |
| Document Templates | `templates` | 6 | System templates for specific aims, abstracts, etc. |
| Checklist Templates | `checklist_templates` | 4 | Application checklists for NIH R01, R21, NSF Standard, CAREER |
| Compliance Rules | `compliance_rules` | 7 | Formatting rules (font size, margins, page limits) |

### Individual Seed Scripts

You can also run individual seed scripts:

```bash
# Seed only grant mechanisms
python -m backend.scripts.seed_mechanisms

# Seed only budget templates
python -m backend.scripts.seed_budget_templates

# Seed only compliance requirements
python -m backend.scripts.seed_compliance_requirements

# Seed only document templates
python -c "import asyncio; from backend.services.seed_templates import seed_templates; asyncio.run(seed_templates())"

# Seed only checklists
python -c "import asyncio; from backend.services.seed_checklists import seed_checklist_templates; asyncio.run(seed_checklist_templates())"

# Seed only compliance rules
python -c "import asyncio; from backend.database import get_async_session; from backend.services.seed_compliance_rules import seed_compliance_rules; asyncio.run(seed_compliance_rules(get_async_session()))"
```

## Data Sources

| Source | Grants | Update Frequency |
|--------|--------|------------------|
| NIH Reporter | ~50,000 | Daily |
| NSF Awards | ~25,000 | Daily |
| Grants.gov | ~10,000 | Daily |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
