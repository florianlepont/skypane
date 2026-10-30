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
from server.plane import calendar_rules, manual_resolutions
import server.state_store as state_store

_URL_ATTRS = ("href", "action", "src")
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


def _inside_device_selector(node):
    while node is not None:
        if "device-selector" in node.attrs.get("class", ""):
            return True
        node = node.parent
    return False


def _prefixed_urls_outside_selector(body):
    """URL-valued attributes under /devices/ anywhere except the device
    selector, whose job is to link to other devices."""
    found = []
    for node in parse_html(body).find_all():
        if _inside_device_selector(node):
            continue
        for name, value in node.attrs.items():
            if isinstance(value, str) and value.startswith("/devices/") \
                    and (name in _URL_ATTRS or name.startswith("data-")):
                found.append((name, value))
    return found


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
    assert _prefixed_urls_outside_selector(_page(app, path)) == []


def test_unprefixed_flash_toast_carries_no_device_prefix(app):
    body = _page(app, "/display?flash=display_on")
    assert _prefixed_urls_outside_selector(body) == []
    toast = parse_html(body).select_one("form.toast__action-form")
    assert toast.attrs["action"] == "/quick/display"


def test_the_helper_agrees_with_the_route_table():
    assert routes.match("GET", "/update", "")[0].device_scoped is False


# --- airlines, resolve dialog, calendar sheet, previews, freshness ----------

PREFIX_REGISTRY = {
    "XQZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XQZ123"}}
CALENDAR_URL = "https://device-links.example/feed.ics?token=DEVICELINKSTOKEN"


def _seed_airline_state(fleet):
    for device in (fleet.dev_a, fleet.dev_b, fleet.live):
        state_store.save_poll_state(device.state_dir, {"unresolved_prefixes": PREFIX_REGISTRY})
        manual_resolutions.add_entry(
            device.state_dir, "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
        calendar_rules.save_calendar_url(device.state_dir, CALENDAR_URL)


@pytest.fixture(scope="module")
def seeded(module_app_server_factory):
    app = start_fleet_app(module_app_server_factory, seed_extra=_seed_airline_state)
    get(app, "/display")
    return app


def _local_urls(body):
    """Every local URL attribute value on the page, including the dialog's
    data-view-panel-* address attributes."""
    urls = []
    for node in parse_html(body).find_all():
        for name, value in node.attrs.items():
            if (name in _URL_ATTRS or name.startswith("data-view-panel-")) \
                    and isinstance(value, str) and value.startswith("/") \
                    and not value.startswith("//"):
                urls.append(value)
    return urls


def _device_scoped(url, method="GET"):
    path = re.split(r"[?#]", url, maxsplit=1)[0]
    found = routes.match(method, path, "")
    return found is not None and found[0].device_scoped


def _assert_no_escape(body, prefix):
    """No device-scoped route is addressed without the device's prefix."""
    for url in _local_urls(body):
        if url.startswith(prefix):
            continue
        assert not (_device_scoped(url) or _device_scoped(url, "POST")), url


@pytest.mark.parametrize("query", ("", "?resolve=XQZ", "?resolve=ABC"))
def test_airlines_page_keeps_every_scoped_link_under_the_prefix(seeded, query):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines" + query)
    _assert_no_escape(body, prefix)
    urls = _local_urls(body)
    assert any(url.startswith(prefix + "/airlines") for url in urls)
    assert any(url.startswith(prefix + "/airlines/resolve") for url in urls)


def test_airlines_page_carries_manual_delete_and_upload_actions(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines")
    urls = _local_urls(body)
    assert any(
        url.startswith(prefix + "/airlines/manual-resolutions/") for url in urls)
    assert any(url.startswith(prefix + "/illustration/") for url in urls)
    assert any(url.startswith(prefix + "/airlines/rename") for url in urls)


def test_resolve_fallback_back_link_stays_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines?resolve=ABC")
    fallback = parse_html(body).select_one("[data-resolve-fallback]")
    hrefs = [node.attrs.get("href") for node in fallback.find_all("a")]
    assert prefix + "/airlines" in hrefs
    assert "/airlines" not in hrefs


def test_resolve_dialog_forms_stay_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines")
    assert prefix + "/airlines/resolve" in _actions(body)
    assert "/airlines/resolve" not in _actions(body)
    assert prefix + "/airlines/rename" in _actions(body)
    assert "/airlines/rename" not in _actions(body)


def test_calendar_sheet_actions_and_close_links_stay_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/display?sheet=manage")
    sheet = parse_html(body).select_one("dialog[data-calendar-sheet]")
    actions = [node.attrs.get("action") for node in sheet.find_all("form")]
    assert prefix + "/settings/calendar/connect" in actions
    assert prefix + "/settings/calendar/disconnect" in actions
    for link in sheet.find_all("a"):
        assert link.attrs["href"].startswith(prefix + "/display#"), link.attrs


def test_frame_preview_urls_resolve_under_the_prefix(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/display")
    sources = [
        node.attrs["src"] for node in parse_html(body).find_all("img")
        if "frame-preview" in node.attrs.get("src", "")]
    assert sources
    for source in sources[:2]:
        assert source.startswith(prefix + "/frame-preview/")
        status, headers, _ = get(seeded, source)
        assert status == 200
        assert headers["Content-Type"].startswith("image/png")


def test_unprefixed_airlines_and_display_pages_carry_no_prefix(seeded):
    for path in ("/airlines", "/airlines?resolve=ABC", "/display?sheet=manage", "/health"):
        assert _prefixed_urls_outside_selector(_page(seeded, path)) == [], path


def test_freshness_script_refreshes_its_own_page_and_finds_the_prefixed_health_link(seeded):
    status, _headers, script = get(seeded, "/static/freshness.js")
    assert status == 200
    assert "fetch(window.location.href" in script
    assert 'a[href$="/health"]' in script
    selector = 'a[href$="/health"]'
    prefix = _prefix(seeded.fleet.dev_a)
    root = parse_html(_page(seeded, prefix + "/health"))
    assert any(
        node.attrs.get("href", "").endswith("/health")
        for node in root.select_one("nav.sidebar-nav").find_all("a")), selector


def test_step_b_trigger_addresses_stay_in_the_device_and_return_stays_plain(tmp_path):
    from companion import device_scope, resolve_dialog
    manual_resolutions.add_entry(
        str(tmp_path), "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
    device = device_scope.Device(
        id="d_0123abcd", name="x", hardware_type="sim-ee02-clone",
        state_path="devices/d_0123abcd", state_dir=str(tmp_path), is_live=False)
    device_scope.set_request_scope(device, [device])
    try:
        html = resolve_dialog.step_b_trigger_html(
            str(tmp_path), "ABC", resolve_dialog.RETURN_HEALTH)
    finally:
        device_scope.set_request_scope(None, ())
    trigger = parse_html(html).select_one("a[hidden]")
    assert trigger.attrs["href"].startswith("/devices/d_0123abcd/airlines?resolve=")
    assert trigger.attrs["data-view-panel-upload-action"].startswith(
        "/devices/d_0123abcd/illustration/")
    assert "return=health" in trigger.attrs["data-view-panel-upload-action"]
    assert trigger.attrs["data-view-panel-delete-action"].startswith(
        "/devices/d_0123abcd/airlines/manual-resolutions/")
    assert trigger.attrs["data-view-panel-return"] == "health"
