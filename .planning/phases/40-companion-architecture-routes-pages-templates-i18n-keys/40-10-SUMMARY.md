---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 10
subsystem: ui
tags: [companion, html-templating, playwright, i18n, escaping]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "Plans 40-05..40-09's route table, static allowlist, page/context split, named templates, and app.py decomposition — this plan runs after all of them so the render baseline it regenerates reflects their landed, behaviour-preserving state"
provides:
  - "Flights desktop When cell, Display's Calendar status detail, and Health's unresolved-prefix registry cells now render their relative age as a live <time data-relative> element (CFG-34, all three clauses)"
  - "A regenerated companion/testdata/render_baseline.json whose only diff from the previous baseline is the three sites' added <time> wrappers, proven by a wrapper-only diff check"
  - "A reusable escaping pattern (build primary/secondary halves separately, splice pre-escaped markup) for the two call sites that need it, without widening _merged_cell()'s or status_row()'s general contract"
affects: [companion-pages, companion-settings, design-system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bypass a shared escaping helper only at the exact call site that needs markup, by building that one branch inline with the same CSS classes the helper emits, rather than widening the helper's own contract (history_page._when_cell_html, settings.calendar._status_row_with_html_detail)"
    - "Playwright virtual clock (page.clock.install() before navigation + page.clock.run_for()) to prove a minutes-range ticking element crosses a bucket boundary without a real wall-clock wait"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/settings/calendar.py
    - companion/pages/health_page.py
    - companion/testdata/render_baseline.json
    - companion/test_view_pages_03.py
    - companion/test_config_page_05.py
    - companion/test_status_pages_03.py
    - companion/test_status_pages_04.py
    - companion/test_browser_ux_03.py
    - .claude/skills/sketch-findings-skypane/references/data-density.md

key-decisions:
  - "Bypassed _merged_cell()/status_row() only at the two call sites CFG-34 needs (history_page's When cell, settings.calendar's status detail), following home_page._recent_flight_time_html()'s build-and-concatenate precedent — neither helper's general contract or other callers changed, proven by the wrapper-only baseline diff"
  - "health_page's registry cell needed no bypass — it already built its own <span> markup, so relative_age_text() was a direct drop-in swap for relative_time_html()"
  - "Battery-trend tooltip (the fourth static age) stays static and is documented as the one deliberate exception in the design system, per developer decision and its own structural constraint (an SVG <title> written via setAttribute cannot hold an element)"

requirements-completed: [CFG-34]

# Metrics
duration: ~45min
completed: 2026-09-27
---

# Phase 40 Plan 10: CFG-34 live ages (Flights, Calendar, Health) Summary

**Converts Flights' When cell, Display's Calendar status detail, and Health's registry cells from static relative-age text into live `<time data-relative>` elements ticked by relative-time.js, via two new local escaping-bypass helpers that leave `_merged_cell()`/`status_row()`'s contracts untouched.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-27
- **Tasks:** 2 (both from the plan)
- **Files modified:** 10

## Accomplishments

- `history_page._when_cell_html()`'s has-age branch now splices `layout.relative_time_html()`'s pre-escaped `<time data-relative>` markup as the When cell's secondary half, inline, bypassing `_merged_cell()` for that one branch only (its fallback/unparseable branches still call it unchanged)
- `settings.calendar._calendar_status_html()`'s "usable" branch does the same for the Calendar row's "N entries, refreshed Xm ago" detail, via a new `_status_row_with_html_detail()` helper that reproduces `layout.status_row()`'s exact markup but splices pre-escaped detail HTML instead of re-escaping it
- `health_page._registry_seen_cell_html()` swaps `escape_html(layout.relative_age_text(age))` for `layout.relative_time_html(raw_ts, now)` directly — no bypass needed, since this function already built its own markup
- Regenerated `companion/testdata/render_baseline.json`; a purpose-built wrapper-only diff check (stripping every `<time datetime="..." data-relative>...</time>` from both the old and new baseline) proved the two documents are otherwise byte-identical, and that the only keys gaining `<time>` elements are Flights (+15, one per seeded row), Display (+1, the calendar status), and Health (+2, First/Last seen)
- Added unit tests for all three sites (parsed-HTML assertions on the `time[data-relative]` element's text/datetime, plus a `&lt;time` double-escaping guard) and a parametrised Playwright browser test proving each site's age genuinely ticks, using Playwright's virtual clock (installed before navigation, then run forward 65 virtual seconds) to cross a minute boundary without a real wall-clock wait
- Updated `data-density.md`'s design-system reference: the four-row "still static" table is kept verbatim (its per-site reasoning is exactly what a future editor needs), with a new resolution paragraph marking (a)-(c) live and (d) — the battery-trend tooltip — as the one remaining, structurally-forced exception

## Task Commits

Each task was committed atomically, plus three small follow-up fixes discovered during verification (all Rule 1/Rule 3 — see Deviations):

1. **Task 1: Convert the three sites and regenerate the baseline** - `e9abde8` (feat)
2. Follow-up fix: drop ticket-id references from CFG-34 docstrings - `eab914e` (fix)
3. **Task 2: Browser proof of ticking and the enumerated exception** - `bbac90f` (test)
4. Follow-up fix: drop unused `parse_html` import from the Flights ticker test - `7ecd354` (fix)
5. Follow-up fix: update `test_status_pages_04.py`'s registry-pairing test for the desktop cell's now-live age - `04e7e31` (fix)

**Plan metadata:** committed together with this SUMMARY (see `<state_updates>`/`<final_commit>` below).

## Files Created/Modified

- `companion/pages/history_page.py` - `_when_cell_html()`'s has-age branch now splices live markup; `_merged_cell()` itself untouched
- `companion/settings/calendar.py` - new `_status_row_with_html_detail()` helper; `_calendar_status_html()`'s "usable" branch uses it
- `companion/pages/health_page.py` - `_registry_seen_cell_html()`'s secondary span now uses `relative_time_html()`
- `companion/testdata/render_baseline.json` - regenerated; wrapper-only diff versus the previous baseline (proof recorded below)
- `companion/test_view_pages_03.py` - new Flights When-cell live-element test
- `companion/test_config_page_05.py` - new Calendar status-detail live-element test
- `companion/test_status_pages_03.py` - new Health registry-cell live-element test
- `companion/test_status_pages_04.py` - existing registry-pairing test updated for the desktop cell's new markup
- `companion/test_browser_ux_03.py` - new parametrised browser ticker proof over all three sites
- `.claude/skills/sketch-findings-skypane/references/data-density.md` - resolution note; (d) recorded as the sole remaining exception

## Decisions Made

- Followed the plan's escaping resolution exactly: bypass `_merged_cell()`/`status_row()` only at the two call sites that need markup, by building that branch inline with the same CSS classes, rather than widening either helper's contract
- No bypass needed for `health_page`'s cell — it already built its own `<span>` markup outside any shared helper, so the change there was a direct one-line swap
- Used Playwright's virtual clock (`page.clock.install()` + `page.clock.run_for()`) rather than a real multi-minute wall-clock wait, matching the existing login-lockout countdown test's own technique in this codebase, since the plan calls for ages seeded "in the minutes range" (a real-time wait to cross a minute boundary would be too slow for CI)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed ticket-ID references from new docstrings/comments**
- **Found during:** post-Task-1 verification (`scripts/check_comment_history.py check`)
- **Issue:** New docstrings in `test_browser_ux_03.py` referenced "CFG-34" literally; a bare `CFG-34` (no letter suffix) tripped the comment-history linter's `prefix-id` pattern, and the `CFG-34a`/`b`/`c` variants in the Task 1 files evaded the regex on a boundary technicality but still violated CLAUDE.md's "no plan/ticket IDs in comments" rule in spirit
- **Fix:** Removed the parenthetical ticket references from all six affected files' docstrings/comments; no behaviour change
- **Files modified:** `companion/settings/calendar.py`, `companion/pages/health_page.py`, `companion/test_view_pages_03.py`, `companion/test_config_page_05.py`, `companion/test_status_pages_03.py`, `companion/test_browser_ux_03.py`
- **Verification:** `scripts/check_comment_history.py check` now exits 0
- **Committed in:** `eab914e`

**2. [Rule 3 - Blocking] Dropped an unused import ruff flagged**
- **Found during:** post-Task-2 lint pass (`ruff check`)
- **Issue:** `test_view_pages_03.py`'s new Flights test imported `companion_markup.parse_html` locally but never called it directly (it uses `test_view_pages_helpers.row_block()`, which imports `parse_html` itself)
- **Fix:** Removed the unused import
- **Files modified:** `companion/test_view_pages_03.py`
- **Verification:** `ruff check` clean; the test still passes
- **Committed in:** `7ecd354`

**3. [Rule 1 - Bug] Fixed a pre-existing test broken by the Health registry conversion**
- **Found during:** full non-browser companion suite run (`pytest companion/ -m "not browser"`), outside the plan's own named test files
- **Issue:** `test_status_pages_04.py::test_registry_mobile_cards_paired_with_the_desktop_table` asserted the desktop registry cell's age half was `escape_html(relative_age_text(...))` — the exact shape this plan intentionally replaced with a live `<time data-relative>` element
- **Fix:** Updated the test's `expected_cell` construction to use `layout.relative_time_html(raw_ts, now_iso)` for the age half, matching `health_page._registry_seen_cell_html()`'s new construction; the mobile card's own assertions (still `concise_timestamp_html()`-based) were untouched since that side was not converted
- **Files modified:** `companion/test_status_pages_04.py`
- **Verification:** `pytest companion/test_status_pages_04.py -k registry_mobile_cards_paired` passes; full non-browser companion suite (1723 passed, 3 skipped) and the full browser suite for `test_browser_ux_01/02/03/04.py` (104 passed) both green afterward
- **Committed in:** `04e7e31`

---

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 3)
**Impact on plan:** All three were necessary corrections to the plan's own intended behaviour change or to internal code-quality gates; none changed the plan's scope or the three converted sites' final shape.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## Wrapper-Only Diff Check (recorded per the plan's acceptance criteria)

Ran a one-off script comparing the pre-plan baseline (captured via `git show` at the commit this plan started from, before any edits) against the regenerated one, stripping every `<time datetime="..." data-relative>...</time>` element (keeping its inner text) from both sides before comparing:

```
Keys with non-wrapper differences: 0

Keys with added <time data-relative> elements:
  /display?flash=saved|en|dark: +1
  /display?flash=saved|en|light: +1
  /display?flash=saved|fr|dark: +1
  /display?flash=saved|fr|light: +1
  /display|en|dark: +1
  /display|en|light: +1
  /display|fr|dark: +1
  /display|fr|light: +1
  /flights|en|dark: +15
  /flights|en|light: +15
  /flights|fr|dark: +15
  /flights|fr|light: +15
  /health|en|dark: +2
  /health|en|light: +2
  /health|fr|dark: +2
  /health|fr|light: +2

PASS: wrapper-only diff confirmed.
```

Zero non-wrapper differences across every page key, in both languages and both themes; additions confined to exactly the three converted sites (Flights: 15 seeded rows × 1 age each; Display: 1 calendar status row; Health: 2 registry cells for the one seeded unresolved prefix).

## Known Stubs

None.

## Threat Flags

None — the two bypass sites are covered by this plan's own threat register (T-40-20, T-40-21), and no new network endpoint, auth path, or trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- This was the only plan in Phase 40 expected to change rendered output; the render baseline is now the new steady state for any later plan in this phase to verify against
- CFG-34's clause 1 ("every relative age on screen is live") holds with exactly one enumerated, justified exception (the battery-trend tooltip), matching the plan's own success criterion
- No blockers for subsequent Phase 40 plans

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*
