"""The frame chip and card sheet markup: the chip, the shared-modal sheet, the
card contents and the two list rules (personal pages and Console frame pages),
in English and French. Rendered in-process over a seeded fleet.
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


def _enter(state_dir, role, user_id, email, current_id):
    principal = access.Principal(access.KIND_USER, user_id, email, role)
    devices = device_scope.load_devices_for(state_dir, principal)
    current = next(d for d in devices if d.id == current_id)
    prefs.set_request_principal(role, role)
    device_scope.set_request_scope(current, devices, user_id, state_dir)
    return current


def _cards(html):
    return parse_html(html).select("dialog.frame-sheet a.frame-card")


def test_the_chip_opens_the_sheet_through_the_hash_link(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    current = _enter(state_dir, "user", seeded.owner_id, OWNER_EMAIL, seeded.owner_device)
    root = parse_html(ui_shell.frame_switcher_html("display"))
    chip = root.select_one("a.frame-chip")
    assert chip.attrs["href"] == "#dlg-frames"
    assert "data-modal-open" in chip.attrs
    assert chip.attrs["aria-label"] == "Switch frame, current: %s" % current.name
    sheet = root.select_one("dialog.modal.frame-sheet#dlg-frames")
    assert sheet.select_one(".modal__title").text().strip() == "Choose a frame"
    assert sheet.select_one("a.modal__dismiss").text().strip() == "Close"


def test_the_sheet_is_french_in_french(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, "user", seeded.owner_id, OWNER_EMAIL, seeded.owner_device)
    prefs.set_request_prefs(lang="fr")
    try:
        root = parse_html(ui_shell.frame_switcher_html("display"))
    finally:
        prefs.set_request_prefs(lang="en")
    assert root.select_one(".modal__title").text().strip() == "Choisir un cadre"
    assert root.select_one(".frame-sheet__footer a").text().strip() == "Gérer mes cadres"
    hidden = [n.text().strip() for n in root.select(".frame-card[aria-current] .visually-hidden")]
    assert "Actuel" in hidden
    assert root.select_one("a.frame-chip").attrs["aria-label"].startswith("Changer de cadre")


def test_the_current_card_carries_the_marks_and_the_owned_card_the_hardware(fleet):
    state_dir, seeded = fleet
    second = _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, "user", seeded.owner_id, OWNER_EMAIL, seeded.owner_device)
    cards = _cards(ui_shell.frame_switcher_html("flights"))
    current = [c for c in cards if c.attrs.get("aria-current") == "true"]
    assert [c.attrs["href"] for c in current] == ["/devices/%s/flights" % seeded.owner_device]
    assert "Current" in [n.text().strip() for n in current[0].select(".visually-hidden")]
    assert current[0].select_one("svg")
    other = next(c for c in cards if c.attrs["href"] == "/devices/%s/flights" % second)
    assert "Current" not in other.text()
    label = hardware.REGISTRY[hardware.LEGACY_KEY].label
    assert other.select_one(".frame-card__note").text().strip() == label


def test_a_user_never_receives_another_users_email(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.owner_id, 0x11, "Desk")
    _enter(state_dir, "user", seeded.owner_id, OWNER_EMAIL, seeded.owner_device)
    html = ui_shell.frame_switcher_html("display")
    assert OTHER_EMAIL not in html and ADMIN_EMAIL not in html


def test_hostile_names_and_emails_are_escaped(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.admin_id, 0x12, '<script>alert("a")</script>')
    _add_device(state_dir, seeded.admin_id, 0x13, "Mine too")
    _enter(
        state_dir, "admin", seeded.admin_id, ADMIN_EMAIL,
        next(d.id for d in device_scope.load_devices(state_dir)
             if d.owner_user_id == seeded.admin_id))
    html = ui_shell.frame_switcher_html("health")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def _console_html(state_dir, seeded, active):
    _enter(
        state_dir, "admin", seeded.admin_id, ADMIN_EMAIL,
        device_scope.load_devices(state_dir)[0].id)
    return ui_shell.frame_switcher_html(active)


@pytest.mark.parametrize("active", ["health", "device", "airlines/manage"])
def test_console_pages_list_every_frame_with_the_owner_email(fleet, active):
    state_dir, seeded = fleet
    page = {"health": "/health", "device": "/device", "airlines/manage": "/airlines/manage"}[active]
    html = _console_html(state_dir, seeded, active)
    cards = _cards(html)
    hrefs = {c.attrs["href"] for c in cards}
    assert hrefs >= {
        "/devices/%s%s" % (seeded.owner_device, page),
        "/devices/%s%s" % (seeded.other_device, page)}
    notes = {c.attrs["href"]: c.select_one(".frame-card__note").text().strip() for c in cards}
    assert notes["/devices/%s%s" % (seeded.owner_device, page)] == OWNER_EMAIL
    assert notes["/devices/%s%s" % (seeded.other_device, page)] == OTHER_EMAIL


def test_console_cards_put_problems_first_then_sort_by_name(fleet):
    state_dir, seeded = fleet
    html = _console_html(state_dir, seeded, "health")
    words = [
        c.select_one('[role="img"]').attrs["aria-label"] for c in _cards(html)]
    ranked = [0 if w == "No contact" else 1 if w in ("Not seen yet", "Overdue", "Low battery")
              else 2 for w in words]
    assert ranked == sorted(ranked)


def test_the_personal_page_of_an_administrator_has_no_console_list(fleet):
    state_dir, seeded = fleet
    _add_device(state_dir, seeded.admin_id, 0x12, "Mine")
    _add_device(state_dir, seeded.admin_id, 0x13, "Mine too")
    mine = [d for d in device_scope.load_devices(state_dir) if d.owner_user_id == seeded.admin_id]
    _enter(state_dir, "admin", seeded.admin_id, ADMIN_EMAIL, mine[0].id)
    html = ui_shell.frame_switcher_html("display")
    assert OWNER_EMAIL not in html and OTHER_EMAIL not in html
    assert len(_cards(html)) == 2
