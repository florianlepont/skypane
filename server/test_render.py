#!/usr/bin/env python3
"""Contract tests for server/plane/render.py's two-flight poster layout.

Runs under server/.venv's interpreter - render.py transitively imports
Pillow, so the bare system python3 cannot collect this module.

Asserts on the rendered canvas and packed bytes only - never on a
screenshot. Text-content assertions spy on `ImageDraw.ImageDraw.text`
rather than rendering to a scratch canvas and comparing pixel signatures or
doing OCR. Most roles draw one whole-string call per role; the top row
(state label + runway tag, spike 002a's `LABEL_TRACKING_PX` tracking) is
the sole exception - it composites glyph-by-glyph through
`draw_tracked_text()`, so top-row checks reconstruct each run from
consecutive single-character calls at `y == MARGIN` instead of matching a
single whole-string text value.

Uses the real vendored illustration files under
server/assets/icons/illustrations/ (air-france.png, transavia-france.png,
generic-fallback.png, ...) - these are real project assets, not test
fixtures, so a broken selection/compositing path is caught against the
same files poll_loop.py will actually serve.
"""
import contextlib
import inspect
import io
import os
import sys
from collections import Counter

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.plane.render as render  # noqa: E402
import server.panel_format as panel_format  # noqa: E402
import server.plane.illustrations as illustrations  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

# The real Pillow renders in this module (several per test) take a single
# worker over 10s, so it is marked slow and a `-m "not slow"` run can skip
# it deliberately, not by accident.
pytestmark = pytest.mark.slow

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}
LEGAL_IDX = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}
# Bridges the two index/nibble numbering schemes independently of
# panel_format.INDEX_TO_NIBBLE, so this harness's expectations stay
# independently derived.
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
# illustration file (transavia-france.png). callsign_iata ("TO16VB") is
# the real value the same fixture carries, not a synthetic value, so the
# default test render exercises tier 1 with a genuinely real identifier.
TEST_ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
    "callsign_iata": "TO16VB",
}
# callsign_iata ("VY8163") is a synthetic IATA-format value (Vueling's
# real IATA prefix, VY) - this route is hand-built, not from a recorded
# fixture.
TEST_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY8163",
}

# A genuinely long real destination city name and a genuinely long real
# airline name, used to exercise fit_text_size()'s shrink path.
# callsign_iata ("AT9051") is a synthetic IATA-format value (Royal Air
# Maroc's real IATA prefix, AT), needed because the tier-1 identifier
# prefix would otherwise shorten the exercised string.
TEST_LONG_ROUTE = {
    "airline_name": "Compagnie Nationale Royale Air Maroc Express",
    "origin_iata": "SCQ",
    "origin_city": "Santiago de Compostela–Rosalía de Castro",
    "destination_iata": "ORY",
    "destination_city": "Paris",
    "callsign_iata": "AT9051",
}


def nibble_counts(buf):
    # Counter(buf) counts each distinct byte value once in C, then each
    # byte's count is expanded into its two nibbles - same {nibble: count}
    # dict shape as the old per-byte Python loop, one pass over the buffer
    # instead of two nibble-dict increments per byte.
    counts = {}
    for byte, n in Counter(buf).items():
        for nibble in ((byte >> 4) & 0xF, byte & 0xF):
            counts[nibble] = counts.get(nibble, 0) + n
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
    rectangle-drawing seam instead of the text-drawing one: proves no
    background-filled rectangle is painted behind text.
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
    bbox-measurement seam instead of the draw seam: lets a check read the
    actual measured bounding box a text run received, without re-deriving
    `fit_text_size()`'s own font-fitting logic independently - a
    re-derivation would go stale the moment that logic changes and would
    silently stop protecting anything.
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


def _write_garbage_png(tmp_path):
    """Create a file under tmp_path with a `.png` suffix that passes
    os.path.isfile() but carries no valid PNG signature - a file that
    exists on disk but is not decodable image data.
    """
    path = tmp_path / "garbage.png"
    path.write_bytes(b"not a real PNG file - just a short run of garbage bytes 0123456789")
    return str(path)


def _write_oversized_png(tmp_path):
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
    img = Image.new("L", (7000, 6000), color=128)
    path = tmp_path / "oversized.png"
    img.save(str(path), format="PNG", compress_level=1)
    return str(path)


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


@pytest.fixture(scope="module")
def departing_bytes():
    """render_panel(TEST_FLIGHT, 'departing', route=TEST_ROUTE)'s packed
    bytes, computed once per xdist worker for the several checks that only
    read this render rather than build their own.
    """
    return render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)


@pytest.fixture(scope="module")
def arriving_bytes():
    """render_panel(TEST_FLIGHT, 'arriving', route=TEST_ROUTE)'s packed
    bytes - the arriving-state counterpart of `departing_bytes`.
    """
    return render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)


def test_departing_packs_correctly(departing_bytes):
    """render_panel(flight, 'departing', route) packs to exactly 960000 bytes with only legal nibbles"""
    buf = departing_bytes
    if len(buf) != panel_format.IMAGE_BYTES:
        pytest.fail("departing render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES))
    bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
    if bad:
        pytest.fail("departing render contains illegal nibble codes: %r" % (sorted(bad),))





def test_arriving_packs_correctly(arriving_bytes):
    """render_panel(flight, 'arriving', route) packs to exactly 960000 bytes with only legal nibbles"""
    buf = arriving_bytes
    if len(buf) != panel_format.IMAGE_BYTES:
        pytest.fail("arriving render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES))
    bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
    if bad:
        pytest.fail("arriving render contains illegal nibble codes: %r" % (sorted(bad),))





# Both states share one field colour (White), the default theme's
# background - so the two expectations below being identical is
# deliberate, not a copy-paste error: DEPARTING vs. ARRIVING is carried
# by the label text alone.
def test_departing_dominant_is_white(departing_bytes):
    """departing render's dominant nibble is 0x1 (White), the default theme background"""
    dom = dominant_nibble(departing_bytes)
    if dom != NIBBLE_WHITE:
        pytest.fail("departing render's dominant nibble is 0x%x, expected 0x1 (White)" % dom)





def test_arriving_dominant_is_white(arriving_bytes):
    """arriving render's dominant nibble is also 0x1 (White) - the single shared field colour for both states, not a copy-paste duplicate of the departing check above"""
    dom = dominant_nibble(arriving_bytes)
    if dom != NIBBLE_WHITE:
        pytest.fail("arriving render's dominant nibble is 0x%x, expected 0x1 (White)" % dom)





def test_departing_has_white_and_black_from_real_livery(departing_bytes):
    """departing render contains White (text/frame) and Black (real illustration livery) nibbles from full-colour illustration compositing"""
    counts = nibble_counts(departing_bytes)
    if NIBBLE_WHITE not in counts:
        pytest.fail("departing render contains no White (0x1) nibble - no foreground content drawn")
    if NIBBLE_BLACK not in counts:
        pytest.fail("departing render contains no Black (0x0) nibble - Transavia France's real livery art should contribute some")





def test_only_legal_indices_present(departing_bytes):
    """departing render's nibble set is a subset of the 6 legal Spectra 6 codes"""
    bad = set(nibble_counts(departing_bytes)) - LEGAL_NIBBLES
    if bad:
        pytest.fail("departing render contains illegal nibble(s): %r" % (sorted(bad),))


def test_empty_state_white_dominant_with_black():
    """empty-state render is White-dominant and contains at least one Black nibble"""
    buf = render.render_panel(None, "empty")
    if len(buf) != panel_format.IMAGE_BYTES:
        pytest.fail("empty render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES))
    counts = nibble_counts(buf)
    dom = max(counts, key=counts.get)
    if dom != NIBBLE_WHITE:
        pytest.fail("empty render's dominant nibble is 0x%x, expected 0x1 (White)" % dom)
    if NIBBLE_BLACK not in counts:
        pytest.fail("empty render contains no Black (0x0) nibble - expected Black text")


def test_rendering_is_deterministic():
    """rendering the same flight+route twice produces byte-identical output (determinism)"""
    first = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    second = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    if first != second:
        pytest.fail("rendering the same flight twice produced different bytes - render_panel is not deterministic")





def test_departing_and_arriving_differ(departing_bytes, arriving_bytes):
    """departing and arriving renders of the same flight differ in bytes (state changes output)"""
    if departing_bytes == arriving_bytes:
        pytest.fail("departing and arriving renders of the same flight are byte-identical - state does not change output")


def test_illustration_not_mirrored_between_states():
    """the main illustration's opaque pixels are byte-identical between departing and arriving renders - never mirrored by state"""
    path = illustrations.select_illustration(TEST_ROUTE)
    if path is None:
        pytest.fail("illustrations.select_illustration(TEST_ROUTE) returned None - no vendored file resolved")
    inner_width = panel_format.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
    main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
    resized = render._resize_illustration(path, main_w)
    # main_top follows the PAINTED content's centre, same as
    # `_build_active_canvas()` itself computes it, so this locally-derived
    # bbox keeps lining up with where the real render actually places the
    # illustration.
    main_top = render._top_for_centered_content(resized, panel_format.HEIGHT * render.MAIN_ILLUSTRATION_CENTER_Y_FRAC)
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
        pytest.fail("only %d opaque illustration pixels found in the computed bbox %r - geometry looks wrong" % (opaque_total, bbox))
    if mismatches:
        pytest.fail("%d of %d opaque illustration pixels differ between departing and arriving renders - illustration is being mirrored/recolored by state (D-24 violation)" % (mismatches, opaque_total))


def test_illustration_functions_have_no_mirror_param():
    """draw_illustration()/_resize_illustration() have no mirror/flip parameter - illustrations are never mirrored by state"""
    for fn_name in ("draw_illustration", "_resize_illustration"):
        fn = getattr(render, fn_name, None)
        if fn is None:
            pytest.fail("server.plane.render has no %s()" % fn_name)
        params = set(inspect.signature(fn).parameters)
        bad = {p for p in params if "mirror" in p.lower() or "flip" in p.lower()}
        if bad:
            pytest.fail("%s() has a mirror/flip parameter %r - D-24 dropped mirroring entirely" % (fn_name, bad))


def test_soft_alpha_illustration_stays_within_legal_palette():
    """draw_illustration() with a soft/gradient alpha source never produces an illegal in-between palette index (Pitfall 2 regression), and returns .rect (full placement) plus .content (tight painted bbox) as distinct boxes"""
    gradient = Image.new("RGBA", (40, 40))
    pixels = gradient.load()
    for y in range(40):
        for x in range(40):
            # A soft horizontal alpha ramp over a solid Red-ish fill.
            pixels[x, y] = (200, 30, 30, int(255 * x / 39))
    canvas = panel_format.new_canvas(IDX_BLUE)
    placement = render.draw_illustration(canvas, gradient, 10, 10)
    # `.rect` is the full 40x40 placement rectangle pasted at (10, 10) -
    # unchanged by the illustration-crop-text-margin fix.
    if placement.rect != (10, 10, 50, 50):
        pytest.fail("draw_illustration() returned rect %r, expected (10, 10, 50, 50)" % (placement.rect,))
    # `.content` is the tight bbox of what actually gets PAINTED. This
    # source's alpha ramp is int(255 * x / 39), so alpha exceeds the
    # threshold of 127 first at x=20 (int(130.7)=130) and not at x=19
    # (int(124.2)=124) - columns 20..39 are painted, 0..19 are erased.
    # Absolute: (10+20, 10+0, 10+40, 10+40).
    if placement.content != (30, 10, 50, 50):
        pytest.fail("draw_illustration() returned content %r, expected (30, 10, 50, 50) - the tight "
            "bbox of pixels above the alpha threshold, not the full rectangle" % (placement.content,))
    idx_set = {value for _count, value in canvas.getcolors()} if canvas.getcolors() else set()
    illegal = idx_set - LEGAL_IDX
    if illegal:
        pytest.fail("a soft-alpha source produced illegal palette index(es) %r on the canvas - alpha must be hard-thresholded before paste()" % (sorted(illegal),))


def test_different_airline_changes_the_rendered_bytes():
    """a route whose airline_name has no vendored file falls back to generic-fallback.png and renders different bytes than a route with real art"""
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
        pytest.fail("rendering with TEST_ROUTE's real airline vs. an unvendored airline (falls back to generic-fallback.png) produced byte-identical panels")


# The top row (state label + runway tag) is tracked glyph-by-glyph at
# LABEL_TRACKING_PX, near the MARGIN inset. draw_top_labels() draws the
# label first and the tag second (its own fixed draw order), so the
# single-character calls captured at y == MARGIN can be reconstructed in
# call order without needing to x-sort them.
def test_departing_top_row_labels_present():
    """departing render draws the top-left 'DEPARTING' label and the top-right runway tag, both tracked glyph-by-glyph, label first then tag"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
    joined = "".join(t for t, _xy, _a in top_row)
    label_text = render.STATE_LABEL_TEXT["departing"]
    tag_text = render.TOP_RIGHT_TAG_TEXT
    expected = label_text + tag_text
    if joined != expected:
        pytest.fail("reconstructed top-row glyph run = %r, expected label %r followed by tag %r (%r)"
            % (joined, label_text, tag_text, expected))


def test_top_labels_sit_at_the_margin_inset():
    """the state label's first glyph sits at the MARGIN inset and the top-right tag's first glyph is positioned so its tracked run ends flush at WIDTH - MARGIN"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
    top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
    label_text = render.STATE_LABEL_TEXT["arriving"]
    tag_text = render.TOP_RIGHT_TAG_TEXT
    if len(top_row) < len(label_text) + len(tag_text):
        pytest.fail("expected %d top-row glyph draws, got %d: %r" % (
            len(label_text) + len(tag_text), len(top_row), top_row,
        ))
    label_glyphs = top_row[: len(label_text)]
    tag_glyphs = top_row[len(label_text):len(label_text) + len(tag_text)]
    (first_label_xy, first_label_anchor) = label_glyphs[0][1], label_glyphs[0][2]
    if first_label_xy != (render.MARGIN, render.MARGIN) or first_label_anchor != "la":
        pytest.fail("state label's first glyph drawn at %r anchor=%r, expected (%d, %d) anchor='la'" % (
            first_label_xy, first_label_anchor, render.MARGIN, render.MARGIN,
        ))
    weight = render.device_config.theme_weight(render.device_config.DEFAULT_THEME_ID)
    tag_font = render._role_font(render.TOP_TAG_FONT, weight)
    tracked_width = render._tracked_text_width(tag_font, tag_text, render.LABEL_TRACKING_PX)
    expected_tag_x = panel_format.WIDTH - render.MARGIN - tracked_width
    (first_tag_xy, first_tag_anchor) = tag_glyphs[0][1], tag_glyphs[0][2]
    if abs(first_tag_xy[0] - expected_tag_x) > 0.01 or first_tag_xy[1] != render.MARGIN or first_tag_anchor != "la":
        pytest.fail("top-right tag's first glyph drawn at %r anchor=%r, expected (%.2f, %d) anchor='la'" % (
            first_tag_xy, first_tag_anchor, expected_tag_x, render.MARGIN,
        ))
    if abs((first_tag_xy[0] + tracked_width) - (panel_format.WIDTH - render.MARGIN)) > 0.01:
        pytest.fail("top-right tag run does not end flush at WIDTH - MARGIN (%d): first glyph x %.2f + tracked width %.2f" % (
            panel_format.WIDTH - render.MARGIN, first_tag_xy[0], tracked_width,
        ))


def test_frame_outline_is_drawn():
    """draw_frame() draws a thin outline at the ~2.5%%-of-width inset"""
    canvas = panel_format.new_canvas(IDX_BLUE)
    box = render.draw_frame(canvas, IDX_WHITE)
    inset = round(panel_format.WIDTH * render.FRAME_INSET_FRAC)
    if box != (inset, inset, panel_format.WIDTH - inset, panel_format.HEIGHT - inset):
        pytest.fail("draw_frame() returned box %r, expected a %dpx inset rectangle" % (box, inset))
    # Sample a point along the top edge - must be the ink color, not the background.
    sample = canvas.getpixel((panel_format.WIDTH // 2, inset))
    if sample != IDX_WHITE:
        pytest.fail("sampled frame pixel at %r is index %r, expected IDX_WHITE" % ((panel_format.WIDTH // 2, inset), sample))


# Main flight text: "{identifier} to|from {city}" line 1, airline name
# line 2, no "PREVIOUS ·" prefix leaking onto the main block.
def test_departing_main_text_uses_lowercase_to():
    """departing main flight text is '{identifier} to {destination_city}' / '{airline_name} · {type_label}'"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    texts = [t for t, _xy, _anchor in spy.calls]
    expected_line1 = "%s to %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["destination_city"])
    type_label = render._TYPE_DISPLAY_LABELS[TEST_FLIGHT["aircraft_type"]]
    expected_line2 = "%s · %s" % (TEST_ROUTE["airline_name"], type_label)
    if expected_line1 not in texts:
        pytest.fail("expected main line 1 %r among the text draws, got %r" % (expected_line1, texts))
    if expected_line2 not in texts:
        pytest.fail("expected main line 2 %r among the text draws, got %r" % (expected_line2, texts))


def test_arriving_main_text_uses_lowercase_from():
    """arriving main flight text is '{identifier} from {origin_city}', lowercase sentence text"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
    texts = [t for t, _xy, _anchor in spy.calls]
    expected_line1 = "%s from %s" % (TEST_ROUTE["callsign_iata"], TEST_ROUTE["origin_city"])
    if expected_line1 not in texts:
        pytest.fail("expected main line 1 %r among the text draws, got %r" % (expected_line1, texts))


def test_enrichment_miss_shows_unknown_flight():
    """a full enrichment miss (route=None) draws 'Unknown flight' and ROUTE_FALLBACK_TEXT, never the raw callsign"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=None)
    texts = [t for t, _xy, _anchor in spy.calls]
    if "Unknown flight" not in texts:
        pytest.fail("expected 'Unknown flight' among the text draws on a full enrichment miss (D-10 tier 4), got %r" % (texts,))
    if render.ROUTE_FALLBACK_TEXT not in texts:
        pytest.fail("expected %r among the text draws on an enrichment miss, got %r" % (render.ROUTE_FALLBACK_TEXT, texts))
    if TEST_FLIGHT["callsign"] in texts:
        pytest.fail("the raw callsign %r must never appear on a full enrichment miss (D-08), got %r" % (TEST_FLIGHT["callsign"], texts))


# Previous flight card: present only when supplied, no "PREVIOUS ·"
# prefix, right-aligned text, own real illustration.
def test_previous_flight_card_renders_its_own_text():
    """a supplied previous_flight/previous_route renders its own real two-line text block"""
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
        pytest.fail("expected previous-flight line 1 %r among the text draws, got %r" % (expected_line1, texts))
    if expected_line2 not in texts:
        pytest.fail("expected previous-flight line 2 %r among the text draws, got %r" % (expected_line2, texts))


def test_previous_flight_text_has_no_previous_prefix():
    """no drawn text contains a 'PREVIOUS ·' prefix"""
    with _TextSpy(render) as spy:
        render.build_canvas(
            TEST_FLIGHT, "departing", route=TEST_ROUTE,
            previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
        )
    texts = [t for t, _xy, _anchor in spy.calls]
    offenders = [t for t in texts if "PREVIOUS" in t.upper()]
    if offenders:
        pytest.fail("found a 'PREVIOUS' prefix in the drawn text %r - D-26 explicitly removed it" % (offenders,))


def test_previous_flight_text_is_right_aligned():
    """the previous flight's text block is drawn right-aligned (anchor='ra')"""
    with _TextSpy(render) as spy:
        render.build_canvas(
            TEST_FLIGHT, "departing", route=TEST_ROUTE,
            previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
        )
    expected_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
    anchors = [anchor for t, _xy, anchor in spy.calls if t == expected_line1]
    if not anchors:
        pytest.fail("did not capture the previous-flight line 1 draw call")
    if anchors[0] != "ra":
        pytest.fail("previous-flight text anchor is %r, expected 'ra' (right-aligned, D-26)" % (anchors[0],))


def test_no_previous_flight_omits_the_card():
    """omitting previous_flight/previous_route renders a genuinely different (single-flight) panel"""
    single = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    two_flight = render.render_panel(
        TEST_FLIGHT, "departing", route=TEST_ROUTE,
        previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
    )
    if single == two_flight:
        pytest.fail("a render with no previous_flight is byte-identical to one with a previous flight supplied - the card is not actually optional")


def test_pt_serif_bold_is_the_active_weight():
    """every active-state text role uses PTSerif-Bold.ttf; the empty-state heading keeps PTSerif-Bold.ttf and EMPTY_BODY_FONT keeps PTSerif-Regular.ttf"""
    active_roles = ("STATE_LABEL_FONT", "TOP_TAG_FONT", "MAIN_LINE1_FONT", "MAIN_LINE2_FONT", "PREVIOUS_LINE1_FONT", "PREVIOUS_LINE2_FONT")
    for name in active_roles:
        if not hasattr(render, name):
            pytest.fail("server.plane.render has no %s role constant" % name)
        path, _size, _weight = getattr(render, name)
        if not path.endswith("PTSerif-Bold.ttf"):
            pytest.fail("%s font path %r is not PTSerif-Bold.ttf (D-06)" % (name, path))
    if not render.EMPTY_HEADING_FONT[0].endswith("PTSerif-Bold.ttf"):
        pytest.fail("EMPTY_HEADING_FONT font path %r is not PTSerif-Bold.ttf" % (render.EMPTY_HEADING_FONT[0],))
    if not render.EMPTY_BODY_FONT[0].endswith("PTSerif-Regular.ttf"):
        pytest.fail("EMPTY_BODY_FONT font path %r is not PTSerif-Regular.ttf - it is the one remaining active reference to the Regular file" % (render.EMPTY_BODY_FONT[0],))


def test_previous_line2_font_grew_to_20px():
    """PREVIOUS_LINE2_FONT's size is 20px with its overflow floor unchanged"""
    if render.PREVIOUS_LINE2_FONT[1] != 20:
        pytest.fail("PREVIOUS_LINE2_FONT size is %r, expected 20 (D-11)" % (render.PREVIOUS_LINE2_FONT[1],))
    if render.PREVIOUS_LINE2_MIN_SIZE != 12:
        pytest.fail("PREVIOUS_LINE2_MIN_SIZE is %r, expected unchanged 12" % (render.PREVIOUS_LINE2_MIN_SIZE,))


# The active weight is theme-conditional, not universal. On the flat
# White theme (never dithered), every active-state role must request
# PTSerif-Regular.ttf and never PTSerif-Bold.ttf - Bold's whole job
# (resisting dithered speckle) never applies there, and it reads as
# needlessly heavy on real ink. On a dithered theme (Sky), every role
# must request PTSerif-Bold.ttf and never Regular. Monkeypatches
# render._font, the seam both the direct role-constant lookups
# (draw_top_labels()) and fit_text_size() itself call through via
# _role_font()/_role_fit_text_size(), so it captures every font path
# actually requested.
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
    # request is captured too.
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


def test_white_theme_uses_only_regular_weight():
    """the White theme's active-state roles request only PTSerif-Regular.ttf, never Bold"""
    requested_paths = _spy_requested_font_paths("white")
    if not requested_paths:
        pytest.fail("no font was requested at all - the spy did not capture anything")
    bold_hits = [p for p in requested_paths if p.endswith("PTSerif-Bold.ttf")]
    if bold_hits:
        pytest.fail("PTSerif-Bold.ttf was requested %d time(s) on a White-theme active-state panel - expected zero, White is never dithered (08-06): %r" % (len(bold_hits), bold_hits))
    regular_hits = [p for p in requested_paths if p.endswith("PTSerif-Regular.ttf")]
    if not regular_hits:
        pytest.fail("PTSerif-Regular.ttf was never requested while rendering a White-theme active-state panel")


# Same behavioural contract, generalised across every registry entry
# (each with its own `dithered`/`weight` pair - see device_config.THEMES'
# own module comment). Each theme's requested font paths must match its
# own declared `theme_weight()` exactly - never the other weight.
def test_every_theme_uses_only_its_declared_weight():
    """every one of the 11 registry themes requests only its own declared weight"""
    for theme_id in render.device_config.THEME_IDS:
        requested_paths = _spy_requested_font_paths(theme_id)
        if not requested_paths:
            pytest.fail("%r: no font was requested at all - the spy did not capture anything" % (theme_id,))
        declared_weight = render.device_config.theme_weight(theme_id)
        wrong_suffix = "PTSerif-Regular.ttf" if declared_weight == "bold" else "PTSerif-Bold.ttf"
        right_suffix = "PTSerif-Bold.ttf" if declared_weight == "bold" else "PTSerif-Regular.ttf"
        wrong_hits = [p for p in requested_paths if p.endswith(wrong_suffix)]
        if wrong_hits:
            pytest.fail("%r (declared weight %r): %s was requested %d time(s) - expected zero: %r" % (
                theme_id, declared_weight, wrong_suffix, len(wrong_hits), wrong_hits))
        right_hits = [p for p in requested_paths if p.endswith(right_suffix)]
        if not right_hits:
            pytest.fail("%r (declared weight %r): %s was never requested" % (theme_id, declared_weight, right_suffix))


# The text-backing-plate helper no longer exists on the module at all -
# the removal is complete, not partial.
def test_paint_text_backing_helper_is_gone():
    """_paint_text_backing() no longer exists on server.plane.render"""
    if hasattr(render, "_paint_text_backing"):
        pytest.fail("server.plane.render still carries _paint_text_backing - D-05 requires its complete removal")


# No rectangle filled with the state's own background index is ever
# painted (i.e. no background-filled "backing plate" behind text, on any
# theme). Captured via _RectangleSpy across every registered theme and
# both active states - driven from the theme registry so a future sixth
# theme is exercised automatically, matching the per-theme dominance
# check's own pattern above. draw_frame() is not called from this render
# path and the text-backing-plate is gone too, so this currently passes
# vacuously per-render and exists purely as a regression guard against
# either being reintroduced.
def test_no_background_filled_rectangle_behind_text_on_any_theme():
    """no rectangle filled with the state's own background index is painted, on any registered theme, in either active state"""
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
                    pytest.fail("theme=%r state=%r: a rectangle at %r was filled with bg_idx=%r - a background-filled plate exists (D-05 regression)" % (theme_id, state, bounds, bg_idx))


def test_long_name_stress_case_shrinks_without_crashing():
    """a genuinely long destination/origin city name (Santiago de Compostela) shrinks via fit_text_size() without crashing, drawn in full"""
    try:
        with _TextSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_LONG_ROUTE)
    except AssertionError as exc:
        pytest.fail("long-name render raised an assertion: %r" % (exc,))
    texts = [t for t, _xy, _anchor in spy.calls]
    expected_line1 = "%s from %s" % (TEST_LONG_ROUTE["callsign_iata"], TEST_LONG_ROUTE["origin_city"])
    if expected_line1 not in texts:
        pytest.fail("long origin-city line %r was not drawn in full (found %r) - the shrink path must fit the text, not truncate it" % (expected_line1, texts))


def test_unlabelled_type_renders_airline_alone():
    """_flight_line2_text() renders the airline name alone for an unlabelled (unrecognized) type designator"""
    result = render._flight_line2_text({"airline_name": "Air France"}, "ZZZZ")
    if result != "Air France":
        pytest.fail("expected 'Air France' for an unlabelled designator, got %r" % (result,))


def test_none_type_renders_airline_alone():
    """_flight_line2_text() renders the airline name alone for aircraft_type=None"""
    result = render._flight_line2_text({"airline_name": "Air France"}, None)
    if result != "Air France":
        pytest.fail("expected 'Air France' for aircraft_type=None, got %r" % (result,))


def test_one_argument_call_renders_airline_alone():
    """_flight_line2_text() renders the airline name alone when aircraft_type is omitted entirely"""
    result = render._flight_line2_text({"airline_name": "Air France"})
    if result != "Air France":
        pytest.fail("expected 'Air France' for the one-argument call, got %r" % (result,))


def test_display_airline_name_applies_the_p01_alias_only_where_defined():
    """the P-01 presentation-only airline alias renders the current brand name; a non-aliased airline is unchanged"""
    if render.display_airline_name("CCM Airlines") != "Air Corsica":
        pytest.fail("display_airline_name('CCM Airlines') did not return the P-01 alias 'Air Corsica'")
    if render.display_airline_name("Air France") != "Air France":
        pytest.fail("display_airline_name('Air France') should return the input unchanged (no alias)")
    aliased_line2 = render._flight_line2_text({"airline_name": "CCM Airlines"}, "AT72")
    if "Air Corsica" not in aliased_line2 or "CCM Airlines" in aliased_line2:
        pytest.fail("_flight_line2_text() with the CCM Airlines route did not render the P-01 alias: %r" % (aliased_line2,))


def test_flight_line2_text_never_raises_for_hostile_inputs():
    """_flight_line2_text() never raises across a battery of malformed routes x hostile aircraft types, and always returns a string"""
    malformed_routes = (None, {}, "not-a-dict", 42, ["a", "list"], {"airline_name": 12345})
    hostile_types = (None, "", "   ", "../../etc/passwd", "..\\..\\windows", 999, ["x"], "z" * 500)
    for route in malformed_routes:
        for aircraft_type in hostile_types:
            try:
                result = render._flight_line2_text(route, aircraft_type)
            except Exception as exc:
                pytest.fail("_flight_line2_text(%r, %r) raised %r" % (route, aircraft_type, exc))
            if not isinstance(result, str):
                pytest.fail("_flight_line2_text(%r, %r) returned non-string %r" % (route, aircraft_type, result))


def test_long_name_plus_longest_label_fits_within_canvas():
    """the longest real airline name combined with the longest type label still renders without tripping _assert_within_canvas"""
    longest_type, longest_label = max(render._TYPE_DISPLAY_LABELS.items(), key=lambda kv: len(kv[1]))
    long_flight = dict(TEST_FLIGHT, aircraft_type=longest_type)
    try:
        render.build_canvas(long_flight, "arriving", route=TEST_LONG_ROUTE)
    except AssertionError as exc:
        pytest.fail("long airline name + longest type label (%r) raised an assertion: %r" % (longest_label, exc))


def test_select_illustration_receives_main_flights_type():
    """rendering with a main flight carrying a type calls select_illustration() with that exact type"""
    with _SelectIllustrationSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    if not spy.calls:
        pytest.fail("no select_illustration() call captured")
    main_route, main_type = spy.calls[0]
    if main_type != TEST_FLIGHT["aircraft_type"]:
        pytest.fail("main-card select_illustration() call got aircraft_type=%r, expected %r" % (main_type, TEST_FLIGHT["aircraft_type"]))
    if main_route != TEST_ROUTE:
        pytest.fail("main-card select_illustration() call got route=%r, expected TEST_ROUTE" % (main_route,))


def test_select_illustration_calls_each_receive_their_own_flights_type():
    """a main + previous flight makes two select_illustration() calls, each receiving its own flight's type (no crossover)"""
    with _SelectIllustrationSpy(render) as spy:
        render.build_canvas(
            TEST_FLIGHT, "departing", route=TEST_ROUTE,
            previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE, previous_state="arriving",
        )
    if len(spy.calls) != 2:
        pytest.fail("expected exactly 2 select_illustration() calls (main + previous), got %d: %r" % (len(spy.calls), spy.calls))
    (main_route, main_type), (prev_route, prev_type) = spy.calls
    if main_type != TEST_FLIGHT["aircraft_type"]:
        pytest.fail("main-card call got aircraft_type=%r, expected %r" % (main_type, TEST_FLIGHT["aircraft_type"]))
    if prev_type != TEST_PREVIOUS_FLIGHT["aircraft_type"]:
        pytest.fail("previous-card call got aircraft_type=%r, expected %r" % (prev_type, TEST_PREVIOUS_FLIGHT["aircraft_type"]))
    if prev_type == main_type and TEST_FLIGHT["aircraft_type"] != TEST_PREVIOUS_FLIGHT["aircraft_type"]:
        pytest.fail("previous-card call received the main flight's type - card-type crossover bug")
    if main_route != TEST_ROUTE or prev_route != TEST_PREVIOUS_ROUTE:
        pytest.fail("select_illustration() calls got the wrong route pairing: %r" % (spy.calls,))


def test_no_previous_flight_never_raises_and_never_crosses_over():
    """previous_flight=None still completes without raising and never fabricates a type for the omitted previous card"""
    try:
        with _SelectIllustrationSpy(render) as spy:
            render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, previous_flight=None)
    except Exception as exc:
        pytest.fail("build_canvas() with previous_flight=None raised %r" % (exc,))
    # Only the main-card call is expected (no previous_flight means no
    # previous card at all, per _build_active_canvas()'s own guard) -
    # but the real assertion is simply that nothing raised, and that if
    # a second call somehow occurred, it did not fabricate a type.
    for _route, aircraft_type in spy.calls[1:]:
        if aircraft_type not in (None, TEST_FLIGHT["aircraft_type"]):
            pytest.fail("a previous-card call with no previous_flight got an unexpected aircraft_type=%r" % (aircraft_type,))


def test_render_source_never_uses_text_outline_arguments():
    """server/plane/render.py's comment-stripped source contains no stroke_width/stroke_fill text-outline usage"""
    render_path = os.path.join(REPO_ROOT, "server", "plane", "render.py")
    with open(render_path, "r") as fh:
        code_lines = [line for line in fh if not line.lstrip().startswith("#")]
    stripped_source = "".join(code_lines)
    if "stroke_width" in stripped_source or "stroke_fill" in stripped_source:
        pytest.fail("server/plane/render.py references stroke_width/stroke_fill outside a full-line comment")





def test_corrupt_illustration_degrades_to_generic_fallback(tmp_path):
    """a corrupt (byte-garbage) illustration file degrades to the generic fallback instead of raising out of render_panel()"""
    garbage_path = _write_garbage_png(tmp_path)
    with _forced_illustration(render, garbage_path):
        garbage_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    with _forced_illustration(render, illustrations.generic_fallback_path()):
        fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    if len(garbage_buf) != panel_format.IMAGE_BYTES:
        pytest.fail("corrupt-illustration render is %d bytes, expected %d" % (len(garbage_buf), panel_format.IMAGE_BYTES))
    if garbage_buf != fallback_buf:
        pytest.fail("a corrupt illustration file did not degrade to a byte-identical generic-fallback panel")





def test_oversized_illustration_rejected_on_header(tmp_path):
    """an oversized illustration is rejected on its PNG header, before any pixel data is decoded"""
    oversized_path = _write_oversized_png(tmp_path)
    with Image.open(oversized_path) as probe:
        pixel_count = probe.size[0] * probe.size[1]
    if pixel_count <= illustrations.ILLUSTRATION_MAX_PIXELS:
        pytest.fail(
            "fixture pixel count %d does not exceed ILLUSTRATION_MAX_PIXELS %d - "
            "fixture is not actually oversized" % (pixel_count, illustrations.ILLUSTRATION_MAX_PIXELS)
        )
    with _forced_illustration(render, oversized_path):
        oversized_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    with _forced_illustration(render, illustrations.generic_fallback_path()):
        fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    if len(oversized_buf) != panel_format.IMAGE_BYTES:
        pytest.fail("oversized-illustration render is %d bytes, expected %d" % (len(oversized_buf), panel_format.IMAGE_BYTES))
    if oversized_buf != fallback_buf:
        pytest.fail("an oversized illustration file did not degrade to a byte-identical generic-fallback panel")





def test_both_illustration_and_fallback_undecodable_still_renders(tmp_path):
    """when the selected illustration and the generic fallback are both undecodable, the render skips the illustration and still returns a valid panel"""
    garbage_path = _write_garbage_png(tmp_path)
    with _forced_illustration(render, garbage_path, fallback_path=garbage_path):
        both_bad_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    with _forced_illustration(render, illustrations.generic_fallback_path()):
        fallback_buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    if len(both_bad_buf) != panel_format.IMAGE_BYTES:
        pytest.fail(
            "render with both illustration and fallback undecodable is %d bytes, expected %d"
            % (len(both_bad_buf), panel_format.IMAGE_BYTES)
        )
    if both_bad_buf == fallback_buf:
        pytest.fail(
            "render with both illustration and fallback undecodable is byte-identical to the "
            "fallback-forced render - the illustration was not actually skipped"
        )


# An intermediate render state: an airline-only route (adsbdb missed, the
# callsign's ICAO prefix resolved the carrier) still shows the airline
# name and the airline's own illustration; the destination stays
# genuinely unknown.

def test_airline_only_route_shows_airline_not_fallback_text():
    """an airline-only route (adsbdb miss, prefix-resolved 'easyJet') omits line 1 entirely and draws only the airline name, never the raw callsign or ROUTE_FALLBACK_TEXT"""
    import server.plane.enrich as enrich

    airline_only_flight = {"hex": "440cb1", "callsign": "EJU84YF"}
    airline_only_route = enrich.airline_only_route("easyJet")
    with _TextSpy(render) as spy:
        render.build_canvas(airline_only_flight, "departing", route=airline_only_route)
    texts = [t for t, _xy, _anchor in spy.calls]
    if "EJU84YF" in texts:
        pytest.fail("the raw callsign 'EJU84YF' must never appear on an airline-only route (D-08/D-10 tier 3), got %r" % (texts,))
    if "easyJet" not in texts:
        pytest.fail("expected the resolved airline name 'easyJet' among the text draws, got %r" % (texts,))
    if render.ROUTE_FALLBACK_TEXT in texts:
        pytest.fail("ROUTE_FALLBACK_TEXT must not appear when the airline is known (D-06), got %r" % (texts,))


def test_airline_only_route_composes_line2_like_a_full_hit():
    """an airline-only Transavia France + B738 route composes line 2 as '{airline} · {type label}' exactly like a full hit, line 1 omitted entirely, never the raw callsign or a to/from clause"""
    import server.plane.enrich as enrich

    flight = {"hex": "39de4a", "callsign": "TVF12ZW", "aircraft_type": "B738"}
    airline_only_route = enrich.airline_only_route("Transavia France")
    with _TextSpy(render) as spy:
        render.build_canvas(flight, "departing", route=airline_only_route)
    texts = [t for t, _xy, _anchor in spy.calls]
    expected_line2 = "Transavia France · %s" % render._TYPE_DISPLAY_LABELS["B738"]
    if expected_line2 not in texts:
        pytest.fail("expected main line 2 %r among the text draws, got %r" % (expected_line2, texts))
    if "TVF12ZW" in texts:
        pytest.fail("the raw callsign 'TVF12ZW' must never appear on an airline-only route (D-08/D-10 tier 3), got %r" % (texts,))
    for text in texts:
        if " to " in text or " from " in text:
            pytest.fail("found a to/from clause %r - the destination must stay genuinely unknown (D-06)" % (text,))


def test_airline_only_route_selects_the_airlines_own_illustration():
    """illustrations.select_illustration() on an airline-only Transavia France route resolves to 'transavia-france.png' - the airline's own art, not the generic fallback"""
    import server.plane.enrich as enrich

    airline_only_route = enrich.airline_only_route("Transavia France")
    path = illustrations.select_illustration(airline_only_route, "B738")
    if path is None or os.path.basename(path) != "transavia-france.png":
        pytest.fail("expected the airline's own illustration 'transavia-france.png', got %r" % (path,))


# A route already corrected by enrich.correct_airline_name() renders its
# current brand name in the caption via _flight_line2_text(), and
# render.display_airline_name() is a no-op on that already-corrected
# string (it has no alias of its own to apply - the alias table only
# ever held "CCM Airlines").
def test_corrected_route_renders_current_brand_and_display_alias_is_noop():
    """a route already corrected by enrich.correct_airline_name() renders its current brand name via _flight_line2_text(), and display_airline_name() is a no-op on the already-corrected string"""
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
        pytest.fail("setup failure: expected a corrected 'Air Corsica' route, got %r" % (route,))
    if render.display_airline_name(route["airline_name"]) != "Air Corsica":
        pytest.fail("display_airline_name() must be a no-op on the already-corrected 'Air Corsica' string")
    line2 = render._flight_line2_text(route, "A320")
    if "Air Corsica" not in line2:
        pytest.fail("_flight_line2_text() on the corrected route did not render the current brand name: %r" % (line2,))
    if "CCM Airlines" in line2:
        pytest.fail("_flight_line2_text() on the corrected route must not render the stale upstream string: %r" % (line2,))


# _flight_line1_text()'s four-tier content ladder: unit-level checks
# against the function directly, plus one end-to-end guard and one
# hostile-input battery.

def test_tier1_identifier_and_city_both_known():
    """_flight_line1_text() tier 1 (identifier + city) returns the exact '{identifier} to|from {city}' string for both states"""
    route = {
        "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
        "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": "AF1234",
    }
    flight = {"hex": "aaaaaa", "callsign": "AFR001"}
    departing = render._flight_line1_text(flight, "departing", route)
    arriving = render._flight_line1_text(flight, "arriving", route)
    if departing != "AF1234 to New York":
        pytest.fail("tier 1 departing expected 'AF1234 to New York', got %r" % (departing,))
    if arriving != "AF1234 from Paris":
        pytest.fail("tier 1 arriving expected 'AF1234 from Paris', got %r" % (arriving,))


def test_tier2_city_known_no_identifier():
    """_flight_line1_text() tier 2 (city known, no identifier) returns the title-case direction word and city, with no identifier, for both states"""
    route = {
        "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
        "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": None,
    }
    flight = {"hex": "aaaaaa", "callsign": "AFR001"}
    departing = render._flight_line1_text(flight, "departing", route)
    arriving = render._flight_line1_text(flight, "arriving", route)
    if departing != "To New York":
        pytest.fail("tier 2 departing expected 'To New York', got %r" % (departing,))
    if arriving != "From Paris":
        pytest.fail("tier 2 arriving expected 'From Paris', got %r" % (arriving,))


def test_tier3_airline_only_returns_empty_string():
    """_flight_line1_text() tier 3 (airline known, no city, no identifier) returns an empty string - the sentinel meaning line 1 is omitted"""
    import server.plane.enrich as enrich

    route = enrich.airline_only_route("Ryanair")
    flight = {"hex": "bbbbbb", "callsign": "RYR123"}
    departing = render._flight_line1_text(flight, "departing", route)
    arriving = render._flight_line1_text(flight, "arriving", route)
    if departing != "" or arriving != "":
        pytest.fail("tier 3 (airline-only route) expected an empty string for both states, got %r/%r" % (departing, arriving))


def test_tier4_nothing_resolved_returns_unknown_flight():
    """_flight_line1_text() tier 4 (nothing resolved) returns the fixed string 'Unknown flight' for both route=None and a dict with no airline name, identical for both states"""
    flight = {"hex": "cccccc", "callsign": "XYZ999"}
    no_airline_route = {
        "airline_name": None, "origin_iata": None, "origin_city": None,
        "destination_iata": None, "destination_city": None, "callsign_iata": None,
    }
    for route in (None, no_airline_route):
        departing = render._flight_line1_text(flight, "departing", route)
        arriving = render._flight_line1_text(flight, "arriving", route)
        if departing != "Unknown flight":
            pytest.fail("tier 4 departing expected 'Unknown flight' for route=%r, got %r" % (route, departing))
        if arriving != "Unknown flight":
            pytest.fail("tier 4 arriving expected 'Unknown flight' for route=%r, got %r" % (route, arriving))


def test_d08_no_raw_callsign_or_hex_anywhere_across_all_tiers():
    """no drawn text on either card contains the raw callsign or hex, across all four content-ladder tiers (end-to-end guard)"""
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
                    pytest.fail("raw callsign/hex %r leaked into drawn text %r at route=%r (D-08)" % (banned, text, route))


def test_hostile_route_shapes_degrade_a_tier_without_raising():
    """_flight_line1_text() degrades a tier rather than raising for hostile route shapes (non-string/empty/whitespace identifier, non-dict route)"""
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
                pytest.fail("route=%r state=%r raised %r instead of degrading a tier" % (route, state, exc))
            if not isinstance(result, str):
                pytest.fail("route=%r state=%r returned a non-string %r" % (route, state, result))


# Bottom-left battery-low icon. BATTERY_ICON_BOX is computed from
# render's own constants (not restated as a hand-written literal) exactly
# the way draw_battery_icon() derives its own total bounding box - so
# this containment window can never go stale relative to the
# BATTERY_ICON_* constants again. Check D below is the one place that
# still pins the literal geometry values.

BATTERY_ICON_BOX = (
    render.BATTERY_ICON_LEFT,
    render.BATTERY_ICON_BOTTOM - render.BATTERY_ICON_BODY_H,
    render.BATTERY_ICON_LEFT + render.BATTERY_ICON_BODY_W + render.BATTERY_ICON_NUB_W,
    render.BATTERY_ICON_BOTTOM,
)


def _states_for_battery_checks():
    """(state, flight, kwargs) triples exercising all three render
    states - departing/arriving carry a real previous-flight card
    (TEST_PREVIOUS_FLIGHT/TEST_PREVIOUS_ROUTE) so a real one is on the
    canvas.
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


def test_battery_default_off_matches_explicit_false():
    """build_canvas() with no battery kwarg is pixel-identical to battery_low=False for departing/arriving/empty (default-off, no regression)"""
    for state, flight, kwargs in _states_for_battery_checks():
        no_kw = render.build_canvas(flight, state, **kwargs)
        explicit_false = render.build_canvas(flight, state, battery_low=False, **kwargs)
        if no_kw.tobytes() != explicit_false.tobytes():
            pytest.fail("state=%r: build_canvas() with no battery kwarg differs from battery_low=False" % (state,))


def test_battery_icon_conditional_draw_is_spatially_contained():
    """battery_low=True differs from battery_low=False only inside the icon bounding box (64,1514,115,1536), for departing/arriving (with a real previous-flight card on the canvas) and empty"""
    for state, flight, kwargs in _states_for_battery_checks():
        off = render.build_canvas(flight, state, battery_low=False, **kwargs)
        on = render.build_canvas(flight, state, battery_low=True, **kwargs)
        inside, outside = _diff_inside_outside(off, on, BATTERY_ICON_BOX)
        if not inside:
            pytest.fail("state=%r: battery_low=True produced no pixel difference inside the icon box %r" % (state, BATTERY_ICON_BOX))
        if outside:
            pytest.fail("state=%r: battery_low=True changed a pixel outside the icon box %r" % (state, BATTERY_ICON_BOX))


def test_battery_icon_ink_and_hollow_interior():
    """with battery_low=True, the body outline corner/fill/nub read as the state's own ink (EMPTY_INK for the empty state), while the hollow interior right of the fill still reads as the state's background"""
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
            pytest.fail("state=%r: body outline corner (64,1514) is %r, expected ink %r" % (state, corner, ink_idx))
        if fill_interior != ink_idx:
            pytest.fail("state=%r: fill-interior pixel (70,1525) is %r, expected ink %r" % (state, fill_interior, ink_idx))
        if nub != ink_idx:
            pytest.fail("state=%r: nub pixel (112,1524) is %r, expected ink %r" % (state, nub, ink_idx))
        if gap != bg_idx:
            pytest.fail("state=%r: pixel (95,1525) inside the body outline but right of the fill is %r, expected background %r" % (state, gap, bg_idx))


def test_battery_icon_geometry_derives_from_spacing_scale():
    """battery icon size constants are a uniform round(original * 0.7) reduction of the former spacing-scale values, with the stroke never dropping below FRAME_STROKE_PX, position constants (BATTERY_ICON_LEFT/BOTTOM) unchanged, the nub centred to within one pixel, and a total bounding box of (64,1514,115,1536)"""
    if render.BATTERY_ICON_BODY_W != round(render.SPACE_LG * 0.7):
        pytest.fail("BATTERY_ICON_BODY_W is not round(SPACE_LG * 0.7)")
    if render.BATTERY_ICON_BODY_H != round(render.SPACE_MD * 0.7):
        pytest.fail("BATTERY_ICON_BODY_H is not round(SPACE_MD * 0.7)")
    if render.BATTERY_ICON_NUB_W != round(render.SPACE_XS * 0.7):
        pytest.fail("BATTERY_ICON_NUB_W is not round(SPACE_XS * 0.7)")
    if render.BATTERY_ICON_NUB_H != round(render.SPACE_SM * 0.7):
        pytest.fail("BATTERY_ICON_NUB_H is not round(SPACE_SM * 0.7)")
    if render.BATTERY_ICON_STROKE_PX != 2:
        pytest.fail("BATTERY_ICON_STROKE_PX != 2")
    if render.BATTERY_ICON_STROKE_PX < render.FRAME_STROKE_PX:
        pytest.fail("BATTERY_ICON_STROKE_PX dropped below FRAME_STROKE_PX, the legibility floor")
    if render.BATTERY_ICON_LEFT is not render.MARGIN:
        pytest.fail("BATTERY_ICON_LEFT is not MARGIN")
    if render.BATTERY_ICON_BOTTOM != render.HEIGHT - render.MARGIN:
        pytest.fail("BATTERY_ICON_BOTTOM != HEIGHT - MARGIN")
    body_top = render.BATTERY_ICON_BOTTOM - render.BATTERY_ICON_BODY_H
    nub_top = body_top + (render.BATTERY_ICON_BODY_H - render.BATTERY_ICON_NUB_H) // 2
    nub_bottom = nub_top + render.BATTERY_ICON_NUB_H
    gap_above = nub_top - body_top
    gap_below = render.BATTERY_ICON_BOTTOM - nub_bottom
    if gap_above < 0 or gap_below < 0 or (gap_below - gap_above) not in (0, 1):
        pytest.fail("nub is not centred to within one pixel: gap_above=%r gap_below=%r" % (gap_above, gap_below))
    total = (
        render.BATTERY_ICON_LEFT, body_top,
        render.BATTERY_ICON_LEFT + render.BATTERY_ICON_BODY_W + render.BATTERY_ICON_NUB_W,
        render.BATTERY_ICON_BOTTOM,
    )
    if total != (64, 1514, 115, 1536):
        pytest.fail("computed total bounding box %r != (64, 1514, 115, 1536)" % (total,))


# The aircraft-to-text gap must be a property of the layout, not of
# whichever airline is flying. Three real vendored files are chosen for
# maximal spread in transparent bottom padding, measured with the
# renderer's own alpha threshold at the main card's 992px render width:
# 37px, 74px and 174px. These checks are deliberately
# illustration-file-agnostic: they assert the gap is identical across the
# three, never that any file lands on a particular pixel row.
# Re-anchoring either text block to `.rect` would fail them immediately,
# no matter how the constants were retuned.
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


def test_main_text_gap_is_constant_across_illustrations():
    """the main flight text sits exactly MAIN_TEXT_GAP_PX below the aircraft's last actually-painted pixel row, identically for illustrations whose transparent bottom padding differs by over 100px (illustration-crop-text-margin: no full-rectangle anchoring)"""
    measured = {name: _measured_gaps(name) for name in GAP_SPREAD_ILLUSTRATIONS}
    pads = {name: m[2] for name, m in measured.items()}
    if max(pads.values()) - min(pads.values()) < 100:
        pytest.fail("these fixtures no longer span a wide range of transparent bottom padding (%r) - the check "
            "would pass trivially and must be re-pointed at files that do" % (pads,))
    gaps = {name: m[0] for name, m in measured.items()}
    if len(set(gaps.values())) != 1:
        pytest.fail("the gap between the aircraft's last painted pixel and the main text varies by illustration: %r "
            "(bottom padding %r) - the text is anchored to the illustration's full rectangle, not its opaque "
            "content bbox" % (gaps, pads))
    only = next(iter(set(gaps.values())))
    if only != render.MAIN_TEXT_GAP_PX:
        pytest.fail("constant main gap is %dpx, expected MAIN_TEXT_GAP_PX (%d)" % (only, render.MAIN_TEXT_GAP_PX))


def test_previous_text_gap_is_constant_across_illustrations():
    """the previous flight text sits exactly PREVIOUS_TEXT_GAP_PX below its aircraft's last actually-painted pixel row, identically across illustrations with very different transparent bottom padding"""
    measured = {name: _measured_gaps(name) for name in GAP_SPREAD_ILLUSTRATIONS}
    pads = {name: m[3] for name, m in measured.items()}
    if max(pads.values()) - min(pads.values()) < 50:
        pytest.fail("these fixtures no longer span a wide range of transparent bottom padding at the previous card's "
            "scale (%r) - the check would pass trivially" % (pads,))
    gaps = {name: m[1] for name, m in measured.items()}
    if len(set(gaps.values())) != 1:
        pytest.fail("the gap between the previous aircraft's last painted pixel and its text varies by illustration: %r "
            "(bottom padding %r) - the previous text block is anchored to the full rectangle" % (gaps, pads))
    only = next(iter(set(gaps.values())))
    if only != render.PREVIOUS_TEXT_GAP_PX:
        pytest.fail("constant previous gap is %dpx, expected PREVIOUS_TEXT_GAP_PX (%d)" % (only, render.PREVIOUS_TEXT_GAP_PX))


def test_opaque_bbox_uses_the_paste_threshold_not_a_naive_getbbox():
    """_opaque_bbox() measures the hard-thresholded paste mask, never a naive Image.getbbox() - the soft drop-shadow band (alpha 1..127) that is never painted must not count as content"""
    path = _illustration_path("air-france.png")
    rgba = Image.open(path).convert("RGBA")
    naive_rgba = rgba.getbbox()
    naive_alpha = rgba.getchannel("A").getbbox()
    thresholded = render._opaque_bbox(rgba)
    if thresholded is None:
        pytest.fail("_opaque_bbox() returned None for a real vendored illustration")
    if naive_alpha[3] != rgba.size[1]:
        pytest.fail("fixture drift: air-france.png's raw-alpha bbox bottom is %d, not the full height %d - it no longer "
            "demonstrates the soft-shadow trap this check exists to guard" % (naive_alpha[3], rgba.size[1]))
    if thresholded[3] >= naive_alpha[3] or thresholded[3] >= naive_rgba[3]:
        pytest.fail("_opaque_bbox() bottom (%d) is not strictly above the naive bboxes (rgba %d, alpha %d) - it is "
            "counting sub-threshold drop-shadow pixels that draw_illustration() never paints"
            % (thresholded[3], naive_rgba[3], naive_alpha[3]))
    # And it must agree exactly with the mask actually handed to paste().
    painted = render._threshold_alpha(rgba).getbbox()
    if thresholded != painted:
        pytest.fail("_opaque_bbox() %r disagrees with the mask draw_illustration() pastes with %r - layout and painting "
            "must measure the same pixels" % (thresholded, painted))


def test_placement_content_is_strictly_inside_its_rect():
    """draw_illustration() returns a placement whose .content is strictly contained in .rect, with a strictly higher bottom edge, for real vendored art (structural guard against restoring full-rectangle anchoring)"""
    path = _illustration_path("air-france.png")
    inner_width = panel_format.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
    main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
    resized = render._resize_illustration(path, main_w)
    canvas = panel_format.new_canvas(IDX_BLUE)
    placement = render.draw_illustration(canvas, resized, 100, 200)
    rect, content = placement.rect, placement.content
    if rect != (100, 200, 100 + resized.size[0], 200 + resized.size[1]):
        pytest.fail("placement.rect %r is not the full pasted rectangle" % (rect,))
    if content == rect:
        pytest.fail("placement.content is identical to placement.rect for real vendored art - draw_illustration() is "
            "not measuring the painted pixels, and every text gap will drift per airline again")
    if not (rect[0] <= content[0] and rect[1] <= content[1] and content[2] <= rect[2] and content[3] <= rect[3]):
        pytest.fail("placement.content %r is not contained within placement.rect %r" % (content, rect))
    if content[3] >= rect[3]:
        pytest.fail("placement.content's bottom (%d) is not above placement.rect's bottom (%d) - the transparent bottom "
            "padding this fix exists to exclude is still being counted" % (content[3], rect[3]))


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


def test_main_illustration_is_centred_on_its_visible_pixels():
    """the main illustration's VISIBLE horizontal midpoint sits on the canvas centre (within rounding) for files with sharply different left/right padding asymmetry - centred by painted pixels, not by rectangle"""
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
        pytest.fail("the main aircraft's visible horizontal midpoint is off the canvas centre by up to %.1fpx %r - "
            "the illustration is being centred by its source rectangle, not its painted pixels" % (worst, offsets))


def test_previous_card_and_text_align_to_the_main_aircrafts_visible_right_edge():
    """the previous aircraft's visible right edge lands exactly on the main aircraft's visible right edge, and the previous text right-aligns to that same shared line minus the optical offset, for two files with very different right padding"""
    main_placement, prev_placement, text_calls = _render_two_cards(
        "km-malta-airlines.png", "transavia-france.png")
    main_right = main_placement.content[2]
    prev_right = prev_placement.content[2]
    # Guard: the two files must actually differ in right padding, or the
    # check proves nothing.
    main_pad = main_placement.rect[2] - main_placement.content[2]
    prev_pad = prev_placement.rect[2] - prev_placement.content[2]
    if abs(main_pad - prev_pad) < 10:
        pytest.fail("fixture drift: main/previous right padding are now %dpx/%dpx - too close for this check to "
            "distinguish visible-edge from rectangle alignment" % (main_pad, prev_pad))
    if prev_right != main_right:
        pytest.fail("the previous aircraft's visible right edge is at x=%d but the main aircraft's is at x=%d (%dpx "
            "apart) - the cards are aligned rectangle-to-rectangle, not aircraft-to-aircraft"
            % (prev_right, main_right, prev_right - main_right))
    prev_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
    anchor_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line1)
    expected_anchor_x = prev_right - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
    if anchor_x != expected_anchor_x:
        pytest.fail("the previous flight text is right-aligned to x=%d, but its aircraft's visible right edge minus "
            "PREVIOUS_TEXT_LEFT_OFFSET_PX (%d) is x=%d - text and illustration are not aligned per D-12"
            % (anchor_x, render.PREVIOUS_TEXT_LEFT_OFFSET_PX, expected_anchor_x))


def test_previous_card_both_lines_share_one_anchor_at_the_optical_offset():
    """the previous card's two text lines share one anchor x, equal to the previous aircraft's measured opaque right edge minus PREVIOUS_TEXT_LEFT_OFFSET_PX"""
    _main_placement, prev_placement, text_calls = _render_two_cards(
        "transavia-france.png", "vueling-airlines.png")
    prev_line1 = "%s from %s" % (TEST_PREVIOUS_ROUTE["callsign_iata"], TEST_PREVIOUS_ROUTE["origin_city"])
    type_label = render._TYPE_DISPLAY_LABELS[TEST_PREVIOUS_FLIGHT["aircraft_type"]]
    prev_line2 = "%s · %s" % (TEST_PREVIOUS_ROUTE["airline_name"], type_label)
    line1_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line1)
    line2_x = next(xy[0] for t, xy, _a in text_calls if t == prev_line2)
    if line1_x != line2_x:
        pytest.fail("previous card's two lines anchor at different x (%d vs %d) - they must share one anchor" % (line1_x, line2_x))
    expected_x = prev_placement.content[2] - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
    if line1_x != expected_x:
        pytest.fail("previous card's shared anchor x=%d, expected the aircraft's visible right edge minus "
            "PREVIOUS_TEXT_LEFT_OFFSET_PX = %d" % (line1_x, expected_x))


def test_main_card_text_remains_centred_not_offset():
    """the main card's text lines stay centred on the canvas midpoint with anchor='ma', unaffected by the previous card's optical offset"""
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
            pytest.fail("main line %r was not drawn" % (text,))
        xy, anchor = calls[0]
        if xy[0] != center_x or anchor != "ma":
            pytest.fail("main line %r drawn at x=%r anchor=%r, expected centre x=%d anchor='ma' - the main card must "
                "not receive the previous card's optical offset (D-12)" % (text, xy[0], anchor, center_x))


def test_tier3_promotion_on_main_card():
    """an airline-only route on the main card omits line 1 entirely, promoting line 2 to line 1's y-position, with no empty-string draw call"""
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
        pytest.fail("an empty-string draw call was made for the omitted line 1: %r" % (main_region_calls,))
    if texts_in_region != [expected_line2]:
        pytest.fail("expected exactly one text draw (%r) in the main block region, got %r" % (expected_line2, texts_in_region))
    expected_y = main_placement.content[3] + render.MAIN_TEXT_GAP_PX
    actual_y = main_region_calls[0][1][1]
    if actual_y != expected_y:
        pytest.fail("line 2's y is %d, expected %d (main_placement.content[3] + MAIN_TEXT_GAP_PX, the y line 1 would "
            "have used)" % (actual_y, expected_y))


def test_tier3_promotion_on_previous_card():
    """an airline-only route on the previous card omits its own line 1, promoting line 2 to line 1's y-position using the previous card's own gap constant, with no empty-string draw call - the check that catches the change implemented in only one of the two functions"""
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
        pytest.fail("an empty-string draw call was made for the previous card's omitted line 1: %r" % (prev_region_calls,))
    if texts_in_region != [expected_line2]:
        pytest.fail("expected exactly one text draw (%r) in the previous block region, got %r" % (expected_line2, texts_in_region))
    expected_y = prev_placement.content[3] + render.PREVIOUS_TEXT_GAP_PX
    actual_y = prev_region_calls[0][1][1]
    if actual_y != expected_y:
        pytest.fail("previous card's line 2 y is %d, expected %d (prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX)"
            % (actual_y, expected_y))


def test_tier3_on_both_cards_simultaneously():
    """both cards independently omit line 1 and promote line 2 on a simultaneous airline-only render, without interfering with each other"""
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
        pytest.fail("expected the main card's promoted line 2 %r among the text draws, got %r" % (expected_main_line2, texts))
    if expected_prev_line2 not in texts:
        pytest.fail("expected the previous card's promoted line 2 %r among the text draws, got %r" % (expected_prev_line2, texts))
    if "" in texts:
        pytest.fail("an empty-string draw call was made somewhere: %r" % (texts,))


def test_previous_card_is_vertically_centred_on_its_visible_pixels():
    """the previous card's VISIBLE vertical midpoint sits on the PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC line (within rounding) across illustrations with very different top/bottom padding - no per-file vertical drift"""
    centre_line = panel_format.HEIGHT * render.PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC
    offsets = {}
    for name in ("asl-airlines-france.png", "air-europa.png", "iberia-airlines.png", "amelia.png"):
        _main, prev_placement, _text = _render_two_cards("transavia-france.png", name)
        content = prev_placement.content
        offsets[name] = (content[1] + content[3]) / 2.0 - centre_line
    worst = max(abs(v) for v in offsets.values())
    if worst > 0.5:
        pytest.fail("the previous aircraft's visible vertical midpoint is off the %.1f centre line by up to %.1fpx %r - "
            "the card is being centred by its source rectangle, so it drifts vertically per illustration"
            % (centre_line, worst, offsets))


def test_theme_default_matches_no_theme_arg():
    """render_panel() with no theme_id is byte-identical to an explicit default theme_id"""
    a = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    b = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=render.device_config.DEFAULT_THEME_ID)
    if a != b:
        pytest.fail("render_panel() with no theme_id differs from an explicit default theme_id - CFG-01's default path must be byte-identical")


def test_white_theme_canvas_matches_default_and_others_differ():
    """build_canvas(theme_id='white') matches the no-theme default, and every other registered theme genuinely differs from it - none is a silent no-op"""
    default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    white_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="white")
    if list(default_canvas.getdata()) != list(white_canvas.getdata()):
        pytest.fail("build_canvas(theme_id='white') differs from build_canvas() with no theme_id - White must be the default")
    default_data = list(default_canvas.getdata())
    for theme_id in render.device_config.THEME_IDS:
        if theme_id == "white":
            continue
        other_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
        if default_data == list(other_canvas.getdata()):
            pytest.fail("build_canvas(theme_id=%r) is identical to the White default canvas - every registered theme must be genuinely distinct" % (theme_id,))


def test_unknown_theme_degrades_to_default_canvas():
    """build_canvas(theme_id='not-a-theme') produces the default theme's canvas rather than raising"""
    default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    try:
        unknown_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="not-a-theme")
    except Exception as exc:
        pytest.fail("build_canvas(theme_id='not-a-theme') raised %r - an unknown theme must degrade to the default" % (exc,))
    if list(default_canvas.getdata()) != list(unknown_canvas.getdata()):
        pytest.fail("build_canvas(theme_id='not-a-theme') produced a canvas different from the default theme's")


def test_unknown_state_still_raises_naming_all_three_states():
    """build_canvas(flight, 'nonsense-state') still raises ValueError naming departing/arriving/empty"""
    try:
        render.build_canvas(TEST_FLIGHT, "sideways")
    except ValueError as exc:
        message = str(exc)
        for word in ("departing", "arriving", "empty"):
            if word not in message:
                pytest.fail("ValueError message %r does not name %r" % (message, word))
        return
    except Exception as exc:
        pytest.fail("build_canvas(flight, 'sideways') raised %r, expected ValueError" % (exc,))
    pytest.fail("build_canvas(flight, 'sideways') did not raise - an unknown state must stay loud")


def test_legal_palette_holds_for_every_theme():
    """_assert_legal_palette() (run internally by build_canvas()) passes for every registered theme"""
    for theme_id in render.device_config.THEME_IDS:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)


def test_per_theme_dominant_background_holds_in_both_states():
    """for every registered theme, in both departing and arriving states, a real two-flight panel's dominant nibble is that theme's own background - the flat-field guard rail against a large livery area"""
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
                pytest.fail("theme %r state %r: dominant nibble is 0x%x, expected 0x%x (the theme's own background)"
                    % (theme_id, state, dom, expected_nibble))


def test_ink_index_matches_theme_registry_for_every_theme():
    """render.state_ink_index() agrees with device_config.theme_ink_index() for every registered theme, in both departing and arriving states"""
    for theme_id in render.device_config.THEME_IDS:
        expected = render.device_config.theme_ink_index(theme_id)
        for state in ("departing", "arriving"):
            got = render.state_ink_index(state, theme_id=theme_id)
            if got != expected:
                pytest.fail("state_ink_index(%r, theme_id=%r) = %r, expected device_config.theme_ink_index(%r) = %r"
                    % (state, theme_id, got, theme_id, expected))


def test_runway_tag_text_default_matches_top_right_tag():
    """runway_tag_text() with no argument returns exactly TOP_RIGHT_TAG_TEXT (default render unchanged)"""
    if render.runway_tag_text() != render.TOP_RIGHT_TAG_TEXT:
        pytest.fail("runway_tag_text() != render.TOP_RIGHT_TAG_TEXT")


def test_runway_tag_text_matches_registry_for_other_runways():
    """runway_tag_text('06-24')/('02-20') return the strings from device_config.RUNWAYS"""
    for runway_id in ("06-24", "02-20"):
        expected = render.device_config.runway_tag_text(runway_id)
        got = render.runway_tag_text(runway_id)
        if got != expected:
            pytest.fail("runway_tag_text(%r) = %r, expected %r" % (runway_id, got, expected))


def test_runway_tag_text_unknown_id_degrades_to_default():
    """runway_tag_text('unknown') returns the default runway's tag rather than raising"""
    if render.runway_tag_text("nope") != render.runway_tag_text():
        pytest.fail("runway_tag_text('nope') != runway_tag_text() - an unknown runway id must degrade to the default")


def test_empty_canvas_draws_selected_runways_heading():
    """build_canvas(None, 'empty', runway_id=...) draws that runway's heading as a tracked label, including the longest of the three, and passes the safe-box assertion"""
    longest_runway_id = max(
        render.device_config.RUNWAY_IDS, key=lambda rid: len(render.device_config.runway_empty_heading(rid))
    )
    with _TextSpy(render) as spy:
        render.build_canvas(None, "empty", runway_id=longest_runway_id)
    expected = render.empty_heading_text(longest_runway_id).upper()
    glyphs = [t for t, _xy, _anchor in spy.calls if len(t) == 1]
    joined = "".join(glyphs)
    if expected not in joined:
        pytest.fail("expected the longest runway heading %r (upper-cased, tracked glyph-by-glyph) in the "
            "single-glyph draw run, got %r" % (expected, joined))


def test_active_canvas_draws_selected_runways_tag():
    """build_canvas(flight, 'departing', runway_id='06-24') draws that runway's tag glyph-by-glyph, passing the within-canvas assertion"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, runway_id="06-24")
    top_row = [(t, xy, a) for t, xy, a in spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
    label_text = render.STATE_LABEL_TEXT["departing"]
    expected_tag = render.runway_tag_text("06-24")
    tag_glyphs = top_row[len(label_text):len(label_text) + len(expected_tag)]
    joined_tag = "".join(t for t, _xy, _a in tag_glyphs)
    if joined_tag != expected_tag:
        pytest.fail("reconstructed tag glyph run = %r, expected the runway 06-24 tag %r" % (joined_tag, expected_tag))


def test_source_fault_false_matches_default():
    """render_panel(..., source_fault=False) is byte-identical to the same call without the argument"""
    a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE)
    b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
    if a != b:
        pytest.fail("render_panel(source_fault=False) differs from the default call")


def test_source_fault_true_differs_from_false():
    """render_panel(..., source_fault=True) differs from the same call with the flag false"""
    a = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=False)
    b = render.render_panel(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=True)
    if a == b:
        pytest.fail("render_panel(source_fault=True) is byte-identical to source_fault=False - the badge is not actually drawn")


def test_badge_caption_present_on_active_and_empty_canvases():
    """the source-fault badge is drawn on both the active canvas and the empty canvas (visible in every state)"""
    with _TextSpy(render) as spy_active:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True)
    with _TextSpy(render) as spy_empty:
        render.build_canvas(None, "empty", source_fault=True)
    active_texts = [t for t, _xy, _anchor in spy_active.calls]
    empty_texts = [t for t, _xy, _anchor in spy_empty.calls]
    if render.SOURCE_FAULT_TEXT not in active_texts:
        pytest.fail("SOURCE_FAULT_TEXT missing from the active-state text draws with source_fault=True")
    if render.SOURCE_FAULT_TEXT not in empty_texts:
        pytest.fail("SOURCE_FAULT_TEXT missing from the empty-state text draws with source_fault=True")


def test_badge_caption_absent_from_a_normal_render():
    """the badge caption text is absent from a normal render (source_fault defaults to False)"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    texts = [t for t, _xy, _anchor in spy.calls]
    if render.SOURCE_FAULT_TEXT in texts:
        pytest.fail("SOURCE_FAULT_TEXT appeared in a normal render with no source_fault flag")


def test_legal_palette_holds_with_badge_across_states_and_themes():
    """_assert_legal_palette() (run internally by build_canvas()) passes with the badge drawn, in both active states, the empty state, and every theme"""
    for theme_id in render.device_config.THEME_IDS:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True, theme_id=theme_id)
        render.build_canvas(TEST_FLIGHT, "arriving", route=TEST_ROUTE, source_fault=True, theme_id=theme_id)
    render.build_canvas(None, "empty", source_fault=True)


def test_fault_badged_departing_render_satisfies_legal_palette_via_build_canvas():
    """a fault-badged departing render still satisfies _assert_legal_palette() for the default theme (proven via build_canvas(), not a re-implementation)"""
    render.build_canvas(
        TEST_FLIGHT, "departing", route=TEST_ROUTE, source_fault=True, theme_id=render.device_config.DEFAULT_THEME_ID
    )


def test_badge_bbox_stays_inside_the_drawn_frame():
    """draw_source_fault_badge()'s bounding box stays inside the drawn frame"""
    canvas = panel_format.new_canvas(IDX_BLUE)
    frame_box = render.draw_frame(canvas, IDX_WHITE)
    badge_bbox = render.draw_source_fault_badge(canvas, IDX_WHITE)
    fl, ft, fr, fb = frame_box
    bl, bt, br, bb = badge_bbox
    if not (bl >= fl and bt >= ft and br <= fr and bb <= fb):
        pytest.fail("badge bbox %r is not contained within the frame bbox %r" % (badge_bbox, frame_box))


def test_badge_caption_uses_its_theme_declared_weight():
    """the source-fault badge's caption respects its theme's declared weight, same as every other active-state role"""
    for theme_id in render.device_config.THEME_IDS:
        requested_paths = _spy_requested_font_paths_with_fault(theme_id)
        if not requested_paths:
            pytest.fail("%r: no font was requested at all - the spy did not capture anything" % (theme_id,))
        declared_weight = render.device_config.theme_weight(theme_id)
        wrong_suffix = "PTSerif-Regular.ttf" if declared_weight == "bold" else "PTSerif-Bold.ttf"
        wrong_hits = [p for p in requested_paths if p.endswith(wrong_suffix)]
        if wrong_hits:
            pytest.fail("%r (declared weight %r): the fault badge requested %s %d time(s) - expected zero: %r" % (
                theme_id, declared_weight, wrong_suffix, len(wrong_hits), wrong_hits))


def test_badge_exclamation_dot_paints_more_than_one_pixel():
    """the source-fault badge's exclamation-mark dot paints a visible multi-pixel area, not a single point"""
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
        pytest.fail("the exclamation dot painted only %d ink pixel(s) around (%d, %d) - expected a visible multi-pixel "
            "dot, not a single point (code-review WR-02)" % (count, stroke_x, dot_y))


def test_runway_and_theme_matrix_combines_without_error():
    """all three runway ids combined with the single theme id render without error across both active states (theme-addition regression guard)"""
    for runway_id in render.device_config.RUNWAY_IDS:
        for theme_id in render.device_config.THEME_IDS:
            for state in ("departing", "arriving"):
                render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE, runway_id=runway_id, theme_id=theme_id)


def test_no_frame_outline_on_real_active_renders():
    """the frame outline is genuinely absent from a real build_canvas() render - every sampled point on the former frame band reads the state's own background index or its dithered White speckle, in both active states"""
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
                pytest.fail("state=%r point=%r read index %r, expected one of %r (former D-26 outline band)"
                    % (state, point, sample, allowed))





def test_cli_airline_and_city_flags_reach_captions(tmp_path):
    """--airline/--city CLI flags reach the rendered captions via render.main()"""
    preview_path = str(tmp_path / "preview.png")
    with _TextSpy(render) as spy:
        rc = render.main([
            "--state", "departing", "--callsign", "AFR56XX",
            "--airline", "Test Airline Override Name",
            "--city", "Test City Override Name",
            "--preview", preview_path,
        ])
    if rc != 0:
        pytest.fail("render.main() exited %r, expected 0" % (rc,))
    texts = [text for text, _xy, _anchor in spy.calls]
    if not any("Test City Override Name" in t for t in texts):
        pytest.fail("--city override text not found in any drawn text: %r" % (texts,))
    if not any("Test Airline Override Name" in t for t in texts):
        pytest.fail("--airline override text not found in any drawn text: %r" % (texts,))





def test_cli_no_route_wins_over_airline_and_city(tmp_path):
    """--no-route still overrides --airline/--city ('Unknown flight', ROUTE_FALLBACK_TEXT, never the raw callsign)"""
    preview_path = str(tmp_path / "preview.png")
    with _TextSpy(render) as spy:
        rc = render.main([
            "--state", "departing", "--callsign", "AFR56XX",
            "--airline", "Should Not Appear Airline",
            "--city", "Should Not Appear City",
            "--no-route", "--preview", preview_path,
        ])
    if rc != 0:
        pytest.fail("render.main() exited %r, expected 0" % (rc,))
    texts = [text for text, _xy, _anchor in spy.calls]
    if any("Should Not Appear" in t for t in texts):
        pytest.fail("--no-route did not win over --airline/--city overrides: %r" % (texts,))
    if "Unknown flight" not in texts:
        pytest.fail("expected 'Unknown flight' with --no-route in effect (D-10 tier 4), got: %r" % (texts,))
    if render.ROUTE_FALLBACK_TEXT not in texts:
        pytest.fail("expected ROUTE_FALLBACK_TEXT with --no-route in effect, got: %r" % (texts,))
    if "AFR56XX" in texts:
        pytest.fail("the raw callsign 'AFR56XX' must never appear with --no-route in effect (D-08), got: %r" % (texts,))





def test_calibration_preview_writes_exactly_one_file(tmp_path):
    """--calibration-preview writes exactly one file (palette-swatches.png)"""
    tmp_dir = str(tmp_path)
    rc = render.main(["--calibration-preview", tmp_dir])
    if rc != 0:
        pytest.fail("render.main(['--calibration-preview', ...]) exited %r, expected 0" % (rc,))
    written = sorted(os.listdir(tmp_dir))
    if written != ["palette-swatches.png"]:
        pytest.fail("expected exactly one file 'palette-swatches.png' in %r, got %r" % (tmp_dir, written))





def test_synthetic_reminder_printed_when_override_combined_with_out(tmp_path):
    """combining --no-route with --out prints the skypane-poll.timer restart reminder"""
    out_path = str(tmp_path / "out.bin")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = render.main([
            "--state", "departing", "--callsign", "AFR56XX", "--no-route", "--out", out_path,
        ])
    if rc != 0:
        pytest.fail("render.main() exited %r, expected 0" % (rc,))
    stdout_text = buf.getvalue()
    if "skypane-poll.timer" not in stdout_text:
        pytest.fail("expected a synthetic-panel reminder naming skypane-poll.timer, got stdout: %r" % (stdout_text,))





def test_cli_default_preview_draws_tier1_with_identifier(tmp_path):
    """the default CLI preview (no forcing flags) draws a tier-1 line containing the preview route's real identifier"""
    preview_path = str(tmp_path / "preview.png")
    with _TextSpy(render) as spy:
        rc = render.main(["--state", "departing", "--preview", preview_path])
    if rc != 0:
        pytest.fail("render.main() exited %r, expected 0" % (rc,))
    texts = [t for t, _xy, _a in spy.calls]
    expected = "%s to %s" % (render._PREVIEW_ROUTE["callsign_iata"], render._PREVIEW_ROUTE["destination_city"])
    if expected not in texts:
        pytest.fail("expected the default preview's tier-1 line %r among the text draws, got %r" % (expected, texts))





def test_cli_no_identifier_flag_forces_tier2(tmp_path):
    """--no-identifier forces the default preview into tier 2 (title-case direction + city, no identifier)"""
    preview_path = str(tmp_path / "preview.png")
    with _TextSpy(render) as spy:
        rc = render.main(["--state", "departing", "--no-identifier", "--preview", preview_path])
    if rc != 0:
        pytest.fail("render.main() exited %r, expected 0" % (rc,))
    texts = [t for t, _xy, _a in spy.calls]
    expected = "To %s" % (render._PREVIEW_ROUTE["destination_city"],)
    if expected not in texts:
        pytest.fail("expected --no-identifier's tier-2 line %r among the text draws, got %r" % (expected, texts))
    if any(render._PREVIEW_ROUTE["callsign_iata"] in t for t in texts):
        pytest.fail("the preview route's identifier leaked into a drawn text despite --no-identifier: %r" % (texts,))





def test_cli_no_identifier_is_a_noop_with_no_route_and_airline_only(tmp_path):
    """--no-identifier combined with --no-route still produces tier 4, and combined with --preview-airline-only still produces tier 3 with no line 1 - both are no-ops"""
    tmp1_path = str(tmp_path / "no-route.png")
    tmp2_path = str(tmp_path / "airline-only.png")
    with _TextSpy(render) as spy_no_route:
        rc1 = render.main(["--state", "departing", "--no-identifier", "--no-route", "--preview", tmp1_path])
    with _TextSpy(render) as spy_airline_only:
        rc2 = render.main(["--state", "departing", "--no-identifier", "--preview-airline-only", "--preview", tmp2_path])
    if rc1 != 0 or rc2 != 0:
        pytest.fail("render.main() exited %r/%r, expected 0/0" % (rc1, rc2))
    texts_no_route = [t for t, _xy, _a in spy_no_route.calls]
    texts_airline_only = [t for t, _xy, _a in spy_airline_only.calls]
    if "Unknown flight" not in texts_no_route:
        pytest.fail("expected tier-4 'Unknown flight' with --no-identifier + --no-route (a no-op combo), got %r" % (texts_no_route,))
    if "" in texts_airline_only:
        pytest.fail("an empty-string draw call was made with --no-identifier + --preview-airline-only: %r" % (texts_airline_only,))
    if render._PREVIEW_ROUTE["airline_name"] not in texts_airline_only:
        pytest.fail(
            "expected tier-3 line 2 (airline name alone) with --no-identifier + --preview-airline-only "
            "(a no-op combo), got %r" % (texts_airline_only,)
        )





def test_cli_never_draws_raw_callsign_across_all_four_tiers(tmp_path):
    """no CLI path at any of the four content-ladder tiers draws the raw callsign passed via --callsign"""
    combos = [
        [],  # tier 1, default
        ["--no-identifier"],  # tier 2
        ["--preview-airline-only"],  # tier 3
        ["--no-route"],  # tier 4
    ]
    for i, extra in enumerate(combos):
        preview_path = str(tmp_path / ("cli-%d.png" % i))
        with _TextSpy(render) as spy:
            rc = render.main(["--state", "departing", "--callsign", "DISTINCTCLI99"] + extra + ["--preview", preview_path])
        if rc != 0:
            pytest.fail("render.main() exited %r for flags %r, expected 0" % (rc, extra))
        texts = [t for t, _xy, _a in spy.calls]
        if any("DISTINCTCLI99" in t for t in texts):
            pytest.fail("the raw callsign 'DISTINCTCLI99' leaked into a drawn text with flags %r (D-08): %r" % (extra, texts))


# The previous card's optical offset, spot-checked across a deliberately
# diverse illustration sample rather than just the single Air France /
# Vueling pair it was tuned against.
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


def test_previous_card_optical_offset_holds_across_diverse_illustration_sample():
    """the previous card's optical offset holds its shared-anchor and safe-box invariants across six airline illustrations with deliberately different airframe silhouettes (narrowbody x2, turboprop, small twin, regional jet, widebody) - not just the single pair it was tuned against"""
    paddings = {}
    for airline_name, expected_filename, _airframe in OFFSET_SPREAD_AIRLINES:
        route = dict(TEST_PREVIOUS_ROUTE)
        route["airline_name"] = airline_name
        resolved = illustrations.select_illustration(route, None)
        if resolved is None or os.path.basename(resolved) != expected_filename:
            pytest.fail("airline %r resolved to %r, expected %r - the sample no longer resolves to the "
                "documented fixed file, this check must be re-pointed" % (
                    airline_name, os.path.basename(resolved) if resolved else None, expected_filename,
                ))
        with _PlacementSpy(render) as placements:
            with _TextBBoxSpy(render) as bboxes:
                render.build_canvas(
                    TEST_FLIGHT, "departing", route=TEST_ROUTE,
                    previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=route,
                    previous_state="arriving",
                )
        if len(placements.placements) != 2:
            pytest.fail("airline %r: expected 2 illustration placements, got %d" % (
                airline_name, len(placements.placements),
            ))
        _main_placement, prev_placement = placements.placements
        paddings[airline_name] = prev_placement.rect[2] - prev_placement.content[2]

        prev_line1 = "%s from %s" % (route["callsign_iata"], route["origin_city"])
        type_label = render._TYPE_DISPLAY_LABELS[TEST_PREVIOUS_FLIGHT["aircraft_type"]]
        prev_line2 = "%s · %s" % (route["airline_name"], type_label)
        b1 = next((bb for t, _xy, _a, bb in bboxes.calls if t == prev_line1), None)
        b2 = next((bb for t, _xy, _a, bb in bboxes.calls if t == prev_line2), None)
        if b1 is None or b2 is None:
            pytest.fail("airline %r: expected both previous-card lines drawn, got %r" % (
                airline_name, [t for t, _xy, _a, _bb in bboxes.calls],
            ))
        if b1[2] != b2[2]:
            pytest.fail("airline %r: previous card's two lines anchor at different x (%d vs %d)" % (
                airline_name, b1[2], b2[2],
            ))
        expected_x = prev_placement.content[2] - render.PREVIOUS_TEXT_LEFT_OFFSET_PX
        if b1[2] != expected_x:
            pytest.fail("airline %r: shared anchor x=%d, expected the aircraft's measured opaque right edge minus "
                "PREVIOUS_TEXT_LEFT_OFFSET_PX = %d" % (airline_name, b1[2], expected_x))
        safe_left = render.SAFE_BOX[0]
        if b1[0] < safe_left or b2[0] < safe_left:
            pytest.fail("airline %r: a previous-card line's bbox (line1=%r, line2=%r) crosses the safe box's left "
                "edge (x=%d) - the offset narrowed fit_text_size()'s width budget past what this text needs"
                % (airline_name, b1, b2, safe_left))
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


def test_label_tracking_constant_and_helpers_present():
    """LABEL_TRACKING_PX == 6 and draw_tracked_text()/_tracked_text_width()/_tracked_text_bbox() exist with the original commit's public/private naming split"""
    if render.LABEL_TRACKING_PX != 6:
        pytest.fail("render.LABEL_TRACKING_PX = %r, expected 6" % (render.LABEL_TRACKING_PX,))
    if not hasattr(render, "draw_tracked_text"):
        pytest.fail("render.draw_tracked_text is missing (expected public, no leading underscore)")
    if not hasattr(render, "_tracked_text_width"):
        pytest.fail("render._tracked_text_width is missing (expected private)")
    if not hasattr(render, "_tracked_text_bbox"):
        pytest.fail("render._tracked_text_bbox is missing (expected private)")
    if hasattr(render, "_draw_tracked_text"):
        pytest.fail("render._draw_tracked_text should not exist - draw_tracked_text is public")


def test_tracked_text_width_arithmetic():
    """_tracked_text_width() arithmetic holds for empty/single-char/multi-char/zero-tracking, derived from font.getlength() rather than hardcoded pixel numbers"""
    font = render._role_font(render.TOP_TAG_FONT, "bold")
    empty = render._tracked_text_width(font, "", 6)
    if empty != 0.0:
        pytest.fail("_tracked_text_width(font, '', 6) = %r, expected 0.0" % (empty,))
    single = render._tracked_text_width(font, "A", 6)
    expected_single = font.getlength("A")
    if single != expected_single:
        pytest.fail("_tracked_text_width(font, 'A', 6) = %r, expected font.getlength('A') = %r "
            "(a single glyph carries no trailing tracking)" % (single, expected_single))
    text = "ORY"
    expected_multi = sum(font.getlength(ch) for ch in text) + 6 * (len(text) - 1)
    got_multi = render._tracked_text_width(font, text, 6)
    if got_multi != expected_multi:
        pytest.fail("_tracked_text_width(font, %r, 6) = %r, expected %r" % (text, got_multi, expected_multi))
    expected_zero = sum(font.getlength(ch) for ch in text)
    got_zero = render._tracked_text_width(font, text, 0)
    if got_zero != expected_zero:
        pytest.fail("_tracked_text_width(font, %r, 0) = %r, expected plain summed advance %r"
            % (text, got_zero, expected_zero))


def test_draw_tracked_text_glyph_by_glyph():
    """draw_tracked_text() issues one text draw per character at anchor='la', with inter-glyph advance == font.getlength(previous_char) + tracking, returning the x immediately after the last glyph's advance"""
    font = render._role_font(render.TOP_TAG_FONT, "bold")
    canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
    draw = render.ImageDraw.Draw(canvas)
    text = "ORY"
    with _TextSpy(render) as spy:
        end_x = render.draw_tracked_text(draw, (100, 200), text, font, panel_format.IDX_BLACK, tracking=6)
    calls = spy.calls
    if len(calls) != len(text):
        pytest.fail("draw_tracked_text issued %d text draws, expected %d (one per character)" % (len(calls), len(text)))
    joined = "".join(c[0] for c in calls)
    if joined != text:
        pytest.fail("joined glyph draws = %r, expected %r" % (joined, text))
    if any(a != "la" for _, _, a in calls):
        pytest.fail("not every glyph draw used anchor='la': %r" % ([a for _, _, a in calls],))
    x = 100
    for i, ch in enumerate(text):
        expected_xy = (x, 200)
        got_xy = calls[i][1]
        if got_xy != expected_xy:
            pytest.fail("glyph %d (%r) drawn at %r, expected %r" % (i, ch, got_xy, expected_xy))
        x += font.getlength(ch) + 6
    if end_x != x:
        pytest.fail("draw_tracked_text returned %r, expected %r (start_x + _tracked_text_width(...) + tracking)"
            % (end_x, x))


def test_top_row_inter_glyph_advance_matches_tracking():
    """every consecutive pair of glyph origins within the state-label and runway-tag runs differs by exactly font.getlength(previous_char) + LABEL_TRACKING_PX"""
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
                pytest.fail("glyph %d advance within %r run = %.3f, expected %.3f "
                    "(font.getlength(%r) + %d)" % (i, text, got_advance, expected_advance, prev_char, render.LABEL_TRACKING_PX))


def test_top_row_tracking_stays_within_canvas_across_runways_themes_states():
    """the tracked top row builds without an AssertionError and the computed tag start x is >= 0 for every registered runway id, both active states, and a flat and a dithered theme"""
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
                    pytest.fail("runway=%r theme=%r state=%r: computed tag start x = %.2f is negative"
                        % (runway_id, theme_id, state, tag_x))


def test_tracking_confined_to_top_row_roles_only():
    """for a full two-flight active render with source_fault=True, the main card's line 1, the previous card's line 1, and the source-fault caption are each still drawn as one whole-string call, and the total single-character draw count equals exactly len(label_text) + len(tag_text)"""
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
        pytest.fail("captured %d single-character draws, expected exactly %d (len(label_text) + len(tag_text))"
            % (len(single_char_calls), expected_count))
    whole_string_texts = [t for t, _xy, _a in spy.calls if len(t) > 1]
    main_line1 = render._flight_line1_text(TEST_FLIGHT, "departing", TEST_ROUTE)
    if main_line1 and main_line1 not in whole_string_texts:
        pytest.fail("main card line 1 %r not captured as a single whole-string draw" % (main_line1,))
    prev_line1 = render._flight_line1_text(TEST_PREVIOUS_FLIGHT, "arriving", TEST_PREVIOUS_ROUTE)
    if prev_line1 and prev_line1 not in whole_string_texts:
        pytest.fail("previous card line 1 %r not captured as a single whole-string draw" % (prev_line1,))
    if render.SOURCE_FAULT_TEXT not in whole_string_texts:
        pytest.fail("source-fault caption %r not captured as a single whole-string draw" % (render.SOURCE_FAULT_TEXT,))


def test_band_themes_render_without_exception():
    """every registered band theme (PHASE9-1) renders via build_canvas() in both departing and arriving states without exception"""
    band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
    if not band_theme_ids:
        pytest.fail("no band theme ids found in THEME_IDS - expected plan 09-01's 5 band entries")
    for theme_id in band_theme_ids:
        for state in ("departing", "arriving"):
            render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE, theme_id=theme_id)


def test_draw_diagonal_band_paints_only_legal_two_colour_set():
    """draw_diagonal_band() paints only {IDX_WHITE, band_idx} on a fresh White canvas, flat and dithered"""
    for band_idx, dithered in ((IDX_BLUE, False), (IDX_GREEN, True)):
        canvas = panel_format.new_canvas(IDX_WHITE)
        render.draw_diagonal_band(canvas, band_idx, dithered=dithered)
        colors = {value for _count, value in canvas.getcolors()}
        if not colors <= {IDX_WHITE, band_idx}:
            pytest.fail("draw_diagonal_band(band_idx=%r, dithered=%r) painted colours %r, expected a subset of "
                "{IDX_WHITE, %r}" % (band_idx, dithered, sorted(colors), band_idx))
        if band_idx not in colors:
            pytest.fail("draw_diagonal_band(band_idx=%r, dithered=%r) painted no %r pixels at all" % (
                band_idx, dithered, band_idx
            ))


def test_band_theme_top_labels_are_split():
    """a band theme's top labels are genuinely split into a merged state-label/airport-code run (e.g. 'DEPARTING FROM ORY') and a standalone runway-tag run (e.g. 'RWY 3'), both derived from runway_tag_text().partition(' · ') (PHASE9-3)"""
    band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
    if not band_theme_ids:
        pytest.fail("no band theme ids found in THEME_IDS")
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
        pytest.fail("reconstructed band-theme %r label = %r, expected %r" % (theme_id, joined_label, expected_label))
    if joined_tag != expected_tag:
        pytest.fail("reconstructed band-theme %r tag = %r, expected %r" % (theme_id, joined_tag, expected_tag))


def test_non_band_theme_top_labels_are_unsplit():
    """a non-band theme's (white, the default) top labels remain exactly STATE_LABEL_TEXT and the FULL runway tag, unsplit - both draw_top_labels()'s own default (called with no band_theme argument) and _build_active_canvas()'s wiring genuinely preserve today's behaviour"""
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
        pytest.fail("draw_top_labels() with no band_theme arg: label = %r, expected unsplit %r" % (direct_label, label_text))
    if direct_tag != full_tag:
        pytest.fail("draw_top_labels() with no band_theme arg: tag = %r, expected the FULL unsplit tag %r" % (direct_tag, full_tag))

    with _TextSpy(render) as wired_spy:
        render.build_canvas(
            TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=render.device_config.DEFAULT_THEME_ID
        )
    wired_top_row = [(t, xy, a) for t, xy, a in wired_spy.calls if len(t) == 1 and xy[1] == render.MARGIN]
    wired_label = "".join(t for t, _xy, _a in wired_top_row[: len(label_text)])
    wired_tag = "".join(t for t, _xy, _a in wired_top_row[len(label_text): len(label_text) + len(full_tag)])
    if wired_label != label_text:
        pytest.fail("build_canvas(theme_id='white') label = %r, expected unsplit %r" % (wired_label, label_text))
    if wired_tag != full_tag:
        pytest.fail("build_canvas(theme_id='white') tag = %r, expected the FULL unsplit tag %r" % (wired_tag, full_tag))


def test_default_theme_canvas_unchanged_by_band_port():
    """the default (white) theme's canvas is byte-identical to before this phase (getdata()/getcolors() computed fresh, and 'white' itself is confirmed not a band theme)"""
    if render.device_config.theme_is_band("white"):
        pytest.fail("'white' unexpectedly reports as a band theme - the default render path would be touched")
    default_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE)
    white_canvas = render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="white")
    default_data = list(default_canvas.getdata())
    white_data = list(white_canvas.getdata())
    if len(default_data) != len(white_data):
        pytest.fail("default/white canvas getdata() lengths differ: %d vs %d" % (len(default_data), len(white_data)))
    if default_data != white_data:
        pytest.fail("default/white canvas pixel data differs - the band port must not touch the default path")
    default_colors = {v for _n, v in default_canvas.getcolors()}
    white_colors = {v for _n, v in white_canvas.getcolors()}
    if default_colors != white_colors:
        pytest.fail("default/white canvas colour sets differ: %r vs %r" % (sorted(default_colors), sorted(white_colors)))


def test_non_band_text_blocks_unaffected_by_band_idx_kwarg():
    """every one of the 11 pre-band themes' full two-flight render is pixel-identical whether _build_active_canvas()'s band_idx=band_idx wiring runs (always None) or draw_main_text_block()/draw_previous_text_block() are called with no band_idx argument at all (PHASE9-4/PHASE9-6 regression guard)"""
    non_band_ids = [t for t in render.device_config.THEME_IDS if not render.device_config.theme_is_band(t)]
    if len(non_band_ids) != 11:
        pytest.fail("expected exactly 11 pre-band theme ids, found %d: %r" % (len(non_band_ids), non_band_ids))

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
            pytest.fail("theme %r: build_canvas() output differs when draw_main_text_block()/draw_previous_text_block() "
                "are called with no band_idx argument at all vs. _build_active_canvas()'s normal band_idx=band_idx "
                "wiring - the band_idx=None branch is not a byte-identical no-op wrapper" % (theme_id,))


def test_band_main_card_tier_split_reuses_real_content():
    """a band theme's main card draws the big-number line as route['callsign_iata'] verbatim and the tracked route line as _flight_line1_text()'s real remainder, upper-cased (tier 1); and draws only the promoted airline·type line, with no number/dash/tracked-route draw at all, for a tier-3 (airline-only) route (PHASE9-4)"""
    import server.plane.enrich as enrich

    theme_id = "band_blue"
    identifier = TEST_ROUTE["callsign_iata"]
    line1_full = render._flight_line1_text(TEST_FLIGHT, "departing", TEST_ROUTE)
    expected_tracked = line1_full[len(identifier) + 1:].upper()

    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id=theme_id)
    number_draws = [c for c in spy.calls if c[0] == identifier and c[2] == "ma"]
    if not number_draws:
        pytest.fail("band main card tier-1: no whole-string 'ma' draw of the identifier %r found" % (identifier,))
    tracked_glyphs = [c for c in spy.calls if len(c[0]) == 1 and c[1][1] != render.MARGIN]
    joined_tracked = "".join(t for t, _xy, _a in tracked_glyphs)
    if joined_tracked != expected_tracked:
        pytest.fail("band main card tier-1 tracked route line reconstructed as %r, expected %r"
            % (joined_tracked, expected_tracked))

    tier3_route = enrich.airline_only_route("Band Tier Three Airline")
    tier3_flight = {"hex": "abcdef", "callsign": "XYZ999", "aircraft_type": "A320"}
    line1_full_tier3 = render._flight_line1_text(tier3_flight, "departing", tier3_route)
    if line1_full_tier3 != "":
        pytest.fail("expected fixture to hit D-10 tier 3 (line 1 == ''), got %r" % (line1_full_tier3,))
    line2_full_tier3 = render._flight_line2_text(tier3_route, tier3_flight["aircraft_type"])
    with _TextSpy(render) as spy3:
        render.build_canvas(tier3_flight, "departing", route=tier3_route, theme_id=theme_id)
    tier3_tracked_glyphs = [c for c in spy3.calls if len(c[0]) == 1 and c[1][1] != render.MARGIN]
    if tier3_tracked_glyphs:
        pytest.fail("band main card tier-3 render unexpectedly drew tracked-route glyphs: %r" % (tier3_tracked_glyphs,))
    whole_strings_tier3 = [t for t, _xy, _a in spy3.calls if len(t) > 1]
    if line2_full_tier3 not in whole_strings_tier3:
        pytest.fail("band main card tier-3 render did not draw the promoted airline·type line %r as a whole string"
            % (line2_full_tier3,))


def test_band_center_x_computed_once_not_recomputed_per_line():
    """a band theme's main-card anchor='ma' draws (the number line and the airline·type line) all share exactly one x-coordinate - center_x is computed once per block, never recomputed per line (round-15 fix, PHASE9-4)"""
    with _TextSpy(render) as spy:
        render.build_canvas(TEST_FLIGHT, "departing", route=TEST_ROUTE, theme_id="band_blue")
    ma_draws = [c for c in spy.calls if c[2] == "ma" and c[1][1] != render.MARGIN]
    if len(ma_draws) < 2:
        pytest.fail("expected at least 2 anchor='ma' draws (number line + airline·type line), found %d" % (len(ma_draws),))
    xs = {xy[0] for _t, xy, _a in ma_draws}
    if len(xs) != 1:
        pytest.fail("band main card anchor='ma' draws used %d distinct x-coordinates %r, expected exactly 1 - "
            "center_x must be computed once and reused (round-15 fix, round-12 regression guard)"
            % (len(xs), sorted(xs)))


def test_band_black_main_card_ink_swaps_to_white():
    """every registered band theme's main card text samples as IDX_WHITE (never IDX_BLACK) inside its own drawn bboxes - the round-13 ink swap, widened on real glass to every band colour, is proven by actual pixel colour, not by absence of an exception (PHASE9-5)"""
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

    # Black text reads poorly against every band colour (Blue/Green/Red
    # too, not just Black), so every registered band theme's main card
    # draws in white ink, unconditionally. Proven by actual pixel colour
    # for the full registered set, not by absence of an exception.
    band_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
    if len(band_ids) != 7:
        pytest.fail("expected exactly 7 registered band theme ids, found %d: %r" % (len(band_ids), band_ids))
    for theme_id in band_ids:
        ink_values = _ink_pixels_drawn(theme_id)
        if IDX_WHITE not in ink_values:
            pytest.fail("%s main card: no newly-painted IDX_WHITE ink pixels found - ink swap missing" % theme_id)
        if IDX_BLACK in ink_values:
            pytest.fail("%s main card: newly-painted IDX_BLACK ink pixels found - ink swap incomplete" % theme_id)


def test_previous_card_never_collides_with_the_band():
    """the previous card's drawn text bboxes never overlap the diagonal band's own rightmost extent, at any registered band theme, in a full two-flight render"""
    band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
    if not band_theme_ids:
        pytest.fail("no band theme ids found in THEME_IDS")

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
            pytest.fail("theme %r: no previous-card (anchor='ra') text bbox found" % (theme_id,))
        for bbox in prev_bboxes:
            left, top = bbox[0], bbox[1]
            band_right_at_top = _band_right_edge_x(top, render.WIDTH)
            if left < band_right_at_top:
                pytest.fail("theme %r: previous-card text bbox %r's left edge (%r) sits inside the band's own "
                    "rightmost extent (%r) at that y" % (theme_id, bbox, left, band_right_at_top))


def test_band_themes_full_composition_stays_palette_legal():
    """every registered band theme's full two-flight composition (three-tier main + previous card text, plus the source-fault badge when present) stays _assert_legal_palette()-legal across both active states"""
    band_theme_ids = [t for t in render.device_config.THEME_IDS if render.device_config.theme_is_band(t)]
    if not band_theme_ids:
        pytest.fail("no band theme ids found in THEME_IDS")
    for theme_id in band_theme_ids:
        for state in ("departing", "arriving"):
            for source_fault in (False, True):
                render.build_canvas(
                    TEST_FLIGHT, state, route=TEST_ROUTE,
                    previous_flight=TEST_PREVIOUS_FLIGHT, previous_route=TEST_PREVIOUS_ROUTE,
                    previous_state="arriving" if state == "departing" else "departing",
                    theme_id=theme_id, source_fault=source_fault,
                )


# The main illustration's visible vertical centre must be a property of
# the layout, not of which airline is flying, so this asserts on the
# spread of that centre across every vendored illustration file - never
# on any single file's absolute position, which is a design constant
# defined elsewhere and would force this check into lockstep with it.
# main_w and the vertical anchor are derived from render.py's own
# constants/helpers, never hardcoded copies.
MAIN_VERTICAL_DRIFT_TOLERANCE_PX = 2

def test_main_illustration_vertical_centre_has_no_per_file_drift():
    """the main illustration's VISIBLE vertical centre sits on one fixed canvas line (within MAIN_VERTICAL_DRIFT_TOLERANCE_PX) across all vendored files, instead of drifting with each file's own transparent top padding (illustration-crop-text-margin's missed sixth anchor)"""
    illustrations_dir = os.path.join(REPO_ROOT, "server", "assets", "icons", "illustrations")
    filenames = sorted(f for f in os.listdir(illustrations_dir) if f.lower().endswith(".png"))
    if len(filenames) < 40:
        pytest.fail("found only %d vendored illustration files under %r - expected around 43; the fixture set may "
            "have moved" % (len(filenames), illustrations_dir))
    inner_width = panel_format.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
    main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
    center_y = panel_format.HEIGHT * render.MAIN_ILLUSTRATION_CENTER_Y_FRAC
    centres = {}
    for filename in filenames:
        path = os.path.join(illustrations_dir, filename)
        resized = render._resize_illustration(path, main_w)
        bbox = render._opaque_bbox(resized)
        if bbox is None:
            continue  # documented fallback case (nothing painted) - not a failure
        # main_top follows the painted content's centre
        # (`_top_for_centered_content()`, the same helper
        # `_build_active_canvas()` itself calls), not a fraction of the
        # source rectangle's top.
        main_top = render._top_for_centered_content(resized, center_y)
        centres[filename] = main_top + (bbox[1] + bbox[3]) / 2.0
    if len(centres) < 40:
        pytest.fail("only %d of %d vendored files produced an opaque bbox - too few to measure drift"
            % (len(centres), len(filenames)))
    spread = max(centres.values()) - min(centres.values())
    if spread > MAIN_VERTICAL_DRIFT_TOLERANCE_PX:
        worst_low = min(centres, key=centres.get)
        worst_high = max(centres, key=centres.get)
        pytest.fail("the main aircraft's visible vertical centre drifts %.1fpx across %d vendored files (%s=%.1f, "
            "%s=%.1f) - the main illustration's vertical position is anchored to its source rectangle's top, "
            "not its painted pixels"
            % (spread, len(centres), worst_low, centres[worst_low], worst_high, centres[worst_high]))


def test_quiet_hours_packs_white_dominant_with_black():
    """render_panel(None, 'quiet_hours', quiet_hours_until='07:00') packs to exactly 960000 bytes, dominated by the dimmed Black field, with at least one White nibble"""
    buf = render.render_panel(None, "quiet_hours", quiet_hours_until="07:00")
    if len(buf) != panel_format.IMAGE_BYTES:
        pytest.fail("quiet-hours render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES))
    counts = nibble_counts(buf)
    dom = max(counts, key=counts.get)
    if dom != NIBBLE_BLACK:
        pytest.fail("quiet-hours render's dominant nibble is 0x%x, expected 0x0 (Black, the dimmed field)" % dom)
    if NIBBLE_WHITE not in counts:
        pytest.fail("quiet-hours render contains no White (0x1) nibble - expected White ink")


def test_quiet_hours_only_legal_indices():
    """every pixel index in build_canvas(None, 'quiet_hours', quiet_hours_until='07:00') is one of the six legal palette indices"""
    canvas = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00")
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - LEGAL_IDX
    if bad:
        pytest.fail("quiet-hours canvas contains illegal palette index(es): %r" % (sorted(bad),))


def test_quiet_hours_ignores_theme_id():
    """build_canvas(None, 'quiet_hours', ...) is pixel-identical across different theme_id values (theme is ignored for this screen)"""
    a = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", theme_id="white")
    b = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", theme_id="blue")
    if a.tobytes() != b.tobytes():
        pytest.fail("quiet-hours canvas differs between theme_id='white' and theme_id='blue' - theme_id must be ignored")


def test_quiet_hours_missing_until_omits_body_without_raising():
    """build_canvas(None, 'quiet_hours', quiet_hours_until=None) and quiet_hours_until='' both render without raising and differ from quiet_hours_until='07:00' (heading-only degradation)"""
    with_time = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00").tobytes()
    for missing_value in (None, ""):
        canvas = render.build_canvas(None, "quiet_hours", quiet_hours_until=missing_value)
        if canvas.tobytes() == with_time:
            pytest.fail("quiet_hours_until=%r produced the same canvas as quiet_hours_until='07:00' - the body "
                "line was not actually omitted" % (missing_value,))


def test_quiet_hours_battery_low_changes_canvas():
    """battery_low=True changes the quiet-hours canvas relative to battery_low=False"""
    off = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", battery_low=False)
    on = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", battery_low=True)
    if off.tobytes() == on.tobytes():
        pytest.fail("battery_low=True produced no pixel difference on the quiet-hours canvas")


def test_quiet_hours_source_fault_changes_canvas():
    """source_fault=True changes the quiet-hours canvas relative to source_fault=False"""
    off = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", source_fault=False)
    on = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00", source_fault=True)
    if off.tobytes() == on.tobytes():
        pytest.fail("source_fault=True produced no pixel difference on the quiet-hours canvas")


def test_quiet_hours_state_wins_over_empty_when_flight_is_none():
    """build_canvas(None, 'quiet_hours') renders the quiet-hours canvas, not the empty canvas, even though flight is None for both states"""
    quiet_hours = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00").tobytes()
    empty = render.build_canvas(None, "empty").tobytes()
    if quiet_hours == empty:
        pytest.fail("build_canvas(None, 'quiet_hours') produced the same bytes as build_canvas(None, 'empty') - "
            "every quiet-hours call would silently render the empty state instead")





def test_cli_renders_quiet_hours_state(tmp_path):
    """render.main() via build_parser() with ['--state', 'quiet_hours', '--quiet-hours-until', '07:00', '--out', <path>] returns 0 and writes exactly IMAGE_BYTES bytes"""
    out_path = os.path.join(str(tmp_path), "quiet-hours-cli.bin")
    argv = ["--state", "quiet_hours", "--quiet-hours-until", "07:00", "--out", out_path]
    with contextlib.redirect_stdout(io.StringIO()):
        rc = render.main(argv)
    if rc != 0:
        pytest.fail("render.main(%r) returned %r, expected 0" % (argv, rc))
    if not os.path.isfile(out_path):
        pytest.fail("render.main(%r) did not write %r" % (argv, out_path))
    size = os.path.getsize(out_path)
    if size != panel_format.IMAGE_BYTES:
        pytest.fail("%r is %d bytes, expected %d" % (out_path, size, panel_format.IMAGE_BYTES))


def test_tinted_field_band_themes_prove_dominance_explicitly():
    """band_blue_field/band_red_field each render via build_canvas() in both active states with the state's own background index (never White) provably the single most common index on the panel, stated explicitly rather than merely implied by the absence of an exception"""
    field_theme_ids = ("band_blue_field", "band_red_field")
    missing = [t for t in field_theme_ids if t not in render.device_config.THEME_IDS]
    if missing:
        pytest.fail("expected THEME_IDS to contain %r, missing %r" % (field_theme_ids, missing))
    for theme_id in field_theme_ids:
        for state in ("departing", "arriving"):
            canvas = render.build_canvas(TEST_FLIGHT, state, route=TEST_ROUTE, theme_id=theme_id)
            expected_bg_idx = render.device_config.theme_background_index(state, theme_id)
            counts = canvas.getcolors()
            if counts is None:
                pytest.fail("theme %r state %r: canvas.getcolors() returned None (>256 colours?)" % (theme_id, state))
            counts_sorted = sorted(counts, key=lambda pair: pair[0], reverse=True)
            most_common_count, most_common_idx = counts_sorted[0]
            if most_common_idx != expected_bg_idx:
                pytest.fail("theme %r state %r: most common index is %r (count %r), expected the theme's own "
                    "background index %r to dominate" % (theme_id, state, most_common_idx, most_common_count, expected_bg_idx))
            if expected_bg_idx == panel_format.IDX_WHITE:
                pytest.fail("theme %r state %r: background index resolved to White, expected the theme's own "
                    "tinted hue (this is what distinguishes tone-on-tone field themes from every "
                    "pre-existing White-field band theme)" % (theme_id, state))


def test_display_off_flat_white_black_across_all_themes():
    """build_canvas(None, 'display_off', theme_id=...) renders the dimmed Black/White field (DIMMED_FIELD_IDX dominant, no third index), carrying the heading and body, byte-identical across the full THEME_IDS registry"""
    theme_ids = list(render.device_config.THEME_IDS)
    if not theme_ids:
        pytest.fail("device_config.THEME_IDS is empty - nothing to iterate")
    reference = None
    for theme_id in theme_ids:
        canvas = render.build_canvas(None, "display_off", theme_id=theme_id)
        colors = canvas.getcolors()
        idx_set = {value for _count, value in colors} if colors else set()
        bad = idx_set - {IDX_WHITE, IDX_BLACK}
        if bad:
            pytest.fail("display-off canvas (theme_id=%r) contains index(es) other than White/Black: %r"
                % (theme_id, sorted(bad)))
        if IDX_WHITE not in idx_set:
            pytest.fail("display-off canvas (theme_id=%r) has no White pixels" % (theme_id,))
        if IDX_BLACK not in idx_set:
            pytest.fail("display-off canvas (theme_id=%r) has no Black pixels" % (theme_id,))
        counts = {value: count for count, value in colors}
        if max(counts, key=counts.get) != render.DIMMED_FIELD_IDX:
            pytest.fail("display-off canvas (theme_id=%r) is not dominated by its own field index %r"
                % (theme_id, render.DIMMED_FIELD_IDX))
        data = canvas.tobytes()
        if reference is None:
            reference = data
        elif data != reference:
            pytest.fail("display-off canvas differs for theme_id=%r versus the first theme in THEME_IDS - "
                "theme_id must be ignored entirely" % (theme_id,))


def test_display_off_provably_distinct_from_empty_and_quiet_hours():
    """build_canvas(None, 'display_off') is provably distinct from build_canvas(None, 'empty') and build_canvas(None, 'quiet_hours', ...) - all three pass flight=None, so a reordered dispatch branch is otherwise silent"""
    off = render.build_canvas(None, "display_off").tobytes()
    empty = render.build_canvas(None, "empty").tobytes()
    quiet = render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00").tobytes()
    if off == empty:
        pytest.fail("build_canvas(None, 'display_off') is byte-identical to build_canvas(None, 'empty') - "
            "both pass flight=None, so a reordered dispatch branch would silently render the empty "
            "screen for every off-state call with no error anywhere")
    if off == quiet:
        pytest.fail("build_canvas(None, 'display_off') is byte-identical to build_canvas(None, 'quiet_hours', "
            "quiet_hours_until='07:00') - both pass flight=None and share the same White/Black "
            "structure, so a dispatch mix-up here would be silent too")


def test_display_off_ignores_quiet_hours_until():
    """build_canvas(None, 'display_off', quiet_hours_until='07:00') is byte-identical to the call without it - no return-time value can reach this screen"""
    without = render.build_canvas(None, "display_off").tobytes()
    with_time = render.build_canvas(None, "display_off", quiet_hours_until="07:00").tobytes()
    if without != with_time:
        pytest.fail("build_canvas(None, 'display_off', quiet_hours_until='07:00') differs from the call "
            "without quiet_hours_until - a return-time value leaked into the off screen (D-04)")


def test_display_off_copy_constants_match_locked_strings():
    """DISPLAY_OFF_HEADING_TEXT == 'DISPLAY OFF' and DISPLAY_OFF_BODY_TEXT == the locked body string, asserted by exact equality"""
    if render.DISPLAY_OFF_HEADING_TEXT != "DISPLAY OFF":
        pytest.fail("DISPLAY_OFF_HEADING_TEXT is %r, expected 'DISPLAY OFF'" % (render.DISPLAY_OFF_HEADING_TEXT,))
    expected_body = "Switched off from the companion page. Turn it back on there anytime."
    if render.DISPLAY_OFF_BODY_TEXT != expected_body:
        pytest.fail("DISPLAY_OFF_BODY_TEXT is %r, expected %r" % (render.DISPLAY_OFF_BODY_TEXT, expected_body))


def test_display_off_battery_and_fault_indicators_are_independent():
    """battery_low=True and source_fault=True each change the display-off canvas independently, and both may be set at once, mirroring the equivalent quiet-hours checks"""
    neither = render.build_canvas(None, "display_off", battery_low=False, source_fault=False).tobytes()
    battery_only = render.build_canvas(None, "display_off", battery_low=True, source_fault=False).tobytes()
    fault_only = render.build_canvas(None, "display_off", battery_low=False, source_fault=True).tobytes()
    both = render.build_canvas(None, "display_off", battery_low=True, source_fault=True).tobytes()
    if battery_only == neither:
        pytest.fail("battery_low=True produced no pixel difference on the display-off canvas")
    if fault_only == neither:
        pytest.fail("source_fault=True produced no pixel difference on the display-off canvas")
    if both == neither or both == battery_only or both == fault_only:
        pytest.fail("battery_low=True, source_fault=True together did not produce a distinct canvas from each alone/neither")


def test_display_off_legal_palette_and_safe_box_across_indicator_combos():
    """build_canvas(None, 'display_off', ...) uses only legal palette indices and passes every internal _assert_in_safe_box() check across all four battery_low/source_fault combinations (neither / battery only / fault only / both)"""
    for battery_low in (False, True):
        for source_fault in (False, True):
            canvas = render.build_canvas(
                None, "display_off", battery_low=battery_low, source_fault=source_fault
            )
            colors = canvas.getcolors()
            idx_set = {value for _count, value in colors} if colors else set()
            bad = idx_set - LEGAL_IDX
            if bad:
                pytest.fail("display-off canvas (battery_low=%r, source_fault=%r) contains illegal palette "
                    "index(es): %r" % (battery_low, source_fault, sorted(bad)))


def test_battery_empty_copy_constants_match_locked_strings():
    """BATTERY_EMPTY_HEADING_TEXT == 'BATTERY EMPTY' and BATTERY_EMPTY_BODY_LINES == the two locked authored sentences, asserted by exact equality"""
    if render.BATTERY_EMPTY_HEADING_TEXT != "BATTERY EMPTY":
        pytest.fail("BATTERY_EMPTY_HEADING_TEXT is %r, expected 'BATTERY EMPTY'" % (render.BATTERY_EMPTY_HEADING_TEXT,))
    expected_lines = ("Charge the frame over USB-C.", "It will pick up where it left off.")
    if render.BATTERY_EMPTY_BODY_LINES != expected_lines:
        pytest.fail("BATTERY_EMPTY_BODY_LINES is %r, expected %r" % (render.BATTERY_EMPTY_BODY_LINES, expected_lines))


def test_battery_empty_dispatches_through_shared_dimmed_composition():
    """build_canvas(None, 'battery_empty') calls render._build_dimmed_hold_canvas exactly once, with draw_empty_battery_icon, EMPTY_BATTERY_ICON_HEIGHT_PX, BATTERY_EMPTY_HEADING_TEXT, BATTERY_EMPTY_BODY_LINES, source_fault=False and battery_low=False"""
    orig = render._build_dimmed_hold_canvas
    calls = []

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return orig(*args, **kwargs)

    render._build_dimmed_hold_canvas = _spy
    try:
        render.build_canvas(None, "battery_empty")
    finally:
        render._build_dimmed_hold_canvas = orig
    if len(calls) != 1:
        pytest.fail("_build_dimmed_hold_canvas was called %d time(s), expected exactly 1" % (len(calls),))
    args, kwargs = calls[0]
    if len(args) < 4:
        pytest.fail("_build_dimmed_hold_canvas call had %d positional args, expected at least 4 "
            "(glyph_draw, glyph_height, label_text, sentences)" % (len(args),))
    glyph_draw, glyph_height, label_text, sentences = args[0], args[1], args[2], args[3]
    if glyph_draw is not render.draw_empty_battery_icon:
        pytest.fail("glyph_draw was %r, expected render.draw_empty_battery_icon" % (glyph_draw,))
    if glyph_height != render.EMPTY_BATTERY_ICON_HEIGHT_PX:
        pytest.fail("glyph_height was %r, expected EMPTY_BATTERY_ICON_HEIGHT_PX (%r)"
            % (glyph_height, render.EMPTY_BATTERY_ICON_HEIGHT_PX))
    if label_text != render.BATTERY_EMPTY_HEADING_TEXT:
        pytest.fail("label_text was %r, expected BATTERY_EMPTY_HEADING_TEXT" % (label_text,))
    if tuple(sentences) != render.BATTERY_EMPTY_BODY_LINES:
        pytest.fail("sentences was %r, expected BATTERY_EMPTY_BODY_LINES" % (sentences,))
    if kwargs.get("source_fault", False) is not False:
        pytest.fail("source_fault was %r, expected False" % (kwargs.get("source_fault"),))
    if kwargs.get("battery_low", False) is not False:
        pytest.fail("battery_low was %r, expected False" % (kwargs.get("battery_low"),))


def test_battery_empty_shares_dimmed_field_with_display_off():
    """build_canvas(None, 'battery_empty') and build_canvas(None, 'display_off') are byte-identical in the top and bottom 400 rows (the same dithered field) and provably distinct overall (the centred glyph/label/body differs)"""
    battery_bytes = render.build_canvas(None, "battery_empty").tobytes()
    off_bytes = render.build_canvas(None, "display_off").tobytes()
    row_bytes = panel_format.WIDTH  # 'P' mode: one byte per pixel
    band = 400 * row_bytes
    if battery_bytes[:band] != off_bytes[:band]:
        pytest.fail("battery_empty and display_off differ within the top 400 rows of the shared dithered field")
    if battery_bytes[-band:] != off_bytes[-band:]:
        pytest.fail("battery_empty and display_off differ within the bottom 400 rows of the shared dithered field")
    if battery_bytes == off_bytes:
        pytest.fail("battery_empty is byte-identical to display_off overall - the centred block must differ")


def test_draw_empty_battery_icon_geometry():
    """draw_empty_battery_icon() returns EMPTY_BATTERY_ICON_HEIGHT_PX (== MOON_ICON_DIAMETER_PX), draws an ink bounding box exactly EMPTY_BATTERY_ICON_HEIGHT_PX tall and EMPTY_BATTERY_ICON_WIDTH_PX wide, a POWER_ICON_STROKE_PX-long ink run at body mid-height from the left edge, a hollow body centre, and only the field/ink indices anywhere on the canvas"""
    center_x, top_y = 200, 300
    canvas = panel_format.new_canvas(IDX_BLACK)
    draw = render.ImageDraw.Draw(canvas)
    returned_height = render.draw_empty_battery_icon(draw, center_x, top_y, IDX_WHITE)
    if returned_height != render.EMPTY_BATTERY_ICON_HEIGHT_PX:
        pytest.fail("draw_empty_battery_icon returned %r, expected EMPTY_BATTERY_ICON_HEIGHT_PX (%r)"
            % (returned_height, render.EMPTY_BATTERY_ICON_HEIGHT_PX))
    if render.EMPTY_BATTERY_ICON_HEIGHT_PX != render.MOON_ICON_DIAMETER_PX:
        pytest.fail("EMPTY_BATTERY_ICON_HEIGHT_PX (%r) != MOON_ICON_DIAMETER_PX (%r)"
            % (render.EMPTY_BATTERY_ICON_HEIGHT_PX, render.MOON_ICON_DIAMETER_PX))

    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    stray = idx_set - {IDX_BLACK, IDX_WHITE}
    if stray:
        pytest.fail("canvas contains index(es) other than the field/ink pair: %r" % (sorted(stray),))

    bbox = canvas.getbbox()
    if bbox is None:
        pytest.fail("draw_empty_battery_icon drew nothing (getbbox() is None)")
    left, top, right, bottom = bbox
    if (bottom - top) != render.EMPTY_BATTERY_ICON_HEIGHT_PX:
        pytest.fail("ink bounding box is %dpx tall, expected EMPTY_BATTERY_ICON_HEIGHT_PX (%r)"
            % (bottom - top, render.EMPTY_BATTERY_ICON_HEIGHT_PX))
    if (right - left) != render.EMPTY_BATTERY_ICON_WIDTH_PX:
        pytest.fail("ink bounding box is %dpx wide, expected EMPTY_BATTERY_ICON_WIDTH_PX (%r)"
            % (right - left, render.EMPTY_BATTERY_ICON_WIDTH_PX))

    pixels = canvas.load()
    body_mid_y = (
        top_y + render.EMPTY_BATTERY_NUB_H_PX
        + (render.EMPTY_BATTERY_ICON_HEIGHT_PX - render.EMPTY_BATTERY_NUB_H_PX) // 2
    )
    run = 0
    x = left
    while x < right and pixels[x, body_mid_y] == IDX_WHITE:
        run += 1
        x += 1
    if run != render.EMPTY_BATTERY_ICON_STROKE_PX:
        pytest.fail("horizontal ink run at body mid-height from the left edge is %dpx, expected "
            "EMPTY_BATTERY_ICON_STROKE_PX (%r)" % (run, render.EMPTY_BATTERY_ICON_STROKE_PX))

    body_center_x = (left + right) // 2
    center_value = pixels[body_center_x, body_mid_y]
    if center_value != IDX_BLACK:
        pytest.fail("the body's centre pixel is index %r, expected the field index %r - the interior must "
            "stay hollow so the dithered field shows through" % (center_value, IDX_BLACK))


def test_battery_empty_byte_stable_across_indicators_and_themes():
    """build_canvas(None, 'battery_empty', ...) bytes are byte-stable regardless of source_fault, battery_low or theme_id - the hash the whole parked episode relies on staying constant"""
    default = render.build_canvas(None, "battery_empty").tobytes()
    with_fault = render.build_canvas(None, "battery_empty", source_fault=True).tobytes()
    if with_fault != default:
        pytest.fail("build_canvas(None, 'battery_empty', source_fault=True) differs from the default call")
    with_low = render.build_canvas(None, "battery_empty", battery_low=True).tobytes()
    if with_low != default:
        pytest.fail("build_canvas(None, 'battery_empty', battery_low=True) differs from the default call")
    both = render.build_canvas(None, "battery_empty", source_fault=True, battery_low=True).tobytes()
    if both != default:
        pytest.fail("build_canvas(None, 'battery_empty', source_fault=True, battery_low=True) differs from the default call")
    theme_ids = list(render.device_config.THEME_IDS)
    if not theme_ids:
        pytest.fail("device_config.THEME_IDS is empty - nothing to iterate")
    for theme_id in theme_ids:
        themed = render.build_canvas(None, "battery_empty", theme_id=theme_id).tobytes()
        if themed != default:
            pytest.fail("build_canvas(None, 'battery_empty', theme_id=%r) differs from the default call" % (theme_id,))


def test_battery_empty_black_white_black_dominant():
    """build_canvas(None, 'battery_empty') uses only IDX_BLACK/IDX_WHITE, dominated by DIMMED_FIELD_IDX (Black) - the same dimmed-field family rule as DISPLAY OFF and QUIET HOURS"""
    canvas = render.build_canvas(None, "battery_empty")
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - {IDX_WHITE, IDX_BLACK}
    if bad:
        pytest.fail("battery_empty canvas contains index(es) other than White/Black: %r" % (sorted(bad),))
    if IDX_WHITE not in idx_set:
        pytest.fail("battery_empty canvas has no White pixels")
    if IDX_BLACK not in idx_set:
        pytest.fail("battery_empty canvas has no Black pixels")
    counts = {value: count for count, value in colors}
    if max(counts, key=counts.get) != render.DIMMED_FIELD_IDX:
        pytest.fail("battery_empty canvas is not dominated by its own field index %r" % (render.DIMMED_FIELD_IDX,))



def test_no_connection_copy_constants_match_locked_strings():
    """NO_CONNECTION_HEADING_TEXT == 'NO CONNECTION' and NO_CONNECTION_BODY_LINES == the two locked authored sentences, asserted by exact equality"""
    if render.NO_CONNECTION_HEADING_TEXT != "NO CONNECTION":
        pytest.fail("NO_CONNECTION_HEADING_TEXT is %r, expected 'NO CONNECTION'" % (render.NO_CONNECTION_HEADING_TEXT,))
    expected_lines = ("The frame can't reach its server.", "It will try again on its own.")
    if render.NO_CONNECTION_BODY_LINES != expected_lines:
        pytest.fail("NO_CONNECTION_BODY_LINES is %r, expected %r" % (render.NO_CONNECTION_BODY_LINES, expected_lines))


def test_no_connection_dispatches_through_shared_hold_composition():
    """render._build_no_connection_canvas() calls render._build_hold_canvas exactly once, with draw_alert_icon, ALERT_ICON_HEIGHT_PX, NO_CONNECTION_HEADING_TEXT, NO_CONNECTION_BODY_LINES, DIMMED_FIELD_IDX, DIMMED_INK and dithered=True by default"""
    orig = render._build_hold_canvas
    calls = []

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return orig(*args, **kwargs)

    render._build_hold_canvas = _spy
    try:
        render._build_no_connection_canvas()
    finally:
        render._build_hold_canvas = orig
    if len(calls) != 1:
        pytest.fail("_build_hold_canvas was called %d time(s), expected exactly 1" % (len(calls),))
    args, kwargs = calls[0]
    if len(args) < 7:
        pytest.fail("_build_hold_canvas call had %d positional args, expected at least 7 "
            "(glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered)" % (len(args),))
    glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered = args[0:7]
    if glyph_draw is not render.draw_alert_icon:
        pytest.fail("glyph_draw was %r, expected render.draw_alert_icon" % (glyph_draw,))
    if glyph_height != render.ALERT_ICON_HEIGHT_PX:
        pytest.fail("glyph_height was %r, expected ALERT_ICON_HEIGHT_PX (%r)"
            % (glyph_height, render.ALERT_ICON_HEIGHT_PX))
    if label_text != render.NO_CONNECTION_HEADING_TEXT:
        pytest.fail("label_text was %r, expected NO_CONNECTION_HEADING_TEXT" % (label_text,))
    if sentences != render.NO_CONNECTION_BODY_LINES:
        pytest.fail("sentences was %r, expected NO_CONNECTION_BODY_LINES" % (sentences,))
    if field_idx != render.DIMMED_FIELD_IDX:
        pytest.fail("field_idx was %r, expected DIMMED_FIELD_IDX" % (field_idx,))
    if ink != render.DIMMED_INK:
        pytest.fail("ink was %r, expected DIMMED_INK" % (ink,))
    if dithered is not True:
        pytest.fail("dithered was %r, expected True for the default (flat=False) call" % (dithered,))


def test_no_connection_dithered_legal_palette_and_black_dominant():
    """_build_no_connection_canvas() (dithered) uses only IDX_BLACK/IDX_WHITE, dominated by DIMMED_FIELD_IDX (Black)"""
    canvas = render._build_no_connection_canvas()
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - {IDX_WHITE, IDX_BLACK}
    if bad:
        pytest.fail("no-connection canvas contains index(es) other than White/Black: %r" % (sorted(bad),))
    if IDX_WHITE not in idx_set:
        pytest.fail("no-connection canvas has no White pixels")
    if IDX_BLACK not in idx_set:
        pytest.fail("no-connection canvas has no Black pixels")
    counts = {value: count for count, value in colors}
    if max(counts, key=counts.get) != render.DIMMED_FIELD_IDX:
        pytest.fail("no-connection canvas is not dominated by its own field index %r" % (render.DIMMED_FIELD_IDX,))


def test_no_connection_flat_canvas_contains_only_black_and_white():
    """_build_no_connection_canvas(flat=True) contains only {IDX_BLACK, IDX_WHITE} - no dither noise, since it exists purely for gen_fault_screen.py's ink-mask extraction"""
    canvas = render._build_no_connection_canvas(flat=True)
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - {IDX_WHITE, IDX_BLACK}
    if bad:
        pytest.fail("flat no-connection canvas contains index(es) other than White/Black: %r" % (sorted(bad),))


def test_build_canvas_never_produces_the_no_connection_canvas():
    """build_canvas() never returns the same bytes as _build_no_connection_canvas() for any state it accepts - that screen is drawn only by the firmware, never dispatched by the server"""
    no_connection_bytes = render._build_no_connection_canvas().tobytes()
    cases = [
        (None, "battery_empty", {}),
        (None, "display_off", {}),
        (None, "quiet_hours", {"quiet_hours_until": "07:00"}),
        (None, "empty", {}),
        (TEST_FLIGHT, "departing", {"route": TEST_ROUTE}),
        (TEST_FLIGHT, "arriving", {"route": TEST_ROUTE}),
    ]
    for flight, state, kwargs in cases:
        canvas = render.build_canvas(flight, state, **kwargs)
        if canvas.tobytes() == no_connection_bytes:
            pytest.fail("build_canvas(%r, %r) matched the no-connection canvas - this screen must never be "
                "server-dispatched" % (flight, state))


def test_draw_alert_icon_returns_height_and_uses_only_given_ink():
    """draw_alert_icon() returns ALERT_ICON_HEIGHT_PX, draws only ink_idx, and has inked pixels both above and below the exclamation gap (the dot is present, not a degenerate zero-length line)"""
    canvas = panel_format.new_canvas(IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    top_y = 200
    center_x = 600
    returned = render.draw_alert_icon(draw, center_x, top_y, IDX_BLACK)
    if returned != render.ALERT_ICON_HEIGHT_PX:
        pytest.fail("draw_alert_icon returned %r, expected ALERT_ICON_HEIGHT_PX (%r)"
            % (returned, render.ALERT_ICON_HEIGHT_PX))

    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    stray = idx_set - {IDX_BLACK, IDX_WHITE}
    if stray:
        pytest.fail("canvas contains index(es) other than the field/ink pair: %r" % (sorted(stray),))

    pixels = canvas.load()
    gap_top = int(top_y + render.ALERT_ICON_HEIGHT_PX * 0.65) + 2
    gap_bottom = int(top_y + render.ALERT_ICON_HEIGHT_PX * 0.8) - 8
    above_stroke_y = int(top_y + render.ALERT_ICON_HEIGHT_PX * 0.5)
    dot_y = int(top_y + render.ALERT_ICON_HEIGHT_PX * 0.8)

    def _row_has_ink(y):
        return any(pixels[x, y] == IDX_BLACK for x in range(center_x - 10, center_x + 10))

    if not _row_has_ink(above_stroke_y):
        pytest.fail("no ink found in the exclamation stroke region (above the gap)")
    if not _row_has_ink(dot_y):
        pytest.fail("no ink found at the dot's row - the dot must be a real filled ellipse, not a degenerate zero-length line")
    if gap_top < gap_bottom and _row_has_ink((gap_top + gap_bottom) // 2):
        pytest.fail("ink found inside the stroke/dot gap - stroke and dot should be visually separated")
