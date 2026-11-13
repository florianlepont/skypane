"""Real-browser checks of Home's signature animation: a thin ring around the picture shows
the share of the frame cycle already elapsed (the same data as "Next refresh in N min"), a soft
glass glint crosses the picture and the picture's glow and the status dot breathe. All of it
is content-neutral, takes no room, appears on Home only, is static under reduced motion and
the ring renders at its server-computed progress without scripts."""
from datetime import datetime, timedelta, timezone
import re

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    _no_js_page,
    seed_state_dir,
)
from server import device_config, history_db

pytestmark = pytest.mark.browser

WAKE_S = 300

RING = ".hero__ring"
BAR = ".hero__ring-bar"


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
    page.locator(RING).wait_for(state="attached")
    return context, page


def _progress(page):
    """The ring's drawn share of the cycle, read from the bar's dashoffset attribute."""
    offset = page.locator(BAR).get_attribute("stroke-dashoffset")
    return 1.0 - float(offset) / 100.0


@pytest.mark.parametrize("minutes_ago", [1, 2, 4])
def test_ring_progress_matches_the_next_update_data(new_context, make_app_server, minutes_ago):
    """the ring's drawn progress is the elapsed share of the wake interval, agrees with the
    countdown the page shows, and keeps advancing with the page's own ticking"""
    server = make_app_server(seed=_seed_checkin(minutes_ago), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        expected = minutes_ago * 60.0 / WAKE_S
        first = _progress(page)
        assert abs(first - expected) < 0.06, (first, expected)
        remaining_s = (1.0 - first) * WAKE_S
        # The number counts up on arrival; wait for it to settle on the countdown.
        page.wait_for_function(
            "(remaining) => { const m = /in (\\d+)([ms])/.exec(document.querySelector("
            "'.home-state__next [data-relative-countdown]').textContent);"
            " return m && Math.abs(Number(m[1]) * (m[2] === 'm' ? 60 : 1) - remaining) <= 61 }",
            arg=remaining_s, timeout=8000)
        page.wait_for_function(
            "(before) => 1 - Number(document.querySelector('%s').getAttribute('stroke-dashoffset'))"
            " / 100 > before + 0.004" % BAR, arg=first, timeout=8000)
    finally:
        context.close()


def test_ring_has_an_accessible_name_in_both_languages(new_context, make_app_server):
    """the ring is an image named by the next-update countdown, in English and French"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    for lang, pattern in (("en", r"^Frame cycle: next refresh in \d+"),
                          ("fr", r"^Cycle du cadre\s*: prochain rafraîchissement dans \d+")):
        context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE, lang=lang)
        try:
            ring = page.locator(RING)
            assert ring.get_attribute("role") == "img"
            assert re.search(pattern, ring.get_attribute("aria-label")), ring.get_attribute("aria-label")
        finally:
            context.close()


def test_ring_renders_at_its_server_progress_without_scripts(new_context, make_app_server):
    """with scripts blocked the ring is drawn from attributes alone at the server's progress,
    with its accessible name"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    with _no_js_page(new_context, server.base_url(), layout.HOME_ROUTE) as page:
        ring = page.locator(RING)
        assert ring.count() == 1
        assert re.search(r"next refresh in \d+", ring.get_attribute("aria-label"))
        assert abs(_progress(page) - 2 * 60.0 / WAKE_S) < 0.06
        assert page.locator(BAR).get_attribute("stroke-dasharray") == "100 100"


_ANIMATIONS = """
() => {
  const name = (sel, pseudo) => getComputedStyle(document.querySelector(sel), pseudo || null).animationName;
  return {
    glint: name('.hero__glass', '::after'),
    glow: name('.hero__picture', '::before'),
    dot: name('.home-state__dot')};
}
"""


def test_glint_and_breathing_run_on_home_and_stop_under_reduced_motion(new_context, make_app_server):
    """Home's glint, picture glow and dot breathing are animations; under reduced motion all
    are off and the ring still shows its progress"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE)
    try:
        assert page.evaluate(_ANIMATIONS) == {
            "glint": "skypane-glint", "glow": "skypane-picture-breathe",
            "dot": "skypane-dot-breathe"}
        page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        assert page.locator(RING + ", .hero__glass, .hero__picture").count() == 0
    finally:
        context.close()
    context, page = _open_home(
        new_context, server.base_url(), VIEWPORT_PHONE, reduced_motion="reduce")
    try:
        assert page.evaluate(_ANIMATIONS) == {"glint": "none", "glow": "none", "dot": "none"}
        assert 0 < _progress(page) < 1
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["390", "1280", "360"])
def test_signature_shifts_no_layout_and_adds_no_scroll(new_context, make_app_server, viewport):
    """the ring, glint and glow take no room: no layout shift while Home settles and ticks, and
    the page never scrolls sideways"""
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
            "() => { const r = document.querySelector('.hero__body').getBoundingClientRect();"
            " return [r.left, r.top, r.width, r.height]; }")
        page.wait_for_timeout(2500)
        after = page.evaluate(
            "() => { const r = document.querySelector('.hero__body').getBoundingClientRect();"
            " return [r.left, r.top, r.width, r.height]; }")
        assert before == after
        assert page.evaluate("() => window.__shift") < 0.001
        assert _assert_no_page_overflow(page, "home signature", viewport["width"]) in ("", None)
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


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ring_sits_just_outside_the_picture(new_context, make_app_server, scheme):
    """the ring is a frame of the picture's own box, 5px outside it, in either theme"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE, scheme=scheme)
    try:
        box = page.evaluate(
            "() => { const p = document.querySelector('.hero__picture').getBoundingClientRect();"
            " const r = document.querySelector('.hero__ring').getBoundingClientRect();"
            " return [p.left - r.left, p.top - r.top, r.right - p.right, r.bottom - p.bottom]; }")
        assert all(abs(v - 5) < 0.6 for v in box), box
    finally:
        context.close()


def test_a_refresh_that_starts_a_new_cycle_gives_the_ring_one_flourish(new_context, make_app_server):
    """when a refresh swaps in a ring whose cycle has just restarted, it plays one finite
    flourish; a swap that leaves the progress where it was plays none"""
    server = make_app_server(seed=_seed_checkin(4), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        # Let the ticker record the ring's progress first.
        page.wait_for_function(
            "() => Number(document.querySelector('%s').getAttribute('stroke-dashoffset')) < 25" % BAR)
        page.wait_for_timeout(1200)
        swap = ("() => { document.dispatchEvent(new CustomEvent('skypane-regions-swapped')); }")
        page.evaluate(swap)
        assert not page.locator(RING + ".is-ring-done").count()
        page.evaluate(
            "() => { const r = document.querySelector('%s');"
            " r.setAttribute('data-ring-next', new Date(Date.now() + 290000).toISOString()); }" % RING)
        page.evaluate(swap)
        page.locator(RING + ".is-ring-done").wait_for(state="attached")
        assert page.evaluate(
            "() => getComputedStyle(document.querySelector('%s')).animationName" % RING
        ) == "skypane-ring-pop"
        page.wait_for_function(
            "() => document.querySelector('%s').getAnimations().every((a) => a.effect"
            ".getComputedTiming().iterations !== Infinity)" % RING)
    finally:
        context.close()
