"""Real-browser proof that an administrator moving between the Console and My frame sees the
chrome stay put: the logo, the space switch and (on a phone) every tab bar cell sit at the same
position and size in both views, at 360, 390 and 1280 px, in both languages. The Console bar has
five cells and the personal bar six; both fill the bar at one height and one vertical position."""
import pytest

from nav_spaces_support import admin_page as _admin_page, own_frame_home as _own_frame_home
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}

_SETTLED = """() => {
  if (document.readyState !== 'complete') return false;
  if (document.getAnimations().some((a) => a.playState === 'running'
      && a.effect.getComputedTiming().iterations !== Infinity)) return false;
  const probe = [...document.querySelectorAll('.tab-bar__link, .space-switch__segment')]
    .find((e) => e.getClientRects().length > 0);
  if (!probe) return false;
  const b = probe.getBoundingClientRect();
  const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
  return !!hit && probe.contains(hit);
}"""

_ROUND = "Math.round(n * 100) / 100"

_DESKTOP_BOXES = """() => {
  const box = (el) => { const r = el.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height].map((n) => %s); };
  const visible = (sel) => [...document.querySelectorAll(sel)]
    .find((e) => e.getClientRects().length > 0);
  return {
    brand: box(visible('.dashboard-sidebar .brand')),
    logo: box(visible('.dashboard-sidebar .brand .logo-mark')),
    segments: [...document.querySelectorAll('.dashboard-sidebar .space-switch__segment')]
      .map(box),
    switchTrack: box(visible('.dashboard-sidebar .space-switch')),
  };
}""" % _ROUND

_PHONE_BOXES = """() => {
  const box = (el) => { const r = el.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height].map((n) => %s); };
  const visible = (sel) => [...document.querySelectorAll(sel)]
    .find((e) => e.getClientRects().length > 0);
  return {
    brand: box(visible('.site-header .brand')),
    logo: box(visible('.site-header .brand .logo-mark')),
    bar: box(document.querySelector('.tab-bar')),
    cells: [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')].map(box),
  };
}""" % _ROUND


def _read(page, script):
    page.wait_for_function(_SETTLED)
    return page.evaluate(script)


def _both_views(new_context, server, viewport, lang, script):
    context, page = _admin_page(new_context, server, _own_frame_home, viewport, lang)
    try:
        personal = _read(page, script)
        page.goto(server.base_url() + "/fleet")
        page.locator("main").wait_for(state="visible")
        console = _read(page, script)
        return console, personal
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_desktop_logo_and_space_switch_do_not_move_between_the_views(
        new_context, app_server_in_process, lang):
    console, personal = _both_views(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, lang, _DESKTOP_BOXES)
    assert console["brand"][3] == personal["brand"][3] == 44, (console, personal)
    assert console["brand"] == personal["brand"], (console, personal)
    assert console["logo"] == personal["logo"], (console, personal)
    assert console["switchTrack"] == personal["switchTrack"], (console, personal)
    assert console["segments"] == personal["segments"], (console, personal)
    assert len(console["segments"]) == 2
    assert console["segments"][0][2] == console["segments"][1][2], console


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_phone_header_and_tab_bar_cells_do_not_move_between_the_views(
        new_context, app_server_in_process, viewport, lang):
    console, personal = _both_views(
        new_context, app_server_in_process, viewport, lang, _PHONE_BOXES)
    assert console["brand"] == personal["brand"], (console, personal)
    assert console["logo"] == personal["logo"], (console, personal)
    assert console["bar"] == personal["bar"], (console, personal)
    assert len(console["cells"]) == 5 and len(personal["cells"]) == 6, (console, personal)
    for view in (console, personal):
        assert len({(cell[1], cell[3]) for cell in view["cells"]}) == 1, view
        assert abs(sum(cell[2] for cell in view["cells"]) - (view["bar"][2] - 6)) <= 2, view
