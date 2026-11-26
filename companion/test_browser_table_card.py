#!/usr/bin/env python3
"""Real-browser checks of the table-in-a-rounded-card look on the Users table (wide table, from
79.5rem) and the Editor airline table (wide table, from 70rem), in English and French and in
both themes.

The card takes the corners of its table: no cell reaches past the rounded corner (a point just
inside each corner of the card hits nothing of the table), the header row is tinted with a
readable label, and the last row has no rule under it. An opened "..." menu is never cut by the
card (its corners and centre are hit-tested), including on the last row. A control of the last
row keeps its focus ring inside the card. On the phone the Users card layout is unchanged.

State is waited for (settled page, finished animations), never read right after an input.
"""
import pytest

import animation_settle
import fleet_console_support as fx
import skypane_contrast_check
from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

USERS = {
    "route": "/users",
    "card": "table.users-table",
    "head": "table.users-table thead th.users-col--user",
    "last_row": "table.users-table tbody tr.users-row:last-child",
    "last_cell": "table.users-table tbody tr.users-row:last-child .users-cell--user",
    "first_row": "table.users-table tbody tr.users-row:nth-child(2)",
    "menu": "details.row-menu",
    "clips": True,
}
EDITOR = {
    "route": "/airlines/manage",
    "card": "table.airlines-table:not(.airlines-table--gaps)",
    "head": "table.airlines-table:not(.airlines-table--gaps) thead th.airlines-col--name",
    "last_row": "table.airlines-table:not(.airlines-table--gaps) tbody.airline-group:last-of-type"
                " > tr.airlines-row:first-child",
    "last_cell": "table.airlines-table:not(.airlines-table--gaps) tbody.airline-group:last-of-type"
                 " > tr.airlines-row:first-child > .airlines-cell--name",
    "first_row": "table.airlines-table:not(.airlines-table--gaps) tbody.airline-group:first-of-type"
                 " > tr.airlines-row:first-child",
    "menu": "details.row-menu",
    "clips": False,
}
TABLES = (("users", USERS), ("editor", EDITOR))

# Whether a point just inside each corner of the card still hits something of the table.
_CORNER_HITS = """card => {
  const root = document.querySelector(card);
  const r = root.getBoundingClientRect();
  const points = {tl: [r.left + 1, r.top + 1], tr: [r.right - 2, r.top + 1],
                  bl: [r.left + 1, r.bottom - 2], br: [r.right - 2, r.bottom - 2]};
  const out = {};
  for (const [name, [x, y]] of Object.entries(points)) {
    const hit = document.elementFromPoint(x, y);
    out[name] = !!hit && root.contains(hit);
  }
  return out;
}"""

# The header cell's label and fill (composited as drawn), the card's fill, the card's overflow
# and the bottom rule of the last row's cell.
_FACTS = """args => {
  const q = s => document.querySelector(s);
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const pixel = css => {
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = css; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return {hex: '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join(''),
            alpha: d[3]};
  };
  const head = getComputedStyle(q(args.head));
  const card = getComputedStyle(q(args.card));
  const cell = getComputedStyle(q(args.last_cell));
  return {
    overflow: card.overflow,
    headFill: pixel(head.backgroundColor),
    cardFill: card.backgroundColor,
    headBg: head.backgroundColor,
    headInk: pixel(head.color).hex,
    lastRule: cell.borderBottomWidth,
    rowHeight: q(args.last_row).getBoundingClientRect().height,
  };
}"""

_PANEL_HITS = """panel => {
  const el = document.querySelector(panel);
  const r = el.getBoundingClientRect();
  const points = [[r.left + 10, r.top + 10], [r.right - 10, r.top + 10], [r.left + 10, r.bottom - 10],
                  [r.right - 10, r.bottom - 10], [(r.left + r.right) / 2, (r.top + r.bottom) / 2]];
  return {
    hits: points.map(([x, y]) => { const hit = document.elementFromPoint(x, y);
                                    return !!hit && el.contains(hit); }),
    inViewport: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
    box: {w: r.width, h: r.height},
  };
}"""

# The focus ring (outline plus offset) of the focused element against the card's box.
_RING_INSIDE = """card => {
  const el = document.activeElement;
  const s = getComputedStyle(el);
  const grow = s.outlineStyle === 'none' ? 0
    : parseFloat(s.outlineWidth) + Math.max(0, parseFloat(s.outlineOffset));
  const r = el.getBoundingClientRect();
  const c = document.querySelector(card).getBoundingClientRect();
  return {ring: s.outlineStyle !== 'none', inside: r.left - grow >= c.left - 0.5
    && r.right + grow <= c.right + 0.5 && r.top - grow >= c.top - 0.5
    && r.bottom + grow <= c.bottom + 0.5};
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    def seed(state_dir):
        seed_airline_editor(state_dir)
        fx.seed_users(state_dir)
    return module_app_server_factory(seed=seed, fake_providers=True)


def _open(new_context, server, table, viewport, lang="en", theme="light", **context_args):
    context = new_context(viewport=viewport, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + table["route"])
    page.locator(table["card"]).wait_for(state="visible")
    if theme is not None:
        _set_ui_theme(page, theme)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    return context, page


def _reveal(page, selector):
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,table", TABLES, ids=[t[0] for t in TABLES])
def test_the_card_takes_the_table_corners_tints_its_header_and_ends_without_a_rule(
        new_context, server, name, table, lang, theme):
    context, page = _open(new_context, server, table, VIEWPORT_DESKTOP, lang, theme)
    where = "%s/%s/%s" % (name, lang, theme)
    try:
        _reveal(page, table["card"])
        _assert_corners_hit_nothing(page, table, where)
        page.locator(table["last_row"]).scroll_into_view_if_needed()
        _assert_corners_hit_nothing(page, table, where)
        facts = page.evaluate(_FACTS, table)
        if table["clips"]:
            assert facts["overflow"] == "hidden", (where, facts)
        assert facts["headFill"]["alpha"] == 255, (where, facts)
        assert facts["headBg"] != facts["cardFill"], (where, facts)
        ratio = skypane_contrast_check.contrast_ratio(
            facts["headInk"], facts["headFill"]["hex"])
        assert ratio >= 4.5, (where, ratio, facts)
        assert facts["lastRule"] == "0px", (where, facts)
        assert facts["rowHeight"] >= 44, (where, facts)
    finally:
        context.close()


def _assert_corners_hit_nothing(page, table, where):
    page.locator(table["card"]).evaluate("el => el.scrollIntoView({block: 'nearest'})")
    hits = page.evaluate(_CORNER_HITS, table["card"])
    assert not any(hits.values()), (where, hits)


def _open_menu(page, table, row):
    toggle = "%s %s > summary" % (table[row], table["menu"])
    _reveal(page, toggle)
    page.locator(toggle).first.click()
    panel = "%s %s[open] > .row-menu__panel" % (table[row], table["menu"])
    page.locator(panel).wait_for(state="visible")
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    return panel


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("row", ["first_row", "last_row"])
@pytest.mark.parametrize("name,table", TABLES, ids=[t[0] for t in TABLES])
def test_an_opened_row_menu_is_never_clipped_by_the_card(
        new_context, server, name, table, row, lang):
    context, page = _open(new_context, server, table, VIEWPORT_DESKTOP, lang)
    where = "%s/%s/%s" % (name, row, lang)
    try:
        panel = _open_menu(page, table, row)
        seen = page.evaluate(_PANEL_HITS, panel)
        assert all(seen["hits"]), (where, seen)
        assert seen["inViewport"], (where, seen)
        assert seen["box"]["h"] >= 44, (where, seen)
        page.keyboard.press("Escape")
        page.locator(panel).wait_for(state="hidden")
    finally:
        context.close()


def test_the_users_card_clips_again_once_its_menu_is_closed(new_context, server):
    context, page = _open(new_context, server, USERS, VIEWPORT_DESKTOP)
    try:
        _open_menu(page, USERS, "last_row")
        page.keyboard.press("Escape")
        page.locator("%s details.row-menu[open]" % USERS["card"]).wait_for(state="detached")
        assert page.locator(USERS["card"]).evaluate(
            "el => getComputedStyle(el).overflow") == "hidden"
    finally:
        context.close()


@pytest.mark.parametrize("name,table", TABLES, ids=[t[0] for t in TABLES])
def test_the_focus_ring_of_a_last_row_control_stays_inside_the_card(
        new_context, server, name, table):
    context, page = _open(new_context, server, table, VIEWPORT_DESKTOP)
    try:
        controls = page.locator(
            "%s :is(a[href], button, summary, select, input):visible" % table["last_row"])
        count = controls.count()
        assert count >= 2, (name, count)
        for index in range(count):
            control = controls.nth(index)
            control.scroll_into_view_if_needed()
            control.focus()
            seen = page.evaluate(_RING_INSIDE, table["card"])
            assert seen["ring"] and seen["inside"], (name, index, seen)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_users_phone_cards_are_unchanged(new_context, server, lang):
    context, page = _open(new_context, server, USERS, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        assert not _assert_no_page_overflow(page, "users/360/" + lang, 360)
        assert page.locator("table.users-table thead").evaluate(
            "el => getComputedStyle(el).display") == "none"
        assert page.locator(USERS["card"]).evaluate(
            "el => getComputedStyle(el).overflow") == "visible"
        heights = page.locator("tr.users-row").evaluate_all(
            "rows => rows.map(r => r.getBoundingClientRect().height)")
        assert heights and all(h >= 76 for h in heights), heights
        rule = page.locator(USERS["last_cell"]).evaluate(
            "el => getComputedStyle(el).borderBottomWidth")
        assert rule == "0px", rule
    finally:
        context.close()


@pytest.mark.parametrize("name,table", TABLES, ids=[t[0] for t in TABLES])
def test_no_animation_runs_under_reduced_motion(new_context, server, name, table):
    context, page = _open(
        new_context, server, table, VIEWPORT_DESKTOP, theme=None, reduced_motion="reduce")
    try:
        _reveal(page, table["card"])
        running = page.evaluate(
            "() => document.getAnimations().filter(a => a.playState === 'running').length")
        assert running == 0
    finally:
        context.close()
