---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 09
subsystem: deploy
tags: [deploy, ci, activate, firmware-release]
requires: [64-01]
provides: [typed release download in the deploy job, SKYPANE_ENABLE_SECOND_HARDWARE forwarding to import-dir]
key-files:
  created: [scripts/fw_release_assets.py, deploy/tests/test_release_assets.py]
  modified: [.github/workflows/ci.yml, deploy/activate.sh, deploy/tests/test_activate.py]
requirements: [HW2-03]
completed: 2026-11-14
---

# Phase 64 Plan 09: Typed release download and switch forwarding Summary

The deploy job now downloads the legacy pair plus every typed pair chosen by an allow-listed Python function, and activate.sh forwards the second-hardware switch to the import step only when it is exactly 1.

## Tasks
1. `097b79a` scripts/fw_release_assets.py: wanted_assets(tag, names), stdlib only, key allow-list `[a-z0-9-]{1,64}`, CLI exit 1 (nothing wanted) / 2 (bad tag).
2. `88064bf` ci.yml download step uses the script and exact names; activate.sh parses the switch with `_extract_env` (only 1 accepted) and runs `runuser -u skypane -- env SKYPANE_ENABLE_SECOND_HARDWARE=1 ...` only then; env file never sourced.

## Tests
- `deploy` suite: 302 passed, 1 skipped (pre-existing openssl backdate skip).
- New: 28 release-asset tests (function, CLI, and the ci.yml download step extracted from the workflow and run against a fake gh: live-only set and incomplete-tag warning identical to before), forwarding tests for 1 / absent / empty / 0 / true / 11 / quoted / trailing space / comment / indented / command substitution.
- ruff clean; mypy clean for the script; `bash -n deploy/activate.sh` ok (shellcheck not installed).

## Deviations from Plan
- The draft PR and its description were not created (plan says pre-merge; the caller said not to push). The PR text must state that ci.yml deploys on merge and live-only behaviour is unchanged.
- `gh release download` has no exact-name option, so `--pattern` is used with names emitted only by the validated script (charset has no glob characters).

## Known Stubs
None.

## Self-Check: PASSED
