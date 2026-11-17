"""Real-browser checks of Home's hero and Frame group: the hero sits above the groups
(the Frame group below the hero at every width), the two switches have 44px targets and nothing overflows from 1280
down to 360 px, keyboard operation (Space and Enter) with a visible focus
indicator, the persisted effect plus confirmation flash after each switch, the
same flow with scripts blocked, the battery dial's accessible name, and a
visible unchecked switch thumb in the dark theme."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import pytest

from companion import auth, layout
from companion_app_server import session_cookie_for_state_dir
from provisioned_fleet import USER_A_EMAIL, device_dir, provision_fleet
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
def _assert_zone_arrangement(page, label):
    """the hero and the Frame group (the two switch rows) stay inside the content column and
    never overlap: the group sits below the hero at every width (the personal Home has no
    battery zone)"""
    geometry = page.evaluate(
        """() => {
            const r = s => document.querySelector(s).getBoundingClientRect();
            return {status: r('.hero__body'), switches: r('.home-state__switches .group'),
                    panel: r('main'), viewport: window.innerWidth};
        }""")
    status, switches, panel = geometry["status"], geometry["switches"], geometry["panel"]
    for zone in (status, switches):
        assert panel["left"] - 1 <= zone["left"] and zone["right"] <= panel["right"] + 1, label
        assert 0 <= zone["left"] and zone["right"] <= geometry["viewport"], label
    assert status["bottom"] <= switches["top"] + 1, label
    assert not page.locator(".home-battery").count(), label


SCREEN_BUTTON = 'form[action="/quick/display"] button[role="switch"]'
QUIET_BUTTON = 'form[action="/quick/quiet-hours"] button[role="switch"]'
# The same switches under a frame prefix (a user's Home lives at /devices/<id>/).
SCOPED_SCREEN_BUTTON = 'form[action$="/quick/display"] button[role="switch"]'
SCOPED_QUIET_BUTTON = 'form[action$="/quick/quiet-hours"] button[role="switch"]'
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
    """the hero sits above the Frame group, the two arrange for the width, both
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
                return {header: r('.home-state'), row: r('.home-state__switches'), title: r('h1')};
            }""")
        # The title is the frame name inside the hero, above the Frame group.
        assert geometry["header"]["top"] <= geometry["title"]["top"] < geometry["row"]["top"]
        assert geometry["title"]["bottom"] <= geometry["header"]["bottom"] + 1
        _assert_zone_arrangement(page, viewport_name)
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
        assert _has_visible_focus_indicator(page, ".home-switch__window"), (
            "no focus ring on the quiet-hours window link")
        page.keyboard.press("Tab")
        assert _has_visible_focus_indicator(page, QUIET_BUTTON), "no focus ring on the quiet switch"
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Shift+Tab")
        assert _has_visible_focus_indicator(page, SCREEN_BUTTON), "no focus ring on the screen switch"
        page.evaluate("() => { window.__noReload = true; }")
        page.keyboard.press("Space")
        # The switch flips in place and the headline follows without a page load.
        page.wait_for_function(
            "() => document.querySelector('.home-state__pill')"
            " && document.querySelector('.home-state__detail')"
            " && document.querySelector('.home-state__detail').textContent.trim() !== ''",
            timeout=15000)
        assert page.evaluate("() => window.__noReload === true")
        assert urlsplit(page.url).path == layout.HOME_ROUTE
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
        assert page.locator(SCREEN_BUTTON).get_attribute("aria-checked") == "false"
        headline = page.locator(".home-state__pill").inner_text()
        dot_word = page.get_attribute(".home-state__dot", "aria-label")
        assert headline.strip() == dot_word
        detail = page.locator(".home-state__detail").inner_text()
        assert detail.strip() == ("The frame stays blank" if lang == "en" else "Le cadre reste vide")
    finally:
        context.close()


def test_enter_on_the_quiet_switch_posts_and_the_header_follows(new_context, make_app_server):
    """Enter on the quiet-hours switch (scripts on) posts over fetch and persists: the switch
    reads checked in place, with no page load"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_DESKTOP)
    try:
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "false"
        page.locator(QUIET_BUTTON).focus()
        page.evaluate("() => { window.__noReload = true; }")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "s => document.querySelector(s).getAttribute('aria-checked') === 'true'"
            " && !document.querySelector('[data-quick-region][data-pending]')",
            arg=QUIET_BUTTON, timeout=15000)
        assert page.evaluate("() => window.__noReload === true")
        assert page.locator(FLASH).count() == 0
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
        assert page.locator(QUIET_BUTTON).get_attribute("aria-checked") == "true"
    finally:
        context.close()


def test_clicking_the_row_toggles_the_switch(new_context, make_app_server):
    """the whole switch row is the tap target: a click on the row's left edge, away from the
    track, still presses the switch (in place, no page load)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_PHONE)
    try:
        page.evaluate("() => { window.__noReload = true; }")
        page.locator(".home-switch--on").first.click(position={"x": 12, "y": 28})
        page.wait_for_function(
            "() => document.querySelector('" + SCREEN_BUTTON + "')"
            ".getAttribute('aria-checked') === 'false'", timeout=15000)
        page.wait_for_function(
            "() => !document.querySelector('[data-quick-region][data-pending]')", timeout=15000)
        assert page.evaluate("() => window.__noReload === true")
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_battery_is_read_on_health_not_on_the_personal_home(new_context, make_app_server, scheme):
    """an administrator's personal Home carries no battery block; the seeded reading is read on
    the Console Health page's Battery row instead, with its value readable (not transparent) in
    the light and dark scheme"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(".home-state").wait_for(state="visible")
        assert page.locator(".home-battery").count() == 0
        page.goto(server.base_url() + "/fleet")
        row = page.locator('details.health-row[id$="battery"]')
        row.wait_for(state="visible")
        assert "battery" in row.inner_text().lower()
        value = row.locator(".health-row__value").first
        assert value.evaluate("el => getComputedStyle(el).color") != "rgba(0, 0, 0, 0)"
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
    (2, 4100, "Next refresh in", False),
    (16, 3700, None, True),
    (30, 3381, None, True),
])
def test_late_states_fit_every_viewport_without_a_battery_block(
        new_context, make_app_server, scheme, viewport_name, viewport,
        minutes_ago, battery_mv, wording, amber):
    """on time keeps its next-update line; late and long overdue say it once, in the notification
    above the hero, with no second "Update overdue" line; only the on-time one keeps
    the green dot, a late or long overdue frame turns the dot amber, and none of them links to a
    Health page; the personal Home carries no battery block for an administrator, the zones
    arrange for the card's width, and nothing overflows"""
    server = make_app_server(seed=_seed_checkin(minutes_ago, battery_mv), fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.locator(".home-state").wait_for(state="visible")
        if wording is not None:
            assert wording in page.locator(".home-state__next").inner_text()
        else:
            assert page.locator(".home-state__next").count() == 0
            assert "Update overdue" not in page.locator("main").inner_text()
            assert page.locator(".home-facts").inner_text().strip() != ""
        assert page.locator(".home-state__dot.dot--warn").count() == (1 if amber else 0)
        assert page.locator('.home-state a[href$="/health"]').count() == 0
        if amber:
            assert "home-state--warn" in page.locator(".home-state").get_attribute("class")
        _assert_zone_arrangement(page, "%s/%s" % (viewport_name, minutes_ago))
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
        page.locator(".home-state__pill").click()
        # The rename pencil in the title row comes before the info button in tab order.
        for _ in range(2):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement.classList.contains('info-tip__button')"):
                break
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
                // The bubble is translucent glass: measure its fill composited over the page.
                const sky = getComputedStyle(document.documentElement)
                    .getPropertyValue('--sky-mid').trim().match(/[0-9a-f]{2}/gi)
                    .map(h => parseInt(h, 16));
                const fill = style.backgroundColor.match(/[\\d.]+/g).map(Number);
                const alpha = fill.length > 3 ? fill[3] : 1;
                const over = fill.slice(0, 3).map((v, i) => alpha * v + (1 - alpha) * sky[i]);
                const [x, y] = [lum(style.color), lum('rgb(' + over.join(',') + ')')]
                    .sort((p, q) => q - p);
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
        assert page.locator(".home-state__dot").get_attribute("aria-label") == "Resting"
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


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_quiet_hours_link_owns_a_44px_square_around_it_at_every_width(
        new_context, make_app_server, lang, viewport_name, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        link = page.locator(".home-switch__window")
        link.wait_for(state="visible")
        link.scroll_into_view_if_needed()
        page.wait_for_function(
            """() => { if (document.readyState !== 'complete') return false;
              const el = document.querySelector('.home-switch__window');
              const r = el.getBoundingClientRect();
              const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return hit === el || el.contains(hit); }""", timeout=10000)
        page.wait_for_function(
            "() => document.getAnimations().every((a) => a.playState !== 'running'"
            " || a.effect.getComputedTiming().iterations === Infinity)")
        reach = page.evaluate(
            """() => { const el = document.querySelector('.home-switch__window');
              const r = el.getBoundingClientRect();
              const x = r.left + r.width / 2, cy = r.top + r.height / 2;
              const owns = (px, py) => { const n = document.elementFromPoint(px, py);
                return !!n && el.contains(n); };
              let up = 0, down = 0, left = 0, right = 0;
              while (up < 64 && owns(x, cy - up - 1)) up++;
              while (down < 64 && owns(x, cy + down + 1)) down++;
              while (left < 64 && owns(r.left - left - 1, cy)) left++;
              while (right < 64 && owns(r.right + right, cy)) right++;
              return {height: up + down + 1, width: r.width + left + right}; }""")
        assert reach["height"] >= 44 and reach["width"] >= 44, (viewport_name, lang, reach)
    finally:
        context.close()


@pytest.mark.parametrize("viewport_name,viewport", [VIEWPORTS[0], VIEWPORTS[-2]], ids=["1280", "390"])
def test_quiet_hours_window_link_opens_the_dialog_without_toggling(
        new_context, make_app_server, viewport_name, viewport):
    """the quiet-hours window is a keyboard-focusable link with a 44px target; activating it with
    the keyboard opens the Quiet hours dialog and leaves the switch untouched, while a tap
    elsewhere on the row still flips the switch"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", viewport)
    try:
        link = page.locator(".home-switch__window")
        reach = page.evaluate(
            """() => { const el = document.querySelector('.home-switch__window');
              const r = el.getBoundingClientRect();
              const x = r.left + r.width / 2; let up = 0, down = 0;
              const cy = r.top + r.height / 2;
              const owns = (y) => { const n = document.elementFromPoint(x, y);
                return !!n && el.contains(n); };
              while (up < 64 && owns(cy - up - 1)) up++;
              while (down < 64 && owns(cy + down + 1)) down++;
              return up + down + 1; }""")
        assert reach >= 44, reach
        link.focus()
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('.home-switch__window')")
        assert _has_visible_focus_indicator(page, ".home-switch__window")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.querySelector('#dlg-quiet-hours').open"
            " && document.activeElement.matches('#dlg-quiet-hours .modal__title')", timeout=10000)
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is False
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('#dlg-quiet-hours').open"
            " && document.activeElement.matches('.home-switch__window')", timeout=10000)
        page.eval_on_selector(
            "#home-switch-quiet-label", "el => el.scrollIntoView({block: 'center'})")
        label = page.locator("#home-switch-quiet-label").bounding_box()
        page.mouse.click(label["x"] + 4, label["y"] + 4)
        page.locator(QUIET_BUTTON + '[aria-checked="true"]').wait_for()
        page.wait_for_function(
            "() => !document.querySelector('[data-quick-region][data-pending]')", timeout=15000)
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
    finally:
        context.close()


# --- a plain user's Home: one dot, no battery tile, no attention bar ----------

STALE_TS = "2026-01-01T00:00:00+00:00"


def _seed_user_fleet(mode):
    """A provisioned fleet (user A owns two frames) whose first frame is fresh, never seen,
    long silent or switched off, by `mode`."""
    def seed(state_dir):
        fleet = provision_fleet(state_dir)
        directory = device_dir(state_dir, fleet.a1)
        stamp = {"fresh": datetime.now(timezone.utc).isoformat(), "silent": STALE_TS}.get(mode)
        if stamp is not None:
            with history_db.open_db(directory) as conn:
                history_db.record_device_health(
                    conn, stamp, battery_mv=4000, fw_version="1.0.0",
                    boot_reason="wake", rssi="-60")
        if mode == "off":
            with history_db.open_db(directory) as conn:
                history_db.record_device_health(
                    conn, datetime.now(timezone.utc).isoformat(), battery_mv=4000,
                    fw_version="1.0.0", boot_reason="wake", rssi="-60")
            device_config.save_device_config(directory, display_enabled=False)
        seed.fleet = fleet
    return seed


def _open_user_home(new_context, server, fleet, lang="en", **context_args):
    context = new_context(**context_args)
    base = server.base_url()
    pair = session_cookie_for_state_dir(server.state_dir, USER_A_EMAIL)
    name, value = pair.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + "/devices/%s/" % fleet.a1)
    page.locator(".home-state").wait_for(state="visible")
    # The cards enter with a finite animation; measure only once it has ended.
    page.wait_for_function(
        "() => document.readyState === 'complete' && document.getAnimations().every("
        "a => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
    return context, page


@pytest.mark.parametrize("mode,word,tone", [
    ("fresh", "Online", "ok"),
    ("off", "Resting", "off"),
    ("silent", "No contact", "error"),
    ("never", "Not seen yet", "warn"),
])
def test_user_home_dot_names_the_state_and_links_to_no_health_page(
        new_context, make_app_server, mode, word, tone):
    """the dot's accessible name uses the shared state words; whatever the colour, the card
    carries no link to a Health page"""
    seed = _seed_user_fleet(mode)
    server = make_app_server(seed=seed)
    context, page = _open_user_home(new_context, server, seed.fleet, viewport=VIEWPORT_DESKTOP)
    try:
        dot = page.locator(".home-state__dot")
        assert dot.count() == 1
        assert dot.get_attribute("aria-label") == word
        assert dot.get_attribute("role") == "img"
        assert "home-state--%s" % tone in page.locator(".home-state").get_attribute("class")
        assert page.locator('.home-state a[href$="/health"]').count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport_name,viewport", [VIEWPORTS[0], VIEWPORTS[-1]], ids=["1280", "360"])
def test_user_home_layout_has_the_frame_button_first_and_no_battery_tile(
        new_context, make_app_server, viewport_name, viewport, scheme, lang):
    """a user with two frames sees the frame button above or level with the title, the hero, the Frame group
    and the recent flights in that order; there is no battery tile and no attention bar; the
    switches keep 44px targets and nothing overflows"""
    seed = _seed_user_fleet("silent")
    server = make_app_server(seed=seed)
    context, page = _open_user_home(
        new_context, server, seed.fleet, lang=lang, viewport=viewport, color_scheme=scheme)
    try:
        assert page.locator(".home-battery").count() == 0
        assert page.locator(".home-action").count() == 0
        tops = page.evaluate(
            """() => ['details.frame-menu', '.home-state', '.home-state h1',
                      '.home-state__switches', '.home-section[aria-labelledby="home-flights"]']
                .map(s => document.querySelector(s).getBoundingClientRect().top)""")
        # The title is the frame name inside the hero: the frame button is above or level with
        # the hero, whose title comes before the Frame group and the recent flights.
        assert tops[0] <= tops[1] <= tops[2] < tops[3] < tops[4]
        for selector in (SCOPED_SCREEN_BUTTON, SCOPED_QUIET_BUTTON):
            box = page.locator(selector).bounding_box()
            assert box["height"] >= 44 and box["x"] + box["width"] <= viewport["width"]
        assert page.locator('.home-state a[href$="/health"]').count() == 0
        _assert_zone_arrangement(page, "user-home")
        assert not _assert_no_page_overflow(
            page, "user-home/%s/%s/%s" % (scheme, viewport_name, lang), viewport["width"])
    finally:
        context.close()


def _wait_controls_settled(page):
    """A switch owns its own centre (the page change transition is over) and nothing is pending."""
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    page.wait_for_function(
        "s => { const e = document.querySelector(s); if (!e) return false;"
        " const r = e.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return hit === e || e.contains(hit); }", arg=SCREEN_BUTTON, timeout=15000)
    page.wait_for_function(
        "() => document.getAnimations().every(a => a.effect"
        " && a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')",
        timeout=15000)


def test_a_switch_flips_in_place_and_the_state_regions_follow(new_context, make_app_server):
    """pressing the screen switch posts over fetch: the page is never reloaded (a marker on window
    survives, no navigation happens), the switch, the headline and the saved config all change,
    and the quiet-hours switch then does the same"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_PHONE)
    try:
        _wait_controls_settled(page)
        navigations = []
        page.on("framenavigated", lambda frame: navigations.append(frame.url))
        page.evaluate("() => { window.__noReload = true; }")
        page.locator(SCREEN_BUTTON).click()
        page.wait_for_function(
            "() => document.querySelector('.home-state__detail')"
            " && document.querySelector('.home-state__detail').textContent.includes('stays blank')",
            timeout=15000)
        assert page.get_attribute(SCREEN_BUTTON, "aria-checked") == "false"
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
        page.locator(SCREEN_BUTTON).click()
        page.wait_for_function(
            "() => !document.querySelector('.home-state__detail')", timeout=15000)
        page.locator(QUIET_BUTTON).click()
        page.wait_for_function(
            "s => document.querySelector(s).getAttribute('aria-checked') === 'true'"
            " && !document.querySelector('[data-quick-region][data-pending]')",
            arg=QUIET_BUTTON, timeout=15000)
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
        assert page.evaluate("() => window.__noReload === true")
        assert navigations == []
    finally:
        context.close()


def test_a_refused_switch_flips_back_and_says_so(new_context, make_app_server):
    """when the server answers with anything but 204 the switch returns to what it was and the
    failure toast appears, still without a page load"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_DESKTOP)
    try:
        _wait_controls_settled(page)
        page.route("**/quick/display", lambda route: route.fulfill(status=500, body="no"))
        page.evaluate("() => { window.__noReload = true; }")
        page.locator(SCREEN_BUTTON).click()
        page.wait_for_function(
            "() => !!document.querySelector('.toast-region [role=alert], .toast-region .toast')",
            timeout=15000)
        assert page.get_attribute(SCREEN_BUTTON, "aria-checked") == "true"
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is True
        assert page.evaluate("() => window.__noReload === true")
    finally:
        context.close()
