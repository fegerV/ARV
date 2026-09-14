#!/usr/bin/env bash
#
# Weekly integrity verification (Sunday 05:00).
#
# Two independent checks per backup:
#   1. SHA-256 of the retrieved artifact against the recorded checksum — proves
#      the bytes survived storage.
#   2. `pg_restore --list` against the decompressed archive — proves it is a
#      readable custom-format dump, which the checksum alone cannot tell you.
#
# A byte-perfect but truncated or format-incompatible archive is a real failure
# mode, and it is invisible until the day you actually need to restore.
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

log "verifying the ${LIMIT} most recent backup(s)"

set +e
run_backup_cli verify --limit "${LIMIT}"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "verification passed"
    exit 0
fi

log "verification FAILED (exit ${status})"
exit "${status}"
