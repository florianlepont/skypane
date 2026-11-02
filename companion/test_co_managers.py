"""Co-management flash toasts and audit labels, and the add, remove and leave
routes over real HTTP: audit rows, the single refusal, CSRF and role gates."""
import html
import json
import re
import sqlite3
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import audit, i18n_fr, prefs
from companion.pages import co_managers_card as cards
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import fleet_db

CO_EMAIL = "co-manager@example.test"
STRANGER_EMAIL = "stranger@example.test"


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def base(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    yield server, seed
    server.stop()


def _get(server, cookie, path, language=None):
    extra = {"Accept-Language": language} if language else None
    status, headers, body = http_request(
        server.url(path), cookie=cookie, extra_headers=extra)
    return status, headers, html.unescape(body.decode("utf-8", "replace"))


# --- flash toasts ----------------------------------------------------------

# key -> (English text, toast tone, ARIA role)
FLASHES = {
    cards.FLASH_ADDED: (
        "Co-manager added — they can now manage this frame.", "success", "status"),
    cards.FLASH_REMOVED: (
        "Co-manager removed — they no longer have access to this frame.",
        "success", "status"),
    cards.FLASH_LEFT: (
        "You left the frame — it no longer appears in your account.",
        "success", "status"),
    cards.FLASH_ADD_REFUSED: (
        "That address can't be added — check the spelling, or ask an "
        "administrator to invite this person first.", "error", "alert"),
    cards.FLASH_FAILED: (
        "Couldn't update co-managers — try again in a moment.", "error", "alert"),
    cards.FLASH_LEAVE_NOOP: (
        "Nothing changed — only co-managers can leave a frame.", "info", "status"),
}


def _toast_parts(text):
    """The toast's title and detail; the detail line starts with a capital."""
    title, _sep, detail = text.partition(" — ")
    return title, detail[:1].upper() + detail[1:]


@pytest.mark.parametrize("key", sorted(FLASHES))
def test_each_flash_renders_its_text_tone_and_role(base, key):
    server, seed = base
    cookie = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)
    _s, _h, body = _get(server, cookie, "/devices/%s/?flash=%s" % (seed.owned_id, key))
    text, tone, role = FLASHES[key]
    title, detail = _toast_parts(text)
    toast = re.search(r'<div class="toast toast--(\w+)"[^>]*role="(\w+)"[^>]*>', body)
    assert toast is not None
    assert (toast.group(1), toast.group(2)) == (tone, role)
    assert title in body
    if detail:
        assert detail in body


@pytest.mark.parametrize("key", sorted(FLASHES))
def test_each_flash_renders_in_french(base, key):
    server, seed = base
    cookie = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)
    _s, _h, body = _get(
        server, cookie, "/devices/%s/?flash=%s" % (seed.owned_id, key), language="fr")
    french = i18n_fr.BY_ID[{
        cards.FLASH_ADDED: "co_managers.flash_added",
        cards.FLASH_REMOVED: "co_managers.flash_removed",
        cards.FLASH_LEFT: "co_managers.flash_left",
        cards.FLASH_ADD_REFUSED: "co_managers.flash_add_refused",
        cards.FLASH_FAILED: "co_managers.flash_failed",
        cards.FLASH_LEAVE_NOOP: "co_managers.flash_leave_noop",
    }[key]]
    title, detail = _toast_parts(french)
    assert title in body
    if detail:
        assert detail in body


def test_an_unknown_flash_key_renders_no_toast(base):
    server, seed = base
    cookie = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)
    _s, _h, body = _get(
        server, cookie, "/devices/%s/?flash=co_manager_nonsense" % seed.owned_id)
    assert "toast-region--flash" not in body


def test_no_flash_text_carries_a_placeholder():
    for text, _tone, _role in FLASHES.values():
        assert "{" not in text and "%s" not in text


# --- audit labels ----------------------------------------------------------


@pytest.mark.parametrize("action,english,french", [
    (fleet_db.ACTION_CO_MANAGER_ADD, "Co-manager added", "Co-gestionnaire ajouté"),
    (fleet_db.ACTION_CO_MANAGER_REMOVE, "Co-manager removed", "Co-gestionnaire retiré"),
])
def test_the_audit_page_labels_the_co_manager_actions(base, action, english, french):
    server, seed = base
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            fleet_db.audit_append(
                conn, fx.ACTOR, action, "device", seed.owned_id, "ok",
                {"co_manager_user_id": 1, "via": "owner"})
    finally:
        conn.close()
    cookie = fx.admin_cookie(server.state_dir)
    _s, _h, body = _get(server, cookie, "/audit")
    assert english in body
    assert "Other action" not in body
    _s, _h, body = _get(server, cookie, "/audit", language="fr")
    assert french in body
    assert "Autre action" not in body


# --- routes ----------------------------------------------------------------

INVITEE = "invitee@example.test"
INVITEE2 = "invitee2@example.test"
DISABLED = "disabled@example.test"
UNKNOWN = "nobody-here@example.test"
CO2_EMAIL = "co-manager-two@example.test"


class Rig:
    def __init__(self, server, seed):
        self.server = server
        self.seed = seed
        self.device = seed.owned_id
        state_dir = server.state_dir

        def setup(conn):
            self.invitee_id = fleet_db.add_user(conn, INVITEE, "user")
            self.invitee2_id = fleet_db.add_user(conn, INVITEE2, "user")
            disabled_id = fleet_db.add_user(conn, DISABLED, "user")
            fleet_db.set_user_disabled(conn, DISABLED, True)
            self.disabled_id = disabled_id
            self.co_id = fleet_db.add_user(conn, CO_EMAIL, "user")
            self.co2_id = fleet_db.add_user(conn, CO2_EMAIL, "user")
            fleet_db.add_co_manager(conn, self.device, self.co_id, None)
            fleet_db.add_co_manager(conn, self.device, self.co2_id, None)
        self.db(setup)
        self.cookies = {
            "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
            "co": fx.user_cookie(state_dir, email=CO_EMAIL),
            "co2": fx.user_cookie(state_dir, email=CO2_EMAIL),
            "stranger": fx.user_cookie(state_dir, email=STRANGER_EMAIL),
            "admin": fx.admin_cookie(state_dir),
            "anonymous": None,
        }

    def db(self, fn):
        conn = fleet_db.connect(self.server.state_dir)
        try:
            return fn(conn)
        finally:
            conn.close()

    def members(self):
        return self.db(lambda c: sorted(
            int(r["user_id"]) for r in fleet_db.list_co_managers(c, self.device)))

    def prefix(self):
        return "/devices/%s" % self.device

    def post(self, who, route, form, token=True, prefixed=True, extra=None):
        cookie = self.cookies[who]
        headers = {"Origin": self.server.base_url()}
        headers.update(extra or {})
        data = with_csrf(cookie, form) if token else urllib.parse.urlencode(form).encode()
        path = (self.prefix() if prefixed else "") + route
        status, response, body = http_request(
            self.server.url(path), method="POST", cookie=cookie, data=data,
            extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def audit(self, action=None):
        """The co-management audit rows (all of them, or one action's)."""
        return [
            row for row in fx.audit_rows(self.server.state_dir, action)
            if row["action"].startswith("device.co_manager")]


@pytest.fixture
def rig(base):
    server, seed = base
    return Rig(server, seed)


def _home(rig, flash):
    return "%s/?flash=%s" % (rig.prefix(), flash)


def _detail(row):
    return json.loads(row["detail"])


def _frame_status(rig, who):
    status, _h, _b = http_request(
        rig.server.url(rig.prefix() + "/display"), cookie=rig.cookies[who])
    return status


# add


def test_the_owner_adds_a_co_manager_by_email(rig):
    status, headers, _b = rig.post("owner", cards.ADD_ROUTE, {"email": INVITEE})
    assert status == 303
    assert headers["Location"] == _home(rig, cards.FLASH_ADDED)
    assert rig.invitee_id in rig.members()
    rows = rig.audit(fleet_db.ACTION_CO_MANAGER_ADD)
    assert len(rows) == 1
    assert (rows[0]["outcome"], rows[0]["target_id"]) == ("ok", rig.device)
    assert rows[0]["actor_user_id"] == rig.seed.owner_id
    assert _detail(rows[0]) == {"co_manager_user_id": rig.invitee_id, "via": "owner"}
    cookie = fx.user_cookie(rig.server.state_dir, email=INVITEE)
    status, _h, _b = http_request(rig.server.url(rig.prefix() + "/display"), cookie=cookie)
    assert status == 200


def test_an_address_with_other_case_and_spaces_is_normalised(rig):
    status, headers, _b = rig.post(
        "owner", cards.ADD_ROUTE, {"email": "  Invitee@EXAMPLE.test "})
    assert headers["Location"] == _home(rig, cards.FLASH_ADDED)
    assert rig.invitee_id in rig.members()


def test_an_admin_adds_by_the_same_field_including_a_new_or_admin_user(rig):
    for email, user_id in ((INVITEE, rig.invitee_id), (fx.SECOND_ADMIN_EMAIL, rig.seed.admin2_id)):
        status, headers, _b = rig.post("admin", cards.ADD_ROUTE, {"email": email})
        assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_ADDED))
        assert user_id in rig.members()
    rows = rig.audit(fleet_db.ACTION_CO_MANAGER_ADD)
    assert [_detail(r)["via"] for r in rows] == ["admin", "admin"]


def _refusal_inputs(rig):
    return {
        "unknown": UNKNOWN,
        "disabled": DISABLED,
        "owner": fx.OWNER_EMAIL,
        "owner-shouted": "  OWNER@Example.TEST ",
        "duplicate": CO_EMAIL,
        "malformed": "not an address",
        "empty": "",
        "too-long": "a" * 300 + "@example.test",
        "control-character": "invitee@exam\x07ple.test",
    }


def test_every_add_refusal_is_identical_and_never_echoes_the_address(rig):
    outcomes = {}
    for name, email in _refusal_inputs(rig).items():
        before = rig.members()
        status, headers, body = rig.post("owner", cards.ADD_ROUTE, {"email": email})
        outcomes[name] = (status, headers["Location"], headers.get("Set-Cookie"), body)
        assert rig.members() == before
        if email.strip():
            assert email.strip().split("@")[0] not in "".join(
                [headers["Location"], body, str(headers)])
    assert len(set(outcomes.values())) == 1
    status, location, _cookie, _body = next(iter(outcomes.values()))
    assert (status, location) == (303, _home(rig, cards.FLASH_ADD_REFUSED))
    rows = rig.audit(fleet_db.ACTION_CO_MANAGER_ADD)
    assert len(rows) == len(outcomes)
    assert {r["outcome"] for r in rows} == {"denied"}
    dump = fx.dump_database_text(rig.server.state_dir)
    for email in (UNKNOWN, "not an address", "invitee@exam"):
        assert email not in "".join(r["detail"] or "" for r in rows)
    assert UNKNOWN not in dump
    reasons = {_detail(r)["reason"] for r in rows}
    assert reasons == {"malformed", "unknown", "ineligible", "duplicate"}


def test_a_candidate_disabled_after_the_page_rendered_gets_the_same_refusal(rig):
    rig.db(lambda c: fleet_db.set_user_disabled(c, INVITEE, True))
    status, headers, _b = rig.post("owner", cards.ADD_ROUTE, {"email": INVITEE})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_ADD_REFUSED))
    assert rig.invitee_id not in rig.members()


def test_a_candidate_added_meanwhile_gets_the_same_refusal(rig):
    rig.db(lambda c: fleet_db.add_co_manager(c, rig.device, rig.invitee_id, None))
    status, headers, _b = rig.post("owner", cards.ADD_ROUTE, {"email": INVITEE})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_ADD_REFUSED))
    assert len(rig.audit(fleet_db.ACTION_CO_MANAGER_ADD)) == 1


# remove


@pytest.mark.parametrize("who,via", [("owner", "owner"), ("admin", "admin")])
def test_the_owner_and_an_admin_remove_a_co_manager(rig, who, via):
    status, headers, _b = rig.post(who, cards.REMOVE_ROUTE, {"user_id": str(rig.co_id)})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_REMOVED))
    assert rig.members() == [rig.co2_id]
    rows = rig.audit(fleet_db.ACTION_CO_MANAGER_REMOVE)
    assert len(rows) == 1 and rows[0]["outcome"] == "ok"
    assert _detail(rows[0]) == {"co_manager_user_id": rig.co_id, "via": via}
    assert _frame_status(rig, "co") == 404


def test_removal_inputs_that_name_no_co_manager_change_nothing(rig):
    owner_row = rig.db(lambda c: tuple(fleet_db.get_device(c, rig.device)))
    bad = (str(rig.invitee_id), "abc", "-1", "1 or 1=1", "", str(rig.seed.owner_id),
           "1" * 40, "%d\x00" % rig.co_id)
    for value in bad:
        status, headers, _b = rig.post("owner", cards.REMOVE_ROUTE, {"user_id": value})
        assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_FAILED))
    assert rig.members() == sorted([rig.co_id, rig.co2_id])
    assert rig.db(lambda c: tuple(fleet_db.get_device(c, rig.device))) == owner_row
    assert rig.audit(fleet_db.ACTION_CO_MANAGER_REMOVE) == []


# who may manage


@pytest.mark.parametrize("route,form", [
    (cards.ADD_ROUTE, {"email": INVITEE}),
    (cards.REMOVE_ROUTE, {"user_id": "0"}),
])
def test_a_co_manager_or_stranger_cannot_add_or_remove(rig, route, form):
    form = dict(form, **({"user_id": str(rig.co2_id)} if "user_id" in form else {}))
    unknown_status, _h, unknown_body = rig.post(
        "co", "/no-such-page-anywhere", {}, prefixed=False)
    for who in ("co", "stranger"):
        status, _h, body = rig.post(who, route, form)
        assert (status, body) == (unknown_status, unknown_body) == (404, unknown_body)
    assert rig.members() == sorted([rig.co_id, rig.co2_id])
    assert rig.audit() == []


def test_an_anonymous_caller_is_sent_to_login(rig):
    for route in (cards.ADD_ROUTE, cards.REMOVE_ROUTE, cards.LEAVE_ROUTE):
        status, headers, _b = rig.post("anonymous", route, {"email": INVITEE})
        assert status in (302, 303) and "/login" in headers["Location"]
    assert rig.members() == sorted([rig.co_id, rig.co2_id])


def test_the_unprefixed_add_is_admin_only(rig):
    for who in ("owner", "co"):
        status, _h, _b = rig.post(who, cards.ADD_ROUTE, {"email": INVITEE}, prefixed=False)
        assert status == 404
    status, headers, _b = rig.post(
        "admin", cards.ADD_ROUTE, {"email": INVITEE}, prefixed=False)
    assert status == 303 and headers["Location"] == "/?flash=%s" % cards.FLASH_ADDED
    live = rig.db(lambda c: [r["user_id"] for r in fleet_db.list_co_managers(
        c, rig.seed.live_id)])
    assert live == [rig.invitee_id]


# leave


def test_a_co_manager_leaves_only_their_own_row(rig):
    status, headers, _b = rig.post(
        "co", cards.LEAVE_ROUTE,
        {"user_id": str(rig.co2_id), "email": CO2_EMAIL, "device": rig.seed.live_id})
    assert (status, headers["Location"]) == (303, "/account?flash=%s" % cards.FLASH_LEFT)
    assert rig.members() == [rig.co2_id]
    rows = rig.audit(fleet_db.ACTION_CO_MANAGER_REMOVE)
    assert len(rows) == 1 and rows[0]["actor_user_id"] == rig.co_id
    assert _detail(rows[0]) == {"co_manager_user_id": rig.co_id, "via": "self"}
    assert _frame_status(rig, "co") == 404
    assert _frame_status(rig, "co2") == 200


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_leaving_without_a_membership_changes_nothing(rig, who):
    owner_row = rig.db(lambda c: tuple(fleet_db.get_device(c, rig.device)))
    status, headers, _b = rig.post(who, cards.LEAVE_ROUTE, {"user_id": str(rig.co_id)})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_LEAVE_NOOP))
    assert rig.members() == sorted([rig.co_id, rig.co2_id])
    assert rig.db(lambda c: tuple(fleet_db.get_device(c, rig.device))) == owner_row
    assert rig.audit() == []


# CSRF and origin


@pytest.mark.parametrize("route,who,form", [
    (cards.ADD_ROUTE, "owner", {"email": INVITEE}),
    (cards.REMOVE_ROUTE, "owner", {"user_id": "CO"}),
    (cards.LEAVE_ROUTE, "co", {}),
])
def test_a_missing_or_wrong_csrf_token_is_refused(rig, route, who, form):
    form = {k: str(rig.co_id) if v == "CO" else v for k, v in form.items()}
    status, _h, _b = rig.post(who, route, form, token=False)
    assert status == 403
    status, _h, _b = rig.post(who, route, dict(form, csrf_token="wrong"), token=False)
    assert status == 403
    assert rig.members() == sorted([rig.co_id, rig.co2_id])
    assert rig.audit() == []


def test_a_cross_site_origin_is_refused(rig):
    status, _h, _b = rig.post(
        "owner", cards.ADD_ROUTE, {"email": INVITEE},
        extra={"Origin": "https://evil.example"})
    assert status == 403
    assert rig.invitee_id not in rig.members()


# failure


def test_a_failed_write_rolls_back_the_audit_row_and_flashes_the_failure(rig, monkeypatch):
    def broken(*_args, **_kwargs):
        raise sqlite3.OperationalError("attempt to write a readonly database")
    monkeypatch.setattr(audit, "record_in", broken)
    status, headers, _b = rig.post("owner", cards.ADD_ROUTE, {"email": INVITEE})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_FAILED))
    assert rig.invitee_id not in rig.members()
    status, headers, _b = rig.post("owner", cards.REMOVE_ROUTE, {"user_id": str(rig.co_id)})
    assert (status, headers["Location"]) == (303, _home(rig, cards.FLASH_FAILED))
    assert rig.co_id in rig.members()
    assert {r["outcome"] for r in rig.audit()} <= {"failed"}
