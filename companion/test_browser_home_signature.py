"""Real-browser checks of Home's ambient motion: the status dot breathes while the page is
in use and stops under reduced motion; the title block, cards and pills take no extra room, so
nothing shifts while Home settles and ticks, and the page never scrolls sideways. The old ring
around the picture and the glint across it are gone with the approved layout."""
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    seed_state_dir,
)
from server import device_config, history_db

pytestmark = pytest.mark.browser

WAKE_S = 300

def _seed_checkin(minutes_ago):
    """A frame that checked in `minutes_ago` minutes ago on a 5 minute wake interval."""
    def seed(state_dir):
        seed_state_dir(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=True, quiet_hours_enabled=False, wake_interval_s=WAKE_S)
        ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        with history_db.open_db(state_dir) as conn:
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=4100, fw_version="1.0.0",
                boot_reason="wake", rssi="-60")
    return seed


def _open_home(new_context, base_url, viewport, lang="en", scheme="light", **context_args):
    context = new_context(viewport=viewport, color_scheme=scheme, **context_args)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.HOME_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.locator(".home-state__dot").wait_for(state="attached")
    return context, page


_ANIMATIONS = """() => {
  const name = (sel) => { const el = document.querySelector(sel);
    return el ? getComputedStyle(el).animationName : 'absent'; };
  return {dot: name('.home-state__dot')};
}"""


def test_dot_breathing_runs_on_home_and_stops_under_reduced_motion(new_context, make_app_server):
    """the status dot breathes on Home and not on another page; under reduced motion it is off"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE)
    try:
        assert page.evaluate(_ANIMATIONS) == {"dot": "skypane-dot-breathe"}
        page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        assert page.locator(".home-state__dot, .hero__ring, .hero__glass").count() == 0
    finally:
        context.close()
    context, page = _open_home(
        new_context, server.base_url(), VIEWPORT_PHONE, reduced_motion="reduce")
    try:
        assert page.evaluate(_ANIMATIONS) == {"dot": "none"}
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["390", "1280", "360"])
def test_home_shifts_no_layout_and_adds_no_scroll(new_context, make_app_server, viewport):
    """no layout shift while Home settles and ticks, and the page never scrolls sideways"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.add_init_script(
            "window.__shift = 0; new PerformanceObserver((list) => { for (const e of list.getEntries())"
            " if (!e.hadRecentInput) window.__shift += e.value; })"
            ".observe({type: 'layout-shift', buffered: true});")
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        page.wait_for_function(
            "() => document.getAnimations().every((a) => a.playState !== 'running' || (a.effect"
            " && a.effect.getComputedTiming().iterations === Infinity))", timeout=10000)
        before = page.evaluate(
            "() => { const r = document.querySelector('.home-state').getBoundingClientRect();"
            " return [r.left, r.top, r.width, r.height]; }")
        page.wait_for_timeout(2500)
        after = page.evaluate(
            "() => { const r = document.querySelector('.home-state').getBoundingClientRect();"
            " return [r.left, r.top, r.width, r.height]; }")
        assert before == after
        assert page.evaluate("() => window.__shift") < 0.001
        assert _assert_no_page_overflow(page, "home motion", viewport["width"]) in ("", None)
    finally:
        context.close()


def test_home_opens_without_a_shift_on_a_slow_processor(new_context, make_app_server):
    """a slow processor parses the page in several slices: the first frame still holds the whole
    page, so the frame button and the blocks beside it move by nothing after it"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.add_init_script(
            "window.__shift = 0; new PerformanceObserver((list) => { for (const e of list.getEntries())"
            " if (!e.hadRecentInput) window.__shift += e.value; })"
            ".observe({type: 'layout-shift', buffered: true});")
        context.new_cdp_session(page).send("Emulation.setCPUThrottlingRate", {"rate": 20})
        for _ in range(8):
            page.goto(server.base_url() + layout.HOME_ROUTE)
            page.wait_for_function("() => document.readyState === 'complete'", timeout=30000)
            page.wait_for_timeout(1200)
            assert page.evaluate("() => window.__shift") < 0.0005
    finally:
        context.close()
