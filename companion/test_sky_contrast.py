"""The background and motion language on the SERVED stylesheet: every text colour stays readable
against every stop of the pale Light sky and of the Dark ink gradient both directly on the page and through the frosted-glass surfaces, the
glass has a solid fallback outside its @supports block, and the single reduced-motion rule
covers the entrance animation's duration and delay."""
import re

import pytest

from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio
from companion_app_server import served_stylesheet
from companion_markup import css_rules, custom_properties

_DARK_AT_RULE = ("@media (prefers-color-scheme: dark)",)
_SKY_STOPS = ("--sky-top", "--sky-mid", "--sky-bottom")
_RGBA_RE = re.compile(
    r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)")
_INKS = ("--color-text", "--color-accent")
_RARITY_INKS = ("--color-rarity-occasional", "--color-rarity-rare")


@pytest.fixture(scope="module")
def served_css(module_app_server_factory):
    return served_stylesheet(module_app_server_factory())


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(round(channel) for channel in rgb)


def _channels(hex_colour):
    stripped = hex_colour.lstrip("#")
    return tuple(int(stripped[i:i + 2], 16) for i in (0, 2, 4))


def _over(glass, backdrop_hex):
    """The opaque colour of an rgba() token painted over an opaque backdrop."""
    match = _RGBA_RE.fullmatch(glass.strip())
    assert match, "expected an rgba() glass token, got %r" % (glass,)
    red, green, blue, alpha = (float(group) for group in match.groups())
    back = _channels(backdrop_hex)
    return _hex(tuple(alpha * fg + (1 - alpha) * bg
                      for fg, bg in zip((red, green, blue), back)))


def _themes(served_css):
    """(label, tokens): the cascade each theme actually produces, resolved the way the browser
    does (explicit Light and the dark blocks override the light :root)."""
    light = custom_properties(served_css, ":root")
    light_explicit = dict(light, **custom_properties(served_css, 'html[data-ui-theme="light"]'))
    dark_auto = dict(light, **custom_properties(served_css, ":root", at_rules=_DARK_AT_RULE))
    dark_explicit = dict(light, **custom_properties(served_css, 'html[data-ui-theme="dark"]'))
    return [("light", light), ("light-explicit", light_explicit),
            ("dark-auto", dark_auto), ("dark-explicit", dark_explicit)]


def test_every_theme_declares_its_three_stops(served_css):
    for label, tokens in _themes(served_css):
        for stop in _SKY_STOPS:
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", tokens.get(stop, "")), (
                "%s declares no hex %s" % (label, stop))


def test_there_is_one_pale_sky_and_one_ink_background(served_css):
    """Light is a gentle pale gradient, Dark an ink gradient; Auto + dark and explicit Dark agree,
    and no time-of-day sky is left in the stylesheet"""
    by_label = dict(_themes(served_css))
    for label in ("light", "light-explicit"):
        assert [by_label[label][stop].upper() for stop in _SKY_STOPS] == [
            "#E7EEF7", "#F1F3F6", "#F6F3EE"], label
    for label in ("dark-auto", "dark-explicit"):
        assert [by_label[label][stop].upper() for stop in _SKY_STOPS] == [
            "#12151D", "#161A24", "#1A1F2B"], label
    selectors = [sel for rule in css_rules(served_css) for sel in rule.selectors]
    assert not [sel for sel in selectors if "data-sky" in sel or sel.startswith("html::")]


def test_the_accent_is_graphite_in_light_and_ivory_in_dark(served_css):
    by_label = dict(_themes(served_css))
    for label in ("light", "light-explicit"):
        assert by_label[label]["--color-accent"].upper() == "#1F2430"
        assert by_label[label]["--color-on-accent"].upper() == "#FFFFFF"
    for label in ("dark-auto", "dark-explicit"):
        assert by_label[label]["--color-accent"].upper() == "#F2EFE9"
        assert by_label[label]["--color-on-accent"].upper() == "#14171F"


def test_filled_controls_and_focus_rings_stay_accessible_over_every_background(served_css):
    """the label on a filled accent control reaches 4.5:1; the accent as a focus ring and as a
    toggle/icon fill reaches 3:1 over every stop of the page background and over the glass"""
    failures = []
    for label, tokens in _themes(served_css):
        for hover in ("--color-accent", "--color-accent-hover"):
            ratio = contrast_ratio(tokens["--color-on-accent"], tokens[hover])
            if ratio < WCAG_AA_NORMAL_TEXT:
                failures.append("%s on-accent over %s = %.2f" % (label, hover, ratio))
        for stop in _SKY_STOPS:
            for surface, background in _surfaces(tokens, tokens[stop]):
                ratio = contrast_ratio(tokens["--color-accent"], background)
                if ratio < 3.0:
                    failures.append("%s ring over %s %s = %.2f" % (label, surface, stop, ratio))
    assert not failures, failures


def _surfaces(tokens, stop_hex):
    """Every surface a text colour can sit on for this sky stop: the bare sky, the card glass,
    and the bar glass painted over it."""
    return (
        ("sky", stop_hex),
        ("glass", _over(tokens["--glass-bg"], stop_hex)),
        ("glass bar", _over(tokens["--glass-bar-bg"], stop_hex)),
    )


def test_text_and_accent_stay_readable_over_every_sky_and_glass(served_css):
    failures = []
    for label, tokens in _themes(served_css):
        for stop in _SKY_STOPS:
            for surface, background in _surfaces(tokens, tokens[stop]):
                for ink in _INKS:
                    ratio = contrast_ratio(tokens[ink], background)
                    if ratio < WCAG_AA_NORMAL_TEXT:
                        failures.append("%s %s: %s on %s %s = %.2f"
                                        % (label, stop, ink, surface, background, ratio))
    assert not failures, failures


def test_rarity_inks_stay_readable_on_glass_over_every_sky(served_css):
    failures = []
    for label, tokens in _themes(served_css):
        for stop in _SKY_STOPS:
            for surface, background in _surfaces(tokens, tokens[stop])[1:]:
                for ink in _RARITY_INKS:
                    ratio = contrast_ratio(tokens[ink], background)
                    if ratio < WCAG_AA_NORMAL_TEXT:
                        failures.append("%s %s: %s on %s = %.2f"
                                        % (label, stop, ink, surface, ratio))
    assert not failures, failures


def _supports_rules(served_css):
    return [rule for rule in css_rules(served_css)
            if len(rule.at_rules) == 1 and rule.at_rules[0].startswith("@supports")
            and "backdrop-filter" in rule.at_rules[0]]


def test_glass_applies_only_inside_supports_and_keeps_a_solid_base(served_css):
    """every glass selector paints a translucent --glass-* fill only inside the backdrop-filter
    @supports block, and its own base rule (outside the @supports block, in a width @media where the bars live) keeps a solid fill token, so a
    browser without backdrop-filter shows the solid surface"""
    rules = _supports_rules(served_css)
    assert rules, "the glass block is missing"
    for rule in rules:
        assert "backdrop-filter" in rule.at_rules[0]
    base_backgrounds = {}
    for rule in css_rules(served_css):
        if any(at_rule.startswith("@supports") for at_rule in rule.at_rules):
            continue
        for prop, value in rule.declarations:
            if prop == "background":
                for selector in rule.selectors:
                    base_backgrounds.setdefault(selector, set()).add(value)
    glass_selectors = []
    for rule in rules:
        background = dict(rule.declarations).get("background")
        assert background in ("var(--glass-bg)", "var(--glass-bar-bg)"), rule.selectors
        for selector in rule.selectors:
            glass_selectors.append(selector)
            assert base_backgrounds.get(selector, set()) & {
                "var(--color-dominant)", "var(--color-secondary)"}, (
                "%s has no solid base fill outside @supports: %r"
                % (selector, base_backgrounds.get(selector)))
    for selector in (".dashboard-sidebar", ".tab-bar", ".site-header", ".page-section",
                     ".home-state", "dialog.modal"):
        assert selector in glass_selectors, selector
    blurred = [rule for rule in rules if "backdrop-filter" in dict(rule.declarations)]
    assert 0 < sum(len(rule.selectors) for rule in blurred) <= 10, (
        "backdrop-filter must stay on a bounded number of large surfaces")
    assert not [rule for rule in css_rules(served_css) if not rule.at_rules
                and "backdrop-filter" in dict(rule.declarations)]


def test_the_background_is_painted_on_the_root_element_itself(served_css):
    """the gradient lives on <html> (so the Safari bars and the overscroll area show it), covers
    a short page, and uses neither a fixed layer nor background-attachment: fixed"""
    declarations = {}
    for rule in css_rules(served_css):
        if rule.selectors == ("html",) and not rule.at_rules:
            declarations.update(dict(rule.declarations))
    assert declarations["min-height"] == "100%"
    assert "var(--sky-top)" in declarations["background-image"]
    assert "var(--sky-bottom)" in declarations["background-image"]
    assert declarations["background-color"] == "var(--color-canvas)"
    assert not [rule for rule in css_rules(served_css)
                if dict(rule.declarations).get("background-attachment") == "fixed"]


def test_one_reduced_motion_rule_zeroes_duration_and_delay_of_every_animation(served_css):
    reduce_rules = [rule for rule in css_rules(served_css)
                    if rule.at_rules == ("@media (prefers-reduced-motion: reduce)",)
                    and "*" in rule.selectors]
    assert len(reduce_rules) == 1
    declared = dict(reduce_rules[0].declarations)
    assert declared["animation-duration"] == "0.01ms !important"
    assert declared["animation-delay"] == "0s !important"
    assert declared["transition-duration"] == "0.01ms !important"


def test_overlays_tables_and_empty_states_take_the_glass_inside_the_support_block(served_css):
    """the lightbox and the save bar, the tables and empty states that sit on the sky, and the
    placeholder ink are tokens-only; the glass lives inside the backdrop-filter support block"""
    rules = css_rules(served_css)
    glass = {sel for rule in rules if dict(rule.declarations).get("background") == "var(--glass-bg)"
             for sel in rule.selectors}
    for selector in (".lightbox", ".airlines-table", ".dashboard-main > .empty-state"):
        assert selector in glass, selector
    bar = {sel for rule in rules if dict(rule.declarations).get("background") == "var(--glass-bar-bg)"
           for sel in rule.selectors}
    assert ".dirty-bar" in bar
    placeholder = [dict(rule.declarations) for rule in rules if "::placeholder" in rule.selectors]
    assert any(d.get("color", "").startswith("color-mix(") and d.get("opacity") == "1"
               for d in placeholder)


def test_the_entrance_never_fills_forwards(served_css):
    """fill-mode backwards only: once the entrance ends the element is back in its plain layout
    state and holds no stacking context that could trap a dropdown"""
    for rule in css_rules(served_css):
        for prop, value in rule.declarations:
            if prop == "animation" and "skypane-reveal" in value:
                assert "backwards" in value and "forwards" not in value and "both" not in value
                assert "infinite" not in value


def test_tab_bar_labels_stay_readable_over_any_content_scrolling_beneath(served_css):
    """page content scrolls under the bars, so the bar glass must keep the label ink at 4.5:1
    over the worst content there can be (white picture, black picture) and over every sky"""
    failures = []
    for label, tokens in _themes(served_css):
        for backdrop in ("#FFFFFF", "#000000", tokens["--sky-top"], tokens["--sky-bottom"]):
            bar = _over(tokens["--glass-bar-bg"], backdrop)
            ratio = contrast_ratio(tokens["--color-text"], bar)
            if ratio < WCAG_AA_NORMAL_TEXT:
                failures.append("%s over %s: %.2f" % (label, backdrop, ratio))
    assert not failures, failures
