#!/bin/bash
#
# S3 Backup Upload Script for GrandRadar
#
# Features:
# - Upload backups to S3
# - Lifecycle management (set up S3 lifecycle rules)
# - Sync local backups to S3
# - List and manage S3 backups
#
# Usage: ./s3-upload.sh [COMMAND] [OPTIONS]
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

# S3 configuration
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"
S3_BACKUP_PREFIX="${S3_BACKUP_PREFIX:-grantradar/backups}"
S3_STORAGE_CLASS="${S3_STORAGE_CLASS:-STANDARD_IA}"
S3_LIFECYCLE_DAYS="${S3_LIFECYCLE_DAYS:-90}"
S3_GLACIER_DAYS="${S3_GLACIER_DAYS:-365}"
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Local configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"

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
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  upload <file>       Upload a specific backup file to S3"
    echo "  sync                Sync all local backups to S3"
    echo "  list                List backups in S3"
    echo "  download <file>     Download a backup from S3"
    echo "  delete <file>       Delete a backup from S3"
    echo "  setup-lifecycle     Configure S3 lifecycle rules"
    echo "  show-lifecycle      Show current lifecycle configuration"
    echo "  cleanup             Remove old S3 backups (based on lifecycle)"
    echo ""
    echo "Options:"
    echo "  --bucket <name>     Override S3 bucket name"
    echo "  --prefix <path>     Override S3 prefix"
    echo "  --help              Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  S3_BACKUP_BUCKET    S3 bucket name (required)"
    echo "  S3_BACKUP_PREFIX    S3 prefix/path (default: grantradar/backups)"
    echo "  S3_STORAGE_CLASS    Storage class (default: STANDARD_IA)"
    echo "  S3_LIFECYCLE_DAYS   Days before transition to Glacier (default: 90)"
    echo "  S3_GLACIER_DAYS     Days before deletion (default: 365)"
    echo "  AWS_PROFILE         AWS CLI profile to use (default: default)"
    echo "  AWS_REGION          AWS region (default: us-east-1)"
}

check_dependencies() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
}

check_bucket() {
    if [[ -z "$S3_BACKUP_BUCKET" ]]; then
        log_error "S3_BACKUP_BUCKET is not set"
        log_error "Set it in .env or pass --bucket option"
        exit 1
    fi

    # Verify bucket exists and is accessible
    if ! aws s3 ls "s3://$S3_BACKUP_BUCKET" --profile "$AWS_PROFILE" > /dev/null 2>&1; then
        log_error "Cannot access bucket: $S3_BACKUP_BUCKET"
        log_error "Check your AWS credentials and bucket permissions"
        exit 1
    fi
}

upload_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "File not found: $file"
        exit 1
    fi

    local filename=$(basename "$file")
    local s3_path="s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${filename}"

    log_info "Uploading: $file"
    log_info "Target: $s3_path"
    log_info "Storage class: $S3_STORAGE_CLASS"

    if aws s3 cp "$file" "$s3_path" \
        --storage-class "$S3_STORAGE_CLASS" \
        --profile "$AWS_PROFILE"; then

        local size=$(aws s3 ls "$s3_path" --profile "$AWS_PROFILE" | awk '{print $3}')
        log_success "Uploaded successfully ($(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo $size bytes))"
    else
        log_error "Upload failed!"
        exit 1
    fi
}

sync_backups() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi

    local s3_path="s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/"

    log_info "Syncing local backups to S3..."
    log_info "Source: $BACKUP_DIR"
    log_info "Target: $s3_path"

    if aws s3 sync "$BACKUP_DIR" "$s3_path" \
        --exclude "*" \
        --include "grantradar_backup_*.sql.gz*" \
        --storage-class "$S3_STORAGE_CLASS" \
        --profile "$AWS_PROFILE"; then
        log_success "Sync completed"
    else
        log_error "Sync failed!"
        exit 1
    fi
}

list_backups() {
    local s3_path="s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/"

    log_info "Listing backups in: $s3_path"
    echo ""

    aws s3 ls "$s3_path" --profile "$AWS_PROFILE" --human-readable | \
        grep -E "grantradar_backup_.*\.sql\.gz" | \
        awk '{printf "  %-50s %8s %8s  %s %s\n", $5, $3, $4, $1, $2}' || \
        echo "  No backups found"

    echo ""

    # Show total count and size
    local stats=$(aws s3 ls "$s3_path" --profile "$AWS_PROFILE" --summarize | tail -2)
    echo "Summary:"
    echo "$stats" | sed 's/^/  /'
}

download_backup() {
    local filename="$1"
    local local_path="$BACKUP_DIR/$filename"
    local s3_path="s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${filename}"

    mkdir -p "$BACKUP_DIR"

    log_info "Downloading: $s3_path"
    log_info "Target: $local_path"

    if aws s3 cp "$s3_path" "$local_path" --profile "$AWS_PROFILE"; then
        log_success "Downloaded: $local_path"
    else
        log_error "Download failed!"
        exit 1
    fi
}

delete_backup() {
    local filename="$1"
    local s3_path="s3://${S3_BACKUP_BUCKET}/${S3_BACKUP_PREFIX}/${filename}"

    log_info "Deleting: $s3_path"

    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Cancelled"
        exit 0
    fi

    if aws s3 rm "$s3_path" --profile "$AWS_PROFILE"; then
        log_success "Deleted"
    else
        log_error "Delete failed!"
        exit 1
    fi
}

setup_lifecycle() {
    log_info "Setting up S3 lifecycle rules..."
    log_info "Transition to Glacier after: $S3_LIFECYCLE_DAYS days"
    log_info "Expire after: $S3_GLACIER_DAYS days"

    local lifecycle_config=$(cat <<EOF
{
    "Rules": [
        {
            "ID": "GrandRadar-Backup-Lifecycle",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "${S3_BACKUP_PREFIX}/"
            },
            "Transitions": [
                {
                    "Days": ${S3_LIFECYCLE_DAYS},
                    "StorageClass": "GLACIER"
                }
            ],
            "Expiration": {
                "Days": ${S3_GLACIER_DAYS}
            },
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 30
            }
        }
    ]
}
EOF
)

    if aws s3api put-bucket-lifecycle-configuration \
        --bucket "$S3_BACKUP_BUCKET" \
        --lifecycle-configuration "$lifecycle_config" \
        --profile "$AWS_PROFILE"; then
        log_success "Lifecycle rules configured"
        echo ""
        echo "Lifecycle policy:"
        echo "  - Backups transition to Glacier after $S3_LIFECYCLE_DAYS days"
        echo "  - Backups expire (delete) after $S3_GLACIER_DAYS days"
        echo "  - Non-current versions expire after 30 days"
    else
        log_error "Failed to configure lifecycle rules"
        exit 1
    fi
}

show_lifecycle() {
    log_info "Current lifecycle configuration for: $S3_BACKUP_BUCKET"
    echo ""

    if aws s3api get-bucket-lifecycle-configuration \
        --bucket "$S3_BACKUP_BUCKET" \
        --profile "$AWS_PROFILE" 2>/dev/null; then
        :
    else
        log_info "No lifecycle configuration found"
    fi
}

cleanup_old_backups() {
    log_info "This will list expired backups based on lifecycle rules."
    log_info "S3 handles automatic deletion via lifecycle policies."
    log_info ""
    log_info "To manually clean up, consider:"
    echo "  1. Run 'setup-lifecycle' to configure automatic cleanup"
    echo "  2. Use 'delete <filename>' to remove specific files"
    echo "  3. Use AWS Console for advanced cleanup operations"
}

# =============================================================================
# Main
# =============================================================================

main() {
    local command=""
    local arg=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --bucket)
                S3_BACKUP_BUCKET="$2"
                shift 2
                ;;
            --prefix)
                S3_BACKUP_PREFIX="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            upload|sync|list|download|delete|setup-lifecycle|show-lifecycle|cleanup)
                command="$1"
                shift
                if [[ $# -gt 0 ]] && [[ ! "$1" == --* ]]; then
                    arg="$1"
                    shift
                fi
                ;;
            *)
                if [[ -z "$command" ]]; then
                    log_error "Unknown command: $1"
                    show_usage
                    exit 1
                fi
                arg="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$command" ]]; then
        show_usage
        exit 0
    fi

    # Check dependencies
    check_dependencies
    check_bucket

    # Execute command
    case "$command" in
        upload)
            if [[ -z "$arg" ]]; then
                log_error "Please specify a file to upload"
                exit 1
            fi
            upload_file "$arg"
            ;;
        sync)
            sync_backups
            ;;
        list)
            list_backups
            ;;
        download)
            if [[ -z "$arg" ]]; then
                log_error "Please specify a file to download"
                exit 1
            fi
            download_backup "$arg"
            ;;
        delete)
            if [[ -z "$arg" ]]; then
                log_error "Please specify a file to delete"
                exit 1
            fi
            delete_backup "$arg"
            ;;
        setup-lifecycle)
            setup_lifecycle
            ;;
        show-lifecycle)
            show_lifecycle
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
