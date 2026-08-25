#!/usr/bin/env bash
# Ink Frame — repeatable code-push to an already-provisioned Hetzner VPS
# (run deploy/provision.sh once first). Run from the repository root on
# your laptop, not on the VPS.
#
# Usage:
#   deploy/deploy.sh <ssh-target>
#   deploy/deploy.sh root@203.0.113.10
#
# Rsyncs server/ and stub-server/ to the VPS, reinstalls pinned Python
# requirements only if requirements.txt changed, restarts the byos
# service, starts the poll timer (idempotent if already running), and
# prints the last few journald lines for both units so a bad deploy is
# visible immediately. Never touches deploy/inkframe.env - that file is
# created once, by hand, directly on the VPS (deploy/README.md), and lives
# outside the server/ and stub-server/ directories this script rsyncs.
set -euo pipefail

APP_ROOT="/opt/inkframe"
SSH_TARGET="${1:?usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh root@203.0.113.10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

echo "==> Syncing server/ to ${SSH_TARGET}:${APP_ROOT}/server/"
rsync -az --delete \
    --exclude '.venv' --exclude 'state' --exclude '__pycache__' \
    --exclude '*.pyc' --exclude 'inkframe.env' \
    "${REPO_ROOT}/server/" "${SSH_TARGET}:${APP_ROOT}/server/"

echo "==> Syncing stub-server/ to ${SSH_TARGET}:${APP_ROOT}/stub-server/"
rsync -az --delete \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'inkframe.env' \
    "${REPO_ROOT}/stub-server/" "${SSH_TARGET}:${APP_ROOT}/stub-server/"

echo "==> Checking whether requirements.txt changed"
LOCAL_HASH="$(sha256sum "${REPO_ROOT}/server/requirements.txt" | awk '{print $1}')"
REMOTE_HASH="$(ssh "${SSH_TARGET}" "cat ${APP_ROOT}/.requirements.sha256 2>/dev/null || true")"
if [ "${LOCAL_HASH}" != "${REMOTE_HASH}" ]; then
    echo "    requirements.txt changed - reinstalling into the venv"
    ssh "${SSH_TARGET}" "${APP_ROOT}/venv/bin/pip install --quiet -r ${APP_ROOT}/server/requirements.txt && echo '${LOCAL_HASH}' > ${APP_ROOT}/.requirements.sha256"
else
    echo "    requirements.txt unchanged - skipping pip install"
fi

echo "==> Fixing ownership after rsync (rsync runs as the SSH login user)"
ssh "${SSH_TARGET}" "chown -R inkframe:inkframe ${APP_ROOT}/server ${APP_ROOT}/stub-server"

echo "==> Restarting inkframe-byos.service and starting inkframe-poll.timer"
ssh "${SSH_TARGET}" "systemctl restart inkframe-byos.service && systemctl start inkframe-poll.timer"

echo "==> Recent journald output"
echo "--- inkframe-byos ---"
ssh "${SSH_TARGET}" "journalctl -u inkframe-byos --no-pager -n 10"
echo "--- inkframe-poll ---"
ssh "${SSH_TARGET}" "journalctl -u inkframe-poll --no-pager -n 10"

echo "==> Deploy complete."
