#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Placeholder Auth0 settings so the companion starts; signing in itself
# needs a real tenant.
export SKYPANE_AUTH0_DOMAIN="local-verify.example.test"
export SKYPANE_AUTH0_CLIENT_ID="local-verify-only"
export SKYPANE_AUTH0_CLIENT_SECRET="local-verify-only"
export SKYPANE_COMPANION_PUBLIC_URL="https://local-verify.example.test"
exec server/.venv/bin/python3 companion/app.py --state-dir /tmp/skypane-prod-state
