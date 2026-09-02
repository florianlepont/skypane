#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SKYPANE_COMPANION_PASSWORD="local-verify-only"
exec server/.venv/bin/python3 companion/app.py --state-dir /tmp/skypane-prod-state
