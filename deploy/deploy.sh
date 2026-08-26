#!/usr/bin/env bash
# SkyPane — repeatable code-push to an already-provisioned VPS
# (run deploy/provision.sh once first). Run from the repository root on
# your laptop, not on the VPS.
#
# Usage:
#   deploy/deploy.sh <ssh-target>
#   deploy/deploy.sh root@203.0.113.10
#   deploy/deploy.sh ubuntu@203.0.113.10
#
# SSH_TARGET may log in directly as root, OR as any other user with
# passwordless sudo (e.g. Ubuntu cloud images, which disable direct root
# SSH by default but grant the default user NOPASSWD sudo). Every remote
# step that touches /opt/skypane (owned by the dedicated `skypane`
# service user, not the SSH login user) or manages systemd/journald runs
# through `sudo` so this works either way. `sudo` must be installed and
# passwordless for SSH_TARGET's login user on the remote host - a
# password prompt has no tty to answer over a non-interactive `ssh host
# "sudo ..."` call and will hang/fail.
#
# Rsyncs server/ and stub-server/ to the VPS, reinstalls pinned Python
# requirements only if requirements.txt changed, restarts the byos
# service, starts the poll timer (idempotent if already running), and
# prints the last few journald lines for both units so a bad deploy is
# visible immediately. Never touches deploy/skypane.env - that file is
# created once, by hand, directly on the VPS (deploy/README.md), and lives
# outside the server/ and stub-server/ directories this script rsyncs.
set -euo pipefail

APP_ROOT="/opt/skypane"
SSH_TARGET="${1:?usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh root@203.0.113.10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

echo "==> Syncing server/ to ${SSH_TARGET}:${APP_ROOT}/server/"
# --rsync-path runs the *remote* rsync as the skypane service user via
# sudo, so files land already owned by skypane:skypane regardless of
# whether SSH_TARGET logs in as root or as a sudo-capable non-root user -
# a plain rsync would otherwise try to write as the SSH login user into a
# directory tree owned by skypane and fail with permission denied.
rsync -az --delete --rsync-path="sudo -u skypane rsync" \
    --exclude '.venv' --exclude 'state' --exclude '__pycache__' \
    --exclude '*.pyc' --exclude 'skypane.env' \
    "${REPO_ROOT}/server/" "${SSH_TARGET}:${APP_ROOT}/server/"

echo "==> Syncing stub-server/ to ${SSH_TARGET}:${APP_ROOT}/stub-server/"
rsync -az --delete --rsync-path="sudo -u skypane rsync" \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'skypane.env' \
    "${REPO_ROOT}/stub-server/" "${SSH_TARGET}:${APP_ROOT}/stub-server/"

echo "==> Syncing adsb-test/runway3.json (production geofence config, not a test fixture -"
echo "    server/poll_loop.py's --geofence flag and detect.load_geofence() need this file"
echo "    at runtime for every poll cycle) to ${SSH_TARGET}:${APP_ROOT}/config/runway3.json"
rsync -az --rsync-path="sudo -u skypane rsync" \
    "${REPO_ROOT}/adsb-test/runway3.json" "${SSH_TARGET}:${APP_ROOT}/config/runway3.json"

echo "==> Checking whether requirements.txt changed"
LOCAL_HASH="$(sha256sum "${REPO_ROOT}/server/requirements.txt" | awk '{print $1}')"
REMOTE_HASH="$(ssh "${SSH_TARGET}" "sudo cat ${APP_ROOT}/.requirements.sha256 2>/dev/null || true")"
if [ "${LOCAL_HASH}" != "${REMOTE_HASH}" ]; then
    echo "    requirements.txt changed - reinstalling into the venv"
    ssh "${SSH_TARGET}" "sudo -u skypane ${APP_ROOT}/venv/bin/pip install --quiet -r ${APP_ROOT}/server/requirements.txt && echo '${LOCAL_HASH}' | sudo -u skypane tee ${APP_ROOT}/.requirements.sha256 >/dev/null"
else
    echo "    requirements.txt unchanged - skipping pip install"
fi

echo "==> Fixing ownership after rsync (defensive no-op - rsync above already writes as skypane via sudo)"
ssh "${SSH_TARGET}" "sudo chown -R skypane:skypane ${APP_ROOT}/server ${APP_ROOT}/stub-server"

echo "==> Restarting skypane-byos.service and starting skypane-poll.timer"
ssh "${SSH_TARGET}" "sudo systemctl restart skypane-byos.service && sudo systemctl start skypane-poll.timer"

echo "==> Recent journald output"
echo "--- skypane-byos ---"
ssh "${SSH_TARGET}" "sudo journalctl -u skypane-byos --no-pager -n 10"
echo "--- skypane-poll ---"
ssh "${SSH_TARGET}" "sudo journalctl -u skypane-poll --no-pager -n 10"

echo "==> Deploy complete."
