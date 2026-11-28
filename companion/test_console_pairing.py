# SPDX-License-Identifier: AGPL-3.0-only
"""The Fleet register handler and an administrator's pairing on the Add a frame
page over real HTTP: validation, the identical refusal, throttling, audit
contents, the concurrent claim, the owner choice and CSRF and role gating."""
import json
import re
import threading

import pytest

import fleet_console_support as fx
from companion import console_pairing, console_routes, prefs, routes, throttle
from companion.pages import pair_frame_page
from companion_app_server import http_request
from server import fleet_db, hardware, pairing_code

PAIR_PATH = "/pair-frame"
WRONG_CODE = "KKKK2222"
GUESS = "MMMM3333"


@pytest.fixture(autouse=True)
def _english_and_fresh_throttles(monkeypatch):
    prefs.set_request_prefs(lang="en")
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE",
        throttle.LockoutThrottle(limit=5, lockout_s=300))
    monkeypatch.setattr(
        console_pairing, "GLOBAL_THROTTLE",
        throttle.LockoutThrottle(limit=20, lockout_s=900))
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    return server, seed, fx.admin_cookie(server.state_dir)


def _pair(server, cookie, code, owner_id):
    return fx.post(server, cookie, PAIR_PATH, {
        "code": code, "owner_user_id": str(owner_id)})


def _pair_card(page):
    return re.search(r'<form class="pair-form[ \"].*?</form>', page, re.S).group(0)


def _refusal_page(server, cookie, headers):
    """The page a refusal redirects to, with the cookie that keeps the code."""
    assert headers["Location"].startswith(PAIR_PATH + "?refused=1")
    kept = headers["Set-Cookie"].split(";", 1)[0]
    status, page_headers, page = fx.get(
        server, cookie + "; " + kept, headers["Location"])
    assert status == 200 and page_headers["Cache-Control"] == "no-store"
    return page


def _refused(server, cookie, code, owner_id):
    """(status, page) of one refused claim, the redirect followed."""
    status, headers, _body = _pair(server, cookie, code, owner_id)
    assert status == 303
    return status, _refusal_page(server, cookie, headers)


def _count(state_dir, table, where="1=1"):
    conn = fleet_db.connect(state_dir)
    try:
        return conn.execute("SELECT count(*) FROM %s WHERE %s" % (table, where)).fetchone()[0]
    finally:
        conn.close()


def _flash_page(server, cookie, headers):
    cookies = [value.split(";")[0] for key, value in headers.items()
               if key.lower() == "set-cookie" and value.startswith("sp_flash=")]
    return fx.get(server, cookie + "; " + cookies[0], "/fleet")[2]


def test_the_paths_match_the_console_route_constants():
    assert console_pairing.FLEET_PATH == console_routes.FLEET_ROUTE
    assert console_pairing.REGISTER_PATH == console_routes.FLEET_REGISTER_ROUTE
    assert console_pairing.PAIR_FRAME_PATH == pair_frame_page.PAIR_FRAME_ROUTE
    assert not hasattr(console_routes, "FLEET_PAIR_ROUTE")


# --- register ------------------------------------------------------------


@pytest.mark.parametrize("typed", [
    "AA:BB:CC:DD:EE:F1", "aa-bb-cc-dd-ee-f2", "aabbccddeef3"])
def test_register_accepts_the_three_mac_spellings(rig, typed):
    server, _seed, cookie = rig
    status, headers, _body = fx.post(server, cookie, "/fleet/register", {
        "mac": typed, "secret_sha256": fx.SECRET_HASH.upper(),
        "hardware_type": hardware.LEGACY_KEY})
    assert status == 303 and headers["Location"] == "/fleet"
    conn = fleet_db.connect(server.state_dir)
    try:
        row = fleet_db.get_pending_by_mac(
            conn, "aa:bb:cc:dd:ee:f" + typed[-1])
    finally:
        conn.close()
    assert row is not None and row["status"] == "pending"
    rows = fx.audit_rows(server.state_dir, "frame.register")
    assert rows[-1]["outcome"] == "ok" and rows[-1]["actor_label"] == fx.ADMIN_EMAIL
    assert "Frame registered" in _flash_page(server, cookie, headers)


@pytest.mark.parametrize("secret", [
    "ab" * 16, "g" * 64, fx.SECRET_HASH + "0", "", "raw secret value"])
def test_register_refuses_anything_that_is_not_64_hex_and_does_not_echo_it(rig, secret):
    server, _seed, cookie = rig
    before = _count(server.state_dir, "pending_devices")
    audited = len(fx.audit_rows(server.state_dir, "frame.register"))
    status, _headers, body = fx.post(server, cookie, "/fleet/register", {
        "mac": fx.MAC_NEW, "secret_sha256": secret, "hardware_type": hardware.LEGACY_KEY})
    assert status == 400 and "Enter the 64-character hash." in body
    assert _count(server.state_dir, "pending_devices") == before
    assert len(fx.audit_rows(server.state_dir, "frame.register")) == audited
    if secret:
        assert secret not in body


def test_register_field_errors_for_mac_and_hardware(rig):
    server, _seed, cookie = rig
    status, _headers, body = fx.post(server, cookie, "/fleet/register", {
        "mac": "not-a-mac", "secret_sha256": fx.SECRET_HASH, "hardware_type": "nope"})
    assert status == 400
    assert "Enter a valid MAC address." in body
    assert "Choose the hardware type." in body
    assert "Enter the 64-character hash." not in body


def test_register_duplicate_mac_gives_the_error_flash(rig):
    server, _seed, cookie = rig
    status, headers, _body = fx.post(server, cookie, "/fleet/register", {
        "mac": fx.MAC_PENDING.upper(), "secret_sha256": fx.SECRET_HASH,
        "hardware_type": hardware.LEGACY_KEY})
    assert status == 303
    assert "A frame with this address is already registered." in _flash_page(
        server, cookie, headers)
    assert len(fx.audit_rows(server.state_dir, "frame.register")) == 1


def test_register_never_stores_a_raw_secret_field(rig):
    server, _seed, cookie = rig
    raw = "raw-secret-that-must-not-land-anywhere"
    status, _headers, _body = fx.post(server, cookie, "/fleet/register", {
        "mac": fx.MAC_NEW, "secret_sha256": fx.SECRET_HASH, "secret": raw,
        "hardware_type": hardware.LEGACY_KEY})
    assert status == 303
    assert raw not in fx.dump_database_text(server.state_dir)


# --- claim ----------------------------------------------------------------


def test_a_valid_code_pairs_the_frame_to_the_chosen_owner(rig):
    server, seed, cookie = rig
    status, headers, _body = _pair(server, cookie, "abcd-2345", seed.owner_id)
    assert status == 303 and headers["Location"] == "/fleet"
    page = _flash_page(server, cookie, headers)
    assert "Frame paired" in page and fx.OWNER_EMAIL in page
    assert "next update" in page
    conn = fleet_db.connect(server.state_dir)
    try:
        device = fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
    finally:
        conn.close()
    assert device is not None and device["owner_user_id"] == seed.owner_id
    assert 'href="/fleet?frame=%s"' % device["id"] in page
    ok = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
          if row["outcome"] == "ok"]
    assert len(ok) == 1 and ok[0]["actor_label"] == fx.ADMIN_EMAIL
    detail = json.loads(ok[0]["detail"])
    assert detail["owner_user_id"] == seed.owner_id
    assert ok[0]["actor_user_id"] == seed.admin_id
    assert fx.FAKE_CODE not in fx.dump_database_text(server.state_dir)


def _refusal_cases(server, seed):
    fx.issue_code(server.state_dir, seed.pending_id, fx.FAKE_CODE)
    conn = fleet_db.connect(server.state_dir)
    try:
        expired_pending = fleet_db.register_pending(
            conn, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY, None)
    finally:
        conn.close()
    fx.issue_code(server.state_dir, expired_pending, fx.OTHER_FAKE_CODE, ttl_s=-60)
    return {
        "wrong": "kkkk-2222", "expired": fx.OTHER_FAKE_CODE.lower(),
        "malformed": "no", "used": fx.FAKE_CODE}


def test_wrong_expired_used_and_malformed_codes_get_one_identical_answer(rig):
    server, seed, cookie = rig
    cases = _refusal_cases(server, seed)
    assert _pair(server, cookie, cases["used"], seed.owner_id)[0] == 303
    answers = {}
    for name, code in cases.items():
        status, page = _refused(server, cookie, code, seed.owner_id)
        card = _pair_card(page)
        typed = re.search(r'id="pair-code"[^>]*value="([^"]*)"', card).group(1)
        # A code outside the alphabet is not kept at all.
        assert typed in ("", code.strip().upper())
        answers[name] = (status, card.replace(typed, "TYPED") if typed else card)
        assert "Code not recognised" in card and "Check the code and try again." in card
    assert len({answer[0] for answer in answers.values()}) == 1
    assert len({re.sub(r'value="[^"]*"', "", answer[1]) for answer in answers.values()}) == 1
    failed = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
              if row["outcome"] == "failed"]
    assert len(failed) == 4
    assert all(json.loads(row["detail"]) == {"reason": "invalid"} for row in failed)


def test_the_typed_value_is_escaped_in_the_input(rig):
    server, seed, cookie = rig
    for _ in range(5):
        _refused(server, cookie, WRONG_CODE, seed.owner_id)
    status, _headers, body = _pair(server, cookie, '"><b>x</b>', seed.owner_id)
    assert status == 429
    assert "<b>x</b>" not in body and "&lt;B&gt;X&lt;/B&gt;" in body


def test_the_guess_is_stored_nowhere_and_echoed_only_into_the_input(rig):
    server, seed, cookie = rig
    status, headers, body = _pair(server, cookie, GUESS, seed.owner_id)
    assert status == 303 and GUESS not in body
    assert GUESS not in headers["Location"]
    body = _refusal_page(server, cookie, headers)
    assert body.count(GUESS) == 1
    assert re.search(r'id="pair-code"[^>]*value="%s"' % GUESS, body)
    assert GUESS not in fx.dump_database_text(server.state_dir)
    # The code rides only in the two-minute cookie of the form's own path.
    assert GUESS not in "\n".join(
        str(v) for k, v in headers.items() if k.lower() != "set-cookie")
    assert not any(GUESS in title for title in re.findall(r'title="[^"]*"', body))
    assert GUESS not in headers["Location"]


def test_five_failures_lock_the_session_and_no_code_is_evaluated_after(rig, monkeypatch):
    server, seed, cookie = rig
    calls = []
    original = pairing_code.match_candidates
    monkeypatch.setattr(
        pairing_code, "match_candidates",
        lambda *args, **kw: (calls.append(1), original(*args, **kw))[1])
    for _ in range(5):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 303
    evaluated = len(calls)
    for _ in range(2):
        status, _headers, body = _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)
        assert status == 429 and "Too many attempts" in body
        assert "Frame paired" not in body
    assert len(calls) == evaluated
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 0
    rows = fx.audit_rows(server.state_dir, "pairing.claim")
    throttled = [row for row in rows if "throttled" in row["detail"]]
    assert len(throttled) == 1 and len(rows) == 6
    other = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 303


def test_twenty_failures_across_sessions_lock_everyone(rig):
    server, seed, _cookie = rig
    for index in range(5):
        cookie = fx.admin_cookie(server.state_dir, "extra%d@example.test" % index)
        for _ in range(4):
            assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 303
    fresh = fx.admin_cookie(server.state_dir, "fresh@example.test")
    status, _headers, body = _pair(server, fresh, fx.FAKE_CODE, seed.owner_id)
    assert status == 429 and "Too many attempts" in body
    rows = fx.audit_rows(server.state_dir, "pairing.claim")
    assert len([row for row in rows if "throttled" in row["detail"]]) == 1


def test_a_success_resets_the_session_counter_but_not_the_global_one(
        rig, monkeypatch):
    server, seed, cookie = rig
    for _ in range(3):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 303
    assert _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)[0] == 303
    for _ in range(5):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 303
    assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 429
    # Global: success must not reset its count.
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE", throttle.LockoutThrottle(100, 300))
    monkeypatch.setattr(
        console_pairing, "GLOBAL_THROTTLE", throttle.LockoutThrottle(4, 900))
    other = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    fx.issue_code(server.state_dir, seed.pending_id, fx.FAKE_CODE)
    conn = fleet_db.connect(server.state_dir)
    try:
        second = fleet_db.register_pending(
            conn, fx.MAC_NEW, fx.SECRET_HASH, hardware.LEGACY_KEY, None)
    finally:
        conn.close()
    fx.issue_code(server.state_dir, second, fx.OTHER_FAKE_CODE)
    for _ in range(3):
        assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 303
    assert _pair(server, other, fx.OTHER_FAKE_CODE, seed.owner_id)[0] == 303
    assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 303
    assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 429


def test_two_simultaneous_claims_of_one_code_have_exactly_one_winner(rig):
    server, seed, cookie = rig
    second = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    barrier = threading.Barrier(2)
    results = []

    def run(who, owner_id):
        barrier.wait()
        results.append(_pair(server, who, fx.FAKE_CODE, owner_id))

    threads = [
        threading.Thread(target=run, args=(cookie, seed.owner_id)),
        threading.Thread(target=run, args=(second, seed.user_id))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert [result[0] for result in results] == [303, 303]
    where = sorted(result[1]["Location"].split("?")[0] for result in results)
    assert where == ["/fleet", PAIR_PATH]
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 1
    loser = next(result for result in results if result[1]["Location"].startswith(PAIR_PATH))
    assert "Code not recognised" in _refusal_page(server, second, loser[1])


def test_missing_fields_are_400_and_are_not_counted(rig, monkeypatch):
    server, seed, cookie = rig
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE", throttle.LockoutThrottle(1, 300))
    status, _headers, body = _pair(server, cookie, "", seed.owner_id)
    assert status == 400 and "Enter the pairing code." in body
    status, _headers, body = fx.post(server, cookie, PAIR_PATH, {"code": WRONG_CODE})
    assert status == 400 and "Choose an owner." in body
    status, _headers, body = fx.post(server, cookie, PAIR_PATH, {
        "code": WRONG_CODE, "owner_user_id": "abc"})
    assert status == 400
    assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 303
    invalid = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
               if "invalid" in row["detail"]]
    assert len(invalid) == 1


def test_a_disabled_owner_is_refused_and_the_code_stays_valid(rig):
    server, seed, cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_user_disabled(conn, fx.OWNER_EMAIL, True)
    finally:
        conn.close()
    status, _headers, body = _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)
    assert status == 400 and "That user is no longer available." in body
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 0
    assert _pair(server, cookie, fx.FAKE_CODE, seed.user_id)[0] == 303


def test_the_register_route_and_the_pairing_page_keep_their_gates(rig):
    server, seed, cookie = rig
    found = routes.match("POST", "/fleet/register", "")
    assert found is not None and found[0].csrf is True
    assert found[0].access == routes.ADMIN_ONLY
    found = routes.match("POST", PAIR_PATH, "")
    assert found is not None and found[0].csrf is True
    assert found[0].access == routes.SIGNED_IN
    form = ("code=%s&owner_user_id=%d" % (fx.FAKE_CODE, seed.owner_id)).encode()
    status, _headers, _body = http_request(
        server.url(PAIR_PATH), "POST", data=form, cookie=cookie)
    assert status == 403
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 0
    assert not fx.audit_rows(server.state_dir, "pairing.claim")
    user = fx.user_cookie(server.state_dir)
    unknown = fx.get(server, user, "/no-such-page-anywhere")
    status, _headers, body = fx.post(server, user, "/fleet/register", {"mac": fx.MAC_NEW})
    assert status == 404 and body == unknown[2]
    status, headers, _body = http_request(
        server.url("/fleet/register"), "POST", data=b"x=1")
    assert status == 303 and "/login" in headers["Location"]


def test_the_old_pairing_route_is_gone(rig):
    server, seed, cookie = rig
    assert routes.match("POST", "/fleet/pair", "") is None
    status, _headers, _body = _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)
    assert status == 303
    status, _headers, _body = fx.post(server, cookie, "/fleet/pair", {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)})
    assert status == 404
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 1


def test_the_old_fleet_pair_link_leads_to_the_page(rig):
    server, _seed, cookie = rig
    status, headers, _body = fx.get(server, cookie, "/fleet?pair=1")
    assert (status, headers["Location"]) == (303, PAIR_PATH)
    status, _headers, page = fx.get(server, cookie, "/fleet")
    assert status == 200 and "dlg-add-frame" not in page
    assert 'class="fleet-add-button" href="/pair-frame"' in page


def test_an_inactive_or_unknown_owner_is_refused(rig):
    server, seed, cookie = rig
    for owner in ("9999", "0", "x", " "):
        status, body = fx.post(server, cookie, PAIR_PATH, {
            "code": fx.FAKE_CODE, "owner_user_id": owner})[::2]
        assert status == 400, owner
        assert ("Choose an owner." in body) or ("no longer available" in body)
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 0
    assert _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)[0] == 303


def test_a_refused_code_keeps_the_owner_choice(rig):
    server, seed, cookie = rig
    _status, page = _refused(server, cookie, WRONG_CODE, seed.owner_id)
    chosen = re.findall(r'<option value="(\d+)" selected', page)
    assert chosen == [str(seed.owner_id)]


def test_an_administrator_sees_the_owner_picker_with_themselves_first(rig):
    server, seed, cookie = rig
    page = _pair_card(fx.get(server, cookie, PAIR_PATH)[2])
    options = re.findall(r'<option value="(\d+)"( selected)?>([^<]*)</option>', page)
    assert options[0][0] == str(seed.admin_id) and options[0][1] == " selected"
    assert {value for value, _sel, _label in options} == {
        str(seed.admin_id), str(seed.owner_id), str(seed.admin2_id), str(seed.user_id)}
    assert 'name="owner_user_id"' in page and ">Owner<" in page
    status, _headers, french = http_request(
        server.url(PAIR_PATH), cookie=cookie, extra_headers={"Accept-Language": "fr"})
    assert status == 200 and ">Propri\u00e9taire<" in french.decode("utf-8")


def test_an_administrator_without_script_pairs_the_frame_to_the_chosen_user(rig):
    server, seed, cookie = rig
    status, headers, _body = _pair(server, cookie, fx.FAKE_CODE, seed.user_id)
    assert status == 303 and headers["Location"] == "/fleet"
    conn = fleet_db.connect(server.state_dir)
    try:
        assert fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)["owner_user_id"] == seed.user_id
    finally:
        conn.close()


def test_an_administrator_choosing_themselves_lands_on_the_frame(rig):
    server, seed, cookie = rig
    status, headers, _body = _pair(server, cookie, fx.FAKE_CODE, seed.admin_id)
    assert status == 303 and headers["Location"].endswith("/?flash=frame_paired")
    conn = fleet_db.connect(server.state_dir)
    try:
        assert fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)["owner_user_id"] == seed.admin_id
    finally:
        conn.close()


def test_a_plain_user_has_no_owner_field_and_cannot_pair_to_another_owner(rig):
    server, seed, _cookie = rig
    user = fx.user_cookie(server.state_dir)
    page = fx.get(server, user, PAIR_PATH)[2]
    assert "owner_user_id" not in page and "pair-owner" not in page
    status, headers, _body = fx.post(server, user, PAIR_PATH, {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)})
    assert status == 303 and headers["Location"].endswith("/?flash=frame_paired")
    conn = fleet_db.connect(server.state_dir)
    try:
        device = fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
    finally:
        conn.close()
    assert device["owner_user_id"] == seed.user_id
    ok = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
          if row["outcome"] == "ok"]
    assert json.loads(ok[0]["detail"])["owner_user_id"] == seed.user_id
