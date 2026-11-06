"""Real-browser proof that every result and every dialog behaves the same way: a success message
after an action is the one floating toast above the tab bar and never pushes the page; the calendar
dialog is a bottom sheet on a phone and a centred dialog on a wide screen like the others; a refused
pairing code is shown once; Tab loops inside an open dialog and Escape returns focus to the trigger;
the Quiet hours dialog opens without a field focused and its 12-hour times are not clipped.

Focus, layout and DOM state is always waited for, never read straight after a key or a navigation.
"""
import pytest

import fleet_console_support as fx
from frame_menu_support import click_add
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _login, seed_state_dir)
from server import device_config

pytestmark = pytest.mark.browser

INVITE = "#dlg-invite-user"
ADD = "#dlg-add-frame"
CALENDAR = "#calendar-sheet"
CALENDAR_OPENER = ".calendar-status [data-calendar-open]"
TOAST = ".toast-region--flash .toast"
QUIET_DIALOG = "dialog#dlg-quiet-hours"
QUIET_LINK = "a.home-switch__window"
START = "#quiet-window-start"
END = "#quiet-window-end"

_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => (a.effect && a.effect.getComputedTiming().iterations === Infinity)"
    " || a.playState !== 'running')")


def _context(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    return context, page


def _seed_quiet(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00", wake_interval_s=600)


def _top(page, selector):
    return page.evaluate(
        "s => document.querySelector(s).getBoundingClientRect().top", selector)


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_invite_result_is_a_floating_toast_that_does_not_move_the_list(
        new_context, app_server_in_process, viewport):
    """after Invite user the confirmation floats above the tab bar (fixed, out of flow) and the
    Users list stays exactly where it was"""
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _context(new_context, server, viewport)
    try:
        page.goto(server.base_url() + "/users")
        page.locator("table.users-table").wait_for(state="attached")
        page.wait_for_function(_SETTLED, timeout=10000)
        before = _top(page, "table.users-table")
        page.locator("a.page-header__action").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        page.fill("#invite-email", "toast.person@example.test")
        page.locator(INVITE + " button[type=submit]").click()
        page.locator(TOAST).wait_for(state="visible")
        page.wait_for_function("() => document.readyState === 'complete'")
        assert page.locator(".toast-region--flash").evaluate(
            "r => getComputedStyle(r).position") == "fixed"
        # The toast slides in; it settles above the tab bar (and stays up for several seconds).
        page.wait_for_function(
            "() => { const t = document.querySelector('%s');"
            " const b = document.querySelector('.tab-bar');"
            " return !!t && t.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 0.5; }"
            % TOAST, timeout=5000)
        # The page-change transition may still move things for a moment; a toast in flow would
        # keep the list pushed down for as long as it is shown.
        page.wait_for_function(
            "b => Math.abs(document.querySelector('table.users-table')"
            ".getBoundingClientRect().top - b) <= 0.5", arg=before, timeout=3000)
        assert "toast.person@example.test" in page.locator(TOAST).inner_text()
    finally:
        context.close()


def test_the_invite_result_stays_in_flow_with_scripts_blocked(new_context, app_server_in_process):
    """without script the same confirmation is still rendered, in its own region"""
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = new_context(viewport=VIEWPORT_PHONE, java_script_enabled=False)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/users#dlg-invite-user")
        page.fill("#invite-email", "plain.person@example.test")
        with page.expect_navigation():
            page.locator(INVITE + " button[type=submit]").click()
        assert page.locator(TOAST).count() == 1
        assert "plain.person@example.test" in page.locator(TOAST).inner_text()
    finally:
        context.close()


def _open_calendar(new_context, server, viewport):
    context, page = _context(new_context, server, viewport)
    page.goto(server.base_url() + "/display/calendar")
    page.locator(CALENDAR_OPENER).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=10000)
    page.locator(CALENDAR_OPENER).click()
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open && d.matches(':modal'); }",
        arg=CALENDAR, timeout=10000)
    return context, page


def test_the_calendar_dialog_is_a_bottom_sheet_on_a_phone(new_context, app_server_in_process):
    context, page = _open_calendar(new_context, app_server_in_process, VIEWPORT_PHONE)
    try:
        box = page.locator(CALENDAR).bounding_box()
        assert abs(box["x"]) <= 0.5 and abs(box["width"] - VIEWPORT_PHONE["width"]) <= 0.5, box
        assert abs(box["y"] + box["height"] - VIEWPORT_PHONE["height"]) <= 1, box
        radius = page.locator(CALENDAR).evaluate(
            "d => getComputedStyle(d).borderTopLeftRadius")
        assert float(radius.replace("px", "")) > 0
    finally:
        context.close()


def test_the_calendar_dialog_is_centred_on_a_wide_screen(new_context, app_server_in_process):
    context, page = _open_calendar(new_context, app_server_in_process, VIEWPORT_DESKTOP)
    try:
        box = page.locator(CALENDAR).bounding_box()
        assert abs(box["x"] + box["width"] / 2 - VIEWPORT_DESKTOP["width"] / 2) <= 1, box
        assert box["y"] > 8 and box["y"] + box["height"] < VIEWPORT_DESKTOP["height"] - 8, box
    finally:
        context.close()


def test_a_refused_pairing_code_is_shown_once(new_context, app_server_in_process):
    """one error element, beside the field: no toast and no repeated sentence in the dialog"""
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
        page.locator("main").wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=10000)
        click_add(page)
        page.fill("#pair-code", "kkkk-2222")
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        page.locator(ADD + " button[type=submit]").click()
        page.locator(ADD + ".is-modal[open]").wait_for(state="visible")
        page.locator(ADD + " .field-error").wait_for(state="visible")
        assert page.locator(ADD + " .field-error").count() == 1
        assert page.locator(ADD + " .toast").count() == 0
        assert page.locator(ADD).inner_text().count("Code not recognised") == 1
        assert page.locator(ADD).inner_text().count("Check the code and try again.") == 1
    finally:
        context.close()


def test_tab_loops_inside_an_open_dialog_and_escape_returns_to_the_trigger(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _context(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.goto(server.base_url() + "/users")
        page.locator("a.page-header__action").wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=10000)
        page.locator("a.page-header__action").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        inside = (
            "s => { const a = document.activeElement; return !!a && a !== document.body"
            " && document.querySelector(s).contains(a); }")
        seen = set()
        for key in ["Tab"] * 12 + ["Shift+Tab"] * 12:
            page.keyboard.press(key)
            page.wait_for_function(inside, arg=INVITE, timeout=5000)
            seen.add(page.evaluate("() => document.activeElement.outerHTML.slice(0, 80)"))
        assert len(seen) >= 4
        page.keyboard.press("Escape")
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.page-header__action')",
            arg=INVITE, timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_quiet_hours_opens_on_its_title_and_the_times_are_not_clipped(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, viewport)
    try:
        page.goto(server.base_url() + "/")
        page.locator(QUIET_LINK).wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=10000)
        page.locator(QUIET_LINK).click()
        page.wait_for_function(
            "s => document.querySelector(s).open"
            " && document.activeElement.matches(s + ' .modal__title')",
            arg=QUIET_DIALOG, timeout=10000)
        page.wait_for_function(_SETTLED, timeout=10000)
        assert page.evaluate("() => document.activeElement.tagName") == "H2"
        assert page.locator(START).input_value() == "23:00"
        for selector in (START, END):
            fit = page.locator(selector).evaluate(
                "e => ({sw: e.scrollWidth, cw: e.clientWidth})")
            assert fit["sw"] <= fit["cw"], (selector, fit)
        # The dialog's own width holds the whole value: a field narrower than "11:00 PM" at the
        # field's own font would clip it.
        needed = page.evaluate(
            """sel => { const e = document.querySelector(sel);
              const c = document.createElement('span');
              const cs = getComputedStyle(e);
              c.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font:' + cs.font;
              c.textContent = '11:00 PM';
              document.body.appendChild(c);
              const w = c.getBoundingClientRect().width; c.remove(); return w; }""", START)
        assert page.locator(START).bounding_box()["width"] >= needed, needed
        assert page.locator(QUIET_DIALOG).evaluate("d => d.open")
    finally:
        context.close()
