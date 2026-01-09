#!/bin/bash
#
# PostgreSQL Backup Cron Wrapper Script for GrandRadar
#
# This script is designed to be run from cron or systemd timer.
# It wraps the main backup.sh script with:
# - Proper logging to file
# - Error notifications (email/Slack)
# - Lock file to prevent concurrent runs
# - Health check integration
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/grantradar/scripts/backup/backup-cron.sh >> /var/log/grantradar-backup.log 2>&1
#
# Usage: ./backup-cron.sh [--upload-s3] [--encrypt]
#

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load environment variables
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Logging configuration
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/backup.log}"
MAX_LOG_SIZE="${MAX_LOG_SIZE:-10485760}"  # 10MB
MAX_LOG_FILES="${MAX_LOG_FILES:-5}"

# Lock file to prevent concurrent runs
LOCK_FILE="/tmp/grantradar_backup.lock"
LOCK_TIMEOUT="${LOCK_TIMEOUT:-3600}"  # 1 hour

# Notification configuration
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-}"
SMTP_SERVER="${SMTP_SERVER:-localhost}"

# Health check URL (optional - for services like healthchecks.io)
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"

# Backup script options (passed through)
BACKUP_OPTIONS=()

# =============================================================================
# Functions
# =============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

setup_logging() {
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"

    # Rotate logs if needed
    if [[ -f "$LOG_FILE" ]]; then
        local log_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
        if [[ "$log_size" -gt "$MAX_LOG_SIZE" ]]; then
            rotate_logs
        fi
    fi
}

rotate_logs() {
    log "Rotating log files..."

    # Shift existing log files
    for i in $(seq $((MAX_LOG_FILES - 1)) -1 1); do
        if [[ -f "${LOG_FILE}.${i}" ]]; then
            mv "${LOG_FILE}.${i}" "${LOG_FILE}.$((i + 1))"
        fi
    done

    # Rotate current log
    if [[ -f "$LOG_FILE" ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.1"
    fi

    # Remove oldest log if exceeds max
    if [[ -f "${LOG_FILE}.${MAX_LOG_FILES}" ]]; then
        rm -f "${LOG_FILE}.${MAX_LOG_FILES}"
    fi
}

acquire_lock() {
    log "Acquiring lock..."

    # Check if lock file exists and is stale
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        local lock_time=$(stat -f%m "$LOCK_FILE" 2>/dev/null || stat -c%Y "$LOCK_FILE" 2>/dev/null)
        local current_time=$(date +%s)
        local lock_age=$((current_time - lock_time))

        # Check if process is still running
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            if [[ "$lock_age" -gt "$LOCK_TIMEOUT" ]]; then
                log "Lock is stale (age: ${lock_age}s), removing..."
                rm -f "$LOCK_FILE"
            else
                log_error "Another backup is already running (PID: $lock_pid, age: ${lock_age}s)"
                exit 1
            fi
        else
            log "Stale lock file found (process not running), removing..."
            rm -f "$LOCK_FILE"
        fi
    fi

    # Create lock file
    echo $$ > "$LOCK_FILE"
    log "Lock acquired (PID: $$)"
}

release_lock() {
    log "Releasing lock..."
    rm -f "$LOCK_FILE"
}

send_slack_notification() {
    local status="$1"
    local message="$2"

    if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        return 0
    fi

    local color="good"
    local emoji=":white_check_mark:"

    if [[ "$status" == "error" ]]; then
        color="danger"
        emoji=":x:"
    elif [[ "$status" == "warning" ]]; then
        color="warning"
        emoji=":warning:"
    fi

    local hostname=$(hostname)
    local payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "$emoji GrandRadar Backup $status",
            "text": "$message",
            "fields": [
                {
                    "title": "Host",
                    "value": "$hostname",
                    "short": true
                },
                {
                    "title": "Time",
                    "value": "$(date '+%Y-%m-%d %H:%M:%S')",
                    "short": true
                }
            ]
        }
    ]
}
EOF
)

    curl -s -X POST -H "Content-Type: application/json" \
        -d "$payload" "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
}

send_email_notification() {
    local status="$1"
    local message="$2"

    if [[ -z "$NOTIFICATION_EMAIL" ]]; then
        return 0
    fi

    if ! command -v mail &> /dev/null; then
        log "mail command not available, skipping email notification"
        return 0
    fi

    local subject="[GrandRadar] Backup $status - $(hostname)"
    local body="GrandRadar Database Backup Report

Status: $status
Host: $(hostname)
Time: $(date '+%Y-%m-%d %H:%M:%S')

$message

---
This is an automated message from GrandRadar backup system.
"

    echo "$body" | mail -s "$subject" "$NOTIFICATION_EMAIL" 2>/dev/null || true
}

ping_healthcheck() {
    local status="$1"

    if [[ -z "$HEALTHCHECK_URL" ]]; then
        return 0
    fi

    local url="$HEALTHCHECK_URL"

    case "$status" in
        start)
            url="${url}/start"
            ;;
        success)
            # Default URL for success
            ;;
        fail)
            url="${url}/fail"
            ;;
    esac

    curl -s -m 10 "$url" > /dev/null 2>&1 || true
}

run_backup() {
    log "Starting backup..."

    local backup_script="$SCRIPT_DIR/backup.sh"

    if [[ ! -x "$backup_script" ]]; then
        log_error "Backup script not found or not executable: $backup_script"
        return 1
    fi

    # Run backup and capture output
    local output
    local exit_code=0

    output=$("$backup_script" "${BACKUP_OPTIONS[@]}" 2>&1) || exit_code=$?

    # Log output
    echo "$output" | while read -r line; do
        log "$line"
    done

    return $exit_code
}

cleanup() {
    release_lock
}

# =============================================================================
# Main
# =============================================================================

main() {
    local start_time=$(date +%s)
    local exit_code=0

    # Parse arguments (pass through to backup.sh)
    while [[ $# -gt 0 ]]; do
        case $1 in
            --upload-s3|--encrypt)
                BACKUP_OPTIONS+=("$1")
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    # Setup
    setup_logging

    # Redirect all output to log file
    exec > >(tee -a "$LOG_FILE") 2>&1

    log "=========================================="
    log "GrandRadar Backup Cron Job Started"
    log "=========================================="

    # Set up cleanup on exit
    trap cleanup EXIT

    # Acquire lock
    acquire_lock

    # Ping health check start
    ping_healthcheck "start"

    # Run backup
    if run_backup; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log "Backup completed successfully in ${duration}s"

        # Send success notifications
        send_slack_notification "Success" "Database backup completed successfully in ${duration} seconds."
        send_email_notification "Success" "Database backup completed successfully in ${duration} seconds."
        ping_healthcheck "success"
    else
        exit_code=$?
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log_error "Backup failed after ${duration}s with exit code $exit_code"

        # Send failure notifications
        send_slack_notification "error" "Database backup FAILED after ${duration} seconds. Exit code: $exit_code"
        send_email_notification "Failed" "Database backup FAILED after ${duration} seconds. Exit code: $exit_code. Check logs at: $LOG_FILE"
        ping_healthcheck "fail"
    fi

    log "=========================================="
    log "GrandRadar Backup Cron Job Finished"
    log "=========================================="

    exit $exit_code
}

main "$@"
