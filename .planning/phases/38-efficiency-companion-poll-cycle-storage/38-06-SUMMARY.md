---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 06
subsystem: web
tags: [performance, http, static-assets, companion, stdlib]

# Dependency graph
requires:
  - phase: 38-02
    provides: "companion/app.py's _serve_static() ETag/304 machinery (unrelated file region; no direct dependency, but confirms the companion suite's shape this plan continues)"
provides:
  - "companion/layout.py: SHELL_SCRIPT_ORDER (the shell's 15 script srcs in their fixed relative emission order), GLOBAL_PAGE_SCRIPTS (nav-dropdown, flash-cleanup, submit-guard, relative-time - present on every authenticated page), and page_shell(scripts=...) - collapses the old unconditional 15-tag template into one join over the wanted subset, raising ValueError on an unknown src"
  - "companion/app.py's _PAGE_SCRIPTS: one extra-scripts tuple per layout.NAV_TABS route (the superset over every state that route can be in), threaded through _page_shell_for()'s scripts= keyword"
  - "companion/test_page_scripts.py: a behaviour-level hook-coverage + exact-set harness against a real running companion/app.py, parametrised over six routes and three states (empty/seeded/flash), plus 404/login/missing-tuple guards"
affects: [38-07, 38-08, 38-09, 38-10, 38-11, 38-12, 38-13, "42 (OTA Update page must declare a _PAGE_SCRIPTS tuple or its confirm-submit.js silently disappears)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "page_shell(scripts=...) is opt-in, not a route table: each of the six live routes keeps its own fixed dict entry in companion/app.py, and layout.py stays the single place the emission order is declared (SHELL_SCRIPT_ORDER) - no CMP-01/02 route table introduced"
    - "A route's _PAGE_SCRIPTS tuple is the superset over every state that page can render, including a region freshness.js may swap in later with no fresh page load of its own (Flights' flight-rows/copy-button at zero rows; Display's calendar-disconnect confirm.js before a calendar is ever connected) - the hook-coverage test only asserts a present hook has its script, never the reverse, so over-inclusion is always safe"
    - "companion/test_page_scripts.py drives a real AppServer subprocess through login()/get() and parses served HTML with companion_markup.parse_html().select(), never regexing or reading JS/Python source text (test_suite_guards.py G2/G11)"

key-files:
  created:
    - companion/test_page_scripts.py
  modified:
    - companion/layout.py
    - companion/app.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_03.py

key-decisions:
  - "The RESEARCH doc's own hook-scan hint placed confirm-submit.js on /device (\"calendar connected\"); reading companion/pages/config_page.py directly shows the Aspect card - and both its data-confirm forms (calendar disconnect, colour-rule delete) - render only under SCOPE_DISPLAY (screens.py's EVERYDAY_GROUPS carries GROUP_THEME/GROUP_CALENDAR; SCOPE_DEVICE's ADVANCED_GROUPS does not). confirm-submit.js went on Display's tuple, not Device's - the research hint was explicitly flagged as \"a hint, not the source of truth\", and this plan trusted the code over the hint."
  - "Chose three states over the plan's suggested minimum of two (empty, seeded) by adding a third case - the empty state with ?flash=saved - reusing the same two backing AppServer subprocesses (module-scoped) rather than starting a third, since flash-cleanup.js is already global and the interesting proof is that the flash banner's own hook still resolves correctly under the new opt-in scheme."

requirements-completed: [EFF-02]

# Metrics
duration: ~26min
completed: 2026-09-26
---

# Phase 38 Plan 06: Per-page scripts (EFF-02) Summary

**`layout.page_shell(scripts=...)` plus a `companion/app.py` `_PAGE_SCRIPTS` table per tab now serve 6-10 shell `<script>` tags per route instead of a fixed 15, with a behaviour-level hook-coverage test guarding every current and future tab.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-09-26T16:35:00Z (approx., immediately after 38-05)
- **Completed:** 2026-09-26T17:01:00Z
- **Tasks:** 1 completed (RED/GREEN TDD cycle)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- `companion/layout.py`: `SHELL_SCRIPT_ORDER` (the shell's 15 script srcs, in the exact order the old template hard-coded them) and `GLOBAL_PAGE_SCRIPTS` (`NAV_DROPDOWN_SCRIPT_SRC`, `FLASH_CLEANUP_SCRIPT_SRC`, `SUBMIT_GUARD_SCRIPT_SRC`, `RELATIVE_TIME_SCRIPT_SRC` — present on every authenticated `page_shell()` document regardless of `scripts`). `page_shell()` gained `scripts=()`: the old 15 positional `%s` script-tag lines and their 15 per-script comments collapsed into one `"".join(...)` over `SHELL_SCRIPT_ORDER`, filtered to `GLOBAL_PAGE_SCRIPTS | set(scripts)`, each src emitted at most once in `SHELL_SCRIPT_ORDER`'s relative order. A src in `scripts` outside `SHELL_SCRIPT_ORDER` raises `ValueError` (fails fast on a typo). `login_shell()` and `_not_found_page()`/`_forbidden_page()` are untouched — the 404/403 pages call `page_shell()` with no `scripts=`, so they keep exactly `GLOBAL_PAGE_SCRIPTS`, and the login page keeps emitting exactly `login-card.js`.
- `companion/app.py`'s new `_PAGE_SCRIPTS` dict gives each of the six `layout.NAV_TABS` routes its own extra-scripts tuple, threaded through `_page_shell_for()`'s new `scripts=_PAGE_SCRIPTS[route]` argument (the one `page_shell()` call site for every GET tab and the rejected-settings-POST re-render):
  - Home: `freshness`, `quick-switch` (6 shell tags total)
  - Display: `confirm-submit`, `dirty-state`, `freshness`, `quick-switch`, `theme-preview`, `value-controls` (10)
  - Device: `dirty-state`, `poll-cooldown`, `quick-switch`, `value-controls` (8)
  - Flights: `copy-button`, `flight-rows`, `freshness`, `list-filter`, `panel-lookup` (9)
  - Health: `copy-button`, `freshness`, `list-filter` (7, plus `battery-trend.js` unchanged in its own body)
  - Airlines: `list-filter`, `panel-lookup` (6)
  Each tuple is the superset over every state that route can render, including a swap-only region with no hook present at initial load (Flights keeps `flight-rows`/`copy-button` even with zero rows on the page; Display keeps `confirm-submit` even before a calendar is ever connected, since the disconnect/rule-delete `data-confirm` forms can appear after a save with no fresh page load).
- `companion/test_page_scripts.py` (39 tests, new): drives two module-scoped real `AppServer` subprocesses ("empty" and history/registry/calendar/gallery-"seeded") through `login()`/`get()`, and for six routes × three states (empty, seeded, and the empty server's own `?flash=saved` query) asserts every present DOM hook has its script, the shell's exact script set equals `GLOBAL_PAGE_SCRIPTS | _PAGE_SCRIPTS[route]` with no repeats and in `SHELL_SCRIPT_ORDER`'s order, every route serves fewer than 15 shell tags, every `NAV_TABS` route has a `_PAGE_SCRIPTS` entry, the authenticated 404 carries exactly `GLOBAL_PAGE_SCRIPTS`, and `/login` carries exactly `login-card.js`.
- Six pre-existing assertions in `companion/test_companion_app_02.py`/`test_companion_app_03.py` pinned the old serve-everywhere convention (a bare `page_shell()` call expected to already carry a specific non-global script). Each now passes `scripts=(...)` explicitly for the src(s) under test, preserving the original test's intent (cross-file route/src equality, exactly-one-tag, no-bare-inline-script) under the new opt-in default.

## Task Commits

1. **Task 1 RED: failing per-page script coverage tests** - `40bc5ac` (test) — 39 tests written; 20 fail against the unmodified `companion/layout.py`/`app.py` (the exact-set, missing-tuple and 404 checks — the hook-coverage and login checks already passed, since nothing about *hook presence* changed yet)
2. **Task 1 GREEN: `page_shell(scripts=...)` + per-route `_PAGE_SCRIPTS`** - `0f25b6f` (feat) — all 39 tests pass; six pre-existing tests updated for the new opt-in default; full companion suite (not-browser) 1620 passed; `ruff`/`check_comment_history.py` clean

## Files Created/Modified
- `companion/layout.py` — `SHELL_SCRIPT_ORDER`, `GLOBAL_PAGE_SCRIPTS`, `page_shell(scripts=())` (ValueError on an unknown src; one `"".join(...)` slot replacing 15 positional `%s` lines and their comments)
- `companion/app.py` — `_PAGE_SCRIPTS` (six route tuples, next to `_PAGE_TITLES`); `_page_shell_for()` passes `scripts=_PAGE_SCRIPTS[route]`
- `companion/test_page_scripts.py` — 39 new tests: hook coverage, exact-set/order/no-repeat, missing-tuple guard, 404/login fixed sets
- `companion/test_companion_app_02.py` — one test (`test_four_new_static_routes_dom_contract_guard`) updated to request its four srcs explicitly via `scripts=`
- `companion/test_companion_app_03.py` — five tests (theme-preview, flight-rows, quick-switch and value-controls exactly-once checks, plus the fifteen-deferred-scripts check) updated: the four exactly-once tests now request their one src via `scripts=`; the fifteen-scripts test first asserts a bare call emits exactly `len(GLOBAL_PAGE_SCRIPTS)` (4) tags, then asserts requesting every other `SHELL_SCRIPT_ORDER` src via `scripts=` still emits all fifteen together (the original test's real point — that the shell mechanism can still produce every script when asked, and that login/quick-switch/etc. stay off the login shell)

## Decisions Made
- `confirm-submit.js` went on **Display**'s tuple, not Device's, contradicting `38-RESEARCH.md`'s own hook-scan hint ("`/device` ... + confirm-submit when the calendar is connected"). Reading `companion/pages/config_page.py` and `companion/screens.py` directly: the Aspect card — which holds both `data-confirm` forms (calendar disconnect, colour-rule delete) — is built only when `scope == SCOPE_DISPLAY` (`screens.EVERYDAY_GROUPS` carries `GROUP_THEME`/`GROUP_CALENDAR`; `SCOPE_DEVICE`'s `ADVANCED_GROUPS` does not). The RESEARCH doc explicitly says its scan "is a hint and not the source of truth"; this plan trusted the code.
- Used three states (empty, seeded, and the empty server's own `?flash=saved` query) rather than the plan's stated minimum of two, reusing the two module-scoped `AppServer` subprocesses rather than starting a third — the flash case's interesting proof (flash-cleanup.js's hook still resolving under the new opt-in scheme) doesn't need its own server, since flash-cleanup.js is already global.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in existing tests] Six pre-existing tests pinned the old serve-everywhere convention**
- **Found during:** Task 1 GREEN, running the whole companion suite per the plan's own instruction
- **Issue:** `test_four_new_static_routes_dom_contract_guard` (`test_companion_app_02.py`) and five tests in `test_companion_app_03.py` (`test_theme_preview_script_tag_exactly_once_and_no_bare_inline_script`, `test_flight_rows_script_tag_exactly_once_and_no_bare_inline_script`, `test_quick_switch_script_tag_exactly_once_and_no_bare_inline_script`, `test_value_controls_script_tag_exactly_once_and_no_bare_inline_script`, `test_fifteen_deferred_scripts_before_closing_body`) all called `layout.page_shell(title="T", active="health", body="<p>b</p>")` with no `scripts=` and expected specific non-global script tags in the result — true under the old unconditional-15 template, false now that those srcs are opt-in.
- **Fix:** Each of the four "exactly-once" tests now passes `scripts=(that one src,)` to keep asserting its real point (route/src equality, one instance, no bare inline `<script>`). The DOM-contract guard requests all four of its srcs via `scripts=`. The fifteen-tags test was split in two: a bare call now asserts exactly `len(GLOBAL_PAGE_SCRIPTS)` (4) tags, then a call requesting every other `SHELL_SCRIPT_ORDER` src via `scripts=` asserts all fifteen still emit together, in order, without login-card.js and without the four newly-scoped scripts on the login shell — preserving the original test's real intent (the shell mechanism can still produce every script when every one is asked for).
- **Files modified:** `companion/test_companion_app_02.py`, `companion/test_companion_app_03.py`
- **Verification:** Full companion suite (`-m "not browser"`) 1620 passed; `ruff check companion` clean; `scripts/check_comment_history.py check` clean.
- **Committed in:** `0f25b6f` (Task 1 GREEN)

---

**Total deviations:** 1 auto-fixed (Rule 1, explicitly directed by this plan's own `<action>` text: "update only those existing tests whose assertion is the old serve-everywhere convention")
**Impact on plan:** No scope change beyond what the plan itself called for. `companion/test_companion_app_02.py`/`03.py` are not in the plan's `files_modified` frontmatter list but their edits were the plan's own explicit instruction.

## Issues Encountered
None beyond the deviation above.

## User Setup Required

None. No config, env var, or deploy-pipeline change; the companion service picks up the smaller per-page script set on its next normal restart.

## Next Phase Readiness

`layout.page_shell(scripts=...)`, `layout.GLOBAL_PAGE_SCRIPTS`/`SHELL_SCRIPT_ORDER`, and `companion/app.py`'s `_PAGE_SCRIPTS` are in place and fully tested: `companion/test_page_scripts.py` (39 tests) plus the full companion suite (`-m "not browser"`, 1620 passed) and the whole-repo suite with the Playwright shim (2959 passed, 1 known local Chromium-baseline failure unrelated to this plan — `test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script`, per the orchestrator's own note — 6 skipped, coverage 94.10% against the 93.0% floor). EFF-02 is fully closed by this plan.

Phase 42 (OTA) is explicitly at risk here, as flagged by `38-RESEARCH.md` Pitfall 3 and repeated in this plan's own `<conventions>`: an Update page added to `layout.NAV_TABS`/`companion/app.py` without a `_PAGE_SCRIPTS` entry will fail `test_every_nav_tab_route_has_a_page_scripts_tuple`, naming the missing route — that test is the guard, not a manual reminder.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All 6 named files found on disk; both named commit hashes (`40bc5ac`, `0f25b6f`) found in `git log --oneline --all`.
