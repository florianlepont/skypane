#!/usr/bin/env python3
"""End-to-end contract test: server/poll_loop.py's run_once() through the
real stub-server/byos_server.py device protocol (PLANE-03, D-04).

poll_loop transitively imports Pillow via server.plane.render, so this
module must be run under server/.venv's interpreter, not the bare system
python3.

This is ONE consolidated test function rather than seven independent
ones (MR-4): every one of the seven old checks below shares the same
`tmp_path` state directory and, from check 3 onward, the same served
`panel.bin` - check 5 asserts the panel is unchanged from check 1's
write, check 6's "re-detection, not a new one" depends on a flight
already being on screen from check 1/5, and check 7's battery-empty park
and recovery both read and write `poll_state.json`/`battery_state.json`
in that same shared directory across three separate byos_server.py
subprocesses. Splitting this into independent pytest tests would mean
either reinventing that shared state per test (not what the original
harness proves) or introducing inter-test ordering dependencies MR-4
forbids - one node id, one docstring line per old check label, is the
faithful translation.
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
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
STUB_SERVER_PATH = os.path.join(REPO_ROOT, "stub-server", "byos_server.py")
IMAGE_BYTES = 960000
LEGAL_NIBBLES = {0x0, 0x1, 0x2, 0x3, 0x5, 0x6}
STARTUP_DEADLINE_S = 10.0
# A fixed 64-lowercase-hex enrolment secret BYOSHarness.start() registers
# every fixture MAC against before its subprocess starts, so the positive
# setup calls below keep working against byos_server.py's registry-gated
# /device/v1/setup.
HARNESS_ENROL_SECRET = "4" * 64
HARNESS_MACS = ("aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:03", "aa:bb:cc:dd:ee:04")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# `pytest` invocation; the legacy-runner bridge below (MR-3) executes this
# file directly instead, so the same directory is added here too.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import server.device_config as device_config  # noqa: E402
import server.panel_format as panel_format  # noqa: E402
import server.plane.render as render  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402
from skypane_test_support import child_env  # noqa: E402


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


def load_byos_module():
    """Import byos_server.py by path so BYOSHarness.start() can call
    register_device() directly; its top level is constants and defs only."""
    spec = importlib.util.spec_from_file_location(
        "byos_server_pipeline_e2e_under_test", STUB_SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BYOSHarness:
    """Owns a byos_server.py subprocess lifecycle for the download half of
    this test. Modeled on stub-server/test_poll_cycle.py's Harness class -
    free port, guaranteed teardown, never leaves an orphaned server
    holding the port. `env` defaults to `child_env()` (MR-9) so the child
    interpreter carries the same no-network guard as this pytest process.
    """

    def __init__(self, image_path, state_dir, env=None):
        self.image_path = image_path
        self.state_dir = state_dir
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(state_dir, "byos_server.stdout.log")
        self.env = env if env is not None else child_env()
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
        # Setup is registry-gated: register every fixture MAC against this
        # instance's --state-dir (replace=True: instances may share one).
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
                stdout=stdout_fh, stderr=subprocess.STDOUT, env=self.env,
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


@pytest.fixture
def byos_server_factory(tmp_path):
    """A factory fixture: each call starts a NEW byos_server.py subprocess
    and guarantees it is stopped at teardown, even if the test fails
    partway through starting a later one. Defaults each new instance's
    own state dir to a fresh subdirectory under `tmp_path` (isolated from
    poll_loop's own state_dir); a caller that needs a server to share
    poll_loop's state (the battery/park checks below) passes `state_dir`
    explicitly.
    """
    harnesses = []

    def _start(image_path, state_dir=None):
        if state_dir is None:
            state_dir = tmp_path / ("byos-%d" % len(harnesses))
            state_dir.mkdir()
            state_dir = str(state_dir)
        harness = BYOSHarness(image_path, state_dir)
        harness.start()
        harnesses.append(harness)
        return harness

    yield _start

    for harness in harnesses:
        harness.stop()


def test_full_pipeline_end_to_end_through_the_real_device_protocol(tmp_path, fake_providers, byos_server_factory):
    """Covers, in order, the seven old checks this file used to run as
    independent `check()` calls sharing one process-global state
    directory:

    1. run_once(multi-aircraft fixture) writes panel.bin at exactly 960000 bytes
    2. panel.bin bytes decompose into only the six legal nibble codes
    3. byos_server.py setup->display returns a valid image_url and image_hash
    4. downloaded image is 960000 bytes and SHA-256-verifies against image_hash
    5. run_once(empty fixture) leaves panel.bin byte-identical (D-04)
    6. a real authenticated poll carrying X-Battery-Mv:3400, followed by a run_once() cycle, changes the served panel.bin only inside the icon's byte columns/rows, and the packed ink nibble at (1520,70) matches whichever state run_once() actually reported
    7. end to end through the real device protocol: a 3290 mV check-in followed by run_once() latches BATTERY EMPTY and serves its hash with sleep_s 3600; a second run_once() is a byte-identical hash-skip; a 4100 mV check-in's OWN reply anticipates recovery (sleep_s != 3600) before the next run_once() clears the park and serves a different hash

    fake_providers is required (not called on): run_once() enriches the
    displayed flight's route via server.plane.enrich.resolve_route(),
    which - absent a canned response - reaches its default adsbdb host
    and gets the fixture's default 404 "unknown callsign", falling back
    to the static airline-prefix table exactly like the pre-migration
    baseline's "route_source=airline_only" outcome (enrich.py's own
    lookup_route() never lets that miss raise into this test).
    """
    tmpdir = str(tmp_path)
    multi_snapshot = load_fixture("geofence_multi_aircraft.json")
    empty_snapshot = load_fixture("geofence_empty.json")
    panel_path = os.path.join(tmpdir, "panel.bin")

    # 1. run_once() with the multi-aircraft fixture writes a panel.bin of
    #    exactly 960000 bytes.
    poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    assert os.path.exists(panel_path), "run_once did not write panel.bin"
    with open(panel_path, "rb") as fh:
        panel_bytes = fh.read()
    assert len(panel_bytes) == IMAGE_BYTES, "panel.bin is %d bytes, expected %d" % (len(panel_bytes), IMAGE_BYTES)

    # 2. Every byte of the panel decomposes into two nibbles drawn only
    #    from the six legal Spectra 6 codes.
    bad_nibbles = set()
    for b in panel_bytes:
        left, right = (b >> 4) & 0xF, b & 0xF
        if left not in LEGAL_NIBBLES:
            bad_nibbles.add(left)
        if right not in LEGAL_NIBBLES:
            bad_nibbles.add(right)
    assert not bad_nibbles, "panel.bin contains illegal nibble codes: %r" % (sorted(bad_nibbles),)

    # 3. byos_server.py serves that panel.bin through the real protocol:
    #    setup -> bearer token -> display metadata.
    harness = byos_server_factory(panel_path)
    status, _, body = http_request(
        harness.base_url() + "/device/v1/setup", method="POST",
        json_body={"mac": "aa:bb:cc:dd:ee:02", "hw_rev": "pipeline-e2e-harness",
                   "provision_secret": HARNESS_ENROL_SECRET})
    assert status == 200, "setup expected 200, got %d" % status
    token = json.loads(body.decode())["device_token"]

    status, _, body = http_request(
        harness.base_url() + "/device/v1/display", method="GET",
        headers={"Authorization": "Bearer %s" % token})
    assert status == 200, "display expected 200, got %d" % status
    display_obj = json.loads(body.decode())
    image_url = display_obj.get("image_url")
    image_hash = display_obj.get("image_hash")
    assert image_url and image_hash, "missing image_url/image_hash in display response: %r" % (display_obj,)

    # 4. Downloading image_url yields exactly 960000 bytes whose SHA-256
    #    matches the declared image_hash (the firmware verification rule).
    status, _, buf = http_request(image_url, method="GET")
    assert status == 200, "image download expected 200, got %d" % status
    assert verify_panel_bytes(buf, image_hash), (
        "downloaded bytes failed SHA-256 verification against image_hash (len=%d)" % len(buf)
    )

    # 5. D-04: run_once() with an empty geofence snapshot leaves the
    #    already-served panel.bin byte-identical - no waiting screen, no
    #    expiry.
    poll_loop.run_once(snapshot=empty_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    with open(panel_path, "rb") as fh:
        after_empty = fh.read()
    assert after_empty == panel_bytes, "panel.bin changed after an empty-snapshot cycle (violates D-04)"

    # 6. Check E (05-02, DEVICE-04): the whole slice, end to end, through
    # the real protocol. A second byos_server.py subprocess is started
    # against THIS SAME tmp_path (mirroring the real deployment's shared
    # SKYPANE_STATE_DIR - byos_server.py writes battery_state.json there,
    # poll_loop.py both reads it and serves panel.bin from the same
    # directory), a real authenticated poll carries X-Battery-Mv:3400,
    # and the next run_once() cycle's served panel.bin must differ from
    # the pre-battery baseline only inside the icon's byte columns/rows.
    battery_harness = byos_server_factory(panel_path, state_dir=tmpdir)
    status, _, body = http_request(
        battery_harness.base_url() + "/device/v1/setup", method="POST",
        json_body={"mac": "aa:bb:cc:dd:ee:03", "hw_rev": "pipeline-e2e-battery",
                   "provision_secret": HARNESS_ENROL_SECRET})
    assert status == 200, "battery-check setup expected 200, got %d" % status
    token = json.loads(body.decode())["device_token"]

    # Healthy-battery baseline: re-run the multi-aircraft cycle (same
    # aircraft already on screen - a re-detection, not a new one) with no
    # battery signal ever reported yet.
    poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    with open(panel_path, "rb") as fh:
        panel_before = fh.read()

    status, _, _ = http_request(
        battery_harness.base_url() + "/device/v1/display", method="GET",
        headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3400"})
    assert status == 200, "battery-carrying display poll expected 200, got %d" % status
    time.sleep(1.0)  # allow the child process's write to land

    result_after = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    with open(panel_path, "rb") as fh:
        panel_after = fh.read()

    assert panel_after != panel_before, (
        "panel.bin did not change after a real X-Battery-Mv:3400 poll followed by a run_once() cycle"
    )

    # 260828-0qo: icon shrunk to 70% linear size, anchor unchanged. Row
    # range is body_top..BATTERY_ICON_BOTTOM (1514..1536); byte columns
    # are the icon's x-range (64..115) halved, since the packed panel is
    # 4bpp (2px/byte): 64//2=32 .. 115//2=57.
    row_bytes = 600
    icon_row_start, icon_row_end = 1514, 1536
    icon_byte_start, icon_byte_end = 32, 57
    for row in range(1600):
        row_before = panel_before[row * row_bytes:(row + 1) * row_bytes]
        row_after = panel_after[row * row_bytes:(row + 1) * row_bytes]
        if row_before == row_after:
            continue
        assert icon_row_start <= row <= icon_row_end, (
            "row %d, outside the icon's row range %d..%d, differs between the two panels"
            % (row, icon_row_start, icon_row_end)
        )
        for b in range(row_bytes):
            assert row_before[b] == row_after[b] or (icon_byte_start <= b <= icon_byte_end), (
                "row %d byte %d, outside the icon's byte columns %d..%d, differs" % (row, b, icon_byte_start, icon_byte_end)
            )

    # Sample pixel (70, 1520) - byte offset 35, high nibble - still lands
    # inside the new fill rectangle (66, 1516, 75, 1534), so this probe
    # stays valid unchanged after the resize.
    #
    # 08-01 (D-01): the battery icon's ink for a non-empty state is the
    # ACTIVE theme's own ink index (render.py's docstring: the empty
    # state is always White/Black regardless of theme) - this was
    # hardcoded to nibble 0x1 (White) because the pre-Phase-8 default
    # theme's ink was White for every active state. Now that
    # DEFAULT_THEME_ID is "white" (ink_index=IDX_BLACK), that assumption
    # no longer holds; derive the expectation from the theme run_once()
    # actually used instead of a stale literal.
    state = result_after.get("state")
    theme_id = result_after.get("theme", device_config.DEFAULT_THEME_ID)
    if state == "empty":
        expected_nibble = 0x0
    else:
        expected_idx = device_config.theme_ink_index(theme_id)
        expected_nibble = panel_format.INDEX_TO_NIBBLE[expected_idx]
    sample_byte = panel_after[1520 * row_bytes + 35]
    actual_nibble = (sample_byte >> 4) & 0xF
    assert actual_nibble == expected_nibble, (
        "packed nibble at row 1520 x=70 (byte 1520*600+35, high nibble) is 0x%x, expected 0x%x "
        "for run_once()'s reported state=%r" % (actual_nibble, expected_nibble, state)
    )

    # 7. Quick task 260923-fr4 (battery-empty-screen-before-the-pack-die):
    # the whole BATTERY EMPTY slice, end to end, through the real device
    # protocol. A third byos_server.py subprocess is started against this
    # same tmp_path, mirroring the real deployment's shared
    # SKYPANE_STATE_DIR exactly like check 6 above.
    park_harness = byos_server_factory(panel_path, state_dir=tmpdir)
    status, _, body = http_request(
        park_harness.base_url() + "/device/v1/setup", method="POST",
        json_body={"mac": "aa:bb:cc:dd:ee:04", "hw_rev": "pipeline-e2e-battery-critical",
                   "provision_secret": HARNESS_ENROL_SECRET})
    assert status == 200, "battery-critical setup expected 200, got %d" % status
    token = json.loads(body.decode())["device_token"]

    # Check in at 3290 mV (below BATTERY_CRITICAL_MV), then run one poll
    # cycle - it must latch the park and render BATTERY EMPTY,
    # byte-identical to pack_panel(build_canvas(None, "battery_empty")).
    status, _, _ = http_request(
        park_harness.base_url() + "/device/v1/display", method="GET",
        headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "3290"})
    assert status == 200, "3290 mV check-in expected 200, got %d" % status
    time.sleep(1.0)  # allow the child process's write to land

    result1 = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    assert result1.get("state") == "battery_empty", (
        "expected state='battery_empty' after a 3290 mV check-in, got %r" % (result1.get("state"),)
    )
    with open(panel_path, "rb") as fh:
        panel_parked_1 = fh.read()
    expected_hash = hashlib.sha256(
        panel_format.pack_panel(render.build_canvas(None, "battery_empty"))
    ).hexdigest()
    assert hashlib.sha256(panel_parked_1).hexdigest() == expected_hash, (
        "panel.bin after the park does not equal pack_panel(build_canvas(None, 'battery_empty'))"
    )

    status, _, body = http_request(
        park_harness.base_url() + "/device/v1/display", method="GET",
        headers={"Authorization": "Bearer %s" % token})
    assert status == 200, "post-park display poll expected 200, got %d" % status
    obj = json.loads(body.decode())
    assert obj.get("sleep_s") == 3600, "post-park sleep_s = %r, expected exactly 3600" % (obj.get("sleep_s"),)
    served_hash = (obj.get("image_hash") or "").split(":", 1)[-1]
    assert served_hash == expected_hash, (
        "post-park image_hash %r does not match the BATTERY EMPTY hash %r" % (served_hash, expected_hash)
    )

    # A second run_once() with the panel already parked changes nothing -
    # the hash-skip the whole park exists to produce.
    poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    with open(panel_path, "rb") as fh:
        panel_parked_2 = fh.read()
    assert panel_parked_2 == panel_parked_1, (
        "a second parked run_once() cycle changed panel.bin - expected a byte-identical hash-skip"
    )

    # Check in at 4100 mV (recovering) - THIS reply must already carry
    # the normal (non-parked) sleep_s, anticipating recovery within the
    # very request that reports it, before the next run_once() has even
    # run.
    status, _, body = http_request(
        park_harness.base_url() + "/device/v1/display", method="GET",
        headers={"Authorization": "Bearer %s" % token, "X-Battery-Mv": "4100"})
    assert status == 200, "4100 mV recovery check-in expected 200, got %d" % status
    obj = json.loads(body.decode())
    assert obj.get("sleep_s") != 3600, "recovering check-in still returned the parked sleep_s (3600) - recovery anticipation failed"
    time.sleep(1.0)  # allow the child process's write to land

    # The next run_once() clears the park and repaints the live board - a
    # different hash from the parked one.
    result2 = poll_loop.run_once(snapshot=multi_snapshot, state_dir=tmpdir, geofence=GEOFENCE_PATH)
    assert result2.get("state") != "battery_empty", (
        "expected the park to clear after a 4100 mV recovery, but state is still 'battery_empty'"
    )
    with open(panel_path, "rb") as fh:
        panel_recovered = fh.read()
    assert hashlib.sha256(panel_recovered).hexdigest() != expected_hash, (
        "panel.bin after recovery still matches the BATTERY EMPTY hash, expected a different one"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
