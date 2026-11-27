# Phase 70: pre-flip gate and post-flip verification

Written 2026-11-27 by a session from the evidence files and the CI. Nothing here is a secret. The visibility is changed only by the owner himself, last.

## Pre-flip gate

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Criterion 1: manual deploy proven | pass | `70-EVIDENCE.md` "Manual deploy proof": two refusals (runs 45712777893 and 45712969497) and successes (runs 45713258859 and 45713738451); frame poll unchanged: yes. Further manual deploys succeeded on 2026-11-26 and 2026-11-27 (runs 8, 9, 11); a deploy attempt with a mismatched `ci_sha` was refused by the guard on 2026-11-27 (run 10) |
| 2 | Criterion 2: signing on the Mac | pass | `70-EVIDENCE.md` "Signed test release": tag fw-v1.2.2, release assets: 7, shown on the companion Update page (the `firmware_cli` listing was not run), offered to frame: no; "Signing secret retired": deleted by the owner: yes |
| 3 | Criterion 3: CI fits the plan, measured and decided | open (owner) | `70-MEASUREMENTS.md`: measurements recorded; the decision on where CI runs is pending the owner (Mac, mini PC or paid minutes) |
| 4 | Criterion 4: inventory handled | pass | `70-INVENTORY.md`: every row has an owner decision (all "leave"), no secret needed rotating |
| 5 | Documents merged and `main` green | pass | #600 merged (README and the other documents describe the private repository); the push CI run of `main` at 7c994a1 (run 1504) is green after one re-run of a timing failure |
| 6 | Charge watch | pass | postponed with no new date, read on 2026-11-27 (see `70-MEASUREMENTS.md`); expires 2026-12-24 |
| 7 | Token scope for sessions | open (owner) | The owner confirms that the sessions' GitHub integration can push, open draft pull requests, read check status and job logs (contents, pull requests, Actions) on the private repository. The sandbox `gh` token is invalid; reads work today only because the repository is public. The integration did read job logs on 2026-11-27 |
| 8 | Settings the owner checks | open (owner) | Dependabot alerts and updates on; fork pull request workflows off; "Require approval for all outside collaborators" set; no collaborators |
| 9 | Fresh artifact for the release dry run | open (owner) | `fw-unsigned-fw-v1.2.2` was built on 2026-11-25 and expires after 14 days (about 2026-12-09); regenerate with a re-run of that `firmware-release.yml` run if expired |
| 10 | D-07 delivered | pass | `70-MEASUREMENTS.md` has one `D-07 decision:` line ("decided by the owner") and one `D-07 delivered:` line; the "CI path splitting" section has before/after counts |

Rows 1, 2, 4, 5, 6 and 10 pass. Rows 3, 7, 8 and 9 wait for the owner; the gate is not open.

Before the flip, also: set `CI_RUNS_ON` again to the chosen runner, re-read the self-hosted charge status, and confirm that no workflow uses `environment:` (checked 2026-11-27: none in `.github/workflows`).

## Switch

visibility changed by the owner: pending

## Post-flip verification

Filled in after the owner has made the repository private. Items as in plan 70-10: session push and draft pull request, read CI status and a job log, dispatch test (sessions must not dispatch `deploy.yml`), CI on the Mac runner and on the hosted fallback, Dependabot, nightly backup, manual deploy with the release download, firmware release dry run, no use of environments, branch protection or secret scanning.

| # | Item | Result |
|---|------|--------|
| 1 | Session push, draft pull request, CI status and log | pending |
| 2 | Can a session dispatch a workflow? | pending |
| 3 | CI on the Mac runner, then on the hosted fallback (private-repository minutes) | pending |
| 4 | Dependabot | pending |
| 5 | Nightly backup | pending |
| 6 | Manual production deploy with the firmware release download | pending |
| 7 | Firmware release dry run on the Mac | pending |
| 8 | No environments, branch protection or secret scanning assumed | pending |
