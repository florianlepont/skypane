"""The wording that describes a device's saved detection setting.

One place builds the sentence, the frame-text rows and the legacy runway
pill, so the Detection page, the Display card and the Device card always
agree. Nothing here reads storage: callers pass the selection
(`server.detection.current_selection()`) and the name of the device's
usable location, if it has one.
"""
from companion import i18n
from companion.layout import escape_html
from server import airports, detection

SUMMARY_RUNWAY_VALUE = i18n.msg(
    "detection.summary_runway", "Runway %(runway)s at %(airport)s")
SUMMARY_RUNWAY_DETAIL = i18n.msg(
    "detection.summary_runway_detail", "Departures and arrivals, in both directions.")
SUMMARY_POSITION_VALUE = i18n.msg(
    "detection.summary_position", "Aircraft within %(radius)d km of %(location)s")
SUMMARY_POSITION_DETAIL = i18n.msg(
    "detection.summary_position_detail", "In the air, below 10,000 ft, lowest first.")
LEGACY_PILL = i18n.msg("detection.legacy_runway_pill", "Runway %(number)s")

LEGACY_PILL_NUMBER = {"3": "3", "06-24": "4", "02-20": "2"}
_LEGACY_BY_RUNWAY = {pair: key for key, pair in detection.LEGACY_RUNWAY_MAP.items()}


def display_id_for(icao, designator):
    """The id the frame text is built from: the legacy Orly id when the
    runway has one, else "ICAO:designator"."""
    legacy = _LEGACY_BY_RUNWAY.get((icao, designator))
    return legacy if legacy is not None else detection.runway_display_id(icao, designator)


def airport_label(airport):
    return "%s (%s)" % (airport.name, airport.iata or airport.icao)


def is_fail_safe(selection, location_name):
    """A position setting whose device has no usable location: the frame
    keeps following the default Orly runway."""
    return selection["mode"] == detection.POSITION_MODE and location_name is None


def summary_values(selection, location_name):
    """(value, detail, pill, tag, empty) texts for the saved setting. The
    pill is markup; the other four are plain text for the caller to escape."""
    if selection["mode"] == detection.POSITION_MODE and location_name is not None:
        display_id = detection.position_display_id(selection["radius_km"])
        value = i18n.t(SUMMARY_POSITION_VALUE) % {
            "radius": selection["radius_km"], "location": location_name}
        return (value, i18n.t(SUMMARY_POSITION_DETAIL), "",
                detection.tag_text(display_id), detection.empty_heading(display_id))
    if selection["mode"] == detection.POSITION_MODE:
        selection = detection.current_selection({})
    icao, designator = selection["airport"], selection["runway"]
    airport = airports.find_airport(icao)
    display_id = display_id_for(icao, designator)
    value = i18n.t(SUMMARY_RUNWAY_VALUE) % {
        "runway": designator, "airport": airport_label(airport)}
    number = LEGACY_PILL_NUMBER.get(display_id)
    pill = (
        '<span class="banner__pill">%s</span>' % escape_html(
            i18n.t(LEGACY_PILL) % {"number": number}) if number else "")
    return (value, i18n.t(SUMMARY_RUNWAY_DETAIL), pill,
            detection.tag_text(display_id), detection.empty_heading(display_id))
