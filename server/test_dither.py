#!/usr/bin/env python3
"""Contract harness for server/plane/dither.py's full-6-color palette
dither helper (D-25/D-26, PLANE-01/PLANE-02).

Stdlib-only, plus the module under test (server.plane.dither,
server.panel_format) - dither.py transitively imports Pillow, so this
harness must be run under server/.venv's interpreter, not the bare system
python3. Exits 0 only when every check below passes; any failure (or
exception - none is ever swallowed into a pass) exits 1. Matches the same
check()/EXPECTED_CHECK_COUNT/main() convention every sibling server/test_*.py
file uses (see server/test_plane_detection.py) - no pytest.

Phase 3 D-21 (03-CONTEXT.md): this module's earlier two-tone dithered
"mood background" (`build_mood_background()`, D-17/D-18) was retired when
the active-state background became a flat single-color fill - this harness
no longer tests it. Only `panel_palette_image()`/`dither_to_full_panel_palette()`
survive, now reused by render.py's real-illustration compositing path.

Note: Pillow's Image.getcolors() returns (count, value) pairs - count
first, value second.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 6


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
        from server import panel_format as pf
    except ImportError as exc:
        print("FAIL import server.plane.dither / server.panel_format - %r" % (exc,))
        print("dither: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    from PIL import Image

    def _index_set(canvas):
        return {value for _count, value in canvas.getcolors()}

    # 1. panel_palette_image() carries exactly PALETTE_RGB's 6 entries, no
    # zero-padding to 256 (03-RESEARCH.md Pitfall 2 - a padded filler entry
    # can win nearest-neighbour matching for near-black source pixels).
    def _palette_image_is_unpadded():
        img = dither.panel_palette_image()
        palette = img.getpalette()
        expected = list(pf.PALETTE_RGB)
        if palette != expected:
            return False, "panel_palette_image()'s palette is %r, expected exactly PALETTE_RGB %r (unpadded)" % (
                palette, expected,
            )
        return True, ""
    check("panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded", _palette_image_is_unpadded)

    # 2. dither_to_full_panel_palette() maps an arbitrary RGB image onto
    # indices drawn only from 0..5, with no remap applied.
    def _full_palette_dither_stays_within_legal_indices():
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

    # 3. A flat single-color source image quantizes to exactly that one
    # index - the nearest-neighbour match must be exact for an already-
    # legal color, not smeared across neighbours by dithering noise.
    def _flat_source_quantizes_to_single_index():
        flat = Image.new("RGB", (16, 16), tuple(pf.PALETTE_RGB[pf.IDX_RED * 3 : pf.IDX_RED * 3 + 3]))
        quantized = dither.dither_to_full_panel_palette(flat)
        idx_set = _index_set(quantized)
        if idx_set != {pf.IDX_RED}:
            return False, "flat Red-colored source quantized to index set %r, expected {IDX_RED}" % (idx_set,)
        return True, ""
    check("a flat single-color RGB source quantizes to exactly that color's own index", _flat_source_quantizes_to_single_index)

    # 4. dither_to_full_panel_palette() is deterministic for the same input.
    def _same_input_is_deterministic():
        hue_rich = Image.new("RGB", (32, 32))
        pixels = hue_rich.load()
        for y in range(32):
            for x in range(32):
                pixels[x, y] = (x * 8 % 256, y * 8 % 256, 128)
        first = dither.dither_to_full_panel_palette(hue_rich).tobytes()
        second = dither.dither_to_full_panel_palette(hue_rich).tobytes()
        if first != second:
            return False, "two dither_to_full_panel_palette() calls on the same input produced different bytes"
        return True, ""
    check("dither_to_full_panel_palette() is deterministic for the same input image", _same_input_is_deterministic)

    # 5. write_calibration_preview() writes the palette-swatch PNG and
    # returns its path.
    def _calibration_preview_writes_swatch_png():
        tmp_dir = tempfile.mkdtemp(prefix="skypane-dither-calib-")
        try:
            paths = dither.write_calibration_preview(tmp_dir)
            if len(paths) != 1:
                return False, "write_calibration_preview() returned %d paths, expected 1: %r" % (len(paths), paths)
            path = paths[0]
            if not os.path.isfile(path):
                return False, "write_calibration_preview() reported %r but it does not exist on disk" % (path,)
            if not path.lower().endswith(".png"):
                return False, "write_calibration_preview() reported a non-PNG path: %r" % (path,)
            return True, ""
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    check(
        "write_calibration_preview() writes exactly one palette-swatch PNG and returns its path",
        _calibration_preview_writes_swatch_png,
    )

    # 6. build_mood_background() no longer exists - a live-drift check that
    # the D-21 retirement was actually completed, not just intended.
    def _mood_background_is_retired():
        if hasattr(dither, "build_mood_background"):
            return False, "dither.build_mood_background() still exists - D-21 retired it, this must be dead code left behind"
        return True, ""
    check("build_mood_background() no longer exists on server.plane.dither (D-21 retirement)", _mood_background_is_retired)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("dither: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
