"""Real-browser flows of the two removal dialogs: an administrator deleting a
user from the Users "..." menu, and an owner removing their frame from the
Manage access dialog. Each is checked at 360 and 1280px, in both languages and
themes where the geometry could differ: an opaque dialog, a reachable
confirm button, 44px targets, the outcome in the database and the toast."""
import pytest

import fleet_console_support as fx
from co_manager_browser_support import Rig, _open
from companion import auth
from companion.test_browser_ux_helpers import (
    _SETTLE_PROBE, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme)
from server import fleet_db

pytestmark = pytest.mark.browser

VIEWPORTS = ((VIEWPORT_MIN_SUPPORTED, "360"), (VIEWPORT_DESKTOP, "1280"))
_OWNS_CENTRE = (
    "s => { const e = document.querySelector(s); if (!e) return false;"
    " const r = e.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === e || e.contains(hit)); }")
_SURFACE = """sel => { const d = document.querySelector(sel); const s = getComputedStyle(d);
  const m = /rgba?\\(([^)]+)\\)/.exec(s.backgroundColor);
  const alpha = m ? (m[1].split(',').length > 3 ? parseFloat(m[1].split(',')[3]) : 1) : 0;
  return {alpha: alpha, filter: s.backdropFilter || s.webkitBackdropFilter || 'none'}; }"""
_REACHABLE = """sel => { const d = document.querySelector(sel);
  const box = d.getBoundingClientRect();
  const out = [];
  d.querySelectorAll('.modal__actions button, .modal__actions a, .modal__close').forEach(el => {
    el.scrollIntoView({block: 'nearest'});
    const r = el.getBoundingClientRect();
    if (r.height < 43.5 || r.width < 43.5) out.push('small ' + el.className);
    if (r.top < box.top - 1 || r.bottom > Math.min(box.bottom, innerHeight) + 1) {
      out.push('unreachable ' + el.className);
    }
    if (r.left < -0.5 || r.right > innerWidth + 0.5) out.push('sideways ' + el.className);
  });
  return out; }"""


def _sql(server, sql, args=()):
    conn = fleet_db.connect(server.state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _wait_rows(page, server, sql, args, expected):
    for _ in range(100):
        if _sql(server, sql, args) == expected:
            return
        page.wait_for_timeout(50)
    raise AssertionError("%s never returned %r" % (sql, expected))


# --- Delete user (Users page) -------------------------------------------------


def _users_page(new_context, server, viewport, lang, theme):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport, color_scheme=theme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, theme)
    page.wait_for_function("() => document.readyState === 'complete'")
    page.wait_for_function(_OWNS_CENTRE, arg="a.page-header__action", timeout=10000)
    return context, page, seed


def _open_delete_dialog(page, user_id, item_text):
    row = page.locator("#user-%d" % user_id)
    row.locator("summary").click()
    item = row.locator("a.row-menu__item", has_text=item_text)
    item.wait_for(state="visible")
    assert item.bounding_box()["height"] >= 43.5
    item.click()
    dialog = "#dlg-delete-user-%d" % user_id
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open"
        " && d.classList.contains('is-modal'); }", arg=dialog, timeout=10000)
    page.evaluate(_SETTLE_PROBE, dialog + " .modal__title")
    return dialog


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_deleting_a_user_from_the_menu_confirms_then_removes_them(
        new_context, app_server_in_process, viewport, name, theme):
    server = app_server_in_process
    context, page, seed = _users_page(new_context, server, viewport, "en", theme)
    try:
        dialog = _open_delete_dialog(page, seed.user_id, "Delete user")
        assert page.locator(dialog + " .modal__title").inner_text() == "Delete this user?"
        text = page.locator(dialog).inner_text()
        assert fx.USER_EMAIL in text and "audit log keeps their address" in text
        assert "reassign or retire the frame first" in text
        surface = page.evaluate(_SURFACE, dialog)
        assert surface["alpha"] == 1 and surface["filter"] == "none", surface
        assert page.evaluate(_REACHABLE, dialog) == []
        page.locator(dialog + " button[type=submit]").click()
        page.wait_for_url("**/users")
        _wait_rows(page, server, "SELECT COUNT(*) FROM users WHERE id = ?",
                   (seed.user_id,), [(0,)])
        toast = page.locator('[role="status"]').first
        toast.wait_for(state="visible")
        assert "User deleted" in toast.inner_text() and fx.USER_EMAIL in toast.inner_text()
        assert page.locator("#user-%d" % seed.user_id).count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_keeping_the_user_closes_the_dialog_and_changes_nothing(
        new_context, app_server_in_process, viewport, name):
    server = app_server_in_process
    context, page, seed = _users_page(new_context, server, viewport, "en", "light")
    try:
        dialog = _open_delete_dialog(page, seed.user_id, "Delete user")
        page.locator(dialog + " a.modal__dismiss").click()
        page.wait_for_function("s => !document.querySelector(s).open", arg=dialog)
        assert _sql(server, "SELECT COUNT(*) FROM users WHERE id = ?", (seed.user_id,)) == [(1,)]
    finally:
        context.close()


@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_a_user_who_owns_a_frame_is_refused_with_the_frame_name(
        new_context, app_server_in_process, viewport, name):
    server = app_server_in_process
    context, page, seed = _users_page(new_context, server, viewport, "en", "light")
    try:
        dialog = _open_delete_dialog(page, seed.owner_id, "Delete user")
        page.locator(dialog + " button[type=submit]").click()
        page.wait_for_url("**/users")
        toast = page.locator('[role="alert"]').first
        toast.wait_for(state="visible")
        assert "Kitchen" in toast.inner_text()
        assert "Reassign or retire the frame first" in toast.inner_text()
        assert _sql(server, "SELECT COUNT(*) FROM users WHERE id = ?", (seed.owner_id,)) == [(1,)]
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_the_delete_dialog_is_in_french(new_context, app_server_in_process, viewport, name, theme):
    server = app_server_in_process
    context, page, seed = _users_page(new_context, server, viewport, "fr", theme)
    try:
        dialog = _open_delete_dialog(page, seed.user_id, "Supprimer l’utilisateur")
        assert page.locator(dialog + " .modal__title").inner_text() == "Supprimer cet utilisateur\u00a0?"
        assert page.locator(dialog + " a.modal__dismiss").inner_text() == "Garder cet utilisateur"
        assert page.evaluate(_REACHABLE, dialog) == []
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    finally:
        context.close()


# --- Remove this frame (Manage access) ---------------------------------------


class RemoveRig(Rig):
    def __init__(self, server):
        super().__init__(server)
        slug = self.seed.owned_id.lower().replace("_", "-")
        self.access = "#dlg-access-" + slug
        self.confirm = "#dlg-remove-frame-" + slug
        self.opener = 'a[href="%s"]' % self.access
        self.trigger = 'a[href="%s"]' % self.confirm


@pytest.fixture
def rrig(app_server_in_process):
    return RemoveRig(app_server_in_process)


def _open_access(new_context, rig, viewport, lang, theme):
    context, page = _open(
        new_context, rig, "owner", path="/account", lang=lang, theme=theme,
        viewport=viewport)
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_function(_OWNS_CENTRE, arg=rig.opener, timeout=10000)
    page.locator(rig.opener).click()
    page.locator(rig.access + "[open]").wait_for(state="visible")
    page.evaluate(_SETTLE_PROBE, rig.access + " .modal__title")
    return context, page


def _open_confirm(page, rig):
    trigger = page.locator(rig.access + " " + rig.trigger)
    trigger.scroll_into_view_if_needed()
    assert trigger.bounding_box()["height"] >= 43.5
    trigger.click()
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open"
        " && d.classList.contains('is-modal'); }", arg=rig.confirm, timeout=10000)
    page.evaluate(_SETTLE_PROBE, rig.confirm + " .modal__title")


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_an_owner_removes_their_frame_from_the_access_dialog(
        new_context, rrig, viewport, name, theme):
    context, page = _open_access(new_context, rrig, viewport, "en", theme)
    try:
        trigger = rrig.access + " " + rrig.trigger
        assert page.locator(trigger).inner_text() == "Remove this frame"
        colour = page.locator(trigger).evaluate(
            "a => getComputedStyle(a).color")
        assert colour != page.locator(rrig.access + " .modal__title").evaluate(
            "t => getComputedStyle(t).color")
        _open_confirm(page, rrig)
        assert page.locator(rrig.confirm + " .modal__title").inner_text() == "Remove this frame?"
        text = page.locator(rrig.confirm).inner_text()
        assert "disappears from your account" in text and "co-managers lose access" in text
        assert "assign it to someone again" in text
        surface = page.evaluate(_SURFACE, rrig.confirm)
        assert surface["alpha"] == 1 and surface["filter"] == "none", surface
        assert page.evaluate(_REACHABLE, rrig.confirm) == []
        page.locator(rrig.confirm + " button[type=submit]").click()
        page.wait_for_url("**/account?flash=frame_removed")
        _wait_rows(page, rrig.server, "SELECT COUNT(*) FROM devices WHERE id = ?",
                   (rrig.seed.owned_id,), [(0,)])
        toast = page.locator('[role="status"]').first
        toast.wait_for(state="visible")
        assert "Frame removed" in toast.inner_text()
        assert page.locator(rrig.opener).count() == 0
        assert _sql(rrig.server, "SELECT COUNT(*) FROM pending_devices WHERE "
                    "previous_device_id = ? AND status = 'retired'",
                    (rrig.seed.owned_id,)) == [(1,)]
    finally:
        context.close()


@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_keeping_the_frame_closes_only_the_confirmation_and_focus_returns(
        new_context, rrig, viewport, name):
    context, page = _open_access(new_context, rrig, viewport, "en", "light")
    try:
        _open_confirm(page, rrig)
        page.locator(rrig.confirm + " a.modal__dismiss").click()
        page.wait_for_function("s => !document.querySelector(s).open", arg=rrig.confirm)
        page.wait_for_function(
            "s => document.querySelector(s).open", arg=rrig.access)
        page.wait_for_function(
            "(s) => document.activeElement === document.querySelector(s)",
            arg=rrig.access + " " + rrig.trigger)
        assert _sql(rrig.server, "SELECT COUNT(*) FROM devices WHERE id = ?",
                    (rrig.seed.owned_id,)) == [(1,)]
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("viewport,name", VIEWPORTS)
def test_the_remove_frame_dialogs_are_in_french(new_context, rrig, viewport, name, theme):
    context, page = _open_access(new_context, rrig, viewport, "fr", theme)
    try:
        assert page.locator(rrig.access + " " + rrig.trigger).inner_text() == "Retirer ce cadre"
        _open_confirm(page, rrig)
        assert page.locator(rrig.confirm + " .modal__title").inner_text() == "Retirer ce cadre\u00a0?"
        assert page.locator(rrig.confirm + " a.modal__dismiss").inner_text() == "Garder ce cadre"
        assert page.evaluate(_REACHABLE, rrig.confirm) == []
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    finally:
        context.close()


def test_a_co_manager_is_not_offered_the_removal(new_context, rrig):
    context, page = _open(
        new_context, rrig, "co", path="/account", viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page.wait_for_function("document.readyState === 'complete'")
        assert page.locator("a[href^='#dlg-remove-frame']").count() == 0
        assert page.locator("a[href^='#dlg-leave']").count() == 1
    finally:
        context.close()
