#!/usr/bin/env bash
set -eu

cd -- "$(dirname -- "$0")"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import flask" 2>/dev/null; then
  .venv/bin/python -m pip install -r requirements.txt
fi

supplier_pid=""

stop_supplier() {
  if [ -n "$supplier_pid" ]; then
    kill "$supplier_pid" 2>/dev/null || true
    wait "$supplier_pid" 2>/dev/null || true
  fi
}

trap stop_supplier EXIT INT TERM

.venv/bin/python supplier_service.py &
supplier_pid=$!

.venv/bin/python app.py
