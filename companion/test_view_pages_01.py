"""Part 01 of the `companion/test_view_pages.py` migration chain
(33-05-PLAN.md): the original harness's check() calls #1-#37, covering
`companion/pages/history_page.py`'s empty state, newest-first ordering,
the reused render-module presentation mappings, monospace/escaping
contracts, the merged When/Flight cells, the Corroboration column's
agreement with `health_page.py`, the filter bar, and the per-row
disclosure (summary row <-> sibling detail row) pairing.

Every check calls `history_page.render()` directly (never over HTTP) with
a `tmp_path`-backed state directory seeded through
`server.history_db`'s own writer functions — no `Harness` subprocess is
needed for this slice. The four checks that used to open
`companion/static/style.css` from disk instead fetch it from a running
`companion/app.py` (`module_app_server_factory` + `served_stylesheet()`)
and assert on `companion_markup.css_rules()`/`declarations_for()`.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion.pages import history_page
from companion_app_server import served_stylesheet
from companion_markup import css_rules, parse_html
from server import device_config
from server.plane import render as panel_render


@pytest.fixture(scope="module")
def served_css(module_app_server_factory):
    """The stylesheet companion/app.py actually serves (the 4 checks in
    this module that used to read companion/static/style.css from disk
    instead fetch it once, read-only, from a running server)."""
    server = module_app_server_factory()
    return served_stylesheet(server)


# ======================================================================
# Section 1: companion/pages/history_page.py
# ======================================================================


def test_empty_database_renders_empty_state_no_table(tmp_path):
    """an empty database renders the flight-history empty-state copy and no <table"""
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert history_page._NO_FLIGHTS_HEADING in rendered
    assert "<table" not in rendered


def test_three_events_render_newest_first(tmp_path):
    """three seeded runway events render one row each, newest first"""
    events = [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "bbb222", "callsign": "FLT2"},
        {"ts": "2026-08-27T10:02:00+00:00", "hex": "ccc333", "callsign": "FLT3"},
    ]
    vp.seed_runway_events(tmp_path, events)
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    # 21-03-PLAN.md Task 2 (D-15): each summary row carries a sibling
    # .flight-detail-row <tr> - 1 header + 3 summary + 3 detail = 7.
    # 22-09-PLAN.md Task 2 (X5): +1 day-separator row - all three fixture
    # events fall on the same Europe/Paris day: 7 + 1 = 8.
    assert len(doc.select("tr")) == 8
    assert len(doc.select('[class="flight-day-row"]')) == 1
    idx3, idx2, idx1 = rendered.find("FLT3"), rendered.find("FLT2"), rendered.find("FLT1")
    assert idx3 < idx2 < idx1, "expected newest-first ordering (FLT3, FLT2, FLT1)"


def test_known_aircraft_type_friendly_label(tmp_path):
    """a known aircraft-type designator renders its friendly label (case-insensitive)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d1", "aircraft_type": "b738"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    expected_label = panel_render._TYPE_DISPLAY_LABELS["B738"]
    assert expected_label in rendered


def test_unknown_aircraft_type_raw_designator(tmp_path):
    """an aircraft type absent from the display-label table renders the raw designator, not an empty cell"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d2", "aircraft_type": "ZZZZ"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert "ZZZZ" in rendered


def test_no_airline_no_route_matches_render_fallback(tmp_path):
    """a row with no airline and no route renders the same fallback wording server.plane.render.py uses (read from the module)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d3", "callsign": "NOROUTE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    # Read the expected string from the render module itself, never a
    # literal, so the History page and the panel cannot silently drift.
    assert panel_render.ROUTE_FALLBACK_TEXT in rendered


def test_mono_columns_present(tmp_path):
    """timestamp, callsign and hex columns carry monospace CSS classes"""
    # The merged Callsign+Hex cell's monospace treatment lives on the
    # cell-primary/cell-secondary span classes (both mono in style.css),
    # not on a td[class="mono"] attribute - Timestamp is the one
    # remaining exact class="mono" cell.
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "abc123", "callsign": "MONO1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    assert len(doc.select('[class="mono"]')) >= 1
    assert doc.select('[class="%s"]' % history_page.CELL_PRIMARY_CLASS)
    assert doc.select('[class="%s"]' % history_page.CELL_SECONDARY_CLASS)


def test_hostile_callsign_escaped(tmp_path):
    """a callsign containing angle brackets renders escaped"""
    hostile = "<script>alert(1)</script>"
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d4", "callsign": hostile},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert hostile not in rendered
    assert "&lt;script&gt;" in rendered


def test_unreadable_db_degrades_without_raising(tmp_path):
    """a state directory that cannot hold a database renders the health-unavailable copy without raising"""
    blocked_state_dir = tmp_path / "blocked"
    blocked_state_dir.write_text("this is a file, not a directory")
    rendered = history_page.render(vp.history_ctx(blocked_state_dir))
    assert history_page._HISTORY_UNAVAILABLE_TEXT in rendered


def test_history_page_never_imports_html_module_directly():
    """companion/pages/history_page.py never imports the stdlib html module directly"""
    import html as stdlib_html
    assert getattr(history_page, "html", None) is not stdlib_html


def test_history_page_never_redefines_type_display_labels_locally():
    """companion/pages/history_page.py never redefines _TYPE_DISPLAY_LABELS locally"""
    assert not hasattr(history_page, "_TYPE_DISPLAY_LABELS")


def test_history_opens_with_shared_page_header(tmp_path):
    """History opens with the shared layout.page_header() component, not a bare <h1>"""
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    h1s = doc.select("h1")
    assert any(
        h.attrs.get("class") == "page-title" and h.text() == "Flights" for h in h1s)
    assert not doc.select('[class="text-heading"]')


def test_history_table_wrapped_for_horizontal_scroll_dot_survives(tmp_path):
    """History's flight table gains the .data-table-wrap horizontal-scroll wrapper Airlines/Health already have, without disturbing the Corroboration status dot"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d5", "callsign": "WRAP1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    assert doc.select('[class="data-table-wrap"]')
    # 21-03-PLAN.md Task 1 (D-15): the scoped data-table--flights modifier.
    # find_all()'s attrs= does an exact-string match without the
    # selector-syntax tokenizer, which would otherwise split this
    # attribute value on its embedded space.
    assert doc.find_all("table", attrs={"class": "data-table data-table--flights"})
    assert any("dot--" in (n.attrs.get("class") or "") for n in doc.select("*"))


def test_six_columns_named_and_ordered(tmp_path):
    """History renders exactly the 5 data headers in history_page._HEADERS plus a sixth, visually-hidden 'Details' toggle-column header, all in order, with no standalone Hex/Airline/Runway/Type/Callsign/Timestamp column (21-03-PLAN.md Task 1, D-15)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d6", "callsign": "SEVEN1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    # A bare <th> (no attributes) only - the day-separator row's own
    # <th scope="colgroup" colspan="6"> is a different column-header kind
    # entirely (a whole-row caption, not a data/toggle column) and must
    # not be counted here, exactly as the original's literal "<th>"
    # substring match never matched it either.
    ths = [th for th in doc.select("th") if not th.attrs]
    assert len(ths) == 6, "expected exactly 6 <th> cells (5 data + 1 toggle)"
    for th, header in zip(ths[:5], history_page._HEADERS):
        assert th.text() == header
    details_th = ths[5]
    assert details_th.select('[class="visually-hidden"]')
    assert details_th.text() == "Details"


def test_runway_survives_in_row_title_and_mobile_details(tmp_path):
    """the runway value the dropped desktop Runway column used to show survives in the <tr title="..."> attribute and, unchanged, in the mobile card's More details (A-36/D-19)"""
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": "rwt01",
            "callsign": "RWTITLE", "tracked_runway": "3",
        },
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    runway_label = device_config.runway_label("3")
    tr_block = vp.row_block(rendered, "tr", 0)
    li_block = vp.row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None
    assert tr_block.attrs.get("title") == runway_label
    dts = li_block.select("dt")
    dds = li_block.select("dd")
    idx = next(i for i, dt in enumerate(dts) if dt.text() == "Runway")
    assert dds[idx].text() == runway_label


def test_scroller_focusable_and_named(tmp_path):
    """the .data-table-wrap scroller is focusable (tabindex="0") and carries a non-empty aria-label naming what it scrolls (A-36/D-19)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "scr01", "callsign": "SCROLL1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    wrap = doc.select_one('[class="data-table-wrap"]')
    assert wrap.attrs.get("tabindex") == "0"
    assert wrap.attrs.get("role") == "region"
    assert wrap.attrs.get("aria-label")


def test_desktop_when_cell_clock_primary_relative_age_secondary(tmp_path):
    """the desktop When cell shows a local clock primary line plus a STACKED relative-age secondary line, with no title attribute carrying the full ISO string any more (21-03-PLAN.md Task 1, D-15)"""
    raw_ts = "2026-08-27T10:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": raw_ts, "hex": "clk01", "callsign": "CLOCK1"},
    ])
    now = "2026-08-27T10:05:00+00:00"
    rendered = history_page.render(vp.history_ctx(tmp_path, now=now))
    tr_block = vp.row_block(rendered, "tr", 0)
    assert tr_block is not None
    assert not any(n.attrs.get("title") == raw_ts for n in tr_block.select("*"))
    assert "5m ago" in tr_block.text()
    when_cell = tr_block.select("td")[0]
    assert when_cell.select_one('[class="cell-primary"]').text() == "12:00"
    assert when_cell.select_one('[class="cell-secondary"]').text() == "5m ago"


def test_merged_flight_cell_carries_callsign_airline_and_type(tmp_path):
    """the Flight cell's callsign and its airline/aircraft-type secondary line both appear inside the same <td>, and the hex value is not visible in the desktop table (21-03-PLAN.md Task 1, D-15)"""
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": "39d301",
            "callsign": "AFR123", "aircraft_type": "A320", "airline": "AFR",
        },
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    expected_type_label = panel_render._TYPE_DISPLAY_LABELS.get("A320", "A320")
    expected_airline_label = panel_render.display_airline_name("AFR")
    for value in ("AFR123", expected_type_label, expected_airline_label):
        assert value in rendered
    doc = parse_html(rendered)
    tbody_tds = doc.select("tbody td")
    flight_td = next(td for td in tbody_tds if "AFR123" in td.text())
    assert expected_airline_label in flight_td.text()
    assert expected_type_label in flight_td.text()
    assert "39d301" not in flight_td.text()


def test_merged_cells_stay_one_line(tmp_path):
    """the merged Callsign/Hex and Type/Airline cells stay on one line - no <br>, no block-level child"""
    # Row-height contract (data-density.md's "What to Avoid"): scoped to
    # the SUMMARY row only (21-03-PLAN.md Task 2, D-15) - the sibling
    # .flight-detail-row legitimately carries a <dl>/<div> grid.
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d7", "callsign": "LINE1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    summary_tr = doc.select_one('tr[class="row"]')
    assert not summary_tr.select("br")
    assert not summary_tr.select("div")
    assert not summary_tr.select("p")


def test_merged_cell_hostile_values_escaped(tmp_path):
    """hostile values in both merged cells (Callsign/Hex, Type/Airline) render escaped"""
    hostile_callsign = '<b>AFR"1</b>'
    hostile_hex = '<i>39"d</i>'
    hostile_type = '<u>A32"0</u>'
    hostile_airline = '<s>AFR"L</s>'
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": hostile_hex,
            "callsign": hostile_callsign, "aircraft_type": hostile_type,
            "airline": hostile_airline,
        },
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    for raw in (hostile_callsign, hostile_hex, hostile_type, hostile_airline):
        assert raw not in rendered
    assert "&lt;" in rendered


def test_merged_cell_classes_agree_with_stylesheet(tmp_path, served_css):
    """history_page's CELL_PRIMARY_CLASS/CELL_SECONDARY_CLASS/CELL_SEPARATOR_CLASS all appear in style.css and in the rendered page"""
    rules = css_rules(served_css)
    for name in (
        history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
        history_page.CELL_SEPARATOR_CLASS,
    ):
        assert any(name in sel for rule in rules for sel in rule.selectors), (
            "class %r is emitted by history_page but not styled in style.css" % name)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "d8", "callsign": "CLS1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    for name in (
        history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
        history_page.CELL_SEPARATOR_CLASS,
    ):
        assert doc.select('[class="%s"]' % name), (
            "expected class %r to appear in the rendered History page" % name)
