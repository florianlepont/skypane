"""Hold screens (empty, quiet hours, display off, battery empty, no
connection, updating) for the native landscape layout family.

One composition: a glyph centred in the left column and, in the right
column, a tracked heading, a short rule and wrapped body text, the whole
block vertically centred. Every dimension derives from the canvas size.
Must not import `layout.py` or `hold_screens.py`.
"""
from PIL import Image, ImageDraw

from server import device_config
from server import panel_format as pf
from server.plane import dither
from server.plane.render import glyphs, landscape_common as common, style, text

_RULE_HEIGHT_FRACTION = 0.008
_RULE_WIDTH_FRACTION = 0.12
_TRACKING_FRACTION = 0.012


def _tracking(size):
    """Heading letter-spacing in pixels."""
    return max(1, round(size[1] * _TRACKING_FRACTION))


def _text_metrics(size, label_text, sentences):
    """Fitted heading font, wrapped body lines and the body font."""
    cols = common.hold_columns(size)
    max_width = cols.text_right - cols.text_left
    heading_font = text._role_fit_tracked_text_size(
        (style.PT_SERIF_BOLD, common.heading_px(size), 700),
        label_text,
        _tracking(size),
        max_width,
        common.MIN_HEADING_PX,
        "bold",
    )
    body_font = text._font((style.PT_SERIF_REGULAR, common.body_px(size), 400))
    lines = []
    for sentence in sentences:
        lines.extend(text._wrap_text(body_font, sentence, max_width))
    return heading_font, body_font, lines


def _draw_text_column(draw, size, top, label_text, heading_font, body_font, lines, ink):
    """Draw heading, rule and body from `top`; returns nothing."""
    cols = common.hold_columns(size)
    tracking = _tracking(size)
    ascent, descent = heading_font.getmetrics()
    heading_h = ascent + descent
    text.draw_tracked_text(draw, (cols.text_left, top), label_text, heading_font, ink, tracking=tracking)
    heading_w = text._tracked_text_width(heading_font, label_text, tracking)
    common.assert_within_canvas(
        (cols.text_left, top, cols.text_left + heading_w, top + heading_h), size, "landscape heading"
    )
    gap = max(8, round(size[1] * 0.03))
    rule_h = max(2, round(size[1] * _RULE_HEIGHT_FRACTION))
    rule_y = top + heading_h + gap
    rule_w = round(size[0] * _RULE_WIDTH_FRACTION)
    draw.rectangle((cols.text_left, rule_y, cols.text_left + rule_w - 1, rule_y + rule_h - 1), fill=ink)
    b_asc, b_desc = body_font.getmetrics()
    line_h = b_asc + b_desc + max(2, round(size[1] * 0.01))
    y = rule_y + rule_h + gap
    for line in lines:
        bbox = draw.textbbox((cols.text_left, y), line, font=body_font)
        common.assert_within_canvas(bbox, size, "landscape body line")
        draw.text((cols.text_left, y), line, font=body_font, fill=ink)
        y += line_h


def _block_height(heading_font, body_font, lines, size):
    """Total height of the text column's content."""
    ascent, descent = heading_font.getmetrics()
    gap = max(8, round(size[1] * 0.03))
    rule_h = max(2, round(size[1] * _RULE_HEIGHT_FRACTION))
    b_asc, b_desc = body_font.getmetrics()
    line_h = b_asc + b_desc + max(2, round(size[1] * 0.01))
    body = gap + len(lines) * line_h if lines else 0
    return ascent + descent + gap + rule_h + body


def build_hold_canvas(
    size, glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered
):
    """Compose a hold screen of `size`: a flat or dithered `field_idx`
    field with the glyph, heading, rule and body drawn in `ink`. An empty
    `sentences` tuple omits the body."""
    size = (int(size[0]), int(size[1]))
    canvas = (
        dither.dithered_state_background(field_idx, size=size)
        if dithered
        else pf.new_canvas(field_idx, size)
    )
    draw = ImageDraw.Draw(canvas)
    cols = common.hold_columns(size)
    heading_font, body_font, lines = _text_metrics(size, label_text, sentences)
    block_h = _block_height(heading_font, body_font, lines, size)
    text_top = (size[1] - block_h) // 2
    glyph_top = (size[1] - glyph_height) // 2
    half = max(glyphs.POWER_ICON_DIAMETER_PX, glyphs.ALERT_ICON_WIDTH_PX) // 2
    common.assert_within_canvas(
        (cols.glyph_center_x - half, glyph_top, cols.glyph_center_x + half, glyph_top + glyph_height),
        size,
        "landscape glyph",
    )
    glyph_draw(draw, cols.glyph_center_x, glyph_top, ink)
    _draw_text_column(draw, size, text_top, label_text, heading_font, body_font, lines, ink)
    return canvas


def _dimmed(size, glyph_draw, glyph_height, label_text, sentences):
    """Dimmed variant: dithered dark field with light ink."""
    return build_hold_canvas(
        size, glyph_draw, glyph_height, label_text, sentences,
        style.DIMMED_FIELD_IDX, style.DIMMED_INK, True,
    )


def build_empty_canvas(size, runway_id=device_config.DEFAULT_RUNWAY_ID) -> Image.Image:
    """The "watching" screen: white field, black ink."""
    return build_hold_canvas(
        size, glyphs.draw_runway_icon, glyphs.RUNWAY_ICON_HEIGHT_PX,
        style.empty_heading_text(runway_id).upper(), style.EMPTY_BODY_LINES,
        pf.IDX_WHITE, style.EMPTY_INK, False,
    )


def build_quiet_hours_canvas(size, quiet_hours_until=None) -> Image.Image:
    """Quiet-hours screen; the "Back at HH:MM" line is omitted unless
    `quiet_hours_until` is a non-empty string."""
    if isinstance(quiet_hours_until, str) and quiet_hours_until:
        sentences = (style.QUIET_HOURS_BODY_TEMPLATE % quiet_hours_until,)
    else:
        sentences = ()
    return _dimmed(size, glyphs.draw_moon_icon, glyphs.MOON_ICON_DIAMETER_PX,
                   style.QUIET_HOURS_HEADING_TEXT, sentences)


def build_display_off_canvas(size) -> Image.Image:
    """Remote display-off screen."""
    return _dimmed(
        size, glyphs.draw_power_icon,
        glyphs.POWER_ICON_BAR_RISE_PX + glyphs.POWER_ICON_DIAMETER_PX,
        style.DISPLAY_OFF_HEADING_TEXT, style.DISPLAY_OFF_BODY_LINES,
    )


def build_battery_empty_canvas(size) -> Image.Image:
    """Battery-empty parked screen."""
    return _dimmed(
        size, glyphs.draw_empty_battery_icon, glyphs.EMPTY_BATTERY_ICON_HEIGHT_PX,
        style.BATTERY_EMPTY_HEADING_TEXT, style.BATTERY_EMPTY_BODY_LINES,
    )


def build_no_connection_canvas(size) -> Image.Image:
    """No-connection screen (geometry only; the device draws its own)."""
    return _dimmed(
        size, glyphs.draw_alert_icon, glyphs.ALERT_ICON_HEIGHT_PX,
        style.NO_CONNECTION_HEADING_TEXT, style.NO_CONNECTION_BODY_LINES,
    )


def build_updating_canvas(size) -> Image.Image:
    """Firmware-updating screen (geometry only; the device draws its own)."""
    return _dimmed(
        size, glyphs.draw_updating_icon, glyphs.UPDATING_ICON_DIAMETER_PX,
        style.UPDATING_HEADING_TEXT, style.UPDATING_BODY_LINES,
    )
