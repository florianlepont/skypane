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
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
STATIC_DIR = os.path.join(_HERE, "static")

STYLE_ROUTE = "/static/style.css"
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
POLL_COOLDOWN_SCRIPT_ROUTE = "/static/poll-cooldown.js"
CONFIRM_SUBMIT_SCRIPT_ROUTE = "/static/confirm-submit.js"
THEME_PREVIEW_SCRIPT_ROUTE = "/static/theme-preview.js"
AIRLINE_TYPES_SCRIPT_ROUTE = "/static/airline-types.js"
LOGIN_CARD_SCRIPT_ROUTE = "/static/login-card.js"
SUBMIT_GUARD_SCRIPT_ROUTE = "/static/submit-guard.js"
RELATIVE_TIME_SCRIPT_ROUTE = "/static/relative-time.js"
QUICK_SWITCH_SCRIPT_ROUTE = "/static/quick-switch.js"
VALUE_CONTROLS_SCRIPT_ROUTE = "/static/value-controls.js"

_STYLE_CSS_PATH = os.path.join(STATIC_DIR, "style.css")
_BATTERY_TREND_JS_PATH = os.path.join(STATIC_DIR, "battery-trend.js")
_NAV_DROPDOWN_JS_PATH = os.path.join(STATIC_DIR, "nav-dropdown.js")
_DIRTY_STATE_JS_PATH = os.path.join(STATIC_DIR, "dirty-state.js")
_LIST_FILTER_JS_PATH = os.path.join(STATIC_DIR, "list-filter.js")
_COPY_BUTTON_JS_PATH = os.path.join(STATIC_DIR, "copy-button.js")
_FRESHNESS_JS_PATH = os.path.join(STATIC_DIR, "freshness.js")
_PANEL_LOOKUP_JS_PATH = os.path.join(STATIC_DIR, "panel-lookup.js")
_FLASH_CLEANUP_JS_PATH = os.path.join(STATIC_DIR, "flash-cleanup.js")
_POLL_COOLDOWN_JS_PATH = os.path.join(STATIC_DIR, "poll-cooldown.js")
_CONFIRM_SUBMIT_JS_PATH = os.path.join(STATIC_DIR, "confirm-submit.js")
_THEME_PREVIEW_JS_PATH = os.path.join(STATIC_DIR, "theme-preview.js")
_AIRLINE_TYPES_JS_PATH = os.path.join(STATIC_DIR, "airline-types.js")
_LOGIN_CARD_JS_PATH = os.path.join(STATIC_DIR, "login-card.js")
_SUBMIT_GUARD_JS_PATH = os.path.join(STATIC_DIR, "submit-guard.js")
_RELATIVE_TIME_JS_PATH = os.path.join(STATIC_DIR, "relative-time.js")
_QUICK_SWITCH_JS_PATH = os.path.join(STATIC_DIR, "quick-switch.js")
_VALUE_CONTROLS_JS_PATH = os.path.join(STATIC_DIR, "value-controls.js")

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
    POLL_COOLDOWN_SCRIPT_ROUTE: StaticAsset(_POLL_COOLDOWN_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    CONFIRM_SUBMIT_SCRIPT_ROUTE: StaticAsset(_CONFIRM_SUBMIT_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    THEME_PREVIEW_SCRIPT_ROUTE: StaticAsset(_THEME_PREVIEW_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    AIRLINE_TYPES_SCRIPT_ROUTE: StaticAsset(_AIRLINE_TYPES_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    LOGIN_CARD_SCRIPT_ROUTE: StaticAsset(_LOGIN_CARD_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    SUBMIT_GUARD_SCRIPT_ROUTE: StaticAsset(_SUBMIT_GUARD_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    RELATIVE_TIME_SCRIPT_ROUTE: StaticAsset(_RELATIVE_TIME_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    QUICK_SWITCH_SCRIPT_ROUTE: StaticAsset(_QUICK_SWITCH_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
    VALUE_CONTROLS_SCRIPT_ROUTE: StaticAsset(_VALUE_CONTROLS_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE),
}


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
