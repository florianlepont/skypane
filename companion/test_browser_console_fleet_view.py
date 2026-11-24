"""Real-browser checks of the Console Fleet view: the list of frames and the frame switch, the
sections of one frame in one column on desktop and a phone's tab showing its own, nothing
overflowing at 360 and 1280px in either theme and language, 44px targets, and a fleet of 30
frames that stays usable (a bounded switch, a search that filters the list)."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login,
    _set_ui_theme)

pytestmark = pytest.mark.browser

_BLOCKS = (
    "() => [...document.querySelectorAll('section.fleet-block')]"
    ".filter(s => s.getClientRects().length > 0).map(s => {"
    " const b = s.getBoundingClientRect();"
    " return {title: s.querySelector('h2.section-label').textContent, x: b.left, y: b.top,"
    "  w: b.width, right: b.right}; })")
_ROWS = (
    "() => [...document.querySelectorAll('.fleet-list li.fleet-frame-row > a')]"
    ".filter(a => a.getClientRects().length > 0).map(a => {"
    " const b = a.getBoundingClientRect(); return {w: b.width, h: b.height,"
    "  href: a.getAttribute('href')}; })")
_CHIPS = (
    "() => [...document.querySelectorAll('.fleet-switch .fleet-chip')].map(a => {"
    " const b = a.getBoundingClientRect(); const c = getComputedStyle(a);"
    " return {y: b.top, h: b.height, w: b.width, justify: c.justifyContent,"
    "  align: c.textAlign, href: a.getAttribute('href'),"
    "  current: a.getAttribute('aria-current')}; })")
_VISIBLE = "(sel) => [...document.querySelectorAll(sel)].some(e => e.getClientRects().length > 0)"
_SETTLED = "() => document.readyState === 'complete'"


def _open(new_context, server, viewport, lang, scheme, path="/fleet", extra=0):
    seed = fx.seed_fleet(server.state_dir)
    if extra:
        fx.add_frames(server.state_dir, extra, seed.owner_id)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path.replace("{owned}", seed.owned_id))
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, scheme)
    return context, page, seed


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_blocks_lay_out_and_nothing_overflows(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, scheme,
        "/fleet?frame={owned}")
    where = "console-fleet/%d/%s/%s" % (viewport["width"], lang, scheme)
    wide = viewport["width"] >= 960
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        blocks = page.evaluate(_BLOCKS)
        # The three sections (State, Settings, Access) are stacked on the page at every width.
        assert len(blocks) == 3, where
        for upper, lower in zip(blocks, blocks[1:]):
            assert abs(lower["x"] - upper["x"]) < 2 and lower["y"] > upper["y"], (where, blocks)
        for block in blocks:
            assert block["right"] <= viewport["width"] + 0.5, (where, block)
        # The list is a column beside the frame on desktop and gone on a phone, where the
        # switch stands in; no frame button in the top bar either way.
        assert page.evaluate(_VISIBLE, ".fleet-list") is wide, where
        assert page.evaluate(_VISIBLE, ".fleet-switch") is (not wide), where
        assert page.locator("details.frame-menu").count() == 0
        title = page.locator("main h1").first.bounding_box()
        assert abs(blocks[0]["x"] - title["x"]) <= 2, (where, blocks[0], title)
        if wide:
            rows = page.evaluate(_ROWS)
            assert len(rows) >= 4, where
            for row in rows:
                assert row["h"] >= 44, (where, row)
            assert rows[0]["w"] < blocks[0]["x"], (where, rows[0], blocks[0])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_switch_is_one_line_of_centred_44px_chips_starting_with_all_frames(
        new_context, app_server_in_process, lang):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, lang, "light",
        "/fleet?frame={owned}", extra=12)
    try:
        chips = page.evaluate(_CHIPS)
        assert chips[0]["href"] == "/fleet"
        # All frames, the frame in view, then at most seven more: a bounded row.
        assert len(chips) == 9
        assert chips[1]["href"] == "/fleet?frame=%s" % seed.owned_id
        assert [c["current"] for c in chips].count("page") == 1 and chips[1]["current"] == "page"
        assert len({round(c["y"]) for c in chips}) == 1
        for chip in chips:
            assert chip["h"] >= 44 and chip["justify"] == "center" and chip["align"] == "center"
        # One line that scrolls sideways when the chips do not fit, never the page.
        row = page.evaluate(
            "() => { const n = document.querySelector('.fleet-switch');"
            " return {sw: n.scrollWidth, cw: n.clientWidth,"
            " overflow: getComputedStyle(n).overflowX, wrap: getComputedStyle(n).flexWrap}; }")
        assert row["sw"] > row["cw"] and row["overflow"] == "auto" and row["wrap"] == "nowrap"
        assert not _assert_no_page_overflow(page, "switch/" + lang, 360)
        page.locator(".fleet-switch .fleet-chip").nth(2).click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "/fleet?frame=" in page.url and seed.owned_id not in page.url
    finally:
        context.close()


def test_the_phone_shows_the_list_or_a_frame_and_the_desktop_both(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, "en", "light")
    try:
        # No frame chosen: the list, and no frame page or chips.
        assert page.evaluate(_VISIBLE, ".fleet-list")
        assert not page.evaluate(_VISIBLE, "section.fleet-block")
        assert not page.evaluate(_VISIBLE, ".fleet-switch")
        assert page.locator("main h1:visible").inner_text() == "Frames"
        page.locator(".fleet-list li.fleet-frame-row > a[href='/fleet?frame=%s']" % seed.owned_id).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.owned_id)
        assert not page.evaluate(_VISIBLE, ".fleet-list")
        assert page.evaluate(_VISIBLE, ".fleet-switch")
        assert page.locator("main h1:visible").inner_text().startswith("Kitchen")
        page.locator(".fleet-switch .fleet-chip--all").click()
        page.wait_for_url("**/fleet")
        assert page.evaluate(_VISIBLE, ".fleet-list")
    finally:
        context.close()


def test_a_list_row_is_a_plain_link_that_selects_the_frame_on_desktop(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "light")
    try:
        # No frame chosen: the list and the first frame side by side.
        assert page.evaluate(_VISIBLE, ".fleet-list")
        assert page.locator("section.fleet-block").count() == 3
        assert not page.evaluate(_VISIBLE, ".fleet-switch")
        assert page.locator("main h1:visible").count() == 1
        assert page.locator("main h1:visible").inner_text() in ("Orly frame", "Kitchen")
        target = ".fleet-list li.fleet-frame-row > a[href='/fleet?frame=%s']" % seed.owned_id
        page.locator(target).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.owned_id)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(".fleet-list [aria-current='page']").count() == 1
        assert page.locator(target).get_attribute("aria-current") == "page"
        assert page.locator("section.fleet-block").count() == 3
        assert page.locator(".fleet-list a[href='/fleet?view=system']").count() == 0
        page.locator("nav.sidebar-nav a[href='/fleet?view=system']").click()
        page.wait_for_url("**/fleet?view=system")
        page.wait_for_function(_SETTLED, timeout=15000)
        # The System view is one group per topic (flight data, sources, identification and the
        # two route topics).
        assert page.locator("section.fleet-block").count() == 5
        assert page.locator("main h1").inner_text() == "System"
        assert page.locator(".fleet-list [aria-current='page']").count() == 0
        current = page.locator("nav.sidebar-nav a[aria-current='page']")
        assert current.count() == 1 and current.get_attribute("href") == "/fleet?view=system"
    finally:
        context.close()


def test_a_retired_and_a_pending_frame_open_their_own_page_from_the_list(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "light")
    try:
        page.locator(
            ".fleet-list a[href='/fleet?frame=%s']" % seed.retired_id).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.retired_id)
        assert page.locator("main h1").inner_text().startswith("Attic")
        assert page.locator("section.fleet-block").count() == 0
        page.locator(".fleet-other a.fleet-action-button").click()
        page.locator("dialog[open] .btn--danger").wait_for(state="visible")
        page.keyboard.press("Escape")
        page.locator(
            ".fleet-list a[href='/fleet?frame=%s']" % seed.pending_id).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.pending_id)
        assert page.locator(".fleet-other a.fleet-action-button").inner_text() == "Pair frame"
        page.locator(
            ".fleet-list a[href='/fleet?frame=%s']" % seed.owned_id).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.owned_id)
        main = page.locator(".fleet-split__main").inner_text()
        assert "Attic" not in main and "Retired" not in main
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_thirty_frames_stay_usable_and_the_search_filters_the_list(
        new_context, app_server_in_process, viewport, lang):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, lang, "light", extra=26)
    where = "thirty/%d/%s" % (viewport["width"], lang)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        rows = page.evaluate(_ROWS)
        assert len(rows) >= 30, where
        for row in rows:
            assert row["h"] >= 44 and row["w"] > 0, (where, row)
        search = page.locator("#fleet-frame-search")
        assert search.is_visible()
        assert (search.get_attribute("placeholder") or "").count("30") == 1
        search.fill("frame 07")
        page.wait_for_function(
            "() => [...document.querySelectorAll('.fleet-list li.fleet-frame-row')]"
            ".filter(l => !l.hidden && l.dataset.filterText).length === 1")
        # A group with no visible row is hidden with it, and nothing matching shows the note.
        search.fill("zzzz")
        page.locator("[data-filter-empty]").wait_for(state="visible")
        assert not page.evaluate(_VISIBLE, ".fleet-list-group li")
    finally:
        context.close()


_COLUMNS = (
    "() => { const box = s => { const e = document.querySelector(s); if (!e) return null;"
    " const b = e.getBoundingClientRect();"
    " return {x: b.left, y: b.top, w: b.width, h: b.height, r: b.right}; };"
    " return {side: box('.dashboard-sidebar'), list: box('.fleet-split__list'),"
    "  head: box('.fleet-list__head'), body: box('.fleet-list__body'),"
    "  main: box('.fleet-split__main'), title: box('.fleet-head__title'),"
    "  vh: window.innerHeight, vw: document.documentElement.clientWidth}; }")


@pytest.mark.parametrize("viewport", [
    {"width": 1200, "height": 800}, {"width": 1440, "height": 900},
    {"width": 1920, "height": 1000}], ids=["1200", "1440", "1920"])
def test_the_list_is_a_full_height_column_attached_to_the_sidebar(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(
        new_context, app_server_in_process, viewport, "en", "light",
        "/fleet?frame={owned}", extra=28)
    where = "fleet-column/%d" % viewport["width"]
    try:
        box = page.evaluate(_COLUMNS)
        side, listing = box["side"], box["list"]
        assert abs(listing["w"] - 350) <= 1, (where, listing)
        # Against the sidebar: same top, same height, a small gap and not the page's centred column.
        assert 0 <= listing["x"] - side["r"] <= 24, (where, side, listing)
        assert abs(listing["y"] - side["y"]) <= 1 and abs(listing["h"] - side["h"]) <= 1, (
            where, side, listing)
        assert abs(listing["h"] - (box["vh"] - 2 * side["y"])) <= 2, (where, listing, box["vh"])
        # The selected frame fills the rest: it starts after the list and its title is inside it.
        assert box["main"]["x"] >= listing["r"] - 1, (where, box)
        assert box["title"]["x"] >= box["main"]["x"] and box["title"]["r"] <= box["vw"], where
        assert box["main"]["r"] <= box["vw"] + 0.5, (where, box)
        assert page.locator("main h1:visible").count() == 1
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        # A fixed header (title, Add, search) above a body that scrolls on its own.
        assert box["head"]["y"] - listing["y"] <= 2 and box["head"]["h"] >= 100, (where, box)
        assert page.evaluate(
            "() => { const b = document.querySelector('.fleet-list__body');"
            " return b.scrollHeight > b.clientHeight && getComputedStyle(b).overflowY === 'auto'; }")
        page.evaluate("() => { document.querySelector('.fleet-list__body').scrollTop = 400; }")
        # The frame column scrolls the page; the list stays where the sidebar is.
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        after = page.evaluate(_COLUMNS)
        assert abs(after["list"]["y"] - listing["y"]) <= 1, (where, after["list"], listing)
        assert abs(after["head"]["y"] - box["head"]["y"]) <= 1, (where, after["head"], box["head"])
        assert abs(after["side"]["y"] - side["y"]) <= 1, (where, after["side"], side)
        for control in (".fleet-add-button", "#fleet-frame-search"):
            top = page.locator(control).bounding_box()
            assert listing["y"] <= top["y"] and top["y"] + top["height"] <= listing["y"] + listing["h"], (
                where, control, top)
    finally:
        context.close()


def test_below_1200px_the_list_is_not_a_column_beside_the_frame(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, {"width": 1199, "height": 800}, "en", "light",
        "/fleet?frame={owned}", extra=4)
    try:
        assert not page.evaluate(_VISIBLE, ".fleet-list")
        assert page.evaluate(_VISIBLE, ".fleet-switch")
        assert page.locator("main h1:visible").count() == 1
    finally:
        context.close()


def test_the_unsaved_changes_bar_docks_under_the_frame_column_clear_of_the_list(
        new_context, app_server_in_process):
    context, page, _seed = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "light",
        "/fleet?frame={owned}", extra=8)
    try:
        page.locator("#wake-interval-m").fill("2")
        bar = page.locator(".dirty-bar")
        bar.wait_for(state="visible")
        # Let the bar's own entrance end before it is measured.
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.dirty-bar')).opacity === '1'")
        box = bar.bounding_box()
        listing = page.locator(".fleet-split__list").bounding_box()
        assert box["x"] >= listing["x"] + listing["width"], (box, listing)
        assert box["x"] + box["width"] <= VIEWPORT_DESKTOP["width"], box
    finally:
        context.close()


_SELECTED_ROW = """() => {
  const body = document.querySelector('.fleet-list__body');
  const row = document.querySelector('.fleet-list__body .fleet-frame-row.is-selected');
  const b = body.getBoundingClientRect(), r = row.getBoundingClientRect();
  return {top: r.top - b.top, bottom: b.bottom - r.bottom, scrolled: body.scrollTop,
          page: window.scrollY, overflow: body.scrollHeight - body.clientHeight}; }"""


def test_the_selected_frame_is_scrolled_into_view_in_a_long_list(
        new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    ids = fx.add_frames(server.state_dir, 30, seed.owner_id)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme="light")
    page = context.new_page()
    _login(page, server.base_url())
    try:
        for frame_id in (ids[0], ids[-1]):
            page.goto(server.base_url() + "/fleet?frame=" + frame_id)
            page.locator("main").wait_for(state="visible")
            page.wait_for_function(_SETTLED, timeout=15000)
            found = page.evaluate(_SELECTED_ROW)
            assert found["overflow"] > 0, found
            assert found["top"] >= 0 and found["bottom"] >= 0, found
            assert found["page"] == 0, found
        assert found["scrolled"] > 0, found
    finally:
        context.close()
