"""Behaviour tests for a user principal's navigation: the sidebar, the phone
tab bar and the wordmark link, all derived from the route table so a link
exists only for a page the user can open.
"""
import re

import pytest

import companion.device_scope as device_scope
import companion.layout as layout
import companion.prefs as prefs
from companion import routes, ui_nav

FRAME = device_scope.Device(
    id="abc123", name="Kitchen", hardware_type="x", state_path="devices/abc123",
    state_dir="", is_live=False)

FRAME_PAGES = ("/", "/flights", "/detection", "/display", "/airlines", "/health")
ADMIN_ONLY_LABELS = (
    "Admin", "Console", "Fleet", "Users", "Audit", "Releases", "Update", "Device",
    "Health", "My views", "My frame")


@pytest.fixture(autouse=True)
def _reset_state():
    prefs.set_request_principal(None)
    prefs.set_request_prefs(lang="en")
    device_scope.set_request_scope(None, ())
    yield
    prefs.set_request_principal(None)
    device_scope.set_request_scope(None, ())


def _open_frame_pages_to_users(monkeypatch, extra=()):
    """The route table as it stands once the frame pages are signed-in."""
    opened = tuple(
        route._replace(access=routes.SIGNED_IN)
        if route.method == "GET" and isinstance(route.matcher, routes.Exact)
        and route.matcher.path in FRAME_PAGES else route
        for route in routes.ROUTES)
    monkeypatch.setattr(routes, "ROUTES", opened + tuple(extra))


def _close_frame_pages_to_users(monkeypatch):
    """The route table with every frame page admin-only again."""
    closed = tuple(
        route._replace(access=routes.ADMIN_ONLY)
        if route.method == "GET" and route.device_scoped else route
        for route in routes.ROUTES)
    monkeypatch.setattr(routes, "ROUTES", closed)


def _as_user_with_frame():
    prefs.set_request_principal("user", "user")
    device_scope.set_request_scope(FRAME, [FRAME])


def _links(markup):
    return re.findall(r'<a class="[^"]*" href="([^"]+)"[^>]*>(.*?)</a>', markup, re.S)


def _hrefs(markup):
    return [href for href, _text in _links(markup)]


def test_user_sidebar_lists_the_reachable_frame_pages_then_account(monkeypatch):
    _open_frame_pages_to_users(monkeypatch)
    _as_user_with_frame()
    sidebar = layout.sidebar_nav("home")
    prefix = "/devices/abc123"
    assert _hrefs(sidebar) == [
        prefix + "/", prefix + "/flights", prefix + "/detection", prefix + "/display",
        prefix + "/airlines", "/account"]
    for label in ADMIN_ONLY_LABELS:
        assert label not in sidebar
    assert "nav-group__label" not in sidebar
    assert "nav-notification" not in sidebar


def test_user_sidebar_without_reachable_frame_pages_is_account_only(monkeypatch):
    _close_frame_pages_to_users(monkeypatch)
    _as_user_with_frame()
    assert _hrefs(layout.sidebar_nav("account")) == ["/account"]


def test_user_sidebar_without_a_frame_is_account_only(monkeypatch):
    _open_frame_pages_to_users(monkeypatch)
    prefs.set_request_principal("user", "user")
    assert _hrefs(layout.sidebar_nav("account")) == ["/account"]


def test_user_phone_tab_bar_needs_a_frame(monkeypatch):
    _open_frame_pages_to_users(monkeypatch)
    prefs.set_request_principal("user", "user")
    assert ui_nav._tab_bar_html("account", device_config={}) == ""

    _as_user_with_frame()
    bar = ui_nav._tab_bar_html("home", device_config={})
    prefix = "/devices/abc123"
    cells, sheet = bar.split('<div class="tab-bar__more-panel">')
    assert _hrefs(cells) == [
        prefix + "/", prefix + "/flights", prefix + "/airlines", prefix + "/display",
        prefix + "/detection"]
    assert _hrefs(sheet) == ["/account"]
    assert 'aria-current="page"' in bar
    for label in ADMIN_ONLY_LABELS:
        assert label not in bar


def test_user_tab_bar_is_empty_when_only_account_is_reachable(monkeypatch):
    _close_frame_pages_to_users(monkeypatch)
    _as_user_with_frame()
    assert ui_nav._tab_bar_html("account", device_config={}) == ""


def test_a_user_sidebar_never_links_locations_whatever_the_route_table_holds(monkeypatch):
    locations = routes.Route(
        "GET", routes.Exact("/locations"), lambda handler, match: None, routes.SIGNED_IN)
    _open_frame_pages_to_users(monkeypatch, extra=(locations,))
    _as_user_with_frame()
    assert "/locations" not in _hrefs(layout.sidebar_nav("home"))


def test_brand_link_goes_to_frame_home_or_account(monkeypatch):
    _close_frame_pages_to_users(monkeypatch)
    _as_user_with_frame()
    assert ui_nav.user_brand_href() == "/account"
    _open_frame_pages_to_users(monkeypatch)
    assert ui_nav.user_brand_href() == "/devices/abc123/"


def test_no_disabled_or_greyed_links_for_a_user(monkeypatch):
    _open_frame_pages_to_users(monkeypatch)
    _as_user_with_frame()
    markup = layout.sidebar_nav("home") + ui_nav._tab_bar_html("home", device_config={})
    assert "disabled" not in markup
    assert "aria-disabled" not in markup
