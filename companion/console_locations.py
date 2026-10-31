"""Console routes for the Locations page: list, add, edit and delete.

Both roles use the page. Security invariants:
- Every route needs a signed-in user and every POST carries a CSRF token.
- Ownership is a row-level check made on the server for every action: a user
  acts only on rows whose owner is their own user id; an administrator acts
  on every row, ownerless ones included. A foreign, ownerless or unknown id
  answers with the same 404 as an unknown path, so existence is never
  confirmed to a user.
- A location id in a path is shape-checked (digits only) before any lookup.
- Coordinates must be finite and in range and are stored rounded to four
  decimals; the time zone must be an IANA zone; control characters are
  removed from the name.
- A user holds at most `USER_LOCATION_LIMIT` locations and every mutation
  attempt counts toward a per-user throttle. Administrators are neither
  capped nor throttled.
- Each change and its audit row share one transaction; a refusal is audited
  afterwards as a denied row.
"""
import functools
import math
import re
import sqlite3
import unicodedata
import zoneinfo

from companion import (
    access, audit, console_flash, device_scope, i18n, prefs, route_types, throttle)
from companion.pages import locations_page
from server import fleet_db

# Same literals as companion/console_routes.py (which imports this module, so
# it cannot be imported at module level); a test pins that the two agree.
LOCATIONS_PATH = "/locations"
LOCATIONS_ADD_PATH = "/locations/add"
LOCATION_ACTION_PREFIX = "/locations/"
EDIT_SUFFIX = "/edit"
DELETE_SUFFIX = "/delete"

USER_LOCATION_LIMIT = 10
MUTATION_LIMIT = 20
MUTATION_LOCKOUT_S = 600
_ID_RE = re.compile(r"^[0-9]{1,9}$")
_NUMBER_RE = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$")
_ZONE_NAME_RE = re.compile(r"^[A-Za-z0-9_+\-/]{1,64}$")
_MAX_NUMBER_CHARS = 20

# One entry per user id; every create, edit or delete attempt counts.
_MUTATIONS = throttle.LockoutThrottle(limit=MUTATION_LIMIT, lockout_s=MUTATION_LOCKOUT_S)

FLASH_ADDED = "locations.added"
FLASH_SAVED = "locations.saved"
FLASH_DELETED = "locations.deleted"
FLASH_LIMIT = "locations.limit"
FLASH_IN_USE = "locations.in_use"
FLASH_RATE_LIMITED = "locations.rate_limited"

console_flash.register_flash(
    FLASH_ADDED, "success",
    i18n.msg("admin_locations.flash_location_added", "Location added"),
    i18n.msg(
        "admin_locations.flash_location_added_detail",
        "{name} can now be chosen for a frame."))
console_flash.register_flash(
    FLASH_SAVED, "success",
    i18n.msg("admin_locations.flash_location_saved", "Location saved"),
    i18n.msg("admin_locations.flash_location_saved_detail", "{name} was updated."))
console_flash.register_flash(
    FLASH_DELETED, "success",
    i18n.msg("admin_locations.flash_location_deleted", "Location deleted"),
    i18n.msg("admin_locations.flash_location_deleted_detail", "{name} was removed."))
console_flash.register_flash(
    FLASH_LIMIT, "warning",
    i18n.msg("admin_locations.flash_location_limit_reached", "Location limit reached"),
    i18n.msg(
        "admin_locations.flash_location_limit_reached_detail",
        "You can keep up to {n} locations. Delete one before adding another."))
console_flash.register_flash(
    FLASH_IN_USE, "error",
    i18n.msg("admin_locations.flash_location_not_deleted", "Location not deleted"),
    i18n.msg(
        "admin_locations.flash_this_location_is_used_by_a_frame",
        "This location is used by a frame."))
console_flash.register_flash(
    FLASH_RATE_LIMITED, "warning",
    i18n.msg("admin_locations.flash_too_many_changes", "Too many changes"),
    i18n.msg(
        "admin_locations.flash_too_many_changes_detail",
        "Wait a few minutes before changing locations again. Nothing was modified."))


class _NotFound(Exception):
    """The row is unknown or the caller may not act on it."""


class _LimitReached(Exception):
    """The user already holds the maximum number of locations."""


# ---- helpers ------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def time_zone_names():
    """The IANA zone names offered by the select, sorted, with the default
    always present."""
    names = {
        name for name in zoneinfo.available_timezones()
        if "/" in name and not name.startswith(("Etc/", "posix/", "right/"))}
    names.add(locations_page.DEFAULT_TIMEZONE)
    return tuple(sorted(names))


def _principal(h):
    """The signed-in principal when it may use the page at all, else None."""
    principal = h._safe_principal()
    if principal is None:
        return None
    if principal.role != access.ADMIN and principal.user_id is None:
        return None
    return principal


def _is_admin(principal):
    return principal.role == access.ADMIN


def _not_found(h):
    # The same answer as a path that is not in the table: no frame scope, so
    # the shell carries nothing a refused id could be told apart by.
    device_scope.set_request_scope(None, ())
    return h.send_html(404, h._not_found_page())


def _target_id(m):
    """The numeric location id from the path, or None for any other shape."""
    return int(m.captured) if _ID_RE.match(m.captured) else None


def _may_act(principal, row):
    if row is None:
        return False
    if _is_admin(principal):
        return True
    return row["owner_user_id"] is not None and row["owner_user_id"] == principal.user_id


def _throttled(principal):
    """True when this attempt must be refused. A user's attempt that is let
    through is counted here, so every mutation counts."""
    if _is_admin(principal):
        return False
    key = str(principal.user_id)
    if _MUTATIONS.locked_for(key):
        return True
    _MUTATIONS.record_failure(key)
    return False


def _back(flash_key, **params):
    return console_flash.queue_flash(flash_key, **params)


def _redirect(h, flash_key, **params):
    return h.redirect(LOCATIONS_PATH, set_cookie=_back(flash_key, **params))


def _clean_name(raw):
    text = "".join(ch for ch in raw if unicodedata.category(ch) not in ("Cc", "Zl", "Zp"))
    return text.strip()


def _parse_coordinate(raw, limit):
    """The coordinate rounded to the stored precision, or None when it is
    not a finite number within +-`limit`."""
    text = raw.strip()
    if len(text) > _MAX_NUMBER_CHARS or not _NUMBER_RE.match(text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or abs(value) > limit:
        return None
    # Adding 0.0 turns a negative zero into a plain zero.
    return round(value, locations_page.COORDINATE_DECIMALS) + 0.0


def _valid_zone(raw):
    if not _ZONE_NAME_RE.match(raw):
        return False
    try:
        zoneinfo.ZoneInfo(raw)
    except (KeyError, ValueError, OSError):
        return False
    return True


def _validate(form, target_id):
    """(clean values or None, FormState echoing the input). The one place
    both add and edit validate."""
    raw_name = form.get(locations_page.NAME_FIELD, "")
    raw_lat = form.get(locations_page.LATITUDE_FIELD, "")
    raw_lon = form.get(locations_page.LONGITUDE_FIELD, "")
    raw_zone = form.get(locations_page.TIMEZONE_FIELD, "")
    name = _clean_name(raw_name)
    latitude = _parse_coordinate(raw_lat, 90.0)
    longitude = _parse_coordinate(raw_lon, 180.0)
    errors = {}
    if not name or len(name) > locations_page.NAME_MAX_CHARS:
        errors[locations_page.NAME_FIELD] = i18n.t(locations_page.ERROR_NAME)
    if latitude is None:
        errors[locations_page.LATITUDE_FIELD] = i18n.t(locations_page.ERROR_LATITUDE)
    if longitude is None:
        errors[locations_page.LONGITUDE_FIELD] = i18n.t(locations_page.ERROR_LONGITUDE)
    if not _valid_zone(raw_zone):
        errors[locations_page.TIMEZONE_FIELD] = i18n.t(locations_page.ERROR_TIMEZONE)
    state = locations_page.FormState(
        target_id, name[:locations_page.NAME_MAX_CHARS], raw_lat.strip()[:_MAX_NUMBER_CHARS],
        raw_lon.strip()[:_MAX_NUMBER_CHARS],
        raw_zone if _ZONE_NAME_RE.match(raw_zone) else locations_page.DEFAULT_TIMEZONE, errors)
    if errors:
        return None, state
    return (name, latitude, longitude, raw_zone), state


# ---- page ---------------------------------------------------------------


def _rows(conn, principal):
    is_admin = _is_admin(principal)
    stored = fleet_db.list_locations_for(conn, principal.user_id, is_admin)
    usage = fleet_db.location_usage_counts(conn)
    emails = {}
    if is_admin:
        emails = {
            int(row["id"]): str(row["email"])
            for row in conn.execute("SELECT id, email FROM users")}
    return tuple(
        locations_page.LocationRow(
            location_id=int(row["id"]), name=str(row["name"]),
            latitude=float(row["latitude"]), longitude=float(row["longitude"]),
            timezone=str(row["timezone"]), used_by=usage.get(int(row["id"]), 0),
            owner=(emails.get(row["owner_user_id"]) if row["owner_user_id"] is not None
                   else None))
        for row in stored)


def _view(h, principal, state):
    conn = fleet_db.connect(h.args.state_dir)
    try:
        rows = _rows(conn, principal)
    finally:
        conn.close()
    return locations_page.LocationsView(
        rows=rows, is_admin=_is_admin(principal), timezones=time_zone_names(), state=state)


def _render(h, principal, state=None, status=200):
    """Admins get the console shell with its section sub-nav; a user's page
    is the plain shell (the sub-nav links administration pages)."""
    from companion import console_routes, layout

    def body():
        return locations_page.render(_view(h, principal, state))

    if _is_admin(principal):
        return h._console_page(
            console_routes.LOCATIONS_ROUTE, None, body, locations_page.LOCATIONS_PURPOSE,
            status=status)
    h.page_context()
    title = i18n.t(console_routes.CONSOLE_TITLES[console_routes.LOCATIONS_ROUTE])
    flash_html, clear_cookie = console_flash.take_flash(h.headers.get("Cookie"))
    page = layout.page_shell(
        title=title, active=layout.nav_slug(console_routes.LOCATIONS_ROUTE),
        body=layout.page_header(title, i18n.t(locations_page.LOCATIONS_PURPOSE)) + body(),
        ui_theme=h._resolved_ui_theme(), flash=flash_html or None, health_alert=None)
    return h.send_html(status, page, set_cookies=(clear_cookie,) if clear_cookie else ())


def handle_locations_get(h, m):
    principal = _principal(h)
    if principal is None:
        return _not_found(h)
    return _render(h, principal)


# ---- add ----------------------------------------------------------------


def handle_add(h, m):
    principal = _principal(h)
    if principal is None:
        return _not_found(h)
    if _throttled(principal):
        return _redirect(h, FLASH_RATE_LIMITED)
    values, state = _validate(h.read_form(), None)
    if values is None:
        return _render(h, principal, state, status=400)
    name, latitude, longitude, zone = values
    is_admin = _is_admin(principal)
    conn = fleet_db.connect(h.args.state_dir)
    try:
        try:
            with fleet_db.transaction(conn):
                if (not is_admin and fleet_db.count_locations_owned(
                        conn, principal.user_id) >= USER_LOCATION_LIMIT):
                    raise _LimitReached()
                location_id = fleet_db.add_location(
                    conn, name, latitude, longitude, zone,
                    None if is_admin else principal.user_id)
                audit.record_in(h, conn, "location.add", "location", str(location_id), "ok")
        except _LimitReached:
            audit.record_standalone(
                h, "location.add", "location", None, "denied", {"reason": "limit"})
            return _redirect(h, FLASH_LIMIT, n=USER_LOCATION_LIMIT)
    finally:
        conn.close()
    return _redirect(h, FLASH_ADDED, name=name)


# ---- edit and delete ----------------------------------------------------


def _open_for_action(h, m):
    """(principal, location id) for an edit or delete that may proceed to the
    row check, or the response that ends it."""
    principal = _principal(h)
    location_id = _target_id(m)
    if principal is None or location_id is None:
        return None, _not_found(h)
    if _throttled(principal):
        return None, _redirect(h, FLASH_RATE_LIMITED)
    return (principal, location_id), None


def handle_edit(h, m):
    opened, response = _open_for_action(h, m)
    if response is not None:
        return response
    principal, location_id = opened
    conn = fleet_db.connect(h.args.state_dir)
    try:
        # Checked before the input is validated, so a foreign id never
        # learns anything from a validation answer.
        if not _may_act(principal, fleet_db.get_location(conn, location_id)):
            return _not_found(h)
        values, state = _validate(h.read_form(), location_id)
        if values is None:
            return _render(h, principal, state, status=400)
        try:
            with fleet_db.transaction(conn):
                if not _may_act(principal, fleet_db.get_location(conn, location_id)):
                    raise _NotFound()
                fleet_db.update_location(conn, location_id, *values)
                audit.record_in(
                    h, conn, "location.update", "location", str(location_id), "ok")
        except _NotFound:
            return _not_found(h)
    finally:
        conn.close()
    return _redirect(h, FLASH_SAVED, name=values[0])


def handle_delete(h, m):
    opened, response = _open_for_action(h, m)
    if response is not None:
        return response
    principal, location_id = opened
    conn = fleet_db.connect(h.args.state_dir)
    try:
        try:
            with fleet_db.transaction(conn):
                row = fleet_db.get_location(conn, location_id)
                if not _may_act(principal, row):
                    raise _NotFound()
                name = str(row["name"])
                fleet_db.delete_location_if_unused(conn, location_id)
                audit.record_in(
                    h, conn, "location.delete", "location", str(location_id), "ok")
        except _NotFound:
            return _not_found(h)
        except fleet_db.LocationInUse:
            audit.record_standalone(
                h, "location.delete", "location", str(location_id), "denied",
                {"reason": "in_use"})
            return _redirect(h, FLASH_IN_USE)
    finally:
        conn.close()
    return _redirect(h, FLASH_DELETED, name=name)


# ---- assignment to a frame ----------------------------------------------


class _Refused(Exception):
    """The assignment is not allowed or names nothing that exists."""


def _viewer_options(conn, device, is_admin):
    """The (id, name) pairs the viewer of `device`'s Display page may choose:
    every location for an administrator, for a user only the frame owner's own
    (a user reaches a frame only when they own it)."""
    if is_admin:
        rows = fleet_db.list_locations(conn)
    elif device.owner_user_id is None:
        rows = []
    else:
        rows = fleet_db.list_locations_for(conn, device.owner_user_id, False)
    return [(int(row["id"]), str(row["name"])) for row in rows]


def display_picker_html(ctx):
    """The Location picker for the Display page of `ctx.device`, or "" when
    the frame has no fleet row, the fleet database cannot be read, or an
    administrator has no location to offer."""
    device, root = ctx.device, ctx.root_state_dir
    role = prefs.current_principal()
    if device is None or root is None or role is None or device.id == device_scope.LIVE_ID:
        return ""
    is_admin = role[1] == access.ADMIN
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return ""
    try:
        row = fleet_db.get_device(conn, device.id)
        if row is None:
            return ""
        options = _viewer_options(conn, device, is_admin)
    except sqlite3.Error:
        return ""
    finally:
        conn.close()
    current = None if row["location_id"] is None else int(row["location_id"])
    if is_admin and not options:
        return ""
    return locations_page.picker_html(
        options, current, _settings_form_id(), _dirty_section_attr())


def _settings_form_id():
    # Imported on use: the settings page imports this module on use too.
    from companion.settings import form
    return form.SETTINGS_FORM_ID


def _dirty_section_attr():
    from companion.settings import form
    return form.DIRTY_SECTION_ATTR


def apply_device_location(form, ctx, handler, previous=None):
    """Apply the Display form's `location_id` to `ctx.device`; True when the
    form carries none, it equals the stored value, or the assignment was
    made, False when it was refused (nothing is changed then).

    When `previous` is a list and an assignment was made, the location id it
    replaced is appended, so the caller can undo it with
    `undo_device_location` if a later step of the same save fails.

    A user may assign only a location they own and only to a frame they own;
    an administrator may assign any location. The change and its audit row
    share one transaction; a refusal is audited afterwards as denied."""
    raw = form.get(locations_page.LOCATION_FIELD)
    if raw is None:
        return True
    principal = handler._safe_principal()
    device = ctx.device
    if principal is None or device is None or ctx.root_state_dir is None:
        return False
    if raw == "":
        location_id = None
    elif _ID_RE.match(raw):
        location_id = int(raw)
    else:
        return _deny_assignment(handler, device, None)
    conn = fleet_db.connect(ctx.root_state_dir)
    try:
        row = fleet_db.get_device(conn, device.id)
        if row is not None and row["location_id"] == location_id:
            return True
        replaced = None if row is None else row["location_id"]
        try:
            with fleet_db.transaction(conn):
                try:
                    assigned = fleet_db.set_device_location_checked(
                        conn, device.id, location_id, principal.user_id,
                        _is_admin(principal))
                except (PermissionError, ValueError) as exc:
                    raise _Refused() from exc
                if not assigned:
                    raise _Refused()
                audit.record_in(
                    handler, conn, "location.update", "device", device.id, "ok",
                    {"location_id": location_id})
        except _Refused:
            return _deny_assignment(handler, device, location_id)
        if previous is not None:
            previous.append(replaced)
    finally:
        conn.close()
    return True


def undo_device_location(ctx, handler, location_id):
    """Put `location_id` back on `ctx.device` after a failed save.

    Skips the ownership check on purpose: it restores a value that was
    already stored. The restoration is audited next to the original change.
    """
    conn = fleet_db.connect(ctx.root_state_dir)
    try:
        with fleet_db.transaction(conn):
            conn.execute(
                "UPDATE devices SET location_id = ? WHERE id = ?",
                (location_id, ctx.device.id))
            audit.record_in(
                handler, conn, "location.update", "device", ctx.device.id, "failed",
                {"location_id": location_id, "reason": "settings_save_failed"})
    finally:
        conn.close()


def _deny_assignment(handler, device, location_id):
    audit.record_standalone(
        handler, "location.update", "device", device.id, "denied",
        {"location_id": location_id})
    return False


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(LOCATIONS_PATH), handle_locations_get,
        route_types.SIGNED_IN),
    route_types.Route(
        "POST", route_types.Exact(LOCATIONS_ADD_PATH), handle_add,
        route_types.SIGNED_IN, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(LOCATION_ACTION_PREFIX, EDIT_SUFFIX),
        handle_edit, route_types.SIGNED_IN, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(LOCATION_ACTION_PREFIX, DELETE_SUFFIX),
        handle_delete, route_types.SIGNED_IN, csrf=True),
)
