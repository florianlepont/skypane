"""Health page markup builders for the registry ("Airlines we could not
name"), the resolution-statistics breakdown ("How well we name flights")
extracted out of
companion/pages/health_page.py to keep that file under the companion
app's own file-size ceiling (companion/test_structure_guards.py).

This module lives outside companion/pages/ on purpose: a page module may
not import another page module (companion/pages/__init__.py's own
contract), so a markup helper shared by exactly one page still needs a
home next to companion/battery_chart.py and companion/health_signals.py
rather than beside history_page.py or airlines_page.py.

health_page.py imports this module and re-exports the names its own
render() and its remaining tile builders still call as bare names, and a
number of tests still read as `health_page.X` — this module is never the
one importing health_page.py back (that would be circular, since
health_page.py imports this module at load time).
"""

from datetime import datetime, timedelta, timezone

from companion.layout import escape_html
import companion.battery_chart as battery_chart
import companion.health_signals as health_signals_module
import companion.i18n as i18n
import companion.layout as layout
from server import history_db

# Re-read under their own bare names purely for this module's own
# internal use (never re-exported back to health_page.py under these
# names) — `_DB_UNAVAILABLE` is the sentinel health_signals.py's own
# functions return, and `_full_local_timestamp_text` is
# battery_chart.py's own full-timestamp formatter, already used
# elsewhere in this file's registry table.
_DB_UNAVAILABLE = health_signals_module._DB_UNAVAILABLE
_full_local_timestamp_text = battery_chart._full_local_timestamp_text


HEALTH_UNAVAILABLE_TEXT = i18n.msg(
    "health.health_history_is_temporarily_unavailable_check",
    "Health history is temporarily unavailable — check the companion "
    "service logs.")


UNRESOLVED_SECTION_HEADING = i18n.msg(
    "health.airlines_we_could_not_name", "Airlines we could not name")
STATS_SECTION_HEADING = i18n.msg(
    "health.how_well_we_name_flights", "Flight identification")


# The heading is a %-template interpolated with RESOLUTION_WINDOW_DAYS
# at the one call site, never a literal "30", so it cannot silently
# drift from the window constant.
_NO_STATS_HEADING = i18n.msg(
    "health.no_flights_in_the_last_days", "No flights in the last %d days")
_NO_STATS_BODY = i18n.msg(
    "health.the_frame_has_not_recorded_a_detection_in_this",
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.")

# Only the event count varies between these templates; the day count is
# always RESOLUTION_WINDOW_DAYS, so a "1 day" singular form would be
# dead copy. Singular chosen at the call site, never a runtime "add an
# s" rule, which French cannot express (it pluralises the noun and
# needs article agreement too).
_RESOLUTION_DETAIL_TEMPLATE = i18n.msg(
    "health.over_the_last_days_events", "over the last %d days, %d events")
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = i18n.msg(
    "health.over_the_last_days_event", "over the last %d days, %d event")

RESOLUTION_WINDOW_DAYS = 30  # A month smooths over a quiet week at this
# single-airport traffic volume, while still reading as "recent".

# The four categories server/plane/enrich.py's resolve_route() documents,
# plus a fifth ("manual", an operator answering by hand at runtime from
# this companion web interface), in a fixed display order with a
# plain-English gloss so the page is readable without the source. The
# live/cache/static-table distinction is kept deliberately: collapsing
# it would hide which mechanism actually resolved the route.
_SOURCE_ROWS = (
    ("fresh_hit", i18n.msg("health.fresh_lookup", "Fresh lookup"),
     i18n.msg(
         "health.a_live_lookup_in_the_route_database_resolved_a",
         "A live lookup in the route database resolved a full route this cycle.")),
    ("cache_hit", i18n.msg("health.cached_hit", "Cached hit"),
     i18n.msg(
         "health.a_previously_cached_route_was_reused_sparing_a",
         "A previously-cached route was reused, sparing a network request.")),
    ("airline_only", i18n.msg("health.airline_only", "Airline only"),
     i18n.msg(
         "health.the_route_database_had_no_route_but_the",
         "The route database had no route, but the callsign's ICAO prefix "
         "identified the airline from the static prefix table.")),
    ("miss", i18n.msg("health.miss", "Miss"),
     i18n.msg(
         "health.neither_the_route_database_nor_the_static",
         "Neither the route database nor the static prefix table resolved "
         "anything for this callsign, so it shows up in the %s list above."
         % UNRESOLVED_SECTION_HEADING)),
    ("manual", i18n.msg("health.manual", "Manual"),
     i18n.msg(
         "health.the_operator_resolved_this_callsign_s_prefix_by",
         "The operator resolved this callsign's prefix by hand, from the "
         "companion web interface.")),
)

# A sixth, catch-all row for any route_source value outside the five
# above; folded in rather than dropped from the total. Kept out of
# _SOURCE_ROWS itself: that tuple is the fixed, ordered enumeration of
# known mechanisms, and folding an "unknown" bucket into it would
# misrepresent it as a sixth understood mechanism.
_OTHER_SOURCE_LABEL = i18n.msg("health.other", "Other")
_OTHER_SOURCE_GLOSS = i18n.msg(
    "health.a_route_source_this_page_does_not_recognise_or",
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.")

# Single-sourced so the table and the mobile card list can never
# disagree on a header word. Index 2 ("Count") is read directly by the
# card builder; "Description" has no card-side equivalent, since the
# mobile card renders the full description as stacked prose.
_STATS_HEADERS = (
    i18n.msg("health.source", "Source"),
    i18n.msg("health.description", "Description"),
    i18n.msg("health.count", "Count"),
)

def _unavailable_block():
    return '<p class="text-body">%s</p>' % escape_html(i18n.t(HEALTH_UNAVAILABLE_TEXT))


def resolution_stats(conn, window_days=RESOLUTION_WINDOW_DAYS, now=None):
    """Windowed resolution-rate breakdown, mapped onto `_SOURCE_ROWS`'s
    categories. Resolved percentage is the share that produced any
    usable route (everything except `"miss"`); real traffic measured
    around 52.6%, so that region is expected, not a defect. Returns
    `{"rows": [...], "total": N, "resolved_pct": float_or_None}`;
    `resolved_pct` is `None` when `total` is zero. `total` counts every
    row in the window, folding an unrecognised `route_source` into
    `_OTHER_SOURCE_LABEL` rather than dropping it.
    """
    now_dt = now or datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=window_days)).isoformat(timespec="seconds")
    counts = history_db.route_source_counts(conn, since=since)

    total = sum(counts.values())
    if total == 0:
        return {"rows": [], "total": 0, "resolved_pct": None}

    resolved = total - counts.get("miss", 0)
    resolved_pct = round((resolved / total) * 100, 1)
    # label/gloss are translated here, the one place both
    # _stats_cards_html() and _stats_table_html() read them from.
    rows = [
        (i18n.t(label), i18n.t(gloss), counts.get(source, 0))
        for source, label, gloss in _SOURCE_ROWS
    ]
    known_sources = {source for source, _label, _gloss in _SOURCE_ROWS}
    other_count = sum(
        n for source, n in counts.items() if source not in known_sources)
    if other_count:
        rows.append((
            i18n.t(_OTHER_SOURCE_LABEL), i18n.t(_OTHER_SOURCE_GLOSS), other_count))
    return {"rows": rows, "total": total, "resolved_pct": resolved_pct}


def _stats_cards_html(rows):
    """Mobile stacked-prose representation of the resolution-statistics
    table: one `<li class="data-card">` per `(label, gloss, count)` in
    `rows`. A column of full sentences must wrap, not scroll
    (`.data-table--prose` in style.css), so the Description sentence
    renders full and untruncated rather than behind a disclosure.
    """
    if not rows:
        return ""
    items = []
    for label, gloss, count in rows:
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary">%s</span>'
            '<span class="data-card__value">'
            '<span class="data-card__label">%s</span> %s'
            "</span>"
            "</div>"
        ) % (escape_html(label), escape_html(i18n.t(_STATS_HEADERS[2])), escape_html(count))
        desc = '<p class="data-card__desc">%s</p>' % escape_html(gloss)
        items.append('<li class="data-card">%s%s</li>' % (primary, desc))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _stats_table_html(stats):
    """The resolution-statistics breakdown table, with its `.data-cards`
    mobile sibling emitted first (style.css's sibling-combinator toggle
    depends on that order — do not reorder). Empty when there is nothing
    to show: `_resolution_rate_tile_html()` already carries that message.
    The only table whose Description column holds real prose, so it is
    the only one opted into `layout.data_table()`'s `prose` keyword and
    `desc` column role.
    """
    if stats is _DB_UNAVAILABLE or stats["total"] == 0:
        return ""
    return _stats_cards_html(stats["rows"]) + layout.data_table(
        [i18n.t(header) for header in _STATS_HEADERS], stats["rows"],
        desc_columns=(1,), prose=True)
