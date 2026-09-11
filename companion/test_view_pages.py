#!/usr/bin/env python3
"""Contract harness for companion/pages/history_page.py (CFG-06/CFG-10/
CFG-11) — the page that absorbed companion/pages/preview_page.py's entire
live-panel/render-gallery content in 06.6.4.1-05; that module itself was
deleted outright by 06.6.4.1-08 (D-22) once its standalone /preview page
route became a plain redirect to History.

Covers: the flight-history log's empty state, newest-first row ordering,
the two reused render-module presentation mappings (friendly aircraft-
type labels with a raw-designator fallback, the display-airline alias),
route-unavailable wording agreement with server/plane/render.py's own
ROUTE_FALLBACK_TEXT, monospace column styling, per-cell escaping
(including a markup-shaped callsign), degrade-not-raise behaviour
against an unreadable database; quick task 260903-etm's retirement of
History's top-of-page render-gallery <section> outright (developer
redirection superseding quick task 260903-c4o's own always-visible
render-gallery section on this same unmerged branch) — that the section
is fully absent (zero <h2, zero page-section, zero gallery-grid/
gallery-tile) both with seeded gallery content and with an empty
gallery, that the per-row View-panel mechanism and History's own card
disclosures survive in the same render, that the gallery filename-
timestamp helper degrades safely, the per-row View-panel lookup and
shared lightbox including a native title tooltip byte-equal to the
trigger's aria-label, that the orphaned colour caveat is rehomed into
the lightbox note exactly once, the unresolved-airline link to Health;
and one end-to-end HTTP round trip proving companion/app.py's router and
this page module agree, including a real PNG fetched over
/gallery/{name}.png (the route the per-row lightbox links to,
/preview.png having been retired outright by quick task 260903-c4o and
now 404ing) and the retired /preview page route's redirect to /history.

Every fixture is seeded programmatically into a temporary state
directory - flight events via server/history_db.py's own writer
functions, a real panel.bin via server.plane.render.render_panel(), and
gallery files as small real PNGs via Pillow - never a committed fixture
file, so this harness cannot drift from the schema/format those modules
define.

Stdlib-only, plus the modules under test (server.plane.render,
server.history_db) and Pillow - Pillow is a hard dependency of the
render pipeline this harness seeds fixtures through, so this harness
must be run under server/.venv's interpreter, not the bare system
python3. No pytest.

Usage:
    server/.venv/bin/python3 companion/test_view_pages.py
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth  # noqa: E402
import companion.battery as battery  # noqa: E402
import companion.layout as layout  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import render as panel_render  # noqa: E402

TEST_PASSWORD = "view-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 70  # 67 + 3 (19-03-PLAN.md Task 1: A-36/D-19's 7->6 column drop and
# clock-only Timestamp cell — retargeted the .data-table-wrap exact-match and 7-column checks in
# place, plus 3 new checks: the runway survives in the <tr title>/mobile details, the scroller is
# focusable and named, and the desktop Timestamp cell drops its relative-age suffix) — was 67
# 67 = 65 + 2 (19-01-PLAN.md Task 1: D-01's battery_percent() move — the
# retargeted battery.battery_percent() check, plus the two new boundary checks proving the
# function is gone from home_page and that companion/battery.py imports neither companion.pages
# nor server) — was 65
# 65 = 63 + 2 (phase 18: Home page) — was 63 # + 8 (phase 14 plan 14-05 Task 2: 8 new
# source-content checks pinning panel-lookup.js's own contract without a
# live DOM - no image.src="" anywhere; image.removeAttribute("src") is
# conditional, not unconditional at module scope; the shared populate
# function (openFromTrigger) is defined exactly once and called from at
# least two sites; location.search is read exactly once, at script init,
# outside any click-only-reachable function; every one of the eleven new
# data-view-panel-* attribute name literals appears in the file's source;
# the mode-governed elements' hidden assignments all occur, textually,
# before the shared function's own showModal() call; evt.preventDefault()
# appears exactly once, positioned after the trigger-null-check and
# before any showModal()-reaching call; and exactly one
# document.getElementById("panel-lookup-dialog")/document.addEventListener
# ("click", ...) pair still exists) = 63.
# 55 = 54 + 1 (phase 14 plan 14-01 Task 2: the new
# reflection-driven _view_panel_attr_constants_all_classified() check -
# _lightbox_dom_contract_three_file_guard() itself was restructured onto
# three classified token tuples in place, still one check) = 55.
# 54 = 52 + 2 (quick 260903-peo Task 3: UIR-17's desktop
# copy-button reveal stylesheet contract — [data-copy-value]-scoped, opacity
# + pointer-events only, both tr:hover/tr:focus-within named — and the
# cross-file markup guard pinning the [data-copy-value] discriminator that
# keeps the View-panel/eye button always visible)
# 52 = merge origin/main into
# claude/history-preview-gallery-32b974 (2026-09-03): this branch forked
# from main at 49 (46 + 3, quick task 260902-w4t, see below) and made a
# net +0 change of its own on top (quick task 260903-c4o +1 -> 50, quick
# task 260903-etm -5+4 -> 49 - see below for both). Independently, main
# went from that same 49 to 52 (+1 quick task 260902-v26, +2 quick task
# 260903-btu - both entirely absent from this branch until now). Net:
# 49 + 0 (this branch) + 3 (main) = 52.
#
# --- this branch's own history since the 49 fork point ---
# 49 = 50 - 5 (quick task 260903-etm: History's
# top-of-page render-gallery <section> retired outright, superseding
# quick task 260903-c4o's own always-visible section on this same
# unmerged branch - _render_gallery_nonempty_structure,
# _render_gallery_empty_state, _render_gallery_not_a_disclosure and
# _render_gallery_display_limit_newest_first all asserted structure that
# no longer exists, and _recent_renders_malformed_filename_caption_
# fallback's tile-class subject was deleted with the section - its
# residual "a malformed filename degrades safely" coverage already lives
# in _gallery_name_to_iso_fixtures and in nearest_gallery_entry()'s own
# unparseable-entry-is-skipped fixture) + 4 (quick task 260903-etm's
# replacement checks: _history_render_gallery_section_absent_with_content,
# _history_render_gallery_section_absent_when_empty,
# _view_panel_trigger_title_matches_aria_label,
# _colour_caveat_rehomed_into_lightbox_note).
# Deliberately KEPT rather than replaced, despite living among the
# retired group: _render_gallery_no_preview_apparatus_even_with_panel_file
# - every one of its assertions still passes unmodified, and its real
# subject is quick task 260903-c4o's /preview.png route retirement, not
# the render-gallery section this task removes; only its check()
# description prose was refreshed.
# 50 = quick task 260903-c4o's own tip on this same branch, +1 from the
# same 49 fork point below.
#
# --- main's own history since the same 49 fork point ---
# 52 = 47 + 5 (quick task 260902-w4t Task 3, UIR-04:
# _status_dot_title_backward_compatible_and_escaped,
# _corroboration_none_row_shows_short_label_with_tooltip, and
# _data_table_wrap_scroll_edge_affordance_css - status_dot()'s new
# backward-compatible title parameter, the shortened corroboration
# label's tooltip in both renderings, and the CSS-only scroll-edge
# affordance's background-attachment/pointer-events contract; Task 2,
# UIR-06: _hex_only_row_promotes_hex_to_primary - a callsign-less row
# with a hex promotes the hex into the primary slot on both the desktop
# cell and the mobile card, with a no-copy-button "no callsign" note,
# and a row with neither callsign nor hex renders without raising;
# Task 1, UIR-05: _airline_fallback_distinct_from_route_fallback - a
# no-airline row's AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT are
# distinct strings in distinct columns, and the unresolved-link's
# UNRESOLVED_LINK_CLASS is styled in style.css and present on the
# rendered anchor - all three merged in from main, additive to this
# branch's own chain below, zero overlap in the checks each side added).
# 47 = 44 + 1 (quick task 260902-v26 Task 3: render({}) with a
# literal empty dict still contains the .illustration-grid gallery
# container, pinning the ctx.get("state_dir") tolerance render(ctx) grew
# in this task) + 2 (quick task 260903-btu Task 4: a real, seeded
# history_page.render() call carries zero replace-related markup, and
# the two new Airlines-only lightbox constants each appear in
# panel-lookup.js/airlines_page.render()/style.css and never in a real
# history_page.render() call — _lightbox_dom_contract_three_file_guard()
# and _airlines_lightbox_constants_match_history() themselves were left
# unmodified, since their existing tokens/pairs are all still true).
# 44 = 43 + 1 (quick task 260902-tli Task 2: the
# airlines_page/history_page cross-module LIGHTBOX_DIALOG_ID/
# _VIEW_PANEL_*_ATTR equality guard. _lightbox_dom_contract_three_file_
# guard() was widened in place to also assert the six shared tokens
# against a real airlines_page.render() output - no count change from
# that retarget) + 1 (quick task 260902-v26 Task 3: render({}) with a
# literal empty dict still contains the .illustration-grid gallery
# container, pinning the ctx.get("state_dir") tolerance render(ctx) grew
# in this task) + 2 (quick task 260903-btu Task 4: a real, seeded
# history_page.render() call carries zero replace-related markup, and
# the two new Airlines-only lightbox constants each appear in
# panel-lookup.js/airlines_page.render()/style.css and never in a real
# history_page.render() call — _lightbox_dom_contract_three_file_guard()
# and _airlines_lightbox_constants_match_history() themselves were left
# unmodified, since their existing tokens/pairs are all still true).
# 43 = 06.6.4.1-08 Task 3: 56 - 16 (Section 2's whole
# companion/pages/preview_page.py-specific test section deleted outright —
# the module itself is deleted, and every one of its 16 checks either has
# a live History-side equivalent already (plan 05) or was carried over
# onto history_page.py's absorbed symbols below) + 3 (2 carried-over
# checks the History side did not already have — _gallery_name_to_iso()'s
# degrade-safely fixtures, and a malformed gallery filename's
# caption-fallback rendering in the Recent-renders disclosure — plus 1
# new check pinning that a View-panel trigger still carries non-empty
# <svg icon markup after the nav shrink) = 43. Section 3's end-to-end
# check was retargeted in place (still 1 check, not counted as new) to
# assert the /preview -> /history redirect instead of a 200/"Preview"
# heading, while still proving /preview.png (untouched) returns a real
# PNG. # 56 = 51 (pre-06.6.4.1-05 Task 3) + 5 (06.6.4.1-05
# Task 3: the unresolved-airline link absent for a resolved airline,
# present exactly once per representation for an unresolved airline,
# keyed on the airline label and not the route label, its href matching
# health_page.SERVER_DATA_SECTION_ID, and no prefix-registry table
# duplicated onto History). Prior baseline: 47 (pre-06.6.4.1-05 Task 2) +
# 4 (06.6.4.1-05 Task 2: nearest_gallery_entry()'s at-or-before/boundary/skip/None
# behaviour; three interleaved rows' desktop+mobile View-panel triggers
# carrying byte-identical, correctly-targeted attributes plus exactly one
# lightbox dialog; zero triggers/zero dialog with an empty gallery entry
# list; the LIGHTBOX_DIALOG_ID/data-view-panel-*/lightbox__* three-file
# DOM-contract guard). Prior baseline: 42 (pre-06.6.4.1-05) + 5
# (06.6.4.1-05 Task 1: History's own Now-showing section with a panel
# present/absent, the Recent-renders disclosure closed by default with a
# correct shown-count summary, the same disclosure's empty-gallery
# no-renders empty state, and confirmation that Preview's page-level
# freshness apparatus (data-loaded-at/data-stale-banner) was deliberately
# not ported). Prior baseline: 41 (pre-06.6.4-05) + 1 (06.6.4-05 Task 3: the
# shared [data-filter-clear] Clear-control contract - History renders the
# attribute, style.css styles it by attribute, no class-keyed rule
# competes). Prior baseline: 35 (pre-06.6.3-07) + 6 (06.6.3-07 Task 3:
# _gallery_name_to_iso() fixtures; matte-frame/sizing/caption re-asserted
# against the full render() output; no-panel branch stays img/frame-less
# in the full render() output; gallery sizing/links/D-10 window label
# re-asserted against the full render() output; a malformed gallery
# filename's caption-fallback re-asserted against the full render()
# output; Preview's data-loaded-at/data-stale-banner markers). Prior
# baseline: 30 (pre-06.6.3-05) + 5 (06.6.3-05 Task 3: filter bar markers
# present-once; data-filter-text on both representations; desktop
# Callsign+Hex cell's 2 copy buttons + feedback siblings; mobile details
# region's 3 copy buttons + feedback siblings; confirmed_state/
# tracked_runway presentation labels re-asserted against the full
# render() output). Prior baseline: 28 (pre-06.6.2-04) + 2 (06.6.2-04:
# History/Preview page_header() shared component checks). Before that:
# 25 (pre-06.6-03) + 3 (06.6-03 Task 1: History Timestamp column reads
# "ISO (Nm ago)"; Task 2: Preview's Captured caption reads "Captured ISO
# (Nm ago)"; Task 3: corroboration copy cross-page drift guard, D-03)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# --- lightbox DOM-contract token classification (phase 14 plan 14-01 Task 2) ---
#
# _lightbox_dom_contract_three_file_guard() below used to carry a single
# inline `tokens` tuple. That worked while History and the Airlines
# gallery rendered an identical vocabulary, but Airlines-only lightbox
# markup (the replace form) already exists today and this phase is about
# to add more server-rendered vocabulary that panel-lookup.js never
# reads. Restructuring the guard's data into three explicitly-scoped
# tuples, each with its own present/absent contract, lets the guard keep
# growing without ever again silently degrading into "shared" coverage
# for something that is provably not shared.
#
# _view_panel_attr_constants_all_classified() (below, in main()) enforces
# by reflection that every airlines_page._VIEW_PANEL_*_ATTR constant's
# *value* lives in exactly one of these three tuples - a constant left
# out of all three, or placed in two at once, fails the harness by
# construction rather than by someone remembering to update this list.

# Must appear in companion/static/panel-lookup.js's source, in the
# rendered History page, and in the rendered Airlines page - the
# vocabulary every one of the three genuinely shares today.
_LIGHTBOX_SHARED_TOKENS = (
    history_page.LIGHTBOX_DIALOG_ID,
    "data-view-panel-src",
    "data-view-panel-caption",
    "lightbox__image",
    "lightbox__caption",
    "lightbox__note",
    "data-view-panel-close",
)

# Must appear in panel-lookup.js's source and in the rendered Airlines
# page, and must be absent from the rendered History page - History
# deliberately renders no replace form and never should (see
# airlines_page.py's own comment on _VIEW_PANEL_REPLACE_ACTION_ATTR).
#
# Phase 14 plan 14-05 Task 2 promotes every member 14-02 staged in
# _LIGHTBOX_RENDER_ONLY_TOKENS (below, now empty) into this tuple:
# panel-lookup.js now reads every one of the eleven new
# data-view-panel-* attributes and looks up every one of the six new
# dialog classes, and every one of them is, like the replace form
# before it, genuinely Airlines-only - History never renders a
# resolve/gap/manual surface, so none of Phase 14's own new tokens ever
# lands in _LIGHTBOX_SHARED_TOKENS.
_LIGHTBOX_AIRLINES_ONLY_TOKENS = (
    "data-view-panel-replace-action",
    "lightbox__replace",
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
    airlines_page.LIGHTBOX_HEADING_CLASS,
    airlines_page.LIGHTBOX_MANUAL_NOTE_CLASS,
    airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS,
    airlines_page.LIGHTBOX_DELETE_CLASS,
    airlines_page.RESOLVE_CONTEXT_CLASS,
    airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
)

# Server-rendered vocabulary the script does not read yet: asserted
# present in the rendered Airlines page only, with no assertion at all
# against panel-lookup.js. A staging area for one wave at most - plan
# 14-05 Task 2 emptied this back to () by promoting every token it held
# (the eleven new data-view-panel-* attribute values, the four
# new/promoted dialog classes, resolve-context, resolve-upload-zone)
# into _LIGHTBOX_AIRLINES_ONLY_TOKENS above, once panel-lookup.js
# learned to read/look up all of them. Stays empty absent a future wave
# introducing a fourth rendered-but-not-yet-scripted token.
_LIGHTBOX_RENDER_ONLY_TOKENS = ()

# The eleven data-view-panel-* attribute name literals 14-02 added to
# the vocabulary (14-05 Task 2's own check #5) - built from the same
# airlines_page constants already threaded into
# _LIGHTBOX_AIRLINES_ONLY_TOKENS above, never a second hand-copied list.
_NEW_VIEW_PANEL_ATTR_NAMES = (
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
)


def _strip_js_comments(src):
    """Crude but sufficient for this one hand-written file: strips
    /* */ block comments and // line comments so a source-content check
    can search "real code" without a comment's own prose (e.g. an
    explanatory mention of the exact anti-pattern being pinned as
    absent) producing a false positive. Not a full JS tokenizer - does
    not account for either sequence appearing inside a string literal -
    but panel-lookup.js's own actual string literals never contain "//"
    or "/*", so this is safe for this file's real content.
    """
    without_block = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    without_line = re.sub(r"//[^\n]*", "", without_block)
    return without_line


def _read_panel_lookup_source():
    js_path = os.path.join(HERE, "static", "panel-lookup.js")
    with open(js_path) as fh:
        return fh.read()


# --- fixture helpers -----------------------------------------------------


def _mkstate(prefix):
    return tempfile.mkdtemp(prefix="skypane-view-pages-%s-" % prefix)


def _seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for record_runway_event()."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def _write_panel_file(state_dir):
    """A real, production-produced 960,000-byte panel.bin - the same
    bytes server.poll_loop.write_panel_atomic() would write - so the
    preview round trip this harness exercises is against genuine
    production output, not a hand-built fixture.
    """
    os.makedirs(state_dir, exist_ok=True)
    packed = panel_render.render_panel(None, "empty")
    with open(os.path.join(state_dir, "panel.bin"), "wb") as fh:
        fh.write(packed)


def _write_gallery_png(path):
    from PIL import Image
    Image.new("RGB", (4, 4), color=(200, 200, 200)).save(path, format="PNG")


def _seed_gallery(state_dir, names):
    gallery_dir = os.path.join(state_dir, "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    for name in names:
        _write_gallery_png(os.path.join(gallery_dir, name))


def _history_ctx(state_dir, now=None, gallery_entries=None):
    return {
        "state_dir": state_dir,
        "now": now or history_db.utc_now_iso(),
        "gallery_entries": gallery_entries or [],
    }


# --- HTTP harness (Section 3 only) ----------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Structurally identical to companion/test_companion_app.py's own
    Harness class - owns the companion/app.py subprocess lifecycle.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-view-pages-e2e-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def start(self):
        env = dict(os.environ)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "companion/app.py exited early (code %s) before "
                    "accepting connections:\n%s"
                    % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(
            "companion/app.py did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def _login(harness, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ======================================================================
    # Section 1: companion/pages/history_page.py
    # ======================================================================

    def _empty_db_good_news_no_table():
        tmp = _mkstate("h-empty")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if history_page._NO_FLIGHTS_HEADING not in rendered:
                return False, "expected the flight-history empty-state heading"
            if "<table" in rendered:
                return False, "did not expect a <table with zero events"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an empty database renders the flight-history empty-state copy and no <table",
        _empty_db_good_news_no_table)

    def _three_events_newest_first():
        tmp = _mkstate("h-three")
        try:
            events = [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "bbb222", "callsign": "FLT2"},
                {"ts": "2026-08-27T10:02:00+00:00", "hex": "ccc333", "callsign": "FLT3"},
            ]
            _seed_runway_events(tmp, events)
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count("<tr") != 4:  # 1 header row + 3 body rows
                return False, "expected exactly 3 body rows, got %d <tr" % (rendered.count("<tr") - 1)
            idx3 = rendered.find("FLT3")
            idx2 = rendered.find("FLT2")
            idx1 = rendered.find("FLT1")
            if not (idx3 < idx2 < idx1):
                return False, "expected newest-first ordering (FLT3, FLT2, FLT1)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "three seeded runway events render one row each, newest first",
        _three_events_newest_first)

    def _known_aircraft_type_friendly_label():
        tmp = _mkstate("h-known-type")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d1", "aircraft_type": "b738"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_label = panel_render._TYPE_DISPLAY_LABELS["B738"]
            if expected_label not in rendered:
                return False, "expected the friendly label %r for aircraft_type=b738" % expected_label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a known aircraft-type designator renders its friendly label (case-insensitive)",
        _known_aircraft_type_friendly_label)

    def _unknown_aircraft_type_raw_designator():
        tmp = _mkstate("h-unknown-type")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d2", "aircraft_type": "ZZZZ"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if "ZZZZ" not in rendered:
                return False, "expected the raw designator ZZZZ to appear, not an empty cell"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an aircraft type absent from the display-label table renders the raw designator, not an empty cell",
        _unknown_aircraft_type_raw_designator)

    def _no_airline_no_route_matches_render_fallback():
        tmp = _mkstate("h-no-route")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d3", "callsign": "NOROUTE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            # Read the expected string from the render module itself, never a
            # literal, so the History page and the panel cannot silently drift.
            if panel_render.ROUTE_FALLBACK_TEXT not in rendered:
                return False, "expected server.plane.render.ROUTE_FALLBACK_TEXT to appear"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a row with no airline and no route renders the same fallback wording server.plane.render.py uses (read from the module)",
        _no_airline_no_route_matches_render_fallback)

    def _mono_columns_present():
        # 06.6.1-02: the merged Callsign+Hex cell moved its monospace
        # treatment off a td[class="mono"] attribute and onto the
        # cell-primary/cell-secondary span classes (both mono in
        # style.css) - a plain "mono" attribute on the merged <td> would
        # fight the 12px secondary size, per _merged_cell()'s docstring.
        # Timestamp is the one remaining td[class="mono"] cell; callsign
        # and hex are asserted via the merged-cell span classes instead.
        tmp = _mkstate("h-mono")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "abc123", "callsign": "MONO1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count('class="mono"') < 1:
                return False, "expected the timestamp cell to carry the monospace CSS class"
            if ('class="%s"' % history_page.CELL_PRIMARY_CLASS) not in rendered:
                return False, "expected the merged-cell primary span to carry its mono CSS class"
            if ('class="%s"' % history_page.CELL_SECONDARY_CLASS) not in rendered:
                return False, "expected the merged-cell secondary span to carry its mono CSS class"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "timestamp, callsign and hex columns carry monospace CSS classes",
        _mono_columns_present)

    def _hostile_callsign_escaped():
        tmp = _mkstate("h-hostile")
        try:
            hostile = "<script>alert(1)</script>"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d4", "callsign": hostile},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if hostile in rendered:
                return False, "an unescaped callsign reached the rendered output"
            if "&lt;script&gt;" not in rendered:
                return False, "expected the escaped form of the hostile callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a callsign containing angle brackets renders escaped",
        _hostile_callsign_escaped)

    def _unreadable_db_degrades_without_raising():
        base = tempfile.mkdtemp(prefix="skypane-view-pages-blocked-")
        blocked_state_dir = os.path.join(base, "blocked")
        try:
            with open(blocked_state_dir, "w") as fh:
                fh.write("this is a file, not a directory")
            rendered = history_page.render(_history_ctx(blocked_state_dir))
            if history_page._HISTORY_UNAVAILABLE_TEXT not in rendered:
                return False, "expected the health-unavailable copy when the database cannot be opened"
            return True, ""
        finally:
            shutil.rmtree(base, ignore_errors=True)
    check(
        "a state directory that cannot hold a database renders the health-unavailable copy without raising",
        _unreadable_db_degrades_without_raising)

    def _history_page_never_imports_html_module():
        with open(os.path.join(HERE, "pages", "history_page.py")) as fh:
            source = fh.read()
        for line in source.splitlines():
            if line.strip() == "import html":
                return False, "history_page.py must never import the stdlib html module directly"
        return True, ""
    check(
        "companion/pages/history_page.py never imports the stdlib html module directly",
        _history_page_never_imports_html_module)

    def _history_page_never_redefines_type_labels():
        with open(os.path.join(HERE, "pages", "history_page.py")) as fh:
            source = fh.read()
        if re.search(r"_TYPE_DISPLAY_LABELS\s*=", source):
            return False, "history_page.py must import _TYPE_DISPLAY_LABELS from the render module, not redefine it"
        return True, ""
    check(
        "companion/pages/history_page.py never redefines _TYPE_DISPLAY_LABELS locally",
        _history_page_never_redefines_type_labels)

    def _history_page_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): History's top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        tmp = _mkstate("h-page-header")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if '<h1 class="page-title">Flights</h1>' not in rendered:
                return False, "expected the page_header()-rendered <h1 class=\"page-title\">History</h1>"
            if '<h1 class="text-heading">' in rendered:
                return False, "expected no bare <h1 class=\"text-heading\"> heading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History opens with the shared layout.page_header() component, not a bare <h1>",
        _history_page_opens_with_shared_page_header)

    def _history_table_wrapped_for_horizontal_scroll_dot_survives():
        # D-03/D-22 regression pin: History's own hand-built table gained
        # the same .data-table-wrap horizontal-scroll wrapper Airlines and
        # Health already had (mirrors test_companion_app.py's
        # _data_table_wrapped_for_horizontal_scroll() check for
        # layout.data_table() itself), and the Corroboration cell's
        # unescaped status_dot() embedding must survive the wrap untouched.
        tmp = _mkstate("h-wrap")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d5", "callsign": "WRAP1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            # A-36/D-19: the wrapper now also carries tabindex/role/
            # aria-label (see the scroller-focusable checks below), so
            # this can no longer be an exact-tag match — the substring
            # keeps checking the same wrapper class is still present.
            if '<div class="data-table-wrap"' not in rendered:
                return False, "expected the flight table to be wrapped in .data-table-wrap"
            if '<table class="data-table">' not in rendered:
                return False, "expected the .data-table itself to still be present"
            if "dot--" not in rendered:
                return False, "expected the Corroboration cell's status_dot() dot class to survive the wrap"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's flight table gains the .data-table-wrap horizontal-scroll wrapper Airlines/Health already have, without disturbing the Corroboration status dot",
        _history_table_wrapped_for_horizontal_scroll_dot_survives)

    def _six_columns_named_and_ordered():
        # A-36/D-19: proves the 7->6 column reduction shipped (the
        # Runway column dropped) - the header labels come from
        # history_page._HEADERS itself (the contract), not a re-typed
        # literal list. Was _seven_columns_named_and_ordered() /
        # 06.6.1-02 (D-02)'s own 9->7 pin before this task's drop.
        tmp = _mkstate("h-6col")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d6", "callsign": "SEVEN1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            th_count = len(re.findall(r"<th>", rendered))
            if th_count != 6:
                return False, "expected exactly 6 <th> cells, got %d" % th_count
            positions = []
            for header in history_page._HEADERS:
                idx = rendered.find("<th>%s</th>" % header)
                if idx == -1:
                    return False, "expected header %r to appear as a <th>" % header
                positions.append(idx)
            if positions != sorted(positions):
                return False, "expected the 6 headers in history_page._HEADERS' own left-to-right order"
            if "<th>Hex</th>" in rendered or "<th>Airline</th>" in rendered:
                return False, "did not expect standalone Hex/Airline header cells after the merge"
            if "<th>Runway</th>" in rendered:
                return False, "did not expect a standalone Runway header cell after A-36/D-19's drop"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History renders exactly the 6 headers in history_page._HEADERS, in order, with no standalone Hex/Airline/Runway column (A-36/D-19)",
        _six_columns_named_and_ordered)

    def _runway_survives_in_row_title_and_mobile_details():
        # A-36/D-19: the dropped Runway column's value must survive
        # somewhere - the desktop <tr>'s title attribute, and the
        # mobile card's existing <dt>Runway</dt> disclosure row (which
        # this task deliberately leaves untouched).
        tmp = _mkstate("h-runway-title")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "rwt01",
                    "callsign": "RWTITLE", "tracked_runway": "3",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            runway_label = device_config.runway_label("3")
            # A plain regex, not the shared _row_block() helper (defined
            # later in this function's own source order — a nested def
            # is only bound once execution reaches it, and this check
            # runs earlier): its capture starts AFTER the opening tag's
            # own ">", so it cannot see an attribute on the <tr> itself
            # (only its inner content) - the title lives on the tag, so
            # match the whole opening tag directly instead.
            tr_tag_match = re.search(
                r'<tr[^>]*data-filter-group="0"[^>]*>', rendered)
            li_match = re.search(
                r'<li[^>]*data-filter-group="0"[^>]*>(.*?)</li>', rendered, re.S)
            if tr_tag_match is None or li_match is None:
                return False, "could not locate row block for data-filter-group=0"
            tr_tag = tr_tag_match.group(0)
            li_block = li_match.group(1)
            if ('title="%s"' % layout.escape_html(runway_label)) not in tr_tag:
                return False, "expected the desktop <tr> to carry the runway in its title attribute"
            if "<dt>Runway</dt><dd>%s</dd>" % layout.escape_html(runway_label) not in li_block:
                return False, "expected the mobile card's More details to still show Runway"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the runway value the dropped desktop Runway column used to show survives in the "
        "<tr title=\"...\"> attribute and, unchanged, in the mobile card's More details (A-36/D-19)",
        _runway_survives_in_row_title_and_mobile_details)

    def _scroller_focusable_and_named():
        # A-36/D-19: a keyboard user must be able to Tab to the
        # .data-table-wrap scroller and arrow-scroll it - tabindex="0"
        # plus a non-empty accessible name (aria-label).
        tmp = _mkstate("h-scroller")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "scr01", "callsign": "SCROLL1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            wrap_match = re.search(r'<div class="data-table-wrap"([^>]*)>', rendered)
            if wrap_match is None:
                return False, "expected a .data-table-wrap opening tag"
            attrs = wrap_match.group(1)
            if 'tabindex="0"' not in attrs:
                return False, "expected the scroller to carry tabindex=\"0\""
            if 'role="region"' not in attrs:
                return False, "expected the scroller to carry role=\"region\""
            aria_match = re.search(r'aria-label="([^"]*)"', attrs)
            if aria_match is None or not aria_match.group(1):
                return False, "expected the scroller to carry a non-empty aria-label"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the .data-table-wrap scroller is focusable (tabindex=\"0\") and carries a non-empty "
        "aria-label naming what it scrolls (A-36/D-19)",
        _scroller_focusable_and_named)

    def _desktop_timestamp_cell_clock_only_no_relative_age():
        # A-36/D-19: the desktop Timestamp cell must drop the relative-
        # age suffix layout.concise_timestamp_html() adds (that suffix
        # is what made the column too wide) while still carrying the
        # full ISO string in a title attribute.
        tmp = _mkstate("h-clock-only")
        try:
            raw_ts = "2026-08-27T10:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": raw_ts, "hex": "clk01", "callsign": "CLOCK1"},
            ])
            now = "2026-08-27T10:05:00+00:00"
            rendered = history_page.render(_history_ctx(tmp, now=now))
            # Inlined rather than the shared _row_block() helper, which
            # is defined later in this function's source order.
            tr_match = re.search(
                r'<tr[^>]*data-filter-group="0"[^>]*>(.*?)</tr>', rendered, re.S)
            if tr_match is None:
                return False, "could not locate row block for data-filter-group=0"
            tr_block = tr_match.group(1)
            if "title=\"%s\"" % layout.escape_html(raw_ts) not in tr_block:
                return False, "expected the full ISO timestamp in a title attribute"
            if " ago" in tr_block:
                return False, "did not expect a relative-age suffix (\" ago\") in the desktop row"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop Timestamp cell shows a local clock with no relative-age suffix, and the "
        "full ISO timestamp still lives in a title attribute (A-36/D-19)",
        _desktop_timestamp_cell_clock_only_no_relative_age)

    def _merged_values_survive_in_same_cell():
        # The merge removed *columns*, not *data* - and both halves must
        # land inside the same <td>, which a count-only check cannot prove.
        tmp = _mkstate("h-merge-data")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "39d301",
                    "callsign": "AFR123", "aircraft_type": "A320",
                    "airline": "AFR",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_type_label = panel_render._TYPE_DISPLAY_LABELS.get("A320", "A320")
            expected_airline_label = panel_render.display_airline_name("AFR")
            for value in ("AFR123", "39d301", expected_type_label, expected_airline_label):
                if value not in rendered:
                    return False, "expected merged value %r to still appear somewhere" % value
            # Scope the same-<td> check to the desktop table's <tbody> -
            # the mobile card representation (06.6.3-05) also renders
            # "AFR123" earlier in the document (the primary line's
            # <span>, outside any <td>), so a whole-document .find()
            # would locate that occurrence instead of the table's.
            tbody_match = re.search(r"<tbody>(.*)</tbody>", rendered, re.S)
            if not tbody_match:
                return False, "expected a <tbody> element in the rendered table"
            tbody = tbody_match.group(1)
            idx = tbody.find("AFR123")
            td_start = tbody.rfind("<td>", 0, idx)
            td_end = tbody.find("</td>", idx)
            if idx == -1 or td_start == -1 or td_end == -1:
                return False, "could not locate the callsign's enclosing <td>"
            cell = tbody[td_start:td_end]
            if "39d301" not in cell:
                return False, "expected the hex value inside the same <td> as the callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the callsign and hex merged values both appear, inside the same <td>",
        _merged_values_survive_in_same_cell)

    def _merged_cells_stay_one_line():
        # Row-height contract (Variant A guard, data-density.md's "What to
        # Avoid"): the merged cells must stay on one line - Variant A
        # ("Stacked cells") was rejected specifically because a taller row
        # works against fast scanning. A future two-line "improvement"
        # must fail this check, not read as progress.
        tmp = _mkstate("h-oneline")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d7", "callsign": "LINE1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tbody_match = re.search(r"<tbody>(.*)</tbody>", rendered, re.S)
            if not tbody_match:
                return False, "expected a <tbody> element in the rendered table"
            tbody = tbody_match.group(1)
            if "<br" in tbody:
                return False, "did not expect a <br> inside the table body (one-line cell contract)"
            if "<div" in tbody or "<p " in tbody:
                return False, "did not expect a block-level element inside a <td> (one-line cell contract)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the merged Callsign/Hex and Type/Airline cells stay on one line - no <br>, no block-level child",
        _merged_cells_stay_one_line)

    def _merged_cell_hostile_values_escaped():
        tmp = _mkstate("h-merge-hostile")
        try:
            hostile_callsign = '<b>AFR"1</b>'
            hostile_hex = '<i>39"d</i>'
            hostile_type = '<u>A32"0</u>'
            hostile_airline = '<s>AFR"L</s>'
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": hostile_hex,
                    "callsign": hostile_callsign, "aircraft_type": hostile_type,
                    "airline": hostile_airline,
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for raw in (hostile_callsign, hostile_hex, hostile_type, hostile_airline):
                if raw in rendered:
                    return False, "an unescaped merged-cell value reached the rendered output: %r" % raw
            if "&lt;" not in rendered:
                return False, "expected at least one escaped '<' from the hostile merged-cell fixtures"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "hostile values in both merged cells (Callsign/Hex, Type/Airline) render escaped",
        _merged_cell_hostile_values_escaped)

    def _merged_cell_classes_agree_with_stylesheet():
        # Cross-file drift guard (same pattern 06.5-02 established for the
        # Python/CSS/JS trio): if history_page.py's class constants
        # (cell-primary, cell-secondary, cell-inline-sep) and style.css's
        # selectors ever diverge, the merged cells silently render as
        # unstyled plain text instead of failing loudly. Read by symbol
        # below (history_page.CELL_*_CLASS), never re-typed as literals.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        for name in (
            history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
            history_page.CELL_SEPARATOR_CLASS,
        ):
            if name not in css:
                return False, "class %r is emitted by history_page but not styled in style.css" % name
        tmp = _mkstate("h-class-agree")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d8", "callsign": "CLS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for name in (
                history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
                history_page.CELL_SEPARATOR_CLASS,
            ):
                if ('class="%s"' % name) not in rendered:
                    return False, "expected class %r to appear in the rendered History page" % name
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "history_page's CELL_PRIMARY_CLASS/CELL_SECONDARY_CLASS/CELL_SEPARATOR_CLASS all appear in style.css and in the rendered page",
        _merged_cell_classes_agree_with_stylesheet)

    def _timestamp_column_absolute_and_relative():
        # D-09 (06.6.3-05): History's Timestamp column/mobile primary
        # line now read through the shared
        # companion.layout.concise_timestamp_html() helper instead of
        # the old bare "ISO (Nm ago)" text - reads the expected markup
        # from the layout module itself, never a hand-typed literal, so
        # the two cannot silently diverge.
        tmp = _mkstate("h-ts-relative")
        try:
            seeded_ts = "2026-08-28T13:58:02+00:00"
            three_min_later = "2026-08-28T14:01:02+00:00"
            _seed_runway_events(tmp, [
                {"ts": seeded_ts, "hex": "d9", "callsign": "TS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp, now=three_min_later))
            expected = layout.concise_timestamp_html(seeded_ts, three_min_later)
            if expected not in rendered:
                return False, "expected %r in the rendered History page" % expected

            # A one-argument format_event_row() call degrades to the raw
            # stored timestamp, unchanged — no hypothetical existing
            # caller that hasn't been updated to pass `now` breaks.
            one_arg = history_page.format_event_row({"ts": seeded_ts})
            if one_arg["ts"] != seeded_ts:
                return False, (
                    "expected a one-argument format_event_row() call to "
                    "return the raw timestamp unchanged, got %r" % one_arg["ts"])

            # A row with no stored timestamp still produces an empty
            # Timestamp cell, not the shared helper's "no reading yet"
            # default.
            no_ts = history_page.format_event_row({}, three_min_later)
            if no_ts["ts"] != "":
                return False, (
                    "expected a missing timestamp to render an empty "
                    "cell, got %r" % no_ts["ts"])

            # render(ctx) with no "now" key still renders without raising
            # and still shows a relative suffix (falls back to
            # history_db.utc_now_iso()).
            rendered_no_now = history_page.render({"state_dir": tmp})
            if " ago)" not in rendered_no_now:
                return False, (
                    "expected a relative-age suffix even when ctx carries "
                    "no 'now' key (render() must fall back to "
                    "history_db.utc_now_iso())")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Timestamp column/mobile primary line read through layout.concise_timestamp_html(), format_event_row() degrades gracefully with one argument or a missing timestamp, and render() falls back when ctx carries no 'now' key",
        _timestamp_column_absolute_and_relative)

    def _corroboration_copy_agrees_with_health_page():
        # D-03, restated by quick task 260902-w4t (UIR-04): History's
        # "None" (single-source) label was shortened to "Single-source"
        # to fix an overlong Corroboration column, so the two pages'
        # visible labels are now DELIBERATELY allowed to diverge for
        # that one key - health_page._CORROBORATION_ROWS still carries
        # the long form as ITS OWN visible label by design. This guard
        # is restated, not weakened, to keep asserting everything that
        # must still agree: statuses agree key-by-key for all three
        # states; visible labels are still identical for True/False (the
        # two keys this task did not touch); and for None, History's
        # visible label must be the short form AND
        # history_page._CORROBORATION_TITLES["None"] (the tooltip) must
        # equal Health's full label exactly, so a future edit to
        # Health's copy still fails this check loudly instead of
        # silently going stale in History's tooltip.
        health_rows = {
            stored: (status, label)
            for stored, label, status, _explanation in health_page._CORROBORATION_ROWS
        }
        history_labels = history_page._CORROBORATION_LABELS
        history_titles = history_page._CORROBORATION_TITLES

        if set(health_rows) != {"True", "None", "False"}:
            return False, "expected health_page._CORROBORATION_ROWS to cover exactly True/None/False"
        if set(history_labels) != {"True", "None", "False"}:
            return False, "expected history_page._CORROBORATION_LABELS to cover exactly True/None/False"

        # Statuses must agree key-by-key for all three states.
        for key in ("True", "None", "False"):
            if history_labels[key][0] != health_rows[key][0]:
                return False, (
                    "corroboration status drifted for %r: history_page has %r, "
                    "health_page has %r" % (key, history_labels[key][0], health_rows[key][0]))

        # Visible labels must still be identical for True/False.
        for key in ("True", "False"):
            if history_labels[key][1] != health_rows[key][1]:
                return False, (
                    "corroboration label drifted for %r: history_page has %r, "
                    "health_page has %r" % (key, history_labels[key][1], health_rows[key][1]))

        # None: History's visible label is the documented short form...
        if history_labels["None"][1] != "Single-source":
            return False, (
                "expected history_page's 'None' visible label to be the short form "
                "'Single-source', got %r" % (history_labels["None"][1],))
        # ...and its tooltip carries Health's full label exactly, so a
        # future edit to Health's copy fails this check, not silently.
        if history_titles.get("None") != health_rows["None"][1]:
            return False, (
                "expected history_page._CORROBORATION_TITLES['None'] to equal "
                "health_page's 'None' visible label %r, got %r"
                % (health_rows["None"][1], history_titles.get("None")))

        # D-03/D-15: the single-source, uncorroborated "None" state is a
        # genuinely unknown state, not a failure — it must stay "ok" in
        # both tables, never a warning or an error.
        if history_labels["None"][0] != "ok":
            return False, "expected history_page's 'None' (single-source) status to be 'ok', not a failure"
        if health_rows["None"][0] != "ok":
            return False, "expected health_page's 'None' (single-source) status to be 'ok', not a failure"

        return True, ""
    check(
        "history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS on "
        "status key-by-key and on visible label for True/False; History's shortened 'None' label "
        "is the documented short form and its _CORROBORATION_TITLES tooltip equals Health's own "
        "full label exactly; the single-source 'None' state is never labelled a failure in "
        "either table (quick task 260902-w4t, UIR-04)",
        _corroboration_copy_agrees_with_health_page)

    def _status_dot_title_backward_compatible_and_escaped():
        # quick task 260902-w4t (UIR-04, 3a): status_dot()'s new third
        # `title` parameter must be fully backward-compatible - every
        # pre-existing 2-arg call site's output stays character-for-
        # character identical - and, when supplied, must escape a
        # hostile value the same way `label` already is.
        two_arg = layout.status_dot("ok", "All good")
        if "title=" in two_arg:
            return False, "expected the 2-arg call to emit no title attribute at all"
        three_arg_equivalent = layout.status_dot("ok", "All good", None)
        if three_arg_equivalent != two_arg:
            return False, "expected an explicit title=None to produce byte-identical markup to the 2-arg call"
        titled = layout.status_dot("ok", "All good", "Long form")
        if 'title="Long form"' not in titled:
            return False, "expected a truthy title to appear as an escaped title attribute"
        hostile = layout.status_dot("ok", "All good", "<script>evil()</script>")
        if "<script>" in hostile:
            return False, "expected a hostile title value to be escaped, not rendered raw"
        if "&lt;script&gt;" not in hostile:
            return False, "expected the escaped form of the hostile title value"
        return True, ""
    check(
        "layout.status_dot()'s 2-arg output is unchanged, an explicit title=None is byte-identical "
        "to omitting it, and a truthy title renders as an escaped title attribute "
        "(quick task 260902-w4t, UIR-04)",
        _status_dot_title_backward_compatible_and_escaped)

    # Relocated ahead of its original first use (was defined further down,
    # in Section 1c) so this section's own new UIR-04 check below — the
    # first check in file order that needs it — can call it: Python
    # resolves a nested function's free variables against the enclosing
    # scope at CALL time, not definition time, so a check registered (and
    # immediately invoked by check()) before this def executes would hit
    # "cannot access free variable '_row_block'" even though the name
    # exists later in the same function body. Every later call site is
    # unaffected — this is the same function, only earlier.
    def _row_block(rendered, tag, group_index):
        pattern = r"<%s[^>]*data-filter-group=\"%d\"[^>]*>(.*?)</%s>" % (
            tag, group_index, tag)
        match = re.search(pattern, rendered, re.S)
        return match.group(1) if match else None

    def _corroboration_none_row_shows_short_label_with_tooltip():
        # quick task 260902-w4t (UIR-04): a "None" (single-source) row's
        # Corroboration cell must render the short visible label in BOTH
        # the desktop <td> and the mobile <dd>, with the long form
        # reachable only via a title attribute, in both renderings.
        tmp = _mkstate("h-corrob-none")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cn01", "callsign": "CORNONE",
                 "corroborated": None},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a None-corroboration row"
            long_form = history_page._CORROBORATION_TITLES["None"]
            for label, block in (("desktop", tr_block), ("mobile", li_block)):
                if ">Single-source<" not in block:
                    return False, "expected the short 'Single-source' label visible in the %s row" % label
                if 'title="%s"' % long_form not in block:
                    return False, "expected the long form in a title attribute in the %s row" % label
                # The long form's parenthetical must not appear as separate
                # VISIBLE text - only inside the title attribute value.
                visible_text = re.sub(r'\stitle="[^"]*"', "", block)
                if "(uncorroborated)" in visible_text:
                    return False, "did not expect the parenthetical to appear as visible text in the %s row" % label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a 'None' (single-source) row's Corroboration cell shows the short visible label with the "
        "long form only in a title attribute, in both the desktop and mobile renderings "
        "(quick task 260902-w4t, UIR-04)",
        _corroboration_none_row_shows_short_label_with_tooltip)

    def _data_table_wrap_scroll_edge_affordance_css():
        # quick task 260902-w4t (UIR-04, 3d): the CSS-only, pointer-inert
        # scroll-edge affordance must declare both background-attachment
        # values (local for the covers, scroll for the shadows) and must
        # introduce no pointer-events-blocking overlay anywhere in the
        # stylesheet's .data-table-wrap rule.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule_match = re.search(r"\.data-table-wrap\s*\{([^}]*)\}", css, re.S)
        if rule_match is None:
            return False, "expected a base .data-table-wrap rule in style.css"
        rule_body = rule_match.group(1)
        if "background-attachment" not in rule_body:
            return False, "expected .data-table-wrap to declare background-attachment"
        if "local" not in rule_body or "scroll" not in rule_body:
            return False, "expected .data-table-wrap's background-attachment to declare both local and scroll"
        if "pointer-events" in rule_body:
            return False, "did not expect a pointer-events declaration on .data-table-wrap"
        override_match = re.search(
            r"\.page-section \.data-table-wrap,\s*\n\.battery-trend-section \.data-table-wrap\s*\{([^}]*)\}",
            css, re.S)
        if override_match is None:
            return False, "expected the .page-section/.battery-trend-section .data-table-wrap surface override"
        if "pointer-events" in override_match.group(1):
            return False, "did not expect a pointer-events declaration on the surface override rule"
        return True, ""
    check(
        ".data-table-wrap declares both background-attachment values (local covers, scroll "
        "shadows) and style.css introduces no pointer-events-blocking overlay "
        "(quick task 260902-w4t, UIR-04)",
        _data_table_wrap_scroll_edge_affordance_css)

    def _filter_bar_markers_present_once():
        # D-20: exactly one of each list-filter.js attribute marker,
        # only rendered when there is data to filter (a zero-row page
        # renders no filter bar at all, matching the table/card
        # renderers' own "no chrome with no data" rule).
        tmp = _mkstate("h-filter-bar")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fb01", "callsign": "FB1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for marker in (
                "data-filter-input", "data-filter-count", "data-filter-clear",
                "data-filter-empty",
            ):
                count = rendered.count(marker)
                if count != 1:
                    return False, "expected exactly one %r marker, got %d" % (marker, count)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's filter bar carries exactly one data-filter-input/-count/-clear/-empty marker each",
        _filter_bar_markers_present_once)

    def _clear_control_shared_attribute_contract():
        # 06.6.4-05 (D-08): History's Clear <button> and Airlines' Clear
        # <a> converge on one shared style.css rule keyed by the
        # [data-filter-clear] attribute both pages already emit, not a
        # new shared class - so a future author adding a class to one
        # page and not the other is exactly how the two Clear controls
        # would silently diverge again. Pins all three legs of that
        # contract: History's rendered output still carries the
        # attribute, style.css styles it via the attribute selector, and
        # style.css contains no competing class-keyed Clear-control rule.
        tmp = _mkstate("h-clear-attr")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "ca01", "callsign": "CA1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if "data-filter-clear" not in rendered:
                return False, "expected History's rendered filter bar to carry data-filter-clear"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        # Comments are stripped first: this task's own commit adds prose
        # explaining the attribute-selector choice, and that prose must
        # not trip the check it documents.
        declarations = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        # WR-05 fix: the rule-matching regex below requires the selector
        # and its opening `{` on the same line, so a multi-line,
        # comma-grouped selector (e.g. `a:focus-visible,\nbutton:focus-
        # visible {`) would otherwise have its earlier lines silently
        # dropped from `selector`, undermining this check's own
        # regression guard. Joining each selector-list newline back onto
        # one line first makes the regex robust to that style.css
        # convention.
        declarations = re.sub(r",\s*\n\s*", ", ", declarations)
        if "[data-filter-clear]" not in declarations:
            return False, "expected a [data-filter-clear] rule in style.css"
        for m in re.finditer(r"\n([^{\n]*\{[^}]*\})", declarations):
            rule = m.group(1)
            selector = rule.split("{", 1)[0]
            if "[data-filter-clear]" in selector:
                continue
            if "clear" in selector.lower() and (
                    "background: none" in rule or "text-decoration: underline" in rule):
                return False, (
                    "found a class-keyed Clear-control rule outside "
                    "[data-filter-clear]: %r - the shared attribute "
                    "contract must stay the only Clear-control styling "
                    "site" % selector.strip())
        return True, ""
    check(
        "the Clear control's shared [data-filter-clear] contract holds: History renders the "
        "attribute, style.css styles it by attribute, and no class-keyed rule competes",
        _clear_control_shared_attribute_contract)

    def _filter_text_attribute_on_both_representations():
        # D-20/T-06.6.3-09: the same escaped, lowercased "callsign hex"
        # value drives both the desktop <tr> and the mobile <li> for the
        # same flight, so a filter query matches both representations
        # identically.
        tmp = _mkstate("h-filter-text")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "3944F0", "callsign": "AFR123"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_attr = 'data-filter-text="afr123 3944f0"'
            count = rendered.count(expected_attr)
            if count != 2:
                return False, (
                    "expected %r to appear exactly twice (desktop <tr> + "
                    "mobile <li>), got %d" % (expected_attr, count))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real flight's data-filter-text attribute (lowercased escaped callsign+hex) appears on both the desktop <tr> and the mobile <li>",
        _filter_text_attribute_on_both_representations)

    def _desktop_callsign_hex_cell_two_copy_buttons():
        # D-23: the dedicated Callsign+Hex cell function carries exactly
        # 2 copy buttons (callsign, hex), each immediately followed by
        # its data-copy-feedback sibling (copy-button.js's exact
        # contract).
        tmp = _mkstate("h-copy-desktop")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cd01", "callsign": "CDONE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tbody_match = re.search(r"<tbody>(.*)</tbody>", rendered, re.S)
            if not tbody_match:
                return False, "expected a <tbody> element in the rendered table"
            tbody = tbody_match.group(1)
            idx = tbody.find("CDONE")
            td_start = tbody.rfind("<td>", 0, idx)
            td_end = tbody.find("</td>", idx)
            if idx == -1 or td_start == -1 or td_end == -1:
                return False, "could not locate the callsign's enclosing <td>"
            cell = tbody[td_start:td_end]
            if cell.count("data-copy-value") != 2:
                return False, (
                    "expected exactly 2 copy buttons in the desktop "
                    "Callsign+Hex cell, got %d" % cell.count("data-copy-value"))
            feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", cell))
            if feedback_pairs != 2:
                return False, (
                    "expected each copy button to be immediately "
                    "followed by its data-copy-feedback sibling, found %d pairs"
                    % feedback_pairs)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop Callsign+Hex cell contains exactly 2 copy buttons, each immediately followed by its data-copy-feedback sibling",
        _desktop_callsign_hex_cell_two_copy_buttons)

    def _mobile_details_three_copy_buttons():
        # D-23: the mobile card's details region carries all 3 copy
        # buttons (callsign, hex, full timestamp), each immediately
        # followed by its data-copy-feedback sibling.
        tmp = _mkstate("h-copy-mobile")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cm01", "callsign": "CMONE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            details_match = re.search(
                r'<details class="history-card__details">(.*?)</details>', rendered, re.S)
            if not details_match:
                return False, "expected a history-card__details block"
            details = details_match.group(1)
            if details.count("data-copy-value") != 3:
                return False, (
                    "expected exactly 3 copy buttons in the mobile "
                    "details region, got %d" % details.count("data-copy-value"))
            feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", details))
            if feedback_pairs != 3:
                return False, (
                    "expected each mobile copy button to be immediately "
                    "followed by its data-copy-feedback sibling, found %d pairs"
                    % feedback_pairs)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the mobile card's details region contains exactly 3 copy buttons (callsign, hex, full timestamp), each immediately followed by its data-copy-feedback sibling",
        _mobile_details_three_copy_buttons)

    def _quick_260903_peo_desktop_copy_reveal_stylesheet_contract():
        # UIR-17: the desktop-only reveal rule lives inside the shared
        # min-width: 960px block, is scoped by [data-copy-value] (never
        # the bare .copy-btn class the always-visible View-panel/eye
        # trigger also carries), reveals via opacity + pointer-events
        # (never visibility: hidden or display: none, which would remove
        # the control from the tab order and break keyboard access — the
        # exact regression this finding forbids), and names both
        # tr:hover and tr:focus-within as its reveal triggers.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        media_marker = "@media (min-width: 960px) {"
        if media_marker not in css_source:
            return False, "expected style.css to declare the shared min-width: 960px block"
        media_start = css_source.index(media_marker)
        brace_at = css_source.index("{", media_start)
        depth, i = 0, brace_at
        while True:
            ch = css_source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        media_block = css_source[brace_at + 1:i]
        # Same multi-line-selector normalization the existing
        # [data-filter-clear] guard above uses (joining a comma-grouped
        # selector split across lines onto one line), so this check is
        # not fooled by the file's own line-wrapping convention.
        normalized = re.sub(r",\s*\n\s*", ", ", media_block)

        rest_selector = ".data-table tbody tr [data-copy-value] {"
        if rest_selector not in normalized:
            return False, (
                "expected the at-rest rule to be scoped by [data-copy-value] "
                "inside the 960px block, not the bare .copy-btn class")
        rest_start = normalized.index(rest_selector)
        rest_body = normalized[rest_start:normalized.index("}", rest_start)]
        if "opacity" not in rest_body:
            return False, "expected the at-rest rule to declare opacity"
        if "visibility: hidden" in rest_body or "display: none" in rest_body:
            return False, (
                "expected the at-rest rule to use opacity + pointer-events, "
                "never visibility: hidden or display: none")

        reveal_selector = (
            ".data-table tbody tr:hover [data-copy-value], "
            ".data-table tbody tr:focus-within [data-copy-value] {")
        if reveal_selector not in normalized:
            return False, "expected one reveal rule naming both tr:hover and tr:focus-within"
        reveal_start = normalized.index(reveal_selector)
        reveal_body = normalized[reveal_start:normalized.index("}", reveal_start)]
        if "opacity: 1" not in reveal_body:
            return False, "expected the reveal rule to restore opacity: 1"
        if "visibility: hidden" in reveal_body or "display: none" in reveal_body:
            return False, "expected the reveal rule to carry no visibility/display override"
        return True, ""
    check(
        "the desktop copy-button reveal rule lives inside the shared 960px block, is scoped by "
        "[data-copy-value] (never the bare .copy-btn class), reveals via opacity + pointer-events "
        "(never visibility: hidden or display: none) on both tr:hover and tr:focus-within "
        "(quick task 260903-peo, UIR-17)",
        _quick_260903_peo_desktop_copy_reveal_stylesheet_contract)

    def _quick_260903_peo_desktop_row_copy_buttons_and_eye_button_discriminator():
        # UIR-17's cross-file guard: the [data-copy-value] discriminator
        # the reveal rule above depends on cannot silently disappear. A
        # real rendered desktop row still carries both copy buttons with
        # their aria-labels and data-copy-feedback siblings intact, and
        # the same row's View-panel/eye trigger carries
        # data-view-panel-src and NEVER data-copy-value.
        tmp = _mkstate("h-copy-reveal-discriminator")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "rev01", "callsign": "REVEAL"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            tr_block = _row_block(rendered, "tr", 0)
            if tr_block is None:
                return False, "could not locate the seeded row's desktop <tr>"
            if tr_block.count("data-copy-value") != 2:
                return False, (
                    "expected exactly 2 copy buttons (callsign, hex) in the "
                    "desktop row, got %d" % tr_block.count("data-copy-value"))
            if tr_block.count("data-copy-feedback") != 2:
                return False, "expected each copy button's data-copy-feedback sibling to survive"
            for label in (history_page._COPY_CALLSIGN_LABEL, history_page._COPY_HEX_LABEL):
                if layout.escape_html(label) not in tr_block:
                    return False, "expected %r as an aria-label in the desktop row" % label
            if "data-view-panel-src" not in tr_block:
                return False, "expected the row's View-panel/eye trigger to still render"
            view_panel_start = tr_block.index("data-view-panel-src")
            view_panel_tag = tr_block[
                tr_block.rindex("<", 0, view_panel_start):tr_block.index(">", view_panel_start) + 1]
            if "data-copy-value" in view_panel_tag:
                return False, (
                    "the View-panel/eye button must never carry data-copy-value "
                    "— that is the sole discriminator separating it from the "
                    "two copy buttons the desktop reveal rule targets")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real rendered desktop History row keeps both copy buttons (aria-labels, "
        "data-copy-feedback siblings intact) and its View-panel/eye trigger never carries "
        "data-copy-value — the discriminator the desktop reveal rule depends on "
        "(quick task 260903-peo, UIR-17)",
        _quick_260903_peo_desktop_row_copy_buttons_and_eye_button_discriminator)

    def _presentation_labels_in_full_render():
        # UXA-05: Task 1's format_event_row()-level fixture, re-asserted
        # against the full render() output (both the desktop cell and
        # the mobile card), and confirms the audit's own incorrect
        # literal state-value strings never appear.
        #
        # merge of origin/main (quick task 260902-j21): runway "3"'s
        # device_config.runway_label() display text was relabelled from
        # "Runway 3 (07/25)" to the official "Piste 3" — derived here at
        # test time from the real registry rather than hardcoded, so this
        # check tracks whatever label device_config actually returns
        # instead of re-drifting the next time the copy changes.
        tmp = _mkstate("h-labels")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "pl01", "callsign": "PL1",
                    "confirmed_state": "departing", "tracked_runway": "3",
                },
                {
                    "ts": "2026-08-27T10:01:00+00:00", "hex": "pl02", "callsign": "PL2",
                    "confirmed_state": "taxiing",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for expected in ("Departing", device_config.runway_label("3"), "Taxiing"):
                if expected not in rendered:
                    return False, "expected %r in the rendered History page" % expected
            for wrong in ("on_runway", "approaching", 'departed"'):
                if wrong in rendered:
                    return False, (
                        "did not expect the audit's own incorrect literal "
                        "state value %r in the rendered History page" % wrong)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "confirmed_state/tracked_runway presentation labels (Task 1's format_event_row() fixture) also appear correctly through the full render() output",
        _presentation_labels_in_full_render)

    # ======================================================================
    # Section 1b: quick task 260903-etm - History's top-of-page render-
    # gallery <section> retired outright (developer redirection superseding
    # quick task 260903-c4o's own always-visible render-gallery section on
    # this same unmerged branch). The per-row "View panel near this time"
    # lightbox (D-20) is the sole surviving way to see a rendered panel on
    # this page; the orphaned colour caveat is rehomed into its note.
    # ======================================================================

    def _history_render_gallery_section_absent_with_content():
        tmp = _mkstate("h-gallery-section-absent")
        try:
            names = [
                "2026-08-27T10-02-00+00-00.png",
                "2026-08-27T10-01-00+00-00.png",
                "2026-08-27T10-00-00+00-00.png",
            ]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:03:00+00:00", "hex": "notdisc1", "callsign": "NOTDISC"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            if "<h2" in rendered:
                return False, "did not expect any <h2 element - the render-gallery section is gone"
            if "page-section" in rendered:
                return False, "did not expect any page-section element - the render-gallery section is gone"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid container element"
            if 'class="gallery-tile"' in rendered:
                return False, "did not expect a gallery-tile element"
            if "Recent renders" in rendered:
                return False, "did not expect the retired render-gallery heading text"
            if "No renders yet." in rendered:
                return False, "did not expect the retired no-renders empty-state heading text"
            # The per-row mechanism must survive in the SAME render that
            # proves the section is gone (T-etm-03) - a careless "remove
            # the gallery" reading could sever gallery_entries_list along
            # with the markup it used to feed.
            if "data-view-panel-src" not in rendered:
                return False, "expected at least one View-panel trigger to survive"
            if rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) != 1:
                return False, "expected exactly one lightbox dialog to survive"
            if '<details class="history-card__details"' not in rendered:
                return False, "expected History's own card disclosures to survive"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with 3 gallery entries and one seeded flight row, the rendered page carries zero <h2, "
        "zero page-section, zero gallery-grid/gallery-tile elements and zero occurrences of the "
        "retired heading/empty-state text, WHILE the per-row View-panel mechanism (a trigger, "
        "exactly one lightbox dialog) and History's own card disclosures survive in the same render",
        _history_render_gallery_section_absent_with_content)

    def _history_render_gallery_section_absent_when_empty():
        tmp = _mkstate("h-gallery-section-absent-empty")
        try:
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=[]))
            if "<h2" in rendered:
                return False, "did not expect any <h2 element with an empty gallery"
            if "page-section" in rendered:
                return False, "did not expect any page-section element with an empty gallery"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid container element"
            if 'class="gallery-tile"' in rendered:
                return False, "did not expect a gallery-tile element"
            if "Recent renders" in rendered:
                return False, "did not expect the retired render-gallery heading text"
            if "No renders yet." in rendered:
                return False, "did not expect the retired no-renders empty-state heading text"
            if "data-view-panel-src" in rendered:
                return False, "did not expect any View-panel trigger with an empty gallery"
            if ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) in rendered:
                return False, "did not expect a lightbox dialog with an empty gallery"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with gallery_entries=[], the same absences hold (the section is gone, not merely "
        "emptied) and, as before, zero View-panel triggers and zero lightbox dialogs render",
        _history_render_gallery_section_absent_when_empty)

    def _view_panel_trigger_title_matches_aria_label():
        tmp = _mkstate("h-view-panel-title")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vptt01", "callsign": "VPTITLE"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        escaped_label = layout.escape_html(history_page.VIEW_PANEL_LABEL)
        expected_title = 'title="%s"' % escaped_label
        expected_aria = 'aria-label="%s"' % escaped_label
        tr_block = _row_block(rendered, "tr", 0)
        li_block = _row_block(rendered, "li", 0)
        if tr_block is None or li_block is None:
            return False, "could not locate row block for data-filter-group=0"
        for label, block in (("desktop <tr>", tr_block), ("mobile <li>", li_block)):
            if expected_title not in block:
                return False, "expected %s to carry title=%r" % (label, escaped_label)
            if expected_aria not in block:
                return False, "expected %s to carry aria-label=%r" % (label, escaped_label)
        return True, ""
    check(
        "a rendered View-panel trigger carries title=\"View panel near this time\" byte-equal to "
        "its own aria-label value, on both the desktop <tr> and the mobile <li> representation "
        "of the same row",
        _view_panel_trigger_title_matches_aria_label)

    def _colour_caveat_rehomed_into_lightbox_note():
        tmp = _mkstate("h-caveat-rehomed")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "cvt001", "callsign": "CAVEAT"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if rendered.count(history_page.COLOUR_CAVEAT) != 1:
            return False, "expected the colour caveat sentence exactly once in the rendered page"
        note_match = re.search(
            r'<p class="lightbox__note text-body">(.*?)</p>', rendered, re.S)
        if note_match is None:
            return False, "could not locate the lightbox__note element"
        if history_page.COLOUR_CAVEAT not in note_match.group(1):
            return False, "expected the colour caveat to fall inside the lightbox__note element"
        return True, ""
    check(
        "the colour caveat sentence appears exactly once in the rendered page, and that single "
        "occurrence lies inside the lightbox__note element (the caveat's new, and only, home "
        "after the render-gallery section's removal)",
        _colour_caveat_rehomed_into_lightbox_note)

    def _render_gallery_no_preview_apparatus_even_with_panel_file():
        tmp = _mkstate("h-gallery-no-preview-apparatus")
        try:
            names = ["20260827T100000Z.png"]
            _seed_gallery(tmp, names)
            _write_panel_file(tmp)
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            for marker in ("/preview.png", "preview-frame", "preview-image"):
                if marker in rendered:
                    return False, "did not expect %r anywhere in the rendered page" % marker
            if "No panel has been rendered yet." in rendered:
                return False, "did not expect the retired no-panel caption sentence"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with a real panel.bin on disk and gallery entries seeded, the rendered output contains "
        "zero occurrences of /preview.png, preview-frame, preview-image, and the old no-panel "
        "caption sentence - a present panel file changes nothing about the markup any more "
        "(this check's real subject is quick task 260903-c4o's /preview.png route retirement, "
        "not the render-gallery section retired by this task; kept in place rather than dropped)",
        _render_gallery_no_preview_apparatus_even_with_panel_file)

    def _now_showing_no_preview_freshness_apparatus():
        # D-18: Preview's page-level freshness apparatus (its own
        # data-loaded-at Refresh link and paired data-stale-banner) was
        # deliberately not ported when Preview's content first moved onto
        # History (06.6.4.1-05), and quick task 260903-c4o's further
        # restructure (folding the newest render into the gallery grid,
        # retiring the separate frame) does not change that guarantee -
        # retained here unmodified except for this comment and the seeding
        # below.
        tmp = _mkstate("h-no-freshness")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if "data-loaded-at" in rendered:
                return False, "did not expect a data-loaded-at attribute on the History page"
            if "data-stale-banner" in rendered:
                return False, "did not expect a data-stale-banner element on the History page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered History page contains no data-loaded-at attribute and no data-stale-banner "
        "element - Preview's page-level freshness apparatus was deliberately not ported",
        _now_showing_no_preview_freshness_apparatus)

    def _gallery_name_to_iso_fixtures():
        # D-22/06.6.3-RESEARCH.md Pitfall 2: the well-formed reversal only
        # touches the time+offset portion; a missing "T" separator or a
        # malformed time+offset portion both degrade to None rather than
        # raising. Carried over here (06.6.4.1-08 Task 3) from
        # companion/pages/preview_page.py's own now-deleted coverage of
        # the identical helper, which history_page.py absorbed byte-for-
        # byte in 06.6.4.1-05 — not otherwise duplicated on the History
        # side.
        well_formed = history_page._gallery_name_to_iso(
            "2026-08-30T19-20-42+00-00.png")
        if well_formed != "2026-08-30T19:20:42+00:00":
            return False, (
                "expected the well-formed fixture to reverse to %r, got %r"
                % ("2026-08-30T19:20:42+00:00", well_formed))
        if history_page._gallery_name_to_iso("not-a-real-name.png") is not None:
            return False, "expected a filename with no 'T' separator to return None"
        if history_page._gallery_name_to_iso("2026-08-30Tgarbage.png") is not None:
            return False, "expected a malformed time+offset portion to return None"
        return True, ""
    check(
        "history_page._gallery_name_to_iso() reverses a well-formed gallery filename and "
        "returns None (never raising) on a missing 'T' separator or a "
        "malformed time+offset portion",
        _gallery_name_to_iso_fixtures)

    def _view_panel_trigger_carries_nonempty_icon():
        # 06.6.4.1-08 (D-22) Task 2 acceptance criterion, placed here
        # (test_view_pages.py) rather than test_companion_app.py since
        # this needs a full History render with a matched gallery entry
        # — layout-level coverage that icon_html("icon-nav-preview")
        # itself returns non-empty markup lives in
        # test_companion_app.py's own eye-glyph-survives-nav-shrink check.
        tmp = _mkstate("h-view-panel-icon")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpicon1", "callsign": "VPICON"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if "data-view-panel-src" not in rendered:
            return False, "expected at least one View-panel trigger to render"
        trigger_start = rendered.find("data-view-panel-src")
        button_start = rendered.rfind("<button", 0, trigger_start)
        button_end = rendered.find("</button>", trigger_start)
        button_markup = rendered[button_start:button_end]
        if "<svg" not in button_markup:
            return False, "expected the View-panel trigger button to carry non-empty <svg icon markup"
        return True, ""
    check(
        "a rendered History page's View-panel trigger carries a non-empty icon (<svg markup) "
        "for a fixture with a matched gallery entry — the eye glyph survives the nav shrink",
        _view_panel_trigger_carries_nonempty_icon)

    # ======================================================================
    # Section 1c: 06.6.4.1-05 Task 2 - server-side nearest-render lookup,
    # per-row View-panel buttons, and the shared lightbox (D-20).
    # ======================================================================

    def _nearest_gallery_entry_behaviour():
        entries = [
            "2026-08-27T10-05-00+00-00.png",
            "2026-08-27T10-02-00+00-00.png",
            "2026-08-27T10-00-00+00-00.png",
            "not-a-real-gallery-name.png",  # unparseable - must be skipped
        ]

        # Between two entries: matches the latest one at or before row_ts.
        match = history_page.nearest_gallery_entry(entries, "2026-08-27T10:03:00+00:00")
        if match != ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"):
            return False, "expected the latest entry at or before 10:03:00, got %r" % (match,)

        # Exact boundary: row_ts equal to an entry's own recovered
        # timestamp still matches that entry ("at or before" is
        # inclusive).
        match = history_page.nearest_gallery_entry(entries, "2026-08-27T10:02:00+00:00")
        if match != ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"):
            return False, "expected an exact-boundary row_ts to match its own entry, got %r" % (match,)

        # Every recoverable entry strictly after row_ts -> None.
        if history_page.nearest_gallery_entry(entries, "2026-08-27T09:00:00+00:00") is not None:
            return False, "expected None when every recoverable entry is strictly after row_ts"

        # Empty entry list -> None.
        if history_page.nearest_gallery_entry([], "2026-08-27T10:03:00+00:00") is not None:
            return False, "expected None for an empty entry list"

        # Unparseable/empty row_ts -> None, never raising.
        if history_page.nearest_gallery_entry(entries, "") is not None:
            return False, "expected None for an empty row_ts"
        if history_page.nearest_gallery_entry(entries, "not-a-real-timestamp") is not None:
            return False, "expected None for an unparseable row_ts"
        if history_page.nearest_gallery_entry(entries, None) is not None:
            return False, "expected None for a None row_ts, never raising"

        return True, ""
    check(
        "nearest_gallery_entry() matches the latest at-or-before entry (inclusive boundary), skips "
        "an entry with an unrecoverable filename timestamp, and returns None for an empty entry "
        "list, an empty/unparseable row_ts, or when every recoverable entry is strictly after row_ts",
        _nearest_gallery_entry_behaviour)

    def _view_panel_triggers_per_row_full_render():
        tmp = _mkstate("h-view-panel-rows")
        try:
            names = [
                "2026-08-27T10-05-00+00-00.png",
                "2026-08-27T10-02-00+00-00.png",
                "2026-08-27T10-00-00+00-00.png",
            ]
            _seed_gallery(tmp, names)
            # Newest-first row order (history_rows()'s own ordering):
            # VP-C (10:10) -> VP-B (10:03) -> VP-A (10:01).
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpa01", "callsign": "VPA"},
                {"ts": "2026-08-27T10:03:00+00:00", "hex": "vpb01", "callsign": "VPB"},
                {"ts": "2026-08-27T10:10:00+00:00", "hex": "vpc01", "callsign": "VPC"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))

            expected_by_group = {
                0: ("2026-08-27T10-05-00+00-00.png", "2026-08-27T10:05:00+00:00"),  # VPC
                1: ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"),  # VPB
                2: ("2026-08-27T10-00-00+00-00.png", "2026-08-27T10:00:00+00:00"),  # VPA
            }
            for index, (expected_name, expected_iso) in expected_by_group.items():
                expected_src = "/gallery/%s" % expected_name
                expected_caption = history_page.lightbox_caption_text(expected_iso)

                tr_block = _row_block(rendered, "tr", index)
                li_block = _row_block(rendered, "li", index)
                if tr_block is None or li_block is None:
                    return False, "could not locate row block for data-filter-group=%d" % index

                for label, block in (("desktop <tr>", tr_block), ("mobile <li>", li_block)):
                    if ('data-view-panel-src="%s"' % expected_src) not in block:
                        return False, (
                            "expected %s for row %d to carry data-view-panel-src=%r"
                            % (label, index, expected_src))
                    if ('data-view-panel-caption="%s"' % expected_caption) not in block:
                        return False, (
                            "expected %s for row %d to carry data-view-panel-caption=%r"
                            % (label, index, expected_caption))
                    if history_page.VIEW_PANEL_LABEL not in block:
                        return False, "expected %s for row %d to carry the View-panel aria-label" % (label, index)

                tr_src = re.search(r'data-view-panel-src="([^"]*)"', tr_block).group(1)
                li_src = re.search(r'data-view-panel-src="([^"]*)"', li_block).group(1)
                tr_caption = re.search(r'data-view-panel-caption="([^"]*)"', tr_block).group(1)
                li_caption = re.search(r'data-view-panel-caption="([^"]*)"', li_block).group(1)
                if tr_src != li_src or tr_caption != li_caption:
                    return False, (
                        "expected byte-identical trigger attributes on the desktop and mobile "
                        "representations of row %d" % index)

            if rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) != 1:
                return False, "expected exactly one lightbox dialog element"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "for three gallery entries and three interleaved rows, each row's desktop and mobile "
        "View-panel trigger carries byte-identical, correctly-targeted data-view-panel-src/-caption "
        "attributes matching its own nearest gallery entry, and exactly one lightbox dialog is emitted",
        _view_panel_triggers_per_row_full_render)

    def _view_panel_empty_gallery_zero_triggers_zero_dialog():
        tmp = _mkstate("h-view-panel-empty-gallery")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "vpe01", "callsign": "VPEMPTY"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=[]))
            if "data-view-panel-src" in rendered:
                return False, "did not expect any View-panel trigger with an empty gallery entry list"
            if ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) in rendered:
                return False, "did not expect a lightbox dialog element with an empty gallery entry list"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with an empty gallery entry list, History renders zero View-panel triggers and zero "
        "lightbox dialog elements, never a disabled or broken control",
        _view_panel_empty_gallery_zero_triggers_zero_dialog)

    def _lightbox_dom_contract_three_file_guard():
        # Source/DOM-contract guard, restructured (phase 14 plan 14-01
        # Task 2) into three classified token tuples instead of one
        # inline literal: _LIGHTBOX_SHARED_TOKENS must appear in
        # panel-lookup.js's source and in both pages' rendered markup;
        # _LIGHTBOX_AIRLINES_ONLY_TOKENS must appear in panel-lookup.js
        # and in Airlines' rendered markup, and must be absent from
        # History's; _LIGHTBOX_RENDER_ONLY_TOKENS is asserted present in
        # Airlines' rendered markup only, with no claim at all against
        # panel-lookup.js or History. A drift in any of the three would
        # leave the button silently doing nothing with no signal from
        # any file in isolation.
        js_path = os.path.join(HERE, "static", "panel-lookup.js")
        with open(js_path) as fh:
            js_source = fh.read()

        tmp = _mkstate("h-dom-contract")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "dc01", "callsign": "DOMCONTRACT"},
            ])
            history_rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        # airlines_page.render() reads nothing from ctx - a plain dict is
        # call-site parity only, matching every other page module's
        # render(ctx) signature.
        airlines_rendered = airlines_page.render({})

        for token in _LIGHTBOX_SHARED_TOKENS:
            if token not in js_source:
                return False, "expected shared token %r to appear in companion/static/panel-lookup.js" % token
            if token not in history_rendered:
                return False, "expected shared token %r to appear in the rendered History page" % token
            if token not in airlines_rendered:
                return False, "expected shared token %r to appear in the rendered Airlines page" % token

        for token in _LIGHTBOX_AIRLINES_ONLY_TOKENS:
            if token not in js_source:
                return False, (
                    "expected Airlines-only token %r to appear in companion/static/panel-lookup.js" % token)
            if token not in airlines_rendered:
                return False, "expected Airlines-only token %r to appear in the rendered Airlines page" % token
            if token in history_rendered:
                return False, "did not expect Airlines-only token %r in the rendered History page" % token

        for token in _LIGHTBOX_RENDER_ONLY_TOKENS:
            if token not in airlines_rendered:
                return False, "expected render-only token %r to appear in the rendered Airlines page" % token

        return True, ""
    check(
        "the shared, Airlines-only and render-only lightbox token tuples each appear (or, for "
        "Airlines-only, are absent from History) exactly where their own classification says they "
        "must, across companion/static/panel-lookup.js and both pages' rendered markup",
        _lightbox_dom_contract_three_file_guard)

    def _view_panel_attr_constants_all_classified():
        # Reflection-driven coverage check (phase 14 plan 14-01 Task 2):
        # enumerate every airlines_page module attribute matching the
        # exact shape _VIEW_PANEL_...(_ATTR) and assert its *value*
        # appears in exactly one of the three classified token tuples
        # above. A hand-copied list here would be the same drift this
        # guard exists to catch, one level up - so this walks
        # dir(airlines_page) instead of restating a name list.
        all_tuples = (
            _LIGHTBOX_SHARED_TOKENS,
            _LIGHTBOX_AIRLINES_ONLY_TOKENS,
            _LIGHTBOX_RENDER_ONLY_TOKENS,
        )

        # The three tuples must never overlap - a token classified in
        # two of them at once would carry contradictory expectations.
        seen = {}
        for tuple_name, tup in (
            ("_LIGHTBOX_SHARED_TOKENS", _LIGHTBOX_SHARED_TOKENS),
            ("_LIGHTBOX_AIRLINES_ONLY_TOKENS", _LIGHTBOX_AIRLINES_ONLY_TOKENS),
            ("_LIGHTBOX_RENDER_ONLY_TOKENS", _LIGHTBOX_RENDER_ONLY_TOKENS),
        ):
            for token in tup:
                if token in seen:
                    return False, (
                        "token %r is classified in both %s and %s - the three tuples must be "
                        "pairwise disjoint" % (token, seen[token], tuple_name))
                seen[token] = tuple_name

        for name in dir(airlines_page):
            if not (name.startswith("_VIEW_PANEL_") and name.endswith("_ATTR")):
                continue
            value = getattr(airlines_page, name)
            memberships = [tup for tup in all_tuples if value in tup]
            if len(memberships) == 0:
                return False, (
                    "airlines_page.%s = %r is not classified in any of _LIGHTBOX_SHARED_TOKENS, "
                    "_LIGHTBOX_AIRLINES_ONLY_TOKENS or _LIGHTBOX_RENDER_ONLY_TOKENS" % (name, value))
            if len(memberships) > 1:
                return False, (
                    "airlines_page.%s = %r is classified in more than one of the three token "
                    "tuples" % (name, value))
        return True, ""
    check(
        "every airlines_page._VIEW_PANEL_*_ATTR constant's value is classified in exactly one of "
        "the three lightbox token tuples, discovered by reflection over dir(airlines_page) rather "
        "than a hand-copied name list",
        _view_panel_attr_constants_all_classified)

    # --- Phase 14 plan 14-05 Task 2: eight source-content checks pinning
    # panel-lookup.js's own contract without a live DOM/JS engine (no
    # headless browser exists in this project's toolchain - see
    # RESEARCH.md's Validation Architecture section). ---------------------

    def _panel_lookup_never_sets_image_src_to_empty_string():
        stripped = _strip_js_comments(_read_panel_lookup_source())
        if 'image.src = ""' in stripped:
            return False, (
                'expected zero occurrences of image.src = "" in panel-lookup.js\'s '
                "comment-stripped source (D-02/RESEARCH.md Pitfall 1)")
        return True, ""
    check(
        "panel-lookup.js never sets image.src to the empty string anywhere in its "
        "comment-stripped source - D-02/RESEARCH.md Pitfall 1's single riskiest line, "
        "the exact cross-browser spurious-request bug this phase's imageless-open branch exists "
        "to avoid",
        _panel_lookup_never_sets_image_src_to_empty_string)

    def _panel_lookup_remove_attribute_src_is_conditional():
        src = _read_panel_lookup_source()
        needle = 'image.removeAttribute("src")'
        if needle not in src:
            return False, "expected %r to appear at least once" % needle
        line = next(line for line in src.splitlines() if needle in line)
        indent = len(line) - len(line.lstrip(" "))
        # Every bare top-level statement inside the IIFE (a var
        # declaration, a function definition) sits at 2-space indent;
        # anything nested one level deeper than that (inside an
        # if/else/for) sits at 4+ spaces - this must be nested, never a
        # bare, unconditional module-scope statement.
        if indent <= 2:
            return False, (
                "expected image.removeAttribute(\"src\") indented inside a conditional branch, "
                "not written unconditionally at module scope (indent was %d)" % indent)
        return True, ""
    check(
        "panel-lookup.js's image.removeAttribute(\"src\") call is nested inside a conditional "
        "branch (the src-absent case), never written unconditionally at module scope",
        _panel_lookup_remove_attribute_src_is_conditional)

    def _panel_lookup_shared_populate_function_two_call_sites():
        src = _read_panel_lookup_source()
        def_needle = "function openFromTrigger(trigger)"
        def_count = src.count(def_needle)
        if def_count != 1:
            return False, "expected exactly one openFromTrigger definition, got %d" % def_count
        total_mentions = src.count("openFromTrigger(")
        call_sites = total_mentions - def_count
        if call_sites < 2:
            return False, (
                "expected openFromTrigger referenced (called) from at least two sites, found %d"
                % call_sites)
        return True, ""
    check(
        "panel-lookup.js's shared populate-and-open function (openFromTrigger) is defined exactly "
        "once and referenced from at least two call sites - the click listener and the load-time "
        "auto-open (RESEARCH.md Pitfall 2's mandatory factoring)",
        _panel_lookup_shared_populate_function_two_call_sites)

    def _panel_lookup_location_search_read_once_outside_click_only_function():
        src = _read_panel_lookup_source()
        stripped = _strip_js_comments(src)
        code_count = stripped.count("location.search")
        if code_count != 1:
            return False, (
                "expected location.search to be read exactly once in panel-lookup.js's own code "
                "(comments excluded), got %d" % code_count)
        # openFromTrigger is the one function reachable from a click;
        # location.search's single read must sit outside its body,
        # after the click listener that calls it is already wired
        # (RESEARCH.md Pitfall 2, D-13/D-14).
        func_start = src.index("function openFromTrigger(trigger)")
        func_end = src.index("\n  }\n", func_start)
        search_idx = src.index("location.search")
        click_listener_idx = src.index('document.addEventListener("click"')
        if func_start < search_idx < func_end:
            return False, "expected location.search's one read outside openFromTrigger's own body"
        if search_idx < click_listener_idx:
            return False, "expected location.search's one read positioned after the click listener is wired"
        return True, ""
    check(
        "panel-lookup.js reads location.search exactly once in its own code, at script init, "
        "outside openFromTrigger (the one function reachable from a click) and after the click "
        "listener is already wired",
        _panel_lookup_location_search_read_once_outside_click_only_function)

    def _panel_lookup_eleven_new_attrs_present_in_source():
        src = _read_panel_lookup_source()
        missing = [name for name in _NEW_VIEW_PANEL_ATTR_NAMES if name not in src]
        if missing:
            return False, (
                "expected every one of the eleven new data-view-panel-* attribute name literals "
                "in panel-lookup.js's source, missing: %r" % missing)
        return True, ""
    check(
        "every one of the eleven new data-view-panel-* attribute name literals 14-02 added to the "
        "vocabulary appears at least once in panel-lookup.js's own source",
        _panel_lookup_eleven_new_attrs_present_in_source)

    def _panel_lookup_mode_hidden_toggles_before_showmodal():
        src = _read_panel_lookup_source()
        func_start = src.index("function openFromTrigger(trigger)")
        show_modal_idx = src.index("dialog.showModal();", func_start)
        func_body = src[func_start:show_modal_idx]
        needles = (
            'resolveNameForm.hidden = (mode !== "gap")',
            'resolveUploadZone.hidden = (mode !== "needs-artwork")',
            'replaceForm.hidden = (mode !== "art")',
        )
        for needle in needles:
            if needle not in func_body:
                return False, (
                    "expected %r to occur, textually, before openFromTrigger's own "
                    "dialog.showModal() call" % needle)
        return True, ""
    check(
        "the mode-governed elements' (resolveNameForm/resolveUploadZone/replaceForm) hidden "
        "assignments all occur, textually, before openFromTrigger's own dialog.showModal() call "
        "(RESEARCH.md Pitfall 3 - showModal()'s one-time autofocus placement must see the final, "
        "already-toggled subtree)",
        _panel_lookup_mode_hidden_toggles_before_showmodal)

    def _panel_lookup_prevent_default_once_correctly_positioned():
        src = _read_panel_lookup_source()
        count = src.count("evt.preventDefault()")
        if count != 1:
            return False, "expected evt.preventDefault() exactly once, got %d" % count
        click_idx = src.index('document.addEventListener("click"')
        null_check_idx = src.index("if (!trigger) {", click_idx)
        prevent_idx = src.index("evt.preventDefault()", click_idx)
        open_call_idx = src.index("openFromTrigger(trigger)", click_idx)
        if not (click_idx < null_check_idx < prevent_idx < open_call_idx):
            return False, (
                "expected evt.preventDefault() positioned after the trigger-null-check and before "
                "openFromTrigger() (the one showModal()-reaching call) inside the click listener")
        return True, ""
    check(
        "panel-lookup.js's evt.preventDefault() appears exactly once, inside the click listener, "
        "positioned after the trigger-null-check and before the showModal()-reaching "
        "openFromTrigger() call (D-12's <a> interception)",
        _panel_lookup_prevent_default_once_correctly_positioned)

    def _panel_lookup_single_dialog_lookup_single_click_listener():
        src = _read_panel_lookup_source()
        dialog_count = src.count('document.getElementById("panel-lookup-dialog")')
        click_count = src.count('document.addEventListener("click"')
        if dialog_count != 1:
            return False, (
                'expected exactly one document.getElementById("panel-lookup-dialog"), got %d'
                % dialog_count)
        if click_count != 1:
            return False, (
                'expected exactly one document.addEventListener("click", ...), got %d' % click_count)
        return True, ""
    check(
        "panel-lookup.js still contains exactly one document.getElementById(\"panel-lookup-dialog\") "
        "and exactly one document.addEventListener(\"click\", ...) - this plan extended the existing "
        "single mechanism rather than adding a second one (D-03's own rejected alternative)",
        _panel_lookup_single_dialog_lookup_single_click_listener)

    def _airlines_lightbox_constants_match_history():
        # quick task 260902-tli: the dialog id and the three
        # data-view-panel-* attribute names are duplicated, not imported
        # (a page module has no import path to a sibling page module),
        # into airlines_page.py from history_page.py's own values -
        # pinned here so a drift fails loudly instead of leaving the
        # Airlines trigger silently inert.
        pairs = (
            ("LIGHTBOX_DIALOG_ID", airlines_page.LIGHTBOX_DIALOG_ID, history_page.LIGHTBOX_DIALOG_ID),
            ("_VIEW_PANEL_SRC_ATTR", airlines_page._VIEW_PANEL_SRC_ATTR, history_page._VIEW_PANEL_SRC_ATTR),
            ("_VIEW_PANEL_CAPTION_ATTR", airlines_page._VIEW_PANEL_CAPTION_ATTR,
                history_page._VIEW_PANEL_CAPTION_ATTR),
            ("_VIEW_PANEL_CLOSE_ATTR", airlines_page._VIEW_PANEL_CLOSE_ATTR, history_page._VIEW_PANEL_CLOSE_ATTR),
        )
        for name, airlines_value, history_value in pairs:
            if airlines_value != history_value:
                return False, (
                    "expected airlines_page.%s (%r) to equal history_page.%s (%r)"
                    % (name, airlines_value, name, history_value))
        return True, ""
    check(
        "airlines_page's LIGHTBOX_DIALOG_ID and its three _VIEW_PANEL_*_ATTR constants each equal "
        "history_page's own values (the duplicated-not-imported shared-lightbox contract)",
        _airlines_lightbox_constants_match_history)

    def _history_lightbox_carries_zero_replace_markup():
        # new (quick task 260903-btu): actually exercises history_page.
        # render() against a seeded fixture — a real gallery entry and a
        # real runway event, mirroring _lightbox_dom_contract_three_file_
        # guard()'s own fixture shape — since History only emits its
        # dialog when at least one row carries a trigger; a fixture with
        # no entries would prove absence for the wrong reason.
        tmp = _mkstate("h-no-replace-markup")
        try:
            names = ["2026-08-27T10-05-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:06:00+00:00", "hex": "dc02", "callsign": "NOREPLACE"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        dialog_count = rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID)
        if dialog_count != 1:
            return False, "expected the History dialog exactly once (proves the absence checks below mean something), got %d" % dialog_count
        for token, label in (
                (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS"),
                (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR"),
                ("<form", "<form"),
                ('<input type="file"', '<input type="file"'),
                ("enctype", "enctype"),
                # quick task 260903-df3: the framed zone's three new
                # class constants extend this non-regression guard too —
                # History must carry none of this task's new markup any
                # more than it carried the old inline-row markup.
                (airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS, "airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS"),
                (airlines_page.REPLACE_HINT_CLASS, "airlines_page.REPLACE_HINT_CLASS"),
                (airlines_page.REPLACE_ICON_CLASS, "airlines_page.REPLACE_ICON_CLASS")):
            count = rendered.count(token)
            if count != 0:
                return False, "expected zero occurrences of %s in a real, seeded history_page.render() output, got %d" % (label, count)
        return True, ""
    check(
        "a real, seeded history_page.render() call (real gallery entry, real runway event) renders its "
        "lightbox dialog exactly once, and carries zero occurrences of airlines_page's replace-form class, "
        "replace-action attribute, <form>, file input, enctype, or the framed zone's three class constants "
        "(quick task 260903-df3) anywhere (quick task 260903-btu)",
        _history_lightbox_carries_zero_replace_markup)

    def _replace_lightbox_names_appear_in_three_files_never_in_history():
        # new (quick task 260903-btu): the three-file contract for the
        # two new names, mirroring _lightbox_dom_contract_three_file_
        # guard()'s style — each token must appear in panel-lookup.js's
        # source and in a real airlines_page.render({}) call, and must
        # never appear in a real, seeded history_page.render() call.
        # These two constants deliberately have no history_page
        # counterpart and must never be added to
        # _airlines_lightbox_constants_match_history()'s pairs tuple.
        js_path = os.path.join(HERE, "static", "panel-lookup.js")
        with open(js_path) as fh:
            js_source = fh.read()
        style_css_path = os.path.join(HERE, "static", "style.css")
        with open(style_css_path) as fh:
            style_css_source = fh.read()

        airlines_rendered = airlines_page.render({})
        tmp = _mkstate("h-replace-tokens-absent")
        try:
            names = ["2026-08-27T10-07-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:08:00+00:00", "hex": "dc03", "callsign": "TOKENGONE"},
            ])
            history_rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        for token in (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, airlines_page.LIGHTBOX_REPLACE_FORM_CLASS):
            if token not in js_source:
                return False, "expected %r in companion/static/panel-lookup.js" % (token,)
            if token not in airlines_rendered:
                return False, "expected %r in a real airlines_page.render({}) call" % (token,)
            if token in history_rendered:
                return False, "expected %r to never appear in a real, seeded history_page.render() call" % (token,)
        # quick task 260903-df3: a bare substring test here is no longer
        # sufficient — LIGHTBOX_REPLACE_FORM_CLASS ("lightbox__replace")
        # is now also a prefix of LIGHTBOX_REPLACE_ZONE_CLASS's own
        # selector ("lightbox__replace-zone"), so the bare substring
        # would keep passing even if the `.lightbox__replace { ... }`
        # rule itself were deleted from the stylesheet (the zone
        # selector alone would satisfy it). Require the exact selector,
        # built from the constant rather than hard-coding the literal.
        #
        # Phase 14 (14-03-PLAN.md Task 2) retargeted this pattern IN
        # PLACE (no count change to EXPECTED_CHECK_COUNT — same check,
        # re-scoped): .lightbox__replace's own selector is now the head
        # of a three-way group (`.lightbox__replace,\n.lightbox__resolve-
        # name,\n.lightbox__delete {`), so the class name is followed by
        # a comma, not always " {". A lookahead for whitespace/comma/
        # brace immediately after the class name (excluding the
        # "-zone" hyphen continuation) still proves the exact selector
        # exists as its own token, in either the old standalone form or
        # the new grouped form.
        #
        # 14-08 on-glass fix (2026-09-06) retargeted this pattern IN
        # PLACE a second time: a real-browser check found `display:
        # block` on this group winning a specificity tie against the UA
        # stylesheet's `[hidden] { display: none }`, so every selector
        # in the group now carries `:not([hidden])` immediately after
        # the class name — a colon, not whitespace/comma/brace. Added
        # `:` to the lookahead so the exact-selector proof still holds
        # for the scoped form.
        exact_selector_pattern = re.compile(
            r'\.' + re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS) + r'(?=[\s,{:])')
        if not exact_selector_pattern.search(style_css_source):
            return False, (
                "expected a '.%s' selector (not merely a '-zone' prefix match) in "
                "companion/static/style.css — the fourth file in the chain, and the one whose drift would "
                "leave the form functional but unstyled" % (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,))
        return True, ""
    check(
        "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR and airlines_page.LIGHTBOX_REPLACE_FORM_CLASS each "
        "appear in companion/static/panel-lookup.js's source and in a real airlines_page.render({}) call, "
        "the exact '.lightbox__replace' selector (not merely a substring, which the newer "
        "'.lightbox__replace-zone' selector could otherwise satisfy) appears in companion/static/style.css "
        "standalone or as the head of the phase-14 three-way group, and neither token appears in a real, "
        "seeded history_page.render() call (quick task 260903-btu; these two constants have no history_page "
        "counterpart by design and must never join _airlines_lightbox_constants_match_history()'s pairs "
        "tuple; pattern retargeted in place by phase 14 plan 14-03 Task 2)",
        _replace_lightbox_names_appear_in_three_files_never_in_history)

    def _airlines_render_empty_ctx_still_contains_gallery_grid():
        # quick task 260902-v26 threaded an optional state_dir read
        # through render(ctx) via ctx.get("state_dir") - this pins that
        # render({}) with a literal empty dict (exactly what
        # _lightbox_dom_contract_three_file_guard() above already calls)
        # still succeeds and its output still contains the gallery grid,
        # not just that it doesn't raise.
        rendered = airlines_page.render({})
        if "illustration-grid" not in rendered:
            return False, "expected render({}) to still contain the .illustration-grid gallery container"
        return True, ""
    check(
        "airlines_page.render({}) with a literal empty dict still succeeds and its output still contains the "
        "gallery grid (quick task 260902-v26's ctx.get(\"state_dir\") tolerance)",
        _airlines_render_empty_ctx_still_contains_gallery_grid)

    # ======================================================================
    # Section 1d: 06.6.4.1-05 Task 3 - unresolved-airline link to Health's
    # Server & data anchor (D-21).
    # ======================================================================

    def _unresolved_link_absent_for_resolved_airline():
        tmp = _mkstate("h-link-resolved")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "lkr01", "callsign": "LINKRES",
                    "airline": "AFR", "origin": "LFPO", "destination": "LFPG",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a resolved-airline row"
            if history_page.UNRESOLVED_LINK_HREF in tr_block:
                return False, "did not expect the unresolved-airline link in the desktop cell for a resolved airline"
            if history_page.UNRESOLVED_LINK_HREF in li_block:
                return False, "did not expect the unresolved-airline link in the mobile details for a resolved airline"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a formatted row with a resolved airline produces a Type-and-Airline cell (desktop) and "
        "Aircraft detail row (mobile) with no anchor pointing at the Health server-data route",
        _unresolved_link_absent_for_resolved_airline)

    def _unresolved_link_present_once_each_for_unresolved_airline():
        tmp = _mkstate("h-link-unresolved")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "lku01", "callsign": "LINKUNR"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for an unresolved-airline row"
            href_attr = 'href="%s"' % history_page.UNRESOLVED_LINK_HREF
            if tr_block.count(href_attr) != 1:
                return False, (
                    "expected exactly one unresolved-airline link in the desktop cell, found %d"
                    % tr_block.count(href_attr))
            if li_block.count(href_attr) != 1:
                return False, (
                    "expected exactly one unresolved-airline link in the mobile details list, found %d"
                    % li_block.count(href_attr))
            if history_page.UNRESOLVED_LINK_TEXT not in tr_block:
                return False, "expected the link text in the desktop cell"
            if history_page.UNRESOLVED_LINK_TEXT not in li_block:
                return False, "expected the link text in the mobile details list"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a formatted row whose airline label equals the route-fallback constant produces exactly "
        "one unresolved-airline anchor in the desktop cell and exactly one in the mobile details list",
        _unresolved_link_present_once_each_for_unresolved_airline)

    def _unresolved_link_keyed_on_airline_not_route():
        tmp = _mkstate("h-link-route-only")
        try:
            _seed_runway_events(tmp, [
                # airline resolved, but no origin/destination -> route
                # unavailable while the airline itself is not.
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "lkro1", "callsign": "LINKROUTE",
                    "airline": "AFR",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a route-only-unresolved row"
            if panel_render.ROUTE_FALLBACK_TEXT not in tr_block:
                return False, "expected the Route cell to still render the fallback text"
            if history_page.UNRESOLVED_LINK_HREF in tr_block:
                return False, "did not expect the unresolved-airline link when only the route is unresolved"
            if history_page.UNRESOLVED_LINK_HREF in li_block:
                return False, "did not expect the unresolved-airline link in mobile details either"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a row whose route is unresolved but whose airline IS resolved produces no unresolved-"
        "airline link - the link is keyed on the airline label, not on the route label",
        _unresolved_link_keyed_on_airline_not_route)

    def _airline_fallback_distinct_from_route_fallback():
        # quick task 260902-w4t (UIR-05): a no-airline row must render
        # AIRLINE_FALLBACK_TEXT ("Airline unknown") in the Type+Airline
        # cell/Aircraft detail row and panel_render.ROUTE_FALLBACK_TEXT
        # ("Route unavailable") in the Route cell/detail row - two
        # distinct strings in two distinct columns, never the same
        # phrase borrowed twice. Also pins the new anchor class
        # (UNRESOLVED_LINK_CLASS) into both the rendered page and
        # style.css, matching _merged_cell_classes_agree_with_stylesheet's
        # own cross-file drift discipline.
        if history_page.AIRLINE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT:
            return False, "AIRLINE_FALLBACK_TEXT must not equal ROUTE_FALLBACK_TEXT"
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        if history_page.UNRESOLVED_LINK_CLASS.split()[-1] not in css:
            return False, (
                "expected UNRESOLVED_LINK_CLASS's spacing class to be styled in style.css")
        tmp = _mkstate("h-airline-fallback")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "af01", "callsign": "AIRFB1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a no-airline row"
            for label, block in (("desktop", tr_block), ("mobile", li_block)):
                if history_page.AIRLINE_FALLBACK_TEXT not in block:
                    return False, "expected AIRLINE_FALLBACK_TEXT in the %s row" % label
                if panel_render.ROUTE_FALLBACK_TEXT not in block:
                    return False, "expected ROUTE_FALLBACK_TEXT in the %s row" % label
                if block.count(panel_render.ROUTE_FALLBACK_TEXT) != 1:
                    return False, (
                        "expected ROUTE_FALLBACK_TEXT exactly once (Route column only) in "
                        "the %s row, found %d" % (label, block.count(panel_render.ROUTE_FALLBACK_TEXT)))
                if 'class="%s"' % history_page.UNRESOLVED_LINK_CLASS not in block:
                    return False, "expected the unresolved-link's class attribute in the %s row" % label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct "
        "strings in two distinct columns, and the unresolved-link's spacing class is styled in "
        "style.css and present in the rendered anchor (quick task 260902-w4t, UIR-05)",
        _airline_fallback_distinct_from_route_fallback)

    def _hex_only_row_promotes_hex_to_primary():
        # quick task 260902-w4t (UIR-06): a callsign-less row must never
        # render a dead copy button on a blank primary value. When a hex
        # is present it is promoted to the primary slot (desktop cell
        # AND mobile card primary line), with a "no callsign" secondary
        # note carrying NO copy button of its own. When both callsign
        # and hex are absent, render() must not raise and the cell must
        # carry zero copy buttons.
        tmp = _mkstate("h-hex-only")
        try:
            _seed_runway_events(tmp, [
                # Row 0 (newest, ts sorts DESC): hex only, no callsign.
                {"ts": "2026-08-27T10:02:00+00:00", "hex": "34560d"},
                # Row 1: neither callsign nor hex.
                {"ts": "2026-08-27T10:01:00+00:00"},
                # Row 2: callsign present, no hex - unaffected control.
                {"ts": "2026-08-27T10:00:00+00:00", "callsign": "CTRL01"},
            ])
            rendered = history_page.render(_history_ctx(tmp))

            # Row 0: hex-only, desktop.
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for the hex-only row"
            if '<span class="cell-primary">34560d</span>' not in tr_block:
                return False, "expected the desktop cell's primary slot to carry the hex"
            if ('<span class="cell-secondary">%s</span>'
                    % history_page.NO_CALLSIGN_NOTE_TEXT) not in tr_block:
                return False, "expected the desktop cell's secondary slot to carry the no-callsign note"
            if tr_block.count("data-copy-value") != 1:
                return False, (
                    "expected exactly 1 copy button in the hex-only desktop cell, got %d"
                    % tr_block.count("data-copy-value"))
            if 'data-copy-value="34560d"' not in tr_block:
                return False, "expected the lone copy button to copy the hex value"

            # Row 0: hex-only, mobile primary line (never blank).
            if '<span class="cell-primary mono">34560d</span>' not in li_block:
                return False, "expected the mobile card's primary line to carry the hex"
            if ('<span class="cell-secondary">%s</span>'
                    % history_page.NO_CALLSIGN_NOTE_TEXT) not in li_block:
                return False, "expected the mobile card's primary line to carry the no-callsign note"

            # Row 1: both falsy - no crash, zero copy buttons in that cell.
            tr_block_1 = _row_block(rendered, "tr", 1)
            if tr_block_1 is None:
                return False, "could not locate row block for the both-falsy row"
            callsign_hex_td = re.search(r"<td>(.*?)</td>", tr_block_1, re.S)
            if callsign_hex_td is None:
                return False, "expected a <td> for the both-falsy row's Callsign+Hex cell"
            if callsign_hex_td.group(1).count("data-copy-value") != 0:
                return False, "expected zero copy buttons in the both-falsy Callsign+Hex cell"

            # Row 2 (control): callsign-present branch is unaffected.
            tr_block_2 = _row_block(rendered, "tr", 2)
            if tr_block_2 is None or "CTRL01" not in tr_block_2:
                return False, "expected the control row's callsign to render unchanged"
            if history_page.NO_CALLSIGN_NOTE_TEXT in tr_block_2:
                return False, "did not expect the no-callsign note on a row with a callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a callsign-less row with a hex promotes the hex to the primary slot (desktop cell and "
        "mobile card) with a no-copy-button 'no callsign' note, a callsign+hex row is unaffected, "
        "and a row with neither renders without raising and with zero copy buttons "
        "(quick task 260902-w4t, UIR-06)",
        _hex_only_row_promotes_hex_to_primary)

    def _unresolved_link_href_matches_health_anchor():
        expected_suffix = "#" + health_page.SERVER_DATA_SECTION_ID
        if not history_page.UNRESOLVED_LINK_HREF.endswith(expected_suffix):
            return False, (
                "expected history_page.UNRESOLVED_LINK_HREF to end with %r, got %r"
                % (expected_suffix, history_page.UNRESOLVED_LINK_HREF))
        return True, ""
    check(
        "history_page.UNRESOLVED_LINK_HREF ends with \"#\" + health_page.SERVER_DATA_SECTION_ID",
        _unresolved_link_href_matches_health_anchor)

    def _no_prefix_registry_duplicated_on_history():
        tmp = _mkstate("h-no-registry")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "reg01", "callsign": "REGCHK"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if health_page.UNRESOLVED_SECTION_HEADING in rendered:
                return False, "did not expect Health's Unresolved-prefixes registry heading on History"
            if "<th>Prefix</th>" in rendered or "<th>First seen</th>" in rendered:
                return False, "did not expect the registry table's own column headers on History"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered History page contains no prefix-registry table and no element carrying the "
        "registry table's own headers",
        _no_prefix_registry_duplicated_on_history)

    # ======================================================================
    # Section 3: one end-to-end check - a real companion/app.py subprocess,
    # logged in, fetching /history, the retired /preview redirect, the
    # retired /preview.png route (now 404), and a real /gallery/{name}.png
    # (quick task 260903-etm: the per-row View-panel lightbox is now the
    # sole consumer of this route, the top-of-page render gallery having
    # been retired outright).
    # ======================================================================

    # --- Phase 18: the Home page -------------------------------------------

    def _home_page_render_with_seeded_state():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home")
        try:
            now = "2026-08-27T12:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
                 "airline": "Air France", "origin": "ORY", "destination": "TLS",
                 "confirmed_state": "departing"},
                {"ts": "2026-08-27T11:40:00+00:00", "hex": "4b1a72", "callsign": "<XYZ>"},
            ])
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
            ctx = {
                "state_dir": tmp, "now": now,
                "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
                "device_config": {"display_enabled": False, "quiet_hours_enabled": True,
                                  "quiet_hours_start": "22:00", "quiet_hours_end": "06:30"},
                "health_state": {"device_state": "ok", "pipeline_state": "warn",
                                 "battery_state": "ok", "device_html": "<b>d</b>",
                                 "pipeline_html": "<b>p</b>"},
                "poll_cooldown_remaining": 0,
            }
            rendered = home_page.render(ctx)
            for needle in (
                    '<h1 class="page-title">Home</h1>', "AFR1380", "Air France", "ORY → TLS",
                    'src="/gallery/2026-08-27T11-50-00+00-00.png"', "Switch on",
                    "On — 22:00 to 06:30", "Turn off", "Refresh now", "3750 mV",
                    'value="on"', "quick-action--off", "quick-action--on",
                    "≈ 50%"):
                if needle not in rendered:
                    return False, "expected %r in the Home page" % needle
            if "<XYZ>" in rendered or "&lt;XYZ&gt;" not in rendered:
                return False, "expected the hostile callsign to be escaped"
            if rendered.count("recent-flight ") != 2 and rendered.count('class="recent-flight"') != 2:
                return False, "expected exactly two recent-flight rows"
            cooled = home_page.render(dict(ctx, poll_cooldown_remaining=12))
            if "try again in 12s" not in cooled or "<button type=\"submit\" disabled>" not in cooled:
                return False, "expected the refresh widget to honour the cooldown"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "home_page.render() with seeded flights, a battery reading and a gallery entry renders the "
        "status tiles (with a battery percentage estimate), the current-panel image, the three "
        "quick-action widgets reflecting the saved state, escaped recent flights, and a disabled "
        "refresh control during the cooldown",
        _home_page_render_with_seeded_state)

    def _home_page_render_degrades_with_nothing():
        from companion.pages import home_page
        rendered = home_page.render({})
        for needle in (home_page.NO_FLIGHTS_HEADING, home_page.NO_PANEL_HEADING,
                       home_page.NO_READING_TEXT, "Quick actions"):
            if needle not in rendered:
                return False, "expected %r for an empty ctx" % needle
        if battery.battery_percent(4200) != 100 or battery.battery_percent(3300) != 0:
            return False, "expected the percentage estimate to clamp at the full/empty voltages"
        if battery.battery_percent("x") is not None or battery.battery_percent(0) is not None:
            return False, "expected a non-numeric or zero reading to yield None"
        if home_page._gallery_name_to_iso("2026-09-10T21-38-48+00-00.png") != "2026-09-10T21:38:48+00:00":
            return False, "expected the gallery filename to round-trip to its ISO timestamp"
        if home_page._gallery_name_to_iso("junk.png") is not None or home_page._gallery_name_to_iso(None) is not None:
            return False, "expected an unparseable gallery name to yield None"
        return True, ""
    check(
        "home_page.render({}) degrades to its empty states without raising, battery.battery_percent() "
        "clamps and rejects bad input, and the gallery filename parser round-trips or returns None",
        _home_page_render_degrades_with_nothing)

    def _battery_percent_moved_out_of_home_page():
        from companion.pages import home_page
        if hasattr(home_page, "battery_percent"):
            return False, "expected home_page.battery_percent to be gone after the D-01 move"
        return True, ""
    check(
        "battery_percent() no longer exists on home_page after moving to companion/battery.py (D-01)",
        _battery_percent_moved_out_of_home_page)

    def _battery_module_never_imports_pages_or_server():
        battery_path = os.path.join(REPO_ROOT, "companion", "battery.py")
        with open(battery_path, "r") as fh:
            source = fh.read()
        if "companion.pages" in source or "from server" in source:
            return False, (
                "expected companion/battery.py to never import companion.pages or server, "
                "keeping it usable by both home_page and health_page without either importing "
                "the other")
        return True, ""
    check(
        "companion/battery.py imports neither companion.pages nor server, preserving its "
        "shared, page-independent boundary (D-01)",
        _battery_module_never_imports_pages_or_server)

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        _seed_runway_events(harness.tmpdir, [
            {"ts": "2026-08-27T10:00:00+00:00", "hex": "e2e001", "callsign": "E2E001"},
        ])
        # A present panel.bin that changes nothing about the markup any
        # more is part of what this check proves (quick task 260903-c4o).
        _write_panel_file(harness.tmpdir)
        _seed_gallery(harness.tmpdir, ["20260827T100002Z.png"])

        def _history_preview_gallery_end_to_end():
            # 06.6.4.1-08 (D-22): /preview is retired as a page — this
            # subprocess-level check proves the redirect. Quick task
            # 260903-c4o further retires /preview.png outright (404 now,
            # not a real PNG) and upgrades this check to also prove the
            # route the per-row View-panel lightbox links to
            # (/gallery/{name}.png) genuinely serves full-resolution
            # bytes, against a real running service - the only consumer
            # of that route since quick task 260903-etm retired the
            # top-of-page render gallery.
            status, _headers, body = http_request(base + "/flights", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for /history, got %d" % status
            if b"Flights" not in body:
                return False, "expected the 'Flights' heading in /flights's response body"

            status, headers, body = http_request(base + "/preview", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect for /preview, got %d" % status
            if headers.get("Location") != "/flights":
                return False, "expected /preview to redirect to /history, got %r" % headers.get("Location")

            status, _headers, body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for the retired /preview.png route, got %d" % status

            status, headers, body = http_request(
                base + "/gallery/20260827T100002Z.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for a real /gallery/{name}.png, got %d" % status
            if not body.startswith(_PNG_SIGNATURE):
                return False, "expected a real PNG signature at the start of the gallery image body"
            content_type = headers.get("Content-Type", "")
            if content_type != "image/png":
                return False, "expected Content-Type: image/png, got %r" % content_type
            return True, ""
        check(
            "GET /history returns 200 with its own heading, GET /preview redirects (303) to "
            "/history, GET /preview.png now returns 404 (the route is retired), and GET "
            "/gallery/{name}.png returns 200 image/png with a real PNG signature — proving the "
            "route the per-row View-panel lightbox now links to genuinely serves full-resolution "
            "bytes, against a real running service",
            _history_preview_gallery_end_to_end)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("view-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
