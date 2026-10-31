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
    "sp_session=<token>" cookie pair. `principal_kind` is normally
    fleet_sessions.PRINCIPAL_USER; PRINCIPAL_LEGACY_ADMIN (with no user)
    plants the invalid old-format row that must never authenticate.
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
