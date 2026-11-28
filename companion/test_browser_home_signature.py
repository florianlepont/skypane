# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of Home's ambient motion: the status dot breathes while the page is
in use and stops under reduced motion; a thin ring around the frame picture fills as the time to
the next update runs out (the same instant the title block's sentence reads), ticks without a
reload, stays static under reduced motion, starts over when a refresh swaps in a new cycle and
is absent while the frame rests or has lost contact; the title block, cards and pills take no
extra room, so nothing shifts while Home settles and ticks, and the page never scrolls
sideways."""
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
RING = ".home-flight__picture > .home-ring"
BAR = RING + " .home-ring__bar"


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
        assert page.locator(".home-state__dot, .home-ring").count() == 0
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


def _progress(page):
    """The ring's drawn share of the cycle, read from the bar's dashoffset attribute."""
    return 1.0 - float(page.locator(BAR).get_attribute("stroke-dashoffset")) / 100.0


def _open_home_on_a_fake_clock(new_context, server, **context_args):
    """Home opened with the browser clock installed at the real time, so a test can move it."""
    context = new_context(viewport=VIEWPORT_PHONE, **context_args)
    page = context.new_page()
    _login(page, server.base_url())
    page.clock.install(time=datetime.now(timezone.utc))
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.locator(RING).wait_for(state="attached")
    return context, page


@pytest.mark.parametrize("minutes_ago", [1, 2, 4])
def test_ring_starts_at_the_elapsed_share_of_the_cycle(new_context, make_app_server, minutes_ago):
    """the ring's drawn progress is the elapsed share of the wake interval"""
    server = make_app_server(seed=_seed_checkin(minutes_ago), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        assert abs(_progress(page) - minutes_ago * 60.0 / WAKE_S) < 0.06, _progress(page)
    finally:
        context.close()


def test_ring_fills_as_time_passes_without_a_reload(new_context, make_app_server):
    """moving the page's clock forward fills the ring in step, and it stops at full"""
    server = make_app_server(seed=_seed_checkin(1), fake_providers=True)
    context, page = _open_home_on_a_fake_clock(new_context, server)
    try:
        first = _progress(page)
        page.clock.run_for(60_000)
        later = _progress(page)
        assert abs(later - first - 60.0 / WAKE_S) < 0.02, (first, later)
        page.clock.run_for(10 * 60_000)
        assert _progress(page) == 1.0
    finally:
        context.close()


_MS_TO_NEXT = ("() => new Date(document.querySelector('%s').getAttribute('data-ring-next'))"
               ".getTime() - Date.now()" % RING)


def _run_to_next_update(page, after_ms=1500):
    """Move the page's clock to `after_ms` past the next-update instant."""
    page.clock.run_for(int(page.evaluate(_MS_TO_NEXT)) + after_ms)


_STROKE = "() => getComputedStyle(document.querySelector('%s')).stroke" % BAR
_OK_COLOUR = ("() => { const p = document.createElement('i'); p.style.color = "
              "'var(--color-status-ok)'; document.body.appendChild(p);"
              " const c = getComputedStyle(p).color; p.remove(); return c; }")
_RING_IS_DONE = "() => document.querySelector('%s').classList.contains('is-ring-done')" % RING
_SWAP_THE_RING = (
    "() => { const old = document.querySelector('%s'); const fresh = old.cloneNode(true);"
    " fresh.classList.remove('is-ring-done', 'is-ring-resumed'); old.replaceWith(fresh);"
    " document.dispatchEvent(new CustomEvent('skypane-regions-swapped')); }" % RING)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ring_flashes_green_at_one_hundred_percent_then_returns(
        new_context, make_app_server, lang, scheme):
    """at the next-update instant the bar turns the success colour, and goes back to the
    accent colour once the flourish is over"""
    server = make_app_server(seed=_seed_checkin(4), fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme=scheme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.clock.install(time=datetime.now(timezone.utc))
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(RING).wait_for(state="attached")
        normal = page.evaluate(_STROKE)
        ok = page.evaluate(_OK_COLOUR)
        assert normal != ok
        page.clock.run_for(30_000)
        assert not page.evaluate(_RING_IS_DONE)
        _run_to_next_update(page)
        assert page.evaluate(_RING_IS_DONE) and _progress(page) == 1.0
        assert page.evaluate(_STROKE) == ok
        page.clock.run_for(5_000)
        assert not page.evaluate(_RING_IS_DONE)
        assert page.evaluate(_STROKE) == normal
    finally:
        context.close()


def test_ring_flourish_happens_once_per_cycle_even_across_a_region_swap(
        new_context, make_app_server):
    """a ring swapped in during the flourish keeps it green without replaying the animation,
    and a swap after it never brings it back"""
    server = make_app_server(seed=_seed_checkin(4), fake_providers=True)
    context, page = _open_home_on_a_fake_clock(new_context, server)
    try:
        _run_to_next_update(page)
        assert page.evaluate(_RING_IS_DONE)
        assert page.evaluate(
            "() => document.querySelector('%s').getAnimations().length" % BAR) == 1
        page.evaluate(_SWAP_THE_RING)
        assert page.evaluate(_RING_IS_DONE)
        assert page.evaluate(
            "() => document.querySelector('%s').getAnimations().length" % BAR) == 0
        page.clock.run_for(5_000)
        assert not page.evaluate(_RING_IS_DONE)
        page.evaluate(_SWAP_THE_RING)
        assert not page.evaluate(_RING_IS_DONE)
    finally:
        context.close()


def test_ring_does_not_flash_under_reduced_motion(new_context, make_app_server):
    """with reduced motion the ring never turns green and never animates"""
    server = make_app_server(seed=_seed_checkin(4), fake_providers=True)
    context, page = _open_home_on_a_fake_clock(new_context, server, reduced_motion="reduce")
    try:
        _run_to_next_update(page)
        assert not page.evaluate(_RING_IS_DONE)
        assert page.evaluate(
            "() => document.querySelector('%s').getAnimations({subtree: true}).length" % RING) == 0
    finally:
        context.close()


def test_ring_is_static_under_reduced_motion(new_context, make_app_server):
    """with reduced motion the ring has no animation and stays where the server drew it"""
    server = make_app_server(seed=_seed_checkin(1), fake_providers=True)
    context, page = _open_home_on_a_fake_clock(
        new_context, server, reduced_motion="reduce")
    try:
        first = _progress(page)
        page.clock.run_for(60_000)
        assert _progress(page) == first
        assert page.evaluate(
            "() => document.querySelector('%s').getAnimations({subtree: true}).length" % RING) == 0
    finally:
        context.close()


def test_ring_is_decorative_and_the_sentence_is_its_text(new_context, make_app_server):
    """the ring is hidden from assistive technology and carries no name; the next-update
    sentence beside the title stays the text alternative, in both languages"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    for lang, words in (("en", "Next refresh in"), ("fr", "Prochain rafra\u00eechissement dans")):
        context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE, lang=lang)
        try:
            ring = page.locator(RING)
            assert ring.get_attribute("aria-hidden") == "true"
            assert ring.get_attribute("role") is None and ring.get_attribute("aria-label") is None
            assert words in page.locator(".home-state__next").inner_text()
        finally:
            context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ring_sits_just_outside_the_picture_and_takes_no_room(new_context, make_app_server, scheme):
    """the ring is a frame of the picture's own box, 5px outside it, with a visible stroke in
    either theme, and adds no height to the card"""
    server = make_app_server(seed=_seed_checkin(2), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE, scheme=scheme)
    try:
        box = page.evaluate(
            "() => { const p = document.querySelector('.home-flight__picture').getBoundingClientRect();"
            " const r = document.querySelector('%s').getBoundingClientRect();"
            " return [p.left - r.left, p.top - r.top, r.right - p.right, r.bottom - p.bottom]; }" % RING)
        assert all(abs(v - 5) < 0.6 for v in box), box
        stroke = page.evaluate(
            "() => getComputedStyle(document.querySelector('%s')).stroke" % BAR)
        assert stroke not in ("none", "rgba(0, 0, 0, 0)"), stroke
    finally:
        context.close()


def test_a_refresh_that_starts_a_new_cycle_restarts_the_ring(new_context, make_app_server):
    """when the frame checks in again, the next refresh redraws the ring from the new cycle"""
    server = make_app_server(seed=_seed_checkin(4), fake_providers=True)
    context, page = _open_home_on_a_fake_clock(new_context, server)
    try:
        assert _progress(page) > 0.7
        with history_db.open_db(server.state_dir) as conn:
            history_db.record_device_health(
                conn, datetime.now(timezone.utc).isoformat(), battery_mv=4100,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
        page.clock.run_for(50_000)
        page.wait_for_function(
            "() => 1 - Number(document.querySelector('%s').getAttribute('stroke-dashoffset'))"
            " / 100 < 0.5" % BAR, timeout=10000)
    finally:
        context.close()


def test_no_ring_while_the_frame_rests_or_is_out_of_contact(new_context, make_app_server):
    """a frame in its quiet hours or with its screen off, and one that lost contact, has no
    cycle to count down: Home draws no ring"""
    def resting(state_dir):
        _seed_checkin(1)(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=False, quiet_hours_enabled=False, wake_interval_s=WAKE_S)

    def silent(state_dir):
        _seed_checkin(3 * 60)(state_dir)

    for seed in (resting, silent):
        server = make_app_server(seed=seed, fake_providers=True)
        context, page = _open_home(new_context, server.base_url(), VIEWPORT_PHONE)
        try:
            assert page.locator(".home-flight").count() == 1
            assert page.locator(".home-ring").count() == 0
        finally:
            context.close()
