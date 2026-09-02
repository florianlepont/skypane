# Quick Task 260902-l0b: Redesign the companion Health page battery-trend chart from latest-N-readings to a 3-month (90-day) trend with server-side aggregation, and the latest computed reading - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning

<domain>
## Task Boundary

Redesign Health's battery-trend chart (`companion/pages/health_page.py`'s `battery_sparkline_svg()` / `_battery_trend_section_html()` / `_battery_readout_block()`, plus `companion/static/battery-trend.js`) from showing only the latest `BATTERY_TREND_LIMIT=20` raw `device_health` rows to a 90-day (3-month) trend, while still surfacing the latest computed reading. Developer's own words: "sur la courbe de la batterie, tu affiches seulement les dernières valeurs, alors que moi, ce qui m'intéresse, c'est globalement l'évolution sur plusieurs jours. Et la dernière valeur calculée." Default window explicitly locked at 3 months (rejected 7-day/30-day alternatives): "Mais j'imaginais quand même quelque chose à trois mois."

</domain>

<decisions>
## Implementation Decisions

### Aggregation strategy
- Daily average. One point per calendar day (server-side SQL `GROUP BY date(ts)` aggregation, following the existing `route_source_counts()`/`corroboration_counts()` GROUP-BY pattern already established in `server/history_db.py`), giving ~90 points for the full window. Intra-day min/max amplitude is explicitly NOT shown — daily average only.
- Ground truth confirmed during discussion: `device_health` already retains history forever (D-13; `BATTERY_TREND_LIMIT` in `health_page.py` is a *display* LIMIT, not a retention policy) — no new retention/storage schema needed, only a new aggregation query.

### Visualization
- Extend the existing sparkline treatment (thin single line, no grid) rather than switching to a min/max band or a bar chart. Same visual language as today's card, just fed ~90 aggregated points instead of ~20 raw ones.

### X-axis date labels
- Two labels at the plot's extremities (same position as today's oldest/newest clock-time labels), reformatted as month/day (e.g. "4 juin" / "2 sept") instead of clock time. Not a full month-by-month tick series along the axis — just the two endpoint labels, consistent with the current `_axis_clock_label()` structure's shape (left/right, not a repeated tick series).

### Claude's Discretion
- Exact SQL query shape/name for the new daily-average aggregation in `history_db.py` (e.g. `daily_device_health_summary()` or similar), and how far back to query (90 days from "now," or from the latest reading).
- Whether `BATTERY_TREND_LIMIT` is repurposed/renamed or a new constant is introduced for the day-count window (90).
- Exact locale/format string for the month/day endpoint labels (e.g. "Sep 2" vs "2 sept" — match whatever locale convention the rest of the page already uses; check `_axis_clock_label()` and any other date-formatting helper already in `health_page.py` for precedent before inventing a new format).
- Whether this ships as a single quick task or needs to be split/escalated to a roadmap phase, based on actual implementation size once scoped — the discussion covered product/design decisions only, not process scope. Server-side change (new history_db.py query) + page render change + battery-trend.js + test coverage across companion/test_status_pages.py at minimum.
- What happens to the "— Latest N readings" caption phrasing given the window is now days, not a reading count (e.g. becomes "— Last 3 months" or similar) — not discussed explicitly, but implied by the shift from a reading-count window to a day-count window.

</decisions>

<specifics>
## Specific Ideas

The existing sparkline is a CSS-grid-based SVG wrapper (`.sparkline`, `companion/static/style.css`) with axis labels as `<span>` elements outside the SVG's own viewBox-less coordinate system (a structural rework landed by quick task 260902-ep7 specifically so the browser measures real label widths rather than Python hand-estimating gutter space) — the new date-label strings should flow through that same `<span>`-based axis mechanism, not a reintroduced SVG `<text>` node or a hand-estimated gutter.

`_battery_readout_block()` (the "latest computed reading" the developer explicitly asked to keep) is a separate function from the sparkline/chart — confirm during planning that it stays keyed off `latest_device_health()` (today's single-row reader) unaffected by the new aggregated-history query, since the developer's request was additive ("Et la dernière valeur calculée" — keep showing it), not a replacement.

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above. Read `companion/pages/health_page.py`'s current `BATTERY_TREND_LIMIT` (line ~96), `battery_trend_rows()` (line ~424, its own docstring already states D-13's forever-retention fact), `battery_sparkline_svg()` (line ~540), `_battery_readout_block()` (line ~1185), `_battery_trend_section_html()` (line ~1245) before planning — these were touched by several quick tasks today (260901-tsa, 260902-gjj, 260902-dng, 260902-ep7, 260902-j8w) so the real current shape must be read fresh, not assumed from any prior description. Also read `server/history_db.py`'s `recent_device_health()`/`route_source_counts()`/`corroboration_counts()` for the existing query/aggregation patterns to follow.

</canonical_refs>
