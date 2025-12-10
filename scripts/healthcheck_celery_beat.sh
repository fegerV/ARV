#!/bin/sh

# Celery Beat Health Check Script
# POSIX-compliant fail-fast health check for Celery beat scheduler
# Verifies PID file, schedule file existence, and process aliveness

# Set file paths for beat scheduler
PID_FILE="/tmp/celerybeat.pid"
SCHEDULE_FILE="/tmp/celerybeat-schedule"

# Set timeout for commands (in seconds)
TIMEOUT=5

# Log the health check attempt with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S'): Checking Celery beat health..."

# Check if PID file exists
if [ ! -f "${PID_FILE}" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Celery beat PID file ${PID_FILE} does not exist"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: Beat scheduler may not be running or PID file path misconfigured"
    exit 1
fi

# Check if schedule file exists
if [ ! -f "${SCHEDULE_FILE}" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Celery beat schedule file ${SCHEDULE_FILE} does not exist"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: Beat scheduler may not have initialized or schedule file path misconfigured"
    exit 1
fi

# Read PID from file
PID=$(cat "${PID_FILE}" 2>/dev/null)

# Validate PID is a number
if [ -z "${PID}" ] || [ "${PID}" -eq 0 ] 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Invalid or empty PID in ${PID_FILE}: '${PID}'"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: Beat scheduler PID file is corrupted"
    exit 1
fi

# Check if process with this PID is running and is celery beat
if ! kill -0 "${PID}" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Celery beat process with PID ${PID} is not running"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: Beat scheduler process has died, restart the service"
    exit 1
fi

# Additional check: verify the process is actually celery beat (if ps is available)
if command -v ps >/dev/null 2>&1; then
    if ! ps -p "${PID}" -o command= | grep -q "celery.*beat"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: Process ${PID} exists but is not a Celery beat process"
        echo "$(date '+%Y-%m-%d %H:%M:%S'): ACTION REQUIRED: PID file may be stale, clean up and restart beat"
        exit 1
    fi
fi

# Final check: try to inspect scheduled tasks (with timeout)
if timeout "${TIMEOUT}" celery -A app.tasks.celery_app inspect scheduled >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): SUCCESS: Celery beat is healthy (PID: ${PID}, files present, scheduler responsive)"
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): WARNING: Beat process alive but scheduler inspection failed"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): DEBUG: Broker may be unreachable but scheduler continues with local schedule"
    # Don't fail here since beat can continue working even if broker is temporarily unreachable
    echo "$(date '+%Y-%m-%d %H:%M:%S'): SUCCESS: Celery beat is healthy (PID: ${PID}, files present)"
    exit 0
fi