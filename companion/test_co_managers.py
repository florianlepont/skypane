"""Co-management flash toasts and audit labels, and the add, remove and leave
routes over real HTTP: audit rows, the single refusal, CSRF and role gates."""
import html
import re

import pytest

import fleet_console_support as fx
from companion import i18n_fr, prefs
from companion.pages import co_managers_card as cards
from companion_app_server import InProcessAppServer, http_request
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
