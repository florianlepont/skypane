"""Real-browser check that the last row's actions menu on the Fleet page is reachable.

The Other frames list ends with a retired frame whose menu offers Re-activate. Opening that menu
must show every option fully (no ancestor clips the popover) and a click on each option's centre
and corners must land on the option, at desktop and phone width, in English and French and in
both themes."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login, _set_ui_theme

pytestmark = pytest.mark.browser

DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}
_LAST_ROW = ".fleet-block--others li.entity-row:last-child"
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
# Per option: every sample point (centre and the four corners, inset 2px) is inside the
# viewport and the element found there is the option or one of its descendants.
_REACHABLE = """
items => items.map(el => {
  // Only the window scrolls: scrollIntoView would also scroll a clipping ancestor and hide the bug.
  const before = el.getBoundingClientRect();
  window.scrollBy(0, before.top + before.height / 2 - document.documentElement.clientHeight / 2);
  const r = el.getBoundingClientRect();
  const w = document.documentElement.clientWidth, h = document.documentElement.clientHeight;
  const points = [[r.left + r.width / 2, r.top + r.height / 2], [r.left + 2, r.top + 2],
    [r.right - 2, r.top + 2], [r.left + 2, r.bottom - 2], [r.right - 2, r.bottom - 2]];
  const hits = points.map(([x, y]) => {
    if (x < 0 || y < 0 || x > w || y > h) return false;
    const hit = document.elementFromPoint(x, y);
    return !!hit && (hit === el || el.contains(hit));
  });
  return {text: el.textContent.trim(), hits: hits};
})
"""


def _open(new_context, server, viewport, lang, theme):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=state&frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_last_other_frame_menu_options_are_reachable(
        new_context, app_server_in_process, viewport, lang, theme):
    context, page = _open(new_context, app_server_in_process, viewport, lang, theme)
    try:
        row = page.locator(_LAST_ROW)
        row.scroll_into_view_if_needed()
        row.locator("summary.row-menu__toggle").click()
        panel = row.locator(".row-menu__panel")
        panel.wait_for(state="visible")
        items = row.locator("a.row-menu__item")
        assert items.count() >= 1
        results = items.evaluate_all(_REACHABLE)
        for result in results:
            assert all(result["hits"]), result
    finally:
        context.close()
