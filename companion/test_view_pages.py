#!/usr/bin/env python3
"""Contract harness for companion/pages/history_page.py (CFG-06) and
companion/pages/preview_page.py (CFG-10/CFG-11).

Covers: the flight-history log's empty state, newest-first row ordering,
the two reused render-module presentation mappings (friendly aircraft-
type labels with a raw-designator fallback, the display-airline alias),
route-unavailable wording agreement with server/plane/render.py's own
ROUTE_FALLBACK_TEXT, monospace column styling, per-cell escaping
(including a markup-shaped callsign), degrade-not-raise behaviour
against an unreadable database; the live-preview image element and its
honest "no panel yet" fallback, the mandatory colour caveat, the render
gallery's empty state, its display-limit cap and newest-first ordering,
that the gallery never gains a form-input element or an import of
companion/app.py; and one end-to-end HTTP round trip proving
companion/app.py's router and both page modules agree, including a real
PNG fetched over /preview.png.

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
from companion.pages import history_page, preview_page  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import render as panel_render  # noqa: E402

TEST_PASSWORD = "view-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 20

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


def _history_ctx(state_dir):
    return {"state_dir": state_dir}


def _preview_ctx(state_dir, gallery_entries=None):
    return {"state_dir": state_dir, "gallery_entries": gallery_entries or []}


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
        tmp = _mkstate("h-mono")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "abc123", "callsign": "MONO1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count('class="mono"') < 3:
                return False, "expected at least 3 mono-styled cells (timestamp, callsign, hex)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "timestamp, callsign and hex columns carry the monospace CSS class",
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

    # ======================================================================
    # Section 2: companion/pages/preview_page.py
    # ======================================================================

    def _panel_present_one_image_one_caveat():
        tmp = _mkstate("p-present")
        try:
            _write_panel_file(tmp)
            rendered = preview_page.render(_preview_ctx(tmp))
            if rendered.count('src="/preview.png"') != 1:
                return False, "expected exactly one image element pointing at /preview.png"
            if rendered.count(preview_page.COLOUR_CAVEAT) != 1:
                return False, "expected the colour caveat sentence exactly once"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a valid panel file present renders exactly one preview image element and the colour caveat exactly once",
        _panel_present_one_image_one_caveat)

    def _no_panel_no_image_element():
        tmp = _mkstate("p-absent")
        try:
            rendered = preview_page.render(_preview_ctx(tmp))
            if 'src="/preview.png"' in rendered:
                return False, "did not expect an image element pointing at /preview.png with no panel file"
            if preview_page._NO_PANEL_CAPTION not in rendered:
                return False, "expected the honest no-panel-yet caption"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "no panel file renders no preview image element, with an honest caption instead",
        _no_panel_no_image_element)

    def _zero_gallery_entries_empty_state():
        tmp = _mkstate("p-gallery-empty")
        try:
            rendered = preview_page.render(_preview_ctx(tmp, gallery_entries=[]))
            if preview_page._NO_RENDERS_HEADING not in rendered:
                return False, "expected the render-gallery empty-state heading"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid element with zero entries"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "zero gallery entries render the render-gallery empty state and no gallery-grid element",
        _zero_gallery_entries_empty_state)

    def _gallery_entries_under_limit_one_tile_each():
        tmp = _mkstate("p-gallery-under")
        try:
            names = ["20260827T100002Z.png", "20260827T100001Z.png", "20260827T100000Z.png"]
            _seed_gallery(tmp, names)
            rendered = preview_page.render(_preview_ctx(tmp, gallery_entries=names))
            if rendered.count('class="gallery-tile"') != 3:
                return False, "expected exactly 3 gallery tiles"
            for name in names:
                if ("/gallery/%s" % name) not in rendered:
                    return False, "expected a gallery URL for %r" % name
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "gallery entries under the display limit render one tile per entry",
        _gallery_entries_under_limit_one_tile_each)

    def _gallery_entries_over_limit_capped_and_newest():
        tmp = _mkstate("p-gallery-over")
        try:
            # A fixed pool size, independent of preview_page.GALLERY_DISPLAY_LIMIT
            # itself (T-06-09 acceptance criterion: deliberately raising the
            # module's constant must make this check fail, not just generate a
            # bigger fixture) - list slicing can never produce more tiles than
            # this pool has entries, so an inflated limit constant is caught
            # the moment tile_count stops matching GALLERY_DISPLAY_LIMIT.
            total = 30
            names = ["20260827T1%05dZ.png" % i for i in range(total)]
            names_newest_first = sorted(names, reverse=True)
            _seed_gallery(tmp, names)
            rendered = preview_page.render(_preview_ctx(tmp, gallery_entries=names_newest_first))
            tile_count = rendered.count('class="gallery-tile"')
            if tile_count != preview_page.GALLERY_DISPLAY_LIMIT:
                return False, "expected exactly GALLERY_DISPLAY_LIMIT=%d tiles, got %d" % (
                    preview_page.GALLERY_DISPLAY_LIMIT, tile_count)
            newest_name = names_newest_first[0]
            oldest_name = names_newest_first[-1]
            if ("/gallery/%s" % newest_name) not in rendered:
                return False, "expected the newest gallery entry to be tiled"
            if ("/gallery/%s" % oldest_name) in rendered:
                return False, "did not expect the oldest gallery entry to be tiled (cap must keep the newest)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "gallery entries over the display limit render exactly GALLERY_DISPLAY_LIMIT tiles, keeping the newest",
        _gallery_entries_over_limit_capped_and_newest)

    def _preview_page_never_imports_app():
        with open(os.path.join(HERE, "pages", "preview_page.py")) as fh:
            source = fh.read()
        if "import companion.app" in source or "from companion import app" in source:
            return False, "preview_page.py must never import companion.app (router-import cycle)"
        return True, ""
    check(
        "companion/pages/preview_page.py never imports companion.app",
        _preview_page_never_imports_app)

    def _preview_page_no_input_element():
        with open(os.path.join(HERE, "pages", "preview_page.py")) as fh:
            source = fh.read()
        if "<input" in source:
            return False, "preview_page.py must contain no <input element (D-20's deferred simulate-a-flight control)"
        return True, ""
    check(
        "companion/pages/preview_page.py contains no <input element",
        _preview_page_no_input_element)

    def _every_image_has_nonempty_alt():
        tmp = _mkstate("p-alt")
        try:
            _write_panel_file(tmp)
            names = ["20260827T100000Z.png"]
            _seed_gallery(tmp, names)
            rendered = preview_page.render(_preview_ctx(tmp, gallery_entries=names))
            if _img_tag_count(rendered) < 2:
                return False, "expected at least 2 <img elements (preview + one gallery tile)"
            for alt in _img_alt_values(rendered):
                if not alt:
                    return False, "found an <img with an empty alt attribute"
            if _img_tag_count(rendered) != len(_img_alt_values(rendered)):
                return False, "found an <img with no alt attribute at all"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every <img element on the Preview page carries a non-empty alt attribute",
        _every_image_has_nonempty_alt)

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

        def _tabs_and_preview_image_end_to_end():
            for path, heading in (("/history", "History"), ("/preview", "Preview")):
                status, _headers, body = http_request(base + path, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200 for %s, got %d" % (path, status)
                if heading.encode() not in body:
                    return False, "expected the %r heading in %s's response body" % (heading, path)

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
            "GET /history and GET /preview return 200 with their own heading, and GET /preview.png returns a real PNG, against a real running service",
            _tabs_and_preview_image_end_to_end)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("view-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
