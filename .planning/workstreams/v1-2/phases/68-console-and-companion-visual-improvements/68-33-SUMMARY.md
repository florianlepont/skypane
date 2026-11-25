---
phase: 68-console-and-companion-visual-improvements
plan: 33
subsystem: companion-home
tags: [home, statistics, history-db, i18n, svg]
requires: ["68-01", "68-08"]
provides:
  - "history_db.home_day_timeline / home_week_totals / home_airline_highlights (read-only)"
  - "companion/pages/home_stats.stats_card_html"
  - "companion/pages/home_recent_strip.recent_strip_html"
affects: ["68-13"]
key-files:
  created:
    - companion/pages/home_stats.py
    - companion/pages/home_recent_strip.py
    - companion/test_home_stats.py
    - server/test_history_home_stats.py
  modified:
    - server/history_db.py
    - companion/i18n_fr/home.py
    - companion/test_home_recent_tiles.py
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 33: Home statistics and recent strip builders Summary

Read-only history aggregates plus two pure builders (statistics card with a
script-free Day/Week switch and server-drawn SVG; recent-flights preview strip
using the Flights archived-render match rule) for plan 13 to mount on Home.

## Flag for the owner

`history_db.py` gains read-only functions only (no schema change, no new
write, no `CREATE`/`ALTER`/`INSERT`, no `user_version`), because no Home
aggregate queries existed. Daily activity (flights per day) belongs to Health
today; Home now computes its own copy of those numbers from `runway_events`.

## What was built

- `server/history_db.py`: `home_day_timeline` (24 zero-filled hours of the
  frame's local day, arrival/departure counts, plus one tick per flight at its
  local time), `home_week_totals` (seven zero-filled local days ending today),
  `home_airline_highlights` (most seen airline over the 7 days, ties
  alphabetical; airlines first seen inside the window). Each takes the frame's
  IANA zone and an explicit `now`, reads one `runway_events` range through
  `idx_runway_events_ts`, and folds a pass stored twice within 60 s (the
  Flights/Home rule). Scope is the connection's own database, i.e. one frame,
  as the existing aggregates; asserted in `test_each_frame_reads_only_its_own_database`.
  Owner airline-name overrides can be passed and are applied on read.
- `companion/pages/home_stats.py`: `stats_card_html(timeline, week, highlights,
  now_hour, quiet_windows)`. Day/Week are the shared segmented radios
  (`ui_segmented`), 44px, labels centred (measured: text centre within 1px of
  the segment centre). Timeline and bars use SVG attributes only (no inline
  style, CSP safe) with `var(--color-*)` tokens, so Light/Dark follow.
- `companion/pages/home_recent_strip.py`: `recent_strip_html(rows, now,
  state_dir, gallery_entries)`: heading, "See all flights" link, tiles with
  "Arrival · 12 min" captions; render, else airline illustration, else plane
  chip; empty state under the same heading.
- EN/FR in `companion/i18n_fr/home.py` (23 new ids, no orphan; `test_i18n.py` green).

## Verification

Focused run, 549 passed: the new tests, `test_i18n.py`, `test_suite_guards.py`,
`test_page_structure.py`, `test_structure_guards.py`, `test_stylesheet_structure.py`,
history db tests, the Home tests. ruff, mypy, `check_function_size.py check --max 80`,
`check_comment_history.py check` clean. `companion/app.py` still 1490 lines.
No `.css`, `home_page.py`, schema, render baseline or golden changed.
Both builders were also rendered in a throwaway Playwright page at 360px with
the real `style.css` plus temporary rules for the new classes: no horizontal
overflow, Day/Week switch works with no script, timeline, bars and facts match
the approved mockup.

## Design-system divergences

1. Class names are BEM-prefixed (`home-stats__head`, `home-strip__tile`, ...)
   instead of the mockup's bare names (`.head`, `.big`, `.tl`, `.strip`,
   `.card`), to avoid collisions with global classes; mapping is 1:1.
2. The Day/Week switch is native radios via `ui_segmented.segmented_radios_html`
   (works without script, plan requirement) instead of the mockup's JS buttons
   with `aria-pressed`. Panels switch with `:has()`; plan 13 supplies that CSS.
3. Tile age text is a static "12 min" / "3 h" / "2 d" (mockup wording) in a
   plain `<time datetime>` rather than the app's live `data-relative` "12m ago",
   because the ticker would overwrite the mockup wording. It is stale until the
   page reloads.
4. No separate empty state for the statistics card (the mockup has none and no
   unapproved copy was added): no flight renders the same card at zero with no
   airline facts. The "+N new airlines" fact is omitted when N is 0.
5. Timeline is one SVG (viewBox 288x64, 12 units/hour, stretched) instead of
   absolutely positioned divs; the quiet-band corner radius is stretched
   slightly on cards wider than a phone. Ticks are one per flight at its
   minute, as in the mockup.
6. Token names are the real ones (`--color-secondary`, `--color-border`,
   `--color-accent`, `--color-status-error`), the mockup's `--chip/--border/--err`
   do not exist in `style.css`.
7. English wording is mine (the mockup is French only): "flights today",
   "flights in 7 days", "N arrivals/departures", "most seen · N", "new
   airlines", "Arrival"/"Departure", weekday abbreviations. French follows the
   mockup (Jour/Semaine, "la plus vue", "nouvelles compagnies", Arrivée/Décollage,
   "Derniers vols"). The strip heading uses a new id `home.strip_heading`
   ("Derniers vols") so the existing "Vols récents" on the current Home is untouched.
8. "Overhead" rows are not counted as arrivals or departures (the mockup totals
   are arrivals + departures).

## Notes for plan 13

- Needs CSS in `style-home.css` for: `.home-stats*` (card glass, head, timeline
  `display:block`, hours row, bars flex, `.home-stats__bar` background/border/radius
  and `--today` accent fill, facts), the `:has(#home-stats-week:checked)` panel switch
  (hide `.home-stats__panel--week` by default; hide the day panel when week is checked),
  and `.home-strip*` (tiles row scrolling horizontally, `.home-strip__frame` 3:4 box,
  image `object-fit: contain`, `figcaption span {display:block}`, head row 44px).
  The throwaway rules used are in the scratchpad render script.
- Call the history functions inside one `history_db` scope; pass the frame's zone,
  `ctx.now`, `now_hour` (local time as a float) and quiet windows as `(start, end)`
  floats; pass rows already folded (`flight_card.fold_repeated_passes`) with
  `gallery_entries` from the request context.
- The strip tile frame is fixed 3:4 portrait (112x149); a landscape frame profile
  is not handled. The strip's heading `id="home-flights"` matches the current
  section id, so remove the old recent-flights group when mounting.
- The Home title row decisions (pencil, cadence info icon, quiet-hours link) are not part of this plan.

## Deviations from Plan

None - plan executed as written. `test_home_recent_tiles.py` was extended (builder
tests appended), the existing Home tests there are untouched. The plan's key_link
pattern `GALLERY_MATCH` is satisfied by calling `history_page.matching_gallery_entry`
(which uses those constants) and by a test that exercises the 90 s / 10 s edges
through the constants, instead of re-importing the constants.

## Commits

- c6c559ee feat(68-33): read-only history aggregates for the Home statistics card
- 6dc309d4 feat(68-33): Home statistics card and recent-flights strip builders

## Self-Check: PASSED
