---
phase: 66-security-audit
plan: 07
subsystem: fix-handling
tags: [SEC-AUD-01, fixes]
requires: [66-02, 66-03, 66-04, 66-05, 66-06]
provides:
  - 66-FIX-LEDGER.md
affects: [66-08]
metrics:
  completed: 2026-11-27
---

# Phase 66 Plan 07: Fix handling Summary

No high or critical finding was recorded, so the held-back path of this plan was not used. The three medium findings were fixed, one small change per root cause, each with tests, on its own branch from `main`, as draft pull requests merged by the owner.

## Changes

- Deploy approval (two audit rows, one root cause): the deploy job runs in the protected `production` environment. Pull requests #627 and #629 (README wording). Tests in `deploy/tests/test_deploy_workflow.py` and `deploy/tests/test_ci_secrets.py`; the full `deploy/tests` suite passed (395 passed, 1 skipped).
- Backups at rest: an opt-in disk-encryption requirement on the Mac pull, documented in `deploy/README.md`. Pull request #628. Four tests in `deploy/tests/test_mac_pull.py`; the full `deploy/tests` suite passed (398 passed, 1 skipped). The backup format and restore path are unchanged.

## Owner-side steps, all done on 2026-11-27

- The deploy secrets moved to the protected environment with a required reviewer and a `main` branch rule; the repository-level copies were deleted; a new deploy key replaced the previous one, and the previous key was removed from the host.
- One manual deploy through the gated workflow paused for approval and succeeded.
- Disk encryption is on for the Mac that holds the backup copy, the opt-in setting is in its backup configuration, and one pull completed with it.

## Deviations from Plan

- The plan's per-finding procedure was run by hand rather than through the executor, because only medium findings existed. The ledger (`66-FIX-LEDGER.md`) is the record.
- The first deploy attempts after the move failed at the host-key step because a secret held a stale or mismatched value; correcting the secrets fixed it. No code change was needed.
- The golden-hash, freeze and access-rule suites were not touched by any change (the three pull requests change only the deploy workflow, its tests, the Mac pull script and the deploy README); their CI runs were green.
