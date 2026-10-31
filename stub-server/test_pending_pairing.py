#!/usr/bin/env python3
"""A registered but unassigned (pending) frame and a retired frame through a
real byos_server.py subprocess: enrolment, the pairing and retired screens,
code rotation, claim hand-over, and isolation from the live frame's state."""
import hashlib
import json
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

import byos_server  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state, snapshot_dir  # noqa: E402

from server import (  # noqa: E402
    fleet_db, fleet_migrate, fleet_ops, hardware, image_container,
    pairing_code,
)

OWNER_EMAIL = "owner@example.com"
PENDING_MAC = "aa:bb:cc:00:11:22"
PENDING_SECRET_HEX = "ab" * 32
PENDING_SECRET_SHA = hashlib.sha256(PENDING_SECRET_HEX.encode()).hexdigest()
FAKE_CODE = "ABCD2345"
ACTOR = fleet_db.AuditActor(None, "test", None)
SIX_KEYS = {"image_url", "image_hash", "sleep_s", "firmware", "reset", "led_enabled"}
HEADERS = {"X-Battery-Mv": "3900", "X-Fw-Version": "1.0.0"}


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _path_of(url):
    return "/" + url.split("/", 3)[3]


def _db(state_dir):
    conn = fleet_db.connect(state_dir, create=False)
    return conn


class World:
    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.live = seed_live_like_state(state_dir)
        fleet_migrate.migrate(state_dir, OWNER_EMAIL, dry_run=False)
        conn = _db(state_dir)
        try:
            self.pending_id = fleet_ops.register_frame(
                conn, PENDING_MAC, PENDING_SECRET_SHA, hardware.LEGACY_KEY, ACTOR)
            owner = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
            self.owner_id = int(owner["id"])
        finally:
            conn.close()
        self.server = FrameServer(state_dir)
        self.server.start()
        self.token = None

    def enrol(self):
        status, doc = self.server.setup(PENDING_MAC, PENDING_SECRET_HEX)
        assert status == 200
        self.token = doc["device_token"]
        return self.token

    def poll(self, headers=None):
        hdrs = dict(HEADERS)
        hdrs.update(headers or {})
        return self.server.display(self.token, hdrs)

    def row(self):
        conn = _db(self.state_dir)
        try:
            return conn.execute(
                "SELECT * FROM pending_devices WHERE id = ?", (self.pending_id,)
            ).fetchone()
        finally:
            conn.close()

    def sql(self, statement, params=()):
        conn = _db(self.state_dir)
        try:
            with fleet_db.transaction(conn):
                conn.execute(statement, params)
        finally:
            conn.close()

    def audit_actions(self):
        conn = _db(self.state_dir)
        try:
            return [(r["action"], r["actor_label"], r["outcome"])
                    for r in conn.execute("SELECT * FROM audit_log ORDER BY id")]
        finally:
            conn.close()


@pytest.fixture
def world(tmp_path):
    w = World(str(tmp_path))
    yield w
    w.server.stop()


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _fetch_image(world, doc):
    status, body = _get(world.server.base_url + _path_of(doc["image_url"]))
    assert status == 200
    return body


def test_pending_enrol_stores_token_in_fleet_db_only(world):
    legacy = (os.path.join(world.state_dir, "byos_state.json"),
              os.path.join(world.state_dir, "devices.json"))
    before = [_bytes(p) for p in legacy]
    status, _ = world.server.setup(PENDING_MAC, "00" * 32)
    assert status == 401
    status, _ = world.server.setup("aa:bb:cc:99:99:99", PENDING_SECRET_HEX)
    assert status == 403
    token = world.enrol()
    assert world.row()["token"] == token
    assert [_bytes(p) for p in legacy] == before


def test_pending_display_serves_pairing_image(world):
    world.enrol()
    status, doc = world.poll()
    assert status == 200
    assert set(doc) == SIX_KEYS
    assert doc["sleep_s"] == pairing_code.PENDING_SLEEP_S == 300
    assert doc["firmware"] is None and doc["reset"] is False
    assert doc["image_url"].startswith("http://127.0.0.1:")
    assert _path_of(doc["image_url"]).startswith("/img/" + world.pending_id + "/")
    body = _fetch_image(world, doc)
    assert len(body) == 960000
    assert "sha256:" + hashlib.sha256(body).hexdigest() == doc["image_hash"]
    assert world.audit_actions().count(
        ("pairing.issue", "frame:" + world.pending_id, "ok")) == 1
    row = world.row()
    assert row["code_hash"] is not None and row["code_expires_at"] is not None


def test_code_is_stable_then_rotates_after_expiry(world):
    world.enrol()
    _, first = world.poll()
    _, again = world.poll()
    assert again["image_hash"] == first["image_hash"]
    issues = [a for a in world.audit_actions() if a[0] == "pairing.issue"]
    assert len(issues) == 1
    world.sql("UPDATE pending_devices SET code_expires_at = 1 WHERE id = ?",
              (world.pending_id,))
    _, rotated = world.poll()
    assert rotated["image_hash"] != first["image_hash"]
    issues = [a for a in world.audit_actions() if a[0] == "pairing.issue"]
    assert len(issues) == 2


def test_container_is_served_when_announced(world):
    world.enrol()
    _, raw_doc = world.poll()
    raw = _fetch_image(world, raw_doc)
    _, doc = world.poll({"X-Img-Fmt": "1"})
    wrapped = _fetch_image(world, doc)
    view = image_container.decode_container(wrapped, 1200, 1600)
    assert wrapped != raw
    assert view is not None


def test_retired_frame_and_reactivation(world):
    world.enrol()
    world.sql("UPDATE pending_devices SET status = 'retired', retired_at = 5 "
              "WHERE id = ?", (world.pending_id,))
    status, doc = world.poll()
    assert status == 200 and set(doc) == SIX_KEYS
    assert doc["sleep_s"] == pairing_code.RETIRED_SLEEP_S == 86400
    retired_hash = doc["image_hash"]
    assert len(_fetch_image(world, doc)) == 960000
    assert world.row()["token"] == world.token
    conn = _db(world.state_dir)
    try:
        fleet_ops.reactivate_frame(conn, world.state_dir, world.pending_id, ACTOR)
    finally:
        conn.close()
    status, doc = world.poll()
    assert status == 200
    assert doc["sleep_s"] == 300
    assert doc["image_hash"] != retired_hash
    assert world.row()["code_hash"] is not None


def test_claim_hands_the_token_to_a_normal_device(world):
    world.enrol()
    _, pairing_doc = world.poll()
    salt = pairing_code.new_salt()
    world.sql(
        "UPDATE pending_devices SET code_salt = ?, code_hash = ?, "
        "code_expires_at = 4102444800 WHERE id = ?",
        (salt, pairing_code.hash_code(salt, FAKE_CODE), world.pending_id))
    conn = _db(world.state_dir)
    try:
        result = fleet_ops.claim_pairing_code(
            conn, world.state_dir, FAKE_CODE, world.owner_id, ACTOR)
    finally:
        conn.close()
    status, doc = world.poll()
    assert status == 200
    assert set(doc) == SIX_KEYS
    assert _path_of(doc["image_url"]).startswith("/img/" + result.device_id + "/")
    assert doc["image_hash"] != pairing_doc["image_hash"]
    status, _ = _get(world.server.base_url + _path_of(pairing_doc["image_url"]))
    assert status == 404


def test_pending_frames_leave_live_state_alone(world):
    world.enrol()
    live_before = snapshot_dir(world.state_dir)
    for _ in range(3):
        world.poll()
    after = snapshot_dir(world.state_dir)
    changed = {name for name in after if live_before.get(name) != after[name]}
    allowed_prefixes = ("pairing" + os.sep,)
    allowed = {"fleet.db", "fleet.db-wal", "fleet.db-shm", "fleet_status.json",
               "byos.stdout.log"}
    unexpected = {n for n in changed
                  if n not in allowed and not n.startswith(allowed_prefixes)}
    assert unexpected == set()
    assert not any(n.startswith("img" + os.sep) for n in after)
    assert not os.path.exists(os.path.join(world.state_dir, "devices"))
    for name in ("battery_state.json", "poll_state.json"):
        assert after[name] == live_before[name]


def test_pending_image_route_rejects_bad_paths(world):
    world.enrol()
    _, doc = world.poll()
    good = _path_of(doc["image_url"])
    base = world.server.base_url
    assert _get(base + good)[0] == 200
    digest = doc["image_hash"].split(":")[1]
    for bad in (
        "/img/p_zzzzzzzz/%s.bin" % digest,
        "/img/p_%s/%s.bin" % ("0" * 8, digest),
        "/img/%s/%s.bin" % (world.pending_id, digest.upper()),
        "/img/%s/../%s.bin" % (world.pending_id, digest),
        "/img/%s/%s.bin?x=1" % (world.pending_id, digest),
        "/img/%s/%s" % (world.pending_id, digest),
        "/img/%s/%s.bin" % (world.pending_id, "0" * 64),
    ):
        assert _get(base + bad)[0] == 404, bad


def test_legacy_mirror_refuses_a_pending_mac(world):
    conn = _db(world.state_dir)
    try:
        with fleet_db.transaction(conn):
            with pytest.raises(ValueError):
                byos_server._apply_mirror(conn, "add", PENDING_MAC, PENDING_SECRET_SHA)
        count = conn.execute(
            "SELECT count(*) FROM devices WHERE mac = ?", (PENDING_MAC,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0
    assert byos_server.mirror_to_fleet(
        world.state_dir, "add", PENDING_MAC, PENDING_SECRET_SHA) is not None


def test_database_never_holds_the_plaintext_code(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    seed_live_like_state(state_dir)
    fleet_migrate.migrate(state_dir, OWNER_EMAIL, dry_run=False)
    conn = _db(state_dir)
    try:
        pid = fleet_ops.register_frame(
            conn, PENDING_MAC, PENDING_SECRET_SHA, hardware.LEGACY_KEY, ACTOR)
        row = fleet_db.get_pending(conn, pid)
    finally:
        conn.close()
    monkeypatch.setattr(pairing_code, "generate_code", lambda: FAKE_CODE)
    profile = hardware.get_profile(hardware.LEGACY_KEY, os.environ)
    image, sleep_s = byos_server._pending_panel(
        state_dir, row, profile, 1000, None, None)
    assert sleep_s == 300 and len(image) == 960000
    blob = b""
    for name in os.listdir(state_dir):
        if name.startswith("fleet.db"):
            blob += _bytes(os.path.join(state_dir, name))
    assert FAKE_CODE.encode() not in blob
    assert pairing_code.format_code(FAKE_CODE).encode() not in blob
    conn = _db(state_dir)
    try:
        stored = fleet_db.get_pending(conn, pid)
        assert stored["code_hash"] == pairing_code.hash_code(
            stored["code_salt"], FAKE_CODE)
        detail = conn.execute(
            "SELECT detail FROM audit_log WHERE action = 'pairing.issue'"
        ).fetchone()["detail"]
    finally:
        conn.close()
    assert FAKE_CODE not in detail
    panel = os.path.join(state_dir, "pairing", pid, "panel.bin")
    assert oct(os.stat(panel).st_mode & 0o777) == oct(0o600)


def test_unknown_token_and_missing_pending_row_are_401(world):
    world.enrol()
    assert world.server.display("not-a-token", HEADERS)[0] == 401
    world.sql("DELETE FROM pending_devices WHERE id = ?", (world.pending_id,))
    assert world.poll()[0] == 401


def test_response_carries_no_secret_or_token(world):
    world.enrol()
    _, doc = world.poll()
    text = json.dumps(doc)
    assert PENDING_SECRET_SHA not in text and world.token not in text
