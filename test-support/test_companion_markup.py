"""Self-tests for companion_markup.py's HTML/CSS/JS structural parsers:
every idiom a companion test needs instead of grepping served source
text as a raw string.
"""

import pytest

from companion_markup import (
    at_rule_blocks,
    css_rules,
    custom_properties,
    declarations_for,
    keyframes,
    parse_html,
    rule_indices,
    rules_with_selector,
    strip_js_comments_and_strings,
)


# --- HTML --------------------------------------------------------------

_SAMPLE_HTML = '<div class="a b"><p id="x">Hi <b>there</b></p><br><img src=y></div>'


def test_select_descendant_combinator_returns_matching_text():
    root = parse_html(_SAMPLE_HTML)
    matches = root.select(".a p#x")
    assert len(matches) == 1
    assert matches[0].text() == "Hi there"


def test_find_all_reads_attrs():
    root = parse_html(_SAMPLE_HTML)
    imgs = root.find_all("img")
    assert imgs[0].attrs["src"] == "y"


def test_void_element_does_not_swallow_following_siblings():
    root = parse_html(_SAMPLE_HTML)
    div = root.find("div")
    # br and img are siblings of p under div, not children of br.
    tags_under_div = [c.tag for c in div.children if hasattr(c, "tag")]
    assert tags_under_div == ["p", "br", "img"]


def test_select_supports_class_id_attr_descendant_and_child_combinator():
    root = parse_html(
        '<div class="outer"><section><span class="target" data-x="1">a</span></section>'
        '<span class="target" data-x="2">b</span></div>'
    )
    assert len(root.select("div span")) == 2
    assert len(root.select("div > span")) == 1
    assert root.select("div > span")[0].attrs["data-x"] == "2"
    assert len(root.select("[data-x]")) == 2
    assert len(root.select('[data-x="1"]')) == 1
    assert len(root.select("#missing")) == 0


def test_select_unsupported_selector_raises_value_error():
    root = parse_html(_SAMPLE_HTML)
    with pytest.raises(ValueError):
        root.select(".a:hover")


def test_find_raises_lookup_error_when_absent():
    root = parse_html(_SAMPLE_HTML)
    with pytest.raises(LookupError):
        root.find("section")


# --- CSS -----------------------------------------------------------------

_CSS_MEDIA = (
    "a{color:red} /* } */ "
    "@media (max-width: 959.98px){ .x, .y > z { margin: 0 !important } }"
)

_CSS_SUPPORTS = (
    "@supports selector(:has(*)) { "
    ".c:has(input:checked) { border-color: var(--color-accent) } }"
)

_CSS_KEYFRAMES = "@keyframes k { from {opacity:0} to {opacity:1} }"


def test_css_rules_top_level_and_media_selectors_declarations_at_rules():
    rules = css_rules(_CSS_MEDIA)
    top_level = [r for r in rules if not r.at_rules]
    assert len(top_level) == 1
    assert top_level[0].selectors == ("a",)
    assert top_level[0].declarations == [("color", "red")]

    media_rules = [r for r in rules if r.at_rules]
    assert len(media_rules) == 1
    rule = media_rules[0]
    assert rule.selectors == (".x", ".y > z")
    assert rule.declarations == [("margin", "0 !important")]
    assert rule.at_rules == ("@media (max-width: 959.98px)",)


def test_css_rules_supports_block_with_pseudo_class_selector():
    rules = css_rules(_CSS_SUPPORTS)
    assert len(rules) == 1
    rule = rules[0]
    assert rule.selectors == (".c:has(input:checked)",)
    assert rule.declarations == [("border-color", "var(--color-accent)")]
    assert rule.at_rules == ("@supports selector(:has(*))",)


def test_css_rules_keyframes_not_returned_as_rules():
    rules = css_rules(_CSS_KEYFRAMES)
    assert rules == []


def test_keyframes_returns_names():
    assert keyframes(_CSS_KEYFRAMES) == {"k"}


def test_declarations_for_empty_without_matching_at_rules_context():
    assert declarations_for(_CSS_MEDIA, ".x") == {}


def test_declarations_for_with_matching_at_rules_context():
    assert declarations_for(
        _CSS_MEDIA, ".x", at_rules=("@media (max-width: 959.98px)",)
    ) == {"margin": "0 !important"}


def test_declarations_for_raises_key_error_for_absent_selector():
    with pytest.raises(KeyError):
        declarations_for(_CSS_MEDIA, ".totally-absent-anywhere")


def test_string_value_containing_semicolon_and_brace_does_not_split():
    css = '.p { content: "};" }'
    rules = css_rules(css)
    assert rules[0].declarations == [("content", '"};"')]


def test_custom_property_with_nested_parens_stays_intact():
    css = ":root { --a: color-mix(in srgb, var(--a) 70%, transparent); }"
    props = custom_properties(css, ":root")
    assert props["--a"] == "color-mix(in srgb, var(--a) 70%, transparent)"


def test_rules_with_selector_any_context():
    css = _CSS_MEDIA + " .x { color: blue }"
    matches = rules_with_selector(css, ".x")
    assert len(matches) == 2


def test_rule_indices_give_source_order_optionally_per_context():
    css = _CSS_MEDIA + " .x { color: blue } .later { color: green }"
    assert rule_indices(css, "a") == [0]
    assert rule_indices(css, ".x") == [1, 2]
    assert rule_indices(css, ".x", at_rules=()) == [2]
    assert rule_indices(css, ".x", at_rules=("@media (max-width: 959.98px)",)) == [1]
    assert rule_indices(css, ".later") == [3]
    assert rule_indices(css, ".absent") == []


def test_at_rule_blocks_keep_repeats_nesting_and_ignore_comments():
    css = (
        "/* @supports selector(:has(*)) { a { b: c } } */ "
        + _CSS_SUPPORTS + " " + _CSS_KEYFRAMES + " "
        + "@media (min-width: 960px) { @supports selector(:has(*)) { .d { e: f } } } "
        + _CSS_KEYFRAMES
    )
    assert at_rule_blocks(css) == [
        "@supports selector(:has(*))",
        "@keyframes k",
        "@media (min-width: 960px)",
        "@supports selector(:has(*))",
        "@keyframes k",
    ]
    assert at_rule_blocks("a { b: c }") == []


# --- JS --------------------------------------------------------------------

def test_strip_js_comments_and_strings():
    js = "var a = '//x'; // c\n/* d */ b = `t`;"
    stripped = strip_js_comments_and_strings(js)
    assert "var a = ;" in stripped
    assert "b = ;" in stripped
    assert "//x" not in stripped
    assert "// c" not in stripped
    assert "/* d */" not in stripped
    assert "`t`" not in stripped
