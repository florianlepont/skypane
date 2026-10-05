---
quick_id: 261004-fc1
subsystem: companion
tags: [flights, filter, chips, search, css, i18n]
key-files:
  created:
    - companion/ui_filter.py
  modified:
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/health_sections.py
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/i18n_fr/flights.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/health.py
    - companion/i18n_fr/common.py
    - companion/testdata/render_baseline.json
completed: 2026-10-04
---

# Quick 261004-fc1: Filter bar as segmented chips plus expanding search

One shared component, `layout.filter_bar_html()` (`companion/ui_filter.py`), now
builds the filter bar on Flights, Airlines and Health's unresolved-prefix list.

- **Search:** 16px text in a 48px field (no iOS focus zoom, above the 44px
  floor), a magnifier, an inline 44px clear that shows only while the field holds
  text, and a placeholder in place of the visible label (the label stays as a
  visually-hidden `<label for>`). The native search cancel glyph is hidden.
- **Flights chips:** All / Departures / Arrivals with live counts. On a phone the
  search rests as a 48px icon beside the chips and opens over the row on focus or
  while it holds text; on desktop it is always open at the right. The chips are
  `.js-gate` hidden without a script, since they cannot filter anything then.
- **Airlines and Health:** the plain search pill and a visible quiet count; no chips.
- **Search text:** the Flights haystack now holds callsign, hex, airline name,
  both route codes and the aircraft type. Only codes exist for airports, so the
  placeholder says "Callsign, airline, airport…" and no airport names are claimed.
- **Empty state:** a soft card with a search glyph and its own Clear, which also
  resets the chips. A day header with no visible flight under it hides.
- **`list-filter.js`:** every `[data-filter-clear]` is wired (it was only the first),
  chip filtering ANDs with the text, chip counts follow the text, the count template
  reaches the script with `#` rather than `%d`, which also fixes Airlines' count
  falling back to English after typing in French.

## Chip set

Rows carry one honest dimension: `confirmed_state`, written only as `departing`
or `arriving`, both of which occur. Runway, resolved-vs-unidentified and "today"
were rejected as redundant (see the plan). A row with any other state counts under
All only.

## Verification

Full suite 3771 passed, 8 skipped (root-only permission skips); ruff, mypy,
function-size and comment-history gates clean. Render baseline rewritten, with
diffs only on the Flights, Airlines and Health pages.
