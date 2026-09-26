#!/usr/bin/env bash
# SkyPane — ship one git SHA's committed tree to an already-provisioned
# VPS and run its own activate.sh there.
#
# Run from the repository root on your laptop or CI runner, not on the
# VPS. deploy/provision.sh must have run there once first.

# Usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh ubuntu@203.0.113.10
#
# SSH_TARGET logs in as a non-root user with passwordless sudo, never as
# root directly; every remote step runs through `sudo`.
#
# `git archive` streams exactly the committed tree at HEAD — no local
# edits, untracked files, state/, venv/ or skypane.env ever leave this
# machine. Staging, the atomic swap, restarts and rollback all belong to
# deploy/activate.sh (runs as root on the VPS); this script only relays its exit status.
set -euo pipefail

SSH_TARGET="${1:?usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh ubuntu@203.0.113.10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

SHA="$(git -C "${REPO_ROOT}" rev-parse HEAD)"

if [ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]; then
    echo "==> WARNING: working tree has uncommitted changes - only the" \
        "committed tree at ${SHA} ships, nothing else" >&2
fi

INCOMING="/opt/skypane/releases/.incoming-${SHA}"

echo "==> Streaming the committed tree at ${SHA} to ${SSH_TARGET}:${INCOMING}"
# server/state/** is excluded even though it is (mostly) untracked,
# because server/state/.gitignore itself is a tracked file and would
# otherwise be the one server/state/ entry that leaks into the archive.
# SC2029: INCOMING is expanded locally on purpose; it is a fixed path built
# from a hex SHA, so it needs no remote-side quoting beyond the single quotes.
# shellcheck disable=SC2029
git -C "${REPO_ROOT}" archive --format=tar "${SHA}" -- \
    server stub-server companion deploy adsb-test/runway3.json \
    ':(exclude)server/state/**' \
    | ssh "${SSH_TARGET}" "sudo install -d -m 0755 /opt/skypane/releases \
        && sudo rm -rf '${INCOMING}' \
        && sudo install -d -m 0755 '${INCOMING}' \
        && sudo tar -x -C '${INCOMING}'"

echo "==> Running activate.sh on ${SSH_TARGET} for ${SHA}"
# shellcheck disable=SC2029
ssh "${SSH_TARGET}" "sudo bash '${INCOMING}/deploy/activate.sh' '${SHA}' '${INCOMING}'"

echo "==> Deploy complete."
