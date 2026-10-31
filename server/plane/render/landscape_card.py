"""Active flight card (departing / arriving) for the native landscape layout
family.

The aircraft illustration fills the left of the canvas, nose-left; the right
column holds the flight text and, when there is one, a compact strip for
the previous flight. Band themes add a diagonal band across the full canvas,
slanted like the portrait band; the flight text and previous strip are
centred inside it in white ink and the aircraft illustration is drawn over
it. Every dimension derives from the canvas size passed in, so any landscape
panel renders natively.
"""
from typing import NamedTuple

from PIL import Image, ImageDraw

from server import device_config
from server import panel_format as pf
from server.plane import dither, illustrations
from server.plane.render import landscape_common as common, layout, style, text

ILLUSTRATION_LEFT_FRACTION = 0.0
ILLUSTRATION_RIGHT_FRACTION = 0.55
ILLUSTRATION_MAX_HEIGHT_FRACTION = 0.55
TEXT_LEFT_FRACTION = 0.58
BAND_CENTER_FRACTION = 0.70
BAND_TOP_WIDTH_FRACTION = 0.34
BAND_BOTTOM_WIDTH_FRACTION = 0.46
BAND_TEXT_REFERENCE_HEIGHT_FRACTION = 0.4
BAND_TEXT_INK = pf.IDX_WHITE
LABEL_HEIGHT_FRACTION = 0.045
LABEL_TRACKING_FRACTION = 0.008
LINE1_HEIGHT_FRACTION = 0.075
LINE1_MIN_FRACTION = 0.045
LINE2_HEIGHT_FRACTION = 0.048
LINE2_MIN_FRACTION = 0.032
PREVIOUS_HEIGHT_FRACTION = 0.034
LINE_GAP_FRACTION = 0.012
BLOCK_GAP_FRACTION = 0.03
LINE1_MAX_LINES = 3
LINE2_MAX_LINES = 2
ELLIPSIS = "…"


class CardGeometry(NamedTuple):
    """Pixel columns of a landscape card for one canvas size. For band
    themes the text columns are the nominal text width at the band's
    mid-height; lines are centred on the band, not on these edges."""

    margin: int
    illustration_left: int
    illustration_right: int
    text_left: int
    text_right: int
    band: bool
    overlay_right: int


def band_slope(size):
    """Horizontal shift per row of the band's centreline (towards the left
    going down): the portrait band's slope, so both orientations share one
    angle."""
    return (style.BAND_TOP_LEFT_FRAC - style.BAND_BOT_LEFT_FRAC) * pf.WIDTH / pf.HEIGHT


def band_center(size, y):
    """Horizontal centre of the band at canvas row `y`."""
    width, height = size
    return BAND_CENTER_FRACTION * width + band_slope(size) * (height / 2 - y)


def band_edges(size, y):
    """Band's (left, right) pixel edges at canvas row `y`; it widens
    linearly from the top row to the bottom row."""
    width, height = size
    fraction = BAND_TOP_WIDTH_FRACTION + (BAND_BOTTOM_WIDTH_FRACTION - BAND_TOP_WIDTH_FRACTION) * y / height
    center = band_center(size, y)
    return center - fraction * width / 2, center + fraction * width / 2


def band_span(size, center, y_top, y_bottom):
    """Width of the text that, centred on `center`, stays inside the band
    for every row from `y_top` to `y_bottom`, with a margin of clearance
    on both sides."""
    pad = common.margin_for(size)
    half = min(
        min(center - left, right - center)
        for left, right in (band_edges(size, y_top), band_edges(size, y_bottom))
    )
    return max(1, round(2 * (half - pad)))


def card_geometry(size, band_theme) -> CardGeometry:
    """Column edges for `size`. A band theme sizes the text column to fit
    inside the band around the text block's expected extent and keeps the
    bottom-left overlays clear of the band's left edge."""
    width, height = size
    margin = common.margin_for(size)
    if band_theme:
        mid = height / 2
        reference = BAND_TEXT_REFERENCE_HEIGHT_FRACTION * height
        center = band_center(size, mid)
        column = band_span(size, center, mid - reference / 2, mid + reference / 2)
        text_left = round(center - column / 2)
        text_right = text_left + column
        overlay_right = max(margin, round(band_edges(size, height)[0] - margin))
    else:
        text_left = round(width * TEXT_LEFT_FRACTION)
        text_right = width - margin
        overlay_right = text_left
    return CardGeometry(
        margin=margin,
        illustration_left=margin + round(width * ILLUSTRATION_LEFT_FRACTION),
        illustration_right=round(width * ILLUSTRATION_RIGHT_FRACTION),
        text_left=text_left,
        text_right=text_right,
        band=bool(band_theme),
        overlay_right=overlay_right,
    )


def draw_diagonal_band(canvas, band_idx, dithered):
    """Paint the full-canvas diagonal band in `band_idx` (flat or dithered
    toward White) onto `canvas`, behind all later drawing."""
    size = canvas.size
    height = size[1]
    top_left, top_right = band_edges(size, 0)
    bottom_left, bottom_right = band_edges(size, height)
    poly = [(top_left, 0), (top_right, 0), (bottom_right, height), (bottom_left, height)]
    if dithered:
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        canvas.paste(dither.dithered_state_background(band_idx, size=size), (0, 0), mask)
    else:
        ImageDraw.Draw(canvas).polygon(poly, fill=band_idx)


def _ellipsize(font, value, max_width):
    """`value` cut to fit `max_width` with a trailing ellipsis when needed."""
    if font.getlength(value) <= max_width:
        return value
    while value and font.getlength(value + ELLIPSIS) > max_width:
        value = value[:-1]
    return value.rstrip() + ELLIPSIS


def _fit_lines(font_path, initial_px, min_px, value, max_width, max_lines):
    """Font and lines for `value`: one line shrunk to fit when possible,
    otherwise wrapped at the minimum size and ellipsized to `max_lines`
    lines, each at most `max_width` wide."""
    font = text.fit_text_size(font_path, initial_px, value, max_width, min_px)
    if font.getlength(value) <= max_width:
        return font, [value]
    lines = text._wrap_text(font, value, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1] + ELLIPSIS
    return font, [_ellipsize(font, line, max_width) for line in lines]


def _line_height(font, size):
    """Advance of one text line in `font` including the inter-line gap."""
    ascent, descent = font.getmetrics()
    return ascent + descent + max(2, round(size[1] * LINE_GAP_FRACTION))


def _draw_top_row(canvas, size, state, geom, ink, weight, runway_id):
    """State label at the left and runway tag at the right, both tracked.
    The tag is flush to the text column's right edge, or centred on the
    band's top row in white ink for band themes."""
    draw = ImageDraw.Draw(canvas)
    px = max(12, round(size[1] * LABEL_HEIGHT_FRACTION))
    tracking = max(1, round(size[1] * LABEL_TRACKING_FRACTION))
    font = text._font((text._role_weight_path(weight), px, None))
    label = style.STATE_LABEL_TEXT[state]
    tag = style.runway_tag_text(runway_id)
    top = geom.margin
    label_bbox = text._tracked_text_bbox(font, (geom.margin, top), label, tracking)
    common.assert_within_canvas(label_bbox, size, "landscape state label")
    text.draw_tracked_text(draw, (geom.margin, top), label, font, ink, tracking=tracking)
    tag_width = text._tracked_text_width(font, tag, tracking)
    if geom.band:
        tag_x = band_center(size, top + px / 2) - tag_width / 2
    else:
        tag_x = geom.text_right - tag_width
    tag_ink = BAND_TEXT_INK if geom.band else ink
    tag_bbox = text._tracked_text_bbox(font, (tag_x, top), tag, tracking)
    common.assert_within_canvas(tag_bbox, size, "landscape runway tag")
    text.draw_tracked_text(draw, (tag_x, top), tag, font, tag_ink, tracking=tracking)
    return label_bbox[3]


def _draw_illustration(canvas, size, geom, flight, route, state_dir):
    """Draw the main aircraft, nose-left, in the left column; returns its
    placement or None when no illustration could be loaded."""
    width, height = size
    target_w = geom.illustration_right - geom.illustration_left
    path = illustrations.select_illustration(route, flight.get("aircraft_type"), state_dir=state_dir)
    resized = layout._load_illustration_safely(path, target_w)
    if resized is None:
        return None
    max_h = round(height * ILLUSTRATION_MAX_HEIGHT_FRACTION)
    if resized.size[1] > max_h:
        resized = layout._load_illustration_safely(path, max(1, round(target_w * max_h / resized.size[1])))
        if resized is None:
            return None
    center_x = (geom.illustration_left + geom.illustration_right) / 2
    left = layout._left_for_centered_content(resized, center_x)
    top = layout._top_for_centered_content(resized, height / 2)
    placement = layout.draw_illustration(canvas, resized, left, top)
    common.assert_within_canvas(placement.content, size, "landscape aircraft illustration")
    return placement


def _main_text_lines(size, geom, flight, state, route, weight):
    """Fitted (font, lines) pairs for the two main text lines; the first
    pair is None when the flight has no line 1."""
    path = text._role_weight_path(weight)
    width = geom.text_right - geom.text_left
    line1 = text._flight_line1_text(flight, state, route)
    line2 = text._flight_line2_text(route, flight.get("aircraft_type"))
    first = None
    if line1:
        first = _fit_lines(
            path, round(size[1] * LINE1_HEIGHT_FRACTION), round(size[1] * LINE1_MIN_FRACTION),
            line1, width, LINE1_MAX_LINES,
        )
    second = _fit_lines(
        path, round(size[1] * LINE2_HEIGHT_FRACTION), round(size[1] * LINE2_MIN_FRACTION),
        line2, width, LINE2_MAX_LINES,
    )
    return first, second


def _centered_line(draw, size, geom, line, font, y, center, ink, what):
    """Draw `line` centred on `center` (band themes) or left-aligned in the
    text column; a band line is first ellipsized to the band's width over
    its own rows so it never overhangs onto the background."""
    if not geom.band:
        bbox = draw.textbbox((geom.text_left, y), line, font=font)
        common.assert_within_canvas(bbox, size, what)
        draw.text((geom.text_left, y), line, font=font, fill=ink)
        return
    ascent, descent = font.getmetrics()
    line = _ellipsize(font, line, band_span(size, center, y, y + ascent + descent))
    bbox = draw.textbbox((center, y), line, font=font, anchor="ma")
    common.assert_within_canvas(bbox, size, what)
    draw.text((center, y), line, font=font, fill=BAND_TEXT_INK, anchor="ma")


def _draw_main_text(canvas, size, geom, flight, state, route, ink, weight, top, bottom):
    """Draw the flight text block vertically centred between `top` and
    `bottom`: left-aligned in the text column, or centred on the band at
    the block's mid-height for band themes."""
    draw = ImageDraw.Draw(canvas)
    groups = [g for g in _main_text_lines(size, geom, flight, state, route, weight) if g]
    gap = round(size[1] * BLOCK_GAP_FRACTION)
    heights = [len(lines) * _line_height(font, size) for font, lines in groups]
    block_h = sum(heights) + gap * (len(groups) - 1)
    y = top + max(0, (bottom - top - block_h) // 2)
    center = band_center(size, y + block_h / 2) if geom.band else 0
    for font, lines in groups:
        for line in lines:
            _centered_line(draw, size, geom, line, font, y, center, ink, "landscape flight text")
            y += _line_height(font, size)
        y += gap


def _previous_strip_height(size):
    """Height reserved at the bottom of the text column for the strip."""
    px = max(10, round(size[1] * PREVIOUS_HEIGHT_FRACTION))
    return px + 2 * round(size[1] * BLOCK_GAP_FRACTION)


def _draw_previous_strip(canvas, size, geom, previous_flight, previous_state, previous_route, ink, weight):
    """One ellipsized line for the previous flight above a thin rule, at
    the bottom of the text column (centred on the band for band themes)."""
    draw = ImageDraw.Draw(canvas)
    px = max(10, round(size[1] * PREVIOUS_HEIGHT_FRACTION))
    font = text._font((text._role_weight_path(weight), px, None))
    state_word = style.STATE_LABEL_TEXT.get(previous_state, "").lower()
    summary = text._flight_line1_text(previous_flight, previous_state, previous_route)
    if not summary:
        summary = text._flight_line2_text(previous_route, previous_flight.get("aircraft_type"))
    line = "Previous %s \u00b7 %s" % (state_word, summary) if state_word else "Previous \u00b7 %s" % (summary,)
    ascent, descent = font.getmetrics()
    y = size[1] - geom.margin - ascent - descent
    rule_y = y - round(size[1] * BLOCK_GAP_FRACTION) // 2
    if geom.band:
        center = band_center(size, y)
        ink = BAND_TEXT_INK
        rule_left = center - band_span(size, center, rule_y, y + ascent + descent) / 2
        rule_right = center + (center - rule_left)
        line = line.strip()
    else:
        center = 0
        rule_left, rule_right = geom.text_left, geom.text_right
        line = _ellipsize(font, line.strip(), geom.text_right - geom.text_left)
    draw.line((rule_left, rule_y, rule_right, rule_y), fill=ink, width=max(1, round(size[1] * 0.004)))
    _centered_line(draw, size, geom, line, font, y, center, ink, "landscape previous strip")


def _battery_box(size, margin):
    """Bottom-left battery body box (left, top, right, bottom) and nub
    width, all derived from the canvas height."""
    body_h = max(12, round(size[1] * 0.045))
    body_w = body_h * 2
    bottom = size[1] - margin
    return (margin, bottom - body_h, margin + body_w, bottom), max(3, body_h // 4)


def draw_battery_low(canvas, size, ink):
    """Bottom-left low-battery glyph: outlined body, nub and a short fill."""
    margin = common.margin_for(size)
    box, nub_w = _battery_box(size, margin)
    left, top, right, bottom = box
    stroke = max(2, (bottom - top) // 10)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(box, outline=ink, width=stroke)
    nub_h = (bottom - top) // 2
    nub_top = top + ((bottom - top) - nub_h) // 2
    draw.rectangle((right, nub_top, right + nub_w, nub_top + nub_h), fill=ink)
    fill_w = round((right - left - 2 * stroke) * 0.22)
    draw.rectangle((left + stroke, top + stroke, left + stroke + fill_w, bottom - stroke), fill=ink)


def draw_source_fault(canvas, size, geom, ink, weight):
    """Alert triangle and caption in the bottom-left corner, right of the
    battery slot, clear of the text column and the band."""
    draw = ImageDraw.Draw(canvas)
    box, nub_w = _battery_box(size, geom.margin)
    side = max(16, round(size[1] * 0.06))
    gap = max(6, round(size[1] * 0.015))
    left = box[2] + nub_w + 2 * gap
    bottom = size[1] - geom.margin
    top = bottom - side
    stroke = max(2, side // 12)
    draw.polygon([(left + side // 2, top), (left + side, bottom), (left, bottom)], outline=ink, width=stroke)
    mid = left + side // 2
    draw.line((mid, top + side // 3, mid, bottom - side // 3), fill=ink, width=stroke)
    draw.rectangle((mid - stroke // 2, bottom - side // 4, mid + stroke // 2, bottom - side // 4 + stroke), fill=ink)
    font = text._font((text._role_weight_path(weight), max(10, round(size[1] * 0.03)), None))
    caption_left = left + side + gap
    caption = _ellipsize(font, style.SOURCE_FAULT_TEXT, geom.overlay_right - gap - caption_left)
    ascent, descent = font.getmetrics()
    caption_top = bottom - side // 2 - (ascent + descent) // 2
    bbox = draw.textbbox((caption_left, caption_top), caption, font=font)
    common.assert_within_canvas(bbox, size, "landscape source fault caption")
    draw.text((caption_left, caption_top), caption, font=font, fill=ink)


def build_card_canvas(
    size, flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, state_dir=None,
):
    """Pre-pack "P"-mode landscape card of `size` for `flight` in `state`
    ("departing" or "arriving"). Theme colours, band and text weight come
    from `theme_id`; the previous strip is omitted when `previous_flight`
    is None."""
    if state not in style.STATE_LABEL_TEXT:
        raise ValueError("unknown card state %r (expected 'departing' or 'arriving')" % (state,))
    size = (int(size[0]), int(size[1]))
    theme_id = device_config.normalise_theme_id(theme_id)
    bg_idx = style.state_background_index(state, theme_id=theme_id)
    ink = style.state_ink_index(state, theme_id=theme_id)
    weight = device_config.theme_weight(theme_id)
    band_theme = device_config.theme_is_band(theme_id)
    geom = card_geometry(size, band_theme)
    if device_config.theme_dithered(theme_id):
        canvas = dither.dithered_state_background(bg_idx, size=size)
    else:
        canvas = pf.new_canvas(bg_idx, size)
    if band_theme:
        draw_diagonal_band(
            canvas, device_config.theme_band_index(theme_id), device_config.theme_band_dithered(theme_id)
        )
    label_bottom = _draw_top_row(canvas, size, state, geom, ink, weight, runway_id)
    _draw_illustration(canvas, size, geom, flight, route, state_dir)
    gap = round(size[1] * BLOCK_GAP_FRACTION)
    text_bottom = size[1] - geom.margin
    if previous_flight is not None:
        text_bottom -= _previous_strip_height(size)
        _draw_previous_strip(canvas, size, geom, previous_flight, previous_state, previous_route, ink, weight)
    _draw_main_text(canvas, size, geom, flight, state, route, ink, weight, label_bottom + gap, text_bottom)
    if source_fault:
        draw_source_fault(canvas, size, geom, ink, weight)
    if battery_low:
        draw_battery_low(canvas, size, ink)
    layout._assert_legal_palette(canvas, bg_idx)
    return canvas
