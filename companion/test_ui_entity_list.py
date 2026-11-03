"""The shared entity list: helper markup contract and the served rules.
Browser behaviour of the list is asserted on the pages that adopt it."""
from companion import ui_entity_list as el
from companion_markup import parse_html

HOSTILE = '"><script>alert(1)</script>'


def _row(**overrides):
    args = dict(
        dot_html='<span class="dot dot--ok"></span>', title="Kitchen frame",
        subtitle="owner@example.com", pills_html="", action_html="<button>Go</button>",
        href="/devices/abc/")
    args.update(overrides)
    return parse_html(el.entity_list_html(el.entity_row_html(**args), el.count_line_html("1 frame")))


def test_row_has_dot_text_block_and_action_and_no_table():
    doc = _row()
    rows = doc.select("ul.entity-list li.entity-row")
    assert len(rows) == 1
    assert doc.select("li.entity-row .dot")
    link = doc.select_one("a.entity-row__title")
    assert link.attrs["href"] == "/devices/abc/" and link.text() == "Kitchen frame"
    assert doc.select_one(".entity-row__meta").text() == "owner@example.com"
    assert doc.select("li.entity-row button")
    assert doc.select_one("p.entity-count").text() == "1 frame"
    assert doc.select("table") == []


def test_row_without_href_or_dot():
    doc = _row(dot_html=None, href=None, subtitle=None)
    assert doc.select("span.entity-row__title")
    assert doc.select("a.entity-row__title") == []
    assert doc.select(".entity-row__meta") == []
    assert doc.select("li.entity-row--no-dot")


def test_hostile_title_subtitle_and_href_are_escaped():
    html = el.entity_row_html(None, HOSTILE, HOSTILE, "", "", href=HOSTILE)
    assert "<script>" not in html
    doc = parse_html(html)
    assert doc.select_one(".entity-row__title").text() == HOSTILE
    assert doc.select_one(".entity-row__meta").text() == HOSTILE


def test_menu_renders_label_and_three_items():
    html = el.row_menu_html(
        "Actions for " + HOSTILE,
        [("Open frame", "/devices/abc/", False),
         ("Reassign", "reassign-abc", False),
         ("Retire", "retire-abc", True)])
    assert "<script>" not in html
    doc = parse_html(html)
    summary = doc.select_one("details.row-menu summary")
    assert summary.attrs["aria-label"] == "Actions for " + HOSTILE
    items = doc.select("a.row-menu__item")
    assert [i.text() for i in items] == ["Open frame", "Reassign", "Retire"]
    assert "data-modal-open" not in items[0].attrs and items[0].attrs["href"] == "/devices/abc/"
    assert items[1].attrs["href"] == "#reassign-abc" and "data-modal-open" in items[1].attrs
    assert "row-menu__item--destructive" in items[2].attrs["class"]
