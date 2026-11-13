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


_TOP = """() => {
  const panel = document.querySelector('.tab-bar__more-panel');
  const css = (el) => getComputedStyle(el);
  const grab = panel.querySelector('.tab-bar__grab');
  const row = panel.querySelector('.tab-bar__account');
  const avatar = row.querySelector('.tab-bar__avatar');
  const email = row.querySelector('.tab-bar__account-email');
  const name = row.querySelector('.tab-bar__account-name');
  const gb = grab ? grab.getBoundingClientRect() : null;
  const pb = panel.getBoundingClientRect();
  const ab = avatar ? avatar.getBoundingClientRect() : null;
  const rb = row.getBoundingClientRect();
  const hit = document.elementFromPoint(rb.left + rb.width / 2, rb.top + rb.height / 2);
  return {
    grabFirst: panel.firstElementChild === grab, grabHidden: !!grab && grab.getAttribute('aria-hidden') === 'true',
    grabW: gb && gb.width, grabH: gb && gb.height, grabCentred: gb && Math.abs((gb.left + gb.width / 2) - (pb.left + pb.width / 2)) < 1.5,
    grabBg: grab ? css(grab).backgroundColor : '',
    initial: avatar ? avatar.textContent.trim() : null, avatarW: ab && ab.width, avatarH: ab && ab.height,
    avatarRadius: avatar ? css(avatar).borderTopLeftRadius : '',
    avatarBg: avatar ? css(avatar).backgroundColor : '',
    name: name ? name.textContent.trim() : null, email: email ? email.textContent.trim() : null,
    emailWhole: !email || (email.scrollWidth <= email.clientWidth + 1 && email.getBoundingClientRect().right <= rb.right + 0.5),
    href: row.getAttribute('href'), h: rb.height, hit: !!hit && row.contains(hit),
    chevron: !!row.querySelector('svg use[href$="icon-chevron-right"]'),
    nameBeforeEmail: !!name && !!email && name.getBoundingClientRect().bottom <= email.getBoundingClientRect().top + 1};
}"""


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("role", ["admin", "user"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_panel_opens_with_a_grab_handle_and_the_account_row(
        new_context, app_server_in_process, viewport, role, lang, scheme):
    context, page = _page(role, new_context, app_server_in_process, viewport, lang, scheme)
    try:
        _open_panel(page)
        top = page.evaluate(_TOP)
        assert top["grabFirst"] and top["grabHidden"], top
        assert 36 <= top["grabW"] <= 44 and 3 <= top["grabH"] <= 5 and top["grabCentred"], top
        assert top["grabBg"] not in ("rgba(0, 0, 0, 0)", "transparent"), top
        assert top["name"] == _ACCOUNT_LABEL[lang], top
        assert top["email"] and "@" in top["email"], top
        assert top["initial"] == top["email"][0].upper(), top
        assert top["avatarW"] == 44 and top["avatarH"] == 44, top
        assert top["avatarRadius"] in ("50%", "22px"), top
        assert top["avatarBg"] not in ("rgba(0, 0, 0, 0)", "transparent"), top
        assert top["h"] >= 64 and top["hit"] and top["chevron"], top
        assert top["emailWhole"] and top["nameBeforeEmail"], top
        assert top["href"].rstrip("/").endswith("/account"), top
    finally:
        context.close()


def test_the_account_row_opens_the_account_page(new_context, app_server_in_process):
    context, page = _page("user", new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, "en", "light")
    try:
        _open_panel(page)
        page.locator(".tab-bar__account").click()
        page.wait_for_url("**/account")
    finally:
        context.close()


_SETTINGS = """() => {
  const panel = document.querySelector('.tab-bar__more-panel');
  const css = (el) => getComputedStyle(el);
  const label = panel.querySelector('.section-label');
  const group = panel.querySelector('.group');
  const rows = [...panel.querySelectorAll('.group > .row')];
  const out = panel.querySelector('.tab-bar__sign-out button');
  const probe = document.createElement('span');
  probe.style.color = 'var(--color-status-error)';
  document.body.appendChild(probe);
  const alert = css(probe).color;
  probe.remove();
  const pb = panel.getBoundingClientRect();
  const gb = group.getBoundingClientRect();
  const ob = out.getBoundingClientRect();
  const hitOf = (el) => { const b = el.getBoundingClientRect();
    const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return !!hit && el.contains(hit); };
  return {
    label: label.textContent.trim(), labelTransform: css(label).textTransform,
    labelAboveGroup: label.getBoundingClientRect().bottom <= gb.top + 1,
    groupBorder: css(group).borderTopWidth, groupInPanel: gb.left >= pb.left && gb.right <= pb.right,
    rows: rows.map((row) => {
      const rb = row.getBoundingClientRect();
      const text = row.querySelector('.row__label');
      const form = row.querySelector('form');
      const icon = row.querySelector('.tab-bar__row-icon use');
      const tb = text.getBoundingClientRect(), fb = form.getBoundingClientRect();
      return {h: rb.height, text: text.textContent.trim(),
        icon: icon ? icon.getAttribute('href') : '', formAction: form.getAttribute('action'),
        labelLeftOfControl: tb.right <= fb.left + 1, controlInside: fb.right <= rb.right + 0.5 && fb.left >= rb.left,
        labelWhole: text.scrollWidth <= text.clientWidth + 1,
        options: [...form.querySelectorAll('button')].map((b) => b.getBoundingClientRect().height),
        optionsWhole: [...form.querySelectorAll('button')].every((b) => b.scrollWidth <= b.clientWidth + 0.5),
        optionsHit: [...form.querySelectorAll('button')].every(hitOf)}; }),
    out: {text: out.textContent.trim(), h: ob.height, w: ob.width, panelW: pb.width,
      color: css(out).color, alert, background: css(out).backgroundColor,
      icon: !!out.querySelector('svg use[href$="icon-sign-out"]'), hit: hitOf(out),
      belowGroup: ob.top >= gb.bottom + 8, inside: ob.right <= pb.right && ob.left >= pb.left,
      whole: out.scrollWidth <= out.clientWidth + 1}};
}"""
_SIGN_OUT_TEXT = {"en": "Sign out", "fr": "Se déconnecter"}
_ROWS = {
    "en": [("Theme", "icon-sun", "/ui-theme"), ("Language", "icon-globe", "/ui-lang")],
    "fr": [("Thème", "icon-sun", "/ui-theme"), ("Langue", "icon-globe", "/ui-lang")],
}


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("role", ["admin", "user"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_settings_group_and_the_sign_out_button(
        new_context, app_server_in_process, viewport, role, lang, scheme):
    context, page = _page(role, new_context, app_server_in_process, viewport, lang, scheme)
    try:
        _open_panel(page)
        data = page.evaluate(_SETTINGS)
        assert data["label"] == _SETTINGS_LABEL[lang] and data["labelTransform"] == "uppercase", data
        assert data["labelAboveGroup"] and data["groupBorder"] == "1px" and data["groupInPanel"], data
        assert [(r["text"], r["icon"].split("#")[-1], r["formAction"]) for r in data["rows"]] == [
            (text, icon, action) for text, icon, action in _ROWS[lang]], data
        for row in data["rows"]:
            assert row["h"] == 56, data
            assert row["labelLeftOfControl"] and row["controlInside"] and row["labelWhole"], data
            assert all(h >= MIN_TAP_PX for h in row["options"]) and row["optionsHit"], data
            assert row["optionsWhole"], data
        out = data["out"]
        assert out["text"] == _SIGN_OUT_TEXT[lang] and out["h"] == 48, data
        assert out["w"] >= out["panelW"] - 2 * 24 - 2 and out["inside"] and out["belowGroup"], data
        assert out["color"] == out["alert"] and out["icon"] and out["hit"] and out["whole"], data
        assert out["background"] not in ("rgba(0, 0, 0, 0)", "transparent"), data
    finally:
        context.close()


def test_sign_out_button_is_still_the_post_logout_form(new_context, app_server_in_process):
    context, page = _page("user", new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, "en", "light")
    try:
        _open_panel(page)
        assert page.locator("form.tab-bar__sign-out").get_attribute("method") == "post"
        assert page.locator("form.tab-bar__sign-out").get_attribute("action") == "/logout"
        assert page.locator("form.tab-bar__sign-out button[type=submit]").count() == 1
    finally:
        context.close()
