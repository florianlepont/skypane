#!/usr/bin/env python3
"""Browser checks for the phone's draggable bottom sheets and the swipeable floating toast.

Every check drives the real served page with a real pointer: the box the sheet or toast occupies,
what the document reports about focus and open state, and the transform the browser computed.
State is always waited for, never read straight after a pointer action.
"""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _login, seed_state_dir)
from server import device_config

pytestmark = pytest.mark.browser

QUIET_DIALOG = "dialog#dlg-quiet-hours"
QUIET_LINK = "a.home-switch__window"
INVITE = "#dlg-invite-user"
INVITE_LINK = "a.page-header__action"
GRABBER = QUIET_DIALOG + " .modal__grabber"
TOAST = ".toast-region--flash .toast"

_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => (a.effect && a.effect.getComputedTiming().iterations === Infinity)"
    " || a.playState !== 'running')")


def _seed_quiet(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00", wake_interval_s=600)


def _context(new_context, server, viewport, reduced=False, lang="en"):
    context = new_context(
        viewport=viewport, reduced_motion="reduce" if reduced else "no-preference")
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    return context, page


def _open_quiet(page, server):
    page.goto(server.base_url() + "/")
    page.locator(QUIET_LINK).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=10000)
    page.locator(QUIET_LINK).click()
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open && d.matches(':modal')"
        " && document.activeElement.matches(s + ' .modal__title'); }",
        arg=QUIET_DIALOG, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)


def _centre(page, selector):
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _drag(page, start, dy, dx=0, steps=8, release=True):
    x, y = start
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx, y + dy, steps=steps)
    if release:
        page.mouse.up()


def _transform(page, selector):
    return page.locator(selector).evaluate("e => getComputedStyle(e).transform")


# ---- bottom sheets ---------------------------------------------------------------------


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_dragging_the_grabber_past_the_threshold_closes_the_sheet_and_returns_focus(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, viewport)
    try:
        _open_quiet(page, server)
        grabber = page.locator(GRABBER)
        assert grabber.is_visible()
        assert grabber.get_attribute("aria-label") == "Drag down to close"
        start = _centre(page, GRABBER)
        _drag(page, start, 140, release=False)
        # The sheet follows the pointer in whole pixels while the button is down.
        page.wait_for_function(
            "s => { const m = new DOMMatrix(getComputedStyle(document.querySelector(s)).transform);"
            " return m.f > 60 && Number.isInteger(m.f); }", arg=QUIET_DIALOG, timeout=15000)
        page.mouse.up()
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.home-switch__window')",
            arg=QUIET_DIALOG, timeout=10000)
        assert "dlg-quiet-hours" not in page.url
    finally:
        context.close()


def test_a_fast_short_flick_also_closes_the_sheet(new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        _open_quiet(page, server)
        # Fewer steps over the same distance is a faster gesture; 60px is under the distance.
        _drag(page, _centre(page, GRABBER), 60, steps=1)
        page.wait_for_function(
            "s => !document.querySelector(s).open", arg=QUIET_DIALOG, timeout=10000)
    finally:
        context.close()


def test_a_short_drag_springs_back_and_the_sheet_stays_open(new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        _open_quiet(page, server)
        start = _centre(page, GRABBER)
        before = page.locator(QUIET_DIALOG).bounding_box()
        page.mouse.move(*start)
        page.mouse.down()
        page.mouse.move(start[0], start[1] + 30, steps=10)
        page.wait_for_timeout(300)
        page.mouse.up()
        page.wait_for_function(
            "s => { const d = document.querySelector(s); return d.open"
            " && getComputedStyle(d).transform === 'none'"
            " && !d.hasAttribute('data-sheet-state'); }", arg=QUIET_DIALOG, timeout=10000)
        after = page.locator(QUIET_DIALOG).bounding_box()
        assert abs(after["y"] - before["y"]) <= 0.5, (before, after)
        assert page.evaluate(
            "s => document.querySelector(s).contains(document.activeElement)", QUIET_DIALOG)
    finally:
        context.close()


def test_a_drag_in_the_body_does_not_move_the_sheet(new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        _open_quiet(page, server)
        body = page.locator(QUIET_DIALOG + " .modal__body")
        box = body.bounding_box()
        _drag(page, (box["x"] + 4, box["y"] + box["height"] - 4), 200, release=False)
        assert _transform(page, QUIET_DIALOG) == "none"
        page.mouse.up()
        assert page.locator(QUIET_DIALOG).evaluate("d => d.open")
        assert _transform(page, QUIET_DIALOG) == "none"
    finally:
        context.close()


def test_dragging_the_heading_closes_the_sheet_but_its_close_link_still_works(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        _open_quiet(page, server)
        title = page.locator(QUIET_DIALOG + " .modal__title").bounding_box()
        _drag(page, (title["x"] + 6, title["y"] + title["height"] / 2), 160)
        page.wait_for_function(
            "s => !document.querySelector(s).open", arg=QUIET_DIALOG, timeout=10000)
        _open_quiet(page, server)
        page.locator(QUIET_DIALOG + " .modal__close").click()
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.home-switch__window')",
            arg=QUIET_DIALOG, timeout=10000)
    finally:
        context.close()


def test_tab_still_loops_inside_the_sheet_and_never_lands_on_the_grabber(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    try:
        _open_quiet(page, server)
        inside = (
            "s => { const a = document.activeElement; const d = document.querySelector(s);"
            " return !!a && d.contains(a) && !a.matches('.modal__grabber'); }")
        for key in ["Tab"] * 10 + ["Shift+Tab"] * 10:
            page.keyboard.press(key)
            page.wait_for_function(inside, arg=QUIET_DIALOG, timeout=15000)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.home-switch__window')",
            arg=QUIET_DIALOG, timeout=10000)
    finally:
        context.close()


def test_with_reduced_motion_a_drag_release_still_closes_instantly(new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE, reduced=True)
    try:
        _open_quiet(page, server)
        _drag(page, _centre(page, GRABBER), 150)
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.home-switch__window')",
            arg=QUIET_DIALOG, timeout=10000)
        _open_quiet(page, server)
        _drag(page, _centre(page, GRABBER), 25)
        # No spring: the sheet is back at rest as soon as the pointer is released.
        page.wait_for_function(
            "s => { const d = document.querySelector(s); return d.open"
            " && getComputedStyle(d).transform === 'none'; }", arg=QUIET_DIALOG, timeout=15000)
        assert page.locator(QUIET_DIALOG).evaluate(
            "d => getComputedStyle(d).transitionDuration") in ("0s", "1e-05s")
    finally:
        context.close()


def test_a_wide_screen_dialog_has_no_grabber_and_ignores_a_heading_drag(
        new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_quiet(page, server)
        assert not page.locator(GRABBER).is_visible()
        title = page.locator(QUIET_DIALOG + " .modal__title").bounding_box()
        _drag(page, (title["x"] + 6, title["y"] + title["height"] / 2), 200)
        assert page.locator(QUIET_DIALOG).evaluate("d => d.open")
        assert _transform(page, QUIET_DIALOG) == "none"
    finally:
        context.close()


def test_the_grabber_label_is_french_in_french(new_context, make_app_server):
    server = make_app_server(seed=_seed_quiet, fake_providers=True)
    context, page = _context(new_context, server, VIEWPORT_PHONE, lang="fr")
    try:
        _open_quiet(page, server)
        assert page.locator(GRABBER).get_attribute("aria-label") == (
            "Faites glisser vers le bas pour fermer")
    finally:
        context.close()


def test_a_sheet_closed_by_drag_leaves_the_forms_unsent(new_context, app_server_in_process):
    """closing by drag takes the cancel path: nothing is posted and the typed text is dropped
    with the dialog like a Close tap"""
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _context(new_context, server, VIEWPORT_PHONE)
    posts = []
    page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
    try:
        page.goto(server.base_url() + "/users")
        page.locator(INVITE_LINK).wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=10000)
        page.locator(INVITE_LINK).click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=10000)
        page.fill("#invite-email", "nobody@example.test")
        title = page.locator(INVITE + " .modal__title").bounding_box()
        _drag(page, (title["x"] + 6, title["y"] + title["height"] / 2), 200)
        page.wait_for_function(
            "s => !document.querySelector(s).open"
            " && document.activeElement.matches('a.page-header__action')",
            arg=INVITE, timeout=10000)
        assert posts == []
    finally:
        context.close()


# ---- swipeable toast ------------------------------------------------------------------


def _invite_toast(new_context, server, reduced=False, lang="en", viewport=VIEWPORT_PHONE):
    context, page = _context(new_context, server, viewport, reduced=reduced, lang=lang)
    page.goto(server.base_url() + "/users")
    page.locator(INVITE_LINK).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=10000)
    page.locator(INVITE_LINK).click()
    page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
    page.fill("#invite-email", "swipe.person@example.test")
    page.locator(INVITE + " button[type=submit]").click()
    page.locator(TOAST).wait_for(state="visible")
    # The pointer rests where the submit button was, which may now be under the toast, and a
    # hovered toast pauses its countdown on its own.
    page.mouse.move(1, 300)
    page.wait_for_function("() => document.readyState === 'complete'")
    page.wait_for_function(
        "s => { const t = document.querySelector(s); return !!t && t.getAnimations()"
        ".every(a => a.playState !== 'running' || a.effect.target !== t); }",
        arg=TOAST, timeout=10000)
    return context, page


def test_the_toast_drops_in_with_a_spring_and_settles_in_place(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server)
    try:
        assert _transform(page, TOAST) == "none"
        assert page.locator(TOAST).evaluate(
            "t => getComputedStyle(t).touchAction") == "pan-y"
    finally:
        context.close()


def test_swiping_the_toast_sideways_past_the_threshold_dismisses_it(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server)
    try:
        box = page.locator(TOAST).bounding_box()
        start = (box["x"] + box["width"] / 2, box["y"] + 6)
        _drag(page, start, 0, dx=-150, release=False)
        page.wait_for_function(
            "s => { const m = new DOMMatrix(getComputedStyle(document.querySelector(s)).transform);"
            " return m.e < -60 && Number.isInteger(m.e); }", arg=TOAST, timeout=15000)
        page.mouse.up()
        page.wait_for_function(
            "s => document.querySelectorAll(s).length === 0", arg=TOAST, timeout=10000)
    finally:
        context.close()


def test_a_short_toast_swipe_springs_back_and_the_toast_stays(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server)
    try:
        box = page.locator(TOAST).bounding_box()
        start = (box["x"] + box["width"] / 2, box["y"] + 6)
        page.mouse.move(*start)
        page.mouse.down()
        page.mouse.move(start[0] + 40, start[1], steps=10)
        page.wait_for_timeout(300)
        page.mouse.up()
        page.wait_for_function(
            "s => { const t = document.querySelector(s); return !!t"
            " && getComputedStyle(t).transform === 'none'"
            " && !t.classList.contains('is-returning'); }", arg=TOAST, timeout=10000)
    finally:
        context.close()


def test_the_dwell_bar_pauses_during_the_gesture_and_resumes_after(
        new_context, app_server_in_process):
    """a synthetic touch (no hover to pause it) held on the toast pauses the countdown hairline;
    letting go short of the threshold resumes it"""
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server)
    try:
        page.evaluate(
            """async s => { const t = document.querySelector(s); const r = t.getBoundingClientRect();
              const base = {pointerId: 71, pointerType: 'touch', isPrimary: true, bubbles: true,
                clientY: r.top + 6};
              t.dispatchEvent(new PointerEvent('pointerdown', {...base, clientX: r.left + 50}));
              await new Promise(done => setTimeout(done, 400));
              t.dispatchEvent(new PointerEvent('pointermove', {...base, clientX: r.left + 80}));
              await new Promise(done => setTimeout(done, 400));
              window.__finish = () => t.dispatchEvent(
                new PointerEvent('pointerup', {...base, clientX: r.left + 80})); }""", TOAST)
        page.wait_for_function(
            "s => document.querySelector(s).classList.contains('is-paused')"
            " && getComputedStyle(document.querySelector(s + ' .toast__timer'))"
            ".animationPlayState === 'paused'", arg=TOAST, timeout=15000)
        page.evaluate("() => window.__finish()")
        page.wait_for_function(
            "s => { const t = document.querySelector(s); return !!t"
            " && !t.classList.contains('is-paused'); }", arg=TOAST, timeout=10000)
    finally:
        context.close()


def test_the_toast_close_button_still_dismisses_it(new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server)
    try:
        page.locator(TOAST + " [data-toast-dismiss]").click()
        page.wait_for_function(
            "s => document.querySelectorAll(s).length === 0", arg=TOAST, timeout=10000)
    finally:
        context.close()


def test_with_reduced_motion_a_swipe_still_dismisses_the_toast(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context, page = _invite_toast(new_context, server, reduced=True)
    try:
        box = page.locator(TOAST).bounding_box()
        _drag(page, (box["x"] + box["width"] / 2, box["y"] + 6), 0, dx=150)
        page.wait_for_function(
            "s => document.querySelectorAll(s).length === 0", arg=TOAST, timeout=15000)
    finally:
        context.close()
