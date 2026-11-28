#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Browser checks for the SVG-drawing scenario group: the battery gauge, the battery chart's
area/line/threshold and the absence of a regularity grid, all on Health, plus the rows card's
alignment and width.

Two module-scoped, read-only servers are shared across these checks: `server` (the default
seed, whose readings stay far above the low-battery mark, so the chart carries its caption
instead of the line) and `near` (readings that approach the mark, so the dashed line, its
label and the tinted zone are drawn). None of the tests below POSTs or otherwise mutates
server state, so sharing them is safe under xdist.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
from skypane_contrast_check import (
    contrast_ratio,
)
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _RING_INK_PROBE,
    _assert_no_page_overflow, _computed_paint, _login, _no_js_page,
    _set_ui_theme, seed_state_dir,
)
from server import history_db

pytestmark = pytest.mark.browser

VISIBLE_VIEW = ".battery-chart__view:not([hidden])"

# The battery gauge, measured where it actually has to be correct: a real browser, both
# themes, the narrowest supported screen, and with scripts off.

# Scoped to the Battery row: the Identification row carries a ring.
RING_FIGURE = "#health-row-battery svg.drawing__figure"
RING_VALUE = "#health-row-battery svg.drawing__figure .drawing-arc-value"
RING_TRACK = "#health-row-battery svg.drawing__figure .drawing-arc-track"
FRAME_ROUTE = "/fleet?frame=live&view=battery"
RING_PAGES = (("Fleet", FRAME_ROUTE),)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture the battery gauge and battery chart checks
    measure against — module-scoped because every test in this group only GETs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _seed_near_the_mark(state_dir):
    """The default seed with its battery history replaced by one that comes within a step of
    the low-battery mark."""
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        conn.execute("DELETE FROM device_health")
        for day in range(40, -1, -1):
            history_db.record_device_health(
                conn, (now - timedelta(days=day, minutes=2)).isoformat(timespec="seconds"),
                battery_mv=3570 + day * 4, fw_version="1.0.0", boot_reason="wake", rssi="-60")


@pytest.fixture(scope="module")
def near(module_app_server_factory):
    return module_app_server_factory(seed=_seed_near_the_mark, fake_providers=True)


@pytest.mark.parametrize("label,route", RING_PAGES, ids=[p[0] for p in RING_PAGES])
def test_the_gauge_paints_a_theme_token_in_both_themes(new_context, server, label, route):
    """The battery gauge's value arc resolves to a real theme token on both pages in both
    themes: never the SVG default fill or stroke, never the same paint as its own track,
    and never the same value in light and dark.
    """
    # A source scan can see that the arc carries class="drawing-ring-value"; it cannot see
    # what that class resolves to. getComputedStyle has already run the cascade, resolved
    # currentColor against the inherited colour and substituted the theme's custom property,
    # so this is the only way to tell a token-painted shape from one that fell through to the
    # SVG default. Both themes are sampled here, since the two rings are two sizes of one
    # emitter and a single sample would not notice if only one of them inherited its colour.
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        seen = {}
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            value = _computed_paint(page, RING_VALUE)
            track = _computed_paint(page, RING_TRACK)
            if "stroke" in value["svg_default"]:
                raise AssertionError(
                    "%s in %s: the ring's value arc resolves stroke to the "
                    "SVG default %r — it inherited no colour from the "
                    "cascade and is painting nothing a theme chose"
                    % (label, theme, value["stroke"]))
            if "fill" in value["svg_default"]:
                raise AssertionError(
                    "%s in %s: the ring's value arc resolves fill to the SVG "
                    "default black, which is correct in one theme and "
                    "invisible in the other" % (label, theme))
            if value["stroke"] == track["stroke"]:
                raise AssertionError(
                    "%s in %s: the value arc and the track resolve to the "
                    "same paint (%r), so the gauge reads as a plain circle "
                    "with no reading in it"
                    % (label, theme, value["stroke"]))
            seen[theme] = value["stroke"]
        light = seen[UI_THEMES_EXPLICIT[0]]
        dark = seen[UI_THEMES_EXPLICIT[1]]
        if light == dark:
            raise AssertionError(
                "%s: the ring's value arc resolves to %r in BOTH themes. The "
                "status token it paints through is declared separately for "
                "light and dark, so an unchanged value means the arc is not "
                "reaching that token at all" % (label, light))
    finally:
        context.close()


@pytest.mark.parametrize("label,route", RING_PAGES, ids=[p[0] for p in RING_PAGES])
def test_the_gauges_viewbox_contains_its_own_stroked_geometry(new_context, server, label, route):
    """The battery ring's viewBox contains its own stroked geometry on both pages: each
    arc's browser-reported bounding box, expanded by half its resolved stroke width on
    every side, lies inside the box the emitter declared.
    """
    # A stroked arc extends half its stroke width beyond the nominal radius, which is the
    # single most common way a ring gets clipped by its own box, so the geometry comes back
    # from the browser rather than from arithmetic on the emitter's constants: getBBox() for
    # the path's own box and the resolved stroke-width from getComputedStyle, expanded by
    # half on every side. getBBox() deliberately excludes the stroke (SVG 1.1 behaviour), so
    # the half-stroke is added here, in the open, since that half-stroke is the property
    # under test.
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        box = page.evaluate(_RING_INK_PROBE, {"selector": RING_FIGURE})
        if box is None:
            raise AssertionError(
                "%s: no %s on the page — with none, this check measures "
                "nothing" % (label, RING_FIGURE))
        if not box["shapes"]:
            raise AssertionError("%s: the ring figure holds no drawn shape" % label)
        side = box["viewBox"]
        for shape in box["shapes"]:
            if shape["strokeWidth"] <= 0:
                raise AssertionError(
                    "%s: %s resolves a stroke-width of %r — an arc with no "
                    "stroke draws nothing at all"
                    % (label, shape["cls"], shape["strokeWidth"]))
            left, top, right, bottom = shape["inked"]
            if (left < -0.01 or top < -0.01
                    or right > side[0] + 0.01 or bottom > side[1] + 0.01):
                raise AssertionError(
                    "%s: %s inks [%.3f, %.3f, %.3f, %.3f], outside its own "
                    "viewBox 0 0 %g %g — the stroke is clipped at the box "
                    "edge, which is the ring's own half-stroke overhang "
                    "going unaccounted for"
                    % (label, shape["cls"], left, top, right, bottom,
                       side[0], side[1]))
    finally:
        context.close()


def test_the_gauge_costs_no_width_no_height_and_no_script(new_context, server):
    """At the 360px floor the ring costs nothing it must not: the page's body does not scroll
    sideways, and the ring still renders, and still paints a dark-mode token, with scripts
    blocked through _no_js_page().
    """
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        for label, route in RING_PAGES:
            page.goto(server.base_url() + route)
            if page.locator(RING_VALUE).count() != 1:
                raise AssertionError(
                    "%s: expected exactly one ring value arc at 360px, got %d"
                    % (label, page.locator(RING_VALUE).count()))
            message = _assert_no_page_overflow(
                page, label, VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)

        # The ring is complete markup in the first response, so it must arrive whole with
        # scripts blocked; asking through _no_js_page() composes with the existing no-JS
        # floor instead of being a second, private way to turn scripts off.
        for label, route in RING_PAGES:
            with _no_js_page(new_context, server.base_url(), route,
                             viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
                if blocked.locator(RING_VALUE).count() != 1:
                    raise AssertionError(
                        "%s with scripts blocked: expected exactly one ring "
                        "value arc, got %d — the ring is server-rendered SVG "
                        "and owes nothing to a script (D-09)"
                        % (label, blocked.locator(RING_VALUE).count()))
                _set_ui_theme(blocked, UI_THEMES_EXPLICIT[1])
                paint = _computed_paint(blocked, RING_VALUE)
                if paint["svg_default"]:
                    raise AssertionError(
                        "%s with scripts blocked, in %s: the ring resolves %r to "
                        "the SVG default — 'correct in dark mode with scripts "
                        "off' is the combination most likely to be wrong, which "
                        "is why it is the one measured"
                        % (label, UI_THEMES_EXPLICIT[1], paint["svg_default"]))
    finally:
        context.close()


# The battery chart's drawn parts, measured where they have to be correct.

CHART_AREA = ".sparkline-area"
CHART_LINE = ".sparkline-line"
CHART_MARK = ".sparkline-mark"
CHART_THRESHOLD = ".sparkline-threshold"
CHART_ZONE = ".sparkline-zone"
CHART_LEGEND = ".sparkline-legend"
CHART_SWATCH = ".sparkline-swatch"
CHART_TEXT = ".sparkline-text, .sparkline-text--strong"

# The area is a translucent fill, so its resolved `fill` is not what lands on screen: what
# lands is that colour composited over the card behind it at the resolved `fill-opacity`.
# Composited here and compared against the card's own resolved background through the app's
# own contrast formula. The 1.20:1 floor is not WCAG's 3:1, which is for a UI component a
# user must find and identify; this is a wash under a line that already carries the data
# (and fades out downwards), and at 3:1 it would be a block of ink. What it must not be is
# present but invisible, technically painted, visually absent.
CHART_AREA_MIN_CONTRAST = 1.20


def _composite_over(fg_text, alpha, bg_text):
    fg = [float(v) for v in re.findall(r"[\d.]+", fg_text)[:3]]
    bg = [float(v) for v in re.findall(r"[\d.]+", bg_text)[:3]]
    if len(fg) != 3 or len(bg) != 3:
        raise AssertionError(
            "expected two rgb() colours to composite, got %r over %r"
            % (fg_text, bg_text))
    return "#%02X%02X%02X" % tuple(
        int(round(alpha * f + (1 - alpha) * b)) for f, b in zip(fg, bg))


def _as_hex(text):
    return "#%02X%02X%02X" % tuple(
        int(round(float(v))) for v in re.findall(r"[\d.]+", text)[:3])


def test_the_charts_area_mark_and_threshold_paint_real_tokens_in_both_themes(page, near):
    """The battery chart's area, line, mark, threshold line and zone each resolve to a real
    theme token in both themes: never the SVG default, the area/line/mark sharing one
    currentColor ink while the threshold deliberately does not, and the area's composite over
    the card clearing a 1.20:1 floor so it is visible and not merely painted.
    """
    # Three different questions are asked, because "not the default" alone would be green for
    # a shape that is the same in both themes, and "differs between themes" alone would be
    # green for a shape painted the wrong colour consistently: the area, the line and the
    # mark must resolve to the same ink, since all three are currentColor; the threshold must
    # resolve to something else, since a judgement painted in the data's own ink is a
    # judgement nobody can see; and every one of them must move when the theme does.
    _login(page, near.base_url())
    page.goto(near.base_url() + FRAME_ROUTE)
    page.wait_for_selector(VISIBLE_VIEW + " " + CHART_THRESHOLD, state="attached")
    seen = {}
    for theme in UI_THEMES_EXPLICIT:
        _set_ui_theme(page, theme)
        view = VISIBLE_VIEW + " "
        area = _computed_paint(page, view + CHART_AREA, ("fill", "fill-opacity"))
        line = _computed_paint(page, view + CHART_LINE, ("stroke",))
        mark = _computed_paint(page, view + CHART_MARK, ("fill",))
        threshold = _computed_paint(page, view + CHART_THRESHOLD, ("stroke",))
        zone = _computed_paint(page, view + CHART_ZONE, ("fill",))
        # The card is translucent glass: its surface is its fill composited over the sky
        # behind it (measured on the middle stop).
        card = page.evaluate(
            "() => { const html = getComputedStyle(document.documentElement);"
            " const fill = getComputedStyle(document.querySelector('.health-rows'))"
            ".backgroundColor.match(/[\\d.]+/g).map(Number);"
            " const alpha = fill.length > 3 ? fill[3] : 1;"
            " const sky = html.getPropertyValue('--sky-mid').trim();"
            " const mixed = [0, 1, 2].map(i => Math.round(alpha * fill[i]"
            " + (1 - alpha) * parseInt(sky.substr(1 + 2 * i, 2), 16)));"
            " return 'rgb(' + mixed.join(', ') + ')'; }")
        for name, paint, prop in (
                ("area", area, "fill"), ("line", line, "stroke"), ("mark", mark, "fill"),
                ("threshold", threshold, "stroke"), ("zone", zone, "fill")):
            if prop in paint["svg_default"]:
                raise AssertionError(
                    "in %s the chart's %s resolves %s to the SVG default (%r) — it "
                    "inherited no colour at all" % (theme, name, prop, paint[prop]))
        if not (area["fill"] == line["stroke"] == mark["fill"]):
            raise AssertionError(
                "in %s the area (%r), the line (%r) and the mark (%r) are three "
                "different inks — all three are meant to be currentColor, which is "
                "what makes dark mode correct by construction rather than by a "
                "second colour value"
                % (theme, area["fill"], line["stroke"], mark["fill"]))
        if threshold["stroke"] == line["stroke"]:
            raise AssertionError(
                "in %s the threshold resolves to the trend line's own ink (%r) — a "
                "judgement painted in the data's colour is not a judgement anyone "
                "can read" % (theme, threshold["stroke"]))
        if zone["fill"] != threshold["stroke"]:
            raise AssertionError(
                "in %s the zone (%r) and the threshold line (%r) are different "
                "colours" % (theme, zone["fill"], threshold["stroke"]))

        alpha = float(area["fill-opacity"])
        if not (0.0 < alpha < 1.0):
            raise AssertionError(
                "in %s the area's fill-opacity is %r — an opaque area hides the "
                "grid and the threshold beneath it" % (theme, alpha))
        composite = _composite_over(area["fill"], alpha, card)
        ratio = contrast_ratio(composite, _as_hex(card))
        if ratio < CHART_AREA_MIN_CONTRAST:
            raise AssertionError(
                "in %s the area composites to %s over the card's %s for a contrast "
                "of %.3f:1, under this check's %.2f:1 floor — at that opacity the "
                "area is painted and invisible, which is the exact failure mode of "
                "this feature" % (theme, composite, _as_hex(card), ratio,
                                  CHART_AREA_MIN_CONTRAST))
        seen[theme] = {
            "ink": area["fill"], "alpha": alpha, "threshold": threshold["stroke"],
            "card": card, "composite": composite, "ratio": ratio}

    first, second = UI_THEMES_EXPLICIT
    for token in ("ink", "threshold", "card"):
        if seen[first][token] == seen[second][token]:
            raise AssertionError(
                "the chart's %s resolves to %r in BOTH %s and %s — the theme token "
                "is not reaching it, and every paint assertion above is comparing a "
                "value to itself"
                % (token, seen[first][token], first, second))


_BOXES_PROBE = (
    "() => {"
    "  const r = el => { const b = el.getBoundingClientRect();"
    "    return {l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height}; };"
    "  const view = '.battery-chart__view:not([hidden]) ';"
    "  const q = s => document.querySelector(view + s);"
    "  const legend = q('.sparkline-legend');"
    "  return {"
    "    card: r(document.querySelector('#health-row-battery .health-row__body')),"
    "    canvas: r(q('.sparkline__canvas')),"
    "    mark: r(q('.sparkline-mark')),"
    "    texts: [...document.querySelectorAll(view + '.sparkline-text, ' + view + '.sparkline-text--strong')]"
    "      .map(e => ({box: r(e), size: getComputedStyle(e).fontSize, text: e.textContent})),"
    "    legend: legend ? {box: r(legend), size: getComputedStyle(legend).fontSize,"
    "      swatch: r(q('.sparkline-swatch')),"
    "      swatchBorder: getComputedStyle(q('.sparkline-swatch')).borderTopStyle} : null};}")


@pytest.mark.parametrize("which", ("server", "near"))
def test_the_chart_costs_no_width_at_360_in_either_language_and_needs_no_script(
        new_context, server, near, which):
    """At the 360px floor the battery chart costs nothing it must not: the page body does
    not scroll sideways in either language, every chart label is at least 13px and inside
    the chart's own box, the caption for an off-range threshold (default seed) stays inside
    its card with a dashed 20px swatch, the newest point's marker stays inside the card, and
    the area, mark and threshold (or its caption) all still render, and still paint dark-mode
    tokens, with scripts blocked.
    """
    app = server if which == "server" else near
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            base_url = app.base_url()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + FRAME_ROUTE)
            page.wait_for_selector(VISIBLE_VIEW + " " + CHART_MARK)
            message = _assert_no_page_overflow(
                page, "/fleet in %s" % lang, VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)
            boxes = page.evaluate(_BOXES_PROBE)
            if len(boxes["texts"]) < 4:
                raise AssertionError(
                    "expected the chart's grid, end and date labels in %s, got %d"
                    % (lang, len(boxes["texts"])))
            canvas = boxes["canvas"]
            for label in boxes["texts"]:
                if float(label["size"][:-2]) < 13:
                    raise AssertionError(
                        "in %s the chart label %r renders at %s, under the 13px floor"
                        % (lang, label["text"], label["size"]))
                box = label["box"]
                if box["l"] < canvas["l"] - 1 or box["r"] > canvas["r"] + 1:
                    raise AssertionError(
                        "in %s at 360px the chart label %r %r leaves its canvas %r"
                        % (lang, label["text"], box, canvas))
            if which == "server":
                legend = boxes["legend"]
                if legend is None or round(legend["swatch"]["w"], 2) != 20.0 \
                        or legend["swatchBorder"] != "dashed":
                    raise AssertionError(
                        "in %s the off-range caption's swatch is not a 20px dashed line: %r"
                        % (lang, legend))
                if legend["box"]["r"] > boxes["card"]["r"] or legend["box"]["l"] < boxes["card"]["l"]:
                    raise AssertionError(
                        "in %s at 360px the caption %r escapes its own card %r"
                        % (lang, legend["box"], boxes["card"]))
            else:
                assert boxes["legend"] is None, "a threshold drawn on the chart needs no caption"
            # The mark is drawn at the canvas's own edge (cx=100%), so its radius hangs
            # outside the plot area; the card's padding is what must absorb it.
            mark = boxes["mark"]
            if mark["r"] > boxes["card"]["r"] or mark["t"] < boxes["card"]["t"]:
                raise AssertionError(
                    "in %s at 360px the mark's ink %r escapes the card %r"
                    % (lang, mark, boxes["card"]))
        finally:
            context.close()

    # All of it is server-rendered SVG and owes nothing to a script. Measured in the
    # theme+no-JS combination most likely to be wrong.
    with _no_js_page(new_context, app.base_url(), FRAME_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        wanted = [("area", CHART_AREA, "fill"), ("mark", CHART_MARK, "fill")]
        wanted.append(("threshold", CHART_THRESHOLD, "stroke") if which == "near"
                      else ("caption", CHART_LEGEND, "color"))
        for label, selector, _prop in wanted:
            # The hidden voltage twin carries its own copy of each drawing.
            shown = blocked.locator(VISIBLE_VIEW + " " + selector)
            if shown.count() != 1:
                raise AssertionError(
                    "with scripts blocked: expected exactly one %s, got %d"
                    % (label, shown.count()))
        _set_ui_theme(blocked, UI_THEMES_EXPLICIT[1])
        for label, selector, prop in wanted:
            paint = _computed_paint(blocked, VISIBLE_VIEW + " " + selector, (prop,))
            if paint["svg_default"]:
                raise AssertionError(
                    "with scripts blocked, in %s: the chart's %s resolves %r to the SVG "
                    "default" % (UI_THEMES_EXPLICIT[1], label, paint["svg_default"]))


# The Battery page draws no check-in regularity grid.

@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED),
                         ids=("1280", "360"))
def test_the_battery_page_has_no_regularity_grid_and_never_scrolls_sideways(
        new_context, server, lang, viewport):
    """The Battery page holds no regularity grid, cells, key or scale; its one row still shows
    inside its card, and the page never scrolls sideways."""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
        page.goto(server.base_url() + FRAME_ROUTE)
        for selector in (".check-in-grid", ".check-in-key", ".check-in-grid__scale",
                         "rect.drawing-cell"):
            assert page.locator(selector).count() == 0, (
                "The Battery page still draws %s in %s" % (selector, lang))
        assert page.locator("div.health-row").count() == 1
        assert page.locator("#health-row-connection").count() == 0
        message = _assert_no_page_overflow(
            page, "/fleet in %s" % lang, viewport["width"])
        if message:
            raise AssertionError(message)
    finally:
        context.close()


# --- Status: percentage / voltage switch, readable width, hierarchy ----------------------

UNIT_VIEWPORTS = (
    ("1280", VIEWPORT_DESKTOP),
    ("390", {"width": 390, "height": 844}),
    ("360", VIEWPORT_MIN_SUPPORTED),
)


def _open_status(context, base_url, lang):
    page = context.new_page()
    _login(page, base_url)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page.goto(base_url + FRAME_ROUTE)
    page.wait_for_selector(".battery-unit:not([hidden])")
    return page


def _shown_unit(page):
    return page.evaluate(
        "() => document.querySelector('%s').getAttribute('data-unit')" % VISIBLE_VIEW)


def _pressed_units(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('.battery-unit__option')]"
        ".filter(b => b.getAttribute('aria-checked') === 'true')"
        ".map(b => b.getAttribute('data-unit'))")


def _readout_value(page):
    return page.inner_text(".battery-readout__value").strip()


def _active_reading(page):
    return page.evaluate(
        "() => { const a = document.querySelector('%s .sparkline-hit--active');"
        " return a ? a.getAttribute('data-reading') || (a.getAttribute('data-mv') + ' mV')"
        " : null; }" % VISIBLE_VIEW)


@pytest.mark.parametrize("width_label,viewport", UNIT_VIEWPORTS, ids=[v[0] for v in UNIT_VIEWPORTS])
@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_battery_unit_switch_changes_chart_and_readout_by_keyboard_and_pointer(
        new_context, server, width_label, viewport, lang):
    """The Percentage/Voltage control is a radio group revealed once the script runs, starts
    on the server-rendered percentage view, has two 44px segments, and switches the chart and
    its readout together by pointer, Enter, Space and the arrow keys with a visible focus
    ring and an explicit checked state; the readout is empty until a point is revealed and
    then always equals the active point's server-computed text. The page never scrolls
    sideways, and below the desktop breakpoint the bottom tab bar stays visible.
    """
    context = new_context(viewport=viewport)
    try:
        page = _open_status(context, server.base_url(), lang)
        assert page.get_attribute(".battery-unit", "role") == "radiogroup"
        assert _shown_unit(page) == "percent" and _pressed_units(page) == ["percent"]
        assert page.is_hidden('.battery-chart__view[data-unit="mv"]')
        for unit in ("percent", "mv"):
            box = page.locator('.battery-unit__option[data-unit="%s"]' % unit).bounding_box()
            assert box["height"] >= 44 - 0.5 and box["width"] >= 44, box
        assert _readout_value(page) == "", "nothing is revealed until a point is"

        page.click('.battery-unit__option[data-unit="mv"]')
        assert _shown_unit(page) == "mv" and _pressed_units(page) == ["mv"]
        assert page.is_hidden('.battery-chart__view[data-unit="percent"]')

        page.focus(VISIBLE_VIEW + " .sparkline-hit[tabindex='0']")
        value = _readout_value(page)
        assert re.fullmatch(r"\d+ mV", value), value
        assert value == _active_reading(page), "readout and chart point disagree"

        page.focus('.battery-unit__option[data-unit="mv"]')
        page.keyboard.press("ArrowLeft")
        assert _shown_unit(page) == "percent" and _pressed_units(page) == ["percent"]
        assert page.evaluate("() => document.activeElement.getAttribute('data-unit')") == "percent"
        value = _readout_value(page)
        assert re.fullmatch(r"≈ \d+\s?%", value) or re.fullmatch(r"≈ \d+%", value), value
        assert value == _active_reading(page), "the reading carries across the switch"

        page.keyboard.press("ArrowRight")
        assert _shown_unit(page) == "mv"
        page.focus('.battery-unit__option[data-unit="percent"]')
        page.keyboard.press("Enter")
        assert _shown_unit(page) == "percent"
        page.focus('.battery-unit__option[data-unit="mv"]')
        page.keyboard.press("Space")
        assert _shown_unit(page) == "mv"
        outline = page.evaluate(
            "() => { const s = getComputedStyle(document.activeElement);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }")
        assert outline[0] != "none" and outline[1] >= 2, "no visible focus ring: %r" % (outline,)

        # The chart's own roving-tabindex keyboard path still works in the shown view.
        page.focus(VISIBLE_VIEW + " .sparkline-hit[tabindex='0']")
        page.keyboard.press("ArrowLeft")
        assert _readout_value(page) == _active_reading(page)

        message = _assert_no_page_overflow(
            page, "/fleet unit switch %s %s" % (width_label, lang), viewport["width"])
        if message:
            raise AssertionError(message)
        assert page.locator(".day-band").count() == 0, "Health carries no day band"
        if viewport["width"] < 960:
            box = page.locator(".tab-bar").bounding_box()
            assert box is not None and box["height"] > 0
            assert page.evaluate(
                "() => getComputedStyle(document.querySelector('.tab-bar')).visibility") == "visible"
    finally:
        context.close()


def test_the_battery_unit_switch_works_by_touch(new_context, server):
    """A tap on the Voltage button switches the chart view, and back."""
    context = new_context(viewport={"width": 390, "height": 844}, has_touch=True)
    try:
        page = _open_status(context, server.base_url(), "en")
        page.tap('.battery-unit__option[data-unit="mv"]')
        assert _shown_unit(page) == "mv" and _pressed_units(page) == ["mv"]
        page.tap('.battery-unit__option[data-unit="percent"]')
        assert _shown_unit(page) == "percent"
    finally:
        context.close()


def test_the_battery_chart_stays_on_percentage_without_script(new_context, server):
    """With scripts blocked the control and the hover readout are not offered and the
    percentage chart stays visible."""
    with _no_js_page(new_context, server.base_url(), FRAME_ROUTE) as page:
        assert page.is_hidden(".battery-unit") and page.is_hidden(".battery-readout")
        assert page.is_visible('.battery-chart__view[data-unit="percent"] .sparkline__canvas')
        assert page.is_hidden('.battery-chart__view[data-unit="mv"]')
