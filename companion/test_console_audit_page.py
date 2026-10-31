"""The read-only Audit log page and the release audit events, over real HTTP."""
import hashlib
import re
import time

import pytest

import fleet_console_support as fx
from companion import console_pairing, prefs, routes, throttle
from companion.pages import audit_page, update_page
from companion_app_server import get, http_request, login, with_csrf
from server import atomic_io
from server import firmware_registry as fr
from skypane_fw_image import build_image

_NOW = "2026-09-28T12:00:00+00:00"
_RUNNING = "fw-v1.2.0"
_OLDER = "fw-v1.1.0"


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


_FUTURE = int(time.time()) + 100_000


def _append(state_dir, count, action="frame.register", outcome="ok", start=_FUTURE,
            actor=fx.ACTOR, target_id="d_00000001", target_type="device"):
    conn = fx.fleet_db.connect(state_dir)
    try:
        with fx.fleet_db.transaction(conn):
            for index in range(count):
                fx.fleet_db.audit_append(
                    conn, actor, action, target_type, target_id, outcome,
                    {"n": index}, now=start + index)
    finally:
        conn.close()


def _page(server, cookie, query=""):
    return fx.get(server, cookie, "/audit" + query)


def _rows(html):
    return re.findall(r"<tr><td>.*?</tr>", html, re.S)


def test_events_are_listed_newest_first_with_every_column(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 3, action="pairing.claim", start=_FUTURE)
    _append(server.state_dir, 1, action="device.retire", outcome="denied", start=_FUTURE + 100)
    status, _headers, html = _page(server, cookie)
    assert status == 200
    rows = _rows(html)
    assert "Frame retired" in rows[0] and "Refused" in rows[0]
    assert "Pairing code claimed" in rows[1] and "Success" in rows[1]
    assert 'class="time-value"' in rows[0]
    for head in ("When", "Who", "Action", "Target", "Outcome", "From"):
        assert "<th>%s</th>" % head in html
    assert "127.0.0.1" in rows[0]
    assert "pairing.claim" not in html and "device.retire" not in html


def test_ids_break_ties_newest_first(rig):
    server, _seed, cookie = rig
    conn = fx.fleet_db.connect(server.state_dir)
    try:
        with fx.fleet_db.transaction(conn):
            for action in ("user.invite", "user.role"):
                fx.fleet_db.audit_append(
                    conn, fx.ACTOR, action, "user", "1", "ok", None, now=_FUTURE)
    finally:
        conn.close()
    rows = _rows(_page(server, cookie)[2])
    assert "Role changed" in rows[0] and "User invited" in rows[1]


def test_fifty_rows_per_page_with_older_and_newer_links(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 120)
    count_before = len(fx.audit_rows(server.state_dir))
    html = _page(server, cookie)[2]
    assert len(_rows(html)) == 50
    assert 'href="/audit?page=2"' in html and ">Older<" in html and ">Newer<" not in html
    second = _page(server, cookie, "?page=2")[2]
    assert len(_rows(second)) == 50
    assert 'href="/audit"' in second and ">Newer<" in second and ">Older<" in second
    last = _page(server, cookie, "?page=3")[2]
    assert len(_rows(last)) == count_before - 100
    assert ">Older<" not in last and ">Newer<" in last


@pytest.mark.parametrize("raw", ["abc", "-3", "0", "", "1.5", "99999999999999999999",
                                 "999999", "%00", "%D9%A3"])
def test_odd_page_values_fall_back_safely(rig, raw):
    server, _seed, cookie = rig
    _append(server.state_dir, 60)
    status, _headers, html = _page(server, cookie, "?page=" + raw)
    assert status == 200
    assert 1 <= len(_rows(html)) <= 50


def test_the_chips_are_plain_links_and_filter(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 2, action="pairing.claim")
    _append(server.state_dir, 2, action="user.role")
    _append(server.state_dir, 1, action="release.install", outcome="failed")
    _append(server.state_dir, 1, action="device.retire", outcome="denied")
    html = _page(server, cookie)[2]
    nav = re.search(r'<nav class="filter-bar__chips audit-chips".*?</nav>', html, re.S).group(0)
    for label in ("All", "Pairing", "Frames", "Users", "Locations", "Releases", "Failed"):
        assert ">%s<" % label in nav
    assert "<script" not in nav and "<input" not in nav
    assert nav.count('aria-current="true"') == 1
    total = len(fx.audit_rows(server.state_dir))
    assert "%d events" % total in html
    pairing = _page(server, cookie, "?category=pairing")[2]
    assert "2 events" in pairing and len(_rows(pairing)) == 2
    users = _page(server, cookie, "?category=users")[2]
    assert "Role changed" in users and "Pairing code claimed" not in users
    failed = _page(server, cookie, "?category=failed")[2]
    assert "2 events" in failed
    assert "Failed" in failed and "Refused" in failed
    assert _page(server, cookie, "?category=bogus")[2].count("<tr><td>") == min(
        50, total)


def test_one_event_uses_the_singular_count(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 1, action="location.add", target_type="location")
    assert "1 event<" in _page(server, cookie, "?category=locations")[2]


def test_empty_states(app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    cookie = fx.admin_cookie(server.state_dir)
    html = _page(server, cookie)[2]
    assert "Nothing recorded yet" in html
    assert "Actions such as pairing, role changes and releases will appear here." in html
    filtered = _page(server, cookie, "?category=releases")[2]
    assert "No events match this filter" in filtered
    assert "empty-state--filter" in filtered
    assert "Choose All to see every event." in filtered


def test_a_failed_claim_row_shows_no_target_and_never_the_guess(rig, monkeypatch):
    server, seed, cookie = rig
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE", throttle.LockoutThrottle(limit=5, lockout_s=300))
    monkeypatch.setattr(
        console_pairing, "GLOBAL_THROTTLE", throttle.LockoutThrottle(limit=20, lockout_s=900))
    fx.issue_code(server.state_dir, seed.pending_id)
    guess = "WXYZ7654"
    status, _headers, _body = fx.post(server, cookie, "/fleet/pair", {
        "code": guess, "owner_user_id": str(seed.owner_id)})
    assert status == 200
    status, _headers, html = _page(server, cookie)
    assert status == 200
    assert guess not in html and fx.FAKE_CODE not in html
    row = _rows(html)[0]
    assert "Pairing code claimed" in row and "Failed" in row
    assert '<span class="cell-primary">-</span>' in row


def test_actor_and_target_texts(rig):
    server, seed, cookie = rig
    _append(server.state_dir, 1, actor=fx.fleet_db.AuditActor(None, "cli", None),
            action="frame.register", target_type="pending", target_id=seed.pending_id)
    _append(server.state_dir, 1, actor=fx.fleet_db.AuditActor(None, "frame:p_00000000", None),
            action="pairing.issue", target_type="pending", target_id="p_00000000")
    _append(server.state_dir, 1, actor=fx.fleet_db.AuditActor(seed.admin_id, fx.ADMIN_EMAIL, "1.2.3.4"),
            action="device.reassign", target_id=seed.owned_id, start=_FUTURE + 1000)
    rows = _rows(_page(server, cookie)[2])
    assert fx.ADMIN_EMAIL in rows[0] and "Kitchen" in rows[0] and seed.owned_id in rows[0]
    assert "<td>Frame</td>" in rows[1]
    assert "<td>System</td>" in rows[2]


def test_unknown_action_keys_get_a_generic_label(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 1, action="mystery.thing")
    html = _page(server, cookie)[2]
    assert "Other action" in html and "mystery.thing" not in html


def test_stored_text_is_escaped(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 1, actor=fx.fleet_db.AuditActor(
        None, "<script>alert(1)</script>", "<img src=x>"),
        target_id="<b>bold</b>")
    html = _page(server, cookie)[2]
    assert "<script>alert(1)" not in html and "<img src=x>" not in html
    assert "<b>bold</b>" not in html
    assert "&lt;script&gt;" in html


def test_the_page_is_read_only(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 3)
    html = _page(server, cookie)[2]
    body = html[html.index('<main'):] if "<main" in html else html
    assert "<form" not in body.split('class="filter-bar__chips')[1]
    assert "<button" not in body.split('class="filter-bar__chips')[1]
    audit_routes = [
        route for route in routes.ROUTES
        if (route.matcher.path if isinstance(route.matcher, routes.Exact)
            else route.matcher.prefix).startswith("/audit")]
    assert [(route.method, route.matcher) for route in audit_routes] == [
        ("GET", routes.Exact("/audit"))]
    status, _headers, _body = fx.post(server, cookie, "/audit", {})
    unknown = http_request(server.url("/no-such-path"), "POST", data=with_csrf(cookie, {}),
                           cookie=cookie)
    assert status == unknown[0] == 404


def test_users_and_anonymous_callers(rig):
    server, _seed, _cookie = rig
    assert fx.get(server, fx.user_cookie(server.state_dir), "/audit")[0] == 404
    status, headers, _ = http_request(server.url("/audit"))
    assert status in (302, 303) and headers["Location"]


def test_the_audit_page_has_french_text(rig):
    server, _seed, cookie = rig
    _append(server.state_dir, 1, action="pairing.claim")
    status, _headers, html = fx.get(server, cookie + "; sp_ui_lang=fr", "/audit")
    assert status == 200
    assert "Code d’association utilisé" in html
    assert "Journal d’audit" in html
    assert "Pairing code claimed" not in html


def test_every_action_label_has_a_french_string():
    from companion import i18n_fr
    for message in audit_page.ACTION_LABELS.values():
        assert message.msg_id in i18n_fr.BY_ID


# --- release events -----------------------------------------------------------


def _seed_releases(state_dir):
    import os
    os.makedirs(str(state_dir), exist_ok=True)
    for version in (_OLDER, _RUNNING):
        image_path = os.path.join(str(state_dir), version + ".bin")
        image = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image)
        fr.publish_release(str(state_dir), {
            "version": version, "sha256": hashlib.sha256(image).hexdigest(),
            "size": len(image), "released_at": _NOW, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY, "notes": ["release " + version],
        }, image_path, now=_NOW)
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), (
        '{"schema": 1, "next_seq": 1, "devices": {"dev1": {"fw_version": "%s", '
        '"reported_at": "%s", "events": []}}}' % (_RUNNING, _NOW)))


@pytest.fixture
def release_server(make_app_server):
    return make_app_server(seed=_seed_releases)


def _post(server, path, cookie, data=None):
    return http_request(
        server.base_url() + path, method="POST", data=with_csrf(cookie, data), cookie=cookie,
        extra_headers={"Origin": server.base_url()})


def test_install_and_cancel_write_audit_rows(release_server):
    server = release_server
    cookie = login(server)
    status, headers, _ = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _OLDER, "confirm": "yes"})
    assert status == 303 and headers["Location"] == "/update"
    status, headers, _ = _post(server, update_page.CANCEL_ROUTE, cookie)
    assert status == 303 and headers["Location"] == "/update"
    rows = fx.audit_rows(server.state_dir)
    install = [r for r in rows if r["action"] == "release.install"]
    cancel = [r for r in rows if r["action"] == "release.cancel"]
    assert len(install) == 1 and len(cancel) == 1
    assert install[0]["outcome"] == "ok" and cancel[0]["outcome"] == "ok"
    assert install[0]["target_id"] == fr.hardware.LEGACY_KEY
    assert install[0]["actor_label"] and install[0]["actor_user_id"] is not None
    assert _OLDER in install[0]["detail"]
    page = get(server, "/audit", cookie=cookie)[2].decode("utf-8")
    assert "Release install scheduled" in page and "Release install cancelled" in page


def test_a_refused_install_is_audited_as_failed(release_server):
    server = release_server
    cookie = login(server)
    status, headers, _ = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": "fw-v9.9.9", "confirm": "yes"})
    assert status == 303 and headers["Location"].startswith("/update?flash=")
    rows = [r for r in fx.audit_rows(server.state_dir) if r["action"] == "release.install"]
    assert [r["outcome"] for r in rows] == ["failed"]


def test_the_confirm_step_writes_no_audit_row(release_server):
    server = release_server
    cookie = login(server)
    status, _headers, _ = _post(
        server, update_page.INSTALL_ROUTE, cookie, {"version": _OLDER})
    assert status == 200
    assert fx.audit_rows(server.state_dir, "release.install") == []
