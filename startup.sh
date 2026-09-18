#!/usr/bin/env bash
set -euo pipefail
cd /home/site/wwwroot
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
exec python -m uvicorn server:app --host 0.0.0.0 --port 8000
