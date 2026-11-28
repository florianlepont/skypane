# SPDX-License-Identifier: AGPL-3.0-only
"""Seed helpers and recording stubs for the route x principal x owner matrix
in companion/test_access_matrix.py.

No pytest import. Everything here builds plain data: fleet.db rows, session
cookies and route tables whose handlers only record the request and answer
200 "reached", so a matrix request never runs a real side effect.
"""
from companion import auth, routes
from server import fleet_db, fleet_sessions, hardware

OWNER_EMAIL = "owner@example.test"
OTHER_EMAIL = "other@example.test"
ADMIN_EMAIL = "admin@example.test"

REACHED_BODY = b"reached"
PROBE_PREFIX = "/d/"
PROBE_SUFFIX = "/_probe"

_SECRET_A = "a" * 64
_SECRET_B = "b" * 64
MAC_OWNER_DEVICE = "aa:bb:cc:dd:ee:01"
MAC_OTHER_DEVICE = "aa:bb:cc:dd:ee:02"


class MatrixFleet:
    """Ids of the rows `seed_matrix_fleet` created."""

    def __init__(self, owner_id, other_id, admin_id, owner_device, other_device):
        self.owner_id = owner_id
        self.other_id = other_id
        self.admin_id = admin_id
        self.owner_device = owner_device
        self.other_device = other_device


def seed_matrix_fleet(state_dir):
    """Two users, one admin and one device per user, written to fleet.db."""
    conn = fleet_db.connect(state_dir)
    try:
        # The device routes resolve a /devices/<id> prefix only against a
        # migrated fleet.db, and each seeded device gets its own directory
        # path, as the fleet CLI's `--state-path auto` does.
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        owner_id = fleet_db.add_user(conn, OWNER_EMAIL, "user")
        other_id = fleet_db.add_user(conn, OTHER_EMAIL, "user")
        admin_id = fleet_db.add_user(conn, ADMIN_EMAIL, "admin")
        owner_device = fleet_db.add_device(
            conn, MAC_OWNER_DEVICE, _SECRET_A, hardware.LEGACY_KEY, owner_id,
            state_path="auto")
        other_device = fleet_db.add_device(
            conn, MAC_OTHER_DEVICE, _SECRET_B, hardware.LEGACY_KEY, other_id,
            state_path="auto")
    finally:
        conn.close()
    return MatrixFleet(owner_id, other_id, admin_id, owner_device, other_device)


def session_cookie_for(state_dir, principal_kind, user_id, now):
    """Write a real session row at the injected clock `now` and return the
    "sp_session=<token>" cookie pair. `principal_kind` is
    fleet_sessions.PRINCIPAL_USER; any other principal is refused by the
    database itself (sqlite3.IntegrityError) and no row is written.
    """
    token = auth.new_session_token()
    conn = fleet_db.connect(state_dir)
    try:
        fleet_sessions.create_session(
            conn, auth.hash_session_token(token),
            user_id=user_id, principal=principal_kind, now=now)
    finally:
        conn.close()
    return "%s=%s" % (auth.SESSION_COOKIE_NAME, token)


# The sessions table as schema 4 defined it, which allowed the retired
# 'legacy-admin' principal. Only `plant_legacy_session_row` uses it.
_SESSIONS_SCHEMA_4 = (
    "CREATE TABLE sessions ("
    " id_hash TEXT PRIMARY KEY,"
    " user_id INTEGER REFERENCES users(id),"
    " principal TEXT NOT NULL CHECK (principal IN ('user', 'legacy-admin')),"
    " created_at INTEGER NOT NULL,"
    " last_seen_at INTEGER NOT NULL,"
    " expires_at INTEGER NOT NULL,"
    " CHECK ((principal = 'user') = (user_id IS NOT NULL)))"
)


def plant_legacy_session_row(state_dir, now):
    """Put the sessions table of `state_dir` back into its schema 4 shape
    (empty), insert one valid-looking 'legacy-admin' row and return its
    "sp_session=<token>" cookie pair. A schema 5 database cannot hold such a
    row; this is the negative fixture proving the app still refuses it.
    """
    token = auth.new_session_token()
    conn = fleet_db.connect(state_dir)
    try:
        with fleet_db.transaction(conn):
            conn.execute("DROP TABLE sessions")
            conn.execute(_SESSIONS_SCHEMA_4)
            conn.execute("CREATE INDEX sessions_user ON sessions (user_id)")
            conn.execute("CREATE INDEX sessions_expires ON sessions (expires_at)")
            conn.execute(
                "INSERT INTO sessions VALUES (?, NULL, 'legacy-admin', ?, ?, ?)",
                (auth.hash_session_token(token), now, now,
                 now + fleet_sessions.ABSOLUTE_LIFETIME_S))
    finally:
        conn.close()
    return "%s=%s" % (auth.SESSION_COOKIE_NAME, token)


class Recorder:
    """The (method, path) of every request a stub handler served."""

    def __init__(self):
        self.calls = []

    def clear(self):
        self.calls = []


def _recording_handler(recorder):
    def handler(h, m):
        recorder.calls.append((h.command, m.path))
        h.send_response(200)
        h.send_header("Content-Type", "text/plain")
        h.send_header("Content-Length", str(len(REACHED_BODY)))
        h.end_headers()
        h.wfile.write(REACHED_BODY)
    return handler


def stub_routes(routes_tuple, recorder):
    """The same routes (method, matcher, access, device_scoped) with
    recording handlers."""
    handler = _recording_handler(recorder)
    return tuple(r._replace(handler=handler) for r in routes_tuple)


def probe_routes(recorder):
    """A device-scoped GET and POST route that exists only in a test."""
    handler = _recording_handler(recorder)
    matcher = routes.PrefixSuffix(PROBE_PREFIX, PROBE_SUFFIX)
    access = routes.Access(routes.USER, "device")
    return (
        routes.Route("GET", matcher, handler, access),
        routes.Route("POST", matcher, handler, access),
    )


def probe_path(device_id):
    return PROBE_PREFIX + device_id + PROBE_SUFFIX
