#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN=python3
VENV="$ROOT/.venv"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$VENV/bin/python" -m py_compile "$ROOT/src/oc_node.py" "$ROOT/src/oc_protocol.py"
echo "Dependencies installed in: $VENV"
echo "No host network interfaces, firewall rules, firmware or system services were changed."
