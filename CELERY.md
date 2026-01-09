# GrandRadar Celery Configuration

This document describes the Celery distributed task queue configuration for the GrandRadar platform.

## Quick Start

```bash
# Start Redis (required)
redis-server

# Start Celery worker (processes tasks)
./scripts/start_celery_worker.sh --dev

# Start Celery Beat (schedules periodic tasks)
./scripts/start_celery_beat.sh --dev

# Start Flower (optional, monitoring dashboard)
./scripts/start_flower.sh
```

## Architecture Overview

```
                    +----------------+
                    |   Celery Beat  |
                    |  (Scheduler)   |
                    +-------+--------+
                            |
                            | Schedules tasks
                            v
+------------+       +------+-------+       +---------------+
|  FastAPI   | ----> |    Redis     | <---- | Celery Worker |
|   App      |       |   (Broker)   |       |  (Processes)  |
+------------+       +--------------+       +---------------+
                            |
                            v
                    +-------+--------+
                    |    Redis       |
                    | (Result Store) |
                    +----------------+
```

## Queue Configuration

GrandRadar uses three priority queues:

| Queue | Priority | Purpose | Tasks |
|-------|----------|---------|-------|
| `critical` | Highest (10) | Urgent alerts, deadline notifications | High-match alerts, deadline reminders |
| `high` | High (7) | Grant processing, matching | New grant processing, API polling |
| `normal` | Standard (3) | Background tasks | Analytics, cleanup, indexing |

## Scheduled Tasks (Beat Schedule)

| Task | Schedule | Queue | Description |
|------|----------|-------|-------------|
| `grants-gov-poll` | Every 5 min | high | Poll Grants.gov RSS/XML |
| `nsf-poll` | Every 15 min | high | Poll NSF Award Search API |
| `nih-scrape` | Every 30 min | high | Scrape NIH funding page |
| `nih-reporter-poll` | Every 15 min | high | Poll NIH Reporter API |
| `deadline-reminder` | Hourly | critical | Send deadline reminders |
| `check-user-deadline-reminders` | Every 5 min | normal | Check user deadline configs |
| `analytics-compute` | Every 6 hours | normal | Compute daily analytics |
| `cleanup-expired` | Daily | normal | Clean up expired data |
| `send-funding-alerts` | Daily | normal | Send funding alert emails |
| `precalculate-workflow-analytics` | Hourly | normal | Pre-cache workflow analytics |
| `aggregate-workflow-analytics` | Daily | normal | Aggregate workflow metrics |

## Commands

### Starting Services

```bash
# Development mode (verbose logging, fewer workers)
./scripts/start_celery_worker.sh --dev
./scripts/start_celery_beat.sh --dev

# Production mode (optimized settings)
./scripts/start_celery_worker.sh --prod
./scripts/start_celery_beat.sh --prod

# Process specific queues only
./scripts/start_celery_worker.sh --queue=critical,high
./scripts/start_celery_worker.sh --queue=normal
```

### Manual Commands

```bash
# Start worker manually
celery -A backend.celery_app worker -l INFO -c 4 -Q critical,high,normal

# Start beat manually
celery -A backend.celery_app beat -l INFO

# Start flower manually
celery -A backend.celery_app flower --port=5555

# Inspect active workers
celery -A backend.celery_app inspect active

# Inspect scheduled tasks
celery -A backend.celery_app inspect scheduled

# Inspect reserved tasks
celery -A backend.celery_app inspect reserved

# Purge all tasks from a queue
celery -A backend.celery_app purge -Q normal

# List registered tasks
celery -A backend.celery_app inspect registered
```

### Running Tasks Manually

```bash
# Run a task directly (bypassing queue)
celery -A backend.celery_app call backend.tasks.analytics.compute_daily_analytics

# Run a task with arguments
celery -A backend.celery_app call backend.tasks.funding_alerts.send_funding_alert --args='["user-uuid-here"]'

# Check task status
celery -A backend.celery_app result <task-id>
```

### Python Shell

```python
from backend.celery_app import celery_app

# Send a task
result = celery_app.send_task('backend.tasks.analytics.compute_daily_analytics')
print(result.id)

# Import and call directly
from backend.tasks.analytics import compute_daily_analytics
result = compute_daily_analytics.delay()
print(result.get(timeout=60))

# Call with arguments
from backend.tasks.polling import poll_grants_gov
result = poll_grants_gov.delay()
```

## Monitoring

### Flower Dashboard

Access the Flower monitoring dashboard at `http://localhost:5555`

Features:
- Real-time task progress
- Worker status and control
- Task history and statistics
- Queue inspection

### Logging

Logs are written to:
- Worker: `logs/celery_worker.log` (when using `--logfile`)
- Beat: stdout by default
- Flower: `logs/flower.db` (task history)

PID files are stored in `logs/`:
- `logs/celery_worker.pid`
- `logs/celery_beat.pid`

## Task Modules

| Module | Tasks |
|--------|-------|
| `backend.tasks.polling` | `poll_grants_gov`, `poll_nsf`, `scrape_nih`, `poll_nih_reporter` |
| `backend.tasks.notifications` | `send_deadline_reminders`, `send_high_match_alert`, `send_password_reset_email` |
| `backend.tasks.deadline_reminders` | `check_and_send_deadline_reminders` |
| `backend.tasks.funding_alerts` | `send_funding_alert`, `send_scheduled_alerts` |
| `backend.tasks.analytics` | `compute_daily_analytics`, `compute_user_analytics` |
| `backend.tasks.cleanup` | `cleanup_expired_data`, `cleanup_old_alerts`, `cleanup_redis_streams` |
| `backend.tasks.workflow_analytics` | `aggregate_workflow_analytics`, `precalculate_analytics` |
| `backend.tasks.grants` | Grant processing tasks |
| `backend.tasks.matching` | Match computation tasks |
| `backend.tasks.indexing` | Search index tasks |
| `backend.tasks.embeddings` | Embedding generation tasks |

## Configuration

### Environment Variables

Set in `.env`:

```env
# Redis URLs
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Celery Settings (backend/celery_app.py)

Key settings:
- `task_serializer`: json
- `worker_concurrency`: 4 (configurable)
- `worker_prefetch_multiplier`: 2
- `task_soft_time_limit`: 300 seconds
- `task_time_limit`: 600 seconds
- `task_acks_late`: True
- `result_expires`: 86400 (24 hours)

## Circuit Breakers

External API calls are protected by circuit breakers:

| Service | Failure Threshold | Recovery Timeout |
|---------|------------------|------------------|
| Grants.gov | 5 failures | 2 minutes |
| NSF | 5 failures | 2 minutes |
| NIH | 5 failures | 3 minutes |
| NIH Reporter | 5 failures | 2 minutes |

When a circuit opens, polling tasks will skip that service until recovery.

## Retry Policy

Default retry configuration:
- Max retries: 3
- Retry backoff: Exponential
- Initial delay: 10 seconds
- Max delay: 5 minutes (300 seconds)
- Jitter: Enabled (prevents thundering herd)

## Troubleshooting

### Worker not processing tasks

1. Check Redis is running: `redis-cli ping`
2. Check worker is connected: `celery -A backend.celery_app inspect ping`
3. Check queue has tasks: `celery -A backend.celery_app inspect reserved`
4. Check for errors in worker logs

### Beat not scheduling tasks

1. Ensure only ONE beat instance is running
2. Check for stale PID file: `rm logs/celery_beat.pid`
3. Check beat schedule in `backend/celery_app.py`
4. Verify task names match between schedule and task definitions

### Tasks failing

1. Check task logs in Flower or worker output
2. Verify environment variables are set
3. Check circuit breaker status (may be open)
4. Verify database connectivity

### High memory usage

1. Reduce `worker_concurrency`
2. Reduce `worker_prefetch_multiplier`
3. Check for memory leaks in tasks
4. Use `celery -A backend.celery_app purge` to clear queues
