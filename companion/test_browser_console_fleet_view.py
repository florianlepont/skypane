"""Real-browser checks of the Console Fleet view: the frame button's popover selects a frame
with a plain link, lists System and Add a frame and the owner of other people's frames, the
sections form one column on desktop and a phone's tab shows its own, nothing overflows at 360 and
1280px in either theme and language, and every row is a 52px target."""
import pytest

import fleet_console_support as fx
from frame_menu_support import ADD, BUTTON, FRAMES, SYSTEM, open_menu
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
_TILES = (
    "() => [...document.querySelectorAll('a.frame-row')].map(a => {"
    " const b = a.getBoundingClientRect(); return {w: b.width, h: b.height,"
    "  href: a.getAttribute('href')}; })")
_SETTLED = "() => document.readyState === 'complete'"


def _open(new_context, server, viewport, lang, scheme, path="/fleet"):
    seed = fx.seed_fleet(server.state_dir)
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
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        blocks = page.evaluate(_BLOCKS)
        # A phone's State tab shows State, Device and version and the pending and retired
        # frames; from 960px every section (State, Device and version, Settings, Access,
        # Other frames) is on the page.
        assert len(blocks) == (5 if viewport["width"] >= 960 else 3), where
        for upper, lower in zip(blocks, blocks[1:]):
            assert abs(lower["x"] - upper["x"]) < 2 and lower["y"] > upper["y"], (where, blocks)
        if viewport["width"] >= 960:
            title = page.locator("main h1").first.bounding_box()
            button = page.locator("details.frame-menu > summary").bounding_box()
            assert abs(blocks[0]["x"] - title["x"]) <= 2, (where, blocks[0], title)
            assert abs(blocks[0]["right"] - (button["x"] + button["width"])) <= 2, (
                where, blocks[0], button)
        for block in blocks:
            assert block["right"] <= viewport["width"] + 0.5, (where, block)
        open_menu(page)
        rows = page.evaluate(_TILES)
        assert len(rows) >= 4, where
        for row in rows:
            assert row["w"] >= 44 and row["h"] >= 52, (where, row)
        assert page.locator(SYSTEM).count() == 1 and page.locator(ADD).count() == 1
        assert page.locator(ADD).get_attribute("href") == "#dlg-add-frame"
    finally:
        context.close()


def test_a_row_is_a_plain_link_that_selects_the_frame(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "light")
    try:
        open_menu(page)
        target = "a.frame-row[href='/fleet?frame=%s']" % seed.owned_id
        page.locator(target).click()
        page.wait_for_url("**/fleet?frame=%s" % seed.owned_id)
        page.wait_for_function(_SETTLED, timeout=15000)
        open_menu(page)
        page.wait_for_function(
            "(sel) => document.querySelector(sel).getAttribute('aria-current') === 'true'",
            arg=target)
        assert page.locator(FRAMES + '[aria-current="true"]').count() == 1
        # State, Device and version, Settings, Access and Other frames.
        assert page.locator("section.fleet-block").count() == 5
        page.locator(SYSTEM).click()
        page.wait_for_url("**/fleet?view=system")
        page.wait_for_function(_SETTLED, timeout=15000)
        # The System view is one group per topic (flight data, sources, identification).
        assert page.locator("section.fleet-block").count() == 3
        assert page.locator(BUTTON + " .frame-menu__name").inner_text() == "System"
        open_menu(page)
        assert page.locator(SYSTEM + '[aria-current="true"]').count() == 1
        assert page.locator(FRAMES + '[aria-current="true"]').count() == 0
    finally:
        context.close()


def test_the_console_popover_names_other_peoples_frames_by_owner(
        new_context, app_server_in_process):
    context, page, seed = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "light")
    try:
        open_menu(page)
        notes = page.locator(FRAMES + " .frame-row__note").all_inner_texts()
        assert notes and all("@" in note for note in notes)
        assert page.locator(BUTTON + " .frame-menu__name").inner_text()
    finally:
        context.close()
