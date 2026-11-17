"""Rename a frame: the page with one name field and the POST that stores it.

Security invariants:
- Both routes are device-scoped for the frame's owner or an administrator
  (a co-manager cannot rename); the frame id comes from the matched path.
- `return_to` is only ever followed when it passes the sign-in `next`
  check (an allow-listed page of this site); anything else is ignored.
- The name is typed text: trimmed, blanks collapsed, 1 to 40 printable
  characters, otherwise refused with the field's error and nothing stored.
- The change and its audit row share one transaction. Only the display name
  in fleet.db changes (an existing column); the frame's image, interval and
  protocol never read it.
"""
import re
import sqlite3
from urllib.parse import parse_qsl, quote

from companion import (
    access, audit, console_components, console_flash, console_routes, i18n, layout, prefs, route_types,
    ui_base, ui_shell)
from companion.pages import frame_name_page as page
from server import fleet_db

_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)
_FRAME_PREFIX = re.compile(r"\A/devices/(d_[0-9a-f]{8})(?=/|\Z)")
ACCOUNT_PATH = "/account"
FLEET_PATH = "/fleet"

console_flash.register_flash(
    page.FLASH_FRAME_RENAMED, "success", page.FLASH_FRAME_RENAMED_TEXT)


def _is_admin(h):
    principal = h._safe_principal()
    return principal is not None and principal.role == "admin"


def _return_to(h, raw):
    """`raw` when it is a safe page of this site other than this page, else
    None."""
    safe = h._next_route_of(raw) if isinstance(raw, str) and raw else None
    if safe is None:
        return None
    path = safe.partition("?")[0]
    if path.endswith(page.RENAME_ROUTE):
        return None
    if (console_routes.is_console_path(path) or path == console_components.COMPONENTS_PATH) \
            and not _is_admin(h):
        return None
    if not _frame_reachable(h, path):
        return None
    return safe


def _frame_reachable(h, path):
    """False when `path` is a page of a frame the viewer cannot reach, so
    Cancel and Save never land on the unknown-page answer."""
    prefixed = _FRAME_PREFIX.match(path)
    if prefixed is None:
        return True
    return access.authorized_device_id(
        h._safe_principal(), prefixed.group(1), h._owner_lookup,
        h._co_manager_lookup) is not None


def _active_slug(h, return_to):
    """The navigation slug the page is drawn under: the console page the
    person came from when they are an administrator, else the personal
    Account tab, so a normal user never sees console chrome."""
    path = return_to.partition("?")[0] if return_to else ""
    if _is_admin(h) and console_routes.is_console_path(path):
        return layout.nav_slug(path)
    return layout.nav_slug(ACCOUNT_PATH)


def _back_href(h, device, return_to):
    if return_to:
        return return_to
    if _is_admin(h):
        return "%s?frame=%s&tab=settings" % (FLEET_PATH, device.id)
    return ACCOUNT_PATH


def _respond(h, device, status, name, error="", return_to=None):
    body = page.render(
        name, page.device_route(device.id), _back_href(h, device, return_to), error,
        return_to)
    html = layout.page_shell(
        title="%s - %s" % (i18n.t(page.TITLE), ui_shell.device_display_name(device)),
        active=_active_slug(h, return_to), body=body,
        ui_theme=h._resolved_ui_theme(), health_alert=None,
        scripts=(ui_base.DIRTY_STATE_SCRIPT_SRC, ui_base.SUBMIT_GUARD_SCRIPT_SRC))
    return h.send_html(status, html)


def handle_get(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    unnamed = m.device.name == m.device.id
    query = dict(parse_qsl(m.query or "", keep_blank_values=True))
    return_to = _return_to(h, query.get(page.RETURN_FIELD, ""))
    # The name as every other page shows it: the first frame's default name
    # reads in the viewer's language until someone gives it another.
    return _respond(
        h, m.device, 200, "" if unnamed else ui_shell.device_display_name(m.device),
        return_to=return_to)


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


def _redirect_back(h, return_to):
    """Send the person back to the page they came from, as a 303 so the form
    result is not a history entry. Administrators get the console toast, the
    others the `flash` query the personal pages read."""
    if _is_admin(h) and console_routes.is_console_path(return_to.partition("?")[0]):
        return h.redirect(
            return_to, set_cookie=console_flash.queue_flash(page.FLASH_FRAME_RENAMED))
    joiner = "&" if "?" in return_to else "?"
    return h.redirect(
        "%s%sflash=%s" % (return_to, joiner, quote(page.FLASH_FRAME_RENAMED)))


def handle_post(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    device = m.device
    form = h.read_form()
    raw = form.get(page.NAME_FIELD, "")
    return_to = _return_to(h, form.get(page.RETURN_FIELD, ""))
    name = page.normalise_name(raw)
    if name is None:
        return _respond(
            h, device, 400, " ".join(raw.split())[:page.MAX_NAME_CHARS],
            i18n.t(page.NAME_ERROR), return_to)
    try:
        stored = _store(h, device, name)
    except _STORE_ERRORS:
        stored = False
    if not stored:
        return _respond(h, device, 500, name, i18n.t(page.SAVE_FAILED), return_to)
    if return_to:
        return _redirect_back(h, return_to)
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
