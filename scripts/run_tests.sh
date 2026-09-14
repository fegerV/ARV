#!/usr/bin/env bash
# Local test runner for the ARV project.
#
# Loads environment from .env.test (never commit real credentials there) and
# runs pytest with the isolated interpreter, so tests do not need inline
# secrets on the command line.
#
# Usage:
#   bash scripts/run_tests.sh tests/test_csrf_exemptions.py -q
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="${ARV_PYTHON:-$HOME/.workbuddy-ai/binaries/python/envs/arv2/Scripts/python.exe}"

if [ -f .env.test ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env.test
  set +a
fi

exec "$PYTHON_BIN" -m pytest "$@"
