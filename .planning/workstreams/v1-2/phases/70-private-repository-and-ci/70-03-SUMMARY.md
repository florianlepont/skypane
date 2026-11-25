---
phase: 70-private-repository-and-ci
plan: 03
subsystem: firmware-release
tags: [signing, ci, github-actions]
requires: [70-01]
provides: [build-only firmware-release workflow, scripts/fw_publish_signed.py]
key-files:
  created: [scripts/fw_publish_signed.py, deploy/tests/test_fw_publish_signed.py]
  modified: [.github/workflows/firmware-release.yml, deploy/tests/test_ci_secrets.py]
requirements: [PRV-01]
---

# Phase 70 Plan 03: Signing on the Mac Summary

firmware-release.yml now only builds both boards and uploads the unsigned images with SHA256SUMS (`fw-unsigned-<tag>`, 14 days); `scripts/fw_publish_signed.py` verifies provenance, signs with the pinned container and local key, and publishes the seven unchanged asset names.

## Base

Plan depends on 70-01 (PR #589, not on main). This branch merges `origin/phase-70-01-manual-deploy-pr` (merge commit 633001c) so `deploy.yml` exists and the workflow-wide tests hold.

## Commits

- bb5465f: firmware-release.yml build-only, test_ci_secrets.py repointed
- a5cf1f8: fw_publish_signed.py and its tests

## Tasks

1. Workflow: job `release` became `build` (contents: read, no environment, no secret, no gh calls); guard steps unchanged. `test_firmware_release_passes_signing_key_through_env` replaced (the plan's deliberate repointing) by four workflow-wide absence/presence tests.
2. Script plus 18 tests with a faked `run` seam (git, gh, docker, manifest, registry): bad tag, off-main, run/sha/branch mismatch, tampered, extra or missing artifact file, loose key mode, dry-run publishes nothing and scratch-imports, exactly seven names, existing release refused, key mounted `:ro` with `--network none` and never printed, verification against the committed public key, deploy dispatch only on `y`, worktree removed on failure.

## Deviations

- The guard job's explanatory comment mentioned the `firmware-signing` environment and `environment:`; its comment text was rewritten (steps byte-identical) so that "no `environment:`" holds workflow-wide.
- Tests are over a monkeypatched `run` seam rather than PATH shims; the real `gh`/`docker`/`git` are never invoked.
- `check_function_size.py` only gates `server`/`stub-server`; the script's functions are all well under 80 lines anyway.

## Not run

No real docker signing, no real `gh`, no real key, no GitHub workflow; the real dry-run and test release are owner steps in plan 70-04. The script's scratch import (`server.firmware_cli import-dir`) is exercised only against the fake, not the real registry.

## Verification

deploy/tests, stub-server/test_phase47_freeze.py, golden render and giant render tests: 475 passed, 1 skipped (pre-existing openssl backdating skip). ruff and comment-history check clean.
