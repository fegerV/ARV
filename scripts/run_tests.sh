#!/usr/bin/env bash
# Single entry point for the ARV test suite, on a laptop or on the server.
#
# Sources .env.test on purpose. `app.core.config.settings` reads `.env`, so
# without this the suite inherits the *deployment's* configuration and the
# result depends on how prod happens to be set up — switching on dump
# encryption was enough to break an assertion about the uploaded artifact's
# suffix, and a red suite then hides real regressions.
#
# Usage:
#   bash scripts/run_tests.sh -q
#   bash scripts/run_tests.sh tests/test_backup_cli.py -q --no-cov
#
# Override the interpreter with ARV_PYTHON=/path/to/python.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Prefer an explicit interpreter, then the project venv that sits next to the
# app on the server (/opt/arv/app + /opt/arv/venv), then the managed developer
# runtime, then whatever is on PATH.
if [[ -n "${ARV_PYTHON:-}" ]]; then
  PYTHON_BIN="${ARV_PYTHON}"
elif [[ -x "${REPO_ROOT}/../venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/../venv/bin/python"
elif [[ -x "${HOME}/.workbuddy-ai/binaries/python/envs/arv2/Scripts/python.exe" ]]; then
  PYTHON_BIN="${HOME}/.workbuddy-ai/binaries/python/envs/arv2/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  PYTHON_BIN="$(command -v python)"
fi

if [[ ! -f .env.test ]]; then
  echo "run_tests.sh: .env.test is missing; the suite would inherit the live .env" >&2
  exit 78   # EX_CONFIG
fi

set -a
# shellcheck disable=SC1091
. ./.env.test
set +a

echo "run_tests.sh: $(basename "${PYTHON_BIN}") + .env.test" >&2
exec "${PYTHON_BIN}" -m pytest "$@"
