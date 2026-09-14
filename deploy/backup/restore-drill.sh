#!/usr/bin/env bash
#
# Monthly restore drill (1st of the month, 06:00).
#
# Restores the newest database backup into a throwaway database on the real
# cluster and counts the tables that came back. This is the only check that
# proves the backup is *usable* rather than merely present, and it is what the
# `arv_backup_restore_drill_last_timestamp_seconds` metric reports on.
#
# The throwaway database is dropped even if the restore fails, so a broken
# drill never leaves debris behind.
#
# Requires a role with CREATEDB; the connection comes from DATABASE_URL.
#
# Exit codes: 0 ok, 1 drill failed, 78 config error.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

acquire_lock "drill"
prepare_stage

log "starting restore drill"

set +e
run_backup_cli drill --backup-type "${ARV_DRILL_BACKUP_TYPE:-db}"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "restore drill succeeded"
    exit 0
fi

log "restore drill FAILED (exit ${status})"
exit "${status}"
