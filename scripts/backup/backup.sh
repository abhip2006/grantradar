#!/bin/bash
#
# PostgreSQL Database Backup Script for GrandRadar
#
# Features:
# - Full database backup using pg_dump
# - Compressed output (.sql.gz)
# - Timestamped filenames
# - Configurable retention (delete backups older than X days)
# - Support for both local and S3 storage
# - Optional encryption with GPG
#
# Usage: ./backup.sh [--upload-s3] [--encrypt]
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

# Database configuration (can be overridden by environment)
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-grantradar}"
DB_USER="${PGUSER:-grantradar}"
DB_PASSWORD="${PGPASSWORD:-grantradar_dev_password}"

# Backup configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# S3 configuration (optional)
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"
S3_BACKUP_PREFIX="${S3_BACKUP_PREFIX:-grantradar/backups}"
AWS_PROFILE="${AWS_PROFILE:-default}"

# Timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="grantradar_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILENAME"

# Flags
UPLOAD_S3=false
ENCRYPT=false

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --upload-s3     Upload backup to S3 after creation"
    echo "  --encrypt       Encrypt backup with GPG (requires BACKUP_ENCRYPTION_KEY)"
    echo "  --help          Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD - Database connection"
    echo "  BACKUP_DIR              - Local backup directory (default: ./backups)"
    echo "  BACKUP_RETENTION_DAYS   - Days to keep local backups (default: 30)"
    echo "  BACKUP_ENCRYPTION_KEY   - GPG passphrase for encryption"
    echo "  S3_BACKUP_BUCKET        - S3 bucket for remote storage"
    echo "  S3_BACKUP_PREFIX        - S3 prefix/path (default: grantradar/backups)"
}

check_dependencies() {
    local missing=()

    if ! command -v pg_dump &> /dev/null; then
        missing+=("pg_dump (PostgreSQL client)")
    fi

    if ! command -v gzip &> /dev/null; then
        missing+=("gzip")
    fi

    if [[ "$UPLOAD_S3" == true ]] && ! command -v aws &> /dev/null; then
        missing+=("aws (AWS CLI)")
    fi

    if [[ "$ENCRYPT" == true ]] && ! command -v gpg &> /dev/null; then
        missing+=("gpg (GnuPG)")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
        exit 1
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

perform_backup() {
    log_info "Starting database backup..."
    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "Output: $BACKUP_PATH"

    # Export password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    # Perform backup with compression
    if pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-privileges \
        --verbose \
        2>&1 | gzip > "$BACKUP_PATH"; then

        local backup_size=$(du -h "$BACKUP_PATH" | cut -f1)
        log_success "Backup created successfully: $BACKUP_PATH ($backup_size)"
    else
        log_error "Backup failed!"
        rm -f "$BACKUP_PATH"
        exit 1
    fi

    unset PGPASSWORD
}

encrypt_backup() {
    if [[ "$ENCRYPT" != true ]]; then
        return 0
    fi

    if [[ -z "$BACKUP_ENCRYPTION_KEY" ]]; then
        log_error "BACKUP_ENCRYPTION_KEY is not set. Cannot encrypt backup."
        exit 1
    fi

    log_info "Encrypting backup..."

    local encrypted_path="${BACKUP_PATH}.gpg"

    if echo "$BACKUP_ENCRYPTION_KEY" | gpg --batch --yes --passphrase-fd 0 \
        --symmetric --cipher-algo AES256 \
        --output "$encrypted_path" \
        "$BACKUP_PATH"; then

        # Remove unencrypted backup
        rm -f "$BACKUP_PATH"
        BACKUP_PATH="$encrypted_path"
        BACKUP_FILENAME="${BACKUP_FILENAME}.gpg"
        log_success "Backup encrypted: $BACKUP_PATH"
    else
        log_error "Encryption failed!"
        exit 1
    fi
}

upload_to_s3() {
    if [[ "$UPLOAD_S3" != true ]]; then
        return 0
    fi

    if [[ -z "$S3_BACKUP_BUCKET" ]]; then
        log_error "S3_BACKUP_BUCKET is not set. Cannot upload to S3."
        exit 1
    fi

    log_info "Uploading backup to S3..."
    log_info "Target: s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${BACKUP_FILENAME}"

    if aws s3 cp "$BACKUP_PATH" \
        "s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${BACKUP_FILENAME}" \
        --profile "$AWS_PROFILE"; then
        log_success "Backup uploaded to S3"
    else
        log_error "S3 upload failed!"
        exit 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."

    local count=0
    while IFS= read -r -d '' file; do
        log_info "Removing old backup: $file"
        rm -f "$file"
        ((count++))
    done < <(find "$BACKUP_DIR" -name "grantradar_backup_*.sql.gz*" -type f -mtime +$BACKUP_RETENTION_DAYS -print0 2>/dev/null)

    if [[ $count -gt 0 ]]; then
        log_info "Removed $count old backup(s)"
    else
        log_info "No old backups to remove"
    fi
}

show_backup_info() {
    echo ""
    echo "=============================================="
    echo "Backup Summary"
    echo "=============================================="
    echo "Backup file: $BACKUP_PATH"
    echo "File size: $(du -h "$BACKUP_PATH" | cut -f1)"
    echo "Database: $DB_NAME"
    echo "Timestamp: $TIMESTAMP"
    if [[ "$ENCRYPT" == true ]]; then
        echo "Encrypted: Yes (AES-256)"
    fi
    if [[ "$UPLOAD_S3" == true ]]; then
        echo "S3 Location: s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${BACKUP_FILENAME}"
    fi
    echo "=============================================="
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --upload-s3)
                UPLOAD_S3=true
                shift
                ;;
            --encrypt)
                ENCRYPT=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    log_info "GrandRadar Database Backup"
    log_info "=========================="

    # Pre-flight checks
    check_dependencies
    create_backup_dir

    # Perform backup
    perform_backup

    # Optional encryption
    encrypt_backup

    # Optional S3 upload
    upload_to_s3

    # Cleanup old backups
    cleanup_old_backups

    # Show summary
    show_backup_info

    log_success "Backup completed successfully!"
}

main "$@"
