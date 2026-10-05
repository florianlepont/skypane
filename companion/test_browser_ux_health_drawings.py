#!/usr/bin/env python3
"""Browser checks for the SVG-drawing scenario group: the battery ring, the battery chart's
area/line/threshold and the absence of a regularity grid, all on Health, plus the rows card's
alignment and width.

The drawings live inside the Health rows' details, so each check opens the rows first (by
keyboard, the native disclosure, which also works with scripts blocked) before it measures.

One module-scoped, read-only server (`server`) is shared across these checks. None of the
tests below POSTs or otherwise mutates server state, so sharing it is safe under xdist.
"""
import re

import pytest

from companion import auth
from skypane_contrast_check import (
    contrast_ratio,
)
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _RING_INK_PROBE,
    _assert_no_page_overflow, _computed_paint, _login, _no_js_page,
    _open_health_rows, _set_ui_theme, seed_state_dir,
)

pytestmark = pytest.mark.browser

VISIBLE_VIEW = ".battery-chart__view:not([hidden])"

# The battery ring, measured where it actually has to be correct: a real browser, both
# themes, the narrowest supported screen, and with scripts off.

# Scoped to the Battery row: the Identification row carries a second, smaller ring.
RING_FIGURE = "#health-row-battery svg.drawing__figure"
RING_VALUE = "#health-row-battery svg.drawing__figure .drawing-ring-value"
RING_TRACK = "#health-row-battery svg.drawing__figure .drawing-ring-track"
RING_PAGES = (("Health", "/health"),)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture the battery ring and battery chart checks
    measure against — module-scoped because every test in this group only GETs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


@pytest.mark.parametrize("label,route", RING_PAGES, ids=[p[0] for p in RING_PAGES])
def test_the_ring_paints_a_theme_token_in_both_themes(new_context, server, label, route):
    """The battery ring's value arc resolves to a real theme token on both pages in both
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
        _open_health_rows(page)
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
def test_the_rings_viewbox_contains_its_own_stroked_geometry(new_context, server, label, route):
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
        _open_health_rows(page)
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


def test_the_ring_costs_no_width_no_height_and_no_script(new_context, server):
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
            _open_health_rows(page)
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
                _open_health_rows(blocked)
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


# The battery chart's three additions, measured where they have to be correct.

CHART_AREA = ".sparkline-area"
CHART_LINE = ".sparkline-line"
CHART_MARK = ".sparkline-mark"
CHART_THRESHOLD = ".sparkline-threshold"
CHART_LEGEND = ".sparkline-legend"
CHART_SWATCH = ".sparkline-swatch"

# The area is a translucent fill, so its resolved `fill` is not what lands on screen: what
# lands is that colour composited over the card behind it at the resolved `fill-opacity`.
# Composited here and compared against the card's own resolved background through the app's
# own contrast formula. The 1.20:1 floor is not WCAG's 3:1, which is for a UI component a
# user must find and identify; this is a wash under a line that already carries the data,
# and at 3:1 it would be a block of ink. What it must not be is present but invisible,
# technically painted, visually absent.
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


def test_the_charts_area_mark_and_threshold_paint_real_tokens_in_both_themes(page, server):
    """The battery chart's area, line, mark and threshold each resolve to a real theme token
    in both themes: never the SVG default, the area/line/mark sharing one currentColor ink
    while the threshold deliberately does not, the legend's swatch equal to the drawn
    threshold, and the area's composite over the card clearing a 1.20:1 floor so it is
    visible and not merely painted.
    """
    # Three different questions are asked, because "not the default" alone would be green for
    # a shape that is the same in both themes, and "differs between themes" alone would be
    # green for a shape painted the wrong colour consistently: the area, the line and the
    # mark must resolve to the same ink, since all three are currentColor; the threshold must
    # resolve to something else, since a judgement painted in the data's own ink is a
    # judgement nobody can see; and every one of them must move when the theme does.
    _login(page, server.base_url())
    page.goto(server.base_url() + "/health")
    _open_health_rows(page)
    page.wait_for_selector(CHART_AREA)
    seen = {}
    for theme in UI_THEMES_EXPLICIT:
        _set_ui_theme(page, theme)
        area = _computed_paint(page, CHART_AREA, ("fill", "fill-opacity"))
        line = _computed_paint(page, CHART_LINE, ("stroke",))
        mark = _computed_paint(page, CHART_MARK, ("fill",))
        threshold = _computed_paint(page, CHART_THRESHOLD, ("fill",))
        swatch = page.evaluate(
            "s => getComputedStyle(document.querySelector(s)).backgroundColor",
            CHART_SWATCH)
        # The chart sits in a card-less wrapper inside a row, so the surface it is composited
        # over is the rows card's own.
        card = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'.health-rows')).backgroundColor")
        for name, paint, prop in (
                ("area", area, "fill"), ("line", line, "stroke"),
                ("mark", mark, "fill"), ("threshold", threshold, "fill")):
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
        if threshold["fill"] == line["stroke"]:
            raise AssertionError(
                "in %s the threshold resolves to the trend line's own ink (%r) — a "
                "judgement painted in the data's colour is not a judgement anyone "
                "can read" % (theme, threshold["fill"]))
        if swatch != threshold["fill"]:
            raise AssertionError(
                "in %s the legend's swatch (%r) and the drawn threshold (%r) are "
                "different colours — the legend would be describing a line the "
                "chart does not draw" % (theme, swatch, threshold["fill"]))

        alpha = float(area["fill-opacity"])
        if not (0.0 < alpha < 1.0):
            raise AssertionError(
                "in %s the area's fill-opacity is %r — an opaque area hides the "
                "axis and the threshold beneath it" % (theme, alpha))
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
            "ink": area["fill"], "alpha": alpha, "threshold": threshold["fill"],
            "card": card, "composite": composite, "ratio": ratio}

    first, second = UI_THEMES_EXPLICIT
    for token in ("ink", "threshold", "card"):
        if seen[first][token] == seen[second][token]:
            raise AssertionError(
                "the chart's %s resolves to %r in BOTH %s and %s — the theme token "
                "is not reaching it, and every paint assertion above is comparing a "
                "value to itself"
                % (token, seen[first][token], first, second))


def test_the_chart_costs_no_width_at_360_in_either_language_and_needs_no_script(new_context, server):
    """At the 360px floor the battery chart's additions cost nothing they must not: the
    page body does not scroll sideways in either language, the threshold's legend overlaps
    none of the four axis labels and stays inside its card at the 10px micro-label tier,
    its swatch measures a real 12x1 box (which an inline <span> could not), the canvas keeps
    its share of the grid rather than being squeezed by a legend that claimed the Y-label
    column, the mark's edge-hung ink stays inside the card, and the area, mark, threshold
    and legend all still render, and still paint dark-mode tokens, with scripts blocked.
    """
    # The 360px floor, in both languages, since French is the longer copy here and this file
    # already carries several checks that exist because French overflowed where English did
    # not. The legend sits in its own full-width grid row, so no overlap with the axis labels
    # is structural rather than lucky, hence the check is written as a box comparison instead
    # of "the legend is in its own row": it keeps measuring the property that matters if the
    # row is ever traded for absolute positioning.
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            base_url = server.base_url()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/health")
            _open_health_rows(page)
            page.wait_for_selector(CHART_LEGEND)
            message = _assert_no_page_overflow(
                page, "/health in %s" % lang, VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)

            boxes = page.evaluate(
                "() => {"
                "  const r = el => { const b = el.getBoundingClientRect();"
                "    return {l: b.left, t: b.top, r: b.right, b: b.bottom,"
                "            w: b.width, h: b.height}; };"
                "  const legend = document.querySelector('.sparkline-legend');"
                "  return {legend: r(legend),"
                "          text: legend.textContent.trim(),"
                "          font: getComputedStyle(legend).fontSize,"
                "          swatch: r(document.querySelector('.sparkline-swatch')),"
                "          card: r(document.querySelector('#health-row-battery .health-row__body')),"
                "          grid: r(document.querySelector('.sparkline')),"
                "          canvas: r(document.querySelector('.sparkline__canvas')),"
                "          mark: r(document.querySelector('.sparkline-mark')),"
                "          axis: [...document.querySelectorAll("
                "            '.battery-chart__view:not([hidden]) .sparkline-axis-label')]"
                "                  .map(r)};}")
            if len(boxes["axis"]) != 4:
                raise AssertionError(
                    "expected the chart's four axis labels in %s, got %d — with another "
                    "number this overlap check measures nothing"
                    % (lang, len(boxes["axis"])))
            legend = boxes["legend"]
            for index, axis in enumerate(boxes["axis"]):
                overlaps = (legend["l"] < axis["r"] and axis["l"] < legend["r"]
                            and legend["t"] < axis["b"] and axis["t"] < legend["b"])
                if overlaps:
                    raise AssertionError(
                        "in %s at 360px the threshold's legend %r overlaps axis label %d "
                        "%r" % (lang, legend, index, axis))

            # THE LEGEND MUST NOT CLAIM THE Y-LABEL COLUMN, and this is
            # the assertion that makes `.sparkline__legend`'s
            # `grid-column: 1 / -1` measurable. Without it the legend
            # auto-places into column 1 — the `auto` column sized to the
            # widest Y-axis label — and that column grows to fit a whole
            # sentence: measured at 360px, the canvas drops from 229.97px
            # to ~109px inside the same 278px grid, with NO overflow and
            # no other signal. Every other assertion in this check stayed
            # green through that mutation, which is how the gap was
            # found. The 0.70 share separates 0.827 (shipped) from 0.39
            # (mutated) with room on both sides and is not a layout
            # number anyone would otherwise tune.
            share = boxes["canvas"]["w"] / boxes["grid"]["w"]
            if share < 0.70:
                raise AssertionError(
                    "in %s at 360px the chart's canvas is %.2fpx of its %.2fpx grid "
                    "(%.2f) — the legend has claimed the auto-sized Y-label column and "
                    "squeezed the drawing, which overflows nothing and so shows up "
                    "nowhere else" % (lang, boxes["canvas"]["w"], boxes["grid"]["w"], share))

            # A bare inline <span> ignores width and height, so the
            # swatch would compute to a zero-sized box and the legend
            # would describe a colour it never shows. This box is what
            # proves `.sparkline-legend`'s inline-flex is doing
            # something: measured with `display: inline` instead, the
            # swatch is 0.00x11.00.
            swatch = boxes["swatch"]
            if round(swatch["w"], 2) != 12.0 or round(swatch["h"], 2) != 1.0:
                raise AssertionError(
                    "in %s at 360px the legend's swatch measures %.2fx%.2f, not the "
                    "12x1 it declares — an inline <span> ignores width/height, so this "
                    "is what proves the legend's flex context is doing something"
                    % (lang, swatch["w"], swatch["h"]))
            if boxes["font"] != "10px":
                raise AssertionError(
                    "in %s the legend renders at %s, not the 10px micro-label tier its "
                    "neighbours use" % (lang, boxes["font"]))
            if legend["r"] > boxes["card"]["r"] or legend["l"] < boxes["card"]["l"]:
                raise AssertionError(
                    "in %s at 360px the legend %r escapes its own card %r"
                    % (lang, legend, boxes["card"]))

            # The mark is drawn at the canvas's own edge (cx=100%), so its radius hangs
            # outside the plot area exactly as the existing dot and hit target already do.
            # What must hold is that the card absorbs it.
            mark = boxes["mark"]
            if mark["r"] > boxes["card"]["r"] or mark["t"] < boxes["card"]["t"]:
                raise AssertionError(
                    "in %s at 360px the mark's ink %r escapes the card %r — the chart's "
                    "x scale runs edge to edge, so the newest point's radius overhangs "
                    "the canvas by design and the card's padding is what must absorb it"
                    % (lang, mark, boxes["card"]))
        finally:
            context.close()

    # All three additions are server-rendered SVG and owe nothing to a script. Measured in
    # the theme+no-JS combination most likely to be wrong.
    with _no_js_page(new_context, server.base_url(), "/health",
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        _open_health_rows(blocked)
        for label, selector in (("area", CHART_AREA), ("mark", CHART_MARK),
                                ("threshold", CHART_THRESHOLD),
                                ("legend", CHART_LEGEND)):
            # The hidden percentage twin carries its own copy of each drawing.
            shown = blocked.locator(VISIBLE_VIEW + " " + selector)
            if shown.count() != 1:
                raise AssertionError(
                    "with scripts blocked: expected exactly one %s, got %d"
                    % (label, shown.count()))
        _set_ui_theme(blocked, UI_THEMES_EXPLICIT[1])
        for label, selector, props in (
                ("area", CHART_AREA, ("fill",)),
                ("mark", CHART_MARK, ("fill",)),
                ("threshold", CHART_THRESHOLD, ("fill",))):
            paint = _computed_paint(blocked, selector, props)
            if paint["svg_default"]:
                raise AssertionError(
                    "with scripts blocked, in %s: the chart's %s resolves %r to the SVG "
                    "default" % (UI_THEMES_EXPLICIT[1], label, paint["svg_default"]))


# Health draws no check-in regularity grid: the connection row is plain facts.

@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED),
                         ids=("1280", "360"))
def test_health_has_no_regularity_grid_and_the_connection_row_still_renders(
        new_context, server, lang, viewport):
    """With every row opened, Health holds no regularity grid, cells, key or scale; the
    connection row still shows its verdict, its last-check-in fact and its one-line
    explanation inside the card, and the page never scrolls sideways."""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
        page.goto(server.base_url() + "/health")
        _open_health_rows(page)
        for selector in (".check-in-grid", ".check-in-key", ".check-in-grid__scale",
                         "rect.drawing-cell"):
            assert page.locator(selector).count() == 0, (
                "Health still draws %s in %s" % (selector, lang))
        row = page.locator("#health-row-connection")
        assert row.count() == 1
        assert row.locator("summary .health-row__verdict").is_visible()
        assert row.locator(".health-row__body .health-row__facts").is_visible()
        assert row.locator(".health-row__body .health-row__note").is_visible()
        body = page.evaluate(
            "() => { const b = document.querySelector("
            "'#health-row-connection .health-row__body');"
            " const r = b.getBoundingClientRect();"
            " const c = document.querySelector('.health-rows').getBoundingClientRect();"
            " return {l: r.left, r: r.right, cl: c.left, cr: c.right}; }")
        assert body["l"] >= body["cl"] - 0.5 and body["r"] <= body["cr"] + 0.5, (
            "the connection row body spills out of its card: %r" % (body,))
        message = _assert_no_page_overflow(
            page, "/health in %s" % lang, viewport["width"])
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
    page.goto(base_url + "/health")
    _open_health_rows(page)
    page.wait_for_selector(".battery-unit:not([hidden])")
    return page


def _shown_unit(page):
    return page.evaluate(
        "() => document.querySelector('%s').getAttribute('data-unit')" % VISIBLE_VIEW)


def _pressed_units(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('.battery-unit__option')]"
        ".filter(b => b.getAttribute('aria-pressed') === 'true')"
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
    """The Percentage/Voltage control is revealed once the script runs, starts on the
    server-rendered voltage view, and switches the chart and its readout together by pointer,
    Enter and Space with a visible focus ring and an explicit pressed state; the readout always
    equals the active point's server-computed text. The page never scrolls sideways, today's
    activity sits on this page, and below the desktop breakpoint the bottom tab bar stays
    visible.
    """
    context = new_context(viewport=viewport)
    try:
        page = _open_status(context, server.base_url(), lang)
        assert _shown_unit(page) == "mv" and _pressed_units(page) == ["mv"]
        assert page.is_hidden('.battery-chart__view[data-unit="percent"]')

        page.click('.battery-unit__option[data-unit="percent"]')
        assert _shown_unit(page) == "percent" and _pressed_units(page) == ["percent"]
        assert page.is_hidden('.battery-chart__view[data-unit="mv"]')
        value = _readout_value(page)
        assert re.fullmatch(r"≈ \d+\s?%", value) or re.fullmatch(r"≈ \d+%", value), value
        assert value == _active_reading(page), "readout and chart point disagree"

        page.focus('.battery-unit__option[data-unit="mv"]')
        page.keyboard.press("Enter")
        assert _shown_unit(page) == "mv" and _pressed_units(page) == ["mv"]
        assert re.fullmatch(r"\d+ mV", _readout_value(page)), _readout_value(page)
        assert _readout_value(page) == _active_reading(page)

        page.focus('.battery-unit__option[data-unit="percent"]')
        page.keyboard.press("Space")
        assert _shown_unit(page) == "percent"
        outline = page.evaluate(
            "() => { const s = getComputedStyle(document.activeElement);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }")
        assert outline[0] != "none" and outline[1] >= 2, "no visible focus ring: %r" % (outline,)

        # The chart's own roving-tabindex keyboard path still works in the shown view.
        page.focus(VISIBLE_VIEW + " .sparkline-hit[tabindex='0']")
        page.keyboard.press("ArrowLeft")
        assert _readout_value(page) == _active_reading(page)

        message = _assert_no_page_overflow(
            page, "/health unit switch %s %s" % (width_label, lang), viewport["width"])
        if message:
            raise AssertionError(message)
        assert page.locator(".day-band").count() == 0, "Health carries no day band"
        assert "3 months" not in page.inner_text("main") and "3 mois" not in page.inner_text("main")
        if viewport["width"] < 960:
            box = page.locator(".tab-bar").bounding_box()
            assert box is not None and box["height"] > 0
            assert page.evaluate(
                "() => getComputedStyle(document.querySelector('.tab-bar')).visibility") == "visible"
    finally:
        context.close()


def test_the_battery_unit_switch_works_by_touch(new_context, server):
    """A tap on the Percentage button switches the chart view."""
    context = new_context(viewport={"width": 390, "height": 844}, has_touch=True)
    try:
        page = _open_status(context, server.base_url(), "en")
        page.tap('.battery-unit__option[data-unit="percent"]')
        assert _shown_unit(page) == "percent" and _pressed_units(page) == ["percent"]
        page.tap('.battery-unit__option[data-unit="mv"]')
        assert _shown_unit(page) == "mv"
    finally:
        context.close()


def test_the_battery_chart_stays_on_voltage_without_script(new_context, server):
    """With scripts blocked the control is not offered and the voltage chart stays visible."""
    with _no_js_page(new_context, server.base_url(), "/health") as page:
        _open_health_rows(page)
        assert page.is_hidden(".battery-unit")
        assert page.is_visible('.battery-chart__view[data-unit="mv"] .sparkline__canvas')
        assert page.is_hidden('.battery-chart__view[data-unit="percent"]')


@pytest.mark.parametrize("width", (1280, 1024, 960, 700, 390, 360))
def test_health_cards_share_one_width_and_every_row_aligns(new_context, server, width):
    """Every card on Health spans the same column: the rows card, the unresolved-prefix card and the
    docked toast share their left and right edges at every viewport (no per-element width cap), the
    group bands span their card, and every row's icon, name, verdict and value columns line up
    from one row to the next, with nothing overflowing sideways."""
    context = new_context(viewport={"width": width, "height": 900})
    try:
        page = _open_status(context, server.base_url(), "fr")
        edges = page.evaluate(
            "() => { const e = s => { const b = document.querySelector(s).getBoundingClientRect();"
            " return [Math.round(b.left * 10) / 10, Math.round(b.right * 10) / 10]; };"
            " return {rows: e('.health-rows'), registry: e('#unresolved-prefixes'),"
            " page: e('.status-page'),"
            " bands: [...document.querySelectorAll('.health-rows__group')].map("
            "   g => { const b = g.getBoundingClientRect();"
            "     return [Math.round(b.left * 10) / 10, Math.round(b.right * 10) / 10]; }),"
            " toasts: [...document.querySelectorAll('.status-page > .toast')].map("
            "   t => { const b = t.getBoundingClientRect();"
            "     return [Math.round(b.left * 10) / 10, Math.round(b.right * 10) / 10]; })}; }")
        assert edges["rows"] == edges["registry"] == edges["page"], (
            "the rows card, the registry card and the page column must share one width, got %r" % (edges,))
        inner = [edges["rows"][0] + 1, edges["rows"][1] - 1]  # inside the card's 1px hairline
        for band in edges["bands"]:
            assert band == inner, "a group band must span its card, got %r vs %r" % (band, inner)
        for toast in edges["toasts"]:
            assert toast == edges["rows"], "a toast must share the card width, got %r" % (toast,)
        columns = page.evaluate(
            "() => [...document.querySelectorAll('.health-row__summary')].map(s => {"
            " const r = c => { const el = s.querySelector(c);"
            "   const b = el.getBoundingClientRect();"
            "   return [Math.round(b.left * 10) / 10, Math.round(b.right * 10) / 10,"
            "           Math.round(b.top * 10) / 10]; };"
            " return {icon: r('.health-row__icon'), name: r('.health-row__name'),"
            "   verdict: r('.health-row__verdict'), value: r('.health-row__value'),"
            "   nameHeight: s.querySelector('.health-row__name').getBoundingClientRect().height,"
            "   box: s.getBoundingClientRect().height}; })")
        assert len(columns) >= 5
        # The value column is right-aligned on the wide layout, so only its right edge is shared.
        left_aligned = ("icon", "name", "verdict") if width >= 700 else ("icon", "name", "verdict", "value")
        for key in left_aligned:
            lefts = {row[key][0] for row in columns}
            assert len(lefts) == 1, "the %s column's left edge differs from row to row: %r" % (key, lefts)
        if width >= 700:
            rights = {row["value"][1] for row in columns}
            assert len(rights) == 1, "the value column's right edge differs from row to row: %r" % (rights,)
        else:
            for row in columns:
                assert row["name"][2] < row["verdict"][2] < row["value"][2], (
                    "on a phone the name, verdict and value stack in that order, got %r" % (row,))
        for row in columns:
            assert row["nameHeight"] <= 20, (
                "a row name wraps onto a second line (%.1fpx tall) at %dpx" % (row["nameHeight"], width))
            assert row["box"] >= 64 - 0.5, "a row is at least 64px tall (8px grid), got %.1f" % row["box"]
        message = _assert_no_page_overflow(page, "/health rows at %dpx" % width, width)
        if message:
            raise AssertionError(message)
    finally:
        context.close()
