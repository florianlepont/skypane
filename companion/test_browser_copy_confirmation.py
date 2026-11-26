"""Real-browser checks of the copy confirmation: when a copy button succeeds, a check springs in
on scale and opacity only (180ms) and the label rises 4px; under reduced motion the same check
and word appear at once with no animation running. The word (Copied / Copié) is also announced
by the button's live region, the check is ink with at least 4.5:1 against what is behind it, the
control keeps its 44px height, the page does not overflow at 360px, and the button returns to
its normal label after the confirmation window. Two surfaces copy: the invitation link dialog
of Users and the build line of Account."""
import pytest

import animation_settle
import fleet_console_support as fx
import skypane_contrast_check
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

CLIPBOARD = ["clipboard-read", "clipboard-write"]
COPIED = {"en": "Copied", "fr": "Copié"}
RESET_WAIT_MS = 4000

USERS = {
    "button": "#dlg-invitation-ready button[data-copy-value]",
    "check": ".copy-btn__check",
    "label": ".copy-btn__label",
    "status": "#dlg-invitation-ready [data-copy-feedback]",
    "copy_word": {"en": "Copy", "fr": "Copier"},
}
ACCOUNT = {
    "button": "button.account-build",
    "check": ".account-build__check",
    "label": ".account-build__hint",
    "status": "[data-build-status]",
    "copy_word": None,
}

_FACTS = """spec => {
  const button = document.querySelector(spec.button);
  const check = button.querySelector(spec.check);
  const label = button.querySelector(spec.label);
  const status = document.querySelector(spec.status);
  const box = button.getBoundingClientRect();
  const running = (el) => el.getAnimations().filter(
    a => a.playState === 'running' && a.effect.getTiming().duration > 1).map(a => ({
      duration: a.effect.getTiming().duration,
      properties: [...new Set(a.effect.getKeyframes().flatMap(k => Object.keys(k)))].filter(
        p => !['offset', 'easing', 'composite', 'computedOffset'].includes(p)).sort(),
    }));
  const fills = [];
  for (let el = button; el; el = el.parentElement) {
    const bg = getComputedStyle(el).backgroundColor;
    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') { fills.unshift(bg); }
  }
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const over = (ink, under) => {
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = under; ctx.fillRect(0, 0, 1, 1);
    ctx.fillStyle = ink; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
  const flat = fills.reduce((under, fill) => over(fill, under), '#ffffff');
  return {
    hasCheck: !!check,
    checkHidden: check ? getComputedStyle(check).display === 'none' : null,
    checkAria: check ? check.getAttribute('aria-hidden') : null,
    checkRunning: check ? running(check) : [],
    labelRunning: running(label),
    anyRunning: button.getAnimations({subtree: true}).filter(
      a => a.playState === 'running' && a.effect.getTiming().duration > 1).length,
    label: label.textContent.replace(/\\s+/g, ' ').trim(),
    status: status ? status.textContent : null,
    height: box.height, width: box.width,
    checkInk: check ? over(getComputedStyle(check).color, flat) : null, flat: flat,
  };
}"""


def _context(new_context, lang, scheme="light", **extra):
    return new_context(
        viewport=VIEWPORT_MIN_SUPPORTED, color_scheme=scheme, permissions=CLIPBOARD, **extra)


def _lang(context, base_url, lang):
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])


def _open_users(new_context, server, lang, theme, **extra):
    fx.seed_users(server.state_dir)
    context = _context(new_context, lang, **extra)
    _lang(context, server.base_url(), lang)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    page.locator("a.page-header__action").click()
    page.locator("#dlg-invite-user.is-modal[open]").wait_for(state="visible")
    page.fill("#invite-email", "new.person@example.test")
    page.locator("#dlg-invite-user button[type=submit]").click()
    page.locator(USERS["button"]).wait_for(state="visible")
    page.wait_for_function(
        "() => document.getAnimations().every(a => a.playState !== 'running'"
        " || a.effect.getComputedTiming().iterations === Infinity)")
    return context, page


def _open_account(new_context, server, lang, theme, **extra):
    context = _context(new_context, lang, **extra)
    _lang(context, server.base_url(), lang)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/account")
    page.locator(ACCOUNT["button"]).wait_for(state="attached")
    if theme:
        _set_ui_theme(page, theme)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    page.locator(ACCOUNT["button"]).scroll_into_view_if_needed()
    return context, page


def _click_and_read(page, spec):
    before = page.evaluate(_FACTS, spec)
    page.locator(spec["button"]).click()
    page.wait_for_function(
        "spec => !!document.querySelector(spec.button + ' ' + spec.check)", arg=spec, timeout=5000)
    return before, page.evaluate(_FACTS, spec)


@pytest.fixture(scope="module")
def account_server(module_app_server_factory):
    return module_app_server_factory(fake_providers=True)


def _assert_confirmation(page, spec, lang, before, now):
    assert before["hasCheck"] is False, before
    assert now["checkAria"] == "true", now
    assert now["checkHidden"] is False, now
    assert now["label"].endswith(COPIED[lang]), now
    assert now["status"] == COPIED[lang], now
    assert now["height"] >= 44, now
    assert abs(now["height"] - before["height"]) <= 1, (before, now)
    assert skypane_contrast_check.contrast_ratio(now["checkInk"], now["flat"]) >= 4.5, now
    _assert_no_page_overflow(page, "copy confirmation", VIEWPORT_MIN_SUPPORTED["width"])


def _assert_springs(now):
    assert now["checkRunning"], now
    for animation in now["checkRunning"]:
        assert animation["duration"] == 180, now
        assert animation["properties"] == ["opacity", "transform"], now
    assert now["labelRunning"], now
    for animation in now["labelRunning"]:
        assert animation["duration"] == 180, now
        assert animation["properties"] == ["opacity", "transform"], now


def _assert_back_to_normal(page, spec, lang, before):
    page.wait_for_function(
        "spec => !document.querySelector(spec.button + ' ' + spec.check)", arg=spec,
        timeout=RESET_WAIT_MS)
    after = page.evaluate(_FACTS, spec)
    assert after["label"] == before["label"], (before, after)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_copy_springs_a_check_in_on_the_invitation_link(
        new_context, app_server_in_process, invitation_auth0, lang, theme):
    context, page = _open_users(new_context, app_server_in_process, lang, theme)
    try:
        before, now = _click_and_read(page, USERS)
        _assert_confirmation(page, USERS, lang, before, now)
        assert now["label"] == COPIED[lang], now
        assert before["label"].endswith(USERS["copy_word"][lang]), before
        _assert_springs(now)
        _assert_back_to_normal(page, USERS, lang, before)
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_copy_springs_a_check_in_on_the_account_build_line(
        new_context, account_server, lang, theme):
    context, page = _open_account(new_context, account_server, lang, theme)
    try:
        before, now = _click_and_read(page, ACCOUNT)
        _assert_confirmation(page, ACCOUNT, lang, before, now)
        assert now["label"].endswith(COPIED[lang]), now
        assert page.locator(ACCOUNT["status"]).inner_text() == COPIED[lang]
        _assert_springs(now)
        _assert_back_to_normal(page, ACCOUNT, lang, before)
    finally:
        context.close()


def test_under_reduced_motion_the_invitation_check_appears_at_once(
        new_context, app_server_in_process, invitation_auth0):
    context, page = _open_users(
        new_context, app_server_in_process, "en", None, reduced_motion="reduce")
    try:
        before, now = _click_and_read(page, USERS)
        assert now["label"] == COPIED["en"], now
        assert now["checkHidden"] is False, now
        assert now["anyRunning"] == 0 and not now["checkRunning"] and not now["labelRunning"], now
        assert now["status"] == COPIED["en"], now
    finally:
        context.close()


def test_under_reduced_motion_the_account_check_appears_at_once(new_context, account_server):
    context, page = _open_account(new_context, account_server, "en", None, reduced_motion="reduce")
    try:
        before, now = _click_and_read(page, ACCOUNT)
        assert now["label"].endswith(COPIED["en"]), now
        assert now["checkHidden"] is False, now
        assert now["anyRunning"] == 0 and not now["checkRunning"] and not now["labelRunning"], now
    finally:
        context.close()
