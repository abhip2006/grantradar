#!/bin/bash
# GrandRadar Celery Worker Startup Script
#
# This script starts the Celery worker with proper configuration.
# Workers process tasks from the Redis broker.
#
# Usage:
#   ./scripts/start_celery_worker.sh [options]
#
# Options:
#   --dev       Development mode (verbose logging, single worker)
#   --prod      Production mode (optimized settings)
#   --queue=X   Specific queue(s) to process (comma-separated)
#   --help      Show this help message
#
# Examples:
#   ./scripts/start_celery_worker.sh --dev
#   ./scripts/start_celery_worker.sh --prod
#   ./scripts/start_celery_worker.sh --queue=critical,high

set -e

# Default settings
CONCURRENCY=4
LOG_LEVEL="INFO"
QUEUES="critical,high,normal"
PREFETCH_MULTIPLIER=2
POOL="prefork"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dev)
            CONCURRENCY=2
            LOG_LEVEL="DEBUG"
            echo "Running in DEVELOPMENT mode"
            ;;
        --prod)
            CONCURRENCY=8
            LOG_LEVEL="INFO"
            PREFETCH_MULTIPLIER=4
            echo "Running in PRODUCTION mode"
            ;;
        --queue=*)
            QUEUES="${arg#*=}"
            echo "Processing queues: $QUEUES"
            ;;
        --help)
            echo "GrandRadar Celery Worker Startup Script"
            echo ""
            echo "Usage: ./scripts/start_celery_worker.sh [options]"
            echo ""
            echo "Options:"
            echo "  --dev       Development mode (verbose logging, 2 workers)"
            echo "  --prod      Production mode (optimized settings, 8 workers)"
            echo "  --queue=X   Specific queue(s) to process (comma-separated)"
            echo "  --help      Show this help message"
            echo ""
            echo "Queues available:"
            echo "  critical - High-priority alerts, urgent deadlines"
            echo "  high     - New grant processing, validation"
            echo "  normal   - Analytics, cleanup, background tasks"
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
    echo "Warning: Redis may not be running. Worker may fail to connect."
    echo "Start Redis with: redis-server"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting Celery worker..."
echo "  Concurrency: $CONCURRENCY"
echo "  Log level: $LOG_LEVEL"
echo "  Queues: $QUEUES"
echo "  Pool: $POOL"
echo ""

# Start Celery worker
# -A: Application module
# -l: Log level
# -c: Concurrency (number of worker processes)
# -Q: Queues to consume from
# -P: Pool type (prefork for CPU-bound, gevent/eventlet for I/O-bound)
# --prefetch-multiplier: Number of tasks to prefetch per worker
# -E: Enable events for monitoring
# --pidfile: PID file location
# --logfile: Log file location (optional, remove to log to stdout)

exec celery -A backend.celery_app worker \
    --loglevel="$LOG_LEVEL" \
    --concurrency="$CONCURRENCY" \
    --queues="$QUEUES" \
    --pool="$POOL" \
    --prefetch-multiplier="$PREFETCH_MULTIPLIER" \
    -E \
    --pidfile="logs/celery_worker.pid" \
    --hostname="worker@%h"
