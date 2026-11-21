"""Real-browser checks of the Users dialogs: the invite sheet that stays above the phone's
on-screen keyboard, the even spacing of the short dialogs, the invitation link shown once (copy,
selection fallback, gone after Done), the failure dialog with its retry, the scripts-blocked
card, and the shared dialogs keeping their own spacing. 320, 360/390 and 1280/1440 px, English
and French, light and dark."""
import re

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme, seed_state_dir)
from server import device_config
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio

pytestmark = pytest.mark.browser

INVITE = "#dlg-invite-user"
READY = "#dlg-invitation-ready"
FAILED = "#dlg-invitation-failed"
VIEWPORT_NARROW = {"width": 320, "height": 700}
VIEWPORT_WIDE = {"width": 1440, "height": 900}

# A stand-in for the on-screen keyboard: the layout viewport keeps its height while the visual
# viewport (what the keyboard leaves visible) shrinks, as it does on a phone.
_FAKE_VISUAL_VIEWPORT = """(() => {
  const listeners = {};
  const vv = {height: window.innerHeight, width: window.innerWidth, offsetTop: 0, offsetLeft: 0,
    scale: 1,
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener() {},
    dispatch(type) { (listeners[type] || []).forEach(fn => fn()); }};
  Object.defineProperty(window, 'visualViewport', {value: vv, configurable: true});
})()"""

_BOXES = """sel => { const r = document.querySelector(sel).getBoundingClientRect();
  return {t: r.top, b: r.bottom, l: r.left, r: r.right}; }"""
_FIT = "d => ({sw: d.scrollWidth, cw: d.clientWidth})"
_COLOURS = """sel => { const s = getComputedStyle(document.querySelector(sel));
  return {fg: s.color, bg: s.backgroundColor}; }"""


def _context(new_context, server, viewport, lang="en", scheme="light", **extra):
    context = new_context(viewport=viewport, color_scheme=scheme, **extra)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    return context


def _open_users(context, server, scheme="light"):
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    page.wait_for_function("() => document.readyState === 'complete'")
    return page


def _invite(page, email="new.person@example.test", admin=False):
    page.locator("a.page-header__action").click()
    page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
    page.fill("#invite-email", email)
    if admin:
        page.check("#invite-role")
    page.locator(INVITE + " button[type=submit]").click()


def _settled(page, selector):
    page.locator(selector).wait_for(state="visible")
    page.wait_for_function(
        "() => document.getAnimations().every(a => a.playState !== 'running'"
        " || a.effect.getComputedTiming().iterations === Infinity)")


def _gap(page, upper, lower):
    return round(page.evaluate(_BOXES, lower)["t"] - page.evaluate(_BOXES, upper)["b"], 1)


def _hex(css_colour):
    channels = [int(round(float(c))) for c in re.findall(r"[\d.]+", css_colour)[:3]]
    return "#%02x%02x%02x" % tuple(channels)


# ---- the phone's keyboard ----------------------------------------------------------------


def test_the_invite_field_stays_above_the_on_screen_keyboard(
        new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, VIEWPORT_PHONE)
    context.add_init_script(_FAKE_VISUAL_VIEWPORT)
    try:
        page = _open_users(context, server)
        page.locator("a.page-header__action").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        _settled(page, INVITE)
        height = page.evaluate("() => innerHeight")
        assert page.evaluate(_BOXES, INVITE)["b"] == pytest.approx(height, abs=1)
        keyboard = round(height * 0.6)
        page.evaluate("h => { visualViewport.height = h; visualViewport.dispatch('resize'); }",
                      keyboard)
        page.focus("#invite-email")
        page.wait_for_function(
            "k => document.querySelector('%s').getBoundingClientRect().bottom <= k + 1" % INVITE,
            arg=keyboard)
        field = page.evaluate(_BOXES, "#invite-email")
        sheet = page.evaluate(_BOXES, INVITE)
        assert field["t"] >= 0 and field["b"] <= keyboard, (field, keyboard)
        assert sheet["t"] >= 0 and sheet["b"] <= keyboard + 1, (sheet, keyboard)
        # The Invite button is above the keyboard too, so the form can be sent.
        assert page.evaluate(_BOXES, INVITE + " button[type=submit]")["b"] <= keyboard
        page.evaluate("h => { visualViewport.height = h; visualViewport.dispatch('resize'); }",
                      height)
        page.wait_for_function(
            "h => Math.abs(document.querySelector('%s').getBoundingClientRect().bottom - h) <= 1"
            % INVITE, arg=height)
    finally:
        context.close()


def test_a_short_viewport_keeps_the_whole_sheet_reachable(new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, {"width": 390, "height": 468})
    try:
        page = _open_users(context, server)
        page.locator("a.page-header__action").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        _settled(page, INVITE)
        sheet = page.evaluate(_BOXES, INVITE)
        assert sheet["t"] >= 0 and sheet["b"] <= 468 + 1
        _assert_hit_target(page, INVITE + " #invite-email", "short viewport")
        _assert_hit_target(page, INVITE + " button[type=submit]", "short viewport")
    finally:
        context.close()


# ---- spacing -----------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_invite_dialog_is_short_and_evenly_spaced(
        new_context, app_server_in_process, viewport, lang):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, viewport, lang)
    try:
        page = _open_users(context, server)
        page.locator("a.page-header__action").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        _settled(page, INVITE)
        assert page.locator(INVITE + " .modal__body p").count() == 0
        text = page.locator(INVITE).inner_text()
        assert "Auth0" not in text and "SkyPane does not" not in text
        assert not page.is_checked("#invite-role")
        assert page.locator(INVITE + " a.modal__close, " + INVITE + " select").count() == 0
        head, label = INVITE + " .modal__head", "%s label[for=invite-email]" % INVITE
        check, actions = INVITE + " .modal__check", INVITE + " .modal__actions"
        assert _gap(page, head, label) == 14
        assert _gap(page, "#invite-email", check) == 14
        assert _gap(page, check, actions) == 14
        assert page.locator(INVITE).evaluate("d => d.scrollWidth <= d.clientWidth")
        for control in ("#invite-email", "#invite-role", "button[type=submit]", "a.modal__dismiss"):
            _assert_hit_target(page, "%s %s" % (INVITE, control), "invite")
        buttons = [page.evaluate(_BOXES, INVITE + " " + s)
                   for s in ("a.modal__dismiss", "button[type=submit]")]
        assert buttons[0]["r"] < buttons[1]["l"], "Cancel first, Invite second, one row"
        assert abs(buttons[0]["t"] - buttons[1]["t"]) <= 1
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_role_confirmation_has_even_margins_and_no_subtitle(
        new_context, app_server_in_process, viewport, lang):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    context = _context(new_context, server, viewport, lang)
    try:
        page = _open_users(context, server)
        page.goto("%s/users?role_change=%d&role=admin" % (server.base_url(), seed.user_id))
        dialog = "#dlg-role-user-%d" % seed.user_id
        _settled(page, dialog)
        assert page.locator(dialog + " .modal__subtitle, " + dialog + " .modal__close").count() == 0
        assert _gap(page, dialog + " .modal__head", dialog + " .modal__note") == 14
        assert _gap(page, dialog + " .modal__note", dialog + " .modal__actions") == 14
        assert fx.USER_EMAIL in page.locator(dialog + " .modal__note").inner_text()
        assert page.locator(dialog).evaluate("d => d.scrollWidth <= d.clientWidth")
    finally:
        context.close()


def test_other_dialogs_keep_their_own_spacing(new_context, app_server_in_process):
    server = app_server_in_process
    seed_state_dir(server.state_dir)
    device_config.save_device_config(
        server.state_dir, display_enabled=True, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00", wake_interval_s=600)
    context = _context(new_context, server, VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.locator("a.home-pill--quiet").click()
        _settled(page, "dialog#dlg-quiet-hours")
        seen = page.evaluate("""() => { const d = document.querySelector('dialog#dlg-quiet-hours');
          const body = d.querySelector('.modal__body');
          const actions = d.querySelector('.modal__actions');
          return {cls: d.className, pad: getComputedStyle(d).padding,
                  bodyTop: getComputedStyle(body).marginTop,
                  actionsTop: getComputedStyle(actions).marginTop,
                  actionsDir: getComputedStyle(actions).flexDirection}; }""")
        assert "modal--compact" not in seen["cls"]
        assert seen["pad"] == "24px 24px 0px"
        assert seen["bodyTop"] == "16px" and seen["actionsTop"] == "16px"
    finally:
        context.close()


# ---- the invitation link -----------------------------------------------------------------


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_NARROW, VIEWPORT_PHONE, VIEWPORT_WIDE], ids=["320", "390", "1440"])
def test_the_invitation_dialog_fits_and_every_control_is_44px(
        new_context, app_server_in_process, invitation_auth0, viewport, lang, scheme):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, viewport, lang, scheme)
    try:
        page = _open_users(context, server, scheme)
        _invite(page)
        _settled(page, READY)
        where = "invitation/%d/%s/%s" % (viewport["width"], lang, scheme)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        assert page.locator(READY).evaluate("d => d.scrollWidth <= d.clientWidth"), where
        assert page.locator(READY + " code").evaluate(
            "c => getComputedStyle(c).userSelect") == "all"
        assert page.locator(READY + " code").inner_text().startswith("http://127.0.0.1")
        assert page.locator(READY + " .copy-btn__label").is_visible()
        for control in ("button[data-copy-value]", "a.modal__done"):
            _assert_hit_target(page, "%s %s" % (READY, control), where)
        assert page.locator(READY + " a[href^=http], " + READY + " a[rel]").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_copy_writes_the_message_with_the_link_and_the_address_to_open(
        new_context, app_server_in_process, invitation_auth0, lang):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(
        new_context, server, VIEWPORT_PHONE, lang, permissions=["clipboard-read", "clipboard-write"])
    try:
        page = _open_users(context, server)
        _invite(page)
        _settled(page, READY)
        link = page.locator(READY + " code").inner_text()
        page.locator(READY + " button[data-copy-value]").click()
        page.wait_for_function("t => navigator.clipboard.readText().then(c => c.includes(t))",
                               arg=link)
        message = page.evaluate("() => navigator.clipboard.readText()")
        assert link in message and "new.person@example.test" in message
        assert server.base_url() in message
        assert ("expires in 5 days" if lang == "en" else "expire dans 5 jours") in message
        label = "Copied" if lang == "en" else "Copié"
        page.wait_for_function(
            "([sel, t]) => document.querySelector(sel).textContent === t",
            arg=[READY + " .copy-btn__label", label])
    finally:
        context.close()


def test_copy_falls_back_to_a_selection_inside_the_open_dialog(
        new_context, app_server_in_process, invitation_auth0):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, VIEWPORT_PHONE)
    try:
        page = _open_users(context, server)
        page.add_init_script(
            """Object.defineProperty(navigator, 'clipboard', {value: {
                 writeText: () => Promise.reject(new Error('refused'))}});
               window.__copied = null;
               const original = document.execCommand.bind(document);
               document.execCommand = function (name) {
                 if (name === 'copy') {
                   window.__copied = document.getSelection().toString();
                   window.__host = document.activeElement && document.activeElement.parentNode
                     && document.activeElement.parentNode.nodeName; return true; }
                 return original.apply(document, arguments); };""")
        page.reload()
        page.wait_for_function("() => document.readyState === 'complete'")
        _invite(page)
        _settled(page, READY)
        page.locator(READY + " button[data-copy-value]").click()
        page.wait_for_function(
            "() => typeof window.__copied === 'string' && window.__copied.indexOf('/lo/reset') > 0")
        assert page.evaluate("() => window.__host") == "DIALOG"
    finally:
        context.close()


def test_done_removes_the_link_from_the_page_and_a_reload_does_not_post_again(
        new_context, app_server_in_process, invitation_auth0):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    context = _context(new_context, server, VIEWPORT_PHONE)
    try:
        page = _open_users(context, server)
        posts = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        _invite(page)
        _settled(page, READY)
        token = page.locator(READY + " code").inner_text().split("ticket=")[1]
        assert page.evaluate("() => location.pathname") == "/users/invite"
        page.locator(READY + " a.modal__done").click()
        page.wait_for_function("s => !document.querySelector(s)", arg=READY)
        assert page.evaluate("() => location.pathname") == "/users"
        assert token not in page.content()
        assert page.locator("[data-copy-value]").count() == 0
        page.reload()
        page.wait_for_function("() => document.readyState === 'complete'")
        assert token not in page.content()
        assert [u for u in posts if u.endswith("/users/invite")] == [server.url("/users/invite")]
    finally:
        context.close()


def test_without_script_the_link_dialog_is_a_card_and_done_goes_home(
        new_context, app_server_in_process, invitation_auth0):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    with _no_js_page(new_context, server.base_url(), "/users",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click("a.page-header__action")
        page.fill("#invite-email", "nojs@example.test")
        page.locator(INVITE + " button[type=submit]").click()
        page.locator(READY).wait_for(state="visible")
        assert page.locator(READY + " code").inner_text().startswith("http://127.0.0.1")
        assert page.locator(READY + " button[data-copy-value]").count() == 1
        page.locator(READY + " a.modal__done").click()
        page.wait_for_url("**/users")
        assert page.locator(READY).count() == 0


# ---- failure and retry ---------------------------------------------------------------------


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_NARROW, VIEWPORT_WIDE], ids=["320", "1440"])
def test_the_failure_dialog_fits_and_try_again_makes_the_link(
        new_context, app_server_in_process, invitation_auth0, viewport, lang, scheme):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    invitation_auth0.set_knob("mgmt_ticket_status", 500)
    context = _context(new_context, server, viewport, lang, scheme)
    try:
        page = _open_users(context, server, scheme)
        _invite(page)
        _settled(page, FAILED)
        where = "failure/%d/%s/%s" % (viewport["width"], lang, scheme)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        assert page.locator(FAILED).evaluate("d => d.scrollWidth <= d.clientWidth"), where
        assert page.locator("tr.users-row", has_text="new.person@example.test").count() == 1
        for control in ("button[type=submit]", "a.modal__done"):
            _assert_hit_target(page, "%s %s" % (FAILED, control), where)
        invitation_auth0.clear_knobs()
        page.locator(FAILED + " button[type=submit]").click()
        page.locator(READY).wait_for(state="visible")
        assert page.locator(READY + " code").inner_text().startswith("http://127.0.0.1")
        # A retry is a renewal: the link lasts a day.
        assert ("24 hours" if lang == "en" else "24 heures") in page.locator(READY).inner_text()
    finally:
        context.close()


# ---- colours ---------------------------------------------------------------------------------


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_delete_and_confirm_buttons_are_readable(new_context, app_server_in_process, scheme):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    context = _context(new_context, server, VIEWPORT_PHONE, scheme=scheme)
    try:
        page = _open_users(context, server, scheme)
        page.locator("#user-%d summary" % seed.user_id).click()
        page.locator("#user-%d a.row-menu__item" % seed.user_id).click()
        dialog = "#dlg-delete-user-%d" % seed.user_id
        _settled(page, dialog)
        seen = page.evaluate(_COLOURS, dialog + " button[type=submit]")
        assert contrast_ratio(_hex(seen["fg"]), _hex(seen["bg"])) >= WCAG_AA_NORMAL_TEXT
        assert _gap(page, dialog + " .modal__note", dialog + " .modal__actions") == 14
    finally:
        context.close()
