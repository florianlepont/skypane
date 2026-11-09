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

from PIL import Image

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

# Defaults for the halved placement, as fractions of the canvas: opaque width
# of the whole aircraft the nose half is cut from, the same for the rear half,
# the vertical centre of the nose half and the bottom edge of the rear half.
NOSE_PLANE_WIDTH_FRAC = 2200 / 1200
REAR_PLANE_WIDTH_FRAC = 1250 / 1200
NOSE_CENTER_Y_FRAC = 470 / 1600
REAR_BOTTOM_Y_FRAC = 1275 / 1600

# White halo around the aircraft: its radius as a share of canvas width.
HALO_RADIUS_FRAC = 0.00625

# Width the illustration is loaded at when only its shape is being measured.
_MEASURE_WIDTH_PX = 800

_cut_cache = {}
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
    means = alpha.resize((groups, 1), Image.BOX).tobytes()
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
