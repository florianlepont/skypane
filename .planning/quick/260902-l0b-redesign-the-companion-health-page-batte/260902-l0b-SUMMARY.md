---
phase: quick-260902-l0b
plan: 260902-l0b
subsystem: ui
tags: [sqlite, health-page, sparkline, chart, companion-web-app]

requires:
  - phase: quick-260902-ep7
    provides: "The percentage-coordinate sparkline geometry (no viewBox, no gutter estimate) this task's date-endpoint labels and density rule build on top of, untouched"
  - phase: quick-260901-uzi
    provides: "_battery_reading_parts()'s (value, when) tuple contract and the data-when attribute battery-trend.js reads, which _daily_reading_parts() reuses"
provides:
  - "history_db.daily_battery_averages(conn, since=None) — a UTC-calendar-day GROUP BY aggregate over device_health"
  - "health_page.battery_daily_rows()/BATTERY_TREND_WINDOW_DAYS (90) — the chart's primary 90-day daily-average series"
  - "health_page.battery_sparkline_svg(rows, now=None, daily=False) — daily-mode date labels, averaged point labels, and a density-gated cosmetic-dot suppression rule"
  - "A day-1 fallback (< 2 UTC calendar days of history) that keeps the pre-existing raw-readings chart and readout instead of losing both"
affects: [companion-health-page, sketch-findings-skypane-skill]

tech-stack:
  added: []
  patterns:
    - "One shared boolean predicate (_battery_daily_series_usable()) decides the plotted series, the caption text, and the chart's label mode together, so none of the three can independently drift out of sync with what is actually on screen"
    - "Threshold constants derived from a live-measured browser value (a real getBoundingClientRect(), not a CSS-only estimate), with the derivation and its re-derivation trigger written beside the constant — same convention as this file's pre-existing _SPARKLINE_VERTICAL_INSET_PERCENT"

key-files:
  created: []
  modified:
    - server/history_db.py
    - server/test_config_history.py
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md

key-decisions:
  - "Density threshold re-derived live at 39 points (not the 293px-grid-based planning estimate of 50) after a real Chrome measurement of .sparkline__canvas showed 226px, not 293px — the Y-axis label column and its gap were unaccounted for in the CSS-only estimate"
  - "Month abbreviations use a fixed English _MONTH_ABBR table, not strftime('%b') as the plan's own action text suggested — %b is locale-dependent and this app's own UI text is English-only regardless of server locale"
  - "The empty-database caption uses the 3-month framing (not the readings-count framing) because there is no chart of any kind to be honest about — it names the window this page will show once data exists"

requirements-completed: [QUICK-260902-l0b]

coverage:
  - id: D1
    description: "daily_battery_averages() groups device_health by UTC calendar day, rounds the mean, excludes NULL-battery and unparseable-timestamp rows"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_daily_battery_averages_groups_excludes_and_bounds_correctly"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Health battery chart plots a 90-day daily-average series and provably never plots a raw reading value as a point"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_battery_chart_plots_daily_averages_not_raw_readings"
        status: pass
      - kind: automated_ui
        ref: ".planning/quick/260902-l0b-redesign-the-companion-health-page-batte/evidence/health-375-battery-card-centered.png"
        status: pass
    human_judgment: false
  - id: D3
    description: "A device with fewer than two UTC calendar days of history falls back to the pre-existing raw-readings chart and keeps its readout"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_battery_chart_falls_back_to_raw_series_on_day_one"
        status: pass
      - kind: automated_ui
        ref: ".planning/quick/260902-l0b-redesign-the-companion-health-page-batte/evidence/health-375-battery-sameday-fallback.png"
        status: pass
    human_judgment: false
  - id: D4
    description: "The heading caption always names the window actually on screen (empty/multi-day/same-day)"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_battery_caption_is_mode_honest_across_renders"
        status: pass
      - kind: automated_ui
        ref: ".planning/quick/260902-l0b-redesign-the-companion-health-page-batte/evidence/health-375-battery-empty-state.png"
        status: pass
    human_judgment: false
  - id: D5
    description: "Date endpoint labels and per-point averaged labels in daily mode; density rule suppresses cosmetic dots only above the derived threshold"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_sparkline_daily_mode_shows_date_endpoints_not_clock, #_sparkline_daily_point_label_names_day_and_average_count, #_sparkline_density_rule_suppresses_dots_only_above_threshold"
        status: pass
      - kind: automated_ui
        ref: ".planning/quick/260902-l0b-redesign-the-companion-health-page-batte/evidence/health-375-battery-38pt-just-under-threshold.png (38pt: dots present), live dotCount=0 at 40pt/91pt"
        status: pass
    human_judgment: false
  - id: D6
    description: "Tap/pointer precision on the reduced dense hit radius, on a real phone"
    verification: []
    human_judgment: true
    rationale: "Only a real touchscreen device settles finger-tap precision; headless Chrome hover/click cannot simulate a finger's contact area. Live-measured hit-circle spacing (~2.5px between adjacent 8px-diameter hit circles at 91 points on a 375px viewport) is recorded below as a real, heavily-overlapping data point for the human pass to judge against."

duration: ~50min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-l0b: Redesign the Health page's battery-trend chart Summary

**The battery-trend chart's primary mode now plots one server-aggregated daily average per UTC calendar day across a 90-day window (`history_db.daily_battery_averages()`), replacing the old "latest 20 raw readings" chart, while the latest computed reading, the raw-readings disclosure table, and the abnormal-drop anomaly scan all keep reading the untouched raw series.**

## Performance

- **Duration:** ~50 min (including the live-browser verification pass and one threshold correction it produced)
- **Completed:** 2026-09-02
- **Tasks:** 3 (plus one live-verification-driven fix commit)
- **Files modified:** 5

## Accomplishments

- `server/history_db.py` gained `daily_battery_averages(conn, since=None)`, a `GROUP BY date(ts)` aggregate that rounds the mean `battery_mv` per UTC calendar day, excludes NULL-battery and unparseable-timestamp rows, and never touches D-13's keep-forever retention.
- `companion/pages/health_page.py`'s battery chart plots that 90-day daily series by default, with a day-1 fallback to the pre-existing raw-readings chart when fewer than two calendar days of history exist — a data-availability degradation, not a reduced feature, since the daily chart is otherwise complete and the fallback exists specifically to prevent `_battery_section()`'s `if sparkline_html:` guard from also hiding the readout on a freshly-deployed device.
- The chart reads as a day series: two date endpoint labels ("31 Aug"/"2 Sep"), per-point labels naming the day and that the value is a daily average with its contributing reading count, and cosmetic dots suppressed above a live-measured density threshold (39 points) so the thin-line treatment survives at 4.5x the point count.
- The heading caption is mode-honest across all three render states (empty, multi-day daily, same-day fallback), computed from the same predicate that chooses the plotted series.
- The readout, the raw-readings disclosure table, and `battery_status()`'s abnormal-drop anomaly scan all still read the raw series — verified both by a unit check with a "flat daily averages, spiky raw readings" fixture and by a live render.
- `companion/static/battery-trend.js` and `companion/static/style.css` needed no edit — confirmed from source (`reveal()` reads `data-mv`/`data-ts`/`data-when` via `getAttribute()`/`textContent` with no reformatting logic of its own; every marker radius is a Python-emitted SVG attribute, never a CSS declaration) — and confirmed unmodified in every commit's `git diff --name-only`.

## Task Commits

1. **Task 1: Add the daily-average aggregate query to history_db.py** — `fa8264d` (feat)
2. **Task 2: Plot the 90-day daily series, keep the readout and anomaly scan on the raw one, honest caption** — `2444d40` (feat)
3. **Task 3: Make the chart read as a day series (labels, density rule)** — `b5ff8c6` (refactor)
4. **Live-verification fix: re-derive the density threshold from a real measured canvas** — `eafe88a` (fix)

## Files Created/Modified

- `server/history_db.py` — `daily_battery_averages(conn, since=None)`, the new UTC-day aggregate reader
- `server/test_config_history.py` — one new check covering grouping, rounding, ordering, `since`, and both exclusion paths; `EXPECTED_CHECK_COUNT` 29 → 30
- `companion/pages/health_page.py` — `BATTERY_TREND_WINDOW_DAYS`, `battery_daily_rows()`, `_battery_daily_series_usable()`, `_battery_trend_caption()`, `_axis_day_label()`, `_daily_reading_parts()`, the density constants, `battery_sparkline_svg()`'s new `daily` parameter, `_battery_section()`'s new `daily_rows` parameter, `_read_health_inputs()`'s sixth key
- `companion/test_status_pages.py` — six new checks, two gates retargeted in place; `EXPECTED_CHECK_COUNT` 100 → 106
- `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md` — the "Battery trend section" bullet rewritten under the file's SUPERSEDED convention

## The Four SQLite `date()` Facts, Re-Verified

All four facts recorded in the plan's own must-haves were re-verified against a real SQLite connection before writing `daily_battery_averages()` — no disagreement with the plan's recorded results:

1. `date(ts)` converts an offset timestamp to UTC before taking the calendar day: `date('2026-09-02T01:30:00+02:00')` → `'2026-09-01'`.
2. Every timestamp shape the writer can produce parses identically: the `+00:00` offset form, the `Z`-suffixed form, the naive form, the space-separated form, and a fractional-seconds form all mapped to the correct UTC calendar day.
3. `date('not-a-timestamp')` returns `NULL` — confirmed directly, which is why the query filters `date(ts) IS NOT NULL` rather than trusting `battery_mv IS NOT NULL` alone to exclude such a row.
4. Nothing about this behavior is retention-related; the function is a read, `since` is a display window exactly like `BATTERY_TREND_LIMIT`, and D-13's keep-forever retention is untouched.

## Density Threshold: Measured Canvas Width and Its Re-Derivation

**Planning-time estimate: 293px, wrong.** The plan's own action text pointed at `.battery-trend-section svg:not(.icon)`'s comment in `style.css`, which documents "375px viewport -> 293px (the narrowest real container)" — but that figure is the whole `.sparkline` grid's content width (both the Y-label column and the canvas), not the canvas alone. Using it as if it were the canvas produced a threshold of 50 points.

**Live-measured correction: 226px.** Against a real `companion/app.py` instance (Chrome DevTools, 375px viewport, a 96-day seeded dataset), `.sparkline__canvas`'s own `getBoundingClientRect().width` measured **226px**, not 293px. `.sparkline__y`'s auto-sized Y-axis label column measured 43.8px (for this project's realistic 4-digit "NNNN mV" labels — a LiPo battery's usable range, ~3000-4200mV, is always 4 digits) plus its 8px `column-gap`, accounting for the ~52px difference.

**Corrected threshold: 39 points**, derived from the real 226px figure: `226 / (point_count - 1) < 6px diameter` → `point_count > 38.67` → 39 is the first integer point count where suppression is warranted. This was corrected in place (`eafe88a`) after the live-browser pass caught it — the original 50-point threshold under-protected point counts in the 39-49 range, where dots would have kept rendering while already visually crowded. Live-verified at both sides of the corrected boundary: 38 points → 38 `.sparkline-dot` elements present; 40 points → 0 present; 91 points (the full 96-day dataset) → 0 present, 91 hit targets, all reachable.

**Re-derivation trigger:** re-measure `.sparkline__canvas`'s real rendered width from a running instance (not from memory or a CSS-only estimate) if the narrowest supported viewport, the card's padding tokens, the Y-label column's realistic digit count, or the cosmetic dot radius ever change.

## `battery-trend.js` and `style.css`: Confirmed to Need No Edit

- **`companion/static/battery-trend.js`:** `reveal()` reads `data-mv`/`data-ts`/`data-when` via `getAttribute()` and writes them through `textContent`/`setAttribute("title", ts)` with zero date-formatting or reformatting logic of its own — it is agnostic to whether `data-when` carries a clock-format string or a day-plus-average string. Read in full before concluding this; confirmed correct.
- **`companion/static/style.css`:** every marker/hit-target radius (`r="3"`, `r="8"`, now also `r="4"` for the dense case) is a Python-emitted SVG attribute inside `battery_sparkline_svg()`, never a CSS declaration. `.sparkline-dot`/`.sparkline-hit`/`.sparkline-axis-label`/`.sparkline__x` all already size themselves to whatever content or geometry they're given.
- Both confirmed unmodified by `git diff --name-only` after every commit in this task.

## Day-1 Fallback: A Data-Availability Degradation, Not a Reduced Feature

`_battery_section()`'s `if sparkline_html:` guard gates the readout AND the script tag together — a device whose entire history sits inside one UTC calendar day would collapse to one daily bucket (`daily_battery_averages()` groups by day), which means an empty sparkline from `battery_sparkline_svg()` (it needs at least two plotted points), which without the fallback would mean the readout also disappears. `_battery_daily_series_usable(daily_rows)` (at least two day buckets) is the one predicate that decides both the series `_battery_section()` plots and the caption text `_battery_trend_caption()` builds, so the two can never disagree about which is on screen. The 90-day daily chart itself ships complete in this task and renders the moment two calendar days of history exist — the fallback fires only when the DATA cannot support a daily series, never as a simplified first version of the feature.

## The Two Gate Retargets

1. **`_battery_trend_timestamps_show_concise_format()`'s single-argument pin** (originally 06.5-02's exact `len(parameters) != 1` assertion) is retargeted onto the positional-arity property it actually protects: every parameter after the first must carry a default, so the pinned call site `battery_html, battery_state = _battery_section(trend_rows, inputs["daily_rows"])` cannot break. 06.5-02's own concurrent-execution window (the reason for the original exact-count pin) closed long ago.
2. **`_read_health_inputs_gained_no_new_key()`** is renamed `_read_health_inputs_keeps_registry_stats_separate()` (its old name stopped being true the moment `daily_rows` joined `trend_rows`) and grown to a six-key exact set, with an explicit negative assertion (no `registr`/`stat` substring in any key) restating D-11's real intent: the migrated registry/stats reads stay their own independent calls in `render()`, which this new assertion checks directly rather than only via key count.

Neither gate was deleted; both retargets counted as zero movement in `EXPECTED_CHECK_COUNT`.

## Measured Baseline Comparison

`scripts/run-all-tests.sh`'s FAILED list was measured **before Task 3's first edit** (empty — the tree was fully green) and re-measured **after every commit in this task, including the live-verification threshold fix**. Both measurements are identical (empty). No harness that passed before this task failed after it, and no pre-existing failure was ever present to misattribute.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Density threshold re-derived from a live measurement, not the CSS-only 293px estimate**
- **Found during:** Task 3's own required live-browser verification pass
- **Issue:** The plan's own action text pointed the derivation at a pre-existing style.css comment's 293px figure, which is the whole `.sparkline` grid's width, not the canvas the density rule actually needs. This produced a threshold (50) that under-protected real point counts in the 39-49 range.
- **Fix:** Measured `.sparkline__canvas`'s real `getBoundingClientRect().width` (226px) against a live running instance and re-derived the threshold (39) from that number; verified live at both sides of the corrected boundary.
- **Files modified:** `companion/pages/health_page.py`, `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md`
- **Verification:** Full harness suite (106/106 companion, 30/30 config-history) and `scripts/run-all-tests.sh` green at the corrected threshold; live dot-count checks at 38/40/91 points.
- **Committed in:** `eafe88a`

**2. [Rule 1 - Bug] `%b` locale-dependence avoided in favor of a fixed English month table**
- **Found during:** Task 3, while implementing `_axis_day_label()`
- **Issue:** The plan's own action text named `strftime`'s `%b` directive as the month-abbreviation mechanism. `%b` is locale-dependent — a companion service process running under any locale other than English (plausible for this French developer's own deployment) would silently print a non-English month abbreviation, contradicting this page's own "app text is English throughout" convention (recorded in the plan's must-haves).
- **Fix:** Added a fixed `_MONTH_ABBR` module-level tuple (`"Jan"`...`"Dec"`) with no dependency on process locale, and composed `_axis_day_label()` from it plus the parsed `datetime`'s own `.month`/`.day` integers.
- **Files modified:** `companion/pages/health_page.py`
- **Verification:** `_sparkline_daily_mode_shows_date_endpoints_not_clock()` asserts the exact expected label strings.
- **Committed in:** `b5ff8c6`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — real bugs a live/careful read caught before shipping)
**Impact on plan:** Both fixes are corrections to derivations the plan itself flagged as needing verification ("measure it — not from memory"); no scope creep, no architectural change.

## Issues Encountered

None beyond the two deviations above. Port conflicts from a leftover background server process (unrelated to this task) required picking a fresh port for the live-verification instance; no code or test impact.

## Handed Forward

- The 38-point (just-under-threshold) screenshot shows dots that are visually close to touching, not cleanly separated — an inherent property of any single-count threshold (the boundary is defined exactly at "gap == diameter", so the point just below it will always look closer to crowded than comfortably spaced). Not a defect; noted for whoever next tunes this rule.
- The synthetic 96-day seed used for live verification includes a simulated recharge bump every 18 days purely to make the sawtooth pattern visually legible in screenshots; it is not derived from any real device's discharge curve and should not be read as a battery-life claim.
- `RESOLUTION rate`/`Corroboration` tiles showed "no data yet" placeholder states throughout verification because the seeded fixture only populated `device_health`/`meta`, not `runway_events` — expected and unrelated to this task's scope.

## Pixel-Level Items Outstanding

Reproducing the plan's own live-verification checklist with what was actually observed (a real Chrome instance against a real `companion/app.py`, via the `chrome-devtools` CLI):

1. **The whole point — CONFIRMED.** The 90-day sawtooth pattern (slow drain, periodic recharge) is immediately legible at a glance in the 375px and 1280px screenshots — a materially different read from a 20-reading chart, which could never show a multi-week drain/recharge cycle at all.
2. **Density at the real width — CONFIRMED, one correction made.** At 91 points (the full 96-day dataset), the thin line reads cleanly with zero cosmetic dots; the derived threshold itself was found wrong (50 was too generous) and corrected to 39 from a live measurement — see "Density Threshold" above. The corrected boundary was re-verified live (38pt: dots present; 40pt: suppressed).
3. **Hover/tap precision — NOT settled, real touchscreen still needed.** Live-measured: at 91 points on a 375px viewport, adjacent hit circles sit ~2.5px apart while each is 8px in diameter (the dense radius) — meaning adjacent hit targets overlap substantially. Every point stayed reachable and correctly labeled via hover in headless Chrome (confirmed: hovering point 36 of 91 updated the readout to "4200 mV — 22 Jun — daily average (3 readings)"), but headless hover cannot simulate a finger's actual contact area or judge real tap accuracy — this remains a genuine open item for a real phone.
4. **The readout's two meanings — CONFIRMED, reads clearly.** At rest: "4204 mV — 21:00 UTC (0s ago)" (the raw latest reading). After hovering a chart point: "4200 mV — 22 Jun — daily average (3 readings)" — the switch from a clock-relative label to an explicit "daily average (N readings)" label makes the distinction unambiguous, not "one number changing inexplicably."
5. **Endpoint date labels — CONFIRMED, fit cleanly.** "4 Jun"/"2 Sep" render without wrapping or colliding with the Y-axis label column at 375px, the narrowest tested viewport. CONTEXT.md left the exact format (day-plus-month vs. a French convention) to discretion; the shipped English form matches this page's existing all-English convention and was not revisited.
6. **The caption — CONFIRMED in all three modes.** "Battery trend — Last 3 months, daily average" on the seeded multi-day render; "Battery trend — Last 3 months, daily average" on a fresh, empty state directory (the default framing, no chart present); "Battery trend — Latest 20 readings" on a same-day (day-1) fallback render, alongside its own raw-readings chart.
7. **Both themes, narrow viewport — CONFIRMED.** Screenshots captured at 375px light, 375px dark (via a wide-viewport dark-mode capture that also incidentally exercised the >=960px desktop layout), and 1280px light. The chart, caption, and readout render correctly in all three; no contrast or legibility issues observed against either surface.

Evidence screenshots: `.planning/quick/260902-l0b-redesign-the-companion-health-page-batte/evidence/` (8 PNGs — multi-day full page, battery card at 375px/1280px/dark, same-day fallback, empty state, and both sides of the corrected density boundary).

## Next Phase Readiness

Health's battery chart redesign is complete and shipped. No follow-up work is required by this task's own scope. A real-device (not emulated) tap-precision check on the dense hit radius remains the one open item (Pixel-Level Items Outstanding #3) for whoever next has physical access to a touchscreen.

---
*Phase: quick-260902-l0b*
*Completed: 2026-09-02*

## Self-Check: PASSED

All files created/modified confirmed present on disk. All four task commits (`fa8264d`, `2444d40`, `b5ff8c6`, `eafe88a`) confirmed present in git log.
