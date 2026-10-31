"""The Locations page and its add, edit and delete actions over real HTTP for
both roles: role-scoped listing, validation, the per-user quota and rate
limit, ownership refusals that look like an unknown path, audit rows and the
access gates. Every place here is an obviously generic fake."""
import json
import re
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import console_locations, console_routes, i18n_fr, prefs, throttle
from companion_app_server import http_request
from server import fleet_db

LAT = "10.123456"
LON = "20.654321"


@pytest.fixture(autouse=True)
def _english_and_fresh_throttle(monkeypatch):
    prefs.set_request_prefs(lang="en")
    monkeypatch.setattr(
        console_locations, "_MUTATIONS",
        throttle.LockoutThrottle(
            limit=console_locations.MUTATION_LIMIT,
            lockout_s=console_locations.MUTATION_LOCKOUT_S))
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    cookies = {
        "admin": fx.admin_cookie(server.state_dir),
        "owner": fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL),
        "plain": fx.user_cookie(server.state_dir, email=fx.USER_EMAIL),
    }
    return server, seed, cookies


def _sql(state_dir, sql, args=()):
    conn = fleet_db.connect(state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _add(state_dir, name, owner=None, lat=10.0, lon=20.0, tz="Europe/Paris"):
    conn = fleet_db.connect(state_dir)
    try:
        return fleet_db.add_location(conn, name, lat, lon, tz, owner)
    finally:
        conn.close()


def _table(state_dir, name):
    return _sql(state_dir, "SELECT * FROM %s ORDER BY 1" % name)


def _form(name="Sample Town", lat=LAT, lon=LON, tz="Europe/Paris"):
    return {"name": name, "latitude": lat, "longitude": lon, "timezone": tz}


def _flash_text(server, cookie, headers):
    values = [value.split(";")[0] for key, value in headers.items()
              if key.lower() == "set-cookie" and value.startswith("sp_flash=")]
    assert values, "no flash cookie"
    return fx.get(server, cookie + "; " + values[0], "/locations")[2]


def _location_audit(state_dir, action=None):
    rows = [row for row in fx.audit_rows(state_dir) if row["action"].startswith("location.")]
    return [row for row in rows if action is None or row["action"] == action]


def _row_html(body, location_id):
    match = re.search(r'<tr data-location="%d".*?</tr>' % location_id, body, re.S)
    assert match, "no table row for location %d" % location_id
    return match.group(0)


def _unknown_path_404(server, cookie):
    status, _headers, body = fx.post(server, cookie, "/no-such-page-anywhere", {})
    assert status == 404
    return status, body


# --- page ---------------------------------------------------------------------


def test_an_admin_sees_every_location_with_owner_and_used_by_counts(rig):
    server, seed, cookies = rig
    mine = _add(server.state_dir, "Owner Place", seed.owner_id)
    legacy = _add(server.state_dir, "Legacy Place")
    _add(server.state_dir, "Plain Place", seed.user_id)
    _sql(server.state_dir, "UPDATE devices SET location_id = ? WHERE id = ?",
         (mine, seed.owned_id))
    status, _headers, body = fx.get(server, cookies["admin"], "/locations")
    assert status == 200
    for name in ("Owner Place", "Legacy Place", "Plain Place"):
        assert name in body
    assert "<th>Owner</th>" in body
    assert fx.OWNER_EMAIL in _row_html(body, mine)
    assert "Platform" in _row_html(body, legacy)
    assert "1 frame" in _row_html(body, mine)
    assert "No frame" in _row_html(body, legacy)
    assert "/locations/%d/edit" % legacy in body and "/locations/%d/delete" % legacy in body
    assert "10.0000, 20.0000" in body


def test_a_user_sees_only_their_own_rows_and_no_owner_column(rig):
    server, seed, cookies = rig
    _add(server.state_dir, "Owner Place", seed.owner_id)
    _add(server.state_dir, "Legacy Place")
    _add(server.state_dir, "Plain Place", seed.user_id)
    status, _headers, body = fx.get(server, cookies["owner"], "/locations")
    assert status == 200
    assert "Owner Place" in body
    assert "Legacy Place" not in body and "Plain Place" not in body
    assert "<th>Owner</th>" not in body and "Platform" not in body
    assert fx.USER_EMAIL not in body
    assert "Administration sections" not in body
    assert 'href="/fleet"' not in body


def test_empty_states_and_the_default_time_zone(rig):
    server, _seed, cookies = rig
    admin = fx.get(server, cookies["admin"], "/locations")[2]
    user = fx.get(server, cookies["owner"], "/locations")[2]
    assert "No locations yet" in admin and "Add the first place a frame can use." in admin
    assert "No locations yet" in user and "Add a place to choose it for your frame." in user
    for body in (admin, user):
        assert '<option value="Europe/Paris" selected>Europe/Paris</option>' in body
        assert "Add location" in body and "New location" in body


def test_every_form_has_csrf_and_a_location_path(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    body = fx.get(server, cookies["owner"], "/locations")[2]
    forms = [
        form for form in re.findall(
            r'<form method="post" action="([^"]+)"[^>]*>(.*?)</form>', body, re.S)
        if form[0].startswith("/locations")]
    assert len(forms) >= 3
    for action, inner in forms:
        assert 'name="csrf_token"' in inner, action
        assert re.match(r"^/locations(/add|/\d+/(edit|delete))$", action)
    assert "/locations/%d/edit" % row in body
    assert "<dialog" not in body and "confirm(" not in body


def test_stored_text_is_escaped(rig):
    server, seed, cookies = rig
    _add(server.state_dir, "<script>alert(1)</script>", seed.owner_id)
    body = fx.get(server, cookies["owner"], "/locations")[2]
    assert "<script>alert(1)" not in body
    assert "&lt;script&gt;" in body


# --- create -------------------------------------------------------------------


def test_a_user_creates_an_owned_location_with_rounded_coordinates(rig):
    server, seed, cookies = rig
    status, headers, _ = fx.post(server, cookies["owner"], "/locations/add", _form())
    assert status == 303 and headers["Location"] == "/locations"
    rows = _sql(
        server.state_dir,
        "SELECT name, latitude, longitude, timezone, owner_user_id FROM locations")
    assert rows == [("Sample Town", 10.1235, 20.6543, "Europe/Paris", seed.owner_id)]
    audit = _location_audit(server.state_dir, "location.add")
    assert len(audit) == 1 and audit[0]["outcome"] == "ok"
    assert audit[0]["target_type"] == "location" and audit[0]["target_id"].isdigit()
    assert audit[0]["actor_user_id"] == seed.owner_id
    flash = _flash_text(server, cookies["owner"], headers)
    assert "Location added" in flash and "Sample Town" in flash


def test_an_admin_creates_an_ownerless_platform_location(rig):
    server, _seed, cookies = rig
    for index in range(12):
        status, _h, _b = fx.post(
            server, cookies["admin"], "/locations/add", _form(name="Admin Place %d" % index))
        assert status == 303
    rows = _sql(server.state_dir, "SELECT owner_user_id FROM locations")
    assert len(rows) == 12 and all(row == (None,) for row in rows)
    body = fx.get(server, cookies["admin"], "/locations")[2]
    assert "Platform" in body


def test_the_eleventh_location_of_a_user_is_refused_with_a_denied_audit_row(rig):
    server, seed, cookies = rig
    for index in range(10):
        _add(server.state_dir, "Place %d" % index, seed.owner_id)
    before = _table(server.state_dir, "locations")
    status, headers, _ = fx.post(server, cookies["owner"], "/locations/add", _form())
    assert status == 303
    assert _table(server.state_dir, "locations") == before
    flash = _flash_text(server, cookies["owner"], headers)
    assert "Location limit reached" in flash
    assert "You can keep up to 10 locations." in flash
    audit = _location_audit(server.state_dir, "location.add")
    assert len(audit) == 1 and audit[0]["outcome"] == "denied"
    # Another user is not affected by the first user's count.
    assert fx.post(server, cookies["plain"], "/locations/add", _form())[0] == 303
    assert len(_table(server.state_dir, "locations")) == 11


# --- validation ---------------------------------------------------------------

BAD_INPUTS = [
    ("empty name", _form(name="  "), "Enter a name."),
    ("long name", _form(name="x" * 61), "Enter a name."),
    ("name of control characters", _form(name="\t\x07"), "Enter a name."),
    ("nan latitude", _form(lat="nan"), "Enter a latitude between -90 and 90."),
    ("inf latitude", _form(lat="inf"), "Enter a latitude between -90 and 90."),
    ("text latitude", _form(lat="north"), "Enter a latitude between -90 and 90."),
    ("empty latitude", _form(lat=""), "Enter a latitude between -90 and 90."),
    ("exponent latitude", _form(lat="1e1"), "Enter a latitude between -90 and 90."),
    ("high latitude", _form(lat="90.0001"), "Enter a latitude between -90 and 90."),
    ("low latitude", _form(lat="-91"), "Enter a latitude between -90 and 90."),
    ("nan longitude", _form(lon="NaN"), "Enter a longitude between -180 and 180."),
    ("inf longitude", _form(lon="-inf"), "Enter a longitude between -180 and 180."),
    ("text longitude", _form(lon="east"), "Enter a longitude between -180 and 180."),
    ("high longitude", _form(lon="180.5"), "Enter a longitude between -180 and 180."),
    ("low longitude", _form(lon="-181"), "Enter a longitude between -180 and 180."),
    ("unknown zone", _form(tz="Mars/Olympus"), "Choose a time zone."),
    ("path zone", _form(tz="../etc/passwd"), "Choose a time zone."),
    ("empty zone", _form(tz=""), "Choose a time zone."),
]


@pytest.mark.parametrize("label, form, message", BAD_INPUTS, ids=[b[0] for b in BAD_INPUTS])
def test_invalid_input_gives_the_field_error_and_writes_nothing(rig, label, form, message):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    before = _table(server.state_dir, "locations")
    for path in ("/locations/add", "/locations/%d/edit" % row):
        status, _headers, body = fx.post(server, cookies["owner"], path, form)
        assert status == 400, path
        assert 'class="field-error"' in body and message in body, path
    assert _table(server.state_dir, "locations") == before
    assert _location_audit(server.state_dir) == []


def test_boundary_coordinates_are_accepted_and_negative_zero_is_plain(rig):
    server, _seed, cookies = rig
    for lat, lon in (("90", "180"), ("-90", "-180"), ("-0.00001", ".5"), ("+3.5", "7.")):
        assert fx.post(
            server, cookies["owner"], "/locations/add", _form(lat=lat, lon=lon))[0] == 303
    stored = _sql(server.state_dir, "SELECT latitude, longitude FROM locations ORDER BY id")
    assert stored == [(90.0, 180.0), (-90.0, -180.0), (0.0, 0.5), (3.5, 7.0)]
    assert str(stored[2][0]) == "0.0"


def test_control_characters_are_stripped_from_the_name(rig):
    server, _seed, cookies = rig
    assert fx.post(
        server, cookies["owner"], "/locations/add", _form(name="Sam\tple\x07 Town"))[0] == 303
    assert _sql(server.state_dir, "SELECT name FROM locations") == [("Sample Town",)]


def test_a_refused_submission_keeps_what_was_typed(rig):
    server, _seed, cookies = rig
    _status, _headers, body = fx.post(
        server, cookies["owner"], "/locations/add", _form(name="Kept Name", lat="999"))
    assert 'value="Kept Name"' in body and 'value="999"' in body


# --- edit and delete ----------------------------------------------------------


def test_an_owner_edits_their_own_location(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    status, headers, _ = fx.post(
        server, cookies["owner"], "/locations/%d/edit" % row,
        _form(name="Renamed", lat="11.5", lon="21.5", tz="Europe/London"))
    assert status == 303
    assert _sql(
        server.state_dir,
        "SELECT name, latitude, longitude, timezone, owner_user_id FROM locations") == [
        ("Renamed", 11.5, 21.5, "Europe/London", seed.owner_id)]
    audit = _location_audit(server.state_dir, "location.update")
    assert len(audit) == 1 and audit[0]["target_id"] == str(row) and audit[0]["outcome"] == "ok"
    assert "Location saved" in _flash_text(server, cookies["owner"], headers)


def test_an_owner_deletes_their_own_unused_location(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    status, headers, _ = fx.post(
        server, cookies["owner"], "/locations/%d/delete" % row, {})
    assert status == 303
    assert _table(server.state_dir, "locations") == []
    audit = _location_audit(server.state_dir, "location.delete")
    assert len(audit) == 1 and audit[0]["target_id"] == str(row)
    assert "Location deleted" in _flash_text(server, cookies["owner"], headers)


def test_deleting_a_location_used_by_a_frame_is_refused(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    _sql(server.state_dir, "UPDATE devices SET location_id = ? WHERE id = ?",
         (row, seed.owned_id))
    before = _table(server.state_dir, "locations")
    status, headers, _ = fx.post(
        server, cookies["owner"], "/locations/%d/delete" % row, {})
    assert status == 303
    assert _table(server.state_dir, "locations") == before
    assert "This location is used by a frame." in _flash_text(
        server, cookies["owner"], headers)
    audit = _location_audit(server.state_dir, "location.delete")
    assert len(audit) == 1 and audit[0]["outcome"] == "denied"
    assert _sql(server.state_dir, "SELECT location_id FROM devices WHERE id = ?",
                (seed.owned_id,)) == [(row,)]


def test_an_admin_edits_and_deletes_any_location_including_ownerless(rig):
    server, seed, cookies = rig
    legacy = _add(server.state_dir, "Legacy Place")
    theirs = _add(server.state_dir, "Owner Place", seed.owner_id)
    assert fx.post(
        server, cookies["admin"], "/locations/%d/edit" % legacy, _form(name="Edited"))[0] == 303
    assert fx.post(
        server, cookies["admin"], "/locations/%d/edit" % theirs, _form(name="Edited 2"))[0] == 303
    names = _sql(server.state_dir, "SELECT name, owner_user_id FROM locations ORDER BY id")
    assert names == [("Edited", None), ("Edited 2", seed.owner_id)]
    assert fx.post(server, cookies["admin"], "/locations/%d/delete" % legacy, {})[0] == 303
    assert fx.post(server, cookies["admin"], "/locations/%d/delete" % theirs, {})[0] == 303
    assert _table(server.state_dir, "locations") == []
    assert len(_location_audit(server.state_dir, "location.update")) == 2
    assert len(_location_audit(server.state_dir, "location.delete")) == 2


def test_an_edit_keeps_the_owner(rig):
    server, seed, cookies = rig
    theirs = _add(server.state_dir, "Owner Place", seed.owner_id)
    fx.post(server, cookies["admin"], "/locations/%d/edit" % theirs, _form(name="Edited"))
    assert _sql(server.state_dir, "SELECT owner_user_id FROM locations") == [(seed.owner_id,)]


# --- cross-owner ----------------------------------------------------------------


@pytest.mark.parametrize("action", ["edit", "delete"])
def test_a_foreign_ownerless_or_unknown_id_is_the_unknown_path_404(rig, action):
    server, seed, cookies = rig
    foreign = _add(server.state_dir, "Plain Place", seed.user_id)
    legacy = _add(server.state_dir, "Legacy Place")
    mine = _add(server.state_dir, "Owner Place", seed.owner_id)
    _sql(server.state_dir, "UPDATE devices SET location_id = ? WHERE id = ?",
         (foreign, seed.owned_id))
    expected = _unknown_path_404(server, cookies["owner"])
    snapshot = (_table(server.state_dir, "locations"), _table(server.state_dir, "audit_log"),
                _table(server.state_dir, "devices"))
    body = _form(name="Hijacked") if action == "edit" else {}
    for target in (foreign, legacy, 999999, 0, "12345678901", "abc", "-1"):
        path = "/locations/%s/%s" % (target, action)
        status, _headers, text = fx.post(server, cookies["owner"], path, body)
        assert (status, text) == expected, path
    # An invalid submission for a foreign id must not reveal a validation answer.
    if action == "edit":
        status, _headers, text = fx.post(
            server, cookies["owner"], "/locations/%d/edit" % foreign, _form(name=""))
        assert (status, text) == expected
    assert snapshot == (_table(server.state_dir, "locations"),
                        _table(server.state_dir, "audit_log"),
                        _table(server.state_dir, "devices"))
    assert mine  # the caller's own row exists and is untouched
    assert _sql(server.state_dir, "SELECT name FROM locations WHERE id = ?", (mine,)) == [
        ("Owner Place",)]


def test_a_user_get_never_lists_another_users_rows(rig):
    server, seed, cookies = rig
    _add(server.state_dir, "Owner Place", seed.owner_id)
    _add(server.state_dir, "Plain Place", seed.user_id)
    plain = fx.get(server, cookies["plain"], "/locations")[2]
    assert "Plain Place" in plain and "Owner Place" not in plain


# --- rate limit -----------------------------------------------------------------


def test_the_twenty_first_mutation_by_a_user_is_refused_but_others_are_not(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    for index in range(console_locations.MUTATION_LIMIT):
        status, _h, _b = fx.post(
            server, cookies["owner"], "/locations/%d/edit" % row,
            _form(name="Name %d" % index))
        assert status == 303
    status, headers, _ = fx.post(
        server, cookies["owner"], "/locations/%d/edit" % row, _form(name="One too many"))
    assert status == 303
    assert _sql(server.state_dir, "SELECT name FROM locations") == [("Name 19",)]
    assert "Too many changes" in _flash_text(server, cookies["owner"], headers)
    # Add and delete are refused too while locked.
    assert fx.post(server, cookies["owner"], "/locations/add", _form())[0] == 303
    assert fx.post(server, cookies["owner"], "/locations/%d/delete" % row, {})[0] == 303
    assert _sql(server.state_dir, "SELECT name FROM locations") == [("Name 19",)]
    # Another user is unaffected.
    assert fx.post(server, cookies["plain"], "/locations/add", _form())[0] == 303
    assert len(_table(server.state_dir, "locations")) == 2


def test_an_admin_is_not_rate_limited(rig):
    server, _seed, cookies = rig
    row = _add(server.state_dir, "Legacy Place")
    for index in range(console_locations.MUTATION_LIMIT + 5):
        assert fx.post(
            server, cookies["admin"], "/locations/%d/edit" % row,
            _form(name="Name %d" % index))[0] == 303
    expected = "Name %d" % (console_locations.MUTATION_LIMIT + 4)
    assert _sql(server.state_dir, "SELECT name FROM locations") == [(expected,)]


# --- gates ------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/locations/add", "/locations/1/edit", "/locations/1/delete"])
def test_missing_csrf_is_403_and_anonymous_is_sent_to_sign_in(rig, path):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    assert row == 1
    before = _table(server.state_dir, "locations")
    audit_before = _table(server.state_dir, "audit_log")
    body = urllib.parse.urlencode(_form()).encode()
    status, _headers, _body = http_request(
        server.url(path), "POST", data=body, cookie=cookies["owner"])
    assert status == 403
    status, headers, _body = http_request(server.url(path), "POST", data=body)
    assert status in (302, 303) and "/" in headers["Location"]
    assert _table(server.state_dir, "locations") == before
    assert _table(server.state_dir, "audit_log") == audit_before


def test_anonymous_page_request_is_sent_to_sign_in(rig):
    server, _seed, _cookies = rig
    status, headers, _ = http_request(server.url("/locations"))
    assert status in (302, 303) and "/login" in headers["Location"]


def test_no_get_route_exists_for_the_actions(rig):
    server, seed, cookies = rig
    row = _add(server.state_dir, "Owner Place", seed.owner_id)
    unknown = fx.get(server, cookies["owner"], "/no-such-page-anywhere")
    for path in ("/locations/add", "/locations/%d/edit" % row, "/locations/%d/delete" % row):
        assert fx.get(server, cookies["owner"], path)[::2] == unknown[::2]


# --- constants, French -----------------------------------------------------------


def test_the_paths_match_the_console_route_constants():
    assert console_locations.LOCATIONS_PATH == console_routes.LOCATIONS_ROUTE
    assert console_locations.LOCATIONS_ADD_PATH == console_routes.LOCATIONS_ADD_ROUTE
    assert console_locations.LOCATION_ACTION_PREFIX == console_routes.LOCATION_ACTION_PREFIX
    assert console_locations.EDIT_SUFFIX == console_routes.LOCATION_EDIT_SUFFIX
    assert console_locations.DELETE_SUFFIX == console_routes.LOCATION_DELETE_SUFFIX


def test_the_french_page_uses_the_catalogue(rig):
    server, seed, cookies = rig
    _add(server.state_dir, "Owner Place", seed.owner_id)
    status, _headers, body = fx.get(
        server, cookies["owner"], "/locations", headers={"Accept-Language": "fr"})
    assert status == 200
    assert i18n_fr.BY_ID["admin_locations.add_location"] == "Ajouter un lieu"
    assert "Ajouter un lieu" in body and "Nouveau lieu" in body
    assert "Garder le lieu" in body


def test_audit_target_ids_are_numeric_for_every_location_action(rig):
    server, seed, cookies = rig
    fx.post(server, cookies["owner"], "/locations/add", _form())
    row = _sql(server.state_dir, "SELECT id FROM locations")[0][0]
    fx.post(server, cookies["owner"], "/locations/%d/edit" % row, _form(name="Again"))
    fx.post(server, cookies["owner"], "/locations/%d/delete" % row, {})
    rows = _location_audit(server.state_dir)
    assert [r["action"] for r in rows] == ["location.add", "location.update", "location.delete"]
    assert all(r["target_id"] == str(row) for r in rows)
    assert all(json.dumps(r).find(LAT) < 0 for r in rows)
