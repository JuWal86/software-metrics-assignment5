#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-textual}"

# Collect metrics
measure run --project "$PROJECT"

# Dashboard screenshots assume streamlit is already running.
# If you want to run streamlit automatically, do it in a separate service.
python3.11 scripts/screenshot_dashboard.py --name "$(date +%Y-%m-%d)"
