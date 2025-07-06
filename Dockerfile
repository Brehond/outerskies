# Multi-stage build for Outer Skies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=astrology_ai.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    postgresql-client \
    redis-tools \
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy manage.py first for better caching
COPY manage.py .

# Copy project structure
COPY outer_skies/ ./outer_skies/
COPY chart/ ./chart/
COPY plugins/ ./plugins/
COPY api/ ./api/
COPY payments/ ./payments/
COPY monitoring/ ./monitoring/
COPY ai_integration/ ./ai_integration/

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/backups

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy backup script
COPY scripts/backup.sh /app/scripts/backup.sh
RUN chmod +x /app/scripts/backup.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Development stage
FROM base as development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production
# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"] 