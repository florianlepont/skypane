#!/usr/bin/env python3
"""Contract harness for server/plane/render.py's state colour field and
label (PLANE-01/PLANE-02 visual contract, 02-UI-SPEC.md Revision 2).

Stdlib-only, plus the module under test (server.plane.render,
server.panel_format) - render.py transitively imports Pillow, so this
harness must be run under server/.venv's interpreter, not the bare system
python3. Exits 0 only when every check below passes; any failure (or
exception - none is ever swallowed into a pass) exits 1.

This harness asserts on the rendered canvas and packed bytes only - never
on a screenshot. "Dominant nibble" means the most common nibble by count,
which is unambiguous for a full-bleed field.

02-04 addition (route line / airline line, zones 7-9): text-content
assertions for these zones are made by monkeypatching
`render.draw_tracked_text` (captures the "TO"/"FROM" Label-role prefix)
and `render.ImageDraw.ImageDraw.text` (captures every Body-role run - the
city name, the airline name, and the "Route unavailable" fallback copy),
then asserting on the captured strings/positions directly. This was picked
over rendering each caption to its own scratch canvas and comparing pixel
signatures because it asserts on exactly what the render pipeline
received, without needing OCR or a second rendering pass.

Usage:
    server/.venv/bin/python3 server/test_render.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 37

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}

TEST_FLIGHT = {"hex": "3985a7", "callsign": "AF1380"}

# A real resolved route (server/fixtures/adsbdb_hit_TVF16VB.json, already
# sentence-cased per server.plane.enrich.to_sentence_case_city) - used to
# exercise zones 7/9's "hit" branch without importing server.plane.enrich
# itself (this harness's contract is render.py's, not enrich.py's).
TEST_ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
}

# 03-01 Task 2 (D-04's automated half): a genuinely long real destination
# city name and a genuinely long real airline name, used to exercise the
# shrink path at the new 64px Destination/Origin hero-secondary size - the
# on-glass half of D-04 is 03-04.
TEST_LONG_ROUTE = {
    "airline_name": "Compagnie Nationale Royale Air Maroc Express",
    "origin_iata": "SCQ",
    "origin_city": "Santiago de Compostela–Rosalía de Castro",
    "destination_iata": "ORY",
    "destination_city": "Paris",
}


def nibble_counts(buf):
    counts = {}
    for b in buf:
        for nibble in ((b >> 4) & 0xF, b & 0xF):
            counts[nibble] = counts.get(nibble, 0) + 1
    return counts


def dominant_nibble(buf):
    counts = nibble_counts(buf)
    return max(counts, key=counts.get)


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.plane.render as render
        import server.panel_format as panel_format
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before this
        # slice's render.py state-colour/label work exists. It must fail -
        # Task 3 turns it green.
        print("FAIL import server.plane.render / server.panel_format - %r" % (exc,))
        print("render: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    ctx = {}

    # 1-2. Both active states pack to exactly 960000 bytes with only legal nibble codes.
    def _departing_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "departing")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "departing render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "departing render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["departing_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'departing') packs to exactly 960000 bytes with only legal nibbles", _departing_packs_correctly)

    def _arriving_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "arriving")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "arriving render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "arriving render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["arriving_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'arriving') packs to exactly 960000 bytes with only legal nibbles", _arriving_packs_correctly)

    # 3-4. Dominant nibble per state.
    def _departing_dominant_is_blue():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_BLUE:
            return False, "departing render's dominant nibble is 0x%x, expected 0x5 (Blue)" % dom
        return True, ""
    check("departing render's dominant nibble is 0x5 (Blue)", _departing_dominant_is_blue)

    def _arriving_dominant_is_green():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_GREEN:
            return False, "arriving render's dominant nibble is 0x%x, expected 0x6 (Green)" % dom
        return True, ""
    check("arriving render's dominant nibble is 0x6 (Green)", _arriving_dominant_is_green)

    # 5-6. Black drops out of the active states (UI-SPEC Revision 2).
    def _departing_has_no_black():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        if NIBBLE_BLACK in nibble_counts(buf):
            return False, "departing render contains a Black (0x0) nibble - UI-SPEC's 'Black drops out of the active states' violated"
        return True, ""
    check("departing render contains no Black (0x0) nibble", _departing_has_no_black)

    def _arriving_has_no_black():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        if NIBBLE_BLACK in nibble_counts(buf):
            return False, "arriving render contains a Black (0x0) nibble - UI-SPEC's 'Black drops out of the active states' violated"
        return True, ""
    check("arriving render contains no Black (0x0) nibble", _arriving_has_no_black)

    # 7-8. Foreground content exists (at least one White nibble).
    def _departing_has_white():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        if NIBBLE_WHITE not in nibble_counts(buf):
            return False, "departing render contains no White (0x1) nibble - no foreground content drawn"
        return True, ""
    check("departing render contains at least one White (0x1) nibble (foreground content)", _departing_has_white)

    def _arriving_has_white():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        if NIBBLE_WHITE not in nibble_counts(buf):
            return False, "arriving render contains no White (0x1) nibble - no foreground content drawn"
        return True, ""
    check("arriving render contains at least one White (0x1) nibble (foreground content)", _arriving_has_white)

    # 9. Empty state is unchanged: White-dominant, at least one Black pixel.
    def _empty_state_white_dominant_with_black():
        buf = render.render_panel(None, "empty")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "empty render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        counts = nibble_counts(buf)
        dom = max(counts, key=counts.get)
        if dom != NIBBLE_WHITE:
            return False, "empty render's dominant nibble is 0x%x, expected 0x1 (White)" % dom
        if NIBBLE_BLACK not in counts:
            return False, "empty render contains no Black (0x0) nibble - expected Black text"
        return True, ""
    check("empty-state render is White-dominant and contains at least one Black nibble", _empty_state_white_dominant_with_black)

    # 10-11. Yellow/Red are reserved for later phases - never used this phase.
    def _departing_has_no_yellow_or_red():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        counts = nibble_counts(buf)
        bad = {NIBBLE_YELLOW, NIBBLE_RED} & set(counts)
        if bad:
            return False, "departing render contains reserved nibble(s): %r" % (sorted(bad),)
        return True, ""
    check("departing render contains no Yellow (0x2) or Red (0x3) nibble (cross-phase reservation)", _departing_has_no_yellow_or_red)

    def _arriving_has_no_yellow_or_red():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        counts = nibble_counts(buf)
        bad = {NIBBLE_YELLOW, NIBBLE_RED} & set(counts)
        if bad:
            return False, "arriving render contains reserved nibble(s): %r" % (sorted(bad),)
        return True, ""
    check("arriving render contains no Yellow (0x2) or Red (0x3) nibble (cross-phase reservation)", _arriving_has_no_yellow_or_red)

    # 12-13. Pre-pack canvas palette contract (03-02: re-expressed from
    #        "exactly two distinct palette indices" - now that the
    #        background is a dithered mood field rather than a flat fill,
    #        "exactly two" is necessary but no longer sufficient; the
    #        stronger, correct assertion is *which* two: the state's own
    #        background index and White, and nothing else).
    def _departing_canvas_is_exactly_blue_and_white():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "departing")
        colors = canvas.getcolors()
        idx_set = {value for _count, value in colors} if colors else set()
        if idx_set != {IDX_BLUE, IDX_WHITE}:
            return False, "departing canvas index set is %r, expected exactly {IDX_BLUE, IDX_WHITE}" % (idx_set,)
        return True, ""
    check("departing pre-pack canvas's index set is exactly {IDX_BLUE, IDX_WHITE}", _departing_canvas_is_exactly_blue_and_white)

    def _arriving_canvas_is_exactly_green_and_white():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "arriving")
        colors = canvas.getcolors()
        idx_set = {value for _count, value in colors} if colors else set()
        if idx_set != {IDX_GREEN, IDX_WHITE}:
            return False, "arriving canvas index set is %r, expected exactly {IDX_GREEN, IDX_WHITE}" % (idx_set,)
        return True, ""
    check("arriving pre-pack canvas's index set is exactly {IDX_GREEN, IDX_WHITE}", _arriving_canvas_is_exactly_green_and_white)

    # 14. Determinism: rendering the same flight twice is byte-identical.
    def _rendering_is_deterministic():
        first = render.render_panel(TEST_FLIGHT, "departing")
        second = render.render_panel(TEST_FLIGHT, "departing")
        if first != second:
            return False, "rendering the same flight twice produced different bytes - render_panel is not deterministic"
        return True, ""
    check("rendering the same flight twice produces byte-identical output (determinism)", _rendering_is_deterministic)

    # 15. State actually changes the output.
    def _departing_and_arriving_differ():
        departing = ctx.get("departing_bytes")
        arriving = ctx.get("arriving_bytes")
        if departing is None or arriving is None:
            return False, "missing captured bytes from a previous check"
        if departing == arriving:
            return False, "departing and arriving renders of the same flight are byte-identical - state does not change output"
        return True, ""
    check("departing and arriving renders of the same flight differ in bytes (state changes output)", _departing_and_arriving_differ)

    # 16-19. Silhouette centrepiece (02-03, PLANE-01/02): the aircraft
    #        silhouette must actually contribute pixels, mirror by state,
    #        stay inside the safe box without overlapping its neighbouring
    #        zones, and never appear in the Empty state. These checks read
    #        the render.SILHOUETTE_* named geometry constants directly
    #        (02-03-PLAN.md Task 2's acceptance criteria) rather than
    #        hardcoding pixel numbers, so they stay meaningful if the
    #        geometry ever changes deliberately.
    #
    # 03-02 note: these checks used to isolate the silhouette by testing
    # `pixel == IDX_WHITE` directly, which worked only because the old flat
    # background contained zero White pixels outside text/silhouette. Since
    # 03-02 the background is a dithered mood gradient whose minority index
    # IS IDX_WHITE (~19% of every band, everywhere on the canvas) - so raw
    # index equality can no longer distinguish "silhouette White" from
    # "background dither White" the same way. These checks are re-expressed
    # (03-RESEARCH.md's "may need to re-express" note, same root cause as
    # checks 12-13) to diff the composited canvas's silhouette band against
    # the same state's un-silhouetted mood background (dither.
    # build_mood_background() is deterministic and memoized, so this is a
    # stable, repeatable ground truth) - any pixel that differs from that
    # reference is unambiguously something draw_silhouette() painted.
    _SILHOUETTE_ATTRS = ("SILHOUETTE_ZONE_TOP", "SILHOUETTE_ZONE_HEIGHT", "SILHOUETTE_TARGET_W", "SILHOUETTE_MAX_H")

    def _silhouette_band(render_mod, canvas):
        top = getattr(render_mod, "SILHOUETTE_ZONE_TOP")
        height = getattr(render_mod, "SILHOUETTE_ZONE_HEIGHT")
        return canvas.crop((0, top, panel_format.WIDTH, top + height)), top

    def _silhouette_diff_mask(render_mod, state):
        """Return (mask, band_top): a binary "L"-mode mask, same size as
        the zone-3 band, 255 where the fully-composited canvas differs from
        the same state's raw (un-silhouetted) mood background, 0 where it
        matches - i.e. exactly the pixels draw_silhouette() painted, immune
        to the background's own legitimate White dither noise.
        """
        import server.plane.dither as dither_mod

        canvas = render_mod.build_canvas(TEST_FLIGHT, state)
        band, band_top = _silhouette_band(render_mod, canvas)
        bg_reference = dither_mod.build_mood_background(state)
        bg_band, _ = _silhouette_band(render_mod, bg_reference)
        band_bytes = band.tobytes()
        bg_bytes = bg_band.tobytes()
        diff_bytes = bytes(255 if a != b else 0 for a, b in zip(band_bytes, bg_bytes))
        from PIL import Image as _Image

        mask = _Image.frombytes("L", band.size, diff_bytes)
        return mask, band_top

    def _departing_silhouette_has_substantial_white_run():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS):
            return False, "server.plane.render is missing one or more SILHOUETTE_* geometry constants: %r" % (_SILHOUETTE_ATTRS,)
        mask, _ = _silhouette_diff_mask(render, "departing")
        changed_count = mask.histogram()[255]
        min_expected = int(0.1 * render.SILHOUETTE_TARGET_W * render.SILHOUETTE_MAX_H)
        if changed_count < min_expected:
            return False, "departing silhouette band differs from its un-silhouetted background in only %d pixels, expected at least %d (derived from SILHOUETTE_TARGET_W x SILHOUETTE_MAX_H) - silhouette paste looks like a no-op" % (changed_count, min_expected)
        return True, ""
    check("departing render's silhouette band contains a substantial run of pixels changed from its own un-silhouetted background (silhouette actually painted)", _departing_silhouette_has_substantial_white_run)

    def _departing_and_arriving_silhouette_bands_differ_by_shape():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS):
            return False, "server.plane.render is missing one or more SILHOUETTE_* geometry constants: %r" % (_SILHOUETTE_ATTRS,)
        dep_mask, _ = _silhouette_diff_mask(render, "departing")
        arr_mask, _ = _silhouette_diff_mask(render, "arriving")
        if dep_mask.tobytes() == arr_mask.tobytes():
            return False, "departing and arriving silhouette diff-masks are byte-identical - mirroring is a no-op (both masks isolate exactly the pixels changed from each state's own background, so a background colour/noise difference alone cannot satisfy this check)"
        return True, ""
    check("departing and arriving silhouette bands differ in shape specifically - not just background colour or dither noise (mirroring applied)", _departing_and_arriving_silhouette_bands_differ_by_shape)

    def _silhouette_bbox_in_safe_box_no_overlap():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS) or not hasattr(render, "FLIGHT_NUMBER_TOP_Y") or not hasattr(render, "MARGIN"):
            return False, "server.plane.render is missing SILHOUETTE_* geometry, FLIGHT_NUMBER_TOP_Y, or MARGIN"
        mask, band_top = _silhouette_diff_mask(render, "departing")
        bbox = mask.getbbox()
        if bbox is None:
            return False, "no silhouette pixels found in the zone-3 band at all"
        left, top, right, bottom = bbox
        abs_top = top + band_top
        abs_bottom = bottom + band_top
        sb_left, sb_top, sb_right, sb_bottom = render.MARGIN, render.MARGIN, panel_format.WIDTH - render.MARGIN, panel_format.HEIGHT - render.MARGIN
        if not (left >= sb_left and right <= sb_right and abs_top >= sb_top and abs_bottom <= sb_bottom):
            return False, "silhouette bounding box (%r absolute) exceeds the inviolable safe box %r" % ((left, abs_top, right, abs_bottom), (sb_left, sb_top, sb_right, sb_bottom))
        if abs_top < render.SILHOUETTE_ZONE_TOP:
            return False, "silhouette bounding box top %d creeps above its reserved zone (SILHOUETTE_ZONE_TOP=%d) - overlaps the state-label band" % (abs_top, render.SILHOUETTE_ZONE_TOP)
        if abs_bottom > render.FLIGHT_NUMBER_TOP_Y:
            return False, "silhouette bounding box bottom %d overlaps the flight-number caption band (FLIGHT_NUMBER_TOP_Y=%d)" % (abs_bottom, render.FLIGHT_NUMBER_TOP_Y)
        return True, ""
    check("departing silhouette's bounding box stays inside the safe box and does not overlap the state-label or flight-number caption bands", _silhouette_bbox_in_safe_box_no_overlap)

    def _empty_state_never_calls_draw_silhouette():
        # A pixel-region check ("the band must be blank") is the wrong
        # invariant here: the empty state's heading/body text is
        # vertically centred on the *whole* 1600px canvas and legitimately
        # passes through the silhouette-zone Y range - it is Black text on
        # White background, the exact opposite foreground/background pair
        # the active states use, so there is no colour-based marker that
        # distinguishes "silhouette pixel" from "empty-state text pixel"
        # in that band. The real UI-SPEC guarantee ("nothing detected,
        # nothing to depict") is structural: draw_silhouette() must simply
        # never be invoked while building the empty-state canvas. Verify
        # that directly by spying on the call.
        if not hasattr(render, "draw_silhouette"):
            return False, "server.plane.render has no draw_silhouette()"
        calls = []
        original = render.draw_silhouette

        def _spy(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)

        render.draw_silhouette = _spy
        try:
            render.build_canvas(None, "empty")
        except Exception as exc:
            return False, "build_canvas(None, 'empty') raised: %r" % (exc,)
        finally:
            render.draw_silhouette = original
        if calls:
            return False, "draw_silhouette() was called while building the empty-state canvas - UI-SPEC requires text-only, no silhouette"
        return True, ""
    check("empty-state render never calls draw_silhouette() (nothing detected, nothing to depict)", _empty_state_never_calls_draw_silhouette)

    # 20-25. Route line (zone 7) / airline line (zone 9), 02-04
    # (PLANE-01/02): a resolved route renders TO/FROM + city + airline
    # name; an enrichment miss (route=None) omits the route line entirely
    # and renders exactly "Route unavailable" at the airline line's normal
    # position - no doubled gap. See the module docstring's "02-04
    # addition" note for why these checks spy on draw_tracked_text() and
    # ImageDraw.Draw.text() instead of comparing pixel signatures.
    class _RenderSpy:
        """Captures every render.draw_tracked_text() call (Label-role
        runs - the route-line prefix, among others) and every
        ImageDraw.Draw.text() call (Body-role runs - city names, the
        airline name, the fallback copy) made while building one canvas.
        """

        def __init__(self, render_mod):
            self._render_mod = render_mod
            self.tracked = []  # list of (text, xy)
            self.body = []  # list of (text, xy)
            self._orig_tracked = None
            self._orig_text = None

        def __enter__(self):
            self._orig_tracked = self._render_mod.draw_tracked_text
            self._orig_text = self._render_mod.ImageDraw.ImageDraw.text

            def _spy_tracked(draw, xy, text, font, fill, tracking=0):
                self.tracked.append((text, xy))
                return self._orig_tracked(draw, xy, text, font, fill, tracking=tracking)

            def _spy_text(draw_self, xy, text, *args, **kwargs):
                self.body.append((text, xy))
                return self._orig_text(draw_self, xy, text, *args, **kwargs)

            self._render_mod.draw_tracked_text = _spy_tracked
            self._render_mod.ImageDraw.ImageDraw.text = _spy_text
            return self

        def __exit__(self, exc_type, exc, tb):
            self._render_mod.draw_tracked_text = self._orig_tracked
            self._render_mod.ImageDraw.ImageDraw.text = self._orig_text
            return False

    def _departing_with_route_renders_to_prefix_city_and_airline():
        with _RenderSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        tracked_texts = [t for t, _xy in spy.tracked]
        body_texts = [t for t, _xy in spy.body]
        if "TO" not in tracked_texts:
            return False, "expected the route-line prefix 'TO' among the tracked-text draws, got %r" % (tracked_texts,)
        if TEST_ROUTE["destination_city"] not in body_texts:
            return False, "expected the destination city %r among the body-text draws, got %r" % (TEST_ROUTE["destination_city"], body_texts)
        if TEST_ROUTE["airline_name"] not in body_texts:
            return False, "expected the airline name %r among the body-text draws, got %r" % (TEST_ROUTE["airline_name"], body_texts)
        return True, ""
    check(
        "departing render with a resolved route draws the route line ('TO' + destination city) and the airline line (airline name)",
        _departing_with_route_renders_to_prefix_city_and_airline,
    )

    def _arriving_with_route_renders_from_prefix_and_city():
        with _RenderSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        tracked_texts = [t for t, _xy in spy.tracked]
        body_texts = [t for t, _xy in spy.body]
        if "FROM" not in tracked_texts:
            return False, "expected the route-line prefix 'FROM' among the tracked-text draws, got %r" % (tracked_texts,)
        if TEST_ROUTE["origin_city"] not in body_texts:
            return False, "expected the origin city %r among the body-text draws, got %r" % (TEST_ROUTE["origin_city"], body_texts)
        return True, ""
    check(
        "arriving render with a resolved route draws the route line with prefix 'FROM' + origin city",
        _arriving_with_route_renders_from_prefix_and_city,
    )

    def _miss_render_omits_route_line_and_shows_fallback():
        with _RenderSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=None)
        tracked_texts = [t for t, _xy in spy.tracked]
        body_texts = [t for t, _xy in spy.body]
        if "TO" in tracked_texts or "FROM" in tracked_texts:
            return False, "enrichment-miss render must never draw the route-line prefix, got tracked texts %r" % (tracked_texts,)
        fallback_count = body_texts.count("Route unavailable")
        if fallback_count != 1:
            return False, "expected the airline line to carry exactly one 'Route unavailable', found %d occurrence(s) in %r" % (fallback_count, body_texts)
        return True, ""
    check(
        "enrichment-miss render (route=None) never draws the route line and draws the airline line with the exact fallback text 'Route unavailable'",
        _miss_render_omits_route_line_and_shows_fallback,
    )

    def _miss_fallback_sits_at_the_normal_airline_line_position():
        with _RenderSpy(render) as hit_spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        with _RenderSpy(render) as miss_spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=None)

        hit_airline_ys = [xy[1] for t, xy in hit_spy.body if t == TEST_ROUTE["airline_name"]]
        miss_airline_ys = [xy[1] for t, xy in miss_spy.body if t == "Route unavailable"]
        if not hit_airline_ys:
            return False, "did not capture the resolved-route render's airline-name draw call"
        if not miss_airline_ys:
            return False, "did not capture the enrichment-miss render's fallback draw call"
        if hit_airline_ys[0] != miss_airline_ys[0]:
            return False, (
                "fallback airline line y-offset %r does not match the resolved-route airline line y-offset %r - "
                "UI-SPEC requires the fallback to sit at the airline line's normal position, not doubled up "
                "with an empty route line above it" % (miss_airline_ys[0], hit_airline_ys[0])
            )
        return True, ""
    check(
        "enrichment-miss render's fallback airline line sits at the exact same y-offset as a resolved-route render's airline line (no doubled gap)",
        _miss_fallback_sits_at_the_normal_airline_line_position,
    )

    def _miss_render_still_has_silhouette_label_and_flight_number():
        if not hasattr(render, "draw_silhouette") or not hasattr(render, "draw_state_label"):
            return False, "server.plane.render is missing draw_silhouette()/draw_state_label()"
        silhouette_calls = []
        label_calls = []
        orig_silhouette = render.draw_silhouette
        orig_label = render.draw_state_label

        def _spy_silhouette(*args, **kwargs):
            silhouette_calls.append(1)
            return orig_silhouette(*args, **kwargs)

        def _spy_label(*args, **kwargs):
            label_calls.append(1)
            return orig_label(*args, **kwargs)

        render.draw_silhouette = _spy_silhouette
        render.draw_state_label = _spy_label
        try:
            with _RenderSpy(render) as spy:
                render.build_canvas(TEST_FLIGHT, "departing", route=None)
        finally:
            render.draw_silhouette = orig_silhouette
            render.draw_state_label = orig_label

        if not silhouette_calls:
            return False, "draw_silhouette() was not called for an enrichment-miss render - the silhouette must still render from ADS-B data alone"
        if not label_calls:
            return False, "draw_state_label() was not called for an enrichment-miss render"
        if TEST_FLIGHT["callsign"] not in [t for t, _xy in spy.body]:
            return False, "the flight-number caption was not drawn for an enrichment-miss render"
        return True, ""
    check(
        "enrichment-miss render still renders the silhouette, state label, and flight-number caption from ADS-B data alone",
        _miss_render_still_has_silhouette_label_and_flight_number,
    )

    def _hit_and_miss_renders_keep_two_palette_indices():
        hit_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        miss_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=None)
        hit_idx_set = {value for _count, value in hit_canvas.getcolors()} if hit_canvas.getcolors() else set()
        miss_idx_set = {value for _count, value in miss_canvas.getcolors()} if miss_canvas.getcolors() else set()
        if hit_idx_set != {IDX_BLUE, IDX_WHITE}:
            return False, "resolved-route canvas index set is %r, expected exactly {IDX_BLUE, IDX_WHITE}" % (hit_idx_set,)
        if miss_idx_set != {IDX_BLUE, IDX_WHITE}:
            return False, "enrichment-miss canvas index set is %r, expected exactly {IDX_BLUE, IDX_WHITE}" % (miss_idx_set,)
        return True, ""
    check(
        "both a resolved-route render and an enrichment-miss render retain exactly {IDX_BLUE, IDX_WHITE} after compositing",
        _hit_and_miss_renders_keep_two_palette_indices,
    )

    # 26-32. 03-01 Task 2 (D-15/D-16): the four Zilla Slab typographic
    # roles, the widened tracking, the retired-role removal, the co-equal
    # hero-pair size contract, and the long-name shrink path.
    _ROLE_SPECS = {
        "LABEL_FONT": (36, 700),
        "CAPTION_FONT": (40, 600),
        "DESTINATION_FONT": (64, 600),
        "FLIGHT_NUMBER_FONT": (72, 700),
    }

    def _role_constants_are_exactly_four_zilla_slab_roles():
        for name, (size, weight) in _ROLE_SPECS.items():
            if not hasattr(render, name):
                return False, "server.plane.render has no %s role constant" % name
            path, got_size, got_weight = getattr(render, name)
            if got_size != size or got_weight != weight:
                return False, "%s is %r, expected size=%d weight=%d" % (name, (path, got_size, got_weight), size, weight)
            if not (path.endswith("ZillaSlab-SemiBold.ttf") or path.endswith("ZillaSlab-Bold.ttf")):
                return False, "%s font path %r is not a vendored Zilla Slab file" % (name, path)
        return True, ""
    check(
        "the four typographic role constants exist with exactly sizes 36/40/64/72 and weights 700/600/600/700, all pointing at a vendored Zilla Slab file",
        _role_constants_are_exactly_four_zilla_slab_roles,
    )

    def _label_tracking_is_6px():
        if not hasattr(render, "LABEL_TRACKING_PX"):
            return False, "server.plane.render has no LABEL_TRACKING_PX"
        if render.LABEL_TRACKING_PX != 6:
            return False, "render.LABEL_TRACKING_PX is %r, expected 6 (D-15's widened tracking)" % (render.LABEL_TRACKING_PX,)
        return True, ""
    check("render.LABEL_TRACKING_PX equals 6 (D-15 widened tracking)", _label_tracking_is_6px)

    def _body_and_heading_font_roles_removed():
        if hasattr(render, "BODY_FONT"):
            return False, "server.plane.render still exposes the retired BODY_FONT role"
        if hasattr(render, "HEADING_FONT"):
            return False, "server.plane.render still exposes the retired HEADING_FONT role"
        return True, ""
    check("render no longer exposes the retired BODY_FONT or HEADING_FONT roles", _body_and_heading_font_roles_removed)

    def _hero_pair_is_co_equal():
        if not (hasattr(render, "FLIGHT_NUMBER_FONT") and hasattr(render, "DESTINATION_FONT") and hasattr(render, "CAPTION_FONT")):
            return False, "server.plane.render is missing one or more of FLIGHT_NUMBER_FONT/DESTINATION_FONT/CAPTION_FONT"
        gap = render.FLIGHT_NUMBER_FONT[1] - render.DESTINATION_FONT[1]
        if gap != 8:
            return False, "FLIGHT_NUMBER_FONT[1] - DESTINATION_FONT[1] is %d, expected 8 (D-16 co-equal hero pair)" % gap
        if not (render.CAPTION_FONT[1] < render.DESTINATION_FONT[1] and render.CAPTION_FONT[1] < render.FLIGHT_NUMBER_FONT[1]):
            return False, "CAPTION_FONT[1]=%d is not strictly smaller than both hero sizes (%d, %d)" % (
                render.CAPTION_FONT[1], render.DESTINATION_FONT[1], render.FLIGHT_NUMBER_FONT[1],
            )
        return True, ""
    check(
        "the hero pair is co-equal: FLIGHT_NUMBER_FONT - DESTINATION_FONT size gap is 8px, and CAPTION_FONT is strictly smaller than both (D-16)",
        _hero_pair_is_co_equal,
    )

    def _departing_route_render_still_carries_all_three_captions():
        with _RenderSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        body_texts = [t for t, _xy in spy.body]
        if TEST_FLIGHT["callsign"] not in body_texts:
            return False, "expected the flight number %r among the body-text draws, got %r" % (TEST_FLIGHT["callsign"], body_texts)
        if TEST_ROUTE["destination_city"] not in body_texts:
            return False, "expected the destination city %r among the body-text draws, got %r" % (TEST_ROUTE["destination_city"], body_texts)
        if TEST_ROUTE["airline_name"] not in body_texts:
            return False, "expected the airline name %r among the body-text draws, got %r" % (TEST_ROUTE["airline_name"], body_texts)
        return True, ""
    check(
        "a departing render with a resolved route still draws the flight number, destination city, and airline name after the font swap",
        _departing_route_render_still_carries_all_three_captions,
    )

    def _long_name_stress_case_shrinks_without_breaching_safe_box():
        # arriving state shows origin_city (enrich.city_for_state) - the
        # long name lives on TEST_LONG_ROUTE's origin_city field.
        try:
            with _RenderSpy(render) as spy:
                render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_LONG_ROUTE)
        except AssertionError as exc:
            return False, "long-name render raised the safe-box assertion: %r" % (exc,)
        body_texts = [t for t, _xy in spy.body]
        if TEST_LONG_ROUTE["origin_city"] not in body_texts:
            return False, (
                "long origin-city name %r was not drawn in full (found %r) - the shrink path must fit the "
                "text, not truncate it" % (TEST_LONG_ROUTE["origin_city"], body_texts)
            )
        return True, ""
    check(
        "a genuinely long destination/origin city name (Santiago de Compostela) shrinks via fit_text_size() rather than breaching the safe box, and is drawn in full (automated half of D-04)",
        _long_name_stress_case_shrinks_without_breaching_safe_box,
    )

    def _rendering_same_flight_twice_stays_deterministic_after_font_swap():
        first = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        second = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        if first != second:
            return False, "rendering the same flight+route twice produced different bytes after the font swap"
        return True, ""
    check(
        "rendering the same flight+route twice remains byte-identical after the Zilla Slab font swap (determinism)",
        _rendering_same_flight_twice_stays_deterministic_after_font_swap,
    )

    # 33-37. 03-02 (D-17/D-18): the mood background is not a flat fill,
    # quiet-zone geometry actually observed on the render path is correct,
    # no text-outline arguments exist anywhere in the source, and
    # determinism survives an interleaved build of the other state.
    class _QuietZoneSpy:
        """Captures every render.draw_quiet_zone() call made while building
        one canvas: the caller-supplied (unpadded) text bbox and the
        clamped rectangle actually drawn and returned - the same
        monkeypatch-a-module-global pattern _RenderSpy above already uses
        for draw_tracked_text()/ImageDraw.Draw.text()."""

        def __init__(self, render_mod):
            self._render_mod = render_mod
            self.calls = []  # list of (input_bbox, drawn_rect)
            self._orig = None

        def __enter__(self):
            self._orig = self._render_mod.draw_quiet_zone

            def _spy(canvas, bbox, bg_idx, pad=self._render_mod.QUIET_ZONE_PAD):
                rect = self._orig(canvas, bbox, bg_idx, pad=pad)
                self.calls.append((bbox, rect))
                return rect

            self._render_mod.draw_quiet_zone = _spy
            return self

        def __exit__(self, exc_type, exc, tb):
            self._render_mod.draw_quiet_zone = self._orig
            return False

    def _departing_background_is_not_a_flat_fill():
        with _QuietZoneSpy(render) as spy:
            canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        scratch = canvas.copy()
        scratch_draw = render.ImageDraw.Draw(scratch)
        SENTINEL = 255
        for _bbox, rect in spy.calls:
            scratch_draw.rectangle(tuple(int(v) for v in rect), fill=SENTINEL)
        scratch_draw.rectangle(
            (0, render.SILHOUETTE_ZONE_TOP, panel_format.WIDTH, render.SILHOUETTE_ZONE_TOP + render.SILHOUETTE_ZONE_HEIGHT),
            fill=SENTINEL,
        )
        colors = scratch.getcolors()
        idx_set = {value for _count, value in colors} if colors else set()
        idx_set.discard(SENTINEL)
        if IDX_BLUE not in idx_set or IDX_WHITE not in idx_set:
            return False, (
                "departing canvas outside every quiet zone and the silhouette band has index set %r, "
                "expected both IDX_BLUE and IDX_WHITE present (regression to a flat pf.new_canvas() fill)" % (idx_set,)
            )
        return True, ""
    check(
        "departing background is a real dithered gradient (both IDX_BLUE and IDX_WHITE present outside every quiet zone and the silhouette band) - not a flat fill",
        _departing_background_is_not_a_flat_fill,
    )

    def _departing_quiet_zone_geometry_is_correct():
        if not hasattr(render, "draw_quiet_zone") or not hasattr(render, "QUIET_ZONE_PAD"):
            return False, "server.plane.render is missing draw_quiet_zone() or QUIET_ZONE_PAD"
        with _QuietZoneSpy(render) as spy:
            canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        if len(spy.calls) != 5:
            return False, "expected exactly 5 quiet-zone rectangles for a departing render with a resolved route (state label, flight number, route line, airline line, bottom tag), got %d: %r" % (
                len(spy.calls), spy.calls,
            )
        sb_left, sb_top, sb_right, sb_bottom = render.SAFE_BOX
        for bbox, rect in spy.calls:
            r_left, r_top, r_right, r_bottom = rect
            if not (r_left >= sb_left and r_top >= sb_top and r_right <= sb_right and r_bottom <= sb_bottom):
                return False, "quiet-zone rectangle %r lies outside SAFE_BOX %r" % (rect, render.SAFE_BOX)
            b_left, b_top, b_right, b_bottom = bbox
            if not (r_left <= b_left and r_top <= b_top and r_right >= b_right and r_bottom >= b_bottom):
                return False, "quiet-zone rectangle %r does not fully contain the text bbox %r it backs" % (rect, bbox)
            crop = canvas.crop(tuple(int(v) for v in rect))
            crop_colors = crop.getcolors()
            crop_idx_set = {value for _count, value in crop_colors} if crop_colors else set()
            if not crop_idx_set.issubset({IDX_BLUE, IDX_WHITE}):
                return False, "quiet-zone rectangle %r contains illegal index(es) %r" % (rect, crop_idx_set - {IDX_BLUE, IDX_WHITE})
        return True, ""
    check(
        "each of the 5 quiet-zone rectangles the departing render path actually draws contains only {IDX_BLUE, IDX_WHITE}, lies entirely inside SAFE_BOX, and fully contains the text bbox it backs",
        _departing_quiet_zone_geometry_is_correct,
    )

    def _render_source_never_uses_text_outline_arguments():
        render_path = os.path.join(REPO_ROOT, "server", "plane", "render.py")
        with open(render_path, "r") as fh:
            code_lines = [line for line in fh if not line.lstrip().startswith("#")]
        stripped_source = "".join(code_lines)
        if "stroke_width" in stripped_source or "stroke_fill" in stripped_source:
            return False, "server/plane/render.py references stroke_width/stroke_fill outside a full-line comment"
        return True, ""
    check(
        "server/plane/render.py's comment-stripped source contains no stroke_width/stroke_fill text-outline usage",
        _render_source_never_uses_text_outline_arguments,
    )

    def _departing_determinism_survives_interleaved_other_state_build():
        import hashlib

        from server.plane import dither as dither_mod

        first = render.render_panel(TEST_FLIGHT, "departing")
        first_hash = hashlib.sha256(first).hexdigest()
        dither_mod.build_mood_background("arriving")  # interleave the other state's memoized build
        second = render.render_panel(TEST_FLIGHT, "departing")
        second_hash = hashlib.sha256(second).hexdigest()
        if first_hash != second_hash:
            return False, "departing panel SHA-256 changed after an interleaved build_mood_background('arriving') call: %s vs %s - the memo is order-dependent" % (
                first_hash, second_hash,
            )
        return True, ""
    check(
        "the departing panel's SHA-256 is unaffected by an interleaved build_mood_background('arriving') call (memoization is not order-dependent)",
        _departing_determinism_survives_interleaved_other_state_build,
    )

    def _empty_state_still_uses_flat_new_canvas():
        render_path = os.path.join(REPO_ROOT, "server", "plane", "render.py")
        with open(render_path, "r") as fh:
            code_lines = [line for line in fh if not line.lstrip().startswith("#")]
        stripped_source = "".join(code_lines)
        if stripped_source.count("new_canvas") != 1:
            return False, "server/plane/render.py's comment-stripped source calls new_canvas() %d time(s), expected exactly 1 (only the empty state)" % (
                stripped_source.count("new_canvas"),
            )
        empty_canvas = render.build_canvas(None, "empty")
        idx_set = {value for _count, value in empty_canvas.getcolors()} if empty_canvas.getcolors() else set()
        if idx_set != {IDX_BLACK, IDX_WHITE}:
            return False, "empty-state canvas index set is %r, expected exactly {IDX_BLACK, IDX_WHITE} (unaffected flat fill)" % (idx_set,)
        return True, ""
    check(
        "the empty state still builds its canvas via the sole remaining pf.new_canvas() call site and stays exactly {IDX_BLACK, IDX_WHITE}",
        _empty_state_still_uses_flat_new_canvas,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
