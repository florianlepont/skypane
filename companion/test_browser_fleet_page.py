"""Real-browser checks of the admin Fleet page's list of frames (live, pending and retired
rows) and the selected frame's header. No table and no sideways scroll at 360 and 1280px,
English and French, light and dark; one status dot per row with its accessible name, in the same
place on every row; wrapping frame names; 44px hit areas on the header's icon buttons and the
list's Add a frame; and the header links with and without script."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44
LONG_NAME = "Salon with an exceedingly long frame name " + "x" * 60

_ROW_FACTS = (
    "() => [...document.querySelectorAll('.fleet-list li.fleet-frame-row')]"
    ".filter(row => row.getClientRects().length > 0 && row.querySelector('.dot')).map(row => {"
    " const b = row.getBoundingClientRect(); const dot = row.querySelector('.dot');"
    " const value = row.querySelector('.row__value');"
    " const kids = [...row.querySelectorAll('.row__label, .row__detail')];"
    " return {dots: row.querySelectorAll('.dot').length, h: b.height,"
    "  label: row.querySelector('[role=img]').getAttribute('aria-label'),"
    "  dotX: Math.round(dot.getBoundingClientRect().left),"
    "  valueRight: value ? Math.round(value.getBoundingClientRect().right) : null,"
    "  family: getComputedStyle(kids[0]).fontFamily,"
    "  clipped: kids.some(k => k.getBoundingClientRect().right > b.right + 0.5)}; })")

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
def test_the_list_rows_fit_with_one_dot_per_row_in_the_same_place_and_no_table(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, scheme)
    where = "fleet/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        assert page.locator("table").count() == 0
        rows = page.evaluate(_ROW_FACTS)
        assert len(rows) == 4
        for row in rows:
            assert row["dots"] == 1 and row["label"], (where, row)
            assert row["h"] >= MIN_TAP_PX and not row["clipped"], (where, row)
            assert "mono" not in row["family"].lower(), (where, row)
            if lang == "en":
                assert row["label"] in _EN_WORDS, (where, row)
        # The status dot and the last-seen word stand in the same place on every row.
        assert len({row["dotX"] for row in rows}) == 1, (where, rows)
        assert len({row["valueRight"] for row in rows if row["valueRight"]}) <= 1, (where, rows)
        _assert_hit_target(page, ".fleet-add-button", where)
        assert page.locator(
            "main h1:visible").evaluate("e => !getComputedStyle(e).fontFamily.includes('mono')")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_long_frame_name_never_overflows_and_the_header_buttons_stay_in_view_at_360(
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
        links = page.locator(".fleet-head a.fleet-icon-button")
        links.first.wait_for(state="visible")
        assert links.count() == 2
        for index in range(2):
            box = links.nth(index).bounding_box()
            assert box["height"] >= MIN_TAP_PX - 0.5 and box["x"] >= -0.5
            assert box["x"] + box["width"] <= 360 + 0.5
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_header_offers_two_44px_icon_buttons_named_for_assistive_technology(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(
        new_context, app_server_in_process, viewport, path="/fleet?frame={owned}")
    try:
        links = ".fleet-head a.fleet-icon-button"
        _assert_hit_target(page, links + ":nth-of-type(1)", "personal view")
        _assert_hit_target(page, links + ":nth-of-type(2)", "rename")
        assert page.locator(links).evaluate_all("els => els.map(e => e.getAttribute('aria-label'))") == [
            "Open the personal view of Kitchen", "Rename Kitchen"]
        assert page.locator(".fleet-head details").count() == 0
        for index in range(2):
            box = page.locator(links).nth(index).bounding_box()
            assert box["height"] >= MIN_TAP_PX - 0.5 and box["width"] >= MIN_TAP_PX - 0.5
        assert not _assert_no_page_overflow(page, "header-links", viewport["width"])
        assert page.locator("main h1").count() == 1
        assert page.locator("main h1").inner_text() == "Kitchen"
    finally:
        context.close()


def test_the_header_links_work_without_script(new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    with _no_js_page(new_context, server.base_url(), "/fleet?frame=" + seed.owned_id,
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.locator(".fleet-head a.fleet-icon-button[title=Rename]").click()
        assert page.url.endswith("#dlg-rename-" + seed.owned_id.replace("_", "-"))
        assert page.locator('dialog:target input[name="name"]').input_value() == "Kitchen"


_TEXT_INSET = """(selector) => {
  const bad = [];
  const blocks = [...document.querySelectorAll(selector)]
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
  const title = r('main h1'), state = r('.fleet-head__state');
  const links = [...document.querySelectorAll('.fleet-head a.fleet-icon-button')]
      .map((a) => a.getBoundingClientRect());
  return {titleLeft: title.left, titleTop: title.top, titleBottom: title.bottom,
          stateTop: state.top, stateLeft: state.left,
          links: links.map((l) => [l.left, l.top, l.right, l.bottom])};
}"""


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_a_frame_that_never_woke_keeps_its_state_text_inside_the_card_and_its_buttons_beside_the_title(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, scheme, path="/fleet?frame={owned}")
    where = "fleet-state/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        # The State section is three tiles whose text stays inside them; the other sections'
        # groups keep theirs inside too.
        assert page.locator(".fleet-tile").count() == 3
        read = page.evaluate(_TEXT_INSET, ".fleet-group, .fleet-tile")
        assert read["blocks"] >= 5 and not read["bad"], (where, read)
        head = page.evaluate(_HEAD)
        # The title, then the state line directly under it, both at the same left edge; the two
        # icon buttons side by side at the right of the title row, inside the viewport.
        assert abs(head["stateLeft"] - head["titleLeft"]) <= 1, (where, head)
        assert 0 <= head["stateTop"] - head["titleBottom"] <= 16, (where, head)
        assert len(head["links"]) == 2 and head["links"][0][2] <= head["links"][1][0] + 1, (
            where, head)
        assert head["links"][0][0] > head["titleLeft"], (where, head)
        assert abs(head["links"][0][1] - head["titleTop"]) <= 8, (where, head)
        assert all(link[2] <= viewport["width"] for link in head["links"]), (where, head)
    finally:
        context.close()


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_versions_page_and_system_view_keep_their_text_inside_their_cards(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(
        new_context, app_server_in_process, viewport, "en", "dark", path="/fleet?view=system")
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        read = page.evaluate(_TEXT_INSET, ".fleet-group")
        assert read["blocks"] >= 1 and not read["bad"], read
        for view in ("versions", "health"):
            page.goto(page.url.split("?")[0] + "?frame=%s&view=%s" % (seed.owned_id, view))
            page.locator(".fleet-back").wait_for(state="visible")
            read = page.evaluate(
                _TEXT_INSET, ".fleet-group, .update-cta, .update-hist__list, .update-hist__empty")
            assert read["blocks"] >= 1 and not read["bad"], (view, read)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_retired_header_detail_takes_its_own_line_without_a_dangling_dot_on_a_phone(
        new_context, app_server_in_process, lang):
    viewport = {"width": 320, "height": 800}
    context, page, seed = _open(new_context, app_server_in_process, viewport, lang)
    try:
        page.goto(app_server_in_process.base_url() + "/fleet?frame=" + seed.retired_id)
        page.locator(".fleet-head__seen").wait_for(state="visible")
        facts = page.evaluate(
            "() => { const s = document.querySelector('.fleet-head__state > span');"
            " const d = document.querySelector('.fleet-head__seen');"
            " const dot = d.querySelector('.fleet-head__dot');"
            " return {dot: getComputedStyle(dot).display,"
            "  below: d.getBoundingClientRect().top >= s.getBoundingClientRect().bottom - 1,"
            "  left: Math.abs(d.getBoundingClientRect().left"
            "    - document.querySelector('.fleet-head__state').getBoundingClientRect().left) < 1}; }")
        assert facts == {"dot": "none", "below": True, "left": True}, facts
    finally:
        context.close()
