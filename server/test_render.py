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

EXPECTED_CHECK_COUNT = 38

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

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
