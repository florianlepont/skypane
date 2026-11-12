"""POST /detection: store a device's detection choice or a saved location.

The route's access policy has already decided that the caller owns the
device (or is an admin) before this runs. Everything posted is untrusted:
only a fixed set of fields is read, each is stripped of control characters
and length-capped, and every value is validated on the server for the
posted mode only. A rejected post re-renders the page with the exact inline
errors (status 400 for save_place, 200 for the older actions) and writes
nothing; a write only ever targets the device the
dispatcher bound to the request.

Locations belong to the device's owner. A signed-in user acts on their own
locations; an admin acts on the owner's (or their own for a device without
an owner), so the list, the select and the form always share one subject.
A co-manager picks from the owner's locations but never writes a saved
location; save_place writes the frame's own position, which is part of the
frame's detection setting, so a co-manager may use it.
"""
import collections
import math
import re
import sqlite3
from urllib.parse import quote

from companion import access, device_scope, flash, page_policy
from companion.pages import detection_page, place_page
from companion.settings import form_post, quiet_hours
from server import airports, detection, device_config, fleet_db

# Posted fields the handler reads; anything else is dropped.
FORM_FIELDS = (
    "action", "mode", "airport", "runway", "location_id", "radius_km",
    "location_name", "latitude", "longitude", "timezone", "place_label")
FIELD_CAP = 64
NAME_MAX = 60

_RADIUS_RE = re.compile(r"\d{1,3}\Z", re.ASCII)
_ID_RE = re.compile(r"\d{1,9}\Z", re.ASCII)
_DECIMAL_RE = re.compile(r"[+-]?(?:\d+(?:[.,]\d{0,6})?|[.,]\d{1,6})\Z", re.ASCII)

# conn: this request's fleet.db handle; actor_id/is_admin: the signed-in
# principal; subject_id: whose locations the page lists and edits; may_write:
# false for a co-manager, who may only choose among the owner's locations.
Subject = collections.namedtuple(
    "Subject", "conn actor_id is_admin owner_id subject_id may_write",
    defaults=(True,))


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
    co_manager = (
        not is_admin and actor_id is not None and owner_id is not None
        and actor_id != owner_id
        and fleet_db.is_co_manager(conn, device.id, actor_id))
    if (is_admin or co_manager) and owner_id is not None:
        subject_id = owner_id
    else:
        subject_id = actor_id
    return Subject(conn, actor_id, is_admin, owner_id, subject_id, not co_manager)


def _location_dict(row):
    return {key: row[key] for key in ("id", "name", "latitude", "longitude", "timezone")}


def _may_see_location(subject, located):
    """Whether the viewer may be told this location's name: an administrator,
    anyone for an ownerless location, else only its owner."""
    owner = located["owner_user_id"]
    return subject.is_admin or owner is None or owner == subject.subject_id


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
        if (
            located is not None and detection_page.location_usable(located)
            and _may_see_location(subject, located)
        ):
            name = located["name"]
    other_owner = (
        (subject.is_admin or not subject.may_write) and subject.owner_id is not None
        and subject.owner_id != subject.actor_id)
    return detection_page.LocationScope(
        rows, other_owner, location_id, name, subject.may_write)


def location_scope(handler, device):
    """`scope_for()` for a GET; an unreadable fleet.db reads as no locations."""
    try:
        return scope_for(subject_for(handler, device), device)
    except sqlite3.Error:
        return detection_page.LocationScope()


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


def frame_place(handler, device):
    """The device's own position row for the page, or None when it has none,
    cannot be read, or belongs to someone the viewer may not see named."""
    try:
        subject = subject_for(handler, device)
        place = fleet_db.frame_position(subject.conn, device.id)
        if place is None:
            return None
        located = fleet_db.get_location(subject.conn, place["id"])
        if located is None or not _may_see_location(subject, located):
            return None
        return place
    except sqlite3.Error:
        return None


def _rerender(handler, ctx, device, errors, form, status=200):
    """Render the page again with the refusal beside its fields. Every
    refused post, whatever its action, sends the map page policy."""
    body = place_page.render(
        ctx, errors=errors, submitted=form, place=frame_place(handler, device))
    return handler.send_html(
        status, handler._page_shell_for(detection_page.DETECTION_ROUTE, body, ctx),
        policy=page_policy.MAP_PAGE_POLICY)


def _store_detection(ctx, device, subject, form):
    """None once stored, else the field errors that refuse it. A write
    failure raises OSError or sqlite3.Error."""
    if form["mode"] == detection_page.MODE_RUNWAY:
        detection.apply_runway_selection(ctx.state_dir, form["airport"], form["runway"])
        return None
    before = fleet_db.get_device(subject.conn, device.id)
    previous = None if before is None else before["location_id"]
    try:
        assigned = fleet_db.set_device_location_checked(
            subject.conn, device.id, int(form["location_id"]),
            subject.actor_id, subject.is_admin)
    except (PermissionError, ValueError):
        return {"location_id": detection_page.ERROR_LOCATION_UNAVAILABLE}
    if not assigned:
        raise OSError("device has no fleet.db row")
    try:
        detection.apply_position_selection(ctx.state_dir, int(form["radius_km"]))
    except OSError:
        _restore_location(subject.conn, device.id, previous)
        raise
    return None


def _restore_location(conn, device_id, location_id):
    """Put the previous location back after a failed config write. This
    restores an already stored value, so it skips the ownership check; a
    failure here is ignored because the caller is already reporting one."""
    try:
        with fleet_db.transaction(conn):
            conn.execute(
                "UPDATE devices SET location_id = ? WHERE id = ?",
                (location_id, device_id))
    except sqlite3.Error:
        pass


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
    target = form.get("location_id", "")
    # An edit keeps the stored timezone, so only a new location is checked.
    if not target and form.get("timezone") != quiet_hours.CURATED_TIMEZONES[0][0]:
        errors["timezone"] = detection_page.ERROR_TIMEZONE
    if target and _find_row(rows, target) is None:
        errors["location_form"] = detection_page.ERROR_LOCATION_UNAVAILABLE
    return errors, name, lat, lon


def _write_location(subject, form, name, lat, lon):
    """Create the location for the subject, or update one the subject owns.
    False when an edit target is not the subject's."""
    target = form.get("location_id", "")
    with fleet_db.transaction(subject.conn):
        if not target:
            fleet_db.add_location(
                subject.conn, name, lat, lon, form["timezone"],
                owner_user_id=subject.subject_id)
            return True
        current = fleet_db.get_location(subject.conn, int(target))
        if current is None or current["owner_user_id"] != subject.subject_id:
            return False
        return fleet_db.update_location(
            subject.conn, int(target), name, lat, lon, current["timezone"])


def _save_location(handler, ctx, device, subject, scope, form):
    if subject.subject_id is None or not subject.may_write:
        return _rerender(
            handler, ctx, device,
            {"location_form": detection_page.ERROR_LOCATION_UNAVAILABLE}, form)
    errors, name, lat, lon = _location_errors(form, scope.rows)
    if errors:
        return _rerender(handler, ctx, device, errors, form)
    try:
        written = _write_location(subject, form, name, lat, lon)
    except (sqlite3.Error, ValueError):
        return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    if not written:
        return _rerender(
            handler, ctx, device,
            {"location_form": detection_page.ERROR_LOCATION_UNAVAILABLE}, form)
    return _redirect_with(handler, flash.FLASH_KEY_LOCATION_SAVED)

# A place is one frame's own position plus what it follows. The mode, airport
# and runway are validated as the detection form does; the pin is range-checked
# here and, for the area mode, held to the coarse France box.
PLACE_LABEL_FALLBACK = detection_page.DEFAULT_PLACE_LABEL
# How far, in degrees, a pin may sit from an airport and still carry its name.
_AIRPORT_PIN_TOLERANCE = 0.0005


def _pin_errors(form, errors, required):
    """The posted (latitude, longitude), or None when no pin was posted (or
    one was refused, with the message noted in `errors`)."""
    raw_lat, raw_lon = form.get("latitude", ""), form.get("longitude", "")
    if not required and not raw_lat and not raw_lon:
        return None
    lat, lon = parse_coordinate(raw_lat), parse_coordinate(raw_lon)
    if lat is None:
        errors["latitude"] = detection_page.ERROR_NUMBER
    if lon is None:
        errors["longitude"] = detection_page.ERROR_NUMBER
    if lat is None or lon is None:
        return None
    if required and not detection.inside_france(lat, lon):
        errors["latitude"] = detection_page.ERROR_LOCATION_OUTSIDE
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        errors["latitude"] = detection_page.ERROR_NUMBER
        return None
    return lat, lon


def _place_runway(form, errors):
    """(lat, lon, default label) of a runway-mode place: the moved pin if one
    was posted, else the airport's own coordinates."""
    errors.update(_runway_errors(form))
    pin = _pin_errors(form, errors, False)
    airport = airports.find_airport(form.get("airport"))
    if errors or airport is None:
        return None, None, None
    lat, lon = pin if pin is not None else (airport.lat, airport.lon)
    return lat, lon, airport.name


def _left_airport_label(label, lat, lon):
    """Whether `label` is the name of a catalogue airport the pin is not on:
    the name an airport choice left in the field before the pin was moved."""
    wanted = label.casefold()
    named = [a for a in airports.load_catalogue().values() if a.name.casefold() == wanted]
    return bool(named) and not any(
        abs(a.lat - lat) <= _AIRPORT_PIN_TOLERANCE
        and abs(a.lon - lon) <= _AIRPORT_PIN_TOLERANCE for a in named)


def _place_position(form, errors):
    pin = _pin_errors(form, errors, True)
    radius = form.get("radius_km", "")
    try:
        if not _RADIUS_RE.match(radius):
            raise ValueError("radius")
        detection.validate_radius_km(int(radius))
    except ValueError:
        errors["radius_km"] = detection_page.ERROR_RADIUS
    if pin is None or errors:
        return None, None, None
    return pin[0], pin[1], None


def parse_place(form, current_zone):
    """(place, errors) for a save_place post. `place` is None when anything
    is refused; `errors` maps field -> message."""
    errors = {}
    mode = form.get("mode")
    if mode == detection_page.MODE_RUNWAY:
        lat, lon, default_label = _place_runway(form, errors)
    elif mode == detection_page.MODE_POSITION:
        lat, lon, default_label = _place_position(form, errors)
    else:
        return None, {"mode": detection_page.ERROR_MODE}
    label = form.get("place_label", "").strip()
    if len(label) > NAME_MAX:
        errors["place_label"] = detection_page.ERROR_NAME
    zone = form_post.resolve_timezone(form, errors, current_zone)
    if errors or zone is form_post.FAILED:
        return None, errors
    if mode == detection_page.MODE_POSITION and _left_airport_label(label, lat, lon):
        label = ""
    place = {
        "mode": mode, "airport": form.get("airport"), "runway": form.get("runway"),
        "radius_km": form.get("radius_km"), "lat": lat, "lon": lon,
        "label": label or default_label or PLACE_LABEL_FALLBACK,
        "forwarded_zone": zone["timezone"]}
    return place, {}


def _store_place(ctx, device, subject, place):
    """Write the position row, then the detection setting, then a changed time
    zone. A failed later write puts the previous location link back; the
    failure is raised (OSError, sqlite3.Error, PermissionError, ValueError)."""
    row_zone = place["forwarded_zone"] or ctx.device_config["timezone"]
    before = fleet_db.get_device(subject.conn, device.id)
    previous = None if before is None else before["location_id"]
    fleet_db.save_frame_position(
        subject.conn, device.id, place["label"], place["lat"], place["lon"],
        row_zone, subject.actor_id, subject.is_admin)
    try:
        if place["mode"] == detection_page.MODE_RUNWAY:
            detection.apply_runway_selection(
                ctx.state_dir, place["airport"], place["runway"])
        else:
            detection.apply_position_selection(
                ctx.state_dir, int(place["radius_km"]))
        if place["forwarded_zone"] is not None:
            device_config.save_device_config(
                ctx.state_dir, timezone=place["forwarded_zone"])
    except (OSError, ValueError):
        _restore_location(subject.conn, device.id, previous)
        raise


def _save_place(handler, ctx, device, subject, form):
    place, errors = parse_place(form, ctx.device_config["timezone"])
    if errors:
        return _rerender(handler, ctx, device, errors, form, status=400)
    try:
        _store_place(ctx, device, subject, place)
    except (OSError, ValueError, PermissionError, sqlite3.Error):
        return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    return _redirect_with(handler, flash.FLASH_KEY_PLACE_SAVED)


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
    if form.get("action") == detection_page.ACTION_SAVE_PLACE:
        return _save_place(handler, ctx, device, subject, form)
    errors = validate(form, scope.rows)
    if not errors:
        try:
            errors = _store_detection(ctx, device, subject, form)
        except (OSError, sqlite3.Error):
            return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    if errors:
        return _rerender(handler, ctx, device, errors, form)
    return _redirect_with(handler, flash.FLASH_KEY_DETECTION_SAVED)
