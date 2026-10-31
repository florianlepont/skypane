"""The per-frame Location picker on the Display page: what each role may
choose, the checked assignment through the Display save, the refusals for a
foreign location or frame, audit rows and the reset on reassignment. Every
place here is an obviously generic fake."""
import json
import re
import urllib.parse

import pytest

from companion import prefs
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from provisioned_fleet import (
    ADMIN_EMAIL, USER_A_EMAIL, USER_B_EMAIL, device_dir, provision_fleet)
from server import device_config, fleet_db

PICKER_ID = 'id="location-picker"'


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
            data=urllib.parse.urlencode(form).encode(), cookie=self.cookies[who],
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


def _options(body):
    select = re.search(r'<select id="location-picker".*?</select>', body, re.S)
    assert select, "no location select"
    return re.findall(r'<option value="([^"]*)"( selected)?>([^<]*)</option>', select.group(0))


# --- markup -----------------------------------------------------------------------


def test_a_user_picker_lists_only_their_own_locations_with_the_current_one_selected(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    other_mine = rig.add_location("Beta Place", rig.fleet.a_id)
    rig.add_location("Neighbour Place", rig.fleet.b_id)
    rig.add_location("Platform Place")
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (other_mine, rig.fleet.a1))
    body = rig.display(rig.fleet.a1, "a")
    assert _options(body) == [
        ("", "", "No location"), (str(mine), "", "Alpha Place"),
        (str(other_mine), " selected", "Beta Place")]
    assert "Neighbour Place" not in body and "Platform Place" not in body
    assert 'href="/locations">Manage locations</a>' in body


def test_the_select_is_part_of_the_settings_form(rig):
    rig.add_location("Alpha Place", rig.fleet.a_id)
    body = rig.display(rig.fleet.a1, "a")
    form_id = re.search(r'<form class="config-form" id="([^"]+)"', body).group(1)
    select = re.search(r'<select id="location-picker"[^>]*>', body).group(0)
    assert 'form="%s"' % form_id in select and 'name="location_id"' in select


def test_with_no_location_a_user_sees_a_note_and_an_add_link(rig):
    body = rig.display(rig.fleet.a1, "a")
    assert PICKER_ID not in body
    assert "No location chosen." in body
    assert 'href="/locations">Add a location</a>' in body


def test_an_admin_picker_lists_every_location_including_ownerless(rig):
    ids = [
        rig.add_location("Alpha Place", rig.fleet.a_id),
        rig.add_location("Neighbour Place", rig.fleet.b_id),
        rig.add_location("Platform Place")]
    body = rig.display(rig.fleet.a1, "admin")
    assert [option[0] for option in _options(body)] == [""] + [str(i) for i in ids]


def test_an_admin_display_without_any_location_has_no_picker(rig):
    body = rig.display(rig.fleet.a1, "admin")
    assert PICKER_ID not in body and "No location chosen." not in body
    assert "Manage locations" not in body


def test_the_live_frame_page_of_an_admin_shows_the_picker(rig):
    rig.add_location("Platform Place")
    status, body = rig.get("/display", "admin")
    assert status == 200 and PICKER_ID in body


def test_a_location_an_admin_assigned_to_a_user_frame_is_kept_and_not_named(rig):
    foreign = rig.add_location("Secret Neighbour Place", rig.fleet.b_id)
    rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (foreign, rig.fleet.a1))
    body = rig.display(rig.fleet.a1, "a")
    assert "Secret Neighbour Place" not in body
    assert (str(foreign), " selected", "Assigned by an administrator") in _options(body)
    status, _headers, _body = rig.save_display(
        rig.fleet.a1, "a", location_id=str(foreign), quiet_hours_start="21:30")
    assert status == 303
    assert rig.location_of(rig.fleet.a1) == foreign
    assert rig.audit() == []


def test_the_picker_is_in_french(rig):
    rig.add_location("Alpha Place", rig.fleet.a_id)
    body = rig.display(rig.fleet.a1, "a", headers={"Accept-Language": "fr"})
    assert "Gérer les lieux" in body and "Aucun lieu" in body


def test_the_picker_with_no_location_is_in_french(rig):
    body = rig.display(rig.fleet.a1, "a", headers={"Accept-Language": "fr"})
    assert "Aucun lieu choisi." in body and "Ajouter un lieu" in body


# --- saving -----------------------------------------------------------------------


def test_saving_a_location_the_user_owns_assigns_it_and_empty_clears_it(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    status, headers, _ = rig.save_display(rig.fleet.a1, "a", location_id=str(mine))
    assert status == 303
    assert headers["Location"].startswith("/devices/%s/" % rig.fleet.a1)
    assert "flash=saved" in headers["Location"]
    assert rig.location_of(rig.fleet.a1) == mine
    status, _headers, _ = rig.save_display(rig.fleet.a1, "a", location_id="")
    assert status == 303
    assert rig.location_of(rig.fleet.a1) is None


def test_a_save_without_the_field_leaves_the_location_alone(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (mine, rig.fleet.a1))
    status, _headers, _ = rig.save_display(rig.fleet.a1, "a", quiet_hours_start="21:30")
    assert status == 303
    assert rig.location_of(rig.fleet.a1) == mine


def test_the_assignment_is_audited_and_changes_nothing_else_in_the_config(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    before = rig.config(rig.fleet.a1)
    assert rig.save_display(rig.fleet.a1, "a", location_id=str(mine))[0] == 303
    assert rig.config(rig.fleet.a1) == before
    audit = rig.audit()
    assert len(audit) == 1
    assert audit[0]["target_type"] == "device" and audit[0]["target_id"] == rig.fleet.a1
    assert audit[0]["outcome"] == "ok"
    assert json.loads(audit[0]["detail"]) == {"location_id": mine}


def test_an_unchanged_value_writes_no_audit_row(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (mine, rig.fleet.a1))
    assert rig.save_display(rig.fleet.a1, "a", location_id=str(mine))[0] == 303
    assert rig.audit() == []


def test_a_refused_assignment_changes_nothing_and_shows_the_save_failed_toast(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    neighbour = rig.add_location("Neighbour Place", rig.fleet.b_id)
    platform = rig.add_location("Platform Place")
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (mine, rig.fleet.a1))
    config_before = rig.config(rig.fleet.a1)
    for crafted in (str(neighbour), str(platform), "999999", "abc", "-1", "1e3"):
        status, headers, _ = rig.save_display(
            rig.fleet.a1, "a", location_id=crafted, quiet_hours_start="01:02")
        assert status == 303, crafted
        assert "flash=save_failed" in headers["Location"], crafted
        assert rig.location_of(rig.fleet.a1) == mine, crafted
    assert rig.config(rig.fleet.a1) == config_before
    denied = [row for row in rig.audit() if row["outcome"] == "denied"]
    assert len(denied) == 6


def test_a_failed_config_save_puts_the_location_back(rig, monkeypatch):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    config_before = rig.config(rig.fleet.a1)

    def refuse(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(device_config, "save_device_config", refuse)
    status, headers, _ = rig.save_display(
        rig.fleet.a1, "a", location_id=str(mine), quiet_hours_start="01:02")
    assert status == 303 and "flash=save_failed" in headers["Location"]
    assert rig.location_of(rig.fleet.a1) is None
    assert rig.config(rig.fleet.a1) == config_before
    assert [row["outcome"] for row in rig.audit()] == ["ok", "failed"]
    assert json.loads(rig.audit()[-1]["detail"]) == {
        "location_id": None, "reason": "settings_save_failed"}


def test_a_user_cannot_assign_a_location_to_a_frame_they_do_not_own(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    before = rig.config(rig.fleet.b1)
    status, headers, body = rig.save_display(rig.fleet.b1, "a", location_id=str(mine))
    assert status == 404
    unknown = http_request(
        rig.server.url("/no-such-page-anywhere"), cookie=rig.cookies["a"])
    assert body == unknown[2]
    assert rig.location_of(rig.fleet.b1) is None
    assert rig.config(rig.fleet.b1) == before


def test_the_live_frame_form_is_refused_for_a_user(rig):
    mine = rig.add_location("Alpha Place", rig.fleet.a_id)
    status, _headers, _body = http_request(
        rig.server.url("/settings"), method="POST",
        data=urllib.parse.urlencode(
            {"scope": "display", "location_id": str(mine)}).encode(),
        cookie=rig.cookies["a"], extra_headers={"Origin": rig.server.base_url()})
    assert status == 404
    assert rig.location_of(rig.fleet.live) is None


def test_an_admin_may_assign_any_location(rig):
    neighbour = rig.add_location("Neighbour Place", rig.fleet.b_id)
    platform = rig.add_location("Platform Place")
    for target in (neighbour, platform):
        status, headers, _ = rig.save_display(rig.fleet.a1, "admin", location_id=str(target))
        assert status == 303 and "flash=saved" in headers["Location"]
        assert rig.location_of(rig.fleet.a1) == target
    status, headers, _ = rig.save_display(rig.fleet.a1, "admin", location_id="999999")
    assert "flash=save_failed" in headers["Location"]
    assert rig.location_of(rig.fleet.a1) == platform


def test_the_picker_field_is_ignored_on_the_device_scope(rig):
    platform = rig.add_location("Platform Place")
    status, _headers, _ = rig.save_display(
        rig.fleet.a1, "admin", scope="device", return_to="/device",
        location_id=str(platform))
    assert status == 303
    assert rig.location_of(rig.fleet.a1) is None


# --- reassignment -------------------------------------------------------------------


def test_after_a_reassignment_the_new_owner_starts_with_no_location(rig):
    old = rig.add_location("Alpha Place", rig.fleet.a_id)
    rig.add_location("Beta Place", rig.fleet.b_id)
    rig.sql("UPDATE devices SET location_id = ? WHERE id = ?", (old, rig.fleet.a1))
    cookie = rig.cookies["admin"]
    status, _headers, _body = http_request(
        rig.server.url("/fleet/frames/%s/reassign" % rig.fleet.a1), method="POST",
        data=with_csrf(cookie, {"owner_user_id": str(rig.fleet.b_id)}), cookie=cookie)
    assert status == 303
    assert rig.location_of(rig.fleet.a1) is None
    body = rig.display(rig.fleet.a1, "b")
    assert "Alpha Place" not in body
    assert [name for _value, _selected, name in _options(body)] == ["No location", "Beta Place"]
    status, headers, _ = rig.save_display(rig.fleet.a1, "b", location_id=str(old))
    assert status == 303 and "flash=save_failed" in headers["Location"]
    assert rig.location_of(rig.fleet.a1) is None
