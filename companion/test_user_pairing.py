# SPDX-License-Identifier: AGPL-3.0-only
"""A signed-in person adds their own frame with the pairing code over real
HTTP: ownership, audit, the identical refusal, the shared throttles, role
and CSRF gating, and the empty state of a person with no frame."""
import re

from companion_markup import parse_html

import pytest

import fleet_console_support as fx
from companion import auth, console_pairing, prefs, throttle
from companion_app_server import http_request
from server import fleet_db, hardware

WRONG_CODE = "KKKK2222"
PATH = "/pair-frame"


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
    return server, seed, fx.user_cookie(server.state_dir)


def _device(state_dir, mac=fx.MAC_PENDING):
    conn = fleet_db.connect(state_dir)
    try:
        return fleet_db.get_device_by_mac(conn, mac)
    finally:
        conn.close()


def _claim(server, cookie, code, **extra):
    return fx.post(server, cookie, PATH, dict({"code": code}, **extra))


def _card(page):
    return re.search(r'<form class="pair-form[ \"].*?</form>', page, re.S).group(0)


def test_a_user_pairs_a_frame_and_becomes_its_owner(rig):
    server, seed, cookie = rig
    status, headers, _body = _claim(server, cookie, "abcd-2345")
    assert status == 303
    device = _device(server.state_dir)
    assert device["owner_user_id"] == seed.user_id
    assert headers["Location"] == "/devices/%s/?flash=frame_paired" % device["id"]
    status, _headers, home = fx.get(server, cookie, headers["Location"])
    assert status == 200 and "Frame added" in home
    # The new frame is called "Unnamed frame" wherever it is named, never by its internal id.
    assert ">%s<" % device["id"] not in home and "Unnamed frame" in home
    ok = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
          if row["outcome"] == "ok"]
    assert len(ok) == 1 and ok[0]["actor_label"] == fx.USER_EMAIL
    assert fx.FAKE_CODE not in fx.dump_database_text(server.state_dir)


def test_a_submitted_owner_is_ignored_and_other_frames_are_unaffected(rig):
    server, seed, cookie = rig
    before = _device(server.state_dir, fx.MAC_OWNED)["owner_user_id"]
    status, _headers, _body = _claim(
        server, cookie, fx.FAKE_CODE, owner_user_id=str(seed.admin_id),
        owner=str(seed.owner_id))
    assert status == 303
    assert _device(server.state_dir)["owner_user_id"] == seed.user_id
    assert _device(server.state_dir, fx.MAC_OWNED)["owner_user_id"] == before
    assert _device(server.state_dir, fx.MAC_LIVE)["owner_user_id"] == seed.admin_id


def test_an_administrator_claim_on_the_page_still_chooses_the_owner(rig):
    server, seed, _cookie = rig
    admin = fx.admin_cookie(server.state_dir)
    status, _headers, _body = fx.post(server, admin, PATH, {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)})
    assert status == 303
    assert _device(server.state_dir)["owner_user_id"] == seed.owner_id


def test_the_claimed_frame_is_reachable_by_its_owner_and_not_by_another_user(rig):
    server, _seed, cookie = rig
    _claim(server, cookie, fx.FAKE_CODE)
    device = _device(server.state_dir)
    other = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    assert fx.get(server, cookie, "/devices/%s/" % device["id"])[0] == 200
    assert fx.get(server, other, "/devices/%s/" % device["id"])[0] == 404


def test_wrong_expired_used_and_malformed_codes_get_one_identical_answer(rig):
    server, seed, cookie = rig
    fx.issue_code(server.state_dir, seed.pending_id, fx.FAKE_CODE)
    conn = fleet_db.connect(server.state_dir)
    try:
        expired = fleet_db.register_pending(
            conn, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY, None)
    finally:
        conn.close()
    fx.issue_code(server.state_dir, expired, fx.OTHER_FAKE_CODE, ttl_s=-60)
    assert _claim(server, cookie, fx.FAKE_CODE)[0] == 303
    answers = set()
    for code in ("kkkk-2222", fx.OTHER_FAKE_CODE.lower(), "no", fx.FAKE_CODE):
        status, headers, body = _claim(server, cookie, code)
        kept = headers.get("Set-Cookie")
        # Post/Redirect/Get: the refusal is a redirect, so a reload never re-sends the code.
        assert status == 303 and headers["Location"] == "/pair-frame?refused=1", (code, status)
        assert not body
        status, headers, page = fx.get(
            server, _with_kept(cookie, kept), headers["Location"])
        assert status == 200 and headers["Cache-Control"] == "no-store"
        card = _card(page)
        assert "Code not recognised" in card
        # Only the kept code differs between the refusals: the answer is the same.
        answers.add(re.sub(r'value="[^"]*"', "", card))
    assert len(answers) == 1
    failed = [row for row in fx.audit_rows(server.state_dir, "pairing.claim")
              if row["outcome"] == "failed"]
    assert len(failed) == 4 and all('"invalid"' in row["detail"] for row in failed)


def _refusal_page(server, cookie, lang=None):
    _status, headers, _body = _claim(server, cookie, WRONG_CODE)
    kept = _with_kept(cookie, headers.get("Set-Cookie"))
    if lang:
        kept += "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    return fx.get(server, kept, headers["Location"])[2]


def test_a_refused_code_is_one_alert_with_the_sentence_and_the_validity_line(rig):
    server, _seed, cookie = rig
    page = _refusal_page(server, cookie)
    alerts = parse_html(_card(page)).find_all(attrs={"role": "alert"})
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.find_all("svg")
    text = alert.text()
    assert text.startswith("Code not recognised. Check the code and try again.")
    assert "Valid for 35 minutes" in text
    assert _card(page).count("Valid for 35 minutes") == 1
    assert 'aria-describedby="%s"' % alert.attrs["id"] in _card(page)
    assert "press its Reset button" not in _card(page)


def test_a_refused_code_reads_in_french(rig):
    server, _seed, cookie = rig
    page = _refusal_page(server, cookie, "fr")
    alert = parse_html(_card(page)).find(attrs={"role": "alert"})
    text = alert.text()
    assert text.startswith("Code non reconnu. Vérifiez le code et réessayez.")
    assert "Valable 35" in text and "minutes." in text


@pytest.mark.parametrize("lang,sentence", [
    (None, "Press its Reset button."),
    ("fr", "Appuyez sur son bouton Reset."),
])
def test_the_plain_form_tells_a_frame_without_a_code_to_press_reset(rig, lang, sentence):
    server, _seed, cookie = rig
    if lang:
        cookie += "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    page = fx.get(server, cookie, PATH)[2]
    card = parse_html(_card(page))
    assert sentence in card.text()
    assert card.find_all(attrs={"role": "alert"}) == []


def _with_kept(cookie, set_cookie):
    """`cookie` plus the cookie a refusal asked the browser to keep."""
    if not set_cookie:
        return cookie
    return "%s; %s" % (cookie, set_cookie.split(";", 1)[0])


def _field_value(page):
    return re.search(r'id="pair-code"[^>]*value="([^"]*)"', _card(page)).group(1)


def test_the_guess_is_stored_nowhere_and_never_in_an_address(rig, capsys):
    server, _seed, cookie = rig
    status, headers, body = _claim(server, cookie, "MMMM3333")
    assert status == 303 and "MMMM3333" not in headers["Location"]
    assert "MMMM3333" not in body
    assert "MMMM3333" not in fx.dump_database_text(server.state_dir)
    fx.get(server, _with_kept(cookie, headers["Set-Cookie"]), headers["Location"])
    out = capsys.readouterr()
    assert "MMMM3333" not in out.out + out.err


def test_a_refused_code_comes_back_in_the_field_once(rig):
    server, _seed, cookie = rig
    _status, headers, _body = _claim(server, cookie, "kkkk 2222")
    kept = headers["Set-Cookie"]
    status, shown, page = fx.get(server, _with_kept(cookie, kept), "/pair-frame?refused=1")
    assert status == 200 and _field_value(page) == "KKKK2222"
    assert "Code not recognised" in page
    cleared = shown["Set-Cookie"]
    assert cleared.startswith("sp_pair_code=;") and "Max-Age=0" in cleared
    # The browser dropped the cookie: the second visit has an empty field.
    status, again, page = fx.get(server, cookie, "/pair-frame?refused=1")
    assert status == 200 and _field_value(page) == "" and "Set-Cookie" not in again
    assert "Code not recognised" not in page


def test_a_refusal_with_an_odd_value_also_shows_its_error_once(rig):
    server, _seed, cookie = rig
    _status, headers, _body = _claim(server, cookie, "A;B=C")
    kept = headers["Set-Cookie"]
    assert kept.split(";")[0].endswith(".") and "A;B" not in kept
    status, _shown, page = fx.get(server, _with_kept(cookie, kept), "/pair-frame?refused=1")
    assert status == 200 and "Code not recognised" in page and _field_value(page) == ""
    status, _again, page = fx.get(server, cookie, "/pair-frame?refused=1")
    assert status == 200 and "Code not recognised" not in page


def test_the_kept_code_cookie_is_short_lived_and_scoped(rig):
    server, _seed, cookie = rig
    _status, headers, _body = _claim(server, cookie, WRONG_CODE)
    attributes = [part.strip() for part in headers["Set-Cookie"].split(";")]
    assert attributes[0].startswith("sp_pair_code=") and WRONG_CODE in attributes[0]
    assert {"HttpOnly", "SameSite=Strict", "Path=/pair-frame", "Max-Age=120"} <= set(attributes)
    # The test server runs without TLS, so the Secure flag follows the app's own setting.
    assert ("Secure" in attributes) == (auth.secure_cookie_flag() != "")
    # Only a refusal keeps a code.
    _status, ok_headers, _b = _claim(server, cookie, fx.FAKE_CODE)
    assert "sp_pair_code=" not in ok_headers.get("Set-Cookie", "")


def test_a_very_long_or_odd_value_is_cut_or_not_kept(rig):
    server, _seed, cookie = rig
    _status, headers, _body = _claim(server, cookie, "A" * 500)
    value = headers["Set-Cookie"].split(";")[0].split("=", 1)[1]
    assert value.endswith("." + "A" * 12) and len(value) == 16 + 1 + 12
    for odd in ("<script>1</script>", "AB\u00e9D2222", "A;B=C"):
        _status, headers, _body = _claim(server, cookie, odd)
        assert headers["Location"] == "/pair-frame?refused=1"
        # Only a marker that a refusal happened, never any of the odd text.
        assert headers["Set-Cookie"].split(";")[0].endswith("."), odd
    forged = "%s; sp_pair_code=%s.%s" % (
        cookie, console_pairing.session_key(_Handler(cookie)), "<b>x</b>")
    status, _h, page = fx.get(server, forged, PATH)
    assert status == 200 and _field_value(page) == "" and "<b>x</b>" not in page


class _Handler:
    """Just enough of a request handler for session_key()."""

    def __init__(self, cookie):
        self._cookie = cookie

    def _raw_session_token(self):
        return self._cookie.split("=", 1)[1]


def test_another_session_never_sees_the_kept_code(rig):
    server, _seed, cookie = rig
    _status, headers, _body = _claim(server, cookie, WRONG_CODE)
    other = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    status, shown, page = fx.get(server, _with_kept(other, headers["Set-Cookie"]), PATH)
    assert status == 200 and _field_value(page) == "" and WRONG_CODE not in page
    assert "Max-Age=0" in shown["Set-Cookie"]
    # Nobody signed in gets no page at all.
    assert fx.get(server, headers["Set-Cookie"].split(";")[0], PATH)[0] in (303, 404)


def test_five_failures_lock_a_user_session_and_no_code_is_evaluated_after(rig):
    server, _seed, cookie = rig
    for _ in range(5):
        assert _claim(server, cookie, WRONG_CODE)[0] == 303
    status, _headers, body = _claim(server, cookie, fx.FAKE_CODE)
    assert status == 429 and "Too many attempts" in body
    assert _device(server.state_dir) is None
    rows = fx.audit_rows(server.state_dir, "pairing.claim")
    assert len([row for row in rows if "throttled" in row["detail"]]) == 1
    other = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    assert _claim(server, other, WRONG_CODE)[0] == 303


def test_the_global_throttle_covers_users_and_administrators_alike(rig):
    server, seed, _cookie = rig
    for index in range(5):
        cookie = fx.user_cookie(server.state_dir, "extra%d@example.test" % index)
        for _ in range(4):
            assert _claim(server, cookie, WRONG_CODE)[0] == 303
    fresh = fx.user_cookie(server.state_dir, "fresh@example.test")
    assert _claim(server, fresh, fx.FAKE_CODE)[0] == 429
    admin = fx.admin_cookie(server.state_dir)
    assert fx.post(server, admin, PATH, {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)})[0] == 429


def test_an_empty_code_is_a_400_and_is_not_counted(rig, monkeypatch):
    server, _seed, cookie = rig
    monkeypatch.setattr(
        console_pairing, "SESSION_THROTTLE", throttle.LockoutThrottle(1, 300))
    status, _headers, body = _claim(server, cookie, "  ")
    assert status == 400 and "Enter the pairing code." in body
    assert _claim(server, cookie, WRONG_CODE)[0] == 303


def test_a_user_cannot_reach_the_administrator_routes(rig):
    server, _seed, cookie = rig
    assert fx.get(server, cookie, "/fleet")[0] == 404
    assert fx.post(server, cookie, "/fleet/register", {
        "mac": fx.MAC_NEW, "secret_sha256": fx.SECRET_HASH,
        "hardware_type": hardware.LEGACY_KEY})[0] == 404
    assert _device(server.state_dir) is None
    assert _device(server.state_dir, fx.MAC_NEW) is None


def test_the_claim_needs_a_session_and_the_csrf_token(rig):
    server, _seed, cookie = rig
    status, headers, _body = http_request(
        server.url(PATH), "POST", data=b"code=" + fx.FAKE_CODE.encode(), cookie=None)
    assert status == 303 and headers["Location"].startswith("/login")
    status, _headers, _body = http_request(
        server.url(PATH), "POST", data=b"code=" + fx.FAKE_CODE.encode(), cookie=cookie)
    assert status == 403
    assert _device(server.state_dir) is None


def test_the_page_is_a_plain_form_without_an_owner_field(rig):
    server, _seed, cookie = rig
    status, headers, page = fx.get(server, cookie, PATH)
    assert status == 200
    form = _card(page)
    assert 'action="/pair-frame"' in form and 'method="post"' in form
    assert 'name="code"' in form and 'name="csrf_token"' in form
    assert "owner" not in form.lower().replace("pair-form", "")
    assert "<script" not in form
    assert "script-src 'self'" in headers["Content-Security-Policy"]


def test_a_user_without_a_frame_sees_the_add_your_frame_prompt(rig):
    server, _seed, cookie = rig
    status, _headers, page = fx.get(server, cookie, "/account")
    assert status == 200
    assert "Your frames will appear here" in page
    assert "The pairing code is shown on your frame&#x27;s screen." in page or (
        "The pairing code is shown on your frame's screen." in page)
    links = re.findall(r'<a class="pair-link pair-link--primary" href="([^"]*)">([^<]*)</a>', page)
    assert links == [("/pair-frame", "Add your frame")]
    status, headers, _body = fx.get(server, cookie, "/")
    assert (status, headers["Location"]) == (303, "/account")


def test_the_prompt_is_in_french(rig):
    server, _seed, cookie = rig
    status, _headers, page = http_request(
        server.url("/account"), cookie=cookie,
        extra_headers={"Accept-Language": "fr"})
    page = page.decode("utf-8")
    assert status == 200 and "Ajouter votre cadre" in page
    assert "Vos cadres apparaîtront ici" in page


def test_a_user_with_a_frame_gets_the_add_a_frame_link(rig):
    server, _seed, _cookie = rig
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    _status, _headers, page = fx.get(server, owner, "/account")
    doc = parse_html(page)
    assert [(a.attrs["href"], a.text()) for a in doc.select("li.account-add-frame a.row__main")] == [
        ("/pair-frame", "Add a frame")]
    assert "pair-link--primary" not in page


# The optional name typed with the code (Step 1 of the page).

def _name_input(page):
    return re.search(r'id="pair-name"[^>]*value="([^"]*)"', _card(page)).group(1)


def _frame_name(state_dir):
    """The paired frame's name; None while the code has not been claimed."""
    device = _device(state_dir)
    return device["name"] if device is not None else None


def test_the_page_has_the_two_steps_and_one_button(rig):
    server, _seed, cookie = rig
    page = fx.get(server, cookie, PATH)[2]
    card = _card(page)
    assert "Step 1: name it" in card and "Step 2: enter its pairing code" in card
    assert card.index("pair-name") < card.index("pair-code")
    assert card.count("<button") == 1
    fr = fx.get(server, cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME, PATH)[2]
    assert "nommez-le" in _card(fr) and "Ajouter le cadre" in _card(fr)


def test_a_valid_code_with_a_name_pairs_the_frame_under_that_name(rig):
    server, _seed, cookie = rig
    status, headers, _body = _claim(server, cookie, fx.FAKE_CODE, frame_name="  Orly   kitchen ")
    assert status == 303 and headers["Location"].endswith("?flash=frame_paired")
    assert _frame_name(server.state_dir) == "Orly kitchen"
    assert "Orly kitchen" in fx.get(server, cookie, headers["Location"])[2]
    assert [r for r in fx.audit_rows(server.state_dir, "device.rename")
            if r["outcome"] == "ok"]


@pytest.mark.parametrize("blank", ["", "   \t "])
def test_a_blank_name_is_not_an_error_and_renames_nothing(rig, blank):
    server, _seed, cookie = rig
    status, _headers, _body = _claim(server, cookie, fx.FAKE_CODE, frame_name=blank)
    assert status == 303
    assert not _frame_name(server.state_dir)
    assert fx.audit_rows(server.state_dir, "device.rename") == []


@pytest.mark.parametrize("bad", ["x" * 41, "bell\x07name"])
def test_an_invalid_name_is_refused_beside_its_field_and_claims_nothing(rig, bad):
    server, _seed, cookie = rig
    status, _headers, body = _claim(server, cookie, fx.FAKE_CODE, frame_name=bad)
    assert status == 400
    assert "Enter a name of 1 to 40 characters." in body
    assert _device(server.state_dir) is None
    assert _name_input(body) == bad[:40]
    # The code was not evaluated, so the pairing stays open for a retry.
    assert _claim(server, cookie, fx.FAKE_CODE)[0] == 303


def test_markup_in_a_name_is_stored_as_text_and_always_escaped(rig):
    server, _seed, cookie = rig
    name = '"><script>x</script>'
    status, headers, _body = _claim(server, cookie, fx.FAKE_CODE, frame_name=name)
    assert status == 303 and _frame_name(server.state_dir) == name
    home = fx.get(server, cookie, headers["Location"])[2]
    assert "<script>x</script>" not in home


def test_a_refused_code_never_stores_or_echoes_the_name_outside_its_input(rig):
    server, _seed, cookie = rig
    status, headers, _body = _claim(server, cookie, WRONG_CODE, frame_name="Secret Name")
    assert status == 303 and headers["Location"] == "/pair-frame?refused=1"
    assert "Secret" not in headers["Location"]
    cookies = headers["Set-Cookie"]
    assert cookies.startswith("sp_pair_code=") and "Secret" not in cookies
    assert "Secret" not in fx.dump_database_text(server.state_dir)
    assert not _frame_name(server.state_dir)
    sent = _with_kept(cookie, cookies)
    page = fx.get(server, sent, headers["Location"])[2]
    assert _name_input(page) == "Secret Name"
    assert "Secret" not in page.replace('value="Secret Name"', "")
    # Once: a reload carries no cookie.
    assert _name_input(fx.get(server, cookie, PATH)[2]) == ""


def test_the_empty_code_answer_keeps_the_typed_name(rig):
    server, _seed, cookie = rig
    status, _headers, body = _claim(server, cookie, "  ", frame_name="Kept <name>")
    assert status == 400 and _name_input(body) == "Kept &lt;name&gt;"
    assert "Kept <name>" not in body
    assert not _frame_name(server.state_dir)


def test_the_lockout_answer_keeps_the_typed_name(rig, monkeypatch):
    server, _seed, cookie = rig
    monkeypatch.setattr(console_pairing, "is_locked", lambda key: True)
    status, _headers, body = _claim(server, cookie, fx.FAKE_CODE, frame_name="Kept name")
    assert status == 429 and _name_input(body) == "Kept name"
    assert _device(server.state_dir) is None


def test_the_owner_gone_answer_keeps_the_typed_name(rig):
    server, seed, _cookie = rig
    admin = fx.admin_cookie(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (seed.owner_id,))
        conn.commit()
    finally:
        conn.close()
    status, _headers, body = fx.post(server, admin, PATH, {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id), "frame_name": "Kept name"})
    assert status == 400 and _name_input(body) == "Kept name"
    assert not _frame_name(server.state_dir)


def test_an_over_long_name_is_cut_where_it_is_echoed(rig):
    server, _seed, cookie = rig
    _status, _headers, body = _claim(server, cookie, " ", frame_name="y" * 90)
    assert _name_input(body) == "y" * 40


@pytest.mark.parametrize("lang,sentence", [
    ("en", "Hangar 7 now belongs to %s."), ("fr", "Hangar 7 appartient maintenant à %s.")])
def test_an_administrator_flash_for_another_owner_names_the_applied_name(rig, lang, sentence):
    server, seed, _cookie = rig
    admin = fx.admin_cookie(server.state_dir) + "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    status, headers, _body = fx.post(server, admin, PATH, {
        "code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id), "frame_name": "Hangar 7"})
    assert status == 303 and headers["Location"] == "/fleet"
    page = fx.get(server, _with_kept(admin, headers["Set-Cookie"]), "/fleet")[2]
    assert sentence % fx.OWNER_EMAIL in page
    assert "Unnamed frame" not in page and "Cadre sans nom" not in page


def test_a_plain_user_cannot_use_the_name_to_reach_another_frame(rig):
    server, _seed, cookie = rig
    before = _device(server.state_dir, fx.MAC_OWNED)["name"]
    _claim(server, cookie, fx.FAKE_CODE, frame_name="Hijack")
    assert _device(server.state_dir, fx.MAC_OWNED)["name"] == before
