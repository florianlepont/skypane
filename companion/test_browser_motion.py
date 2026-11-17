#!/usr/bin/env python3
"""Browser checks for the motion layer: picture placeholders and blur-up, spring press
feedback, the tab bar's sliding pill and the spring switch with its tick.

Every check reads the real served page in a real browser: the computed style, the box the
browser hit-tests, the classes the script leaves behind.
"""
import pytest

from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _login, _no_js_page, seed_state_dir,
)

pytestmark = pytest.mark.browser

SWITCH = "#quick-switch-led-label ~ .settings-switch-row .switch"

# Counts navigator.vibrate calls without needing a motor.
_VIBRATE_SPY = """() => {
  window.__vibrations = [];
  navigator.vibrate = (pattern) => { window.__vibrations.push(pattern); return true; };
}"""

# Where the sliding pill sits against the active link's own pill, in viewport pixels.
_PILL_GEOMETRY = """() => {
  const rect = (el) => { const r = el.getBoundingClientRect();
    return {left: r.left, top: r.top, width: r.width, height: r.height}; };
  const slider = document.querySelector('.tab-bar__slider');
  const active = document.querySelector(
    '.tab-bar__link--active .tab-bar__pill');
  return {slider: rect(slider), active: active ? rect(active) : null,
          on: document.querySelector('.tab-bar').classList.contains('tab-bar--slider')};
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _wait(page, body, arg=None):
    """wait_for_function on a function form: the page's CSP refuses string evaluation."""
    page.wait_for_function("(a) => " + body, arg=arg)


def _eval(page, body, arg=None):
    return page.evaluate("(a) => " + body, arg)


def _wait_ready(page):
    _wait(page, "document.readyState === 'complete'")


def _wait_animations_end(page):
    _wait(page, "document.getAnimations().every(a => !Number.isFinite("
                "a.effect.getComputedTiming().endTime) || a.playState !== 'running')")


def _settle_geometry(page):
    """The slider and the active pill, once nothing finite is still moving."""
    _wait_animations_end(page)
    return page.evaluate(_PILL_GEOMETRY)


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_tab_pill_ends_under_the_active_tab(new_context, server, viewport):
    """After a real navigation to another tab the sliding pill sits exactly under the new
    active tab's pill, in whole pixels, and the bar has handed the active background to it."""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        _wait_ready(page)
        seen = _settle_geometry(page)
        assert seen["on"], "the script never took over the active pill on Home"
        for target in ("/flights", "/display", "/"):
            link = page.locator('.tab-bar a.tab-bar__link[href="%s"]' % target)
            link.click()
            page.wait_for_url("**" + target)
            _wait_ready(page)
            _wait(page, "document.querySelector('.tab-bar').classList.contains('tab-bar--slider')")
            seen = _settle_geometry(page)
            assert seen["active"] is not None, "no active tab on %s" % target
            for key in ("left", "top", "width", "height"):
                assert abs(seen["slider"][key] - seen["active"][key]) <= 1, (
                    "%s: the slider's %s is %s but the active pill's is %s"
                    % (target, key, seen["slider"][key], seen["active"][key]))
            assert seen["slider"]["left"] == round(seen["slider"]["left"]), (
                "the slider sits on a fractional pixel: %s" % seen["slider"])
    finally:
        context.close()


def test_a_cancelled_tab_click_returns_the_pill_to_the_current_tab(new_context, server):
    """A click another handler cancels leaves the page where it is, so the pill goes back
    under the tab the page really is on."""
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        _wait_ready(page)
        before = _settle_geometry(page)
        _eval(page, "document.addEventListener('click', e => e.preventDefault())")
        page.locator('.tab-bar a.tab-bar__link[href="/flights"]').click()
        _wait(page, "document.querySelector('.tab-bar__link--active')"
                    ".getAttribute('href') === '/'")
        after = _settle_geometry(page)
        assert abs(after["slider"]["left"] - before["slider"]["left"]) <= 1
        assert abs(after["slider"]["left"] - after["active"]["left"]) <= 1
    finally:
        context.close()


def test_without_the_script_the_active_tab_keeps_its_own_pill(new_context, server):
    """Scripts blocked: no slider takes over, and the active link paints its own pill."""
    with _no_js_page(new_context, server.base_url(), "/", viewport=VIEWPORT_PHONE) as page:
        page.wait_for_selector(".tab-bar__link--active")
        seen = page.evaluate("""() => ({
          on: document.querySelector('.tab-bar').classList.contains('tab-bar--slider'),
          slider: document.querySelector('.tab-bar__slider') === null,
          paint: getComputedStyle(document.querySelector(
            '.tab-bar__link--active .tab-bar__pill'
          )).backgroundColor})""")
        assert seen["on"] is False and seen["slider"] is True, seen
        assert seen["paint"] != "rgba(0, 0, 0, 0)", seen


def test_pictures_show_a_placeholder_until_they_load(new_context, server):
    """A picture still on its way marks its container .is-loading; when it lands the mark is
    gone and the blur-up class ends by itself."""
    context = new_context(viewport=VIEWPORT_PHONE)
    held = []
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.route("**/gallery/**", lambda route: held.append(route))
        page.goto(server.base_url() + "/", wait_until="domcontentloaded")
        page.wait_for_selector(".preview-frame__image", state="attached")
        _wait(page, "document.querySelector('.preview-frame').classList.contains('is-loading')")
        assert held, "the picture request was never made"
        for route in held:
            route.continue_()
        _wait(page, "!document.querySelector('.preview-frame').classList.contains('is-loading')")
        _wait(page, "!document.querySelector('.preview-frame__image')"
                    ".classList.contains('is-revealed')")
    finally:
        context.close()


def test_reduced_motion_runs_no_motion(new_context, server):
    """Under prefers-reduced-motion the animations collapse to ~0 ms, a press does not scale,
    the tab slider does not glide, and a switch press plays no ring and vibrates nothing."""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce")
    try:
        page = context.new_page()
        page.add_init_script("(" + _VIBRATE_SPY + ")()")
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet?tab=settings")
        _wait_ready(page)
        durations = page.evaluate("""() => {
          const out = {};
          for (const sel of ['.switch__thumb', '.tab-bar__pill', 'button']) {
            const cs = getComputedStyle(document.querySelector(sel));
            out[sel] = cs.transitionDuration.split(', ').map(parseFloat);
          }
          return out;
        }""")
        for sel, values in durations.items():
            assert all(v <= 0.001 for v in values), (sel, values)
        page.locator(SWITCH).first.click()
        assert _eval(page, "window.__vibrations.length") == 0
        assert not _eval(page, "document.querySelector(a).classList.contains('switch--tick')",
                         SWITCH)
        assert _eval(page, "document.querySelector('.tab-bar__slider').classList"
                           ".contains('tab-bar__slider--glide')") is False
        page.locator(SWITCH).scroll_into_view_if_needed()
        page.mouse.move(*_centre(page, SWITCH))
        page.mouse.down()
        assert _eval(page, "getComputedStyle(document.querySelector(a)).scale", SWITCH) == "none"
        page.mouse.up()
    finally:
        context.close()


def _centre(page, selector):
    box = page.locator(selector).first.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_switch_springs_ticks_and_keeps_its_44px_target(new_context, server, viewport):
    """Pressing the switch stretches its thumb (the button itself never scales), a toggle plays
    the ring once and vibrates 10 ms, and the 44px hit target holds mid-animation and after."""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        page.add_init_script("(" + _VIBRATE_SPY + ")()")
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet?tab=settings")
        _wait_ready(page)
        page.wait_for_selector(SWITCH)
        before = page.locator(SWITCH).get_attribute("aria-checked")
        page.locator(SWITCH).scroll_into_view_if_needed()
        x, y = _centre(page, SWITCH)
        page.mouse.move(x, y)
        page.mouse.down()
        _wait(page, "getComputedStyle(document.querySelector(a + ' .switch__thumb')).scale"
                    " !== 'none'", SWITCH)
        box = page.locator(SWITCH).bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, box
        page.mouse.up()
        _wait(page, "document.querySelector(a).classList.contains('switch--tick')", SWITCH)
        box = page.locator(SWITCH).bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, box
        assert _eval(page, "window.__vibrations") == [10]
        _wait(page, "document.querySelector(a.sel).getAttribute('aria-checked') !== a.before",
              {"sel": SWITCH, "before": before})
        _wait_animations_end(page)
        _assert_hit_target(page, SWITCH, "settings switch after the toggle")
    finally:
        context.close()


def test_a_press_scales_a_button_and_releases_to_rest(new_context, server):
    """A pressed button shrinks to 97 % and, released, springs back to no scale at all."""
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        _wait_ready(page)
        selector = ".tab-bar__more > summary.tab-bar__link .tab-bar__pill"
        page.wait_for_selector(selector)
        x, y = _centre(page, selector)
        page.mouse.move(x, y)
        page.mouse.down()
        _wait(page, "getComputedStyle(document.querySelector(a)).scale === '0.97'", selector)
        page.mouse.up()
        _wait(page, "getComputedStyle(document.querySelector(a)).scale === 'none'", selector)
        transition = _eval(
            page, "getComputedStyle(document.querySelector(a)).transitionProperty", selector)
        assert "scale" in transition and "background-color" in transition, transition
    finally:
        context.close()


@pytest.mark.parametrize("route", ["/", "/flights", "/fleet?tab=settings"])
def test_hit_targets_settle_on_the_swept_pages(new_context, server, route):
    """With the motion layer on, the tab links and the page's own controls still own their
    centres once the page has settled, on a phone."""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        _wait_ready(page)
        _assert_hit_target(
            page, ".tab-bar a.tab-bar__link", route)
        _assert_hit_target(page, ".tab-bar__more > summary", route)
    finally:
        context.close()
