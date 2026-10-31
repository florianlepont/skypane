"""POST /detection: store a device's detection choice or a saved location.

The route's access policy has already decided that the caller owns the
device (or is an admin) before this runs. Everything posted is untrusted:
only a fixed set of fields is read, each is stripped of control characters
and length-capped, and every value is validated on the server for the
posted mode only. A rejected post re-renders the page at 200 with the exact
inline errors and writes nothing; a write only ever targets the device the
dispatcher bound to the request.

Locations belong to the device's owner. A signed-in user acts on their own
locations; an admin acts on the owner's (or their own for a device without
an owner), so the list, the select and the form always share one subject.
"""
import collections
import math
import re
import sqlite3
from urllib.parse import quote

from companion import access, device_scope, flash
from companion.pages import detection_page
from companion.settings import quiet_hours
from server import detection, fleet_db

# Posted fields the handler reads; anything else is dropped.
FORM_FIELDS = (
    "action", "mode", "airport", "runway", "location_id", "radius_km",
    "location_name", "latitude", "longitude", "timezone")
FIELD_CAP = 64
NAME_MAX = 60

_RADIUS_RE = re.compile(r"\d{1,3}\Z", re.ASCII)
_ID_RE = re.compile(r"\d{1,9}\Z", re.ASCII)
_DECIMAL_RE = re.compile(r"[+-]?(?:\d+(?:[.,]\d{0,6})?|[.,]\d{1,6})\Z", re.ASCII)

# conn: this request's fleet.db handle; actor_id/is_admin: the signed-in
# principal; subject_id: whose locations the page lists and edits.
Subject = collections.namedtuple("Subject", "conn actor_id is_admin owner_id subject_id")


def clean_form(raw):
    """The known fields of `raw`, control characters removed, capped."""
    return {
        name: detection_page.clean_text(raw.get(name), FIELD_CAP)
        for name in FORM_FIELDS if name in raw}


def subject_for(handler, device):
    """Who the device's locations belong to for this request."""
    principal = handler._safe_principal()
    conn = handler._fleet_conn()
    owner_id = fleet_db.get_device_owner(conn, device.id)
    is_admin = principal is not None and principal.role == access.ADMIN
    actor_id = principal.user_id if principal is not None else None
    if is_admin and owner_id is not None:
        subject_id = owner_id
    else:
        subject_id = actor_id
    return Subject(conn, actor_id, is_admin, owner_id, subject_id)


def _location_dict(row):
    return {key: row[key] for key in ("id", "name", "latitude", "longitude", "timezone")}


def scope_for(subject, device):
    """The LocationScope the page renders from."""
    if subject.subject_id is None:
        return detection_page.LocationScope()
    rows = [
        _location_dict(row)
        for row in fleet_db.list_locations_for(subject.conn, subject.subject_id, False)]
    device_row = fleet_db.get_device(subject.conn, device.id)
    location_id = device_row["location_id"] if device_row is not None else None
    name = None
    if location_id is not None:
        located = fleet_db.get_location(subject.conn, location_id)
        if located is not None and detection_page.location_usable(located):
            name = located["name"]
    other_owner = (
        subject.is_admin and subject.owner_id is not None
        and subject.owner_id != subject.actor_id)
    return detection_page.LocationScope(rows, other_owner, location_id, name)


def location_scope(handler, device):
    """`scope_for()` for a GET; an unreadable fleet.db reads as no locations."""
    try:
        return scope_for(subject_for(handler, device), device)
    except sqlite3.Error:
        return detection_page.LocationScope()


def card_location_name(handler, device, device_cfg):
    """The device's usable location name for the Detection card on Display
    and Device; None unless the saved setting follows a position, so a
    runway device never reads fleet.db for it."""
    if detection.current_selection(device_cfg)["mode"] != detection.POSITION_MODE:
        return None
    return location_scope(handler, device).device_location_name


def _runway_errors(form):
    """Field -> message for a runway-mode post; empty when it is valid."""
    airport = form.get("airport", "")
    if not airport:
        return {"airport": detection_page.ERROR_AIRPORT}
    if not form.get("runway"):
        return {"runway": detection_page.ERROR_RUNWAY_MISSING}
    try:
        detection.validate_runway_selection(airport, form["runway"])
    except ValueError as exc:
        code = exc.args[0] if exc.args else ""
        if code == "airport":
            return {"airport": detection_page.ERROR_AIRPORT}
        return {"runway": detection_page.ERROR_RUNWAY_UNKNOWN}
    return {}


def _find_row(rows, raw):
    """The listed location whose id is the digits in `raw`, else None."""
    if not _ID_RE.match(raw or ""):
        return None
    wanted = int(raw)
    for row in rows:
        if row["id"] == wanted:
            return row
    return None


def _position_errors(form, rows):
    """Field -> message for a position-mode post; empty when it is valid."""
    errors = {}
    raw = form.get("location_id", "")
    row = _find_row(rows, raw)
    if not raw:
        errors["location_id"] = detection_page.ERROR_LOCATION_MISSING
    elif row is None:
        errors["location_id"] = detection_page.ERROR_LOCATION_UNAVAILABLE
    elif not detection.inside_france(row["latitude"], row["longitude"]):
        errors["location_id"] = detection_page.ERROR_LOCATION_OUTSIDE
    radius = form.get("radius_km", "")
    try:
        if not _RADIUS_RE.match(radius):
            raise ValueError("radius")
        detection.validate_radius_km(int(radius))
    except ValueError:
        errors["radius_km"] = detection_page.ERROR_RADIUS
    return errors


def validate(form, rows):
    """Field -> message for a detection post; empty when it can be stored.
    Only the posted mode's fields are looked at."""
    if form.get("action") != detection_page.ACTION_SAVE_DETECTION:
        return {"mode": detection_page.ERROR_MODE}
    if form.get("mode") == detection_page.MODE_RUNWAY:
        return _runway_errors(form)
    if form.get("mode") == detection_page.MODE_POSITION:
        return _position_errors(form, rows)
    return {"mode": detection_page.ERROR_MODE}


def _redirect_with(handler, flash_key):
    back = device_scope.scoped(detection_page.DETECTION_ROUTE)
    return handler.redirect("%s?flash=%s" % (back, quote(flash_key)))


def _rerender(handler, ctx, scope, errors, form):
    body = detection_page.render(ctx, errors=errors, submitted=form, locations=scope)
    return handler.send_html(
        200, handler._page_shell_for(detection_page.DETECTION_ROUTE, body, ctx))


def _store_detection(ctx, device, subject, form):
    """None once stored, else the field errors that refuse it. A write
    failure raises OSError or sqlite3.Error."""
    if form["mode"] == detection_page.MODE_RUNWAY:
        detection.apply_runway_selection(ctx.state_dir, form["airport"], form["runway"])
        return None
    try:
        assigned = fleet_db.set_device_location_checked(
            subject.conn, device.id, int(form["location_id"]),
            subject.actor_id, subject.is_admin)
    except (PermissionError, ValueError):
        return {"location_id": detection_page.ERROR_LOCATION_UNAVAILABLE}
    if not assigned:
        raise OSError("device has no fleet.db row")
    detection.apply_position_selection(ctx.state_dir, int(form["radius_km"]))
    return None


def parse_coordinate(text):
    """A finite decimal degree from `text` (comma or dot, at most six
    decimals, no exponent), else None."""
    text = (text or "").strip()
    if not _DECIMAL_RE.match(text):
        return None
    value = float(text.replace(",", "."))
    return value if math.isfinite(value) else None


def _location_errors(form, rows):
    """Field -> message for a location post, plus the parsed values."""
    errors = {}
    name = form.get("location_name", "").strip()
    if not 1 <= len(name) <= NAME_MAX:
        errors["location_name"] = detection_page.ERROR_NAME
    lat = parse_coordinate(form.get("latitude"))
    lon = parse_coordinate(form.get("longitude"))
    if lat is None:
        errors["latitude"] = detection_page.ERROR_NUMBER
    if lon is None:
        errors["longitude"] = detection_page.ERROR_NUMBER
    if lat is not None and lon is not None and not detection.inside_france(lat, lon):
        errors["latitude"] = detection_page.ERROR_LOCATION_OUTSIDE
    if form.get("timezone") != quiet_hours.CURATED_TIMEZONES[0][0]:
        errors["timezone"] = detection_page.ERROR_TIMEZONE
    target = form.get("location_id", "")
    if target and _find_row(rows, target) is None:
        errors["location_form"] = detection_page.ERROR_LOCATION_UNAVAILABLE
    return errors, name, lat, lon


def _write_location(subject, form, name, lat, lon):
    """Create the location for the subject, or update one the subject owns.
    False when an edit target is not the subject's."""
    zone = form["timezone"]
    target = form.get("location_id", "")
    with fleet_db.transaction(subject.conn):
        if not target:
            fleet_db.add_location(
                subject.conn, name, lat, lon, zone, owner_user_id=subject.subject_id)
            return True
        current = fleet_db.get_location(subject.conn, int(target))
        if current is None or current["owner_user_id"] != subject.subject_id:
            return False
        return fleet_db.update_location(subject.conn, int(target), name, lat, lon, zone)


def _save_location(handler, ctx, device, subject, scope, form):
    if subject.subject_id is None:
        return _rerender(
            handler, ctx, scope,
            {"location_form": detection_page.ERROR_LOCATION_UNAVAILABLE}, form)
    errors, name, lat, lon = _location_errors(form, scope.rows)
    if errors:
        return _rerender(handler, ctx, scope, errors, form)
    try:
        written = _write_location(subject, form, name, lat, lon)
    except (sqlite3.Error, ValueError):
        return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    if not written:
        return _rerender(
            handler, ctx, scope,
            {"location_form": detection_page.ERROR_LOCATION_UNAVAILABLE}, form)
    return _redirect_with(handler, flash.FLASH_KEY_LOCATION_SAVED)


def handle_post(handler, device):
    """Validate and store, then 303 back to the page; or re-render at 200
    with inline errors."""
    form = clean_form(handler.read_form())
    ctx = handler.page_context(device)
    try:
        subject = subject_for(handler, device)
        scope = scope_for(subject, device)
    except sqlite3.Error:
        return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    if form.get("action") == detection_page.ACTION_SAVE_LOCATION:
        return _save_location(handler, ctx, device, subject, scope, form)
    errors = validate(form, scope.rows)
    if not errors:
        try:
            errors = _store_detection(ctx, device, subject, form)
        except (OSError, sqlite3.Error):
            return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    if errors:
        return _rerender(handler, ctx, scope, errors, form)
    return _redirect_with(handler, flash.FLASH_KEY_DETECTION_SAVED)
