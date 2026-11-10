"""The public credits page: loads and validates companion/credits.json and
renders it as the page body. Pure markup apart from reading the one fixed
data file; the route handler lives in companion/app.py.

Never imports `companion.app` (app.py imports this module).
"""
import json
import os
from urllib.parse import urlsplit

from companion import i18n, layout, prefs

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
    pill = (
        '<span class="banner__pill">%s</span>'
        % layout.escape_html(i18n.t(_ATTRIBUTION_TEXT))
    ) if source["citation_required"] else ""
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
            layout.escape_html(source["licence"]),
            pill,
            layout.escape_html(source["url"]),
            layout.escape_html(
                "%s: %s" % (i18n.t(_VISIT_TEXT), source["name"]))))


def credits_body(sources=None):
    """The page body for the request language set through prefs."""
    if sources is None:
        sources = load_credits()
    lang = prefs.current_lang()
    if lang not in LANGUAGES:
        lang = "en"
    return (
        layout.page_header(i18n.t(TITLE_TEXT), purpose=i18n.t(_INTRO_TEXT))
        + "".join(_source_card_html(source, lang) for source in sources)
        + '<p class="text-body"><a href="/login">%s</a></p>'
        % layout.escape_html(i18n.t(_BACK_TEXT)))


def credits_page(ui_theme, health_alert, sources=None):
    return layout.page_shell(
        title=i18n.t(TITLE_TEXT), active="", body=credits_body(sources),
        ui_theme=ui_theme, health_alert=health_alert)
