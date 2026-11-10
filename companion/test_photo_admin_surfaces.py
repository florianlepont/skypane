"""No administrator-visible surface exposes a user photo.

With photos stored for several frames, every GET route is fetched with an
administrator session (the administrator owns and co-manages nothing). The
bodies must carry no photo id, no photo path, no per-photo file size, and the
audit page, health page and fleet status document no photo numbers. At the
service layer a pure administrator is refused, and becomes a manager of one
frame only by being added to it explicitly.
"""
import json
import os
import re

import pytest

import fleet_console_support as fx
import photo_samples
from companion import prefs, routes
from companion_app_server import InProcessAppServer, http_request
from photo_fleet import ADMIN_EMAIL, seed_photo_fleet
from server import fleet_db, fleet_ops, hardware, photo_quota, photo_store

NOW = 1_700_000_000
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")
ID_SHAPE = re.compile(r"ph_[0-9a-f]{16}")
_SECRET = "d" * 64
PHOTOS_PER_FRAME = 2
# A GET route that cannot be fetched with an administrator cookie must be
# named here with the reason.
ALLOWED_SKIPS = {}


@pytest.fixture(autouse=True)
def _no_disk_floor(monkeypatch):
    monkeypatch.setattr(photo_quota, "MIN_FREE_DISK_BYTES", 0)


class Rig:
    """A server over a state directory holding photos on three frames."""

    def __init__(self, server, state, fleet):
        self.server = server
        self.state = state
        self.fleet = fleet
        self.ids = []
        self.sizes = []
        self.frames = [fleet.device_id]
        self.admin_cookie = fx.admin_cookie(state, ADMIN_EMAIL)

    def conn(self):
        return fleet_db.connect(self.state)

    def upload(self, conn, device_id, user_id):
        manager = photo_store.authorize_manager(conn, device_id, user_id)
        for _ in range(PHOTOS_PER_FRAME):
            photo_id = photo_store.add(
                manager, conn, self.state, photo_samples.jpeg_bytes(), NOW)
            self.ids.append(photo_id)
            path = os.path.join(self.state, "photos", device_id, photo_id + ".jpg")
            self.sizes.append(os.path.getsize(path))

    def add_frame(self, conn, mac, owner_id):
        device_id = fleet_db.add_device(
            conn, mac, _SECRET, hardware.LEGACY_KEY, owner_id, state_path="auto")
        self.upload(conn, device_id, owner_id)
        return device_id


@pytest.fixture
def rig(tmp_path):
    state = str(tmp_path / "state")
    prefs.set_request_prefs(lang="en")
    server = InProcessAppServer(state)
    fleet = seed_photo_fleet(state)
    built = Rig(server, state, fleet)
    conn = built.conn()
    try:
        built.upload(conn, fleet.device_id, fleet.owner_id)
        built.upload(conn, fleet.device_id, fleet.co_manager_id)
        second = built.add_frame(conn, "aa:bb:cc:dd:ee:11", fleet.other_id)
        built.frames.append(second)
        retired = built.add_frame(conn, "aa:bb:cc:dd:ee:12", fleet.other_id)
        fleet_ops.retire_frame(conn, state, retired, ACTOR)
    finally:
        conn.close()
    yield built
    server.stop()


def _template(route):
    matcher = route.matcher
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return matcher.prefix + "{}" + matcher.suffix


def _get_routes():
    return [_template(r) for r in routes.ROUTES if r.method == "GET"]


def _fill(template):
    return template.replace("{}", "sample")


def _fetch(rig, path):
    status, _headers, body = http_request(
        rig.server.url(path), cookie=rig.admin_cookie)
    return status, body.decode("utf-8", "replace")


def _size_lines(body, sizes):
    pattern = r"\b(?:%s)\s?(?:bytes|B|o|octets)\b" % "|".join(
        str(size) for size in sorted(set(sizes)))
    return re.findall(pattern, body)


def _assert_clean(rig, where, body):
    leaked = [pid for pid in rig.ids if pid in body]
    assert not leaked, "%s shows a photo id" % where
    assert not ID_SHAPE.search(body), "%s shows an id-shaped value" % where
    assert "photos/" not in body, "%s shows a photos path" % where
    assert not _size_lines(body, rig.sizes), "%s shows a photo file size" % where


def _fleet_paths(rig):
    """The Fleet page of each frame in every tab; the retired Health page
    moves an administrator here."""
    return ["/fleet?frame=%s&tab=%s" % (frame, tab)
            for frame in rig.frames for tab in ("state", "settings", "access")]


def _paths_for(rig, template):
    path = _fill(template)
    paths = [path]
    scoped = routes.match("GET", path, "")
    if scoped is not None and scoped[0].device_scoped:
        paths += ["/devices/%s%s" % (frame, path) for frame in rig.frames]
    return paths


def test_every_admin_get_route_is_free_of_photo_data(rig):
    fetched = 0
    for template in _get_routes():
        if template in ALLOWED_SKIPS:
            continue
        for path in _paths_for(rig, template):
            status, body = _fetch(rig, path)
            assert status < 500, (path, status)
            _assert_clean(rig, path, body)
            fetched += 1
    assert fetched >= len(_get_routes())


def test_the_fleet_tabs_of_every_frame_are_free_of_photo_data(rig):
    for path in _fleet_paths(rig):
        status, body = _fetch(rig, path)
        assert status == 200, path
        _assert_clean(rig, path, body)


def test_the_route_sweep_reaches_photo_free_pages_that_exist(rig):
    status, headers, _body = http_request(
        rig.server.url("/devices/%s/health" % rig.frames[0]), cookie=rig.admin_cookie)
    assert status == 303
    assert headers["Location"] == "/fleet?frame=%s" % rig.frames[0]
    status, _body = _fetch(rig, "/audit")
    assert status == 200
    status, _body = _fetch(rig, "/fleet")
    assert status == 200


def test_the_audit_page_after_a_retire_shows_the_count_but_no_id(rig):
    for language, label in (("en", "Photos purged"), ("fr", "Photos supprimées")):
        prefs.set_request_prefs(lang=language)
        status, _h, body = fx.get(
            rig.server, rig.admin_cookie, "/audit",
            headers={"Accept-Language": language})
        assert status == 200
        assert label in body
        assert not any(pid in body for pid in rig.ids)
        assert not ID_SHAPE.search(body)
    conn = rig.conn()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT detail FROM audit_log WHERE action = 'device.photo_purge'")]
    finally:
        conn.close()
    assert [json.loads(r["detail"]) for r in rows] == [
        {"count": PHOTOS_PER_FRAME, "cause": "retire"}]


def test_the_health_page_and_the_status_document_carry_no_photo_numbers(rig):
    fleet_db.write_status(rig.state, fleet_db.STATUS_OK, "")
    with open(os.path.join(rig.state, fleet_db.FLEET_STATUS_FILENAME), encoding="utf-8") as fh:
        text = fh.read()
    document = json.loads(text)
    assert not [key for key in document if "photo" in key.lower()]
    assert "photo" not in text.lower()
    assert not any(pid in text for pid in rig.ids)
    for path in ["/health"] + _fleet_paths(rig):
        status, headers, body = http_request(
            rig.server.url(path), cookie=rig.admin_cookie)
        assert status in (200, 303), path
        _assert_clean(rig, path, body.decode("utf-8", "replace"))
        assert "photo" not in headers.get("Location", "").lower()


def test_the_battery_history_export_has_no_photo_field(rig):
    status, _headers, body = http_request(rig.server.url(routes.EXPORT_ROUTE))
    assert status in (200, 401, 403, 404, 503)
    text = body.decode("utf-8", "replace")
    assert "photo" not in text.lower()
    assert not ID_SHAPE.search(text)


def test_a_pure_admin_is_refused_at_the_service_layer(rig):
    conn = rig.conn()
    try:
        admin_id = rig.fleet.admin_id
        for frame in rig.frames:
            with pytest.raises(photo_store.PhotoAccessDenied):
                photo_store.authorize_manager(conn, frame, admin_id)
        first, second = rig.frames
        fleet_db.add_co_manager(conn, first, admin_id, rig.fleet.owner_id)
        manager = photo_store.authorize_manager(conn, first, admin_id)
        assert len(photo_store.list_photos(manager, conn)) == 2 * PHOTOS_PER_FRAME
        with pytest.raises(photo_store.PhotoAccessDenied):
            photo_store.authorize_manager(conn, second, admin_id)
    finally:
        conn.close()
