# SPDX-License-Identifier: AGPL-3.0-only
"""An airline has no picture of its own, only its aircraft types have: the Editor lists the
type rows alone (the star on the default type), an upload always names a type, and the first
picture of an airline makes its type the airline's default."""
import os
import re

import pytest

import fleet_console_support as fx
from companion.test_airline_editor_helpers import EDITOR, VENDORED, Rig, override as _override, query_of as _query
from companion_app_server import InProcessAppServer
from server import fleet_db
from server.plane import airline_default_types, illustrations, manual_resolutions


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    yield Rig(server, seed, {"admin": fx.admin_cookie(state_dir)})
    server.stop()


def _audit_actions(rig):
    conn = fleet_db.connect(rig.server.state_dir)
    try:
        return [row["action"] for row in fleet_db.list_audit(conn, "all", 50, 0)]
    finally:
        conn.close()


def _png():
    with open(os.path.join(VENDORED, "vueling-airlines.png"), "rb") as handle:
        return handle.read()


def _editor(rig):
    return rig.get("admin", rig.frame + EDITOR + "?types=all")[2]


def _group(body, key):
    start = body.index('<tbody class="airline-group" id="airline-%s"' % key)
    return body[start:body.index("</tbody>", start)]


def _type_rows(group):
    return re.findall(r'<span class="airlines-type"[^>]*>([^<]*)</span>', group)


def test_the_editor_has_no_all_types_row_and_one_row_per_type(rig):
    body = _editor(rig)
    assert "All types" not in body and "Any aircraft" not in body
    assert _type_rows(_group(body, "air-france")) == ["Airbus A320"]
    assert _type_rows(_group(body, "transavia-france")) == ["Airbus A320", "Boeing 737"]
    # The airline row carries no picture of its own: its thumbnails are on the type rows.
    france = _group(body, "air-france")
    assert france.index('class="airlines-subrow"') < france.index("airlines-thumb")


def test_the_star_is_on_the_default_type_only(rig):
    airline_default_types.set_default_type(rig.owned_dir, "transavia-france", "A320")
    group = _group(_editor(rig), "transavia-france")
    rows = re.findall(r'<tr class="airlines-subrow">.*?</tr>', group)
    starred = [row for row in rows if "airlines-star" in row]
    assert len(starred) == 1 and ">Airbus A320<" in starred[0]
    # An airline with no stored default shows its legacy picture's airframe as the default.
    france = _group(_editor(rig), "air-france")
    assert "airlines-star" in france


def test_the_type_row_actions_are_icon_buttons_named_for_the_airline_and_the_family(rig):
    group = _group(_editor(rig), "transavia-france")
    rows = re.findall(r'<tr class="airlines-subrow">.*?</tr>', group)
    for row in rows:
        name = re.search(r'class="airlines-type"[^>]*>([^<]*)<', row).group(1)
        add = re.search(r'<button[^>]*airlines-act--icon[^>]*>.*?</button>', row, re.S)
        change = re.search(r'<label class="airlines-act airlines-act--icon"[^>]*>.*?</label>', row, re.S)
        assert (add is None) != (change is None), row
        if add:
            assert 'aria-label="Add an illustration for Transavia France, %s"' % name in add.group(0)
            assert 'data-tip="Add artwork"' in add.group(0) and "icon-picture-add" in add.group(0)
        else:
            assert 'data-tip="Change artwork"' in change.group(0)
            assert "Change the artwork of Transavia France, %s</span>" % name in change.group(0)
            assert "icon-picture-edit" in change.group(0)
        assert "airlines-act__text" not in row
        # Without a script the add form keeps its plain text button.
        assert "airlines-act-nojs" not in row or "airlines-act__text" in row.split("airlines-act-nojs")[1]


def test_an_upload_without_a_type_is_refused_for_an_airline_with_no_picture(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    before = rig.stored()
    status, headers = rig.upload("admin", rig.frame + "/illustration/zephyr-air.png", _png())
    assert status == 303 and _query(headers)[1]["flash"] == ["artwork_type_invalid"]
    status, headers = rig.upload(
        "admin", rig.frame + "/illustration/zephyr-air.png?default_type=", _png())
    assert _query(headers)[1]["flash"] == ["artwork_type_invalid"]
    assert rig.stored() == before


def test_the_first_picture_of_an_airline_makes_its_type_the_default_and_is_audited(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    status, headers = rig.upload(
        "admin", rig.frame + "/illustration/zephyr-air.png?default_type=a321", _png())
    assert status == 303 and _query(headers)[1]["flash"] == ["illustration_replaced"]
    assert airline_default_types.load_default_types(rig.owned_dir) == {"zephyr-air": "A321"}
    assert "airline.default_type" in _audit_actions(rig)
    group = _group(_editor(rig), "zephyr-air")
    assert _type_rows(group) == ["Airbus A320"] and "airlines-star" in group


def test_a_later_picture_keeps_the_default_the_airline_already_has(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    rig.upload("admin", rig.frame + "/illustration/zephyr-air.png?default_type=A321", _png())
    rig.upload("admin", rig.frame + "/illustration/zephyr-air-b737.png?default_type=B738", _png())
    assert airline_default_types.load_default_types(rig.owned_dir) == {"zephyr-air": "A321"}
    assert _type_rows(_group(_editor(rig), "zephyr-air")) == ["Airbus A320", "Boeing 737"]


def test_a_picture_for_an_airline_with_an_airframe_keeps_that_airframe_as_default(rig):
    status, _headers = rig.upload(
        "admin", rig.frame + "/illustration/air-france-b737.png?default_type=B738", _png())
    assert status == 303
    assert airline_default_types.load_default_types(rig.owned_dir) == {}
    assert _type_rows(_group(_editor(rig), "air-france")) == ["Airbus A320", "Boeing 737"]


def test_every_type_row_uploads_with_its_own_type(rig):
    group = _group(_editor(rig), "transavia-france")
    actions = re.findall(r'<form class="airlines-art"[^>]* action="([^"]+)"', group)
    assert actions == [
        rig.frame + "/illustration/transavia-france-a320.png?default_type=A320",
        rig.frame + "/illustration/transavia-france.png?default_type=B737"]


def test_the_default_menu_item_is_offered_on_a_picture_type_only(rig):
    _override(rig, "air-france-b737")
    group = _group(_editor(rig), "air-france")
    assert group.count("Set as default") == 1


def test_the_airlines_list_shows_the_picture_of_the_default_type(tmp_path):
    from types import SimpleNamespace

    from companion.pages import airline_collection_page as page
    state = str(tmp_path)
    entry = SimpleNamespace(picture_key="transavia-france", name="Transavia France")
    assert "/illustration/transavia-france.png" in page._picture_html(entry, state)
    assert airline_default_types.set_default_type(state, "transavia-france", "A320") == "ok"
    html = page._picture_html(entry, state)
    assert "/illustration/transavia-france-a320.png" in html
    assert "/illustration/transavia-france.png" not in html
    nobody = SimpleNamespace(picture_key="no-such-airline", name="No Such Airline")
    assert "collection-card__blank" in page._picture_html(nobody, state)


def _upload_with_type_part(rig, path, code):
    """The upload a script-free browser sends: token part, the type select as a text part, the file."""
    import companion.test_companion_app_helpers as cah
    from companion_app_server import http_request, with_csrf_part
    body, content_type = cah.encode_multipart(_png(), field_name="illustration")
    boundary = content_type.split("boundary=", 1)[1].encode("ascii")
    part = (b"--" + boundary + b'\r\nContent-Disposition: form-data; name="default_type"\r\n\r\n'
            + code.encode("ascii") + b"\r\n")
    body, content_type = with_csrf_part(rig.cookies["admin"], part + body, content_type)
    status, headers, _b = http_request(
        rig.server.url(path), method="POST", data=body, cookie=rig.cookies["admin"],
        content_type=content_type, extra_headers={"Origin": rig.server.base_url()})
    return status, headers


def test_a_script_free_form_sends_the_type_as_a_part_before_the_file(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    status, headers = _upload_with_type_part(rig, rig.frame + "/illustration/zephyr-air.png", "A321")
    assert status == 303 and _query(headers)[1]["flash"] == ["illustration_replaced"]
    assert airline_default_types.load_default_types(rig.owned_dir) == {"zephyr-air": "A321"}
    assert os.path.isfile(os.path.join(rig.server.state_dir, "illustration_overrides", "zephyr-air.png"))


def test_a_script_free_form_with_no_or_a_bad_type_is_refused_and_writes_nothing(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    before = rig.stored()
    for code in ("", "not a type!"):
        _status, headers = _upload_with_type_part(rig, rig.frame + "/illustration/zephyr-air.png", code)
        assert _query(headers)[1]["flash"] == ["artwork_type_invalid"]
    assert rig.stored() == before


def test_the_script_free_fallback_form_asks_for_a_required_named_type(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    status, _headers, body = rig.get("admin", rig.frame + EDITOR + "?resolve=ZEP")
    form = body[body.index('id="manual-illustration-form"'):]
    form = form[:form.index("</form>")]
    select = re.search(r"<select[^>]*>", form).group(0)
    assert 'name="default_type"' in select and " required" in select and " hidden" not in select
    assert form.index("csrf_token") < form.index("<select") < form.index('type="file"')
    assert "A320" in form and "B738" in form


def test_a_seen_type_and_the_legacy_airframe_of_one_slot_are_one_row(tmp_path):
    from types import SimpleNamespace

    from companion.pages import airline_table
    state = str(tmp_path)
    entry = SimpleNamespace(type_counts=(("B738", 3), ("A321", 2), ("A320", 1), ("A333", 1)))
    facts = {"key": "air-france", "state_dir": state, "default_type": "A320",
             "stored_default": "",
             "pictures": illustrations.type_pictures(
                 "air-france", state, ("B738", "A321", "A320", "A333"))}
    rows = airline_table._sub_rows(entry, facts, "Air France", [])
    # A321 and A320 are drawn with one picture (the legacy A320): one row naming both.
    assert [row["code"] for row in rows] == ["B738", "A321, A320", "A333"]
    assert rows[1]["views"] == 3 and rows[1]["picture"].key == "air-france"
    assert rows[1]["is_default"] and not rows[0]["is_default"]
    assert rows[0]["picture"] is None and rows[2]["picture"] is None


def test_the_default_menu_labels_are_short_in_both_languages():
    from companion import i18n
    from companion.pages import airline_table
    assert i18n.t_lang(airline_table.MENU_SET_DEFAULT_TYPE, "en") == "Set as default"
    assert i18n.t_lang(airline_table.MENU_CLEAR_DEFAULT_TYPE, "en") == "Remove as default"
    assert i18n.t_lang(airline_table.MENU_SET_DEFAULT_TYPE, "fr") == "Image par défaut"
    assert i18n.t_lang(airline_table.MENU_CLEAR_DEFAULT_TYPE, "fr") == "Retirer par défaut"
