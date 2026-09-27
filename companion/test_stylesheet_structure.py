"""Parser-based structural guards on the SERVED stylesheet: no selector declared in
more than one rule of the same at-rule context, and no colour literal outside a
custom-property definition.

Both checks parse `companion_app_server.served_stylesheet()`'s text with
`companion_markup.css_rules()` -- never a regex or substring search over the raw
stylesheet text (companion/test_suite_guards.py's G11).
"""
import re

import pytest

from companion_app_server import served_stylesheet
from companion_markup import css_rules


# --- module-scoped read-only server, for this served-CSS check only --------

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


def test_no_selector_is_declared_in_two_rules_of_one_context(css_text):
    """Every (selector, at_rules) pair `css_rules()` reports appears in exactly one
    rule -- a comma-separated selector list counts as one declaration site for each
    of its members, same as a single-selector rule. The failure message lists every
    duplicate with its count, not just the first.
    """
    counts = {}
    for rule in css_rules(css_text):
        for selector in rule.selectors:
            key = (selector, rule.at_rules)
            counts[key] = counts.get(key, 0) + 1

    duplicates = {key: count for key, count in counts.items() if count > 1}
    assert not duplicates, (
        "expected every selector to be declared in exactly one rule per at-rule "
        "context; found %d duplicate selector(s): %s"
        % (len(duplicates), ", ".join(
            "%r at %r (%d rules)" % (selector, at_rules, count)
            for (selector, at_rules), count in sorted(
                duplicates.items(), key=lambda item: -item[1]))))


# The CSS Color Module's extended named-colour keywords (the full standard set,
# excluding the CSS-wide/special keywords this check allows outright below) --
# checked against the parsed declaration VALUE, never the stylesheet text, so a
# comment or a class name mentioning a colour word can never trip this guard.
_NAMED_COLOURS = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black
blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse
chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
darkslateblue darkslategray darkslategrey darkturquoise darkviolet
deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray grey green
greenyellow honeydew hotpink indianred indigo ivory khaki lavender
lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
lightsalmon lightseagreen lightskyblue lightslategray lightslategrey
lightsteelblue lightyellow lime limegreen linen magenta maroon
mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
mediumslateblue mediumspringgreen mediumturquoise mediumvioletred
midnightblue mintcream mistyrose moccasin navajowhite navy oldlace
olive olivedrab orange orangered orchid palegoldenrod palegreen
paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown
salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato
turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())

# transparent/currentColor/inherit/initial/unset are the explicitly allowed
# non-token colour-shaped values a declaration may still carry outside a token.
_ALLOWED_KEYWORDS = frozenset({"transparent", "currentcolor", "inherit", "initial", "unset"})

_HEX_OR_FUNCTION_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z-]*")


def _colour_literal(value):
    """The first colour literal in a declaration VALUE: a #hex, an
    rgb()/rgba()/hsl()/hsla() call, or a named colour keyword other than the
    allowed set above. None when the value carries none. color-mix(...) built from
    var(--color-*) is not a literal -- its own arguments are custom-property
    references, and "mix"/"srgb"/"in" are not colour keywords.
    """
    match = _HEX_OR_FUNCTION_RE.search(value)
    if match:
        return match.group(0)
    for word_match in _WORD_RE.finditer(value):
        word = word_match.group(0).lower()
        if word in _NAMED_COLOURS and word not in _ALLOWED_KEYWORDS:
            return word_match.group(0)
    return None


def test_no_colour_literal_outside_the_token_definitions(css_text):
    """No declaration outside a custom-property (--*) definition carries a colour
    literal. The failure message lists every offending (selector, at_rules,
    property, value), not just the first.
    """
    offenders = []
    for rule in css_rules(css_text):
        for prop, value in rule.declarations:
            if prop.startswith("--"):
                continue
            literal = _colour_literal(value)
            if literal:
                offenders.append((rule.selectors, rule.at_rules, prop, value, literal))

    assert not offenders, (
        "expected no colour literal outside a custom-property definition; found "
        "%d offending declaration(s): %s"
        % (len(offenders), ", ".join(
            "%r at %r: %s: %r (literal %r)" % (selectors, at_rules, prop, value, literal)
            for selectors, at_rules, prop, value, literal in offenders)))
