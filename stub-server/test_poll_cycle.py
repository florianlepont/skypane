#!/usr/bin/env python3
"""End-to-end poll-cycle contract harness for stub-server/byos_server.py.

Stdlib-only (urllib.request, hashlib, json, subprocess, socket, time, os,
sys, tempfile, shutil - nothing else). Generates a deterministic panel
image with make_test_panel.py, launches byos_server.py as a subprocess
on a free local port, and drives it through the full device-protocol
contract documented in flightportrait/frame's docs/PROTOCOL.md at the
pinned commit ce3335fc5e566bcc6ccd29966ec39bf5c5318f12 (sections 1, 2,
3 and 5): setup, the bearer-token auth gate, the display-response
shape, download + SHA-256 + exact-size verification, the hash-skip
optimisation, a served-image change, telemetry header echoing, the log
endpoint, two hand-built malformed-response rejections, and connection
failure classification when the server is down.

Exits 0 only when every check below passes; any failure (or exception -
none is ever swallowed into a pass) exits 1.

Usage:
    python3 stub-server/test_poll_cycle.py
"""
import hashlib
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

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(HERE, "byos_server.py")
MAKE_PANEL_PATH = os.path.join(HERE, "make_test_panel.py")
IMAGE_BYTES = 960000
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 17


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
            ctx["image_hash_full"] = obj["image_hash"]
            ctx["image_url"] = obj["image_url"]
            return True, ""
        check("display poll returns a valid response shape (incl. firmware:null)", _display_shape)

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

        # 17. Failure classification: with the server stopped, a display poll
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
