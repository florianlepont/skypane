---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 03
subsystem: ui
tags: [flights-table, css-min-width-max-content, es5-static-script, detail-row-disclosure, i18n]

# Dependency graph
requires: ["21-01"]
provides:
  - "companion/pages/history_page.py — the Flights desktop table compacted to five data columns (When/Flight/Route/State/Corroboration) plus a visually-hidden 'Details' toggle-column header; When/Flight are two-line, genuinely-stacked cell-primary/cell-secondary pairs; each summary row has a sibling flight-detail-row <tr> carrying the hex, the full ISO timestamp, the runway and copy buttons"
  - "companion/layout.py — status_dot(visually_hide_label=False) keyword, byte-identical when falsy; Flights' desktop Corroboration cell is the one caller passing True"
  - "companion/static/flight-rows.js — the ES5 detail-row disclosure script, registered through the six-touch-point static-script contract"
  - "companion/static/list-filter.js — applyFilter() hides/shows a filtered row's sibling detail row in lockstep with the summary row"
  - "companion/static/style.css — table.data-table--flights padding rule plus a stacked-cell override that keeps the table inside the real 880px column at 1280px in both languages"
affects: ["21-08"]

tech-stack:
  added: []
  patterns:
    - "six-touch-point static-script contract (route constant, path constant, serve delegate, do_GET() dispatch, layout.py SRC constant, page_shell() script-tag tuple, route==src agreement check), copied verbatim from theme-preview.js for flight-rows.js"
    - "per-script class-at-load no-JS-floor pattern (flight-detail-row--collapsed added only by flight-rows.js at load, never server-rendered) instead of a page-wide '.js' class"
    - "keyword-with-default, byte-identical-when-falsy parameter contract (status_dot's visually_hide_label), matching stat_tile()'s own caption_title precedent"
    - "headless Playwright measurement (pinned Chromium executablePath, real /ui-lang form control, .data-table-wrap scrollWidth/clientWidth) as the authoritative check for a CSS width-budget claim, over arithmetic alone"

key-files:
  created:
    - companion/static/flight-rows.js
  modified:
    - companion/pages/history_page.py
    - companion/layout.py
    - companion/app.py
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/i18n_fr/flights.py
    - companion/test_view_pages.py
    - companion/test_companion_app.py

key-decisions:
  - "The Flight cell's secondary line keeps the D-21 unresolved-airline link (folded into the new _flight_cell_html(), carried over verbatim from the retired _type_airline_cell()) even though the plan's Task 1 action text didn't name it explicitly — dropping it would have silently regressed existing desktop coverage the test suite already required."
  - "The detail row's standalone 'copy-name' button (named but not detailed in the plan/UI-SPEC) is read as the callsign's own copy button with no re-displayed dt/dd label, since the callsign is already visible on the summary row's Flight cell — only the copy affordance needed a new home."
  - "Task 1's own new-checks list ('two stacked lines, never an inline suffix') was initially read against 21-UI-SPEC.md §F's illustrative markup block, which shows an INLINE cell-primary/cell-inline-sep/cell-secondary composition — the same shape _merged_cell() already produces everywhere else. The headless measurement step (Task 3) proved that inline shape blows through the 880px budget once combined with .data-table's own pre-existing `min-width: max-content` rule (a deliberate no-crop floor from an earlier phase). Task 3 therefore adds a scoped override making the When/Flight primary/secondary lines genuinely block-level (stacked) for this table only, which is what makes the plan's own prose literally true and is what the measured numbers required."

requirements-completed: [CFG-22]

# Metrics
duration: ~110min
completed: 2026-09-12
---

# Phase 21 Plan 03: Compact Flights table, detail row, flight-rows.js Summary

**The desktop Flights table drops from six visible columns to five (When, Flight, Route, State, Corroboration) plus a visually-hidden toggle column; the hex, full ISO timestamp, runway and copy buttons move into a per-row expandable detail row driven by a new ES5 script, and a CSS fix (found by headless measurement, not assumed) makes the table genuinely fit its real 880px column at 1280px in both English and French.**

## Performance

- **Duration:** ~110 min
- **Started:** 2026-09-12
- **Completed:** 2026-09-12
- **Tasks:** 3
- **Files modified:** 8 (1 created)

## Accomplishments

- `companion/pages/history_page.py`: `_HEADERS` drops from `("Timestamp", "Callsign", "Type", "Route", "State", "Corroboration")` to `("When", "Flight", "Route", "State", "Corroboration")`; the table's sixth `<th>` is a visually-hidden "Details" toggle-column header; `_when_cell_html()`/`_flight_cell_html()` replace the retired `_clock_cell_html()`/`_callsign_hex_cell()`/`_type_airline_cell()`; each summary row gets a "More"/"Plus" row-toggle button and a sibling `_flight_detail_row_html()` `<tr>` (colspan 6) carrying the hex + copy button, the full ISO timestamp + copy button, the runway, and a standalone callsign copy button — every dt/dd pair omitted when its value is absent
- `companion/layout.py`: `status_dot()` gains `visually_hide_label=False`, byte-identical for every pre-existing caller; Flights' desktop Corroboration cell is the one call site passing `True`
- `companion/static/flight-rows.js` (new, ES5 IIFE): registered through all six touch points in `companion/app.py`/`companion/layout.py`; on load it adds `flight-detail-row--collapsed` to every detail row; on click of `[data-row-toggle]` it toggles that class on the row named by `aria-controls`, flips `aria-expanded`, and swaps the button's `textContent` between its own `data-more-text`/`data-less-text` attributes
- `companion/static/list-filter.js`: `applyFilter()` now also hides/shows a summary row's sibling `.flight-detail-row` (matched by `id="flight-detail-{group}"`, never DOM adjacency)
- `companion/static/style.css`: the scoped `table.data-table--flights` padding rule (`var(--space-sm)` both axes); the detail row's own styling (`.flight-detail-row td`, `.flight-detail-row__grid`, `.flight-detail-row--collapsed`); a Task-3 Rule 1 fix making the When/Flight cells' primary/secondary lines genuinely stacked (block-level) and hiding the now-redundant inline separator, needed because `.data-table`'s pre-existing `min-width: max-content` rule sizes each column to its widest *unwrapped* line
- `companion/i18n_fr/flights.py`: adds `"When"`/`"Details"`/`"More"`/`"Less"`; reuses the existing `"Flight"` entry from `i18n_fr/rules.py` (identical English source string, same French value "Vol") instead of redefining it; drops the now-orphaned `"Type"`/`"Modèle"` entry
- Measured, not assumed (Task 3): started the companion service against the seeded scratchpad state directory and ran a new headless Playwright probe (pinned Chromium executablePath) that logs in, switches language via the real `form[action="/ui-lang"] button[value="fr"]` control, loads `/flights` at 1280×900 in both languages, and reads `document.documentElement.scrollWidth`/`window.innerWidth` plus `.data-table-wrap`'s own `scrollWidth`/`clientWidth`. Also verified the "More"/"Plus" toggle's live behaviour and the no-JS floor with `javaScriptEnabled: false`.
- `test_view_pages.py`/`test_companion_app.py`: retargeted every check asserting the old six-header tuple or the old cell composition; added new checks for `visually_hide_label`'s default, the dot-only Corroboration cell, the When/Flight merged-cell shape, the detail-row/summary-row pairing, the hex/ISO/runway living in the detail row and not the summary row, no inline script/handler, `flight-rows.js`'s own six-touch-point registration, and the static half of the width-budget guarantee (the padding rule's token usage, six `<th>` cells in both languages)
- `ruff check .` clean; `test_i18n.py` 22/22; `test_status_pages.py` 212/213 (the one documented `anomaly_active()` root-sandbox FAIL, untouched)

## Task Commits

1. **Task 1: Five columns, two-line cells, a dot-only Corroboration column** - `77231ca` (feat)
2. **Task 2: The detail row and companion/static/flight-rows.js** - `9a063ee` (feat)
3. **Task 3: Filter the detail rows in lockstep, and prove the 880px fit** - `ca4adea` (feat)

## Harness Counts (before → after)

| Harness | Before (main, 614d41e) | After Task 1 | After Task 2 | After Task 3 | Notes |
|---|---|---|---|---|---|
| `companion/test_view_pages.py` | 105 | 108 | 111 | 113 | +3 net each task (retargets net 0, genuinely new checks counted) |
| `companion/test_companion_app.py` | 251 | 251 (untouched) | 256 | 256 | +5 net at Task 2 (flight-rows.js's six-touch-point checks) |
| `companion/test_i18n.py` | 22 | 22 | 22 | 22 | net 0 — "When"/"Details"/"More"/"Less" added, "Type" dropped |
| `companion/test_status_pages.py` | 213 | 213 (untouched) | 213 (untouched) | 213 (untouched) | not owned by this plan |

Real on-disk pass counts at the final commit: `test_view_pages.py` 113/113, `test_companion_app.py` 254/256 (the two documented WR-11 root-sandbox FAILs), `test_i18n.py` 22/22, `test_status_pages.py` 212/213 (the one documented `anomaly_active()` FAIL). `ruff check .` clean.

## Files Created/Modified

- `companion/static/flight-rows.js` — new ES5 IIFE, the detail-row disclosure script
- `companion/pages/history_page.py` — `_HEADERS`, `_when_cell_html()`, `_flight_cell_html()`, `_flight_detail_row_html()`, `_history_table_html()`'s row-toggle cell, `_MORE_TOGGLE_TEXT`/`_LESS_TOGGLE_TEXT`/`_DETAILS_HEADER_TEXT`; `_callsign_hex_cell()`/`_type_airline_cell()`/`_clock_cell_html()` retired
- `companion/layout.py` — `status_dot(visually_hide_label=False)`, `FLIGHT_ROWS_SCRIPT_SRC`, `page_shell()`'s eleventh script-tag slot
- `companion/app.py` — `FLIGHT_ROWS_SCRIPT_ROUTE`, `_FLIGHT_ROWS_JS_PATH`, `_serve_flight_rows_script()`, its `do_GET()` dispatch line
- `companion/static/list-filter.js` — `applyFilter()`'s sibling-detail-row hide/show extension
- `companion/static/style.css` — `table.data-table--flights` padding rule, `.flight-detail-row*` rules, the stacked-cell override (Task 3 Rule 1 fix)
- `companion/i18n_fr/flights.py` — `"When"`/`"Details"`/`"More"`/`"Less"` added, `"Type"` dropped, `"Flight"` documented as reused from `i18n_fr/rules.py`
- `companion/test_view_pages.py` — extensive retargeting plus new checks (see Accomplishments); `EXPECTED_CHECK_COUNT` 105 → 108 → 111 → 113
- `companion/test_companion_app.py` — `flight-rows.js`'s six-touch-point checks, the "eleven deferred scripts" retarget; `EXPECTED_CHECK_COUNT` 251 → 256

## Decisions Made

- Kept the D-21 unresolved-airline link on the new Flight cell (see key-decisions above).
- Read the detail row's "copy-name button" as the callsign's own copy button with no re-displayed label.
- Resolved the "stacked lines" vs. the UI-SPEC's inline-looking worked-example markup by trusting the measured behaviour: added a scoped CSS override making the lines genuinely block-level, which the headless probe confirms actually fits 880px in both languages (see Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The When/Flight cells' inline composition blew through the 880px column budget; fixed with a scoped stacked-line CSS override**
- **Found during:** Task 3's own mandated "measure, do not assume" step
- **Issue:** Task 1 implemented the When/Flight cells via `_merged_cell()`'s existing inline `primary + separator + secondary` composition (the same shape `21-UI-SPEC.md §F`'s own worked-example markup block shows, and the shape every other merged cell in this codebase already uses). `companion/static/style.css`'s pre-existing `.data-table { min-width: max-content; }` rule (a deliberate "no-crop" floor from an earlier phase) sizes every column to its widest *unwrapped* line — so a Flight cell rendering "AFR1380 · Air France · A320" on one line wanted roughly 400px, and the table's real measured content width was ~1081px (EN) / ~1173px (FR) inside the 880px column, with the French page even overflowing the full 1280px viewport (1331px `documentElement.scrollWidth`). This directly contradicted D-15's own acceptance criterion ("no horizontal scroll at 1280px in either language") and this task's own Task 1 prose ("two stacked lines, never an inline suffix" — read too literally as descriptive of the *content* shape rather than the *rendering* shape on first pass).
- **Fix:** Added a scoped `table.data-table--flights .cell-primary/.cell-secondary { display: block; }` plus `.cell-inline-sep { display: none; }` rule. This makes each column's max-content width the wider of its two lines, not their concatenation, and makes the plan's own "two stacked lines" text literally true. Re-measured with the same headless probe: EN and FR both now report `.data-table-wrap` `scrollWidth === clientWidth === 880`, and `document.documentElement.scrollWidth === window.innerWidth === 1280` in both languages — no horizontal scroll anywhere.
- **Files modified:** `companion/static/style.css`
- **Verification:** headless Playwright probe (below); `test_view_pages.py` 113/113; `ruff check .` clean.
- **Committed in:** `ca4adea` (Task 3)

**2. [Rule 1 - Bug] Pre-existing comments in `list-filter.js` and my own new comment in `flight-rows.js` tripped this same plan's own ES5-token-ban acceptance-criteria greps**
- **Found during:** Task 2 and Task 3's own acceptance-criteria verification
- **Issue:** `flight-rows.js`'s first-draft header comment spelled out "innerHTML"/a backtick while describing what the file must NOT do (mirroring the banned-token list itself); `list-filter.js`'s own pre-existing header comment (written before this plan, describing the file's ES5-safety contract) spelled "let"/"const" as literal words inside a slash-delimited list. Both tripped the `grep -cE "\b(let|const)\b|=>|innerHTML|..."`-style checks this plan's own Task 2/Task 3 acceptance criteria introduce, since those greps scan the whole file text, not parsed code.
- **Fix:** Reworded both comments to describe the same constraints without spelling out the literal banned tokens (e.g. "var-only declarations, no arrow functions, no template-literal syntax" instead of "no let/const/arrow functions/template literals/backticks"), preserving the same meaning.
- **Files modified:** `companion/static/flight-rows.js`, `companion/static/list-filter.js`
- **Verification:** `grep -cE "\b(let|const)\b|=>|innerHTML|document\.write|insertAdjacentHTML" companion/static/flight-rows.js` → `0`; `grep -cE "\b(let|const)\b|=>" companion/static/list-filter.js` → `0`.
- **Committed in:** `9a063ee` (Task 2), `ca4adea` (Task 3)

### Not Fixed — Flagged Instead

None.

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bug), 0 flagged/not-fixed.
**Impact on plan:** No scope creep — both fixes stayed within this plan's own D-15/R-12 goals; the CSS fix is what actually delivers the plan's headline acceptance criterion (no horizontal scroll at 1280px in either language), which the arithmetic-only reasoning in 21-UI-SPEC.md §F did not by itself guarantee against `.data-table`'s own pre-existing layout rule.

## Known Stubs
None.

## Threat Flags
None — every threat this plan's own STRIDE register named (T-21-08 hex/callsign/airline/type/runway/ISO-timestamp XSS in the detail row, T-21-09 `flight-rows.js`'s label-swap sink, T-21-10 the new `<script src>` registration, T-21-11 the no-JS floor showing strictly less-hidden data than before) was mitigated/accepted exactly as the plan's threat model specified. No new network-facing surface, auth path, or schema change was introduced.

## Issues Encountered

- 21-UI-SPEC.md §F's worked-example markup block shows the When/Flight cells as one inline `cell-primary + cell-inline-sep + cell-secondary` run — the exact same shape every other merged cell in this app already uses — which reads, on its own, as directly contradicting this same section's prose ("two stacked lines, never an inline suffix"). The headless measurement step (mandated by Task 3, not optional) resolved the ambiguity empirically: the inline shape measurably overflows the real 880px budget once `.data-table`'s pre-existing `min-width: max-content` rule is accounted for, so the prose's "stacked" reading is the one that actually satisfies D-15's acceptance criterion. Future phases reading 21-UI-SPEC.md §F's markup block literally should treat it as illustrative of CONTENT composition (which value goes in which span), not of final CSS layout (whether the spans render on one line or two) — this plan's own CSS override is the authoritative shape.
- Headless verification required a locally-running companion service; this worktree does carry the seeded scratchpad state directory and a pinned Playwright/Chromium install (both already proven working in this session per `21-RESEARCH.md`'s Cross-Cutting "Headless sweep mechanism" note), so the probe ran successfully rather than needing to be deferred to phase 21-08's own binding sweep. The probe scripts themselves live in the scratchpad (`/tmp/.../scratchpad/probe-flights-880.js`, `probe-flights-detail.js`, `probe-flights-toggle.js`, `probe-flights-nojs.js`), not in the repo — they are throwaway verification tooling, not shipped artifacts.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness

- The Flights desktop table fits its real 880px content column at 1280px viewport width with no horizontal scrollbar, measured (not assumed) in both English and French via a headless Playwright probe: `.data-table-wrap` reports `scrollWidth === clientWidth === 880` and `document.documentElement.scrollWidth === window.innerWidth === 1280` in both languages.
- Every hex/full-ISO-timestamp/runway/copy-button affordance that used to live in the desktop summary row now lives in a per-row expandable detail row, visible without any script (the no-JS floor), collapsed only by `flight-rows.js` at load — verified with a `javaScriptEnabled: false` Playwright context.
- `flight-rows.js` is registered through all six touch points with a passing `route == src` check, mirroring `theme-preview.js`'s own precedent exactly — plan 21-08's binding sweep (the phase's own headless sweep across all six live tabs) should find Flights already compliant with the "no horizontal overflow, no inline script, no 404" contract the other pages in this phase are held to.
- `list-filter.js`'s sibling-detail-row extension means a filtered-out Flights row never leaves an orphaned, still-visible detail row behind — this is the one behavioural change to a script two other pages (Airlines, the mobile card) also depend on, and both were re-verified unaffected (`test_view_pages.py`/`test_companion_app.py` green throughout).
- The mobile cards, the filter bar and the View-panel lightbox are byte-identical to before this plan (D-16) — no check in either touched harness needed retargeting for any of the three.

## Self-Check: PASSED

- FOUND: `companion/static/flight-rows.js`
- FOUND: `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-03-SUMMARY.md`
- FOUND commit `77231ca` (Task 1)
- FOUND commit `9a063ee` (Task 2)
- FOUND commit `ca4adea` (Task 3)

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*
