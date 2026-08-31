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
"""

WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0
WCAG_AA_UI_COMPONENT = 3.0


def _linearize_channel(value_0_255):
    """Convert one 0-255 sRGB channel to its linear-light value per the
    WCAG 2.x relative-luminance formula."""
    c = value_0_255 / 255
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color):
    """Return the WCAG relative luminance (0.0-1.0) of a hex colour.

    Accepts both "E8622C" and "#E8622C" — a leading "#" is stripped, not
    required.
    """
    stripped = hex_color.lstrip("#")
    r = int(stripped[0:2], 16)
    g = int(stripped[2:4], 16)
    b = int(stripped[4:6], 16)
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
