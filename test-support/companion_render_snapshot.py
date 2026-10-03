"""Deterministic render-snapshot harness for the companion app.

Produces (and, via `main()`, writes) `companion/testdata/render_baseline.json`:
a byte-level record of every page's served HTML (both languages, both
explicit themes, a deterministic seeded state, a frozen clock) plus the
unauthenticated (status, Location) response of every route
`companion/routes.py`'s `ROUTES` table knows about today.
`companion/test_render_baseline.py` asserts a fresh capture equals this
file byte-for-byte — the "no rendered-output change" proof this
behaviour-preserving refactor phase is verified against.

Three real time sources leak into the companion app's rendered HTML, and
all three are frozen by `frozen_clock()` for the whole capture:

- `server.history_db.utc_now_iso()` — the "now" every page-rendering call
  site threads through explicitly (layout.py's age/freshness helpers,
  every page module's own `now` parameter).
- `time.time()` — `server.plane.calendar_rules.load_calendar_registry()`'s
  retention-window filter falls back to it when no `now=` is supplied
  (companion/app.py's own read call sites never pass one), so the set of
  calendar entries a page sees at render time depends on it too.
- `companion.health_sections.datetime.now(timezone.utc)` — the one
  fallback `resolution_stats()` takes when its own caller
  (`companion/pages/health_page.py`'s `render()`) does not pass `now=`
  explicitly; frozen by replacing the module's own `datetime` name with a
  `datetime` subclass whose `now()` is pinned, not by patching the
  immutable stdlib class itself. `resolution_stats()` moved out of
  `health_page.py` into `companion/health_sections.py` (a companion-level
  markup module, not a page module) to keep `health_page.py` under this
  app's own file-size ceiling; the frozen name follows the function.

One value cannot be frozen by patching its source and is instead
normalised by regex, exactly once, on every captured page body: the four
freshness pages' (Home, Display, Health, Flights) `data-refresh-token`
attribute (and the identical value in their ETag, not itself captured).
`companion/freshness.py`'s `_freshness_file_stamp()` folds each stamped file's
`st_ctime_ns` into the token, and `ctime` is the filesystem's own
"metadata last changed" clock — set by the kernel on every write, with no
syscall (`os.utime()` included) able to back-date it. Two independent
temporary state directories, however identically seeded and however
frozen every application-level clock is, therefore always produce
different tokens. `_TOKEN_RE` replaces the attribute's 32-hex value with
a fixed placeholder before a page body is stored or compared.
"""
import argparse
import json
import os
import re
import tempfile
import time
import urllib.parse
from contextlib import contextmanager
from datetime import datetime, timedelta

import companion_app_server
import companion.app as companion_app
from companion import auth
import companion.health_sections as health_sections
from companion.pages import airlines_page
from server import device_config, history_db
from server.plane import calendar_rules, colour_rules, manual_resolutions
import server.state_store as state_store
from skypane_test_support import REPO_ROOT

# A fixed, deterministic instant — never real wall-clock time. Every
# on-disk timestamp this module seeds is computed relative to it, and
# frozen_clock() pins every render-time clock read to it too, so two
# captures taken at genuinely different wall-clock times are byte-identical.
FROZEN_NOW = "2026-08-15T09:00:00+00:00"

BASELINE_RELATIVE_PATH = os.path.join("companion", "testdata", "render_baseline.json")

LANGS = ("en", "fr")
THEMES = ("light", "dark")

_NOT_FOUND_PATH = "/this-page-does-not-exist"

# One concrete (path, method, needs_session, form) sample per PAGE_REQUESTS
# entry the plan calls for: the seven NAV_TABS routes, /device and
# /display with the flash-banner query, the unauthenticated /login page,
# a 404 path, and the calendar-disconnect confirm page (a POST with no
# confirm field, which renders the confirm page at 200 without changing
# state).
PAGE_REQUESTS = (
    (companion_app.HOME_ROUTE, "GET", True, None),
    (companion_app.DISPLAY_ROUTE, "GET", True, None),
    (companion_app.DEVICE_ROUTE, "GET", True, None),
    (companion_app.FLIGHTS_ROUTE, "GET", True, None),
    (companion_app.HEALTH_ROUTE, "GET", True, None),
    (companion_app.AIRLINES_ROUTE, "GET", True, None),
    (companion_app.UPDATE_ROUTE, "GET", True, None),
    (companion_app.DEVICE_ROUTE + "?flash=saved", "GET", True, None),
    (companion_app.DISPLAY_ROUTE + "?flash=saved", "GET", True, None),
    (companion_app.LOGIN_ROUTE, "GET", False, None),
    (_NOT_FOUND_PATH, "GET", True, None),
    (companion_app.CALENDAR_DISCONNECT_ROUTE, "POST", True, {}),
)

# One concrete (method, path) sample for EVERY route companion/routes.py's
# ROUTES table knows about today, named from companion/app.py's own
# route constants — never discovered by reading its source text. Prefix
# routes get a plausible id; POSTs are issued with an Origin header
# auth.post_origin_ok() accepts (the server's own base URL).
_UNAUTH_GET_REQUESTS = (
    companion_app.LOGIN_ROUTE,
    companion_app.STYLE_ROUTE,
    companion_app.SCRIPT_ROUTE,
    companion_app.NAV_SCRIPT_ROUTE,
    companion_app.DIRTY_STATE_SCRIPT_ROUTE,
    companion_app.LIST_FILTER_SCRIPT_ROUTE,
    companion_app.COPY_BUTTON_SCRIPT_ROUTE,
    companion_app.FRESHNESS_SCRIPT_ROUTE,
    companion_app.PANEL_LOOKUP_SCRIPT_ROUTE,
    companion_app.FLASH_CLEANUP_SCRIPT_ROUTE,
    companion_app.POLL_COOLDOWN_SCRIPT_ROUTE,
    companion_app.CONFIRM_SUBMIT_SCRIPT_ROUTE,
    companion_app.THEME_PREVIEW_SCRIPT_ROUTE,
    companion_app.AIRLINE_TYPES_SCRIPT_ROUTE,
    companion_app.LOGIN_CARD_SCRIPT_ROUTE,
    companion_app.SUBMIT_GUARD_SCRIPT_ROUTE,
    companion_app.RELATIVE_TIME_SCRIPT_ROUTE,
    companion_app.QUICK_SWITCH_SCRIPT_ROUTE,
    companion_app.VALUE_CONTROLS_SCRIPT_ROUTE,
    companion_app.HOME_ROUTE,
    companion_app.DISPLAY_ROUTE,
    companion_app.DEVICE_ROUTE,
    companion_app.FLIGHTS_ROUTE,
    companion_app.HEALTH_ROUTE,
    companion_app.AIRLINES_ROUTE,
    companion_app.UPDATE_ROUTE,
    companion_app.SETTINGS_ROUTE,
    companion_app.HISTORY_LEGACY_ROUTE,
    companion_app.PREVIEW_PAGE_ROUTE,
    companion_app.GALLERY_ROUTE_PREFIX + "sample.png",
    companion_app.RUNWAY_IMAGE_ROUTE_PREFIX + "09.png",
    companion_app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + "air-france.png",
    companion_app.THEME_PREVIEW_ROUTE_PREFIX + "midnight.png",
    companion_app.FRAME_PREVIEW_ROUTE_PREFIX + "white.png",
    _NOT_FOUND_PATH,
)

_UNAUTH_POST_REQUESTS = (
    companion_app.LOGIN_ROUTE,
    companion_app.SETTINGS_ROUTE,
    companion_app.POLL_ROUTE,
    companion_app.QUICK_DISPLAY_ROUTE,
    companion_app.QUICK_QUIET_HOURS_ROUTE,
    companion_app.QUICK_LED_ROUTE,
    companion_app.THEME_ROUTE,
    companion_app.LANG_ROUTE,
    companion_app.LOGOUT_ROUTE,
    airlines_page.RESOLVE_ROUTE,
    airlines_page.MANUAL_DELETE_ROUTE_PREFIX + "RYR" + airlines_page.MANUAL_DELETE_ROUTE_SUFFIX,
    companion_app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + "air-france.png",
    companion_app.RULES_ADD_ROUTE,
    companion_app.CALENDAR_DISCONNECT_ROUTE,
    companion_app.CALENDAR_CONNECT_ROUTE,
    companion_app.UPDATE_INSTALL_ROUTE,
    companion_app.UPDATE_CANCEL_ROUTE,
    companion_app.RULES_DELETE_ROUTE_PREFIX + "callsign/AFR" + companion_app.RULES_DELETE_ROUTE_SUFFIX,
    _NOT_FOUND_PATH,
)

UNAUTH_REQUESTS = tuple(("GET", path) for path in _UNAUTH_GET_REQUESTS) + tuple(
    ("POST", path) for path in _UNAUTH_POST_REQUESTS)

# Never a real credential: capture_unauthenticated()'s one POST /login
# sample records today's failed-login response (401), which requires a
# password that does not match the test server's own configured one.
_WRONG_PASSWORD = "wrong-password-for-baseline-capture-only"

# See the module docstring: data-refresh-token folds in a filesystem
# ctime no syscall can back-date, so it can never be reproduced across
# two independent temporary state directories. Normalised to a fixed
# placeholder before a page body is stored or compared — the one
# regex-based normalisation this module performs.
_TOKEN_RE = re.compile(r'data-refresh-token="[0-9a-f]{32}"')
_TOKEN_PLACEHOLDER = 'data-refresh-token="normalised-ctime-cannot-be-frozen"'


def _normalise_body(body_text):
    return _TOKEN_RE.sub(_TOKEN_PLACEHOLDER, body_text)


@contextmanager
def frozen_clock(now_iso=FROZEN_NOW):
    """Pin every render-time clock read (see the module docstring's list)
    to `now_iso` for the duration of the block, restoring each on exit
    even if the block raises. Plain save/restore of module attributes —
    works both under pytest and from `main()`'s bare script context.
    """
    frozen_dt = datetime.fromisoformat(now_iso)
    frozen_epoch = frozen_dt.timestamp()

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_dt if tz is None else frozen_dt.astimezone(tz)

    original_utc_now_iso = history_db.utc_now_iso
    original_time_time = time.time
    original_health_datetime = health_sections.datetime
    history_db.utc_now_iso = lambda: now_iso
    time.time = lambda: frozen_epoch
    health_sections.datetime = _FrozenDatetime
    try:
        yield frozen_dt
    finally:
        history_db.utc_now_iso = original_utc_now_iso
        time.time = original_time_time
        health_sections.datetime = original_health_datetime


def seed_snapshot_state(state_dir, now_iso):
    """Deterministic state through the server's own write APIs, anchored
    to `now_iso`: flights in history within the last day, device health
    readings spanning the battery-trend window (the newest one AT
    `now_iso` itself, doubling as the device's last check-in), one
    unresolved callsign prefix, a connected calendar registry with a
    real entry and a recent `last_synced_at`, one colour rule, and one
    manual resolution.
    """
    now_dt = datetime.fromisoformat(now_iso)
    runway_ids = device_config.RUNWAY_IDS
    theme_ids = device_config.THEME_IDS

    with history_db.open_db(state_dir) as conn:
        # 24 runway events over the last 20 hours — "within the last day".
        step = timedelta(hours=20) / 24
        for i in range(24):
            ts = now_dt - timedelta(hours=20) + step * i
            history_db.record_runway_event(
                conn,
                ts=ts.isoformat(),
                hex="39%04x" % (0x9000 + i),
                callsign="AFR%03d" % (100 + i),
                aircraft_type="A320",
                confirmed_state="confirmed",
                corroborated=(i % 3 != 0),
                route_source="adsb" if i % 2 == 0 else "schedule",
                airline="Air France",
                origin="LFPO",
                destination="LFPG",
                tracked_runway=runway_ids[i % len(runway_ids)],
            )

        # 41 daily battery readings, the newest at now_iso itself.
        for day in range(40, -1, -1):
            ts = now_dt - timedelta(days=day)
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=4200 - day * 3,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")

    device_config.save_device_config(
        state_dir, theme=theme_ids[0], tracked_runway=runway_ids[0],
        wake_interval_s=300, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00",
        display_enabled=True,
    )

    # One unresolved prefix, so Health's registry renders its First/Last
    # seen cells.
    state_store.save_poll_state(state_dir, {"unresolved_prefixes": {
        "TVF": {
            "count": 5, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "TVF123",
        },
    }})

    # One manual resolution.
    manual_resolutions.add_entry(state_dir, "RYR", "Ryanair", now=now_iso)

    # One colour rule.
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_PREFIX, "AFR", theme_ids[0], now=now_iso)

    # A connected calendar: save_calendar_url() erases the registry as
    # part of staging the secret, so the real entry is written after it,
    # never before.
    calendar_rules.save_calendar_url(
        state_dir, "https://example.invalid/roster.ics", now=now_dt.timestamp())
    entry_start = now_dt + timedelta(hours=3)
    entry_end = entry_start + timedelta(hours=2)
    calendar_rules.write_calendar_registry(
        state_dir,
        [{
            "airline_iata": "AF",
            "origin_iata": "ORY",
            "destination_iata": "NCE",
            "start_at": entry_start.timestamp(),
            "end_at": entry_end.timestamp(),
        }],
        last_attempt_at=now_dt.timestamp(),
        last_synced_at=(now_dt - timedelta(minutes=12)).isoformat(timespec="seconds"),
        now=now_dt.timestamp(),
    )


def _cookie_header(session_cookie, lang, theme):
    parts = []
    if session_cookie:
        parts.append(session_cookie)
    parts.append("%s=%s" % (auth.UI_LANG_COOKIE_NAME, lang))
    parts.append("%s=%s" % (auth.UI_THEME_COOKIE_NAME, theme))
    return "; ".join(parts)


def capture_pages(server, cookie):
    """{"<path>|<lang>|<theme>": {"status": int, "body": str}} for every
    PAGE_REQUESTS entry, across both LANGS and both THEMES. The login
    entry (needs_session=False) carries no session cookie — its own
    "unauthenticated" served HTML is genuinely part of the baseline.
    """
    pages = {}
    origin_header = {"Origin": server.base_url()}
    for path, method, needs_session, form in PAGE_REQUESTS:
        for lang in LANGS:
            for theme in THEMES:
                page_cookie = _cookie_header(
                    cookie if needs_session else None, lang, theme)
                if method == "GET":
                    status, _headers, body = companion_app_server.http_request(
                        server.url(path), cookie=page_cookie)
                else:
                    data = urllib.parse.urlencode(form or {}).encode()
                    status, _headers, body = companion_app_server.http_request(
                        server.url(path), method="POST", data=data,
                        cookie=page_cookie, extra_headers=origin_header)
                key = "%s|%s|%s" % (path, lang, theme)
                pages[key] = {
                    "status": status,
                    "body": _normalise_body(body.decode("utf-8", "replace")),
                }
    return pages


def capture_unauthenticated(server):
    """{"METHOD path": {"status": int, "location": str|None}} for every
    UNAUTH_REQUESTS sample, issued with no cookie and redirects not
    followed. The one POST /login sample records today's failed-login
    (wrong-password) response.
    """
    result = {}
    origin_header = {"Origin": server.base_url()}
    for method, path in UNAUTH_REQUESTS:
        if method == "GET":
            status, headers, _body = companion_app_server.http_request(
                server.url(path))
        else:
            if path == companion_app.LOGIN_ROUTE:
                data = urllib.parse.urlencode({"password": _WRONG_PASSWORD}).encode()
            else:
                data = b""
            status, headers, _body = companion_app_server.http_request(
                server.url(path), method="POST", data=data,
                extra_headers=origin_header)
        key = "%s %s" % (method, path)
        result[key] = {"status": status, "location": headers.get("Location")}
    return result


def load_baseline():
    path = os.path.join(REPO_ROOT, BASELINE_RELATIVE_PATH)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_baseline(data):
    path = os.path.join(REPO_ROOT, BASELINE_RELATIVE_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write("\n")


def capture_snapshot(now_iso=FROZEN_NOW):
    """The full {"pages": ..., "unauthenticated": ...} snapshot: a fresh
    temporary state dir, seeded and captured under one frozen clock.
    Shared by `main()` and companion/test_render_baseline.py, so
    generation and verification can never drift apart.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_dir = os.path.join(tmp_dir, "state")
        with frozen_clock(now_iso):
            seed_snapshot_state(state_dir, now_iso)
            server = companion_app_server.InProcessAppServer(state_dir)
            try:
                cookie = companion_app_server.login(server)
                pages = capture_pages(server, cookie)
                unauthenticated = capture_unauthenticated(server)
            finally:
                server.stop()
    return {"pages": pages, "unauthenticated": unauthenticated}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true",
        help="Capture a fresh baseline and overwrite %s" % BASELINE_RELATIVE_PATH)
    args = parser.parse_args()
    if not args.write:
        parser.error("nothing to do without --write")
    write_baseline(capture_snapshot())
    print("wrote %s" % os.path.join(REPO_ROOT, BASELINE_RELATIVE_PATH))


if __name__ == "__main__":
    main()
