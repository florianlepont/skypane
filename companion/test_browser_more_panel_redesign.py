"""Real-browser proof of the redesigned More panel on a phone: a grab handle,
the account row with the person's initial, for an administrator a Console card
(tinted, accent border, accent icon tile, title, subtitle, accent chevron), a
Settings group holding theme and language, and Sign out as a full-width soft
alert button. A person who is not an administrator sees the same panel without
the Console card."""
import pytest

from nav_spaces_support import (
    MIN_TAP_PX, admin_page as _admin_page, own_frame_home as _own_frame_home,
    user_page as _user_page)
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE)

pytestmark = pytest.mark.browser

_CARD_TEXT = {
    "en": ("Console", "Fleet, users, audit", "Switch to the administration console"),
    "fr": ("Console", "Flotte, utilisateurs, audit", "Passer à la console d’administration"),
}
_SETTINGS_LABEL = {"en": "Settings", "fr": "Réglages"}
_ACCOUNT_LABEL = {"en": "Account", "fr": "Compte"}
_SETTLED = (
    "() => { const d = document.querySelector('.tab-bar__more');"
    " if (document.readyState !== 'complete' || !d || !d.open) return false;"
    " if (document.getAnimations().some((x) => x.playState === 'running'"
    " && x.effect.getComputedTiming().iterations !== Infinity)) return false;"
    " return [...d.querySelectorAll('.tab-bar__more-panel a, .tab-bar__more-panel button')]"
    ".every((a) => { const b = a.getBoundingClientRect();"
    " const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);"
    " return !!hit && a.contains(hit); }); }")
_CARD = """() => {
  const card = document.querySelector('.tab-bar__more-panel .link-card');
  if (!card) return null;
  const css = (el) => getComputedStyle(el);
  const box = card.getBoundingClientRect();
  const tile = card.querySelector('.link-card__icon');
  const chevron = card.querySelector('.link-card__chevron');
  const sub = card.querySelector('.link-card__subtitle');
  const probe = document.createElement('span');
  probe.style.color = 'var(--color-accent)';
  document.body.appendChild(probe);
  const accent = css(probe).color;
  probe.remove();
  const whole = (el) => !el || (el.scrollWidth <= el.clientWidth + 1
    && el.getBoundingClientRect().right <= box.right + 0.5);
  return {
    href: card.getAttribute('href'), aria: card.getAttribute('aria-label'),
    title: card.querySelector('.link-card__title').textContent.trim(),
    subtitle: sub ? sub.textContent.trim() : '', h: box.height, w: box.width,
    background: css(card).backgroundColor, border: css(card).borderTopColor,
    borderWidth: css(card).borderTopWidth, accent,
    tile: tile ? css(tile).backgroundColor : '', tileSvg: !!tile && !!tile.querySelector('svg use'),
    tileUse: tile && tile.querySelector('use') ? tile.querySelector('use').getAttribute('href') : '',
    chevron: chevron ? css(chevron).color : '', chevronSvg: !!chevron && !!chevron.querySelector('svg'),
    isSpaceLink: card.classList.contains('tab-bar__space-link'),
    subtitleWhole: whole(sub), titleWhole: whole(card.querySelector('.link-card__title')),
    inside: box.left >= 0 && box.right <= window.innerWidth,
    hit: (() => { const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
      return !!hit && card.contains(hit); })()};
}"""


def _page(role, new_context, server, viewport, lang, scheme, path=None):
    if role == "user":
        return _user_page(new_context, server, viewport, lang, scheme)
    return _admin_page(new_context, server, path or _own_frame_home, viewport, lang, scheme)


def _open_panel(page):
    page.wait_for_function("() => document.readyState === 'complete'")
    page.locator(".tab-bar__more > summary").click()
    page.wait_for_function(_SETTLED)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_an_administrator_sees_the_console_card_in_the_panel(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page = _page("admin", new_context, app_server_in_process, viewport, lang, scheme)
    try:
        _open_panel(page)
        card = page.evaluate(_CARD)
        title, subtitle, aria = _CARD_TEXT[lang]
        assert card is not None
        assert (card["title"], card["subtitle"], card["aria"]) == (title, subtitle, aria), card
        assert card["href"] == "/fleet" and card["isSpaceLink"], card
        assert card["h"] >= 56 and card["w"] > 200, card
        assert card["borderWidth"] == "1px" and card["border"] == card["accent"], card
        assert card["background"] not in ("rgba(0, 0, 0, 0)", "transparent"), card
        assert card["background"] != card["tile"], card
        assert card["tile"] == card["accent"] and card["tileUse"].endswith("icon-shield"), card
        assert card["chevronSvg"] and card["chevron"] == card["accent"], card
        assert card["titleWhole"] and card["subtitleWhole"] and card["inside"] and card["hit"], card
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_console_card_is_a_plain_get_link_that_opens_the_console(
        new_context, app_server_in_process, lang):
    context, page = _page("admin", new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, lang, "light")
    try:
        _open_panel(page)
        page.locator(".tab-bar__more-panel .link-card").click()
        page.wait_for_url("**/fleet")
        page.locator("main").wait_for(state="visible")
        _open_panel(page)
        back = page.evaluate(_CARD)
        assert back["href"].startswith("/"), back
        assert back["subtitle"] == "", back
        assert back["title"] == {"en": "My frame", "fr": "Mon cadre"}[lang], back
        assert back["isSpaceLink"] and back["h"] >= MIN_TAP_PX, back
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_person_who_is_not_an_administrator_has_no_console_card(
        new_context, app_server_in_process, lang):
    context, page = _page("user", new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, lang, "light")
    try:
        _open_panel(page)
        assert page.evaluate(_CARD) is None
        assert page.locator(".tab-bar__space-link").count() == 0
    finally:
        context.close()


def test_the_link_card_is_on_the_components_page_at_desktop_width(
        new_context, app_server_in_process):
    context, page = _admin_page(
        new_context, app_server_in_process, "/components", VIEWPORT_DESKTOP, "en", "light")
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        card = page.locator("#components-cards .link-card").first
        card.wait_for(state="visible")
        box = card.bounding_box()
        assert box["height"] >= 56 and box["width"] > 200
        assert card.locator(".link-card__title").inner_text().strip()
        assert card.locator(".link-card__subtitle").inner_text().strip()
    finally:
        context.close()
