"""The Locations page body: the places a frame can show flights for, and the
"New location" card.

Pure markup: it takes a `LocationsView` and reads nothing else. The caller
decides which rows a viewer may see; this module only chooses the columns
(an Owner column appears for an administrator view). Every stored text is
escaped on output.
"""
from typing import NamedTuple

from companion import i18n
from companion.ui_base import escape_html

LOCATIONS_PURPOSE = i18n.msg(
    "admin_locations.places_a_frame_can_show_flights_for",
    "Places a frame can show flights for.")

NAME_FIELD = "name"
LATITUDE_FIELD = "latitude"
LONGITUDE_FIELD = "longitude"
TIMEZONE_FIELD = "timezone"
LOCATION_FIELD = "location_id"
DEFAULT_TIMEZONE = "Europe/Paris"
NAME_MAX_CHARS = 60
COORDINATE_DECIMALS = 4

_LOCATIONS_TEXT = i18n.msg("admin_locations.locations", "Locations")
_COUNT_MANY = i18n.msg("admin_locations.n_locations", "%d locations")
_COUNT_ONE = i18n.msg("admin_locations.one_location", "1 location")
_COL_NAME = i18n.msg("admin_locations.name", "Name")
_COL_POSITION = i18n.msg("admin_locations.latitude_longitude", "Latitude, longitude")
_COL_TIMEZONE = i18n.msg("admin_locations.time_zone", "Time zone")
_COL_USED_BY = i18n.msg("admin_locations.used_by", "Used by")
_COL_OWNER = i18n.msg("admin_locations.owner", "Owner")
_COL_ACTIONS = i18n.msg("admin_locations.actions", "Actions")
_PLATFORM = i18n.msg("admin_locations.platform", "Platform")
_LABEL_LATITUDE = i18n.msg("admin_locations.latitude", "Latitude")
_LABEL_LONGITUDE = i18n.msg("admin_locations.longitude", "Longitude")
_FRAMES_ONE = i18n.msg("admin_locations.one_frame", "1 frame")
_FRAMES_MANY = i18n.msg("admin_locations.n_frames", "%d frames")
_NO_FRAME = i18n.msg("admin_locations.no_frame", "No frame")

_EDIT_SUMMARY = i18n.msg("admin_locations.edit", "Edit")
_SAVE = i18n.msg("admin_locations.save_location", "Save location")
_KEEP_AS_IS = i18n.msg("admin_locations.keep_as_is", "Keep as is")
_DELETE_SUMMARY = i18n.msg("admin_locations.delete", "Delete")
_DELETE_BUTTON = i18n.msg("admin_locations.delete_location", "Delete location")
_DELETE_SENTENCE = i18n.msg(
    "admin_locations.frames_that_do_not_use_it_are_unaffected",
    "Frames that do not use it are unaffected.")
_KEEP_LOCATION = i18n.msg("admin_locations.keep_location", "Keep location")

_NEW_TITLE = i18n.msg("admin_locations.new_location", "New location")
_ADD_SUBMIT = i18n.msg("admin_locations.add_location", "Add location")
_EMPTY_HEADING = i18n.msg("admin_locations.no_locations_yet", "No locations yet")
_EMPTY_USER = i18n.msg(
    "admin_locations.add_a_place_to_choose_it_for_your_frame",
    "Add a place to choose it for your frame.")
_EMPTY_ADMIN = i18n.msg(
    "admin_locations.add_the_first_place_a_frame_can_use",
    "Add the first place a frame can use.")

ERROR_NAME = i18n.msg("admin_locations.enter_a_name", "Enter a name.")
ERROR_LATITUDE = i18n.msg(
    "admin_locations.enter_a_latitude_between_90_and_90",
    "Enter a latitude between -90 and 90.")
ERROR_LONGITUDE = i18n.msg(
    "admin_locations.enter_a_longitude_between_180_and_180",
    "Enter a longitude between -180 and 180.")
ERROR_TIMEZONE = i18n.msg("admin_locations.choose_a_time_zone", "Choose a time zone.")

_PICKER_LABEL = i18n.msg("admin_locations.location", "Location")
_PICKER_NONE_OPTION = i18n.msg("admin_locations.no_location", "No location")
_PICKER_MANAGE = i18n.msg("admin_locations.manage_locations", "Manage locations")
_PICKER_NONE_CHOSEN = i18n.msg("admin_locations.no_location_chosen", "No location chosen.")
_PICKER_ADD = i18n.msg("admin_locations.add_a_location", "Add a location")
_PICKER_ASSIGNED = i18n.msg(
    "admin_locations.assigned_by_an_administrator", "Assigned by an administrator")


class LocationRow(NamedTuple):
    """One location as the list shows it. `owner` is the owner's email, or
    None for an ownerless (platform) location."""
    location_id: int
    name: str
    latitude: float
    longitude: float
    timezone: str
    used_by: int
    owner: str | None


class FormState(NamedTuple):
    """The submitted values and field errors of a refused submission.
    `target_id` is None for the New location card, else the edited row."""
    target_id: int | None
    name: str
    latitude: str
    longitude: str
    timezone: str
    errors: dict


class LocationsView(NamedTuple):
    rows: tuple
    is_admin: bool
    timezones: tuple
    state: FormState | None = None


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _routes():
    # Imported on use: companion.console_routes imports the route modules.
    from companion import console_routes
    return console_routes


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def coordinate_text(value):
    """A coordinate as the fixed number of decimals it is stored with."""
    return "%.*f" % (COORDINATE_DECIMALS, value)


def _tz_options(timezones, selected):
    names = list(timezones)
    if selected not in names:
        names.insert(0, selected)
    return "".join(
        '<option value="%s"%s>%s</option>' % (
            _esc(name), " selected" if name == selected else "", _esc(name))
        for name in names)


def _field_error(field_id, message):
    if not message:
        return "", ""
    return (
        ' aria-invalid="true" aria-describedby="%s-error"' % field_id,
        '<p class="field-error" id="%s-error">%s</p>' % (field_id, _esc(message)))


def _fields_html(prefix, values, timezones, errors):
    """The four inputs of a location form. `prefix` keeps ids unique when a
    row's form appears in both the card and the table markup."""
    name_attrs, name_error = _field_error(prefix + "-name", errors.get(NAME_FIELD))
    lat_attrs, lat_error = _field_error(prefix + "-lat", errors.get(LATITUDE_FIELD))
    lon_attrs, lon_error = _field_error(prefix + "-lon", errors.get(LONGITUDE_FIELD))
    tz_attrs, tz_error = _field_error(prefix + "-tz", errors.get(TIMEZONE_FIELD))
    return (
        '<p><label for="%(p)s-name">%(name_l)s</label>'
        '<input type="text" id="%(p)s-name" name="%(name_f)s" required maxlength="%(max)d" '
        'autocomplete="off" value="%(name)s"%(name_a)s>%(name_e)s</p>'
        '<p><label for="%(p)s-lat">%(lat_l)s</label>'
        '<input type="text" inputmode="decimal" id="%(p)s-lat" name="%(lat_f)s" required '
        'maxlength="20" autocomplete="off" spellcheck="false" value="%(lat)s"%(lat_a)s>'
        "%(lat_e)s</p>"
        '<p><label for="%(p)s-lon">%(lon_l)s</label>'
        '<input type="text" inputmode="decimal" id="%(p)s-lon" name="%(lon_f)s" required '
        'maxlength="20" autocomplete="off" spellcheck="false" value="%(lon)s"%(lon_a)s>'
        "%(lon_e)s</p>"
        '<p><label for="%(p)s-tz">%(tz_l)s</label>'
        '<select id="%(p)s-tz" name="%(tz_f)s"%(tz_a)s>%(tz_o)s</select>%(tz_e)s</p>'
    ) % {
        "p": prefix, "max": NAME_MAX_CHARS,
        "name_l": _t(_COL_NAME), "name_f": NAME_FIELD, "name": _esc(values.name),
        "name_a": name_attrs, "name_e": name_error,
        "lat_l": _t(_LABEL_LATITUDE), "lat_f": LATITUDE_FIELD, "lat": _esc(values.latitude),
        "lat_a": lat_attrs, "lat_e": lat_error,
        "lon_l": _t(_LABEL_LONGITUDE), "lon_f": LONGITUDE_FIELD,
        "lon": _esc(values.longitude), "lon_a": lon_attrs, "lon_e": lon_error,
        "tz_l": _t(_COL_TIMEZONE), "tz_f": TIMEZONE_FIELD, "tz_a": tz_attrs,
        "tz_o": _tz_options(timezones, values.timezone), "tz_e": tz_error,
    }


def _row_values(row, view):
    """The values an edit form of `row` starts from: the refused submission
    when it was for this row, else the stored ones."""
    state = view.state
    if state is not None and state.target_id == row.location_id:
        return state
    return FormState(
        row.location_id, row.name, coordinate_text(row.latitude),
        coordinate_text(row.longitude), row.timezone, {})


def _action_path(row, suffix):
    return "%s%d%s" % (_routes().LOCATION_ACTION_PREFIX, row.location_id, suffix)


def _edit_html(row, view, prefix):
    values = _row_values(row, view)
    is_open = view.state is not None and view.state.target_id == row.location_id
    return (
        '<details class="fleet-confirm"%s><summary>%s</summary>'
        '<form method="post" action="%s" class="fleet-confirm__form" autocomplete="off">%s%s'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button>'
        '<a class="text-link" href="%s">%s</a></div></form></details>' % (
            " open" if is_open else "", _t(_EDIT_SUMMARY),
            _esc(_action_path(row, _routes().LOCATION_EDIT_SUFFIX)), _ui().csrf_field(),
            _fields_html("%s-%d" % (prefix, row.location_id), values, view.timezones,
                         values.errors),
            _t(_SAVE), _esc(_routes().LOCATIONS_ROUTE), _t(_KEEP_AS_IS)))


def _delete_html(row):
    return (
        '<details class="fleet-confirm"><summary>%s</summary>'
        '<form method="post" action="%s" class="fleet-confirm__form">%s'
        '<p class="text-body">%s%s</p>'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button>'
        '<a class="text-link" href="%s">%s</a></div></form></details>' % (
            _t(_DELETE_SUMMARY), _esc(_action_path(row, _routes().LOCATION_DELETE_SUFFIX)),
            _ui().csrf_field(), _ui().toast_icon_html("warning"), _t(_DELETE_SENTENCE),
            _t(_DELETE_BUTTON), _esc(_routes().LOCATIONS_ROUTE), _t(_KEEP_LOCATION)))


def _actions_html(row, view, prefix):
    return '<div class="fleet-actions">%s%s</div>' % (
        _edit_html(row, view, prefix), _delete_html(row))


def _position_html(row):
    return '<span class="mono">%s, %s</span>' % (
        _esc(coordinate_text(row.latitude)), _esc(coordinate_text(row.longitude)))


def _used_by_text(count):
    if count == 0:
        return i18n.t(_NO_FRAME)
    return i18n.t(_FRAMES_ONE) if count == 1 else i18n.t(_FRAMES_MANY) % count


def _owner_text(row):
    return row.owner if row.owner is not None else i18n.t(_PLATFORM)


def _table_row_html(row, view):
    owner = "<td>%s</td>" % _esc(_owner_text(row)) if view.is_admin else ""
    return (
        '<tr data-location="%d"><td><span class="cell-primary text-heading">%s</span></td>'
        "<td>%s</td><td>%s</td><td>%s</td>%s<td>%s</td></tr>" % (
            row.location_id, _esc(row.name), _position_html(row), _esc(row.timezone),
            _esc(_used_by_text(row.used_by)), owner, _actions_html(row, view, "t")))


def _pair_label(label, value_html):
    return (
        '<span class="data-card__label">%s</span> '
        '<span class="data-card__value">%s</span>' % (_t(label), value_html))


def _card_row_html(row, view):
    owner = (
        '<div class="data-card__secondary">%s</div>' % _pair_label(
            _COL_OWNER, _esc(_owner_text(row))) if view.is_admin else "")
    return (
        '<li class="data-card" data-location="%d">'
        '<div class="data-card__primary"><span>%s</span></div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>%s'
        '<div class="data-card__action">%s</div></li>' % (
            row.location_id, _esc(row.name),
            _pair_label(_COL_POSITION, _position_html(row)),
            _pair_label(_COL_TIMEZONE, _esc(row.timezone)),
            _pair_label(_COL_USED_BY, _esc(_used_by_text(row.used_by))), owner,
            _actions_html(row, view, "c")))


def _table_html(view):
    labels = [_COL_NAME, _COL_POSITION, _COL_TIMEZONE, _COL_USED_BY]
    if view.is_admin:
        labels.append(_COL_OWNER)
    labels.append(_COL_ACTIONS)
    heads = "".join("<th>%s</th>" % _t(label) for label in labels)
    body = "".join(_table_row_html(row, view) for row in view.rows)
    cards = "".join(_card_row_html(row, view) for row in view.rows)
    # The cards come first: style.css hides the table behind
    # `.data-cards ~ .data-table-wrap` below 960px by sibling order.
    return (
        '<ul class="data-cards">%s</ul>'
        '<div class="data-table-wrap"><table class="data-table data-table--locations">'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (cards, heads, body))


def _count_html(count):
    text = i18n.t(_COUNT_ONE) if count == 1 else i18n.t(_COUNT_MANY) % count
    return '<p class="filter-bar__count" role="status">%s</p>' % _esc(text)


def _card(heading_id, heading, inner_html):
    return (
        '<section class="page-section page-section--nested" '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s</section>'
        % (heading_id, heading_id, _t(heading), inner_html))


def _list_card(view):
    if not view.rows:
        body = _ui().empty_state(
            i18n.t(_EMPTY_HEADING), i18n.t(_EMPTY_ADMIN if view.is_admin else _EMPTY_USER))
    else:
        body = _count_html(len(view.rows)) + _table_html(view)
    return _card("locations-list", _LOCATIONS_TEXT, body)


def _new_card(view):
    state = view.state
    if state is None or state.target_id is not None:
        state = FormState(None, "", "", "", DEFAULT_TIMEZONE, {})
    form = (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s%s'
        '<div class="update-actions"><button type="submit">%s</button></div></form>' % (
            _esc(_routes().LOCATIONS_ADD_ROUTE), _ui().csrf_field(),
            _fields_html("new", state, view.timezones, state.errors), _t(_ADD_SUBMIT)))
    return _card("locations-new", _NEW_TITLE, form)


def render(view):
    """The Locations page body (the shell supplies the header)."""
    return _list_card(view) + _new_card(view)


def picker_html(options, selected_id, form_id, section_attr):
    """The per-frame Location picker for the Display page.

    `options` is a sequence of (location_id, name) the viewer may choose and
    `selected_id` the frame's current location id or None. The select submits
    through the settings form `form_id`. A current location the viewer may not
    choose (assigned by an administrator) stays selected under a generic label,
    so saving the page unchanged never clears it and its name is not shown.
    With nothing to choose and nothing assigned the select is replaced by a
    note and a link to add a location.
    """
    heading = _t(_PICKER_LABEL)
    known = {location_id for location_id, _name in options}
    foreign = selected_id is not None and selected_id not in known
    if not options and not foreign:
        return (
            '<div class="theme-status" %s="%s"><h2 class="text-heading">%s</h2>'
            '<p class="text-label">%s</p>'
            '<a class="text-link" href="%s">%s</a></div>' % (
                section_attr, heading, heading, _t(_PICKER_NONE_CHOSEN),
                _esc(_routes().LOCATIONS_ROUTE), _t(_PICKER_ADD)))
    items = ['<option value=""%s>%s</option>' % (
        "" if selected_id is not None else " selected", _t(_PICKER_NONE_OPTION))]
    if foreign:
        items.append('<option value="%d" selected>%s</option>' % (
            selected_id, _t(_PICKER_ASSIGNED)))
    for location_id, name in options:
        items.append('<option value="%d"%s>%s</option>' % (
            location_id, " selected" if location_id == selected_id else "", _esc(name)))
    return (
        '<div class="theme-status" %s="%s"><h2 class="text-heading">%s</h2>'
        '<p><label for="location-picker">%s</label>'
        '<select id="location-picker" name="%s" form="%s">%s</select></p>'
        '<a class="text-link" href="%s">%s</a></div>' % (
            section_attr, heading, heading, heading, LOCATION_FIELD, _esc(form_id),
            "".join(items), _esc(_routes().LOCATIONS_ROUTE), _t(_PICKER_MANAGE)))
