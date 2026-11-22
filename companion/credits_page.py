"""The public credits page: loads and validates companion/credits.json and
renders it as the page body. Pure markup apart from reading the one fixed
data file; the route handler lives in companion/app.py.

Never imports `companion.app` (app.py imports this module).
"""
import json
import os
from urllib.parse import urlsplit

from companion import i18n, layout, login_page, prefs, ui_components

CREDITS_ROUTE = "/credits"

# Fixed location: the path is never derived from request input.
DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credits.json")

SUPPORTED_VERSION = 1
REQUIRED_IDS = ("adsbfi", "adsblol", "adsbdb", "ourairports")
LANGUAGES = ("en", "fr")
_SOURCE_KEYS = frozenset(
    ("id", "name", "url", "licence", "citation_required", "description"))
# The one source whose terms require a visible citation must point at
# its own host, so a data-file typo cannot cite the wrong site.
_REQUIRED_HOSTS = {"adsbfi": "adsb.fi"}

TITLE_TEXT = i18n.msg("credits.credits", "Credits")
_INTRO_TEXT = i18n.msg(
    "credits.skypane_shows_live_flights_thanks_to_these_open",
    "SkyPane shows live flights thanks to these open data sources.")
_VISIT_TEXT = i18n.msg("credits.visit_site", "Visit site")
_LICENCE_TEXT = i18n.msg("credits.license", "License")
_ATTRIBUTION_TEXT = i18n.msg(
    "credits.attribution_required", "Attribution required")
_BACK_TEXT = i18n.msg("credits.back_to_sign_in", "Back to sign in")

# The data file holds one English licence line per source. A line that is plain
# words (not a licence identifier such as CC0 or BSD-2-Clause) is translated
# here, keyed by its exact text; any other text is shown as written.
_LICENCE_LINE_TEXTS = {
    "Open data, non-commercial use": i18n.msg(
        "credits.licence_open_data_non_commercial", "Open data, non-commercial use"),
    "Free, crowdsourced": i18n.msg("credits.licence_free_crowdsourced", "Free, crowdsourced"),
    "Public domain": i18n.msg("credits.licence_public_domain", "Public domain"),
    "Map data © OpenStreetMap contributors, ODbL": i18n.msg(
        "credits.licence_osm_map_data", "Map data © OpenStreetMap contributors, ODbL"),
    "Search data © OpenStreetMap contributors, ODbL": i18n.msg(
        "credits.licence_osm_search_data", "Search data © OpenStreetMap contributors, ODbL"),
}


def _licence_line(licence):
    message = _LICENCE_LINE_TEXTS.get(licence)
    return i18n.t(message) if message is not None else licence


def _fail(message):
    raise ValueError("credits file: " + message)


def _validate_url(source_id, url):
    if not isinstance(url, str):
        _fail("%s: url must be a string" % source_id)
    parts = urlsplit(url)
    if parts.scheme != "https":
        _fail("%s: url must use https" % source_id)
    if not parts.hostname:
        _fail("%s: url has no host" % source_id)
    expected = _REQUIRED_HOSTS.get(source_id)
    if expected is not None and parts.hostname != expected:
        _fail("%s: url host must be %s" % (source_id, expected))


def _validate_source(source):
    if not isinstance(source, dict):
        _fail("each source must be an object")
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id:
        _fail("source without an id")
    extra = set(source) - _SOURCE_KEYS
    if extra:
        _fail("%s: unknown key(s) %s" % (source_id, sorted(extra)))
    for key in sorted(_SOURCE_KEYS - set(source)):
        _fail("%s: missing %s" % (source_id, key))
    for key in ("name", "licence"):
        if not isinstance(source[key], str) or not source[key].strip():
            _fail("%s: %s must be a non-empty string" % (source_id, key))
    if not isinstance(source["citation_required"], bool):
        _fail("%s: citation_required must be true or false" % source_id)
    _validate_url(source_id, source["url"])
    description = source["description"]
    if not isinstance(description, dict) or set(description) != set(LANGUAGES):
        _fail("%s: description needs exactly en and fr" % source_id)
    for lang in LANGUAGES:
        if not isinstance(description[lang], str) or not description[lang].strip():
            _fail("%s: description.%s must be non-empty text" % (source_id, lang))


def load_credits(path=DEFAULT_PATH):
    """Read and validate the credits file; returns its list of sources.
    Raises ValueError for any malformed content.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError("credits file: not valid JSON (%s)" % exc) from exc
    if not isinstance(data, dict) or set(data) != {"version", "sources"}:
        _fail("top level must hold exactly version and sources")
    if data["version"] != SUPPORTED_VERSION:
        _fail("unsupported version %r" % (data["version"],))
    sources = data["sources"]
    if not isinstance(sources, list):
        _fail("sources must be a list")
    seen = set()
    for source in sources:
        _validate_source(source)
        if source["id"] in seen:
            _fail("duplicate id %s" % source["id"])
        seen.add(source["id"])
    missing = [source_id for source_id in REQUIRED_IDS if source_id not in seen]
    if missing:
        _fail("missing required id(s) %s" % missing)
    return sources


def _source_card_html(source, lang):
    pill = ui_components.pill_html(i18n.t(_ATTRIBUTION_TEXT)) if source["citation_required"] else ""
    return (
        '<section class="page-section credits-source" data-credit="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-body">%s</p>'
        '<p class="text-label section-caption">%s: %s %s</p>'
        '<a class="text-link" href="%s" target="_blank" '
        'rel="noopener noreferrer">%s</a>'
        "</section>" % (
            layout.escape_html(source["id"]),
            layout.escape_html(source["name"]),
            layout.escape_html(source["description"][lang]),
            layout.escape_html(i18n.t(_LICENCE_TEXT)),
            layout.escape_html(_licence_line(source["licence"])),
            pill,
            layout.escape_html(source["url"]),
            layout.escape_html(
                "%s: %s" % (i18n.t(_VISIT_TEXT), source["name"]))))


def _back_link_html(back):
    """The way out of the page: back to sign-in for a visitor with no session.
    A signed-in person, user or administrator, came from the Account page and
    goes back there: a chevron link above the title."""
    if back == login_page.BACK_SIGN_IN:
        return '<p class="text-body credits-back"><a class="text-link" href="/login">%s</a></p>' % (
            layout.escape_html(i18n.t(_BACK_TEXT)))
    return (
        '<p class="credits-back credits-back--top"><a class="text-link" href="/account">'
        '%s%s</a></p>' % (
            layout.icon_html("icon-chevron-left", 20),
            layout.escape_html(i18n.t(login_page._BACK_TO_ACCOUNT_TEXT))))


def credits_body(sources=None, back=login_page.BACK_SIGN_IN, home_route=None):
    """The page body for the request language set through prefs. `home_route`
    is kept for callers; a signed-in person's way back is always Account."""
    if sources is None:
        sources = load_credits()
    lang = prefs.current_lang()
    if lang not in LANGUAGES:
        lang = "en"
    back_html = _back_link_html(back)
    top = back_html if back != login_page.BACK_SIGN_IN else ""
    bottom = back_html if back == login_page.BACK_SIGN_IN else ""
    return (
        top
        + layout.page_header(i18n.t(TITLE_TEXT), purpose=i18n.t(_INTRO_TEXT))
        + "".join(_source_card_html(source, lang) for source in sources)
        + bottom)


def credits_page(ui_theme, health_alert, sources=None, back=login_page.BACK_SIGN_IN,
                 home_route=None):
    return layout.page_shell(
        title=i18n.t(TITLE_TEXT), active="", body=credits_body(sources, back, home_route),
        ui_theme=ui_theme, health_alert=health_alert)
