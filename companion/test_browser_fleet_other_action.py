"""Real-browser check that the action button of a retired frame's page (Re-activate) and of a
pending frame's page (Pair frame) keeps the same right margin as the text keeps on its left."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login
from server import device_config

pytestmark = pytest.mark.browser

VIEWPORTS = {"phone": {"width": 390, "height": 844}, "desktop": {"width": 1440, "height": 900}}
_GAPS = (
    "() => { const row = document.querySelector('.fleet-other .group > .row');"
    " const btn = row.querySelector('.fleet-action-button');"
    " const main = row.querySelector('.row__main');"
    " const r = row.getBoundingClientRect(), b = btn.getBoundingClientRect();"
    " const m = main.getBoundingClientRect();"
    " return {right: r.right - b.right,"
    "  left: m.left + parseFloat(getComputedStyle(main).paddingLeft) - r.left,"
    "  pad: parseFloat(getComputedStyle(main).paddingLeft), width: b.width}; }")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", sorted(VIEWPORTS))
@pytest.mark.parametrize("which", ["retired_id", "pending_id"])
def test_other_frame_action_keeps_right_margin(
        app_server_in_process, new_context, which, viewport, lang):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    context = new_context(viewport=VIEWPORTS[viewport])
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet?frame=" + getattr(seed, which))
        page.locator(".fleet-other .fleet-action-button").wait_for(state="visible")
        gaps = page.evaluate(_GAPS)
        assert gaps["width"] > 0
        assert gaps["right"] > 0
        assert abs(gaps["right"] - gaps["left"]) <= 1, gaps
    finally:
        context.close()
