"""Links, forms and image URLs rendered on a non-live device's pages stay under
that device's /devices/<id> prefix; global routes and the live frame's
un-prefixed pages never carry it. Real app subprocess over a seeded
two-device fleet.
"""
import re

import pytest

from companion import routes
from companion.test_device_helpers import get, start_fleet_app
from companion_markup import parse_html

LIVE_PAGES = ("/", "/display", "/flights", "/airlines", "/health", "/device")
NAV_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    app = start_fleet_app(module_app_server_factory)
    get(app, "/display")
    return app


def _prefix(device):
    return "/devices/%s" % device.id


def _page(app, path):
    status, _headers, body = get(app, path)
    assert status == 200, path
    return body


def _hrefs(body, *, within=None):
    root = parse_html(body)
    if within:
        root = root.select_one(within)
    return [node.attrs.get("href", "") for node in root.find_all("a")]


def _actions(body):
    return [node.attrs.get("action", "") for node in parse_html(body).find_all("form")]


def _scoped_nav(prefix, route):
    return prefix + route


def test_nav_links_carry_the_device_prefix(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/health")
    for container in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = _hrefs(body, within=container)
        for route in NAV_ROUTES:
            assert _scoped_nav(prefix, route) in hrefs, (container, route)
            if route != "/":
                assert route not in hrefs, (container, route)


def test_update_link_is_never_prefixed(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/health")
    for container in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = _hrefs(body, within=container)
        assert "/update" in hrefs, container
        assert prefix + "/update" not in hrefs, container


def test_active_nav_state_resolves_from_the_unprefixed_route(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/health")
    current = [
        node.attrs["href"] for node in
        parse_html(body).select_one("nav.sidebar-nav").find_all("a")
        if node.attrs.get("aria-current") == "page"]
    assert current == [prefix + "/health"]


def test_quick_switch_forms_post_under_the_prefix_with_unprefixed_return_to(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/")
    forms = [
        node for node in parse_html(body).find_all("form")
        if "data-quick-switch" in node.attrs]
    assert forms
    for form in forms:
        assert form.attrs["action"].startswith(prefix + "/quick/")
        return_to = [
            hidden.attrs["value"] for hidden in form.find_all("input")
            if hidden.attrs.get("name") == "return_to"]
        assert return_to and not any("/devices/" in value for value in return_to)


def test_led_form_posts_under_the_prefix(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/device")
    assert prefix + "/quick/led" in _actions(body)
    assert "/quick/led" not in _actions(body)


def test_flash_undo_action_posts_under_the_prefix(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/display?flash=display_on")
    toast = parse_html(body).select_one("form.toast__action-form")
    assert toast.attrs["action"] == prefix + "/quick/display"
    return_to = [
        hidden.attrs["value"] for hidden in toast.find_all("input")
        if hidden.attrs.get("name") == "return_to"]
    assert return_to == ["/display"]


def test_flash_link_action_and_dismiss_keep_the_prefix(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/airlines?flash=manual_prefix_stale")
    root = parse_html(body)
    assert prefix + "/health" in [
        node.attrs.get("href") for node in root.find_all("a", cls="toast__action")]
    assert prefix + "/airlines" in [
        node.attrs.get("href") for node in root.find_all("a", cls="toast__dismiss")]


@pytest.mark.parametrize("path", LIVE_PAGES)
def test_unprefixed_pages_carry_no_device_prefix(app, path):
    body = _page(app, path)
    assert "/devices/" not in body
    assert not re.search(r'(?:href|action|src)="/devices', body)


def test_unprefixed_flash_toast_carries_no_device_prefix(app):
    body = _page(app, "/display?flash=display_on")
    assert "/devices/" not in body
    toast = parse_html(body).select_one("form.toast__action-form")
    assert toast.attrs["action"] == "/quick/display"


def test_the_helper_agrees_with_the_route_table():
    assert routes.match("GET", "/update", "")[0].device_scoped is False
