#!/usr/bin/env python3
"""Freeze-safety siblings for pending and retired frames.

stub-server/test_phase47_freeze.py and measured_fields_freeze.json stay as
they are; these tests prove that registering pending or retired frames in
fleet.db changes nothing the live frame measures: its display response, its
image hash, its sleep_s and the set of files its polls write.
"""
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state, snapshot_dir  # noqa: E402

from server import fleet_db, fleet_migrate, fleet_ops, hardware  # noqa: E402

FREEZE_PATH = os.path.join(HERE, "measured_fields_freeze.json")
OWNER_EMAIL = "owner@example.com"
ACTOR = fleet_db.AuditActor(None, "test", None)
POLL_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
}
PENDING_MAC = "aa:bb:cc:00:11:22"
RETIRED_MAC = "aa:bb:cc:00:11:33"
PENDING_SECRET_HEX = "cd" * 32
RETIRED_SECRET_HEX = "ef" * 32
LEGACY_FILES = ("devices.json", "byos_state.json")
# Written by a poll whatever fleet.db holds: the harness log, fleet.db
# bookkeeping and the live frame's own telemetry files.
NOISE = ("byos.stdout.log",)


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _freeze_keys():
    with open(FREEZE_PATH, encoding="utf-8") as fh:
        return json.load(fh)["display_response_keys"]["keys"]


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _seed(state_dir, with_pending):
    live = seed_live_like_state(state_dir)
    fleet_migrate.migrate(state_dir, OWNER_EMAIL, dry_run=False)
    if with_pending:
        conn = fleet_db.connect(state_dir, create=False)
        try:
            fleet_ops.register_frame(
                conn, PENDING_MAC, _sha(PENDING_SECRET_HEX), hardware.LEGACY_KEY, ACTOR)
            retired = fleet_ops.register_frame(
                conn, RETIRED_MAC, _sha(RETIRED_SECRET_HEX), hardware.LEGACY_KEY, ACTOR)
            with fleet_db.transaction(conn):
                conn.execute(
                    "UPDATE pending_devices SET status = 'retired' WHERE id = ?",
                    (retired,))
        finally:
            conn.close()
    return live


def _live_poll(state_dir, with_pending):
    live = _seed(state_dir, with_pending)
    before = snapshot_dir(state_dir)
    server = FrameServer(state_dir)
    server.start()
    try:
        status, doc = server.display(live.token, POLL_HEADERS)
    finally:
        server.stop()
    after = snapshot_dir(state_dir)
    changed = {n for n in after if before.get(n) != after[n]}
    return status, doc, changed - set(NOISE)


def test_live_frame_unchanged_by_pending_and_retired_rows(tmp_path):
    plain = str(tmp_path / "plain")
    mixed = str(tmp_path / "mixed")
    status_a, doc_a, changed_a = _live_poll(plain, with_pending=False)
    status_b, doc_b, changed_b = _live_poll(mixed, with_pending=True)
    assert status_a == status_b == 200
    assert sorted(doc_b) == sorted(_freeze_keys())
    assert doc_b["image_hash"] == doc_a["image_hash"]
    assert doc_b["sleep_s"] == doc_a["sleep_s"]
    assert doc_b["image_url"].split("/", 3)[3] == doc_a["image_url"].split("/", 3)[3]
    assert changed_b == changed_a
    assert not any(n.startswith("pairing") for n in changed_b)


@pytest.fixture
def pending_world(tmp_path):
    state_dir = str(tmp_path)
    live = _seed(state_dir, with_pending=True)
    server = FrameServer(state_dir)
    server.start()
    yield state_dir, live, server
    server.stop()


def test_pending_and_retired_answers_have_the_live_keys(pending_world):
    state_dir, live, server = pending_world
    status, live_doc = server.display(live.token, POLL_HEADERS)
    assert status == 200
    keys = sorted(live_doc)
    assert keys == sorted(_freeze_keys())
    for mac, secret in ((PENDING_MAC, PENDING_SECRET_HEX),
                        (RETIRED_MAC, RETIRED_SECRET_HEX)):
        status, doc = server.setup(mac, secret)
        assert status == 200
        status, answer = server.display(doc["device_token"], POLL_HEADERS)
        assert status == 200
        assert sorted(answer) == keys
        assert answer["firmware"] is None and answer["reset"] is False
        assert answer["image_hash"].startswith("sha256:")


def test_pending_enrol_and_display_write_no_legacy_or_root_image(pending_world):
    state_dir, live, server = pending_world
    legacy_before = {n: _read(os.path.join(state_dir, n)) for n in LEGACY_FILES}
    img_before = os.path.exists(os.path.join(state_dir, "img"))
    status, doc = server.setup(PENDING_MAC, PENDING_SECRET_HEX)
    assert status == 200
    for _ in range(2):
        status, _ = server.display(doc["device_token"], POLL_HEADERS)
        assert status == 200
    assert {n: _read(os.path.join(state_dir, n)) for n in LEGACY_FILES} == legacy_before
    assert os.path.exists(os.path.join(state_dir, "img")) == img_before
    assert not img_before
    assert os.listdir(os.path.join(state_dir, "pairing"))
