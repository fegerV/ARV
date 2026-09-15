#!/usr/bin/env bash
#
# Nightly media backup (03:30) — restic snapshot of the uploaded originals.
#
# Media originals are the largest and least recoverable dataset: a lost upload
# cannot be re-created by the customer. restic ships only changed chunks, so the
# nightly run stays cheap after the first full snapshot.
#
# Runs 30 minutes after the database job on purpose: the two compete for disk
# I/O and for the uplink to the object storage.
#
# Exit codes: 0 ok, 1 backup failed, 2 not configured, 78 configuration error.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

acquire_lock "media"
prepare_stage

log "starting media backup"

set +e
run_backup_cli media "$@"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "media backup finished"
    exit 0
fi

if [[ "${status}" -eq 2 ]]; then
    log "media backup is not configured; nothing to do"
    exit 2
fi

log "media backup FAILED (exit ${status})"
exit "${status}"
