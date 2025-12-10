#!/bin/sh

# Celery Beat Health Check Script
# This script checks if the Celery beat scheduler is running by checking for active schedules

# Set a timeout for the celery command (in seconds)
TIMEOUT=5

# Log the health check attempt
echo "$(date): Checking Celery beat health..."

# Check if celery beat is running by inspecting scheduled tasks
if timeout "${TIMEOUT}" celery -A app.tasks.celery_app inspect scheduled >/dev/null 2>&1; then
    echo "$(date): Celery beat is healthy"
    exit 0
else
    echo "$(date): ERROR: Celery beat health check failed"
    echo "$(date): This could indicate the scheduler is not running or the broker is unreachable"
    exit 1
fi