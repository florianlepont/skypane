#!/bin/bash
# SessionStart hook for Claude Code on the web (remote sessions only).
#
# Two jobs, both idempotent:
#   1. Provision server/.venv exactly as README.md / scripts/run-all-tests.sh
#      expect it (Pillow + requests, plus ruff + coverage for the CI-parity
#      lint and coverage gate), so `./scripts/run-all-tests.sh` and
#      `server/.venv/bin/ruff check .` work without any PYTHON= override.
#   2. Install the GSD (get-shit-done) workflow skills globally for Claude
#      Code — the `/gsd-*` entry points .claude/CLAUDE.md's "GSD Workflow
#      Enforcement" section requires. Remote containers are ephemeral, so
#      without this every web session starts without them. Pinned to the
#      same version the maintainer runs locally; bump deliberately.
#
# Local (non-web) sessions are left alone: the maintainer's own machine
# already carries both.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# --- 1. Python virtualenv for the test runner ---------------------------
if [ ! -x server/.venv/bin/python3 ]; then
  python3 -m venv server/.venv
fi
server/.venv/bin/pip install -q --disable-pip-version-check \
  -r server/requirements.txt -r server/requirements-dev.txt

# --- 2. GSD workflow skills -------------------------------------------
GSD_VERSION="1.42.3"
GSD_VERSION_FILE="$HOME/.claude/get-shit-done/VERSION"
if [ ! -f "$GSD_VERSION_FILE" ] || [ "$(cat "$GSD_VERSION_FILE" 2>/dev/null)" != "$GSD_VERSION" ]; then
  npx -y "get-shit-done-cc@${GSD_VERSION}" --claude --global >/dev/null 2>&1 \
    || echo "session-start: GSD install failed (non-fatal); /gsd-* skills unavailable this session" >&2
fi

echo "session-start: venv ready, GSD $(cat "$GSD_VERSION_FILE" 2>/dev/null || echo 'not installed')"
