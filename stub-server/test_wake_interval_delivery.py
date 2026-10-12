#!/usr/bin/env python3
"""A wake interval saved through the companion Device settings handler is
what a healthy frame receives as sleep_s, and the safety pins still win.

The save goes through companion.pages.config_page.handle_post into the state
directory a real stub-server/byos_server.py subprocess serves, and the
reply is read from a real GET /device/v1/display over loopback. The
precedence matrix (battery-critical park, display off, recovery) is
checked over HTTP for several saved intervals, and the companion's
read-side mirror server.wake.effective_wake_interval_s is checked against
the frame-facing reply for the same inputs.
"""
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SERVER_PATH = os.path.join(HERE, "byos_server.py")
IMAGE_BYTES = 960000
STARTUP_DEADLINE_S = 10.0
START_PORT_ATTEMPTS = 5
# Deliberately different from every interval under test, so a fallback to
# the server's own default can never pass as a saved value.
ENV_DEFAULT_SLEEP_S = 30
ENROL_SECRET = "5" * 64
TEST_MAC = "aa:bb:cc:dd:ee:21"

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import server.device_config as device_config  # noqa: E402
import server.device_policy as device_policy  # noqa: E402
import server.wake as server_wake  # noqa: E402
from companion.pages import config_page  # noqa: E402
from skypane_test_support import child_env  # noqa: E402

CANDIDATE_INTERVALS = (60, 300, 600, 900, 1800, 3600)
PARK_S = device_policy.BATTERY_CRITICAL_SLEEP_S
DISPLAY_OFF_S = device_config.DISPLAY_OFF_SLEEP_S


def load_byos_module():
    spec = importlib.util.spec_from_file_location("byos_server_delivery", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pick_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _http(url, method="GET", headers=None, json_body=None, timeout=10):
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class FrameServer:
    """A byos_server.py subprocess on a loopback port serving `state_dir`."""

    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.port = _pick_free_port()
        self.proc = None
        self.token = None
        self.stdout_path = os.path.join(state_dir, "byos.stdout.log")

    @property
    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def start(self):
        image_path = os.path.join(self.state_dir, "panel.bin")
        with open(image_path, "wb") as fh:
            fh.write(bytes(IMAGE_BYTES))
        load_byos_module().register_device(
            self.state_dir, TEST_MAC,
            hashlib.sha256(ENROL_SECRET.encode("ascii")).hexdigest(), replace=True)
        # pick_free_port() releases the port before the child binds it, so a
        # foreign listener can take it in between. Readiness is therefore
        # this child's own "serving" line (printed after a successful bind),
        # not a connect, and a child that lost the port is relaunched.
        for _ in range(START_PORT_ATTEMPTS):
            if self._launch_and_wait(image_path):
                break
            self.port = _pick_free_port()
        else:
            raise RuntimeError("byos_server.py could not get a free port")
        status, body = _http(
            self.base_url + "/device/v1/setup", method="POST",
            json_body={"mac": TEST_MAC, "hw_rev": "delivery-test",
                       "provision_secret": ENROL_SECRET})
        assert status == 200, "setup expected 200, got %d" % status
        self.token = json.loads(body.decode())["device_token"]

    def _launch_and_wait(self, image_path):
        """True once serving; False when the port was taken."""
        env = child_env()
        env["PYTHONUNBUFFERED"] = "1"
        with open(self.stdout_path, "w") as stdout_fh:
            self.proc = subprocess.Popen(
                [sys.executable, SERVER_PATH, "--image", image_path,
                 "--port", str(self.port), "--sleep", str(ENV_DEFAULT_SLEEP_S),
                 "--state-dir", self.state_dir],
                stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            output = self._read_stdout()
            if "serving" in output and (":%d" % self.port) in output:
                return True
            if self.proc.poll() is not None:
                if "Address already in use" in output:
                    self.proc = None
                    return False
                raise RuntimeError("byos_server.py exited early:\n%s" % output)
            time.sleep(0.05)
        raise RuntimeError("byos_server.py did not start:\n%s" % self._read_stdout())

    def _read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

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

    def display(self, battery_mv=None):
        """Parsed JSON of GET /device/v1/display (asserts a 200)."""
        headers = {"Authorization": "Bearer %s" % self.token}
        if battery_mv is not None:
            headers["X-Battery-Mv"] = str(battery_mv)
        status, body = _http(self.base_url + "/device/v1/display", headers=headers)
        assert status == 200, "display expected 200, got %d" % status
        return json.loads(body.decode())

    def sleep_s(self, battery_mv=None):
        return self.display(battery_mv)["sleep_s"]


@pytest.fixture
def frame_server(tmp_path):
    server = FrameServer(str(tmp_path))
    try:
        server.start()
        yield server
    finally:
        server.stop()


def save_interval(state_dir, value):
    flash = config_page.handle_post(
        {"wake_interval_s": str(value)}, {"state_dir": state_dir})
    assert flash == config_page.FLASH_SAVED, "saving %r gave %r" % (value, flash)


def set_latch(state_dir, active):
    with open(os.path.join(state_dir, "poll_state.json"), "w") as fh:
        json.dump({"battery_critical_active": active}, fh)


@pytest.mark.parametrize("value", CANDIDATE_INTERVALS)
def test_saved_interval_reaches_frame_sleep_s(frame_server, value):
    """An interval saved through the Device settings handler is exactly the
    sleep_s a healthy frame (4000 mV, no quiet hours) is told to sleep."""
    save_interval(frame_server.state_dir, value)
    assert frame_server.sleep_s(battery_mv=4000) == value


def test_unsaved_interval_falls_back_to_server_default(frame_server):
    """Control: without a saved interval the reply is the server's own
    default, which differs from every candidate."""
    assert frame_server.sleep_s(battery_mv=4000) == ENV_DEFAULT_SLEEP_S


def test_resaving_changes_the_next_reply(frame_server):
    """The config is read per request: a re-save shows in the very next reply."""
    save_interval(frame_server.state_dir, 300)
    assert frame_server.sleep_s(battery_mv=4000) == 300
    save_interval(frame_server.state_dir, 900)
    assert frame_server.sleep_s(battery_mv=4000) == 900


def test_interval_save_carries_quiet_hours_and_display_forward(tmp_path):
    """Saving only the interval leaves quiet hours and the display toggle alone."""
    state_dir = str(tmp_path)
    device_config.save_device_config(
        state_dir, quiet_hours_enabled=True, quiet_hours_start="23:30",
        quiet_hours_end="06:00", display_enabled=True)
    before = device_config.load_device_config(state_dir)
    save_interval(state_dir, 900)
    after = device_config.load_device_config(state_dir)
    assert after["wake_interval_s"] == 900
    for key in ("quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end",
                "display_enabled"):
        assert after[key] == before[key], "%s changed: %r -> %r" % (
            key, before[key], after[key])
    assert after["quiet_hours_enabled"] is True
    assert after["quiet_hours_start"] == "23:30"
    assert after["quiet_hours_end"] == "06:00"


def test_quiet_hours_never_shortens_saved_interval(tmp_path):
    """Inside a quiet-hours window the composed sleep is max(interval, time
    left in the window); outside it is the interval. The clock is injected
    because the HTTP handler uses the real one."""
    from datetime import datetime

    state_dir = str(tmp_path)
    device_config.save_device_config(
        state_dir, quiet_hours_enabled=True, quiet_hours_start="23:30",
        quiet_hours_end="06:00")
    save_interval(state_dir, 1800)
    byos = load_byos_module()
    base = byos.read_wake_interval_s(state_dir, ENV_DEFAULT_SLEEP_S)
    assert base == 1800

    # 22:00 UTC is 00:00 in Paris (UTC+2), inside the 23:30-06:00 window.
    inside = byos.quiet_hours_sleep_s(
        base, state_dir, now=datetime.fromisoformat("2026-10-12T22:00:00+00:00"))
    remaining = 6 * 3600
    assert inside == max(1800, remaining)
    assert inside >= 1800

    outside = byos.quiet_hours_sleep_s(
        base, state_dir, now=datetime.fromisoformat("2026-10-12T10:00:00+00:00"))
    assert outside == 1800


# (latch, display_enabled, X-Battery-Mv, expected kind)
# "park" -> 3600, "off" -> 300, "interval" -> the saved interval.
PRECEDENCE_CASES = [
    pytest.param(True, True, 3290, "park", id="latched-low-reading"),
    pytest.param(True, True, None, "park", id="latched-no-reading"),
    pytest.param(False, False, 4000, "off", id="display-off"),
    pytest.param(True, False, 3290, "park", id="display-off-and-latched"),
    pytest.param(True, True, 4100, "interval", id="latched-recovering"),
    pytest.param(False, True, 3290, "interval", id="unlatched-low-reading"),
]


def expected_sleep_s(kind, interval):
    return {"park": PARK_S, "off": DISPLAY_OFF_S, "interval": interval}[kind]


def arrange(frame_server, interval, latched, display_enabled):
    state_dir = frame_server.state_dir
    save_interval(state_dir, interval)
    if display_enabled is False:
        device_config.save_device_config(state_dir, display_enabled=False)
    set_latch(state_dir, latched)


@pytest.mark.parametrize("interval", (300, 900, 1800))
@pytest.mark.parametrize("latched,display_enabled,battery_mv,kind", PRECEDENCE_CASES)
def test_safety_pins_win_over_saved_interval(
        frame_server, interval, latched, display_enabled, battery_mv, kind):
    """The park (3600) and display-off (300) pins beat the saved interval,
    park beats display-off, and a recovery reading restores the interval."""
    arrange(frame_server, interval, latched, display_enabled)
    assert frame_server.sleep_s(battery_mv) == expected_sleep_s(kind, interval)


@pytest.mark.parametrize("interval", (60, 300, 900, 1800, 3600))
@pytest.mark.parametrize("latched,display_enabled,battery_mv,kind", PRECEDENCE_CASES)
def test_wake_mirror_matches_frame_sleep_s(
        frame_server, monkeypatch, interval, latched, display_enabled, battery_mv, kind):
    """The companion's server.wake.effective_wake_interval_s agrees with the
    frame-facing reply for every in-range case outside quiet hours."""
    monkeypatch.setenv("SKYPANE_SLEEP_S", str(ENV_DEFAULT_SLEEP_S))
    arrange(frame_server, interval, latched, display_enabled)
    # The companion passes the pin's truth (latch combined with the freshest
    # reading), which is what the frame-facing chain also uses.
    pinned = device_policy.battery_critical_pin_applies(latched, battery_mv)
    mirror = server_wake.effective_wake_interval_s(
        device_config.load_device_config(frame_server.state_dir),
        battery_critical=pinned)
    assert mirror == frame_server.sleep_s(battery_mv)
    assert mirror == expected_sleep_s(kind, interval)


def test_wake_mirror_matches_frame_without_saved_interval(frame_server, monkeypatch):
    """With no saved interval both fall back to the server's default."""
    monkeypatch.setenv("SKYPANE_SLEEP_S", str(ENV_DEFAULT_SLEEP_S))
    mirror = server_wake.effective_wake_interval_s(
        device_config.load_device_config(frame_server.state_dir),
        battery_critical=False)
    assert mirror == frame_server.sleep_s(battery_mv=4000) == ENV_DEFAULT_SLEEP_S
