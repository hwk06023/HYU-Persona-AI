#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

echo ""
echo "Setup complete. Activate the venv with:"
echo "  source .venv/bin/activate"
echo ""
echo "Then check that .env contains: OPENAI_API_KEY=..."
