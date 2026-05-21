#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/../.venv/bin/activate" ]; then
  source "$SCRIPT_DIR/../.venv/bin/activate"
fi
cd "$SCRIPT_DIR"
python chat.py "$@"
