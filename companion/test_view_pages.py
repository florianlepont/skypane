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
import ast
import inspect
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
import companion.draw as draw  # noqa: E402
import companion.layout as layout  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import render as panel_render  # noqa: E402

TEST_PASSWORD = "view-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0

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


def _history_ctx(state_dir, now=None, gallery_entries=None, flights_limit=None):
    return {
        "state_dir": state_dir,
        "now": now or history_db.utc_now_iso(),
        "gallery_entries": gallery_entries or [],
        # 29-03-PLAN.md Task 1 (CFG-83): the raw `?limit=` value, mirroring
        # app.py's own ctx key exactly (None when the caller does not care).
        "flights_limit": flights_limit,
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


EXPECTED_CHECK_COUNT = 35  # 169 - 37 - 59 - 38 (33-05: part 01; 33-06: part 02; 33-07: part 03 to test_view_pages_03.py)
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

    def _home_page_full_seeded_render_french_end_to_end():
        from companion.pages import home_page
        from server import history_db as _hdb
        import companion.prefs as _prefs
        tmp = _mkstate("home-fr")
        try:
            now = "2026-08-27T12:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
                 "airline": "Air France", "origin": "ORY", "destination": "TLS",
                 "confirmed_state": "departing"},
            ])
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
            ctx = {
                "state_dir": tmp, "now": now,
                "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
                "last_checkin_ts": "2026-08-27T11:55:00+00:00",
                "device_config": {"wake_interval_s": 900, "display_enabled": True},
                "health_state": {"device_state": "ok", "pipeline_state": "warn",
                                 "battery_state": "ok",
                                 "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                                 "pipeline_html": "<p>A little stale</p>"},
                "simple_mode": False,
            }
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered_fr = home_page.render(ctx)
            finally:
                _prefs.set_request_prefs(lang="en")
            for needle in (
                    ">Accueil<", "Vols récents", "Voir tous les vols", "Cadre", "Batterie",
                    "Données de vol", "Au départ"):
                if needle not in rendered_fr:
                    return False, "expected the French %r in the French Home render" % (needle,)
            if "Prochaine mise à jour" not in rendered_fr and "Attendue depuis" not in rendered_fr:
                return False, "expected either French next-update headline wording"
            for english_only in (
                    "Recent flights", "See all flights", ">Frame<", ">Battery<", "Departing"):
                if english_only in rendered_fr:
                    return False, "expected no English %r leaking into the French render" % (
                        english_only,)
            if "AFR1380" not in rendered_fr or "Air France" not in rendered_fr:
                return False, "expected the callsign/airline data to stay untranslated in French"

            rendered_en = home_page.render(ctx)
            for needle in (
                    '<h1 class="page-title">Home</h1>', "Recent flights", "See all flights",
                    home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL,
                    home_page.DATA_ROW_LABEL, "Next update ≈"):
                if needle not in rendered_en:
                    return False, "expected the English %r in the default-language Home render" % (
                        needle,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-seeded Home render under lang='fr' shows the French page title, section "
        "headings, status-row labels and next-update headline with no English string leaking "
        "in (while the callsign/airline data stays untranslated), and the identical seeded "
        "render under the default language still carries every pre-existing English needle",
        _home_page_full_seeded_render_french_end_to_end)

    def _home_status_card_localises_real_health_state_timestamps_under_french():
        # Polish fix 2: unlike the check above (which hand-builds
        # ctx["health_state"] with already-English literal fragments,
        # never exercising the real timestamp-formatting path), this
        # check derives ctx["health_state"] from a REAL health_page.
        # compute_health_state() call — the exact value companion/
        # app.py's page_context() threads into every authenticated
        # page's ctx — with `now` on a different calendar day from
        # every seeded timestamp, so a surviving English month
        # abbreviation or "ago" is unmistakable.
        #
        # 22-07-PLAN.md Task 1 (B2) RETARGET: this check used to also
        # assert the Flight-data row's detail joined its verdict/
        # timestamp/last-detection clauses with " · " — that was
        # exercising the OLD re-embedded-pipeline_html defect this very
        # plan removes. Home now reads pipeline_detail_html (health_
        # page.py's verdict-free, SINGLE-clause sibling of pipeline_
        # html, 22-03-PLAN.md), so the Flight-data row's detail is one
        # clause, not three, and never joins anything with " · " at
        # all — the assertion below is flipped to pin exactly that.
        from companion.pages import home_page
        from server import history_db as _hdb
        import companion.prefs as _prefs
        tmp = _mkstate("home-fr-health")
        try:
            now = "2026-09-12T00:00:00+00:00"
            device_ts = "2026-09-10T23:58:00+00:00"
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, device_ts, battery_mv=3800)
                _hdb.set_meta(conn, _hdb.META_LAST_PIPELINE_RUN, device_ts)
                _hdb.set_meta(conn, _hdb.META_LAST_DETECTION, device_ts)
            try:
                _prefs.set_request_prefs(lang="fr")
                health_state = health_page.compute_health_state(tmp, now=now)
                ctx = {
                    "state_dir": tmp, "now": now, "gallery_entries": [],
                    "last_checkin_ts": device_ts,
                    "device_config": {"wake_interval_s": 900, "display_enabled": True},
                    "health_state": health_state, "simple_mode": False,
                }
                rendered = home_page.render(ctx)
            finally:
                _prefs.set_request_prefs(lang="en")
            if "sept." not in rendered:
                return False, "expected the French month abbreviation 'sept.' in the Home render"
            if " ago" in rendered:
                return False, "expected no English ' ago' in the Home render"
            for english_month in (
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                    "Oct", "Nov", "Dec"):
                if english_month in rendered:
                    return False, "expected no English month abbreviation %r in the Home render" % (
                        english_month,)
            # "Données de vol" is companion/i18n_fr/home.py's own French
            # translation of DATA_ROW_LABEL ("Flight data") — the label
            # itself is French text by this point in the render, so the
            # anchor must be too.
            data_row_start = rendered.index("Données de vol")
            data_row_end = rendered.index("</div>", data_row_start)
            data_row = rendered[data_row_start:data_row_end]
            if data_row.count(" · ") != 0:
                return False, (
                    "expected NO ' · '-joined multi-clause detail in the Flight-data row — "
                    "22-07-PLAN.md Task 1 (B2) replaced the re-embedded 3-clause pipeline_html "
                    "with the verdict-free, single-clause pipeline_detail_html (got %r)"
                    % (data_row,))
            if health_page.PIPELINE_STATE_TEXT["error"] in data_row:
                return False, (
                    "expected Health's own PIPELINE_STATE_TEXT verdict wording NOT to appear "
                    "inside Home's Flight-data row — Home renders its OWN verdict only (B2)")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's status card, fed a REAL health_page.compute_health_state() result computed "
        "under lang='fr', fully localises the Frame/Flight-data rows' timestamps (no English "
        "month abbreviation or ' ago' survives) and the Flight-data row's detail is now a "
        "single, verdict-free clause — never joined with ' · ', never repeating Health's own "
        "verdict wording (Polish fix 2 / 22-07-PLAN.md Task 1 B2 retarget)",
        _home_status_card_localises_real_health_state_timestamps_under_french)

    # --- 22-07-PLAN.md Task 1 (X2/B2/X4): Home reads one frame state, one
    # pipeline detail and one airline name -----------------------------

    def _home_frame_tile_matches_strip_for_the_nightly_held_regression():
        # The exact X2 nightly false alarm fixture (22-UI-SPEC.md §3.3
        # rule 6, mirrored from test_status_pages.py's own
        # _frame_strip_nightly_regression_held_is_neutral_never_warn):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00
        # Europe/Paris. battery_state/pipeline_state are pinned "ok" in
        # the fixture so the warn/error scan below is unambiguously
        # about the Frame signal alone, not an unrelated tile.
        from companion.pages import home_page
        from datetime import datetime, timezone, timedelta
        paris = timezone(timedelta(hours=1))
        device_cfg = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
        ctx = {
            "last_checkin_ts": checkin.isoformat(), "device_config": device_cfg,
            "now": clock.isoformat(), "gallery_entries": [],
            "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        rendered = home_page.render(ctx)
        for warn_token in ("dot--warn", "dot--error", "stat-tile--warn", "stat-tile--error"):
            if warn_token in rendered:
                return False, "expected zero %r in a held Home render, found it" % (warn_token,)
        strip_match = re.search(r'time-value time-value--primary">([^<]+)</span>', rendered)
        tile_match = re.search(r'<span class="time-value">([^<]+)</span>', rendered)
        if not strip_match or not tile_match:
            return False, "expected both the strip and the Frame tile to render a clock value"
        if strip_match.group(1) != tile_match.group(1):
            return False, (
                "expected the SAME clock string in the strip and the Frame tile, got %r vs %r"
                % (strip_match.group(1), tile_match.group(1)))
        if home_page.FRAME_STATE_TEXT["off"] not in rendered:
            return False, "expected the held Frame tile's own neutral verdict text"
        return True, ""
    check(
        "the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/"
        "Paris): Home's Frame tile and the strip render the SAME clock string, and zero warn/"
        "error tokens appear anywhere on the page (X2, D-03/CFG-26)",
        _home_frame_tile_matches_strip_for_the_nightly_held_regression)

    def _home_frame_tile_flips_to_late_together_with_the_strip():
        from companion.pages import home_page
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        ctx = {
            "last_checkin_ts": "2026-08-27T11:00:00+00:00", "device_config": device_cfg,
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
            "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        rendered = home_page.render(ctx)
        if "Expected since" not in rendered:
            return False, "expected the strip's own late headline"
        if "dot--warn" not in rendered:
            return False, "expected the strip's own warn dot for a late frame"
        if home_page.FRAME_STATE_TEXT["warn"] not in rendered:
            return False, "expected the Frame tile's own late verdict text"
        if "stat-tile stat-tile--warn" not in rendered:
            return False, "expected the Frame tile's own warn border class"
        return True, ""
    check(
        "a late frame flips the strip to 'Expected since'/dot--warn and Home's Frame tile to "
        "its own late verdict/stat-tile--warn together, at the same threshold — they cannot "
        "disagree because neither computes anything the other does not (X2)",
        _home_frame_tile_flips_to_late_together_with_the_strip)

    def _home_flight_data_tile_one_verdict_verdict_free_detail():
        from companion.pages import home_page
        ctx = {
            "health_state": {
                "device_state": "ok", "pipeline_state": "warn", "battery_state": "ok",
                "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                "pipeline_html": (
                    '<p>%s</p><p>10 Sep 23:58 (1d ago)</p>' % health_page.PIPELINE_STATE_TEXT["warn"]),
                "pipeline_detail_html": '<span class="mono">10 Sep 23:58 (1d ago)</span>',
            },
            "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        }
        rendered = home_page.render(ctx)
        if rendered.count(home_page.DATA_STATE_TEXT["warn"]) != 1:
            return False, "expected Home's own Flight-data verdict exactly once"
        if health_page.PIPELINE_STATE_TEXT["warn"] in rendered:
            return False, (
                "expected Health's own pipeline verdict text NOT to appear on Home — re-"
                "embedding it is the exact double-verdict stacking B2 removes")
        if "10 Sep 23:58" not in rendered:
            return False, "expected the verdict-free pipeline_detail_html's own timestamp to render"
        return True, ""
    check(
        "Home's Flight-data tile renders exactly one verdict (its own DATA_STATE_TEXT) with "
        "Health's verdict-free pipeline_detail_html beneath it, never Health's own "
        "PIPELINE_STATE_TEXT verdict sentence a second time (B2)",
        _home_flight_data_tile_one_verdict_verdict_free_detail)

    def _home_recent_flights_use_display_airline_name_matching_flights():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home-airline-alias")
        try:
            with _hdb.open_db(tmp) as conn:
                _hdb.record_runway_event(
                    conn, ts="2026-08-27T11:50:00+00:00", hex="3c6444", callsign="CCM123",
                    airline="CCM Airlines", origin="ORY", destination="AJA",
                    confirmed_state="departing")
            ctx = {
                "state_dir": tmp, "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
                "health_state": {}, "device_config": {},
            }
            rendered = home_page.render(ctx)
            if "Air Corsica" not in rendered:
                return False, "expected the aliased display name 'Air Corsica' on Home"
            if "CCM Airlines" in rendered:
                return False, "expected the raw upstream airline string not to leak onto Home"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a recent-flight row whose stored airline is an alias (\"CCM Airlines\") renders the "
        "SAME display name (\"Air Corsica\") Flights shows via display_airline_name(), never "
        "the raw upstream string (X4)",
        _home_recent_flights_use_display_airline_name_matching_flights)

    def _home_exactly_one_element_named_frame():
        from companion.pages import home_page
        ctx = {
            "health_state": {}, "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        }
        rendered = home_page.render(ctx)
        if rendered.count(">Frame<") != 1:
            return False, (
                "expected exactly one element named 'Frame' (the strip's own heading), got %d"
                % (rendered.count(">Frame<"),))
        if home_page.FRAME_ROW_LABEL == "Frame":
            return False, "expected the tile caption to be renamed away from 'Frame' (X4 collision)"
        if home_page.FRAME_ROW_LABEL not in rendered:
            return False, "expected the renamed tile caption to still render"
        return True, ""
    check(
        "exactly one element on a rendered Home page is named 'Frame' (the shared strip's own "
        "heading) — Home's tile caption is renamed to resolve the X4 collision",
        _home_exactly_one_element_named_frame)

    # --- 22-07-PLAN.md Task 2 (B18/B2): one line for the time, one height
    # for the tiles, one weight for the thumbnails -----------------------

    def _home_recent_flight_time_one_line_no_mono_class():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home-time-one-line")
        try:
            with _hdb.open_db(tmp) as conn:
                _hdb.record_runway_event(
                    conn, ts="2026-08-27T11:35:00+00:00", hex="3c6444", callsign="AFR1380",
                    airline="Air France", origin="ORY", destination="TLS",
                    confirmed_state="departing")
            ctx = {
                "state_dir": tmp, "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
                "health_state": {}, "device_config": {},
            }
            rendered = home_page.render(ctx)
            start = rendered.index('class="recent-flight__time')
            end = rendered.index("</li>", start)
            time_cell = rendered[start:end]
            if "mono" in time_cell:
                return False, "expected no monospace class in the recent-flight time cell"
            if 'class="time-value"' not in time_cell:
                return False, "expected the clock to carry the .time-value role"
            if 'class="cell-inline-sep"' not in time_cell:
                return False, "expected the existing .cell-inline-sep middle dot"
            if 'class="time-value__age"' not in time_cell:
                return False, "expected the relative age in the .time-value__age muted role"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the recent-flight time cell markup carries no monospace class, and reads the clock "
        "(.time-value), the existing .cell-inline-sep middle dot and the relative age "
        "(.time-value__age) as one line (B18)",
        _home_recent_flight_time_one_line_no_mono_class)

    def _home_status_grid_declares_align_items_stretch_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        start = css_source.index(".home-status-grid {")
        end = css_source.index("}", start)
        block = css_source[start:end]
        if "align-items: stretch" not in block:
            return False, "expected .home-status-grid to declare align-items: stretch (B2)"
        return True, ""
    check(
        ".home-status-grid's own CSS rule declares align-items: stretch (B2)",
        _home_status_grid_declares_align_items_stretch_in_css)

    def _recent_flight_time_nowrap_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        # .recent-flight__time appears in TWO rules — a shared colour-only
        # rule with .recent-flight__detail, and its own dedicated rule
        # (text-align/justify-self/white-space). The bare selector text
        # cannot anchor this lookup: the shared rule ends in the IDENTICAL
        # ".recent-flight__time {" and comes first in source order. So
        # anchor on a declaration unique to the dedicated rule.
        #
        # Quick task 260913-bjy: that anchor used to be the percentage
        # width cap, which this task deleted — it clamped the box to 60%
        # of its OWN max-content (the item sits in a content-sized `auto`
        # grid track, so the percentage resolved against the very content
        # it bounded) and painted the relative age outside the card at
        # every width, off the right edge of a 390px viewport. The anchor
        # moved to the grid end-alignment declaration, verified unique in
        # the stylesheet. It is deliberately a DIFFERENT declaration from
        # the asserted one, so this check still fails if `white-space:
        # nowrap` alone is ever dropped.
        #
        # Quick task 260913-dgh: that anchor is gone in turn — the row is
        # a wrapping flex line now, so a grid-only self-alignment would
        # have been a dead declaration. The anchor moves to the auto
        # inline-start margin that replaced it, re-verified as the single
        # occurrence in the stylesheet (the only other `margin-inline-
        # start` there carries a length, not the keyword). The
        # different-declaration property above is preserved: the anchor
        # is still not the assertion.
        start = css_source.index("margin-inline-start: auto")
        block_start = css_source.rindex("{", 0, start)
        end = css_source.index("}", start)
        block = css_source[block_start:end]
        if "white-space: nowrap" not in block:
            return False, "expected .recent-flight__time to declare white-space: nowrap (B18)"
        return True, ""
    check(
        ".recent-flight__time's own CSS rule declares white-space: nowrap so the clock/age "
        "pair can never wrap onto a second line (B18)",
        _recent_flight_time_nowrap_in_css)

    def _recent_flight_thumbnails_share_the_shipped_treatments_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        # The real thumbnail joins the shared white-backing/hairline/
        # radius rule .now-showing__image/.preview-frame__image already
        # carry — tag-qualified (img.recent-flight__thumb) so it can
        # never accidentally match the placeholder <span>, which shares
        # the bare .recent-flight__thumb class for its own 40x40 sizing.
        shared_start = css_source.index(".now-showing__image,")
        shared_end = css_source.index("}", shared_start)
        shared_block = css_source[shared_start:shared_end]
        if "img.recent-flight__thumb" not in shared_block:
            return False, (
                "expected img.recent-flight__thumb to join the shared white-backing/hairline/"
                "radius rule (B18)")
        # The placeholder's own dashed/canvas-fill values string-equal
        # .airline-card__placeholder's (reused BY VALUE, never a new
        # literal) — NOT selector-shared with it, since companion/
        # test_status_pages.py (a sibling plan's file this plan may not
        # edit) pins ".airline-card__placeholder {" as a standalone
        # selector whose own rule body alone carries all five of its
        # declarations.
        if ".airline-card__placeholder,\n.recent-flight__thumb--placeholder" in css_source:
            return False, (
                "expected .airline-card__placeholder's OWN selector to stay standalone — "
                "companion/test_status_pages.py pins it as such")
        placeholder_start = css_source.index(".recent-flight__thumb--placeholder {\n  border:")
        placeholder_end = css_source.index("}", placeholder_start)
        placeholder_block = css_source[placeholder_start:placeholder_end]
        for expected in (
                "border: 1px dashed var(--color-border)", "background: var(--color-canvas)"):
            if expected not in placeholder_block:
                return False, (
                    "expected .recent-flight__thumb--placeholder's own rule to reuse %r "
                    "(the exact value .airline-card__placeholder declares) (B18)" % (expected,))
        return True, ""
    check(
        "the real recent-flight thumbnail joins the shared white-backing/hairline/radius rule "
        "and the placeholder's own rule reuses .airline-card__placeholder's exact dashed/"
        "canvas-fill values (never a new literal, never sharing that pinned selector), so a "
        "missing thumbnail matches the real ones in weight (B18)",
        _recent_flight_thumbnails_share_the_shipped_treatments_in_css)

    def _single_has_supports_block_unmoved():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        count = css_source.count("@supports selector(:has(*)) {")
        if count != 1:
            return False, "expected exactly one @supports selector(:has(*)) block, got %d" % count
        return True, ""
    check(
        "companion/static/style.css still carries exactly one @supports selector(:has(*)) "
        "block — this plan opens no second one",
        _single_has_supports_block_unmoved)

    def _home_catalog_keys_all_present_in_merged_catalog():
        import companion.i18n_fr as i18n_fr
        import companion.i18n_fr.home as i18n_fr_home
        missing = [k for k in i18n_fr_home.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from the merged CATALOG: %r" % (missing,)
        return True, ""
    check(
        "every key in companion/i18n_fr/home.py's own CATALOG is also a key of the merged "
        "companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up",
        _home_catalog_keys_all_present_in_merged_catalog)

    def _home_page_full_render_has_quick_action_only_inside_the_strip_and_three_tiles():
        # 21-04-PLAN.md Task 3 (D-04/D-05): retargeted — D-01 puts the
        # Screen/Quiet-hours instant switches ON Home now, inside the
        # shared Frame strip, so "no quick-action anywhere" (the old
        # D-16 assertion) is no longer the correct claim; the new claim
        # is "quick-action markup exists exactly once, inside the
        # strip, and nowhere else on the page."
        from companion.pages import home_page
        ctx = {
            "health_state": {"device_state": "ok", "pipeline_state": "ok", "battery_state": "ok"},
            "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00",
        }
        rendered = home_page.render(ctx)
        if "status-card__rows" in rendered or "home-hero" in rendered:
            return False, "expected no status-card__rows or home-hero markup on the rebuilt Home page"
        strip_start = rendered.index('class="frame-strip stat-tile stat-tile--accent"')
        tiles_start = rendered.index('class="dashboard-grid home-status-grid"')
        outside_strip = rendered[:strip_start] + rendered[tiles_start:]
        if "quick-action" in outside_strip:
            return False, "expected no quick-action markup anywhere outside .frame-strip"
        strip_segment = rendered[strip_start:tiles_start]
        on_off_count = strip_segment.count("quick-action--on") + strip_segment.count("quick-action--off")
        if on_off_count != 2:
            return False, (
                "expected exactly two quick-action--on/off cells inside .frame-strip, got %d"
                % on_off_count)
        if rendered.count('class="stat-tile ') != 3:
            return False, "expected exactly three stat-tile elements, got %d" % (
                rendered.count('class="stat-tile '),)
        for label in (home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL,
                      home_page.DATA_ROW_LABEL):
            if label not in rendered:
                return False, "expected the %r tile label" % (label,)
        if rendered.count(home_page.FRAME_STATE_TEXT["ok"]) != 1:
            return False, (
                "expected the Frame state sentence to appear exactly once — the "
                "20-RESEARCH.md Pitfall 3 duplicated-verdict regression test")
        return True, ""
    check(
        "a rendered Home page carries no status-card__rows/home-hero markup, quick-action markup "
        "only inside .frame-strip (exactly two cells) and nowhere else, exactly three stat-tile "
        "elements labelled Frame/Battery/Flight data, and the Frame verdict sentence exactly once "
        "(D-04/D-05)",
        _home_page_full_render_has_quick_action_only_inside_the_strip_and_three_tiles)

    def _home_status_card_headline_next_update_or_expected_since():
        # 21-04-PLAN.md Task 3 (D-01/D-04): retargeted at
        # layout.frame_strip_html() — home_page._status_card_html() is
        # deleted; the headline computation it owned moved to the
        # strip helper unchanged (Task 1).
        import companion.wake as wake
        base_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
        }

        def _strip_html(ctx):
            next_wake_iso = wake.next_wake_at_iso(
                ctx.get("last_checkin_ts"), ctx.get("device_config"))
            return layout.frame_strip_html(
                ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)

        future_ctx = dict(
            base_ctx, last_checkin_ts="2026-08-27T11:55:00+00:00", now="2026-08-27T12:00:00+00:00")
        rendered_future = _strip_html(future_ctx)
        # 11:55 UTC + 15 minutes = 12:10 UTC = 14:10 Europe/Paris (CEST,
        # UTC+2, in effect in late August) — still AFTER the 12:00 UTC
        # "now", so this is the not-yet-due branch.
        # 22-04-PLAN.md Task 2 (C5): the clock value is now its own
        # <span class="time-value time-value--primary"> element rather
        # than baked into the sentence's plain text, so "Next update ≈
        # 14:10" is no longer one contiguous substring — checked as two
        # pieces instead.
        if "Next update ≈" not in rendered_future or "14:10" not in rendered_future:
            return False, "expected the future next-update headline"
        if "status-card__headline--warn" in rendered_future:
            return False, "expected no warn modifier for a future next-update"

        past_ctx = dict(
            base_ctx, last_checkin_ts="2026-08-27T11:00:00+00:00", now="2026-08-27T12:00:00+00:00")
        rendered_past = _strip_html(past_ctx)
        # 11:00 UTC + 15 minutes = 11:15 UTC, already BEFORE the 12:00 UTC
        # "now" — the overdue, warn-treatment branch.
        if "Expected since" not in rendered_past:
            return False, "expected the overdue headline wording"
        if "status-card__headline--warn" not in rendered_past:
            return False, "expected the warn modifier for an overdue next-update"

        missing_checkin = dict(base_ctx, last_checkin_ts=None, now="2026-08-27T12:00:00+00:00")
        if "status-card__headline" in _strip_html(missing_checkin):
            return False, "expected no headline at all when there is no check-in yet"
        missing_interval = dict(
            base_ctx, device_config={}, last_checkin_ts="2026-08-27T11:55:00+00:00",
            now="2026-08-27T12:00:00+00:00")
        if "status-card__headline" in _strip_html(missing_interval):
            return False, "expected no headline at all when the wake interval is unknown"
        return True, ""
    check(
        "the Frame strip's headline reads 'Next update ≈ HH:MM' for a future next-update, "
        "'Expected since HH:MM' in the warn treatment for a past one, and renders no headline "
        "at all when either the check-in or the wake interval is unknown (D-01, moved from the "
        "deleted _status_card_html())",
        _home_status_card_headline_next_update_or_expected_since)

    def _home_status_card_always_shows_health_link():
        """D-17 (21-01-PLAN.md Task 2): the display-mode gate that used
        to hide this link is deleted — replaces a deleted check that
        tested that now-removed mechanism. 21-04-PLAN.md Task 3:
        retargeted at _status_tiles_html(), the deleted
        _status_card_html()'s own replacement.
        """
        from companion.pages import home_page
        ctx = {
            "health_state": {}, "device_config": {},
            "state_dir": "/tmp/skypane-no-such-state-dir", "now": "2026-08-27T12:00:00+00:00",
        }
        rendered = home_page._status_tiles_html(ctx)
        if home_page.HEALTH_LINK_TEXT not in rendered:
            return False, "expected the Health link to always render (D-17)"
        return True, ""
    check(
        "a default Home render always carries the status tiles section's 'See details on "
        "Health' link (D-17)",
        _home_status_card_always_shows_health_link)

    def _home_page_render_degrades_with_nothing():
        from companion.pages import home_page
        rendered = home_page.render({})
        for needle in (home_page.NO_FLIGHTS_HEADING, home_page.NO_PANEL_HEADING,
                       home_page.NO_READING_TEXT):
            if needle not in rendered:
                return False, "expected %r for an empty ctx" % needle
        if (battery.battery_percent(battery.BATTERY_FULL_MV) != 100
                or battery.battery_percent(4200) != 100
                or battery.battery_percent(battery.BATTERY_EMPTY_MV) != 0
                or battery.battery_percent(2900) != 0):
            return False, (
                "expected the percentage estimate to clamp at BATTERY_FULL_MV/4200 -> 100 and "
                "BATTERY_EMPTY_MV/2900 -> 0 (SEED-006 curve endpoints)")
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

    # --- 24-06-PLAN.md Task 1 (CFG-42): the time domain -----------------
    #
    # THE ONE THING THESE FOUR CHECKS ARE FOR. Every other drawing in
    # this phase maps an INDEX to an x position, and an index scale is
    # indistinguishable from a time scale on any series that arrived on
    # a perfectly even cadence — which is exactly what a seeded fixture
    # tends to be. So the checks below are written around the case the
    # two scales DISAGREE about: a gap. Under an index scale a six-hour
    # outage is one step, the same width as the fifteen minutes either
    # side of it; under a time scale it is a quarter of the band with
    # nothing in it. The mutation recorded in the summary substitutes
    # draw.percent_x() for draw.percent_time() and _day_band_time_scale_
    # places_by_when_not_by_index() is the check that goes red.

    # An arbitrary, fixed epoch second standing in for a Paris midnight.
    # The scale is pure arithmetic on two numbers in the same unit, so
    # nothing here needs a real timezone — which is the point of the
    # helper taking numbers rather than datetimes (companion/draw.py may
    # not import the server package, where the one Paris-day conversion
    # lives).
    _BAND_DAY_START = 1756000000

    def _band_hour(n):
        return _BAND_DAY_START + int(n * 3600)

    def _band_shapes(markup, class_name):
        """Every <rect> in `markup` carrying exactly `class_name`.

        The closing quote in the pattern is load-bearing: `drawing-band`
        is a strict prefix of both `drawing-band-span` and
        `drawing-band-mark`, so a `'class="drawing-band"' in element`
        test would report all three as the frame. This file has been bitten
        by that collision before (companion/test_companion_app.py:4134's
        own `(?<![-\\w])fill="none"` records the mirror case).
        """
        return re.findall(
            r'<rect class="%s"[^>]*/>' % re.escape(class_name), markup)

    def _band_attr(element, name):
        found = re.search(r'\s%s="([^"]*)"' % re.escape(name), element)
        return found.group(1) if found else None

    def _band_percent(element, name):
        raw = _band_attr(element, name)
        if raw is None or not raw.endswith("%"):
            return None
        return float(raw[:-1])

    def _day_band_time_scale_places_by_when_not_by_index():
        day = draw.SECONDS_PER_DAY
        # Midnight, midday, and the day's own final instant.
        for offset, expected in ((0, 0.0), (day / 2.0, 50.0), (day, 100.0)):
            got = draw.percent_time(_BAND_DAY_START + offset, _BAND_DAY_START)
            if got is None or abs(got - expected) > 1e-9:
                return False, (
                    "expected %+.1fs into the day at %.1f%%, got %r — the three positions a "
                    "reader checks a time axis against first" % (offset, expected, got))
        # Outside the day is REJECTED, never positioned. A clamped
        # instant would put yesterday's check-in at this band's midnight
        # and make today's drawing claim a check-in that never happened
        # (T-24-06-A).
        for outside in (_BAND_DAY_START - 1, _BAND_DAY_START + day + 1):
            if draw.percent_time(outside, _BAND_DAY_START) is not None:
                return False, (
                    "expected an instant outside the day to be rejected, got %r for %r — "
                    "clamping it would invent a check-in at an edge of the band"
                    % (draw.percent_time(outside, _BAND_DAY_START), outside))
        # Totality, because these numbers arrive from stored text.
        for hostile in (None, True, float("nan"), float("inf"), "12:00", [], {}):
            if draw.percent_time(hostile, _BAND_DAY_START) is not None:
                return False, "expected %r as an instant to be rejected" % (hostile,)
            if draw.percent_time(_BAND_DAY_START, hostile) is not None:
                return False, "expected %r as a day start to be rejected" % (hostile,)
        if draw.percent_time(_BAND_DAY_START, _BAND_DAY_START, 0) is not None:
            return False, "expected a zero-length day to be rejected rather than divided by"

        # A Europe/Paris day is 23 or 25 hours twice a year, so the
        # day's length is a parameter and an hour is a share of THAT
        # day, not of a hardcoded 86400.
        short = draw.percent_time(_BAND_DAY_START + 3600, _BAND_DAY_START, 23 * 3600)
        if short is None or abs(short - 100.0 / 23) > 1e-9:
            return False, (
                "on a 23-hour DST day an hour should be %.4f%% of the band, got %r"
                % (100.0 / 23, short))

        # THE PROPERTY AN INDEX SCALE DOES NOT HAVE: the distance between
        # two instants an hour apart is the same 1/24 of the band however
        # many other instants are on it. Measured off the drawn band, not
        # off the helper, because the band is what a reader sees.
        hour_percent = 100.0 / 24
        seen = []
        for fillers in ([], [_band_hour(h) for h in (0, 2, 4, 6, 20, 22)]):
            instants = fillers + [_band_hour(8), _band_hour(9)]
            markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
            if collapsed:
                return False, (
                    "expected no collapsing in a %d-instant series spaced two hours apart, "
                    "got %d collapsed" % (len(instants), collapsed))
            marks = [_band_percent(el, "x") for el in _band_shapes(markup, "drawing-band-mark")]
            if len(marks) != len(instants):
                return False, (
                    "expected one mark per instant (%d), got %d" % (len(instants), len(marks)))
            eight = min(marks, key=lambda p: abs(p - 8 * hour_percent))
            nine = min(marks, key=lambda p: abs(p - 9 * hour_percent))
            seen.append((len(instants), eight, nine))
            if abs(eight - 8 * hour_percent) > 0.02:
                return False, (
                    "with %d instants on the band, the 08:00 check-in is drawn at %.2f%% "
                    "instead of %.2f%% — that is an INDEX position, not a time position "
                    "(under draw.percent_x() it would sit at %.2f%%)"
                    % (len(instants), eight, 8 * hour_percent,
                       draw.percent_x(sorted(instants).index(_band_hour(8)), len(instants))))
            if abs((nine - eight) - hour_percent) > 0.02:
                return False, (
                    "with %d instants on the band, an hour measures %.2f%% of it instead of "
                    "%.2f%% — an index scale distributes points evenly whenever they happened, "
                    "so a six-hour outage would draw as one ordinary step"
                    % (len(instants), nine - eight, hour_percent))
        if abs(seen[0][1] - seen[1][1]) > 0.02 or abs(seen[0][2] - seen[1][2]) > 0.02:
            return False, (
                "the same two instants landed at different positions on a 2-instant band %r "
                "and an 8-instant band %r — a time scale places an instant by WHEN it "
                "happened and nothing else" % (seen[0][1:], seen[1][1:]))
        return True, ""
    check(
        "draw.percent_time() is a TIME scale and not the index scale beside it: midnight/"
        "midday/the day's final instant land at 0/50/100%, an hour is 1/24 of the band however "
        "many other instants are on it (so an outage draws as an outage), a DST day's own "
        "length is a parameter rather than a hardcoded 86400, and an instant outside the day is "
        "REJECTED rather than clamped onto an edge where it would invent a check-in "
        "(CFG-42, T-24-06-A, 24-06-PLAN.md Task 1)",
        _day_band_time_scale_places_by_when_not_by_index)

    def _day_band_night_window_shades_the_night_as_two_spans():
        day = draw.SECONDS_PER_DAY
        hour_percent = 100.0 / 24

        # 22:00-07:00 — a NIGHT window, which is what quiet hours
        # normally is, not an edge case.
        markup, _ = draw.day_band(
            _BAND_DAY_START, day, [], window=(_band_hour(22), _band_hour(7)))
        spans = _band_shapes(markup, "drawing-band-span")
        if len(spans) != 2:
            return False, (
                "expected a 22:00-07:00 window to shade TWO spans on a one-day band, got %d — "
                "one span from 22:00 back to 07:00 has a negative width, and the obvious "
                "repair (swap them) shades the whole DAY and leaves the night clear, which "
                "looks entirely plausible" % (len(spans),))
        widths = [_band_percent(el, "width") for el in spans]
        starts = [_band_percent(el, "x") for el in spans]
        if None in widths or None in starts:
            return False, "expected every span to carry percentage x/width, got %r" % (spans,)
        if abs(sum(widths) - 9 * hour_percent) > 0.02:
            return False, (
                "expected the two spans to cover nine hours (%.2f%%), got %.2f%% — %r"
                % (9 * hour_percent, sum(widths), list(zip(starts, widths))))
        if abs(min(starts)) > 1e-9:
            return False, (
                "expected the leading span to start at the band's own 00:00, got %r" % (starts,))
        ends = [s + w for s, w in zip(starts, widths)]
        if abs(max(ends) - 100.0) > 0.02:
            return False, (
                "expected the trailing span to reach the band's own 24:00, got %r" % (ends,))
        # And the middle of the day is NOT shaded: the failure this
        # check exists for is a band that shades 07:00-22:00.
        for start, width in zip(starts, widths):
            if start < 12 * hour_percent < start + width:
                return False, (
                    "midday falls inside a shaded span (%.2f%%..%.2f%%) — the night window has "
                    "been rendered inverted" % (start, start + width))

        # A daytime window is ONE span, so "always two" is not the fix.
        markup, _ = draw.day_band(
            _BAND_DAY_START, day, [], window=(_band_hour(9), _band_hour(17)))
        spans = _band_shapes(markup, "drawing-band-span")
        if len(spans) != 1:
            return False, "expected a 09:00-17:00 window to shade exactly one span, got %d" % (
                len(spans),)
        if abs(_band_percent(spans[0], "x") - 9 * hour_percent) > 0.02:
            return False, "expected the span to start at 09:00, got %r" % (spans[0],)
        if abs(_band_percent(spans[0], "width") - 8 * hour_percent) > 0.02:
            return False, "expected the span to be eight hours wide, got %r" % (spans[0],)

        # No window, a zero-width window and a window outside the day
        # all shade nothing. A zero-width window is never ACTIVE
        # (server/device_config.py's seconds_until_quiet_hours_end()
        # says so in as many words), so a hairline of shade would claim
        # a window the device does not honour.
        for label, window in (
                ("absent", None),
                ("zero-width", (_band_hour(9), _band_hour(9))),
                ("outside the day", (_BAND_DAY_START - 7200, _band_hour(7))),
                ("malformed", ("23:00", "07:00")),
                ("not a pair", 3)):
            markup, _ = draw.day_band(_BAND_DAY_START, day, [], window=window)
            spans = _band_shapes(markup, "drawing-band-span")
            if spans:
                return False, "expected a %s window to shade nothing, got %r" % (label, spans)
            if len(_band_shapes(markup, "drawing-band")) != 1:
                return False, "expected the band's own frame to survive a %s window" % (label,)
        return True, ""
    check(
        "the day band renders a wrapping night window (22:00-07:00) as TWO shaded spans "
        "covering nine hours, one flush to 00:00 and one flush to 24:00 with midday left "
        "clear — never one inverted span that would shade the middle of the day — while a "
        "daytime window stays one span and an absent/zero-width/out-of-day/malformed window "
        "shades nothing at all (CFG-42, 24-06-PLAN.md Task 1)",
        _day_band_night_window_shades_the_night_as_two_spans)

    def _day_band_collapses_crowded_marks_and_reports_exactly_how_many():
        day = draw.SECONDS_PER_DAY
        spacing = draw.DAY_BAND_MIN_MARK_SPACING_PERCENT
        ceiling = int(100.0 / spacing) + 1

        # A 30-minute cadence is 48 marks in the band's ~330px at the
        # 360px floor — about 7px apart, which is drawable. Nothing is
        # collapsed and the caller may caption the exact number.
        sparse = [_BAND_DAY_START + 1800 * i for i in range(48)]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, sparse)
        marks = _band_shapes(markup, "drawing-band-mark")
        if len(marks) != 48 or collapsed != 0:
            return False, (
                "expected 48 marks and 0 collapsed at a 30-minute cadence, got %d and %d"
                % (len(marks), collapsed))

        # A 60-second cadence is 1440 marks in the same 330px. Drawing
        # them all would let the reader believe the band shows 1440
        # things; the emitter collapses and SAYS how many.
        for cadence, total in ((60, 1440), (1, 86400)):
            instants = [_BAND_DAY_START + cadence * i for i in range(total)]
            markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
            marks = _band_shapes(markup, "drawing-band-mark")
            if len(marks) + collapsed != total:
                return False, (
                    "at a %ds cadence %d marks + %d collapsed != the %d instants supplied — "
                    "the number the caption is written from has to be exact"
                    % (cadence, len(marks), collapsed, total))
            if len(marks) > ceiling:
                return False, (
                    "at a %ds cadence the band drew %d marks, over the %d its own minimum "
                    "spacing allows — T-24-06-C is that the element count is bounded by the "
                    "band's WIDTH, never by the row count" % (cadence, len(marks), ceiling))
            positions = [_band_percent(el, "x") for el in marks]
            if positions != sorted(positions):
                return False, "expected the kept marks in chronological order, got %r" % (
                    positions[:8],)
            tight = [(a, b) for a, b in zip(positions, positions[1:])
                     if b - a < spacing - 0.011]
            if tight:
                return False, (
                    "at a %ds cadence two kept marks sit %.2f%% apart, under the %.2f%% "
                    "minimum — they would paint as one smear and the band would show fewer "
                    "things than it appears to" % (cadence, tight[0][1] - tight[0][0], spacing))
            # THE LOWER BOUND, and the half of this check the three
            # assertions above cannot see. They are all CEILINGS — at
            # most `ceiling` marks, none closer than the minimum — and
            # every one of them is satisfied perfectly by a band that
            # draws ONE mark at 00:00 and nothing else. That is not a
            # hypothetical: it is what this emitter does if its forward
            # pass compares each position against its immediate
            # PREDECESSOR rather than against the last KEPT mark, since
            # at a sub-minimum cadence every consecutive gap is under
            # the minimum and so nothing after the first is ever kept.
            # A day of 1 440 check-ins would then draw as one check-in
            # at midnight and an empty day after it — the band saying
            # the device died at 00:00 — with `collapsed` dutifully
            # reporting 1 439 and every ceiling above still green. The
            # mutation is recorded in 24-06-SUMMARY.md; these two
            # assertions are what it now fails.
            #
            # Both are consequences of the greedy rule rather than
            # chosen thresholds: a candidate lying a full
            # minimum-spacing past the last kept mark is kept BY
            # DEFINITION, so neither an interior gap nor the unmarked
            # tail at the band's end can reach the minimum plus one
            # cadence step. The 0.011 is the same allowance the `tight`
            # assertion above carries and is not slack in the rule: this
            # check reads POSITIONS OFF THE DRAWING, and an x attribute
            # carries two decimals, so a gap between two rounded
            # endpoints can differ from the true one by up to 0.01.
            step_percent = cadence / float(day) * 100
            last_instant = (instants[-1] - _BAND_DAY_START) / float(day) * 100
            if last_instant - positions[-1] >= spacing + 0.011:
                return False, (
                    "at a %ds cadence the kept marks stop at %.2f%% while the instants run to "
                    "%.2f%% — a tail of %.2f%% carrying %d check-ins drew nothing, though the "
                    "greedy rule keeps anything a full %.2f%% past the last kept mark. The band "
                    "would say the device stopped checking in"
                    % (cadence, positions[-1], last_instant, last_instant - positions[-1],
                       int((last_instant - positions[-1]) / step_percent), spacing))
            slack = [(a, b) for a, b in zip(positions, positions[1:])
                     if b - a > spacing + step_percent + 0.011]
            if slack:
                return False, (
                    "at a %ds cadence two kept marks sit %.2f%% apart, over the %.2f%% the "
                    "greedy rule allows — instants that had room for a mark of their own were "
                    "dropped, so the band shows a gap where the device was checking in "
                    "normally" % (cadence, slack[0][1] - slack[0][0], spacing + step_percent))

        # An instant the band cannot place counts as not-individually-
        # visible too, so a caller captioning from this number can never
        # name a total the drawing does not reach.
        mixed = [_BAND_DAY_START, _BAND_DAY_START - 60, "not a number", None,
                 _BAND_DAY_START + day // 2]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, mixed)
        marks = _band_shapes(markup, "drawing-band-mark")
        if len(marks) != 2 or collapsed != 3:
            return False, (
                "expected 2 marks and 3 unplaceable instants reported, got %d and %d"
                % (len(marks), collapsed))
        # Every mark is centred on its instant rather than hung to the
        # right of it: a 23:59 mark whose LEFT edge were the instant
        # would sit entirely outside the canvas. Asserted on the band
        # just drawn, which has two marks — asserting it on an empty
        # band is a loop that runs zero times and proves nothing.
        offset = -draw.DAY_BAND_MARK_WIDTH_PX / 2.0
        for element in marks:
            if _band_attr(element, "transform") != "translate(%.2f 0)" % offset:
                return False, "expected every mark centred on its instant, got %r" % (element,)

        markup, collapsed = draw.day_band(_BAND_DAY_START, day, 17)
        if collapsed != 0 or _band_shapes(markup, "drawing-band-mark"):
            return False, "expected a non-iterable series to draw no marks and report 0"
        return True, ""
    check(
        "the day band collapses marks closer than its own stated minimum spacing and returns "
        "EXACTLY how many it hid — 48 marks at a 30-minute cadence with nothing collapsed, a "
        "60-second and a 1-second cadence both bounded by the band's width rather than the row "
        "count (T-24-06-C), no two kept marks under the minimum apart, and an unplaceable "
        "instant counted too so a caption built from the number can never claim a total the "
        "drawing does not reach (T-24-06-B, 24-06-PLAN.md Task 1)",
        _day_band_collapses_crowded_marks_and_reports_exactly_how_many)

    def _day_band_emits_only_registered_classes_and_no_colour():
        markup, _ = draw.day_band(
            _BAND_DAY_START, draw.SECONDS_PER_DAY,
            [_band_hour(h) for h in (1, 5, 9, 13, 17, 21)],
            window=(_band_hour(23), _band_hour(7)), label="the day")
        for constant in (draw.DRAWING_BAND_CLASS, draw.DRAWING_BAND_SPAN_CLASS,
                         draw.DRAWING_BAND_MARK_CLASS):
            if constant not in draw.DRAWING_CLASSES:
                return False, (
                    "the band's class %r is not in draw.DRAWING_CLASSES, so the guard that "
                    "every emitted class resolves to a real selector cannot see it — a class "
                    "that exists in Python and nowhere in CSS paints nothing at all"
                    % (constant,))
        for class_name in re.findall(r'class="([^"]*)"', markup):
            for token in class_name.split():
                if token not in draw.DRAWING_CLASSES:
                    return False, (
                        "the band emitted class %r, which is not one of draw.py's own named "
                        "constants" % (token,))
        for forbidden in ("url(", "#", "rgb(", "style=", "<linearGradient"):
            if forbidden in markup:
                return False, (
                    "the band's markup carries %r — a colour decided in Python is correct in "
                    "one theme only, and an external reference is banned outright"
                    % (forbidden,))
        if 'role="group"' not in markup or 'aria-label="the day"' not in markup:
            return False, (
                "expected a labelled band: it is the only statement of its data, so it is not "
                "aria-hidden the way the ring beside its own printed percentage is")
        unlabelled, _ = draw.day_band(_BAND_DAY_START, draw.SECONDS_PER_DAY, [])
        if 'aria-hidden="true"' not in unlabelled:
            return False, "expected an unlabelled band to be hidden rather than an unnamed group"
        return True, ""
    check(
        "every class the day band emits is one of companion/draw.py's own named constants and "
        "is registered in DRAWING_CLASSES (so the stylesheet-resolution guard can see it), the "
        "markup carries no colour literal, no url() reference and no inline style, and a band "
        "supplied with a label announces itself as a named group rather than being hidden "
        "(CFG-39/CFG-42, 24-06-PLAN.md Task 1)",
        _day_band_emits_only_registered_classes_and_no_colour)

    # --- 24-06-PLAN.md Task 2 (CFG-42): the day band on Home -------------
    #
    # The band's three risks, one check each: that it shows the wrong DAY
    # (the Paris/UTC boundary), that it shows the wrong WINDOW (quiet
    # hours), and that it disappears rather than degrades (an empty day,
    # an absent database). The "no check-ins" case is a distinct STATE and
    # not an error: an absent section is indistinguishable from an unbuilt
    # feature, and this page already draws that distinction elsewhere (the
    # battery tile's "No reading yet" verdict rather than a zero).

    def _home_day_band_section(rendered):
        """The day band's <section> only, or None.

        Sliced out rather than searched for in the whole page because two
        of the assertions below are about what the caption does NOT say,
        and "quiet hours" appears elsewhere on this page in the frame
        strip's own switch. A page-wide `"quiet" not in rendered` would be
        green only on a page that had lost the strip.
        """
        opened = re.search(r'<section class="[^"]*\bday-band\b[^"]*"', rendered)
        if opened is None:
            return None
        end = rendered.index("</section>", opened.start())
        return rendered[opened.start():end + len("</section>")]

    def _home_band_marks(section):
        return re.findall(r'<rect class="drawing-band-mark"[^>]*/>', section)

    def _home_band_spans(section):
        return re.findall(r'<rect class="drawing-band-span"[^>]*/>', section)

    def _home_band_ctx(tmp, now, checkins, config=None):
        from server import history_db as _hdb
        with _hdb.open_db(tmp) as conn:
            for ts in checkins:
                _hdb.record_device_health(conn, ts, battery_mv=3750)
        return {
            "state_dir": tmp, "now": now,
            "last_checkin_ts": checkins[-1] if checkins else None,
            "device_config": config or {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {"device_state": "ok", "pipeline_state": "ok",
                             "battery_state": "ok", "device_detail_html": "",
                             "pipeline_html": ""},
            "simple_mode": False,
        }

    def _home_day_band_renders_the_day_and_says_what_it_shows():
        from companion.pages import home_page
        # Paris 14:00 on 2026-08-27 (CEST, UTC+2), so the band's day runs
        # 2026-08-26T22:00Z .. 2026-08-27T22:00Z.
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("band-day")
        try:
            # 08:00, 12:00 and 13:00 Paris — two of them an hour apart, so
            # the time scale's own property is visible on the real page and
            # not only in the unit check above.
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
                "2026-08-27T11:00:00+00:00",
            ])
            rendered = home_page.render(ctx)
            section = _home_day_band_section(rendered)
            if section is None:
                return False, "expected a day-band section on Home, got none"
            marks = _home_band_marks(section)
            if len(marks) != 3:
                return False, "expected one mark per check-in (3), got %d" % (len(marks),)
            xs = sorted(float(re.search(r'x="([\d.]+)%"', el).group(1)) for el in marks)
            hour = 100.0 / 24
            for got, want_hour in zip(xs, (8, 12, 13)):
                if abs(got - want_hour * hour) > 0.02:
                    return False, (
                        "expected the %02d:00 Paris check-in at %.2f%%, got %.2f%% — the band's "
                        "marks are placed by the PARIS clock, which is what every other date on "
                        "this page uses" % (want_hour, want_hour * hour, got))
            # The caption names the day it is showing. A band captioned
            # only "today" cannot be checked against the row beneath it.
            if "2026-08-27" not in section:
                return False, "expected the caption to name the Paris day it draws, got %r" % (
                    section,)
            if "3" not in re.sub(r"<[^>]*>", " ", section):
                return False, "expected the caption to state the check-in count as text"

            # THE EMPTY DAY IS A STATE, NOT AN ABSENCE.
            empty = _mkstate("band-empty")
            try:
                empty_ctx = _home_band_ctx(empty, now, [])
                # A check-in on a DIFFERENT day, so the table is not empty
                # and the emptiness is the band's bucketing rather than an
                # unreadable database.
                from server import history_db as _hdb
                with _hdb.open_db(empty) as conn:
                    _hdb.record_device_health(conn, "2026-08-20T10:00:00+00:00", battery_mv=3700)
                rendered_empty = home_page.render(empty_ctx)
                empty_section = _home_day_band_section(rendered_empty)
                if empty_section is None:
                    return False, (
                        "expected the band section to survive a day with no check-ins — an "
                        "absent section reads as an unbuilt feature, an empty band reads as "
                        "no activity, and those are different statements")
                if _home_band_marks(empty_section):
                    return False, "expected no marks on an empty day, got %r" % (
                        _home_band_marks(empty_section),)
                if 'class="drawing-band"' not in empty_section:
                    return False, "expected the band's own frame to render on an empty day"
                if "2026-08-27" not in empty_section:
                    return False, "expected the empty band's caption to name the day too"
            finally:
                shutil.rmtree(empty, ignore_errors=True)

            # THE COLLAPSE, CAPTIONED (T-24-06-B). The band above drew
            # three well-separated marks and must NOT carry the merge
            # sentence — a caption that always admitted a collapse would
            # be as untrue as one that never did. A day at a one-minute
            # cadence must carry it, because at that density the band
            # genuinely cannot show each check-in separately and a reader
            # counting marks would otherwise conclude it lost some.
            if home_page.DAY_BAND_COLLAPSED_TEXT in section:
                return False, (
                    "the band collapsed nothing (3 marks for 3 check-ins) yet its caption said "
                    "marks were merged — a caption that always admits a collapse tells the "
                    "reader nothing and is untrue on every sparse day")
            dense = _mkstate("band-dense")
            try:
                from server import history_db as _hdb
                minutes = ["2026-08-27T%02d:%02d:00+00:00" % (6 + i // 60, i % 60)
                           for i in range(300)]
                dense_ctx = _home_band_ctx(dense, now, minutes)
                dense_section = _home_day_band_section(home_page.render(dense_ctx))
                if dense_section is None:
                    return False, "expected a band on a dense day"
                dense_marks = _home_band_marks(dense_section)
                if len(dense_marks) >= len(minutes):
                    return False, (
                        "expected a one-minute cadence to collapse (300 check-ins cannot be 300 "
                        "distinguishable marks in ~330px), got %d marks" % (len(dense_marks),))
                if home_page.DAY_BAND_COLLAPSED_TEXT not in dense_section:
                    return False, (
                        "the band drew %d marks for %d check-ins and its caption did not say "
                        "they were merged — the drawing dropping marks silently and the caption "
                        "printing a total are the two halves of one lie (T-24-06-B)"
                        % (len(dense_marks), len(minutes)))
                dense_text = re.sub(r"<[^>]*>", " ", dense_section)
                if str(len(minutes)) not in dense_text:
                    return False, (
                        "expected the true total still printed as TEXT beside the merge "
                        "sentence — the count is honest, only the COUNTING of marks is not")
            finally:
                shutil.rmtree(dense, ignore_errors=True)

            # NO DATABASE AT ALL: no band, no raise, a page that still
            # renders (T-24-06-D).
            #
            # The unreadable database is made unreadable by putting a
            # DIRECTORY where history.db belongs, not by chmod: this
            # harness runs as root in its container, where a 0o500 state
            # dir is not read-only at all (the same reason the four WR-11
            # checks in companion/test_companion_app.py fail here and
            # pass in CI). sqlite cannot open a directory whoever you
            # are, so this check measures the same degradation in both
            # environments.
            absent = _mkstate("band-nodb")
            try:
                absent_ctx = _home_band_ctx(absent, now, [])
                for name in os.listdir(absent):
                    path = os.path.join(absent, name)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                os.mkdir(os.path.join(absent, "history.db"))
                rendered_absent = home_page.render(absent_ctx)
                if '<h1 class="page-title">' not in rendered_absent:
                    return False, "expected Home to render with history.db absent"
                if _home_day_band_section(rendered_absent) is not None:
                    return False, (
                        "expected NO band with history.db unreadable — an empty band there "
                        "would claim the device made no check-ins when nothing was read")
            finally:
                shutil.rmtree(absent, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band draws one mark per check-in at its PARIS clock position, captions the "
        "Paris day it shows and states the count as text; a day with no check-ins still renders "
        "the band and its frame with a caption naming the day (an absent section would read as "
        "an unbuilt feature, an empty band reads as no activity); and with history.db unreadable "
        "the page renders with no band at all rather than an empty one claiming no check-ins "
        "(CFG-42, T-24-06-D, 24-06-PLAN.md Task 2)",
        _home_day_band_renders_the_day_and_says_what_it_shows)

    def _home_day_band_shades_quiet_hours_only_when_configured():
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        checkins = ["2026-08-27T10:00:00+00:00"]
        hour = 100.0 / 24
        tmp = _mkstate("band-quiet")
        try:
            # The DEFAULT night window, and the case a naive span renders
            # inverted: 23:00-07:00 wraps midnight.
            ctx = _home_band_ctx(tmp, now, checkins, config={
                "wake_interval_s": 900, "display_enabled": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
            })
            section = _home_day_band_section(home_page.render(ctx))
            if section is None:
                return False, "expected a day-band section"
            spans = _home_band_spans(section)
            if len(spans) != 2:
                return False, (
                    "expected the default 23:00-07:00 quiet hours to shade TWO spans on a "
                    "one-day band, got %d — one span would shade the middle of the DAY and "
                    "leave the night clear" % (len(spans),))
            widths = [float(re.search(r'width="([\d.]+)%"', el).group(1)) for el in spans]
            if abs(sum(widths) - 8 * hour) > 0.05:
                return False, (
                    "expected the shaded spans to cover the window's eight hours (%.2f%%), got "
                    "%.2f%%" % (8 * hour, sum(widths)))
            text = re.sub(r"<[^>]*>", " ", section)
            if "23:00" not in text or "07:00" not in text:
                return False, (
                    "expected the caption to name the shaded window's own hours, got %r" % (text,))

            # DISABLED: nothing shaded, and the caption does not mention a
            # window the device is not honouring.
            off = _mkstate("band-quiet-off")
            try:
                off_ctx = _home_band_ctx(off, now, checkins, config={
                    "wake_interval_s": 900, "display_enabled": True,
                    "quiet_hours_enabled": False,
                    "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                    "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
                })
                off_section = _home_day_band_section(home_page.render(off_ctx))
                if off_section is None:
                    return False, "expected the band to render with quiet hours disabled"
                if _home_band_spans(off_section):
                    return False, (
                        "expected zero shaded spans with quiet hours disabled, got %r"
                        % (_home_band_spans(off_section),))
                off_text = re.sub(r"<[^>]*>", " ", off_section).lower()
                if "quiet" in off_text or "23:00" in off_text:
                    return False, (
                        "expected the band's caption to say nothing about quiet hours when they "
                        "are off — a legend for a span that is not drawn describes a band the "
                        "reader is not looking at. Got %r" % (off_text,))
                if not _home_band_marks(off_section):
                    return False, "expected the check-in marks to survive quiet hours being off"
            finally:
                shutil.rmtree(off, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band shades the CONFIGURED quiet-hours window — the default 23:00-07:00 "
        "wrapping night window as two spans covering its eight hours, named in the caption — and "
        "with quiet hours disabled shades nothing and says nothing about them, while still "
        "drawing the day's check-ins (CFG-42/D-03, 24-06-PLAN.md Task 2)",
        _home_day_band_shades_quiet_hours_only_when_configured)

    def _home_day_band_buckets_by_paris_day_and_costs_one_read():
        from companion.pages import home_page
        from server import history_db as _hdb
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("band-boundary")
        try:
            # THE BOUNDARY THIS BREAKS AT IF IT BREAKS. Paris is UTC+1/+2
            # and so never BEHIND UTC — 24-06-PLAN.md Task 2's own
            # acceptance criterion names "23:30 Paris on a date whose UTC
            # instant falls on the next day", which cannot occur for
            # Europe/Paris. The real case is its mirror, and it is the
            # same defect: 00:30 Paris is 22:30 UTC on the PREVIOUS day,
            # so a band bucketed by the UTC date drops it from today and
            # picks up tomorrow's 00:30 instead. Both directions below.
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-26T21:30:00+00:00",  # Paris 2026-08-26 23:30 — yesterday
                "2026-08-26T22:30:00+00:00",  # Paris 2026-08-27 00:30 — TODAY
                "2026-08-27T22:30:00+00:00",  # Paris 2026-08-28 00:30 — tomorrow
            ])
            section = _home_day_band_section(home_page.render(ctx))
            if section is None:
                return False, "expected a day-band section"
            marks = _home_band_marks(section)
            if len(marks) != 1:
                return False, (
                    "expected exactly ONE of the three check-ins on the 2026-08-27 Paris band, "
                    "got %d — under a UTC date bucket the 22:30Z check-in (Paris 00:30 today) "
                    "drops off and the 2026-08-27T22:30Z one (Paris 00:30 TOMORROW) appears "
                    "instead, which is the same count from the wrong rows" % (len(marks),))
            got = float(re.search(r'x="([\d.]+)%"', marks[0]).group(1))
            want = 0.5 * (100.0 / 24)  # 00:30 Paris
            if abs(got - want) > 0.02:
                return False, (
                    "expected the 00:30 Paris check-in at %.2f%%, got %.2f%%" % (want, got))

            # A 25-HOUR PARIS DAY. 2026-10-25 is the EU autumn transition,
            # so the band is 25 hours wide and midday sits at 52.00%, not
            # at the 54.17% a hardcoded 86400 would put it at.
            dst = _mkstate("band-dst")
            try:
                dst_ctx = _home_band_ctx(
                    dst, "2026-10-25T12:00:00+00:00", ["2026-10-25T11:00:00+00:00"])
                dst_section = _home_day_band_section(home_page.render(dst_ctx))
                dst_marks = _home_band_marks(dst_section or "")
                if len(dst_marks) != 1:
                    return False, "expected one mark on the DST band, got %d" % (len(dst_marks),)
                dst_got = float(re.search(r'x="([\d.]+)%"', dst_marks[0]).group(1))
                if abs(dst_got - 52.0) > 0.02:
                    return False, (
                        "on the 25-hour Paris day 2026-10-25 the 12:00 check-in belongs at "
                        "52.00%% of the band, got %.2f%% — a hardcoded 86400 puts it at 54.17%% "
                        "and leaves an hour of the band unreachable" % (dst_got,))
            finally:
                shutil.rmtree(dst, ignore_errors=True)

            # ONE READ, REUSED (D-20), MEASURED. render() made two
            # history.db reads before this plan; the band adds exactly
            # one, and a band that re-queried per section would show up
            # here as three or more.
            counted = _mkstate("band-reads")
            try:
                read_ctx = _home_band_ctx(counted, now, ["2026-08-27T10:00:00+00:00"])
                opened = []
                real_open = _hdb.open_db
                def _counting_open(state_dir):
                    opened.append(state_dir)
                    return real_open(state_dir)
                _hdb.open_db = _counting_open
                try:
                    rendered = home_page.render(read_ctx)
                finally:
                    _hdb.open_db = real_open
                if len(opened) != 3:
                    return False, (
                        "expected render() to make exactly 3 history.db reads — the 2 it made "
                        "before this plan (recent flights, latest battery) plus the band's one "
                        "— got %d. 'One read, reused' is measured here, not assumed"
                        % (len(opened),))
                # The frame verdict still appears exactly once on the page
                # (_status_tiles_html()'s own recorded property, which a
                # new section carrying a state word could quietly break).
                verdicts = [v for v in home_page.FRAME_STATE_TEXT.values()
                            if rendered.count(v)]
                for verdict in verdicts:
                    if rendered.count(verdict) != 1:
                        return False, (
                            "expected the frame verdict %r exactly once on Home, got %d"
                            % (verdict, rendered.count(verdict)))
                if len(verdicts) != 1:
                    return False, (
                        "expected exactly one frame verdict rendered on Home, got %r" % (
                            verdicts,))
            finally:
                shutil.rmtree(counted, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band buckets check-ins by the PARIS day — a 22:30Z check-in (Paris 00:30 "
        "today) is on the band and a 2026-08-27T22:30Z one (Paris 00:30 tomorrow) is not, the "
        "mirror of the boundary 24-06-PLAN.md Task 2 named since Paris is never behind UTC — "
        "and spans a real 25-hour Paris day so midday lands at 52.00% rather than the 54.17% a "
        "hardcoded 86400 would give; it costs render() exactly one history.db read more than "
        "the two it made before, measured, and the frame verdict still appears exactly once "
        "(CFG-42/D-20, 24-06-PLAN.md Task 2)",
        _home_day_band_buckets_by_paris_day_and_costs_one_read)

    # --- 24-08-PLAN.md Task 1 (CFG-44): D4's hero, assembled from calls -
    #
    # "The Home hero the others feed" is a STRUCTURAL claim with exactly
    # one failure mode: a hero that looks composed but carries its own
    # copies of the ring and the band, which then drift from the
    # originals the first time either is fixed. This codebase has already
    # paid for that once (companion/battery.py exists because
    # battery_percent() had been copied), so the checks here are written
    # against that failure rather than against the markup's shape.

    def _home_hero_inner(rendered):
        """The hero container's own inner markup, or None when the page
        renders no hero at all.

        A BALANCED SCAN, never `rendered.index("</div>")`: the hero holds
        sections that hold divs of their own, so the first closing tag
        after the opening one belongs to a descendant. A slicer that took
        it would return a fragment that happened to start with the strip
        and stop somewhere inside the tiles, and every "is inside the
        hero" assertion below would then be measuring a shorter string
        than its own message names — green for the wrong reason, which is
        the one way a containment check fails silently.
        """
        from companion.pages import home_page
        opened = re.search(
            r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered)
        if opened is None:
            return None
        depth = 0
        for token in re.finditer(r"<div\b|</div>", rendered[opened.start():]):
            depth += 1 if token.group(0) == "<div" else -1
            if depth == 0:
                return rendered[opened.end():opened.start() + token.start()]
        return None

    def _home_top_is_one_composition_holding_the_ring_and_the_band():
        import companion.draw as _draw
        import companion.i18n as _i18n
        import companion.prefs as _prefs
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-compose")
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ])
            ctx["gallery_entries"] = ["2026-08-27T11-50-00+00-00.png"]
            rendered = home_page.render(ctx)

            # ONE hero. Two containers would be the phase-20 collision
            # back in a new costume (22-07 had to rename a second thing
            # called "Frame" on this very page).
            opens = len(re.findall(
                r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered))
            if opens != 1:
                return False, (
                    "expected exactly one hero container on Home, got %d" % (opens,))
            inner = _home_hero_inner(rendered)
            if inner is None:
                return False, "expected the hero container to open and close"

            # Its three parts, each still rendered by the builder that
            # owns it. The strip is matched on the class the SHARED
            # helper emits, so a hero that inlined a second rendering of
            # it would have to reproduce that class to pass — and would
            # then fail the count below.
            for label, pattern in (
                    ("the shared Frame strip",
                     r'class="frame-strip stat-tile stat-tile--accent"'),
                    ("the three status tiles",
                     r'class="dashboard-grid home-status-grid"'),
                    ("the day band", r'<section class="[^"]*\bday-band\b')):
                if re.search(pattern, inner) is None:
                    return False, (
                        "expected %s inside the hero — a composition that does not contain "
                        "its parts is a wrapper, not a hero (looked for %r)"
                        % (label, pattern))
            if rendered.count('class="frame-strip stat-tile stat-tile--accent"') != 1:
                return False, (
                    "expected the shared Frame strip rendered exactly once — the hero wraps "
                    "the shared component, it never inlines a second rendering of it")

            # What the hero is NOT. The picture row is the page's own
            # second half and sits after it; a hero that swallowed it
            # would make every 360px stacking measurement below about
            # the whole page instead of the composition.
            for absent in ("home-picture-row", "preview-frame", "recent-flight"):
                if absent in inner:
                    return False, (
                        "expected %r outside the hero — the hero is Home's TOP, not its "
                        "whole body" % (absent,))
            if rendered.index('class="home-columns home-picture-row"') < rendered.index(
                    '<div class="%s"' % home_page.HERO_CLASS):
                return False, "expected the hero to precede the picture row"

            # EXACTLY ONE RING AND EXACTLY ONE BAND, both the hero's.
            # The needles are whole class ATTRIBUTES rather than bare
            # class names: the band frame's own name is a prefix of the
            # span's and the mark's, so a substring test would count
            # three things as the frame (the trap
            # companion/test_companion_app.py:4134 records from the
            # other direction).
            for label, needle in (
                    ("battery ring value arc",
                     'class="%s"' % _draw.DRAWING_RING_VALUE_CLASS),
                    ("day band frame", 'class="%s"' % _draw.DRAWING_BAND_CLASS)):
                if rendered.count(needle) != 1:
                    return False, (
                        "expected exactly one %s on Home, got %d"
                        % (label, rendered.count(needle)))
                if needle not in inner:
                    return False, (
                        "expected the %s INSIDE the hero — CFG-44's hero is the composition "
                        "the drawings feed, not a container beside them" % (label,))

            # NO GEOMETRY AND NO SECOND ESTIMATE IN THIS MODULE. The
            # boundary regex on the estimator is the point: a bare
            # `battery_percent(` is a local copy, while the qualified
            # call through companion/battery.py is the one home the
            # allow-list permits.
            source = inspect.getsource(home_page)
            for token in ("stroke-dasharray", "BATTERY_FULL_MV", "4200", "3300",
                          "BATTERY_DISCHARGE_CURVE", "4112", "2946"):
                if token in source:
                    return False, (
                        "companion/pages/home_page.py contains %r — geometry and battery "
                        "arithmetic belong to the shared modules, and a page that carries "
                        "either has started a second copy" % (token,))
            if re.search(r"(?<![-\w.])battery_percent\s*\(", source) is not None:
                return False, (
                    "companion/pages/home_page.py names battery_percent( with no module "
                    "qualifier — either a local definition or a bare `from companion.battery "
                    "import` — and both make the estimator read as this page's own. It has "
                    "exactly two allowed homes and this module is not one of them, so every "
                    "call site here says so")
            for call in ("draw.ring_gauge(", "draw.day_band("):
                if call not in source:
                    return False, (
                        "expected %r in home_page.py — the hero is assembled from CALLS into "
                        "the shared emitters" % (call,))

            # THE RECORDED FIXED BUG (20-RESEARCH.md Pitfall 3), re-asked
            # in BOTH languages because a hero is precisely the shape
            # that reintroduces it and French is a separate string table
            # that could disagree.
            for lang in ("en", "fr"):
                _prefs.set_request_prefs(lang=lang)
                try:
                    page = home_page.render(ctx)
                    seen = [_i18n.t(v) for v in home_page.FRAME_STATE_TEXT.values()
                            if page.count(_i18n.t(v))]
                    if len(seen) != 1:
                        return False, (
                            "in %s expected exactly one frame verdict on Home, got %r"
                            % (lang, seen))
                    if page.count(seen[0]) != 1:
                        return False, (
                            "in %s expected the frame verdict %r exactly once on Home, got "
                            "%d — the duplicated verdict 21-04 deleted a whole status-card "
                            "builder to remove" % (lang, seen[0], page.count(seen[0])))
                finally:
                    _prefs.set_request_prefs(lang="en")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's top is ONE composition: a single hero container holds the shared Frame strip "
        "(rendered once, unforked), the three status tiles carrying the battery ring, and the "
        "day band — the picture row stays outside it, the ring and the band each appear exactly "
        "once and both inside the hero, home_page.py carries no ring geometry and no second "
        "battery estimate (an unqualified battery_percent( is refused by a boundary regex), and "
        "the frame verdict still appears exactly once in BOTH languages (CFG-44, 24-08-PLAN.md "
        "Task 1)",
        _home_top_is_one_composition_holding_the_ring_and_the_band)

    # --- 24-08-PLAN.md Task 2 (CFG-44): "fed by", proven ---------------
    #
    # Two checks with two different jobs, named for what they prove so a
    # later tidy-up does not read them as duplicate coverage of the
    # hero's markup. The first is STRUCTURAL: every class the hero's two
    # drawings carry is one of companion/draw.py's OWN named constants,
    # read from that module at check time and never restated here — a
    # literal would keep passing against a forked copy that still used
    # the old string, which is precisely the failure being tested for.
    # The second is BEHAVIOURAL, and it is the one CFG-44 actually asks
    # for: change a shared emitter and watch BOTH the hero and the page
    # the emitter was borrowed from move with it.

    def _classes_inside_svg(markup, opening_class):
        """The set of class attributes emitted INSIDE the first <svg>
        whose own class begins with `opening_class`, or None when there
        is no such element.

        Non-greedy to the first closing tag, which is correct for both
        drawings this is asked about: neither nests an <svg>. A drawing
        that did would need a balanced scan, the same way the hero's own
        container does.
        """
        svg = re.search(
            r'<svg class="%s[^"]*"[^>]*>(.*?)</svg>' % re.escape(opening_class),
            markup, re.S)
        if svg is None:
            return None
        return set(re.findall(r'class="([^"]*)"', svg.group(1)))

    def _the_heros_ring_is_the_emitter_healths_ring_is():
        import textwrap
        import companion.draw as _draw
        from companion.pages import health_page, home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-vocab")
        health_tmp = _mkstate("hero-vocab-health")
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ], config={
                "wake_interval_s": 900, "display_enabled": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
            })
            rendered = home_page.render(ctx)
            hero = _home_hero_inner(rendered)
            if hero is None:
                return False, "expected a hero container on Home"
            with history_db.open_db(health_tmp) as conn:
                for minute, mv in ((50, 3600), (55, 3690)):
                    history_db.record_device_health(
                        conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
            health_rendered = health_page.render({"state_dir": health_tmp, "now": now})

            # ONE RING, TWO PAGES. The two rings' class vocabularies are
            # COMPUTED from the markup rather than listed here, so this
            # cannot drift into a hand-maintained copy of the emitter's
            # own list — which would be the same defect one level up.
            hero_ring = _classes_inside_svg(hero, _draw.DRAWING_FIGURE_CLASS)
            health_ring = _classes_inside_svg(health_rendered, _draw.DRAWING_FIGURE_CLASS)
            if not hero_ring:
                return False, "found no ring inside Home's hero"
            if not health_ring:
                return False, "found no ring on Health"
            if hero_ring != health_ring:
                return False, (
                    "the hero's ring and Health's carry different class vocabularies (%r "
                    "against %r) — one drawing at two sizes emits one vocabulary; two "
                    "vocabularies means two components"
                    % (sorted(hero_ring), sorted(health_ring)))

            # THE BAND, AND ITS FLOOR. "Every class is one of the shared
            # module's own" is satisfied by a band that drew nothing but
            # its frame, so the distinct-element floor is asserted
            # alongside it: the frame, the shaded quiet-hours span and
            # the check-in marks are three different shapes, and a band
            # that lost two of them would still pass the vocabulary half
            # on its own.
            hero_band = _classes_inside_svg(hero, _draw.DRAWING_CANVAS_CLASS)
            if not hero_band:
                return False, "found no day band inside Home's hero"
            if len(hero_band) < 3:
                return False, (
                    "the hero's band draws only %d kind(s) of shape (%r) — with a quiet-hours "
                    "window configured and two check-ins on the day it owes three: its own "
                    "frame, the shaded span and the marks" % (len(hero_band), sorted(hero_band)))

            # EVERY ONE OF THEM A NAMED CONSTANT OF THE SHARED MODULE.
            # A forked copy is free to emit any string it likes; this is
            # what refuses the ones draw.py does not own.
            for class_name in sorted(hero_ring | hero_band):
                for token in class_name.split():
                    if token not in _draw.DRAWING_CLASSES:
                        return False, (
                            "the hero emits the drawing class %r, which companion/draw.py does "
                            "not name — a class the shared module does not own came from "
                            "somewhere else" % (token,))

            # THE PAGE MODULE RESTATES NONE OF THEM, AND NEITHER DOES
            # THIS CHECK. That is the fork's own fingerprint: markup
            # emitted by hand has to write these strings down somewhere.
            #
            # A BARE SUBSTRING SCAN CANNOT ASK THIS, and finding that out
            # cost this check a draft: draw.DRAWING_GRID_CLASS is the
            # single word "drawing", which appears in home_page.py's
            # PROSE ("a drawing that implied calibration would out-claim
            # the number it sits beside") and in this check's own failure
            # messages. A scan that reads English as evidence is the
            # phase's own recorded trap — check your own prose does not
            # satisfy your own grep — so what is scanned is string
            # LITERALS only, docstrings excluded, and each one is asked
            # two precise questions instead of one loose one.
            def _restated_drawing_class(source):
                tree = ast.parse(source)
                docs = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Module, ast.ClassDef,
                                         ast.FunctionDef, ast.AsyncFunctionDef)):
                        if ast.get_docstring(node, clean=False) is not None:
                            docs.add(id(node.body[0].value))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Constant) or id(node) in docs:
                        continue
                    if not isinstance(node.value, str):
                        continue
                    # Question one: is the literal a class name outright
                    # (the `'<circle class="%s"' % "..."` shape)?
                    if node.value in _draw.DRAWING_CLASSES:
                        return node.value
                    # Question two: does it write one into a class
                    # attribute (the inlined-markup shape)?
                    for attribute in re.findall(r'class="([^"]*)"', node.value):
                        for token in attribute.split():
                            if token in _draw.DRAWING_CLASSES:
                                return token
                return None

            restated = _restated_drawing_class(inspect.getsource(home_page))
            if restated is not None:
                return False, (
                    "companion/pages/home_page.py writes the drawing class %r into a string "
                    "literal — the page calls the emitters, it does not restate their markup"
                    % (restated,))
            restated = _restated_drawing_class(textwrap.dedent(
                inspect.getsource(_the_heros_ring_is_the_emitter_healths_ring_is)
                + inspect.getsource(_classes_inside_svg)))
            if restated is not None:
                return False, (
                    "this check writes the drawing class %r into a literal instead of reading "
                    "it from companion/draw.py — rename the constant and a literal here goes "
                    "on passing against the fork" % (restated,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(health_tmp, ignore_errors=True)
    check(
        "the hero's battery ring is the same emitter Health's ring is — the two pages' rings "
        "carry one class vocabulary, computed from the markup rather than listed; the hero's "
        "day band draws three different shapes and not one; every class either of them emits is "
        "a constant companion/draw.py itself names; and neither companion/pages/home_page.py nor "
        "this check writes any of those strings down, because a literal goes on passing against "
        "a forked copy that still uses the old one (CFG-44, 24-08-PLAN.md Task 2)",
        _the_heros_ring_is_the_emitter_healths_ring_is)

    def _breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from():
        import companion.draw as _draw
        from companion.pages import health_page, home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-link")
        health_tmp = _mkstate("hero-link-health")
        # Not a member of DRAWING_CLASSES and not a substring of one, so
        # "the sentinel arrived" and "the original left" are two
        # independent readings rather than one.
        sentinel = "skypane-emitter-under-mutation"
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ])
            with history_db.open_db(health_tmp) as conn:
                for minute, mv in ((50, 3600), (55, 3690)):
                    history_db.record_device_health(
                        conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
            health_ctx = {"state_dir": health_tmp, "now": now}
            home_before = home_page.render(ctx)
            health_before = health_page.render(health_ctx)

            def _mutated(attr):
                """Both pages rendered with one of draw.py's class
                constants replaced, the constant restored afterwards
                whatever happens."""
                original = getattr(_draw, attr)
                setattr(_draw, attr, sentinel)
                try:
                    return original, home_page.render(ctx), health_page.render(health_ctx)
                finally:
                    setattr(_draw, attr, original)

            # THE RING: one definition, two pages. A hero built from its
            # own copy would still carry the ORIGINAL class here while
            # Health carried the sentinel — which is exactly the drift
            # CFG-44 is about, and is invisible to any check that only
            # looks at the markup as shipped.
            original, home_after, health_after = _mutated("DRAWING_RING_VALUE_CLASS")
            for label, before, after in (("the hero", home_before, home_after),
                                         ("Health", health_before, health_after)):
                if sentinel not in after:
                    return False, (
                        "a change inside the shared ring emitter did not reach %s — it draws "
                        "its own ring, not the shared one" % (label,))
                if 'class="%s"' % original in after:
                    return False, (
                        "%s still carries the ring's original class after the emitter was "
                        "changed — part of that drawing is a copy" % (label,))
                if after == before:
                    return False, "%s rendered identically under the mutation" % (label,)

            # THE MUTATION WAS TARGETED, not a global perturbation: the
            # band is Home's alone, so changing it must move the hero and
            # leave Health BYTE-IDENTICAL. Without this, "both pages
            # changed" above would be worth much less.
            original, home_after, health_after = _mutated("DRAWING_BAND_MARK_CLASS")
            if sentinel not in home_after:
                return False, (
                    "a change inside the shared band emitter did not reach the hero — its band "
                    "is a copy")
            if 'class="%s"' % original in home_after:
                return False, (
                    "the hero still carries the band mark's original class after the emitter "
                    "was changed — part of that drawing is a copy")
            if health_after != health_before:
                return False, (
                    "changing the band emitter also changed Health, which draws no band — the "
                    "mutation is not measuring what it names")

            # THE RESTORE IS PART OF THE CHECK. A mutation left behind
            # would make every later check in this file measure a
            # sabotaged module, and the failure would land somewhere
            # else entirely.
            if home_page.render(ctx) != home_before:
                return False, "Home did not return to its pre-mutation markup"
            if health_page.render(health_ctx) != health_before:
                return False, "Health did not return to its pre-mutation markup"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(health_tmp, ignore_errors=True)
    check(
        "breaking a shared emitter breaks the hero WITH the page it borrowed it from: one class "
        "constant inside companion/draw.py's ring emitter is replaced at check time and both "
        "Home's hero and Health's readout change, neither keeping the original string (a hero "
        "built from its own copy would); the band emitter's own mutation reaches the hero and "
        "leaves Health byte-identical, proving the mutation is targeted rather than a global "
        "perturbation; and both pages return to their pre-mutation markup (CFG-44, "
        "24-08-PLAN.md Task 2)",
        _breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from)

    # --- 19-12-PLAN.md Task 3 (D-13/S-02): the "Next wake ≈ HH:MM" figure --

    def _wake_next_wake_at_iso_contract():
        import companion.wake as wake
        from server import device_config as _dc
        from datetime import datetime, timedelta, timezone
        # None for a falsy/unparseable ts, or no known interval.
        if wake.next_wake_at_iso(None, {}) is not None:
            return False, "expected None for a falsy last_checkin_ts"
        if wake.next_wake_at_iso("", {"wake_interval_s": 900}) is not None:
            return False, "expected None for an empty-string last_checkin_ts"
        if wake.next_wake_at_iso("not-a-timestamp", {"wake_interval_s": 900}) is not None:
            return False, "expected None for an unparseable last_checkin_ts"
        if wake.next_wake_at_iso("2026-08-27T11:55:00+00:00", {}) is not None:
            return False, "expected None for a config with no known interval and no env fallback"
        # A screen-on config: last_checkin + wake_interval_s. Pre-existing
        # fixture, pinned byte-identical — 22-02-PLAN.md Task 1 must not
        # move this string, since this config carries no quiet-hours key
        # at all and quiet_hours_status() degrades to (None, None) for it.
        got = wake.next_wake_at_iso(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
        if got != "2026-08-27T12:10:00+00:00":
            return False, "expected last_checkin + wake_interval_s, got %r" % (got,)
        # A screen-off config: last_checkin + DISPLAY_OFF_SLEEP_S, the D-13
        # screen-off rule — wins over wake_interval_s regardless of its value.
        # Pre-existing fixture, pinned byte-identical for the same reason.
        got = wake.next_wake_at_iso(
            "2026-08-27T11:55:00+00:00",
            {"wake_interval_s": 900, "display_enabled": False})
        expected = (
            datetime(2026, 8, 27, 11, 55, 0, tzinfo=timezone.utc)
            + timedelta(seconds=_dc.DISPLAY_OFF_SLEEP_S)).isoformat()
        if got != expected:
            return False, "expected last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config, got %r" % (got,)

        # --- 22-02-PLAN.md Task 1 (D-03/CFG-26): the quiet-hours-active
        # fixtures the phase's validation contract lists as a Wave 0 gap
        # (22-VALIDATION.md line 48) — the existing pinned test above
        # covered screen-on/screen-off only, never a held frame, which is
        # exactly the case X2 is about.

        # Fixture A: quiet hours 23:00-07:00 Europe/Paris, last check-in
        # 22:58 Europe/Paris (a non-DST date), interval 900s. The naive
        # last_checkin + interval candidate (23:13) falls INSIDE the
        # window that opens two minutes after the check-in — the window
        # must win, returning the window's end (07:00 the next day), not
        # 23:13. This is the exact fixture 22-UI-SPEC.md §3.3 rule 6 (the
        # nightly regression) is built from.
        qh_config_a = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin_a = datetime(2026, 1, 15, 22, 58, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_a.isoformat(), qh_config_a)
        expected_a = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
        if got != expected_a:
            return False, (
                "fixture A (quiet hours 23:00-07:00, check-in 22:58, interval 900s): "
                "expected the window's end (%r), not the naive 23:13 candidate, got %r"
                % (expected_a, got))
        status_a = wake.next_wake_status(checkin_a.isoformat(), qh_config_a)
        if status_a[0] != expected_a:
            return False, "fixture A: next_wake_status()'s ISO element disagreed with next_wake_at_iso()"
        if status_a[2] != wake.HOLD_QUIET_HOURS:
            return False, "fixture A: expected hold_reason == HOLD_QUIET_HOURS, got %r" % (status_a[2],)
        if (checkin_a + timedelta(seconds=status_a[1])).isoformat() != expected_a:
            return False, (
                "fixture A: effective_interval_s (%r) added back to the check-in did not "
                "reproduce the returned ISO string" % (status_a[1],))

        # Fixture B: quiet hours enabled, but nowhere near active at the
        # check-in instant NOR at the check-in-plus-interval candidate —
        # returns the plain interval, unmodified. The window is evaluated
        # relative to last_checkin_ts, never at a render-time "now".
        qh_config_b = dict(qh_config_a)
        checkin_b = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_b.isoformat(), qh_config_b)
        expected_b = (checkin_b + timedelta(seconds=900)).isoformat()
        if got != expected_b:
            return False, (
                "fixture B (quiet hours enabled but inactive at check-in and at "
                "check-in+interval): expected the plain interval (%r), got %r"
                % (expected_b, got))
        status_b = wake.next_wake_status(checkin_b.isoformat(), qh_config_b)
        if status_b[2] is not None:
            return False, "fixture B: expected hold_reason is None when quiet hours never engages"

        # Fixture C: quiet hours active AND the screen off — the window
        # still wins when its remaining time is longer than
        # DISPLAY_OFF_SLEEP_S (300s); the screen-off cadence alone would
        # otherwise have won every 5 minutes all night.
        qh_config_c = {
            "wake_interval_s": 900, "display_enabled": False,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin_c = datetime(2026, 1, 16, 1, 0, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_c.isoformat(), qh_config_c)
        expected_c = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
        if got != expected_c:
            return False, (
                "fixture C (quiet hours active AND screen off): expected the window's end "
                "(%r), got %r — the window must win over the 300s screen-off cadence"
                % (expected_c, got))
        status_c = wake.next_wake_status(checkin_c.isoformat(), qh_config_c)
        if status_c[2] != wake.HOLD_QUIET_HOURS:
            return False, "fixture C: expected hold_reason == HOLD_QUIET_HOURS"

        # Fixture D: the richer accessor's None-triple for the same
        # never-raise edge cases the bare-ISO wrapper already covers.
        if wake.next_wake_status(None, {}) != (None, None, None):
            return False, "expected (None, None, None) for a falsy last_checkin_ts"
        if wake.next_wake_status("2026-08-27T11:55:00+00:00", {}) != (None, None, None):
            return False, (
                "expected (None, None, None) for a config with no known interval and no "
                "env fallback")

        # Fixture E: the richer accessor returns the effective interval
        # and hold reason (None) alongside the ISO string for the two
        # pre-existing, non-quiet-hours fixtures above.
        status_on = wake.next_wake_status(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
        if status_on != ("2026-08-27T12:10:00+00:00", 900, None):
            return False, "expected the screen-on fixture's richer result to carry interval=900, " \
                "hold_reason=None, got %r" % (status_on,)
        status_off = wake.next_wake_status(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": False})
        if status_off != (expected, _dc.DISPLAY_OFF_SLEEP_S, None):
            return False, "expected the screen-off fixture's richer result to carry " \
                "interval=DISPLAY_OFF_SLEEP_S, hold_reason=None, got %r" % (status_off,)
        return True, ""
    check(
        "wake.next_wake_at_iso()/next_wake_status() return None/(None, None, None) for a "
        "falsy/unparseable ts or an unknown interval, last_checkin + wake_interval_s for a "
        "screen-on config, last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config (D-13's "
        "screen-off rule), and — 22-02-PLAN.md Task 1, D-03/CFG-26 — the quiet-hours-active "
        "fixtures: a window opening during the base interval wins over the naive candidate, an "
        "enabled-but-nowhere-near-active window changes nothing, an active window beats a "
        "300s screen-off cadence, and the richer accessor carries the same effective interval "
        "and hold reason for every fixture above",
        _wake_next_wake_at_iso_contract)

    # --- 22-02-PLAN.md Task 2 (D-03/D-04): the one frame-state
    # resolution and the one delay sentence ---------------------------

    def _frame_state_resolve_state_contract():
        import companion.frame_state as frame_state
        from datetime import datetime, timedelta, timezone

        # No check-in recorded at all: unknown, no dot class claimed —
        # this module never returns a dot class in the first place.
        if frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00") \
                != frame_state.STATE_UNKNOWN:
            return False, "expected STATE_UNKNOWN for a falsy next_wake_iso"
        if frame_state.headline_template(
                frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00")) \
                != frame_state.HEADLINE_DUE:
            return False, "expected the unknown state to degrade to HEADLINE_DUE, never None"
        if frame_state.delay_sentence_template(None, None, None) != frame_state.DELAY_UNKNOWN:
            return False, "expected DELAY_UNKNOWN when no next_wake_iso is known"

        next_wake = "2026-01-15T12:00:00+00:00"
        interval_s = 900

        # now before next_wake: due.
        now_before = "2026-01-15T11:00:00+00:00"
        if frame_state.resolve_state(next_wake, interval_s, None, now_before) != frame_state.STATE_DUE:
            return False, "expected STATE_DUE when now is before next_wake"
        if frame_state.headline_template(frame_state.STATE_DUE) != frame_state.HEADLINE_DUE:
            return False, "expected HEADLINE_DUE for STATE_DUE"

        # now between next_wake and next_wake + 2 * interval: still due,
        # same copy — the grace window is invisible (rule 3), no third
        # state, no colour shift.
        now_in_grace = (
            datetime.fromisoformat(next_wake) + timedelta(seconds=interval_s)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, None, now_in_grace) != frame_state.STATE_DUE:
            return False, "expected STATE_DUE inside the grace window (next_wake + 1 * interval)"

        # now >= next_wake + 2 * interval, no hold: late.
        now_late = (
            datetime.fromisoformat(next_wake) + timedelta(seconds=2 * interval_s)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, None, now_late) != frame_state.STATE_LATE:
            return False, "expected STATE_LATE at exactly next_wake + 2 * interval"
        if frame_state.headline_template(frame_state.STATE_LATE) != frame_state.HEADLINE_LATE:
            return False, "expected HEADLINE_LATE for STATE_LATE"

        # hold reason quiet hours: held, regardless of how far now sits
        # past next_wake + 2 * interval (rule 4: a held frame cannot
        # escalate to late by elapsed time alone).
        import companion.wake as wake
        far_past = (
            datetime.fromisoformat(next_wake) + timedelta(days=3)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, now_late) \
                != frame_state.STATE_HELD:
            return False, "expected STATE_HELD when hold_reason is HOLD_QUIET_HOURS"
        if frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, far_past) \
                != frame_state.STATE_HELD:
            return False, (
                "expected STATE_HELD to survive 3 days past next_wake + 2 * interval — "
                "elapsed time alone must never escalate a held frame to late")
        if frame_state.headline_template(frame_state.STATE_HELD) != frame_state.HEADLINE_HELD:
            return False, "expected HEADLINE_HELD for STATE_HELD"

        # The delay sentence has exactly three branches — due, held,
        # unknown, never a fourth "late" branch.
        if frame_state.delay_sentence_template(next_wake, interval_s, None) != frame_state.DELAY_DUE:
            return False, "expected DELAY_DUE for a due (or late) triple"
        if frame_state.delay_sentence_template(next_wake, interval_s, wake.HOLD_QUIET_HOURS) \
                != frame_state.DELAY_HELD:
            return False, "expected DELAY_HELD when hold_reason is HOLD_QUIET_HOURS"

        # --- The nightly regression (22-UI-SPEC.md §3.3 binding rule 6):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00,
        # Europe/Paris (a non-DST date) — the resolved state must be
        # STATE_HELD, never STATE_LATE, end to end through
        # wake.next_wake_status() into frame_state.resolve_state().
        paris = timezone(timedelta(hours=1))
        qh_config = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
        next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
            checkin.isoformat(), qh_config)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
        nightly_state = frame_state.resolve_state(
            next_wake_iso, effective_interval_s, hold_reason, clock.isoformat())
        if nightly_state != frame_state.STATE_HELD:
            return False, (
                "the nightly regression: expected STATE_HELD at 02:00 for a 22:58 check-in "
                "inside a 23:00-07:00 quiet-hours window, got %r (next_wake=%r, "
                "effective_interval_s=%r, hold_reason=%r) — this is exactly X2's nightly "
                "false alarm" % (nightly_state, next_wake_iso, effective_interval_s, hold_reason))

        return True, ""
    check(
        "companion.frame_state.resolve_state() resolves due/held/late/unknown from a "
        "(next_wake_iso, effective_interval_s, hold_reason, now) tuple with an invisible grace "
        "window and a held frame that cannot escalate by elapsed time alone, "
        "headline_template()/delay_sentence_template() return the matching three-branch copy "
        "constants, and the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock "
        "02:00 Europe/Paris) resolves to STATE_HELD end to end through wake.next_wake_status() "
        "(D-03/D-04, 22-02-PLAN.md Task 2, 22-UI-SPEC.md §3.3 binding rule 6)",
        _frame_state_resolve_state_contract)

    def _frame_state_view_free_and_i18n_contract():
        frame_state_path = os.path.join(REPO_ROOT, "companion", "frame_state.py")
        with open(frame_state_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        if "dot--warn" in source:
            return False, "expected frame_state.py to never name a CSS dot class"
        for needle in ("import layout", "from companion.layout", "from .layout"):
            if needle in source:
                return False, "expected frame_state.py to stay view-free (no layout import)"

        import companion.frame_state as frame_state
        import companion.i18n as i18n
        # Each of the three headline and three delay-sentence constants
        # round-trips through the French catalogue (either frame_state's
        # own new entries, or — for the two deliberately-not-redefined
        # collisions — the pre-existing entries this module's docstring
        # names) and renders unchanged in English.
        headline_pairs = (
            (frame_state.HEADLINE_DUE, "Prochaine mise à jour ≈ %s"),
            (frame_state.HEADLINE_HELD, "Prochain réveil vers %s · heures calmes"),
            # 22-04-PLAN.md Task 1 (critical constraint 8): reconciled
            # from "Attendue depuis %s" (feminine agreement) to the
            # locked Copywriting Contract value, in companion/i18n_fr/
            # home.py, in the same commit as this plan's real consumer.
            (frame_state.HEADLINE_LATE, "Attendu depuis %s"),
        )
        for english, french in headline_pairs:
            if i18n.t_lang(english, "en") != english:
                return False, "expected %r unchanged under lang='en'" % (english,)
            if i18n.t_lang(english, "fr") != french:
                return False, "expected %r to translate to %r under lang='fr', got %r" % (
                    english, french, i18n.t_lang(english, "fr"))
        delay_pairs = (
            (frame_state.DELAY_DUE, "S’applique au prochain réveil, vers %s."),
            (frame_state.DELAY_HELD, "S’applique à la fin des heures calmes, vers %s."),
            (frame_state.DELAY_UNKNOWN, "S’applique au prochain réveil du cadre."),
        )
        for english, french in delay_pairs:
            if i18n.t_lang(english, "en") != english:
                return False, "expected %r unchanged under lang='en'" % (english,)
            if i18n.t_lang(english, "fr") != french:
                return False, "expected %r to translate to %r under lang='fr', got %r" % (
                    english, french, i18n.t_lang(english, "fr"))
        return True, ""
    check(
        "companion/frame_state.py names no dot--warn class and imports no layout module "
        "(view-free, D-03), and each of its six copy constants round-trips through "
        "companion.i18n's French catalogue unchanged in English (22-02-PLAN.md Task 2)",
        _frame_state_view_free_and_i18n_contract)

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

        def _airlines_dialog_forms_render_unconditionally_over_real_http():
            # 29-01-PLAN.md (CFG-81): the exact-"1" ?edit= membership
            # test this check used to prove end to end is deleted along
            # with the query parameter itself - a real authenticated
            # HTTP GET now renders the dialog's replace/delete/upload
            # forms with NO query string at all, and an arbitrary
            # leftover ?edit=1 in a bookmark changes nothing, proving
            # the removed parameter has no reader anywhere in the real
            # request path (not just in a direct render() call).
            unconditional_tokens = (
                airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,
                airlines_page.LIGHTBOX_DELETE_CLASS,
                airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
            )
            for query in ("", "?edit=1"):
                status, _headers, body = http_request(
                    base + "/airlines" + query, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200 for /airlines%s, got %d" % (query, status)
                body_text = body.decode("utf-8", "replace")
                for token in unconditional_tokens:
                    if ('class="%s"' % token) not in body_text:
                        return False, (
                            "expected /airlines%s to render a %r form (CFG-81: unconditional now)"
                            % (query, token))
            return True, ""
        check(
            "a real authenticated GET of /airlines renders the dialog's replace, delete and "
            "upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark "
            "renders identically — against a real running service, proving the removed query "
            "parameter has no reader anywhere in the real request path (CFG-81, 29-01-PLAN.md)",
            _airlines_dialog_forms_render_unconditionally_over_real_http)

        def _both_dialogs_arrive_through_one_starting_style_entrance():
            """23-10-PLAN.md Task 2 (D3/CFG-32): both <dialog>s fade and
            zoom in, from ONE rule.

            The two dialogs — History's panel lightbox and the Airlines
            gallery's wide variant — are the same component under two
            classes, so the entrance is declared once on `.lightbox` and
            reaches both. This check asserts that count directly (one
            entrance, two dialogs) rather than letting a second, drifting
            copy appear for the wide variant.

            It also asserts what is deliberately ABSENT. 23-08-PLAN.md
            Task 2 already set this app's precedent for a one-directional
            entrance — opening animates, closing is instant — and wrote
            down the reason: an element kept in the flow through
            `transition-behavior: allow-discrete` is still in the tab
            order and still in the accessibility tree for the whole of
            its exit, and for every browser that does not support the
            property. A <dialog> raises the stakes rather than lowering
            them, because a modal that has not reached `display: none`
            is an invisible sheet over the page that swallows clicks
            (T-23-36). So `display` must not appear in the lightbox
            transition at all: `close()` must end the dialog outright.
            """
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path, "r", encoding="utf-8") as fh:
                css = fh.read()
            # Comment-stripped, for the reason this file's own sibling
            # scans already record: the paragraphs around these rules
            # discuss @starting-style, allow-discrete and `display` by
            # name, and a raw scan would be answered by the prose that
            # explains the rule instead of by the rule.
            stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

            rendered = []
            for label, module, dialog_class in (
                ("history", history_page, "lightbox"),
                ("airlines", airlines_page, "lightbox lightbox--wide"),
            ):
                marker = '<dialog class="%s"' % dialog_class
                rendered.append((label, marker))

            entrances = re.findall(
                r"@starting-style\s*\{\s*\.lightbox\[open\]", stripped)
            # The open-state rule is counted with the @starting-style
            # blocks REMOVED, because the entrance block necessarily
            # repeats the same selector - counting the bare literal
            # reads 2 on a correct file, which is a number that means
            # nothing. What must be exactly one is the open-state rule
            # itself: one entrance, two dialogs.
            without_entrances = re.sub(
                r"@starting-style\s*\{.*?\}\s*\}", "", stripped, flags=re.DOTALL)
            open_rule = ".lightbox[open] {"
            if without_entrances.count(open_rule) != 1:
                return False, (
                    "expected exactly one %r rule outside @starting-style — one entrance serving "
                    "BOTH dialogs, got %d"
                    % (open_rule, without_entrances.count(open_rule)))
            if len(entrances) != 1:
                return False, (
                    "expected exactly ONE @starting-style entrance for .lightbox[open] (one "
                    "rule, two dialogs — History's and the Airlines gallery's wide variant are "
                    "the same component under two classes), got %d" % (len(entrances),))
            start_body = stripped[stripped.index(entrances[0]):]
            start_body = start_body[:start_body.index("}")]
            if "opacity: 0" not in start_body:
                return False, (
                    "expected the @starting-style entrance to start from opacity 0 — an element "
                    "going from display:none to displayed has no previous computed value to "
                    "transition from, which is the whole job of this block")
            if "scale(" not in start_body:
                return False, (
                    "expected the @starting-style entrance to start from a scale — D3's clause "
                    "is that both dialogs FADE AND ZOOM in")

            base_idx = stripped.index("\n.lightbox {")
            base = stripped[base_idx:stripped.index("}", base_idx)]
            if "transition:" not in base:
                return False, "expected .lightbox to declare the entrance transition"
            decl = base[base.index("transition:"):]
            decl = decl[:decl.index(";") + 1]
            for prop in ("opacity", "transform"):
                if prop not in decl:
                    return False, (
                        "expected the .lightbox transition to name %r, got %r" % (prop, decl))
            if "var(--motion-fast)" not in decl:
                return False, (
                    "expected the dialog entrance to spend var(--motion-fast), got %r" % (decl,))
            if "display" in decl or "allow-discrete" in decl:
                return False, (
                    "the .lightbox transition must NOT carry `display`/`allow-discrete`: a modal "
                    "that has not reached display:none is an invisible sheet over the page that "
                    "swallows clicks (T-23-36), and it stays in the tab order and the "
                    "accessibility tree for the whole of its exit — 23-08-PLAN.md Task 2's own "
                    "one-directional precedent, raised in stakes by a modal. Got %r" % (decl,))
            # ::backdrop is deliberately NOT animated, and that is a
            # reduced-motion fact rather than a taste one: the global
            # override matches `*, *::before, *::after`, which are
            # ELEMENT selectors — ::backdrop is in neither, exactly as
            # this file already records for the view-transition
            # pseudo-element tree. An animated backdrop would be motion
            # a reduced-motion visitor cannot switch off.
            backdrop_idx = stripped.index(".lightbox::backdrop {")
            backdrop = stripped[backdrop_idx:stripped.index("}", backdrop_idx)]
            if "transition" in backdrop or "animation" in backdrop:
                return False, (
                    ".lightbox::backdrop must not be animated — the global reduced-motion "
                    "override matches `*, *::before, *::after`, none of which is ::backdrop, so "
                    "a backdrop transition is motion a reduced-motion visitor cannot escape")

            # And both dialogs really do render with the class the one
            # rule above is keyed to.
            tmp = _mkstate("dialog-entrance")
            try:
                # History emits its dialog only on a page that has a
                # panel to show, so the fixture has to have one - an
                # empty-state render carries no dialog at all, which
                # would make the assertion below pass for the wrong
                # reason if it were inverted, and fail for the wrong
                # reason as written.
                names = ["2026-08-27T10-00-00+00-00.png"]
                _seed_gallery(tmp, names)
                _seed_runway_events(tmp, [
                    {"ts": "2026-08-27T10:03:00+00:00", "hex": "dlgent1",
                     "callsign": "DLGENT"},
                ])
                history_html = history_page.render(
                    _history_ctx(tmp, gallery_entries=names))
                airlines_html = airlines_page.render({})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            for label, marker in rendered:
                html_text = history_html if label == "history" else airlines_html
                if marker not in html_text:
                    return False, (
                        "expected the %s page to render %r so the one .lightbox[open] entrance "
                        "reaches it" % (label, marker))
            return True, ""
        check(
            "both <dialog>s arrive through ONE @starting-style entrance on .lightbox[open] — "
            "fading and zooming from opacity 0 over var(--motion-fast), reaching History's "
            "lightbox and the Airlines gallery's wide variant from a single rule, with `display`/"
            "`allow-discrete` deliberately absent so close() ends the dialog outright rather than "
            "leaving an invisible click-swallowing sheet over the page (T-23-36), and with "
            "::backdrop unanimated because the global reduced-motion override cannot reach it "
            "(D3/CFG-32, 23-10-PLAN.md Task 2)",
            _both_dialogs_arrive_through_one_starting_style_entrance)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("view-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
