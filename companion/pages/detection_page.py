"""The Detection page: what this frame follows. Runway mode picks an airport
by search and one of its runways; the saved setting is summarised at the top.

Everything works without scripts: searching and picking an airport are GET
navigations that carry their state in the URL and never change anything,
and one native POST form stores the choice. The server validates every
posted value against the committed airport catalogue.

Position mode picks one of the device owner's saved locations and a whole
kilometre radius; a small form below saves or edits those locations. Only
rounded coordinates are shown next to the choice that is sent to providers.

`render()` returns the body markup only: the summary, the mode form with its
panels, the dirty bar and the locations card.
"""
import collections
import unicodedata
from urllib.parse import parse_qs, urlencode

from companion import device_scope, i18n, layout, page_context, prefs
from companion.detection_summary import (
    LEGACY_PILL, LEGACY_PILL_NUMBER, airport_label as airport_label,
    display_id_for, summary_values)
from companion.layout import escape_html
from companion.pages import config_page
from companion.settings import quiet_hours
from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR, SELECTED_LABEL,
    _field_error_attrs, _field_error_html, _submitted_or_current)
from server import airports, detection

DETECTION_ROUTE = "/detection"

FORM_ID = "detection-form"
ACTION_FIELD = "action"
ACTION_SAVE_DETECTION = "save_detection"
ACTION_SAVE_LOCATION = "save_location"
LOCATION_FORM_ID = "location-form"
DEFAULT_RADIUS_KM = 9
MODE_RUNWAY = detection.RUNWAY_MODE
MODE_POSITION = detection.POSITION_MODE
MODES = (MODE_RUNWAY, MODE_POSITION)

QUERY_MAX_FIELDS = 20
QUERY_VALUE_CAP = 64
SEARCH_RESULT_LIMIT = airports.DEFAULT_SEARCH_LIMIT

FLASH_DETECTION_SAVED = "detection_saved"
FLASH_LOCATION_SAVED = "location_saved"

# What the page needs to know about the locations it may show: `rows` are
# the subject's own locations as dicts (id, name, latitude, longitude,
# timezone); `other_owner` is true when an admin acts for another user.
LocationScope = collections.namedtuple(
    "LocationScope",
    "rows other_owner device_location_id device_location_name",
    defaults=((), False, None, None))

PAGE_TITLE = i18n.msg("detection.detection", "Detection")
PAGE_PURPOSE = i18n.msg(
    "detection.page_purpose",
    "Choose which flights this frame shows: traffic on one runway, or aircraft "
    "around a location.")
BACK_LINK_TEXT = i18n.msg("detection.back_to_display", "Back to Display")

SUMMARY_TITLE = i18n.msg("detection.current_setting", "Current setting")
SUMMARY_FOLLOWING = i18n.msg("detection.following", "Following")
SUMMARY_TAG = i18n.msg("detection.text_on_the_frame", "Text on the frame")
SUMMARY_EMPTY = i18n.msg("detection.when_nothing_is_in_range", "When nothing is in range")
FAIL_SAFE_TOAST = i18n.msg(
    "detection.fail_safe_toast",
    "No usable location — the frame keeps following Orly runway 3 until you "
    "choose a location inside France.")
FLASH_DETECTION_SAVED_TEXT = i18n.msg(
    "detection.saved_flash",
    "Detection saved — the frame will use it at its next wake.")
FLASH_LOCATION_SAVED_TEXT = i18n.msg(
    "detection.location_saved_flash",
    "Location saved — you can now choose it above.")

MODE_TITLE = i18n.msg("detection.detection_mode", "Detection mode")
MODE_RUNWAY_LABEL = i18n.msg("detection.airport_and_runway", "Airport and runway")
MODE_POSITION_LABEL = i18n.msg("detection.around_a_location", "Around a location")

AIRPORT_TITLE = i18n.msg("detection.airport", "Airport")
SEARCH_LABEL = i18n.msg("detection.find_an_airport", "Find an airport")
SEARCH_HINT = i18n.msg(
    "detection.search_hint", "Search by ICAO code, IATA code, name or city.")
SEARCH_LANDMARK = i18n.msg("detection.airports", "Airports")
SEARCH_BUTTON = i18n.msg("detection.search_airports", "Search airports")
COUNT_MANY = i18n.msg("detection.airports_found", "%(count)d airports found")
COUNT_ONE = i18n.msg("detection.one_airport_found", "1 airport found")
COUNT_NONE = i18n.msg("detection.no_airport_matches", "No airport matches “%(query)s”")
COUNT_CAPPED = i18n.msg(
    "detection.airports_capped",
    "Showing the first %(shown)d of %(total)d airports. Refine your search to "
    "narrow the list.")
NO_RESULT_HEADING = i18n.msg("detection.no_airport_found", "No airport found")
NO_RESULT_BODY = i18n.msg(
    "detection.no_airport_found_body",
    "Check the spelling, or try an ICAO code such as LFPG or an IATA code such as CDG.")
UNKNOWN_AIRPORT = i18n.msg(
    "detection.unknown_airport", "This airport is not in the catalogue.")
SELECTED_AIRPORT = i18n.msg("detection.selected_airport", "Selected airport")
CHANGE_AIRPORT = i18n.msg("detection.change_airport", "Change airport")

RUNWAY_TITLE = i18n.msg("detection.runway", "Runway")
RUNWAY_CAPTION = i18n.msg(
    "detection.runway_caption",
    "The frame follows departures and arrivals in both directions.")
RUNWAY_BEARING = i18n.msg(
    "detection.runway_bearing", "Bearing %(a)s° / %(b)s° (true)")
SURFACES = {
    "asphalt": i18n.msg("detection.surface_asphalt", "Asphalt"),
    "concrete": i18n.msg("detection.surface_concrete", "Concrete"),
    "grass": i18n.msg("detection.surface_grass", "Grass"),
    "gravel": i18n.msg("detection.surface_gravel", "Gravel"),
}
TAG_HINT = i18n.msg(
    "detection.frame_tag_hint",
    "The frame labels this airport “%(code)s”, then the runway, for example "
    "%(example)s.")

POSITION_TITLE = i18n.msg("detection.location", "Location")
POSITION_CAPTION = i18n.msg(
    "detection.location_caption",
    "The frame shows the lowest aircraft that is in the air, below 10,000 ft, "
    "inside the radius.")

LOCATION_LABEL = i18n.msg("detection.location_label", "Location")
LOCATION_OPTION = i18n.msg("detection.location_option", "%(name)s — %(lat)s, %(lon)s")
LOCATION_OPTION_OUTSIDE = i18n.msg(
    "detection.location_option_outside", "%(name)s — outside France")
ROUNDING_NOTE = i18n.msg(
    "detection.rounding_note", "Shared with data providers rounded to about 1 km.")
RADIUS_LABEL = i18n.msg("detection.radius_label", "Radius (kilometres)")
RADIUS_HINT = i18n.msg("detection.radius_hint", "From 4 to 28 km.")
NO_LOCATION_HEADING = i18n.msg("detection.no_location_heading", "No location yet")
NO_LOCATION_BODY = i18n.msg(
    "detection.no_location_body",
    "Add a location below, then choose it above to follow the aircraft around it.")
ADD_LOCATION = i18n.msg("detection.add_location", "Add a location")
LOCATIONS_TITLE = i18n.msg("detection.locations_title", "Your locations")
LOCATIONS_CAPTION = i18n.msg(
    "detection.locations_caption", "Locations you save here can be used by your frames.")
LOCATIONS_TITLE_OWNER = i18n.msg(
    "detection.locations_title_owner", "Locations of this frame’s owner")
LOCATIONS_CAPTION_OWNER = i18n.msg(
    "detection.locations_caption_owner",
    "You are saving locations for this frame’s owner.")
EDIT_LOCATION = i18n.msg("detection.edit_location", "Edit location")
EDIT_LOCATION_NAMED = i18n.msg("detection.edit_location_named", "Edit location %(name)s")
EDIT_LOCATION_SUMMARY = i18n.msg(
    "detection.edit_location_summary", "Edit location details")
FIELD_NAME = i18n.msg("detection.field_name", "Name")
FIELD_LATITUDE = i18n.msg("detection.field_latitude", "Latitude")
FIELD_LONGITUDE = i18n.msg("detection.field_longitude", "Longitude")
LATITUDE_HINT = i18n.msg(
    "detection.latitude_hint", "Decimal degrees, for example 48.8566.")
LONGITUDE_HINT = i18n.msg(
    "detection.longitude_hint", "Decimal degrees, for example 2.3522.")
SAVE_LOCATION = i18n.msg("detection.save_location", "Save location")
CANCEL_LOCATION = i18n.msg("detection.cancel_location", "Cancel location")

ERROR_MODE = i18n.msg("detection.error_mode", "Choose a detection mode.")
ERROR_AIRPORT = i18n.msg("detection.error_airport", "Choose an airport.")
ERROR_RUNWAY_MISSING = i18n.msg("detection.error_runway_missing", "Choose a runway.")
ERROR_RUNWAY_UNKNOWN = i18n.msg(
    "detection.error_runway_unknown",
    "This runway does not exist at this airport. Choose one from the list.")

ERROR_LOCATION_MISSING = i18n.msg(
    "detection.error_location_missing", "Choose a location.")
ERROR_LOCATION_UNAVAILABLE = i18n.msg(
    "detection.error_location_unavailable",
    "This location is not available. Choose one from the list.")
ERROR_LOCATION_OUTSIDE = i18n.msg(
    "detection.error_location_outside",
    "This location is outside metropolitan France. Choose a location in France.")
ERROR_RADIUS = i18n.msg(
    "detection.error_radius", "Enter a whole number of kilometres from 4 to 28.")
ERROR_NAME = i18n.msg(
    "detection.error_name", "Enter a name of up to 60 characters.")
ERROR_NUMBER = i18n.msg(
    "detection.error_number", "Enter a number such as 48.8566.")
ERROR_TIMEZONE = i18n.msg(
    "detection.error_timezone", "Choose a time zone from the list.")

_RESULTS_ANCHOR = "airport-results"
_RUNWAYS_ANCHOR = "airport-runways"
_COUNT_ID = "airport-results-count"
_MODE_HEADING_ID = "detection-mode-heading"
_MODE_ERROR_FIELD = "mode"


def clean_text(value, cap):
    """`value` without control characters, at most `cap` characters; never
    raises, a non-string reads as empty."""
    if not isinstance(value, str):
        return ""
    kept = "".join(c for c in value if unicodedata.category(c) != "Cc")
    return kept[:cap]


def parse_query(raw):
    """First value of each query field, control characters removed and
    length capped; a malformed or oversized query reads as empty."""
    try:
        parsed = parse_qs(raw or "", keep_blank_values=True, max_num_fields=QUERY_MAX_FIELDS)
    except ValueError:
        return {}
    cap = max(QUERY_VALUE_CAP, airports.MAX_QUERY_CHARS)
    return {key[:32]: clean_text(values[0], cap) for key, values in parsed.items() if values}


def _digits(value, cap):
    text = clean_text(value, cap)
    return text if text.isascii() and text.isdigit() else ""


def _detection_href(**fields):
    """The scoped page URL with the given non-empty query fields."""
    pairs = [(key, value) for key, value in fields.items() if value]
    query = "?" + urlencode(pairs) if pairs else ""
    return device_scope.scoped(DETECTION_ROUTE) + query


def format_count(number, lang):
    """A thousands-grouped integer: comma in English, no-break space in French."""
    grouped = "{:,}".format(number)
    return grouped.replace(",", " ") if lang == "fr" else grouped


def airport_codes(airport):
    """"LFPG · CDG · Roissy-en-France", the IATA segment omitted when empty."""
    parts = [airport.icao]
    if airport.iata:
        parts.append(airport.iata)
    parts.append(airport.municipality)
    return " · ".join(parts)


class _View:
    """What one render shows: the saved setting, the requested mode and
    airport, the search term and the position controls' values. Built once
    per request."""

    def __init__(self, ctx, query, submitted, location_name, scope):
        self.query = query or {}
        action = submitted.get("action") if submitted is not None else None
        self.submitted = submitted if action != ACTION_SAVE_LOCATION else None
        self.location_post = submitted if action == ACTION_SAVE_LOCATION else None
        self.lang = prefs.current_lang()
        self.selection = detection.current_selection(ctx.device_config)
        saved_mode = self.selection["mode"]
        self.scope = scope
        self.locations = list(scope.rows)
        if location_name is None:
            location_name = scope.device_location_name
        self.location_name = location_name
        self.fail_safe = saved_mode == MODE_POSITION and location_name is None
        requested = _submitted_or_current(
            self.submitted, "mode", self.query.get("mode"))
        self.mode_from_request = requested in MODES
        self.mode = requested if self.mode_from_request else saved_mode
        self.q = clean_text(self.query.get("q"), airports.MAX_QUERY_CHARS).strip()
        self.saved_airport = self.selection.get("airport")
        self.saved_runway = self.selection.get("runway")
        self.airport_code = self._requested_airport()
        self.default_location = self._default_location()
        self.radius_value = self._radius_value()
        self.location_value = self._location_value()
        self.carried_dirty = self._carried_dirty(saved_mode)

    def _requested_airport(self):
        if self.submitted is not None:
            return clean_text(self.submitted.get("airport"), 8)
        if "airport" in self.query:
            return clean_text(self.query["airport"], 8)
        if not self.q and self.saved_airport:
            return self.saved_airport
        return ""

    def _default_location(self):
        """The location the select shows when nothing else is requested: the
        device's own when it is listed and usable, else the first usable."""
        usable = [row["id"] for row in self.locations if location_usable(row)]
        if self.scope.device_location_id in usable:
            return self.scope.device_location_id
        return usable[0] if usable else None

    def _radius_value(self):
        if self.submitted is not None and "radius_km" in self.submitted:
            return self.submitted["radius_km"]
        carried = _digits(self.query.get("radius_km"), 3)
        return carried or str(self.selection.get("radius_km") or DEFAULT_RADIUS_KM)

    def _location_value(self):
        if self.submitted is not None and "location_id" in self.submitted:
            raw = _digits(self.submitted["location_id"], 9)
        else:
            raw = _digits(self.query.get("location_id"), 9)
        ids = [row["id"] for row in self.locations]
        if raw and int(raw) in ids:
            return int(raw)
        return self.default_location

    def _carried_dirty(self, saved_mode):
        """Whether unsaved values arrived with the page: a rejected save, or
        a mode, radius or location in the URL that differs from what is
        stored."""
        if self.submitted is not None:
            return True
        if self.mode_from_request and self.mode != saved_mode:
            return True
        radius = _digits(self.query.get("radius_km"), 3)
        stored_radius = str(self.selection.get("radius_km") or DEFAULT_RADIUS_KM)
        if radius and radius != stored_radius:
            return True
        location = _digits(self.query.get("location_id"), 9)
        return bool(location) and self.location_value != self.default_location

    def carried(self):
        """Query fields the page-local navigations pass along unchanged."""
        return {
            "radius_km": _digits(self.radius_value, 3) if self.locations else "",
            "location_id": (
                str(self.location_value) if self.location_value is not None else ""),
        }


def location_usable(row):
    """Whether a stored location lies in the supported area once rounded."""
    return detection.inside_france(row["latitude"], row["longitude"])


def coordinate_text(value):
    """A stored coordinate as the owner entered it: up to six decimals, no
    trailing zeros."""
    text = ("%.6f" % value).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def summary_card_html(view):
    value, detail, pill, tag, empty = summary_values(view.selection, view.location_name)
    return (
        '<div class="theme-status">'
        '<h2 class="text-heading">%s</h2>'
        '<dl class="detection-summary">'
        "<div><dt>%s</dt><dd>%s %s"
        '<span class="detection-summary__detail text-label section-caption">%s</span></dd></div>'
        '<div><dt>%s</dt><dd><code class="detection-tag" lang="en">%s</code></dd></div>'
        '<div><dt>%s</dt><dd><code class="detection-tag" lang="en">%s</code></dd></div>'
        "</dl></div>"
    ) % (
        escape_html(i18n.t(SUMMARY_TITLE)),
        escape_html(i18n.t(SUMMARY_FOLLOWING)), escape_html(value), pill,
        escape_html(detail),
        escape_html(i18n.t(SUMMARY_TAG)), escape_html(tag),
        escape_html(i18n.t(SUMMARY_EMPTY)), escape_html(empty),
    )


def fail_safe_toast_html(view):
    """The docked warning above the form when a position setting has no
    usable location; empty otherwise."""
    if not view.fail_safe:
        return ""
    title, detail = layout.split_toast_message(i18n.t(FAIL_SAFE_TOAST))
    return layout.toast_html(
        title, detail, tone=layout.TOAST_TONE_WARNING, role="status", docked=True)


def _mode_radio_html(mode, label, checked):
    radio_id = "detection-mode-%s" % mode
    return (
        '<input type="radio" name="mode" id="%s" value="%s" class="visually-hidden" '
        'form="%s"%s><label for="%s">%s</label>'
    ) % (
        radio_id, mode, FORM_ID, " checked" if checked else "", radio_id,
        escape_html(i18n.t(label)))


def mode_form_html(view, errors):
    """The POST form, holding the mode card; every other control reaches it
    through its `form` attribute."""
    radios = (
        _mode_radio_html(MODE_RUNWAY, MODE_RUNWAY_LABEL, view.mode == MODE_RUNWAY)
        + _mode_radio_html(MODE_POSITION, MODE_POSITION_LABEL, view.mode == MODE_POSITION))
    return (
        '<form method="post" id="%s" action="%s" data-dirty-form novalidate>'
        '<input type="hidden" name="%s" value="%s">'
        '<div class="theme-status detection-mode">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<div role="radiogroup" aria-labelledby="%s"><div class="theme-form">%s</div></div>'
        "%s</div></form>"
    ) % (
        FORM_ID, escape_html(device_scope.scoped(DETECTION_ROUTE, "POST")),
        ACTION_FIELD, ACTION_SAVE_DETECTION,
        _MODE_HEADING_ID, escape_html(i18n.t(MODE_TITLE)), _MODE_HEADING_ID, radios,
        _field_error_html(errors, _MODE_ERROR_FIELD, "detection-mode"))


def _result_row_html(view, airport):
    href = _detection_href(
        airport=airport.icao, mode=MODE_RUNWAY, q=view.q, **view.carried())
    current = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if airport.icao == view.saved_airport else "")
    return (
        '<li><a class="detection-result" href="%s#%s" data-detection-nav>'
        '<span class="detection-result__text">'
        '<span class="detection-result__name">%s</span>'
        '<span class="detection-result__codes text-label"%s>%s</span></span>%s</a></li>'
    ) % (
        escape_html(href), _RUNWAYS_ANCHOR, escape_html(airport.name), current,
        escape_html(airport_codes(airport)), layout.icon_html("icon-chevron-right", 16))


def _count_text(view, found, total):
    if not view.q:
        return ""
    if total == 0:
        return i18n.t(COUNT_NONE) % {"query": view.q}
    if total > len(found):
        return i18n.t(COUNT_CAPPED) % {"shown": len(found), "total": total}
    if total == 1:
        return i18n.t(COUNT_ONE)
    return i18n.t(COUNT_MANY) % {"count": total}


def results_html(view):
    """The live count region, always present, plus the list or the empty
    state when a search term was submitted."""
    found, total = airports.search_airports(view.q, SEARCH_RESULT_LIMIT)
    count = _count_text(view, found, total)
    count_html = (
        '<p id="%s" class="text-label" role="status" aria-live="polite" '
        'aria-atomic="true">%s</p>') % (_COUNT_ID, escape_html(count))
    if view.q and not found:
        return count_html + layout.empty_state(
            i18n.t(NO_RESULT_HEADING), i18n.t(NO_RESULT_BODY), compact=True)
    if not found:
        return count_html
    rows = "".join(_result_row_html(view, airport) for airport in found)
    return '%s<ul class="detection-results" aria-labelledby="%s">%s</ul>' % (
        count_html, _COUNT_ID, rows)


def search_form_html(view):
    hidden = {"mode": MODE_RUNWAY, **view.carried()}
    hidden_html = "".join(
        '<input type="hidden" name="%s" value="%s">' % (name, escape_html(value))
        for name, value in hidden.items() if value)
    return (
        '<form method="get" action="%s#%s" role="search" aria-label="%s" data-detection-nav>'
        "%s"
        '<label for="airport-q" class="text-label">%s</label>'
        '<div class="filter-bar"><div class="filter-bar__search">'
        '<input type="search" id="airport-q" name="q" value="%s" autocomplete="off" '
        'autocapitalize="off" spellcheck="false" enterkeyhint="search" maxlength="%d" '
        'placeholder="LFPG, CDG, Nice…" aria-describedby="airport-search-hint">%s</div>'
        '<button type="submit" class="detection-search">%s</button></div>'
        '<p id="airport-search-hint" class="text-label section-caption">%s</p></form>'
    ) % (
        escape_html(device_scope.scoped(DETECTION_ROUTE)), _RESULTS_ANCHOR,
        escape_html(i18n.t(SEARCH_LANDMARK)), hidden_html,
        escape_html(i18n.t(SEARCH_LABEL)), escape_html(view.q),
        airports.MAX_QUERY_CHARS, layout.icon_html("icon-search", 20),
        escape_html(i18n.t(SEARCH_BUTTON)), escape_html(i18n.t(SEARCH_HINT)))


def _bearing_text(runway):
    forward = round(runway.bearing_deg) % 360
    return i18n.t(RUNWAY_BEARING) % {
        "a": "%03d" % forward, "b": "%03d" % ((forward + 180) % 360)}


def _length_surface_text(runway, lang):
    text = "%s m" % format_count(runway.length_m, lang)
    surface = SURFACES.get(runway.surface or "")
    if surface is not None:
        text += " · " + i18n.t(surface)
    return text


def _runway_card_html(view, airport, runway, checked, current):
    display_id = display_id_for(airport.icao, runway.designator)
    number = LEGACY_PILL_NUMBER.get(display_id)
    pill = (
        ' <span class="banner__pill">%s</span>' % escape_html(
            i18n.t(LEGACY_PILL) % {"number": number}) if number else "")
    classes = "runway-card runway-card--selected" if current else "runway-card"
    badge = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if current else "")
    return (
        '<label class="%s"%s>'
        '<input type="radio" name="runway" value="%s" class="visually-hidden" form="%s"%s>'
        '<span class="runway-card__number">%s%s</span>'
        '<span class="runway-card__detail text-label section-caption">%s</span>'
        '<span class="runway-card__detail text-label section-caption">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        classes, badge, escape_html(runway.designator), FORM_ID,
        " checked" if checked else "",
        escape_html(runway.designator), pill,
        escape_html(_bearing_text(runway)),
        escape_html(_length_surface_text(runway, view.lang)),
        layout.icon_html("icon-check"), escape_html(i18n.t(SELECTED_LABEL)))


def _preselected_runway(view, airport):
    if view.submitted is not None:
        return view.submitted.get("runway")
    if airport.icao == view.saved_airport:
        return view.saved_runway
    if len(airport.runways) == 1:
        return airport.runways[0].designator
    return None


def runway_group_html(view, airport, errors):
    """The chosen airport line and one radio card per runway."""
    picked = _preselected_runway(view, airport)
    cards = "".join(
        _runway_card_html(
            view, airport, runway, runway.designator == picked,
            airport.icao == view.saved_airport and runway.designator == view.saved_runway)
        for runway in airport.runways)
    first_id = display_id_for(airport.icao, airport.runways[0].designator)
    hint = i18n.t(TAG_HINT) % {
        "code": airport.iata or airport.icao, "example": detection.tag_text(first_id)}
    change_href = _detection_href(mode=MODE_RUNWAY, q=view.q, **view.carried())
    return (
        '<div id="%s" class="detection-airport">'
        '<p class="text-label section-caption">%s</p>'
        '<p><span class="detection-airport__name">%s</span> '
        '<span class="text-label section-caption">%s</span></p>'
        '<a class="text-link detection-link" href="%s#%s" data-detection-nav>%s</a></div>'
        '<h2 class="text-heading" id="runway-group-heading">%s</h2>'
        '<p class="text-label section-caption" id="runway-caption">%s</p>'
        '<div class="runway-row detection-runways" role="radiogroup" '
        'aria-labelledby="runway-group-heading" aria-describedby="runway-caption">%s</div>'
        "%s"
        '<input type="hidden" name="airport" value="%s" form="%s">'
        '<p class="text-label section-caption">%s</p>'
    ) % (
        _RUNWAYS_ANCHOR, escape_html(i18n.t(SELECTED_AIRPORT)),
        escape_html(airport.name), escape_html(airport_codes(airport)),
        escape_html(change_href), _RESULTS_ANCHOR, escape_html(i18n.t(CHANGE_AIRPORT)),
        escape_html(i18n.t(RUNWAY_TITLE)), escape_html(i18n.t(RUNWAY_CAPTION)), cards,
        _field_error_html(errors, "runway", "runway"),
        escape_html(airport.icao), FORM_ID, escape_html(hint))


def _chosen_airport_html(view, errors):
    code = view.airport_code
    if not code:
        return _field_error_html(errors, "airport", "airport")
    airport = airports.find_airport(code)
    if airport is None:
        return (
            layout.empty_state(i18n.t(UNKNOWN_AIRPORT), i18n.t(NO_RESULT_BODY), compact=True)
            + _field_error_html(errors, "airport", "airport"))
    return runway_group_html(view, airport, errors)


def _panel_attrs(view, mode):
    """Class and, after a server round trip, the `hidden` attribute of the
    inactive panel (a browser without :has() then shows one panel)."""
    hidden = " hidden" if view.mode_from_request and view.mode != mode else ""
    return 'class="detection-panel detection-panel--%s"%s' % (mode, hidden)


def airport_panel_html(view, errors):
    return (
        "<section %s>"
        '<div class="theme-status">'
        '<h2 class="text-heading">%s</h2>%s%s%s</div></section>'
    ) % (
        _panel_attrs(view, MODE_RUNWAY), escape_html(i18n.t(AIRPORT_TITLE)),
        search_form_html(view), results_html(view), _chosen_airport_html(view, errors))


def _location_option_html(view, row):
    lat = detection.round_coordinate(row["latitude"])
    lon = detection.round_coordinate(row["longitude"])
    usable = location_usable(row)
    if usable:
        text = i18n.t(LOCATION_OPTION) % {
            "name": row["name"], "lat": "%.2f" % lat, "lon": "%.2f" % lon}
    else:
        text = i18n.t(LOCATION_OPTION_OUTSIDE) % {"name": row["name"]}
    selected = " selected" if usable and row["id"] == view.location_value else ""
    return '<option value="%d"%s%s>%s</option>' % (
        row["id"], selected, "" if usable else " disabled", escape_html(text))


def location_select_html(view, errors):
    options = "".join(_location_option_html(view, row) for row in view.locations)
    return (
        '<label for="detection-location">%s</label>'
        '<select id="detection-location" name="location_id" form="%s"%s>%s</select>'
        '%s<p id="location-rounding-note" class="text-label section-caption">%s</p>'
    ) % (
        escape_html(i18n.t(LOCATION_LABEL)), FORM_ID,
        _field_error_attrs(
            errors, "location_id", "detection-location", "location-rounding-note"),
        options, _field_error_html(errors, "location_id", "detection-location"),
        escape_html(i18n.t(ROUNDING_NOTE)))


def radius_field_html(view, errors):
    return (
        '<label for="detection-radius">%s</label>'
        '<input type="number" id="detection-radius" name="radius_km" form="%s" '
        'min="%d" max="%d" step="1" inputmode="numeric" value="%s"%s>'
        '<span class="text-label field-inline-value" aria-hidden="true">km</span>'
        '<p id="radius-hint" class="text-label section-caption">%s</p>%s'
    ) % (
        escape_html(i18n.t(RADIUS_LABEL)), FORM_ID, detection.RADIUS_KM_MIN,
        detection.RADIUS_KM_MAX, escape_html(view.radius_value),
        _field_error_attrs(errors, "radius_km", "detection-radius", "radius-hint"),
        escape_html(i18n.t(RADIUS_HINT)),
        _field_error_html(errors, "radius_km", "detection-radius"))


def _add_location_link():
    return '<a class="text-link detection-link" href="%s#%s">%s</a>' % (
        escape_html(_detection_href(new_location="1")), LOCATION_FORM_ID,
        escape_html(i18n.t(ADD_LOCATION)))


def position_panel_html(view, errors):
    """Location select and radius, or the empty state when the subject has
    no saved location (then no radius field exists to post)."""
    if view.locations:
        controls = location_select_html(view, errors) + radius_field_html(view, errors)
    else:
        controls = (
            layout.empty_state(
                i18n.t(NO_LOCATION_HEADING), i18n.t(NO_LOCATION_BODY), compact=True)
            + _field_error_html(errors, "location_id", "detection-location")
            + _add_location_link())
    return (
        "<section %s>"
        '<div class="theme-status"><h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>%s</div></section>'
    ) % (
        _panel_attrs(view, MODE_POSITION), escape_html(i18n.t(POSITION_TITLE)),
        escape_html(i18n.t(POSITION_CAPTION)), controls)


def _location_row_html(row):
    lat, lon = coordinate_text(row["latitude"]), coordinate_text(row["longitude"])
    zone = quiet_hours.timezone_label_text(row["timezone"])
    name = i18n.t(EDIT_LOCATION_NAMED) % {"name": row["name"]}
    href = _detection_href(location=str(row["id"]))
    return (
        "<li>"
        '<span class="detection-locations__name">%s</span>'
        '<span class="text-label section-caption"><code class="detection-tag">%s, %s</code>'
        " · %s</span>"
        '<a class="text-link detection-link" href="%s#%s" aria-label="%s">%s</a></li>'
    ) % (
        escape_html(row["name"]), escape_html(lat), escape_html(lon), escape_html(zone),
        escape_html(href), LOCATION_FORM_ID, escape_html(name),
        escape_html(i18n.t(EDIT_LOCATION)))


def _location_form_state(view):
    """(open, location id text, field values) for the location form: the
    rejected post echoed, else the row being edited, else blank."""
    post = view.location_post
    if post is not None:
        values = {key: post.get(key, "") for key in (
            "location_name", "latitude", "longitude", "timezone")}
        return True, post.get("location_id", ""), values
    edit_id = _digits(view.query.get("location"), 9)
    for row in view.locations:
        if edit_id and row["id"] == int(edit_id):
            values = {
                "location_name": row["name"],
                "latitude": coordinate_text(row["latitude"]),
                "longitude": coordinate_text(row["longitude"]),
                "timezone": row["timezone"]}
            return True, str(row["id"]), values
    blank = {"location_name": "", "latitude": "", "longitude": "",
             "timezone": quiet_hours.CURATED_TIMEZONES[0][0]}
    return view.query.get("new_location") == "1", "", blank


def _text_field_html(errors, field, control_id, label, value, extra, hint=None):
    hint_html = (
        '<p id="%s-hint" class="text-label section-caption">%s</p>' % (
            control_id, escape_html(i18n.t(hint))) if hint else "")
    return (
        '<label for="%s">%s</label>'
        '<input type="text" id="%s" name="%s" value="%s" required autocomplete="off" %s%s>'
        "%s%s"
    ) % (
        control_id, escape_html(i18n.t(label)), control_id, field, escape_html(value),
        extra, _field_error_attrs(errors, field, control_id, hint and control_id + "-hint"),
        hint_html, _field_error_html(errors, field, control_id))


def location_form_html(view, errors):
    is_open, location_id, values = _location_form_state(view)
    zone_key, zone_msg = quiet_hours.CURATED_TIMEZONES[0]
    summary = EDIT_LOCATION_SUMMARY if location_id else ADD_LOCATION
    return (
        '<details id="%s" class="detection-location-form"%s>'
        "<summary>%s</summary>"
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="location_id" value="%s">'
        "%s%s%s"
        '<label for="location-timezone">%s</label>'
        '<select id="location-timezone" name="timezone"%s>'
        '<option value="%s" selected>%s</option></select>%s'
        '<button type="submit" class="detection-location-save">%s</button> '
        '<a class="text-link detection-link" href="%s">%s</a>'
        "</form></details>"
    ) % (
        LOCATION_FORM_ID, " open" if is_open else "",
        escape_html(i18n.t(summary)),
        escape_html(device_scope.scoped(DETECTION_ROUTE, "POST")),
        ACTION_FIELD, ACTION_SAVE_LOCATION, escape_html(location_id),
        _field_error_html(errors, "location_form", "location-form-top"),
        _text_field_html(
            errors, "location_name", "location-name", FIELD_NAME,
            values["location_name"], 'maxlength="60"'),
        _text_field_html(
            errors, "latitude", "location-latitude", FIELD_LATITUDE,
            values["latitude"], 'inputmode="decimal"', LATITUDE_HINT)
        + _text_field_html(
            errors, "longitude", "location-longitude", FIELD_LONGITUDE,
            values["longitude"], 'inputmode="decimal"', LONGITUDE_HINT),
        escape_html(i18n.t(quiet_hours.TIMEZONE_LABEL)),
        _field_error_attrs(errors, "timezone", "location-timezone"),
        escape_html(zone_key), escape_html(i18n.t(zone_msg)),
        _field_error_html(errors, "timezone", "location-timezone"),
        escape_html(i18n.t(SAVE_LOCATION)),
        escape_html(device_scope.scoped(DETECTION_ROUTE)),
        escape_html(i18n.t(CANCEL_LOCATION)))


def locations_card_html(view, errors):
    owner = view.scope.other_owner
    title = LOCATIONS_TITLE_OWNER if owner else LOCATIONS_TITLE
    caption = LOCATIONS_CAPTION_OWNER if owner else LOCATIONS_CAPTION
    if view.locations:
        listing = '<ul class="detection-locations">%s</ul>' % "".join(
            _location_row_html(row) for row in view.locations)
    else:
        listing = layout.empty_state(
            i18n.t(NO_LOCATION_HEADING), i18n.t(NO_LOCATION_BODY), compact=True)
    return (
        '<div class="theme-status"><h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>%s%s</div>'
    ) % (
        escape_html(i18n.t(title)), escape_html(i18n.t(caption)), listing,
        location_form_html(view, errors))


def dirty_bar_html(carried_href=None):
    """The unsaved-changes bar: visible in the markup so Save works with
    scripts blocked, hidden at init by dirty-state.js. `carried_href` marks
    a bar rendered for unsaved values that came with the page; it is where
    Cancel returns to the stored setting."""
    strings = config_page._dirty_bar_strings()
    carried = (
        ' data-dirty-carried="%s"' % escape_html(carried_href)
        if carried_href is not None else "")
    return (
        '<div class="dirty-bar" data-dirty-bar%s role="status" '
        'data-dirty-changed-suffix="%s" data-dirty-and="%s" data-dirty-list-and="%s" '
        'data-dirty-unsaved-singular="%s" data-dirty-unsaved-plural="%s" '
        'data-dirty-saving="%s" data-dirty-initial-text="%s">'
        "<span data-dirty-count></span>"
        '<button type="submit" class="dirty-bar__save" form="%s" %s>%s</button>'
        '<button type="reset" form="%s" class="dirty-bar__cancel" data-dirty-cancel>%s</button>'
        "</div>"
    ) % (
        carried, strings["changed_suffix"], strings["and_word"], strings["list_and"],
        strings["unsaved_singular"], strings["unsaved_plural"], strings["saving"],
        strings["initial_text"], FORM_ID, config_page.STATIC_SAVE_FALLBACK_ATTR,
        escape_html(i18n.t(config_page.SAVE_BUTTON_TEXT)), FORM_ID,
        escape_html(i18n.t(config_page.CANCEL_BUTTON_TEXT)))


def render(ctx, query=None, errors=None, submitted=None, location_name=None, locations=None):
    """The Detection page body.

    `query` is `parse_query()`'s output for a GET; `errors`/`submitted`
    come together from a rejected POST and echo what was posted.
    `location_name` is the device's usable location, if it has one;
    `locations` is the LocationScope the signed-in user may choose from.
    """
    ctx = page_context.coerce(ctx)
    errors = errors or {}
    view = _View(ctx, query, submitted, location_name, locations or LocationScope())
    back = (
        '<a class="text-link detection-link" href="%s">%s</a>'
        % (escape_html(device_scope.scoped(layout.DISPLAY_ROUTE)),
           escape_html(i18n.t(BACK_LINK_TEXT))))
    plain_href = device_scope.scoped(DETECTION_ROUTE)
    return (
        layout.page_header(i18n.t(PAGE_TITLE), i18n.t(PAGE_PURPOSE))
        + back
        + fail_safe_toast_html(view)
        + summary_card_html(view)
        + '<div class="detection-modes" %s="%s">%s%s%s</div>' % (
            DIRTY_SECTION_ATTR, escape_html(i18n.t(PAGE_TITLE)),
            mode_form_html(view, errors), airport_panel_html(view, errors),
            position_panel_html(view, errors))
        + dirty_bar_html(plain_href if view.carried_dirty else None)
        + locations_card_html(view, errors)
    )
