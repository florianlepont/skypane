#!/usr/bin/env python3
"""Real-browser checks of the calendar connection page: it is a page (no modal) reached from the
status row's one button at 390 and 1280 px in both languages and both themes with usable controls
(>= 44 px targets, 16 px field) and no overflow; the floating Cancel and Connect bar sits above the
tab bar on a phone; a plain visit leaves focus alone; a replace round-trips through the real route
and a refused one returns to the page with the error and leaves the working connection untouched;
the Connect button shows its pending label while the server reads the link; Disconnect confirms in
a dialog; and with scripts blocked the same flows work through plain links and forms.
"""
from datetime import datetime

import pytest

import companion.test_companion_app_helpers as cah
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _assert_no_page_overflow,
    _in_both_themes, _login, _no_js_page,
)
from server.plane import calendar_rules

pytestmark = pytest.mark.browser

CONNECT_ROUTE = "/display/calendar/connect"
OPENER = ".calendar-status a.calendar-manage"
URL_INPUT = "#calendar-connect-url"
SAVE = ".dirty-bar button[type=submit]"
CANCEL = ".dirty-bar a.dirty-bar__cancel"
DISCONNECT_LINK = "a.form-page__danger[data-modal-open]"
DISCONNECT_DIALOG = "dialog#disconnect-calendar"
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


def _open_page(new_context, server, viewport, path, lang="en", scheme=None, wait_for=URL_INPUT):
    extra = {"color_scheme": scheme} if scheme else {}
    context = new_context(viewport=viewport, **extra)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator(wait_for).wait_for(state="visible")
    return context, page


def _state(page):
    return page.locator(".calendar-status").get_attribute("data-calendar-state")


def _active_id(page):
    return page.evaluate("() => document.activeElement && document.activeElement.id")


def test_the_button_opens_the_page_and_cancel_returns_to_the_list(new_context, server):
    """Choose calendar is a link to a page (no dialog opens), Cancel and the back link return to
    the list untouched"""
    _connect_old(server)
    context, page = _open_page(
        new_context, server, VIEWPORT_DESKTOP, "/display/calendar", wait_for=OPENER)
    try:
        page.locator(OPENER).click()
        page.wait_for_url("**" + CONNECT_ROUTE)
        page.locator(URL_INPUT).wait_for(state="visible")
        assert page.locator("dialog[open]").count() == 0
        # The Save bar waits for an edit; Cancel is in it once something is typed.
        assert page.locator(".dirty-bar").is_hidden()
        page.locator(URL_INPUT).fill("https://typed.example/")
        page.locator(CANCEL).wait_for(state="visible")
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator(CANCEL).click()
        page.wait_for_url("**/display/calendar")
        assert _state(page) == "ok"
        assert calendar_rules.configured_calendar_url(server.state_dir) == OLD_URL
        page.locator(OPENER).click()
        page.wait_for_url("**" + CONNECT_ROUTE)
        page.locator("a.form-back").click()
        page.wait_for_url("**/display/calendar")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_page_is_usable_in_both_themes(new_context, server, viewport, lang):
    """the page shows only the masked host, with a 16 px field, 44 px controls, the floating bar
    in the viewport (above the tab bar on a phone) and nothing overflowing - light and dark; the
    full link is nowhere in the page"""
    _connect_old(server)
    context, page = _open_page(new_context, server, viewport, CONNECT_ROUTE, lang)
    try:
        assert _active_id(page) != "calendar-connect-url", "a plain visit must not focus the field"
        assert page.locator(".calendar-masked-url").inner_text() == "old-calendar.example…"
        content = page.content()
        for needle in ("OLDSECRET", "OLDTOKEN", OLD_URL):
            assert needle not in content
        for theme in _in_both_themes(page):
            font_px = page.locator(URL_INPUT).evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
            assert font_px >= 16, (theme, font_px)
            where = "calendar page (%s, %s, %d)" % (lang, theme["theme"], viewport["width"])
            page.locator(URL_INPUT).fill("https://typed.example/")
            page.locator(SAVE).wait_for(state="visible")
            for selector in (URL_INPUT, SAVE, CANCEL, DISCONNECT_LINK, "a.form-back"):
                _assert_hit_target(page, selector, where)
            bar = page.locator(".dirty-bar").bounding_box()
            assert bar["x"] >= 0 and bar["x"] + bar["width"] <= viewport["width"], bar
            assert bar["y"] >= 0 and bar["y"] + bar["height"] <= viewport["height"], bar
            if viewport["width"] < 960:
                tab = page.locator(".tab-bar").bounding_box()
                assert bar["y"] + bar["height"] <= tab["y"] + 0.5, (bar, tab)
            assert _assert_no_page_overflow(page, where) == ""
            sizes = page.evaluate(
                "args => args.map(s => getComputedStyle(document.querySelector(s)).fontSize)",
                [SAVE, CANCEL])
            assert sizes[0] == sizes[1], (where, "Save and Cancel differ in type size", sizes)
        french = "Nouveau lien" in page.locator(".form-page__card").inner_text()
        assert french == (lang == "fr")
    finally:
        context.close()


def test_replace_round_trips_and_the_page_shows_the_new_flights(new_context, server):
    """pasting a working link replaces the connection: the list shows a confirmation toast and the
    status row counts the new link's flights"""
    _connect_old(server)
    context, page = _open_page(new_context, server, VIEWPORT_PHONE, CONNECT_ROUTE)
    try:
        page.fill(URL_INPUT, NEW_URL)
        body = cah.ics_body([("AF9999", "ORY", "NCE", 3)])
        with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
                cah.fake_public_hostname("new-calendar.example"):
            page.click(SAVE)
            page.wait_for_url("**flash=calendar_connect_ok")
        assert page.locator(".toast").first.is_visible()
        assert _state(page) == "ok"
        assert "1 flight in the next 48 h" in page.locator(".calendar-status__detail").inner_text()
        assert page.locator(".calendar-status__title b").inner_text() == "new-calendar.example"
        assert calendar_rules.configured_calendar_url(server.state_dir) == NEW_URL
    finally:
        context.close()


def test_a_refused_replace_returns_to_the_page_with_the_error_and_keeps_the_old_link(
        new_context, server):
    """an unreachable link: the page comes back on the explicit error, the field is empty, the
    list still shows the old healthy connection and its two flights, and the old link is still the
    stored one"""
    _connect_old(server)
    before = calendar_rules.load_calendar_registry(server.state_dir)
    context, page = _open_page(new_context, server, VIEWPORT_PHONE, CONNECT_ROUTE)
    try:
        page.fill(URL_INPUT, NEW_URL)
        transport = cah.make_calendar_transport(raise_exc=ConnectionError("boom"))
        with cah.stubbed_calendar_transport(transport), cah.fake_public_hostname("new-calendar.example"):
            page.click(SAVE)
            page.wait_for_url("**flash=calendar_connect_failed**")
        page.locator("#calendar-connect-url-error").wait_for(state="visible")
        assert "doesn’t answer" in page.locator("#calendar-connect-url-error").inner_text() \
            or "doesn't answer" in page.locator("#calendar-connect-url-error").inner_text()
        assert page.locator(URL_INPUT).input_value() == ""
        assert calendar_rules.configured_calendar_url(server.state_dir) == OLD_URL
        assert calendar_rules.load_calendar_registry(server.state_dir) == before
        page.locator(CANCEL).click()
        page.wait_for_url("**/display/calendar")
        assert _state(page) == "ok"
        assert "2 flights in the next 48 h" in page.locator(".calendar-status__detail").inner_text()
    finally:
        context.close()


def test_the_connect_button_shows_a_pending_label_on_submit(new_context, server):
    """a real click on Connect swaps the button's label for the server-rendered 'Checking…' and
    marks the form busy. The navigation itself is held back by a later listener: Playwright cannot
    evaluate in a frame whose navigation response is still pending, so the pending window is
    observed at the submit event, which is where the label is written"""
    context, page = _open_page(new_context, server, VIEWPORT_PHONE, CONNECT_ROUTE)
    try:
        page.fill(URL_INPUT, NEW_URL)
        assert page.locator(SAVE).inner_text() == "Save"
        page.evaluate(
            "() => document.querySelector('[data-calendar-connect]')"
            ".addEventListener('submit', e => e.preventDefault())")
        page.click(SAVE)
        assert page.locator(SAVE).inner_text() == "Checking…"
        assert page.locator("[data-calendar-connect]").get_attribute("aria-busy") == "true"
    finally:
        context.close()


def test_disconnect_confirms_in_a_dialog_and_dismiss_backs_out(new_context, server):
    """Disconnect opens a confirmation dialog saying what happens to the flights (no native
    confirm), focus on the safe dismiss; dismissing keeps the connection; confirming disconnects
    and clears the flights"""
    _connect_old(server)
    context, page = _open_page(new_context, server, VIEWPORT_PHONE, CONNECT_ROUTE)
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    try:
        page.locator(DISCONNECT_LINK).click()
        page.locator(DISCONNECT_DIALOG + "[open]").wait_for()
        assert "flights it supplied are deleted" in page.locator(DISCONNECT_DIALOG).inner_text()
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.classList.contains('modal__dismiss')")
        page.click(DISCONNECT_DIALOG + " a.modal__dismiss")
        page.locator(DISCONNECT_DIALOG + "[open]").wait_for(state="detached")
        assert calendar_rules.calendar_is_configured(server.state_dir)
        page.locator(DISCONNECT_LINK).click()
        page.locator(DISCONNECT_DIALOG + "[open]").wait_for()
        page.click(DISCONNECT_DIALOG + " button[type=submit]")
        page.wait_for_url("**flash=calendar_disconnected")
        assert _state(page) == "none"
        assert not calendar_rules.calendar_is_configured(server.state_dir)
        assert calendar_rules.load_calendar_registry(server.state_dir)["entries"] == []
        assert dialogs == [], "no native confirm() dialog is used"
    finally:
        context.close()


# --- scripts blocked -------------------------------------------------------


def _dom_click(page, selector):
    """The DOM's own click(): a control low on the page can sit under the fixed tab bar on a
    phone, where a coordinate click can land on the bar."""
    page.eval_on_selector(selector, "el => el.click()")


def _no_js_login_and_goto(new_context, server, route):
    # Form flows, not motion: without the cross-document view transition, a click made right after
    # a navigation cannot land on the transition overlay (`<html>`) on a slow machine.
    return _no_js_page(new_context, server.base_url(), route, viewport=VIEWPORT_PHONE,
                       reduced_motion="reduce")


def test_with_scripts_blocked_the_page_replaces_and_disconnects(new_context, server):
    """no script: the page is plain links and forms; a refused replace comes back to it with the
    error, a good one replaces, and Disconnect goes through its dialog's form"""
    _connect_old(server)
    with _no_js_login_and_goto(new_context, server, CONNECT_ROUTE) as page:
        assert page.locator(URL_INPUT).is_visible()
        page.fill(URL_INPUT, NEW_URL)
        failing = cah.make_calendar_transport(raise_exc=ConnectionError("boom"))
        with cah.stubbed_calendar_transport(failing), cah.fake_public_hostname("new-calendar.example"):
            _dom_click(page, SAVE)
            page.wait_for_url("**calendar_error=unreachable**")
        assert page.locator("#calendar-connect-url-error").is_visible()
        assert calendar_rules.configured_calendar_url(server.state_dir) == OLD_URL
        page.fill(URL_INPUT, NEW_URL)
        good = cah.make_calendar_transport(body=cah.ics_body([("AF9999", "ORY", "NCE", 3)]))
        with cah.stubbed_calendar_transport(good), cah.fake_public_hostname("new-calendar.example"):
            _dom_click(page, SAVE)
            page.wait_for_url("**flash=calendar_connect_ok")
        assert calendar_rules.configured_calendar_url(server.state_dir) == NEW_URL
        page.goto(server.base_url() + CONNECT_ROUTE + "#disconnect-calendar")
        page.wait_for_load_state("load")
        _dom_click(page, DISCONNECT_DIALOG + " button[type=submit]")
        page.wait_for_url("**flash=calendar_disconnected")
        assert not calendar_rules.calendar_is_configured(server.state_dir)


def test_a_signed_out_post_never_reaches_the_connection(new_context, server):
    """sanity: the route stays session-gated (the page is no new way in)"""
    context = new_context()
    try:
        page = context.new_page()
        response = page.request.post(
            server.base_url() + "/settings/calendar/connect", form={"calendar_url": NEW_URL},
            max_redirects=0)
        assert response.status == 303
        assert response.headers["location"] == "/login?expired=1"
        assert not calendar_rules.calendar_is_configured(server.state_dir)
    finally:
        context.close()
