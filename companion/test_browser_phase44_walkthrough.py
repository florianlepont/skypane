"""Evidence-first browser walkthrough for the authenticated companion routes.

The module keeps production code untouched.  It records the base companion
experience that the owner will review before authorising any focused polish.
"""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _click_control,
    _login,
    _save_via_bar,
    _wait_for_bar,
    seed_state_dir,
    seed_two_releases,
)
from server import device_config, state_store


pytestmark = pytest.mark.browser


ROUTES = (
    ("home", layout.HOME_ROUTE),
    ("display", layout.DISPLAY_ROUTE),
    ("flights", layout.FLIGHTS_ROUTE),
    ("airlines", layout.AIRLINES_ROUTE),
    ("health", layout.HEALTH_ROUTE),
    ("device", layout.DEVICE_ROUTE),
    ("update", layout.UPDATE_ROUTE),
)
VIEWPORTS = (
    ("1280", VIEWPORT_DESKTOP),
    ("390", VIEWPORT_PHONE),
    ("360", VIEWPORT_MIN_SUPPORTED),
)


def _seed_walkthrough_state(state_dir):
    seed_state_dir(state_dir)
    seed_two_releases(state_dir)


def _seed_intentional_sleep_state(state_dir):
    _seed_walkthrough_state(state_dir)
    state_store.save_poll_state(state_dir, {"unresolved_prefixes": {}})
    device_config.save_device_config(
        state_dir,
        theme=device_config.THEME_IDS[0],
        tracked_runway=device_config.RUNWAY_IDS[0],
        wake_interval_s=300,
        quiet_hours_enabled=True,
        quiet_hours_start="00:00",
        quiet_hours_end="23:59",
        display_enabled=True,
    )


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_walkthrough_state, fake_providers=True)


def _open_authenticated_page(new_context, base_url, lang, viewport, route):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url,
    }])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    page.locator("main").wait_for(state="visible")
    return context, page


@pytest.mark.parametrize("route_name,route", ROUTES, ids=[item[0] for item in ROUTES])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[item[0] for item in VIEWPORTS])
def test_authenticated_route_matrix_has_primary_content_and_no_page_overflow(
        new_context, server, route_name, route, lang, viewport_name, viewport):
    """Every authenticated route remains usable in both languages and three viewports."""
    context, page = _open_authenticated_page(
        new_context, server.base_url(), lang, viewport, route)
    try:
        if page.evaluate("() => document.documentElement.lang") != lang:
            raise AssertionError("%s/%s: served document language did not resolve" % (route_name, lang))
        if page.url != server.base_url() + route:
            raise AssertionError("%s/%s: authenticated navigation landed on %s" % (
                route_name, lang, page.url))
        if not page.locator("main h1").first.inner_text().strip():
            raise AssertionError("%s/%s: route rendered no primary heading" % (route_name, lang))
        active_routes = page.locator('a[aria-current="page"]').evaluate_all(
            "els => els.map(el => el.getAttribute('href'))")
        if route not in active_routes:
            raise AssertionError("%s/%s: navigation exposes no active route" % (route_name, lang))
        overflow = _assert_no_page_overflow(
            page, "%s/%s/%s" % (route_name, lang, viewport_name), viewport["width"])
        if overflow:
            raise AssertionError(overflow)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_display_setting_saves_and_reports_a_keyboard_focusable_control(
        new_context, make_app_server, lang):
    """A real Display change confirms, persists, and leaves a focus witness."""
    server = make_app_server(seed=_seed_walkthrough_state, fake_providers=True)
    before = device_config.load_device_config(server.tmpdir)
    target = next(item for item in device_config.RUNWAY_IDS if item != before["tracked_runway"])
    context, page = _open_authenticated_page(
        new_context, server.base_url(), lang, VIEWPORT_MIN_SUPPORTED, layout.DISPLAY_ROUTE)
    try:
        selector = 'input[name="tracked_runway"][value="%s"]' % target
        page.locator(selector).focus()
        if not page.evaluate("sel => document.activeElement === document.querySelector(sel)", selector):
            raise AssertionError("%s: native runway control could not receive keyboard focus" % lang)
        _click_control(page, selector)
        _wait_for_bar(page)
        _save_via_bar(page)
        after = device_config.load_device_config(server.tmpdir)
        if after["tracked_runway"] != target:
            raise AssertionError("%s: served save feedback did not persist the selected runway" % lang)
        if page.locator('.toast-region--flash .toast[role="status"]').count() != 1:
            raise AssertionError("%s: successful save did not render its served confirmation" % lang)
    finally:
        context.close()


@pytest.mark.parametrize("route", [layout.FLIGHTS_ROUTE, layout.AIRLINES_ROUTE])
def test_data_review_disclosures_open_from_the_keyboard(new_context, server, route):
    """The existing native disclosure controls remain keyboard-operable."""
    context, page = _open_authenticated_page(
        new_context, server.base_url(), "en", VIEWPORT_PHONE, route)
    try:
        summary = page.locator("details summary").first
        summary.focus()
        summary.press("Enter")
        if not page.locator("details").first.evaluate("el => el.open"):
            raise AssertionError("%s: keyboard activation did not open the first disclosure" % route)
    finally:
        context.close()


def test_health_warning_and_intentional_sleep_are_seeded_as_separate_review_states(
        new_context, module_app_server_factory):
    """The walkthrough uses distinct fixtures before the owner judges either status state."""
    warning_server = module_app_server_factory(seed=_seed_walkthrough_state, fake_providers=True)
    sleep_server = module_app_server_factory(seed=_seed_intentional_sleep_state, fake_providers=True)
    contexts = []
    try:
        for label, served in (("warning", warning_server), ("scheduled-sleep", sleep_server)):
            context, page = _open_authenticated_page(
                new_context, served.base_url(), "en", VIEWPORT_DESKTOP, layout.HEALTH_ROUTE)
            contexts.append(context)
            if not page.locator("main").inner_text().strip():
                raise AssertionError("%s fixture rendered no Health content" % label)
        if device_config.load_device_config(sleep_server.tmpdir)["quiet_hours_start"] != "00:00":
            raise AssertionError("scheduled-sleep fixture did not retain its all-day quiet window")
    finally:
        for context in contexts:
            context.close()
