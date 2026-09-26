#!/usr/bin/env python3
"""Behaviour tests for stub-server/byos_server.py's hardening work:

- `_atomic_write`, byos's local same-directory-mkstemp atomic writer,
  proven to share `server/atomic_io.py`'s observable contract by a test
  parametrised over both callables, plus its three writers (`save_state`,
  `save_registry`, `save_battery_state`).
- Content-addressed `img/<sha256>.bin` publishing, so the device always
  downloads the bytes it was told about.
- Request hardening: bounded/validated `Content-Length`, a socket timeout
  on a stalled client, a constant-time bearer compare, and non-dict
  `/device/v1/log` entries skipped rather than raising.

Every assertion is about observable behaviour (bytes on disk, HTTP status
codes, file mode, presence/absence of a leftover temp file, server stdout) -
never about byos_server.py's source text, per the behaviour-over-source
convention this repo's tests follow throughout.
"""
import hashlib
import importlib.util
import json
import os
import socket
import stat
import subprocess
import sys
import threading
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
# executed directly (matching stub-server/test_poll_cycle.py's own bootstrap).
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from server import atomic_io  # noqa: E402 - path bootstrap above must run first
from skypane_test_support import child_env  # noqa: E402

# A fixed MAC/token pair seeded directly into byos_state.json (never through
# the /device/v1/setup handshake, which stub-server/test_devices_registry.py
# already covers) so tests here can call /device/v1/display and
# /device/v1/log directly with a known bearer token.
KNOWN_MAC = "aa:bb:cc:dd:ee:ff"
KNOWN_TOKEN = "ab" * 32


def load_byos_module():
    """Load byos_server.py directly via importlib.util, matching
    stub-server/test_poll_cycle.py's and test_devices_registry.py's own
    pattern, so its pure functions can be unit-checked without HTTP.
    """
    spec = importlib.util.spec_from_file_location(
        "byos_server_hardening_under_test", SERVER_PATH)
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


def make_panel_bytes(n):
    """A 960000-byte panel image whose every byte is `n` (0-255) - enough
    for byos to hash and serve; not a real PROTOCOL.md panel (that's
    make_test_panel.py's job), which none of this file's tests need.
    """
    return bytes([n & 0xFF]) * IMAGE_BYTES


def _temp_leftovers(directory):
    return [name for name in os.listdir(directory) if name.endswith(".tmp")]


def _raw_request(port, request_line, header_lines, body=b"", read_timeout=5.0):
    """Send a hand-built HTTP/1.1 request over a fresh socket and return
    (status_code_or_None, raw_response_bytes). Used where a malformed
    Content-Length must reach the wire verbatim - urllib/http.client
    validate or normalise a header value before a high-level client
    ever sends it.
    """
    sock = socket.create_connection(("127.0.0.1", port), timeout=read_timeout)
    try:
        sock.settimeout(read_timeout)
        lines = [request_line] + header_lines + ["Connection: close", "", ""]
        sock.sendall("\r\n".join(lines).encode("ascii") + body)
        chunks = []
        try:
            while True:
                chunk = sock.recv(4096)
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


class Harness:
    """Owns one byos_server.py subprocess: a free port, the caller's
    tmp_path as --state-dir, and a seeded byos_state.json carrying
    KNOWN_TOKEN for KNOWN_MAC - so callers can drive /device/v1/display
    and /device/v1/log without the /device/v1/setup handshake. Callers
    must run stop() in a finally block - never leaves an orphaned server
    holding the port.
    """

    def __init__(self, state_dir, image_bytes=None):
        self.tmpdir = str(state_dir)
        self.port = self._pick_free_port()
        self.image_path = os.path.join(self.tmpdir, "panel.bin")
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
        self.proc = None
        with open(self.image_path, "wb") as fh:
            fh.write(image_bytes if image_bytes is not None else make_panel_bytes(0))
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
    """byos_server.py loaded once via importlib.util - a pure module of
    constants and defs, safely reused read-only across every unit test
    below (no test mutates it).
    """
    return load_byos_module()


@pytest.fixture(params=["server.atomic_io.atomic_write", "byos._atomic_write"])
def write_fn(request, byos_module):
    """Parametrises every parity test below over both atomic-write
    implementations, so a single test body proves the same observable
    contract for each.
    """
    if request.param == "server.atomic_io.atomic_write":
        return atomic_io.atomic_write
    return byos_module._atomic_write


# --- _atomic_write parity and byos's three writers ------------------------


def test_atomic_write_parity_str_and_bytes_round_trip(write_fn, tmp_path):
    """Both atomic_write and byos._atomic_write round-trip str (UTF-8-encoded)
    and bytes payloads identically"""
    path = tmp_path / "state.json"
    write_fn(str(path), "hello")
    assert path.read_bytes() == b"hello"

    path2 = tmp_path / "state.bin"
    write_fn(str(path2), b"\x00\x01binary")
    assert path2.read_bytes() == b"\x00\x01binary"

    text_path = tmp_path / "text.json"
    write_fn(str(text_path), "café")
    assert text_path.read_bytes() == "café".encode("utf-8")


def test_atomic_write_parity_default_mode_matches_umask(write_fn, tmp_path):
    """Both implementations default to 0o666 & ~umask, matching open(path, 'w')"""
    old = os.umask(0)
    os.umask(old)
    expected = 0o666 & ~old
    path = tmp_path / "state.json"
    write_fn(str(path), "x")
    assert stat.S_IMODE(path.stat().st_mode) == expected


def test_atomic_write_parity_explicit_mode_gives_0600(write_fn, tmp_path):
    """Both implementations honour an explicit mode=0o600"""
    path = tmp_path / "secret.json"
    write_fn(str(path), "s3cr3t", mode=0o600)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_atomic_write_parity_os_replace_failure_leaves_original_and_no_temp(
        write_fn, tmp_path, monkeypatch):
    """A forced os.replace failure leaves the pre-existing content untouched and no '*.tmp'
    leftover, for both implementations"""
    path = tmp_path / "state.json"
    write_fn(str(path), "original")

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError):
        write_fn(str(path), "new content")

    assert path.read_bytes() == b"original"
    assert _temp_leftovers(str(tmp_path)) == []


def test_atomic_write_parity_concurrent_threads_write_one_complete_payload(write_fn, tmp_path):
    """8 threads x 50 writes to the same path leave exactly one complete payload and no
    leftover temp file, for both implementations - the fixed-name bug this replaces would
    otherwise let two threads collide on the same temp file"""
    path = tmp_path / "shared.bin"
    payloads = {}
    errors = []

    def make_payload(tag, i):
        marker = ("%s-write-%d-" % (tag, i)).encode()
        reps = (65536 // len(marker)) + 1
        return (marker * reps)[:65536]

    def worker(thread_id):
        try:
            for i in range(50):
                payload = make_payload("thread%d" % thread_id, i)
                payloads[(thread_id, i)] = payload
                write_fn(str(path), payload)
        except Exception as exc:  # collected, not swallowed
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    final = path.read_bytes()
    assert final in payloads.values()
    assert _temp_leftovers(str(tmp_path)) == []


def test_save_registry_leaves_devices_json_mode_0600(byos_module, tmp_path):
    """save_registry() leaves devices.json at mode 0600"""
    tmpdir = str(tmp_path)
    registry = {"devices": {KNOWN_MAC: {"secret_sha256": "a" * 64}}}
    byos_module.save_registry(tmpdir, registry)
    path = byos_module.registry_path(tmpdir)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    with open(path) as fh:
        assert json.load(fh) == registry
    assert _temp_leftovers(tmpdir) == []


def test_save_state_and_save_battery_state_leave_no_temp_and_valid_json(byos_module, tmp_path):
    """save_state() and save_battery_state() leave no temp file and valid, round-trippable JSON"""
    tmpdir = str(tmp_path)
    byos_module.save_state(tmpdir, {"tokens": {KNOWN_MAC: KNOWN_TOKEN}})
    byos_module.save_battery_state(tmpdir, 3700)
    assert _temp_leftovers(tmpdir) == []
    with open(byos_module.state_path(tmpdir)) as fh:
        assert json.load(fh) == {"tokens": {KNOWN_MAC: KNOWN_TOKEN}}
    with open(byos_module.battery_state_path(tmpdir)) as fh:
        battery = json.load(fh)
    assert battery["battery_mv"] == 3700
    assert isinstance(battery["received_at"], float)


def test_save_state_concurrent_threads_no_exception(byos_module, tmp_path):
    """Two threads calling save_state() concurrently, 100 times each, raise no exception -
    today both would share byos_state.json.tmp and could collide"""
    tmpdir = str(tmp_path)
    errors = []

    def worker(tag):
        try:
            for i in range(100):
                byos_module.save_state(tmpdir, {"tokens": {tag: "%d" % i}})
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=("t%d" % t,)) for t in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert _temp_leftovers(tmpdir) == []


# --- Content-addressed image download --------------------------------------


def test_display_publishes_image_and_img_endpoint_serves_it_by_hash(tmp_path):
    """GET /device/v1/display advertises image_hash sha256:X; after the served --image
    file is replaced with different bytes, /img/X.bin still returns the bytes whose
    SHA-256 is X (content-addressed, not "whatever's currently on disk"), and the
    following /display advertises the new image under its own hash"""
    image_x = make_panel_bytes(1)
    harness = Harness(tmp_path, image_bytes=image_x)
    try:
        harness.start()
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200, "expected 200, got %d" % status
        obj = json.loads(body.decode())
        digest_x = obj["image_hash"].split(":", 1)[1]
        assert digest_x == hashlib.sha256(image_x).hexdigest()
        image_url_x = obj["image_url"]

        # Replace the served panel with different bytes before downloading -
        # the download must still yield X, not the new on-disk content.
        with open(harness.image_path, "wb") as fh:
            fh.write(make_panel_bytes(2))

        dstatus, _, dbuf = http_request(image_url_x)
        assert dstatus == 200, "expected 200 downloading X, got %d" % dstatus
        assert hashlib.sha256(dbuf).hexdigest() == digest_x
        assert dbuf == image_x

        # The next /display advertises the new image (Y), served at its own hash.
        status2, _, body2 = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status2 == 200
        obj2 = json.loads(body2.decode())
        digest_y = obj2["image_hash"].split(":", 1)[1]
        assert digest_y != digest_x
        dstatus2, _, dbuf2 = http_request(obj2["image_url"])
        assert dstatus2 == 200
        assert hashlib.sha256(dbuf2).hexdigest() == digest_y
    finally:
        harness.stop()


def test_img_endpoint_404_for_unknown_or_malformed_paths(tmp_path):
    """GET /img/<64-hex not published>.bin, /img/../panel.bin, /img/<hex>.BIN,
    /img/<hex>.bin?x=1, /img/<hex> (no extension), /img/ and a 63-hex name all answer
    404 - only the exact published /img/<64 lowercase hex>.bin path is ever served"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200
        digest = json.loads(body.decode())["image_hash"].split(":", 1)[1]
        unknown_hex = "0" * 64 if digest != "0" * 64 else "1" * 64

        bad_paths = [
            "/img/%s.bin" % unknown_hex,
            "/img/../panel.bin",
            "/img/%s.BIN" % digest,
            "/img/%s.bin?x=1" % digest,
            "/img/%s" % digest,
            "/img/",
            "/img/%s.bin" % digest[:63],
        ]
        for path in bad_paths:
            status, _, _ = http_request(harness.base_url() + path)
            assert status == 404, "expected 404 for %r, got %d" % (path, status)
    finally:
        harness.stop()


def test_img_dir_bounded_to_img_keep_after_ten_publishes(byos_module, tmp_path):
    """After publishing 10 distinct images through /display, img/ holds exactly
    IMG_KEEP files matching the hash pattern, and the most recently advertised
    hash is among them"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        last_digest = None
        for n in range(10):
            with open(harness.image_path, "wb") as fh:
                fh.write(make_panel_bytes(n))
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
            assert status == 200, "publish %d: expected 200, got %d" % (n, status)
            last_digest = json.loads(body.decode())["image_hash"].split(":", 1)[1]

        img_dir = os.path.join(harness.tmpdir, "img")
        names = os.listdir(img_dir)
        assert len(names) == byos_module.IMG_KEEP, (
            "expected exactly IMG_KEEP (%d) files, found %d: %r"
            % (byos_module.IMG_KEEP, len(names), names))
        for name in names:
            assert byos_module._IMG_NAME_RE.match(name), "unexpected name in img/: %r" % (name,)
        assert ("%s.bin" % last_digest) in names, "most recently advertised hash was pruned"
    finally:
        harness.stop()


def test_prune_images_never_removes_the_just_advertised_hash(byos_module, tmp_path):
    """_prune_images keeps at most IMG_KEEP files and never removes keep_digest, even
    when keep_digest is the oldest file by mtime - the guarantee _publish_image relies
    on for a panel that alternates back to a previously-served image"""
    img_dir = os.path.join(str(tmp_path), "img")
    os.makedirs(img_dir)
    keep_digest = "a" * 64
    keep_path = os.path.join(img_dir, "%s.bin" % keep_digest)
    with open(keep_path, "wb") as fh:
        fh.write(b"keep")
    os.utime(keep_path, (1_000_000, 1_000_000))  # oldest of all the entries below

    for i in range(byos_module.IMG_KEEP + 5):
        digest = "%064x" % i
        path = os.path.join(img_dir, "%s.bin" % digest)
        with open(path, "wb") as fh:
            fh.write(b"x")
        os.utime(path, (2_000_000 + i, 2_000_000 + i))  # all newer than keep_digest

    byos_module._prune_images(img_dir, keep_digest=keep_digest)
    names = set(os.listdir(img_dir))
    assert ("%s.bin" % keep_digest) in names, "keep_digest was pruned despite being the oldest"
    assert len(names) == byos_module.IMG_KEEP, (
        "expected exactly IMG_KEEP (%d) survivors, found %d: %r"
        % (byos_module.IMG_KEEP, len(names), names))


def test_img_survives_byos_restart(tmp_path):
    """A byos restart between /display and /img/<X>.bin still serves X - the
    published file lives on disk, not only in the running process's memory"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        status, _, body = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200
        digest = json.loads(body.decode())["image_hash"].split(":", 1)[1]
        harness.stop()
        harness.start()
        status2, _, dbuf = http_request(harness.base_url() + "/img/%s.bin" % digest)
        assert status2 == 200, "expected 200 after restart, got %d" % status2
        assert hashlib.sha256(dbuf).hexdigest() == digest
    finally:
        harness.stop()


def test_display_answers_503_when_img_dir_cannot_be_written(tmp_path):
    """When img/ cannot be created or written (a read-only state dir), /display answers
    503 "image unavailable" rather than advertise a hash it cannot serve"""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permission bits")
    harness = Harness(tmp_path)
    try:
        harness.start()
        os.chmod(harness.tmpdir, 0o500)
        try:
            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        finally:
            os.chmod(harness.tmpdir, 0o700)
        assert status == 503, "expected 503, got %d" % status
        assert json.loads(body.decode()).get("detail") == "image unavailable"
    finally:
        harness.stop()


# --- Request hardening: Content-Length, socket timeout, bearer, log body ---


def test_malformed_content_length_gets_400_or_413_without_hanging(tmp_path):
    """A negative or non-integer Content-Length gets 400, and one above MAX_BODY_BYTES
    gets 413, both within 2s and without the server ever reading the body; a missing
    Content-Length on /device/v1/setup gets 422 (empty body fails JSON parsing, the
    same fail-closed path as any malformed body); the server keeps serving normal
    requests afterward"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        cases = [
            (["Content-Length: -1"], 400),
            (["Content-Length: abc"], 400),
            (["Content-Length: 70000"], 413),
        ]
        for header_lines, expected in cases:
            start = time.time()
            status, _ = _raw_request(
                harness.port, "POST /device/v1/log HTTP/1.1",
                ["Host: 127.0.0.1", "Authorization: Bearer %s" % KNOWN_TOKEN] + header_lines,
                read_timeout=2.0)
            elapsed = time.time() - start
            assert status == expected, (
                "headers=%r: expected %d, got %r" % (header_lines, expected, status))
            assert elapsed < 2.0, "headers=%r took %.2fs, expected under 2s" % (header_lines, elapsed)

        status, _ = _raw_request(
            harness.port, "POST /device/v1/setup HTTP/1.1", ["Host: 127.0.0.1"], read_timeout=2.0)
        assert status == 422, "expected 422 for a missing Content-Length, got %r" % (status,)

        # The server survives every malformed request above: a normal poll
        # still answers 200 - no thread was left wedged, no crash.
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200, "expected 200 after the malformed requests, got %d" % status
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()


def test_stalled_client_dropped_after_request_timeout_others_still_served(tmp_path):
    """A client that sends headers (Content-Length: 100) and then stalls has its
    connection closed within Handler.timeout, a second client is served while the
    first is still stalled (ThreadingHTTPServer must not block on it), and a third
    client is served normally after the stall too"""
    harness = Harness(tmp_path)
    try:
        harness.start(extra_args=["--request-timeout", "1"])
        sock = socket.create_connection(("127.0.0.1", harness.port), timeout=5)
        try:
            request = (
                "POST /device/v1/log HTTP/1.1\r\n"
                "Host: 127.0.0.1\r\n"
                "Authorization: Bearer %s\r\n"
                "Content-Length: 100\r\n"
                "Connection: close\r\n\r\n" % KNOWN_TOKEN
            ).encode("ascii")
            sock.sendall(request)  # headers only - the 100-byte body never arrives

            status, _, _ = http_request(
                harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
            assert status == 200, (
                "expected a concurrent client to be served during the stall, got %d" % status)

            start = time.time()
            sock.settimeout(5)
            data = sock.recv(4096)
            elapsed = time.time() - start
            assert data == b"", (
                "expected the stalled connection to be closed (empty recv), got %r" % (data,))
            assert elapsed < 3.0, "connection was not dropped within 3s (took %.2fs)" % elapsed
        finally:
            sock.close()

        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200, "expected a fresh client to be served after the stall, got %d" % status

        time.sleep(0.5)
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()


def test_client_sending_nothing_is_closed_after_timeout_no_traceback(tmp_path):
    """A client that connects and sends nothing at all is closed after
    --request-timeout, and byos's stdout never contains a traceback - the timeout
    fires before self.command/self.path exist on the handler instance"""
    harness = Harness(tmp_path)
    try:
        harness.start(extra_args=["--request-timeout", "1"])
        sock = socket.create_connection(("127.0.0.1", harness.port), timeout=5)
        try:
            start = time.time()
            sock.settimeout(5)
            data = sock.recv(4096)
            elapsed = time.time() - start
            assert data == b"", (
                "expected the connection to be closed (empty recv), got %r" % (data,))
            assert elapsed < 3.0, "connection was not dropped within 3s (took %.2fs)" % elapsed
        finally:
            sock.close()
        time.sleep(0.5)
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()


def test_bearer_ok_wrong_right_and_non_ascii(tmp_path):
    """A wrong bearer token gets 401; the seeded token gets 200; a non-ASCII bearer
    value gets 401, never a 500"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display",
            headers={"Authorization": "Bearer " + "0" * 64})
        assert status == 401, "expected 401 for a wrong bearer, got %d" % status

        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display", headers=harness.auth_headers())
        assert status == 200, "expected 200 for the seeded token, got %d" % status

        # Pre-encoded UTF-8 bytes, not a str: http.client's putheader()
        # latin-1-encodes a str header value and would raise before the
        # hostile bytes ever left the client (see test_poll_cycle.py's own
        # X-Battery-Mv coverage of the same gotcha).
        status, _, _ = http_request(
            harness.base_url() + "/device/v1/display",
            headers={"Authorization": ("Bearer " + "é" * 8).encode("utf-8")})
        assert status == 401, "expected 401 for a non-ASCII bearer, got %d" % status
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()


def test_log_endpoint_skips_non_dict_entries_and_accepts_dict_ones(tmp_path):
    """POST /device/v1/log with a logs array mixing non-dict and dict entries answers
    200, ok:true - non-dict entries are skipped rather than raising on entry.get"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        status, _, body = http_request(
            harness.base_url() + "/device/v1/log", method="POST",
            headers=harness.auth_headers(),
            json_body={"logs": [1, "x", None, {"level": "info", "message": "ok"}]})
        assert status == 200, "expected 200, got %d" % status
        assert json.loads(body.decode()).get("ok") is True
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()


def test_log_endpoint_rejects_deeply_nested_body_with_422_not_500(tmp_path):
    """A body of 30,000 '[' characters (deeper than the JSON decoder's recursion
    limit, still well under MAX_BODY_BYTES) answers 422, not 500 - RecursionError is
    caught alongside the usual JSON/Unicode decode errors"""
    harness = Harness(tmp_path)
    try:
        harness.start()
        deep_body = b"[" * 30000
        assert len(deep_body) < 64 * 1024
        status, _ = _raw_request(
            harness.port, "POST /device/v1/log HTTP/1.1",
            ["Host: 127.0.0.1",
             "Authorization: Bearer %s" % KNOWN_TOKEN,
             "Content-Type: application/json",
             "Content-Length: %d" % len(deep_body)],
            body=deep_body, read_timeout=5.0)
        assert status == 422, "expected 422 for a deeply nested body, got %r" % (status,)
        assert "Traceback" not in harness.read_stdout()
    finally:
        harness.stop()
