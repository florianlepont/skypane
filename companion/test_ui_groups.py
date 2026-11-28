# SPDX-License-Identifier: AGPL-3.0-only
"""The grouped-list components, asserted on the markup they produce and on the page that
uses them: one `<h2>` label per group, links and buttons only where a row acts, a control
beside (never inside) a link and no group inside a group."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import ui_groups
from companion_app_server import get, login
from companion_markup import parse_html


def _doc(markup):
    return parse_html("<main>%s</main>" % markup)


def test_a_plain_row_is_a_block_with_no_link_and_no_chevron():
    doc = _doc(ui_groups.group(ui_groups.row("Model", value_html="EE02"), label="Device"))
    row = doc.select_one("ul.group > li.row")
    assert row.attrs["class"] == "row"
    assert row.select_one("div.row__main") is not None
    assert row.select("a") == [] and row.select("button") == [] and row.select(".row__chevron") == []
    assert row.select_one(".row__value").text() == "EE02"


def test_a_link_row_is_one_link_with_a_chevron_and_a_button_row_one_button():
    link = _doc(ui_groups.group(ui_groups.row("Flights", icon="icon-plane", href="/flights")))
    row = link.select_one("li.row")
    assert "row--action" in row.attrs["class"].split()
    anchor = row.select_one("a.row__main")
    assert anchor.attrs["href"] == "/flights"
    assert anchor.select_one(".row__chip") is not None and anchor.select_one(".row__chevron")
    button = _doc(ui_groups.group(ui_groups.row("Edit", button_attrs='data-x="1"')))
    control = button.select_one("li.row > button.row__main")
    assert control.attrs["type"] == "button" and control.attrs["data-x"] == "1"
    assert button.select("a") == []


def test_a_trailing_control_sits_after_the_main_area_never_inside_a_link():
    markup = ui_groups.row("Screen", href="/x", trailing_html='<select><option>a</option></select>')
    row = _doc(ui_groups.group(markup)).select_one("li.row")
    assert row.select("a.row__main select") == []
    assert [c.tag for c in row.children if not isinstance(c, str)] == ["a", "select"]


def test_a_group_has_one_label_heading_and_no_group_inside_a_group():
    markup = ui_groups.group(ui_groups.row("A") + ui_groups.row("B"), label="Frame", label_id="g1")
    doc = _doc(markup)
    section = doc.select_one("section.group-block")
    assert section.attrs["aria-labelledby"] == "g1"
    assert [h.text() for h in section.select("h2.section-label")] == ["Frame"]
    assert len(section.select("ul.group > li.row")) == 2
    panel = _doc(ui_groups.group_panel("<p>x</p>", label="Panel", label_id="g2"))
    assert panel.select_one("div.group.group--panel p") is not None


def test_text_is_escaped():
    doc = _doc(ui_groups.group(ui_groups.row("<b>x</b>", detail="<i>y</i>"), label="<u>z</u>"))
    assert doc.select("b") == [] and doc.select("i") == [] and doc.select("u") == []


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_home_tile_variety)


@pytest.mark.parametrize("path", ["/"])
def test_home_is_one_column_of_blocks_with_no_group_nesting(server, path):
    """Home is the title block, the flight card, the pills, the statistics and the strip, in
    that order, each its own surface: no hero, no list group inside another surface"""
    status, _, body = get(server, path, cookie=login(server))
    assert status == 200
    doc = parse_html(body.decode("utf-8"))
    column = doc.select_one("main div.home")
    order = [
        (child.tag, child.attrs.get("class", "").split()[0])
        for child in column.children if not isinstance(child, str)]
    assert order == [
        ("section", "home-state"), ("div", "home-facts"), ("section", "home-flight"),
        ("section", "home-pills"), ("div", "home-stats"), ("section", "home-strip")]
    assert doc.select("main .group") == []
    labels = [h.text() for h in doc.select("main h2.home-strip__label")]
    assert labels == ["Recent flights"]
    assert len(doc.select("main h1")) == 1
    for anchor in doc.select("main a.home-pill--link"):
        assert anchor.attrs.get("href")
