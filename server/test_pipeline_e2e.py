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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
STUB_SERVER_PATH = os.path.join(REPO_ROOT, "stub-server", "byos_server.py")
IMAGE_BYTES = 960000
LEGAL_NIBBLES = {0x0, 0x1, 0x2, 0x3, 0x5, 0x6}
STARTUP_DEADLINE_S = 10.0
# A fixed 64-lowercase-hex enrolment secret BYOSHarness.start() registers
# every fixture MAC against before its subprocess starts, so the three
# positive setup calls below keep working against byos_server.py's
# registry-gated /device/v1/setup (devices_registry contract).
HARNESS_ENROL_SECRET = "4" * 64
# The MACs any BYOSHarness instance in this file may enrol - registering
# all three against every instance's own --state-dir is simpler than
# threading a per-call mac list through BYOSHarness.start(), and costs
# nothing extra since register_device() is a local file write.
HARNESS_MACS = ("aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:03", "aa:bb:cc:dd:ee:04")
EXPECTED_CHECK_COUNT = 7  # Quick task 260923-fr4 (battery-empty-screen-before-the-pack-die):
# +1 (end to end through the real device protocol: a 3290 mV check-in latches BATTERY EMPTY
# and its hash is served with sleep_s 3600; a second run_once() is a byte-identical hash-skip;
# a 4100 mV check-in's own reply anticipates recovery before the next run_once() clears the
# park and serves a different hash)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


def load_byos_module():
    """Load byos_server.py directly via importlib.util, matching
    stub-server/test_poll_cycle.py's own pattern, so BYOSHarness.start()
    can call register_device() without going through HTTP. Safe because
    the module's top level is constants and defs only - main() sits
    behind an `if __name__ == "__main__"` guard.
    """
    spec = importlib.util.spec_from_file_location(
        "byos_server_pipeline_e2e_under_test", STUB_SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        # Registry-gated setup (devices_registry contract): register every
        # fixture MAC this file's checks use against this instance's own
        # --state-dir before the subprocess starts. Idempotent (replace=True)
        # - the second and third BYOSHarness instances below share the same
        # state_dir as the first, so re-registering is a harmless overwrite,
        # not a duplicate-MAC error.
        byos_module = load_byos_module()
        for mac in HARNESS_MACS:
            byos_module.register_device(
                self.state_dir, mac,
                hashlib.sha256(HARNESS_ENROL_SECRET.encode("ascii")).hexdigest(),
                replace=True)
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
        import server.device_config as device_config
        import server.panel_format as panel_format
        import server.plane.render as render
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
                json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "pipeline-e2e-harness",
                           "provision_secret": HARNESS_ENROL_SECRET})
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

        # 6. Check E (05-02, DEVICE-04): the whole slice, end to end, through
        # the real protocol. A second byos_server.py subprocess is started
        # against THIS SAME tmpdir (mirroring the real deployment's shared
        # SKYPANE_STATE_DIR - byos_server.py writes battery_state.json there,
        # poll_loop.py both reads it and serves panel.bin from the same
        # directory), a real authenticated poll carries X-Battery-Mv:3400,
        # and the next run_once() cycle's served panel.bin must differ from
        # the pre-battery baseline only inside the icon's byte columns/rows.
        def _real_battery_poll_changes_only_the_icon_region():
            battery_harness = BYOSHarness(panel_path, tmpdir)
            ctx["battery_harness"] = battery_harness
            try:
                battery_harness.start()
                status, _, body = http_request(
                    battery_harness.base_url() + "/device/v1/setup", method="POST",
                    json_body={"mac": "aa:bb:cc:dd:ee:03", "hw_rev": "pipeline-e2e-battery",
                               "provision_secret": HARNESS_ENROL_SECRET})
                if status != 200:
                    return False, "battery-check setup expected 200, got %d" % status
                token = json.loads(body.decode())["device_token"]

                # Healthy-battery baseline: re-run the multi-aircraft cycle
                # (same aircraft already on screen - a re-detection, not a
                # new one) with no battery signal ever reported yet.
                poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
                with open(panel_path, "rb") as fh:
                    panel_before = fh.read()

                status, _, _ = http_request(
                    battery_harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3400"})
                if status != 200:
                    return False, "battery-carrying display poll expected 200, got %d" % status
                time.sleep(1.0)  # allow the child process's write to land

                result_after = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
                with open(panel_path, "rb") as fh:
                    panel_after = fh.read()

                if panel_after == panel_before:
                    return False, "panel.bin did not change after a real X-Battery-Mv:3400 poll followed by a run_once() cycle"

                # 260828-0qo: icon shrunk to 70% linear size, anchor unchanged.
                # Row range is body_top..BATTERY_ICON_BOTTOM (1514..1536); byte
                # columns are the icon's x-range (64..115) halved, since the
                # packed panel is 4bpp (2px/byte): 64//2=32 .. 115//2=57.
                row_bytes = 600
                icon_row_start, icon_row_end = 1514, 1536
                icon_byte_start, icon_byte_end = 32, 57
                for row in range(1600):
                    row_before = panel_before[row * row_bytes:(row + 1) * row_bytes]
                    row_after = panel_after[row * row_bytes:(row + 1) * row_bytes]
                    if row_before == row_after:
                        continue
                    if not (icon_row_start <= row <= icon_row_end):
                        return False, "row %d, outside the icon's row range %d..%d, differs between the two panels" % (
                            row, icon_row_start, icon_row_end)
                    for b in range(row_bytes):
                        if row_before[b] != row_after[b] and not (icon_byte_start <= b <= icon_byte_end):
                            return False, "row %d byte %d, outside the icon's byte columns %d..%d, differs" % (
                                row, b, icon_byte_start, icon_byte_end)

                # Sample pixel (70, 1520) - byte offset 35, high nibble - still
                # lands inside the new fill rectangle (66, 1516, 75, 1534), so
                # this probe stays valid unchanged after the resize.
                #
                # 08-01 (D-01): the battery icon's ink for a non-empty state is
                # the ACTIVE theme's own ink index (render.py's docstring: the
                # empty state is always White/Black regardless of theme) - this
                # was hardcoded to nibble 0x1 (White) because the pre-Phase-8
                # default theme's ink was White for every active state. Now
                # that DEFAULT_THEME_ID is "white" (ink_index=IDX_BLACK), that
                # assumption no longer holds; derive the expectation from the
                # theme run_once() actually used instead of a stale literal.
                state = result_after.get("state")
                theme_id = result_after.get("theme", device_config.DEFAULT_THEME_ID)
                if state == "empty":
                    expected_nibble = 0x0
                else:
                    expected_idx = device_config.theme_ink_index(theme_id)
                    expected_nibble = panel_format.INDEX_TO_NIBBLE[expected_idx]
                sample_byte = panel_after[1520 * row_bytes + 35]
                actual_nibble = (sample_byte >> 4) & 0xF
                if actual_nibble != expected_nibble:
                    return False, (
                        "packed nibble at row 1520 x=70 (byte 1520*600+35, high nibble) is 0x%x, expected 0x%x "
                        "for run_once()'s reported state=%r" % (actual_nibble, expected_nibble, state)
                    )
                return True, ""
            finally:
                battery_harness.stop()
        check(
            "a real authenticated poll carrying X-Battery-Mv:3400, followed by a run_once() cycle, changes the "
            "served panel.bin only inside the icon's byte columns/rows, and the packed ink nibble at (1520,70) "
            "matches whichever state run_once() actually reported",
            _real_battery_poll_changes_only_the_icon_region,
        )

        # 7. Quick task 260923-fr4 (battery-empty-screen-before-the-pack-
        # die): the whole BATTERY EMPTY slice, end to end, through the
        # real device protocol. A third byos_server.py subprocess is
        # started against this same tmpdir, mirroring the real
        # deployment's shared SKYPANE_STATE_DIR exactly like check 6
        # above.
        def _real_battery_critical_park_and_recovery_end_to_end():
            park_harness = BYOSHarness(panel_path, tmpdir)
            ctx["park_harness"] = park_harness
            try:
                park_harness.start()
                status, _, body = http_request(
                    park_harness.base_url() + "/device/v1/setup", method="POST",
                    json_body={"mac": "aa:bb:cc:dd:ee:04", "hw_rev": "pipeline-e2e-battery-critical",
                               "provision_secret": HARNESS_ENROL_SECRET})
                if status != 200:
                    return False, "battery-critical setup expected 200, got %d" % status
                token = json.loads(body.decode())["device_token"]

                # Check in at 3290 mV (below BATTERY_CRITICAL_MV), then run
                # one poll cycle - it must latch the park and render
                # BATTERY EMPTY, byte-identical to
                # pack_panel(build_canvas(None, "battery_empty")).
                status, _, _ = http_request(
                    park_harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3290"})
                if status != 200:
                    return False, "3290 mV check-in expected 200, got %d" % status
                time.sleep(1.0)  # allow the child process's write to land

                result1 = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
                if result1.get("state") != "battery_empty":
                    return False, (
                        "expected state='battery_empty' after a 3290 mV check-in, got %r" % (result1.get("state"),)
                    )
                with open(panel_path, "rb") as fh:
                    panel_parked_1 = fh.read()
                expected_hash = hashlib.sha256(
                    panel_format.pack_panel(render.build_canvas(None, "battery_empty"))
                ).hexdigest()
                if hashlib.sha256(panel_parked_1).hexdigest() != expected_hash:
                    return False, "panel.bin after the park does not equal pack_panel(build_canvas(None, 'battery_empty'))"

                status, _, body = http_request(
                    park_harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % token})
                if status != 200:
                    return False, "post-park display poll expected 200, got %d" % status
                obj = json.loads(body.decode())
                if obj.get("sleep_s") != 3600:
                    return False, "post-park sleep_s = %r, expected exactly 3600" % (obj.get("sleep_s"),)
                served_hash = (obj.get("image_hash") or "").split(":", 1)[-1]
                if served_hash != expected_hash:
                    return False, (
                        "post-park image_hash %r does not match the BATTERY EMPTY hash %r"
                        % (served_hash, expected_hash)
                    )

                # A second run_once() with the panel already parked changes
                # nothing - the hash-skip the whole park exists to produce.
                poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
                with open(panel_path, "rb") as fh:
                    panel_parked_2 = fh.read()
                if panel_parked_2 != panel_parked_1:
                    return False, "a second parked run_once() cycle changed panel.bin - expected a byte-identical hash-skip"

                # Check in at 4100 mV (recovering) - THIS reply must
                # already carry the normal (non-parked) sleep_s,
                # anticipating recovery within the very request that
                # reports it, before the next run_once() has even run.
                status, _, body = http_request(
                    park_harness.base_url() + "/device/v1/display", method="GET",
                    headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "4100"})
                if status != 200:
                    return False, "4100 mV recovery check-in expected 200, got %d" % status
                obj = json.loads(body.decode())
                if obj.get("sleep_s") == 3600:
                    return False, "recovering check-in still returned the parked sleep_s (3600) - recovery anticipation failed"
                time.sleep(1.0)  # allow the child process's write to land

                # The next run_once() clears the park and repaints the live
                # board - a different hash from the parked one.
                result2 = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
                if result2.get("state") == "battery_empty":
                    return False, "expected the park to clear after a 4100 mV recovery, but state is still 'battery_empty'"
                with open(panel_path, "rb") as fh:
                    panel_recovered = fh.read()
                if hashlib.sha256(panel_recovered).hexdigest() == expected_hash:
                    return False, "panel.bin after recovery still matches the BATTERY EMPTY hash, expected a different one"
                return True, ""
            finally:
                park_harness.stop()
        check(
            "end to end through the real device protocol: a 3290 mV check-in followed by run_once() "
            "latches BATTERY EMPTY and serves its hash with sleep_s 3600; a second run_once() is a "
            "byte-identical hash-skip; a 4100 mV check-in's OWN reply anticipates recovery (sleep_s "
            "!= 3600) before the next run_once() clears the park and serves a different hash",
            _real_battery_critical_park_and_recovery_end_to_end,
        )

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
