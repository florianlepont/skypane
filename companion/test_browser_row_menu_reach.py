"""Real-browser check that the action of a retired frame's page on the Fleet page is reachable.

A retired frame opens its own page whose one action is Re-activate. The button must be fully in
reach (a click on its centre and corners lands on it), at least 44px, and open its confirmation,
at desktop and phone width, in English and French and in both themes."""
import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login, _set_ui_theme

pytestmark = pytest.mark.browser

DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}
_ACTION = ".fleet-other a.fleet-action-button"
_SETTLED = animation_settle.SETTLED
# Per button: every sample point (centre and the four corners, inset 16px: the radius) is inside the
# viewport and the element found there is the option or one of its descendants.
_REACHABLE = """
items => items.map(el => {
  // Only the window scrolls: scrollIntoView would also scroll a clipping ancestor and hide the bug.
  const before = el.getBoundingClientRect();
  window.scrollBy(0, before.top + before.height / 2 - document.documentElement.clientHeight / 2);
  const r = el.getBoundingClientRect();
  const w = document.documentElement.clientWidth, h = document.documentElement.clientHeight;
  const points = [[r.left + r.width / 2, r.top + r.height / 2], [r.left + 16, r.top + 16],
    [r.right - 16, r.top + 16], [r.left + 16, r.bottom - 16], [r.right - 16, r.bottom - 16]];
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
    page.goto(server.base_url() + "/fleet?frame=" + seed.retired_id)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_retired_frames_action_is_reachable_and_opens_its_confirmation(
        new_context, app_server_in_process, viewport, lang, theme):
    context, page = _open(new_context, app_server_in_process, viewport, lang, theme)
    try:
        action = page.locator(_ACTION)
        action.scroll_into_view_if_needed()
        results = action.evaluate_all(_REACHABLE)
        assert len(results) == 1
        for result in results:
            assert all(result["hits"]), result
        box = action.bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44
        action.click()
        page.locator("dialog[open]").wait_for(state="visible")
    finally:
        context.close()
