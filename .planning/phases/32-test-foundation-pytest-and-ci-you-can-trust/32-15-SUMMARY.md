---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 15
subsystem: testing
tags: [pytest-cov, coverage, subprocess-coverage, python3.14, documentation]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    plan: "13"
    provides: "pytest-cov + `patch = [\"subprocess\"]` subprocess coverage measurement, proven live"
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    plan: "14"
    provides: "CI running Python 3.14 with a hash-locked server/requirements-dev.txt install"
provides:
  - "companion/app.py, stub-server/byos_server.py and stub-server/make_test_panel.py measured
     (57%, 54%, 98%) instead of omitted at a permanent 0%"
  - "fail_under raised from 83 to 88 (the measured floor, no margin), documented in pyproject.toml
     with the measurement command, interpreter and date"
  - "CLAUDE.md, CONTRIBUTING.md, README.md and server/README.md describing pytest as the way to
     run tests and Python 3.14 as the target"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Coverage floor measured as a single non-root run (`runuser -u nobody`) on both the CI
       interpreter (a scratch CPython 3.14 venv, hash-locked install) and the repo's own dev venv,
       cross-checked for agreement before trusting the number"

key-files:
  created: []
  modified:
    - pyproject.toml
    - .claude/CLAUDE.md
    - CONTRIBUTING.md
    - README.md
    - server/README.md
    - deploy/provision.sh

key-decisions:
  - "fail_under set to 88 (floor(88.11%)), not a 4-point-margin derivation like the prior 83 —
     TST-09 explicitly calls for the measured floor with no margin"
  - "Coverage measured as a non-root user (runuser -u nobody), not root, because 3 tests
     (permission-bit checks) skip under root and pass under non-root, and GitHub CI runners are
     non-root; a root measurement would have under-counted by 3 tests without changing the
     percentage materially, but would not match what CI actually gates on"
  - "Built the 3.14 scratch venv's own Python install in a world-readable location (/opt/cpython314,
     copied from the sandbox's root-only ~/.local/share/uv/python store) because uv's default venv
     symlinks to a directory nobody could traverse into, which silently made every invocation as
     nobody report \"interpreter not found\" — not an installation problem, a permissions one"
  - "stub-server/devices_cli.py (added by Phase 34's merge into this branch) was left out of the
     omit list untouched — it was never in omit to begin with and already measures at 86%, so this
     plan's scope (the three explicitly-named files) needed no adjustment for it"

requirements-completed: [TST-09, TST-01, TST-04]

# Metrics
duration: ~35min
completed: 2026-09-23
---

# Phase 32 Plan 15: Subprocess-measured coverage floor; pytest and Python 3.14 documentation Summary

**Removed the three subprocess-launched files from the coverage omit list now that `patch = ["subprocess"]` measures them directly, raised `fail_under` from 83 to the measured floor of 88 (no margin, confirmed identical — 88.11% — on both a hash-locked CPython 3.14.0rc2 scratch venv and this repo's CPython 3.11.15 dev venv, both non-root), and rewrote CLAUDE.md/README/CONTRIBUTING/server-README/provision.sh to describe pytest and Python 3.14 as the project's actual test tooling and target interpreter.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-23T18:11Z
- **Tasks:** 2/2 completed
- **Files modified:** 6

## Accomplishments
- `[tool.coverage.run] omit` in `pyproject.toml` shrunk from six entries (three `test_*.py` globs plus `companion/app.py`, `stub-server/byos_server.py`, `stub-server/make_test_panel.py`) to the three `test_*.py` globs only — the three subprocess-launched files are now measured in-scope.
- Built a scratch Python 3.14 venv (`uv venv --python 3.14 --seed`, `pip install --require-hashes -r server/requirements-dev.txt`) against `cpython-3.14.0rc2`, the same interpreter CI's `setup-python: '3.14'` resolves to — all packages, including Playwright, installed cleanly with hashes verified.
- Ran the full suite (`./scripts/run-all-tests.sh --cov-report=term-missing`) as a non-root user on both interpreters:
  - CPython 3.14.0rc2 (scratch venv): **768 passed**, exit 0, **88.11%** total coverage.
  - CPython 3.11.15 (`server/.venv`): **768 passed**, exit 0, **88.11%** total coverage (identical).
  - `companion/app.py` 57%, `stub-server/byos_server.py` 54%, `stub-server/make_test_panel.py` 98% — all now measured with real, non-trivial route-body coverage (companion/app.py was ~21% import-only under the old omit rationale).
- `fail_under` raised from 83 to **88** — the measured total rounded down, no margin — with the derivation comment rewritten to name the measurement command, both interpreters, the date, and the "changing source/omit invalidates this number" rule.
- Rewrote `.claude/CLAUDE.md`'s Server row (Python 3.12 → 3.14) and Tests / CI row (pytest + pytest-xdist + pytest-cov, the pytest-socket guard, the companion legacy-harness shim, coverage gate, Playwright shell, hash-locked requirements, firmware host tests) — exactly the two table rows named in scope, nothing else in the file touched.
- Rewrote `README.md` ("Requires Python 3.12" → "Requires Python 3.14"; `--require-hashes` install lines; a dev-superset install line for `server/requirements-dev.txt`; the Tests section rewritten to describe `pytest -n auto --cov` instead of "There is no pytest").
- Rewrote `server/README.md`'s "Running the tests" section for pytest, with `--require-hashes` on both install commands.
- Rewrote `CONTRIBUTING.md`'s "Before you start" section: Python 3.14 + `--require-hashes` setup, running a pytest subset, the no-network rule and `fake_providers` fixture, and `scripts/lock-deps.sh` for dependency changes.
- `deploy/provision.sh`: comment-only edit removing the stale "CPython 3.12" reference (`bash -n` confirms no code changed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Subprocess-measured coverage on Python 3.14; fail_under at the measured floor** - `5ba95e9` (feat)
2. **Task 2: Documentation — pytest and Python 3.14** - `640c457` (docs)

**Plan metadata:** committed together with this SUMMARY (see below)

## Files Created/Modified
- `pyproject.toml` - `omit` list shrunk to the three `test_*.py` globs; `fail_under` 83 → 88 with a rewritten derivation comment
- `.claude/CLAUDE.md` - Server row → Python 3.14; Tests / CI row → pytest stack description
- `CONTRIBUTING.md` - pytest setup/run/subset instructions, no-network rule, lock regeneration
- `README.md` - Python 3.14 requirement, `--require-hashes` installs, pytest-based Tests section
- `server/README.md` - "Running the tests" rewritten for pytest, `--require-hashes` installs
- `deploy/provision.sh` - one comment updated (no code change; `bash -n` verified)

## Decisions Made
- Measured the coverage floor as a **non-root** user (`runuser -u nobody`), matching GitHub CI's non-root runner, rather than the sandbox's default root shell — root silently skips 3 permission-bit tests (`server/test_manual_resolutions.py`, `server/test_poll_loop.py`) that pass under non-root, and running the whole suite as root also surfaces 2 pre-existing, unrelated root-sandbox failures in the legacy companion shim (`test_status_pages`, `test_companion_app`) documented before this plan started. Confirmed a root run (3.11, `server/.venv`) still reports the coverage gate itself passing (`Required test coverage of 88.0% reached. Total coverage: 88.03%`) even though the run exits 1 overall on those 2 known failures — not a regression from this plan.
- The 3.14 scratch venv's own interpreter had to be copied out of the sandbox's `/root/.local/share/uv/python/` store into a world-readable `/opt/cpython314` before `runuser -u nobody` could execute it — `uv venv --seed` produces a symlink chain rooted under `/root`, which `nobody` cannot traverse (`drwx------`). This is an environment-specific fix to make the non-root measurement possible, not a change to any tracked file; the scratch venv and `/opt/cpython314` were both removed after measuring, per the plan's own instruction.
- `fail_under` set to the measured floor with **no margin** (88, not e.g. 84), per TST-09's explicit decision — the prior 83 had a documented 4-point margin under the smaller (six-entry) omit scope; that margin discipline does not carry forward once the scope and the decision both changed.

## Deviations from Plan

None — plan executed exactly as written. The `/opt/cpython314` interpreter relocation and the choice to measure non-root are both implementation details of "build the 3.14 scratch venv" and "run the full suite" already specified by the plan and the orchestrator's environment notes, not departures from it.

## Issues Encountered
- `uv venv --python 3.14 --seed <path>` under the sandbox's default root shell created a venv whose `python3` symlink resolves through `/root/.local/share/uv/python/cpython-3.14.0rc2-linux-x86_64-gnu/bin/python3.14` — a path `nobody` cannot traverse (`/root` is `0700`). The first `runuser -u nobody -- ... PYTHON=<scratch venv>` attempt failed with `scripts/run-all-tests.sh`'s own "interpreter not found or not executable" error, which looked like a missing-venv problem but was actually a traversal-permission problem one level down the symlink chain. Resolved by copying the interpreter tree to `/opt/cpython314` (`chmod -R a+rX`) and rebuilding the venv against that copy.
- The scratchpad temp directory (`/tmp/claude-0/.../scratchpad/`) also turned out to be `0700` per-segment, so an initial scratch venv built there was equally unreachable by `nobody`; moved the scratch venv to `/tmp/skypane-scratch314` (world-traversable `/tmp`) instead.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TST-09 is complete: the coverage floor is measured on the CI interpreter with subprocess coverage live, and the gate only ratchets up from here.
- TST-01 and TST-04's remaining documentation halves are complete: CLAUDE.md, CONTRIBUTING, README and server/README all describe pytest and Python 3.14 consistently. Both requirements now span only completed plans (32-01 provided the pytest infrastructure/CI-version halves; this plan closes the documentation halves), so both are marked complete alongside TST-09.
- This closes out Phase 32's server-side pytest foundation. Phase 33 (per 32-CONTEXT.md's stated boundary) picks up: migrating the remaining hand-rolled `companion/test_*.py` harnesses to real pytest tests, the single app-server fixture, pytest-playwright, source-text assertion cleanup, root-safety of companion tests, retiring companion `EXPECTED_CHECK_COUNT`s, and the 2018-check parity close-out (TST-10..TST-15).
- No blockers. `fail_under = 88` is a genuine floor now — any future plan that adds untested code to `server/`, `stub-server/` or `companion/` will trip the gate rather than silently pass under the old, looser 83.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 6 claimed modified files confirmed present on disk (`pyproject.toml`, `.claude/CLAUDE.md`,
`CONTRIBUTING.md`, `README.md`, `server/README.md`, `deploy/provision.sh`); this SUMMARY file
confirmed present; both task commit hashes (`5ba95e9`, `640c457`) confirmed in `git log --oneline --all`.
