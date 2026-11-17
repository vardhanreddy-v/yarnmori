#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Install Python 3.12 or newer, then reopen this launcher.'
  read -r -p 'Press Enter to close.'
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12 or newer is required"'
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r requirements.txt
if [ ! -f .env ]; then python setup.py; fi
echo 'Open http://127.0.0.1:8000 in your browser. Keep this window open.'
python -m uvicorn app:app --host 127.0.0.1 --port 8000
