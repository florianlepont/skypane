"""The Display page no longer carries a location picker and its save never
assigns a place: the controls are absent for every role, a crafted
`location_id` posted to the settings form moves nothing and writes no audit
row, and the frame's place stays reachable on the Location and detection
page. Every place here is an obviously generic fake."""

import pytest

from companion import prefs
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from provisioned_fleet import (
    ADMIN_EMAIL, USER_A_EMAIL, USER_B_EMAIL, device_dir, provision_fleet)
from server import device_config, fleet_db



class Rig:
    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.server = InProcessAppServer(state_dir)
        self.fleet = provision_fleet(state_dir)
        self.cookies = {
            "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL),
            "a": session_cookie_for_state_dir(state_dir, USER_A_EMAIL),
            "b": session_cookie_for_state_dir(state_dir, USER_B_EMAIL),
        }

    def add_location(self, name, owner=None):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.add_location(conn, name, 10.5, 20.5, "Europe/Paris", owner)
        finally:
            conn.close()

    def sql(self, sql, args=()):
        conn = fleet_db.connect(self.state_dir)
        try:
            rows = [tuple(row) for row in conn.execute(sql, args)]
            conn.commit()
            return rows
        finally:
            conn.close()

    def location_of(self, device_id):
        return self.sql("SELECT location_id FROM devices WHERE id = ?", (device_id,))[0][0]

    def get(self, path, who, headers=None):
        status, _headers, body = http_request(
            self.server.url(path), cookie=self.cookies[who], extra_headers=headers)
        return status, body.decode("utf-8")

    def display(self, device_id, who, headers=None):
        status, body = self.get("/devices/%s/display" % device_id, who, headers)
        assert status == 200
        return body

    def save_display(self, device_id, who, **fields):
        form = {"scope": "display", "return_to": "/display"}
        form.update(fields)
        return http_request(
            self.server.url("/devices/%s/settings" % device_id), method="POST",
            data=with_csrf(self.cookies[who], form), cookie=self.cookies[who],
            extra_headers={"Origin": self.server.base_url()})

    def config(self, device_id):
        return device_config.load_device_config(device_dir(self.state_dir, device_id))

    def audit(self):
        return [
            dict(zip(("action", "target_type", "target_id", "outcome", "detail"), row))
            for row in self.sql(
                "SELECT action, target_type, target_id, outcome, detail FROM audit_log "
                "WHERE action = 'location.update' ORDER BY id")]


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(tmp_path):
    built = Rig(str(tmp_path / "state"))
    yield built
    built.server.stop()


def _assert_no_picker(page):
    assert 'id="location-picker"' not in page
    assert 'name="location_id"' not in page
    assert "No location chosen." not in page


# --- markup -----------------------------------------------------------------------


@pytest.mark.parametrize("who", ["a", "admin"])
def test_display_serves_no_picker_even_with_locations_to_choose_from(rig, who):
    rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.add_location("Platform Place")
    page = rig.display(rig.fleet.a1, who)
    _assert_no_picker(page)
    assert "Alpha Place" not in page and "Platform Place" not in page


def test_display_serves_no_picker_for_the_live_frame_of_an_admin(rig):
    rig.add_location("Platform Place")
    status, page = rig.get("/devices/%s/display" % rig.fleet.live, "admin")
    assert status == 200
    _assert_no_picker(page)


def test_display_names_no_location_a_frame_already_has(rig):
    foreign = rig.add_location("Secret Neighbour Place", rig.fleet.b_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (foreign, rig.fleet.a1))
    page = rig.display(rig.fleet.a1, "a")
    _assert_no_picker(page)
    assert "Secret Neighbour Place" not in page


def test_display_in_french_has_no_picker_either(rig):
    rig.add_location("Alpha Place", rig.fleet.a_id)
    page = rig.display(rig.fleet.a1, "a", headers={"Accept-Language": "fr"})
    assert 'id="location-picker"' not in page and "Aucun lieu" not in page


def test_the_location_page_is_where_the_place_is_chosen(rig):
    status, page = rig.get("/devices/%s/detection" % rig.fleet.a1, "a")
    assert status == 200
    assert 'id="place-map"' in page and 'name="place_label"' in page
    assert 'name="location_id"' not in page


# --- saving -----------------------------------------------------------------------


def test_a_crafted_location_id_on_the_display_form_moves_nothing(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    neighbour = rig.add_location("Neighbour Place", rig.fleet.b_id)
    platform = rig.add_location("Platform Place")
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (mine, rig.fleet.a1))
    for who in ("a", "admin"):
        for crafted in (str(neighbour), str(platform), "", "999999", "abc", "-1"):
            status, headers, _ = rig.save_display(
                rig.fleet.a1, who, location_id=crafted, quiet_hours_start="01:02")
            assert status == 303, (who, crafted)
            assert "flash=saved" in headers["Location"], (who, crafted)
            assert rig.location_of(rig.fleet.a1) == mine, (who, crafted)
    assert rig.audit() == []


def test_a_crafted_location_id_assigns_nothing_to_a_frame_without_one(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    platform = rig.add_location("Platform Place")
    for target in (mine, platform):
        status, _headers, _ = rig.save_display(
            rig.fleet.a1, "admin", location_id=str(target))
        assert status == 303
        assert rig.location_of(rig.fleet.a1) is None
    assert rig.audit() == []


def test_a_save_without_the_field_leaves_the_location_alone(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (mine, rig.fleet.a1))
    status, _headers, _ = rig.save_display(rig.fleet.a1, "a", theme="black")
    assert status == 303
    assert rig.location_of(rig.fleet.a1) == mine
    assert rig.config(rig.fleet.a1)["theme"] == "black"


def test_a_user_still_cannot_post_to_a_frame_they_do_not_own(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    before = rig.config(rig.fleet.b1)
    status, _headers, body = rig.save_display(rig.fleet.b1, "a", location_id=str(mine))
    assert status == 404
    unknown = http_request(
        rig.server.url("/no-such-page-anywhere"), cookie=rig.cookies["a"])
    assert body == unknown[2]
    assert rig.location_of(rig.fleet.b1) is None
    assert rig.config(rig.fleet.b1) == before


def test_the_live_frame_form_is_still_refused_for_a_user(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    status, _headers, _body = http_request(
        rig.server.url("/settings"), method="POST",
        data=with_csrf(rig.cookies["a"], {"scope": "display", "location_id": str(mine)}),
        cookie=rig.cookies["a"], extra_headers={"Origin": rig.server.base_url()})
    assert status == 404
    assert rig.location_of(rig.fleet.live) is None


# --- reassignment -------------------------------------------------------------------


def test_after_a_reassignment_the_new_owner_starts_with_no_location(rig):
    old = rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (old, rig.fleet.a1))
    cookie = rig.cookies["admin"]
    status, _headers, _body = http_request(
        rig.server.url("/fleet/frames/%s/reassign" % rig.fleet.a1), method="POST",
        data=with_csrf(cookie, {"owner_user_id": str(rig.fleet.b_id)}), cookie=cookie)
    assert status == 303
    assert rig.location_of(rig.fleet.a1) is None
    assert "Alpha Place" not in rig.display(rig.fleet.a1, "b")
    status, _headers, _ = rig.save_display(rig.fleet.a1, "b", location_id=str(old))
    assert status == 303
    assert rig.location_of(rig.fleet.a1) is None
