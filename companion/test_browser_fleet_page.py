"""Real-browser checks of the admin Fleet page's frame list: the Other frames
block (pending and retired rows) and the selected frame's detail header. No table
and no sideways scroll at 360 and 1280px, English and French, light and dark; one
status dot per row with its accessible name; wrapping frame names; 44px hit areas
on the header action and the actions menus; and the actions menu with and without
script."""
import pytest

import fleet_console_support as fx
from frame_menu_support import open_menu
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44
LONG_NAME = "Salon with an exceedingly long frame name " + "x" * 60

_ROW_FACTS = (
    "() => [...document.querySelectorAll('li.entity-row')]"
    ".filter(row => row.getClientRects().length > 0).map(row => {"
    " const title = row.querySelector('.entity-row__title');"
    " const b = row.getBoundingClientRect();"
    " const kids = [...row.querySelectorAll('.entity-row__title, .entity-row__meta')];"
    " return {dots: row.querySelectorAll('.dot').length,"
    "  label: (row.querySelector('[role=img]') || {getAttribute: () => ''})"
    "    .getAttribute('aria-label'),"
    "  text: title.textContent,"
    "  family: getComputedStyle(title).fontFamily,"
    "  metaFamily: kids.map(k => getComputedStyle(k).fontFamily),"
    "  clipped: kids.some(k => k.scrollWidth > k.clientWidth + 1"
    "    || k.getBoundingClientRect().right > b.right + 0.5)}; })")

_EN_WORDS = {
    "Not seen yet", "No contact", "Overdue", "Low battery", "Resting", "Online",
    "Waiting for pairing", "Retired"}


def _open(new_context, server, viewport, lang="en", scheme="light", path="/fleet"):
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path.replace("{owned}", seed.owned_id))
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_other_frames_fit_with_one_dot_per_row_and_no_table(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, scheme)
    where = "fleet/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        assert page.locator("table").count() == 0
        # The pending and retired frames are a section of the page, open at every width.
        assert page.locator("details.fleet-other").count() == 0
        assert page.locator(".fleet-block--others li.entity-row").count() == 2
        assert not _assert_no_page_overflow(page, where + "/other", viewport["width"])
        rows = page.evaluate(_ROW_FACTS)
        assert len(rows) == 2
        for row in rows:
            assert row["dots"] == 1 and row["label"], (where, row)
            assert not row["clipped"], (where, row)
            assert "mono" not in row["family"].lower(), (where, row)
            assert all("mono" not in family.lower() for family in row["metaFamily"])
            if lang == "en":
                assert row["label"] in _EN_WORDS, (where, row)
        _assert_hit_target(page, "summary.frame-menu__button", where)
        open_menu(page)
        _assert_hit_target(page, "a.frame-row--add", where)
        assert page.locator(".page-header a.page-header__action").count() == 0
        assert page.locator(
            "main h1").evaluate("e => !getComputedStyle(e).fontFamily.includes('mono')")
        header = page.locator(".page-header")
        assert header.bounding_box()["height"] < 220, where
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_long_frame_name_never_overflows_and_the_header_links_stay_in_view_at_360(
        new_context, app_server_in_process, lang):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    from server import fleet_db
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute("UPDATE devices SET name = ? WHERE id = ?", (LONG_NAME, seed.owned_id))
        conn.commit()
    finally:
        conn.close()
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
        page.locator("main").wait_for(state="visible")
        assert not _assert_no_page_overflow(page, "long-name", 360)
        links = page.locator(".fleet-detail-head a.row-action")
        links.first.wait_for(state="visible")
        assert links.count() == 2
        for index in range(2):
            box = links.nth(index).bounding_box()
            assert box["height"] >= MIN_TAP_PX - 0.5 and box["x"] >= -0.5
            assert box["x"] + box["width"] <= 360 + 0.5
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_header_offers_two_visible_44px_links_not_a_menu(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(
        new_context, app_server_in_process, viewport, path="/fleet?frame={owned}")
    try:
        links = ".fleet-detail-head a.row-action"
        _assert_hit_target(page, links + ":nth-of-type(1)", "personal view")
        _assert_hit_target(page, links + ":nth-of-type(2)", "rename")
        assert page.locator(links).all_inner_texts() == ["Open personal view", "Rename"]
        assert page.locator(".fleet-detail-head details").count() == 0
        for index in range(2):
            assert page.locator(links).nth(index).bounding_box()["height"] >= MIN_TAP_PX - 0.5
        assert not _assert_no_page_overflow(page, "header-links", viewport["width"])
        # The header names the frame once less: no repeated heading.
        assert page.locator(".fleet-detail-head h2").count() == 0
    finally:
        context.close()


def test_the_header_links_work_without_script(new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    with _no_js_page(new_context, server.base_url(), "/fleet?frame=" + seed.owned_id,
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        with page.expect_navigation():
            page.locator(".fleet-detail-head a.row-action", has_text="Rename").click()
        assert page.url.endswith("/devices/%s/frame/name" % seed.owned_id)
        assert page.locator('input[name="name"]').input_value() == "Kitchen"


_TEXT_INSET = """() => {
  const bad = [];
  const blocks = [...document.querySelectorAll('.fleet-group')]
      .filter((b) => b.getClientRects().length > 0);
  for (const block of blocks) {
    const box = block.getBoundingClientRect();
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.textContent.trim() || !node.parentElement.checkVisibility()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const r of range.getClientRects()) {
        if (r.width === 0) continue;
        if (r.left < box.left + 16 - 0.5 || r.right > box.right - 16 + 0.5) {
          bad.push(node.textContent.trim().slice(0, 30) + ' ' + Math.round(r.left - box.left)
                   + '/' + Math.round(box.right - r.right));
        }
      }
    }
  }
  return {bad: bad, blocks: blocks.length};
}"""

_HEAD = """() => {
  const r = (s) => document.querySelector(s).getBoundingClientRect();
  const title = r('main h1'), head = r('.fleet-detail-head');
  const links = [...document.querySelectorAll('.fleet-detail-head a.row-action')]
      .map((a) => a.getBoundingClientRect());
  return {titleLeft: title.left, titleBottom: title.bottom, headLeft: head.left,
          headTop: head.top, links: links.map((l) => [l.left, l.top, l.right, l.bottom])};
}"""


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_a_frame_that_never_woke_keeps_its_state_text_inside_the_card_and_its_actions_under_the_title(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, scheme, path="/fleet?frame={owned}")
    where = "fleet-state/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        assert page.locator(".fleet-block--state .empty-state").count() >= 1
        for tab in ("state", "settings", "access"):
            if viewport is VIEWPORT_MIN_SUPPORTED:
                page.goto(page.url.split("&tab=")[0].split("#")[0] + "&tab=" + tab)
                page.locator("main").wait_for(state="visible")
            read = page.evaluate(_TEXT_INSET)
            assert read["blocks"] >= 1 and not read["bad"], (where, tab, read)
        head = page.evaluate(_HEAD)
        # The two actions start at the title's left edge, directly under it, side by side or
        # stacked, never on a floating row far below.
        assert abs(head["headLeft"] - head["titleLeft"]) <= 1, (where, head)
        assert 0 <= head["headTop"] - head["titleBottom"] <= 24, (where, head)
        assert len(head["links"]) == 2 and abs(head["links"][0][0] - head["titleLeft"]) <= 1, (
            where, head)
        assert head["links"][0][1] - head["headTop"] <= 1, (where, head)
        assert all(link[2] <= viewport["width"] for link in head["links"]), (where, head)
    finally:
        context.close()


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_versions_and_system_sections_keep_their_text_inside_their_cards(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(
        new_context, app_server_in_process, viewport, "en", "dark", path="/fleet?view=system")
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        read = page.evaluate(_TEXT_INSET)
        assert read["blocks"] >= 1 and not read["bad"], read
        page.goto(page.url.split("?")[0] + "?frame=" + seed.owned_id)
        page.locator(".fleet-block--device").wait_for(state="visible")
        read = page.evaluate(_TEXT_INSET)
        assert read["blocks"] >= 1 and not read["bad"], read
    finally:
        context.close()
