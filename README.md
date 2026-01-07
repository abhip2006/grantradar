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

6. **Start the backend**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

7. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

8. **Start the frontend**
   ```bash
   npm run dev
   ```

9. **Open the app**
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
