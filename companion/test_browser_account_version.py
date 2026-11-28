# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the build line at the end of Account: one quiet caption (`SkyPane
build <id>`, 13px, secondary ink, no uppercase, no mid-dot) with a hint line, a tap area of at
least 44px, a tap that copies the version text, a copied label that stays inside the card in
English and French at 360px, and an instant swap under reduced motion."""
import re

import pytest

import animation_settle
import skypane_contrast_check
from companion import auth, build_info
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

LINE = "button.account-build"
ID_LINE = LINE + " .account-build__id"
HINT_LINE = LINE + " .account-build__hint"
TEXT = {
    "en": {"hint": "Tap to copy for support", "copied": "Copied"},
    "fr": {"hint": "Touchez pour copier (support)", "copied": "Copié"},
}
CLIPBOARD = ["clipboard-read", "clipboard-write"]

_FACTS = """sel => {
  const line = document.querySelector(sel);
  const id = line.querySelector('.account-build__id');
  const hint = line.querySelector('.account-build__hint');
  const s = getComputedStyle(id);
  const hs = getComputedStyle(hint);
  const box = line.getBoundingClientRect();
  let el = line, fill = null;
  while (el && !fill) {
    const bg = getComputedStyle(el).backgroundColor;
    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') { fill = bg; }
    el = el.parentElement;
  }
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const over = (ink, under) => {
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = under; ctx.fillRect(0, 0, 1, 1);
    ctx.fillStyle = ink; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
  const flat = over(fill, '#ffffff');
  const main = document.querySelector('main').getBoundingClientRect();
  return {
    fontSize: s.fontSize, transform: s.textTransform, ink: over(s.color, flat),
    hintInk: over(hs.color, flat), flat: flat,
    hintSize: hs.fontSize, fill: fill, height: box.height, text: id.textContent,
    hint: hint.textContent, lineScroll: line.scrollWidth, lineClient: line.clientWidth,
    mainRight: main.right, lineRight: box.right,
    animations: line.getAnimations({subtree: true}).filter(
      a => a.playState === 'running' && a.effect.getTiming().duration > 1).length,
  };
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(fake_providers=True)


def _open(new_context, server, lang="en", theme="light", **context_args):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/account")
    page.locator(LINE).wait_for(state="attached")
    if theme is not None:
        _set_ui_theme(page, theme)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    page.locator(LINE).scroll_into_view_if_needed()
    return context, page


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_build_line_is_a_quiet_44px_caption(new_context, server, lang, theme):
    context, page = _open(new_context, server, lang, theme)
    try:
        facts = page.evaluate(_FACTS, LINE)
        assert re.fullmatch(r"SkyPane build ([0-9a-f]{7}|dev)", facts["text"]), facts
        assert "·" not in facts["text"] + facts["hint"], facts
        assert facts["hint"] == TEXT[lang]["hint"], facts
        assert facts["fontSize"] == "13px" and facts["hintSize"] == "13px", facts
        assert facts["transform"] == "none", facts
        assert facts["height"] >= 44, facts
        assert facts["fill"], facts
        for ink in (facts["ink"], facts["hintInk"]):
            assert skypane_contrast_check.contrast_ratio(ink, facts["flat"]) >= 4.5, facts
        _assert_no_page_overflow(page, "account build line")
    finally:
        context.close()


def test_the_build_id_is_the_servers_own_and_carries_nothing_personal(new_context, server):
    context, page = _open(new_context, server)
    try:
        expected = "SkyPane build " + build_info.build_id()
        assert page.locator(ID_LINE).inner_text() == expected
        assert page.locator(LINE).get_attribute("data-build-copy") == expected
        line = page.locator(LINE).inner_text().lower()
        assert "@" not in line and "token" not in line
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_tap_copies_the_version_text_and_the_label_swaps_back(new_context, server, lang):
    context, page = _open(new_context, server, lang, permissions=CLIPBOARD)
    try:
        shown = page.locator(ID_LINE).inner_text()
        page.locator(LINE).click()
        page.wait_for_function(
            "(t) => document.querySelector('%s').textContent === t" % HINT_LINE,
            arg=TEXT[lang]["copied"], timeout=5000)
        assert page.evaluate("navigator.clipboard.readText()") == shown
        facts = page.evaluate(_FACTS, LINE)
        assert facts["lineScroll"] <= facts["lineClient"], facts
        assert facts["lineRight"] <= facts["mainRight"] + 0.5, facts
        _assert_no_page_overflow(page, "account build line")
        page.wait_for_function(
            "(t) => document.querySelector('%s').textContent === t" % HINT_LINE,
            arg=TEXT[lang]["hint"], timeout=5000)
    finally:
        context.close()


def test_under_reduced_motion_the_swap_is_instant(new_context, server):
    context, page = _open(
        new_context, server, theme=None, reduced_motion="reduce", permissions=CLIPBOARD)
    try:
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        page.locator(LINE).click()
        page.wait_for_function(
            "(t) => document.querySelector('%s').textContent === t" % HINT_LINE,
            arg=TEXT["en"]["copied"])
        assert page.evaluate(_FACTS, LINE)["animations"] == 0
    finally:
        context.close()
