#!/usr/bin/env python3
"""Browser checks for Home's recent-flights group: no horizontal overflow at 390 and 360 px in
both themes and both languages, each row at least 54 px tall with its content inside it and a
44 px link target, a long operator name kept inside its row (the detail wraps, the value
truncates), all five flights fitting in one 390x844 screen with the group label at the top, the
rows working with scripts blocked, and the same rows at 1280 px. Also checks that Display, like
the other pages, shows no visible freshness line while keeping its hidden refresh marker.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

ROW = "li.recent-flight"
SECTION = 'section[aria-labelledby="home-flights"]'


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """A read-only server seeded with every flight variant and one repeated pass."""
    return module_app_server_factory(seed=vp.seed_home_tile_variety, fake_providers=True)


def _open_home(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/")
    page.locator(ROW).first.wait_for(state="visible")
    return context, page


_ROW_PROBE = (
    "() => [...document.querySelectorAll('li.recent-flight')].map(li => {"
    "  const c = li.getBoundingClientRect();"
    "  const inside = [...li.querySelectorAll('*')].every(el => {"
    "    const r = el.getBoundingClientRect();"
    "    return r.width === 0 || (r.left >= c.left - 0.5 && r.right <= c.right + 0.5"
    "      && r.top >= c.top - 0.5 && r.bottom <= c.bottom + 0.5);"
    "  });"
    "  const link = li.querySelector('.row__main').getBoundingClientRect();"
    "  const chip = li.querySelector('.row__chip').getBoundingClientRect();"
    "  return {callsign: li.querySelector('.row__label').textContent,"
    "          inside, height: c.height, link: [link.width, link.height],"
    "          chip: [Math.round(chip.width), Math.round(chip.height)]};"
    "})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_rows_fit_the_phone_in_both_themes(new_context, server, viewport, lang):
    """At 390 and 360 px, in English and French, light and dark: the page never scrolls
    sideways and every flight row is at least 54 px tall with its content inside its own box,
    a 32 px icon chip and a main area covering the row at 44 px or more (a plain row, not a link)."""
    context, page = _open_home(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            where = "Home rows (%s, %s)" % (lang, theme["theme"])
            failure = _assert_no_page_overflow(page, where, expected_width=viewport["width"])
            if failure:
                raise AssertionError(failure)
            rows = page.evaluate(_ROW_PROBE)
            assert len(rows) == 5, "%s: expected 5 rows, got %d" % (where, len(rows))
            for row in rows:
                ok = (row["inside"] and row["height"] >= 54 and row["link"][1] >= 44
                      and row["link"][0] >= viewport["width"] * 0.5 and row["chip"] == [32, 32])
                if not ok:
                    raise AssertionError("%s: row %r is broken: %r" % (where, row["callsign"], row))
    finally:
        context.close()


def test_five_flights_fit_one_phone_screen(new_context, server):
    """With the Recent flights label scrolled to the top of a 390x844 screen, all five rows
    sit fully above the tab bar."""
    context, page = _open_home(new_context, server, VIEWPORT_PHONE)
    try:
        seen = page.evaluate(
            "() => {"
            "  const s = document.querySelector('%s');"
            "  const top = s.getBoundingClientRect().top;"
            "  const tab = [...document.querySelectorAll('.tab-bar')]"
            "    .find(t => getComputedStyle(t).display !== 'none');"
            "  const floor = tab ? tab.getBoundingClientRect().top : innerHeight;"
            "  const rows = [...s.querySelectorAll('li.recent-flight')]"
            "    .map(li => li.getBoundingClientRect().bottom - top);"
            "  return {fit: rows.filter(b => b <= floor).length, floor, rows};"
            "}" % SECTION)
        if seen["fit"] < 5:
            raise AssertionError("expected 5 rows in one 390x844 screen, got %r" % (seen,))
    finally:
        context.close()


def test_rows_render_with_scripts_blocked(new_context, server):
    """The rows are server-rendered: with scripts blocked a phone still gets five rows with
    their ages, as plain rows (no link); only the See all flights row links to Flights."""
    with _no_js_page(new_context, server.base_url(), "/", viewport=VIEWPORT_PHONE) as page:
        assert page.locator(ROW).count() == 5
        assert page.locator("%s .row__value" % ROW).first.is_visible()
        assert page.locator("%s a" % ROW).count() == 0
        assert page.locator("li.recent-flight-all a.row__main").get_attribute("href") == "/flights"


def test_desktop_shows_the_same_rows(new_context, server):
    """At 1280 px the group renders the same five rows, each a flex row with its 32px chip,
    callsign, detail line and age, and a See all flights row after them."""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.locator(ROW).first.wait_for(state="visible")
        seen = page.evaluate(
            "() => ({"
            "  all: document.querySelectorAll('li.recent-flight-all').length,"
            "  rows: [...document.querySelectorAll('li.recent-flight')].map(li => ({"
            "    display: getComputedStyle(li).display,"
            "    parts: ['.row__label', '.row__detail', '.row__value'].every("
            "      s => li.querySelector(s))}))"
            "})")
        assert seen["all"] == 1 and len(seen["rows"]) == 5, seen
        for row in seen["rows"]:
            assert row == {"display": "flex", "parts": True}, row
    finally:
        context.close()


@pytest.mark.parametrize("lang,visible_word", [("en", "Updated"), ("fr", "Mis à jour")])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_display_shows_no_freshness_line_but_keeps_the_refresh_marker(
        new_context, server, viewport, lang, visible_word):
    """Display's header reads only its title: no "Updated" line and no live dot are painted,
    while the hidden refresh pill with its data-loaded-at instant is still in the header."""
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.locator(".page-header h1").wait_for(state="visible")
        header_text = page.locator(".page-header").inner_text()
        assert visible_word not in header_text, header_text
        assert page.locator("[data-refresh-live-dot], [data-refresh-clock]").count() == 0
        marker = page.locator(".page-header .page-header__freshness--silent [data-loaded-at]")
        assert marker.count() == 1
        assert marker.get_attribute("data-loaded-at")
        assert not marker.is_visible()
    finally:
        context.close()


_STATE_LINES = """() => {
  const out = [];
  for (const el of document.querySelectorAll('li.recent-flight .row__detail')) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const m = /(Au[\\s\\u00a0]d\\u00e9part|\\u00c0[\\s\\u00a0]l\\u2019arriv\\u00e9e)/.exec(n.data);
      if (!m) continue;
      const range = document.createRange();
      range.setStart(n, m.index); range.setEnd(n, m.index + m[0].length);
      const tops = new Set([...range.getClientRects()].map((r) => Math.round(r.top)));
      out.push({text: m[0], lines: tops.size});
    }
  }
  return out; }"""


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_a_french_state_phrase_is_never_split_across_two_lines(new_context, server, viewport):
    """"Au départ" and "À l'arrivée" stay whole on one line of a recent-flight detail"""
    context, page = _open_home(new_context, server, viewport, "fr")
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        found = page.evaluate(_STATE_LINES)
        assert found, "no state phrase in the seeded rows"
        assert all(item["lines"] == 1 for item in found), found
    finally:
        context.close()
