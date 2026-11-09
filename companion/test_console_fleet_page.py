"""The admin Fleet page: one list row per frame, row menus and dialogs by
state, absence of secret material, the empty state, role gating and French
rendering."""
import re

import pytest

import fleet_console_support as fx
from companion import console_routes, prefs
from server import fleet_db


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_device_token(conn, fx.MAC_OWNED, "tok-fake-owned")
        fleet_db.set_pending_token(conn, fx.MAC_PENDING, "tok-fake-pending")
    finally:
        conn.close()
    fx.issue_code(server.state_dir, seed.pending_id)
    return server, seed, fx.admin_cookie(server.state_dir)


def _list_html(page):
    """The `<ul>` markup of every entity list on the page, main list first."""
    return re.findall(r'<ul class="entity-list">.*?</ul>', page, re.S)


def _rows(page):
    """{frame id or name: row markup} for every list row on the page."""
    rows = {}
    for lists in _list_html(page):
        for row in re.findall(r'<li class="entity-row.*?</li>', lists, re.S):
            title = re.search(r'entity-row__title"[^>]*>([^<]*)<', row).group(1)
            link = re.search(r'href="/devices/([^/"]+)/"', row)
            rows[link.group(1) if link else title] = row
    return rows


def _dialog(page, dialog_id):
    match = re.search(
        r'<dialog class="modal" id="%s".*?</dialog>' % re.escape(dialog_id), page, re.S)
    return match.group(0) if match else None


def _slug(frame_id):
    return frame_id.lower().replace("_", "-")


def _text(markup):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


def _header(page):
    """The selected frame's detail header markup, or None."""
    match = re.search(r'<div class="fleet-detail-head">.*?</div>', page, re.S)
    return match.group(0) if match else None


def test_the_frame_list_is_the_strip_and_the_other_frames_block(fleet):
    server, seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert status == 200
    assert "<table" not in page and "<th" not in page
    for frame_id in (seed.owned_id, seed.live_id):
        assert 'href="/fleet?frame=%s"' % frame_id in page
    # Live frames are strip tiles, not list rows; the list holds the others.
    rows = _rows(page)
    assert list(rows) == ["New frame", "Attic"]
    header = _header(page)
    # The frame's name is the frame button's label; the header is two link
    # buttons (its personal view and Rename) and repeats neither the name nor the owner.
    assert _text(header) == "Open personal view Rename"
    assert 'aria-label="Rename Kitchen"' in header
    # The owner is named once, in the Access section, not repeated in the header.
    assert fx.OWNER_EMAIL not in _text(header)
    assert seed.owned_id not in _text(header)
    pending = rows["New frame"]
    assert "Waiting for pairing" in pending and 'href="#dlg-add-frame"' in pending
    assert fx.MAC_PENDING not in page
    retired = rows["Attic"]
    assert "Formerly %s" % fx.OWNER_EMAIL in retired and "/devices/" not in retired
    other = re.search(r'<section class="group-block fleet-block fleet-block--state '
                      r'fleet-block--others".*?</section>', page, re.S).group(0)
    assert "Other frames (2)" in other and "dot--hollow" in other
    assert "fleet-other" not in other
    assert "Retired frames" not in page and "need attention" not in page


def test_add_a_frame_lives_only_in_the_strip_and_there_is_no_register_form(fleet):
    server, _seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    header = re.search(r'<div class="page-header">.*?</div>', page, re.S).group(0)
    assert "dlg-add-frame" not in header and "Add a frame" not in header
    assert "page-header__actions" not in header
    assert page.count("frame-row--add") == 1
    assert '<a class="frame-row frame-row--add" href="#dlg-add-frame" data-modal-open>' in page
    assert page.rindex("frame-row--add") > page.rindex("frame-row--system")
    assert page.index("frame-menu__list") < page.index("page-header")
    assert "<h1" in header and ">Fleet<" in header
    for text in ("Register a frame", "Register frame", 'name="mac"', 'name="secret_sha256"',
                 'action="/fleet/register"', "MAC address"):
        assert text not in page, text


def test_one_status_dot_per_row_with_the_shared_vocabulary(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    rows = _rows(page)
    assert 'aria-label="Not seen yet"' in page
    assert 'aria-label="Waiting for pairing"' in rows["New frame"]
    assert "dot--hollow" in rows["New frame"] and "dot--hollow" in rows["Attic"]
    assert 'aria-label="Retired"' in rows["Attic"]


def test_actions_menus_follow_the_frame_state(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    rows = _rows(page)
    owned = _header(page)
    prefix = "/devices/%s" % seed.owned_id
    assert "Open frame" not in owned
    assert re.findall(r'class="row-action"[^>]*>([^<]*)<', owned) == [
        "Open personal view", "Rename"]
    assert 'href="%s/"' % prefix in owned
    assert 'href="%s/frame/name?return_to=%%2Ffleet%%3Fframe%%3D%s"' % (
        prefix, seed.owned_id) in owned
    # Health and Device are sections of the page, no menu entries; access, reassign and retire
    # are inline in the Access section (the retire link opens the one confirmation dialog).
    assert "/health" not in owned and '/device"' not in owned
    assert "dlg-access" not in page
    assert 'href="#dlg-reassign-%s" class="row-action"' % _slug(seed.owned_id) in page
    assert 'href="#dlg-retire-%s" class="fleet-retire__link"' % _slug(seed.owned_id) in page
    assert 'action="%s%s%s"' % (
        console_routes.FRAME_ACTION_PREFIX, seed.owned_id,
        console_routes.FRAME_REASSIGN_SUFFIX) in page
    assert 'aria-label="Rename Kitchen"' in owned
    _status, _headers, live_page = fx.get(server, cookie, "/fleet?frame=%s" % seed.live_id)
    live = _header(live_page)
    assert "dlg-retire-%s" % _slug(seed.live_id) not in live_page
    assert "Only the owner changes. Nothing is erased." in live_page
    assert re.findall(r'class="row-action"[^>]*>([^<]*)<', live) == [
        "Open personal view", "Rename"]
    assert re.findall(r'class="row-menu__item[^"]*"[^>]*>([^<]*)<', rows["New frame"]) == [
        "Pair frame"]
    retired = rows["Attic"]
    assert 'href="#dlg-reactivate-%s"' % _slug(seed.retired_id) in retired
    assert "dlg-retire" not in retired and "dlg-reassign" not in retired
    assert _dialog(live_page, "dlg-retire-%s" % _slug(seed.live_id)) is None
    assert "{owner_email}" not in page


def test_dialogs_post_to_the_unchanged_routes_with_csrf(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    prefix = console_routes.FRAME_ACTION_PREFIX
    # A live frame's dialogs dismiss back to that frame's view.
    cases = (
        ("dlg-add-frame", "/fleet/pair", "/fleet"),
        ("dlg-retire-" + _slug(seed.owned_id),
         prefix + seed.owned_id + console_routes.FRAME_RETIRE_SUFFIX,
         "/fleet?frame=" + seed.owned_id + "&amp;tab=access"),
        ("dlg-reactivate-" + _slug(seed.retired_id),
         prefix + seed.retired_id + console_routes.FRAME_REACTIVATE_SUFFIX, "/fleet"))
    for dialog_id, action, dismiss in cases:
        dialog = _dialog(page, dialog_id)
        assert dialog is not None, dialog_id
        assert 'action="%s"' % action in dialog and 'name="csrf_token"' in dialog
        assert ' open' not in dialog.split(">", 1)[0]
        assert 'href="%s" data-modal-close' % dismiss in dialog
    retire = _dialog(page, "dlg-retire-" + _slug(seed.owned_id))
    assert "Retire \u201cKitchen\u201d?" in retire and "Keep frame" in retire
    assert "btn--danger" in retire and "Retire frame" in retire
    # A confirm-only dialog focuses its dismiss link, so Enter never confirms.
    assert re.search(r'<a class="modal__dismiss"[^>]* autofocus', retire)
    # Reassign is a button beside the owner that opens one confirmation dialog.
    _status, _headers, frame_page = fx.get(server, cookie, "/fleet?frame=" + seed.owned_id)
    reassign = _dialog(frame_page, "dlg-reassign-" + _slug(seed.owned_id))
    assert reassign is not None
    assert 'action="%s"' % (
        prefix + seed.owned_id + console_routes.FRAME_REASSIGN_SUFFIX) in reassign
    assert 'name="csrf_token"' in reassign
    assert "%s&#x27;s settings" % fx.OWNER_EMAIL in reassign
    assert "<select" in reassign and " required" in reassign
    assert "Reassign \u201cKitchen\u201d?" in reassign and "Keep current owner" in reassign
    reactivate = _dialog(page, "dlg-reactivate-" + _slug(seed.retired_id))
    assert "Keep retired" in reactivate and "Re-activate frame" in reactivate
    assert "{owner_email}" not in page


def test_ordering_puts_problems_first_then_others_by_name_then_pending(fleet):
    from companion.pages import fleet_page
    base = fleet_page.FleetRow(
        kind="live", frame_id="d_a", name="Zeta", mono_id="d_a", owner_email="a@x",
        previous_owner=False, hardware="h", last_seen=1.0, battery_percent=90,
        is_live_frame=False, offline=False)
    rows = [
        base,
        base._replace(frame_id="d_b", name="Alpha"),
        base._replace(frame_id="d_c", name="Mid", last_seen=None),
        base._replace(frame_id="d_d", name="Gone", offline=True),
        base._replace(frame_id="p_e", name="x", kind="pending", last_seen=None),
        base._replace(frame_id="p_f", name="Attic", kind="retired"),
        base._replace(frame_id="d_g", name="Low", battery_percent=3),
    ]
    ordered = [row.frame_id for row in fleet_page.sort_rows(rows)]
    assert ordered == ["d_d", "d_g", "d_c", "d_b", "d_a", "p_e", "p_f"]


def test_the_markup_carries_no_secret_material(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    conn = fleet_db.connect(server.state_dir)
    try:
        stored_code_hash = conn.execute(
            "SELECT code_hash FROM pending_devices WHERE id = ?", (seed.pending_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    for secret in (
            fx.SECRET_HASH, "tok-fake-owned", "tok-fake-pending", fx.FAKE_CODE,
            "ABCD-2345", stored_code_hash, "code_expires_at", "code_hash", "code_salt"):
        assert secret not in page, secret


def test_the_empty_state_and_the_add_dialog(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_user_disabled(conn, fx.USER_EMAIL, True)
    finally:
        conn.close()
    cookie = fx.admin_cookie(server.state_dir)
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    assert "No frames yet" in page and "<table" not in page
    assert "Switch a frame on. When its pairing code appears" in page
    dialog = _dialog(page, "dlg-add-frame")
    assert dialog is not None and "Pair frame" in dialog and "Back to Fleet" in dialog
    owners = re.search(r'<select id="pair-owner".*?</select>', dialog, re.S).group(0)
    assert "Choose an owner" in owners
    assert fx.ADMIN_EMAIL in owners and fx.OWNER_EMAIL in owners
    assert fx.USER_EMAIL not in owners
    assert 'value="%d"' % seed.user_id not in owners
    assert "No frame is showing a code yet" in dialog
    assert "confirm(" not in page and "Register a frame" not in page


def test_the_pair_hint_disappears_when_a_frame_waits(fleet):
    server, _seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    assert "No frame is showing a code yet" not in page
    assert "confirm(" not in page


def test_the_add_dialog_is_open_only_with_the_pair_flag_or_a_refusal(fleet):
    server, _seed, cookie = fleet
    _status, _headers, plain = fx.get(server, cookie, "/fleet")
    _status, _headers, flagged = fx.get(server, cookie, "/fleet?pair=1")
    assert " open" not in _dialog(plain, "dlg-add-frame").split(">", 1)[0]
    assert " open" in _dialog(flagged, "dlg-add-frame").split(">", 1)[0]


def test_a_refused_pair_reopens_the_dialog_with_the_escaped_code_and_field_errors(fleet):
    server, seed, cookie = fleet
    status, _headers, page = fx.post(server, cookie, "/fleet/pair", {
        "code": '"><b>x</b>', "owner_user_id": str(seed.owner_id)})
    assert status == 200
    dialog = _dialog(page, "dlg-add-frame")
    assert " open" in dialog.split(">", 1)[0]
    assert "<b>x</b>" not in page
    assert 'aria-invalid="true"' in dialog and "Code not recognised" in dialog
    status, _headers, page = fx.post(server, cookie, "/fleet/pair", {"code": "abcd-2345"})
    assert status == 400
    dialog = _dialog(page, "dlg-add-frame")
    assert " open" in dialog.split(">", 1)[0] and "Choose an owner." in dialog
    assert 'aria-describedby="dlg-add-frame-owner-error"' in dialog


def test_a_user_gets_the_unknown_path_404_and_anonymous_the_sign_in_redirect(fleet):
    server, _seed, _cookie = fleet
    user = fx.user_cookie(server.state_dir)
    refused = fx.get(server, user, "/fleet")
    unknown = fx.get(server, user, "/no-such-page-anywhere")
    assert refused[0] == 404 and refused[2] == unknown[2]
    status, headers, _body = fx.get(server, None, "/fleet")
    assert status == 303 and "/login" in headers["Location"]


def test_french_rendering_uses_the_console_terms(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.owned_id,
        headers={"Accept-Language": "fr"})
    for term in ("Flotte", "Ajouter un cadre", "Retiré", "Associer le cadre",
                 "En attente d\u2019association", "Retour \u00e0 la flotte",
                 "Autres cadres (2)", "Garder le cadre", "Laisser retiré",
                 "Retirer ce cadre", "Renommer Kitchen",
                 "Anciennement", "Nouveau cadre"):
        assert term in page, term
    assert "Pair frame" not in page and "Waiting for pairing" not in page
    assert "Cadres</h1>" not in page and ">Cadres<" not in page


def test_a_long_frame_name_is_escaped_into_the_row_and_dialog_titles(fleet):
    server, seed, cookie = fleet
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute(
            "UPDATE devices SET name = ? WHERE id = ?", ('<i>x</i>' * 20, seed.owned_id))
        conn.commit()
    finally:
        conn.close()
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    assert "<i>x</i>" not in page and "&lt;i&gt;x&lt;/i&gt;" in page
