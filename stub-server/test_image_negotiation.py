#!/usr/bin/env python3
"""Legacy display behaviour of byos_server.py, pinned to committed constants.

A frame that sends no image-format announcement (or one the server cannot
use) must keep receiving the raw 960,000-byte panel file, the same
image_hash and the same display JSON as before format negotiation existed.
The REFERENCE_* constants were captured from the server before any
negotiation code was added; the panel bytes come from deterministic_panel().
"""
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state  # noqa: E402
from server import image_container  # noqa: E402

PANEL_BYTES = 960000
# The six Spectra 6 nibble codes.
LEGAL = (0, 1, 2, 3, 5, 6)
POLL_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
}
STATE_FILES = (
    "devices.json", "byos_state.json", "device_config.json",
    "battery_state.json", os.path.join("firmware", "device_report.json"),
)
FREEZE_PATH = os.path.join(HERE, "measured_fields_freeze.json")

REFERENCE_PANEL_SHA256 = "46d99bcb92a8c1e39f5da6aeb7d46d974d24cacaac9dee63080c01e93bb86378"
REFERENCE_DISPLAY = {
    "firmware": None,
    "image_hash": "sha256:" + REFERENCE_PANEL_SHA256,
    "image_url": "/img/" + REFERENCE_PANEL_SHA256 + ".bin",
    "led_enabled": True,
    "reset": False,
    "sleep_s": 1800,
}


def deterministic_panel():
    """960,000 bytes of legal packed nibble pairs, two pixels per byte."""
    return bytes(
        (LEGAL[(i * 5) % 6] << 4) | LEGAL[(i * 3 + 1) % 6]
        for i in range(PANEL_BYTES))


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def served(tmp_path):
    live = seed_live_like_state(str(tmp_path))
    with open(os.path.join(live.state_dir, "panel.bin"), "wb") as fh:
        fh.write(deterministic_panel())
    server = FrameServer(live.state_dir)
    server.start()
    yield live, server
    server.stop()


def fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


def normalise(doc):
    out = dict(doc)
    out["image_url"] = re.sub(r"^https?://[^/]+", "", doc["image_url"])
    return out


def poll(server, live, extra=None):
    status, doc = server.display(live.token, dict(POLL_HEADERS, **(extra or {})))
    assert status == 200
    return doc


def test_legacy_poll_serves_the_raw_panel_bytes(served):
    live, server = served
    doc = poll(server, live)
    body = fetch_bytes(doc["image_url"])
    assert len(body) == PANEL_BYTES
    assert body == deterministic_panel()
    assert hashlib.sha256(body).hexdigest() == REFERENCE_PANEL_SHA256


def test_legacy_poll_response_matches_the_reference(served):
    live, server = served
    doc = poll(server, live)
    assert doc["image_hash"] == "sha256:" + REFERENCE_PANEL_SHA256
    assert normalise(doc) == REFERENCE_DISPLAY


def test_legacy_response_keys_equal_the_freeze_list(served):
    live, server = served
    with open(FREEZE_PATH, encoding="utf-8") as fh:
        frozen = json.load(fh)["display_response_keys"]["keys"]
    assert sorted(poll(server, live)) == sorted(frozen)


JUNK_ANNOUNCEMENTS = ["", "0", "abc", "1,2", "-1", "+1", "1000", "9" * 100]


@pytest.mark.parametrize("value", JUNK_ANNOUNCEMENTS)
def test_legacy_junk_announcement_is_served_raw(served, value):
    live, server = served
    doc = poll(server, live, {"X-Img-Fmt": value})
    body = fetch_bytes(doc["image_url"])
    assert len(body) == PANEL_BYTES
    assert body == deterministic_panel()
    assert doc["image_hash"] == "sha256:" + REFERENCE_PANEL_SHA256


def without_timestamps(node):
    """The JSON document with receive-time stamps blanked."""
    if isinstance(node, dict):
        return {k: (None if k.endswith("_at") else without_timestamps(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [without_timestamps(v) for v in node]
    return node


def read_state_files(state_dir):
    out = {}
    for name in STATE_FILES:
        with open(os.path.join(state_dir, name), encoding="utf-8") as fh:
            out[name] = without_timestamps(json.load(fh))
    return out


@pytest.mark.parametrize("value", ["1", "abc"])
def test_legacy_state_files_ignore_announcement_header(served, value):
    live, server = served
    poll(server, live)
    baseline = read_state_files(live.state_dir)
    poll(server, live, {"X-Img-Fmt": value})
    assert read_state_files(live.state_dir) == baseline


CONTAINER_BYTES = PANEL_BYTES + image_container.HEADER_LEN


@pytest.mark.parametrize("value", ["1", "2", "999"])
def test_announce_serves_the_container(served, value):
    live, server = served
    doc = poll(server, live, {"X-Img-Fmt": value})
    body = fetch_bytes(doc["image_url"])
    assert len(body) == CONTAINER_BYTES
    assert body.startswith(b"SPIM")
    view = image_container.decode_container(body, 1200, 1600)
    assert view.payload == deterministic_panel()
    assert doc["image_hash"] == "sha256:" + hashlib.sha256(body).hexdigest()
    assert doc["image_url"].endswith(hashlib.sha256(body).hexdigest() + ".bin")


def test_announce_adds_no_display_key(served):
    live, server = served
    with open(FREEZE_PATH, encoding="utf-8") as fh:
        frozen = json.load(fh)["display_response_keys"]["keys"]
    assert sorted(poll(server, live, {"X-Img-Fmt": "1"})) == sorted(frozen)


def test_announce_and_legacy_urls_both_stay_fetchable(served):
    live, server = served
    announced = poll(server, live, {"X-Img-Fmt": "1"})
    legacy = poll(server, live)
    assert legacy["image_hash"] == "sha256:" + REFERENCE_PANEL_SHA256
    assert fetch_bytes(legacy["image_url"]) == deterministic_panel()
    body = fetch_bytes(announced["image_url"])
    assert len(body) == CONTAINER_BYTES


def test_announce_leaves_state_files_unchanged(served):
    live, server = served
    poll(server, live)
    baseline = read_state_files(live.state_dir)
    poll(server, live, {"X-Img-Fmt": "1"})
    assert read_state_files(live.state_dir) == baseline


def test_announce_uses_the_shared_container_encoder():
    spec = importlib.util.spec_from_file_location(
        "byos_server_negotiation", os.path.join(HERE, "byos_server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.image_container.encode_container is image_container.encode_container
    assert module.image_container.negotiate_version is image_container.negotiate_version
