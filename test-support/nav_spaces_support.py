"""Shared browser helpers for the navigation tests: signed-in administrator and
user pages in a chosen viewport, language and theme, and the equal-cells check
of the phone tab bar (each cell follows its label and the cells together fill the bar)."""
import fleet_console_support as fx
from locations_page_support import open_locations_page
from companion import auth
from companion.test_browser_ux_helpers import _assert_no_page_overflow, _login, _set_ui_theme

MIN_TAP_PX = 44

_CELLS = (
    "() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')]"
    ".map(e => { const b = e.getBoundingClientRect();"
    " return {w: b.width, h: b.height, r: b.right}; })")
_BAR_WIDTH = "() => document.querySelector('.tab-bar').getBoundingClientRect().width"
_LABELS = (
    "() => [...document.querySelectorAll('.tab-bar__label')]"
    ".map(e => ({text: e.textContent, sw: e.scrollWidth, cw: e.clientWidth,"
    " slack: e.closest('.tab-bar__pill').getBoundingClientRect().width"
    " - (() => { const r = document.createRange(); r.selectNodeContents(e);"
    " return r.getBoundingClientRect().width; })(),"
    " lines: new Set([...(() => { const r = document.createRange();"
    " r.selectNodeContents(e); return [...r.getClientRects()]; })()]"
    ".map(x => Math.round(x.top))).size}))")


def context_for(new_context, server, viewport, lang="en", scheme="light"):
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    return context


def admin_page(new_context, server, path, viewport, lang="en", scheme="light"):
    seed = fx.seed_fleet(server.state_dir)
    if callable(path):
        path = path(seed)
    context = context_for(new_context, server, viewport, lang, scheme)
    page = context.new_page()
    _login(page, server.base_url())
    if path == "/locations":
        open_locations_page(page, server.base_url())
    else:
        page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page


def user_page(new_context, server, viewport, lang="en", scheme="light"):
    seed = fx.seed_fleet(server.state_dir)
    name, value = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL).split("=", 1)
    context = context_for(new_context, server, viewport, lang, scheme)
    context.add_cookies([{
        "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
        "sameSite": "Strict"}])
    page = context.new_page()
    page.goto("%s/devices/%s/" % (server.base_url(), seed.owned_id))
    page.locator("main").wait_for(state="visible")
    return context, page


def assert_bar(page, expected_cells, where):
    cells = page.evaluate(_CELLS)
    assert len(cells) == expected_cells, (where, cells)
    if len(cells) > 1:
        # The bar's border (2px) and padding (4px) are the only width the cells leave over.
        assert abs(sum(cell["w"] for cell in cells) - (page.evaluate(_BAR_WIDTH) - 6)) <= 2, (
            where, cells)
    for cell in cells:
        assert cell["h"] >= MIN_TAP_PX and cell["w"] >= MIN_TAP_PX, (where, cells)
        assert cell["r"] <= page.viewport_size["width"] + 0.5, (where, cells)
    for label in page.evaluate(_LABELS):
        assert label["sw"] <= label["cw"], (where, label)
        assert label["lines"] <= 1, (where, label)
        # The text keeps at least 3px on each side inside its pill, the switch cell's
        # outline included, so no label touches an edge.
        assert label["slack"] >= 6, (where, label)
    assert not _assert_no_page_overflow(page, where, page.viewport_size["width"])


def own_frame_home(seed):
    return "/devices/%s/" % seed.owned_id


