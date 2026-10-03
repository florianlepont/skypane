"""Real-browser checks of Home's status header: it sits above the picture row,
the two switches have 44px targets and no horizontal overflow at 1280/390/360
px, keyboard operation (Space and Enter) with a visible focus indicator, the
persisted effect plus confirmation flash after each switch, the same flow with
scripts blocked, and the battery block's accessible name."""
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
    ("390", VIEWPORT_PHONE),
    ("360", VIEWPORT_MIN_SUPPORTED),
)
SCREEN_BUTTON = 'form[action="/quick/display"] button[role="switch"]'
QUIET_BUTTON = 'form[action="/quick/quiet-hours"] button[role="switch"]'
FLASH = '.banner--flash[role="status"]'


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
    """the header sits above the picture row, both switches are at least 44px tall inside the
    viewport with no page overflow (side by side with the status on desktop, stacked on a
    phone), show a focus indicator under keyboard navigation, and a Space press on the screen
    switch persists display_enabled=false and lands back on Home with the confirmation flash"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        card = page.locator('section[aria-labelledby="home-frame-state"]')
        card.wait_for(state="visible")
        geometry = page.evaluate(
            """() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return {header: r('.home-state'), row: r('.home-picture-row'),
                        title: r('h1'), status: r('.home-state__status'),
                        switches: r('.home-state__switches')};
            }""")
        assert geometry["title"]["bottom"] <= geometry["header"]["top"] < geometry["row"]["top"]
        if viewport["width"] >= 1024:
            assert geometry["status"]["right"] <= geometry["switches"]["left"]
        else:
            assert geometry["status"]["bottom"] <= geometry["switches"]["top"]
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
        # flash-cleanup.js drops the query string once the banner is shown.
        assert urlsplit(page.url).path == layout.HOME_ROUTE
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
        assert page.locator(SCREEN_BUTTON).get_attribute("aria-checked") == "false"
        headline = page.locator(".home-state__headline").inner_text()
        assert headline.strip() == ("Screen off — the frame stays blank" if lang == "en"
                                    else "Écran éteint — le cadre reste vide")
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
    about", and its text stays readable (not transparent) in the light and dark scheme"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        block = page.locator('.home-battery[role="img"]')
        block.wait_for(state="visible")
        assert (block.get_attribute("aria-label") or "").startswith("Battery about")
        assert block.locator(".home-battery__glyph").is_visible()
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
    (2, 4100, "Next update ≈", False),
    (16, 3700, "Update overdue · expected at", False),
    (30, 3381, "Update overdue · expected at", True),
])
def test_late_states_and_battery_fit_every_viewport(
        new_context, make_app_server, scheme, viewport_name, viewport,
        minutes_ago, battery_mv, wording, amber):
    """on time, briefly late and long overdue each read their own wording; only the long one
    turns the dot amber and shows the Health link; the battery figure and glyph are large, the
    panel keeps the battery between status and switches on desktop, and nothing overflows"""
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
            assert link.is_visible() and link.inner_text() == "See Health"
        figure = page.locator(".home-battery__value").evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)")
        glyph = page.locator(".home-battery__glyph").bounding_box()
        assert figure >= 28 and glyph["width"] >= 64 and glyph["height"] >= 28
        geometry = page.evaluate(
            """() => {
                const r = s => document.querySelector(s).getBoundingClientRect();
                return {status: r('.home-state__status'), battery: r('.home-battery'),
                        switches: r('.home-state__switches'), panel: r('.home-state')};
            }""")
        if viewport["width"] >= 1024:
            assert geometry["status"]["right"] <= geometry["battery"]["left"]
            assert geometry["battery"]["right"] <= geometry["switches"]["left"]
        else:
            assert geometry["status"]["bottom"] <= geometry["battery"]["top"]
            assert geometry["battery"]["bottom"] <= geometry["switches"]["top"]
        overflow = _assert_no_page_overflow(
            page, "home/%s/%s/%s" % (scheme, viewport_name, minutes_ago), viewport["width"])
        assert not overflow, overflow
    finally:
        context.close()


def test_cadence_disclosure_opens_from_the_keyboard(new_context, make_app_server):
    """the cadence summary is a tab stop; Enter reveals the reason and shows it in the viewport"""
    server = make_app_server(seed=_seed_checkin(2, 4100), fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_PHONE)
    try:
        summary = page.locator(".home-state__cadence summary")
        assert summary.inner_text() == "Updates about every 5 min"
        reason = page.locator(".home-state__cadence p")
        assert not reason.is_visible()
        summary.focus()
        page.keyboard.press("Enter")
        assert reason.is_visible()
        assert "does not refresh continuously" in reason.inner_text()
    finally:
        context.close()
