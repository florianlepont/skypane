"""Aircraft handling for the giant-lettering layouts.

Pure geometry (crop point, paste rectangles) is kept apart from painting.
Geometry is expressed as fractions of the canvas, so portrait and landscape
frames share the same code.

Illustrations are drawn nose-left. The "halved" placement shows the nose
entering from the right edge and the rear half entering from the left edge;
the cut columns sit outside the visible canvas so the aircraft looks as if it
continues beyond the frame.
"""
import os
import statistics

from PIL import Image, ImageFilter

from server.panel_format import IDX_WHITE
from server.plane.render import layout

# The cut is searched inside this share of the opaque aircraft width.
CUT_SEARCH_MIN = 0.40
CUT_SEARCH_MAX = 0.70
CUT_FALLBACK = 0.5

# Columns whose smoothed height is within this factor of the lowest one are
# equally good cut candidates; the one nearest the middle wins so the two
# halves stay balanced.
CUT_PLATEAU_TOLERANCE = 1.05

# Cut-search resolution: columns are averaged in groups of this many pixels,
# and smoothed over this share of the width on each side.
_COLUMN_GROUP_PX = 4
_SMOOTH_HALF_WIDTH_FRAC = 0.01

# Distance the cut columns sit beyond the canvas edge, as a share of canvas
# width.
OVERSHOOT_FRAC = 0.025

# Defaults for the halved placement (portrait), as fractions of the canvas
# width: the painted width of the whole aircraft behind the nose half and
# behind the rear half. The nose half is then anchored by its left (cockpit)
# end and the rear half by its right (tail) end, both as fractions of the
# canvas width, and placed vertically by the vertical centre of the nose half
# and the bottom edge of the rear half, as fractions of the canvas height.
NOSE_PLANE_WIDTH_FRAC = 2200 / 1200
REAR_PLANE_WIDTH_FRAC = 1250 / 1200
NOSE_LEFT_X_FRAC = 130 / 1200
REAR_RIGHT_X_FRAC = 595 / 1200
NOSE_CENTER_Y_FRAC = 470 / 1600
REAR_BOTTOM_Y_FRAC = 1275 / 1600

# White halo around the aircraft: its radius as a share of canvas width.
HALO_RADIUS_FRAC = 0.00625

# Width the illustration is loaded at when only its shape is being measured.
_MEASURE_WIDTH_PX = 800

_cut_cache: dict = {}
_CUT_CACHE_MAX_ENTRIES = 256


def opaque_content(rgba):
    """`rgba` cropped to the pixels the paste would draw (alpha above the
    shared threshold), or `rgba` itself when nothing would be drawn."""
    bbox = layout._opaque_bbox(rgba)
    return rgba.crop(bbox) if bbox else rgba


def column_heights(rgba):
    """Opaque pixels per column of `rgba`, using the paste threshold."""
    alpha = layout._threshold_alpha(rgba)
    width, height = alpha.size
    groups = max(1, width // _COLUMN_GROUP_PX)
    means = alpha.resize((groups, 1), Image.Resampling.BOX).tobytes()
    return [value * height / 255 for value in means]


def fuselage_median(rgba):
    """Median non-empty column height: a stand-in for the fuselage depth."""
    heights = [h for h in column_heights(rgba) if h > 0]
    return statistics.median(heights) if heights else 0.0


def _smoothed(heights):
    radius = max(1, round(len(heights) * _SMOOTH_HALF_WIDTH_FRAC))
    out = []
    for i in range(len(heights)):
        window = heights[max(0, i - radius) : i + radius + 1]
        out.append(sum(window) / len(window))
    return out


def cut_fraction(rgba):
    """Fraction of the opaque width at which to cut the aircraft in two.

    Searches the middle of the aircraft for its thinnest stretch so the cut
    goes through bare fuselage rather than a wing or an engine. Falls back to
    `CUT_FALLBACK` when the image is empty or too narrow to measure.
    """
    content = opaque_content(rgba)
    heights = column_heights(content)
    count = len(heights)
    low, high = int(CUT_SEARCH_MIN * count), int(CUT_SEARCH_MAX * count)
    if count < 8 or high <= low or content.size[0] == 0:
        return CUT_FALLBACK
    smooth = _smoothed(heights)
    thinnest = min(smooth[low : high + 1])
    if thinnest <= 0:
        return CUT_FALLBACK
    limit = thinnest * CUT_PLATEAU_TOLERANCE
    candidates = [i for i in range(low, high + 1) if smooth[i] <= limit]
    best = min(candidates, key=lambda i: (abs(i / count - CUT_FALLBACK), i))
    return best / count


def cut_fraction_for_path(path):
    """`cut_fraction` of the illustration at `path`, memoized on the file's
    identity. Goes through the render family's safe loader, so oversize or
    unreadable art degrades the same way it does everywhere else; returns
    `CUT_FALLBACK` when nothing can be loaded."""
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
    except (OSError, TypeError):
        key = None
    if key is not None and key in _cut_cache:
        return _cut_cache[key]
    loaded = layout._load_illustration_safely(path, _MEASURE_WIDTH_PX)
    value = CUT_FALLBACK if loaded is None else cut_fraction(loaded)
    if key is not None:
        if len(_cut_cache) >= _CUT_CACHE_MAX_ENTRIES:
            _cut_cache.clear()
        _cut_cache[key] = value
    return value


def split_halves(rgba, fraction):
    """(nose, rear) pieces of `rgba` cut at `fraction` of its opaque width,
    each cropped to its own painted pixels."""
    content = opaque_content(rgba)
    width, height = content.size
    cut = min(max(round(width * fraction), 1), max(width - 1, 1))
    return (
        opaque_content(content.crop((0, 0, cut, height))),
        opaque_content(content.crop((cut, 0, width, height))),
    )


def overshoot_px(canvas_size):
    """How far past the canvas edge the cut columns sit at least."""
    return round(canvas_size[0] * OVERSHOOT_FRAC)


def nose_cut(canvas_size, cut, plane_frac=NOSE_PLANE_WIDTH_FRAC, left_frac=NOSE_LEFT_X_FRAC):
    """`cut` raised, if needed, so the nose half anchored at `left_frac` of the
    canvas width still reaches past the right edge."""
    width = canvas_size[0]
    needed = (width - round(left_frac * width) + overshoot_px(canvas_size) + 1) / (plane_frac * width)
    return min(max(cut, needed), 0.99)


def rear_cut(canvas_size, cut, plane_frac=REAR_PLANE_WIDTH_FRAC, right_frac=REAR_RIGHT_X_FRAC):
    """`cut` lowered, if needed, so the rear half ending at `right_frac` of the
    canvas width still reaches past the left edge."""
    width = canvas_size[0]
    needed = 1 - (round(right_frac * width) + overshoot_px(canvas_size) + 1) / (plane_frac * width)
    return max(min(cut, needed), 0.01)


def nose_half(canvas_size, nose_size, center_y_frac=NOSE_CENTER_Y_FRAC, left_frac=NOSE_LEFT_X_FRAC):
    """Paste rectangle `(left, top, right, bottom)` of the nose half: its
    cockpit end at `left_frac` of the width, its cut (right-hand) column
    beyond the canvas."""
    width, height = canvas_size
    nose_w, nose_h = nose_size
    left = round(left_frac * width)
    top = round(center_y_frac * height) - nose_h // 2
    return (left, top, left + nose_w, top + nose_h)


def rear_half(canvas_size, rear_size, bottom_y_frac=REAR_BOTTOM_Y_FRAC, right_frac=REAR_RIGHT_X_FRAC):
    """Paste rectangle of the rear half: its tail end at `right_frac` of the
    width, its cut (left-hand) column beyond the canvas."""
    width, height = canvas_size
    rear_w, rear_h = rear_size
    right = round(right_frac * width)
    top = round(bottom_y_frac * height) - rear_h
    return (right - rear_w, top, right, top + rear_h)


def whole_aircraft(box, size):
    """Size and rectangle of a whole aircraft of `size` fitted, centred,
    inside `box` `(left, top, right, bottom)` keeping its aspect ratio.
    Returns `((width, height), (left, top, right, bottom))`."""
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    width, height = size
    scale = min(box_w / width, box_h / height)
    new_w, new_h = max(1, round(width * scale)), max(1, round(height * scale))
    left = box[0] + (box_w - new_w) // 2
    top = box[1] + (box_h - new_h) // 2
    return (new_w, new_h), (left, top, left + new_w, top + new_h)


def halo_radius(canvas_size):
    """Halo radius in pixels for a canvas of `canvas_size`."""
    return max(1, round(canvas_size[0] * HALO_RADIUS_FRAC))


def _padded(rgba, margin):
    out = Image.new("RGBA", (rgba.size[0] + 2 * margin, rgba.size[1] + 2 * margin), (0, 0, 0, 0))
    out.paste(rgba, (margin, margin))
    return out


def paint_aircraft(canvas, rgba, left, top, halo):
    """Paint `rgba` with its top-left at `(left, top)`, over a white halo
    `halo` pixels wide. Halo and body masks are both hard-thresholded, so the
    canvas only ever receives palette indices. Offsets may be negative or
    reach past the canvas; the overhang is clipped."""
    padded = _padded(rgba, halo)
    mask = layout._threshold_alpha(padded)
    grown = mask.filter(ImageFilter.MaxFilter(2 * halo + 1)).point(lambda p: 255 if p > 127 else 0)
    canvas.paste(IDX_WHITE, (int(left) - halo, int(top) - halo), grown)
    layout.draw_illustration(canvas, padded, left - halo, top - halo)


def load_content(path, content_width):
    """The illustration at `path` as RGBA cropped to its painted pixels and
    scaled so those pixels are `content_width` wide; `None` when nothing can
    be loaded."""
    probe = layout._load_illustration_safely(path, content_width)
    if probe is None:
        return None
    bbox = layout._opaque_bbox(probe)
    if not bbox or bbox[2] - bbox[0] == content_width:
        return opaque_content(probe)
    target = max(1, round(content_width * probe.size[0] / (bbox[2] - bbox[0])))
    resized = layout._load_illustration_safely(path, target)
    return opaque_content(resized) if resized is not None else opaque_content(probe)
