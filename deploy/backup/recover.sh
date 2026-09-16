#!/usr/bin/env bash
#
# One-command recovery: restore a backup, then optionally cut production over.
#
# This exists because the documented procedure had too many manual steps for
# the moment it is needed. The runbook required, by hand: createdb, mount the
# age key, restore, alembic, edit DATABASE_URL, restart, smoke, and remember
# the rollback. Every one of those was a chance to get it wrong while under
# pressure. Here they are one command, and the parts that are genuinely
# dangerous still stop and ask.
#
# Run as the DEPLOY user (aruser), not as arv:
#   * stopping/starting arv.service needs sudo, and only aruser has NOPASSWD;
#   * reading .env and running the CLI needs the arv user.
# The script crosses between the two with `sudo -n -u`.
#
# Usage:
#   recover.sh --backup-id 148 --target-db vertex_ar_recovered
#       Restore only. Creates the target database, leaves production alone.
#
#   recover.sh --from-file /path/backup_20260916_030000.sql.gz.age \
#              --target-db vertex_ar_recovered [--cutover]
#       Same, but restore an artifact that is already on this host instead of
#       downloading it. This is the ONLY form that works when the database is
#       gone: the normal path reads the Yandex Disk token from the database
#       itself, so it cannot be the way back from losing it. Use it with the
#       copy of the artifact you keep off the host.
#       The file must be readable by the 'arv' user.
#       Encryption is inferred from the .age suffix; pass --encrypted if the
#       file was renamed without it.
#
#   recover.sh --backup-id 148 --target-db vertex_ar_recovered --cutover
#       Restore and then cut production over to it, end to end.
#
#   recover.sh --cutover --target-db vertex_ar_recovered
#       Cut over to a database that was already restored.
#
# What --cutover does, in order:
#   1. snapshots the CURRENT database to the staging directory (so the state
#      before the recovery is not lost, even if it is the damaged one);
#   2. stops arv.service;
#   3. backs up .env and repoints DATABASE_URL;
#   4. starts arv.service and smoke-tests it;
#   5. prints the exact rollback command.
# If any step fails it stops there and tells you how to get back.
#
# Exit codes: 0 ok, 1 restore failed, 2 usage error, 3 refused by operator,
#             4 cutover failed, 77 environment not usable.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/backup/common.sh
source "${SCRIPT_DIR}/common.sh"

BACKUP_ID=""
FROM_FILE=""
FORCE_ENCRYPTED=0
TARGET_DB=""
CUTOVER=0
ASSUME_YES=0
DOMAIN="${ARV_DOMAIN:-ar.neuroimagen.ru}"
ENV_FILE="${APP_DIR}/.env"

usage() {
    # Print the header comment block. Derived from the file itself so it cannot
    # drift when the header changes — the previous fixed line range silently
    # printed code once the header grew.
    awk 'NR > 2 { if ($0 !~ /^#/) exit; sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup-id) BACKUP_ID="${2:-}"; shift 2 ;;
        --from-file) FROM_FILE="${2:-}"; shift 2 ;;
        --encrypted) FORCE_ENCRYPTED=1; shift ;;
        --target-db) TARGET_DB="${2:-}"; shift 2 ;;
        --cutover)   CUTOVER=1; shift ;;
        --domain)    DOMAIN="${2:-}"; shift 2 ;;
        --yes|-y)    ASSUME_YES=1; shift ;;
        -h|--help)   usage ;;
        *) echo "unknown argument: $1" >&2; usage ;;
    esac
done

if [[ -z "${TARGET_DB}" ]]; then
    echo "--target-db is required" >&2
    usage
fi
if [[ -n "${BACKUP_ID}" && -n "${FROM_FILE}" ]]; then
    echo "pass either --backup-id or --from-file, not both" >&2
    usage
fi
if [[ -z "${BACKUP_ID}" && -z "${FROM_FILE}" && "${CUTOVER}" -ne 1 ]]; then
    echo "nothing to do: pass --backup-id, --from-file, --cutover, or a combination" >&2
    usage
fi

if ! sudo -n true 2>/dev/null; then
    log "ERROR: passwordless sudo is required."
    log "       Run this as the deploy user (e.g. 'sudo -u aruser $0 ...'),"
    log "       because the 'arv' user has no sudo rights on this host."
    exit 77
fi

# --- helpers ---------------------------------------------------------------

# Run the backup CLI as the arv user with the application .env loaded. Running
# it as the caller would fail: .env is 0600 and owned by arv.
run_cli_as_arv() {
    sudo -n -u arv bash -c \
        "cd '${APP_DIR}' && set -a && . ./.env && set +a && '${PYTHON}' -m app.cli.backup \"\$@\"" \
        bash "$@"
}

# The live database name, read from the application's own DATABASE_URL so it
# cannot drift from what the app actually connects to.
live_db_name() {
    local raw
    raw="$(sudo -n -u arv bash -c \
        "set -a; . '${ENV_FILE}'; set +a; printf '%s' \"\${DATABASE_URL:-}\"")"
    raw="${raw%%\?*}"
    printf '%s' "${raw##*/}"
}

count_tables() {
    sudo -n -u postgres psql -d "$1" -tAc \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
        2>/dev/null | tr -d '[:space:]'
}

confirm() {
    [[ "${ASSUME_YES}" -eq 1 ]] && return 0
    local prompt="$1" expected="$2" reply
    echo
    read -r -p "${prompt}" reply
    if [[ "${reply}" != "${expected}" ]]; then
        log "confirmation did not match; aborted"
        exit 3
    fi
}

# --- preflight -------------------------------------------------------------

LIVE_DB="$(live_db_name)"
if [[ -z "${LIVE_DB}" ]]; then
    log "ERROR: could not read DATABASE_URL from ${ENV_FILE}"
    exit 77
fi

if [[ "${TARGET_DB}" == "${LIVE_DB}" ]]; then
    log "REFUSING: target database '${TARGET_DB}' is the live database."
    log "          Restore into a separate database and cut over deliberately."
    exit 3
fi

prepare_stage

log "live database: ${LIVE_DB}"
log "target database: ${TARGET_DB}"

if [[ ! -r "${ARV_AGE_IDENTITY_FILE:-/etc/arv/backup-age.key}" ]]; then
    log "note: no age identity at ${ARV_AGE_IDENTITY_FILE:-/etc/arv/backup-age.key}"
    log "      an encrypted backup cannot be opened without it"
fi

# --- 1. restore ------------------------------------------------------------

if [[ -n "${FROM_FILE}" ]]; then
    if [[ ! -f "${FROM_FILE}" ]]; then
        log "ERROR: no such artifact: ${FROM_FILE}"
        exit 77
    fi
    # The CLI runs as arv, so the operator's own copy is not automatically
    # readable by it. Check up front: discovering this after the confirmation
    # prompt would waste the operator's attention at the worst moment.
    if ! sudo -n -u arv test -r "${FROM_FILE}"; then
        log "ERROR: ${FROM_FILE} is not readable by the 'arv' user."
        log "       Copy it somewhere arv can read, e.g.:"
        log "         sudo -n install -o arv -g arv -m 0600 ${FROM_FILE} /var/backups/arv/"
        exit 77
    fi

    confirm "Restore artifact ${FROM_FILE} into '${TARGET_DB}'. Type the target name to confirm: " \
            "${TARGET_DB}"

    log "restoring ${FROM_FILE} into ${TARGET_DB} (no database needed)"
    set +e
    if [[ "${FORCE_ENCRYPTED}" -eq 1 ]]; then
        run_cli_as_arv restore --from-file "${FROM_FILE}" --encrypted \
            --target-db "${TARGET_DB}" --create-db
    else
        run_cli_as_arv restore --from-file "${FROM_FILE}" \
            --target-db "${TARGET_DB}" --create-db
    fi
    restore_status=$?
    set -e

    if [[ "${restore_status}" -ne 0 ]]; then
        log "restore FAILED (exit ${restore_status}); production was not touched"
        exit 1
    fi
fi

if [[ -n "${BACKUP_ID}" ]]; then
    confirm "Restore backup ${BACKUP_ID} into '${TARGET_DB}'. Type the target name to confirm: " \
            "${TARGET_DB}"

    log "restoring backup ${BACKUP_ID} into ${TARGET_DB}"
    set +e
    run_cli_as_arv restore "${BACKUP_ID}" --target-db "${TARGET_DB}" --create-db
    restore_status=$?
    set -e

    if [[ "${restore_status}" -ne 0 ]]; then
        log "restore FAILED (exit ${restore_status}); production was not touched"
        exit 1
    fi
fi

TABLES="$(count_tables "${TARGET_DB}")"
if [[ -z "${TABLES}" || "${TABLES}" -eq 0 ]]; then
    log "ERROR: '${TARGET_DB}' has no tables in schema 'public' — refusing to cut over to it"
    exit 4
fi
log "target '${TARGET_DB}' holds ${TABLES} tables"

if [[ "${CUTOVER}" -ne 1 ]]; then
    log "restore finished. Production is unchanged."
    log "run the post-restore checklist, then: $0 --cutover --target-db ${TARGET_DB}"
    exit 0
fi

# --- 2. cutover ------------------------------------------------------------

confirm "Cut production over to '${TARGET_DB}'? Type the target name to confirm: " "${TARGET_DB}"

# Snapshot before changing anything. Even a damaged database is worth keeping:
# it is the only copy of whatever happened after the backup was taken.
SNAPSHOT_TMP="$(mktemp -p /var/tmp arv-before-recover-XXXXXX.dump)"
SNAPSHOT="${STAGE_DIR}/before_recover_$(date -u +%Y%m%d_%H%M%S).dump"
log "snapshotting current '${LIVE_DB}' -> ${SNAPSHOT}"
if ! sudo -n -u postgres pg_dump -Fc -Z0 "${LIVE_DB}" > "${SNAPSHOT_TMP}"; then
    log "ERROR: could not snapshot the current database; aborting before any change"
    rm -f "${SNAPSHOT_TMP}"
    exit 4
fi
sudo -n -u arv bash -c "cat > '${SNAPSHOT}'" < "${SNAPSHOT_TMP}"
sudo -n -u arv chmod 0600 "${SNAPSHOT}"
rm -f "${SNAPSHOT_TMP}"
log "snapshot saved ($(stat -c %s "${SNAPSHOT}" 2>/dev/null || echo '?') bytes)"

ENV_BACKUP="${ENV_FILE}.bak-$(date -u +%Y%m%d_%H%M%S)"
sudo -n -u arv cp -p "${ENV_FILE}" "${ENV_BACKUP}"
log ".env backed up to ${ENV_BACKUP}"

log "stopping arv.service"
sudo -n systemctl stop arv.service

# Repoint DATABASE_URL in place. Only the path component is rewritten: the
# credentials, host and query string are left byte-for-byte alone, because
# reassembling the URL from parsed parts risks re-encoding the password.
set +e
sudo -n -u arv "${PYTHON}" - "${ENV_FILE}" "${TARGET_DB}" <<'PY'
import re
import sys

path, new_db = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    text = handle.read()

match = re.search(r"^(DATABASE_URL\s*=\s*)(.*)$", text, re.M)
if not match:
    sys.exit("DATABASE_URL not found in .env")

raw = match.group(2).strip()
quote = ""
if raw[:1] in ('"', "'") and raw[-1:] == raw[:1]:
    quote, raw = raw[0], raw[1:-1]

base, sep, query = raw.partition("?")
head, _, _old = base.rpartition("/")
if not head:
    sys.exit(f"cannot parse database name out of {raw!r}")

new_url = f"{head}/{new_db}{sep}{query}"
with open(path, "w", encoding="utf-8") as handle:
    handle.write(text[: match.start(2)] + quote + new_url + quote + text[match.end(2):])
print(f"DATABASE_URL -> {new_url}")
PY
rewrite_status=$?
set -e

if [[ "${rewrite_status}" -ne 0 ]]; then
    log "ERROR: could not rewrite DATABASE_URL; restoring .env and starting the service"
    sudo -n -u arv cp -p "${ENV_BACKUP}" "${ENV_FILE}"
    sudo -n systemctl start arv.service
    exit 4
fi

log "starting arv.service"
sudo -n systemctl start arv.service
sleep 6

if ! systemctl is-active --quiet arv.service; then
    log "ERROR: arv.service did not come up on '${TARGET_DB}'."
    log "       Rolling back to '${LIVE_DB}' automatically."
    sudo -n systemctl stop arv.service || true
    sudo -n -u arv cp -p "${ENV_BACKUP}" "${ENV_FILE}"
    sudo -n systemctl start arv.service
    sleep 5
    log "rollback done; service is $(systemctl is-active arv.service)"
    exit 4
fi

# --- 3. smoke --------------------------------------------------------------

smoke() {
    local path="$1" expected="$2" code
    code="$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: ${DOMAIN}" "https://127.0.0.1${path}" || true)"
    if [[ "${code}" == "${expected}" ]]; then
        log "  ok   ${path} -> ${code}"
        return 0
    fi
    log "  FAIL ${path} -> ${code} (expected ${expected})"
    return 1
}

log "smoke test against ${DOMAIN}"
smoke_ok=1
smoke "/" "200" || smoke_ok=0
smoke "/admin/login" "200" || smoke_ok=0

if [[ "${smoke_ok}" -ne 1 ]]; then
    log "WARNING: smoke test failed on '${TARGET_DB}'."
    log "         Roll back with:"
    log "           sudo -n systemctl stop arv.service"
    log "           sudo -n -u arv cp -p ${ENV_BACKUP} ${ENV_FILE}"
    log "           sudo -n systemctl start arv.service"
    exit 4
fi

log "cutover complete: production now serves '${TARGET_DB}'"

cat <<EOF

  Rollback (any time, the old database is untouched):
      sudo -n systemctl stop arv.service
      sudo -n -u arv cp -p ${ENV_BACKUP} ${ENV_FILE}
      sudo -n systemctl start arv.service

  Pre-recovery snapshot of '${LIVE_DB}':
      ${SNAPSHOT}

  Then, by hand, before declaring the incident closed:
    - sign in as super admin; companies and projects are listed
    - open one AR content: photo, video, marker.mind and QR code present
    - scan the QR code and play the video
    - open a company's storage settings: if the OAuth token is rejected, the
      .env does not match the data (see docs/RESTORE_RUNBOOK.md §8)

  Retire the old database only after a quiet day:
      sudo -n -u postgres psql -c 'ALTER DATABASE ${LIVE_DB} RENAME TO ${LIVE_DB}_pre_$(date -u +%Y%m%d)'
EOF

exit 0
