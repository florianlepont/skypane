#!/usr/bin/env python3
"""Contract harness for server/panel_preview.py (CFG-10): proves
unpack_panel() is the exact inverse of panel_format.pack_panel() over a
full canvas containing all six legal palette indices (including a mixed
nibble pair inside one packed byte), that malformed input raises the
typed PanelDecodeError rather than crashing, that panel_png_bytes()
produces a real PNG with nearest-neighbour-only thumbnailing, and that a
real production render round-trips exactly.

Stdlib-only, plus the modules under test (server.panel_preview,
server.panel_format, server.plane.render) and Pillow - Pillow is a hard
dependency of every module under test, so this harness must be run under
server/.venv's interpreter, not the bare system python3. Exits 0 only
when every check below passes; any failure (or exception - none is ever
swallowed into a pass) exits 1.

Usage:
    server/.venv/bin/python3 server/test_panel_preview.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 11


def _draw_all_six_indices_canvas(panel_format):
    """A full-canvas fixture painted in six horizontal bands, one per
    legal palette index (0-5), so every legal nibble code appears in the
    packed output - built in-process, no fixture file.
    """
    from PIL import ImageDraw

    canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    indices = [
        panel_format.IDX_BLACK,
        panel_format.IDX_WHITE,
        panel_format.IDX_YELLOW,
        panel_format.IDX_RED,
        panel_format.IDX_BLUE,
        panel_format.IDX_GREEN,
    ]
    band_height = panel_format.HEIGHT // len(indices)
    for i, idx in enumerate(indices):
        top = i * band_height
        bottom = panel_format.HEIGHT if i == len(indices) - 1 else (i + 1) * band_height
        draw.rectangle([0, top, panel_format.WIDTH - 1, bottom - 1], fill=idx)
    return canvas


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
        from PIL import Image, ImageDraw

        import server.panel_format as panel_format
        import server.panel_preview as panel_preview
        import server.plane.render as render
    except ImportError as exc:
        print("FAIL import server.panel_preview / server.panel_format / server.plane.render - %r" % (exc,))
        print("panel-preview: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    ctx = {}

    # 1. A canvas built with new_canvas() and drawn on, packed then
    # unpacked, yields a "P"-mode image whose per-pixel index data is
    # identical to the original canvas's - every pixel, not a sample.
    def _basic_round_trip_is_exact():
        canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([100, 100, 500, 900], fill=panel_format.IDX_BLUE)
        draw.rectangle([600, 200, 1100, 700], fill=panel_format.IDX_GREEN)
        raw = panel_format.pack_panel(canvas)
        unpacked = panel_preview.unpack_panel(raw)
        if unpacked.mode != "P":
            return False, "expected 'P' mode, got %r" % (unpacked.mode,)
        if unpacked.size != (panel_format.WIDTH, panel_format.HEIGHT):
            return False, "expected size %r, got %r" % ((panel_format.WIDTH, panel_format.HEIGHT), unpacked.size)
        original_data = list(canvas.getdata())
        unpacked_data = list(unpacked.getdata())
        if unpacked_data != original_data:
            return False, "unpacked index data does not match the original canvas, pixel-for-pixel"
        return True, ""
    check(
        "a drawn canvas, packed then unpacked, yields identical per-pixel index data",
        _basic_round_trip_is_exact,
    )

    # 2. The round trip holds for a canvas containing all six legal
    # palette indices at once, including an odd/even column pair carrying
    # two different indices inside one packed byte.
    def _all_six_indices_with_mixed_pair_round_trips():
        canvas = _draw_all_six_indices_canvas(panel_format)
        draw = ImageDraw.Draw(canvas)
        # Force an explicit mixed nibble pair: column 400 (even, left of a
        # packed byte) and column 401 (odd, right of the same packed
        # byte) get two different legal indices.
        draw.point((400, 10), fill=panel_format.IDX_RED)
        draw.point((401, 10), fill=panel_format.IDX_GREEN)
        raw = panel_format.pack_panel(canvas)
        unpacked = panel_preview.unpack_panel(raw)
        if list(unpacked.getdata()) != list(canvas.getdata()):
            return False, "round trip diverged on the all-six-indices canvas"
        return True, ""
    check(
        "a canvas containing all six legal indices, including a mixed odd/even column pair, round-trips exactly",
        _all_six_indices_with_mixed_pair_round_trips,
    )

    # 3. unpack_panel() on a byte string of the wrong length raises
    # PanelDecodeError, not AssertionError and not IndexError.
    def _wrong_length_raises_panel_decode_error():
        try:
            panel_preview.unpack_panel(b"\x00" * (panel_format.IMAGE_BYTES - 1))
        except panel_preview.PanelDecodeError:
            return True, ""
        except (AssertionError, IndexError) as exc:
            return False, "raised %r instead of PanelDecodeError" % (exc,)
        except Exception as exc:
            return False, "raised unexpected %r instead of PanelDecodeError" % (exc,)
        return False, "no exception raised on wrong-length input"
    check(
        "unpack_panel() on wrong-length input raises PanelDecodeError, never AssertionError/IndexError",
        _wrong_length_raises_panel_decode_error,
    )

    # 4. unpack_panel() on a correctly-sized buffer containing the one
    # illegal nibble code (0x4, skipped between red 0x3 and blue 0x5)
    # raises PanelDecodeError naming the offending code.
    def _illegal_nibble_raises_named_panel_decode_error():
        raw = bytearray(panel_format.IMAGE_BYTES)
        raw[0] = 0x40  # high nibble 0x4 is illegal; low nibble 0x0 (black) is legal
        try:
            panel_preview.unpack_panel(bytes(raw))
        except panel_preview.PanelDecodeError as exc:
            if "0x4" not in str(exc) and "4" not in str(exc):
                return False, "PanelDecodeError message does not name the illegal code: %r" % (str(exc),)
            return True, ""
        except Exception as exc:
            return False, "raised %r instead of PanelDecodeError" % (exc,)
        return False, "no exception raised on illegal-nibble input"
    check(
        "unpack_panel() on the one illegal nibble code raises PanelDecodeError naming the offending code",
        _illegal_nibble_raises_named_panel_decode_error,
    )

    # 5. panel_png_bytes() returns a bytes object beginning with the
    # 8-byte PNG signature, decodable by Pillow back to the expected
    # dimensions.
    def _panel_png_bytes_is_a_real_png():
        canvas = _draw_all_six_indices_canvas(panel_format)
        raw = panel_format.pack_panel(canvas)
        ctx["all_six_raw"] = raw
        png_bytes = panel_preview.panel_png_bytes(raw)
        if not isinstance(png_bytes, bytes):
            return False, "expected bytes, got %r" % (type(png_bytes),)
        png_signature = b"\x89PNG\r\n\x1a\n"
        if png_bytes[:8] != png_signature:
            return False, "first 8 bytes are not the PNG signature: %r" % (png_bytes[:8],)
        decoded = Image.open(__import__("io").BytesIO(png_bytes))
        decoded.load()
        if decoded.size != (panel_format.WIDTH, panel_format.HEIGHT):
            return False, "decoded PNG size %r != expected %r" % (decoded.size, (panel_format.WIDTH, panel_format.HEIGHT))
        ctx["full_png_bytes"] = png_bytes
        return True, ""
    check(
        "panel_png_bytes() returns real, Pillow-decodable PNG bytes at the expected dimensions",
        _panel_png_bytes_is_a_real_png,
    )

    # 6. panel_png_bytes(..., max_width=N) returns a proportionally
    # smaller image resampled with nearest-neighbour, keeping the flat
    # six-colour fields rather than inventing intermediate colours.
    def _thumbnail_is_proportionally_resized():
        raw = ctx["all_six_raw"]
        thumb_bytes = panel_preview.panel_png_bytes(raw, max_width=240)
        import io as _io

        decoded = Image.open(_io.BytesIO(thumb_bytes))
        decoded.load()
        expected_height = round(panel_format.HEIGHT * (240 / float(panel_format.WIDTH)))
        if decoded.width != 240:
            return False, "expected thumbnail width 240, got %d" % (decoded.width,)
        if abs(decoded.height - expected_height) > 1:
            return False, "expected thumbnail height ~%d, got %d" % (expected_height, decoded.height)
        ctx["thumb_bytes"] = thumb_bytes
        return True, ""
    check(
        "panel_png_bytes(max_width=240) returns a proportionally resized thumbnail",
        _thumbnail_is_proportionally_resized,
    )

    # 7. read_panel_file() on a missing file returns None rather than raising.
    def _read_panel_file_missing_returns_none():
        result = panel_preview.read_panel_file("/nonexistent/skypane-panel-preview-test-dir")
        if result is not None:
            return False, "expected None on a missing panel file, got %r" % (result,)
        return True, ""
    check(
        "read_panel_file() on a missing file returns None rather than raising",
        _read_panel_file_missing_returns_none,
    )

    # 8. A canvas painted so that column 0 and column 1 of some row carry
    # two *different* legal indices, proving the high/low nibble split is
    # not transposed. A transposition bug would round-trip a uniform
    # canvas perfectly and only show up on a mixed pair, so this check is
    # the one that actually catches it.
    def _mixed_pair_catches_nibble_transposition():
        canvas = panel_format.new_canvas(panel_format.IDX_BLACK)
        draw = ImageDraw.Draw(canvas)
        # Column 0 (left/high nibble) and column 1 (right/low nibble) of
        # row 5 get two distinct legal indices.
        draw.point((0, 5), fill=panel_format.IDX_YELLOW)
        draw.point((1, 5), fill=panel_format.IDX_RED)
        raw = panel_format.pack_panel(canvas)
        unpacked = panel_preview.unpack_panel(raw)
        left = unpacked.getpixel((0, 5))
        right = unpacked.getpixel((1, 5))
        if left != panel_format.IDX_YELLOW or right != panel_format.IDX_RED:
            return False, "expected (yellow, red) at (col0, col1) of row 5, got (%r, %r)" % (left, right)
        return True, ""
    check(
        "a row with two different legal indices at column 0 and column 1 round-trips without a high/low nibble swap",
        _mixed_pair_catches_nibble_transposition,
    )

    # 9. A canvas exercising all six legal indices at once, with the round
    # trip compared over the full getdata() sequence, not a sampled subset.
    def _full_getdata_sequence_matches_over_all_six_indices():
        canvas = _draw_all_six_indices_canvas(panel_format)
        raw = panel_format.pack_panel(canvas)
        unpacked = panel_preview.unpack_panel(raw)
        original_data = list(canvas.getdata())
        unpacked_data = list(unpacked.getdata())
        if len(unpacked_data) != panel_format.WIDTH * panel_format.HEIGHT:
            return False, "unpacked getdata() length %d != expected %d" % (
                len(unpacked_data), panel_format.WIDTH * panel_format.HEIGHT
            )
        if unpacked_data != original_data:
            mismatches = sum(1 for a, b in zip(original_data, unpacked_data) if a != b)
            return False, "%d of %d pixels mismatched over the full getdata() sequence" % (mismatches, len(original_data))
        return True, ""
    check(
        "the full getdata() sequence (not a sampled subset) matches exactly for an all-six-indices canvas",
        _full_getdata_sequence_matches_over_all_six_indices,
    )

    # 10. A production round trip: render.render_panel(None, "empty")
    # unpacked and compared index-for-index against
    # render.build_canvas(None, "empty")'s own data.
    def _production_render_round_trips_exactly():
        raw = render.render_panel(None, "empty")
        unpacked = panel_preview.unpack_panel(raw)
        expected_canvas = render.build_canvas(None, "empty")
        if list(unpacked.getdata()) != list(expected_canvas.getdata()):
            return False, "production render_panel(None, 'empty') round trip diverged from build_canvas(None, 'empty')"
        return True, ""
    check(
        "a real production render.render_panel(None, 'empty') round-trips index-for-index against build_canvas()",
        _production_render_round_trips_exactly,
    )

    # 11. A panel_png_bytes(..., max_width=240) check asserting the
    # decoded thumbnail's colour set is a subset of the full image's
    # colour set - the operational proof that nearest-neighbour
    # resampling introduced no new colours.
    def _thumbnail_colour_set_is_subset_of_full_image():
        import io as _io

        full_decoded = Image.open(_io.BytesIO(ctx["full_png_bytes"]))
        full_decoded.load()
        thumb_decoded = Image.open(_io.BytesIO(ctx["thumb_bytes"]))
        thumb_decoded.load()
        full_colours = {rgb for _count, rgb in full_decoded.getcolors(maxcolors=1000)}
        thumb_colours = {rgb for _count, rgb in thumb_decoded.getcolors(maxcolors=1000)}
        if not thumb_colours.issubset(full_colours):
            extra = thumb_colours - full_colours
            return False, "thumbnail introduced colours not present in the full image: %r" % (extra,)
        return True, ""
    check(
        "the nearest-neighbour thumbnail's colour set is a strict subset of the full image's colour set",
        _thumbnail_colour_set_is_subset_of_full_image,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("panel-preview: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
