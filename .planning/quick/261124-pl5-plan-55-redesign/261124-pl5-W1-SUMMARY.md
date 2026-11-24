# Wave 1 (F1 shared filter bar): summary

Branch: phase-68-plan-55-redesign. Variant B of the F1 mockup. Not pushed.

## What changed

One filter module now serves Flights and the Airlines collection (`ui_filter.controls_html`),
replacing the two different bars (Flights: title-row search that collapsed to an icon + a chips/sort
bar; Airlines: one sticky glass card with search, sort, legend).

- Structure (both pages, same placement, under the title): a GET form. Row 1 = search field (takes
  the remaining width), sort menu, info button (always last), all 44 px. Row 2 = scrolling pill row
  of filter chips with counts (scrolls on a phone, wraps from 960 px). Under it a visible count line
  ("34 of 148 flights", "21 of 36 airlines"). Apply button is the no-script send.
- Flights: chips All / Departures / Arrivals now carry counts that follow the search; all existing
  server behaviour kept (`?q`, `?kind`, `?sort`, Load more, in-place swap, offline toast). The
  script now re-renders the sort menu and chips inside the form after each answer and leaves the
  search field alone (typed text and focus stay). New info button: short explanation of directions.
- Airlines: search + sort + the existing rarity legend (now the info button). New chip row:
  All / With artwork / No artwork / Seen this month with counts, filtered in the page by
  `list-filter.js` (`data-filter-kind` on each card); like the old script-driven chips it is hidden
  without a script. Text search and sort keep working without a script (server answers `?q`, `?sort`).
- Removed: `filter_title_search_html`, `filter_title_search_form_html`, the title-row collapsing
  search CSS, `.collection-controls`, `.history-controls`, `.collection-legend`, the sliding-thumb
  chips on Flights, the dead `data-filter-active` plumbing. The airline editor's own
  `filter_bar_html` (Fleet-wide editor, client-side) is untouched.
- Components page: new "Filter controls" state; search states reworked; skill references
  (`components.md`, `page-patterns.md`, `SKILL.md` as-of) updated.
- EN/FR: new ids for the count lines, chips, info text; old `flights.matches_*` and
  `airlines.collection_count*` ids removed (no orphans). French count is "N sur M compagnies"
  (prose about airlines; the page name stays "Airlines").

## Deviations / decisions to review

- The mockup's Flights "7 jours" (period) chip was NOT built: no period filter exists in the
  product and the plan says keep existing filters. Airlines chips are artwork / no artwork /
  seen this month (owner's note), as single-choice chips (the mockup mixes a toggle into the row).
- The Airlines bar is no longer sticky (two rows would eat a phone screen; the mockup shows no card).
  The sticky test was replaced by a chip test.
- Tests that pinned old behaviour were rewritten, not loosened: title-row search tests (collapse,
  overlap with the frame button, thumb slide) replaced by two-row layout, 44 px, no-overflow, chip
  count, in-place chip filtering tests; the scroll-disclosure sweep and glass-surface audit exempt
  the deliberate scrolling chip row.

## Gates and tests

- ruff, mypy, `check_function_size.py check --max 80 server stub-server` (none over 80),
  `check_comment_history.py check`: clean. `companion/app.py` 1491 lines; `list-filter.js` about 990.
- Full `companion test-support scripts` run before the final test edits: 11889 passed, 21 failed
  (all addressed afterwards except `test_render_baseline.py::test_rendered_pages_match_the_baseline`,
  which needs the orchestrator's single regenerated `render_baseline.json`; not regenerated here).
- Targeted re-run after the fixes: see the final report.

## Not done

- `render_baseline.json` not regenerated (as instructed); that test fails until it is.
