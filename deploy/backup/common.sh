#!/usr/bin/env bash
#
# Shared environment for the ARV backup scripts.
#
# Sourced, never executed. Keeps the individual scripts to the parts bash is
# actually good at: locking, permissions, exit codes. All backup logic lives in
# `python -m app.cli.backup` so it is covered by the test suite.
#
set -euo pipefail

APP_DIR="${ARV_APP_DIR:-/opt/arv/app}"
VENV_DIR="${ARV_VENV_DIR:-/opt/arv/venv}"
PYTHON="${VENV_DIR}/bin/python"
STAGE_DIR="${ARV_BACKUP_STAGE:-/var/backups/arv}"
LOCK_DIR="${ARV_BACKUP_LOCK_DIR:-/var/lock}"
LOG_TAG="arv-backup"

if [[ ! -x "${PYTHON}" ]]; then
    echo "${LOG_TAG}: interpreter not found at ${PYTHON}" >&2
    exit 78   # EX_CONFIG
fi

log() {
    printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${LOG_TAG}" "$*"
}

# Serialise runs of the same job. `flock` on a dedicated file descriptor is the
# only variant that survives the process being killed mid-run.
acquire_lock() {
    local name="$1"
    mkdir -p "${LOCK_DIR}"
    exec 9>"${LOCK_DIR}/arv-${name}.lock"
    if ! flock -n 9; then
        log "another '${name}' job is already running; skipping this trigger"
        exit 0
    fi
}

# Run a CLI subcommand from the application directory with its virtualenv.
run_backup_cli() {
    cd "${APP_DIR}"
    "${PYTHON}" -m app.cli.backup "$@"
}

# The staging directory holds plaintext (or at least pre-upload) artifacts and
# the age identity during a restore. Only the backup user may read it.
prepare_stage() {
    mkdir -p "${STAGE_DIR}"
    chmod 0700 "${STAGE_DIR}"
}
