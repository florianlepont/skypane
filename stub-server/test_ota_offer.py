#!/usr/bin/env python3
"""End-to-end contract tests for byos_server.py's OTA offer: the
firmware offer in GET /device/v1/display, and the device report it is
derived from and records into firmware/device_report.json.

Every scenario below drives a real byos_server.py subprocess on
loopback (matching stub-server/test_poll_cycle.py's own Harness shape)
against a tmp_path state dir, calling server/firmware_registry.py
directly to publish and schedule releases the way the companion's
Update page and the CI deploy import eventually will.

Usage:
    python3 stub-server/test_ota_offer.py
"""
import hashlib
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

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# `pytest` invocation; add it explicitly too so this file also runs when
# executed directly (matching stub-server/test_poll_cycle.py's bootstrap).
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from server import firmware_registry, state_store  # noqa: E402 - path bootstrap above must run first
from skypane_test_support import child_env  # noqa: E402

# A fixed MAC/token pair seeded directly into byos_state.json (never
# through the /device/v1/setup handshake, which stub-server/
# test_devices_registry.py already covers), so every test here can call
# /device/v1/display directly with a known bearer token and a known
# device_report.json key.
KNOWN_MAC = "aa:bb:cc:dd:ee:01"
KNOWN_TOKEN = "cd" * 32


def http_request(url, method="GET", headers=None, json_body=None, timeout=10):
    """Minimal stdlib HTTP client. Returns (status, headers_dict, raw_bytes)
    for both success and HTTP-error responses.
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


def raw_http_get(port, path, extra_header_lines=None, read_timeout=5.0):
    """Send a hand-built HTTP/1.1 GET request over a fresh socket and
    return (status_code_or_None, raw_response_bytes). Latin-1 encoding
    (never ASCII, never urllib) so a raw header byte in 0x80-0xFF
    reaches the wire exactly as written - urllib/http.client may reject
    or re-encode it before a high-level request is ever sent.
    """
    sock = socket.create_connection(("127.0.0.1", port), timeout=read_timeout)
    try:
        sock.settimeout(read_timeout)
        lines = ["GET %s HTTP/1.1" % path, "Host: 127.0.0.1"]
        lines += list(extra_header_lines or [])
        lines += ["Connection: close", "", ""]
        sock.sendall("\r\n".join(lines).encode("latin-1"))
        chunks = []
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except socket.timeout:
            pass
        raw = b"".join(chunks)
        status = None
        if raw.startswith(b"HTTP/"):
            parts = raw.split(b" ", 2)
            if len(parts) >= 2:
                try:
                    status = int(parts[1])
                except ValueError:
                    status = None
        return status, raw
    finally:
        sock.close()


def publish_test_release(state_dir, version, image_bytes=None, commit="a" * 40, notes=None):
    """Publish one release through server/firmware_registry.py's own
    publish_release() - never a hand-written registry.json entry - and
    return (sha256, image_bytes). image_bytes defaults to a small
    deterministic buffer derived from `version`, well under
    firmware_registry.MAX_IMAGE_BYTES.
    """
    if image_bytes is None:
        image_bytes = hashlib.sha256(version.encode("ascii")).digest() * 64
    image_path = os.path.join(state_dir, "release-%s.bin" % version.replace(".", "_").replace("-", "_"))
    with open(image_path, "wb") as fh:
        fh.write(image_bytes)
    sha256 = hashlib.sha256(image_bytes).hexdigest()
    manifest = {
        "version": version, "sha256": sha256, "size": len(image_bytes),
        "released_at": "2026-01-01T00:00:00Z", "commit": commit,
        "notes": notes or [],
    }
    firmware_registry.publish_release(state_dir, manifest, image_path)
    return sha256, image_bytes


class Harness:
    """Owns one byos_server.py subprocess: a free port, the caller's
    tmp_path as --state-dir, a generated panel image, and a seeded
    byos_state.json carrying KNOWN_TOKEN for KNOWN_MAC - so tests can
    drive /device/v1/display directly, and separately call
    server/firmware_registry.py's own publish_release()/
    schedule_release()/cancel_schedule() against the same --state-dir.
    Callers must run stop() in a finally block - never leaves an
    orphaned server holding the port.
    """

    def __init__(self, state_dir):
        self.tmpdir = str(state_dir)
        self.port = self._pick_free_port()
        self.image_path = os.path.join(self.tmpdir, "panel.bin")
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
        self.proc = None
        with open(self.image_path, "wb") as fh:
            fh.write(bytes([0x11]) * IMAGE_BYTES)
        with open(os.path.join(self.tmpdir, "byos_state.json"), "w") as fh:
            json.dump({"tokens": {KNOWN_MAC: KNOWN_TOKEN}}, fh)

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

    def auth_headers(self):
        return {"Authorization": "Bearer %s" % KNOWN_TOKEN}

    def start(self, extra_args=None):
        stdout_fh = open(self.stdout_path, "w")
        cmd = [sys.executable, SERVER_PATH,
               "--image", self.image_path,
               "--port", str(self.port),
               "--sleep", "300",
               "--state-dir", self.tmpdir]
        if extra_args:
            cmd += extra_args
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=child_env())
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


# --- The offer in GET /device/v1/display ----------------------------------


def test_offer_present_when_scheduled_version_differs_from_reported(tmp_path):
    """A published fw-v1.1.0 scheduled release is offered to a device
    reporting X-Fw-Version fw-v1.0.0, with the {version, url, sha256,
    size} shape server/firmware_registry.py's compute_offer() defines.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        sha256, image_bytes = publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200, "expected 200, got %d" % status
        offer = json.loads(body.decode()).get("firmware")
        assert offer is not None, "expected a firmware offer, got None"
        assert offer["version"] == "fw-v1.1.0"
        assert offer["sha256"] == "sha256:" + sha256
        assert offer["size"] == len(image_bytes)
        assert offer["url"] == harness.base_url() + "/fw/" + sha256 + ".bin", (
            "unexpected offer url: %r" % (offer["url"],))
    finally:
        harness.stop()


def test_offer_absent_when_reported_version_matches_scheduled(tmp_path):
    """The same schedule offers nothing to a device that already reports
    the scheduled version.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.1.0"})
        assert status == 200, "expected 200, got %d" % status
        assert json.loads(body.decode()).get("firmware") is None, (
            "expected no offer once the device already reports the scheduled version")
    finally:
        harness.stop()


def test_offer_withheld_while_battery_low_active(tmp_path):
    """poll_state.json's battery_low_active latch withholds the offer
    while True, and it resumes once the latch is False.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        state_store.save_poll_state(state_dir, {"battery_low_active": True})
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200
        assert json.loads(body.decode()).get("firmware") is None, (
            "expected no offer while battery_low_active is True")

        state_store.save_poll_state(state_dir, {"battery_low_active": False})
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200
        assert json.loads(body.decode()).get("firmware") is not None, (
            "expected the offer back once battery_low_active cleared")
    finally:
        harness.stop()


def test_offer_present_during_quiet_hours_and_display_off(tmp_path):
    """Quiet hours and display-off still change sleep_s, but never
    withhold the offer.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start(extra_args=["--sleep", "300"])
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"
        with open(os.path.join(state_dir, "device_config.json"), "w") as fh:
            json.dump({
                "quiet_hours_enabled": True, "quiet_hours_start": "00:00",
                "quiet_hours_end": "23:59", "display_enabled": False,
            }, fh)

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200
        obj = json.loads(body.decode())
        assert obj.get("firmware") is not None, (
            "expected the offer to survive an active quiet-hours window and display-off")
        assert obj.get("sleep_s") != 300, (
            "expected sleep_s to change under quiet hours + display-off, got the unchanged base")
    finally:
        harness.stop()


def test_offered_event_recorded_and_schedule_not_cancellable(tmp_path):
    """After a request that returns an offer, device_report.json holds
    an "offered" event for the current schedule id, and
    firmware_registry.cancel_schedule() refuses to cancel it.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"
        schedule_id = firmware_registry.load_registry(state_dir)["schedule"]["id"]

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200
        assert json.loads(body.decode()).get("firmware") is not None

        device_report = firmware_registry.load_device_report(state_dir)
        entry = device_report["devices"].get(KNOWN_MAC)
        assert entry is not None, "expected a device_report.json entry for the known MAC"
        offered = [e for e in entry["events"] if e["kind"] == "offered" and e["schedule_id"] == schedule_id]
        assert len(offered) == 1, "expected exactly one offered event, got %r" % (entry["events"],)

        assert firmware_registry.cancel_schedule(state_dir) == "not_cancellable"
    finally:
        harness.stop()


def test_third_counted_failure_withdraws_offer_in_the_same_response(tmp_path):
    """A device reporting three fail-hash results for the same schedule
    sees the offer withdrawn on the response containing the third
    failure - no fourth offer, even before the poll loop reconciles.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        for attempt in range(3):
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0",
                         "X-Ota-Result": "fail-hash;fw-v1.1.0"})
            assert status == 200
            offer = json.loads(body.decode()).get("firmware")
            if attempt < 2:
                assert offer is not None, "expected an offer before the third failure (attempt %d)" % (attempt + 1)
            else:
                assert offer is None, "expected no offer on the response carrying the third failure"

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0"})
        assert status == 200
        assert json.loads(body.decode()).get("firmware") is None, (
            "expected the offer to stay withdrawn on a plain follow-up poll")
    finally:
        harness.stop()


def test_malformed_ota_headers_are_ignored(tmp_path):
    """An unknown result token, a missing ';', an over-64-byte header,
    and a non-ASCII header are all ignored - no result event is
    recorded and the response is otherwise unaffected. A malformed
    X-Fw-Version is ignored the same way.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        bad_ascii_results = [
            "bogus-token;fw-v1.1.0",          # unknown result token
            "fail-hash-fw-v1.1.0",            # missing ';'
            "fail-download;" + "a" * 60,      # header over 64 bytes
        ]
        for bad in bad_ascii_results:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={**harness.auth_headers(), "X-Fw-Version": "fw-v1.0.0", "X-Ota-Result": bad})
            assert status == 200, "expected 200 for a malformed X-Ota-Result, got %d" % status
            assert json.loads(body.decode()).get("firmware") is not None, (
                "malformed X-Ota-Result %r unexpectedly withheld the offer" % (bad,))

        # Non-ASCII: a raw Latin-1 byte (0xE9) inside the header value,
        # sent over a hand-built socket since urllib/http.client would
        # otherwise reject or re-encode it before it ever reached byos.
        raw_status, _ = raw_http_get(
            harness.port, "/device/v1/display",
            extra_header_lines=[
                "Authorization: Bearer %s" % KNOWN_TOKEN,
                "X-Fw-Version: fw-v1.0.0",
                "X-Ota-Result: fail-hash;caf\xe9",
            ])
        assert raw_status == 200, "expected 200 for a non-ASCII X-Ota-Result, got %r" % (raw_status,)

        device_report = firmware_registry.load_device_report(state_dir)
        entry = device_report["devices"].get(KNOWN_MAC, {})
        result_events = [e for e in entry.get("events", []) if e["kind"] == "result"]
        assert result_events == [], (
            "a malformed X-Ota-Result was recorded as a result event: %r" % (result_events,))

        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={**harness.auth_headers(), "X-Fw-Version": "not valid!"})
        assert status == 200, "expected 200 for a malformed X-Fw-Version, got %d" % status
        assert json.loads(body.decode()).get("firmware") is not None, (
            "a malformed X-Fw-Version unexpectedly withheld the offer")
    finally:
        harness.stop()


def test_unauthenticated_request_records_nothing_and_401(tmp_path):
    """An unauthenticated poll gets the existing 401 and never touches
    device_report.json.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        publish_test_release(state_dir, "fw-v1.1.0")
        assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers={"X-Fw-Version": "fw-v1.0.0", "X-Ota-Result": "fail-hash;fw-v1.1.0"})
        assert status == 401, "expected 401 for an unauthenticated poll, got %d" % status

        device_report = firmware_registry.load_device_report(state_dir)
        assert device_report["devices"] == {}, (
            "expected no device_report.json entries after an unauthenticated poll")
    finally:
        harness.stop()


def test_nothing_written_when_no_header_and_no_offer(tmp_path):
    """A plain authenticated poll, with nothing published or scheduled
    and no OTA headers, writes nothing to device_report.json at all.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", method="GET",
            headers=harness.auth_headers())
        assert status == 200
        assert json.loads(body.decode()).get("firmware") is None
        assert not os.path.exists(firmware_registry.device_report_path(state_dir)), (
            "expected no device_report.json to be created by an ordinary poll")
    finally:
        harness.stop()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
