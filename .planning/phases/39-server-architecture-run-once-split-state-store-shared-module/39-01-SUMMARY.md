---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 01
subsystem: testing
tags: [ast, tokenize, static-analysis, radon, cyclomatic-complexity, refactor-instruments]

requires: []
provides:
  - "scripts/check_function_size.py: stdlib-only function-size gate (check/report subcommands)"
  - "test-support/test_check_function_size.py: 14 detector tests"
  - "39-ARC-BASELINE.md ## Before: function size, CC, typed-function ratio, companion import sites, module-global setters, duplicated device policy (incl. the quiet-hours fallback difference), suite/coverage numbers"
affects: [39-02, 39-03, 39-04, 39-05, 39-06, 39-07, 39-08, 39-09, 39-10]

tech-stack:
  added: []
  patterns:
    - "Function-size measurement: code lines = tokenize-derived non-blank/non-comment/non-structural lines, minus ast-derived docstring line ranges, over a function's own lineno..end_lineno span (nested defs counted in both outer and inner)"
    - "Detector test loaded via importlib.util.spec_from_file_location, same pattern as test_check_comment_history.py"

key-files:
  created:
    - scripts/check_function_size.py
    - test-support/test_check_function_size.py
    - .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-ARC-BASELINE.md
  modified: []

key-decisions:
  - "Top-5 highest-CC table in the baseline reports non-test functions only (the raw radon command also surfaces test-scenario functions at CC 11-36); the raw command and its full output are still documented so the exclusion is visible, not silent."
  - "Quiet-hours invalid-time fallback difference (server: substitutes 23:00-07:00 defaults and holds; byos: treats as disabled) is recorded verbatim in the baseline as the one intentional behaviour change this phase makes (D-4), not something to fix in this instruments-only plan."

requirements-completed: [ARC-01, ARC-02, ARC-03, ARC-04, ARC-05, ARC-06]

duration: 25min
completed: 2026-09-27
---

# Phase 39 Plan 01: Function-size gate and architecture baseline Summary

**Built a stdlib-only AST/tokenize function-size gate (`check`/`report` subcommands) and used it, plus radon and grep, to record every ARC-01..ARC-06 "Before" number on the unmodified tree ahead of any refactor.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2 completed
- **Files created:** 3 (0 modified)

## Accomplishments

- `scripts/check_function_size.py` measures function size the way ARC-01's success criterion requires (code lines = tokenize tokens minus COMMENT/NL/NEWLINE/INDENT/DEDENT/ENDMARKER, minus docstring line ranges, over each function's own line span, nested defs counted toward both the nested and the enclosing function), with a `check --max N` gate (exit 1 + offender list) and a `report --top N` markdown table.
- `check --max 80 server stub-server` reproduces the research inventory exactly — the same six offenders at the same sizes (`_run_once_locked` 335, `build_parser` 98, `draw_main_text_block` 91, `save_device_config` 87, `pinned_request` 85, `main` 84), out of 365 functions scanned.
- `39-ARC-BASELINE.md` records every number the phase's later plans will need to compare against: `_run_once_locked` CC 53 / `run_once` CC 2 (radon, cross-checked against the AST McCabe count), the top-5 non-test CC functions, 0/318 typed non-test server functions, the companion's three `poll_loop` import sites (`app.py`, `health_page.py`, `airlines_page.py`) plus the test files that will need retargeting, the three module-global setters and their sole production caller (`poll_loop.py:945-950`), the full device-policy duplication table with file:line for every copy, and the whole-suite numbers (2915 passed / 139 skipped / 94.07% coverage, ruff and comment-history guard both clean).

## Task Commits

1. **Task 1: scripts/check_function_size.py and its detector tests** - `ece675b` (feat)
2. **Task 2: 39-ARC-BASELINE.md, Before section, on the unmodified tree** - `bd3ec1d` (docs)

## Files Created/Modified

- `scripts/check_function_size.py` - `code_lines`, `docstring_lines`, `measure_source`, `iter_sources`, `main`; `check`/`report` CLI subcommands
- `test-support/test_check_function_size.py` - 14 tests covering every behavior bullet (statements/docstring/comments/blanks counting, nested-def double-counting, non-first string literals, multi-line expressions, both scope-skip rules, single-file roots, both CLI subcommands, stdlib-only imports)
- `.planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-ARC-BASELINE.md` - the committed "Before" record

## Decisions Made

- The baseline's five-highest-CC table reports non-test functions only, with the raw (unfiltered) command's own test-file outliers named explicitly rather than silently dropped, so a reader can see what was excluded and why.
- No changes were made to production code in this plan — both commits are instruments/docs only, verified by `git log --name-only` showing no path under `server/`, `companion/`, `stub-server/` or `deploy/`.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were verified directly:
- `check --max 80 server stub-server` and `check --max 400 server stub-server` produce the exact exit codes and offender list the plan specified.
- `39-ARC-BASELINE.md` has exactly one `## Before` and one `## After` line (verified with `grep -c`), and both commits touch only their own file (`git log --name-only`).

## Known Stubs

None.

## Threat Flags

None — this plan added a dev-only static-analysis script and a documentation file; no new network endpoint, auth path, file-access pattern or schema change.

## Self-Check: PASSED

- FOUND: scripts/check_function_size.py
- FOUND: test-support/test_check_function_size.py
- FOUND: .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-ARC-BASELINE.md
- FOUND commit: ece675b
- FOUND commit: bd3ec1d
