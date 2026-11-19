"""The wording that describes a device's saved detection setting.

One place builds the sentence, the frame-text rows and the legacy runway
pill, so the Detection page, the Display card and the Device card always
agree. Nothing here reads storage: callers pass the selection
(`server.detection.current_selection()`) and the name of the device's
usable location, if it has one.
"""
from companion import i18n, prefs, ui_components
from companion.pages import detection_page
from server import airports, detection

SUMMARY_RUNWAY_VALUE = i18n.msg(
    "detection.summary_runway", "Runway %(runway)s at %(airport)s")
SUMMARY_RUNWAY_DETAIL = i18n.msg(
    "detection.summary_runway_detail", "Departures and arrivals, in both directions.")
SUMMARY_POSITION_VALUE = i18n.msg(
    "detection.summary_position", "Aircraft within %(radius)d km of %(location)s")
SUMMARY_POSITION_DETAIL = i18n.msg(
    "detection.summary_position_detail", "In the air, lowest first.")
LEGACY_PILL = i18n.msg("detection.legacy_runway_pill", "Runway %(number)s")

PILL_RUNWAY = i18n.msg("detection.pill_runway", "%(airport)s \u00b7 runway %(runway)s")
PILL_POSITION = i18n.msg("detection.pill_position", "%(location)s \u00b7 %(radius)d km radius")
PILL_NO_PLACE = i18n.msg("detection.pill_no_place", "No place set")

LEGACY_PILL_NUMBER = {"3": "3", "06-24": "4", "02-20": "2"}
_LEGACY_BY_RUNWAY = {pair: key for key, pair in detection.LEGACY_RUNWAY_MAP.items()}


def display_id_for(icao, designator):
    """The id the frame text is built from: the legacy Orly id when the
    runway has one, else "ICAO:designator"."""
    legacy = _LEGACY_BY_RUNWAY.get((icao, designator))
    return legacy if legacy is not None else detection.runway_display_id(icao, designator)


def airport_label(airport):
    return "%s (%s)" % (airport.name, airport.iata or airport.icao)


def coords_text(lat, lon):
    """Coordinates as one readout ("48.7262 N · 2.3652 E"), with the decimal
    comma in French."""
    def number(value):
        text = "%.4f" % abs(value)
        return text.replace(".", ",") if prefs.current_lang() == "fr" else text
    return "%s %s · %s %s" % (
        number(lat), "N" if lat >= 0 else "S", number(lon), "E" if lon >= 0 else "W")


def followed_text(device_cfg, place):
    """What the saved setting follows, for the sentence of the saved toast:
    the airport of a runway setting, or the area of a position setting named
    by the place's label (its coordinates when it has no label of its own).
    None when a position setting has no place."""
    selection = detection.current_selection(device_cfg)
    if selection["mode"] != detection.POSITION_MODE:
        airport = airports.find_airport(selection["airport"])
        return None if airport is None else airport.name
    if place is None:
        return None
    location = place["name"]
    if not location or location == detection_page.DEFAULT_PLACE_LABEL:
        location = coords_text(place["latitude"], place["longitude"])
    return i18n.t(detection_page.FLASH_AREA_TARGET) % {
        "radius": selection["radius_km"], "location": location}


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
        ui_components.pill_html(i18n.t(LEGACY_PILL) % {"number": number}) if number else "")
    return (value, i18n.t(SUMMARY_RUNWAY_DETAIL), pill,
            detection.tag_text(display_id), detection.empty_heading(display_id))


def home_place_text(device_cfg, place):
    """`(icon_id, text)` for Home's place pill: what the saved setting
    follows, in a few words. `place` is the frame's own position row (or
    None); a position setting without a usable place reads as unset, as the
    Detection page does."""
    selection = detection.current_selection(device_cfg)
    if selection["mode"] != detection.POSITION_MODE:
        return "icon-pin", _runway_pill_text(selection)
    inside = place is not None and detection.inside_france(
        place["latitude"], place["longitude"])
    if not inside:
        return "icon-warning", i18n.t(PILL_NO_PLACE)
    return "icon-locate", i18n.t(PILL_POSITION) % {
        "location": place["name"], "radius": selection["radius_km"]}


def _runway_pill_text(selection):
    """"ORY · runway 06/24": the airport's code and the runway number the
    frame follows (the short legacy number for an Orly runway)."""
    airport = airports.find_airport(selection["airport"])
    display_id = display_id_for(selection["airport"], selection["runway"])
    runway = LEGACY_PILL_NUMBER.get(display_id) or selection["runway"]
    return i18n.t(PILL_RUNWAY) % {
        "airport": (airport.iata or airport.icao) if airport else selection["airport"],
        "runway": runway}
