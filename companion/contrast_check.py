"""companion/contrast_check.py — pure-stdlib WCAG 2.1 SC 1.4.3 relative-
luminance/contrast-ratio calculator for the SkyPane companion service
(06.6.2-CONTEXT.md D-14, UXA-04).

This is the WCAG 2.1 Success Criterion 1.4.3 relative-luminance and
contrast-ratio algorithm, reproduced from the published spec text
(https://www.w3.org/TR/WCAG21/#dfn-relative-luminance and
https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio) — verified in
06.6.2-RESEARCH.md to reproduce 06.6.1-UX-AUDIT.md's own published
contrast numbers exactly. No external tool, no network call, no
third-party library: zero `import` statements in this module, matching
this project's zero-external-dependency discipline (see companion/auth.py
for the same house convention).

Three functions:

- `_linearize_channel(value_0_255)`: converts one 0-255 sRGB channel to
  its linear-light value.
- `relative_luminance(hex_color)`: the WCAG relative luminance of a hex
  colour (accepts both "E8622C" and "#E8622C" — a leading "#" is
  stripped, never required).
- `contrast_ratio(hex_a, hex_b)`: the WCAG contrast ratio between two hex
  colours, lighter-over-darker, always >= 1.0.

Three named threshold constants so callers never hard-code a bare 4.5 or
3.0 — companion/test_contrast_check.py imports all of these by name, and
Phase 06.6.3's planner reads this module's function names as the literal
contract for verifying its own new per-page token pairs.

Since the heading-color-consistency debug session: three further
functions and two thresholds cover *signal separation* rather than
contrast. Contrast answers "can this be read against that background";
separation answers "can these two colours be told apart as different
signals at a glance" — a completely different question that this
project's design direction has always asserted in prose
(companion/static/style.css's header comment) and never once measured.
That gap is what let 06.6.2's WCAG-AA accent darkening (#E8622C ->
#B13F16) silently move --color-accent to within dE76 22.9 of
--color-status-error while every contrast check stayed green.

- `hue_degrees(hex_color)`: the HSL hue angle (0-360) of a hex colour.
- `hue_separation(hex_a, hex_b)`: the shortest angular distance between
  two hues, 0-180 — so 350 and 10 are 20 apart, not 340.
- `perceptual_distance(hex_a, hex_b)`: CIE76 dE in CIE L*a*b* (D65).
  CIE76 rather than CIE2000 on purpose: this module's whole point is
  zero imports and hand-verifiable arithmetic, and CIE76 is more than
  precise enough to answer "are these two signal colours confusable",
  which is the only question asked of it.

Still zero `import` statements — every one of these is plain arithmetic
(`** (1/3)` and `** 0.5` stand in for math.cbrt/math.sqrt).
"""

WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0
WCAG_AA_UI_COMPONENT = 3.0

# --- Signal-separation floors ------------------------------------------
#
# The primary gate. Calibrated to the accent-vs-warn pair that 06.6.1's
# design direction (D-04) explicitly examined and accepted as "these two
# never read as the same signal at a glance": in light mode that pair
# sits at dE76 28.6. So the floor is "every accent-vs-status pair must
# be at least as distinguishable as the one pair the direction actually
# validated". Applied to both themes and every status colour — this is
# the rule that, had it existed, would have failed the moment 06.6.2
# darkened the accent to #B13F16 (which put it at dE76 22.9 from the
# then-current --color-status-error #DC2626).
MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0

# The secondary gate, applied to the accent-vs-ERROR pair only —
# deliberately not to accent-vs-warn, which would fail it at 16.3 and
# is *supposed* to. The difference is real, not an exemption of
# convenience: the warn amber is a different colour family from the
# terracotta accent (golden/yellow vs red/orange) and is told apart by
# chroma and value even at a close hue angle, which is the specific
# trade D-04 examined. The error red is the SAME family as the accent —
# both are saturated red-oranges — so hue angle is the only channel
# left to separate them with, and a dE that clears the floor on
# lightness alone would still leave two red things that read as one
# signal. 24 degrees is comfortably past the ~16 degrees at which the
# two collided.
MIN_SIGNAL_HUE_SEPARATION = 24.0


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
    """Return the CIE76 Delta-E between two hex colours.

    Roughly: how different two colours look to a human, on a scale where
    ~1 is the just-noticeable threshold for adjacent patches and the
    tens are "obviously different colours". Used here to check that two
    *signal* colours (accent vs a status colour) cannot be mistaken for
    one another at a glance — a question WCAG contrast ratios say
    nothing about, since two colours can have near-identical luminance
    contrast against a shared background while being the same hue.
    """
    lab_a = _lab(hex_a)
    lab_b = _lab(hex_b)
    return sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)) ** 0.5
