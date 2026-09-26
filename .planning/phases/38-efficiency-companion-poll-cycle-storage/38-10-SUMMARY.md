---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 10
subsystem: companion
tags: [lazy-evaluation, health-page, severity, python, pytest]

# Dependency graph
requires:
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-05's health_signals()/safe_health_signals()/health_state_from_signals() split - the severity-without-markup interface this plan's lazy loaders call"
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-08's one-connection-per-companion-request wiring - the connection_scope() this plan's poll_cooldown_remaining degrade relies on to see a remembered failure rather than retry"
provides:
  - "companion/app.py: _LazyContext(dict) - a page_context() ctx whose expensive values (health_state/health_severity, gallery_entries, manual_resolutions, colour_rules, the calendar registry, poll_cooldown_remaining) resolve at most once, only when a route actually reads them"
  - "companion/app.py: _not_found_page()/_forbidden_page() read health_page.safe_health_signals() directly (severity alone), never the full safe_health_state() markup build"
  - "companion/app.py: poll_cooldown_remaining's lazy ctx value degrades to 0 on (sqlite3.Error, OSError) instead of raising through a page render"
affects: ["38-12 (freshness token - reads the same health_signals()/severity path this plan made lazy)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A dict subclass with a loaders map, overriding __getitem__/get()/__contains__ so a pending loader looks the same to every access pattern a plain dict ctx already supported, and resolves at most once"
    - "A shared internal loader key (leading underscore, e.g. _health_signals, _calendar_registry) backing several public ctx keys, so three separate config_page.render() reads of calendar_last_synced_at/calendar_last_attempt_at/calendar_entry_count still cost one registry load"
    - "A lazy loader closes over the ctx object itself (via the enclosing method's local variable, kept alive by the closure after the method returns) so one loader can read another already-resolved key without recomputing it - health_severity reads health_state via dict.__contains__()/dict.__getitem__() directly, bypassing _LazyContext's own __contains__() so the check itself never triggers a build"

key-files:
  created:
    - companion/test_page_context.py
  modified:
    - companion/app.py

key-decisions:
  - "health_severity's loader checks whether 'health_state' was already resolved via dict.__contains__(ctx, ...)/dict.__getitem__(ctx, ...) - the real dict storage, bypassing _LazyContext's own overridden __contains__() (which treats a pending loader as present) - so the check for 'has Home/Health already built markup' can never itself trigger that build."
  - "poll_cooldown_remaining's plain module-level function stays unguarded (still called directly by _handle_poll_now() and _resolve_flash_text()'s FLASH_KEY_POLL_COOLDOWN branch, both of which need a database fault to surface, not hide); only the new page_context() lazy loader (_safe_poll_cooldown_remaining) degrades to 0, since a page render's own cooldown display is decorative."
  - "gallery_entries is read by both Home and Flights (history_page.py's own ctx.get('gallery_entries') read, found while implementing rather than assumed from the plan's own hedged wording) - the plan's '0 calls on /flights' bullet for that specific loader is satisfied instead as 'exactly one call', with the other three loaders (manual_resolutions/colour_rules/the calendar registry) confirmed at zero."

requirements-completed: []  # EFF-04 spans 38-05/10/12; not marked complete here per phase coordination note.

# Metrics
duration: ~55min
completed: 2026-09-26
---

# Phase 38 Plan 10: Lazy page context and markup-free severity Summary

**`page_context()` now returns a `_LazyContext`: Health's markup, the gallery listing, three registry loads and the poll cooldown all resolve at most once, only if a route's own render() or the nav-dot read actually touches them - collapsing every tab's unconditional Health-markup build down to the two pages (Home, Health) that render it.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-26T19:10:00Z (approx.)
- **Completed:** 2026-09-26T20:05:00Z (approx.)
- **Tasks:** 1 completed
- **Files modified:** 2 (1 created)

## Accomplishments
- New `_LazyContext(dict)` in `companion/app.py`: constructed with the request's cheap values already computed eagerly plus a `loaders` mapping of key -> zero-argument callable. `__getitem__` resolves a pending loader once and caches it via `dict.__setitem__`; `get()`/`__contains__` are both overridden (`dict.get()` never calls `__missing__`) so every access pattern a plain dict ctx already supported - `ctx["k"]`, `ctx.get("k")`, `"k" in ctx`, `ctx.get("missing", default)` - sees the same lazily-resolved, once-only value.
- `page_context()` rewritten: `state_dir`, `ui_theme`, `lang`, `device_config`, `screen_id`, `last_checkin_ts`, `battery_critical`, `wake_interval_env_default`, `flash`, `flash_role`, `runway_images`, `now`, `resolve_prefix` and `flights_limit` stay eager (every route needs them, or a later value depends on one); `health_state`/`health_severity`/`gallery_entries`/`manual_resolutions`/`colour_rules`/the three calendar registry keys/`poll_cooldown_remaining` are lazy. A shared internal `_health_signals` loader (`health_page.safe_health_signals()`) backs both `health_state` (the markup `health_page.health_state_from_signals()` builds, read only by Home and Health) and `health_severity` (read by every tab's nav dot) - `health_severity`'s loader takes the severity from `health_state` without recomputing anything once that markup was already built, and from the shared signals snapshot otherwise, so a route that never reads `health_state` still pays for exactly one `health_signals()` call, never two. A shared internal `_calendar_registry` loader backs `calendar_last_synced_at`/`calendar_last_attempt_at`/`calendar_entry_count`, so `config_page.render()`'s three separate reads of those keys still cost one `calendar_rules.load_calendar_registry()` call; `calendar_configured`/`calendar_drift` keep their own file-mode reads (`calendar_is_configured()`/`calendar_secret_mode_is_unsafe()`), never the registry.
- New `_safe_poll_cooldown_remaining(state_dir)`: the lazy ctx loader's own wrapper, degrading to 0 on `(sqlite3.Error, OSError)` - the plain module-level `poll_cooldown_remaining()` itself stays unguarded, since `_handle_poll_now()` and the `FLASH_KEY_POLL_COOLDOWN` flash text both still need a database fault to surface rather than hide.
- `_not_found_page()`/`_forbidden_page()` now call `health_page.safe_health_signals()` directly for the nav-dot severity, never the full `safe_health_state()` markup build - still gated on `self._is_authenticated()` so Health's warn/error state never leaks pre-auth.
- New `companion/test_page_context.py` (10 tests, against a real running server via `app_server_in_process`, never source text): `_LazyContext`'s own getitem/get/contains contract (4 tests); `health_state_from_signals()` building markup on Home/Health only while `health_signals()` still runs exactly once on every one of the six tab routes; a seeded stale-device (warn) scenario showing the warn nav dot on Flights and proving the nav dot and the Health page's own banner agree in the same response (parsed from served HTML, not computed independently); an authenticated 404 computing severity from `health_signals()` alone with zero `health_state_from_signals()` calls, and an unauthenticated 404 running zero `health_signals()` calls either; the four expensive registries loading at most once per request on every tab, with zero calls on Flights for the three it does not read (gallery_entries is the exception - Flights does read it, so that count is exactly one, not zero; found while implementing, not assumed); a `sqlite3.connect`-raising fault degrading Home, Flights and Device to 200, with Device's poll-trigger button rendering enabled rather than disabled by a stale cooldown; and a plain dict ctx still rendering correctly through `config_page.render()`.

## Task Commits

Each task was committed atomically, following its `tdd="true"` RED/GREEN gates:

1. **Task 1 (RED): failing tests for lazy page_context and markup-free severity** - `0286ab6` (test)
2. **Task 1 (GREEN): _LazyContext, lazy page_context, safe_health_signals-only 404/403** - `33e3603` (feat)

**Plan metadata:** (this commit) - `docs(38-10): complete lazy page_context and markup-free severity plan`

## Files Created/Modified
- `companion/app.py` - New `_LazyContext(dict)`; `page_context()` rewritten to return one, with cheap values eager and Health/gallery/manual-resolutions/colour-rules/calendar/poll-cooldown lazy; new `_lazy_health_state()`/`_lazy_health_severity()`/`_safe_poll_cooldown_remaining()` module-level loader helpers; `_not_found_page()`/`_forbidden_page()` switched to `health_page.safe_health_signals()`.
- `companion/test_page_context.py` - New: 10 tests covering `_LazyContext`'s contract, markup-build-site counts, the nav-dot/banner agreement, the 404 page's auth-gated severity, the four registries' at-most-once-per-request loads, the database-fault degrade, and a plain-dict ctx still working.

## Decisions Made
- `health_severity`'s loader checks whether `health_state` was already resolved via `dict.__contains__(ctx, "health_state")`/`dict.__getitem__(ctx, "health_state")` - real dict storage, bypassing `_LazyContext`'s own overridden `__contains__()` (which treats a pending loader as present) - so that check itself can never trigger the markup build it is trying to avoid recomputing from.
- `poll_cooldown_remaining()` (the plain module-level function) stays unguarded exactly as 38-08 left it; only the new lazy ctx loader degrades to 0, per the plan's own `<action>` and `38-CONTEXT.md`'s "Claude's Discretion" note approving this as a small robustness win scoped to the page-render path alone.
- Empirically confirmed (rather than assumed from the plan's own hedged "(if Flights does not read them)" wording) that `history_page.py` (Flights) reads `ctx.get("gallery_entries")` for its lightbox thumbnails, so that loader's "0 calls on /flights" plan bullet is satisfied instead as "exactly one call" - the other three loaders (`manual_resolutions`/`colour_rules`/the calendar registry) are confirmed at zero for Flights, matching the plan.
- Verified the seeded "warn" scenario (a device check-in 600s stale, past the default 300s warn floor but under the 1200s error floor) resolves to `severity == "warn"` by running `health_page.health_signals()` directly before writing the test against it, rather than assuming a threshold boundary.

## Deviations from Plan

### Process deviation (not a code change)

**1. `check_comment_history.py` caught a requirement ID in the new test module's own docstring**

- **Found during:** the plan's own verify command, after the RED/GREEN split.
- **Issue:** `companion/test_page_context.py`'s module docstring originally read "Lazy `page_context()` and markup-free severity (EFF-04).", carrying the phase's own requirement ID - forbidden by `.claude/CLAUDE.md`'s "no plan/phase/requirement IDs in comments" rule, enforced by `scripts/check_comment_history.py check`.
- **Fix:** Reworded to "Lazy `page_context()` and markup-free severity." with no ID. Folded into the GREEN commit (`33e3603`) alongside `companion/app.py`, since the RED commit (`0286ab6`) had already landed with the violation and amending is disallowed.
- **Files affected:** `companion/test_page_context.py` (docstring wording only, no behaviour change).

---

**Total deviations:** 0 code deviations; 1 process deviation (a requirement-ID wording slip in a test docstring, caught and fixed before the plan's own verify command was accepted as green).

## TDD Gate Compliance

Task 1 declares `tdd="true"`. Both gates are present in git log: `0286ab6` `test(38-10): add failing tests for lazy page_context and markup-free severity` (RED - verified by running the new test file against the pre-plan `companion/app.py`, restored via `git show HEAD:companion/app.py`: 8 of 10 tests failed), then `33e3603` `feat(38-10): lazy page_context and markup-free severity` (GREEN - all 10 pass against the real implementation). The two RED-phase passes were expected and are documented in the RED commit's own message: they assert invariants (the warn nav-dot/banner agreement, and a plain dict still working for a page module's `render()`) that already held independently of this plan's change, not properties the change itself introduces. No REFACTOR-gate commit was needed.

## Issues Encountered

None beyond the docstring wording slip above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 38-12 (the D-2 freshness token) can now read `health_page.health_signals()`/`safe_health_signals()` for the same severity/anomaly/next-wake-triple data this plan's `_health_signals` loader already fetches once per request, without paying for markup - exactly the lazy foundation EFF-04's freshness slice needs.
- `_LazyContext` is additive: every existing page module's own unit tests (which pass a plain dict, never `_LazyContext`) stay green unchanged, confirmed by the full companion suite and one new explicit check in `test_page_context.py`.
- Plan verify green: `test_page_context.py` + `test_request_connections.py` + `test_health_signals.py` + `test_suite_guards.py` (126 passed); full companion suite not-browser (1638 passed, 2 skipped); whole-repo `./scripts/run-all-tests.sh -m "not browser"` (2862 passed, 6 skipped); with the Playwright shim (2991 passed, 6 skipped, 1 known local Chromium-baseline failure unrelated to this plan - `test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script`); ruff and `check_comment_history.py` both clean; coverage 94.21%.
- EFF-04 stays open - 38-12 (the D-2 freshness token) is next; this plan's own two must_haves ("Display/Device/Flights/Airlines build no Health markup", "the poll cooldown degrades on a database error") are both closed.
- No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

- FOUND: companion/app.py
- FOUND: companion/test_page_context.py
- FOUND: .planning/phases/38-efficiency-companion-poll-cycle-storage/38-10-SUMMARY.md
- FOUND: 0286ab6
- FOUND: 33e3603
