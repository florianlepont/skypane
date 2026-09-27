"""Hand-drawn glyphs and small status indicators: the five centred hold
glyphs (power ring, crescent, empty battery, alert triangle, runway
strip), plus the two small indicators overlaid on ANY canvas - the
bottom-centre source-fault badge and the bottom-left low-battery icon.
Each `draw_*_icon()` takes a Pillow `ImageDraw.ImageDraw` plus a centred/
top-anchored origin and returns its own total height.

The two indicators live here, not in `layout.py`, so that both
`layout.py` (active-flight canvases) and `hold_screens.py` (hold
canvases) can call them without either importing the other -
`hold_screens.py` must not import `layout.py` (`layout.build_canvas()`
dispatches into `hold_screens.py`, so the reverse import would cycle).
"""
import math

from PIL import ImageDraw

from server.panel_format import HEIGHT, WIDTH
from server.plane.render import style, text


def draw_source_fault_badge(canvas, ink_idx, weight="bold"):
    """Draw a small triangular alert glyph with `style.SOURCE_FAULT_TEXT`
    beside it, bottom-centre inside the frame. Uses `ink_idx` only, so it
    can never introduce an illegal palette index. Bounding box is kept
    small so `layout._assert_legal_palette()`'s background-dominance
    assertion still holds.

    Must be driven only by an all-providers-failed classification, never
    merely "no aircraft selected" - see `layout.render_panel()`'s docstring.

    `weight` resolves the caption's PT Serif weight via `text._role_font()`
    (Bold reads too heavy on White); defaults to `"bold"` for the
    not-theme-dependent empty-state call site.
    """
    draw = ImageDraw.Draw(canvas)
    frame_inset = round(WIDTH * style.FRAME_INSET_FRAC)
    frame_bottom = HEIGHT - frame_inset

    caption_font = text._role_font(style.TOP_TAG_FONT, weight)
    glyph_size = style.SOURCE_FAULT_GLYPH_PX
    gap = style.SPACE_XS

    bottom = frame_bottom - style.MARGIN // 2
    top = bottom - glyph_size
    mid_y = (top + bottom) // 2

    # Measure the caption at (0, mid_y) first purely to get its rendered
    # width - the real, final draw position (below) depends on that width
    # to stay horizontally centred.
    probe_bbox = draw.textbbox((0, mid_y), style.SOURCE_FAULT_TEXT, font=caption_font, anchor="lm")
    caption_w = probe_bbox[2] - probe_bbox[0]

    total_w = glyph_size + gap + caption_w
    left = (WIDTH - total_w) // 2
    text_left = left + glyph_size + gap

    triangle = [
        (left + glyph_size / 2, top),
        (left, bottom),
        (left + glyph_size, bottom),
    ]

    caption_bbox = draw.textbbox((text_left, mid_y), style.SOURCE_FAULT_TEXT, font=caption_font, anchor="lm")
    combined_bbox = (
        left,
        min(top, caption_bbox[1]),
        caption_bbox[2],
        max(bottom, caption_bbox[3]),
    )
    style._assert_within_canvas(combined_bbox, "source-fault badge")

    draw.polygon(triangle, outline=ink_idx)
    stroke_x = left + glyph_size / 2
    draw.line(
        [(stroke_x, top + glyph_size * 0.3), (stroke_x, top + glyph_size * 0.65)],
        fill=ink_idx, width=2,
    )
    # A zero-length ImageDraw.line() paints a single pixel regardless of
    # `width` - Pillow doesn't expand a degenerate segment - so the dot is
    # drawn as a small filled ellipse instead.
    dot_r = 2
    dot_y = top + glyph_size * 0.8
    draw.ellipse(
        [(stroke_x - dot_r, dot_y - dot_r), (stroke_x + dot_r, dot_y + dot_r)],
        fill=ink_idx,
    )
    draw.text((text_left, mid_y), style.SOURCE_FAULT_TEXT, font=caption_font, fill=ink_idx, anchor="lm")

    return combined_bbox


def draw_battery_icon(canvas, draw, ink_idx):
    """Bottom-left battery glyph: a hollow outlined body with a solid
    terminal nub and a left-aligned solid partial fill, signalling a
    fixed "low" reading, not a live gauge. Geometry derives entirely from
    the `style.BATTERY_ICON_*` constants. Box tuples are Pillow's
    inclusive corner coordinates (rendered footprint 52x23px for a
    nominal 51x22 box), matching `layout.draw_frame()`'s convention.

    Returns the icon's total bounding box - (64, 1514, 115, 1536).
    """
    body_top = style.BATTERY_ICON_BOTTOM - style.BATTERY_ICON_BODY_H
    body_right = style.BATTERY_ICON_LEFT + style.BATTERY_ICON_BODY_W
    body = (style.BATTERY_ICON_LEFT, body_top, body_right, style.BATTERY_ICON_BOTTOM)

    nub_top = body_top + (style.BATTERY_ICON_BODY_H - style.BATTERY_ICON_NUB_H) // 2
    nub_bottom = nub_top + style.BATTERY_ICON_NUB_H
    nub_right = body_right + style.BATTERY_ICON_NUB_W
    nub = (body_right, nub_top, nub_right, nub_bottom)

    interior_left = style.BATTERY_ICON_LEFT + style.BATTERY_ICON_STROKE_PX
    interior_top = body_top + style.BATTERY_ICON_STROKE_PX
    interior_right = body_right - style.BATTERY_ICON_STROKE_PX
    interior_bottom = style.BATTERY_ICON_BOTTOM - style.BATTERY_ICON_STROKE_PX
    fill_w = round((interior_right - interior_left) * style.BATTERY_ICON_FILL_FRAC)
    fill = (interior_left, interior_top, interior_left + fill_w, interior_bottom)

    total = (style.BATTERY_ICON_LEFT, body_top, nub_right, style.BATTERY_ICON_BOTTOM)
    # Looser canvas guard: this sits inside the 64px band, like the frame
    # and both illustrations.
    style._assert_within_canvas(total, "battery icon")

    draw.rectangle(body, outline=ink_idx, width=style.BATTERY_ICON_STROKE_PX)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)
    return total


# --- Display-off power glyph --------------------------------------------
# Drawn from primitives, no vendored asset. A power mark, not a moon or
# "Zzz" (QUIET HOURS' own register), in white ink with an 8px Bold-class
# stroke safe against the dither.
POWER_ICON_DIAMETER_PX = 76
POWER_ICON_STROKE_PX = 8
POWER_ICON_GAP_DEGREES = 64  # the ring's opening, centred on 12 o'clock
POWER_ICON_BAR_RISE_PX = 10  # how far the bar stands above the ring
POWER_ICON_BAR_DROP_PX = 34  # how far it reaches down into the ring


def draw_power_icon(draw, center_x, top_y, ink_idx):
    """Draw the power mark centred on `center_x`, topmost pixel at
    `top_y`; returns the glyph's total height. `ImageDraw.arc()`'s angles
    run clockwise from 3 o'clock (12 o'clock = 270); drawing the long way
    round from `270 + half_gap` to `270 - half_gap` leaves the opening at
    the top.
    """
    radius = POWER_ICON_DIAMETER_PX // 2
    ring_top = top_y + POWER_ICON_BAR_RISE_PX
    ring_box = (
        center_x - radius,
        ring_top,
        center_x + radius,
        ring_top + POWER_ICON_DIAMETER_PX,
    )
    half_gap = POWER_ICON_GAP_DEGREES / 2.0
    draw.arc(ring_box, 270 + half_gap, 270 - half_gap, fill=ink_idx, width=POWER_ICON_STROKE_PX)

    bar_left = center_x - POWER_ICON_STROKE_PX // 2
    draw.rectangle(
        (bar_left, top_y, bar_left + POWER_ICON_STROKE_PX - 1, ring_top + POWER_ICON_BAR_DROP_PX),
        fill=ink_idx,
    )
    return POWER_ICON_BAR_RISE_PX + POWER_ICON_DIAMETER_PX


# --- Quiet-hours crescent glyph ------------------------------------------
# Same 76px footprint and Bold-class white as the power ring, differing
# only by mark. Filled, not outlined: an outline's bite would paint a
# solid patch over the dithered field.
MOON_ICON_DIAMETER_PX = 76
MOON_ICON_BITE_DIAMETER_PX = 68
MOON_ICON_BITE_OFFSET_PX = 20  # the bite's centre, right of the disc's centre
MOON_ICON_SAMPLES = 180


def draw_moon_icon(draw, center_x, top_y, ink_idx):
    """Draw a filled crescent (points inside the main disc, outside the
    bite disc) centred on `center_x`, topmost pixel at `top_y`. Returns
    the glyph's height.
    """
    radius = MOON_ICON_DIAMETER_PX / 2.0
    bite_radius = MOON_ICON_BITE_DIAMETER_PX / 2.0
    cx = float(center_x)
    cy = top_y + radius
    bx = cx + MOON_ICON_BITE_OFFSET_PX

    outer = []
    for i in range(MOON_ICON_SAMPLES):
        a = 2.0 * math.pi * i / MOON_ICON_SAMPLES
        px, py = cx + radius * math.cos(a), cy + radius * math.sin(a)
        if math.hypot(px - bx, py - cy) >= bite_radius:
            outer.append((a, (px, py)))
    inner = []
    for i in range(MOON_ICON_SAMPLES):
        a = 2.0 * math.pi * i / MOON_ICON_SAMPLES
        px, py = bx + bite_radius * math.cos(a), cy + bite_radius * math.sin(a)
        if math.hypot(px - cx, py - cy) <= radius:
            inner.append((a, (px, py)))

    # Sampled angles straddle pi; unwrap so the run is contiguous.
    def _unwrap(run):
        run = sorted(run, key=lambda t: t[0])
        gap_at = max(range(1, len(run)), key=lambda k: run[k][0] - run[k - 1][0], default=0)
        if gap_at and run[gap_at][0] - run[gap_at - 1][0] > math.pi:
            run = run[gap_at:] + run[:gap_at]
        return [p for _a, p in run]

    points = _unwrap(outer) + list(reversed(_unwrap(inner)))
    draw.polygon(points, fill=ink_idx)
    return MOON_ICON_DIAMETER_PX


# --- Battery-empty glyph --------------------------------------------------
# Upright hollow battery, at the family's shared 76px height and the
# runway strip's 48px width. Stroke-only outline, hollow interior so the
# dithered field shows through - an empty battery has nothing inside to show.
EMPTY_BATTERY_ICON_HEIGHT_PX = 76
EMPTY_BATTERY_ICON_WIDTH_PX = 48
EMPTY_BATTERY_NUB_W_PX = 20
EMPTY_BATTERY_NUB_H_PX = 8
EMPTY_BATTERY_ICON_STROKE_PX = POWER_ICON_STROKE_PX  # same Bold-class 8px stroke as the ring


def draw_empty_battery_icon(draw, center_x, top_y, ink_idx):
    """Draw the battery-empty mark (solid terminal nub, then a
    stroke-only outlined body below it, hollow) centred on `center_x`,
    topmost pixel at `top_y`. Uses the inclusive-corner `right - 1` /
    `bottom - 1` convention so the rendered footprint matches the nominal
    width/height exactly (contrast `layout.draw_battery_icon()`'s
    one-pixel-wider convention). Returns the glyph's total height.
    """
    nub_left = center_x - EMPTY_BATTERY_NUB_W_PX // 2
    nub_right = nub_left + EMPTY_BATTERY_NUB_W_PX
    draw.rectangle((nub_left, top_y, nub_right - 1, top_y + EMPTY_BATTERY_NUB_H_PX - 1), fill=ink_idx)

    body_top = top_y + EMPTY_BATTERY_NUB_H_PX
    body_left = center_x - EMPTY_BATTERY_ICON_WIDTH_PX // 2
    body_right = body_left + EMPTY_BATTERY_ICON_WIDTH_PX
    body_bottom = top_y + EMPTY_BATTERY_ICON_HEIGHT_PX
    draw.rectangle(
        (body_left, body_top, body_right - 1, body_bottom - 1),
        outline=ink_idx,
        width=EMPTY_BATTERY_ICON_STROKE_PX,
    )
    return EMPTY_BATTERY_ICON_HEIGHT_PX


# --- No-connection alert glyph -------------------------------------------
# Same shape family as `layout.draw_source_fault_badge()`'s triangular
# alert mark, scaled to the 76px hold-glyph family; a sibling glyph, not a
# shared call. Stroke matches POWER_ICON_STROKE_PX - thin strokes drown
# in dither noise.
ALERT_ICON_HEIGHT_PX = 76
ALERT_ICON_WIDTH_PX = 88
ALERT_ICON_STROKE_PX = POWER_ICON_STROKE_PX


def draw_alert_icon(draw, center_x, top_y, ink_idx):
    """Draw the no-connection alert mark (outline triangle, exclamation
    stroke, and a filled-ellipse dot - not a zero-length line, which
    paints only a single pixel) centred on `center_x`, apex at `top_y`.
    Returns the glyph's total height.
    """
    half_w = ALERT_ICON_WIDTH_PX / 2.0
    apex = (center_x, top_y)
    base_left = (center_x - half_w, top_y + ALERT_ICON_HEIGHT_PX - 1)
    base_right = (center_x + half_w, top_y + ALERT_ICON_HEIGHT_PX - 1)
    draw.polygon([apex, base_left, base_right], outline=ink_idx, width=ALERT_ICON_STROKE_PX)

    stroke_top = top_y + ALERT_ICON_HEIGHT_PX * 0.35
    stroke_bottom = top_y + ALERT_ICON_HEIGHT_PX * 0.65
    draw.line([(center_x, stroke_top), (center_x, stroke_bottom)], fill=ink_idx, width=ALERT_ICON_STROKE_PX)

    dot_r = 5
    dot_y = top_y + ALERT_ICON_HEIGHT_PX * 0.8
    draw.ellipse(
        [(center_x - dot_r, dot_y - dot_r), (center_x + dot_r, dot_y + dot_r)],
        fill=ink_idx,
    )
    return ALERT_ICON_HEIGHT_PX


# --- Empty-state runway glyph ---------------------------------------------
# A runway seen from above: a strip with a dashed centreline and a
# threshold bar at each end. Same 76px height as the ring and crescent.
RUNWAY_ICON_HEIGHT_PX = 76
RUNWAY_ICON_WIDTH_PX = 48
RUNWAY_ICON_STROKE_PX = 4
RUNWAY_ICON_DASH_PX = 6
RUNWAY_ICON_DASH_GAP_PX = 5
RUNWAY_ICON_KEY_PX = 10  # the threshold "piano key" bars' height
RUNWAY_ICON_KEY_W_PX = 4  # ... and width; two per end, either side of the centreline


def draw_runway_icon(draw, center_x, top_y, ink_idx):
    """Draw the runway mark (threshold "piano keys" either side of a
    dashed centreline - a solid bar alone reads as a battery at glyph
    size) centred on `center_x`, top edge at `top_y`. Returns its height.
    """
    left = center_x - RUNWAY_ICON_WIDTH_PX // 2
    right = left + RUNWAY_ICON_WIDTH_PX
    bottom = top_y + RUNWAY_ICON_HEIGHT_PX
    s = RUNWAY_ICON_STROKE_PX
    draw.rectangle((left, top_y, right - 1, bottom - 1), outline=ink_idx, width=s)

    inner_top = top_y + s + 3
    inner_bottom = bottom - s - 3
    key_w = RUNWAY_ICON_KEY_W_PX
    key_h = RUNWAY_ICON_KEY_PX
    for kx in (center_x - 9 - key_w, center_x + 9):
        draw.rectangle((kx, inner_top, kx + key_w - 1, inner_top + key_h - 1), fill=ink_idx)
        draw.rectangle((kx, inner_bottom - key_h + 1, kx + key_w - 1, inner_bottom), fill=ink_idx)

    dash_w = 4
    span_top = inner_top + key_h + RUNWAY_ICON_DASH_GAP_PX
    span_bottom = inner_bottom - key_h - RUNWAY_ICON_DASH_GAP_PX
    step = RUNWAY_ICON_DASH_PX + RUNWAY_ICON_DASH_GAP_PX
    n = max(1, (span_bottom - span_top + 1 + RUNWAY_ICON_DASH_GAP_PX) // step)
    used = n * step - RUNWAY_ICON_DASH_GAP_PX
    y = span_top + (span_bottom - span_top + 1 - used) // 2
    for _ in range(n):
        draw.rectangle((center_x - dash_w // 2, y, center_x + dash_w // 2 - 1, y + RUNWAY_ICON_DASH_PX - 1), fill=ink_idx)
        y += step
    return RUNWAY_ICON_HEIGHT_PX
