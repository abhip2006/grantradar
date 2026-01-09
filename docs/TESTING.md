# GrandRadar Testing Guide

## Running Tests

### Full Test Suite
```bash
python3 -m pytest tests/ -v --tb=short
```

### With Coverage Report
```bash
python3 -m pytest tests/ -v --tb=short --cov=backend --cov=agents --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Unit tests only
python3 -m pytest tests/ -m unit

# API tests only
python3 -m pytest tests/ -m api

# Integration tests only
python3 -m pytest tests/ -m integration

# Agent tests
python3 -m pytest tests/ -m discovery
python3 -m pytest tests/ -m curation
python3 -m pytest tests/ -m matching
python3 -m pytest tests/ -m delivery
```

### Run Failed Tests Only
```bash
python3 -m pytest tests/ --last-failed
```

---

## Test Structure

```
tests/
├── agents/
│   ├── curation/
│   ├── delivery/
│   ├── discovery/
│   └── matching/
├── api/
│   ├── test_auth.py
│   ├── test_grants.py
│   ├── test_kanban.py
│   ├── test_analytics.py
│   └── ...
├── services/
│   ├── test_matching.py
│   ├── test_forecast.py
│   └── ...
├── conftest.py          # Test fixtures
└── test_audit.py        # Audit logging tests
```

---

## Key Fixtures

### Database Session
```python
@pytest.fixture
async def db_session():
    """Async database session for tests."""
```

### Authenticated User
```python
@pytest.fixture
async def authenticated_user(db_session):
    """Create and return an authenticated test user."""
```

### Test Client
```python
@pytest.fixture
async def client(db_session):
    """FastAPI test client with database session."""
```

---

## Test Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
markers =
    slow: marks tests as slow
    integration: integration tests
    unit: unit tests
    discovery: discovery agent tests
    curation: curation agent tests
    matching: matching engine tests
    delivery: delivery agent tests
    api: API endpoint tests
```

---

## Common Issues & Solutions

### Event Loop Errors
If you see `RuntimeError: There is no current event loop`:
- Ensure `tests/conftest.py` has function-scoped event_loop fixture
- Don't use session-scoped async fixtures

### Database Conflicts
If tests fail with unique constraint violations:
- Each test should clean up after itself
- Use `db_session.rollback()` in fixtures

### Skipped Tests
Some tests are skipped because they require:
- PostgreSQL-specific functions (array_agg)
- External services (actual API calls)

---

## Manual Testing Checklist

### Dashboard
- [ ] Grants load with match scores
- [ ] Filters work (Federal, Foundation, State)
- [ ] Search filters grants by title
- [ ] Save/dismiss buttons work

### Grant Detail
- [ ] Full grant information displays
- [ ] AI Insights section appears
- [ ] Generate Insights button triggers API call
- [ ] Quick actions (Save, Apply, Not Interested) work

### Analytics
- [ ] Overview tab shows metrics
- [ ] Performance tab shows charts
- [ ] Matches tab shows distribution
- [ ] Trends tab shows historical data

### Kanban
- [ ] Columns display correctly
- [ ] Cards can be dragged between columns
- [ ] Hover shows action buttons
- [ ] Add Application button works

### Portfolio
- [ ] Stats show saved grants count
- [ ] Timeline displays deadlines
- [ ] Watched grants list populates

### Team
- [ ] Members tab shows team
- [ ] Invitations tab shows pending invites
- [ ] Activity tab shows recent actions
- [ ] Permissions tab shows access levels

### Settings
- [ ] Profile updates save
- [ ] Notifications toggle works
- [ ] Calendar integration available
