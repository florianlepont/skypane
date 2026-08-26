---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
plan: 02
subsystem: testing
tags: [ruff, coverage, pytest-free-harnesses, pyproject-toml, shell, ci-gate]

# Dependency graph
requires:
  - phase: 04-01
    provides: repo-root .gitignore (already covering .ruff_cache/, .coverage, .coverage.*) and a clean, history-scrubbed working tree
provides:
  - server/requirements-dev.txt pinning ruff==0.16.4 and coverage==7.15.4, provenance-verified, separate from production deps
  - repo-root pyproject.toml with [tool.ruff] (select E4,E7,E9,F; ignore E402 for the 8 documented sys.path bootstraps) and [tool.coverage] (parallel mode, server+stub-server scope, 75% fail_under)
  - scripts/run-all-tests.sh - the single canonical entry point running all 9 harnesses under coverage, combining and enforcing the threshold
affects: [04-04 (CI workflow calls this script), 04-05 (README tells contributors to run this script)]

# Tech tracking
tech-stack:
  added: [ruff 0.16.4, coverage.py 7.15.4]
  patterns: [dev-only tooling pinned separately from production requirements.txt so deploy.sh never installs it on the VPS; single shell entry point as the one source of truth for the test-file list, referenced by both local dev and CI rather than restated]

key-files:
  created:
    - server/requirements-dev.txt
    - pyproject.toml
    - scripts/run-all-tests.sh
  modified: []

key-decisions:
  - "Ruff lint restricted to E4,E7,E9,F (correctness-only) rather than defaults - unconfigured ruleset reports 397 findings, 328 of them UP031 printf-formatting used consistently and deliberately across the codebase"
  - "E402 ignored repo-wide (not code-fixed) for the 8 findings, all the project's documented sys.path bootstrap blocks in poll_loop.py/render.py/enrich.py that enable direct script execution"
  - "Coverage threshold set to 75, four points below the measured 79% production-only baseline (server+stub-server scope, harnesses and the two subprocess-launched stub-server scripts omitted)"
  - "scripts/run-all-tests.sh does not use set -e for its test loop so a single failing harness doesn't hide the rest of the run's results"

patterns-established:
  - "One canonical 9-file harness list lives in scripts/run-all-tests.sh with a comment marking CONTEXT.md's D-07 list as known-stale, so CI (04-04) and README (04-05) both defer to it instead of re-enumerating"
  - "Coverage threshold and scope live only in pyproject.toml; the runner script reads them implicitly via `coverage report`/`coverage run`, never restating the number"

requirements-completed: [D-07, D-08, D-09]

coverage:
  - id: D1
    description: "server/requirements-dev.txt pins ruff and coverage separately from production deps, provenance-verified against upstream repos"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "pip install + importlib.metadata provenance assertion (Task 1 verify block)"
        status: pass
    human_judgment: false
  - id: D2
    description: "pyproject.toml configures ruff (green on unmodified codebase) and coverage (scoped, parallel, 75% threshold derived from measurement)"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "ruff check . exit 0 + tomllib config assertions (Task 2 verify block)"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/run-all-tests.sh runs all 9 harnesses, aggregates coverage, enforces the pyproject.toml threshold, demonstrated to fail when threshold is exceeded"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "./scripts/run-all-tests.sh (9/9 checks-pass lines, exit 0); invoked from /tmp (exit 0); fail_under=100 override (exit 1, restored)"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-08-26
status: complete
---

# Phase 04 Plan 02: Local Quality Baseline (Lint + Coverage + Test Runner) Summary

**Repo-root pyproject.toml pins Ruff to a correctness-only ruleset (E4/E7/E9/F, green on the untouched codebase) and scopes coverage.py to server+stub-server with a 75% threshold measured 4 points below the real 79% baseline; scripts/run-all-tests.sh is the one command that runs all 9 harnesses, combines parallel coverage data, and enforces that threshold for both contributors and CI.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-26T19:13:06Z
- **Completed:** 2026-08-26T19:17:57Z
- **Tasks:** 3
- **Files modified:** 3 (all new)

## Accomplishments

- `server/requirements-dev.txt` pins `ruff==0.16.4` and `coverage==7.15.4`, mirroring `server/requirements.txt`'s one-package-per-line `==` convention; both packages' installed metadata verified to resolve to their genuine upstream projects (`astral-sh/ruff`, `coveragepy/coveragepy`), closing 04-RESEARCH.md's open legitimacy item.
- Repo-root `pyproject.toml` carries `[tool.ruff]`/`[tool.coverage]` config only (deliberately no `[project]` table — this is a deployed app, not a distribution). Ruff's selected rule set (`E4,E7,E9,F`) is green with zero findings against the untouched codebase; `E402` is ignored repo-wide with a written rationale (the 8 findings are the documented `sys.path` bootstrap blocks that make direct script execution work). Coverage is scoped to `server` + `stub-server`, runs in parallel mode (never combined with `append` — confirmed mutually exclusive, M2), omits the 9 test harnesses and the two subprocess-launched `stub-server/` scripts, and fails under 75%.
- `scripts/run-all-tests.sh` runs all 9 harnesses (the M1-measured list, explicitly marked as superseding CONTEXT.md's stale 7-file D-07 enumeration), continues through failures to report the full picture, combines parallel coverage data, and enforces the `pyproject.toml` threshold without restating it. Self-locating (works from any cwd), overridable interpreter via `PYTHON` env var, executable, and leaves no stray coverage files behind.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin CI-only tooling in a separate dev requirements file** - `61e14ac` (feat)
2. **Task 2: Lint and coverage configuration, green by measurement** - `50e86c9` (feat)
3. **Task 3: One command that runs the whole suite, for contributors and CI alike** - `82510d9` (feat)

_Note: no TDD tasks in this plan._

## Files Created/Modified

- `server/requirements-dev.txt` - Two `==`-pinned dev-only packages (ruff, coverage), separate from production requirements so `deploy/deploy.sh` never installs them onto the VPS
- `pyproject.toml` - `[tool.ruff]` (correctness-only selected rules, E402 suppressed with rationale) and `[tool.coverage]` (parallel mode, scoped source/omit, `fail_under = 75` with its derivation recorded in a comment)
- `scripts/run-all-tests.sh` - Executable, canonical 9-harness runner; single source of truth for CI (04-04) and README (04-05)

## Decisions Made

- Restricted Ruff's selected rule set to `E4,E7,E9,F` instead of the tool's evolving defaults, because the unconfigured ruleset reports 397 findings (328 `UP031` printf-formatting) against a codebase that uses that idiom consistently and correctly — rewriting 328 working call sites would be pure change-risk with no correctness benefit.
- Suppressed `E402` repo-wide (not code-fixed) for the 8 findings, all of which are the project's documented `sys.path` bootstrap blocks enabling direct script execution — the exact invocation style `server/README.md` prescribes for the whole test suite.
- Set the coverage failure threshold to 75, four points below the measured 79% production-only baseline under this exact `source`/`omit` scope — tight enough to catch a real regression, loose enough that a legitimate refactor shifting a few statements doesn't red-line the build.
- `scripts/run-all-tests.sh` deliberately does not use `set -e` for its harness loop, so one failing test doesn't hide the results of the other 8 in the same run.

## Deviations from Plan

None - plan executed exactly as written. All measured figures in `<planner_findings>` (9-file list, 8 `E402` findings, 79% baseline) were independently re-confirmed live during execution rather than taken on faith, and matched exactly.

## Issues Encountered

None. The only notable runtime artifact was a non-fatal `coverage` `CoverageWarning: No data was collected` for `stub-server/test_poll_cycle.py`'s own coverage-run invocation (that harness file itself is in the omit list and its subprocess-launched server isn't instrumented) — expected given M5's stated scope, does not affect exit code or the aggregated report.

## Gate-Failure Evidence (T-04-02-03)

Demonstrated the blocking gate actually gates, per Task 3's acceptance criteria:

1. Ran `./scripts/run-all-tests.sh` normally: exit 0, 9/9 "checks pass" lines, coverage report shows `TOTAL ... 79%`.
2. Temporarily edited `pyproject.toml`'s `fail_under` from `75` to `100`.
3. Re-ran the script: `coverage report` printed `Coverage failure: total of 79 is less than fail-under=100`, script exited 1 (`FAIL`).
4. Restored `pyproject.toml` from the pre-edit backup; `diff` against `git show HEAD:pyproject.toml` confirmed byte-identical restoration.
5. Re-ran the script once more: exit 0, `PASS`, confirming the restore didn't leave the config in a broken state.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `scripts/run-all-tests.sh` is ready for plan 04-04's CI workflow to call directly (no file-list restatement needed) and for plan 04-05's README to reference as the one contributor-facing test command.
- `pyproject.toml`'s coverage scope/threshold is the traceability anchor for any future coverage discussion — changing `source`/`omit` invalidates the recorded 79%/75 pairing per the in-file comment.
- Production dependency pins (`server/requirements.txt`) are confirmed byte-identical to their pre-plan content; nothing in this plan can reach the VPS through the deploy path.

---
*Phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created files confirmed present on disk; all three task commit hashes (61e14ac, 50e86c9, 82510d9) confirmed present in git log.
