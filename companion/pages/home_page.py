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

import companion.battery as battery
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from companion.layout import escape_html
from server import history_db
from server.plane import illustrations

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
FRAME_ROW_LABEL = "Frame"
BATTERY_ROW_LABEL = "Battery"
DATA_ROW_LABEL = "Flight data"
HEALTH_LINK_TEXT = "See details on Health"

FRAME_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
}
DATA_STATE_TEXT = {
    "ok": "Up to date",
    "warn": "A little stale",
    "error": "Stale — the server may be down",
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
    airline = row.get("airline") or ""
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


def _tile_content_html(verdict, detail):
    """The Emphasis-verdict-plus-Label-detail composition every one of
    the three tiles below shares — a genuinely new pairing every time
    (never the same sentence twice, 20-RESEARCH.md Pitfall 3's
    confirmed root cause), so this one helper is the single write site
    for it rather than three near-identical inline literals. `detail`
    is omitted ENTIRELY (no placeholder) when falsy, matching every
    other "omit rather than fabricate" contract in this module.
    """
    verdict_html = '<p class="text-body widget-verdict">%s</p>' % escape_html(verdict)
    if not detail:
        return verdict_html
    return verdict_html + '<p class="text-label widget-detail">%s</p>' % escape_html(detail)


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
    verdict-free field (`device_detail_html`/`pipeline_html`), reduced
    to plain text by `_plain_text_from_markup()` above — NEVER the
    health state's own combined device-summary field, which carries
    the Frame verdict a second time (the phase-19 body's own bug this
    rebuild does not resurrect). The
    frame verdict therefore appears exactly once on the whole page.
    """
    health = ctx.get("health_state") or {}
    device_state = health.get("device_state") or "warn"
    pipeline_state = health.get("pipeline_state") or "warn"
    battery_state = health.get("battery_state") or "warn"

    frame_verdict = i18n.t(FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
    frame_detail = _plain_text_from_markup(health.get("device_detail_html"))
    frame_html = _tile_content_html(frame_verdict, frame_detail)

    reading = _safe_query(ctx.get("state_dir"), _latest_battery)
    if reading and reading.get("battery_mv"):
        pct = battery.battery_percent(reading["battery_mv"])
        pct_text = ("≈ %d%%" % pct) if pct is not None else ""
        mv_text = "%s mV" % reading["battery_mv"]
        battery_verdict = i18n.t(BATTERY_STATE_TEXT.get(battery_state, BATTERY_STATE_TEXT["warn"]))
        battery_detail = "%s · %s" % (pct_text, mv_text) if pct_text else mv_text
    else:
        battery_verdict = i18n.t(NO_READING_TEXT)
        battery_detail = ""
    battery_html = _tile_content_html(battery_verdict, battery_detail)

    data_verdict = i18n.t(DATA_STATE_TEXT.get(pipeline_state, DATA_STATE_TEXT["warn"]))
    data_detail = _plain_text_from_markup(health.get("pipeline_html"))
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
    key = illustrations.normalise_airline_key(row.get("airline"))
    if key and illustrations.resolved_illustration_path(key, state_dir) is not None:
        alt_text = i18n.t(THUMBNAIL_ALT_TEMPLATE) % row.get("airline")
        return (
            '<img class="recent-flight__thumb" loading="lazy" decoding="async" '
            'width="40" height="40" src="%s%s.png" alt="%s">'
        ) % (ILLUSTRATION_ROUTE_PREFIX, key, escape_html(alt_text))
    return '<span class="recent-flight__thumb recent-flight__thumb--placeholder"></span>'


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
                   escape_html(secondary), layout.concise_timestamp_html(row.get("ts"), now)))
        body = '<ul class="recent-flights">%s</ul>' % "".join(items)
    return (
        '<section class="page-section home-section" aria-labelledby="home-flights">'
        '<h2 class="text-heading" id="home-flights">%s</h2>%s'
        '<p class="text-label"><a href="%s">%s</a></p>'
        "</section>"
    ) % (
        escape_html(i18n.t(RECENT_FLIGHTS_HEADING)), body,
        FLIGHTS_ROUTE, escape_html(i18n.t(RECENT_FLIGHTS_LINK_TEXT)))


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
    header = layout.page_header(i18n.t(PAGE_TITLE), purpose=i18n.t(PAGE_PURPOSE))
    next_wake_iso = wake.next_wake_at_iso(ctx.get("last_checkin_ts"), ctx.get("device_config"))
    return (
        header
        + layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)
        + _status_tiles_html(ctx)
        + '<div class="home-columns home-picture-row">'
        + _hero_figure_html(ctx, current_flight_row)
        + _recent_flights_html(rows, now, ctx.get("state_dir"))
        + "</div>"
    )
