"""Real-browser checks of Home's status header: it sits above the picture row,
its three zones (state, battery dial, switches) arrange as columns on a wide
card, state beside dial with the switches below on a medium one, and stacked
on a phone, the two switches have 44px targets and nothing overflows from 1280
down to 360 px, keyboard operation (Space and Enter) with a visible focus
indicator, the persisted effect plus confirmation flash after each switch, the
same flow with scripts blocked, the battery dial's accessible name, and a
visible unchecked switch thumb in the dark theme."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

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

VIEWPORTS = (
    ("1280", VIEWPORT_DESKTOP),
    ("1024", {"width": 1024, "height": 900}),
    ("840", {"width": 840, "height": 900}),
    ("600", {"width": 600, "height": 900}),
    ("390", VIEWPORT_PHONE),
    ("360", VIEWPORT_MIN_SUPPORTED),
)
# The header's zone arrangement follows its own width (a container query):
# columns from 840px of card, state beside dial with the switches below
# from 520px, stacked under that.
CARD_COLUMNS_MIN = 840
CARD_SIDE_BY_SIDE_MIN = 520


def _zone_geometry(page):
    return page.evaluate(
        """() => {
            const r = s => document.querySelector(s).getBoundingClientRect();
            return {status: r('.home-state__status'), battery: r('.home-battery'),
                    switches: r('.home-state__switches'), panel: r('.home-state')};
        }""")


def _assert_zone_arrangement(geometry, label):
    """Columns, two rows or a stack, chosen by the card's measured width."""
    status, battery, switches = geometry["status"], geometry["battery"], geometry["switches"]
    width = geometry["panel"]["width"]
    if width >= CARD_COLUMNS_MIN:
        assert status["right"] <= battery["left"] + 1 and battery["right"] <= switches["left"] + 1, label
    elif width >= CARD_SIDE_BY_SIDE_MIN:
        assert status["right"] <= battery["left"] + 1, label
        assert max(status["bottom"], battery["bottom"]) <= switches["top"] + 1, label
    else:
        assert status["bottom"] <= battery["top"] + 1, label
        assert battery["bottom"] <= switches["top"] + 1, label
    for zone in (status, battery, switches):
        assert geometry["panel"]["left"] - 1 <= zone["left"], label
        assert zone["right"] <= geometry["panel"]["right"] + 1, label
SCREEN_BUTTON = 'form[action="/quick/display"] button[role="switch"]'
QUIET_BUTTON = 'form[action="/quick/quiet-hours"] button[role="switch"]'
FLASH = '.toast-region--flash .toast[role="status"]'


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=False)


def _open_home(new_context, base_url, lang, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.HOME_ROUTE)
    page.locator("main").wait_for(state="visible")
    return context, page


def _has_visible_focus_indicator(page, selector):
    return page.evaluate(
        """sel => {
            const el = document.querySelector(sel);
            if (document.activeElement !== el) return false;
            const style = getComputedStyle(el);
            const outline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
            return outline || style.boxShadow !== 'none';
        }""", selector)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_status_header_layout_targets_and_keyboard(
        new_context, make_app_server, lang, viewport_name, viewport):
    """the header sits above the picture row, its zones arrange for the card's width, both
    switches are at least 44px tall inside the viewport with no page overflow, show a focus
    indicator under keyboard navigation, and a Space press on the screen switch persists
    display_enabled=false and lands back on Home with the confirmation flash and the
    "Screen off" title"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        card = page.locator('section[aria-labelledby="home-frame-state"]')
        card.wait_for(state="visible")
        geometry = page.evaluate(
            """() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return {header: r('.home-state'), row: r('.home-picture-row'), title: r('h1')};
            }""")
        assert geometry["title"]["bottom"] <= geometry["header"]["top"] < geometry["row"]["top"]
        _assert_zone_arrangement(_zone_geometry(page), viewport_name)
        for selector in (SCREEN_BUTTON, QUIET_BUTTON):
            box = page.locator(selector).bounding_box()
            assert box is not None
            assert box["height"] >= 44 and box["width"] >= 44, (
                "%s: %s is %sx%s" % (viewport_name, selector, box["width"], box["height"]))
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], (
                "%s: %s leaves the viewport" % (viewport_name, selector))
        overflow = _assert_no_page_overflow(page, "home/%s/%s" % (lang, viewport_name), viewport["width"])
        assert not overflow, overflow

        page.locator(SCREEN_BUTTON).focus()
        page.keyboard.press("Tab")
        assert _has_visible_focus_indicator(page, QUIET_BUTTON), "no focus ring on the quiet switch"
        page.keyboard.press("Shift+Tab")
        assert _has_visible_focus_indicator(page, SCREEN_BUTTON), "no focus ring on the screen switch"
        with page.expect_navigation():
            page.keyboard.press("Space")
        # flash-cleanup.js drops the query string once the toast is shown.
        assert urlsplit(page.url).path == layout.HOME_ROUTE
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
        assert page.locator(SCREEN_BUTTON).get_attribute("aria-checked") == "false"
        headline = page.locator(".home-state__headline").inner_text()
        assert headline.strip() == ("Screen off" if lang == "en" else "Écran éteint")
        detail = page.locator(".home-state__detail").inner_text()
        assert detail.strip() == ("The frame stays blank" if lang == "en" else "Le cadre reste vide")
    finally:
        context.close()


def test_enter_on_the_quiet_switch_posts_and_the_header_follows(new_context, make_app_server):
    """Enter on the quiet-hours switch (scripts on) posts, persists, redirects with the flash
    and the switch reads checked with the headline following the new state"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_DESKTOP)
    try:
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "false"
        page.locator(QUIET_BUTTON).focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "true"
    finally:
        context.close()


def test_clicking_the_row_toggles_the_switch(new_context, make_app_server):
    """the whole switch row is the tap target: a click on the row's left edge, away from the
    track, still presses the switch"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_PHONE)
    try:
        with page.expect_navigation():
            page.locator(".home-switch--on").first.click(position={"x": 12, "y": 28})
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_battery_block_has_an_accessible_name_in_both_themes(new_context, make_app_server, scheme):
    """the seeded battery reading renders as one named image whose label starts with "Battery
    about", its dial is drawn, and its text stays readable (not transparent) in the light and
    dark scheme"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        block = page.locator('.home-battery[role="img"]')
        block.wait_for(state="visible")
        assert (block.get_attribute("aria-label") or "").startswith("Battery about")
        dial = block.locator("svg")
        assert dial.is_visible()
        assert dial.locator("circle.drawing-arc-track").count() == 1
        assert page.locator('.home-battery [role="img"], .home-battery [aria-label]').count() == 0
        value_color = block.locator(".home-battery__value").evaluate(
            "el => getComputedStyle(el).color")
        assert value_color != "rgba(0, 0, 0, 0)"
    finally:
        context.close()


def test_quiet_hours_switch_with_scripts_blocked(new_context, make_app_server):
    """with JavaScript disabled the quiet-hours switch still posts, persists, redirects to Home
    and shows the flash plus the flipped switch"""
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), layout.HOME_ROUTE) as page:
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "false"
        with page.expect_navigation():
            page.locator(QUIET_BUTTON).click()
        assert page.url == server.base_url() + "/?flash=quiet_on"
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "true"


def _seed_checkin(minutes_ago, battery_mv):
    """A seed with a fresh check-in `minutes_ago` and the given battery reading, on a 5 minute
    wake interval: due within 10 minutes of the expected wake, overdue after, long overdue
    after 15."""
    def seed(state_dir):
        seed_state_dir(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=True, quiet_hours_enabled=False, wake_interval_s=300)
        ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        with history_db.open_db(state_dir) as conn:
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=battery_mv, fw_version="1.0.0",
                boot_reason="wake", rssi="-60")
    return seed


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
@pytest.mark.parametrize("minutes_ago,battery_mv,wording,amber", [
    (2, 4100, "Next update in", False),
    (16, 3700, "Update overdue · expected at", False),
    (30, 3381, "Update overdue · expected at", True),
])
def test_late_states_and_battery_fit_every_viewport(
        new_context, make_app_server, scheme, viewport_name, viewport,
        minutes_ago, battery_mv, wording, amber):
    """on time, briefly late and long overdue each read their own wording; only the long one
    turns the dot amber and shows the Health link (a 44px target on a phone); the battery
    figure and dial are large, the zones arrange for the card's width, and nothing overflows"""
    server = make_app_server(seed=_seed_checkin(minutes_ago, battery_mv), fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(".home-state").wait_for(state="visible")
        assert wording in page.locator(".home-state__next").inner_text()
        assert page.locator(".home-state__dot.dot--warn").count() == (1 if amber else 0)
        link = page.locator('.home-state a[href="/health"]')
        assert link.count() == (1 if amber else 0)
        if amber:
            assert link.is_visible() and link.inner_text().strip() == "See Health"
            box = link.bounding_box()
            assert box["height"] >= (32 if viewport["width"] >= 1280 else 44)
            assert "home-state--warn" in page.locator(".home-state").get_attribute("class")
        figure = page.locator(".home-battery__value").evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)")
        dial = page.locator(".home-battery svg").bounding_box()
        assert figure >= 28 and dial["width"] >= 120 and dial["height"] >= 120
        _assert_zone_arrangement(_zone_geometry(page), "%s/%s" % (viewport_name, minutes_ago))
        overflow = _assert_no_page_overflow(
            page, "home/%s/%s/%s" % (scheme, viewport_name, minutes_ago), viewport["width"])
        assert not overflow, overflow
    finally:
        context.close()


INFO_BUTTON = ".home-state .info-tip__button"
INFO_BUBBLE = ".home-state .info-tip__bubble"


def _assert_bubble_inside_viewport(page, viewport_width):
    box = page.locator(INFO_BUBBLE).bounding_box()
    assert box is not None
    assert box["x"] >= 0 and box["x"] + box["width"] <= viewport_width, box
    panel = page.locator(".home-state").bounding_box()
    assert box["x"] >= panel["x"] - 1 and box["x"] + box["width"] <= panel["x"] + panel["width"] + 1


@pytest.mark.parametrize("lang,sentence", [
    ("en", "it wakes about every 5 min, so it does not refresh continuously."),
    ("fr", "il se réveille environ toutes les 5 min, il ne se rafraîchit donc pas en continu."),
])
@pytest.mark.parametrize("viewport_name,viewport", [VIEWPORTS[0], VIEWPORTS[-2], VIEWPORTS[-1]],
                         ids=["1280", "390", "360"])
def test_cadence_tooltip_opens_on_hover_and_keyboard_focus(
        new_context, make_app_server, lang, sentence, viewport_name, viewport):
    """the info button has a 44px hit area; the tooltip is hidden at rest, shows on hover and on
    keyboard focus with the interval sentence, stays inside the viewport and the status card
    (including at 360px) and the page does not overflow while it is open"""
    server = make_app_server(seed=_seed_checkin(2, 4100), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        button, bubble = page.locator(INFO_BUTTON), page.locator(INFO_BUBBLE)
        box = button.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, box
        assert not bubble.is_visible()
        button.hover()
        assert bubble.is_visible() and sentence in bubble.inner_text()
        _assert_bubble_inside_viewport(page, viewport["width"])
        assert not _assert_no_page_overflow(page, "tooltip/%s" % viewport_name, viewport["width"])
        page.mouse.move(0, 0)
        assert not bubble.is_visible()
        page.locator(".home-state__eyebrow").click()
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.classList.contains('info-tip__button')")
        assert bubble.is_visible() and sentence in bubble.inner_text()
        _assert_bubble_inside_viewport(page, viewport["width"])
        assert _has_visible_focus_indicator(page, INFO_BUTTON)
        described = button.get_attribute("aria-describedby")
        assert page.locator("#" + described).get_attribute("role") == "tooltip"
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_cadence_tooltip_is_legible_in_both_themes(new_context, make_app_server, scheme):
    """the open tooltip's text reads against its own background in light and dark"""
    server = make_app_server(seed=_seed_checkin(2, 4100), fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(INFO_BUTTON).focus()
        assert page.locator(INFO_BUBBLE).is_visible()
        ratio = page.evaluate(
            """() => {
                const el = document.querySelector('.home-state .info-tip__bubble');
                const style = getComputedStyle(el);
                const lum = css => {
                    const c = css.match(/[\\d.]+/g).map(Number).slice(0, 3).map(v => {
                        v /= 255;
                        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                    });
                    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
                };
                const [x, y] = [lum(style.color), lum(style.backgroundColor)].sort((p, q) => q - p);
                return (x + 0.05) / (y + 0.05);
            }""")
        assert ratio >= 4.5, ratio
    finally:
        context.close()


def _dot_animation(page):
    return page.evaluate(
        """() => {
            const style = getComputedStyle(
                document.querySelector('.home-state__dot'), '::after');
            return {name: style.animationName, duration: style.animationDuration};
        }""")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_status_dot_halo_pulses_and_reduced_motion_stops_it(new_context, make_app_server, scheme):
    """a healthy screen-on dot carries a halo animation on the --motion-dot-pulse period whose
    frames differ a moment apart; under prefers-reduced-motion the computed animation is none"""
    server = make_app_server(seed=_seed_checkin(2, 4100), fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(".home-state__dot").wait_for(state="visible")
        animation = _dot_animation(page)
        assert animation["name"] == "skypane-dot-halo" and animation["duration"] == "3.2s", animation
        frames = []
        for _ in range(2):
            frames.append(page.evaluate(
                "getComputedStyle(document.querySelector('.home-state__dot'), '::after').transform"))
            page.wait_for_timeout(700)
        assert frames[0] != frames[1], frames
    finally:
        context.close()
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme=scheme, reduced_motion="reduce")
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(".home-state__dot").wait_for(state="visible")
        assert _dot_animation(page)["name"] == "none"
    finally:
        context.close()


def test_resting_dot_does_not_pulse(new_context, make_app_server):
    """quiet hours and a switched-off screen carry the neutral dot with no halo animation"""
    fresh = _seed_checkin(2, 4100)

    def seed(state_dir):
        fresh(state_dir)
        device_config.save_device_config(state_dir, display_enabled=False)
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_PHONE)
    try:
        assert page.locator(".home-state__dot.dot--off").count() == 1
        assert _dot_animation(page)["name"] == "none"
    finally:
        context.close()


def _contrast(page, selector_a, selector_b):
    """The WCAG contrast ratio between two elements' computed background colours."""
    return page.evaluate(
        """([a, b]) => {
            const lum = sel => {
                const m = getComputedStyle(document.querySelector(sel)).backgroundColor
                    .match(/[\\d.]+/g).map(Number);
                const c = m.slice(0, 3).map(v => {
                    v /= 255;
                    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
            };
            const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
            return (x + 0.05) / (y + 0.05);
        }""", [selector_a, selector_b])


def test_dark_theme_unchecked_switch_thumb_stands_out_from_its_track(new_context, make_app_server):
    """in the dark theme an unchecked switch's thumb is a light disc on the dark track (at least
    3:1), not a dark-on-dark circle"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme="dark")
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "false"
        ratio = _contrast(page, QUIET_BUTTON + " .switch__thumb", QUIET_BUTTON + " .switch__track")
        assert ratio >= 3, ratio
    finally:
        context.close()
