"""companion/draw.py — the shared SVG geometry and emission primitives
for every drawing the SkyPane companion service renders (CFG-39,
24-01-PLAN.md Task 2).

Phase 24 adds four drawings across five plans on top of the one this app
already ships. Without a shared module that is five coordinate
vocabularies, five escaping habits and five ways for a shape to end up
invisible in one theme. This module is the one vocabulary; the executable
half of the contract lives in companion/test_companion_app.py, which
fails on a colour literal in emitted markup, on a drawn shape with no
fill route, and on a class name emitted from here that resolves to no
selector in companion/static/style.css.

This module is stdlib-only, exactly as companion/battery.py's own
docstring requires of itself and for the same reason. It must never
import a page module, never import anything from the server package, and
never import companion/layout.py — layout.py owns the page shell, nav,
tiles and timestamps, and dragging that into a geometry module would make
every drawing depend on the shell it is drawn inside.

It does NOT import companion/battery.py either, though it would be
allowed to. Geometry has no business knowing what it is plotting: the
page module reads the battery estimate from companion/battery.py (the one
home for it) and hands this module a fraction or a millivolt value with a
domain. Keeping the dependency out means a drawing of something else
entirely — a check-in gap, a punctuality cell — calls exactly the same
primitives with no battery-shaped concept in the way.

Nothing here needs, produces or tolerates JavaScript. D-09's no-JS floor
is why this whole phase server-renders its SVG: the drawing arrives
complete in the first HTTP response, paints identically with scripts
blocked, needs no measurement pass, and is unaffected by the app's
`script-src 'self'` policy. No primitive in this module returns markup
that a script has to finish.

TWO COORDINATE SCHEMES LIVE HERE, AND A DRAWING MUST NEVER MIX THEM.
They are two separately-named families of helpers rather than one family
with a `use_viewbox=` flag, because a flag is precisely how the two get
mixed inside one drawing:

  `percent_*`  — the no-viewBox scheme this app already ships (see
                 health_page.battery_sparkline_svg()). The <svg> carries
                 no viewBox and no preserveAspectRatio, so 1 SVG user
                 unit IS 1 CSS pixel: every position is a percentage in
                 [0, 100] and every size (radius, stroke, tick) is an
                 absolute CSS pixel at every container width. There is no
                 scale factor anywhere to go wrong, labels live OUTSIDE
                 the SVG as HTML in a CSS grid, and the drawing fills its
                 card at 360 px without a scrollbar. Right for a
                 card-filling time series.

  `unit_*`     — the viewBox scheme, user units on a uniform scale.
                 Right for an intrinsically aspect-locked mark (a ring
                 gauge, a grid cell) whose proportions must not stretch.
                 Its price is that strokes and any SVG text shrink with
                 the box, and that the viewBox must contain the outermost
                 label — so a drawing that can keep its labels outside
                 the SVG should use the percentage scheme instead.

Every value interpolated into emitted markup goes through `escape()`.
There is no "this value is always safe" exception: the drawings in this
phase carry timestamps, firmware strings and airline names out of
history.db and into <title> elements, and a value that is safe today is
a value nobody re-checks tomorrow.
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

# Structural ink: axis lines and ticks, drawn as filled rects.
DRAWING_AXIS_CLASS = "drawing-axis"
# A stroked path or line segment. Its rule declares `fill: none`, which is
# contract rule 4's "deliberately unfilled" case stated out loud.
DRAWING_LINE_CLASS = "drawing-line"
# A filled mark: a data point, a tick, a grid cell.
DRAWING_MARK_CLASS = "drawing-mark"
# An HTML label sitting outside the canvas in the grid above.
DRAWING_AXIS_LABEL_CLASS = "drawing-axis-label"

# Status colouring, for a drawing whose marks carry an ok/warn/error
# verdict. These set `color`, so every currentColor shape beneath them
# follows — and they use the app's existing status tokens. Deliberately
# NOT var(--color-accent): style.css's header comment keeps an exhaustive
# list of accent's reserved uses and a chart mark is not on it.
DRAWING_STATUS_OK_CLASS = "drawing--ok"
DRAWING_STATUS_WARN_CLASS = "drawing--warn"
DRAWING_STATUS_ERROR_CLASS = "drawing--error"

DRAWING_CLASSES = (
    DRAWING_GRID_CLASS,
    DRAWING_Y_LABELS_CLASS,
    DRAWING_X_LABELS_CLASS,
    DRAWING_CANVAS_CLASS,
    DRAWING_AXIS_CLASS,
    DRAWING_LINE_CLASS,
    DRAWING_MARK_CLASS,
    DRAWING_AXIS_LABEL_CLASS,
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
    series' own min/max (D-04/A-22). A scale that measures its own data
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


def _attrs(attrs):
    """` k="v"` for each attribute, every value escaped, insertion order
    preserved. Raises on an attribute this module refuses to emit.

    Three refusals, each one a defect this module exists to make
    unreachable: a fill or stroke carrying anything but a paint keyword
    (a literal colour is correct in one theme only), any value carrying
    an external reference, and any attribute that loads something.
    """
    out = ""
    for name, value in attrs.items():
        if name in ("href", "xlink:href", "src", "onload", "style"):
            raise ValueError(
                "companion/draw.py emits no external reference and no inline "
                "style: refusing attribute %r" % (name,))
        text = value if isinstance(value, str) else _number(value)
        if name in ("fill", "stroke", "stop-color"):
            if text not in PAINT_KEYWORDS:
                raise ValueError(
                    "%s=%r is a colour decided in Python — a drawing takes its "
                    "colour from a class bound to a theme token, so it is correct "
                    "in both themes; only %r may be set here"
                    % (name, text, PAINT_KEYWORDS))
        if "url(" in text or "<" in text:
            raise ValueError(
                "companion/draw.py emits no external reference and no nested "
                "markup: refusing %s=%r" % (name, text))
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
