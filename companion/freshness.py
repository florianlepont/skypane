"""The light freshness check's server-computed input token, moved out of
`companion/app.py`: built from a route's own inputs alone (a handful of
`stat()` calls, one small `SELECT` through the request's own scoped
connection, and the shared `health_signals()` snapshot), with no markup
ever rendered to answer a tick. `companion/app.py`'s `Handler._render_tab()`
computes it right after `page_context()` but before `render()` runs, and
answers a matching freshness tick with a bodiless 304 — see that method's
own docstring for the full contract.

Never imports `companion.app` (that would be a cycle — app.py imports
this module).
"""
import hashlib
import json
import os
import sqlite3
from zoneinfo import ZoneInfo

from companion import frame_state, layout
from companion.pages import health_page
from server import device_config, history_db
from server.plane import calendar_rules, colour_rules, manual_resolutions
import server.state_store as state_store

# The four refresh pages a freshness tick may answer with a bodiless 304:
# a conditional GET on the page's OWN URL, never a new route. Keyed by
# layout.nav_slug(route) - the same vocabulary
# layout.REFRESH_PAGE_* and companion/static/freshness.js's
# SWAP_SELECTORS_BY_PAGE already use - so /device and /airlines (neither
# a member) never compute a token or carry one on <body> at all.
_FRESHNESS_PAGE_SLUGS = frozenset((
    layout.REFRESH_PAGE_HOME, layout.REFRESH_PAGE_DISPLAY,
    layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_FLIGHTS,
))


def _freshness_file_stamp(path):
    """`[mtime_ns, ctime_ns, size, mode]` for `path`, or the literal
    "missing" - a stat() failure (never created, or deleted) is a real,
    distinct input state for the freshness token, not an error to
    swallow. `st_ctime_ns`/`st_mode` matter beyond `st_mtime_ns`/
    `st_size` for at least one stamped file: a bare `chmod` on the
    calendar secret changes only the mode and the ctime, never the
    mtime or the size, and that mode is itself a security signal
    (`calendar_rules.calendar_secret_mode_is_unsafe()` reads it to
    raise the drift banner).
    """
    try:
        st = os.stat(path)
    except OSError:
        return "missing"
    return [st.st_mtime_ns, st.st_ctime_ns, st.st_size, st.st_mode]


def _freshness_file_stamps(state_dir):
    """`_freshness_file_stamp()` for every file-backed freshness-token
    input: `device_config.json`, `poll_state.json`, the calendar
    registry, the calendar secret, the manual-resolutions registry, the
    colour-rules registry, `panel.bin`, and the off-box marker (if
    configured at all - "disabled" when `OFFBOX_MARKER_ENV_VAR` is
    unset, distinct from "missing", which means the env var names a file
    that is not there). Each path comes from its own module's own path
    builder, never a second, drifting copy of the filename - `panel.bin`
    has no such builder anywhere in the codebase (every writer inlines
    the name), so this does too.

    The calendar secret is stamped separately from the calendar registry
    it is stored beside: Display renders `calendar_configured` and
    `calendar_drift` (`config_page._aspect_card_html()`), both read from
    `calendar_rules.calendar_secret_path()` - a drift appearing/clearing,
    the secret being removed by hand, or a `save_calendar_url()` path
    that leaves the registry untouched are all otherwise invisible to
    this token until the forced full refresh, on a signal that can mean
    the secret was exposed.
    """
    marker_path = os.environ.get(health_page.OFFBOX_MARKER_ENV_VAR)
    return {
        "device_config": _freshness_file_stamp(
            device_config.device_config_path(state_dir)),
        "poll_state": _freshness_file_stamp(state_store.poll_state_path(state_dir)),
        "calendar_registry": _freshness_file_stamp(
            calendar_rules.calendar_rules_path(state_dir)),
        "calendar_secret": _freshness_file_stamp(
            calendar_rules.calendar_secret_path(state_dir)),
        "manual_resolutions": _freshness_file_stamp(
            manual_resolutions.manual_resolutions_path(state_dir)),
        "colour_rules": _freshness_file_stamp(colour_rules.colour_rules_path(state_dir)),
        "panel_bin": _freshness_file_stamp(os.path.join(state_dir, "panel.bin")),
        "offbox_marker": (
            "disabled" if not marker_path else _freshness_file_stamp(marker_path)),
    }


def _freshness_db_signal(state_dir, want_pipeline_run):
    """The freshness token's database-backed piece: the two per-table
    MAX(id) watermarks (one SELECT) plus the last-detection/source-fault
    meta keys, read through the request's own single scoped connection -
    an `open_db()` call here inside an active `connection_scope()`
    reuses it, never opens a second one. Any (sqlite3.Error, OSError)
    collapses the WHOLE group to the literal "unavailable" (still
    hashed into the token, so an outage still answers 200 with a token,
    never a 500) rather than a partial read. `want_pipeline_run` is set
    for Health and Home - Health's Pipeline tile and Home's Flight-data
    tile both render that timestamp as plain text via
    `concise_timestamp_html()`, and `.home-status-grid` is one of
    Home's own declared swap regions - the other two pages (Flights,
    Display) render nothing derived from it, so they must never see it
    change on every poll cycle, or an unchanged repeat cycle would give
    them a new token for no visible reason.

    No third watermark from the per-wake-interval-change table: nothing
    under companion/ may read it yet (a repo-wide guard test enforces
    this - it accrues data for a later phase), so it can never be a
    token input here either.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            row = conn.execute(
                "SELECT "
                "(SELECT MAX(id) FROM runway_events) AS runway_events_id, "
                "(SELECT MAX(id) FROM device_health) AS device_health_id"
            ).fetchone()
            result = {
                "runway_events_id": row["runway_events_id"],
                "device_health_id": row["device_health_id"],
                "last_detection": history_db.get_meta(conn, history_db.META_LAST_DETECTION),
                "source_fault": history_db.get_meta(conn, history_db.META_SOURCE_FAULT),
            }
            if want_pipeline_run:
                result["last_pipeline_run"] = history_db.get_meta(
                    conn, history_db.META_LAST_PIPELINE_RUN)
            return result
    except (sqlite3.Error, OSError):
        return "unavailable"


def _freshness_paris_date(now):
    """The Europe/Paris calendar date `now` falls on, or `None` when
    `now` fails to parse - Health's regularity grid buckets its cells
    by this same day. A naive `now` (never produced by
    `history_db.utc_now_iso()` in practice) is taken as UTC first,
    matching `health_page._as_paris()`'s own convention, rather than
    the ambiguous "system local time" `astimezone()` would otherwise
    assume.
    """
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(layout.LOCAL_TZ).date().isoformat()


# The health_signals() fields every freshness token folds in unchanged -
# never recomputed, the same "copy, don't recompute" discipline
# health_page.health_state_from_signals() itself follows. Anything a
# route's own render() derives from one of these (a tile's verdict text,
# the frame strip) is therefore already covered without naming it twice.
_FRESHNESS_SIGNAL_FIELDS = (
    "severity", "anomalies", "device_state", "pipeline_state",
    "battery_state", "coverage_state", "disagreement_warn", "source_fault",
    "offbox", "next_wake_iso", "effective_interval_s", "hold_reason",
)


def _page_freshness_token(route, ctx, query):
    """The freshness check's server-computed input token: built from the
    page's own inputs alone, with NO markup ever rendered
    to answer a tick - `render(ctx)` never runs on this path at all when
    the token matches. A completeness test mutates each input below and
    expects a different token on the affected route or routes; the
    client's own periodic forced full refresh
    (companion/static/freshness.js's FORCED_REFRESH_EVERY_N_TICKS)
    bounds whatever this list still misses.

    `ctx["_health_signals"]` is read through the ctx's own internal
    loader key (shared with "health_state"/"health_severity"), so the
    one `health_page.health_signals()` read this triggers is the same
    snapshot a route's own `render()` reuses afterwards on a token
    mismatch - never a second, independent read at a later instant.
    """
    state_dir = ctx["state_dir"]
    now = ctx["now"]
    slug = layout.nav_slug(route)
    signals = ctx["_health_signals"]
    signal_fields = (
        None if signals is None
        else {key: signals[key] for key in _FRESHNESS_SIGNAL_FIELDS}
    )
    parts = {
        "route": route,
        "query": query,
        "lang": ctx["lang"],
        "ui_theme": ctx["ui_theme"],
        "db": _freshness_db_signal(
            state_dir,
            want_pipeline_run=slug in (layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_HOME)),
        "signals": signal_fields,
        "files": _freshness_file_stamps(state_dir),
        # Reuses the ctx's own lazy "gallery_entries" loader (cached after
        # this first read) rather than a second, direct gallery_entries()
        # call - a route whose render() also reads it (Home, Flights)
        # must still pay for exactly one scandir(), not two.
        "gallery_newest": (ctx["gallery_entries"] or [None])[0],
    }
    if slug in (layout.REFRESH_PAGE_HOME, layout.REFRESH_PAGE_DISPLAY):
        parts["frame_state"] = (
            None if signals is None else frame_state.resolve_state(
                signals["next_wake_iso"], signals["effective_interval_s"],
                signals["hold_reason"], now))
    if slug in (layout.REFRESH_PAGE_HEALTH, layout.REFRESH_PAGE_HOME, layout.REFRESH_PAGE_DISPLAY):
        # Home's day band (_day_checkins()) buckets check-ins by this same
        # Paris calendar day, and both Home's and Display's own next-wake
        # local_clock_text() choose day qualifiers ("today"/"tomorrow")
        # relative to `now` - at midnight, with no new check-in, neither
        # page's token would otherwise change until the forced refresh.
        parts["paris_date"] = _freshness_paris_date(now)
    encoded = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]
