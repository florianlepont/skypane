"""Uploaded artwork is fleet-wide: a picture added through one frame lives in
the fleet root's `illustration_overrides/` directory and is listed, served,
cache-busted and deletable from every other frame. The upload route's
refusals are unchanged and leave nothing behind."""
import io
import os
import re

import pytest
from PIL import Image

import companion.test_companion_app_helpers as cah
import fleet_console_support as fx
from companion import device_scope
from companion import upload_form
from companion.flash import FLASH_KEY_ARTWORK_DELETED
from companion_app_server import InProcessAppServer, http_request, with_csrf_part
from server import fleet_db, state_store
from server.plane import illustrations, manual_resolutions

KEY = "air-france"


def _png(width=None, colour=(200, 30, 30, 128)):
    buffer = io.BytesIO()
    Image.new("RGBA", (width or illustrations.ILLUSTRATION_MIN_WIDTH, 400), colour).save(buffer, format="PNG")
    return buffer.getvalue()


class Fleet:
    def __init__(self, tmp_path):
        self.root = str(tmp_path / "state")
        self.server = InProcessAppServer(self.root)
        self.seed = fx.seed_fleet(self.root)
        conn = fleet_db.connect(self.root)
        try:
            self.second_id = fleet_db.add_device(
                conn, "aa:bb:cc:00:00:99", fx.SECRET_HASH, fx.hardware.LEGACY_KEY,
                self.seed.owner_id, name="Hall", state_path="auto")
        finally:
            conn.close()
        devices = {d.id: d for d in device_scope.load_devices(self.root)}
        self.frame_a = devices[self.seed.owned_id].state_dir
        self.frame_b = devices[self.second_id].state_dir
        for directory in (self.frame_a, self.frame_b):
            os.makedirs(directory, exist_ok=True)
        self.cookie = fx.admin_cookie(self.root)
        self.fleet_dir = os.path.join(self.root, "illustration_overrides")

    def upload(self, device_id, key, payload, csrf=True):
        body, content_type = cah.encode_multipart(payload, field_name="illustration")
        if csrf:
            body, content_type = with_csrf_part(self.cookie, body, content_type)
        return http_request(
            self.server.url("/devices/%s/illustration/%s.png?default_type=A320" % (device_id, key)),
            method="POST", data=body, cookie=self.cookie, content_type=content_type,
            extra_headers={"Origin": self.server.base_url()})[:2]

    def manage(self, device_id):
        """The editor with every airline's type rows in the table: an airline's
        pictures are those of its type rows."""
        return fx.get(
            self.server, self.cookie, "/devices/%s/airlines/manage?types=all" % device_id)[2]

    def picture(self, device_id, key, query=""):
        return http_request(
            self.server.url("/devices/%s/illustration/%s.png%s" % (device_id, key, query)),
            cookie=self.cookie)

    def device_dir_listing(self):
        found = []
        for frame in (self.frame_a, self.frame_b):
            for base, _dirs, names in os.walk(frame):
                found.extend(os.path.join(base, n) for n in names if n.endswith((".png", ".tmp")))
        return found

    def fleet_listing(self):
        try:
            return sorted(os.listdir(self.fleet_dir))
        except OSError:
            return []


@pytest.fixture
def fleet(tmp_path):
    rig = Fleet(tmp_path)
    yield rig
    rig.server.stop()


def _flash(headers):
    return re.search(r"flash=([a-z_]+)", headers["Location"]).group(1)


def test_override_dir_is_the_fleet_directory_for_every_frame(tmp_path):
    root = str(tmp_path / "state")
    frame = os.path.join(root, "devices", "d_0123abcd")
    expected = os.path.join(root, "illustration_overrides")
    assert illustrations.override_dir_for_state_dir(root) == expected
    assert illustrations.override_dir_for_state_dir(frame) == expected
    assert illustrations.override_dir_for_state_dir("") is None
    assert illustrations.override_dir_for_state_dir(None) is None
    for state_dir in (root, frame):
        assert illustrations.override_path_for_key("../x", state_dir) is None
        assert illustrations.override_path_for_key("a/b", state_dir) is None
        assert illustrations.override_path_for_key("a\\b", state_dir) is None
        assert illustrations.override_path_for_key(KEY, state_dir) == os.path.join(expected, KEY + ".png")
    assert not os.path.exists(root)


def test_a_picture_uploaded_on_one_frame_is_used_on_every_frame(fleet):
    status, headers = fleet.upload(fleet.seed.owned_id, KEY, _png())
    assert (status, _flash(headers)) == (303, "illustration_replaced")
    assert fleet.fleet_listing() == [KEY + ".png"]
    assert fleet.device_dir_listing() == []
    other = fleet.manage(fleet.second_id)
    assert "illustration/%s.png?v=" % KEY in other
    assert not os.path.exists(os.path.join(fleet.frame_b, "illustration_overrides"))
    # Frame B serves the picture A uploaded, with the same cache buster.
    status, _h, body = fleet.picture(fleet.second_id, KEY)
    assert status == 200 and body.startswith(b"\x89PNG")
    first = fleet.manage(fleet.seed.owned_id)
    assert re.findall(r"illustration/%s\.png\?v=\d+" % KEY, first) == re.findall(
        r"illustration/%s\.png\?v=\d+" % KEY, other)


def test_deleting_the_picture_on_another_frame_removes_it_for_all(fleet):
    fleet.upload(fleet.seed.owned_id, KEY, _png())
    form = {"key": KEY, "airline_key": KEY}
    status, headers, _b = fx.post(
        fleet.server, fleet.cookie, "/devices/%s/airlines/artwork/delete" % fleet.second_id, form)
    assert status == 303
    assert _flash(headers) == FLASH_KEY_ARTWORK_DELETED
    assert fleet.fleet_listing() == []


def test_a_hand_named_airline_with_a_picture_on_another_frame_is_in_the_table(fleet):
    manual_resolutions.add_entry(fleet.frame_b, "ZZZ", "Zed Air", now="2026-01-01T00:00:00+00:00")
    before = fleet.manage(fleet.second_id)
    assert 'airlines-missing__name">Zed Air<' in before
    status, _h = fleet.upload(fleet.seed.owned_id, "zed-air", _png())
    assert status == 303
    assert fleet.fleet_listing() == ["zed-air.png"]
    after = fleet.manage(fleet.second_id)
    assert "illustration/zed-air.png?v=" in after
    assert 'airlines-missing__name">Zed Air<' not in after


@pytest.mark.parametrize("what", ["too_big", "not_png", "unknown_key", "path_key", "no_csrf", "wide"])
def test_refused_uploads_write_nothing_in_the_fleet_directory(fleet, what):
    key, payload, csrf = KEY, _png(), True
    if what == "too_big":
        payload = b"\x00" * (upload_form.MAX_UPLOAD_BYTES + 4096)
    elif what == "not_png":
        payload = b"not an image at all"
    elif what == "unknown_key":
        key = "no-such-airline-anywhere"
    elif what == "path_key":
        key = "..%2Fx"
    elif what == "no_csrf":
        csrf = False
    elif what == "wide":
        payload = _png(width=illustrations.ILLUSTRATION_MAX_PIXELS // 400 + 50)
    fleet.upload(fleet.seed.owned_id, key, payload, csrf=csrf)
    assert fleet.fleet_listing() == []
    assert fleet.device_dir_listing() == []


def test_a_renamed_hand_named_airline_shows_its_carried_picture_on_another_frame(fleet):
    manual_resolutions.add_entry(fleet.frame_a, "ZZZ", "Zed Air", now="2026-01-01T00:00:00+00:00")
    state_store.save_poll_state(fleet.frame_a, {})
    fleet.upload(fleet.seed.owned_id, "zed-air", _png())
    status, _h, _b = fx.post(
        fleet.server, fleet.cookie, "/devices/%s/airlines/rename/manual" % fleet.seed.owned_id,
        {"prefix": "ZZZ", "airline_name": "Zulu Air"})
    assert status == 303
    assert fleet.fleet_listing() == ["zed-air.png", "zulu-air.png"]
    assert "illustration/zulu-air.png?v=" in fleet.manage(fleet.second_id)


def test_the_owner_cannot_reach_the_upload_route(fleet):
    owner = fx.user_cookie(fleet.root, email=fx.OWNER_EMAIL)
    body, content_type = with_csrf_part(owner, *cah.encode_multipart(_png(), field_name="illustration"))
    status = http_request(
        fleet.server.url("/devices/%s/illustration/%s.png" % (fleet.seed.owned_id, KEY)),
        method="POST", data=body, cookie=owner, content_type=content_type,
        extra_headers={"Origin": fleet.server.base_url()})[0]
    assert status in (403, 404)
    assert fleet.fleet_listing() == []


@pytest.mark.parametrize("what", ["not_png", "wide", "good"])
def test_the_raw_upload_is_gone_before_the_answer_is_sent(fleet, monkeypatch, what):
    from companion.app import Handler
    payload = {"not_png": b"not an image at all",
               "wide": _png(width=illustrations.ILLUSTRATION_MAX_PIXELS // 400 + 50),
               "good": _png()}[what]
    real_redirect = Handler.redirect
    seen = []

    def spying_redirect(handler, location, set_cookie=None):
        seen.append(sorted(n for n in os.listdir(fleet.fleet_dir) if n.endswith(".tmp"))
                    if os.path.isdir(fleet.fleet_dir) else [])
        return real_redirect(handler, location, set_cookie)

    monkeypatch.setattr(Handler, "redirect", spying_redirect)
    fleet.upload(fleet.seed.owned_id, KEY, payload)
    assert seen == [[]]
