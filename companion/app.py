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
page module.

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
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

# Same repo-root sys.path bootstrap as server/poll_loop.py, so
# `server.device_config`/`server.history_db`/`server.panel_preview`/
# `server.poll_loop` all resolve whether this file is imported as a
# package or executed directly (`server/.venv/bin/python3
# companion/app.py`, the exact invocation the systemd unit uses).
_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from companion import auth, layout  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page,
    config_page,
    health_page,
    history_page,
    preview_page,
)
from server import device_config, history_db, panel_preview  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

DEFAULT_PORT = 8643
GALLERY_DIRNAME = "gallery"
GALLERY_DEFAULT_LIMIT = 30
POLL_COOLDOWN_S = 45  # D-17: tens of seconds, a double-click guard, not an abuse rate-limit.
PREVIEW_THUMB_WIDTH = 600  # nearest-neighbour cap for a faster mobile load (D-22).
THEME_COOKIE_MAX_AGE_S = 365 * 24 * 3600
MAX_FORM_BYTES = 8192  # far more than any form on this site needs (Pitfall/T-06-05-07).

LOGIN_ROUTE = "/login"
STYLE_ROUTE = "/static/style.css"
CONFIG_ROUTE = "/config"
LED_ROUTE = "/config-led"
POLL_ROUTE = "/poll-now"
THEME_ROUTE = "/ui-theme"
LOGOUT_ROUTE = "/logout"
PREVIEW_IMAGE_ROUTE = "/preview.png"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# exactly like the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX

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
}

_STYLE_CSS_PATH = os.path.join(_HERE, "static", "style.css")
_RUNWAY_IMAGE_DIR = os.path.join(_HERE, "static")

# Process-global, not per-session (06-RESEARCH.md Pitfall 8's own login
# analogue) — D-01/D-02 mean there are no distinct users for a per-session
# counter to key on.
LOGIN_THROTTLE = auth.LoginThrottle()

_PAGE_TITLES = {
    "/config": "Config",
    "/health": "Health",
    "/airlines": "Airlines",
    "/history": "History",
    "/preview": "Preview",
}


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


class Handler(BaseHTTPRequestHandler):
    server_version = "skypane-companion"
    args = None

    # --- response helpers -------------------------------------------

    def send_html(self, code, html_str):
        body = html_str.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, code, content_type, payload, cache_seconds=0):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if cache_seconds > 0:
            self.send_header("Cache-Control", "public, max-age=%d" % cache_seconds)
        else:
            self.send_header("Cache-Control", "no-store")
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
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, MAX_FORM_BYTES + 1))
        if length > MAX_FORM_BYTES:
            remaining = length - len(raw)
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            return {}
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {}
        parsed = parse_qs(text, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items() if values}

    def page_context(self):
        """Build the `ctx` dict every page module's render()/handle_post()
        receives — documented in full in companion/pages/__init__.py.
        """
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query)
        flash_key = params.get("flash", [None])[0]
        state_dir = self.args.state_dir
        return {
            "state_dir": state_dir,
            "ui_theme": self._resolved_ui_theme(),
            "device_config": device_config.load_device_config(state_dir),
            "flash": _resolve_flash_text(flash_key, state_dir),
            "poll_cooldown_remaining": poll_cooldown_remaining(state_dir),
            "gallery_entries": gallery_entries(state_dir),
            "runway_images": runway_images_available(),
            "now": history_db.utc_now_iso(),
        }

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        body = (
            '<h1 class="text-heading">Page not found.</h1>'
            '<p class="text-body"><a href="%s">Back to Config</a></p>'
        ) % CONFIG_ROUTE
        return layout.page_shell(
            title="Not Found", active="", body=body,
            ui_theme=self._resolved_ui_theme())

    def _login_body(self, error=None, lockout_seconds=None):
        parts = [
            '<h1 class="text-heading">SkyPane</h1>',
            '<p class="text-body">Companion Access</p>',
        ]
        if lockout_seconds:
            parts.append(
                '<p class="text-body">%s</p>'
                % layout.escape_html(
                    "Too many attempts — try again in %ds." % lockout_seconds))
        elif error:
            parts.append('<p class="text-body">%s</p>' % layout.escape_html(error))
        parts.append(
            '<form method="post" action="%s">'
            '<label for="password">Password</label>'
            '<input type="password" id="password" name="password" required>'
            '<button type="submit">Sign In</button>'
            "</form>" % LOGIN_ROUTE
        )
        return "".join(parts)

    def _render_login_page(self, error=None, lockout_seconds=None):
        body = self._login_body(error=error, lockout_seconds=lockout_seconds)
        return layout.page_shell(
            title="Login", active="", body=body,
            ui_theme=self._resolved_ui_theme())

    def _serve_stylesheet(self):
        try:
            with open(_STYLE_CSS_PATH, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "text/css", payload, cache_seconds=300)

    def _serve_preview_image(self):
        state_dir = self.args.state_dir
        raw = panel_preview.read_panel_file(state_dir)
        if raw is None:
            body = layout.empty_state(
                "No preview yet.", "The panel hasn't rendered anything yet.")
            return self.send_html(404, layout.page_shell(
                title="Preview unavailable", active="", body=body,
                ui_theme=self._resolved_ui_theme()))
        try:
            payload = panel_preview.panel_png_bytes(raw, max_width=PREVIEW_THUMB_WIDTH)
        except panel_preview.PanelDecodeError:
            body = layout.empty_state(
                "Preview unavailable.",
                "Preview is temporarily unavailable — check the "
                "companion service logs.")
            return self.send_html(503, layout.page_shell(
                title="Preview unavailable", active="", body=body,
                ui_theme=self._resolved_ui_theme()))
        return self.send_bytes(200, "image/png", payload)

    def _serve_gallery_image(self, requested):
        payload = gallery_bytes(self.args.state_dir, requested)
        if payload is None:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=3600)

    def _serve_runway_image(self, runway_id):
        # Membership test FIRST, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — T-06.4-02). An
        # unknown id and an unreadable file both return this same 404, so
        # a caller can never distinguish "not a real runway" from "no
        # image for a real runway" — leaking nothing about the
        # filesystem beyond the RUNWAY_IDS set the authenticated /config
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

    def _referring_tab(self):
        referer = self.headers.get("Referer", "")
        try:
            path = urlsplit(referer).path
        except ValueError:
            path = ""
        allowed = {route for route, _ in layout.NAV_TABS}
        return path if path in allowed else CONFIG_ROUTE

    def _render_tab(self, route, page_module):
        if not self.require_session():
            return None
        ctx = self.page_context()
        body = page_module.render(ctx)
        flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
        html_doc = layout.page_shell(
            title=_PAGE_TITLES[route], active=route.lstrip("/"), body=body,
            ui_theme=ctx["ui_theme"], flash=flash_html)
        return self.send_html(200, html_doc)

    # --- GET -------------------------------------------------------------

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            if self._is_authenticated():
                return self.redirect(CONFIG_ROUTE)
            return self.send_html(200, self._render_login_page())

        if path == STYLE_ROUTE:
            return self._serve_stylesheet()

        if path == "/config":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = config_page.render(ctx)
            flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
            return self.send_html(200, layout.page_shell(
                title="Config", active="config", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html))

        if path == "/health":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = health_page.render(ctx)
            flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
            return self.send_html(200, layout.page_shell(
                title="Health", active="health", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html))

        if path == "/airlines":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = airlines_page.render(ctx)
            flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
            return self.send_html(200, layout.page_shell(
                title="Airlines", active="airlines", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html))

        if path == "/history":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = history_page.render(ctx)
            flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
            return self.send_html(200, layout.page_shell(
                title="History", active="history", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html))

        if path == "/preview":
            if not self.require_session():
                return None
            ctx = self.page_context()
            body = preview_page.render(ctx)
            flash_html = layout.flash_banner(ctx["flash"]) if ctx["flash"] else None
            return self.send_html(200, layout.page_shell(
                title="Preview", active="preview", body=body,
                ui_theme=ctx["ui_theme"], flash=flash_html))

        if path == PREVIEW_IMAGE_ROUTE:
            if not self.require_session():
                return None
            return self._serve_preview_image()

        if path.startswith(GALLERY_ROUTE_PREFIX):
            if not self.require_session():
                return None
            return self._serve_gallery_image(path[len(GALLERY_ROUTE_PREFIX):])

        if path.startswith(RUNWAY_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            runway_id = path[len(RUNWAY_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._serve_runway_image(runway_id)

        if path == LOGOUT_ROUTE:
            return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())

        return self.send_html(404, self._not_found_page())

    # --- POST --------------------------------------------------------------

    def _handle_login_post(self):
        if LOGIN_THROTTLE.locked_out():
            remaining = LOGIN_THROTTLE.seconds_remaining()
            return self.send_html(429, self._render_login_page(lockout_seconds=remaining))
        form = self.read_form()
        submitted = form.get("password", "")
        if auth.password_ok(submitted):
            LOGIN_THROTTLE.record_success()
            token = auth.issue_session_token()
            return self.redirect(
                CONFIG_ROUTE, set_cookie=auth.session_set_cookie_header(token))
        LOGIN_THROTTLE.record_failure()
        return self.send_html(
            401, self._render_login_page(error="Incorrect password. Try again."))

    def _handle_poll_now(self):
        state_dir = self.args.state_dir
        remaining = poll_cooldown_remaining(state_dir)
        if remaining > 0:
            return self.redirect(
                "%s?flash=%s" % (CONFIG_ROUTE, quote(FLASH_KEY_POLL_COOLDOWN)))
        try:
            # Pattern 3 (06-RESEARCH.md): the exact production code path
            # the systemd timer already runs, in-process — never a second
            # process and never a re-parsed subprocess result.
            poll_loop.run_once(state_dir=state_dir, geofence=self.args.geofence)
        except Exception:
            return self.redirect(
                "%s?flash=%s" % (CONFIG_ROUTE, quote(FLASH_KEY_POLL_FAILED)))
        mark_poll_triggered(state_dir)
        return self.redirect(
            "%s?flash=%s" % (CONFIG_ROUTE, quote(FLASH_KEY_POLL_TRIGGERED)))

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

        if path == "/config":
            if not self.require_session():
                return None
            form = self.read_form()
            ctx = self.page_context()
            flash_key = config_page.handle_post(form, ctx)
            return self.redirect("%s?flash=%s" % (CONFIG_ROUTE, quote(flash_key)))

        if path == LED_ROUTE:
            if not self.require_session():
                return None
            form = self.read_form()
            ctx = self.page_context()
            flash_key = config_page.handle_led_post(form, ctx)
            return self.redirect("%s?flash=%s" % (CONFIG_ROUTE, quote(flash_key)))

        if path == POLL_ROUTE:
            if not self.require_session():
                return None
            return self._handle_poll_now()

        if path == THEME_ROUTE:
            return self._handle_theme_post()

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
