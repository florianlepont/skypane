"""The Airlines editor's artwork-removal and default-type POST handlers.

Both are admin routes on one device, carry the per-session token, write only
under that device's state directory and answer with a redirect back to the
editor. Each successful change is audited with the same standalone row the
other console actions write. The form fields are re-validated here, never
trusted: a key must name artwork the editor can show, a type code must match
the designator pattern.
"""
import os
import sqlite3
from urllib.parse import quote

from companion import audit
from companion.pages import airline_sheet, airlines_page
from server import fleet_db
from server.plane import airline_default_types, illustrations

ACTION_ARTWORK_DELETE = "airline.artwork_delete"
ACTION_DEFAULT_TYPE = "airline.default_type"
ACTION_RESOLVE = "airline.resolve"
TARGET_TYPE = "airline"

FLASH_KEY_ARTWORK_DELETE_FAILED = airline_sheet.FLASH_ARTWORK_DELETE_FAILED
FLASH_KEY_ARTWORK_DELETED = airline_sheet.FLASH_ARTWORK_DELETED
FLASH_KEY_ARTWORK_STALE = airline_sheet.FLASH_ARTWORK_STALE
FLASH_KEY_DEFAULT_TYPE_FAILED = airline_sheet.FLASH_DEFAULT_TYPE_FAILED
FLASH_KEY_DEFAULT_TYPE_SAVED = airline_sheet.FLASH_DEFAULT_TYPE_SAVED

_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)


def record(handler, action, target_id, detail=None):
    """One `ok` audit row for an airline action. A store failure is
    swallowed: the change itself has already been made and flashed."""
    try:
        audit.record_standalone(handler, action, TARGET_TYPE, target_id, "ok", detail)
    except _STORE_ERRORS:
        pass


def _back(handler, flash_key):
    return handler._scoped_redirect(
        "%s?flash=%s" % (airlines_page.MANAGE_ROUTE, quote(flash_key)))


def _known(filename, state_dir):
    # Imported on use: post_actions imports the flash module, which imports
    # the route table that imports this module.
    from companion import post_actions
    return post_actions.illustration_filename_known(filename, state_dir)


def _artwork_key(handler, device):
    """The validated artwork key of the form, or `None`. A key is accepted
    only when its file name is one the editor can hold artwork under."""
    key = handler.read_form().get("key")
    if not isinstance(key, str) or not key:
        return None
    if not _known(key + ".png", device.state_dir):
        return None
    return key


def handle_artwork_delete(handler, match):
    """POST /airlines/artwork/delete: remove the owner's uploaded artwork of
    one key so the type or airline shows its default illustration again.
    Deleting an already-absent upload is success; the vendored picture is
    never touched."""
    device = match.device
    key = _artwork_key(handler, device)
    if key is None:
        return _back(handler, FLASH_KEY_ARTWORK_STALE)
    path = illustrations.override_path_for_key(key, device.state_dir)
    try:
        if path and os.path.isfile(path):
            os.unlink(path)
    except OSError:
        return _back(handler, FLASH_KEY_ARTWORK_DELETE_FAILED)
    record(handler, ACTION_ARTWORK_DELETE, key)
    return _back(handler, FLASH_KEY_ARTWORK_DELETED)


def handle_default_type(handler, match):
    """POST /airlines/default-type: make one aircraft type the airline's
    default, or clear it when `type` is empty."""
    device = match.device
    form = handler.read_form()
    key = form.get("airline_key")
    known = isinstance(key, str) and _known(key + ".png", device.state_dir)
    if not known:
        return _back(handler, FLASH_KEY_ARTWORK_STALE)
    code = form.get("type") or ""
    result = airline_default_types.set_default_type(device.state_dir, key, code)
    if result != airline_default_types.SET_OK:
        return _back(handler, FLASH_KEY_DEFAULT_TYPE_FAILED)
    record(handler, ACTION_DEFAULT_TYPE, key, {"type": code.strip().upper()} if code else None)
    return _back(handler, FLASH_KEY_DEFAULT_TYPE_SAVED)
