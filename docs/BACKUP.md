# GrandRadar Database Backup & Recovery Guide

This document describes the backup and recovery procedures for the GrandRadar PostgreSQL database.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Backup Scripts](#backup-scripts)
- [Restore Procedures](#restore-procedures)
- [S3 Storage](#s3-storage)
- [Automated Backups](#automated-backups)
- [Recovery Testing](#recovery-testing)
- [Troubleshooting](#troubleshooting)

## Overview

GrandRadar uses a PostgreSQL database with the pgvector extension for storing grant data, user information, and AI embeddings. The backup system provides:

- **Full database backups** using `pg_dump`
- **Compressed storage** (.sql.gz format)
- **Optional encryption** (AES-256 via GPG)
- **Local and S3 storage** options
- **Automated scheduling** via cron
- **Configurable retention** policies

## Quick Start

### Create a Manual Backup

```bash
# Basic backup (local storage)
./scripts/backup/backup.sh

# Backup with S3 upload
./scripts/backup/backup.sh --upload-s3

# Encrypted backup with S3 upload
./scripts/backup/backup.sh --encrypt --upload-s3
```

### Restore from Backup

```bash
# List available backups
./scripts/backup/restore.sh --list

# Restore from local backup
./scripts/backup/restore.sh backups/grantradar_backup_20240115_120000.sql.gz

# Restore from S3
./scripts/backup/restore.sh s3://my-bucket/grantradar/backups/grantradar_backup_20240115_120000.sql.gz
```

## Backup Scripts

### backup.sh

Main backup script that creates compressed database dumps.

**Usage:**
```bash
./scripts/backup/backup.sh [OPTIONS]

Options:
  --upload-s3     Upload backup to S3 after creation
  --encrypt       Encrypt backup with GPG (requires BACKUP_ENCRYPTION_KEY)
  --help          Show help message
```

**Features:**
- Full database dump using `pg_dump`
- Gzip compression
- Timestamped filenames
- Automatic cleanup of old backups (configurable retention)
- Optional S3 upload
- Optional AES-256 encryption

**Example Output:**
```
grantradar_backup_20240115_120000.sql.gz
grantradar_backup_20240115_120000.sql.gz.gpg  (if encrypted)
```

### restore.sh

Script to restore database from backup files.

**Usage:**
```bash
./scripts/backup/restore.sh [OPTIONS] <backup_file_or_s3_path>

Options:
  --dry-run       Show what would be done without executing
  --force         Skip confirmation prompts
  --list          List available local backups
  --list-s3       List available S3 backups
  --help          Show help message
```

**Safety Features:**
- Connection verification before restore
- Confirmation prompt (can be skipped with --force)
- Dry-run mode for testing
- Support for encrypted backups
- Support for S3 sources

### backup-cron.sh

Wrapper script for automated backups via cron.

**Features:**
- File-based logging with rotation
- Lock file to prevent concurrent runs
- Slack/email notifications
- Health check integration (healthchecks.io compatible)

### s3-upload.sh

Utility script for S3 operations.

**Commands:**
```bash
./scripts/backup/s3-upload.sh upload <file>      # Upload specific file
./scripts/backup/s3-upload.sh sync               # Sync all local backups to S3
./scripts/backup/s3-upload.sh list               # List S3 backups
./scripts/backup/s3-upload.sh download <file>    # Download from S3
./scripts/backup/s3-upload.sh delete <file>      # Delete from S3
./scripts/backup/s3-upload.sh setup-lifecycle    # Configure lifecycle rules
./scripts/backup/s3-upload.sh show-lifecycle     # Show current lifecycle config
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Database (usually already configured)
PGHOST=localhost
PGPORT=5432
PGDATABASE=grantradar
PGUSER=grantradar
PGPASSWORD=your_password

# Backup settings
BACKUP_DIR=./backups
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY=your_strong_passphrase  # Optional

# S3 settings (optional)
S3_BACKUP_BUCKET=your-bucket-name
S3_BACKUP_PREFIX=grantradar/backups
S3_STORAGE_CLASS=STANDARD_IA
S3_LIFECYCLE_DAYS=90
S3_GLACIER_DAYS=365
AWS_PROFILE=default
AWS_REGION=us-east-1

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
NOTIFICATION_EMAIL=admin@example.com
HEALTHCHECK_URL=https://hc-ping.com/your-uuid

# Logging
LOG_DIR=./logs
```

## Automated Backups

### Cron Setup

Add to crontab (`crontab -e`):

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/grantradar/scripts/backup/backup-cron.sh --upload-s3

# Weekly encrypted backup on Sundays at 3 AM
0 3 * * 0 /path/to/grantradar/scripts/backup/backup-cron.sh --upload-s3 --encrypt
```

### Docker-based Scheduling

Use the backup service in docker-compose.yml:

```bash
# Run backup via Docker
docker-compose run --rm backup
```

### Systemd Timer (Alternative)

Create `/etc/systemd/system/grantradar-backup.timer`:

```ini
[Unit]
Description=GrandRadar Daily Backup

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## S3 Storage

### Initial Setup

1. Create an S3 bucket:
```bash
aws s3 mb s3://your-backup-bucket --region us-east-1
```

2. Configure environment variables in `.env`:
```bash
S3_BACKUP_BUCKET=your-backup-bucket
S3_BACKUP_PREFIX=grantradar/backups
```

3. Set up lifecycle rules:
```bash
./scripts/backup/s3-upload.sh setup-lifecycle
```

### Lifecycle Policy

Default lifecycle (configurable):
- **0-90 days**: Standard-IA storage
- **90+ days**: Glacier Deep Archive
- **365+ days**: Automatic deletion

### IAM Policy

Minimum required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-backup-bucket",
                "arn:aws:s3:::your-backup-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutLifecycleConfiguration",
                "s3:GetLifecycleConfiguration"
            ],
            "Resource": "arn:aws:s3:::your-backup-bucket"
        }
    ]
}
```

## Recovery Testing

Regular recovery testing is essential. Follow this checklist monthly:

### Recovery Test Procedure

1. **Create a test environment**
   ```bash
   # Create a test database
   docker-compose exec postgres createdb -U grantradar grantradar_test
   ```

2. **Restore to test database**
   ```bash
   # Modify restore to use test database
   PGDATABASE=grantradar_test ./scripts/backup/restore.sh --force backups/latest.sql.gz
   ```

3. **Verify data integrity**
   ```bash
   # Connect and run verification queries
   docker-compose exec postgres psql -U grantradar -d grantradar_test

   -- Check table counts
   SELECT schemaname, tablename, n_live_tup
   FROM pg_stat_user_tables
   ORDER BY n_live_tup DESC;

   -- Verify critical tables
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM grants;
   SELECT COUNT(*) FROM organizations;
   ```

4. **Document results**
   - Record backup file used
   - Record restore duration
   - Note any issues encountered

5. **Cleanup**
   ```bash
   docker-compose exec postgres dropdb -U grantradar grantradar_test
   ```

### Recovery Test Checklist

- [ ] Backup file is accessible
- [ ] Backup file is not corrupted (gzip test passes)
- [ ] Restore completes without errors
- [ ] All tables are present
- [ ] Row counts match expectations
- [ ] Application can connect to restored database
- [ ] Critical queries execute successfully

## Backup Schedule Recommendations

| Environment | Frequency | Retention | S3 Storage | Encryption |
|------------|-----------|-----------|------------|------------|
| Development | Weekly | 7 days | Optional | No |
| Staging | Daily | 14 days | Recommended | Optional |
| Production | Every 6 hours | 30 days local, 365 days S3 | Required | Required |

### Production Schedule

```bash
# Crontab for production
# Every 6 hours
0 */6 * * * /path/to/backup-cron.sh --upload-s3 --encrypt

# Full weekly backup on Sundays (keep longer)
0 1 * * 0 /path/to/backup.sh --upload-s3 --encrypt && \
    aws s3 cp backups/latest.sql.gz.gpg s3://bucket/weekly/$(date +\%Y\%m\%d).sql.gz.gpg
```

## Troubleshooting

### Common Issues

**1. Backup fails with "connection refused"**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Verify connection details
docker-compose exec postgres pg_isready -U grantradar
```

**2. S3 upload fails**
```bash
# Check AWS credentials
aws sts get-caller-identity --profile default

# Verify bucket access
aws s3 ls s3://your-bucket/ --profile default
```

**3. Restore fails with "permission denied"**
```bash
# Check database user permissions
docker-compose exec postgres psql -U grantradar -c "\du"

# Grant necessary permissions
docker-compose exec postgres psql -U grantradar -c "GRANT ALL ON DATABASE grantradar TO grantradar;"
```

**4. Encrypted backup decryption fails**
```bash
# Verify encryption key is set
echo $BACKUP_ENCRYPTION_KEY

# Test decryption manually
gpg --decrypt backup.sql.gz.gpg > backup.sql.gz
```

### Log Locations

- Backup logs: `./logs/backup.log`
- Docker logs: `docker-compose logs postgres`
- Cron logs: `/var/log/cron` or `/var/log/syslog`

### Emergency Recovery

In case of complete data loss:

1. **Identify latest backup**
   ```bash
   ./scripts/backup/restore.sh --list-s3
   ```

2. **Download and decrypt**
   ```bash
   ./scripts/backup/s3-upload.sh download grantradar_backup_YYYYMMDD_HHMMSS.sql.gz.gpg
   ```

3. **Restore to fresh database**
   ```bash
   docker-compose up -d postgres
   ./scripts/backup/restore.sh --force backups/grantradar_backup_YYYYMMDD_HHMMSS.sql.gz.gpg
   ```

4. **Verify application functionality**
   ```bash
   docker-compose up -d
   curl http://localhost:8000/health
   ```

## Security Considerations

1. **Encryption**: Always encrypt backups containing sensitive data
2. **Access Control**: Limit access to backup files and encryption keys
3. **Key Management**: Store encryption keys separately from backups
4. **Audit Logging**: Enable CloudTrail for S3 bucket access logging
5. **Network Security**: Use VPC endpoints for S3 access in production

## Monitoring

### Recommended Alerts

1. **Backup failure**: Alert on non-zero exit code
2. **Backup age**: Alert if no backup in last 24 hours
3. **Backup size anomaly**: Alert on significant size changes (>50%)
4. **S3 upload failure**: Alert on upload errors

### Health Check Integration

Use services like healthchecks.io:

```bash
HEALTHCHECK_URL=https://hc-ping.com/your-uuid
```

The backup script will ping:
- `/start` when backup begins
- Base URL on success
- `/fail` on failure
