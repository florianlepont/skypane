---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 33
subsystem: testing
tags: [pytest, ledger, parity, coverage, root-safety, non-root]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "32"
    provides: "no transition machinery left, a strict guard, 33-ledger-check.py --all at 0 pending"
provides:
  - "33-MIGRATION-LEDGER.md assembled from the 9 fragments (phase33_total=1250: 1238 ported, 12 deleted, 0 pending) with a Closing parity section reconciling 769 + 1250 = 2019 to the audit's 2018 (+1 = 17d5bc7, verified per harness against git)"
  - "coverage measured non-root on the CI interpreter: 93.38% vs the pre-migration tree's 93.35%, same method; fail_under stays 93 with the derivation comment updated"
  - "the one line that lost coverage in the migration (home_page.py's arriving branch) covered again by an HTTP behaviour test"
  - "root and nobody full runs green, with git status clean and /nonexistent unchanged after each"
  - "TST-10..TST-15 marked complete"
affects: ["35", "36"]

tech-stack:
  added: []
  patterns:
    - "Per-file coverage parity: run the pre-migration tree and HEAD the same way (nobody, 3.14, hash-locked venvs), export coverage JSON and diff the missing-line sets per file, not just TOTAL"

key-files:
  created:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-33-SUMMARY.md
  modified:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-MIGRATION-LEDGER.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger-check.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-FOLLOWUPS.md
    - companion/test_companion_app_04b.py
    - pyproject.toml
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/STATE.md

key-decisions:
  - "Coverage parity is judged like for like: nobody, CPython 3.14.0rc2, hash-locked venv, full run with no extra arguments. That is how the recorded 93.35% was measured, and re-running the pre-migration tree (d2c53a0) that way reproduced 93.35% exactly. The root/3.11 figure (93.26%) is lower only because 5 requires_non_root tests skip under euid 0."
  - "fail_under stays 93. The measurement (93.38%) rounds down to the same floor; source/omit/patch/sigterm are untouched."
  - "Task 3 (push, draft PR, watch CI, CI-evidence section) was not run: the orchestrator's rule is never to push. CI evidence is left to the orchestrator's push."
  - "Playwright's leftover empty temp dirs in /tmp (F-03) predate Phase 33 and are created by Playwright's Node driver, not by a path any test chooses. TST-13 is marked complete on its requirement text; the leftover dirs are recorded as an open follow-up rather than silently absorbed."

requirements-completed: [TST-10, TST-11, TST-12, TST-13, TST-14, TST-15]

duration: ~50min
completed: 2026-09-25
---

# Phase 33 Plan 33: Closing parity, coverage and root/non-root proof

**The migration ledger is assembled: 1250 companion checks, 1238 ported and 12 deleted with rubric codes. With Phase 32's 769 that makes 2019, which is the audit's 2018 plus exactly one check added later by `17d5bc7`. Coverage on a non-root run of the CI interpreter is 93.38%, against 93.35% for the pre-migration tree measured the same way. The one line the migration stopped covering is covered again by a behaviour test. The suite passes as root and as `nobody`, and neither run writes to the repo or `/nonexistent`.**

## Performance

- **Duration:** ~50 min (started 2026-09-25T02:30Z, completed 03:20Z). This includes 6 full-suite runs of about 5 min each: 3 as nobody on HEAD, 1 as nobody on the pre-migration tree, 2 as root.
- **Tasks:** 2 of 3 plan tasks executed. Task 3 is deferred to the orchestrator (see Deviations).
- **Commits:** 3 task commits plus this metadata commit.

## Task 1: ledger and closing parity

- `33-ledger-check.py --all` exited 0 with 0 pending rows. `--assemble` printed `phase33_total=1250`.
- The first `--assemble` truncated the ledger header. Fix and self-test described under Deviations.
- Closing parity numbers:
  - Per harness: 49 / 24 / 169 / 276 / 320 / 317 / 11 / 9 / 75.
  - 0 addendum checks. There are no `*.addendum.txt` files; Phase 37's companion tests were written natively in pytest.
  - 1238 ported and 12 deleted: C 1, S 8, P 1, R 2, and 0 each for B, D, J and T.
  - The rubric check over deleted rows prints 0.
- The arithmetic, checked against git:
  - Audit: 2018 at `2808f8a`.
  - Phase 32: 769. Phase 33 baseline: 1250, captured at `3655cc9`. 769 + 1250 = 2019.
  - The last effective `EXPECTED_CHECK_COUNT` of each harness matches between the audit commit and the capture commit, except `test_companion_app.py`: 319 at the audit, 320 at the capture.
  - `git log 2808f8a..3655cc9 -- 'companion/test_*.py'` lists only `320a642` and `17d5bc7`.
  - `17d5bc7` (plan 32-11, TST-03) adds exactly one `check(` and `EXPECTED_CHECK_COUNT = 320`.
  - The audit-time companion sum is 1249, and 769 + 1249 = 2018 exactly.
  - The +1 check is companion_app row 288, ported as `companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence`.
- 1238 ported rows map to 1219 distinct node ids. `comm -23` of those ids against `pytest --collect-only` is empty, so every ported target is a live test.
- Collected: 2593 tests at the time, 2594 after this plan's new test. 1669 are under `companion/`, and 126 of those are `[chromium]` tests.

## Task 2: the runs

The same `/nonexistent` snapshot was taken before any run and compared after each one: `ls -la --time-style=full-iso` of both levels, plus the sha256, size and mtime of the one file inside.

- **Pre-existing:** `/nonexistent/definitely-not-here/` (dir mtime 2026-09-24 12:38:56Z) holds `history.db`: 36864 bytes, mtime 2026-09-24 07:38:03Z, sha256 `692e9acd…cd950b5`. This is the pre-migration root-unsafe leftover that 33-01 recorded.
- **After every run:** identical, compared with whitespace normalised. The only raw diff was `ls` column padding, because nobody-owned dirs were present when the listing was taken.

| Run | Tree | User / interpreter | Result | TOTAL | git status --porcelain |
| --- | --- | --- | --- | --- | --- |
| nobody #1 | `89f4da9` clone | nobody (euid 65534), CPython 3.14.0rc2 hash-locked venv | 2593 passed, 0 skipped, rc 0 | 93.38% (651/9830 missed) | empty (ignored: `.coverage`, `.pytest_cache`, `__pycache__`) |
| root #1 | repo at `89f4da9` | root, dev venv CPython 3.11.15 | 2588 passed, 5 skipped, rc 0 | 93.23% | empty |
| pre-migration | `d2c53a0` clone | nobody, CPython 3.14.0rc2, pre-migration lock | 776 passed, 1 failed (see below) | **93.35%** (622/9356 missed) | n/a (baseline only) |
| **nobody #2 (final)** | `9c59884` clone | nobody, CPython 3.14.0rc2 | **2594 passed, 0 skipped, rc 0** | **93.38%** (651/9830 missed) | empty |
| nobody #3 (diagnostic) | `9c59884` clone + scratch `stop()` logging | nobody, CPython 3.14.0rc2 | 2594 passed, 0 skipped, rc 0 | 93.39% | empty once the scratch edit was reverted |
| **root #2 (final)** | repo at `9c59884` | root, CPython 3.11.15 | **2589 passed, 5 skipped, rc 0** | **93.26%** (663/9830 missed) | empty (ignored: `.coverage`, `.pytest_cache`, `.ruff_cache`, `server/.venv`) |

- All runs used `SKYPANE_REQUIRE_BROWSER=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers ./scripts/run-all-tests.sh`. Nobody runs used `env -i` with `HOME` set to a scratch dir. Nobody could execute the headless shell in place, so no browser copy was needed.
- The 5 root skips are the 5 `requires_non_root` tests: `server/test_poll_loop.py:1238`, `server/test_manual_resolutions.py:314` and `:325`, and `companion/test_companion_app_01.py:827` and `:868`. Each reports "root ignores permission bits; needs a non-root euid".
- All 126 `[chromium]` tests ran in every run: 0 skips as nobody, and only the 5 permission skips as root.
- `fail_under` stays at 93, since 93.38 rounds down to 93. The derivation comment in `pyproject.toml` now records the date, interpreter, euid, test count and TOTAL.

### Coverage-gap analysis

Coverage was compared like for like: the recorded 93.35% was measured as nobody on 3.14, not as root.

- The non-root measurement (93.38%) is at least the pre-migration figure.
- The margin is thin (0.03 pp), and the root/3.11 number is lower. So both trees were also compared per file, using coverage JSON from the pre-migration run and nobody #1:

| File | Pre-migration | HEAD (nobody #1) | Lines |
| --- | --- | --- | --- |
| `companion/pages/home_page.py` | 14/269 missed | 15/269 missed | **lost: 283** |
| `server/device_config.py` | 12/207 | 11/207 | gained: 50 |
| `companion/app.py`, `companion/auth.py`, `companion/pages/health_page.py`, `server/plane/render.py` | | | % up; statement counts changed from Phase 37 and other work in between |
| `companion/conftest.py`, `deploy/backup/*.py` | absent | present | new files in scope since the baseline |

Only one line lost coverage: `home_page.py:283`, `_direction_text()`'s `return DIRECTION_ARRIVING_TEXT`.

- **How the legacy suite covered it:** only by accident. At `test_companion_app.py:9723`, the theme-preview check seeded an arriving `VLG9999` row into the harness's single shared state dir. Later checks did `GET /` on the same shared server, and Home rendered that row.
- **Why the migration lost it:** the ported test gets its own server, so no later request sees that row.
- **The fix:** `test_home_recent_flights_detail_names_a_direction_only_when_known` in `companion/test_companion_app_04b.py`. It seeds departing, arriving, another state (`confirmed`) and no state. It then asserts each Recent flights detail line from the parsed page served by `GET /`.
- **Mutation check:** making the arriving branch return the departing text fails the test, and so does making the fallback return a direction.
- **Result:** nobody #2 covers line 283.

Nothing else needed replacing. The retired shim and `LegacyHarness` were test code: `companion/test_*.py` is omitted from the coverage scope, and `test-support/` is outside `source`. Their removal therefore changes no measured statement, and no production line depended on them for coverage.

**A ±1-line race in the measurement (F-04).**

- `companion/app.py:3617` was covered in nobody #1 and #3 but missed in #2, which is why #2's TOTAL shows the same 651 missed lines as #1 even with line 283 now covered.
- That line is the `return None` after `require_session()` on the manual-resolution delete route. It runs after the 303 response has been written.
- It was covered in 15 of 15 isolated runs. Logging `stop()` showed no SIGKILL fallback: all 147 stops took 34 ms or less.
- So the cause is teardown's SIGTERM reaching the child before the daemon request thread has executed its last line. It is not lost data from a killed child.
- It is recorded as F-04 and left unfixed.

### The pre-migration tree's one failure, root-caused

The failing check was `17d5bc7`'s "first poll trigger's run_once() was served by the fake ADS-B providers" in the legacy `test_companion_app.py`.

- **Deterministic:** it failed every time at about 04:50 Paris time, both as root and as nobody, on 3.11 and on 3.14.
- **Cause:** instrumenting a scratch copy showed the shared harness state dir held `quiet_hours_enabled=True`, left there by an earlier check, with the default 23:00-07:00 window. `quiet_hours_status()` returned `(7392, '07:00')`. `run_once()` therefore took the quiet-hours hold and returned before any detection.
- **Scope:** this is a time-of-day dependency in the pre-migration harness, caused by state leaking between checks. It explains why 33-01's capture at 08:51 UTC passed.
- **Current code:** the ported test starts a fresh server with default config and passed at the same hour. No current code is affected.

## Task Commits

1. **Task 1: assemble the ledger, closing parity** - `89f4da9` (docs)
2. **Task 2a: behaviour test for the lost coverage line** - `9c59884` (test)
3. **Task 2b: coverage derivation comment** - `10487aa` (chore)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `--assemble` truncated the ledger header**
- **Found during:** Task 1
- **Issue:** `cmd_assemble` used `existing.find("<!-- fragments -->")`. That matched the marker quoted in the header prose on line 13 instead of the real marker line on line 88, so about 70 header lines (Format, rubric, status table, verification) were dropped.
- **Fix:** `ledger_header_lines()` matches only a line that is exactly the marker. A self-test case covers the quoted-marker case (self-test: 44 checks OK). The ledger was restored from git and re-assembled.
- **Commit:** `89f4da9`

**2. [Rule 2 - Coverage parity] A behaviour test for the one line the migration stopped covering**
- **Found during:** Task 2 (per-file comparison)
- **Fix:** `test_home_recent_flights_detail_names_a_direction_only_when_known`, described above.
- **Commit:** `9c59884`

### Not executed

**Task 3 (push, draft PR, `gh pr checks --watch`, "CI evidence" section in the ledger).** The orchestrator's rules for this plan say to never push, because the orchestrator pushes. `gh` is also not installed on this host. The ledger therefore has no "CI evidence" section yet, and the orchestrator adds it after its push.

TST-11's evidence without CI:
- `.github/workflows/ci.yml` sets `SKYPANE_REQUIRE_BROWSER: "1"` on 3.14 with the `--only-shell` Chromium.
- `companion/test_browser_policy.py::test_missing_browser_fails_in_ci` proves that a missing browser gives rc != 0 with `CI=true`.
- Every local run executed all 126 `[chromium]` tests under xdist with no browser skip.

### Other

- The plan text says "commit and push" in Task 2 step 6. The push was not done, for the same reason.
- The non-root clone was made with `git clone --no-hardlinks` rather than `git worktree add`. A clone gives nobody its own `.git`, whereas a worktree's `.git` file points into `/home/user/skypane/.git`, which nobody cannot read. Both clones were deleted afterwards.
- The CPython 3.14.0rc2 interpreter was installed with `uv` into `/opt/skypane-uvpy`, which is world-readable, following 32-15's pitfall note. `uv` also added a `~/.local/bin/python3.14` shim. Both were removed along with the two scratch venvs and the scratch home.

## Requirement evidence (TST-10..TST-15, marked complete)

- **TST-10:** 44 `companion/test_*.py` modules run under pytest with no legacy runner (guard `test_no_legacy_runner_anywhere`). One shared app-server fixture family lives in `test-support/companion_app_server.py` and `companion/conftest.py`. The guard bans copied `Harness`, `http_request` and `_NoRedirectHandler` (33-02, 33-32).
- **TST-11:** pytest-playwright with 126 `[chromium]` ids, each its own xdist-distributable test. Missing-browser policy: `test_missing_browser_fails_in_ci` and `test_missing_browser_skips_locally`; `ci.yml` sets `SKYPANE_REQUIRE_BROWSER=1`. CI's own run on the phase PR is pending the orchestrator's push.
- **TST-12:** the strict guard (`companion/test_suite_guards.py`, rules G1-G12 with failing-sample self-tests) passes over every companion test module. All 12 deletions carry rubric codes C/S/P/R.
- **TST-13:**
  - The 5 `requires_non_root` tests skip under euid 0 and pass as nobody.
  - Both runs leave the repo's `git status --porcelain` empty.
  - `/nonexistent` is byte-identical before and after.
  - Every test-chosen write path is a `tmp_path` (guard G6).
  - F-03 records Playwright's own driver temp dirs. These are not test-chosen paths, and they predate the phase.
- **TST-14:** the shim, the legacy lists, `collect_ignore`, `LegacyHarness` and every `EXPECTED_CHECK_COUNT` are gone. The only remaining mention is in the guard, as the pattern it detects. `scripts/run-all-tests.sh` is a thin `exec pytest -n auto --cov` wrapper (33-32).
- **TST-15:** closing parity as above (2018 plus 1 check added after the audit baseline, all accounted for). Coverage is 93.38% against 93.35%, like for like, with a per-file comparison.

## Known Stubs

None.

## Follow-ups

`33-FOLLOWUPS.md`:
- F-02 (gsd-sdk STATE.md corruption) stays OPEN as a tooling issue outside this phase.
- New F-03: Playwright's empty temp dirs in `/tmp`.
- New F-04: the ±1-line coverage race on `app.py:3617`.

Also for the orchestrator: a pre-existing background `until … sleep 5` wait loop (pid 23898, parent the main session, started about 6 h before this plan) was still running. This plan did not start it and did not touch it.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

Commits `89f4da9`, `9c59884` and `10487aa` found in `git log --all`, each ending with the
required trailers. The SUMMARY, the assembled ledger and the new test module are on disk.
