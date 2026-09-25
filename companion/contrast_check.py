"""Pure-stdlib WCAG 2.1 SC 1.4.3 relative-luminance/contrast-ratio
calculator, reproduced from the published spec
(https://www.w3.org/TR/WCAG21/#dfn-relative-luminance,
https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio). Zero imports,
matching this project's zero-external-dependency discipline.

Also covers *signal separation* (hue/perceptual distance): a different
question from contrast — "can two colours be told apart at a glance" —
that once let an accent-colour darkening drift close to the
status-error colour while every contrast check stayed green.
"""

WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0
WCAG_AA_UI_COMPONENT = 3.0

# --- Signal-separation floors ------------------------------------------
#
# Calibrated to the accent-vs-warn pair the design direction examined
# and accepted as never reading as the same signal: dE76 28.6 in light
# mode. Applied to every accent-vs-status pair, both themes.
MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0

# Applied to accent-vs-ERROR only, not accent-vs-warn (which fails it
# at 16.3 on purpose: warn is a different colour family, told apart by
# chroma/value; error is the same red-orange family as accent, so hue
# angle is the only separating channel left). 24° clears the ~16° where
# the two once collided.
MIN_SIGNAL_HUE_SEPARATION = 24.0

# --- Named token pairs --------------------------------------------------
#
# The one status colour used as body text. Light mode measures 3.19:1,
# below WCAG_AA_NORMAL_TEXT (4.5) — the overdue state is carried by
# wording and a warn dot, not this text's own contrast.
STATUS_WARN_ON_CARD_PAIRS = (
    ("light", "#D97706", "#FFFFFF"),
    ("dark", "#FBBF24", "#151922"),
)


def _linearize_channel(value_0_255):
    """Convert one 0-255 sRGB channel to its linear-light value per the
    WCAG 2.x relative-luminance formula."""
    c = value_0_255 / 255
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _channels(hex_color):
    """Split a hex colour into its three 0-255 channels.

    Accepts both "E8622C" and "#E8622C" — a leading "#" is stripped, not
    required. Factored out so every function below parses colours
    identically and a malformed value fails in exactly one place.
    """
    stripped = hex_color.lstrip("#")
    return (
        int(stripped[0:2], 16),
        int(stripped[2:4], 16),
        int(stripped[4:6], 16),
    )


def relative_luminance(hex_color):
    """Return the WCAG relative luminance (0.0-1.0) of a hex colour.

    Accepts both "E8622C" and "#E8622C" — a leading "#" is stripped, not
    required.
    """
    r, g, b = _channels(hex_color)
    return (
        0.2126 * _linearize_channel(r)
        + 0.7152 * _linearize_channel(g)
        + 0.0722 * _linearize_channel(b)
    )


def contrast_ratio(hex_a, hex_b):
    """Return the WCAG contrast ratio between two hex colours.

    Always >= 1.0 — the lighter colour's luminance is ordered first
    regardless of argument order.
    """
    l_a = relative_luminance(hex_a)
    l_b = relative_luminance(hex_b)
    lighter, darker = (l_a, l_b) if l_a >= l_b else (l_b, l_a)
    return (lighter + 0.05) / (darker + 0.05)


def hue_degrees(hex_color):
    """Return the HSL hue angle (0.0-360.0) of a hex colour.

    A fully desaturated colour (r == g == b) has no meaningful hue and
    returns 0.0 — callers comparing greys should not be using this
    function at all, so no exception is raised for a case that cannot
    occur among this project's saturated signal colours.
    """
    r, g, b = (channel / 255 for channel in _channels(hex_color))
    high = max(r, g, b)
    low = min(r, g, b)
    span = high - low
    if span == 0:
        return 0.0
    if high == r:
        hue = ((g - b) / span) % 6
    elif high == g:
        hue = ((b - r) / span) + 2
    else:
        hue = ((r - g) / span) + 4
    return (hue * 60) % 360


def hue_separation(hex_a, hex_b):
    """Return the shortest angular distance (0.0-180.0) between two hues.

    Hue is a circle, so the naive absolute difference is wrong at the
    wrap point: a crimson at 345 and a red-orange at 15 are 30 apart,
    not 330. Taking the shorter of the two arcs is what makes this
    usable as a "can these be told apart" measure.
    """
    delta = abs(hue_degrees(hex_a) - hue_degrees(hex_b)) % 360
    return 360 - delta if delta > 180 else delta


def _lab(hex_color):
    """Return the CIE L*a*b* (D65, 2 degree observer) triple for a hex
    colour. Internal — `perceptual_distance()` is the public entry."""
    linear = [_linearize_channel(channel) for channel in _channels(hex_color)]
    r, g, b = linear
    # sRGB -> CIEXYZ (D65), then normalised by the D65 white point.
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.00000
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy) - 16, 500 * (fx - fy), 200 * (fy - fz)


def perceptual_distance(hex_a, hex_b):
    """Return the CIE76 Delta-E between two hex colours: ~1 is the
    just-noticeable threshold, tens are "obviously different colours".
    Checks that two *signal* colours cannot be mistaken for one another
    at a glance — a question WCAG contrast ratios say nothing about,
    since two colours can share luminance contrast while being the
    same hue.
    """
    lab_a = _lab(hex_a)
    lab_b = _lab(hex_b)
    return sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)) ** 0.5
