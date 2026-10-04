# 261004-fla Summary

Flights now renders every folded flight (up to 50) in the first response.

## Removed

- `FLIGHTS_PAGE_SIZE`, `FLIGHTS_LIMIT_QUERY_PARAM`, `flights_limit()`, `SHOW_MORE_TEMPLATE`,
  `_show_more_html()` and the "limited" filter empty-state template in `history_page.py`.
- The `flights_limit` page-context field (`page_context.py`, `pages/__init__.py` contract).
- The `.flights-more` swap region (`ui_nav.py`, `static/freshness.js`) and its CSS rules.
- i18n: `flights.show_more_remaining` and `flights.try_a_different_search_this_only_searches_the` (EN msg + FR).
- Tests: the reveal-state, plain-anchor, CSS-selector and hostile-limit tests, the
  `?limit=` freshness-token test, the `flights_limit` helper argument.

## Behaviour

A hand-typed `?limit=` is never read, so it is ignored. Folding is applied in
`history_rows()` before everything, so day headers, chip counts, the filter count
and the empty state count the full folded list. Cards keep `loading="lazy"`
`decoding="async"` (50/50 verified); HTML grows 46 KB to 106 KB for 50 flights, no
image is fetched until scrolled near. list-filter.js has no limit logic and counts
the DOM cards (browser test: chips 50/40/10 equal visible cards, "50 of 50 shown",
no overflow at 390 px).

## Other references to the page size

None outside Flights: Home's "See all flights" link goes to plain `/flights` and
Home's own tile limit is separate. The freshness token hashes the raw query string
generically, so no token code referenced it. The render baseline changed only for
the four Flights pages (24-row fixture: all rows, no Show more, shorter empty-state body).

Screenshots: scratchpad `shots-flights-all/{before,after}-{390,1280}.png`.
