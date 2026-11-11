"""Static-asset allowlist and in-memory revalidation cache behind
`companion/app.py`'s pre-auth CSS/JS routes.

Every route named here is public: a static asset carries no per-user or
sensitive data, so gating it would add a session round-trip for zero
benefit (the same reasoning `companion/app.py`'s route table applies to
each one). The runway, gallery, illustration and theme-preview image
routes are NOT here — they are gated, per-request handlers with their
own membership checks against request-supplied ids, never exact-path
lookups against a fixed allowlist.

`STATIC_ROUTES[route]` is looked up by exact dict key only; no
request-derived path segment is ever joined onto `STATIC_DIR`, so this
module has no path-traversal surface.
"""
import collections
import email.utils
import hashlib
import os
import re
import threading
from urllib.parse import parse_qs

from companion import js_minify

_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
STATIC_DIR = os.path.join(_HERE, "static")

STYLE_ROUTE = "/static/style.css"
# The stylesheets linked after the core one (see page_styles.py): first the
# component sheets, rules that several but not all page families use, then
# the page-family sheets. Link order is cascade order.
COMPONENT_STYLE_NAMES = ("c-console", "c-lists")
AREA_STYLE_NAMES = COMPONENT_STYLE_NAMES + (
    "home", "flights", "airlines", "place", "display", "admin")
AREA_STYLE_ROUTES = tuple("/static/style-%s.css" % name for name in AREA_STYLE_NAMES)
# Each *_SCRIPT_ROUTE is the authoritative value a matching
# *_SCRIPT_SRC constant in companion/layout.py must equal exactly; a
# test asserts the sync. Most are pre-auth by design (no session data,
# or served only to the login page itself).
SCRIPT_ROUTE = "/static/battery-trend.js"
NAV_SCRIPT_ROUTE = "/static/nav-dropdown.js"
DIRTY_STATE_SCRIPT_ROUTE = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_ROUTE = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_ROUTE = "/static/copy-button.js"
FRESHNESS_SCRIPT_ROUTE = "/static/freshness.js"
PANEL_LOOKUP_SCRIPT_ROUTE = "/static/panel-lookup.js"
FLASH_CLEANUP_SCRIPT_ROUTE = "/static/flash-cleanup.js"
TOAST_SCRIPT_ROUTE = "/static/toast.js"
CONFIRM_SUBMIT_SCRIPT_ROUTE = "/static/confirm-submit.js"
THEME_PREVIEW_SCRIPT_ROUTE = "/static/theme-preview.js"
SUBMIT_GUARD_SCRIPT_ROUTE = "/static/submit-guard.js"
RELATIVE_TIME_SCRIPT_ROUTE = "/static/relative-time.js"
QUICK_SWITCH_SCRIPT_ROUTE = "/static/quick-switch.js"
VALUE_CONTROLS_SCRIPT_ROUTE = "/static/value-controls.js"
CALENDAR_CONNECT_SCRIPT_ROUTE = "/static/calendar-connect.js"
MODAL_SCRIPT_ROUTE = "/static/modal.js"
MOTION_SCRIPT_ROUTE = "/static/motion.js"
SESSION_GUARD_SCRIPT_ROUTE = "/static/session-guard.js"
PREFETCH_SCRIPT_ROUTE = "/static/prefetch.js"
SPLASH_BOOT_SCRIPT_ROUTE = "/static/splash-boot.js"
SPLASH_SCRIPT_ROUTE = "/static/splash.js"
# Vendored Leaflet, unmodified; only the location page links the script and the
# stylesheet. The library's marker images are not vendored and not served.
LEAFLET_SCRIPT_ROUTE = "/static/vendor/leaflet/leaflet.js"
LEAFLET_STYLE_ROUTE = "/static/vendor/leaflet/leaflet.css"
LEAFLET_LICENSE_ROUTE = "/static/vendor/leaflet/LICENSE"
PLACE_MAP_SCRIPT_ROUTE = "/static/place-map.js"
PLACE_MAP_SEARCH_SCRIPT_ROUTE = "/static/place-map-search.js"
PLACE_CARD_SCRIPT_ROUTE = "/static/place-card.js"
PLACE_SEARCH_SCRIPT_ROUTE = "/static/place-search.js"
PLACE_START_SCRIPT_ROUTE = "/static/place-start.js"
PLACE_AIRPORT_LIST_SCRIPT_ROUTE = "/static/place-airport-list.js"
AIRLINE_TYPES_SCRIPT_ROUTE = "/static/airline-types.js"
# Brand icons. Browsers fetch these before any session exists (the login page
# links them), so they are public like every other static asset.
FAVICON_ROUTE = "/static/favicon.svg"
APPLE_TOUCH_ICON_ROUTE = "/static/apple-touch-icon.png"

_STYLE_CSS_PATH = os.path.join(STATIC_DIR, "style.css")
_CSS_PATHS = frozenset(
    [_STYLE_CSS_PATH] + [os.path.join(STATIC_DIR, "style-%s.css" % n) for n in AREA_STYLE_NAMES])
_BATTERY_TREND_JS_PATH = os.path.join(STATIC_DIR, "battery-trend.js")
_NAV_DROPDOWN_JS_PATH = os.path.join(STATIC_DIR, "nav-dropdown.js")
_DIRTY_STATE_JS_PATH = os.path.join(STATIC_DIR, "dirty-state.js")
_LIST_FILTER_JS_PATH = os.path.join(STATIC_DIR, "list-filter.js")
_COPY_BUTTON_JS_PATH = os.path.join(STATIC_DIR, "copy-button.js")
_FRESHNESS_JS_PATH = os.path.join(STATIC_DIR, "freshness.js")
_PANEL_LOOKUP_JS_PATH = os.path.join(STATIC_DIR, "panel-lookup.js")
_FLASH_CLEANUP_JS_PATH = os.path.join(STATIC_DIR, "flash-cleanup.js")
_TOAST_JS_PATH = os.path.join(STATIC_DIR, "toast.js")
_CONFIRM_SUBMIT_JS_PATH = os.path.join(STATIC_DIR, "confirm-submit.js")
_THEME_PREVIEW_JS_PATH = os.path.join(STATIC_DIR, "theme-preview.js")
_SUBMIT_GUARD_JS_PATH = os.path.join(STATIC_DIR, "submit-guard.js")
_RELATIVE_TIME_JS_PATH = os.path.join(STATIC_DIR, "relative-time.js")
_QUICK_SWITCH_JS_PATH = os.path.join(STATIC_DIR, "quick-switch.js")
_VALUE_CONTROLS_JS_PATH = os.path.join(STATIC_DIR, "value-controls.js")
_CALENDAR_CONNECT_JS_PATH = os.path.join(STATIC_DIR, "calendar-connect.js")
_MODAL_JS_PATH = os.path.join(STATIC_DIR, "modal.js")
_MOTION_JS_PATH = os.path.join(STATIC_DIR, "motion.js")
_SESSION_GUARD_JS_PATH = os.path.join(STATIC_DIR, "session-guard.js")
_PREFETCH_JS_PATH = os.path.join(STATIC_DIR, "prefetch.js")
_SPLASH_BOOT_JS_PATH = os.path.join(STATIC_DIR, "splash-boot.js")
_SPLASH_JS_PATH = os.path.join(STATIC_DIR, "splash.js")
_LEAFLET_DIR = os.path.join(STATIC_DIR, "vendor", "leaflet")
_LEAFLET_JS_PATH = os.path.join(_LEAFLET_DIR, "leaflet.js")
_LEAFLET_CSS_PATH = os.path.join(_LEAFLET_DIR, "leaflet.css")
_LEAFLET_LICENSE_PATH = os.path.join(_LEAFLET_DIR, "LICENSE")
_PLACE_MAP_JS_PATH = os.path.join(STATIC_DIR, "place-map.js")
_PLACE_MAP_SEARCH_JS_PATH = os.path.join(STATIC_DIR, "place-map-search.js")
_PLACE_CARD_JS_PATH = os.path.join(STATIC_DIR, "place-card.js")
_PLACE_SEARCH_JS_PATH = os.path.join(STATIC_DIR, "place-search.js")
_PLACE_START_JS_PATH = os.path.join(STATIC_DIR, "place-start.js")
_PLACE_AIRPORT_LIST_JS_PATH = os.path.join(STATIC_DIR, "place-airport-list.js")
_AIRLINE_TYPES_JS_PATH = os.path.join(STATIC_DIR, "airline-types.js")
_FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.svg")
_APPLE_TOUCH_ICON_PATH = os.path.join(STATIC_DIR, "apple-touch-icon.png")

# In-memory static-asset cache behind Handler._serve_static() (companion/app.py):
# populated on first read per process, keyed by absolute path. companion/app.py
# restarts on every deploy (deploy/activate.sh restarts
# skypane-companion.service), so a per-process cache is never stale in
# production. An OSError from read_static_bytes() propagates and leaves
# the path uncached, so a file that starts missing and later appears is
# served on the very next request.
_StaticEntry = collections.namedtuple(
    "_StaticEntry", "payload etag last_modified mtime_s")
_STATIC_CACHE = {}
_STATIC_CACHE_LOCK = threading.Lock()

# Every static route shares the same "public, no-cache" policy: no
# per-user data, but `no-cache` (never a max-age window) so every load
# revalidates - no page can ever run new HTML against a browser's stale
# cached CSS/JS after a deploy. The runway image route keeps its own,
# different policy (private, max-age=300) and is not in this allowlist.
_PUBLIC_NO_CACHE = "public, no-cache"

StaticAsset = collections.namedtuple("StaticAsset", "path content_type cache_control")

# route -> the on-disk asset it serves. Exact dict-key lookup only - see
# the module docstring.
STATIC_ROUTES = {
    STYLE_ROUTE: StaticAsset(_STYLE_CSS_PATH, "text/css", _PUBLIC_NO_CACHE),
    **{route: StaticAsset(
        os.path.join(STATIC_DIR, route.rsplit("/", 1)[1]), "text/css", _PUBLIC_NO_CACHE)
       for route in AREA_STYLE_ROUTES},
    # text/javascript is the sole current-standard MIME type for
    # JavaScript per RFC 9239 (2022), which obsoletes RFC 4329's older
    # application/-prefixed form - deliberately not used here.
    SCRIPT_ROUTE: StaticAsset(_BATTERY_TREND_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    NAV_SCRIPT_ROUTE: StaticAsset(_NAV_DROPDOWN_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    DIRTY_STATE_SCRIPT_ROUTE: StaticAsset(_DIRTY_STATE_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    LIST_FILTER_SCRIPT_ROUTE: StaticAsset(_LIST_FILTER_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    COPY_BUTTON_SCRIPT_ROUTE: StaticAsset(_COPY_BUTTON_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    FRESHNESS_SCRIPT_ROUTE: StaticAsset(_FRESHNESS_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PANEL_LOOKUP_SCRIPT_ROUTE: StaticAsset(_PANEL_LOOKUP_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    FLASH_CLEANUP_SCRIPT_ROUTE: StaticAsset(_FLASH_CLEANUP_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    TOAST_SCRIPT_ROUTE: StaticAsset(_TOAST_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    CONFIRM_SUBMIT_SCRIPT_ROUTE: StaticAsset(_CONFIRM_SUBMIT_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    THEME_PREVIEW_SCRIPT_ROUTE: StaticAsset(_THEME_PREVIEW_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    SUBMIT_GUARD_SCRIPT_ROUTE: StaticAsset(_SUBMIT_GUARD_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    RELATIVE_TIME_SCRIPT_ROUTE: StaticAsset(_RELATIVE_TIME_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    QUICK_SWITCH_SCRIPT_ROUTE: StaticAsset(_QUICK_SWITCH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    VALUE_CONTROLS_SCRIPT_ROUTE: StaticAsset(_VALUE_CONTROLS_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    CALENDAR_CONNECT_SCRIPT_ROUTE: StaticAsset(_CALENDAR_CONNECT_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    MODAL_SCRIPT_ROUTE: StaticAsset(_MODAL_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    MOTION_SCRIPT_ROUTE: StaticAsset(_MOTION_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    SESSION_GUARD_SCRIPT_ROUTE: StaticAsset(_SESSION_GUARD_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PREFETCH_SCRIPT_ROUTE: StaticAsset(_PREFETCH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    SPLASH_BOOT_SCRIPT_ROUTE: StaticAsset(_SPLASH_BOOT_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    SPLASH_SCRIPT_ROUTE: StaticAsset(_SPLASH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    LEAFLET_SCRIPT_ROUTE: StaticAsset(_LEAFLET_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    LEAFLET_STYLE_ROUTE: StaticAsset(_LEAFLET_CSS_PATH, "text/css", _PUBLIC_NO_CACHE),
    LEAFLET_LICENSE_ROUTE: StaticAsset(_LEAFLET_LICENSE_PATH, "text/plain", _PUBLIC_NO_CACHE),
    PLACE_MAP_SCRIPT_ROUTE: StaticAsset(_PLACE_MAP_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PLACE_MAP_SEARCH_SCRIPT_ROUTE: StaticAsset(
        _PLACE_MAP_SEARCH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PLACE_CARD_SCRIPT_ROUTE: StaticAsset(_PLACE_CARD_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PLACE_SEARCH_SCRIPT_ROUTE: StaticAsset(
        _PLACE_SEARCH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PLACE_START_SCRIPT_ROUTE: StaticAsset(
        _PLACE_START_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    PLACE_AIRPORT_LIST_SCRIPT_ROUTE: StaticAsset(
        _PLACE_AIRPORT_LIST_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    AIRLINE_TYPES_SCRIPT_ROUTE: StaticAsset(
        _AIRLINE_TYPES_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    FAVICON_ROUTE: StaticAsset(_FAVICON_PATH, "image/svg+xml", _PUBLIC_NO_CACHE),
    APPLE_TOUCH_ICON_ROUTE: StaticAsset(_APPLE_TOUCH_ICON_PATH, "image/png", _PUBLIC_NO_CACHE),
}


# A CSS string literal (kept verbatim) or a block comment (dropped).
_CSS_TOKEN = re.compile(
    r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|/\*.*?\*/""", re.DOTALL)


def minify_css(payload):
    """The served form of a stylesheet: block comments removed (string
    literals untouched), every line trimmed and blank lines dropped. The
    result depends only on the input bytes, so its hash is stable, and
    the source file keeps its comments.
    """
    text = _CSS_TOKEN.sub(lambda m: m.group(1) or " ", payload.decode("utf-8"))
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line).encode("utf-8") + b"\n"


# A long-lived, content-addressed URL: the `?v=` token changes with the
# served bytes, so a deploy that edits an asset also changes every URL
# the HTML names and no browser can run new markup against old assets.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
_VERSION_LENGTH = 12
_STATIC_URL = re.compile(r'((?:href|src)=")(/static/[^"?#]+\.(?:css|js))(")')


def asset_version(route):
    """The `?v=` token for a STATIC_ROUTES route (a prefix of the served
    payload's SHA-256), or None for an unknown route or unreadable file."""
    asset = STATIC_ROUTES.get(route)
    if asset is None:
        return None
    try:
        return static_entry(asset.path).etag.strip('"')[:_VERSION_LENGTH]
    except OSError:
        return None


def version_static_urls(html):
    """`html` with every known /static/ href or src given its `?v=` token.
    Applied to the final markup at send time, so page modules keep
    naming plain routes."""
    def add(match):
        version = asset_version(match.group(2))
        if version is None:
            return match.group(0)
        return "%s%s?v=%s%s" % (match.group(1), match.group(2), version, match.group(3))
    return _STATIC_URL.sub(add, html)


def cache_control_for(route, query, default):
    """The immutable policy only for a request whose `v` names the
    current bytes; any other (or missing) token revalidates as before."""
    version = asset_version(route)
    requested = parse_qs(query).get("v", [None])[0]
    if version is not None and requested == version:
        return IMMUTABLE_CACHE
    return default


def read_static_bytes(abs_path):
    """The one disk-read seam behind `static_entry()` - kept as its own
    function so a test can monkeypatch it and count how often it runs.
    """
    with open(abs_path, "rb") as fh:
        return fh.read()


def static_entry(abs_path):
    """The cached `_StaticEntry` for `abs_path`, reading the file at most
    once per process. Raises the underlying `OSError` (never caught
    here) when the file is missing or unreadable; the caller maps that
    to a 404.
    """
    with _STATIC_CACHE_LOCK:
        entry = _STATIC_CACHE.get(abs_path)
    if entry is not None:
        return entry
    payload = read_static_bytes(abs_path)
    if abs_path in _CSS_PATHS:
        payload = minify_css(payload)
    elif abs_path.endswith(".js") and os.path.dirname(abs_path) == STATIC_DIR:
        payload = js_minify.minify_js(payload)
    mtime_s = int(os.stat(abs_path).st_mtime)
    etag = '"%s"' % hashlib.sha256(payload).hexdigest()[:32]
    last_modified = email.utils.formatdate(mtime_s, usegmt=True)
    entry = _StaticEntry(payload, etag, last_modified, mtime_s)
    with _STATIC_CACHE_LOCK:
        _STATIC_CACHE[abs_path] = entry
    return entry


def if_none_match_matches(headers, etag):
    """Whether `headers`' `If-None-Match` (a comma-separated list, each
    entry optionally `W/`-prefixed, or a bare `*`) already matches
    `etag`. `None` (not `False`) when the header is absent, so a caller
    that also wants the `If-Modified-Since` fallback (`not_modified()`
    below) can tell "no match" apart from "nothing to match against".
    Header values are only ever compared here, never echoed into a
    response.
    """
    inm = headers.get("If-None-Match")
    if inm is None:
        return None
    tags = [tag.strip() for tag in inm.split(",")]
    return "*" in tags or any(tag.removeprefix("W/") == etag for tag in tags)


def not_modified(headers, etag, mtime_s):
    """Whether a conditional request already holds the current
    representation, per RFC 9110 13.2.2's evaluation order: a present
    If-None-Match decides the outcome outright (a mismatch just means
    "no match", never an error), and If-Modified-Since is consulted only
    in its absence. Defensive: a malformed date never raises, it simply
    fails to match.
    """
    match = if_none_match_matches(headers, etag)
    if match is not None:
        return match
    ims = headers.get("If-Modified-Since")
    if not ims:
        return False
    try:
        return mtime_s <= email.utils.parsedate_to_datetime(ims).timestamp()
    except (TypeError, ValueError, OverflowError, IndexError):
        return False


# File extensions a browser, crawler or scanner asks for on its own
# (favicon, manifest, source maps, images): an unknown one is answered
# without a page.
_ASSET_EXTENSIONS = frozenset((
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".js", ".mjs", ".css",
    ".map", ".json", ".txt", ".xml", ".webmanifest", ".woff", ".woff2", ".ttf"))
ASSET_NOT_FOUND_MAX_AGE_S = 300


def looks_like_asset(path):
    """Whether `path` names a file a browser or scanner asks for on its own:
    a known asset extension on a path under /static/ or on a single-segment
    path (/favicon.ico, /robots.txt). Two-segment and device-scoped file
    routes (/illustration/x.png, /devices/<id>/runway-image/x.png) are
    excluded: a refused one answers the page 404, and an absent one must
    not be told apart from it."""
    if not (path.startswith("/static/") or path.count("/") == 1):
        return False
    last = path.rsplit("/", 1)[-1]
    dot = last.rfind(".")
    return dot > 0 and last[dot:].lower() in _ASSET_EXTENSIONS


def send_asset_not_found(handler):
    """An empty 404 that may be cached briefly, for an asset-like path that
    matches no route."""
    handler.send_response(404)
    handler.send_header("Content-Length", "0")
    handler.send_header("Cache-Control", "public, max-age=%d" % ASSET_NOT_FOUND_MAX_AGE_S)
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
