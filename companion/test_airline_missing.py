"""The "Missing illustrations" section of the Airlines editor: one row per airline x aircraft
family without a picture, grouped under a small header per airline; an airline with no sighting and
no artwork has one "type to choose" row; the chip, the title and the page count agree; an upload
removes the row. Checked over HTTP against a real server."""
import html
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

import companion.test_companion_app_helpers as cah
import fleet_console_support as fx
from companion_app_server import InProcessAppServer, http_request, with_csrf_part
from server import history_db
from server.plane import illustrations, manual_resolutions

EDITOR = "/airlines/manage"
ITEM = re.compile(r'<li class="airlines-missing__item".*?</li>', re.S)
HEAD = re.compile(r'<li class="airlines-missing__head".*?</li>', re.S)
SECTION = re.compile(r'<section class="airlines-missing.*?</section>', re.S)
SIGHTINGS = (
    ("Emirates", "A388", 4), ("Emirates", "B77W", 2),
    ("Korean Air", "AN24", 1), ("Korean Air", "B748", 3))


def _seed_sightings(state_dir, sightings):
    now = datetime.now(timezone.utc)
    number = 0
    with history_db.open_db(state_dir) as conn:
        for airline, code, count in sightings:
            for _ in range(count):
                number += 1
                history_db.record_runway_event(
                    conn, ts=(now - timedelta(hours=number)).isoformat(), hex="ms%04d" % number,
                    callsign="XXX%03d" % number, aircraft_type=code,
                    confirmed_state="departing", airline=airline)


def _put_picture(state_dir, key):
    path = illustrations.override_path_for_key(key, state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG")


@pytest.fixture
def missing(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fx.seed_fleet(state_dir)
    _seed_sightings(state_dir, SIGHTINGS)
    cookie = fx.admin_cookie(state_dir)

    def get(lang="en"):
        status, _h, raw = http_request(
            server.url(EDITOR), cookie=cookie, extra_headers={"Accept-Language": lang})
        assert status == 200
        return raw.decode("utf-8")

    get.server, get.cookie = server, cookie
    yield state_dir, get
    server.stop()


def _items(page):
    return ITEM.findall(page)


def _group(page, name):
    """`(header, rows)` of the airline `name`: the header and the rows up to the next one."""
    parts = re.split(r'(?=<ul class="airlines-missing__airline")', SECTION.search(page).group(0))
    head = next(p for p in parts if '__name">%s<' % name in p)
    return head, _items(head)


def _text(markup):
    return html.unescape(re.sub(r"<[^>]+>", " ", markup))


def test_the_title_counts_the_rows_in_both_languages(missing):
    _state, get = missing
    page = get()
    count = len(_items(page))
    assert "Missing illustrations · %d" % count in page
    assert count == sum(
        int(n) for n in re.findall(r"(\d+) to do", " ".join(HEAD.findall(page))))
    fr = html.unescape(get("fr"))
    assert "Illustrations manquantes · %d" % count in fr
    assert "Connues par leur nom seulement" not in fr and "Known by name only" not in page


def test_one_row_per_airline_and_family_with_codes_and_views(missing):
    _state, get = missing
    head, rows = _group(get(), "Emirates")
    assert len(rows) == 2
    first, second = (_text(r) for r in rows)
    assert "Airbus A380" in first and "A388" in first and "4 views" in first
    assert "Boeing 777" in second and "B77W" in second and "2 views" in second
    assert "No artwork yet · 2 to do" in _text(head)
    for row in rows:
        assert 'class="airlines-missing__slot"' in row
        assert 'data-view-panel-fixed-type="' in row and 'aria-label="Add an illustration for Emirates, ' in row


def test_the_rows_of_an_airline_follow_its_views_and_the_airlines_follow_their_names(missing):
    _state, get = missing
    page = get()
    names = [html.unescape(n) for n in re.findall(r'airlines-missing__name">([^<]*)<', page)]
    assert names == sorted(names, key=str.casefold)
    _head, rows = _group(page, "Korean Air")
    assert [("Boeing 747" in r) for r in rows] == [True, False]


def test_an_airline_with_some_artwork_is_listed_for_its_missing_families_only(missing):
    state_dir, get = missing
    _put_picture(state_dir, "emirates-a380")
    head, rows = _group(get(), "Emirates")
    assert len(rows) == 1 and "Boeing 777" in rows[0]
    assert "Airbus A380 family already done · 1 to do" in _text(head) or (
        "Airbus A380 already done · 1 to do" in _text(head))
    fr_head, _rows = _group(html.unescape(get("fr")), "Emirates")
    assert "déjà illustré · 1 à faire" in _text(fr_head)


def test_an_airline_with_all_its_families_illustrated_is_not_listed(missing):
    state_dir, get = missing
    _put_picture(state_dir, "emirates-a380")
    _put_picture(state_dir, "emirates-b777")
    assert 'airlines-missing__name">Emirates<' not in get()


def test_an_airline_with_no_sighting_has_one_row_that_asks_for_the_type(missing):
    _state, get = missing
    page = get()
    head, rows = _group(page, "Finnair")
    assert len(rows) == 1
    row = rows[0]
    assert "Type to choose" in row and "No sighting yet" in row
    assert 'data-view-panel-ask-type=""' in row and "data-view-panel-fixed-type" not in row
    assert "No artwork yet · 1 to do" in _text(head)
    assert "Type à choisir" in get("fr") and "Aucun passage observé" in html.unescape(get("fr"))
    # an airline with sightings never gets the row
    assert "Type to choose" not in _group(page, "Emirates")[1][0]


def test_an_airline_with_artwork_and_no_sighting_is_not_listed(missing):
    state_dir, get = missing
    key = manual_resolutions.illustration_key_for_name("Finnair")
    _put_picture(state_dir, key)
    assert 'airlines-missing__name">Finnair<' not in get()


def test_a_rare_type_is_the_other_row_of_its_airline(missing):
    _state, get = missing
    page = get()
    _head, rows = _group(page, "Korean Air")
    other = next(r for r in rows if "AN24" in r)
    assert "Other" in _text(other) and "1 view" in _text(other)
    assert "Autre" in _text(next(r for r in _group(html.unescape(get("fr")), "Korean Air")[1] if "AN24" in r))
    assert "default_type=AN24" in other


def test_the_menu_of_a_hand_named_airline_is_in_its_header_not_on_its_rows(missing):
    state_dir, get = missing
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    head, rows = _group(get(), "Zephyr Air")
    assert "ZPH" in head and "Delete my name" in head and ">Rename<" in head
    assert 'href="#rename-airline-' in head and "/airlines/manual-resolutions/ZPH/delete" in head
    assert head.index(">Rename<") < head.index("Delete my name")
    assert "row-menu" not in "".join(rows)
    assert 'id="airline-zephyr-air"' in head
    fr = html.unescape(get("fr"))
    assert "Supprimer mon nom" in _group(fr, "Zephyr Air")[0]


def test_a_hand_named_airline_with_artwork_is_in_the_table_and_not_listed_without_sighting(missing):
    state_dir, get = missing
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    _put_picture(state_dir, "zephyr-air")
    page = get()
    assert 'airlines-missing__name">Zephyr Air<' not in page
    assert 'id="airline-zephyr-air"' in page


def test_the_chip_and_the_page_count_use_the_row_unit(missing):
    _state, get = missing
    page = get()
    count = len(_items(page))
    chip = re.search(r'<input[^>]*value="missing"[^>]*>.*?</label>', page, re.S).group(0)
    assert "Missing illustrations" in chip and ">%d<" % count in chip
    groups = set(re.findall(r'data-filter-group="([^"]*)"', page))
    all_chip = re.search(r'<input[^>]*value=""[^>]*data-filter-chip[^>]*>.*?</label>', page, re.S)
    all_chip = all_chip or re.search(r'<input[^>]*data-filter-chip[^>]*value=""[^>]*>.*?</label>', page, re.S)
    assert ">%d<" % len(groups) in all_chip.group(0)
    assert len([g for g in groups if g.startswith("missing-")]) == count
    fr = html.unescape(get("fr"))
    assert "Illustrations manquantes" in re.search(
        r'<input[^>]*value="missing"[^>]*>.*?</label>', fr, re.S).group(0)


def test_without_a_script_every_row_has_a_plain_upload_form(missing):
    _state, get = missing
    page = get()
    _head, rows = _group(page, "Emirates")
    for row in rows:
        nojs = row.split('airlines-act-nojs">')[1]
        assert 'method="post"' in nojs and 'enctype="multipart/form-data"' in nojs
        assert "/illustration/emirates-" in nojs and "default_type=" in nojs
        assert 'type="file"' in nojs and "<noscript><button" in nojs
    ask = _group(page, "Finnair")[1][0].split('airlines-act-nojs">')[1]
    assert re.search('action="[^"]*/illustration/finnair.png', ask)
    assert ask.index('<select name="default_type"') < ask.index('type="file"')
    assert "required" in ask.split("</select>")[0]


def _upload(get, path, cookie_png):
    body, content_type = with_csrf_part(
        get.cookie, *cah.encode_multipart(cookie_png, field_name="illustration"))
    return http_request(
        get.server.url(path), method="POST", data=body, cookie=get.cookie,
        content_type=content_type, extra_headers={"Origin": get.server.base_url()})


def _vendored_png():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "server", "assets", "icons", "illustrations", "vueling-airlines.png")
    with open(path, "rb") as handle:
        return handle.read()


def test_an_upload_removes_the_row_and_the_airlines_header_with_its_last_row(missing):
    _state, get = missing
    before = get()
    count = len(_items(before))
    action = re.search(r'action="([^"]*illustration/emirates-a380\.png[^"]*)"', _group(before, "Emirates")[1][0])
    status, _headers, _raw = _upload(get, html.unescape(action.group(1)), _vendored_png())
    assert status == 303
    after = get()
    assert len(_items(after)) == count - 1
    assert "Missing illustrations · %d" % (count - 1) in after
    assert "Airbus A380 already done · 1 to do" in _text(_group(after, "Emirates")[0]) or (
        "already done · 1 to do" in _text(_group(after, "Emirates")[0]))
    action = re.search(r'action="([^"]*illustration/emirates-b777\.png[^"]*)"', _group(after, "Emirates")[1][0])
    _upload(get, html.unescape(action.group(1)), _vendored_png())
    assert 'airlines-missing__name">Emirates<' not in get()


def test_an_upload_for_the_row_without_sighting_moves_the_airline_to_the_table(missing):
    _state, get = missing
    status, headers, _raw = _upload(get, "/illustration/finnair.png?default_type=A333", _vendored_png())
    assert status == 303 and "flash=illustration_replaced" in headers["Location"]
    page = get()
    assert 'airlines-missing__name">Finnair<' not in page
    assert re.search(r'<tbody class="airline-group"[^>]*id="airline-finnair"', page)


def test_the_empty_state_says_everything_is_in_place(missing):
    _state, get = missing
    for _round in range(4):
        rows = _items(get())
        if not rows:
            break
        for row in rows:
            action = re.search(r'airlines-act-nojs">.*?action="([^"]*)"', row, re.S).group(1)
            _upload(get, html.unescape(action) + ("" if "default_type=" in action else "?default_type=A333"),
                    _vendored_png())
    page = get()
    section = SECTION.search(page).group(0)
    assert "Missing illustrations · 0" in section and "airlines-missing--done" in section
    assert "All illustrations are in place" in section and "icon-check" in section
    assert "<li" not in section
    assert "Toutes les illustrations sont en place" in html.unescape(get("fr"))
