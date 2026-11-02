"""A co-manager over real HTTP: reaches and changes the shared frame like its
owner, is shut out of the admin and owner-only routes, and loses everything
the moment the membership row is removed. Outsiders keep getting the same 404
as for an unknown path."""
import os
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import device_scope
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import device_config, fleet_db, hardware
from server.plane import colour_rules, name_overrides

CO_EMAIL = "co-manager@example.test"
STRANGER_EMAIL = "stranger@example.test"

PAGES = ("/", "/display", "/detection", "/flights", "/health", "/airlines")
LEGACY_REDIRECTS = ("/settings", "/history", "/preview")
OWNER_ONLY_GETS = ("/device", "/update")
ADMIN_GETS = ("/fleet", "/users", "/audit")


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        self.device = seed.owned_id
        self.state_dir = {
            d.id: d.state_dir for d in device_scope.load_devices(server.state_dir)
        }[seed.owned_id]
        os.makedirs(self.state_dir, exist_ok=True)

    def prefix(self, device_id=None):
        return "/devices/%s" % (device_id or self.device)

    def get(self, who, path):
        status, headers, body = http_request(
            self.server.url(path), cookie=self.cookies[who])
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, path, form):
        cookie = self.cookies[who]
        status, headers, body = http_request(
            self.server.url(path), method="POST", cookie=cookie,
            data=with_csrf(cookie, form),
            extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def unknown(self, method):
        """The status and body of a path that matches no route."""
        path = "/no-such-page-anywhere"
        if method == "GET":
            status, _h, body = self.get("co", path)
        else:
            status, _h, body = self.post("co", path, {})
        assert status == 404
        return status, body

    def db(self, fn):
        conn = fleet_db.connect(self.server.state_dir)
        try:
            return fn(conn)
        finally:
            conn.close()

    def frame_row(self):
        return self.db(lambda c: tuple(fleet_db.get_device(c, self.device)))


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "stranger": fx.user_cookie(state_dir, email=STRANGER_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    built = Rig(server, seed, cookies)

    def share(conn):
        user = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, user, None)
        return user
    built.co_id = built.db(share)
    yield built
    server.stop()


def _remove_membership(rig):
    rig.db(lambda c: fleet_db.remove_co_manager(c, rig.device, rig.co_id))


# --- reach ---------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_a_co_manager_reaches_every_page_of_the_shared_frame(rig, page):
    path = rig.prefix() + ("" if page == "/" else page)
    status, _h, body = rig.get("co", path)
    assert status == 200
    assert "Kitchen" in body


@pytest.mark.parametrize("page", LEGACY_REDIRECTS)
def test_a_co_manager_follows_the_legacy_redirects(rig, page):
    status, headers, _b = rig.get("co", rig.prefix() + page)
    assert status in (301, 302, 303)
    assert headers["Location"].startswith(rig.prefix() + "/")


def test_the_shared_frame_is_in_the_co_manager_device_selector(rig):
    own = rig.db(lambda c: fleet_db.add_device(
        c, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY, rig.co_id,
        name="Desk", state_path="auto"))
    _s, _h, body = rig.get("co", rig.prefix(own) + "/display")
    assert 'value="%s"' % rig.device in body and 'value="%s"' % own in body
    assert 'value="%s"' % rig.seed.live_id not in body


# --- change --------------------------------------------------------------


def _owner_and_co(rig, path, form):
    """The same POST by the owner and by the co-manager: both statuses."""
    return (rig.post("owner", path, form)[0], rig.post("co", path, form)[0])


def test_a_co_manager_toggles_the_display_like_the_owner(rig):
    path = rig.prefix() + "/quick/display"
    status, _h, _b = rig.post("co", path, {"state": "off", "return_to": "/home"})
    assert status == 303
    assert device_config.load_device_config(rig.state_dir)["display_enabled"] is False
    rig.post("owner", path, {"state": "on"})
    assert device_config.load_device_config(rig.state_dir)["display_enabled"] is True
    rig.post("co", path, {"state": "on"})
    assert device_config.load_device_config(rig.state_dir)["display_enabled"] is True


def test_a_co_manager_saves_display_settings_like_the_owner(rig):
    path = rig.prefix() + "/settings"
    form = {"scope": "display", "return_to": "/display"}
    owner, co = _owner_and_co(rig, path, form)
    assert co == owner and co in (200, 303)


def test_a_co_manager_adds_a_colour_rule(rig):
    status, _h, _b = rig.post("co", rig.prefix() + "/settings/rules/add", {
        "rule_kind": "callsign", "rule_key": "AFR1234", "rule_theme_id": "white"})
    assert status == 303
    assert os.path.exists(colour_rules.colour_rules_path(rig.state_dir))


def test_a_co_manager_renames_an_airline(rig):
    status, _h, _b = rig.post("co", rig.prefix() + "/airlines/rename", {
        "airline": "Air France", "airline_name": "Frame Test Air"})
    assert status == 303
    assert os.path.exists(name_overrides.name_overrides_path(rig.state_dir))


def test_a_co_manager_saves_a_detection_runway(rig):
    status, _h, _b = rig.post("co", rig.prefix() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFMN",
        "runway": "04L/22R"})
    assert status == 303
    stored = device_config.load_device_config(rig.state_dir)["detection"]
    assert stored["airport"] == "LFMN"


# --- excluded ------------------------------------------------------------


@pytest.mark.parametrize("page", OWNER_ONLY_GETS)
def test_a_co_manager_gets_404_for_the_device_and_update_pages(rig, page):
    status, body = rig.unknown("GET")
    assert rig.get("co", rig.prefix() + page)[::2] == (status, body)


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_a_co_manager_gets_404_for_the_admin_pages(rig, path):
    status, body = rig.unknown("GET")
    assert rig.get("co", path)[::2] == (status, body)


@pytest.mark.parametrize("suffix", ["retire", "reassign", "reactivate"])
def test_a_co_manager_cannot_retire_reassign_or_reactivate_the_frame(rig, suffix):
    before = rig.frame_row()
    audit_before = fx.audit_rows(rig.server.state_dir)
    status, body = rig.unknown("POST")
    path = "/fleet/frames/%s/%s" % (rig.device, suffix)
    got = rig.post("co", path, {"owner_user_id": str(rig.co_id)})
    assert (got[0], got[2]) == (status, body)
    assert rig.frame_row() == before
    assert fx.audit_rows(rig.server.state_dir) == audit_before
    assert rig.db(lambda c: fleet_db.get_device_owner(c, rig.device)) == rig.seed.owner_id


# --- isolation -----------------------------------------------------------


def test_a_co_manager_gets_404_for_a_frame_they_do_not_co_manage(rig):
    status, body = rig.unknown("GET")
    for page in PAGES:
        path = rig.prefix(rig.seed.live_id) + ("" if page == "/" else page)
        assert rig.get("co", path)[::2] == (status, body), path


def test_a_stranger_gets_404_for_the_shared_frame(rig):
    status, body = rig.unknown("GET")
    for page in PAGES:
        path = rig.prefix() + ("" if page == "/" else page)
        assert rig.get("stranger", path)[::2] == (status, body), path
    post_status, post_body = rig.unknown("POST")
    got = rig.post("stranger", rig.prefix() + "/quick/display", {"state": "off"})
    assert (got[0], got[2]) == (post_status, post_body)
    assert device_config.load_device_config(rig.state_dir)["display_enabled"] is not False


# --- after removal ---------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_after_removal_every_page_of_the_frame_is_404(rig, page):
    path = rig.prefix() + ("" if page == "/" else page)
    assert rig.get("co", path)[0] == 200
    _remove_membership(rig)
    status, body = rig.unknown("GET")
    assert rig.get("co", path)[::2] == (status, body)


def test_after_removal_the_co_manager_can_no_longer_change_the_frame(rig):
    _remove_membership(rig)
    status, _h, _b = rig.post("co", rig.prefix() + "/quick/display", {"state": "off"})
    assert status == 404
    assert device_config.load_device_config(rig.state_dir)["display_enabled"] is not False


# --- the owner -----------------------------------------------------------


def test_the_owner_is_unaffected_by_the_co_manager(rig):
    for page in PAGES:
        path = rig.prefix() + ("" if page == "/" else page)
        assert rig.get("owner", path)[0] == 200
    assert rig.db(lambda c: fleet_db.get_device_owner(c, rig.device)) == rig.seed.owner_id
    _remove_membership(rig)
    assert rig.get("owner", rig.prefix() + "/display")[0] == 200


def test_the_admin_still_sees_every_frame(rig):
    _s, _h, body = rig.get("admin", rig.prefix() + "/display")
    assert "Kitchen" in body
    assert urllib.parse.quote(rig.device) in body
