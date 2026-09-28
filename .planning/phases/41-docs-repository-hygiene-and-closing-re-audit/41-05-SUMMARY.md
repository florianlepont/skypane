---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 05
subsystem: testing
tags: [firmware, esp-idf, audit, re-verification, byos, tls-session, nvs]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: FW-01..FW-15 remediations (reset backoff, wake deadline, token re-enrolment, sleep_s cap, checked returns, host-tested validators, https-only, per-device enrolment, DHCP, TLS session reuse, battery averaging, memtest off, dead-code removal, deduped helpers, git-describe version)
provides:
  - Independent, current-code re-audit of all 15 FW findings (41-REAUDIT-FW.md)
  - Confirmation that firmware/ was not modified during this re-audit
  - A documented positive drift: 34-VERIFICATION.md's W-1 warning was fixed after that report was written, even though it was scored non-blocking
affects: [42-remote-firmware-update-ota, 41-08-closing-plan]

# Tech tracking
tech-stack:
  added: []
  patterns: ["read-only re-verification against current file:line, host-test/check-script runs, and Phase 34 hardware logs rather than trusting SUMMARY/VERIFICATION checkboxes"]

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-FW.md
  modified: []

key-decisions:
  - "All 15 FW findings verify VERIFIED-CLOSED against current firmware/main/*.c, sdkconfig.defaults, and stub-server/byos_server.py"
  - "FW-09/FW-10/FW-11/FW-12's specific measured figures (DHCP timing, TLS handshake savings, battery mV delta, spacing-hold duration) are labelled hardware-log-evidence in Notes rather than independently re-measured, per 41-CONTEXT.md's evidence standard"
  - "This repo's git history is squashed at the PR/phase level (65 total commits for the whole project), not per-plan — 'closing commit' cells cite the actual git log --follow result and note the caveat once in the report header rather than guessing a per-plan commit that does not exist"

patterns-established: []

requirements-completed: []  # DOC-03 spans 4 re-audit slices (41-04..41-07) plus the 41-08 closing merge; not complete until 41-08

# Metrics
duration: 55min
completed: 2026-09-28T06:13:54Z
---

# Phase 41 Plan 05: Closing re-audit of Phase 34 firmware (FW-01..FW-15) Summary

**Independently re-verified all 15 Phase 34 firmware findings against current firmware source, sdkconfig, and byos_server.py — all 15 VERIFIED-CLOSED, firmware/ untouched throughout.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-28T05:19:00Z (approx.)
- **Completed:** 2026-09-28T06:13:54Z
- **Tasks:** 2 (combined into one report/one commit — see Deviations)
- **Files modified:** 1 (`41-REAUDIT-FW.md`, new)

## Accomplishments

- Ran all three firmware gate scripts (`run_host_tests.sh` — 10 suites pass,
  `check_production_config.sh static` — PASS, `check_log_contract.sh` — PASS)
  and confirmed `firmware/` was byte-identical before/during/after each run.
- Wrote 15 report rows (FW-01..FW-15), each with a verdict, the closing
  commit(s) `git log --follow` actually reports, current file:line evidence,
  and — where applicable — the covering host test or stub-server pytest id.
- Ran the byos re-enrolment test suite directly:
  `test_setup_with_wrong_secret_returns_401_and_leaves_existing_token_working`
  and `test_setup_with_registered_mac_and_matching_secret_issues_token_and_revokes_previous`
  both pass, proving FW-08's "byos refuses re-enrolment of a known MAC"
  claim on the current code, not just the ledger's word.
- Confirmed `git grep -nE "fp_api_post_logs|FP_PROVISION_TIMEOUT_S|FP_FACTORY_PREP" firmware`
  is empty (FW-13's orphan-symbol claim holds) and
  `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n` at `sdkconfig.defaults:19`.
  the ledger's dead-code/rollback lore holds in the current tree.
- Discovered and documented a positive drift: `34-VERIFICATION.md`'s W-1
  warning (a persistent-NVS-failure panic loop, explicitly scored "not a
  blocker" at verification time) was actually fixed after that report was
  written — `app_main.c` no longer has the flagged `ESP_ERROR_CHECK`, a new
  `nvs_boot.c` module and `test_nvs_boot.c` host test now exist, and
  `run_host_tests.sh` runs 10 suites (one more than the 9 the verification
  report recorded).
- Confirmed `git diff --stat 7bd8664 -- firmware/` shows exactly one file
  changed (`firmware/VENDOR.md`, 41-02's concurrent doc-prose edit) — zero
  firmware code or config drift across this entire re-audit.

## Task Commits

Both plan tasks (Task 1: FW-01..FW-07, Task 2: FW-08..FW-15) target the same
single output file (`41-REAUDIT-FW.md`); the work was done as one continuous
read-only investigation and committed as one commit, since splitting an
atomic markdown-file write into two partial commits would have left an
incomplete/invalid intermediate report on disk between commits.

1. **Tasks 1+2: Re-audit FW-01..FW-15 against current firmware, read-only** - `b30c741` (docs)

**Plan metadata:** (this SUMMARY.md and the final metadata commit, see below)

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-FW.md` - 15-row re-audit report (FW-01..FW-15), gate-run results, git-history caveat, and Flags section

## Decisions Made

- Combined the plan's two tasks into a single commit (see Task Commits above)
  because they write to the same file and an intermediate partial-table
  commit would not be a valid standalone artifact.
- Where the ledger's remediation text includes a specific measured figure
  (DHCP timing, TLS handshake savings, battery mV delta, panel spacing-hold
  duration) that this plan did not re-measure on hardware, the verdict is
  still VERIFIED-CLOSED for the code-level claim, with the figure itself
  explicitly labelled "hardware-log-evidence" in that row's Notes — per
  41-CONTEXT.md's instruction to label hardware-only claims as such rather
  than re-deriving them.
- Recorded the repo's squashed-history reality (65 total commits, no
  per-plan `(34-NN)` tagged commits) once in the report header rather than
  fabricating a plausible-looking commit hash per row.

## Deviations from Plan

None - plan executed exactly as written. The only adaptation was procedural
(one commit instead of two, documented above under Decisions Made), not a
deviation under Rules 1-4 - no bug was fixed, no missing functionality was
added, nothing blocking was resolved, and no architectural change was made.
This plan's own action step permits itself to be run as one continuous
investigation ("Then write rows FW-01..FW-07" / "Write rows FW-08..FW-15",
both appending to the same file), and the acceptance criteria for both tasks
were verified together against the completed file.

## Issues Encountered

None. All three firmware gate scripts ran cleanly on the first attempt;
`git status --porcelain firmware/` was empty after every command in this
plan, including the final check against `7bd8664` (the commit that captured
Phase 41's starting context, used as pre-phase-41 baseline).

## User Setup Required

None - no external service configuration required. This plan is read-only
verification; no code was written, and no services were touched other than
running local pytest against a fixture stub-server instance.

## Next Phase Readiness

- FW-01..FW-15 are provably closed on the current codebase — Phase 42 (OTA)
  can proceed on the assumption that Phase 34's rollback-disabled,
  ISRG-only-bundle, per-device-enrolment, PROJECT_VER-from-git-describe
  foundations are real, not just documented as real.
- `firmware/` remains completely unmodified by this plan; Phase 42 is free
  to make its own first change to it.
- No blockers for 41-08 (the closing plan that merges all four re-audit
  slices): this slice's report format matches 41-04's (same columns, same
  three verdicts, `## Flags` section, header with audited commit and
  tools), so it can be merged directly.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-FW.md`
- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-05-SUMMARY.md`
- FOUND commit `b30c741` in `git log --oneline --all`
