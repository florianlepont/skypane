---
phase: 70-private-repository-and-ci
plan: 01
subsystem: ci-deploy
tags: [github-actions, deploy, workflow_dispatch]
requires: []
provides:
  - "workflow_dispatch-only production deploy (deploy.yml)"
affects: [70-03, 70-04]
key-files:
  created:
    - .github/workflows/deploy.yml
    - deploy/tests/test_deploy_workflow.py
  modified:
    - .github/workflows/ci.yml
    - deploy/tests/test_ci_secrets.py
    - deploy/tests/test_release_assets.py
    - deploy/tests/test_docs.py
    - deploy/README.md
key-decisions:
  - "ci.yml keeps its workflow_dispatch trigger because firmware-release.yml still dispatches it until plan 70-03"
requirements-completed: [PRV-01]
completed: 2026-11-25
---

# Phase 70 Plan 01: Manual production deploy Summary

Production deploy moved out of ci.yml into a workflow_dispatch-only deploy.yml (no environment, loud refusals, behaviour-tested guard steps).

## Commits
- 981b58d: deploy.yml, ci.yml deploy job removed, test_deploy_workflow.py (25 tests)
- f86aaa1: tests repointed to deploy.yml, README "Production deploy (started by hand)" section, lift runbook updated

## Verification
- deploy/tests: 339 passed, 1 skipped (openssl cannot backdate a certificate, pre-existing)
- stub-server/test_phase47_freeze.py, server/test_golden_render.py, server/test_golden_giant_render.py: 115 passed
- ruff, check_comment_history, check_function_size (max 80): clean
- shellcheck: not run (binary not installed here; no .sh file edited)
- Full scripts/run-all-tests.sh and any workflow run: not run

## Deviations from Plan
None. The deploy.yml header comment avoids the literal "environment:" so the acceptance grep prints nothing.

## Notes
- Between this merge and 70-03, firmware-release.yml still runs `gh workflow run ci.yml`, which now only runs tests: no firmware release may be tagged in that window. README "Firmware releases (OTA)" steps 1-2 are intentionally untouched (plan 70-04).

## Known Stubs
None.

## Self-Check: PASSED
