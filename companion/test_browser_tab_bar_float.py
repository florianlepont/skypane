"""Real-browser geometry of the floating tab bar and the phone top bar: 12px side margins, 68px
high, a pill above the home-indicator inset (forced with --safe-bottom), the stronger glass, the
admin's space switch kept first and set apart, the last content clear of the bar at the end of the
page, ink that holds over a white and a black backdrop in both themes, a top bar that is
transparent and clears the status bar, and reduced motion."""
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
          shadow: glass.boxShadow, image: glass.backgroundImage};
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
        assert flat["left"] == pytest.approx(12, abs=0.5)
        assert flat["right"] == pytest.approx(12, abs=0.5)
        assert flat["height"] == pytest.approx(68, abs=0.5)
        assert flat["bottom"] == pytest.approx(12, abs=0.5)
        assert flat["radius"] >= 32
        assert "blur(26px)" in flat["blur"] and "saturate(2)" in flat["blur"]
        assert "inset" in flat["shadow"] and "linear-gradient" in flat["image"]
        page.evaluate(
            "(px) => document.documentElement.style.setProperty('--safe-bottom', px + 'px')",
            INSET)
        lifted = page.evaluate(_BAR)
        assert lifted["bottom"] == pytest.approx(12 + INSET, abs=0.5)
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
def test_the_space_switch_stays_first_set_apart_and_the_active_item_is_an_inner_pill(
        new_context, app, viewport, scheme):
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        facts = page.evaluate(
            """() => {
              const cells = [...document.querySelectorAll('.tab-bar > *')];
              const first = cells[0];
              const pill = first.querySelector('.tab-bar__pill');
              const active = document.querySelector(
                  '.tab-bar__link--active .tab-bar__pill');
              const bar = document.querySelector('.tab-bar').getBoundingClientRect();
              return {firstIsSwitch: first.classList.contains('tab-bar__link--switch'),
                      outline: getComputedStyle(pill).borderTopWidth,
                      outlineColour: getComputedStyle(pill).borderTopColor,
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
        assert facts["firstIsSwitch"] and facts["outline"] == "1px"
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
def test_the_bar_ink_holds_over_a_white_and_a_black_backdrop(
        new_context, app, viewport, scheme):
    """the computed fill of the bar (topped by the brightest sheen stop) is composited over a
    pure white and a pure black backdrop; every inactive label and the active label hold 4.5:1"""
    context, page = _open(new_context, app, _home(app), viewport, scheme)
    try:
        read = page.evaluate(
            """() => {
              const rgba = (css) => css.match(/[\\d.]+/g).map(Number);
              const bar = document.querySelector('.tab-bar');
              const glass = getComputedStyle(bar, '::before');
              const sheen = glass.backgroundImage.match(/rgba?\\([^)]*\\)/)[0];
              const labels = [...document.querySelectorAll(
                  '.tab-bar__link:not(.tab-bar__link--active):not(.tab-bar__link--switch)'
                  + ' .tab-bar__label')];
              const active = document.querySelector(
                  '.tab-bar__link--active .tab-bar__label');
              const pill = document.querySelector('.tab-bar__link--active .tab-bar__pill');
              return {fill: glass.backgroundColor, sheen,
                      pill: getComputedStyle(pill).backgroundColor,
                      inks: labels.map(el => getComputedStyle(el).color),
                      active: getComputedStyle(active).color};
            }""")

        def over(top, base):
            parts = [float(p) for p in top[top.index("(") + 1:-1].split(",")]
            alpha = parts[3] if len(parts) == 4 else 1.0
            return [alpha * c + (1 - alpha) * b for c, b in zip(parts[:3], base)]

        def hex_of(rgb):
            return "#%02X%02X%02X" % tuple(round(c) for c in rgb)

        def ink_hex(css):
            return hex_of([float(p) for p in css[css.index("(") + 1:-1].split(",")[:3]])

        assert read["inks"]
        for backdrop in ((255, 255, 255), (0, 0, 0)):
            fill = over(read["sheen"], over(read["fill"], backdrop))
            for ink in read["inks"]:
                assert contrast_ratio(ink_hex(ink), hex_of(fill)) >= WCAG_AA_NORMAL_TEXT, (
                    scheme, backdrop, ink)
            pill = over(read["pill"], fill)
            assert contrast_ratio(ink_hex(read["active"]), hex_of(pill)) >= WCAG_AA_NORMAL_TEXT, (
                scheme, backdrop, "active")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_more_sheet_has_the_bar_glass_and_its_ink_holds_over_any_backdrop(
        new_context, app, scheme):
    """the More sheet takes the floating bar's fill, sheen, edge and blur, is not nested in a
    backdrop root (so it blurs the page, not the empty bar), and its row ink (the current row's
    accent included, over its 12% tint) holds 4.5:1 over a white and a black backdrop"""
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
              const barStyle = getComputedStyle(bar);
              const links = [...document.querySelectorAll('.tab-bar__more-panel a')];
              return {
                same: ['backgroundColor', 'backgroundImage', 'backdropFilter']
                    .every((k) => glass[k] === panel[k]) && barStyle.backdropFilter === 'none'
                    && panel.borderTopColor === barStyle.borderTopColor,
                fill: panel.backgroundColor,
                sheen: panel.backgroundImage.match(/rgba?\\([^)]*\\)/)[0],
                inks: links.map((a) => [getComputedStyle(a).color,
                                        a.classList.contains('mobile-nav__link--active')]),
                tall: links.every((a) => a.getBoundingClientRect().height >= 44)};
            }""")
        assert read["same"] and read["tall"] and read["inks"], read

        def parts(css):
            return [float(p) for p in css[css.index("(") + 1:-1].split(",")]

        def over(top, base):
            numbers = parts(top)
            alpha = numbers[3] if len(numbers) == 4 else 1.0
            return [alpha * c + (1 - alpha) * b for c, b in zip(numbers[:3], base)]

        def hex_of(rgb):
            return "#%02X%02X%02X" % tuple(round(c) for c in rgb)

        for backdrop in ((255, 255, 255), (0, 0, 0)):
            fill = over(read["sheen"], over(read["fill"], backdrop))
            for ink, active in read["inks"]:
                ink_rgb = parts(ink)[:3]
                plate = [0.12 * i + 0.88 * f for i, f in zip(ink_rgb, fill)] if active else fill
                assert contrast_ratio(hex_of(ink_rgb), hex_of(plate)) >= WCAG_AA_NORMAL_TEXT, (
                    scheme, backdrop, ink, active)
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
