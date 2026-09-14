#!/usr/bin/env bash
#
# Operator-initiated restore (disaster recovery).
#
# THIS SCRIPT IS THE DANGEROUS ONE. It is interactive by design: the runbook
# (docs/BACKUP_AND_RECOVERY.md §10.1) requires the incident to be declared, the
# application to be stopped, and the current (possibly damaged) state to be
# preserved before anything is overwritten. A restore fired off in a panic is
# how a recoverable incident becomes an unrecoverable one.
#
# Usage:
#   restore.sh --backup-id 42 --target-db vertex_ar_recovered
#   restore.sh --list
#
# The target database must NOT be the live one; the service refuses that case
# regardless, but the check is repeated here so the operator sees it early.
#
# Exit codes: 0 ok, 1 restore failed, 2 usage error, 3 refused by operator.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

BACKUP_ID=""
TARGET_DB=""
ASSUME_YES=0
LIST_ONLY=0

usage() {
    sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup-id) BACKUP_ID="${2:-}"; shift 2 ;;
        --target-db) TARGET_DB="${2:-}"; shift 2 ;;
        --list)      LIST_ONLY=1; shift ;;
        --yes|-y)    ASSUME_YES=1; shift ;;
        -h|--help)   usage ;;
        *) echo "unknown argument: $1" >&2; usage ;;
    esac
done

prepare_stage

if [[ "${LIST_ONLY}" -eq 1 ]]; then
    run_backup_cli status
    exit $?
fi

if [[ -z "${BACKUP_ID}" || -z "${TARGET_DB}" ]]; then
    echo "--backup-id and --target-db are both required" >&2
    usage
fi

# The encryption identity is not kept on the production host. If the backup is
# encrypted and the key has not been mounted, stop before touching anything.
if [[ ! -r "${ARV_AGE_IDENTITY_FILE:-/etc/arv/backup-age.key}" ]]; then
    log "WARNING: age identity not readable at ${ARV_AGE_IDENTITY_FILE:-/etc/arv/backup-age.key}"
    log "         an encrypted backup cannot be restored without it"
fi

if systemctl is-active --quiet arv.service; then
    log "WARNING: arv.service is still running."
    log "         Restoring while the application writes will interleave new"
    log "         rows with the restored data. Stop it first:"
    log "           systemctl stop arv.service"
    if [[ "${ASSUME_YES}" -ne 1 ]]; then
        echo
        read -r -p "Continue anyway? [y/N] " reply
        [[ "${reply}" =~ ^[Yy]$ ]] || { log "aborted by operator"; exit 3; }
    fi
fi

if [[ "${ASSUME_YES}" -ne 1 ]]; then
    echo
    log "About to restore backup ${BACKUP_ID} into database '${TARGET_DB}'."
    read -r -p "Type the target database name to confirm: " confirmation
    if [[ "${confirmation}" != "${TARGET_DB}" ]]; then
        log "confirmation did not match; aborted"
        exit 3
    fi
fi

log "restoring backup ${BACKUP_ID} into ${TARGET_DB}"

set +e
run_backup_cli restore "${BACKUP_ID}" --target-db "${TARGET_DB}"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
    log "restore finished — run the post-restore checklist before returning traffic:"
    log "  docs/BACKUP_AND_RECOVERY.md §10.1 step 6"
    exit 0
fi

log "restore FAILED (exit ${status})"
exit "${status}"
