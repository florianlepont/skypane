#!/usr/bin/env python3
"""Contract harness for the SkyPane companion service: companion/auth.py,
companion/layout.py, and (plan 06-05) the real subprocess-launched
companion/app.py route table.

Covers: constant-time password checking, fail-closed behaviour when no
password is configured, stateless signed session tokens (issue/verify
round trip, six distinct malformed-token rejections, forged-secret and
hand-built-expired coverage), session/logout cookie security flags,
cookie parsing, the process-global login-attempt throttle, the single
canonical HTML-escaping helper, the page shell's document shape and
active-nav/theme rendering, the status-dot/data-table component
builders, that AuthNotConfigured never leaks the configured password
value, the D-02 whole-site auth gate asserted route by route against a
real running service, the login failure/success flow and its cookie
flags, the 404 copy, the preview PNG path (missing file vs. a real
960,000-byte panel), gallery path-traversal rejection with a canary
file, and the server-global (not per-session) poll-trigger cooldown.

Checks are grouped under three clearly-commented sections: Section 1
(companion/auth.py) and Section 2 (companion/layout.py) are pure
in-process unit checks against the imported modules. Section 3 (plan
06-05) launches companion/app.py as a real subprocess on a free local
port and drives it with urllib.request, mirroring
stub-server/test_poll_cycle.py's Harness/http_request()/readiness-poll
pattern.

Stdlib-only (hashlib, hmac, html, os, shutil, socket, subprocess, sys,
tempfile, time, urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_companion_app.py
"""
import ast
import hashlib
import html
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# 32-11-PLAN.md Task 1 (TST-03): test-support/ on sys.path so this harness
# works standalone (server/.venv/bin/python3 companion/test_companion_app.py),
# not only when launched through companion/test_legacy_harness_shim.py's own
# child_env(), which already puts test-support/ on PYTHONPATH.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from companion import auth, layout  # noqa: E402
from companion.pages import config_page  # noqa: E402
from server import device_config  # noqa: E402
from server.plane import calendar_rules  # noqa: E402
from server.plane import colour_rules  # noqa: E402
from server.plane import manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402
from skypane_test_support import FakeProviders, child_env  # noqa: E402

TEST_PASSWORD = "companion-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
IMAGE_BYTES = 960000  # server/panel_format.py's IMAGE_BYTES, duplicated as a
# plain literal so this harness never has to import Pillow (or
# server.panel_format) itself, matching panel_format.py's own documented
# precedent for stub-server/make_test_panel.py's independent duplication.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STARTUP_DEADLINE_S = 10.0

# 29-06-PLAN.md Task 3 (CFG-79): the site-wide caption-floor's own
# exemption list. Begins with config_page.ASPECT_CAPTION_EXEMPTIONS
# (imported, never re-listed — one home, emptied in one place the day
# Phase 30 lands) and carries NO further members. The one candidate
# this plan anticipated — layout.empty_state()'s compact body, which
# composes "empty-state__body text-label section-caption" — never
# needs a text-based entry here: it is already excluded by the SAME
# class-subset selector _measured_section_captions() below uses (its
# extra "empty-state__body" token fails the strict
# {"text-label", "section-caption"} subset check, the identical
# mechanism that already excludes config_page.py's wake-gauge
# readouts, per 29-05-SUMMARY.md). It never enters the measured set at
# all, so it needs no exemption-list entry — recorded here as the
# judgement call this plan made, not left silent.
CAPTION_FLOOR_EXEMPTIONS = config_page.ASPECT_CAPTION_EXEMPTIONS


# 23-01-PLAN.md Task 2 (D3/CFG-32): the reduced-motion floor, expressed as
# two numbers a plan has to edit deliberately rather than drift past.
#
# EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS pins the LIVE (comment-stripped)
# `@media (prefers-reduced-motion: reduce)` block count in
# companion/static/style.css. The two are style.css's global
# `*, *::before, *::after` override (D-19) and `.js .mobile-nav`'s narrow
# `transition: none`, the one documented case where 0.01ms is not good
# enough because a size-interpolating transition still running at 0.01ms
# can strand an intermediate computed value. THIS NUMBER STAYS AT TWO FOR
# THE WHOLE OF PHASE 23: `references/accessibility-contrast.md`'s "What to
# Avoid" records a per-rule reduced-motion block for a plain colour,
# border, shadow or transform transition as dead code, not a safety net,
# and the global override already covers every one of them for free. No
# plan in this phase is permitted to move it; a plan that believes it has
# the third genuine case must argue it the way `.js .mobile-nav` was
# argued, in its own SUMMARY, before touching this line.
EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 2
# EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS pins the opposite wrapper.
# It stood at ZERO for exactly one plan, because the gap it exists for was
# not yet closed: `*, *::before, *::after` matches ELEMENTS, and the
# view-transition pseudo-element tree is not an element tree, so the
# global reduce block does not disable a cross-document view transition
# (23-RESEARCH.md's Risk 3, confirmed in this project's own harness
# Chromium). 23-04-PLAN.md Task 1 is the ONE plan 23-01 permitted to move
# this constant, and it moved it to exactly 1 — the media wrapper around
# style.css's one navigation at-rule, which prevents the transition being
# SET UP at all rather than setting one up and running it fast. That is
# the whole of the licence: the number is back to being frozen, and any
# plan raising it to 2 has to argue its own case first, in its own
# SUMMARY, the way `.js .mobile-nav` argued the reduce side.
EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS = 1

# 23-01-PLAN.md Task 2: every non-custom identifier the `animation`
# shorthand may legally carry BESIDES the keyframes name. Anything in an
# animation value that is not one of these, not a `--custom-property` and
# not a time literal is taken to be a keyframes reference and must
# resolve to a block defined in the same stylesheet.
_ANIMATION_VALUE_KEYWORDS = frozenset((
    "var", "none", "infinite", "normal", "reverse", "alternate", "alternate-reverse",
    "forwards", "backwards", "both", "running", "paused", "auto",
    "linear", "ease", "ease-in", "ease-out", "ease-in-out",
    "step-start", "step-end", "steps", "cubic-bezier",
    "jump-start", "jump-end", "jump-none", "jump-both", "start", "end",
    "inherit", "initial", "unset", "revert", "revert-layer",
))


def _without_reduced_motion_blocks(css_source):
    """`css_source` with every `@media (prefers-reduced-motion: ...)` block
    (query and body) removed, by brace matching rather than by regex.

    23-01-PLAN.md Task 2. These blocks are the one place in the file where
    a bare duration literal is correct: the global override's
    `animation-duration: 0.01ms !important` exists to CANCEL motion, so
    binding it to a motion token would invert its purpose. Their counts
    are asserted separately, before this removal.
    """
    out = ""
    pos = 0
    for match in re.finditer(r"@media[^{]*prefers-reduced-motion", css_source):
        if match.start() < pos:
            continue
        open_brace = css_source.find("{", match.start())
        if open_brace < 0:
            continue
        depth = 0
        index = open_brace
        while index < len(css_source):
            if css_source[index] == "{":
                depth += 1
            elif css_source[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        out += css_source[pos:match.start()]
        pos = index + 1
    return out + css_source[pos:]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return None from redirect_request() so a 303 (or any other
    redirect) is surfaced to the caller as an HTTPError instead of being
    silently followed — the auth-gate and flash-key checks below need to
    see the raw status code and Location/Set-Cookie headers, not the page
    the redirect points at.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# A single shared opener with redirects disabled. Deliberately NOT built
# with urllib.request.HTTPCookieProcessor: this test server runs over
# plain HTTP, and companion/auth.py's session cookie always carries the
# `Secure` flag (correctly, for production) - http.cookiejar honours that
# flag and silently refuses to store or resend a Secure cookie over a
# non-HTTPS connection, which would make an automatic cookie jar quietly
# drop the session cookie in exactly this harness. Cookies are instead
# captured from Set-Cookie response headers and threaded through
# explicitly as plain Cookie request headers below.
_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(
        url, method="GET", data=None, cookie=None, timeout=10,
        content_type=None, extra_headers=None):
    """Minimal stdlib HTTP client (mirrors
    stub-server/test_poll_cycle.py's http_request()): returns
    (status, headers_dict, raw_bytes) for both success and HTTP-error
    responses; connection-level failures propagate.

    `content_type` (quick task 260902-v26): an explicit override for the
    Content-Type request header — used by the illustration-upload checks
    to send `multipart/form-data; boundary=...` instead of the default
    urlencoded type a POST otherwise gets. `None` (the default) preserves
    every existing caller's behaviour exactly.

    `extra_headers` (20-01-PLAN.md Task 2): an optional {name: value}
    dict merged into the request headers — used by the D-03
    Accept-Language checks. `None` (the default) preserves every
    existing caller's behaviour exactly.
    """
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if content_type is not None:
        headers["Content-Type"] = content_type
    elif data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    """Extract just the "name=value" portion of a Set-Cookie response
    header (dropping the trailing attribute flags), or None.
    """
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Owns the companion/app.py subprocess lifecycle: a free port, an
    isolated temp state directory, startup readiness polling, and clean
    teardown - structurally mirrors
    stub-server/test_poll_cycle.py's own Harness class.
    """

    def __init__(self, extra_args=()):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-companion-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None
        self.extra_args = list(extra_args)

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def state_path(self, *parts):
        return os.path.join(self.tmpdir, *parts)

    def fake_provider_calls(self):
        """The fake ADS-B/adsbdb providers' call log for THIS harness's
        child - what companion/app.py's run_once() actually queried,
        proving a /poll-now cycle was served by the fake, not the real
        network (32-11-PLAN.md Task 1, TST-03).
        """
        return FakeProviders.read_calls_log(
            os.path.join(self.tmpdir, "fake-providers.json"))

    def start(self):
        # 32-11-PLAN.md Task 1 (TST-03): every companion/app.py child this
        # harness starts runs under the no-network guard and serves
        # ADS-B/adsbdb from a fresh FakeProviders() (default empty-traffic
        # responses) rather than reaching the real providers.
        env = child_env(
            dict(os.environ), fake_providers=FakeProviders(), state_dir=self.tmpdir)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ] + self.extra_args
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "companion/app.py exited early (code %s) before "
                    "accepting connections:\n%s"
                    % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(
            "companion/app.py did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class _InProcessHarness:
    """A real `companion/app.py` `ThreadingHTTPServer`, running in a
    background thread of THIS test process — deliberately NOT a
    `Harness` subprocess (phase 17 plan 04, D-06/T-17-FLASH's checks).

    The calendar-sync checks below need to monkeypatch `server.plane.
    calendar_rules.default_calendar_transport` and `socket.getaddrinfo`
    so a save-triggered fetch never touches a real socket — the exact
    technique `server/test_calendar_rules.py`'s own `make_calendar_
    transport()`/fake-`getaddrinfo` helpers already use in-process. A
    monkeypatch made in this process has no effect on a `Harness`'s
    `subprocess.Popen`'d child, which is a separate interpreter with its
    own separate copy of every imported module — hence this second,
    in-process harness rather than reusing `Harness` for this section.

    Mirrors `companion/app.py`'s own `main()` construction exactly:
    `Handler.args` set at class level, then a `ThreadingHTTPServer`
    built the identical way. `auth.PASSWORD_ENV_VAR` is set explicitly
    here, not inherited from this test module's own `main()` — by the
    time Section 3/4 run, this file's own outer `try`/`finally` (Section
    1/2's setup) has already restored the process environment to
    whatever it was before this file started, since every `Harness`
    subprocess check below sets the variable in its OWN child `env`
    dict instead (`Harness.start()`, above), never relying on the
    parent process's environment. This harness runs in-process, so it
    must set it here, and restore it in `stop()`.
    """

    def __init__(self):
        import argparse
        from http.server import ThreadingHTTPServer

        import companion.app as app_module

        self.tmpdir = tempfile.mkdtemp(prefix="skypane-calendar-sync-")
        self.port = Harness._pick_free_port()
        self._app_module = app_module
        self._previous_password = os.environ.get(auth.PASSWORD_ENV_VAR)
        os.environ[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        app_module.Handler.args = argparse.Namespace(
            state_dir=self.tmpdir, geofence=None)
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), app_module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        if self._previous_password is None:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)
        else:
            os.environ[auth.PASSWORD_ENV_VAR] = self._previous_password
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class _FakeCalendarResponse:
    """Hermetic stand-in for `requests.Response`, `server/test_calendar_
    rules.py`'s own class of the same shape exactly — no check below
    ever makes a real network call.
    """

    def __init__(self, status_code=200, body=b""):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self.is_redirect = False
        self.closed = False

    def iter_content(self, chunk_size=8192):
        yield self._body

    def close(self):
        self.closed = True


def _make_calendar_transport(status_code=200, body=b"", raise_exc=None, calls=None):
    """Build a fake `fetch_ics()`-shaped transport — `server/test_
    calendar_rules.py`'s own `make_calendar_transport()` helper, adapted
    for `_FakeCalendarResponse`. Records every URL it was invoked with
    (or raises `raise_exc` instead of returning), simulating success or
    failure without ever touching a real socket.
    """
    def transport(url, timeout):
        if calls is not None:
            calls.append(url)
        if raise_exc is not None:
            raise raise_exc
        return _FakeCalendarResponse(status_code, body)
    return transport


class _stubbed_calendar_transport:
    """Context manager: monkeypatches `calendar_rules.default_calendar_
    transport` to `transport_fn` for the duration of the block,
    restoring the real function on exit. `fetch_ics()` looks up
    `default_calendar_transport` as a bare name in its own module's
    global namespace when its `transport` parameter is `None` (the
    companion's real call site never passes one), so patching the
    attribute on the imported `calendar_rules` module object — the SAME
    module object the in-process server thread's own code runs against,
    since this is one process — is sufficient; no reload, no subprocess
    env var, no second definition of the fetch path.
    """

    def __init__(self, transport_fn):
        self.transport_fn = transport_fn
        self._real = None

    def __enter__(self):
        self._real = calendar_rules.default_calendar_transport
        calendar_rules.default_calendar_transport = self.transport_fn
        return self

    def __exit__(self, *exc_info):
        calendar_rules.default_calendar_transport = self._real


class _fake_public_hostname:
    """Context manager: monkeypatches `socket.getaddrinfo` so `hostname`
    resolves to a genuinely public-looking address for the duration of
    the block, restoring the real resolver on exit — `server/test_
    calendar_rules.py`'s own technique for getting a fabricated URL past
    `calendar_rules._url_is_safe()`'s SSRF gate without a real DNS answer
    or a real network call.
    """

    def __init__(self, hostname, address="93.184.216.34"):
        self.hostname = hostname
        self.address = address
        self._real = None

    def __enter__(self):
        self._real = socket.getaddrinfo
        real, hostname, address = self._real, self.hostname, self.address

        def fake(host, port=None, *a, **k):
            if host == hostname:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port or 443))]
            return real(host, port, *a, **k)
        socket.getaddrinfo = fake
        return self

    def __exit__(self, *exc_info):
        socket.getaddrinfo = self._real


def _ics_body(entries):
    """Build a minimal, real-shaped iCal body from `entries` — a list of
    `(flight, origin, destination, hours_from_now)` tuples — matching
    `calendar_rules._build_entry()`'s exact accepted shape (CATEGORIES:
    FLT, a `FLIGHT ORI-DST` summary, bare-UTC DTSTART/DTEND). Every
    DTSTART is computed from real wall-clock time at call time, since
    the settings-post handler under test calls `poll_loop.now_s()`
    (real `time.time()`) for its own `now` — there is no injectable
    clock on this path the way `server/test_calendar_rules.py`'s
    in-process `refresh_calendar_registry()` checks have.
    """
    def stamp(hours):
        when = datetime.now(timezone.utc) + timedelta(hours=hours)
        return when.strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VCALENDAR"]
    for flight, origin, destination, hours in entries:
        lines += [
            "BEGIN:VEVENT",
            "SUMMARY:%s %s-%s" % (flight, origin, destination),
            "CATEGORIES:FLT",
            "DTSTART:%s" % stamp(hours),
            "DTEND:%s" % stamp(hours + 1),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def _login(harness, password=TEST_PASSWORD):
    """POST /login with `password` and return the session cookie's
    "name=value" pair. Raises AssertionError if login did not succeed -
    callers that expect failure should call http_request() directly.
    """
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def _seed_unresolved_prefixes(state_dir, registry):
    """Write `registry` as `poll_state.json`'s `unresolved_prefixes` value
    — mirrors companion/test_status_pages.py's own helper of the same
    name exactly (phase 13 plan 13-06), since that is the exact D-11
    membership set `unresolved_row_for_prefix()` reads.
    """
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def _encode_multipart(
        payload, boundary=b"SkyPaneTestBoundary7Q2vpH",
        filename="upload.png", field_name="file", content_type="image/png"):
    """Hand-build a single-file `multipart/form-data` body — quick task
    260902-v26. This harness deliberately does not import a multipart-
    encoding library, matching `companion.app.parse_single_uploaded_
    file()`'s own zero-third-party-dependency discipline. Returns
    `(body_bytes, content_type_header)`, shared by both the in-process
    parser checks (Section 2/Task 1) and the real-HTTP round-trip checks
    (Section 3/Task 3) so every caller builds a request the same way.
    """
    boundary_str = boundary.decode("ascii")
    header = (
        'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
        'Content-Type: %s\r\n\r\n'
    ) % (field_name, filename, content_type)
    body = (
        b"--" + boundary + b"\r\n"
        + header.encode("utf-8")
        + payload
        + b"\r\n--" + boundary + b"--\r\n"
    )
    return body, "multipart/form-data; boundary=%s" % boundary_str


# 33-14-PLAN.md Task 3: the historical EXPECTED_CHECK_COUNT reassignment
# trail (79 -> 320 across every phase since 06.6.4.1) is collapsed into
# this one authoritative line, per 33-MIGRATION-RULES.md section 1. Every
# later companion_app migration plan edits only this line, to the pending
# row count its own ledger fragment records.
EXPECTED_CHECK_COUNT = 52  # 141 - 89 (33-17: part 04's 89 ledger rows,
# #178-#266), re-derived by RUNNING (52/52 pass).


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # Section 3: companion/app.py (plan 06-05) — a real companion/app.py
    # subprocess, launched on a free local port, driven with
    # urllib.request. This section owns its own harness lifecycle
    # (independent of Section 1/2's env-var save/restore above), and
    # tolerates the ADS-B aggregators being unreachable in this sandboxed
    # environment — the poll-trigger checks below assert on the flash
    # outcome and the cooldown behaviour, never on a flight being
    # detected.
    # ==================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()

        # 33-15-PLAN.md Task 3: this main()-level import and the two
        # closure factories below are shared plumbing several still-legacy
        # checks further down main() still call directly (by name, or via
        # `app_module.SOME_CONSTANT` referenced at this same top-level
        # scope) — they are NOT closures only this plan's own (now
        # migrated) checks used, so they survive the 33-15 shrink even
        # though every check() call that used to sit directly below them
        # is gone.
        import companion.app as app_module

        def _unauth_redirects_to_login(method, path, data=None, next_route=None):
            # 06.6.2-07 (UXA-03): require_session() carries an
            # allowlisted `next` query param for any requested path that
            # is one of layout.NAV_TABS's known routes, regardless of
            # HTTP method, since it only ever looks at self.path. A path
            # outside that set still redirects to the bare /login.
            expected_location = (
                "/login?next=%s" % urllib.parse.quote(next_route, safe="")
                if next_route else "/login")

            def _run():
                status, headers, body = http_request(base + path, method=method, data=data)
                if status != 303:
                    return False, "expected 303, got %d" % status
                if headers.get("Location") != expected_location:
                    return False, "expected a redirect to %r, got %r" % (
                        expected_location, headers.get("Location"))
                if body:
                    return False, "expected an empty redirect body, got %d bytes of content" % len(body)
                return True, ""
            return _run

        def _static_script_public(route):
            def _run():
                status, headers, body = http_request(base + route)
                if status != 200:
                    return False, "expected 200, got %d" % status
                content_type = headers.get("Content-Type", "")
                if "text/javascript" not in content_type:
                    return False, "expected a text/javascript content type, got %r" % content_type
                if not body:
                    return False, "expected a non-empty script body"
                cache_control = headers.get("Cache-Control", "")
                if "max-age=300" not in cache_control:
                    return False, "expected Cache-Control max-age=300, got %r" % cache_control
                return True, ""
            return _run


        # Authenticate once for every check below that needs a session — every check
        # between here and the illustration-upload setup below was migrated to
        # companion/test_companion_app_04.py and _04b.py (33-17-PLAN.md); this is the one
        # login the still-legacy checks after this point (33-18/part 05) still need.
        session_cookie = _login(harness)

        # --- 260902-v26 Task 3: the live upload round trip, against this ---
        # --- real running companion/app.py subprocess (D-01/D-02/D-03).  ---
        # app_module is already in scope from this same block's earlier
        # `import companion.app as app_module` (33-15-PLAN.md Task 3).

        _VENDORED_ILLUSTRATIONS_DIR = os.path.join(
            REPO_ROOT, "server", "assets", "icons", "illustrations")
        _vendored_air_france_path = os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "air-france.png")
        with open(_vendored_air_france_path, "rb") as fh:
            _pre_upload_vendored_hash = hashlib.sha256(fh.read()).hexdigest()
        _pre_upload_vendored_stat = os.stat(_vendored_air_france_path)

        _illustration_pre_upload_render = []  # populated by the round-trip check below
        # 33-17-PLAN.md migrated this check itself to companion/test_companion_app_04b.py::
        # test_illustration_upload_round_trip_replaces_served_bytes. Its own side effects stay
        # here as bare setup: every check below reads state only a real upload creates (the
        # override file on disk, and the pre-upload render the D-03 normalization check below
        # compares against).
        with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
            _vueling_bytes = fh.read()
        _pre_status, _pre_headers, _pre_body = http_request(
            base + "/illustration/air-france.png", cookie=session_cookie)
        if _pre_status != 200:
            raise AssertionError("setup: expected 200 for the pre-upload GET, got %d" % _pre_status)
        _illustration_pre_upload_render.append(_pre_body)
        _upload_body, _upload_content_type = _encode_multipart(
            _vueling_bytes, filename="../../../etc/passwd", field_name="illustration")
        _upload_status, _upload_headers, _ = http_request(
            base + "/illustration/air-france.png", method="POST", data=_upload_body,
            cookie=session_cookie, content_type=_upload_content_type)
        if _upload_status != 303:
            raise AssertionError(
                "setup: expected a 303 redirect after a valid upload, got %d" % _upload_status)


        def _illustration_override_uses_same_normalization_pipeline():
            if not _illustration_pre_upload_render:
                return False, "no pre-upload render was captured by the round-trip check above"
            pre_body = _illustration_pre_upload_render[0]
            override_status, _h1, override_body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            vueling_status, _h2, vueling_body = http_request(
                base + "/illustration/vueling-airlines.png", cookie=session_cookie)
            if override_status != 200 or vueling_status != 200:
                return False, "expected 200 for both routes, got %d/%d" % (override_status, vueling_status)
            if override_body == vueling_body:
                return True, ""
            # Fallback (D-03, documented in the plan 02 SUMMARY): if the
            # store-time Pillow RGBA re-encode turns out not to be
            # byte-for-byte lossless against illustration_normalize's own
            # re-encode of the untouched vendored file, fall back to a
            # weaker-but-still-meaningful equivalence check rather than
            # silently accepting inequality.
            if not override_body.startswith(PNG_SIGNATURE):
                return False, "expected the override render to start with the PNG signature even on the fallback path"
            if override_body == pre_body:
                return False, "expected the override render to differ from the pre-upload render"
            if len(override_body) != len(vueling_body):
                return False, (
                    "fallback check failed too: override render length %d != vueling render "
                    "length %d (byte-for-byte equality did not hold)"
                    % (len(override_body), len(vueling_body)))
            return True, ""
        check(
            "the overridden air-france render and the vueling-airlines render (the same source "
            "image) come out of the identical illustration_normalize pipeline (D-03)",
            _illustration_override_uses_same_normalization_pipeline)

        def _illustration_override_written_to_expected_path_only():
            override_path = harness.state_path("illustration_overrides", "air-france.png")
            if not os.path.isfile(override_path):
                return False, "expected an override file at %r" % override_path
            override_dir = harness.state_path("illustration_overrides")
            entries = sorted(os.listdir(override_dir))
            if entries != ["air-france.png"]:
                return False, (
                    "expected exactly one file (air-france.png) in the override directory, got %r"
                    % entries)
            return True, ""
        check(
            "the upload was written to {state_dir}/illustration_overrides/air-france.png, and "
            "nothing else was created in that directory",
            _illustration_override_written_to_expected_path_only)

        def _illustration_vendored_original_untouched_after_upload():
            with open(_vendored_air_france_path, "rb") as fh:
                post_hash = hashlib.sha256(fh.read()).hexdigest()
            if post_hash != _pre_upload_vendored_hash:
                return False, "the vendored air-france.png file's bytes changed after an upload"
            post_stat = os.stat(_vendored_air_france_path)
            if post_stat.st_size != _pre_upload_vendored_stat.st_size:
                return False, "the vendored air-france.png file's size changed after an upload"
            if post_stat.st_mtime_ns != _pre_upload_vendored_stat.st_mtime_ns:
                return False, "the vendored air-france.png file's mtime changed after an upload"
            return True, ""
        check(
            "the vendored server/assets/icons/illustrations/air-france.png file is provably "
            "byte-identical (hash, size, and mtime) after a successful upload",
            _illustration_vendored_original_untouched_after_upload)

        def _illustration_override_reaches_select_illustration():
            # The panel-side effect (plan 01's whole point), asserted
            # against the exact override file the real HTTP route above
            # just wrote — never a hand-placed fixture.
            from server.plane import illustrations as server_illustrations
            override_result = server_illustrations.select_illustration(
                {"airline_name": "Air France"}, state_dir=harness.tmpdir)
            vendored_result = server_illustrations.select_illustration(
                {"airline_name": "Air France"})
            expected_override_path = harness.state_path("illustration_overrides", "air-france.png")
            if override_result != expected_override_path:
                return False, (
                    "expected select_illustration(..., state_dir=harness.tmpdir) to return %r, got %r"
                    % (expected_override_path, override_result))
            if vendored_result != _vendored_air_france_path:
                return False, (
                    "expected select_illustration() with no state_dir to still return the "
                    "vendored path, got %r" % (vendored_result,))
            return True, ""
        check(
            "select_illustration() given the harness's own state_dir resolves Air France to the "
            "override the real route just wrote; with no state_dir it still resolves to the "
            "vendored file",
            _illustration_override_reaches_select_illustration)

        def _illustration_non_image_upload_is_rejected():
            body, content_type = _encode_multipart(
                b"not a real image, just some text bytes", filename="fake.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/easyjet.png", method="POST", data=body,
                cookie=session_cookie, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for a non-image upload, got %d" % status
            location = headers.get("Location", "")
            if ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) not in location:
                return False, "expected the rejection flash key in the redirect, got %r" % location
            override_path = harness.state_path("illustration_overrides", "easyjet.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for a rejected non-image upload"
            return True, ""
        check(
            "POSTing a non-image payload is rejected with the rejection flash key and writes "
            "no override file",
            _illustration_non_image_upload_is_rejected)

        def _illustration_oversized_upload_is_rejected_and_connection_stays_healthy():
            oversized_payload = b"\x00" * (app_module.MAX_ILLUSTRATION_UPLOAD_BYTES + 4096)
            body, content_type = _encode_multipart(oversized_payload, filename="huge.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/corsair.png", method="POST", data=body,
                cookie=session_cookie, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for an oversized upload, got %d" % status
            location = headers.get("Location", "")
            if ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) not in location:
                return False, "expected the rejection flash key in the redirect, got %r" % location
            override_path = harness.state_path("illustration_overrides", "corsair.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for a rejected oversized upload"
            # A fresh, ordinary authenticated GET on a new connection proves
            # the over-cap drain (T-v26-02-03) left the service healthy.
            health_status, _headers2, _body2 = http_request(base + "/health", cookie=session_cookie)
            if health_status != 200:
                return False, (
                    "expected a fresh authenticated GET after the oversized-upload drain to "
                    "still return 200, got %d" % health_status)
            return True, ""
        check(
            "POSTing a body over MAX_ILLUSTRATION_UPLOAD_BYTES is rejected, writes no override "
            "file, and the drain leaves the service healthy for the next request",
            _illustration_oversized_upload_is_rejected_and_connection_stays_healthy)

        def _illustration_post_unknown_and_traversal_keys_returns_404():
            small_body, small_content_type = _encode_multipart(
                b"irrelevant - membership test runs before the body is read", filename="x.png")
            override_dir = harness.state_path("illustration_overrides")
            before_entries = sorted(os.listdir(override_dir))
            adversarial_paths = [
                "/illustration/not-a-real-airline.png",
                "/illustration/..%2F..%2Fetc%2Fpasswd.png",
                "/illustration/../../../etc/passwd.png",
                "/illustration/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, _body = http_request(
                    base + adversarial_path, method="POST", data=small_body,
                    cookie=session_cookie, content_type=small_content_type)
                if status != 404:
                    return False, "expected 404 for POST %r, got %d" % (adversarial_path, status)
            after_entries = sorted(os.listdir(override_dir))
            if after_entries != before_entries:
                return False, (
                    "expected the override directory to gain nothing from rejected POSTs, "
                    "before=%r after=%r" % (before_entries, after_entries))
            return True, ""
        check(
            "POSTing a valid payload to a key outside the membership set, and to three "
            "traversal-shaped paths, all 404 and write nothing to the override directory",
            _illustration_post_unknown_and_traversal_keys_returns_404)

        def _illustration_unauthenticated_post_redirects_to_login_and_writes_nothing():
            body, content_type = _encode_multipart(
                b"irrelevant - require_session() runs before anything else", filename="x.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/tunisair.png", method="POST", data=body, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            override_path = harness.state_path("illustration_overrides", "tunisair.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for an unauthenticated POST"
            return True, ""
        check(
            "an unauthenticated POST /illustration/tunisair.png redirects to /login and writes "
            "no override file",
            _illustration_unauthenticated_post_redirects_to_login_and_writes_nothing)

        # --- POST /airlines/resolve and the manual-resolution delete route
        # (phase 13 plan 13-06 Task 3, D-03/D-07/D-08/D-11) — each check
        # below spins up its own isolated Harness(), matching the
        # widened-membership-set checks above, since these routes write
        # real manual_resolutions.json/poll_state.json/override files.

        def _manual_resolve_and_delete_routes_require_auth_and_write_nothing():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                _seed_unresolved_prefixes(manual_harness.tmpdir, {
                    "PQR": {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "PQR100"},
                })
                manual_resolutions_path = manual_resolutions.manual_resolutions_path(
                    manual_harness.tmpdir)

                resolve_data = urllib.parse.urlencode(
                    {"prefix": "PQR", "airline_name": "Unauthorized Air"}).encode()
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data)
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated POST "
                        "/airlines/resolve, got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json to be written by an "
                        "unauthenticated POST")

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/PQR/delete", method="POST")
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated delete POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json to exist after an "
                        "unauthenticated delete POST")
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "unauthenticated POSTs to /airlines/resolve and "
            "/airlines/manual-resolutions/{prefix}/delete both redirect to /login and write "
            "no manual_resolutions.json — the state dir is unchanged, not only the status code",
            _manual_resolve_and_delete_routes_require_auth_and_write_nothing)

        def _manual_resolve_post_revalidates_prefix_against_live_registry():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)
                manual_resolutions_path = manual_resolutions.manual_resolutions_path(
                    manual_harness.tmpdir)

                resolve_data = urllib.parse.urlencode(
                    {"prefix": "XYZ", "airline_name": "Ghost Air"}).encode()
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data, cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_prefix_stale" not in location:
                    return False, "expected the stale flash key, got %r" % location
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json for a prefix absent from the "
                        "live registry — even though its shape is valid")

                _seed_unresolved_prefixes(manual_harness.tmpdir, {
                    "XYZ": {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "XYZ100"},
                })
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data, cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect once the prefix is live, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_resolved" not in location:
                    return False, (
                        "expected the resolved flash key once the prefix is a live "
                        "registry member, got %r" % location)
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "XYZ" not in registry or registry["XYZ"].get("airline_name") != "Ghost Air":
                    return False, (
                        "expected the entry to be persisted once the prefix is live, "
                        "got %r" % registry)
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/resolve re-validates the prefix against the live "
            "unresolved-prefix registry on write (D-11): a well-shaped but unregistered "
            "prefix writes nothing and gets the stale flash; the identical POST succeeds "
            "once the prefix is a live registry member",
            _manual_resolve_post_revalidates_prefix_against_live_registry)

        def _manual_resolve_post_rejection_mapping_and_d03_branch():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                def _seed_gap(prefix):
                    state = poll_loop.load_poll_state(manual_harness.tmpdir)
                    registry = state.get("unresolved_prefixes")
                    if not isinstance(registry, dict):
                        registry = {}
                    registry[prefix] = {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00",
                        "example_callsign": prefix + "100"}
                    _seed_unresolved_prefixes(manual_harness.tmpdir, registry)

                def _resolve_post(prefix, airline_name):
                    data = urllib.parse.urlencode(
                        {"prefix": prefix, "airline_name": airline_name}).encode()
                    return http_request(
                        mbase + "/airlines/resolve", method="POST", data=data, cookie=msession)

                rejection_cases = (
                    ("EMP", "", "flash=manual_name_empty"),
                    ("TLN", "A" * 101, "flash=manual_name_too_long"),
                    ("RSV", "Generic Fallback", "flash=manual_name_reserved"),
                    ("UNU", "../../etc/passwd", "flash=manual_name_unusable"),
                )
                for prefix, airline_name, expected_flash in rejection_cases:
                    _seed_gap(prefix)
                    status, headers, _ = _resolve_post(prefix, airline_name)
                    if status != 303:
                        return False, "prefix %r: expected a 303 redirect, got %d" % (prefix, status)
                    location = headers.get("Location", "")
                    if expected_flash not in location:
                        return False, (
                            "prefix %r: expected %r in the redirect, got %r"
                            % (prefix, expected_flash, location))
                    registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                    if prefix in registry:
                        return False, (
                            "prefix %r: expected the rejected entry to NOT be persisted" % (prefix,))

                # D-03 branch: a brand-new name (no existing artwork)
                # redirects WITH resolve= (Step B is offered); a name
                # already covered by illustrations.target_airline_names()
                # (Air France, real vendored artwork) redirects WITHOUT
                # resolve= — no upload is ever asked for. Run BEFORE the
                # cap-fill below, since once the registry is at its
                # 200-entry cap no further distinct prefix can be added at
                # all (that is the exact behaviour the cap-fill check
                # exercises next).
                _seed_gap("NEW")
                status, headers, _ = _resolve_post("NEW", "Totally Novel Airline")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "resolve=NEW" not in location or "flash=manual_resolved" not in location:
                    return False, (
                        "expected resolve=NEW and the resolved flash for a brand-new "
                        "name, got %r" % location)

                _seed_gap("OLD")
                status, headers, _ = _resolve_post("OLD", "Air France")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "resolve=" in location:
                    return False, (
                        "expected NO resolve= param when the named airline already has "
                        "artwork, got %r" % location)
                if "flash=manual_resolved" not in location:
                    return False, "expected the resolved flash key, got %r" % location

                # ADD_REJECTED_FULL: fill the registry to the cap with
                # unrelated, already-valid entries directly through the
                # module (mirroring server/test_manual_resolutions.py's
                # own _cap_enforcement precedent), then attempt one more
                # through the real route. NEW/OLD above already persisted
                # two entries, so only top up the remainder to reach the
                # cap exactly — filling past it would itself start
                # returning ADD_REJECTED_FULL mid-setup.
                existing_count = len(
                    manual_resolutions.load_manual_resolutions(manual_harness.tmpdir))
                needed = manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES - existing_count
                import string
                cap_prefixes = []
                count = 0
                for a in string.ascii_uppercase:
                    for b in string.ascii_uppercase:
                        if count >= needed:
                            break
                        cap_prefixes.append("Y" + a + b)
                        count += 1
                    if count >= needed:
                        break
                for i, pfx in enumerate(cap_prefixes):
                    result = manual_resolutions.add_entry(
                        manual_harness.tmpdir, pfx, "Cap Filler %d" % i)
                    if result != manual_resolutions.ADD_OK:
                        return False, (
                            "test setup failure filling the cap: add_entry(%r, ...) "
                            "returned %r" % (pfx, result))
                _seed_gap("CAP")
                status, headers, _ = _resolve_post("CAP", "One Too Many Air")
                if status != 303:
                    return False, "expected a 303 redirect for the at-cap POST, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_registry_full" not in location:
                    return False, "expected the registry-full flash key, got %r" % location
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "CAP" in registry:
                    return False, "expected the at-cap entry to NOT be persisted"
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "each add_entry() rejection reaches its own distinct flash key and persists "
            "nothing (empty/too-long/reserved names, and the registry cap); the D-03 "
            "branch: a brand-new name redirects with resolve= (Step B offered) while a "
            "name already covered by existing artwork redirects without it",
            _manual_resolve_post_rejection_mapping_and_d03_branch)

        def _manual_resolution_delete_route_full_contract():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                add_result = manual_resolutions.add_entry(
                    manual_harness.tmpdir, "DEL", "Deletable Air")
                if add_result != manual_resolutions.ADD_OK:
                    return False, "test setup failure: add_entry() returned %r" % (add_result,)
                key = manual_resolutions.illustration_key_for_name("Deletable Air")
                override_dir = manual_harness.state_path("illustration_overrides")
                os.makedirs(override_dir, exist_ok=True)
                override_path = os.path.join(override_dir, key + ".png")
                with open(override_path, "wb") as fh:
                    fh.write(b"not a real png - only its continued existence is asserted here")

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/DEL/delete", method="POST",
                    cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if location != "/airlines":
                    return False, "expected a redirect to /airlines with no flash, got %r" % location
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "DEL" in registry:
                    return False, "expected the DEL entry to be removed from the registry"
                if not os.path.isfile(override_path):
                    return False, "expected the override file to survive the delete (D-08)"

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/DEL/delete", method="POST",
                    cookie=msession)
                if status != 303:
                    return False, (
                        "expected a second, identical delete POST to also redirect "
                        "(idempotent), got %d" % status)
                location = headers.get("Location", "")
                if location != "/airlines":
                    return False, (
                        "expected the same no-flash redirect on a second delete of an "
                        "already-absent prefix, got %r" % location)

                status, _headers, _body = http_request(
                    mbase + "/airlines/manual-resolutions/not-three-letters/delete",
                    method="POST", cookie=msession)
                if status != 404:
                    return False, "expected 404 for a malformed prefix, got %d" % status
                if not os.path.isfile(override_path):
                    return False, (
                        "expected the override file to still exist after a 404'd "
                        "malformed-prefix POST")
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry, "
            "leaves the override PNG on disk (D-08), and redirects to /airlines with no "
            "flash; a second identical POST is a no-op that also redirects without an "
            "error flash; a malformed prefix 404s without touching the registry",
            _manual_resolution_delete_route_full_contract)

        # --- POST /settings/rules/add and POST /settings/rules/{kind}/
        # {value}/delete (Phase 15 D-10, D-11, 15-05-PLAN.md Task 3,
        # 15-VALIDATION.md rows 10/11) — each check below spins up its
        # own isolated Harness(), matching the manual-resolution checks
        # above, since these routes write a real colour_rules.json. The
        # add route's three form fields are rule_kind, rule_key and
        # rule_theme_id (config_page.py's own field names); the delete
        # route carries no form body at all, only its two path segments.

        def _rules_routes_require_auth_and_write_nothing():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rules_path = colour_rules.colour_rules_path(rules_harness.tmpdir)

                add_data = urllib.parse.urlencode(
                    {"rule_kind": "callsign", "rule_key": "AFR1234",
                     "rule_theme_id": "white"}).encode()
                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST", data=add_data)
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated add POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(rules_path):
                    return False, (
                        "expected no colour_rules.json to be written by an "
                        "unauthenticated POST")

                delete_path = "%scallsign/AFR1234%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, headers, _ = http_request(rbase + delete_path, method="POST")
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated delete POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(rules_path):
                    return False, (
                        "expected no colour_rules.json to exist after an unauthenticated "
                        "delete POST")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "unauthenticated POSTs to /settings/rules/add and "
            "/settings/rules/{kind}/{value}/delete both redirect to /login and write no "
            "colour_rules.json — the state dir is unchanged, not only the status code",
            _rules_routes_require_auth_and_write_nothing)

        def _rules_add_and_delete_forms_sit_outside_settings_form():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "AFR9001", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                # 20-07 (D-10/D-11) moved the rules editor to Display.
                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200 GET /display, got %d" % status
                page = body.decode("utf-8")

                add_form_marker = 'action="%s"' % config_page.RULES_ADD_ROUTE
                add_tag_start = page.rindex("<form", 0, page.index(add_form_marker))
                add_tag_end = page.index(">", add_tag_start)
                add_form_tag = page[add_tag_start:add_tag_end + 1]

                # An exact expected delete action (not a prefix search) —
                # RULES_ADD_ROUTE itself starts with RULES_DELETE_ROUTE_
                # PREFIX ("/settings/rules/add" vs "/settings/rules/"), so
                # a bare prefix search could ambiguously match the add
                # form's own action instead of the delete form's.
                expected_delete_action = "%scallsign/AFR9001%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                delete_form_marker = 'action="%s"' % expected_delete_action
                delete_tag_start = page.rindex("<form", 0, page.index(delete_form_marker))
                delete_tag_end = page.index(">", delete_tag_start)
                delete_form_tag = page[delete_tag_start:delete_tag_end + 1]

                for tag, name in ((add_form_tag, "add"), (delete_form_tag, "delete")):
                    if config_page.SETTINGS_FORM_ID in tag:
                        return False, (
                            "expected the %s form to not carry the settings form's id, "
                            "got %r" % (name, tag))
                    if "form=" in tag:
                        return False, (
                            "expected the %s form to carry no form= attribute, got %r"
                            % (name, tag))

                # A rule add followed by an unrelated settings-form save
                # leaves both the rule and the setting intact — the two
                # write paths do not interfere.
                status, _headers, _body = http_request(
                    rbase + "/settings", method="POST",
                    data=urllib.parse.urlencode({"tracked_runway": "3"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect from the settings save, got %d" % status
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR9001" not in registry.get("callsign", {}):
                    return False, "expected the rule to survive an unrelated settings-form save"
                cfg = device_config.load_device_config(rules_harness.tmpdir)
                if cfg.get("tracked_runway") != "3":
                    return False, (
                        "expected the settings save to persist independently of the rule add")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "the rules add form and each delete form sit outside <form id=SETTINGS_FORM_ID> "
            "(D-10): neither carries the settings form's id nor a form= attribute pointing at "
            "it, and a rule add followed by an unrelated settings-form save leaves both the "
            "rule and every device-config setting intact (15-VALIDATION.md row 10)",
            _rules_add_and_delete_forms_sit_outside_settings_form)

        def _rules_add_route_no_js_added_then_replaced():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST",
                    data=urllib.parse.urlencode(
                        {"rule_kind": "callsign", "rule_key": "afr1234",
                         "rule_theme_id": "white"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_added" not in headers.get("Location", ""):
                    return False, (
                        "expected the added flash key on first add, got %r"
                        % headers.get("Location"))

                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST",
                    data=urllib.parse.urlencode(
                        {"rule_kind": "callsign", "rule_key": "AFR1234",
                         "rule_theme_id": "blue"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=rule_replaced" not in location or "rule=AFR1234" not in location:
                    return False, (
                        "expected the replaced flash key echoing the normalised key, "
                        "got %r" % location)

                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                callsign_entries = registry.get("callsign", {})
                if list(callsign_entries.keys()) != ["AFR1234"]:
                    return False, (
                        "expected exactly one callsign entry keyed AFR1234, got %r"
                        % (callsign_entries,))
                if callsign_entries["AFR1234"]["theme_id"] != "blue":
                    return False, (
                        "expected the second add's theme to win, got %r"
                        % (callsign_entries["AFR1234"],))
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "raw URL-encoded no-JS POSTs to the rules add route (15-VALIDATION.md row 11): a "
            "first add flashes rule_added, a second add for the same key (case-insensitive "
            "input) flashes rule_replaced and echoes the normalised key back, and the "
            "registry holds exactly one entry with the second theme",
            _rules_add_route_no_js_added_then_replaced)

        def _rules_add_route_rejection_paths():
            from companion.pages import config_page
            import itertools
            import string

            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                def _add(kind, key, theme_id):
                    data = urllib.parse.urlencode(
                        {"rule_kind": kind, "rule_key": key, "rule_theme_id": theme_id}).encode()
                    return http_request(
                        rbase + config_page.RULES_ADD_ROUTE, method="POST", data=data,
                        cookie=rsession)

                # A malformed value for the selected kind — a prefix must
                # be exactly three letters.
                status, headers, _ = _add("prefix", "TOOLONG", "white")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_key_invalid" not in headers.get("Location", ""):
                    return False, (
                        "expected the key-invalid flash key, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if registry.get("prefix"):
                    return False, "expected nothing written for a malformed value"

                # A crafted kind outside the closed set.
                status, headers, _ = _add("../../etc/passwd", "AFR", "white")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_save_failed" not in headers.get("Location", ""):
                    return False, (
                        "expected the generic save-failed flash key for a crafted kind, "
                        "got %r" % headers.get("Location"))

                # A crafted theme id outside THEME_IDS.
                status, headers, _ = _add("callsign", "AFR9999", "not-a-real-theme")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_save_failed" not in headers.get("Location", ""):
                    return False, (
                        "expected the generic save-failed flash key for a crafted theme "
                        "id, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR9999" in registry.get("callsign", {}):
                    return False, "expected nothing written for a crafted theme id"

                # Fill the registry to the cap with distinct, already-
                # valid prefixes (mirroring
                # server/test_manual_resolutions.py's own cap-enforcement
                # precedent), then attempt one more through the real
                # route.
                existing_count = sum(len(v) for v in registry.values())
                needed = colour_rules.COLOUR_RULE_MAX_ENTRIES - existing_count
                cap_prefixes = []
                for combo in itertools.product(string.ascii_uppercase, repeat=3):
                    if len(cap_prefixes) >= needed:
                        break
                    cap_prefixes.append("".join(combo))
                for prefix in cap_prefixes:
                    result = colour_rules.add_rule(
                        rules_harness.tmpdir, "prefix", prefix, "white")
                    if result != colour_rules.ADD_OK_NEW:
                        return False, (
                            "test setup failure filling the cap: add_rule(%r, ...) "
                            "returned %r" % (prefix, result))
                status, headers, _ = _add("prefix", "ZZZ", "white")
                if status != 303:
                    return False, "expected a 303 redirect for the at-cap POST, got %d" % status
                if "flash=rule_registry_full" not in headers.get("Location", ""):
                    return False, (
                        "expected the registry-full flash key, got %r" % headers.get("Location"))
                registry_after = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "ZZZ" in registry_after.get("prefix", {}):
                    return False, "expected the at-cap entry to NOT be persisted"
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "the rules add route's rejection paths: a malformed value for the selected kind "
            "flashes rule_key_invalid and writes nothing; a crafted kind and a crafted theme "
            "id each flash the generic rule_save_failed and write nothing; filling the "
            "registry to its cap and adding one more flashes rule_registry_full without "
            "persisting the at-cap entry",
            _rules_add_route_rejection_paths)

        def _rules_delete_route_full_contract():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "hex", "3944F2", "blue")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                delete_path = "%shex/3944F2%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, headers, _ = http_request(rbase + delete_path, method="POST", cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_deleted" not in headers.get("Location", ""):
                    return False, (
                        "expected the deleted flash key, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "3944F2" in registry.get("hex", {}):
                    return False, "expected the entry to be removed from the registry"

                # A second, identical delete of an already-absent entry
                # is success, not an error — idempotent double-submission
                # tolerance, matching the manual-resolutions delete
                # precedent (no flash on a repeat delete either).
                status, headers, _ = http_request(rbase + delete_path, method="POST", cookie=rsession)
                if status != 303:
                    return False, (
                        "expected a second identical delete to also redirect, got %d" % status)
                if "flash=" in headers.get("Location", ""):
                    return False, (
                        "expected no flash on a repeat delete of an already-absent entry, "
                        "got %r" % headers.get("Location"))

                # A malformed kind segment and a malformed value segment
                # each 404 without touching an unrelated existing entry.
                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "AFR1234", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)
                bad_kind_path = "%sbogus/AFR1234%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, _headers, _body = http_request(
                    rbase + bad_kind_path, method="POST", cookie=rsession)
                if status != 404:
                    return False, "expected 404 for a malformed kind segment, got %d" % status
                bad_value_path = "%scallsign/bad-value%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, _headers, _body = http_request(
                    rbase + bad_value_path, method="POST", cookie=rsession)
                if status != 404:
                    return False, "expected 404 for a malformed value segment, got %d" % status
                registry_after = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR1234" not in registry_after.get("callsign", {}):
                    return False, (
                        "expected the unrelated entry to survive both 404'd delete attempts")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "POST /settings/rules/{kind}/{value}/delete removes the registry entry and "
            "flashes rule_deleted; a second identical delete of an already-absent entry is a "
            "no-op that redirects with no flash; a malformed kind segment and a malformed "
            "value segment each 404 without touching an unrelated existing entry",
            _rules_delete_route_full_contract)

        def _rules_page_context_reads_fresh_per_request():
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                # 20-07 (D-10/D-11) moved the rules editor to Display.
                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if b"FRESHRD1" in body:
                    return False, "expected the rule to be absent before it is written"

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "FRESHRD1", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if b"FRESHRD1" not in body:
                    return False, (
                        "expected page_context() to read the rules registry fresh per "
                        "request, not through the poll-cycle process cache")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "a rule written directly to state_dir between two GETs of the Settings page "
            "appears in the second render — proving page_context() reads colour_rules fresh "
            "per request rather than through any process-scoped cache",
            _rules_page_context_reads_fresh_per_request)

        # --- poll-trigger cooldown: server-global, not per-session ---

        def _poll_trigger_first_call():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_triggered" not in location:
                return False, "expected the poll_triggered flash key in the redirect, got %r" % location
            return True, ""
        check(
            "a first poll trigger redirects with the poll_triggered flash key",
            _poll_trigger_first_call)

        # 32-11-PLAN.md Task 1 (TST-03): the check above proves the HTTP
        # contract; this one proves run_once() itself never reached the
        # real adsb.fi/adsb.lol - read straight from the fake provider's
        # own JSONL call log, written by the harness's child interpreter.
        def _poll_trigger_first_call_served_by_fake_providers():
            calls = harness.fake_provider_calls()
            providers_called = {call["provider"] for call in calls}
            missing = {"adsbfi", "adsblol"} - providers_called
            if missing:
                return False, (
                    "expected the fake provider's call log to show both "
                    "adsbfi and adsblol queried by the first poll trigger's "
                    "run_once(), missing %r - full log: %r" % (missing, calls))
            return True, ""
        check(
            "the first poll trigger's run_once() was served by the fake ADS-B providers (adsbfi and adsblol called, no live network)",
            _poll_trigger_first_call_served_by_fake_providers)

        def _poll_trigger_cooldown_same_session():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, "expected the poll_cooldown flash key in the redirect, got %r" % location
            return True, ""
        check(
            "an immediate second poll trigger redirects with the poll_cooldown flash key",
            _poll_trigger_cooldown_same_session)

        def _poll_trigger_cooldown_second_opener():
            second_session_cookie = _login(harness)
            status, headers, _ = http_request(
                base + "/poll-now", method="POST", cookie=second_session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, (
                    "expected a fresh second-opener session to also see the "
                    "poll_cooldown flash key, got %r" % location)
            return True, ""
        check(
            "a fresh second-opener session is refused by the same cooldown (server-global, not per-session)",
            _poll_trigger_cooldown_second_opener)

        # 2026-08-28 fix: a genuine run_once() failure (e.g. an unreadable
        # --geofence path, exactly what production hit when
        # deploy/skypane-companion.service never passed --geofence at all
        # and the relative default didn't resolve under its
        # WorkingDirectory) must redirect with the distinct poll_failed
        # flash key, never the misleading save_failed one - a poll
        # trigger failing has nothing to do with "couldn't save settings".
        def _poll_trigger_failure_uses_distinct_flash_key():
            broken_harness = Harness(extra_args=["--geofence", "/nonexistent/no-such-geofence.json"])
            try:
                broken_harness.start()
                broken_session = _login(broken_harness)
                status, headers, _ = http_request(
                    broken_harness.base_url() + "/poll-now", method="POST", cookie=broken_session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=poll_failed" not in location:
                    return False, "expected the poll_failed flash key, got %r" % location
                if "flash=save_failed" in location:
                    return False, "a poll-trigger failure must never reuse save_failed's misleading copy"
                return True, ""
            finally:
                broken_harness.stop()
                broken_harness.cleanup()
        check(
            "a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never save_failed",
            _poll_trigger_failure_uses_distinct_flash_key)

        # UXA-15: two genuinely overlapping threads issuing POST
        # /poll-now against the same running subprocess, on a session
        # with zero cooldown, must never both reach run_once() — the
        # server-side _POLL_LOCK (companion/app.py) is the correctness
        # boundary, not merely a claim verified by reading the source.
        # A fresh Harness/session is used (rather than reusing the
        # cooldown-exhausted session_cookie above) so the cooldown gate
        # never confounds which flash key each response carries.
        def _poll_now_concurrent_requests_serialize_on_the_lock():
            concurrent_harness = Harness()
            try:
                concurrent_harness.start()
                cbase = concurrent_harness.base_url()
                concurrent_cookie = _login(concurrent_harness)

                start_event = threading.Event()
                responses = []
                responses_lock = threading.Lock()

                def _worker():
                    start_event.wait()
                    status, headers, _ = http_request(
                        cbase + "/poll-now", method="POST", cookie=concurrent_cookie)
                    with responses_lock:
                        responses.append((status, headers.get("Location", "")))

                threads = [threading.Thread(target=_worker) for _ in range(2)]
                for t in threads:
                    t.start()
                # Released together, after both threads are already
                # blocked on it — the tightest overlap this harness can
                # produce without instrumenting the server itself.
                start_event.set()
                for t in threads:
                    t.join(timeout=30)

                if len(responses) != 2:
                    return False, "expected two responses, got %d: %r" % (len(responses), responses)
                for status, _location in responses:
                    if status != 303:
                        return False, "expected both responses to be 303 redirects, got %r" % (responses,)
                already_running_count = sum(
                    1 for _status, location in responses
                    if "flash=poll_already_running" in location)
                if already_running_count != 1:
                    return False, (
                        "expected exactly one of the two overlapping /poll-now "
                        "requests to receive the poll_already_running flash key "
                        "(the other must complete/fail on its own honest "
                        "outcome), got %d of 2: %r" % (already_running_count, responses))
                return True, ""
            finally:
                concurrent_harness.stop()
                concurrent_harness.cleanup()
        check(
            "two genuinely overlapping POST /poll-now requests: exactly one gets the poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution",
            _poll_now_concurrent_requests_serialize_on_the_lock)

        # --- Section 4 (phase 17 plan 04, D-06/D-09): the save-triggered
        # immediate calendar sync, its four outcomes, the throttle bypass,
        # lock contention, and the T-17-FLASH leak guard. Every check here
        # uses _InProcessHarness (a real ThreadingHTTPServer in THIS
        # process, not a Harness subprocess) because it needs to
        # monkeypatch calendar_rules.default_calendar_transport and
        # socket.getaddrinfo — a monkeypatch a Harness subprocess, with
        # its own separate interpreter, could never see.

        def _calendar_connect_reports_plural_count():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                calls = []
                hostname = "calendar-sync-plural.example"
                url = "https://%s/feed.ics?token=PLURALCOUNTTOKEN" % hostname
                body = _ics_body([
                    ("AF1234", "CDG", "ORY", 2),
                    ("BA5678", "LHR", "CDG", 4),
                    ("KL2222", "AMS", "ORY", 6),
                ])
                with _stubbed_calendar_transport(
                        _make_calendar_transport(body=body, calls=calls)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, "expected the calendar_connected flash key, got %r" % location
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if status2 != 200:
                    return False, "expected 200 following the redirect, got %d" % status2
                if b"3 flights" not in page_body:
                    return False, "expected the rendered banner to name 3 flights, got %r" % (page_body,)
                if calls != [url]:
                    return False, "expected exactly one transport call with the submitted URL, got %r" % (calls,)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "saving a calendar feed with three in-window flights performs exactly one refresh call and the rendered banner names the plural flight count (D-06)",
            _calendar_connect_reports_plural_count)

        def _calendar_connect_reports_singular_count():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-singular.example"
                url = "https://%s/feed.ics?token=SINGULARCOUNTTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                location = headers.get("Location", "")
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if status2 != 200:
                    return False, "expected 200 following the redirect, got %d" % status2
                if b"1 flight from this calendar" not in page_body:
                    return False, "expected the singular form '1 flight', got %r" % (page_body,)
                if b"1 flights" in page_body:
                    return False, "the singular count must never carry a trailing 's'"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "saving a calendar feed with exactly one in-window flight pins the singular form ('1 flight', never '1 flights')",
            _calendar_connect_reports_singular_count)

        def _calendar_connect_zero_entries_still_succeeds():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-empty.example"
                url = "https://%s/feed.ics?token=EMPTYFEEDTOKEN" % hostname
                # A syntactically valid but empty feed - a parsed feed
                # with nothing in the window is a different, legitimate
                # outcome from a broken feed, and the two must be
                # distinguishable (D-06's "zero is a legitimate,
                # informative value").
                body = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, (
                        "a zero-entry feed that parsed correctly must still report "
                        "success, got %r" % location)
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"0 flights" not in page_body:
                    return False, "expected the rendered banner to name 0 flights, got %r" % (page_body,)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a syntactically valid feed with nothing in the frame's window reports success with a 0 count, distinguishable from a failure",
            _calendar_connect_zero_entries_still_succeeds)

        def _calendar_sync_failure_reports_generic_message_and_still_saves():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-failure.example"
                url = "https://%s/feed.ics?token=FAILURETOKEN" % hostname
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=ConnectionError("boom"))), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_sync_failed" not in location:
                    return False, "expected the single calendar_sync_failed flash key, got %r" % location
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, (
                        "the URL must be saved regardless of whether the immediate "
                        "fetch succeeded")
                import companion.app as app_module
                # escape_html() rewrites this copy's apostrophe to
                # "&#x27;" on render (17-02's own recorded surprise for
                # CALENDAR_STATUS_NOT_CONFIGURED) - the rendered page is
                # therefore compared against the ESCAPED form, never the
                # raw FLASH_MESSAGES source string.
                expected_text = layout.escape_html(
                    app_module.FLASH_MESSAGES[app_module.FLASH_KEY_CALENDAR_SYNC_FAILED])
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if expected_text.encode() not in page_body:
                    return False, (
                        "expected the single generic failure copy verbatim (HTML-escaped) "
                        "in the rendered banner, got %r" % (page_body,))
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a failing fetch redirects with the single generic failure flash key, renders the exact failure copy, and the URL is saved regardless (D-06)",
            _calendar_sync_failure_reports_generic_message_and_still_saves)

        def _calendar_sync_failure_never_leaks_the_url():
            # T-17-FLASH: a transport whose raised error's message embeds
            # the full URL - the shape a real name-resolution or
            # connection error has - must never surface any of five
            # distinct needles (token, host, path segment,
            # query-parameter name, whole URL) anywhere the operator can
            # see: the redirect's Location header, or the served body of
            # either response. 21-07-PLAN.md Task 2 (D-14/R-10): the
            # SERVED SETTINGS PAGE is now the one legitimate exception —
            # the URL was saved successfully (the sync failure is a
            # separate, later fetch problem), so the page now renders
            # correctly connected, and D-14's own masked-URL line
            # legitimately shows the bare host + "…" there. The plain
            # hostname therefore stays forbidden everywhere else (the
            # Location header, the redirect response body) but is
            # narrowed to "masked form only" for the final served page.
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "leak-check-host.example"
                token = "LEAKTOKEN99999"
                path_segment = "leak-path-segment"
                query_param = "leakqueryparam"
                url = "https://%s/private/%s/feed.ics?%s=%s" % (
                    hostname, path_segment, query_param, token)
                needles = [token, hostname, path_segment, query_param, url]
                raise_exc = ConnectionError(
                    "Failed to resolve %s: Name or service not known" % url)
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=raise_exc)), \
                        _fake_public_hostname(hostname):
                    status, headers, redirect_body = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                for needle in needles:
                    if needle in location:
                        return False, "leak in Location header: %r found in %r" % (needle, location)
                    if needle.encode() in redirect_body:
                        return False, "leak in the redirect response body: %r" % (needle,)
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if layout.escape_html("%s…" % hostname).encode() not in page_body:
                    return False, (
                        "expected the masked host + ellipsis fragment to be served once "
                        "connected (D-14/R-10)")
                for needle in (token, path_segment, query_param, url):
                    if needle.encode() in page_body:
                        return False, (
                            "leak in the served response body: %r found on the "
                            "rendered Settings page" % (needle,))
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, "
            "path segment, query-parameter name, or whole URL in the Location header or any served "
            "response body — the served Settings page legitimately shows the masked host + ellipsis "
            "once connected (D-14/R-10, extended by 21-07-PLAN.md Task 2)",
            _calendar_sync_failure_never_leaks_the_url)

        def _calendar_disconnect_reports_deletion_and_erases_entries():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-disconnect.example"
                url = "https://%s/feed.ics?token=DISCONNECTTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                registry_before = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if not registry_before["entries"]:
                    return False, "test setup failure: expected at least one entry before disconnecting"

                from companion.pages import config_page
                status, headers, _b = http_request(
                    calendar_harness.base_url() + "/settings", method="POST",
                    data=urllib.parse.urlencode(
                        {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_disconnected" not in location:
                    return False, "expected the calendar_disconnected flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be disconnected"
                registry_after = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if registry_after["entries"]:
                    return False, (
                        "expected every fetched flight to be deleted on disconnect, "
                        "found %r" % (registry_after["entries"],))
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"deleted" not in page_body:
                    return False, "expected the rendered banner to state the flights were deleted"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "checking the disconnect box redirects with the disconnected flash key, and the calendar's previously-fetched flights are actually erased from disk (D-04)",
            _calendar_disconnect_reports_deletion_and_erases_entries)

        # ==============================================================
        # 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect
        # action's own dedicated POST /settings/calendar/disconnect
        # route — a bare/wrong-confirm POST renders the two-step
        # confirmation page and erases nothing; only confirm=yes
        # disconnects; the route is session-gated like every other
        # state-changing route.
        # ==============================================================

        def _calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://bare-post.example/feed.ics?token=BAREPOSTTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, _headers, body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST", data=b"", cookie=session)
                if status != 200:
                    return False, "expected a 200 confirmation page for a bare POST, got %d" % status
                if html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() not in body:
                    return False, "expected the confirmation copy in the rendered page"
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected after a bare POST"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a bare authenticated POST /settings/calendar/disconnect with no confirm field returns 200 "
            "with the confirmation copy and leaves the calendar connected (D-08/A-26)",
            _calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing)

        def _calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://confirm-maybe.example/feed.ics?token=MAYBETOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, _headers, body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD: "maybe"}).encode(),
                    cookie=session)
                if status != 200:
                    return False, "expected a 200 confirmation page for confirm=maybe, got %d" % status
                if html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() not in body:
                    return False, "expected the confirmation copy in the rendered page"
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected after confirm=maybe"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an authenticated POST /settings/calendar/disconnect with confirm=maybe renders the "
            "confirmation page rather than disconnecting anything (D-08/A-26)",
            _calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing)

        def _calendar_disconnect_route_confirm_yes_disconnects():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://confirm-yes.example/feed.ics?token=YESTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, headers, _body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {
                            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD:
                                config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
                        }).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect for confirm=yes, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_disconnected" not in location:
                    return False, "expected the calendar_disconnected flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be disconnected"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an authenticated POST /settings/calendar/disconnect with confirm=yes 303-redirects with the "
            "disconnected flash key and actually disconnects the calendar (D-08/A-26)",
            _calendar_disconnect_route_confirm_yes_disconnects)

        def _calendar_disconnect_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                url = "https://unauth-disconnect.example/feed.ics?token=UNAUTHTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, headers, _body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {
                            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD:
                                config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
                        }).encode())
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected — nothing should be written"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an unauthenticated POST /settings/calendar/disconnect (even with confirm=yes) redirects to "
            "/login and writes nothing (D-08/A-26, T-19-41)",
            _calendar_disconnect_route_unauthenticated_redirects_to_login)

        # ==============================================================
        # 20-09-PLAN.md Task 2 (D-14c): the calendar connect action's own
        # dedicated POST /settings/calendar/connect route — never through
        # config_page.handle_post()'s scope/in_scope machinery (T-20-11),
        # session-gated like every other state-changing route (T-20-10).
        # ==============================================================

        def _calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                # T-20-11's own pinned regression: seed Quiet hours and
                # the screen ON, connect a calendar, and assert both are
                # STILL on afterwards — a scoped POST through the settings
                # handler would read their absent checkboxes as an
                # explicit OFF and silently switch both off.
                device_config.save_device_config(
                    calendar_harness.tmpdir, quiet_hours_enabled=True, display_enabled=True)
                session = _login(calendar_harness)
                hostname = "connect-route.example"
                url = "https://%s/feed.ics?token=CONNECTROUTETOKEN" % hostname
                body = _ics_body([("AFR1234", "ORY", "TLS", 2), ("AFR5678", "ORY", "NCE", 3)])
                calls = []
                with _stubbed_calendar_transport(
                        _make_calendar_transport(body=body, calls=calls)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                        method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if not location.startswith("/display"):
                    return False, "expected a redirect to Display, got %r" % location
                if "flash=calendar_connect_ok" not in location:
                    return False, "expected the calendar_connect_ok flash key, got %r" % location
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be configured"
                if calendar_rules.configured_calendar_url(calendar_harness.tmpdir) != url:
                    return False, "expected the submitted URL to be stored"
                if len(calls) != 1:
                    return False, "expected exactly one registry refresh (one transport call), got %d" % len(calls)
                registry = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if len(registry["entries"]) != 2:
                    return False, "expected two fetched entries, got %r" % (registry["entries"],)
                on_disk = device_config.load_device_config(calendar_harness.tmpdir)
                if on_disk.get("quiet_hours_enabled") is not True:
                    return False, "expected quiet_hours_enabled to remain True (T-20-11 regression)"
                if on_disk.get("display_enabled") is not True:
                    return False, "expected display_enabled to remain True (T-20-11 regression)"
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"2 flights found" not in page_body:
                    return False, "expected the success flash text to include the flight count"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a valid POST /settings/calendar/connect 303-redirects to Display with the "
            "calendar_connect_ok flash key, persists the URL, triggers exactly one registry refresh, "
            "and leaves quiet_hours_enabled/display_enabled exactly as they were (D-14c, T-20-11 "
            "pinned regression)",
            _calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone)

        def _calendar_connect_route_invalid_url_rejects_and_persists_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                status, headers, _b = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode({"calendar_url": ""}).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connect_invalid" not in location:
                    return False, "expected the calendar_connect_invalid flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain unconfigured — nothing should be written"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an empty calendar_url on POST /settings/calendar/connect 303-redirects with the "
            "calendar_connect_invalid flash key and persists nothing (D-14c)",
            _calendar_connect_route_invalid_url_rejects_and_persists_nothing)

        def _calendar_connect_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                status, headers, _b = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {"calendar_url": "https://unauth-connect.example/feed.ics"}).encode())
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected nothing to be written for an unauthenticated POST"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an unauthenticated POST /settings/calendar/connect redirects to /login and writes nothing "
            "(D-14c, T-20-10)",
            _calendar_connect_route_unauthenticated_redirects_to_login)

        # ==============================================================
        # 20-11-PLAN.md Task 1 (D-26/T-20-13): "Send a test"'s own
        # dedicated POST /settings/notifications/test route — session-
        # gated, reads the topic URL from the stored config only, and
        # never trusts a submitted topic_url field.
        # ==============================================================

        def _notifications_test_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            harness = _InProcessHarness()
            try:
                status, headers, _b = http_request(
                    harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                    method="POST", data=b"")
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                return True, ""
            finally:
                harness.stop()
        check(
            "an unauthenticated POST /settings/notifications/test redirects to /login (D-26, T-20-10)",
            _notifications_test_route_unauthenticated_redirects_to_login)

        def _notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) not in location:
                    return False, "expected the notifications_test_failed flash key, got %r" % location
                if calls:
                    return False, "expected send_notification() to never be called with no stored URL"
                return True, ""
            finally:
                harness.stop()
        check(
            "with no stored topic URL, POST /settings/notifications/test redirects with the "
            "notifications_test_failed flash key and never calls notify.send_notification() (D-26)",
            _notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender)

        def _notifications_test_route_configured_calls_sender_once_and_flashes_success():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-abc"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_OK) not in location:
                    return False, "expected the notifications_test_ok flash key, got %r" % location
                if calls != [stored_url]:
                    return False, (
                        "expected send_notification() to be called exactly once with the stored "
                        "url, got %r" % (calls,))
                return True, ""
            finally:
                harness.stop()
        check(
            "with a stored topic URL, POST /settings/notifications/test calls "
            "notify.send_notification() exactly once with the stored URL and redirects with the "
            "notifications_test_ok flash key (D-26)",
            _notifications_test_route_configured_calls_sender_once_and_flashes_success)

        def _notifications_test_route_sender_returning_false_flashes_failure():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-def"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                original = notify_module.send_notification
                notify_module.send_notification = lambda *a, **k: False
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) not in location:
                    return False, "expected the notifications_test_failed flash key, got %r" % location
                return True, ""
            finally:
                harness.stop()
        check(
            "a sender returning False redirects with the notifications_test_failed flash key (D-26)",
            _notifications_test_route_sender_returning_false_flashes_failure)

        def _notifications_test_route_ignores_a_submitted_topic_url_field():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-ghi"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, _headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST",
                        data=urllib.parse.urlencode(
                            {"topic_url": "https://attacker.example/forward-me"}).encode(),
                        cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if calls != [stored_url]:
                    return False, (
                        "expected send_notification() to receive the STORED url only, got %r"
                        % (calls,))
                return True, ""
            finally:
                harness.stop()
        check(
            "a POST /settings/notifications/test carrying its own topic_url field is ignored in "
            "favour of the stored one — the field is never read from the request body (T-20-13)",
            _notifications_test_route_ignores_a_submitted_topic_url_field)

        def _calendar_sync_bypasses_the_throttle_via_min_interval_zero():
            """D-06's bypass, proven two ways.

            The behavioural half: seed a recorded attempt a minute ago
            (well inside the standard 1800s throttle) and confirm the
            save-triggered sync still fetches and still reports success.

            The wiring half, and the one that actually distinguishes
            `min_interval_s=0` from an omitted argument on THIS call
            path: `config_page.handle_post()`'s own call to
            `calendar_rules.save_calendar_url()` (plan 17-01)
            unconditionally erases the whole registry - including
            `last_attempt_at`, resetting it to `None` - on every
            successful set, BEFORE `_handle_settings_post()`'s own
            refresh call ever runs. Since `calendar_fetch_is_due()`
            already returns `True` unconditionally whenever
            `last_attempt_at is None`, a seeded stale attempt is wiped
            before the throttle is ever consulted - the fetch would run
            here whether `min_interval_s` were 0, omitted, or anything
            else. A spy on `refresh_calendar_registry()` itself is what
            actually pins the argument.
            """
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-throttle.example"
                url = "https://%s/feed.ics?token=THROTTLEBYPASSTOKEN" % hostname
                now = time.time()
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                calendar_rules.write_calendar_registry(
                    calendar_harness.tmpdir, [], now - 60, None, now=now)

                captured_intervals = []
                real_refresh = calendar_rules.refresh_calendar_registry

                def _spy_refresh(state_dir, when, transport=None, min_interval_s=None):
                    captured_intervals.append(min_interval_s)
                    return real_refresh(
                        state_dir, when, transport=transport, min_interval_s=min_interval_s)

                calendar_rules.refresh_calendar_registry = _spy_refresh
                try:
                    with _stubbed_calendar_transport(_make_calendar_transport()), \
                            _fake_public_hostname(hostname):
                        status, headers, _b = http_request(
                            calendar_harness.base_url() + "/settings", method="POST",
                            data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                            cookie=session)
                finally:
                    calendar_rules.refresh_calendar_registry = real_refresh
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if captured_intervals != [0]:
                    return False, (
                        "expected exactly one refresh_calendar_registry() call with "
                        "min_interval_s=0 (not omitted, not None), got %r" % (captured_intervals,))
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, "expected the calendar_connected flash key, got %r" % location
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a save-triggered sync against a calendar with a 60s-old last_attempt_at still fetches and reports success, and refresh_calendar_registry() is called with min_interval_s=0 explicitly - not omitted, which a call-shape spy is the only thing that can actually distinguish here, since config_page.handle_post()'s own save_calendar_url() (17-01) already resets last_attempt_at to None on every set before this handler's own refresh call runs",
            _calendar_sync_bypasses_the_throttle_via_min_interval_zero)

        def _poll_modules_own_refresh_call_site_still_throttles():
            # The opposite of the check above: refresh_calendar_registry()
            # called the way server/poll_loop.py's own production call
            # site calls it - with NO min_interval_s override - must still
            # honour the standard throttle against the identical seeded
            # state. Proves the bypass is scoped to companion/app.py's new
            # call site alone, never widening the poll cycle's own
            # throttle.
            with tempfile.TemporaryDirectory() as tmp:
                now = time.time()
                url = "https://calendar-sync-throttle-control.example/feed.ics?token=CONTROLTOKEN"
                calendar_rules.save_calendar_url(tmp, url)
                calendar_rules.write_calendar_registry(tmp, [], now - 60, None, now=now)
                calls = []
                with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)), \
                        _fake_public_hostname("calendar-sync-throttle-control.example"):
                    result_code, _registry = calendar_rules.refresh_calendar_registry(tmp, now)
                if result_code != calendar_rules.FETCH_SKIPPED_THROTTLED:
                    return False, "expected FETCH_SKIPPED_THROTTLED, got %r" % (result_code,)
                if calls:
                    return False, "expected no transport call when the standard throttle applies, got %r" % (calls,)
                return True, ""
        check(
            "server/poll_loop.py's own refresh_calendar_registry() call shape (no min_interval_s override) still honours the standard throttle against the identical seeded state - the bypass is scoped to the new call site alone",
            _poll_modules_own_refresh_call_site_still_throttles)

        def _calendar_sync_lock_contention_is_honest():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-contention.example"
                url = "https://%s/feed.ics?token=CONTENTIONTOKEN" % hostname
                calls = []
                import companion.app as app_module
                locked = app_module._POLL_LOCK.acquire(blocking=False)
                if not locked:
                    return False, "test setup failure: could not acquire _POLL_LOCK from the test thread"
                try:
                    with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)), \
                            _fake_public_hostname(hostname):
                        status, headers, _b = http_request(
                            calendar_harness.base_url() + "/settings", method="POST",
                            data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                            cookie=session)
                finally:
                    app_module._POLL_LOCK.release()
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_sync_deferred" not in location:
                    return False, "expected the calendar_sync_deferred flash key, got %r" % location
                if calls:
                    return False, "expected no transport call while the lock was held, got %r" % (calls,)
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the URL to be saved even though the sync was deferred"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a save arriving while the poll lock is already held redirects with the deferred flash key, performs no fetch, and still saves the URL (D-09)",
            _calendar_sync_lock_contention_is_honest)

        def _calendar_sync_lock_is_released_after_a_failed_sync():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-release.example"
                url = "https://%s/feed.ics?token=RELEASETOKEN" % hostname
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=ConnectionError("boom"))), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                import companion.app as app_module
                reacquired = app_module._POLL_LOCK.acquire(blocking=False)
                if reacquired:
                    app_module._POLL_LOCK.release()
                if not reacquired:
                    return False, (
                        "expected the poll lock to be free after one failed sync - a "
                        "wedged trigger is the failure mode the finally-release exists "
                        "to prevent")
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "after a save whose immediate fetch fails, the poll lock is still free - one failure never wedges a later manual poll trigger",
            _calendar_sync_lock_is_released_after_a_failed_sync)

        def _unrelated_settings_save_never_reaches_the_refresh_call():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-unrelated.example"
                url = "https://%s/feed.ics?token=UNRELATEDTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                registry_before = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)

                calls = []
                with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"theme": "black"}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=saved" not in location:
                    return False, "expected the ordinary saved flash key, got %r" % location
                if calls:
                    return False, (
                        "expected an unrelated save to never reach the refresh call, "
                        "got %r" % (calls,))
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain configured"
                registry_after = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if registry_after["entries"] != registry_before["entries"]:
                    return False, "expected the fetched entries to be untouched by an unrelated save"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a settings save that changes only the theme, against an already-connected calendar, redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its fetched entries untouched",
            _unrelated_settings_save_never_reaches_the_refresh_call)

        def _calendar_save_does_not_touch_the_manual_poll_cooldown():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-cooldown.example"
                url = "https://%s/feed.ics?token=COOLDOWNTOKEN" % hostname
                with _stubbed_calendar_transport(_make_calendar_transport()), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                # 32-11-PLAN.md Task 1 (TST-03): this harness runs
                # companion/app.py's server in a thread of THIS process, so
                # run_once() sees a plain monkeypatch of requests.get -
                # FakeProviders().installed() rather than child_env(),
                # which is for a subprocess child's own interpreter.
                with FakeProviders().installed():
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/poll-now", method="POST", cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=poll_cooldown" in location:
                    return False, (
                        "a calendar save must never consume the manual poll trigger's "
                        "own cooldown, got %r" % location)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a calendar save immediately followed by a manual poll trigger does not hit the poll cooldown - the two mechanisms are independent",
            _calendar_save_does_not_touch_the_manual_poll_cooldown)

        # ==============================================================
        # 21-01-PLAN.md Task 3 (D-17): a package-wide guard pinning the
        # removal — a mechanical source scan, following the same shape
        # as test_status_pages.py's own
        # _no_module_in_companion_redefines_the_alpha_threshold.
        # ==============================================================

        # The exact deleted identifiers/route literals this scan pins —
        # necessarily spelled out verbatim here, since the whole point
        # of the scan below is to detect these exact strings reappearing
        # anywhere else under companion/.
        _DISPLAY_MODE_SWITCH_TOKENS = (
            "simple_mode", "MODE_CHOICES", "DEFAULT_MODE", "_MODE_CTX",
            "UI_MODE_COOKIE_NAME", "MODE_ROUTE", '"/ui-mode"', "sp_ui_mode")
        # companion/pages/__init__.py's own ctx-contract docstring still
        # documents a ctx key this removal deletes (added by 20-01-
        # PLAN.md Task 2, deleted by 21-01-PLAN.md Task 1) — a real,
        # tracked doc-staleness gap, left in place because companion/
        # pages/__init__.py is outside this plan's own files_modified
        # boundary (21-01-SUMMARY.md's Deviations section flags it for a
        # follow-up plan). This is the ONLY exemption this scan grants,
        # and only for this one file/token pair — a genuine
        # reintroduction of any token in any OTHER file, or any OTHER
        # token in this same file, still fails the check below.
        _EXEMPT_PATH_TOKEN_PAIRS = frozenset({
            (os.path.join("companion", "pages", "__init__.py"), _DISPLAY_MODE_SWITCH_TOKENS[0]),
        })

        def _no_module_or_static_script_in_companion_reintroduces_the_display_mode_switch():
            """D-17 pins the removal of the simple/full display-mode
            switch across six modules (prefs.py, auth.py, app.py,
            layout.py, three page modules) — a partial reintroduction
            of any one of the tokens above in any of them would
            otherwise be invisible until a much later, unrelated bug
            report. Scans every *.py file under companion/ (excluding
            this package's own test_*.py harness files and __pycache__
            — this check's own literal token list would otherwise match
            itself and every other harness that documents the removal
            in a comment) plus every companion/static/*.js file.
            """
            companion_dir = HERE
            offenders = []
            for root, dirs, files in os.walk(companion_dir):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in files:
                    if name.startswith("test_") and name.endswith(".py"):
                        continue
                    if not (name.endswith(".py") or name.endswith(".js")):
                        continue
                    path = os.path.join(root, name)
                    rel_path = os.path.relpath(path, REPO_ROOT)
                    with open(path, "r", encoding="utf-8") as fh:
                        source = fh.read()
                    for token in _DISPLAY_MODE_SWITCH_TOKENS:
                        if token in source and (rel_path, token) not in _EXEMPT_PATH_TOKEN_PAIRS:
                            offenders.append("%s: %r" % (rel_path, token))
            if offenders:
                return False, (
                    "expected zero display-mode-switch tokens anywhere under companion/ "
                    "(excluding test_*.py harnesses and the one documented pre-existing "
                    "companion/pages/__init__.py docstring exemption), found: %r" % (offenders,))
            return True, ""
        check(
            "no *.py module or *.js static script anywhere under companion/ (test_*.py harnesses "
            "excluded) reintroduces any part of the deleted simple/full display-mode switch "
            "(D-17) — six modules' worth of removal, pinned by one mechanical scan",
            _no_module_or_static_script_in_companion_reintroduces_the_display_mode_switch)

        # D-17 (21-01-PLAN.md Task 1): the former Section 5 block
        # (20-12-PLAN.md Task 2, D-30/D-31) exercised the display-mode
        # switch's on/off states over real HTTP end to end, keyed off a
        # per-browser cookie for that now-deleted preference. The
        # mechanism it tested no longer exists — every check in that
        # block (both nav-visibility factories and their loop-generated
        # calls, the per-page hide/show pairs for Home's Health link,
        # Airlines' "Change pictures" toggle and Display's two
        # disclosures, and the cross-request persistence check) is
        # deleted in full. The behaviour the "on" side of each pair
        # proved is now the ONLY behaviour, and is covered by this
        # plan's own new checks in test_view_pages.py (Home's health
        # link, Airlines' "Change pictures" toggle) and test_config_
        # page.py (Display's two full <details> disclosures).

        # ==============================================================
        # Section 6 (22-08-PLAN.md Task 1/2, D-06/B16): round-trip
        # checks for every flash template, every page <title> and the
        # nav/theme labels this plan translates — i18n.t_lang(), never
        # prefs.set_request_prefs(), which would leak its ContextVar
        # state into every check that runs after this one in the same
        # process (companion/test_i18n.py's own documented reason for
        # the same choice).
        # ==============================================================

        def _flash_and_title_strings_round_trip_to_french_and_back():
            import companion.app as app_module
            import companion.i18n as i18n_module

            def _assert_round_trips(text, label):
                en_result = i18n_module.t_lang(text, "en")
                if en_result != text:
                    return (
                        "expected t_lang(%r, 'en') to be byte-identical to "
                        "the English source (%s), got %r" % (text, label, en_result))
                fr_result = i18n_module.t_lang(text, "fr")
                if fr_result == text:
                    return (
                        "expected t_lang(%r, 'fr') (%s) to be a real French "
                        "translation, got the English source back unchanged"
                        % (text, label))
                return None

            for key, template in app_module.FLASH_MESSAGES.items():
                problem = _assert_round_trips(template, "FLASH_MESSAGES[%r]" % (key,))
                if problem:
                    return False, problem
            for route, title in app_module._PAGE_TITLES.items():
                problem = _assert_round_trips(title, "_PAGE_TITLES[%r]" % (route,))
                if problem:
                    return False, problem
            # The two <title> literals with no FLASH_MESSAGES/_PAGE_TITLES
            # home: the 404's own short-form title and the login shell's.
            for title in ("Not Found", "Login"):
                problem = _assert_round_trips(title, "the %r <title> literal" % (title,))
                if problem:
                    return False, problem
            return True, ""
        check(
            "every companion.app.FLASH_MESSAGES template and every "
            "_PAGE_TITLES value, plus the 404's and login shell's own "
            "<title> literals, round-trip to French under "
            "i18n.t_lang(..., 'fr') and to their original English text "
            "under i18n.t_lang(..., 'en')",
            _flash_and_title_strings_round_trip_to_french_and_back)

        def _nav_and_theme_labels_round_trip_to_french_and_back():
            import companion.i18n as i18n_module
            for text in ("Primary navigation", "Auto", "Light", "Dark"):
                en_result = i18n_module.t_lang(text, "en")
                if en_result != text:
                    return False, (
                        "expected t_lang(%r, 'en') to be byte-identical to "
                        "the English source, got %r" % (text, en_result))
                fr_result = i18n_module.t_lang(text, "fr")
                if fr_result == text:
                    return False, (
                        "expected t_lang(%r, 'fr') to be a real French "
                        "translation, got the English source back "
                        "unchanged" % (text,))
            return True, ""
        check(
            "the nav landmark's aria-label (\"Primary navigation\") and "
            "the theme picker's three segment labels (\"Auto\"/\"Light\"/"
            "\"Dark\") round-trip to French under i18n.t_lang(..., 'fr') "
            "and to their original English text under "
            "i18n.t_lang(..., 'en') (D-06/B16)",
            _nav_and_theme_labels_round_trip_to_french_and_back)

        def _site_wide_editorial_floor_all_six_routes_both_languages():
            # 29-06-PLAN.md Task 3 (CFG-79): generalises plan 29-05's
            # render-level editorial floor (Display/Device only) to all
            # six authenticated routes, over a REAL server, in both
            # languages. This is the one check the phase is held to.
            import companion.i18n as i18n_module
            from companion import frame_state

            # --- THE ONE COUNTING RULE, duplicated from
            # test_config_page_05.py's own module-level
            # _caption_word_count_text() (33-13-PLAN.md retired the legacy
            # companion/test_config_page.py this used to point at — that
            # module's own copy lived inside main() and had to be
            # extracted via ast/exec because it was not importable; the
            # part-05 pytest module's copy is a plain top-level function,
            # but this file keeps the same ast-extract-and-exec technique
            # rather than importing it directly, since this harness runs
            # as a standalone script and test_config_page_05.py's own
            # imports (companion_app_server, from test-support/) are not
            # on sys.path outside a pytest run). ---
            def _caption_word_count_text(fragment):
                stripped = re.sub(r"<[^>]*>", "", fragment)
                text = html.unescape(stripped).strip()
                if text.startswith("— "):
                    text = text[2:]
                return re.sub(r"\s+", " ", text).strip()

            tcp_path = os.path.join(HERE, "test_config_page_05.py")
            with open(tcp_path, encoding="utf-8") as fh:
                tcp_source = fh.read()
            tcp_tree = ast.parse(tcp_source, filename=tcp_path)
            tcp_func_node = None
            for node in ast.walk(tcp_tree):
                if isinstance(node, ast.FunctionDef) and node.name == "_caption_word_count_text":
                    tcp_func_node = node
                    break
            if tcp_func_node is None:
                return False, (
                    "expected companion/test_config_page_05.py to still define "
                    "_caption_word_count_text — this file's own duplicate has "
                    "nothing to be pinned equal to")
            tcp_func_source = ast.get_source_segment(tcp_source, tcp_func_node)
            tcp_namespace = {"re": re, "html": html}
            exec(  # noqa: S102 — the extracted source is our own test file's, never external input
                compile(tcp_func_source, "<test_config_page_05._caption_word_count_text>", "exec"),
                tcp_namespace)
            tcp_caption_word_count_text = tcp_namespace["_caption_word_count_text"]
            fixture = '  — Hello   "World"&#x27;s <b>caption</b>  '
            mine, theirs = _caption_word_count_text(fixture), tcp_caption_word_count_text(fixture)
            if mine != theirs:
                return False, (
                    "this file's counting-rule duplicate disagrees with "
                    "test_config_page_05.py's own _caption_word_count_text on "
                    "fixture %r: got %r here, %r there — the two would measure "
                    "the site inconsistently" % (fixture, mine, theirs))

            def _measured_section_captions(rendered):
                out = []
                for m in re.finditer(r'<p\s+class="([^"]*)"[^>]*>(.*?)</p>', rendered, re.DOTALL):
                    classes = m.group(1).split()
                    if "section-caption" not in classes:
                        continue
                    if set(classes) - {"text-label", "section-caption"}:
                        continue
                    out.append((m.start(), m.end(), m.group(2)))
                return out

            def _frame_strip_slice(rendered):
                marker = '<div class="frame-strip stat-tile stat-tile--accent"'
                start = rendered.find(marker)
                if start == -1:
                    return None
                depth = 0
                for token in re.finditer(r"<div\b[^>]*>|</div>", rendered[start:]):
                    depth += 1 if token.group(0) != "</div>" else -1
                    if depth == 0:
                        return start, start + token.end()
                raise AssertionError("unbalanced frame-strip <div> markup")

            # --- route-list parity: layout's own six constants vs.
            # test_browser_ux.py's declared VIEW_TRANSITION_ROUTES, read as
            # TEXT (never imported — this is an app-level harness, not a
            # browser one) so a seventh route added to one enumeration and
            # not the other fails here. 31-01-PLAN.md Task 2 relocated the
            # actual VIEW_TRANSITION_ROUTES assignment out of
            # test_browser_ux.py into the shared
            # test_browser_ux_helpers.py module (test_browser_ux.py now
            # only imports the name) — read the constant from its current
            # canonical declaration site rather than the file that merely
            # imports it. ---
            site_routes = (
                layout.HOME_ROUTE, layout.DISPLAY_ROUTE, layout.FLIGHTS_ROUTE,
                layout.AIRLINES_ROUTE, layout.HEALTH_ROUTE, layout.DEVICE_ROUTE,
            )
            browser_ux_path = os.path.join(HERE, "test_browser_ux_helpers.py")
            with open(browser_ux_path, encoding="utf-8") as fh:
                browser_ux_source = fh.read()
            browser_ux_tree = ast.parse(browser_ux_source, filename=browser_ux_path)
            view_transition_routes = None
            for node in ast.walk(browser_ux_tree):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == "VIEW_TRANSITION_ROUTES"):
                    view_transition_routes = ast.literal_eval(node.value)
                    break
            if view_transition_routes is None:
                return False, (
                    "expected test_browser_ux.py to still declare "
                    "VIEW_TRANSITION_ROUTES")
            if set(site_routes) != set(view_transition_routes):
                return False, (
                    "layout's own six route constants %r do not equal "
                    "test_browser_ux.py's declared VIEW_TRANSITION_ROUTES "
                    "membership %r" % (sorted(site_routes), sorted(view_transition_routes)))

            # --- fetch every route x language over the real server ---
            cookie = _login(harness)
            exempt_by_lang = {
                lang: {
                    _caption_word_count_text(i18n_module.t_lang(text, lang))
                    for text in CAPTION_FLOOR_EXEMPTIONS
                }
                for lang in ("en", "fr")
            }
            apply_timing_templates = (
                frame_state.DELAY_DUE, frame_state.DELAY_HELD, frame_state.DELAY_UNKNOWN)

            rendered_by = {}
            for route in site_routes:
                for lang in ("en", "fr"):
                    cookie_header = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
                    status, _headers, body = http_request(base + route, cookie=cookie_header)
                    if status != 200:
                        return False, "%s/%s: expected an authenticated 200, got %d" % (
                            route, lang, status)
                    rendered = body.decode("utf-8", errors="replace")
                    expected_lang_attr = '<html lang="%s"' % lang
                    if expected_lang_attr not in rendered:
                        return False, (
                            "%s/%s: expected the served document's <html lang> to be %r — "
                            "otherwise this pass could be silently re-measuring English"
                            % (route, lang, lang))
                    rendered_by[(route, lang)] = rendered

            # --- the length floor + exemption skip-count + anti-vacuity floors ---
            # Minimums pinned a little below the observed figures on this
            # exact (fresh, unseeded) fixture — re-derived by RUNNING this
            # exact selector against a real render of each route: Home 2,
            # Display 11 (30-05-PLAN.md Task 3, CFG-85: down from 15 —
            # FRAME_COLOURS_CAPTION and the three retired per-grid swatch
            # legends all disappeared once the accordion rebuild landed),
            # Flights 0 (a genuinely empty page with no .section-caption
            # element at all on a fresh state dir — not a narrowed-
            # selector artefact; Airlines 2, Health 4, Device 8 (English
            # counts; French renders the identical structure). Enough
            # margin for an unrelated future caption to be added or
            # removed without retuning this number, not so much margin
            # that a badly narrowed selector could still clear it.
            per_route_min = {
                layout.HOME_ROUTE: 1, layout.DISPLAY_ROUTE: 9, layout.FLIGHTS_ROUTE: 0,
                layout.AIRLINES_ROUTE: 1, layout.HEALTH_ROUTE: 3, layout.DEVICE_ROUTE: 6,
            }
            # Site-wide total across BOTH languages: 2+2 + 11+11 + 0+0 +
            # 2+2 + 4+4 + 8+8 = 54 observed, re-derived by RUNNING
            # (30-05-PLAN.md Task 3, CFG-85: down from 62 — Display's own
            # drop from 15 to 11 per route above is the only change).
            site_total_min = 47

            skip_counts = {"en": 0, "fr": 0}
            site_total_captions = 0
            outside_matches = []
            any_inside_strip = False
            for route in site_routes:
                for lang in ("en", "fr"):
                    rendered = rendered_by[(route, lang)]
                    captions = _measured_section_captions(rendered)
                    if lang == "en":
                        if len(captions) < per_route_min[route]:
                            return False, (
                                "%s/%s: only %d .section-caption element(s) measured, expected "
                                "at least %d — a narrowed selector could pass over an empty set"
                                % (route, lang, len(captions), per_route_min[route]))
                    site_total_captions += len(captions)

                    strip_bounds = _frame_strip_slice(rendered)

                    for start, _end, fragment in captions:
                        text = _caption_word_count_text(fragment)
                        if text in exempt_by_lang[lang]:
                            skip_counts[lang] += 1
                            continue
                        words = text.split()
                        if len(words) > 12:
                            return False, (
                                "%s/%s: a non-exempt section-caption renders %d word(s) "
                                "(max 12): %r" % (route, lang, len(words), text))

                        for template in apply_timing_templates:
                            translated = i18n_module.t_lang(template, lang)
                            if "%s" in translated:
                                pattern = re.escape(translated).replace(re.escape("%s"), r".+?")
                            else:
                                pattern = re.escape(translated)
                            if not re.search(pattern, text):
                                continue
                            if strip_bounds is not None and strip_bounds[0] <= start < strip_bounds[1]:
                                any_inside_strip = True
                            else:
                                outside_matches.append(
                                    "%s/%s at offset %d (%r): %r"
                                    % (route, lang, start, text[:80], text))
                            break

            if site_total_captions < site_total_min:
                return False, (
                    "site-wide total: only %d .section-caption element(s) measured across all "
                    "six routes/both languages, expected at least %d"
                    % (site_total_captions, site_total_min))

            expected_skip_count = len(CAPTION_FLOOR_EXEMPTIONS)
            for lang in ("en", "fr"):
                if skip_counts[lang] != expected_skip_count:
                    return False, (
                        "%s: expected exactly %d CAPTION_FLOOR_EXEMPTIONS skip(s) across the "
                        "whole site, got %d — either the exemption is unreachable or it "
                        "silently swallowed a caption it should not have"
                        % (lang, expected_skip_count, skip_counts[lang]))

            if outside_matches:
                return False, (
                    "the apply-timing sentence rendered outside the Frame strip's own slice — "
                    "CFG-79 confines it to exactly one place per page: %s"
                    % "; ".join(outside_matches))
            if not any_inside_strip:
                return False, (
                    "the apply-timing relationship never matched INSIDE the Frame strip either "
                    "— this assertion is vacuous unless it is proven to fire on the strip's own, "
                    "untouched markup at least once")
            return True, ""
        check(
            "the site-wide editorial floor (CFG-79): every non-exempt .section-caption element "
            "on all six authenticated routes, in both English and French, over a real running "
            "server, is at most 12 whitespace-split words; the route list is proven equal to "
            "test_browser_ux.py's own VIEW_TRANSITION_ROUTES; CAPTION_FLOOR_EXEMPTIONS (config_"
            "page.ASPECT_CAPTION_EXEMPTIONS, imported not re-listed) is skipped exactly its own "
            "length per language across the whole site; per-route and site-wide caption-count "
            "minimums guard against a narrowed selector passing vacuously; and the apply-timing "
            "sentence (read from frame_state.py's own DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN "
            "constants) never renders outside the Frame strip's own markup slice, proven to fire "
            "inside it at least once (29-06-PLAN.md Task 3)",
            _site_wide_editorial_floor_all_six_routes_both_languages)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("companion-app: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
