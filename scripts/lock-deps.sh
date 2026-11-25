#!/usr/bin/env bash
# SkyPane -- regenerate the hash-locked dependency files.
#
# Compiles server/requirements.in -> requirements.txt (runtime lock) and
# requirements-dev.in -> requirements-dev.txt (dev superset, what CI
# installs). Both pin every transitive package with sha256 hashes.
#
# Requires `uv` on PATH (https://docs.astral.sh/uv/). Never hand-edit the
# lock hashes -- always regenerate through this script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    echo "scripts/lock-deps.sh: 'uv' not found on PATH." >&2
    echo "  Install: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# Production (OVH VPS, Ubuntu 26.04) and hosted CI (ubuntu-latest) are
# x86_64 Linux on Python 3.14, so one manylinux_2_28 target covers both.
# The lock also carries linux aarch64 wheels (checked with `pip download
# --only-binary=:all: --platform manylinux_2_28_aarch64 --python-version 3.14
# --require-hashes -r server/requirements-dev.txt`), so an Apple-Silicon
# Linux VM installs it unchanged; production stays x86_64.
# If a future uv rejects that platform tag, fall back to the coarser
# "linux" value (--python-platform linux).

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
