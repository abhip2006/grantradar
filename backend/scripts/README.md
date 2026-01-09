# Backend Scripts

Utility scripts for database seeding, migrations, and maintenance.

## Available Scripts

### seed_mechanisms.py

Seeds the `grant_mechanisms` table with NIH and NSF mechanism reference data.

#### Overview

This script populates the `grant_mechanisms` table with comprehensive information about grant mechanisms from major funding agencies including:

- **NIH Research Grants**: R01, R21, R03, R15
- **NIH Career Development Awards**: K01, K08, K23, K99
- **NIH Fellowship Awards**: F31, F32
- **NSF Grants**: CAREER, Standard Research, SBIR/STTR

#### Data Included

Each mechanism record includes:
- **Mechanism Code**: Standard abbreviation (e.g., "R01", "K99")
- **Name**: Full descriptive name
- **Description**: Detailed explanation of the mechanism
- **Funding Agency**: NIH, NSF, or other
- **Category**: research, career, training, fellowship
- **Typical Duration**: Project duration in months
- **Typical Budget**: Min and max annual budget in USD
- **Success Rates**:
  - Overall success rate
  - New application success rate
  - Renewal success rate
  - Resubmission success rate
- **Competition Level**: low, medium, high, very_high
- **Estimated Applicants**: Per funding cycle
- **Review Criteria**: Ordered review criteria with importance
- **Tips**: Best practices and application recommendations

#### Prerequisites

1. Database must be initialized with the migration:
   ```bash
   alembic upgrade 031
   ```

2. Environment variables configured (.env file):
   ```
   DATABASE_URL=postgresql://user:password@localhost/grantradar
   ```

#### Usage

**As a Python Script:**
```bash
python -m backend.scripts.seed_mechanisms
```

**From Python Code:**
```python
import asyncio
from backend.scripts.seed_mechanisms import seed_mechanisms

asyncio.run(seed_mechanisms())
```

**With FastAPI Application:**
```python
# In startup event
from contextlib import asynccontextmanager
from backend.scripts.seed_mechanisms import seed_mechanisms

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed mechanisms if not already present
    await seed_mechanisms()
    yield
    # Shutdown code here

app = FastAPI(lifespan=lifespan)
```

#### Output

The script will:
1. Check if each mechanism already exists by code
2. Skip existing mechanisms to prevent duplicates
3. Insert new mechanisms with proper timestamps
4. Print progress for each insertion
5. Report "Seed complete!" when finished

Example output:
```
Inserted mechanism: R01 - Research Project Grant
Inserted mechanism: R21 - Exploratory/Developmental Research Grant
Inserted mechanism: R03 - Small Grant Program
...
Seed complete! Inserted mechanism data successfully.
```

#### Database Schema

The `grant_mechanisms` table structure:

```sql
CREATE TABLE grant_mechanisms (
    id UUID PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    funding_agency VARCHAR(50),
    category VARCHAR(50),
    typical_duration_months INTEGER,
    typical_budget_min INTEGER,
    typical_budget_max INTEGER,
    success_rate_overall FLOAT,
    success_rate_new FLOAT,
    success_rate_renewal FLOAT,
    success_rate_resubmission FLOAT,
    competition_level VARCHAR(30),
    estimated_applicants_per_cycle INTEGER,
    review_criteria JSONB,
    tips JSONB,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

#### Using the Data

Once seeded, query mechanisms in your application:

```python
from backend.database import get_async_session
from sqlalchemy import select
from backend.models import GrantMechanism

async with get_async_session() as session:
    # Get all NIH mechanisms
    result = await session.execute(
        select(GrantMechanism).where(
            GrantMechanism.funding_agency == "NIH"
        )
    )
    mechanisms = result.scalars().all()

    # Get specific mechanism
    result = await session.execute(
        select(GrantMechanism).where(
            GrantMechanism.code == "R01"
        )
    )
    r01_grant = result.scalar_one_or_none()

    # Get high-competition mechanisms
    result = await session.execute(
        select(GrantMechanism).where(
            GrantMechanism.competition_level == "high"
        )
    )
    competitive_mechanisms = result.scalars().all()
```

#### Data Sources

Success rates and statistical data based on:
- NIH National Institutes of Health FY statistics
- NSF Award Statistics (published annually)
- Program-specific guidance documents

Note: Success rates and budgets are approximate and may vary by year and institute.

#### Updating Mechanism Data

To update mechanism information:

1. Edit the `MECHANISMS_DATA` list in `seed_mechanisms.py`
2. If modifying an existing mechanism, use `UPDATE` instead of `INSERT`
3. For new mechanisms, add to the list and run the script

For ongoing updates, consider creating a management command:
```bash
python manage.py update_mechanisms --code=R01 --success-rate=0.22
```

#### Troubleshooting

**"Mechanism X already exists"**
- Script found existing record, skipping
- To force update, delete from database and re-run
- Or modify script to use UPSERT (update or insert)

**"Connection refused"**
- Database not running
- Check DATABASE_URL configuration
- Verify PostgreSQL is accessible

**"table grant_mechanisms does not exist"**
- Migration not applied
- Run: `alembic upgrade 031`

## Future Scripts

Potential future scripts:
- `update_success_rates.py` - Annual update of NIH/NSF statistics
- `sync_mechanisms_api.py` - Sync with live funding agency APIs
- `generate_mechanism_reports.py` - Analytics on mechanism popularity

