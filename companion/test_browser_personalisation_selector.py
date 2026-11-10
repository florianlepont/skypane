#!/usr/bin/env python3
"""Browser checks of the Personalisation selector (Departures, Arrivals, Layout, Special
looks, Calendar): one segmented control that fits a 360 px phone in English and French without scrolling sideways or
clipping a label, four 44px segments inside one track, exactly one current segment, a labelled
navigation of plain links reachable and operable from the keyboard, and the Special looks and
Calendar views as one group of rows with a dashed add row instead of a titled card.
"""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login,
    _set_ui_theme, seed_state_dir,
)
from server.plane import colour_rules

pytestmark = pytest.mark.browser

NAV = "nav.personalisation-nav"
LINK = NAV + " a.personalisation-nav__link"
ROUTES = (layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE,
          layout.DISPLAY_SPECIAL_LOOKS_ROUTE, layout.DISPLAY_CALENDAR_ROUTE)
LABELS = {
    "en": ["Departures", "Arrivals", "Special looks", "Calendar"],
    "fr": ["Départs", "Arrivées", "Allures spéciales", "Calendrier"],
}
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
_PROBE = """() => {
  const nav = document.querySelector('nav.personalisation-nav');
  const track = nav.getBoundingClientRect();
  return {
    overflow: nav.scrollWidth - nav.clientWidth,
    links: [...nav.querySelectorAll('a')].map((a) => {
      const r = a.getBoundingClientRect(); const span = a.querySelector('span');
      const s = span.getBoundingClientRect();
      return {text: span.textContent, w: r.width, h: r.height,
              inside: r.left >= track.left - 0.5 && r.right <= track.right + 0.5,
              clipped: span.scrollWidth > span.clientWidth + 0.5,
              current: a.getAttribute('aria-current'),
              centred: Math.abs((s.left + s.right) / 2 - (r.left + r.right) / 2) <= 1};
    })};
}"""


def _seed(state_dir):
    seed_state_dir(state_dir)
    assert colour_rules.add_rule(state_dir, "prefix", "TVF", "white") == colour_rules.ADD_OK_NEW


def _open(new_context, server, viewport, lang, route, theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(NAV + ".is-enhanced").wait_for(state="visible")
    _set_ui_theme(page, theme)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.fixture
def server(make_app_server):
    return make_app_server(seed=_seed)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("route", ROUTES, ids=["departures", "arrivals", "looks", "calendar"])
def test_the_selector_fits_a_360px_phone_in_every_view(new_context, server, lang, route, theme):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang, route, theme)
    try:
        probe = page.evaluate(_PROBE)
        assert probe["overflow"] <= 0, probe
        assert [link["text"] for link in probe["links"]] == LABELS[lang]
        for link in probe["links"]:
            assert link["h"] >= 44 - 0.5 and link["inside"] and not link["clipped"], link
            assert link["centred"], link
        assert [link["current"] for link in probe["links"]].count("page") == 1
        assert not _assert_no_page_overflow(page, "selector", VIEWPORT_MIN_SUPPORTED["width"])
    finally:
        context.close()


def test_the_selector_is_a_labelled_navigation_operable_from_the_keyboard(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, "en", layout.DISPLAY_ROUTE)
    try:
        assert page.locator(NAV).get_attribute("aria-label") == "Style sections"
        assert page.locator(LINK).count() == 4
        page.focus(LINK + ":nth-of-type(3)")
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.textContent.trim()"
            " === 'Special looks'", timeout=5000)
        page.keyboard.press("Enter")
        page.wait_for_url("**" + layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
        page.wait_for_function(_SETTLED, timeout=15000)
        current = page.locator(LINK + '[aria-current="page"]')
        assert current.count() == 1 and current.inner_text().strip() == "Special looks"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_special_looks_and_calendar_are_one_group_with_a_dashed_add_row(new_context, server, lang):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang,
                          layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        measured = page.evaluate("""() => {
          const card = document.querySelector('#personalisation-special-looks');
          const group = card.querySelector('ul.special-list:not(.special-list--add)');
          const add = card.querySelector('.special-row--add');
          const cs = (e) => getComputedStyle(e);
          return {cardBg: cs(card).backgroundColor, cardBorder: cs(card).borderTopWidth,
                  groupRadius: cs(group).borderTopLeftRadius, groupBg: cs(group).backgroundColor,
                  groupRows: group.querySelectorAll(':scope > li.special-row').length,
                  addInGroup: !!group.querySelector('.special-row--add'),
                  addBorder: cs(add).borderTopStyle,
                  addBelow: add.getBoundingClientRect().top >= group.getBoundingClientRect().bottom,
                  addHeight: add.getBoundingClientRect().height};
        }""")
        assert measured["cardBg"] == "rgba(0, 0, 0, 0)" and measured["cardBorder"] == "0px", measured
        assert measured["groupRadius"] == "22px" and measured["groupBg"] != "rgba(0, 0, 0, 0)", measured
        assert measured["groupRows"] >= 1 and not measured["addInGroup"], measured
        assert measured["addBorder"] == "dashed" and measured["addBelow"], measured
        assert measured["addHeight"] >= 44 - 0.5, measured
        page.goto(server.base_url() + layout.DISPLAY_CALENDAR_ROUTE)
        page.wait_for_function(_SETTLED, timeout=15000)
        connect = page.locator("#personalisation-calendar a.calendar-manage--primary")
        assert connect.inner_text().strip() == (
            "Connect a calendar" if lang == "en" else "Connecter un calendrier")
        assert page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'#personalisation-calendar a.calendar-manage--primary')).borderTopStyle") == "dashed"
        connect.click()
        page.wait_for_url("**" + layout.DISPLAY_CALENDAR_CONNECT_ROUTE)
        page.locator("#calendar-connect-url").wait_for(state="visible")
        assert page.locator("dialog[open]").count() == 0
    finally:
        context.close()


def test_the_selector_fits_the_desktop_column(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, "fr", layout.DISPLAY_ROUTE)
    try:
        probe = page.evaluate(_PROBE)
        assert probe["overflow"] <= 0 and not any(link["clipped"] for link in probe["links"])
    finally:
        context.close()
