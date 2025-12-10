#!/bin/sh

# Celery Worker Health Check Script
# POSIX-compliant fail-fast health check for Celery worker
# Checks if the worker is responsive via hostname-specific ping

# Set timeout for the celery ping command (in seconds)
TIMEOUT=5

# Get the current hostname to construct the worker destination
WORKER_NAME="celery@$(hostname)"

# Log the health check attempt with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S'): Checking Celery worker health for ${WORKER_NAME}..."

# Run celery inspect ping with timeout against hostname-specific worker
# Use --timeout flag for celery command and system timeout for fail-fast
if timeout "${TIMEOUT}" celery -A app.tasks.celery_app inspect ping --destination="${WORKER_NAME}" --timeout="${TIMEOUT}" >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): SUCCESS: Celery worker ${WORKER_NAME} is healthy and responsive"
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Celery worker ${WORKER_NAME} health check failed"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: Worker may be unresponsive, broker unreachable, or process dead"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): DEBUG: Check 'celery -A app.tasks.celery_app inspect active' and broker connectivity"
    exit 1
fi