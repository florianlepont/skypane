#!/usr/bin/env python3
"""Contract harness for companion/contrast_check.py (06.6.2-CONTEXT.md
D-14, UXA-04).

Covers: contrast_ratio() reproducing 06.6.1-UX-AUDIT.md's own published
contrast numbers exactly (formula fidelity), and every real light/dark
text-on-surface token pair companion/static/style.css actually uses for
normal text or a primary-button label meeting WCAG AA (>= 4.5:1) — a
permanent regression suite, not a one-off script. Final hex literals are
hard-coded here rather than read from the CSS file dynamically, so a
future accidental token change is caught as a real regression.

Section 3 (heading-color-consistency debug session) covers SIGNAL
SEPARATION, a different guarantee from contrast: that --color-accent
cannot be mistaken for any --color-status-* colour at a glance. That
guarantee existed for three phases as prose in style.css naming only the
accent-vs-warn pair, and nothing measured it — which is exactly how
06.6.2's WCAG-AA accent darkening (#E8622C -> #B13F16) moved the accent
to within dE76 22.9 / 15.9 degrees of --color-status-error #DC2626 with
all 16 contrast checks still green, producing an app where the primary
"Save Settings" button and the "something is wrong" banner edge read as
the same brick red. Contrast and separation are orthogonal: two colours
can have near-identical contrast against a shared background while being
the same hue.

Stdlib-only (os, sys). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_contrast_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion.contrast_check import (  # noqa: E402
    MIN_SIGNAL_HUE_SEPARATION,
    MIN_SIGNAL_PERCEPTUAL_DISTANCE,
    WCAG_AA_NORMAL_TEXT,
    WCAG_AA_UI_COMPONENT,
    contrast_ratio,
    hue_separation,
    perceptual_distance,
)

EXPECTED_CHECK_COUNT = 34


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # Section 1: formula fidelity — contrast_ratio() reproduces
    # 06.6.1-UX-AUDIT.md's own published numbers exactly (the same
    # fixtures proven in companion/contrast_check.py's own Task 1
    # <verify>, now as permanent regression checks).
    # ==================================================================

    def _make_formula_check(hex_a, hex_b, expected):
        def _check():
            got = round(contrast_ratio(hex_a, hex_b), 2)
            if got != expected:
                return False, (
                    "contrast_ratio(%r, %r) = %.2f, expected %.2f"
                    % (hex_a, hex_b, got, expected))
            return True, ""
        return _check

    for hex_a, hex_b, expected in (
        ("#E8622C", "#FBF9F6", 3.22),
        ("#E8622C", "#F3EEE7", 2.93),
        ("#D2521F", "#FBF9F6", 4.02),
        ("#FF8A5C", "#0D0F14", 8.25),
        ("B13F16", "FFFFFF", 5.85),
        ("#B13F16", "#F7F4EF", 5.33),
        ("#B13F16", "#EEE8DE", 4.80),
        ("#FF9B73", "#0C0F14", 9.31),
    ):
        check(
            "contrast_ratio(%r, %r) reproduces the audit's published %.2f" % (hex_a, hex_b, expected),
            _make_formula_check(hex_a, hex_b, expected))

    # ==================================================================
    # Section 2: live token-pair contrast — every real light/dark
    # text-on-surface pair companion/static/style.css actually uses for
    # normal text or a primary-button label meets WCAG AA. Hex literals
    # are hard-coded (not read from the CSS file), so a future
    # accidental token change is caught as a real regression, not
    # silently re-validated against its own new (possibly broken) value.
    # ==================================================================

    def _make_live_pair_check(label, fg, bg):
        def _check():
            ratio = contrast_ratio(fg, bg)
            if ratio < WCAG_AA_NORMAL_TEXT:
                return False, (
                    "%s: contrast_ratio(%r, %r) = %.2f, below WCAG_AA_NORMAL_TEXT (%.1f)"
                    % (label, fg, bg, ratio, WCAG_AA_NORMAL_TEXT))
            return True, ""
        return _check

    live_pairs = (
        # Light mode
        ("light: accent text/link on canvas", "#B13F16", "#F7F4EF"),
        ("light: accent on primary surface / active nav", "#B13F16", "#FFFFFF"),
        ("light: accent on secondary/sidebar surface", "#B13F16", "#EEE8DE"),
        ("light: primary-button label on accent fill", "#FFFFFF", "#B13F16"),
        ("light: body text on canvas", "#17191F", "#F7F4EF"),
        # 06.6.4-03 (D-04): every banner and card now renders text on
        # --color-dominant (the card surface), not just canvas/secondary
        # — pinned so a future token change fails here, not on inspection.
        ("light: body text on card surface", "#17191F", "#FFFFFF"),
        # Dark mode
        ("dark: accent text/link on canvas", "#FF8A5C", "#0C0F14"),
        ("dark: accent on primary surface", "#FF8A5C", "#151922"),
        ("dark: accent on secondary/sidebar surface", "#FF8A5C", "#1C222D"),
        ("dark: primary-button label on accent fill", "#151922", "#FF8A5C"),
        ("dark: body text on card surface", "#F1F3F6", "#151922"),
    )
    for label, fg, bg in live_pairs:
        check(
            "%s meets WCAG AA normal-text contrast (>= 4.5:1)" % label,
            _make_live_pair_check(label, fg, bg))

    # ==================================================================
    # Section 3: signal separation — --color-accent must be
    # distinguishable from every --color-status-* colour, in both
    # themes. See this module's docstring for why contrast checks alone
    # could not catch the accent/error collision this section exists to
    # prevent. Hex literals are hard-coded for the same reason as
    # Section 2: a token change must surface here as a regression, not
    # be silently re-validated against its own new value.
    # ==================================================================

    THEMES = (
        ("light", "#B13F16", {
            "ok": "#16A34A", "warn": "#D97706", "error": "#BE123C"}),
        ("dark", "#FF8A5C", {
            "ok": "#4ADE80", "warn": "#FBBF24", "error": "#FB7185"}),
    )

    def _make_distance_check(accent, status_hex):
        def _check():
            distance = perceptual_distance(accent, status_hex)
            if distance < MIN_SIGNAL_PERCEPTUAL_DISTANCE:
                return False, (
                    "perceptual_distance(%r, %r) = %.1f, below "
                    "MIN_SIGNAL_PERCEPTUAL_DISTANCE (%.1f) — these two read "
                    "as the same signal at a glance"
                    % (accent, status_hex, distance,
                       MIN_SIGNAL_PERCEPTUAL_DISTANCE))
            return True, ""
        return _check

    for theme, accent, statuses in THEMES:
        for status_name in ("ok", "warn", "error"):
            check(
                "%s: --color-accent is perceptually separated from "
                "--color-status-%s (dE76 >= %.0f)"
                % (theme, status_name, MIN_SIGNAL_PERCEPTUAL_DISTANCE),
                _make_distance_check(accent, statuses[status_name]))

    # The accent-vs-error pair additionally clears the hue floor. It is
    # the only pair held to this: accent and error are the same colour
    # family (both saturated red-oranges), so hue angle is the only
    # channel left to separate them — see MIN_SIGNAL_HUE_SEPARATION's
    # own comment in companion/contrast_check.py.
    def _make_hue_check(accent, status_hex):
        def _check():
            separation = hue_separation(accent, status_hex)
            if separation < MIN_SIGNAL_HUE_SEPARATION:
                return False, (
                    "hue_separation(%r, %r) = %.1f deg, below "
                    "MIN_SIGNAL_HUE_SEPARATION (%.1f deg)"
                    % (accent, status_hex, separation,
                       MIN_SIGNAL_HUE_SEPARATION))
            return True, ""
        return _check

    for theme, accent, statuses in THEMES:
        check(
            "%s: --color-accent and --color-status-error are hue-separated "
            "(>= %.0f deg)" % (theme, MIN_SIGNAL_HUE_SEPARATION),
            _make_hue_check(accent, statuses["error"]))

    # Discrimination guards. A threshold everything passes proves
    # nothing — these assert that the two floors above actually REJECT
    # the exact values that shipped the bug (#DC2626 light / #F87171
    # dark). If either of these four checks ever starts failing, the
    # floors have been loosened to the point of being decorative.
    SUPERSEDED_ERROR = (("light", "#B13F16", "#DC2626"),
                        ("dark", "#FF8A5C", "#F87171"))

    def _make_rejects_distance_check(accent, superseded):
        def _check():
            distance = perceptual_distance(accent, superseded)
            if distance >= MIN_SIGNAL_PERCEPTUAL_DISTANCE:
                return False, (
                    "the dE76 floor no longer rejects the superseded error "
                    "colour %r (dE76 %.1f vs floor %.1f) — the threshold has "
                    "been loosened past the defect it exists to catch"
                    % (superseded, distance, MIN_SIGNAL_PERCEPTUAL_DISTANCE))
            return True, ""
        return _check

    def _make_rejects_hue_check(accent, superseded):
        def _check():
            separation = hue_separation(accent, superseded)
            if separation >= MIN_SIGNAL_HUE_SEPARATION:
                return False, (
                    "the hue floor no longer rejects the superseded error "
                    "colour %r (%.1f deg vs floor %.1f deg)"
                    % (superseded, separation, MIN_SIGNAL_HUE_SEPARATION))
            return True, ""
        return _check

    for theme, accent, superseded in SUPERSEDED_ERROR:
        check(
            "%s: the dE76 floor rejects the superseded error colour %s "
            "(guard against a decorative threshold)" % (theme, superseded),
            _make_rejects_distance_check(accent, superseded))
        check(
            "%s: the hue floor rejects the superseded error colour %s "
            "(guard against a decorative threshold)" % (theme, superseded),
            _make_rejects_hue_check(accent, superseded))

    # --color-status-error is painted as a fill (.dot--error), a 3px top
    # border (.stat-tile--error), a 4px left edge (.banner--anomaly) and
    # an icon stroke (.stat-tile--error .stat-tile__icon) — all
    # non-text graphics, so WCAG_AA_UI_COMPONENT (3.0) is the applicable
    # bar, not 4.5. Worth pinning because the superseded #DC2626 scored
    # only 3.96 against these same light surfaces: it cleared this bar
    # but would have failed as text, a trap the replacement removes.
    SURFACES = {
        "light": ("#F7F4EF", "#FFFFFF", "#EEE8DE"),
        "dark": ("#0C0F14", "#151922", "#1C222D"),
    }

    def _make_error_signal_contrast_check(theme, error_hex):
        def _check():
            for surface in SURFACES[theme]:
                ratio = contrast_ratio(error_hex, surface)
                if ratio < WCAG_AA_UI_COMPONENT:
                    return False, (
                        "contrast_ratio(%r, %r) = %.2f, below "
                        "WCAG_AA_UI_COMPONENT (%.1f)"
                        % (error_hex, surface, ratio, WCAG_AA_UI_COMPONENT))
            return True, ""
        return _check

    for theme, _accent, statuses in THEMES:
        check(
            "%s: --color-status-error meets WCAG AA UI-component contrast "
            "(>= 3:1) on every %s surface" % (theme, theme),
            _make_error_signal_contrast_check(theme, statuses["error"]))

    # Formula fidelity for hue_separation()'s wrap-around, the one piece
    # of arithmetic in the new functions that is easy to get wrong: hue
    # is a circle, so a crimson near 350 and a red near 10 are 20 apart,
    # not 340. Without this the floors above would silently pass any
    # pair straddling 0.
    def _hue_separation_wraps_around_zero():
        for hex_a, hex_b, expected in (
                # Pure-channel fixtures only (0x00/0xFF), so every
                # expected value is exact and the check can never fail
                # on a rounding artefact instead of a real regression.
                ("#FF0000", "#FF0000", 0.0),      # identical, hue 0
                ("#FF0000", "#00FF00", 120.0),    # hue 0 vs 120
                ("#FF0000", "#00FFFF", 180.0),    # maximal, opposite
                ("#FF00FF", "#FF0000", 60.0),     # 300 vs 0 — crosses 0/360
                ("#FFFF00", "#FF00FF", 120.0),    # 60 vs 300 — crosses 0/360
        ):
            got = round(hue_separation(hex_a, hex_b), 1)
            if got != expected:
                return False, (
                    "hue_separation(%r, %r) = %.1f, expected %.1f"
                    % (hex_a, hex_b, got, expected))
        return True, ""
    check(
        "hue_separation() takes the shorter arc, including across the "
        "0/360 wrap point",
        _hue_separation_wraps_around_zero)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("contrast-check: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
