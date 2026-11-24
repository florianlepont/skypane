"""Renaming an airline the owner named by hand: POST /airlines/rename/manual is the
administrator's, carries the session token, renames every prefix of the carrier in one
write, refuses a name another airline has, carries the artwork and the default aircraft
type of the old name, is audited, and is visible on every frame."""
import html
import os
import re
import shutil
import types

import pytest

import fleet_console_support as fx
from companion import airline_actions, device_scope
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import fleet_db
from server.plane import airline_default_types, illustrations, manual_resolutions, name_overrides

CO_EMAIL = "co-manager@example.test"
ROUTE = "/airlines/rename/manual"
EDITOR = "/airlines/manage"
STAMP = "2026-01-01T00:00:00+00:00"
VENDORED_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)
        self.frame = "/devices/%s" % seed.owned_id
        self.root = server.state_dir

    def post(self, who, form, path=None, token=True):
        cookie = self.cookies.get(who)
        data = with_csrf(cookie, form) if token else with_csrf(None, form)
        status, headers, body = http_request(
            self.server.url(path or self.frame + ROUTE), method="POST", cookie=cookie, data=data,
            extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def get(self, who, path):
        status, headers, body = http_request(self.server.url(path), cookie=self.cookies.get(who))
        return status, headers, body.decode("utf-8", "replace")

    def registry(self):
        return manual_resolutions.load_manual_resolutions(self.root)

    def files(self):
        out = {}
        for base, _dirs, names in os.walk(self.root):
            for name in names:
                if name.endswith(("-wal", "-shm")) or name.startswith(("fleet.db", "history.db")):
                    continue
                path = os.path.join(base, name)
                with open(path, "rb") as fh:
                    out[os.path.relpath(path, self.root)] = fh.read()
        return out

    def audit(self):
        return fx.audit_rows(self.root, "airline.rename_manual")


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()
    manual_resolutions.add_entry(state_dir, "OCN", "Oceanic", now=STAMP)
    manual_resolutions.add_entry(state_dir, "OCP", "Oceanic", now=STAMP)
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air", now=STAMP)
    yield Rig(server, seed, cookies)
    server.stop()


def _flash(headers):
    return re.search(r"flash=([a-z_]+)", headers["Location"]).group(1)


def test_an_administrator_renames_every_prefix_of_the_carrier_and_the_change_is_audited(rig):
    status, headers, _b = rig.post("admin", {"prefix": "OCN", "airline_name": "Oceanic Airways"})
    assert status == 303 and headers["Location"].startswith(rig.frame + EDITOR)
    assert _flash(headers) == "airline_renamed"
    registry = rig.registry()
    assert registry["OCN"]["airline_name"] == registry["OCP"]["airline_name"] == "Oceanic Airways"
    assert registry["OCN"]["created_at"] != STAMP
    assert registry["ZPH"] == {"airline_name": "Zephyr Air", "created_at": STAMP}
    (row,) = rig.audit()
    assert row["target_id"] == "oceanic-airways"
    assert "Oceanic" in row["detail"] and "Oceanic Airways" in row["detail"]


def test_the_new_name_is_what_every_other_frame_reads(rig):
    rig.post("admin", {"prefix": "ZPH", "airline_name": "Zephyr Airways"})
    assert manual_resolutions.load_manual_resolutions(rig.owned_dir)["ZPH"]["airline_name"] == "Zephyr Airways"
    other = [d for d in device_scope.load_devices(rig.root) if d.state_dir != rig.owned_dir][0]
    assert manual_resolutions.load_manual_resolutions(other.state_dir)["ZPH"]["airline_name"] == "Zephyr Airways"
    _s, _h, page = rig.get("admin", "/devices/%s%s" % (other.id, EDITOR))
    assert "Zephyr Airways" in page and "Zephyr Air<" not in html.unescape(page).replace("Zephyr Airways", "")


def test_a_case_only_change_keeps_the_group_and_only_changes_the_shown_name(rig):
    status, headers, _b = rig.post("admin", {"prefix": "ZPH", "airline_name": "ZEPHYR AIR"})
    assert _flash(headers) == "airline_renamed"
    assert rig.registry()["ZPH"]["airline_name"] == "ZEPHYR AIR"


REFUSALS = (
    ({"prefix": "ZPH", "airline_name": ""}, "manual_name_empty"),
    ({"prefix": "ZPH", "airline_name": "   "}, "manual_name_empty"),
    ({"prefix": "ZPH", "airline_name": "x" * 101}, "manual_name_too_long"),
    ({"prefix": "ZPH", "airline_name": "generic-x"}, "manual_name_reserved"),
    ({"prefix": "ZPH", "airline_name": "../x"}, "manual_name_unusable"),
    ({"prefix": "ZPH", "airline_name": "Air France"}, "airline_rename_taken"),
    ({"prefix": "ZPH", "airline_name": "Oceanic"}, "airline_rename_taken"),
    ({"prefix": "NOP", "airline_name": "Fine Name"}, "airline_rename_stale"),
    ({"prefix": "AFR", "airline_name": "Fine Name"}, "airline_rename_stale"),
    ({"prefix": "Z1", "airline_name": "Fine Name"}, "airline_rename_stale"),
    ({"airline_name": "Fine Name"}, "airline_rename_stale"),
)


@pytest.mark.parametrize("form,flash_key", REFUSALS)
def test_a_refusal_changes_no_file_and_writes_no_audit_row(rig, form, flash_key):
    name_overrides.set_names(rig.root, ["TVF"], "Skyline", own_builtin_name="Transavia France")
    before = rig.files()
    status, headers, _b = rig.post("admin", form)
    assert status == 303 and _flash(headers) == flash_key
    assert rig.files() == before
    assert rig.audit() == []


def test_a_name_held_by_an_override_is_refused(rig):
    name_overrides.set_names(rig.root, ["TVF"], "Skyline", own_builtin_name="Transavia France")
    before = rig.files()
    _s, headers, _b = rig.post("admin", {"prefix": "ZPH", "airline_name": "skyline"})
    assert _flash(headers) == "airline_rename_taken" and rig.files() == before


def test_a_prefix_the_static_table_now_covers_cannot_be_renamed_here(rig):
    manual_resolutions.add_entry(rig.root, "KLM", "Klm Old Name", now=STAMP)
    before = rig.files()
    _s, headers, _b = rig.post("admin", {"prefix": "KLM", "airline_name": "Another"})
    assert _flash(headers) == "airline_rename_stale" and rig.files() == before


def test_a_missing_or_wrong_token_is_refused_and_changes_nothing(rig):
    before = rig.files()
    status, _h, _b = rig.post("admin", {"prefix": "ZPH", "airline_name": "Fine Name"}, token=False)
    assert status == 403
    assert rig.files() == before and rig.audit() == []


def _put_png(directory, key):
    path = illustrations.override_path_for_key(key, directory)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy(VENDORED_PNG, path)
    return path


def test_the_artwork_and_the_default_type_follow_the_new_name_and_the_old_ones_stay(rig):
    slug = illustrations.type_slug("A320")
    base = _put_png(rig.owned_dir, "zephyr-air")
    typed = _put_png(rig.owned_dir, "zephyr-air-" + slug)
    airline_default_types.set_default_type(rig.owned_dir, "zephyr-air", "A320")
    status, headers, _b = rig.post("admin", {"prefix": "ZPH", "airline_name": "Zephyr Airways"})
    assert _flash(headers) == "airline_renamed"
    new_base = illustrations.override_path_for_key("zephyr-airways", rig.owned_dir)
    new_typed = illustrations.override_path_for_key("zephyr-airways-" + slug, rig.owned_dir)
    assert open(new_base, "rb").read() == open(base, "rb").read()
    assert open(new_typed, "rb").read() == open(typed, "rb").read()
    assert os.path.exists(base) and os.path.exists(typed)
    defaults = airline_default_types.load_default_types(rig.owned_dir)
    assert defaults == {"zephyr-air": "A320", "zephyr-airways": "A320"}
    # Renaming back finds the old pictures without copying over anything.
    rig.post("admin", {"prefix": "ZPH", "airline_name": "Zephyr Air"})
    assert rig.registry()["ZPH"]["airline_name"] == "Zephyr Air"
    assert os.path.exists(base)


def test_an_existing_picture_of_the_new_name_is_not_overwritten(rig):
    _put_png(rig.owned_dir, "zephyr-air")
    other = illustrations.override_path_for_key("zephyr-airways", rig.owned_dir)
    os.makedirs(os.path.dirname(other), exist_ok=True)
    with open(other, "wb") as fh:
        fh.write(b"mine")
    rig.post("admin", {"prefix": "ZPH", "airline_name": "Zephyr Airways"})
    assert open(other, "rb").read() == b"mine"


def test_a_copy_failure_is_logged_and_does_not_fail_the_rename(rig, monkeypatch, capsys):
    _put_png(rig.owned_dir, "zephyr-air")

    def boom(path, data):
        raise OSError("read-only")
    monkeypatch.setattr(airline_actions, "atomic_io", types.SimpleNamespace(atomic_write=boom))
    _s, headers, _b = rig.post("admin", {"prefix": "ZPH", "airline_name": "Zephyr Airways"})
    assert _flash(headers) == "airline_renamed"
    assert "could not carry artwork" in capsys.readouterr().out
    assert rig.registry()["ZPH"]["airline_name"] == "Zephyr Airways"


def test_the_built_in_rename_still_carries_the_artwork_through_the_shared_function(rig):
    base = _put_png(rig.owned_dir, "air-france")
    status, headers, _b = rig.post(
        "admin", {"airline": "Air France", "airline_name": "AF Test"}, path=rig.frame + "/airlines/rename")
    assert status == 303
    assert os.path.exists(illustrations.override_path_for_key("af-test", rig.owned_dir))
    assert os.path.exists(base)


@pytest.mark.parametrize("who,expect", (("owner", 404), ("co", 404), ("anonymous", 303)))
def test_only_an_administrator_can_rename(rig, who, expect):
    before = rig.files()
    status, headers, _b = rig.post(who, {"prefix": "ZPH", "airline_name": "Fine Name"})
    assert status == expect
    if who == "anonymous":
        assert headers["Location"].startswith("/login")
    assert rig.files() == before and rig.audit() == []


def test_a_get_on_the_route_is_not_routed(rig):
    assert rig.get("admin", rig.frame + ROUTE)[0] == 404


def test_the_editor_offers_rename_on_a_hand_named_row_and_not_on_a_built_in_or_superseded_one(rig):
    manual_resolutions.add_entry(rig.root, "KLM", "Klm Old Name", now=STAMP)
    _s, _h, page = rig.get("admin", rig.frame + EDITOR)
    row = next(r for r in re.findall(r"<tbody.*?</tbody>", page, re.S) if "Zephyr Air" in r)
    assert 'name="prefix" value="ZPH"' in row
    assert row.index(">Rename<") < row.index("Delete my name")
    assert html.escape(rig.frame + ROUTE) in row or (rig.frame + ROUTE) in row
    assert page.count('name="prefix" value="KLM"') == 0
    assert "Flights already stored keep their name." in page


def test_a_hostile_stored_name_is_escaped_everywhere_in_the_row_and_dialog(rig):
    hostile = 'Evil <b onmouseover="x()">&\' Air'
    manual_resolutions.add_entry(rig.root, "EVL", hostile, now=STAMP)
    _s, _h, page = rig.get("admin", rig.frame + EDITOR)
    assert "<b onmouseover" not in page
    assert html.escape(hostile) in page or html.escape(hostile, quote=False) in page
