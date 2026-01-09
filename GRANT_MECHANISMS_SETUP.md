# Grant Mechanisms Setup Guide

Complete implementation guide for the grant mechanisms feature in GrantRadar.

## Overview

The grant mechanisms feature provides reference data about funding opportunities from major agencies (NIH, NSF). It enables users to understand grant types, success rates, budget expectations, and application strategies.

## Components Created

### 1. Database Model
**File**: `/backend/models/mechanisms.py`

Defines the `GrantMechanism` SQLAlchemy model with the following fields:
- `id` (UUID): Unique identifier
- `code` (String): Grant mechanism code (e.g., "R01", "K99")
- `name` (String): Full mechanism name
- `description` (Text): Detailed description
- `funding_agency` (String): NIH, NSF, etc.
- `category` (String): research, career, training, fellowship
- `typical_duration_months` (Integer): Project duration
- `typical_budget_min/max` (Integer): Budget range in USD
- `success_rate_*` (Float): Success rates for different application types
- `competition_level` (String): low, medium, high, very_high
- `estimated_applicants_per_cycle` (Integer): Application volume
- `review_criteria` (JSONB): Review criteria and importance order
- `tips` (JSONB): Application tips and best practices
- `last_updated` (Timestamp): Last update time
- `created_at` (Timestamp): Creation time

**Indexes**:
- `code` - For fast mechanism lookup
- `funding_agency` - Filter by funder
- `category` - Filter by mechanism type
- `competition_level` - Filter by competitiveness

### 2. Database Migration
**File**: `/alembic/versions/031_add_grant_mechanisms.py`

Creates the `grant_mechanisms` table with:
- Primary key on `id`
- Unique constraint on `code`
- Four performance indexes

**To apply the migration**:
```bash
alembic upgrade 031
```

**To rollback**:
```bash
alembic downgrade 030
```

### 3. Seed Script
**File**: `/backend/scripts/seed_mechanisms.py`

Populates the database with 13 grant mechanisms across:

**NIH Research Grants** (4 mechanisms):
- R01: Research Project Grant (21% overall success)
- R21: Exploratory/Developmental (18% overall success)
- R03: Small Grant Program (25% overall success)
- R15: AREA - Academic Research Enhancement (28% overall success)

**NIH Career Development** (4 mechanisms):
- K01: Mentored Research Scientist (35% overall success)
- K08: Mentored Clinical Scientist (38% overall success)
- K23: Mentored Patient-Oriented Research (40% overall success)
- K99: Pathway to Independence (32% overall success)

**NIH Fellowships** (2 mechanisms):
- F31: Predoctoral NRSA (28% overall success)
- F32: Postdoctoral NRSA (30% overall success)

**NSF Grants** (3 mechanisms):
- CAREER: Faculty Early Career Development (18% overall success)
- Standard: NSF Standard Research Grant (25% overall success)
- SBIR/STTR: Small Business Innovation (15% overall success)

## Implementation Steps

### Step 1: Apply Database Migration
```bash
# From project root
alembic upgrade 031
```

Verify the table exists:
```sql
SELECT * FROM grant_mechanisms;
```

### Step 2: Seed the Data
```bash
# Run the seed script
python -m backend.scripts.seed_mechanisms
```

Expected output:
```
Inserted mechanism: R01 - Research Project Grant
Inserted mechanism: R21 - Exploratory/Developmental Research Grant
...
Inserted mechanism: SBIR/STTR - Small Business Innovation Research / Small Business Technology Transfer

Seed complete! Inserted mechanism data successfully.
```

### Step 3: Verify the Data
```python
from sqlalchemy import select
from backend.database import get_async_session
from backend.models import GrantMechanism

async with get_async_session() as session:
    result = await session.execute(select(GrantMechanism))
    mechanisms = result.scalars().all()
    print(f"Total mechanisms: {len(mechanisms)}")

    # List all
    for mech in mechanisms:
        print(f"  {mech.code}: {mech.name}")
```

## Integration with FastAPI

### Option 1: Startup Hook
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.scripts.seed_mechanisms import seed_mechanisms

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await seed_mechanisms()
    except Exception as e:
        print(f"Mechanisms already seeded or error: {e}")

    yield

    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)
```

### Option 2: Manual Seeding
```bash
# Before starting the application
python -m backend.scripts.seed_mechanisms
```

## API Integration

Add an endpoint to retrieve mechanisms:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import GrantMechanism

router = APIRouter()

@router.get("/mechanisms")
async def list_mechanisms(
    agency: str = None,
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List grant mechanisms with optional filtering."""
    query = select(GrantMechanism)

    if agency:
        query = query.where(GrantMechanism.funding_agency == agency)
    if category:
        query = query.where(GrantMechanism.category == category)

    result = await db.execute(query)
    mechanisms = result.scalars().all()

    return {
        "total": len(mechanisms),
        "mechanisms": [
            {
                "code": m.code,
                "name": m.name,
                "agency": m.funding_agency,
                "category": m.category,
                "competition_level": m.competition_level,
                "success_rates": {
                    "overall": m.success_rate_overall,
                    "new": m.success_rate_new,
                    "renewal": m.success_rate_renewal,
                    "resubmission": m.success_rate_resubmission,
                },
                "budget": {
                    "min": m.typical_budget_min,
                    "max": m.typical_budget_max,
                },
                "duration_months": m.typical_duration_months,
                "tips": m.tips,
            }
            for m in mechanisms
        ]
    }

@router.get("/mechanisms/{code}")
async def get_mechanism(code: str, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific mechanism."""
    result = await db.execute(
        select(GrantMechanism).where(GrantMechanism.code == code)
    )
    mechanism = result.scalar_one_or_none()

    if not mechanism:
        raise HTTPException(status_code=404, detail="Mechanism not found")

    return {
        "code": mechanism.code,
        "name": mechanism.name,
        "description": mechanism.description,
        "agency": mechanism.funding_agency,
        "category": mechanism.category,
        "competition_level": mechanism.competition_level,
        "success_rates": {
            "overall": mechanism.success_rate_overall,
            "new": mechanism.success_rate_new,
            "renewal": mechanism.success_rate_renewal,
            "resubmission": mechanism.success_rate_resubmission,
        },
        "budget": {
            "min": mechanism.typical_budget_min,
            "max": mechanism.typical_budget_max,
            "typical_annual_budget": f"${mechanism.typical_budget_min:,} - ${mechanism.typical_budget_max:,}"
        },
        "duration_months": mechanism.typical_duration_months,
        "estimated_applicants": mechanism.estimated_applicants_per_cycle,
        "review_criteria": mechanism.review_criteria,
        "tips": mechanism.tips,
        "last_updated": mechanism.last_updated.isoformat(),
    }
```

## Updating Mechanism Data

### For One-Time Updates
Edit `/backend/scripts/seed_mechanisms.py`:
1. Modify the `MECHANISMS_DATA` list
2. Delete affected records from database
3. Re-run the seed script

### For Ongoing Updates
Create a new script `/backend/scripts/update_mechanisms.py`:

```python
from sqlalchemy import update
from backend.database import get_async_session
from backend.models import GrantMechanism

async def update_success_rates(code: str, new_rate: float):
    """Update success rate for a mechanism."""
    async with get_async_session() as session:
        await session.execute(
            update(GrantMechanism)
            .where(GrantMechanism.code == code)
            .values(success_rate_overall=new_rate)
        )
        await session.commit()
```

## Data Accuracy

**Current Data Sources:**
- NIH success rates: FY 2023-2024 published statistics
- NSF success rates: Annual NSF Award Statistics
- Budget ranges: Program-specific guidance documents

**Notes:**
- Success rates vary by institute and year
- Budget ranges are typical maximums (may vary by program)
- Data should be updated annually with new statistics

## Related Tables

This feature integrates with:
- `grants`: Can link to mechanisms via grant type
- `deadlines`: Can reference mechanism types
- `grant_applications`: Can track mechanism choices

## File Structure

```
backend/
├── models/
│   ├── mechanisms.py           # GrantMechanism model
│   └── __init__.py             # Updated with GrantMechanism export
├── scripts/
│   ├── __init__.py            # Package marker
│   ├── seed_mechanisms.py      # Seeding script
│   └── README.md               # Script documentation
alembic/
└── versions/
    └── 031_add_grant_mechanisms.py  # Database migration
GRANT_MECHANISMS_SETUP.md       # This file
```

## Testing

Test the implementation:

```python
import pytest
from sqlalchemy import select
from backend.database import get_async_session
from backend.models import GrantMechanism

@pytest.mark.asyncio
async def test_grant_mechanisms_seeded():
    """Test that mechanisms are seeded correctly."""
    async with get_async_session() as session:
        result = await session.execute(select(GrantMechanism))
        mechanisms = result.scalars().all()

        assert len(mechanisms) == 13

        codes = {m.code for m in mechanisms}
        expected_codes = {"R01", "R21", "R03", "R15", "K01", "K08",
                         "K23", "K99", "F31", "F32", "CAREER",
                         "Standard", "SBIR/STTR"}
        assert codes == expected_codes

        # Verify NIH mechanisms
        nih_result = await session.execute(
            select(GrantMechanism).where(
                GrantMechanism.funding_agency == "NIH"
            )
        )
        nih_mechanisms = nih_result.scalars().all()
        assert len(nih_mechanisms) == 10

        # Verify NSF mechanisms
        nsf_result = await session.execute(
            select(GrantMechanism).where(
                GrantMechanism.funding_agency == "NSF"
            )
        )
        nsf_mechanisms = nsf_result.scalars().all()
        assert len(nsf_mechanisms) == 3
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "table grant_mechanisms does not exist" | Run `alembic upgrade 031` |
| "duplicate key value violates unique constraint" | Mechanisms already exist, script skips them |
| "Connection refused" | Verify DATABASE_URL and PostgreSQL is running |
| "ImportError: cannot import GrantMechanism" | Verify `backend/models/__init__.py` includes GrantMechanism |

## Next Steps

1. Apply migration: `alembic upgrade 031`
2. Run seed script: `python -m backend.scripts.seed_mechanisms`
3. Add API endpoints to expose mechanism data
4. Update frontend to display mechanism information
5. Link mechanisms to grant selection UI
6. Create annual update schedule for success rates

