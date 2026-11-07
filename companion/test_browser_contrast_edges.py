"""Real-browser checks of colour and edges, read from what is painted: a switch whose off track and
thumb hold 3:1 against the card and each other in both themes, the dark map label and the "..."
menu item at 4.5:1, a Location sheet header that wraps instead of ellipsizing, and a floating tab
bar whose shadow is bounded so nothing it paints reaches beyond the gap under it."""
import io
import re

import pytest
from companion_app_server import session_cookie_for_state_dir
from PIL import Image, ImageChops
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, WCAG_AA_UI_COMPONENT, contrast_ratio

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _login, _set_ui_theme)
from place_map_support import Hosts, seed as place_seed
from server import fleet_db

pytestmark = pytest.mark.browser

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

THEMES = ["light", "dark"]


def _seed_switches(state_dir):
    seed = fx.seed_users(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (seed.user_id,))
        conn.commit()
    finally:
        conn.close()


def _hex(pixel):
    return "#%02X%02X%02X" % tuple(pixel[:3])


def _cookie_context(new_context, server, email, scheme, viewport):
    context = new_context(viewport=viewport, color_scheme=scheme)
    name, value = session_cookie_for_state_dir(server.state_dir, email).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    return context


@pytest.mark.parametrize("scheme", THEMES)
def test_switch_track_and_thumb_hold_three_to_one_in_both_states(
        new_context, module_app_server_factory, scheme):
    server = module_app_server_factory(seed=_seed_switches)
    context = _cookie_context(new_context, server, fx.ADMIN_EMAIL, scheme, VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/users")
        page.locator("main").wait_for(state="visible")
        page.evaluate("t => document.documentElement.setAttribute('data-ui-theme', t)", scheme)
        page.wait_for_function(_SETTLED)
        seen = {}
        for state in ("false", "true"):
            switch = page.locator(
                ".users-row button.switch[aria-checked=%s]:not([disabled])" % state).first
            switch.scroll_into_view_if_needed()
            page.wait_for_function(_SETTLED)
            page.wait_for_timeout(400)
            track = switch.locator(".switch__track").bounding_box()
            thumb = switch.locator(".switch__thumb").bounding_box()
            shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
            middle = track["y"] + track["height"] / 2
            card = shot.getpixel((round(track["x"] - 6), round(middle)))
            thumb_pixel = shot.getpixel(
                (round(thumb["x"] + thumb["width"] / 2), round(middle)))
            near_end = (track["x"] + track["width"] - 5 if state == "false" else track["x"] + 5)
            track_pixel = shot.getpixel((round(near_end), round(middle)))
            seen[state] = (card, track_pixel, thumb_pixel)
            assert contrast_ratio(_hex(track_pixel), _hex(card)) >= WCAG_AA_UI_COMPONENT, (
                scheme, state, "track against the card", seen[state])
            assert contrast_ratio(_hex(thumb_pixel), _hex(track_pixel)) >= WCAG_AA_UI_COMPONENT, (
                scheme, state, "thumb against the track", seen[state])
        assert seen["false"][1] != seen["true"][1]
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
def test_the_map_label_holds_four_and_a_half_to_one_on_a_light_tile(
        new_context, make_app_server, scheme):
    server = make_app_server(seed=place_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    Hosts(context)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "en",
                          "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection?airport=LFPO")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        _set_ui_theme(page, scheme)
        page.wait_for_function(_SETTLED)
        label = page.locator(".place-dot--selected .place-dot__label")
        label.wait_for(state="visible")
        ink, fill = label.evaluate(
            "el => [getComputedStyle(el).color, getComputedStyle(el).backgroundColor]")
        assert fill.startswith("rgb(") and not fill.startswith("rgba("), fill
        assert contrast_ratio(_css_hex(ink), _css_hex(fill)) >= WCAG_AA_NORMAL_TEXT
    finally:
        context.close()


def _css_hex(css):
    numbers = [float(p) for p in css[css.index("(") + 1:-1].split(",")]
    return "#%02X%02X%02X" % tuple(round(n) for n in numbers[:3])


def _seed_fleet(state_dir):
    fx.seed_fleet(state_dir)


@pytest.mark.parametrize("scheme", THEMES)
def test_the_reactivate_menu_item_sits_on_an_opaque_panel_with_readable_ink(
        new_context, module_app_server_factory, scheme):
    server = module_app_server_factory(seed=_seed_fleet)
    context = _cookie_context(
        new_context, server, fx.ADMIN_EMAIL, scheme, {"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/fleet")
        page.locator("main").wait_for(state="visible")
        page.evaluate("t => document.documentElement.setAttribute('data-ui-theme', t)", scheme)
        page.wait_for_function(_SETTLED)
        item = page.locator(".fleet-block--others a.row-menu__item", has_text="Re-activate").first
        item.evaluate(
            "el => { for (let d = el.closest('details'); d;"
            " d = d.parentElement && d.parentElement.closest('details')) d.open = true; }")
        item.wait_for(state="visible")
        ink = item.evaluate("el => getComputedStyle(el).color")
        panel = item.locator("xpath=ancestor::*[contains(@class,'row-menu__panel')][1]")
        fill = panel.evaluate("el => getComputedStyle(el).backgroundColor")
        assert fill.startswith("rgb(") and not fill.startswith("rgba("), fill
        assert contrast_ratio(_css_hex(ink), _css_hex(fill)) >= WCAG_AA_NORMAL_TEXT
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
def test_the_location_sheet_header_wraps_and_the_sheet_stays_compact(
        new_context, make_app_server, scheme):
    server = make_app_server(seed=place_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    Hosts(context)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "en",
                          "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection?airport=LFPO")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        _set_ui_theme(page, scheme)
        page.wait_for_function(_SETTLED)
        facts = page.evaluate(
            """() => {
              const cut = (el) => el.scrollWidth > el.clientWidth + 0.5
                || getComputedStyle(el).textOverflow === 'ellipsis';
              const parts = [...document.querySelectorAll(
                '.place-sheet .place-chosen__name, .place-sheet .place-chosen .section-caption')];
              const sheet = document.querySelector('.place-sheet').getBoundingClientRect();
              return {cut: parts.filter(cut).length, parts: parts.length,
                      height: sheet.height, limit: window.innerHeight * 0.28,
                      titles: [...document.querySelectorAll('.place-sheet .runway-card')]
                        .map((el) => el.title)}; }""")
        assert facts["parts"] == 2 and facts["cut"] == 0
        assert facts["height"] <= facts["limit"] + 0.5
        assert facts["titles"] and all(" m" in title for title in facts["titles"])
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("inset", [34, 60])
def test_the_tab_bar_shadow_never_paints_beyond_the_gap_below_the_bar(
        new_context, module_app_server_factory, scheme, inset):
    server = module_app_server_factory(seed=_seed_fleet)
    context = _cookie_context(new_context, server, fx.ADMIN_EMAIL, scheme, VIEWPORT_PHONE)
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/fleet")
        page.locator(".tab-bar").wait_for(state="visible")
        page.evaluate("t => document.documentElement.setAttribute('data-ui-theme', t)", scheme)
        page.evaluate(
            "px => document.documentElement.style.setProperty('--safe-bottom', px + 'px')", inset)
        page.wait_for_function(_SETTLED)
        page.wait_for_timeout(300)
        bar = page.locator(".tab-bar").bounding_box()
        gap = page.evaluate("() => window.innerHeight") - (bar["y"] + bar["height"])
        assert gap == pytest.approx(6 + inset, abs=0.5)
        shown = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
        page.evaluate("() => { document.querySelector('.tab-bar').style.visibility = 'hidden'; }")
        page.wait_for_timeout(300)
        hidden = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
        first_row = round(bar["y"] + bar["height"]) + 14
        below = (0, first_row, shown.width, shown.height)
        assert ImageChops.difference(
            shown.crop(below), hidden.crop(below)).getbbox() is None, (
            "the bar paints more than 14px under itself")
        beside = (0, round(bar["y"]), 3, shown.height)
        assert ImageChops.difference(
            shown.crop(beside), hidden.crop(beside)).getbbox() is None, (
            "the bar paints into the screen-edge margin")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", THEMES)
def test_the_bar_shadow_is_soft_not_a_hard_band(new_context, module_app_server_factory, scheme):
    server = module_app_server_factory(seed=_seed_fleet)
    context = _cookie_context(new_context, server, fx.ADMIN_EMAIL, scheme, VIEWPORT_PHONE)
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/fleet")
        page.locator(".tab-bar").wait_for(state="visible")
        shadow = page.evaluate(
            "() => getComputedStyle(document.querySelector('.tab-bar'), '::before').boxShadow")
        gap = page.evaluate(
            "() => parseFloat(getComputedStyle(document.documentElement)"
            ".getPropertyValue('--tab-bar-gap'))")
        reach = 0.0
        for layer in _outer_shadows(shadow):
            offset_y, blur, spread = layer
            reach = max(reach, offset_y + blur + spread)
        assert 0 < reach <= gap, (shadow, reach, gap)
    finally:
        context.close()


def _outer_shadows(value):
    """(offset-y, blur, spread) of each non-inset layer of a computed box-shadow."""
    result = []
    for layer in re.split(r",\s*(?=rgba?\()", value):
        if "inset" in layer:
            continue
        lengths = [float(x) for x in re.findall(r"(-?\d+(?:\.\d+)?)px", layer)]
        assert len(lengths) >= 3, layer
        result.append((lengths[1], lengths[2], lengths[3] if len(lengths) > 3 else 0.0))
    return result
