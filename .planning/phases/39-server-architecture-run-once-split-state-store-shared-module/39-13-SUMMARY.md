---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 13
subsystem: infra
tags: [ci, mypy, function-size-gate, architecture-docs, phase-close]

# Dependency graph
requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-04/39-06/39-08/39-10/39-11/39-12: every ARC-01..ARC-06 production change (poll_cycle.py's named steps over CycleContext, state_store.py, the render/calendar_rules packages, themes.py, net/safe_fetch.py, device_policy.py, no module-global setters, mypy on the 11-module pure core)"
provides:
  - "A committed tree-wide test (test-support/test_check_function_size.py) plus a blocking CI step (\"Function size gate\") that together fail the build if any non-test function in server/ or stub-server/ exceeds 80 code lines - the size gate is now a standing property, not a one-time measurement"
  - "server/poll_cycle.py added to [tool.mypy]'s global files list (12 files total); mypy stays green"
  - "39-ARC-BASELINE.md's After section, criteria table and intentional-behaviour-changes section - the phase's measured before/after record"
  - "ARCHITECTURE.md's module map and every corrected poll_loop.py/render.py reference in the render pipeline section"
  - "ARC-01 through ARC-06 marked Complete in REQUIREMENTS.md (checklist + summary table)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The function-size gate is enforced two ways from the same tool: a pytest test (test-support/test_check_function_size.py) that calls scripts/check_function_size.py's own main() in-process, and a CI step running the same command as a subprocess - removing either one alone still leaves the other failing the build (T-39-28's own mitigation)."

key-files:
  created: []
  modified:
    - test-support/test_check_function_size.py
    - .github/workflows/ci.yml
    - pyproject.toml
    - server/poll_cycle.py
    - ARCHITECTURE.md
    - .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-ARC-BASELINE.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/STATE.md

key-decisions:
  - "server/poll_cycle.py went into [tool.mypy]'s global files list, not the strict per-flag override list the 11 typed-at-birth/annotated modules use - its orchestration steps stay partially annotated (only the pure core - decide_hold, advance_is_due, normalise_pending, enqueue_pending, pop_fresh_pending, CycleContext - is fully typed, per 39-11's own must-have), so only the global (lenient) mypy options apply to it."
  - "The pyproject E402 comment was refreshed to the real 6-file list (server/device_config.py, server/panel_preview.py, server/plane/detect.py, server/plane/enrich.py, server/themes.py, stub-server/byos_server.py) obtained from `ruff check --isolated --select E402 .`; server/poll_loop.py was dropped from that list since its own two post-bootstrap imports already carry an inline `# noqa: E402` each and no longer rely on the project-wide suppression."
  - "39-ARC-BASELINE.md's After section reports the highest CC among run_once and its own named steps (advance_display_queue, CC 10) separately from the module's overall ceiling (_record_history, CC 12, a pre-existing accessory helper this phase's split calls but never touched) - both numbers matter for different reasons and neither should be presented as if it were the other."

requirements-completed: [ARC-01, ARC-02, ARC-03, ARC-04, ARC-05, ARC-06]

# Metrics
duration: ~25min
completed: 2026-09-27
---

# Phase 39 Plan 13: Phase close - permanent size gate, mypy on poll_cycle, ARC baseline After Summary

**The function-size gate and mypy are now permanent, blocking CI properties (not one-time measurements), `server/poll_cycle.py` is under mypy's global settings at 12 checked files total, and `39-ARC-BASELINE.md` carries a measured Before/After record showing `_run_once_locked`'s CC 53 replaced by a CC-10 ceiling across `run_once`'s own named steps - closing out ARC-01 through ARC-06.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2 completed
- **Files modified:** 9 (2 code/test files, 2 CI/config files, 2 docs files, 3 planning-state files)

## Accomplishments

- **Task 1 (`9a1f444`, feat):** Added `test_no_function_in_server_or_stub_server_exceeds_80_code_lines` to `test-support/test_check_function_size.py` (calls the tool's own `main(["check", "--max", "80", ...])` in-process and asserts exit 0), and a blocking CI step "Function size gate (non-test code in server/ and stub-server/)" running the same command as a subprocess, right after the Type check step - two independent enforcement paths from one tool, so deleting either alone still fails the suite. Added `server/poll_cycle.py` to `[tool.mypy]`'s global `files` list (not the strict override - its pure core is fully typed per 39-11, the orchestration steps stay partially annotated); the only real gap the global settings found was `detect_flight`'s `diagnostics` local needing an explicit `dict | None` annotation (a typing fix, zero behaviour change - `mypy` now reports "12 source files", up from 11). Refreshed the `pyproject.toml` E402 comment to the real 6-file list from `ruff check --isolated --select E402 .`, dropping `server/poll_loop.py` (its own two imports now carry an inline `# noqa: E402` rather than relying on the project-wide suppression).
- **Task 2 (`39f9401`, docs):** Re-ran every Before command from `39-ARC-BASELINE.md` on the final tree and filled in the After section with the same seven subsections (function size: 401 functions scanned, zero offenders, up from 365 scanned/6 offenders; cyclomatic complexity: `run_once` CC 3, its highest named step `advance_display_queue` CC 10, vs Before's `_run_once_locked` CC 53/grade F - an 81% drop; typed functions: 73 of 356 non-test server functions annotated, up from 0 of 318, mypy 12 files green; companion imports of `server.poll_loop`: zero statement-level imports left, confirmed by a repo-wide grep; module-global setters: all three deleted outright, not merely uncalled; duplicated device policy: all nine rows now one definition each with file:line evidence, the tenth (quiet-hours invalid-time fallback) unified per D-4; suite: 2995 passed/139 skipped, coverage 94.27%, ruff and comment-history clean). Added a Criteria table (four ROADMAP criteria, each marked Met with its evidence command) and an Intentional behaviour changes section naming D-4 (unified quiet-hours invalid-time fallback) and D-5 (vendored-only theme preview), each with the test that pins it. Updated `ARCHITECTURE.md`: replaced every stale `poll_loop.py`/`render.py` reference in the render-pipeline body with `poll_cycle.py`/`server/plane/render/`, and added a Module map paragraph naming `poll_loop.py`, `poll_cycle.py`, `state_store.py`, `device_policy.py`, `themes.py`, `net/safe_fetch.py` and the `render/`/`calendar_rules/` packages.
- **Phase close-out (this plan's own scope, not a numbered task):** `ARC-01` through `ARC-06` marked Complete in `.planning/REQUIREMENTS.md` (both the checklist and the summary table) via `gsd-sdk query requirements.mark-complete`.

## Task Commits

1. **Task 1: permanent size gate and poll_cycle under mypy** - `9a1f444` (feat)
2. **Task 2: 39-ARC-BASELINE.md After section and ARCHITECTURE.md module map** - `39f9401` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `test-support/test_check_function_size.py` - tree-wide size-gate test
- `.github/workflows/ci.yml` - blocking "Function size gate" step
- `pyproject.toml` - `server/poll_cycle.py` added to `[tool.mypy] files`; E402 comment refreshed
- `server/poll_cycle.py` - one variable annotation (`detect_flight`'s `diagnostics`)
- `ARCHITECTURE.md` - module map, corrected pipeline-body references
- `.planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-ARC-BASELINE.md` - After section, Criteria table, Intentional behaviour changes
- `.planning/REQUIREMENTS.md` - ARC-01..ARC-06 marked Complete
- `.planning/ROADMAP.md` - phase 39 progress/status
- `.planning/STATE.md` - position, decisions, session

## Decisions Made

See `key-decisions` in the frontmatter above: `poll_cycle.py` under mypy's global (not strict) settings; the E402 comment's real 6-file list, dropping `poll_loop.py` (inline `noqa` now, not the project-wide ignore); the After section's two distinct CC figures (named-step ceiling vs. module-wide ceiling) reported separately rather than conflated.

## Deviations from Plan

**None** - plan executed exactly as written. The only code change beyond the plan's literal file list was the one `diagnostics: dict | None = None` annotation in `server/poll_cycle.py`, which the plan's own Task 1 action text explicitly anticipated ("fix any report with annotations or narrowing that does not change behaviour").

## Issues Encountered

None. `./scripts/run-all-tests.sh` (no extra arguments) was used instead of the plan verify text's own `./scripts/run-all-tests.sh -q` form, since passing any extra argument to that script disables its coverage gate (per the script's own comment) - the acceptance criteria explicitly required the coverage floor to be checked, so the full, gate-enabled invocation was run instead. Not a deviation in outcome: both the size gate and the coverage gate report the exact result the plan's acceptance criteria named.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 39 is closed at 13/13 plans: ARC-01 through ARC-06 are all measured, enforced by CI, and marked Complete. The function-size gate and mypy are now standing CI properties that any future phase touching `server/`/`stub-server/` inherits automatically. `39-ARC-BASELINE.md` is the phase's permanent before/after record. No blockers for Phase 40 (companion architecture, already executing in parallel per `39-CONTEXT.md`'s coordination note).

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*
