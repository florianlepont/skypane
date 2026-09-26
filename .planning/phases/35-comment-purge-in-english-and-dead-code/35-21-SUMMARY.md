---
phase: 35-comment-purge-in-english-and-dead-code
plan: 21
subsystem: firmware
tags: [comment-hygiene, firmware, esp-idf, vendor-provenance, ci-guard]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "the settled firmware tree this plan purges (gate G-34)"
  - phase: 35-comment-purge-in-english-and-dead-code (35-20)
    provides: "groups 1-8 already purged; scripts/check_comment_history.py CLI"
provides:
  - "Every firmware/*.c, firmware/*.h, Kconfig/CMake/sdkconfig/shell script and firmware/tools/gen_fault_screen.py history-free (0 hits)"
  - "firmware/VENDOR.md rewritten concisely (477 -> 367 lines) with every fact check_log_contract.sh greps preserved"
  - "scripts/comment-history-pending.txt emptied of every firmware/ path"
  - "check_comment_history.py check with no arguments exits 0 for the first time this phase"
affects: [35-22]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hash-comment same-code check is strictly positional (line-index equality after blanking comment text), so every edit to a .sh/Kconfig/sdkconfig/CMake comment must preserve the file's total line count exactly, unlike C (cpp -fpreprocessed) or Python (AST) same-code"
    - "A runtime __doc__ module (argparse ArgumentParser(description=__doc__)) needs same-code --allow when its docstring text changes, the same pattern group 2 used for server/plane/illustrations.py"

key-files:
  created: []
  modified:
    - firmware/main/*.c (all 20 files with history hits: api_client.c, app_main.c, battery.c, fault_inject.c, fault_screen.c, state_machine.c, wifi.c — plus comment-cap trims with no hits)
    - firmware/main/*.h (24 files with history hits or cap trims)
    - firmware/tests/*.c (5 files with history hits)
    - firmware/main/Kconfig.projbuild, firmware/sdkconfig.defaults, firmware/sdkconfig.ee02.defaults
    - firmware/.gitignore, firmware/build.sh, firmware/flash.sh, firmware/provision.sh
    - firmware/tests/check_log_contract.sh, firmware/tests/check_production_config.sh, firmware/tests/run_host_tests.sh
    - firmware/tools/gen_fault_screen.py
    - firmware/VENDOR.md
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md

key-decisions:
  - "Base for every same-code check was the literal commit 9baf745 the orchestrator specified, not a freshly recomputed merge-base — origin/main had moved 2 commits ahead (Phase 42 planning docs, no firmware/ paths) since that base, so no merge into the branch was needed"
  - "firmware/tools/gen_fault_screen.py was purged even though it is not in this plan's own files_modified list: it is a Python file under firmware/ that was left in scripts/comment-history-pending.txt, and the close_procedure's GROUP_PATHS is all of firmware/"
  - "Docker's daemon could not be started in this sandbox (ulimit permission denied on dockerd startup) — firmware/build.sh could not run; CI's firmware.yml is the build gate for this push, per the plan's own stated fallback"
  - "While purging main/sdkconfig.ee02.defaults' battery-sense comment (Rule 1), corrected its stale 'NOT YET CONFIRMED ON THIS BOARD' claim to CONFIRMED, matching hardware/BRINGUP-LOG.md's already-recorded 'ADC Battery-Sense Bring-Up: CONFIRMED — 2026-08-28' entry; the bring-up LED comment's own NOT YET CONFIRMED status was left alone since BRINGUP-LOG.md still records that one as unconfirmed"

requirements-completed: []

# Metrics
duration: 34min
completed: 2026-09-26
---

# Phase 35 Plan 21: Firmware comment-history purge (group 9) and phase close Summary

**Every firmware C/H/Kconfig/CMake/sdkconfig/shell/Python source is history-free (0 hits) and code-unchanged (same-code proven); `firmware/VENDOR.md` is rewritten from 477 to 367 lines with every log-contract fact preserved; `scripts/comment-history-pending.txt` is now empty of paths, so the CI guard covers every tracked code file in the repository for the first time this phase.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-09-26T01:53:51Z (base commit 9baf745)
- **Completed:** 2026-09-26T02:27:44Z
- **Tasks:** 3 (Task 1: C/H purge; Task 2: hash-comment files + VENDOR.md; Task 3: build proof + group close)
- **Files modified:** 51 firmware files + 2 phase-bookkeeping files (`scripts/comment-history-pending.txt`, `35-COMMENT-RATIO.md`)

## Gate Evidence (G-34)

Confirmed before any edit: `.planning/phases/34-firmware-resilience-power-security-cleanup/34-11-SUMMARY.md` exists on `origin/main`, and both `.planning/ROADMAP.md` and `.planning/STATE.md` (already on this branch) record Phase 34 as COMPLETE, 11/11 plans, hardware session PASS. `git fetch origin main` showed `origin/main` at `94016c7` — two commits ahead of the `c4fed5e` this branch already contained (`3983d7d`, `94016c7`, Phase 42 planning docs, `.planning/` only, no `firmware/` paths) — so no merge into the working branch was required before starting, and the group base stayed the literal `9baf745` specified.

## Accomplishments

- Purged every history-ID hit (`FW-01`/`02`/`06`/`10`/`11`/`14`, `DEVICE-01`/`04`/`05`/`06`, `D-34-02`/`03`, `T-34-04-02`/`03`/`09-01`/`09-06`/`10-01`, `T-u7n-01`/`04` (manually, unmatched by the checker's regex but clearly history), `260827-wo4`, `260924-u7n`, `260923-fr4`, `Phase 1`/`4`/`5`, `plan 01-05`/`34-06`/`34-08`, `01-RESEARCH.md`, `05-RESEARCH.md`, `05-CONTEXT.md`, `05-UI-SPEC.md`, `34-CONTEXT.md`, `34-04-SUMMARY.md`, `D-01`, `D-08`) from every firmware C/H source, test file, Kconfig/CMake/sdkconfig file, shell script and the one Python tool under `firmware/`.
- Trimmed the worst file-header and function-comment cap violations (`state_machine.h`, `wake_guard.h`, `fault_screen.h`, `nvs_schema.h`, `nvs_boot.h`, `panel.h`, `panel_guard.h`, `reset_reason.h`, `sleep_decision.h`, `tls_session.h`/`.c`, `wake_deadline.h`, `led.h`, `api_client.h`, `app_main.c`'s file header and `maybe_draw_fault_screen()`) down to or near the plan's hard caps, in every case keeping the underlying hardware/protocol/security why (SPDX headers, upstream attribution, the two-mechanism watchdog/deadline split, the private-struct TLS-session-mirror version pin, the fault-screen exclusion rationale, the GDEP133C02 datasheet finding) rather than deleting it.
- Rewrote `firmware/VENDOR.md`'s provenance concisely: every "Local changes" and "Original To This Repository" row is now a plain description of what changed and why, with zero plan/decision/threat/requirement IDs, while the upstream repository/commit/licence facts, the full five-line Log Line Contract table (all 14 `poll fail step=` tokens), the diagnostic-line reference table and the three operational-risk notes are all kept in substance — `check_log_contract.sh` passes against the rewritten file both before and after.
- Emptied `scripts/comment-history-pending.txt` of every remaining path (all 36 were `firmware/`); `check_comment_history.py check` with **no arguments** now exits 0 — the CI guard (once 35-22 deletes the pending mechanism entirely) covers every tracked code file in the repository.

## Task Commits

1. **Task 1 (C/H purge), battery telemetry** - `7604564` (docs)
2. **Task 1, fault-injection and LED** - `377e8a5` (docs)
3. **Task 1, fault-screen and NVS schema** - `17909f6` (docs)
4. **Task 1, nvs_boot.h header trim** - `4fc81f7` (docs)
5. **Task 1, panel.h/panel_guard.h caps** - `38d1c98` (docs)
6. **Task 1, reset_reason.h/sleep_decision.h** - `96960be` (docs)
7. **Task 1, state_machine/tls_session** - `9cacbf8` (docs)
8. **Task 1, wake_deadline.h/wake_guard.h** - `7acafac` (docs)
9. **Task 1, wifi.c/.h** - `b4d94c9` (docs)
10. **Task 1, api_client.c/.h** - `07dedfd` (docs)
11. **Task 1, app_main.c** - `ac7da65` (docs)
12. **Task 1, firmware host tests (5 test_*.c)** - `2fc7c9e` (docs)
13. **Task 2, .gitignore/build.sh/flash.sh** - `86782da` (docs)
14. **Task 2, provision.sh + test shell scripts** - `d13d80a` (docs)
15. **Task 2, Kconfig.projbuild + sdkconfig defaults** - `942c8b6` (docs)
16. **Task 2, gen_fault_screen.py** - `f0a70f3` (docs)
17. **Task 2, VENDOR.md rewrite** - `23e76fe` (docs)
18. **Task 3, group-9 close (ratio table + pending-list empty)** - `684761e` (docs)

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified

- `firmware/main/*.c`, `firmware/main/*.h` — history purged; several headers also trimmed to the file-header/function-comment caps (see Task Commits above for the per-batch breakdown).
- `firmware/tests/*.c`, `firmware/tests/*.sh` — history purged (5 `.c` test files with hits; `check_log_contract.sh`, `check_production_config.sh`, `run_host_tests.sh`).
- `firmware/main/Kconfig.projbuild`, `firmware/sdkconfig.defaults`, `firmware/sdkconfig.ee02.defaults` — history purged, comment line counts preserved exactly for the hash-format same-code check.
- `firmware/.gitignore`, `firmware/build.sh`, `firmware/flash.sh`, `firmware/provision.sh` — history purged.
- `firmware/tools/gen_fault_screen.py` — history purged from its module docstring (argparse `--help` text) and a function docstring.
- `firmware/VENDOR.md` — rewritten provenance, 477 -> 367 lines.
- `scripts/comment-history-pending.txt` — every `firmware/` line removed; file now has only its 3-line header.
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — group-9 section appended (79-file table, group total 24.6% -> 21.3%, justifications for files still above the 35% guideline).

## Decisions Made

- Used the literal base `9baf745` for every `same-code` invocation, as the orchestrator specified, rather than recomputing `git merge-base HEAD origin/main` (which would have resolved to `3983d7d`, an ancestor of `9baf745`'s own history on this branch) — this matches close_procedure's intent since origin/main brought no firmware changes.
- Purged `firmware/tools/gen_fault_screen.py` despite it not appearing in this plan's `files_modified` frontmatter list: it is a Python file under `firmware/`, sat in the pending list, and the close_procedure's `GROUP_PATHS = firmware/` covers it. Applied the same `--allow` treatment group 2 used for `server/plane/illustrations.py` (its module docstring is read via `argparse.ArgumentParser(description=__doc__)`), documented in its own commit.
- Discovered mid-task that the hash-comment `same-code` check (`_hash_code_lines`) is **strictly positional**: it blanks each comment line's text but keeps its position, so collapsing a two-line comment into one line shifts every subsequent line's index and fails `same-code` even though no code changed. Two edits to `firmware/tests/check_production_config.sh` tripped this on first attempt (caught before committing, since `same-code` is run before every commit) and were rewritten to preserve the original line count exactly. Recorded as a pattern for 35-22.
- Rule 1 auto-fix: `sdkconfig.ee02.defaults`' battery-sense comment claimed "NOT YET CONFIRMED ON THIS BOARD" while `hardware/BRINGUP-LOG.md`'s own "ADC Battery-Sense Bring-Up" entry already records "Status: CONFIRMED — 2026-08-28" — corrected the stale claim while removing its plan-ID citations, since I was already rewriting that exact comment. Left the neighbouring bring-up-LED comment's own "NOT YET CONFIRMED" wording untouched, since `BRINGUP-LOG.md` still records that one as unconfirmed.
- `firmware/build.sh` deliberately not forced to run: Docker's daemon cannot start in this sandbox (`sudo service docker start` failed with `ulimit: error setting limit (Operation not permitted)`), confirmed by a second direct `dockerd` attempt and `docker info` still reporting no socket. Recorded per the plan's own instruction to rely on CI's `firmware.yml` in that case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale "NOT YET CONFIRMED" battery-sense comment corrected**
- **Found during:** Task 2 (`firmware/sdkconfig.ee02.defaults`)
- **Issue:** The battery-sense pin comment said the EE02 battery-sense circuit was "NOT YET CONFIRMED ON THIS BOARD," but `hardware/BRINGUP-LOG.md`'s own "ADC Battery-Sense Bring-Up" section (out of scope for this plan, `hardware/` is markdown) already records "Status: CONFIRMED — 2026-08-28," confirmed on first flash.
- **Fix:** Rewrote the comment to say CONFIRMED, matching the bring-up log, while stripping its plan/quick-task IDs. Left the adjacent bring-up-LED comment's "NOT YET CONFIRMED" wording exactly as-is, since that one genuinely still reads unconfirmed in `BRINGUP-LOG.md`.
- **Files modified:** `firmware/sdkconfig.ee02.defaults`
- **Verification:** Read `hardware/BRINGUP-LOG.md`'s two bring-up sections directly to confirm the differing status before editing either comment.
- **Committed in:** `942c8b6`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** Corrects a factual staleness the purge pass happened to touch; no scope creep, no behaviour change (comment only).

## Issues Encountered

- The hash-comment `same-code` check compares comment-blanked lines **positionally**, so removing a full comment line (rather than editing within one) silently breaks it for `.sh`/Kconfig/sdkconfig/CMake files, unlike C (`cpp -fpreprocessed`) or Python (AST) same-code, which are structure-based and tolerate line-count changes. Caught immediately by running `same-code` before every commit as instructed (two edits in `firmware/tests/check_production_config.sh` failed on first attempt, fixed by re-wrapping the comment to the same line count before committing). No incorrect commit landed.
- Docker's daemon could not be started in this sandbox (`ulimit` permission denied), so `firmware/build.sh`'s containerised ESP-IDF build could not be run locally. Recorded as a stated, plan-anticipated fallback: CI's `.github/workflows/firmware.yml` runs the same build on push and is the gate for this change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every tracked code file in the repository is now history-free: `server/.venv/bin/python scripts/check_comment_history.py check` (no arguments, no pending-list skip) exits 0 for the first time in Phase 35.
- `scripts/comment-history-pending.txt` is empty except for its 3-line header, exactly as the ratchet-rollout design (`35-CONTEXT.md`) anticipates for the phase's last purge wave. **35-22 (the final closing plan) still owns deleting the pending-list mechanism entirely** and any phase-wide closing verification — this plan deliberately left the file in place with an empty body, per its own task instructions, rather than deleting it.
- `HYG-01` and `HYG-03` are **deliberately not marked complete** in `.planning/REQUIREMENTS.md` by this plan, per explicit orchestrator instruction — that traceability update is reserved for 35-22's phase-wide close.
- No PR was opened and nothing was pushed by this plan — the orchestrator owns that step.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-26*

## Self-Check: PASSED

- All 18 task/close commit hashes verified present via `git cat-file -e` (7604564, 377e8a5, 17909f6, 4fc81f7, 38d1c98, 96960be, 9cacbf8, 7acafac, b4d94c9, 07dedfd, ac7da65, 2fc7c9e, 86782da, d13d80a, 942c8b6, f0a70f3, 23e76fe, 684761e).
- `firmware/VENDOR.md` exists.
- `scripts/comment-history-pending.txt` has 0 `firmware/` lines remaining.
- `server/.venv/bin/python scripts/check_comment_history.py check` (no args) exits 0.
- `./scripts/run-all-tests.sh` and `server/.venv/bin/ruff check .` both green (2691 passed, 5 skipped, 93.24% coverage).
