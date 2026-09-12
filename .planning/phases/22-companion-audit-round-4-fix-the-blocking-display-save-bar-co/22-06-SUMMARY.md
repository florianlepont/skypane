---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 06
subsystem: ui
tags: [timezone, zoneinfo, dst, battery, health-page, i18n]

# Dependency graph
requires:
  - phase: 22 (waves 1-3, plans 22-01..22-05)
    provides: the `.time-value`/`.time-value--primary`/`.time-value__age` CSS role (22-04) this plan adopts
provides:
  - Europe/Paris day bucketing for the battery trend chart, computed in Python (ZoneInfo), proven across both DST transitions
  - layout.local_clock_text() as the sole formatter for every visible battery time on Health (readout, sparkline tooltips/aria-labels/data-when, axis labels)
  - a corrected concise_timestamp_html() docstring and a local-full-timestamp title (no raw ISO) — every caller of that shared function inherits the fix
  - a battery-trend.js hover swap that reads only pre-formatted server text, with no raw-ISO fallback
affects: [22-11 (the airline resolve dialog's own raw-ISO half of D-05/CFG-28), 22-12 (Health tile anatomy), 22-16 (phase-closing verification)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Day bucketing that must respect a real-world timezone (DST) belongs in Python (datetime + ZoneInfo), never in SQLite's date()/strftime() modifiers — no fixed UTC-offset SQL modifier is DST-correct."
    - "A full (day-qualified) local timestamp is built by calling the existing local_clock_text(parsed, now_parsed=<a sentinel guaranteed to differ in Paris calendar day>) rather than writing a second, competing formatter — reused independently in both companion/layout.py and companion/pages/health_page.py."

key-files:
  created: []
  modified:
    - server/history_db.py
    - server/test_config_history.py
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - companion/static/battery-trend.js
    - companion/layout.py

key-decisions:
  - "daily_battery_averages() fetches battery_mv IS NOT NULL rows filtered by the existing since >= ? SQL comparison (index-preserving), then buckets in Python via datetime.fromisoformat(ts) treated as UTC when naive, .astimezone(ZoneInfo('Europe/Paris')).date() — GROUP BY date() is gone entirely."
  - "A sparkline point's <title>, aria-label and data-when are now the literal SAME string (previously title/aria-label carried 'value — when' while data-when carried only 'when') — data-mv already carries the value machine-readably, and battery-trend.js's own JS prepends the value separately, so keeping the composite in title/aria-label would have printed the value twice once JS took over and would have failed the plan's own same-string acceptance criterion."
  - "Every title/aria-label/data-when/readout-detail-title on Health is now a FULL Europe/Paris local timestamp (day + month + HH:MM), built by forcing layout.local_clock_text()'s own cross-day branch with a fixed sentinel now (1970-01-01), rather than the previous bare 'HH:MM' — this satisfies the plan's literal 'never a bare clock' criterion and keeps disambiguation available without relying on hover-only distinction."
  - "The .time-value role (22-04) is applied to the STABLE `.battery-readout__detail` wrapper span, not to a nested `.time-value__age` sibling: battery-trend.js's reveal() overwrites that span's textContent (never its class list) on every hover/tap, so a class on the outer span survives interaction while a nested child span would be silently destroyed on the very first hover — recorded here as a deliberate implementation choice, not a missing CSS rule."
  - "CFG-28's REQUIREMENTS.md row is annotated in progress, not checked off: the requirement also covers the airline resolve dialog (B5), which is plan 22-11's file (airlines_page.py), not this plan's."

requirements-completed: []

# Metrics
duration: ~30min (task work; excludes context-reading)
completed: 2026-09-12
---

# Phase 22 Plan 06: Paris local time everywhere on Health Summary

**Europe/Paris ZoneInfo-based day bucketing (proven across both DST transitions) plus one shared local_clock_text() formatter for every visible battery timestamp, tooltip, and axis label on the Health page.**

## Performance

- **Duration:** ~30 min of task execution (Task 1 → Task 2 → Task 3, each committed atomically)
- **Completed:** 2026-09-12
- **Tasks:** 3/3
- **Files modified:** 6

## Accomplishments

- `daily_battery_averages()` no longer groups with SQLite's UTC-only `date()`; bucketing moved to Python with `ZoneInfo("Europe/Paris")`, with new fixtures proving both the March (skipped hour) and October (repeated hour) DST transitions, plus the plan's own literal `01:30+02:00` example.
- Every visible battery time on Health (`_battery_reading_parts()`, the readout, every sparkline point's tooltip/aria-label/data-when, `_axis_clock_label()`, `_axis_day_label()`) now reads Paris local time; the literal `" UTC"` string no longer appears anywhere in a rendered Health page, in either language.
- The battery trend caption states the real number of readings rendered, not the `BATTERY_TREND_LIMIT` constant.
- `battery-trend.js`'s hover swap sets `title` from the pre-formatted `when` text (never the raw `ts`), and its no-data fallback no longer prints a raw ISO string; the file still contains zero client-side date parsing/formatting.
- `layout.concise_timestamp_html()`'s stale `"<HH:MM> UTC (<relative>)"` docstring is corrected, and its `title` attribute is now a full Europe/Paris local timestamp instead of the raw ISO — every existing caller of this shared function inherits the fix, and `companion/test_view_pages.py` (owned by plan 22-07) stayed green at its own pin throughout, because its assertions re-derive the expected markup live rather than hard-coding it.

## Task Commits

1. **Task 1: Move the daily battery bucketing out of SQL and into Europe/Paris days** — `bafd1bf` (fix)
2. **Task 2: Every visible battery time goes through the one formatter** — `402185a` (fix)
3. **Task 3: The client-side swap reads server text, and the stale docstring stops teaching the bug** — `13f383f` (fix)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `server/history_db.py` — `daily_battery_averages()` rewritten to bucket in Python via `ZoneInfo("Europe/Paris")`; new `_paris_day_or_none()` helper; docstring rewritten to describe the new mechanism and name the DST caveat explicitly (same accepted framing `seconds_until_quiet_hours_end()` uses).
- `server/test_config_history.py` — the existing bucketing fixture's hours changed to avoid a UTC/Paris day-boundary crossing (isolating grouping/mean/order/exclusion coverage from DST behavior); three new checks: the plan's own `01:30+02:00` example plus a same-Paris-day/different-UTC-day merge, the March DST-forward (skipped-hour) transition, and the October DST-back (repeated-hour) transition. `EXPECTED_CHECK_COUNT` 69 → 72.
- `companion/pages/health_page.py` — `_battery_reading_parts()` no longer does `strftime("%H:%M")` plus a literal `" UTC"`; new `_full_local_timestamp_text()` and `_as_paris()` helpers; `_axis_clock_label()`/`_axis_day_label()` now Paris-aware; `_battery_trend_caption()` names the real reading count via new `_real_trend_reading_count()`; `_battery_readout_block()`'s detail span's `title` is now the same full local timestamp as its visible text (never the raw ISO), carrying the `.time-value` role; each sparkline point's `title`/`aria-label`/`data-when` are now the identical string.
- `companion/test_status_pages.py` — fixed two existing tests whose fixtures/assertions depended on the retired UTC-day/raw-ISO/`BATTERY_TREND_LIMIT` behavior; added 6 new checks (Paris-aware axis labels, sparkline one-string invariant, zero-`" UTC"` page render in both languages, the battery-trend.js source scan, `concise_timestamp_html()`'s full-timestamp title). `EXPECTED_CHECK_COUNT` 246 → 252.
- `companion/static/battery-trend.js` — the hover swap's `title` write and its no-data fallback no longer carry the raw `ts`; both now read (or omit) the pre-formatted `when` text only.
- `companion/layout.py` — `concise_timestamp_html()`'s docstring corrected; its `title` now a full local timestamp via a new `_FULL_TIMESTAMP_SENTINEL_NOW`-forced `local_clock_text()` call, replacing the raw ISO.

## Decisions Made

See `key-decisions` in the frontmatter above for the full rationale on each. In short: bucketing moves to Python (there is no DST-correct SQL fix); the sparkline's title/aria-label/data-when collapse to one shared string (data-mv already carries the value machine-readably); every title/tooltip on this page is now a full day-qualified local timestamp, not a bare clock; and the `.time-value` role is applied to the stable wrapper span rather than a nested sibling, because `battery-trend.js` overwrites that span's `textContent` (not its class list) on every interaction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sparkline point's title/aria-label carried a different string than data-when**
- **Found during:** Task 2, while implementing the "tooltip, aria-label and data-when are the same string" acceptance criterion.
- **Issue:** `title`/`aria-label` were built as `"value — when"` while `data-when` carried only `"when"` — not literally equal, contradicting the plan's own acceptance criterion, though not a user-visible defect before this task (nothing previously required them to match).
- **Fix:** All three now carry `escaped_when` alone. `data-mv` already exposes the exact value machine-readably, and battery-trend.js's own `reveal()` already prepends the value separately (`readoutValue.textContent = mv + " mV"`), so keeping the value inside the same string `data-when` carries would have printed it twice once JS took over.
- **Files modified:** `companion/pages/health_page.py`, `companion/test_status_pages.py`
- **Verification:** new check `_sparkline_point_title_aria_data_when_are_one_string`; full `companion/test_status_pages.py` run.
- **Committed in:** `402185a` (Task 2 commit)

**2. [Rule 1 - Bug] Two pre-existing test fixtures depended on UTC-day bucketing / the retired BATTERY_TREND_LIMIT caption / the raw-ISO title**
- **Found during:** Tasks 1-3, running the harness after each source change.
- **Issue:** `server/test_config_history.py`'s original daily-bucketing fixture used hours (2, 14, 23 UTC) where 23:00 UTC in September (CEST) lands on the NEXT Paris day — the fixture's own hand-computed expected means no longer held once bucketing correctly moved to Paris days. Two `companion/test_status_pages.py` checks hard-coded `BATTERY_TREND_LIMIT`/the raw ISO string as the expected caption/title, which the plan's own fixes intentionally retire.
- **Fix:** Adjusted the history_db fixture's hours to avoid crossing a Paris-day boundary (isolating that check's own grouping/mean/order/exclusion coverage from DST behavior, which gets dedicated new fixtures instead); retargeted the caption checks to the real reading count; retargeted the title checks to assert the new full-local-timestamp shape (self-deriving from `concise_timestamp_html()` rather than hard-coding a literal, per the plan's own guidance from 22-05's similar experience).
- **Files modified:** `server/test_config_history.py`, `companion/test_status_pages.py`
- **Verification:** both harnesses green at their new pins.
- **Committed in:** `bafd1bf` (Task 1), `402185a` (Task 2), `13f383f` (Task 3)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs/inconsistencies surfaced while implementing the plan's own literal acceptance criteria). No scope creep; no architectural changes.

## Issues Encountered

None that required a checkpoint or a stop. One thing worth flagging explicitly per the plan's own critical constraints: Task 3's change to `layout.concise_timestamp_html()`'s `title` is a cross-cutting change (every caller on every page inherits it). Per the plan's own guidance I ran `companion/test_view_pages.py` (owned by plan 22-07) immediately after making the change and before committing — it stayed green at its existing pin (116/116) with no edits needed, because its own assertions re-derive the expected markup from `concise_timestamp_html()` live rather than hard-coding the old raw-ISO string. No revert was needed.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None.

## Threat Flags

None — this plan's own threat register (T-22-20..T-22-23) already anticipated every surface this plan touches (the hostile-`ts` parse path in `history_db.py`, the client-side reformatting risk in `battery-trend.js`, the DST-bucketing correctness risk), and no new network endpoint, auth path, or schema change was introduced.

## Next Phase Readiness

- CFG-28 is still open in `REQUIREMENTS.md` (annotated "in progress") — plan 22-11 must land the airline resolve dialog's own raw-ISO half (B5, `airlines_page.py`/`panel-lookup.js`) before the requirement can be checked off.
- `companion/i18n_fr/health.py` was re-checked and needed no new keys (`"Latest %d readings"` already has its French translation from a prior phase).
- No CSS rule was found missing during this plan — the `.time-value`/`.time-value--primary`/`.time-value__age` role plan 22-04 defined already covered every shape this plan needed; nothing to record for 22-12/22-15.
- `scripts/run-all-tests.sh` at plan close: 93% coverage, 3 known-failing harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`) — all three fail only because this sandbox runs as root (the read-only-directory reproduction cases succeed for root where they should fail), matching the plan's own documented environment fact; all three pass in CI. No new failure was introduced by this plan.

## Self-Check: PASSED

All 6 modified files confirmed present on disk; all 3 task commit hashes (`bafd1bf`, `402185a`, `13f383f`) confirmed in `git log`.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-12*
