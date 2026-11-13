"""Real-browser geometry of the floating tab bar and the phone top bar: 8px side margins, 68px
high, a pill 6px above the home-indicator inset (forced with --safe-bottom), opaque (the More
sheet too), the
admin's space switch kept first and set apart, the last content clear of the bar at the end of the
page, ink and active pill contrast in both themes, a top bar that is
transparent and clears the status bar, and reduced motion."""
import re

import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE]
VIEWPORT_IDS = ["360", "390"]
INSET = 34

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

_BAR = """() => {
  const bar = document.querySelector('.tab-bar');
  const box = bar.getBoundingClientRect();
  const style = getComputedStyle(bar);
  const glass = getComputedStyle(bar, '::before');
  return {left: box.left, right: window.innerWidth - box.right, top: box.top,
          bottom: window.innerHeight - box.bottom, height: box.height,
          radius: parseFloat(style.borderTopLeftRadius),
          blur: glass.backdropFilter || glass.webkitBackdropFilter,
          shadow: glass.boxShadow, image: glass.backgroundImage,
          fill: glass.backgroundColor, barFill: style.backgroundColor,
          border: style.borderTopColor, borderWidth: parseFloat(style.borderTopWidth)};
}"""

_LAST_CONTENT_BOTTOM = """() => {
  const main = document.querySelector('main');
  let bottom = 0;
  for (const el of main.querySelectorAll('*')) {
    if (!el.checkVisibility()) continue;
    const position = getComputedStyle(el).position;
    if (position === 'fixed' || position === 'absolute') continue;
    const box = el.getBoundingClientRect();
    if (box.width > 0 && box.height > 0) bottom = Math.max(bottom, box.bottom);
  }
  return bottom;
}"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, viewport, scheme="light", lang="en", **context_args):
    context = new_context(viewport=viewport, color_scheme=scheme, **context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator(".tab-bar").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        page.wait_for_function(_SETTLED)
    return context, page


def _home(app):
    return "/devices/%s/" % app.fleet.live.id


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_bar_floats_as_a_pill_with_margins_above_the_inset(
        new_context, app, viewport, scheme):
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        flat = page.evaluate(_BAR)
        assert flat["left"] == pytest.approx(8, abs=0.5)
        assert flat["right"] == pytest.approx(8, abs=0.5)
        assert flat["height"] == pytest.approx(68, abs=0.5)
        assert flat["bottom"] == pytest.approx(6, abs=0.5)
        assert flat["radius"] >= 32
        # Opaque: one solid colour, no blur, no sheen, a visible edge and a shadow.
        assert flat["blur"] in ("none", "")
        assert flat["image"] == "none"
        assert flat["fill"] == flat["barFill"] and flat["fill"].startswith("rgb(")
        assert flat["borderWidth"] == 1 and flat["border"].startswith("rgb(")
        assert flat["shadow"] != "none"
        page.evaluate(
            "(px) => document.documentElement.style.setProperty('--safe-bottom', px + 'px')",
            INSET)
        lifted = page.evaluate(_BAR)
        assert lifted["bottom"] == pytest.approx(6 + INSET, abs=0.5)
        assert lifted["left"] == flat["left"] and lifted["height"] == flat["height"]
    finally:
        context.close()


@pytest.mark.parametrize("path_name", ["home", "flights", "fleet"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_last_content_clears_the_bar_at_the_end_of_the_page(
        new_context, app, viewport, path_name):
    path = {"home": _home(app), "flights": "/devices/%s/flights" % app.fleet.live.id,
            "fleet": "/fleet"}[path_name]
    context, page = _open(new_context, app, path, viewport)
    try:
        for inset in (0, INSET):
            page.evaluate(
                "(px) => document.documentElement.style.setProperty('--safe-bottom', px + 'px')",
                inset)
            page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_function(
                "() => Math.abs(window.scrollY + window.innerHeight"
                " - document.documentElement.scrollHeight) < 2")
            bar_top = page.evaluate(_BAR)["top"]
            assert page.evaluate(_LAST_CONTENT_BOTTOM) <= bar_top + 0.5, (path_name, inset)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_no_cell_is_a_space_switch_and_the_active_item_is_an_inner_pill(
        new_context, app, viewport, scheme):
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        # Once the script has placed the sliding pill it paints the active item's fill, so the
        # inner pill is measured on the slider, after its glide has ended.
        page.wait_for_function(
            "() => document.querySelector('.tab-bar').classList.contains('tab-bar--slider')"
            " && document.querySelector('.tab-bar__slider').getAnimations().length === 0")
        facts = page.evaluate(
            """() => {
              const cells = [...document.querySelectorAll('.tab-bar > :not(.tab-bar__slider)')];
              const first = cells[0];
              const active = document.querySelector('.tab-bar__slider');
              const bar = document.querySelector('.tab-bar').getBoundingClientRect();
              return {firstIsSwitch: first.classList.contains('tab-bar__link--switch'),
                      switchCells: document.querySelectorAll('.tab-bar__link--switch').length,
                      accent: getComputedStyle(document.documentElement)
                          .getPropertyValue('--color-accent'),
                      activeBg: getComputedStyle(active).backgroundColor,
                      activeRadius: parseFloat(getComputedStyle(active).borderTopLeftRadius),
                      activeBox: active.getBoundingClientRect().toJSON(),
                      bar: bar.toJSON(),
                      narrow: cells.filter(c => {
                          const r = c.getBoundingClientRect();
                          return r.width < 44 || r.height < 44; }).length,
                      clipped: [...document.querySelectorAll('.tab-bar__label')]
                          .filter(el => el.scrollWidth > el.clientWidth + 0.5).length};
            }""")
        assert not facts["firstIsSwitch"] and facts["switchCells"] == 0
        assert facts["activeBg"] not in ("rgba(0, 0, 0, 0)", "transparent")
        assert facts["activeRadius"] >= 16
        box, bar = facts["activeBox"], facts["bar"]
        assert box["x"] >= bar["x"] and box["right"] <= bar["right"]
        assert box["y"] >= bar["y"] and box["bottom"] <= bar["bottom"]
        assert facts["narrow"] == 0 and facts["clipped"] == 0
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_bar_ink_and_active_pill_hold_their_contrast(
        new_context, app, viewport, scheme):
    """the bar is opaque, so what scrolls beneath never changes its contrast: every inactive
    label holds 4.5:1 on it, the solid active pill holds 3:1 against the bar and its label
    4.5:1 on the pill"""
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        read = page.evaluate(
            """() => {
              const bar = getComputedStyle(document.querySelector('.tab-bar'), '::before');
              const labels = [...document.querySelectorAll(
                  '.tab-bar__link:not(.tab-bar__link--active)'
                  + ' .tab-bar__label')];
              const active = document.querySelector(
                  '.tab-bar__link--active .tab-bar__label');
              const pill = document.querySelector('.tab-bar__link--active .tab-bar__pill');
              const slider = getComputedStyle(document.querySelector('.tab-bar__slider'));
              return {fill: bar.backgroundColor,
                      pill: getComputedStyle(pill).backgroundColor,
                      slider: slider.backgroundColor, sliderOpacity: slider.opacity,
                      inks: labels.map(el => getComputedStyle(el).color),
                      active: getComputedStyle(active).color};
            }""")

        def hex_of(css):
            numbers = [float(p) for p in css[css.index("(") + 1:-1].split(",")]
            assert len(numbers) == 3, css
            return "#%02X%02X%02X" % tuple(round(c) for c in numbers)

        assert read["inks"]
        bar = hex_of(read["fill"])
        for ink in read["inks"]:
            assert contrast_ratio(hex_of(ink), bar) >= WCAG_AA_NORMAL_TEXT, (scheme, ink)
        # The sliding pill (once the script has placed it) and the server-rendered pill are both
        # the solid accent.
        solid = read["slider"] if read["sliderOpacity"] == "1" else read["pill"]
        assert contrast_ratio(hex_of(solid), bar) >= 3.0, (scheme, solid, bar)
        assert contrast_ratio(hex_of(read["active"]), hex_of(solid)) >= WCAG_AA_NORMAL_TEXT, (
            scheme, "active")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_more_sheet_is_opaque_and_the_colour_of_the_bar(new_context, app, scheme):
    """the More sheet is one solid colour, the bar's own, with the bar's edge colour and no blur;
    its shadow is cast upward only (no downward offset that would darken the bar); its row ink
    (the current row's accent included, over its 12% tint) holds 4.5:1"""
    context, page = _open(new_context, app, _home(app), VIEWPORT_PHONE, scheme)
    try:
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel a").first.wait_for(state="visible")
        page.wait_for_function(_SETTLED)
        read = page.evaluate(
            """() => {
              const bar = document.querySelector('.tab-bar');
              const glass = getComputedStyle(bar, '::before');
              const panel = getComputedStyle(document.querySelector('.tab-bar__more-panel'));
              const links = [...document.querySelectorAll('.tab-bar__more-panel a')];
              return {
                fill: panel.backgroundColor, barFill: glass.backgroundColor,
                image: panel.backgroundImage, blur: panel.backdropFilter,
                edge: panel.borderTopColor === getComputedStyle(bar).borderTopColor,
                shadow: panel.boxShadow,
                inks: links.map((a) => [getComputedStyle(a).color,
                                        a.classList.contains('mobile-nav__link--active')]),
                tall: links.every((a) => a.getBoundingClientRect().height >= 44)};
            }""")
        assert read["fill"] == read["barFill"] and read["fill"].startswith("rgb("), read
        assert read["image"] == "none" and read["blur"] in ("none", ""), read
        assert read["edge"] and read["tall"] and read["inks"], read
        # Every layer's vertical offset is negative: the shadow is cast upward only.
        for layer in re.split(r",\s*(?=rgba?\()", read["shadow"]):
            lengths = [float(x) for x in re.findall(r"(-?\d+(?:\.\d+)?)px", layer)]
            assert lengths[1] <= 0, read["shadow"]

        def parts(css):
            return [float(p) for p in css[css.index("(") + 1:-1].split(",")]

        def hex_of(rgb):
            return "#%02X%02X%02X" % tuple(round(c) for c in rgb)

        fill = parts(read["fill"])
        for ink, active in read["inks"]:
            ink_rgb = parts(ink)[:3]
            plate = [0.12 * i + 0.88 * f for i, f in zip(ink_rgb, fill)] if active else fill
            assert contrast_ratio(hex_of(ink_rgb), hex_of(plate)) >= WCAG_AA_NORMAL_TEXT, (
                scheme, ink, active)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_phone_top_bar_is_transparent_and_clears_the_status_bar(
        new_context, app, viewport, scheme):
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        page.evaluate(
            "(px) => document.documentElement.style.setProperty('--safe-top', px + 'px')", 47)
        facts = page.evaluate(
            """() => {
              const header = document.querySelector('.site-header');
              const style = getComputedStyle(header);
              const brand = header.querySelector('.brand').getBoundingClientRect();
              return {bg: style.backgroundColor, border: style.borderBottomWidth,
                      filter: style.backdropFilter, brandTop: brand.top,
                      paddingTop: parseFloat(style.paddingTop)};
            }""")
        assert facts["bg"] == "rgba(0, 0, 0, 0)" and facts["border"] == "0px"
        assert facts["filter"] in ("none", "")
        assert facts["paddingTop"] >= 47
        assert facts["brandTop"] >= 47
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_reduced_motion_zeroes_the_active_pill_entrance(new_context, app, viewport):
    context, page = _open(
        new_context, app, _home(app), viewport, reduced_motion="reduce")
    try:
        duration = page.locator(".tab-bar__link--active .tab-bar__pill").evaluate(
            "(el) => parseFloat(getComputedStyle(el).animationDuration)")
        assert duration < 0.001
    finally:
        context.close()


def test_without_script_the_bar_is_still_a_floating_pill(new_context, app):
    context, page = _open(
        new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        assert page.evaluate(_BAR)["height"] == pytest.approx(68, abs=0.5)
    finally:
        context.close()
