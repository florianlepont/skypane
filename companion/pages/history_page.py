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
import urllib.parse
from datetime import datetime, timezone

import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.prefs as prefs
from server import device_config
from server import history_db
from server.plane import illustrations
from server.plane import manual_resolutions
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

# 5 entries (21-03-PLAN.md Task 1, D-15: dropped from 6 — the real
# available width at a 1280px viewport is 880px, not 1280px (240px
# sidebar + 32px gap + 128px .dashboard-main padding), and even the
# prior 6-column table already overflowed that box in French. "When"
# and "Flight" are now two-line cell-primary/cell-secondary pairs
# (_merged_cell(), reused from the prior "Timestamp"/"Callsign+Hex"
# merge, STACKED this time rather than inline — Pitfall 4, do not
# reach for layout.concise_timestamp_html()'s inline-suffix shape
# here): When's clock (primary) plus relative age (secondary,
# layout.relative_age_text()); Flight's callsign (primary) plus
# "{airline} · {aircraft type}" (secondary). The ICAO24 hex, the full
# ISO timestamp, the runway and the copy buttons that used to live in
# the Callsign+Hex/Timestamp cells move into a sibling expandable
# detail <tr> (_history_table_html()) — the sixth <th> is a
# visually-hidden "Details" toggle-column header, not a data column,
# so it is built directly rather than through _HEADERS' own i18n.t(h)
# loop. Corroboration keeps its dot but loses its visible label
# (status_dot(visually_hide_label=True)) — the dot alone already
# answers agree/disagree/unknown, and a ~90px-wide label would blow
# the 590px column-content budget the 21-UI-SPEC.md §F arithmetic
# depends on. _callsign_hex_cell()/_type_airline_cell() are retired:
# nothing else calls them (_history_cards_html() builds its own
# primary line inline) and their hex-copy-button/type+airline-merge
# shapes are absorbed into the new Flight cell and the Task 2 detail
# row instead.
_HEADERS = (
    "When", "Flight", "Route", "State", "Corroboration",
)

# 21-03-PLAN.md Task 1: the sixth, non-data <th> — a visually-hidden
# "Details" label naming the row-toggle column for a screen-reader
# user, never emitted through the _HEADERS/i18n.t(h) loop above (it
# has no column of formatted data behind it).
_DETAILS_HEADER_TEXT = "Details"

# 22-09-PLAN.md Task 1 (X5, 22-UI-SPEC.md §2): the row toggle is
# ICON-ONLY now — the fifty visible "More"/"Plus" text labels that used
# to sit one per row (and made the table's scan path fifty buttons
# wide) are gone, and with them the retired _MORE_TOGGLE_TEXT/
# _LESS_TOGGLE_TEXT pair. What replaces them is an accessible NAME, not
# a visible label: an icon-only control with no accessible name is the
# same defect class as T15/B10, so each button carries a translated
# `aria-label` that swaps with its state, exactly as the login card's
# show-password toggle does.
#
# The copy is deliberately WIDER than 22-UI-SPEC.md §1's base wording
# ("Show flight details" / "Hide flight details"): Task 2 moves the
# panel-picture control INTO that detail row, and a name that says only
# "details" would hide the picture from precisely the user who has to be
# told it is there. Both forms ship with their French entries in
# companion/i18n_fr/flights.py in the same commit.
_TOGGLE_SHOW_LABEL = "Show flight details and picture"
_TOGGLE_HIDE_LABEL = "Hide flight details and picture"

# The chevron itself: a decorative glyph inside an aria-hidden span, so
# the button's accessible name is the aria-label above and nothing else.
# Rendered server-side rather than through a CSS `content:` string (T10's
# own rule — a pseudo-element string is not server-rendered and cannot be
# translated) and rather than through layout.icon_html() (the sprite
# carries no chevron symbol, and companion/layout.py belongs to plan
# 22-08 in this same wave). It carries no letters, so it is language-
# neutral and needs no catalogue entry.
_TOGGLE_GLYPH = "▾"

# The two attribute names companion/static/flight-rows.js reads the
# swapped accessible name from — duplicated here, not imported (a page
# module has no import path to a static script), exactly like the
# data-view-panel-* attribute names above, and pinned against that
# file's own source by companion/test_view_pages.py.
_TOGGLE_SHOW_LABEL_ATTR = "data-show-label"
_TOGGLE_HIDE_LABEL_ATTR = "data-hide-label"

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
    return callsign or hex_value or i18n.t(NO_CALLSIGN_NOTE_TEXT)

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

# 22-09-PLAN.md Task 2 (X5): ONE HOP TO ACT. D-21's original link sent
# an unresolved row to `/health#server-data` — a list Health's own copy
# calls read-only, so naming the airline took two hops (Flights ->
# Health -> Airlines). The link now goes straight to the Airlines
# resolve view for THIS row's prefix.
#
# The route and query-parameter names are duplicated, not imported —
# companion/pages/__init__.py's only documented boundary forbids one
# page module importing another — exactly as the retired
# UNRESOLVED_LINK_HREF duplicated Health's own anchor id, and pinned the
# same way: companion/test_view_pages.py's cross-module guard asserts
# this template is built from the real airlines_page.AIRLINES_ROUTE and
# airlines_page.RESOLVE_QUERY_PARAM values, never a re-typed literal.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_TEXT = "Name this airline"
# quick task 260902-w4t (UIR-05): the anchor's own class, so it renders
# visibly separated from the airline text it follows instead of reading
# as one glued run - `text-label` for the existing quiet-link treatment,
# plus a dedicated spacing hook styled in style.css. (22-09-PLAN.md
# Task 2 keeps the class and its rule verbatim; only the anchor's
# destination and text change, so the spacing fix is not re-derived.)
UNRESOLVED_LINK_CLASS = "text-label cell-unresolved-link"

# 22-09-PLAN.md Task 2 (X5, 22-UI-SPEC.md §1): the day-separator row's
# two relative labels. The absolute form is NOT a constant and NOT a
# direct date-formatting call — see day_label() below.
_DAY_TODAY_LABEL = "Today"
_DAY_YESTERDAY_LABEL = "Yesterday"

# 22-09-PLAN.md Task 2 (X5): the panel-picture control's VISIBLE label.
# The control used to be a 16px icon-only eye in the summary row — the
# smallest control on the page, with no name beside it, and the only
# route to the picture. It is now a labelled text control living inside
# the expanded detail row, beside the hex/timestamp/copy siblings the
# picture belongs with. VIEW_PANEL_LABEL survives as its `title`.
VIEW_PICTURE_LABEL = "View picture"

# 22-09-PLAN.md Task 2 (X5): the phone card's artwork thumbnail. Both
# constants are the same values companion/pages/home_page.py's own
# recent-flight thumbnail already holds (D-17.2) — duplicated, not
# imported, under companion/pages/__init__.py's no-page-imports-a-page
# rule, the same way that module itself duplicates the route prefix from
# airlines_page/app.py. The alt template's French entry lives in
# companion/i18n_fr/home.py, which already owns this exact key.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
_THUMBNAIL_ALT_TEMPLATE = "%s illustration"

# quick task 260902-w4t (UIR-05): a missing AIRLINE used to fall back to
# `panel_render.ROUTE_FALLBACK_TEXT` ("Route unavailable") - a string
# that describes a different noun (the route, not the airline) and made
# the exact same phrase appear twice in one unresolved row (once in the
# Type+Airline cell, once in the Route cell). This constant gives the
# airline its own fallback text so the two columns stop sharing one
# string.
AIRLINE_FALLBACK_TEXT = "Airline unknown"
# Phase 21 polish: the Route cell's fallback, held as a local literal so
# the French catalogue (companion/i18n_fr/flights.py) can carry it and
# companion/test_i18n.py's scanner can see it — the renderer's own
# `panel_render.ROUTE_FALLBACK_TEXT` stays the on-panel English string;
# the two are kept equal below by construction so the wording never
# drifts between the panel and the companion.
ROUTE_FALLBACK_TEXT = "Route unavailable"
assert ROUTE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT

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

    Polish fix 5 (D-05): the resolved label is translated at this
    display site via i18n.t() — companion/i18n_fr/registry.py supplies
    the French entries; the raw id (and the untranslated fallback for
    an unrecognised id, which is data, not a registry label) are never
    touched.
    """
    if raw and raw in device_config.RUNWAY_IDS:
        return i18n.t(device_config.runway_label(raw))
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

    20-10-PLAN.md Task 3 (D-07): the day/month prefix is built here
    rather than through `layout.local_clock_text()` (called below with
    `now_parsed=None` for the clock portion only, exactly as before —
    that function's own day/month branch never runs without a `now`),
    so this function selects `layout._MONTH_ABBR`/`_MONTH_ABBR_FR`
    itself from `prefs.current_lang()`, the identical membership test
    `local_clock_text()` applies internally — never a second,
    independently-derived language rule.
    """
    parsed = layout.parse_iso(iso)
    if parsed is None:
        return i18n.t(LIGHTBOX_CAPTION_TEMPLATE) % iso
    local = parsed.astimezone(layout.LOCAL_TZ) if parsed.tzinfo else parsed
    month_abbr = layout._MONTH_ABBR_FR if prefs.current_lang() == "fr" else layout._MONTH_ABBR
    when = "%d %s %s" % (
        local.day, month_abbr[local.month - 1], layout.local_clock_text(parsed, None))
    return i18n.t(LIGHTBOX_CAPTION_TEMPLATE) % when


def _view_panel_button_html(name, iso):
    """A D-20 "View panel near this time" trigger button - one per
    History row that has a nearest render.

    22-09-PLAN.md Task 2 (X5): this used to be a 16px icon-only eye in
    the summary row — the smallest control on the page, with no name
    beside it, and the ONLY route to the panel picture. It is now a
    LABELLED text control ("View picture" / "Voir l'image") living
    inside the expanded detail row, where the hex, the timestamp and the
    copy buttons the picture belongs with already are; moving it there
    is what leaves the summary row's scan path a single chevron. It
    reuses `.calendar-disconnect-btn`'s small-grey-secondary treatment
    (30px, 12px text, the existing 6%/12% wash and 20% hairline) — that
    component's SECOND consumer, which `references/control-density.md`
    names explicitly as the pattern to reuse for a small, deliberately
    de-emphasised secondary action. No `.btn` family is started, and its
    30px height is the base button register's existing accepted trade,
    not a new one.

    The visible label IS the accessible name now, so the `aria-label`
    that used to duplicate `VIEW_PANEL_LABEL` is dropped rather than
    left to contradict the visible text (WCAG 2.5.3 label-in-name);
    `VIEW_PANEL_LABEL` survives as the `title`, the longer explanation a
    pointer user gets on hover.

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
    return (
        '<button type="button" class="calendar-disconnect-btn" %s="%s" %s="%s" '
        'title="%s">%s</button>'
    ) % (
        _VIEW_PANEL_SRC_ATTR, src,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(caption),
        escape_html(i18n.t(VIEW_PANEL_LABEL)),
        escape_html(i18n.t(VIEW_PICTURE_LABEL)),
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
        '<button type="button" %s>%s</button>'
        "</dialog>"
    ) % (LIGHTBOX_DIALOG_ID, escape_html(i18n.t(LIGHTBOX_ARIA_LABEL)),
         escape_html(i18n.t(LIGHTBOX_NOTE)), _VIEW_PANEL_CLOSE_ATTR, escape_html(i18n.t("Close")))


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
    # 20-10-PLAN.md Task 3 (D-05): kept in ENGLISH here, deliberately —
    # _type_airline_cell() and _history_cards_html() both compare this
    # value against the module's own AIRLINE_FALLBACK_TEXT constant to
    # decide whether to append the unresolved-airline link, and i18n.t()
    # is applied at THEIR render sites instead, so that membership test
    # never has to compare a translated string against an untranslated
    # constant under a French request.
    airline_label = (
        panel_render.display_airline_name(airline) if airline
        else AIRLINE_FALLBACK_TEXT)

    origin = row.get("origin")
    destination = row.get("destination")
    route_label = (
        "%s → %s" % (origin, destination) if origin and destination
        else i18n.t(ROUTE_FALLBACK_TEXT))

    corroboration_status, corroboration_label = _CORROBORATION_LABELS.get(
        row.get("corroborated"), _DEFAULT_CORROBORATION)
    corroboration_label = i18n.t(corroboration_label)

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
        # 22-09-PLAN.md Task 2 (X5): the RAW stored airline string, kept
        # beside the display label because the phone card's artwork
        # thumbnail keys on it — `illustrations.normalise_airline_key()`
        # resolves on the raw value, never on the aliased display name
        # (server/plane/render.py's own _flight_line2_text() docstring is
        # explicit that display_airline_name() "never reaches
        # illustration selection"), exactly as home_page.py's own
        # recent-flight thumbnail does.
        "airline_raw": row.get("airline") or "",
        "route_label": route_label,
        "confirmed_state": i18n.t(_confirmed_state_label(row.get("confirmed_state"))),
        "corroboration_status": corroboration_status,
        "corroboration_label": corroboration_label,
        # quick task 260902-w4t (UIR-04): the long form for the "None"
        # (single-source) state, rendered as status_dot()'s optional
        # tooltip - "" (no tooltip) for True/False, which need none.
        "corroboration_title": i18n.t(_CORROBORATION_TITLES.get(row.get("corroborated"), "")),
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
    the transient success text into that label span's `textContent`
    only — never into the button element itself, which would destroy
    the SVG icon and have no way to restore it. This keeps the no-HTML-
    writing-sink rule intact: only `textContent` on a leaf `<span>`.

    D-06 (20-11-PLAN.md Task 3): the button carries a new attribute
    naming the translated success text `companion/static/copy-button.js`
    reads at click time instead of a hardcoded English literal — the
    data-* label shape `freshness.js` uses (its former `data-pause-text`
    pair was retired in 21-02).
    """
    return (
        '<button type="button" class="copy-btn" data-copy-value="%s" '
        'aria-label="%s" data-copied-text="%s">'
        '<span class="copy-btn__icon" aria-hidden="true">%s</span>'
        '<span class="copy-btn__label"></span>'
        '</button>'
        '<span class="visually-hidden" data-copy-feedback role="status" '
        'aria-live="polite"></span>'
    ) % (
        escape_html(value), escape_html(label), escape_html(i18n.t("Copied")),
        layout.icon_html("icon-copy"))


def resolve_prefix_for_callsign(callsign):
    """The 3-letter ICAO prefix `callsign` would be filed under in the
    unresolved-prefix registry, or None (never raising) for anything
    that cannot yield one.

    The normalisation itself is `manual_resolutions.normalise_prefix()` —
    the SAME function `airlines_page.unresolved_row_for_prefix()` applies
    at the resolve view's own boundary, so a prefix this function
    produces is exactly a prefix that view accepts. Only one gate is
    re-stated rather than imported: `server/plane/enrich.py`'s registry
    writer requires a callsign of shape `[A-Z]{3}[A-Z0-9]+` — three
    letters plus at least one more character — before it ever records a
    prefix, and its `_AIRLINE_PREFIX_SHAPE_RE` is private to that module.
    A bare three-character callsign therefore yields None here too, so
    this function can never offer a one-hop link to a prefix the
    registry could not contain in the first place.
    """
    if not isinstance(callsign, str):
        return None
    normalised = callsign.strip().upper()
    if len(normalised) < 4:
        return None
    return manual_resolutions.normalise_prefix(normalised[:3])


def _resolve_link_html(prefix):
    """The 22-09 one-hop link: from a flight whose airline could not be
    named straight to the Airlines resolve view for that flight's own
    prefix. Used by both the desktop Flight cell and the phone card,
    exactly where the retired two-hop `_unresolved_link_html()` was
    used, and carrying its identical UNRESOLVED_LINK_CLASS treatment
    (quick task 260902-w4t, UIR-05) so it still renders visibly
    separated from the airline text it follows.

    T-22-30: `prefix` reaches an href, so it is URL-quoted for the query
    string and then escaped for the attribute — both, at this single
    point of interpolation. The value is already
    `manual_resolutions.normalise_prefix()`-normalised (three upper-case
    letters, nothing else can reach here), so neither step can change
    it today; they are the standing guarantee, not a repair. The resolve
    view re-validates the prefix on arrival, unchanged.
    """
    href = RESOLVE_LINK_HREF_TEMPLATE % urllib.parse.quote(prefix, safe="")
    return '<a class="%s" href="%s">%s</a>' % (
        escape_html(UNRESOLVED_LINK_CLASS),
        escape_html(href), escape_html(i18n.t(RESOLVE_LINK_TEXT)))


def _row_resolve_link_html(row):
    """`_resolve_link_html()` for a formatted row whose airline could not
    be resolved, or "" — for a resolved airline, and for an unresolved
    one whose callsign yields no usable prefix (a row with no callsign
    at all cannot be named BY prefix, and offering a link that could
    only land on a validation failure would be worse than offering
    none). Both the desktop cell and the phone card call this, so the
    two representations can never disagree about whether the affordance
    is present.
    """
    if row["airline_label"] != AIRLINE_FALLBACK_TEXT:
        return ""
    prefix = resolve_prefix_for_callsign(row["callsign"])
    return _resolve_link_html(prefix) if prefix else ""


def paris_day(raw_ts):
    """The Europe/Paris calendar DATE a stored timestamp falls on, or
    None (never raising) for a falsy or unparseable value.

    `layout.LOCAL_TZ` is the same zone `layout.local_clock_text()` — the
    app's one visible-time formatter (D-05) — converts to, and a naive
    datetime is taken as UTC here for the identical reason that function
    does it: `history_db.utc_now_iso()`'s own output is what these
    timestamps are. No second timezone rule, and no direct
    date-formatting call anywhere in this module — this plan's own
    acceptance criterion greps this file for exactly that, so the token
    is deliberately not spelled out even in prose.
    """
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return None
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(layout.LOCAL_TZ).date()
    except (ValueError, OverflowError, OSError):
        return None


def day_label(day, today):
    """The day-separator's own label (22-UI-SPEC.md §1): "Today",
    "Yesterday", or an absolute date — translated, and in the label
    voice at its render site.

    The absolute form is composed from `layout.month_abbr()`, which is
    `local_clock_text()`'s OWN month table exposed for callers that
    build a "D Mon" label (its docstring says exactly that) — it is the
    same day and the same words that formatter's cross-day branch
    produces for this timestamp, never a second date path and never a
    direct date-formatting call. A second date path in this file is how
    the UTC leak this phase is fixing got in.

    `today` (the Europe/Paris date of the page's own reference instant)
    may be None, in which case every group falls to its absolute label
    rather than raising.
    """
    if today is not None:
        if day == today:
            return i18n.t(_DAY_TODAY_LABEL)
        if (today - day).days == 1:
            return i18n.t(_DAY_YESTERDAY_LABEL)
    return "%d %s" % (day.day, layout.month_abbr(day.month))


def _flight_cell_html(row):
    """The desktop Flight column's own cell builder (21-03-PLAN.md
    Task 1, D-15) — replaces the retired `_callsign_hex_cell()`/
    `_type_airline_cell()` pair now that the hex and the copy buttons
    have moved into the Task 2 detail row. `_merged_cell()`'s primary
    slot carries the callsign (mono); the secondary slot carries
    "{airline} · {aircraft type}" as ONE plain string (UI-SPEC §F's own
    "Air France · A320" example) — `_merged_cell()` still adds its own
    inline separator between the callsign and this string, so the
    rendered cell reads "AFR1234 · Air France · A320", matching the
    UI-SPEC markup block exactly. `_unresolved_link_html()` is appended
    immediately after, only when this row's airline could not be
    resolved (D-21, carried over verbatim from the retired
    `_type_airline_cell()` — the mobile card keeps its own identical
    copy of this same is_unresolved/airline_display logic).
    """
    is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
    airline_display = i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]
    secondary = "%s · %s" % (airline_display, row["aircraft_type_label"])
    html = _merged_cell(row["callsign"], secondary)
    resolve_link = _row_resolve_link_html(row)
    if resolve_link:
        html = html[:-len("</td>")] + resolve_link + "</td>"
    return html


def _filter_bar_html(total):
    """D-20's filter bar — a `<label>` + `<input type="search"
    data-filter-input>` (with `icon-search` inside, decorative), a live
    `<span data-filter-count>`, a `Clear` control, and a hidden-by-
    default `data-filter-empty` block. Entirely inert without JS —
    `companion/static/list-filter.js`'s own early-return guard means the
    full unfiltered table/card list underneath stays completely usable
    if the script never loads.

    D-06 (20-11-PLAN.md Task 3): `data-filter-count` also carries a
    `data-filter-count-template` attribute — the SAME translated
    template this function's own initial `count_text` is built from,
    with its two `%d` placeholders left unformatted — so
    `companion/static/list-filter.js` can re-render the live count on
    every keystroke without ever hardcoding the English words "of"/
    "shown" itself.
    """
    count_template = i18n.t("%d of %d shown")
    count_text = count_template % (total, total)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        '<input type="search" id="%s" data-filter-input>'
        "</div>"
        '<span class="filter-bar__count" data-filter-count '
        'data-filter-count-template="%s">%s</span>'
        '<button type="button" data-filter-clear>%s</button>'
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(i18n.t(_FILTER_LABEL_TEXT)),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_template),
        escape_html(count_text),
        escape_html(i18n.t("Clear")),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


# A-36/D-19 (retired function's own comment, kept for its fallback
# string's continuity): mirrors layout.concise_timestamp_html()'s own
# default fallback string exactly, so a caller can never tell the two
# functions apart by their empty-value behaviour. Still consumed by
# _when_cell_html() below (21-03-PLAN.md Task 1, D-15).
_CLOCK_CELL_FALLBACK = "no reading yet"


def _when_cell_html(raw_ts, now):
    """The desktop table's When column cell builder (21-03-PLAN.md
    Task 1, D-15) — replaces the retired `_clock_cell_html()`'s one call
    site. Two STACKED lines via `_merged_cell()` (never an inline
    suffix — Pitfall 4, do not reach for
    `layout.concise_timestamp_html()` here): a local clock primary line
    ("HH:MM", or "D Mon HH:MM" once the row is no longer from today —
    `layout.local_clock_text()`, Europe/Paris, the exact text
    `_clock_cell_html()` used to wrap in a `<span title="...">`) and a
    relative-age secondary line (`layout.relative_age_text()` over
    `layout.age_seconds()`). The retired function's own `title`
    attribute (the full ISO timestamp) is dropped, not relocated: D-15
    moves the full ISO into the Task 2 detail row's own "Full
    timestamp" `<dt>/<dd>` pair, so this cell no longer needs a
    title-attribute home for it.

    Degrades the way `_clock_cell_html()` used to: a falsy `raw_ts`
    renders the escaped fallback text as a bare primary line with no
    secondary; an unparseable `raw_ts` renders the raw value as the
    primary line, still with no secondary (a relative age is undefined
    for a value that never parsed). Never raises.

    22-09-PLAN.md Task 2 (X5): the `view_panel_html` parameter is gone
    with the icon-only eye it carried. The panel-picture control is a
    labelled control inside the detail row now (see
    `_flight_detail_row_html()`), so this cell is back to the two
    stacked lines D-15 specified and nothing else.
    """
    if not raw_ts:
        html = _merged_cell(i18n.t(_CLOCK_CELL_FALLBACK), "")
    else:
        parsed = layout.parse_iso(raw_ts)
        if parsed is None:
            html = _merged_cell(raw_ts, "")
        else:
            now_parsed = layout.parse_iso(now)
            clock_text = layout.local_clock_text(parsed, now_parsed)
            age = layout.age_seconds(raw_ts, now)
            secondary = layout.relative_age_text(age) if age is not None else ""
            html = _merged_cell(clock_text, secondary)
    return html


def full_local_time_text(raw_ts):
    """The VISIBLE form of a stored timestamp inside a detail row or a
    card disclosure (22-09-PLAN.md Task 2, D-05/C5): a day-qualified
    Europe/Paris local clock ("27 Aug 10:00"), never the raw ISO string
    and never monospace — mono stays reserved for identifiers
    (callsign, ICAO24 hex, the masked calendar URL), and the raw ISO now
    survives only behind the copy control that carries it as its
    `data-copy-value`.

    Built from `layout.local_clock_text()` itself, forced onto its own
    cross-day "D Mon HH:MM" branch by the same
    `layout._FULL_TIMESTAMP_SENTINEL_NOW` reference instant
    `layout.concise_timestamp_html()`'s own `title` uses — the one
    visible-time formatter, reached the one sanctioned way, not a second
    implementation. (Reaching for that private module attribute follows
    this file's own precedent in `lightbox_caption_text()` above, which
    already selects `layout._MONTH_ABBR`/`_MONTH_ABBR_FR` directly for
    exactly the same "never derive a second date rule" reason.)

    Degrades to the raw value, unchanged, when it cannot be parsed —
    never raises, never an empty cell.
    """
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return raw_ts
    return layout.local_clock_text(parsed, layout._FULL_TIMESTAMP_SENTINEL_NOW)


def _flight_detail_row_html(row, index):
    """The D-15/R-12 sibling detail `<tr>`, immediately following the
    summary row of the same `index` (the same index `_history_table_
    html()`'s row-toggle button names via `aria-controls`/`id`). Its
    content is the mobile card's own `<details>` set (`_history_cards_
    html()`, :952-978-ish), re-wrapped as a `<dl>` inside one
    `colspan="6"` cell: Hex + its copy button, Full timestamp (the raw
    ISO) + its copy button, Runway — each `<dt>`/`<dd>` pair OMITTED
    entirely when its value is absent, never a fabricated "—" (the
    UI-SPEC's own Empty/Error rule) — followed by a standalone
    "copy-name" button (the callsign's own copy button, no dt/dd pair:
    the callsign itself is already visible on the summary row's Flight
    cell, so only the copy affordance needs a home here, omitted
    entirely when the row has no callsign). `_copy_button_html()` is
    reused verbatim; every interpolated value keeps its `escape_html()`
    wrap, exactly as every other cell in this module already does.

    No `hidden` attribute and no inline style: the no-JS floor is a
    fully visible detail row (D-15, locked) — companion/static/
    flight-rows.js adds the collapsing class at load, never this
    function.
    """
    row_name = _row_copy_name(row["callsign"], row["hex"])
    parts = []
    if row["hex"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd class="mono">%s</dd>%s</div>'
            % (
                escape_html(i18n.t("Hex")), escape_html(row["hex"]),
                _copy_button_html(row["hex"], i18n.t(_COPY_HEX_LABEL) % row_name)))
    if row["raw_ts"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd class="time-value">%s</dd>%s</div>'
            % (
                escape_html(i18n.t("Full timestamp")),
                escape_html(full_local_time_text(row["raw_ts"])),
                _copy_button_html(row["raw_ts"], i18n.t(_COPY_TIMESTAMP_LABEL) % row_name)))
    if row["tracked_runway"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd>%s</dd></div>'
            % (escape_html(i18n.t("Runway")), escape_html(row["tracked_runway"])))
    copy_name_button = (
        _copy_button_html(row["callsign"], i18n.t(_COPY_CALLSIGN_LABEL) % row_name)
        if row["callsign"] else "")
    return (
        '<tr class="flight-detail-row" id="flight-detail-%d" data-row-detail>'
        '<td colspan="6"><dl class="flight-detail-row__grid">%s</dl>%s%s</td>'
        "</tr>"
    ) % (index, "".join(parts), copy_name_button, row.get("view_panel_html", ""))


def _day_separator_row_html(day, today):
    """One day-separator row (22-09-PLAN.md Task 2, X5): a real table
    row spanning the table as a `<th scope="colgroup">`, carrying the
    day's label in the label voice.

    Deliberately NOT sticky. Sticky day headers are D7/Phase 23, and
    T4 in this same phase removes the app's one broken `position:
    sticky` claim rather than adding a second one — so this function
    introduces no positioning of any kind, and its stylesheet rule
    declares none.
    """
    return (
        '<tr class="flight-day-row">'
        '<th scope="colgroup" colspan="6" class="text-label">%s</th>'
        "</tr>"
    ) % escape_html(day_label(day, today))


def _history_table_html(formatted_rows, now=None):
    if not formatted_rows:
        return layout.empty_state(i18n.t(_NO_FLIGHTS_HEADING), i18n.t(_NO_FLIGHTS_BODY))

    # 21-03-PLAN.md Task 1 (D-15): the sixth <th> is the visually-hidden
    # "Details" toggle-column header — it has no data column behind it,
    # so it is built directly here rather than through the _HEADERS/
    # i18n.t(h) loop, and it always reads "Détails" under a French
    # request because it goes through i18n.t() at this one render site,
    # never the bare English literal.
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _HEADERS)
    header_cells += '<th><span class="visually-hidden">%s</span></th>' % escape_html(
        i18n.t(_DETAILS_HEADER_TEXT))

    # 22-09-PLAN.md Task 2 (X5): thirty-six to fifty rows used to run
    # together with nothing marking where one day ended and the next
    # began. `today` is the page's own reference instant as a
    # Europe/Paris calendar date, so "Today"/"Yesterday" mean what a
    # reader standing in Paris means by them; a `now` that does not
    # parse leaves it None and every group falls to its absolute label.
    today = paris_day(now)
    current_day = None

    body_rows = []
    for index, row in enumerate(formatted_rows):
        # A separator before each new Paris day. A row whose timestamp
        # cannot be dated (paris_day() -> None) takes the existing
        # ungrouped path: no separator is emitted for it and the current
        # group is left open, so it never splits a real day in two
        # (T-22-31 — the grouping degrades, it does not raise).
        day = paris_day(row["raw_ts"])
        if day is not None and day != current_day:
            current_day = day
            body_rows.append(_day_separator_row_html(day, today))

        row_class = "row-alt" if index % 2 else "row"
        # D-15: five data cells plus the row-toggle cell. When/Flight
        # already return already-safe, fully-built <td>...</td> markup
        # (_when_cell_html()/_flight_cell_html()) - interpolated
        # directly, matching _merged_cell()'s own documented "do not
        # double-escape already-safe markup" discipline. D-20's
        # View-panel trigger is threaded into _when_cell_html() itself
        # now (it used to be appended inline here).
        cells = (
            _when_cell_html(row["raw_ts"], now),
            _flight_cell_html(row),
            "<td>%s</td>" % escape_html(row["route_label"]),
            "<td>%s</td>" % escape_html(row["confirmed_state"]),
            "<td>%s</td>" % layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"], visually_hide_label=True),
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
        # other attribute value this function builds. 21-03-PLAN.md
        # Task 2 also gives the runway a visible home in the sibling
        # detail row; this title attribute is unchanged.
        #
        # 21-03-PLAN.md Task 2 (D-15/R-12): the sixth cell is the
        # row-toggle button matching the visually-hidden "Details"
        # header Task 1 already added. data-row-toggle/aria-controls/
        # aria-expanded are companion/static/flight-rows.js's own
        # contract (a click flips aria-expanded and toggles the matching
        # flight-detail-{n} row's collapsed class). The no-JS floor
        # means the sibling detail row is ALREADY fully visible without
        # any script running, so this button is inert chrome in that
        # case, never a broken affordance.
        #
        # 22-09-PLAN.md Task 1 (X5): icon-only. The visible "More"/
        # "Plus" text is gone; the button's own accessible NAME carries
        # the meaning instead, escaped server-side through i18n.t() at
        # this one render site and handed to flight-rows.js as the two
        # data-*-label attribute values it only ever writes back into
        # aria-label, never builds itself. aria-expanded stays HERE, on
        # a real <button> — a <tr> is not focusable and cannot carry the
        # state (22-UI-SPEC.md §2's X5 contract, stated as a
        # prohibition).
        toggle_cell = (
            '<td><button type="button" class="row-toggle" data-row-toggle '
            'aria-expanded="false" aria-controls="flight-detail-%d" '
            'aria-label="%s" %s="%s" %s="%s">'
            '<span class="row-toggle__glyph" aria-hidden="true">%s</span>'
            "</button></td>"
        ) % (
            index,
            escape_html(i18n.t(_TOGGLE_SHOW_LABEL)),
            _TOGGLE_SHOW_LABEL_ATTR, escape_html(i18n.t(_TOGGLE_SHOW_LABEL)),
            _TOGGLE_HIDE_LABEL_ATTR, escape_html(i18n.t(_TOGGLE_HIDE_LABEL)),
            escape_html(_TOGGLE_GLYPH),
        )
        # 22-09-PLAN.md Task 1 (X5): data-flight-row is the hook
        # flight-rows.js's delegated whole-row click reads — a plain
        # marker attribute, never a class, so the alternating row/row-alt
        # class values stay this function's own business. The
        # pointer-cursor class that goes with it is added by the SCRIPT
        # at load, never here: a scripts-blocked page must never show a
        # pointer on a row that does nothing.
        body_rows.append(
            '<tr class="%s" data-flight-row data-filter-text="%s" '
            'data-filter-group="%d" title="%s">%s%s</tr>'
            % (row_class, _filter_text_attr(row), index,
               escape_html(row["tracked_runway"]), "".join(cells), toggle_cell))
        body_rows.append(_flight_detail_row_html(row, index))

    return (
        '<div class="data-table-wrap" tabindex="0" role="region" '
        'aria-label="%s">'
        '<table class="data-table data-table--flights">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (escape_html(i18n.t(SCROLLER_ARIA_LABEL)), header_cells, "".join(body_rows))


def _card_thumb_html(airline_raw, state_dir):
    """The phone card's artwork thumbnail (22-09-PLAN.md Task 2, X5), or
    "" when this row's airline resolves to no artwork file on disk.

    The same two-call seam `home_page._recent_flight_thumb_html()` and
    the Airlines gallery/gap cards already use:
    `illustrations.normalise_airline_key()` for the key (a pure string
    resolve on the RAW stored airline — the display alias never reaches
    illustration selection) and `illustrations.resolved_illustration_
    path()` for the "is there really a file" test. Never an
    unconditional `<img>`: a key with no file behind it would 404 and
    render as a broken-image icon, which is a worse defect than no
    thumbnail at all (home_page.py's own docstring records that finding).

    The served image is the Airlines gallery's own 450x132 frame; the
    fixed 56px-tall box and `object-fit: contain` are style.css's,
    where `img.history-card__thumb` joins the shared white-backing /
    hairline / radius rule as a fourth selector rather than restating a
    colour literal.
    """
    key = illustrations.normalise_airline_key(airline_raw)
    if not key or illustrations.resolved_illustration_path(key, state_dir) is None:
        return ""
    alt_text = i18n.t(_THUMBNAIL_ALT_TEMPLATE) % panel_render.display_airline_name(airline_raw)
    return (
        '<img class="history-card__thumb" loading="lazy" decoding="async" '
        'src="%s%s.png" alt="%s">'
    ) % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key), escape_html(alt_text))


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
            ) % (escape_html(row["hex"]), escape_html(i18n.t(NO_CALLSIGN_NOTE_TEXT)))
        else:
            primary_value_html = '<span class="cell-primary mono"></span>'
        primary = (
            '<div class="history-card__primary">'
            "%s"
            '<span class="history-card__time">%s</span>'
            "</div>"
        ) % (
            primary_value_html,
            layout.concise_timestamp_html(row["raw_ts"], now),
        )
        # 22-09-PLAN.md Task 2 (X5): "ORY → JFK Departing" used to run
        # together as two bare spans. The separator is the module's
        # EXISTING middle dot (CELL_SEPARATOR_TEXT in its own
        # CELL_SEPARATOR_CLASS span, the same pair _merged_cell() emits
        # on the desktop side) — reused, never a second separator
        # invented for this one line.
        secondary = (
            '<div class="history-card__secondary">'
            "<span>%s</span>"
            '<span class="%s">%s</span>'
            "<span>%s</span>"
            "</div>"
        ) % (
            escape_html(row["route_label"]),
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            escape_html(row["confirmed_state"]),
        )
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
        is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
        airline_display = i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]
        # 22-09-PLAN.md Task 2 (X5): the airline and the artwork moved
        # OUT of the disclosure and onto the card's own face — a phone
        # card that dropped both was showing less about the flight than
        # the desktop row for the same data. The one-hop resolve link
        # rides with the airline name, so the card and the desktop cell
        # carry the identical affordance exactly once each.
        airline_line = (
            '<div class="history-card__airline">%s'
            '<span class="history-card__airline-name">%s</span>%s'
            "</div>"
        ) % (
            row.get("thumb_html", ""),
            escape_html(airline_display),
            _row_resolve_link_html(row),
        )
        # A-37/D-20: the mobile disclosure's three copy buttons name
        # their own row too, via the same _row_copy_name() fallback
        # order the desktop cell uses.
        row_name = _row_copy_name(row["callsign"], row["hex"])
        details = (
            '<details class="history-card__details">'
            "<summary>%s</summary>"
            "<dl>"
            '<dt>%s</dt><dd class="mono">%s%s</dd>'
            "<dt>%s</dt><dd>%s</dd>"
            "<dt>%s</dt><dd>%s</dd>"
            "<dt>%s</dt><dd>%s</dd>"
            '<dt>%s</dt><dd class="mono">%s%s</dd>'
            '<dt>%s</dt><dd class="time-value">%s%s</dd>'
            "</dl>%s"
            "</details>"
        ) % (
            escape_html(i18n.t("More details")),
            escape_html(i18n.t("Callsign")),
            escape_html(row["callsign"]),
            _copy_button_html(row["callsign"], i18n.t(_COPY_CALLSIGN_LABEL) % row_name),
            # The airline left this pair with the artwork (see
            # airline_line above); the aircraft type keeps it alone.
            escape_html(i18n.t("Aircraft")),
            escape_html(row["aircraft_type_label"]),
            escape_html(i18n.t("Corroboration")),
            layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"]),
            escape_html(i18n.t("Runway")),
            escape_html(row["tracked_runway"]),
            escape_html(i18n.t("Hex")),
            escape_html(row["hex"]),
            _copy_button_html(row["hex"], i18n.t(_COPY_HEX_LABEL) % row_name),
            # D-05/C5, 22-09-PLAN.md Task 2: the VISIBLE timestamp is the
            # Paris local clock in the time-value role; the raw ISO
            # survives only as the copy control's own data-copy-value.
            escape_html(i18n.t("Full timestamp")),
            escape_html(full_local_time_text(row["raw_ts"])),
            _copy_button_html(row["raw_ts"], i18n.t(_COPY_TIMESTAMP_LABEL) % row_name),
            # The picture control lives inside the disclosure here for
            # the same reason it lives inside the desktop detail row:
            # beside the hex, the timestamp and their copy buttons.
            row.get("view_panel_html", ""),
        )
        items.append(
            '<li class="history-card" data-filter-text="%s" '
            'data-filter-group="%d">%s%s%s%s</li>'
            % (_filter_text_attr(row), index, primary, secondary, airline_line, details))
    return '<ul class="history-cards">%s</ul>' % "".join(items)


def render(ctx):
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()
    rows = _safe_query(state_dir, history_rows)

    # D-10: the display-window label folded into the header's purpose
    # sentence, using the real HISTORY_ROW_LIMIT constant rather than a
    # hardcoded "50".
    header = layout.page_header(
        i18n.t(PAGE_TITLE), purpose=i18n.t(PAGE_PURPOSE_TEMPLATE) % HISTORY_ROW_LIMIT)

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
        body = '<p class="text-body">%s</p>' % escape_html(i18n.t(_HISTORY_UNAVAILABLE_TEXT))
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
            # 22-09-PLAN.md Task 2 (X5): the phone card's artwork
            # thumbnail, resolved here for the same reason the
            # View-panel match is — once per row, onto the one
            # formatted_rows list both representations share, never a
            # second lookup that could disagree with the first. The
            # desktop table does not render it (data-density.md's
            # measured width budget has no room), so this is the phone
            # card's own key alone.
            row["thumb_html"] = _card_thumb_html(row["airline_raw"], state_dir)
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
