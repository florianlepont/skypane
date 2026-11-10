"""The reduced user view over the real handlers: a fleet with provisioned
device directories, no stubbed routes, real session cookies. Proves page and
derived-image access (owner, another user, admin), the identical 404, and the
live-frame and selector rules, over HTTP.
"""
import json
import os
import re
import urllib.parse

import pytest

from companion import i18n, layout, routes
from companion_markup import parse_html
from companion.layout import escape_html
from companion.pages import health_page
from companion.settings import calendar as calendar_settings
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir)
from matrix_rows_landing import FRAME_PAGE_REDIRECTS, LEGACY_PAGE_TARGETS
from provisioned_fleet import (
    ADMIN_EMAIL, FRAMELESS_EMAIL, GALLERY_FILENAME, NAME_A1, NAME_A2, NAME_B1,
    SEEDED_ADMIN_ONLY, USER_A_EMAIL, USER_B_EMAIL, device_dir, mark_checked_in,
    provision_fleet)
from server import history_db, device_config, device_dirs
from server.plane import calendar_rules
from server.plane.calendar_rules import registry as calendar_registry

_EMAILS = {
    "a": USER_A_EMAIL, "b": USER_B_EMAIL, "admin": ADMIN_EMAIL,
    "frameless": FRAMELESS_EMAIL}

# One concrete middle per templated route; a new owner-device route without an
# entry here fails `test_every_owner_device_get_route_has_a_sample`.
SAMPLE_MIDDLE = {
    "/gallery/{}": GALLERY_FILENAME,
    "/illustration/{}.png": "air-france",
    "/theme-preview/{}.png": "black",
    "/frame-preview/{}.png": "white",
}

# The legacy page routes are fixed redirects to a current page.
LEGACY_REDIRECT = {
    "/settings": "/display", "/history": "/flights", "/preview": "/flights",
    "/display/screen": "/display", "/display/layout": "/display"}

UNKNOWN_ID = "d_00000000"


def _template(route):
    matcher = route.matcher
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return matcher.prefix + "{}" + matcher.suffix


def _owner_get_templates():
    return [
        _template(r) for r in routes.ROUTES
        if r.method == "GET" and r.access == routes.OWNER_DEVICE]


def _sample(template):
    if "{}" not in template:
        return template
    assert template in SAMPLE_MIDDLE, "no sample path declared for " + template
    return template.replace("{}", SAMPLE_MIDDLE[template])


class Rig:
    """A running companion over one provisioned fleet, with a session cookie
    per persona."""

    def __init__(self, state_dir, live_owner="admin"):
        self.state_dir = state_dir
        self.server = InProcessAppServer(state_dir)
        self.fleet = provision_fleet(state_dir, live_owner=live_owner)
        self.cookies = {
            name: session_cookie_for_state_dir(state_dir, email)
            for name, email in _EMAILS.items()}
        self.cookies["anonymous"] = None

    def request(self, method, path, who, data=None, extra_headers=None):
        headers = dict(extra_headers or {})
        if method == "POST":
            headers["Origin"] = self.server.base_url()
            if data is not None and self.cookies[who]:
                data = data + b"&csrf_token=" + _csrf(self.cookies[who])
        return http_request(
            self.server.url(path), method=method, data=data,
            cookie=self.cookies[who], extra_headers=headers or None)

    def get(self, path, who):
        return self.request("GET", path, who)

    def page(self, path, who):
        status, _headers, body = self.get(path, who)
        assert status == 200, (path, who, status)
        return body.decode("utf-8")

    def unknown_404(self, who):
        status, _headers, body = self.get("/no-such-page-anywhere", who)
        assert status == 404
        return body

    def assert_unknown(self, method, path, who, data=None):
        status, _headers, body = self.request(method, path, who, data=data)
        assert status == 404, (method, path, who, status)
        assert body == self.unknown_404(who), (method, path, who)

    def stop(self):
        self.server.stop()


# Function-scoped on purpose: `Handler.args` is a class attribute, so a second
# in-process server in the same interpreter would re-point a long-lived one at
# its own state directory.
@pytest.fixture
def rig(tmp_path):
    built = Rig(str(tmp_path / "state"))
    yield built
    built.stop()


@pytest.fixture
def live_rig(tmp_path):
    built = Rig(str(tmp_path / "state"), live_owner="a")
    yield built
    built.stop()


def test_the_provisioned_fleet_has_real_device_directories(rig):
    for device_id in (rig.fleet.a1, rig.fleet.a2, rig.fleet.b1):
        directory = device_dirs.resolve_state_dir(
            rig.state_dir, device_dirs.state_path_for(device_id))
        assert os.path.isfile(os.path.join(directory, "device_config.json"))
        assert os.path.isfile(os.path.join(directory, "gallery", GALLERY_FILENAME))


def test_every_owner_device_get_route_has_a_sample():
    templates = _owner_get_templates()
    assert templates
    for template in templates:
        _sample(template)


@pytest.mark.parametrize("template", _owner_get_templates())
def test_an_owner_reaches_their_frame_and_another_user_gets_the_unknown_404(
        rig, template):
    path = "/devices/%s%s" % (rig.fleet.a1, _sample(template))
    status, headers, body = rig.get(path, "a")
    if template in LEGACY_REDIRECT:
        assert status == 303
        assert headers["Location"] == "/devices/%s%s" % (
            rig.fleet.a1, LEGACY_REDIRECT[template])
    else:
        assert status == 200, path
        assert body
    rig.assert_unknown("GET", path, "b")
    admin_status, _h, _b = rig.get(path, "admin")
    assert admin_status == (303 if template in LEGACY_REDIRECT else 200)


@pytest.mark.parametrize("template", _owner_get_templates())
def test_the_unprefixed_frame_routes_are_admin_only(rig, template):
    path = _sample(template)
    moved = {"a": rig.fleet.a2, "b": rig.fleet.b1}
    for who in ("a", "b", "frameless"):
        if path in FRAME_PAGE_REDIRECTS and who in moved:
            # A user's Home, Display, Flights, Airlines, Health and Detection
            # move to the same page under their default frame (first by name).
            status, headers, _body = rig.get(path, who)
            assert status == 303, (path, who)
            assert headers["Location"] == "/devices/%s%s" % (moved[who], path)
            continue
        if path in LEGACY_PAGE_TARGETS and who in moved:
            status, headers, _body = rig.get(path, who)
            assert status == 303, (path, who)
            assert headers["Location"] == "/devices/%s%s" % (
                moved[who], LEGACY_PAGE_TARGETS[path])
            continue
        if path in LEGACY_PAGE_TARGETS and who == "frameless":
            status, headers, _body = rig.get(path, who)
            assert (status, headers["Location"]) == (303, "/account"), path
            continue
        if path in FRAME_PAGE_REDIRECTS and who == "frameless":
            # No frame to move to: the account page offers to add one.
            status, headers, _body = rig.get(path, who)
            assert (status, headers["Location"]) == (303, "/account"), path
            continue
        rig.assert_unknown("GET", path, who)
    anonymous_status, headers, _b = rig.get(path, "anonymous")
    assert anonymous_status == 303 and headers["Location"].startswith("/login")


@pytest.mark.parametrize("path", ["/", "/display", "/flights", "/airlines"])
def test_an_admin_moves_from_the_personal_pages_to_their_own_frame(rig, path):
    status, headers, _body = rig.get(path, "admin")
    assert status == 303
    location = headers["Location"]
    assert re.fullmatch(r"/devices/d_[0-9a-f]{8}" + re.escape(path), location)
    assert rig.get(location, "admin")[0] == 200


@pytest.mark.parametrize("path", ["/runway-image/06-24.png"])
def test_admin_only_frame_routes_are_404_for_users_in_both_forms(rig, path):
    for who in ("a", "b"):
        rig.assert_unknown("GET", path, who)
        rig.assert_unknown("GET", "/devices/%s%s" % (rig.fleet.a1, path), who)


def test_a_user_who_owns_the_live_frame_is_served_under_its_real_id(live_rig):
    live = live_rig.fleet.live
    home = live_rig.page("/devices/%s/" % live, "a")
    assert "/devices/%s/" % live in home
    status, headers, _body = live_rig.get("/", "a")
    assert status == 303
    assert headers["Location"] == "/devices/%s/" % live_rig.fleet.a2
    pages = ("/", "/display", "/flights", "/airlines")
    for path in pages:
        body = live_rig.page("/devices/%s%s" % (live, path), "a")
        links = re.findall(r'(?:data-)?href="([^"]*)"', body)
        for target in links:
            assert target not in ("/display", "/flights", "/airlines"), (
                path, target)
        assert any(t.startswith("/devices/%s" % live) for t in links), path
        assert 'value="live"' not in body


def test_the_frame_sheet_lists_only_the_users_own_frames(rig):
    body = rig.page("/devices/%s/display" % rig.fleet.a1, "a")
    for own in (rig.fleet.a1, rig.fleet.a2):
        assert 'href="/devices/%s/display"' % own in body
    assert NAME_A1 in body and NAME_A2 in body
    for foreign in (rig.fleet.b1, rig.fleet.live):
        assert foreign not in body
    assert NAME_B1 not in body


def test_a_selector_value_naming_a_foreign_frame_is_a_404_that_hides_existence(rig):
    base = "/devices/%s/display" % rig.fleet.a1
    # The page keeps the caller's own navigation, so it is compared with the
    # answer for an id that exists nowhere: a foreign id must be no different.
    status, _h, unknown_id_body = rig.get("%s?device=%s" % (base, UNKNOWN_ID), "a")
    assert status == 404
    for value in (rig.fleet.b1, rig.fleet.live, rig.fleet.pending, "live"):
        status, _h, body = rig.get("%s?device=%s" % (base, value), "a")
        assert status == 404, value
        assert body == unknown_id_body, value
    assert rig.fleet.b1 not in unknown_id_body.decode("utf-8")
    status, headers, _b = rig.get("%s?device=%s" % (base, rig.fleet.a2), "a")
    assert status == 303
    assert headers["Location"] == "/devices/%s/display" % rig.fleet.a2


def test_pending_and_retired_frames_do_not_exist_for_a_user(rig):
    for pending_id in (rig.fleet.pending, rig.fleet.retired):
        assert pending_id.startswith("p_")
        for who in ("a", "b", "frameless"):
            rig.assert_unknown("GET", "/devices/%s/" % pending_id, who)
            rig.assert_unknown("GET", "/devices/%s/display" % pending_id, who)
    for who in ("a", "b"):
        for body_text in (rig.page("/account", who), rig.page(
                "/devices/%s/" % (rig.fleet.a1 if who == "a" else rig.fleet.b1), who)):
            assert rig.fleet.pending not in body_text
            assert rig.fleet.retired not in body_text


# --- reduced content, crafted POSTs and the calendar gate -----------------------

ADMIN_ONLY_KEYS = tuple(SEEDED_ADMIN_ONLY)
_ADMIN_LINK_PATHS = (
    "/fleet", "/users", "/audit", "/update", "/device", "/health", "/airlines/manage",
    "/locations")
_FRAME_PAGES = ("/", "/display", "/flights", "/airlines")


def _csrf(cookie):
    from companion import auth
    return auth.csrf_token(cookie.split("=", 1)[1]).encode()


def _form(**fields):
    return urllib.parse.urlencode(fields).encode()


def _admin_only_values(rig, device_id):
    config = device_config.load_device_config(device_dir(rig.state_dir, device_id))
    return {key: config[key] for key in ADMIN_ONLY_KEYS}


def _hrefs(body):
    return re.findall(r'(?:data-)?href="([^"]*)"', body)


def _page_path(href):
    """The page an href names, without a frame prefix, query or fragment."""
    path = urllib.parse.urlsplit(href).path
    return _strip_frame_prefix(path)


def _strip_frame_prefix(path):
    return re.sub(r"\A/devices/d_[0-9a-f]{8}", "", path) or "/"


def test_a_crafted_settings_post_changes_no_quiet_hours_and_no_admin_only_key(rig):
    before = _admin_only_values(rig, rig.fleet.a1)
    assert before == SEEDED_ADMIN_ONLY
    config_before = device_config.load_device_config(device_dir(rig.state_dir, rig.fleet.a1))
    status, headers, _body = rig.request(
        "POST", "/devices/%s/settings" % rig.fleet.a1, "a",
        data=_form(
            wake_interval_s="60", led_enabled="on", tracked_runway="02-20",
            scope="all", quiet_hours_enabled="on", quiet_hours_start="21:30",
            quiet_hours_end="06:15"))
    assert status == 303
    assert headers["Location"].startswith("/devices/%s/" % rig.fleet.a1)
    config = device_config.load_device_config(device_dir(rig.state_dir, rig.fleet.a1))
    for key in ("quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end", "timezone"):
        assert config[key] == config_before[key], key
    assert _admin_only_values(rig, rig.fleet.a1) == before


def test_a_crafted_settings_post_to_another_users_frame_is_a_404_and_changes_nothing(rig):
    path = os.path.join(device_dir(rig.state_dir, rig.fleet.b1), "device_config.json")
    with open(path, "rb") as fh:
        before = fh.read()
    rig.assert_unknown(
        "POST", "/devices/%s/settings" % rig.fleet.b1, "a",
        data=_form(
            wake_interval_s="60", led_enabled="on", tracked_runway="02-20",
            scope="all", quiet_hours_start="01:00"))
    with open(path, "rb") as fh:
        assert fh.read() == before


def test_a_crafted_post_cannot_use_the_unprefixed_live_frame_form(rig):
    live_before = device_config.load_device_config(rig.state_dir)
    rig.assert_unknown(
        "POST", "/settings", "a", data=_form(wake_interval_s="60", scope="all"))
    assert device_config.load_device_config(rig.state_dir) == live_before


def test_user_display_has_no_runway_wake_interval_or_led_control(rig):
    admin_only_fields = ("tracked_runway", "wake_interval_s", "led_enabled")
    user_display = rig.page("/devices/%s/display" % rig.fleet.a1, "a")
    assert 'name="quiet_hours_start"' not in user_display
    for field in admin_only_fields:
        assert 'name="%s"' % field not in user_display
    assert "/quick/led" not in user_display
    admin_display = rig.page("/devices/%s/display" % rig.fleet.a1, "admin")
    assert 'name="tracked_runway"' not in admin_display
    assert "detection-card" not in admin_display
    admin_device = rig.page("/fleet?frame=%s" % rig.fleet.a1, "admin")
    assert 'name="wake_interval_s"' in admin_device
    assert "/quick/led" in admin_device


def test_user_home_has_no_led_switch_and_no_refresh_trigger(rig):
    home = rig.page("/devices/%s/" % rig.fleet.a1, "a")
    for absent in ("/quick/led", "led_enabled", "/poll", "Refresh now"):
        assert absent not in home
    assert "/quick/display" in home and "/quick/quiet-hours" in home


def test_home_has_one_dot_and_no_battery_tile_or_attention_bar_for_either_role(rig):
    """a user's and an administrator's Home read the frame state from one dot with its word, in
    the order frame chip, status card, picture, recent flights; neither shows the battery tile or
    the attention bar (the battery lives on the Console Health page)"""
    mark_checked_in(rig.state_dir, rig.fleet.a1, source_fault=True)
    path = "/devices/%s/" % rig.fleet.a1
    user_home = rig.page(path, "a")
    admin_home = rig.page(path, "admin")
    root = parse_html(user_home)
    assert len(root.select(".home-state__dot")) == 1
    assert root.select_one(".home-state__dot").attrs["aria-label"]
    assert not root.select(".home-battery") and not root.select(".home-action")
    assert user_home.index("frame-menu__list") < user_home.index("home-state ")
    assert user_home.index("home-state ") < user_home.index("home-flights")
    admin_root = parse_html(admin_home)
    assert not admin_root.select(".home-battery") and not admin_root.select(".home-action")
    assert len(admin_root.select(".home-state__dot")) == 1
    # The battery is read in the State block of the administrator's Fleet view instead.
    admin_health = rig.page("/fleet?frame=%s" % rig.fleet.a1, "admin")
    assert "Battery" in admin_health


def test_the_system_view_is_the_administrators_alone_and_keeps_its_platform_rows(rig):
    with history_db.open_db(rig.state_dir) as conn:
        history_db.set_meta(conn, history_db.META_SOURCE_FAULT, "True")
    platform_texts = (
        health_page.ROW_FLIGHT_DATA_NAME, health_page.ROW_SOURCES_NAME, health_page.SOURCE_FAULT_HEADING,
        health_page.UNRESOLVED_SECTION_HEADING)
    admin_health = rig.page("/fleet?view=system", "admin")
    for text in platform_texts:
        assert escape_html(i18n.t(text)) in admin_health, text
    rig.assert_unknown("GET", "/fleet?view=system", "a")
    # The retired Health address moves a user to their own Home, never to a platform page.
    status, headers, _body = rig.get("/health", "a")
    assert status == 303 and headers["Location"].startswith("/devices/")
    assert "fleet" not in headers["Location"]


def test_user_pages_link_to_no_admin_page_and_admin_pages_still_do(rig):
    own = rig.fleet.a1
    user_paths = ["/devices/%s%s" % (own, page) for page in _FRAME_PAGES] + ["/account"]
    for path in user_paths:
        for target in _hrefs(rig.page(path, "a")):
            page = _page_path(target)
            assert page not in _ADMIN_LINK_PATHS, (path, target)
            assert not page.startswith(("/fleet/", "/users/", "/audit/")), (path, target)
    personal = [_page_path(t) for t in _hrefs(rig.page("/devices/%s/" % own, "admin"))]
    assert "/fleet" in personal
    assert "/device" not in personal and "/health" not in personal
    console = [_page_path(t) for t in _hrefs(rig.page("/fleet?frame=%s" % own, "admin"))]
    assert "/fleet" in console
    assert "/device" not in console


def test_a_user_quick_toggle_changes_their_frame_and_returns_to_it(rig):
    own = rig.fleet.a1
    base = "/devices/%s" % own
    cases = (
        ("/quick/display", "display_enabled", False, "off"),
        ("/quick/quiet-hours", "quiet_hours_enabled", True, "on"))
    for route, key, expected, state in cases:
        status, headers, _b = rig.request(
            "POST", base + route, "a", data=_form(**{layout.QUICK_STATE_FIELD: state}))
        assert status == 303
        assert headers["Location"].startswith(base + "/display")
        config = device_config.load_device_config(device_dir(rig.state_dir, own))
        assert config[key] is expected


def test_the_led_quick_toggle_is_a_404_for_a_user_and_changes_nothing(rig):
    before = _admin_only_values(rig, rig.fleet.a1)
    for path in ("/quick/led", "/devices/%s/quick/led" % rig.fleet.a1):
        rig.assert_unknown("POST", path, "a", data=_form(**{layout.QUICK_STATE_FIELD: "on"}))
    assert _admin_only_values(rig, rig.fleet.a1) == before


def test_a_user_with_no_frame_reaches_the_account_page_and_no_device_page(rig):
    assert rig.page("/account", "frameless")
    for page in _FRAME_PAGES:
        for prefix in ("/devices/%s" % rig.fleet.a1, "/devices/%s" % rig.fleet.live):
            rig.assert_unknown("GET", prefix + page, "frameless")
        if page in FRAME_PAGE_REDIRECTS:
            status, headers, _body = rig.get(page, "frameless")
            assert (status, headers["Location"]) == (303, "/account"), page
        else:
            rig.assert_unknown("GET", page, "frameless")
    for target in _hrefs(rig.page("/account", "frameless")):
        assert not target.startswith("/devices/"), target
        assert _page_path(target) not in _FRAME_PAGES[1:], target


@pytest.fixture
def calendar_calls(monkeypatch):
    """Every outbound calendar transport call; the real transport is
    replaced so a call that slipped past the gate cannot touch the network."""
    calls = []

    def refuse(url, timeout):
        calls.append(url)
        raise OSError("no outbound connection in this test")

    monkeypatch.setattr(calendar_rules, "default_calendar_transport", refuse)
    return calls


_PRIVATE_CALENDAR_URLS = (
    "http://127.0.0.1:%d/x.ics",
    "https://127.0.0.1:%d/x.ics",
    "http://10.0.0.1/x.ics",
    "https://10.0.0.1/x.ics",
    "https://192.168.1.10/x.ics",
    "https://169.254.169.254/latest/x.ics",
    "https://localhost/x.ics",
    "webcal://127.0.0.1/x.ics",
)


@pytest.mark.parametrize("template", _PRIVATE_CALENDAR_URLS)
def test_a_user_calendar_url_aimed_at_a_private_address_is_rejected_with_no_fetch(
        rig, calendar_calls, template):
    url = template % rig.server.port if "%d" in template else template
    own = rig.fleet.a1
    status, headers, _b = rig.request(
        "POST", "/devices/%s/settings/calendar/connect" % own, "a",
        data=_form(calendar_url=url))
    assert status == 303
    assert headers["Location"].startswith("/devices/%s/display" % own)
    assert "calendar_error=invalid" in headers["Location"]
    assert calendar_calls == []
    secret = os.path.join(
        device_dir(rig.state_dir, own), calendar_registry.CALENDAR_SECRET_FILENAME)
    assert not os.path.exists(secret)
    shown = rig.page(headers["Location"].split("#")[0], "a")
    assert escape_html(i18n.t(calendar_settings.CALENDAR_ERROR_INVALID)) in shown


@pytest.mark.parametrize("template", _PRIVATE_CALENDAR_URLS)
def test_a_private_calendar_url_in_the_settings_form_is_never_fetched(
        rig, calendar_calls, template):
    url = template % rig.server.port if "%d" in template else template
    rig.request(
        "POST", "/devices/%s/settings" % rig.fleet.a1, "a",
        data=_form(calendar_url=url))
    assert calendar_calls == []


def test_the_calendar_connect_route_is_a_404_on_another_users_frame(rig, calendar_calls):
    rig.assert_unknown(
        "POST", "/devices/%s/settings/calendar/connect" % rig.fleet.b1, "a",
        data=_form(calendar_url="https://example.test/x.ics"))
    assert calendar_calls == []
    assert not os.path.exists(os.path.join(
        device_dir(rig.state_dir, rig.fleet.b1), calendar_registry.CALENDAR_SECRET_FILENAME))


def test_the_provisioned_config_file_stays_valid_json_after_a_user_save(rig):
    rig.request(
        "POST", "/devices/%s/settings" % rig.fleet.a1, "a",
        data=_form(quiet_hours_start="20:00"))
    path = os.path.join(device_dir(rig.state_dir, rig.fleet.a1), "device_config.json")
    with open(path) as fh:
        assert isinstance(json.load(fh), dict)


# --- who may change the wake interval ------------------------------------------

def _settings_post(rig, who, **fields):
    return rig.request(
        "POST", "/devices/%s/settings" % rig.fleet.a1, who, data=_form(**fields))


@pytest.mark.parametrize("scope", ["display", "device", "all"])
def test_a_users_posted_wake_interval_is_dropped_whatever_the_scope(rig, scope):
    before = _admin_only_values(rig, rig.fleet.a1)
    status, _headers, _body = _settings_post(
        rig, "a", wake_interval_s="600", scope=scope, theme="black")
    assert status == 303
    assert _admin_only_values(rig, rig.fleet.a1) == before


def test_an_administrator_changes_the_wake_interval_on_the_device_page_within_bounds(rig):
    status, _headers, _body = _settings_post(
        rig, "admin", wake_interval_s="1200", scope="device",
        return_to="/device")
    assert status == 303
    assert _admin_only_values(rig, rig.fleet.a1)["wake_interval_s"] == 1200
    below = str(device_config.WAKE_INTERVAL_MIN_S - 1)
    status, _headers, body = _settings_post(
        rig, "admin", wake_interval_s=below, scope="device", return_to="/device")
    assert status == 200
    assert _admin_only_values(rig, rig.fleet.a1)["wake_interval_s"] == 1200


def test_no_refresh_card_on_personalisation_for_either_role_and_device_keeps_it(rig):
    for who in ("a", "admin"):
        display = rig.page("/devices/%s/display" % rig.fleet.a1, who)
        assert 'name="wake_interval_s"' not in display, who
        assert "wake-interval" not in display, who
    assert 'name="wake_interval_s"' in rig.page(
        "/fleet?frame=%s" % rig.fleet.a1, "admin")
