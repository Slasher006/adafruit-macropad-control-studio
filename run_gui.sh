#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON=python3
fi
PYTHONPATH="$ROOT/desktop${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m macropad_configurator.app "$@"
