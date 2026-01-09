# GrantRadar Celery Tasks Documentation

Complete guide to running, testing, and monitoring all GrantRadar Celery tasks and the event-driven architecture.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Task Modules](#task-modules)
- [Queue Routing](#queue-routing)
- [Running Celery](#running-celery)
- [Event Stream Flow](#event-stream-flow)
- [Configuration](#configuration)
- [Testing Tasks](#testing-tasks)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Overview

GrantRadar uses Celery for distributed task processing with a multi-queue priority system and Redis Streams for event-driven communication between agents.

### Key Components
- **Celery Workers**: Process background tasks (discovery, validation, matching, alerts)
- **Celery Beat**: Scheduler for periodic tasks (polling, deadline reminders, analytics)
- **Redis Streams**: Event bus for agent-to-agent communication
- **Redis Queues**: Task queue storage (3 priority levels)

### Processing Pipeline
```
Discovery → Validation → Matching → Alert Delivery
   (high)     (high)      (high)      (critical/high/normal)
```

---

## Architecture

### Task Dependency Graph
```
Scheduled Tasks (Celery Beat)
├── poll_grants_gov (every 5 min)  ──┐
├── poll_nsf (every 15 min)         ├──> [grants:discovered stream]
└── scrape_nih (every 30 min)       ┘
                                     │
                                     ▼
                         validate_grant_task ──> [grants:validated stream]
                                     │
                                     ▼
                        process_grant_matches ──> [matches:computed stream]
                                     │
                                     ▼
                    ┌────────────────┴──────────────┐
                    │                               │
            send_critical_alert          send_high_priority_alert
            (SMS+Email+Slack)              (Email+Slack)
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                          Alert Delivery Complete

Maintenance Tasks (Scheduled)
├── send_deadline_reminders (hourly)
├── compute_daily_analytics (every 6h)
└── cleanup_expired_data (daily)
```

---

## Task Modules

### 1. Discovery Tasks (`agents/discovery/`)

#### `discover_grants_gov` (Grants.gov RSS)
- **Module**: `agents.discovery.grants_gov_rss`
- **Queue**: `high`
- **Schedule**: Every 5 minutes
- **Purpose**: Poll Grants.gov RSS feed and publish to `grants:discovered` stream
- **API Keys**: None required (public API)

**Key Features**:
- Rate limiting (3 req/sec)
- Duplicate detection via Redis set
- Fetches full details from Grants.gov API
- Circuit breaker for API failures

**Task Signature**:
```python
discover_grants_gov.delay()  # No arguments
```

#### `poll_nsf` (NSF API)
- **Module**: `backend.tasks.polling` (referenced but not yet implemented)
- **Queue**: `high`
- **Schedule**: Every 15 minutes
- **Purpose**: Poll NSF awards API

#### `scrape_nih` (NIH Reporter)
- **Module**: `backend.tasks.polling` (referenced but not yet implemented)
- **Queue**: `high`
- **Schedule**: Every 30 minutes
- **Purpose**: Scrape NIH Reporter for new grants

---

### 2. Validation/Curation Tasks (`agents/curation/`)

#### `validate_grant_task`
- **Module**: `agents.curation.validator`
- **Queue**: `high`
- **Purpose**: Validate, categorize, and enrich discovered grants
- **API Keys**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

**Processing Steps**:
1. Quality validation using Claude (checks title, description, deadline)
2. Research categorization (10 predefined categories)
3. Embedding generation using OpenAI `text-embedding-3-small`
4. Duplicate detection (Levenshtein distance + LLM comparison)
5. Publish to `grants:validated` stream

**Task Signature**:
```python
validate_grant_task.delay(grant_data: dict)
```

**Input Schema** (grant_data):
```python
{
    "grant_id": str,
    "external_id": str,
    "source": str,  # "grants_gov", "nsf", "nih"
    "title": str,
    "description": str,
    "funding_agency": str,
    "estimated_amount": float,
    "deadline": str,  # ISO format
    "url": str,
    "raw_data": dict
}
```

#### `consume_discovery_stream_task`
- **Purpose**: Consumer task that reads from `grants:discovered` stream
- **Mode**: Batch processing (10 grants per batch)

#### `run_validator_worker`
- **Purpose**: Long-running worker that continuously consumes discovery stream
- **Iterations**: 100 batches before completing

---

### 3. Matching Tasks (`agents/matching/`)

#### `process_grant_matches`
- **Module**: `agents.matching.matcher`
- **Queue**: `high`
- **Priority**: 7
- **Purpose**: Two-phase matching (vector similarity + LLM re-ranking)
- **API Keys**: `ANTHROPIC_API_KEY`, Database connection

**Matching Algorithm**:
1. **Phase 1**: Vector similarity search using pgvector (top 50 candidates, threshold: 0.6)
2. **Phase 2**: LLM re-ranking using Claude (top 20 candidates, batches of 5)
3. **Final Score**: `0.4 * vector_similarity + 0.6 * llm_match_score`
4. Publish matches >70% to `matches:computed` stream

**Task Signature**:
```python
process_grant_matches.delay(grant_id: str)  # UUID string
```

**Output**: Publishes `MatchComputedEvent` to Redis stream with priority level

#### `run_matching_consumer`
- **Purpose**: Long-running consumer that reads from `grants:validated` stream
- **Mode**: Continuous polling with 5s block timeout

---

### 4. Alert Delivery Tasks (`agents/delivery/`)

#### `send_critical_alert`
- **Module**: `agents.delivery.alerter`
- **Queue**: `critical`
- **Priority**: 10
- **Channels**: SMS + Email + Slack
- **Trigger**: Match score >95% AND deadline <14 days
- **API Keys**: `ANTHROPIC_API_KEY`, `SENDGRID_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

**Task Signature**:
```python
send_critical_alert.delay(payload_json: str)  # AlertPayload as JSON
```

#### `send_high_priority_alert`
- **Queue**: `high`
- **Channels**: Email + Slack
- **Trigger**: Match score 85-95%

#### `send_medium_priority_alert`
- **Queue**: `normal`
- **Channels**: Email only
- **Trigger**: Match score 70-85%
- **Batching**: If user has >3 medium alerts/day, batches into digest

#### `process_digest_batch`
- **Queue**: `normal`
- **Purpose**: Send daily digest email with batched medium-priority alerts

#### `process_all_digests`
- **Schedule**: Daily (Celery Beat)
- **Purpose**: Process all pending digest batches at end of day

---

### 5. Scheduled Maintenance Tasks

#### `send_deadline_reminders`
- **Module**: `backend.tasks.notifications`
- **Queue**: `critical`
- **Schedule**: Every hour
- **Purpose**: Send alerts for grants with approaching deadlines (7 days, 3 days, 1 day)

#### `compute_daily_analytics`
- **Module**: `backend.tasks.analytics`
- **Queue**: `normal`
- **Schedule**: Every 6 hours
- **Purpose**: Compute metrics (discovery rate, match quality, delivery latency)

#### `cleanup_expired_data`
- **Module**: `backend.tasks.cleanup`
- **Queue**: `normal`
- **Schedule**: Daily
- **Purpose**: Clean up old task results, expired grants, processed stream entries

---

## Queue Routing

### Queue Definitions

#### `critical` Queue
- **Priority**: 10 (highest)
- **Max Priority**: 10
- **Use Cases**:
  - >90% match alerts
  - Urgent deadline notifications (<7 days)
  - Critical alert delivery

**Routed Tasks**:
- `send_high_match_alert`
- `send_deadline_urgent_alert`
- `process_high_priority_match`

#### `high` Queue
- **Priority**: 7
- **Max Priority**: 7
- **Use Cases**:
  - New grant processing
  - Grant validation
  - Match computation
  - Source polling

**Routed Tasks**:
- `process_new_grant`
- `validate_grant`
- `compute_grant_matches`
- `poll_grants_gov`
- `poll_nsf`
- `scrape_nih`

#### `normal` Queue (default)
- **Priority**: 3
- **Max Priority**: 3
- **Use Cases**:
  - Re-indexing
  - Analytics
  - Background cleanup
  - Batched alerts

**Routed Tasks**:
- `reindex_grants`
- `compute_analytics`
- `cleanup_old_data`
- Medium priority alerts

### Dynamic Priority Routing

The `route_by_priority()` helper automatically routes tasks:
```python
from backend.celery_app import route_by_priority

queue = route_by_priority(
    match_score=95.5,  # >90 → critical
    is_new_grant=True   # → high
)
```

---

## Running Celery

### 1. Start Redis
```bash
redis-server
# Or with Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. Start Celery Worker
```bash
# Basic worker (all queues)
celery -A backend.celery_app worker -l info -Q critical,high,normal

# Worker with concurrency control
celery -A backend.celery_app worker -l info -Q critical,high,normal \
  --concurrency=4 --prefetch-multiplier=2

# Dedicated critical queue worker (low-latency)
celery -A backend.celery_app worker -l info -Q critical \
  --concurrency=2 --prefetch-multiplier=1

# High-throughput worker for normal queue
celery -A backend.celery_app worker -l info -Q normal \
  --concurrency=8 --prefetch-multiplier=4
```

**Worker Options**:
- `-A backend.celery_app`: Application module
- `-l info`: Log level (debug, info, warning, error)
- `-Q`: Queue names (comma-separated)
- `--concurrency`: Number of worker processes (default: CPU count)
- `--prefetch-multiplier`: Tasks per worker to prefetch

### 3. Start Celery Beat (Scheduler)
```bash
# Basic beat scheduler
celery -A backend.celery_app beat -l info

# With custom schedule database location
celery -A backend.celery_app beat -l info \
  --schedule=/var/run/celerybeat-schedule
```

### 4. Start Flower (Monitoring Web UI)
```bash
# Basic Flower
celery -A backend.celery_app flower

# With authentication
celery -A backend.celery_app flower \
  --basic_auth=admin:password \
  --port=5555

# Access at: http://localhost:5555
```

### 5. Production Deployment (Systemd)

Create `/etc/systemd/system/grantradar-worker.service`:
```ini
[Unit]
Description=GrantRadar Celery Worker
After=network.target redis.target postgresql.target

[Service]
Type=forking
User=grantradar
Group=grantradar
WorkingDirectory=/opt/grantradar
Environment="PATH=/opt/grantradar/venv/bin"
ExecStart=/opt/grantradar/venv/bin/celery -A backend.celery_app worker \
  -l info -Q critical,high,normal --concurrency=4 --pidfile=/var/run/grantradar-worker.pid
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/grantradar-beat.service`:
```ini
[Unit]
Description=GrantRadar Celery Beat Scheduler
After=network.target redis.target

[Service]
Type=simple
User=grantradar
Group=grantradar
WorkingDirectory=/opt/grantradar
Environment="PATH=/opt/grantradar/venv/bin"
ExecStart=/opt/grantradar/venv/bin/celery -A backend.celery_app beat \
  -l info --schedule=/var/run/celerybeat-schedule
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable grantradar-worker grantradar-beat
sudo systemctl start grantradar-worker grantradar-beat
```

---

## Event Stream Flow

### Redis Streams Architecture

```
┌──────────────────┐
│  grants:discovered│  ← Discovery agents publish here
└────────┬─────────┘
         │ Consumer Group: discovery-validators
         ▼
┌──────────────────┐
│ grants:validated │  ← Validation agent publishes here
└────────┬─────────┘
         │ Consumer Group: curation-processors
         ▼
┌──────────────────┐
│ matches:computed │  ← Matching agent publishes here
└────────┬─────────┘
         │ Consumer Group: matching-workers
         ▼
┌──────────────────┐
│  alerts:pending  │  ← Alert delivery agent processes
└────────┬─────────┘
         │ Consumer Group: alert-dispatchers
         ▼
    Email/SMS/Slack
```

### Stream Details

#### `grants:discovered`
- **Purpose**: Newly discovered grants from external sources
- **Producer**: Discovery agents (Grants.gov, NSF, NIH)
- **Consumer Group**: `discovery-validators`
- **Retention**: 10,000 messages (approximate)

**Message Format**:
```json
{
  "payload": "{...DiscoveredGrant JSON...}",
  "event_type": "GrantDiscoveredEvent",
  "published_at": "2026-01-06T12:34:56Z"
}
```

#### `grants:validated`
- **Purpose**: Validated and enriched grants ready for matching
- **Producer**: Validation agent
- **Consumer Group**: `curation-processors`

**Message Format**:
```json
{
  "data": "{...GrantValidatedEvent JSON...}",
  "event_id": "uuid",
  "grant_id": "uuid",
  "quality_score": 0.95,
  "categories": ["Computer Science", "Engineering"],
  "embedding_generated": true,
  "validation_details": {...}
}
```

#### `matches:computed`
- **Purpose**: User-grant matches ready for alert delivery
- **Producer**: Matching agent
- **Consumer Group**: `matching-workers`

**Message Format**:
```json
{
  "data": "{...MatchComputedEvent JSON...}",
  "event_id": "uuid",
  "match_id": "uuid",
  "grant_id": "uuid",
  "user_id": "uuid",
  "match_score": 0.92,
  "priority_level": "CRITICAL",
  "matching_criteria": ["research_areas", "methods"],
  "explanation": "Strong alignment...",
  "grant_deadline": "2026-02-15T00:00:00Z"
}
```

#### `alerts:pending`
- **Purpose**: Queued alerts for delivery
- **Producer**: Alert delivery agent
- **Consumer Group**: `alert-dispatchers`

### Dead Letter Queues (DLQs)

Failed messages after 3 retries are moved to DLQs:
- `dlq:grants:discovered`
- `dlq:grants:validated`
- `dlq:matches:computed`
- `dlq:alerts:pending`

**DLQ Consumer Group**: `dlq-handlers`

### Consumer Groups

| Consumer Group | Stream | Purpose |
|----------------|--------|---------|
| `discovery-validators` | `grants:discovered` | Validate discovered grants |
| `curation-processors` | `grants:validated` | Process validated grants |
| `matching-workers` | `matches:computed` | Compute user matches |
| `alert-dispatchers` | `alerts:pending` | Send alerts |
| `dlq-handlers` | All DLQs | Handle failed messages |

---

## Configuration

### Required Environment Variables

```bash
# ===== Database =====
DATABASE_URL=postgresql://user:pass@localhost:5432/grantradar
ASYNC_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/grantradar

# ===== Redis =====
REDIS_URL=redis://localhost:6379/0              # Redis Streams
CELERY_BROKER_URL=redis://localhost:6379/1      # Celery broker
CELERY_RESULT_BACKEND=redis://localhost:6379/2  # Task results

# ===== AI API Keys =====
ANTHROPIC_API_KEY=your_anthropic_key_here        # Required for validation & matching
OPENAI_API_KEY=your_openai_key_here              # Required for embeddings

# ===== Notification Services =====
SENDGRID_API_KEY=your_sendgrid_key_here          # Email delivery
TWILIO_ACCOUNT_SID=your_twilio_sid_here          # SMS delivery
TWILIO_AUTH_TOKEN=your_twilio_token_here         # SMS authentication
TWILIO_PHONE_NUMBER=+1234567890      # SMS sender number

# ===== Application =====
SECRET_KEY=your_secret_key_here       # JWT signing (use: openssl rand -hex 32)
ENVIRONMENT=development
DEBUG=true
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# ===== Email Settings =====
FROM_EMAIL=alerts@grantradar.com
FROM_NAME=GrantRadar

# ===== LLM Configuration =====
LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=4096
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

### Celery Configuration

See `backend/celery_app.py` for full configuration. Key settings:

```python
# Time limits
task_soft_time_limit = 300  # 5 minutes
task_time_limit = 600       # 10 minutes hard limit

# Concurrency
worker_concurrency = 4
worker_prefetch_multiplier = 2

# Retry policy
task_default_retry_delay = 10
task_max_retries = 3
retry_backoff = True
retry_backoff_max = 300     # 5 minutes max delay
retry_jitter = True

# Result backend
result_expires = 86400      # 24 hours
task_acks_late = True
task_reject_on_worker_lost = True
```

### Database Setup

Ensure PostgreSQL has pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run migrations:
```bash
alembic upgrade head
```

---

## Testing Tasks

### 1. Test Individual Tasks

#### Discovery Task
```python
from agents.discovery.grants_gov_rss import discover_grants_gov

# Queue the task
result = discover_grants_gov.delay()

# Check status
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE

# Get result (blocking)
output = result.get(timeout=300)
print(output)
# {'status': 'success', 'grants_discovered': 5, 'grant_ids': [...]}
```

#### Validation Task
```python
from agents.curation.validator import validate_grant_task

grant_data = {
    "grant_id": "12345",
    "external_id": "OPP-123",
    "source": "grants_gov",
    "title": "AI Research Grant",
    "description": "Funding for AI safety research...",
    "funding_agency": "NSF",
    "estimated_amount": 500000,
    "deadline": "2026-12-31T23:59:59Z",
    "url": "https://grants.gov/...",
    "raw_data": {}
}

result = validate_grant_task.delay(grant_data)
enriched_grant = result.get(timeout=120)
print(f"Quality Score: {enriched_grant['quality_score']}")
print(f"Categories: {enriched_grant['categories']}")
```

#### Matching Task
```python
from agents.matching.matcher import process_grant_matches

grant_id = "550e8400-e29b-41d4-a716-446655440000"
result = process_grant_matches.delay(str(grant_id))
stats = result.get(timeout=180)
print(f"Matches found: {stats['matches_published']}")
```

#### Alert Task
```python
from agents.delivery.alerter import send_critical_alert
from agents.delivery.models import AlertPayload, UserInfo, GrantInfo, MatchInfo
from uuid import uuid4

payload = AlertPayload(
    match_id=uuid4(),
    user=UserInfo(
        user_id=uuid4(),
        name="Dr. Smith",
        email="smith@university.edu",
        phone="+15551234567",
    ),
    grant=GrantInfo(
        grant_id=uuid4(),
        title="AI Safety Research Grant",
        funding_agency="NSF",
        amount_min=250000,
        amount_max=500000,
        deadline=datetime(2026, 12, 31),
        url="https://grants.gov/...",
        description="...",
    ),
    match=MatchInfo(
        match_id=uuid4(),
        match_score=0.96,
        matching_criteria=["AI Safety", "Machine Learning"],
        explanation="Excellent fit for your research...",
    ),
    priority="CRITICAL",
    channels=["EMAIL", "SMS", "SLACK"],
)

result = send_critical_alert.delay(payload.model_dump_json())
delivery_status = result.get(timeout=60)
```

### 2. Test Event Stream Flow

#### Publish to Discovery Stream
```python
from backend.events import EventBus
from backend.core.events import GrantDiscoveredEvent
from uuid import uuid4
from datetime import datetime

bus = EventBus()
await bus.connect()

event = GrantDiscoveredEvent(
    event_id=uuid4(),
    grant_id=uuid4(),
    source="grants_gov",
    external_id="OPP-12345",
    title="Test Grant",
    agency="NSF",
    deadline=datetime(2026, 12, 31),
    url="https://example.com",
)

message_id = await bus.publish_grant_discovered(event)
print(f"Published: {message_id}")
```

#### Consume from Stream
```python
from backend.events import EventBus

bus = EventBus()
await bus.connect()
await bus.setup_consumer_groups()

# Read new messages
messages = await bus.consume(
    stream="grants:discovered",
    group="discovery-validators",
    consumer="test-consumer",
    count=10,
    block_ms=5000,
)

for msg_id, data in messages:
    print(f"Message {msg_id}: {data}")
    await bus.acknowledge("grants:discovered", "discovery-validators", msg_id)
```

### 3. Monitor Task Execution

#### Using Celery CLI
```bash
# Inspect active tasks
celery -A backend.celery_app inspect active

# View registered tasks
celery -A backend.celery_app inspect registered

# Check worker stats
celery -A backend.celery_app inspect stats

# View scheduled tasks (Beat)
celery -A backend.celery_app inspect scheduled

# Revoke a task
celery -A backend.celery_app revoke <task-id>
```

#### Using Python
```python
from backend.celery_app import celery_app

# Inspect registered tasks
print(celery_app.control.inspect().registered())

# Check active workers
print(celery_app.control.inspect().active())

# Get task result
from celery.result import AsyncResult
result = AsyncResult('task-id-here', app=celery_app)
print(result.state)
print(result.result)
```

### 4. Performance Testing

#### Load Test Discovery
```python
import asyncio
from agents.discovery.grants_gov_rss import discover_grants_gov

async def load_test_discovery(n=100):
    """Queue 100 discovery tasks."""
    tasks = []
    for i in range(n):
        result = discover_grants_gov.delay()
        tasks.append(result)

    # Wait for all
    for task in tasks:
        try:
            output = task.get(timeout=300)
            print(f"Task completed: {output}")
        except Exception as e:
            print(f"Task failed: {e}")

asyncio.run(load_test_discovery())
```

#### Measure Task Latency
```python
import time
from agents.matching.matcher import process_grant_matches

start = time.time()
result = process_grant_matches.delay(grant_id)
result.get()
latency = time.time() - start
print(f"Task latency: {latency:.2f}s")
```

---

## Monitoring

### 1. Flower Web UI

Access at `http://localhost:5555`

**Features**:
- Real-time task monitoring
- Worker status and stats
- Task history and results
- Rate limit graphs
- Queue length visualization

### 2. Redis Stream Monitoring

Check stream lengths:
```bash
redis-cli XLEN grants:discovered
redis-cli XLEN grants:validated
redis-cli XLEN matches:computed
redis-cli XLEN alerts:pending
```

Check consumer group info:
```bash
redis-cli XINFO GROUPS grants:discovered
redis-cli XPENDING grants:discovered discovery-validators
```

View stream messages:
```bash
# Read last 10 messages
redis-cli XREVRANGE grants:discovered + - COUNT 10

# Read specific message
redis-cli XRANGE grants:discovered <msg-id> <msg-id>
```

### 3. Task Metrics

GrantRadar tracks these metrics (see `backend/celery_app.py`):

#### Task Latency Tracking
```python
# Emitted on task completion
task_name: str
latency: float  # seconds
state: str      # SUCCESS, FAILURE, RETRY
```

#### Integration Points
The `emit_task_metric()` function is a placeholder for integration with:
- **Prometheus**: `prometheus_client` library
- **Datadog**: `datadog` library
- **CloudWatch**: `boto3` client
- **StatsD**: `statsd` library

Example Prometheus integration:
```python
from prometheus_client import Histogram, Counter

TASK_LATENCY = Histogram(
    'celery_task_latency_seconds',
    'Task execution latency',
    ['task_name'],
)

TASK_COUNTER = Counter(
    'celery_task_total',
    'Total tasks executed',
    ['task_name', 'state'],
)

def emit_task_metric(task_name: str, latency: float, state: str | None) -> None:
    TASK_LATENCY.labels(task=task_name).observe(latency)
    TASK_COUNTER.labels(task=task_name, state=state).inc()
```

### 4. Circuit Breaker Monitoring

Check circuit breaker states:
```python
from backend.celery_app import grants_gov_circuit, nsf_circuit, nih_circuit

print(f"Grants.gov circuit: {grants_gov_circuit.state}")
print(f"NSF circuit: {nsf_circuit.state}")
print(f"NIH circuit: {nih_circuit.state}")
```

States:
- `CLOSED`: Normal operation
- `OPEN`: Service failing, requests blocked
- `HALF_OPEN`: Testing recovery

### 5. Health Checks

#### Celery Health
```python
from backend.celery_app import celery_app

# Ping workers
celery_app.control.inspect().ping()
```

#### Redis Streams Health
```python
from backend.events import get_event_bus

bus = await get_event_bus()
health = await bus.health_check()
print(health)
# {
#   "status": "healthy",
#   "connected": true,
#   "latency_ms": 1.23,
#   "stream_lengths": {...}
# }
```

---

## Troubleshooting

### Common Issues

#### 1. Task Not Starting
```bash
# Check if worker is running
celery -A backend.celery_app inspect active

# Verify queue routing
celery -A backend.celery_app inspect registered

# Check Redis connection
redis-cli ping
```

**Fix**:
```bash
# Restart worker
sudo systemctl restart grantradar-worker

# Or manually
celery -A backend.celery_app worker -l debug
```

#### 2. Consumer Group Not Found
**Error**: `NOGROUP No such consumer group`

**Fix**:
```python
from backend.events import EventBus

bus = EventBus()
await bus.connect()
await bus.setup_consumer_groups()  # Creates all groups
```

Or manually:
```bash
redis-cli XGROUP CREATE grants:discovered discovery-validators 0 MKSTREAM
```

#### 3. Stuck Tasks / Stale Consumer Groups

**Symptoms**: Tasks stuck in `PENDING`, stream messages not processing

**Diagnosis**:
```bash
# Check pending messages
redis-cli XPENDING grants:discovered discovery-validators

# View consumer details
redis-cli XINFO CONSUMERS grants:discovered discovery-validators
```

**Fix** - Reset consumer group:
```bash
# Delete group (will lose pending state)
redis-cli XGROUP DESTROY grants:discovered discovery-validators

# Recreate from beginning
redis-cli XGROUP CREATE grants:discovered discovery-validators 0 MKSTREAM

# Or from latest (skip old messages)
redis-cli XGROUP CREATE grants:discovered discovery-validators $ MKSTREAM
```

#### 4. High Memory Usage

**Symptoms**: Redis memory growing, worker memory leaks

**Diagnosis**:
```bash
# Check Redis memory
redis-cli INFO memory

# Check stream lengths
redis-cli XLEN grants:discovered
```

**Fix** - Trim streams:
```python
from backend.events import EventBus

bus = EventBus()
await bus.connect()

# Trim to last 1000 messages
removed = await bus.trim_stream("grants:discovered", maxlen=1000)
print(f"Removed {removed} old messages")
```

Manual:
```bash
redis-cli XTRIM grants:discovered MAXLEN ~ 1000
```

#### 5. Rate Limiting Issues

**Error**: `429 Too Many Requests` from external APIs

**Fix** - Circuit breaker will automatically open. Check state:
```python
from backend.celery_app import grants_gov_circuit

print(grants_gov_circuit.state)  # Should be OPEN
# Wait for recovery timeout (120s for Grants.gov)
```

Manual reset:
```python
grants_gov_circuit._state = grants_gov_circuit.CLOSED
grants_gov_circuit._failure_count = 0
```

#### 6. Task Timeout

**Error**: `SoftTimeLimitExceeded` or `TimeLimitExceeded`

**Current Limits**:
- Soft: 300s (5 min)
- Hard: 600s (10 min)

**Fix** - Increase limits for specific task:
```python
@celery_app.task(
    soft_time_limit=600,  # 10 min
    time_limit=900,       # 15 min
)
def long_running_task():
    ...
```

#### 7. Duplicate Messages

**Symptoms**: Same grant processed multiple times

**Diagnosis**:
```bash
# Check processed IDs set
redis-cli SISMEMBER grants_gov:processed_ids OPP-12345
```

**Fix** - Ensure acknowledgment:
```python
# Always acknowledge after successful processing
await bus.acknowledge(stream, group, message_id)
```

#### 8. Missing API Keys

**Error**: `ValueError: ANTHROPIC_API_KEY is required`

**Fix**:
```bash
# Check .env file exists
cat .env | grep ANTHROPIC_API_KEY

# Load in shell
export $(cat .env | xargs)

# Restart worker
sudo systemctl restart grantradar-worker
```

#### 9. Database Connection Issues

**Error**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Diagnosis**:
```bash
# Test database connection
psql -U grantradar -d grantradar -h localhost

# Check if PostgreSQL is running
sudo systemctl status postgresql
```

**Fix**:
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

#### 10. Purge Queues

**Reset all queues**:
```bash
# Celery queues
celery -A backend.celery_app purge

# Redis streams (WARNING: deletes all messages)
redis-cli DEL grants:discovered grants:validated matches:computed alerts:pending
```

**Purge specific queue**:
```bash
celery -A backend.celery_app purge -Q critical
```

---

## Quick Reference

### Start All Services
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL (if not running as service)
postgres -D /usr/local/var/postgres

# Terminal 3: Celery Worker
celery -A backend.celery_app worker -l info -Q critical,high,normal

# Terminal 4: Celery Beat
celery -A backend.celery_app beat -l info

# Terminal 5: Flower
celery -A backend.celery_app flower
```

### Environment Setup
```bash
# Copy example env
cp .env.example .env

# Edit with your keys
vim .env

# Load variables
export $(cat .env | xargs)

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Setup Redis consumer groups
python -c "
import asyncio
from backend.events import get_event_bus
async def setup():
    bus = await get_event_bus()
    await bus.setup_consumer_groups()
asyncio.run(setup())
"
```

### Manual Task Execution
```bash
# Run discovery manually
python -m agents.discovery.grants_gov_rss

# Run validator manually
python -m agents.curation.validator

# Run matcher manually
python agents/matching/matcher.py

# Run alerter manually
python agents/delivery/alerter.py
```

---

## Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Streams Guide](https://redis.io/docs/data-types/streams/)
- [Flower Documentation](https://flower.readthedocs.io/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

For more details, see:
- `backend/celery_app.py` - Celery configuration
- `backend/events.py` - Redis Streams event bus
- `agents/` - Individual agent implementations
