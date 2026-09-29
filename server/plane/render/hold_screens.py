"""The five non-active-flight canvases: empty (watching), quiet hours,
display off, battery empty, and no-connection. All five funnel through
one of two shared compositions (`_build_hold_canvas`/
`_build_dimmed_hold_canvas`) - a centred glyph, tracked label, optional
rule, and wrapped body text over a flat or dithered field.

Must not import `layout.py`: `layout.build_canvas()` dispatches into this
module, so the reverse import would cycle.
"""
from PIL import ImageDraw

from server import device_config
from server.plane import dither
from server.plane.render import glyphs, style, text
from server import panel_format as pf


def _build_empty_canvas(runway_id=device_config.DEFAULT_RUNWAY_ID, source_fault=False, battery_low=False):
    """Build the empty-state canvas ("Watching Runway 3" by default; the
    heading follows `runway_id`). Uses the shared hold composition
    (`_build_hold_canvas()`, white variant), the one white hold screen -
    the frame is working here, not resting.

    `battery_low`/`source_fault`: independent device/server-health
    indicators, both drawn in `style.EMPTY_INK` when True.
    """
    # Heading is upper-cased at draw time only; style.EMPTY_HEADING_TEXT
    # and style.empty_heading_text() stay untouched.
    return _build_hold_canvas(
        glyphs.draw_runway_icon,
        glyphs.RUNWAY_ICON_HEIGHT_PX,
        style.empty_heading_text(runway_id).upper(),
        style.EMPTY_BODY_LINES,
        pf.IDX_WHITE,
        style.EMPTY_INK,
        False,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_quiet_hours_canvas(quiet_hours_until=None, source_fault=False, battery_low=False):
    """Build the scheduled-quiet-hours canvas via the shared dimmed hold
    composition (crescent mark, white ink on a dithered dark field) -
    always White/Black regardless of the configured theme.

    `quiet_hours_until` is the "HH:MM" end-time string from
    `device_config.seconds_until_quiet_hours_end()`; when missing, empty
    or non-string, the body line is omitted rather than showing
    "Back at None".

    `battery_low`/`source_fault`: as `_build_empty_canvas()`, drawn in
    `style.DIMMED_INK`.
    """
    if isinstance(quiet_hours_until, str) and quiet_hours_until:
        sentences = (style.QUIET_HOURS_BODY_TEMPLATE % quiet_hours_until,)
    else:
        sentences = ()
    return _build_dimmed_hold_canvas(
        glyphs.draw_moon_icon,
        glyphs.MOON_ICON_DIAMETER_PX,
        style.QUIET_HOURS_HEADING_TEXT,
        sentences,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_display_off_canvas(source_fault=False, battery_low=False):
    """Build the remote display-off canvas via the shared dimmed hold
    composition (power-ring mark), always White/Black. Unlike the
    quiet-hours screen, `style.DISPLAY_OFF_BODY_TEXT` is a fixed constant
    with no interpolated value, so the body is always drawn.

    `battery_low`/`source_fault`: as `_build_empty_canvas()`, drawn in
    `style.DIMMED_INK`.
    """
    return _build_dimmed_hold_canvas(
        glyphs.draw_power_icon,
        glyphs.POWER_ICON_BAR_RISE_PX + glyphs.POWER_ICON_DIAMETER_PX,
        style.DISPLAY_OFF_HEADING_TEXT,
        style.DISPLAY_OFF_BODY_LINES,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_battery_empty_canvas():
    """Build the BATTERY EMPTY hold canvas via the shared
    `_build_dimmed_hold_canvas()` composition. poll_loop.py latches this
    state once pack voltage crosses BATTERY_CRITICAL_MV.

    Accepts no `theme_id`/`battery_low`/`source_fault`: the image's bytes
    (and sha256 hash) must stay constant for the whole parked episode, so
    every hourly byos check-in is a hash-skip, never a redraw.
    """
    return _build_dimmed_hold_canvas(
        glyphs.draw_empty_battery_icon,
        glyphs.EMPTY_BATTERY_ICON_HEIGHT_PX,
        style.BATTERY_EMPTY_HEADING_TEXT,
        style.BATTERY_EMPTY_BODY_LINES,
    )


def _build_no_connection_canvas(flat=False):
    """Build the NO CONNECTION hold canvas via `_build_hold_canvas()`.
    Never reached by `layout.build_canvas()`: the device draws this screen
    entirely on its own in firmware, from a generated ink mask
    (`firmware/tools/gen_fault_screen.py` ->
    `firmware/main/fault_screen_mask.h`); this function is that mask's
    one source of truth on the Python side.

    `flat=True` (used only by `gen_fault_screen.py`) returns a flat
    two-colour canvas with no dither noise, so its ink-mask extraction
    (`pixel == IDX_WHITE`) is exact.
    """
    return _build_hold_canvas(
        glyphs.draw_alert_icon,
        glyphs.ALERT_ICON_HEIGHT_PX,
        style.NO_CONNECTION_HEADING_TEXT,
        style.NO_CONNECTION_BODY_LINES,
        style.DIMMED_FIELD_IDX,
        style.DIMMED_INK,
        not flat,
    )


def _build_updating_canvas(flat=False):
    """Build the UPDATING hold canvas via `_build_hold_canvas()`, the same
    shared composition `_build_no_connection_canvas()` uses. Never reached
    by `layout.build_canvas()`: the device draws this screen entirely on
    its own in firmware, from a generated ink mask
    (`firmware/tools/gen_fault_screen.py --screen updating` ->
    `firmware/main/updating_screen_mask.h`); this function is that mask's
    one source of truth on the Python side, the same relationship
    `_build_no_connection_canvas()` has to the NO CONNECTION mask.

    `flat=True` (used only by `gen_fault_screen.py`) returns a flat
    two-colour canvas with no dither noise, so its ink-mask extraction
    (`pixel == IDX_WHITE`) is exact - see `_build_no_connection_canvas()`'s
    own docstring for why.

    No `source_fault`/`battery_low` badges: an update never starts while
    the battery-low alert is active, so `battery_low` is structurally
    always False here, and `source_fault` (ADS-B corroboration) is
    orthogonal to a firmware update and would confuse the reader mid-update.
    """
    return _build_hold_canvas(
        glyphs.draw_updating_icon,
        glyphs.UPDATING_ICON_DIAMETER_PX,
        style.UPDATING_HEADING_TEXT,
        style.UPDATING_BODY_LINES,
        style.DIMMED_FIELD_IDX,
        style.DIMMED_INK,
        not flat,
    )


def _build_hold_canvas(glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered, source_fault=False, battery_low=False):
    """Shared hold-screen composition: a field (`field_idx` dithered
    toward White when `dithered`, else flat) with a vertically-centred
    block in `ink` - glyph, tracked Bold label, short rule, body.
    `sentences` are wrapped one by one so an authored line break is
    honoured; an empty tuple omits the body entirely.

    `battery_low`/`source_fault`: device/server-health indicators drawn
    in the screen's own `ink`.
    """
    canvas = dither.dithered_state_background(field_idx) if dithered else pf.new_canvas(field_idx)
    draw = ImageDraw.Draw(canvas)
    center_x = pf.WIDTH // 2
    safe_width = style.SAFE_BOX[2] - style.SAFE_BOX[0]

    label_font = text._font(style.DIMMED_LABEL_FONT)
    tracking = style.DIMMED_LABEL_TRACKING_PX
    label_width = sum(label_font.getlength(ch) for ch in label_text) + tracking * (len(label_text) - 1)
    label_ascent, label_descent = label_font.getmetrics()
    label_height = label_ascent + label_descent

    body_font = text._font(style.DIMMED_BODY_FONT)
    body_lines = []
    for sentence in sentences:
        body_lines.extend(text._wrap_text(body_font, sentence, safe_width))
    body_ascent, body_descent = body_font.getmetrics()
    body_line_height = body_ascent + body_descent + style.DIMMED_BODY_LINE_GAP_PX

    total_height = (
        glyph_height
        + style.SPACE_MD
        + label_height
        + style.SPACE_MD
        + style.DIMMED_RULE_HEIGHT_PX
        + (style.SPACE_MD + len(body_lines) * body_line_height if body_lines else 0)
    )
    start_y = (pf.HEIGHT - total_height) // 2

    half = max(glyphs.POWER_ICON_DIAMETER_PX, glyphs.MOON_ICON_DIAMETER_PX) // 2
    style._assert_in_safe_box((center_x - half, start_y, center_x + half, start_y + glyph_height), "dimmed-hold glyph")
    glyph_draw(draw, center_x, start_y, ink)

    label_y = start_y + glyph_height + style.SPACE_MD
    label_left = round(center_x - label_width / 2)
    style._assert_in_safe_box((label_left, label_y, round(label_left + label_width), label_y + label_height), "dimmed-hold label")
    text.draw_tracked_text(draw, (label_left, label_y), label_text, label_font, ink, tracking=tracking)

    rule_y = label_y + label_height + style.SPACE_MD
    rule_left = center_x - style.DIMMED_RULE_WIDTH_PX // 2
    draw.rectangle((rule_left, rule_y, rule_left + style.DIMMED_RULE_WIDTH_PX, rule_y + style.DIMMED_RULE_HEIGHT_PX - 1), fill=ink)

    y = rule_y + style.DIMMED_RULE_HEIGHT_PX + style.SPACE_MD
    for line in body_lines:
        line_bbox = draw.textbbox((center_x, y), line, font=body_font, anchor="ma")
        style._assert_in_safe_box(line_bbox, "dimmed-hold body line")
        draw.text((center_x, y), line, font=body_font, fill=ink, anchor="ma")
        y += body_line_height

    if source_fault:
        glyphs.draw_source_fault_badge(canvas, ink, weight="bold")

    if battery_low:
        glyphs.draw_battery_icon(canvas, draw, ink)

    return canvas


def _build_dimmed_hold_canvas(glyph_draw, glyph_height, label_text, sentences, source_fault=False, battery_low=False):
    """Dimmed variant of `_build_hold_canvas()`: `style.DIMMED_FIELD_IDX`
    dithered toward White, `style.DIMMED_INK` for everything drawn on it."""
    return _build_hold_canvas(
        glyph_draw, glyph_height, label_text, sentences,
        style.DIMMED_FIELD_IDX, style.DIMMED_INK, True,
        source_fault=source_fault, battery_low=battery_low,
    )
