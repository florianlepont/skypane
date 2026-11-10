"""Shared parts of the Location and detection page: the route and form
constants, the messages the page and its POST handler use, the query-string
reader, and the save bar.

`companion/pages/place_page.py` renders the page; `companion/detection_actions.py`
validates what it posts. Everything on the page works without scripts:
choosing an airport is a GET navigation that carries its state in the URL and
changes nothing, and one native POST form stores the choice. The server
validates every posted value against the committed airport catalogue.
"""
import collections
import unicodedata
from urllib.parse import parse_qs

from companion import i18n, ui_save_bar
from server import airports, detection

DETECTION_ROUTE = "/detection"

FORM_ID = "detection-form"
ACTION_FIELD = "action"
ACTION_SAVE_DETECTION = "save_detection"
ACTION_SAVE_LOCATION = "save_location"
ACTION_SAVE_PLACE = "save_place"
DEFAULT_RADIUS_KM = 9
MODE_RUNWAY = detection.RUNWAY_MODE
MODE_POSITION = detection.POSITION_MODE
MODES = (MODE_RUNWAY, MODE_POSITION)

QUERY_MAX_FIELDS = 20
QUERY_VALUE_CAP = 64

FLASH_DETECTION_SAVED = "detection_saved"
FLASH_LOCATION_SAVED = "location_saved"
FLASH_PLACE_SAVED = "place_saved"

# What the POST handler needs to know about the locations it may use: `rows`
# are the subject's own locations as dicts (id, name, latitude, longitude,
# timezone); `other_owner` is true when the rows belong to another user (an
# admin acting for them, or a co-manager); `may_edit` is false when the
# viewer may only choose a location, not create or change one.
LocationScope = collections.namedtuple(
    "LocationScope",
    "rows other_owner device_location_id device_location_name may_edit",
    defaults=((), False, None, None, True))

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
FLASH_PLACE_SAVED_TEXT = i18n.msg(
    "detection.place_saved_flash",
    "Location saved — Detection now follows {place}.")
PLACE_FALLBACK_NAME = i18n.msg("detection.place_fallback_name", "the chosen place")

SECTION_DETECTION = i18n.msg("detection.detection", "Detection")

SEARCH_HINT = i18n.msg(
    "detection.search_hint", "Search by ICAO code, IATA code, name or city.")
SEARCH_BUTTON = i18n.msg("detection.search_airports", "Search airports")
COUNT_MANY = i18n.msg("detection.airports_found", "%(count)d airports found")
COUNT_ONE = i18n.msg("detection.one_airport_found", "1 airport found")
COUNT_NONE = i18n.msg("detection.no_airport_matches", "No airport matches “%(query)s”")
NO_RESULT_HEADING = i18n.msg("detection.no_airport_found", "No airport found")
NO_RESULT_BODY = i18n.msg(
    "detection.no_airport_found_body",
    "Check the spelling, or try an ICAO code such as LFPG or an IATA code such as CDG.")
UNKNOWN_AIRPORT = i18n.msg(
    "detection.unknown_airport", "This airport is not in the catalogue.")

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

FIELD_LATITUDE = i18n.msg("detection.field_latitude", "Latitude")
FIELD_LONGITUDE = i18n.msg("detection.field_longitude", "Longitude")
LATITUDE_HINT = i18n.msg(
    "detection.latitude_hint", "Decimal degrees, for example 48.8566.")
LONGITUDE_HINT = i18n.msg(
    "detection.longitude_hint", "Decimal degrees, for example 2.3522.")

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
    "detection.error_radius", "Enter a whole number of kilometres from 2 to 28.")
ERROR_NAME = i18n.msg(
    "detection.error_name", "Enter a name of up to 60 characters.")
ERROR_NUMBER = i18n.msg(
    "detection.error_number", "Enter a number such as 48.8566.")
ERROR_TIMEZONE = i18n.msg(
    "detection.error_timezone", "Choose a time zone from the list.")


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


def digits(value, cap):
    """`value` when it is 1 to `cap` ASCII digits, else an empty string."""
    text = clean_text(value, cap)
    return text if text.isascii() and text.isdigit() else ""


def format_count(number, lang):
    """A thousands-grouped integer: comma in English, no-break space in French."""
    grouped = "{:,}".format(number)
    return grouped.replace(",", "\u00a0") if lang == "fr" else grouped


def airport_codes(airport):
    """"LFPG · CDG · Roissy-en-France", the IATA segment omitted when empty."""
    parts = [airport.icao]
    if airport.iata:
        parts.append(airport.iata)
    parts.append(airport.municipality)
    return " · ".join(parts)


def location_usable(row):
    """Whether a stored location lies in the supported area once rounded."""
    return detection.inside_france(row["latitude"], row["longitude"])


def dirty_bar_html(carried_href=None):
    """The unsaved-changes bar of the page: visible in the markup so Save
    works with scripts blocked, hidden at init by dirty-state.js.
    `carried_href` marks a bar rendered for unsaved values that came with the
    page; it is where Cancel returns to the stored setting."""
    return ui_save_bar.save_bar_html(FORM_ID, carried_href=carried_href)
