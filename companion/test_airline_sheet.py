"""The airline sheet: the pencil on an Airlines tile opens one place to
rename an airline, see its built-in callsign prefixes and replace its
artwork. Served-HTML checks on the page, POST-route checks on the two new
routes against a real server, and the artwork-follows-the-name behaviour.
Nothing here reads production source text.
"""
import os
import re
import urllib.parse

import companion.prefs as prefs
import companion.test_status_pages_helpers as shp
from companion.pages import airline_sheet, airlines_page
from companion_app_server import http_request, login
from server.plane import illustrations, manual_resolutions, name_overrides


def _card(rendered, airline_name):
    name_index = rendered.index('class="airline-card__name">%s<' % airline_name)
    start = rendered.rindex('<div class="airline-card"', 0, name_index)
    end = rendered.find('<div class="airline-card"', start + 1)
    return rendered[start:] if end == -1 else rendered[start:end]


def _attr(fragment, name):
    match = re.search(r'%s="([^"]*)"' % re.escape(name), fragment)
    assert match, "expected %s in %r" % (name, fragment[:200])
    return match.group(1)


def _post(server, session, path, **fields):
    return http_request(
        server.base_url() + path, method="POST", cookie=session,
        data=urllib.parse.urlencode(fields).encode())


def _flash(headers):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)


def test_a_builtin_tile_carries_the_sheet_vocabulary_and_a_link_pencil(tmp_path):
    """every curated tile's triggers carry the five sheet attributes with the built-in name,
    its prefixes and the artwork key, and the pencil is a real link to the no-script sheet"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    card = _card(rendered, "Transavia France")
    assert _attr(card, airline_sheet.AIRLINE_ATTR) == "Transavia France"
    assert _attr(card, airline_sheet.AIRLINE_NAME_ATTR) == "Transavia France"
    assert _attr(card, airline_sheet.AIRLINE_PREFIXES_ATTR) == "TFV TVF"
    assert _attr(card, airline_sheet.RENAMED_ATTR) == ""
    assert 'href="/airlines?sheet=transavia-france#airline-sheet" class="airline-card__edit"' in card
    assert 'href="/airlines?sheet=transavia-france-a320#airline-sheet" class="airline-card__edit"' in card
    assert ">Renamed</span>" not in card


def test_every_trigger_on_the_page_carries_all_five_sheet_attributes(tmp_path):
    """a gap card and a manual-only card carry the sheet attributes too, empty, so a click
    never inherits another card's values"""
    tmp = str(tmp_path)
    manual_resolutions.add_entry(tmp, "XQZ", "Totally Novel Airline", now="2026-01-01T00:00:00+00:00")
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"}})
    rendered = airlines_page.render(shp.ctx(tmp))
    triggers = re.findall(r"<(?:a|button)\b[^>]*data-view-panel-src[^>]*>", rendered)
    assert len(triggers) > 40
    for trigger in triggers:
        for attr in airline_sheet.SHEET_ATTRS:
            assert ('%s="' % attr) in trigger, (attr, trigger[:120])
    novel = _card(rendered, "Totally Novel Airline")
    assert _attr(novel, airline_sheet.AIRLINE_ATTR) == ""
    assert 'class="airline-card__edit"' in novel and "<button" in novel
    gap = re.search(r'<a class="airline-card" href="/airlines\?resolve=XYZ"[^>]*>', rendered).group(0)
    assert _attr(gap, airline_sheet.AIRLINE_ATTR) == ""


def test_the_shared_dialog_holds_the_sheet_forms_with_fixed_post_actions(tmp_path):
    """the dialog carries the name form, the chip list, the reset form and the artwork label,
    their actions fixed server-side and the name field a 16px-safe text input on the known-airlines
    datalist"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    dialog = rendered[rendered.index('<dialog'):]
    assert 'class="airline-sheet"' in dialog
    assert 'method="post" action="/airlines/rename"' in dialog
    assert 'method="post" action="/airlines/rename/reset"' in dialog
    assert 'name="airline_name" list="known-airlines-dialog" maxlength="100" required' in dialog
    assert 'id="known-airlines-dialog"' in dialog
    assert "Reset to SkyPane’s name" in dialog


def test_a_renamed_airline_shows_its_new_name_badge_and_new_artwork_key(tmp_path):
    """an override renames the tile, adds the Renamed badge, keeps the built-in name as the
    sheet's identity and points the artwork at the new name's key; the Reset form is offered"""
    tmp = str(tmp_path)
    name_overrides.set_names(tmp, ["TFV", "TVF"], "Transavia", now="2026-01-01T00:00:00+00:00")
    rendered = airlines_page.render(shp.ctx(tmp) | {"name_overrides": name_overrides.load_name_overrides(tmp)})
    card = _card(rendered, "Transavia")
    assert _attr(card, airline_sheet.AIRLINE_ATTR) == "Transavia France"
    assert _attr(card, airline_sheet.AIRLINE_NAME_ATTR) == "Transavia"
    assert _attr(card, airline_sheet.RENAMED_ATTR) == "active"
    assert '<span class="airline-card__chip">Renamed</span>' in card
    assert 'sheet=transavia#airline-sheet' in card
    assert 'class="airline-card__name">Transavia<' in card


def test_the_renamed_badge_is_french_and_loses_to_a_resolved_by_hand_chip(tmp_path):
    """the badge reads Renommée in French; on a card that also has a manual entry the existing
    manual chip keeps the single badge slot"""
    tmp = str(tmp_path)
    overrides = {"AFR": {"airline_name": "Skyline Air", "created_at": "t"}}
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = airlines_page.render(shp.ctx(tmp) | {"name_overrides": overrides})
        assert '<span class="airline-card__chip">Renommée</span>' in _card(rendered, "Skyline Air")
    finally:
        prefs.set_request_prefs(lang="en")
    manual_resolutions.add_entry(tmp, "AFR", "Some Other", now="2026-01-01T00:00:00+00:00")
    rendered = airlines_page.render(shp.ctx(tmp) | {"name_overrides": overrides})
    card = _card(rendered, "Skyline Air")
    assert "Renamed</span>" not in card
    assert airline_sheet.RENAMED_ATTR in card


def test_the_no_script_sheet_renders_for_a_known_key_only(tmp_path):
    """?sheet= for a rendered artwork key renders the in-page sheet with real values, the
    chips and, only for a renamed airline, the reset form; an unknown or hostile key renders
    nothing"""
    tmp = str(tmp_path)
    plain = airlines_page.render(shp.ctx(tmp) | {"sheet_key": "air-france"})
    section = plain[plain.index("data-sheet-fallback"):]
    assert 'value="Air France"' in section
    assert '<li class="airline-card__chip mono">AFR</li>' in section
    assert 'action="/airlines/rename/reset"' not in section
    assert 'action="/illustration/air-france.png"' in section
    renamed = airlines_page.render(shp.ctx(tmp) | {
        "sheet_key": "transavia", "name_overrides": {
            "TVF": {"airline_name": "Transavia", "created_at": "t"}}})
    section = renamed[renamed.index("data-sheet-fallback"):]
    assert 'value="Transavia"' in section and 'action="/airlines/rename/reset"' in section
    assert section.count('<li class="airline-card__chip mono">') == 2
    for hostile in ("nope", '"><script>', "../etc", ""):
        out = airlines_page.render(shp.ctx(tmp) | {"sheet_key": hostile})
        assert "data-sheet-fallback" not in out and "<script>alert" not in out


def test_rename_post_stores_every_prefix_and_carries_the_artwork(make_app_server):
    """a rename writes the override for each built-in prefix, flashes the pending toast key,
    copies the artwork to the new key as an owner override while the old key's files stay, and
    the new key serves and accepts uploads"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    status, headers, _ = _post(
        server, session, "/airlines/rename", airline="Transavia France", airline_name="  Transavia ")
    assert status == 303 and urllib.parse.urlsplit(headers["Location"]).path == "/airlines"
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAMED]
    stored = name_overrides.load_name_overrides(server.state_dir)
    assert {p: e["airline_name"] for p, e in stored.items()} == {"TFV": "Transavia", "TVF": "Transavia"}
    for suffix in ("", "-a320"):
        copied = illustrations.override_path_for_key("transavia" + suffix, server.state_dir)
        assert os.path.isfile(copied)
        assert os.path.isfile(illustrations.illustration_path_for_key("transavia-france" + suffix))
    status, _, body = http_request(server.base_url() + "/illustration/transavia.png", cookie=session)
    assert status == 200 and body.startswith(b"\x89PNG")
    status, _, _ = http_request(
        server.base_url() + "/illustration/transavia-a320.png", method="POST", cookie=session,
        data=b"x", content_type="multipart/form-data; boundary=zz")
    assert status != 404
    page = http_request(server.base_url() + "/airlines", cookie=session)[2].decode()
    assert _attr(_card(page, "Transavia"), airline_sheet.RENAMED_ATTR) == "active"


def test_rename_post_never_overwrites_artwork_the_new_name_already_has(make_app_server):
    """renaming onto a name that already has artwork copies nothing"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    _post(server, session, "/airlines/rename", airline="Transavia France", airline_name="Air France")
    assert not os.path.exists(os.path.join(server.state_dir, "illustration_overrides", "air-france.png"))
    assert name_overrides.load_name_overrides(server.state_dir)["TVF"]["airline_name"] == "Air France"


def test_rename_post_refusals_reopen_the_sheet_and_write_nothing(make_app_server):
    """empty, unusable, too long and reserved names each reach their own flash key, send the
    owner back to the open sheet and write nothing"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    cases = (
        ("", "manual_name_empty"), ("   ", "manual_name_empty"), ("!!!", "manual_name_unusable"),
        ("x" * 101, "manual_name_too_long"), ("Generic Fallback", "manual_name_reserved"),
        ("../../x", "manual_name_unusable"),
    )
    for name, expected in cases:
        status, headers, _ = _post(
            server, session, "/airlines/rename", airline="Air France", airline_name=name)
        query = _flash(headers)
        assert status == 303 and query["flash"] == [expected], (name, headers["Location"])
        assert query["sheet"] == ["air-france"]
    assert name_overrides.load_name_overrides(server.state_dir) == {}


def test_rename_post_for_an_unknown_airline_is_stale(make_app_server):
    """a name that is not a built-in airline (or a missing field) writes nothing and says so"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    for fields in ({"airline": "Nobody Air", "airline_name": "X"}, {"airline_name": "X"}):
        status, headers, _ = _post(server, session, "/airlines/rename", **fields)
        assert status == 303 and _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_STALE]
    assert name_overrides.load_name_overrides(server.state_dir) == {}


def test_rename_post_refuses_when_the_registry_is_full(make_app_server):
    """at the 200-entry cap a new prefix is refused with its own flash key and the sheet stays
    open; the stored overrides are untouched"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    letters = "ABCDEFGHIJ"
    filler = ["%s%s%s" % (a, b, c) for a in "PQ" for b in letters for c in letters][:200]
    name_overrides.set_names(server.state_dir, filler, "Filler")
    status, headers, _ = _post(
        server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    query = _flash(headers)
    assert status == 303 and query["flash"] == [airline_sheet.FLASH_RENAME_FULL]
    assert query["sheet"] == ["air-france"]
    assert len(name_overrides.load_name_overrides(server.state_dir)) == 200


def test_rename_to_the_builtin_name_and_reset_both_remove_the_override(make_app_server):
    """posting the built-in name back, or the reset form, clears the override and returns to
    SkyPane's name; resetting twice is harmless and the old artwork key still serves"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    _post(server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    assert name_overrides.load_name_overrides(server.state_dir)["AFR"]["airline_name"] == "Skyline Air"
    status, headers, _ = _post(
        server, session, "/airlines/rename", airline="Air France", airline_name="Air France")
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_RESET]
    assert name_overrides.load_name_overrides(server.state_dir) == {}
    _post(server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    for _ in range(2):
        status, headers, _ = _post(server, session, "/airlines/rename/reset", airline="Air France")
        assert status == 303 and _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_RESET]
    assert name_overrides.load_name_overrides(server.state_dir) == {}
    page = http_request(server.base_url() + "/airlines", cookie=session)[2].decode()
    assert _attr(_card(page, "Air France"), airline_sheet.RENAMED_ATTR) == ""
    assert http_request(server.base_url() + "/illustration/air-france.png", cookie=session)[0] == 200
    status, headers, _ = _post(server, session, "/airlines/rename/reset", airline="Nobody Air")
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_STALE]


def test_the_sheet_flash_messages_exist_in_both_languages(tmp_path):
    """every flash key the two routes can produce resolves to non-empty text in English and
    French, with a distinct French wording"""
    from companion import flash
    keys = (airline_sheet.FLASH_RENAMED, airline_sheet.FLASH_RENAME_RESET,
            airline_sheet.FLASH_RENAME_STALE, airline_sheet.FLASH_RENAME_FULL,
            airline_sheet.FLASH_RENAME_SAVE_FAILED)
    try:
        for key in keys:
            prefs.set_request_prefs(lang="en")
            english = flash.resolve_flash_text(key, str(tmp_path))
            prefs.set_request_prefs(lang="fr")
            french = flash.resolve_flash_text(key, str(tmp_path))
            assert english and french and english != french, key
    finally:
        prefs.set_request_prefs(lang="en")


def test_flights_and_home_show_stored_flights_under_the_new_name_and_reset_restores(make_app_server):
    """after a rename the Flights and Home pages list an already-stored flight under the owner's
    name (with the carried artwork), without the stored row changing; after a reset they list
    the original name again"""

    from server import history_db
    server = make_app_server(fake_providers=True)
    with history_db.open_db(server.state_dir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-01-01T10:00:00+00:00", hex="abc", callsign="AFR123", aircraft_type="A320",
            confirmed_state="departing", corroborated=True, route_source="fresh_hit",
            airline="Air France", origin="ORY", destination="NCE", tracked_runway="3")

    session = login(server)

    def pages():
        return [http_request(server.base_url() + path, cookie=session)[2].decode()
                for path in ("/flights", "/")]

    _post(server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    for page in pages():
        assert "Skyline Air" in page and "/illustration/skyline-air.png" in page
    with history_db.open_db(server.state_dir) as conn:
        assert history_db.recent_runway_events(conn)[0]["airline"] == "Air France"
    _post(server, session, "/airlines/rename/reset", airline="Air France")
    for page in pages():
        assert "Skyline Air" not in page and "Air France" in page
