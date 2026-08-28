#!/usr/bin/env python3
"""Contract harness for server/plane/render.py's two-flight poster layout
(D-21/D-24/D-25/D-26/D-27, 03-CONTEXT.md decisions_addendum_2/3).

Stdlib-only, plus the module under test (server.plane.render,
server.panel_format, server.plane.illustrations) - render.py transitively
imports Pillow, so this harness must be run under server/.venv's
interpreter, not the bare system python3. Exits 0 only when every check
below passes; any failure (or exception - none is ever swallowed into a
pass) exits 1.

This harness asserts on the rendered canvas and packed bytes only - never
on a screenshot. Text-content assertions spy on `ImageDraw.ImageDraw.text`
(the module's sole text-draw call site since D-26 dropped tracked-text
compositing) rather than rendering to a scratch canvas and comparing pixel
signatures or doing OCR.

Uses the real vendored illustration files under
server/assets/icons/illustrations/ (air-france.png, transavia-france.png,
generic-fallback.png, ...) - these are real project assets, not test
fixtures, so a broken selection/compositing path is caught against the
same files poll_loop.py will actually serve.

Usage:
    server/.venv/bin/python3 server/test_render.py
"""
import contextlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 64

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}
LEGAL_IDX = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}

TEST_FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
TEST_PREVIOUS_FLIGHT = {"hex": "4a1b02", "callsign": "VLG6PD", "aircraft_type": "A320"}

# A real resolved route (server/fixtures/adsbdb_hit_TVF16VB.json, already
# sentence-cased per server.plane.enrich.to_sentence_case_city) - its
# airline_name ("Transavia France") resolves to a real vendored
# illustration file (transavia-france.png, added to HANDOFF.md 2026-08-26).
TEST_ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
}
TEST_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
}

# A genuinely long real destination city name and a genuinely long real
# airline name, used to exercise fit_text_size()'s shrink path.
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


class _TextSpy:
    """Captures every ImageDraw.ImageDraw.text() call made while building
    one canvas - the module's sole text-draw call site since D-26 dropped
    tracked-text compositing. list of (text, xy, anchor).
    """

    def __init__(self, render_mod):
        self._render_mod = render_mod
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = self._render_mod.ImageDraw.ImageDraw.text

        def _spy(draw_self, xy, text, *args, **kwargs):
            self.calls.append((text, xy, kwargs.get("anchor")))
            return self._orig(draw_self, xy, text, *args, **kwargs)

        self._render_mod.ImageDraw.ImageDraw.text = _spy
        return self

    def __exit__(self, exc_type, exc, tb):
        self._render_mod.ImageDraw.ImageDraw.text = self._orig
        return False


class _SelectIllustrationSpy:
    """Captures every illustrations.select_illustration() call made by
    render.py's _build_active_canvas() while building one canvas - a list
    of (route, aircraft_type) argument pairs, in call order. Monkeypatches
    render.illustrations.select_illustration (the reference render.py
    itself calls through), following _TextSpy's monkeypatch-and-restore
    shape.
    """

    def __init__(self, render_mod):
        self._render_mod = render_mod
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = self._render_mod.illustrations.select_illustration

        def _spy(route, aircraft_type=None):
            self.calls.append((route, aircraft_type))
            return self._orig(route, aircraft_type)

        self._render_mod.illustrations.select_illustration = _spy
        return self

    def __exit__(self, exc_type, exc, tb):
        self._render_mod.illustrations.select_illustration = self._orig
        return False


def _write_garbage_png():
    """Create a NamedTemporaryFile with a `.png` suffix that passes
    os.path.isfile() but carries no valid PNG signature - matching
    03-VERIFICATION.md's live repro of the crash 03-04-PLAN.md closes: a
    file that exists on disk but is not decodable image data.
    """
    fh = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fh.write(b"not a real PNG file - just a short run of garbage bytes 0123456789")
    fh.close()
    return fh.name


def _write_oversized_png():
    """Build a genuinely valid, decodable PNG whose pixel count exceeds
    illustrations.ILLUSTRATION_MAX_PIXELS (40,000,000): 7000x6000 =
    42,000,000 pixels. Single-band mode "L" keeps the in-memory fixture
    around 42MB rather than the 168MB an RGBA buffer of that size would
    need, and stays comfortably under Pillow's own Image.MAX_IMAGE_PIXELS
    so no DecompressionBombWarning fires. compress_level=1 keeps the write
    fast (about a second) and the on-disk size small (a few tens of KB).
    Using a genuinely decodable oversized file (not garbage) is what makes
    the check that consumes this fixture prove a header-only cap exists -
    a bare try/except around the decode cannot satisfy it, because the
    decode would succeed and paint a different panel.
    """
    from PIL import Image

    img = Image.new("L", (7000, 6000), color=128)
    fh = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fh.close()
    img.save(fh.name, format="PNG", compress_level=1)
    return fh.name


@contextlib.contextmanager
def _forced_illustration(render_mod, path, fallback_path=None):
    """Monkeypatch `render_mod.illustrations.select_illustration` to a
    lambda accepting `(route, aircraft_type=None)` and returning `path` -
    following `_SelectIllustrationSpy`'s exact monkeypatch-and-restore
    shape, but overriding the return value instead of recording arguments.
    When `fallback_path` is given, also monkeypatches
    `render_mod.illustrations.generic_fallback_path` to return it -
    letting a caller force both the primary candidate and the fallback
    candidate to the same (or different) undecodable file. Restores both
    originals on exit, even if the body raises.
    """
    orig_select = render_mod.illustrations.select_illustration
    orig_fallback = render_mod.illustrations.generic_fallback_path
    render_mod.illustrations.select_illustration = lambda route, aircraft_type=None: path
    if fallback_path is not None:
        render_mod.illustrations.generic_fallback_path = lambda: fallback_path
    try:
        yield
    finally:
        render_mod.illustrations.select_illustration = orig_select
        render_mod.illustrations.generic_fallback_path = orig_fallback


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
        import server.plane.illustrations as illustrations
        from PIL import Image
    except ImportError as exc:
        print("FAIL import server.plane.render / server.panel_format / server.plane.illustrations - %r" % (exc,))
        print("render: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    ctx = {}

    # 1-2. Both active states pack to exactly 960000 bytes with only legal nibble codes.
    def _departing_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "departing render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "departing render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["departing_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'departing', route) packs to exactly 960000 bytes with only legal nibbles", _departing_packs_correctly)

    def _arriving_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "arriving render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "arriving render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["arriving_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'arriving', route) packs to exactly 960000 bytes with only legal nibbles", _arriving_packs_correctly)

    # 3-4. The flat background field (D-21) is still the dominant nibble per state.
    def _departing_dominant_is_blue():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_BLUE:
            return False, "departing render's dominant nibble is 0x%x, expected 0x5 (Blue)" % dom
        return True, ""
    check("departing render's dominant nibble is 0x5 (Blue) - D-21 flat background field", _departing_dominant_is_blue)

    def _arriving_dominant_is_green():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_GREEN:
            return False, "arriving render's dominant nibble is 0x%x, expected 0x6 (Green)" % dom
        return True, ""
    check("arriving render's dominant nibble is 0x6 (Green) - D-21 flat background field", _arriving_dominant_is_green)

    # 5-6. A real illustration's full livery colors legitimately reach the
    # panel - D-25 supersedes the old "Black/Yellow/Red drop out of the
    # active states" reservation, which only held while the centrepiece was
    # a flat single-index silhouette fill.
    def _departing_has_white_and_black_from_real_livery():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        counts = nibble_counts(buf)
        if NIBBLE_WHITE not in counts:
            return False, "departing render contains no White (0x1) nibble - no foreground content drawn"
        if NIBBLE_BLACK not in counts:
            return False, "departing render contains no Black (0x0) nibble - Transavia France's real livery art should contribute some"
        return True, ""
    check(
        "departing render contains White (text/frame) and Black (real illustration livery) nibbles - D-25 full-color compositing",
        _departing_has_white_and_black_from_real_livery,
    )

    def _only_legal_indices_present():
        buf = ctx.get("departing_bytes")
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "departing render contains illegal nibble(s): %r" % (sorted(bad),)
        return True, ""
    check("departing render's nibble set is a subset of the 6 legal Spectra 6 codes", _only_legal_indices_present)

    # 7. Empty state is unchanged: White-dominant, at least one Black pixel.
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

    # 8. Determinism: rendering the same flight+route twice is byte-identical.
    def _rendering_is_deterministic():
        first = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        second = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        if first != second:
            return False, "rendering the same flight twice produced different bytes - render_panel is not deterministic"
        return True, ""
    check("rendering the same flight+route twice produces byte-identical output (determinism)", _rendering_is_deterministic)

    # 9. State actually changes the output.
    def _departing_and_arriving_differ():
        departing = ctx.get("departing_bytes")
        arriving = ctx.get("arriving_bytes")
        if departing is None or arriving is None:
            return False, "missing captured bytes from a previous check"
        if departing == arriving:
            return False, "departing and arriving renders of the same flight are byte-identical - state does not change output"
        return True, ""
    check("departing and arriving renders of the same flight differ in bytes (state changes output)", _departing_and_arriving_differ)

    # 10. D-24: illustrations are never mirrored. The main illustration's
    # own opaque pixels must be byte-identical between departing and
    # arriving renders of the same flight+route - only the background
    # color and text below/around it may differ by state.
    def _illustration_not_mirrored_between_states():
        path = illustrations.select_illustration(TEST_ROUTE)
        if path is None:
            return False, "illustrations.select_illustration(TEST_ROUTE) returned None - no vendored file resolved"
        inner_width = panel_format.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
        main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
        main_top = round(panel_format.HEIGHT * render.MAIN_ILLUSTRATION_TOP_FRAC)
        resized = render._resize_illustration(path, main_w)
        left = (panel_format.WIDTH - resized.size[0]) // 2
        bbox = (left, main_top, left + resized.size[0], main_top + resized.size[1])

        dep_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        arr_canvas = render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        dep_px = list(dep_canvas.crop(bbox).getdata())
        arr_px = list(arr_canvas.crop(bbox).getdata())

        opaque_total = 0
        mismatches = 0
        for dep_v, arr_v in zip(dep_px, arr_px):
            dep_is_bg = dep_v == IDX_BLUE
            arr_is_bg = arr_v == IDX_GREEN
            if not dep_is_bg and not arr_is_bg:
                opaque_total += 1
                if dep_v != arr_v:
                    mismatches += 1
        if opaque_total < 1000:
            return False, "only %d opaque illustration pixels found in the computed bbox %r - geometry looks wrong" % (opaque_total, bbox)
        if mismatches:
            return False, "%d of %d opaque illustration pixels differ between departing and arriving renders - illustration is being mirrored/recolored by state (D-24 violation)" % (mismatches, opaque_total)
        return True, ""
    check(
        "the main illustration's opaque pixels are byte-identical between departing and arriving renders (D-24: never mirrored by state)",
        _illustration_not_mirrored_between_states,
    )

    # 11. draw_illustration()/_resize_illustration() have no mirror/flip
    # parameter at all - a structural guard against D-24 being silently
    # reintroduced.
    def _illustration_functions_have_no_mirror_param():
        import inspect

        for fn_name in ("draw_illustration", "_resize_illustration"):
            fn = getattr(render, fn_name, None)
            if fn is None:
                return False, "server.plane.render has no %s()" % fn_name
            params = set(inspect.signature(fn).parameters)
            bad = {p for p in params if "mirror" in p.lower() or "flip" in p.lower()}
            if bad:
                return False, "%s() has a mirror/flip parameter %r - D-24 dropped mirroring entirely" % (fn_name, bad)
        return True, ""
    check("draw_illustration()/_resize_illustration() have no mirror/flip parameter (D-24)", _illustration_functions_have_no_mirror_param)

    # 12. D-25: a soft/gradient alpha source never leaks an illegal
    # in-between palette index onto the canvas (03-RESEARCH.md Pitfall 2) -
    # the alpha channel must be hard-thresholded before paste().
    def _soft_alpha_illustration_stays_within_legal_palette():
        gradient = Image.new("RGBA", (40, 40))
        pixels = gradient.load()
        for y in range(40):
            for x in range(40):
                # A soft horizontal alpha ramp over a solid Red-ish fill -
                # exactly the shape 03-RESEARCH.md Pitfall 2 describes.
                pixels[x, y] = (200, 30, 30, int(255 * x / 39))
        canvas = panel_format.new_canvas(IDX_BLUE)
        bbox = render.draw_illustration(canvas, gradient, 10, 10)
        if bbox != (10, 10, 50, 50):
            return False, "draw_illustration() returned bbox %r, expected (10, 10, 50, 50)" % (bbox,)
        idx_set = {value for _count, value in canvas.getcolors()} if canvas.getcolors() else set()
        illegal = idx_set - LEGAL_IDX
        if illegal:
            return False, "a soft-alpha source produced illegal palette index(es) %r on the canvas - alpha must be hard-thresholded before paste()" % (sorted(illegal),)
        return True, ""
    check(
        "draw_illustration() with a soft/gradient alpha source never produces an illegal in-between palette index (Pitfall 2 regression)",
        _soft_alpha_illustration_stays_within_legal_palette,
    )

    # 13. The illustration is genuinely selected from `route` - a different
    # airline_name changes which file gets composited, hence changes bytes.
    def _different_airline_changes_the_rendered_bytes():
        fallback_route = {
            "airline_name": "Some Airline Never Vendored",
            "origin_iata": "ORY",
            "origin_city": "Paris",
            "destination_iata": "PMI",
            "destination_city": "Palma de Mallorca",
        }
        with_real_airline = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        with_fallback = render.render_panel(TEST_FLIGHT, "departing", route=fallback_route)
        if with_real_airline == with_fallback:
            return False, "rendering with TEST_ROUTE's real airline vs. an unvendored airline (falls back to generic-fallback.png) produced byte-identical panels"
        return True, ""
    check(
        "a route whose airline_name has no vendored file falls back to generic-fallback.png and renders different bytes than a route with real art",
        _different_airline_changes_the_rendered_bytes,
    )

    # 14-15. D-26 top row: state label + static tag, both near the MARGIN
    # inset, in the correct top corners.
    def _departing_top_row_labels_present():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        if "DEPARTING" not in texts:
            return False, "expected the top-left state label 'DEPARTING' among the text draws, got %r" % (texts,)
        if render.TOP_RIGHT_TAG_TEXT not in texts:
            return False, "expected the top-right tag %r among the text draws, got %r" % (render.TOP_RIGHT_TAG_TEXT, texts)
        return True, ""
    check("departing render draws the top-left 'DEPARTING' label and the top-right static tag", _departing_top_row_labels_present)

    def _top_labels_sit_at_the_margin_inset():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        label_calls = [(xy, anchor) for t, xy, anchor in spy.calls if t == "ARRIVING"]
        tag_calls = [(xy, anchor) for t, xy, anchor in spy.calls if t == render.TOP_RIGHT_TAG_TEXT]
        if not label_calls:
            return False, "no 'ARRIVING' text draw captured"
        if not tag_calls:
            return False, "no top-right tag text draw captured"
        (label_xy, label_anchor) = label_calls[0]
        (tag_xy, tag_anchor) = tag_calls[0]
        if label_xy != (render.MARGIN, render.MARGIN) or label_anchor != "la":
            return False, "state label drawn at %r anchor=%r, expected (%d, %d) anchor='la'" % (label_xy, label_anchor, render.MARGIN, render.MARGIN)
        if tag_xy != (panel_format.WIDTH - render.MARGIN, render.MARGIN) or tag_anchor != "ra":
            return False, "top-right tag drawn at %r anchor=%r, expected (%d, %d) anchor='ra'" % (tag_xy, tag_anchor, panel_format.WIDTH - render.MARGIN, render.MARGIN)
        return True, ""
    check("the state label and top-right tag are drawn exactly at the MARGIN inset, in their respective top corners (D-26)", _top_labels_sit_at_the_margin_inset)

    # 16. D-26 frame: a thin outline is present at the ~2.5%-of-width inset.
    def _frame_outline_is_drawn():
        canvas = panel_format.new_canvas(IDX_BLUE)
        box = render.draw_frame(canvas, IDX_WHITE)
        inset = round(panel_format.WIDTH * render.FRAME_INSET_FRAC)
        if box != (inset, inset, panel_format.WIDTH - inset, panel_format.HEIGHT - inset):
            return False, "draw_frame() returned box %r, expected a %dpx inset rectangle" % (box, inset)
        # Sample a point along the top edge - must be the ink color, not the background.
        sample = canvas.getpixel((panel_format.WIDTH // 2, inset))
        if sample != IDX_WHITE:
            return False, "sampled frame pixel at %r is index %r, expected IDX_WHITE" % ((panel_format.WIDTH // 2, inset), sample)
        return True, ""
    check("draw_frame() draws a thin outline at the ~2.5%%-of-width inset (D-26)", _frame_outline_is_drawn)

    # 17-19. Main flight text: "{callsign} to|from {city}" line 1, airline
    # name line 2, no "PREVIOUS ·" prefix leaking onto the main block.
    def _departing_main_text_uses_lowercase_to():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s to %s" % (TEST_FLIGHT["callsign"], TEST_ROUTE["destination_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_FLIGHT["aircraft_type"]]
        expected_line2 = "%s · %s" % (TEST_ROUTE["airline_name"], type_label)
        if expected_line1 not in texts:
            return False, "expected main line 1 %r among the text draws, got %r" % (expected_line1, texts)
        if expected_line2 not in texts:
            return False, "expected main line 2 %r among the text draws, got %r" % (expected_line2, texts)
        return True, ""
    check("departing main flight text is '{callsign} to {destination_city}' / '{airline_name} · {type_label}' (D-26/PLANE-04)", _departing_main_text_uses_lowercase_to)

    def _arriving_main_text_uses_lowercase_from():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s from %s" % (TEST_FLIGHT["callsign"], TEST_ROUTE["origin_city"])
        if expected_line1 not in texts:
            return False, "expected main line 1 %r among the text draws, got %r" % (expected_line1, texts)
        return True, ""
    check("arriving main flight text is '{callsign} from {origin_city}' (D-26 lowercase sentence text)", _arriving_main_text_uses_lowercase_from)

    def _enrichment_miss_falls_back_to_callsign_and_fallback_text():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=None)
        texts = [t for t, _xy, _anchor in spy.calls]
        if TEST_FLIGHT["callsign"] not in texts:
            return False, "expected bare callsign %r among the text draws on an enrichment miss, got %r" % (TEST_FLIGHT["callsign"], texts)
        if render.ROUTE_FALLBACK_TEXT not in texts:
            return False, "expected %r among the text draws on an enrichment miss, got %r" % (render.ROUTE_FALLBACK_TEXT, texts)
        return True, ""
    check("an enrichment miss (route=None) draws the bare callsign and ROUTE_FALLBACK_TEXT instead of a half-resolved route", _enrichment_miss_falls_back_to_callsign_and_fallback_text)

    # 20-22. D-25/D-26 previous flight card: present only when supplied, no
    # "PREVIOUS ·" prefix, right-aligned text, own real illustration.
    def _previous_flight_card_renders_its_own_text():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s from %s" % (TEST_PREVIOUS_FLIGHT["callsign"], TEST_PREVIOUS_ROUTE["origin_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_PREVIOUS_FLIGHT["aircraft_type"]]
        expected_line2 = "%s · %s" % (TEST_PREVIOUS_ROUTE["airline_name"], type_label)
        if expected_line1 not in texts:
            return False, "expected previous-flight line 1 %r among the text draws, got %r" % (expected_line1, texts)
        if expected_line2 not in texts:
            return False, "expected previous-flight line 2 %r among the text draws, got %r" % (expected_line2, texts)
        return True, ""
    check("a supplied previous_flight/previous_route renders its own real two-line text block", _previous_flight_card_renders_its_own_text)

    def _previous_flight_text_has_no_previous_prefix():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        texts = [t for t, _xy, _anchor in spy.calls]
        offenders = [t for t in texts if "PREVIOUS" in t.upper()]
        if offenders:
            return False, "found a 'PREVIOUS' prefix in the drawn text %r - D-26 explicitly removed it" % (offenders,)
        return True, ""
    check("no drawn text contains a 'PREVIOUS ·' prefix (D-26: explicitly removed after the live sketch pass)", _previous_flight_text_has_no_previous_prefix)

    def _previous_flight_text_is_right_aligned():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        expected_line1 = "%s from %s" % (TEST_PREVIOUS_FLIGHT["callsign"], TEST_PREVIOUS_ROUTE["origin_city"])
        anchors = [anchor for t, _xy, anchor in spy.calls if t == expected_line1]
        if not anchors:
            return False, "did not capture the previous-flight line 1 draw call"
        if anchors[0] != "ra":
            return False, "previous-flight text anchor is %r, expected 'ra' (right-aligned, D-26)" % (anchors[0],)
        return True, ""
    check("the previous flight's text block is drawn right-aligned (anchor='ra', D-26)", _previous_flight_text_is_right_aligned)

    # 23. No previous_flight supplied -> no previous-flight text at all
    # (the card is simply omitted, not drawn empty/placeholder).
    def _no_previous_flight_omits_the_card():
        single = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        two_flight = render.render_panel(
            TEST_FLIGHT, "departing", route=TEST_ROUTE,
            previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
        )
        if single == two_flight:
            return False, "a render with no previous_flight is byte-identical to one with a previous flight supplied - the card is not actually optional"
        return True, ""
    check("omitting previous_flight/previous_route renders a genuinely different (single-flight) panel", _no_previous_flight_omits_the_card)

    # 24. PT Serif Regular (D-27) is the active weight for every active-state
    # text role; the empty state's heading keeps a Bold weight.
    def _pt_serif_regular_is_the_active_weight():
        active_roles = ("STATE_LABEL_FONT", "TOP_TAG_FONT", "MAIN_LINE1_FONT", "MAIN_LINE2_FONT", "PREVIOUS_LINE1_FONT", "PREVIOUS_LINE2_FONT")
        for name in active_roles:
            if not hasattr(render, name):
                return False, "server.plane.render has no %s role constant" % name
            path, _size, _weight = getattr(render, name)
            if not path.endswith("PTSerif-Regular.ttf"):
                return False, "%s font path %r is not PTSerif-Regular.ttf (D-27)" % (name, path)
        if not render.EMPTY_HEADING_FONT[0].endswith("PTSerif-Bold.ttf"):
            return False, "EMPTY_HEADING_FONT font path %r is not PTSerif-Bold.ttf" % (render.EMPTY_HEADING_FONT[0],)
        return True, ""
    check("every active-state text role uses PTSerif-Regular.ttf (D-27); the empty-state heading keeps PTSerif-Bold.ttf", _pt_serif_regular_is_the_active_weight)

    # 25. A genuinely long real destination/origin city+airline name
    # shrinks via fit_text_size() rather than breaching the canvas or
    # raising, and is still drawn in full (not truncated).
    def _long_name_stress_case_shrinks_without_crashing():
        try:
            with _TextSpy(render) as spy:
                render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_LONG_ROUTE)
        except AssertionError as exc:
            return False, "long-name render raised an assertion: %r" % (exc,)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s from %s" % (TEST_FLIGHT["callsign"], TEST_LONG_ROUTE["origin_city"])
        if expected_line1 not in texts:
            return False, "long origin-city line %r was not drawn in full (found %r) - the shrink path must fit the text, not truncate it" % (expected_line1, texts)
        return True, ""
    check(
        "a genuinely long destination/origin city name (Santiago de Compostela) shrinks via fit_text_size() without crashing, drawn in full",
        _long_name_stress_case_shrinks_without_crashing,
    )

    # 26. An unlabelled designator renders the airline name alone.
    def _unlabelled_type_renders_airline_alone():
        result = render._flight_line2_text({"airline_name": "Air France"}, "ZZZZ")
        if result != "Air France":
            return False, "expected 'Air France' for an unlabelled designator, got %r" % (result,)
        return True, ""
    check(
        "_flight_line2_text() renders the airline name alone for an unlabelled (unrecognized) type designator",
        _unlabelled_type_renders_airline_alone,
    )

    # 27. A None type renders the airline name alone.
    def _none_type_renders_airline_alone():
        result = render._flight_line2_text({"airline_name": "Air France"}, None)
        if result != "Air France":
            return False, "expected 'Air France' for aircraft_type=None, got %r" % (result,)
        return True, ""
    check("_flight_line2_text() renders the airline name alone for aircraft_type=None", _none_type_renders_airline_alone)

    # 28. The one-argument call (aircraft_type omitted entirely) renders the
    # airline name alone.
    def _one_argument_call_renders_airline_alone():
        result = render._flight_line2_text({"airline_name": "Air France"})
        if result != "Air France":
            return False, "expected 'Air France' for the one-argument call, got %r" % (result,)
        return True, ""
    check("_flight_line2_text() renders the airline name alone when aircraft_type is omitted entirely", _one_argument_call_renders_airline_alone)

    # 29. The P-01 display alias: the one carrier with a display alias
    # renders under its current public brand while a non-aliased airline
    # is returned unchanged, and the alias never touches selection.
    def _display_airline_name_applies_the_p01_alias_only_where_defined():
        if render.display_airline_name("CCM Airlines") != "Air Corsica":
            return False, "display_airline_name('CCM Airlines') did not return the P-01 alias 'Air Corsica'"
        if render.display_airline_name("Air France") != "Air France":
            return False, "display_airline_name('Air France') should return the input unchanged (no alias)"
        aliased_line2 = render._flight_line2_text({"airline_name": "CCM Airlines"}, "AT72")
        if "Air Corsica" not in aliased_line2 or "CCM Airlines" in aliased_line2:
            return False, "_flight_line2_text() with the CCM Airlines route did not render the P-01 alias: %r" % (aliased_line2,)
        return True, ""
    check(
        "the P-01 presentation-only airline alias renders the current brand name; a non-aliased airline is unchanged",
        _display_airline_name_applies_the_p01_alias_only_where_defined,
    )

    # 30. Never-raises battery: malformed routes crossed with hostile
    # aircraft types must never raise, and the result is always a string.
    def _flight_line2_text_never_raises_for_hostile_inputs():
        malformed_routes = (None, {}, "not-a-dict", 42, ["a", "list"], {"airline_name": 12345})
        hostile_types = (None, "", "   ", "../../etc/passwd", "..\\..\\windows", 999, ["x"], "z" * 500)
        for route in malformed_routes:
            for aircraft_type in hostile_types:
                try:
                    result = render._flight_line2_text(route, aircraft_type)
                except Exception as exc:
                    return False, "_flight_line2_text(%r, %r) raised %r" % (route, aircraft_type, exc)
                if not isinstance(result, str):
                    return False, "_flight_line2_text(%r, %r) returned non-string %r" % (route, aircraft_type, result)
        return True, ""
    check(
        "_flight_line2_text() never raises across a battery of malformed routes x hostile aircraft types, and always returns a string",
        _flight_line2_text_never_raises_for_hostile_inputs,
    )

    # 31. TEST_LONG_ROUTE combined with the longest known type label still
    # fits without tripping _assert_within_canvas - the composed line 2 is
    # strictly longer than today's, exercising fit_text_size()'s shrink path.
    def _long_name_plus_longest_label_fits_within_canvas():
        longest_type, longest_label = max(render._TYPE_DISPLAY_LABELS.items(), key=lambda kv: len(kv[1]))
        long_flight = dict(TEST_FLIGHT, aircraft_type=longest_type)
        try:
            render.build_canvas(long_flight, "arriving", route=TEST_LONG_ROUTE)
        except AssertionError as exc:
            return False, "long airline name + longest type label (%r) raised an assertion: %r" % (longest_label, exc)
        return True, ""
    check(
        "the longest real airline name combined with the longest type label still renders without tripping _assert_within_canvas",
        _long_name_plus_longest_label_fits_within_canvas,
    )

    # 32. Rendering a main flight carrying a type calls select_illustration()
    # with that exact type as the second argument.
    def _select_illustration_receives_main_flights_type():
        with _SelectIllustrationSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        if not spy.calls:
            return False, "no select_illustration() call captured"
        main_route, main_type = spy.calls[0]
        if main_type != TEST_FLIGHT["aircraft_type"]:
            return False, "main-card select_illustration() call got aircraft_type=%r, expected %r" % (main_type, TEST_FLIGHT["aircraft_type"])
        if main_route != TEST_ROUTE:
            return False, "main-card select_illustration() call got route=%r, expected TEST_ROUTE" % (main_route,)
        return True, ""
    check(
        "rendering with a main flight carrying a type calls select_illustration() with that exact type",
        _select_illustration_receives_main_flights_type,
    )

    # 33. A main + previous flight makes two select_illustration() calls,
    # each receiving its own flight's type - the previous card must never
    # receive the main flight's type (the specific bug this threading can
    # introduce).
    def _select_illustration_calls_each_receive_their_own_flights_type():
        with _SelectIllustrationSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        if len(spy.calls) != 2:
            return False, "expected exactly 2 select_illustration() calls (main + previous), got %d: %r" % (len(spy.calls), spy.calls)
        (main_route, main_type), (prev_route, prev_type) = spy.calls
        if main_type != TEST_FLIGHT["aircraft_type"]:
            return False, "main-card call got aircraft_type=%r, expected %r" % (main_type, TEST_FLIGHT["aircraft_type"])
        if prev_type != TEST_PREVIOUS_FLIGHT["aircraft_type"]:
            return False, "previous-card call got aircraft_type=%r, expected %r" % (prev_type, TEST_PREVIOUS_FLIGHT["aircraft_type"])
        if prev_type == main_type and TEST_FLIGHT["aircraft_type"] != TEST_PREVIOUS_FLIGHT["aircraft_type"]:
            return False, "previous-card call received the main flight's type - card-type crossover bug"
        if main_route != TEST_ROUTE or prev_route != TEST_PREVIOUS_ROUTE:
            return False, "select_illustration() calls got the wrong route pairing: %r" % (spy.calls,)
        return True, ""
    check(
        "a main + previous flight makes two select_illustration() calls, each receiving its own flight's type (no crossover)",
        _select_illustration_calls_each_receive_their_own_flights_type,
    )

    # 34. previous_flight=None still completes without raising, and the
    # previous-card lookup (if made at all) never receives a non-None type
    # derived from a None flight.
    def _no_previous_flight_never_raises_and_never_crosses_over():
        try:
            with _SelectIllustrationSpy(render) as spy:
                render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, previous_flight=None)
        except Exception as exc:
            return False, "build_canvas() with previous_flight=None raised %r" % (exc,)
        # Only the main-card call is expected (no previous_flight means no
        # previous card at all, per _build_active_canvas()'s own guard) -
        # but the real assertion is simply that nothing raised, and that if
        # a second call somehow occurred, it did not fabricate a type.
        for _route, aircraft_type in spy.calls[1:]:
            if aircraft_type not in (None, TEST_FLIGHT["aircraft_type"]):
                return False, "a previous-card call with no previous_flight got an unexpected aircraft_type=%r" % (aircraft_type,)
        return True, ""
    check(
        "previous_flight=None still completes without raising and never fabricates a type for the omitted previous card",
        _no_previous_flight_never_raises_and_never_crosses_over,
    )

    # 35. No text-outline arguments anywhere in the source (still a real
    # regression guard: Pillow's stroke_width/stroke_fill leak illegal
    # anti-aliased indices through blended stroke edges).
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

    # 36. A corrupt (byte-garbage) illustration file degrades to the
    # generic fallback instead of raising out of render_panel() -
    # 03-VERIFICATION.md gap #1 / T-03-04-01.
    def _corrupt_illustration_degrades_to_generic_fallback():
        garbage_path = _write_garbage_png()
        try:
            with _forced_illustration(render, garbage_path):
                garbage_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
            with _forced_illustration(render, illustrations.generic_fallback_path()):
                fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        finally:
            os.unlink(garbage_path)
        if len(garbage_buf) != panel_format.IMAGE_BYTES:
            return False, "corrupt-illustration render is %d bytes, expected %d" % (len(garbage_buf), panel_format.IMAGE_BYTES)
        if garbage_buf != fallback_buf:
            return False, "a corrupt illustration file did not degrade to a byte-identical generic-fallback panel"
        return True, ""
    check(
        "a corrupt (byte-garbage) illustration file degrades to the generic fallback instead of raising out of render_panel()",
        _corrupt_illustration_degrades_to_generic_fallback,
    )

    # 37. An oversized illustration is rejected on its PNG header, before
    # any pixel data is decoded - 03-VERIFICATION.md gap #2 / T-03-04-02.
    def _oversized_illustration_rejected_on_header():
        oversized_path = _write_oversized_png()
        try:
            with Image.open(oversized_path) as probe:
                pixel_count = probe.size[0] * probe.size[1]
            if pixel_count <= illustrations.ILLUSTRATION_MAX_PIXELS:
                return False, (
                    "fixture pixel count %d does not exceed ILLUSTRATION_MAX_PIXELS %d - "
                    "fixture is not actually oversized" % (pixel_count, illustrations.ILLUSTRATION_MAX_PIXELS)
                )
            with _forced_illustration(render, oversized_path):
                oversized_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
            with _forced_illustration(render, illustrations.generic_fallback_path()):
                fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        finally:
            os.unlink(oversized_path)
        if len(oversized_buf) != panel_format.IMAGE_BYTES:
            return False, "oversized-illustration render is %d bytes, expected %d" % (len(oversized_buf), panel_format.IMAGE_BYTES)
        if oversized_buf != fallback_buf:
            return False, "an oversized illustration file did not degrade to a byte-identical generic-fallback panel"
        return True, ""
    check(
        "an oversized illustration is rejected on its PNG header, before any pixel data is decoded",
        _oversized_illustration_rejected_on_header,
    )

    # 38. When the selected illustration and the generic fallback are both
    # undecodable, the render skips the illustration entirely and still
    # returns a valid panel - the tail of the degradation ladder.
    def _both_illustration_and_fallback_undecodable_still_renders():
        garbage_path = _write_garbage_png()
        try:
            with _forced_illustration(render, garbage_path, fallback_path=garbage_path):
                both_bad_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
            with _forced_illustration(render, illustrations.generic_fallback_path()):
                fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        finally:
            os.unlink(garbage_path)
        if len(both_bad_buf) != panel_format.IMAGE_BYTES:
            return False, (
                "render with both illustration and fallback undecodable is %d bytes, expected %d"
                % (len(both_bad_buf), panel_format.IMAGE_BYTES)
            )
        if both_bad_buf == fallback_buf:
            return False, (
                "render with both illustration and fallback undecodable is byte-identical to the "
                "fallback-forced render - the illustration was not actually skipped"
            )
        return True, ""
    check(
        "when the selected illustration and the generic fallback are both undecodable, the render skips the illustration and still returns a valid panel",
        _both_illustration_and_fallback_undecodable_still_renders,
    )

    # --- Quick task 260827-hyy: D-06's intermediate render state - an
    # airline-only route (adsbdb missed, the callsign's ICAO prefix
    # resolved the carrier) still shows the airline name and the airline's
    # own illustration; the destination stays genuinely unknown. ------------

    # 39. EJU84YF (a confirmed adsbdb miss, easyJet Europe): line 1 is the
    # bare callsign (no to/from clause, no city - genuinely unknown), line 2
    # is the resolved airline name alone (no aircraft_type supplied), and
    # ROUTE_FALLBACK_TEXT does not appear anywhere - D-06's middle row is
    # not the same as a full miss.
    def _airline_only_route_shows_airline_not_fallback_text():
        import server.plane.enrich as enrich

        airline_only_flight = {"hex": "440cb1", "callsign": "EJU84YF"}
        airline_only_route = enrich.airline_only_route("easyJet")
        with _TextSpy(render) as spy:
            render.build_canvas(airline_only_flight, "departing", route=airline_only_route)
        texts = [t for t, _xy, _anchor in spy.calls]
        if "EJU84YF" not in texts:
            return False, "expected the bare callsign 'EJU84YF' among the text draws, got %r" % (texts,)
        if "easyJet" not in texts:
            return False, "expected the resolved airline name 'easyJet' among the text draws, got %r" % (texts,)
        if render.ROUTE_FALLBACK_TEXT in texts:
            return False, "ROUTE_FALLBACK_TEXT must not appear when the airline is known (D-06), got %r" % (texts,)
        return True, ""
    check(
        "an airline-only route (adsbdb miss, prefix-resolved 'easyJet') draws the bare callsign and the airline "
        "name, never ROUTE_FALLBACK_TEXT (D-06 quick task 260827-hyy)",
        _airline_only_route_shows_airline_not_fallback_text,
    )

    # 40. Transavia France + B738: line 2 composes exactly like a full hit
    # ("{airline} · {type label}"), while line 1 stays the bare callsign -
    # no to/from clause, no city fabricated from the prefix.
    def _airline_only_route_composes_line2_like_a_full_hit():
        import server.plane.enrich as enrich

        flight = {"hex": "39de4a", "callsign": "TVF12ZW", "aircraft_type": "B738"}
        airline_only_route = enrich.airline_only_route("Transavia France")
        with _TextSpy(render) as spy:
            render.build_canvas(flight, "departing", route=airline_only_route)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line2 = "Transavia France · %s" % render._TYPE_DISPLAY_LABELS["B738"]
        if expected_line2 not in texts:
            return False, "expected main line 2 %r among the text draws, got %r" % (expected_line2, texts)
        if "TVF12ZW" not in texts:
            return False, "expected the bare callsign 'TVF12ZW' (no to/from clause, no city) among the text draws, got %r" % (texts,)
        for text in texts:
            if " to " in text or " from " in text:
                return False, "found a to/from clause %r - the destination must stay genuinely unknown (D-06)" % (text,)
        return True, ""
    check(
        "an airline-only Transavia France + B738 route composes line 2 as '{airline} · {type label}' exactly like a "
        "full hit, while line 1 stays the bare callsign with no to/from clause or city (D-06)",
        _airline_only_route_composes_line2_like_a_full_hit,
    )

    # 41. This is the check that proves the todo's actual goal: the
    # airline-only route resolves to the airline's own illustration, not the
    # generic fallback.
    def _airline_only_route_selects_the_airlines_own_illustration():
        import server.plane.enrich as enrich

        airline_only_route = enrich.airline_only_route("Transavia France")
        path = illustrations.select_illustration(airline_only_route, "B738")
        if path is None or os.path.basename(path) != "transavia-france.png":
            return False, "expected the airline's own illustration 'transavia-france.png', got %r" % (path,)
        return True, ""
    check(
        "illustrations.select_illustration() on an airline-only Transavia France route resolves to "
        "'transavia-france.png' - the airline's own art, not the generic fallback",
        _airline_only_route_selects_the_airlines_own_illustration,
    )

    # 42 (quick task 260827-kih). A route already corrected by
    # enrich.correct_airline_name() renders its current brand name in the
    # caption via _flight_line2_text(), and render.display_airline_name()
    # is a no-op on that already-corrected string (it has no P-01 alias of
    # its own to apply - the alias table only ever held "CCM Airlines").
    def _corrected_route_renders_current_brand_and_display_alias_is_noop():
        import server.plane.enrich as enrich

        cache = {}
        body = {
            "response": {
                "flightroute": {
                    "airline": {"name": "CCM Airlines"},
                    "origin": {"iata_code": "ORY", "municipality": "Paris"},
                    "destination": {"iata_code": "AJA", "municipality": "Ajaccio"},
                }
            }
        }

        def _transport(_callsign, _timeout=None):
            return 200, body

        route, _source = enrich.resolve_route("CCM21AW", cache, transport=_transport)
        if route is None or route.get("airline_name") != "Air Corsica":
            return False, "setup failure: expected a corrected 'Air Corsica' route, got %r" % (route,)
        if render.display_airline_name(route["airline_name"]) != "Air Corsica":
            return False, "display_airline_name() must be a no-op on the already-corrected 'Air Corsica' string"
        line2 = render._flight_line2_text(route, "A320")
        if "Air Corsica" not in line2:
            return False, "_flight_line2_text() on the corrected route did not render the current brand name: %r" % (line2,)
        if "CCM Airlines" in line2:
            return False, "_flight_line2_text() on the corrected route must not render the stale upstream string: %r" % (line2,)
        return True, ""
    check(
        "a route already corrected by enrich.correct_airline_name() renders its current brand name via "
        "_flight_line2_text(), and display_airline_name() is a no-op on the already-corrected string (260827-kih)",
        _corrected_route_renders_current_brand_and_display_alias_is_noop,
    )

    # --- Task 1 (05-02, DEVICE-04): bottom-left battery-low icon -------------
    # BATTERY_ICON_BOX is computed from render's own constants (not restated
    # as a hand-written literal) exactly the way draw_battery_icon() derives
    # its own total bounding box - so this containment window can never go
    # stale relative to the BATTERY_ICON_* constants again. Check D below is
    # the one place that still pins the literal geometry values.

    BATTERY_ICON_BOX = (
        render.BATTERY_ICON_LEFT,
        render.BATTERY_ICON_BOTTOM - render.BATTERY_ICON_BODY_H,
        render.BATTERY_ICON_LEFT + render.BATTERY_ICON_BODY_W + render.BATTERY_ICON_NUB_W,
        render.BATTERY_ICON_BOTTOM,
    )

    def _states_for_battery_checks():
        """(state, flight, kwargs) triples exercising all three render
        states - departing/arriving carry a real previous-flight card
        (TEST_PREVIOUS_FLIGHT/TEST_PREVIOUS_ROUTE), per Task 1 Check B's
        instruction that a real previous-flight card be on the canvas.
        """
        return [
            ("departing", TEST_FLIGHT, dict(
                route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                previous_state="arriving",
            )),
            ("arriving", TEST_FLIGHT, dict(
                route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                previous_state="departing",
            )),
            ("empty", None, {}),
        ]

    def _diff_inside_outside(canvas_a, canvas_b, box):
        """Return (inside, outside) bools: whether canvas_a and canvas_b
        differ at at least one pixel inside `box` and at at least one pixel
        outside it. `box` is treated with Pillow's own inclusive-corner
        rectangle convention (matching draw_frame()'s/draw_battery_icon()'s
        (left, top, right, bottom) - the drawn footprint spans left..right
        and top..bottom INCLUSIVE, so containment here is `<=` on both
        ends, not the exclusive `<` a half-open crop box would use.
        Row-sliced byte comparison (fast C-level bytes equality per row) so
        only rows that actually differ ever pay for a per-column Python
        loop - the 1200x1600 canvas is never scanned pixel-by-pixel in the
        common (near-identical) case.
        """
        left, top, right, bottom = box
        width, height = canvas_a.size
        bytes_a = canvas_a.tobytes()
        bytes_b = canvas_b.tobytes()
        inside = False
        outside = False
        for row in range(height):
            start = row * width
            end = start + width
            row_a = bytes_a[start:end]
            row_b = bytes_b[start:end]
            if row_a == row_b:
                continue
            in_row_band = top <= row <= bottom
            for col in range(width):
                if row_a[col] != row_b[col]:
                    if in_row_band and left <= col <= right:
                        inside = True
                    else:
                        outside = True
        return inside, outside

    # 43. Check A - default-off and no regression: no battery kwarg and
    # battery_low=False produce pixel-identical canvases for all three
    # states (no pixel anywhere on the 1200x1600 canvas differs).
    def _battery_default_off_matches_explicit_false():
        for state, flight, kwargs in _states_for_battery_checks():
            no_kw = render.build_canvas(flight, state, **kwargs)
            explicit_false = render.build_canvas(flight, state, battery_low=False, **kwargs)
            if no_kw.tobytes() != explicit_false.tobytes():
                return False, "state=%r: build_canvas() with no battery kwarg differs from battery_low=False" % (state,)
        return True, ""
    check(
        "build_canvas() with no battery kwarg is pixel-identical to battery_low=False for departing/arriving/empty (default-off, no regression)",
        _battery_default_off_matches_explicit_false,
    )

    # 44. Check B - conditional draw is spatially contained: battery_low=True
    # vs battery_low=False differ at >=1 pixel inside the icon bbox and 0
    # pixels outside it, for all three states.
    def _battery_icon_conditional_draw_is_spatially_contained():
        for state, flight, kwargs in _states_for_battery_checks():
            off = render.build_canvas(flight, state, battery_low=False, **kwargs)
            on = render.build_canvas(flight, state, battery_low=True, **kwargs)
            inside, outside = _diff_inside_outside(off, on, BATTERY_ICON_BOX)
            if not inside:
                return False, "state=%r: battery_low=True produced no pixel difference inside the icon box %r" % (state, BATTERY_ICON_BOX)
            if outside:
                return False, "state=%r: battery_low=True changed a pixel outside the icon box %r" % (state, BATTERY_ICON_BOX)
        return True, ""
    check(
        "battery_low=True differs from battery_low=False only inside the icon bounding box (64,1514,115,1536), for "
        "departing/arriving (with a real previous-flight card on the canvas) and empty",
        _battery_icon_conditional_draw_is_spatially_contained,
    )

    # 45. Check C - per-state ink and hollow interior: the body outline
    # corner, the left-aligned fill interior, and the solid nub all read as
    # the state's own ink; the body interior right of the fill still reads
    # as the state's background - the glyph must read as mostly empty.
    def _battery_icon_ink_and_hollow_interior():
        expectations = [
            ("departing", TEST_FLIGHT, dict(route=TEST_ROUTE), render.STATE_INK["departing"], render.STATE_BACKGROUND["departing"]),
            ("arriving", TEST_FLIGHT, dict(route=TEST_ROUTE), render.STATE_INK["arriving"], render.STATE_BACKGROUND["arriving"]),
            ("empty", None, {}, render.EMPTY_INK, IDX_WHITE),
        ]
        for state, flight, kwargs, ink_idx, bg_idx in expectations:
            canvas = render.build_canvas(flight, state, battery_low=True, **kwargs)
            corner = canvas.getpixel((64, 1514))
            fill_interior = canvas.getpixel((70, 1525))
            nub = canvas.getpixel((112, 1524))
            gap = canvas.getpixel((95, 1525))
            if corner != ink_idx:
                return False, "state=%r: body outline corner (64,1514) is %r, expected ink %r" % (state, corner, ink_idx)
            if fill_interior != ink_idx:
                return False, "state=%r: fill-interior pixel (70,1525) is %r, expected ink %r" % (state, fill_interior, ink_idx)
            if nub != ink_idx:
                return False, "state=%r: nub pixel (112,1524) is %r, expected ink %r" % (state, nub, ink_idx)
            if gap != bg_idx:
                return False, "state=%r: pixel (95,1525) inside the body outline but right of the fill is %r, expected background %r" % (state, gap, bg_idx)
        return True, ""
    check(
        "with battery_low=True, the body outline corner/fill/nub read as the state's own ink (EMPTY_INK for the "
        "empty state), while the hollow interior right of the fill still reads as the state's background",
        _battery_icon_ink_and_hollow_interior,
    )

    # 46. Check D - size constants derive from a uniform 0.7 reduction of the
    # spacing scale (260828-0qo, live on-glass correction), the two position
    # constants are unchanged, the stroke never drops below the frame's own
    # weight, the nub is centred to within one pixel (the odd BODY_H-NUB_H
    # leftover puts it one pixel low, not a defect), and the total bounding
    # box is exactly (64, 1514, 115, 1536).
    def _battery_icon_geometry_derives_from_spacing_scale():
        if render.BATTERY_ICON_BODY_W != round(render.SPACE_LG * 0.7):
            return False, "BATTERY_ICON_BODY_W is not round(SPACE_LG * 0.7)"
        if render.BATTERY_ICON_BODY_H != round(render.SPACE_MD * 0.7):
            return False, "BATTERY_ICON_BODY_H is not round(SPACE_MD * 0.7)"
        if render.BATTERY_ICON_NUB_W != round(render.SPACE_XS * 0.7):
            return False, "BATTERY_ICON_NUB_W is not round(SPACE_XS * 0.7)"
        if render.BATTERY_ICON_NUB_H != round(render.SPACE_SM * 0.7):
            return False, "BATTERY_ICON_NUB_H is not round(SPACE_SM * 0.7)"
        if render.BATTERY_ICON_STROKE_PX != 2:
            return False, "BATTERY_ICON_STROKE_PX != 2"
        if render.BATTERY_ICON_STROKE_PX < render.FRAME_STROKE_PX:
            return False, "BATTERY_ICON_STROKE_PX dropped below FRAME_STROKE_PX, the legibility floor"
        if render.BATTERY_ICON_LEFT is not render.MARGIN:
            return False, "BATTERY_ICON_LEFT is not MARGIN"
        if render.BATTERY_ICON_BOTTOM != render.HEIGHT - render.MARGIN:
            return False, "BATTERY_ICON_BOTTOM != HEIGHT - MARGIN"
        body_top = render.BATTERY_ICON_BOTTOM - render.BATTERY_ICON_BODY_H
        nub_top = body_top + (render.BATTERY_ICON_BODY_H - render.BATTERY_ICON_NUB_H) // 2
        nub_bottom = nub_top + render.BATTERY_ICON_NUB_H
        gap_above = nub_top - body_top
        gap_below = render.BATTERY_ICON_BOTTOM - nub_bottom
        if gap_above < 0 or gap_below < 0 or (gap_below - gap_above) not in (0, 1):
            return False, "nub is not centred to within one pixel: gap_above=%r gap_below=%r" % (gap_above, gap_below)
        total = (
            render.BATTERY_ICON_LEFT, body_top,
            render.BATTERY_ICON_LEFT + render.BATTERY_ICON_BODY_W + render.BATTERY_ICON_NUB_W,
            render.BATTERY_ICON_BOTTOM,
        )
        if total != (64, 1514, 115, 1536):
            return False, "computed total bounding box %r != (64, 1514, 115, 1536)" % (total,)
        return True, ""
    check(
        "battery icon size constants are a uniform round(original * 0.7) reduction of the former spacing-scale "
        "values (260828-0qo on-glass correction) with the stroke never dropping below FRAME_STROKE_PX, position "
        "constants (BATTERY_ICON_LEFT/BOTTOM) unchanged, the nub centred to within one pixel, and a total "
        "bounding box of (64,1514,115,1536)",
        _battery_icon_geometry_derives_from_spacing_scale,
    )

    # --- Plan 06-06: CFG-01 theme, CFG-12 runway, CFG-05 source-fault badge ---

    # 47. render_panel() with no theme_id is byte-identical to an explicit
    # default theme_id - the default path is genuinely unchanged.
    def _theme_default_matches_no_theme_arg():
        a = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        b = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=render.device_config.DEFAULT_THEME_ID)
        if a != b:
            return False, "render_panel() with no theme_id differs from an explicit default theme_id - CFG-01's default path must be byte-identical"
        return True, ""
    check("render_panel() with no theme_id is byte-identical to an explicit default theme_id (CFG-01)", _theme_default_matches_no_theme_arg)

    # 48. build_canvas(theme_id="sky") and build_canvas() with no theme
    # produce identical canvases.
    def _sky_theme_canvas_matches_default():
        a = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        b = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="sky")
        if list(a.getdata()) != list(b.getdata()):
            return False, "build_canvas(theme_id='sky') differs from build_canvas() with no theme_id"
        return True, ""
    check("build_canvas(theme_id='sky') and build_canvas() with no theme produce identical canvases", _sky_theme_canvas_matches_default)

    # 49. An unrecognised theme id degrades to the default theme's canvas
    # rather than raising - an unknown theme is forgiving.
    def _unknown_theme_degrades_to_default_canvas():
        default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        try:
            unknown_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="not-a-theme")
        except Exception as exc:
            return False, "build_canvas(theme_id='not-a-theme') raised %r - an unknown theme must degrade to the default" % (exc,)
        if list(default_canvas.getdata()) != list(unknown_canvas.getdata()):
            return False, "build_canvas(theme_id='not-a-theme') produced a canvas different from the default theme's"
        return True, ""
    check("build_canvas(theme_id='not-a-theme') produces the default theme's canvas rather than raising", _unknown_theme_degrades_to_default_canvas)

    # 50. An unrecognised state still raises ValueError naming all three
    # legal states - an unknown state is a real caller-bug detector and
    # must stay loud even though an unknown theme is forgiving.
    def _unknown_state_still_raises_naming_all_three_states():
        try:
            render.build_canvas(TEST_FLIGHT, "sideways")
        except ValueError as exc:
            message = str(exc)
            for word in ("departing", "arriving", "empty"):
                if word not in message:
                    return False, "ValueError message %r does not name %r" % (message, word)
            return True, ""
        except Exception as exc:
            return False, "build_canvas(flight, 'sideways') raised %r, expected ValueError" % (exc,)
        return False, "build_canvas(flight, 'sideways') did not raise - an unknown state must stay loud"
    check("build_canvas(flight, 'nonsense-state') still raises ValueError naming departing/arriving/empty", _unknown_state_still_raises_naming_all_three_states)

    # 51. _assert_legal_palette() (run internally by build_canvas()) still
    # passes for every registered theme.
    def _legal_palette_holds_for_every_theme():
        for theme_id in render.device_config.THEME_IDS:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
        return True, ""
    check("_assert_legal_palette() (run internally by build_canvas()) passes for every registered theme", _legal_palette_holds_for_every_theme)

    # 52. runway_tag_text() with no argument returns exactly the current
    # top-right tag string - the default render is unchanged.
    def _runway_tag_text_default_matches_top_right_tag():
        if render.runway_tag_text() != render.TOP_RIGHT_TAG_TEXT:
            return False, "runway_tag_text() != render.TOP_RIGHT_TAG_TEXT"
        return True, ""
    check("runway_tag_text() with no argument returns exactly TOP_RIGHT_TAG_TEXT (default render unchanged)", _runway_tag_text_default_matches_top_right_tag)

    # 53. runway_tag_text("06-24")/("02-20") return the strings from the
    # runway registry.
    def _runway_tag_text_matches_registry_for_other_runways():
        for runway_id in ("06-24", "02-20"):
            expected = render.device_config.runway_tag_text(runway_id)
            got = render.runway_tag_text(runway_id)
            if got != expected:
                return False, "runway_tag_text(%r) = %r, expected %r" % (runway_id, got, expected)
        return True, ""
    check("runway_tag_text('06-24')/('02-20') return the strings from device_config.RUNWAYS", _runway_tag_text_matches_registry_for_other_runways)

    # 54. An unrecognised runway id degrades to the default runway's tag
    # rather than raising.
    def _runway_tag_text_unknown_id_degrades_to_default():
        if render.runway_tag_text("nope") != render.runway_tag_text():
            return False, "runway_tag_text('nope') != runway_tag_text() - an unknown runway id must degrade to the default"
        return True, ""
    check("runway_tag_text('unknown') returns the default runway's tag rather than raising", _runway_tag_text_unknown_id_degrades_to_default)

    # 55. build_canvas(None, "empty", runway_id=...) draws that runway's
    # heading - including the longest of the three registry headings - and
    # still passes the safe-box assertion (fit_text_size() shrink path).
    def _empty_canvas_draws_selected_runways_heading():
        longest_runway_id = max(
            render.device_config.RUNWAY_IDS, key=lambda rid: len(render.device_config.runway_empty_heading(rid))
        )
        with _TextSpy(render) as spy:
            render.build_canvas(None, "empty", runway_id=longest_runway_id)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected = render.empty_heading_text(longest_runway_id)
        if expected not in texts:
            return False, "expected the longest runway heading %r among the text draws, got %r" % (expected, texts)
        return True, ""
    check(
        "build_canvas(None, 'empty', runway_id=...) draws that runway's heading, including the longest of the "
        "three, and passes the safe-box assertion",
        _empty_canvas_draws_selected_runways_heading,
    )

    # 56. build_canvas(flight, "departing", runway_id="06-24") draws that
    # runway's tag, still passing the within-canvas assertion.
    def _active_canvas_draws_selected_runways_tag():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, runway_id="06-24")
        texts = [t for t, _xy, _anchor in spy.calls]
        expected = render.runway_tag_text("06-24")
        if expected not in texts:
            return False, "expected the runway 06-24 tag %r among the text draws, got %r" % (expected, texts)
        return True, ""
    check(
        "build_canvas(flight, 'departing', runway_id='06-24') draws that runway's tag, passing the "
        "within-canvas assertion",
        _active_canvas_draws_selected_runways_tag,
    )

    # 57. render_panel(..., source_fault=False) is byte-identical to the
    # same call without the argument.
    def _source_fault_false_matches_default():
        a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
        if a != b:
            return False, "render_panel(source_fault=False) differs from the default call"
        return True, ""
    check("render_panel(..., source_fault=False) is byte-identical to the same call without the argument", _source_fault_false_matches_default)

    # 58. render_panel(..., source_fault=True) differs from the same call
    # with the flag false - the badge is genuinely drawn.
    def _source_fault_true_differs_from_false():
        a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
        b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=True)
        if a == b:
            return False, "render_panel(source_fault=True) is byte-identical to source_fault=False - the badge is not actually drawn"
        return True, ""
    check("render_panel(..., source_fault=True) differs from the same call with the flag false", _source_fault_true_differs_from_false)

    # 59. The fault badge is drawn on the active canvas and on the empty
    # canvas alike - visible whichever state the panel is in.
    def _badge_caption_present_on_active_and_empty_canvases():
        with _TextSpy(render) as spy_active:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True)
        with _TextSpy(render) as spy_empty:
            render.build_canvas(None, "empty", source_fault=True)
        active_texts = [t for t, _xy, _anchor in spy_active.calls]
        empty_texts = [t for t, _xy, _anchor in spy_empty.calls]
        if render.SOURCE_FAULT_TEXT not in active_texts:
            return False, "SOURCE_FAULT_TEXT missing from the active-state text draws with source_fault=True"
        if render.SOURCE_FAULT_TEXT not in empty_texts:
            return False, "SOURCE_FAULT_TEXT missing from the empty-state text draws with source_fault=True"
        return True, ""
    check(
        "the source-fault badge is drawn on both the active canvas and the empty canvas (visible in every state)",
        _badge_caption_present_on_active_and_empty_canvases,
    )

    # 60. The badge caption is absent from a normal render (source_fault
    # defaults to False) - same text-draw spy idiom already used for the
    # top-right tag.
    def _badge_caption_absent_from_a_normal_render():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        if render.SOURCE_FAULT_TEXT in texts:
            return False, "SOURCE_FAULT_TEXT appeared in a normal render with no source_fault flag"
        return True, ""
    check("the badge caption text is absent from a normal render (source_fault defaults to False)", _badge_caption_absent_from_a_normal_render)

    # 61. _assert_legal_palette() (run internally by build_canvas()) still
    # passes with the badge drawn, in both active states, the empty state,
    # and every theme.
    def _legal_palette_holds_with_badge_across_states_and_themes():
        for theme_id in render.device_config.THEME_IDS:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True, theme_id=theme_id)
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=True, theme_id=theme_id)
        render.build_canvas(None, "empty", source_fault=True)
        return True, ""
    check(
        "_assert_legal_palette() (run internally by build_canvas()) passes with the badge drawn, in both active "
        "states, the empty state, and every theme",
        _legal_palette_holds_with_badge_across_states_and_themes,
    )

    # 62. A fault-badged departing render still satisfies
    # _assert_legal_palette() for the default theme - proven by calling
    # build_canvas() (which runs the assertion internally), not by
    # re-implementing it.
    def _fault_badged_departing_render_satisfies_legal_palette_via_build_canvas():
        render.build_canvas(
            TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True, theme_id=render.device_config.DEFAULT_THEME_ID
        )
        return True, ""
    check(
        "a fault-badged departing render still satisfies _assert_legal_palette() for the default theme "
        "(proven via build_canvas(), not a re-implementation)",
        _fault_badged_departing_render_satisfies_legal_palette_via_build_canvas,
    )

    # 63. The badge's bounding box stays inside the drawn frame.
    def _badge_bbox_stays_inside_the_drawn_frame():
        canvas = panel_format.new_canvas(IDX_BLUE)
        frame_box = render.draw_frame(canvas, IDX_WHITE)
        badge_bbox = render.draw_source_fault_badge(canvas, IDX_WHITE)
        fl, ft, fr, fb = frame_box
        bl, bt, br, bb = badge_bbox
        if not (bl >= fl and bt >= ft and br <= fr and bb <= fb):
            return False, "badge bbox %r is not contained within the frame bbox %r" % (badge_bbox, frame_box)
        return True, ""
    check("draw_source_fault_badge()'s bounding box stays inside the drawn frame", _badge_bbox_stays_inside_the_drawn_frame)

    # 64. All three runway ids combined with the single registered theme id
    # render without error across both active states - a small matrix, so
    # a future theme addition is immediately exercised.
    def _runway_and_theme_matrix_combines_without_error():
        for runway_id in render.device_config.RUNWAY_IDS:
            for theme_id in render.device_config.THEME_IDS:
                for state in ("departing", "arriving"):
                    render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE, runway_id=runway_id, theme_id=theme_id)
        return True, ""
    check(
        "all three runway ids combined with the single theme id render without error across both active states "
        "(theme-addition regression guard)",
        _runway_and_theme_matrix_combines_without_error,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
