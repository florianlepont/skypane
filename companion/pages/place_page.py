"""The Location and detection page: where the frame is and what it follows.

Top to bottom on a phone: the status card, the place card (the map's
container, the search form, the locate button and the explanation shown
while the map is not running), the French airports card, the What to follow
card, the details card and the save bar. The whole page is server-rendered
and complete without scripts and without any external network: choosing an
airport is a GET navigation (`?airport=`, `?q=`), the coordinates, label and
time zone are plain fields, and one native POST form stores them with
`action=save_place`.

Data contract for the map script (companion/static/place-map.js):
`div#place-map.place-map` carries `data-lat`, `data-lon` (empty when there is
no place), `data-zoom`, `data-mode`, `data-airport` and `data-radius-km`; each
airport row is an anchor with `data-icao`, `data-lat`, `data-lon` and
`data-name`; the controls keep the ids `place-lat`, `place-lon`,
`place-label`, `place-radius`, `place-timezone`, `place-mode-runway` and
`place-mode-area`, and `place-status` is the polite status line. The script
adds `map-ready` to the page element once the map runs; until then the
fallback explanation shows and the details card is open.
"""
import unicodedata
from urllib.parse import urlencode

from companion import device_scope, i18n, layout, page_context, prefs
from companion.detection_summary import (
    LEGACY_PILL, LEGACY_PILL_NUMBER, display_id_for, is_fail_safe, summary_values)
from companion.layout import escape_html
from companion.pages import detection_page as dp
from companion.settings import quiet_hours
from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR, SELECTED_LABEL,
    _field_error_attrs, _field_error_html)
from server import airports, detection

PAGE_TITLE = i18n.msg("nav.detection", "Location and detection")
PAGE_PURPOSE = i18n.msg(
    "detection.page_purpose",
    "Detection follows your place: choose an airport to follow a runway, or drop "
    "a pin to follow the area around it.")

PLACE_TITLE = i18n.msg("detection.title", "Place")
NO_SCRIPT_MAP = i18n.msg(
    "detection.no_script_map",
    "The map needs scripts and a network connection. You can still choose a place "
    "with the airport list or by typing coordinates.")
MAP_LABEL = i18n.msg(
    "detection.map_label", "Map. Use arrow keys to move, plus and minus to zoom.")
SEARCH_LABEL = i18n.msg("detection.search_label", "Search a city or address")
SEARCH_BUTTON = i18n.msg("detection.search_button", "Search places")
SEARCH_HELP = i18n.msg(
    "detection.search_help",
    "What you type is sent to OpenStreetMap’s search service (Nominatim).")
LOCATE_BUTTON = i18n.msg("detection.locate", "Use my position")
ABOUT_MAP = i18n.msg("detection.about_map", "About this map")
MAP_CREDITS = i18n.msg(
    "detection.map_credits",
    "Map data © OpenStreetMap contributors, ODbL. Map pictures from the "
    "OpenStreetMap tile server. Search by Nominatim.")
MAP_PRIVACY = i18n.msg(
    "detection.map_privacy",
    "Viewing the map asks OpenStreetMap’s servers for map pictures of the area "
    "you look at. Your frame’s saved position stays on SkyPane.")
REPORT_PROBLEM = i18n.msg("detection.report_problem", "Report a map problem")
COPYRIGHT_LINK = i18n.msg("detection.copyright_link", "OpenStreetMap copyright")

EMPTY_HEADING = i18n.msg("detection.empty_heading", "No place chosen yet")
EMPTY_BODY = i18n.msg(
    "detection.empty_body", "Pick an airport, search a place or tap the map, then save.")

AIRPORTS_TITLE = i18n.msg("detection.airports_title", "French airports")
FILTER_LABEL = i18n.msg("detection.filter_airports", "Filter airports")
FILTER_COUNT_TEMPLATE = i18n.msg("health.of_shown", "%d of %d shown")

FOLLOW_TITLE = i18n.msg("detection.follow_title", "What to follow")
MODE_RUNWAY_CARD = i18n.msg("detection.mode_runway", "A runway")
MODE_AREA_CARD = i18n.msg("detection.mode_area", "The area around the pin")
RUNWAY_LABEL = i18n.msg("detection.runway_label", "Runway to follow")
PICK_AIRPORT_NOTE = i18n.msg(
    "detection.pick_airport",
    "Pick an airport from the list to follow one of its runways.")
RADIUS_LABEL = i18n.msg("detection.radius_label", "Radius (km)")
RADIUS_HELP = i18n.msg(
    "detection.radius_help",
    "Planes near this spot are shown. 9 km is a good start.")

DETAILS_TITLE = i18n.msg("detection.details_title", "Coordinates and time zone")
PLACE_LABEL_FIELD = i18n.msg("detection.label_field", "Place label")
SECTION_PLACE = i18n.msg("detection.section_place", "Place")

# Field names the page has a control for; any other refusal (an older form's)
# is listed above the cards.
_PAGE_FIELDS = frozenset((
    "mode", "airport", "runway", "radius_km", "latitude", "longitude",
    "place_label", "timezone"))

OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
OSM_FIX_URL = "https://www.openstreetmap.org/fixthemap"
CATALOGUE_ZOOM = 13
PLACE_ZOOM = 12
FRANCE_ZOOM = 5


def _fold(text):
    """Lowercase, accents removed: the same fold the airport search uses."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def _coord(value):
    return "%.4f" % value


class _View:
    """What one render shows: the saved setting, the requested mode and
    airport, the search term and the values of the form controls. Built once
    per request."""

    def __init__(self, ctx, query, errors, submitted, place):
        self.ctx = ctx
        self.query = query or {}
        self.errors = errors or {}
        self.submitted = submitted
        self.place = place
        self.lang = prefs.current_lang()
        self.selection = detection.current_selection(ctx.device_config)
        self.saved_mode = self.selection["mode"]
        self.saved_airport = self.selection.get("airport")
        self.saved_runway = self.selection.get("runway")
        self.q = dp.clean_text(self.query.get("q"), airports.MAX_QUERY_CHARS).strip()
        code = self.query.get("airport")
        self.query_airport = airports.find_airport(code) if code else None
        self.mode = self._mode()
        self.airport_code = self._airport_code()
        self.airport = airports.find_airport(self.airport_code)
        self.runway = self._runway()
        self.carry_radius = dp.digits(self.query.get("radius_km"), 3)
        self.radius = self._radius()
        self.latitude, self.longitude, self.label = self._pin()
        self.timezone = self._posted("timezone", ctx.device_config.get(
            "timezone") or quiet_hours.CURATED_TIMEZONES[0][0])
        self.location_name = self._location_name()
        self.fail_safe = is_fail_safe(self.selection, self.location_name)
        self.carried_dirty = self._carried_dirty()

    def _posted(self, key, default):
        """The value a refused post carried for `key`, else `default`."""
        if self.submitted is not None and key in self.submitted:
            return self.submitted[key]
        return default

    def _mode(self):
        """The posted mode, else runway when an airport was picked from the
        list (that choice wins over a carried mode), else the carried mode,
        else the stored one."""
        requested = self._posted("mode", None)
        if requested is None and self.query_airport is not None:
            return dp.MODE_RUNWAY
        if requested is None:
            requested = self.query.get("mode")
        return requested if requested in dp.MODES else self.saved_mode

    def _airport_code(self):
        if self.submitted is not None and "airport" in self.submitted:
            return self.submitted["airport"]
        if self.query_airport is not None:
            return self.query_airport.icao
        return self.saved_airport or ""

    def _runway(self):
        if self.submitted is not None and "runway" in self.submitted:
            return self.submitted["runway"]
        if self.airport is None:
            return ""
        if self.airport.icao == self.saved_airport and self.saved_runway:
            return self.saved_runway
        return self.airport.runways[0].designator

    def _radius(self):
        if self.submitted is not None and "radius_km" in self.submitted:
            return self.submitted["radius_km"]
        return self.carry_radius or str(self.selection.get("radius_km") or dp.DEFAULT_RADIUS_KM)

    def _pin(self):
        """(latitude, longitude, label) texts of the pin controls: what a
        refused post carried, else the chosen airport when it differs from
        what is stored, else the stored place, else blank."""
        lat, lon, label = "", "", ""
        if self.query_airport is not None and self._airport_pin_wanted():
            airport = self.query_airport
            lat, lon, label = _coord(airport.lat), _coord(airport.lon), airport.name
        elif self.place is not None:
            lat, lon = _coord(self.place["latitude"]), _coord(self.place["longitude"])
            label = self.place["name"]
        return (
            self._posted("latitude", lat), self._posted("longitude", lon),
            self._posted("place_label", label))

    def _airport_pin_wanted(self):
        """Whether the airport asked for in the URL supplies the pin: only in
        runway mode, and not when it already is the stored place."""
        if self.mode != dp.MODE_RUNWAY:
            return False
        unchanged = (
            self.place is not None and self.saved_mode == dp.MODE_RUNWAY
            and self.query_airport.icao == self.saved_airport)
        return not unchanged

    def _location_name(self):
        """The stored place's name when the setting follows a position and the
        place lies in the supported area, else None."""
        if self.saved_mode != dp.MODE_POSITION or self.place is None:
            return None
        return self.place["name"] if dp.location_usable(self.place) else None

    def _carried_dirty(self):
        """Whether unsaved values arrived with the page: a refused save, or a
        mode, airport or radius in the URL that differs from what is stored."""
        if self.submitted is not None:
            return True
        if self.query.get("mode") in dp.MODES and self.mode != self.saved_mode:
            return True
        if self.query_airport is not None and (
                self.saved_mode != dp.MODE_RUNWAY
                or self.query_airport.icao != self.saved_airport):
            return True
        radius = dp.digits(self.query.get("radius_km"), 3)
        stored = str(self.selection.get("radius_km") or dp.DEFAULT_RADIUS_KM)
        return bool(radius) and radius != stored


def _href(**fields):
    """The scoped page URL with the given non-empty query fields."""
    pairs = [(key, value) for key, value in fields.items() if value]
    query = "?" + urlencode(pairs) if pairs else ""
    return device_scope.scoped(dp.DETECTION_ROUTE) + query


def _card(title_id, title, body, extra_class="", attrs=""):
    return (
        '<section class="theme-status theme-status--nested place-card%s"%s '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s</section>'
    ) % (extra_class, attrs, title_id, title_id, escape_html(title), body)


def _stray_errors_html(view):
    """The refusals of an older form, which have no control on this page."""
    return "".join(
        _field_error_html(view.errors, field, "place-" + field.replace("_", "-"))
        for field in view.errors if field not in _PAGE_FIELDS)


def fail_safe_toast_html(view):
    """The docked warning above the cards when a position setting has no
    usable place; empty otherwise."""
    if not view.fail_safe:
        return ""
    title, detail = layout.split_toast_message(i18n.t(dp.FAIL_SAFE_TOAST))
    return layout.toast_html(
        title, detail, tone=layout.TOAST_TONE_WARNING, role="status", docked=True)


def _summary_html(view):
    value, detail, pill, tag, empty = summary_values(view.selection, view.location_name)
    return (
        '<dl class="detection-summary">'
        "<div><dt>%s</dt><dd>%s %s"
        '<span class="detection-summary__detail text-label section-caption">%s</span></dd></div>'
        '<div><dt>%s</dt><dd><code class="detection-tag" lang="en">%s</code></dd></div>'
        '<div><dt>%s</dt><dd><code class="detection-tag" lang="en">%s</code></dd></div>'
        "</dl>"
    ) % (
        escape_html(i18n.t(dp.SUMMARY_FOLLOWING)), escape_html(value), pill,
        escape_html(detail),
        escape_html(i18n.t(dp.SUMMARY_TAG)), escape_html(tag),
        escape_html(i18n.t(dp.SUMMARY_EMPTY)), escape_html(empty))


def _place_line_html(view):
    place = view.place
    if place is None:
        return layout.empty_state(
            i18n.t(EMPTY_HEADING), i18n.t(EMPTY_BODY), compact=True)
    return '<p class="place-line text-label section-caption">%s · %s, %s</p>' % (
        escape_html(place["name"]), escape_html(_coord(place["latitude"])),
        escape_html(_coord(place["longitude"])))


def status_card_html(view):
    return _card(
        "place-status-heading", i18n.t(dp.SUMMARY_TITLE),
        _summary_html(view) + _place_line_html(view), " place-card--status")


def _form_html(view):
    """The POST form. It holds no visible control: every field reaches it
    through its `form` attribute, so the cards can sit anywhere."""
    return (
        '<form method="post" id="%s" action="%s" data-dirty-form novalidate>'
        "%s"
        '<input type="hidden" name="%s" value="%s"></form>'
    ) % (
        dp.FORM_ID, escape_html(device_scope.scoped(dp.DETECTION_ROUTE, "POST")),
        layout.csrf_field(), dp.ACTION_FIELD, dp.ACTION_SAVE_PLACE)


def _map_attrs(view):
    has_pin = bool(view.latitude and view.longitude)
    if not has_pin:
        zoom = FRANCE_ZOOM
    elif view.mode == dp.MODE_RUNWAY and view.airport is not None:
        zoom = CATALOGUE_ZOOM
    else:
        zoom = PLACE_ZOOM
    return (
        'data-lat="%s" data-lon="%s" data-zoom="%d" data-mode="%s" '
        'data-airport="%s" data-radius-km="%s"'
    ) % (
        escape_html(view.latitude if has_pin else ""),
        escape_html(view.longitude if has_pin else ""), zoom, escape_html(view.mode),
        escape_html(view.airport.icao if view.airport is not None else ""),
        escape_html(view.radius))


def _search_form_html():
    return (
        '<form class="place-search js-gate" role="search" aria-label="%s" '
        'method="get" action="%s">'
        '<label for="place-search" class="text-label">%s</label>'
        '<div class="place-search__row">'
        '<input type="search" id="place-search" autocomplete="off" '
        'autocapitalize="off" spellcheck="false" enterkeyhint="search" maxlength="120" '
        'aria-describedby="place-search-help">'
        '<button type="submit" class="detection-search">%s</button></div>'
        '<p id="place-search-help" class="text-label section-caption">%s</p></form>'
    ) % (
        escape_html(i18n.t(PLACE_TITLE)), escape_html(_href()),
        escape_html(i18n.t(SEARCH_LABEL)), escape_html(i18n.t(SEARCH_BUTTON)),
        escape_html(i18n.t(SEARCH_HELP)))


def _about_map_html():
    return (
        '<details class="place-about"><summary>%s</summary>'
        '<p class="text-label section-caption">%s</p>'
        '<p class="text-label section-caption">%s</p>'
        '<p class="text-label section-caption">'
        '<a class="text-link detection-link" href="%s" rel="noopener noreferrer">%s</a> · '
        '<a class="text-link detection-link" href="%s" rel="noopener noreferrer">%s</a></p>'
        "</details>"
    ) % (
        escape_html(i18n.t(ABOUT_MAP)), escape_html(i18n.t(MAP_CREDITS)),
        escape_html(i18n.t(MAP_PRIVACY)), OSM_COPYRIGHT_URL,
        escape_html(i18n.t(COPYRIGHT_LINK)), OSM_FIX_URL,
        escape_html(i18n.t(REPORT_PROBLEM)))


def place_card_html(view):
    body = (
        '<p class="place-fallback text-label section-caption">%s</p>'
        "%s"
        '<button type="button" class="place-locate detection-search js-gate" '
        'id="place-locate">%s%s</button>'
        '<div id="place-map" class="place-map js-gate" role="group" tabindex="0" '
        'aria-label="%s" %s></div>'
        '<p id="place-status" class="place-status text-label" role="status" '
        'aria-live="polite"></p>'
        "%s"
    ) % (
        escape_html(i18n.t(NO_SCRIPT_MAP)), _search_form_html(),
        layout.icon_html("icon-locate", 20), escape_html(i18n.t(LOCATE_BUTTON)),
        escape_html(i18n.t(MAP_LABEL)), _map_attrs(view), _about_map_html())
    return _card("place-heading", i18n.t(PLACE_TITLE), body, " place-card--map")


def _airport_row_html(view, airport):
    haystack = _fold(" ".join(
        (airport.name, airport.municipality, airport.icao, airport.iata)))
    current = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if airport.icao == view.saved_airport and view.saved_mode == dp.MODE_RUNWAY
        else "")
    href = _href(airport=airport.icao, q=view.q, radius_km=view.carry_radius)
    return (
        '<li class="place-airport" data-filter-text="%s">'
        '<a class="place-airport__link" href="%s#airport-runways" data-detection-nav data-icao="%s" '
        'data-lat="%s" data-lon="%s" data-name="%s">'
        '<span class="place-airport__name">%s</span>'
        '<span class="place-airport__meta text-label"%s>%s</span></a></li>'
    ) % (
        escape_html(haystack), escape_html(href), escape_html(airport.icao),
        _coord(airport.lat), _coord(airport.lon), escape_html(airport.name),
        escape_html(airport.name), current, escape_html(dp.airport_codes(airport)))


def _listed_airports(view):
    """The airports the list shows, sorted by municipality: all of them, or
    every match of the search term."""
    if view.q:
        found, _total = airports.search_airports(view.q, len(airports.load_catalogue()))
    else:
        found = list(airports.load_catalogue().values())
    return sorted(found, key=lambda a: (_fold(a.municipality), _fold(a.name), a.icao))


def _count_text(view, listed):
    if not view.q:
        return i18n.t(FILTER_COUNT_TEMPLATE) % (len(listed), len(listed))
    if not listed:
        return i18n.t(dp.COUNT_NONE) % {"query": view.q}
    if len(listed) == 1:
        return i18n.t(dp.COUNT_ONE)
    return i18n.t(dp.COUNT_MANY) % {"count": len(listed)}


def _filter_form_html(view, listed):
    return (
        '<form method="get" action="%s" role="search" aria-label="%s" data-detection-nav>'
        '<input type="hidden" name="mode" value="%s">'
        '<input type="hidden" name="radius_km" value="%s">'
        '<label for="airport-filter" class="text-label">%s</label>'
        '<div class="place-search__row">'
        '<input type="search" id="airport-filter" name="q" value="%s" '
        'autocomplete="off" autocapitalize="off" spellcheck="false" '
        'enterkeyhint="search" maxlength="%d" data-filter-input '
        'aria-describedby="airport-filter-hint">'
        '<button type="submit" class="detection-search" id="airport-filter-submit">%s</button></div>'
        '<p id="airport-filter-hint" class="text-label section-caption">%s</p></form>'
        '<p id="airport-results-count" class="text-label" role="status" '
        'aria-live="polite" data-filter-count data-filter-count-template="%s">%s</p>'
    ) % (
        escape_html(device_scope.scoped(dp.DETECTION_ROUTE)),
        escape_html(i18n.t(AIRPORTS_TITLE)), escape_html(view.mode),
        escape_html(view.radius), escape_html(i18n.t(FILTER_LABEL)),
        escape_html(view.q), airports.MAX_QUERY_CHARS,
        escape_html(i18n.t(dp.SEARCH_BUTTON)), escape_html(i18n.t(dp.SEARCH_HINT)),
        escape_html(i18n.t(FILTER_COUNT_TEMPLATE).replace("%d", "#")),
        escape_html(_count_text(view, listed)))


def airports_card_html(view):
    listed = _listed_airports(view)
    rows = "".join(_airport_row_html(view, airport) for airport in listed)
    if listed:
        listing = '<ul class="place-airports" aria-label="%s">%s</ul>' % (
            escape_html(i18n.t(AIRPORTS_TITLE)), rows)
        empty = ""
    else:
        listing = ""
        empty = layout.empty_state(
            i18n.t(dp.NO_RESULT_HEADING), i18n.t(dp.NO_RESULT_BODY), compact=True)
    hidden_empty = (
        '<p class="empty-state__body text-label" data-filter-empty hidden>%s</p>'
        % escape_html(i18n.t(dp.NO_RESULT_HEADING)))
    return _card(
        "airports-heading", i18n.t(AIRPORTS_TITLE),
        _filter_form_html(view, listed) + listing + empty + hidden_empty,
        " place-card--airports")


def _mode_card_html(view, mode, control_id, text):
    return (
        '<label class="runway-card place-mode">'
        '<input type="radio" name="mode" id="%s" value="%s" class="visually-hidden" '
        'form="%s"%s><span class="runway-card__number">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        control_id, mode, dp.FORM_ID, " checked" if view.mode == mode else "",
        escape_html(i18n.t(text)), layout.icon_html("icon-check"),
        escape_html(i18n.t(SELECTED_LABEL)))


def _runway_detail(runway, lang):
    text = "%s m" % dp.format_count(runway.length_m, lang)
    surface = dp.SURFACES.get(runway.surface or "")
    return text + (" · " + i18n.t(surface) if surface is not None else "")


def _runway_card_html(view, airport, runway):
    display_id = display_id_for(airport.icao, runway.designator)
    number = LEGACY_PILL_NUMBER.get(display_id)
    pill = (
        ' <span class="banner__pill">%s</span>' % escape_html(
            i18n.t(LEGACY_PILL) % {"number": number}) if number else "")
    current = (
        airport.icao == view.saved_airport and runway.designator == view.saved_runway
        and view.saved_mode == dp.MODE_RUNWAY)
    badge = (
        ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if current else "")
    return (
        '<label class="runway-card%s"%s>'
        '<input type="radio" name="runway" value="%s" class="visually-hidden" form="%s"%s>'
        '<span class="runway-card__number">%s%s</span>'
        '<span class="runway-card__detail text-label section-caption">%s</span>'
        '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        " runway-card--selected" if current else "", badge,
        escape_html(runway.designator), dp.FORM_ID,
        " checked" if runway.designator == view.runway else "",
        escape_html(runway.designator), pill,
        escape_html(_runway_detail(runway, view.lang)),
        layout.icon_html("icon-check"), escape_html(i18n.t(SELECTED_LABEL)))


def _runway_group_html(view):
    """The chosen airport's runways as radio cards, or the note asking for an
    airport (an unknown code posted by hand reads as not in the catalogue)."""
    errors = view.errors
    airport = view.airport
    if airport is None:
        note = (
            layout.empty_state(
                i18n.t(dp.UNKNOWN_AIRPORT), i18n.t(dp.NO_RESULT_BODY), compact=True)
            if view.airport_code else
            '<p class="text-label section-caption">%s</p>' % escape_html(
                i18n.t(PICK_AIRPORT_NOTE)))
        return (
            note + '<input type="hidden" name="airport" value="%s" form="%s">' % (
                escape_html(view.airport_code), dp.FORM_ID)
            + _field_error_html(errors, "airport", "place-airport")
            + _field_error_html(errors, "runway", "place-runway"))
    cards = "".join(_runway_card_html(view, airport, r) for r in airport.runways)
    first_id = display_id_for(airport.icao, airport.runways[0].designator)
    hint = i18n.t(dp.TAG_HINT) % {
        "code": airport.iata or airport.icao, "example": detection.tag_text(first_id)}
    return (
        '<div id="airport-runways" class="place-chosen">'
        '<p><span class="place-chosen__name">%s</span> '
        '<span class="text-label section-caption">%s</span></p></div>'
        '<h3 class="place-subtitle" id="runway-group-heading">%s</h3>'
        '<div class="runway-row detection-runways" role="radiogroup" '
        'aria-labelledby="runway-group-heading">%s</div>%s'
        '<input type="hidden" name="airport" value="%s" form="%s">'
        '<p class="text-label section-caption">%s</p>'
    ) % (
        escape_html(airport.name), escape_html(dp.airport_codes(airport)),
        escape_html(i18n.t(RUNWAY_LABEL)), cards,
        _field_error_html(errors, "runway", "place-runway"),
        escape_html(airport.icao), dp.FORM_ID, escape_html(hint)
    ) + _field_error_html(errors, "airport", "place-airport")


def _radius_html(view):
    return (
        '<div class="place-radius">'
        '<label for="place-radius">%s</label>'
        '<input type="number" id="place-radius" name="radius_km" form="%s" '
        'min="%d" max="%d" step="1" inputmode="numeric" value="%s"%s>'
        '<p id="place-radius-help" class="text-label section-caption">%s</p>%s</div>'
    ) % (
        escape_html(i18n.t(RADIUS_LABEL)), dp.FORM_ID, detection.RADIUS_KM_MIN,
        detection.RADIUS_KM_MAX, escape_html(view.radius),
        _field_error_attrs(view.errors, "radius_km", "place-radius", "place-radius-help"),
        escape_html(i18n.t(RADIUS_HELP)),
        _field_error_html(view.errors, "radius_km", "place-radius"))


def follow_card_html(view):
    modes = (
        '<div class="runway-row place-modes" role="radiogroup" '
        'aria-labelledby="follow-heading">%s%s</div>%s'
    ) % (
        _mode_card_html(view, dp.MODE_RUNWAY, "place-mode-runway", MODE_RUNWAY_CARD),
        _mode_card_html(view, dp.MODE_POSITION, "place-mode-area", MODE_AREA_CARD),
        _field_error_html(view.errors, "mode", "place-mode"))
    return _card(
        "follow-heading", i18n.t(FOLLOW_TITLE),
        modes + _runway_group_html(view) + _radius_html(view),
        " place-card--follow", ' %s="%s"' % (
            DIRTY_SECTION_ATTR, escape_html(i18n.t(dp.SECTION_DETECTION))))


def _number_field_html(view, field, control_id, label, value, hint):
    return (
        '<label for="%s">%s</label>'
        '<input type="number" id="%s" name="%s" form="%s" step="0.0001" '
        'inputmode="decimal" value="%s"%s>'
        '<p id="%s-hint" class="text-label section-caption">%s</p>%s'
    ) % (
        control_id, escape_html(i18n.t(label)), control_id, field, dp.FORM_ID,
        escape_html(value),
        _field_error_attrs(view.errors, field, control_id, control_id + "-hint"),
        control_id, escape_html(i18n.t(hint)),
        _field_error_html(view.errors, field, control_id))


def _label_field_html(view):
    return (
        '<label for="place-label">%s</label>'
        '<input type="text" id="place-label" name="place_label" form="%s" '
        'maxlength="60" autocomplete="off" value="%s"%s>%s'
    ) % (
        escape_html(i18n.t(PLACE_LABEL_FIELD)), dp.FORM_ID, escape_html(view.label),
        _field_error_attrs(view.errors, "place_label", "place-label"),
        _field_error_html(view.errors, "place_label", "place-label"))


def _timezone_options_html(current):
    keys = [key for key, _label in quiet_hours.CURATED_TIMEZONES]
    if current not in keys:
        keys.append(current)
    options = []
    for key in keys:
        offset = quiet_hours.timezone_offset_text(key)
        text = quiet_hours.timezone_label_text(key)
        if offset:
            text = "%s (%s)" % (text, offset)
        options.append('<option value="%s"%s>%s</option>' % (
            escape_html(key), " selected" if key == current else "", escape_html(text)))
    return "".join(options)


def _timezone_field_html(view):
    return (
        '<label for="place-timezone">%s</label>'
        '<select id="place-timezone" name="timezone" form="%s"%s>%s</select>%s'
    ) % (
        escape_html(i18n.t(quiet_hours.TIMEZONE_LABEL)), dp.FORM_ID,
        _field_error_attrs(view.errors, "timezone", "place-timezone"),
        _timezone_options_html(view.timezone),
        _field_error_html(view.errors, "timezone", "place-timezone"))


def details_card_html(view):
    place_section = (
        '<div class="place-fields" %s="%s">%s%s%s</div>'
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(SECTION_PLACE)),
        _number_field_html(
            view, "latitude", "place-lat", dp.FIELD_LATITUDE, view.latitude,
            dp.LATITUDE_HINT),
        _number_field_html(
            view, "longitude", "place-lon", dp.FIELD_LONGITUDE, view.longitude,
            dp.LONGITUDE_HINT),
        _label_field_html(view))
    zone_section = '<div class="place-fields" %s="%s">%s</div>' % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(quiet_hours.TIMEZONE_LABEL)),
        _timezone_field_html(view))
    return (
        '<details id="details" class="theme-status theme-status--nested '
        'place-card place-details" open><summary>%s</summary>%s%s</details>'
    ) % (escape_html(i18n.t(DETAILS_TITLE)), place_section, zone_section)


def render(ctx, query=None, errors=None, submitted=None, place=None):
    """The Location and detection page body.

    `query` is `detection_page.parse_query()`'s output for a GET; `errors` and
    `submitted` come together from a refused POST and echo what was posted;
    `place` is the frame's own position (`fleet_db.frame_position`), or None.
    """
    ctx = page_context.coerce(ctx)
    view = _View(ctx, query, errors, submitted, place)
    plain_href = device_scope.scoped(dp.DETECTION_ROUTE)
    return (
        layout.page_header(i18n.t(PAGE_TITLE), i18n.t(PAGE_PURPOSE))
        + fail_safe_toast_html(view)
        + _stray_errors_html(view)
        + _form_html(view)
        + '<div class="place-page">%s%s<div class="place-page__rest">%s%s%s</div></div>' % (
            status_card_html(view), place_card_html(view),
            airports_card_html(view), follow_card_html(view),
            details_card_html(view))
        + dp.dirty_bar_html(
            plain_href if view.carried_dirty else None, i18n.t(dp.SAVE_LOCATION))
    )
