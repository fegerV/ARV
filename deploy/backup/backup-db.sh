#!/usr/bin/env bash
#
# Nightly PostgreSQL backup (03:00).
#
# Dumps the database, compresses and encrypts it, ships it to the primary and
# secondary off-site targets, applies the GFS rotation and pings the external
# dead-man's-switch. All of that is `app.cli.backup db`; this script only adds
# locking and staging-directory hygiene.
#
# Exit codes: 0 ok, 1 backup failed, 2 not configured, 78 configuration error.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

acquire_lock "db"
prepare_stage

log "starting database backup"

set +e
run_backup_cli db "$@"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "database backup finished"
    exit 0
fi

log "database backup FAILED (exit ${status})"
exit "${status}"
