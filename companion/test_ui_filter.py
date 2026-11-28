# SPDX-License-Identifier: AGPL-3.0-only
"""The shared count line of the Flights and Airlines filter controls."""
from companion import ui_filter


def test_the_count_line_is_one_status_paragraph():
    html = ui_filter.count_line_html("4 of 4 airlines", "# of # airlines")
    assert html == (
        '<p class="filter-count" data-filter-count role="status" '
        'data-filter-count-template="# of # airlines">4 of 4 airlines</p>')


def test_the_template_attribute_is_present_only_with_a_template():
    html = ui_filter.count_line_html("3 flights")
    assert "data-filter-count-template" not in html
    assert html.count("<p ") == 1 and html.count("data-filter-count") == 1


def test_text_and_template_are_inert_markup():
    hostile = '<b>&"x'
    html = ui_filter.count_line_html(hostile, hostile)
    assert "<b>" not in html
    assert 'data-filter-count-template="&lt;b&gt;&amp;&quot;x"' in html
    assert ">&lt;b&gt;&amp;&quot;x</p>" in html


def test_attrs_are_the_callers_literal_hook_and_stay_verbatim():
    html = ui_filter.count_line_html("1 flight", attrs=" data-flights-view")
    assert html == (
        '<p class="filter-count" data-filter-count data-flights-view role="status">1 flight</p>')
