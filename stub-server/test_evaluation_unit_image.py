#!/usr/bin/env python3
"""The evaluation unit's hardware type through a real BYOS subprocess: a
device of that type is served exactly one 800x480 packed frame whose hash
matches, the live frame keeps its legacy answer, and with the gate off the
unit is refused instead of being handed the wrong image."""
import hashlib
import os
import sys
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, HERE, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skypane_frame_server import FrameServer  # noqa: E402
from skypane_two_device_fleet import device_headers, seed_two_device_fleet  # noqa: E402

from server import hardware  # noqa: E402

SIM_ENV = {hardware.SIM_ENV_VAR: "1"}
EVALUATION_BYTES = 192000
LIVE_BYTES = 960000


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")


@pytest.fixture
def fleet(tmp_path):
    return seed_two_device_fleet(
        str(tmp_path), with_landscape=True, landscape_type=hardware.EVALUATION_KEY)


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _poll(server, device):
    headers = dict(device_headers(device))
    headers.pop("Authorization")
    return server.display(device.token, headers)


def _panel(device):
    with open(os.path.join(device.state_dir, "panel.bin"), "rb") as fh:
        return fh.read()


def _fetch(server, doc):
    return _get(server.base_url + "/" + doc["image_url"].split("/", 3)[3])


def test_evaluation_unit_is_served_a_192000_byte_image_with_matching_hash(fleet):
    unit = fleet.landscape
    assert unit.hardware_type == hardware.EVALUATION_KEY
    server = FrameServer(fleet.live.state_dir, env_overrides=SIM_ENV)
    server.start()
    try:
        live_status, live_before = _poll(server, fleet.live)
        status, doc = _poll(server, unit)
        assert status == 200, doc
        assert doc["image_url"] and doc["image_hash"]
        fetched_status, body = _fetch(server, doc)
        live_status_after, live_after = _poll(server, fleet.live)
        live_fetch = _fetch(server, live_after)
    finally:
        server.stop()
    assert fetched_status == 200
    assert len(body) == EVALUATION_BYTES
    assert body == _panel(unit)
    assert doc["image_hash"] == "sha256:" + hashlib.sha256(body).hexdigest()
    assert (live_status, live_status_after) == (200, 200)
    assert live_after["image_hash"] == live_before["image_hash"]
    assert live_fetch[0] == 200
    assert len(live_fetch[1]) == LIVE_BYTES
    assert live_fetch[1] == _panel(fleet.live)


def test_evaluation_unit_is_refused_when_the_gate_is_off(fleet):
    server = FrameServer(
        fleet.live.state_dir, env_overrides={hardware.SIM_ENV_VAR: "0"})
    server.start()
    try:
        status, doc = _poll(server, fleet.landscape)
        live_status, _ = _poll(server, fleet.live)
    finally:
        server.stop()
    assert status == 503
    assert "image_url" not in doc
    assert live_status == 200
