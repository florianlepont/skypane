"""The airline sheet: an Airlines row opens one place to rename an
airline, see its built-in callsign prefixes and replace its artwork, one
aircraft type at a time. Served-HTML checks on the page, POST-route checks on the two new
routes against a real server, and the artwork-follows-the-name behaviour.
Nothing here reads production source text.
"""
import os
import re
import urllib.parse

import companion.prefs as prefs
import companion.test_companion_app_helpers as cah
import companion.test_status_pages_helpers as shp
from companion.pages import airline_sheet, airlines_page
from companion_app_server import http_request, login, with_csrf, with_csrf_part
from server.plane import illustrations, manual_resolutions, name_overrides


def _card(rendered, airline_name):
    """The one `<tbody>` (the airline's row and its aircraft-type sub-rows) of `airline_name`."""
    escaped = airline_name
    name_index = max(
        rendered.find('name="airline_name" value="%s"' % escaped),
        rendered.find('airlines-name--fixed">%s<' % escaped))
    assert name_index >= 0, airline_name
    start = rendered.rindex('<tbody class="airline-group"', 0, name_index)
    return rendered[start:rendered.find("</tbody>", start)]


def _attr(fragment, name):
    match = re.search(r'%s="([^"]*)"' % re.escape(name), fragment)
    assert match, "expected %s in %r" % (name, fragment[:200])
    return match.group(1)


def _post(server, session, path, **fields):
    return http_request(
        server.base_url() + path, method="POST", cookie=session,
        data=with_csrf(session, fields))


def _flash(headers):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)


def test_a_builtin_row_edits_the_name_in_place_and_lists_its_prefixes_read_only(tmp_path):
    """every curated row is a rename form posting the built-in name and the shown name, saved
    on change with a script and by a visible Save button without one; its callsign prefixes
    are read-only text, never an input"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    card = _card(rendered, "Transavia France")
    form = card[card.index('<form class="airlines-name"'):card.index("</form>")]
    assert 'method="post" action="/airlines/rename"' in form
    assert 'name="airline" value="Transavia France"' in form
    assert 'name="airline_name" value="Transavia France" maxlength="100" required' in form
    assert "data-autosubmit" in form and "list=" not in form and "autofocus" not in form
    assert '<noscript><button type="submit" class="airlines-name__save">Save</button></noscript>' in form
    assert re.search(r'<td class="airlines-cell airlines-cell--prefixes mono">'
                     r'<span class="visually-hidden">Prefixes </span>TFV TVF</td>', card)
    assert card.count('name="airline_name"') == 1
    assert "Renamed" not in card and "Renommée" not in card


def test_manual_only_and_unidentified_rows_have_no_rename_form(tmp_path):
    """an owner-named airline (no built-in prefix to rename by) shows its name as plain text,
    and an unidentified prefix is resolved in its own row: a form posting to the resolve route
    with the prefix, a name field with suggestions and an optional default aircraft type"""
    tmp = str(tmp_path)
    manual_resolutions.add_entry(tmp, "XQZ", "Totally Novel Airline", now="2026-01-01T00:00:00+00:00")
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"}})
    rendered = airlines_page.render(shp.ctx(tmp))
    triggers = re.findall(r"<(?:a|button)\b[^>]*data-view-panel-src[^>]*>", rendered)
    assert len(triggers) > 30
    for trigger in triggers:
        for attr in airline_sheet.SHEET_ATTRS:
            assert ('%s="' % attr) in trigger, (attr, trigger[:120])
    novel = _card(rendered, "Totally Novel Airline")
    assert 'name="airline_name"' not in novel and "<form" in novel
    gap = re.search(r'<form class="airlines-resolve".*?</form>', rendered, re.S).group(0)
    assert 'action="/airlines/resolve"' in gap and 'name="prefix" value="XYZ"' in gap
    assert 'name="airline_name"' in gap and 'list="airlines-known-names"' in gap
    assert '<select name="default_type"' in gap and ">Validate<" in gap and ">Ignore<" in gap
    assert 'id="airlines-known-names"' in rendered


def test_the_shared_dialog_no_longer_holds_a_name_form(tmp_path):
    """the shared dialog serves the artwork and the resolve flow only: names are edited in the
    table, so it carries no rename or reset form and no type switcher"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    dialog = rendered[rendered.index('<dialog'):]
    assert 'action="/airlines/rename' not in dialog
    assert "airline-sheet" not in dialog
    assert dialog.count('<h2 class="lightbox__heading">') == 1
    assert 'id="known-airlines-dialog"' in dialog


def test_a_renamed_airline_shows_its_new_name_and_new_artwork_key_without_a_chip(tmp_path):
    """an override renames the row, keeps the built-in name as the form's identity and its
    aircraft types, points the artwork at the new name's key, offers the reset in the row menu
    and carries no status chip"""
    tmp = str(tmp_path)
    name_overrides.set_names(tmp, ["TFV", "TVF"], "Transavia", now="2026-01-01T00:00:00+00:00")
    rendered = airlines_page.render(shp.ctx(tmp) | {"types_open": "all", "name_overrides": name_overrides.load_name_overrides(tmp)})
    card = _card(rendered, "Transavia")
    assert 'name="airline" value="Transavia France"' in card
    assert 'name="airline_name" value="Transavia"' in card
    assert 'action="/illustration/transavia.png"' in card
    assert 'action="/illustration/transavia-a320.png"' in card
    reset = card[card.index('<form class="airlines-menu__form"'):]
    assert 'action="/airlines/rename/reset"' in reset and "Reset to the original name" in reset
    assert 'name="airline" value="Transavia France"' in reset
    assert "airline-card__chip" not in card and "Renamed" not in card


def test_an_unrenamed_airline_has_no_reset_item(tmp_path):
    """the row menu offers the reset only for an airline carrying an owner name"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    card = _card(rendered, "Air France")
    assert "Reset to the original name" not in card and "airlines-menu__form" not in card
    assert "Change artwork" in card and 'aria-label="Enlarge the artwork of Air France"' in card


def test_a_row_names_the_airframe_and_never_an_any_aircraft_label(tmp_path):
    """no row for a built-in airline says "Any aircraft"/"Tout appareil"; the secondary
    picture's own aircraft is named in its sub-row, in both languages"""
    try:
        for lang, forbidden in (("en", "Any aircraft"), ("fr", "Tout appareil")):
            prefs.set_request_prefs(lang=lang)
            rendered = airlines_page.render(shp.ctx(str(tmp_path)) | {"types_open": "all"})
            assert forbidden not in rendered
            assert '<span class="airlines-type">A320</span>' in _card(rendered, "Transavia France")
    finally:
        prefs.set_request_prefs(lang="en")


def test_a_refused_rename_focuses_the_name_of_that_row_only(tmp_path):
    """the editor reached after a name refusal (taken included) puts focus on the name field of
    the refused airline's row, and only there; any other flash or key focuses nothing"""
    tmp = str(tmp_path)

    def table(markup):
        start = markup.index('<table class="airlines-table"')
        return markup[start:markup.index("</table>", start)]

    plain = airlines_page.render(shp.ctx(tmp) | {"sheet_key": "air-france"})
    assert "autofocus" not in table(plain)
    for key in (airline_sheet.FLASH_RENAME_TAKEN, "manual_name_too_long"):
        refused = airlines_page.render(shp.ctx(tmp) | {"sheet_key": "air-france", "flash_key": key})
        assert table(refused).count(" autofocus") == 1
        assert " autofocus" in re.search(r'<input type="text" name="airline_name" value="Air France"[^>]*>', refused).group(0)
    reset = airlines_page.render(shp.ctx(tmp) | {"sheet_key": "air-france", "flash_key": "airline_renamed"})
    assert " autofocus" not in table(reset)
    for hostile in ("nope", '"><script>', "../etc", ""):
        out = airlines_page.render(shp.ctx(tmp) | {
            "sheet_key": hostile, "flash_key": airline_sheet.FLASH_RENAME_TAKEN})
        assert " autofocus" not in table(out) and "<script>alert" not in out


def test_rename_post_stores_every_prefix_and_carries_the_artwork(make_app_server):
    """a rename writes the override for each built-in prefix, flashes the pending toast key,
    copies the artwork to the new key as an owner override while the old key's files stay, and
    the new key serves and accepts uploads"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    status, headers, _ = _post(
        server, session, "/airlines/rename", airline="Transavia France", airline_name="  Transavia ")
    assert status == 303 and urllib.parse.urlsplit(headers["Location"]).path == "/airlines/manage"
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAMED]
    stored = name_overrides.load_name_overrides(server.state_dir)
    assert {p: e["airline_name"] for p, e in stored.items()} == {"TFV": "Transavia", "TVF": "Transavia"}
    for suffix in ("", "-a320"):
        copied = illustrations.override_path_for_key("transavia" + suffix, server.state_dir)
        assert os.path.isfile(copied)
        assert os.path.isfile(illustrations.illustration_path_for_key("transavia-france" + suffix))
    status, _, body = http_request(server.base_url() + "/illustration/transavia.png", cookie=session)
    assert status == 200 and body.startswith(b"\x89PNG")
    upload, upload_type = with_csrf_part(
        session, *cah.encode_multipart(b"x"))
    status, _, _ = http_request(
        server.base_url() + "/illustration/transavia-a320.png", method="POST", cookie=session,
        data=upload, content_type=upload_type)
    assert status != 404
    page = http_request(server.base_url() + "/airlines/manage", cookie=session)[2].decode()
    assert "Reset to the original name" in _card(page, "Transavia")


def test_rename_post_never_overwrites_artwork_the_new_name_already_has(make_app_server):
    """renaming onto a name whose key already holds owner artwork copies nothing over it"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    existing = illustrations.override_path_for_key("skyline-air", server.state_dir)
    os.makedirs(os.path.dirname(existing), exist_ok=True)
    with open(existing, "wb") as fh:
        fh.write(b"owner-art")
    _post(server, session, "/airlines/rename", airline="Transavia France", airline_name="Skyline Air")
    with open(existing, "rb") as fh:
        assert fh.read() == b"owner-art"
    assert name_overrides.load_name_overrides(server.state_dir)["TVF"]["airline_name"] == "Skyline Air"


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
    page = http_request(server.base_url() + "/airlines/manage", cookie=session)[2].decode()
    assert 'name="airline_name" value="Air France"' in _card(page, "Air France")
    assert "Reset to the original name" not in _card(page, "Air France")
    assert http_request(server.base_url() + "/illustration/air-france.png", cookie=session)[0] == 200
    status, headers, _ = _post(server, session, "/airlines/rename/reset", airline="Nobody Air")
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_STALE]


def test_the_sheet_flash_messages_exist_in_both_languages(tmp_path):
    """every flash key the two routes can produce resolves to non-empty text in English and
    French, with a distinct French wording"""
    from companion import flash
    keys = (airline_sheet.FLASH_RENAMED, airline_sheet.FLASH_RENAME_RESET,
            airline_sheet.FLASH_RENAME_STALE, airline_sheet.FLASH_RENAME_FULL,
            airline_sheet.FLASH_RENAME_SAVE_FAILED, airline_sheet.FLASH_RENAME_TAKEN)
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
    flights_page, home_page = pages()
    assert "Skyline Air" in flights_page
    assert "Skyline Air" in home_page
    with history_db.open_db(server.state_dir) as conn:
        assert history_db.recent_runway_events(conn)[0]["airline"] == "Air France"
    _post(server, session, "/airlines/rename/reset", airline="Air France")
    for page in pages():
        assert "Skyline Air" not in page and "Air France" in page


def _stored_names(server):
    return {p: e["airline_name"] for p, e in name_overrides.load_name_overrides(server.state_dir).items()}


def test_rename_onto_another_airlines_builtin_name_is_refused_in_any_spelling(make_app_server):
    """a name whose artwork key equals another curated airline's (case, accents, spacing,
    punctuation variants) is refused with the taken flash, the sheet reopens on the same airline
    and nothing is written"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    for name in ("Transavia France", "transavia  france", "TRANSAVIA-FRANCE", "Tränsavia France", "Air Algérie"):
        status, headers, _ = _post(
            server, session, "/airlines/rename", airline="Air France", airline_name=name)
        query = _flash(headers)
        assert status == 303, name
        assert query["flash"] == [airline_sheet.FLASH_RENAME_TAKEN], (name, headers["Location"])
        assert query["sheet"] == ["air-france"]
    assert _stored_names(server) == {}
    assert not os.path.exists(os.path.join(server.state_dir, "illustration_overrides", "transavia-france.png"))


def test_rename_onto_another_airlines_override_is_refused(make_app_server):
    """once Air France is called Skyline Air, no other airline can take that name in any
    spelling, and Air France's own stored name is untouched"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    _post(server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    for name in ("Skyline Air", "SKYLINE air", "skyline-air"):
        _, headers, _ = _post(
            server, session, "/airlines/rename", airline="Transavia France", airline_name=name)
        query = _flash(headers)
        assert query["flash"] == [airline_sheet.FLASH_RENAME_TAKEN], name
        assert query["sheet"] == ["transavia-france"]
    assert _stored_names(server) == {"AFR": "Skyline Air"}


def test_resaving_the_same_name_and_resetting_by_own_name_are_not_collisions(make_app_server):
    """an airline keeps its own override name (same or respelled) and posting its own built-in
    name is still the reset, never a collision with itself"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    _post(server, session, "/airlines/rename", airline="Air France", airline_name="Skyline Air")
    for name in ("Skyline Air", "skyline air", "Skyline Air Two"):
        _, headers, _ = _post(
            server, session, "/airlines/rename", airline="Air France", airline_name=name)
        assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAMED], name
    assert _stored_names(server) == {"AFR": "Skyline Air Two"}
    _, headers, _ = _post(
        server, session, "/airlines/rename", airline="Air France", airline_name="Air France")
    assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAME_RESET]
    assert _stored_names(server) == {}


def test_a_multi_prefix_airline_keeps_its_own_name_across_prefixes(make_app_server):
    """Transavia France's two prefixes share one override; re-saving it does not collide with
    its own other prefix"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    for _ in range(2):
        _, headers, _ = _post(
            server, session, "/airlines/rename", airline="Transavia France", airline_name="Transavia")
        assert _flash(headers)["flash"] == [airline_sheet.FLASH_RENAMED]
    assert _stored_names(server) == {"TFV": "Transavia", "TVF": "Transavia"}


def test_the_taken_flash_is_an_error_toast(tmp_path):
    """the taken refusal is an error-toned flash like the other name refusals"""
    from companion import flash
    assert flash.FLASH_ROLES[airline_sheet.FLASH_RENAME_TAKEN] == flash.FLASH_ROLES["manual_name_too_long"]
