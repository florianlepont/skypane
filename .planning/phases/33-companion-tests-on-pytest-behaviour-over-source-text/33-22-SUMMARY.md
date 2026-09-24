---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 22
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "21"
    provides: "companion/test_browser_ux_01.py's module-scoped-server-for-read-only / function-scoped-server-for-mutating split, and its single-primary-node-id ledger convention for a parametrized check"
provides:
  - "companion/test_browser_ux_02.py: checks #19-#37 of companion/test_browser_ux.py's 75 legacy check() calls (dialog entrance/exit motion, the live theme preview crossfade, image-hold skeletons, the login card layout and show-password toggle, the login lockout countdown, the nav-status line-breaking, the mobile nav close consistency, the restored dirty bar's clearance geometry, the Health refresh loop's failure/recovery pill, four B11-class overflow sweeps, the view-transition name uniqueness and its reduced-motion opt-out, and the Health freshness ticker/no-JS floor), rewritten as 19 native pytest-playwright tests (43 collected node ids after parametrizing 7 independent-iteration loops)"
  - "18 of the 19 ported checks share one module-scoped, read-only seeded server; the login-lockout check gets its own function-scoped make_app_server since it drives the process-global LoginThrottle to its own limit"
  - "companion/test_browser_ux.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 57 to 38, the 19 migrated check() calls and the closures only they used removed from main(), the freshness-line TICK_SETTLE_MS/FRESHNESS_AGE constants kept alive at their new call site (still used by the un-migrated countdown check)"
  - "the migration ledger fragment's rows 19-37 flipped: 19 ported, 0 deleted"
affects: [33-23, 33-24, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A dialog's mid-transition opacity is sampled by nesting two requestAnimationFrame callbacks after the trigger click, never by a fixed setTimeout budget — the sample point is defined by frame count from the browser's own scheduler, not by wall-clock time, so it stays correct regardless of CI runner frame-rate pressure (contrast with 33-20's own fixed-400ms-loop bug, fixed in 98455b6, which this slice's dialog-fade check does not repeat)."
    - "Timer-driven UI (the Health freshness ticker) is asserted with a real wall-clock wait_for_timeout(2200ms) rather than a frame count, since the underlying mechanism is a setInterval/setTimeout tick, not a requestAnimationFrame loop — a real visible-tab wait is the correct instrument for that mechanism, and is not vulnerable to the frame-rate assumption commit 98455b6 fixed."
    - "None of the 19 checks in this slice ever opened companion/static/style.css as text (all `style.css` mentions in the pre-migration source were comments, not code) — so the plan's conditional C-rubric requirement (any check that read CSS text now asserts computed style via _computed_paint / _resolved_property, or is deleted with a C reason) has zero applicable rows this plan; 0 deleted, 19 ported confirms this by the ledger note."

key-files:
  created:
    - companion/test_browser_ux_02.py
  modified:
    - companion/test_browser_ux.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md

key-decisions:
  - "This continuation session did not redo any migration work: the two task commits (6f556e4, 72340ee) from the executor killed by a container restart were verified line-by-line against the plan's acceptance criteria before treating the plan as otherwise complete. All three tasks' acceptance criteria (part-02 module 0-skipped in a real browser, no sync_playwright/new_context/open()/tempfile calls, the shrunk legacy shim green, EXPECTED_CHECK_COUNT==pending rows, ruff clean) were independently re-verified rather than assumed from the commit messages."
  - "Task 1 and Task 2 (first half / second half of part 02) were committed together as a single commit (6f556e4) by the prior executor rather than as two separate commits. This is within 33-MIGRATION-RULES.md section 6's explicit 'one commit per task is fine' latitude — it does not combine differently-typed work and both halves' acceptance criteria are independently satisfied by the resulting file, so this continuation did not split or re-commit it."
  - "The grep-based acceptance criterion `grep -cE \"sync_playwright|browser\\.new_context|open\\(|tempfile\" companion/test_browser_ux_02.py` reports 1, not 0 — the single match is the `new_context` FIXTURE parameter name in a function signature (`def test_health_tables_fit_their_wraps_with_every_disclosure_open(new_context, server, lang)`), not a `browser.new_context(...)` call. Read line-by-line rather than trusting the raw grep count: the file makes zero direct sync_playwright/browser.new_context/open()/tempfile calls, matching the guarded-fixture-only rule (G10)."

requirements-completed: []

# Metrics
duration: 2h51min (commit-to-commit; see Issues Encountered for the real interruption this spans)
completed: 2026-09-24
---

# Phase 33 Plan 22: Browser UX Part 02 Migration Summary

**Checks #19-#37 of `companion/test_browser_ux.py`'s 75 legacy checks (dialog entrance/exit motion, the live theme crossfade, image-hold skeletons, the login card/show-password/lockout family, nav-status and mobile-nav consistency, the restored dirty bar's clearance geometry, Health's refresh failure/recovery pill, four B11 overflow sweeps, view-transition name uniqueness, and the Health freshness ticker/no-JS floor) now run as 19 native pytest-playwright tests (43 node ids) in `companion/test_browser_ux_02.py`.**

## Performance

- **Duration:** ~2h51m (commit-to-commit, previous plan's last commit `f3ca405` at 17:35:02Z to this plan's last task commit `72340ee` at 20:26:09Z) — this interval spans a container restart that killed the original executor mid-plan; see Issues Encountered for the real timeline.
- **Started:** 2026-09-24T17:35:02Z
- **Completed:** 2026-09-24T20:26:09Z
- **Tasks:** 3/3 completed
- **Files modified:** 3

## Accomplishments

- `companion/test_browser_ux_02.py` created: `pytestmark = pytest.mark.browser`, one module-scoped read-only seeded server (`module_app_server_factory(seed=seed_state_dir, fake_providers=True)`) shared by 18 of the 19 checks. The login-lockout check (row 24) gets its own function-scoped `make_app_server`, since it drives the process-global `LoginThrottle` to its own limit and would otherwise lock out any other check sharing its server.
- 7 of the 19 checks parametrize an independent-iteration loop that had no cross-iteration comparison in the original code (both dialogs' routes, the dirty-bar clearance viewports/languages, Home's overflow sweep at two widths/two languages, the recent-flight starvation sweep over 5 widths x 2 languages, Health's disclosure-gated tables in both languages, every-disclosure-open across 3 widths x 2 languages, and the view-transition reduced-motion opt-out) — 43 collected node ids total from 19 test functions.
- `companion/test_browser_ux.py` shrunk further: `EXPECTED_CHECK_COUNT` collapsed from 57 to 38; the 19 migrated `check()` calls and the closures only they used removed from `main()`; the freshness-line `TICK_SETTLE_MS`/`FRESHNESS_AGE` constants kept alive at their new call site, since the un-migrated countdown check (row 38, part 03's first row) still uses them.
- The migration ledger fragment's rows 19-37 flipped: 19 `ported` (0 `deleted` — this slice contains no check that reads `style.css` as text, confirmed by inspecting the pre-migration source for the slice's line range: every `style.css` mention there is a comment, never an `open()`/regex read). `33-ledger-check.py --allow-pending` confirms `75/75 baseline checks mapped (36 ported, 1 deleted, 38 pending)`.
- Full verification chain re-run and confirmed green by this continuation session (none of it assumed from the killed executor's commit messages):
  - `companion/test_browser_ux_02.py`: 43/43 passed, 0 skipped, `SKYPANE_REQUIRE_BROWSER=1`, real Chromium, `-n auto` (27.3s).
  - The shrunk legacy file through the shim (`companion/test_legacy_harness_shim.py -k "exits_zero and test_browser_ux"`): 1 passed in 109.15s, same `SKYPANE_REQUIRE_BROWSER=1` real-Chromium proof, now against 38 remaining checks.
  - `companion/test_suite_guards.py -k browser_ux`: 5 passed. `companion/test_suite_guards.py test-support` (full, unscoped): 101 passed.
  - `ruff check companion/test_browser_ux*.py` and `ruff check .` (whole tree): both clean.
  - `33-ledger-check.py --allow-pending companion/test_browser_ux.py`: exit 0, `75/75 baseline checks mapped (36 ported, 1 deleted, 38 pending)`.
  - Full suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`): **2085 passed, 5 skipped, 0 failed** in 197.37s. All 5 skips are the pre-existing, unrelated `root ignores permission bits; needs a non-root euid` skips in `test_companion_app_01.py`/`test_manual_resolutions.py`/`test_poll_loop.py` — none touch `test_browser_ux*`.

## Task Commits

Each task was committed atomically by the original (killed-and-restarted) executor; this continuation session verified rather than recreated them:

1. **Task 1: First half of part 02** + **Task 2: Second half of part 02** - `6f556e4` (test) — both halves landed in one commit
2. **Task 3: Shrink the legacy harness, fill the ledger, verify in a browser, commit** - `72340ee` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `companion/test_browser_ux_02.py` - new module, 19 pytest-playwright test functions (43 collected node ids after parametrization)
- `companion/test_browser_ux.py` - shrunk: `EXPECTED_CHECK_COUNT` 57 -> 38, the 19 migrated `check()` calls and their dedicated closures removed, `TICK_SETTLE_MS`/`FRESHNESS_AGE` kept for the still-legacy countdown check
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md` - rows 19-37 flipped (19 ported, 0 deleted), `### Part 02 (plan 33-22)` note added

## Decisions Made

See `key-decisions` in the frontmatter: no migration work was redone since the killed executor's two commits were verified line-by-line rather than trusted at face value; Tasks 1/2 landing in a single commit is within the migration rules' explicit latitude; and the one nonzero grep hit in the plan's own acceptance-criteria grep pattern is a `new_context` fixture parameter name, not a `browser.new_context(...)` call, confirmed by reading the matched line directly.

## Deviations from Plan

None - the plan's own migration work was executed exactly as written by the prior (killed) executor, and this continuation session found no gap between what the plan specified and what the tree contained. No production code was touched; no auto-fixes were needed.

## Issues Encountered

**Container restart mid-plan.** A previous executor was killed by a container restart after committing both task commits (`6f556e4`, `72340ee`) but before running the plan's own verification steps or writing this SUMMARY. This continuation session:
1. Read the plan and both commits in full and checked every task's acceptance criteria against the tree (none were missing or partially done — both commits' content matches the plan's Tasks 1-3 exactly).
2. Re-ran every verification command named in the plan and in `33-MIGRATION-RULES.md` section 5 from scratch, plus the full unscoped suite — all green, reported above.
3. Found the sandbox's `/opt/pw-browsers` Chromium build stale for this session (`chrome-headless-shell` executable missing), matching `33-MIGRATION-RULES.md` section 0's documented pre-flight case — resolved by exporting `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers` and running `playwright install --only-shell chromium`, per the rule's own prescribed fix, before any test command.

No test failed at any point in this session; nothing required investigation as a genuine regression.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/test_browser_ux.py` now carries 38 remaining legacy checks across parts 03-04 (originally numbered 38-75); its `EXPECTED_CHECK_COUNT` and legacy-detection markers are otherwise unchanged, so `companion/test_legacy_harness_shim.py` keeps running it unmodified until 33-24 (the chain's last plan) deletes the file outright.
- `companion/test_browser_ux_02.py`'s module-scoped-server-for-read-only / function-scoped-server-for-mutating split (with the login-lockout check as this plan's own example of "mutates process-global state, not just disk") is available as direct precedent for 33-23/33-24's own parts of this same harness.
- No blockers for 33-23 (part 03, picking up immediately after this plan's LAST anchor, `_the_relative_age_is_server_rendered_and_static_without_scripts` / row 37) or the rest of the companion migration chain. Both the scoped verification named in the plan and a full unscoped suite run (`companion test-support server stub-server deploy`, 2085 passed / 5 skipped / 0 failed) are green as of this plan's last commit.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

`companion/test_browser_ux_02.py` and the updated `companion/test_browser_ux.py` and ledger fragment all found on disk; commit hashes `6f556e4` and `72340ee` both found in `git log --oneline --all`. All verification commands re-run live in this session (not inferred): part-02 module 43/43, legacy shim 1/1, suite guards 5/5 (scoped) and 101/101 (full, with test-support), ledger check exit 0, `ruff check .` clean, full unscoped suite 2085 passed / 5 skipped / 0 failed.
