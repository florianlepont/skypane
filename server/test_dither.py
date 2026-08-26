#!/usr/bin/env python3
"""Contract harness for server/plane/dither.py's two-tone mood background
generator and the full-palette dither helper (D-17/D-18, PLANE-01/PLANE-02).

Stdlib-only, plus the module under test (server.plane.dither,
server.panel_format) - dither.py transitively imports Pillow, so this
harness must be run under server/.venv's interpreter, not the bare system
python3. Exits 0 only when every check below passes; any failure (or
exception - none is ever swallowed into a pass) exits 1. Matches the same
check()/EXPECTED_CHECK_COUNT/main() convention every sibling server/test_*.py
file uses (see server/test_plane_detection.py) - no pytest.

Note: Pillow's Image.getcolors() returns (count, value) pairs - count
first, value second. Every check below unpacks with
`{value for _count, value in canvas.getcolors()}`, never the reverse.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 15


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
        from server.plane import dither
        from server.plane import runway_config
        from server import panel_format as pf
    except ImportError as exc:
        print("FAIL import server.plane.dither / server.plane.runway_config / server.panel_format - %r" % (exc,))
        print("dither: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    ctx = {}

    def _index_set(canvas):
        return {value for _count, value in canvas.getcolors()}

    def _index_counts(canvas):
        return {value: count for count, value in canvas.getcolors()}

    # 1-2. Each state's background contains exactly the two expected indices,
    # with the state hue in the clear majority.
    def _departing_is_white_and_blue_only():
        canvas = dither.build_mood_background(runway_config.STATE_DEPARTING)
        idx_set = _index_set(canvas)
        if idx_set != {pf.IDX_WHITE, pf.IDX_BLUE}:
            return False, "departing background index set is %r, expected {IDX_WHITE, IDX_BLUE}" % (idx_set,)
        counts = _index_counts(canvas)
        total = sum(counts.values())
        if counts.get(pf.IDX_BLUE, 0) <= total / 2:
            return False, "Blue is not a clear majority of the departing background: %r" % (counts,)
        ctx["departing_canvas"] = canvas
        return True, ""
    check(
        "build_mood_background('departing') contains exactly {IDX_WHITE, IDX_BLUE} with Blue in the majority",
        _departing_is_white_and_blue_only,
    )

    def _arriving_is_white_and_green_only():
        canvas = dither.build_mood_background(runway_config.STATE_ARRIVING)
        idx_set = _index_set(canvas)
        if idx_set != {pf.IDX_WHITE, pf.IDX_GREEN}:
            return False, "arriving background index set is %r, expected {IDX_WHITE, IDX_GREEN}" % (idx_set,)
        counts = _index_counts(canvas)
        total = sum(counts.values())
        if counts.get(pf.IDX_GREEN, 0) <= total / 2:
            return False, "Green is not a clear majority of the arriving background: %r" % (counts,)
        ctx["arriving_canvas"] = canvas
        return True, ""
    check(
        "build_mood_background('arriving') contains exactly {IDX_WHITE, IDX_GREEN} with Green in the majority",
        _arriving_is_white_and_green_only,
    )

    # 3. The two states' backgrounds differ from each other in bytes.
    def _states_differ_in_bytes():
        dep = ctx.get("departing_canvas")
        arr = ctx.get("arriving_canvas")
        if dep is None or arr is None:
            return False, "missing captured canvases from a previous check"
        if dep.tobytes() == arr.tobytes():
            return False, "departing and arriving mood backgrounds are byte-identical"
        return True, ""
    check("departing and arriving mood backgrounds differ in bytes", _states_differ_in_bytes)

    # 4. Two calls for the same state return byte-identical pixel data.
    def _same_state_is_deterministic():
        first = dither.build_mood_background(runway_config.STATE_DEPARTING)
        second = dither.build_mood_background(runway_config.STATE_DEPARTING)
        if first.tobytes() != second.tobytes():
            return False, "two build_mood_background('departing') calls produced different bytes"
        return True, ""
    check("two build_mood_background() calls for the same state are byte-identical", _same_state_is_deterministic)

    # 5. Calls interleaved between states do not perturb each other.
    def _interleaved_calls_do_not_perturb_each_other():
        d1 = dither.build_mood_background(runway_config.STATE_DEPARTING).tobytes()
        a1 = dither.build_mood_background(runway_config.STATE_ARRIVING).tobytes()
        d2 = dither.build_mood_background(runway_config.STATE_DEPARTING).tobytes()
        a2 = dither.build_mood_background(runway_config.STATE_ARRIVING).tobytes()
        if d1 != d2:
            return False, "departing background changed after an interleaved arriving call"
        if a1 != a2:
            return False, "arriving background changed after an interleaved departing call"
        return True, ""
    check(
        "build_mood_background() calls interleaved between states do not perturb each other",
        _interleaved_calls_do_not_perturb_each_other,
    )

    # 6. The returned canvas carries the same 768-entry padded palette a
    # new_canvas() canvas carries.
    def _mood_canvas_palette_matches_new_canvas():
        mood = dither.build_mood_background(runway_config.STATE_DEPARTING)
        reference = pf.new_canvas(pf.IDX_BLUE)
        mood_palette = mood.getpalette()
        ref_palette = reference.getpalette()
        if mood_palette != ref_palette:
            return False, "mood background palette differs from new_canvas()'s palette"
        if len(mood_palette) != 768:
            return False, "mood background palette has %d entries, expected 768" % (len(mood_palette),)
        return True, ""
    check(
        "build_mood_background()'s canvas carries the same 768-entry padded palette a new_canvas() canvas carries",
        _mood_canvas_palette_matches_new_canvas,
    )

    # 7. dither_to_full_panel_palette() maps an arbitrary RGB image onto
    # indices drawn only from 0..5, with no remap applied.
    def _full_palette_dither_stays_within_legal_indices():
        from PIL import Image

        hue_rich = Image.new("RGB", (64, 64))
        pixels = hue_rich.load()
        for y in range(64):
            for x in range(64):
                pixels[x, y] = (x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256)
        quantized = dither.dither_to_full_panel_palette(hue_rich)
        idx_set = _index_set(quantized)
        if not idx_set.issubset({0, 1, 2, 3, 4, 5}):
            return False, "dither_to_full_panel_palette() produced out-of-range indices: %r" % (idx_set,)
        return True, ""
    check(
        "dither_to_full_panel_palette() on a hue-rich synthetic image yields indices that are a subset of {0,1,2,3,4,5}",
        _full_palette_dither_stays_within_legal_indices,
    )

    # 8. An unknown state string raises ValueError rather than returning a
    # wrong-coloured canvas.
    def _unknown_state_raises_value_error():
        try:
            dither.build_mood_background("sideways")
        except ValueError:
            return True, ""
        except Exception as exc:
            return False, "expected ValueError, got %r" % (exc,)
        return False, "build_mood_background('sideways') did not raise"
    check("build_mood_background() raises ValueError for an unknown state", _unknown_state_raises_value_error)

    # 9-10. Hue-dominance thresholds: state hue >= 60%, White >= 5%.
    def _departing_hue_dominant_and_gradient():
        counts = _index_counts(ctx["departing_canvas"])
        total = sum(counts.values())
        blue_share = counts.get(pf.IDX_BLUE, 0) / total
        white_share = counts.get(pf.IDX_WHITE, 0) / total
        if blue_share < 0.60:
            return False, "departing Blue share is %.1f%%, expected at least 60%%" % (blue_share * 100,)
        if white_share < 0.05:
            return False, "departing White share is %.1f%%, expected at least 5%% (not a flat fill)" % (white_share * 100,)
        return True, ""
    check(
        "departing background is at least 60%% Blue and at least 5%% White (hue-dominant, not a flat fill)",
        _departing_hue_dominant_and_gradient,
    )

    def _arriving_hue_dominant_and_gradient():
        counts = _index_counts(ctx["arriving_canvas"])
        total = sum(counts.values())
        green_share = counts.get(pf.IDX_GREEN, 0) / total
        white_share = counts.get(pf.IDX_WHITE, 0) / total
        if green_share < 0.60:
            return False, "arriving Green share is %.1f%%, expected at least 60%%" % (green_share * 100,)
        if white_share < 0.05:
            return False, "arriving White share is %.1f%%, expected at least 5%% (not a flat fill)" % (white_share * 100,)
        return True, ""
    check(
        "arriving background is at least 60%% Green and at least 5%% White (hue-dominant, not a flat fill)",
        _arriving_hue_dominant_and_gradient,
    )

    # 11-12. pack_panel() nibble contract per state.
    def _departing_packs_to_exact_nibble_set():
        buf = pf.pack_panel(ctx["departing_canvas"])
        if len(buf) != pf.IMAGE_BYTES:
            return False, "departing mood canvas packs to %d bytes, expected %d" % (len(buf), pf.IMAGE_BYTES)
        nibbles = set()
        for b in buf:
            nibbles.add((b >> 4) & 0xF)
            nibbles.add(b & 0xF)
        if nibbles != {0x1, 0x5}:
            return False, "departing mood canvas's packed nibble set is %r, expected {0x1, 0x5}" % (nibbles,)
        return True, ""
    check(
        "pack_panel() on the departing mood canvas produces exactly 960000 bytes with nibble set {0x1, 0x5}",
        _departing_packs_to_exact_nibble_set,
    )

    def _arriving_packs_to_exact_nibble_set():
        buf = pf.pack_panel(ctx["arriving_canvas"])
        if len(buf) != pf.IMAGE_BYTES:
            return False, "arriving mood canvas packs to %d bytes, expected %d" % (len(buf), pf.IMAGE_BYTES)
        nibbles = set()
        for b in buf:
            nibbles.add((b >> 4) & 0xF)
            nibbles.add(b & 0xF)
        if nibbles != {0x1, 0x6}:
            return False, "arriving mood canvas's packed nibble set is %r, expected {0x1, 0x6}" % (nibbles,)
        return True, ""
    check(
        "pack_panel() on the arriving mood canvas produces exactly 960000 bytes with nibble set {0x1, 0x6}",
        _arriving_packs_to_exact_nibble_set,
    )

    # 13. build_mood_background() returns a distinct object each call;
    # mutating the returned canvas must not affect a later call's result.
    def _returned_canvas_is_a_distinct_copy_each_call():
        first = dither.build_mood_background(runway_config.STATE_DEPARTING)
        before_mutation = first.tobytes()
        first.paste(pf.IDX_WHITE, (0, 0, 10, 10))
        second = dither.build_mood_background(runway_config.STATE_DEPARTING)
        if second.tobytes() != before_mutation:
            return False, "mutating a returned mood-background canvas leaked into a later call's result"
        if first is second:
            return False, "build_mood_background() returned the same object instance twice"
        return True, ""
    check(
        "build_mood_background() returns a fresh copy each call - mutating it does not affect a later call",
        _returned_canvas_is_a_distinct_copy_each_call,
    )

    # 14. write_calibration_preview() writes three PNGs and returns their paths.
    def _calibration_preview_writes_three_pngs():
        tmp_dir = tempfile.mkdtemp(prefix="ink-frame-dither-calib-")
        try:
            paths = dither.write_calibration_preview(tmp_dir)
            if len(paths) != 3:
                return False, "write_calibration_preview() returned %d paths, expected 3: %r" % (len(paths), paths)
            for path in paths:
                if not os.path.isfile(path):
                    return False, "write_calibration_preview() reported %r but it does not exist on disk" % (path,)
                if not path.lower().endswith(".png"):
                    return False, "write_calibration_preview() reported a non-PNG path: %r" % (path,)
            return True, ""
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    check(
        "write_calibration_preview() writes exactly three PNG files and returns their paths",
        _calibration_preview_writes_three_pngs,
    )

    # 15. MOOD_BASE_RGB is genuinely derived from panel_format.PALETTE_RGB,
    # not re-typed - a live-drift check, not just a static source grep.
    def _mood_base_rgb_tracks_palette_rgb():
        from server.plane import runway_config as rc

        expected_blue = tuple(pf.PALETTE_RGB[pf.IDX_BLUE * 3 : pf.IDX_BLUE * 3 + 3])
        expected_green = tuple(pf.PALETTE_RGB[pf.IDX_GREEN * 3 : pf.IDX_GREEN * 3 + 3])
        if dither.MOOD_BASE_RGB[rc.STATE_DEPARTING] != expected_blue:
            return False, "MOOD_BASE_RGB[departing] is %r, expected panel_format.PALETTE_RGB's Blue entry %r" % (
                dither.MOOD_BASE_RGB[rc.STATE_DEPARTING], expected_blue,
            )
        if dither.MOOD_BASE_RGB[rc.STATE_ARRIVING] != expected_green:
            return False, "MOOD_BASE_RGB[arriving] is %r, expected panel_format.PALETTE_RGB's Green entry %r" % (
                dither.MOOD_BASE_RGB[rc.STATE_ARRIVING], expected_green,
            )
        return True, ""
    check(
        "MOOD_BASE_RGB tracks panel_format.PALETTE_RGB's Blue/Green entries directly (no re-typed literals)",
        _mood_base_rgb_tracks_palette_rgb,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("dither: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
