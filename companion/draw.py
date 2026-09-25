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
#
# Every class this module can emit is a named constant, and DRAWING_CLASSES
# below collects them, so the harness can assert each one resolves to a
# real selector in companion/static/style.css rather than scraping string
# literals out of this file. A class that exists in Python and nowhere in
# CSS paints nothing at all, and nothing else in this codebase would
# notice — which is why that check exists and why these are constants.
#
# The paint idiom is currentColor plus a theme token, copied deliberately
# from the shipped .sparkline* rules: the SVG inherits `color` from its
# container, the container's colour is a theme token, and the drawing is
# therefore correct in BOTH themes with no second rule and no media
# query. A literal colour would be correct in one theme only, which is a
# defect and not a polish item.

# The grid wrapper that puts a time series' labels OUTSIDE the canvas:
# an auto-sized label column beside a minmax(0, 1fr) canvas column.
DRAWING_GRID_CLASS = "drawing"
DRAWING_Y_LABELS_CLASS = "drawing__y"
DRAWING_X_LABELS_CLASS = "drawing__x"

# The canvas itself. Carrying this class IS the percentage scheme's size
# route: companion/layout.py's icon_html() docstring records the trap
# that an <svg> with neither a size attribute nor a CSS rule renders at
# the SVG default 300x150 and blows the layout apart. The unit scheme
# takes the other route — intrinsic width/height attributes, emitted by
# unit_canvas() below — so neither scheme can reach that default.
DRAWING_CANVAS_CLASS = "drawing__canvas"

# The unit scheme's own canvas class. Separate from the one above, and
# separate for the same reason the two coordinate schemes are two
# separately-named helper families: .drawing__canvas declares a width and
# a height, which would override a unit canvas's intrinsic attributes and
# letterbox the aspect-locked shape inside a stretched box. One class
# with a modifier is how the two schemes get mixed inside one drawing.
DRAWING_FIGURE_CLASS = "drawing__figure"

# Structural ink: axis lines and ticks, drawn as filled rects.
DRAWING_AXIS_CLASS = "drawing-axis"
# A stroked path or line segment. Its rule declares `fill: none`, which is
# contract rule 4's "deliberately unfilled" case stated out loud.
DRAWING_LINE_CLASS = "drawing-line"
# A filled mark: a data point, a tick, a grid cell.
DRAWING_MARK_CLASS = "drawing-mark"
# An HTML label sitting outside the canvas in the grid above.
DRAWING_AXIS_LABEL_CLASS = "drawing-axis-label"

# The day band's three shapes. Three classes rather than one
# with modifiers, because the three are three different KINDS of thing
# and they take their colour from three different places: the frame is
# the day itself (structural ink, faint), the shaded span is a
# configured window the device honours (structural ink, solid) and a
# mark is a thing that HAPPENED (currentColor, the page's own text ink).
# Collapsing them into one class plus modifiers would make "the day",
# "asleep" and "a check-in" the same kind of statement, which is exactly
# what this drawing must not say.
DRAWING_BAND_CLASS = "drawing-band"
DRAWING_BAND_SPAN_CLASS = "drawing-band-span"
DRAWING_BAND_MARK_CLASS = "drawing-band-mark"

# The ring gauge's two arcs. Two classes, not one class with a
# modifier, because the two arcs take their colour from two different
# places on purpose: the track is structural ink (--color-border, the
# same token .drawing-axis uses) and the value arc is currentColor, so
# the status modifier below reaches the VALUE and leaves the track alone.
# A single class plus a modifier would make "the unfilled remainder" and
# "the reading" the same kind of thing, which is exactly what a gauge
# must not say.
DRAWING_RING_TRACK_CLASS = "drawing-ring-track"
DRAWING_RING_VALUE_CLASS = "drawing-ring-value"

# The check-in regularity grid's cells. A base class carrying
# the paint route and FOUR state modifiers — four, not three, and the
# fourth is the reason this is not `status_class()` above with a spare
# value bolted on. "I have no observation of this bucket" is a different
# KIND of statement from the three verdicts: the three are judgements
# about a measured interval, and the fourth is the absence of one. It
# takes structural ink rather than a status token precisely so it cannot
# read as a mild verdict.
#
# The modifiers set `color` and nothing else, so the same four classes
# paint an SVG cell (through the base class's `fill: currentColor`) and
# an HTML legend swatch (through its own `background: currentColor`)
# from ONE rule each. A legend that could disagree with the cells it
# explains is worse than no legend at all.
DRAWING_CELL_CLASS = "drawing-cell"
DRAWING_CELL_ON_CADENCE_CLASS = "drawing-cell--on-cadence"
DRAWING_CELL_LATE_CLASS = "drawing-cell--late"
DRAWING_CELL_MISSING_CLASS = "drawing-cell--missing"
DRAWING_CELL_NONE_CLASS = "drawing-cell--none"

# Status colouring, for a drawing whose marks carry an ok/warn/error
# verdict. These set `color`, so every currentColor shape beneath them
# follows — and they use the app's existing status tokens. Deliberately
# NOT var(--color-accent): style.css's header comment keeps an exhaustive
# list of accent's reserved uses and a chart mark is not on it.
DRAWING_STATUS_OK_CLASS = "drawing--ok"
DRAWING_STATUS_WARN_CLASS = "drawing--warn"
DRAWING_STATUS_ERROR_CLASS = "drawing--error"

# The three, as a set an emitter can VALIDATE a caller's argument
# against. An emitter that interpolated whatever status string it was
# handed would emit an arbitrary, caller-influenceable class name — the
# same reason layout.stat_tile() maps its own `status` through a fixed
# dict instead of formatting it into the class attribute.
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

# The only values a fill or stroke attribute may carry. Every real colour
# comes from a class bound to a theme token; these four keywords are the
# cases where no colour is wanted at all. `transparent` is here because a
# transparent fill is still opaque to SVG hit-testing, which is what makes
# an enlarged invisible circle work as a tap target (the shipped
# .sparkline-hit idiom).
PAINT_KEYWORDS = ("none", "currentColor", "transparent", "inherit")

_INFINITY = float("inf")


def status_class(state):
    """The drawing status modifier for one of the app's own `"ok"` /
    `"warn"` / `"error"` verdicts, or None for anything else. Never
    raises.

    ONE mapping, for the same reason DRAWING_STATUS_CLASSES exists above:
    both of the ring's call sites colour their drawing from a verdict a
    page ALREADY computed, and two `{"ok": ...}` dicts in two page
    modules is the drift this phase keeps removing. It lives here rather
    than in companion/layout.py because layout.py owns the page shell and
    draw.py may not import it; the vocabulary is already encoded in this
    module's own class names either way.

    An unrecognised verdict returns None rather than a guessed class, so
    an emitter handed one falls back to the container's own colour
    instead of painting an arbitrary, caller-influenceable class name —
    layout.stat_tile()'s own fixed-dict discipline, restated.
    """
    return {
        "ok": DRAWING_STATUS_OK_CLASS,
        "warn": DRAWING_STATUS_WARN_CLASS,
        "error": DRAWING_STATUS_ERROR_CLASS,
    }.get(state)


# --- escaping ---------------------------------------------------------

def escape(value):
    """`value` coerced to its escaped string form for safe interpolation
    into emitted markup. None becomes an empty string; any other
    non-string is coerced with str() first. Never raises.

    This is the module's ONE escaping helper and every emitter below uses
    it — including for numbers, where it is a no-op. The no-op case is
    the point: an emitter with an "this argument is always a float"
    exception is an emitter someone later passes a label to.

    All five dangerous characters are covered (`<`, `>`, `&`, `"` and
    `'`), because a value reaching an attribute needs the quote forms and
    a value reaching element content needs the others, and a drawing's
    <title> is reached by both kinds of caller.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


# --- the series, filtered exactly once --------------------------------

def is_number(value):
    """True for a real, finite int or float. False for None, a bool, a
    string, a NaN and an infinity. Never raises.

    A bool is excluded explicitly because `isinstance(True, int)` is True
    in Python and a `battery_mv` of True would otherwise plot as 1 mV. A
    NaN is excluded because it would format into a coordinate attribute
    as the text "nan" and silently un-draw the shape.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if value != value:  # NaN is the only value unequal to itself
        return False
    return value not in (_INFINITY, -_INFINITY)


def usable_pairs(rows, value_key, newest_first=True):
    """`[(value, row), ...]` in CHRONOLOGICAL order — one entry per row
    of `rows` whose `value_key` is a usable number, each paired with the
    row it came from. Never raises; a non-iterable `rows` degrades to [].

    ONE filtering pass, and each kept value stays attached to its OWN
    row. That is the whole reason this helper exists rather than two list
    comprehensions: filter the values and the labels separately and a
    single dropped row shifts every later label by one, so the chart ends
    up naming a value it does not reach. This codebase solved that once
    already, inside health_page.battery_sparkline_svg(); this is the same
    technique generalised, not a re-derivation of it.

    The consequence worth stating because a caller will rely on it: when
    the NEWEST row carries no usable value, the last pair returned is the
    newest row that does — so a "mark the latest point" drawing marks a
    reading that exists instead of a hole.

    `rows` is taken newest-first (every reader in this app returns that
    shape); pass `newest_first=False` for a series already in
    chronological order.
    """
    try:
        ordered = list(rows)
    except TypeError:
        return []
    if newest_first:
        ordered.reverse()
    pairs = []
    for row in ordered:
        try:
            value = row.get(value_key)
        except AttributeError:
            continue
        if is_number(value):
            pairs.append((value, row))
    return pairs


# --- the percentage scheme (no viewBox) -------------------------------

def percent_x(index, point_count):
    """The x position of point `index` of `point_count`, as a percentage
    in [0, 100]. Never raises.

    Spans the full width, edge to edge: "the drawing fills its card" is a
    property of this formula, not a tuned margin, and there is no margin
    constant anywhere for a later edit to get wrong.

    `index` is clamped into [0, point_count - 1], so an out-of-range
    index pins at an edge rather than drawing outside the canvas. A
    series of fewer than two points returns 0.0 rather than dividing by
    zero — a caller wanting a trend should refuse below two points, the
    way the shipped battery chart does, but a primitive must never raise.
    """
    if not is_number(point_count) or point_count < 2:
        return 0.0
    if not is_number(index):
        return 0.0
    index = max(0, min(int(point_count) - 1, index))
    return index / (int(point_count) - 1) * 100


def percent_y(value, domain_min, domain_max, inset_percent=0.0):
    """The y position of `value` inside the FIXED domain
    [`domain_min`, `domain_max`], as a percentage in
    [`inset_percent`, 100 - `inset_percent`]. Never raises.

    Three properties, each of which was paid for once already:

    The domain is a CONSTANT the caller supplies, never derived from the
    series' own min/max. A scale that measures its own data
    silently rescales when a reading goes out of range: a flat series
    pins to the bottom, a 15 mV wiggle stretches to fill the canvas and
    reads as a cliff. With a fixed domain a flat series draws flat and an
    out-of-range value PINS at the edge — there is no axis left to
    rescale.

    The axis is inverted (a larger value gets a smaller y), because SVG's
    y coordinate grows downward and a chart's value grows upward.

    `inset_percent` reserves a margin at top and bottom that the drawn
    line never crosses, so a marker's radius stays inside the canvas. It
    is a caller-supplied number rather than a constant here because it is
    derived from the caller's own label line-height — see
    health_page._SPARKLINE_VERTICAL_INSET_PERCENT, which is half the axis
    label's line box expressed as a percentage of the canvas height, so
    that a `space-between` label column puts each label's optical centre
    on the level it names.
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
#
# A THIRD DOMAIN, NOT A THIRD SCHEME, and the distinction is the reason
# `percent_time()` sits here beside `percent_x()` rather than in a
# family of its own: it emits percentages into the same no-viewBox
# canvas, so a drawing may mix it with `percent_y()` freely. What
# differs is what a percentage MEANS on the x axis.
#
#   percent_x()     maps an INDEX to a position. Point 4 of 7 sits at
#                   50% because it is the fourth of seven, whenever it
#                   happened. Right for a series whose readings arrive
#                   on a fixed cadence, where the ordinal IS the story —
#                   the shipped battery chart is exactly that.
#
#   percent_time()  maps an INSTANT to a position inside a NAMED day.
#                   An hour with no data still occupies its hour of
#                   width.
#
# The difference is not cosmetic, and it is the whole reason the second
# one exists. Under an index scale a six-hour outage is ONE STEP, the
# same width as the fifteen minutes either side of it, so the picture
# says "the frame checked in, then checked in again". Under a time scale
# the same outage is a quarter of the band with nothing in it. The time
# scale is what makes an outage look like an outage.

SECONDS_PER_DAY = 24 * 60 * 60


def percent_time(instant, day_start, day_seconds=SECONDS_PER_DAY):
    """The x position of `instant` inside the day that begins at
    `day_start` and runs for `day_seconds`, as a percentage in
    [0, 100] — or None when `instant` falls outside that day, or when
    any argument is unusable. Never raises.

    `instant` and `day_start` are plain numbers in the SAME unit (epoch
    seconds at every call site in this app). Geometry takes numbers
    rather than datetimes deliberately: this module may not import the
    server package, the one Paris-day conversion lives in
    server/history_db.py's own `_paris_day_or_none()`, and a scale that
    parsed timestamps would be a second place for a day boundary to be
    decided.

    `day_seconds` IS A PARAMETER AND NOT THE CONSTANT ABOVE, because a
    Europe/Paris day is 23 or 25 hours twice a year. A band that assumed
    86 400 would place every mark on a DST day at the wrong position and
    leave an hour of its own width unreachable; the caller subtracts two
    real tz-aware midnights and passes the answer.

    OUT OF RANGE IS REJECTED, NOT CLAMPED, and this is the one place
    this helper deliberately disagrees with `percent_y()` above it.
    Clamping is right for a VALUE: a battery reading under the domain is
    still a real reading of this device, and pinning it at the floor
    says "at or below this". Clamping is wrong for an INSTANT on a named
    day: pinning yesterday's check-in at 0% would make today's band
    claim a check-in at midnight that never happened, and a drawing that
    invents data is worse than one that omits it. A caller
    must therefore handle the None — which is also why a returned
    percentage can be trusted to be ON the band.

    Both endpoints are INCLUSIVE: `day_start` is 0% and `day_start +
    day_seconds` is 100%, because that instant is the band's own right
    edge. Which DAY a timestamp belongs to is a bucketing question, and
    it is answered by `_paris_day_or_none()` before anything reaches
    here — not by this function's endpoint convention.
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

    Two decimal places, matching the shipped chart exactly. The `%` sign
    is what makes the coordinate resolve against the canvas's own rendered
    size — drop it and the number becomes user units, which in this scheme
    means CSS pixels, which is the silent way to mix the two schemes
    inside one drawing.
    """
    if not is_number(value):
        value = 0.0
    return "%.2f%%" % value


def percent_canvas(class_name, children, label=None, hidden=False):
    """An <svg> in the percentage scheme: NO viewBox, NO
    preserveAspectRatio, so 1 user unit is 1 CSS pixel and every
    percentage inside resolves against this element's own rendered size.

    `class_name` is required and is this scheme's size route: the CSS
    rule on that class declares the canvas height, and every percentage
    coordinate emitted into it is a percentage OF that declared height.
    The height must therefore be declared exactly once and never varied
    inside a media query — a responsive height would move every point on
    the drawing with no other visual signal that anything broke.

    Pass `label` for a drawing that is the only statement of its data
    (it becomes role="group" plus an accessible name), or `hidden=True`
    for one whose reading is already in text beside it. Marking a
    decorative drawing aria-hidden is the correct choice, not a lazy one:
    a gauge beside its own printed percentage that also announced itself
    would make a screen reader say the number twice.
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
    user units PLUS intrinsic width/height attributes in CSS pixels.

    `class_name` is normally DRAWING_FIGURE_CLASS, never
    DRAWING_CANVAS_CLASS: the latter declares a width and a height, which
    would override the intrinsic attributes emitted here and letterbox
    this aspect-locked shape inside a stretched box.

    The intrinsic attributes are this scheme's size route — the other
    half of the trap companion/layout.py's icon_html() records, where an
    <svg> with neither an attribute nor a CSS rule renders at the SVG
    default 300x150. Emitting them here means a unit-scheme drawing
    cannot reach that default even with no stylesheet at all.

    Everything inside scales uniformly with the box, strokes and any SVG
    text included. That is the trade this scheme makes and the reason it
    is only right for an aspect-locked mark. A drawing that puts text
    INSIDE the viewBox also owes contract rule 5 — the viewBox must
    contain the text's own bounding box — and the practical way to prove
    that in this codebase is a real browser measurement, not arithmetic.
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
    `radius` user units — the ring gauge's value arc, expressed as a
    dashed full circle rather than an arc path. `fraction` is clamped into
    [0, 1]. Never raises.

    Deliberately the dash route and not an arc <path>: an arc whose sweep
    is the whole circle is DEGENERATE in SVG — start and end points
    coincide and the renderer draws nothing, so a gauge built from an arc
    path reads 100% as empty, which is the worst possible value to be
    wrong at. A dashed circle has no such case: at 1.0 the dash covers
    the circumference and at 0.0 it covers none of it, monotonically.
    It also needs no large-arc-flag reasoning and no trigonometry.

    Pair it with `stroke-dashoffset` and a rotation, or start the circle
    at the top with a transform, if the arc must begin somewhere other
    than the default three-o'clock start point.
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

    For an endpoint marker, a tick, or a label anchor on a radial
    drawing — not for the arc itself, which `unit_circle_dash_array()`
    above draws without any trigonometry at all.

    Twelve o'clock rather than SVG's own three-o'clock zero angle because
    every radial gauge a reader has ever seen starts at the top, and a
    primitive whose zero is somewhere else is a primitive whose callers
    each add their own quarter-turn correction.
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
#
# Every one of them takes an explicit class name and refuses to emit
# without it. A primitive that can emit an unclassed shape is a primitive
# that can emit an INVISIBLE one: with no class and no fill an SVG shape
# takes the format's default black fill, which is correct in one theme,
# invisible in the other, and invisible to the contrast harness too.

def rect(class_name, x, y, width, height, attrs=None):
    """A filled <rect> — this project's axis, tick and cell primitive.

    A filled rect rather than a stroked <line> for a real reason worth
    restating every time it is copied: an axis-aligned integer-width
    filled rect has no stroke-centring and no half-pixel rounding to
    reason about, and a rect can pair a PERCENTAGE position with an
    ABSOLUTE size — which no stroked line can, and which the percentage
    scheme needs for every tick it draws.
    """
    return _shape("rect", class_name, (
        ("x", x), ("y", y), ("width", width), ("height", height)), attrs)


def line(class_name, x1, y1, x2, y2, attrs=None):
    """One stroked <line> segment.

    A trend line in the percentage scheme is n-1 of these rather than one
    <polyline>, because percentages are not permitted inside a `points`
    list — a polyline simply cannot carry this coordinate scheme. The
    same constraint binds <polygon>, which is why a filled area under a
    percentage-scheme line is a real design question rather than an
    obvious polygon.
    """
    return _shape("line", class_name, (
        ("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)), attrs)


def circle(class_name, centre_x, centre_y, radius, attrs=None):
    """A <circle> — a data marker, a hit target, or a gauge ring.

    Document order is paint order in SVG and pointer events go to the
    topmost element, so a cosmetic marker is emitted immediately before
    the enlarged transparent target that shares its coordinates.
    """
    return _shape("circle", class_name, (
        ("cx", centre_x), ("cy", centre_y), ("r", radius)), attrs)


def path(class_name, d, attrs=None):
    """A <path>. Its `d` is in USER UNITS: percentages are not permitted
    in path data, so a path belongs to the unit scheme, or to a nested
    unit-scheme canvas inside a percentage-scheme drawing — never mixed
    directly into percentage geometry.
    """
    return _shape("path", class_name, (("d", d),), attrs)


def title(text):
    """A <title> child — the tooltip and accessible name a drawn shape
    carries. `text` is escaped, with no exception for a value that
    "comes from our own database": these carry timestamps, firmware
    strings and airline names straight out of history.db.
    """
    return "<title>%s</title>" % escape(text)


def label_span(text, hidden=True):
    """One axis label, as an HTML <span> OUTSIDE the canvas.

    Keeping labels out of the SVG is what makes viewBox overflow
    unreachable for a time-series drawing, and it keeps the label at a
    constant CSS size at every container width instead of shrinking with
    the box. `hidden` defaults True because a drawing whose points
    already announce their own readings would otherwise have a screen
    reader read its extremes twice.
    """
    attrs = {"class": DRAWING_AXIS_LABEL_CLASS}
    if hidden:
        attrs["aria-hidden"] = "true"
    return "<span%s>%s</span>" % (_attrs(attrs), escape(text))


def label_grid(y_labels_html, canvas_html, x_labels_html):
    """The grid wrapper that puts a time series' labels outside its
    canvas: an auto-sized label column beside the canvas, a label row
    below it.

    Document order is the contract, and it is the same order the shipped
    chart uses: the y-label column claims column 1 row 1, the canvas
    auto-places into the only cell left in row 1, and the x-label row
    auto-places into row 2. The canvas column is `minmax(0, 1fr)` in CSS,
    which is what lets it SHRINK at 360 px — a plain `1fr` would take its
    content's min-content width as a floor and produce exactly the
    horizontal page scrollbar this project forbids.
    """
    return '<div class="%s">%s%s%s</div>' % (
        escape(DRAWING_GRID_CLASS), y_labels_html, canvas_html, x_labels_html)


# --- the ring gauge: ONE emitter, every size ---------------------------
#
# The requirement is not "a ring appears" — it is ONE emitter with
# TWO call sites. The predictable failure is two functions that start
# identical and drift: one gains a threshold marker, the other does not;
# one is fixed at 4px stroke, the other at 2; six months later they
# disagree about what 20% looks like. companion/battery.py exists because
# that exact drift happened once with the percentage itself. These
# constants are the picture's half of the same fix.
#
# They are RATIOS OF THE BOX SIDE, not pixel values, and that is the
# whole mechanism: every size is the same drawing scaled, so the small
# ring's stroke is proportionally identical to the large one's and the
# two read as one component. A CSS-only "small variant" — same geometry,
# a thinner stroke class — would make the small ring's stroke
# proportionally twice as thick, which is a second component wearing the
# first one's name.

# The stroke, as a fraction of the box side. 0.12 is thick enough to read
# as a gauge at the small size (36px -> 4.32px of ink) without closing
# the hole at the large one.
RING_STROKE_RATIO = 0.12

# Clear space between the stroke's OUTER edge and the viewBox edge, again
# as a fraction of the side. It exists because a stroked arc extends half
# its stroke width beyond the nominal radius, which is the single most
# common way a ring gets clipped by its own box — contract rule 5, and
# the property companion/test_browser_ux.py measures in a real browser
# rather than deriving here.
RING_CLEARANCE_RATIO = 0.02

# Below this the ring is no longer a ring. A size at or under it is
# CLAMPED rather than refused: this is a primitive, and a primitive that
# raises has broken the whole page rather than just itself.
RING_MIN_SIZE = 8


def ring_gauge(fraction, size, status_class=None):
    """A ring gauge: a full-circumference track plus a value arc, `size`
    CSS pixels square, drawn for `fraction` of a turn. Never raises.

    THE ONE RING EMITTER. There is no `variant` parameter and
    there must never be one — a variant name is how two drawings hide
    inside one function, and it would defeat the requirement this
    function exists to satisfy. What varies is `size`, and `size` moves
    the GEOMETRY: the radius, the stroke width and the viewBox all scale
    from it together.

    `fraction` IS A FRACTION, NOT A MILLIVOLT READING. This module
    deliberately does not import companion/battery.py (see the module
    docstring): geometry has no business knowing what it is plotting, and
    a ring that took millivolts could not draw a check-in rate or any
    other share without growing a second domain. The caller reads
    the estimate from companion/battery.py — the ONE home for it — and
    hands the result here.

    DIRECTION, STATED SO A LATER CALLER CANNOT SILENTLY MIRROR IT: the
    value arc starts at TWELVE O'CLOCK and advances CLOCKWISE, matching
    `unit_point_on_circle()`'s own zero above so a tick or an endpoint
    marker added later lands on the arc rather than a quarter-turn off
    it. Mechanically that is a `rotate(-90)` about the centre on top of
    <circle>'s own three-o'clock, clockwise dash origin.

    THE DASH ROUTE, NOT AN ARC PATH, and the two degenerate cases it
    still owes explicitly:

      fraction 1.0 emits a COMPLETE CIRCLE with no dash pattern at all.
      An arc <path> whose sweep is the whole circle is degenerate in SVG
      — start and end coincide and the renderer draws nothing — so a
      gauge built from an arc path reads 100% as EMPTY, the worst
      possible value to be wrong at. Emitting the complete circle
      complete also means no rounding of the circumference can leave a
      hairline seam at the top.

      fraction 0.0 emits NO VALUE ARC AT ALL. A zero-length dash is not
      nothing: under a round line cap it renders as a DOT, so empty would
      read as a few percent. The element is omitted rather than emitted
      empty, which is the same "omit rather than fabricate" contract the
      pages already follow for a missing reading.

    TOTALITY, because the fraction arrives from a stored integer
    None, a bool, a NaN, a string and a negative all pin at
    empty; anything above 1 pins at exactly a full ring and never wraps
    round to a second lap. An unusable or too-small `size` clamps to
    RING_MIN_SIZE. Nothing here raises.

    `status_class` is validated against DRAWING_STATUS_CLASSES and
    IGNORED when it is anything else, so this function can never emit an
    arbitrary, caller-influenceable class name. It sets `color` on the
    <svg>, which the value arc follows through currentColor; the track
    keeps its own structural token either way.

    ARIA-HIDDEN, and that is a positive choice rather than a shortcut:
    the percentage is already printed in text beside this drawing at BOTH
    of its call sites, so a labelled graphic would make a screen reader
    announce the reading twice — the same reasoning `label_span()`'s own
    default already records for axis labels. A call site with no text
    percentage beside it would need a label instead, and would be a
    different function's problem.

    No tick marks and no gradient are emitted, and none may be added: the
    reading is an estimate, printed with an "approximately" marker, and a
    drawing that implied calibration would out-claim the number it sits
    beside.
    """
    if not is_number(size) or size < RING_MIN_SIZE:
        size = RING_MIN_SIZE
    if not is_number(fraction):
        fraction = 0.0
    fraction = max(0.0, min(1.0, fraction))

    # Rounded HERE, once, so the dash arithmetic below runs on exactly
    # the numbers the attributes carry — a dash length computed from an
    # unrounded radius and printed beside a rounded one is a drawing that
    # disagrees with its own markup by a hair, and a harness that
    # recomputes the arc from the emitted attributes would have to invent
    # a tolerance to hide it.
    centre = round(size / 2.0, 2)
    stroke = round(size * RING_STROKE_RATIO, 2)
    radius = round(size * (0.5 - RING_STROKE_RATIO / 2.0 - RING_CLEARANCE_RATIO), 2)

    shapes = [circle(DRAWING_RING_TRACK_CLASS, centre, centre, radius, attrs={
        "fill": "none",
        # A presentation ATTRIBUTE, never a stylesheet declaration: a CSS
        # stroke-width of any specificity beats a presentation attribute,
        # so a rule in style.css would flatten every size to one
        # thickness and quietly turn `size` back into a CSS-only variant.
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
#
# The day band is the only drawing here whose x axis is TIME
# rather than index (see `percent_time()` above for what that buys). It
# is emitted in the percentage scheme: a no-viewBox canvas whose height
# comes from CSS, percentage positions, absolute pixel sizes.

# The drawn width of one check-in mark, in CSS pixels. 2 and not 1: a
# 1px rect landing on a half-pixel boundary at device pixel ratio 1
# paints as two half-covered columns of grey rather than one column of
# ink, so the mark would be present and unreadable — this drawing's own
# version of the "painted but invisible" defect 24-05 had to composite
# an area over a card to see.
DAY_BAND_MARK_WIDTH_PX = 2

# The closest two marks may sit and still read as TWO marks, as a
# percentage of the band's width. THE ARITHMETIC, recorded here the way
# health_page._SPARKLINE_DENSE_POINT_THRESHOLD records its own, because
# a spacing constant with no derivation is a number the next reader
# tunes:
#
#   at the 360px contract floor the band's canvas MEASURES 278.00px.
#   That is a real number read off a real browser by
#   companion/test_browser_ux.py, not an estimate: this constant's first
#   draft assumed "about 330px" (viewport less gutters less card
#   padding) and was wrong by 52px, which made every figure below wrong
#   with it. The check now reads the width back and re-derives this
#   constant from it, so the estimate cannot drift from the layout
#   again.
#
#   1% of 278px is 2.78px. Two DAY_BAND_MARK_WIDTH_PX marks need their
#   2px of ink each plus a clear pixel between them to be two things
#   rather than one smear: 4px centre to centre, and 4 / 278 = 1.4388%.
#
# 1.5 is that figure rounded UP, and UP rather than down because this is
# a floor on legibility: rounding down would let two marks sit closer
# than the 4px the derivation just established, which is the one thing
# the constant exists to prevent. Three consequences a caller captions
# from: two marks at the minimum sit 4.17px apart with 2.17px of clear
# ground between them, the band can hold at most int(100 / 1.5) + 1 = 67
# marks whatever the row count, and the finest interval it
# can resolve on a 24-hour day is 1.5% of it, about 22 minutes. A
# 30-minute cadence is above that; a 60-second cadence is 1 440 instants
# and most of them WILL be collapsed, which is what `day_band()` reports
# rather than hides.
DAY_BAND_MIN_MARK_SPACING_PERCENT = 1.5


def day_band(day_start, day_seconds, instants, window=None, label=None):
    """`(markup, collapsed)` — one day drawn as a horizontal band: the
    day's own frame, a shaded span for `window`, and one mark per
    instant of `instants` that has room for a mark of its own. Never
    raises.

    `day_start`/`day_seconds`/`instants`/`window` are all plain numbers
    in one unit, exactly as `percent_time()` above takes them;
    `window` is a `(start, end)` pair of instants or None.

    `collapsed` IS HALF THE DRAWING AND NOT A DIAGNOSTIC. It counts
    every supplied instant that did NOT become a mark of its own —
    squeezed out by the minimum spacing, outside the day, or unusable.
    One number with one meaning: how many of the instants you gave me
    are not individually visible. A caller that captions "37 check-ins"
    over a band drawing 22 marks has told the reader they can count
    something they cannot, and a drawing that silently drops marks
    beside a caption claiming a total is the two halves of one lie
    Returning this is what lets the caption say something
    true instead.

    THE ELEMENT COUNT IS BOUNDED BY THE BAND'S WIDTH, NEVER BY THE ROW
    COUNT: at most 67 marks leave this function however many
    thousand rows a day holds, because the minimum spacing is what
    decides, and the frame and the spans are at most three more.

    Marks are CENTRED on their instants — see the transform below — and
    carry no <title> each. A per-mark tooltip on up to 67 elements would
    be 84 accessible names for one statement; the canvas takes a single
    `label` instead, and a band with no `label` is aria-hidden because
    the only honest reason to have none is that the page already states
    the same thing in text beside it.
    """
    shapes = [rect(DRAWING_BAND_CLASS, 0, 0, "100%", "100%")]
    for start_percent, end_percent in _day_band_spans(
            day_start, day_seconds, window):
        shapes.append(rect(
            DRAWING_BAND_SPAN_CLASS, percent_attr(start_percent), 0,
            percent_attr(end_percent - start_percent), "100%"))
    kept, collapsed = _day_band_mark_percents(day_start, day_seconds, instants)
    # Centred on the instant, not hung to the right of it. A mark whose
    # LEFT edge were its instant would say every check-in happened up to
    # DAY_BAND_MARK_WIDTH_PX later than it did, and would put the whole
    # of a 23:59 mark outside the canvas. A transform is the only way to
    # pair a PERCENTAGE position with an ABSOLUTE half-width offset —
    # the same constraint `rect()`'s own docstring records from the
    # other side, and the reason the offset is a transform rather than
    # arithmetic on the percentage (which would need the band's rendered
    # pixel width, a number Python does not have).
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
    on the band — TWO of them when the window wraps past the end of the
    day, which for a night window is the NORMAL case and not an edge
    case. Never raises; an unusable window shades nothing.

    A quiet-hours window of 22:00-07:00 under a naive "start percent to
    end percent" rect renders INVERTED: from 91.7% back to 29.2% is a
    negative width, and the obvious repair — swap the two — shades 07:00
    to 22:00, which is the whole of the day and none of the night. That
    repair looks entirely plausible in code and entirely wrong on
    screen, which is why the wrap is handled here once rather than left
    to each caller.

    A ZERO-WIDTH WINDOW SHADES NOTHING, deliberately:
    server/device_config.py's `seconds_until_quiet_hours_end()` states
    that a window whose start equals its end is never active and that
    this is intentional rather than a bug to fix. A hairline of shade
    would claim a window the device does not honour.
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
    """`(kept_percents, collapsed)` — the positions the band can draw
    one mark each for, in chronological order, and the count of supplied
    instants that get none. Never raises.

    The rule is a single forward pass over the sorted positions, each
    compared against the LAST KEPT one rather than against its own
    predecessor. The difference is not the element-count ceiling — that
    ceiling holds under either comparison, because the positions are
    sorted, so a gap of at least the minimum to the immediate
    predecessor is also a gap of at least the minimum to every earlier
    mark. The difference is the FLOOR, and it is the whole of why the
    comparison is against the last kept mark:

    at a cadence finer than the minimum spacing, EVERY consecutive gap
    is under the minimum, so a predecessor comparison keeps the first
    position and then never keeps another. A day of 1 440 check-ins
    would draw as one mark at 00:00 and an empty band after it — the
    device rendered as having died at midnight — while `collapsed`
    reported 1 439 and every ceiling stayed satisfied. Re-basing on each
    kept mark instead makes the run walk the band at the minimum
    spacing, so a busy day reads as busy: the same 1 440 check-ins draw
    66 marks spread from 0.00% to 99.31%.

    That failure passed all four of this band's original checks, which
    were ceilings to a one. `companion/test_view_pages.py` now asserts
    the floor too: no interior gap and no tail at the band's end may
    reach the minimum spacing, both exact consequences of the greedy
    rule rather than tolerances.
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
#
# The regularity grid: this module's other drawing. It
# is emitted in the UNIT scheme rather than the percentage one, which is
# the opposite choice from the day band immediately above, so the reason
# is worth stating: a cell is an aspect-locked mark. Percentage geometry
# would make every cell as wide as a tenth of the card and as tall as a
# third of a fixed canvas height, so the same drawing would be squares on
# a phone and letterboxes on a desktop — `.drawing__figure`'s own comment
# names exactly that distortion, and a grid of cells is the case it names.
#
# THE FOURTH STATE IS THE DRAWING'S SUBJECT, not an edge case it also
# handles. A log range `history_db.
# ingest_caddy_battery_log()` missed leaves a hole in `device_health`
# that no schema change can tell apart from a device that did not wake.
# So a bucket the record says nothing about gets its own state, painted
# in structural ink, and it is neither of the two verdicts a reader would
# act on. Conflating it with "on cadence" would report a device as
# healthy on the strength of no evidence; conflating it with "missing"
# would accuse a freshly-provisioned device of failing on the same.

# The width, in CSS pixels, a drawing has inside a Health card at the
# 360px contract floor. MEASURED IN A REAL BROWSER, never estimated: a
# `.page-section--nested` card there reports clientWidth 310 with 16px of
# padding on each side, so its content box is exactly 278.00px — the same
# number the day band above measured on Home by a different route.
#
# 24-06 planned its own spacing against "about 330px" and was wrong by
# 52px, which made every figure derived from it wrong with it. That is
# why this is a measurement and why companion/test_browser_ux.py reads
# the card's real width back and re-derives this constant from it, so the
# two cannot drift apart again.
CARD_DRAWING_WIDTH_PX = 278

# The smallest square a cell may be drawn at. WCAG 2.5.8 (Level AA)
# target size — which .claude/skills/sketch-findings-skypane/references/
# control-density.md names by number as the floor this app still meets
# after trading away 2.5.5's 44px for its buttons. It is the applicable
# floor here rather than a bare legibility guess because a cell carries a
# <title>: it is a pointer target, and a target nobody can hit is a
# tooltip nobody can read.
CELL_MIN_SIZE_PX = 24

# Clear ground between two cells. 2px would be the day band's own minimum
# separation for a mark, but a cell is a filled square rather than a
# hairline and its neighbours carry DIFFERENT colours — the gap here is
# what stops two adjacent verdicts reading as one longer block, not what
# stops one mark smearing into two. 3 is the smallest value that survives
# the fractional cell size below without a rounding artefact closing it.
CELL_GAP_PX = 3

# THE ARITHMETIC, recorded the way DAY_BAND_MIN_MARK_SPACING_PERCENT
# above records its own, because a layout constant with no derivation is
# a number the next reader tunes:
#
#   a row of c cells inside CARD_DRAWING_WIDTH_PX with CELL_GAP_PX
#   between them gives each cell (278 - 3(c - 1)) / c pixels.
#     c = 10  ->  25.10px, clear of the 24px floor
#     c = 11  ->  22.55px, under it
#   so TEN is the most cells one row can hold at the 360px floor while
#   every one of them stays a real target.
#
# `grid_columns()` below COMPUTES that rather than hard-coding 10, so a
# card that gets narrower reduces the column count on its own — the
# direction this drawing must degrade in. A grid of sub-pixel cells is a
# texture, not a chart.
#
# THE ROW COUNT IS WHAT BOUNDS THE ELEMENT COUNT. Columns are
# bounded by width; rows are not bounded by anything the geometry knows,
# so a caller handing over a year of buckets would emit a year of rects.
# Six rows of ten is 60 cells and about 170px tall — a drawing, not a
# wall — and anything past that is reported to the caller rather than
# drawn, exactly as `day_band()` reports its own collapsed marks.
GRID_MAX_ROWS = 6

# The four cell states, keyed on `wake.classify_check_in_gap()`'s own
# CHECK_IN_* VALUES. They are re-typed here by necessity and not by
# choice: this module is stdlib-only and may never import the server
# package (see the module docstring), so the coupling cannot be an
# import. companion/test_status_pages.py asserts this table's keys are
# exactly that function's four values, which is what stops the necessity
# becoming a drift — rename a verdict there and every cell would paint in
# the no-observation colour with nothing else failing, drawing a device
# that had checked in perfectly as a month of silence.
CELL_STATE_CLASSES = {
    "on_cadence": DRAWING_CELL_ON_CADENCE_CLASS,
    "late": DRAWING_CELL_LATE_CLASS,
    "missing": DRAWING_CELL_MISSING_CLASS,
    "unknown": DRAWING_CELL_NONE_CLASS,
}


def cell_class(state):
    """The cell modifier for one `wake.classify_check_in_gap()` verdict.
    Never raises.

    ANYTHING UNRECOGNISED FALLS TO THE NO-OBSERVATION CLASS, and that
    direction is the whole point rather than a tidy default.
    `status_class()` above returns None for a verdict it does not know,
    because a ring with no status modifier simply inherits its
    container's colour and says nothing. A cell has no such neutral: it
    is going to be painted something, so an unknown verdict has to land
    on the one state that claims nothing about the device. Falling to
    "on cadence" would report health from a value nobody recognised;
    falling to "missing" would accuse the device on the same.
    """
    return CELL_STATE_CLASSES.get(state, DRAWING_CELL_NONE_CLASS)


def grid_columns(width=CARD_DRAWING_WIDTH_PX):
    """The most cells one row of a `width`-pixel grid can hold while
    every cell stays at least CELL_MIN_SIZE_PX square. At least 1, never
    raises.

    This is the "reduce the buckets, never the cells" rule as a function.
    Solving (width - gap(c - 1)) / c >= min for c gives
    c <= (width + gap) / (min + gap), and the floor of that is the answer.
    """
    if not is_number(width) or width <= 0:
        width = CARD_DRAWING_WIDTH_PX
    return max(1, int((width + CELL_GAP_PX) // (CELL_MIN_SIZE_PX + CELL_GAP_PX)))


def grid_cell_size(width=CARD_DRAWING_WIDTH_PX, columns=None):
    """The side of one square cell, in CSS pixels, for a `columns`-wide
    grid inside `width`. Never raises.

    DELIBERATELY FRACTIONAL. Rounding down to whole pixels would leave
    the canvas narrower than the card it sits in — 10 cells of 25px plus
    9 gaps is 277 against 278 — and that 1px would then have to be
    absorbed somewhere: either the drawing stops filling its card, or the
    HTML label row beneath it (which sizes itself from the card, not from
    this arithmetic) ends one pixel wider than the cells it labels, so
    the last label no longer sits under the last column. One scale places
    the cells and the labels, and this is what keeps that true.
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

    `cells` is an iterable of `(state, title)` pairs: `state` is a
    `wake.classify_check_in_gap()` verdict (anything else paints as no
    observation, see `cell_class()`), and `title` is the caller's own
    text for that bucket.

    THE <title> IS REQUIRED AND A MISSING ONE RAISES. This is the one
    place this module refuses a VALUE rather than degrading, and the
    reason is the same one `_require_class()` gives for a missing class:
    a coloured cell with nothing naming what it judged is a verdict a
    reader cannot check, and the honest failure is loud. `_attrs()`
    escapes every one of them — these carry timestamps out of history.db.

    `dropped` IS HALF THE RETURN VALUE, exactly as `day_band()`'s
    `collapsed` is: it counts the OLDEST buckets that did not fit inside
    GRID_MAX_ROWS rows, so a caption can say what window is actually on
    screen instead of naming one the drawing truncated. The cells KEPT
    are the newest — a bounded grid that kept the oldest would draw a
    window that had already ended, which is the shape of defect 24-06
    found in the day band's own spacing rule and which every ceiling
    assertion in the world stays green for.

    No cells at all draws NOTHING and drops nothing. The empty case is a
    real case (a fresh deployment), but it belongs to the caller: a page
    that knows its window can hand over a grid of no-observation cells
    and say so, which is a truer picture than an absent section.
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


# Attribute names this module will not emit under any value: each one
# either loads something or paints something from outside the stylesheet.
REFUSED_ATTRIBUTES = ("href", "xlink:href", "src", "style",
                      "filter", "mask", "clip-path")
# Attribute names whose value is a PAINT rather than text. These are the
# ones a colour literal or a url() reference could hide in, so their
# values are restricted to the keyword list rather than escaped.
PAINT_ATTRIBUTES = ("fill", "stroke", "stop-color")


def _attrs(attrs):
    """` k="v"` for each attribute, every value escaped, insertion order
    preserved. Raises on an attribute this module refuses to emit.

    The refusals are narrow ON PURPOSE, and the boundary between
    "refuse" and "escape" is the whole point of this function:

    A paint attribute may carry only a paint keyword, because a colour
    decided in Python is correct in one theme only and a url() there is
    an external reference. That is a refusal, because there is no safe
    rendering of a value that should not exist.

    An attribute that LOADS something is refused by name, whatever it
    carries.

    Everything else is TEXT — a timestamp, an airline name, a firmware
    string out of history.db — and text is escaped, never refused.
    Refusing it would turn a page render into an exception for a value
    the app cannot control, which is a worse outcome than the escaping
    that already makes it safe.
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
