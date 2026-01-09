#!/bin/bash
# GrandRadar Celery Beat Startup Script
#
# This script starts the Celery Beat scheduler which triggers periodic tasks.
# Beat is responsible for scheduling tasks like:
#   - Grant polling (every 5-30 minutes)
#   - Deadline reminders (hourly)
#   - Analytics computation (every 6 hours)
#   - Cleanup tasks (daily)
#
# Usage:
#   ./scripts/start_celery_beat.sh [options]
#
# Options:
#   --dev       Development mode (verbose logging)
#   --prod      Production mode (standard logging)
#   --help      Show this help message
#
# Note: Only run ONE beat scheduler instance at a time!
# Multiple beat instances will cause duplicate task execution.

set -e

# Default settings
LOG_LEVEL="INFO"
SCHEDULER="celery.beat:PersistentScheduler"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dev)
            LOG_LEVEL="DEBUG"
            echo "Running in DEVELOPMENT mode"
            ;;
        --prod)
            LOG_LEVEL="INFO"
            echo "Running in PRODUCTION mode"
            ;;
        --help)
            echo "GrandRadar Celery Beat Startup Script"
            echo ""
            echo "Usage: ./scripts/start_celery_beat.sh [options]"
            echo ""
            echo "Options:"
            echo "  --dev       Development mode (verbose logging)"
            echo "  --prod      Production mode (standard logging)"
            echo "  --help      Show this help message"
            echo ""
            echo "Scheduled Tasks:"
            echo "  grants-gov-poll           - Every 5 minutes"
            echo "  nsf-poll                  - Every 15 minutes"
            echo "  nih-scrape                - Every 30 minutes"
            echo "  nih-reporter-poll         - Every 15 minutes"
            echo "  deadline-reminder         - Every hour"
            echo "  check-user-deadline-reminders - Every 5 minutes"
            echo "  analytics-compute         - Every 6 hours"
            echo "  cleanup-expired           - Daily"
            echo "  send-funding-alerts       - Daily"
            echo "  precalculate-workflow-analytics - Hourly"
            echo "  aggregate-workflow-analytics - Daily"
            echo ""
            echo "WARNING: Only run ONE beat instance at a time!"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "Warning: No virtual environment found. Ensure dependencies are installed."
    fi
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Warning: Redis may not be running. Beat may fail to connect."
    echo "Start Redis with: redis-server"
fi

# Check for existing beat process
if [ -f "logs/celery_beat.pid" ]; then
    OLD_PID=$(cat logs/celery_beat.pid 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Error: Celery Beat is already running (PID: $OLD_PID)"
        echo "Only one beat scheduler should run at a time!"
        echo "Stop the existing process first: kill $OLD_PID"
        exit 1
    fi
    # Clean up stale PID file
    rm -f logs/celery_beat.pid
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting Celery Beat scheduler..."
echo "  Log level: $LOG_LEVEL"
echo "  Scheduler: $SCHEDULER"
echo "  Schedule DB: celerybeat-schedule.db"
echo ""

# Start Celery Beat
# -A: Application module
# -l: Log level
# -S: Scheduler class
# --pidfile: PID file location
# -s: Schedule database file location

exec celery -A backend.celery_app beat \
    --loglevel="$LOG_LEVEL" \
    --scheduler="$SCHEDULER" \
    --pidfile="logs/celery_beat.pid" \
    -s celerybeat-schedule.db
