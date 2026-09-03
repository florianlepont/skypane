#!/usr/bin/env python3
"""companion/app.py — the SkyPane companion service entrypoint: a stdlib
`ThreadingHTTPServer` plus a hand-rolled route table, mirroring
`stub-server/byos_server.py`'s own shape (D-03, 06-CONTEXT.md: this is a
separate process, its own systemd unit — it never touches that vendored
device-protocol server).

Whole-site auth gate (D-02): every route except the login routes, the
stylesheet, and the theme-toggle POST calls `Handler.require_session()`
as its first statement and returns immediately when the session is
invalid — this file is the single place that gate is enforced, not each
page module. This same exemption list also decides the caching scope on
byte-served responses (`Handler.send_bytes()`'s `public` parameter): a
route not in this list must never be advertised to a shared/intermediary
cache as storable, so the two lists are not allowed to silently drift
apart.

This service binds all interfaces (0.0.0.0), exactly like
`stub-server/byos_server.py` already does in production — loopback
restriction is enforced at the firewall/reverse-proxy layer (ufw + Caddy)
rather than in the app, matching `deploy/skypane-byos.service`'s own
documented discipline (plan 06-11 adds the matching ufw deny for this
service's own port).

This service never writes the poll pipeline's own persisted flight-state
file — `server.poll_loop.run_once()` is that file's one legitimate writer
(06-RESEARCH.md's Pitfall 5). `POST /poll-now` calls `run_once()`
directly, in-process: the exact same production code path the systemd
timer already runs on its own 30-second cadence, never a second process
and never a re-implementation.

Startup refusal: `main()` calls `companion.auth.configured_password()`
before binding the socket. A missing password fails closed — this
service must never come up with authentication silently disabled.
"""
import email.message
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from PIL import Image

# Same repo-root sys.path bootstrap as server/poll_loop.py, so
# `server.device_config`/`server.history_db`/`server.poll_loop` all
# resolve whether this file is imported as a package or executed
# directly (`server/.venv/bin/python3 companion/app.py`, the exact
# invocation the systemd unit uses). Quick task 260903-c4o retired this
# file's only two `server.panel_preview` call sites along with the
# /preview.png route they served — that module is no longer imported
# here.
_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from companion import auth, illustration_normalize, layout  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page,
    config_page,
    health_page,
    history_page,
)
from server import device_config, history_db  # noqa: E402
from server.plane import illustrations  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

DEFAULT_PORT = 8643
GALLERY_DIRNAME = "gallery"
GALLERY_DEFAULT_LIMIT = 30
POLL_COOLDOWN_S = 45  # D-17: tens of seconds, a double-click guard, not an abuse rate-limit.
THEME_COOKIE_MAX_AGE_S = 365 * 24 * 3600
MAX_FORM_BYTES = 8192  # far more than any form on this site needs (Pitfall/T-06-05-07).
# quick task 260902-v26: comfortably above any real high-resolution
# transparent aircraft PNG — every vendored asset in
# server/assets/icons/illustrations/ is well under this — while bounding
# a single request's peak memory to a few MB on a CX22-class VPS.
# Enforcing this size is the caller's job (Handler._read_upload_body(),
# plan 02's Task 2), not parse_single_uploaded_file()'s own.
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024
# WR-03: bounds how long a single connection's socket reads (including the
# unauthenticated POST /login body read in read_form()) may block on a
# slow/stalled client. Without this, a client that opens a connection with
# a plausible Content-Length and then trickles (or never sends) the body
# ties up a ThreadingHTTPServer worker thread indefinitely — a slowloris-
# shaped DoS reachable before any credential check. 30s comfortably covers
# a slow real client on this LAN/VPN deployment while bounding the worst case.
REQUEST_SOCKET_TIMEOUT_S = 30

LOGIN_ROUTE = "/login"
STYLE_ROUTE = "/static/style.css"
# Authoritative route value — companion/pages/health_page.py's
# BATTERY_TREND_SCRIPT_SRC (plan 06.5-02) must equal this exactly; that
# plan adds a check asserting the two stay in sync. Do not edit one
# without the other.
SCRIPT_ROUTE = "/static/battery-trend.js"
# Authoritative route value — companion/layout.py's NAV_DROPDOWN_SCRIPT_SRC
# (plan 06.6.1-05) must equal this exactly; that plan's Task 3 asserts the
# two stay in sync, mirroring SCRIPT_ROUTE/BATTERY_TREND_SCRIPT_SRC's own
# established pair above.
NAV_SCRIPT_ROUTE = "/static/nav-dropdown.js"
# 06.6.3: four more authoritative route values — each must equal
# companion/layout.py's matching *_SCRIPT_SRC constant exactly (this
# plan's own checks assert the equality), mirroring the
# SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
DIRTY_STATE_SCRIPT_ROUTE = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_ROUTE = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_ROUTE = "/static/copy-button.js"
FRESHNESS_SCRIPT_ROUTE = "/static/freshness.js"
# D-20 (06.6.4.1-02): companion/layout.py's PANEL_LOOKUP_SCRIPT_SRC must
# equal this exactly, mirroring the SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
PANEL_LOOKUP_SCRIPT_ROUTE = "/static/panel-lookup.js"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# rather than re-typed, exactly like RUNWAY_IMAGE_ROUTE_PREFIX and the
# FLASH_KEY_* constants below (D-26, 06.6.4.1-07: renamed from "/config"
# to "/settings"; the old path now 404s by design, no redirect).
SETTINGS_ROUTE = config_page.SETTINGS_ROUTE
POLL_ROUTE = "/poll-now"
THEME_ROUTE = "/ui-theme"
LOGOUT_ROUTE = "/logout"
# D-22 (06.6.4.1-08): the standalone Preview HTML page is retired — its
# entire content moved into History (06.6.4.1-05) — so this route is kept
# solely as a fixed-redirect source, not a page route. Named
# PREVIEW_PAGE_ROUTE (not PREVIEW_ROUTE) to say what it now is.
PREVIEW_PAGE_ROUTE = "/preview"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# exactly like the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
# D-15 (06.6.4.1-02): the Airlines gallery's per-variant illustration image
# route. Naming convention matches RUNWAY_IMAGE_ROUTE_PREFIX above.
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"

# The four flash-key string literals are defined exactly once, in
# companion/pages/config_page.py (plan 06-07's Task 2) — imported here
# under their historical FLASH_KEY_* names so every existing call site in
# this file (and companion/test_companion_app.py's own assertions against
# the literal query-string values) stays unchanged.
FLASH_KEY_SAVED = config_page.FLASH_SAVED
FLASH_KEY_SAVE_FAILED = config_page.FLASH_SAVE_FAILED
FLASH_KEY_POLL_TRIGGERED = config_page.FLASH_POLL_TRIGGERED
FLASH_KEY_POLL_COOLDOWN = config_page.FLASH_POLL_COOLDOWN
FLASH_KEY_POLL_FAILED = config_page.FLASH_POLL_FAILED
FLASH_KEY_POLL_ALREADY_RUNNING = config_page.FLASH_POLL_ALREADY_RUNNING
# quick task 260902-v26: the three illustration-replace flash keys are
# defined once in companion/pages/airlines_page.py (that module's own
# comment explains why, mirroring config_page.py's FLASH_* rebinding
# pattern above exactly).
FLASH_KEY_ILLUSTRATION_REPLACED = airlines_page.FLASH_ILLUSTRATION_REPLACED
FLASH_KEY_ILLUSTRATION_REJECTED = airlines_page.FLASH_ILLUSTRATION_REJECTED
FLASH_KEY_ILLUSTRATION_REPLACE_FAILED = airlines_page.FLASH_ILLUSTRATION_REPLACE_FAILED

# A fixed key -> 06-UI-SPEC.md-copy dictionary — the flash mechanism only
# ever renders one of these, never a value taken verbatim from the query
# string (T-06-05-05). FLASH_KEY_POLL_COOLDOWN's "{n}" is filled in with a
# server-computed remaining-seconds figure, never anything client-supplied.
FLASH_MESSAGES = {
    FLASH_KEY_SAVED: "Saved — will apply on the frame's next scheduled refresh.",
    FLASH_KEY_SAVE_FAILED: (
        "Couldn't save settings — please try again. If this keeps "
        "happening, check the companion service logs."),
    FLASH_KEY_POLL_TRIGGERED: (
        "Poll triggered — refresh this page in a few seconds to see the result."),
    FLASH_KEY_POLL_COOLDOWN: "Poll triggered recently — try again in {n}s.",
    FLASH_KEY_POLL_FAILED: (
        "Poll trigger failed — please try again. If this keeps happening, "
        "check the companion service logs."),
    FLASH_KEY_POLL_ALREADY_RUNNING: "A poll is already in progress — try again in a moment.",
    FLASH_KEY_ILLUSTRATION_REPLACED: (
        "Illustration replaced — will apply on the frame's next scheduled refresh."),
    # Actionable, states the real requirements in user terms, and never
    # echoes a server path or any part of the uploaded file back to the
    # client (T-v26-02-08) — validate_illustration_file()'s own problem
    # strings go to the service log only, never into this copy.
    FLASH_KEY_ILLUSTRATION_REJECTED: (
        "Couldn't use that image — upload a transparent PNG that's at "
        "least 1200 pixels wide and landscape (wider than tall)."),
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: (
        "Couldn't replace the illustration — please try again. If this "
        "keeps happening, check the companion service logs."),
}

# 06.6.2-06 (UXA-07): every FLASH_KEY_* -> the ARIA role its rendered
# flash banner should carry — "alert" (assertive) for a genuine failure,
# "status" (polite) for everything else, chosen by real severity rather
# than one role for every outcome. page_context() resolves this into
# ctx["flash_role"], threaded into every layout.flash_banner(role=...)
# call site below.
FLASH_ROLES = {
    FLASH_KEY_SAVED: "status",
    FLASH_KEY_SAVE_FAILED: "alert",
    FLASH_KEY_POLL_TRIGGERED: "status",
    FLASH_KEY_POLL_COOLDOWN: "status",
    FLASH_KEY_POLL_FAILED: "alert",
    # Informational, not itself a failure — a different session/tab is
    # already legitimately running a poll.
    FLASH_KEY_POLL_ALREADY_RUNNING: "status",
    # Success and rejection are both user-facing outcomes of a normal
    # upload flow (polite "status"); an unexpected server-side failure
    # takes the assertive "alert" role, matching FLASH_KEY_SAVE_FAILED's
    # own treatment above.
    FLASH_KEY_ILLUSTRATION_REPLACED: "status",
    FLASH_KEY_ILLUSTRATION_REJECTED: "status",
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: "alert",
}

_STYLE_CSS_PATH = os.path.join(_HERE, "static", "style.css")
_BATTERY_TREND_JS_PATH = os.path.join(_HERE, "static", "battery-trend.js")
_NAV_DROPDOWN_JS_PATH = os.path.join(_HERE, "static", "nav-dropdown.js")
_DIRTY_STATE_JS_PATH = os.path.join(_HERE, "static", "dirty-state.js")
_LIST_FILTER_JS_PATH = os.path.join(_HERE, "static", "list-filter.js")
_COPY_BUTTON_JS_PATH = os.path.join(_HERE, "static", "copy-button.js")
_FRESHNESS_JS_PATH = os.path.join(_HERE, "static", "freshness.js")
_PANEL_LOOKUP_JS_PATH = os.path.join(_HERE, "static", "panel-lookup.js")
_RUNWAY_IMAGE_DIR = os.path.join(_HERE, "static")

# Process-global, not per-session (06-RESEARCH.md Pitfall 8's own login
# analogue) — D-01/D-02 mean there are no distinct users for a per-session
# counter to key on.
LOGIN_THROTTLE = auth.LoginThrottle()

# Same process-global-singleton shape as LOGIN_THROTTLE above (UXA-15):
# a single, module-level `threading.Lock()` guarding the entire
# check-cooldown -> run_once() -> mark-triggered sequence in
# _handle_poll_now(), so two POST /poll-now requests arriving before the
# first has finished can never both call poll_loop.run_once(). Correct
# because main() runs exactly one ThreadingHTTPServer in a single OS
# process (no worker/replica config anywhere in
# deploy/skypane-companion.service) — a cross-process or file-based lock
# would be the wrong tool here.
_POLL_LOCK = threading.Lock()

_PAGE_TITLES = {
    "/settings": "Settings",
    "/health": "Health",
    "/airlines": "Airlines",
    "/history": "History",
    # 06.6.4.1-08 (D-22): "/preview" entry removed — the Preview page is
    # retired (PREVIEW_PAGE_ROUTE now only redirects); NAV_TABS shrinks to
    # match in companion/layout.py.
}

# 06.6.2-07 (UXA-03): the login card's one-sentence purpose text, shown
# instead of the generic "Companion Access" copy the old page_shell()-based
# login reused.
LOGIN_EXPLANATION_TEXT = "Sign in to manage this device's settings."

# Quick task 260903-peo (UIR-16): the 404 page's title and one-sentence
# purpose, promoted to module constants matching LOGIN_EXPLANATION_TEXT's
# own precedent for user-facing copy. `layout.page_header()` escapes both
# when it renders them — these are always plain strings, never
# pre-escaped markup.
NOT_FOUND_TITLE = "Page not found."
NOT_FOUND_PURPOSE_TEXT = "The page you requested doesn't exist or may have moved."


def _validated_next_route(candidate):
    """Validate a caller-supplied `next` redirect target (a GET query
    value or a POST form value) against `layout.NAV_TABS`'s known
    routes — 06.6.2-07 (T-06.6.2-12, high-severity open-redirect
    mitigation).

    This is deliberately an exact-membership equality test against the
    set of NAV_TABS route literals — never `str.startswith("/")`, never
    URL-parsed, never regex-matched. There is no parsing logic here an
    attacker-controlled value could exploit: `candidate` either equals
    one of the known routes byte-for-byte, or it is discarded (returns
    `None`). A scheme-relative value (`//evil.example`), an absolute URL
    (`https://evil.example`), a path-traversal-shaped value, or any
    value not byte-identical to a real NAV_TABS route all fail this
    test and fall back to the caller's own safe default
    (`SETTINGS_ROUTE` on a successful POST, the bare `LOGIN_ROUTE` on an
    unauthenticated GET) — an open redirect is structurally impossible
    here, not merely discouraged. Deliberately not stated as a literal
    route count here (06.6.4.1-07): the allowlist is derived from
    NAV_TABS at runtime and self-adjusts whenever that tuple's own
    membership changes, so this docstring never needs a second edit
    when a route is added, renamed, or removed.

    Mirrors `Handler._referring_tab()`'s own exact-membership allowlist
    shape, but is a module-level function (not a method) since it must
    validate both a query-string value (GET) and a form value (POST),
    neither of which is `self.headers.get("Referer")`.
    """
    allowed = {route for route, _ in layout.NAV_TABS}
    return candidate if candidate in allowed else None


def _resolve_flash_text(flash_key, state_dir):
    if flash_key not in FLASH_MESSAGES:
        return None
    template = FLASH_MESSAGES[flash_key]
    if flash_key == FLASH_KEY_POLL_COOLDOWN:
        return template.format(n=poll_cooldown_remaining(state_dir))
    return template


def poll_cooldown_remaining(state_dir):
    """Seconds remaining before another `POST /poll-now` is allowed, or 0
    when the cooldown has elapsed. Server-global and persisted in
    `history.db`'s meta table (not the session cookie), so a second
    browser tab cannot bypass it and a service restart does not reset it
    (D-17, 06-RESEARCH.md Pitfall 8).
    """
    with history_db.open_db(state_dir) as conn:
        value = history_db.get_meta(conn, history_db.META_LAST_POLL_TRIGGER)
    if not value:
        return 0
    try:
        last_triggered = int(value)
    except (TypeError, ValueError):
        return 0
    remaining = POLL_COOLDOWN_S - (time.time() - last_triggered)
    return int(remaining) if remaining > 0 else 0


def mark_poll_triggered(state_dir):
    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_POLL_TRIGGER, str(int(time.time())))


def gallery_entries(state_dir, limit=GALLERY_DEFAULT_LIMIT):
    """The newest `limit` gallery filenames (name-descending — plan 06-10
    names them by timestamp, so lexical order is chronological), filtered
    to files ending in the PNG extension. A missing gallery directory
    returns an empty list rather than raising.
    """
    gallery_dir = os.path.join(state_dir, GALLERY_DIRNAME)
    try:
        entries = sorted(
            (entry.name for entry in os.scandir(gallery_dir)
             if entry.is_file() and entry.name.endswith(".png")),
            reverse=True,
        )
    except OSError:
        return []
    return entries[:limit]


def gallery_bytes(state_dir, requested):
    """Return the named gallery file's bytes only when `requested` is an
    exact match against a real `os.scandir()` listing of the gallery
    directory — the requested name is never joined onto a filesystem path
    (T-06-05-02); an unmatched, traversal-shaped, or otherwise unknown
    name returns None.
    """
    gallery_dir = os.path.join(state_dir, GALLERY_DIRNAME)
    try:
        for entry in os.scandir(gallery_dir):
            if entry.is_file() and entry.name == requested:
                with open(entry.path, "rb") as fh:
                    return fh.read()
    except OSError:
        return None
    return None


def _runway_image_filename(runway_id):
    """The single, mechanical place the on-disk naming convention (D-03's
    asset contract) is expressed: `runway-{runway_id}.png`.
    """
    return "runway-%s.png" % runway_id


def _runway_image_path(runway_id, image_dir=_RUNWAY_IMAGE_DIR):
    return os.path.join(image_dir, _runway_image_filename(runway_id))


def runway_images_available(image_dir=_RUNWAY_IMAGE_DIR):
    """The subset of `device_config.RUNWAY_IDS` that currently has a real
    `runway-{id}.png` file on disk. A missing `image_dir`, a missing
    individual file, or any other OS-level error while checking
    (permissions, a symlink loop) is not an error — it is D-03's
    documented graceful-fallback state, so this never raises:
    `os.path.isfile()` itself already swallows `OSError`/`ValueError`
    and returns `False`. The result is bounded by the fixed `RUNWAY_IDS`
    registry (iterated, never `os.scandir()`-ed), so it can never report
    an image for an id that isn't a real runway.
    """
    available = set()
    for runway_id in device_config.RUNWAY_IDS:
        if os.path.isfile(_runway_image_path(runway_id, image_dir)):
            available.add(runway_id)
    return available


def _illustration_filenames():
    """The known-safe membership set `Handler._serve_illustration_image()`
    validates a requested key against BEFORE any filesystem path is
    constructed (D-15) — `illustrations.target_filenames()` wrapped in a
    `frozenset`. `target_filenames()` performs no I/O, but materialising it
    once at import time (rather than per request) makes the "one closed,
    server-controlled list" property visible at a glance.
    """
    return frozenset(illustrations.target_filenames())


_ILLUSTRATION_FILENAMES = _illustration_filenames()


def parse_single_uploaded_file(content_type, body):
    """Parse a `multipart/form-data` body known to hold exactly one file
    part, returning that part's raw payload `bytes`, or `None` for
    anything that doesn't match that exact shape. Never raises, for any
    input including `None`/empty/truncated/binary-garbage `body` and a
    `None` `content_type` — every failure mode degrades to `None`
    (quick task 260902-v26, matching `read_form()`'s own never-raises
    discipline above).

    This is deliberately NOT a general multipart parser. The one form
    this route ever serves carries a single file input and nothing else,
    so refusing anything but exactly one part is the smallest
    provably-correct behaviour, not an arbitrary restriction — a second
    part, a missing part, or a malformed delimiter structure all return
    `None` rather than being tolerated or best-effort-parsed.

    The part's header block (its declared filename, field name, and
    declared media type) is discarded entirely and never parsed — by
    construction, not merely by convention, this function has no code
    path that reads a client-declared filename. The destination path an
    upload is eventually written to is derived solely from the URL key
    the caller has already membership-validated (`_ILLUSTRATION_FILENAMES`),
    never from anything in this body. Likewise, a client-declared media
    type is not evidence of anything: `illustrations.validate_illustration_
    file()`'s own Pillow-based header read is the sole authority on
    "is this really an image", not this parser and not this header block.

    Enforcing `MAX_ILLUSTRATION_UPLOAD_BYTES` is the caller's
    responsibility (`Handler._read_upload_body()`, plan 02's Task 2), not
    this function's — this parser only ever sees bytes the caller already
    decided to hand it and never independently bounds anything by size.

    Boundary/media-type parsing uses `email.message.Message` (assign the
    raw header value, then `get_content_type()`/`get_param("boundary")`)
    — the non-deprecated stdlib replacement for `cgi.parse_header` on
    this project's pinned Python 3.11 venv. Do not "modernise" this back
    to the `cgi` module: it is deprecated there and removed outright in
    Python 3.13.
    """
    try:
        message = email.message.Message()
        message["content-type"] = content_type
        if message.get_content_type() != "multipart/form-data":
            return None
        boundary = message.get_param("boundary")
        if not isinstance(boundary, str) or not boundary:
            return None
        boundary_bytes = boundary.encode("ascii")
        if len(boundary_bytes) > 70:  # RFC 2046 boundary length ceiling.
            return None

        delimiter = b"--" + boundary_bytes
        segments = body.split(delimiter)
        # Exactly one part: a preamble, the part itself, and an epilogue.
        # Zero parts, two-or-more parts, and a missing closing delimiter
        # all produce a different segment count and are rejected here.
        if len(segments) != 3:
            return None
        preamble, part, epilogue = segments
        if preamble.strip(b"\r\n \t") != b"":
            return None
        if not epilogue.startswith(b"--"):
            return None

        if not part.startswith(b"\r\n"):
            return None
        part = part[2:]
        header_block, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            return None
        del header_block  # deliberately discarded — see docstring above.

        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if not payload:
            return None
        return payload
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "skypane-companion"
    args = None
    # WR-03: socketserver.StreamRequestHandler honours this attribute by
    # calling self.connection.settimeout(self.timeout) before setup, so a
    # stalled read anywhere on the connection (in particular the
    # unauthenticated POST /login body read) raises socket.timeout instead
    # of blocking the worker thread forever.
    timeout = REQUEST_SOCKET_TIMEOUT_S

    # --- response helpers -------------------------------------------

    def _send_hardening_headers(self):
        """WR-02: baseline hardening headers applied to every response.

        This is an authenticated admin panel (device config, poll
        trigger, LED control) reachable from the public internet per
        this module's own docstring — with no X-Frame-Options/CSP an
        authenticated page can be framed by a third-party site for
        clickjacking, and with no X-Content-Type-Options a MIME-sniffing
        quirk is one upstream misconfiguration away from an XSS vector.
        """
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")

    def send_html(self, code, html_str):
        body = html_str.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, code, content_type, payload, cache_seconds=0, public=False):
        """`public` (default False, fail-closed) decides whether a cached
        response is advertised as shared-cacheable. A shared/intermediary
        cache has no knowledge of the session cookie `require_session()`
        checked — telling it a response may be stored means it can later
        replay that response to a different client that never presented
        the cookie. Callers must therefore explicitly opt into shared
        cacheability by passing a true `public` value; a route that is
        genuinely session-gated should never need to (WR-02,
        06.4-REVIEW.md).
        """
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if cache_seconds > 0:
            scope = "public" if public else "private"
            self.send_header(
                "Cache-Control", "%s, max-age=%d" % (scope, cache_seconds))
        else:
            self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(payload)

    def redirect(self, location, set_cookie=None):
        self.send_response(303)
        self.send_header("Location", location)
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # --- auth ----------------------------------------------------------

    def _is_authenticated(self):
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        return auth.verify_session_token(cookies.get(auth.SESSION_COOKIE_NAME))

    def require_session(self):
        if self._is_authenticated():
            return True
        # 06.6.2-07 (UXA-03): carry the originally-requested protected
        # route through the login round-trip via an allowlisted `next`
        # query parameter, so a successful login returns the user to
        # the exact route they asked for instead of always /settings.
        # _validated_next_route() (T-06.6.2-12) is the sole gate — an
        # unrecognised requested_path is silently discarded and the
        # redirect degrades to the bare LOGIN_ROUTE exactly as before
        # this change.
        requested_path = urlsplit(self.path).path
        next_route = _validated_next_route(requested_path)
        if next_route:
            # safe="" (never the default safe="/") so the encoded value
            # is unambiguously a single query-string token — matching
            # this plan's own acceptance criteria ("/login?next=%2Fhealth",
            # not "/login?next=/health").
            self.redirect(
                "%s?next=%s" % (LOGIN_ROUTE, quote(next_route, safe="")))
        else:
            self.redirect(LOGIN_ROUTE)
        return False

    def _resolved_ui_theme(self):
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        return layout.ui_theme_from_cookie(cookies)

    # --- form / query parsing -------------------------------------------

    def read_form(self):
        """Read the request body as a `application/x-www-form-urlencoded`
        form, capped at MAX_FORM_BYTES. An oversized or undecodable body
        degrades to an empty form rather than raising (T-06-05-07) — the
        remainder of an oversized body is still drained from the socket
        so a persistent connection is not left in a corrupted state.

        WR-03: `Handler.timeout` (set on the class) bounds every socket
        read below, including this one — reachable pre-auth from
        `POST /login`. A stalled/slow-drip body triggers `socket.timeout`
        here, which is treated exactly like any other malformed-body case
        (degrade to an empty form) rather than propagating and blocking
        the worker thread indefinitely.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(min(length, MAX_FORM_BYTES + 1))
            if length > MAX_FORM_BYTES:
                remaining = length - len(raw)
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                return {}
        except socket.timeout:
            return {}
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {}
        parsed = parse_qs(text, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items() if values}

    def _read_upload_body(self):
        """Read the POST body for an illustration-replace request, bounded
        by `MAX_ILLUSTRATION_UPLOAD_BYTES` (quick task 260902-v26,
        T-v26-02-03) — deliberately mirrors `read_form()`'s own draining
        discipline above rather than reusing it (`read_form()` is
        urlencoded-only and capped much lower). Returns `None` when
        `Content-Length` is absent, unparseable, non-positive, or exceeds
        the cap; an over-cap body still has its remainder drained from
        the socket in bounded chunks first, so a persistent connection is
        never left mid-body. `socket.timeout` (bounded by `Handler.timeout`,
        WR-03) is treated exactly like any other malformed/over-cap body.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            return None
        if length <= 0:
            return None
        try:
            raw = self.rfile.read(min(length, MAX_ILLUSTRATION_UPLOAD_BYTES + 1))
            if length > MAX_ILLUSTRATION_UPLOAD_BYTES:
                remaining = length - len(raw)
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                return None
        except socket.timeout:
            return None
        return raw

    def page_context(self):
        """Build the `ctx` dict every page module's render()/handle_post()
        receives — documented in full in companion/pages/__init__.py.
        """
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query)
        flash_key = params.get("flash", [None])[0]
        state_dir = self.args.state_dir
        now = history_db.utc_now_iso()
        # WR-04: compute once per request (fail-closed to None on any
        # unanticipated exception — see health_page.safe_health_state()'s
        # docstring) and thread both the derived severity and the full
        # state dict into ctx, so health_page.render() can reuse the
        # exact same DB-read snapshot instead of re-deriving it from a
        # second, non-atomic set of reads when the user is on /health.
        health_state = health_page.safe_health_state(state_dir, now)
        return {
            "state_dir": state_dir,
            "ui_theme": self._resolved_ui_theme(),
            "device_config": device_config.load_device_config(state_dir),
            "flash": _resolve_flash_text(flash_key, state_dir),
            # 06.6.2-06 (UXA-07): the ARIA role the resolved flash text
            # should render with, looked up from the same flash_key this
            # method already resolved above — "status" for any key not
            # in FLASH_ROLES (including no flash at all), the same
            # safe-fallback direction flash_banner()'s own role
            # whitelist uses.
            "flash_role": FLASH_ROLES.get(flash_key, "status"),
            "poll_cooldown_remaining": poll_cooldown_remaining(state_dir),
            "gallery_entries": gallery_entries(state_dir),
            "runway_images": runway_images_available(),
            # 06.6.1-04: computed here, not by a nav renderer, because
            # companion/pages/__init__.py forbids a page module importing
            # another page module — this file already imports health_page
            # legitimately (the runway_images entry above set the same
            # precedent in Phase 06.4), so this is the boundary's intended
            # crossing point. health_page.safe_health_state() (called
            # above to build `health_state`) is contractually
            # never-raising *because* this line runs on every
            # authenticated page render.
            #
            # 06.6.2-06 (UXA-14): this key was previously a boolean
            # named for the old anomaly_active() call; it is now the
            # "ok"/"warn"/"error" severity string. WR-04: sourced from
            # the single `health_state` computed above (falling back to
            # "ok" when that computation failed) rather than a second,
            # independent health_page.health_severity() call — every
            # consumer below moved together in the earlier commit that
            # introduced this key, and this one collapses the
            # once-per-page-render duplicate DB read that commit left
            # behind.
            "health_severity": health_state["severity"] if health_state else "ok",
            "health_state": health_state,
            "now": now,
        }

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        """The shared 404 body, reached from ELEVEN call sites across this
        module — including the two PRE-AUTH static-asset delegates,
        `_serve_stylesheet()` and `_serve_script_file()`, both reached
        before any `require_session()` gate because D-02 exempts static
        assets from the session gate entirely. Quick task 260903-peo
        (UIR-16): the heading now uses the shared `layout.page_header()`
        component (the 30px serif `.page-title` role every other
        authenticated page opens with) instead of the old bare
        `<h1 class="text-heading">` (the 20px section-heading role,
        wrong here).

        The Health nav dot is threaded through `health_alert` on the
        `self._is_authenticated()` branch ONLY — that predicate (L549) is
        a pure bool check with no side effect, unlike `require_session()`
        (which redirects). Computing severity unconditionally would leak
        Health's warn/error state to an unauthenticated caller landing on
        either of the two pre-auth paths named above. `self.page_context()`
        is deliberately NOT called here: it performs six-plus SQLite
        reads, a device-config load and a filesystem scan for a single
        value on what is, structurally, an error path.
        """
        health_alert = None
        if self._is_authenticated():
            health_state = health_page.safe_health_state(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = health_state["severity"] if health_state else "ok"
        body = (
            layout.page_header(NOT_FOUND_TITLE, purpose=NOT_FOUND_PURPOSE_TEXT)
            + '<p class="text-body"><a href="%s">Back to Settings</a></p>' % SETTINGS_ROUTE
        )
        return layout.page_shell(
            title="Not Found", active="", body=body,
            ui_theme=self._resolved_ui_theme(), health_alert=health_alert)

    def _login_body(self, error=None, lockout_seconds=None, next_route=None):
        """The login card's inner markup — 06.6.2-07 (UXA-03).

        `next_route` (already validated by `_validated_next_route()` at
        every call site — never a raw, unvalidated value) is carried
        through a hidden form field so a failed login attempt does not
        lose the originally-requested destination, and is only ever
        rendered when truthy.

        The lockout/error paragraph (whichever applies) carries
        `role="alert"` so assistive tech announces it immediately
        rather than waiting for the user to discover it visually. The
        password field carries `autocomplete="current-password"`
        (password-manager support, T-06.6.2-14) and `autofocus`
        unconditionally — this is the one page in the app with a
        single, always-relevant focus target, so no error-conditional
        branching is needed.
        """
        parts = [
            '<h1 class="page-title">SkyPane</h1>',
            '<p class="text-body">%s</p>' % layout.escape_html(LOGIN_EXPLANATION_TEXT),
        ]
        if lockout_seconds:
            parts.append(
                '<p class="text-body" role="alert">%s</p>'
                % layout.escape_html(
                    "Too many attempts — try again in %ds." % lockout_seconds))
        elif error:
            parts.append(
                '<p class="text-body" role="alert">%s</p>'
                % layout.escape_html(error))
        next_field_html = (
            '<input type="hidden" name="next" value="%s">'
            % layout.escape_html(next_route)) if next_route else ""
        parts.append(
            '<form method="post" action="%s">'
            "%s"
            '<label for="password">Password</label>'
            '<input type="password" id="password" name="password" '
            'autocomplete="current-password" autofocus required>'
            '<button type="submit">Sign in</button>'
            "</form>" % (LOGIN_ROUTE, next_field_html)
        )
        return "".join(parts)

    def _render_login_page(self, error=None, lockout_seconds=None, next_route=None):
        body = self._login_body(
            error=error, lockout_seconds=lockout_seconds, next_route=next_route)
        return layout.login_shell(body, ui_theme=self._resolved_ui_theme())

    def _serve_stylesheet(self):
        try:
            with open(_STYLE_CSS_PATH, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        # One of the three D-02 gate exemptions named in this module's
        # docstring (login routes, stylesheet, theme-toggle POST): no
        # per-user content, identical for every client, so it is
        # legitimately shared-cacheable.
        return self.send_bytes(200, "text/css", payload, cache_seconds=300, public=True)

    def _serve_script_file(self, abs_path):
        """Serve one fixed JavaScript file, pre-auth, structurally
        identical to _serve_stylesheet() above. Unlike
        _serve_gallery_image(), this resolves a single fixed module
        constant (`abs_path` is always one of this module's own path
        constants — _BATTERY_TREND_JS_PATH or _NAV_DROPDOWN_JS_PATH — never
        a client-supplied segment) and never joins a request-derived
        segment into a filesystem path, so it has no path-traversal
        surface. Shared body for _serve_battery_trend_script() and
        _serve_nav_dropdown_script() below.

        `public=True`: this route is pre-auth and content-identical for
        every client (like `_serve_stylesheet()`, opted in the same way),
        so shared/intermediary caching is safe — matches
        `send_bytes()`'s WR-02 fix (quick task 260829-0rl), which made
        `private` the default for every OTHER route and left this one an
        accidental straggler only because this method predates that
        parameter existing at all.
        """
        try:
            with open(abs_path, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        # text/javascript is the sole current-standard MIME type for
        # JavaScript per RFC 9239 (2022), which obsoletes RFC 4329's older
        # application/-prefixed form — deliberately not used here.
        return self.send_bytes(200, "text/javascript", payload, cache_seconds=300, public=True)

    def _serve_battery_trend_script(self):
        """Serve companion/static/battery-trend.js, pre-auth. Thin
        delegate onto _serve_script_file() — kept as its own named method
        (rather than inlined at the do_GET call site) since an existing
        check references it by name.
        """
        return self._serve_script_file(_BATTERY_TREND_JS_PATH)

    def _serve_nav_dropdown_script(self):
        """Serve companion/static/nav-dropdown.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_battery_trend_script()'s
        shape exactly.
        """
        return self._serve_script_file(_NAV_DROPDOWN_JS_PATH)

    def _serve_dirty_state_script(self):
        """Serve companion/static/dirty-state.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_DIRTY_STATE_JS_PATH)

    def _serve_list_filter_script(self):
        """Serve companion/static/list-filter.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_LIST_FILTER_JS_PATH)

    def _serve_copy_button_script(self):
        """Serve companion/static/copy-button.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_COPY_BUTTON_JS_PATH)

    def _serve_freshness_script(self):
        """Serve companion/static/freshness.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_FRESHNESS_JS_PATH)

    def _serve_panel_lookup_script(self):
        """Serve companion/static/panel-lookup.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_PANEL_LOOKUP_JS_PATH)

    def _serve_gallery_image(self, requested):
        payload = gallery_bytes(self.args.state_dir, requested)
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # This route sits behind do_GET()'s require_session() gate, so it
        # deliberately relies on send_bytes()'s non-shared (private)
        # default rather than opting into shared cacheability.
        return self.send_bytes(200, "image/png", payload, cache_seconds=3600)

    def _serve_runway_image(self, runway_id):
        # Membership test FIRST, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — T-06.4-02). An
        # unknown id and an unreadable file both return this same 404, so
        # a caller can never distinguish "not a real runway" from "no
        # image for a real runway" — leaking nothing about the
        # filesystem beyond the RUNWAY_IDS set the authenticated /settings
        # page already renders in full to the same caller.
        if runway_id not in device_config.RUNWAY_IDS:
            return self.send_html(404, self._not_found_page())
        path = _runway_image_path(runway_id)
        try:
            with open(path, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _serve_illustration_image(self, key):
        # Membership test FIRST, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — same shape as
        # _serve_runway_image() above, D-15). An unknown key, a missing
        # file and a malformed/unreadable asset all return this same 404
        # (quick task 260902-req-02, T-260902req-05) — a caller can never
        # distinguish "not a real illustration" from "no file for a real
        # one" from "normalization failed on this one file";
        # illustrations.resolved_illustration_path()'s own _UNSAFE_KEY_RE
        # check below is defence in depth, never a substitute for this
        # membership test.
        filename = key + ".png"
        if filename not in _ILLUSTRATION_FILENAMES:
            return self.send_html(404, self._not_found_page())
        # quick task 260902-v26: resolved_illustration_path() checks
        # {state_dir}/illustration_overrides/{key}.png first, falling back
        # to the vendored file — the same seam server.plane.illustrations.
        # select_illustration() goes through for the panel compositor
        # (plan 01). The *key set* this route accepts is still closed and
        # server-controlled (the membership test above); what changed
        # since 260902-req-02 is that the *bytes on disk* for an
        # overridden key may now have originated as a user upload
        # (POST /illustration/{key}.png, this route's sibling below, no
        # longer "never user-supplied image bytes" as this comment used to
        # claim). That is still safe to decode here because this route
        # only ever sees bytes this server itself re-encoded through
        # Pillow in _handle_illustration_replace() after
        # validate_illustration_file() passed — never a client's raw
        # uploaded bytes — and because a decode failure on either an
        # override or a vendored file still degrades to this same uniform
        # 404 (T-260902req-05), never a 500.
        path = illustrations.resolved_illustration_path(key, self.args.state_dir)
        if path is None:
            return self.send_html(404, self._not_found_page())
        # T-260902req-06: cached_normalized_png_bytes() is lru_cache'd per
        # path+mtime, so a replaced/overridden asset (a changed mtime, or a
        # changed path entirely once an override first appears) is picked
        # up on the very next request, not decoded/re-encoded once and
        # left stale.
        try:
            payload = illustration_normalize.cached_normalized_png_bytes(path)
        except Exception:
            # Any decode/normalize failure on this one asset degrades to
            # the same 404 as a missing file (T-260902req-05), never a
            # 500 — the membership test above already proved this is a
            # known-safe key, whether it currently resolves to the
            # vendored file or a validated user override.
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _handle_illustration_replace(self, key):
        """POST /illustration/{key}.png — upload a replacement illustration
        (quick task 260902-v26, T-v26-02-*). This is the feature's entire
        security surface: the first untrusted file upload this codebase
        has ever handled. Steps run in this exact order; the ordering is
        the security property, not an implementation detail:

        1. Membership test on `key` FIRST, before any path is constructed
           or any byte of the body is read — validate-then-join, never
           sanitise-then-join, over the SAME closed 43-member set
           `_serve_illustration_image()` above already validates against
           (D-15). A traversal-shaped key is structurally unable to reach
           a path here, for exactly the reason that method's own comment
           documents.
        2. `_read_upload_body()` — bounded by `MAX_ILLUSTRATION_UPLOAD_
           BYTES`, draining an over-cap body so the connection is not
           left corrupted (T-v26-02-03).
        3. `parse_single_uploaded_file()` — a strict, stdlib-only,
           single-part multipart parse. The client's declared filename is
           never read by construction; the destination filename is always
           the already-membership-validated URL key, never anything from
           the request (T-v26-02-01).
        4. Write the raw payload to a temp file inside this key's override
           directory, named from the validated key plus this process's
           pid (never from the request), then run `illustrations.
           validate_illustration_file()` against it — the SAME validation
           every vendored illustration is held to (D-03/D-04). A non-empty
           problem list rejects the upload; the problem strings (which
           carry the server-side temp path) go to the service log only,
           never into the response (T-v26-02-08).
        5. Only once validated: decode with Pillow, convert to RGBA, and
           re-encode to a second temp file in the same directory. The
           client's original bytes are NEVER stored — this route only
           ever writes bytes this server's own Pillow encoder produced,
           so `_serve_illustration_image()` above (and, after the next
           poll cycle, the panel compositor via `select_illustration()`)
           only ever decode server-produced bytes, never a remote
           client's. This also strips any ancillary chunk, trailing
           appended data, or polyglot payload the original upload may
           have carried (T-v26-02-05).
        6. `os.replace()` the re-encoded temp onto the override path —
           atomic on one filesystem, since both temps live in the same
           override directory as the destination (T-v26-02-09) — then
           redirect with the success flash. Every failure branch unlinks
           both temp files before redirecting with the appropriate flash.

        No CSRF token: the session cookie's `SameSite=Strict` flag is this
        site's documented CSRF control for every state-changing POST
        (companion/auth.py:132) — this route follows that same,
        already-established posture (matching `POST /settings` and
        `POST /poll-now`) rather than inventing a second mechanism for
        itself alone (T-v26-02-07, accepted risk).
        """
        filename = key + ".png"
        if filename not in _ILLUSTRATION_FILENAMES:
            return self.send_html(404, self._not_found_page())

        raw = self._read_upload_body()
        if raw is None:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        payload = parse_single_uploaded_file(self.headers.get("Content-Type"), raw)
        if payload is None or len(payload) > MAX_ILLUSTRATION_UPLOAD_BYTES:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        state_dir = self.args.state_dir
        override_dir = illustrations.override_dir_for_state_dir(state_dir)
        try:
            os.makedirs(override_dir, exist_ok=True)
        except OSError:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))

        # Both temp files live alongside the destination (inside
        # override_dir) so the final os.replace() below stays a same-
        # filesystem, atomic rename — never a cross-filesystem copy.
        # Named from the validated key plus this process's pid plus a
        # fixed suffix, never from anything in the request.
        raw_tmp_path = os.path.join(
            override_dir, ".%s.%d.upload.tmp" % (key, os.getpid()))
        encoded_tmp_path = os.path.join(
            override_dir, ".%s.%d.encoded.tmp" % (key, os.getpid()))
        try:
            with open(raw_tmp_path, "wb") as fh:
                fh.write(payload)

            # This is what proves the bytes are really an image: it opens
            # the file with Pillow and reads format/dimensions from the
            # header, returning early on an over-cap pixel count before
            # any pixel data is decoded, so a decompression-bomb upload is
            # rejected without ever being expanded (T-v26-02-04).
            problems = illustrations.validate_illustration_file(raw_tmp_path)
            if problems:
                for problem in problems:
                    print("illustration replace rejected for %r: %s" % (key, problem))
                return self.redirect(
                    "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

            with Image.open(raw_tmp_path) as img:
                rgba = img.convert("RGBA")
                rgba.save(encoded_tmp_path, format="PNG")

            override_path = illustrations.override_path_for_key(key, state_dir)
            os.replace(encoded_tmp_path, override_path)
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACED))
        except Exception:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))
        finally:
            for tmp_path in (raw_tmp_path, encoded_tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _referring_tab(self):
        referer = self.headers.get("Referer", "")
        try:
            path = urlsplit(referer).path
        except ValueError:
            path = ""
        allowed = {route for route, _ in layout.NAV_TABS}
        return path if path in allowed else SETTINGS_ROUTE

    def _render_tab(self, route, page_module):
        if not self.require_session():
            return None
        ctx = self.page_context()
        body = page_module.render(ctx)
        flash_html = (
            layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
            if ctx["flash"] else None)
        html_doc = layout.page_shell(
            title=_PAGE_TITLES[route], active=route.lstrip("/"), body=body,
            ui_theme=ctx["ui_theme"], flash=flash_html,
            health_alert=ctx["health_severity"])
        return self.send_html(200, html_doc)

    # --- GET -------------------------------------------------------------

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            if self._is_authenticated():
                return self.redirect(SETTINGS_ROUTE)
            # 06.6.2-07 (UXA-03): a `?next=` query value survives the
            # require_session() redirect round-trip; validated here too
            # (not only on the POST path) so an unrecognised value never
            # even renders a hidden field for the user to resubmit.
            next_route = _validated_next_route(
                parse_qs(parsed.query).get("next", [None])[0])
            return self.send_html(200, self._render_login_page(next_route=next_route))

        if path == STYLE_ROUTE:
            return self._serve_stylesheet()

        # Pre-auth, matching /static/style.css: a static asset carries no
        # per-user or sensitive data, so gating it would add a session
        # round-trip for zero benefit (06.5-RESEARCH.md, Security Domain,
        # V2/V4 both "no"). NAV_SCRIPT_ROUTE (06.6.1-05) below is the same
        # reasoning, not a second justification.
        if path == SCRIPT_ROUTE:
            return self._serve_battery_trend_script()

        if path == NAV_SCRIPT_ROUTE:
            return self._serve_nav_dropdown_script()

        # 06.6.3: four more pre-auth static routes, same reasoning as
        # NAV_SCRIPT_ROUTE immediately above — a static asset carries no
        # per-user data, so gating it would add a session round-trip for
        # zero benefit.
        if path == DIRTY_STATE_SCRIPT_ROUTE:
            return self._serve_dirty_state_script()

        if path == LIST_FILTER_SCRIPT_ROUTE:
            return self._serve_list_filter_script()

        if path == COPY_BUTTON_SCRIPT_ROUTE:
            return self._serve_copy_button_script()

        if path == FRESHNESS_SCRIPT_ROUTE:
            return self._serve_freshness_script()

        if path == PANEL_LOOKUP_SCRIPT_ROUTE:
            return self._serve_panel_lookup_script()

        if path == SETTINGS_ROUTE:
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = config_page.render(ctx)
            flash_html = (
                layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
                if ctx["flash"] else None)
            return self.send_html(200, layout.page_shell(
                title="Settings", active="settings", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html,
                health_alert=ctx["health_severity"]))

        if path == "/health":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = health_page.render(ctx)
            flash_html = (
                layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
                if ctx["flash"] else None)
            return self.send_html(200, layout.page_shell(
                title="Health", active="health", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html,
                health_alert=ctx["health_severity"]))

        if path == "/airlines":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = airlines_page.render(ctx)
            flash_html = (
                layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
                if ctx["flash"] else None)
            return self.send_html(200, layout.page_shell(
                title="Airlines", active="airlines", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html,
                health_alert=ctx["health_severity"]))

        if path == "/history":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = history_page.render(ctx)
            flash_html = (
                layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
                if ctx["flash"] else None)
            return self.send_html(200, layout.page_shell(
                title="History", active="history", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html,
                health_alert=ctx["health_severity"]))

        if path == PREVIEW_PAGE_ROUTE:
            if not self.require_session():
                return None
            # D-22: the Preview page is retired — History absorbed all of
            # its content (06.6.4.1-05) — so this route now exists solely
            # to send a stale bookmark/link somewhere useful. The
            # redirect target is a fixed literal, never derived from a
            # query parameter, form value, Referer header, or
            # _validated_next_route()'s allowlisted next-route mechanism
            # above: that mechanism exists to honour a caller's requested
            # *login* destination and is allowlisted for that reason,
            # whereas this route has exactly one correct destination, and
            # consulting any request value here would turn a fixed
            # redirect into an open one. self.redirect() already emits
            # this site's one 302-class status for every redirect (303),
            # matching D-22's requirement.
            return self.redirect("/history")

        if path.startswith(GALLERY_ROUTE_PREFIX):
            if not self.require_session():
                return None
            return self._serve_gallery_image(path[len(GALLERY_ROUTE_PREFIX):])

        if path.startswith(RUNWAY_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            runway_id = path[len(RUNWAY_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._serve_runway_image(runway_id)

        if path.startswith(ILLUSTRATION_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            key = path[len(ILLUSTRATION_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._serve_illustration_image(key)

        return self.send_html(404, self._not_found_page())

    # --- POST --------------------------------------------------------------

    def _handle_login_post(self):
        # 06.6.2-07 (UXA-03/T-06.6.2-12): read and validate `next` before
        # the lockout/password checks so it survives every branch below
        # (lockout, incorrect password, and success) — a failed attempt
        # must not lose the originally-requested destination.
        form = self.read_form()
        next_route = _validated_next_route(form.get("next"))
        if LOGIN_THROTTLE.locked_out():
            remaining = LOGIN_THROTTLE.seconds_remaining()
            return self.send_html(429, self._render_login_page(
                lockout_seconds=remaining, next_route=next_route))
        submitted = form.get("password", "")
        if auth.password_ok(submitted):
            LOGIN_THROTTLE.record_success()
            token = auth.issue_session_token()
            return self.redirect(
                next_route or SETTINGS_ROUTE,
                set_cookie=auth.session_set_cookie_header(token))
        LOGIN_THROTTLE.record_failure()
        return self.send_html(401, self._render_login_page(
            error="Incorrect password. Try again.", next_route=next_route))

    def _handle_poll_now(self):
        # UXA-15: non-blocking acquire, never a timeout (06.6.2-RESEARCH.md).
        if not _POLL_LOCK.acquire(blocking=False):
            # Two requests arriving before the first has finished must
            # never both pass the cooldown check and both call
            # run_once() — the loser gets an immediate, honest "already
            # running" redirect instead of racing into a second poll
            # cycle or queueing silently behind a blocking acquire.
            return self.redirect(
                "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_ALREADY_RUNNING)))
        try:
            state_dir = self.args.state_dir
            remaining = poll_cooldown_remaining(state_dir)
            if remaining > 0:
                return self.redirect(
                    "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_COOLDOWN)))
            try:
                # Pattern 3 (06-RESEARCH.md): the exact production code
                # path the systemd timer already runs, in-process — never
                # a second process and never a re-parsed subprocess
                # result.
                poll_loop.run_once(state_dir=state_dir, geofence=self.args.geofence)
            except Exception:
                return self.redirect(
                    "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_FAILED)))
            mark_poll_triggered(state_dir)
            return self.redirect(
                "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_TRIGGERED)))
        finally:
            # Always released — including on the except Exception: branch
            # above, which must stay inside this try so a failed poll
            # still releases the guard for the next attempt (never a
            # permanently wedged trigger, T-06.6.2-05).
            _POLL_LOCK.release()

    def _handle_theme_post(self):
        form = self.read_form()
        submitted = form.get("ui_theme")
        cookie_header = None
        if submitted in layout.UI_THEME_CHOICES:
            cookie_header = (
                "%s=%s; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=%d"
                % (auth.UI_THEME_COOKIE_NAME, submitted, THEME_COOKIE_MAX_AGE_S))
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    def do_POST(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            return self._handle_login_post()

        if path == SETTINGS_ROUTE:
            if not self.require_session():
                return None
            form = self.read_form()
            ctx = self.page_context()
            flash_key = config_page.handle_post(form, ctx)
            return self.redirect("%s?flash=%s" % (SETTINGS_ROUTE, quote(flash_key)))

        if path == POLL_ROUTE:
            if not self.require_session():
                return None
            return self._handle_poll_now()

        if path == THEME_ROUTE:
            return self._handle_theme_post()

        if path == LOGOUT_ROUTE:
            return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())

        # quick task 260902-v26: mirrors the GET dispatch's own
        # ILLUSTRATION_IMAGE_ROUTE_PREFIX branch above byte for byte — same
        # prefix constant, same ".png" suffix test, same require_session()
        # gate first, same slice arithmetic.
        if path.startswith(ILLUSTRATION_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            key = path[len(ILLUSTRATION_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._handle_illustration_replace(key)

        return self.send_html(404, self._not_found_page())

    # --- logging -------------------------------------------------------

    def log_message(self, fmt, *fmt_args):
        # Method and path only — matching stub-server/byos_server.py's own
        # override. Never a header, a cookie, a form body, or a query
        # string (T-06-05-08); the query string is stripped here even
        # though self.path may carry one (e.g. a flash-key redirect).
        print("%s %s" % (self.command, urlsplit(self.path).path))


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--state-dir",
        default=poll_loop.DEFAULT_STATE_DIR,
        help="Directory holding the poll pipeline's own state (default: "
             "server/state/) — read-only from this service's perspective "
             "except via the real production poll cycle POST /poll-now "
             "triggers.",
    )
    parser.add_argument(
        "--geofence",
        default=None,
        help="Path to the geofence JSON forwarded to a manually-triggered "
             "poll cycle (default: adsb-test/runway3.json).",
    )
    return parser


def main():
    args = build_parser().parse_args()
    try:
        auth.configured_password()
    except auth.AuthNotConfigured as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    # Matches stub-server/byos_server.py's own main(): stdout is fully
    # buffered (not line-buffered) once journald redirects it away from a
    # TTY, which can silently lose this process's own startup line and
    # every server.poll_loop print a POST /poll-now trigger emits if the
    # service is ever killed before the buffer next flushes.
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("companion: serving on port %d (state_dir=%s)" % (args.port, args.state_dir))
    server.serve_forever()


if __name__ == "__main__":
    main()
