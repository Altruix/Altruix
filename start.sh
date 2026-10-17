#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3.10 or newer is required. Set PYTHON to the interpreter path if needed." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "Python 3.10 or newer is required." >&2
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m Main.core.apm_env_setup
exec .venv/bin/python -m Main
