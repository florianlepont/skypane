---
phase: 51-per-device-config-image-and-state
plan: 13
subsystem: verification
tags: [verification, owner-checks, validation]
requires: ["51-12"]
provides:
  - full-gate results on the merged branch
  - plain-French owner checks
affects: [51-VALIDATION.md, ROADMAP.md, STATE.md]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-OWNER-CHECKS.md
  modified:
    - .planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-VALIDATION.md
    - .planning/workstreams/v1-2/ROADMAP.md
    - .planning/workstreams/v1-2/STATE.md
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 13: Merged-branch verification and owner checks Summary

Full suite, linters, type check and guards are green on the branch that already contains main; the owner's plain-French verification steps are written down; no deploy was performed.

## Gate results

- Merge: main was already merged (b455899). `git fetch origin main` and `git log HEAD..origin/main` is empty; `git merge-base --is-ancestor origin/main HEAD` passes.
- `./scripts/run-all-tests.sh --basetemp=/tmp/pb --cov-fail-under=93` with `SKYPANE_REQUIRE_BROWSER=1` and a Playwright path mapping the available browser build: 6432 passed, 8 skipped, 0 failed, coverage 95.85% (floor 93%). Skips: 7 root-permission tests (root ignores permission bits), 1 openssl backdating test (local openssl cannot backdate a certificate).
- ruff: all checks passed. mypy: no issues in 19 source files. comment-history check: exit 0. function-size gate (max 80): 641 functions, none over.
- Frozen tests, `measured_fields_freeze.json`, `hardware/`, `firmware/`, `deploy/deploy.sh`, `deploy/activate.sh`, `deploy/provision.sh`: empty diff against 51-BASE-REF.txt. `.planning/phases/47-*`: empty diff. Freeze and negotiation tests pass in the full run.
- No deploy, activate or provision command was run, and no production system was contacted.

## Deviations from Plan

**1. [Rule 3 - Blocking] Chromium could not launch with the default pytest temp dir.** The first full run gave 558 browser-fixture errors: Chromium aborted with "Socket path too long" (the singleton socket path under `/tmp/pytest-of-root/pytest-N/popen-gwN/...` exceeds the 107-character limit). Re-ran with `--basetemp=/tmp/pb` (explicit `--cov-fail-under=93` to keep the floor enforced, because extra pytest arguments disable it in the wrapper). No test, gate or code changed.

**2. Plan step "merge main"** was already done before this plan (per the orchestrator), so only the up-to-date check was run.

**3. Bookkeeping check against the base ref** reports 22 non-Phase-51 changed lines in ROADMAP.md and STATE.md because those come from the main merge (other phases' work). The lines changed by this plan (against HEAD) are all Phase 51: plan checkboxes 08, 09, 11, 13 ticked, progress row 13/13, and the two "Stopped At" lines. The Phase 51 checklist line near the top is left unticked and REQUIREMENTS.md is untouched, for the verifier.

## Known limits

- A temporary seeded state directory used to check the owner commands remains under `/tmp` (cleanup was blocked by a safety check); it is harmless.

## Human checks

<human-check>Owner runs the numbered steps of 51-OWNER-CHECKS.md on a development machine: selector switch, poll one cadre, change heures calmes and fuseau horaire of one cadre, empty states, live frame unchanged. Expected: every step's stated result.</human-check>

## Self-Check: PASSED

51-OWNER-CHECKS.md and the updated 51-VALIDATION.md exist; gate results recorded above.
