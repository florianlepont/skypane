---
phase: 70-private-repository-and-ci
status: complete-with-criteria-moved
updated: 2026-11-27
requirements: [PRV-02]
---

# Phase 70 verification: private repository and CI

State on 2026-11-27. The phase is closed for success criteria 1 to 4. Criteria 5 and 6 depend on the switch to private, which the owner makes at the close of v1.4, so they moved to the inserted Phase 70.1 (owner decision of 2026-11-27). Everything below was done by the owner on his machine or in GitHub, or read by a session from the CI; no session read, used or deleted a secret or a key.

## Success criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | The production deploy needs an explicit act of the owner, proven on a test run | Met | `70-EVIDENCE.md` "Manual deploy proof": two refusals and successes of `deploy.yml`; further manual deploys on 2026-11-26 and 2026-11-27 (a mismatched `ci_sha` was refused by the guard) |
| 2 | Firmware signed on the owner's computer, no key in a secret, signed test release imported | Met | `70-EVIDENCE.md` "Signed test release" (fw-v1.2.2, 7 assets, shown on the Update page, never offered to the frame) and "Signing secret retired" |
| 3 | The CI fits the plan: choice made and recorded with measured minutes, no test skipped, browser tests on every code change | Met | `70-MEASUREMENTS.md` (before and after, decision of 2026-11-27); `70-TEST-AUDIT.md` and `70-TEST-SPEED-SUMMARY.md`; gates unchanged (skipped ceiling 0, executed floor 12,821, coverage floor on `main`) |
| 4 | Inventory of what has been public, handled | Met | `70-INVENTORY.md`: every row decided by the owner, no secret needed rotating |
| 5 | After the switch everything still works | Moved to Phase 70.1 | pre-flip gate prepared in `70-POSTFLIP.md` |
| 6 | The repository is private and the documents describe the new setup | Moved to Phase 70.1 | the documents were merged on 2026-11-26 (#600) while the repository is public |

## Requirements

PRV-02 complete. PRV-01 and PRV-03 move to Phase 70.1 with criteria 5 and 6.

## Open points

- Hosted minutes on a private repository and a solo Mac run were not measured (see `70-MEASUREMENTS.md`).
- The self-hosted charge status expires on 2026-12-24 and is re-read before the switch.
- Plan 70-10 (gate, switch, post-switch checks) is carried by Phase 70.1.
