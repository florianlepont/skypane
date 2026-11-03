"""Real-browser checks of the admin Fleet list: no table and no sideways scroll
at 360 and 1280px, English and French, light and dark; one status dot per row
with its accessible name; wrapping frame names; 44px hit areas on the header
action and the row menus; and the row menu with and without script."""
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
    "() => [...document.querySelectorAll('li.entity-row')].map(row => {"
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
    "Not seen yet", "No contact", "Overdue", "Low battery", "Resting", "Up to date",
    "Waiting for pairing", "Retired"}


def _open(new_context, server, viewport, lang="en", scheme="light", path="/fleet"):
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_list_fits_with_one_dot_per_row_and_no_table(
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
            assert not row["clipped"], (where, row)
            assert "mono" not in row["family"].lower(), (where, row)
            assert all("mono" not in family.lower() for family in row["metaFamily"])
            if lang == "en":
                assert row["label"] in _EN_WORDS, (where, row)
        page.locator("details.fleet-retired > summary").click()
        assert page.locator("details.fleet-retired li.entity-row").count() == 1
        assert not _assert_no_page_overflow(page, where + "/retired", viewport["width"])
        _assert_hit_target(page, "a.page-header__action", where)
        assert page.locator(
            "main h1").evaluate("e => !getComputedStyle(e).fontFamily.includes('mono')")
        header = page.locator(".page-header")
        action = page.locator("a.page-header__action").bounding_box()
        title = page.locator(".page-header h1").bounding_box()
        assert abs((action["y"] + action["height"] / 2)
                   - (title["y"] + title["height"] / 2)) < 30, where
        assert header.bounding_box()["height"] < 220, where
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_long_frame_name_wraps_inside_the_row_at_360(
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
        page.goto(server.base_url() + "/fleet")
        page.locator("main").wait_for(state="visible")
        assert not _assert_no_page_overflow(page, "long-name", 360)
        rows = page.evaluate(_ROW_FACTS)
        long_row = next(row for row in rows if row["text"] == LONG_NAME)
        assert not long_row["clipped"]
        title = page.locator("a.entity-row__title", has_text=LONG_NAME).bounding_box()
        assert title["height"] > 30
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_row_menu_opens_closes_with_escape_and_has_44px_items(
        new_context, app_server_in_process, viewport):
    context, page, seed = _open(new_context, app_server_in_process, viewport)
    try:
        toggle = "li.entity-row >> nth=0 >> .row-menu__toggle"
        _assert_hit_target(page, "li.entity-row:first-child .row-menu__toggle", "toggle")
        page.locator(toggle).click()
        assert page.locator("li.entity-row >> nth=0 >> details.row-menu[open]").count() == 1
        items = page.locator("li.entity-row >> nth=0 >> .row-menu__item")
        assert items.all_inner_texts() == [
            "Health", "Device", "Open personal view", "Manage access", "Reassign",
            "Retire"]
        for index in range(items.count()):
            assert items.nth(index).bounding_box()["height"] >= MIN_TAP_PX
        assert not _assert_no_page_overflow(page, "menu-open", viewport["width"])
        page.keyboard.press("Escape")
        assert page.locator("details.row-menu[open]").count() == 0
        page.locator(toggle).click()
        page.mouse.click(5, 5)
        assert page.locator("details.row-menu[open]").count() == 0
        assert seed.owned_id
    finally:
        context.close()


def test_the_row_menu_toggles_without_script(new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    with _no_js_page(new_context, server.base_url(), "/fleet",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        first = page.locator("li.entity-row >> nth=0 >> details.row-menu")
        first.locator("summary").click()
        assert first.get_attribute("open") is not None
        assert first.locator(".row-menu__item").first.bounding_box()["height"] >= MIN_TAP_PX
        first.locator("summary").click()
        assert first.get_attribute("open") is None
