"""Behaviour tests for companion/contrast_check.py's WCAG contrast and
signal-separation math, run against the colour tokens companion/app.py
actually SERVES over HTTP — never against companion/static/style.css
opened from disk.

Two kinds of check:

- Formula fidelity: contrast_ratio()/hue_separation() reproduce a fixed
  set of hand-verified numbers exactly. These fixtures are historical
  reference values (some superseded by later token changes) and are
  hard-coded on purpose — they test the FORMULA, not the current
  stylesheet.
- Live tokens: every real light/dark colour pair the app actually ships
  (text-on-surface contrast, accent-vs-status signal separation) is
  measured against the `:root` custom properties fetched from a running
  server, via `served_stylesheet()` and `companion_markup.custom_properties()`.
  A future accidental token change fails these tests directly, because
  they read the value that shipped, not a copy of it.

Section 3 covers SIGNAL SEPARATION, a different guarantee from contrast:
that the accent colour cannot be mistaken for any status colour at a
glance. See companion/contrast_check.py's own module docstring for the
regression history this section exists to prevent.
"""
import re

import pytest

from companion.contrast_check import (
    MIN_SIGNAL_HUE_SEPARATION,
    MIN_SIGNAL_PERCEPTUAL_DISTANCE,
    STATUS_WARN_ON_CARD_PAIRS,
    WCAG_AA_NORMAL_TEXT,
    WCAG_AA_UI_COMPONENT,
    contrast_ratio,
    hue_separation,
    perceptual_distance,
)
from companion_app_server import served_stylesheet
from companion_markup import custom_properties, declarations_for

_DARK_AT_RULE = ("@media (prefers-color-scheme: dark)",)

_STATUS_TOKENS = {
    "ok": "--color-status-ok",
    "warn": "--color-status-warn",
    "error": "--color-status-error",
}


@pytest.fixture(scope="module")
def served_css(module_app_server_factory):
    """The stylesheet companion/app.py actually serves, fetched once for
    every test in this module (read-only: nothing here mutates server
    state)."""
    server = module_app_server_factory()
    return served_stylesheet(server)


@pytest.fixture(scope="module")
def theme_tokens(served_css):
    """The app's `:root` custom properties as actually served: the base
    block (light/default) and the `prefers-color-scheme: dark` override
    block, keyed by property name (e.g. "--color-accent")."""
    return {
        "light": custom_properties(served_css, ":root"),
        "dark": custom_properties(served_css, ":root", at_rules=_DARK_AT_RULE),
    }


def _hex_to_rgb(hex_color):
    stripped = hex_color.lstrip("#")
    return tuple(int(stripped[i:i + 2], 16) for i in (0, 2, 4))


def _alpha_composite(fg_hex, alpha_pct, bg_hex):
    """The colour a browser paints for `color: color-mix(in srgb, fg
    <alpha_pct>%, transparent)` text sitting on an opaque `bg_hex`
    background: color-mix() against `transparent` yields fg at alpha
    `alpha_pct` unchanged in its own RGB channels (mixing toward alpha 0
    at the same colour cancels out); the browser then composites that
    semi-transparent colour over the background beneath it, which is a
    plain per-channel alpha blend.
    """
    a = alpha_pct / 100.0
    fg = _hex_to_rgb(fg_hex)
    bg = _hex_to_rgb(bg_hex)
    return "#%02X%02X%02X" % tuple(round(a * f + (1 - a) * b) for f, b in zip(fg, bg))


_COLOR_MIX_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")


def _color_mix_percentage(declaration_value):
    """The percentage out of a `color-mix(in srgb, var(...) NN%,
    transparent)` declaration value."""
    match = _COLOR_MIX_PERCENT_RE.search(declaration_value)
    assert match, "expected a percentage in %r" % (declaration_value,)
    return float(match.group(1))


# ==========================================================================
# Formula fidelity: contrast_ratio() reproduces a fixed set of
# hand-verified numbers exactly, independent of whatever style.css ships
# today.
# ==========================================================================

_FORMULA_FIXTURES = (
    ("#E8622C", "#FBF9F6", 3.22),
    ("#E8622C", "#F3EEE7", 2.93),
    ("#D2521F", "#FBF9F6", 4.02),
    ("#FF8A5C", "#0D0F14", 8.25),
    ("B13F16", "FFFFFF", 5.85),
    ("#B13F16", "#F7F4EF", 5.33),
    ("#B13F16", "#EEE8DE", 4.80),
    ("#FF9B73", "#0C0F14", 9.31),
)


@pytest.mark.parametrize(
    "hex_a, hex_b, expected", _FORMULA_FIXTURES,
    ids=["%s-%s" % (a, b) for a, b, _ in _FORMULA_FIXTURES])
def test_contrast_ratio_reproduces_a_known_value(hex_a, hex_b, expected):
    assert round(contrast_ratio(hex_a, hex_b), 2) == expected


def test_hue_separation_takes_the_shorter_arc_across_the_wrap_point():
    # Pure-channel fixtures only (0x00/0xFF), so every expected value is
    # exact and this can never fail on a rounding artefact instead of a
    # real regression.
    for hex_a, hex_b, expected in (
            ("#FF0000", "#FF0000", 0.0),      # identical, hue 0
            ("#FF0000", "#00FF00", 120.0),    # hue 0 vs 120
            ("#FF0000", "#00FFFF", 180.0),    # maximal, opposite
            ("#FF00FF", "#FF0000", 60.0),     # 300 vs 0 — crosses 0/360
            ("#FFFF00", "#FF00FF", 120.0)):   # 60 vs 300 — crosses 0/360
        assert round(hue_separation(hex_a, hex_b), 1) == expected


# ==========================================================================
# Live tokens: every real light/dark text-on-surface pair the app ships
# meets WCAG AA, measured against the token the server actually sent.
# ==========================================================================

_LIVE_PAIRS = (
    ("light", "accent text/link on canvas", "--color-accent", "--color-canvas"),
    ("light", "accent on primary surface / active nav", "--color-accent", "--color-dominant"),
    ("light", "accent on secondary/sidebar surface", "--color-accent", "--color-secondary"),
    ("light", "primary-button label on accent fill", "--color-on-accent", "--color-accent"),
    ("light", "body text on canvas", "--color-text", "--color-canvas"),
    ("light", "body text on card surface", "--color-text", "--color-dominant"),
    ("dark", "accent text/link on canvas", "--color-accent", "--color-canvas"),
    ("dark", "accent on primary surface", "--color-accent", "--color-dominant"),
    ("dark", "accent on secondary/sidebar surface", "--color-accent", "--color-secondary"),
    ("dark", "primary-button label on accent fill", "--color-on-accent", "--color-accent"),
    ("dark", "body text on card surface", "--color-text", "--color-dominant"),
    ("light", "body text on secondary/sidebar surface", "--color-text", "--color-secondary"),
    ("dark", "body text on secondary/sidebar surface", "--color-text", "--color-secondary"),
)


@pytest.mark.parametrize(
    "theme, label, fg_token, bg_token", _LIVE_PAIRS,
    ids=["%s-%s" % (theme, label) for theme, label, _, _ in _LIVE_PAIRS])
def test_live_token_pair_meets_wcag_aa_normal_text(theme, label, fg_token, bg_token, theme_tokens):
    fg = theme_tokens[theme][fg_token]
    bg = theme_tokens[theme][bg_token]
    ratio = contrast_ratio(fg, bg)
    assert ratio >= WCAG_AA_NORMAL_TEXT, (
        "%s: %s: contrast_ratio(%r, %r) = %.2f, below WCAG_AA_NORMAL_TEXT (%.1f)"
        % (theme, label, fg, bg, ratio, WCAG_AA_NORMAL_TEXT))


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_muted_detail_text_on_card_surface_meets_wcag_aa_normal_text(theme, theme_tokens, served_css):
    """.battery-readout__detail's own muted-text strength (a `color-mix()`
    of --color-text against the card surface it renders on) still clears
    WCAG AA once actually composited over --color-dominant."""
    declarations = declarations_for(served_css, ".battery-readout__detail")
    percentage = _color_mix_percentage(declarations["color"])
    text = theme_tokens[theme]["--color-text"]
    card = theme_tokens[theme]["--color-dominant"]
    composited = _alpha_composite(text, percentage, card)
    ratio = contrast_ratio(composited, card)
    assert ratio >= WCAG_AA_NORMAL_TEXT, (
        "%s: contrast_ratio(%r, %r) = %.2f, below WCAG_AA_NORMAL_TEXT (%.1f)"
        % (theme, composited, card, ratio, WCAG_AA_NORMAL_TEXT))


# ==========================================================================
# Signal separation: --color-accent must be distinguishable from every
# --color-status-* colour, and the three status colours from each other,
# in both themes.
# ==========================================================================

@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("status_name", ("ok", "warn", "error"))
def test_accent_is_perceptually_separated_from_status(status_name, theme, theme_tokens):
    accent = theme_tokens[theme]["--color-accent"]
    status = theme_tokens[theme][_STATUS_TOKENS[status_name]]
    distance = perceptual_distance(accent, status)
    assert distance >= MIN_SIGNAL_PERCEPTUAL_DISTANCE, (
        "%s: perceptual_distance(accent, %s) = %.1f, below "
        "MIN_SIGNAL_PERCEPTUAL_DISTANCE (%.1f) — these two read as the "
        "same signal at a glance"
        % (theme, status_name, distance, MIN_SIGNAL_PERCEPTUAL_DISTANCE))


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("first, second", (("ok", "warn"), ("ok", "error"), ("warn", "error")))
def test_status_colours_are_perceptually_separated_from_each_other(first, second, theme, theme_tokens):
    """The check-in regularity grid paints all three status colours as
    adjacent cells with nothing but colour between them — the first
    surface in this app where that pairing matters."""
    a = theme_tokens[theme][_STATUS_TOKENS[first]]
    b = theme_tokens[theme][_STATUS_TOKENS[second]]
    distance = perceptual_distance(a, b)
    assert distance >= MIN_SIGNAL_PERCEPTUAL_DISTANCE, (
        "%s: perceptual_distance(%s, %s) = %.1f, below "
        "MIN_SIGNAL_PERCEPTUAL_DISTANCE (%.1f)"
        % (theme, first, second, distance, MIN_SIGNAL_PERCEPTUAL_DISTANCE))


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_accent_and_error_are_hue_separated(theme, theme_tokens):
    """Accent and error are the same colour family (both saturated
    red-oranges), so hue angle is the only channel left to separate them —
    the only pair held to this additional floor."""
    accent = theme_tokens[theme]["--color-accent"]
    error = theme_tokens[theme]["--color-status-error"]
    separation = hue_separation(accent, error)
    assert separation >= MIN_SIGNAL_HUE_SEPARATION, (
        "%s: hue_separation(accent, error) = %.1f deg, below "
        "MIN_SIGNAL_HUE_SEPARATION (%.1f deg)"
        % (theme, separation, MIN_SIGNAL_HUE_SEPARATION))


# A threshold everything passes proves nothing — these assert that the
# two floors above actually REJECT the exact values that shipped a real
# accent/error collision. If either of these ever starts failing, the
# floors have been loosened to the point of being decorative.
_SUPERSEDED_ERROR = (("light", "#DC2626"), ("dark", "#F87171"))


@pytest.mark.parametrize("theme, superseded", _SUPERSEDED_ERROR)
def test_perceptual_distance_floor_rejects_the_superseded_error_colour(theme, superseded, theme_tokens):
    accent = theme_tokens[theme]["--color-accent"]
    distance = perceptual_distance(accent, superseded)
    assert distance < MIN_SIGNAL_PERCEPTUAL_DISTANCE, (
        "the dE76 floor no longer rejects the superseded error colour %r "
        "(dE76 %.1f vs floor %.1f) — the threshold has been loosened past "
        "the defect it exists to catch"
        % (superseded, distance, MIN_SIGNAL_PERCEPTUAL_DISTANCE))


@pytest.mark.parametrize("theme, superseded", _SUPERSEDED_ERROR)
def test_hue_floor_rejects_the_superseded_error_colour(theme, superseded, theme_tokens):
    accent = theme_tokens[theme]["--color-accent"]
    separation = hue_separation(accent, superseded)
    assert separation < MIN_SIGNAL_HUE_SEPARATION, (
        "the hue floor no longer rejects the superseded error colour %r "
        "(%.1f deg vs floor %.1f deg)" % (superseded, separation, MIN_SIGNAL_HUE_SEPARATION))


# --color-status-error is painted as a fill, a border, an edge and an
# icon stroke — all non-text graphics, so WCAG_AA_UI_COMPONENT (3.0) is
# the applicable bar, not 4.5.
@pytest.mark.parametrize("theme", ("light", "dark"))
def test_status_error_meets_ui_component_contrast_on_every_surface(theme, theme_tokens):
    error = theme_tokens[theme]["--color-status-error"]
    for bg_token in ("--color-canvas", "--color-dominant", "--color-secondary"):
        bg = theme_tokens[theme][bg_token]
        ratio = contrast_ratio(error, bg)
        assert ratio >= WCAG_AA_UI_COMPONENT, (
            "%s: contrast_ratio(error, %s) = %.2f, below "
            "WCAG_AA_UI_COMPONENT (%.1f)" % (theme, bg_token, ratio, WCAG_AA_UI_COMPONENT))


# ==========================================================================
# The warn-coloured "Expected since" headline's own contrast gate. Unlike
# the live pairs above (every one required to PASS), this pair's own
# per-theme checks assert the ACTUAL measured verdict — dark clears WCAG
# AA, light does not — because that asymmetry is exactly what justifies
# style.css's own non-colour fallback for that headline.
# ==========================================================================

def _find_warn_on_card_pair(theme):
    for pair_theme, fg, bg in STATUS_WARN_ON_CARD_PAIRS:
        if pair_theme == theme:
            return fg, bg
    raise LookupError("no %s entry in STATUS_WARN_ON_CARD_PAIRS" % theme)


def test_warn_coloured_headline_on_card_surface_meets_contrast_in_dark_mode():
    fg, bg = _find_warn_on_card_pair("dark")
    ratio = contrast_ratio(fg, bg)
    assert ratio >= WCAG_AA_NORMAL_TEXT, (
        "dark: contrast_ratio(%r, %r) = %.2f, below WCAG_AA_NORMAL_TEXT (%.1f)"
        % (fg, bg, ratio, WCAG_AA_NORMAL_TEXT))


def test_warn_coloured_headline_on_card_surface_correctly_fails_contrast_in_light_mode():
    fg, bg = _find_warn_on_card_pair("light")
    ratio = contrast_ratio(fg, bg)
    assert ratio < WCAG_AA_NORMAL_TEXT, (
        "light: contrast_ratio(%r, %r) = %.2f, no longer below "
        "WCAG_AA_NORMAL_TEXT (%.1f) — the non-colour status-warn fallback "
        "may no longer be justified; re-check before reverting to a "
        "warn-coloured headline" % (fg, bg, ratio, WCAG_AA_NORMAL_TEXT))


def test_status_warn_on_card_pair_is_present_for_both_themes():
    themes_present = {theme for theme, _fg, _bg in STATUS_WARN_ON_CARD_PAIRS}
    assert themes_present == {"light", "dark"}


# ==========================================================================
# The login field's error BORDER: a non-text graphic (WCAG_AA_UI_COMPONENT,
# 3.0), distinguishable from both colours physically adjacent to it — the
# field's own fill (--color-secondary) and the login card's own surface
# (--color-dominant).
# ==========================================================================

@pytest.mark.parametrize("theme", ("light", "dark"))
def test_login_field_error_border_meets_contrast_against_adjacent_colours(theme, theme_tokens):
    border = theme_tokens[theme]["--color-status-error"]
    for bg_token in ("--color-secondary", "--color-dominant"):
        bg = theme_tokens[theme][bg_token]
        ratio = contrast_ratio(border, bg)
        assert ratio >= WCAG_AA_UI_COMPONENT, (
            "%s: contrast_ratio(border, %s) = %.2f, below "
            "WCAG_AA_UI_COMPONENT (%.1f) — drop the border from "
            ".login-form__input[aria-invalid=\"true\"] rather than "
            "weakening this threshold"
            % (theme, bg_token, ratio, WCAG_AA_UI_COMPONENT))
