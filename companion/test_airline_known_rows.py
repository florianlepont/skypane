"""The airlines known by name only in the Airlines editor: one read-only row each, with the name, the
prefix and the Artwork button that opens the shared add-artwork step; a chip filters them; an airline
that gains artwork leaves the block, an airline named by hand without artwork joins it. Checked over HTTP against a real server."""
import html
import os
import re

import pytest

import companion.test_companion_app_helpers as cah
import fleet_console_support as fx
from companion_app_server import InProcessAppServer, http_request, with_csrf_part
from server.plane import airline_default_types, enrich, illustrations, manual_resolutions

EDITOR = "/airlines/manage"
ROW = re.compile(r'<tbody class="airline-group airline-group--known".*?</tbody>', re.S)


@pytest.fixture
def known(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fx.seed_fleet(state_dir)
    cookie = fx.admin_cookie(state_dir)

    def get(lang="en"):
        status, _h, raw = http_request(
            server.url(EDITOR), cookie=cookie, extra_headers={"Accept-Language": lang})
        assert status == 200
        return raw.decode("utf-8")

    get.server, get.cookie = server, cookie
    yield state_dir, get
    server.stop()


def _rows(page):
    return ROW.findall(page)


def test_one_read_only_row_per_airline_known_by_name_only(known):
    _state, get = known
    page = get()
    rows = _rows(page)
    pairs = enrich.names_without_artwork()
    assert len(rows) == len(pairs)
    for row, (prefix, name) in zip(rows, pairs):
        text = html.unescape(row)
        assert name in text and prefix in text
        assert "<form" not in row and "<input" not in row
        assert 'aria-label="Add the first artwork for %s"' % name in text
        assert 'data-filter-kind="known"' in row
    assert "Known by name only · %d" % len(pairs) in page


def test_the_labels_are_french_in_french(known):
    _state, get = known
    page = html.unescape(get("fr"))
    count = len(enrich.names_without_artwork())
    assert "Connues par leur nom seulement · %d" % count in page
    assert "Ajouter la première illustration pour Turkish Airlines" in page
    assert ">Illustration<" in page


def test_the_chip_counts_the_known_rows(known):
    _state, get = known
    page = get()
    chip = re.search(r'<input[^>]*value="known"[^>]*>.*?</label>', page, re.S)
    assert chip and ">%d<" % len(enrich.names_without_artwork()) in chip.group(0)
    assert "Known by name only" in chip.group(0)


def test_an_airline_with_artwork_leaves_the_block(known):
    state_dir, get = known
    key = manual_resolutions.illustration_key_for_name("Finnair")
    path = illustrations.override_path_for_key(key, state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG")
    page = get()
    assert "Finnair" not in " ".join(_rows(page))
    assert 'id="airline-finnair"' in page
    assert "FIN" in re.search(r'<tbody[^>]*id="airline-finnair".*?</tbody>', page, re.S).group(0)


def test_an_airline_named_by_hand_without_artwork_is_listed_once_in_the_block(known):
    state_dir, get = known
    count = len(_rows(get()))
    manual_resolutions.add_entry(state_dir, "KLM", "KLM Royal Dutch Airlines")
    page = get()
    names = [html.unescape(re.search(r'airlines-known__name">([^<]*)<', r).group(1)) for r in _rows(page)]
    assert names.count("KLM Royal Dutch Airlines") == 1 and len(names) == count
    assert "Known by name only · %d" % count in page
    assert 'id="airline-klm-royal-dutch-airlines"' in page


def test_a_hand_named_airline_without_artwork_is_in_the_block_with_its_menu_and_not_in_the_table(known):
    state_dir, get = known
    count = len(_rows(get()))
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    page = get()
    row = next(r for r in _rows(page) if "Zephyr Air" in r)
    assert "ZPH" in row and "Delete my name" in row
    assert 'href="#rename-airline-' in row and 'data-modal-open' in row
    assert row.index(">Rename<") < row.index("Delete my name")
    assert 'name="prefix" value="ZPH"' in row and "/airlines/rename/manual" in row
    assert "/airlines/manual-resolutions/ZPH/delete" in row
    assert "Known by name only · %d" % (count + 1) in page
    table = page.split("Airlines · ")[-1]
    assert "Zephyr Air" not in table
    assert re.search(r'value="known"[^>]*>.*?filter-chip__count">%d<' % (count + 1), page, re.S)
    assert "No artwork" not in page
    fr = html.unescape(get("fr"))
    assert "Supprimer mon nom" in next(r for r in _rows(fr) if "Zephyr Air" in r)
    assert "Connues par leur nom seulement · %d" % (count + 1) in fr and "Sans illustration" not in fr


def test_a_hand_named_airline_with_artwork_is_in_the_table_and_not_in_the_block(known):
    state_dir, get = known
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    path = illustrations.override_path_for_key("zephyr-air", state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG")
    page = get()
    assert "Zephyr Air" not in " ".join(_rows(page))
    assert 'id="airline-zephyr-air"' in page
    assert "airline-group--known\" id=\"airline-zephyr-air" not in page


def test_an_upload_for_a_known_by_name_airline_is_accepted_and_an_unknown_key_is_not(known):
    state_dir, get = known
    vendored = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "server", "assets", "icons", "illustrations", "vueling-airlines.png")
    with open(vendored, "rb") as handle:
        good = handle.read()
    statuses = {}
    for key in ("finnair", "no-such-airline"):
        body, content_type = with_csrf_part(
            get.cookie, *cah.encode_multipart(good, field_name="illustration"))
        status, _headers, _raw = http_request(
            get.server.url("/illustration/%s.png" % key), method="POST", data=body,
            cookie=get.cookie, content_type=content_type,
            extra_headers={"Origin": get.server.base_url()})
        statuses[key] = status
    assert statuses == {"finnair": 303, "no-such-airline": 404}
    assert os.path.isfile(os.path.join(state_dir, "illustration_overrides", "finnair.png"))


def _upload(get, key, query, cookie_png):
    body, content_type = with_csrf_part(
        get.cookie, *cah.encode_multipart(cookie_png, field_name="illustration"))
    return http_request(
        get.server.url("/illustration/%s.png%s" % (key, query)), method="POST", data=body,
        cookie=get.cookie, content_type=content_type,
        extra_headers={"Origin": get.server.base_url()})


def _vendored_png():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "server", "assets", "icons", "illustrations", "vueling-airlines.png")
    with open(path, "rb") as handle:
        return handle.read()


def test_the_artwork_button_asks_for_an_aircraft_type_in_both_languages(known):
    _state_dir, get = known
    for lang, label in (("en", "Aircraft type"), ("fr", "Type d’avion")):
        page = get(lang)
        assert 'data-view-panel-ask-type=""' in _rows(page)[0]
        select = re.search(r'<select id="airline_artwork_type".*?</select>', page, re.S).group(0)
        assert ' hidden' in select.split(">")[0]
        assert 'aria-label="%s"' % label in select
        assert '<option value="A333">A333</option>' in select


@pytest.mark.parametrize("code", ("", "a", "A3 30", "A330/../x", "ABCDEFGHIJKLM"))
def test_an_invalid_aircraft_type_refuses_the_upload_and_stores_nothing(known, code):
    state_dir, get = known
    status, headers, _raw = _upload(get, "finnair", "?default_type=%s" % code.replace(" ", "%20"), _vendored_png())
    assert status == 303
    assert "flash=artwork_type_invalid" in headers["Location"]
    assert not os.path.exists(os.path.join(state_dir, "illustration_overrides", "finnair.png"))
    assert not os.path.exists(os.path.join(state_dir, "airline_default_types.json"))
    status, _h, raw = http_request(
        get.server.url(headers["Location"].split("#")[0]), cookie=get.cookie,
        extra_headers={"Accept-Language": "fr"})
    assert status == 200
    page = html.unescape(raw.decode("utf-8"))
    assert "Impossible d’ajouter l’illustration" in page and "type d’avion valide" in page.lower()


def test_a_valid_aircraft_type_becomes_the_default_type_of_the_airline(known):
    state_dir, get = known
    status, headers, _raw = _upload(get, "finnair", "?default_type=a330", _vendored_png())
    assert status == 303
    assert "flash=illustration_replaced" in headers["Location"]
    assert os.path.isfile(os.path.join(state_dir, "illustration_overrides", "finnair.png"))
    assert airline_default_types.load_default_types(state_dir)["finnair"] == "A330"
