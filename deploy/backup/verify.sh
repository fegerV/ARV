#!/usr/bin/env bash
#
# Weekly integrity verification (Sunday 05:00).
#
# Two independent checks per database backup:
#   1. SHA-256 of the retrieved artifact against the recorded checksum — proves
#      the bytes survived storage.
#   2. `pg_restore --list` against the decompressed archive — proves it is a
#      readable custom-format dump, which the checksum alone cannot tell you.
#
# A byte-perfect but truncated or format-incompatible archive is a real failure
# mode, and it is invisible until the day you actually need to restore.
#
# Media is verified separately, with `restic check --read-data-subset`: it is a
# different storage mechanism (a restic repository, not a single uploaded file),
# so `pg_restore` has nothing to say about it. Only re-reading and re-hashing
# pack files can detect a truncated upload or bit rot.
#
# When the database dump is encrypted and the age identity is not on this host
# (the normal state — see docs/RESTORE_RUNBOOK.md §10), step 2 is reported as
# `toc=skipped` rather than a failure. That is intentional: an alert that fires
# forever is an alert nobody reads.
#
# Exit codes: 0 all verified, 1 at least one check failed, 78 config error.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

acquire_lock "verify"
prepare_stage

# Verify more than just the newest artifact on the first Sunday of the month.
LIMIT=1
if [[ "$(date -u +%d)" == "01" ]]; then
    LIMIT=3
fi

log "verifying the ${LIMIT} most recent database backup(s)"
set +e
run_backup_cli verify --limit "${LIMIT}"
db_status=$?
set -e

log "checking the media repository"
set +e
run_backup_cli verify-media
media_status=$?
set -e

# 2 == "not configured on this host". Not a failure: a deployment without media
# backup has nothing to check.
if [[ "${media_status}" -eq 2 ]]; then
    log "media backup is not configured; skipping the repository check"
    media_status=0
fi

if [[ "${db_status}" -eq 0 && "${media_status}" -eq 0 ]]; then
    log "verification passed"
    exit 0
fi

log "verification FAILED (db=${db_status} media=${media_status})"
if [[ "${db_status}" -ne 0 ]]; then
    exit "${db_status}"
fi
exit "${media_status}"
