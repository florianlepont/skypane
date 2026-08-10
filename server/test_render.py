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

Usage:
    server/.venv/bin/python3 server/test_render.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 19

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}

TEST_FLIGHT = {"hex": "3985a7", "callsign": "AF1380"}


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

    # 12-13. Pre-pack canvas anti-aliasing guard: exactly two palette
    #        indices, per 02-RESEARCH.md's own verified Image.getcolors()
    #        method.
    def _departing_canvas_has_two_indices():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "departing")
        colors = canvas.getcolors()
        if colors is None or len(colors) != 2:
            return False, "departing canvas has %r distinct palette indices, expected exactly 2" % (
                None if colors is None else len(colors),
            )
        return True, ""
    check("departing pre-pack canvas contains exactly two distinct palette indices (no anti-aliasing)", _departing_canvas_has_two_indices)

    def _arriving_canvas_has_two_indices():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "arriving")
        colors = canvas.getcolors()
        if colors is None or len(colors) != 2:
            return False, "arriving canvas has %r distinct palette indices, expected exactly 2" % (
                None if colors is None else len(colors),
            )
        return True, ""
    check("arriving pre-pack canvas contains exactly two distinct palette indices (no anti-aliasing)", _arriving_canvas_has_two_indices)

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
    _SILHOUETTE_ATTRS = ("SILHOUETTE_ZONE_TOP", "SILHOUETTE_ZONE_HEIGHT", "SILHOUETTE_TARGET_W", "SILHOUETTE_MAX_H")

    def _silhouette_band(render_mod, canvas):
        top = getattr(render_mod, "SILHOUETTE_ZONE_TOP")
        height = getattr(render_mod, "SILHOUETTE_ZONE_HEIGHT")
        return canvas.crop((0, top, panel_format.WIDTH, top + height)), top

    def _fg_only_bytes(band, fg_idx):
        # Reduce the band to a pure foreground/not-foreground mask so a
        # background-colour difference (Blue vs Green) alone can never
        # satisfy a "differs" comparison - only an actual shape change can.
        return band.point(lambda p: 255 if p == fg_idx else 0).tobytes()

    def _departing_silhouette_has_substantial_white_run():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS):
            return False, "server.plane.render is missing one or more SILHOUETTE_* geometry constants: %r" % (_SILHOUETTE_ATTRS,)
        canvas = render.build_canvas(TEST_FLIGHT, "departing")
        band, _ = _silhouette_band(render, canvas)
        white_count = band.histogram()[IDX_WHITE]
        min_expected = int(0.1 * render.SILHOUETTE_TARGET_W * render.SILHOUETTE_MAX_H)
        if white_count < min_expected:
            return False, "departing silhouette band contains only %d White pixels, expected at least %d (derived from SILHOUETTE_TARGET_W x SILHOUETTE_MAX_H) - silhouette paste looks like a no-op" % (white_count, min_expected)
        return True, ""
    check("departing render's silhouette band contains a substantial run of White pixels (silhouette actually painted)", _departing_silhouette_has_substantial_white_run)

    def _departing_and_arriving_silhouette_bands_differ_by_shape():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS):
            return False, "server.plane.render is missing one or more SILHOUETTE_* geometry constants: %r" % (_SILHOUETTE_ATTRS,)
        dep_canvas = render.build_canvas(TEST_FLIGHT, "departing")
        arr_canvas = render.build_canvas(TEST_FLIGHT, "arriving")
        dep_band, _ = _silhouette_band(render, dep_canvas)
        arr_band, _ = _silhouette_band(render, arr_canvas)
        dep_fg = _fg_only_bytes(dep_band, IDX_WHITE)
        arr_fg = _fg_only_bytes(arr_band, IDX_WHITE)
        if dep_fg == arr_fg:
            return False, "departing and arriving foreground-only silhouette bands are byte-identical - mirroring is a no-op (a background colour difference alone cannot satisfy this check, since both bands were reduced to a White-vs-not mask first)"
        return True, ""
    check("departing and arriving silhouette bands differ in their foreground (White) shape specifically - not just background colour (mirroring applied)", _departing_and_arriving_silhouette_bands_differ_by_shape)

    def _silhouette_bbox_in_safe_box_no_overlap():
        if not all(hasattr(render, a) for a in _SILHOUETTE_ATTRS) or not hasattr(render, "FLIGHT_NUMBER_TOP_Y") or not hasattr(render, "MARGIN"):
            return False, "server.plane.render is missing SILHOUETTE_* geometry, FLIGHT_NUMBER_TOP_Y, or MARGIN"
        canvas = render.build_canvas(TEST_FLIGHT, "departing")
        band, band_top = _silhouette_band(render, canvas)
        fg_mask = band.point(lambda p: 255 if p == IDX_WHITE else 0)
        bbox = fg_mask.getbbox()
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

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
