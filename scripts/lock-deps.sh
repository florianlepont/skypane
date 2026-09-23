#!/usr/bin/env bash
# SkyPane — regenerate the hash-locked dependency files (TST-08).
#
# Compiles server/requirements.in -> server/requirements.txt (runtime
# lock, what deploy/deploy.sh installs on the VPS with --require-hashes)
# and server/requirements-dev.in -> server/requirements-dev.txt (dev
# lock, a superset that CI installs with --require-hashes). Both locks
# pin every transitive package (urllib3, certifi, idna,
# charset-normalizer, ...) with sha256 hashes, not just the direct pins
# above.
#
# Requires `uv` on PATH (https://docs.astral.sh/uv/). Never hand-edit the
# hashes in the compiled .txt files - always regenerate through this
# script so the lock and the resolver that produced it stay in sync.
#
# Usage:
#   scripts/lock-deps.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    echo "scripts/lock-deps.sh: 'uv' not found on PATH." >&2
    echo "  Install: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# Locks are generated for Python 3.14 on x86_64 Linux (manylinux_2_28):
# production (OVH VPS, Ubuntu 26.04, Python 3.14) and CI (ubuntu-latest,
# Python 3.14) are both x86_64 Linux, so one platform target covers both.
# If a future uv rejects the manylinux_2_28 platform tag, fall back to
# the coarser "linux" value instead (--python-platform linux).

echo "==> Locking server/requirements.in -> server/requirements.txt"
uv pip compile --generate-hashes \
    --python-version 3.14 \
    --python-platform x86_64-manylinux_2_28 \
    --custom-compile-command "scripts/lock-deps.sh" \
    "${REPO_ROOT}/server/requirements.in" \
    -o "${REPO_ROOT}/server/requirements.txt"

echo "==> Locking server/requirements-dev.in -> server/requirements-dev.txt"
uv pip compile --generate-hashes \
    --python-version 3.14 \
    --python-platform x86_64-manylinux_2_28 \
    --custom-compile-command "scripts/lock-deps.sh" \
    "${REPO_ROOT}/server/requirements-dev.in" \
    -o "${REPO_ROOT}/server/requirements-dev.txt"

echo "==> Done. Review the diff before committing."
