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
from server.plane import airline_default_types, manual_resolutions


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
    return re.findall(r'<span class="airlines-type">([^<]*)</span>', group)


def test_the_editor_has_no_all_types_row_and_one_row_per_type(rig):
    body = _editor(rig)
    assert "All types" not in body and "Any aircraft" not in body
    assert _type_rows(_group(body, "air-france")) == ["A320"]
    assert _type_rows(_group(body, "transavia-france")) == ["A320", "B737"]
    # The airline row carries no picture of its own: its thumbnails are on the type rows.
    france = _group(body, "air-france")
    assert france.index('class="airlines-subrow"') < france.index("airlines-thumb")


def test_the_star_is_on_the_default_type_only(rig):
    airline_default_types.set_default_type(rig.owned_dir, "transavia-france", "A320")
    group = _group(_editor(rig), "transavia-france")
    rows = re.findall(r'<tr class="airlines-subrow">.*?</tr>', group)
    starred = [row for row in rows if "airlines-pill--star" in row]
    assert len(starred) == 1 and ">A320<" in starred[0]
    # An airline with no stored default shows its legacy picture's airframe as the default.
    france = _group(_editor(rig), "air-france")
    assert "airlines-pill--star" in france


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
    assert _type_rows(group) == ["A321"] and "airlines-pill--star" in group


def test_a_later_picture_keeps_the_default_the_airline_already_has(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZEP", "Zephyr Air")
    rig.upload("admin", rig.frame + "/illustration/zephyr-air.png?default_type=A321", _png())
    rig.upload("admin", rig.frame + "/illustration/zephyr-air-b737.png?default_type=B738", _png())
    assert airline_default_types.load_default_types(rig.owned_dir) == {"zephyr-air": "A321"}
    assert _type_rows(_group(_editor(rig), "zephyr-air")) == ["A321", "B737"]


def test_a_picture_for_an_airline_with_an_airframe_keeps_that_airframe_as_default(rig):
    status, _headers = rig.upload(
        "admin", rig.frame + "/illustration/air-france-b737.png?default_type=B738", _png())
    assert status == 303
    assert airline_default_types.load_default_types(rig.owned_dir) == {}
    assert _type_rows(_group(_editor(rig), "air-france")) == ["A320", "B737"]


def test_every_type_row_uploads_with_its_own_type(rig):
    group = _group(_editor(rig), "transavia-france")
    actions = re.findall(r'<form class="airlines-art"[^>]* action="([^"]+)"', group)
    assert actions == [
        rig.frame + "/illustration/transavia-france-a320.png?default_type=A320",
        rig.frame + "/illustration/transavia-france.png?default_type=B737"]


def test_the_default_menu_item_is_offered_on_a_picture_type_only(rig):
    _override(rig, "air-france-b737")
    group = _group(_editor(rig), "air-france")
    assert group.count("Use as the airline&#x27;s default picture") + group.count(
        "Use as the airline's default picture") == 1


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
