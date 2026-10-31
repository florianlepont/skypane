"""Owner-aware device scope: a user's device list, URL prefix, selector and
post-POST redirect are confined to the frames they own, and the live frame
is only ever reached through its real id. Admin behaviour is unchanged.
"""
import hashlib
import urllib.parse

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import access, app, device_dispatch, device_scope, prefs, ui_shell
from companion_app_server import http_request
from server import device_dirs, fleet_db, fleet_sessions, hardware

_SECRET = "c" * 64


@pytest.fixture(autouse=True)
def _reset_scope():
    yield
    device_scope.set_request_scope(None, ())
    prefs.set_request_principal(None)


@pytest.fixture
def fleet(tmp_path):
    (tmp_path / "state").mkdir()
    state_dir = str(tmp_path / "state")
    seeded = seed_matrix_fleet(state_dir)
    return state_dir, seeded


def _principal(seeded, who):
    return {
        "owner": access.Principal(access.KIND_USER, seeded.owner_id, OWNER_EMAIL, "user"),
        "other": access.Principal(access.KIND_USER, seeded.other_id, OTHER_EMAIL, "user"),
        "admin": access.Principal(access.KIND_USER, seeded.admin_id, ADMIN_EMAIL, "admin"),
    }[who]


def _add_live_device(state_dir, owner_id):
    conn = fleet_db.connect(state_dir)
    try:
        return fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:09", _SECRET, hardware.LEGACY_KEY, owner_id,
            name="Orly live", state_path=device_dirs.LIVE_STATE_PATH)
    finally:
        conn.close()


def _enter(role, devices, current):
    prefs.set_request_principal(role, role)
    device_scope.set_request_scope(current, devices)


def test_device_gains_a_defaulted_owner_field_and_load_devices_fills_it(fleet):
    state_dir, seeded = fleet
    legacy = device_scope.Device("d_00000001", "n", "t", "devices/x", "/x", False)
    assert legacy.owner_user_id is None
    owners = {d.id: d.owner_user_id for d in device_scope.load_devices(state_dir)}
    assert owners[seeded.owner_device] == seeded.owner_id
    assert owners[seeded.other_device] == seeded.other_id
    assert owners[device_scope.LIVE_ID] is None


def test_an_admin_sees_every_device_with_the_live_frame_first(fleet):
    state_dir, seeded = fleet
    devices = device_scope.load_devices_for(state_dir, _principal(seeded, "admin"))
    assert [d.id for d in devices][1:] == sorted(
        [seeded.owner_device, seeded.other_device])
    assert devices[0].is_live and devices[0].id == device_scope.LIVE_ID
    assert devices == device_scope.load_devices(state_dir)


def test_a_user_sees_only_their_own_frames_and_no_live_fallback(fleet):
    state_dir, seeded = fleet
    devices = device_scope.load_devices_for(state_dir, _principal(seeded, "owner"))
    assert [d.id for d in devices] == [seeded.owner_device]
    assert not any(d.is_live for d in devices)


def test_a_user_with_no_frame_gets_an_empty_list(fleet):
    state_dir, _seeded = fleet
    conn = fleet_db.connect(state_dir)
    try:
        lonely = fleet_db.add_user(conn, "lonely@example.test", "user")
    finally:
        conn.close()
    principal = access.Principal(access.KIND_USER, lonely, "lonely@example.test", "user")
    assert device_scope.load_devices_for(state_dir, principal) == []


def test_no_principal_keeps_the_previous_list(fleet):
    state_dir, _seeded = fleet
    assert device_scope.load_devices_for(state_dir, None) == device_scope.load_devices(state_dir)


def test_a_user_who_owns_the_live_frame_gets_real_id_urls(fleet):
    state_dir, seeded = fleet
    live_id = _add_live_device(state_dir, seeded.owner_id)
    principal = _principal(seeded, "owner")
    devices = device_scope.load_devices_for(state_dir, principal)
    live = next(d for d in devices if d.is_live)
    assert live.id == live_id

    _enter("user", devices, live)
    assert device_scope.current_prefix() == "/devices/" + live_id
    assert device_scope.scoped("/display") == "/devices/%s/display" % live_id
    assert device_scope.target_path("/flights", live) == "/devices/%s/flights" % live_id
    assert device_scope.selector_value(live) == live_id


def test_the_selector_option_values_never_use_the_literal_live_for_a_user(fleet):
    state_dir, seeded = fleet
    live_id = _add_live_device(state_dir, seeded.owner_id)
    devices = device_scope.load_devices_for(state_dir, _principal(seeded, "owner"))
    live = next(d for d in devices if d.is_live)
    _enter("user", devices, live)
    html = ui_shell.device_selector_html("display")
    assert 'value="%s"' % live_id in html
    assert 'value="live"' not in html
    assert 'data-href="/devices/%s/display"' % live_id in html


def test_an_admin_keeps_the_unprefixed_live_frame(fleet):
    state_dir, seeded = fleet
    live_id = _add_live_device(state_dir, seeded.owner_id)
    devices = device_scope.load_devices_for(state_dir, _principal(seeded, "admin"))
    live = next(d for d in devices if d.is_live)
    assert live.id == live_id
    _enter("admin", devices, live)
    assert device_scope.current_prefix() == ""
    assert device_scope.scoped("/display") == "/display"
    assert device_scope.selector_value(live) == device_scope.LIVE_ID


def test_switch_target_for_a_user_refuses_a_foreign_or_unknown_id(fleet):
    state_dir, seeded = fleet
    devices = device_scope.load_devices_for(state_dir, _principal(seeded, "owner"))
    _enter("user", devices, devices[0])
    for value in (seeded.other_device, "d_00000000", "live", "../x"):
        assert device_scope.switch_target(
            "/display", "device=" + value, devices) == device_scope.SWITCH_UNKNOWN
    assert device_scope.switch_target(
        "/display", "device=" + seeded.owner_device, devices
    ) == "/devices/%s/display" % seeded.owner_device


class _Handler(device_dispatch.DeviceDispatchMixin):
    def __init__(self, principal, referer):
        self._principal_value = principal
        self.headers = {"Referer": referer}

    def _safe_principal(self):
        return self._principal_value


def _referring(seeded, who, referer, state_dir, any_device=False):
    principal = _principal(seeded, who)
    devices = device_scope.load_devices_for(state_dir, principal)
    prefs.set_request_principal(principal.role, principal.role)
    device_scope.set_request_scope(devices[0] if devices else None, devices)
    return _Handler(principal, referer)._referring_tab(any_device=any_device)


def test_a_user_returns_to_the_owned_frame_page_they_came_from(fleet):
    state_dir, seeded = fleet
    referer = "https://x.test/devices/%s/display" % seeded.owner_device
    assert _referring(seeded, "owner", referer, state_dir) == (
        "/devices/%s/display" % seeded.owner_device)
    assert _referring(seeded, "owner", referer, state_dir, any_device=True) == (
        "/devices/%s/display" % seeded.owner_device)


@pytest.mark.parametrize("referer_path", [
    "/devices/{other}/display",
    "/devices/d_00000000/display",
    "/devices/{own}/update",
    "/devices/{own}/device",
    "/devices/{own}/../account",
    "//evil.test/devices/{own}/display",
    "/health",
    "",
])
def test_a_user_referer_that_is_foreign_or_not_a_user_page_goes_to_their_home(
        fleet, referer_path):
    state_dir, seeded = fleet
    path = referer_path.format(own=seeded.owner_device, other=seeded.other_device)
    target = _referring(seeded, "owner", "https://x.test" + path, state_dir)
    assert target == "/devices/%s/" % seeded.owner_device


def test_a_user_on_the_account_page_stays_there(fleet):
    state_dir, seeded = fleet
    assert _referring(seeded, "owner", "https://x.test/account", state_dir) == "/account"


def test_a_user_with_no_frame_goes_to_the_account_page(fleet):
    state_dir, seeded = fleet
    conn = fleet_db.connect(state_dir)
    try:
        lonely = fleet_db.add_user(conn, "lonely2@example.test", "user")
    finally:
        conn.close()
    principal = access.Principal(access.KIND_USER, lonely, "lonely2@example.test", "user")
    prefs.set_request_principal("user", "user")
    device_scope.set_request_scope(None, ())
    handler = _Handler(principal, "https://x.test/devices/%s/display" % seeded.owner_device)
    assert handler._referring_tab() == "/account"


def test_an_admin_keeps_the_previous_referring_tab_behaviour(fleet):
    state_dir, seeded = fleet
    referer = "https://x.test/devices/%s/flights" % seeded.other_device
    assert _referring(seeded, "admin", referer, state_dir) == "/flights"
    assert _referring(seeded, "admin", referer, state_dir, any_device=True) == (
        "/devices/%s/flights" % seeded.other_device)


# --- over real HTTP -------------------------------------------------------------

@pytest.fixture
def http_fleet(app_server_in_process):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    cookies = {}
    conn = fleet_db.connect(server.state_dir)
    try:
        lonely = fleet_db.add_user(conn, "lonely3@example.test", "user")
        for name, user_id in (
                ("owner", seeded.owner_id), ("other", seeded.other_id),
                ("admin", seeded.admin_id), ("lonely", lonely)):
            token = "tok-" + name
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                principal="user", now=app._now())
            cookies[name] = "sp_session=" + token
    finally:
        conn.close()
    return server, seeded, cookies


def _get(server, path, cookie):
    status, headers, body = http_request(server.url(path), cookie=cookie)
    return status, headers, body.decode("utf-8", "replace")


def _post(server, path, cookie, referer=None):
    extra = {"Origin": server.base_url()}
    if referer:
        extra["Referer"] = server.url(referer)
    return http_request(
        server.url(path), method="POST", cookie=cookie,
        data=urllib.parse.urlencode({"theme": "dark", "lang": "fr"}).encode(),
        extra_headers=extra)


def test_an_owner_reaches_their_frame_and_nobody_else_does(http_fleet):
    server, seeded, cookies = http_fleet
    own = "/devices/%s/display" % seeded.owner_device
    foreign = "/devices/%s/display" % seeded.other_device
    assert _get(server, own, cookies["owner"])[0] == 200
    assert _get(server, own, cookies["admin"])[0] == 200
    unknown = _get(server, "/no-such-page-anywhere", cookies["other"])
    refused = _get(server, own, cookies["other"])
    assert (refused[0], refused[2]) == (unknown[0], unknown[2]) == (404, unknown[2])
    assert _get(server, own, None)[0] == 303
    assert _get(server, foreign, cookies["owner"])[0] == 404


def test_the_unprefixed_live_frame_is_admin_only(http_fleet):
    server, _seeded, cookies = http_fleet
    for path in ("/", "/display", "/flights", "/health", "/airlines"):
        assert _get(server, path, cookies["admin"])[0] == 200, path
        assert _get(server, path, cookies["owner"])[0] == 404, path
        assert _get(server, path, cookies["lonely"])[0] == 404, path


def test_a_user_page_links_only_to_their_own_frame(http_fleet):
    server, seeded, cookies = http_fleet
    _status, _headers, body = _get(
        server, "/devices/%s/display" % seeded.owner_device, cookies["owner"])
    assert seeded.owner_device in body
    assert seeded.other_device not in body
    assert 'value="live"' not in body


def test_a_preference_post_returns_to_the_frame_page_the_user_came_from(http_fleet):
    server, seeded, cookies = http_fleet
    referer = "/devices/%s/flights" % seeded.owner_device
    status, headers, _body = _post(server, "/ui-theme", cookies["owner"], referer)
    assert status == 303
    assert headers["Location"] == referer


def test_a_user_with_no_frame_still_gets_global_routes_and_the_account_redirect(http_fleet):
    server, _seeded, cookies = http_fleet
    assert _get(server, "/account", cookies["lonely"])[0] == 200
    status, headers, _body = _post(server, "/ui-theme", cookies["lonely"], "/account")
    assert (status, headers["Location"]) == (303, "/account")
    status, headers, _body = _post(server, "/ui-lang", cookies["lonely"])
    assert (status, headers["Location"]) == (303, "/account")
