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
against an unreadable database; History's own Now-showing live-preview
image element and its honest "no panel yet" fallback, the mandatory
colour caveat, the Recent-renders disclosure's empty state, its
display-limit cap and newest-first ordering, that the gallery filename-
timestamp helper degrades safely and a malformed filename still renders
a non-empty caption, the per-row View-panel lookup and shared lightbox,
the unresolved-airline link to Health; and one end-to-end HTTP round
trip proving companion/app.py's router and this page module agree,
including a real PNG fetched over /preview.png (still served — only the
standalone Preview HTML page route was retired) and the retired
/preview page route's redirect to /history.

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
import companion.layout as layout  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import render as panel_render  # noqa: E402

TEST_PASSWORD = "view-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 45  # 44 + 1 (quick task 260902-w4t Task 1, UIR-05:
# _airline_fallback_distinct_from_route_fallback - a no-airline row's
# AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT are distinct strings in
# distinct columns, and the unresolved-link's UNRESOLVED_LINK_CLASS is
# styled in style.css and present on the rendered anchor).
# 44 = 43 + 1 (quick task 260902-tli Task 2: the
# airlines_page/history_page cross-module LIGHTBOX_DIALOG_ID/
# _VIEW_PANEL_*_ATTR equality guard. _lightbox_dom_contract_three_file_
# guard() was widened in place to also assert the six shared tokens
# against a real airlines_page.render() output - no count change from
# that retarget).
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


def _img_alt_values(rendered):
    return re.findall(r'<img\b[^>]*\balt="([^"]*)"', rendered)


def _img_tag_count(rendered):
    return len(re.findall(r"<img\b", rendered))


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
            if '<h1 class="page-title">History</h1>' not in rendered:
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
            if '<div class="data-table-wrap">' not in rendered:
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

    def _seven_columns_named_and_ordered():
        # 06.6.1-02 (D-02): proves the 9->7 column reduction shipped - the
        # header labels come from history_page._HEADERS itself (the
        # contract), not a re-typed literal list.
        tmp = _mkstate("h-7col")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d6", "callsign": "SEVEN1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            th_count = len(re.findall(r"<th>", rendered))
            if th_count != 7:
                return False, "expected exactly 7 <th> cells, got %d" % th_count
            positions = []
            for header in history_page._HEADERS:
                idx = rendered.find("<th>%s</th>" % header)
                if idx == -1:
                    return False, "expected header %r to appear as a <th>" % header
                positions.append(idx)
            if positions != sorted(positions):
                return False, "expected the 7 headers in history_page._HEADERS' own left-to-right order"
            if "<th>Hex</th>" in rendered or "<th>Airline</th>" in rendered:
                return False, "did not expect standalone Hex/Airline header cells after the merge"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History renders exactly the 7 headers in history_page._HEADERS, in order, with no standalone Hex/Airline column",
        _seven_columns_named_and_ordered)

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
        # D-03: health_page._CORROBORATION_ROWS is the canonical
        # (stored, label, status, explanation) table; history_page's own
        # hand-maintained _CORROBORATION_LABELS must stay equal to it,
        # key by key, so the two pages read consistently and so a future
        # edit to either table cannot silently drift from the other.
        health_rows = {
            stored: (status, label)
            for stored, label, status, _explanation in health_page._CORROBORATION_ROWS
        }
        history_labels = history_page._CORROBORATION_LABELS

        if set(health_rows) != {"True", "None", "False"}:
            return False, "expected health_page._CORROBORATION_ROWS to cover exactly True/None/False"
        if set(history_labels) != {"True", "None", "False"}:
            return False, "expected history_page._CORROBORATION_LABELS to cover exactly True/None/False"

        for key in ("True", "None", "False"):
            if history_labels[key] != health_rows[key]:
                return False, (
                    "corroboration copy drifted for %r: history_page has %r, "
                    "health_page has %r" % (key, history_labels[key], health_rows[key]))

        # D-03/D-15: the single-source, uncorroborated "None" state is a
        # genuinely unknown state, not a failure — it must stay "ok" in
        # both tables, never a warning or an error.
        if history_labels["None"][0] != "ok":
            return False, "expected history_page's 'None' (single-source) status to be 'ok', not a failure"
        if health_rows["None"][0] != "ok":
            return False, "expected health_page's 'None' (single-source) status to be 'ok', not a failure"

        return True, ""
    check(
        "history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS key-by-key, and the single-source 'None' state is never labelled a failure in either table",
        _corroboration_copy_agrees_with_health_page)

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
    # Section 1b: 06.6.4.1-05 Task 1 - History's own Now-showing section
    # and collapsed Recent-renders disclosure (D-18/D-19), moved from
    # companion/pages/preview_page.py.
    # ======================================================================

    def _now_showing_panel_present_one_image_one_caveat():
        tmp = _mkstate("h-now-showing-present")
        try:
            _write_panel_file(tmp)
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count('class="preview-frame"') != 1:
                return False, "expected exactly one .preview-frame element"
            if rendered.count('src="/preview.png"') != 1:
                return False, "expected exactly one image element pointing at /preview.png"
            if "Captured " not in rendered:
                return False, "expected the captured-at caption wording"
            if rendered.count(history_page.COLOUR_CAVEAT) != 1:
                return False, "expected the colour caveat sentence exactly once"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Now-showing section renders one .preview-frame, one preview image, a "
        "captured-at caption, and the colour caveat exactly once when a panel file exists",
        _now_showing_panel_present_one_image_one_caveat)

    def _now_showing_no_panel_no_image_element():
        tmp = _mkstate("h-now-showing-absent")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if 'src="/preview.png"' in rendered:
                return False, "did not expect a preview image element with no panel file"
            if 'class="preview-frame"' in rendered:
                return False, "did not expect a .preview-frame element with no panel file"
            if history_page._NO_PANEL_CAPTION not in rendered:
                return False, "expected the honest no-panel-yet caption"
            if rendered.count(history_page.COLOUR_CAVEAT) != 1:
                return False, "expected the colour caveat sentence exactly once"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Now-showing section renders no .preview-frame and no preview image element "
        "with no panel file, still with the honest caption and the colour caveat exactly once",
        _now_showing_no_panel_no_image_element)

    def _recent_renders_disclosure_closed_by_default_correct_count():
        tmp = _mkstate("h-recent-renders")
        try:
            names = ["20260827T100002Z.png", "20260827T100001Z.png", "20260827T100000Z.png"]
            _seed_gallery(tmp, names)
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            if '<details class="readings-disclosure"><summary>Recent renders' not in rendered:
                return False, (
                    "expected a readings-disclosure details element (no open attribute) "
                    "with a Recent renders summary")
            match = re.search(
                r'<details class="readings-disclosure"><summary>(Recent renders \(\d+\))'
                r'</summary>(.*?)</details>', rendered, re.S)
            if not match:
                return False, "expected a readings-disclosure details element with a Recent renders summary"
            summary_text = match.group(1)
            tile_count_in_disclosure = match.group(2).count('class="gallery-tile"')
            if summary_text != ("Recent renders (%d)" % tile_count_in_disclosure):
                return False, (
                    "expected the summary count %r to equal the number of "
                    "gallery-tile elements actually rendered (%d)"
                    % (summary_text, tile_count_in_disclosure))
            if tile_count_in_disclosure != 3:
                return False, "expected exactly 3 gallery tiles for 3 seeded entries"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Recent-renders disclosure is collapsed by default (no open attribute) and its "
        "summary count equals the number of gallery-tile elements actually rendered inside it",
        _recent_renders_disclosure_closed_by_default_correct_count)

    def _recent_renders_disclosure_empty_gallery():
        tmp = _mkstate("h-recent-renders-empty")
        try:
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=[]))
            if history_page._NO_RENDERS_HEADING not in rendered:
                return False, "expected the render-gallery empty-state heading"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid element with zero entries"
            if "Recent renders (0)" not in rendered:
                return False, "expected the disclosure summary to read 'Recent renders (0)'"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Recent-renders disclosure shows the existing no-renders empty state and a "
        "'Recent renders (0)' summary with an empty gallery entry list",
        _recent_renders_disclosure_empty_gallery)

    def _now_showing_no_preview_freshness_apparatus():
        # D-18: Preview's page-level freshness apparatus (its own
        # data-loaded-at Refresh link and paired data-stale-banner) was
        # deliberately not ported - only preview_section()'s content
        # moved.
        tmp = _mkstate("h-no-freshness")
        try:
            _write_panel_file(tmp)
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

    def _recent_renders_malformed_filename_caption_fallback():
        # Carried over here (06.6.4.1-08 Task 3) from
        # companion/pages/preview_page.py's own now-deleted coverage: a
        # manually-dropped or renamed gallery file must still render a
        # tile with a non-empty raw-filename-derived caption, never
        # raising and never a blank caption.
        tmp = _mkstate("h-gallery-malformed")
        try:
            names = ["not-a-real-gallery-name.png"]
            _seed_gallery(tmp, names)
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            if 'class="gallery-tile"' not in rendered:
                return False, "expected a gallery tile to still render for a malformed filename"
            if '<p class="text-label mono"></p>' in rendered:
                return False, "did not expect a blank caption for a malformed filename"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Recent-renders disclosure still renders a tile with a non-empty "
        "raw-filename-derived caption for a malformed gallery filename, never raising",
        _recent_renders_malformed_filename_caption_fallback)

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

    def _row_block(rendered, tag, group_index):
        pattern = r"<%s[^>]*data-filter-group=\"%d\"[^>]*>(.*?)</%s>" % (
            tag, group_index, tag)
        match = re.search(pattern, rendered, re.S)
        return match.group(1) if match else None

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
                expected_caption = history_page.LIGHTBOX_CAPTION_TEMPLATE % expected_iso

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
        # Source/DOM-contract guard: LIGHTBOX_DIALOG_ID, the two trigger
        # attribute names, and the three lightbox element class names
        # must each appear in panel-lookup.js's source, and in the
        # rendered markup of every page that shares this mechanism -
        # since quick task 260902-tli that is both History and the
        # Airlines gallery (widened from History-only). A drift in any
        # of the three would leave the button silently doing nothing
        # with no signal from any file in isolation.
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

        tokens = (
            history_page.LIGHTBOX_DIALOG_ID,
            "data-view-panel-src",
            "data-view-panel-caption",
            "lightbox__image",
            "lightbox__caption",
            "lightbox__note",
        )
        for token in tokens:
            if token not in js_source:
                return False, "expected %r to appear in companion/static/panel-lookup.js" % token
            if token not in history_rendered:
                return False, "expected %r to appear in the rendered History page" % token
            if token not in airlines_rendered:
                return False, "expected %r to appear in the rendered Airlines page" % token
        return True, ""
    check(
        "LIGHTBOX_DIALOG_ID, the two data-view-panel-* trigger attribute names, and the three "
        "lightbox__* element class names each appear in companion/static/panel-lookup.js and in "
        "the rendered markup of both History and the Airlines gallery (quick task 260902-tli)",
        _lightbox_dom_contract_three_file_guard)

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
    # logged in, fetching both tab routes and the preview image route.
    # ======================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        _seed_runway_events(harness.tmpdir, [
            {"ts": "2026-08-27T10:00:00+00:00", "hex": "e2e001", "callsign": "E2E001"},
        ])
        _write_panel_file(harness.tmpdir)

        def _history_preview_redirect_and_preview_image_end_to_end():
            # 06.6.4.1-08 (D-22): /preview is retired as a page — this
            # subprocess-level check proves the redirect, and that
            # deleting preview_page.py did not remove anything
            # /preview.png's byte-serving route still calls into.
            status, _headers, body = http_request(base + "/history", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for /history, got %d" % status
            if b"History" not in body:
                return False, "expected the 'History' heading in /history's response body"

            status, headers, body = http_request(base + "/preview", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect for /preview, got %d" % status
            if headers.get("Location") != "/history":
                return False, "expected /preview to redirect to /history, got %r" % headers.get("Location")

            status, headers, body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for /preview.png, got %d" % status
            if not body.startswith(_PNG_SIGNATURE):
                return False, "expected a real PNG signature at the start of /preview.png's body"
            content_type = headers.get("Content-Type", "")
            if content_type != "image/png":
                return False, "expected Content-Type: image/png, got %r" % content_type
            return True, ""
        check(
            "GET /history returns 200 with its own heading, GET /preview redirects (303) to "
            "/history, and GET /preview.png still returns a real PNG — proving the deleted "
            "preview_page.py module removed nothing the byte-serving routes still call into, "
            "against a real running service",
            _history_preview_redirect_and_preview_image_end_to_end)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("view-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
