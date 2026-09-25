"""companion/draw.py: the shared SVG geometry and emission primitives for
every drawing the SkyPane companion service renders.

stdlib-only; never imports companion/layout.py, a page module, or the
server package, so a drawing never depends on the shell it renders inside.
Every SVG is server-rendered in full (no-JS floor). Two coordinate schemes
live here, `percent_*` and `unit_*` (see each family's own docstring), and
must never be mixed inside one drawing. Every value interpolated into
emitted markup goes through `escape()`, without exception.
"""
import html
import math

# --- the shared class vocabulary --------------------------------------
# Every emittable class is a named constant; DRAWING_CLASSES below collects
# them so a harness can assert each resolves to a real selector in
# companion/static/style.css. Paint is currentColor plus a theme token, so
# a drawing is correct in both themes with no second rule.

# The grid wrapper that puts a time series' labels OUTSIDE the canvas:
# an auto-sized label column beside a minmax(0, 1fr) canvas column.
DRAWING_GRID_CLASS = "drawing"
DRAWING_Y_LABELS_CLASS = "drawing__y"
DRAWING_X_LABELS_CLASS = "drawing__x"

# The canvas itself. Carrying this class is the percentage scheme's size
# route: an <svg> with neither a size attribute nor a CSS rule renders at
# the SVG default 300x150. The unit scheme takes the other route —
# intrinsic width/height attributes, emitted by unit_canvas() below.
DRAWING_CANVAS_CLASS = "drawing__canvas"

# The unit scheme's own canvas class, separate from the one above:
# .drawing__canvas declares a width and height, which would override a
# unit canvas's intrinsic attributes and letterbox the aspect-locked shape
# inside a stretched box.
DRAWING_FIGURE_CLASS = "drawing__figure"

# Structural ink: axis lines and ticks, drawn as filled rects.
DRAWING_AXIS_CLASS = "drawing-axis"
# A stroked path or line segment; its rule declares `fill: none`.
DRAWING_LINE_CLASS = "drawing-line"
# A filled mark: a data point, a tick, a grid cell.
DRAWING_MARK_CLASS = "drawing-mark"
# An HTML label sitting outside the canvas in the grid above.
DRAWING_AXIS_LABEL_CLASS = "drawing-axis-label"

# The day band's three shapes: three classes, not one with modifiers,
# because each takes colour from a different place — the frame is the day
# itself (faint structural ink), the shaded span is a configured window
# (solid structural ink), and a mark is a thing that happened
# (currentColor).
DRAWING_BAND_CLASS = "drawing-band"
DRAWING_BAND_SPAN_CLASS = "drawing-band-span"
DRAWING_BAND_MARK_CLASS = "drawing-band-mark"

# The ring gauge's two arcs: two classes, not one with a modifier, since
# they take colour from different places — the track is structural ink
# (--color-border) and the value arc is currentColor, so the status
# modifier below reaches only the value.
DRAWING_RING_TRACK_CLASS = "drawing-ring-track"
DRAWING_RING_VALUE_CLASS = "drawing-ring-value"

# The check-in regularity grid's cells: a base class plus four state
# modifiers — the fourth ("no observation") is a different kind of
# statement from the three verdicts. The modifiers set `color` only, so
# the same four classes paint an SVG cell and an HTML legend swatch.
DRAWING_CELL_CLASS = "drawing-cell"
DRAWING_CELL_ON_CADENCE_CLASS = "drawing-cell--on-cadence"
DRAWING_CELL_LATE_CLASS = "drawing-cell--late"
DRAWING_CELL_MISSING_CLASS = "drawing-cell--missing"
DRAWING_CELL_NONE_CLASS = "drawing-cell--none"

# Status colouring for a drawing whose marks carry an ok/warn/error
# verdict; these set `color`, so every currentColor shape beneath them
# follows. Not var(--color-accent): style.css reserves accent for other
# uses.
DRAWING_STATUS_OK_CLASS = "drawing--ok"
DRAWING_STATUS_WARN_CLASS = "drawing--warn"
DRAWING_STATUS_ERROR_CLASS = "drawing--error"

# The three, as a set an emitter can validate a caller's argument
# against, so an emitter never interpolates an arbitrary,
# caller-influenceable class name.
DRAWING_STATUS_CLASSES = (
    DRAWING_STATUS_OK_CLASS,
    DRAWING_STATUS_WARN_CLASS,
    DRAWING_STATUS_ERROR_CLASS,
)

DRAWING_CLASSES = (
    DRAWING_GRID_CLASS,
    DRAWING_Y_LABELS_CLASS,
    DRAWING_X_LABELS_CLASS,
    DRAWING_CANVAS_CLASS,
    DRAWING_FIGURE_CLASS,
    DRAWING_AXIS_CLASS,
    DRAWING_LINE_CLASS,
    DRAWING_MARK_CLASS,
    DRAWING_AXIS_LABEL_CLASS,
    DRAWING_BAND_CLASS,
    DRAWING_BAND_SPAN_CLASS,
    DRAWING_BAND_MARK_CLASS,
    DRAWING_RING_TRACK_CLASS,
    DRAWING_RING_VALUE_CLASS,
    DRAWING_CELL_CLASS,
    DRAWING_CELL_ON_CADENCE_CLASS,
    DRAWING_CELL_LATE_CLASS,
    DRAWING_CELL_MISSING_CLASS,
    DRAWING_CELL_NONE_CLASS,
    DRAWING_STATUS_OK_CLASS,
    DRAWING_STATUS_WARN_CLASS,
    DRAWING_STATUS_ERROR_CLASS,
)

# The only values a fill or stroke attribute may carry; every real colour
# comes from a class bound to a theme token. `transparent` is included
# because a transparent fill is still opaque to SVG hit-testing, which is
# what makes an enlarged invisible circle work as a tap target.
PAINT_KEYWORDS = ("none", "currentColor", "transparent", "inherit")

_INFINITY = float("inf")


def status_class(state):
    """The drawing status modifier for one of the app's `"ok"`/`"warn"`/
    `"error"` verdicts, or None for anything else. Never raises.

    Lives here rather than in companion/layout.py because layout.py owns
    the page shell and draw.py may not import it. An unrecognised verdict
    returns None rather than a guessed class, so a caller falls back to
    the container's own colour instead of an arbitrary class name.
    """
    return {
        "ok": DRAWING_STATUS_OK_CLASS,
        "warn": DRAWING_STATUS_WARN_CLASS,
        "error": DRAWING_STATUS_ERROR_CLASS,
    }.get(state)


# --- escaping ---------------------------------------------------------

def escape(value):
    """`value` coerced to its escaped string form for safe interpolation
    into emitted markup. None becomes "". Never raises.

    The module's one escaping helper; every emitter uses it, including
    for numbers (a no-op there — an emitter with a "this is always a
    float" exception is one someone later hands a label to). Covers all
    five dangerous characters (`<`, `>`, `&`, `"`, `'`), since a drawing's
    <title> is reached both as an attribute value and as element content.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


# --- number validation, shared by every scheme below -------------------

def is_number(value):
    """True for a real, finite int or float. False for None, a bool, a
    string, a NaN and an infinity. Never raises.

    A bool is excluded because `isinstance(True, int)` is True in Python.
    A NaN is excluded because it would format into a coordinate attribute
    as the text "nan" and silently un-draw the shape.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if value != value:  # NaN is the only value unequal to itself
        return False
    return value not in (_INFINITY, -_INFINITY)


# --- the percentage scheme (no viewBox) -------------------------------

def percent_x(index, point_count):
    """The x position of point `index` of `point_count`, as a percentage
    in [0, 100]. Never raises.

    Spans the full width edge to edge, with no margin. `index` is clamped
    into [0, point_count - 1]. A series of fewer than two points returns
    0.0 rather than dividing by zero.
    """
    if not is_number(point_count) or point_count < 2:
        return 0.0
    if not is_number(index):
        return 0.0
    index = max(0, min(int(point_count) - 1, index))
    return index / (int(point_count) - 1) * 100


def percent_y(value, domain_min, domain_max, inset_percent=0.0):
    """The y position of `value` inside the fixed domain [`domain_min`,
    `domain_max`], as a percentage in [`inset_percent`, 100 -
    `inset_percent`]. Never raises.

    The domain is a constant the caller supplies, never derived from the
    series' own min/max — a self-scaling axis would rescale silently
    whenever a reading went out of range. The axis is inverted (larger
    value, smaller y) since SVG's y grows downward. `inset_percent`
    reserves a margin so a marker's radius stays inside the canvas; it
    comes from the caller's own label line-height (see
    health_page._SPARKLINE_VERTICAL_INSET_PERCENT).
    """
    if not is_number(value) or not is_number(domain_min) or not is_number(domain_max):
        return 0.0
    if not is_number(inset_percent):
        inset_percent = 0.0
    span = domain_max - domain_min
    if span == 0:
        return inset_percent
    clamped = max(domain_min, min(domain_max, value))
    return inset_percent + (
        1 - (clamped - domain_min) / span
    ) * (100 - 2 * inset_percent)


# --- the time domain, inside the percentage scheme --------------------
# A third domain, not a third scheme: percent_time() shares percent_x()'s
# no-viewBox canvas, but its x percentage is an instant's position inside
# a named day, not an index's share of a series — an index scale would
# draw a six-hour outage as one ordinary step.

SECONDS_PER_DAY = 24 * 60 * 60


def percent_time(instant, day_start, day_seconds=SECONDS_PER_DAY):
    """The x position of `instant` inside the day that begins at
    `day_start` and runs for `day_seconds`, as a percentage in [0, 100] —
    or None when `instant` falls outside that day or any argument is
    unusable. Never raises.

    `instant`/`day_start` are plain numbers in the same unit (epoch
    seconds); the Paris-day conversion itself stays in
    server/history_db.py, since this module may not import the server
    package. `day_seconds` is a parameter, not a constant, because a
    Europe/Paris day is 23 or 25 hours twice a year.

    Out of range is rejected, not clamped: pinning yesterday's check-in
    at 0% would draw a check-in that never happened. Both endpoints are
    inclusive (`day_start` is 0%, `day_start + day_seconds` is 100%).
    """
    if not is_number(instant) or not is_number(day_start):
        return None
    if not is_number(day_seconds) or day_seconds <= 0:
        return None
    offset = instant - day_start
    if offset < 0 or offset > day_seconds:
        return None
    return offset / day_seconds * 100


def percent_attr(value):
    """A percentage coordinate formatted for an SVG attribute, e.g. the
    text a `cx` or `y` attribute carries in the no-viewBox scheme.

    Two decimal places, matching the shipped chart. The `%` sign makes
    the coordinate resolve against the canvas's own rendered size; drop
    it and the number becomes CSS-pixel user units, silently mixing the
    two schemes.
    """
    if not is_number(value):
        value = 0.0
    return "%.2f%%" % value


def percent_canvas(class_name, children, label=None, hidden=False):
    """An <svg> in the percentage scheme: no viewBox, no
    preserveAspectRatio, so 1 user unit is 1 CSS pixel and every
    percentage resolves against this element's own rendered size.

    `class_name` is required: its CSS rule declares the canvas height,
    which every percentage coordinate is relative to, and must never vary
    inside a media query. Pass `label` for a drawing that is the only
    statement of its data (role="group" plus an accessible name), or
    `hidden=True` for one whose reading is already printed in text beside
    it.
    """
    attrs = {"class": _require_class(class_name)}
    if hidden:
        attrs["aria-hidden"] = "true"
    elif label is not None:
        attrs["role"] = "group"
        attrs["aria-label"] = label
    return "<svg%s>%s</svg>" % (_attrs(attrs), _children(children))


# --- the user-unit scheme (a viewBox) ---------------------------------

def unit_canvas(class_name, children, width, height, label=None, hidden=False):
    """An <svg> in the user-unit scheme: a viewBox of `width` x `height`
    user units plus intrinsic width/height attributes in CSS pixels.

    `class_name` is normally DRAWING_FIGURE_CLASS, never
    DRAWING_CANVAS_CLASS, which declares a width/height that would
    override these intrinsic attributes and letterbox the shape.
    Everything inside scales uniformly with the box (strokes and text
    included), which is why this scheme is only right for an
    aspect-locked mark.
    """
    attrs = {
        "class": _require_class(class_name),
        "viewBox": "0 0 %s %s" % (_number(width), _number(height)),
        "width": _number(width),
        "height": _number(height),
    }
    if hidden:
        attrs["aria-hidden"] = "true"
    elif label is not None:
        attrs["role"] = "img"
        attrs["aria-label"] = label
    return "<svg%s>%s</svg>" % (_attrs(attrs), _children(children))


def unit_circle_dash_array(fraction, radius):
    """The `stroke-dasharray` value that paints `fraction` of a circle of
    `radius` user units — the ring gauge's value arc, as a dashed full
    circle rather than an arc path. `fraction` is clamped into [0, 1].
    Never raises.

    The dash route, not an arc <path>: an arc whose sweep is the whole
    circle is degenerate in SVG (start and end coincide, so the renderer
    draws nothing), so a gauge built from an arc path would read 100% as
    empty.
    """
    if not is_number(radius) or radius <= 0:
        return "0 0"
    if not is_number(fraction):
        fraction = 0.0
    fraction = max(0.0, min(1.0, fraction))
    circumference = 2 * math.pi * radius
    drawn = circumference * fraction
    return "%.4f %.4f" % (drawn, circumference - drawn)


def unit_point_on_circle(fraction, centre_x, centre_y, radius):
    """The (x, y) user-unit point at `fraction` of the way clockwise
    around a circle, starting at twelve o'clock. `fraction` is clamped
    into [0, 1]. Never raises.

    For an endpoint marker or tick on a radial drawing, not the arc
    itself (see unit_circle_dash_array() above). Starts at twelve
    o'clock, not SVG's own three-o'clock zero, matching how a radial
    gauge is normally read.
    """
    if not is_number(radius):
        radius = 0.0
    if not is_number(centre_x):
        centre_x = 0.0
    if not is_number(centre_y):
        centre_y = 0.0
    if not is_number(fraction):
        fraction = 0.0
    fraction = max(0.0, min(1.0, fraction))
    angle = 2 * math.pi * fraction
    # Sine on x and negative cosine on y put fraction 0 at the top and
    # send it clockwise, in SVG's downward-growing y direction.
    return (centre_x + radius * math.sin(angle),
            centre_y - radius * math.cos(angle))


# --- shape emitters ---------------------------------------------------
# Every one of these takes an explicit class name and refuses to emit
# without it: an unclassed shape with no fill takes the SVG default
# black, invisible in one theme and invisible to the contrast harness.

def rect(class_name, x, y, width, height, attrs=None):
    """A filled <rect> — this project's axis, tick and cell primitive.

    Filled rather than a stroked <line>: no stroke-centring or
    half-pixel rounding to reason about, and a rect can pair a percentage
    position with an absolute size, which no stroked line can.
    """
    return _shape("rect", class_name, (
        ("x", x), ("y", y), ("width", width), ("height", height)), attrs)


def line(class_name, x1, y1, x2, y2, attrs=None):
    """One stroked <line> segment.

    A trend line in the percentage scheme is n-1 of these rather than one
    <polyline>: percentages are not permitted inside a `points` list, so
    a polyline cannot carry this coordinate scheme.
    """
    return _shape("line", class_name, (
        ("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)), attrs)


def circle(class_name, centre_x, centre_y, radius, attrs=None):
    """A <circle> — a data marker, a hit target, or a gauge ring.

    Document order is paint order in SVG and pointer events go to the
    topmost element, so a cosmetic marker is emitted immediately before
    an enlarged transparent target sharing its coordinates.
    """
    return _shape("circle", class_name, (
        ("cx", centre_x), ("cy", centre_y), ("r", radius)), attrs)


def path(class_name, d, attrs=None):
    """A <path>. Its `d` is in user units: percentages are not permitted
    in path data, so a path belongs to the unit scheme, or to a nested
    unit-scheme canvas inside a percentage-scheme drawing.
    """
    return _shape("path", class_name, (("d", d),), attrs)


def title(text):
    """A <title> child — the tooltip and accessible name a drawn shape
    carries. `text` is escaped, with no exception: these carry
    timestamps, firmware strings and airline names out of history.db.
    """
    return "<title>%s</title>" % escape(text)


def label_span(text, hidden=True):
    """One axis label, as an HTML <span> outside the canvas.

    Keeping labels outside the SVG makes viewBox overflow unreachable and
    keeps the label at a constant CSS size. `hidden` defaults True since
    a drawing whose points already announce their readings would
    otherwise be read twice.
    """
    attrs = {"class": DRAWING_AXIS_LABEL_CLASS}
    if hidden:
        attrs["aria-hidden"] = "true"
    return "<span%s>%s</span>" % (_attrs(attrs), escape(text))


# --- the ring gauge: ONE emitter, every size ---------------------------
# One emitter, two call sites, so the picture cannot drift the way it did
# once already with the percentage itself (companion/battery.py exists
# for that reason). Sizes below are ratios of the box side, not pixels,
# so every size is the same drawing scaled.

# The stroke, as a fraction of the box side: thick enough to read as a
# gauge at the small size (36px -> 4.32px) without closing the hole at
# the large one.
RING_STROKE_RATIO = 0.12

# Clear space between the stroke's outer edge and the viewBox edge: a
# stroked arc extends half its stroke width beyond the nominal radius,
# the most common way a ring gets clipped by its own box.
RING_CLEARANCE_RATIO = 0.02

# Below this the ring is no longer legible. Clamped rather than refused:
# a primitive that raises breaks the whole page rather than just itself.
RING_MIN_SIZE = 8


def ring_gauge(fraction, size, status_class=None):
    """A ring gauge: a full-circumference track plus a value arc, `size`
    CSS pixels square, for `fraction` of a turn. Never raises.

    `fraction` is 0..1 (not millivolts — this module doesn't import
    companion/battery.py), clamped; a non-number pins at empty, >1 pins
    at a full ring. The arc starts at 12 o'clock and advances clockwise
    (`rotate(-90)`). 1.0 draws a full circle with no dash (a full-sweep
    arc path renders nothing in SVG); 0.0 omits the arc (a zero-length
    dash renders as a dot under round caps). `status_class` is validated
    against DRAWING_STATUS_CLASSES; `aria-hidden`, since the percentage
    is already printed beside this drawing.
    """
    if not is_number(size) or size < RING_MIN_SIZE:
        size = RING_MIN_SIZE
    if not is_number(fraction):
        fraction = 0.0
    fraction = max(0.0, min(1.0, fraction))

    # Rounded once, here, so the dash arithmetic below runs on exactly
    # the numbers the attributes carry — an unrounded radius feeding a
    # rounded one would disagree with its own markup by a hair.
    centre = round(size / 2.0, 2)
    stroke = round(size * RING_STROKE_RATIO, 2)
    radius = round(size * (0.5 - RING_STROKE_RATIO / 2.0 - RING_CLEARANCE_RATIO), 2)

    shapes = [circle(DRAWING_RING_TRACK_CLASS, centre, centre, radius, attrs={
        "fill": "none",
        # A presentation attribute, not a stylesheet rule: a CSS
        # stroke-width of any specificity would flatten every size to
        # one thickness.
        "stroke-width": _number(stroke),
    })]
    if fraction > 0:
        value_attrs = {
            "fill": "none",
            "stroke-width": _number(stroke),
            "transform": "rotate(-90 %s %s)" % (_number(centre), _number(centre)),
        }
        if fraction < 1:
            value_attrs["stroke-dasharray"] = unit_circle_dash_array(fraction, radius)
        shapes.append(circle(
            DRAWING_RING_VALUE_CLASS, centre, centre, radius, attrs=value_attrs))

    class_name = DRAWING_FIGURE_CLASS
    if status_class in DRAWING_STATUS_CLASSES:
        class_name += " " + status_class
    return unit_canvas(class_name, shapes, size, size, hidden=True)


# --- the day band: a day, drawn at its real width ----------------------
# The only drawing here whose x axis is TIME rather than index (see
# percent_time() above). Emitted in the percentage scheme: a no-viewBox
# canvas, percentage positions, absolute pixel sizes.

# The drawn width of one check-in mark, in CSS pixels. 2, not 1: a 1px
# rect landing on a half-pixel boundary paints as two half-covered
# columns of grey rather than one column of ink — present but unreadable.
DAY_BAND_MARK_WIDTH_PX = 2

# The closest two marks may sit and still read as two marks, as a
# percentage of the band's width. At the 360px contract floor the band
# measures 278.00px (test_browser_ux.py re-derives this from a real
# browser); two 2px marks need 4px centre-to-centre to read as separate,
# and 4 / 278 = 1.4388%, rounded up to a legibility floor.
DAY_BAND_MIN_MARK_SPACING_PERCENT = 1.5


def day_band(day_start, day_seconds, instants, window=None, label=None):
    """`(markup, collapsed)` — one day drawn as a horizontal band: the
    day's frame, a shaded span for `window`, and one mark per instant
    that has room for a mark of its own. Never raises.

    Numbers are plain, one unit, as percent_time() above takes them.

    `collapsed` counts every instant that did not get its own mark
    (squeezed out by spacing, outside the day, or unusable) — a caption
    naming a total needs this. Element count is bounded by the band's
    width, never by row count: at most 67 marks regardless of how many
    rows a day holds.

    Marks are centred on their instants and carry no per-mark <title>;
    the canvas takes one `label` instead, aria-hidden when absent.
    """
    shapes = [rect(DRAWING_BAND_CLASS, 0, 0, "100%", "100%")]
    for start_percent, end_percent in _day_band_spans(
            day_start, day_seconds, window):
        shapes.append(rect(
            DRAWING_BAND_SPAN_CLASS, percent_attr(start_percent), 0,
            percent_attr(end_percent - start_percent), "100%"))
    kept, collapsed = _day_band_mark_percents(day_start, day_seconds, instants)
    # Centred on the instant: a mark whose left edge were the instant
    # would place a 23:59 mark outside the canvas. A transform pairs a
    # percentage position with an absolute half-width offset, which
    # arithmetic on the percentage alone cannot (it would need the
    # band's rendered pixel width, a number Python does not have).
    offset = "translate(%s 0)" % _number(-DAY_BAND_MARK_WIDTH_PX / 2.0)
    for percent in kept:
        shapes.append(rect(
            DRAWING_BAND_MARK_CLASS, percent_attr(percent), 0,
            DAY_BAND_MARK_WIDTH_PX, "100%", attrs={"transform": offset}))
    markup = percent_canvas(
        DRAWING_CANVAS_CLASS, shapes, label=label, hidden=label is None)
    return markup, collapsed


def _day_band_spans(day_start, day_seconds, window):
    """The `[(start_percent, end_percent), ...]` a shaded window occupies
    on the band — two of them when the window wraps past the end of the
    day (the normal case for a night window). Never raises; an unusable
    window shades nothing.

    A naive "start percent to end percent" rect renders a wrapping window
    inverted, so the wrap is handled here once rather than by each
    caller. A zero-width window shades nothing: server/device_config.py
    treats a window whose start equals its end as never active.
    """
    if window is None:
        return []
    try:
        start, end = window
    except (TypeError, ValueError):
        return []
    start_percent = percent_time(start, day_start, day_seconds)
    end_percent = percent_time(end, day_start, day_seconds)
    if start_percent is None or end_percent is None:
        return []
    if start_percent == end_percent:
        return []
    if end_percent > start_percent:
        return [(start_percent, end_percent)]
    # Document order is left to right, so the leading span first.
    return [(0.0, end_percent), (start_percent, 100.0)]


def _day_band_mark_percents(day_start, day_seconds, instants):
    """`(kept_percents, collapsed)` — the positions the band can draw one
    mark each for, in chronological order, and the count of supplied
    instants that get none. Never raises.

    A single forward pass over the sorted positions, each compared
    against the last KEPT one rather than its own predecessor: comparing
    against the immediate predecessor would let a cadence finer than the
    minimum spacing collapse an entire busy day into one mark at 00:00,
    with every element-count ceiling still satisfied. Comparing against
    the last kept mark instead walks the band at the minimum spacing, so
    a busy day reads as busy.
    """
    try:
        supplied = list(instants)
    except TypeError:
        return [], 0
    positions = []
    for instant in supplied:
        percent = percent_time(instant, day_start, day_seconds)
        if percent is not None:
            positions.append(percent)
    positions.sort()
    kept = []
    for percent in positions:
        if kept and percent - kept[-1] < DAY_BAND_MIN_MARK_SPACING_PERCENT:
            continue
        kept.append(percent)
    return kept, len(supplied) - len(kept)


# --- the check-in regularity grid: one cell, one bucket ---------------
# Unit scheme, not percentage: a cell is an aspect-locked mark, and
# percentage geometry would letterbox it. The fourth state (no
# observation) is the drawing's subject: a bucket the record says
# nothing about must not read as either verdict.

# The width, in CSS pixels, a drawing has inside a Health card at the
# 360px contract floor. Measured in a real browser (test_browser_ux.py
# re-derives it from the card's live clientWidth): 278.00px, the same
# number the day band above measures on Home by a different route.
CARD_DRAWING_WIDTH_PX = 278

# The smallest square a cell may be drawn at: the WCAG 2.5.8 (AA) target
# size. Applicable here because a cell carries a <title> and is a
# pointer target — a target nobody can hit is a tooltip nobody can read.
CELL_MIN_SIZE_PX = 24

# Clear ground between two cells, so two adjacent verdicts of different
# colours read as separate rather than one block. 3 is the smallest
# value that survives the fractional cell size below without a rounding
# artefact closing the gap.
CELL_GAP_PX = 3

# Ten cells is the most one row can hold at the 360px floor while every
# cell clears CELL_MIN_SIZE_PX ((278 - 3*9) / 10 = 25.10px; 11 cells
# would be 22.55px, under the floor). grid_columns() below computes this
# rather than hard-coding it, so a narrower card reduces columns on its
# own.

# The row count is what bounds the element count: columns are bounded by
# width, rows are not, so a caller handing over a year of buckets would
# emit a year of rects. Six rows of ten (60 cells) is what GRID_MAX_ROWS
# allows; anything past that is reported to the caller, not drawn.
GRID_MAX_ROWS = 6

# The four cell states, keyed on wake.classify_check_in_gap()'s own
# CHECK_IN_* values — re-typed here since this module is stdlib-only and
# may not import the server package. test_status_pages.py asserts this
# table's keys match that function's four values exactly.
CELL_STATE_CLASSES = {
    "on_cadence": DRAWING_CELL_ON_CADENCE_CLASS,
    "late": DRAWING_CELL_LATE_CLASS,
    "missing": DRAWING_CELL_MISSING_CLASS,
    "unknown": DRAWING_CELL_NONE_CLASS,
}


def cell_class(state):
    """The cell modifier for one wake.classify_check_in_gap() verdict.
    Never raises.

    An unrecognised state falls to the no-observation class, never to a
    real verdict: a cell always paints something, and only the
    no-observation class claims nothing about the device.
    """
    return CELL_STATE_CLASSES.get(state, DRAWING_CELL_NONE_CLASS)


def grid_columns(width=CARD_DRAWING_WIDTH_PX):
    """The most cells one row of a `width`-pixel grid can hold while
    every cell stays at least CELL_MIN_SIZE_PX square. At least 1. Never
    raises.

    Solves (width - gap*(c-1))/c >= min for c and floors the result.
    """
    if not is_number(width) or width <= 0:
        width = CARD_DRAWING_WIDTH_PX
    return max(1, int((width + CELL_GAP_PX) // (CELL_MIN_SIZE_PX + CELL_GAP_PX)))


def grid_cell_size(width=CARD_DRAWING_WIDTH_PX, columns=None):
    """The side of one square cell, in CSS pixels, for a `columns`-wide
    grid inside `width`. Never raises.

    Deliberately fractional: rounding down to whole pixels would leave
    the canvas narrower than its card, so the HTML label row beneath
    (sized from the card) would drift out from under the last column.
    """
    if not is_number(width) or width <= 0:
        width = CARD_DRAWING_WIDTH_PX
    if columns is None:
        columns = grid_columns(width)
    if not is_number(columns) or columns < 1:
        columns = 1
    columns = int(columns)
    return (width - CELL_GAP_PX * (columns - 1)) / float(columns)


def regularity_grid(cells, width=CARD_DRAWING_WIDTH_PX, label=None):
    """`(markup, dropped)` — a grid of square cells, one per bucket, laid
    out oldest-first left to right and top to bottom.

    `cells` is an iterable of `(state, title)` pairs; `state` is a
    wake.classify_check_in_gap() verdict (anything else paints as no
    observation) and `title` is the caller's text for that bucket. A
    missing or blank title raises: a coloured cell with nothing naming
    what it judged is a verdict nobody can check.

    `dropped` counts the oldest buckets that did not fit inside
    GRID_MAX_ROWS rows; the cells kept are the newest, so the drawing
    never shows a window that already ended. No cells draws nothing and
    drops nothing — the empty case belongs to the caller.
    """
    try:
        supplied = list(cells)
    except TypeError:
        return "", 0
    if not supplied:
        return "", 0

    columns = grid_columns(width)
    size = grid_cell_size(width, columns)
    capacity = columns * GRID_MAX_ROWS
    kept = supplied[-capacity:]
    dropped = len(supplied) - len(kept)
    rows = int(math.ceil(len(kept) / float(columns)))

    step = size + CELL_GAP_PX
    shapes = []
    for index, entry in enumerate(kept):
        try:
            state, text = entry
        except (TypeError, ValueError):
            raise ValueError(
                "a regularity-grid cell is a (state, title) pair — a cell with no title "
                "is a coloured verdict with nothing naming what it judged (got %r)"
                % (entry,))
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "a regularity-grid cell needs a title naming the bucket it judged: a "
                "coloured cell whose reading nobody can check is a claim, not a "
                "drawing (got %r)" % (text,))
        column = index % columns
        row = index // columns
        shapes.append(rect(
            "%s %s" % (DRAWING_CELL_CLASS, cell_class(state)),
            round(column * step, 2), round(row * step, 2),
            round(size, 2), round(size, 2), attrs={"title": text}))

    height = rows * size + CELL_GAP_PX * (rows - 1)
    markup = unit_canvas(
        DRAWING_FIGURE_CLASS, shapes, round(width, 2), round(height, 2),
        label=label, hidden=label is None)
    return markup, dropped


# --- internals --------------------------------------------------------

def _require_class(class_name):
    """`class_name`, or ValueError. See the shape-emitter note above."""
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValueError(
            "a drawn shape needs an explicit class — a shape with neither a "
            "class nor a fill takes the SVG default black and is invisible in "
            "one of the two themes (got %r)" % (class_name,))
    return class_name


def _number(value):
    """A coordinate or size formatted for an attribute: an int stays an
    int, a float gets two decimals, anything unusable becomes 0. A
    pre-formatted string (a percentage from `percent_attr()`, or path
    data) passes through to be escaped like everything else.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or not is_number(value):
        return "0"
    if isinstance(value, int):
        return "%d" % value
    return "%.2f" % value


# Attribute names this module will not emit under any value: each either
# loads something or paints something from outside the stylesheet.
REFUSED_ATTRIBUTES = ("href", "xlink:href", "src", "style",
                      "filter", "mask", "clip-path")
# Attribute names whose value is a paint rather than text — restricted to
# the keyword list rather than escaped, since a colour literal or url()
# could hide there.
PAINT_ATTRIBUTES = ("fill", "stroke", "stop-color")


def _attrs(attrs):
    """` k="v"` for each attribute, every value escaped, insertion order
    preserved. Raises on an attribute this module refuses to emit.

    A paint attribute may carry only a paint keyword: a colour decided in
    Python is correct in one theme only, and a url() there is an external
    reference — there is no safe rendering of either, so it is refused
    rather than escaped. An attribute that loads something is refused by
    name, whatever it carries. Everything else is text — a timestamp, an
    airline name, a firmware string out of history.db — and is escaped,
    never refused: refusing it would turn a page render into an exception
    for a value the app cannot control.
    """
    out = ""
    for name, value in attrs.items():
        if name in REFUSED_ATTRIBUTES or name.startswith("on"):
            raise ValueError(
                "companion/draw.py emits no external reference, no inline style "
                "and no event handler: refusing attribute %r" % (name,))
        text = value if isinstance(value, str) else _number(value)
        if name in PAINT_ATTRIBUTES and text not in PAINT_KEYWORDS:
            raise ValueError(
                "%s=%r is a paint decided in Python — a drawing takes its "
                "colour from a class bound to a theme token, so it is correct "
                "in both themes; only %r may be set here"
                % (name, text, PAINT_KEYWORDS))
        out += ' %s="%s"' % (name, escape(text))
    return out


def _children(children):
    """`children` joined: a string passes through, an iterable is joined."""
    if children is None:
        return ""
    if isinstance(children, str):
        return children
    return "".join(children)


def _shape(tag, class_name, geometry, attrs):
    """One self-closing shape element: the class first, then its geometry,
    then the caller's own attributes, then any <title> child.
    """
    merged = {"class": _require_class(class_name)}
    for name, value in geometry:
        merged[name] = _number(value)
    child = ""
    if attrs:
        for name, value in attrs.items():
            if name == "title":
                child = title(value)
                continue
            merged[name] = value
    if child:
        return "<%s%s>%s</%s>" % (tag, _attrs(merged), child, tag)
    return "<%s%s/>" % (tag, _attrs(merged))
