---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 11
subsystem: api
tags: [python, stdlib-http-server, refactor, page-context]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys (plans 40-04, 40-06, 40-08, 40-09, 40-10)
    provides: routes table, static allowlist, render()/handle_post() split, body-drain/cookie helpers, live-age conversions - the app.py shape this plan's typed context slots into
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: the _LazyContext laziness/sharing invariants this plan preserves byte-for-byte (one-SQLite-connection-per-request, freshness 304 path, per-page script sets)
provides:
  - companion/page_context.py - PageContext (typed, lazy, __slots__-based ctx), build_page_context(handler), coerce()
  - every page module (home_page, history_page, airlines_page, health_page, config_page) and every shared reader (ui_components.frame_strip_html, screens.current_screen_id, freshness._page_freshness_token, settings/calendar.calendar_disconnect_confirm_page, settings/rules.rules_usage_row_html) reading ctx by attribute, never dict-style
  - companion/app.py under the 1500-line ceiling (1196 lines), _LazyContext deleted
affects: [companion architecture cleanup, any future phase touching companion/pages/*.py's ctx contract]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Typed per-request context object with __slots__ eager fields plus a lazy-loader dict, replacing a dict-subclass god object"
    - "coerce() as the single boundary converting a plain test-fixture mapping into the typed object, rejecting unknown keys by name"
    - "Deferred (function-local) imports to break a would-be circular import between a shared module and the leaf modules it only needs at call time"

key-files:
  created:
    - companion/page_context.py
  modified:
    - companion/app.py
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/pages/health_page.py
    - companion/pages/config_page.py
    - companion/pages/__init__.py
    - companion/ui_components.py
    - companion/screens.py
    - companion/freshness.py
    - companion/flash.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/test_page_context.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_05.py
    - companion/test_status_pages_05.py
    - companion/test_status_pages_07.py
    - companion/test_view_pages_03.py
    - companion/test_view_pages_04.py
    - companion/test_structure_guards.py

key-decisions:
  - "PageContext keeps mapping-compatibility (__getitem__/get/__contains__) only through Task 2, deleted in Task 3 once every production reader uses attribute access - exactly as the plan specified"
  - "page_context.py defers its companion.pages.{health_page,airlines_page,history_page} and companion.flash imports to function-call time (not module level) to break a real circular import: those modules (via companion.flash importing config_page/airlines_page) import page_context.coerce() at their own module level"
  - "companion/settings/rules.py (a real ctx reader found only by grepping the whole tree, not listed in the plan's files_modified) was migrated too - required by the plan's own Task 3 acceptance grep, which scans all of companion/"
  - "Renamed config_page.py's local calendar_ctx dict to calendar_status - an unrelated local variable whose name happened to shadow-match the CMP-04 completion grep"
  - "Removed app.py's own now-stale entry from test_structure_guards.py's PENDING_OVERSIZED_FILES allowlist, since app.py is back under the 1500-line ceiling"

requirements-completed: [CMP-04, CMP-03]

# Metrics
duration: ~30min
completed: 2026-09-27
---

# Phase 40 Plan 11: Typed PageContext (CMP-04) Summary

**Replaced companion/app.py's `_LazyContext` dict-subclass god object with a typed, `__slots__`-based `PageContext` in a new `companion/page_context.py`, migrating every production reader (5 page modules + 5 shared readers) to attribute access while preserving every Phase 38 laziness/sharing invariant byte-for-byte.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 (as planned)
- **Files modified:** 20 modified, 1 created (companion/page_context.py)

## Accomplishments

- `companion/page_context.py`: `PageContext` (eager fields as real `__slots__` attributes, lazy fields resolved at most once via `__getattr__`, retry-after-raise, `is_resolved()`), `build_page_context(handler)` (the old `page_context()` method body, moved verbatim), and `coerce()` (converts a plain mapping, rejecting unknown keys by name; passes a `PageContext` through unchanged; never runs a loader).
- `companion/app.py`'s `Handler.page_context()` is now a one-line delegation; `_LazyContext` and its 9 associated helper functions are gone from app.py (rebound under their historical names for tests that still read them off `companion.app`). File dropped from ~1468 to 1196 lines, comfortably under the 1500-line ceiling, and removed from `test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` allowlist.
- Every shared reader (`ui_components.frame_strip_html`, `screens.current_screen_id`, `freshness._page_freshness_token`, `settings/calendar.calendar_disconnect_confirm_page`) and every page module's public ctx-taking entry point (`render()`, `handle_post()`, `history_page.flights_limit()`, `home_page._status_tiles_html()`/`_current_picture_html()`) now calls `page_context.coerce(ctx)` once at the top; every private helper receives the already-typed object and reads it by plain attribute access.
- `PageContext`'s temporary `__getitem__`/`get`/`__contains__` mapping-compatibility methods (kept through Task 2 for a smooth migration) are deleted; the full companion suite (1726 checks, 3 skipped for root-permission reasons) passes with zero dict-style ctx access left in production code.
- `companion/test_render_baseline.py` (the byte-equality baseline from plan 40-10) still passes unchanged — every page's rendered output is untouched by this refactor.

## Task Commits

1. **Task 1: PageContext type with lazy fields, and its builder** - `49b222c` (refactor)
2. **Task 2: Migrate shared ctx readers** - `a083851` (refactor)
3. **Task 3: Migrate the five page modules to typed attribute access** - `3fe905e` (refactor)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `companion/page_context.py` - new: `PageContext`, `EAGER_FIELDS`/`LAZY_FIELDS`/`ALL_FIELDS`, `coerce()`, `build_page_context()`, and the 8 loader/helper functions moved out of `app.py`
- `companion/app.py` - `_LazyContext` and its helpers deleted/rebound; `page_context()` is a one-liner; drops to 1196 lines
- `companion/pages/{home_page,history_page,airlines_page,health_page,config_page}.py` - every ctx reader migrated to `PageContext` attribute access, with `coerce()` at each public entry point
- `companion/pages/__init__.py` - ctx contract docstring rewritten for `PageContext` instead of a plain dict
- `companion/ui_components.py`, `companion/screens.py`, `companion/freshness.py`, `companion/settings/calendar.py`, `companion/settings/rules.py` - shared ctx readers migrated
- `companion/flash.py` - one comment corrected (`ctx.flash_role` instead of `ctx["flash_role"]`)
- `companion/test_page_context.py` - unit section rewritten against `PageContext` (`is_resolved()` replaces `in`); server-level test bodies unchanged except retargeting the `gallery_entries` monkeypatch to its new defining module
- `companion/test_companion_app_02.py` - two checks that exercised a REAL `PageContext` (via `Handler.page_context()`) through the now-deleted dict-style API, converted to attribute access / `is_resolved()`
- `companion/test_companion_app_05.py`, `companion/test_status_pages_05.py`, `companion/test_status_pages_07.py`, `companion/test_view_pages_03.py`, `companion/test_view_pages_04.py` - dead `"simple_mode": False` fixture keys removed (see Deviations)
- `companion/test_structure_guards.py` - `companion/app.py` removed from `PENDING_OVERSIZED_FILES`

## Decisions Made

- Deferred (function-local, not module-level) imports of `companion.pages.{health_page,airlines_page,history_page}` and `companion.flash` inside `companion/page_context.py` — those modules import `page_context.coerce()` at their own module level (directly, or transitively through `companion.flash` importing `config_page`/`airlines_page`), so a module-level import the other way would cycle. Verified with a direct `import companion.app` smoke test after every edit.
- `companion/settings/rules.py`, not listed in the plan's `files_modified`, needed the same migration: it is a real ctx reader (`rules_usage_row_html(ctx)`, called from `config_page.py` with the request's real `PageContext`) that the plan's own Task 3 acceptance grep (scanning all of `companion/`, not just the listed files) would otherwise still flag. Treated as in-scope per the plan's literal acceptance criteria.
- Renamed `config_page.py`'s local `calendar_ctx` dict (built by `_render_calendar_and_poll_context()`) to `calendar_status`, since `calendar_ctx["..."]` was a false-positive match against the same completion grep despite being an unrelated local variable, not the page's own `ctx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `coerce()` surfaced dead `"simple_mode": False` fixture keys as unknown-field errors**
- **Found during:** Task 2 (running the plan's own verify command against `test_status_pages_07.py`)
- **Issue:** `page_context.coerce()` correctly rejects any ctx mapping key that isn't a declared `PageContext` field. Several test fixture ctx dicts across `test_status_pages_05.py`, `test_status_pages_07.py`, and `test_view_pages_03.py`/`04.py` (7 call sites) carried a `"simple_mode": False` key left over from a fully retired display-mode switch (confirmed dead in production code by `test_companion_app_05.py`'s own `test_no_companion_module_redefines_the_retired_display_mode_switch`) — a real typo/leftover, not a real field.
- **Fix:** Removed the dead key from all 7 fixture dicts; corrected `test_companion_app_05.py`'s own comment (which had claimed these keys still existed only as harmless unrelated leftovers) to note they've now been removed.
- **Files modified:** `companion/test_status_pages_05.py`, `companion/test_status_pages_07.py`, `companion/test_view_pages_03.py`, `companion/test_view_pages_04.py`, `companion/test_companion_app_05.py`
- **Verification:** Full companion suite green (1726 passed, 3 skipped)
- **Committed in:** `a083851` (Task 2 commit)

**2. [Rule 3 - Blocking] Two `test_companion_app_02.py` checks used the now-deleted dict-style API on a REAL PageContext**
- **Found during:** Task 3, after deleting `PageContext.__getitem__`/`get`/`__contains__`
- **Issue:** `test_page_context_threads_wake_interval_env_default` and `test_page_context_supplies_resolve_prefix_and_manual_resolutions` call `Handler.page_context()` directly (not a plain-dict fixture) and then read the result with `.get()`/`[...]`/`in` — these are the one place in the suite exercising the real object through the mapping API the plan says to delete.
- **Fix:** Converted every such read to attribute access (`ctx.wake_interval_env_default`) or `ctx.is_resolved(name)` for the two "always present" membership checks.
- **Files modified:** `companion/test_companion_app_02.py`
- **Verification:** Full companion suite green (1726 passed, 3 skipped)
- **Committed in:** `3fe905e` (Task 3 commit)

**3. [Rule 2 - Missing critical functionality] `companion/settings/rules.py` was a real ctx reader missing from the plan's files_modified list**
- **Found during:** Task 3, before deleting the mapping-compatibility methods
- **Issue:** `rules_usage_row_html(ctx)` (called from `config_page.py`'s Display scope with the request's real ctx) still read `ctx.get("colour_rules")`/`ctx.get("state_dir")`. Deleting the mapping methods without fixing this file would have broken it at runtime, and the plan's own Task 3 acceptance grep (`grep -rnE 'ctx(\.get\(|\[)"' companion --include=*.py`) scans the whole tree, not just files_modified.
- **Fix:** Migrated to plain attribute access (`ctx.colour_rules`, `ctx.state_dir`); no `coerce()` needed since it is only ever called with an already-typed ctx.
- **Files modified:** `companion/settings/rules.py`
- **Verification:** Task 3's acceptance grep now returns 0; full companion suite green
- **Committed in:** `3fe905e` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 1 blocking, 1 missing-scope item)
**Impact on plan:** All three were necessary for the plan's own acceptance criteria and correctness; none change rendered output (confirmed by `test_render_baseline.py` staying green throughout) or widen `PageContext`'s field vocabulary.

## Issues Encountered

- A genuine circular-import risk: `companion/page_context.py` needs `companion.pages.health_page`/`airlines_page`/`history_page` and `companion.flash`, but those modules (directly, or via `flash` importing `config_page`/`airlines_page`) need `page_context.coerce()`. Resolved by making `page_context.py`'s own imports of those four modules function-local (deferred to call time) rather than module-level, while the five page modules and shared readers import `page_context` normally at their own top level. Verified with a plain `import companion.app` smoke test after each file's edit, before running any test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CMP-04 and this plan's slice of CMP-03 (moving the context builder out of `app.py`) are both complete; `app.py` is at 1196 lines, well under the 1500-line ceiling.
- `companion/pages/health_page.py` remains the one file still over the ceiling in `test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` allowlist — unrelated to this plan, left for whichever later plan in this phase addresses it.
- No blockers for the remaining phase 40 plans.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: companion/page_context.py
- FOUND commit: 49b222c (Task 1)
- FOUND commit: a083851 (Task 2)
- FOUND commit: 3fe905e (Task 3)
