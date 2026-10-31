"""Seed and request helpers for the Fleet page and pairing handler tests.

No pytest import. Every code, secret and MAC here is a made-up test value;
no real pairing code or enrolment secret may appear in this file.
"""
import hashlib
import time

from companion_app_server import (
    http_request, http_request_full, session_cookie_for_state_dir, with_csrf)
from server import fleet_db, fleet_ops, hardware, pairing_code

ADMIN_EMAIL = "admin@example.test"
OWNER_EMAIL = "owner@example.test"
SECOND_ADMIN_EMAIL = "admin2@example.test"
USER_EMAIL = "plain@example.test"

SECRET_HASH = hashlib.sha256(b"fake-enrolment-secret").hexdigest()
FAKE_CODE = "ABCD2345"
OTHER_FAKE_CODE = "EFGH6789"
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")

MAC_LIVE = "aa:bb:cc:00:00:01"
MAC_OWNED = "aa:bb:cc:00:00:02"
MAC_PENDING = "aa:bb:cc:00:00:03"
MAC_RETIRED = "aa:bb:cc:00:00:04"
MAC_NEW = "aa:bb:cc:00:00:05"


class Seed:
    """Ids of what `seed_fleet` wrote."""

    def __init__(self, **ids):
        self.__dict__.update(ids)


def seed_users(state_dir):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        return Seed(
            admin_id=fleet_db.add_user(conn, ADMIN_EMAIL, "admin"),
            owner_id=fleet_db.add_user(conn, OWNER_EMAIL, "user"),
            admin2_id=fleet_db.add_user(conn, SECOND_ADMIN_EMAIL, "admin"),
            user_id=fleet_db.add_user(conn, USER_EMAIL, "user"))
    finally:
        conn.close()


def seed_fleet(state_dir):
    """Users plus a live frame, an owned frame, a pending frame and a
    retired frame."""
    seed = seed_users(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        seed.live_id = fleet_db.add_device(
            conn, MAC_LIVE, SECRET_HASH, hardware.LEGACY_KEY, seed.admin_id,
            name="Orly frame", state_path=".")
        seed.owned_id = fleet_db.add_device(
            conn, MAC_OWNED, SECRET_HASH, hardware.LEGACY_KEY, seed.owner_id,
            name="Kitchen", state_path="auto")
        seed.pending_id = fleet_ops.register_frame(
            conn, MAC_PENDING, SECRET_HASH, hardware.LEGACY_KEY, ACTOR)
        retire_me = fleet_db.add_device(
            conn, MAC_RETIRED, SECRET_HASH, hardware.LEGACY_KEY, seed.owner_id,
            name="Attic", state_path="auto")
        seed.retired_device_id = retire_me
        seed.retired_id = fleet_db.park_retired(conn, retire_me, int(time.time()))
    finally:
        conn.close()
    return seed


def issue_code(state_dir, pending_id, code=FAKE_CODE, ttl_s=600):
    """Give the pending frame a pairing code expiring `ttl_s` from now
    (negative for an expired one)."""
    conn = fleet_db.connect(state_dir)
    try:
        salt = pairing_code.new_salt()
        fleet_db.issue_pending_code(
            conn, pending_id, salt, pairing_code.hash_code(salt, code),
            int(time.time()) + ttl_s)
    finally:
        conn.close()


def admin_cookie(state_dir, email=ADMIN_EMAIL):
    return session_cookie_for_state_dir(state_dir, email=email, role="admin")


def user_cookie(state_dir, email=USER_EMAIL):
    return session_cookie_for_state_dir(state_dir, email=email, role="user")


def get(server, cookie, path, headers=None):
    status, headers, body = http_request(
        server.url(path), cookie=cookie, extra_headers=headers)
    return status, headers, body.decode("utf-8")


def post(server, cookie, path, form):
    """POST `form` with the session's anti-forgery token."""
    status, headers, body = http_request(
        server.url(path), "POST", data=with_csrf(cookie, form), cookie=cookie)
    return status, headers, body.decode("utf-8")


def post_full(server, cookie, path, form):
    status, headers, body = http_request_full(
        server.url(path), "POST", data=with_csrf(cookie, form), cookie=cookie)
    return status, headers, body.decode("utf-8")


def dump_database_text(state_dir):
    """Every value of every row of `audit_log` and `pending_devices`, as one
    string, for "this value is stored nowhere" assertions."""
    conn = fleet_db.connect(state_dir)
    try:
        parts = []
        for table in ("audit_log", "pending_devices"):
            for row in conn.execute("SELECT * FROM %s" % table):
                parts.extend(str(value) for value in tuple(row))
        return "\n".join(parts)
    finally:
        conn.close()


def audit_rows(state_dir, action=None):
    conn = fleet_db.connect(state_dir)
    try:
        rows = [dict(row) for row in conn.execute("SELECT * FROM audit_log ORDER BY id")]
    finally:
        conn.close()
    return [row for row in rows if action is None or row["action"] == action]
