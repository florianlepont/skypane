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

import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
from companion.pages import health_page, history_page
from companion_app_server import served_stylesheet
from companion_markup import css_rules, declarations_for, parse_html
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


def test_timestamp_column_absolute_and_relative(tmp_path):
    """History's Timestamp column/mobile primary line read through layout.concise_timestamp_html(), format_event_row() degrades gracefully with one argument or a missing timestamp, and render() falls back when ctx carries no 'now' key"""
    seeded_ts = "2026-08-28T13:58:02+00:00"
    three_min_later = "2026-08-28T14:01:02+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": seeded_ts, "hex": "d9", "callsign": "TS1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, now=three_min_later))
    expected = layout.concise_timestamp_html(seeded_ts, three_min_later)
    assert expected in rendered

    # A one-argument format_event_row() call degrades to the raw stored
    # timestamp, unchanged.
    one_arg = history_page.format_event_row({"ts": seeded_ts})
    assert one_arg["ts"] == seeded_ts

    # A row with no stored timestamp produces an empty Timestamp cell.
    no_ts = history_page.format_event_row({}, three_min_later)
    assert no_ts["ts"] == ""

    # render(ctx) with no "now" key still renders without raising and
    # still shows a relative suffix (falls back to
    # history_db.utc_now_iso()).
    rendered_no_now = history_page.render({"state_dir": str(tmp_path)})
    doc = parse_html(rendered_no_now)
    times = doc.select("time[data-relative]")
    assert any(t.text().endswith(" ago") for t in times), (
        "expected a relative-age suffix even when ctx carries no 'now' key")


def test_history_timestamps_carry_a_relative_time_element(tmp_path):
    """History's Timestamp cells carry layout.concise_timestamp_html()'s new <time data-relative> element through data_table()'s raw_columns — as real markup, never double-escaped — with its text and its instant both intact (23-03, D14/CFG-34)"""
    seeded_ts = "2026-08-28T13:58:02+00:00"
    three_min_later = "2026-08-28T14:01:02+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": seeded_ts, "hex": "d9", "callsign": "TS1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, now=three_min_later))
    doc = parse_html(rendered)
    # 23-08-PLAN.md Task 1: Flights joined the refresh loop, so the
    # header now carries its own <time data-relative> freshness clock -
    # narrow the search to the card list so this check keeps measuring
    # the ROW's own age, not the header's render-instant clock.
    assert doc.select("[data-refresh-clock]")
    cards = doc.select_one('[class="history-cards"]')
    assert not cards.select("[data-refresh-clock]")
    times = cards.select("time[data-relative]")
    assert times, "expected a <time data-relative> element in the rendered History row list"
    match = times[0]
    assert "&lt;time" not in rendered
    assert match.text() == layout.relative_age_text(
        layout.age_seconds(seeded_ts, three_min_later))
    assert layout.age_seconds(match.attrs.get("datetime"), three_min_later) == 180


def test_corroboration_copy_agrees_with_health_page():
    """history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS on status key-by-key and on visible label for True/False; History's shortened 'None' label is the documented short form and its _CORROBORATION_TITLES tooltip equals Health's own full label exactly; the single-source 'None' state is pinned by name on each side (History 'ok', Health the neutral 'off'), is never a failure in either table, and carries a visible label distinct from 'Both agree' (quick task 260902-w4t UIR-04, retargeted by 22-12-PLAN.md Task 1's X8)"""
    health_rows = {
        stored: (status, label)
        for stored, label, status, _explanation in health_page._CORROBORATION_ROWS
    }
    history_labels = history_page._CORROBORATION_LABELS
    history_titles = history_page._CORROBORATION_TITLES

    assert set(health_rows) == {"True", "None", "False"}
    assert set(history_labels) == {"True", "None", "False"}

    # Statuses must agree key-by-key for True and False - History's
    # desktop table deliberately keeps "ok" for None (21-UI-SPEC/D-15),
    # while Health's None moved to the neutral "off" token (22-UI-SPEC.md
    # §5 contract 4), so that key is pinned by name below instead.
    for key in ("True", "False"):
        assert history_labels[key][0] == health_rows[key][0]
        assert history_labels[key][1] == health_rows[key][1]

    assert history_labels["None"][1] == "Single-source"
    assert history_titles.get("None") == health_rows["None"][1]

    assert history_labels["None"][0] == "ok"
    assert health_rows["None"][0] == "off"
    for status in (history_labels["None"][0], health_rows["None"][0]):
        assert status not in ("warn", "error")
    # X8's own safety clause: colour is not the only signal.
    assert health_rows["None"][1] != health_rows["True"][1]


def test_status_dot_title_backward_compatible_and_escaped():
    """layout.status_dot()'s 2-arg output is unchanged, an explicit title=None is byte-identical to omitting it, and a truthy title renders as an escaped title attribute (quick task 260902-w4t, UIR-04)"""
    two_arg = layout.status_dot("ok", "All good")
    assert "title=" not in two_arg
    three_arg_equivalent = layout.status_dot("ok", "All good", None)
    assert three_arg_equivalent == two_arg
    titled = layout.status_dot("ok", "All good", "Long form")
    assert 'title="Long form"' in titled
    hostile = layout.status_dot("ok", "All good", "<script>evil()</script>")
    assert "<script>" not in hostile
    assert "&lt;script&gt;" in hostile


def test_status_dot_visually_hide_label_defaults_false_byte_identical():
    """layout.status_dot()'s visually_hide_label keyword defaults to False with a byte-identical return value, and True adds the visually-hidden class to the label span while leaving its text/title unchanged (21-03-PLAN.md Task 1, D-15)"""
    without_keyword = layout.status_dot("ok", "All good", "A tooltip")
    explicit_false = layout.status_dot("ok", "All good", "A tooltip", visually_hide_label=False)
    assert explicit_false == without_keyword
    assert 'class="dot-label"' in without_keyword
    hidden = layout.status_dot("ok", "All good", "A tooltip", visually_hide_label=True)
    assert 'class="dot-label visually-hidden"' in hidden
    assert 'title="A tooltip"' in hidden
    assert ">All good<" in hidden


def test_corroboration_none_row_shows_short_label_with_tooltip(tmp_path):
    """a 'None' (single-source) row's Corroboration cell shows the short visible label with the long form only in a title attribute, in both the desktop and mobile renderings (quick task 260902-w4t, UIR-04)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "cn01", "callsign": "CORNONE",
         "corroborated": None},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = vp.row_block(rendered, "tr", 0)
    li_block = vp.row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None
    long_form = history_page._CORROBORATION_TITLES["None"]
    for block in (tr_block, li_block):
        # find_all(cls=...) does token membership, so this matches the
        # desktop span's "dot-label visually-hidden" as well as the
        # mobile card's plain "dot-label".
        label_node = block.find_all("span", cls="dot-label")[0]
        assert label_node.text() == "Single-source"
        assert any(n.attrs.get("title") == long_form for n in block.select("*"))
        assert "(uncorroborated)" not in block.text()


def test_desktop_corroboration_cell_dot_only_no_visible_word(tmp_path):
    """the desktop Corroboration cell renders the dot only, with the visible word hidden via visually-hidden (not deleted); the mobile card's own Corroboration <dd> still shows the word (21-03-PLAN.md Task 1, D-15/D-16)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "cdo01", "callsign": "CDOTONLY",
         "corroborated": "True"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = vp.row_block(rendered, "tr", 0)
    li_block = vp.row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None
    assert tr_block.find_all(attrs={"class": "dot-label visually-hidden"})
    assert "Both agree" in tr_block.text()
    assert not li_block.find_all(attrs={"class": "dot-label visually-hidden"})
    assert "Both agree" in li_block.text()


def test_when_and_flight_cells_each_carry_one_primary_one_secondary(tmp_path):
    """the desktop When and Flight cells each carry exactly one cell-primary span and one cell-secondary span (21-03-PLAN.md Task 1, D-15)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "wf01", "callsign": "WHENFLT",
         "aircraft_type": "A320", "airline": "AFR"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = vp.row_block(rendered, "tr", 0)
    assert tr_block is not None
    tds = tr_block.select("td")
    assert len(tds) >= 2
    when_cell, flight_cell = tds[0], tds[1]
    for cell in (when_cell, flight_cell):
        assert len(cell.find_all(cls="cell-primary")) == 1
        assert len(cell.find_all(cls="cell-secondary")) == 1


def test_data_table_wrap_scroll_edge_affordance_css(served_css):
    """.data-table-wrap declares both background-attachment values (local covers, scroll shadows) and style.css introduces no pointer-events-blocking overlay (quick task 260902-w4t, UIR-04)"""
    base = declarations_for(served_css, ".data-table-wrap")
    assert "background-attachment" in base
    assert "local" in base["background-attachment"]
    assert "scroll" in base["background-attachment"]
    assert "pointer-events" not in base
    override = declarations_for(served_css, ".page-section .data-table-wrap")
    assert "pointer-events" not in override


def test_filter_bar_markers_present_once(tmp_path):
    """History's filter bar carries exactly one data-filter-input/-count/-clear/-empty marker each"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "fb01", "callsign": "FB1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    for marker in (
        "data-filter-input", "data-filter-count", "data-filter-clear", "data-filter-empty",
    ):
        assert len(doc.select("[%s]" % marker)) == 1, "expected exactly one %r marker" % marker


def test_filter_input_carries_safari_autofill_suppression_attributes(tmp_path):
    """History's search filter input carries autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "fb01", "callsign": "FB1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    filter_input = doc.select_one("[data-filter-input]")
    assert filter_input.attrs.get("autocomplete") == "off"
    assert filter_input.attrs.get("spellcheck") == "false"
    assert filter_input.attrs.get("autocapitalize") == "characters"


def test_filter_count_template_attribute_english_and_french(tmp_path):
    """History's filter bar carries data-filter-count-template="%d of %d shown" under the default language and the French "%d sur %d affichés" under lang='fr' (D-06)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "fc01", "callsign": "FC1"},
    ])
    rendered_en = history_page.render(vp.history_ctx(tmp_path))
    doc_en = parse_html(rendered_en)
    template_en = doc_en.select_one("[data-filter-count-template]")
    assert template_en.attrs.get("data-filter-count-template") == "%d of %d shown"

    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    doc_fr = parse_html(rendered_fr)
    template_fr = doc_fr.select_one("[data-filter-count-template]")
    assert template_fr.attrs.get("data-filter-count-template") == "%d sur %d affichés"


def test_filter_bar_count_and_clear_wrap_as_one_group(tmp_path, served_css):
    """History's filter count and Clear control render as siblings inside one .filter-bar__meta group whose page-agnostic rule declares flex/centre/nowrap/auto-left-margin, with no page-scoped fork of the converged [data-filter-clear] rule anywhere (B11, 22-09-PLAN.md Task 3 — a regression of Phase 18's A-18)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "fm01", "callsign": "FILTMETA"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    group = doc.select_one('[class="filter-bar__meta"]')
    assert group.select("[data-filter-count]")
    assert group.select("[data-filter-clear]")
    assert len(doc.select("[data-filter-clear]")) == 1

    rules = css_rules(served_css)
    meta_rule_count = sum(1 for rule in rules if ".filter-bar__meta" in rule.selectors)
    assert meta_rule_count == 1, "expected exactly one .filter-bar__meta rule, never a per-page variant"
    decls = declarations_for(served_css, ".filter-bar__meta")
    assert decls.get("display") == "flex"
    assert decls.get("align-items") == "center"
    assert decls.get("white-space") == "nowrap"
    assert decls.get("margin-left") == "auto"
    joined = " ".join("%s:%s" % item for item in decls.items())
    assert "flight" not in joined and "history" not in joined

    forks = [
        sel for rule in rules for sel in rule.selectors
        if "[data-filter-clear]" in sel
        and any(kw in sel for kw in ("flight", "airline", "health", "registry"))
    ]
    assert not forks, "expected no page-scoped fork of the converged [data-filter-clear] rule, found %r" % (forks,)


def test_clear_control_shared_attribute_contract(tmp_path, served_css):
    """the Clear control's shared [data-filter-clear] contract holds: History renders the attribute, style.css styles it by attribute, and no class-keyed rule competes"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "ca01", "callsign": "CA1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    assert doc.select("[data-filter-clear]")

    rules = css_rules(served_css)
    assert any("[data-filter-clear]" in sel for rule in rules for sel in rule.selectors)
    for rule in rules:
        selector_text = ", ".join(rule.selectors)
        if "[data-filter-clear]" in selector_text:
            continue
        if "clear" in selector_text.lower():
            decls_text = " ".join("%s: %s" % (k, v) for k, v in rule.declarations)
            assert "background: none" not in decls_text, (
                "found a class-keyed Clear-control rule outside [data-filter-clear]: %r"
                % (selector_text,))
            assert "text-decoration: underline" not in decls_text, (
                "found a class-keyed Clear-control rule outside [data-filter-clear]: %r"
                % (selector_text,))


def test_filter_text_attribute_on_both_representations(tmp_path):
    """a real flight's data-filter-text attribute (lowercased escaped callsign+hex) appears on both the desktop <tr> and the mobile <li>"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "3944F0", "callsign": "AFR123"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    assert len(doc.find_all(attrs={"data-filter-text": "afr123 3944f0"})) == 2


def test_desktop_flight_cell_carries_no_copy_buttons(tmp_path):
    """the desktop Flight cell contains zero copy buttons (21-03-PLAN.md Task 1, D-15 - they move into the Task 2 detail row instead)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "cd01", "callsign": "CDONE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    tds = doc.select("tbody td")
    flight_td = next(td for td in tds if "CDONE" in td.text())
    assert not flight_td.select("[data-copy-value]")


def test_detail_row_pairs_with_summary_row_by_aria_controls_and_id(tmp_path):
    """each summary row gets exactly one sibling detail row, matched by aria-controls/id, with no hidden attribute and no inline style (the no-JS floor), and every row-toggle starts aria-expanded="false" (21-03-PLAN.md Task 2, D-15/R-12)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "dr01", "callsign": "DETAIL1"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "dr02", "callsign": "DETAIL2"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    doc = parse_html(rendered)
    detail_trs = doc.select('tr[class="flight-detail-row"]')
    assert len(detail_trs) == 2, "expected exactly 2 detail rows (one per summary row)"
    for index in (0, 1):
        assert doc.select('[aria-controls="flight-detail-%d"]' % index)
        assert doc.select('[id="flight-detail-%d"]' % index)
    for tag in detail_trs:
        assert "hidden" not in tag.attrs
        assert "style" not in tag.attrs
    assert len(doc.select('[aria-expanded="false"]')) >= 2
