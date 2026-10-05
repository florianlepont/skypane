"""Real-browser checks of the toast family: with scripts a flash toast floats
top centre over the content column on desktop and above the tab bar on a
phone without moving the page; success and info hide on their own after the
dwell and pending ones after 12 s, paused while hovered, focused or while the
document is hidden; error and warning toasts never hide on their own; reduced
motion drops the slide and the countdown; the dismiss control works from the keyboard and never
leaves focus stranded; the quick-switch failure is the same error toast; and
with scripts blocked the same toast sits in flow and its dismiss link
reloads the page without the flash."""
from urllib.parse import urlsplit

import pytest

from companion import auth, flash, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_PHONE,
    _login,
    _no_js_page,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

TOAST = ".toast-region--flash .toast"
LIVE_TOAST = ".toast-region--live .toast"
DWELL_MS = 6000
LONG_DWELL_MS = 12000

_SUCCESS_FLASH = (layout.DISPLAY_ROUTE, flash.FLASH_KEY_CALENDAR_CONNECT_OK)
_INFO_FLASH = (layout.HOME_ROUTE, flash.FLASH_KEY_POLL_ALREADY_RUNNING)
_ERROR_FLASH = (layout.DISPLAY_ROUTE, flash.FLASH_KEY_SAVE_FAILED)
_PENDING_FLASH = (layout.HOME_ROUTE, flash.FLASH_KEY_QUIET_ON)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", clock=False, **kwargs):
    context = new_context(viewport=viewport, **kwargs)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                          "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    if clock:
        page.clock.install()
    return context, page


def _goto(page, server, route, key=None):
    page.goto(server.base_url() + route + ("?flash=%s" % key if key else ""))
    page.locator("main").wait_for(state="visible")


def _rect(page, selector):
    return page.evaluate(
        "s => { const r = document.querySelector(s).getBoundingClientRect();"
        " return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; }", selector)


def _toast_count(page, selector=TOAST):
    return page.locator(selector).count()


@pytest.mark.parametrize("route,key", (_ERROR_FLASH, _PENDING_FLASH), ids=("error", "pending"))
def test_desktop_toast_floats_top_centre_without_moving_the_page(new_context, server, route, key):
    """at 1280px the flash toast is fixed near the top, centred over the content column (not
    the sidebar), and the page title sits exactly where it sits with no flash at all"""
    context, page = _open(new_context, server)
    try:
        _goto(page, server, route)
        title_without = _rect(page, ".page-title")
        _goto(page, server, route, key)
        assert page.evaluate(
            "s => getComputedStyle(document.querySelector(s).parentNode).position",
            TOAST) == "fixed"
        toast = _rect(page, TOAST)
        main = _rect(page, "main")
        assert 0 <= toast["top"] <= 24, "expected the toast in the top gutter, got %r" % toast
        centre = (toast["left"] + toast["right"]) / 2
        main_centre = (main["left"] + main["right"]) / 2
        assert abs(centre - main_centre) <= 24, (
            "expected the toast centred over the content column (%.0f), got %.0f"
            % (main_centre, centre))
        assert toast["left"] >= _rect(page, ".dashboard-sidebar")["right"], (
            "the toast must not cover the sidebar")
        assert _rect(page, ".page-title") == title_without, (
            "a floating toast must not shift the page")
    finally:
        context.close()


def test_phone_toast_sits_above_the_tab_bar_without_moving_the_page(new_context, server):
    """at 390px the toast spans the width just above the bottom tab bar, within thumb reach,
    and the page title does not move"""
    context, page = _open(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        route, key = _PENDING_FLASH
        _goto(page, server, route)
        title_without = _rect(page, ".page-title")
        _goto(page, server, route, key)
        toast = _rect(page, TOAST)
        tab_bar = _rect(page, ".tab-bar")
        assert toast["bottom"] <= tab_bar["top"], "the toast must sit above the tab bar"
        assert tab_bar["top"] - toast["bottom"] <= 24, "expected the toast right above the bar"
        assert toast["left"] >= 0 and toast["right"] <= VIEWPORT_PHONE["width"]
        assert _rect(page, ".page-title") == title_without
    finally:
        context.close()


@pytest.mark.parametrize("route,key", (_SUCCESS_FLASH, _INFO_FLASH), ids=("success", "info"))
def test_success_and_info_hide_after_the_dwell(new_context, server, route, key):
    """a success or info toast is still there just before the dwell and gone just after it,
    with its timer hairline drawn while it counts down"""
    context, page = _open(new_context, server, clock=True)
    try:
        _goto(page, server, route, key)
        assert page.locator(TOAST + " .toast__timer").is_visible()
        page.clock.run_for(DWELL_MS - 500)
        assert _toast_count(page) == 1, "hid too early"
        page.clock.run_for(1000)
        assert _toast_count(page) == 0, "expected the toast gone after the dwell"
    finally:
        context.close()


def test_auto_hide_pauses_on_hover_focus_and_hidden_document(new_context, server):
    """hovering the toast, focusing a control inside it, or hiding the document each pause the
    countdown; it resumes with the time that was left once the cause ends"""
    context, page = _open(new_context, server, clock=True)
    try:
        route, key = _SUCCESS_FLASH
        _goto(page, server, route, key)
        page.clock.run_for(2000)
        page.hover(TOAST)
        page.clock.run_for(20000)
        assert _toast_count(page) == 1, "hover must pause the countdown"
        assert "is-paused" in page.get_attribute(TOAST, "class")
        page.mouse.move(5, 5)
        page.clock.run_for(3500)
        assert _toast_count(page) == 1, "the countdown resumes with the time left, not reset"

        page.focus(TOAST + " .toast__dismiss")
        page.clock.run_for(20000)
        assert _toast_count(page) == 1, "focus inside the toast must pause the countdown"
        page.evaluate("document.activeElement.blur()")
        page.evaluate("""() => {
            Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});
            document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.clock.run_for(20000)
        assert _toast_count(page) == 1, "a hidden document must pause the countdown"
        page.evaluate("""() => {
            Object.defineProperty(document, 'hidden', {configurable: true, get: () => false});
            document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.clock.run_for(1000)
        assert _toast_count(page) == 0, "expected the toast gone once nothing pauses it"
    finally:
        context.close()


def test_pending_hides_after_the_long_dwell(new_context, server):
    """a pending toast is still there at the short dwell and just before 12 s, and gone just
    after it, with its hairline drawn while it counts down"""
    context, page = _open(new_context, server, clock=True)
    try:
        route, key = _PENDING_FLASH
        _goto(page, server, route, key)
        assert page.locator(TOAST + " .toast__timer").is_visible()
        page.clock.run_for(DWELL_MS + 500)
        assert _toast_count(page) == 1, "a pending toast must outlive the short dwell"
        page.clock.run_for(LONG_DWELL_MS - DWELL_MS - 1000)
        assert _toast_count(page) == 1, "hid too early"
        page.clock.run_for(1500)
        assert _toast_count(page) == 0, "expected the toast gone after the long dwell"
    finally:
        context.close()


def test_pending_pauses_on_hover_and_focus(new_context, server):
    """hovering a pending toast, or focusing a control inside it, pauses its countdown"""
    context, page = _open(new_context, server, clock=True)
    try:
        route, key = _PENDING_FLASH
        _goto(page, server, route, key)
        page.clock.run_for(2000)
        page.hover(TOAST)
        page.clock.run_for(60000)
        assert _toast_count(page) == 1, "hover must pause the countdown"
        page.mouse.move(5, 5)
        page.focus(TOAST + " .toast__dismiss")
        page.clock.run_for(60000)
        assert _toast_count(page) == 1, "focus inside the toast must pause the countdown"
        page.evaluate("document.activeElement.blur()")
        page.clock.run_for(LONG_DWELL_MS)
        assert _toast_count(page) == 0, "expected the toast gone once nothing pauses it"
    finally:
        context.close()


@pytest.mark.parametrize("route,key", (_ERROR_FLASH, (layout.DISPLAY_ROUTE,
                                       flash.FLASH_KEY_CALENDAR_SYNC_FAILED)),
                         ids=("error", "warning"))
def test_error_and_warning_never_hide_on_their_own(new_context, server, route, key):
    """an error or warning toast is still there long after both dwells and draws no countdown"""
    context, page = _open(new_context, server, clock=True)
    try:
        _goto(page, server, route, key)
        assert page.locator(TOAST + " .toast__timer").count() == 0
        page.clock.run_for(10 * 60 * 1000)
        assert _toast_count(page) == 1
    finally:
        context.close()


def test_reduced_motion_appears_without_sliding_or_countdown(new_context, server):
    """under prefers-reduced-motion the toast's entrance and its countdown hairline both run
    at a near-zero duration: it simply appears, and no bar visibly drains"""
    context, page = _open(new_context, server, reduced_motion="reduce")
    try:
        route, key = _SUCCESS_FLASH
        _goto(page, server, route, key)
        durations = page.evaluate("""s => {
            const ms = v => parseFloat(v) * (v.endsWith('ms') ? 1 : 1000);
            const toast = document.querySelector(s);
            return [ms(getComputedStyle(toast).animationDuration),
                    ms(getComputedStyle(toast.querySelector('.toast__timer')).animationDuration)];
        }""", TOAST)
        assert all(value < 1 for value in durations), (
            "expected near-zero entrance and countdown durations, got %r ms" % durations)
    finally:
        context.close()


def test_keyboard_dismiss_removes_the_toast_in_place_and_keeps_focus(new_context, server):
    """Enter on the dismiss control removes the toast without a navigation, focus lands on the
    main region rather than being lost, and Escape inside a toast dismisses it too"""
    context, page = _open(new_context, server)
    try:
        route, key = _ERROR_FLASH
        _goto(page, server, route, key)
        page.focus(TOAST + " .toast__dismiss")
        url_before = page.url
        page.keyboard.press("Enter")
        assert _toast_count(page) == 0
        assert page.url == url_before, "dismiss with scripts must not navigate"
        assert page.evaluate("document.activeElement.id") == layout.SKIP_LINK_TARGET_ID

        route, key = _PENDING_FLASH
        _goto(page, server, route, key)
        page.focus(TOAST + " .toast__action")
        page.keyboard.press("Escape")
        assert _toast_count(page) == 0
    finally:
        context.close()


def test_toast_never_takes_focus_on_arrival(new_context, server):
    """a page that arrives with a toast leaves focus where the browser put it"""
    context, page = _open(new_context, server)
    try:
        route, key = _ERROR_FLASH
        _goto(page, server, route, key)
        assert page.evaluate(
            "s => document.querySelector(s).contains(document.activeElement)", TOAST) is False
    finally:
        context.close()


def test_quick_switch_failure_is_a_sticky_error_toast(new_context, make_app_server):
    """a quick switch whose request fails shows the same error toast in the live region,
    which stays past the dwell and goes with its dismiss button"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, clock=True)
    try:
        page.route("**/quick/led", lambda route: route.abort())
        _goto(page, server, layout.DEVICE_ROUTE)
        page.click('[data-quick-region] button[role="switch"]')
        page.locator(LIVE_TOAST).wait_for(state="visible")
        assert "toast--error" in page.get_attribute(LIVE_TOAST, "class")
        page.clock.run_for(10 * 60 * 1000)
        assert _toast_count(page, LIVE_TOAST) == 1
        page.click(LIVE_TOAST + " .toast__dismiss")
        assert _toast_count(page, LIVE_TOAST) == 0
    finally:
        context.close()


def test_without_scripts_the_toast_is_in_flow_and_dismiss_reloads(new_context, server):
    """with scripts blocked the same toast sits in flow under the title (no timer, nothing
    floating) and its dismiss link reloads the page without the flash"""
    route, key = _ERROR_FLASH
    with _no_js_page(new_context, server.base_url(), route + "?flash=%s" % key) as page:
        assert page.evaluate(
            "s => getComputedStyle(document.querySelector(s).parentNode).position",
            TOAST) == "static"
        assert _rect(page, TOAST)["top"] > _rect(page, ".page-title")["bottom"]
        page.click(TOAST + " .toast__dismiss")
        page.wait_for_load_state("load")
        assert urlsplit(page.url).path == route and "flash=" not in page.url
        assert _toast_count(page) == 0
