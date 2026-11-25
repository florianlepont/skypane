---
phase: 68-console-and-companion-visual-improvements
plan: 32
subsystem: companion
tags: [audit, design-system-skill, verification, battery]
requires: ["68-31", "68-47"]
provides:
  - 68-COVERAGE-AUDIT.md
  - updated sketch-findings-skypane skill
  - Battery page uses the width (owner-directed addition, plan label 48)
requirements: [CON-01]
metrics:
  completed: 2026-11-23
---

# Phase 68 Plan 32: coverage audit, skill, verification (tasks 1 to 3) Summary

Tasks 4 (draft PR) and 5 (owner validation) are not part of this run. CON-01 is not ticked; STATE.md and ROADMAP.md were not touched.

## Commits

- `c2db2e1f` the Components page shows the scrolling chip row and the short dialog (EN/FR states, tests, style-admin rule, baseline).
- `129adcb6` design-system skill brought up to date (SKILL.md and all seven references).
- `51772007` coverage audit.
- `7adcbbbf` `feat(68-48)`: the Battery page uses the width and shows its readings open (owner request, below).
- `fcb9ae08` test follow-up for plan 48 (`test_status_pages_04`).

## Task 1: audit and verification

`68-COVERAGE-AUDIT.md`: 49 rows, each with mockup (or "non-visual"), plan and squash commit, and tests whose file and function were machine-checked to exist; plus the table of owner-directed additions (29, 30, 31+45, 37 to 44, 46, 47 and now 48). **Defects: none.** Points for the owner are listed in "Open points" of the audit (D-26 levels A and B only by decision, R29 "Marchand" unanswered, D-03 mockup without approval block, device checks).

D-14 one-off check: no non-test Python module builds `banner__pill` any more; `system_cards.py` uses its own `sys-banner__pill` class and `freshness.js` composes the class on the client (both justified in the audit). Secret grep: only variable names, commented placeholders and test placeholders.

Verification, all after the last code change (`fcb9ae08`, test-only; the five browser shards ran on `7adcbbbf`, which differs from the final tree only by that one core test file):
- `SKYPANE_REQUIRE_BROWSER=1 SKYPANE_TEST_GROUP=core ./scripts/run-all-tests.sh`: **12572 passed, 7 skipped (root-only permission tests), 0 failed** (a first run on `7adcbbbf` had one failure, `test_status_pages_04::test_interaction_skip_guard_cross_file_contract`, caused by plan 48 removing the last `<details>`; fixed in `fcb9ae08` and the whole core group re-run).
- Browser shards 0 to 4 of 5: 1274, 737, 737 (1 skipped), 600, 830 passed, 0 failed. They include `test_browser_overhaul_sweep.py`, `test_browser_french_fit.py`, `test_browser_contrast_edges.py`, the Components browser test, the must-not-break golden and access tests (core).
- ruff clean; mypy "no issues in 49 source files"; function size none over 80 (1231 scanned); comment history clean; `companion/app.py` 1497 lines; largest JS 1227 lines; `test_render_baseline.py` passes (baseline regenerated twice on purpose: after the Components CSS, and once at the end of plan 48).

## Task 2: ROADMAP criterion 5 (not edited)

The text already says "the route x role x owner matrix is unchanged except the owner-requested removal of the Locations routes" (grep count 1). **The claim no longer holds literally.** Route table compared at the first phase commit `30cca3c5` and now (dumped from `companion.routes.ROUTES`): removed exactly the four `/locations*` routes (GET `/locations`, POST `/locations/add`, `/locations/{}/edit`, `/locations/{}/delete`, matrix module `matrix_rows_locations` deleted); **added** three administrator-only, device-scoped, CSRF POST routes in `matrix_rows_admin_frame` with the same policy kind as their neighbours: `/airlines/rename/manual`, `/airlines/suggest`, `/airlines/suggest/reject`; and three anonymous static scripts (`/static/airline-suggest.js`, `fleet-anchors.js`, `update-question.js`). No existing route changed its access policy. `/health` and `/devices/<id>/health` already answered 303 at the start; their targets changed (now the frame's Battery view `/fleet?frame=<id>&view=battery`, the System view with no frame); `/fleet?view=health` is a new 303; the retired Update address now lands on `&view=versions` (the matrix test expectation changed accordingly).

Proposed wording: "...and the route x role x owner matrix is unchanged except the owner-requested removal of the Locations routes and the three administrator-only airline routes the owner asked for (rename of a hand-named airline, and the two name-suggestion routes), each with the same access as its neighbours; the retired Health and Update addresses still answer a 303 and now land on the frame's Battery and Versions pages."

## Task 3: skill and Components page

SKILL.md and references (navigation, page-patterns, components, tokens-and-theming, accessibility, i18n-bilingual, motion) rewritten to the shipped code: one page order, Console bar with System and Audit in More, space switch "My frames | Console", foreign-frame marker, Fleet list / three-tile frame page / Battery / Versions / System full page with compact tiles, Home blocks, Flights rows, Location (dark map, icon buttons), Editor fleet-wide, Airlines by role, Users (phone header, card list, role chip and menu, invitation dialogs), Account icon actions and About, sign-in first-visit line, 404 illustration, leave dialog (two equal answers and a cross), yellow tile edge, `--keyboard-inset`, secondary ink (text at 70%), caption size, rarity tint, icon-only names. "As of" 2026-11-23. No plan or phase identifiers in the skill text (grep checked). Components page: two states added (scrolling filter chips, short dialog), EN and FR, with a served-markup test and a browser test; `pytest companion/test_components_page.py` 12 passed and the browser components tests passed inside shard runs.

## Plan 48: Battery page uses the width (owner request relayed by the coordinator)

- Desktop: the page column cap is lifted for the Battery page (`.fleet-split__main:has(.fleet-blocks--detail)`), the gauge and the facts (level pill, millivolts, last reading) share one header row from 720 px of card width, the chart is 360 px tall from 960 px (stays about 190 px on a phone), full card width.
- The readings table is shown open under the chart with a heading "Readings (N)" / "Relevés (N)", same columns (Time, Voltage, Level, "Latest" tag), no expander, works without script. The Percentage/Voltage switch is unchanged. The narrowest phones (320 px) shrink the table padding so it fits.
- Strings: `health.view_reading` removed, `health.battery_readings_heading` added (EN and FR, no orphan).
- Tests changed to the new behaviour: `test_battery_card.py` (readings table selector, heading, no details), `test_browser_battery_card.py` (card containment uses the table, full-width readings, table visible without a tap, readings fit at 360 px; two new tests: wide layout with 320 to 420 px chart and readings below, compact chart on a phone), `test_status_pages_01.py` (renamed to `...readings_are_shown_open_after_chart`, "Readings (N)" x3), `test_status_pages_03.py`, `test_status_pages_05.py`, `test_status_pages_helpers.py`, `test_fleet_tiles.py`, `test_browser_ux_helpers.py`, `test_browser_ux_02.py` (waits on the table), `test_status_pages_04.py` (contract fixture), `test_browser_page_opening.py` (the disclosure-fade test removed: no disclosure is left).
- Captures: `scratchpad/p48/before/` (the p45 Battery captures, light) and `scratchpad/p48/after/` (`battery-{normal,low}-{phone,desktop}-{en,fr}-light.png`, 390 and 1440 px).
- Side effect to confirm: the same width rule applies to nothing else (the Versions page keeps its cap).

## Deferred cleanups to record

- Delete the frozen per-frame airline name files (FLT-13) and per-frame illustration directories (ART-10) in a later release, with their backup include entries and rollback caveats.
- `layout.data_table(prose=, desc_columns=)` and its CSS are unused.
- `nav.frame_tools` dead id; `ui_nav.py` comments still mention the hamburger; `CONSOLE_NAV_ENTRIES` still lists Health, Device, Releases.
- `_gap_overflow_html` in `airlines_page.py` still links to `/health` (unused outside its own test).

## Deviations

- [Rule 1] The first Components specimen failed three existing tests: chip radios share one group name (the new row unchecked the first), and the scrolling row bleeds to the page edge; fixed by giving the specimen its own form and a catalogue-only margin rule.
- Plan 48's captures and tests were added at the coordinator's request, before the final verification.
- Tasks 1 to 3 only, as instructed; no push, no PR.
