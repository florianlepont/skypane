"""Fonts, text fitting, tracked (letter-spaced) text, and the main/
previous flight text blocks - plain layout and the diagonal-band variant
alike.

Cross-module calls into here (from `layout.py` and `hold_screens.py`) go
through this module's own attribute (`text._font(...)`,
`text.draw_main_text_block(...)`, ...), never a bare/`from`-imported
name - `server/test_render.py` rebinds several of these names for the
duration of one test, and a rebind only reaches call sites that look the
name up through this module.
"""
from PIL import ImageDraw, ImageFont

from server.panel_format import IDX_WHITE, WIDTH
from server.plane import enrich, runway_config
from server.plane.render import style

_font_cache = {}


def _font(spec):
    path, size, _weight = spec
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def fit_text_size(font_path, initial_size, text, max_width, min_size):
    """Largest ImageFont at `font_path` whose rendered `text` width fits
    `max_width`, stepping down from `initial_size`, floored at `min_size`.
    """
    size = initial_size
    while size > min_size:
        font = _font((font_path, size, None))
        if font.getlength(text) <= max_width:
            return font
        size -= style._FIT_STEP_PX
    return _font((font_path, min_size, None))


def _tracked_text_width(font, text, tracking):
    """Total rendered advance of `text` at `font`, with `tracking` extra
    pixels between each glyph pair (none trailing). 0.0 for an empty string.
    """
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked_text(draw, xy, text, font, fill, tracking=0):
    """Draw `text` glyph-by-glyph with `tracking` extra pixels of advance
    between each glyph (Pillow has no native letter-spacing API). `xy` is
    the top-left origin of the first glyph; right/centre-aligned callers
    should pre-compute width with `_tracked_text_width()`. Returns the
    x-coordinate after the last glyph.
    """
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="la")
        x += font.getlength(ch) + tracking
    return x


def _tracked_text_bbox(font, xy, text, tracking):
    """`draw.textbbox()`'s counterpart for tracked text: `ImageDraw.textbbox()`
    measures an untracked run and would under-report the width of a tracked
    one, so `style._assert_within_canvas()` must be fed this instead.
    """
    x, y = xy
    width = _tracked_text_width(font, text, tracking)
    ascent, descent = font.getmetrics()
    return (x, y, x + width, y + ascent + descent)


def _role_weight_path(weight):
    """Resolve `weight` ("regular" or "bold") to the matching PT Serif
    static-weight file. Not derivable from `bg_idx` alone: the same
    palette index can back two themes with different weights (e.g.
    `IDX_BLACK` is both flat "black"/Regular and dithered "grey"/Bold).
    """
    if weight == "regular":
        return style.PT_SERIF_REGULAR
    if weight == "bold":
        return style.PT_SERIF_BOLD
    raise ValueError("unknown weight %r (expected 'regular' or 'bold')" % (weight,))


def _role_font(role_spec, weight):
    """`_font()` for an active-state role tuple, resolving weight via
    `_role_weight_path()` instead of the tuple's own (always-Bold) path.
    """
    _path, size, role_weight = role_spec
    return _font((_role_weight_path(weight), size, role_weight))


def _role_fit_text_size(role_spec, text, max_width, min_size, weight):
    """`fit_text_size()` for an active-state role tuple, resolving weight
    the same way `_role_font()` does.
    """
    _path, size, _role_weight = role_spec
    return fit_text_size(_role_weight_path(weight), size, text, max_width, min_size)


def _wrap_text(font, text, max_width):
    """Manual word-wrap (Pillow's multiline_text does not word-wrap):
    greedily pack words onto a line while the rendered width fits
    `max_width`.
    """
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if not current or font.getlength(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _flight_line1_text(flight, state, route):
    """Four-tier content ladder for the main line, evaluated in order:

    - **Tier 1**: identifier + city known -> `"{identifier} to|from {city}"`.
    - **Tier 2**: city only -> `"To|From {city}"` (TITLE-case, starts the line).
    - **Tier 3**: airline known, no city/identifier -> `""` (line 1
      omitted; callers must promote line 2 into its slot).
    - **Tier 4**: nothing usable -> `"Unknown flight"`.

    The raw ADS-B callsign is never reachable at any tier. Never raises;
    a malformed `route` or a hostile `route.get()` degrades a tier
    rather than propagating.
    """
    fallback_word = "Unknown flight"
    if not isinstance(route, dict):
        return fallback_word

    try:
        identifier_raw = route.get("callsign_iata")
    except Exception:
        identifier_raw = None
    identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

    try:
        city = enrich.city_for_state(route, state)
    except Exception:
        city = None
    if not isinstance(city, str) or not city.strip():
        city = None

    if identifier and city:
        direction_lower = "to" if state == runway_config.STATE_DEPARTING else "from"
        return "%s %s %s" % (identifier, direction_lower, city)
    if city:
        direction_title = "To" if state == runway_config.STATE_DEPARTING else "From"
        return "%s %s" % (direction_title, city)

    try:
        airline_name = route.get("airline_name")
    except Exception:
        airline_name = None
    if isinstance(airline_name, str) and airline_name.strip():
        return ""

    return fallback_word


# Friendly labels for ICAO type designators, so `{airline} · {type}` shows
# a legible label rather than a raw code. A designator absent here
# renders the airline name alone (_flight_line2_text()'s fallback).
_TYPE_DISPLAY_LABELS = {
    # A320 family - familiar designations, neo variants named.
    "A318": "A318", "A319": "A319", "A320": "A320", "A321": "A321",
    "A20N": "A320neo", "A21N": "A321neo",
    # B737 family - commercial model numbers, MAX variants named.
    "B731": "737-100", "B732": "737-200", "B733": "737-300", "B734": "737-400",
    "B735": "737-500", "B736": "737-600", "B737": "737-700", "B738": "737-800",
    "B739": "737-900", "B37M": "737 MAX 7", "B38M": "737 MAX 8",
    "B39M": "737 MAX 9", "B3XM": "737 MAX 10",
    # ATR turboprops.
    "AT43": "ATR 42", "AT44": "ATR 42-500", "AT45": "ATR 42", "AT46": "ATR 42-600",
    "AT72": "ATR 72", "AT73": "ATR 72", "AT75": "ATR 72-500", "AT76": "ATR 72-600",
    # Beechcraft 1900D.
    "BE9L": "Beechcraft 1900D",
    # Embraer E-Jet family - keep the E1xx designations.
    "E135": "E135", "E145": "E145", "E170": "E170", "E75L": "E175",
    "E75S": "E175", "E190": "E190", "E195": "E195", "E290": "E190-E2",
    "E295": "E195-E2",
    # A330 family.
    "A332": "A330-200", "A333": "A330-300", "A339": "A330-900neo",
    # A350 family.
    "A359": "A350-900", "A35K": "A350-1000",
}

# Presentation-only display alias. `enrich.correct_airline_name()` now
# corrects this carrier's name upstream, so this is a defensive no-op for
# any hand-built route dict that still carries the literal stale name.
_AIRLINE_DISPLAY_ALIASES = {
    "CCM Airlines": "Air Corsica",
}


def display_airline_name(airline_name):
    """Presentation-only display name: the aliased brand name when one
    exists, else `airline_name` unchanged. Never raises.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return airline_name
    return _AIRLINE_DISPLAY_ALIASES.get(airline_name, airline_name)


def _flight_line2_text(route, aircraft_type=None):
    """`"{airline} · {friendly type label}"`, via `display_airline_name()`
    and `_TYPE_DISPLAY_LABELS`. Falls back to the display name alone when
    `aircraft_type` has no friendly label, and to `style.ROUTE_FALLBACK_TEXT`
    only when neither adsbdb nor the callsign-prefix fallback produced an
    airline name. Never raises.
    """
    try:
        airline_name = route.get("airline_name") if isinstance(route, dict) else None
    except Exception:
        airline_name = None
    if not airline_name:
        return style.ROUTE_FALLBACK_TEXT
    display_name = display_airline_name(airline_name)
    type_key = aircraft_type.strip().upper() if isinstance(aircraft_type, str) and aircraft_type else None
    label = _TYPE_DISPLAY_LABELS.get(type_key) if type_key else None
    if label:
        return "%s · %s" % (display_name, label)
    return "%s" % (display_name,)


# --- Band-only main-card text roles ---------------------------------
# Declared weight ("700"/"400" in the tuple) is never read directly -
# `_role_font()` resolves the real weight from the active theme's `weight`
# field, same mechanism every other active-state role already uses.
BAND_MAIN_NUMBER_FONT = (style.PT_SERIF_BOLD, 56, 700)
BAND_MAIN_ROUTE_FONT = (style.PT_SERIF_REGULAR, 22, 400)
BAND_MAIN_AIRLINE_FONT = (style.PT_SERIF_REGULAR, 20, 400)
BAND_MAIN_DASH_W = 48
BAND_MAIN_DASH_GAP = 10

# Shrink-to-fit floors, roughly the same ~70% ratio MAIN_LINE1_FONT/
# MAIN_LINE2_FONT use, so a long airline/city name never overflows.
BAND_MAIN_NUMBER_MIN_SIZE = 40
BAND_MAIN_ROUTE_MIN_SIZE = 16
BAND_MAIN_AIRLINE_MIN_SIZE = 14


def _role_fit_tracked_text_size(role_spec, text, tracking, max_width, min_size, weight):
    """`_role_fit_text_size()`'s step-down loop, measuring width via
    `_tracked_text_width()` instead of `font.getlength()`, since tracking
    adds pixels `fit_text_size()` alone would miss.
    """
    font_path, size, _role_weight = role_spec
    resolved_path = _role_weight_path(weight)
    while size > min_size:
        font = _font((resolved_path, size, None))
        if _tracked_text_width(font, text, tracking) <= max_width:
            return font
        size -= style._FIT_STEP_PX
    return _font((resolved_path, min_size, None))


def draw_main_text_block(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight, band_idx=None):
    """Main flight text: two centred lines starting `style.MAIN_TEXT_GAP_PX`
    below the illustration's OPAQUE bottom edge (`.content`, not `.rect`,
    which would vary the gap by 37-174px per file's own padding).

    When line 1 is empty, line 2 is promoted into its slot and the first
    return slot is `None`. `weight` selects PT Serif weight (not
    derivable from `bg_idx` alone; see `_role_weight_path()`). `band_idx`
    `None` draws the plain layout; a band theme instead draws a
    three-tier hierarchy (identifier / dash rule / route line /
    airline·type line) centred inside the band.

    Returns (line1_bbox, line2_bbox).
    """
    if band_idx is None:
        draw = ImageDraw.Draw(canvas)
        center_x = WIDTH // 2
        safe_width = style.SAFE_BOX[2] - style.SAFE_BOX[0]

        line1_text = _flight_line1_text(flight, state, route)
        line2_text = _flight_line2_text(route, flight.get("aircraft_type"))

        top_y = main_placement.content[3] + style.MAIN_TEXT_GAP_PX

        if line1_text:
            line1_font = _role_fit_text_size(style.MAIN_LINE1_FONT, line1_text, safe_width, style.MAIN_LINE1_MIN_SIZE, weight)
            line1_bbox = draw.textbbox((center_x, top_y), line1_text, font=line1_font, anchor="ma")
            style._assert_within_canvas(line1_bbox, "main flight text line 1")
            draw.text((center_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ma")
            line2_top = line1_bbox[3] + style.MAIN_LINE_GAP_PX
        else:
            line1_bbox = None
            line2_top = top_y

        line2_font = _role_fit_text_size(style.MAIN_LINE2_FONT, line2_text, safe_width, style.MAIN_LINE2_MIN_SIZE, weight)
        line2_bbox = draw.textbbox((center_x, line2_top), line2_text, font=line2_font, anchor="ma")
        style._assert_within_canvas(line2_bbox, "main flight text line 2")
        draw.text((center_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ma")

        return line1_bbox, line2_bbox
    else:
        draw = ImageDraw.Draw(canvas)
        # White-ink override: unconditional for every band theme, since
        # black is illegible on real Spectra 6 ink regardless of band colour.
        effective_ink = IDX_WHITE

        line1_full = _flight_line1_text(flight, state, route)
        line2_full = _flight_line2_text(route, flight.get("aircraft_type"))

        identifier_raw = route.get("callsign_iata") if isinstance(route, dict) else None
        identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

        # Classify from the real content ladder's own output, never a
        # separate re-derivation.
        if line1_full == "":
            number_text, tracked_text, plain_text = None, None, line2_full
        elif identifier and line1_full.startswith(identifier + " "):
            number_text = identifier
            tracked_text = line1_full[len(identifier) + 1:].upper()
            plain_text = line2_full
        else:
            number_text, tracked_text, plain_text = None, line1_full.upper(), line2_full

        # First-pass fonts, fit against SAFE_BOX's width to get an
        # approximate block height for the midpoint calc below only.
        band_safe_width = style.SAFE_BOX[2] - style.SAFE_BOX[0]
        num_font = _role_fit_text_size(BAND_MAIN_NUMBER_FONT, number_text or "", band_safe_width, BAND_MAIN_NUMBER_MIN_SIZE, weight)
        route_font = _role_fit_tracked_text_size(BAND_MAIN_ROUTE_FONT, tracked_text or "", style.LABEL_TRACKING_PX, band_safe_width, BAND_MAIN_ROUTE_MIN_SIZE, weight)
        airline_font = _role_fit_text_size(BAND_MAIN_AIRLINE_FONT, plain_text, band_safe_width, BAND_MAIN_AIRLINE_MIN_SIZE, weight)

        # center_x is computed ONCE at the block's MIDPOINT and reused for
        # every line (see style._band_center_x()) - anchoring at the block's
        # TOP instead would leave lower lines visibly off-centre, since the
        # band's centreline drifts left as y increases.
        y = main_placement.content[3] + style.MAIN_TEXT_GAP_PX
        measure_y = y
        if number_text:
            num_bbox_m = draw.textbbox((0, measure_y), number_text, font=num_font, anchor="ma")
            dash_y_m = num_bbox_m[3] + BAND_MAIN_DASH_GAP
            measure_y = dash_y_m + BAND_MAIN_DASH_GAP + 4
        if tracked_text:
            tracked_bbox_m = _tracked_text_bbox(route_font, (0, measure_y), tracked_text, style.LABEL_TRACKING_PX)
            measure_y = tracked_bbox_m[3] + 12
        plain_bbox_m = draw.textbbox((0, measure_y), plain_text, font=airline_font, anchor="ma")
        block_bottom_y = plain_bbox_m[3]
        center_x = style._band_center_x((y + block_bottom_y) / 2, WIDTH)
        first_bbox = None

        # Re-fit each line against the band's own width at its actual y
        # (not SAFE_BOX's width): white ink is only visible ON the band,
        # so an overhang lands on White and silently vanishes.
        if number_text:
            band_left, band_right = style._band_edges(y, WIDTH)
            num_max_w = 2 * min(center_x - band_left, band_right - center_x)
            num_font = _role_fit_text_size(BAND_MAIN_NUMBER_FONT, number_text, num_max_w, BAND_MAIN_NUMBER_MIN_SIZE, weight)
            num_bbox = draw.textbbox((center_x, y), number_text, font=num_font, anchor="ma")
            style._assert_within_canvas(num_bbox, "band main flight number")
            draw.text((center_x, y), number_text, font=num_font, fill=effective_ink, anchor="ma")
            first_bbox = num_bbox
            dash_y = num_bbox[3] + BAND_MAIN_DASH_GAP
            draw.line(
                [(center_x - BAND_MAIN_DASH_W / 2, dash_y), (center_x + BAND_MAIN_DASH_W / 2, dash_y)],
                fill=effective_ink, width=2,
            )
            y = dash_y + BAND_MAIN_DASH_GAP + 4

        if tracked_text:
            band_left, band_right = style._band_edges(y, WIDTH)
            tracked_max_w = 2 * min(center_x - band_left, band_right - center_x)
            route_font = _role_fit_tracked_text_size(
                BAND_MAIN_ROUTE_FONT, tracked_text, style.LABEL_TRACKING_PX, tracked_max_w, BAND_MAIN_ROUTE_MIN_SIZE, weight
            )
            tracked_w = _tracked_text_width(route_font, tracked_text, style.LABEL_TRACKING_PX)
            tracked_x = center_x - tracked_w / 2
            tracked_bbox = _tracked_text_bbox(route_font, (tracked_x, y), tracked_text, style.LABEL_TRACKING_PX)
            style._assert_within_canvas(tracked_bbox, "band main flight tracked route line")
            draw_tracked_text(draw, (tracked_x, y), tracked_text, route_font, effective_ink, tracking=style.LABEL_TRACKING_PX)
            if first_bbox is None:
                first_bbox = tracked_bbox
            y = tracked_bbox[3] + 12

        band_left, band_right = style._band_edges(y, WIDTH)
        airline_max_w = 2 * min(center_x - band_left, band_right - center_x)
        airline_font = _role_fit_text_size(BAND_MAIN_AIRLINE_FONT, plain_text, airline_max_w, BAND_MAIN_AIRLINE_MIN_SIZE, weight)
        plain_bbox = draw.textbbox((center_x, y), plain_text, font=airline_font, anchor="ma")
        style._assert_within_canvas(plain_bbox, "band main flight airline·type line")
        draw.text((center_x, y), plain_text, font=airline_font, fill=effective_ink, anchor="ma")
        if first_bbox is None:
            first_bbox = plain_bbox

        return first_bbox, plain_bbox


# --- Band-only previous-card text roles ---------------------------------
# The same right-aligned three-tier hierarchy as the main card, at the
# previous card's existing ~57% scale.
BAND_PREV_NUMBER_FONT = (style.PT_SERIF_BOLD, 32, 700)
BAND_PREV_ROUTE_FONT = (style.PT_SERIF_REGULAR, 16, 400)
BAND_PREV_AIRLINE_FONT = (style.PT_SERIF_REGULAR, 14, 400)
BAND_PREV_DASH_W = 16
BAND_PREV_DASH_GAP = 6

# Same real-glass long-name finding as BAND_MAIN_*_MIN_SIZE above - the
# previous card's band roles were equally fixed-size with no
# shrink-to-fit.
BAND_PREV_NUMBER_MIN_SIZE = 23
BAND_PREV_ROUTE_MIN_SIZE = 12
BAND_PREV_AIRLINE_MIN_SIZE = 10


def draw_previous_text_block(canvas, flight, state, route, prev_placement, ink_idx, bg_idx, weight, band_idx=None):
    """Previous flight text: two right-aligned lines, positioned from
    `prev_placement.content` (not `.rect`) like `draw_main_text_block()`.
    Right edge is `.content[2]` minus `style.PREVIOUS_TEXT_LEFT_OFFSET_PX`,
    so the main/previous aircraft and this text share one reference line.
    Line 2 sits below line 1's TOP, not bottom; when line 1 is empty,
    line 2 is promoted and the first return slot is `None`.

    `band_idx` `None` draws the plain layout; a band theme draws a
    right-aligned hierarchy in the caller's plain `ink_idx` (no ink
    override here, unlike the main card).

    Returns (line1_bbox, line2_bbox).
    """
    if band_idx is None:
        draw = ImageDraw.Draw(canvas)
        right_x = prev_placement.content[2] - style.PREVIOUS_TEXT_LEFT_OFFSET_PX
        available_width = right_x - style.SAFE_BOX[0]

        line1_text = _flight_line1_text(flight, state, route)
        line2_text = _flight_line2_text(route, (flight or {}).get("aircraft_type"))

        top_y = prev_placement.content[3] + style.PREVIOUS_TEXT_GAP_PX

        if line1_text:
            line1_font = _role_fit_text_size(style.PREVIOUS_LINE1_FONT, line1_text, available_width, style.PREVIOUS_LINE1_MIN_SIZE, weight)
            line1_bbox = draw.textbbox((right_x, top_y), line1_text, font=line1_font, anchor="ra")
            style._assert_within_canvas(line1_bbox, "previous flight text line 1")
            draw.text((right_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ra")
            line2_top = line1_bbox[1] + style.PREVIOUS_LINE_GAP_PX
        else:
            line1_bbox = None
            line2_top = top_y

        line2_font = _role_fit_text_size(style.PREVIOUS_LINE2_FONT, line2_text, available_width, style.PREVIOUS_LINE2_MIN_SIZE, weight)
        line2_bbox = draw.textbbox((right_x, line2_top), line2_text, font=line2_font, anchor="ra")
        style._assert_within_canvas(line2_bbox, "previous flight text line 2")
        draw.text((right_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ra")

        return line1_bbox, line2_bbox
    else:
        draw = ImageDraw.Draw(canvas)
        right_x = prev_placement.content[2] - style.PREVIOUS_TEXT_LEFT_OFFSET_PX

        line1_full = _flight_line1_text(flight, state, route)
        line2_full = _flight_line2_text(route, (flight or {}).get("aircraft_type"))

        identifier_raw = route.get("callsign_iata") if isinstance(route, dict) else None
        identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

        if line1_full == "":
            number_text, tracked_text, plain_text = None, None, line2_full
        elif identifier and line1_full.startswith(identifier + " "):
            number_text = identifier
            tracked_text = line1_full[len(identifier) + 1:].upper()
            plain_text = line2_full
        else:
            number_text, tracked_text, plain_text = None, line1_full.upper(), line2_full

        band_available_width = right_x - style.SAFE_BOX[0]
        num_font = _role_fit_text_size(BAND_PREV_NUMBER_FONT, number_text or "", band_available_width, BAND_PREV_NUMBER_MIN_SIZE, weight)
        route_font = _role_fit_tracked_text_size(BAND_PREV_ROUTE_FONT, tracked_text or "", style.LABEL_TRACKING_PX, band_available_width, BAND_PREV_ROUTE_MIN_SIZE, weight)
        airline_font = _role_fit_text_size(BAND_PREV_AIRLINE_FONT, plain_text, band_available_width, BAND_PREV_AIRLINE_MIN_SIZE, weight)

        y = prev_placement.content[3] + style.PREVIOUS_TEXT_GAP_PX
        first_bbox = None

        if number_text:
            num_bbox = draw.textbbox((right_x, y), number_text, font=num_font, anchor="ra")
            style._assert_within_canvas(num_bbox, "band previous flight number")
            draw.text((right_x, y), number_text, font=num_font, fill=ink_idx, anchor="ra")
            first_bbox = num_bbox
            dash_y = num_bbox[3] + BAND_PREV_DASH_GAP
            draw.line([(right_x - BAND_PREV_DASH_W, dash_y), (right_x, dash_y)], fill=ink_idx, width=2)
            y = dash_y + BAND_PREV_DASH_GAP + 3

        if tracked_text:
            tracked_w = _tracked_text_width(route_font, tracked_text, style.LABEL_TRACKING_PX)
            tracked_x = right_x - tracked_w
            tracked_bbox = _tracked_text_bbox(route_font, (tracked_x, y), tracked_text, style.LABEL_TRACKING_PX)
            style._assert_within_canvas(tracked_bbox, "band previous flight tracked route line")
            draw_tracked_text(draw, (tracked_x, y), tracked_text, route_font, ink_idx, tracking=style.LABEL_TRACKING_PX)
            if first_bbox is None:
                first_bbox = tracked_bbox
            y = tracked_bbox[3] + 8

        plain_bbox = draw.textbbox((right_x, y), plain_text, font=airline_font, anchor="ra")
        style._assert_within_canvas(plain_bbox, "band previous flight airline·type line")
        draw.text((right_x, y), plain_text, font=airline_font, fill=ink_idx, anchor="ra")
        if first_bbox is None:
            first_bbox = plain_bbox

        return first_bbox, plain_bbox
