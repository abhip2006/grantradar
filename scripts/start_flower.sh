#!/bin/bash
# GrandRadar Celery Flower Monitoring Startup Script
#
# This script starts Flower, a real-time web-based monitoring tool for Celery.
# Flower provides:
#   - Real-time worker status and task progress
#   - Task history and statistics
#   - Worker control (shutdown, restart)
#   - Task rate limiting and management
#
# Usage:
#   ./scripts/start_flower.sh [options]
#
# Options:
#   --port=X    Port to run Flower on (default: 5555)
#   --auth      Enable basic authentication
#   --help      Show this help message
#
# Access the dashboard at: http://localhost:5555

set -e

# Default settings
PORT=5555
AUTH=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --port=*)
            PORT="${arg#*=}"
            echo "Running on port: $PORT"
            ;;
        --auth)
            echo "Basic authentication enabled"
            echo "Set FLOWER_BASIC_AUTH environment variable (format: user:password)"
            AUTH="--basic_auth=${FLOWER_BASIC_AUTH:-admin:admin}"
            ;;
        --help)
            echo "GrandRadar Celery Flower Monitoring Startup Script"
            echo ""
            echo "Usage: ./scripts/start_flower.sh [options]"
            echo ""
            echo "Options:"
            echo "  --port=X    Port to run Flower on (default: 5555)"
            echo "  --auth      Enable basic authentication"
            echo "  --help      Show this help message"
            echo ""
            echo "Dashboard Features:"
            echo "  - Real-time task monitoring"
            echo "  - Worker status and control"
            echo "  - Task history and statistics"
            echo "  - Queue inspection"
            echo ""
            echo "Access at: http://localhost:5555"
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
    echo "Warning: Redis may not be running. Flower may fail to connect."
    echo "Start Redis with: redis-server"
fi

# Set Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting Celery Flower monitoring..."
echo "  Port: $PORT"
echo "  Dashboard URL: http://localhost:$PORT"
echo ""

# Start Flower
# -A: Application module
# --port: Web server port
# --broker: Redis broker URL (from app config)
# --persistent: Enable persistent database for task history
# --db: SQLite database for persistence

exec celery -A backend.celery_app flower \
    --port="$PORT" \
    --persistent=True \
    --db="logs/flower.db" \
    $AUTH
