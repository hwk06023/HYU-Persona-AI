#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# venv 만들기 (python3 → python 순서로 시도)
if [ ! -d ".venv" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
  else
    echo "Error: python3/python을 찾을 수 없습니다."
    exit 1
  fi
fi

source .venv/bin/activate

# pip 호출 — bare `pip` 실패 시 python -m pip, 그래도 안 되면 python3 -m pip 로 fallback
do_pip() {
  if pip "$@"; then
    return 0
  fi
  echo "[setup] 'pip' 실패. 'python -m pip' 로 재시도합니다."
  if python -m pip "$@"; then
    return 0
  fi
  echo "[setup] 'python -m pip' 실패. 'python3 -m pip' 로 재시도합니다."
  python3 -m pip "$@"
}

do_pip install -U pip
do_pip install -r requirements.txt

echo ""
echo "Setup complete. Activate the venv with:"
echo "  source .venv/bin/activate"
echo ""
echo "Then check that .env contains: OPENAI_API_KEY=..."
