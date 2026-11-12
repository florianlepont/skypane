"""Real-browser checks of the Users rows from a tablet width up: every address is one line
that ends in an ellipsis when it is too long (the whole address is its title and the row's
name), the last sign-in never wraps, and rows that show the same parts are equally tall."""
import time

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _assert_no_page_overflow, seed_state_dir
from server import fleet_db

pytestmark = pytest.mark.browser

LONG_EMAIL = "a-very-long-first-name.and-a-long-family-name@a-long-company-name.example.test"

# The table starts at 1272px, the narrowest width that holds every column on one line.
TABLE_FROM = 1272
WIDTHS = (
    pytest.param({"width": 768, "height": 1024}, id="768"),
    pytest.param({"width": 1120, "height": 900}, id="1120"),
    pytest.param({"width": TABLE_FROM, "height": 900}, id="1272"),
    pytest.param({"width": 1280, "height": 900}, id="1280"))

_READY = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")

_ROWS = """() => [...document.querySelectorAll('.users-table .users-row')].map((row) => {
  const lines = (el) => { const range = document.createRange(); range.selectNodeContents(el);
    return new Set([...range.getClientRects()].filter((r) => r.width > 0)
      .map((r) => Math.round(r.top))).size; };
  const email = row.querySelector('.users-email');
  const seen = row.querySelector('.users-cell--seen');
  const frames = row.querySelector('.users-cell--frames');
  const head = row.querySelector('th[scope=row]');
  const style = getComputedStyle(email);
  return {height: Math.round(row.getBoundingClientRect().height * 2) / 2,
          email: email.textContent, title: email.title, emailLines: lines(email),
          emailCut: email.scrollWidth > email.clientWidth, ellipsis: style.textOverflow,
          emailInside: email.getBoundingClientRect().right
            <= head.getBoundingClientRect().right + 0.5,
          named: head.textContent.includes(email.textContent),
          seen: seen.textContent.trim(), seenLines: lines(seen),
          seenCut: seen.scrollWidth > seen.clientWidth + 1,
          frames: frames.textContent.trim(),
          parts: [...frames.querySelectorAll('.users-frames__part')].map((part) => (
            {lines: lines(part), cut: part.scrollWidth > part.clientWidth})),
          invite: !!row.querySelector('.users-copy')};
})"""


@pytest.fixture(scope="module")
def rig(module_app_server_factory):
    """Four people who differ in everything a row shows: a recent sign-in, a co-manager, a
    very long address and two who never signed in."""
    def seed(state_dir):
        seed_state_dir(state_dir)
        people = fx.seed_fleet(state_dir)
        conn = fleet_db.connect(state_dir)
        try:
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?", (LONG_EMAIL, people.admin2_id))
            conn.execute(
                "INSERT INTO device_co_managers (device_id, user_id, added_by, added_at) "
                "VALUES (?, ?, ?, ?)",
                (people.owned_id, people.user_id, people.admin_id, int(time.time())))
            conn.commit()
        finally:
            conn.close()

    return module_app_server_factory(seed=seed, fake_providers=True)


def _users(new_context, rig, viewport, lang):
    name, value = fx.admin_cookie(rig.state_dir).split("=", 1)
    base = rig.base_url()
    context = new_context(viewport=viewport, reduced_motion="reduce")
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + "/users")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_READY, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS)
def test_every_address_is_one_line_and_a_long_one_ends_in_an_ellipsis(
        new_context, rig, viewport, lang):
    context, page = _users(new_context, rig, viewport, lang)
    try:
        rows = page.evaluate(_ROWS)
        assert len(rows) == 4, rows
        for row in rows:
            assert row["emailLines"] == 1, row
            assert row["ellipsis"] == "ellipsis" and row["emailInside"], row
            # The whole address stays in the row's header cell (its accessible name) and in
            # the title, whatever the ellipsis hides.
            assert row["title"] == row["email"] and row["named"], row
        long_row = next(row for row in rows if row["email"] == LONG_EMAIL)
        assert long_row["emailCut"], long_row
        assert not _assert_no_page_overflow(page, "Users", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS)
def test_the_last_sign_in_is_one_line_and_the_frames_never_break_inside_a_part(
        new_context, rig, viewport, lang):
    """The frame count and the co-manager mark are whole, each on one line: side by side on
    a card, one under the other in the table, where they stay within the row's height."""
    context, page = _users(new_context, rig, viewport, lang)
    try:
        rows = page.evaluate(_ROWS)
        never = "Jamais connecté" if lang == "fr" else "Never signed in"
        assert sum(row["seen"] == never for row in rows) >= 2, rows
        assert any(row["seen"] != never for row in rows), rows
        suffix = "co-gestionnaire" if lang == "fr" else "co-manager"
        assert any(suffix in row["frames"] for row in rows), rows
        for row in rows:
            assert row["seenLines"] == 1 and not row["seenCut"], row
            assert 1 <= len(row["parts"]) <= 2, row
            assert all(part["lines"] == 1 and not part["cut"] for part in row["parts"]), row
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS)
def test_rows_that_show_the_same_parts_are_equally_tall(new_context, rig, viewport, lang):
    """In the table every row has one height. As cards, a person who has not signed in yet
    carries one more line (the Copy invitation button); cards are equal within each kind."""
    context, page = _users(new_context, rig, viewport, lang)
    try:
        rows = page.evaluate(_ROWS)
        table = page.evaluate(
            "() => getComputedStyle(document.querySelector('.users-table')).display") == "table"
        assert table == (viewport["width"] >= TABLE_FROM)
        if table:
            assert len({row["height"] for row in rows}) == 1, rows
        else:
            for invited in (True, False):
                heights = {row["height"] for row in rows if row["invite"] == invited}
                assert len(heights) <= 1, rows
    finally:
        context.close()


# The box of each part of a row: the ink of a text, the box of a control or of a clipped line.
_INK = """() => [...document.querySelectorAll('.users-table .users-row')].map((row) => {
  const flat = (r) => ({l: r.left, r: r.right, t: r.top, b: r.bottom});
  const ink = (el) => { const range = document.createRange(); range.selectNodeContents(el);
    return flat(range.getBoundingClientRect()); };
  const box = (el) => flat(el.getBoundingClientRect());
  const pill = row.querySelector('.users-status .users-pill:not([hidden])');
  const card = row.getBoundingClientRect();
  const boxes = [
    ['address', box(row.querySelector('.users-email'))], ['status', box(pill)],
    ['role', box(row.querySelector('.users-cell--role select, .users-role-fixed'))],
    ['frames', ink(row.querySelector('.users-cell--frames'))],
    ['seen', ink(row.querySelector('.users-cell--seen'))],
    ['switch', box(row.querySelector('button[role=switch]'))]];
  return {boxes: boxes.map(([name, at]) => Object.assign({name: name}, at)),
          left: card.left, right: card.right, pill: pill.textContent,
          pillCut: pill.scrollWidth > pill.clientWidth};
})"""

ALL_WIDTHS = (
    pytest.param({"width": 360, "height": 844}, id="360"),
    pytest.param({"width": 390, "height": 844}, id="390")) + WIDTHS


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", ALL_WIDTHS)
def test_no_part_of_a_row_runs_into_another_or_out_of_the_row(
        new_context, rig, viewport, lang):
    """The address, the status, the role, the frames, the last sign-in and the switch share
    no pixel and stay inside the row, and the status pill is whole, on a phone card, a wide
    card and the table."""
    context, page = _users(new_context, rig, viewport, lang)
    try:
        rows = page.evaluate(_INK)
        assert len(rows) == 4, rows
        for row in rows:
            assert not row["pillCut"], row
            boxes = row["boxes"]
            for box in boxes:
                assert box["l"] >= row["left"] - 0.5 and box["r"] <= row["right"] + 0.5, box
            for index, one in enumerate(boxes):
                for two in boxes[index + 1:]:
                    apart = (one["r"] <= two["l"] + 0.5 or two["r"] <= one["l"] + 0.5
                             or one["b"] <= two["t"] + 0.5 or two["b"] <= one["t"] + 0.5)
                    assert apart, (one, two)
        assert not _assert_no_page_overflow(page, "Users", viewport["width"])
    finally:
        context.close()
