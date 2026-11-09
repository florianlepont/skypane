"""Rename a frame: the page with one name field and the POST that stores it.

Security invariants:
- Both routes are device-scoped for the frame's owner or an administrator
  (a co-manager cannot rename); the frame id comes from the matched path.
- The name is typed text: trimmed, blanks collapsed, 1 to 40 printable
  characters, otherwise refused with the field's error and nothing stored.
- The change and its audit row share one transaction. Only the display name
  in fleet.db changes (an existing column); the frame's image, interval and
  protocol never read it.
"""
import sqlite3

from companion import audit, console_flash, i18n, layout, prefs, route_types, ui_base
from companion.pages import frame_name_page as page
from server import fleet_db

_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)
ACCOUNT_PATH = "/account"
FLEET_PATH = "/fleet"

console_flash.register_flash(
    page.FLASH_FRAME_RENAMED, "success", page.FLASH_FRAME_RENAMED_TEXT)


def _is_admin(h):
    principal = h._safe_principal()
    return principal is not None and principal.role == "admin"


def _back_href(h, device):
    if _is_admin(h):
        return "%s?frame=%s&tab=settings" % (FLEET_PATH, device.id)
    return ACCOUNT_PATH


def _respond(h, device, status, name, error=""):
    body = page.render(
        name, page.device_route(device.id), _back_href(h, device), error)
    html = layout.page_shell(
        title=i18n.t(page.TITLE), active=layout.nav_slug(ACCOUNT_PATH), body=body,
        ui_theme=h._resolved_ui_theme(), health_alert=None,
        scripts=(ui_base.DIRTY_STATE_SCRIPT_SRC, ui_base.SUBMIT_GUARD_SCRIPT_SRC))
    return h.send_html(status, html)


def handle_get(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    unnamed = m.device.name == m.device.id
    return _respond(h, m.device, 200, "" if unnamed else m.device.name or "")


def _store(h, device, name):
    """Store `name` and audit it in one transaction; True when stored."""
    conn = fleet_db.connect(h.args.state_dir)
    try:
        with fleet_db.transaction(conn):
            previous = fleet_db.rename_device(conn, device.id, name)
            if previous is None:
                return False
            audit.record_in(
                h, conn, fleet_db.ACTION_RENAME, "device", device.id, "ok",
                {"from": previous, "to": name})
    finally:
        conn.close()
    return True


def handle_post(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    device = m.device
    raw = h.read_form().get(page.NAME_FIELD, "")
    name = page.normalise_name(raw)
    if name is None:
        return _respond(
            h, device, 400, " ".join(raw.split())[:page.MAX_NAME_CHARS],
            i18n.t(page.NAME_ERROR))
    try:
        stored = _store(h, device, name)
    except _STORE_ERRORS:
        stored = False
    if not stored:
        return _respond(h, device, 500, name, i18n.t(page.SAVE_FAILED))
    if _is_admin(h):
        return h.redirect(
            "%s?frame=%s&tab=settings" % (FLEET_PATH, device.id),
            set_cookie=console_flash.queue_flash(page.FLASH_FRAME_RENAMED))
    return h.redirect("%s?flash=%s" % (ACCOUNT_PATH, page.FLASH_FRAME_RENAMED))


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(page.RENAME_ROUTE), handle_get,
        route_types.OWNER_ONLY_DEVICE),
    route_types.Route(
        "POST", route_types.Exact(page.RENAME_ROUTE), handle_post,
        route_types.OWNER_ONLY_DEVICE, csrf=True),
)
