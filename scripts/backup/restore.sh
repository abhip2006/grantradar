#!/bin/bash
#
# PostgreSQL Database Restore Script for GrandRadar
#
# Features:
# - Restore from local or S3 backup files
# - Safety checks before restore
# - Support for encrypted backups
# - Dry-run mode for verification
# - Point-in-time restore documentation
#
# Usage: ./restore.sh [OPTIONS] <backup_file_or_s3_path>
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

# Database configuration
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-grantradar}"
DB_USER="${PGUSER:-grantradar}"
DB_PASSWORD="${PGPASSWORD:-grantradar_dev_password}"

# Backup configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# S3 configuration
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"
AWS_PROFILE="${AWS_PROFILE:-default}"

# Flags
DRY_RUN=false
FORCE=false
BACKUP_SOURCE=""

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

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
}

show_usage() {
    echo "Usage: $0 [OPTIONS] <backup_file_or_s3_path>"
    echo ""
    echo "Arguments:"
    echo "  backup_file_or_s3_path   Local file path or S3 URI (s3://bucket/path/file.sql.gz)"
    echo ""
    echo "Options:"
    echo "  --dry-run         Show what would be done without executing"
    echo "  --force           Skip confirmation prompts"
    echo "  --list            List available local backups"
    echo "  --list-s3         List available S3 backups"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backups/grantradar_backup_20240115_120000.sql.gz"
    echo "  $0 s3://my-bucket/grantradar/backups/grantradar_backup_20240115_120000.sql.gz"
    echo "  $0 --list"
    echo "  $0 --force backups/latest.sql.gz"
}

check_dependencies() {
    local missing=()

    if ! command -v psql &> /dev/null; then
        missing+=("psql (PostgreSQL client)")
    fi

    if ! command -v gunzip &> /dev/null; then
        missing+=("gunzip")
    fi

    if [[ "$BACKUP_SOURCE" == s3://* ]] && ! command -v aws &> /dev/null; then
        missing+=("aws (AWS CLI)")
    fi

    if [[ "$BACKUP_SOURCE" == *.gpg ]] && ! command -v gpg &> /dev/null; then
        missing+=("gpg (GnuPG)")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
        exit 1
    fi
}

list_local_backups() {
    log_info "Available local backups in $BACKUP_DIR:"
    echo ""

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warn "Backup directory does not exist: $BACKUP_DIR"
        exit 0
    fi

    local count=0
    while IFS= read -r file; do
        local size=$(du -h "$file" | cut -f1)
        local mtime=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d'.' -f1)
        printf "  %-60s %8s  %s\n" "$(basename "$file")" "$size" "$mtime"
        ((count++))
    done < <(find "$BACKUP_DIR" -name "grantradar_backup_*.sql.gz*" -type f | sort -r)

    echo ""
    log_info "Total: $count backup(s)"
}

list_s3_backups() {
    if [[ -z "$S3_BACKUP_BUCKET" ]]; then
        log_error "S3_BACKUP_BUCKET is not set"
        exit 1
    fi

    local prefix="${S3_BACKUP_PREFIX:-grantradar/backups}"
    log_info "Available S3 backups in s3://${S3_BACKUP_BUCKET}/${prefix}/:"
    echo ""

    aws s3 ls "s3://${S3_BACKUP_BUCKET}/${prefix}/" --profile "$AWS_PROFILE" | \
        grep -E "grantradar_backup_.*\.sql\.gz" | \
        awk '{print "  " $4 "  " $3 "  " $1 " " $2}'
}

download_from_s3() {
    local s3_path="$1"
    local local_path="$BACKUP_DIR/$(basename "$s3_path")"

    log_info "Downloading backup from S3..."
    log_info "Source: $s3_path"
    log_info "Destination: $local_path"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would download: $s3_path -> $local_path"
        return 0
    fi

    mkdir -p "$BACKUP_DIR"

    if aws s3 cp "$s3_path" "$local_path" --profile "$AWS_PROFILE"; then
        BACKUP_SOURCE="$local_path"
        log_success "Downloaded backup from S3"
    else
        log_error "Failed to download backup from S3"
        exit 1
    fi
}

decrypt_backup() {
    local encrypted_file="$1"
    local decrypted_file="${encrypted_file%.gpg}"

    if [[ -z "$BACKUP_ENCRYPTION_KEY" ]]; then
        log_error "BACKUP_ENCRYPTION_KEY is not set. Cannot decrypt backup."
        exit 1
    fi

    log_info "Decrypting backup..."

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would decrypt: $encrypted_file -> $decrypted_file"
        return 0
    fi

    if echo "$BACKUP_ENCRYPTION_KEY" | gpg --batch --yes --passphrase-fd 0 \
        --decrypt --output "$decrypted_file" "$encrypted_file"; then
        BACKUP_SOURCE="$decrypted_file"
        log_success "Backup decrypted"
    else
        log_error "Decryption failed!"
        exit 1
    fi
}

verify_backup_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "Backup file not found: $file"
        exit 1
    fi

    log_info "Verifying backup file: $file"

    # Check file size
    local size=$(du -h "$file" | cut -f1)
    log_info "File size: $size"

    # Check if it's a valid gzip file
    if [[ "$file" == *.gz ]] && ! gunzip -t "$file" 2>/dev/null; then
        log_error "Invalid or corrupted gzip file"
        exit 1
    fi

    log_success "Backup file verified"
}

check_database_connection() {
    log_info "Checking database connection..."

    export PGPASSWORD="$DB_PASSWORD"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database connection successful"
    else
        log_error "Cannot connect to database: $DB_NAME@$DB_HOST:$DB_PORT"
        unset PGPASSWORD
        exit 1
    fi

    unset PGPASSWORD
}

get_current_db_stats() {
    export PGPASSWORD="$DB_PASSWORD"

    local table_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

    local db_size=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null | tr -d ' ')

    unset PGPASSWORD

    echo "Tables: ${table_count:-N/A}, Size: ${db_size:-N/A}"
}

confirm_restore() {
    if [[ "$FORCE" == true ]]; then
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "WARNING: Database Restore Operation"
    echo "=============================================="
    echo ""
    echo "This operation will:"
    echo "  1. Drop all existing tables in the database"
    echo "  2. Restore data from the backup file"
    echo ""
    echo "Target database: $DB_NAME@$DB_HOST:$DB_PORT"
    echo "Current state: $(get_current_db_stats)"
    echo "Backup file: $BACKUP_SOURCE"
    echo ""
    echo "=============================================="
    echo ""

    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
}

perform_restore() {
    local backup_file="$BACKUP_SOURCE"

    log_info "Starting database restore..."
    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "Backup file: $backup_file"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would restore database from: $backup_file"
        return 0
    fi

    export PGPASSWORD="$DB_PASSWORD"

    # Drop existing tables (cascade to handle dependencies)
    log_info "Dropping existing tables..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
DO \$\$
DECLARE
    r RECORD;
BEGIN
    -- Disable triggers
    SET session_replication_role = replica;

    -- Drop all tables in public schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;

    -- Drop all sequences
    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequence_name) || ' CASCADE';
    END LOOP;

    -- Re-enable triggers
    SET session_replication_role = DEFAULT;
END \$\$;
EOF

    # Restore from backup
    log_info "Restoring data from backup..."
    if gunzip -c "$backup_file" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1; then
        log_success "Database restored successfully"
    else
        log_error "Restore failed!"
        unset PGPASSWORD
        exit 1
    fi

    # Verify restore
    log_info "Verifying restore..."
    local new_stats=$(get_current_db_stats)
    log_info "Database state after restore: $new_stats"

    unset PGPASSWORD
}

cleanup_temp_files() {
    # Clean up any temporary decrypted files
    if [[ -n "${TEMP_DECRYPTED_FILE:-}" ]] && [[ -f "$TEMP_DECRYPTED_FILE" ]]; then
        rm -f "$TEMP_DECRYPTED_FILE"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    trap cleanup_temp_files EXIT

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --list)
                list_local_backups
                exit 0
                ;;
            --list-s3)
                list_s3_backups
                exit 0
                ;;
            --help)
                show_usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                BACKUP_SOURCE="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$BACKUP_SOURCE" ]]; then
        log_error "No backup file specified"
        show_usage
        exit 1
    fi

    log_info "GrandRadar Database Restore"
    log_info "==========================="

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Running in DRY RUN mode - no changes will be made"
    fi

    # Check dependencies
    check_dependencies

    # Download from S3 if needed
    if [[ "$BACKUP_SOURCE" == s3://* ]]; then
        download_from_s3 "$BACKUP_SOURCE"
    fi

    # Resolve relative paths
    if [[ ! "$BACKUP_SOURCE" = /* ]]; then
        BACKUP_SOURCE="$PROJECT_ROOT/$BACKUP_SOURCE"
    fi

    # Decrypt if needed
    if [[ "$BACKUP_SOURCE" == *.gpg ]]; then
        TEMP_DECRYPTED_FILE="${BACKUP_SOURCE%.gpg}"
        decrypt_backup "$BACKUP_SOURCE"
    fi

    # Verify backup file
    verify_backup_file "$BACKUP_SOURCE"

    # Check database connection
    check_database_connection

    # Confirm with user
    confirm_restore

    # Perform restore
    perform_restore

    echo ""
    echo "=============================================="
    echo "Restore Complete"
    echo "=============================================="
    echo "Database: $DB_NAME"
    echo "State: $(get_current_db_stats)"
    echo "=============================================="

    log_success "Restore completed successfully!"
}

main "$@"
