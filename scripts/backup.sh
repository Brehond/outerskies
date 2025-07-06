#!/bin/bash

# Database Backup Script for Outer Skies
# This script creates automated backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${DB_NAME:-outerskies}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Check if required environment variables are set
if [ -z "$DB_PASSWORD" ]; then
    error "DB_PASSWORD environment variable is not set"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Set PostgreSQL password environment variable
export PGPASSWORD="$DB_PASSWORD"

# Function to create backup
create_backup() {
    local backup_file="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
    
    log "Starting database backup..."
    log "Database: $DB_NAME"
    log "Host: $DB_HOST:$DB_PORT"
    log "User: $DB_USER"
    
    # Create backup using pg_dump
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --create --if-exists > "$backup_file"; then
        
        log "Database backup completed successfully: $backup_file"
        
        # Get backup file size
        backup_size=$(du -h "$backup_file" | cut -f1)
        log "Backup size: $backup_size"
        
        # Compress backup
        log "Compressing backup..."
        gzip "$backup_file"
        compressed_file="$backup_file.gz"
        
        # Get compressed file size
        compressed_size=$(du -h "$compressed_file" | cut -f1)
        log "Compressed size: $compressed_size"
        
        echo "$compressed_file"
    else
        error "Database backup failed"
        exit 1
    fi
}

# Function to sync backups to remote location
sync_backups() {
    if [ -n "$BACKUP_REMOTE_HOST" ] && command -v rsync &> /dev/null; then
        log "Syncing backups to remote location..."
        rsync -avz --delete "$BACKUP_DIR/" "$BACKUP_REMOTE_HOST:$BACKUP_REMOTE_PATH/"
        log "Backup sync completed"
    fi
}

# Function to upload to S3 (if configured)
upload_to_s3() {
    local backup_file="$1"
    
    if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
        log "Uploading backup to S3: $S3_BUCKET"
        
        if aws s3 cp "$backup_file" "s3://$S3_BUCKET/$(basename "$backup_file")"; then
            log "S3 upload completed successfully"
        else
            warning "S3 upload failed"
        fi
    else
        if [ -z "$S3_BUCKET" ]; then
            log "S3 bucket not configured, skipping upload"
        else
            warning "AWS CLI not available, skipping S3 upload"
        fi
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Remove old local backups
    find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    
    # Remove old S3 backups (if configured)
    if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
        log "Cleaning up old S3 backups..."
        aws s3 ls "s3://$S3_BUCKET/" | grep "db_backup_" | while read -r line; do
            createDate=$(echo "$line" | awk {'print $1'})
            createDate=$(date -d "$createDate" +%s)
            olderThan=$(date -d "-$RETENTION_DAYS days" +%s)
            if [[ $createDate -lt $olderThan ]]; then
                fileName=$(echo "$line" | awk {'print $4'})
                if [[ $fileName != "" ]]; then
                    log "Deleting old S3 backup: $fileName"
                    aws s3 rm "s3://$S3_BUCKET/$fileName"
                fi
            fi
        done
    fi
    
    log "Cleanup completed"
}

# Function to verify backup
verify_backup() {
    local backup_file="$1"
    
    log "Verifying backup integrity..."
    
    # Test if the backup file can be read and contains data
    if gunzip -t "$backup_file"; then
        log "Backup file is valid and not corrupted"
        
        # Check if backup contains expected content
        if gunzip -c "$backup_file" | head -n 10 | grep -q "PostgreSQL database dump"; then
            log "Backup contains valid PostgreSQL dump"
            return 0
        else
            error "Backup does not contain valid PostgreSQL dump"
            return 1
        fi
    else
        error "Backup file is corrupted"
        return 1
    fi
}

# Function to create backup summary
create_summary() {
    local backup_file="$1"
    
    log "Creating backup summary..."
    
    summary_file="$BACKUP_DIR/backup_summary_$TIMESTAMP.txt"
    {
        echo "Outer Skies Database Backup Summary"
        echo "=================================="
        echo "Date: $(date)"
        echo "Database: $DB_NAME"
        echo "Host: $DB_HOST:$DB_PORT"
        echo "Backup file: $(basename "$backup_file")"
        echo "Backup size: $(du -h "$backup_file" | cut -f1)"
        echo "Retention: $RETENTION_DAYS days"
        echo "S3 bucket: ${S3_BUCKET:-Not configured}"
        echo ""
        echo "Backup completed successfully!"
    } > "$summary_file"
    
    log "Backup summary created: $summary_file"
}

# Main execution
main() {
    log "Starting Outer Skies database backup process..."
    
    # Check database connectivity
    log "Testing database connectivity..."
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
        log "Database is ready"
    else
        error "Cannot connect to database"
        exit 1
    fi
    
    # Create backup
    backup_file=$(create_backup)
    
    # Verify backup
    if verify_backup "$backup_file"; then
        log "Backup verification passed"
    else
        error "Backup verification failed"
        exit 1
    fi
    
    # Upload to S3
    upload_to_s3 "$backup_file"
    
    # Sync to remote location
    sync_backups
    
    # Clean up old backups
    cleanup_old_backups
    
    # Create summary
    create_summary "$backup_file"
    
    log "Backup process completed successfully!"
    
    # List recent backups
    log "Recent backups:"
    ls -lh "$BACKUP_DIR"/db_backup_*.sql.gz | tail -5
}

# Run main function
main "$@" 