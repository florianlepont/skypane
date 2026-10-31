"""The Fleet register and pair handlers over real HTTP: validation, the
identical refusal, throttling, audit contents, the concurrent claim and
CSRF and role gating."""
import json
import re
import threading

import pytest

import fleet_console_support as fx
from companion import console_pairing, console_routes, prefs, routes, throttle
from companion_app_server import http_request
from server import fleet_db, hardware, pairing_code

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
    return fx.post(server, cookie, "/fleet/pair", {
        "code": code, "owner_user_id": str(owner_id)})


def _pair_card(page):
    return re.search(
        r'<section[^>]*aria-labelledby="fleet-pair".*?</section>', page, re.S).group(0)


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
    assert console_pairing.PAIR_PATH == console_routes.FLEET_PAIR_ROUTE


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
    assert 'data-frame="%s" data-kind="live"' % device["id"] in page
    ok = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
          if row["outcome"] == "ok"]
    assert len(ok) == 1 and ok[0]["actor_label"] == fx.ADMIN_EMAIL
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
        status, headers, body = _pair(server, cookie, code, seed.owner_id)
        assert status == 200, name
        assert headers["Cache-Control"] == "no-store"
        card = _pair_card(body)
        typed = re.search(r'id="pair-code"[^>]*value="([^"]*)"', card).group(1)
        assert typed == code.strip().upper()
        answers[name] = (status, card.replace(typed, "TYPED"))
        assert "Code not recognised" in card and "Check the code and try again." in card
    assert len(set(answers.values())) == 1
    failed = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
              if row["outcome"] == "failed"]
    assert len(failed) == 4
    assert all(json.loads(row["detail"]) == {"reason": "invalid"} for row in failed)


def test_the_typed_value_is_escaped_in_the_input(rig):
    server, seed, cookie = rig
    _status, _headers, body = _pair(server, cookie, '"><b>x</b>', seed.owner_id)
    assert "<b>x</b>" not in body and "&lt;B&gt;X&lt;/B&gt;" in body


def test_the_guess_is_stored_nowhere_and_echoed_only_into_the_input(rig):
    server, seed, cookie = rig
    status, headers, body = _pair(server, cookie, GUESS, seed.owner_id)
    assert status == 200
    assert body.count(GUESS) == 1
    assert re.search(r'id="pair-code"[^>]*value="%s"' % GUESS, body)
    assert GUESS not in fx.dump_database_text(server.state_dir)
    assert GUESS not in "\n".join(str(v) for v in headers.values())
    assert not any(GUESS in title for title in re.findall(r'title="[^"]*"', body))


def test_five_failures_lock_the_session_and_no_code_is_evaluated_after(rig, monkeypatch):
    server, seed, cookie = rig
    calls = []
    original = pairing_code.match_candidates
    monkeypatch.setattr(
        pairing_code, "match_candidates",
        lambda *args, **kw: (calls.append(1), original(*args, **kw))[1])
    for _ in range(5):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 200
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
    assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 200


def test_twenty_failures_across_sessions_lock_everyone(rig):
    server, seed, _cookie = rig
    for index in range(5):
        cookie = fx.admin_cookie(server.state_dir, "extra%d@example.test" % index)
        for _ in range(4):
            assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 200
    fresh = fx.admin_cookie(server.state_dir, "fresh@example.test")
    status, _headers, body = _pair(server, fresh, fx.FAKE_CODE, seed.owner_id)
    assert status == 429 and "Too many attempts" in body
    rows = fx.audit_rows(server.state_dir, "pairing.claim")
    assert len([row for row in rows if "throttled" in row["detail"]]) == 1


def test_a_success_resets_the_session_counter_but_not_the_global_one(
        rig, monkeypatch):
    server, seed, cookie = rig
    for _ in range(3):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 200
    assert _pair(server, cookie, fx.FAKE_CODE, seed.owner_id)[0] == 303
    for _ in range(5):
        assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 200
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
        assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 200
    assert _pair(server, other, fx.OTHER_FAKE_CODE, seed.owner_id)[0] == 303
    assert _pair(server, other, WRONG_CODE, seed.owner_id)[0] == 200
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
    statuses = sorted(result[0] for result in results)
    assert statuses == [200, 303]
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 1
    loser = next(result for result in results if result[0] == 200)
    assert "Code not recognised" in loser[2]


def test_missing_fields_are_400_and_are_not_counted(rig, monkeypatch):
    server, seed, cookie = rig
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE", throttle.LockoutThrottle(1, 300))
    status, _headers, body = _pair(server, cookie, "", seed.owner_id)
    assert status == 400 and "Enter the pairing code." in body
    status, _headers, body = fx.post(server, cookie, "/fleet/pair", {"code": WRONG_CODE})
    assert status == 400 and "Choose an owner." in body
    status, _headers, body = fx.post(server, cookie, "/fleet/pair", {
        "code": WRONG_CODE, "owner_user_id": "abc"})
    assert status == 400
    assert _pair(server, cookie, WRONG_CODE, seed.owner_id)[0] == 200
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


def test_both_post_routes_demand_the_csrf_token_and_an_admin(rig):
    server, seed, cookie = rig
    for path in ("/fleet/pair", "/fleet/register"):
        found = routes.match("POST", path, "")
        assert found is not None and found[0].csrf is True
        assert found[0].access == routes.ADMIN_ONLY
    form = ("code=%s&owner_user_id=%d" % (fx.FAKE_CODE, seed.owner_id)).encode()
    status, _headers, _body = http_request(
        server.url("/fleet/pair"), "POST", data=form, cookie=cookie)
    assert status == 403
    assert _count(server.state_dir, "devices", "mac = '%s'" % fx.MAC_PENDING) == 0
    assert not fx.audit_rows(server.state_dir, "pairing.claim")
    user = fx.user_cookie(server.state_dir)
    unknown = fx.get(server, user, "/no-such-page-anywhere")
    for path, fields in (
            ("/fleet/pair", {"code": fx.FAKE_CODE, "owner_user_id": "1"}),
            ("/fleet/register", {"mac": fx.MAC_NEW})):
        status, _headers, body = fx.post(server, user, path, fields)
        assert status == 404 and body == unknown[2]
        status, headers, _body = http_request(
            server.url(path), "POST", data=b"x=1")
        assert status == 303 and "/login" in headers["Location"]
