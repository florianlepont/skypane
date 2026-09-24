#!/usr/bin/env python3
"""The SVG-drawing scenario group split out of `companion/test_browser_ux.py`
(31-02-PLAN.md, D-04) into its own standalone harness, converted to native
pytest-playwright tests by 33-19-PLAN.md Task 2 (TST-11).

Covers the complete 24-04/24-06/24-07/24-08 drawings series: the battery
ring (Home + Health), the battery chart's area/line/threshold, the day
band, the check-in regularity grid, and the Home hero that composes the
ring and the band together. These eleven checks were the first of D-04's
two mandatory extractions and RESEARCH.md's rank-1 candidate — three of
them already spun up their own isolated `Harness()` rather than reusing
the shared one, so the original authors already treated this cluster as
isolation-worthy, and their `_in_both_themes()` loops make their real
wall-time share larger than their line-count share suggests.

Every test below drives a real headless Chromium against a real
`companion/app.py` subprocess, through the guarded `page`/`new_context`
fixtures (`companion/conftest.py`), and never constructs or navigates to
any URL outside `server.base_url()` / `band_server.base_url()` /
`grid_server.base_url()` — all `127.0.0.1:<ephemeral-port>` origins the
guarded fixtures themselves created. A missing/unlaunchable Chromium is a
hard failure under CI / `SKYPANE_REQUIRE_BROWSER=1` (the `browser` fixture
override in `companion/conftest.py`), never a silent skip.

Three module-scoped, read-only servers replace the three isolated
`Harness()` instances the legacy version of this file spun up per check:
`server` (the shared 24-04/24-05 fixture), `band_server` (one day's worth
of seeded check-ins, shared by the day-band and hero checks, which is
exactly the set that used to call `_band_harness()`), and `grid_server`
(three seeded days with distinct on-cadence/late/missing verdicts, shared
by the two regularity-grid checks). None of the eleven tests below POSTs
or otherwise mutates server state, so sharing a server per group is safe
under xdist (33-MIGRATION-RULES.md section 2).
"""
import itertools
import re
from datetime import datetime, timedelta

import pytest

from companion import auth, draw, layout
from companion.contrast_check import (
    MIN_SIGNAL_PERCEPTUAL_DISTANCE, WCAG_AA_UI_COMPONENT, contrast_ratio,
    perceptual_distance,
)
from companion.pages import health_page, home_page
from server import device_config, history_db
# 31-02-PLAN.md Task 1: shared constants and helpers live in
# companion.test_browser_ux_helpers (31-01-PLAN.md Task 3), so this file
# imports them rather than duplicating them.
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_WIDTH_NARROW, _RING_INK_PROBE, _TILE_CONTENT_PROBE,
    _assert_no_page_overflow, _computed_paint, _login, _no_js_page,
    _set_ui_theme, seed_state_dir,
)

pytestmark = pytest.mark.browser

# ===========================================================================
# 24-04-PLAN.md Task 4 (CFG-40/CFG-45/D-09): the battery ring, measured
# where it actually has to be correct — a real browser, both themes, the
# narrowest supported screen, and with scripts off. Every one of these
# uses 24-02's helpers rather than inventing a second mechanism for the
# same job.
# ===========================================================================

RING_FIGURE = "svg.drawing__figure"
RING_VALUE = "svg.drawing__figure .drawing-ring-value"
RING_TRACK = "svg.drawing__figure .drawing-ring-track"
RING_PAGES = (("Home", "/"), ("Health", "/health"))


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only 22-AUDIT.md-methodology fixture the battery
    ring and battery chart checks measure against — module-scoped because
    every test in this group only GETs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


@pytest.mark.parametrize("label,route", RING_PAGES, ids=[p[0] for p in RING_PAGES])
def test_the_ring_paints_a_theme_token_in_both_themes(new_context, server, label, route):
    """the battery ring's value arc resolves to a real theme token on BOTH pages in
    BOTH themes — never the SVG default fill or stroke, never the same paint as
    its own track, and never the same value in light and dark (CFG-40,
    24-02's theme and computed-paint helpers)"""
    # WHY A BROWSER AT ALL: a source scan can see that the arc carries
    # class="drawing-ring-value". It cannot see what that class RESOLVES
    # to. getComputedStyle has already run the cascade, resolved
    # currentColor against the inherited colour and substituted the
    # theme's custom property — so this is the only thing in the
    # repository that can tell a token-painted shape from one that fell
    # through to the SVG default.
    #
    # A drawing correct in light mode only is a defect, not a polish
    # item. Both themes are sampled on this page, because the two rings
    # are two sizes of one emitter and a single sample would not notice
    # if only one of them inherited its colour.
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
def test_the_rings_viewbox_contains_its_own_stroked_geometry(new_context, server, label, route):
    """the battery ring's viewBox contains its own STROKED geometry on both pages — "
    each arc's browser-reported bounding box, expanded by half its resolved
    stroke width on every side, lies inside the box the emitter declared
    (CFG-45, contract rule 5)"""
    # CONTRACT RULE 5, MEASURED RATHER THAN DERIVED. A stroked arc extends
    # half its stroke width beyond the nominal radius, which is the
    # single most common way a ring gets clipped by its own box — and
    # arithmetic on the emitter's constants would only re-derive what the
    # emitter already believes. So the geometry comes back from the
    # browser: getBBox() for the path's own box and the RESOLVED
    # stroke-width from getComputedStyle, expanded by half on every side.
    #
    # getBBox() deliberately excludes the stroke (SVG 1.1 behaviour, and
    # the option dictionary that would include it is exactly the thing
    # whose support would have to be assumed) — so the half-stroke is
    # added here, in the open, because that half-stroke IS the property
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


def test_the_ring_costs_no_width_no_height_and_no_script(new_context, server):
    """at the 360px floor the ring costs nothing it must not: neither page's body
    scrolls sideways, Home's Battery tile stays exactly as tall as the Frame
    tile beside it (measured against a neighbour, because 'all three equal' is
    false at 360px and vacuous at 1280px), and both rings still render — and
    still paint a dark-mode token — with scripts blocked through _no_js_page()
    (CFG-45, D-09)"""
    # THREE PROPERTIES THE RING COULD PLAUSIBLY BREAK, all at the 360px
    # floor.
    #
    # THE TILE ASSERTION IS DELIBERATELY NOT "all three tiles are equal
    # height", and that is the whole reason it is written this way.
    # Measured on this tree BEFORE the ring existed: at 360px the three
    # tiles are 111.59 / 111.59 / 131.19 — `.dashboard-grid` collapses to
    # ONE COLUMN there, so each tile is its own grid row at its own
    # intrinsic height, and the Data tile is legitimately taller because
    # its detail wraps to a second line. An "all equal" assertion would
    # simply be false. At 1280px, where the three DO share a row,
    # `align-items: stretch` makes them equal no matter what, so "all
    # equal" would be VACUOUS there. Neither width can carry the property
    # this plan actually owes.
    #
    # What it owes is that the RING ADDED NO HEIGHT, and that is measured
    # against the tile the ring did not touch: the Frame tile carries the
    # same two text lines in the same box, so Battery's own content
    # height must still equal it exactly. A ring stacked above the text
    # instead of beside it fails here.
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

        page.goto(server.base_url() + "/")
        tiles = page.evaluate(_TILE_CONTENT_PROBE)
        if len(tiles) != 3:
            raise AssertionError(
                "expected Home's three status tiles, got %d — with another "
                "number this check is measuring the wrong row" % (len(tiles),))
        frame_tile, battery_tile = tiles[0], tiles[1]
        if battery_tile["hasRing"] != 1 or frame_tile["hasRing"] != 0:
            raise AssertionError(
                "expected the ring in the SECOND tile (Battery) and nowhere else "
                "in the row, got ring counts %r"
                % ([t["hasRing"] for t in tiles],))
        if abs(battery_tile["contentH"] - frame_tile["contentH"]) > 0.5:
            raise AssertionError(
                "Home's Battery tile's own content is %.2fpx tall against its "
                "Frame neighbour's %.2fpx at 360px — the ring pushed the tile "
                "down, and `.dashboard-grid`'s stretch would push the whole row "
                "with it" % (battery_tile["contentH"], frame_tile["contentH"]))
        if abs(battery_tile["height"] - frame_tile["height"]) > 0.5:
            raise AssertionError(
                "Home's Battery tile is %.2fpx tall against its Frame "
                "neighbour's %.2fpx at 360px, where the two are separate grid "
                "rows carrying the same two text lines"
                % (battery_tile["height"], frame_tile["height"]))

        # D-09, THROUGH THE SHARED HELPER. The ring is complete markup in
        # the first response, so it must arrive whole with scripts
        # blocked — and asking through _no_js_page() is what makes this
        # compose with the existing no-JS floor instead of being a
        # second, private way to turn scripts off.
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


# ===========================================================================
# 24-05-PLAN.md Task 3 (CFG-41/CFG-45/D-09): the battery chart's three
# additions, measured where they have to be correct. The selectors are
# literals here rather than imported constants, matching RING_VALUE above.
# ===========================================================================

CHART_AREA = ".sparkline-area"
CHART_LINE = ".sparkline-line"
CHART_MARK = ".sparkline-mark"
CHART_THRESHOLD = ".sparkline-threshold"
CHART_LEGEND = ".sparkline-legend"
CHART_SWATCH = ".sparkline-swatch"

# The area is a TRANSLUCENT fill, so its resolved `fill` is not what
# lands on screen — what lands is that colour composited over the card
# behind it at the resolved `fill-opacity`. Composite it here, in the
# open, and compare the result against the card's own resolved
# background through the app's OWN contrast formula
# (companion/contrast_check.py, already the source of truth for every
# colour pair this project pins).
#
# THE FLOOR IS 1.20:1, AND IT IS NOT WCAG's 3:1. That figure is for a UI
# component a user must find and identify; this is a wash under a line
# that already carries the data, and at 3:1 it would be a block of ink.
# What it must not be is PRESENT BUT INVISIBLE — technically painted,
# visually absent — which is this feature's specific failure mode.
# Measured on this tree at the shipped 0.14: light 1.33:1, dark 1.50:1;
# the 1.20 floor is first missed between fill-opacity 0.08 (1.17 light)
# and 0.09 (1.20 light), so it bites at roughly two thirds of the shipped
# value rather than sitting decoratively below it.
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
    """the battery chart's area, line, mark and threshold each resolve to a real theme
    token in BOTH themes — never the SVG default, the area/line/mark sharing one
    currentColor ink while the threshold deliberately does not, the legend's swatch
    equal to the drawn threshold, and the area's COMPOSITE over the card clearing a
    1.20:1 floor so it is visible and not merely painted (CFG-41/CFG-45, 24-05-PLAN.md
    Task 3)"""
    # Four shapes x two themes, resolved by the browser after the cascade
    # has run — the only thing in this repository that can tell a shape
    # painted by a token from a shape painted by the SVG default.
    #
    # Three DIFFERENT questions are asked, because "not the default"
    # alone would be green for a shape that is the same in both themes,
    # and "differs between themes" alone would be green for a shape
    # painted the wrong colour consistently:
    #   - the area, the line and the mark must resolve to the SAME ink,
    #     because all three are currentColor and that IS the mechanism
    #     CFG-45 asks for (the area is the line's own colour, so dark
    #     mode is correct by the same route the line already is);
    #   - the threshold must resolve to something ELSE, because a
    #     judgement painted in the data's own ink is a judgement nobody
    #     can see;
    #   - every one of them must move when the theme does, or the token
    #     is not reaching it at all.
    _login(page, server.base_url())
    page.goto(server.base_url() + "/health")
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
        card = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'.battery-trend-section')).backgroundColor")
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
    """at the 360px floor the battery chart's additions cost nothing they must not: the
    page body does not scroll sideways in EITHER language, the threshold's legend
    overlaps none of the four axis labels and stays inside its card at the 10px
    micro-label tier, its swatch measures a real 12x1 box (which an inline <span> could
    not), the canvas keeps its share of the grid rather than being squeezed by a legend
    that claimed the Y-label column, the mark's edge-hung ink stays inside the card,
    and the area, mark, threshold and legend all still render — and still paint
    dark-mode tokens — with scripts blocked (CFG-45, D-09, 24-05-PLAN.md Task 3)"""
    # The 360px floor, in both languages, because French is the longer
    # copy here ("Batterie faible — 3540 mV (≈ 20 %)") and this file
    # already carries several checks that exist because French
    # overflowed where English did not.
    #
    # WHAT THE LABEL-OVERLAP ASSERTION IS AND IS NOT. The legend sits in
    # its own full-width grid row, so no overlap with the axis labels is
    # STRUCTURAL rather than lucky — and that is precisely why the check
    # is written as a box comparison instead of "the legend is in its own
    # row": it keeps measuring the property that matters if the row is
    # ever traded for the absolute positioning a third Y-axis tick would
    # have needed. What it is NOT is the only thing measured here; the
    # swatch's own box is, and that one is not structural at all (see
    # below).
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            base_url = server.base_url()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/health")
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
                "          card: r(document.querySelector('.battery-trend-section')),"
                "          grid: r(document.querySelector('.sparkline')),"
                "          canvas: r(document.querySelector('.sparkline__canvas')),"
                "          mark: r(document.querySelector('.sparkline-mark')),"
                "          axis: [...document.querySelectorAll('.sparkline-axis-label')]"
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

            # The mark is the one new shape drawn AT the canvas's own
            # edge (cx=100%), so its radius hangs outside the plot area
            # exactly as the existing dot and hit target already do. What
            # must hold is that the card absorbs it.
            mark = boxes["mark"]
            if mark["r"] > boxes["card"]["r"] or mark["t"] < boxes["card"]["t"]:
                raise AssertionError(
                    "in %s at 360px the mark's ink %r escapes the card %r — the chart's "
                    "x scale runs edge to edge, so the newest point's radius overhangs "
                    "the canvas by design and the card's padding is what must absorb it"
                    % (lang, mark, boxes["card"]))
        finally:
            context.close()

    # D-09, through the shared helper: all three additions are
    # server-rendered SVG and owe nothing to a script. Measured in the
    # theme+no-JS combination most likely to be wrong.
    with _no_js_page(new_context, server.base_url(), "/health",
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        for label, selector in (("area", CHART_AREA), ("mark", CHART_MARK),
                                ("threshold", CHART_THRESHOLD),
                                ("legend", CHART_LEGEND)):
            if blocked.locator(selector).count() != 1:
                raise AssertionError(
                    "with scripts blocked: expected exactly one %s, got %d"
                    % (label, blocked.locator(selector).count()))
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


# ===========================================================================
# 24-06-PLAN.md Task 3 (CFG-42): the day band.
#
# THIS GROUP OWNS ITS OWN SERVER, and that is the only reason it costs a
# second subprocess. The shared `server` fixture's device_health rows are
# all BEFORE SEED_BASE_TS, so on any real wall clock the band's own Paris
# day holds nothing and there is not one mark to measure. Seeding today's
# rows into `server` itself would hand the battery chart's checks a 41st
# day bucket they do not expect; an isolated server changes no other
# check at all.
#
# The seeded hours are FIXED Paris clock positions and some of them are
# in the future relative to the wall clock when this runs. That is
# deliberate: the band is a picture of a DAY, midnight to midnight, and
# seeding by "hours before now" would make the mark count depend on what
# time the suite happened to run. No production path writes a future
# check-in.
# ===========================================================================

BAND_SEED_PARIS_HOURS = (2, 8, 12, 18, 22)
BAND_MARK = ".drawing-band-mark"
BAND_FRAME = ".drawing-band"
BAND_SPAN = ".drawing-band-span"
BAND_SECTION = ".day-band"
# The shaded span has to be tellable from the band's own surface, and
# both are the SAME token at two strengths — so this is the one number
# that says the 40% share in style.css is doing something. Shipped:
# 1.246 light, 1.208 dark. The floor bites at roughly a 25% share
# (measured: 1.15 is first missed between 40% and 25%), so it separates
# the shipped value from a decorative one rather than sitting under
# everything.
BAND_SPAN_MIN_CONTRAST = 1.15
# The band's own frame against the card behind it. Faint by design — it
# is the day, not the data — but a frame nobody can see is a band with no
# extent, and the empty day would then render as literally nothing.
# Shipped: 1.148 light, 1.106 dark.
BAND_FRAME_MIN_CONTRAST = 1.05
# A mark crossing the shaded span is where most of a night's check-ins
# land, and currentColor is what is meant to keep it readable there.
# Shipped: 12.29 light, 11.84 dark, so the ordinary text floor is a long
# way below and this asserts a property rather than a coincidence.
BAND_MARK_MIN_CONTRAST = 4.5
# The height .day-band declares, and the reason this number is asserted
# at all: it is a CSS-only value with no Python constant behind it, which
# made it invisible to every check this plan wrote until a mutation found
# it. Removing `--drawing-canvas-height: 24px` does not overflow, does
# not move a mark, does not change a colour and does not fail anything —
# the canvas simply takes .drawing__canvas's 160px default and the day
# renders as a 6.7x taller BLOCK. That is the same shape of gap 24-05
# found in its own `grid-column: 1 / -1`, and this is its assertion.
BAND_CANVAS_HEIGHT_PX = 24.0


def _band_rgba(text):
    """(r, g, b) 0-255 and alpha, from either of the two forms Chromium
    answers with.

    `color-mix()` resolves to `color(srgb 0.87 0.84 0.78 / 0.4)` —
    components 0-1 — while a plain token resolves to `rgb(223, 215,
    200)`. A single `[\\d.]+` scrape treats 0.87 as 0.87/255 of red and
    silently composites near-black; the prefix is the only thing that
    says which scale the numbers are on.
    """
    numbers = [float(v) for v in re.findall(r"[\d.]+", text)]
    if len(numbers) < 3:
        raise AssertionError("not a colour: %r" % (text,))
    if text.strip().startswith("color("):
        rgb = [v * 255 for v in numbers[:3]]
    else:
        rgb = numbers[:3]
    return rgb, (numbers[3] if len(numbers) > 3 else 1.0)


def _band_over(fg_text, bg_text):
    fg, alpha = _band_rgba(fg_text)
    bg, _ = _band_rgba(bg_text)
    return "#%02X%02X%02X" % tuple(
        int(round(alpha * f + (1 - alpha) * b)) for f, b in zip(fg, bg))


def _seed_band(state_dir):
    seed_state_dir(state_dir)
    today = datetime.now(layout.LOCAL_TZ).date()
    midnight = datetime.combine(today, datetime.min.time(), tzinfo=layout.LOCAL_TZ)
    with history_db.open_db(state_dir) as conn:
        for hour in BAND_SEED_PARIS_HOURS:
            history_db.record_device_health(
                conn, (midnight + timedelta(hours=hour)).isoformat(), battery_mv=3800)


@pytest.fixture(scope="module")
def band_server(module_app_server_factory):
    """One Paris day's worth of seeded check-ins, shared read-only by the
    day-band checks and the hero checks (the hero is what used to call
    the legacy `_band_harness()` a second time for its own two checks).
    """
    return module_app_server_factory(seed=_seed_band, fake_providers=True)


def test_the_day_bands_frame_span_and_marks_paint_real_tokens_in_both_themes(page, band_server):
    """the day band's frame, shaded span and check-in marks each resolve to a real
    theme token in BOTH themes and never the SVG default, all three move when
    the theme does, the span clears a 1.15:1 floor against the band's own
    surface (they are one token at two strengths, so 'not the default' says
    nothing about whether they can be told apart), the frame clears 1.05:1
    against its card so an empty day is not literally nothing, and a mark
    crossing the span — which is where a night's check-ins land, and the
    fixture is asserted to produce one — clears 4.5:1 over it
    (CFG-42, 24-06-PLAN.md Task 3)"""
    _login(page, band_server.base_url())
    page.goto(band_server.base_url() + layout.HOME_ROUTE)
    page.wait_for_selector(BAND_SECTION)
    if page.locator(BAND_MARK).count() != len(BAND_SEED_PARIS_HOURS):
        raise AssertionError(
            "expected %d marks from the seeded day, got %d — with a "
            "different number every paint read below is measuring "
            "something other than what was seeded"
            % (len(BAND_SEED_PARIS_HOURS), page.locator(BAND_MARK).count()))
    if page.locator(BAND_SPAN).count() != 2:
        raise AssertionError(
            "expected the fixture's 23:00-07:00 quiet hours as TWO spans, "
            "got %d" % (page.locator(BAND_SPAN).count(),))
    seen = {}
    for theme in UI_THEMES_EXPLICIT:
        _set_ui_theme(page, theme)
        frame = _computed_paint(page, BAND_FRAME, ("fill",))
        span = _computed_paint(page, BAND_SPAN, ("fill",))
        mark = _computed_paint(page, BAND_MARK, ("fill",))
        card = page.evaluate(
            "s => getComputedStyle(document.querySelector(s))"
            ".backgroundColor", BAND_SECTION)
        for name, paint in (("frame", frame), ("span", span), ("mark", mark)):
            if paint["svg_default"]:
                raise AssertionError(
                    "in %s the band's %s resolves %r to the SVG default "
                    "(%r) — it inherited no colour at all and is black in "
                    "both themes" % (theme, name, paint["svg_default"], paint["fill"]))
        frame_hex = _band_over(frame["fill"], card)
        span_hex = _band_over(span["fill"], card)
        mark_hex = _band_over(mark["fill"], card)
        card_hex = _band_over(card, card)
        # THE THREE STATEMENTS MUST BE THREE. The frame is the day, the
        # span is a window the device honours, a mark is something that
        # happened — and the first two are the same token at two
        # strengths, so "not the default" says nothing at all about
        # whether they are distinguishable.
        frame_ratio = contrast_ratio(frame_hex, card_hex)
        if frame_ratio < BAND_FRAME_MIN_CONTRAST:
            raise AssertionError(
                "in %s the band's frame composites to %s over the card's "
                "%s for %.3f:1, under this check's %.2f:1 floor — a frame "
                "nobody can see gives the band no extent, and an empty "
                "day would render as literally nothing"
                % (theme, frame_hex, card_hex, frame_ratio, BAND_FRAME_MIN_CONTRAST))
        span_ratio = contrast_ratio(span_hex, frame_hex)
        if span_ratio < BAND_SPAN_MIN_CONTRAST:
            raise AssertionError(
                "in %s the shaded span (%s) and the band's own surface "
                "(%s) differ by only %.3f:1, under this check's %.2f:1 "
                "floor — quiet hours would be shaded and invisible, which "
                "is the whole of what the span is for"
                % (theme, span_hex, frame_hex, span_ratio, BAND_SPAN_MIN_CONTRAST))
        mark_ratio = contrast_ratio(mark_hex, span_hex)
        if mark_ratio < BAND_MARK_MIN_CONTRAST:
            raise AssertionError(
                "in %s a mark (%s) over the shaded span (%s) is %.3f:1, "
                "under this check's %.2f:1 floor — most of a night's "
                "check-ins land inside that span, and currentColor is "
                "what is meant to keep them readable there"
                % (theme, mark_hex, span_hex, mark_ratio, BAND_MARK_MIN_CONTRAST))
        seen[theme] = {"frame": frame["fill"], "span": span["fill"],
                       "mark": mark["fill"], "card": card,
                       "frame_ratio": frame_ratio, "span_ratio": span_ratio,
                       "mark_ratio": mark_ratio}
    first, second = UI_THEMES_EXPLICIT
    for name in ("frame", "span", "mark", "card"):
        if seen[first][name] == seen[second][name]:
            raise AssertionError(
                "the band's %s resolves to %r in BOTH %s and %s — the "
                "theme token is not reaching it, and every assertion "
                "above has been comparing a value to itself"
                % (name, seen[first][name], first, second))
    # A mark really does cross a span in this fixture, so the contrast
    # assertion above is about a case that occurs rather than a
    # hypothetical one.
    crossing = page.evaluate(
        "() => { const r = el => el.getBoundingClientRect();"
        "  const spans = [...document.querySelectorAll('%s')].map(r);"
        "  return [...document.querySelectorAll('%s')].map(r).filter("
        "    m => spans.some(s => m.left >= s.left && m.right <= s.right)"
        "  ).length; }" % (BAND_SPAN, BAND_MARK))
    if not crossing:
        raise AssertionError(
            "no seeded mark falls inside a shaded span, so the "
            "mark-over-span contrast assertion above measured a case "
            "this fixture never produces — seed a check-in inside the "
            "23:00-07:00 window")


def test_the_day_band_is_a_real_drawing_at_360px_in_both_languages_without_script(new_context, band_server):
    """at the 360px floor the day band is a real drawing in BOTH languages: the
    page body does not scroll sideways, every mark renders at least the 2px
    draw.py declares (a mark emitted in absolute pixels into a CSS-sized canvas
    has nothing in the markup guaranteeing it survives to paint), every mark
    and span stays inside the canvas, the minimum mark spacing re-derived from
    the canvas's MEASURED width still buys the 4px its comment claims, the
    three hour labels sit at the band's own left edge, midpoint and right edge,
    the canvas is the same width in both languages, and the whole band plus its
    two shaded spans still render and still paint dark-mode tokens with scripts
    blocked (CFG-42, D-09, 24-06-PLAN.md Task 3)"""
    base_url = band_server.base_url()
    widths = {}
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + layout.HOME_ROUTE)
            page.wait_for_selector(BAND_SECTION)
            message = _assert_no_page_overflow(
                page, "%s in %s" % (layout.HOME_ROUTE, lang),
                VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)
            boxes = page.evaluate(
                "() => { const r = el => { const b ="
                " el.getBoundingClientRect(); return {l: b.left, t: b.top,"
                " r: b.right, b: b.bottom, w: b.width, h: b.height}; };"
                "  return {canvas: r(document.querySelector("
                "'%s .drawing__canvas')),"
                "          section: r(document.querySelector('%s')),"
                "          hours: [...document.querySelectorAll("
                "'.day-band__hours span')].map(r),"
                "          marks: [...document.querySelectorAll('%s')].map(r),"
                "          spans: [...document.querySelectorAll('%s')].map(r)"
                "  }; }" % (BAND_SECTION, BAND_SECTION, BAND_MARK, BAND_SPAN))
            canvas = boxes["canvas"]
            widths[lang] = canvas["w"]
            if abs(canvas["h"] - BAND_CANVAS_HEIGHT_PX) > 0.5:
                raise AssertionError(
                    "in %s the band's canvas is %.2fpx tall, not the %.2fpx "
                    ".day-band declares — at .drawing__canvas's own 160px "
                    "default the day renders as a block rather than a band, "
                    "which overflows nothing and shows up nowhere else"
                    % (lang, canvas["h"], BAND_CANVAS_HEIGHT_PX))

            # THE MEASUREMENT UNIQUE TO THIS DRAWING, and the one that
            # catches a band which is structurally perfect and visually
            # empty. A mark is emitted with an ABSOLUTE pixel width into
            # a canvas sized by CSS, so nothing in the markup guarantees
            # it survives to paint; a sub-pixel mark is not a mark.
            if len(boxes["marks"]) != len(BAND_SEED_PARIS_HOURS):
                raise AssertionError(
                    "in %s expected %d marks, got %d"
                    % (lang, len(BAND_SEED_PARIS_HOURS), len(boxes["marks"])))
            for index, mark in enumerate(boxes["marks"]):
                if mark["w"] < draw.DAY_BAND_MARK_WIDTH_PX - 0.01:
                    raise AssertionError(
                        "in %s at 360px mark %d renders %.2fpx wide, under "
                        "the %dpx draw.py declares — a mark thinner than the "
                        "ink it asks for is a mark the reader cannot see"
                        % (lang, index, mark["w"], draw.DAY_BAND_MARK_WIDTH_PX))
                if mark["h"] < 1:
                    raise AssertionError(
                        "in %s at 360px mark %d is %.2fpx tall" % (lang, index, mark["h"]))
                if (mark["l"] < canvas["l"] - 0.01
                        or mark["r"] > canvas["r"] + 0.01):
                    raise AssertionError(
                        "in %s at 360px mark %d (%.2f..%.2f) escapes the "
                        "canvas (%.2f..%.2f) — the marks are centred on "
                        "their instants precisely so a 23:5x check-in's ink "
                        "stays on the band"
                        % (lang, index, mark["l"], mark["r"], canvas["l"], canvas["r"]))
            for index, span in enumerate(boxes["spans"]):
                if (span["l"] < canvas["l"] - 0.01
                        or span["r"] > canvas["r"] + 0.01):
                    raise AssertionError(
                        "in %s at 360px shaded span %d (%.2f..%.2f) escapes "
                        "the canvas (%.2f..%.2f)"
                        % (lang, index, span["l"], span["r"], canvas["l"], canvas["r"]))

            # THE SPACING CONSTANT, RE-DERIVED FROM THE REAL WIDTH.
            # draw.py's own comment records an arithmetic — 4px centre to
            # centre, so two 2px marks keep clear ground between them —
            # and its FIRST draft did that arithmetic against an
            # estimated 330px band when the real one is 278px, which made
            # every figure in it wrong. This is the assertion that stops
            # the estimate and the layout drifting apart again: whatever
            # the canvas measures, the minimum spacing must still buy the
            # 4px.
            spacing_px = (draw.DAY_BAND_MIN_MARK_SPACING_PERCENT / 100.0 * canvas["w"])
            if spacing_px < 2 * draw.DAY_BAND_MARK_WIDTH_PX:
                raise AssertionError(
                    "in %s the canvas measures %.2fpx, so draw.py's %.2f%% "
                    "minimum spacing is %.2fpx centre to centre — under the "
                    "%dpx two %dpx marks need to keep a clear pixel between "
                    "them. The constant's derivation and this layout have "
                    "drifted apart"
                    % (lang, canvas["w"], draw.DAY_BAND_MIN_MARK_SPACING_PERCENT,
                       spacing_px, 2 * draw.DAY_BAND_MARK_WIDTH_PX,
                       draw.DAY_BAND_MARK_WIDTH_PX))

            # The hour labels are placed by the same scale the marks are:
            # first flush left, last flush right, middle centred. A row
            # that lost its flex context would stack them at the left and
            # silently mislabel the whole band.
            hours = boxes["hours"]
            if len(hours) != 3:
                raise AssertionError(
                    "in %s expected three hour labels, got %d" % (lang, len(hours)))
            if abs(hours[0]["l"] - canvas["l"]) > 1.5:
                raise AssertionError(
                    "in %s the 00:00 label starts at %.2f, not the canvas's "
                    "own left edge %.2f" % (lang, hours[0]["l"], canvas["l"]))
            if abs(hours[2]["r"] - canvas["r"]) > 1.5:
                raise AssertionError(
                    "in %s the 24:00 label ends at %.2f, not the canvas's "
                    "own right edge %.2f" % (lang, hours[2]["r"], canvas["r"]))
            middle = (hours[1]["l"] + hours[1]["r"]) / 2
            centre = (canvas["l"] + canvas["r"]) / 2
            if abs(middle - centre) > 2.0:
                raise AssertionError(
                    "in %s the 12:00 label centres at %.2f, not the band's "
                    "own midpoint %.2f — the labels and the marks are placed "
                    "by two different scales" % (lang, middle, centre))
            if hours[0]["l"] < boxes["section"]["l"] or (
                    hours[2]["r"] > boxes["section"]["r"]):
                raise AssertionError("in %s the hour labels escape their own section" % (lang,))
        finally:
            context.close()
    if abs(widths["en"] - widths["fr"]) > 0.01:
        raise AssertionError(
            "the band's canvas measures %.2fpx in English and %.2fpx in "
            "French — the drawing's width must not depend on the copy beside "
            "it" % (widths["en"], widths["fr"]))

    # D-09: server-rendered SVG owes nothing to a script, measured in the
    # theme+no-JS combination most likely to be wrong.
    with _no_js_page(new_context, base_url, layout.HOME_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        for label, selector, expected in (
                ("frame", BAND_FRAME, 1),
                ("shaded span", BAND_SPAN, 2),
                ("mark", BAND_MARK, len(BAND_SEED_PARIS_HOURS))):
            if blocked.locator(selector).count() != expected:
                raise AssertionError(
                    "with scripts blocked: expected %d %s, got %d"
                    % (expected, label, blocked.locator(selector).count()))
        _set_ui_theme(blocked, UI_THEMES_EXPLICIT[1])
        for label, selector in (("frame", BAND_FRAME), ("span", BAND_SPAN), ("mark", BAND_MARK)):
            paint = _computed_paint(blocked, selector, ("fill",))
            if paint["svg_default"]:
                raise AssertionError(
                    "with scripts blocked, in %s: the band's %s resolves %r "
                    "to the SVG default"
                    % (UI_THEMES_EXPLICIT[1], label, paint["svg_default"]))


# ===========================================================================
# 24-07-PLAN.md Task 3 (CFG-43): the regularity grid.
#
# ITS OWN SERVER, for the day band's reason and one more. The shared
# `server` fixture's newest device_health row is 40 days before
# SEED_BASE_TS, so on any real wall clock the grid's 30-day window holds
# nothing at all and every cell is the no-observation state — three of
# the four states would never be painted, and every paint assertion below
# would be measuring a colour the page does not actually use.
#
# THE FIXTURE HAS TO BE DENSE, and that is a property of the drawing
# rather than a convenience. A day is judged by its LONGEST observed gap,
# and the first gap ending on a day is the one from the previous day's
# last check-in — so a day cannot read "on cadence" unless it is covered
# end to end. At the fixture's 300s cadence (warn 900s, error 3600s) that
# means a check-in at least every 15 minutes; 10 is used, which is a real
# cadence this device ships with rather than one chosen to sit just
# inside a threshold.
# ===========================================================================

GRID_SELECTOR = ".check-in-grid"
GRID_CELL = ".drawing-cell"
GRID_SWATCH = ".check-in-key__swatch"
GRID_SEED_STEP_MINUTES = 10
# The three seeded days, newest first, each with the verdict its own
# hole produces. Day 1 (yesterday) has a 2-hour hole: past error. Day 2
# has a 30-minute hole: past warn, short of error. Day 3 has none.
GRID_SEED_DAYS = (
    (1, 120, draw.DRAWING_CELL_MISSING_CLASS),
    (2, 30, draw.DRAWING_CELL_LATE_CLASS),
    (3, 0, draw.DRAWING_CELL_ON_CADENCE_CLASS),
)
# Today is seeded with nothing, so the fourth state is produced by the
# same mechanism a real fresh deployment produces it with — an absence,
# not a special value.
GRID_STATE_CLASSES = tuple(
    [c for _, _, c in GRID_SEED_DAYS] + [draw.DRAWING_CELL_NONE_CLASS])
# The app's OWN signal-separation floor, not a number invented here: four
# states that collapse to three in dark mode is precisely the "two
# colours that read as one signal at a glance" defect that constant
# exists for. Measured at the shipped palette, the closest pair in either
# theme is light warn/error at dE76 55.3.
GRID_MIN_SEPARATION = MIN_SIGNAL_PERCEPTUAL_DISTANCE
# The three verdicts are non-text graphics carrying meaning, so
# WCAG_AA_UI_COMPONENT (3.0) is the bar — the same one
# companion/test_contrast_check.py already holds --color-status-error to
# on every surface. Measured: 3.30/3.19/6.29 light, 10.09/10.53/6.54
# dark.
GRID_MIN_VERDICT_CONTRAST = WCAG_AA_UI_COMPONENT
# The no-observation cell is DELIBERATELY below that bar and this is the
# number that says so out loud rather than leaving it unexamined. It is
# structural ink (--color-border, the token .drawing-band's own frame
# spends) because it is the ABSENCE of a verdict, and a day the record
# says nothing about must not shout as loudly as one the record faults.
# What it must still do is be visible at all: a cell nobody can see would
# make an empty month render as blank card. Measured: 1.43 light, 1.34
# dark, against a floor set just under the lower of the two. Its meaning
# is carried in text three ways regardless — the key's own word, the
# cell's title, and the caption — so colour is not the only route to it.
GRID_MIN_ABSENCE_CONTRAST = 1.25
GRID_MIN_CELL_PX = draw.CELL_MIN_SIZE_PX
GRID_SWATCH_PX = 12.0
# Two CSS-only lengths with no Python constant behind them, which is
# exactly what made 24-05's `grid-column` and 24-06's
# `--drawing-canvas-height` invisible to every check their own plans
# wrote. Both are var(--space-xs) = 4px: the clear ground under the
# canvas before its date labels, and the clear ground between a key
# swatch and the word it belongs to. Asserted here because a mutation
# proved that without them nothing at all failed.
GRID_SCALE_GAP_PX = 4.0
GRID_KEY_GAP_PX = 4.0
# And the key's own two: var(--space-sm) = 8px of clear ground above the
# whole key, and var(--space-md) = 16px between one labelled swatch and
# the next. The second is measured at 1280px, where the four items sit
# on one line; at 360px the key WRAPS (measured: without `flex-wrap` a
# French swatch is squeezed from 12.00 to 9.03px), so a gap read there
# would be reading a row break half the time.
GRID_KEY_TOP_GAP_PX = 8.0
GRID_KEY_ITEM_GAP_PX = 16.0


def _seed_grid(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, wake_interval_s=300)
    today = datetime.now(layout.LOCAL_TZ).date()
    midnight = datetime.combine(today, datetime.min.time(), tzinfo=layout.LOCAL_TZ)
    rows = []
    for days_ago, hole_minutes, _cls in sorted(GRID_SEED_DAYS, reverse=True):
        start = midnight - timedelta(days=days_ago)
        minute = 0
        while minute < 24 * 60:
            rows.append(start + timedelta(minutes=minute))
            # The hole sits mid-morning, well clear of both day
            # boundaries, so it is this day's own gap and cannot be
            # attributed to its neighbour.
            minute += (hole_minutes if minute == 8 * 60 and hole_minutes
                       else GRID_SEED_STEP_MINUTES)
    with history_db.open_db(state_dir) as conn:
        for index, ts in enumerate(rows):
            history_db.record_device_health(conn, ts.isoformat(), battery_mv=3800 + index % 7)


@pytest.fixture(scope="module")
def grid_server(module_app_server_factory):
    """Three seeded days with distinct on-cadence/late/missing verdicts,
    shared read-only by the two regularity-grid checks.
    """
    return module_app_server_factory(seed=_seed_grid, fake_providers=True)


def test_the_grids_four_states_stay_four_states_in_both_themes(page, grid_server):
    """all FOUR of the regularity grid's cell states paint a real theme token in
    BOTH themes and never the SVG default, all four move when the theme does,
    each key swatch composites to exactly the colour of the cell it explains
    (one `color` declaration, an SVG fill and an HTML background), the three
    verdicts clear WCAG AA's 3:1 non-text bar against their card while the
    no-observation state clears its own lower, deliberate 1.25:1 floor, and
    every one of the six pairs stays past the app's own
    MIN_SIGNAL_PERCEPTUAL_DISTANCE — four states that read as three in dark
    mode is a defect no source scan can see (CFG-43, CFG-45, 24-07-PLAN.md
    Task 3)"""
    _login(page, grid_server.base_url())
    page.goto(grid_server.base_url() + "/health")
    page.wait_for_selector(GRID_SELECTOR)
    counts = {cls: page.locator(".%s" % cls).count() for cls in GRID_STATE_CLASSES}
    # Every one of the four states must actually be on this page, or the
    # measurements below are of colours the fixture never produced. The
    # swatch in the key carries the same class, so each state is
    # expected at least twice: one cell and one swatch.
    missing = [c for c, n in counts.items() if n < 2]
    if missing:
        raise AssertionError(
            "the fixture did not paint every state — %r appear fewer "
            "than twice (a cell and its key swatch): %r. With one "
            "missing, every paint assertion below measures a colour "
            "this page does not use" % (missing, counts))
    seen = {}
    for theme in UI_THEMES_EXPLICIT:
        _set_ui_theme(page, theme)
        card = page.evaluate(
            "s => getComputedStyle(document.querySelector(s)"
            ".closest('section')).backgroundColor", GRID_SELECTOR)
        resolved = {}
        for cls in GRID_STATE_CLASSES:
            cell = _computed_paint(page, "rect.%s" % cls, ("fill",))
            if cell["svg_default"]:
                raise AssertionError(
                    "in %s the %s cell resolves %r to the SVG default "
                    "(%r) — it inherited no colour at all and is black "
                    "in both themes"
                    % (theme, cls, cell["svg_default"], cell["fill"]))
            swatch = page.evaluate(
                "s => getComputedStyle(document.querySelector(s))"
                ".backgroundColor", "%s.%s" % (GRID_SWATCH, cls))
            # ONE RULE, TWO KINDS OF ELEMENT. The modifier sets `color`
            # and nothing else; the cell follows it through fill:
            # currentColor and the key's swatch through background:
            # currentColor. A key that could disagree with the cells it
            # explains is worse than no key, and this is the assertion
            # that it cannot.
            if _band_over(swatch, card) != _band_over(cell["fill"], card):
                raise AssertionError(
                    "in %s the key's %s swatch paints %r while the cell "
                    "it explains paints %r — the key and the grid are "
                    "reading two different declarations"
                    % (theme, cls, swatch, cell["fill"]))
            resolved[cls] = _band_over(cell["fill"], card)
        card_hex = _band_over(card, card)
        for cls, hex_value in resolved.items():
            floor = (GRID_MIN_ABSENCE_CONTRAST if cls == draw.DRAWING_CELL_NONE_CLASS
                     else GRID_MIN_VERDICT_CONTRAST)
            ratio = contrast_ratio(hex_value, card_hex)
            if ratio < floor:
                raise AssertionError(
                    "in %s the %s cell composites to %s over the card's "
                    "%s for %.2f:1, under this check's %.2f:1 floor"
                    % (theme, cls, hex_value, card_hex, ratio, floor))
        # THE FOUR STATES STAY FOUR. "Not the default" says nothing about
        # whether two of them can be told apart, and a grid whose late
        # and missing cells read as one colour in dark mode is unreadable
        # while every source scan stays green.
        for first, second in itertools.combinations(GRID_STATE_CLASSES, 2):
            distance = perceptual_distance(resolved[first], resolved[second])
            if distance < GRID_MIN_SEPARATION:
                raise AssertionError(
                    "in %s the %s cell (%s) and the %s cell (%s) are "
                    "dE76 %.1f apart, under the app's own "
                    "MIN_SIGNAL_PERCEPTUAL_DISTANCE (%.1f) — four "
                    "states that read as three"
                    % (theme, first, resolved[first], second,
                       resolved[second], distance, GRID_MIN_SEPARATION))
        seen[theme] = dict(resolved, card=card_hex)
    first_theme, second_theme = UI_THEMES_EXPLICIT
    for cls in GRID_STATE_CLASSES + ("card",):
        if seen[first_theme][cls] == seen[second_theme][cls]:
            raise AssertionError(
                "the %s cell resolves to %r in BOTH %s and %s — the "
                "theme token is not reaching it, and every assertion "
                "above has been comparing a value to itself"
                % (cls, seen[first_theme][cls], first_theme, second_theme))


def test_the_grid_is_a_real_drawing_at_360px_in_both_languages_without_script(new_context, grid_server):
    """the regularity grid is a real drawing at the 360px floor in BOTH languages:
    the page body does not scroll sideways, a Health card's content box still
    measures the width draw.CARD_DRAWING_WIDTH_PX records, all 30 cells render
    as one square at or above the 24px floor the bucket count is supposed to
    come down for, every cell inks inside the viewBox, the wrapper is exactly
    as wide as the canvas so the two date labels sit on the first and last
    columns, the four key swatches keep their declared 12px box inside the
    card, the geometry is identical in both languages, the whole grid still
    paints dark-mode tokens with scripts blocked, and at 1280px and 320px the
    wrapper and the canvas still agree with no page overflow and no stretched
    cell (CFG-43, CFG-45, D-09, T-24-07-D, 24-07-PLAN.md Task 3)"""
    base_url = grid_server.base_url()
    # The probe every width below runs: the grid's own boxes, in CSS
    # pixels, read from the browser rather than derived from draw.py's
    # constants — which is the whole point, since those constants are
    # what is under test.
    probe = (
        "() => { const r = el => { const b = el.getBoundingClientRect();"
        "  return {l: b.left, t: b.top, r: b.right, b: b.bottom,"
        "          w: b.width, h: b.height}; };"
        "  const wrap = document.querySelector('%s');"
        "  const svg = wrap.querySelector('svg');"
        "  const vb = svg.viewBox.baseVal;"
        "  const card = wrap.closest('section');"
        "  const cs = getComputedStyle(card);"
        "  return {"
        "    wrap: r(wrap), svg: r(svg), card: r(card),"
        "    cardInner: card.clientWidth"
        "      - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),"
        "    viewBox: [vb.width, vb.height],"
        "    cells: [...svg.querySelectorAll('%s')].map(r),"
        "    inked: [...svg.querySelectorAll('%s')].map(el => {"
        "      const g = el.getBBox();"
        "      return [g.x, g.y, g.x + g.width, g.y + g.height]; }),"
        "    labels: [...wrap.querySelectorAll('.drawing-axis-label')].map(r),"
        "    key: r(document.querySelector('.check-in-key')),"
        "    keyLabels: [...document.querySelectorAll("
        "      '.check-in-key .drawing-axis-label')].map(r),"
        "    swatches: [...document.querySelectorAll('%s')].map(r)"
        "  }; }" % (GRID_SELECTOR, GRID_CELL, GRID_CELL, GRID_SWATCH))
    widths = {}
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + "/health")
            page.wait_for_selector(GRID_SELECTOR)
            message = _assert_no_page_overflow(
                page, "/health in %s" % lang, VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)
            seen = page.evaluate(probe)
            widths[lang] = seen["svg"]["w"]
            # THE CONSTANT RE-DERIVED FROM THE REAL CARD, never assumed.
            # draw.py's own CARD_DRAWING_WIDTH_PX records a measurement
            # of exactly this box; 24-06 planned against an estimate that
            # was 52px wrong, so the measurement and the constant are
            # compared here rather than trusted in parallel.
            if abs(seen["cardInner"] - draw.CARD_DRAWING_WIDTH_PX) > 0.51:
                raise AssertionError(
                    "in %s a Health card's content box measures %.2fpx at "
                    "the 360px floor, against the %dpx "
                    "draw.CARD_DRAWING_WIDTH_PX records — every cell size "
                    "derived from that constant is derived from a number "
                    "the layout no longer has"
                    % (lang, seen["cardInner"], draw.CARD_DRAWING_WIDTH_PX))
            cells = seen["cells"]
            if len(cells) != health_page.CHECK_IN_WINDOW_DAYS:
                raise AssertionError(
                    "in %s the grid draws %d cells, not the %d-day window"
                    % (lang, len(cells), health_page.CHECK_IN_WINDOW_DAYS))
            smallest = min(min(c["w"], c["h"]) for c in cells)
            if smallest < GRID_MIN_CELL_PX:
                raise AssertionError(
                    "in %s the smallest cell renders %.2fpx at the 360px "
                    "floor, under the %dpx target-size floor the bucket "
                    "count is supposed to come down for"
                    % (lang, smallest, GRID_MIN_CELL_PX))
            widest = max(c["w"] for c in cells)
            if abs(widest - smallest) > 0.51:
                raise AssertionError(
                    "in %s the cells render between %.2f and %.2fpx — they "
                    "are meant to be one square" % (lang, smallest, widest))
            # THE VIEWBOX CONTAINS ITS OWN INK. 24-07-PLAN.md left the
            # containment proof owed by whichever label mechanism Task 1
            # chose; it chose HTML spans OUTSIDE the canvas, so there is
            # no SVG text to contain and the hard half of that question
            # does not arise. The cells' own geometry is still measured
            # here rather than skipped, because the grid is aspect-locked
            # and a cell painted past the viewBox clips in one browser
            # and not another.
            box_w, box_h = seen["viewBox"]
            for x0, y0, x1, y1 in seen["inked"]:
                if x0 < -0.01 or y0 < -0.01 or x1 > box_w + 0.01 or y1 > box_h + 0.01:
                    raise AssertionError(
                        "in %s a cell inks (%.2f, %.2f)-(%.2f, %.2f), "
                        "outside the %.2fx%.2f viewBox"
                        % (lang, x0, y0, x1, y1, box_w, box_h))
            # ONE SCALE PLACES THE CELLS AND THE LABELS. The label row
            # sizes itself from its wrapper, so the newest day's label
            # only sits under the newest column while the wrapper is
            # exactly as wide as the canvas — which is `width:
            # max-content`'s entire job.
            if abs(seen["wrap"]["w"] - seen["svg"]["w"]) > 0.51:
                raise AssertionError(
                    "in %s the grid's wrapper is %.2fpx wide against a "
                    "%.2fpx canvas, so its date labels are spread across a "
                    "width the cells do not occupy"
                    % (lang, seen["wrap"]["w"], seen["svg"]["w"]))
            scale = [b for b in seen["labels"]]
            if len(scale) != 2:
                raise AssertionError(
                    "in %s the grid carries %d date labels, expected the "
                    "oldest and the newest" % (lang, len(scale)))
            if abs(scale[0]["l"] - seen["svg"]["l"]) > 1.01:
                raise AssertionError(
                    "in %s the oldest date label starts at %.2f against a "
                    "canvas left edge of %.2f" % (lang, scale[0]["l"], seen["svg"]["l"]))
            if abs(scale[-1]["r"] - seen["svg"]["r"]) > 1.01:
                raise AssertionError(
                    "in %s the newest date label ends at %.2f against a "
                    "canvas right edge of %.2f — the labels and the cells "
                    "are placed by two scales"
                    % (lang, scale[-1]["r"], seen["svg"]["r"]))
            if abs((scale[0]["t"] - seen["svg"]["b"]) - GRID_SCALE_GAP_PX) > 1.01:
                raise AssertionError(
                    "in %s the date labels sit %.2fpx under the canvas, not "
                    "the %.0fpx of clear ground the scale row declares — a "
                    "CSS-only length with no Python constant behind it is "
                    "exactly the kind this phase keeps finding unmeasured"
                    % (lang, scale[0]["t"] - seen["svg"]["b"], GRID_SCALE_GAP_PX))
            # The key: four swatches at their declared size, inside the
            # card, wrapped rather than overflowing.
            if len(seen["swatches"]) != len(GRID_STATE_CLASSES):
                raise AssertionError(
                    "in %s the key carries %d swatches, expected %d"
                    % (lang, len(seen["swatches"]), len(GRID_STATE_CLASSES)))
            for swatch in seen["swatches"]:
                if (abs(swatch["w"] - GRID_SWATCH_PX) > 0.51
                        or abs(swatch["h"] - GRID_SWATCH_PX) > 0.51):
                    raise AssertionError(
                        "in %s a key swatch renders %.2fx%.2f, not the "
                        "%.0fpx square it declares — a swatch a flex line "
                        "squeezed to nothing explains nothing"
                        % (lang, swatch["w"], swatch["h"], GRID_SWATCH_PX))
                if swatch["r"] > seen["card"]["r"] + 0.51:
                    raise AssertionError(
                        "in %s a key swatch reaches %.2f, past its card's "
                        "own right edge at %.2f" % (lang, swatch["r"], seen["card"]["r"]))
            if abs((seen["key"]["t"] - seen["wrap"]["b"]) - GRID_KEY_TOP_GAP_PX) > 1.01:
                raise AssertionError(
                    "in %s the key sits %.2fpx under the drawing, not the "
                    "%.0fpx it declares"
                    % (lang, seen["key"]["t"] - seen["wrap"]["b"], GRID_KEY_TOP_GAP_PX))
            if len(seen["keyLabels"]) != len(seen["swatches"]):
                raise AssertionError(
                    "in %s the key carries %d swatches and %d words"
                    % (lang, len(seen["swatches"]), len(seen["keyLabels"])))
            for swatch, word in zip(seen["swatches"], seen["keyLabels"]):
                if abs((word["l"] - swatch["r"]) - GRID_KEY_GAP_PX) > 1.01:
                    raise AssertionError(
                        "in %s a key swatch and its word are %.2fpx apart, "
                        "not the %.0fpx the key declares — the second of "
                        "this drawing's two unbacked CSS lengths"
                        % (lang, word["l"] - swatch["r"], GRID_KEY_GAP_PX))
                # A third declaration a first mutation found INERT to
                # every assertion here: the swatch carries an explicit
                # height, so the flex default cannot stretch it and
                # `align-items: center` moves only where it sits on its
                # own line. That is a visible property, so it is asserted
                # rather than deleted.
                swatch_mid = (swatch["t"] + swatch["b"]) / 2
                word_mid = (word["t"] + word["b"]) / 2
                if abs(swatch_mid - word_mid) > 1.01:
                    raise AssertionError(
                        "in %s a key swatch's centre sits %.2fpx off its "
                        "own word's — the two read as a swatch and a "
                        "caption rather than as one labelled sample"
                        % (lang, swatch_mid - word_mid))
        finally:
            context.close()
    if abs(widths["en"] - widths["fr"]) > 0.51:
        raise AssertionError(
            "the grid is %.2fpx wide in English and %.2fpx in French — its "
            "geometry must not depend on the copy around it"
            % (widths["en"], widths["fr"]))
    # AND WITH SCRIPTS BLOCKED. D-09's floor: the verdicts are computed in
    # Python and the grid arrives complete, so this is the same drawing
    # with the same colours and not a reduced one.
    with _no_js_page(new_context, base_url, "/health",
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        blocked.wait_for_selector(GRID_SELECTOR)
        _set_ui_theme(blocked, UI_THEMES_EXPLICIT[1])
        if blocked.locator(GRID_CELL).count() != health_page.CHECK_IN_WINDOW_DAYS:
            raise AssertionError(
                "with scripts blocked the grid draws %d cells, not the "
                "%d-day window"
                % (blocked.locator(GRID_CELL).count(), health_page.CHECK_IN_WINDOW_DAYS))
        if blocked.locator(GRID_SWATCH).count() != len(GRID_STATE_CLASSES):
            raise AssertionError(
                "with scripts blocked the key carries %d swatches, expected "
                "%d — the reading of the colours is as server-rendered as "
                "the colours" % (blocked.locator(GRID_SWATCH).count(), len(GRID_STATE_CLASSES)))
        for cls in GRID_STATE_CLASSES:
            paint = _computed_paint(blocked, "rect.%s" % cls, ("fill",))
            if paint["svg_default"]:
                raise AssertionError(
                    "with scripts blocked, in %s: the %s cell resolves %r "
                    "to the SVG default"
                    % (UI_THEMES_EXPLICIT[1], cls, paint["svg_default"]))
        message = _assert_no_page_overflow(
            blocked, "/health with scripts blocked", VIEWPORT_MIN_SUPPORTED["width"])
        if message:
            raise AssertionError(message)
    # THE TWO RESPONSIVE DECLARATIONS, each measured at the width where it
    # is the one doing the work. At 1280 the card is far wider than the
    # drawing, so `width: max-content` is what keeps the label row on the
    # cells (asserted above at 360, where the two widths happen to
    # coincide — so 360 alone could not tell the property from its
    # absence). At 320, out of contract and still measured by this file,
    # the canvas is wider than the card and `max-width`/`height: auto`
    # are the only things between this drawing and a horizontal page
    # scrollbar.
    for width in (VIEWPORT_DESKTOP["width"], VIEWPORT_WIDTH_NARROW):
        context = new_context(viewport={"width": width, "height": 844})
        try:
            page = context.new_page()
            _login(page, base_url)
            page.goto(base_url + "/health")
            page.wait_for_selector(GRID_SELECTOR)
            message = _assert_no_page_overflow(page, "/health at %dpx" % width, width)
            if message:
                raise AssertionError(message)
            seen = page.evaluate(probe)
            if abs(seen["wrap"]["w"] - seen["svg"]["w"]) > 0.51:
                raise AssertionError(
                    "at %dpx the grid's wrapper is %.2fpx against a %.2fpx "
                    "canvas — the label row is spread across a width the "
                    "cells do not occupy"
                    % (width, seen["wrap"]["w"], seen["svg"]["w"]))
            if seen["svg"]["w"] > seen["cardInner"] + 0.51:
                raise AssertionError(
                    "at %dpx the canvas is %.2fpx inside a %.2fpx card"
                    % (width, seen["svg"]["w"], seen["cardInner"]))
            if width == VIEWPORT_DESKTOP["width"]:
                # One line, four items, three gaps.
                tops = {round(b["t"], 1) for b in seen["swatches"]}
                if len(tops) != 1:
                    raise AssertionError(
                        "at %dpx the key's four items sit on %d lines (%r) "
                        "— there is 830px of card and nothing to wrap for"
                        % (width, len(tops), sorted(tops)))
                for word, swatch in zip(seen["keyLabels"], seen["swatches"][1:]):
                    gap = swatch["l"] - word["r"]
                    if abs(gap - GRID_KEY_ITEM_GAP_PX) > 1.01:
                        raise AssertionError(
                            "at %dpx two of the key's labelled swatches are "
                            "%.2fpx apart, not the %.0fpx the key declares "
                            "— four states running together read as one "
                            "sentence" % (width, gap, GRID_KEY_ITEM_GAP_PX))
            box_w, box_h = seen["viewBox"]
            rendered_ratio = seen["svg"]["w"] / seen["svg"]["h"]
            if abs(rendered_ratio - box_w / box_h) > 0.02:
                raise AssertionError(
                    "at %dpx the canvas renders %.2fx%.2f, an aspect of "
                    "%.3f against the viewBox's own %.3f — the cells are no "
                    "longer square"
                    % (width, seen["svg"]["w"], seen["svg"]["h"], rendered_ratio, box_w / box_h))
        finally:
            context.close()


# ===========================================================================
# 24-08-PLAN.md Task 3 (CFG-44/CFG-45/D-09): the hero.
#
# REUSES `band_server` rather than a server of its own: it is the only
# fixture in this group that seeds check-ins on the band's OWN Paris day,
# which is what makes the hero's band a real drawing instead of an empty
# frame — and it seeds a battery reading with them, so the ring renders
# too. A hero measured over an empty band would pass every stacking
# assertion below while showing nothing.
#
# WHAT THIS ASKS THAT A SOURCE SCAN CANNOT. "The hero stacks at 360px
# with its parts at full size" is a sentence about rendered boxes: the
# markup is identical whether the ring measures 36px or has been scaled
# to 12 by a flex context, and "fits by shrinking its parts" is a page
# that passes an overflow check and fails the requirement.
# The ring's BOX is the <svg> the emitter sized, never the value arc
# inside it: the arc's own bounding rectangle is its diameter (30.24px at
# this size), which is a true number about the wrong element and reads
# as a shrunken ring. The arc selector is kept for the paint measurement,
# where the arc IS the subject.
# ===========================================================================

HERO_RING_FIGURE = " svg.drawing__figure"
HERO_RING = " .drawing-ring-value"
HERO_BAND_CANVAS = " .day-band .drawing__canvas"
HERO_BAND_MARK = " .drawing-band-mark"
HERO_AFTER = ".home-columns.home-picture-row"
# The two sizes the hero must NOT change, each chosen from the 360px
# floor by the plan that emitted the drawing: 24-04's small ring
# (home_page.BATTERY_RING_SIZE, read from the module rather than
# restated) and 24-06's MEASURED 278px band canvas.
#
# 278 is pinned here as an equality and not as a floor, and that is the
# point of it: draw.DAY_BAND_MIN_MARK_SPACING_PERCENT was re-derived from
# this exact number, so a hero that narrowed the band would leave two
# check-in marks closer than the 4px that derivation bought while
# overflowing nothing and moving no other measurement in this file.
HERO_BAND_CANVAS_WIDTH_PX = 278.0
# The composition, as two numbers. The parts sit one --space-md apart
# inside the container and the container sits one --space-lg above what
# follows it: bound tighter than they are separated, which is the whole
# of the claim that Home's top is ONE thing. Both are CSS-only values
# with no Python constant behind them — the shape of gap 24-06 found in
# `--drawing-canvas-height: 24px` and 24-05 in `grid-column: 1 / -1`,
# each invisible to every source scan until a mutation went looking.
HERO_INNER_GAP_PX = 16.0
HERO_OUTER_GAP_PX = 24.0


def _hero_boxes(page, hero_selector):
    """The hero's own box, its children's, the status tiles', the ring's,
    the band canvas's and the box of whatever follows the hero — one
    probe, so the two checks below measure the same things the same way.
    """
    return page.evaluate(
        "args => {"
        "  const r = el => { const b = el.getBoundingClientRect();"
        "    return {l: b.left, t: b.top, r: b.right, bo: b.bottom,"
        "            w: b.width, h: b.height}; };"
        "  const one = s => { const e = document.querySelector(s);"
        "    return e ? r(e) : null; };"
        "  const hero = document.querySelector(args.hero);"
        "  if (!hero) return null;"
        "  return {hero: r(hero),"
        "          children: [...hero.children].map(r),"
        "          tiles: [...document.querySelectorAll("
        "            args.hero + ' .home-status-grid .stat-tile')].map(r),"
        "          ring: one(args.hero + args.ring),"
        "          band: one(args.hero + args.band),"
        "          marks: [...document.querySelectorAll("
        "            args.hero + args.mark)].map(r),"
        "          after: one(args.after)};"
        "}",
        {"hero": hero_selector, "ring": HERO_RING_FIGURE,
         "band": HERO_BAND_CANVAS, "mark": HERO_BAND_MARK,
         "after": HERO_AFTER})


def _hero_stack_failure(seen, where):
    """"" when the hero's children share one column with the declared
    gap between them, or a finished sentence naming the measurement that
    says otherwise.

    ONE COLUMN IS THREE PROPERTIES, not one. Equal lefts alone are
    satisfied by three boxes drawn on top of each other; equal widths
    alone by a row; so the vertical order is asserted too, and the gap
    between consecutive children is asserted as an EQUALITY rather than a
    minimum — a 40px gap is what a hero whose children kept their own
    bottom margins would render, and it passes every "at least" a reader
    would think to write.
    """
    children = seen["children"]
    if len(children) < 3:
        return ("%s: the hero holds %d children — the strip, the tiles and the "
                "band are three, and a hero measured with a part missing "
                "measures nothing" % (where, len(children)))
    first = children[0]
    for index, box in enumerate(children[1:], start=1):
        if abs(box["l"] - first["l"]) > 0.51:
            return ("%s: hero child %d starts at %.2f against the first child's "
                    "%.2f — the hero is not one column"
                    % (where, index, box["l"], first["l"]))
        if abs(box["w"] - first["w"]) > 0.51:
            return ("%s: hero child %d is %.2fpx wide against the first child's "
                    "%.2f — the hero is not one column"
                    % (where, index, box["w"], first["w"]))
    for index in range(len(children) - 1):
        gap = children[index + 1]["t"] - children[index]["bo"]
        if abs(gap - HERO_INNER_GAP_PX) > 0.51:
            return ("%s: the hero's parts %d and %d sit %.2fpx apart, not the "
                    "%.0fpx one --space-md declares. 40px is what three parts "
                    "that kept their own bottom margins render, and it reads as "
                    "three stacked blocks rather than one composition"
                    % (where, index, index + 1, gap, HERO_INNER_GAP_PX))
    if seen["after"] is None:
        return "%s: found nothing after the hero to measure its own gap against" % (where,)
    outer = seen["after"]["t"] - seen["hero"]["bo"]
    if abs(outer - HERO_OUTER_GAP_PX) > 0.51:
        return ("%s: the hero sits %.2fpx above the picture row, not the %.0fpx "
                "one --space-lg declares — the group has to be separated from "
                "what follows it by MORE than its parts are separated from each "
                "other, or the grouping says nothing"
                % (where, outer, HERO_OUTER_GAP_PX))
    if outer <= HERO_INNER_GAP_PX:
        return ("%s: the hero's inner gap (%.0fpx) is not smaller than its outer "
                "one (%.2fpx)" % (where, HERO_INNER_GAP_PX, outer))
    return ""


def test_the_hero_stacks_at_360px_with_its_parts_at_the_size_their_own_plans_chose(new_context, band_server):
    """at the 360px floor D4's hero STACKS rather than shrinks, in both languages:
    its three parts share one column with exactly the 16px one --space-md
    declares between them and 24px below the group (bound tighter than it is
    separated, asserted as equalities because a 40px gap is what parts keeping
    their own margins render and passes every 'at least'), the battery ring
    still renders at the 36px home_page.BATTERY_RING_SIZE declares and the day
    band's canvas at the 278px draw.py's mark spacing was derived from, all
    five seeded check-ins still draw, the page body does not scroll sideways,
    the hero is the same width in both languages, and the ring and the band
    paint real inverting tokens in BOTH themes through selectors scoped INSIDE
    the hero (CFG-44, CFG-45, 24-08-PLAN.md Task 3)"""
    hero_selector = "." + home_page.HERO_CLASS
    base_url = band_server.base_url()
    widths = {}
    for lang in ("en", "fr"):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        try:
            page = context.new_page()
            _login(page, base_url)
            context.add_cookies([{
                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
            page.goto(base_url + layout.HOME_ROUTE)
            page.wait_for_selector(hero_selector)
            message = _assert_no_page_overflow(
                page, "%s in %s" % (layout.HOME_ROUTE, lang), VIEWPORT_MIN_SUPPORTED["width"])
            if message:
                raise AssertionError(message)
            seen = _hero_boxes(page, hero_selector)
            if seen is None:
                raise AssertionError("in %s there is no hero on Home" % (lang,))
            message = _hero_stack_failure(
                seen, "in %s at %dpx" % (lang, VIEWPORT_MIN_SUPPORTED["width"]))
            if message:
                raise AssertionError(message)
            widths[lang] = seen["hero"]["w"]

            # THE PARTS AT FULL SIZE. A composition that fits by scaling
            # its parts down has passed the overflow check above and
            # failed the requirement: at 12px the ring is a dot and the
            # band is a texture.
            if seen["ring"] is None:
                raise AssertionError(
                    "in %s the hero draws no battery ring at %dpx"
                    % (lang, VIEWPORT_MIN_SUPPORTED["width"]))
            # `ring` is the emitter's own <svg> box — see HERO_RING_FIGURE
            # above for why it is not the value arc.
            for axis, label in (("w", "wide"), ("h", "tall")):
                if abs(seen["ring"][axis] - float(home_page.BATTERY_RING_SIZE)) > 0.51:
                    raise AssertionError(
                        "in %s the hero's ring renders %.2fpx %s, not the "
                        "%dpx home_page.BATTERY_RING_SIZE declares — a hero "
                        "that fits by shrinking its parts has passed an "
                        "overflow check and failed CFG-44"
                        % (lang, seen["ring"][axis], label, home_page.BATTERY_RING_SIZE))
            if seen["band"] is None:
                raise AssertionError(
                    "in %s the hero draws no day band at %dpx"
                    % (lang, VIEWPORT_MIN_SUPPORTED["width"]))
            if abs(seen["band"]["w"] - HERO_BAND_CANVAS_WIDTH_PX) > 0.51:
                raise AssertionError(
                    "in %s the hero's band canvas measures %.2fpx, not the "
                    "%.2fpx 24-06 measured and derived draw.py's %.2f%% "
                    "minimum mark spacing from — narrowing the band inside "
                    "the hero silently invalidates that derivation"
                    % (lang, seen["band"]["w"], HERO_BAND_CANVAS_WIDTH_PX,
                       draw.DAY_BAND_MIN_MARK_SPACING_PERCENT))
            if abs(seen["band"]["h"] - BAND_CANVAS_HEIGHT_PX) > 0.51:
                raise AssertionError(
                    "in %s the hero's band canvas is %.2fpx tall, not the "
                    "%.2fpx .day-band declares" % (lang, seen["band"]["h"], BAND_CANVAS_HEIGHT_PX))
            if len(seen["marks"]) != len(BAND_SEED_PARIS_HOURS):
                raise AssertionError(
                    "in %s the hero's band draws %d marks, not the %d "
                    "check-ins seeded on its day — a band inside a hero is "
                    "still a drawing of the day"
                    % (lang, len(seen["marks"]), len(BAND_SEED_PARIS_HOURS)))

            # BOTH THEMES, SCOPED INSIDE THE HERO. The paint is 24-04's
            # and 24-06's property; what is new here is the SCOPE — these
            # selectors only match if the drawings really are the hero's
            # children in a real DOM, which no string containment in a
            # source scan can establish.
            painted = {}
            for theme in UI_THEMES_EXPLICIT:
                _set_ui_theme(page, theme)
                for label, selector, prop in (
                        ("ring value arc", hero_selector + HERO_RING, "stroke"),
                        ("band mark", hero_selector + HERO_BAND_MARK, "fill")):
                    paint = _computed_paint(page, selector, ("fill", "stroke"))
                    if prop in paint["svg_default"]:
                        raise AssertionError(
                            "in %s, %s: the hero's %s resolves %s to the "
                            "SVG default — a drawing correct in one theme "
                            "only is a defect"
                            % (lang, theme, label, prop))
                    painted.setdefault(label, []).append(paint[prop])
            for label, values in painted.items():
                if len(set(values)) != len(values):
                    raise AssertionError(
                        "in %s the hero's %s paints %r in every theme — "
                        "either the token does not invert or this "
                        "measurement is comparing a value with itself"
                        % (lang, label, values[0]))
        finally:
            context.close()
    if abs(widths["en"] - widths["fr"]) > 0.01:
        raise AssertionError(
            "the hero measures %.2fpx in English and %.2fpx in French — the "
            "composition's width must not depend on the copy inside it"
            % (widths["en"], widths["fr"]))


def test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script(new_context, band_server):
    """the hero's grouping is the same composition at 360px and at 1280px — one
    column with the same 16px inside and 24px below at both, no page overflow
    at either — while the three status tiles inside it stack at the floor and
    share one row on the desktop, so the stack is a FLOOR behaviour rather than
    the only one; the band gets MORE room as the viewport grows, never less;
    every one of Home's declared refresh-swap selectors still matches a real
    element through the browser's own selector engine (a stale one stops the
    live refresh silently); and with scripts blocked the hero's children keep
    their lefts, widths and gaps and both drawings keep their boxes (CFG-44,
    CFG-45, D-09, 24-08-PLAN.md Task 3)"""
    hero_selector = "." + home_page.HERO_CLASS
    home_regions = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_HOME]
    base_url = band_server.base_url()
    measured = {}
    for viewport in (VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP):
        width = viewport["width"]
        context = new_context(viewport=viewport)
        try:
            page = context.new_page()
            _login(page, base_url)
            page.goto(base_url + layout.HOME_ROUTE)
            page.wait_for_selector(hero_selector)
            message = _assert_no_page_overflow(
                page, "%s at %dpx" % (layout.HOME_ROUTE, width), width)
            if message:
                raise AssertionError(message)
            seen = _hero_boxes(page, hero_selector)
            if seen is None:
                raise AssertionError("no hero on Home at %dpx" % (width,))
            message = _hero_stack_failure(seen, "at %dpx" % (width,))
            if message:
                raise AssertionError(message)
            measured[width] = seen

            # THE REGISTRY, THROUGH A REAL SELECTOR ENGINE.
            # companion/static/freshness.js reads these five selectors
            # and swaps what they match; one that matches nothing fails
            # SILENTLY — the page simply stops refreshing — and
            # restructuring Home's DOM is exactly how that happens. Asked
            # here rather than through the Flights-style witness literal
            # on purpose: a witness is a SECOND transcription of the
            # selector, and it can agree with the page while the selector
            # itself disagrees.
            if not home_regions:
                raise AssertionError(
                    "Home declares no refresh regions at all — with none, this measures nothing")
            missing = page.evaluate(
                "sels => sels.filter(s => document.querySelectorAll(s).length === 0)",
                list(home_regions))
            if missing:
                raise AssertionError(
                    "at %dpx these declared Home refresh regions match "
                    "nothing in the rendered page: %r — a stale swap "
                    "selector stops the live refresh and says nothing"
                    % (width, missing))
        finally:
            context.close()

    # THE STACK IS A FLOOR, NOT THE ONLY BEHAVIOUR. The hero itself is
    # one column at every width by design — a column of its own would
    # have to put the band in it, and a one-third column is NARROWER
    # than the 278px the band already gets at 360px. What changes with
    # the viewport is the PARTS: the three status tiles stack at the
    # floor and share one row on the desktop.
    floor_tiles = measured[VIEWPORT_MIN_SUPPORTED["width"]]["tiles"]
    desk_tiles = measured[VIEWPORT_DESKTOP["width"]]["tiles"]
    if len(floor_tiles) != 3 or len(desk_tiles) != 3:
        raise AssertionError(
            "expected three status tiles inside the hero at both widths, "
            "got %d and %d" % (len(floor_tiles), len(desk_tiles)))
    if len({round(box["t"], 1) for box in floor_tiles}) != 3:
        raise AssertionError(
            "at %dpx the hero's three tiles do not each take their own row "
            "— the floor behaviour is a stack" % (VIEWPORT_MIN_SUPPORTED["width"],))
    if len({round(box["t"], 1) for box in desk_tiles}) != 1:
        raise AssertionError(
            "at %dpx the hero's three tiles sit on %d rows — the stack is "
            "the FLOOR behaviour, not the only one"
            % (VIEWPORT_DESKTOP["width"], len({round(box["t"], 1) for box in desk_tiles})))
    floor_band = measured[VIEWPORT_MIN_SUPPORTED["width"]]["band"]
    desk_band = measured[VIEWPORT_DESKTOP["width"]]["band"]
    if floor_band is None or desk_band is None:
        raise AssertionError("the hero drew no band at one of the two widths")
    if desk_band["w"] <= floor_band["w"]:
        raise AssertionError(
            "the hero's band measures %.2fpx at %dpx and %.2fpx at %dpx — "
            "a composition that gives a drawing LESS room as the viewport "
            "grows has put it in a column of its own"
            % (floor_band["w"], VIEWPORT_MIN_SUPPORTED["width"],
               desk_band["w"], VIEWPORT_DESKTOP["width"]))

    # D-09: the hero is server-rendered markup, so with scripts blocked
    # it is not merely present — it is laid out identically. Compared as
    # the hero's OWN geometry (each child's left, width and the gap to
    # the next) rather than as absolute page positions, because the
    # freshness line and the relative-time ticker above it are scripted
    # and may legitimately reflow the header by a pixel.
    with _no_js_page(new_context, base_url, layout.HOME_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED) as blocked:
        blocked_seen = _hero_boxes(blocked, hero_selector)
        if blocked_seen is None:
            raise AssertionError("with scripts blocked there is no hero on Home")
        message = _hero_stack_failure(blocked_seen, "with scripts blocked")
        if message:
            raise AssertionError(message)
        scripted = measured[VIEWPORT_MIN_SUPPORTED["width"]]
        if len(blocked_seen["children"]) != len(scripted["children"]):
            raise AssertionError(
                "with scripts blocked the hero holds %d children against "
                "%d with scripts"
                % (len(blocked_seen["children"]), len(scripted["children"])))
        for index, (was, now_box) in enumerate(
                zip(scripted["children"], blocked_seen["children"])):
            for axis in ("l", "w"):
                if abs(was[axis] - now_box[axis]) > 0.51:
                    raise AssertionError(
                        "with scripts blocked hero child %d differs on %r: "
                        "%.2f against %.2f — nothing here may depend on a "
                        "script having measured something"
                        % (index, axis, now_box[axis], was[axis]))
        for label, was, now_box in (
                ("ring", scripted["ring"], blocked_seen["ring"]),
                ("band", scripted["band"], blocked_seen["band"])):
            if was is None or now_box is None:
                raise AssertionError("the hero's %s is missing from one of the two runs" % (label,))
            if abs(was["w"] - now_box["w"]) > 0.51 or abs(was["h"] - now_box["h"]) > 0.51:
                raise AssertionError(
                    "with scripts blocked the hero's %s measures %.2fx%.2f "
                    "against %.2fx%.2f with scripts"
                    % (label, now_box["w"], now_box["h"], was["w"], was["h"]))
        missing = blocked.evaluate(
            "sels => sels.filter(s => document.querySelectorAll(s).length === 0)",
            list(home_regions))
        if missing:
            raise AssertionError(
                "with scripts blocked these declared Home refresh regions "
                "match nothing: %r" % (missing,))
