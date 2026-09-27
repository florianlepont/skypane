"""Band, frame, top labels, illustration load/resize/cache/placement, and
the two canvas builders (`build_canvas`/`render_panel`) that assemble a
whole panel: the diagonal band and top-row labels, then the main/previous
aircraft illustrations and their text blocks, dispatching to
`hold_screens.py` for every non-active-flight state.

Imports `hold_screens` (for the dispatch inside `build_canvas`) and
`glyphs` (for the two small overlay indicators); neither of those two
modules imports this one back.
"""
import os
import sys

from PIL import Image, ImageDraw

from server import device_config
from server import panel_format as pf
from server.panel_format import HEIGHT, IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW, WIDTH
from server.plane import dither, illustrations
from server.plane.render import glyphs, hold_screens, style, text


def draw_diagonal_band(canvas, band_idx, dithered=False):
    """Paint the diagonal trapezoid band onto `canvas` in `band_idx`'s
    colour (flat or dithered toward White). Must be called before any
    text/illustration drawing so the band sits behind them. Geometry: see
    the `style.BAND_*_FRAC` constants.
    """
    w, h = canvas.size
    poly = [
        (style.BAND_TOP_LEFT_FRAC * w, 0), (style.BAND_TOP_RIGHT_FRAC * w, 0),
        (style.BAND_BOT_RIGHT_FRAC * w, h), (style.BAND_BOT_LEFT_FRAC * w, h),
    ]
    if dithered:
        band_fill = dither.dithered_state_background(band_idx)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        canvas.paste(band_fill, (0, 0), mask)
    else:
        ImageDraw.Draw(canvas).polygon(poly, fill=band_idx)


def draw_frame(canvas, ink_idx):
    """A thin `ink_idx`-coloured rectangle outline, `style.FRAME_STROKE_PX`
    wide, inset `style.FRAME_INSET_FRAC` of the canvas width from every
    edge. Returns the frame's own bounding box.
    """
    inset = round(WIDTH * style.FRAME_INSET_FRAC)
    box = (inset, inset, WIDTH - inset, HEIGHT - inset)
    ImageDraw.Draw(canvas).rectangle(box, outline=ink_idx, width=style.FRAME_STROKE_PX)
    return box


def draw_top_labels(
    canvas, state, ink_idx, bg_idx, weight, runway_id=device_config.DEFAULT_RUNWAY_ID, band_theme=False
):
    """Top row: state label (top-left) and runway tag (top-right), at
    `style.MARGIN` inset, tracked with `style.LABEL_TRACKING_PX`. Screen-
    preview-validated only, never checked against real Spectra 6 ink.
    Tag's start x is pre-computed from `text._tracked_text_width()` (no
    Pillow `anchor="ra"` for tracked text) to end flush at
    `WIDTH - style.MARGIN`.

    `band_theme`: state label absorbs a direction word plus the tag's
    airport-code half; the tag shrinks to the runway-part half to clear
    the diagonal band. Both halves come from
    `style.runway_tag_text(runway_id)`'s `.partition(" · ")`.
    """
    draw = ImageDraw.Draw(canvas)
    label_font = text._role_font(style.STATE_LABEL_FONT, weight)
    tag_font = text._role_font(style.TOP_TAG_FONT, weight)
    full_tag = style.runway_tag_text(runway_id)

    if band_theme:
        airport_code, _sep, runway_part = full_tag.partition(" · ")
        label_text = "%s %s %s" % (style.STATE_LABEL_TEXT[state], style._BAND_TOP_LABEL_DIRECTION[state], airport_code)
        tag_text = runway_part
    else:
        label_text = style.STATE_LABEL_TEXT[state]
        tag_text = full_tag

    # Looser guard, not the strict safe-box: glyph metrics can carry a
    # 1-2px negative bearing at these small sizes. Uses
    # text._tracked_text_bbox(), not draw.textbbox(), which would
    # under-report a tracked run's width.
    label_bbox = text._tracked_text_bbox(label_font, (style.MARGIN, style.MARGIN), label_text, style.LABEL_TRACKING_PX)
    style._assert_within_canvas(label_bbox, "state label")
    text.draw_tracked_text(draw, (style.MARGIN, style.MARGIN), label_text, label_font, ink_idx, tracking=style.LABEL_TRACKING_PX)

    tag_width = text._tracked_text_width(tag_font, tag_text, style.LABEL_TRACKING_PX)
    tag_x = WIDTH - style.MARGIN - tag_width
    tag_bbox = text._tracked_text_bbox(tag_font, (tag_x, style.MARGIN), tag_text, style.LABEL_TRACKING_PX)
    style._assert_within_canvas(tag_bbox, "top-right tag")
    text.draw_tracked_text(draw, (tag_x, style.MARGIN), tag_text, tag_font, ink_idx, tracking=style.LABEL_TRACKING_PX)


def _illustration_over_pixel_cap(path):
    """`True` when `path`'s PNG header declares more than
    `illustrations.ILLUSTRATION_MAX_PIXELS` pixels, or is unreadable.
    Checks only the header (`Image.open()` is lazy), never triggering a
    full decode; checks only pixel count, not the other vendor-time
    quality rules, so a live poll cycle never drops legitimate art. Never
    raises.
    """
    try:
        with Image.open(path) as img:
            width, height = img.size
            return (width * height) > illustrations.ILLUSTRATION_MAX_PIXELS
    except Exception:
        return True


def _load_illustration_safely(path, target_w):
    """Resized RGBA image loaded from `path`, degrading through `path`
    then `illustrations.generic_fallback_path()`, then `None`. Never
    raises, for any input including `None`.
    """
    candidates = []
    for candidate in (path, illustrations.generic_fallback_path()):
        if not candidate or not os.path.isfile(candidate) or candidate in candidates:
            continue
        candidates.append(candidate)

    for candidate in candidates:
        if _illustration_over_pixel_cap(candidate):
            try:
                with Image.open(candidate) as img:
                    pixel_count = img.size[0] * img.size[1]
            except Exception as exc:
                print(
                    "render: skipping illustration %s - header unreadable (%s)"
                    % (candidate, type(exc).__name__),
                    file=sys.stderr,
                )
            else:
                print(
                    "render: skipping illustration %s - %d pixels exceeds the %d-pixel cap"
                    % (candidate, pixel_count, illustrations.ILLUSTRATION_MAX_PIXELS),
                    file=sys.stderr,
                )
            continue
        try:
            return _resize_illustration(candidate, target_w)
        except Exception as exc:
            print(
                "render: skipping illustration %s - %s" % (candidate, type(exc).__name__),
                file=sys.stderr,
            )
            continue
    return None


_illustration_cache = {}
# Bounded so the long-lived companion process cannot grow it without
# limit; past the cap it is flushed and refilled.
_ILLUSTRATION_CACHE_MAX_ENTRIES = 128


def _resize_illustration(path, target_w):
    """Load a vendored per-airline illustration PNG and resize it to
    `target_w` px wide, preserving aspect ratio. Returns a fresh "RGBA"
    image, memoized on (path, mtime_ns, size, target_w).
    """
    try:
        st = os.stat(path)
        cache_key = (path, st.st_mtime_ns, st.st_size, target_w)
    except OSError:
        cache_key = None

    if cache_key is not None:
        cached = _illustration_cache.get(cache_key)
        if cached is not None:
            return cached.copy()

    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        src_w, src_h = rgba.size
        target_h = max(1, round(target_w * src_h / src_w))
        resized = rgba.resize((target_w, target_h), Image.LANCZOS)

    if cache_key is not None:
        if len(_illustration_cache) >= _ILLUSTRATION_CACHE_MAX_ENTRIES:
            _illustration_cache.clear()
        _illustration_cache[cache_key] = resized
    return resized.copy()


ILLUSTRATION_ALPHA_THRESHOLD = 127
"""Alpha strictly greater than this is painted; named so
`_threshold_alpha()` and every opaque-bbox measurement use one number."""


def _threshold_alpha(resized_rgba):
    """`resized_rgba`'s alpha channel hard-thresholded to strictly binary
    (0 or 255) at `ILLUSTRATION_ALPHA_THRESHOLD`. A soft/gradient mask
    would blend palette INDEX INTEGERS during paste(), producing illegal
    in-between indices.
    """
    return resized_rgba.getchannel("A").point(
        lambda p: 255 if p > ILLUSTRATION_ALPHA_THRESHOLD else 0
    )


def _opaque_bbox(resized_rgba):
    """Tight bounding box of the pixels `draw_illustration()` will
    actually paint, in image-local coordinates. Not `Image.getbbox()` on
    the raw alpha channel: that counts the soft drop-shadow band
    (alpha 1..127) the paste threshold erases. Returns `None` when
    nothing would be painted.
    """
    return _threshold_alpha(resized_rgba).getbbox()


class IllustrationPlacement(tuple):
    """`draw_illustration()`'s return value: two absolute canvas bounding
    boxes, deliberately not the same box.

    - `rect`: the full placement rectangle of the resized source PNG,
      including transparent padding. Use for canvas-containment guards.
    - `content`: the tight bbox of pixels actually painted (see
      `_opaque_bbox()`). Use for anything that must line up with the
      aircraft as seen, above all flight-text vertical anchors. Falls
      back to `rect` when nothing is painted.

    Subclasses `tuple` as `(rect, content)` so it unpacks naturally.
    """

    __slots__ = ()

    def __new__(cls, rect, content):
        return super().__new__(cls, (rect, content))

    @property
    def rect(self):
        return self[0]

    @property
    def content(self):
        return self[1]

    def __repr__(self):
        return "IllustrationPlacement(rect=%r, content=%r)" % (self.rect, self.content)


def _left_for_centered_content(resized_rgba, center_x):
    """Paste `left` that puts the illustration's PAINTED horizontal
    midpoint on `center_x`. Not `(WIDTH - w) // 2`: horizontal transparent
    padding is asymmetric per file, which would displace the visible
    aircraft from centre. Falls back to the full rectangle when nothing
    would be painted.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_x - resized_rgba.size[0] / 2)
    return round(center_x - (local[0] + local[2]) / 2)


def _left_for_right_aligned_content(resized_rgba, right_x):
    """Paste `left` that puts the illustration's PAINTED right edge on
    `right_x`, so two illustrations share one visible edge regardless of
    differing right padding. Falls back to the full rectangle.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(right_x - resized_rgba.size[0])
    return round(right_x - local[2])


def _top_for_centered_content(resized_rgba, center_y):
    """Paste `top` that puts the illustration's PAINTED vertical midpoint
    on `center_y`. Vertical padding is asymmetric (drop-shadow band makes
    bottom exceed top), so centring the source rectangle would push the
    aircraft high. Falls back to the full rectangle.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_y - resized_rgba.size[1] / 2)
    return round(center_y - (local[1] + local[3]) / 2)


def draw_illustration(canvas, resized_rgba, left, top):
    """Composite a resized illustration onto `canvas` at (`left`, `top`),
    dithered to the panel's 6-color palette. Alpha is hard-thresholded to
    strictly binary before paste() (`_threshold_alpha()`). Returns an
    `IllustrationPlacement` (see that class's docstring).
    """
    w, h = resized_rgba.size
    rgb = resized_rgba.convert("RGB")
    quantized = dither.dither_to_full_panel_palette(rgb)
    alpha = _threshold_alpha(resized_rgba)
    canvas.paste(quantized, (int(left), int(top)), mask=alpha)

    rect = (left, top, left + w, top + h)
    local = _opaque_bbox(resized_rgba)
    if local is None:
        # Nothing was painted - there is no visual content to anchor to, so
        # the full rectangle is the only meaningful answer. Never raises.
        content = rect
    else:
        content = (left + local[0], top + local[1], left + local[2], top + local[3])
    return IllustrationPlacement(rect, content)


_LEGAL_PANEL_INDICES = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}


def _assert_legal_palette(canvas, bg_idx):
    """Guard rail: every index anywhere on the panel is one of the 6 legal
    Spectra 6 panel indices, and `bg_idx` (the state's flat background
    fill) is the single most common index on the panel.

    A real illustration's own livery colors may legitimately use every
    other legal index anywhere on the canvas, so the contract is just "no
    illegal index anywhere, and the flat field is provably dominant" - not
    a spatially-scoped check.
    """
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    illegal = idx_set - _LEGAL_PANEL_INDICES
    assert not illegal, (
        "canvas (bg_idx=%r) contains illegal palette index(es) %r - expected a subset of the 6 legal panel indices %r"
        % (bg_idx, sorted(illegal), sorted(_LEGAL_PANEL_INDICES))
    )

    counts = {value: count for count, value in colors} if colors else {}
    bg_count = counts.get(bg_idx, 0)
    other_max = max((count for value, count in counts.items() if value != bg_idx), default=0)
    assert bg_count >= other_max, (
        "canvas's state index bg_idx=%r has %d pixels, not >= the next most common index's %d pixels - "
        "the flat background field is not dominant" % (bg_idx, bg_count, other_max)
    )


def _build_active_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, state_dir=None,
):
    """Build the departing/arriving two-flight poster canvas.

    `battery_low`/`source_fault`: when True, draw the bottom-left
    battery-low icon / bottom-centre source-fault badge in the state's
    own ink, via `style.state_ink_index()` so neither can use an illegal
    index.

    `state_dir`: forwarded to both `illustrations.select_illustration()`
    calls below, so an illustration override placed under this cycle's
    state dir reaches the rendered canvas. `None` means vendored-only.
    """
    if state not in style.STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = style.state_background_index(state, theme_id=theme_id)
    fg_idx = style.state_ink_index(state, theme_id=theme_id)

    # Dithering and text weight are theme properties, not derivable from
    # bg_idx alone - see THEMES' own module comment in device_config.py.
    normalised_theme_id = device_config.normalise_theme_id(theme_id)
    theme_dithered = device_config.theme_dithered(normalised_theme_id)
    weight = device_config.theme_weight(normalised_theme_id)

    is_band_theme = device_config.theme_is_band(normalised_theme_id)
    band_idx = device_config.theme_band_index(normalised_theme_id) if is_band_theme else None
    band_dithered_flag = device_config.theme_band_dithered(normalised_theme_id) if is_band_theme else False

    # Dithering toward White is the only way to lighten a fixed physical
    # ink that reads too dark/saturated at full-panel coverage; themes
    # with `dithered: False` get a flat fill instead.
    canvas = dither.dithered_state_background(bg_idx) if theme_dithered else pf.new_canvas(bg_idx)

    # Band painted first so illustrations occlude it naturally.
    if is_band_theme:
        draw_diagonal_band(canvas, band_idx, dithered=band_dithered_flag)

    # The frame outline is no longer drawn, but style.FRAME_INSET_FRAC
    # still feeds inner_width and glyphs.draw_source_fault_badge()'s
    # bottom anchor.

    draw_top_labels(canvas, state, fg_idx, bg_idx, weight, runway_id=runway_id, band_theme=is_band_theme)

    # Main flight: current detection, always nose-left.
    inner_width = WIDTH * (1 - 2 * style.FRAME_INSET_FRAC)
    main_w = round(inner_width * style.MAIN_ILLUSTRATION_WIDTH_FRAC)

    main_path = illustrations.select_illustration(route, flight.get("aircraft_type"), state_dir=state_dir)
    main_placement = None
    main_resized = _load_illustration_safely(main_path, main_w)
    if main_resized is not None:
        main_left = _left_for_centered_content(main_resized, WIDTH / 2)
        main_top = _top_for_centered_content(main_resized, HEIGHT * style.MAIN_ILLUSTRATION_CENTER_Y_FRAC)
        main_placement = draw_illustration(canvas, main_resized, main_left, main_top)
        style._assert_within_canvas(main_placement.rect, "main aircraft illustration")
        text.draw_main_text_block(canvas, flight, state, route, main_placement, fg_idx, bg_idx, weight, band_idx=band_idx)

    # Previous flight: the detection immediately preceding this one.
    if previous_flight is not None and main_placement is not None:
        prev_path = illustrations.select_illustration(previous_route, (previous_flight or {}).get("aircraft_type"), state_dir=state_dir)
        # SIZE derives from `.rect` (constant per file), not `.content`,
        # so it does not depend on which airline is in the main slot.
        main_rect = main_placement.rect
        prev_w = round((main_rect[2] - main_rect[0]) * style.PREVIOUS_ILLUSTRATION_WIDTH_FRAC)
        prev_resized = _load_illustration_safely(prev_path, prev_w)
        if prev_resized is not None:
            # POSITION is anchored to painted pixels: right-aligned to
            # the main illustration's visible right edge, centred on
            # PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC.
            prev_left = _left_for_right_aligned_content(prev_resized, main_placement.content[2])
            prev_top = _top_for_centered_content(prev_resized, HEIGHT * style.PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC)
            prev_placement = draw_illustration(canvas, prev_resized, prev_left, prev_top)
            style._assert_within_canvas(prev_placement.rect, "previous aircraft illustration")
            text.draw_previous_text_block(canvas, previous_flight, previous_state, previous_route, prev_placement, fg_idx, bg_idx, weight, band_idx=band_idx)

    # The source-fault badge, drawn last so it sits on top of everything
    # else, using the state's own resolved ink index.
    if source_fault:
        glyphs.draw_source_fault_badge(canvas, fg_idx, weight=weight)

    if battery_low:
        glyphs.draw_battery_icon(canvas, ImageDraw.Draw(canvas), fg_idx)

    # Guard rail: every index on the panel is legal, and the flat
    # background field is provably dominant.
    _assert_legal_palette(canvas, bg_idx)

    return canvas


def build_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None, state_dir=None,
):
    """Pre-pack "P"-mode canvas for `flight` in `state` ("departing" /
    "arriving" / "empty" / "quiet_hours" / "display_off" /
    "battery_empty"). Public so callers never reach into private render
    state.

    `route`: a full or airline-only route, `None` on a miss or for the
    empty state. `theme_id`/`runway_id`: registry ids, degrading to the
    default when unrecognised. `source_fault`: only when every ADS-B
    source has failed. `quiet_hours_until` ("HH:MM") applies only to
    `state == "quiet_hours"`. `state_dir`: forwarded to
    `_build_active_canvas()` only - the hold-screen builders in
    `hold_screens.py` (`_build_battery_empty_canvas`/
    `_build_display_off_canvas`/`_build_quiet_hours_canvas`/
    `_build_empty_canvas`) draw no illustration and never consult it.

    `"display_off"`/`"quiet_hours"`/`"empty"` are always White/Black.
    `"battery_empty"` ignores every other argument: its bytes/hash must
    stay constant for the whole parked episode.
    """
    if state == "battery_empty":
        return hold_screens._build_battery_empty_canvas()
    if state == "display_off":
        return hold_screens._build_display_off_canvas(source_fault=source_fault, battery_low=battery_low)
    if state == "quiet_hours":
        return hold_screens._build_quiet_hours_canvas(
            quiet_hours_until=quiet_hours_until, source_fault=source_fault, battery_low=battery_low)
    if flight is None or state == "empty":
        return hold_screens._build_empty_canvas(
            runway_id=runway_id, source_fault=source_fault, battery_low=battery_low)
    return _build_active_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=theme_id,
        runway_id=runway_id,
        source_fault=source_fault,
        battery_low=battery_low,
        state_dir=state_dir,
    )


def render_panel(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None,
):
    """Return a packed 960,000-byte panel for `flight` in `state`
    ("departing" / "arriving" / "empty" / "quiet_hours" / "display_off" /
    "battery_empty"). All other arguments pass straight through to
    `build_canvas()` - see its docstring for the full contract.
    """
    canvas = build_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=theme_id,
        runway_id=runway_id,
        source_fault=source_fault,
        battery_low=battery_low,
        quiet_hours_until=quiet_hours_until,
    )
    return pf.pack_panel(canvas)
