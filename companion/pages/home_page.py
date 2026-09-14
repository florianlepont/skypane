"""companion/pages/home_page.py — the Home page (phase 18, companion audit
/ UX refactor; rebuilt by 20-06-PLAN.md, D-16..D-21; rebuilt again by
21-04-PLAN.md Task 3, D-04/D-05/R-06).

The page a household member lands on after signing in, answering three
questions without any technical background: is the frame alive, what is
it showing, and what has it shown recently. D-16 (20-CONTEXT.md) removed
the "Quick actions" card entirely — the Screen on/off and Quiet hours
instant switches now live in the shared Frame strip (the strip helper
in companion/layout.py), rendered once by this page and once by
Display; the Refresh-now button lives on Device's own Manual
refresh section. Home now reads: the Frame strip, three status tiles
(Frame/Battery/Flight data) in a `.dashboard-grid.home-status-grid`,
then a two-column row holding the current picture beside the recent
flights — with an artwork thumbnail per row when — and only when — a
real illustration file resolves for that row's airline (D-17.2; a
truthy normalised key alone is not enough, since an airline the app
recognises by name but with no artwork file on disk would otherwise
404 as a broken-image icon).

Like every page module this one imports nothing from a sibling page
module (companion/pages/__init__.py's boundary). The status verdicts it
renders come straight from `ctx["health_state"]` (already computed once
per request by companion/app.py) and the recent-flight rows from one
`history_db` read of its own — the SAME read now feeds both the hero
row's flight one-liner and the recent-flights list, so the hero's own
"current flight" costs no second query (D-20).

Everything dynamic passes through `layout.escape_html()`.
"""
import html
import re
from datetime import datetime, time, timedelta

import companion.battery as battery
import companion.draw as draw
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from companion.layout import escape_html
from server import device_config, history_db
from server.plane import illustrations
# 22-07-PLAN.md Task 1 (X4): the SAME presentation-only airline alias
# Flights already applies via `companion/pages/history_page.py`'s own
# `panel_render.display_airline_name()` call — imported the exact same
# way (`from server.plane import render as panel_render`), never
# forked into a second copy. `illustrations.normalise_airline_key()`
# below still resolves on the RAW stored airline string — render.py's
# own `_flight_line2_text()` docstring is explicit that the display
# alias "never reaches illustration selection" — only the user-visible
# text (the flight one-liner, the thumbnail's alt text) is aliased.
from server.plane import render as panel_render

PAGE_TITLE = "Home"
PAGE_PURPOSE = "Your frame at a glance."

RECENT_FLIGHTS_LIMIT = 5
RECENT_FLIGHTS_HEADING = "Recent flights"
RECENT_FLIGHTS_LINK_TEXT = "See all flights"
NO_FLIGHTS_HEADING = "No flights yet."
NO_FLIGHTS_BODY = (
    "The first aircraft the frame detects on the watched runway will "
    "appear here.")
FLIGHTS_ROUTE = "/flights"

# --- the day band (CFG-42, 24-06-PLAN.md Task 2) -----------------------
#
# Home tells you what the frame will do NEXT. The band is the only thing
# on this page that says what it has been DOING, and it is a whole day of
# it at a glance: has it been waking normally, and when was it asleep.
#
# The read is bounded, and the bound is a correctness constraint rather
# than a performance one. `recent_device_health()` returns the newest N
# rows, so a limit smaller than a day's check-ins would silently hand the
# band the last few HOURS and let it caption them as the day. 3000 is a
# 60-second cadence's 1 440 rows with room for the previous day's tail
# (this reads the newest rows, not a day's worth) and better than double
# the headroom besides; `_day_band_html()` below also detects the
# truncation case and stops the caption claiming a total.
DAY_BAND_ROW_LIMIT = 3000

DAY_BAND_HEADING = "Today"
# The canvas's accessible name. The band IS the only statement of this
# data — the caption beneath it says the count, not the shape — so it is
# a named group rather than aria-hidden (draw.percent_canvas()'s own
# two-way contract).
DAY_BAND_LABEL = "The frame's check-ins through the day, midnight to midnight"
DAY_BAND_HOUR_LABELS = ("00:00", "12:00", "24:00")
DAY_BAND_EMPTY_TEXT = "No check-ins recorded on %s."
DAY_BAND_ONE_TEXT = "1 check-in on %s."
DAY_BAND_COUNT_TEXT = "%s check-ins on %s."
# The honest half of T-24-06-B. The count above is printed as TEXT, which
# is fine and stays true; this sentence is what stops the reader trying
# to COUNT the marks and concluding the band lost some. It is appended
# only when draw.day_band() actually reported a collapse.
DAY_BAND_COLLAPSED_TEXT = (
    "Some marks are merged — check-ins closer together than the band can "
    "separate are drawn as one.")
DAY_BAND_QUIET_TEXT = "Shaded: quiet hours, %s to %s."

# D-17.2: the recent-flights thumbnail. Literal here, not imported from
# companion/pages/airlines_page.py — companion/pages/__init__.py forbids
# one page module importing another, and this is the exact string
# airlines_page.ILLUSTRATION_ROUTE_PREFIX/app.py's
# ILLUSTRATION_IMAGE_ROUTE_PREFIX already both hold.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
THUMBNAIL_ALT_TEMPLATE = "%s illustration"

RENDERED_CAPTION_TEMPLATE = "Rendered %s"
NO_PANEL_HEADING = "Nothing rendered yet."
NO_PANEL_BODY = (
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = "The picture currently on the frame"
GALLERY_ROUTE_PREFIX = "/gallery/"

DIRECTION_DEPARTING_TEXT = "Departing"
DIRECTION_ARRIVING_TEXT = "Arriving"

# D-16 (20-CONTEXT.md): the "Quick actions" card — the screen switch, the
# quiet-hours switch and the Refresh-now button — is gone from Home.
# D-01 (21-CONTEXT.md, 21-04-PLAN.md Task 1/3): the screen/quiet-hours
# switches, and the next-update headline that used to live here, now
# render once, in the shared Frame strip helper (see render() below,
# called with `return_to=layout.HOME_ROUTE`) —
# Refresh-now lives on Device's own Manual refresh section. The
# underlying HTTP toggle routes and their flash keys are untouched by
# either move, and POLL_ROUTE's own handler is untouched too.
# `QUICK_STATE_FIELD`/`QUICK_STATE_ON`/`QUICK_STATE_OFF` and (as of
# 21-04-PLAN.md Task 1) `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE`
# all live in companion/layout.py now — a page module may never import
# another page module, and both Home and Display need them.

STATUS_HEADING = "Status"
# 22-07-PLAN.md Task 1 (X4): renamed away from "Frame" — that name is
# now exclusively the shared Frame strip's own <h2> heading
# (companion/layout.py's FRAME_STRIP_HEADING), rendered directly above
# this tile on the same page. Two elements named "Frame" on one page
# was the collision X4 found; the strip's heading is layout.py's own
# shared component (owned by a sibling plan this wave) and is never
# renamed here — only this tile's caption moves.
FRAME_ROW_LABEL = "Check-ins"
BATTERY_ROW_LABEL = "Battery"
DATA_ROW_LABEL = "Flight data"
HEALTH_LINK_TEXT = "See details on Health"

# 22-07-PLAN.md Task 1 (D-03/CFG-26, X2): FRAME_STATE_TEXT's "ok"/
# "warn"/"error" values stay byte-identical to health_page.
# DEVICE_STATE_TEXT's own three values (20-RESEARCH.md Pitfall 3 —
# see companion/i18n_fr/home.py's own comment for why the two dicts
# must never be edited to differ). "off" is NEW here, widened for the
# same reason 22-04-PLAN.md Task 3 widened DEVICE_STATE_TEXT: a held
# (quiet-hours) frame is a genuine fourth state, reusing the SAME
# neutral wording health_page.py already ships — never re-typed
# independently, and never rendered through "warn"/"error".
FRAME_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
    "off": "Asleep for quiet hours",
}
# 22-07-PLAN.md Task 1 (D-03/CFG-26): the ONE mapping from frame_
# state's own three real states to this tile's own vocabulary —
# byte-identical in shape to health_page._FRAME_STATE_TO_DEVICE_STATE
# (a page module may never import another page module, so this is a
# second, independently-typed copy of the SAME mapping, not a forked
# decision: both route STATE_HELD to the neutral "off", never "warn"/
# "error"). STATE_UNKNOWN is deliberately absent — _status_tiles_html()
# below never looks this dict up for that state; it falls back to the
# pre-existing health-state-derived value instead, the one case
# frame_state.py itself cannot resolve (X2's own strip renders no
# update cell at all for the identical case, so there is nothing for
# this tile to disagree with when it takes its own fallback branch).
_FRAME_STATE_TO_TILE_STATE = {
    frame_state.STATE_DUE: "ok",
    frame_state.STATE_HELD: "off",
    frame_state.STATE_LATE: "warn",
}
DATA_STATE_TEXT = {
    "ok": "Up to date",
    "warn": "A little stale",
    "error": "Stale — the server may be down",
    # 22-07-PLAN.md Task 1 (B2): byte-identical to health_page.
    # PIPELINE_STATE_TEXT["off"] (22-03-PLAN.md) — a pipeline that has
    # genuinely never run is the SAME neutral fact on both pages, never
    # Home's own "A little stale" wording (which would misreport a
    # frame that has simply never seen a flight as one that is
    # falling behind).
    "off": "No detection yet",
}
BATTERY_STATE_TEXT = {
    "ok": "Healthy",
    "warn": "Dropping quickly",
    "error": "Dropping quickly",
}
NO_READING_TEXT = "No reading yet"

_TAG_RE = re.compile(r"<[^>]+>")
# Polish fix 2: health_page.py's pipeline_html fragment is TWO OR THREE
# stacked <p>...</p> blocks (a verdict paragraph, a timestamp paragraph,
# and — for the Flight-data row specifically — a third "Last aircraft
# detected" paragraph); device_detail_html is a single bare <span>, no
# <p> wrapper at all. _BLOCK_RE finds each <p>...</p> block's own inner
# markup so _plain_text_from_markup() below can join separate sentences
# with " · " instead of running them together as one undifferentiated
# space-joined string ("Has not run for a long time 10 Sep 23:58 (1d
# ago) Last aircraft detected: 10 Sep 23:46 (1d ago)" — the exact
# unreadable, un-separated fragment this fix closes).
_BLOCK_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL)


def _plain_text_from_markup(fragment):
    """Strip tags and reverse HTML-entity escaping from a pre-built,
    already-escaped markup fragment — health_page.compute_health_
    state()'s own detail-only health-state fields, raw-markup-
    producing in the same way layout.concise_timestamp_html() is
    documented to be ("callers interpolate the return value verbatim —
    never re-escape it").

    The shared status-row primitive's own `detail` parameter escapes
    whatever it is given (T-20-03, 20-03-PLAN.md) — passing either
    fragment straight through would have that escaping turn the
    fragment's own "<span…>"/"<p…>" tags into visible tag text on the
    page, a real rendering defect, not a cosmetic one. This reconciles
    this plan's own instruction to read the verdict-free health-state
    field with that escaping contract: strip the wrapping tags (each
    becomes a single space within its own block), then reverse the
    HTML-entity escaping the fragment's own builder already applied, so
    the row primitive's own escaping re-encodes the text exactly once,
    not twice.

    When `fragment` carries two or more top-level `<p>...</p>` blocks
    (health_page.py's `pipeline_html`, whose verdict/timestamp/last-
    detection paragraphs are three separate sentences), each block's own
    text is joined with " · " so the Flight-data row's detail reads as
    three distinct clauses rather than one run-together sentence with no
    punctuation between them (Polish fix 2). A fragment with no `<p>`
    blocks at all (health_page.py's `device_detail_html`, a bare
    `<span>` with no verdict of its own) falls back to the original
    single-block behaviour unchanged.
    """
    if not fragment:
        return ""
    blocks = _BLOCK_RE.findall(fragment)
    if not blocks:
        spaced = _TAG_RE.sub(" ", fragment)
        return " ".join(html.unescape(spaced).split())
    parts = []
    for block in blocks:
        spaced = _TAG_RE.sub(" ", block)
        text = " ".join(html.unescape(spaced).split())
        if text:
            parts.append(text)
    return " · ".join(parts)


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except Exception:
        return None


def _recent_flights(conn):
    return history_db.recent_runway_events(conn, limit=RECENT_FLIGHTS_LIMIT)


def _latest_battery(conn):
    return history_db.latest_device_health(conn)


def _direction_text(raw):
    if raw == "departing":
        return DIRECTION_DEPARTING_TEXT
    if raw == "arriving":
        return DIRECTION_ARRIVING_TEXT
    return ""


def _route_text(row):
    origin = row.get("origin") or ""
    destination = row.get("destination") or ""
    if origin and destination:
        return "%s → %s" % (origin, destination)
    return ""


def _flight_secondary_text(row):
    """"<airline> · <route> · <direction>", skipping any empty part —
    the shared join-and-skip-empty convention both the hero's flight
    one-liner and the recent-flights list compose (20-UI-SPEC.md
    Section Anatomy B). `direction` is translated at this call site;
    `airline`/`route` are data (an ADS-B/adsbdb-sourced airline name
    and ICAO airport codes) and are never translated (D-05).
    """
    # 22-07-PLAN.md Task 1 (X4): resolved through the SAME presentation-
    # only alias Flights applies (panel_render.display_airline_name()),
    # so a row whose stored airline is an alias ("CCM Airlines") reads
    # the SAME display name ("Air Corsica") on both pages — never the
    # raw upstream string this call site used to read directly.
    airline = panel_render.display_airline_name(row.get("airline")) or ""
    route = _route_text(row)
    direction_raw = _direction_text(row.get("confirmed_state"))
    direction = i18n.t(direction_raw) if direction_raw else ""
    return " · ".join(part for part in (airline, route, direction) if part)


def _gallery_name_to_iso(name):
    """Mirror of history_page's filename convention: the gallery saves
    `<iso with ':' -> '-'>.png`. Returns the ISO string or None."""
    if not isinstance(name, str) or not name.endswith(".png"):
        return None
    stem = name[:-len(".png")]
    if len(stem) < 19 or stem[10] != "T":
        return None
    date_part, time_part = stem[:10], stem[11:]
    time_part = time_part.replace("-", ":", 2)
    if len(time_part) > 8:
        # "+00-00" offset suffix -> "+00:00"
        time_part = time_part[:8] + time_part[8:].replace("-", ":")
    candidate = "%sT%s" % (date_part, time_part)
    return candidate if layout.parse_iso(candidate) is not None else None


def _tile_content_html(verdict, detail, detail_class=None):
    """The Emphasis-verdict-plus-Label-detail composition every one of
    the three tiles below shares — a genuinely new pairing every time
    (never the same sentence twice, 20-RESEARCH.md Pitfall 3's
    confirmed root cause), so this one helper is the single write site
    for it rather than three near-identical inline literals. `detail`
    is omitted ENTIRELY (no placeholder) when falsy, matching every
    other "omit rather than fabricate" contract in this module.

    `detail_class` (22-07-PLAN.md Task 1, C5) is an optional extra
    class wrapping the escaped `detail` text in its own inner `<span>`
    — the Frame tile's own next-wake clock adopts `.time-value` here,
    the ONE role 22-04-PLAN.md defined for a clock/countdown value
    everywhere else on the site, without turning this shared helper's
    `detail` parameter into a second raw-markup injection point: the
    text itself is still escaped exactly once, only the wrapping
    changes. `None` (the default) is byte-identical to this function's
    behaviour before this parameter existed.
    """
    verdict_html = '<p class="text-body widget-verdict">%s</p>' % escape_html(verdict)
    if not detail:
        return verdict_html
    detail_text = escape_html(detail)
    if detail_class:
        detail_text = '<span class="%s">%s</span>' % (detail_class, detail_text)
    return verdict_html + '<p class="text-label widget-detail">%s</p>' % detail_text


# 24-04-PLAN.md Task 3 (CFG-40): the SMALL ring's box side, in CSS
# pixels. The LARGE one lives in health_page.py, because a shared
# "sizes" table would be one rename away from reading as two named
# variants of one drawing — and a variant name is how two drawings hide
# inside one function. What is shared is the EMITTER
# (draw.ring_gauge()), and it is shared for real: a change inside it
# moves both pages, which is what CFG-40 actually asks for.
#
# 36 is half health_page.BATTERY_RING_SIZE, and it has to stay under the
# height of the two text lines it sits beside (a 24px verdict, a 4px
# gap and a 19.6px detail = 47.6px measured at the 360px floor) —
# `stat_tile()`'s box is shared by three tiles, and a taller Battery
# tile would make the row ragged.
BATTERY_RING_SIZE = 36


def _battery_tile_content_html(verdict, detail, ring_html):
    """`_tile_content_html()`'s output with the battery ring beside it.

    With NO ring this returns `_tile_content_html()`'s own markup
    UNWRAPPED, so a device with no reading renders this tile
    byte-identically to what it rendered before the ring existed. The
    "omit rather than fabricate" contract this module already follows
    for a missing `detail`, applied one level up.

    The ring sits BESIDE the text rather than above it, and that is a
    height decision rather than a taste one: `stat_tile()`'s box is
    shared by three tiles in one row, and stacking the ring would push
    this tile taller than its two neighbours.
    """
    content_html = _tile_content_html(verdict, detail)
    if not ring_html:
        return content_html
    return (
        '<div class="stat-tile__gauge">%s'
        '<div class="stat-tile__gauge-text">%s</div></div>'
    ) % (ring_html, content_html)


def _status_tiles_html(ctx):
    """D-04/R-06 (21-CONTEXT.md, 21-04-PLAN.md Task 3): restores the
    phase-19 three-tile LAYOUT (`git show 614d41e~1:companion/pages/
    home_page.py` lines 166-218 — a `.dashboard-grid.home-status-grid`
    of three `stat_tile()` calls, Frame/Battery/Flight data,
    plus the "See details on Health" link below the grid) while
    keeping the CURRENT, bug-fixed content derivation this module's
    own now-deleted status-card builder used: each tile's verdict
    comes from THIS module's own FRAME_STATE_TEXT/BATTERY_STATE_TEXT/
    DATA_STATE_TEXT dicts, and each detail is the health state's own
    verdict-free field, reduced to plain text by
    `_plain_text_from_markup()` above where applicable — NEVER the
    health state's own combined device-summary field, which carries
    the Frame verdict a second time (the phase-19 body's own bug this
    rebuild does not resurrect). The
    frame verdict therefore appears exactly once on the whole page.

    22-07-PLAN.md Task 1 (D-03/CFG-26, X2/B2): the Frame tile no longer
    reads `ctx["health_state"]["device_state"]`/`"device_detail_html"`
    at all when a next-wake result is resolvable — both are health_
    page.py's OWN device-tile shape (a raw last-check-in timestamp),
    not the shared next-wake clock the strip renders. Instead this
    function calls `wake.next_wake_status()`/`frame_state.resolve_
    state()` fresh, against the SAME `ctx["last_checkin_ts"]`/
    `ctx["device_config"]`/`ctx["now"]` render() already used to build
    the strip above it — the strip and this tile can never disagree,
    because neither computes anything the other does not. The
    pre-existing health-state-derived value is kept ONLY as the
    fallback for `frame_state.STATE_UNKNOWN` (no check-in recorded at
    all) — the one case frame_state.py itself cannot resolve, and the
    one case the strip itself renders no update cell for, so there is
    nothing here for this tile's own fallback to disagree with.

    The Flight-data tile reads `pipeline_detail_html` (health_page.
    compute_health_state()'s verdict-free sibling of `pipeline_html`,
    22-03-PLAN.md Task 1) instead of the whole verdict-carrying
    `pipeline_html` fragment — Home renders its OWN verdict above it,
    never Health's second copy of the same judgement (B2).
    """
    health = ctx.get("health_state") or {}
    pipeline_state = health.get("pipeline_state") or "warn"
    battery_state = health.get("battery_state") or "warn"

    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.get("last_checkin_ts"), ctx.get("device_config"))
    resolved_frame_state = frame_state.resolve_state(
        next_wake_iso, effective_interval_s, hold_reason, ctx.get("now"))
    if resolved_frame_state == frame_state.STATE_UNKNOWN:
        device_state = health.get("device_state") or "warn"
        frame_detail = _plain_text_from_markup(health.get("device_detail_html"))
        frame_detail_class = None
    else:
        device_state = _FRAME_STATE_TO_TILE_STATE[resolved_frame_state]
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        frame_detail = layout.local_clock_text(
            next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))
        frame_detail_class = "time-value"
    frame_verdict = i18n.t(FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
    frame_html = _tile_content_html(frame_verdict, frame_detail, detail_class=frame_detail_class)

    reading = _safe_query(ctx.get("state_dir"), _latest_battery)
    battery_ring_html = ""
    if reading and reading.get("battery_mv"):
        pct = battery.battery_percent(reading["battery_mv"])
        pct_text = ("≈ %d%%" % pct) if pct is not None else ""
        mv_text = "%s mV" % reading["battery_mv"]
        battery_verdict = i18n.t(BATTERY_STATE_TEXT.get(battery_state, BATTERY_STATE_TEXT["warn"]))
        battery_detail = "%s · %s" % (pct_text, mv_text) if pct_text else mv_text
        if pct is not None:
            # 24-04-PLAN.md Task 3 (CFG-40): the ring draws THE NUMBER
            # PRINTED BESIDE IT — `pct` itself, over 100 — not a second,
            # finer-grained estimate off the same millivolt value. One
            # call into companion/battery.py, two renderings of its
            # result, so the picture and the number cannot round to
            # different stories. The colour is `battery_state`, the
            # verdict this tile has ALREADY chosen its own border from;
            # never a second judgement about the same reading.
            battery_ring_html = draw.ring_gauge(
                pct / 100.0, BATTERY_RING_SIZE, draw.status_class(battery_state))
    else:
        battery_verdict = i18n.t(NO_READING_TEXT)
        battery_detail = ""
    battery_html = _battery_tile_content_html(
        battery_verdict, battery_detail, battery_ring_html)

    data_verdict = i18n.t(DATA_STATE_TEXT.get(pipeline_state, DATA_STATE_TEXT["warn"]))
    data_detail = _plain_text_from_markup(health.get("pipeline_detail_html"))
    data_html = _tile_content_html(data_verdict, data_detail)

    tiles = (
        layout.stat_tile(i18n.t(FRAME_ROW_LABEL), frame_html, device_state, icon="icon-device")
        + layout.stat_tile(
            i18n.t(BATTERY_ROW_LABEL), battery_html, battery_state, icon="icon-battery")
        + layout.stat_tile(i18n.t(DATA_ROW_LABEL), data_html, pipeline_state, icon="icon-pipeline")
    )

    # D-17 (21-01-PLAN.md Task 2): the display-mode gate that used to
    # hide this link is deleted outright — never re-add it here.
    health_link_html = (
        '<p class="text-label"><a href="/health">%s</a></p>'
    ) % escape_html(i18n.t(HEALTH_LINK_TEXT))

    return (
        '<section class="home-section" aria-labelledby="home-status">'
        '<h2 class="text-heading" id="home-status">%s</h2>'
        '<div class="dashboard-grid home-status-grid">%s</div>'
        "%s"
        "</section>"
    ) % (escape_html(i18n.t(STATUS_HEADING)), tiles, health_link_html)


def _hero_figure_html(ctx, current_flight_row):
    """The hero row's left half: the current picture, its "Rendered
    HH:MM" caption and, when the current flight is known, a one-line
    "AFR1380 · Air France · ORY → TLS" reusing the SAME recent-flights
    query result (D-20 — no second query for the "current flight").
    """
    entries = ctx.get("gallery_entries") or []
    now = ctx.get("now")
    newest = entries[0] if entries else None
    if not newest:
        return layout.empty_state(i18n.t(NO_PANEL_HEADING), i18n.t(NO_PANEL_BODY))

    iso = _gallery_name_to_iso(newest)
    caption = (
        i18n.t(RENDERED_CAPTION_TEMPLATE) % layout.concise_timestamp_html(iso, now)
        if iso else "")
    flight_html = ""
    if current_flight_row:
        callsign = current_flight_row.get("callsign") or current_flight_row.get("hex") or "—"
        secondary = _flight_secondary_text(current_flight_row)
        flight_html = (
            '<span class="preview-frame__flight"><span class="mono">%s</span>%s</span>'
        ) % (
            escape_html(callsign),
            (" · " + escape_html(secondary)) if secondary else "")

    return (
        '<figure class="preview-frame">'
        '<img class="preview-frame__image" src="%s%s" alt="%s" '
        'width="600" height="800" decoding="async">'
        '<figcaption class="preview-frame__caption text-label">%s%s</figcaption>'
        "</figure>"
    ) % (
        GALLERY_ROUTE_PREFIX, escape_html(newest), escape_html(i18n.t(PANEL_ALT_TEXT)),
        caption, flight_html)


def _recent_flight_thumb_html(row, state_dir):
    """D-17.2: the leading thumbnail cell. `illustrations.normalise_
    airline_key()` is the exact pure-string resolver airlines_page.py
    already calls (D-20 — no new query for the key itself); the `<img>`
    renders only when `illustrations.resolved_illustration_path(key,
    state_dir)` (the same override-then-vendored, `os.path.isfile`-
    backed seam airlines_page.py's own gallery/gap cards already call)
    finds a real file on disk for that key — never unconditionally.

    An airline the app recognises by NAME but that carries no artwork
    file at all (a seeded "easyJet Europe" is exactly this case) used
    to still emit `<img src="/illustration/{key}.png">`, which 404s and
    renders as a broken-image icon; that is a real rendering defect
    (a missing resource surfacing as visibly broken chrome), not a
    cosmetic one. A falsy key OR a key with no resolved file both now
    render the identical dashed placeholder with no `<img>` at all, so
    a missing file can never surface as a broken-image icon. This costs
    one extra filesystem stat per row (`resolved_illustration_path()`'s
    own `os.path.isfile()` calls) — at most RECENT_FLIGHTS_LIMIT (5) per
    page load, not a meaningful cost.
    """
    # 22-07-PLAN.md Task 1 (X4): the KEY resolves on the raw stored
    # airline string — server/plane/render.py's own _flight_line2_
    # text() docstring is explicit that display_airline_name() "never
    # reaches illustration selection" — only the alt text below, a
    # user-visible string, is aliased.
    raw_airline = row.get("airline")
    key = illustrations.normalise_airline_key(raw_airline)
    if key and illustrations.resolved_illustration_path(key, state_dir) is not None:
        alt_text = i18n.t(THUMBNAIL_ALT_TEMPLATE) % panel_render.display_airline_name(raw_airline)
        return (
            '<img class="recent-flight__thumb" loading="lazy" decoding="async" '
            'width="40" height="40" src="%s%s.png" alt="%s">'
        ) % (ILLUSTRATION_ROUTE_PREFIX, key, escape_html(alt_text))
    return '<span class="recent-flight__thumb recent-flight__thumb--placeholder"></span>'


_TIME_CELL_FALLBACK_TEXT = "no reading yet"


def _recent_flight_time_html(ts, now):
    """B18 (22-07-PLAN.md Task 2): the recent-flight time, ONE line —
    the clock takes the `.time-value` role (22-04-PLAN.md, C5: sans,
    tabular numerals, never `--font-mono` — monospace stays reserved
    for identifiers, callsign/ICAO24/the masked calendar URL, never a
    clock), the relative age sits beside it as a `.time-value__age`
    sibling (the muted label voice C5 also defined), joined by the
    existing `.cell-inline-sep` middle dot (history_page.py's own
    `_merged_cell()` "Inline compact" convention, reused here rather
    than inventing a second home-page-only separator — a page module
    may never import another, so the dot itself is a local literal,
    not an imported constant).

    Deliberately does NOT reach for `layout.concise_timestamp_html()`
    here (mirroring history_page._when_cell_html()'s own documented
    reasoning for its own two-line shape): that function bundles the
    clock and the relative age into ONE already-escaped `<span
    class="mono">` — exactly the mono-family, single-element shape
    this fix removes. The clock and the age are built and escaped
    separately instead, each in its own role.

    Falls back to the escaped, translated "no reading yet" text — the
    same default `concise_timestamp_html()` carried at this call site
    before this task — when `ts` is falsy or fails to parse.

    23-03-PLAN.md Task 2 (D14/CFG-34): the age half is now
    `layout.relative_time_html()`'s `<time data-relative>` element
    rather than a bare escaped string, so the ticker plan 23-05 adds can
    find it. The split above is UNCHANGED — the clock keeps
    `.time-value`, the age keeps `.time-value__age`, the dot keeps
    `.cell-inline-sep`, and the reasoning for not reaching for
    `concise_timestamp_html()` here still holds, because that function's
    single mono span is still the shape this cell exists to avoid. The
    element is semantic, not presentational: it sits INSIDE the role
    span rather than replacing it. The parentheses stay outside the
    element (they are this cell's punctuation, not part of the age), and
    `relative_time_html()` is a raw-markup producer, so its return value
    is interpolated verbatim and never escaped again.
    """
    if not ts:
        return escape_html(i18n.t(_TIME_CELL_FALLBACK_TEXT))
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return '<span class="time-value">%s</span>' % escape_html(ts)
    clock_text = layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now))
    cell_html = '<span class="time-value">%s</span>' % escape_html(clock_text)
    age = layout.age_seconds(ts, now)
    if age is not None:
        cell_html += (
            '<span class="cell-inline-sep">·</span>'
            '<span class="time-value__age">(%s)</span>'
        ) % layout.relative_time_html(ts, now)
    return cell_html


def _recent_flights_html(rows, now, state_dir):
    if not rows:
        body = layout.empty_state(i18n.t(NO_FLIGHTS_HEADING), i18n.t(NO_FLIGHTS_BODY))
    else:
        items = []
        for row in rows:
            callsign = row.get("callsign") or row.get("hex") or "—"
            secondary = _flight_secondary_text(row)
            items.append(
                '<li class="recent-flight">%s'
                '<span class="recent-flight__callsign mono">%s</span>'
                '<span class="recent-flight__detail text-label">%s</span>'
                '<span class="recent-flight__time text-label">%s</span>'
                "</li>"
                % (_recent_flight_thumb_html(row, state_dir), escape_html(callsign),
                   escape_html(secondary), _recent_flight_time_html(row.get("ts"), now)))
        body = '<ul class="recent-flights">%s</ul>' % "".join(items)
    return (
        '<section class="page-section home-section" aria-labelledby="home-flights">'
        '<h2 class="text-heading" id="home-flights">%s</h2>%s'
        '<p class="text-label"><a href="%s">%s</a></p>'
        "</section>"
    ) % (
        escape_html(i18n.t(RECENT_FLIGHTS_HEADING)), body,
        FLIGHTS_ROUTE, escape_html(i18n.t(RECENT_FLIGHTS_LINK_TEXT)))


def _day_checkins(conn):
    return history_db.recent_device_health(conn, limit=DAY_BAND_ROW_LIMIT)


def _paris_day_bounds(now):
    """`(day, day_start_epoch, day_seconds)` for the Europe/Paris day
    `now` falls in, or None when `now` does not parse.

    `day_seconds` IS MEASURED between two real Paris midnights and never
    assumed to be 86 400: a Europe/Paris day is 23 or 25 hours twice a
    year, and on 2026-10-25 a band assuming 86 400 would put midday at
    54.17% instead of 52.00% and leave an hour of its own width
    unreachable. `draw.percent_time()` takes the length as a parameter
    for exactly this reason.

    `layout.LOCAL_TZ` is this app's one Europe/Paris constant and the
    same one every timestamp on this page is already formatted through,
    so the band and the row beneath it cannot disagree about which day
    it is.
    """
    parsed = history_db._instant_or_none(now)
    if parsed is None:
        return None
    day = parsed.astimezone(layout.LOCAL_TZ).date()
    start = datetime.combine(day, time(0), tzinfo=layout.LOCAL_TZ)
    end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=layout.LOCAL_TZ)
    return day, start.timestamp(), end.timestamp() - start.timestamp()


def _day_band_instants(rows, day):
    """The epoch seconds of every row in `rows` whose stored `ts` falls
    on the Europe/Paris calendar day `day`.

    Bucketed through `history_db._paris_day_or_none()` — the ONE date
    path, the same one `check_in_gaps()` and `daily_battery_averages()`
    use, so a mark on this band and a row in Health's own day-bucketed
    data can never disagree about which day a check-in belongs to. It is
    a private name and reached across a package boundary knowingly:
    server/history_db.py exposes no public equivalent, and it is not
    this plan's file to add one to. A local re-derivation would be the
    second date path this band exists to avoid.

    THE BUCKETING IS THE WHOLE POINT AND NOT A FILTER. Paris is UTC+1 or
    UTC+2, so a check-in at 00:30 Paris is stored as 22:30 UTC on the
    PREVIOUS date; a band that compared UTC dates would drop it from
    today and pick up tomorrow's 00:30 instead — the same number of
    marks drawn from the wrong rows, which is the shape of defect
    nothing downstream would notice.
    """
    instants = []
    for row in rows or ():
        ts = row.get("ts") if isinstance(row, dict) else None
        if history_db._paris_day_or_none(ts) != day:
            continue
        parsed = history_db._instant_or_none(ts)
        if parsed is not None:
            instants.append(parsed.timestamp())
    return instants


def _quiet_hours_window(config, day_start, day_seconds):
    """`((start_epoch, end_epoch), start_hm, end_hm)` for the configured
    quiet-hours window placed on the band's own day, or `(None, None,
    None)` when quiet hours are not enabled or the config is unusable.

    The enabled test is `is True` and not truthiness, byte-for-byte what
    `device_config.quiet_hours_status()` itself applies, and both time
    strings go back through `device_config.normalise_quiet_hours_time()`
    — the one normaliser — so a hand-edited config cannot put an
    unvalidated string into the arithmetic. No "23:00" literal appears
    here; the defaults are the module's own constants.

    `quiet_hours_status()` itself is deliberately NOT the source, and
    this is a correction to 24-06-PLAN.md Task 2's stated interface: it
    returns `(seconds_remaining, end_hm)`, which answers "are quiet
    hours active right now and when do they end" — an ACTIVITY status.
    The band needs the window's two ENDS regardless of whether it is
    active, which that accessor cannot give. What it can give is its own
    derivation path, and this function reuses exactly that path one
    level down rather than inventing a second one.

    The end may precede the start; that is a night window, the normal
    configuration, and `draw.day_band()` is where it becomes two spans.
    """
    if not isinstance(config, dict) or config.get("quiet_hours_enabled") is not True:
        return None, None, None
    try:
        start_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_start"), device_config.DEFAULT_QUIET_HOURS_START)
        end_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_end"), device_config.DEFAULT_QUIET_HOURS_END)
        start = day_start + _hm_seconds(start_hm)
        end = day_start + _hm_seconds(end_hm)
    except (TypeError, ValueError):
        return None, None, None
    if start > day_start + day_seconds or end > day_start + day_seconds:
        # A DST day is 23 or 25 hours long, so an "HH:MM" offset counted
        # from midnight can land past the band's own right edge. Rather
        # than clamp — which would silently redraw the window the user
        # configured — the shading is dropped and the caption with it.
        return None, None, None
    return (start, end), start_hm, end_hm


def _hm_seconds(hm):
    """Seconds from midnight for a normalised "HH:MM" string."""
    hours, _, minutes = hm.partition(":")
    return int(hours) * 3600 + int(minutes) * 60


def _day_band_html(ctx, rows):
    """The day band's <section>, or "" when there is no day to draw.

    `rows` is the ONE device_health read render() makes (D-20) — this
    function re-queries nothing. An unreadable history.db arrives here
    as `rows is None` and renders NOTHING AT ALL, which is the one case
    an empty band would be dishonest in: an empty band says "no
    check-ins today", and a failed read knows nothing of the sort. A day
    that genuinely holds no check-ins renders the band empty, because an
    absent section reads as an unbuilt feature and this page already
    makes that distinction (the battery tile's "No reading yet" verdict
    rather than a zero).
    """
    if rows is None:
        return ""
    bounds = _paris_day_bounds(ctx.get("now"))
    if bounds is None:
        return ""
    day, day_start, day_seconds = bounds
    instants = _day_band_instants(rows, day)
    window, start_hm, end_hm = _quiet_hours_window(
        ctx.get("device_config"), day_start, day_seconds)
    canvas, collapsed = draw.day_band(
        day_start, day_seconds, instants, window=window,
        label=i18n.t(DAY_BAND_LABEL))
    day_text = day.isoformat()

    # The caption is written from `collapsed`, not from the row count
    # alone (T-24-06-B). The total stays printed as TEXT — that number is
    # true and useful — but when the band merged anything it says so, so
    # a reader who counts the marks and gets fewer is not being told the
    # drawing lost some silently.
    total = len(instants)
    if not total:
        caption = i18n.t(DAY_BAND_EMPTY_TEXT) % (day_text,)
    elif total == 1:
        caption = i18n.t(DAY_BAND_ONE_TEXT) % (day_text,)
    else:
        caption = i18n.t(DAY_BAND_COUNT_TEXT) % (total, day_text)
    sentences = [escape_html(caption)]
    if collapsed or len(rows) >= DAY_BAND_ROW_LIMIT:
        sentences.append(escape_html(i18n.t(DAY_BAND_COLLAPSED_TEXT)))
    if window is not None:
        sentences.append(escape_html(i18n.t(DAY_BAND_QUIET_TEXT) % (start_hm, end_hm)))
    hours = "".join(
        "<span>%s</span>" % escape_html(label) for label in DAY_BAND_HOUR_LABELS)
    return (
        '<section class="page-section home-section day-band" '
        'aria-labelledby="home-day-band">'
        '<h2 class="text-heading" id="home-day-band">%s</h2>'
        '%s'
        '<p class="day-band__hours text-label mono">%s</p>'
        '<p class="text-label">%s</p>'
        "</section>"
    ) % (escape_html(i18n.t(DAY_BAND_HEADING)), canvas, hours, " ".join(sentences))


def render(ctx):
    """D-04 (21-CONTEXT.md, 21-04-PLAN.md Task 3): strip -> three tiles
    -> a two-column picture/recent-flights row. `_hero_figure_html()`/
    `_recent_flights_html()` bodies are unchanged — only render()'s own
    assembly order changes; the phase-20 hero row and its status-card
    builder are both gone.
    """
    now = ctx.get("now")
    # D-20: one read, reused for both the hero's flight one-liner (its
    # first row is "the current flight") and the recent-flights list —
    # never two independent queries for what is the same data.
    rows = _safe_query(ctx.get("state_dir"), _recent_flights)
    current_flight_row = rows[0] if rows else None
    # 24-06-PLAN.md Task 2 (CFG-42): the day band's own single read, and
    # the second application of D-20's rule rather than an exception to
    # it — `device_health` is a DIFFERENT table from the runway events
    # above, so this is one more read and not a duplicate one. It is
    # made HERE and passed down for the same reason `rows` is: a builder
    # that queried for itself would make the page's cost depend on how
    # many sections happen to want the data.
    checkin_rows = _safe_query(ctx.get("state_dir"), _day_checkins)
    # 23-06-PLAN.md Task 2 (D1/CFG-35): Home refreshes itself. The
    # freshness line is the shared builder's — one definition site,
    # three call sites — and it is what carries `data-loaded-at`, the
    # marker companion/static/freshness.js requires before it does
    # anything at all. Which regions this page then swaps is declared
    # once, in layout.REFRESH_SWAP_SELECTORS_BY_PAGE, and read by the
    # script through the page key page_shell() renders on <body>; this
    # module names no selector and knows nothing about the loop.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), purpose=i18n.t(PAGE_PURPOSE),
        freshness_html=layout.freshness_line_html(now))
    # 22-07-PLAN.md Task 1 (D-03/CFG-26): migrated to the richer
    # wake.next_wake_status() accessor plan 22-02 added — frame_strip_
    # html()'s own `next_wake_iso` parameter still only needs the ISO
    # element (kept for that function's call-site signature
    # compatibility, 22-04-PLAN.md); _status_tiles_html() below makes
    # its OWN fresh call to the same function against the same ctx
    # fields, exactly mirroring frame_strip_html()'s own "recompute,
    # never re-derive" pattern, so the two can never disagree.
    next_wake_iso = wake.next_wake_status(
        ctx.get("last_checkin_ts"), ctx.get("device_config"))[0]
    return (
        header
        + layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)
        + _status_tiles_html(ctx)
        + _day_band_html(ctx, checkin_rows)
        + '<div class="home-columns home-picture-row">'
        + _hero_figure_html(ctx, current_flight_row)
        + _recent_flights_html(rows, now, ctx.get("state_dir"))
        + "</div>"
    )
