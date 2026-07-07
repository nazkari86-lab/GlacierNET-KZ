#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
TF_CPP_MIN_LOG_LEVEL=3 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
