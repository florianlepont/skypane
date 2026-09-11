"""companion/pages/history_page.py — CFG-06 (flight-history log),
06-CONTEXT.md D-18.

Completed by plan 06-09. Reads `server.history_db.recent_runway_events()`
and reuses `server.plane.render`'s two presentation-only mappings
(`display_airline_name()`, `_TYPE_DISPLAY_LABELS`) so this page and the
physical panel describe the same flight with the same words — a second,
web-only copy of those mappings would drift the moment a new aircraft
type is added, defeating the point of a QA page that is supposed to show
what the panel shows.

Every database access goes through `_safe_query()` (same shape as
`companion/pages/health_page.py`'s own helper), so a missing or locked
database degrades to the health-unavailable copy instead of raising.

`layout.data_table()` cannot host the Corroboration column's
`layout.status_dot()` markup — `data_table()` escapes every cell value it
is given, and escaping status_dot()'s pre-built `<span>` markup would
print the raw tags as visible text instead of rendering the dot. This
module therefore builds its own table markup (`_history_table_html()`),
matching `data_table()`'s CSS classes exactly for visual consistency,
escaping every other cell through `companion.layout.escape_html()`.
Only the escaping had to be hand-rolled, not the scroll container: this
table is still wrapped in the same horizontal-scroll container
`data_table()` itself emits, so History's 6-column table (dropped from
7 by A-36/D-19 — see the note above `_HEADERS`) matches Airlines and
Health's phone behaviour (D-03) — dropping that wrapper along with the
escaping, when this table was first hand-built, was the original defect
this module now closes.

Callsign+Hex and Aircraft type+Airline are each rendered as one merged,
one-line cell (`_merged_cell()`, 06.6.1 D-02/data-density.md sketch 003
Variant B) instead of two separate columns — this cut the table from 9
columns to 7 without changing row height, which is the property that
was chosen over a stacked-cell layout specifically to keep scanning many
rows fast.
"""
import re
import sqlite3
from datetime import datetime

from companion.layout import escape_html
import companion.layout as layout
from server import device_config
from server import history_db
from server.plane import render as panel_render

# D-13 keeps runway_events forever; this is a *display* limit for
# readability, not a retention policy — same distinction the Health
# page's BATTERY_TREND_LIMIT already documents for device_health.
HISTORY_ROW_LIMIT = 50

# Phase 18: the tab is "Flights" now — "History" read as a log to a
# household member, when the page is really "which planes has the frame
# shown".
PAGE_TITLE = "Flights"
PAGE_PURPOSE_TEMPLATE = "The latest %d aircraft the frame has shown."
LIGHTBOX_ARIA_LABEL = "Picture shown on the frame"

# --- 06.6.4.1-05 (D-18/D-19): moved verbatim from
# companion/pages/preview_page.py, which stays on disk and stays routed
# until plan 08 absorbs and retires it — both modules briefly hold these
# symbols. Behaviour is unchanged; only the module has changed.

# D-P2-03 / server/panel_preview.py's own module docstring: the render
# gallery's colours are nominal render-internal swatches, not colour-
# accurate against real Spectra 6 glass — two of the six are still
# explicitly interim pending Phase 7's on-glass calibration. This caveat
# is not optional politeness: without it a user comparing any of these
# renders to the frame on the wall could mistake an expected render/glass
# colour mismatch for a hardware fault. Quick task 260903-etm retired
# History's top-of-page render gallery outright; this caveat is now
# rehomed into LIGHTBOX_NOTE below (composed, not reworded) since the
# per-row View-panel lightbox is the only place on this page a rendered
# panel image is shown any more — its wording and its value are
# unchanged.
COLOUR_CAVEAT = (
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.")

_GALLERY_ROUTE_PREFIX = "/gallery/"

# D-22/06.6.3-RESEARCH.md Pitfall 2: server/poll_loop.py::_save_to_gallery()
# names each gallery file `now_iso.replace(":", "-") + ".png"` — sanitising
# every colon in the ISO string, not just the ones in the time portion. A
# naive full-string `.replace("-", ":")` reversal would also mangle the
# DATE portion's own hyphens (e.g. "2026-08-30" -> "2026:08:30"), so the
# reversal below only ever touches the time+offset portion, matched by
# this exact regex against the substring after the first "T".
_GALLERY_TIME_PATTERN = re.compile(
    r"^(\d{2})-(\d{2})-(\d{2})([+-]\d{2})-(\d{2})$")


def _gallery_name_to_iso(name):
    """Reverse `_save_to_gallery()`'s ':' -> '-' filename sanitisation, or
    return None (never raising) on any name that doesn't match the exact
    expected shape.

    A manually-dropped or renamed file in the gallery directory is not
    attacker-reachable over the network (T-06.6.3-14), but this function
    must still degrade safely on an unexpected shape: a missing "T"
    separator, or a time+offset portion that doesn't match
    `_GALLERY_TIME_PATTERN`, both return None rather than raising —
    `nearest_gallery_entry()` below skips any entry it cannot recover a
    timestamp from, in either case.
    """
    stem = name[:-4] if name.endswith(".png") else name
    if "T" not in stem:
        return None
    date_part, _, time_part = stem.partition("T")
    match = _GALLERY_TIME_PATTERN.match(time_part)
    if not match:
        return None
    hh, mm, ss, tz_sign_hh, tz_mm = match.groups()
    return "%sT%s:%s:%s%s:%s" % (date_part, hh, mm, ss, tz_sign_hh, tz_mm)


_NO_FLIGHTS_HEADING = "No flights yet."
_NO_FLIGHTS_BODY = (
    "No flights detected yet — check back after the next poll cycle.")

# Reused verbatim from companion/pages/health_page.py's own
# HEALTH_UNAVAILABLE_TEXT (companion/pages/__init__.py's contract: no
# page module imports another page module, so the string is duplicated
# here rather than imported).
_HISTORY_UNAVAILABLE_TEXT = (
    "The flight list is temporarily unavailable — try again in a minute.")

# 6 entries (A-36/D-19: dropped from 7 — one runway is tracked at a
# time, so the Runway column carried the same value on every row while
# costing ~90px of a 1,305px table that had to fit an 880px column. The
# value now lives in each rendered <tr>'s title attribute and in the
# mobile card's More details, so nothing is lost by dropping the
# desktop column). Left-to-right order is otherwise unchanged from the
# previous 9-column table so a returning user's scanning habit still
# works. "Callsign" and "Type" are still merged columns: each carries a
# secondary value (hex, airline) rendered on the same line via
# _merged_cell() (06.6.1 D-02).
_HEADERS = (
    "Timestamp", "Callsign", "Type", "Route", "State", "Corroboration",
)

# A-36/D-19: names the .data-table-wrap scroller for keyboard users — at
# 1,305px inside an 880px column the table scrolled behind a 12px
# shadow that a keyboard-only user had no way to reach at all.
# tabindex="0" plus this label turn the wrapper itself into a focusable,
# named region a keyboard user can Tab to and arrow-scroll.
SCROLLER_ARIA_LABEL = "Recent flights table, scrollable"

# Class names styled by companion/static/style.css (plan 06.6.1-01, same
# wave). Duplicated here rather than imported because a page module has
# no import path to the stylesheet; companion/test_view_pages.py's
# cross-file drift guard reads style.css from disk and requires all
# three to appear there, so the two cannot silently diverge.
CELL_PRIMARY_CLASS = "cell-primary"
CELL_SECONDARY_CLASS = "cell-secondary"
CELL_SEPARATOR_CLASS = "cell-inline-sep"

# The middle-dot glyph, defined once so the separator can never be typed
# as a hyphen or a bullet at one call site and a middle dot at another.
CELL_SEPARATOR_TEXT = "·"

# history_db's stored corroborated column (the TEXT form of
# True/False/None) mapped to the same three (status, label) pairs
# companion/pages/health_page.py's own _CORROBORATION_ROWS uses (D-15) —
# so the two pages read consistently. An unrecognised/legacy value falls
# back to the warning class rather than a fabricated label.
#
# 19-06-PLAN.md Task 2 (D-06): health_page._CORROBORATION_ROWS' True/
# False labels were rewritten into plain language ("Agreement"/
# "Disagreement" -> "Both agree"/"They disagree") — retargeted here in
# the same pass, exactly what test_view_pages.py's cross-file drift
# guard (_corroboration_copy_agrees_with_health_page()) exists to force.
_CORROBORATION_LABELS = {
    "True": ("ok", "Both agree"),
    # quick task 260902-w4t (UIR-04): shortened from "Single-source
    # (uncorroborated)" - the parenthetical made History's Corroboration
    # column an overlong 253px. The long form survives below as a
    # tooltip via _CORROBORATION_TITLES; health_page._CORROBORATION_ROWS
    # still carries the long form as ITS OWN visible label by design -
    # the two pages are allowed to diverge in copy now, and
    # test_view_pages.py's restated drift guard is what keeps this
    # constant's tooltip text honest against Health's copy.
    "None": ("ok", "Single-source"),
    "False": ("warn", "They disagree"),
}
_DEFAULT_CORROBORATION = ("warn", "Unknown")

# quick task 260902-w4t (UIR-04): the long form moved out of the visible
# "None" label above. Keys absent from this dict resolve via .get(key,
# "") to no tooltip at all (True/False need none).
#
# 19-06-PLAN.md Task 2 (D-06): kept equal to health_page's own "None"
# visible label ("Only one saw it", not the retired "Single-source
# (uncorroborated)"), per test_view_pages.py's own drift guard.
_CORROBORATION_TITLES = {
    "None": "Only one saw it",
}

_DB_UNAVAILABLE = object()  # Same sentinel discipline as health_page.py:
# distinguishes "query raised" from "query succeeded, legitimately empty".

# D-20: the filter bar's copy (06.6.3-UI-SPEC.md's Copywriting Contract),
# driven client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract — reused verbatim by
# 06.6.3-06's Airlines page (that plan supplies its own label/empty
# copy, same contract).
_FILTER_INPUT_ID = "history-filter-input"
_FILTER_LABEL_TEXT = "Filter by callsign or hex"
_FILTER_EMPTY_HEADING = "No matching flights"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d flights.")

# D-23: the copy-to-clipboard accessible-name contract
# (06.6.3-UI-SPEC.md's Copywriting Contract: "Copy {field}").
# A-37/D-20: each is now a %s template naming the row (a callsign, or a
# hex/NO_CALLSIGN_NOTE_TEXT fallback via _row_copy_name() below) — the
# bare constants used to leave every one of a page's ~50 copy buttons
# sharing one identical accessible name. Constant names are unchanged so
# no unrelated reference breaks.
_COPY_CALLSIGN_LABEL = "Copy callsign %s"
_COPY_HEX_LABEL = "Copy hex ID for %s"
_COPY_TIMESTAMP_LABEL = "Copy timestamp for %s"

# quick task 260902-w4t (UIR-06): the presentational note shown beside a
# promoted hex when a row has no callsign - a module-level constant so
# the desktop cell (_callsign_hex_cell()) and the mobile card
# (_history_cards_html()) cannot drift onto two different wordings.
NO_CALLSIGN_NOTE_TEXT = "no callsign"


def _row_copy_name(callsign, hex_value):
    """The value substituted for the `%s` in each `_COPY_*_LABEL`
    template (A-37/D-20): the row's callsign, falling back to its hex
    when the callsign is absent, and finally to NO_CALLSIGN_NOTE_TEXT so
    a row with neither never leaves the accessible name with a dangling
    "for ". Mirrors _callsign_hex_cell()'s own three-branch fallback
    order exactly — a future edit to one is visibly obliged to touch
    the other.
    """
    return callsign or hex_value or NO_CALLSIGN_NOTE_TEXT

# D-20: the per-row "View panel near this time" lookup and its shared
# lightbox. VIEW_PANEL_LABEL is verbatim from D-20. LIGHTBOX_DIALOG_ID,
# and the three data-view-panel-* attribute names below, must equal
# companion/static/panel-lookup.js's own literals exactly - duplicated,
# not imported (a page module has no import path to a static script),
# and pinned by companion/test_view_pages.py's three-file DOM-contract
# guard, which reads panel-lookup.js and style.css from disk and asserts
# all of these appear in all three places. A drift here means the
# button silently does nothing with no signal from either file in
# isolation.
VIEW_PANEL_LABEL = "View panel near this time"
LIGHTBOX_DIALOG_ID = "panel-lookup-dialog"
LIGHTBOX_CAPTION_TEMPLATE = "Picture from %s"
# Quick task 260903-etm: composed from the pre-existing nearest-render
# sentence plus COLOUR_CAVEAT (verbatim, unreworded) rather than two
# independent strings — the lightbox is now the only surface on this
# page that shows a rendered panel image at a size where a user would
# actually compare its colours to the frame on the wall, so the caveat's
# safety rationale (see COLOUR_CAVEAT's own comment above) belongs here.
# One source of the sentence, no second wording anywhere. Developer
# sign-off received 2026-09-03: composition kept as-is.
LIGHTBOX_NOTE = (
    "This is the nearest recorded render, not necessarily from this "
    "exact flight — the panel updates on its own wake/poll cycle. "
    + COLOUR_CAVEAT)
_VIEW_PANEL_SRC_ATTR = "data-view-panel-src"
_VIEW_PANEL_CAPTION_ATTR = "data-view-panel-caption"
_VIEW_PANEL_CLOSE_ATTR = "data-view-panel-close"

# D-21: the unresolved-airline link. The fragment must equal
# companion/pages/health_page.py's SERVER_DATA_SECTION_ID constant -
# duplicated, not imported, since companion/pages/__init__.py's only
# documented boundary forbids one page module importing another. This is
# the one cross-page string coupling this phase introduces; held by
# discipline and pinned by companion/test_view_pages.py's cross-module
# guard (asserts UNRESOLVED_LINK_HREF ends with "#" + the real
# health_page.SERVER_DATA_SECTION_ID value, never a re-typed literal).
UNRESOLVED_LINK_HREF = "/health#server-data"
UNRESOLVED_LINK_TEXT = "View unresolved prefixes"
# quick task 260902-w4t (UIR-05): the anchor's own class, so it renders
# visibly separated from the airline text it follows instead of reading
# as one glued run - `text-label` for the existing quiet-link treatment,
# plus a dedicated spacing hook styled in style.css.
UNRESOLVED_LINK_CLASS = "text-label cell-unresolved-link"

# quick task 260902-w4t (UIR-05): a missing AIRLINE used to fall back to
# `panel_render.ROUTE_FALLBACK_TEXT` ("Route unavailable") - a string
# that describes a different noun (the route, not the airline) and made
# the exact same phrase appear twice in one unresolved row (once in the
# Type+Airline cell, once in the Route cell). This constant gives the
# airline its own fallback text so the two columns stop sharing one
# string.
AIRLINE_FALLBACK_TEXT = "Airline unknown"

# UXA-05/06.6.3-RESEARCH.md Pitfall 1: the audit's own evidence names
# "on_runway"/"approaching"/"departed" as the raw confirmed_state values
# leaking into this page, but server/plane/runway_config.py's
# infer_runway_config() - the only function that ever writes a
# confirmed_state value to history_db - only ever produces exactly
# "departing" or "arriving" (or leaves the prior value unchanged). Any
# other non-empty value (a future state this codebase hasn't invented
# yet, or legacy test data) degrades to a title-cased, underscore-
# stripped rendering of the raw string via _confirmed_state_label()
# below, never a bare raw value and never the literal word "None".
_CONFIRMED_STATE_LABELS = {
    "departing": "Departing",
    "arriving": "Arriving",
}


def _confirmed_state_label(raw):
    """Map a runway_events.confirmed_state raw value to its presentation
    label (UXA-05). Falsy input (None or "") renders as an empty string,
    matching the pre-existing empty-cell behaviour this replaces - never
    the literal word "None". A recognised value ("departing"/"arriving")
    maps via _CONFIRMED_STATE_LABELS; anything else falls back to a
    title-cased, underscore-stripped rendering of the raw string
    (06.6.3-RESEARCH.md Pitfall 1's documented fallback), so a future or
    unexpected state still reads as a human label instead of a raw
    machine value.
    """
    if not raw:
        return ""
    label = _CONFIRMED_STATE_LABELS.get(raw)
    if label is not None:
        return label
    return raw.replace("_", " ").title()


def _runway_label(raw):
    """Map a runway_events.tracked_runway raw id to
    server.device_config.runway_label()'s human label (UXA-05), e.g. "3"
    -> "Runway 3 (07/25)". Only ever looks the id up when it is a real
    device_config.RUNWAY_IDS member - an unrecognised id (a stale/
    foreign value on an old row) degrades to the raw id unchanged rather
    than raising, matching this module's "never raise, degrade to a
    documented fallback" discipline throughout. Falsy input renders as
    an empty string, same as before this helper existed.
    """
    if raw and raw in device_config.RUNWAY_IDS:
        return device_config.runway_label(raw)
    return raw or ""


def nearest_gallery_entry(entries, row_ts):
    """Return the `(filename, iso)` pair from `entries` whose filename-
    recovered timestamp is the latest one at or before `row_ts`, or
    `None` when no such entry exists (D-20).

    A linear scan over `entries` - the already-in-memory, already-
    ordered list threaded into `ctx["gallery_entries"]` by
    `companion/app.py`'s own `gallery_entries()` listing helper. No
    database query, no new index, no stored relationship: the panel
    refreshes on the device's own wake/poll cycle rather than once per
    detected flight, so no true per-flight render relationship exists
    to store in the first place.

    An entry whose filename does not yield a recoverable timestamp
    (`_gallery_name_to_iso()` returns `None`) is skipped, never matched,
    never raised on. An unparseable or empty `row_ts` returns `None`
    rather than raising. Comparison is always between parsed timezone-
    aware `datetime` values, never between raw strings - gallery
    filenames carry a local UTC offset while history timestamps are
    UTC-suffixed, so a lexicographic compare would silently mis-rank
    across an offset boundary.
    """
    if not row_ts:
        return None
    try:
        row_dt = datetime.fromisoformat(row_ts)
    except ValueError:
        return None

    best = None
    best_dt = None
    for name in entries or []:
        iso = _gallery_name_to_iso(name)
        if iso is None:
            continue
        try:
            entry_dt = datetime.fromisoformat(iso)
        except ValueError:
            continue
        if entry_dt > row_dt:
            continue
        if best_dt is None or entry_dt > best_dt:
            best = (name, iso)
            best_dt = entry_dt
    return best


def lightbox_caption_text(iso):
    """Phase 18 (audit): the lightbox caption for a gallery entry's ISO
    timestamp — a humanised local-time form ("Picture from 3 Sep 23:38")
    instead of the raw ISO string, falling back to the ISO value only
    when it does not parse. Plain text; callers escape it.
    """
    parsed = layout.parse_iso(iso)
    if parsed is None:
        return LIGHTBOX_CAPTION_TEMPLATE % iso
    local = parsed.astimezone(layout.LOCAL_TZ) if parsed.tzinfo else parsed
    when = "%d %s %s" % (
        local.day, layout._MONTH_ABBR[local.month - 1], layout.local_clock_text(parsed, None))
    return LIGHTBOX_CAPTION_TEMPLATE % when


def _view_panel_button_html(name, iso):
    """A D-20 "View panel near this time" trigger button - one per
    History row that has a nearest render. Reuses `.copy-btn`'s exact
    28x28-visual/44x44-hit-area shape (its pseudo-element already
    synthesises a compliant pointer/touch hit area, so this control
    inherits it with no new CSS and no accessibility trade-off).

    `name` (the matched gallery filename) becomes the trigger source
    attribute, joined onto the existing gallery route prefix. `iso` (the
    matched entry's recovered ISO timestamp) is formatted through
    LIGHTBOX_CAPTION_TEMPLATE into the trigger caption attribute -
    `companion/static/panel-lookup.js` copies that attribute's value
    verbatim into the lightbox caption on open (`caption.textContent =
    captionText`, no client-side templating of any kind), so the final
    attribute value must already be UI-SPEC §8.3's exact "Panel near
    {timestamp}" copy. Both attributes are escaped exactly once, at this
    point of interpolation. Quick task 260903-etm: the trigger's `title`
    mirrors its `aria-label` verbatim, so a sighted pointer user gets the
    same native tooltip a screen-reader user already gets as the
    accessible name.
    """
    src = "%s%s" % (_GALLERY_ROUTE_PREFIX, escape_html(name))
    caption = lightbox_caption_text(iso)
    escaped_label = escape_html(VIEW_PANEL_LABEL)
    return (
        '<button type="button" class="copy-btn" %s="%s" %s="%s" '
        'title="%s" aria-label="%s">%s</button>'
    ) % (
        _VIEW_PANEL_SRC_ATTR, src,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(caption),
        escaped_label,
        escaped_label,
        layout.icon_html("icon-nav-preview"),
    )


def _lightbox_html():
    """The single shared D-20 lightbox `<dialog>`, emitted once per page
    (never once per row) by `render()`, only when at least one row
    actually carries a trigger button. Its image src/alt and caption
    text are written by `companion/static/panel-lookup.js` on trigger
    click - this function only emits the note, which is a static,
    server-rendered constant the script never writes.
    """
    return (
        '<dialog class="lightbox" id="%s" aria-label="%s">'
        '<img class="lightbox__image" alt="">'
        '<p class="lightbox__caption text-label mono"></p>'
        '<p class="lightbox__note text-body">%s</p>'
        '<button type="button" %s>Close</button>'
        "</dialog>"
    ) % (LIGHTBOX_DIALOG_ID, escape_html(LIGHTBOX_ARIA_LABEL),
         escape_html(LIGHTBOX_NOTE), _VIEW_PANEL_CLOSE_ATTR)


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except (sqlite3.Error, OSError):
        return _DB_UNAVAILABLE


def history_rows(conn):
    """The most recent `HISTORY_ROW_LIMIT` `runway_events` rows, newest
    first (matches `history_db.recent_runway_events()`'s own ordering).
    """
    return history_db.recent_runway_events(conn, limit=HISTORY_ROW_LIMIT)


def format_event_row(row, now=None):
    """Turn one `runway_events` database row into the display cells this
    page renders. Never raises: every lookup degrades to a documented
    fallback rather than an empty cell or an exception.

    `now` is the reference instant (a UTC ISO-8601 string) used to render
    the Timestamp cell's relative-age suffix; omitting it degrades to an
    absolute-only timestamp rather than raising.
    """
    aircraft_type = row.get("aircraft_type")
    if isinstance(aircraft_type, str) and aircraft_type:
        type_key = aircraft_type.strip().upper()
        aircraft_type_label = panel_render._TYPE_DISPLAY_LABELS.get(type_key, aircraft_type)
    else:
        aircraft_type_label = ""

    airline = row.get("airline")
    airline_label = (
        panel_render.display_airline_name(airline) if airline
        else AIRLINE_FALLBACK_TEXT)

    origin = row.get("origin")
    destination = row.get("destination")
    route_label = (
        "%s → %s" % (origin, destination) if origin and destination
        else panel_render.ROUTE_FALLBACK_TEXT)

    corroboration_status, corroboration_label = _CORROBORATION_LABELS.get(
        row.get("corroborated"), _DEFAULT_CORROBORATION)

    return {
        # Plain-text "ISO (Nm ago)" form, kept under its own distinct key
        # for any future plain-text-only need (mirrors
        # absolute_and_relative()'s own no-markup contract). No renderer
        # in this module uses this key for the visible Timestamp cell/
        # mobile primary-line time any more - both go through raw_ts +
        # layout.concise_timestamp_html() instead (D-09).
        "ts": layout.absolute_and_relative(row.get("ts"), now, fallback=""),
        # The raw, unformatted ISO timestamp string - the input
        # layout.concise_timestamp_html() needs (it builds its own
        # concise markup from the raw value plus a reference `now`, not
        # from absolute_and_relative()'s already-composed text).
        "raw_ts": row.get("ts") or "",
        "callsign": row.get("callsign") or "",
        "hex": row.get("hex") or "",
        "aircraft_type_label": aircraft_type_label,
        "airline_label": airline_label,
        "route_label": route_label,
        "confirmed_state": _confirmed_state_label(row.get("confirmed_state")),
        "corroboration_status": corroboration_status,
        "corroboration_label": corroboration_label,
        # quick task 260902-w4t (UIR-04): the long form for the "None"
        # (single-source) state, rendered as status_dot()'s optional
        # tooltip - "" (no tooltip) for True/False, which need none.
        "corroboration_title": _CORROBORATION_TITLES.get(row.get("corroborated"), ""),
        "tracked_runway": _runway_label(row.get("tracked_runway")),
    }


def _merged_cell(primary, secondary):
    """Build one complete `<td>` holding `primary` and, when present, a
    separator and `secondary` on the same line (06.6.1 D-02, sketch 003
    Variant B "Inline compact").

    `secondary` is only rendered when truthy: `format_event_row()`
    legitimately yields an empty string for a missing hex or a missing
    aircraft type, and rendering a separator with nothing after it would
    read as truncated data rather than as absent data. That is the whole
    reason this is a function rather than an inline format string used
    twice.

    Both arguments go through `escape_html()` here and nowhere else — do
    not pre-escape at the call site as well, or values would be
    double-encoded and print their entity forms as visible text (the
    same trap `stat_tile()`'s docstring already documents for
    `content_html`).
    """
    html = '<span class="%s">%s</span>' % (
        CELL_PRIMARY_CLASS, escape_html(primary))
    if secondary:
        html += '<span class="%s">%s</span><span class="%s">%s</span>' % (
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            CELL_SECONDARY_CLASS, escape_html(secondary))
    return "<td>%s</td>" % html


def _filter_text_attr(row):
    """The escaped, lowercased "{callsign} {hex}" pair for a row's
    `data-filter-text` attribute, computed once per row and reused by
    both the desktop `<tr>` and the mobile `<li>` for the same flight
    (T-06.6.3-09's mitigation: `escape_html()` applied before
    interpolation into the attribute, matching this codebase's single-
    escaping-choke-point discipline even though a callsign/hex value is
    unlikely to contain a quote character — 06.6.3-RESEARCH.md Pitfall 5).
    """
    combined = ("%s %s" % (row["callsign"], row["hex"])).strip().lower()
    return escape_html(combined)


def _copy_button_html(value, label):
    """A D-23 copy-to-clipboard button plus its `data-copy-feedback`
    sibling span — the exact shape `companion/static/copy-button.js`
    requires (the feedback element must be the button's immediate next
    sibling). `value` is escaped once here (T-06.6.3-11's mitigation:
    built only from the same already-escaped row values this page
    already renders, no separate unescaped derivation path); `label`
    (the D-23 "Copy {field}" accessible name, already formatted against
    the row by the caller via `_row_copy_name()` — A-37/D-20) is escaped
    the same way.

    A-37/D-20: the button's visible content (an SVG icon) is wrapped in
    a `<span class="copy-btn__icon" aria-hidden="true">`, with an empty
    `<span class="copy-btn__label"></span>` sibling immediately after
    it, both inside the button. `companion/static/copy-button.js` writes
    the transient "Copied" text into that label span's `textContent`
    only — never into the button element itself, which would destroy
    the SVG icon and have no way to restore it. This keeps the no-HTML-
    writing-sink rule intact: only `textContent` on a leaf `<span>`.
    """
    return (
        '<button type="button" class="copy-btn" data-copy-value="%s" '
        'aria-label="%s">'
        '<span class="copy-btn__icon" aria-hidden="true">%s</span>'
        '<span class="copy-btn__label"></span>'
        '</button>'
        '<span class="visually-hidden" data-copy-feedback role="status" '
        'aria-live="polite"></span>'
    ) % (escape_html(value), escape_html(label), layout.icon_html("icon-copy"))


def _callsign_hex_cell(callsign, hex_value):
    """The desktop Callsign+Hex column's own cell builder — reproduces
    `_merged_cell()`'s primary/separator/secondary markup exactly, then
    appends a copy button after the callsign and, when a hex value is
    present, another after the hex (D-23). This is a dedicated function
    rather than a `_merged_cell()` parameter specifically so the
    Type+Airline column (which also calls `_merged_cell()`) never gains
    copy buttons — the two columns must not share this behaviour.

    Three branches (quick task 260902-w4t, UIR-06):
    - `callsign` truthy: unchanged from before this task — the primary
      slot carries the callsign, and when `hex_value` is also present it
      follows as a secondary value with its own copy button.
    - `callsign` falsy, `hex_value` truthy: the hex is promoted into the
      primary slot (reusing the exact same `_copy_button_html(hex_value,
      _COPY_HEX_LABEL)` call the secondary path above already makes —
      not a second, re-typed call) so the cell is never left with a
      blank primary value and a dead copy button. A `NO_CALLSIGN_NOTE_TEXT`
      secondary note follows, with NO copy button of its own: it is
      presentational text, not data there is anything to copy.
    - both falsy: an empty primary span, no copy button, no separator,
      no secondary — a button that would copy `""` is exactly the dead
      affordance UIR-06 reported, so this branch emits none of it.
    """
    row_name = _row_copy_name(callsign, hex_value)
    if callsign:
        html = '<span class="%s">%s</span>%s' % (
            CELL_PRIMARY_CLASS, escape_html(callsign),
            _copy_button_html(callsign, _COPY_CALLSIGN_LABEL % row_name))
        if hex_value:
            html += '<span class="%s">%s</span><span class="%s">%s</span>%s' % (
                CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
                CELL_SECONDARY_CLASS, escape_html(hex_value),
                _copy_button_html(hex_value, _COPY_HEX_LABEL % row_name))
    elif hex_value:
        html = '<span class="%s">%s</span>%s' % (
            CELL_PRIMARY_CLASS, escape_html(hex_value),
            _copy_button_html(hex_value, _COPY_HEX_LABEL % row_name))
        html += '<span class="%s">%s</span><span class="%s">%s</span>' % (
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            CELL_SECONDARY_CLASS, escape_html(NO_CALLSIGN_NOTE_TEXT))
    else:
        html = '<span class="%s"></span>' % CELL_PRIMARY_CLASS
    return "<td>%s</td>" % html


def _unresolved_link_html():
    """The D-21 inline link to Health's Server & data section, used by
    both the desktop Type+Airline cell and the mobile Aircraft detail
    row when a row's airline could not be resolved. Carries
    UNRESOLVED_LINK_CLASS (quick task 260902-w4t, UIR-05) so it renders
    visibly separated from the airline text it follows instead of
    reading as one glued run.
    """
    return '<a class="%s" href="%s">%s</a>' % (
        escape_html(UNRESOLVED_LINK_CLASS),
        escape_html(UNRESOLVED_LINK_HREF), escape_html(UNRESOLVED_LINK_TEXT))


def _type_airline_cell(row):
    """The desktop Type+Airline column's own cell builder (D-21) —
    reproduces `_merged_cell()`'s primary/separator/secondary markup
    exactly, then appends `_unresolved_link_html()` immediately after it
    only when this row's airline could not be resolved, compared against
    the module's own `AIRLINE_FALLBACK_TEXT` constant (quick task
    260902-w4t, UIR-05 — was `panel_render.ROUTE_FALLBACK_TEXT`, a
    different noun's fallback, before AIRLINE_FALLBACK_TEXT existed),
    never a re-typed literal. A dedicated function rather than a
    `_merged_cell()` parameter, matching `_callsign_hex_cell()`'s own
    precedent: the Route column also calls the shared `_merged_cell()`
    and must never gain this link.
    """
    html = _merged_cell(row["aircraft_type_label"], row["airline_label"])
    if row["airline_label"] == AIRLINE_FALLBACK_TEXT:
        html = html[:-len("</td>")] + _unresolved_link_html() + "</td>"
    return html


def _filter_bar_html(total):
    """D-20's filter bar — a `<label>` + `<input type="search"
    data-filter-input>` (with `icon-search` inside, decorative), a live
    `<span data-filter-count>`, a `Clear` control, and a hidden-by-
    default `data-filter-empty` block. Entirely inert without JS —
    `companion/static/list-filter.js`'s own early-return guard means the
    full unfiltered table/card list underneath stays completely usable
    if the script never loads.
    """
    count_text = "%d of %d shown" % (total, total)
    empty_body = _FILTER_EMPTY_BODY_TEMPLATE % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        '<input type="search" id="%s" data-filter-input>'
        "</div>"
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<button type="button" data-filter-clear>Clear</button>'
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(_FILTER_LABEL_TEXT),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        escape_html(_FILTER_EMPTY_HEADING),
        escape_html(empty_body),
    )


# A-36/D-19: mirrors layout.concise_timestamp_html()'s own default
# fallback string exactly, so a caller can never tell the two functions
# apart by their empty-value behaviour.
_CLOCK_CELL_FALLBACK = "no reading yet"


def _clock_cell_html(raw_ts, now):
    """The desktop table's clock-only Timestamp cell (A-36/D-19): a
    local clock ("HH:MM", or "D Mon HH:MM" once the row is no longer
    from today — layout.local_clock_text(), Europe/Paris, Phase 18
    D-06) with the full ISO still carried in the `title` attribute, and
    no relative-age suffix — that suffix is exactly what made
    layout.concise_timestamp_html()'s own rendering too wide for this
    column. Built directly from layout.parse_iso() +
    layout.local_clock_text() rather than calling
    concise_timestamp_html() itself, and this function must never be
    used as a reason to edit companion/layout.py — plan 19-04 owns that
    file in this same wave.

    Degrades exactly the way concise_timestamp_html() does: a falsy
    raw_ts returns the escaped fallback text (never markup); an
    unparseable raw_ts returns a span carrying the raw value in both
    the title and the visible text. Never raises.
    """
    if not raw_ts:
        return escape_html(_CLOCK_CELL_FALLBACK)
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return '<span class="mono" title="%s">%s</span>' % (
            escape_html(raw_ts), escape_html(raw_ts))
    now_parsed = layout.parse_iso(now)
    return '<span class="mono" title="%s">%s</span>' % (
        escape_html(raw_ts),
        escape_html(layout.local_clock_text(parsed, now_parsed)))


def _history_table_html(formatted_rows, now=None):
    if not formatted_rows:
        return layout.empty_state(_NO_FLIGHTS_HEADING, _NO_FLIGHTS_BODY)

    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in _HEADERS)

    body_rows = []
    for index, row in enumerate(formatted_rows):
        row_class = "row-alt" if index % 2 else "row"
        # A-36/D-19: _clock_cell_html() already returns already-safe
        # <span class="mono" title="..."> markup - this file hand-rolls
        # its own <td> cells (it does not call layout.data_table()), so
        # the return value is interpolated directly with no wrapping
        # escape_html() call, matching _merged_cell()'s own documented
        # "do not double-escape already-safe markup" discipline. D-20's
        # View-panel trigger (already-safe markup, or "" for a row with
        # no nearest render - render() computes this once per row and
        # both representations share it) is appended after the
        # timestamp markup.
        cells = (
            "<td>%s%s</td>" % (
                _clock_cell_html(row["raw_ts"], now),
                row.get("view_panel_html", "")),
            _callsign_hex_cell(row["callsign"], row["hex"]),
            _type_airline_cell(row),
            "<td>%s</td>" % escape_html(row["route_label"]),
            "<td>%s</td>" % escape_html(row["confirmed_state"]),
            "<td>%s</td>" % layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"]),
        )
        # D-20: data-filter-text drives companion/static/list-filter.js's
        # match — the same value the mobile <li> for this same row also
        # carries (_history_cards_html() below), so a filter query
        # matches both representations identically. data-filter-group
        # carries this row's loop index (shared with the <li> at the same
        # index in _history_cards_html(), since render() feeds both
        # functions the identical formatted_rows list) so list-filter.js
        # can count logical rows once instead of once per representation.
        # A-36/D-19: title carries the row's runway — the value the
        # dropped Runway column used to show — escaped through
        # escape_html() at this point of interpolation, same as every
        # other attribute value this function builds.
        body_rows.append(
            '<tr class="%s" data-filter-text="%s" data-filter-group="%d" '
            'title="%s">%s</tr>'
            % (row_class, _filter_text_attr(row), index,
               escape_html(row["tracked_runway"]), "".join(cells)))

    return (
        '<div class="data-table-wrap" tabindex="0" role="region" '
        'aria-label="%s">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (escape_html(SCROLLER_ARIA_LABEL), header_cells, "".join(body_rows))


def _history_cards_html(formatted_rows, now=None):
    """Mobile compact-card representation (D-07) - one `<li>` per row,
    built from the exact same `formatted_rows` list _history_table_html()
    consumes, never a second independently-derived data pass. Returns
    the empty string for an empty list, so render() shows only the
    unchanged empty_state() block in that case, never an empty
    `<ul class="history-cards">` sitting beside it.

    companion/static/style.css's breakpoint toggle (`.history-cards ~
    .data-table-wrap`) requires this `<ul>` to render as a DOM sibling
    immediately before the desktop table - render() below preserves
    that ordering; do not move this call after _history_table_html()'s.

    Every seven-category UXA-01 acceptance requirement (callsign, time,
    route, state, aircraft/airline, corroboration, runway, hex, full
    timestamp) is reachable: the primary/secondary lines carry
    callsign/time/route/state; the nested `<details>` disclosure carries
    the rest, matching the Battery readings table's own native-disclosure
    pattern (no custom JS toggler).
    """
    if not formatted_rows:
        return ""
    items = []
    for index, row in enumerate(formatted_rows):
        # D-09: the identical layout.concise_timestamp_html() call the
        # desktop cell uses (same raw_ts, same now) - the desktop table
        # and the mobile card always render byte-identical timestamp
        # markup for the same row. Already-safe markup, interpolated
        # verbatim, never re-escaped. D-20's View-panel trigger (already-
        # safe markup, or "" for a row with no nearest render) follows
        # the time span - the exact same value the desktop cell above
        # carries for this same row (render() computes it once per row).
        #
        # quick task 260902-w4t (UIR-06): mirrors _callsign_hex_cell()'s
        # desktop hex-only branch exactly — when this row has no
        # callsign but does have a hex, the primary slot carries the hex
        # (never left blank) and a NO_CALLSIGN_NOTE_TEXT secondary note
        # follows it, before the time span. A future edit to one branch
        # is visibly obliged to touch the other.
        if row["callsign"]:
            primary_value_html = (
                '<span class="cell-primary mono">%s</span>'
                % escape_html(row["callsign"]))
        elif row["hex"]:
            primary_value_html = (
                '<span class="cell-primary mono">%s</span>'
                '<span class="cell-secondary">%s</span>'
            ) % (escape_html(row["hex"]), escape_html(NO_CALLSIGN_NOTE_TEXT))
        else:
            primary_value_html = '<span class="cell-primary mono"></span>'
        primary = (
            '<div class="history-card__primary">'
            "%s"
            '<span class="history-card__time">%s</span>%s'
            "</div>"
        ) % (
            primary_value_html,
            layout.concise_timestamp_html(row["raw_ts"], now),
            row.get("view_panel_html", ""),
        )
        secondary = (
            '<div class="history-card__secondary">'
            "<span>%s</span>"
            "<span>%s</span>"
            "</div>"
        ) % (escape_html(row["route_label"]), escape_html(row["confirmed_state"]))
        # D-23: all three mobile copy buttons (callsign, hex, full
        # timestamp) live inside this <details> disclosure — including
        # the callsign one, which is already visible on the primary
        # line above but is repeated here (as its own Callsign dt/dd
        # pair) specifically to give the copy affordance a home
        # alongside its Hex/Full-timestamp siblings, matching the
        # "same button+feedback-sibling shape" contract everywhere.
        # D-21: the same unresolved-airline link the desktop Type+Airline
        # cell carries, appended after the airline value here too - keyed
        # on the same airline_label/AIRLINE_FALLBACK_TEXT comparison
        # (quick task 260902-w4t, UIR-05 — was ROUTE_FALLBACK_TEXT), so
        # the mobile representation never silently loses the affordance.
        unresolved_link = (
            _unresolved_link_html()
            if row["airline_label"] == AIRLINE_FALLBACK_TEXT else "")
        # A-37/D-20: the mobile disclosure's three copy buttons name
        # their own row too, via the same _row_copy_name() fallback
        # order the desktop cell uses.
        row_name = _row_copy_name(row["callsign"], row["hex"])
        details = (
            '<details class="history-card__details">'
            "<summary>More details</summary>"
            "<dl>"
            '<dt>Callsign</dt><dd class="mono">%s%s</dd>'
            "<dt>Aircraft</dt><dd>%s %s %s%s</dd>"
            "<dt>Corroboration</dt><dd>%s</dd>"
            "<dt>Runway</dt><dd>%s</dd>"
            '<dt>Hex</dt><dd class="mono">%s%s</dd>'
            '<dt>Full timestamp</dt><dd class="mono">%s%s</dd>'
            "</dl>"
            "</details>"
        ) % (
            escape_html(row["callsign"]),
            _copy_button_html(row["callsign"], _COPY_CALLSIGN_LABEL % row_name),
            escape_html(row["aircraft_type_label"]),
            escape_html(CELL_SEPARATOR_TEXT),
            escape_html(row["airline_label"]),
            unresolved_link,
            layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"]),
            escape_html(row["tracked_runway"]),
            escape_html(row["hex"]),
            _copy_button_html(row["hex"], _COPY_HEX_LABEL % row_name),
            escape_html(row["raw_ts"]),
            _copy_button_html(row["raw_ts"], _COPY_TIMESTAMP_LABEL % row_name),
        )
        items.append(
            '<li class="history-card" data-filter-text="%s" '
            'data-filter-group="%d">%s%s%s</li>'
            % (_filter_text_attr(row), index, primary, secondary, details))
    return '<ul class="history-cards">%s</ul>' % "".join(items)


def render(ctx):
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()
    rows = _safe_query(state_dir, history_rows)

    # D-10: the display-window label folded into the header's purpose
    # sentence, using the real HISTORY_ROW_LIMIT constant rather than a
    # hardcoded "50".
    header = layout.page_header(
        PAGE_TITLE, purpose=PAGE_PURPOSE_TEMPLATE % HISTORY_ROW_LIMIT)

    # Quick task 260903-etm: developer redirection, superseding quick task
    # 260903-c4o's own always-visible render-gallery section on this same
    # unmerged branch — the section (heading, count caption, colour
    # caveat, tile grid) does not exist in any form any more. Every
    # rendered panel stays reachable through the per-row "View panel near
    # this time" lightbox (D-20) below, which this task keeps intact.
    # gallery_entries_list is NOT gallery-section state — it is the input
    # to nearest_gallery_entry() below, which every per-row trigger
    # depends on. Deliberately NOT (re)introduced: a page-level freshness
    # apparatus (a Refresh link's data-loaded-at attribute and paired
    # hidden data-stale-banner) — each per-row trigger's own lookup is
    # already a sufficient staleness signal, and duplicating Health's
    # whole-page freshness mechanism here would be scope no decision asks
    # for. Do not "restore" it later as an oversight.
    gallery_entries_list = ctx.get("gallery_entries") or []

    if rows is _DB_UNAVAILABLE:
        body = '<p class="text-body">%s</p>' % escape_html(_HISTORY_UNAVAILABLE_TEXT)
        lightbox_html = ""
    else:
        formatted_rows = [format_event_row(row, now) for row in rows]
        # D-20: the nearest-render match is computed exactly once per
        # row, here, and stored onto the row dict both
        # _history_table_html() and _history_cards_html() below already
        # share — never two independent lookups that could disagree
        # between the desktop and mobile representations. A row with no
        # match carries the empty string, never a disabled/broken
        # control.
        for row in formatted_rows:
            match = nearest_gallery_entry(gallery_entries_list, row["raw_ts"])
            row["view_panel_html"] = (
                _view_panel_button_html(match[0], match[1]) if match else "")
        # The shared lightbox is emitted exactly once per page, and only
        # when at least one row actually carries a trigger button - with
        # an empty gallery entry list every row's match is None, so
        # neither a button nor this dialog is ever rendered (the truth
        # this task's own acceptance criteria pin).
        has_view_panel_button = any(
            row["view_panel_html"] for row in formatted_rows)
        lightbox_html = _lightbox_html() if has_view_panel_button else ""
        if not formatted_rows:
            # No filter bar over nothing to filter — matches the table/
            # card renderers' own "no chrome when there's no data" rule.
            body = _history_table_html(formatted_rows, now)
        else:
            # Cards render before the table - companion/static/style.css's
            # `.history-cards ~ .data-table-wrap` sibling-combinator
            # toggle (06.6.3-02) depends on this exact DOM order.
            body = (
                _filter_bar_html(len(formatted_rows))
                + _history_cards_html(formatted_rows, now)
                + _history_table_html(formatted_rows, now))

    return header + body + lightbox_html
