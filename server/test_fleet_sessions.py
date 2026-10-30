#!/usr/bin/env python3
"""Tests for server/fleet_sessions.py: hash-only sessions with absolute and
idle limits, fresh role/disabled reads, and invite-only identity linking."""
import hashlib
import threading

import pytest

import server.fleet_db as fleet_db
import server.fleet_sessions as fs
import server.hardware as hardware

ISS = "https://tenant.example.auth0.com/"
DAY = 86400
T0 = 1_800_000_000


@pytest.fixture
def conn():
    c = fleet_db.connect_memory()
    yield c
    c.close()


def _h(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _user(conn, email="a@example.com", role="user", **kw):
    return fleet_db.add_user(conn, email, role, **kw)


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_create_stores_hash_and_lookup_by_hash_only(conn):
    uid = _user(conn)
    fs.create_session(conn, _h("tok"), user_id=uid, principal="user", now=T0)
    rec = fs.lookup_session(conn, _h("tok"), T0 + 1)
    assert rec is not None
    assert (rec.user_id, rec.principal, rec.email, rec.role) == (
        uid, "user", "a@example.com", "user")
    assert fs.lookup_session(conn, "tok", T0 + 1) is None
    stored = [r[0] for r in conn.execute("SELECT id_hash FROM sessions")]
    assert stored == [_h("tok")]


def test_legacy_admin_session(conn):
    fs.create_session(conn, _h("l"), user_id=None, principal="legacy-admin", now=T0)
    rec = fs.lookup_session(conn, _h("l"), T0)
    assert rec is not None
    assert (rec.user_id, rec.email, rec.role) == (None, None, "admin")


def test_absolute_lifetime(conn):
    uid = _user(conn)
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    # Keep it active so only the absolute limit can end it.
    t = T0
    while t + 6 * DAY < T0 + 30 * DAY - 1:
        t += 6 * DAY
        assert fs.lookup_session(conn, _h("t"), t) is not None
    assert fs.lookup_session(conn, _h("t"), T0 + 30 * DAY - 1) is not None
    assert fs.lookup_session(conn, _h("t"), T0 + 30 * DAY) is None
    assert _count(conn, "sessions") == 0


def test_idle_timeout(conn):
    uid = _user(conn)
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    assert fs.lookup_session(conn, _h("t"), T0 + 7 * DAY + 1) is None
    assert _count(conn, "sessions") == 0


def test_last_seen_is_throttled(conn):
    uid = _user(conn)
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)

    def seen():
        return conn.execute("SELECT last_seen_at FROM sessions").fetchone()[0]

    fs.lookup_session(conn, _h("t"), T0 + 10)
    assert seen() == T0
    fs.lookup_session(conn, _h("t"), T0 + 360)
    assert seen() == T0 + 360


def test_role_and_disabled_are_read_fresh(conn):
    uid = _user(conn, role="admin")
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    conn.execute("UPDATE users SET role = 'user' WHERE id = ?", (uid,))
    rec = fs.lookup_session(conn, _h("t"), T0 + 1)
    assert rec is not None and rec.role == "user"
    fleet_db.set_user_disabled(conn, "a@example.com", True)
    assert fs.lookup_session(conn, _h("t"), T0 + 2) is None
    fleet_db.set_user_disabled(conn, "a@example.com", False)
    assert fs.lookup_session(conn, _h("t"), T0 + 3) is not None


def test_missing_user_row_refuses(conn):
    uid = _user(conn)
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    assert fs.lookup_session(conn, _h("t"), T0 + 1) is None


def test_rotation_delete_and_prune(conn):
    uid = _user(conn)
    other = _user(conn, "b@example.com")
    fs.create_session(conn, _h("old"), user_id=uid, principal="user", now=T0)
    fs.create_session(conn, _h("new"), user_id=uid, principal="user", now=T0,
                      replace_hash=_h("old"))
    assert fs.lookup_session(conn, _h("old"), T0) is None
    assert fs.lookup_session(conn, _h("new"), T0) is not None
    fs.create_session(conn, _h("o"), user_id=other, principal="user", now=T0 - 40 * DAY)
    assert fs.prune_expired(conn, T0) == 1
    assert _count(conn, "sessions") == 1
    fs.delete_session(conn, _h("new"))
    assert _count(conn, "sessions") == 0
    fs.create_session(conn, _h("a"), user_id=uid, principal="user", now=T0)
    fs.create_session(conn, _h("b"), user_id=uid, principal="user", now=T0)
    fs.create_session(conn, _h("c"), user_id=other, principal="user", now=T0)
    assert fs.delete_sessions_for_user(conn, uid) == 2
    assert _count(conn, "sessions") == 1


def test_known_sub_ignores_changed_email(conn):
    uid = _user(conn, iss=ISS, sub="s1")
    out = fs.resolve_login(conn, ISS, "s1", "changed@example.com", True, T0)
    assert out == (uid, "ok")


def test_links_once_by_verified_email(conn):
    uid = _user(conn)
    out = fs.resolve_login(conn, ISS, "s1", "A@Example.com", True, T0)
    assert out == (uid, "linked")
    assert fs.resolve_login(conn, ISS, "s1", "zzz@example.com", True, T0) == (uid, "ok")
    row = conn.execute("SELECT iss, sub FROM users WHERE id = ?", (uid,)).fetchone()
    assert (row["iss"], row["sub"]) == (ISS, "s1")


def test_refusals_insert_nothing(conn):
    uid = _user(conn)
    _user(conn, "linked@example.com", iss=ISS, sub="other")
    _user(conn, "off@example.com", disabled=True)
    _user(conn, "off2@example.com", iss=ISS, sub="offsub", disabled=True)
    before = _count(conn, "users")
    cases = [
        (("s9", "nobody@example.com", True), "unknown"),
        (("s9", "a@example.com", False), "unverified_email"),
        (("s9", "a@example.com", "true"), "unverified_email"),
        (("s9", "linked@example.com", True), "email_linked_other"),
        (("s9", "off@example.com", True), "disabled"),
        (("offsub", "x@example.com", True), "disabled"),
        (("s9", None, True), "unknown"),
        (("s9", "not-an-email", True), "unknown"),
    ]
    for (sub, email, verified), reason in cases:
        assert fs.resolve_login(conn, ISS, sub, email, verified, T0) == (None, reason)
    assert _count(conn, "users") == before
    row = conn.execute("SELECT sub FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["sub"] is None
    assert _count(conn, "sessions") == 0


def test_existing_link_untouched_by_other_sub(conn):
    uid = _user(conn, iss=ISS, sub="first")
    out = fs.resolve_login(conn, ISS, "second", "a@example.com", True, T0)
    assert out == (None, "email_linked_other")
    row = conn.execute("SELECT sub FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["sub"] == "first"


def test_unlink_identity_clears_link_and_sessions(conn):
    uid = _user(conn, iss=ISS, sub="s1")
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    assert fs.unlink_identity(conn, "A@example.com") is True
    assert _count(conn, "sessions") == 0
    assert fs.unlink_identity(conn, "a@example.com") is False
    assert fs.unlink_identity(conn, "nobody@example.com") is False
    assert fs.resolve_login(conn, ISS, "s2", "a@example.com", True, T0) == (uid, "linked")


def test_concurrent_links_to_one_email_yield_one_winner(tmp_path):
    setup = fleet_db.connect(str(tmp_path))
    _user(setup)
    setup.close()
    barrier = threading.Barrier(4)
    results = []

    def run(sub):
        c = fleet_db.connect(str(tmp_path))
        try:
            barrier.wait()
            results.append(fs.resolve_login(c, ISS, sub, "a@example.com", True, T0))
        finally:
            c.close()

    threads = [threading.Thread(target=run, args=(f"s{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r.reason for r in results) == [
        "email_linked_other", "email_linked_other", "email_linked_other", "linked"]


def test_sessions_and_linking_do_not_touch_devices(conn):
    uid = _user(conn)
    fleet_db.add_device(conn, "aa:bb:cc:dd:ee:ff", "0" * 64,
                        hardware.LEGACY_KEY, uid, token="tok")

    def devices():
        return [tuple(r) for r in conn.execute("SELECT * FROM devices")]

    before = devices()
    fs.create_session(conn, _h("t"), user_id=uid, principal="user", now=T0)
    fs.resolve_login(conn, ISS, "s1", "a@example.com", True, T0)
    fs.delete_session(conn, _h("t"))
    assert devices() == before
    assert fleet_db.registry_view(conn)["devices"]["aa:bb:cc:dd:ee:ff"]
