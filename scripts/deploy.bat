@echo off
REM Production Deployment Script for Outer Skies (Windows)
REM This script handles the complete production deployment process

setlocal enabledelayedexpansion

REM Configuration
set DEPLOYMENT_ID=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set DEPLOYMENT_ID=%DEPLOYMENT_ID: =0%
set LOG_FILE=logs\deployment_%DEPLOYMENT_ID%.log
set BACKUP_BEFORE_DEPLOY=true
set HEALTH_CHECK_TIMEOUT=300
set ROLLBACK_ON_FAILURE=true

REM Create log directory
if not exist "logs" mkdir logs

REM Logging function
:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
goto :eof

REM Error function
:error
echo [%date% %time%] ERROR: %~1
echo [%date% %time%] ERROR: %~1 >> "%LOG_FILE%"
goto :eof

REM Warning function
:warning
echo [%date% %time%] WARNING: %~1
echo [%date% %time%] WARNING: %~1 >> "%LOG_FILE%"
goto :eof

REM Check if Docker is running
:check_docker
call :log "Checking Docker status..."
docker info >nul 2>&1
if errorlevel 1 (
    call :error "Docker is not running or not accessible"
    exit /b 1
)
call :log "Docker is running"
goto :eof

REM Check environment variables
:check_environment
call :log "Checking environment variables..."
set required_vars=SECRET_KEY DATABASE_URL REDIS_URL OPENROUTER_API_KEY STRIPE_SECRET_KEY STRIPE_PUBLISHABLE_KEY
for %%v in (%required_vars%) do (
    if "!%%v!"=="" (
        call :error "Missing required environment variable: %%v"
        exit /b 1
    )
)
call :log "All required environment variables are set"
goto :eof

REM Create backup before deployment
:create_backup
if "%BACKUP_BEFORE_DEPLOY%"=="true" (
    call :log "Creating backup before deployment..."
    if exist "scripts\backup.sh" (
        bash scripts\backup.sh
        call :log "Backup completed successfully"
    ) else (
        call :warning "Backup script not found, skipping backup"
    )
)
goto :eof

REM Pull latest code
:pull_latest_code
call :log "Pulling latest code from repository..."
git pull origin main
call :log "Code updated to latest version"
goto :eof

REM Build Docker images
:build_images
call :log "Building Docker images..."
docker-compose -f docker-compose.prod.yml build --no-cache web
docker-compose -f docker-compose.prod.yml build --no-cache celery
docker-compose -f docker-compose.prod.yml build --no-cache celery-beat
docker-compose -f docker-compose.prod.yml build --no-cache backup
call :log "Docker images built successfully"
goto :eof

REM Run database migrations
:run_migrations
call :log "Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
call :log "Database migrations completed"
goto :eof

REM Collect static files
:collect_static
call :log "Collecting static files..."
docker-compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
call :log "Static files collected"
goto :eof

REM Deploy services
:deploy_services
call :log "Deploying services..."
call :log "Stopping existing services..."
docker-compose -f docker-compose.prod.yml down --remove-orphans
call :log "Starting services..."
docker-compose -f docker-compose.prod.yml up -d
call :log "Restarting services for configuration changes..."
docker-compose -f docker-compose.prod.yml restart web nginx
call :log "Services deployed successfully"
goto :eof

REM Wait for services to be ready
:wait_for_services
call :log "Waiting for services to be ready..."
call :log "Waiting for database..."
timeout /t 60 /nobreak >nul
call :log "Waiting for Redis..."
timeout /t 30 /nobreak >nul
call :log "Waiting for web service..."
timeout /t 60 /nobreak >nul
call :log "All services are ready"
goto :eof

REM Run health checks
:run_health_checks
call :log "Running comprehensive health checks..."
curl -f http://localhost/health/ >nul 2>&1
if errorlevel 1 (
    call :error "Basic health check failed"
    exit /b 1
)
call :log "Basic health check passed"

curl -f http://localhost/api/v1/system/health/ >nul 2>&1
if errorlevel 1 (
    call :error "API health check failed"
    exit /b 1
)
call :log "API health check passed"

docker-compose -f docker-compose.prod.yml exec -T web python manage.py check --database default >nul 2>&1
if errorlevel 1 (
    call :error "Database connectivity check failed"
    exit /b 1
)
call :log "Database connectivity check passed"

call :log "All health checks passed"
goto :eof

REM Rollback deployment
:rollback
if "%ROLLBACK_ON_FAILURE%"=="true" (
    call :error "Deployment failed, initiating rollback..."
    docker-compose -f docker-compose.prod.yml down
    if exist "docker-compose.prod.yml.backup" (
        call :log "Restoring previous configuration..."
        copy docker-compose.prod.yml.backup docker-compose.prod.yml
        docker-compose -f docker-compose.prod.yml up -d
    )
    call :error "Rollback completed"
)
goto :eof

REM Send notification
:send_notification
set status=%~1
set message=%~2
call :log "Sending deployment notification: %status%"
echo Deployment %status%: %message% >> "%LOG_FILE%"
goto :eof

REM Cleanup
:cleanup
call :log "Cleaning up deployment artifacts..."
docker image prune -f
docker container prune -f
call :log "Cleanup completed"
goto :eof

REM Main deployment function
:main
call :log "Starting Outer Skies production deployment (ID: %DEPLOYMENT_ID%)"

REM Start deployment
call check_docker
if errorlevel 1 exit /b 1

call check_environment
if errorlevel 1 exit /b 1

call create_backup
call pull_latest_code
call build_images
call run_migrations
call collect_static
call deploy_services
call wait_for_services

REM Run health checks with timeout
set /a attempts=0
:health_check_loop
call run_health_checks
if not errorlevel 1 (
    call :log "Deployment completed successfully!"
    call send_notification "SUCCESS" "Deployment %DEPLOYMENT_ID% completed successfully"
    call cleanup
    goto :end
)
set /a attempts+=1
if %attempts% geq 30 (
    call :error "Health checks failed after %HEALTH_CHECK_TIMEOUT% seconds"
    call rollback
    call send_notification "FAILED" "Deployment %DEPLOYMENT_ID% failed - health checks did not pass"
    exit /b 1
)
timeout /t 10 /nobreak >nul
goto health_check_loop

:end
call :log "Deployment log saved to: %LOG_FILE%"
goto :eof

REM Handle script interruption
:interrupt
call :error "Deployment interrupted"
call rollback
exit /b 1

REM Run main function
call main 