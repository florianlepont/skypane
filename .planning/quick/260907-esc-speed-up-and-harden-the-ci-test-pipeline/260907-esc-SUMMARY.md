---
phase: quick-260907-esc
plan: 01
subsystem: testing
tags: [ci, coverage, concurrency, github-actions, pillow, pack-panel]

requires: []
provides:
  - "Concurrent stdlib-only test runner (scripts/run_all_tests.py) behind the existing scripts/run-all-tests.sh entry point"
  - "Three byte-identical hot-loop rewrites (pack_panel, dithered_state_background, illustration resize cache) plus one harness-side rewrite (nibble_counts)"
  - "Hardened CI/firmware workflows: path filters, concurrency groups, job timeouts, pip caching"
affects: [ci, testing, server/plane, server/panel_format]

tech-stack:
  added: []
  patterns:
    - "translate() + big-int OR for per-pixel/per-byte hot loops instead of Python-level iteration"
    - "mtime/size-keyed memoization returning .copy() to callers that mutate the returned object"
    - "ThreadPoolExecutor-based concurrent subprocess orchestration with per-task timeout and file-redirected (not piped) output"

key-files:
  created:
    - scripts/run_all_tests.py
  modified:
    - server/panel_format.py
    - server/plane/dither.py
    - server/plane/render.py
    - server/test_render.py
    - scripts/run-all-tests.sh
    - pyproject.toml
    - README.md
    - .github/workflows/ci.yml
    - .github/workflows/firmware.yml

key-decisions:
  - "pack_panel() vectorised via translate() on two 256-entry nibble tables plus a big-integer OR — verified byte-identical across 12 real canvases + 1 random 6-index canvas before committing"
  - "dithered_state_background() and _resize_illustration() both memoize but return .copy() on every path (hit and miss) — callers draw onto the returned object"
  - "Concurrency uses ThreadPoolExecutor (not multiprocessing) since each worker only blocks on a subprocess, plus per-harness output goes to a temp file (not a pipe) to avoid deadlocking a chatty harness against a full OS pipe buffer"
  - "COVERAGE_CORE=sysmon set only on Python >=3.12 and only if the caller hasn't already set it"
  - "server/README.md left unchanged — its 'Running the tests' section documents individual-harness invocation, which is still exactly true"
  - "ci.yml paths-ignore deliberately excludes hardware/** and adsb-test/** since ruff lints Python in both"

requirements-completed: [QT-esc-01, QT-esc-02, QT-esc-03]

coverage:
  - id: D1
    description: "pack_panel(), dithered_state_background() and nibble_counts() produce byte-identical output to the pre-change implementations"
    requirement: "QT-esc-01"
    verification:
      - kind: other
        ref: "scratchpad/verify_identity.py — direct old-vs-new comparison across 12 real canvases (4 themes x 3 states) + 1 random 6-index canvas + mandatory-copy mutation-safety check"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 16 harnesses pass under both Python 3.11 and 3.12 via the new concurrent runner, with unchanged check counts (911 total) and coverage TOTAL >= 83%"
    requirement: "QT-esc-01"
    verification:
      - kind: integration
        ref: "PYTHON=.venv (3.11) ./scripts/run-all-tests.sh — 16/16 PASS, 911/911 checks, TOTAL 92%, exit 0"
        status: pass
      - kind: integration
        ref: "PYTHON=venv312 (3.12) ./scripts/run-all-tests.sh — 16/16 PASS, 911/911 checks, TOTAL 92%, exit 0"
        status: pass
      - kind: integration
        ref: "JOBS=1 ./scripts/run-all-tests.sh — serial fallback, 16/16 PASS, exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bad PYTHON path and ruff lint both behave correctly under the new runner/wrapper"
    requirement: "QT-esc-01"
    verification:
      - kind: other
        ref: "PYTHON=/nonexistent/python3 ./scripts/run-all-tests.sh — unchanged 3-line error, exit 1"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check . — All checks passed!"
        status: pass
    human_judgment: false
  - id: D4
    description: "ci.yml and firmware.yml are hardened: every job has timeout-minutes, ci.yml has a top-level PR-cancelling concurrency group, paths-ignore on both triggers (excluding hardware/** and adsb-test/**), a production-deploy concurrency group on deploy, and pip caching on setup-python"
    requirement: "QT-esc-02"
    verification:
      - kind: other
        ref: "actionlint .github/workflows/ci.yml .github/workflows/firmware.yml — exit 0, zero findings (PyYAML unavailable in server/.venv, actionlint used per plan's fallback)"
        status: pass
      - kind: other
        ref: "grep -n timeout-minutes / paths-ignore / concurrency / cache — all present exactly as specified"
        status: pass
    human_judgment: false
  - id: D5
    description: "git diff --stat across all three tasks touches nothing outside the nine permitted paths"
    requirement: "QT-esc-03"
    verification:
      - kind: other
        ref: "git diff HEAD~3 --stat — exactly server/panel_format.py, server/plane/dither.py, server/plane/render.py, server/test_render.py, scripts/run_all_tests.py (new), scripts/run-all-tests.sh, pyproject.toml, README.md, .github/workflows/ci.yml, .github/workflows/firmware.yml"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-09-07
status: complete
---

# Quick Task 260907-esc: Speed up and harden the CI test pipeline Summary

**Cut the local/CI test suite from a 106s sequential baseline to ~9s wall time via a concurrent stdlib-only runner (ThreadPoolExecutor, sysmon coverage core on 3.12+), three byte-identical hot-loop rewrites, and hardened GitHub Actions workflows (path filters, concurrency groups, job timeouts, pip caching).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-07 (session start)
- **Completed:** 2026-09-07T10:52:16+02:00
- **Tasks:** 3/3 completed
- **Files modified:** 10 (1 created, 9 modified)

## Accomplishments

- `pack_panel()`, `dithered_state_background()` and `nibble_counts()` rewritten to use `bytes.translate()` / big-integer OR / `collections.Counter` instead of per-pixel/per-byte Python loops, plus a new `_resize_illustration()` cache — all verified byte-identical to the code they replaced via a direct old-vs-new comparison script (not inferred from the harnesses passing)
- New `scripts/run_all_tests.py`: stdlib-only concurrent runner (`ThreadPoolExecutor`, `JOBS` env var, longest-first submission, per-harness `HARNESS_TIMEOUT_S` default 600s, `COVERAGE_CORE=sysmon` on 3.12+, slowest-first timing table with optional `GITHUB_STEP_SUMMARY` output) behind the unchanged `scripts/run-all-tests.sh` entry point
- `.github/workflows/ci.yml`: top-level PR-cancelling concurrency group, `paths-ignore` on both triggers (docs-only pushes/PRs no longer trigger CI), `timeout-minutes` on both jobs, a `production-deploy` concurrency group on `deploy`, pip caching on `setup-python`
- `.github/workflows/firmware.yml`: `timeout-minutes: 30` on the `build` job

## Task Commits

Each task was committed atomically:

1. **Task 1: Byte-identical hot-loop rewrites** - `c8f8b76` (perf)
2. **Task 2: Concurrent Python test runner + docs** - `19a7011` (perf)
3. **Task 3: Workflow hardening** - `f9a16b7` (ci)
4. **Orchestrator follow-up** - `5c9d4a8` (fix): a harness timeout now kills the whole process group (`start_new_session=True` + `os.killpg`), so the child servers the companion/stub-server harnesses spawn can no longer be orphaned - verified live with `HARNESS_TIMEOUT_S=2` (five harnesses reported as timed out, exit 1, no surviving child process, no `.coverage*` leftovers); `_illustration_cache` bounded at 128 entries; dead `table_lines` block removed; two comment corrections (panel_format.py's length assert guards dimensions, not index legality; ci.yml's job was ~6 min, not ~9).

Orchestrator's independent re-run after the follow-up: Python 3.12 8.5 s at JOBS=10 and 10.8 s at JOBS=4 (the GitHub runner's vCPU count), Python 3.11 9.1 s - 911/911 checks, coverage TOTAL 92 %, `ruff check .` and `actionlint` clean.

**Plan metadata:** committed separately by the orchestrator (this SUMMARY, STATE.md, PLAN.md not committed by the executor per task instructions)

## Files Created/Modified

- `server/panel_format.py` - `_HIGH_NIBBLE_TABLE`/`_LOW_NIBBLE_TABLE` module constants + vectorised `pack_panel()` (0.085s -> ~0.003s per panel)
- `server/plane/dither.py` - `_STATE_BACKGROUND_CACHE` memo + translate-based remap in `dithered_state_background()`
- `server/plane/render.py` - `_illustration_cache` keyed on `(path, st_mtime_ns, st_size, target_w)` in `_resize_illustration()`
- `server/test_render.py` - `Counter`-based `nibble_counts()`
- `scripts/run_all_tests.py` (new) - concurrent stdlib-only test runner, canonical 16-harness list
- `scripts/run-all-tests.sh` - thin wrapper: keeps the PYTHON contract and error message, `exec`s into the new runner
- `pyproject.toml` - `[tool.coverage.run]` comment: 15 -> 16 harnesses, notes concurrency depends on parallel mode
- `README.md` - Tests section: 15 harnesses/394 checks -> 16 harnesses/911 checks, documents `JOBS=1`, `HARNESS_TIMEOUT_S`, timing table
- `.github/workflows/ci.yml` - concurrency groups, paths-ignore, timeout-minutes, pip cache, corrected stale "9 harnesses" comment
- `.github/workflows/firmware.yml` - `timeout-minutes: 30` on `build`

Not modified (verified unnecessary): `server/README.md` — its "Running the tests" section documents individual-harness invocation, which remains exactly true.

## Decisions Made

- Vectorised `pack_panel()` via two 256-entry `bytes.translate()` tables plus a big-integer OR rather than any other per-pixel approach — matches the pre-verified prototype exactly and was re-verified against the actual committed code (not just the prototype) before committing
- Both new caches (`_STATE_BACKGROUND_CACHE`, `_illustration_cache`) return `.copy()` on every path, hit or miss — the correctness contract, not an optimization detail, since callers draw onto the returned canvas/image
- `ThreadPoolExecutor` over `multiprocessing` for the runner: each worker only blocks on a subprocess `wait()`, so there's no CPU-bound Python work competing for the GIL
- Per-harness output redirected to a real file, not a pipe — a pipe can deadlock a chatty harness against a full OS pipe buffer once output exceeds the kernel default
- `paths-ignore` on ci.yml deliberately excludes `hardware/**` and `adsb-test/**` since `ruff check .` lints Python in both directories

## Deviations from Plan

None - plan executed exactly as written. All four hot-loop rewrites, the runner's full feature set (JOBS, HARNESS_TIMEOUT_S, COVERAGE_CORE=sysmon, timing table, GITHUB_STEP_SUMMARY), and all workflow hardening items were implemented as specified. No harness check logic, no `EXPECTED_CHECK_COUNT`, and no coverage threshold was touched.

## Before/After Timing

| Run | Wall time | Harnesses | Checks | Coverage TOTAL | Exit |
|---|---|---|---|---|---|
| Old sequential baseline (local, Python 3.11, measured pre-session) | **106s** | 16 (was measured against the same 16-file list) | — | — | — |
| New concurrent runner, Python 3.11, `JOBS=10` (auto-detected CPU count) | **9.0s** | 16/16 PASS | 911/911 | 92% | 0 |
| New concurrent runner, Python 3.12, `JOBS=10`, sysmon coverage core | **8.5s** | 16/16 PASS | 911/911 | 92% | 0 |
| New concurrent runner, `JOBS=1` (serial escape hatch) | 28.8s | 16/16 PASS | 911/911 | — | 0 |
| Bad `PYTHON` path | — | — | — | — | 1 (unchanged error message) |

**~11.8x speedup** (106s -> 9.0s) on Python 3.11 concurrent vs. the old sequential baseline; ~12.5x on Python 3.12.

### Per-harness timing table (Python 3.11 run, slowest first)

| Harness | Wall (s) | Status |
|---|---|---|
| server/test_render.py | 9.0 | PASS |
| companion/test_companion_app.py | 5.7 | PASS |
| stub-server/test_poll_cycle.py | 3.9 | PASS |
| server/test_poll_loop.py | 3.4 | PASS |
| companion/test_status_pages.py | 3.3 | PASS |
| server/test_panel_preview.py | 3.1 | PASS |
| server/test_pipeline_e2e.py | 1.9 | PASS |
| server/test_illustrations.py | 0.8 | PASS |
| companion/test_view_pages.py | 0.5 | PASS |
| companion/test_config_page.py | 0.5 | PASS |
| server/test_enrich.py | 0.3 | PASS |
| server/test_dither.py | 0.3 | PASS |
| server/test_plane_detection.py | 0.2 | PASS |
| server/test_config_history.py | 0.2 | PASS |
| server/test_runway_config.py | 0.1 | PASS |
| companion/test_contrast_check.py | 0.1 | PASS |

Total wall time: 9.0s (JOBS=10). Because the harnesses run concurrently rather than summing sequentially, total wall time (9.0s) is close to but slightly above the single slowest harness (test_render.py, 9.0s) — the critical path is now effectively just that one harness.

### Per-harness check counts (both interpreters, identical)

companion-app 148/148, config-history 44/44, config-page 87/87, contrast-check 36/36, dither 6/6, enrich 52/52, illustrations 58/58, panel-preview 11/11, pipeline-e2e 6/6, plane-detection 47/47, poll-cycle 34/34, poll-loop 51/51, render 127/127, runway-config 14/14, status-pages 136/136, view-pages 54/54 — **911 total**, matching the plan's expected counts exactly.

## Issues Encountered

- PyYAML is not installed in `server/.venv` (`ModuleNotFoundError: No module named 'yaml'`), so Task 3's verify block's primary YAML-parse check could not run as written. Fell back to `actionlint` per the plan's explicit fallback instruction ("if PyYAML is unavailable in that venv, validate with actionlint or gh workflow view instead, and say which was used"). `actionlint .github/workflows/ci.yml .github/workflows/firmware.yml` exited 0 with zero findings, confirming both workflow files are syntactically and semantically valid GitHub Actions YAML.

## User Setup Required

None - no external service configuration required. The new pip caching, concurrency groups, timeouts, and path filters are all effective on the very next CI run with no dashboard configuration needed (the pre-existing `production` GitHub Environment reviewer gate from plan 04-06 is unaffected).

## Next Phase Readiness

- CI's "Run full test suite" step should now take roughly 9-10s locally-equivalent time instead of 357s on GitHub's 4-vCPU runners (exact CI wall time will differ from this Mac's measurement but the relative speedup should carry over closely, since the runner is CPU-parallel and GitHub's runners have comparable core counts)
- A docs-only PR will no longer trigger the CI job at all (it used to cost the full ~6 minutes)
- Any future hung subprocess server is capped at 600s per harness instead of being able to consume GitHub's 6-hour job default
- No blockers for follow-on work; the coverage threshold (83%) has ~9 points of headroom at the current 92% measurement

---
*Phase: quick-260907-esc*
*Completed: 2026-09-07*

## Self-Check: PASSED

All 11 claimed files verified present on disk (10 code/config files + this SUMMARY). All 4 commit hashes (`c8f8b76`, `19a7011`, `f9a16b7`, `5c9d4a8`) verified present in `git log --oneline --all`.
