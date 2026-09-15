#!/usr/bin/env bash
#
# Secrets and configuration backup (class A3), weekly on Sunday at 04:00.
#
# This is not optional padding around the database dump. OAuth tokens for
# Yandex Disk are stored in the database encrypted with TOKEN_ENCRYPTION_KEY,
# and JWT sessions are signed with SECRET_KEY. A database restored without
# .env contains tokens nobody can decrypt, so every customer silently loses
# access to their storage — and the runbook restores this archive BEFORE the
# database for exactly that reason (docs/BACKUP_AND_RECOVERY.md §10.1 step 2).
#
# The archive is always encrypted with age before it leaves the host; the
# unencrypted tar is removed in the same run.
#
# Exit codes: 0 ok, 1 failed, 78 configuration error.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

acquire_lock "secrets"
prepare_stage

log "starting secrets backup"

set +e
run_backup_cli secrets --stage "${STAGE_DIR}"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "secrets backup finished"
    exit 0
fi

log "secrets backup FAILED (exit ${status})"
exit "${status}"
