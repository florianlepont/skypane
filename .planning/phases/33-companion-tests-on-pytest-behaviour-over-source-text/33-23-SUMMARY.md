---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 23
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "22"
    provides: "companion/test_browser_ux_02.py's module-scoped-server-for-read-only / function-scoped-server-for-mutating split, and the login-lockout precedent for isolating a check that drives process-global state onto its own server"
provides:
  - "companion/test_browser_ux_03.py: checks #38-#62 of companion/test_browser_ux.py's 75 legacy check() calls (the expired-countdown wording floor; Home's D1 swap rules — focus-holding region, [data-pending] region, dirty-settings-form stand-down, hidden-tab zero-requests, the frame picture's fade-only-on-change; the Display fallback save at 360px; the D2 optimistic Frame-strip switch family — flips before the answer, rolls back and announces on failure, survives a mid-flip refresh, saves with scripts blocked; the Flights live-list family — new-detection highlight, refresh-preserves-open-row, refresh-never-interrupts-the-filter, a collapsed detail row's keyboard floor, the phone card's tap-anywhere disclosure; the restored dirty bar's own dirty-count/save-every-field/fallback-save family; the retired runway map's replacement relationship; Display's recorded page height; the theme/arrivals scripts-blocked save floors; and the palette preview's keyboard/hover/focus behaviour), rewritten as 25 native pytest-playwright tests (25 collected node ids, none parametrized)"
  - "14 of the 25 ported checks share one module-scoped, read-only seeded server; 11 checks that persist a real setting or write a new database row each get their own function-scoped make_app_server"
  - "companion/test_browser_ux.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 38 to 13, the 25 migrated check() calls and the closures/module-level helpers only they used removed from main(), five now-unused imports (i18n, layout, history_page, history_db, VIEWPORT_DESKTOP, VIEWPORT_PHONE, _display_page_height) dropped, THEME_PREVIEW_SEL kept alive at its new call site since part 04's remaining checks still read it"
  - "the migration ledger fragment's rows 38-62 flipped: 25 ported, 0 deleted"
affects: [33-24, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Request-count assertions for the D1 'zero requests while hidden/dirty/mid-flip' family are counted through page.on('request', ...) on the guarded context and compared before/after a forced visibilitychange catch-up (_force_refresh), never inferred from the DOM — a page that fetched and then declined to swap is a different and worse behaviour than a page that never fetched, matching this slice's own <slice> instruction."
    - "Node-identity swap assertions (a region 'survived' vs. 'was replaced') are proven with a JS expando (_mark/_marked) rather than a selector re-match, since a replacement node matching the same selector is exactly the defect under test; every one of these checks also asserts a CONTROL phase (another region really was swapped in the same cycle) so a refresh that swaps nothing cannot satisfy the assertion for free."
    - "Two Flights checks (new-detection highlight, refresh-preserves-open-row) write a new runway_events row directly through history_db.record_runway_event() mid-test, mutating on-disk state without going through the app's settings UI — both get their own function-scoped make_app_server so no other test in the module ever sees the injected row."
    - "_persist_without_js()'s self-restoring contract (restore=True by default) is trusted for the two scripts-blocked theme/arrivals save checks, but they still get their own function-scoped server rather than sharing the module's read-only one — matching this slice's own <slice> instruction that Display-page save flows use function-scoped servers regardless of whether the helper restores afterward."
    - "THEME_PREVIEW_SEL = '.theme-live-preview__image' is now defined in BOTH the new module and the still-legacy harness, since part 04's own remaining checks (rows 63-75) still read it — grepped whole-file before this plan's own deletion to confirm the constant has a live consumer on both sides of the cut."

key-files:
  created:
    - companion/test_browser_ux_03.py
  modified:
    - companion/test_browser_ux.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md

key-decisions:
  - "None of the 25 checks were parametrized: every one either drives a single named interaction/procedure (a switch flip, a filter query, a save) or an internal loop whose own final assertion compares values ACROSS iterations (both languages must agree on the translated failure copy; both scripts-blocked switches persist to the SAME field; the height recorded at two widths is one instrument's own two readings) — splitting any of these into independent parametrized cases would need one parametrized run to re-derive data another run depends on, which 33-MIGRATION-RULES.md section 2 forbids under xdist. This mirrors 33-20's own decision for the quiet-hours/wake-interval checks."
  - "Shared D1/D2/D7 helpers local to this slice (_force_refresh, _count_document_requests, _mark/_marked/_dirty_the_region, _hold_fetch/_fetch_was_issued/_release_fetch/_switch_state, _record_a_new_detection/_row_ids/_highlighted) were kept as plain module-level functions inside companion/test_browser_ux_03.py rather than promoted into companion/test_browser_ux_helpers.py — grepped whole-file (both the pre-migration source and the resulting legacy file) before this plan's own commit, confirming no check outside this slice's own 25 calls them, so 33-MIGRATION-RULES.md section 2's 'helpers shared by SEVERAL parts' threshold does not apply."
  - "11 of the 25 checks (the 4 switch checks, the 2 scripts-blocked/fallback Display saves, the bar's own every-field save, the 2 theme/arrivals scripts-blocked saves, and the 2 Flights checks that write a new database row) get their own function-scoped make_app_server rather than sharing the module's read-only server, even where the underlying helper (_persist_without_js) already self-restores — the <slice> note in 33-23-PLAN.md states this as an explicit rule ('Display-page save flows MUTATE state, so they use function-scoped servers'), not a per-check judgment call."

requirements-completed: []

# Metrics
duration: 17min (commit-to-commit: previous plan's last commit 9277288 at 23:30:32Z to this plan's last task commit f29b557 at 23:47:25Z)
completed: 2026-09-24
---

# Phase 33 Plan 23: Browser UX Part 03 Migration Summary

**Checks #38-#62 of `companion/test_browser_ux.py`'s 75 legacy checks (the expired-countdown wording floor, Home's D1 swap rules, the D2 optimistic Frame-strip switch family, the Flights live-list family, the restored dirty bar's own dirty-count/save/fallback family, the retired runway map's replacement relationship, Display's recorded page height, the theme/arrivals scripts-blocked save floors, and the palette preview's keyboard/hover/focus behaviour) now run as 25 native pytest-playwright tests in `companion/test_browser_ux_03.py`.**

## Performance

- **Duration:** ~17 min (commit-to-commit, previous plan's last commit `9277288` at 23:30:32Z to this plan's last task commit `f29b557` at 23:47:25Z)
- **Started:** 2026-09-24T23:30:32Z
- **Completed:** 2026-09-24T23:47:25Z
- **Tasks:** 3/3 completed
- **Files modified:** 3

## Accomplishments

- `companion/test_browser_ux_03.py` created: `pytestmark = pytest.mark.browser`, one module-scoped read-only seeded server (`module_app_server_factory(seed=seed_state_dir, fake_providers=True)`) shared by 14 of the 25 checks. 11 checks that persist a real setting through the UI or write a new database row directly get their own function-scoped `make_app_server` server: all four Frame-strip switch checks (D2's optimistic flip/rollback/mid-flip-refresh/scripts-blocked family), the Display/fallback-Save/theme/arrivals scripts-blocked saves, the bar's own every-field save, and the two Flights checks that write a new `runway_events` row through `history_db.record_runway_event()`.
- Every `browser.new_context(...)` call site is now the guarded `new_context` fixture from `companion/conftest.py`; every `harness.base_url()`/`harness.tmpdir` reference is now `server.base_url()`/`server.tmpdir`; every `return False, (...)` became a raised `AssertionError`, and every `return True, ""` was dropped in favour of a plain fall-through return.
- Shared D1/D2/D7 helpers local to this slice (the request-counting/force-refresh/node-marking family for the swap-rule checks, the fetch-holding family for the optimistic-switch checks, and the flight-detection-writing family) were promoted to plain module-level functions inside the new file, taking explicit `state_dir`/`page` parameters instead of closing over a single shared `harness` — the same promotion pattern 33-20 established for `_quiet_hours_on_disk()`/`_wake_interval_on_disk()`.
- `companion/test_browser_ux.py` shrunk further: `EXPECTED_CHECK_COUNT` collapsed from 38 to 13; the 25 migrated `check()` calls and their dedicated closures removed from `main()`; `ruff check --fix` removed five now-dead imports (`i18n`, `layout`, `history_page`, `history_db`, `VIEWPORT_DESKTOP`, `VIEWPORT_PHONE`, `_display_page_height`) that only this slice's own checks used; `THEME_PREVIEW_SEL = ".theme-live-preview__image"` was kept in the legacy file (in addition to the new module) since part 04's own remaining checks (rows 63-75) still read it.
- The migration ledger fragment's rows 38-62 flipped: 25 `ported` (0 `deleted` — every check in this slice already asserted real behaviour through an HTTP request count, live DOM state, or a disk read, so no rubric-C/S/P/R deletion applied to any row). `33-ledger-check.py --allow-pending` confirms `75/75 baseline checks mapped (61 ported, 1 deleted, 13 pending)`.
- Full verification chain, all green:
  - `companion/test_browser_ux_03.py`: 13/13 passed after Task 1, 25/25 passed after Task 2, `SKYPANE_REQUIRE_BROWSER=1`, real Chromium, `-n auto`.
  - The shrunk legacy file through the shim (`companion/test_legacy_harness_shim.py -k "exits_zero and test_browser_ux"`): 1 passed (25.45s), same `SKYPANE_REQUIRE_BROWSER=1` real-Chromium proof, now against 13 remaining checks.
  - `companion/test_suite_guards.py test-support` (full, unscoped): 105 passed.
  - `ruff check companion/test_browser_ux*.py` and `ruff check .` (implied by the full-tree run below): clean.
  - `33-ledger-check.py --allow-pending companion/test_browser_ux.py`: exit 0, `75/75 baseline checks mapped (61 ported, 1 deleted, 13 pending)`.
  - Full suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`): **2256 passed, 5 skipped, 0 failed** in 282.54s. All 5 skips are the pre-existing, unrelated `root ignores permission bits; needs a non-root euid` skips — none touch `test_browser_ux*`.

## Task Commits

1. **Task 1: First half of part 03** - `f846559` (test) — checks #38-50 (the expired-countdown floor, Home's D1 swap rules, the Display fallback save floor, and the D2 optimistic switch family)
2. **Task 2: Second half of part 03** - `b30019c` (test) — checks #51-62 (the Flights filter-immunity floor, the collapsed-row keyboard floor, the phone card disclosure, the dirty bar's own family, the retired runway map relationship, Display's recorded height, the theme/arrivals save floors, and the palette preview behaviour)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify in a browser, commit** - `f29b557` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `companion/test_browser_ux_03.py` - new module, 25 pytest-playwright test functions (25 collected node ids, none parametrized)
- `companion/test_browser_ux.py` - shrunk: `EXPECTED_CHECK_COUNT` 38 -> 13, the 25 migrated `check()` calls and their dedicated closures/local helpers removed, five now-unused imports dropped, `THEME_PREVIEW_SEL` kept for part 04's own remaining checks
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md` - rows 38-62 flipped (25 ported, 0 deleted), `### Part 03 (plan 33-23)` note added

## Decisions Made

See `key-decisions` in the frontmatter: why none of the 25 checks were parametrized (every internal loop's final assertion compares values across iterations); why the D1/D2/D7 request-counting/node-marking/fetch-holding/flight-detection helpers stayed local to this module rather than moving into the shared helpers file (grepped, zero consumers outside this slice); and why 11 checks get their own function-scoped server even where the underlying helper already self-restores (the plan's own `<slice>` instruction, not a per-check judgment call).

## Deviations from Plan

None - the plan's own migration work was executed exactly as written. No production code was touched; no auto-fixes were needed. The only mechanical adjustment beyond the plan's own text was letting `ruff check --fix` remove the five imports that became dead once this slice's checks were cut from the legacy file's `main()`, which is exactly what 33-MIGRATION-RULES.md section 1 anticipates ("Setup that remaining checks still need stays" — the inverse, that setup no remaining check needs is removed, follows from the same rule).

## Issues Encountered

None. The sandbox's `/opt/pw-browsers` Chromium build was stale for this session (matching `33-MIGRATION-RULES.md` section 0's documented pre-flight case) — resolved by exporting `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers` before any browser command, per the rule's own prescribed fix. No `companion/app.py` or `byos_server` process was left running at the end of this session (checked via `ps aux`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/test_browser_ux.py` now carries 13 remaining legacy checks (rows 63-75) for 33-24, the chain's closing plan; its `EXPECTED_CHECK_COUNT` and legacy-detection markers are otherwise unchanged, so `companion/test_legacy_harness_shim.py` keeps running it unmodified until 33-24 deletes the file outright.
- `companion/test_browser_ux_03.py`'s module-scoped-server-for-read-only / function-scoped-server-for-mutating-or-database-writing split is available as direct precedent for 33-24's own part 04 (the accordion's own operability/scripts-blocked-save family, the Touch Targets measurement sweep, the no-JS floor's save-to-disk proof, the bar's own settle contract, validation-rejection handling, the dirty-count's document-order proof, the Cancel-restores-every-surface check, and the settings-card-title-consistency probe) and for closing plan 33-33's own verification.
- `THEME_PREVIEW_SEL` is now defined in both files by design; 33-24 should either delete the legacy file's own copy outright when it removes `main()` (since nothing else in the legacy file will read it after part 04's own checks are ported), or note explicitly if it keeps it for some other reason.
- No blockers for 33-24 or the rest of the companion migration chain. Both the scoped verification named in the plan and a full unscoped suite run (`companion test-support server stub-server deploy`, 2256 passed / 5 skipped / 0 failed) are green as of this plan's last commit.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

`companion/test_browser_ux_03.py`, the shrunk `companion/test_browser_ux.py`, and the updated
ledger fragment all found on disk; commit hashes `f846559`, `b30019c` and `f29b557` all found
in `git log --oneline --all`. All verification commands re-run live in this session: part-03
module 13/13 (Task 1) then 25/25 (Task 2), legacy shim 1/1, suite guards + test-support 105/105,
`ruff check` clean, ledger check exit 0 (75/75 mapped, 61 ported / 1 deleted / 13 pending), full
unscoped suite 2256 passed / 5 skipped / 0 failed.
