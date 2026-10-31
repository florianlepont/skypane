#!/usr/bin/env python3
"""Tests for server.fleet_ops: register, claim, retire, re-activate, reassign."""
import contextlib
import hmac
import os
import threading

import pytest
import skypane_live_state as live

import server.fleet_db as fleet_db
from server import device_dirs, fleet_ops, hardware, pairing_code, panel_format

SECRET = "ab" * 32
MAC = "aa:bb:cc:dd:ee:01"
MAC2 = "aa:bb:cc:dd:ee:02"
CODE = "ABCD2345"
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")
HW = hardware.LEGACY_KEY
WHITE_BYTE = (panel_format.WHITE << 4) | panel_format.WHITE
PANEL_BYTES = (hardware.REGISTRY[HW].width // 2) * hardware.REGISTRY[HW].height


@pytest.fixture
def root(tmp_path):
    return str(tmp_path)


@pytest.fixture
def conn(root):
    c = fleet_db.connect(root)
    yield c
    c.close()


@pytest.fixture
def owner(conn):
    return fleet_db.add_user(conn, "owner@example.test", "admin")


def _issue(conn, pending_id, code=CODE, expires=None, now=1000):
    salt = pairing_code.new_salt()
    fleet_db.issue_pending_code(
        conn, pending_id, salt, pairing_code.hash_code(salt, code),
        now + 600 if expires is None else expires,
    )


def _pending(conn, mac=MAC, code=CODE, token=None, **kw):
    pid = fleet_ops.register_frame(conn, mac, SECRET, HW, ACTOR)
    if token:
        fleet_db.set_pending_token(conn, mac, token)
    if code:
        _issue(conn, pid, code, **kw)
    return pid


def _audit_rows(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id")]


# ---- Task 1: register --------------------------------------------------


def test_register_normalises_and_audits(conn):
    pid = fleet_ops.register_frame(conn, "AA:BB:CC:DD:EE:01", SECRET, HW, ACTOR)
    row = fleet_db.get_pending(conn, pid)
    assert row["mac"] == MAC and row["status"] == "pending"
    assert conn.execute("SELECT token FROM pending_devices").fetchone()[0] is None
    audit = _audit_rows(conn)
    assert [a["action"] for a in audit] == ["frame.register"]
    assert audit[0]["target_id"] == pid and audit[0]["outcome"] == "ok"
    assert SECRET not in repr(audit)


@pytest.mark.parametrize(
    "mac,secret,hw",
    [
        ("nope", SECRET, HW),
        (MAC, "short", HW),
        (MAC, "AB" * 32, HW),
        (MAC, "plaintext-secret", HW),
        (MAC, SECRET, "no-such-hardware"),
    ],
)
def test_register_rejects_bad_input_and_writes_nothing(conn, mac, secret, hw):
    with pytest.raises(ValueError):
        fleet_ops.register_frame(conn, mac, secret, hw, ACTOR)
    assert fleet_db.list_pending(conn) == []
    assert _audit_rows(conn) == []


def test_register_duplicate_mac_pending_or_device(conn, owner):
    fleet_ops.register_frame(conn, MAC, SECRET, HW, ACTOR)
    with pytest.raises(fleet_ops.DuplicateFrame):
        fleet_ops.register_frame(conn, MAC, SECRET, HW, ACTOR)
    fleet_db.add_device(conn, MAC2, SECRET, HW, owner)
    with pytest.raises(fleet_ops.DuplicateFrame):
        fleet_ops.register_frame(conn, MAC2, SECRET, HW, ACTOR)


# ---- Task 1: claim ------------------------------------------------------


def test_claim_creates_device_dir_and_audit(conn, root, owner):
    pid = _pending(conn, token="tok-fake")
    os.makedirs(fleet_ops.pairing_dir(root, pid))
    res = fleet_ops.claim_pairing_code(conn, root, "abcd-2345", owner, ACTOR, now=1000)
    assert res.pending_id == pid and res.owner_user_id == owner
    assert fleet_db.get_pending(conn, pid) is None
    dev = conn.execute("SELECT * FROM devices WHERE id = ?", (res.device_id,)).fetchone()
    assert (dev["mac"], dev["secret_sha256"], dev["hardware_type"], dev["token"]) == (
        MAC, SECRET, HW, "tok-fake")
    assert dev["owner_user_id"] == owner
    assert dev["state_path"] == "devices/" + res.device_id
    directory = os.path.join(root, "devices", res.device_id)
    assert os.path.isfile(os.path.join(directory, "device_config.json"))
    panel = open(os.path.join(directory, "panel.bin"), "rb").read()
    assert len(panel) == PANEL_BYTES and set(panel) == {WHITE_BYTE}
    claim = [a for a in _audit_rows(conn) if a["action"] == "pairing.claim"]
    assert len(claim) == 1 and claim[0]["outcome"] == "ok"
    assert claim[0]["target_id"] == res.device_id
    assert not os.path.exists(fleet_ops.pairing_dir(root, pid))
    assert CODE not in repr(_audit_rows(conn))


def test_claim_race_has_exactly_one_winner(conn, root, owner):
    _pending(conn)
    barrier = threading.Barrier(2)
    results = []

    def worker():
        c = fleet_db.connect(root)
        try:
            barrier.wait()
            try:
                results.append(fleet_ops.claim_pairing_code(c, root, CODE, owner, ACTOR, now=1000))
            except fleet_ops.ClaimRefused as exc:
                results.append(exc)
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wins = [r for r in results if isinstance(r, fleet_ops.ClaimResult)]
    refused = [r for r in results if isinstance(r, fleet_ops.ClaimRefused)]
    assert len(wins) == 1 and len(refused) == 1
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 1
    assert os.listdir(os.path.join(root, "devices")) == [wins[0].device_id]


def _claim_outcome(conn, root, owner, text, monkeypatch):
    calls = []
    real = hmac.compare_digest

    def counting(a, b):
        calls.append(1)
        return real(a, b)

    monkeypatch.setattr(pairing_code.hmac, "compare_digest", counting)
    try:
        fleet_ops.claim_pairing_code(conn, root, text, owner, ACTOR, now=1000)
    except fleet_ops.ClaimRefused as exc:
        return type(exc), str(exc), len(calls)
    return None, "", len(calls)


def test_refusals_are_indistinguishable(conn, root, owner, monkeypatch):
    _pending(conn, mac=MAC, code=CODE)
    _pending(conn, mac=MAC2, code="WXYZ6789", expires=500)  # expired at now=1000
    outcomes = {
        "wrong": _claim_outcome(conn, root, owner, "ZZZZ2222", monkeypatch),
        "expired": _claim_outcome(conn, root, owner, "WXYZ6789", monkeypatch),
        "shape": _claim_outcome(conn, root, owner, "x", monkeypatch),
    }
    fleet_ops.claim_pairing_code(conn, root, CODE, owner, ACTOR, now=1000)
    outcomes["used"] = _claim_outcome(conn, root, owner, CODE, monkeypatch)
    types_msgs = {(t, m) for t, m, _ in outcomes.values()}
    assert types_msgs == {(fleet_ops.ClaimRefused, "pairing code not accepted")}
    # Two pending rows while scanning, one after the winner left: a refusal
    # scans every row exactly like a valid claim does.
    assert outcomes["wrong"][2] == outcomes["expired"][2] == outcomes["shape"][2] == 2
    assert outcomes["used"][2] == 1


def test_unavailable_owner_keeps_code_valid(conn, root, owner):
    pid = _pending(conn)
    gone = fleet_db.add_user(conn, "gone@example.test", "user")
    fleet_db.set_user_disabled(conn, "gone@example.test", True)
    for bad in (gone, 9999):
        with pytest.raises(fleet_ops.OwnerUnavailable):
            fleet_ops.claim_pairing_code(conn, root, CODE, bad, ACTOR, now=1000)
    assert fleet_db.get_pending(conn, pid) is not None
    assert not os.path.exists(os.path.join(root, "devices"))
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 0
    fleet_ops.claim_pairing_code(conn, root, CODE, owner, ACTOR, now=1000)


def test_audit_failure_rolls_back_and_removes_directory(conn, root, owner, monkeypatch):
    pid = _pending(conn)

    def boom(*_a, **_k):
        raise RuntimeError("audit down")

    monkeypatch.setattr(fleet_db, "audit_append", boom)
    with pytest.raises(RuntimeError):
        fleet_ops.claim_pairing_code(conn, root, CODE, owner, ACTOR, now=1000)
    assert fleet_db.get_pending(conn, pid) is not None
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 0
    devices = os.path.join(root, "devices")
    assert not os.path.isdir(devices) or os.listdir(devices) == []


def test_record_claim_failure_never_stores_the_guess(conn, root, owner):
    guess = "DISTINCT-GUESS-xyz"
    _pending(conn)
    with pytest.raises(fleet_ops.ClaimRefused):
        fleet_ops.claim_pairing_code(conn, root, guess, owner, ACTOR, now=1000)
    fleet_ops.record_claim_failure(conn, ACTOR, fleet_ops.FAIL_INVALID)
    fleet_ops.record_claim_failure(conn, ACTOR, fleet_ops.FAIL_THROTTLED)
    rows = _audit_rows(conn)
    assert [(r["action"], r["outcome"]) for r in rows] == [
        ("frame.register", "ok"), ("pairing.claim", "failed"), ("pairing.claim", "failed")]
    assert "invalid" in rows[1]["detail"] and "throttled" in rows[2]["detail"]
    dump = "\n".join(str(tuple(r.values())) for r in rows).lower()
    assert guess.lower() not in dump and "distinct" not in dump
    with pytest.raises(ValueError):
        fleet_ops.record_claim_failure(conn, ACTOR, guess)


def test_pairing_dir_validates_id(root):
    assert fleet_ops.pairing_dir(root, "p_0123abcd").endswith("pairing/p_0123abcd")
    with pytest.raises(ValueError):
        fleet_ops.pairing_dir(root, "../etc")


# ---- Task 2: reassign, retire, re-activate -----------------------------

OTHER_FILES = (
    "calendar_url.secret", "history.db", "poll_state.json",
    "airline_name_overrides.json", "gallery/img1.png",
    "illustration_overrides/a.png",
)


def _claimed(conn, root, owner, mac=MAC, code=CODE, token="tok-fake"):
    _pending(conn, mac=mac, code=code, token=token)
    res = fleet_ops.claim_pairing_code(conn, root, code, owner, ACTOR, now=1000)
    directory = os.path.join(root, "devices", res.device_id)
    for rel in OTHER_FILES:
        full = os.path.join(directory, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(b"previous owner data")
    loc = fleet_db.add_location(conn, "Home", 48.7, 2.4, "Europe/Paris")
    conn.execute(
        "UPDATE devices SET location_id = ?, name = ? WHERE id = ?",
        (loc, "Kitchen", res.device_id),
    )
    return res.device_id, directory


def _second_user(conn):
    return fleet_db.add_user(conn, "second@example.test", "user")


def _live_device(conn, root, owner):
    ns = live.seed_live_like_state(root)
    did = fleet_db.add_device(conn, ns.mac, SECRET, HW, owner, token="live-tok")
    return did


def _tree(root):
    snap = live.snapshot_dir(root)
    return {k: v for k, v in snap.items() if not k.startswith("fleet.db")}


def test_reassign_wipes_and_keeps_identity(conn, root, owner):
    new_owner = _second_user(conn)
    did, directory = _claimed(conn, root, owner)
    before = dict(conn.execute("SELECT * FROM devices WHERE id = ?", (did,)).fetchone())
    fleet_ops.reassign_frame(conn, root, did, new_owner, ACTOR)
    after = dict(conn.execute("SELECT * FROM devices WHERE id = ?", (did,)).fetchone())
    assert after["owner_user_id"] == new_owner
    assert after["location_id"] is None and after["name"] is None
    for key in ("mac", "secret_sha256", "token", "state_path", "hardware_type"):
        assert after[key] == before[key]
    assert sorted(os.listdir(directory)) == ["device_config.json", "panel.bin"]
    assert open(os.path.join(directory, "device_config.json")).read().strip() == "{}"
    assert os.path.getsize(os.path.join(directory, "panel.bin")) == PANEL_BYTES
    row = [a for a in _audit_rows(conn) if a["action"] == "device.reassign"][0]
    assert row["outcome"] == "ok"
    assert f'"new_owner_user_id": {new_owner}' in row["detail"]
    assert f'"old_owner_user_id": {owner}' in row["detail"]


def test_reassign_live_frame_changes_only_owner(conn, root, owner, monkeypatch):
    new_owner = _second_user(conn)
    did = _live_device(conn, root, owner)
    loc = fleet_db.add_location(conn, "Orly", 48.7, 2.4, "Europe/Paris")
    conn.execute("UPDATE devices SET location_id = ?, name = ? WHERE id = ?", (loc, "Wall", did))
    snapshot = _tree(root)

    def fail(*_a, **_k):
        raise AssertionError("wipe must not run for the live frame")

    monkeypatch.setattr(device_dirs, "wipe_device_dir", fail)
    fleet_ops.reassign_frame(conn, root, did, new_owner, ACTOR)
    assert _tree(root) == snapshot
    dev = conn.execute("SELECT * FROM devices WHERE id = ?", (did,)).fetchone()
    assert dev["owner_user_id"] == new_owner
    assert dev["location_id"] == loc and dev["name"] == "Wall"


def test_retire_live_frame_is_refused_and_audited(conn, root, owner):
    did = _live_device(conn, root, owner)
    snapshot = _tree(root)
    with pytest.raises(fleet_ops.LiveFrameProtected):
        fleet_ops.retire_frame(conn, root, did, ACTOR)
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 1
    assert _tree(root) == snapshot
    row = [a for a in _audit_rows(conn) if a["action"] == "device.retire"]
    assert [r["outcome"] for r in row] == ["denied"]


def test_retire_parks_row_and_keeps_data(conn, root, owner):
    did, directory = _claimed(conn, root, owner)
    before = _tree(directory)
    pid = fleet_ops.retire_frame(conn, root, did, ACTOR, now=2000)
    assert fleet_db.get_device(conn, did) is None
    row = conn.execute("SELECT * FROM pending_devices WHERE id = ?", (pid,)).fetchone()
    assert (row["status"], row["mac"], row["secret_sha256"], row["token"],
            row["hardware_type"]) == ("retired", MAC, SECRET, "tok-fake", HW)
    assert row["previous_owner_user_id"] == owner
    assert row["previous_device_id"] == did
    assert row["previous_state_path"] == "devices/" + did
    assert _tree(directory) == before
    assert any(a["action"] == "device.retire" and a["outcome"] == "ok" for a in _audit_rows(conn))


def test_reactivate_wipes_previous_directory(conn, root, owner):
    did, directory = _claimed(conn, root, owner)
    pid = fleet_ops.retire_frame(conn, root, did, ACTOR)
    fleet_ops.reactivate_frame(conn, root, pid, ACTOR)
    assert not os.path.exists(directory)
    row = conn.execute("SELECT * FROM pending_devices WHERE id = ?", (pid,)).fetchone()
    assert row["status"] == "pending" and row["code_hash"] is None
    assert (row["mac"], row["secret_sha256"], row["token"]) == (MAC, SECRET, "tok-fake")
    assert any(a["action"] == "device.reactivate" for a in _audit_rows(conn))


def test_reactivate_requires_a_retired_row(conn, root, owner):
    pid = _pending(conn)
    with pytest.raises(fleet_ops.NotFound):
        fleet_ops.reactivate_frame(conn, root, pid, ACTOR)
    with pytest.raises(fleet_ops.NotFound):
        fleet_ops.reactivate_frame(conn, root, "p_00000000", ACTOR)


def test_busy_guard_blocks_every_wipe(conn, root, owner):
    new_owner = _second_user(conn)
    did, directory = _claimed(conn, root, owner)

    @contextlib.contextmanager
    def busy(_directory):
        yield False

    snapshot = _tree(root)
    db_before = fleet_db.dump_logical(conn)
    with pytest.raises(fleet_ops.FrameBusy):
        fleet_ops.reassign_frame(conn, root, did, new_owner, ACTOR, busy_guard=busy)
    pid = fleet_ops.retire_frame(conn, root, did, ACTOR)
    db_retired = fleet_db.dump_logical(conn)
    with pytest.raises(fleet_ops.FrameBusy):
        fleet_ops.reactivate_frame(conn, root, pid, ACTOR, busy_guard=busy)
    assert fleet_db.dump_logical(conn) == db_retired
    assert _tree(root) == snapshot
    assert db_before != db_retired


@pytest.mark.parametrize("failing", ["wipe_device_dir", "provision_device_dir"])
def test_failure_during_wipe_rolls_back_reassign(conn, root, owner, monkeypatch, failing):
    new_owner = _second_user(conn)
    did, _ = _claimed(conn, root, owner)

    def boom(*_a, **_k):
        raise OSError("disk")

    monkeypatch.setattr(device_dirs, failing, boom)
    with pytest.raises(OSError):
        fleet_ops.reassign_frame(conn, root, did, new_owner, ACTOR)
    dev = conn.execute("SELECT * FROM devices WHERE id = ?", (did,)).fetchone()
    assert dev["owner_user_id"] == owner and dev["name"] == "Kitchen"
    assert not [a for a in _audit_rows(conn) if a["action"] == "device.reassign"]


def test_unavailable_new_owner_before_any_wipe(conn, root, owner, monkeypatch):
    did, directory = _claimed(conn, root, owner)
    disabled = fleet_db.add_user(conn, "off@example.test", "user", disabled=True)
    snapshot = _tree(root)

    def fail(*_a, **_k):
        raise AssertionError("wipe must not run")

    monkeypatch.setattr(device_dirs, "wipe_device_dir", fail)
    for bad in (disabled, 9999):
        with pytest.raises(fleet_ops.OwnerUnavailable):
            fleet_ops.reassign_frame(conn, root, did, bad, ACTOR)
    assert _tree(root) == snapshot
