#!/usr/bin/env python3
"""End-to-end contract harness: server/poll_loop.py's run_once() through the
real stub-server/byos_server.py device protocol (PLANE-03, D-04).

Stdlib-only, plus the module under test (server.poll_loop) - poll_loop
transitively imports Pillow via server.plane.render, so this harness must be
run under server/.venv's interpreter, not the bare system python3. Exits 0
only when every check below passes; any failure (or exception - none is ever
swallowed into a pass) exits 1.

Usage:
    server/.venv/bin/python3 server/test_pipeline_e2e.py
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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
STUB_SERVER_PATH = os.path.join(REPO_ROOT, "stub-server", "byos_server.py")
IMAGE_BYTES = 960000
LEGAL_NIBBLES = {0x0, 0x1, 0x2, 0x3, 0x5, 0x6}
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 5

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


def verify_panel_bytes(buf, expected_hash):
    """Mirror the firmware verification rule (PROTOCOL.md section 2): a
    buffer reaches the panel only when its length is exactly 960000 bytes
    AND its SHA-256 hex digest equals the hex portion of the server-declared
    image_hash (which carries a "sha256:" prefix).
    """
    if len(buf) != IMAGE_BYTES:
        return False
    if expected_hash is None:
        return False
    expected_hex = expected_hash.split(":", 1)[-1] if ":" in expected_hash else expected_hash
    return hashlib.sha256(buf).hexdigest() == expected_hex


def http_request(url, method="GET", headers=None, json_body=None, timeout=10):
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


class BYOSHarness:
    """Owns a byos_server.py subprocess lifecycle for the download half of
    this test. Modeled on stub-server/test_poll_cycle.py's Harness class -
    free port, finally-guaranteed teardown, never leaves an orphaned server
    holding the port.
    """

    def __init__(self, image_path, state_dir):
        self.image_path = image_path
        self.state_dir = state_dir
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(state_dir, "byos_server.stdout.log")
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
        stdout_fh = open(self.stdout_path, "w")
        try:
            self.proc = subprocess.Popen(
                [sys.executable, STUB_SERVER_PATH,
                 "--image", self.image_path,
                 "--port", str(self.port),
                 "--sleep", "300",
                 "--state-dir", self.state_dir],
                stdout=stdout_fh, stderr=subprocess.STDOUT,
            )
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("byos_server.py exited early (code %s)" % self.proc.returncode)
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

    try:
        import server.poll_loop as poll_loop
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before
        # server/poll_loop.py (or its server/plane/render.py dependency)
        # exists. It must fail - Task 3 turns it green.
        print("FAIL import server.poll_loop - %r" % (exc,))
        print("pipeline-e2e: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    tmpdir = tempfile.mkdtemp(prefix="ink-pipeline-e2e-")
    ctx = {}

    try:
        multi_snapshot = load_fixture("geofence_multi_aircraft.json")
        empty_snapshot = load_fixture("geofence_empty.json")
        panel_path = os.path.join(tmpdir, "panel.bin")

        # 1. run_once() with the multi-aircraft fixture writes a panel.bin of
        #    exactly 960000 bytes.
        def _writes_correctly_sized_panel():
            poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
            if not os.path.exists(panel_path):
                return False, "run_once did not write panel.bin"
            with open(panel_path, "rb") as fh:
                buf = fh.read()
            if len(buf) != IMAGE_BYTES:
                return False, "panel.bin is %d bytes, expected %d" % (len(buf), IMAGE_BYTES)
            ctx["panel_bytes"] = buf
            return True, ""
        check("run_once(multi-aircraft fixture) writes panel.bin at exactly 960000 bytes", _writes_correctly_sized_panel)

        # 2. Every byte of the panel decomposes into two nibbles drawn only
        #    from the six legal Spectra 6 codes.
        def _only_legal_nibbles():
            buf = ctx.get("panel_bytes")
            if buf is None:
                return False, "no panel bytes captured from the previous check"
            bad = set()
            for b in buf:
                left, right = (b >> 4) & 0xF, b & 0xF
                if left not in LEGAL_NIBBLES:
                    bad.add(left)
                if right not in LEGAL_NIBBLES:
                    bad.add(right)
            if bad:
                return False, "panel.bin contains illegal nibble codes: %r" % (sorted(bad),)
            return True, ""
        check("panel.bin bytes decompose into only the six legal nibble codes", _only_legal_nibbles)

        # 3. byos_server.py serves that panel.bin through the real protocol:
        #    setup -> bearer token -> display metadata.
        def _protocol_setup_and_display():
            harness = BYOSHarness(panel_path, tempfile.mkdtemp(prefix="ink-pipeline-e2e-byos-", dir=tmpdir))
            ctx["harness"] = harness
            harness.start()
            status, _, body = http_request(
                harness.base_url() + "/device/v1/setup", method="POST",
                json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "pipeline-e2e-harness"})
            if status != 200:
                return False, "setup expected 200, got %d" % status
            token = json.loads(body.decode())["device_token"]

            status, _, body = http_request(
                harness.base_url() + "/device/v1/display", method="GET",
                headers={"Authorization": "Bearer %s" % token})
            if status != 200:
                return False, "display expected 200, got %d" % status
            display_obj = json.loads(body.decode())
            image_url = display_obj.get("image_url")
            image_hash = display_obj.get("image_hash")
            if not image_url or not image_hash:
                return False, "missing image_url/image_hash in display response: %r" % (display_obj,)
            ctx["image_url"] = image_url
            ctx["image_hash"] = image_hash
            return True, ""
        check("byos_server.py setup->display returns a valid image_url and image_hash", _protocol_setup_and_display)

        # 4. Downloading image_url yields exactly 960000 bytes whose SHA-256
        #    matches the declared image_hash (the firmware verification rule).
        def _download_hash_verifies():
            image_url = ctx.get("image_url")
            image_hash = ctx.get("image_hash")
            if not image_url:
                return False, "no image_url captured from the previous check"
            status, _, buf = http_request(image_url, method="GET")
            if status != 200:
                return False, "image download expected 200, got %d" % status
            if not verify_panel_bytes(buf, image_hash):
                return False, "downloaded bytes failed SHA-256 verification against image_hash (len=%d)" % len(buf)
            return True, ""
        check("downloaded image is 960000 bytes and SHA-256-verifies against image_hash", _download_hash_verifies)

        # 5. D-04: run_once() with an empty geofence snapshot leaves the
        #    already-served panel.bin byte-identical - no waiting screen,
        #    no expiry.
        def _empty_leaves_panel_unchanged():
            before = ctx.get("panel_bytes")
            if before is None:
                return False, "no prior panel.bin bytes captured"
            poll_loop.run_once(snapshot=empty_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
            with open(panel_path, "rb") as fh:
                after = fh.read()
            if after != before:
                return False, "panel.bin changed after an empty-snapshot cycle (violates D-04)"
            return True, ""
        check("run_once(empty fixture) leaves panel.bin byte-identical (D-04)", _empty_leaves_panel_unchanged)

    finally:
        harness = ctx.get("harness")
        if harness is not None:
            harness.stop()
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("pipeline-e2e: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
