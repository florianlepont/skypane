"""Real-browser checks of the device selector: its layout at 360px and 1280px,
the no-script submit (scripts blocked) and the armed enhancement (scripts
running), both colour schemes, and the 44px hit areas."""
import pytest

from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _hit_area,
    _login, _no_js_page)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

SELECT = "#device-selector-select"
FORM = "form.device-selector"
SUBMIT = "form.device-selector .device-selector__go"
LABEL = "form.device-selector label"
PILL = "form.device-selector .banner__pill"
HIT_FLOOR = 44
# The select's CSS box may differ from the content column by sub-pixel rounding.
COLUMN_TOLERANCE = 2


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    return start_fleet_app(module_app_server_factory)


def _box(page, selector):
    box = page.locator(selector).bounding_box()
    assert box is not None, selector
    return box


def _page_url(app, route):
    return app.server.base_url() + route


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_phone_layout_caption_above_select_pill_below(new_context, fleet_app, scheme):
    """at 360px the caption is on its own line above a 44px select that spans the content
    column, the pill wraps below the select, and nothing scrolls sideways"""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, fleet_app.server.base_url())
        page.goto(_page_url(fleet_app, "/devices/%s/flights" % fleet_app.fleet.landscape.id))
        page.locator(SELECT).wait_for(state="visible")
        label, select, pill = _box(page, LABEL), _box(page, SELECT), _box(page, PILL)
        main = _box(page, "main")
        assert label["y"] + label["height"] <= select["y"] + 1
        assert select["height"] >= HIT_FLOOR
        assert select["x"] >= main["x"] - 1
        assert select["width"] >= main["width"] - 2 * 24 - COLUMN_TOLERANCE
        assert select["x"] + select["width"] <= VIEWPORT_MIN_SUPPORTED["width"]
        assert pill["y"] >= select["y"] + select["height"] - 1
        assert not _assert_no_page_overflow(page, "selector/phone", 360)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_desktop_layout_is_one_row_with_native_controls_at_44px(
        new_context, fleet_app, scheme):
    """at 1280px the caption, select and pill share one row and the select stays 44px"""
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, fleet_app.server.base_url())
        page.goto(_page_url(fleet_app, "/devices/%s/flights" % fleet_app.fleet.landscape.id))
        page.locator(SELECT).wait_for(state="visible")
        label, select, pill = _box(page, LABEL), _box(page, SELECT), _box(page, PILL)
        for part in (label, pill):
            centre = part["y"] + part["height"] / 2
            assert select["y"] <= centre <= select["y"] + select["height"]
        assert label["x"] + label["width"] <= select["x"] + 1
        assert select["x"] + select["width"] <= pill["x"] + 1
        assert select["height"] >= HIT_FLOOR
        assert select["width"] <= 24 * 16 + 1
        assert not _assert_no_page_overflow(page, "selector/desktop", 1280)
    finally:
        context.close()


def test_scripts_blocked_submit_is_visible_and_navigates(new_context, fleet_app):
    """with scripts blocked the submit stays visible, and choosing a frame then submitting
    lands on the same page under that frame"""
    device = fleet_app.fleet.dev_a
    with _no_js_page(
            new_context, fleet_app.server.base_url(), "/flights",
            viewport=VIEWPORT_MIN_SUPPORTED) as page:
        assert page.locator(SUBMIT).is_visible()
        assert "device-selector--armed" not in (page.locator(FORM).get_attribute("class") or "")
        # No page.evaluate on a scripts-blocked page: measure the box directly.
        assert _box(page, SUBMIT)["height"] >= HIT_FLOOR - 1
        assert _box(page, SELECT)["height"] >= HIT_FLOOR - 1
        page.select_option(SELECT, value=device.id)
        with page.expect_navigation():
            page.click(SUBMIT)
        assert page.url.endswith("/devices/%s/flights" % device.id)
        assert page.locator(SELECT).input_value() == device.id
        with page.expect_navigation():
            page.select_option(SELECT, value="live")
            page.click(SUBMIT)
        assert page.url.endswith("/flights") and "/devices/" not in page.url


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_scripts_armed_hides_submit_and_change_navigates(new_context, fleet_app, scheme):
    """with scripts running the form is armed, the submit is hidden, and changing the select
    navigates to the option's own page"""
    device = fleet_app.fleet.dev_b
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, fleet_app.server.base_url())
        page.goto(_page_url(fleet_app, "/airlines"))
        page.locator(SELECT).wait_for(state="visible")
        assert "device-selector--armed" in page.locator(FORM).get_attribute("class")
        assert not page.locator(SUBMIT).is_visible()
        with page.expect_navigation():
            page.select_option(SELECT, value=device.id)
        assert page.url.endswith("/devices/%s/airlines" % device.id)
        assert "device-selector--armed" in page.locator(FORM).get_attribute("class")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_select_focus_outline_is_visible_and_not_accent_filled(new_context, fleet_app, scheme):
    """keyboard focus on the select draws an outline in both themes and the control is not
    filled with the accent colour"""
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme=scheme)
    try:
        page = context.new_page()
        _login(page, fleet_app.server.base_url())
        page.goto(_page_url(fleet_app, "/flights"))
        page.locator(SELECT).wait_for(state="visible")
        # Skip link first, then the selector is the first stop inside the content.
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.id") == SELECT[1:]
        state = page.evaluate(
            """() => {
                const s = getComputedStyle(document.activeElement);
                const accent = getComputedStyle(document.documentElement)
                    .getPropertyValue('--color-accent').trim();
                return {style: s.outlineStyle, width: parseFloat(s.outlineWidth),
                        colour: s.outlineColor, background: s.backgroundColor,
                        accent: accent};
            }""")
        assert state["style"] != "none" and state["width"] > 0, state
        assert state["colour"] not in ("rgba(0, 0, 0, 0)", "transparent"), state
        probe = page.evaluate(
            """(accent) => { const d = document.createElement('i');
                d.style.color = accent; document.body.appendChild(d);
                const c = getComputedStyle(d).color; d.remove(); return c; }""",
            state["accent"])
        assert state["background"] != probe, state
    finally:
        context.close()


def test_hit_areas_at_360px(new_context, fleet_app):
    """the select, and the selector's own container, meet the 44px floor at 360px"""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, fleet_app.server.base_url())
        page.goto(_page_url(fleet_app, "/devices/%s/health" % fleet_app.fleet.landscape.id))
        page.locator(SELECT).wait_for(state="visible")
        area = _hit_area(page, SELECT)
        assert area["visual"][1] >= HIT_FLOOR and area["visual"][0] >= HIT_FLOOR
        assert _box(page, FORM)["height"] >= HIT_FLOOR
        assert _box(page, PILL)["width"] > 0
    finally:
        context.close()
