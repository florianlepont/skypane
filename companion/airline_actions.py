# SPDX-License-Identifier: AGPL-3.0-only
"""The Airlines editor's artwork-removal, default-type and hand-named-airline
rename POST handlers.

All are admin routes on one device, carry the per-session token, write only
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
from server import atomic_io, fleet_db
from server.plane import (
    airline_default_types, enrich, illustrations, manual_resolutions, name_overrides)

ACTION_ARTWORK_DELETE = "airline.artwork_delete"
ACTION_DEFAULT_TYPE = "airline.default_type"
ACTION_RESOLVE = "airline.resolve"
ACTION_RENAME_MANUAL = "airline.rename_manual"
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
    changed = _fix_defaults_without_livery(device.state_dir)
    record(handler, ACTION_ARTWORK_DELETE, key,
           {"default_type": [list(entry) for entry in changed]} if changed else None)
    return _back(handler, FLASH_KEY_ARTWORK_DELETED)


def _fix_defaults_without_livery(state_dir):
    """After artwork is gone, every airline whose default type has no picture
    left is re-pointed to the first type it still has a picture for (the
    alphabetical order of the type codes), or cleared when it has none: a
    default never names a type with no picture. Returns `[(airline key, old
    type, new type or "")]`. Best effort; a failed write leaves the entry."""
    changed = []
    for airline_key, code in sorted(airline_default_types.load_default_types(state_dir).items()):
        if illustrations.has_type_livery(airline_key, code, state_dir):
            continue
        remaining = sorted(
            c for c in illustrations.type_pictures(airline_key, state_dir)
            if airline_default_types.normalise_code(c))
        target = remaining[0] if remaining else ""
        if airline_default_types.set_default_type(state_dir, airline_key, target) == (
                airline_default_types.SET_OK):
            changed.append((airline_key, code, target))
    return changed


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


def carry_artwork_to_new_name(state_dir, from_name, to_name, suffixes):
    """Best-effort copy of the artwork flights use under `from_name` to the
    key `to_name` resolves to, so renaming does not blank the airline's
    pictures on new flights. `suffixes` are the file-name endings to carry
    (`""` for the airline's own picture, `"-<type slug>"` for a type's).
    Copies, never moves, and only when `to_name` has no artwork at all (it may
    be another airline's name); the old key's files stay, so a way back (and
    every older picture) still finds them. Both renames call this one
    function, with `state_dir` the one place the artwork lives."""
    from_key = illustrations.normalise_airline_key(from_name)
    to_key = illustrations.normalise_airline_key(to_name)
    if not from_key or not to_key or from_key == to_key:
        return
    if any(illustrations.resolved_illustration_path(to_key + suffix, state_dir) for suffix in suffixes):
        return
    for suffix in suffixes:
        source = illustrations.resolved_illustration_path(from_key + suffix, state_dir)
        target = illustrations.override_path_for_key(to_key + suffix, state_dir)
        if source is None or target is None:
            continue
        try:
            with open(source, "rb") as fh:
                data = fh.read()
            os.makedirs(os.path.dirname(target), exist_ok=True)
            atomic_io.atomic_write(target, data)
        except OSError as exc:
            print("airline rename: could not carry artwork %s: %s" % (suffix or "base", exc))


def _carry_default_type(state_dir, from_key, to_key):
    """Copy the old key's default aircraft type to the new key when the new
    key has none; the old entry stays. A full registry is logged and ignored."""
    if not from_key or not to_key or from_key == to_key:
        return
    types = airline_default_types.load_default_types(state_dir)
    code = types.get(from_key)
    if not code or to_key in types:
        return
    result = airline_default_types.set_default_type(state_dir, to_key, code)
    if result != airline_default_types.SET_OK:
        print("airline rename: could not carry the default type: %s" % result)


def _taken_keys(manual, overrides, group):
    """The illustration keys another airline already has: the built-in
    airlines (with and without artwork), every override and the hand-named
    airlines outside `group` (two prefixes of one carrier may share a name)."""
    names = [name for name, _shapes in illustrations.target_variants_by_airline()]
    names += [name for _prefix, name in enrich.names_without_artwork()]
    names += [entry["airline_name"] for entry in overrides.values()]
    names += [entry["airline_name"] for prefix, entry in manual.items() if prefix not in group]
    return {key for key in (illustrations.normalise_airline_key(n) for n in names) if key}


def _manual_rename_group(registry, prefix):
    """Every prefix whose stored name resolves to the same artwork key."""
    key = manual_resolutions.illustration_key_for_name(registry[prefix]["airline_name"])
    return {p for p, entry in registry.items()
            if manual_resolutions.illustration_key_for_name(entry["airline_name"]) == key}


def _manual_rename_flash(result, raw_name):
    if result == manual_resolutions.ADD_OK:
        return airlines_page.FLASH_RENAMED
    if result == manual_resolutions.ADD_REJECTED_NAME_EMPTY:
        return (airlines_page.FLASH_MANUAL_NAME_UNUSABLE if isinstance(raw_name, str) and raw_name.strip()
                else airlines_page.FLASH_MANUAL_NAME_EMPTY)
    return {
        manual_resolutions.ADD_REJECTED_NAME_TOO_LONG: airlines_page.FLASH_MANUAL_NAME_TOO_LONG,
        manual_resolutions.ADD_REJECTED_NAME_RESERVED: airlines_page.FLASH_MANUAL_NAME_RESERVED,
        manual_resolutions.ADD_REJECTED_PREFIX: airlines_page.FLASH_RENAME_STALE,
        manual_resolutions.ADD_REJECTED_FULL: airlines_page.FLASH_RENAME_FULL,
        manual_resolutions.RENAME_NAME_TAKEN: airlines_page.FLASH_RENAME_TAKEN,
    }.get(result, airlines_page.FLASH_RENAME_SAVE_FAILED)


def handle_manual_rename(handler, match):
    """POST /airlines/rename/manual: rename an airline the owner named by
    hand. `prefix` is normalised and re-validated against the fleet registry,
    never trusted: it must be a stored hand-named prefix the built-in tables
    do not already cover. Every prefix sharing the old name is renamed in one
    write; a name another airline already has is refused. The artwork and the
    default aircraft type of the old name are carried to the new one (copied,
    never moved). Flights already stored keep their name."""
    state_dir = match.device.state_dir
    form = handler.read_form()
    raw_name = form.get("airline_name")
    prefix = manual_resolutions.normalise_prefix(form.get("prefix"))
    registry = manual_resolutions.load_manual_resolutions(state_dir)
    if prefix is None or prefix not in registry or not airlines_page.manual_prefix_renamable(prefix):
        return _back(handler, airlines_page.FLASH_RENAME_STALE)
    old_name = registry[prefix]["airline_name"]
    group = _manual_rename_group(registry, prefix)
    taken = _taken_keys(registry, name_overrides.load_name_overrides(state_dir), group)
    result = manual_resolutions.rename_entries(state_dir, group, raw_name, taken)
    if result != manual_resolutions.ADD_OK:
        return _back(handler, _manual_rename_flash(result, raw_name))
    new_name = manual_resolutions.load_manual_resolutions(state_dir)[prefix]["airline_name"]
    _carry_manual_extras(state_dir, old_name, new_name)
    record(handler, ACTION_RENAME_MANUAL, manual_resolutions.illustration_key_for_name(new_name),
           {"from": old_name, "to": new_name})
    return _back(handler, airlines_page.FLASH_RENAMED)


def _carry_manual_extras(state_dir, old_name, new_name):
    # Imported on use, like `_known`: post_actions sits behind the route table.
    from companion import post_actions
    suffixes = [""] + ["-" + slug for slug in post_actions.type_slugs()]
    carry_artwork_to_new_name(state_dir, old_name, new_name, suffixes)
    _carry_default_type(
        state_dir, manual_resolutions.illustration_key_for_name(old_name),
        manual_resolutions.illustration_key_for_name(new_name))
