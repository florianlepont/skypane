---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 08
subsystem: firmware-release
tags: [firmware_cli, import-dir, release-manifest, hardware-gating]
requires: [64-01]
provides:
  - import-dir skip semantics for typed releases of unavailable types
  - release manifest tool independent of the production switch
affects: [server/firmware_cli.py, scripts/fw_release_manifest.py]
key-files:
  modified:
    - server/firmware_cli.py
    - server/test_firmware_cli.py
    - scripts/fw_release_manifest.py
    - deploy/tests/test_release_manifest.py
requirements: [HW2-03]
completed: 2026-11-14
---

# Phase 64 Plan 08: Skip semantics and switch-independent manifest tool Summary

import-dir now skips a typed release whose valid-shape key is unknown or unavailable (exit 0, `skipped <tag> [<key>]: hardware type not available here` on stderr), and fw_release_manifest.py resolves profiles with its own forced-switch environment copy.

## Tasks

1. Skip semantics (commit 8889bd0). `_typed_key_error` keeps only shape and legacy-key errors; new `_typed_key_unavailable` drives the skip, checked before any path is built from the key. Tests: the unknown-key and simulated-refused cases were adapted on purpose (now rc 0 + notice, with a why-comment); bad shape and the legacy key as typed item stay rc 1; added re-run idempotency and "imports once available" tests.
2. Manifest tool (commit 2c25b8d). `_release_environ()` copies os.environ, forces SECOND_ENV_VAR=1 and removes SIM_ENV_VAR; `_profile()` is used by `size_bound` and `check_image`. New tests: evaluation key builds a manifest with both switches cleared, evaluation size bound, sim key still exit 2 (with and without SIM switch exported). Existing unknown-type test passes unmodified.

## Deviations from Plan

- The bad-key parametrization dropped "no-such-type" (now a skip) and added "a.b" and the legacy key; a slash key was tried but cannot be a filename, so it was removed.
- Sim keys are refused even if the host exports the simulation switch, because the tool removes it from its copy (stricter than "does not set it").

## Verification

- pytest: server/test_firmware_cli.py, server/test_firmware_registry.py, deploy/tests/test_release_manifest.py: 272 passed.
- Phase 47 freeze, pairing freeze, golden render tests: 118 passed.
- ruff clean, mypy clean, function-size gate clean (none over 80), comment-history guard clean.
- No change to .github/workflows/firmware-release.yml.

## Self-Check: PASSED
