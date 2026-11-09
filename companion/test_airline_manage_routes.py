"""Health, the Airline editor and the airline write routes are the
administrator's: an owner and a co-manager get the unknown-path 404, an
administrator reaches them on any frame, an anonymous caller is sent to
sign-in. /airlines?resolve= hands an administrator to the editor."""
import os
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import airline_display, device_scope
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import fleet_db
from server.plane import illustrations, name_overrides

CO_EMAIL = "co-manager@example.test"

ADMIN_GETS = ("/airlines/manage",)
AIRLINE_POSTS = (
    ("/airlines/resolve", {"prefix": "ZZZ", "airline_name": "Zed Air"}),
    ("/airlines/rename", {"airline": "Air France", "airline_name": "AF Test"}),
    ("/airlines/rename/reset", {"airline": "Air France"}),
    ("/airlines/manual-resolutions/ZZZ/delete", {}),
    ("/illustration/air-france.png", {}),
)


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)

    def get(self, who, path):
        status, headers, body = http_request(
            self.server.url(path), cookie=self.cookies.get(who))
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, path, form):
        cookie = self.cookies.get(who)
        status, headers, body = http_request(
            self.server.url(path), method="POST", cookie=cookie,
            data=with_csrf(cookie, form),
            extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def unknown(self, who):
        status, _h, body = self.get(who, "/no-such-page-anywhere")
        assert status == 404
        return body

    def prefix(self, device_id):
        return "/devices/%s" % device_id


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()
    yield Rig(server, seed, cookies)
    server.stop()


@pytest.mark.parametrize("page", ADMIN_GETS)
def test_an_administrator_reaches_the_page_on_the_served_frame_and_any_frame(rig, page):
    assert rig.get("admin", page)[0] == 200
    assert rig.get("admin", rig.prefix(rig.seed.owned_id) + page)[0] == 200


@pytest.mark.parametrize("page", ADMIN_GETS)
@pytest.mark.parametrize("who", ("owner", "co"))
def test_an_owner_and_a_co_manager_get_the_unknown_path_404(rig, page, who):
    unknown = rig.unknown(who)
    for path in (rig.prefix(rig.seed.owned_id) + page, page):
        status, _h, body = rig.get(who, path)
        assert status == 404 and body == unknown


@pytest.mark.parametrize("page", ADMIN_GETS)
def test_an_anonymous_caller_is_sent_to_sign_in(rig, page):
    for path in (page, rig.prefix(rig.seed.owned_id) + page):
        status, headers, _b = rig.get("anonymous", path)
        assert status == 303 and headers["Location"].startswith("/login")


def test_the_editor_of_an_unknown_frame_is_a_404_for_an_administrator(rig):
    assert rig.get("admin", "/devices/d_00000000/airlines/manage")[0] == 404


@pytest.mark.parametrize("path,form", AIRLINE_POSTS)
@pytest.mark.parametrize("who", ("owner", "co"))
def test_an_owner_and_a_co_manager_cannot_write_airline_data(rig, path, form, who):
    unknown = rig.unknown(who)
    status, _h, body = rig.post(who, rig.prefix(rig.seed.owned_id) + path, form)
    assert status == 404 and body == unknown
    assert name_overrides.load_name_overrides(rig.owned_dir) == {}


@pytest.mark.parametrize("path,form", AIRLINE_POSTS)
def test_an_administrator_reaches_the_airline_handlers_on_any_frame(rig, path, form):
    status, _h, _b = rig.post("admin", rig.prefix(rig.seed.owned_id) + path, form)
    assert status != 404 and status < 500


def test_an_administrator_rename_is_written_to_the_chosen_frame(rig):
    status, _h, _b = rig.post(
        "admin", rig.prefix(rig.seed.owned_id) + "/airlines/rename",
        {"airline": "Air France", "airline_name": "AF Test"})
    assert status == 303
    assert name_overrides.load_name_overrides(rig.owned_dir)


def test_the_illustration_image_stays_readable_by_an_owner(rig):
    status, headers, _b = rig.get(
        "owner", rig.prefix(rig.seed.owned_id) + "/illustration/air-france.png")
    assert status == 200
    assert headers["Content-Type"] == "image/png"


def test_resolve_on_the_collection_sends_an_administrator_to_the_editor(rig):
    frame = rig.prefix(rig.seed.owned_id)
    status, headers, _b = rig.get("admin", frame + "/airlines?resolve=XYZ")
    assert status == 303
    assert headers["Location"] == frame + "/airlines/manage?resolve=XYZ"
    # Without a prefix the administrator is first moved to their own frame's
    # page, which then moves on to the editor.
    live = rig.prefix(rig.seed.live_id)
    status, headers, _b = rig.get("admin", "/airlines?resolve=XYZ")
    assert (status, headers["Location"]) == (303, live + "/airlines?resolve=XYZ")
    status, headers, _b = rig.get("admin", headers["Location"])
    assert (status, headers["Location"]) == (303, live + "/airlines/manage?resolve=XYZ")


def test_the_resolve_value_is_re_encoded_never_echoed(rig):
    raw = "A B&next=//evil.example/"
    live = rig.prefix(rig.seed.live_id)
    status, headers, _b = rig.get(
        "admin", "/airlines?resolve=" + urllib.parse.quote(raw, safe=""))
    assert status == 303
    assert headers["Location"] == live + "/airlines?" + urllib.parse.urlencode(
        {"resolve": raw})
    status, headers, _b = rig.get("admin", headers["Location"])
    assert status == 303
    assert headers["Location"] == live + "/airlines/manage?" + urllib.parse.urlencode(
        {"resolve": raw})
    assert "&next=" not in headers["Location"]


def test_the_collection_ignores_resolve_for_an_owner(rig):
    status, _h, plain = rig.get("owner", rig.prefix(rig.seed.owned_id) + "/airlines")
    assert status == 200
    status, _h, with_param = rig.get(
        "owner", rig.prefix(rig.seed.owned_id) + "/airlines?resolve=XYZ")
    assert status == 200
    assert "XYZ" not in with_param



def test_the_editor_shows_the_accented_name_and_the_key_is_unchanged(rig):
    prefix = rig.prefix(rig.seed.owned_id)
    status, _h, body = rig.get("admin", prefix + "/airlines/manage")
    assert status == 200
    assert "Air Algérie" in body
    assert 'name="airline_name" value="Air Algérie"' in body
    assert 'name="airline_name" value="Air Algerie"' not in body
    assert 'name="airline" value="Air Algerie"' in body
    assert illustrations.normalise_airline_key("Air Algerie") == "air-algerie"
    assert airline_display.builtin_name("Air Algérie") == "Air Algerie"


def test_posting_the_shown_name_back_is_a_reset_not_a_rename(rig):
    prefix = rig.prefix(rig.seed.owned_id)
    status, _h, _b = rig.post(
        "admin", prefix + "/airlines/rename",
        {"airline": "Air Algerie", "airline_name": "Air Algérie"})
    assert status == 303
    assert name_overrides.load_name_overrides(rig.owned_dir) == {}
