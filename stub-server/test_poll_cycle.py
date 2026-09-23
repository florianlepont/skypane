#!/usr/bin/env python3
"""End-to-end poll-cycle contract tests for stub-server/byos_server.py.

Generates a deterministic panel image with make_test_panel.py, launches
byos_server.py as a real subprocess on a free local port (both under the
non-loopback network guard via skypane_test_support.child_env()), and
drives it through the full device-protocol contract documented in
flightportrait/frame's docs/PROTOCOL.md at the pinned commit
ce3335fc5e566bcc6ccd29966ec39bf5c5318f12 (sections 1, 2, 3 and 5): setup,
the bearer-token auth gate, the display-response shape, download +
SHA-256 + exact-size verification, the hash-skip optimisation, a
served-image change, telemetry header echoing, the log endpoint, two
hand-built malformed-response rejections, connection failure
classification when the server is down, and the quiet-hours-aware
sleep_s extension (D-01): a drift guard pinning byos_server.py's
vendored seconds_until_quiet_hours_end()/_HHMM_RE byte-for-byte equal
to server/device_config.py's, unit coverage of read_quiet_hours()/
quiet_hours_sleep_s() loaded directly via importlib.util (byos_server.py's
module level is import-safe - constants and defs only, with main() behind
an `if __name__ == "__main__"` guard), and integration coverage of the
sleep_s extension and its fail-open contract over real HTTP. Also covers
read_wake_interval_s()'s fail-open contract (including the bool-is-an-int
gotcha) and happy path (D-01/D-03), the configured wake interval layering
under quiet_hours_sleep_s() without being re-clamped past
WAKE_INTERVAL_MAX_S, read_display_enabled()'s fail-open contract, the flat
300s off-state sleep_s pin (display_off_sleep_s()), the display-off/
quiet-hours overlap in both directions (D-05's sleep axis: the longest of
the two wins), an on-state regression guard proving the off-state branch
does not alter the pre-existing chain, a constant-parity check pinning
DISPLAY_OFF_SLEEP_S numerically equal between this file and
server/device_config.py, read_battery_critical()'s fail-open contract and
its behaviour parity against server.wake.read_battery_critical(),
battery_critical_sleep_s()'s parked/not-parked/recovery-anticipation
decision and its composed-chain interaction with the display-off and
quiet-hours pins, a constant-parity check for BATTERY_CRITICAL_SLEEP_S/
BATTERY_CRITICAL_RECOVER_MV, and a live-HTTP integration pair (parked,
then recovering) proving the pin over the real do_GET response.

The behaviour-parity check imports server.wake directly (the only
project import in this file) - unlike byos_server.py itself (the
vendored file this suite tests, which must never import server.*), this
file is not vendored, and every other cross-file check here reads the
project side as plain text (the drift guards) rather than importing it.
This one check needs the REAL function, not a byte-identical source
text, because read_battery_critical()'s two copies are deliberately NOT
byte-identical (one references server.wake.BATTERY_CRITICAL_STATE_KEY,
the other the literal string it equals) - so behaviour, not source
text, is what it proves equal.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SERVER_PATH = os.path.join(HERE, "byos_server.py")
MAKE_PANEL_PATH = os.path.join(HERE, "make_test_panel.py")
DEVICE_CONFIG_MODULE_PATH = os.path.join(REPO_ROOT, "server", "device_config.py")
POLL_LOOP_MODULE_PATH = os.path.join(REPO_ROOT, "server", "poll_loop.py")
IMAGE_BYTES = 960000
STARTUP_DEADLINE_S = 10.0
# A fixed 64-lowercase-hex enrolment secret Harness.start_server() registers
# both fixture MACs against before the subprocess starts, so the positive
# setup calls below keep working against byos_server.py's registry-gated
# /device/v1/setup.
HARNESS_ENROL_SECRET = "3" * 64

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# `pytest` invocation; the legacy-runner bridge below (MR-3) executes this
# file directly instead, so the same directory is added here too.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import server.wake as server_wake  # noqa: E402 - see the module docstring
from skypane_test_support import child_env  # noqa: E402


def verify_panel_bytes(buf, expected_hash):
    """Mirror the firmware verification rule (PROTOCOL.md section 2): a
    buffer reaches the panel only when its length is exactly 960000 bytes
    AND its SHA-256 hex digest equals the hex portion of the
    server-declared image_hash (which carries a "sha256:" prefix).
    """
    if len(buf) != IMAGE_BYTES:
        return False
    if expected_hash is None:
        return False
    expected_hex = expected_hash.split(":", 1)[-1] if ":" in expected_hash else expected_hash
    return hashlib.sha256(buf).hexdigest() == expected_hex


def validate_display_response(obj):
    """Mirror the firmware-side field rules for GET /device/v1/display
    responses (PROTOCOL.md section 2): image_hash is "sha256:" plus 64
    lowercase hex chars, sleep_s is an integer in 1..4294967295, reset
    is a JSON boolean, and image_url is a non-empty http/https string.

    The DEVICE-05 bring-up LED toggle (`led_enabled`) is deliberately
    *not* validated here: the firmware treats it as optional (absent,
    null or wrong-typed all resolve to enabled), and a mirror stricter
    than the thing it mirrors would be worse than no mirror at all.
    """
    if not isinstance(obj, dict):
        return False

    image_hash = obj.get("image_hash")
    if not isinstance(image_hash, str) or not image_hash.startswith("sha256:"):
        return False
    hexpart = image_hash[len("sha256:"):]
    if len(hexpart) != 64 or any(c not in "0123456789abcdef" for c in hexpart):
        return False

    sleep_s = obj.get("sleep_s")
    if isinstance(sleep_s, bool) or not isinstance(sleep_s, int):
        return False
    if not (1 <= sleep_s <= 4294967295):
        return False

    if not isinstance(obj.get("reset"), bool):
        return False

    image_url = obj.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        return False
    if not (image_url.startswith("http://") or image_url.startswith("https://")):
        return False

    return True


def http_request(url, method="GET", headers=None, json_body=None, timeout=10):
    """Minimal stdlib HTTP client. Returns (status, headers_dict, raw_bytes)
    for both success and HTTP-error responses; connection-level failures
    (server down, DNS, etc.) propagate as urllib.error.URLError / OSError
    so callers can classify them explicitly rather than have them
    misread as a 200.
    """
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def load_byos_module():
    """Load byos_server.py directly via importlib.util so its pure
    functions (read_quiet_hours(), quiet_hours_sleep_s(),
    seconds_until_quiet_hours_end()) can be unit-checked without going
    through HTTP. Safe because the module's top level is constants and
    defs only - main() sits behind an `if __name__ == "__main__"` guard.
    """
    spec = importlib.util.spec_from_file_location("byos_server_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_def_block(source_text, def_line_prefix):
    """Return the line starting with `def_line_prefix` plus every
    following line, up to (but not including) the first subsequent
    non-blank line that starts at column 0 - i.e. the whole body of the
    named top-level def, including its docstring. Returns None if
    `def_line_prefix` is never found.
    """
    lines = source_text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.startswith(def_line_prefix):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        if not line[0].isspace():
            end = i
            break
    return "".join(lines[start:end])


def _extract_line(source_text, line_prefix):
    """Return the first line in `source_text` starting with
    `line_prefix`, or None if not found.
    """
    for line in source_text.splitlines():
        if line.startswith(line_prefix):
            return line
    return None


class Harness:
    """Owns the byos_server.py subprocess lifecycle for a given state
    directory (always a pytest tmp_path, never a self-managed
    tempfile-created one - MR-5). Never leaves an orphaned server
    holding the port - callers must run stop_server() in a finally
    block. `env` defaults to child_env() (MR-9) so both the
    make_test_panel.py and byos_server.py children run under the same
    no-network guard as this pytest process.
    """

    def __init__(self, state_dir, env=None):
        self.tmpdir = state_dir
        self.port = self._pick_free_port()
        self.image_path = os.path.join(self.tmpdir, "panel.bin")
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
        self.env = env if env is not None else child_env()
        self.proc = None

    @staticmethod
    def _pick_free_port():
        # Bind port 0 and read back the OS-assigned port - never hardcode
        # a listen port, since a fixed port would collide with the
        # long-running stub instance the hardware plans keep alive.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def generate_panel(self, pattern, out_path=None):
        out_path = out_path or self.image_path
        subprocess.run(
            [sys.executable, MAKE_PANEL_PATH, "--pattern", pattern, "--out", out_path],
            check=True, capture_output=True, text=True, env=self.env,
        )
        return out_path

    def start_server(self, sleep_s=300, image_url_scheme=None):
        # Setup is registry-gated: register both fixture MACs against this
        # instance's own --state-dir before the subprocess starts.
        byos_module = load_byos_module()
        for mac in ("aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"):
            byos_module.register_device(
                self.tmpdir, mac,
                hashlib.sha256(HARNESS_ENROL_SECRET.encode("ascii")).hexdigest(),
                replace=True)
        stdout_fh = open(self.stdout_path, "w")
        cmd = [sys.executable, SERVER_PATH,
               "--image", self.image_path,
               "--port", str(self.port),
               "--sleep", str(sleep_s),
               "--state-dir", self.tmpdir]
        if image_url_scheme is not None:
            cmd += ["--image-url-scheme", image_url_scheme]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=stdout_fh, stderr=subprocess.STDOUT, env=self.env,
            )
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "byos_server.py exited early (code %s) before accepting "
                    "connections:\n%s" % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop_server(self):
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


@pytest.fixture(scope="module")
def byos_module():
    """byos_server.py loaded once via importlib.util - a pure module of
    constants and defs, safely reused read-only across every unit test
    below (MR-4: no test mutates it).
    """
    return load_byos_module()


# --- Unit: quiet-hours-aware sleep_s extension (D-01) --------------------


def test_quiet_hours_helpers_drift_guard_matches_device_config():
    """seconds_until_quiet_hours_end() and _HHMM_RE are byte-for-byte identical between
    server/device_config.py and stub-server/byos_server.py"""
    with open(DEVICE_CONFIG_MODULE_PATH) as fh:
        origin_text = fh.read()
    with open(SERVER_PATH) as fh:
        vendored_text = fh.read()

    origin_fn = _extract_def_block(origin_text, "def seconds_until_quiet_hours_end(")
    vendored_fn = _extract_def_block(vendored_text, "def seconds_until_quiet_hours_end(")
    assert origin_fn is not None, "could not locate seconds_until_quiet_hours_end() in server/device_config.py"
    assert vendored_fn is not None, "could not locate seconds_until_quiet_hours_end() in stub-server/byos_server.py"
    assert origin_fn == vendored_fn, (
        "seconds_until_quiet_hours_end() has drifted between server/device_config.py and "
        "stub-server/byos_server.py - the two copies must stay byte-for-byte identical:\n"
        "--- server/device_config.py ---\n%s\n"
        "--- stub-server/byos_server.py ---\n%s" % (origin_fn, vendored_fn)
    )

    origin_re = _extract_line(origin_text, "_HHMM_RE = re.compile(")
    vendored_re = _extract_line(vendored_text, "_HHMM_RE = re.compile(")
    assert origin_re is not None and vendored_re is not None, (
        "could not locate '_HHMM_RE = re.compile(' in one of the two files"
    )
    assert origin_re == vendored_re, (
        "_HHMM_RE has drifted between server/device_config.py and stub-server/byos_server.py:\n"
        "%r\nvs\n%r" % (origin_re, vendored_re)
    )


def test_read_quiet_hours_fail_open_never_raises(byos_module, tmp_path):
    """read_quiet_hours() returns None and never raises for a missing, truncated, non-dict,
    disabled, or badly-shaped device_config.json"""
    tmpdir = str(tmp_path)
    assert byos_module.read_quiet_hours(tmpdir) is None, "expected None for a missing device_config.json"
    cfg_path = os.path.join(tmpdir, "device_config.json")
    cases = [
        ("{truncated", "truncated JSON"),
        ('["not", "a", "dict"]', "a non-dict (list) document"),
        (json.dumps({"quiet_hours_enabled": False, "quiet_hours_start": "23:00",
                     "quiet_hours_end": "07:00"}), "quiet_hours_enabled: false"),
        (json.dumps({"quiet_hours_enabled": "yes", "quiet_hours_start": "23:00",
                     "quiet_hours_end": "07:00"}), 'quiet_hours_enabled: "yes"'),
        (json.dumps({"quiet_hours_enabled": True, "quiet_hours_start": "25:99",
                     "quiet_hours_end": "07:00"}), 'quiet_hours_start: "25:99"'),
        (json.dumps({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                     "quiet_hours_end": 7}), "quiet_hours_end: 7 (non-string)"),
    ]
    for raw, label in cases:
        with open(cfg_path, "w") as fh:
            fh.write(raw)
        result = byos_module.read_quiet_hours(tmpdir)
        assert result is None, "expected None for %s, got %r" % (label, result)


def test_quiet_hours_sleep_s_extends_inside_window_and_flat_after(byos_module, tmp_path):
    """quiet_hours_sleep_s() returns 28000 inside an enabled 23:00-07:00 window and the
    unchanged base 300 once the window has ended"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    with open(cfg_path, "w") as fh:
        json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                   "quiet_hours_end": "07:00"}, fh)
    inside = byos_module.quiet_hours_sleep_s(
        300, tmpdir, now=datetime.fromtimestamp(1700000000.0, timezone.utc))
    assert inside == 28000, "expected 28000 inside the window, got %r" % (inside,)
    past_end = byos_module.quiet_hours_sleep_s(
        300, tmpdir, now=datetime.fromtimestamp(1700028800.0, timezone.utc))
    assert past_end == 300, "expected 300 past the window's end, got %r" % (past_end,)


def test_quiet_hours_sleep_s_never_shorter_than_base(byos_module, tmp_path):
    """quiet_hours_sleep_s() never returns less than the base sleep, even when the base
    already carries the device past the window's end"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    with open(cfg_path, "w") as fh:
        json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                   "quiet_hours_end": "07:00"}, fh)
    result = byos_module.quiet_hours_sleep_s(
        86400, tmpdir, now=datetime.fromtimestamp(1700000000.0, timezone.utc))
    assert result == 86400, "expected max(86400, 28000) == 86400, got %r" % (result,)


# --- Unit: wake_interval_s delivery (D-01/D-03) ---------------------------


def test_read_wake_interval_s_fail_open_never_raises(byos_module, tmp_path):
    """read_wake_interval_s() returns the caller's default and never raises for a missing,
    truncated, non-dict, key-absent, bool (true), string, float, or out-of-range
    device_config.json"""
    tmpdir = str(tmp_path)
    assert byos_module.read_wake_interval_s(tmpdir, 300) == 300, "expected 300 for a missing device_config.json"
    cfg_path = os.path.join(tmpdir, "device_config.json")
    cases = [
        ("{truncated", "truncated JSON"),
        ('["not", "a", "dict"]', "a non-dict (list) document"),
        (json.dumps({"theme": "dark"}), "document with no wake_interval_s key"),
        (json.dumps({"wake_interval_s": True}), "wake_interval_s: true (bool-is-an-int gotcha)"),
        (json.dumps({"wake_interval_s": "120"}), 'wake_interval_s: "120" (string)'),
        (json.dumps({"wake_interval_s": 120.5}), "wake_interval_s: 120.5 (float)"),
        (json.dumps({"wake_interval_s": 30}), "wake_interval_s: 30 (below the 60s floor)"),
        (json.dumps({"wake_interval_s": 59}), "wake_interval_s: 59 (one below the floor)"),
        (json.dumps({"wake_interval_s": 3601}), "wake_interval_s: 3601 (one above the ceiling)"),
    ]
    for raw, label in cases:
        with open(cfg_path, "w") as fh:
            fh.write(raw)
        result = byos_module.read_wake_interval_s(tmpdir, 300)
        assert result == 300, "expected 300 (default) for %s, got %r" % (label, result)


def test_read_wake_interval_s_happy_path(byos_module, tmp_path):
    """read_wake_interval_s() returns 120 for a stored 120 and returns the inclusive bounds
    60 and 3600 unchanged"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    for stored, expected in ((120, 120), (60, 60), (3600, 3600)):
        with open(cfg_path, "w") as fh:
            json.dump({"wake_interval_s": stored}, fh)
        result = byos_module.read_wake_interval_s(tmpdir, 300)
        assert result == expected, "expected %r for stored wake_interval_s=%r, got %r" % (expected, stored, result)


def test_wake_interval_layers_under_quiet_hours_without_reclamping(byos_module, tmp_path):
    """quiet_hours_sleep_s(read_wake_interval_s(...), ...) uses the configured 120 as its
    base with quiet hours disabled, and still returns 28000 (> 3600) inside an active
    quiet-hours window - the delivered value is deliberately not re-clamped"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    with open(cfg_path, "w") as fh:
        json.dump({"wake_interval_s": 120}, fh)
    disabled = byos_module.quiet_hours_sleep_s(
        byos_module.read_wake_interval_s(tmpdir, 300), tmpdir)
    assert disabled == 120, "expected the configured 120 with quiet hours disabled, got %r" % (disabled,)

    with open(cfg_path, "w") as fh:
        json.dump({"wake_interval_s": 120, "quiet_hours_enabled": True,
                   "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}, fh)
    inside_window = byos_module.quiet_hours_sleep_s(
        byos_module.read_wake_interval_s(tmpdir, 300), tmpdir,
        now=datetime.fromtimestamp(1700000000.0, timezone.utc))
    assert inside_window == 28000, "expected 28000 inside the window, got %r" % (inside_window,)
    assert inside_window > byos_module.WAKE_INTERVAL_MAX_S, (
        "expected the delivered sleep_s (%r) to exceed WAKE_INTERVAL_MAX_S (%r) during an "
        "active quiet-hours window - re-clamping here would strand the device waking hourly "
        "through the window" % (inside_window, byos_module.WAKE_INTERVAL_MAX_S))


# --- Unit: display-off sleep_s pin (D-01/D-05) ----------------------------


def test_read_display_enabled_fail_open_never_raises(byos_module, tmp_path):
    """read_display_enabled() returns True and never raises for a missing, truncated,
    non-dict, key-absent, or non-bool (0, 1, "false", null) device_config.json, and a
    real display_enabled:false survives as False"""
    tmpdir = str(tmp_path)
    assert byos_module.read_display_enabled(tmpdir) is True, "expected True for a missing device_config.json"
    cfg_path = os.path.join(tmpdir, "device_config.json")
    cases = [
        ("{truncated", "truncated JSON"),
        ('["not", "a", "dict"]', "a non-dict (list) document"),
        (json.dumps({"theme": "dark"}), "document with no display_enabled key"),
        (json.dumps({"display_enabled": 0}), "display_enabled: 0 (int)"),
        (json.dumps({"display_enabled": 1}), "display_enabled: 1 (int)"),
        (json.dumps({"display_enabled": "false"}), 'display_enabled: "false" (string)'),
        (json.dumps({"display_enabled": None}), "display_enabled: null"),
    ]
    for raw, label in cases:
        with open(cfg_path, "w") as fh:
            fh.write(raw)
        result = byos_module.read_display_enabled(tmpdir)
        assert result is True, "expected True (fail-open) for %s, got %r" % (label, result)
    with open(cfg_path, "w") as fh:
        json.dump({"display_enabled": False}, fh)
    assert byos_module.read_display_enabled(tmpdir) is False, "expected a real display_enabled:false to survive as False"


def test_display_off_flat_pin_is_300_regardless_of_base(byos_module, tmp_path):
    """with display_enabled false and no quiet-hours window, quiet_hours_sleep_s(display_off_sleep_s(base, d), d)
    is exactly 300 for base in 60, 300, 900 and 3600 (base=3600 proves the pin REPLACES rather than bounds the
    configured interval)"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    with open(cfg_path, "w") as fh:
        json.dump({"display_enabled": False}, fh)
    for base in (60, 300, 900, 3600):
        result = byos_module.quiet_hours_sleep_s(
            byos_module.display_off_sleep_s(base, tmpdir), tmpdir)
        assert result == 300, "expected 300 for base=%r, got %r" % (base, result)


def test_display_off_and_quiet_hours_overlap_unit(byos_module, tmp_path):
    """with the display off and quiet hours active, the served sleep_s is max(300, quiet_hours_remaining)
    in both directions: 28000s of remaining window time wins over the 300s off-state pin, and the 300s pin
    still floors the value when only 200s remain in the window - the device never wakes more often than
    quiet hours alone would have made it"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    with open(cfg_path, "w") as fh:
        json.dump({"display_enabled": False, "quiet_hours_enabled": True,
                   "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}, fh)

    # Well inside the window (23:30 entry -> 28000s remaining, verified
    # independently against seconds_until_quiet_hours_end() during
    # planning). The remaining time must win over the 300s off-state pin.
    far_from_end = byos_module.quiet_hours_sleep_s(
        byos_module.display_off_sleep_s(300, tmpdir), tmpdir,
        now=datetime.fromtimestamp(1700000000.0, timezone.utc))
    assert far_from_end == 28000, (
        "expected the remaining 28000s to win over the 300s off-state pin, got %r - the off "
        "state must never shorten a quiet-hours sleep" % (far_from_end,))

    # Inside the window's last 200 seconds (below the 300s pin; window
    # end epoch 1700028000.0, verified during planning). The 300s pin
    # must win here - the device never sleeps for LESS than the
    # off-state pin either.
    close_to_end = byos_module.quiet_hours_sleep_s(
        byos_module.display_off_sleep_s(300, tmpdir), tmpdir,
        now=datetime.fromtimestamp(1700028000.0 - 200, timezone.utc))
    assert close_to_end == 300, (
        "expected the 300s off-state pin to win when only 200s remain in the quiet-hours "
        "window, got %r" % (close_to_end,))


def test_display_on_state_matches_preexisting_chain(byos_module, tmp_path):
    """with display_enabled true, the composed sleep_s chain (including display_off_sleep_s())
    equals the pre-existing Phase 10/11 quiet_hours_sleep_s(read_wake_interval_s(...)) chain
    across all four combinations of window active/inactive and wake_interval_s set/unset - this
    plan adds a branch, it does not alter the on-state behaviour"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    base_default = 300
    window_now = datetime.fromtimestamp(1700000000.0, timezone.utc)
    combos = [
        ({"display_enabled": True}, None,
         "no wake_interval_s, no window"),
        ({"display_enabled": True, "wake_interval_s": 120}, None,
         "wake_interval_s set, no window"),
        ({"display_enabled": True, "quiet_hours_enabled": True,
          "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"},
         window_now, "no wake_interval_s, window active"),
        ({"display_enabled": True, "wake_interval_s": 120,
          "quiet_hours_enabled": True, "quiet_hours_start": "23:00",
          "quiet_hours_end": "07:00"},
         window_now, "wake_interval_s set, window active"),
    ]
    for cfg, now, label in combos:
        with open(cfg_path, "w") as fh:
            json.dump(cfg, fh)
        kwargs = {"now": now} if now is not None else {}
        preexisting = byos_module.quiet_hours_sleep_s(
            byos_module.read_wake_interval_s(tmpdir, base_default), tmpdir, **kwargs)
        composed = byos_module.quiet_hours_sleep_s(
            byos_module.display_off_sleep_s(
                byos_module.read_wake_interval_s(tmpdir, base_default), tmpdir),
            tmpdir, **kwargs)
        assert composed == preexisting, (
            "on-state regression for %s: composed=%r, pre-existing chain=%r"
            % (label, composed, preexisting))


def test_display_off_sleep_s_constant_parity(byos_module):
    """DISPLAY_OFF_SLEEP_S is numerically equal between server/device_config.py (read as plain
    text, never imported) and the loaded stub-server/byos_server.py module"""
    with open(DEVICE_CONFIG_MODULE_PATH) as fh:
        origin_text = fh.read()
    origin_line = _extract_line(origin_text, "DISPLAY_OFF_SLEEP_S = ")
    assert origin_line is not None, "could not locate 'DISPLAY_OFF_SLEEP_S = ' in server/device_config.py"
    origin_value = int(origin_line.split("=", 1)[1].strip().split()[0])
    assert origin_value == byos_module.DISPLAY_OFF_SLEEP_S, (
        "DISPLAY_OFF_SLEEP_S has drifted between server/device_config.py (%r) and "
        "stub-server/byos_server.py (%r)" % (origin_value, byos_module.DISPLAY_OFF_SLEEP_S)
    )


# --- Unit: BATTERY EMPTY hold (battery-empty-screen-before-the-pack-die) --


def test_read_battery_critical_fail_open_matches_server_wake(byos_module, tmp_path):
    """read_battery_critical() degrades to False and never raises for a missing file, malformed
    JSON, a non-dict payload, the string "true", the int 1, and a literal false, returns True
    only for a literal JSON true, and matches server.wake.read_battery_critical() on every one
    of those fixtures (behaviour parity)"""
    tmpdir = str(tmp_path)
    path = os.path.join(tmpdir, "poll_state.json")

    def _both(label):
        byos_result = byos_module.read_battery_critical(tmpdir)
        server_result = server_wake.read_battery_critical(tmpdir)
        assert byos_result == server_result, (
            "%s: byos read_battery_critical()=%r != server.wake.read_battery_critical()=%r"
            % (label, byos_result, server_result)
        )
        return byos_result

    got = _both("a missing poll_state.json")
    assert got is False, "a missing poll_state.json: expected False, got %r" % (got,)

    cases = [
        ("{not valid json", "malformed JSON"),
        (json.dumps([1, 2, 3]), "a non-dict (list) payload"),
        (json.dumps({"battery_critical_active": "true"}), 'a string "true"'),
        (json.dumps({"battery_critical_active": 1}), "an int 1"),
        (json.dumps({"battery_critical_active": False}), "a literal false"),
    ]
    for raw, label in cases:
        with open(path, "w") as fh:
            fh.write(raw)
        got = _both(label)
        assert got is False, "%s: expected False, got %r" % (label, got)

    with open(path, "w") as fh:
        json.dump({"battery_critical_active": True}, fh)
    got = _both("a literal true")
    assert got is True, "a literal JSON true: expected True, got %r" % (got,)


def test_battery_critical_sleep_s_unit(byos_module, tmp_path):
    """battery_critical_sleep_s(base, d, fresh_mv): not parked returns base unchanged for every
    base; parked returns exactly BATTERY_CRITICAL_SLEEP_S (3600) for bases 60/300/3600; a fresh
    reading of 3800 mV (at or above BATTERY_CRITICAL_RECOVER_MV) anticipates recovery and returns
    base instead; and a fresh reading of 3500 mV or None stays parked"""
    tmpdir = str(tmp_path)
    path = os.path.join(tmpdir, "poll_state.json")

    # Not parked: base wins for every base, regardless of the fresh reading.
    for base in (60, 300, 3600):
        got = byos_module.battery_critical_sleep_s(base, tmpdir, 3290)
        assert got == base, "not parked: base=%r expected unchanged, got %r" % (base, got)

    with open(path, "w") as fh:
        json.dump({"battery_critical_active": True}, fh)

    # Parked: exactly BATTERY_CRITICAL_SLEEP_S for every base - a flat
    # replacement, not a max()/min() against the base.
    for base in (60, 300, 3600):
        got = byos_module.battery_critical_sleep_s(base, tmpdir, None)
        assert got == byos_module.BATTERY_CRITICAL_SLEEP_S, (
            "parked: base=%r expected BATTERY_CRITICAL_SLEEP_S (%r), got %r"
            % (base, byos_module.BATTERY_CRITICAL_SLEEP_S, got)
        )

    # Recovery anticipation: a fresh reading at or above
    # BATTERY_CRITICAL_RECOVER_MV wins over the parked pin even while
    # the persisted latch is still True.
    got = byos_module.battery_critical_sleep_s(300, tmpdir, 3800)
    assert got == 300, "parked with fresh_battery_mv=3800 (recovering): expected base (300), got %r" % (got,)

    # Below the recovery threshold, or unreported, stays parked.
    for fresh_mv in (3500, None):
        got = byos_module.battery_critical_sleep_s(300, tmpdir, fresh_mv)
        assert got == byos_module.BATTERY_CRITICAL_SLEEP_S, (
            "parked with fresh_battery_mv=%r: expected BATTERY_CRITICAL_SLEEP_S (%r), got %r"
            % (fresh_mv, byos_module.BATTERY_CRITICAL_SLEEP_S, got)
        )


def test_battery_critical_composed_chain(byos_module, tmp_path):
    """the composed sleep_s chain: parked with display_enabled=False yields exactly 3600s (the
    parked pin beats the 300s off-state pin), and parked inside a quiet-hours window with more
    than 3600s remaining yields the window's own remaining time (the longer pin always wins,
    D-05's sleep axis extended)"""
    tmpdir = str(tmp_path)
    cfg_path = os.path.join(tmpdir, "device_config.json")
    poll_state_path = os.path.join(tmpdir, "poll_state.json")

    # Parked AND display off: the 3600s parked pin beats the 300s
    # display-off pin - composed inside it, per the documented nesting
    # order.
    with open(cfg_path, "w") as fh:
        json.dump({"display_enabled": False}, fh)
    with open(poll_state_path, "w") as fh:
        json.dump({"battery_critical_active": True}, fh)
    got = byos_module.quiet_hours_sleep_s(
        byos_module.battery_critical_sleep_s(
            byos_module.display_off_sleep_s(300, tmpdir), tmpdir, None),
        tmpdir)
    assert got == byos_module.BATTERY_CRITICAL_SLEEP_S, (
        "parked with display_enabled=False: expected the 3600s parked pin to beat the 300s "
        "off-state pin, got %r" % (got,)
    )

    # Parked inside a quiet-hours window with MORE than 3600s remaining
    # (the same 23:00-07:00 window entered at 23:30, 28000s remaining):
    # the window's remaining time wins over the 3600s parked pin.
    os.remove(cfg_path)
    now = datetime.fromtimestamp(1700000000.0, timezone.utc)
    with open(cfg_path, "w") as fh:
        json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                   "quiet_hours_end": "07:00"}, fh)
    got = byos_module.quiet_hours_sleep_s(
        byos_module.battery_critical_sleep_s(
            byos_module.display_off_sleep_s(300, tmpdir), tmpdir, None),
        tmpdir, now=now)
    assert got == 28000, (
        "parked inside a >3600s quiet-hours window: expected the window's remaining 28000s to "
        "win over the 3600s parked pin, got %r" % (got,)
    )


def test_battery_critical_constant_parity(byos_module):
    """BATTERY_CRITICAL_SLEEP_S is numerically equal between server/device_config.py and the
    loaded stub-server/byos_server.py module, and BATTERY_CRITICAL_RECOVER_MV is numerically
    equal between server/poll_loop.py and the loaded module - both read as plain text, never
    imported"""
    with open(DEVICE_CONFIG_MODULE_PATH) as fh:
        device_config_text = fh.read()
    with open(POLL_LOOP_MODULE_PATH) as fh:
        poll_loop_text = fh.read()

    sleep_line = _extract_line(device_config_text, "BATTERY_CRITICAL_SLEEP_S = ")
    assert sleep_line is not None, "could not locate 'BATTERY_CRITICAL_SLEEP_S = ' in server/device_config.py"
    sleep_value = int(sleep_line.split("=", 1)[1].strip().split()[0])
    assert sleep_value == byos_module.BATTERY_CRITICAL_SLEEP_S, (
        "BATTERY_CRITICAL_SLEEP_S has drifted between server/device_config.py (%r) and "
        "stub-server/byos_server.py (%r)" % (sleep_value, byos_module.BATTERY_CRITICAL_SLEEP_S)
    )

    recover_line = _extract_line(poll_loop_text, "BATTERY_CRITICAL_RECOVER_MV = ")
    assert recover_line is not None, "could not locate 'BATTERY_CRITICAL_RECOVER_MV = ' in server/poll_loop.py"
    recover_value = int(recover_line.split("=", 1)[1].strip().split()[0])
    assert recover_value == byos_module.BATTERY_CRITICAL_RECOVER_MV, (
        "BATTERY_CRITICAL_RECOVER_MV has drifted between server/poll_loop.py (%r) and "
        "stub-server/byos_server.py (%r)" % (recover_value, byos_module.BATTERY_CRITICAL_RECOVER_MV)
    )


# --- Standalone: validate_display_response() negative controls -----------


def test_validate_display_response_rejects_sleep_s_zero():
    """validate_display_response rejects sleep_s=0"""
    bad = {"image_hash": "sha256:" + "a" * 64, "sleep_s": 0, "reset": False,
           "image_url": "http://example.invalid/img/x.bin"}
    assert not validate_display_response(bad), "validator accepted a hand-built response with sleep_s=0"


def test_validate_display_response_rejects_uppercase_image_hash():
    """validate_display_response rejects uppercase hex in image_hash"""
    bad = {"image_hash": "sha256:" + "A" * 64, "sleep_s": 300, "reset": False,
           "image_url": "http://example.invalid/img/x.bin"}
    assert not validate_display_response(bad), (
        "validator accepted a hand-built response with uppercase hex in image_hash"
    )


# --- Integration: the real device protocol over one long-lived server ----


def test_device_protocol_end_to_end_over_real_http(tmp_path):
    """Covers, in order, every old check this suite used to run against ONE
    long-lived byos_server.py subprocess sharing state across the whole
    scenario (a device_token issued once and reused, a served image hash
    that later checks assert against, and a battery_state.json
    persistence chain) - MR-4, these are not independently reorderable:

    1. setup issues a 64-lowercase-hex device_token
    2. setup rejects a body missing mac with 422
    3. display poll with no Authorization header returns 401
    4. display poll with an unissued bearer returns 401
    5. display poll returns a valid response shape (incl. firmware:null and led_enabled:true)
    6. download yields exactly 960000 bytes matching image_hash
    7. verify_panel_bytes rejects a flipped byte
    8. verify_panel_bytes rejects a one-byte truncation
    9. a second poll of an unchanged image returns the same image_hash (hash-skip)
    10. replacing the served image changes image_hash and the client re-downloads
    11. telemetry headers are accepted and echoed to server stdout
    12. log endpoint accepts a logs array and returns ok:true
    13. default --image-url-scheme (http) is served in image_url
    14. --image-url-scheme https serves image_url with https:// and an unchanged host/path/digest
    15. an authenticated poll carrying a plausible X-Battery-Mv persists {battery_mv, received_at}
        to battery_state.json, and a second poll with a different value overwrites it
    16. 10 hostile/malformed X-Battery-Mv values all return 200 and persist nothing
    17. a display poll with a bogus bearer token returns 401 and never writes battery_state.json
    18. a device_config.json with led_enabled:false yields a 200 display response with led_enabled:false
    19. a device_config.json with a hostile string led_enabled yields a 200 display response with led_enabled:true
    20. a truncated/invalid device_config.json still yields a 200 display response with led_enabled:true
        and passes validate_display_response()
    21. a device_config.json with a currently-active quiet-hours window yields sleep_s in (300, 7200]
    22. a hostile device_config.json still yields sleep_s exactly equal to the base --sleep (300)
    23. a device_config.json with wake_interval_s:120 yields sleep_s exactly 120
    24. a device_config.json with a below-floor wake_interval_s:30 yields sleep_s exactly 300
    25. with display off and quiet hours active for a window ~1h from ending, sleep_s is strictly
        greater than 300 (the composition-order negative control)
    26. with poll_state.json's battery_critical_active latched True, a poll carrying X-Battery-Mv:3290
        returns sleep_s exactly 3600 (the parked pin)
    27. with the same latch, a poll carrying a recovering X-Battery-Mv:4100 returns the base sleep_s
        (300), not the stale parked pin
    28. a poll against a stopped server is classified as a failed wake, not a crash
    """
    tmpdir = str(tmp_path)
    harness = Harness(tmpdir)
    try:
        harness.generate_panel("palette")
        harness.start_server(sleep_s=300)

        # 1. Setup: POST /device/v1/setup returns 200 + a 64-lowercase-hex device_token.
        status, _, body = http_request(
            harness.base_url() + "/device/v1/setup", method="POST",
            json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "poll-cycle-harness",
                       "provision_secret": HARNESS_ENROL_SECRET})
        assert status == 200, "expected 200, got %d (%r)" % (status, body[:200])
        obj = json.loads(body.decode())
        token = obj.get("device_token")
        assert isinstance(token, str) and len(token) == 64 and \
            all(c in "0123456789abcdef" for c in token), (
                "device_token not 64 lowercase hex chars: %r" % (token,))

        # 2. Setup rejects a malformed body (no mac key) with 422.
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/setup", method="POST",
            json_body={"hw_rev": "poll-cycle-harness"})
        assert status == 422, "expected 422 for a body missing mac, got %d" % status

        # 3. Auth gate: no Authorization header -> 401.
        status, _, _ = http_request(harness.base_url() + "/device/v1/display", method="GET")
        assert status == 401, "expected 401 with no Authorization header, got %d" % status

        # 4. Auth gate: a bearer that was never issued -> 401.
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer " + "0" * 64})
        assert status == 401, "expected 401 with an unissued bearer, got %d" % status

        # 5. Display shape: 200 + image_hash/sleep_s/reset/image_url/firmware:null.
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token})
        assert status == 200, "expected 200, got %d" % status
        obj = json.loads(body.decode())
        assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
        assert obj.get("firmware") is None, "expected firmware:null in Phase 1, got %r" % (obj.get("firmware"),)
        assert obj.get("led_enabled") is True, "expected led_enabled:true, got %r" % (obj.get("led_enabled"),)
        image_hash_full = obj["image_hash"]
        image_url = obj["image_url"]

        # 6. Download: the image URL yields exactly 960000 bytes matching the hash.
        status, _, buf = http_request(image_url, method="GET")
        assert status == 200, "download status %d" % status
        assert verify_panel_bytes(buf, image_hash_full), (
            "downloaded buffer failed verify_panel_bytes (len=%d)" % len(buf))
        image_bytes = buf

        # 7. Integrity gate: a flipped byte is rejected by verify_panel_bytes.
        tampered = bytearray(image_bytes)
        tampered[0] ^= 0xFF
        assert not verify_panel_bytes(bytes(tampered), image_hash_full), (
            "verify_panel_bytes accepted a buffer with one flipped byte")
        assert verify_panel_bytes(image_bytes, image_hash_full), (
            "the untampered original unexpectedly failed verification")

        # 8. Size gate: a one-byte truncation is rejected by verify_panel_bytes.
        truncated = image_bytes[:-1]
        assert not verify_panel_bytes(truncated, image_hash_full), (
            "verify_panel_bytes accepted a one-byte-truncated buffer")

        # 9. Hash-skip: a second poll returns the same image_hash; the
        # simulated client skips the download entirely (no download call
        # is made below).
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token})
        assert status == 200, "expected 200 on the second poll, got %d" % status
        obj = json.loads(body.decode())
        assert validate_display_response(obj), "second poll response failed validation: %r" % (obj,)
        assert obj["image_hash"] == image_hash_full, (
            "image_hash changed on an unchanged served image: %r vs %r" % (obj["image_hash"], image_hash_full))

        # 10. Image change: replacing the served file changes image_hash
        # on the next poll, and the simulated client downloads again.
        quadrants_path = harness.generate_panel(
            "quadrants", out_path=os.path.join(harness.tmpdir, "panel_quadrants.bin"))
        shutil.copyfile(quadrants_path, harness.image_path)
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token})
        assert status == 200, "expected 200 after swapping the served image, got %d" % status
        obj = json.loads(body.decode())
        assert validate_display_response(obj), "post-swap response failed validation: %r" % (obj,)
        assert obj["image_hash"] != image_hash_full, "image_hash did not change after the served image was replaced"
        dstatus, _, dbuf = http_request(obj["image_url"], method="GET")
        assert dstatus == 200, "re-download after image change returned status %d" % dstatus
        assert verify_panel_bytes(dbuf, obj["image_hash"]), (
            "re-downloaded buffer failed verify_panel_bytes after image change")
        image_hash_full = obj["image_hash"]

        # 11. Telemetry: a poll carrying battery/RSSI/firmware/boot-reason
        # headers still returns 200, and the server echoes those values
        # to stdout.
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={
                "Authorization": "Bearer %s" % token,
                "X-Battery-Mv": "3941",
                "X-Rssi": "-61",
                "X-Fw-Version": "0.1.0-poll-cycle",
                "X-Boot-Reason": "rtc",
            })
        assert status == 200, "expected 200 on a telemetry-carrying poll, got %d" % status
        time.sleep(0.3)  # let the child's line-buffered stdout flush
        log_text = harness.read_stdout()
        for needle in ("3941", "-61", "0.1.0-poll-cycle", "rtc"):
            assert needle in log_text, "telemetry value %r not found in server stdout" % needle

        # 12. Log endpoint: POST /device/v1/log with a logs array returns 200, ok:true.
        status, _, body = http_request(
            harness.base_url() + "/device/v1/log", method="POST",
            headers={"Authorization": "Bearer %s" % token},
            json_body={"logs": [{"message": "poll-cycle harness check", "level": "warn"}]})
        assert status == 200, "expected 200, got %d" % status
        obj = json.loads(body.decode())
        assert obj.get("ok") is True, "expected ok:true in the /device/v1/log response, got %r" % (obj,)

        # 13. Scheme default: with the server started at its default (no
        # --image-url-scheme passed), image_url begins with http://.
        assert image_url.startswith("http://"), (
            "expected default image_url to start with http://, got %r" % (image_url,))

        # 14. Scheme flag: a server started with --image-url-scheme https
        # serves an image_url beginning with https://, with the rest of
        # the URL (host, /img/ path, digest) unchanged apart from the
        # scheme - so the flag cannot be satisfied by an unrelated URL
        # rewrite.
        https_state_dir = os.path.join(tmpdir, "https-harness")
        os.makedirs(https_state_dir)
        https_harness = Harness(https_state_dir)
        try:
            https_harness.generate_panel("palette")
            https_harness.start_server(sleep_s=300, image_url_scheme="https")
            status, _, body = http_request(
                https_harness.base_url() + "/device/v1/setup", method="POST",
                json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "poll-cycle-harness",
                       "provision_secret": HARNESS_ENROL_SECRET})
            assert status == 200, "https-scheme setup expected 200, got %d" % status
            https_token = json.loads(body.decode())["device_token"]
            status, _, body = http_request(
                https_harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % https_token})
            assert status == 200, "https-scheme display poll expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "https-scheme response failed validation: %r" % (obj,)
            https_url = obj["image_url"]
            assert https_url.startswith("https://"), (
                "expected image_url to start with https://, got %r" % (https_url,))
            # Compare host (not port - each harness instance binds its own
            # free port by design) and the /img/<digest>.bin path: only
            # the scheme should differ.
            https_parts = urllib.parse.urlsplit(https_url)
            default_parts = urllib.parse.urlsplit(image_url)
            assert https_parts.hostname == default_parts.hostname, (
                "expected identical host, got %r vs %r" % (https_parts.hostname, default_parts.hostname))
            assert https_parts.path == default_parts.path, (
                "expected identical digest path, got %r vs %r" % (https_parts.path, default_parts.path))
        finally:
            https_harness.stop_server()

        # --- X-Battery-Mv validation/persistence (DEVICE-04) ------------

        def _battery_state_path():
            return os.path.join(harness.tmpdir, "battery_state.json")

        def _read_battery_state():
            try:
                with open(_battery_state_path()) as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                return None

        # 15. Happy path: an authenticated poll carrying a plausible
        # X-Battery-Mv still returns 200, and battery_state.json appears
        # with {"battery_mv": <int>, "received_at": <float>}. A second
        # poll with a different value overwrites it.
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3487"})
        assert status == 200, "expected 200 on a battery-carrying poll, got %d" % status
        time.sleep(1.0)  # allow the child process's write to land
        state = _read_battery_state()
        assert isinstance(state, dict) and state.get("battery_mv") == 3487, (
            "battery_state.json after the first poll = %r, expected battery_mv=3487" % (state,))
        assert isinstance(state.get("received_at"), float), (
            "battery_state.json's received_at is %r, expected a float" % (state.get("received_at"),))

        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3402"})
        assert status == 200, "expected 200 on the second battery-carrying poll, got %d" % status
        time.sleep(1.0)
        state2 = _read_battery_state()
        assert isinstance(state2, dict) and state2.get("battery_mv") == 3402, (
            "battery_state.json after the second poll = %r, expected battery_mv=3402 (overwrite)" % (state2,))

        # 16. Hostile and malformed values are ignored, never persisted,
        # never fatal: every one of these returns 200, and after all of
        # them the previously persisted value (3402) is still exactly
        # what it was - no rewrite, no new file, no 5xx, no traceback in
        # the server's stdout.
        hostile_values = [
            "abc", "-1", "3500.5", "  3500  ", "3500; rm -rf /", "99999", "0", "",
            "3" * 400,
            "٣٥٠٠",  # Arabic-Indic "3500"
        ]
        before = _read_battery_state()
        assert isinstance(before, dict) and before.get("battery_mv") == 3402, (
            "setup failure: expected battery_mv=3402 persisted from the happy-path check, got %r" % (before,))
        for raw in hostile_values:
            # http.client's putheader() latin-1-encodes a str header
            # value and raises UnicodeEncodeError for the Arabic-Indic
            # case - not a server-side rejection, a client-side encode
            # error that would never let the hostile poll reach the
            # server at all. Send pre-encoded UTF-8 bytes instead: bytes
            # header values pass through putheader() unmodified, so the
            # server actually receives (and must reject) the raw hostile
            # bytes, exactly as a hostile device would send them.
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": raw.encode("utf-8")})
            assert status == 200, "hostile X-Battery-Mv=%r: expected 200, got %d" % (raw, status)
        time.sleep(0.5)
        log_text = harness.read_stdout()
        assert "Traceback" not in log_text, "server stdout contains a traceback after a hostile-value battery poll"
        after = _read_battery_state()
        assert after == before, "battery_state.json changed after a battery of hostile values: %r -> %r" % (before, after)

        # 17. The write barrier sits behind auth: a poll with a bogus
        # bearer token and a plausible X-Battery-Mv returns 401 and
        # leaves battery_state.json unchanged.
        before = _read_battery_state()
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"Authorization": "Bearer " + "f" * 64, "X-Battery-Mv": "3400"})
        assert status == 401, "expected 401 for a bogus bearer token, got %d" % status
        time.sleep(0.5)
        after = _read_battery_state()
        assert after == before, "battery_state.json changed after an unauthenticated poll: %r -> %r" % (before, after)

        # --- read_led_enabled() checks (Phase 06.2, T-06.2-01/T-06.2-03) --
        # Each writes its own device_config.json fixture directly into
        # harness.tmpdir (the harness already passes --state-dir there),
        # polls /device/v1/display, and removes the fixture afterward so
        # no later check observes it. byos_server.py reads the file
        # per-request, so no server restart is needed.

        def _device_config_fixture_path():
            return os.path.join(harness.tmpdir, "device_config.json")

        # 18. A document whose led_enabled is JSON false yields a 200
        # whose response field is exactly False.
        fixture_path = _device_config_fixture_path()
        with open(fixture_path, "w") as fh:
            json.dump({"led_enabled": False}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert obj.get("led_enabled") is False, "expected led_enabled:false, got %r" % (obj.get("led_enabled"),)
        finally:
            os.remove(fixture_path)

        # 19. A document whose led_enabled is a hostile string yields a
        # 200 whose response field is True.
        with open(fixture_path, "w") as fh:
            json.dump({"led_enabled": "off"}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert obj.get("led_enabled") is True, (
                "expected led_enabled:true (fail-open), got %r" % (obj.get("led_enabled"),))
        finally:
            os.remove(fixture_path)

        # 20. A truncated/invalid JSON document yields a 200 whose
        # response field is True and which still satisfies
        # validate_display_response().
        with open(fixture_path, "w") as fh:
            fh.write("{not valid json")
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            assert obj.get("led_enabled") is True, (
                "expected led_enabled:true (fail-open), got %r" % (obj.get("led_enabled"),))
        finally:
            os.remove(fixture_path)

        # 21. Integration, over real HTTP: a device_config.json whose
        # window is guaranteed active right now must extend sleep_s past
        # the harness's own base --sleep value.
        now_paris = datetime.now(ZoneInfo("Europe/Paris"))
        start_hm = (now_paris - timedelta(hours=1)).strftime("%H:%M")
        end_hm = (now_paris + timedelta(hours=1)).strftime("%H:%M")
        with open(fixture_path, "w") as fh:
            json.dump({"quiet_hours_enabled": True, "quiet_hours_start": start_hm,
                       "quiet_hours_end": end_hm}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            sleep_s = obj.get("sleep_s")
            assert 300 < sleep_s <= 7200, "expected sleep_s in (300, 7200], got %r" % (sleep_s,)
        finally:
            os.remove(fixture_path)

        # 22. Integration, hostile config: a corrupted quiet-hours
        # document must never take down the always-on /display handler -
        # sleep_s degrades to exactly the unchanged base value.
        with open(fixture_path, "w") as fh:
            json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "'; DROP",
                       "quiet_hours_end": None}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert obj.get("sleep_s") == 300, "expected sleep_s exactly 300 (fail-open), got %r" % (obj.get("sleep_s"),)
        finally:
            os.remove(fixture_path)

        # 23. Integration, over real HTTP: a device_config.json with an
        # in-range wake_interval_s is delivered as sleep_s, not the
        # harness's base.
        with open(fixture_path, "w") as fh:
            json.dump({"wake_interval_s": 120}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            assert obj.get("sleep_s") == 120, "expected sleep_s exactly 120, got %r" % (obj.get("sleep_s"),)
        finally:
            os.remove(fixture_path)

        # 24. Integration, negative twin: a below-floor stored value
        # never reaches the wire - it degrades to the fail-open CLI
        # default.
        with open(fixture_path, "w") as fh:
            json.dump({"wake_interval_s": 30}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            assert obj.get("sleep_s") == 300, (
                "expected sleep_s exactly 300 (fail-open default), got %r" % (obj.get("sleep_s"),))
        finally:
            os.remove(fixture_path)

        # 25. Integration, over real HTTP: the display-off/quiet-hours
        # overlap (D-05, sleep axis), exercised through the actual
        # do_GET /device/v1/display response construction rather than a
        # direct function call - sensitive to the composition ORDER as
        # wired inside byos_server.py's inlined sleep_s expression. With
        # display_enabled false and an enabled quiet-hours window still
        # far from ending (~1h remaining, well above the 300s off-state
        # pin), the served sleep_s must reflect the remaining window
        # time, NOT collapse to the flat 300s pin.
        now_paris = datetime.now(ZoneInfo("Europe/Paris"))
        start_hm = (now_paris - timedelta(hours=1)).strftime("%H:%M")
        end_hm = (now_paris + timedelta(hours=1)).strftime("%H:%M")
        with open(fixture_path, "w") as fh:
            json.dump({"display_enabled": False, "quiet_hours_enabled": True,
                       "quiet_hours_start": start_hm, "quiet_hours_end": end_hm}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            sleep_s = obj.get("sleep_s")
            assert 300 < sleep_s <= 7200, (
                "expected sleep_s in (300, 7200] (the remaining window time, not the flat 300s "
                "off-state pin), got %r - display_off_sleep_s() may be nested outside "
                "quiet_hours_sleep_s() instead of inside it" % (sleep_s,))
        finally:
            os.remove(fixture_path)

        # 26. Integration, live HTTP: with poll_state.json's
        # battery_critical_active latched True in the harness's own
        # --state-dir, a GET /device/v1/display carrying a
        # still-critical X-Battery-Mv reading (3290, below
        # BATTERY_CRITICAL_RECOVER_MV) returns sleep_s exactly 3600 -
        # the parked pin, over the real do_GET response construction.
        poll_state_path = os.path.join(harness.tmpdir, "poll_state.json")
        with open(poll_state_path, "w") as fh:
            json.dump({"battery_critical_active": True}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3290"})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            assert obj.get("sleep_s") == 3600, "expected sleep_s exactly 3600 while parked, got %r" % (obj.get("sleep_s"),)
        finally:
            os.remove(poll_state_path)

        # 27. Integration, live HTTP, the recovery-anticipation twin: the
        # SAME latched-True poll_state.json, but this poll's own
        # X-Battery-Mv reports recovery (4100, at or above
        # BATTERY_CRITICAL_RECOVER_MV) - the response must NOT hand out
        # the stale 3600s pin; sleep_s falls back to the harness's base
        # --sleep value (300) instead.
        with open(poll_state_path, "w") as fh:
            json.dump({"battery_critical_active": True}, fh)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "4100"})
            assert status == 200, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            assert validate_display_response(obj), "response failed validate_display_response: %r" % (obj,)
            assert obj.get("sleep_s") == 300, (
                "expected sleep_s exactly 300 (the base value, recovery anticipated) with a "
                "recovering X-Battery-Mv:4100, got %r" % (obj.get("sleep_s"),)
            )
        finally:
            os.remove(poll_state_path)

        # 28. Failure classification: with the server stopped, a display
        # poll raises a connection error that the harness classifies as
        # a failed wake rather than crashing.
        harness.stop_server()
        try:
            http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token},
                timeout=3)
            raise AssertionError("expected a connection error against a stopped server, request succeeded instead")
        except (urllib.error.URLError, ConnectionError, OSError):
            pass  # classified as a failed wake, not a crash

    finally:
        harness.stop_server()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
