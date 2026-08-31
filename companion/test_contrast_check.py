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
    WCAG_AA_NORMAL_TEXT,
    contrast_ratio,
)

EXPECTED_CHECK_COUNT = 16


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
        # Dark mode
        ("dark: accent text/link on canvas", "#FF8A5C", "#0C0F14"),
        ("dark: accent on primary surface", "#FF8A5C", "#151922"),
        ("dark: accent on secondary/sidebar surface", "#FF8A5C", "#1C222D"),
    )
    for label, fg, bg in live_pairs:
        check(
            "%s meets WCAG AA normal-text contrast (>= 4.5:1)" % label,
            _make_live_pair_check(label, fg, bg))

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("contrast-check: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
