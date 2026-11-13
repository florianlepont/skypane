"""Links, forms and image URLs rendered on a non-live device's pages stay under
that device's /devices/<id> prefix, the live frame's included once it has a
fleet row; global routes never carry it. Real app subprocess over a seeded
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
LIVE_PAGES = ("/", "/display", "/flights", "/airlines")
PERSONAL_NAV_ROUTES = ("/", "/flights", "/detection", "/display", "/airlines")
# The airline editor is one global list: its address is never frame-scoped.
GLOBAL_CONSOLE_ADDRESS = "/airlines/manage"
SPACE_SWITCH_CLASSES = ("space-switch", "tab-bar__space-link")


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    app = start_fleet_app(module_app_server_factory)
    get(app, "/devices/%s/display" % app.fleet.live.id)
    return app


def _prefix(device):
    return "/devices/%s" % device.id


def _fleet_view(device):
    return "/fleet?frame=%s" % device.id


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


def _inside_frame_switcher(node):
    while node is not None:
        if "frame-menu" in node.attrs.get("class", ""):
            return True
        node = node.parent
    return False


def _prefixed_urls_outside_switcher(body):
    """URL-valued attributes under /devices/ anywhere except the frame
    switcher, whose job is to link to other devices."""
    found = []
    for node in parse_html(body).find_all():
        if _inside_frame_switcher(node):
            continue
        for name, value in node.attrs.items():
            if isinstance(value, str) and value.startswith("/devices/") \
                    and (name in _URL_ATTRS or name.startswith("data-")):
                found.append((name, value))
    return found


def _other_frame_urls_outside_switcher(body, device):
    """The /devices/ URLs outside the switcher that do not stay in `device`."""
    own = _prefix(device)
    return [
        (name, value) for name, value in _prefixed_urls_outside_switcher(body)
        if value != own and not value.startswith(own + "/")]


def _scoped_nav(prefix, route):
    return prefix + route


def test_nav_links_carry_the_device_prefix(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, prefix + "/flights")
    for container in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = _hrefs(body, within=container)
        for route in PERSONAL_NAV_ROUTES:
            assert _scoped_nav(prefix, route) in hrefs, (container, route)
            if route != "/":
                assert route not in hrefs, (container, route)
    body = _page(app, _fleet_view(app.fleet.dev_a))
    for container in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = _hrefs(body, within=container)
        assert GLOBAL_CONSOLE_ADDRESS in hrefs, container
        assert _scoped_nav(prefix, GLOBAL_CONSOLE_ADDRESS) not in hrefs, container


def test_global_links_are_never_prefixed(app):
    prefix = _prefix(app.fleet.dev_a)
    body = _page(app, _fleet_view(app.fleet.dev_a))
    for container in ("nav.sidebar-nav", "nav.tab-bar"):
        hrefs = _hrefs(body, within=container)
        for route in ("/account", "/fleet", "/users", "/audit"):
            assert route in hrefs, (container, route)
            assert prefix + route not in hrefs, (container, route)


def test_active_nav_state_resolves_from_the_unprefixed_route(app):
    body = _page(app, _fleet_view(app.fleet.dev_a))
    current = [
        node.attrs["href"] for node in
        parse_html(body).select_one("nav.sidebar-nav").find_all("a")
        if node.attrs.get("aria-current") == "page"]
    # Health, Device and Update live in the Fleet view, which marks Fleet
    # (a global link, never prefixed) as the current destination.
    assert current == ["/fleet"]


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
    body = _page(app, _fleet_view(app.fleet.dev_a))
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
    assert "/fleet?view=system" in [
        node.attrs.get("href") for node in root.find_all("a", cls="toast__action")]
    assert prefix + "/airlines" in [
        node.attrs.get("href") for node in root.find_all("a", cls="toast__dismiss")]


@pytest.mark.parametrize("path", LIVE_PAGES)
def test_the_live_frame_pages_stay_under_the_live_frames_own_prefix(app, path):
    live = app.fleet.live
    body = _page(app, _prefix(live) + path)
    assert _prefixed_urls_outside_switcher(body)
    assert _other_frame_urls_outside_switcher(body, live) == []


def test_the_live_frame_flash_toast_posts_under_its_own_prefix(app):
    live = app.fleet.live
    body = _page(app, _prefix(live) + "/display?flash=display_on")
    assert _other_frame_urls_outside_switcher(body, live) == []
    toast = parse_html(body).select_one("form.toast__action-form")
    assert toast.attrs["action"] == _prefix(live) + "/quick/display"


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
    get(app, "/devices/%s/display" % app.fleet.live.id)
    return app


def _local_urls(body):
    """Every local URL attribute value on the page, including the dialog's
    data-view-panel-* address attributes. The frame sheet is left out (its
    job is to link to other frames). The space switch leads to a
    destination the server resolves (the administrator's own frame), so it is
    not a frame-scoped address."""
    urls = []
    for node in parse_html(body).find_all():
        if any(name in str(node.attrs.get("class", "")) for name in SPACE_SWITCH_CLASSES):
            continue
        if _inside_frame_switcher(node):
            continue
        for name, value in node.attrs.items():
            if (name in _URL_ATTRS or name.startswith("data-view-panel-")) \
                    and isinstance(value, str) and value.startswith("/") \
                    and not value.startswith("//"):
                urls.append(value)
    return urls


def _device_scoped(url, method="GET"):
    path = re.split(r"[?#]", url, maxsplit=1)[0]
    if path == GLOBAL_CONSOLE_ADDRESS and method == "GET":
        return False
    found = routes.match(method, path, "")
    return found is not None and found[0].device_scoped


def _assert_no_escape(body, prefix):
    """No device-scoped route is addressed without the device's prefix."""
    for url in _local_urls(body):
        if url.startswith(prefix):
            continue
        assert not (_device_scoped(url) or _device_scoped(url, "POST")), url


@pytest.mark.parametrize("page", (
    "/airlines/manage", "/airlines/manage?resolve=XQZ",
    "/airlines/manage?resolve=ABC"))
def test_airlines_page_keeps_every_scoped_link_under_the_prefix(seeded, page):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + page)
    _assert_no_escape(body, prefix)
    urls = _local_urls(body)
    assert any(url.startswith(prefix + "/airlines") for url in urls)
    assert any(url.startswith(prefix + "/airlines/resolve") for url in urls)


def test_the_collection_keeps_every_scoped_link_under_the_prefix(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines")
    _assert_no_escape(body, prefix)
    urls = _local_urls(body)
    assert any(url.startswith(prefix + "/airlines") for url in urls)
    assert not any(url.startswith(prefix + "/airlines/") for url in urls)


def test_airlines_page_carries_manual_delete_and_upload_actions(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines/manage")
    urls = _local_urls(body)
    assert any(
        url.startswith(prefix + "/airlines/manual-resolutions/") for url in urls)
    assert any(url.startswith(prefix + "/illustration/") for url in urls)
    assert any(url.startswith(prefix + "/airlines/rename") for url in urls)


def test_resolve_fallback_back_link_stays_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines/manage?resolve=ABC")
    fallback = parse_html(body).select_one("[data-resolve-fallback]")
    hrefs = [node.attrs.get("href") for node in fallback.find_all("a")]
    assert prefix + "/airlines/manage" in hrefs
    assert "/airlines/manage" not in hrefs


def test_resolve_dialog_forms_stay_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/airlines/manage")
    assert prefix + "/airlines/resolve" in _actions(body)
    assert "/airlines/resolve" not in _actions(body)
    assert prefix + "/airlines/rename" in _actions(body)
    assert "/airlines/rename" not in _actions(body)


def test_calendar_connection_page_actions_and_links_stay_in_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/display/calendar/connect")
    page = parse_html(body).select_one("div.form-view")
    actions = [node.attrs.get("action") for node in page.find_all("form")]
    assert prefix + "/settings/calendar/connect" in actions
    assert prefix + "/settings/calendar/disconnect" in actions
    for link in page.find_all("a"):
        if link.attrs["href"].startswith("#"):
            continue
        assert link.attrs["href"].startswith(prefix + "/display/calendar"), link.attrs
    bar = parse_html(body).select_one(".dirty-bar")
    assert bar.select_one("a.dirty-bar__cancel").attrs["href"] == prefix + "/display/calendar"


def test_special_look_pages_post_and_link_inside_the_device(seeded):
    prefix = _prefix(seeded.fleet.dev_a)
    body = _page(seeded, prefix + "/display/special-looks/new")
    page = parse_html(body).select_one("div.form-view")
    assert [node.attrs.get("action") for node in page.find_all("form")] == [
        prefix + "/settings/rules/add"]
    for link in page.find_all("a"):
        assert link.attrs["href"].startswith(prefix + "/display/special-looks"), link.attrs


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


def test_live_airlines_and_display_pages_stay_under_the_live_prefix(seeded):
    live = seeded.fleet.live
    for path in ("/airlines", "/airlines/manage?resolve=ABC", "/display?sheet=manage"):
        body = _page(seeded, _prefix(live) + path)
        assert _other_frame_urls_outside_switcher(body, live) == [], path
    # The served frame's Console page still answers without a prefix.
    assert get(seeded, "/airlines/manage?resolve=ABC")[0] == 200


def test_freshness_script_refreshes_its_own_page_and_the_fleet_page_has_no_health_nav_link(seeded):
    status, _headers, script = get(seeded, "/static/freshness.js")
    assert status == 200
    assert "fetch(window.location.href" in script
    assert 'a[href$="/fleet"]' in script
    selector = 'a[href$="/health"]'
    root = parse_html(_page(seeded, _fleet_view(seeded.fleet.dev_a)))
    assert not any(
        node.attrs.get("href", "").endswith("/health")
        for node in root.select_one("nav.sidebar-nav").find_all("a")), selector
    # The swapped nav link is the Fleet entry, the one that carries the dot.
    assert any(
        node.attrs.get("href", "").endswith("/fleet")
        for node in root.select_one("nav.sidebar-nav").find_all("a"))


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
    assert trigger.attrs["href"].startswith("/devices/d_0123abcd/airlines/manage?resolve=")
    assert trigger.attrs["data-view-panel-upload-action"].startswith(
        "/devices/d_0123abcd/illustration/")
    assert "return=health" in trigger.attrs["data-view-panel-upload-action"]
    assert trigger.attrs["data-view-panel-delete-action"].startswith(
        "/devices/d_0123abcd/airlines/manual-resolutions/")
    assert trigger.attrs["data-view-panel-return"] == "health"
