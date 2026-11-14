#!/usr/bin/env python3
"""X-Hw-Type handling of GET /device/v1/display.

A frame that sends no claim is served exactly as before. A well-formed
claim that differs from the server-assigned type withdraws the firmware
offer and the image container (the frame still gets the raw panel). A
claim never adds anything and is never stored.
"""
import hashlib
import importlib.util
import io
import os
import sys
import urllib.request
from contextlib import redirect_stdout

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server import (  # noqa: E402
    firmware_registry, fleet_db, fleet_migrate, fleet_ops, hardware, image_container)
from skypane_fw_image import build_image  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state  # noqa: E402

PANEL_BYTES = 960000
CONTAINER_BYTES = PANEL_BYTES + image_container.HEADER_LEN
FOREIGN_TYPE = "seeed-ee04-7in3-spectra6"
POLL_HEADERS = {"X-Battery-Mv": "3900", "X-Fw-Version": "fw-v1.0.0"}
VERSION = "fw-v1.1.0"


def _load_byos():
    spec = importlib.util.spec_from_file_location(
        "byos_server_hw_claim", os.path.join(HERE, "byos_server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


byos = _load_byos()


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


def _panel():
    return bytes([0x11] * PANEL_BYTES)


def _schedule_release(state_dir, hardware_type=None):
    image = build_image(VERSION)
    path = os.path.join(state_dir, "release.bin")
    with open(path, "wb") as fh:
        fh.write(image)
    manifest = {
        "version": VERSION, "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image), "released_at": "2026-01-01T00:00:00Z",
        "commit": "a" * 40, "notes": [],
        "hardware_type": hardware_type or hardware.LEGACY_KEY,
    }
    firmware_registry.publish_release(state_dir, manifest, path)
    assert firmware_registry.schedule_release(
        state_dir, VERSION, running_version=None) == "scheduled"


@pytest.fixture
def served(tmp_path):
    live = seed_live_like_state(str(tmp_path))
    with open(os.path.join(live.state_dir, "panel.bin"), "wb") as fh:
        fh.write(_panel())
    _schedule_release(live.state_dir)
    server = FrameServer(live.state_dir)
    server.start()
    yield live, server
    server.stop()


def _poll(server, live, extra=None):
    status, doc = server.display(live.token, dict(POLL_HEADERS, **(extra or {})))
    assert status == 200
    with urllib.request.urlopen(doc["image_url"], timeout=10) as resp:
        return doc, resp.read()


def test_claim_contradicts_table():
    legacy = hardware.LEGACY_KEY
    assert byos.claim_contradicts(None, legacy) is False
    assert byos.claim_contradicts("", legacy) is False
    assert byos.claim_contradicts("Bad Value", legacy) is False
    assert byos.claim_contradicts("a;b", legacy) is False
    assert byos.claim_contradicts("x" * 65, legacy) is False
    assert byos.claim_contradicts(FOREIGN_TYPE, None) is False
    assert byos.claim_contradicts(legacy, legacy) is False
    assert byos.claim_contradicts(FOREIGN_TYPE, legacy) is True


def test_no_headers_gets_raw_image_and_offer(served):
    live, server = served
    doc, body = _poll(server, live)
    assert len(body) == PANEL_BYTES
    assert doc["firmware"]["version"] == VERSION


def test_matching_claim_with_announcement_gets_container_and_offer(served):
    live, server = served
    doc, body = _poll(server, live, {
        "X-Hw-Type": hardware.LEGACY_KEY, "X-Img-Fmt": "1"})
    assert len(body) == CONTAINER_BYTES
    assert doc["firmware"]["version"] == VERSION


def test_announcement_without_claim_gets_container_and_offer(served):
    live, server = served
    doc, body = _poll(server, live, {"X-Img-Fmt": "1"})
    assert len(body) == CONTAINER_BYTES
    assert doc["firmware"]["version"] == VERSION


def test_contradicting_claim_withdraws_offer_and_container(served):
    live, server = served
    doc, body = _poll(server, live, {
        "X-Hw-Type": FOREIGN_TYPE, "X-Img-Fmt": "1"})
    assert len(body) == PANEL_BYTES
    assert doc["firmware"] is None
    assert doc["image_hash"] == "sha256:" + hashlib.sha256(_panel()).hexdigest()


def test_contradicting_claim_without_announcement_withdraws_offer(served):
    live, server = served
    doc, body = _poll(server, live, {"X-Hw-Type": FOREIGN_TYPE})
    assert len(body) == PANEL_BYTES
    assert doc["firmware"] is None


@pytest.mark.parametrize("value", ["Bad Value", "a;b", "", "X" * 80])
def test_malformed_claim_is_treated_as_absent(served, value):
    live, server = served
    doc, body = _poll(server, live, {"X-Hw-Type": value, "X-Img-Fmt": "1"})
    assert len(body) == CONTAINER_BYTES
    assert doc["firmware"]["version"] == VERSION


def test_contradiction_still_records_the_reported_version(served):
    live, server = served
    _poll(server, live, {"X-Hw-Type": FOREIGN_TYPE, "X-Fw-Version": "fw-v1.0.5"})
    report = firmware_registry.load_device_report(live.state_dir)
    entry = report["devices"][live.mac]
    assert entry["fw_version"] == "fw-v1.0.5"
    assert not any(e["kind"] == "offered" for e in entry["events"])


def test_claim_is_never_stored(served):
    live, server = served
    _poll(server, live, {"X-Hw-Type": FOREIGN_TYPE, "X-Img-Fmt": "1"})
    for root, _dirs, files in os.walk(live.state_dir):
        for name in files:
            if name.endswith(".bin") or name == "byos.stdout.log":
                continue
            with open(os.path.join(root, name), "rb") as fh:
                assert FOREIGN_TYPE.encode() not in fh.read()


def test_contradiction_log_line_is_deduplicated(served):
    live, _server = served
    out = io.StringIO()
    with redirect_stdout(out):
        byos._log_claim_mismatch_once("aa:bb", "seeed-x")
        byos._log_claim_mismatch_once("aa:bb", "seeed-x")
    assert out.getvalue().count("claim mismatch") == 1


def _seed_fleet_frame(state_dir, mac, token, hardware_type):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        owner = fleet_db.add_user(conn, "owner@example.com", "admin")
        fleet_db.add_device(
            conn, mac, "1" * 64, hardware_type, owner, token=token,
            environ={}, state_path="auto")
    finally:
        conn.close()


def test_fleet_frame_follows_the_same_rule(tmp_path):
    state_dir = str(tmp_path)
    mac, token = "aa:bb:cc:dd:ee:09", "ab" * 32
    _seed_fleet_frame(state_dir, mac, token, hardware.LEGACY_KEY)
    _schedule_release(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        row = fleet_db.get_device_by_mac(conn, mac)
        panel_dir = os.path.join(state_dir, row["state_path"])
    finally:
        conn.close()
    os.makedirs(panel_dir, exist_ok=True)
    with open(os.path.join(panel_dir, "panel.bin"), "wb") as fh:
        fh.write(_panel())
    server = FrameServer(state_dir)
    server.start()
    try:
        live = type("L", (), {"token": token, "mac": mac, "state_dir": state_dir})
        doc, body = _poll(server, live, {
            "X-Hw-Type": FOREIGN_TYPE, "X-Img-Fmt": "1"})
        assert len(body) == PANEL_BYTES
        assert doc["firmware"] is None
        doc, body = _poll(server, live, {
            "X-Hw-Type": hardware.LEGACY_KEY, "X-Img-Fmt": "1"})
        assert len(body) == CONTAINER_BYTES
        assert doc["firmware"]["version"] == VERSION
    finally:
        server.stop()


def test_pending_frame_contradiction_gets_raw_image(tmp_path):
    state_dir = str(tmp_path)
    seed_live_like_state(state_dir)
    fleet_migrate.migrate(state_dir, "owner@example.com", dry_run=False)
    mac = "aa:bb:cc:00:11:22"
    secret = "cd" * 32
    conn = fleet_db.connect(state_dir, create=False)
    try:
        fleet_ops.register_frame(
            conn, mac, hashlib.sha256(secret.encode()).hexdigest(),
            hardware.LEGACY_KEY, fleet_db.AuditActor(None, "test", None))
    finally:
        conn.close()
    server = FrameServer(state_dir)
    server.start()
    try:
        status, setup = server.setup(mac, secret)
        assert status == 200
        token = setup["device_token"]
        sizes = []
        for claim in (None, FOREIGN_TYPE):
            extra = {"X-Img-Fmt": "1"}
            if claim:
                extra["X-Hw-Type"] = claim
            status, doc = server.display(token, dict(POLL_HEADERS, **extra))
            assert status == 200
            assert doc["firmware"] is None
            with urllib.request.urlopen(doc["image_url"], timeout=10) as resp:
                sizes.append(len(resp.read()))
        assert sizes == [CONTAINER_BYTES, PANEL_BYTES]
    finally:
        server.stop()
