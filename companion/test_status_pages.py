#!/usr/bin/env python3
"""Contract harness for companion/pages/health_page.py (CFG-03, CFG-05's
landing context) and companion/pages/airlines_page.py (CFG-04, CFG-08).

Covers: the two independent device/pipeline freshness signals and their
threshold boundaries, the battery trend table + dependency-free sparkline
(including the anomaly-vs-gentle-decline distinction), the three
corroboration states (the unknown state never reading as a failure), the
D-14 anomaly banner's presence/absence, CFG-05's source-fault landing
block, degrade-not-raise behaviour against a locked/missing database, the
CFG-04 unresolved-prefix registry's deterministic ordering and
malformed-entry tolerance, escaping of hostile registry values (a
script-tag-shaped example callsign), CFG-08's windowed resolution-rate
breakdown including its zero-history guard, that the Airlines page emits
no form/button anywhere (D-16), two static source-content regressions
guards, and one end-to-end HTTP round trip proving companion/app.py's
router and both page modules agree.

Every fixture is seeded programmatically into a temporary state directory
via server/history_db.py's own writer functions and
server/poll_loop.py's save_poll_state() — never a committed fixture file,
so this harness cannot drift from the schema those modules define.

Stdlib-only (datetime, os, shutil, socket, sqlite3, subprocess, sys,
tempfile, time, urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_status_pages.py
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth  # noqa: E402
from companion.pages import airlines_page, health_page  # noqa: E402
from server import history_db  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

TEST_PASSWORD = "status-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 40


# --- fixture helpers ---------------------------------------------------


def _mkstate(prefix):
    return tempfile.mkdtemp(prefix="skypane-status-pages-%s-" % prefix)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _now():
    return datetime.now(timezone.utc)


def _ago(seconds):
    return _iso(_now() - timedelta(seconds=seconds))


def _seed_device_health(state_dir, readings):
    """`readings`: an iterable of (ts, battery_mv) pairs."""
    with history_db.open_db(state_dir) as conn:
        for ts, battery_mv in readings:
            history_db.record_device_health(conn, ts, battery_mv=battery_mv)


def _seed_meta(state_dir, **kv):
    with history_db.open_db(state_dir) as conn:
        for key, value in kv.items():
            history_db.set_meta(conn, key, value)


def _seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for record_runway_event()."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def _seed_unresolved_prefixes(state_dir, registry):
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def _ctx(state_dir, now=None):
    return {"state_dir": state_dir, "now": now or _iso(_now())}


# --- HTTP harness (Section 3 only) --------------------------------------


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
    Harness class — owns the companion/app.py subprocess lifecycle.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-status-pages-e2e-")
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
    # Section 1: companion/pages/health_page.py
    # ======================================================================

    def _both_freshness_labels_present():
        tmp = _mkstate("h-labels")
        try:
            rendered = health_page.render(_ctx(tmp))
            if health_page.DEVICE_FRESHNESS_LABEL not in rendered:
                return False, "missing the device freshness label"
            if health_page.PIPELINE_FRESHNESS_LABEL not in rendered:
                return False, "missing the pipeline freshness label"
            if health_page.DEVICE_FRESHNESS_LABEL == health_page.PIPELINE_FRESHNESS_LABEL:
                return False, "the two labels must be distinct strings"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "render() shows two distinct, separately-labelled freshness signals",
        _both_freshness_labels_present)

    def _staleness_status_boundaries():
        warn_s, error_s = 100, 200
        if health_page.staleness_status(50, warn_s, error_s) != "ok":
            return False, "expected ok below the warn threshold"
        if health_page.staleness_status(warn_s, warn_s, error_s) != "warn":
            return False, "expected warn exactly at the warn threshold"
        if health_page.staleness_status(error_s, warn_s, error_s) != "error":
            return False, "expected error exactly at the error threshold"
        if health_page.staleness_status(None, warn_s, error_s) != "warn":
            return False, "expected warn (not error/ok) for a never-seen signal"
        return True, ""
    check(
        "staleness_status() returns ok/warn/error at the right boundaries, warn for a never-seen signal",
        _staleness_status_boundaries)

    def _independent_thresholds_one_warn_one_ok():
        tmp = _mkstate("h-independent")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            non_healthy = rendered.count("dot--warn") + rendered.count("dot--error")
            if non_healthy != 1:
                return False, "expected exactly one warn/error status class, got %d" % non_healthy
            # Two healthy dots are expected here: the fresh pipeline's, and
            # the Battery badge's (D-01) — a single seeded reading has no
            # consecutive pair to compare, so battery_status() correctly
            # returns "ok".
            if rendered.count("dot--ok") != 2:
                return False, (
                    "expected exactly two healthy status classes "
                    "(pipeline + battery badge), got %d" % rendered.count("dot--ok"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a stale device and a fresh pipeline produce one non-healthy row and two healthy rows, not a blended verdict",
        _independent_thresholds_one_warn_one_ok)

    def _battery_empty_state_no_svg():
        tmp = _mkstate("h-battery-empty")
        try:
            rendered = health_page.render(_ctx(tmp))
            if "No battery readings yet." not in rendered:
                return False, "expected the battery good-news empty-state heading"
            if "<svg" in rendered:
                return False, "did not expect an <svg with zero battery rows"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "zero battery rows render the good-news empty state and no <svg",
        _battery_empty_state_no_svg)

    def _battery_trend_shows_all_readings_and_one_sparkline():
        tmp = _mkstate("h-battery-trend")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            for _ts, mv in readings:
                if str(mv) not in rendered:
                    return False, "expected battery_mv=%d to appear (a trend, not just the latest)" % mv
            if rendered.count("<svg") != 1:
                return False, "expected exactly one <svg, got %d" % rendered.count("<svg")
            if rendered.count("<polyline") != 1:
                return False, "expected exactly one <polyline, got %d" % rendered.count("<polyline")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "three battery rows render the full trend (not just the latest value) and exactly one <svg><polyline>",
        _battery_trend_shows_all_readings_and_one_sparkline)

    def _battery_badge_present_and_healthy_on_normal_trend():
        tmp = _mkstate("h-battery-badge-ok")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4190),
            ]
            _seed_device_health(tmp, readings)
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if health_page.BATTERY_STATUS_LABEL not in rendered:
                return False, "expected the battery status badge label to appear"
            # Three healthy dots: device, pipeline (both fresh) and battery.
            if rendered.count("dot--ok") != 3:
                return False, "expected exactly three healthy status classes, got %d" % rendered.count("dot--ok")
            if "dot--warn" in rendered or "dot--error" in rendered:
                return False, "did not expect any non-healthy status class in this fixture"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Battery trend renders a healthy status_dot() badge on a normal trend (D-01)",
        _battery_badge_present_and_healthy_on_normal_trend)

    def _battery_empty_history_ok_badge_no_anomaly_banner():
        # 06.5-RESEARCH.md Pitfall 2: the empty-history branch must stay
        # "ok" (Assumption A1), or a freshly-provisioned device with zero
        # readings would display "A battery reading shows an abnormal
        # drop." — factually wrong copy. This check is a permanent
        # regression guard against that switch.
        #
        # Direct unit-level proof that _battery_section([]) itself never
        # produces an error badge or the abnormal-drop copy:
        markup, state = health_page._battery_section([])
        if state != "ok":
            return False, "expected _battery_section([]) to return state 'ok', got %r" % (state,)
        if health_page.BATTERY_STATUS_LABEL not in markup:
            return False, "expected the battery status badge label in the empty-history markup"
        if "dot--error" in markup or "dot--warn" in markup:
            return False, "did not expect a non-healthy status class in the empty-history markup"
        # Page-level proof that a fresh device with no meaningful battery
        # readings (device/pipeline both healthy, no drop possible) never
        # surfaces the abnormal-drop anomaly or the banner it drives —
        # device_health and battery trend share one table, so a page-level
        # "zero device_health rows at all" fixture would also make Device
        # check-in read as stale for an unrelated reason; this fixture
        # isolates the battery-specific guarantee instead.
        tmp = _mkstate("h-battery-empty-badge")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "dot--error" in rendered:
                return False, "did not expect an error status class with a single battery reading"
            if health_page.ANOMALY_BANNER_TEXT in rendered:
                return False, "did not expect the anomaly banner with a single, healthy battery reading"
            if "A battery reading shows an abnormal drop." in rendered:
                return False, "did not expect the abnormal-drop copy with a single battery reading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an empty/single-reading battery trend renders an ok badge and no anomaly banner (Assumption A1 regression guard)",
        _battery_empty_history_ok_badge_no_anomaly_banner)

    # 06.6.1-UI-SPEC.md's "Anomaly detail list (removed)" row: the <ul>
    # detail list this check used to assert on is gone this plan, so the
    # abnormal-drop copy must now be ABSENT from the rendered page while
    # collect_anomalies() called directly still returns it — the badge
    # and banner assertions (the check's real meaning: one signal drives
    # both) are kept exactly as they were.
    def _battery_drop_drives_badge_and_banner_detail_copy_not_rendered():
        tmp = _mkstate("h-battery-drop-badge")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
            ]
            _seed_device_health(tmp, readings)
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "dot--error" not in rendered:
                return False, "expected an error status class for a drop >= BATTERY_DROP_WARN_MV"
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            if "A battery reading shows an abnormal drop." in rendered:
                return False, "the abnormal-drop detail copy must no longer be rendered on the page"
            if health_page.collect_anomalies("ok", "ok", "error", False) != [
                    "A battery reading shows an abnormal drop."]:
                return False, "collect_anomalies() must still compute the abnormal-drop item directly"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real battery drop drives both the badge (error) and the banner; the detail copy is no longer rendered",
        _battery_drop_drives_badge_and_banner_detail_copy_not_rendered)

    def _anomaly_detail_list_markup_is_gone():
        tmp = _mkstate("h-no-list-markup")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if rendered.count("<ul") != 0:
                return False, "expected zero <ul occurrences — the anomaly detail list must be gone"
            if rendered.count("<li") != 0:
                return False, "expected zero <li occurrences — the anomaly detail list must be gone"
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an unhealthy fixture renders the anomaly banner with zero <ul/<li list markup",
        _anomaly_detail_list_markup_is_gone)

    def _none_of_the_four_anomaly_item_strings_render():
        tmp = _mkstate("h-all-four-anomalies")
        try:
            now = _now()
            # Trip all four D-14 signals at once: stale device, stale
            # pipeline, an abnormal battery drop, and a disagreement
            # recorded within the corroboration window.
            _seed_device_health(tmp, [
                (_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4200),
                (_ago(health_page.STALE_DEVICE_ERROR_S + 30),
                 4200 - health_page.BATTERY_DROP_WARN_MV),
            ])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN:
                    _ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": False}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            expected_items = health_page.collect_anomalies("error", "error", "error", True)
            if len(expected_items) != 4:
                return False, "expected collect_anomalies() to return all four items, got %r" % (expected_items,)
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            for item in expected_items:
                if item in rendered:
                    return False, "anomaly item copy leaked into the rendered page: %r" % item
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with all four D-14 signals unhealthy, none of collect_anomalies()'s four item strings is rendered",
        _none_of_the_four_anomaly_item_strings_render)

    # This check's scope is narrower than it first appears — it exercises
    # only battery_sparkline_svg()'s own return value, which still never
    # gains a script/url/image reference after Task 2's D-02 markup was
    # added. The page-level "exactly one scoped script" guarantee is
    # carried by _page_allows_exactly_one_scoped_script_no_inline_handlers()
    # below, added additively rather than by relaxing this one.
    def _sparkline_has_no_external_reference():
        rows = [
            {"ts": "t1", "battery_mv": 4200},
            {"ts": "t2", "battery_mv": 4100},
            {"ts": "t3", "battery_mv": 4050},
        ]
        svg = health_page.battery_sparkline_svg(rows)
        for forbidden in ("url(", "<image", "<script"):
            if forbidden in svg:
                return False, "found forbidden %r in the sparkline SVG" % forbidden
        return True, ""
    check(
        "battery_sparkline_svg() emits no url(, <image, or <script — no external reference at all",
        _sparkline_has_no_external_reference)

    def _sparkline_svg_has_per_point_interactive_markup():
        rows = [
            {"ts": "2024-01-03T00:00:00", "battery_mv": 4050},
            {"ts": "2024-01-02T00:00:00", "battery_mv": 4100},
            {"ts": "2024-01-01T00:00:00", "battery_mv": 4200},
        ]
        svg = health_page.battery_sparkline_svg(rows)
        if svg.count(health_page.SPARKLINE_HIT_CLASS) != 3:
            return False, "expected exactly 3 hit-target circles, got %d" % svg.count(health_page.SPARKLINE_HIT_CLASS)
        if svg.count(health_page.SPARKLINE_DOT_CLASS) != 3:
            return False, "expected exactly 3 cosmetic dot circles, got %d" % svg.count(health_page.SPARKLINE_DOT_CLASS)
        if svg.count("data-mv=") != 3:
            return False, "expected exactly 3 data-mv attributes, got %d" % svg.count("data-mv=")
        if svg.count("data-ts=") != 3:
            return False, "expected exactly 3 data-ts attributes, got %d" % svg.count("data-ts=")
        if svg.count("<title") != 3:
            return False, "expected exactly 3 <title elements, got %d" % svg.count("<title")
        if svg.count('tabindex="0"') != 3:
            return False, "expected exactly 3 tabindex=\"0\" hit targets, got %d" % svg.count('tabindex="0"')
        if svg.count("<polyline") != 1:
            return False, "expected exactly 1 <polyline, got %d" % svg.count("<polyline")
        for _ts, mv in [(r["ts"], r["battery_mv"]) for r in rows]:
            if ('data-mv="%d"' % mv) not in svg:
                return False, "expected battery_mv=%d to appear inside a data-mv attribute" % mv
        oldest_index = svg.find("2024-01-01T00:00:00")
        middle_index = svg.find("2024-01-02T00:00:00")
        newest_index = svg.find("2024-01-03T00:00:00")
        if not (oldest_index < middle_index < newest_index):
            return False, "expected timestamps in chronological (oldest-first) order, matching the polyline's own ordering"
        return True, ""
    check(
        "battery_sparkline_svg() emits per-point interactive hit targets with data-mv/data-ts/<title>, in chronological order",
        _sparkline_svg_has_per_point_interactive_markup)

    def _page_allows_exactly_one_scoped_script_no_inline_handlers():
        tmp = _mkstate("h-script-scope")
        try:
            base = _now()
            _seed_device_health(tmp, [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if rendered.count("<script") != 1:
                return False, "expected exactly one <script tag, got %d" % rendered.count("<script")
            if health_page.BATTERY_TREND_SCRIPT_SRC not in rendered:
                return False, "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>"
            for forbidden in ("onclick=", "onmouseover=", "ontouchstart=", "onfocus=", "onload="):
                if forbidden in rendered:
                    return False, "found forbidden inline event-handler attribute %r" % forbidden
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a chart-bearing page emits exactly one scoped <script src> and zero inline event-handler attributes",
        _page_allows_exactly_one_scoped_script_no_inline_handlers)

    def _empty_battery_history_stays_script_free():
        tmp = _mkstate("h-empty-script-free")
        try:
            rendered = health_page.render(_ctx(tmp))
            if "<script" in rendered:
                return False, "did not expect any <script tag with zero battery rows"
            if "<svg" in rendered:
                return False, "did not expect any <svg with zero battery rows"
            if health_page.BATTERY_READOUT_ID in rendered:
                return False, "did not expect the readout element id with zero battery rows"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the empty-history battery path stays script-free — no <script, no <svg, no readout element",
        _empty_battery_history_stays_script_free)

    def _hostile_timestamp_is_escaped_in_chart_markup():
        tmp = _mkstate("h-hostile-ts")
        try:
            base = _now()
            hostile_ts = '2024-01-01T00:00:00Z"><script>alert(1)</script>'
            _seed_device_health(tmp, [
                (hostile_ts, 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if hostile_ts in rendered:
                return False, "the raw hostile timestamp fragment survived unescaped into the output"
            if '"><script>alert(1)</script>' in rendered:
                return False, "the raw quote-and-tag fragment survived unescaped into a double-quoted attribute"
            escaped_ts = health_page.escape_html(hostile_ts)
            if escaped_ts not in rendered:
                return False, "expected the escaped form of the hostile timestamp to appear"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a hostile timestamp reaching data-ts/<title> is escaped, never interpolated raw",
        _hostile_timestamp_is_escaped_in_chart_markup)

    def _cross_file_contract_drift_guard():
        import companion.app as app_module
        if app_module.SCRIPT_ROUTE != health_page.BATTERY_TREND_SCRIPT_SRC:
            return False, "companion.app.SCRIPT_ROUTE and health_page.BATTERY_TREND_SCRIPT_SRC have drifted apart"
        js_path = os.path.join(HERE, "static", "battery-trend.js")
        with open(js_path) as fh:
            js_source = fh.read()
        if health_page.BATTERY_READOUT_ID not in js_source:
            return False, "battery-trend.js no longer references BATTERY_READOUT_ID's literal value"
        if health_page.SPARKLINE_HIT_CLASS not in js_source:
            return False, "battery-trend.js no longer references SPARKLINE_HIT_CLASS's literal value"
        tmp = _mkstate("h-contract-drift")
        try:
            base = _now()
            _seed_device_health(tmp, [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "expected BATTERY_READOUT_ID in a rendered chart-bearing page"
            if health_page.SPARKLINE_HIT_CLASS not in rendered:
                return False, "expected SPARKLINE_HIT_CLASS in a rendered chart-bearing page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Python/CSS/JS three-file contract (route + DOM literals) is guarded against silent drift",
        _cross_file_contract_drift_guard)

    def _battery_drop_flags_anomaly_gentle_decline_does_not():
        # battery_status() takes newest-first rows (matching
        # battery_trend_rows()'s/recent_device_health()'s own ordering) —
        # t2 (newer) sorts before t1 (older) in both fixtures below.
        drop_rows = [
            {"ts": "t2", "battery_mv": 4200 - health_page.BATTERY_DROP_WARN_MV},
            {"ts": "t1", "battery_mv": 4200},
        ]
        if health_page.battery_status(drop_rows) != "error":
            return False, "expected a drop >= BATTERY_DROP_WARN_MV to flag the battery anomaly"
        gentle_rows = [
            {"ts": "t3", "battery_mv": 4190},
            {"ts": "t2", "battery_mv": 4195},
            {"ts": "t1", "battery_mv": 4200},
        ]
        if health_page.battery_status(gentle_rows) != "ok":
            return False, "expected a gentle monotonic decline to not flag the battery anomaly"
        return True, ""
    check(
        "a large consecutive-reading drop flags the battery anomaly; a gentle monotonic decline does not",
        _battery_drop_flags_anomaly_gentle_decline_does_not)

    def _corroboration_unknown_only_no_error_or_warn():
        tmp = _mkstate("h-corrob-unknown")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": None},
                {"ts": _iso(now), "hex": "abc123", "corroborated": None},
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "dot--error" in rendered:
                return False, "expected no error status class for an unknown-state-only corroboration count"
            if "dot--warn" in rendered:
                return False, "expected no warn status class either — this fixture is fully healthy otherwise"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "corroboration counts made only of the unknown state produce no error status class",
        _corroboration_unknown_only_no_error_or_warn)

    def _no_anomaly_banner_when_all_healthy():
        tmp = _mkstate("h-no-anomaly")
        try:
            now = _now()
            _seed_device_health(tmp, [
                (_iso(now - timedelta(minutes=2)), 4200),
                (_iso(now), 4198),
            ])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [{"ts": _iso(now), "hex": "abc123", "corroborated": True}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if health_page.ANOMALY_BANNER_TEXT in rendered:
                return False, "did not expect the anomaly banner when every signal is healthy"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-healthy fixture renders no anomaly banner at all",
        _no_anomaly_banner_when_all_healthy)

    def _stale_pipeline_shows_banner_exactly_once():
        tmp = _mkstate("h-stale-pipeline")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN: _ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a stale ADS-B pipeline shows the anomaly banner copy exactly once",
        _stale_pipeline_shows_banner_exactly_once)

    def _unreadable_database_degrades_without_raising():
        base = tempfile.mkdtemp(prefix="skypane-status-pages-blocked-")
        blocked_state_dir = os.path.join(base, "blocked")
        try:
            with open(blocked_state_dir, "w") as fh:
                fh.write("this is a file, not a directory")
            rendered = health_page.render(_ctx(blocked_state_dir))
            if health_page.HEALTH_UNAVAILABLE_TEXT not in rendered:
                return False, "expected the health-unavailable copy when the database cannot be opened"
            return True, ""
        finally:
            shutil.rmtree(base, ignore_errors=True)
    check(
        "a state directory that cannot hold a database renders the health-unavailable copy without raising",
        _unreadable_database_degrades_without_raising)

    def _source_fault_set_shows_landing_explanation():
        tmp = _mkstate("h-source-fault-set")
        try:
            _seed_meta(tmp, **{history_db.META_SOURCE_FAULT: "True"})
            rendered = health_page.render(_ctx(tmp))
            if health_page.SOURCE_FAULT_HEADING not in rendered:
                return False, "expected the CFG-05 landing explanation when the source-fault flag is set"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with the source-fault meta key set, the CFG-05 landing explanation appears",
        _source_fault_set_shows_landing_explanation)

    def _source_fault_unset_hides_landing_explanation():
        tmp = _mkstate("h-source-fault-unset")
        try:
            rendered = health_page.render(_ctx(tmp))
            if health_page.SOURCE_FAULT_HEADING in rendered:
                return False, "did not expect the CFG-05 landing explanation with no source-fault flag set"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with the source-fault meta key unset, the CFG-05 landing explanation is absent",
        _source_fault_unset_hides_landing_explanation)

    def _health_page_never_imports_html_module():
        with open(os.path.join(HERE, "pages", "health_page.py")) as fh:
            source = fh.read()
        for line in source.splitlines():
            if line.strip() == "import html":
                return False, "health_page.py must never import the stdlib html module directly"
        return True, ""
    check(
        "companion/pages/health_page.py never imports the stdlib html module directly",
        _health_page_never_imports_html_module)

    def _health_page_renders_one_dashboard_grid_of_three_tiles_plus_battery_section():
        tmp = _mkstate("h-dashboard-grid")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if rendered.count('<div class="dashboard-grid">') != 1:
                return False, (
                    "expected exactly one dashboard-grid div, got %d"
                    % rendered.count('<div class="dashboard-grid">'))
            if rendered.count('class="stat-tile') != 3:
                return False, (
                    "expected exactly three stat-tile occurrences, got %d"
                    % rendered.count('class="stat-tile'))
            if rendered.count(">Overview<") != 1:
                return False, (
                    "expected exactly one Overview group heading, got %d"
                    % rendered.count(">Overview<"))
            if 'class="page-section"' in rendered:
                return False, "did not expect any page-section from the four signal sections"
            if rendered.count(health_page.BATTERY_SECTION_CLASS) != 1:
                return False, (
                    "expected exactly one battery-trend section, got %d"
                    % rendered.count(health_page.BATTERY_SECTION_CLASS))
            grid_close_index = rendered.index('<div class="dashboard-grid">') + rendered[
                rendered.index('<div class="dashboard-grid">'):].index("</div>")
            if rendered.index(health_page.BATTERY_SECTION_CLASS) <= grid_close_index:
                return False, "expected the battery-trend section to follow the dashboard-grid, not precede/overlap it"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a healthy fixture renders one dashboard-grid with exactly three stat tiles under one Overview heading, "
        "plus a positioned battery-trend section after it",
        _health_page_renders_one_dashboard_grid_of_three_tiles_plus_battery_section)

    def _battery_section_keeps_everything_after_the_move():
        tmp = _mkstate("h-battery-section-intact")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if ">%s<" % health_page.BATTERY_SECTION_HEADING not in rendered:
                return False, "expected BATTERY_SECTION_HEADING inside an <h2>"
            if health_page.BATTERY_STATUS_LABEL not in rendered:
                return False, "expected the battery status badge label to survive the move"
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "expected the readout element id to survive the move"
            if rendered.count("<script") != 1:
                return False, "expected exactly one <script occurrence, got %d" % rendered.count("<script")
            if health_page.BATTERY_TREND_SCRIPT_SRC not in rendered:
                return False, "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>"
            # Slice to the battery section's own boundaries — the three
            # surviving tiles would make a whole-page "no stat-tile"
            # search trivially fail.
            section_start = rendered.index('<section class="%s">' % health_page.BATTERY_SECTION_CLASS)
            section_html = rendered[section_start:]
            if "stat-tile" in section_html:
                return False, "the battery-trend section must carry no stat-tile class"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery-trend section keeps its badge, readout, and single script tag after moving out of the grid",
        _battery_section_keeps_everything_after_the_move)

    def _battery_section_class_is_styled_in_stylesheet():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        if health_page.BATTERY_SECTION_CLASS not in css_source:
            return False, "companion/static/style.css no longer styles BATTERY_SECTION_CLASS"
        return True, ""
    check(
        "health_page.BATTERY_SECTION_CLASS is guarded against silent drift from companion/static/style.css",
        _battery_section_class_is_styled_in_stylesheet)

    def _health_page_section_builder_markup_survives_reframe():
        tmp = _mkstate("h-reframe-survives")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            _seed_runway_events(tmp, [
                dict(
                    ts=_iso(base), hex="abc123", confirmed_state="DEPARTING",
                    corroborated="True"),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if "dot--" not in rendered:
                return False, "expected at least one dot-- status class to survive the reframe"
            if '<table class="data-table">' not in rendered:
                return False, "expected the battery table to survive the reframe"
            if "<svg" not in rendered:
                return False, "expected the battery sparkline svg to survive the reframe"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "battery and corroboration section-builder markup (dot, table, svg) survives the stat-tile reframe untouched",
        _health_page_section_builder_markup_survives_reframe)

    # ======================================================================
    # Section 2: companion/pages/airlines_page.py
    # ======================================================================

    def _empty_registry_good_news_no_table():
        tmp = _mkstate("a-empty")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            if "No coverage gaps." not in rendered:
                return False, "expected the CFG-04 good-news empty-state heading"
            if "<table" in rendered:
                return False, "did not expect a <table with an empty registry and zero history"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an empty unresolved-prefix registry renders the good-news empty state and no <table",
        _empty_registry_good_news_no_table)

    def _entries_sorted_by_count_descending():
        tmp = _mkstate("a-sorted")
        try:
            registry = {
                "XYZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ111"},
                "ABC": {"count": 9, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC222"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = airlines_page.render(_ctx(tmp))
            higher_index = rendered.find("ABC")
            lower_index = rendered.find("XYZ")
            if higher_index == -1 or lower_index == -1:
                return False, "expected both prefixes to appear in the rendered output"
            if higher_index > lower_index:
                return False, "expected the higher-count prefix (ABC, count=9) to appear before the lower one"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "two entries of unequal count render with the higher count first",
        _entries_sorted_by_count_descending)

    def _malformed_entries_skipped_not_crashing():
        tmp = _mkstate("a-malformed")
        try:
            registry = {
                "BAD": "not-a-dict-at-all",
                "ALSOBAD": {"count": "five"},
                "GOOD": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "GOOD123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rows = airlines_page.unresolved_rows(tmp)
            prefixes = [row[0] for row in rows]
            if prefixes != ["GOOD"]:
                return False, "expected only the well-formed entry to survive, got %r" % (prefixes,)
            rendered = airlines_page.render(_ctx(tmp))
            if "BAD" in rendered or "ALSOBAD" in rendered:
                return False, "a malformed entry's key leaked into the rendered output"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a registry entry that is not a dict, or whose count is not an int, is skipped rather than crashing the page",
        _malformed_entries_skipped_not_crashing)

    def _hostile_prefix_rendered_escaped():
        tmp = _mkstate("a-hostile-prefix")
        try:
            registry = {
                "<b>": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = airlines_page.render(_ctx(tmp))
            if "<b>" in rendered:
                return False, "an unescaped prefix reached the rendered output"
            if "&lt;b&gt;" not in rendered:
                return False, "expected the escaped form of the hostile prefix"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a prefix containing markup characters is rendered escaped",
        _hostile_prefix_rendered_escaped)

    def _script_tag_example_callsign_escaped():
        tmp = _mkstate("a-script-callsign")
        try:
            registry = {
                "ABC": {
                    "count": 1, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "<script>alert(1)</script>",
                },
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = airlines_page.render(_ctx(tmp))
            if "<script>alert(1)</script>" in rendered:
                return False, "an unescaped script tag reached the rendered output"
            if "&lt;script&gt;" not in rendered:
                return False, "expected the escaped form of the hostile example callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an example callsign shaped like a script tag renders escaped, with no unescaped script tag in the output",
        _script_tag_example_callsign_escaped)

    def _resolution_stats_four_categories_and_percentage():
        tmp = _mkstate("a-stats")
        try:
            now = _now()
            events = []
            for source in ("fresh_hit", "fresh_hit", "cache_hit", "airline_only", "miss"):
                events.append({"ts": _iso(now), "hex": "abc123", "route_source": source})
            _seed_runway_events(tmp, events)
            with history_db.open_db(tmp) as conn:
                stats = airlines_page.resolution_stats(conn, airlines_page.RESOLUTION_WINDOW_DAYS, now=now)
            if stats["total"] != 5:
                return False, "expected total=5, got %r" % (stats["total"],)
            if stats["resolved_pct"] != 80.0:
                return False, "expected resolved_pct=80.0 (4 of 5 not-a-miss), got %r" % (stats["resolved_pct"],)
            labels = [label for label, _gloss, _count in stats["rows"]]
            if labels != ["Fresh lookup", "Cached hit", "Airline only", "Miss"]:
                return False, "expected all four category labels in the fixed display order, got %r" % (labels,)
            rendered = airlines_page.render(_ctx(tmp, now=_iso(now)))
            if "80.0%" not in rendered:
                return False, "expected the resolved percentage headline in the rendered output"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "resolution_stats() breaks down the four documented source categories and computes the resolved percentage",
        _resolution_stats_four_categories_and_percentage)

    def _zero_history_stats_no_division_error():
        tmp = _mkstate("a-stats-empty")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            if "No resolution data yet." not in rendered:
                return False, "expected the statistics empty state with zero history rows"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "zero history rows render the statistics empty state rather than dividing by zero",
        _zero_history_stats_no_division_error)

    def _page_has_no_form_or_button():
        tmp = _mkstate("a-no-form")
        try:
            registry = {
                "ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = airlines_page.render(_ctx(tmp))
            if "<form" in rendered:
                return False, "the Airlines page must never contain a <form (D-16, read-only)"
            if "<button" in rendered:
                return False, "the Airlines page must never contain a <button (D-16, read-only)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Airlines page renders no <form and no <button anywhere",
        _page_has_no_form_or_button)

    def _airlines_page_source_has_no_direct_file_open():
        with open(os.path.join(HERE, "pages", "airlines_page.py")) as fh:
            source = fh.read()
        if "open(" in source:
            return False, "airlines_page.py must read the registry through poll_loop.load_poll_state(), never open() directly"
        return True, ""
    check(
        "companion/pages/airlines_page.py never opens a file directly (reads through load_poll_state())",
        _airlines_page_source_has_no_direct_file_open)

    def _airlines_page_source_never_rederives_enrich_logic():
        with open(os.path.join(HERE, "pages", "airlines_page.py")) as fh:
            source = fh.read()
        for needle in ("note_unresolved_prefix", "_AIRLINE_PREFIX_SHAPE_RE"):
            if needle in source:
                return False, "airlines_page.py must never re-derive enrich.py's prefix logic (found %r)" % needle
        return True, ""
    check(
        "companion/pages/airlines_page.py never references enrich.py's prefix-derivation internals",
        _airlines_page_source_never_rederives_enrich_logic)

    def _airlines_page_renders_one_dashboard_grid_of_two_tiles():
        tmp = _mkstate("a-dashboard-grid")
        try:
            registry = {
                "ABC": {
                    "count": 1, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = airlines_page.render(_ctx(tmp))
            if rendered.count('<div class="dashboard-grid">') != 1:
                return False, (
                    "expected exactly one dashboard-grid div, got %d"
                    % rendered.count('<div class="dashboard-grid">'))
            if rendered.count('class="stat-tile') != 2:
                return False, (
                    "expected exactly two stat-tile occurrences, got %d"
                    % rendered.count('class="stat-tile'))
            if rendered.count('<h2 class="text-heading">Coverage</h2>') != 1:
                return False, (
                    "expected exactly one Coverage group heading, got %d"
                    % rendered.count('<h2 class="text-heading">Coverage</h2>'))
            if "stat-tile--warn" not in rendered:
                return False, "expected the registry tile to carry stat-tile--warn with a non-empty registry"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a non-empty registry renders one dashboard-grid with exactly two stat tiles under one Coverage heading, registry tile stat-tile--warn",
        _airlines_page_renders_one_dashboard_grid_of_two_tiles)

    # ======================================================================
    # Section 3: one end-to-end check — a real companion/app.py subprocess,
    # logged in, fetching both tab routes against a seeded database.
    # ======================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        now = _now()
        _seed_device_health(harness.tmpdir, [(_iso(now), 4200)])
        _seed_meta(harness.tmpdir, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
        _seed_unresolved_prefixes(harness.tmpdir, {
            "ABC": {"count": 2, "first_seen": _iso(now), "last_seen": _iso(now), "example_callsign": "ABC123"},
        })

        def _both_tabs_ok_end_to_end():
            for path, heading in (("/health", "Health"), ("/airlines", "Airlines")):
                status, _headers, body = http_request(base + path, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200 for %s, got %d" % (path, status)
                if heading.encode() not in body:
                    return False, "expected the %r heading in %s's response body" % (heading, path)
            return True, ""
        check(
            "GET /health and GET /airlines both return 200 with their own page heading, against a real running service",
            _both_tabs_ok_end_to_end)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("status-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
