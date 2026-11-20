"""Real-browser structure checks of the Console pages on the grouped-list language: the Fleet
blocks are glass groups under a section label with nothing nested, the Users table and the
Airline editor keep header and row geometry, the unidentified rows sit in their own labelled card above the table, the
Audit log phone list is one glass group, and none of them overflows at 360px in either
language and theme."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _set_ui_theme,
    seed_state_dir)
from server import fleet_db

pytestmark = pytest.mark.browser

def _seed(state_dir):
    seed_state_dir(state_dir)
    fx.seed_fleet(state_dir)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, persona, path, dialog, viewport, lang, scheme):
    conn = fleet_db.connect(server.state_dir)
    try:
        owned = conn.execute("SELECT id FROM devices WHERE name = 'Kitchen'").fetchone()["id"]
    finally:
        conn.close()
    name, value = fx.admin_cookie(server.state_dir).split("=", 1)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(),
         "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()},
        {"name": auth.UI_THEME_COOKIE_NAME, "value": scheme, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + path.format(owned=owned))
    page.locator("main").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    _set_ui_theme(page, scheme)
    page.wait_for_function(
        "() => document.getAnimations().every((a) => a.effect.getComputedTiming().iterations !== Infinity"
        " ? a.playState !== 'running' : true)", timeout=10000)
    return context, page


THEMES = ("light", "dark")
LANGS = ("en", "fr")

_FLEET = """() => {
  const bad = [];
  const blocks = [...document.querySelectorAll('section.fleet-block')];
  blocks.forEach((s) => {
    // The State section is four tiles (cards of their own), not a group.
    const ownCards = s.querySelector(':scope > ul.fleet-tiles') !== null;
    const label = s.querySelector(':scope > h2.section-label');
    const groups = s.querySelectorAll(':scope > ul.group');
    if (!label) bad.push('no label');
    if (groups.length !== (ownCards ? 0 : 1)) bad.push('groups: ' + groups.length);
    if (s.querySelectorAll('.group .group').length) bad.push('nested group');
    const inner = ownCards ? [] : [...s.querySelectorAll('.group *')].filter((e) => {
      const c = getComputedStyle(e);
      return e.checkVisibility() && c.boxShadow !== 'none' && !e.closest('.switch, .dirty-bar, details.row-menu')
        && c.borderRadius !== '0px' && c.backgroundColor !== 'rgba(0, 0, 0, 0)'
        && e.matches('section, li, div, ul');
    }).map((e) => e.className);
    if (inner.length) bad.push('card surface inside a group: ' + inner.slice(0, 3));
  });
  const tiles = [...document.querySelectorAll('.fleet-tile')].filter((t) => t.checkVisibility());
  if (tiles.length !== 4) bad.push('tiles: ' + tiles.length);
  return {bad: bad, count: blocks.length};
}"""


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_fleet_blocks_are_flat_glass_groups(new_context, server, viewport, lang, scheme):
    context, page = _open(
        new_context, server, "admin", "/fleet?frame={owned}", None, viewport, lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, "fleet", viewport["width"])
        out = page.evaluate(_FLEET)
        # State (the tiles), Settings and Access.
        assert out["count"] == 3 and out["bad"] == [], out
    finally:
        context.close()


_TABLE = """(sel) => {
  const th = [...document.querySelectorAll(sel + ' thead th, ' + sel + ' thead td.users-col')]
    .filter((e) => e.checkVisibility() && e.textContent.trim());
  const heads = th.map((e) => { const c = getComputedStyle(e);
    return {size: c.fontSize, weight: c.fontWeight, upper: c.textTransform}; });
  const rows = [...document.querySelectorAll(sel + ' tbody tr')]
    .filter((e) => e.checkVisibility() && e.getBoundingClientRect().height > 0)
    .map((e) => e.getBoundingClientRect().height);
  return {heads: heads, rows: rows};
}"""


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("path,sel,head_size", [
    ("/users", ".users-table", "12px"), ("/airlines/manage", ".airlines-table", "13px")])
def test_console_tables_have_the_quiet_header_and_tall_rows(
        new_context, server, path, sel, head_size, lang, scheme):
    context, page = _open(new_context, server, "admin", path, None, VIEWPORT_DESKTOP, lang, scheme)
    try:
        out = page.evaluate(_TABLE, sel)
        assert out["heads"], path
        for head in out["heads"]:
            assert head["size"] == head_size and head["weight"] == "600" and head["upper"] == "none", head
        assert out["rows"] and min(out["rows"]) >= 55.5, out["rows"]
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
def test_unidentified_airline_rows_sit_in_their_own_labelled_card_with_no_chip(
        new_context, server, lang, scheme):
    context, page = _open(
        new_context, server, "admin", "/airlines/manage", None, VIEWPORT_DESKTOP, lang, scheme)
    try:
        assert page.locator(".airline-group--gap .airlines-gap__prefix").count() >= 1
        assert page.locator(".airline-group--gap .airlines-gap-chip").count() == 0
        out = page.evaluate(
            "() => { const gap = document.querySelector('.airline-group--gap').closest('table');"
            " const main = [...document.querySelectorAll('table.airlines-table')]"
            ".find((t) => !t.querySelector('.airline-group--gap') && t.querySelector('#airline-air-france'));"
            " return {label: gap.querySelector('caption').textContent.trim(),"
            " alone: gap.querySelectorAll('.airline-group:not(.airline-group--gap)').length,"
            " above: !!main && gap.getBoundingClientRect().bottom <= main.getBoundingClientRect().top}; }")
        assert out["label"] and out["alone"] == 0 and out["above"], out
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("path", ["/users", "/airlines/manage", "/audit"])
def test_console_pages_fit_a_360px_phone(new_context, server, path, lang, scheme):
    context, page = _open(
        new_context, server, "admin", path, None, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, path, 360)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
def test_the_audit_phone_list_is_one_glass_group(new_context, server, scheme):
    context, page = _open(
        new_context, server, "admin", "/audit", None, VIEWPORT_MIN_SUPPORTED, "en", scheme)
    try:
        box = page.locator("ul.audit-cards")
        assert box.count() == 1
        out = box.evaluate(
            "(e) => ({bg: getComputedStyle(e).backgroundColor, r: getComputedStyle(e).borderRadius,"
            " cards: [...e.children].every((c) => getComputedStyle(c).backgroundColor === 'rgba(0, 0, 0, 0)')})")
        assert out["bg"] != "rgba(0, 0, 0, 0)" and out["r"] == "22px" and out["cards"]
    finally:
        context.close()
