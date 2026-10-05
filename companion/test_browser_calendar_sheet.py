#!/usr/bin/env python3
"""Real-browser checks of the calendar "Manage" sheet on the Display page: it opens as a modal from
the status row's one button at 390 and 1280 px in both languages and both themes with usable
controls (>= 44 px targets, 16 px field) and no overflow; focus does NOT land on the URL field on
a plain open but DOES on a refused replace; a replace round-trips through the real route and a
refused one leaves the working connection untouched and reopens the sheet with the error; the
connect button shows its pending label while the server reads the link; disconnect confirms
inside the sheet; and with scripts blocked the same flows work through plain links and forms.
"""
from datetime import datetime

import pytest

import companion.test_companion_app_helpers as cah
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _assert_no_page_overflow,
    _in_both_themes, _login, _no_js_page,
)
from companion_app_server import TEST_PASSWORD
from server.plane import calendar_rules

pytestmark = pytest.mark.browser

DIALOG = "#calendar-sheet"
OPENER = ".calendar-status [data-calendar-open]"
URL_INPUT = DIALOG + " #calendar-connect-url"
REPLACE = DIALOG + " [data-calendar-connect] button[type=submit]"
DISCONNECT = DIALOG + " [data-calendar-disconnect] button"
CONFIRM = DIALOG + " [data-calendar-confirm]"
OLD_URL = "https://old-calendar.example/published/2/OLDSECRET?auth=OLDTOKEN"
NEW_URL = "https://new-calendar.example/feed.ics?token=NEWTOKEN"


@pytest.fixture
def server(app_server_in_process):
    return app_server_in_process


def _connect_old(server):
    """An already-connected, healthy calendar holding two flights, read through the real refresh
    path with a stubbed transport."""
    body = cah.ics_body([("AF1234", "CDG", "ORY", 2), ("BA5678", "LHR", "CDG", 4)])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname("old-calendar.example"):
        assert calendar_rules.save_calendar_url(server.state_dir, OLD_URL)
        code, _r = calendar_rules.refresh_calendar_registry(
            server.state_dir, datetime.now().timestamp(), min_interval_s=0)
    assert code == calendar_rules.FETCH_OK


def _open_display(new_context, server, viewport, lang="en", scheme=None):
    extra = {"color_scheme": scheme} if scheme else {}
    context = new_context(viewport=viewport, **extra)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/display")
    page.locator(OPENER).wait_for(state="visible")
    return context, page


def _state(page):
    return page.locator(".calendar-status").get_attribute("data-calendar-state")


def _active_id(page):
    return page.evaluate("() => document.activeElement && document.activeElement.id")


def _is_modal(page):
    return page.locator(DIALOG).evaluate("e => e.open && e.matches(':modal')")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_manage_opens_a_usable_modal_sheet_in_both_themes(new_context, server, viewport, lang):
    """Manage opens the sheet as a modal showing only the masked host, with a 16 px field,
    44 px controls, the dialog inside the viewport and nothing overflowing - light and dark; the
    full link is nowhere in the page"""
    _connect_old(server)
    context, page = _open_display(new_context, server, viewport, lang)
    try:
        assert _state(page) == "ok"
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert _is_modal(page)
        assert _active_id(page) != "calendar-connect-url", "a plain open must not focus the field"
        assert page.locator(DIALOG + " .calendar-masked-url").inner_text() == "old-calendar.example…"
        content = page.content()
        for needle in ("OLDSECRET", "OLDTOKEN", OLD_URL):
            assert needle not in content
        for theme in _in_both_themes(page):
            font_px = page.locator(URL_INPUT).evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
            assert font_px >= 16, (theme, font_px)
            where = "calendar sheet (%s, %s, %d)" % (lang, theme["theme"], viewport["width"])
            for selector in (URL_INPUT, REPLACE, DIALOG + " a.calendar-sheet__cancel",
                             DIALOG + " a.calendar-sheet__close", DISCONNECT):
                _assert_hit_target(page, selector, where)
            box = page.locator(DIALOG).bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], box
            assert box["y"] >= 0 and box["y"] + box["height"] <= viewport["height"], box
            assert page.locator(DIALOG).evaluate("e => e.scrollWidth - e.clientWidth") <= 0
            assert _assert_no_page_overflow(page, where) == ""
        french = "Nouveau lien" in page.locator(DIALOG).inner_text()
        assert french == (lang == "fr")
    finally:
        context.close()


def test_escape_closes_the_sheet_and_returns_focus_to_manage(new_context, server):
    """Escape dismisses the modal and focus goes back to the button that opened it"""
    _connect_old(server)
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(OPENER).focus()
        page.keyboard.press("Enter")
        page.locator(DIALOG + "[open]").wait_for()
        page.keyboard.press("Escape")
        page.locator(DIALOG + "[open]").wait_for(state="detached")
        assert page.evaluate("() => document.activeElement.hasAttribute('data-calendar-open')")
    finally:
        context.close()


def test_replace_round_trips_and_the_page_shows_the_new_flights(new_context, server):
    """pasting a working link replaces the connection: the sheet closes, a confirmation toast
    shows, and the status row counts the new link's flights"""
    _connect_old(server)
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.fill(URL_INPUT, NEW_URL)
        body = cah.ics_body([("AF9999", "ORY", "NCE", 3)])
        with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
                cah.fake_public_hostname("new-calendar.example"):
            page.click(REPLACE)
            page.wait_for_url("**flash=calendar_connect_ok")
        assert page.locator(".toast").first.is_visible()
        assert page.locator(DIALOG + "[open]").count() == 0
        assert _state(page) == "ok"
        assert "1 flight in the next 48 h" in page.locator(".calendar-status__detail").inner_text()
        assert page.locator(".calendar-status__title b").inner_text() == "new-calendar.example"
        assert calendar_rules.configured_calendar_url(server.state_dir) == NEW_URL
    finally:
        context.close()


def test_a_refused_replace_reopens_with_the_error_focuses_the_field_and_keeps_the_old_link(
        new_context, server):
    """an unreachable link: the sheet reopens as a modal on the explicit error with focus on the
    field, the page still shows the old healthy connection and its two flights, and the old link
    is still the stored one"""
    _connect_old(server)
    before = calendar_rules.load_calendar_registry(server.state_dir)
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.fill(URL_INPUT, NEW_URL)
        transport = cah.make_calendar_transport(raise_exc=ConnectionError("boom"))
        with cah.stubbed_calendar_transport(transport), cah.fake_public_hostname("new-calendar.example"):
            page.click(REPLACE)
            page.wait_for_url("**flash=calendar_connect_failed**")
        page.locator(DIALOG + "[open]").wait_for()
        assert _is_modal(page)
        assert _active_id(page) == "calendar-connect-url", "a refused replace focuses the field"
        assert "doesn’t answer" in page.locator("#calendar-connect-url-error").inner_text() \
            or "doesn't answer" in page.locator("#calendar-connect-url-error").inner_text()
        assert page.locator(URL_INPUT).input_value() == ""
        assert "calendar=" not in page.url, "the reopen parameters are dropped from the address"
        page.keyboard.press("Escape")
        assert _state(page) == "ok"
        assert "2 flights in the next 48 h" in page.locator(".calendar-status__detail").inner_text()
        assert calendar_rules.configured_calendar_url(server.state_dir) == OLD_URL
        assert calendar_rules.load_calendar_registry(server.state_dir) == before
    finally:
        context.close()


def test_the_connect_button_shows_a_pending_label_on_submit(new_context, server):
    """a real click on Connect swaps the button's label for the server-rendered 'Checking…' and
    marks the form busy. The navigation itself is held back by a later listener: Playwright cannot
    evaluate in a frame whose navigation response is still pending, so the pending window is
    observed at the submit event, which is where the label is written"""
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.fill(URL_INPUT, NEW_URL)
        assert page.locator(REPLACE).inner_text() == "Connect"
        page.evaluate(
            "() => document.querySelector('[data-calendar-connect]')"
            ".addEventListener('submit', e => e.preventDefault())")
        page.click(REPLACE)
        assert page.locator(REPLACE).inner_text() == "Checking…"
        assert page.locator("[data-calendar-connect]").get_attribute("aria-busy") == "true"
    finally:
        context.close()


def test_disconnect_confirms_inside_the_sheet_and_cancel_backs_out(new_context, server):
    """Disconnect shows an in-sheet confirmation saying what happens to the flights (no native
    confirm dialog), focus on the safe Cancel; Cancel restores the sheet untouched; confirming
    disconnects and clears the flights"""
    _connect_old(server)
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    try:
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(CONFIRM).is_hidden()
        page.click(DISCONNECT)
        assert page.locator(CONFIRM).is_visible()
        assert page.locator(DIALOG + " [data-calendar-disconnect]").is_hidden()
        assert "flights it supplied are deleted" in page.locator(CONFIRM).inner_text()
        assert page.evaluate("() => document.activeElement.hasAttribute('data-calendar-confirm-cancel')")
        page.click(CONFIRM + " [data-calendar-confirm-cancel]")
        assert page.locator(CONFIRM).is_hidden() and page.locator(DISCONNECT).is_visible()
        assert calendar_rules.calendar_is_configured(server.state_dir)
        page.click(DISCONNECT)
        page.click(CONFIRM + " [data-calendar-confirm-yes]")
        page.wait_for_url("**flash=calendar_disconnected")
        assert _state(page) == "none"
        assert not calendar_rules.calendar_is_configured(server.state_dir)
        assert calendar_rules.load_calendar_registry(server.state_dir)["entries"] == []
        assert dialogs == [], "no native confirm() dialog is used any more"
    finally:
        context.close()


def test_the_closed_sheet_reopens_clean_after_a_cancelled_disconnect(new_context, server):
    """closing the sheet mid-confirmation resets it: reopening shows Disconnect, not the question"""
    _connect_old(server)
    context, page = _open_display(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(OPENER).click()
        page.click(DISCONNECT)
        page.keyboard.press("Escape")
        page.locator(OPENER).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(CONFIRM).is_hidden() and page.locator(DISCONNECT).is_visible()
    finally:
        context.close()


# --- scripts blocked -------------------------------------------------------


def _dom_click(page, selector):
    """The DOM's own click(): the in-page (scripts-blocked) sheet sits low on the page, under the
    fixed tab bar on a phone, where a coordinate click can land on the bar."""
    page.eval_on_selector(selector, "el => el.click()")


def _click_centred(page, selector):
    """Click `selector` after centring it in the viewport, so the fixed bottom tab bar (phone
    widths) can never sit over the target while the click's own scroll-into-view retries."""
    target = page.locator(selector).first
    target.wait_for(state="visible")
    target.evaluate("el => el.scrollIntoView({block: 'center'})")
    target.click()


def _no_js_login_and_goto(new_context, server, route):
    return _no_js_page(new_context, server.base_url(), route, viewport=VIEWPORT_PHONE)


def test_with_scripts_blocked_manage_is_a_link_to_an_in_page_sheet_that_replaces_and_disconnects(
        new_context, server):
    """no script: Manage navigates to ?calendar=manage and the open dialog is an in-page card;
    a refused replace comes back to it with the error, a good one replaces, and Disconnect goes
    through the server's own confirmation page"""
    _connect_old(server)
    with _no_js_login_and_goto(new_context, server, "/display") as page:
        _click_centred(page, OPENER)
        page.wait_for_url("**calendar=manage**")
        page.wait_for_load_state("load")
        assert page.locator(DIALOG).evaluate("e => e.open && !e.matches(':modal')")
        assert page.locator(URL_INPUT).is_visible()
        page.fill(URL_INPUT, NEW_URL)
        failing = cah.make_calendar_transport(raise_exc=ConnectionError("boom"))
        with cah.stubbed_calendar_transport(failing), cah.fake_public_hostname("new-calendar.example"):
            _dom_click(page, REPLACE)
            page.wait_for_url("**calendar_error=unreachable**")
        assert page.locator("#calendar-connect-url-error").is_visible()
        assert page.locator(DIALOG).evaluate("e => e.open")
        assert calendar_rules.configured_calendar_url(server.state_dir) == OLD_URL
        page.fill(URL_INPUT, NEW_URL)
        good = cah.make_calendar_transport(body=cah.ics_body([("AF9999", "ORY", "NCE", 3)]))
        with cah.stubbed_calendar_transport(good), cah.fake_public_hostname("new-calendar.example"):
            _dom_click(page, REPLACE)
            page.wait_for_url("**flash=calendar_connect_ok")
        assert calendar_rules.configured_calendar_url(server.state_dir) == NEW_URL
        page.goto(server.base_url() + "/display?calendar=manage")
        _dom_click(page, DISCONNECT)
        assert page.locator("h1").inner_text() == "Disconnect calendar?"
        assert calendar_rules.calendar_is_configured(server.state_dir)
        page.wait_for_load_state("load")
        _click_centred(page, 'form[action="/settings/calendar/disconnect"] button[type=submit]')
        page.wait_for_url("**flash=calendar_disconnected")
        assert not calendar_rules.calendar_is_configured(server.state_dir)


def test_a_signed_out_post_never_reaches_the_connection(new_context, server):
    """sanity: the route stays session-gated (the sheet is no new way in)"""
    context = new_context()
    try:
        page = context.new_page()
        response = page.request.post(
            server.base_url() + "/settings/calendar/connect", form={"calendar_url": NEW_URL},
            max_redirects=0)
        assert response.status == 303 and response.headers["location"] == "/login"
        assert not calendar_rules.calendar_is_configured(server.state_dir)
        assert TEST_PASSWORD
    finally:
        context.close()
