"""A modifier rule must not load before its base rule's sheet at equal specificity.

A page links the core sheet and then its area sheets (`companion/page_styles.py`).
When a base rule (`a.btn`) and its modifier (`a.btn--primary`) have the same
specificity, the later sheet wins on every property both set, so a modifier
in an earlier sheet than its base is silently overridden. The check walks the
SERVED sheets in each page family's link order.
"""
import re

import pytest

from companion import page_styles
from companion_app_server import get
from companion_markup import css_rules

_MODIFIER = re.compile(r"(\.[\w-]+?)--[\w-]+")
_ROUTES = tuple(page_styles._EXACT) + ("/display", "/unknown-page")


@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


def _sheet(server, href):
    status, _headers, body = get(server, href)
    assert status == 200, href
    return css_rules(body.decode("utf-8"))


def _declared_properties(rule):
    return {prop for prop, _value in rule.declarations}


def _misordered(sheets):
    """(modifier selector, base selector, modifier sheet, base sheet) for each
    modifier whose base rule sits in a later sheet and sets a shared property.
    `sheets` is a list of (href, rules) in link order."""
    bases = {}
    for index, (href, rules) in enumerate(sheets):
        for rule in rules:
            for selector in rule.selectors:
                bases.setdefault((selector, rule.at_rules), []).append(
                    (index, href, rule))
    found = set()
    for index, (href, rules) in enumerate(sheets):
        for rule in rules:
            for selector in rule.selectors:
                base = _MODIFIER.sub(r"\1", selector)
                if base == selector:
                    continue
                for base_index, base_href, base_rule in bases.get(
                        (base, rule.at_rules), ()):
                    if base_index > index and (
                            _declared_properties(rule) & _declared_properties(base_rule)):
                        found.add((selector, base, href, base_href))
    return sorted(found)


@pytest.mark.parametrize("route", _ROUTES)
def test_no_modifier_rule_loads_before_its_equal_specificity_base(_module_server, route):
    hrefs = ("/static/style.css",) + page_styles.area_hrefs(route)
    if route == "/unknown-page":
        hrefs = ("/static/style.css",) + page_styles.area_hrefs("/unknown-page")
    sheets = [(href, _sheet(_module_server, href)) for href in hrefs]
    problems = _misordered(sheets)
    assert not problems, (
        "a modifier rule loads before its base rule at equal specificity, so the "
        "base wins: %s" % "; ".join("%s (%s) before %s (%s)" % p for p in problems))


def test_the_guard_flags_a_modifier_in_an_earlier_sheet():
    rules = css_rules("a.x--on { color: red; }")
    base = css_rules("a.x { color: blue; }")
    assert _misordered([("core", rules), ("area", base)]) == [
        ("a.x--on", "a.x", "core", "area")]
    assert _misordered([("core", base), ("area", rules)]) == []
