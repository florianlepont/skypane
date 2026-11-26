"""Real-browser checks of the contrast of the "Copied" label on a console copy button (the invitation
link of Users): the word is at least 4.5:1 against what is behind it in Light and Dark, English and
French, at 360 px; in Light it is the dark green of the text token, while the status hue itself
(`--color-status-ok`) keeps its two values; the word is also announced by the button's live region,
the button keeps its 44 px height, nothing scrolls sideways and under reduced motion no animation
runs. The text token resolves in the four theme contexts: explicit Light, explicit Dark, Auto with
a dark scheme, Auto with a light scheme."""
import animation_settle
import fleet_console_support as fx
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

CLIPBOARD = ["clipboard-read", "clipboard-write"]
COPIED = {"en": "Copied", "fr": "Copié"}
BUTTON = "#dlg-invitation-ready button[data-copy-value]"
LABEL = BUTTON + ".copy-btn--copied .copy-btn__label"
STATUS = "#dlg-invitation-ready [data-copy-feedback]"
LIGHT_TEXT = "#15803d"
LIGHT_HUE = "#16a34a"
DARK_GREEN = "#4ade80"

# Colours go through a 1x1 canvas so any CSS colour syntax becomes plain RGBA; a background is the
# stack of translucent layers painted under the label's centre, up to the page canvas; the label sits
# outside its button, so the button's own fill is not what is behind it.
FACTS = """sel => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = (css) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, under) => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat([1]);
  const root = document.documentElement;
  const dark = root.dataset.uiTheme === 'dark'
    || (root.dataset.uiTheme !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches);
  const label = document.querySelector(sel);
  let bg = dark ? rgba(getComputedStyle(root).getPropertyValue('--color-canvas')) : [255, 255, 255, 1];
  const layers = [];
  const box = label.getBoundingClientRect();
  const stack = document.elementsFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  for (const n of stack) if (n !== label) layers.push(rgba(getComputedStyle(n).backgroundColor));
  for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);
  const ink = over(rgba(getComputedStyle(label).color), bg);
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 :
      Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const x = lum(ink), y = lum(bg);
  return {ratio: (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05),
    colour: getComputedStyle(label).color, text: label.textContent.trim()};
}"""
TOKENS = """() => { const s = getComputedStyle(document.documentElement);
  return {text: s.getPropertyValue('--color-status-ok-text').trim().toLowerCase(),
          hue: s.getPropertyValue('--color-status-ok').trim().toLowerCase()}; }"""


def _open(new_context, server, lang, theme=None, width=VIEWPORT_MIN_SUPPORTED, scheme="light"):
    fx.seed_users(server.state_dir)
    context = new_context(
        viewport=width, color_scheme=scheme, permissions=CLIPBOARD)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    return context, page


def _copy(page, theme):
    page.locator("a.page-header__action").click()
    page.locator("#dlg-invite-user.is-modal[open]").wait_for(state="visible")
    page.fill("#invite-email", "new.person@example.test")
    page.locator("#dlg-invite-user button[type=submit]").click()
    page.locator(BUTTON).wait_for(state="visible")
    if theme:
        _set_ui_theme(page, theme)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    page.locator(BUTTON).click()
    page.locator(LABEL).wait_for(state="visible")
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_copied_word_reaches_four_and_a_half_to_one_and_stays_announced(
        new_context, app_server_in_process, invitation_auth0, lang, theme):
    context, page = _open(new_context, app_server_in_process, lang, theme)
    try:
        _copy(page, theme)
        facts = page.evaluate(FACTS, LABEL)
        assert facts["text"] == COPIED[lang]
        assert facts["ratio"] >= 4.5, facts
        if theme == "light":
            assert facts["colour"] == "rgb(21, 128, 61)"
        assert page.locator(STATUS).inner_text().strip() == COPIED[lang]
        assert page.locator(BUTTON).bounding_box()["height"] >= 44 - 0.5
        assert not _assert_no_page_overflow(page, "copied label", VIEWPORT_MIN_SUPPORTED["width"])
    finally:
        context.close()


@pytest.mark.parametrize("scheme,attribute,text,hue", (
    ("light", None, LIGHT_TEXT, LIGHT_HUE), ("dark", None, DARK_GREEN, DARK_GREEN),
    ("dark", "light", LIGHT_TEXT, LIGHT_HUE), ("light", "dark", DARK_GREEN, DARK_GREEN)),
    ids=("auto-light", "auto-dark", "explicit-light", "explicit-dark"))
def test_the_text_token_differs_per_theme_and_the_status_hue_does_not_move(
        new_context, app_server_in_process, scheme, attribute, text, hue):
    context, page = _open(new_context, app_server_in_process, "en", scheme=scheme)
    try:
        if attribute:
            page.evaluate("a => document.documentElement.setAttribute('data-ui-theme', a)", attribute)
        assert page.evaluate(TOKENS) == {"text": text, "hue": hue}
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_under_reduced_motion_the_word_appears_at_once_and_no_animation_runs(
        new_context, app_server_in_process, invitation_auth0, lang):
    context, page = _open(new_context, app_server_in_process, lang)
    try:
        page.emulate_media(reduced_motion="reduce")
        _copy(page, None)
        assert page.locator(LABEL).inner_text().strip() == COPIED[lang]
        assert page.evaluate(
            "() => document.getAnimations().filter(a => a.playState === 'running'"
            " && a.effect.getComputedTiming().iterations !== Infinity).length") == 0
    finally:
        context.close()
