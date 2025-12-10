#!/bin/sh

# Celery Worker Health Check Script
# This script checks if the Celery worker is responsive by sending a ping command

# Set a timeout for the celery ping command (in seconds)
TIMEOUT=5

# Get the current hostname to construct the worker destination
WORKER_NAME="celery@$(hostname)"

# Log the health check attempt
echo "$(date): Checking Celery worker health for ${WORKER_NAME}..."

# Run celery inspect ping with timeout and capture output
if timeout "${TIMEOUT}" celery -A app.tasks.celery_app inspect ping --destination="${WORKER_NAME}" >/dev/null 2>&1; then
    echo "$(date): Celery worker ${WORKER_NAME} is healthy"
    exit 0
else
    echo "$(date): ERROR: Celery worker ${WORKER_NAME} health check failed"
    echo "$(date): This could indicate the worker is not running, not responsive, or the broker is unreachable"
    exit 1
fi
