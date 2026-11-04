"""The frame chip and card sheet in the personal space: which frames the sheet
lists for a user and for an administrator, the same-page links, the footer
link and the escaping of names and owner emails. Rendered in-process over a
seeded fleet.
"""
import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import access, device_scope, prefs, ui_shell
from companion_markup import parse_html
from server import fleet_db, hardware

_SECRET = "d" * 64


@pytest.fixture(autouse=True)
def _reset_scope():
    yield
    device_scope.set_request_scope(None, ())
    prefs.set_request_principal(None)


@pytest.fixture
def fleet(tmp_path):
    (tmp_path / "state").mkdir()
    state_dir = str(tmp_path / "state")
    return state_dir, seed_matrix_fleet(state_dir)


def _add_device(state_dir, owner_id, suffix, name):
    conn = fleet_db.connect(state_dir)
    try:
        return fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:%02x" % suffix, _SECRET, hardware.LEGACY_KEY,
            owner_id, name=name, state_path="auto")
    finally:
        conn.close()


def _principal(seeded, who):
    ids = {"owner": seeded.owner_id, "other": seeded.other_id, "admin": seeded.admin_id}
    emails = {"owner": OWNER_EMAIL, "other": OTHER_EMAIL, "admin": ADMIN_EMAIL}
    role = "admin" if who == "admin" else "user"
    return access.Principal(access.KIND_USER, ids[who], emails[who], role)


def _enter(state_dir, principal, current_id):
    devices = device_scope.load_devices_for(state_dir, principal)
    current = next(d for d in devices if d.id == current_id)
    prefs.set_request_principal(principal.role, principal.role)
    device_scope.set_request_scope(current, devices, principal.user_id, state_dir)
    return current


def _rows(html):
    return parse_html(html).select("dialog.frame-sheet a.frame-card")


def test_one_frame_renders_nothing(fleet):
    state_dir, seeded = fleet
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    assert ui_shell.frame_switcher_html("display") == ""


def test_two_frames_list_both_with_the_current_one_marked(fleet):
    state_dir, seeded = fleet
    second = _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    rows = _rows(ui_shell.frame_switcher_html("display"))
    assert len(rows) == 2
    assert {r.attrs["href"] for r in rows} == {
        "/devices/%s/display" % seeded.owner_device, "/devices/%s/display" % second}
    current = [r for r in rows if r.attrs.get("aria-current") == "true"]
    assert [r.attrs["href"] for r in current] == [
        "/devices/%s/display" % seeded.owner_device]


def test_the_link_keeps_the_page(fleet):
    state_dir, seeded = fleet
    second = _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    for page, slug in (("flights", "/flights"), ("health", "/health")):
        hrefs = {r.attrs["href"] for r in _rows(ui_shell.frame_switcher_html(page))}
        assert "/devices/%s%s" % (second, slug) in hrefs


def test_a_user_gets_manage_my_frames_and_no_fleet_link(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    root = parse_html(ui_shell.frame_switcher_html("display"))
    links = {a.attrs["href"] for a in root.select(".frame-sheet__footer a")}
    assert links == {"/account#account-frames"}
    assert "/fleet" not in ui_shell.frame_switcher_html("display")


def test_an_administrator_gets_no_fleet_link_or_all_frames_entry(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.admin_id, 0x12, "Mine")
    _add_device(state_dir, seeded.admin_id, 0x13, "Mine too")
    admin = _principal(seeded, "admin")
    mine = [d for d in device_scope.load_devices(state_dir) if d.owner_user_id == seeded.admin_id]
    _enter(state_dir, admin, mine[0].id)
    root = parse_html(ui_shell.frame_switcher_html("display"))
    links = {a.attrs["href"] for a in root.select(".frame-sheet__footer a")}
    assert links == {"/account#account-frames"}
    html = ui_shell.frame_switcher_html("display")
    assert "/fleet" not in html
    assert "All frames" not in html


def test_an_administrators_list_is_their_own_frames_plus_the_one_viewed(fleet):
    state_dir, seeded = fleet
    mine_a = _add_device(state_dir, seeded.admin_id, 0x12, "Mine")
    mine_b = _add_device(state_dir, seeded.admin_id, 0x13, "Mine too")
    admin = _principal(seeded, "admin")
    _enter(state_dir, admin, mine_a)
    ids = {r.attrs["href"] for r in _rows(ui_shell.frame_switcher_html("display"))}
    assert ids == {"/devices/%s/display" % mine_a, "/devices/%s/display" % mine_b}
    html = _enter_foreign_and_render(state_dir, seeded, admin)
    rows = _rows(html)
    assert len(rows) == 3
    note = parse_html(html).select_one(
        'a[href="/devices/%s/display"] .frame-card__note' % seeded.owner_device)
    assert note.text().strip() == OWNER_EMAIL
    assert "/devices/%s/display" % seeded.other_device not in html


def _enter_foreign_and_render(state_dir, seeded, admin):
    _enter(state_dir, admin, seeded.owner_device)
    return ui_shell.frame_switcher_html("display")


def test_an_administrator_with_one_frame_and_no_other_sees_no_switcher(fleet):
    state_dir, seeded = fleet
    _enter(state_dir, _principal(seeded, "admin"), seeded.owner_device)
    assert ui_shell.frame_switcher_html("display") == ""


def test_a_co_managed_frame_is_marked_shared_with_its_owner(fleet):
    state_dir, seeded = fleet
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.add_co_manager(conn, seeded.other_device, seeded.owner_id, seeded.admin_id)
    finally:
        conn.close()
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    html = ui_shell.frame_switcher_html("display")
    note = parse_html(html).select_one(
        'a[href="/devices/%s/display"] .frame-card__note' % seeded.other_device)
    assert note is not None and note.text().strip() == "Shared by " + OTHER_EMAIL
    owned = parse_html(html).select_one(
        'a[href="/devices/%s/display"] .frame-card__note' % seeded.owner_device)
    assert "@" not in owned.text()


def test_names_are_escaped(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, '<img src=x onerror="y">')
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    html = ui_shell.frame_switcher_html("display")
    assert "<img" not in html
    assert "&lt;img" in html


def test_a_global_page_has_no_switcher(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, _principal(seeded, "owner"), seeded.owner_device)
    assert ui_shell.frame_switcher_html("update") == ""
