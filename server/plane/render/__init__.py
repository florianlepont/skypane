#!/usr/bin/env python3
"""Panel renderer for the plane view: departure and arrival cards for the
watched runway, plus an empty state.

Draws onto a "P"-mode canvas with integer palette-index fills, never RGB,
to keep anti-aliasing off flat fills; the per-airline illustrations are
the one full-color, dithered exception.

Layout: flat single-color state background, no dithered gradient.
Illustrations are always nose-left, never mirrored. Two flight cards
share one canvas: current detection (large, upper-center) and the
previous one (smaller, bottom-right, right-aligned to the main
illustration's edge). Text uses PT Serif Bold, except on White (never
dithered, so Regular suffices).

Colour comes from `server/device_config.py`'s `THEMES` registry
(`white` default); not yet calibrated against real glass, only
on-screen previews. The 64px SAFE_BOX margin applies only to the
top-row labels; the frame, illustrations and flight text sit at a
tighter ~2.5%-of-width inset, inside that band.

This is a package, split by responsibility:

- `style.py` - spacing, fonts, state colours, headline copy, and the
  frame/band/battery geometry constants.
- `text.py` - font fitting, tracked (letter-spaced) text, and the main/
  previous flight text blocks.
- `glyphs.py` - the five centred hold-screen glyphs plus the two small
  status indicators (source-fault badge, low-battery icon).
- `hold_screens.py` - the five non-active-flight canvases (empty, quiet
  hours, display off, battery empty, no connection).
- `layout.py` - band, top labels, illustration placement, and the two
  canvas builders (`build_canvas`/`render_panel`).
- `cli.py` - the manual-QA preview CLI (`build_parser`/`main`).

Every name any caller or test reaches through `server.plane.render` is
re-exported below, so the public import path this module has always had
stays stable; the companion's theme preview and
`firmware/tools/gen_fault_screen.py` need no edit for this split.

Usage (manual QA):
    server/.venv/bin/python3 -m server.plane.render --state empty --out /tmp/panel.bin
    server/.venv/bin/python3 -m server.plane.render --state arriving --callsign AF1380 \
        --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 -m server.plane.render --state departing --callsign AF1380 \
        --previous-callsign VY1234 --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 -m server.plane.render --state arriving --callsign AFR56XX \
        --airline "Compagnie Nationale Royale Air Maroc Express" \
        --city "Santiago de Compostela-Rosalia de Castro" --preview /tmp/longname.png
    server/.venv/bin/python3 -m server.plane.render --calibration-preview /tmp/calib
Run from the repo root, so `server.*` resolves under `-m`.
"""
from PIL import Image, ImageDraw, ImageFont  # noqa: F401

from server import device_config  # noqa: F401
from server import panel_format as pf  # noqa: F401
from server.panel_format import (  # noqa: F401
    HEIGHT,
    IDX_BLACK,
    IDX_BLUE,
    IDX_GREEN,
    IDX_RED,
    IDX_WHITE,
    IDX_YELLOW,
    WIDTH,
)
from server.plane import dither, enrich, illustrations, runway_config  # noqa: F401

from .style import (  # noqa: F401
    BAND_BOT_LEFT_FRAC,
    BAND_BOT_RIGHT_FRAC,
    BAND_SHIFT_FRAC,
    BAND_TOP_LEFT_FRAC,
    BAND_TOP_RIGHT_FRAC,
    BATTERY_EMPTY_BODY_LINES,
    BATTERY_EMPTY_BODY_TEXT,
    BATTERY_EMPTY_HEADING_TEXT,
    BATTERY_ICON_BODY_H,
    BATTERY_ICON_BODY_W,
    BATTERY_ICON_BOTTOM,
    BATTERY_ICON_FILL_FRAC,
    BATTERY_ICON_LEFT,
    BATTERY_ICON_NUB_H,
    BATTERY_ICON_NUB_W,
    BATTERY_ICON_STROKE_PX,
    DIMMED_BODY_FONT,
    DIMMED_BODY_LINE_GAP_PX,
    DIMMED_FIELD_IDX,
    DIMMED_INK,
    DIMMED_LABEL_FONT,
    DIMMED_LABEL_TRACKING_PX,
    DIMMED_RULE_HEIGHT_PX,
    DIMMED_RULE_WIDTH_PX,
    DISPLAY_OFF_BODY_LINES,
    DISPLAY_OFF_BODY_TEXT,
    DISPLAY_OFF_HEADING_TEXT,
    EMPTY_BODY_FONT,
    EMPTY_BODY_LINES,
    EMPTY_BODY_TEXT,
    EMPTY_HEADING_FONT,
    EMPTY_HEADING_MIN_SIZE,
    EMPTY_HEADING_TEXT,
    EMPTY_INK,
    FONT_DIR,
    FRAME_INSET_FRAC,
    FRAME_STROKE_PX,
    LABEL_TRACKING_PX,
    MAIN_ILLUSTRATION_CENTER_Y_FRAC,
    MAIN_ILLUSTRATION_WIDTH_FRAC,
    MAIN_LINE1_FONT,
    MAIN_LINE1_MIN_SIZE,
    MAIN_LINE2_FONT,
    MAIN_LINE2_MIN_SIZE,
    MAIN_LINE_GAP_PX,
    MAIN_TEXT_GAP_PX,
    MARGIN,
    NO_CONNECTION_BODY_LINES,
    NO_CONNECTION_BODY_TEXT,
    NO_CONNECTION_HEADING_TEXT,
    PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC,
    PREVIOUS_ILLUSTRATION_WIDTH_FRAC,
    PREVIOUS_LINE1_FONT,
    PREVIOUS_LINE1_MIN_SIZE,
    PREVIOUS_LINE2_FONT,
    PREVIOUS_LINE2_MIN_SIZE,
    PREVIOUS_LINE_GAP_PX,
    PREVIOUS_TEXT_GAP_PX,
    PREVIOUS_TEXT_LEFT_OFFSET_PX,
    PT_SERIF_BOLD,
    PT_SERIF_REGULAR,
    QUIET_HOURS_BODY_TEMPLATE,
    QUIET_HOURS_HEADING_TEXT,
    ROUTE_FALLBACK_TEXT,
    SAFE_BOX,
    SOURCE_FAULT_GLYPH_PX,
    SOURCE_FAULT_TEXT,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    STATE_BACKGROUND,
    STATE_INK,
    STATE_LABEL_FONT,
    STATE_LABEL_TEXT,
    TOP_RIGHT_TAG_TEXT,
    TOP_TAG_FONT,
    UPDATING_BODY_LINES,
    UPDATING_BODY_TEXT,
    UPDATING_HEADING_TEXT,
    _BAND_TOP_LABEL_DIRECTION,
    _FIT_STEP_PX,
    _assert_in_safe_box,
    _assert_within_canvas,
    _band_center_x,
    _band_edges,
    empty_heading_text,
    runway_tag_text,
    state_background_index,
    state_ink_index,
)
from .text import (  # noqa: F401
    BAND_MAIN_AIRLINE_FONT,
    BAND_MAIN_AIRLINE_MIN_SIZE,
    BAND_MAIN_DASH_GAP,
    BAND_MAIN_DASH_W,
    BAND_MAIN_NUMBER_FONT,
    BAND_MAIN_NUMBER_MIN_SIZE,
    BAND_MAIN_ROUTE_FONT,
    BAND_MAIN_ROUTE_MIN_SIZE,
    BAND_PREV_AIRLINE_FONT,
    BAND_PREV_AIRLINE_MIN_SIZE,
    BAND_PREV_DASH_GAP,
    BAND_PREV_DASH_W,
    BAND_PREV_NUMBER_FONT,
    BAND_PREV_NUMBER_MIN_SIZE,
    BAND_PREV_ROUTE_FONT,
    BAND_PREV_ROUTE_MIN_SIZE,
    _AIRLINE_DISPLAY_ALIASES,
    _TYPE_DISPLAY_LABELS,
    _flight_line1_text,
    _flight_line2_text,
    _font,
    _font_cache,
    _role_fit_text_size,
    _role_fit_tracked_text_size,
    _role_font,
    _role_weight_path,
    _tracked_text_bbox,
    _tracked_text_width,
    _wrap_text,
    display_airline_name,
    draw_main_text_block,
    draw_previous_text_block,
    draw_tracked_text,
    fit_text_size,
)
from .glyphs import (  # noqa: F401
    ALERT_ICON_HEIGHT_PX,
    ALERT_ICON_STROKE_PX,
    ALERT_ICON_WIDTH_PX,
    EMPTY_BATTERY_ICON_HEIGHT_PX,
    EMPTY_BATTERY_ICON_STROKE_PX,
    EMPTY_BATTERY_ICON_WIDTH_PX,
    EMPTY_BATTERY_NUB_H_PX,
    EMPTY_BATTERY_NUB_W_PX,
    MOON_ICON_BITE_DIAMETER_PX,
    MOON_ICON_BITE_OFFSET_PX,
    MOON_ICON_DIAMETER_PX,
    MOON_ICON_SAMPLES,
    POWER_ICON_BAR_DROP_PX,
    POWER_ICON_BAR_RISE_PX,
    POWER_ICON_DIAMETER_PX,
    POWER_ICON_GAP_DEGREES,
    POWER_ICON_STROKE_PX,
    RUNWAY_ICON_DASH_GAP_PX,
    RUNWAY_ICON_DASH_PX,
    RUNWAY_ICON_HEIGHT_PX,
    RUNWAY_ICON_KEY_PX,
    RUNWAY_ICON_KEY_W_PX,
    RUNWAY_ICON_STROKE_PX,
    RUNWAY_ICON_WIDTH_PX,
    UPDATING_ICON_ARC_SPAN_DEGREES,
    UPDATING_ICON_ARROWHEAD_BACK_DEGREES,
    UPDATING_ICON_ARROWHEAD_SPREAD_PX,
    UPDATING_ICON_ARROWHEAD_TIP_INSET_PX,
    UPDATING_ICON_DIAMETER_PX,
    UPDATING_ICON_STROKE_PX,
    draw_alert_icon,
    draw_battery_icon,
    draw_empty_battery_icon,
    draw_moon_icon,
    draw_power_icon,
    draw_runway_icon,
    draw_source_fault_badge,
    draw_updating_icon,
)
from .hold_screens import (  # noqa: F401
    _build_battery_empty_canvas,
    _build_dimmed_hold_canvas,
    _build_display_off_canvas,
    _build_empty_canvas,
    _build_hold_canvas,
    _build_no_connection_canvas,
    _build_quiet_hours_canvas,
    _build_updating_canvas,
)
from .layout import (  # noqa: F401
    ILLUSTRATION_ALPHA_THRESHOLD,
    IllustrationPlacement,
    _LEGAL_PANEL_INDICES,
    _assert_legal_palette,
    _build_active_canvas,
    _illustration_cache,
    _ILLUSTRATION_CACHE_MAX_ENTRIES,
    _illustration_over_pixel_cap,
    _left_for_centered_content,
    _left_for_right_aligned_content,
    _load_illustration_safely,
    _opaque_bbox,
    _resize_illustration,
    _threshold_alpha,
    _top_for_centered_content,
    build_canvas,
    draw_diagonal_band,
    draw_frame,
    draw_illustration,
    draw_top_labels,
    render_panel,
)
from .cli import (  # noqa: F401
    _PREVIEW_PREVIOUS_ROUTE,
    _PREVIEW_ROUTE,
    build_parser,
    main,
)
