# Phase 61 Plan 90: Flights and empty states Summary

Flights now answers its search, direction chips and sort on the server over the whole history, loads more flights in place without a reload, shows one coherent empty card, and the Airlines collection answers a search with no match with the same card.

## What changed

- **Whole-history search (W142, W143 audit F02/F03).** New `companion/history_query.py` reads the newest 20 000 stored events, folds repeated passes the way Home does, matches every word of `?q=` against the words the page prints (call sign, hex, airline as displayed, both airport codes, aircraft type), then applies `?kind=` and `?sort=` and cuts the page for `?more=N`. Nothing is written, `history_db` and the live frame are untouched, no schema change (the scan is exact because the display airline name can come from an owner override, which a SQL `LIKE` could not see).
- **Chips and counts.** "All / Departures / Arrivals" are radios of one GET form and count the whole history under the current search (stable while a direction is chosen). The empty card quotes the whole history size ("... see all 70 flights"); a status line (`[data-filter-count]`, read by screen readers) says "N flights" / "N flights match".
- **Empty state.** A search or direction with no match renders only the controls and the card (heading, body, Clear link): no table, no table header, no day groups, no shown-count, no Load more. Phone and desktop render the same, the true empty history keeps its own "no flights yet" card with no controls.
- **Load more in place.** `list-filter.js` (second block) fetches the next page, appends the new cards and table rows (continuing the day group, no repeated separators), updates the shown-count and both link addresses, removes the block on the last page, keeps focus on the button or moves it to the first new row, finishes the entrance animation of appended groups and `history.replaceState`s the address. The plain link works without a script.
- **Anchor on both lists.** A fragment targets the first element with its id, and the hidden list has no box, so there are two ids (`flights-new` on the table row, `flights-new-card` on the phone card) and two Load more links (one per representation, the stylesheet shows the one for the viewport). Without scripts the desktop now lands on the first new table row. `scroll-margin-top` leaves room above the landed row.
- **Sort.** Native select (Newest first, Oldest first, Airline, Direction), server-side `?sort=`, kept in the search form, in Load more links and the Clear link. The airline and direction sorts use one group named after the sort and date each row.
- **Works without scripts.** The search is a real GET form (Enter submits); chips and sort belong to it through `form=`; an Apply button shows only without scripts.
- **Layout (F18, F19).** The search keeps its title-row place (never over the frame button): from 1280 px it shares the title row at its right edge (title no longer shrinks), below that it wraps left-aligned under the title. A phone row without a picture has no empty lead gutter (checked at 360/390). Empty-card buttons are 44 px.
- **Airlines collection (workflow FAIL).** A hidden `empty-state--filter` card (heading, "Try another filter...", Clear button) is revealed by `list-filter.js` when typing hides every card; a server-rendered match-less page shows the same card with a Clear link back to `/airlines`. Unlock animation and sticky bar untouched.
- Shared markup moved into `ui_filter.filter_empty_html` and `filter_title_search_form_html`; `page_context` gained `history_query` (raw `q`, `kind`, `sort`). `companion/app.py` is unchanged (1478 lines).

## Commits

One commit: `feat(61-90): ...` (code, tests, render baseline, this summary).

## Tests added or adapted

- New `companion/test_flights_search_sort.py` (12, markup level): old call sign found beyond the first page, word search over airline/airport, chip counts under search, empty card (EN/FR) with no table header/Load more/`<th>`, unknown params, sorts, Load more links keep the view and both anchors.
- `test_browser_flights_search_more.py` rewritten: title-row search at 360/390 EN/FR; Load more in place at 390 and 1280 EN/FR (window marker survives, scroll position kept, focus, address, no repeated day group); button and focus kept while more remains; no-JS Load more lands on the first new row at 390 and 1280; old call sign found at 390/1280; coherent empty card at 390/1280 EN/FR; sort changes order and survives Load more (with and without scripts); desktop title-row alignment at 1280/1440 EN/FR and the wrap at 1100; no phone gutter.
- `test_browser_flights_cards.py`, `test_browser_ux_03.py` (refresh keeps the filter), `test_view_pages_01/02`, `test_flights_cards.py`, `test_view_pages_helpers.py` adapted in place to the server-driven controls (nothing weakened).
- `test_browser_airline_collection.py`: empty card with script (360/1280 EN/FR, Clear restores, bar still sticky) and the no-script path.
- `render_baseline.json` regenerated.

## Deviations from plan

- Two Load more links and two anchor ids instead of one duplicated id (a duplicated id cannot work: the browser targets the first one in tree order, which is the hidden phone card on desktop).
- The visible "N matches" line was dropped (it pushed the list down whenever a search opened, which the title-row search guarantees against); the "All" chip shows the number, and the status line is read by screen readers.
- F18's ragged route wrap is not changed: the route already wraps as one unit under the airline; rows are not forced to three lines.
- The row facts `data-filter-text/-kind/-group` stay on Flights rows (the server's own words, used by tests and styling hooks); list-filter.js ignores them there because the search field no longer carries `data-filter-input`.

## Known stubs

None.

## Self-Check: PASSED
