#!/usr/bin/env python3
"""End-to-end and unit contract tests for byos_server.py's OTA surface:
the firmware offer in GET /device/v1/display, the device report it is
derived from and records into firmware/device_report.json, and the
strict content-addressed GET /fw/<sha256>.bin route.

Every scenario below drives a real byos_server.py subprocess on
loopback (matching stub-server/test_poll_cycle.py's own Harness shape)
against a tmp_path state dir, calling server/firmware_registry.py
directly to publish and schedule releases the way the companion's
Update page and the CI deploy import eventually will. The one exception
is the chunked-streaming proof, a unit test against byos_server.py's
_serve_firmware_image() with a fake handler and no subprocess, since a
bounded-read-size guarantee is not otherwise observable over HTTP.

Usage:
    python3 stub-server/test_ota_offer.py
"""
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from io import BytesIO
from unittest import mock

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


def load_byos_module():
    """Load byos_server.py directly via importlib.util, matching every
    other stub-server test file's own pattern, so _serve_firmware_image()
    can be unit-checked without a subprocess or real sockets.
    """
    spec = importlib.util.spec_from_file_location(
        "byos_server_ota_offer_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


@pytest.fixture(scope="module")
def byos_module():
    return load_byos_module()


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
    The three reports are identical on purpose: an image refused the
    same way on every attempt must still reach the attempt limit, or it
    would be re-offered and re-downloaded on every wake.
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


def test_resolve_device_id_tolerates_concurrent_token_insert(byos_module):
    """_resolve_device_id() iterates state["tokens"] on a
    ThreadingHTTPServer worker while /device/v1/setup can concurrently
    insert into the very same dict (bearer_ok() already guards against
    this the same way). Simulate that insert landing mid-iteration by
    making it a side effect of the first hmac.compare_digest() call --
    deterministic, unlike a real background thread racing the loop --
    and confirm resolution still completes instead of raising
    "dictionary changed size during iteration".
    """
    # The match must not be the first entry compared: the insert below
    # needs the loop to advance to a *second* items() iterator step
    # after the dict has already grown, which is exactly when CPython's
    # dict iterator raises "changed size during iteration" -- a match
    # on the very first entry would return before ever taking that step.
    known_mac = "aa:bb:cc:dd:ee:02"
    tokens = {"aa:bb:cc:dd:ee:01": "other-token", known_mac: "known-token-aaa"}
    state = {"tokens": tokens}
    real_compare_digest = byos_module.hmac.compare_digest
    calls = {"n": 0}

    def racing_compare_digest(a, b):
        calls["n"] += 1
        if calls["n"] == 1:
            tokens["ff:ff:ff:ff:ff:ff"] = "new-token-from-setup"
        return real_compare_digest(a, b)

    with mock.patch.object(byos_module.hmac, "compare_digest", side_effect=racing_compare_digest):
        device_id = byos_module._resolve_device_id(state, "known-token-aaa")
    assert device_id == known_mac


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


def test_cancel_cannot_race_the_offer_decision(byos_module, tmp_path):
    """firmware_registry.cancel_schedule() and byos's own offer decision
    must never observe two different snapshots of the same schedule: a
    cancel that lands between byos's registry read and its "offered"
    write must either (a) complete before that read (so no offer for
    the cancelled schedule is ever computed) or (b) block until after
    the "offered" event is written (so it sees the schedule as already
    started and refuses with "not_cancellable") -- never "cancelled"
    while this same call still serves an offer for that schedule.

    Calls _record_device_report_and_offer() directly (no subprocess),
    the only way to inject a cancel_schedule() call at the exact instant
    between the registry read and the offer write that the real race
    depends on. compute_offer() is patched to signal readiness and give
    a background thread a window to call cancel_schedule() -- a stand-in
    for byos and the companion running in separate processes with no
    shared lock, which real_compute_offer's own I/O-free body cannot
    otherwise be paused inside.
    """
    state_dir = str(tmp_path)
    publish_test_release(state_dir, "fw-v1.1.0")
    assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

    ready = threading.Event()
    cancel_result = {}
    real_compute_offer = firmware_registry.compute_offer

    def slow_compute_offer(*args, **kwargs):
        ready.set()
        time.sleep(0.3)  # a window for the background cancel to run
        return real_compute_offer(*args, **kwargs)

    def do_cancel():
        ready.wait(5)
        cancel_result["value"] = firmware_registry.cancel_schedule(state_dir)

    thread = threading.Thread(target=do_cancel)
    with mock.patch.object(byos_module.firmware_registry, "compute_offer", side_effect=slow_compute_offer):
        thread.start()
        offer = byos_module._record_device_report_and_offer(
            state_dir, {"tokens": {}}, {"X-Fw-Version": "fw-v1.0.0"}, "http", "example.org")
    thread.join(5)
    assert not thread.is_alive(), "cancel_schedule() did not return within the join timeout"

    assert cancel_result["value"] == "not_cancellable", (
        "cancel_schedule() must block on the registry lock byos holds while it decides and "
        "records this offer, then see the just-written 'offered' event and refuse -- got %r "
        "(offer=%r)" % (cancel_result["value"], offer)
    )
    assert offer is not None and offer["version"] == "fw-v1.1.0"
    assert firmware_registry.load_registry(state_dir)["schedule"] is not None, (
        "the schedule must still be present -- cancel_schedule() must not have cleared it"
    )


def test_stale_resent_result_does_not_close_a_different_schedule(byos_module, tmp_path):
    """A device resends its last X-Ota-Result on every poll until a 200
    parses it (firmware/main/api_client.c). If that first 200 is lost,
    the device keeps resending a result for a schedule the operator has
    since replaced. byos must never credit that stale resend to
    whatever schedule happens to be current now -- only to the
    schedule whose version the result actually names.
    """
    state_dir = str(tmp_path)
    publish_test_release(state_dir, "fw-v1.3.0")
    publish_test_release(state_dir, "fw-v1.4.0")
    assert firmware_registry.schedule_release(state_dir, "fw-v1.3.0", running_version=None) == "scheduled"

    # S1 (v1.3.0) installs; byos records it, but (from the device's own
    # point of view) the response never arrives.
    offer1 = byos_module._record_device_report_and_offer(
        state_dir, {"tokens": {}},
        {"X-Fw-Version": "fw-v1.3.0", "X-Ota-Result": "installed;fw-v1.3.0"},
        "http", "example.org")
    assert offer1 is None  # already running the scheduled version

    notifications = firmware_registry.apply_reconcile(state_dir)
    assert [n[0] for n in notifications] == ["installed"]
    assert firmware_registry.load_registry(state_dir)["schedule"] is None

    # The operator schedules v1.4.0 (S2).
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.4.0", running_version="fw-v1.3.0") == "scheduled"

    # The device, still waiting for its own confirmation of the S1
    # install, resends the SAME result on its next wake.
    byos_module._record_device_report_and_offer(
        state_dir, {"tokens": {}},
        {"X-Fw-Version": "fw-v1.3.0", "X-Ota-Result": "installed;fw-v1.3.0"},
        "http", "example.org")

    device_report = firmware_registry.load_device_report(state_dir)
    entry = device_report["devices"]["default"]
    result_events = [e for e in entry["events"] if e["kind"] == "result"]
    stale_event = result_events[-1]
    assert stale_event["version"] == "fw-v1.3.0"
    assert stale_event["schedule_id"] is None, (
        "a resent result for a replaced schedule must not be tagged with the new schedule's id"
    )

    notifications2 = firmware_registry.apply_reconcile(state_dir)
    assert notifications2 == [], "the resent v1.3.0 result must not resolve the v1.4.0 schedule"
    schedule = firmware_registry.load_registry(state_dir)["schedule"]
    assert schedule is not None and schedule["version"] == "fw-v1.4.0", (
        "the new schedule must still be pending -- a stale resend must not close it"
    )


def test_next_seq_stays_monotonic_against_a_reset_device_report(byos_module, tmp_path):
    """A restore whose tarball captured device_report.json just before a
    reconcile and registry.json just after (the two files are read at
    different moments, with no shared lock across a backup/restore) can
    leave device_report.json's own next_seq far behind
    registry["reconciled_seq"]. The next assigned seq must never regress
    below reconciled_seq -- otherwise every new event this call ever
    records is already <= reconciled_seq and reconcile() ignores it
    forever: an offer never counts as an attempt, and an "installed"
    result never closes its schedule.
    """
    state_dir = str(tmp_path)
    publish_test_release(state_dir, "fw-v1.1.0")
    assert firmware_registry.schedule_release(state_dir, "fw-v1.1.0", running_version=None) == "scheduled"

    registry = firmware_registry.load_registry(state_dir)
    registry["reconciled_seq"] = 40
    firmware_registry._save_registry(state_dir, registry)  # noqa: SLF001 - test seeds a restore scenario directly

    # device_report.json is missing/reset (next_seq back to 0), as a
    # fresh document would be after a lossy restore.
    assert not os.path.exists(firmware_registry.device_report_path(state_dir))

    byos_module._record_device_report_and_offer(
        state_dir, {"tokens": {}}, {"X-Fw-Version": "fw-v1.0.0"}, "http", "example.org")

    device_report = firmware_registry.load_device_report(state_dir)
    entry = device_report["devices"]["default"]
    seqs = [e["seq"] for e in entry["events"]]
    assert seqs and min(seqs) > 40, (
        "a new event's seq must be strictly above reconciled_seq, got %r" % (seqs,)
    )
    assert device_report["next_seq"] > 40


# --- GET /fw/<sha256>.bin --------------------------------------------------


def test_fw_route_serves_registered_release_image(tmp_path):
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        sha256, image_bytes = publish_test_release(state_dir, "fw-v1.2.0")

        status, headers, body = http_request(harness.base_url() + "/fw/%s.bin" % sha256, method="GET")
        assert status == 200, "expected 200, got %d" % status
        assert headers.get("Content-Type") == "application/octet-stream"
        assert headers.get("Content-Length") == str(len(image_bytes))
        assert body == image_bytes, "served bytes did not match the published image"
    finally:
        harness.stop()


@pytest.mark.parametrize("bad_path", [
    "/fw/" + "a" * 64 + ".bin",       # well-formed but never published
    "/fw/" + "A" * 64 + ".bin",       # uppercase hex
    "/fw/" + "a" * 63 + ".bin",       # 63 hex chars
    "/fw/" + "a" * 65 + ".bin",       # 65 hex chars
    "/fw/../registry.json",
    "/fw/" + "a" * 64 + ".bin?x=1",   # query string
    "/fw/" + "a" * 64 + ".BIN",       # uppercase extension
])
def test_fw_route_404_for_malformed_or_unregistered_paths(tmp_path, bad_path):
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        status, _ = raw_http_get(harness.port, bad_path)
        assert status == 404, "expected 404 for %r, got %r" % (bad_path, status)
    finally:
        harness.stop()


def test_fw_route_404_when_registered_image_file_is_missing(tmp_path):
    """A sha registered in registry.json whose image file was removed
    out from under it (e.g. a botched manual state-dir edit) is a 404,
    not a 500.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        sha256, _ = publish_test_release(state_dir, "fw-v1.2.0")
        os.remove(firmware_registry.firmware_image_path(state_dir, sha256))

        status, _, _ = http_request(harness.base_url() + "/fw/%s.bin" % sha256, method="GET")
        assert status == 404, "expected 404 for a registered sha with a missing file, got %d" % status
    finally:
        harness.stop()


def test_fw_route_never_serves_a_file_larger_than_max_image_bytes(tmp_path):
    """A registered release whose on-disk file has since grown past
    MAX_IMAGE_BYTES (a corrupted or tampered state dir) is never served.
    """
    state_dir = str(tmp_path)
    harness = Harness(state_dir)
    try:
        harness.start()
        sha256, _ = publish_test_release(state_dir, "fw-v1.2.0")
        oversized_path = firmware_registry.firmware_image_path(state_dir, sha256)
        with open(oversized_path, "wb") as fh:
            fh.write(b"\x00" * (firmware_registry.MAX_IMAGE_BYTES + 1))

        status, _, _ = http_request(harness.base_url() + "/fw/%s.bin" % sha256, method="GET")
        assert status == 404, "expected 404 for an oversized on-disk image, got %d" % status
    finally:
        harness.stop()


def test_serve_firmware_image_streams_in_fixed_size_chunks(byos_module, tmp_path):
    """_serve_firmware_image() never reads the whole release image into
    memory in one call - every open("rb") read against the served file
    requests exactly _FW_STREAM_CHUNK_BYTES bytes, more than once for a
    file larger than one chunk. Proven with a fake handler (no
    subprocess, no real socket) since this is not otherwise observable
    over HTTP.
    """
    state_dir = str(tmp_path)
    image_bytes = os.urandom(3 * byos_module._FW_STREAM_CHUNK_BYTES + 100)
    image_path = os.path.join(state_dir, "release.bin")
    with open(image_path, "wb") as fh:
        fh.write(image_bytes)
    sha256 = hashlib.sha256(image_bytes).hexdigest()
    manifest = {
        "version": "fw-v1.0.0", "sha256": sha256, "size": len(image_bytes),
        "released_at": "2026-01-01T00:00:00Z", "commit": "a" * 40,
    }
    firmware_registry.publish_release(state_dir, manifest, image_path)
    served_path = firmware_registry.firmware_image_path(state_dir, sha256)

    class _FakeHandler:
        def __init__(self):
            self.args = types.SimpleNamespace(state_dir=state_dir)
            self.wfile = BytesIO()
            self.status = None
            self.headers_sent = {}

        def send_response(self, code):
            self.status = code

        def send_header(self, key, value):
            self.headers_sent[key] = value

        def end_headers(self):
            pass

    class _ChunkTrackingFile:
        def __init__(self, real):
            self._real = real
            self.read_sizes = []

        def read(self, size=-1):
            self.read_sizes.append(size)
            return self._real.read(size)

        def close(self):
            self._real.close()

    tracking = {}
    real_open = open

    def _tracking_open(path, mode="r", *args, **kwargs):
        fh = real_open(path, mode, *args, **kwargs)
        if path == served_path and "b" in mode:
            wrapped = _ChunkTrackingFile(fh)
            tracking["file"] = wrapped
            return wrapped
        return fh

    fake = _FakeHandler()
    with mock.patch("builtins.open", side_effect=_tracking_open):
        byos_module.Handler._serve_firmware_image(fake, sha256)

    assert fake.status == 200
    assert fake.headers_sent.get("Content-Length") == str(len(image_bytes))
    assert fake.wfile.getvalue() == image_bytes, "streamed bytes did not match the source image"
    read_sizes = tracking["file"].read_sizes
    assert len(read_sizes) > 1, "expected more than one read() call for a multi-chunk file"
    assert all(size == byos_module._FW_STREAM_CHUNK_BYTES for size in read_sizes), (
        "expected every read() to request exactly _FW_STREAM_CHUNK_BYTES, got %r" % (read_sizes,))

