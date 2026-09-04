#!/usr/bin/env python3
"""End-to-end poll-cycle contract harness for stub-server/byos_server.py.

Stdlib-only (urllib.request, hashlib, json, subprocess, socket, time, os,
sys, tempfile, shutil, importlib.util, datetime, zoneinfo - nothing
else). Generates a deterministic panel image with make_test_panel.py,
launches byos_server.py as a subprocess on a free local port, and
drives it through the full device-protocol contract documented in
flightportrait/frame's docs/PROTOCOL.md at the pinned commit
ce3335fc5e566bcc6ccd29966ec39bf5c5318f12 (sections 1, 2, 3 and 5):
setup, the bearer-token auth gate, the display-response shape,
download + SHA-256 + exact-size verification, the hash-skip
optimisation, a served-image change, telemetry header echoing, the log
endpoint, two hand-built malformed-response rejections, connection
failure classification when the server is down, and (Phase 10, D-01)
the quiet-hours-aware sleep_s extension: a drift guard pinning
byos_server.py's vendored seconds_until_quiet_hours_end()/_HHMM_RE
byte-for-byte equal to server/device_config.py's, unit coverage of
read_quiet_hours()/quiet_hours_sleep_s() loaded directly via
importlib.util (byos_server.py's module level is import-safe - constants
and defs only, with main() behind an `if __name__ == "__main__"` guard),
and integration coverage of the sleep_s extension and its fail-open
contract over real HTTP. Phase 11 (D-01/D-03) adds unit coverage of
read_wake_interval_s()'s fail-open contract (including the
bool-is-an-int gotcha) and happy path, unit coverage of the configured
wake interval layering under quiet_hours_sleep_s() without being
re-clamped past WAKE_INTERVAL_MAX_S, and integration coverage of the
configured value (and a below-floor rejection) reaching sleep_s over
real HTTP.

Exits 0 only when every check below passes; any failure (or exception -
none is ever swallowed into a pass) exits 1.

Usage:
    python3 stub-server/test_poll_cycle.py
"""
import hashlib
import importlib.util
import json
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
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SERVER_PATH = os.path.join(HERE, "byos_server.py")
MAKE_PANEL_PATH = os.path.join(HERE, "make_test_panel.py")
DEVICE_CONFIG_MODULE_PATH = os.path.join(REPO_ROOT, "server", "device_config.py")
IMAGE_BYTES = 960000
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 34


def verify_panel_bytes(buf, expected_hash):
    """Mirror the firmware verification rule (PROTOCOL.md section 2):

    a buffer reaches the panel only when its length is exactly 960000
    bytes AND its SHA-256 hex digest equals the hex portion of the
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
    """Owns the fixture lifecycle: temp dir, free port, generated panel
    image, and the byos_server.py subprocess. Never leaves an orphaned
    server holding the port - callers must run stop_server() in a
    finally block.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-")
        self.port = self._pick_free_port()
        self.image_path = os.path.join(self.tmpdir, "panel.bin")
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
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
            check=True, capture_output=True, text=True,
        )
        return out_path

    def start_server(self, sleep_s=300, image_url_scheme=None):
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
                stdout=stdout_fh, stderr=subprocess.STDOUT,
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

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def main():
    harness = Harness()
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

    try:
        # Ordering note: this harness is written and run now, before
        # byos_server.py or make_test_panel.py exist. It must fail - Task 2
        # turns it green.
        for required_path, label in (
            (MAKE_PANEL_PATH, "stub-server/make_test_panel.py"),
            (SERVER_PATH, "stub-server/byos_server.py"),
        ):
            if not os.path.exists(required_path):
                print("FAIL harness setup - missing %s" % label)
                print("poll-cycle: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
                return 1

        ctx = {}
        ctx["byos_module"] = load_byos_module()

        # --- Task 2 (Phase 10, D-01): quiet-hours-aware sleep_s extension ---

        # A. Drift guard (10-RESEARCH.md Pitfall 1): byos_server.py's
        # vendored seconds_until_quiet_hours_end() and _HHMM_RE must stay
        # byte-for-byte identical to server/device_config.py's. Both
        # files are read as plain text - never imported - so this guard
        # cannot itself breach the boundary it protects.
        def _quiet_hours_drift_guard():
            try:
                with open(DEVICE_CONFIG_MODULE_PATH) as fh:
                    origin_text = fh.read()
            except OSError as exc:
                return False, "could not read %s: %r" % (DEVICE_CONFIG_MODULE_PATH, exc)
            with open(SERVER_PATH) as fh:
                vendored_text = fh.read()

            origin_fn = _extract_def_block(origin_text, "def seconds_until_quiet_hours_end(")
            vendored_fn = _extract_def_block(vendored_text, "def seconds_until_quiet_hours_end(")
            if origin_fn is None:
                return False, "could not locate seconds_until_quiet_hours_end() in server/device_config.py"
            if vendored_fn is None:
                return False, "could not locate seconds_until_quiet_hours_end() in stub-server/byos_server.py"
            if origin_fn != vendored_fn:
                return False, (
                    "seconds_until_quiet_hours_end() has drifted between "
                    "server/device_config.py and stub-server/byos_server.py - "
                    "the two copies must stay byte-for-byte identical:\n"
                    "--- server/device_config.py ---\n%s\n"
                    "--- stub-server/byos_server.py ---\n%s" % (origin_fn, vendored_fn)
                )

            origin_re = _extract_line(origin_text, "_HHMM_RE = re.compile(")
            vendored_re = _extract_line(vendored_text, "_HHMM_RE = re.compile(")
            if origin_re is None or vendored_re is None:
                return False, "could not locate '_HHMM_RE = re.compile(' in one of the two files"
            if origin_re != vendored_re:
                return False, (
                    "_HHMM_RE has drifted between server/device_config.py and "
                    "stub-server/byos_server.py:\n%r\nvs\n%r" % (origin_re, vendored_re)
                )
            return True, ""
        check(
            "seconds_until_quiet_hours_end() and _HHMM_RE are byte-for-byte identical between "
            "server/device_config.py and stub-server/byos_server.py",
            _quiet_hours_drift_guard,
        )

        # B. Unit, fail-open: read_quiet_hours() returns None for every
        # failure mode, never raises.
        def _quiet_hours_fail_open_never_raises():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-qh-failopen-")
            try:
                if module.read_quiet_hours(tmpdir) is not None:
                    return False, "expected None for a missing device_config.json"
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
                    result = module.read_quiet_hours(tmpdir)
                    if result is not None:
                        return False, "expected None for %s, got %r" % (label, result)
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "read_quiet_hours() returns None and never raises for a missing, truncated, non-dict, "
            "disabled, or badly-shaped device_config.json",
            _quiet_hours_fail_open_never_raises,
        )

        # C. Unit, sleep extension: quiet_hours_sleep_s() extends the base
        # sleep inside the window and returns it unchanged past the end.
        def _quiet_hours_sleep_extension():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-qh-extend-")
            try:
                cfg_path = os.path.join(tmpdir, "device_config.json")
                with open(cfg_path, "w") as fh:
                    json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                               "quiet_hours_end": "07:00"}, fh)
                inside = module.quiet_hours_sleep_s(
                    300, tmpdir, now=datetime.fromtimestamp(1700000000.0, timezone.utc))
                if inside != 28000:
                    return False, "expected 28000 inside the window, got %r" % (inside,)
                past_end = module.quiet_hours_sleep_s(
                    300, tmpdir, now=datetime.fromtimestamp(1700028800.0, timezone.utc))
                if past_end != 300:
                    return False, "expected 300 past the window's end, got %r" % (past_end,)
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "quiet_hours_sleep_s() returns 28000 inside an enabled 23:00-07:00 window and the "
            "unchanged base 300 once the window has ended",
            _quiet_hours_sleep_extension,
        )

        # D. Unit, never shorter than the base (D-01's Claude's-Discretion
        # edge case): a base sleep already past the window's end wins.
        def _quiet_hours_never_shorter_than_base():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-qh-neverbelow-")
            try:
                cfg_path = os.path.join(tmpdir, "device_config.json")
                with open(cfg_path, "w") as fh:
                    json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "23:00",
                               "quiet_hours_end": "07:00"}, fh)
                result = module.quiet_hours_sleep_s(
                    86400, tmpdir, now=datetime.fromtimestamp(1700000000.0, timezone.utc))
                if result != 86400:
                    return False, "expected max(86400, 28000) == 86400, got %r" % (result,)
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "quiet_hours_sleep_s() never returns less than the base sleep, even when the base "
            "already carries the device past the window's end",
            _quiet_hours_never_shorter_than_base,
        )

        # --- Task 2 (Phase 11, D-01/D-03): wake_interval_s delivery ------

        # G. Unit, fail-open: read_wake_interval_s() returns the caller's
        # default for every failure mode, never raises. Modelled on
        # _quiet_hours_fail_open_never_raises() above. The JSON-`true` case
        # is the regression guard for the bool-is-an-int gotcha
        # (isinstance(True, int) is True in Python).
        def _wake_interval_fail_open_never_raises():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-wi-failopen-")
            try:
                if module.read_wake_interval_s(tmpdir, 300) != 300:
                    return False, "expected 300 for a missing device_config.json"
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
                    result = module.read_wake_interval_s(tmpdir, 300)
                    if result != 300:
                        return False, "expected 300 (default) for %s, got %r" % (label, result)
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "read_wake_interval_s() returns the caller's default and never raises for a missing, "
            "truncated, non-dict, key-absent, bool (true), string, float, or out-of-range "
            "device_config.json",
            _wake_interval_fail_open_never_raises,
        )

        # H. Unit, happy path: an in-range int (including the two inclusive
        # bounds) is returned unchanged.
        def _wake_interval_happy_path():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-wi-happy-")
            try:
                cfg_path = os.path.join(tmpdir, "device_config.json")
                for stored, expected in ((120, 120), (60, 60), (3600, 3600)):
                    with open(cfg_path, "w") as fh:
                        json.dump({"wake_interval_s": stored}, fh)
                    result = module.read_wake_interval_s(tmpdir, 300)
                    if result != expected:
                        return False, "expected %r for stored wake_interval_s=%r, got %r" % (
                            expected, stored, result)
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "read_wake_interval_s() returns 120 for a stored 120 and returns the inclusive bounds "
            "60 and 3600 unchanged",
            _wake_interval_happy_path,
        )

        # I. Unit, layering: the configured wake interval wins over the CLI
        # default as quiet_hours_sleep_s()'s base, and an active quiet-hours
        # window still extends the result past WAKE_INTERVAL_MAX_S (3600) -
        # the delivered value is deliberately not re-clamped
        # (11-RESEARCH.md Pitfall 4).
        def _wake_interval_layers_under_quiet_hours():
            module = ctx["byos_module"]
            tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-wi-layer-")
            try:
                cfg_path = os.path.join(tmpdir, "device_config.json")
                with open(cfg_path, "w") as fh:
                    json.dump({"wake_interval_s": 120}, fh)
                disabled = module.quiet_hours_sleep_s(
                    module.read_wake_interval_s(tmpdir, 300), tmpdir)
                if disabled != 120:
                    return False, "expected the configured 120 with quiet hours disabled, got %r" % (disabled,)
                with open(cfg_path, "w") as fh:
                    json.dump({"wake_interval_s": 120, "quiet_hours_enabled": True,
                               "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}, fh)
                inside_window = module.quiet_hours_sleep_s(
                    module.read_wake_interval_s(tmpdir, 300), tmpdir,
                    now=datetime.fromtimestamp(1700000000.0, timezone.utc))
                if inside_window != 28000:
                    return False, "expected 28000 inside the window, got %r" % (inside_window,)
                if not (inside_window > module.WAKE_INTERVAL_MAX_S):
                    return False, (
                        "expected the delivered sleep_s (%r) to exceed WAKE_INTERVAL_MAX_S (%r) "
                        "during an active quiet-hours window - re-clamping here would strand the "
                        "device waking hourly through the window" % (inside_window, module.WAKE_INTERVAL_MAX_S))
                return True, ""
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        check(
            "quiet_hours_sleep_s(read_wake_interval_s(...), ...) uses the configured 120 as its "
            "base with quiet hours disabled, and still returns 28000 (> 3600) inside an active "
            "quiet-hours window - the delivered value is deliberately not re-clamped",
            _wake_interval_layers_under_quiet_hours,
        )

        harness.generate_panel("palette")
        harness.start_server(sleep_s=300)

        # 1. Setup: POST /device/v1/setup returns 200 + a 64-lowercase-hex device_token.
        def _setup_ok():
            status, _, body = http_request(
                harness.base_url() + "/device/v1/setup", method="POST",
                json_body={"mac": "aa:bb:cc:dd:ee:01", "hw_rev": "poll-cycle-harness"})
            if status != 200:
                return False, "expected 200, got %d (%r)" % (status, body[:200])
            obj = json.loads(body.decode())
            token = obj.get("device_token")
            if not isinstance(token, str) or len(token) != 64 or \
                    any(c not in "0123456789abcdef" for c in token):
                return False, "device_token not 64 lowercase hex chars: %r" % (token,)
            ctx["token"] = token
            return True, ""
        check("setup issues a 64-lowercase-hex device_token", _setup_ok)

        # 2. Setup rejects a malformed body (no mac key) with 422.
        def _setup_missing_mac():
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/setup", method="POST",
                json_body={"hw_rev": "poll-cycle-harness"})
            if status != 422:
                return False, "expected 422 for a body missing mac, got %d" % status
            return True, ""
        check("setup rejects a body missing mac with 422", _setup_missing_mac)

        # 3. Auth gate: no Authorization header -> 401.
        def _auth_missing_header():
            status, _, _ = http_request(harness.base_url() + "/device/v1/display", method="GET")
            if status != 401:
                return False, "expected 401 with no Authorization header, got %d" % status
            return True, ""
        check("display poll with no Authorization header returns 401", _auth_missing_header)

        # 4. Auth gate: a bearer that was never issued -> 401.
        def _auth_unknown_bearer():
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer " + "0" * 64})
            if status != 401:
                return False, "expected 401 with an unissued bearer, got %d" % status
            return True, ""
        check("display poll with an unissued bearer returns 401", _auth_unknown_bearer)

        # 5. Display shape: 200 + image_hash/sleep_s/reset/image_url/firmware:null.
        def _display_shape():
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % ctx["token"]})
            if status != 200:
                return False, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            if not validate_display_response(obj):
                return False, "response failed validate_display_response: %r" % (obj,)
            if obj.get("firmware") is not None:
                return False, "expected firmware:null in Phase 1, got %r" % (obj.get("firmware"),)
            if obj.get("led_enabled") is not True:
                return False, "expected led_enabled:true, got %r" % (obj.get("led_enabled"),)
            ctx["image_hash_full"] = obj["image_hash"]
            ctx["image_url"] = obj["image_url"]
            return True, ""
        check("display poll returns a valid response shape (incl. firmware:null and led_enabled:true)", _display_shape)

        # 6. Download: the image URL yields exactly 960000 bytes matching the hash.
        def _download():
            image_url = ctx.get("image_url")
            if not image_url:
                return False, "no image_url captured from the display poll"
            status, _, buf = http_request(image_url, method="GET")
            if status != 200:
                return False, "download status %d" % status
            if not verify_panel_bytes(buf, ctx.get("image_hash_full")):
                return False, "downloaded buffer failed verify_panel_bytes (len=%d)" % len(buf)
            ctx["image_bytes"] = buf
            return True, ""
        check("download yields exactly 960000 bytes matching image_hash", _download)

        # 7. Integrity gate: a flipped byte is rejected by verify_panel_bytes.
        def _integrity_gate():
            buf = ctx.get("image_bytes")
            expected_hash = ctx.get("image_hash_full")
            if buf is None:
                return False, "no downloaded buffer available from the previous check"
            tampered = bytearray(buf)
            tampered[0] ^= 0xFF
            if verify_panel_bytes(bytes(tampered), expected_hash):
                return False, "verify_panel_bytes accepted a buffer with one flipped byte"
            if not verify_panel_bytes(buf, expected_hash):
                return False, "the untampered original unexpectedly failed verification"
            return True, ""
        check("verify_panel_bytes rejects a flipped byte", _integrity_gate)

        # 8. Size gate: a one-byte truncation is rejected by verify_panel_bytes.
        def _size_gate():
            buf = ctx.get("image_bytes")
            expected_hash = ctx.get("image_hash_full")
            if buf is None:
                return False, "no downloaded buffer available from the previous check"
            truncated = buf[:-1]
            if verify_panel_bytes(truncated, expected_hash):
                return False, "verify_panel_bytes accepted a one-byte-truncated buffer"
            return True, ""
        check("verify_panel_bytes rejects a one-byte truncation", _size_gate)

        # 9. Hash-skip: a second poll returns the same image_hash; the simulated
        #    client skips the download entirely (no download call is made below).
        def _hash_skip():
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % ctx["token"]})
            if status != 200:
                return False, "expected 200 on the second poll, got %d" % status
            obj = json.loads(body.decode())
            if not validate_display_response(obj):
                return False, "second poll response failed validation: %r" % (obj,)
            if obj["image_hash"] != ctx.get("image_hash_full"):
                return False, "image_hash changed on an unchanged served image: %r vs %r" % (
                    obj["image_hash"], ctx.get("image_hash_full"))
            return True, ""
        check("a second poll of an unchanged image returns the same image_hash (hash-skip)", _hash_skip)

        # 10. Image change: replacing the served file changes image_hash on the
        #     next poll, and the simulated client downloads again.
        def _image_change():
            quadrants_path = harness.generate_panel(
                "quadrants", out_path=os.path.join(harness.tmpdir, "panel_quadrants.bin"))
            shutil.copyfile(quadrants_path, harness.image_path)
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % ctx["token"]})
            if status != 200:
                return False, "expected 200 after swapping the served image, got %d" % status
            obj = json.loads(body.decode())
            if not validate_display_response(obj):
                return False, "post-swap response failed validation: %r" % (obj,)
            if obj["image_hash"] == ctx.get("image_hash_full"):
                return False, "image_hash did not change after the served image was replaced"
            dstatus, _, dbuf = http_request(obj["image_url"], method="GET")
            if dstatus != 200:
                return False, "re-download after image change returned status %d" % dstatus
            if not verify_panel_bytes(dbuf, obj["image_hash"]):
                return False, "re-downloaded buffer failed verify_panel_bytes after image change"
            ctx["image_hash_full"] = obj["image_hash"]
            ctx["image_bytes"] = dbuf
            return True, ""
        check("replacing the served image changes image_hash and the client re-downloads", _image_change)

        # 11. Telemetry: a poll carrying battery/RSSI/firmware/boot-reason headers
        #     still returns 200, and the server echoes those values to stdout.
        def _telemetry():
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={
                    "Authorization": "Bearer %s" % ctx["token"],
                    "X-Battery-Mv": "3941",
                    "X-Rssi": "-61",
                    "X-Fw-Version": "0.1.0-poll-cycle",
                    "X-Boot-Reason": "rtc",
                })
            if status != 200:
                return False, "expected 200 on a telemetry-carrying poll, got %d" % status
            time.sleep(0.3)  # let the child's line-buffered stdout flush
            log_text = harness.read_stdout()
            for needle in ("3941", "-61", "0.1.0-poll-cycle", "rtc"):
                if needle not in log_text:
                    return False, "telemetry value %r not found in server stdout" % needle
            return True, ""
        check("telemetry headers are accepted and echoed to server stdout", _telemetry)

        # 12. Log endpoint: POST /device/v1/log with a logs array returns 200, ok:true.
        def _log_endpoint():
            status, _, body = http_request(
                harness.base_url() + "/device/v1/log", method="POST",
                headers={"Authorization": "Bearer %s" % ctx["token"]},
                json_body={"logs": [{"message": "poll-cycle harness check", "level": "warn"}]})
            if status != 200:
                return False, "expected 200, got %d" % status
            obj = json.loads(body.decode())
            if obj.get("ok") is not True:
                return False, "expected ok:true in the /device/v1/log response, got %r" % (obj,)
            return True, ""
        check("log endpoint accepts a logs array and returns ok:true", _log_endpoint)

        # 13. Response validation, negative: sleep_s=0 is rejected.
        def _validator_rejects_zero_sleep():
            bad = {"image_hash": "sha256:" + "a" * 64, "sleep_s": 0, "reset": False,
                   "image_url": "http://example.invalid/img/x.bin"}
            if validate_display_response(bad):
                return False, "validator accepted a hand-built response with sleep_s=0"
            return True, ""
        check("validate_display_response rejects sleep_s=0", _validator_rejects_zero_sleep)

        # 14. Response validation, negative: uppercase hex in image_hash is rejected.
        def _validator_rejects_uppercase_hash():
            bad = {"image_hash": "sha256:" + "A" * 64, "sleep_s": 300, "reset": False,
                   "image_url": "http://example.invalid/img/x.bin"}
            if validate_display_response(bad):
                return False, "validator accepted a hand-built response with uppercase hex in image_hash"
            return True, ""
        check("validate_display_response rejects uppercase hex in image_hash", _validator_rejects_uppercase_hash)

        # 15. Scheme default: with the server started at its default (no
        #     --image-url-scheme passed), image_url begins with http://.
        def _image_url_scheme_default():
            image_url = ctx.get("image_url")
            if not image_url:
                return False, "no image_url captured from the display poll"
            if not image_url.startswith("http://"):
                return False, "expected default image_url to start with " \
                    "http://, got %r" % (image_url,)
            return True, ""
        check("default --image-url-scheme (http) is served in image_url", _image_url_scheme_default)

        # 16. Scheme flag: a server started with --image-url-scheme https
        #     serves an image_url beginning with https://, with the rest
        #     of the URL (host, /img/ path, digest) unchanged apart from
        #     the scheme - so the flag cannot be satisfied by an
        #     unrelated URL rewrite.
        def _image_url_scheme_https():
            https_harness = Harness()
            try:
                https_harness.generate_panel("palette")
                https_harness.start_server(sleep_s=300, image_url_scheme="https")
                status, _, body = http_request(
                    https_harness.base_url() + "/device/v1/setup", method="POST",
                    json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "poll-cycle-harness"})
                if status != 200:
                    return False, "https-scheme setup expected 200, got %d" % status
                token = json.loads(body.decode())["device_token"]
                status, _, body = http_request(
                    https_harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % token})
                if status != 200:
                    return False, "https-scheme display poll expected 200, got %d" % status
                obj = json.loads(body.decode())
                if not validate_display_response(obj):
                    return False, "https-scheme response failed validation: %r" % (obj,)
                https_url = obj["image_url"]
                if not https_url.startswith("https://"):
                    return False, "expected image_url to start with https://, got %r" % (https_url,)
                default_url = ctx.get("image_url")
                if not default_url:
                    return False, "no default-scheme image_url captured to compare against"
                # Compare host (not port - each harness instance binds its
                # own free port by design, see Harness._pick_free_port) and
                # the /img/<digest>.bin path: only the scheme should differ.
                https_parts = urllib.parse.urlsplit(https_url)
                default_parts = urllib.parse.urlsplit(default_url)
                if https_parts.hostname != default_parts.hostname:
                    return False, "expected identical host, got %r vs %r" % (
                        https_parts.hostname, default_parts.hostname)
                if https_parts.path != default_parts.path:
                    return False, "expected identical digest path, got %r vs %r" % (
                        https_parts.path, default_parts.path)
                return True, ""
            finally:
                https_harness.stop_server()
                https_harness.cleanup()
        check("--image-url-scheme https serves image_url with https:// and an unchanged host/path/digest", _image_url_scheme_https)

        # --- Task 2 (05-02, DEVICE-04): X-Battery-Mv validation/persistence ---

        def _battery_state_path():
            return os.path.join(harness.tmpdir, "battery_state.json")

        def _read_battery_state():
            try:
                with open(_battery_state_path()) as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                return None

        # 17. Check A - happy path: an authenticated poll carrying a
        # plausible X-Battery-Mv still returns 200, and battery_state.json
        # appears with {"battery_mv": <int>, "received_at": <float>}. A
        # second poll with a different value overwrites it.
        def _battery_happy_path_persists_and_overwrites():
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % ctx["token"], "X-Battery-Mv": "3487"})
            if status != 200:
                return False, "expected 200 on a battery-carrying poll, got %d" % status
            time.sleep(1.0)  # allow the child process's write to land
            state = _read_battery_state()
            if not isinstance(state, dict) or state.get("battery_mv") != 3487:
                return False, "battery_state.json after the first poll = %r, expected battery_mv=3487" % (state,)
            if not isinstance(state.get("received_at"), float):
                return False, "battery_state.json's received_at is %r, expected a float" % (state.get("received_at"),)

            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % ctx["token"], "X-Battery-Mv": "3402"})
            if status != 200:
                return False, "expected 200 on the second battery-carrying poll, got %d" % status
            time.sleep(1.0)
            state2 = _read_battery_state()
            if not isinstance(state2, dict) or state2.get("battery_mv") != 3402:
                return False, "battery_state.json after the second poll = %r, expected battery_mv=3402 (overwrite)" % (state2,)
            return True, ""
        check(
            "an authenticated poll carrying a plausible X-Battery-Mv persists {battery_mv, received_at} to "
            "battery_state.json, and a second poll with a different value overwrites it",
            _battery_happy_path_persists_and_overwrites,
        )

        # 18. Check B - hostile and malformed values are ignored, never
        # persisted, never fatal: every one of these returns 200, and after
        # all of them the previously persisted value (3402, from Check A) is
        # still exactly what it was - no rewrite, no new file, no 5xx, no
        # traceback in the server's stdout.
        def _battery_hostile_values_never_persisted():
            hostile_values = [
                "abc", "-1", "3500.5", "  3500  ", "3500; rm -rf /", "99999", "0", "",
                "3" * 400,
                "٣٥٠٠",  # Arabic-Indic "3500"
            ]
            before = _read_battery_state()
            if not isinstance(before, dict) or before.get("battery_mv") != 3402:
                return False, "setup failure: expected battery_mv=3402 persisted from Check A, got %r" % (before,)
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
                    headers={"Authorization": "Bearer %s" % ctx["token"], "X-Battery-Mv": raw.encode("utf-8")})
                if status != 200:
                    return False, "hostile X-Battery-Mv=%r: expected 200, got %d" % (raw, status)
            time.sleep(0.5)
            log_text = harness.read_stdout()
            if "Traceback" in log_text:
                return False, "server stdout contains a traceback after a hostile-value battery poll"
            after = _read_battery_state()
            if after != before:
                return False, "battery_state.json changed after a battery of hostile values: %r -> %r" % (before, after)
            return True, ""
        check(
            "10 hostile/malformed X-Battery-Mv values (non-digit, negative, float, whitespace, injection, "
            "out-of-range, the '0' unknown sentinel, empty, oversized, non-ASCII digits) all return 200 and "
            "persist nothing - the previously persisted value survives byte-identical",
            _battery_hostile_values_never_persisted,
        )

        # 19. Check C - the write barrier sits behind auth: a poll with a
        # bogus bearer token and a plausible X-Battery-Mv returns 401 and
        # leaves battery_state.json unchanged (T-05-02-05).
        def _battery_write_barrier_sits_behind_auth():
            before = _read_battery_state()
            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer " + "f" * 64, "X-Battery-Mv": "3400"})
            if status != 401:
                return False, "expected 401 for a bogus bearer token, got %d" % status
            time.sleep(0.5)
            after = _read_battery_state()
            if after != before:
                return False, "battery_state.json changed after an unauthenticated poll: %r -> %r" % (before, after)
            return True, ""
        check(
            "a display poll with a bogus bearer token returns 401 and never writes battery_state.json "
            "(the write barrier sits strictly behind bearer_ok())",
            _battery_write_barrier_sits_behind_auth,
        )

        # 20-22. read_led_enabled() checks (Phase 06.2, T-06.2-01/T-06.2-03).
        # Each writes its own device_config.json fixture directly into
        # harness.tmpdir (the harness already passes --state-dir there),
        # polls /device/v1/display, and removes the fixture in a finally
        # block so no later check observes it. byos_server.py reads the
        # file per-request, so no server restart is needed.

        def _device_config_fixture_path():
            return os.path.join(harness.tmpdir, "device_config.json")

        # 20. A document whose led_enabled is JSON false yields a 200 whose
        # response field is exactly False. This is the ONLY check that
        # exercises the real read path - the pre-existing _display_shape
        # assertion (check 5) passes identically whether the read works or
        # is broken and always falls through to the default
        # (06.2-RESEARCH.md Pitfall 3), so it is not coverage for this
        # feature.
        def _led_enabled_false_from_shared_config():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                json.dump({"led_enabled": False}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if obj.get("led_enabled") is not False:
                    return False, "expected led_enabled:false, got %r" % (obj.get("led_enabled"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a device_config.json with led_enabled:false yields a 200 display response with led_enabled:false",
            _led_enabled_false_from_shared_config,
        )

        # 21. A document whose led_enabled is a hostile string yields a 200
        # whose response field is True.
        def _led_enabled_hostile_string_falls_back_to_true():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                json.dump({"led_enabled": "off"}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if obj.get("led_enabled") is not True:
                    return False, "expected led_enabled:true (fail-open), got %r" % (obj.get("led_enabled"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a device_config.json with a hostile string led_enabled yields a 200 display response with led_enabled:true",
            _led_enabled_hostile_string_falls_back_to_true,
        )

        # 22. A truncated/invalid JSON document yields a 200 whose response
        # field is True and which still satisfies validate_display_response().
        def _led_enabled_malformed_json_falls_back_to_true():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                fh.write("{not valid json")
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if not validate_display_response(obj):
                    return False, "response failed validate_display_response: %r" % (obj,)
                if obj.get("led_enabled") is not True:
                    return False, "expected led_enabled:true (fail-open), got %r" % (obj.get("led_enabled"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a truncated/invalid device_config.json still yields a 200 display response with led_enabled:true and passes validate_display_response()",
            _led_enabled_malformed_json_falls_back_to_true,
        )

        # E. Integration, over real HTTP: a device_config.json whose window
        # is guaranteed active right now must extend sleep_s past the
        # harness's own base --sleep value.
        def _quiet_hours_integration_active_window_extends_sleep():
            fixture_path = _device_config_fixture_path()
            now_paris = datetime.now(ZoneInfo("Europe/Paris"))
            start_hm = (now_paris - timedelta(hours=1)).strftime("%H:%M")
            end_hm = (now_paris + timedelta(hours=1)).strftime("%H:%M")
            with open(fixture_path, "w") as fh:
                json.dump({"quiet_hours_enabled": True, "quiet_hours_start": start_hm,
                           "quiet_hours_end": end_hm}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if not validate_display_response(obj):
                    return False, "response failed validate_display_response: %r" % (obj,)
                sleep_s = obj.get("sleep_s")
                if not (300 < sleep_s <= 7200):
                    return False, "expected sleep_s in (300, 7200], got %r" % (sleep_s,)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a device_config.json with a currently-active quiet-hours window yields a 200 display "
            "response whose sleep_s is strictly greater than the base --sleep (300) and no greater "
            "than 7200",
            _quiet_hours_integration_active_window_extends_sleep,
        )

        # F. Integration, hostile config: a corrupted quiet-hours document
        # must never take down the always-on /display handler - sleep_s
        # degrades to exactly the unchanged base value.
        def _quiet_hours_hostile_config_fails_open():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                json.dump({"quiet_hours_enabled": True, "quiet_hours_start": "'; DROP",
                           "quiet_hours_end": None}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if obj.get("sleep_s") != 300:
                    return False, "expected sleep_s exactly 300 (fail-open), got %r" % (obj.get("sleep_s"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a hostile device_config.json (non-HH:MM quiet_hours_start, null quiet_hours_end) still "
            "yields a 200 display response with sleep_s exactly equal to the base --sleep (300)",
            _quiet_hours_hostile_config_fails_open,
        )

        # G. Integration, over real HTTP against the running harness (which
        # started with --sleep 300): a device_config.json with an in-range
        # wake_interval_s is delivered as sleep_s, not the harness's base.
        def _wake_interval_integration_delivers_configured_value():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                json.dump({"wake_interval_s": 120}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if not validate_display_response(obj):
                    return False, "response failed validate_display_response: %r" % (obj,)
                if obj.get("sleep_s") != 120:
                    return False, "expected sleep_s exactly 120, got %r" % (obj.get("sleep_s"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a device_config.json with wake_interval_s:120 yields a 200 display response with "
            "sleep_s exactly 120 - not the harness's base --sleep (300)",
            _wake_interval_integration_delivers_configured_value,
        )

        # H. Integration, negative twin: a below-floor stored value never
        # reaches the wire - it degrades to the fail-open CLI default.
        def _wake_interval_integration_below_floor_falls_back_to_default():
            fixture_path = _device_config_fixture_path()
            with open(fixture_path, "w") as fh:
                json.dump({"wake_interval_s": 30}, fh)
            try:
                status, _, body = http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx["token"]})
                if status != 200:
                    return False, "expected 200, got %d" % status
                obj = json.loads(body.decode())
                if not validate_display_response(obj):
                    return False, "response failed validate_display_response: %r" % (obj,)
                if obj.get("sleep_s") != 300:
                    return False, "expected sleep_s exactly 300 (fail-open default), got %r" % (obj.get("sleep_s"),)
                return True, ""
            finally:
                if os.path.exists(fixture_path):
                    os.remove(fixture_path)
        check(
            "a device_config.json with a below-floor wake_interval_s:30 yields a 200 display "
            "response with sleep_s exactly 300 (the fail-open CLI default), and still passes "
            "validate_display_response()",
            _wake_interval_integration_below_floor_falls_back_to_default,
        )

        # 25. Failure classification: with the server stopped, a display poll
        #     raises a connection error that the harness classifies as a
        #     failed wake rather than crashing.
        def _failure_classification():
            harness.stop_server()
            try:
                http_request(
                    harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % ctx.get("token", "0" * 64)},
                    timeout=3)
            except (urllib.error.URLError, ConnectionError, OSError) as exc:
                return True, "classified as a failed wake: %r" % (exc,)
            return False, "expected a connection error against a stopped server, request succeeded instead"
        check("a poll against a stopped server is classified as a failed wake, not a crash", _failure_classification)

    finally:
        harness.stop_server()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("poll-cycle: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
