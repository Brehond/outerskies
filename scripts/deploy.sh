#!/bin/bash

# Production Deployment Script for Outer Skies
# This script handles the complete production deployment process

set -e

# Load environment variables
if [ -f .env.production ]; then
  source .env.production
  export $(grep -v '^#' .env.production | xargs)
fi

# Configuration
DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/app/logs/deployment_$DEPLOYMENT_ID.log"
BACKUP_BEFORE_DEPLOY=true
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
ROLLBACK_ON_FAILURE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

error() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}$message${NC}" >&2
    echo "$message" >> "$LOG_FILE"
}

warning() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

info() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1"
    echo -e "${BLUE}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running or not accessible"
        exit 1
    fi
    log "Docker is running"
}

# Function to check environment variables
check_environment() {
    log "Checking environment variables..."
    
    required_vars=(
        "SECRET_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "OPENROUTER_API_KEY"
        "STRIPE_SECRET_KEY"
        "STRIPE_PUBLISHABLE_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
    
    log "All required environment variables are set"
}

# Function to create backup before deployment
create_backup() {
    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        log "Creating backup before deployment..."
        if [ -f "/app/scripts/backup.sh" ]; then
            bash /app/scripts/backup.sh
            log "Backup completed successfully"
        else
            warning "Backup script not found, skipping backup"
        fi
    fi
}

# Function to pull latest code
pull_latest_code() {
    log "Pulling latest code from repository..."
    
    # Check if we're in a git repository
    if [ -d ".git" ]; then
        git pull origin main
        log "Code updated to latest version"
    else
        warning "Not in a git repository, skipping code update"
    fi
}

# Function to build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build the main application image
    docker-compose -f docker-compose.prod.yml build --no-cache web
    docker-compose -f docker-compose.prod.yml build --no-cache celery
    docker-compose -f docker-compose.prod.yml build --no-cache celery-beat
    docker-compose -f docker-compose.prod.yml build --no-cache backup
    
    log "Docker images built successfully"
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Run migrations in a temporary container
    docker-compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
    
    log "Database migrations completed"
}

# Function to collect static files
collect_static() {
    log "Collecting static files..."
    
    # Collect static files in a temporary container
    docker-compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
    
    log "Static files collected"
}

# Function to deploy services
deploy_services() {
    log "Deploying services..."
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans
    
    # Start services
    log "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Restart services if needed
    log "Restarting services for configuration changes..."
    docker-compose -f docker-compose.prod.yml restart web nginx
    
    log "Services deployed successfully"
}

# Function to wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for database
    log "Waiting for database..."
    timeout 60 bash -c 'until docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres; do sleep 2; done'
    
    # Wait for Redis
    log "Waiting for Redis..."
    timeout 30 bash -c 'until docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping; do sleep 2; done'
    
    # Wait for web service
    log "Waiting for web service..."
    timeout 60 bash -c 'until curl -f http://localhost/health/; do sleep 5; done'
    
    log "All services are ready"
}

# Function to run health checks
run_health_checks() {
    log "Running comprehensive health checks..."
    
    # Basic health check
    if curl -f http://localhost/health/ > /dev/null 2>&1; then
        log "Basic health check passed"
    else
        error "Basic health check failed"
        return 1
    fi
    
    # API health check
    if curl -f http://localhost/api/v1/system/health/ > /dev/null 2>&1; then
        log "API health check passed"
    else
        error "API health check failed"
        return 1
    fi
    
    # Database connectivity check
    if docker-compose -f docker-compose.prod.yml exec -T web python manage.py check --database default > /dev/null 2>&1; then
        log "Database connectivity check passed"
    else
        error "Database connectivity check failed"
        return 1
    fi
    
    # Celery worker check
    if docker-compose -f docker-compose.prod.yml exec -T celery celery -A astrology_ai inspect active > /dev/null 2>&1; then
        log "Celery worker check passed"
    else
        warning "Celery worker check failed (workers might still be starting)"
    fi
    
    log "All health checks passed"
    return 0
}

# Function to rollback deployment
rollback() {
    if [ "$ROLLBACK_ON_FAILURE" = true ]; then
        error "Deployment failed, initiating rollback..."
        
        # Stop all services
        docker-compose -f docker-compose.prod.yml down
        
        # Start previous version (if available)
        if [ -f "docker-compose.prod.yml.backup" ]; then
            log "Restoring previous configuration..."
            cp docker-compose.prod.yml.backup docker-compose.prod.yml
            docker-compose -f docker-compose.prod.yml up -d
        fi
        
        error "Rollback completed"
    fi
}

# Function to send notifications
send_notification() {
    local status="$1"
    local message="$2"
    
    log "Sending deployment notification: $status"
    
    # Add your notification logic here
    # Example: Slack webhook, email, etc.
    echo "Deployment $status: $message" >> "$LOG_FILE"
}

# Function to cleanup
cleanup() {
    log "Cleaning up deployment artifacts..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    log "Cleanup completed"
}

# Main deployment function
main() {
    log "Starting Outer Skies production deployment (ID: $DEPLOYMENT_ID)"
    
    # Create log directory
    mkdir -p /app/logs
    
    # Start deployment
    {
        check_docker
        check_environment
        create_backup
        pull_latest_code
        build_images
        run_migrations
        collect_static
        deploy_services
        wait_for_services
        
        # Run health checks with timeout
        if timeout $HEALTH_CHECK_TIMEOUT bash -c 'while ! run_health_checks; do sleep 10; done'; then
            log "Deployment completed successfully!"
            send_notification "SUCCESS" "Deployment $DEPLOYMENT_ID completed successfully"
            cleanup
        else
            error "Health checks failed after $HEALTH_CHECK_TIMEOUT seconds"
            rollback
            send_notification "FAILED" "Deployment $DEPLOYMENT_ID failed - health checks did not pass"
            exit 1
        fi
        
    } 2>&1 | tee -a "$LOG_FILE"
    
    log "Deployment log saved to: $LOG_FILE"
}

# Handle script interruption
trap 'error "Deployment interrupted"; rollback; exit 1' INT TERM

# Run main function
main "$@" 