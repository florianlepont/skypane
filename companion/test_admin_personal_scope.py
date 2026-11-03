"""An administrator's personal pages follow the same frame rule as a user's:
the un-prefixed page moves to the same page of their default own or
co-managed frame (or to the account page when they have none), every frame
with a fleet row is addressed by its id, and an administrator viewing a frame
they neither own nor co-manage sees a Viewing-owner strip with a way back to
Fleet. Real app subprocess over a seeded fleet.
"""
import re

import pytest

import fleet_console_support as fx
from companion import auth
from companion_app_server import http_request, session_cookie_for_state_dir
from companion_markup import parse_html
from server import device_dirs, fleet_db, hardware

PERSONAL_PAGES = ("/", "/display", "/flights", "/airlines", "/detection")
CONSOLE_FRAME_PAGES = ("/health", "/device", "/airlines/manage")
NASTY_OWNER = "o&<b>wner@example.test"
KEEPER_EMAIL = "keeper@example.test"
COMANAGER_EMAIL = "comanager@example.test"
_SECRET = "d" * 64


def _seed(state_dir):
    seed = fx.seed_users(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        seed.keeper_id = fleet_db.add_user(conn, KEEPER_EMAIL, "admin")
        seed.nasty_id = fleet_db.add_user(conn, NASTY_OWNER, "user")
        seed.comanager_id = fleet_db.add_user(conn, COMANAGER_EMAIL, "user")
        seed.keeper_frame = _device(conn, state_dir, 1, seed.keeper_id, "Keeper frame")
        seed.shared_frame = _device(conn, state_dir, 2, seed.owner_id, "Shared frame")
        seed.nasty_frame = _device(conn, state_dir, 3, seed.nasty_id, "Nasty frame")
        fleet_db.add_co_manager(conn, seed.shared_frame, seed.keeper_id, seed.owner_id)
        fleet_db.add_co_manager(conn, seed.nasty_frame, seed.comanager_id, seed.nasty_id)
    finally:
        conn.close()
    return seed


def _device(conn, state_dir, index, owner_id, name):
    device_id = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:%02x" % index, _SECRET, hardware.LEGACY_KEY, owner_id,
        name=name, state_path="auto")
    profile = hardware.get_profile(hardware.LEGACY_KEY)
    device_dirs.provision_device_dir(
        state_dir, device_id, profile.width, profile.height, fill=0x22)
    return device_id


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = {}

    def seed(state_dir):
        holder["seed"] = _seed(state_dir)

    server = module_app_server_factory(seed=seed)
    seed_ids = holder["seed"]
    cookies = {
        "keeper": session_cookie_for_state_dir(server.state_dir, KEEPER_EMAIL),
        "admin": session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL),
        "owner": session_cookie_for_state_dir(
            server.state_dir, fx.OWNER_EMAIL, role="user"),
        "comanager": session_cookie_for_state_dir(
            server.state_dir, COMANAGER_EMAIL, role="user"),
    }
    return server, seed_ids, cookies


def _get(app, who, path, headers=None):
    server, _seed_ids, cookies = app
    status, response_headers, body = http_request(
        server.base_url() + path, cookie=cookies[who], extra_headers=headers)
    return status, response_headers, body.decode("utf-8", "replace")


def _notice(body):
    found = parse_html(body).select(".frame-notice")
    return found[0] if found else None


# --- the frame rule ---------------------------------------------------------

@pytest.mark.parametrize("page", PERSONAL_PAGES)
def test_an_admin_is_moved_to_their_default_frame(app, page):
    _server, seed, _cookies = app
    status, headers, _body = _get(app, "keeper", page)
    # "Keeper frame" sorts before "Shared frame", which they co-manage.
    assert (status, headers["Location"]) == (
        303, "/devices/%s%s" % (seed.keeper_frame, page))
    assert _get(app, "keeper", headers["Location"])[0] == 200


@pytest.mark.parametrize("page", PERSONAL_PAGES)
def test_an_admin_with_no_frame_is_moved_to_the_account_page(app, page):
    status, headers, _body = _get(app, "admin", page)
    assert (status, headers["Location"]) == (303, "/account")


def test_the_query_survives_re_encoded(app):
    _server, seed, _cookies = app
    status, headers, _body = _get(app, "keeper", "/flights?q=a%26b&n=1")
    assert status == 303
    assert headers["Location"] == "/devices/%s/flights?q=a%%26b&n=1" % seed.keeper_frame


@pytest.mark.parametrize("hostile", [
    "//evil.example", "https://evil.example/x", "a%0d%0aX-Evil:%20y", "%5Cevil.example"])
def test_no_hostile_query_value_leaves_the_site_or_splits_the_header(app, hostile):
    _server, seed, _cookies = app
    status, headers, _body = _get(app, "keeper", "/display?x=" + hostile)
    assert status == 303
    location = headers["Location"]
    assert location.startswith("/devices/%s/display?" % seed.keeper_frame)
    assert "\r" not in location and "\n" not in location and "\\" not in location
    assert "://" not in location


def test_an_admin_can_open_any_frame_by_its_id(app):
    _server, seed, _cookies = app
    for frame in (seed.keeper_frame, seed.shared_frame, seed.nasty_frame):
        for page in ("/", "/display", "/flights"):
            assert _get(app, "admin", "/devices/%s%s" % (frame, page))[0] == 200


def test_a_user_still_gets_their_frame_or_a_404(app):
    _server, seed, _cookies = app
    status, headers, _body = _get(app, "owner", "/display")
    assert (status, headers["Location"]) == (
        303, "/devices/%s/display" % seed.shared_frame)
    assert _get(app, "owner", "/devices/%s/" % seed.keeper_frame)[0] == 404
    assert _get(app, "owner", "/devices/%s/" % seed.nasty_frame)[0] == 404


@pytest.mark.parametrize("page", CONSOLE_FRAME_PAGES)
def test_the_console_pages_of_the_served_frame_resolve_without_a_prefix(app, page):
    assert _get(app, "admin", page)[0] == 200
    assert _get(app, "owner", page)[0] == 404


def test_every_link_keeps_the_frame_being_viewed(app):
    _server, seed, _cookies = app
    prefix = "/devices/%s" % seed.nasty_frame
    _status, _headers, body = _get(app, "admin", prefix + "/flights")
    root = parse_html(body)
    for region in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = [a.attrs.get("href", "") for a in root.select_one(region).find_all("a")]
        personal = [h for h in hrefs if h.rsplit("/", 1)[-1] in (
            "", "display", "flights", "airlines")]
        assert personal and all(h.startswith(prefix) for h in personal), region


# --- the foreign-frame notice ------------------------------------------------

@pytest.mark.parametrize("page", ("/", "/display", "/flights", "/airlines", "/detection"))
def test_the_notice_names_the_owner_and_leads_back_to_fleet(app, page):
    _server, seed, _cookies = app
    _status, _headers, body = _get(
        app, "keeper", "/devices/%s%s" % (seed.nasty_frame, page))
    strip = _notice(body)
    assert strip is not None
    assert "Viewing %s’s frame" % NASTY_OWNER in strip.text()
    link = strip.select_one("a")
    assert (link.attrs["href"], link.text().strip()) == ("/fleet", "Back to Fleet")


def test_the_owner_email_is_escaped(app):
    _server, seed, _cookies = app
    _status, _headers, body = _get(
        app, "keeper", "/devices/%s/flights" % seed.nasty_frame)
    assert NASTY_OWNER not in body
    assert "o&amp;&lt;b&gt;wner@example.test" in body


def test_the_notice_is_in_french(app):
    _server, seed, _cookies = app
    _status, _headers, body = _get(
        app, "keeper", "/devices/%s/flights" % seed.nasty_frame,
        headers={"Cookie": "%s; %s=fr" % (app[2]["keeper"], auth.UI_LANG_COOKIE_NAME)})
    strip = _notice(body)
    assert strip is not None
    assert "Retour à la flotte" in strip.text()
    assert "Cadre de %s en consultation" % NASTY_OWNER in strip.text()


@pytest.mark.parametrize("page", ("/", "/display", "/flights", "/airlines"))
def test_no_notice_on_the_administrators_own_or_co_managed_frames(app, page):
    _server, seed, _cookies = app
    for frame in (seed.keeper_frame, seed.shared_frame):
        _status, _headers, body = _get(app, "keeper", "/devices/%s%s" % (frame, page))
        assert _notice(body) is None, (frame, page)


@pytest.mark.parametrize("page", CONSOLE_FRAME_PAGES)
def test_no_notice_on_console_pages(app, page):
    _server, seed, _cookies = app
    _status, _headers, body = _get(
        app, "keeper", "/devices/%s%s" % (seed.nasty_frame, page))
    assert _notice(body) is None


def test_a_user_and_a_co_manager_never_receive_the_owner_email(app):
    _server, seed, _cookies = app
    for who, frame in (("owner", seed.shared_frame), ("comanager", seed.nasty_frame)):
        _status, _headers, body = _get(app, who, "/devices/%s/flights" % frame)
        assert _notice(body) is None
        assert "Viewing" not in body
        assert "o&amp;&lt;b&gt;wner" not in body
        assert NASTY_OWNER not in body


def test_the_strip_text_matches_a_valid_email_shape(app):
    _server, seed, _cookies = app
    _status, _headers, body = _get(
        app, "admin", "/devices/%s/flights" % seed.shared_frame)
    strip = _notice(body)
    assert strip is not None
    assert re.search(r"Viewing \S+@\S+’s frame", strip.text())
