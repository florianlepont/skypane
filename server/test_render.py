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
rather than rendering to a scratch canvas and comparing pixel signatures or
doing OCR. Most roles draw one whole-string call per role; the top row
(state label + runway tag, spike 002a's `LABEL_TRACKING_PX` tracking,
resurrected this quick task) is the sole exception - it composites
glyph-by-glyph through `draw_tracked_text()`, so top-row checks reconstruct
each run from consecutive single-character calls at `y == MARGIN` instead
of matching a single whole-string text value.

Uses the real vendored illustration files under
server/assets/icons/illustrations/ (air-france.png, transavia-france.png,
generic-fallback.png, ...) - these are real project assets, not test
fixtures, so a broken selection/compositing path is caught against the
same files poll_loop.py will actually serve.

Usage:
    server/.venv/bin/python3 server/test_render.py
"""
import contextlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 118

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}
LEGAL_IDX = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}
# Bridges the two numbering schemes for the CFG-01 per-theme dominance check
# (08-CONTEXT.md D-01/D-02) - mirrors panel_format.INDEX_TO_NIBBLE without
# importing it, so this harness's expectations stay independently derived.
IDX_TO_NIBBLE = {
    IDX_BLACK: NIBBLE_BLACK,
    IDX_WHITE: NIBBLE_WHITE,
    IDX_YELLOW: NIBBLE_YELLOW,
    IDX_RED: NIBBLE_RED,
    IDX_BLUE: NIBBLE_BLUE,
    IDX_GREEN: NIBBLE_GREEN,
}

TEST_FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
TEST_PREVIOUS_FLIGHT = {"hex": "4a1b02", "callsign": "VLG6PD", "aircraft_type": "A320"}

# A real resolved route (server/fixtures/adsbdb_hit_TVF16VB.json, already
# sentence-cased per server.plane.enrich.to_sentence_case_city) - its
# airline_name ("Transavia France") resolves to a real vendored
# illustration file (transavia-france.png, added to HANDOFF.md 2026-08-26).
# callsign_iata ("TO16VB", Phase 8 08-04, D-09/D-10) is the real value the
# same fixture carries - not a synthetic value - so the default test render
# exercises D-10 tier 1 with a genuinely real identifier.
TEST_ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
    "callsign_iata": "TO16VB",
}
# callsign_iata ("VY8163", Phase 8 08-04) is a synthetic IATA-format value
# (Vueling's real IATA prefix, VY) - this route is hand-built, not from a
# recorded fixture.
TEST_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY8163",
}

# A genuinely long real destination city name and a genuinely long real
# airline name, used to exercise fit_text_size()'s shrink path. callsign_iata
# ("AT9051", Phase 8 08-04) is a synthetic IATA-format value (Royal Air
# Maroc's real IATA prefix, AT) - without it, this stress check would
# exercise a SHORTER string than before D-10 tier 1 prepends an identifier,
# quietly weakening the existing guard rail.
TEST_LONG_ROUTE = {
    "airline_name": "Compagnie Nationale Royale Air Maroc Express",
    "origin_iata": "SCQ",
    "origin_city": "Santiago de Compostela–Rosalía de Castro",
    "destination_iata": "ORY",
    "destination_city": "Paris",
    "callsign_iata": "AT9051",
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
    one canvas - list of (text, xy, anchor). Most roles issue one
    whole-string call; the top row (state label + runway tag) issues one
    call per glyph via `draw_tracked_text()`'s `LABEL_TRACKING_PX` tracking
    (spike 002a) - callers reconstruct that run from consecutive
    single-character calls rather than matching a whole-string value.
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


class _RectangleSpy:
    """Captures every ImageDraw.ImageDraw.rectangle() call made while
    building one canvas - list of (bounds, fill, outline, width). Mirrors
    `_TextSpy`'s monkeypatch-and-restore technique, applied to the
    rectangle-drawing seam instead of the text-drawing one (D-05 regression
    guard: proves no background-filled rectangle is painted behind text).
    """

    def __init__(self, render_mod):
        self._render_mod = render_mod
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = self._render_mod.ImageDraw.ImageDraw.rectangle

        def _spy(draw_self, xy, fill=None, outline=None, width=1):
            self.calls.append((tuple(xy), fill, outline, width))
            return self._orig(draw_self, xy, fill=fill, outline=outline, width=width)

        self._render_mod.ImageDraw.ImageDraw.rectangle = _spy
        return self

    def __exit__(self, exc_type, exc, tb):
        self._render_mod.ImageDraw.ImageDraw.rectangle = self._orig
        return False


class _TextBBoxSpy:
    """Captures every ImageDraw.ImageDraw.textbbox() call's RETURN VALUE made
    while building one canvas - list of (text, xy, anchor, bbox). Mirrors
    `_TextSpy`'s monkeypatch-and-restore technique, applied to the
    bbox-measurement seam instead of the draw seam (Phase 8 08-05 D-12
    spot-check): lets a check read the actual measured bounding box a text
    run received, without re-deriving `fit_text_size()`'s own font-fitting
    logic independently - a re-derivation would go stale the moment that
    logic changes and would silently stop protecting anything.
    """

    def __init__(self, render_mod):
        self._render_mod = render_mod
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = self._render_mod.ImageDraw.ImageDraw.textbbox

        def _spy(draw_self, xy, text, *args, **kwargs):
            bbox = self._orig(draw_self, xy, text, *args, **kwargs)
            self.calls.append((text, xy, kwargs.get("anchor"), bbox))
            return bbox

        self._render_mod.ImageDraw.ImageDraw.textbbox = _spy
        return self

    def __exit__(self, exc_type, exc, tb):
        self._render_mod.ImageDraw.ImageDraw.textbbox = self._orig
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


class _PlacementSpy:
    """Captures every `IllustrationPlacement` render.py's
    `_build_active_canvas()` actually produced while building one canvas, in
    call order (main card first, previous card second).

    Wraps the real `draw_illustration` and records its RETURN value rather than
    recomputing placement from the geometry constants - so these checks observe
    what the renderer really did. Recomputing would silently keep passing if
    `_build_active_canvas()` were reverted to positioning by `.rect`.
    """

    def __init__(self, render_mod):
        self._render_mod = render_mod
        self.placements = []
        self._orig = None

    def __enter__(self):
        self._orig = self._render_mod.draw_illustration

        def _spy(canvas, resized_rgba, left, top):
            placement = self._orig(canvas, resized_rgba, left, top)
            self.placements.append(placement)
            return placement

        self._render_mod.draw_illustration = _spy
        return self

    def __exit__(self, exc_type, exc, tb):
        self._render_mod.draw_illustration = self._orig
        return False


@contextlib.contextmanager
def _forced_illustration_pair(render_mod, main_path, prev_path):
    """Force the main card onto `main_path` and the previous card onto
    `prev_path`. `_build_active_canvas()` calls `select_illustration()` exactly
    twice, main first - see the "no crossover" check above, which pins that
    order independently. Lets a check pair two files with deliberately
    mismatched transparent padding, which is the only way to prove the two
    cards are aligned to each other rather than both to a shared rectangle.
    """
    orig = render_mod.illustrations.select_illustration
    paths = iter((main_path, prev_path))
    render_mod.illustrations.select_illustration = lambda route, aircraft_type=None: next(paths)
    try:
        yield
    finally:
        render_mod.illustrations.select_illustration = orig


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

    # 3-4. The flat background field is still the dominant nibble per state -
    # both states now share one field colour (White), the new default theme
    # (08-CONTEXT.md D-01). Two identical expectations below is deliberate,
    # not a copy-paste error: D-01's whole point is that DEPARTING vs.
    # ARRIVING is now carried by the label text alone, since the White theme
    # is single-colour across both states.
    def _departing_dominant_is_white():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_WHITE:
            return False, "departing render's dominant nibble is 0x%x, expected 0x1 (White)" % dom
        return True, ""
    check("departing render's dominant nibble is 0x1 (White) - D-01 White default theme background", _departing_dominant_is_white)

    def _arriving_dominant_is_white():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_WHITE:
            return False, "arriving render's dominant nibble is 0x%x, expected 0x1 (White)" % dom
        return True, ""
    check(
        "arriving render's dominant nibble is also 0x1 (White) - D-01's single shared field colour for both states, "
        "not a copy-paste duplicate of the departing check above",
        _arriving_dominant_is_white,
    )

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
        placement = render.draw_illustration(canvas, gradient, 10, 10)
        # `.rect` is the full 40x40 placement rectangle pasted at (10, 10) -
        # unchanged by the illustration-crop-text-margin fix.
        if placement.rect != (10, 10, 50, 50):
            return False, "draw_illustration() returned rect %r, expected (10, 10, 50, 50)" % (placement.rect,)
        # `.content` is the tight bbox of what actually gets PAINTED. This
        # source's alpha ramp is int(255 * x / 39), so alpha exceeds the
        # threshold of 127 first at x=20 (int(130.7)=130) and not at x=19
        # (int(124.2)=124) - columns 20..39 are painted, 0..19 are erased.
        # Absolute: (10+20, 10+0, 10+40, 10+40).
        if placement.content != (30, 10, 50, 50):
            return False, (
                "draw_illustration() returned content %r, expected (30, 10, 50, 50) - the tight "
                "bbox of pixels above the alpha threshold, not the full rectangle" % (placement.content,)
            )
        idx_set = {value for _count, value in canvas.getcolors()} if canvas.getcolors() else set()
        illegal = idx_set - LEGAL_IDX
        if illegal:
            return False, "a soft-alpha source produced illegal palette index(es) %r on the canvas - alpha must be hard-thresholded before paste()" % (sorted(illegal),)
        return True, ""
    check(
        "draw_illustration() with a soft/gradient alpha source never produces an illegal in-between palette index "
        "(Pitfall 2 regression), and returns .rect (full placement) plus .content (tight painted bbox) as distinct boxes",
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

    # 14-15. D-26/spike-002a top row: state label + runway tag, both tracked
    # glyph-by-glyph at LABEL_TRACKING_PX, near the MARGIN inset, in the
    # correct top corners. draw_top_labels() draws the label first and the
    # tag second (its own fixed draw order), so the single-character calls
    # captured at y == MARGIN can be reconstructed in call order without
    # needing to x-sort them.
    def _departing_top_row_labels_present():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        joined = "".join(t for t, _xy, _a in top_row)
        label_text = render.STATE_LABEL_TEXT["departing"]
        tag_text = render.TOP_RIGHT_TAG_TEXT
        expected = label_text + tag_text
        if joined != expected:
            return False, (
                "reconstructed top-row glyph run = %r, expected label %r followed by tag %r (%r)"
                % (joined, label_text, tag_text, expected)
            )
        return True, ""
    check(
        "departing render draws the top-left 'DEPARTING' label and the top-right runway tag, both tracked "
        "glyph-by-glyph, label first then tag",
        _departing_top_row_labels_present,
    )

    def _top_labels_sit_at_the_margin_inset():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        label_text = render.STATE_LABEL_TEXT["arriving"]
        tag_text = render.TOP_RIGHT_TAG_TEXT
        if len(top_row) < len(label_text) + len(tag_text):
            return False, "expected %d top-row glyph draws, got %d: %r" % (
                len(label_text) + len(tag_text), len(top_row), top_row,
            )
        label_glyphs = top_row[: len(label_text)]
        tag_glyphs = top_row[len(label_text):len(label_text) + len(tag_text)]
        (first_label_xy, first_label_anchor) = label_glyphs[0][1], label_glyphs[0][2]
        if first_label_xy != (render.MARGIN, render.MARGIN) or first_label_anchor != "la":
            return False, "state label's first glyph drawn at %r anchor=%r, expected (%d, %d) anchor='la'" % (
                first_label_xy, first_label_anchor, render.MARGIN, render.MARGIN,
            )
        weight = render.device_config.theme_weight(render.device_config.DEFAULT_THEME_ID)
        tag_font = render._role_font(render.TOP_TAG_FONT, weight)
        tracked_width = render._tracked_text_width(tag_font, tag_text, render.LABEL_TRACKING_PX)
        expected_tag_x = panel_format.WIDTH - render.MARGIN - tracked_width
        (first_tag_xy, first_tag_anchor) = tag_glyphs[0][1], tag_glyphs[0][2]
        if abs(first_tag_xy[0] - expected_tag_x) > 0.01 or first_tag_xy[1] != render.MARGIN or first_tag_anchor != "la":
            return False, "top-right tag's first glyph drawn at %r anchor=%r, expected (%.2f, %d) anchor='la'" % (
                first_tag_xy, first_tag_anchor, expected_tag_x, render.MARGIN,
            )
        if abs((first_tag_xy[0] + tracked_width) - (panel_format.WIDTH - render.MARGIN)) > 0.01:
            return False, "top-right tag run does not end flush at WIDTH - MARGIN (%d): first glyph x %.2f + tracked width %.2f" % (
                panel_format.WIDTH - render.MARGIN, first_tag_xy[0], tracked_width,
            )
        return True, ""
    check(
        "the state label's first glyph sits at the MARGIN inset and the top-right tag's first glyph is "
        "positioned so its tracked run ends flush at WIDTH - MARGIN (D-26, spike 002a)",
        _top_labels_sit_at_the_margin_inset,
    )

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

    # 17-19. Main flight text: "{identifier} to|from {city}" line 1 (D-10
    # tier 1), airline name line 2, no "PREVIOUS ·" prefix leaking onto the
    # main block.
    def _departing_main_text_uses_lowercase_to():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s to %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["destination_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_FLIGHT["aircraft_type"]]
        expected_line2 = "%s · %s" % (TEST_ROUTE["airline_name"], type_label)
        if expected_line1 not in texts:
            return False, "expected main line 1 %r among the text draws, got %r" % (expected_line1, texts)
        if expected_line2 not in texts:
            return False, "expected main line 2 %r among the text draws, got %r" % (expected_line2, texts)
        return True, ""
    check("departing main flight text is '{identifier} to {destination_city}' / '{airline_name} · {type_label}' (D-10 tier 1)", _departing_main_text_uses_lowercase_to)

    def _arriving_main_text_uses_lowercase_from():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s from %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["origin_city"])
        if expected_line1 not in texts:
            return False, "expected main line 1 %r among the text draws, got %r" % (expected_line1, texts)
        return True, ""
    check("arriving main flight text is '{identifier} from {origin_city}' (D-10 tier 1, lowercase sentence text)", _arriving_main_text_uses_lowercase_from)

    def _enrichment_miss_shows_unknown_flight():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=None)
        texts = [t for t, _xy, _anchor in spy.calls]
        if "Unknown flight" not in texts:
            return False, "expected 'Unknown flight' among the text draws on a full enrichment miss (D-10 tier 4), got %r" % (texts,)
        if render.ROUTE_FALLBACK_TEXT not in texts:
            return False, "expected %r among the text draws on an enrichment miss, got %r" % (render.ROUTE_FALLBACK_TEXT, texts)
        if TEST_FLIGHT["callsign"] in texts:
            return False, "the raw callsign %r must never appear on a full enrichment miss (D-08), got %r" % (TEST_FLIGHT["callsign"], texts)
        return True, ""
    check("a full enrichment miss (route=None) draws 'Unknown flight' and ROUTE_FALLBACK_TEXT, never the raw callsign (D-08/D-10 tier 4)", _enrichment_miss_shows_unknown_flight)

    # 20-22. D-25/D-26 previous flight card: present only when supplied, no
    # "PREVIOUS ·" prefix, right-aligned text, own real illustration.
    def _previous_flight_card_renders_its_own_text():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        texts = [t for t, _xy, _anchor in spy.calls]
        expected_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
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
        expected_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
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

    # 24. PT Serif Bold (D-06) is the active weight for every active-state
    # text role; the empty state's heading keeps a Bold weight; EMPTY_BODY_FONT
    # is the one remaining active reference to the Regular file.
    def _pt_serif_bold_is_the_active_weight():
        active_roles = ("STATE_LABEL_FONT", "TOP_TAG_FONT", "MAIN_LINE1_FONT", "MAIN_LINE2_FONT", "PREVIOUS_LINE1_FONT", "PREVIOUS_LINE2_FONT")
        for name in active_roles:
            if not hasattr(render, name):
                return False, "server.plane.render has no %s role constant" % name
            path, _size, _weight = getattr(render, name)
            if not path.endswith("PTSerif-Bold.ttf"):
                return False, "%s font path %r is not PTSerif-Bold.ttf (D-06)" % (name, path)
        if not render.EMPTY_HEADING_FONT[0].endswith("PTSerif-Bold.ttf"):
            return False, "EMPTY_HEADING_FONT font path %r is not PTSerif-Bold.ttf" % (render.EMPTY_HEADING_FONT[0],)
        if not render.EMPTY_BODY_FONT[0].endswith("PTSerif-Regular.ttf"):
            return False, "EMPTY_BODY_FONT font path %r is not PTSerif-Regular.ttf - it is the one remaining active reference to the Regular file" % (render.EMPTY_BODY_FONT[0],)
        return True, ""
    check("every active-state text role uses PTSerif-Bold.ttf (D-06); the empty-state heading keeps PTSerif-Bold.ttf and EMPTY_BODY_FONT keeps PTSerif-Regular.ttf", _pt_serif_bold_is_the_active_weight)

    # 24b. PREVIOUS_LINE2_FONT's size grew from 16 to 20 (D-11); its overflow
    # floor is unchanged.
    def _previous_line2_font_grew_to_20px():
        if render.PREVIOUS_LINE2_FONT[1] != 20:
            return False, "PREVIOUS_LINE2_FONT size is %r, expected 20 (D-11)" % (render.PREVIOUS_LINE2_FONT[1],)
        if render.PREVIOUS_LINE2_MIN_SIZE != 12:
            return False, "PREVIOUS_LINE2_MIN_SIZE is %r, expected unchanged 12" % (render.PREVIOUS_LINE2_MIN_SIZE,)
        return True, ""
    check("PREVIOUS_LINE2_FONT's size is 20px (D-11) with its overflow floor unchanged", _previous_line2_font_grew_to_20px)

    # 24c. Behavioural check, revised on-glass (08-06): the active weight is
    # theme-conditional, not universal. On the flat White theme (never
    # dithered), every active-state role must request PTSerif-Regular.ttf
    # and never PTSerif-Bold.ttf - Bold's whole job (resisting dithered
    # speckle) never applies there, and it read as needlessly heavy on
    # real ink. On a dithered theme (Sky), the original D-06 contract
    # holds: every role must request PTSerif-Bold.ttf and never Regular.
    # Monkeypatches render._font, the seam both the direct role-constant
    # lookups (draw_top_labels()) and fit_text_size() itself call through
    # via _role_font()/_role_fit_text_size(), so it captures every font
    # path actually requested.
    def _spy_requested_font_paths(theme_id):
        requested_paths = []
        orig_font = render._font

        def _spy_font(spec):
            requested_paths.append(spec[0])
            return orig_font(spec)

        render._font = _spy_font
        try:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
                theme_id=theme_id,
            )
            render.build_canvas(
                TEST_FLIGHT, "arriving", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="departing",
                theme_id=theme_id,
            )
        finally:
            render._font = orig_font
        return requested_paths

    def _spy_requested_font_paths_with_fault(theme_id):
        # Same spy idiom as _spy_requested_font_paths(), but with
        # source_fault=True so draw_source_fault_badge()'s caption font
        # request is captured too (code-review WR-01's blind spot).
        requested_paths = []
        orig_font = render._font

        def _spy_font(spec):
            requested_paths.append(spec[0])
            return orig_font(spec)

        render._font = _spy_font
        try:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True, theme_id=theme_id,
            )
        finally:
            render._font = orig_font
        return requested_paths

    def _white_theme_uses_only_regular_weight():
        requested_paths = _spy_requested_font_paths("white")
        if not requested_paths:
            return False, "no font was requested at all - the spy did not capture anything"
        bold_hits = [p for p in requested_paths if p.endswith("PTSerif-Bold.ttf")]
        if bold_hits:
            return False, "PTSerif-Bold.ttf was requested %d time(s) on a White-theme active-state panel - expected zero, White is never dithered (08-06): %r" % (len(bold_hits), bold_hits)
        regular_hits = [p for p in requested_paths if p.endswith("PTSerif-Regular.ttf")]
        if not regular_hits:
            return False, "PTSerif-Regular.ttf was never requested while rendering a White-theme active-state panel"
        return True, ""
    check(
        "the White theme's active-state roles request only PTSerif-Regular.ttf, never Bold (08-06 on-glass correction)",
        _white_theme_uses_only_regular_weight,
    )

    # 24c-ii. Same behavioural contract, generalised across every registry
    # entry (Phase 8 08-06, widened same session: 5 themes -> 11, each with
    # its own `dithered`/`weight` pair - see device_config.THEMES' own
    # module comment). Each theme's requested font paths must match its
    # own declared `theme_weight()` exactly - never the other weight.
    def _every_theme_uses_only_its_declared_weight():
        for theme_id in render.device_config.THEME_IDS:
            requested_paths = _spy_requested_font_paths(theme_id)
            if not requested_paths:
                return False, "%r: no font was requested at all - the spy did not capture anything" % (theme_id,)
            declared_weight = render.device_config.theme_weight(theme_id)
            wrong_suffix = "PTSerif-Regular.ttf" if declared_weight == "bold" else "PTSerif-Bold.ttf"
            right_suffix = "PTSerif-Bold.ttf" if declared_weight == "bold" else "PTSerif-Regular.ttf"
            wrong_hits = [p for p in requested_paths if p.endswith(wrong_suffix)]
            if wrong_hits:
                return False, "%r (declared weight %r): %s was requested %d time(s) - expected zero: %r" % (
                    theme_id, declared_weight, wrong_suffix, len(wrong_hits), wrong_hits)
            right_hits = [p for p in requested_paths if p.endswith(right_suffix)]
            if not right_hits:
                return False, "%r (declared weight %r): %s was never requested" % (theme_id, declared_weight, right_suffix)
        return True, ""
    check(
        "every one of the 11 registry themes requests only its own declared weight (08-06 on-glass correction, widened same session)",
        _every_theme_uses_only_its_declared_weight,
    )

    # 24d. The text-backing-plate helper (D-05) no longer exists on the
    # module at all - the removal is complete, not partial.
    def _paint_text_backing_helper_is_gone():
        if hasattr(render, "_paint_text_backing"):
            return False, "server.plane.render still carries _paint_text_backing - D-05 requires its complete removal"
        return True, ""
    check("_paint_text_backing() no longer exists on server.plane.render (D-05)", _paint_text_backing_helper_is_gone)

    # 24e. No rectangle filled with the state's own background index is ever
    # painted (i.e. no background-filled "backing plate" behind text, on any
    # theme). Captured via _RectangleSpy across every registered theme and
    # both active states - driven from the theme registry so a future sixth
    # theme is exercised automatically, matching the per-theme dominance
    # check's own pattern above. Observed set for a plain two-flight active
    # render (no battery-low icon, no source-fault badge): EMPTY - draw_frame()
    # is not called from this render path (removed 2026-08-28, quick task
    # 260828-k5r) and the text-backing-plate is now gone too, so this check
    # currently passes vacuously per-render and exists purely as a
    # regression guard against either being reintroduced.
    def _no_background_filled_rectangle_behind_text_on_any_theme():
        for theme_id in render.device_config.THEME_IDS:
            for state, prev_state in (("departing", "arriving"), ("arriving", "departing")):
                bg_idx = render.state_background_index(state, theme_id=theme_id)
                with _RectangleSpy(render) as spy:
                    render.build_canvas(
                        TEST_FLIGHT, state, route=TEST_ROUTE, theme_id=theme_id,
                        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state=prev_state,
                    )
                for bounds, fill, _outline, _width in spy.calls:
                    if fill == bg_idx:
                        return False, "theme=%r state=%r: a rectangle at %r was filled with bg_idx=%r - a background-filled plate exists (D-05 regression)" % (theme_id, state, bounds, bg_idx)
        return True, ""
    check(
        "no rectangle filled with the state's own background index is painted, on any registered theme, in either active state (D-05)",
        _no_background_filled_rectangle_behind_text_on_any_theme,
    )

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
        expected_line1 = "%s from %s" % (TEST_LONG_ROUTE["callsign_iata"], TEST_LONG_ROUTE["origin_city"])
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

    # 39. EJU84YF (a confirmed adsbdb miss, easyJet Europe): line 1 is
    # omitted entirely (no to/from clause, no city, no raw callsign -
    # genuinely unknown, D-10 tier 3), line 2 is the resolved airline name
    # alone (no aircraft_type supplied), and ROUTE_FALLBACK_TEXT does not
    # appear anywhere - the airline-only case is not the same as a full miss.
    def _airline_only_route_shows_airline_not_fallback_text():
        import server.plane.enrich as enrich

        airline_only_flight = {"hex": "440cb1", "callsign": "EJU84YF"}
        airline_only_route = enrich.airline_only_route("easyJet")
        with _TextSpy(render) as spy:
            render.build_canvas(airline_only_flight, "departing", route=airline_only_route)
        texts = [t for t, _xy, _anchor in spy.calls]
        if "EJU84YF" in texts:
            return False, "the raw callsign 'EJU84YF' must never appear on an airline-only route (D-08/D-10 tier 3), got %r" % (texts,)
        if "easyJet" not in texts:
            return False, "expected the resolved airline name 'easyJet' among the text draws, got %r" % (texts,)
        if render.ROUTE_FALLBACK_TEXT in texts:
            return False, "ROUTE_FALLBACK_TEXT must not appear when the airline is known (D-06), got %r" % (texts,)
        return True, ""
    check(
        "an airline-only route (adsbdb miss, prefix-resolved 'easyJet') omits line 1 entirely and draws only the "
        "airline name, never the raw callsign or ROUTE_FALLBACK_TEXT (D-08/D-10 tier 3)",
        _airline_only_route_shows_airline_not_fallback_text,
    )

    # 40. Transavia France + B738: line 2 composes exactly like a full hit
    # ("{airline} · {type label}"), while line 1 is omitted entirely -
    # no to/from clause, no city, no raw callsign fabricated from the prefix.
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
        if "TVF12ZW" in texts:
            return False, "the raw callsign 'TVF12ZW' must never appear on an airline-only route (D-08/D-10 tier 3), got %r" % (texts,)
        for text in texts:
            if " to " in text or " from " in text:
                return False, "found a to/from clause %r - the destination must stay genuinely unknown (D-06)" % (text,)
        return True, ""
    check(
        "an airline-only Transavia France + B738 route composes line 2 as '{airline} · {type label}' exactly like a "
        "full hit, line 1 omitted entirely, never the raw callsign or a to/from clause (D-08/D-10 tier 3)",
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

    # --- Phase 8 08-04 (D-08/D-09/D-10): _flight_line1_text()'s four-tier
    # content ladder, unit-level checks against the function directly plus
    # one end-to-end D-08 guard and one hostile-input battery. -------------

    # 43. Tier 1 (identifier + city both known), both states, exact string.
    def _tier1_identifier_and_city_both_known():
        route = {
            "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
            "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": "AF1234",
        }
        flight = {"hex": "aaaaaa", "callsign": "AFR001"}
        departing = render._flight_line1_text(flight, "departing", route)
        arriving = render._flight_line1_text(flight, "arriving", route)
        if departing != "AF1234 to New York":
            return False, "tier 1 departing expected 'AF1234 to New York', got %r" % (departing,)
        if arriving != "AF1234 from Paris":
            return False, "tier 1 arriving expected 'AF1234 from Paris', got %r" % (arriving,)
        return True, ""
    check(
        "_flight_line1_text() tier 1 (identifier + city) returns the exact '{identifier} to|from {city}' string "
        "for both states (D-10)",
        _tier1_identifier_and_city_both_known,
    )

    # 44. Tier 2 (city known, no identifier), both states, title-case
    # direction word, no identifier anywhere in the result.
    def _tier2_city_known_no_identifier():
        route = {
            "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
            "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": None,
        }
        flight = {"hex": "aaaaaa", "callsign": "AFR001"}
        departing = render._flight_line1_text(flight, "departing", route)
        arriving = render._flight_line1_text(flight, "arriving", route)
        if departing != "To New York":
            return False, "tier 2 departing expected 'To New York', got %r" % (departing,)
        if arriving != "From Paris":
            return False, "tier 2 arriving expected 'From Paris', got %r" % (arriving,)
        return True, ""
    check(
        "_flight_line1_text() tier 2 (city known, no identifier) returns the title-case direction word and city, "
        "with no identifier, for both states (D-10)",
        _tier2_city_known_no_identifier,
    )

    # 45. Tier 3 (airline only, no city, no identifier) returns an empty
    # string - the sentinel meaning line 1 is omitted.
    def _tier3_airline_only_returns_empty_string():
        import server.plane.enrich as enrich

        route = enrich.airline_only_route("Ryanair")
        flight = {"hex": "bbbbbb", "callsign": "RYR123"}
        departing = render._flight_line1_text(flight, "departing", route)
        arriving = render._flight_line1_text(flight, "arriving", route)
        if departing != "" or arriving != "":
            return False, "tier 3 (airline-only route) expected an empty string for both states, got %r/%r" % (departing, arriving)
        return True, ""
    check(
        "_flight_line1_text() tier 3 (airline known, no city, no identifier) returns an empty string - the "
        "sentinel meaning line 1 is omitted (D-10)",
        _tier3_airline_only_returns_empty_string,
    )

    # 46. Tier 4 (nothing resolved) returns the fixed "Unknown flight"
    # string, for both route=None and a dict carrying no airline name
    # either, identical for both states.
    def _tier4_nothing_resolved_returns_unknown_flight():
        flight = {"hex": "cccccc", "callsign": "XYZ999"}
        no_airline_route = {
            "airline_name": None, "origin_iata": None, "origin_city": None,
            "destination_iata": None, "destination_city": None, "callsign_iata": None,
        }
        for route in (None, no_airline_route):
            departing = render._flight_line1_text(flight, "departing", route)
            arriving = render._flight_line1_text(flight, "arriving", route)
            if departing != "Unknown flight":
                return False, "tier 4 departing expected 'Unknown flight' for route=%r, got %r" % (route, departing)
            if arriving != "Unknown flight":
                return False, "tier 4 arriving expected 'Unknown flight' for route=%r, got %r" % (route, arriving)
        return True, ""
    check(
        "_flight_line1_text() tier 4 (nothing resolved) returns the fixed string 'Unknown flight' "
        "for both route=None and a dict with no airline name, identical for both states (D-10)",
        _tier4_nothing_resolved_returns_unknown_flight,
    )

    # 47. The D-08 guard, end-to-end: across all four tiers and both cards,
    # no drawn text anywhere on the panel contains the flight's raw callsign
    # or hex.
    def _d08_no_raw_callsign_or_hex_anywhere_across_all_tiers():
        import server.plane.enrich as enrich

        main_flight = {"hex": "dddddd", "callsign": "MAINDISTINCT01", "aircraft_type": "B738"}
        prev_flight = {"hex": "eeeeee", "callsign": "PREVDISTINCT02", "aircraft_type": "A320"}
        tier1_route = dict(TEST_ROUTE)
        tier2_route = dict(TEST_ROUTE, callsign_iata=None)
        tier3_route = enrich.airline_only_route("Distinct Airline Tier3")
        forbidden = (
            main_flight["callsign"], main_flight["hex"].upper(),
            prev_flight["callsign"], prev_flight["hex"].upper(),
        )
        for route in (tier1_route, tier2_route, tier3_route, None):
            with _TextSpy(render) as spy:
                render.build_canvas(
                    main_flight, "departing", route=route,
                    previous_flight=prev_flight, previous_route=route, previous_state="arriving",
                )
            texts = [t for t, _xy, _anchor in spy.calls]
            for text in texts:
                for banned in forbidden:
                    if banned in text:
                        return False, "raw callsign/hex %r leaked into drawn text %r at route=%r (D-08)" % (banned, text, route)
        return True, ""
    check(
        "no drawn text on either card contains the raw callsign or hex, across all four content-ladder tiers "
        "(D-08 end-to-end guard)",
        _d08_no_raw_callsign_or_hex_anywhere_across_all_tiers,
    )

    # 48. Hostile route shapes degrade a tier instead of raising: a non-
    # string, empty, or whitespace-only identifier, and a non-dict route.
    def _hostile_route_shapes_degrade_a_tier_without_raising():
        flight = {"hex": "ffffff", "callsign": "HOSTILE1"}
        hostile_routes = (
            {"callsign_iata": 12345, "airline_name": "Some Airline"},
            {"callsign_iata": "", "airline_name": "Some Airline"},
            {"callsign_iata": "   ", "airline_name": "Some Airline"},
            "not-a-dict",
            42,
            [],
        )
        for state in ("departing", "arriving"):
            for route in hostile_routes:
                try:
                    result = render._flight_line1_text(flight, state, route)
                except Exception as exc:
                    return False, "route=%r state=%r raised %r instead of degrading a tier" % (route, state, exc)
                if not isinstance(result, str):
                    return False, "route=%r state=%r returned a non-string %r" % (route, state, result)
        return True, ""
    check(
        "_flight_line1_text() degrades a tier rather than raising for hostile route shapes (non-string/empty/"
        "whitespace identifier, non-dict route)",
        _hostile_route_shapes_degrade_a_tier_without_raising,
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

    # --- Debug session illustration-crop-text-margin: the aircraft-to-text gap
    # must be a property of the LAYOUT, not of whichever airline is flying. ---
    #
    # Three real vendored files chosen for maximal spread in transparent bottom
    # padding, measured with the renderer's own alpha threshold at the main
    # card's 992px render width: 37px (thinnest in the set), 74px (air-france -
    # the file the D-26 sketch pass was tuned against), 174px (thickest in the
    # set). Under the old full-rectangle anchoring these three produced visible
    # gaps of 17px, 54px and 154px respectively - a 9.1x spread, which is the
    # bug the developer saw on the physical e-ink panel.
    #
    # These checks are deliberately illustration-file-agnostic: they assert the
    # gap is IDENTICAL across the three, never that any file lands on a
    # particular pixel row. Re-anchoring either text block to `.rect` would
    # fail them immediately, no matter how the constants were retuned.
    GAP_SPREAD_ILLUSTRATIONS = (
        "iberia-airlines.png",
        "air-france.png",
        "asl-airlines-france.png",
    )

    def _illustration_path(basename):
        return os.path.join(REPO_ROOT, "server", "assets", "icons", "illustrations", basename)

    def _measured_gaps(basename):
        """Render the real two-flight layout forced onto one illustration, then
        return (main_gap, previous_gap, main_pad, previous_pad): the distance
        from each aircraft's last actually-painted pixel row to its text
        block's drawn anchor y, plus each card's transparent bottom padding.

        Both the painted bottoms and the paddings come from the placements the
        renderer actually produced (`_PlacementSpy`), never from a local
        re-derivation of the geometry constants - a re-derivation goes stale
        the moment placement changes, and would report a layout regression that
        is really just test drift.

        `main_pad`/`previous_pad` are `rect` bottom minus `content` bottom, so
        if `.content` ever degenerated back to `.rect` they would collapse to
        0 and trip the callers' own fixture-spread guard.
        """
        path = _illustration_path(basename)
        with _forced_illustration(render, path):
            with _PlacementSpy(render) as placements:
                with _TextSpy(render) as spy:
                    render.build_canvas(
                        TEST_FLIGHT, "departing", route=TEST_ROUTE,
                        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                        previous_state="arriving",
                    )
        if len(placements.placements) != 2:
            raise AssertionError("expected 2 illustration placements, got %d" % len(placements.placements))
        main_placement, prev_placement = placements.placements

        main_opaque_bottom = main_placement.content[3]
        main_pad = main_placement.rect[3] - main_placement.content[3]
        prev_opaque_bottom = prev_placement.content[3]
        prev_pad = prev_placement.rect[3] - prev_placement.content[3]

        main_line1 = "%s to %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["destination_city"])
        prev_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
        main_y = next(xy[1] for t, xy, _a in spy.calls if t == main_line1)
        prev_y = next(xy[1] for t, xy, _a in spy.calls if t == prev_line1)
        return main_y - main_opaque_bottom, prev_y - prev_opaque_bottom, main_pad, prev_pad

    # 47. The main block's gap is identical across illustrations whose
    # transparent bottom padding differs by >100px.
    def _main_text_gap_is_constant_across_illustrations():
        measured = {name: _measured_gaps(name) for name in GAP_SPREAD_ILLUSTRATIONS}
        pads = {name: m[2] for name, m in measured.items()}
        if max(pads.values()) - min(pads.values()) < 100:
            return False, (
                "these fixtures no longer span a wide range of transparent bottom padding (%r) - the check "
                "would pass trivially and must be re-pointed at files that do" % (pads,)
            )
        gaps = {name: m[0] for name, m in measured.items()}
        if len(set(gaps.values())) != 1:
            return False, (
                "the gap between the aircraft's last painted pixel and the main text varies by illustration: %r "
                "(bottom padding %r) - the text is anchored to the illustration's full rectangle, not its opaque "
                "content bbox" % (gaps, pads)
            )
        only = next(iter(set(gaps.values())))
        if only != render.MAIN_TEXT_GAP_PX:
            return False, "constant main gap is %dpx, expected MAIN_TEXT_GAP_PX (%d)" % (only, render.MAIN_TEXT_GAP_PX)
        return True, ""
    check(
        "the main flight text sits exactly MAIN_TEXT_GAP_PX below the aircraft's last actually-painted pixel row, "
        "identically for illustrations whose transparent bottom padding differs by over 100px "
        "(illustration-crop-text-margin: no full-rectangle anchoring)",
        _main_text_gap_is_constant_across_illustrations,
    )

    # 48. Same guarantee for the previous-flight card, which consumes its own
    # draw_illustration() placement and has its own gap constant.
    def _previous_text_gap_is_constant_across_illustrations():
        measured = {name: _measured_gaps(name) for name in GAP_SPREAD_ILLUSTRATIONS}
        pads = {name: m[3] for name, m in measured.items()}
        if max(pads.values()) - min(pads.values()) < 50:
            return False, (
                "these fixtures no longer span a wide range of transparent bottom padding at the previous card's "
                "scale (%r) - the check would pass trivially" % (pads,)
            )
        gaps = {name: m[1] for name, m in measured.items()}
        if len(set(gaps.values())) != 1:
            return False, (
                "the gap between the previous aircraft's last painted pixel and its text varies by illustration: %r "
                "(bottom padding %r) - the previous text block is anchored to the full rectangle" % (gaps, pads)
            )
        only = next(iter(set(gaps.values())))
        if only != render.PREVIOUS_TEXT_GAP_PX:
            return False, "constant previous gap is %dpx, expected PREVIOUS_TEXT_GAP_PX (%d)" % (only, render.PREVIOUS_TEXT_GAP_PX)
        return True, ""
    check(
        "the previous flight text sits exactly PREVIOUS_TEXT_GAP_PX below its aircraft's last actually-painted pixel "
        "row, identically across illustrations with very different transparent bottom padding",
        _previous_text_gap_is_constant_across_illustrations,
    )

    # 49. The measurement itself must use the paste threshold, not a naive
    # Image.getbbox(). This is the specific mistake that caused the bug: every
    # vendored file carries a soft drop-shadow band (alpha 1..127) that
    # getbbox() counts as content and draw_illustration() erases. Six files -
    # air-france.png among them - report a naive bottom padding of exactly 0
    # while their real painted padding is 82-174px, which is how "the vendored
    # illustration files have no transparent bottom padding of their own" came
    # to be written down as a verified fact.
    def _opaque_bbox_uses_the_paste_threshold_not_a_naive_getbbox():
        path = _illustration_path("air-france.png")
        rgba = Image.open(path).convert("RGBA")
        naive_rgba = rgba.getbbox()
        naive_alpha = rgba.getchannel("A").getbbox()
        thresholded = render._opaque_bbox(rgba)
        if thresholded is None:
            return False, "_opaque_bbox() returned None for a real vendored illustration"
        if naive_alpha[3] != rgba.size[1]:
            return False, (
                "fixture drift: air-france.png's raw-alpha bbox bottom is %d, not the full height %d - it no longer "
                "demonstrates the soft-shadow trap this check exists to guard" % (naive_alpha[3], rgba.size[1])
            )
        if thresholded[3] >= naive_alpha[3] or thresholded[3] >= naive_rgba[3]:
            return False, (
                "_opaque_bbox() bottom (%d) is not strictly above the naive bboxes (rgba %d, alpha %d) - it is "
                "counting sub-threshold drop-shadow pixels that draw_illustration() never paints"
                % (thresholded[3], naive_rgba[3], naive_alpha[3])
            )
        # And it must agree exactly with the mask actually handed to paste().
        painted = render._threshold_alpha(rgba).getbbox()
        if thresholded != painted:
            return False, (
                "_opaque_bbox() %r disagrees with the mask draw_illustration() pastes with %r - layout and painting "
                "must measure the same pixels" % (thresholded, painted)
            )
        return True, ""
    check(
        "_opaque_bbox() measures the hard-thresholded paste mask, never a naive Image.getbbox() - the soft "
        "drop-shadow band (alpha 1..127) that is never painted must not count as content",
        _opaque_bbox_uses_the_paste_threshold_not_a_naive_getbbox,
    )

    # 50. Structural guard on the return contract: for real vendored art the
    # two boxes must genuinely differ, so a future "simplification" that
    # returns the placement rectangle for both fields is caught here rather
    # than silently restoring per-airline gap drift.
    def _placement_content_is_strictly_inside_its_rect():
        path = _illustration_path("air-france.png")
        inner_width = panel_format.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
        main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
        resized = render._resize_illustration(path, main_w)
        canvas = panel_format.new_canvas(IDX_BLUE)
        placement = render.draw_illustration(canvas, resized, 100, 200)
        rect, content = placement.rect, placement.content
        if rect != (100, 200, 100 + resized.size[0], 200 + resized.size[1]):
            return False, "placement.rect %r is not the full pasted rectangle" % (rect,)
        if content == rect:
            return False, (
                "placement.content is identical to placement.rect for real vendored art - draw_illustration() is "
                "not measuring the painted pixels, and every text gap will drift per airline again"
            )
        if not (rect[0] <= content[0] and rect[1] <= content[1] and content[2] <= rect[2] and content[3] <= rect[3]):
            return False, "placement.content %r is not contained within placement.rect %r" % (content, rect)
        if content[3] >= rect[3]:
            return False, (
                "placement.content's bottom (%d) is not above placement.rect's bottom (%d) - the transparent bottom "
                "padding this fix exists to exclude is still being counted" % (content[3], rect[3])
            )
        return True, ""
    check(
        "draw_illustration() returns a placement whose .content is strictly contained in .rect, with a strictly "
        "higher bottom edge, for real vendored art (structural guard against restoring full-rectangle anchoring)",
        _placement_content_is_strictly_inside_its_rect,
    )

    # --- Pass 2 of the same debug session: horizontal/centring placement must
    # follow the painted pixels too, not the padded rectangle. ---------------
    #
    # Measured post-resize across the vendored set: horizontal padding is
    # asymmetric (main left 3-32px, right 5-29px), which pushed the visible
    # aircraft up to 7.5px off the canvas centre; and because the previous card
    # was right-aligned rectangle-to-rectangle, the two aircraft's visible
    # right edges could sit up to 26px apart. Vertical padding is asymmetric in
    # one direction (the drop-shadow band always makes bottom exceed top), so
    # centring the previous card's rectangle put its aircraft 5.5-28.5px high.
    #
    # All three checks read the placements the renderer actually produced (via
    # _PlacementSpy) and pair two DIFFERENT files, so they cannot be satisfied
    # by aligning both cards to a common rectangle.
    def _render_two_cards(main_basename, prev_basename):
        """Build the real two-flight canvas with the two cards forced onto
        different files; return (main_placement, prev_placement, text_calls).
        """
        base = os.path.join(REPO_ROOT, "server", "assets", "icons", "illustrations")
        with _forced_illustration_pair(render, os.path.join(base, main_basename), os.path.join(base, prev_basename)):
            with _PlacementSpy(render) as placements:
                with _TextSpy(render) as text:
                    render.build_canvas(
                        TEST_FLIGHT, "departing", route=TEST_ROUTE,
                        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                        previous_state="arriving",
                    )
        if len(placements.placements) != 2:
            raise AssertionError("expected 2 illustration placements, got %d" % len(placements.placements))
        return placements.placements[0], placements.placements[1], text.calls

    # 51. The main illustration's VISIBLE horizontal midpoint sits on the
    # canvas centre, for files whose left/right padding asymmetry differs
    # sharply. generic-beechcraft1900d.png was the worst offender at +7.5px.
    def _main_illustration_is_centred_on_its_visible_pixels():
        canvas_centre = panel_format.WIDTH / 2.0
        offsets = {}
        for name in ("generic-beechcraft1900d.png", "generic-atr72.png", "lot-polish-airlines.png", "transavia-france.png"):
            main_placement, _prev, _text = _render_two_cards(name, "transavia-france.png")
            content, rect = main_placement.content, main_placement.rect
            offsets[name] = (content[0] + content[2]) / 2.0 - canvas_centre
            # The rectangle must NOT be what is centred - otherwise this check
            # would pass trivially on a symmetric file.
            if (content[0] - rect[0]) == (rect[2] - content[2]):
                continue  # symmetric padding: both definitions agree, nothing to prove
        worst = max(abs(v) for v in offsets.values())
        if worst > 0.5:
            return False, (
                "the main aircraft's visible horizontal midpoint is off the canvas centre by up to %.1fpx %r - "
                "the illustration is being centred by its source rectangle, not its painted pixels" % (worst, offsets)
            )
        return True, ""
    check(
        "the main illustration's VISIBLE horizontal midpoint sits on the canvas centre (within rounding) for files "
        "with sharply different left/right padding asymmetry - centred by painted pixels, not by rectangle",
        _main_illustration_is_centred_on_its_visible_pixels,
    )

    # 52. The previous aircraft's visible right edge lands exactly on the main
    # aircraft's visible right edge, and the previous text is right-aligned to
    # that same shared line. Pairing km-malta-airlines.png (main right padding
    # 29px) with transavia-france.png (previous right padding 3px) is the
    # worst case: rectangle-to-rectangle alignment left the two aircraft 26px
    # apart, and the text 3px off its own aircraft.
    def _previous_card_and_text_align_to_the_main_aircrafts_visible_right_edge():
        main_placement, prev_placement, text_calls = _render_two_cards(
            "km-malta-airlines.png", "transavia-france.png")
        main_right = main_placement.content[2]
        prev_right = prev_placement.content[2]
        # Guard: the two files must actually differ in right padding, or the
        # check proves nothing.
        main_pad = main_placement.rect[2] - main_placement.content[2]
        prev_pad = prev_placement.rect[2] - prev_placement.content[2]
        if abs(main_pad - prev_pad) < 10:
            return False, (
                "fixture drift: main/previous right padding are now %dpx/%dpx - too close for this check to "
                "distinguish visible-edge from rectangle alignment" % (main_pad, prev_pad)
            )
        if prev_right != main_right:
            return False, (
                "the previous aircraft's visible right edge is at x=%d but the main aircraft's is at x=%d (%dpx "
                "apart) - the cards are aligned rectangle-to-rectangle, not aircraft-to-aircraft"
                % (prev_right, main_right, prev_right - main_right)
            )
        prev_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
        anchor_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line1)
        expected_anchor_x = prev_right - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
        if anchor_x != expected_anchor_x:
            return False, (
                "the previous flight text is right-aligned to x=%d, but its aircraft's visible right edge minus "
                "PREVIOUS_TEXT_LEFT_OFFSET_PX (%d) is x=%d - text and illustration are not aligned per D-12"
                % (anchor_x, render.PREVIOUS_TEXT_LEFT_OFFSET_PX, expected_anchor_x)
            )
        return True, ""
    check(
        "the previous aircraft's visible right edge lands exactly on the main aircraft's visible right edge, and the "
        "previous text right-aligns to that same shared line minus the D-12 optical offset, for two files with very "
        "different right padding",
        _previous_card_and_text_align_to_the_main_aircrafts_visible_right_edge,
    )

    # 54. Both of the previous card's text lines share one anchor x, equal to
    # the previous aircraft's measured opaque right edge minus
    # PREVIOUS_TEXT_LEFT_OFFSET_PX (D-12). A different check from 52 above:
    # 52 pins line 1's anchor against a specific worst-case padding pair; this
    # one confirms line 1 and line 2 agree with EACH OTHER, using the default
    # illustration pairing.
    def _previous_card_both_lines_share_one_anchor_at_the_optical_offset():
        _main_placement, prev_placement, text_calls = _render_two_cards(
            "transavia-france.png", "vueling-airlines.png")
        prev_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_PREVIOUS_FLIGHT["aircraft_type"]]
        prev_line2 = "%s · %s" % (TEST_PREVIOUS_ROUTE["airline_name"], type_label)
        line1_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line1)
        line2_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line2)
        if line1_x != line2_x:
            return False, "previous card's two lines anchor at different x (%d vs %d) - they must share one anchor" % (line1_x, line2_x)
        expected_x = prev_placement.content[2] - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
        if line1_x != expected_x:
            return False, (
                "previous card's shared anchor x=%d, expected the aircraft's visible right edge minus "
                "PREVIOUS_TEXT_LEFT_OFFSET_PX = %d" % (line1_x, expected_x)
            )
        return True, ""
    check(
        "the previous card's two text lines share one anchor x, equal to the previous aircraft's measured opaque "
        "right edge minus PREVIOUS_TEXT_LEFT_OFFSET_PX (D-12)",
        _previous_card_both_lines_share_one_anchor_at_the_optical_offset,
    )

    # 55. The main card is NOT offset - its lines stay centred on the canvas
    # midpoint with anchor='ma', unaffected by the previous card's D-12
    # correction.
    def _main_card_text_remains_centred_not_offset():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
            )
        main_line1 = "%s to %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["destination_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_FLIGHT["aircraft_type"]]
        main_line2 = "%s · %s" % (TEST_ROUTE["airline_name"], type_label)
        center_x = panel_format.WIDTH // 2
        for text in (main_line1, main_line2):
            calls = [(xy, a) for t, xy, a in spy.calls if t == text]
            if not calls:
                return False, "main line %r was not drawn" % (text,)
            xy, anchor = calls[0]
            if xy[0] != center_x or anchor != "ma":
                return False, (
                    "main line %r drawn at x=%r anchor=%r, expected centre x=%d anchor='ma' - the main card must "
                    "not receive the previous card's optical offset (D-12)" % (text, xy[0], anchor, center_x)
                )
        return True, ""
    check(
        "the main card's text lines stay centred on the canvas midpoint with anchor='ma', unaffected by the "
        "previous card's optical offset (D-12)",
        _main_card_text_remains_centred_not_offset,
    )

    # 56. Tier-3 promotion on the main card: an airline-only route omits
    # line 1 entirely, promoting line 2 into the y-position line 1 would
    # have used, with no empty-string draw call.
    def _tier3_promotion_on_main_card():
        import server.plane.enrich as enrich

        route = enrich.airline_only_route("Air France")
        flight = {"hex": "111111", "callsign": "AFR9001", "aircraft_type": "B738"}
        with _TextSpy(render) as spy:
            render.build_canvas(flight, "departing", route=route)
        with _PlacementSpy(render) as placements:
            render.build_canvas(flight, "departing", route=route)
        main_placement = placements.placements[0]
        expected_line2 = "%s · %s" % ("Air France", render._TYPE_DISPLAY_LABELS["B738"])
        main_region_calls = [(t, xy) for t, xy, _a in spy.calls if xy[1] >= main_placement.content[3]]
        texts_in_region = [t for t, _xy in main_region_calls]
        if "" in texts_in_region:
            return False, "an empty-string draw call was made for the omitted line 1: %r" % (main_region_calls,)
        if texts_in_region != [expected_line2]:
            return False, "expected exactly one text draw (%r) in the main block region, got %r" % (expected_line2, texts_in_region)
        expected_y = main_placement.content[3] + render.MAIN_TEXT_GAP_PX
        actual_y = main_region_calls[0][1][1]
        if actual_y != expected_y:
            return False, (
                "line 2's y is %d, expected %d (main_placement.content[3] + MAIN_TEXT_GAP_PX, the y line 1 would "
                "have used)" % (actual_y, expected_y)
            )
        return True, ""
    check(
        "an airline-only route on the main card omits line 1 entirely, promoting line 2 to line 1's y-position, "
        "with no empty-string draw call (D-10 tier 3)",
        _tier3_promotion_on_main_card,
    )

    # 57. Tier-3 promotion on the previous card. Deliberately a separate
    # check from 56, not a parameterisation of it - this is the one that
    # catches the omitted-line fix being implemented in only one of the two
    # drawing functions.
    def _tier3_promotion_on_previous_card():
        import server.plane.enrich as enrich

        prev_route = enrich.airline_only_route("Vueling Airlines")
        prev_flight = {"hex": "222222", "callsign": "VLG9002", "aircraft_type": "A320"}
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=prev_flight, previous_route=prev_route, previous_state="arriving",
            )
        with _PlacementSpy(render) as placements:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=prev_flight, previous_route=prev_route, previous_state="arriving",
            )
        _main_placement, prev_placement = placements.placements
        expected_line2 = "%s · %s" % ("Vueling Airlines", render._TYPE_DISPLAY_LABELS["A320"])
        # Previous-card text draws are right-aligned ('ra'); the top-right
        # tag also uses 'ra' but sits far above the previous card's region,
        # so combining the anchor filter with the y-floor isolates exactly
        # this card's own draws.
        prev_region_calls = [(t, xy) for t, xy, a in spy.calls if a == "ra" and xy[1] >= prev_placement.content[3]]
        texts_in_region = [t for t, _xy in prev_region_calls]
        if "" in texts_in_region:
            return False, "an empty-string draw call was made for the previous card's omitted line 1: %r" % (prev_region_calls,)
        if texts_in_region != [expected_line2]:
            return False, "expected exactly one text draw (%r) in the previous block region, got %r" % (expected_line2, texts_in_region)
        expected_y = prev_placement.content[3] + render.PREVIOUS_TEXT_GAP_PX
        actual_y = prev_region_calls[0][1][1]
        if actual_y != expected_y:
            return False, (
                "previous card's line 2 y is %d, expected %d (prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX)"
                % (actual_y, expected_y)
            )
        return True, ""
    check(
        "an airline-only route on the previous card omits its own line 1, promoting line 2 to line 1's y-position "
        "using the previous card's own gap constant, with no empty-string draw call (D-10 tier 3) - the check that "
        "catches the change implemented in only one of the two functions",
        _tier3_promotion_on_previous_card,
    )

    # 58. Tier 3 on both cards simultaneously, confirming the two
    # independent branches compose without interfering.
    def _tier3_on_both_cards_simultaneously():
        import server.plane.enrich as enrich

        main_route = enrich.airline_only_route("Air France")
        prev_route = enrich.airline_only_route("Vueling Airlines")
        main_flight = {"hex": "333333", "callsign": "AFR9003", "aircraft_type": "B738"}
        prev_flight = {"hex": "444444", "callsign": "VLG9004", "aircraft_type": "A320"}
        with _TextSpy(render) as spy:
            render.build_canvas(
                main_flight, "departing", route=main_route,
                previous_flight=prev_flight, previous_route=prev_route, previous_state="arriving",
            )
        texts = [t for t, _xy, _a in spy.calls]
        expected_main_line2 = "%s · %s" % ("Air France", render._TYPE_DISPLAY_LABELS["B738"])
        expected_prev_line2 = "%s · %s" % ("Vueling Airlines", render._TYPE_DISPLAY_LABELS["A320"])
        if expected_main_line2 not in texts:
            return False, "expected the main card's promoted line 2 %r among the text draws, got %r" % (expected_main_line2, texts)
        if expected_prev_line2 not in texts:
            return False, "expected the previous card's promoted line 2 %r among the text draws, got %r" % (expected_prev_line2, texts)
        if "" in texts:
            return False, "an empty-string draw call was made somewhere: %r" % (texts,)
        return True, ""
    check(
        "both cards independently omit line 1 and promote line 2 on a simultaneous airline-only render, without "
        "interfering with each other (D-10 tier 3)",
        _tier3_on_both_cards_simultaneously,
    )

    # 53. The previous card's VISIBLE vertical midpoint sits on the
    # PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC line. Because the drop-shadow band
    # makes bottom padding always exceed top padding, centring the rectangle
    # put every previous aircraft high, by 5.5-28.5px depending on the file.
    def _previous_card_is_vertically_centred_on_its_visible_pixels():
        centre_line = panel_format.HEIGHT * render.PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC
        offsets = {}
        for name in ("asl-airlines-france.png", "air-europa.png", "iberia-airlines.png", "amelia.png"):
            _main, prev_placement, _text = _render_two_cards("transavia-france.png", name)
            content = prev_placement.content
            offsets[name] = (content[1] + content[3]) / 2.0 - centre_line
        worst = max(abs(v) for v in offsets.values())
        if worst > 0.5:
            return False, (
                "the previous aircraft's visible vertical midpoint is off the %.1f centre line by up to %.1fpx %r - "
                "the card is being centred by its source rectangle, so it drifts vertically per illustration"
                % (centre_line, worst, offsets)
            )
        return True, ""
    check(
        "the previous card's VISIBLE vertical midpoint sits on the PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC line (within "
        "rounding) across illustrations with very different top/bottom padding - no per-file vertical drift",
        _previous_card_is_vertically_centred_on_its_visible_pixels,
    )

    # --- Plan 06-06: CFG-01 theme, CFG-12 runway, CFG-05 source-fault badge ---

    # 54. render_panel() with no theme_id is byte-identical to an explicit
    # default theme_id - the default path is genuinely unchanged.
    def _theme_default_matches_no_theme_arg():
        a = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        b = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=render.device_config.DEFAULT_THEME_ID)
        if a != b:
            return False, "render_panel() with no theme_id differs from an explicit default theme_id - CFG-01's default path must be byte-identical"
        return True, ""
    check("render_panel() with no theme_id is byte-identical to an explicit default theme_id (CFG-01)", _theme_default_matches_no_theme_arg)

    # 55. build_canvas(theme_id="white") and build_canvas() with no theme
    # produce identical canvases (D-01: White is now the default) - AND
    # every OTHER registry theme genuinely differs from that default canvas
    # by canvas content alone. "sky" (the old two-tone Blue/Green pairing)
    # was retired outright in the same 08-06 on-glass session that widened
    # the registry to 11 single-colour entries - this check is generalised
    # across whatever THEME_IDS actually holds today rather than naming one
    # theme, so it can never again go stale if the registry's membership
    # changes. Without the loop half, this check would still pass even if
    # every non-white theme had been deleted from the registry entirely.
    def _white_theme_canvas_matches_default_and_others_differ():
        default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        white_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="white")
        if list(default_canvas.getdata()) != list(white_canvas.getdata()):
            return False, "build_canvas(theme_id='white') differs from build_canvas() with no theme_id - White must be the default"
        default_data = list(default_canvas.getdata())
        for theme_id in render.device_config.THEME_IDS:
            if theme_id == "white":
                continue
            other_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
            if default_data == list(other_canvas.getdata()):
                return False, "build_canvas(theme_id=%r) is identical to the White default canvas - every registered theme must be genuinely distinct" % (theme_id,)
        return True, ""
    check(
        "build_canvas(theme_id='white') matches the no-theme default (D-01), and every other registered theme genuinely "
        "differs from it - none is a silent no-op",
        _white_theme_canvas_matches_default_and_others_differ,
    )

    # 56. An unrecognised theme id degrades to the default theme's canvas
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

    # 57. An unrecognised state still raises ValueError naming all three
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

    # 58. _assert_legal_palette() (run internally by build_canvas()) still
    # passes for every registered theme.
    def _legal_palette_holds_for_every_theme():
        for theme_id in render.device_config.THEME_IDS:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
        return True, ""
    check("_assert_legal_palette() (run internally by build_canvas()) passes for every registered theme", _legal_palette_holds_for_every_theme)

    # 59. Per-theme dominant background across both active states (D-01/D-02).
    # For every registered theme and both departing/arriving, a real
    # two-flight panel's dominant nibble must be that theme's own background
    # for that state - the concrete answer to CONTEXT.md's flagged
    # uncertainty about whether background dominance survives on a flat
    # Black/Yellow/Red field against a large livery area. Driven from
    # THEME_IDS/theme_background_index() so a future sixth theme is
    # exercised automatically.
    def _per_theme_dominant_background_holds_in_both_states():
        for theme_id in render.device_config.THEME_IDS:
            for state, previous_state in (("departing", "arriving"), ("arriving", "departing")):
                buf = render.render_panel(
                    TEST_FLIGHT, state, route=TEST_ROUTE,
                    previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                    previous_state=previous_state, theme_id=theme_id,
                )
                expected_idx = render.device_config.theme_background_index(state, theme_id)
                expected_nibble = IDX_TO_NIBBLE[expected_idx]
                dom = dominant_nibble(buf)
                if dom != expected_nibble:
                    return False, (
                        "theme %r state %r: dominant nibble is 0x%x, expected 0x%x (the theme's own background)"
                        % (theme_id, state, dom, expected_nibble)
                    )
        return True, ""
    check(
        "for every registered theme, in both departing and arriving states, a real two-flight panel's dominant "
        "nibble is that theme's own background (D-01/D-02 - the flat-field guard rail against a large livery area)",
        _per_theme_dominant_background_holds_in_both_states,
    )

    # 60. Ink index is the theme's own (D-02) - state_ink_index() must agree
    # with device_config.theme_ink_index() for every registered theme and
    # both active states, so a future per-state ink split cannot silently
    # bypass the registry.
    def _ink_index_matches_theme_registry_for_every_theme():
        for theme_id in render.device_config.THEME_IDS:
            expected = render.device_config.theme_ink_index(theme_id)
            for state in ("departing", "arriving"):
                got = render.state_ink_index(state, theme_id=theme_id)
                if got != expected:
                    return False, (
                        "state_ink_index(%r, theme_id=%r) = %r, expected device_config.theme_ink_index(%r) = %r"
                        % (state, theme_id, got, theme_id, expected)
                    )
        return True, ""
    check(
        "render.state_ink_index() agrees with device_config.theme_ink_index() for every registered theme, in both "
        "departing and arriving states (D-02)",
        _ink_index_matches_theme_registry_for_every_theme,
    )

    # 61. runway_tag_text() with no argument returns exactly the current
    # top-right tag string - the default render is unchanged.
    def _runway_tag_text_default_matches_top_right_tag():
        if render.runway_tag_text() != render.TOP_RIGHT_TAG_TEXT:
            return False, "runway_tag_text() != render.TOP_RIGHT_TAG_TEXT"
        return True, ""
    check("runway_tag_text() with no argument returns exactly TOP_RIGHT_TAG_TEXT (default render unchanged)", _runway_tag_text_default_matches_top_right_tag)

    # 62. runway_tag_text("06-24")/("02-20") return the strings from the
    # runway registry.
    def _runway_tag_text_matches_registry_for_other_runways():
        for runway_id in ("06-24", "02-20"):
            expected = render.device_config.runway_tag_text(runway_id)
            got = render.runway_tag_text(runway_id)
            if got != expected:
                return False, "runway_tag_text(%r) = %r, expected %r" % (runway_id, got, expected)
        return True, ""
    check("runway_tag_text('06-24')/('02-20') return the strings from device_config.RUNWAYS", _runway_tag_text_matches_registry_for_other_runways)

    # 63. An unrecognised runway id degrades to the default runway's tag
    # rather than raising.
    def _runway_tag_text_unknown_id_degrades_to_default():
        if render.runway_tag_text("nope") != render.runway_tag_text():
            return False, "runway_tag_text('nope') != runway_tag_text() - an unknown runway id must degrade to the default"
        return True, ""
    check("runway_tag_text('unknown') returns the default runway's tag rather than raising", _runway_tag_text_unknown_id_degrades_to_default)

    # 64. build_canvas(None, "empty", runway_id=...) draws that runway's
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

    # 65. build_canvas(flight, "departing", runway_id="06-24") draws that
    # runway's tag (tracked glyph-by-glyph), still passing the
    # within-canvas assertion.
    def _active_canvas_draws_selected_runways_tag():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, runway_id="06-24")
        top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        label_text = render.STATE_LABEL_TEXT["departing"]
        expected_tag = render.runway_tag_text("06-24")
        tag_glyphs = top_row[len(label_text):len(label_text) + len(expected_tag)]
        joined_tag = "".join(t for t, _xy, _a in tag_glyphs)
        if joined_tag != expected_tag:
            return False, "reconstructed tag glyph run = %r, expected the runway 06-24 tag %r" % (joined_tag, expected_tag)
        return True, ""
    check(
        "build_canvas(flight, 'departing', runway_id='06-24') draws that runway's tag glyph-by-glyph, passing "
        "the within-canvas assertion",
        _active_canvas_draws_selected_runways_tag,
    )

    # 66. render_panel(..., source_fault=False) is byte-identical to the
    # same call without the argument.
    def _source_fault_false_matches_default():
        a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
        b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
        if a != b:
            return False, "render_panel(source_fault=False) differs from the default call"
        return True, ""
    check("render_panel(..., source_fault=False) is byte-identical to the same call without the argument", _source_fault_false_matches_default)

    # 67. render_panel(..., source_fault=True) differs from the same call
    # with the flag false - the badge is genuinely drawn.
    def _source_fault_true_differs_from_false():
        a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
        b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=True)
        if a == b:
            return False, "render_panel(source_fault=True) is byte-identical to source_fault=False - the badge is not actually drawn"
        return True, ""
    check("render_panel(..., source_fault=True) differs from the same call with the flag false", _source_fault_true_differs_from_false)

    # 68. The fault badge is drawn on the active canvas and on the empty
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

    # 69. The badge caption is absent from a normal render (source_fault
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

    # 70. _assert_legal_palette() (run internally by build_canvas()) still
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

    # 71. A fault-badged departing render still satisfies
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

    # 72. The badge's bounding box stays inside the drawn frame.
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

    # 73. Code-review WR-01: the badge caption is an active-state text role
    # like any other and must resolve its weight from the active theme, not
    # hardcode Bold - the same per-theme font-path spy check #24c-ii already
    # uses, now with source_fault=True so draw_source_fault_badge() is
    # actually exercised (it never was before this check existed).
    def _badge_caption_uses_its_theme_declared_weight():
        for theme_id in render.device_config.THEME_IDS:
            requested_paths = _spy_requested_font_paths_with_fault(theme_id)
            if not requested_paths:
                return False, "%r: no font was requested at all - the spy did not capture anything" % (theme_id,)
            declared_weight = render.device_config.theme_weight(theme_id)
            wrong_suffix = "PTSerif-Regular.ttf" if declared_weight == "bold" else "PTSerif-Bold.ttf"
            wrong_hits = [p for p in requested_paths if p.endswith(wrong_suffix)]
            if wrong_hits:
                return False, "%r (declared weight %r): the fault badge requested %s %d time(s) - expected zero: %r" % (
                    theme_id, declared_weight, wrong_suffix, len(wrong_hits), wrong_hits)
        return True, ""
    check(
        "the source-fault badge's caption respects its theme's declared weight, same as every other active-state "
        "role (code-review WR-01)",
        _badge_caption_uses_its_theme_declared_weight,
    )

    # 74. Code-review WR-02: a zero-length ImageDraw.line() paints exactly
    # one pixel regardless of `width` - Pillow does not expand a degenerate
    # segment - so the exclamation mark's dot must be drawn as a small
    # filled area (multiple pixels), not a single point. Uses the badge's
    # own returned bbox (`left` = combined_bbox[0]) rather than duplicating
    # its internal caption-width measurement.
    def _badge_exclamation_dot_paints_more_than_one_pixel():
        canvas = panel_format.new_canvas(IDX_BLUE)
        badge_bbox = render.draw_source_fault_badge(canvas, IDX_WHITE)
        left = badge_bbox[0]
        frame_inset = round(render.WIDTH * render.FRAME_INSET_FRAC)
        frame_bottom = render.HEIGHT - frame_inset
        bottom = frame_bottom - render.MARGIN // 2
        top = bottom - render.SOURCE_FAULT_GLYPH_PX
        dot_y = round(top + render.SOURCE_FAULT_GLYPH_PX * 0.8)
        stroke_x = round(left + render.SOURCE_FAULT_GLYPH_PX / 2)
        pixels = canvas.load()
        count = sum(
            1
            for dx in range(-3, 4)
            for dy in range(-3, 4)
            if pixels[stroke_x + dx, dot_y + dy] == IDX_WHITE
        )
        if count <= 1:
            return False, (
                "the exclamation dot painted only %d ink pixel(s) around (%d, %d) - expected a visible multi-pixel "
                "dot, not a single point (code-review WR-02)" % (count, stroke_x, dot_y)
            )
        return True, ""
    check(
        "the source-fault badge's exclamation-mark dot paints a visible multi-pixel area, not a single point "
        "(code-review WR-02)",
        _badge_exclamation_dot_paints_more_than_one_pixel,
    )

    # 73. All three runway ids combined with the single registered theme id
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

    # 74. The D-26 outline must be genuinely absent from a REAL build_canvas()
    # render - not just absent from a throwaway canvas draw_frame() is called
    # on directly (that's checks 16/70's job). Sample points are derived from
    # FRAME_INSET_FRAC/panel_format.WIDTH/HEIGHT, never hardcoded pixel
    # literals, so a future inset change can never make this check silently
    # vacuous. Every probe must be one of the state's own background index or
    # the dither.dithered_state_background() White speckle mixed into it
    # (Phase 7 07-01: the flat fill became a dithered lighten-toward-White
    # blend after the developer found it too dark on real glass) - draw_frame()
    # is never called on this path, so no third index can legitimately appear
    # here; that remains the strong claim this check makes.
    def _no_frame_outline_on_real_active_renders():
        for state in ("departing", "arriving"):
            canvas = render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE)
            inset = round(panel_format.WIDTH * render.FRAME_INSET_FRAC)
            expected = render.state_background_index(state)
            allowed = {expected, panel_format.IDX_WHITE}
            points = [
                (panel_format.WIDTH // 2, inset),
                (panel_format.WIDTH // 2, inset + 1),
                (inset, panel_format.HEIGHT // 2),
                (panel_format.WIDTH - inset, panel_format.HEIGHT // 2),
                (panel_format.WIDTH // 2, panel_format.HEIGHT - inset),
                (inset, inset),
                (panel_format.WIDTH - inset, panel_format.HEIGHT - inset),
            ]
            for point in points:
                sample = canvas.getpixel(point)
                if sample not in allowed:
                    return False, (
                        "state=%r point=%r read index %r, expected one of %r (former D-26 outline band)"
                        % (state, point, sample, allowed)
                    )
        return True, ""
    check(
        "the D-26 outline is genuinely absent from a real build_canvas() render - every sampled point on the "
        "former frame band reads the state's own background index or its dithered White speckle, in both active states",
        _no_frame_outline_on_real_active_renders,
    )

    # 75. Phase 7 07-01 (D-04): --airline and --city reach the rendered
    # captions via render.main()'s CLI, following _TextSpy's monkeypatch
    # technique rather than rendering to a scratch canvas and comparing pixels.
    def _cli_airline_and_city_flags_reach_captions():
        preview_fh = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        preview_fh.close()
        with _TextSpy(render) as spy:
            rc = render.main([
                "--state", "departing", "--callsign", "AFR56XX",
                "--airline", "Test Airline Override Name",
                "--city", "Test City Override Name",
                "--preview", preview_fh.name,
            ])
        if rc != 0:
            return False, "render.main() exited %r, expected 0" % (rc,)
        texts = [text for text, _xy, _anchor in spy.calls]
        if not any("Test City Override Name" in t for t in texts):
            return False, "--city override text not found in any drawn text: %r" % (texts,)
        if not any("Test Airline Override Name" in t for t in texts):
            return False, "--airline override text not found in any drawn text: %r" % (texts,)
        return True, ""
    check(
        "--airline/--city CLI flags reach the rendered captions (render.main(), D-04)",
        _cli_airline_and_city_flags_reach_captions,
    )

    # 76. --no-route continues to win over --airline/--city when both are
    # given - "Unknown flight" (line 1, D-10 tier 4) and
    # ROUTE_FALLBACK_TEXT (line 2) render instead of either override, and
    # the raw callsign never appears (D-08).
    def _cli_no_route_wins_over_airline_and_city():
        preview_fh = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        preview_fh.close()
        with _TextSpy(render) as spy:
            rc = render.main([
                "--state", "departing", "--callsign", "AFR56XX",
                "--airline", "Should Not Appear Airline",
                "--city", "Should Not Appear City",
                "--no-route", "--preview", preview_fh.name,
            ])
        if rc != 0:
            return False, "render.main() exited %r, expected 0" % (rc,)
        texts = [text for text, _xy, _anchor in spy.calls]
        if any("Should Not Appear" in t for t in texts):
            return False, "--no-route did not win over --airline/--city overrides: %r" % (texts,)
        if "Unknown flight" not in texts:
            return False, "expected 'Unknown flight' with --no-route in effect (D-10 tier 4), got: %r" % (texts,)
        if render.ROUTE_FALLBACK_TEXT not in texts:
            return False, "expected ROUTE_FALLBACK_TEXT with --no-route in effect, got: %r" % (texts,)
        if "AFR56XX" in texts:
            return False, "the raw callsign 'AFR56XX' must never appear with --no-route in effect (D-08), got: %r" % (texts,)
        return True, ""
    check(
        "--no-route still overrides --airline/--city ('Unknown flight', ROUTE_FALLBACK_TEXT, never the raw "
        "callsign)",
        _cli_no_route_wins_over_airline_and_city,
    )

    # 77. --calibration-preview writes exactly one file (palette-swatches.png)
    # into the given directory and exits 0 without rendering any panel.
    def _calibration_preview_writes_exactly_one_file():
        tmp_dir = tempfile.mkdtemp()
        rc = render.main(["--calibration-preview", tmp_dir])
        if rc != 0:
            return False, "render.main(['--calibration-preview', ...]) exited %r, expected 0" % (rc,)
        written = sorted(os.listdir(tmp_dir))
        if written != ["palette-swatches.png"]:
            return False, "expected exactly one file 'palette-swatches.png' in %r, got %r" % (tmp_dir, written)
        return True, ""
    check(
        "--calibration-preview writes exactly one file (palette-swatches.png, D-13)",
        _calibration_preview_writes_exactly_one_file,
    )

    # 78. Combining a route override (--airline/--city/--no-route) with --out
    # prints the reminder line naming skypane-poll.timer (Phase 8 08-05: the
    # unit was previously misnamed after a pre-rename service) as the unit
    # that must be restarted afterward (T-07-01-01).
    def _synthetic_reminder_printed_when_override_combined_with_out():
        out_fh = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
        out_fh.close()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = render.main([
                "--state", "departing", "--callsign", "AFR56XX", "--no-route", "--out", out_fh.name,
            ])
        if rc != 0:
            return False, "render.main() exited %r, expected 0" % (rc,)
        stdout_text = buf.getvalue()
        if "skypane-poll.timer" not in stdout_text:
            return False, "expected a synthetic-panel reminder naming skypane-poll.timer, got stdout: %r" % (stdout_text,)
        return True, ""
    check(
        "combining --no-route with --out prints the skypane-poll.timer restart reminder (T-07-01-01)",
        _synthetic_reminder_printed_when_override_combined_with_out,
    )

    # --- Phase 8 08-04 Task 3: every content-ladder tier reachable from the
    # CLI, so plan 08-06's on-glass session is one copy-pasteable command
    # per tier. -------------------------------------------------------------

    # 79. The default preview (no forcing flags) draws a tier-1 line
    # containing the preview route's real identifier.
    def _cli_default_preview_draws_tier1_with_identifier():
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        with _TextSpy(render) as spy:
            rc = render.main(["--state", "departing", "--preview", tmp.name])
        if rc != 0:
            return False, "render.main() exited %r, expected 0" % (rc,)
        texts = [t for t, _xy, _a in spy.calls]
        expected = "%s to %s" % (render._PREVIEW_ROUTE["callsign_iata"], render._PREVIEW_ROUTE["destination_city"])
        if expected not in texts:
            return False, "expected the default preview's tier-1 line %r among the text draws, got %r" % (expected, texts)
        return True, ""
    check(
        "the default CLI preview (no forcing flags) draws a tier-1 line containing the preview route's real "
        "identifier (D-10 tier 1)",
        _cli_default_preview_draws_tier1_with_identifier,
    )

    # 80. --no-identifier forces the default preview into tier 2.
    def _cli_no_identifier_flag_forces_tier2():
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        with _TextSpy(render) as spy:
            rc = render.main(["--state", "departing", "--no-identifier", "--preview", tmp.name])
        if rc != 0:
            return False, "render.main() exited %r, expected 0" % (rc,)
        texts = [t for t, _xy, _a in spy.calls]
        expected = "To %s" % (render._PREVIEW_ROUTE["destination_city"],)
        if expected not in texts:
            return False, "expected --no-identifier's tier-2 line %r among the text draws, got %r" % (expected, texts)
        if any(render._PREVIEW_ROUTE["callsign_iata"] in t for t in texts):
            return False, "the preview route's identifier leaked into a drawn text despite --no-identifier: %r" % (texts,)
        return True, ""
    check(
        "--no-identifier forces the default preview into tier 2 (title-case direction + city, no identifier) "
        "(D-10 tier 2)",
        _cli_no_identifier_flag_forces_tier2,
    )

    # 81. --no-identifier combined with --no-route still produces tier 4,
    # and combined with --preview-airline-only still produces tier 3 with
    # no line 1 - the two no-op interactions, pinned so a later refactor
    # cannot make them raise.
    def _cli_no_identifier_is_a_noop_with_no_route_and_airline_only():
        tmp1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp1.close()
        tmp2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp2.close()
        with _TextSpy(render) as spy_no_route:
            rc1 = render.main(["--state", "departing", "--no-identifier", "--no-route", "--preview", tmp1.name])
        with _TextSpy(render) as spy_airline_only:
            rc2 = render.main(["--state", "departing", "--no-identifier", "--preview-airline-only", "--preview", tmp2.name])
        if rc1 != 0 or rc2 != 0:
            return False, "render.main() exited %r/%r, expected 0/0" % (rc1, rc2)
        texts_no_route = [t for t, _xy, _a in spy_no_route.calls]
        texts_airline_only = [t for t, _xy, _a in spy_airline_only.calls]
        if "Unknown flight" not in texts_no_route:
            return False, "expected tier-4 'Unknown flight' with --no-identifier + --no-route (a no-op combo), got %r" % (texts_no_route,)
        if "" in texts_airline_only:
            return False, "an empty-string draw call was made with --no-identifier + --preview-airline-only: %r" % (texts_airline_only,)
        if render._PREVIEW_ROUTE["airline_name"] not in texts_airline_only:
            return False, (
                "expected tier-3 line 2 (airline name alone) with --no-identifier + --preview-airline-only "
                "(a no-op combo), got %r" % (texts_airline_only,)
            )
        return True, ""
    check(
        "--no-identifier combined with --no-route still produces tier 4, and combined with --preview-airline-only "
        "still produces tier 3 with no line 1 - both are no-ops (D-10)",
        _cli_no_identifier_is_a_noop_with_no_route_and_airline_only,
    )

    # 82. The CLI-level D-08 counterpart of Task 1's library-level guard: no
    # CLI path at any of the four tiers draws the raw callsign.
    def _cli_never_draws_raw_callsign_across_all_four_tiers():
        combos = [
            [],  # tier 1, default
            ["--no-identifier"],  # tier 2
            ["--preview-airline-only"],  # tier 3
            ["--no-route"],  # tier 4
        ]
        for extra in combos:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            with _TextSpy(render) as spy:
                rc = render.main(["--state", "departing", "--callsign", "DISTINCTCLI99"] + extra + ["--preview", tmp.name])
            if rc != 0:
                return False, "render.main() exited %r for flags %r, expected 0" % (rc, extra)
            texts = [t for t, _xy, _a in spy.calls]
            if any("DISTINCTCLI99" in t for t in texts):
                return False, "the raw callsign 'DISTINCTCLI99' leaked into a drawn text with flags %r (D-08): %r" % (extra, texts)
        return True, ""
    check(
        "no CLI path at any of the four content-ladder tiers draws the raw callsign passed via --callsign (D-08 "
        "CLI-level guard)",
        _cli_never_draws_raw_callsign_across_all_four_tiers,
    )

    # --- Phase 8 08-05 Task 1: D-12's 20px optical offset (introduced by
    # 08-04), spot-checked across a deliberately diverse illustration sample
    # rather than just the single Air France / Vueling pair it was tuned
    # against - 08-CONTEXT.md D-12's own final bullet asks for exactly this.
    # ------------------------------------------------------------------
    #
    # Six airline names, each confirmed (by reading illustrations.py's
    # `_ILLUSTRATION_TARGETS`/`_TYPE_SHAPE_BUCKETS` tables before hardcoding,
    # not guessed) to resolve via `select_illustration()`'s Tier 2 (airline
    # primary, no `aircraft_type` given) to a distinct vendored file with a
    # genuinely different airframe silhouette:
    #
    #   Air France           -> air-france.png           narrowbody jet (A320/B737 baseline)
    #   Vueling Airlines     -> vueling-airlines.png      narrowbody jet (A320 family)
    #   Chalair Aviation     -> chalair-aviation.png      turboprop (ATR72)
    #   Twin Jet             -> twin-jet.png              small twin turboprop (Beechcraft 1900D)
    #   LOT Polish Airlines  -> lot-polish-airlines.png   regional jet (Embraer E-Jet family)
    #   Air Caraïbes         -> air-caraibes.png          widebody jet (A350 family, primary)
    OFFSET_SPREAD_AIRLINES = (
        ("Air France", "air-france.png", "narrowbody jet (A320/B737 baseline)"),
        ("Vueling Airlines", "vueling-airlines.png", "narrowbody jet (A320 family)"),
        ("Chalair Aviation", "chalair-aviation.png", "turboprop (ATR72)"),
        ("Twin Jet", "twin-jet.png", "small twin turboprop (Beechcraft 1900D)"),
        ("LOT Polish Airlines", "lot-polish-airlines.png", "regional jet (Embraer E-Jet family)"),
        ("Air Caraïbes", "air-caraibes.png", "widebody jet (A350 family, primary)"),
    )

    # 83. For each sampled airline: both previous-card lines share one
    # anchor x equal to that aircraft's measured opaque right edge minus
    # PREVIOUS_TEXT_LEFT_OFFSET_PX (written against the constant, never a
    # literal); neither line's bbox crosses SAFE_BOX's left edge (the real
    # width-budget risk the offset introduces - narrower `available_width`
    # for `fit_text_size()`, not just the looser whole-canvas guard
    # `_assert_within_canvas()` already enforces); and the render completes
    # without raising. Also records each file's right-padding
    # (`rect[2] - content[2]`) so a genuine outlier - if one exists - is
    # named rather than silently absorbed.
    def _previous_card_optical_offset_holds_across_diverse_illustration_sample():
        paddings = {}
        for airline_name, expected_filename, _airframe in OFFSET_SPREAD_AIRLINES:
            route = dict(TEST_PREVIOUS_ROUTE)
            route["airline_name"] = airline_name
            resolved = illustrations.select_illustration(route, None)
            if resolved is None or os.path.basename(resolved) != expected_filename:
                return False, (
                    "airline %r resolved to %r, expected %r - the sample no longer resolves to the "
                    "documented fixed file, this check must be re-pointed" % (
                        airline_name, os.path.basename(resolved) if resolved else None, expected_filename,
                    )
                )
            with _PlacementSpy(render) as placements:
                with _TextBBoxSpy(render) as bboxes:
                    render.build_canvas(
                        TEST_FLIGHT, "departing", route=TEST_ROUTE,
                        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=route,
                        previous_state="arriving",
                    )
            if len(placements.placements) != 2:
                return False, "airline %r: expected 2 illustration placements, got %d" % (
                    airline_name, len(placements.placements),
                )
            _main_placement, prev_placement = placements.placements
            paddings[airline_name] = prev_placement.rect[2] - prev_placement.content[2]

            prev_line1 = "%s from %s" % (route["callsign_iata"], route["origin_city"])
            type_label = render._TYPE_DISPLAY_LABELS[TEST_PREVIOUS_FLIGHT["aircraft_type"]]
            prev_line2 = "%s · %s" % (route["airline_name"], type_label)
            b1 = next((bb for t, _xy, _a, bb in bboxes.calls if t == prev_line1), None)
            b2 = next((bb for t, _xy, _a, bb in bboxes.calls if t == prev_line2), None)
            if b1 is None or b2 is None:
                return False, "airline %r: expected both previous-card lines drawn, got %r" % (
                    airline_name, [t for t, _xy, _a, _bb in bboxes.calls],
                )
            if b1[2] != b2[2]:
                return False, "airline %r: previous card's two lines anchor at different x (%d vs %d)" % (
                    airline_name, b1[2], b2[2],
                )
            expected_x = prev_placement.content[2] - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
            if b1[2] != expected_x:
                return False, (
                    "airline %r: shared anchor x=%d, expected the aircraft's measured opaque right edge minus "
                    "PREVIOUS_TEXT_LEFT_OFFSET_PX = %d" % (airline_name, b1[2], expected_x)
                )
            safe_left = render.SAFE_BOX[0]
            if b1[0] < safe_left or b2[0] < safe_left:
                return False, (
                    "airline %r: a previous-card line's bbox (line1=%r, line2=%r) crosses the safe box's left "
                    "edge (x=%d) - the offset narrowed fit_text_size()'s width budget past what this text needs"
                    % (airline_name, b1, b2, safe_left)
                )
        print(
            "    (D-12 spread: previous-card right-padding by file %r)" % (
                {name: paddings[name] for name, _f, _a in OFFSET_SPREAD_AIRLINES},
            )
        )
        spread = max(paddings.values()) - min(paddings.values())
        outlier = max(paddings, key=paddings.get)
        print(
            "    (D-12 verdict: right-padding spread is %dpx across the sample, widest at %r (%dpx) - "
            "no per-file outlier large enough to threaten the anchor/safe-box invariants above, both of "
            "which held for every sampled file)" % (spread, outlier, paddings[outlier])
        )
        return True, ""
    check(
        "the previous card's D-12 optical offset holds its shared-anchor and safe-box invariants across six "
        "airline illustrations with deliberately different airframe silhouettes (narrowbody x2, turboprop, "
        "small twin, regional jet, widebody) - not just the single pair it was tuned against",
        _previous_card_optical_offset_holds_across_diverse_illustration_sample,
    )

    # 102. Resurrected tracking helpers: constant value + the original
    # commit's public/private naming split (draw_tracked_text is public,
    # _tracked_text_width/_tracked_text_bbox are private).
    def _label_tracking_constant_and_helpers_present():
        if render.LABEL_TRACKING_PX != 6:
            return False, "render.LABEL_TRACKING_PX = %r, expected 6" % (render.LABEL_TRACKING_PX,)
        if not hasattr(render, "draw_tracked_text"):
            return False, "render.draw_tracked_text is missing (expected public, no leading underscore)"
        if not hasattr(render, "_tracked_text_width"):
            return False, "render._tracked_text_width is missing (expected private)"
        if not hasattr(render, "_tracked_text_bbox"):
            return False, "render._tracked_text_bbox is missing (expected private)"
        if hasattr(render, "_draw_tracked_text"):
            return False, "render._draw_tracked_text should not exist - draw_tracked_text is public"
        return True, ""
    check(
        "LABEL_TRACKING_PX == 6 and draw_tracked_text()/_tracked_text_width()/_tracked_text_bbox() exist with "
        "the original commit's public/private naming split",
        _label_tracking_constant_and_helpers_present,
    )

    # 103. _tracked_text_width() arithmetic: empty / single-char / multi-char
    # / zero-tracking, derived from font.getlength() rather than hardcoded
    # pixel numbers.
    def _tracked_text_width_arithmetic():
        font = render._role_font(render.TOP_TAG_FONT, "bold")
        empty = render._tracked_text_width(font, "", 6)
        if empty != 0.0:
            return False, "_tracked_text_width(font, '', 6) = %r, expected 0.0" % (empty,)
        single = render._tracked_text_width(font, "A", 6)
        expected_single = font.getlength("A")
        if single != expected_single:
            return False, (
                "_tracked_text_width(font, 'A', 6) = %r, expected font.getlength('A') = %r "
                "(a single glyph carries no trailing tracking)" % (single, expected_single)
            )
        text = "ORY"
        expected_multi = sum(font.getlength(ch) for ch in text) + 6 * (len(text) - 1)
        got_multi = render._tracked_text_width(font, text, 6)
        if got_multi != expected_multi:
            return False, "_tracked_text_width(font, %r, 6) = %r, expected %r" % (text, got_multi, expected_multi)
        expected_zero = sum(font.getlength(ch) for ch in text)
        got_zero = render._tracked_text_width(font, text, 0)
        if got_zero != expected_zero:
            return False, (
                "_tracked_text_width(font, %r, 0) = %r, expected plain summed advance %r"
                % (text, got_zero, expected_zero)
            )
        return True, ""
    check(
        "_tracked_text_width() arithmetic holds for empty/single-char/multi-char/zero-tracking, derived from "
        "font.getlength() rather than hardcoded pixel numbers",
        _tracked_text_width_arithmetic,
    )

    # 104. draw_tracked_text(): one text draw per character, each anchor='la',
    # inter-glyph advance == font.getlength(previous_char) + tracking, return
    # value is the x immediately after the last glyph's advance.
    def _draw_tracked_text_glyph_by_glyph():
        font = render._role_font(render.TOP_TAG_FONT, "bold")
        canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
        draw = render.ImageDraw.Draw(canvas)
        text = "ORY"
        with _TextSpy(render) as spy:
            end_x = render.draw_tracked_text(draw, (100, 200), text, font, panel_format.IDX_BLACK, tracking=6)
        calls = spy.calls
        if len(calls) != len(text):
            return False, "draw_tracked_text issued %d text draws, expected %d (one per character)" % (len(calls), len(text))
        joined = "".join(c[0] for c in calls)
        if joined != text:
            return False, "joined glyph draws = %r, expected %r" % (joined, text)
        if any(a != "la" for _, _, a in calls):
            return False, "not every glyph draw used anchor='la': %r" % ([a for _, _, a in calls],)
        x = 100
        for i, ch in enumerate(text):
            expected_xy = (x, 200)
            got_xy = calls[i][1]
            if got_xy != expected_xy:
                return False, "glyph %d (%r) drawn at %r, expected %r" % (i, ch, got_xy, expected_xy)
            x += font.getlength(ch) + 6
        if end_x != x:
            return False, (
                "draw_tracked_text returned %r, expected %r (start_x + _tracked_text_width(...) + tracking)"
                % (end_x, x)
            )
        return True, ""
    check(
        "draw_tracked_text() issues one text draw per character at anchor='la', with inter-glyph advance == "
        "font.getlength(previous_char) + tracking, returning the x immediately after the last glyph's advance",
        _draw_tracked_text_glyph_by_glyph,
    )

    # 105. Inter-glyph advance: every consecutive pair of glyph origins
    # within the state-label and runway-tag runs differs by exactly
    # font.getlength(previous_char) + LABEL_TRACKING_PX, derived from the
    # real font rather than a pixel literal.
    def _top_row_inter_glyph_advance_matches_tracking():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        top_row = [(t, xy) for t, xy, _a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        label_text = render.STATE_LABEL_TEXT["departing"]
        tag_text = render.TOP_RIGHT_TAG_TEXT
        weight = render.device_config.theme_weight(render.device_config.DEFAULT_THEME_ID)
        label_font = render._role_font(render.STATE_LABEL_FONT, weight)
        tag_font = render._role_font(render.TOP_TAG_FONT, weight)
        label_glyphs = top_row[: len(label_text)]
        tag_glyphs = top_row[len(label_text): len(label_text) + len(tag_text)]
        for glyphs, text, font in ((label_glyphs, label_text, label_font), (tag_glyphs, tag_text, tag_font)):
            for i in range(1, len(glyphs)):
                prev_char = text[i - 1]
                expected_advance = font.getlength(prev_char) + render.LABEL_TRACKING_PX
                got_advance = glyphs[i][1][0] - glyphs[i - 1][1][0]
                if abs(got_advance - expected_advance) > 0.01:
                    return False, (
                        "glyph %d advance within %r run = %.3f, expected %.3f "
                        "(font.getlength(%r) + %d)" % (i, text, got_advance, expected_advance, prev_char, render.LABEL_TRACKING_PX)
                    )
        return True, ""
    check(
        "every consecutive pair of glyph origins within the state-label and runway-tag runs differs by exactly "
        "font.getlength(previous_char) + LABEL_TRACKING_PX",
        _top_row_inter_glyph_advance_matches_tracking,
    )

    # 106. Overflow sweep: every registered runway id, both active states,
    # a flat (white) and a dithered (grey) theme - _assert_within_canvas()
    # must never raise, and the computed tag start x must be >= 0. Planning
    # measured the worst case at 901 across every combination, against the
    # plan's own "sky" example theme - "sky" was retired by Phase 8's
    # 5-entry-registry work (11 pure/light themes replaced it, no "sky" id
    # remains), so "grey" (currently the bold/dithered theme, per
    # device_config.theme_weight()) is substituted here as the equivalent
    # dithered-theme leg (Rule 1: the plan's context predates that
    # retirement).
    def _top_row_tracking_stays_within_canvas_across_runways_themes_states():
        for runway_id in render.device_config.RUNWAY_IDS:
            for theme_id in ("white", "grey"):
                for state in ("departing", "arriving"):
                    render.build_canvas(
                        TEST_FLIGHT, state, route=TEST_ROUTE, runway_id=runway_id, theme_id=theme_id,
                    )
                    weight = render.device_config.theme_weight(theme_id)
                    tag_font = render._role_font(render.TOP_TAG_FONT, weight)
                    tag_text = render.runway_tag_text(runway_id)
                    tag_width = render._tracked_text_width(tag_font, tag_text, render.LABEL_TRACKING_PX)
                    tag_x = panel_format.WIDTH - render.MARGIN - tag_width
                    if tag_x < 0:
                        return False, (
                            "runway=%r theme=%r state=%r: computed tag start x = %.2f is negative"
                            % (runway_id, theme_id, state, tag_x)
                        )
        return True, ""
    check(
        "the tracked top row builds without an AssertionError and the computed tag start x is >= 0 for every "
        "registered runway id, both active states, and a flat and a dithered theme",
        _top_row_tracking_stays_within_canvas_across_runways_themes_states,
    )

    # 107. Tracking containment: for a full two-flight active render, the
    # main card's line 1, the previous card's line 1, and the source-fault
    # caption are each still captured as a single whole-string draw, and
    # the total count of single-character draws equals exactly
    # len(label_text) + len(tag_text) - tracking has not leaked into any
    # other role.
    def _tracking_confined_to_top_row_roles_only():
        with _TextSpy(render) as spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
                source_fault=True,
            )
        single_char_calls = [c for c in spy.calls if len(c[0]) == 1]
        label_text = render.STATE_LABEL_TEXT["departing"]
        tag_text = render.TOP_RIGHT_TAG_TEXT
        expected_count = len(label_text) + len(tag_text)
        if len(single_char_calls) != expected_count:
            return False, (
                "captured %d single-character draws, expected exactly %d (len(label_text) + len(tag_text))"
                % (len(single_char_calls), expected_count)
            )
        whole_string_texts = [t for t, _xy, _a in spy.calls if len(t) > 1]
        main_line1 = render._flight_line1_text(TEST_FLIGHT, "departing", TEST_ROUTE)
        if main_line1 and main_line1 not in whole_string_texts:
            return False, "main card line 1 %r not captured as a single whole-string draw" % (main_line1,)
        prev_line1 = render._flight_line1_text(TEST_PREVIOUS_FLIGHT, "arriving", TEST_PREVIOUS_ROUTE)
        if prev_line1 and prev_line1 not in whole_string_texts:
            return False, "previous card line 1 %r not captured as a single whole-string draw" % (prev_line1,)
        if render.SOURCE_FAULT_TEXT not in whole_string_texts:
            return False, "source-fault caption %r not captured as a single whole-string draw" % (render.SOURCE_FAULT_TEXT,)
        return True, ""
    check(
        "for a full two-flight active render with source_fault=True, the main card's line 1, the previous "
        "card's line 1, and the source-fault caption are each still drawn as one whole-string call, and the "
        "total single-character draw count equals exactly len(label_text) + len(tag_text)",
        _tracking_confined_to_top_row_roles_only,
    )

    # 108. Phase 9 PHASE9-1: every registered band theme's build_canvas()
    # call succeeds without exception, in both active states. Checks #58-60
    # already loop THEME_IDS generically and therefore already cover this
    # transitively - this loop exists to make band coverage explicit and
    # independently readable, and to fail loudly with the offending theme id
    # named if a band-specific regression ever slips past the generic loops.
    def _band_themes_render_without_exception():
        band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
        if not band_theme_ids:
            return False, "no band theme ids found in THEME_IDS - expected plan 09-01's 5 band entries"
        for theme_id in band_theme_ids:
            for state in ("departing", "arriving"):
                render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE, theme_id=theme_id)
        return True, ""
    check(
        "every registered band theme (PHASE9-1) renders via build_canvas() in both departing and arriving "
        "states without exception",
        _band_themes_render_without_exception,
    )

    # 109. draw_diagonal_band() paints only {IDX_WHITE, band_idx} on a fresh
    # White canvas, confined to the trapezoid region - one flat candidate
    # (IDX_BLUE, dithered=False) and one dithered candidate (IDX_GREEN,
    # dithered=True), using Image.getcolors() the same way
    # _assert_legal_palette() does internally, not a reimplementation of its
    # dominance/legality logic.
    def _draw_diagonal_band_paints_only_legal_two_colour_set():
        for band_idx, dithered in ((IDX_BLUE, False), (IDX_GREEN, True)):
            canvas = panel_format.new_canvas(IDX_WHITE)
            render.draw_diagonal_band(canvas, band_idx, dithered=dithered)
            colors = {value for _count, value in canvas.getcolors()}
            if not colors <= {IDX_WHITE, band_idx}:
                return False, (
                    "draw_diagonal_band(band_idx=%r, dithered=%r) painted colours %r, expected a subset of "
                    "{IDX_WHITE, %r}" % (band_idx, dithered, sorted(colors), band_idx)
                )
            if band_idx not in colors:
                return False, "draw_diagonal_band(band_idx=%r, dithered=%r) painted no %r pixels at all" % (
                    band_idx, dithered, band_idx
                )
        return True, ""
    check(
        "draw_diagonal_band() paints only {IDX_WHITE, band_idx} on a fresh White canvas, flat and dithered",
        _draw_diagonal_band_paints_only_legal_two_colour_set,
    )

    # 110. Band-theme top labels are genuinely split: build a band-theme
    # canvas and reconstruct the top-row glyph run via _TextSpy, the same
    # idiom check #65 uses for runway-tag coverage. The expected strings are
    # derived from runway_tag_text()/STATE_LABEL_TEXT/_BAND_TOP_LABEL_DIRECTION
    # in the check itself, partitioned on " · " - never a hardcoded literal
    # duplicating the production split logic in two places.
    def _band_theme_top_labels_are_split():
        band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
        if not band_theme_ids:
            return False, "no band theme ids found in THEME_IDS"
        theme_id = band_theme_ids[0]
        full_tag = render.runway_tag_text()
        airport_code, _sep, runway_part = full_tag.partition(" · ")
        expected_label = "%s %s %s" % (
            render.STATE_LABEL_TEXT["departing"], render._BAND_TOP_LABEL_DIRECTION["departing"], airport_code
        )
        expected_tag = runway_part
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
        top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        label_glyphs = top_row[: len(expected_label)]
        tag_glyphs = top_row[len(expected_label): len(expected_label) + len(expected_tag)]
        joined_label = "".join(t for t, _xy, _a in label_glyphs)
        joined_tag = "".join(t for t, _xy, _a in tag_glyphs)
        if joined_label != expected_label:
            return False, "reconstructed band-theme %r label = %r, expected %r" % (theme_id, joined_label, expected_label)
        if joined_tag != expected_tag:
            return False, "reconstructed band-theme %r tag = %r, expected %r" % (theme_id, joined_tag, expected_tag)
        return True, ""
    check(
        "a band theme's top labels are genuinely split into a merged state-label/airport-code run "
        "(e.g. 'DEPARTING FROM ORY') and a standalone runway-tag run (e.g. 'RWY 3'), both derived from "
        "runway_tag_text().partition(' · ') (PHASE9-3)",
        _band_theme_top_labels_are_split,
    )

    # 111. Non-band-theme top labels are unaffected. Two layers: (a) calls
    # `draw_top_labels()` DIRECTLY with no `band_theme` argument at all, so
    # this check genuinely exercises the parameter's own default rather than
    # `_build_active_canvas()`'s explicit `band_theme=is_band_theme` wiring
    # (which always passes the argument and would mask a wrong default) -
    # (b) the same _TextSpy reconstruction, run through build_canvas() with
    # the default theme (white), proving the wiring itself resolves to
    # unsplit for a real non-band theme too. Both must reconstruct exactly
    # STATE_LABEL_TEXT["departing"] on the left and the FULL
    # runway_tag_text() string on the right.
    def _non_band_theme_top_labels_are_unsplit():
        label_text = render.STATE_LABEL_TEXT["departing"]
        full_tag = render.runway_tag_text()

        default_weight = render.device_config.theme_weight(render.device_config.DEFAULT_THEME_ID)
        canvas = panel_format.new_canvas(IDX_WHITE)
        with _TextSpy(render) as direct_spy:
            # No band_theme kwarg at all - this is what actually proves the
            # parameter's default is False, not just that callers pass False.
            render.draw_top_labels(canvas, "departing", IDX_BLACK, IDX_WHITE, default_weight)
        direct_top_row = [(t, xy, a) for t, xy, a in direct_spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        direct_label = "".join(t for t, _xy, _a in direct_top_row[: len(label_text)])
        direct_tag = "".join(t for t, _xy, _a in direct_top_row[len(label_text): len(label_text) + len(full_tag)])
        if direct_label != label_text:
            return False, "draw_top_labels() with no band_theme arg: label = %r, expected unsplit %r" % (direct_label, label_text)
        if direct_tag != full_tag:
            return False, "draw_top_labels() with no band_theme arg: tag = %r, expected the FULL unsplit tag %r" % (direct_tag, full_tag)

        with _TextSpy(render) as wired_spy:
            render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=render.device_config.DEFAULT_THEME_ID
            )
        wired_top_row = [(t, xy, a) for t, xy, a in wired_spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
        wired_label = "".join(t for t, _xy, _a in wired_top_row[: len(label_text)])
        wired_tag = "".join(t for t, _xy, _a in wired_top_row[len(label_text): len(label_text) + len(full_tag)])
        if wired_label != label_text:
            return False, "build_canvas(theme_id='white') label = %r, expected unsplit %r" % (wired_label, label_text)
        if wired_tag != full_tag:
            return False, "build_canvas(theme_id='white') tag = %r, expected the FULL unsplit tag %r" % (wired_tag, full_tag)
        return True, ""
    check(
        "a non-band theme's (white, the default) top labels remain exactly STATE_LABEL_TEXT and the FULL "
        "runway tag, unsplit - both draw_top_labels()'s own default (called with no band_theme argument) and "
        "_build_active_canvas()'s wiring genuinely preserve today's behaviour",
        _non_band_theme_top_labels_are_unsplit,
    )

    # 112. Non-band themes are pixel-identical to before this phase: the
    # default (White) canvas's getdata() length/content and getcolors() set,
    # each computed fresh every run (never a hardcoded pixel dump), match
    # between an explicit theme_id="white" call and the no-theme-id default
    # call - strengthening check #55's identity check into an explicit,
    # named "the band port did not touch the default path" regression guard,
    # plus a structural confirmation that "white" itself is not a band theme.
    def _default_theme_canvas_unchanged_by_band_port():
        if render.device_config.theme_is_band("white"):
            return False, "'white' unexpectedly reports as a band theme - the default render path would be touched"
        default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        white_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="white")
        default_data = list(default_canvas.getdata())
        white_data = list(white_canvas.getdata())
        if len(default_data) != len(white_data):
            return False, "default/white canvas getdata() lengths differ: %d vs %d" % (len(default_data), len(white_data))
        if default_data != white_data:
            return False, "default/white canvas pixel data differs - the band port must not touch the default path"
        default_colors = {v for _n, v in default_canvas.getcolors()}
        white_colors = {v for _n, v in white_canvas.getcolors()}
        if default_colors != white_colors:
            return False, "default/white canvas colour sets differ: %r vs %r" % (sorted(default_colors), sorted(white_colors))
        return True, ""
    check(
        "the default (white) theme's canvas is byte-identical to before this phase (getdata()/getcolors() "
        "computed fresh, and 'white' itself is confirmed not a band theme)",
        _default_theme_canvas_unchanged_by_band_port,
    )

    # 113. Plan 09-03 non-band regression, both text blocks: a full
    # two-flight render, for every one of the 11 pre-band theme ids, is
    # pixel-identical whether `_build_active_canvas()`'s normal
    # `band_idx=band_idx` wiring runs (always `None` for a non-band theme)
    # or `draw_main_text_block()`/`draw_previous_text_block()` are called
    # with NO `band_idx` argument at all (their own default). Proves the
    # `band_idx=None` branch is genuinely a no-op wrapper around the
    # pre-this-plan body, using the real production illustration-placement
    # pipeline (via build_canvas() itself) rather than a hand-duplicated
    # reimplementation that could silently drift from it.
    def _non_band_text_blocks_unaffected_by_band_idx_kwarg():
        non_band_ids = [t for t in render.device_config.THEME_IDS if not render.device_config.theme_is_band(t)]
        if len(non_band_ids) != 11:
            return False, "expected exactly 11 pre-band theme ids, found %d: %r" % (len(non_band_ids), non_band_ids)

        orig_main = render.draw_main_text_block
        orig_prev = render.draw_previous_text_block

        def _main_no_band_kwarg(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight, band_idx=None):
            return orig_main(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight)

        def _prev_no_band_kwarg(canvas, flight, state, route, prev_placement, ink_idx, bg_idx, weight, band_idx=None):
            return orig_prev(canvas, flight, state, route, prev_placement, ink_idx, bg_idx, weight)

        for theme_id in non_band_ids:
            canvas_wired = render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
                theme_id=theme_id,
            )
            render.draw_main_text_block = _main_no_band_kwarg
            render.draw_previous_text_block = _prev_no_band_kwarg
            try:
                canvas_unwired = render.build_canvas(
                    TEST_FLIGHT, "departing", route=TEST_ROUTE,
                    previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
                    theme_id=theme_id,
                )
            finally:
                render.draw_main_text_block = orig_main
                render.draw_previous_text_block = orig_prev
            if list(canvas_wired.getdata()) != list(canvas_unwired.getdata()):
                return False, (
                    "theme %r: build_canvas() output differs when draw_main_text_block()/draw_previous_text_block() "
                    "are called with no band_idx argument at all vs. _build_active_canvas()'s normal band_idx=band_idx "
                    "wiring - the band_idx=None branch is not a byte-identical no-op wrapper" % (theme_id,)
                )
        return True, ""
    check(
        "every one of the 11 pre-band themes' full two-flight render is pixel-identical whether "
        "_build_active_canvas()'s band_idx=band_idx wiring runs (always None) or draw_main_text_block()/"
        "draw_previous_text_block() are called with no band_idx argument at all (PHASE9-4/PHASE9-6 regression guard)",
        _non_band_text_blocks_unaffected_by_band_idx_kwarg,
    )

    # 114. Tier-split content reuse, main card: for a tier-1 route
    # (TEST_ROUTE, real identifier + city), the big-number draw's text
    # equals route["callsign_iata"] exactly and the tracked route line -
    # reconstructed from consecutive single-character glyph draws not on
    # the top row (y != MARGIN), the same idiom check #65/#110 already use
    # for the top row itself - equals _flight_line1_text()'s real output
    # with the identifier prefix stripped and upper-cased, computed fresh
    # in this check. For a tier-3 route (enrich.airline_only_route(), no
    # identifier/city), no number and no tracked-route glyphs are drawn at
    # all - only the promoted airline·type line, as a single whole-string
    # draw.
    def _band_main_card_tier_split_reuses_real_content():
        import server.plane.enrich as enrich

        theme_id = "band_blue"
        identifier = TEST_ROUTE["callsign_iata"]
        line1_full = render._flight_line1_text(TEST_FLIGHT, "departing", TEST_ROUTE)
        expected_tracked = line1_full[len(identifier) + 1:].upper()

        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
        number_draws = [c for c in spy.calls if c[0] == identifier and c[2] == "ma"]
        if not number_draws:
            return False, "band main card tier-1: no whole-string 'ma' draw of the identifier %r found" % (identifier,)
        tracked_glyphs = [c for c in spy.calls if len(c[0]) == 1 and c[1][1] != render.MARGIN]
        joined_tracked = "".join(t for t, _xy, _a in tracked_glyphs)
        if joined_tracked != expected_tracked:
            return False, (
                "band main card tier-1 tracked route line reconstructed as %r, expected %r"
                % (joined_tracked, expected_tracked)
            )

        tier3_route = enrich.airline_only_route("Band Tier Three Airline")
        tier3_flight = {"hex": "abcdef", "callsign": "XYZ999", "aircraft_type": "A320"}
        line1_full_tier3 = render._flight_line1_text(tier3_flight, "departing", tier3_route)
        if line1_full_tier3 != "":
            return False, "expected fixture to hit D-10 tier 3 (line 1 == ''), got %r" % (line1_full_tier3,)
        line2_full_tier3 = render._flight_line2_text(tier3_route, tier3_flight["aircraft_type"])
        with _TextSpy(render) as spy3:
            render.build_canvas(tier3_flight, "departing", route=tier3_route, theme_id=theme_id)
        tier3_tracked_glyphs = [c for c in spy3.calls if len(c[0]) == 1 and c[1][1] != render.MARGIN]
        if tier3_tracked_glyphs:
            return False, "band main card tier-3 render unexpectedly drew tracked-route glyphs: %r" % (tier3_tracked_glyphs,)
        whole_strings_tier3 = [t for t, _xy, _a in spy3.calls if len(t) > 1]
        if line2_full_tier3 not in whole_strings_tier3:
            return False, (
                "band main card tier-3 render did not draw the promoted airline·type line %r as a whole string"
                % (line2_full_tier3,)
            )
        return True, ""
    check(
        "a band theme's main card draws the big-number line as route['callsign_iata'] verbatim and the tracked "
        "route line as _flight_line1_text()'s real remainder, upper-cased (tier 1); and draws only the promoted "
        "airline·type line, with no number/dash/tracked-route draw at all, for a tier-3 (airline-only) route "
        "(PHASE9-4)",
        _band_main_card_tier_split_reuses_real_content,
    )

    # 115. Centring-once regression guard (round-15 bug, PHASE9-4): for a
    # tier-1 band render, every anchor="ma" draw call below the top row
    # (the number line and the promoted/plain airline·type line both use
    # this anchor) must land on the SAME x-coordinate - proving center_x
    # was computed once, at the block's top, and reused for every line,
    # never recomputed per line. Manually verified during this plan's own
    # development (not re-run automatically here) that reintroducing the
    # round-12 per-line recompute inside the plain_text branch alone makes
    # this check fail, and reverting makes it pass again.
    def _band_center_x_computed_once_not_recomputed_per_line():
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="band_blue")
        ma_draws = [c for c in spy.calls if c[2] == "ma" and c[1][1] != render.MARGIN]
        if len(ma_draws) < 2:
            return False, "expected at least 2 anchor='ma' draws (number line + airline·type line), found %d" % (len(ma_draws),)
        xs = {xy[0] for _t, xy, _a in ma_draws}
        if len(xs) != 1:
            return False, (
                "band main card anchor='ma' draws used %d distinct x-coordinates %r, expected exactly 1 - "
                "center_x must be computed once and reused (round-15 fix, round-12 regression guard)"
                % (len(xs), sorted(xs))
            )
        return True, ""
    check(
        "a band theme's main-card anchor='ma' draws (the number line and the airline·type line) all share "
        "exactly one x-coordinate - center_x is computed once per block, never recomputed per line "
        "(round-15 fix, PHASE9-4)",
        _band_center_x_computed_once_not_recomputed_per_line,
    )

    # 116. Black-band ink swap (round-13 fix, PHASE9-5): the main card's
    # drawn text pixels sample as IDX_WHITE inside band_black's render and
    # as IDX_BLACK inside another band theme's (band_red) render - by
    # actual sampled pixel colour, not by inference from an exception's
    # absence. band_black's own band FILL is itself IDX_BLACK, so a bare
    # "any IDX_BLACK pixel inside the bbox" probe would misfire on the
    # background, not just missing ink - this diffs a real render against
    # a text-suppressed render of the identical canvas (draw_main_text_block()
    # monkeypatched to a no-op) so only genuinely newly-painted ink pixels
    # are sampled, never the band's own background fill. Only
    # draw.textbbox()-measured bboxes are usable (the tracked route line's
    # own _tracked_text_bbox() bypasses ImageDraw.textbbox() entirely, so
    # _TextBBoxSpy never sees it) - the number line and the airline·type
    # line both go through draw.textbbox() and are sufficient to prove the
    # swap.
    def _band_black_main_card_ink_swaps_to_white():
        orig_main = render.draw_main_text_block

        def _main_no_op(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight, band_idx=None):
            return None, None

        def _ink_pixels_drawn(theme_id):
            with _TextBBoxSpy(render) as bbox_spy:
                canvas_with_text = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
            render.draw_main_text_block = _main_no_op
            try:
                canvas_without_text = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
            finally:
                render.draw_main_text_block = orig_main
            with_pixels = canvas_with_text.load()
            without_pixels = canvas_without_text.load()
            ink_values = set()
            for _text, _xy, _anchor, bbox in bbox_spy.calls:
                left, top, right, bottom = (round(v) for v in bbox)
                for x in range(max(left, 0), min(right, render.WIDTH)):
                    for y in range(max(top, 0), min(bottom, render.HEIGHT)):
                        if with_pixels[x, y] != without_pixels[x, y]:
                            ink_values.add(with_pixels[x, y])
            return ink_values

        # Round 13's black-band-only override widened to every band theme
        # on real Spectra 6 glass (Phase 9 09-04 on-glass session): black
        # text read poorly against Blue/Green/Red too, not just Black -
        # every registered band theme's main card now draws in white ink,
        # unconditionally. Proven by actual pixel colour for the full
        # registered set, not by absence of an exception.
        band_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
        if len(band_ids) != 5:
            return False, "expected exactly 5 registered band theme ids, found %d: %r" % (len(band_ids), band_ids)
        for theme_id in band_ids:
            ink_values = _ink_pixels_drawn(theme_id)
            if IDX_WHITE not in ink_values:
                return False, "%s main card: no newly-painted IDX_WHITE ink pixels found - ink swap missing" % theme_id
            if IDX_BLACK in ink_values:
                return False, "%s main card: newly-painted IDX_BLACK ink pixels found - ink swap incomplete" % theme_id
        return True, ""
    check(
        "every registered band theme's main card text samples as IDX_WHITE (never IDX_BLACK) inside its own drawn "
        "bboxes - the round-13 ink swap, widened on real glass to every band colour, is proven by actual pixel "
        "colour, not by absence of an exception (PHASE9-5)",
        _band_black_main_card_ink_swaps_to_white,
    )

    # 117. Previous-card band clearance: for a full two-flight
    # band_blue_light render (the widest dithered candidate), the band's
    # rightmost x at the previous card's own text y-range - computed via
    # the same linear interpolation _band_center_x() uses internally,
    # derived from BAND_TOP_RIGHT_FRAC/BAND_BOT_RIGHT_FRAC only, never a
    # hardcoded pixel literal - must sit to the LEFT of every previous-card
    # text bbox's left edge, for all 5 band themes (the band's shape is
    # colour-independent; only its fill varies).
    def _previous_card_never_collides_with_the_band():
        band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
        if not band_theme_ids:
            return False, "no band theme ids found in THEME_IDS"

        def _band_right_edge_x(canvas_y, w):
            f = canvas_y / render.HEIGHT
            right_frac = render.BAND_TOP_RIGHT_FRAC - (render.BAND_TOP_RIGHT_FRAC - render.BAND_BOT_RIGHT_FRAC) * f
            return right_frac * w

        for theme_id in band_theme_ids:
            with _TextBBoxSpy(render) as bbox_spy:
                render.build_canvas(
                    TEST_FLIGHT, "departing", route=TEST_ROUTE,
                    previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
                    theme_id=theme_id,
                )
            # The previous card's band branch draws every line anchor="ra"
            # (right-aligned); the main card's band branch draws every line
            # anchor="ma" (centred) - this is the unambiguous discriminator
            # between the two cards' bboxes, not a y-coordinate heuristic
            # (the main card's own band-centred text can legitimately sit
            # below the canvas's vertical midpoint too).
            prev_bboxes = [b for _t, _xy, a, b in bbox_spy.calls if a == "ra"]
            if not prev_bboxes:
                return False, "theme %r: no previous-card (anchor='ra') text bbox found" % (theme_id,)
            for bbox in prev_bboxes:
                left, top = bbox[0], bbox[1]
                band_right_at_top = _band_right_edge_x(top, render.WIDTH)
                if left < band_right_at_top:
                    return False, (
                        "theme %r: previous-card text bbox %r's left edge (%r) sits inside the band's own "
                        "rightmost extent (%r) at that y" % (theme_id, bbox, left, band_right_at_top)
                    )
        return True, ""
    check(
        "the previous card's drawn text bboxes never overlap the diagonal band's own rightmost extent, at any "
        "of the 5 band themes, in a full two-flight render (PHASE9-6 clearance guard)",
        _previous_card_never_collides_with_the_band,
    )

    # 118. Full legal-palette + dominance sweep: for all 5 band themes,
    # both active states, with and without source_fault=True, build_canvas()
    # raises no AssertionError - _assert_legal_palette() (run internally)
    # holds with the full three-tier text and the source-fault badge both
    # present.
    def _band_themes_full_composition_stays_palette_legal():
        band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
        if not band_theme_ids:
            return False, "no band theme ids found in THEME_IDS"
        for theme_id in band_theme_ids:
            for state in ("departing", "arriving"):
                for source_fault in (False, True):
                    render.build_canvas(
                        TEST_FLIGHT, state, route=TEST_ROUTE,
                        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                        previous_state="arriving" if state == "departing" else "departing",
                        theme_id=theme_id, source_fault=source_fault,
                    )
        return True, ""
    check(
        "every registered band theme's full two-flight composition (three-tier main + previous card text, "
        "plus the source-fault badge when present) stays _assert_legal_palette()-legal across both active "
        "states (PHASE9-4/PHASE9-5/PHASE9-6 full sweep)",
        _band_themes_full_composition_stays_palette_legal,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
