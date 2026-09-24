#!/usr/bin/env python3
"""Contract harness for companion/pages/health_page.py (CFG-03, CFG-05's
landing context) and companion/pages/airlines_page.py (CFG-04, CFG-08).

Covers: the two independent device/pipeline freshness signals and their
threshold boundaries, the battery trend table + dependency-free sparkline
(including the anomaly-vs-gentle-decline distinction), the three
corroboration states (the unknown state never reading as a failure), the
D-14 anomaly banner's presence/absence, CFG-05's source-fault landing
block, degrade-not-raise behaviour against a locked/missing database, the
CFG-04 unresolved-prefix registry's deterministic ordering and
malformed-entry tolerance, escaping of hostile registry values (a
script-tag-shaped example callsign), CFG-08's windowed resolution-rate
breakdown including its zero-history guard, that the Airlines page emits
no form/button anywhere (D-16), two static source-content regressions
guards, and one end-to-end HTTP round trip proving companion/app.py's
router and both page modules agree.

Every fixture is seeded programmatically into a temporary state directory
via server/history_db.py's own writer functions and
server/poll_loop.py's save_poll_state() — never a committed fixture file,
so this harness cannot drift from the schema those modules define.

Stdlib-only (datetime, os, shutil, socket, sqlite3, subprocess, sys,
tempfile, time, urllib), plus Pillow (already a server dependency,
transitively imported via server.plane.render) — added by quick task
260902-req-02 for companion/illustration_normalize.py's own PNG-decoding
checks below. No pytest.

Usage:
    server/.venv/bin/python3 companion/test_status_pages.py
"""
import ast
import glob
import inspect
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion.app as app  # noqa: E402
from companion import auth, illustration_normalize, layout, prefs  # noqa: E402
import companion.i18n as i18n  # noqa: E402
import companion.i18n_fr.health as i18n_fr_health  # noqa: E402
import companion.i18n_fr.nav as i18n_fr_nav  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
import companion.wake as wake  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import illustrations  # noqa: E402
from server.plane import manual_resolutions  # noqa: E402
from server.plane import render as panel_render  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

TEST_PASSWORD = "status-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
# 19-05-PLAN.md Task 3 (D-05/A-23): the retired STALE_DEVICE_WARN_S/
# STALE_DEVICE_ERROR_S module constants are gone from health_page — every
# fixture below that seeds a device-staleness boundary now ages against
# these two, the same bare floors wake.device_staleness_thresholds(None)
# returns for a fixture that seeds no device_config.json and no
# SKYPANE_SLEEP_S (which is every fixture in this file).
_DEFAULT_DEVICE_WARN_S, _DEFAULT_DEVICE_ERROR_S = wake.device_staleness_thresholds(None)
# 33-25-PLAN.md Task 3: the historical EXPECTED_CHECK_COUNT reassignment
# trail (the count that grew from every phase since 06.6.4.1 up to 317)
# is collapsed into this one authoritative line, per 33-MIGRATION-
# RULES.md section 1. Every later plan in this chain edits only this
# line, to the pending row count its own ledger fragment records.
EXPECTED_CHECK_COUNT = 177  # 231 - 54 (33-27: part 03's 54 checks), re-derived
# by RUNNING (177/177 pass).


# --- fixture helpers ---------------------------------------------------


def _mkstate(prefix):
    return tempfile.mkdtemp(prefix="skypane-status-pages-%s-" % prefix)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _css_without_comments():
    """The shipped stylesheet with every /* */ comment blanked out.

    24-05-PLAN.md Task 1: this file already strips comments before
    grepping CSS in four places (each inlining the same `re.sub`), and
    for a good reason — style.css's comments quote the very selectors
    and declarations these checks look for, so an un-stripped grep can
    be green because a comment SAYS the rule exists. Named once here
    because this plan's checks need it three more times, not as a
    retrofit of the four existing call sites, which are left exactly as
    they are.
    """
    with open(os.path.join(HERE, "static", "style.css"), encoding="utf-8") as handle:
        return re.sub(r"/\*.*?\*/", " ", handle.read(), flags=re.DOTALL)


def _now():
    return datetime.now(timezone.utc)


def _ago(seconds):
    return _iso(_now() - timedelta(seconds=seconds))


def _seed_device_health(state_dir, readings):
    """`readings`: an iterable of (ts, battery_mv) pairs."""
    with history_db.open_db(state_dir) as conn:
        for ts, battery_mv in readings:
            history_db.record_device_health(conn, ts, battery_mv=battery_mv)


def _seed_meta(state_dir, **kv):
    with history_db.open_db(state_dir) as conn:
        for key, value in kv.items():
            history_db.set_meta(conn, key, value)


def _seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for record_runway_event()."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def _seed_unresolved_prefixes(state_dir, registry):
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def _seed_manual_resolutions(state_dir, entries):
    """Seed `state_dir`'s manual-resolutions registry through the one
    sanctioned write path, `manual_resolutions.add_entry()` — never by
    writing a JSON literal. The registry's on-disk shape and validation
    order belong to `manual_resolutions.py` (phase 14's boundary forbids
    this phase touching that file); a fixture that hand-wrote the file
    would silently drift from it and would additionally bypass the
    `load_manual_resolutions()` rebuild-from-scratch discipline
    downstream checks rely on.

    `entries` is an iterable of `(prefix, airline_name)` pairs, or
    `(prefix, airline_name, created_at)` triples when a harness needs a
    pinned timestamp — passed straight through as `add_entry()`'s
    injectable `now`.

    A superseded fixture is produced by choosing a prefix
    `enrich.static_airline_name_for_prefix()` already answers for (e.g.
    `"AFR"`) — never by mutating the registry after the fact — because
    `airlines_page._manual_resolution_rows()` derives `superseded` from
    that oracle alone (RESEARCH.md Pitfall 6) and downstream checks must
    consume that derivation rather than re-deriving it.

    Raises `AssertionError` naming the prefix and the returned code if
    `add_entry()` ever returns anything other than `ADD_OK`, so a
    fixture that would have seeded nothing fails loudly instead of
    producing a vacuously-passing check downstream.
    """
    for entry in entries:
        if len(entry) == 3:
            prefix, airline_name, created_at = entry
        else:
            prefix, airline_name = entry
            created_at = None
        code = manual_resolutions.add_entry(state_dir, prefix, airline_name, now=created_at)
        if code != manual_resolutions.ADD_OK:
            raise AssertionError(
                "_seed_manual_resolutions: add_entry(%r, %r) returned %r, expected %r"
                % (prefix, airline_name, code, manual_resolutions.ADD_OK))


def _ctx(state_dir, now=None):
    return {"state_dir": state_dir, "now": now or _iso(_now())}


# 29-06-PLAN.md Task 1 (CFG-84): the battery-trend heading's own
# rendered text, computed the SAME way _battery_trend_section_html()
# computes it — a relationship against BATTERY_SECTION_HEADING_
# TEMPLATE/BATTERY_TREND_WINDOW_DAYS, never a typed "Battery · 3
# months" literal — for the many checks below that used to anchor on
# the now-superseded BATTERY_SECTION_HEADING constant. `lang` defaults
# to "en" (this file's own default request language); pass "fr" to get
# the French form via i18n.t_lang(), never i18n.t() (which would read
# whatever the CURRENT ContextVar happens to hold at call time).
def _battery_section_heading(lang="en"):
    return i18n.t_lang(health_page.BATTERY_SECTION_HEADING_TEMPLATE, lang) % (
        health_page.BATTERY_TREND_WINDOW_DAYS // 30)


# --- 22-12-PLAN.md Task 1 (X8): one tile anatomy ------------------------
#
# `.stat-tile` bodies hold nested <div> elements now (X8's detail slot is
# one wrapper regardless of how many lines it carries), so the older
# "slice from the tile's opening tag to the next </div>" idiom silently
# stops at the FIRST nested close and reads a partial tile. This helper
# does a real balanced scan over <div ...> / </div> instead, so a check
# written against it cannot be fooled by a tile gaining or losing an
# inner wrapper.
_DIV_TOKEN_RE = re.compile(r"<div\b[^>]*>|</div>")


def _stat_tile_slices(rendered):
    """Every complete `<div class="stat-tile ...">...</div>` in
    `rendered`, in document order, each sliced on BALANCED div depth."""
    slices = []
    for match in re.finditer(r'<div class="stat-tile[ "]', rendered):
        start = match.start()
        depth = 0
        for token in _DIV_TOKEN_RE.finditer(rendered, start):
            depth += 1 if token.group(0) != "</div>" else -1
            if depth == 0:
                slices.append(rendered[start:token.end()])
                break
        else:
            raise AssertionError("unbalanced .stat-tile markup at offset %d" % (start,))
    return slices


def _tile_slice_by_caption(rendered, caption):
    """The one `.stat-tile` (see `_stat_tile_slices()`) whose markup
    carries `caption`. Kept at module scope (rather than as a `main()`
    closure) because 33-26-PLAN.md's part 02 removed the checks that used
    to define this beside their own callers, but a later section still
    calls it."""
    matching = [tile for tile in _stat_tile_slices(rendered) if caption in tile]
    if len(matching) != 1:
        raise AssertionError(
            "expected exactly one .stat-tile carrying caption %r, got %d"
            % (caption, len(matching)))
    return matching[0]


# --- HTTP harness (Section 3 only) --------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Structurally identical to companion/test_companion_app.py's own
    Harness class — owns the companion/app.py subprocess lifecycle.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-status-pages-e2e-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None

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

    def start(self):
        env = dict(os.environ)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()

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


def _login(harness, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


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

    # ======================================================================
    # Section 1: companion/pages/health_page.py
    # ======================================================================

    def _nested_card_heading_rhythm_end_to_end():
        # quick task 260902-bl2 Task 3 (Check 2): bug 2's markup half (for
        # each of the three nested cards, in both the empty and seeded
        # state, the element immediately following </h2> is either the
        # rhythm-governed p.text-body or a member of the no-top-margin
        # allowlist Task 2 verified — or the card is empty) plus the
        # stylesheet half (the demotion rule's longhand margin-bottom, the
        # prose rhythm rule's selector list/declaration, and its position
        # after the heading rule in source order).
        # quick task 260902-gjj (ISSUE 1/2): two members added in place —
        # the registry's read-only note now composes section-caption
        # onto text-body, so its own opening tag no longer matches the
        # bare '<p class="text-body">' prefix; and with the battery
        # badge retired, the battery-trend section's own next element (on
        # the seeded/chart-present branch) is the readout paragraph
        # (`<p id="battery-readout" ...>`), not a `<p class="text-body">`
        # badge any more.
        # quick task 260903-ghy: a third member added in place — the
        # Resolution-statistics card's next element, when seeded, is now
        # its own `.data-cards` mobile list (UIR-10), which style.css
        # gives its own `margin: 0` list-reset rule, so it needs no
        # separate top-margin exception of its own.
        #
        # 29-06-PLAN.md Task 1 (CFG-84): a fourth member added in place —
        # the battery-trend card's own next element is now a SIBLING
        # `<p class="text-label section-caption">` (never `.text-body`),
        # the same composition every settings-page card caption already
        # uses directly under its own `<h2>` (companion/pages/
        # config_page.py's `theme_fieldset()`/`quiet_hours_group()` etc.,
        # e.g. `<h2 class="text-heading">%s</h2><p class="text-label
        # section-caption" ...>`) — that composition relies on the same
        # UA default top margin `.section-caption`'s own comment in
        # style.css explicitly declines to override ("Settings' own
        # .section-caption role relies on the same UA default in a
        # different context. Do not 'complete' this rule by adding a
        # margin."). This is therefore consistency with an established,
        # already-accepted pattern, not a new gap — no style.css edit
        # accompanies this plan (git diff --stat companion/static/ is
        # empty).
        allowed = (
            '<p class="text-body">', '<p class="text-body section-caption">',
            '<p class="text-label section-caption">',
            '<p id="%s"' % health_page.BATTERY_READOUT_ID, "<div ", "<details", "<svg ",
            '<ul class="data-cards">')
        for seeded in (False, True):
            tmp = _mkstate("h-card-rhythm-%s" % seeded)
            try:
                now = _now()
                if seeded:
                    _seed_device_health(tmp, [
                        (_iso(now - timedelta(minutes=3)), 4200),
                        (_iso(now - timedelta(minutes=1)), 4190),
                    ])
                    _seed_runway_events(tmp, [
                        {"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
                    _seed_unresolved_prefixes(tmp, {
                        "JAF": {"count": 4, "first_seen": _iso(now), "last_seen": _iso(now),
                                "example_callsign": "JAF412"},
                    })
                rendered = health_page.render(_ctx(tmp, now=_iso(now)))
                # 22-03-PLAN.md Task 2 (B3): the Resolution-statistics
                # card is now omitted entirely (no heading at all) when
                # its window holds zero rows — this loop's own
                # unseeded pass seeds no runway_events, so
                # STATS_SECTION_HEADING only joins the rhythm check
                # when seeded (matching the fixture that actually
                # renders it).
                headings_to_check = [
                    _battery_section_heading(),  # 29-06-PLAN.md Task 1 (CFG-84)
                    health_page.UNRESOLVED_SECTION_HEADING,
                ]
                if seeded:
                    headings_to_check.append(health_page.STATS_SECTION_HEADING)
                elif health_page.STATS_SECTION_HEADING in rendered:
                    return False, (
                        "seeded=False: expected the empty Resolution-statistics "
                        "section to be entirely absent (B3, 22-03-PLAN.md Task 2)")
                for heading in headings_to_check:
                    heading_at = rendered.index(">%s" % heading)
                    after = rendered[rendered.index("</h2>", heading_at) + len("</h2>"):]
                    if after.startswith("</section>"):
                        continue
                    if not after.startswith(allowed):
                        return False, (
                            "seeded=%s: %r is followed by %r, outside the no-top-margin allowlist — "
                            "either the new element needs the .page-section--nested/.battery-trend-section "
                            "> p.text-body rhythm rule or its own zero-top-margin rule; this check is the "
                            "replacement for the catch-all rule quick task 260902-bl2 deliberately declined"
                            % (seeded, heading, after[:60]))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        heading_sel_at = css_source.index(".page-section--nested > h2,")
        heading_open = css_source.index("{", heading_sel_at)
        heading_close = css_source.index("}", heading_open)
        heading_body = css_source[heading_open:heading_close]
        if "margin-bottom: var(--space-md)" not in heading_body:
            return False, "expected the demotion rule to declare the sketch's medium bottom margin"
        prose_sel_at = css_source.index(".page-section--nested > p.text-body")
        if prose_sel_at < heading_close:
            return False, "expected the prose rhythm rule to sit after the heading rule it pairs with"
        prose_open = css_source.index("{", prose_sel_at)
        prose_close = css_source.index("}", prose_open)
        prose_selector_list = css_source[prose_sel_at:prose_open]
        prose_body = css_source[prose_open:prose_close]
        if ".battery-trend-section > p.text-body" not in prose_selector_list:
            return False, "expected the prose rhythm rule to also cover .battery-trend-section > p.text-body"
        if "margin: 0 0 var(--space-sm)" not in prose_body:
            return False, "expected the prose rhythm rule to declare zero above and the small space below"
        return True, ""
    check(
        "all three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics) show one "
        "heading-to-content rhythm in both the empty and seeded state — the element after </h2> is either "
        "rhythm-governed p.text-body or a member of the verified no-top-margin allowlist — and style.css's "
        "demotion rule/prose rhythm rule carry the sketch's two margin values in the right source order "
        "(quick task 260902-bl2 Task 3, Check 2)",
        _nested_card_heading_rhythm_end_to_end)

    def _prose_table_opts_out_alone():
        # quick task 260901-uzi Task 4 (Check 3): finding 2's markup half
        # (exactly one table — the Resolution-statistics one, located from
        # its own heading constant — carries data-table--prose; neither
        # the battery readings table nor the unresolved-prefix registry
        # table does) plus the stylesheet half (.data-table still
        # declares the max-content floor, and .data-table--prose declares
        # a zero minimum AND appears later in the file — the source-order
        # fact the fix rests on).
        tmp = _mkstate("h-prose-table-alone")
        try:
            now = _now()
            _seed_device_health(tmp, [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4190),
            ])
            _seed_runway_events(tmp, [{"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            if rendered.count("data-table--prose") != 1:
                return False, (
                    "expected exactly one table to carry data-table--prose, got %d"
                    % rendered.count("data-table--prose"))
            stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
            prose_at = rendered.index("data-table--prose")
            if prose_at < stats_at:
                return False, "expected the opted-out table to be the Resolution-statistics one"
            unresolved_at = rendered.index(health_page.UNRESOLVED_SECTION_HEADING)
            if unresolved_at < prose_at < stats_at:
                return False, "the unresolved-prefix registry table must not carry data-table--prose"
            # 29-06-PLAN.md Task 1 (CFG-84): retargeted onto the new
            # window-derived heading text.
            readings_at = rendered.index(_battery_section_heading())
            if readings_at < prose_at < unresolved_at:
                return False, "the battery readings table must not carry data-table--prose"

            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css_source = fh.read()
            base_at = css_source.index(".data-table {")
            prose_css_at = css_source.index(".data-table--prose {")
            if base_at >= prose_css_at:
                return False, (
                    "equal specificity means source order decides: .data-table--prose "
                    "must follow .data-table in style.css")
            base_body = css_source[base_at:css_source.index("}", base_at)]
            if "min-width: max-content" not in base_body:
                return False, "expected .data-table to still declare the shared no-crop floor"
            prose_body = css_source[prose_css_at:css_source.index("}", prose_css_at)]
            if "min-width: 0" not in prose_body:
                return False, "expected .data-table--prose to neutralise the floor with min-width: 0"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "exactly the Resolution-statistics table carries data-table--prose, neither the battery readings "
        "table nor the unresolved-prefix registry table does, and style.css's .data-table--prose sits after "
        ".data-table with the shared max-content floor still intact on the base rule (quick task 260901-uzi "
        "finding 2, Check 3)",
        _prose_table_opts_out_alone)

    def _desc_column_muted_end_to_end():
        # quick task 260902-bl2 Task 3 (Check 1): bug 1's markup half (the
        # Description column is the only muted column, located from
        # health_page.STATS_SECTION_HEADING rather than a first-occurrence
        # index; neither the registry table's slice nor the battery
        # readings table's slice contains one) plus the builder half
        # (layout.data_table()'s desc_columns contract, called directly)
        # plus the stylesheet half (.data-table td.desc's declaration
        # block, and the file-wide no-muted-token guard).
        tmp = _mkstate("h-desc-column-muted")
        try:
            now = _now()
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 1, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            expected = len(health_page._SOURCE_ROWS)
            desc_count = rendered.count('<td class="desc">')
            if desc_count != expected:
                return False, (
                    "expected exactly %d desc-class cells (one per _SOURCE_ROWS entry), got %d — an "
                    "unclassed Description cell is the original full-black bug returning"
                    % (expected, desc_count))

            stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
            unresolved_at = rendered.index(health_page.UNRESOLVED_SECTION_HEADING)
            # 29-06-PLAN.md Task 1 (CFG-84): retargeted onto the new
            # window-derived heading text.
            battery_at = rendered.index(_battery_section_heading())
            first_desc_at = rendered.index('<td class="desc">')
            if first_desc_at < stats_at:
                return False, "expected every desc cell to live in the Resolution-statistics table (after its own heading)"
            if unresolved_at < first_desc_at < stats_at:
                return False, "the unresolved-prefix registry table must carry no desc cell"
            if battery_at < first_desc_at < unresolved_at:
                return False, "the battery readings table must carry no desc cell"

            # Builder half — layout.data_table()'s desc_columns contract,
            # called directly.
            plain = layout.data_table(["A", "B"], [["1", "2"]])
            if 'class="desc"' in plain or 'class="mono"' in plain:
                return False, "expected the default data_table() output to carry no cell class at all"
            mono_only = layout.data_table(["A", "B"], [["1", "2"]], mono_columns=(0,))
            if '<td class="mono">1</td>' not in mono_only:
                return False, "expected the mono-only output to stay byte-identical to its pre-desc_columns form"
            desc_only = layout.data_table(["A", "B"], [["1", "2"]], desc_columns=(1,))
            if desc_only.replace(' class="desc"', "") != plain:
                return False, "expected desc_columns to change only the added class, nothing else"
            both = layout.data_table(["A", "B"], [["1", "2"]], mono_columns=(0,), desc_columns=(0,))
            if '<td class="mono desc">1</td>' not in both:
                return False, "expected a cell named by both keywords to carry both classes, mono first"

            # Stylesheet half.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css_source = fh.read()
            desc_css_at = css_source.index(".data-table td.desc {")
            desc_body = css_source[desc_css_at:css_source.index("}", desc_css_at)]
            if "color: color-mix(in srgb, var(--color-text) 70%, transparent)" not in desc_body:
                return False, "expected .data-table td.desc to reuse the file's existing 70% muted strength"
            if "min-width" in desc_body:
                return False, (
                    "a min-width in .data-table td.desc is the horizontal overflow .data-table--prose "
                    "removed returning one breakpoint down")
            if "opacity" in desc_body:
                return False, "expected colour, not opacity — opacity would fade the cell's border hairline too"
            if "var(--color-text-muted)" in css_source or "--color-text-muted:" in css_source:
                # Note: the literal substring "--color-text-muted" appears
                # elsewhere in this file as plain prose inside .cell-primary's
                # own comment ("no --color-text-muted token exists..."),
                # explaining why the token is NOT used — a bare substring
                # match would false-positive on that sentence, so this
                # checks for a real usage (var(...)) or declaration (...:)
                # only.
                return False, "a second muted value/token is the thing this stylesheet's own comments forbid"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Description column is the only muted column end to end — markup (exactly len(_SOURCE_ROWS) desc "
        "cells, all inside Resolution-statistics), builder (data_table()'s desc_columns contract: inert "
        "default, byte-identical mono-only output, additive-only desc-only output, both-roles joining mono "
        "first) and stylesheet (.data-table td.desc's 70% muted colour, no min-width, no opacity, no muted "
        "token anywhere in the file) (quick task 260902-bl2 Task 3, Check 1)",
        _desc_column_muted_end_to_end)

    def _stats_cards_list_complete_and_precedes_table():
        # quick task 260903-ghy Task 1, Check A (UIR-10): the
        # Resolution-statistics table's mobile .data-cards representation
        # is complete (one item per _SOURCE_ROWS entry, every label/full-
        # gloss/count reachable) and sits before its unchanged desktop
        # table, which is what style.css's `.data-cards ~ .data-table-wrap`
        # sibling-combinator toggle depends on.
        tmp = _mkstate("h-stats-cards-complete")
        try:
            now = _now()
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc001", "route_source": "fresh_hit"},
                {"ts": _iso(now), "hex": "abc002", "route_source": "cache_hit"},
                {"ts": _iso(now), "hex": "abc003", "route_source": "cache_hit"},
                {"ts": _iso(now), "hex": "abc004", "route_source": "airline_only"},
                {"ts": _iso(now), "hex": "abc005", "route_source": "miss"},
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            cards_list_count = rendered.count('<ul class="data-cards">')
            if cards_list_count != 1:
                return False, (
                    'expected exactly one <ul class="data-cards"> list, got %d' % cards_list_count)
            expected_items = len(health_page._SOURCE_ROWS)
            item_count = rendered.count('<li class="data-card">')
            if item_count != expected_items:
                return False, (
                    'expected exactly %d <li class="data-card"> items (one per _SOURCE_ROWS entry), '
                    'got %d' % (expected_items, item_count))

            stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
            cards_at = rendered.index('<ul class="data-cards">')
            prose_at = rendered.index("data-table--prose")
            if not (stats_at < cards_at < prose_at):
                return False, (
                    "expected the card list to sit after the Resolution-statistics heading and "
                    "before its data-table--prose table")

            card_slice = rendered[cards_at:rendered.index("</ul>", cards_at) + len("</ul>")]
            with history_db.open_db(tmp) as conn:
                stats = health_page.resolution_stats(conn, health_page.RESOLUTION_WINDOW_DAYS)
            for label, gloss, count in stats["rows"]:
                if layout.escape_html(label) not in card_slice:
                    return False, "expected label %r inside the card-list slice" % (label,)
                if layout.escape_html(gloss) not in card_slice:
                    return False, (
                        "expected the FULL gloss %r inside the card-list slice, untruncated" % (gloss,))
                if str(count) not in card_slice:
                    return False, "expected count %r inside the card-list slice" % (count,)

            if rendered.count("data-table--prose") != 1:
                return False, "expected the desktop table to still carry data-table--prose exactly once"
            desc_count = rendered.count('<td class="desc">')
            if desc_count != len(health_page._SOURCE_ROWS):
                return False, "expected the desktop table's desc cells to stay intact"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Resolution-statistics table has a complete mobile .data-cards representation — one item per "
        "_SOURCE_ROWS entry, every label/full-gloss/count present, positioned before its unchanged desktop "
        "table (quick task 260903-ghy Task 1, Check A / UIR-10)",
        _stats_cards_list_complete_and_precedes_table)

    def _data_cards_toggle_contract_and_untouched_rules():
        # quick task 260903-ghy Task 1, Check B: the mobile toggle contract
        # (base hide rule + both >=960px inverse rules), plus every rule
        # this task must NOT disturb — .data-card__label mirrors
        # .data-table th's label tier by value, .data-table-wrap's
        # scroll-edge shadow stays intact, and the three literal selectors
        # this harness itself indexes by elsewhere in this file are all
        # still present. CSS comments are stripped before any presence/
        # absence assertion so this check cannot be satisfied or defeated
        # by comment prose.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        stripped = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)

        def _rule_body(selector, source):
            at = source.index(selector)
            return source[at:source.index("}", at)]

        base_body = _rule_body(".data-cards ~ .data-table-wrap {", stripped)
        if "display: none" not in base_body:
            return False, "expected the base .data-cards ~ .data-table-wrap rule to hide the desktop table"

        media_at = stripped.index("@media (min-width: 960px)")
        media_body = stripped[media_at:]
        hide_cards_at = media_body.index(".data-cards {")
        hide_cards_body = media_body[hide_cards_at:media_body.index("}", hide_cards_at)]
        if "display: none" not in hide_cards_body:
            return False, "expected the >=960px .data-cards rule to hide the mobile card list"
        show_table_at = media_body.index(".data-cards ~ .data-table-wrap {")
        show_table_body = media_body[show_table_at:media_body.index("}", show_table_at)]
        if "display: block" not in show_table_body:
            return False, "expected the >=960px .data-cards ~ .data-table-wrap rule to reveal the desktop table"

        label_body = _rule_body(".data-card__label {", stripped)
        th_body = _rule_body(".data-table th {", stripped)
        for prop in ("font-size", "color"):
            label_decl = next(
                (line.strip() for line in label_body.splitlines()
                 if line.strip().startswith(prop + ":")), None)
            th_decl = next(
                (line.strip() for line in th_body.splitlines()
                 if line.strip().startswith(prop + ":")), None)
            if label_decl is None or th_decl is None or label_decl != th_decl:
                return False, (
                    "expected .data-card__label's %r declaration to be string-equal to .data-table "
                    "th's, got %r vs %r" % (prop, label_decl, th_decl))

        wrap_body = _rule_body(".data-table-wrap {", stripped)
        if "background-attachment" not in wrap_body:
            return False, (
                "expected .data-table-wrap's scroll-edge shadow (background-attachment layers) to "
                "remain intact")

        for literal in (".data-table {", ".data-table--prose {", ".data-table td.desc {"):
            if literal not in css_source:
                return False, "expected the harness's own pinned literal %r to still exist" % (literal,)
        return True, ""
    check(
        "the .data-cards mobile toggle contract exists at both breakpoints, .data-card__label mirrors "
        ".data-table th's label tier by value, .data-table-wrap's scroll-edge shadow is untouched, and "
        "the three literal selectors this harness indexes by elsewhere are all still present (quick task "
        "260903-ghy Task 1, Check B)",
        _data_cards_toggle_contract_and_untouched_rules)

    def _registry_mobile_cards_paired_with_table():
        # quick task 260903-ghy Task 2, Check C (UIR-11): the registry's
        # mobile .data-cards representation is exactly paired with its
        # <tr> table by (data-filter-text, data-filter-group), the
        # distinct-group count stays equal to the row count even though
        # the element count carrying data-filter-text doubles, the two
        # representations' timestamp markup is byte-identical, and every
        # column is reachable in the card slice.
        tmp = _mkstate("h-registry-cards-paired")
        try:
            now = _now()
            now_iso = _iso(now)
            prefixes = {
                "ABC": {"count": 12, "first_seen": _iso(now - timedelta(days=6)),
                        "last_seen": _iso(now - timedelta(hours=1)),
                        "example_callsign": "ABC123"},
                "XYZ": {"count": 3, "first_seen": _iso(now - timedelta(days=4)),
                        "last_seen": _iso(now - timedelta(hours=5)),
                        "example_callsign": "XYZ456"},
                "QRS": {"count": 27, "first_seen": _iso(now - timedelta(days=9)),
                        "last_seen": _iso(now - timedelta(minutes=20)),
                        "example_callsign": "QRS789"},
            }
            _seed_unresolved_prefixes(tmp, prefixes)
            rendered = health_page.render(_ctx(tmp, now=now_iso))

            rows = health_page.unresolved_rows(tmp)
            expected_count = len(rows)
            if expected_count != len(prefixes):
                return False, "expected the fixture's %d seeded prefixes to all be readable" % len(prefixes)

            tr_pattern = re.compile(
                r'<tr class="[^"]*" data-filter-text="([^"]*)" data-filter-group="(\d+)">')
            li_pattern = re.compile(
                r'<li class="data-card" data-filter-text="([^"]*)" data-filter-group="(\d+)">')
            tr_matches = tr_pattern.findall(rendered)
            li_matches = li_pattern.findall(rendered)

            if len(tr_matches) != expected_count:
                return False, "expected %d <tr> rows, got %d" % (expected_count, len(tr_matches))
            if len(li_matches) != expected_count:
                return False, (
                    'expected %d <li class="data-card"> cards, got %d' % (expected_count, len(li_matches)))

            tr_pairs = {(text, int(group)) for text, group in tr_matches}
            li_pairs = {(text, int(group)) for text, group in li_matches}
            if tr_pairs != li_pairs:
                return False, (
                    "expected the <tr> and <li> (filter-text, filter-group) pair sets to be equal, got "
                    "%r vs %r" % (tr_pairs, li_pairs))

            distinct_groups = {group for _text, group in tr_matches}
            if len(distinct_groups) != expected_count:
                return False, "expected %d distinct filter groups, got %d" % (expected_count, len(distinct_groups))
            filter_text_elements = rendered.count("data-filter-text=")
            if filter_text_elements != 2 * expected_count:
                return False, (
                    "expected exactly twice the row count's worth of data-filter-text elements (2N), got %d"
                    % filter_text_elements)

            filter_bar_at = rendered.index('<div class="filter-bar">')
            cards_at = rendered.index('<ul class="data-cards">', filter_bar_at)
            table_wrap_at = rendered.index('<div class="data-table-wrap">', cards_at)
            if not (filter_bar_at < cards_at < table_wrap_at):
                return False, "expected filter bar, then card list, then table wrap, in that document order"
            cards_end = rendered.index("</ul>", cards_at) + len("</ul>")
            card_slice = rendered[cards_at:cards_end]

            table_wrap_slice = rendered[table_wrap_at:]
            for prefix, count, first_seen, last_seen, example_callsign in rows:
                first_html = layout.concise_timestamp_html(first_seen, now_iso, fallback="")
                last_html = layout.concise_timestamp_html(last_seen, now_iso, fallback="")
                # RETARGETED IN PLACE, STRICTLY NARROWER (22-12-PLAN.md
                # Task 2, B12). This used to require each timestamp's
                # markup to appear exactly TWICE — once in the <tr>, once
                # in the paired .data-card — because both representations
                # called concise_timestamp_html(). The desktop cell is
                # two STACKED lines now (measured: the one-line form cost
                # 251px of ink each and put the French table 196px over
                # its 830px budget), so the two shapes deliberately
                # differ.
                #
                # Byte-identity was only ever a proxy for "the two
                # representations cannot disagree about what this value
                # IS". That is now asserted DIRECTLY, and on both sides:
                # the card slice carries concise_timestamp_html()'s exact
                # output exactly once, and the table slice carries the
                # exact `local_clock_text()` and `relative_age_text()`
                # outputs that that same function composes — so a drift
                # in either formatter, or a second `now`, still fails
                # here. Stronger than the old count: the old form could
                # not tell a row whose card and <tr> disagreed from one
                # where the same wrong value appeared twice.
                if rendered.count(first_html) != 1 or first_html not in card_slice:
                    return False, (
                        "expected First seen markup %r exactly once, in the card slice (found %d "
                        "occurrences)" % (first_html, rendered.count(first_html)))
                if rendered.count(last_html) != 1 or last_html not in card_slice:
                    return False, (
                        "expected Last seen markup %r exactly once, in the card slice (found %d "
                        "occurrences)" % (last_html, rendered.count(last_html)))
                for name, raw_ts in (("First seen", first_seen), ("Last seen", last_seen)):
                    clock = layout.escape_html(
                        layout.local_clock_text(layout.parse_iso(raw_ts), layout.parse_iso(now_iso)))
                    age = layout.escape_html(
                        layout.relative_age_text(layout.age_seconds(raw_ts, now_iso)))
                    expected_cell = (
                        '<span class="cell-primary" title="%s">%s</span>'
                        '<span class="cell-inline-sep">%s</span>'
                        '<span class="cell-secondary">%s</span>'
                    ) % (
                        layout.escape_html(health_page._full_local_timestamp_text(raw_ts)),
                        clock, health_page._REGISTRY_CELL_SEPARATOR_TEXT, age)
                    if expected_cell not in table_wrap_slice:
                        return False, (
                            "expected the table's %s cell to be the two stacked lines built from "
                            "the SAME formatters concise_timestamp_html() composes, got neither "
                            "%r in the table slice" % (name, expected_cell))
                    if clock not in first_html and clock not in last_html:
                        return False, (
                            "expected the stacked clock line %r to be the same text the card's own "
                            "concise_timestamp_html() output carries" % (clock,))
                if layout.escape_html(prefix) not in card_slice:
                    return False, "expected prefix %r inside the card-list slice" % (prefix,)
                if str(count) not in card_slice:
                    return False, "expected count %r inside the card-list slice" % (count,)
                if layout.escape_html(example_callsign) not in card_slice:
                    return False, "expected example callsign %r inside the card-list slice" % (example_callsign,)
                if first_html not in card_slice:
                    return False, "expected First seen markup inside the card-list slice"
                if last_html not in card_slice:
                    return False, "expected Last seen markup inside the card-list slice"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the registry's mobile .data-cards representation is exactly paired with its table by "
        "(data-filter-text, data-filter-group), carries concise_timestamp_html()'s own First/Last "
        "seen markup exactly once each while the desktop table carries the stacked cell built from "
        "the same two formatters over the same now (retargeted by 22-12-PLAN.md Task 2's B12), "
        "positioned between the filter bar and the table wrap, and every column (prefix, count, both "
        "timestamps, example callsign) is reachable in the card slice (quick task 260903-ghy Task 2, "
        "Check C / UIR-11)",
        _registry_mobile_cards_paired_with_table)

    def _registry_table_fits_by_stacked_cells_and_short_french_headers():
        # B12 (22-12-PLAN.md Task 2): pins the two levers the headless
        # measurement actually selected, so neither can be quietly undone
        # and reopen the overflow. The measurement itself lives in
        # companion/test_browser_ux.py (scrollWidth === clientWidth at
        # 1280px in both languages); this check pins the MECHANISM.
        #
        # Lever order was the plan's: shorter French headers first, then
        # the Flights stacked-cell precedent, then the card fallback
        # below 1100px. Measured at a 1280px viewport, wrap clientWidth
        # 830px: EN 886px / FR 1026px before. The two timestamp columns
        # alone wanted 251px of INK each in French, i.e. 564px of the
        # 830px budget for two of six columns, leaving 266px for four
        # columns whose own cells need 166px of ink plus 124px of
        # padding — so lever 1 alone could not fit, arithmetically, and
        # lever 2 was required. After stacking: EN 830, FR 900. After
        # also shortening the two French headers (which stacking had left
        # as the widest thing in their own columns): FR 830. The card
        # fallback (lever 3) was NOT needed and was not applied.
        tmp = _mkstate("h-registry-fits")
        try:
            now = _now()
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 12, "first_seen": _iso(now - timedelta(days=6)),
                        "last_seen": _iso(now - timedelta(hours=1)),
                        "example_callsign": "ABC123"},
            })
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            # Lever 2, the mechanism: the scoping modifier, the stacked
            # spans, and the one-line form gone from the table.
            if '<table class="data-table data-table--registry">' not in rendered:
                return False, (
                    "expected the registry table to carry the additive data-table--registry "
                    "modifier that scopes the stacked-cell rule to it")
            table_at = rendered.index('<div class="data-table-wrap">')
            table_slice = rendered[table_at:]
            if table_slice.count('<span class="cell-primary" title=') != 2:
                return False, (
                    "expected both timestamp cells to render a stacked primary line, got %d"
                    % table_slice.count('<span class="cell-primary" title='))
            if table_slice.count('<span class="cell-secondary">') != 2:
                return False, "expected both timestamp cells to render a stacked secondary line"
            if '<span class="mono" title=' in table_slice:
                return False, (
                    "expected the one-line concise_timestamp_html() cell to be gone from the "
                    "table — it is the 251px-of-ink form the overflow came from")
            with open(os.path.join(HERE, "static", "style.css"), encoding="utf-8") as fh:
                css = fh.read()
            for selector in ("table.data-table--registry .cell-primary,",
                             "table.data-table--registry .cell-secondary {",
                             "table.data-table--registry .cell-inline-sep {"):
                if selector not in css:
                    return False, "expected style.css to carry %r" % (selector,)
            # The no-crop floor is KEPT for this table — the fix is the
            # cells' own shape, never releasing min-width: max-content
            # (which .data-table--prose does, for a different table).
            if ".data-table--registry {" in css:
                return False, (
                    "expected no bare .data-table--registry rule — this table keeps the base "
                    "min-width: max-content no-crop floor, unlike .data-table--prose")
            # Lever 1: the two shortened French headers, and the retired
            # long forms gone from the catalogue entirely.
            if i18n_fr_health.CATALOG.get("First seen") != "Première fois":
                return False, (
                    "expected the shortened French 'First seen' header, got %r"
                    % (i18n_fr_health.CATALOG.get("First seen"),))
            if i18n_fr_health.CATALOG.get("Last seen") != "Dernière fois":
                return False, (
                    "expected the shortened French 'Last seen' header, got %r"
                    % (i18n_fr_health.CATALOG.get("Last seen"),))
            for retired in ("Vu pour la première fois", "Vu pour la dernière fois"):
                if retired in i18n_fr_health.CATALOG.values():
                    return False, "expected the retired long French header %r to be gone" % (retired,)
            # The English sources are untouched: English measured 830/830
            # after lever 2 alone, so there was nothing to reword.
            if health_page._REGISTRY_HEADERS[2:4] != ("First seen", "Last seen"):
                return False, (
                    "expected the English header sources to be unchanged, got %r"
                    % (health_page._REGISTRY_HEADERS,))
            # Lever 3 was not needed: the card fallback keeps its own
            # existing breakpoint and no 1100px rule was introduced.
            if "1100px" in css:
                return False, (
                    "expected no 1100px card-fallback breakpoint — measurement showed levers 1 "
                    "and 2 fit the table in both languages, so lever 3 was not applied")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the unresolved-prefix table fits by the two levers headless measurement selected — the "
        "Flights stacked-cell precedent scoped to its own data-table--registry modifier (the base "
        "no-crop floor kept), plus two shortened French headers with the retired long forms gone "
        "and the English sources untouched — and never by a 1100px card fallback (B12, "
        "22-12-PLAN.md Task 2)",
        _registry_table_fits_by_stacked_cells_and_short_french_headers)

    def _no_chrome_with_no_data_and_no_cross_page_leak():
        # quick task 260903-ghy Task 2, Check D: the standing no-chrome-
        # with-no-data rule holds for the new mechanism (an empty registry
        # renders no filter bar and no .data-cards, only empty_state()),
        # both migrated tables together render exactly two .data-cards
        # lists, and the mechanism does not leak its class names onto
        # History or Airlines, which already carry their own unrelated
        # card-list vocabularies.
        tmp_empty = _mkstate("h-registry-empty-no-cards")
        try:
            now = _now()
            rendered_empty = health_page.render(_ctx(tmp_empty, now=_iso(now)))
            unresolved_at = rendered_empty.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
            # 22-03-PLAN.md Task 2 (B3): the Resolution-statistics
            # section is now entirely absent for this genuinely-empty
            # fixture (no runway_events seeded at all), so the slice
            # boundary this check used to anchor on its heading is
            # retargeted to the end of the document — nothing renders
            # after the registry card in this fixture any more.
            if health_page.STATS_SECTION_HEADING in rendered_empty:
                return False, (
                    "expected the empty Resolution-statistics section to be entirely "
                    "absent (B3, 22-03-PLAN.md Task 2)")
            section_slice = rendered_empty[unresolved_at:]
            if "data-card" in section_slice:
                return False, "expected no .data-cards/.data-card markup in an empty registry's section"
            if "filter-bar" in section_slice:
                return False, "expected no filter bar in an empty registry's section"
            if health_page._NO_GAPS_HEADING not in section_slice:
                return False, "expected the empty_state() no-gaps heading in an empty registry's section"
        finally:
            shutil.rmtree(tmp_empty, ignore_errors=True)

        tmp_both = _mkstate("h-both-cards-lists")
        try:
            now = _now()
            _seed_runway_events(tmp_both, [
                {"ts": _iso(now), "hex": "abc111", "route_source": "fresh_hit"}])
            _seed_unresolved_prefixes(tmp_both, {
                "ABC": {"count": 1, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            rendered_both = health_page.render(_ctx(tmp_both, now=_iso(now)))
            cards_list_count = rendered_both.count('<ul class="data-cards">')
            if cards_list_count != 2:
                return False, (
                    'expected exactly two <ul class="data-cards"> lists (stats + registry) when both '
                    "have data, got %d" % cards_list_count)
        finally:
            shutil.rmtree(tmp_both, ignore_errors=True)

        tmp_leak = _mkstate("h-no-cross-page-leak")
        try:
            now = _now()
            history_rendered = history_page.render(_ctx(tmp_leak, now=_iso(now)))
            airlines_rendered = airlines_page.render(_ctx(tmp_leak, now=_iso(now)))
            for page_name, rendered_page in (
                    ("history_page", history_rendered), ("airlines_page", airlines_rendered)):
                if "data-card" in rendered_page:
                    return False, (
                        "expected zero data-card(s) occurrences in %s's rendered output" % page_name)
        finally:
            shutil.rmtree(tmp_leak, ignore_errors=True)
        return True, ""
    check(
        "no card chrome renders for an empty registry (filter bar and .data-cards both absent, "
        "empty_state() present instead); both migrated tables together render exactly two .data-cards "
        "lists; History and Airlines carry zero occurrences of the new card class names (quick task "
        "260903-ghy Task 2, Check D)",
        _no_chrome_with_no_data_and_no_cross_page_leak)

    def _humanised_readout_end_to_end():
        # quick task 260901-uzi Task 4 (Check 4): finding 3's markup half
        # (the readout's id/role/spans, the humanised visible detail) plus
        # the cross-file half (every chart hit target carries data-when,
        # and battery-trend.js's shipped source reads that attribute name,
        # both span class names, and still looks the readout up by its id
        # literal) — a server-side format change the script does not read
        # is the exact regression this check exists to catch.
        #
        # 22-06-PLAN.md Task 2 (D-05, B4): the detail span's title used to
        # carry the raw ISO — it now carries the SAME full Europe/Paris
        # local timestamp as the visible text (never a raw ISO anywhere
        # on this page), so this check's assertion inverts: zero raw ISO
        # occurrences, and a day-qualified "D Mon HH:MM" full timestamp
        # present in both the visible text and the title.
        tmp = _mkstate("h-humanised-readout-e2e")
        try:
            base = _now().replace(hour=12, minute=0, second=0, microsecond=0)  # fixed noon: readings minutes apart must never straddle a UTC day boundary
            readings = [
                (_iso(base - timedelta(minutes=6)), 4210),
                (_iso(base - timedelta(minutes=3)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))

            section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            section_end = rendered.index("</section>", section_start) + len("</section>")
            section_html = rendered[section_start:section_end]

            readout_start = section_html.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
            readout_end = section_html.index("</p>", readout_start) + len("</p>")
            readout_html = section_html[readout_start:readout_end]
            if 'role="status"' not in readout_html:
                return False, "expected role=\"status\" on the readout"
            if "battery-readout__value" not in readout_html:
                return False, "expected the readout's value span"
            if "battery-readout__detail" not in readout_html:
                return False, "expected the readout's detail span"
            if re.search(r"\d{4}-\d{2}-\d{2}T", readout_html):
                return False, "expected zero raw ISO occurrences anywhere in the readout, got %r" % readout_html
            title_match = re.search(r'title="([^"]*)"', readout_html)
            if title_match is None:
                return False, "expected the detail span to carry a title attribute"
            if not re.search(r"^\d{1,2} \w+ \d{2}:\d{2} \(", title_match.group(1)):
                return False, (
                    "expected the title to be a full 'D Mon HH:MM (Nx ago)' local timestamp, got %r"
                    % title_match.group(1))
            visible = re.sub(r"<[^>]*>", "", readout_html)
            if title_match.group(1) not in visible:
                return False, "expected the title to equal the readout's own visible text, got %r vs %r" % (
                    title_match.group(1), visible)

            if section_html.count("data-when=") != 3:
                return False, (
                    "expected one data-when attribute per chart hit target, got %d"
                    % section_html.count("data-when="))

            js_path = os.path.join(HERE, "static", "battery-trend.js")
            with open(js_path) as fh:
                js_source = fh.read()
            for token in ("data-when", "battery-readout__value", "battery-readout__detail"):
                if token not in js_source:
                    return False, "expected battery-trend.js to reference %r" % token
            if ('getElementById("%s")' % health_page.BATTERY_READOUT_ID) not in js_source:
                return False, "expected battery-trend.js to still look up the readout by its id literal"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery readout carries its id, role=\"status\", both value/detail spans and a humanised "
        "visible detail with the machine-precise ISO only in the tooltip, every chart hit target carries "
        "data-when, and battery-trend.js's shipped source still reads that attribute, both span classes, and "
        "the readout's id literal (quick task 260901-uzi finding 3, Check 4)",
        _humanised_readout_end_to_end)

    def _readout_typographic_split_stylesheet_guard():
        # quick task 260901-uzi Task 4 (Check 5): a stylesheet guard —
        # the .mono reach-through rule covers both the tile-value
        # container and the readout container in one rule (not two), and
        # the detail rule carries the Label size, the regular weight, and
        # this file's existing muted strength.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        mono_at = css_source.index(".stat-tile__value .mono,")
        mono_body_open = css_source.index("{", mono_at)
        mono_selector_list = css_source[mono_at:mono_body_open]
        if ".battery-readout .mono" not in mono_selector_list:
            return False, (
                "expected .battery-readout .mono to join .stat-tile__value .mono's "
                "own selector list, not get a second rule")

        detail_at = css_source.index(".battery-readout__detail {")
        detail_body = css_source[detail_at:css_source.index("}", detail_at)]
        if "font-size: var(--font-label-size)" not in detail_body:
            return False, "expected .battery-readout__detail to set the Label size"
        if "font-weight: var(--weight-regular)" not in detail_body:
            return False, "expected .battery-readout__detail to set the regular weight"
        if "color-mix(in srgb, var(--color-text) 70%, transparent)" not in detail_body:
            return False, (
                "expected .battery-readout__detail to reuse this file's existing 70% "
                "muted strength, not invent a fourth value")
        return True, ""
    check(
        "style.css's .mono reach-through covers both .stat-tile__value and .battery-readout in one rule, and "
        ".battery-readout__detail carries the Label size, the regular weight and the file's existing 70% "
        "muted strength (quick task 260901-uzi finding 3, Check 5)",
        _readout_typographic_split_stylesheet_guard)

    def _anomaly_active_agrees_with_banner_both_directions():
        # Compare the two booleans against each other, not against
        # hard-coded expectations, so this pins *agreement* (the
        # property that matters on screen) rather than restating the
        # anomaly rules a third time. Includes both a healthy and an
        # unhealthy fixture so the check cannot pass vacuously.
        fixtures = []

        healthy = _mkstate("h-agree-healthy")
        now = _now()
        _seed_device_health(healthy, [(_iso(now), 4200)])
        _seed_meta(healthy, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
        fixtures.append((healthy, _iso(now)))

        stale_device = _mkstate("h-agree-stale-device")
        _seed_device_health(
            stale_device, [(_ago(_DEFAULT_DEVICE_ERROR_S + 60), 4000)])
        _seed_meta(stale_device, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
        fixtures.append((stale_device, _iso(now)))

        battery_drop = _mkstate("h-agree-battery-drop")
        _seed_device_health(battery_drop, [
            (_iso(now - timedelta(minutes=1)), 4200),
            (_iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
        ])
        _seed_meta(battery_drop, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
        fixtures.append((battery_drop, _iso(now)))

        try:
            for tmp, ts in fixtures:
                verdict = health_page.anomaly_active(tmp, ts)
                rendered = health_page.render(_ctx(tmp, now=ts))
                banner_present = health_page.ANOMALY_BANNER_TEXT in rendered
                if verdict != banner_present:
                    return False, (
                        "anomaly_active()=%r disagreed with the banner's presence=%r for %r"
                        % (verdict, banner_present, tmp))
            return True, ""
        finally:
            for tmp, _ts in fixtures:
                shutil.rmtree(tmp, ignore_errors=True)
    check(
        "anomaly_active() and the anomaly banner's presence agree in both directions, across healthy and unhealthy fixtures",
        _anomaly_active_agrees_with_banner_both_directions)

    def _health_page_section_builder_markup_survives_reframe():
        tmp = _mkstate("h-reframe-survives")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            _seed_runway_events(tmp, [
                dict(
                    ts=_iso(base), hex="abc123", confirmed_state="DEPARTING",
                    corroborated="True"),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if "dot--" not in rendered:
                return False, "expected at least one dot-- status class to survive the reframe"
            # Quick task 260913-cz6 retargeted this anchor IN PLACE: the
            # battery readings table used to be the only .data-table on
            # this page carrying a BARE class attribute (the registry's
            # is data-table--registry, the stats table's is
            # data-table--prose), so the bare literal identified it
            # uniquely. It now carries its own data-table--readings
            # modifier — the hook that scopes the one stylesheet rule
            # releasing this table from the shared min-width: max-content
            # no-crop floor — so the anchor moves onto that modifier
            # rather than being loosened to a substring that would also
            # match the other two tables.
            if '<table class="data-table data-table--readings">' not in rendered:
                return False, "expected the battery table to survive the reframe"
            if "<svg" not in rendered:
                return False, "expected the battery sparkline svg to survive the reframe"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "battery and corroboration section-builder markup (dot, table, svg) survives the stat-tile reframe untouched",
        _health_page_section_builder_markup_survives_reframe)

    def _health_page_tile_icons_only_no_glyph_in_any_heading():
        # quick task 260902-j8w: retargeted IN PLACE (same slot, same
        # EXPECTED_CHECK_COUNT contribution — no check added or removed).
        # This used to pin a fourth, heading-only icon (ICON_BATTERY,
        # rendered via layout.icon_html() straight into the Battery-trend
        # <h2>) alongside the three tile icons. The developer's own
        # instruction — "supprime le logo de la batterie, car c'est
        # inconsistant avec le reste" — removed that glyph because it was
        # the only one of Health's five headings carrying an <svg>. The
        # two former battery-position assertions below are inverted into
        # the positive invariant the complaint actually names: no Health
        # heading, on any render, carries a glyph. A glyph reappearing
        # inside a heading here is exactly the inconsistency this quick
        # task removed at the developer's explicit instruction, not
        # merely a count drifting.
        #
        # 06.6.3-04 (D-12): render() also emits an unrelated icon-refresh
        # instance for the auto-refresh pill (originally the manual
        # Refresh action's icon, now (260902-chc) the pill's) — the
        # empty-render <use> count below accounts for that.
        three = (
            health_page.ICON_DEVICE, health_page.ICON_PIPELINE,
            health_page.ICON_CORROBORATION)
        if len(set(three)) != 3:
            return False, "expected the three tile-only Health icon constants to be distinct: %r" % (three,)
        for icon_id in three:
            if icon_id not in layout.ICON_IDS:
                return False, "%r is not a member of layout.ICON_IDS" % icon_id
        if hasattr(health_page, "ICON_BATTERY"):
            return False, (
                "health_page.ICON_BATTERY must be gone from the module namespace — quick task "
                "260902-j8w removed the heading glyph and its now-unused constant together")

        def _headings_carry_no_glyph(rendered, context_label, expected_heading_count):
            # 22-03-PLAN.md Task 2 (B3): the Resolution-statistics
            # heading is now omitted entirely when its window holds
            # zero rows, so the fixed "always five" expectation this
            # check used to pin is now an explicit per-fixture count —
            # neither fixture below seeds a runway_event, so both are
            # 4, not 5.
            #
            # 24-07-PLAN.md Task 2 (CFG-43): RETARGETED IN PLACE, no
            # count change of this check's own — both fixture counts go
            # 4 -> 5, because Health's Screen section now carries the
            # check-in regularity card and its own <h2>. What this check
            # is FOR is untouched and is the half that matters: that
            # heading carries no glyph either, and the assertion below
            # is what says so.
            heads = re.findall(r"<h2\b.*?</h2>", rendered, re.S)
            if len(heads) != expected_heading_count:
                return "expected Health (%s) to render %d headings, got %d" % (
                    context_label, expected_heading_count, len(heads))
            for head in heads:
                if "<svg" in head:
                    return "no Health heading may carry a glyph any more (%s), found one in: %r" % (
                        context_label, head[:140])
            if "#icon-battery" in rendered:
                return "the retired icon-battery glyph must not be referenced anywhere in the page body (%s)" % (
                    context_label)
            return None

        tmp = _mkstate("h-icons")
        try:
            empty_rendered = health_page.render(_ctx(tmp))
            if empty_rendered.count("<use") != 4:
                return False, (
                    "expected exactly four <use occurrences on the empty render (three tile icons "
                    "— device, pipeline, corroboration — plus the auto-refresh pill icon), got %d"
                    % empty_rendered.count("<use"))
            for icon_id in three:
                count = empty_rendered.count("#" + icon_id)
                if count != 1:
                    return False, "expected %r exactly once, got %d" % (icon_id, count)
            if empty_rendered.count(layout.STAT_TILE_ICON_CLASS) != 3:
                return False, (
                    "expected exactly three glyphs to carry the tile tint class — every Health-signal "
                    "glyph on this page is now a tile glyph, with none left over — got %d" % (
                        empty_rendered.count(layout.STAT_TILE_ICON_CLASS)))
            failure = _headings_carry_no_glyph(empty_rendered, "empty render", 5)
            if failure:
                return False, failure

            now = _now()
            registry = {
                "ABC": {
                    "count": 1, "first_seen": _iso(now), "last_seen": _iso(now),
                    "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            seeded_rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if seeded_rendered.count("<use") != 5:
                return False, (
                    "expected exactly five <use occurrences on a seeded render (the same four plus "
                    "icon-search in the unresolved-prefixes filter bar), got %d" % seeded_rendered.count("<use"))
            failure = _headings_carry_no_glyph(seeded_rendered, "seeded render", 5)
            if failure:
                return False, failure
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's three Health-signal icons are tile-only (device, pipeline, corroboration, all "
        "whitelisted and tile-tinted) and no Health <h2> — empty or seeded render — carries a glyph "
        "any more; health_page.ICON_BATTERY is gone from the module namespace (quick task 260902-j8w)",
        _health_page_tile_icons_only_no_glyph_in_any_heading)

    # --- 260902-chc Task 3: pin the auto-refresh contract -------------------

    def _quick_260902_chc_reversal_recorded_in_both_places():
        # Check 1: D-12's no-automatic-polling rule was enforced by prose
        # alone (no harness gate has ever pinned it), so prose is the
        # only place its reversal can be recorded. Positive assertions
        # only — a ban on the OLD wording anywhere in either file would
        # be a trap, since both files' comments legitimately discuss
        # D-12's old rule in the course of explaining why it changed.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js_source = fh.read()
        if "260902-chc" not in js_source:
            return False, "expected freshness.js to name this quick task"
        if "SUPERSEDED" not in js_source:
            return False, "expected freshness.js to carry the house superseded token"
        if "D-12" not in js_source:
            return False, "expected freshness.js to name the decision it reverses"

        context_path = os.path.join(
            REPO_ROOT, ".planning", "phases",
            "06.6.3-companion-per-page-redesign-config-health-history-airlines-p",
            "06.6.3-CONTEXT.md")
        with open(context_path) as fh:
            context_source = fh.read()
        d12_start = context_source.index("- **D-12:**")
        d12_entry = context_source[d12_start:context_source.index("\n\n", d12_start)]
        if "SUPERSEDED" not in d12_entry:
            return False, "expected D-12's own CONTEXT.md entry to carry the house superseded token"
        if "260902-chc" not in d12_entry:
            return False, "expected D-12's own CONTEXT.md entry to name this quick task"
        if "no automatic background polling" not in d12_entry:
            return False, (
                "expected D-12's original decision wording to survive byte-identical — an "
                "unrecorded reversal reads to the next reader as a violation of a rule still "
                "presented as current")
        return True, ""
    check(
        "the D-12 reversal (260902-chc) is written down at both prose sites it touches — "
        "freshness.js's own header and D-12's own CONTEXT.md entry — each carrying the house "
        "SUPERSEDED token and naming this quick task, with D-12's original wording intact",
        _quick_260902_chc_reversal_recorded_in_both_places)

    def _quick_260902_chc_loop_contract_guard():
        # Check 2: the loop's own contract, pinned against freshness.js's
        # shipped source rather than this plan's own prose.
        #
        # 19-09-PLAN.md (D-02): retargeted in place (same check name/
        # function) for the fetch-and-swap rewrite. The tab-visibility
        # loop machinery below is UNCHANGED from the reload-based version
        # this superseded — same interval constant, same pause/visibility
        # halves, same double-start guard. What changed is the ONE thing
        # this task's own name is about: the no-argument reload form is
        # now REQUIRED ABSENT (D-02 deletes it outright), fetch( moves
        # from the forbidden list to the required list (companion/
        # test_companion_app.py's own new named guard for this file
        # states, in its body, that this is a single, deliberate,
        # reviewed exception — not re-asserted here to avoid duplicating
        # that guard's own reasoning), and the required-safe-primitives
        # list grows by the swap mechanism's own three load-bearing calls.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()

        m = re.search(r"AUTO_REFRESH_INTERVAL_MS\s*=\s*(\d+)", js)
        if not m:
            return False, "expected AUTO_REFRESH_INTERVAL_MS to be a named constant"
        interval_ms = int(m.group(1))
        if not (30000 <= interval_ms <= 60000):
            return False, "interval %d ms falls outside the developer's chosen 30-60s band" % interval_ms

        if "setInterval" not in js or "clearInterval" not in js:
            return False, "expected both setInterval and clearInterval — the pause half of the loop"
        if "visibilitychange" not in js or "document.hidden" not in js:
            return False, "expected both a visibilitychange listener and a document.hidden read"
        if "intervalHandle !== null" not in js:
            return False, "expected the double-start guard (a no-op start when a handle already exists)"
        if "location.reload" in js:
            return False, "expected the retired reload form to be gone entirely (D-02)"

        # test_config_page.py's own _FORBIDDEN_SCRIPT_SINKS tuple, minus
        # fetch( (this file's own single, reviewed exception — see the
        # comment above), copied here (not imported — it is a
        # function-local inside that harness's main()) from the real
        # source read at plan time. If that tuple's membership ever
        # changes, this copy needs updating too.
        forbidden_sinks = (
            "innerHTML", "outerHTML", "insertAdjacentHTML",
            "document.write", "eval(", "XMLHttpRequest",
        )
        for sink in forbidden_sinks:
            if sink in js:
                return False, "forbidden sink discipline broken: %r found in freshness.js" % sink
        for nav in ("location.href =", "location.assign", "location.replace", "window.open"):
            if nav in js:
                return False, "URL-taking navigation form found in freshness.js: %r" % nav

        # The ES5-safe-subset portion of test_companion_app.py's own
        # nav-dropdown.js/panel-lookup.js `banned` tuples, copied here
        # (not imported, same reason as forbidden_sinks above) from the
        # real source read at plan time.
        for token in ("let ", "const ", "=>", "`"):
            if token in js:
                return False, "ES5-safe subset broken: %r found in freshness.js" % token

        # setTimeout/setInterval must be present (the loop needs
        # setInterval to exist at all); fetch(/DOMParser/replaceChild/
        # importNode are the swap mechanism's own required-present
        # primitives (19-09-PLAN.md Task 2).
        for required in (
                "setInterval", "fetch(", "DOMParser", "replaceChild", "importNode"):
            if required not in js:
                return False, "expected %r to be present in freshness.js" % required
        return True, ""
    check(
        "freshness.js's shipped source carries the loop's own contract — a named interval constant "
        "inside the 30-60s band, both halves of pause (setInterval+clearInterval) and visibility "
        "(visibilitychange+document.hidden), the double-start guard, and (19-09-PLAN.md, D-02) the "
        "retired reload form gone entirely while fetch(/DOMParser/replaceChild/importNode are now "
        "required present as this file's own reviewed exception to the forbidden-sink/no-URL-taking-"
        "navigation-form/ES5-safe-subset disciplines, which otherwise still hold unchanged",
        _quick_260902_chc_loop_contract_guard)

    def _quick_260902_chc_pill_markup_contract():
        # Check 3: the pill's own markup contract on a real render,
        # including the state where it matters most that the pill is
        # unconditional — a fresh state directory with no readings at
        # all — so the pill is proven independent of the battery chart's
        # own render branch, not accidentally coupled to it.
        for label, seed_readings in (("seeded", True), ("fresh/no-readings", False)):
            tmp = _mkstate("h-pill-contract-%s" % ("seeded" if seed_readings else "fresh"))
            try:
                now = _now()
                if seed_readings:
                    _seed_device_health(tmp, [
                        (_iso(now - timedelta(minutes=1)), 4200),
                        (_iso(now), 4190),
                    ])
                now_iso = _iso(now)
                rendered = health_page.render(_ctx(tmp, now=now_iso))
                if rendered.count("data-refresh-pill") != 1:
                    return False, (
                        "%s state: expected exactly one pill marker attribute, got %d"
                        % (label, rendered.count("data-refresh-pill")))
                start = rendered.index("data-refresh-pill")
                tag = rendered[rendered.rindex("<", 0, start):rendered.index(">", start) + 1]
                if not tag.startswith("<span"):
                    return False, "%s state: expected the pill to be an inline <span>, got %r" % (label, tag[:40])
                if " hidden" not in tag:
                    return False, "%s state: expected the pill to carry the bare hidden attribute" % label
                if ('data-loaded-at="%s"' % now_iso) not in rendered:
                    return False, "%s state: expected data-loaded-at to carry the real now value" % label
                if rendered.count("data-loaded-at") != 1:
                    return False, "%s state: expected exactly one data-loaded-at, page-wide" % label
                if health_page.REFRESH_PILL_TEXT not in rendered:
                    return False, "%s state: expected the pill copy constant's own value in the rendered page" % label
                header_start = rendered.index('<div class="page-header">')
                header_end = rendered.index("</div>", header_start) + len("</div>")
                if "data-refresh-pill" not in rendered[header_start:header_end]:
                    return False, "%s state: expected the pill inside the .page-header div" % label
                purpose_at = rendered.index(layout.escape_html(health_page.PAGE_PURPOSE_TEXT))
                if start >= purpose_at:
                    return False, "%s state: expected the pill to precede the purpose sentence" % label
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "the auto-refresh pill's markup contract (marker attribute, inline element, hidden-by-default, "
        "live data-loaded-at exactly once page-wide, the pill-copy constant's own value, inside "
        ".page-header, preceding the purpose sentence) holds on a real render both seeded and on a "
        "fresh state directory with no readings at all — proven unconditional, not coupled to the "
        "battery chart's own render branch",
        _quick_260902_chc_pill_markup_contract)

    def _quick_260902_chc_pill_stylesheet_contract():
        # Check 4: the pill's stylesheet contract, matching the existing
        # CSS DOM-contract guard idiom (index()-plus-window-slicing,
        # never a regex CSS parser — see
        # _quick_260901_tsa_css_dom_contract_guard() above).
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        if ".refresh-pill {" not in css_source:
            return False, "expected style.css to declare .refresh-pill"
        pill_start = css_source.index(".refresh-pill {")
        pill_body = css_source[pill_start:css_source.index("}", pill_start)]
        if "display: inline-flex" not in pill_body:
            return False, "expected .refresh-pill to declare an inline-level flex display"

        if ".refresh-pill[hidden] {" not in css_source:
            return False, "expected style.css to declare .refresh-pill[hidden]"
        hidden_start = css_source.index(".refresh-pill[hidden] {")
        hidden_body = css_source[hidden_start:css_source.index("}", hidden_start)]
        if "visibility: hidden" not in hidden_body:
            return False, (
                "expected .refresh-pill[hidden] to hide by visibility — without this override the "
                "pill's own display declaration beats the user-agent [hidden] rule and the pill "
                "renders permanently visible on every page load, the exact collision "
                ".dirty-bar[hidden]'s own comment documents")
        if "display" in hidden_body:
            return False, (
                "expected .refresh-pill[hidden] to declare no display value at all — a display "
                "declaration inside this rule would collapse the reserved line box and reintroduce "
                "the layout shift it exists to prevent")

        if ".refresh-pill .icon" not in css_source:
            return False, "expected a pill-scoped icon-size override — .icon is 20px, the pill is 20px tall"

        if css_source.index(".banner__pill {") >= pill_start:
            return False, "expected .banner__pill to still precede .refresh-pill in source order"

        # 260902-ep7 (BUG 1): the pill is taken out of .page-header's
        # block flow entirely rather than kept in flow with a reserved
        # line box, so this contract must also pin the out-of-flow
        # mechanism itself — a .page-header rule establishing a
        # containing block, and a .page-header-scoped .refresh-pill rule
        # positioned absolutely within it. Strengthened in place, no
        # count change.
        if ".page-header {" not in css_source:
            return False, "expected style.css to declare .page-header"
        header_start = css_source.index(".page-header {")
        header_body = css_source[header_start:css_source.index("}", header_start)]
        if "position: relative" not in header_body:
            return False, "expected .page-header to establish a containing block for the out-of-flow pill"

        if ".page-header .refresh-pill {" not in css_source:
            return False, "expected a .page-header-scoped .refresh-pill rule taking it out of block flow"
        scoped_start = css_source.index(".page-header .refresh-pill {")
        scoped_body = css_source[scoped_start:css_source.index("}", scoped_start)]
        if "position: absolute" not in scoped_body:
            return False, "expected .page-header .refresh-pill to be positioned absolutely"
        if "top:" not in scoped_body or "right:" not in scoped_body:
            return False, "expected .page-header .refresh-pill to declare explicit top/right offsets"
        return True, ""
    check(
        "style.css's .refresh-pill / .refresh-pill[hidden] / pill-scoped icon rules each carry their "
        "load-bearing declaration — the [hidden] override hides by visibility with no display value at "
        "all — .banner__pill still precedes .refresh-pill in source order, and the pill is taken out of "
        ".page-header's block flow entirely via a .page-header-scoped absolute-position rule rather than "
        "kept in flow with a reserved line box (260902-ep7)",
        _quick_260902_chc_pill_stylesheet_contract)

    def _quick_260903_peo_pipeline_second_line():
        # UIR-14: the pipeline tile gains a real second content line
        # sourced from history_db.META_LAST_DETECTION, read inside the
        # same atomic _read_health_inputs() snapshot pipeline_ts already
        # comes from. The rendered timestamp markup must be byte-
        # identical to what concise_timestamp_html() itself returns for
        # the same (ts, now) pair, so the two can never drift into two
        # formats.
        tmp = _mkstate("h-pipeline-detection")
        try:
            now = _now()
            now_iso = _iso(now)
            detection_iso = _iso(now - timedelta(minutes=5))
            _seed_meta(
                tmp,
                **{
                    history_db.META_LAST_PIPELINE_RUN: now_iso,
                    history_db.META_LAST_DETECTION: detection_iso,
                })
            rendered = health_page.render(_ctx(tmp, now=now_iso))
            expected_detail = layout.concise_timestamp_html(detection_iso, now_iso)
            if rendered.count(expected_detail) != 1:
                return False, (
                    "expected the pipeline tile's second line to render "
                    "concise_timestamp_html() byte-identically for the seeded "
                    "META_LAST_DETECTION value exactly once, got %d"
                    % rendered.count(expected_detail))
            if health_page.LAST_DETECTION_LABEL not in rendered:
                return False, "expected the second line's label text in the rendered page"
            if 'class="stat-tile__meta text-label section-caption"' not in rendered:
                return False, (
                    "expected the second line to reuse the existing muted "
                    "text-label/section-caption tier via a layout-only "
                    "stat-tile__meta class, not a new type tier — never "
                    "battery-readout__detail, whose class name would collide "
                    "with the BATTERY_READOUT_ID absence guards below")
            if "battery-readout" in rendered.split(
                    '<p class="stat-tile__meta')[1].split("</p>")[0]:
                return False, (
                    "expected the second line's own markup to carry no "
                    "'battery-readout' substring — that would false-positive "
                    "the BATTERY_READOUT_ID absence guards on a fresh install")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the pipeline tile's new second line renders META_LAST_DETECTION's timestamp "
        "byte-identically to concise_timestamp_html(), reusing the existing muted "
        "text-label/section-caption tier — never battery-readout__detail, whose class "
        "name would collide with the BATTERY_READOUT_ID absence guards (quick task "
        "260903-peo, UIR-14)",
        _quick_260903_peo_pipeline_second_line)

    def _quick_260903_peo_pipeline_second_line_absent_detection_fallback():
        # The absent case: never an empty element or a dangling label —
        # concise_timestamp_html()'s own escaped bare-string fallback
        # renders honestly, matching _device_section()'s own
        # unconditional-render precedent. Scoped to the pipeline tile's
        # own second-line <p> (never a page-wide count): this fixture
        # also leaves device_health unseeded, so the Device tile's own
        # concise_timestamp_html() call renders the identical fallback
        # text independently — a page-wide count would conflate the two.
        tmp = _mkstate("h-pipeline-no-detection")
        try:
            now_iso = _iso(_now())
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: now_iso})
            rendered = health_page.render(_ctx(tmp, now=now_iso))
            fallback_html = layout.escape_html("no reading yet")
            second_line_start = rendered.index('<p class="stat-tile__meta text-label section-caption">')
            second_line_end = rendered.index("</p>", second_line_start) + len("</p>")
            second_line = rendered[second_line_start:second_line_end]
            if fallback_html not in second_line:
                return False, (
                    "expected the pipeline tile's second line to render the honest "
                    "fallback when META_LAST_DETECTION is absent, got %r" % second_line)
            if health_page.LAST_DETECTION_LABEL not in second_line:
                return False, "expected the second line's label to still render alongside the fallback"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the pipeline tile's second line renders its honest no-reading-yet fallback when "
        "META_LAST_DETECTION is absent, never an empty element or a dangling label "
        "(quick task 260903-peo, UIR-14)",
        _quick_260903_peo_pipeline_second_line_absent_detection_fallback)

    def _quick_260903_peo_persistent_freshness_note():
        # 19-09-PLAN.md (D-02, A-20): retargeted in place (same check
        # name/function, same structural-contract shape) for the honest
        # "Updated HH:MM" rewrite. UIR-18's original structural contract
        # survives — a persistent, server-rendered note joins the hidden
        # refresh pill inside ONE block-level wrapper (260902-ep7's
        # anonymous-block-box guard) that is .page-header's next child
        # right after the <h1> — and gains two more assertions that task
        # added: the note carries no relative-age suffix at all, and a
        # single data-refresh-clock span holds the full ISO in its title.
        #
        # 21-02-PLAN.md (D-18): retargeted again — the Pause/Resume
        # button 19-09-PLAN.md's version of this check asserted is
        # deleted outright, with no replacement control. The wrapper now
        # holds only the readout span and the pill, and this check
        # additionally pins that zero occurrences of data-refresh-toggle,
        # data-pause-text or data-resume-text survive anywhere in it.
        tmp = _mkstate("h-persistent-freshness")
        try:
            now_iso = _iso(_now())
            rendered = health_page.render(_ctx(tmp, now=now_iso))

            prefix = layout.escape_html(health_page.FRESHNESS_PREFIX_TEXT)
            if prefix not in rendered:
                return False, "expected the honest 'Updated ' prefix text in the rendered page"
            if health_page.FRESHNESS_PREFIX_TEXT != "Updated ":
                return False, "expected FRESHNESS_PREFIX_TEXT to read 'Updated '"

            if '<p class="page-header__freshness' not in rendered:
                return False, "expected a block-level .page-header__freshness wrapper"
            wrapper_start = rendered.index('<p class="page-header__freshness')
            wrapper_end = rendered.index("</p>", wrapper_start) + len("</p>")
            wrapper_slice = rendered[wrapper_start:wrapper_end]
            if "data-refresh-pill" not in wrapper_slice:
                return False, "expected the hidden refresh pill inside the freshness wrapper"
            # 23-05-PLAN.md Task 2 (D14/D22/CFG-34): RETARGETED IN
            # PLACE, and strictly strengthened. 19-09-PLAN.md (A-20)
            # banned any relative age here because the one that stood
            # was STRUCTURALLY ALWAYS ZERO: `now` was computed once per
            # request and fed straight back into a timestamp claiming to
            # be "(Ns ago)" of itself. The defect was the FREEZE, not
            # the age. The line now carries a LIVE age —
            # layout.relative_time_html() over the same instant
            # data-loaded-at holds, advanced once a second by
            # companion/static/relative-time.js — so the ban becomes:
            # every age in this wrapper must be inside a <time
            # data-relative> element, and a frozen one is still
            # forbidden. Re-rendering A-20's own defect (a bare "(0s
            # ago)" outside an element) fails here exactly as it did
            # before.
            outside = re.sub(r"<time [^>]*data-relative[^>]*>.*?</time>", "",
                             wrapper_slice, flags=re.S)
            if " ago" in outside or "il y a" in outside:
                return False, (
                    "expected every relative age inside .page-header__freshness to be a live "
                    "<time data-relative> element — a frozen age here is A-20's own defect "
                    "('(0s ago)' was structurally always zero), got %r" % (outside,))
            if wrapper_slice.count("data-relative") != 1:
                return False, (
                    "expected exactly one <time data-relative> element inside "
                    ".page-header__freshness, got %d" % wrapper_slice.count("data-relative"))
            # 23-06-PLAN.md (23-05's finding 2, fixed rather than
            # deferred): the ban above says where an age may live; this
            # says what the SERVER may write there. Stripping the element
            # out and finding no age left is a clause a page rendering no
            # age at all satisfies for free — so the element's own text
            # is asserted too. It must be the clock, and it must not be
            # the ladder's zero bucket in either language: with scripts
            # blocked nothing advances this element, and "Updated 0s ago"
            # frozen at load is A-20's own defect read back to the one
            # reader who cannot see the ticker.
            inside = re.search(r"<time [^>]*data-relative[^>]*>(.*?)</time>",
                               wrapper_slice, flags=re.S)
            if inside is None:
                return False, (
                    "expected the freshness value to BE a <time data-relative> element, got %r"
                    % (wrapper_slice,))
            for lang in ("en", "fr"):
                if inside.group(1) == layout.escape_html(layout.relative_age_text(0, lang=lang)):
                    return False, (
                        "the server renders the ladder's zero bucket %r as this element's own "
                        "text — frozen for a scripts-blocked reader, which is exactly the defect "
                        "A-20 removed" % (inside.group(1),))
            if " ago" in inside.group(1) or "il y a" in inside.group(1):
                return False, (
                    "the server renders a relative age (%r) where the no-JS floor needs a value "
                    "that stays true — the age is the ticker's to write, the clock is the "
                    "server's" % (inside.group(1),))

            if wrapper_slice.count("data-refresh-clock") != 1:
                return False, (
                    "expected exactly one data-refresh-clock span, got %d"
                    % wrapper_slice.count("data-refresh-clock"))
            clock_at = wrapper_slice.index("data-refresh-clock")
            clock_tag = wrapper_slice[
                wrapper_slice.rindex("<", 0, clock_at):wrapper_slice.index(">", clock_at) + 1]
            # 22-16-PLAN.md's closing sweep (D-05/CFG-28): RETARGETED in
            # place, deliberately, from 19-09-PLAN.md's own "the title
            # carries the full ISO instant" assertion. A `title` is a
            # tooltip and this one sits behind no copy control, so the
            # raw ISO failed two of CFG-28's clauses. It is now the full
            # Europe/Paris local timestamp, the same conversion
            # 22-06-PLAN.md Task 3 applied to concise_timestamp_html(),
            # and asserted the same way: the raw ISO must not survive
            # verbatim, and the title must match this module's own
            # _full_local_timestamp_text() output exactly.
            expected_title = layout.escape_html(
                health_page._full_local_timestamp_text(now_iso))
            if ('title="%s"' % expected_title) not in clock_tag:
                return False, (
                    "expected the clock span's title to carry the full Europe/Paris local "
                    "timestamp %r, got %r" % (expected_title, clock_tag))
            if now_iso in clock_tag:
                return False, (
                    "expected the raw ISO instant NOT to survive verbatim in the clock "
                    "span's title — a title is a tooltip, and raw ISO belongs only behind "
                    "a copy control (D-05/CFG-28)")

            for needle in ("data-refresh-toggle", "data-pause-text", "data-resume-text"):
                if needle in wrapper_slice:
                    return False, (
                        "expected zero occurrences of %r inside .page-header__freshness — "
                        "the Pause/Resume control is deleted, not replaced (D-18)" % needle)
            if "<button" in wrapper_slice:
                return False, "expected no <button> inside .page-header__freshness (D-18)"

            # Substring ordering, the same way this guard has always
            # pinned the anonymous-block-box fix: prefix, then clock,
            # then pill, both inside the one wrapper.
            prefix_at = wrapper_slice.index(prefix)
            if not (prefix_at < clock_at < wrapper_slice.index("data-refresh-pill")):
                return False, "expected prefix, then clock, then pill in that source order"

            header_start = rendered.index('<div class="page-header">')
            header_end = rendered.index("</div>", header_start) + len("</div>")
            if wrapper_start < header_start or wrapper_end > header_end:
                return False, "expected the freshness wrapper inside the .page-header div"
            header_slice = rendered[header_start:header_end]
            title_end = header_slice.index("</h1>") + len("</h1>")
            between = header_slice[title_end:]
            if not between.startswith('<p class="page-header__freshness'):
                return False, (
                    "expected the freshness wrapper to be .page-header's next "
                    "block-level child right after the <h1> — a stranded bare "
                    "inline node here would reopen 260902-ep7's anonymous-"
                    "block-box gap")

            # The pill's own markup is byte-for-byte unchanged: still an
            # inline <span>, still carrying the bare hidden attribute and a
            # live data-loaded-at — freshness.js itself carries zero diff
            # and needs none of this to change.
            pill_at = rendered.index("data-refresh-pill")
            pill_tag = rendered[rendered.rindex("<", 0, pill_at):rendered.index(">", pill_at) + 1]
            if not pill_tag.startswith("<span"):
                return False, "expected the pill to still be an inline <span>"
            if " hidden" not in pill_tag:
                return False, "expected the pill to still carry the bare hidden attribute"
            if ('data-loaded-at="%s"' % now_iso) not in rendered:
                return False, "expected data-loaded-at to still carry the real now value"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's header renders an honest 'Updated HH:MM' clock — server-rendered as the text of "
        "a <time data-relative> element, never the ladder's zero bucket, so the value is true "
        "with scripts blocked and live with them (23-06-PLAN.md) — (no relative-age suffix, the full "
        "Europe/Paris local timestamp — never the raw ISO — in the clock span's title, retargeted "
        "by 22-16 for D-05/CFG-28) beside the unchanged hidden refresh pill and NO Pause/Resume "
        "toggle (zero data-refresh-toggle/data-pause-text/data-resume-text, zero <button>), all "
        "inside one block-level .page-header__freshness wrapper that is the .page-header's next "
        "child right after the <h1>, in prefix/clock/pill source order (21-02-PLAN.md Task 1, D-18; "
        "supersedes 19-09-PLAN.md Task 1's Pause/Resume-toggle contract, itself superseding quick "
        "task 260903-peo/UIR-18's 'Live — refreshed (Ns ago)' contract)",
        _quick_260903_peo_persistent_freshness_note)

    def _quick_260902_v2v_uir_03_07_12_13_fixes():
        # quick task 260902-v2v: pins all four one-line fixes together in
        # one check so a partial fix (e.g. the CSS half without the
        # markup half, or vice versa) cannot satisfy it.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        # UIR-03a: .banner wraps.
        if ".banner {" not in css_source:
            return False, "expected style.css to declare .banner"
        banner_start = css_source.index(".banner {")
        banner_body = css_source[banner_start:css_source.index("}", banner_start)]
        if "flex-wrap: wrap" not in banner_body:
            return False, "expected .banner to declare flex-wrap: wrap (UIR-03)"

        # UIR-03b: .banner__label exists and is nowrap.
        if ".banner__label {" not in css_source:
            return False, "expected style.css to declare .banner__label (UIR-03)"
        label_start = css_source.index(".banner__label {")
        label_body = css_source[label_start:css_source.index("}", label_start)]
        if "white-space: nowrap" not in label_body:
            return False, "expected .banner__label to declare white-space: nowrap (UIR-03)"

        # UIR-03c: .banner__pill keeps flex: none and gains min-width: 0,
        # and still precedes .refresh-pill in source order (re-asserting
        # the neighbouring source-order contract the check above already
        # owns, so an edit near this rule cannot silently reorder it).
        pill_start = css_source.index(".banner__pill {")
        pill_body = css_source[pill_start:css_source.index("}", pill_start)]
        if "min-width: 0" not in pill_body:
            return False, "expected .banner__pill to declare min-width: 0 (UIR-03)"
        if "flex: none" not in pill_body:
            return False, "expected .banner__pill to still declare flex: none (UIR-03)"
        if pill_start >= css_source.index(".refresh-pill {"):
            return False, "expected .banner__pill to still precede .refresh-pill in source order"

        # UIR-07: .airline-card__image gains height: auto and keeps its
        # aspect-ratio. quick task 260904-e92 (DP-5): the expected
        # declaration is derived from illustration_normalize's own
        # constants instead of a hardcoded literal pair, so the CSS and
        # the Python constants cannot silently drift apart again.
        image_start = css_source.index(".airline-card__image {")
        image_body = css_source[image_start:css_source.index("}", image_start)]
        if "height: auto" not in image_body:
            return False, "expected .airline-card__image to declare height: auto (UIR-07)"
        expected_aspect_ratio = "aspect-ratio: %d / %d" % illustration_normalize.ILLUSTRATION_TARGET_SIZE
        if expected_aspect_ratio not in image_body:
            return False, "expected .airline-card__image to declare %r (UIR-07)" % expected_aspect_ratio

        # UIR-13: a .data-table--prose-scoped :first-child nowrap rule
        # exists and sits after the base .data-table--prose rule.
        prose_at = css_source.index(".data-table--prose {")
        if ".data-table--prose th:first-child" not in css_source:
            return False, "expected a .data-table--prose th:first-child rule (UIR-13)"
        prose_nowrap_start = css_source.index(".data-table--prose th:first-child")
        if prose_nowrap_start <= prose_at:
            return False, (
                "expected the .data-table--prose :first-child nowrap rule to follow the base "
                ".data-table--prose rule in source order (UIR-13)")
        prose_nowrap_body = css_source[
            prose_nowrap_start:css_source.index("}", prose_nowrap_start)]
        if "white-space: nowrap" not in prose_nowrap_body:
            return False, (
                "expected the .data-table--prose :first-child rule to declare white-space: nowrap "
                "(UIR-13)")

        # UIR-03 markup half: a real anomaly-banner render carries the
        # class on the lead span, not a bare <span>.
        tmp = _mkstate("h-v2v-banner-label")
        try:
            rendered = health_page.render(_ctx(tmp))
            if 'class="banner banner--warn"' not in rendered and 'class="banner banner--anomaly"' not in rendered:
                return False, "expected a fresh empty state dir to render an anomaly banner"
            banner_at = rendered.index('<div class="banner ')
            if 'class="banner__label"' not in rendered[banner_at:]:
                return False, "expected the banner's lead span to carry class=\"banner__label\""
            label_open = rendered.index('<span class="banner__label">', banner_at)
            label_close = rendered.index("</span>", label_open)
            label_text = rendered[label_open:label_close]
            if not re.search(r">\d+ (warning|error)s?:\Z", label_text):
                return False, (
                    "expected the count-and-noun lead text inside the banner__label span, got %r"
                    % label_text)
            bare_lead_at = rendered.find("<span>", banner_at, label_open)
            if bare_lead_at != -1:
                return False, "expected no bare <span> lead ahead of the banner__label span"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        # UIR-12 markup half: SUPERSEDED in place by 29-06-PLAN.md Task 1
        # (CFG-84) — the space-before-em-dash fix this used to pin
        # applied to the OLD inline `<span class="text-label
        # section-caption"> — %s</span>` this heading carried; that span
        # (and the em dash it opened with) no longer exists, superseded
        # by a SIBLING `<p class="text-label section-caption">` that
        # carries only `_battery_trend_caption()`'s own text — no
        # leading em dash at all, because the dash was markup this
        # function used to add between heading and caption, never part
        # of the caption's own text. The equivalent property now: the
        # sibling caption follows the heading immediately, and its text
        # opens with no dash of its own.
        tmp2 = _mkstate("h-v2v-em-dash")
        try:
            rendered2 = health_page.render(_ctx(tmp2))
            heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(
                _battery_section_heading())
            after_heading = rendered2[rendered2.index(heading_marker) + len(heading_marker):]
            caption_open = '<p class="text-label section-caption">'
            if not after_heading.startswith(caption_open):
                return False, (
                    "expected the battery heading's sibling caption <p> to follow </h2> "
                    "immediately (UIR-12, retargeted by 29-06-PLAN.md Task 1)")
            caption_text_start = after_heading[len(caption_open):]
            if caption_text_start.startswith("—") or caption_text_start.startswith(" —"):
                return False, (
                    "expected the sibling caption to carry no leading em dash of its own "
                    "(UIR-12, retargeted by 29-06-PLAN.md Task 1)")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        return True, ""
    check(
        "the four UIR-03/07/12/13 one-line fixes hold together: .banner wraps with a nowrap "
        ".banner__label rendered on the anomaly banner's lead span, .banner__pill gains min-width: 0 "
        "while keeping flex: none and its source position before .refresh-pill, .airline-card__image "
        "gains height: auto alongside its surviving aspect-ratio, the .data-table--prose first-column "
        "nowrap rule exists after the base rule, and the rendered Battery trend heading's sibling "
        "caption follows immediately with no leading em dash of its own (UIR-12, retargeted by "
        "29-06-PLAN.md Task 1/CFG-84; quick task 260902-v2v)",
        _quick_260902_v2v_uir_03_07_12_13_fixes)

    def _quick_260902_ep7_dashboard_grid_card_gap_two_role_split():
        # quick task 260902-ep7 (BUG 2): pins the two-role spacing split
        # as a SET, not just one value in isolation — a future edit that
        # "harmonises" .dashboard-grid's margin-bottom back onto
        # .battery-trend-section's value (or vice versa) would flatten
        # the same-section/section-transition distinction right back to
        # the bug this task fixes, with no other check noticing.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        def _margin_bottom(selector_open):
            if selector_open not in css_source:
                return None, "expected style.css to declare %r" % (selector_open,)
            start = css_source.index(selector_open)
            body = css_source[start:css_source.index("}", start)]
            match = re.search(r"margin-bottom:\s*([^;]+);", body)
            if not match:
                return None, "expected %r's rule body to declare a margin-bottom" % (selector_open,)
            return match.group(1).strip(), ""

        grid_mb, err = _margin_bottom(".dashboard-grid {")
        if grid_mb is None:
            return False, err
        page_section_mb, err = _margin_bottom(".page-section {")
        if page_section_mb is None:
            return False, err
        trend_mb, err = _margin_bottom(".battery-trend-section {")
        if trend_mb is None:
            return False, err

        if grid_mb != page_section_mb:
            return False, (
                "expected .dashboard-grid's margin-bottom (%r) to equal .page-section's own "
                "same-section card-to-card value (%r) — both are same-section, card-to-card gaps"
                % (grid_mb, page_section_mb))
        if trend_mb == grid_mb:
            return False, (
                "expected .battery-trend-section's section-transition margin-bottom (%r) to stay "
                "LARGER than .dashboard-grid's card-to-card margin-bottom (%r) — collapsing them back "
                "to one value re-flattens the two-role split this task introduced" % (trend_mb, grid_mb))
        if grid_mb != "var(--space-lg)":
            return False, "expected .dashboard-grid to use the --space-lg token by name, got %r" % (grid_mb,)
        if trend_mb != "var(--space-2xl)":
            return False, (
                "expected .battery-trend-section's margin-bottom to stay var(--space-2xl) — the section "
                "transition value, untouched by this task — got %r" % (trend_mb,))
        return True, ""
    check(
        "the two-role spacing split holds as a pair: .dashboard-grid's margin-bottom equals "
        ".page-section's own same-section card-to-card value (var(--space-lg)), while "
        ".battery-trend-section's section-transition margin-bottom stays the larger, untouched "
        "var(--space-2xl) (260902-ep7 BUG 2)",
        _quick_260902_ep7_dashboard_grid_card_gap_two_role_split)

    def _06_6_4_1_1_03_desktop_card_padding_mobile_density_pair():
        # 06.6.4.1.1-03 Task 1 (D-15): pins BOTH halves of the desktop-
        # padding/mobile-density pair as a set — a future "just harmonise
        # the padding" edit that raises the base rules to --space-lg
        # directly (deleting the mobile-density half) or that forgets to
        # bump one of the three selectors inside the >= 960px override
        # would each silently break one half with no other check
        # noticing.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        selectors = (".page-section", ".theme-status", ".battery-trend-section")

        # Base rules (below the breakpoint) must still declare the
        # mobile-density value.
        for selector in selectors:
            needle = selector + " {"
            if needle not in css_source:
                return False, "expected style.css to declare %r" % (needle,)
            start = css_source.index(needle)
            body = css_source[start:css_source.index("}", start)]
            if "padding: var(--space-md)" not in body:
                return False, (
                    "expected %r's base rule to still declare padding: var(--space-md) "
                    "(the mobile-keeps-its-density half of D-15)" % (selector,))

        # The >= 960px override must exist, cover all three selectors in
        # one rule, and declare the desktop padding value.
        media_at = css_source.index("@media (min-width: 960px) {")
        media_close = css_source.index("\n}\n", media_at)
        media_body = css_source[media_at:media_close]
        override_pattern = (
            r"\.page-section,\s*\.theme-status,\s*\.battery-trend-section\s*\{"
            r"\s*padding:\s*var\(--space-lg\);"
        )
        if not re.search(override_pattern, media_body):
            return False, (
                "expected the @media (min-width: 960px) block to declare a single rule "
                "covering .page-section, .theme-status and .battery-trend-section with "
                "padding: var(--space-lg) (D-15's desktop half)")
        return True, ""
    check(
        "the desktop-padding/mobile-density pair holds together: .page-section, .theme-status "
        "and .battery-trend-section all still declare padding: var(--space-md) in their own base "
        "rules, and one shared rule inside the @media (min-width: 960px) block raises all three "
        "to padding: var(--space-lg) (06.6.4.1.1-03 D-15)",
        _06_6_4_1_1_03_desktop_card_padding_mobile_density_pair)

    def _quick_260902_ep7_summary_accent_and_reservation_list():
        # quick task 260902-ep7 (BUG 3): pins both halves of the fix as
        # a pair — the bare `summary` rule must declare the accent
        # colour, AND style.css's own exhaustive accent-reservation list
        # must name the summary's label text (not just its ::marker) —
        # so the list cannot drift back to naming only the marker while
        # the rule keeps the broader use, or vice versa.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        if "\nsummary {" not in css_source:
            return False, "expected style.css to declare a bare summary rule"
        start = css_source.index("\nsummary {")
        summary_body = css_source[start:css_source.index("}", start)]
        if "var(--color-accent)" not in summary_body:
            return False, "expected the bare summary rule to declare the accent colour"

        # The reservation list lives in the file's opening comment block,
        # well before the first real rule — slice to the first "*/" to
        # stay inside it and avoid a false match against some unrelated
        # later comment mentioning "summary".
        header_end = css_source.index("*/")
        header = css_source[:header_end]
        if "summary" not in header:
            return False, "expected the accent-reservation list to mention <summary> at all"
        if "label text" not in header:
            return False, (
                "expected the accent-reservation list to explicitly name the summary's own label "
                "text, not just its ::marker — the broadening this task makes must be recorded, not "
                "silent")
        return True, ""
    check(
        "the bare summary rule declares var(--color-accent), and style.css's own exhaustive "
        "accent-reservation list explicitly names the summary's label text (not just its ::marker) — "
        "the broadening is recorded, not silent (260902-ep7 BUG 3)",
        _quick_260902_ep7_summary_accent_and_reservation_list)

    def _quick_260902_chc_skip_guard_cross_file_contract():
        # Check 5: the cross-file contract the interaction-skip guard
        # depends on. This guard's failure mode is silence — when it
        # stops matching, nothing errors and no other check moves, the
        # page simply begins swapping content out from under a user
        # mid-interaction — so this is the only thing that would notice.
        #
        # 19-09-PLAN.md (D-02): retargeted in place (same check name/
        # function). The open-disclosure clause is GONE from
        # freshness.js on purpose (D-02 removes the silent-suspension
        # behaviour it caused) — this check's own assertion flips from
        # "still present" to "still absent" for that one clause, while
        # the fixture and the INPUT/SUMMARY/SPARKLINE_HIT_CLASS halves
        # are unchanged: a targeted swap never touches a <details>
        # element, so no interaction-skip clause is needed to protect
        # one any more.
        tmp = _mkstate("h-skip-guard-contract")
        try:
            now = _now()
            _seed_device_health(tmp, [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4190),
            ])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_unresolved_prefixes(tmp, {
                "ABC": {
                    "count": 2, "first_seen": _iso(now), "last_seen": _iso(now),
                    "example_callsign": "ABC123"},
            })
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "<details" not in rendered:
                return False, "expected at least one <details> disclosure to actually render (fixture gap)"
            if "data-filter-input" not in rendered:
                return False, "expected the registry filter input to actually render (fixture gap)"
            if health_page.SPARKLINE_HIT_CLASS not in rendered:
                return False, "expected the battery chart's hit-target class to actually render (fixture gap)"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        if "details[open]" in js:
            return False, (
                "freshness.js still checks for an open <details> disclosure — D-02 removes that "
                "silent-suspension clause entirely")
        for tag_literal in ("INPUT", "SUMMARY"):
            if tag_literal not in js:
                return False, (
                    "freshness.js no longer names %r among the focusable elements it skips on"
                    % tag_literal)
        if health_page.SPARKLINE_HIT_CLASS not in js:
            return False, "freshness.js no longer references SPARKLINE_HIT_CLASS's own literal value"
        return True, ""
    check(
        "the interaction-skip guard's cross-file contract: a fixture rich enough to actually render a "
        "disclosure, a filter input and a chart hit target, and freshness.js's shipped source still "
        "checks for a focused INPUT/SUMMARY and health_page.SPARKLINE_HIT_CLASS's own literal value "
        "but no longer checks for an open <details> at all (19-09-PLAN.md, D-02: a targeted swap never "
        "touches one, so the silent-suspension clause is gone, not merely unused) — this guard's "
        "failure mode is silence, so this check is the only thing that would notice a drift",
        _quick_260902_chc_skip_guard_cross_file_contract)

    # --- 19-09-PLAN.md Task 3: pin the new freshness contract ------------

    def _19_09_freshness_swap_selectors_pinned_both_directions():
        # The duplicated-not-imported agreement between the Python swap
        # registry and freshness.js's own copy of it, pinned from both
        # directions: every declared target must actually appear in the
        # script, AND the script's excluded regions (the sparkline hit
        # class, the filter-input attribute, a <details> selector) must
        # never sneak into a future edit's swap list — a future editor
        # who widens the swap to "just replace the whole main content"
        # would silently kill battery-trend.js's chart and
        # list-filter.js's filter, exactly the regression D-02's own
        # interfaces section names by number (Pitfall 5).
        #
        # 23-06-PLAN.md Task 1 (D1/CFG-35): GENERALISED in place rather
        # than replaced. The one tuple is now one entry in a per-page
        # mapping, so this loop iterates every page's list; the key-set
        # equality that the one-tuple form structurally could not see is
        # asserted by its own check below.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        for page_key, selectors in sorted(
                layout.REFRESH_SWAP_SELECTORS_BY_PAGE.items()):
            for selector in selectors:
                if selector not in js:
                    return False, (
                        "expected layout.REFRESH_SWAP_SELECTORS_BY_PAGE[%r] entry %r verbatim "
                        "in freshness.js" % (page_key, selector))
        # A dot-prefixed class selector, as it would appear inside a
        # querySelector(All) call targeting the sparkline hit points for
        # REPLACEMENT — never confused with the space-padded substring
        # test userIsInteracting() legitimately runs, or with the
        # "sparkline-hit--active" swap-guard used by the battery-readout
        # text update, neither of which is a swap-target selector.
        if ".sparkline-hit\"" in js or ".sparkline-hit'" in js:
            return False, (
                "freshness.js must never carry a .sparkline-hit selector literal — swapping the "
                "sparkline would leave battery-trend.js permanently dead (contract 2)")
        if "[data-filter-input]" in js:
            return False, (
                "freshness.js must never reference [data-filter-input] — swapping the registry "
                "filter would leave list-filter.js permanently dead and discard an in-progress "
                "query (contract 3)")
        if "details[" in js:
            return False, (
                "freshness.js must never carry a details[...] selector literal as a swap target — "
                "the registry/readings disclosures are excluded from the swap list")
        return True, ""
    check(
        "every layout.REFRESH_SWAP_SELECTORS_BY_PAGE entry, on every page key, appears verbatim in "
        "freshness.js, and freshness.js never carries a .sparkline-hit selector literal, a "
        "[data-filter-input] reference, or a details[...] selector — the three regions Pitfall 5 "
        "names as fatal to swap (19-09-PLAN.md Task 3, generalised in place from the one-tuple "
        "form by 23-06-PLAN.md Task 1)",
        _19_09_freshness_swap_selectors_pinned_both_directions)

    # --- 23-06-PLAN.md Task 1 (D1/CFG-35): one registry, one page key,
    # three skip rules ----------------------------------------------------

    def _js_code_without_comments(js):
        """`js` with its /* */ and // comments blanked out.

        The same idiom 23-01's motion guard and 23-05's ladder check use,
        and for the same reason: freshness.js's comments quote the very
        selectors, attributes and constants these checks count, so a scan
        over raw source would be satisfied by a comment promising a rule
        nobody wrote.
        """
        stripped = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        return re.sub(r"//[^\n]*", " ", stripped)

    def _23_06_the_swap_registry_has_one_definition_site_and_one_key_set():
        # WHAT A WRONG IMPLEMENTATION DOES HERE, which is what each
        # clause below exists to catch:
        #   - it leaves the old tuple standing in health_page.py beside
        #     the new mapping (two definition sites, agreeing today);
        #   - it lets the script grow a page key the Python does not
        #     have, or keep one the Python dropped — the drift the
        #     one-tuple pin structurally could not see;
        #   - it declares a registry that agrees with the Python and
        #     never reads it, doing the real work from a second
        #     hard-coded list (23-05's own M7, in this file's shape).
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        health_src_path = os.path.join(HERE, "pages", "health_page.py")
        with open(health_src_path) as fh:
            health_src = fh.read()

        # ONE definition site. The NAME survives (every existing reader
        # and pin keeps working); the second tuple literal does not.
        if "REFRESH_SWAP_SELECTORS = (" in health_src:
            return False, (
                "companion/pages/health_page.py still defines its own REFRESH_SWAP_SELECTORS "
                "tuple — the registry in companion/layout.py is the definition site and this "
                "name must resolve FROM it, never beside it")
        if "REFRESH_SWAP_SELECTORS" not in health_src:
            return False, (
                "expected health_page.REFRESH_SWAP_SELECTORS to survive as a name — every "
                "existing reader and every shipped pin resolves through it")
        registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
        if health_page.REFRESH_SWAP_SELECTORS is not registry[layout.REFRESH_PAGE_HEALTH]:
            return False, (
                "expected health_page.REFRESH_SWAP_SELECTORS to BE the registry's Health entry, "
                "not a copy of it — a copy is a second definition site with extra steps")
        if health_page.REFRESH_SWAP_SELECTORS != (
                ".dashboard-grid",
                "div.banner--anomaly, div.banner--warn",
                "section.banner",
                ".page-header__freshness",
                'a[href="/health"]'):
            return False, (
                "Health's five regions, in their existing order, are unchanged by the move — "
                "got %r" % (health_page.REFRESH_SWAP_SELECTORS,))

        # The two KEY SETS are equal. Parsed out of the script's own
        # registry block rather than looked for one by one, so a key the
        # script carries and the Python does not is visible too.
        block = re.search(r"var SWAP_SELECTORS_BY_PAGE = \{(.*?)\n  \};", js, flags=re.S)
        if block is None:
            return False, (
                "expected a single var SWAP_SELECTORS_BY_PAGE = { ... }; registry block in "
                "freshness.js — the script's own copy of the mapping")
        js_keys = set(re.findall(r'"([a-z][a-z0-9-]*)":', block.group(1)))
        py_keys = set(registry)
        if js_keys != py_keys:
            return False, (
                "freshness.js's registry keys %r and layout.REFRESH_SWAP_SELECTORS_BY_PAGE's %r "
                "are not the same set — only in Python: %r; only in the script: %r. A key on one "
                "side alone is a page that silently never refreshes, or a script list nothing "
                "renders"
                % (sorted(js_keys), sorted(py_keys),
                   sorted(py_keys - js_keys), sorted(js_keys - py_keys)))

        # Not vacuous: the registry must be the ONLY place those
        # selectors appear in the script's own code, and it must
        # actually be read. An agreeing registry beside a second
        # hard-coded list, or an agreeing registry nobody consumes,
        # satisfies every clause above.
        code = _js_code_without_comments(js)
        expected_hits = {}
        for selectors in registry.values():
            for selector in selectors:
                expected_hits[selector] = expected_hits.get(selector, 0) + 1
        for selector, want in sorted(expected_hits.items()):
            got = code.count(selector)
            if got != want:
                return False, (
                    "the selector %r appears %d time(s) in freshness.js's own code (comments "
                    "stripped), expected %d — one per registry entry that carries it, because "
                    "the registry is the single site and a second occurrence is a second list"
                    % (selector, got, want))
        if code.count("SWAP_SELECTORS_BY_PAGE") < 2:
            return False, (
                "SWAP_SELECTORS_BY_PAGE is declared in freshness.js but never read — a registry "
                "that agrees with the Python and is not consumed proves nothing")
        return True, ""
    check(
        "the swap registry has ONE definition site (health_page.REFRESH_SWAP_SELECTORS resolves "
        "from layout.REFRESH_SWAP_SELECTORS_BY_PAGE and is that same object, with Health's five "
        "regions in their existing order, and no second tuple literal survives in health_page.py) "
        "and ONE key set (the script's registry keys equal the Python's, in both directions), with "
        "every selector appearing exactly once per registry entry in the script's comment-stripped "
        "code and the registry actually read (D1/CFG-35, 23-06-PLAN.md Task 1)",
        _23_06_the_swap_registry_has_one_definition_site_and_one_key_set)

    def _23_06_the_page_key_is_server_rendered_and_gates_the_loop():
        # The registry is selected by a key the SERVER renders, so a page
        # that declares no regions runs no loop — and the script must
        # resolve that key defensively, because "an unknown key" includes
        # every inherited Object.prototype property name.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        code = _js_code_without_comments(js)
        if layout.REFRESH_PAGE_ATTR not in code:
            return False, (
                "freshness.js never reads %r — the page key is how one loop serves three pages, "
                "and a script that ignores it is back to one hard-coded list"
                % (layout.REFRESH_PAGE_ATTR,))
        if "hasOwnProperty" not in code:
            return False, (
                "expected freshness.js to resolve the page key with an own-property test: the "
                "key arrives as markup, and 'constructor' or 'toString' would otherwise select "
                "an inherited property instead of returning")
        # Rendered on <body>, beside the two refresh copy attributes,
        # for the reason those live there: several of these regions are
        # this loop's own swap targets and <body> is never swapped.
        for page_key in sorted(layout.REFRESH_SWAP_SELECTORS_BY_PAGE):
            doc = layout.page_shell(title="T", active=page_key, body="<p>b</p>")
            marker = '%s="%s"' % (layout.REFRESH_PAGE_ATTR, page_key)
            if marker not in doc[:doc.index("</head>") + 200]:
                if marker not in doc:
                    return False, (
                        "expected page_shell(active=%r) to render %s, got no such attribute"
                        % (page_key, marker))
            body_at = doc.index("<body")
            body_tag = doc[body_at:doc.index(">", body_at) + 1]
            if marker not in body_tag:
                return False, (
                    "expected the page key on the <body> tag itself (never inside a swap "
                    "target), got %r" % (body_tag,))
        # A page with no registry entry still renders a key, and the
        # script's own guard is what makes it a no-op — the key set
        # check above is what keeps the two lists honest.
        #
        # 23-08-PLAN.md Task 1: RETARGETED IN PLACE, no count change.
        # This clause used "flights" as its example of a page that
        # declares no regions, and Flights now declares four — so the
        # example stopped being an example of anything while the
        # assertion went on passing, which is the quiet way a check
        # stops testing what its own comment claims. "airlines" is the
        # example now, chosen because it is the one remaining nav
        # destination with a filter bar and no registry entry, i.e. the
        # next page a later plan is most likely to join to the loop. The
        # ASSERTION is unchanged and still covers Flights: the loop over
        # every registry key above already renders it.
        no_entry_key = layout.nav_slug(layout.AIRLINES_ROUTE)
        if no_entry_key in layout.REFRESH_SWAP_SELECTORS_BY_PAGE:
            return False, (
                "this clause needs a page that declares NO swap regions, and %r now declares "
                "some — pick another, and do not delete the clause: it is what proves the guard "
                "lives in the script rather than in whether the attribute was rendered"
                % (no_entry_key,))
        doc = layout.page_shell(title="T", active=no_entry_key, body="<p>b</p>")
        if ('%s="%s"' % (layout.REFRESH_PAGE_ATTR, no_entry_key)) not in doc:
            return False, (
                "expected every authenticated document to carry its own page key, including the "
                "pages that declare no swap regions — the guard is in the script, not in "
                "whether the attribute was rendered")
        return True, ""
    check(
        "the swap registry is selected by a page key the SERVER renders on <body> — present for "
        "every registry key and for a page with no entry at all — and freshness.js reads that "
        "attribute and resolves it with an own-property test, so an unknown key is a no-op rather "
        "than an inherited Object property (D1/CFG-35, 23-06-PLAN.md Task 1)",
        _23_06_the_page_key_is_server_rendered_and_gates_the_loop)

    def _23_06_the_loop_knows_three_things_it_must_not_repaint():
        # Focus, pending, dirty form. The first is 22-15's and is only
        # re-asserted here; the other two are this plan's. Source scans
        # only — the BEHAVIOUR of all three is proven in a real browser
        # by companion/test_browser_ux.py, because a source scan cannot
        # tell a skip that works from a skip that is spelled correctly.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        code = _js_code_without_comments(js)
        swap_at = code.index("function swapNodes(")
        swap_body = code[swap_at:code.index("\n  }", swap_at)]
        if "isEqualNode" not in swap_body or "contains" not in swap_body:
            return False, (
                "22-15's two existing skips (an unchanged region, and a region holding the "
                "focused element) must survive this plan untouched")
        # The pending skip is PER REGION and lives in the swap, because
        # the swap is the thing that would repaint an optimistic flip.
        if ('var PENDING_ATTR = "%s";' % layout.REFRESH_PENDING_ATTR) not in code:
            return False, (
                "expected freshness.js to name layout.REFRESH_PENDING_ATTR (%r) in its own "
                "constant — the marker plan 23-07 sets has one definition site on each side and "
                "a rename on one alone is a skip that silently never fires"
                % (layout.REFRESH_PENDING_ATTR,))
        if "PENDING_ATTR" not in swap_body and "PENDING_SELECTOR" not in swap_body:
            return False, (
                "expected swapNodes() to skip a region marked pending — plan 23-07 marks its own "
                "optimistic control and this is the reconciliation rule that reads the mark "
                "(T-23-21)")
        # The dirty-form stand-down is PER TICK: a settings page whose
        # form is mid-edit should not be fetching and diffing itself at
        # all. So it is NOT in the swap, and the pending skip is not in
        # the tick — each rule sits at the level it is about.
        tick_at = code.index("function tick(")
        tick_body = code[tick_at:code.index("\n  }", tick_at)]
        if "unsavedEdits" not in tick_body and "UnsavedEdits" not in tick_body:
            return False, (
                "expected tick() itself to stand the whole cycle down while the settings form "
                "has unsaved edits — a page mid-edit should not be fetching and diffing itself "
                "at all (T-23-20/T-23-21)")
        if "PENDING_ATTR" in tick_body or "PENDING_SELECTOR" in tick_body:
            return False, (
                "the pending skip is PER REGION, not per tick: one unconfirmed control must not "
                "stand down the refresh of every other region on the page")
        # 27-04-PLAN.md (deviation, in-scope per Rule 2 — CFG-63 retired
        # the save bar this gate used to read): SUPERSEDES the B1-lesson
        # clause this check used to assert. dirty-state.js is now the
        # settings form's auto-save driver and exposes the identical
        # question as window.SkyPaneDirtyState.hasUncommittedEdits() — a
        # cross-script query with no proof-of-life marker needed on this
        # side of the seam, because the function itself only ever exists
        # on a page where dirty-state.js found the settings form (see
        # that file's own top guard).
        if "SkyPaneDirtyState" not in code:
            return False, (
                "expected the dirty-form gate to read window.SkyPaneDirtyState — dirty-state.js's "
                "own exposed cross-script query, the same small-namespace-object idiom window."
                "SkyPaneLivePreview already established")
        edits_at = code.index("function unsavedEdits(")
        edits_body = code[edits_at:code.index("\n  }", edits_at)]
        if "hasUncommittedEdits" not in edits_body:
            return False, (
                "expected the gate itself to call SkyPaneDirtyState.hasUncommittedEdits(), got %r"
                % (edits_body,))
        # And nothing about the cadence, the ladder or the guard moved.
        for needle in ("AUTO_REFRESH_INTERVAL_MS = 45000", "RETRY_CEILING_MS = 600000",
                       "RETRY_BASE_MS", "inFlight", "failAndRetry()", "isEqualNode",
                       'redirect: "manual"'):
            if needle not in js:
                return False, (
                    "expected %r to survive this plan — the cadence, the ladder, the ceiling, "
                    "the in-flight guard and the expired-session handling are earned, not "
                    "re-earned" % (needle,))
        return True, ""
    check(
        "freshness.js knows three things it must not repaint: swapNodes() keeps 22-15's unchanged"
        "-region and focused-region skips and gains a per-region pending skip, and tick() stands "
        "the whole cycle down while dirty-state.js's own window.SkyPaneDirtyState."
        "hasUncommittedEdits() reports unsaved edits — with the interval, ladder, ceiling, "
        "in-flight guard and redirect:manual all untouched (D1/CFG-35, 23-06-PLAN.md Task 1; "
        "retargeted from the retired save bar by 27-04-PLAN.md, CFG-63)",
        _23_06_the_loop_knows_three_things_it_must_not_repaint)

    # --- 23-08-PLAN.md Task 1 (D7/CFG-37): Flights joins the loop, and a
    # genuinely new detection says so once --------------------------------

    def _23_08_flights_declares_the_list_the_cards_and_the_count():
        # What Flights' registry entry must COVER and what it must
        # EXCLUDE, both named here rather than left implied. The
        # exclusion is the load-bearing half: list-filter.js captures
        # its input, its Clear control and its empty-state block once at
        # load, so a swap that replaced any of them would leave the
        # filter permanently dead — the identical trade Health's own
        # entry already records for the sparkline and the registry card.
        registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
        if layout.REFRESH_PAGE_FLIGHTS not in registry:
            return False, (
                "expected Flights to declare its own swap regions — it is the page most likely "
                "to be open when something happens and the only one of the four that could not "
                "show it (D7/CFG-37)")
        flights = registry[layout.REFRESH_PAGE_FLIGHTS]
        if layout.REFRESH_PAGE_FLIGHTS != layout.nav_slug(layout.FLIGHTS_ROUTE):
            return False, (
                "expected the Flights key to be nav_slug()'s own value, never a second "
                "vocabulary, got %r" % (layout.REFRESH_PAGE_FLIGHTS,))
        # The three things that change between polls, plus the freshness
        # line every page in this registry carries.
        for needle in ("history-cards", "data-table-wrap", "data-filter-count"):
            if not any(needle in selector for selector in flights):
                return False, (
                    "expected Flights' swap regions to cover %r — the phone card list, the "
                    "desktop table and the live count are the three things a new detection "
                    "changes, got %r" % (needle, flights))
        if ".page-header__freshness" not in flights:
            return False, (
                "expected Flights' freshness line to be a swap target, like Home's and "
                "Health's: it is what carries data-loaded-at and the state badge the loop "
                "rebuilds inside it")
        # The exclusions, by name. Each of these is an element
        # list-filter.js resolves exactly once, at load.
        for forbidden in ("data-filter-input", "data-filter-clear", "data-filter-empty",
                          "data-filter-set"):
            for selector in flights:
                if forbidden in selector:
                    return False, (
                        "Flights' swap regions name %r (%r) — list-filter.js captures that "
                        "element once at load, so replacing it leaves the filter permanently "
                        "dead and silently discards an in-progress query"
                        % (forbidden, selector))
        # Not nested: no entry may contain another, or a swap could
        # detach a node another entry is about to replace.
        for outer in flights:
            for inner in flights:
                if outer is not inner and inner.startswith(outer + " "):
                    return False, (
                        "Flights' regions %r and %r are nested — a swap can detach a node "
                        "another entry is about to replace" % (outer, inner))
        # The registry comment must SAY why the input is out, rather than
        # leaving the next reader to rediscover it.
        layout_src_path = os.path.join(HERE, "layout.py")
        with open(layout_src_path) as fh:
            layout_src = fh.read()
        flights_at = layout_src.index("FLIGHTS (23-08")
        flights_note = layout_src[flights_at:flights_at + 1600]
        if "list-filter.js" not in flights_note:
            return False, (
                "expected the registry's own Flights paragraph to name list-filter.js and the "
                "reason its captured elements are excluded — that reasoning has one home and "
                "this is it")
        return True, ""
    check(
        "Flights' swap registry entry covers the phone card list, the desktop table, the live "
        "count and the freshness line, EXCLUDES every element list-filter.js captures once at "
        "load (the input, Clear, the empty state and the set hooks), nests no entry inside "
        "another, is keyed by nav_slug()'s own value, and the registry's own comment states the "
        "exclusion's reason (D7/CFG-37, 23-08-PLAN.md Task 1)",
        _23_08_flights_declares_the_list_the_cards_and_the_count)

    def _23_08_the_highlight_is_a_diff_and_never_a_first_paint():
        # A highlight that fires on first load has told the user
        # nothing, and a highlight that fires on every row when one
        # arrives has told them something false. Both failures are the
        # same missing thing: a set of identities known BEFORE the swap.
        #
        # Source scans only. The BEHAVIOUR — both directions, and the
        # silent first refresh — is proven in a real browser by
        # companion/test_browser_ux.py, because a source scan cannot
        # tell a diff that works from a diff that is spelled correctly.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        code = _js_code_without_comments(js)
        for name, value in (("ROW_ID_ATTR", layout.REFRESH_ROW_ID_ATTR),
                            ("NEW_ROW_CLASS", layout.REFRESH_NEW_ROW_CLASS)):
            if ('var %s = "%s";' % (name, value)) not in code:
                return False, (
                    "expected freshness.js to name layout.REFRESH_%s (%r) in its own %s "
                    "constant — these are cross-file literals with one definition site on each "
                    "side, and a rename on one alone is a highlight that silently never fires"
                    % ("ROW_ID_ATTR" if name == "ROW_ID_ATTR" else "NEW_ROW_CLASS",
                       value, name))
        if "function markNewRows(" not in code:
            return False, "expected freshness.js to carry the new-row diff as its own function"
        # Called from the swap and from NOWHERE else: definition plus
        # exactly one call site. A call from tick() would run the diff
        # on a cycle that swapped nothing; a call at load would mark the
        # first paint, which is the defect this whole rule is about.
        if code.count("markNewRows(") != 2:
            return False, (
                "expected exactly one definition and one call of markNewRows(), found %d "
                "occurrence(s) — the diff belongs to the swap and to nothing else"
                % code.count("markNewRows("))
        apply_at = code.index("function applySwap(")
        apply_body = code[apply_at:code.index("\n  }", apply_at)]
        if "markNewRows(" not in apply_body:
            return False, (
                "expected applySwap() to run the diff AFTER the regions are replaced — a diff "
                "taken before the swap is a diff over the document that is about to be thrown "
                "away")
        init_at = code.index("var knownRowIds")
        init_line = code[init_at:code.index("\n", init_at)]
        if "collectRowIds()" not in init_line:
            return False, (
                "expected the known-identity set to be populated from the page AS FIRST "
                "RENDERED (var knownRowIds = collectRowIds();), got %r. Starting it empty makes "
                "the first refresh announce the whole list, which is exactly the "
                "everything-is-new failure the diff exists to prevent" % (init_line,))
        mark_at = code.index("function markNewRows(")
        mark_body = code[mark_at:code.index("\n  }", mark_at)]
        if "hasOwnProperty" not in mark_body:
            return False, (
                "expected the diff to test the known set with an own-property test: the "
                "identities arrive as markup, and 'constructor' or 'toString' would otherwise "
                "resolve to an inherited Object property and be read as already-known")
        if "classList.add" not in mark_body:
            return False, "expected the highlight to be applied as a class on an existing node"
        # One-shot by construction: nothing ever removes the class, and
        # nothing needs to. The animation runs once on a node that was
        # itself just inserted, and the next swap replaces that node
        # entirely. A file that removes it is a file that could re-add
        # it, which is a row that flashes twice for one arrival.
        if "NEW_ROW_CLASS" in code and "classList.remove(NEW_ROW_CLASS" in code:
            return False, (
                "expected nothing to remove the highlight class — the animation ends on its "
                "own and the next swap replaces the node, so a removal path is only a way to "
                "re-trigger it")
        # And the diff writes no markup: it is a class toggle on a node
        # the swap already inserted.
        for sink in ("innerHTML", "insertAdjacentHTML", "document.write", "outerHTML"):
            if sink in mark_body:
                return False, (
                    "expected the diff to use no markup-writing DOM sink, found %r" % (sink,))
        return True, ""
    check(
        "freshness.js's new-row highlight is a DIFF over server-rendered row identity: its two "
        "cross-file literals equal layout.REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS, the known "
        "set is populated from the page as first rendered rather than empty, the diff runs from "
        "applySwap() and from nowhere else, resolves the set with an own-property test, applies "
        "one class through classList and never removes it, and writes no markup (D7/CFG-37, "
        "23-08-PLAN.md Task 1)",
        _23_08_the_highlight_is_a_diff_and_never_a_first_paint)

    # --- 23-06-PLAN.md Task 2 (D1/CFG-35): Home and the Frame strip go
    # live, from the same builder and the same loop ------------------------

    def _home_ctx(tmp, now):
        """A Home ctx rich enough to render every region Home declares —
        a gallery entry for the picture, a check-in for the strip's own
        next-wake resolution, and a device config for its two switches.
        """
        return {
            "state_dir": tmp, "now": now,
            "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
            "last_checkin_ts": now,
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {"device_state": "ok", "pipeline_state": "ok",
                             "battery_state": "ok",
                             "device_detail_html": "", "pipeline_html": ""},
            "simple_mode": False,
        }

    def _selector_literals(selector):
        """Every literal identifier a CSS selector names — its tags,
        classes, attribute names and quoted attribute values.

        Used to ask a rendered page "do you actually contain the region
        you declared?" without a DOM parser. It is deliberately loose
        about STRUCTURE (it cannot tell a section from a div) and exact
        about NAMES, which is where the drift this guards against
        happens: a class renamed in a page module and not in the
        registry is a region that silently stops refreshing, with no
        error anywhere.
        """
        return [token for token in re.split(r'[.#\[\],"=\s>]+', selector) if token]

    def _23_06_the_freshness_line_has_one_builder_and_three_call_sites():
        from companion.pages import home_page
        tmp = _mkstate("h-shared-freshness")
        try:
            now_iso = _iso(_now())
            built = layout.freshness_line_html(now_iso)
            health = health_page.render(_ctx(tmp, now=now_iso))
            home = home_page.render(_home_ctx(tmp, now_iso))
            for rendered, name in ((health, "Health"), (home, "Home")):
                if built not in rendered:
                    return False, (
                        "expected %s's freshness line to be layout.freshness_line_html()'s own "
                        "output verbatim — one definition site, three call sites, the same "
                        "contract frame_strip_html() and sidebar_nav() already state. Built:\n%r"
                        "\nRendered page has: %r"
                        % (name, built,
                           rendered[rendered.index("page-header__freshness") - 40:
                                    rendered.index("page-header__freshness") + 300]
                           if "page-header__freshness" in rendered else "no freshness line"))
                if rendered.count("data-loaded-at") != 1:
                    return False, (
                        "expected exactly one data-loaded-at on %s — freshness.js reads it with "
                        "a single querySelector and a second would silently win, got %d"
                        % (name, rendered.count("data-loaded-at")))
                if rendered.count("data-refresh-pill") != 1:
                    return False, (
                        "expected exactly one data-refresh-pill on %s, got %d"
                        % (name, rendered.count("data-refresh-pill")))
            # The markup now comes from layout.py, and health_page.py
            # does not build a second one beside it.
            health_src_path = os.path.join(HERE, "pages", "health_page.py")
            with open(health_src_path) as fh:
                health_src = fh.read()
            if 'class="page-header__freshness' in health_src:
                return False, (
                    "companion/pages/health_page.py still builds its own freshness line — the "
                    "markup has one definition site and it is companion/layout.py")
            layout_src_path = os.path.join(HERE, "layout.py")
            with open(layout_src_path) as fh:
                layout_src = fh.read()
            if 'class="page-header__freshness' not in layout_src:
                return False, "expected the freshness line's markup in companion/layout.py"
            # The builder's own shape, in source order: the neutral dot,
            # the prefix, the clock element, the pill.
            positions = [
                built.index(layout.REFRESH_LIVE_DOT_ATTR),
                built.index(layout.escape_html(health_page.i18n.t(layout.FRESHNESS_PREFIX_TEXT))),
                built.index("data-refresh-clock"),
                built.index("data-refresh-pill"),
            ]
            if positions != sorted(positions):
                return False, (
                    "expected dot, prefix, clock, pill in that source order, got %r in %r"
                    % (positions, built))
            if built.count("data-relative") != 1:
                return False, (
                    "expected exactly one <time data-relative> in the freshness line, got %d"
                    % built.count("data-relative"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's and Home's freshness lines are layout.freshness_line_html()'s own output "
        "verbatim — ONE definition site, the markup gone from health_page.py entirely — each page "
        "renders exactly one data-loaded-at and one data-refresh-pill, and the builder emits the "
        "dot, the prefix, the clock element and the pill in that order with exactly one <time "
        "data-relative> (D1/CFG-35, 23-06-PLAN.md Task 2)",
        _23_06_the_freshness_line_has_one_builder_and_three_call_sites)

    def _23_06_home_declares_the_regions_it_actually_renders():
        from companion.pages import home_page
        tmp = _mkstate("h-home-regions")
        try:
            now_iso = _iso(_now())
            rendered = home_page.render(_home_ctx(tmp, now_iso))
            registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
            if layout.REFRESH_PAGE_HOME not in registry:
                return False, "expected Home to declare its own swap regions"
            if layout.REFRESH_PAGE_DISPLAY not in registry:
                return False, "expected the Display scope to declare its own swap regions"
            # NOT a closed set: plan 23-08 adds Flights, and this check
            # must not be the thing that has to change for it to.
            missing = []
            for selector in registry[layout.REFRESH_PAGE_HOME]:
                for token in _selector_literals(selector):
                    if token not in rendered:
                        missing.append((selector, token))
            if missing:
                return False, (
                    "Home declares regions it does not render: %r — a selector that matches "
                    "nothing is a region that silently never refreshes, and nothing else in this "
                    "codebase would notice" % (missing,))
            # What Home's list must COVER, named here rather than left
            # implied: the strip (where the frame's state is claimed),
            # the status tiles, the picture and the recent-flights list.
            home_list = registry[layout.REFRESH_PAGE_HOME]
            for needle in ("frame-strip", "home-status-grid", "preview-frame", "home-flights"):
                if not any(needle in selector for selector in home_list):
                    return False, (
                        "expected Home's swap regions to cover %r — the four things that change "
                        "between polls, got %r" % (needle, home_list))
            if ".page-header__freshness" not in home_list:
                return False, (
                    "expected Home's freshness line to be a swap target, like Health's: it is "
                    "what carries data-loaded-at and the state badge the loop rebuilds")
            # DISPLAY IS DELIBERATELY CONSERVATIVE. Everything else on
            # that page is a form, and a form is the one thing a swap
            # must never touch.
            display_list = registry[layout.REFRESH_PAGE_DISPLAY]
            if set(display_list) != {".page-header__freshness", ".frame-strip"}:
                return False, (
                    "expected the Display scope to declare exactly the strip and the freshness "
                    "line — everything else on that page is a form; got %r" % (display_list,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home declares the four regions that actually change between polls (the strip, the status "
        "tiles, the picture, the recent-flights list) plus its freshness line, every literal in "
        "every one of its selectors appears in the rendered page, and the Display scope declares "
        "exactly the strip and the freshness line — everything else there is a form (D1/CFG-35, "
        "23-06-PLAN.md Task 2)",
        _23_06_home_declares_the_regions_it_actually_renders)

    def _23_06_the_strip_countdown_formats_and_never_decides():
        # D1's own hardest clause: the countdown is FORMATTING. The
        # instant and the state word are server-computed by
        # companion/wake.py through frame_state.resolve_state(), and the
        # element ticks toward that instant without ever recomputing
        # whether the frame is due, held or late.
        now_iso = "2026-08-27T12:00:00+00:00"
        ctx = {
            "now": now_iso, "last_checkin_ts": "2026-08-27T11:55:00+00:00",
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
        }
        strip = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        if "frame-strip__cell--update" not in strip:
            return False, "expected the strip's next-update cell in this fixture"
        cell = strip[strip.index("frame-strip__cell--update"):]
        element = re.search(r"<time ([^>]*)>(.*?)</time>", cell, flags=re.S)
        if element is None:
            return False, (
                "expected a <time data-relative> countdown in the next-update cell — the "
                "user's own answer to 'will I make the next RER' is how long, not what o'clock")
        attrs, text = element.group(1), element.group(2)
        if layout.RELATIVE_COUNTDOWN_ATTR not in attrs:
            return False, (
                "expected the countdown to be marked as one (%r) — an unmarked element turns "
                "itself into an age the moment its instant passes, which is a different claim "
                "halfway through its own life" % (layout.RELATIVE_COUNTDOWN_ATTR,))
        # It ticks toward the SERVER's own instant, not one computed here.
        resolved_iso = wake.next_wake_status(
            ctx["last_checkin_ts"], ctx["device_config"])[0]
        expected_instant = layout._machine_instant(layout.parse_iso(resolved_iso))
        if ('datetime="%s"' % layout.escape_html(expected_instant)) not in attrs:
            return False, (
                "expected the countdown to carry companion/wake.py's own resolved next-wake "
                "instant %r, got %r" % (expected_instant, attrs))
        if text != layout.escape_html(layout.relative_future_text(
                int((layout.parse_iso(resolved_iso) - layout.parse_iso(now_iso))
                    .total_seconds()))):
            return False, (
                "expected the countdown's server text to be the ladder's own future form over "
                "that instant, got %r" % (text,))
        # And the state word is untouched by it: the headline still
        # carries frame_state's own template, rendered whole.
        if "Next update ≈" not in strip:
            return False, (
                "expected the state word to stay frame_state.resolve_state()'s own — the "
                "countdown formats a duration and decides nothing (D-03/CFG-26)")
        # No script anywhere computes a frame state.
        js_dir = os.path.join(HERE, "static")
        for filename in sorted(os.listdir(js_dir)):
            if not filename.endswith(".js"):
                continue
            with open(os.path.join(js_dir, filename)) as fh:
                js = fh.read()
            for banned in ("resolve_state", "HEADLINE_LATE", "HEADLINE_HELD", "HEADLINE_DUE"):
                if banned in js:
                    return False, (
                        "companion/static/%s names %r — whether the frame is due, held or late "
                        "is server/wake.py's answer and no script's" % (filename, banned))
        return True, ""
    check(
        "the Frame strip's next-update cell carries a marked <time data-relative-countdown> over "
        "companion/wake.py's OWN resolved instant, reading the ladder's future form, beside a "
        "state word that stays frame_state.resolve_state()'s — and no script in companion/static "
        "names a state or a headline template at all (D1/D-03/CFG-26, 23-06-PLAN.md Task 2)",
        _23_06_the_strip_countdown_formats_and_never_decides)

    def _23_06_the_picture_fades_only_when_the_picture_changed():
        # A fade that fires on every swap would flash the page every 45
        # seconds for no information, which is worse than no fade at all.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        stripped = re.sub(r"/\*.*?\*/", " ", css_source, flags=re.S)
        names = re.findall(r"@keyframes\s+([A-Za-z_-][\w-]*)", stripped)
        if len(names) != len(set(names)):
            return False, "every @keyframes name is defined exactly once (23-01's own guard)"
        if "skypane-fade-in" not in names:
            return False, (
                "expected a named fade-in keyframes block for the refreshed picture, got %r"
                % (names,))
        rule_at = stripped.index(".is-fading-in")
        rule = stripped[rule_at:stripped.index("}", rule_at)]
        if "var(--motion-fast)" not in rule:
            return False, (
                "expected the fade to spend 23-01's REACTION token — somebody is waiting to read "
                "the new value — got %r" % (rule,))
        if re.search(r"(?<![\w-])\d+(?:\.\d+)?m?s(?![\w-])", rule):
            return False, (
                "expected no bare duration literal in the fade rule (23-01's guard), got %r"
                % (rule,))
        # The JS half: the class is added only after a real src
        # comparison, and only ever by the script.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        code = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        code = re.sub(r"//[^\n]*", " ", code)
        fade_at = code.index("function markPictureFade(")
        fade_body = code[fade_at:code.index("\n  }", fade_at)]
        if '"src"' not in fade_body:
            return False, (
                "expected the fade to compare the picture's own src — the honest signal for "
                "'this is a NEW render' — got %r" % (fade_body,))
        if "FADE_CLASS" not in fade_body:
            return False, "expected the fade class to be added inside that comparison"
        if code.count("FADE_CLASS") < 2:
            return False, (
                "the fade class is declared and never applied — a constant that agrees with the "
                "stylesheet and is not consumed proves nothing")
        # The SERVER never renders it: the motion belongs to the loop
        # that knows a new picture arrived, exactly like the breathing
        # dot 23-05 shipped.
        from companion.pages import home_page
        tmp = _mkstate("h-fade")
        try:
            rendered = home_page.render(_home_ctx(tmp, _iso(_now())))
            if "is-fading-in" in rendered:
                return False, (
                    "expected the server to render no fade class at all — a picture that fades "
                    "in on every page load is an animation playing, not information")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "the refreshed picture fades through a named keyframes block spending var(--motion-fast) "
        "with no bare literal, the class is applied only after freshness.js compares the image's "
        "own src (a fade on every swap would flash the page every 45s for no information), and the "
        "server renders it never (D1+D3/CFG-32, 23-06-PLAN.md Task 2)",
        _23_06_the_picture_fades_only_when_the_picture_changed)

    # --- 19-06-PLAN.md Task 1: layout.stat_tile()'s caption_title tooltip
    # (D-06) ------------------------------------------------------------

    def _stat_tile_caption_title_byte_identical_when_unused():
        default_call = layout.stat_tile("C", "<p>x</p>", "ok", None)
        explicit_none = layout.stat_tile("C", "<p>x</p>", "ok", None, caption_title=None)
        explicit_empty = layout.stat_tile("C", "<p>x</p>", "ok", None, caption_title="")
        if default_call != explicit_none or default_call != explicit_empty:
            return False, (
                "expected stat_tile()'s output to be byte-identical whether caption_title is "
                "omitted, None, or the empty string")
        if "title=" in default_call:
            return False, "expected no title attribute anywhere in the unused-caption_title output"
        return True, ""
    check(
        "layout.stat_tile()'s new caption_title parameter is byte-identical to the pre-existing output "
        "when omitted, None, or '' (19-06-PLAN.md Task 1, D-06)",
        _stat_tile_caption_title_byte_identical_when_unused)

    def _stat_tile_caption_title_renders_as_tooltip_on_caption_only():
        markup = layout.stat_tile("Cap", "<p>y</p>", "ok", None, caption_title="Tech Term")
        if markup.count('title="Tech Term"') != 1:
            return False, (
                "expected exactly one title=\"Tech Term\" attribute in the output, got %d"
                % markup.count('title="Tech Term"'))
        caption_open = markup.index('<p class="text-label stat-tile__caption"')
        caption_close = markup.index(">", caption_open)
        caption_tag = markup[caption_open:caption_close]
        if 'title="Tech Term"' not in caption_tag:
            return False, "expected the title attribute on the caption <p> element itself, got %r" % caption_tag
        return True, ""
    check(
        "layout.stat_tile()'s caption_title renders as a title attribute on the caption <p> element, and "
        "nowhere else (19-06-PLAN.md Task 1, D-06)",
        _stat_tile_caption_title_renders_as_tooltip_on_caption_only)

    def _stat_tile_caption_title_is_escaped():
        hostile = 'a<b"c'
        markup = layout.stat_tile("Cap", "<p>y</p>", "ok", None, caption_title=hostile)
        if hostile in markup:
            return False, "expected the hostile caption_title to be escaped, not interpolated raw"
        if "&lt;" not in markup or "&quot;" not in markup:
            return False, "expected the escaped caption_title to carry &lt; and &quot;"
        return True, ""
    check(
        "layout.stat_tile()'s caption_title is escaped through escape_html(), matching every other "
        "attribute value this module emits (19-06-PLAN.md Task 1, D-06/T-19-08)",
        _stat_tile_caption_title_is_escaped)

    # --- 19-06-PLAN.md Task 2: Health's stat tiles and corroboration rows
    # read in plain language (D-06) --------------------------------------

    def _visible_text_outside_title_attributes(markup):
        # A title="..." attribute IS the sanctioned home for a technical
        # term under D-06 — strip every such attribute's value before
        # scanning for banned jargon, so this guard only ever fires on a
        # real leak into visible text.
        return re.sub(r'\btitle="[^"]*"', "", markup)

    def _health_tiles_and_rows_read_in_plain_language():
        tmp = _mkstate("h-plain-language-tiles")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [{"ts": _iso(now), "hex": "abc123", "corroborated": True}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        visible = _visible_text_outside_title_attributes(rendered)
        for banned in ("Corroboration", "Single-source (uncorroborated)", "pipeline last ran"):
            if banned in visible:
                return False, "expected %r to be absent from visible text (outside a title attribute)" % banned

        for label, expected_title in (
                (health_page.PIPELINE_FRESHNESS_LABEL, health_page.PIPELINE_FRESHNESS_TITLE),
                (health_page.CORROBORATION_TILE_LABEL, health_page.CORROBORATION_TILE_TITLE),
                (health_page.RESOLUTION_RATE_LABEL, health_page.RESOLUTION_RATE_TITLE)):
            needle = ">%s<" % layout.escape_html(label)
            at = rendered.index(needle)
            caption_open = rendered.rindex('<p class="text-label stat-tile__caption"', 0, at)
            caption_close = rendered.index(">", caption_open)
            caption_tag = rendered[caption_open:caption_close]
            expected_attr = 'title="%s"' % layout.escape_html(expected_title)
            if expected_attr not in caption_tag:
                return False, (
                    "expected the %r tile's caption element to carry %s, got %r"
                    % (label, expected_attr, caption_tag))
        return True, ""
    check(
        "Health's stat tiles and corroboration rows read in plain language: 'Corroboration', "
        "'Single-source (uncorroborated)' and 'pipeline last ran' are all absent from visible text, and the "
        "Pipeline/Corroboration/Resolution-rate tiles' caption elements each carry a title attribute equal "
        "to their matching technical constant (19-06-PLAN.md Task 2, D-06)",
        _health_tiles_and_rows_read_in_plain_language)

    # --- 19-06-PLAN.md Task 3: registry/statistics prose de-jargoned
    # (D-06, CFG-04/CFG-08 surfaces) --------------------------------------

    def _health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id():
        tmp = _mkstate("h-no-jargon-full-render")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 3, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            events = []
            for source in ("fresh_hit", "cache_hit", "airline_only", "miss", "manual"):
                events.append({"ts": _iso(now), "hex": "abc123", "route_source": source})
            _seed_runway_events(tmp, events)
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if health_page.UNRESOLVED_SECTION_HEADING not in rendered or "data-filter-input" not in rendered:
            return False, "fixture gap: expected the registry card to actually render"
        if health_page.STATS_SECTION_HEADING not in rendered or "% resolved" not in rendered:
            return False, "fixture gap: expected the resolution-statistics card to actually render"
        if "adsbdb" in rendered:
            return False, "expected no occurrence of 'adsbdb' anywhere in a full render"
        visible = _visible_text_outside_title_attributes(rendered)
        if re.search(r"CFG-\d", visible):
            return False, "expected no requirement id (CFG-\\d) in visible text"
        return True, ""
    check(
        "a full Health render with a non-empty unresolved registry and stats rows (every branch rendered) "
        "contains no 'adsbdb' and no CFG-\\d requirement id outside a title attribute "
        "(19-06-PLAN.md Task 3, D-06/T-19-24)",
        _health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id)

    # ======================================================================
    # Section 1.5: companion/illustration_normalize.py — the shared
    # opaque-bbox normalization helper (quick task 260902-req-02 Task 1,
    # sibling to plan 01's panel-side server/plane/render.py fix). All
    # checks below iterate the real vendored files under
    # illustrations.ILLUSTRATION_DIR — the same "real project assets, not
    # synthetic fixtures" discipline server/test_render.py already uses —
    # except the None-bbox fallback check, which needs a synthetic
    # fully-transparent source (no vendored file has a None opaque bbox).
    # ======================================================================

    _VENDORED_ILLUSTRATION_PATHS = [
        os.path.join(illustrations.ILLUSTRATION_DIR, filename)
        for filename in illustrations.target_filenames()
    ]

    # quick task 260904-e92 (UIR-08, DP-6): the pre-change 900x263 frame
    # served 132.5-175.5KB per file (measured across the 36 gallery-visible
    # illustrations, updated by quick task 260921-v9c from 27); the
    # post-change 450x132 frame measured 40.8-53.1KB. This ceiling (64KB)
    # sits far below the OLD per-file minimum (132.5KB), so a silent
    # revert to the old frame size fails this check loudly rather than
    # merely getting dimensions right while leaving the served bytes
    # unchanged.
    _ILLUSTRATION_BYTE_CEILING = 65536

    def _all_43_normalized_outputs_share_identical_pixel_dimensions():
        if len(_VENDORED_ILLUSTRATION_PATHS) != 52:
            return False, "expected 52 vendored illustration files, got %d" % len(_VENDORED_ILLUSTRATION_PATHS)
        for path in _VENDORED_ILLUSTRATION_PATHS:
            png_bytes = illustration_normalize.normalized_png_bytes(path)
            with Image.open(io.BytesIO(png_bytes)) as out:
                if out.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                    return False, "%s normalized to %r, expected %r" % (
                        os.path.basename(path), out.size, illustration_normalize.ILLUSTRATION_TARGET_SIZE)
        return True, ""
    check(
        "all 52 vendored illustrations normalize to the exact same pixel dimensions "
        "(illustration_normalize.ILLUSTRATION_TARGET_SIZE)",
        _all_43_normalized_outputs_share_identical_pixel_dimensions)

    def _all_43_normalized_outputs_serve_well_under_the_byte_ceiling():
        for path in _VENDORED_ILLUSTRATION_PATHS:
            png_bytes = illustration_normalize.normalized_png_bytes(path)
            if len(png_bytes) >= _ILLUSTRATION_BYTE_CEILING:
                return False, "%s normalized to %d bytes, expected under the %d-byte ceiling" % (
                    os.path.basename(path), len(png_bytes), _ILLUSTRATION_BYTE_CEILING)
        return True, ""
    check(
        "all 52 vendored illustrations normalize and serve well under %d bytes per file, the UIR-08 "
        "weight fix — a regression that got the dimensions right but left the served bytes unchanged "
        "would defeat this check" % _ILLUSTRATION_BYTE_CEILING,
        _all_43_normalized_outputs_serve_well_under_the_byte_ceiling)

    def _all_43_normalized_outputs_are_centred_and_unclipped():
        target_w, target_h = illustration_normalize.ILLUSTRATION_TARGET_SIZE
        for path in _VENDORED_ILLUSTRATION_PATHS:
            png_bytes = illustration_normalize.normalized_png_bytes(path)
            with Image.open(io.BytesIO(png_bytes)) as out:
                out_rgba = out.convert("RGBA")
            bbox = panel_render._opaque_bbox(out_rgba)
            if bbox is None:
                return False, "%s: normalized output has no opaque bbox at all" % os.path.basename(path)
            left, top, right, bottom = bbox
            if left < 0 or top < 0 or right > target_w or bottom > target_h:
                return False, "%s: painted bbox %r is not fully inside the %dx%d output" % (
                    os.path.basename(path), bbox, target_w, target_h)
            centre_x, centre_y = (left + right) / 2.0, (top + bottom) / 2.0
            if abs(centre_x - target_w / 2.0) > 1.0:
                return False, "%s: painted centre-x %.2f is more than 1px from the output centre %.2f" % (
                    os.path.basename(path), centre_x, target_w / 2.0)
            if abs(centre_y - target_h / 2.0) > 1.0:
                return False, "%s: painted centre-y %.2f is more than 1px from the output centre %.2f" % (
                    os.path.basename(path), centre_y, target_h / 2.0)
        return True, ""
    check(
        "all 52 vendored illustrations normalize with their painted content centred within 1px on both "
        "axes and never clipped",
        _all_43_normalized_outputs_are_centred_and_unclipped)

    def _none_opaque_bbox_falls_back_to_source_image_without_raising():
        tmp_dir = tempfile.mkdtemp(prefix="illustration-normalize-none-bbox-")
        try:
            fully_transparent_path = os.path.join(tmp_dir, "fully-transparent.png")
            Image.new("RGBA", (400, 200), (0, 0, 0, 0)).save(fully_transparent_path)
            png_bytes = illustration_normalize.normalized_png_bytes(fully_transparent_path)
            with Image.open(io.BytesIO(png_bytes)) as out:
                if out.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                    return False, "expected the None-bbox fallback to still normalize to the target size, got %r" % (
                        out.size,)
            return True, ""
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    check(
        "a source image whose opaque bbox is None (nothing painted) falls back to the source image "
        "instead of raising, and still normalizes to the target output size",
        _none_opaque_bbox_falls_back_to_source_image_without_raising)

    def _no_module_in_companion_redefines_the_alpha_threshold():
        threshold_definition_re = re.compile(r"^[A-Z_]*ALPHA_THRESHOLD\s*=", re.MULTILINE)
        companion_dir = os.path.dirname(os.path.abspath(illustration_normalize.__file__))
        offenders = []
        for root, _dirs, files in os.walk(companion_dir):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8") as fh:
                    source = fh.read()
                if threshold_definition_re.search(source):
                    offenders.append(os.path.relpath(path, REPO_ROOT))
        if offenders:
            return False, "expected zero alpha-threshold constant definitions under companion/, found: %r" % (
                offenders,)
        return True, ""
    check(
        "no module anywhere under companion/ defines its own alpha-threshold constant — the threshold "
        "is only ever imported from server.plane.render",
        _no_module_in_companion_redefines_the_alpha_threshold)

    # ======================================================================
    # Section 1.6: companion/layout.py — <html lang>, the three-switch
    # nav footer, localised nav labels and simple-mode nav suppression
    # (D-01..D-09/D-29/D-30, 20-01-PLAN.md Task 3). Pure in-process
    # unit checks against layout.page_shell()/login_shell() — no
    # subprocess needed, mirroring this section's own Section 1.5
    # style. Every check resets prefs' ContextVars in a finally block
    # so no check's language/mode leaks into the next one.
    # ======================================================================

    def _page_shell_html_lang_follows_prefs():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_rendered = layout.page_shell(
                title="Health", active="health", body="", ui_theme="auto")
            prefs.set_request_prefs(lang="en")
            en_rendered = layout.page_shell(
                title="Health", active="health", body="", ui_theme="auto")
        finally:
            prefs.set_request_prefs(lang="en")
        if '<html lang="fr"' not in fr_rendered:
            return False, "expected <html lang=\"fr\" under lang='fr'"
        if '<html lang="en"' not in en_rendered:
            return False, "expected <html lang=\"en\" under lang='en'"
        return True, ""
    check(
        "page_shell() renders <html lang=\"fr\" under prefs.set_request_prefs(lang='fr') "
        "and <html lang=\"en\" otherwise (D-03)",
        _page_shell_html_lang_follows_prefs)

    def _login_shell_html_lang_follows_prefs():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_rendered = layout.login_shell("", ui_theme="auto")
            prefs.set_request_prefs(lang="en")
            en_rendered = layout.login_shell("", ui_theme="auto")
        finally:
            prefs.set_request_prefs(lang="en")
        if '<html lang="fr"' not in fr_rendered:
            return False, "expected <html lang=\"fr\" under lang='fr'"
        if '<html lang="en"' not in en_rendered:
            return False, "expected <html lang=\"en\" under lang='en'"
        return True, ""
    check(
        "login_shell() renders <html lang=\"fr\" under prefs.set_request_prefs(lang='fr') "
        "and <html lang=\"en\" otherwise (D-03)",
        _login_shell_html_lang_follows_prefs)

    def _shell_has_two_ordered_theme_forms_each_with_aria_label():
        rendered = layout.page_shell(
            title="Health", active="health", body="", ui_theme="auto")
        actions_in_order = re.findall(
            r'<form class="theme-form" method="post" action="([^"]+)" aria-label="[^"]+"',
            rendered)
        if actions_in_order.count("/ui-lang") != 2:
            # Once in the sidebar footer, once in the mobile-nav dropdown
            # footer — the same "both copies present" shape the existing
            # /ui-theme count check already established.
            return False, "expected exactly 2 /ui-lang forms (sidebar + mobile), got %r" % (
                actions_in_order.count("/ui-lang"),)
        if actions_in_order.count("/ui-theme") != 2:
            return False, "expected exactly 2 /ui-theme forms (sidebar + mobile), got %r" % (
                actions_in_order.count("/ui-theme"),)
        # D-17 (21-01-PLAN.md Task 1): the simple-mode switch is deleted —
        # zero /ui-mode forms anywhere in a rendered shell.
        if actions_in_order.count("/ui-mode") != 0:
            return False, "expected zero /ui-mode forms now that the route is deleted, got %r" % (
                actions_in_order.count("/ui-mode"),)
        # Document order within EACH footer copy must be lang, theme.
        first_two = actions_in_order[:2]
        if first_two != ["/ui-lang", "/ui-theme"]:
            return False, "expected the first footer's forms in order lang/theme, got %r" % (
                first_two,)
        return True, ""
    check(
        "a rendered shell contains exactly two aria-labelled theme-form forms per footer "
        "copy, actions /ui-lang, /ui-theme in that document order, and zero /ui-mode forms "
        "(D-02/D-17, 21-UI-SPEC.md §G)",
        _shell_has_two_ordered_theme_forms_each_with_aria_label)

    def _french_shell_nav_reads_the_locked_french_labels():
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = layout.page_shell(
                title="Home", active="home", body="", ui_theme="auto")
        finally:
            prefs.set_request_prefs(lang="en")
        for label in ("Accueil", "Affichage", "Vols", "Compagnies",
                      "Avancé", "État", "Appareil"):
            if label not in rendered:
                return False, "expected the French nav label %r in the rendered shell" % (label,)
        return True, ""
    check(
        "under lang='fr' the nav reads Accueil/Affichage/Vols/Compagnies/Avancé/État/"
        "Appareil (D-09)",
        _french_shell_nav_reads_the_locked_french_labels)

    def _advanced_group_always_renders_in_both_nav_copies():
        """D-17 (21-01-PLAN.md Task 1): the display-mode gate that used
        to omit the Advanced group (Health, Device) is deleted — the
        group now renders on every page for every request, in both nav
        copies. Replaces a deleted check that tested the now-removed
        omission mechanism.

        RETARGETED IN PLACE, STRICTLY NARROWER (22-14-PLAN.md Task 2,
        X9/D-10): the sub-960px copy is the BOTTOM TAB BAR now, not the
        hamburger dropdown — the Advanced group lives behind its "More"
        <details> rather than under a group label. The D-17 guarantee
        being defended is unchanged (the group is never omitted), and the
        assertion is tightened: both destinations must appear in the tab
        bar's own slice, not merely twice somewhere in the document.
        """
        rendered = layout.page_shell(
            title="Home", active="home", body="", ui_theme="auto", health_alert="warn",
            device_config={"display_enabled": True, "quiet_hours_enabled": False})
        if layout.ADVANCED_GROUP_LABEL not in rendered:
            return False, (
                "expected the Advanced group label in the sidebar copy, got %d occurrence(s)"
                % rendered.count(layout.ADVANCED_GROUP_LABEL))
        sidebar = rendered[rendered.index('<nav class="sidebar-nav"'):rendered.index("</aside>")]
        bar_start = rendered.index('<nav class="tab-bar"')
        bar = rendered[bar_start:rendered.index("</nav>", bar_start)]
        for route in (layout.HEALTH_ROUTE, layout.DEVICE_ROUTE):
            if ('href="%s"' % route) not in sidebar:
                return False, "expected a %s href in the sidebar copy" % route
            if ('href="%s"' % route) not in bar:
                return False, "expected a %s href in the tab bar copy" % route
        if layout.NAV_NOTIFICATION_CLASS not in rendered:
            return False, "expected the nav status dot (health_alert='warn')"
        return True, ""
    check(
        "the Advanced group (Health, Device) and the nav status dot always render, in both "
        "the sidebar and the bottom tab bar, on a plain request (D-17; retargeted from the "
        "dropdown by 22-14-PLAN.md Task 2)",
        _advanced_group_always_renders_in_both_nav_copies)

    # ======================================================================
    # Section 1.6b: the nav state reminder (D-03/R-03/R-04,
    # 21-04-PLAN.md Task 2) — one shared body, both nav copies, computed
    # from the same ctx["device_config"] the Frame strip reads.
    # ======================================================================

    _NAV_STATUS_DEVICE_CFG = {"display_enabled": True, "quiet_hours_enabled": False}

    def _nav_status_appears_once_in_each_nav_copy_after_the_brand():
        rendered = layout.page_shell(
            title="Home", active="home", body="", ui_theme="auto",
            device_config=_NAV_STATUS_DEVICE_CFG)
        if rendered.count('class="nav-status text-label"') != 2:
            return False, (
                "expected exactly one .nav-status reminder in the sidebar and one in the mobile "
                "dropdown, got %d" % rendered.count('class="nav-status text-label"'))
        if rendered.count('<nav class="tab-bar"') != 1:
            return False, "expected the tab bar beside them, carrying no reminder of its own"
        bar_start = rendered.index('<nav class="tab-bar"')
        if "nav-status" in rendered[bar_start:rendered.index("</nav>", bar_start)]:
            return False, "expected no third copy of the reminder inside the tab bar"
        for match in re.finditer(r'<a class="nav-status text-label"[^>]*>(.*?)</a>', rendered):
            segment = match.group(0)
            if "<form" in segment or "<button" in segment:
                return False, "expected the nav-status link to carry no <form> or <button>"
        brand_pos = rendered.index('<span class="site-title sidebar-title">')
        sidebar_nav_status_pos = rendered.index('class="nav-status text-label"', brand_pos)
        sidebar_nav_list_pos = rendered.index('<nav class="sidebar-nav"', brand_pos)
        if not (brand_pos < sidebar_nav_status_pos < sidebar_nav_list_pos):
            return False, "expected the sidebar's nav-status link between the brand and the primary nav list"
        mobile_panel_pos = rendered.index('<div id="%s" class="mobile-nav">' % layout.MOBILE_NAV_ID)
        mobile_nav_status_pos = rendered.index('class="nav-status text-label"', mobile_panel_pos)
        # RETARGETED IN PLACE (22-14-PLAN.md Task 2): the dropdown's own
        # <nav> is deleted, so "first child, before its own nav list"
        # becomes "first child, before the footer" — the panel's only
        # other region now.
        mobile_footer_pos = rendered.index('class="mobile-nav__footer"', mobile_panel_pos)
        if not (mobile_panel_pos < mobile_nav_status_pos < mobile_footer_pos):
            return False, (
                "expected the mobile dropdown's nav-status to be its first child, before "
                "its footer")
        return True, ""
    check(
        "the sidebar and the mobile dropdown each contain exactly one .nav-status link, with no "
        "<form> or <button> inside it, sitting after the brand and before the primary nav list "
        "in document order (D-03)",
        _nav_status_appears_once_in_each_nav_copy_after_the_brand)

    def _nav_status_dot_classes_follow_the_four_on_off_combinations():
        for display_enabled, quiet_hours_enabled, screen_dot, quiet_dot in (
                (True, False, "dot--ok", "dot--off"),
                (False, False, "dot--off", "dot--off"),
                (True, True, "dot--ok", "dot--ok"),
                (False, True, "dot--off", "dot--ok")):
            rendered = layout.nav_status_html(
                {"display_enabled": display_enabled, "quiet_hours_enabled": quiet_hours_enabled})
            first_dot = re.search(r'<span class="dot ([^"]+)"></span>', rendered).group(1)
            second_dot = re.findall(r'<span class="dot ([^"]+)"></span>', rendered)[1]
            if first_dot != screen_dot or second_dot != quiet_dot:
                return False, (
                    "display_enabled=%r quiet_hours_enabled=%r: expected dots (%r, %r), got (%r, %r)"
                    % (display_enabled, quiet_hours_enabled, screen_dot, quiet_dot, first_dot, second_dot))
        return True, ""
    check(
        "nav_status_html()'s two dots follow all four Screen/Quiet-hours on/off combinations "
        "(dot--ok for on, dot--off for off) (D-03)",
        _nav_status_dot_classes_follow_the_four_on_off_combinations)

    def _french_nav_status_reads_ecran_allume_heures_calmes_desactivees():
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = layout.nav_status_html(_NAV_STATUS_DEVICE_CFG)
        finally:
            prefs.set_request_prefs(lang="en")
        if "Écran allumé" not in rendered or "Heures calmes désactivées" not in rendered:
            return False, "expected the fully-French reminder text, got %r" % (rendered,)
        # Check the VISIBLE dot-label text only — "dot--off" is a
        # legitimate CSS class name, not leaked English text, so the
        # whole markup string is not the thing to scan for "off".
        labels = re.findall(r'<span class="dot-label">([^<]*)</span>', rendered)
        for label in labels:
            if "off" in label.lower():
                return False, "expected no leftover English 'off' in a visible label, got %r" % (label,)
        return True, ""
    check(
        "under lang='fr' the reminder reads 'Écran allumé' and 'Heures calmes désactivées' — "
        "fully French, never 'Heures calmes off' (R-04)",
        _french_nav_status_reads_ecran_allume_heures_calmes_desactivees)

    def _nav_status_html_none_or_falsy_device_config_renders_nothing():
        if layout.nav_status_html(None) != "":
            return False, "expected nav_status_html(None) to return the empty string"
        if layout.nav_status_html({}) != "":
            return False, "expected nav_status_html({}) to return the empty string"
        rendered = layout.page_shell(title="Home", active="home", body="", ui_theme="auto")
        if "nav-status" in rendered:
            return False, "expected page_shell(device_config=None) to render no .nav-status at all"
        return True, ""
    check(
        "nav_status_html(None) and nav_status_html({}) both return '', and "
        "page_shell(..., device_config=None) — the default, used by login/404/error pages — "
        "renders no .nav-status at all (D-03)",
        _nav_status_html_none_or_falsy_device_config_renders_nothing)

    def _login_shell_carries_no_nav_status_and_is_unchanged():
        rendered = layout.login_shell("", ui_theme="auto")
        if "nav-status" in rendered:
            return False, "expected the login shell to carry no .nav-status markup at all"
        return True, ""
    check(
        "login_shell() — which never takes a device_config parameter — carries no .nav-status "
        "markup, unchanged by this task (D-03)",
        _login_shell_carries_no_nav_status_and_is_unchanged)

    # ======================================================================
    # Section 1.7: companion/layout.py's new status_row()/
    # section_intro_html() primitives, and health_page.py's verdict-free
    # _device_timestamp_only()/device_detail_html (D-21/D-17/§C,
    # 20-03-PLAN.md Task 1).
    # ======================================================================

    def _status_row_renders_dot_label_verdict_detail():
        rendered = layout.status_row(
            "Frame", "Checking in normally", "Last check-in 2m ago", "ok")
        if "status-row--ok" not in rendered:
            return False, "expected the status-row--ok modifier class"
        if "dot--ok" not in rendered:
            return False, "expected the dot--ok class"
        for text in ("Frame", "Checking in normally", "Last check-in 2m ago"):
            if text not in rendered:
                return False, "expected %r in the rendered row" % (text,)
        if rendered.count("status-row__label") != 1:
            return False, (
                "expected exactly one status-row__label occurrence, got %d"
                % rendered.count("status-row__label"))
        return True, ""
    check(
        "status_row('Frame', 'Checking in normally', 'Last check-in 2m ago', 'ok') carries "
        "status-row--ok, dot--ok, all three texts and exactly one status-row__label (D-21)",
        _status_row_renders_dot_label_verdict_detail)

    def _status_row_empty_label_omits_the_label_span():
        rendered = layout.status_row("", "Not connected", "checked 10 min ago", "warn")
        if "status-row__label" in rendered:
            return False, "expected no status-row__label span when label=''"
        return True, ""
    check(
        "status_row('', ..., 'warn') omits the status-row__label span entirely, not merely "
        "its text (D-21, 20-UI-SPEC.md Section Anatomy A)",
        _status_row_empty_label_omits_the_label_span)

    def _status_row_unrecognised_state_falls_back_safely():
        rendered = layout.status_row("Frame", "Verdict", "Detail", "nonsense")
        if "status-row--nonsense" in rendered:
            return False, "expected no status-row--nonsense modifier class to ever be emitted"
        if layout._DEFAULT_STATUS_DOT_CLASS not in rendered:
            return False, "expected the default dot class as the fallback"
        return True, ""
    check(
        "status_row(..., state='nonsense') falls back to the default dot class and emits no "
        "status-row--nonsense class (T-20-18)",
        _status_row_unrecognised_state_falls_back_safely)

    def _status_row_escapes_hostile_verdict_and_detail():
        rendered = layout.status_row(
            "Frame", "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "error")
        if "<script>" in rendered or "<img " in rendered:
            return False, "expected the hostile verdict/detail to come back escaped"
        if "&lt;script&gt;" not in rendered:
            return False, "expected the escaped verdict to be present"
        return True, ""
    check(
        "status_row() with a hostile <script>-shaped verdict/detail comes back escaped, never "
        "raw markup (T-20-03)",
        _status_row_escapes_hostile_verdict_and_detail)

    def _section_intro_html_is_byte_identical_to_the_promoted_markup():
        rendered = layout.section_intro_html("test-id", "Heading", "Description")
        expected = (
            '<div class="section-intro">'
            '<h2 id="test-id" class="text-heading">Heading</h2>'
            '<p class="text-label section-caption">Description</p>'
            "</div>")
        if rendered != expected:
            return False, "expected %r, got %r" % (expected, rendered)
        return True, ""
    check(
        "layout.section_intro_html() emits the byte-identical markup health_page.py's own "
        "former private _section_intro_html() rendered before the promotion (20-UI-SPEC.md "
        "Section Anatomy C)",
        _section_intro_html_is_byte_identical_to_the_promoted_markup)

    def _section_intro_html_escapes_hostile_section_id():
        rendered = layout.section_intro_html('"><script>alert(1)</script>', "Heading", "Description")
        if "<script>" in rendered:
            return False, "expected a hostile section_id to be escaped, got raw markup: %r" % (rendered,)
        if "&lt;script&gt;" not in rendered:
            return False, "expected the escaped section_id to be present: %r" % (rendered,)
        return True, ""
    check(
        "layout.section_intro_html() escapes a hostile section_id argument, never writing it raw "
        "into the id=\"...\" attribute (WR-03, 20-REVIEW.md)",
        _section_intro_html_escapes_hostile_section_id)

    def _health_page_no_longer_defines_section_intro_html():
        if hasattr(health_page, "_section_intro_html"):
            return False, "expected health_page._section_intro_html to be gone after the promotion"
        return True, ""
    check(
        "health_page no longer defines its own _section_intro_html — layout.section_intro_html "
        "is the one definition",
        _health_page_no_longer_defines_section_intro_html)

    def _device_timestamp_only_carries_no_verdict_text():
        now = _iso(_now())
        ts = _ago(120)
        detail_only = health_page._device_timestamp_only({"ts": ts}, now)
        if "widget-verdict" in detail_only:
            return False, "expected no widget-verdict class in the detail-only fragment"
        for verdict_text in health_page.DEVICE_STATE_TEXT.values():
            if verdict_text in detail_only:
                return False, "expected no DEVICE_STATE_TEXT verdict text (%r) in the detail-only fragment" % (
                    verdict_text,)
        full_row, _state = health_page._device_section({"ts": ts}, now)
        verdict_occurrences = sum(
            1 for verdict_text in health_page.DEVICE_STATE_TEXT.values()
            if verdict_text in full_row)
        if verdict_occurrences != 1:
            return False, (
                "expected _device_section() to still carry exactly one DEVICE_STATE_TEXT "
                "verdict, got %d" % verdict_occurrences)
        return True, ""
    check(
        "_device_timestamp_only() emits no widget-verdict class and no DEVICE_STATE_TEXT "
        "value, while _device_section() still carries exactly one (D-17)",
        _device_timestamp_only_carries_no_verdict_text)

    def _compute_health_state_carries_device_detail_html():
        tmp = _mkstate("device-detail-html")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(120), 3800)])
            state = health_page.compute_health_state(tmp, now=_iso(now))
            if "device_detail_html" not in state:
                return False, "expected a device_detail_html key on compute_health_state()'s dict"
            detail_only = state["device_detail_html"]
            if "widget-verdict" in detail_only:
                return False, "expected device_detail_html to carry no widget-verdict class"
            for verdict_text in health_page.DEVICE_STATE_TEXT.values():
                if verdict_text in detail_only:
                    return False, "expected device_detail_html to carry no DEVICE_STATE_TEXT verdict text"
            if detail_only not in state["device_html"]:
                return False, (
                    "expected device_detail_html to be the exact verdict-free fragment "
                    "embedded inside device_html")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "compute_health_state()'s returned dict carries a device_detail_html key holding the "
        "verdict-free fragment also embedded (once) inside device_html (D-17)",
        _compute_health_state_carries_device_detail_html)

    # ======================================================================
    # Section 1.8: companion/layout.py's language-aware relative_age_
    # text()/local_clock_text() (D-07, 20-03-PLAN.md Task 2). Every
    # check resets prefs' ContextVars in a finally block so no check's
    # language leaks into the next one.
    # ======================================================================

    def _relative_age_text_french_seconds_bucket_reads_a_linstant():
        try:
            prefs.set_request_prefs(lang="fr")
            thirty_s = layout.relative_age_text(30)
            one_day = layout.relative_age_text(90000)
        finally:
            prefs.set_request_prefs(lang="en")
        if thirty_s != "à l’instant":
            return False, "expected relative_age_text(30) under fr to be 'à l’instant', got %r" % (thirty_s,)
        if not one_day.startswith("il y a 1"):
            return False, "expected relative_age_text(90000) under fr to start with 'il y a 1', got %r" % (one_day,)
        if " " not in one_day:
            return False, "expected a real U+00A0 between the number and the unit (D-09), got %r" % (one_day,)
        return True, ""
    check(
        "under lang='fr', relative_age_text(30) reads 'à l’instant' and relative_age_text(90000) "
        "reads 'il y a 1\\u00a0j' (D-07)",
        _relative_age_text_french_seconds_bucket_reads_a_linstant)

    def _relative_age_text_english_unchanged_under_default_lang():
        try:
            prefs.set_request_prefs(lang="en")
            thirty_s = layout.relative_age_text(30)
            one_day = layout.relative_age_text(90000)
        finally:
            prefs.set_request_prefs(lang="en")
        if thirty_s != "30s ago":
            return False, "expected the unchanged English '30s ago', got %r" % (thirty_s,)
        if one_day != "1d ago":
            return False, "expected the unchanged English '1d ago', got %r" % (one_day,)
        return True, ""
    check(
        "under lang='en' (the default), relative_age_text()'s English output is byte-for-byte "
        "unchanged — '30s ago'/'1d ago' (D-07)",
        _relative_age_text_english_unchanged_under_default_lang)

    def _local_clock_text_french_month_abbreviation():
        try:
            prefs.set_request_prefs(lang="fr")
            september = datetime(2026, 9, 10, 11, 53, tzinfo=timezone.utc)
            now = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
            fr_rendered = layout.local_clock_text(september, now)
            prefs.set_request_prefs(lang="en")
            en_rendered = layout.local_clock_text(september, now)
        finally:
            prefs.set_request_prefs(lang="en")
        if "sept." not in fr_rendered:
            return False, "expected the French month abbreviation 'sept.' in %r" % (fr_rendered,)
        if "Sep" not in en_rendered:
            return False, "expected the English month abbreviation 'Sep' in %r" % (en_rendered,)
        fr_clock = fr_rendered.rsplit(" ", 1)[-1]
        en_clock = en_rendered.rsplit(" ", 1)[-1]
        if fr_clock != en_clock:
            return False, "expected an identical HH:MM in both languages, got %r vs %r" % (
                fr_clock, en_clock)
        return True, ""
    check(
        "local_clock_text() on a September timestamp reads 'sept.' under fr and 'Sep' under en, "
        "with an identical HH:MM in both (D-07)",
        _local_clock_text_french_month_abbreviation)

    def _relative_age_text_signature_unchanged_positionally():
        source = inspect.getsource(layout.relative_age_text)
        if not source.startswith("def relative_age_text(age_seconds"):
            return False, "expected relative_age_text()'s positional signature to stay untouched"
        return True, ""
    check(
        "relative_age_text()'s positional signature (age_seconds first) is untouched — lang is a "
        "trailing keyword only",
        _relative_age_text_signature_unchanged_positionally)

    # ======================================================================
    # Section 1.8b: companion/layout.py's element convention for a
    # relative time (23-03-PLAN.md Task 1, D14/CFG-34). Before this
    # plan the app rendered no <time> element anywhere at all, so every
    # relative age it showed was frozen from page load until something
    # replaced the whole region. These checks pin the WRAPPING: the
    # element's own text must be the ladder's own output, byte for
    # byte, in both languages, because equality is the only thing that
    # proves the ladder was called rather than re-derived beside it.
    #
    # Every check resets prefs' ContextVars in a finally block so no
    # check's language leaks into the next one, exactly as Section 1.8
    # above does.
    # ======================================================================

    # The one shape these checks parse. Written once here rather than
    # inline in four places so a change to the element convention fails
    # in one obvious spot instead of four subtle ones.
    _RELATIVE_ELEMENT_RE = re.compile(
        r'<time datetime="([^"]*)" data-relative>([^<]*)</time>')

    def _relative_time_html_wraps_the_one_ladder_in_both_languages():
        # The four buckets, one representative age each: seconds,
        # minutes, hours, days. 90000s is 1d, the same age Section 1.8's
        # own French check uses, so the two cannot drift apart.
        ages = (30, 180, 7200, 90000)
        base = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        now_iso = _iso(base)
        try:
            for lang in ("en", "fr"):
                prefs.set_request_prefs(lang=lang)
                for age in ages:
                    ts = _iso(base - timedelta(seconds=age))
                    rendered = layout.relative_time_html(ts, now_iso)
                    match = _RELATIVE_ELEMENT_RE.search(rendered)
                    if match is None:
                        return False, (
                            "lang=%s age=%ds: expected a <time datetime=... data-relative> "
                            "element, got %r" % (lang, age, rendered))
                    instant, inner = match.group(1), match.group(2)
                    expected = layout.relative_age_text(age, lang=lang)
                    if inner != expected:
                        return False, (
                            "lang=%s age=%ds: expected the element's own text to EQUAL "
                            "relative_age_text()'s output %r, got %r — a wrapping that changes "
                            "the string is a second ladder, not a wrapping"
                            % (lang, age, expected, inner))
                    if not instant:
                        return False, (
                            "lang=%s age=%ds: expected a non-empty machine-readable instant"
                            % (lang, age))
                    if layout.parse_iso(instant) is None:
                        return False, (
                            "lang=%s age=%ds: expected a parseable instant, got %r"
                            % (lang, age, instant))
                    if layout.age_seconds(instant, now_iso) != age:
                        return False, (
                            "lang=%s age=%ds: expected the element's instant to name the SAME "
                            "moment its text describes, got %r" % (lang, age, instant))
        finally:
            prefs.set_request_prefs(lang="en")
        return True, ""
    check(
        "layout.relative_time_html() renders a <time datetime=... data-relative> element whose "
        "own text EQUALS layout.relative_age_text()'s output for all four buckets in BOTH "
        "languages, and whose instant names the same moment that text describes (23-03, D14)",
        _relative_time_html_wraps_the_one_ladder_in_both_languages)

    def _relative_time_html_degrades_without_an_invented_instant():
        now_iso = "2026-09-13T12:00:00+00:00"
        cases = (
            ("", "a falsy timestamp"),
            (None, "a None timestamp"),
            ("not-a-date", "an unparseable timestamp"),
        )
        for ts, label in cases:
            rendered = layout.relative_time_html(ts, now_iso)
            if "<time" in rendered:
                return False, (
                    "%s must NOT produce a <time> element — an element with an empty or "
                    "invented instant is worse than no element, got %r" % (label, rendered))
        # A mismatched now_ts (naive vs aware) is the one degrade path
        # age_seconds() alone catches; it must not raise either.
        if "<time" in layout.relative_time_html("2026-09-13T11:00:00+00:00", "not-a-date"):
            return False, "an unparseable now_ts must degrade to plain text, not a <time> element"
        # And the degrade path still escapes: an unparseable timestamp
        # is the one value here that can carry hostile bytes.
        hostile = layout.relative_time_html('<script>alert(1)</script>', now_iso)
        if "<script>" in hostile:
            return False, "expected the degrade path to escape its input, got %r" % (hostile,)
        return True, ""
    check(
        "layout.relative_time_html() degrades to escaped plain text — never a raise, never a "
        "<time> element carrying an empty or invented instant — for a falsy, None, unparseable "
        "or mismatched timestamp (23-03)",
        _relative_time_html_degrades_without_an_invented_instant)

    def _future_form_shares_the_past_ladders_own_buckets():
        # One ladder in two directions: the future form must agree with
        # the past form about which bucket a given number of seconds
        # falls in, at and around every boundary. The QUANTITY each
        # direction picks — the number AND its unit — is what proves
        # they share boundaries; asserting only that both are non-empty
        # and differ would pass a future form carrying its own
        # constants, which is the whole defect this check exists for.
        #
        # English determines the relation completely: the past form is
        # "<N><unit> ago" and the future form "in <N><unit>" for every
        # bucket, so one is the other rearranged. French collapses the
        # sub-minute bucket on BOTH sides into a phrase with no number,
        # so there the quantity is compared for the three buckets that
        # have one, and the collapse is asserted for the one that
        # does not.
        boundaries = (0, 1, 59, 60, 61, 3599, 3600, 3601, 86399, 86400, 86401, 900000)
        # A real U+00A0 between the number and the unit (D-09),
        # written as an escape so it stays visible in source.
        quantity_re = re.compile("(\\d+)\\u00a0(\\S+)")
        try:
            for lang in ("en", "fr"):
                prefs.set_request_prefs(lang=lang)
                for seconds in boundaries:
                    past = layout.relative_age_text(seconds, lang=lang)
                    future = layout.relative_future_text(seconds, lang=lang)
                    if not future:
                        return False, (
                            "lang=%s seconds=%d: expected a non-empty future form" % (lang, seconds))
                    if "-" in future:
                        return False, (
                            "lang=%s seconds=%d: a future form must never carry a negative "
                            "number, got %r" % (lang, seconds, future))
                    if future == past:
                        return False, (
                            "lang=%s seconds=%d: the future form must not be the past form — "
                            "both read %r" % (lang, seconds, future))
                    if lang == "en":
                        rearranged = "in " + past[:-len(" ago")]
                        if future != rearranged:
                            return False, (
                                "lang=en seconds=%d: expected the future form to name the SAME "
                                "bucket and the SAME number the past form names (%r), got %r — a "
                                "direction that picks its own boundary is a second ladder"
                                % (seconds, rearranged, future))
                        continue
                    past_quantity = quantity_re.search(past)
                    future_quantity = quantity_re.search(future)
                    if past_quantity is None:
                        # The French sub-minute collapse: neither side
                        # may carry a number there.
                        if future_quantity is not None:
                            return False, (
                                "lang=fr seconds=%d: the past form collapses the sub-minute "
                                "bucket to a phrase with no number (%r) and the future form must "
                                "collapse the same bucket, got %r" % (seconds, past, future))
                        continue
                    if future_quantity is None:
                        return False, (
                            "lang=fr seconds=%d: expected the future form to carry a quantity "
                            "with a real U+00A0 the way the past form %r does, got %r"
                            % (seconds, past, future))
                    if future_quantity.groups() != past_quantity.groups():
                        return False, (
                            "lang=fr seconds=%d: expected the future form to name the SAME number "
                            "and unit the past form names %r, got %r — a direction that picks its "
                            "own boundary is a second ladder"
                            % (seconds, past_quantity.groups(), future_quantity.groups()))
                # The clamp, in the direction that is easy to get wrong:
                # an already-elapsed "future" instant resolves to the
                # zero bucket, never to a negative and never to a
                # past-tense string.
                if layout.relative_future_text(-5, lang=lang) != layout.relative_future_text(
                        0, lang=lang):
                    return False, (
                        "lang=%s: an already-elapsed future instant must resolve to the zero "
                        "bucket" % (lang,))
        finally:
            prefs.set_request_prefs(lang="en")
        return True, ""
    check(
        "layout.relative_future_text() reads the SAME s/m/h/d bucket boundaries the past ladder "
        "reads (asserted at and around all three), is never negative, is never the past form, "
        "and clamps an already-elapsed instant to the zero bucket, in both languages (23-03)",
        _future_form_shares_the_past_ladders_own_buckets)

    def _relative_time_html_reads_a_future_instant_forwards():
        base = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        now_iso = _iso(base)
        try:
            for lang in ("en", "fr"):
                prefs.set_request_prefs(lang=lang)
                # One second either side of `now`: both must render a
                # bounded string, and neither a negative number.
                for delta, direction in ((timedelta(seconds=1), "past"),
                                         (timedelta(seconds=-1), "future")):
                    rendered = layout.relative_time_html(_iso(base - delta), now_iso)
                    match = _RELATIVE_ELEMENT_RE.search(rendered)
                    if match is None:
                        return False, "lang=%s %s: expected a <time> element, got %r" % (
                            lang, direction, rendered)
                    if "-" in match.group(2):
                        return False, "lang=%s %s: expected no negative number, got %r" % (
                            lang, direction, match.group(2))
                ahead = layout.relative_time_html(_iso(base + timedelta(minutes=4)), now_iso)
                ahead_match = _RELATIVE_ELEMENT_RE.search(ahead)
                if ahead_match is None:
                    return False, "lang=%s: expected a <time> element for a future instant" % (lang,)
                if ahead_match.group(2) != layout.relative_future_text(240, lang=lang):
                    return False, (
                        "lang=%s: expected a future instant's element to carry the future form "
                        "%r, got %r" % (
                            lang, layout.relative_future_text(240, lang=lang),
                            ahead_match.group(2)))
        finally:
            prefs.set_request_prefs(lang="en")
        return True, ""
    check(
        "layout.relative_time_html() reads a FUTURE instant through the future form and a past "
        "one through the past form — one function, both directions, bounded and non-negative one "
        "second either side of now, in both languages (23-03, for 23-06's countdown)",
        _relative_time_html_reads_a_future_instant_forwards)

    def _concise_timestamp_htmls_relative_half_is_now_an_element():
        now_iso = "2026-09-12T12:00:00+00:00"
        ts = "2026-09-11T22:30:00+00:00"  # 00:30 Paris the NEXT day (CEST)
        rendered = layout.concise_timestamp_html(ts, now_iso)
        match = _RELATIVE_ELEMENT_RE.search(rendered)
        if match is None:
            return False, (
                "expected concise_timestamp_html()'s relative half to be a <time data-relative> "
                "element, got %r" % (rendered,))
        expected_age = layout.relative_age_text(layout.age_seconds(ts, now_iso))
        if match.group(2) != expected_age:
            return False, (
                "expected the element's text to be the unchanged relative age %r, got %r"
                % (expected_age, match.group(2)))
        # The outer span, its class, its title and the absolute-first
        # ordering are NOT this plan's business and must be untouched.
        if not rendered.startswith('<span class="mono" title="'):
            return False, "expected the outer mono span and its title to be unchanged, got %r" % (
                rendered,)
        if not rendered.endswith("</span>"):
            return False, "expected the outer span to still close the value"
        clock = layout.local_clock_text(layout.parse_iso(ts), layout.parse_iso(now_iso))
        if rendered.index(layout.escape_html(clock)) > rendered.index("<time"):
            return False, "expected absolute-first ordering to be preserved (D-02/06.6 OQ1)"
        if ts in rendered:
            return False, (
                "expected zero occurrences of the RAW ISO string — the element's own instant is "
                "the Europe/Paris form, so D-05/B4's no-raw-ISO rule still holds (22-06 Task 3)")
        return True, ""
    check(
        "layout.concise_timestamp_html()'s parenthesised relative half is now a "
        "<time data-relative> element, its text unchanged, with its outer mono span, its title, "
        "its absolute-first ordering and its no-raw-ISO rule all untouched (23-03, D-09/D-05)",
        _concise_timestamp_htmls_relative_half_is_now_an_element)

    # ======================================================================
    # Section 1.9: companion/pages/health_page.py rendered through t(),
    # with its French catalogue (D-05, 20-03-PLAN.md Task 3). Every
    # check resets prefs' ContextVars in a finally block so no check's
    # language leaks into the next one.
    # ======================================================================

    def _health_page_renders_in_french():
        tmp = _mkstate("health-fr")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(120), 3800)])
            _seed_runway_events(tmp, [{
                "ts": _ago(300), "callsign": "AFR1234", "icao24": "abc123",
                "corroborated": "True"}])
            try:
                prefs.set_request_prefs(lang="fr")
                rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            finally:
                prefs.set_request_prefs(lang="en")
            if "État" not in rendered:
                return False, "expected the French page title (État, via the shared nav catalogue)"
            for french_text in ("Écran", "Serveur et données", "Se connecte normalement"):
                if french_text not in rendered:
                    return False, "expected the French string %r in the rendered page" % (french_text,)
            for english_text in (
                "Screen status and server data quality, in one place.",
                # 29-06-PLAN.md Task 1 (CFG-84): retargeted from the now
                # permanently-dead "Battery trend" literal (no source
                # produces it any more, so its absence proved nothing)
                # onto the ENGLISH form of the real, currently-rendered
                # heading — a check against a string this render would
                # actually produce if the French translation broke.
                _battery_section_heading("en"), "Checking in normally", "Server & data"):
                if english_text in rendered:
                    return False, "expected no English source string %r to leak into the French render" % (
                        english_text,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "health_page.render() under lang='fr' carries the French page title and at least three "
        "other French strings, and none of a short list of English source strings with distinct "
        "French forms (D-05)",
        _health_page_renders_in_french)

    def _health_page_renders_byte_identical_in_english():
        tmp = _mkstate("health-en")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(120), 3800)])
            try:
                prefs.set_request_prefs(lang="en")
                rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            finally:
                prefs.set_request_prefs(lang="en")
            for english_text in (
                health_page.PAGE_PURPOSE_TEXT, health_page.SCREEN_SECTION_HEADING,
                layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING),
                # 29-06-PLAN.md Task 1 (CFG-84): retargeted onto the new
                # window-derived heading text.
                _battery_section_heading(),
                health_page.DEVICE_STATE_TEXT["ok"], "Health"):
                if english_text not in rendered:
                    return False, "expected the unchanged English string %r under lang='en'" % (
                        english_text,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "health_page.render() under lang='en' (the default) is byte-for-byte unchanged for a "
        "seeded state — pinned representative substrings (D-05)",
        _health_page_renders_byte_identical_in_english)

    def _health_page_device_and_pipeline_timestamps_fully_localise_under_french():
        # Polish fix 2: the real production defect was companion/app.py's
        # page_context() calling health_page.safe_health_state() BEFORE
        # prefs.set_request_prefs() — every request's device/pipeline
        # timestamp markup was built under the ContextVar's bare English
        # default regardless of the requester's own language. This check
        # exercises compute_health_state() itself (the function whose
        # OWN readers — layout.local_clock_text()/relative_age_text() —
        # must resolve the CURRENT request's language at call time) with
        # `now` on a different calendar day from every seeded timestamp,
        # so a surviving English month abbreviation or "ago" would be
        # unmistakable rather than accidentally masked by a same-day
        # clock-only render.
        tmp = _mkstate("health-fr-dates")
        try:
            now_iso = "2026-09-12T00:00:00+00:00"
            device_ts = "2026-09-10T23:58:00+00:00"
            _seed_device_health(tmp, [(device_ts, 3800)])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN: device_ts,
                history_db.META_LAST_DETECTION: device_ts})
            try:
                prefs.set_request_prefs(lang="fr")
                state = health_page.compute_health_state(tmp, now=now_iso)
                rendered = health_page.render(dict(_ctx(tmp, now=now_iso), health_state=state))
            finally:
                prefs.set_request_prefs(lang="en")
            fragments = (
                state["device_html"], state["device_detail_html"],
                state["pipeline_html"], rendered)
            for fragment in fragments:
                if "sept." not in fragment:
                    return False, (
                        "expected the French month abbreviation 'sept.' in %r" % (fragment,))
                if " ago" in fragment:
                    return False, "expected no English ' ago' in %r" % (fragment,)
                for english_month in (
                        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                        "Oct", "Nov", "Dec"):
                    if english_month in fragment:
                        return False, (
                            "expected no English month abbreviation %r in %r"
                            % (english_month, fragment))
            if "il y a 1" not in state["device_detail_html"]:
                return False, "expected the French relative-age connector 'il y a 1' in device_detail_html"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "compute_health_state()'s device_html/device_detail_html/pipeline_html fields (and "
        "health_page.render()'s own page) fully localise their timestamps under lang='fr' — no "
        "English month abbreviation or ' ago' survives — proving the request-language ContextVar "
        "is resolved at the correct point relative to when this state is computed (Polish fix 2)",
        _health_page_device_and_pipeline_timestamps_fully_localise_under_french)

    def _health_catalog_every_key_and_value_is_a_nonempty_str():
        bad = [
            (key, value) for key, value in i18n_fr_health.CATALOG.items()
            if not isinstance(key, str) or not key
            or not isinstance(value, str) or not value]
        if bad:
            return False, "expected every CATALOG key/value to be a non-empty str, found: %r" % (bad,)
        return True, ""
    check(
        "every key of companion/i18n_fr/health.py's own CATALOG is a non-empty str mapping to a "
        "non-empty str",
        _health_catalog_every_key_and_value_is_a_nonempty_str)

    # ======================================================================
    # Section 2: companion/pages/airlines_page.py — the illustration
    # gallery (D-13 through D-17, 06.6.4.1 plan 06). The pre-06.6.4.1
    # CFG-04/CFG-08 diagnostics checks that used to live in this section
    # were removed here in plan 06 Task 1 (pulled forward from Task 3,
    # required by this plan's own per-task green-suite verification loop
    # — render() stops emitting that content from Task 1 onward, so the
    # old checks would fail immediately, not just once the underlying
    # symbols are deleted in Task 3). Their Health-side equivalents were
    # added by plan 04 (companion/pages/health_page.py's own Section 1
    # checks above already cover that content there).
    # ======================================================================

    def _airlines_page_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): Airlines' top-level heading goes through
        # layout.page_header() instead of an independent bare <h1> —
        # unchanged by the plan 06 gallery rewrite.
        tmp = _mkstate("a-page-header")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            if '<h1 class="page-title">Airlines</h1>' not in rendered:
                return False, "expected the page_header()-rendered <h1 class=\"page-title\">Airlines</h1>"
            if '<h1 class="text-heading">' in rendered:
                return False, "expected no bare <h1 class=\"text-heading\"> heading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Airlines opens with the shared layout.page_header() component, not a bare <h1>",
        _airlines_page_opens_with_shared_page_header)

    def _gallery_renders_one_card_per_target_airline():
        tmp = _mkstate("a-card-count")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            expected = len(illustrations.target_airline_names())
            got = rendered.count('class="airline-card"')
            if got != expected:
                return False, "expected %d .airline-card elements (one per target airline), got %d" % (expected, got)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery renders exactly one .airline-card per illustrations.target_airline_names() entry "
        "(36 against today's data)",
        _gallery_renders_one_card_per_target_airline)

    def _every_card_image_source_passes_route_membership_test():
        tmp = _mkstate("a-image-membership")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            targets = set(illustrations.target_filenames())
            prefix = airlines_page.ILLUSTRATION_ROUTE_PREFIX
            sources = re.findall(r'src="([^"]+)"', rendered)
            if not sources:
                return False, "expected at least one <img src=...> in the rendered gallery"
            for src in sources:
                if not src.startswith(prefix) or not src.endswith(".png"):
                    return False, "expected every image source to be %s{key}.png, got %r" % (prefix, src)
                filename = src[len(prefix):]
                if filename not in targets:
                    return False, "%r is not a member of illustrations.target_filenames()" % (filename,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every rendered card image source, with the route prefix stripped, is a member of "
        "illustrations.target_filenames() — every rendered URL provably passes the route's own membership test",
        _every_card_image_source_passes_route_membership_test)

    def _card_slice(rendered, airline_name):
        """The one `.airline-card` block for `airline_name`, bounded by
        the next card's opening tag (or end of string) — robust
        regardless of internal nesting, since cards are emitted
        back-to-back with no card-to-card nesting.
        """
        name_index = rendered.index(">%s<" % airline_name)
        card_start = rendered.rindex('<div class="airline-card"', 0, name_index)
        next_start = rendered.find('<div class="airline-card"', card_start + 1)
        return rendered[card_start:] if next_start == -1 else rendered[card_start:next_start]

    def _air_caraibes_card_has_three_upper_cased_chips_including_a350_1000():
        tmp = _mkstate("a-air-caraibes-chips")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            card_slice = _card_slice(rendered, "Air Caraïbes")
            got_chips = re.findall(r'class="airline-card__chip">([^<]+)<', card_slice)
            if got_chips != ["A330", "A350-1000", "ATR72"]:
                return False, "expected exactly [A330, A350-1000, ATR72] chips for Air Caraïbes, got %r" % (got_chips,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Air Caraïbes card renders exactly three chips (A330, A350-1000, ATR72) — the A350-1000 "
        "shape-slug-validation trap is not fallen into",
        _air_caraibes_card_has_three_upper_cased_chips_including_a350_1000)

    def _primary_only_airline_renders_no_chips_container():
        tmp = _mkstate("a-no-variant-airline")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            card_slice = _card_slice(rendered, "Air France")
            if "airline-card__chips" in card_slice:
                return False, "expected Air France's card (no variant shapes) to render no chips container at all"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an airline with no variant entries (Air France) renders no .airline-card__chips container at all",
        _primary_only_airline_renders_no_chips_container)

    def _variant_chip_label_covers_both_domains():
        cases = {
            "a320": "A320", "atr72": "ATR72", "a330": "A330", "b737": "B737",
            "a350-1000": "A350-1000",
            "embraer": "Embraer", "beechcraft1900d": "Beechcraft 1900D",
        }
        for shape, expected in cases.items():
            got = airlines_page.variant_chip_label(shape)
            if got != expected:
                return False, "variant_chip_label(%r) expected %r, got %r" % (shape, expected, got)
        return True, ""
    check(
        "variant_chip_label() upper-cases every alphanumeric type code verbatim and word-cases the Embraer/"
        "Beechcraft manufacturer forms",
        _variant_chip_label_covers_both_domains)

    def _illustration_route_prefix_matches_app_constant():
        if airlines_page.ILLUSTRATION_ROUTE_PREFIX != app.ILLUSTRATION_IMAGE_ROUTE_PREFIX:
            return False, "expected airlines_page.ILLUSTRATION_ROUTE_PREFIX == app.ILLUSTRATION_IMAGE_ROUTE_PREFIX, "\
                "got %r != %r" % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, app.ILLUSTRATION_IMAGE_ROUTE_PREFIX)
        return True, ""
    check(
        "airlines_page.ILLUSTRATION_ROUTE_PREFIX equals app.ILLUSTRATION_IMAGE_ROUTE_PREFIX (the duplicated-not-"
        "imported route-prefix contract)",
        _illustration_route_prefix_matches_app_constant)

    def _every_card_image_carries_matching_intrinsic_dimensions():
        # quick task 260902-req-02 Task 2: every <img> now carries explicit
        # width/height attributes, imported from illustration_normalize's
        # own module constants — never hand-typed — so a browser reserves
        # the right box before the image loads and the grid does not
        # reflow as cards stream in.
        tmp = _mkstate("a-image-dimensions")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            tags = re.findall(r'<img class="airline-card__image"[^>]*>', rendered)
            expected = len(illustrations.target_airline_names())
            if len(tags) != expected:
                return False, "expected %d .airline-card__image tags, got %d" % (expected, len(tags))
            expected_attr = 'width="%d" height="%d"' % (
                illustration_normalize.ILLUSTRATION_TARGET_WIDTH,
                illustration_normalize.ILLUSTRATION_TARGET_HEIGHT)
            for tag in tags:
                if expected_attr not in tag:
                    return False, "expected %r in every card image tag, missing from %r" % (expected_attr, tag)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every rendered card image carries width/height attributes matching "
        "illustration_normalize.ILLUSTRATION_TARGET_WIDTH/HEIGHT exactly",
        _every_card_image_carries_matching_intrinsic_dimensions)

    def _gallery_filter_bar_carries_all_four_contract_markers_exactly_once():
        tmp = _mkstate("a-filter-markers")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            for marker in (
                "data-filter-input", "data-filter-count", "data-filter-clear",
                "data-filter-empty",
            ):
                count = rendered.count(marker)
                if count != 1:
                    return False, "expected exactly one %r marker, got %d" % (marker, count)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery filter bar carries exactly one each of data-filter-input/-count/-clear/-empty",
        _gallery_filter_bar_carries_all_four_contract_markers_exactly_once)

    def _gallery_filter_clear_control_is_a_real_button():
        tmp = _mkstate("a-filter-clear-button")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            if '<button type="button" data-filter-clear>Clear</button>' not in rendered:
                return False, "expected the Clear control to be a <button type=\"button\"> — D-16's read-only " \
                    "constraint no longer applies to this page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery filter bar's Clear control is a real <button type=\"button\"> (D-16 retired)",
        _gallery_filter_clear_control_is_a_real_button)

    def _gallery_filter_label_for_matches_input_id():
        tmp = _mkstate("a-filter-label-for")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            # quick task 260921-p2w Task 1: this literal was
            # "airlines-gallery-filter-input", pinned by
            # .planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md:381
            # (§7.2's `Input id` row). That row is superseded by this
            # quick task's hyphen-removal rename — the archived spec
            # file itself is a historical record and is NOT edited —
            # so the pinned value here is now the hyphen-free form.
            if airlines_page._FILTER_INPUT_ID != "airlines_gallery_filter_input":
                return False, (
                    "expected the hyphen-free input id pinned by quick task 260921-p2w "
                    "Task 1 (superseding 06.6.4.1-UI-SPEC.md §7.2's now-stale hyphenated "
                    "value) — a hyphenated id here would reopen the WebKit/Safari "
                    "contacts-autofill defect that rename fixed, got %r"
                    % (airlines_page._FILTER_INPUT_ID,))
            expected_label = '<label class="text-label" for="%s">' % airlines_page._FILTER_INPUT_ID
            if expected_label not in rendered:
                return False, "expected the filter label's for= to equal the search input's id"
            if ('<input type="search" id="%s" autocomplete="off" spellcheck="false" '
                    'autocapitalize="characters" data-filter-input>' % airlines_page._FILTER_INPUT_ID
                    not in rendered):
                return False, "expected the search input to carry the same id"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery filter label's for attribute equals the search input's id, and that id is the "
        "hyphen-free value quick task 260921-p2w Task 1 pins (superseding the now-stale "
        "06.6.4.1-UI-SPEC.md §7.2 row)",
        _gallery_filter_label_for_matches_input_id)

    def _compagnies_and_health_filter_inputs_carry_safari_autofill_suppression_attributes():
        # Quick task 260921-n2n Task 1: the same Safari contact-autofill
        # fix as History's filter input, proven on the other two rendered
        # sites in one check — Compagnies' gallery filter and Health's
        # unresolved-registry filter (the latter renders only when the
        # registry is non-empty, so it must be seeded here to appear at
        # all).
        attrs = ('autocomplete="off"', 'spellcheck="false"', 'autocapitalize="characters"')
        tmp = _mkstate("ah-filter-autofill")
        try:
            airlines_rendered = airlines_page.render(_ctx(tmp))
            now = _now()
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 3, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            health_rendered = health_page.render(_ctx(tmp, now=_iso(now)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for possessive, rendered in (("Compagnies'", airlines_rendered), ("Health's", health_rendered)):
            for attr in attrs:
                if attr not in rendered:
                    return False, (
                        "expected %s search filter input to carry %r — without it, iOS Safari "
                        "offers contact/phone-number autofill on the field (the defect the "
                        "developer photographed on 2026-09-21)" % (possessive, attr))
        return True, ""
    check(
        "Compagnies' gallery filter input and Health's registry filter input both carry "
        "autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill "
        "suppression)",
        _compagnies_and_health_filter_inputs_carry_safari_autofill_suppression_attributes)

    def _every_search_input_in_the_app_carries_safari_autofill_suppression_attributes():
        # Quick task 260921-n2n Task 4 (FIX 4): Task 1 fixed three
        # hand-copied literals; this makes that fix a standing property
        # of the whole app rather than three named sites, so a FOURTH
        # filter bar added by a later phase cannot reintroduce Safari's
        # contact/phone-number autofill defect with nothing to catch it
        # (this project's own "assert relationships, not endpoints"
        # contract).
        #
        # A SOURCE scan, not a render scan: the literal is a %s-template,
        # and one of the three known sites (health_page.py) renders its
        # filter bar only when the unresolved registry is non-empty.
        #
        # ast-based, not a raw substring search, and docstrings are
        # excluded: history_page.py:947's own _filter_bar_html()
        # docstring DESCRIBES this markup and contains the very substring
        # being matched, with no attributes on it at all — a naive text
        # scan would fail on that docstring forever. This follows
        # test_i18n.py's own methodology (ast.parse() of the source,
        # never an import of the scanned module): walk every
        # ast.Constant string node, skip any node that is a module's,
        # function's or class's own docstring, and search only the
        # surviving literals. Note ast folds adjacent string literals
        # together, so each hit below arrives inside a builder's WHOLE
        # concatenated markup literal, not as a bare standalone tag.
        files = sorted(glob.glob(os.path.join(HERE, "pages", "*.py")))
        files.append(os.path.join(HERE, "app.py"))

        def docstring_constant_ids(tree):
            ids = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    body = getattr(node, "body", None)
                    if (body and isinstance(body[0], ast.Expr)
                            and isinstance(body[0].value, ast.Constant)
                            and isinstance(body[0].value.value, str)):
                        ids.add(id(body[0].value))
            return ids

        required_attrs = ('autocomplete="off"', 'spellcheck="false"', 'autocapitalize="characters"')
        total_hits = 0
        bad = []
        for fp in files:
            with open(fp, "r", encoding="utf-8") as fh:
                src = fh.read()
            tree = ast.parse(src, filename=fp)
            skip_ids = docstring_constant_ids(tree)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                if id(node) in skip_ids:
                    continue
                literal = node.value
                start = 0
                while True:
                    idx = literal.find('<input type="search"', start)
                    if idx == -1:
                        break
                    end = literal.find(">", idx)
                    tag = literal[idx:end + 1] if end != -1 else literal[idx:]
                    total_hits += 1
                    missing = [a for a in required_attrs if a not in tag]
                    if missing:
                        bad.append("%s: %r missing %r" % (os.path.relpath(fp, HERE), tag, missing))
                    start = idx + 1
        if bad:
            return False, (
                "iOS Safari offers contact/phone-number autofill on a bare <input "
                "type=\"search\"> with no name and no autocomplete, as the developer "
                "photographed on 2026-09-21 — found %d occurrence(s) missing at least one "
                "required attribute: %s" % (len(bad), "; ".join(bad)))
        if total_hits < 3:
            return False, (
                "expected at least 3 <input type=\"search\"> occurrences across companion/pages/*.py "
                "and companion/app.py (the floor known at plan time), found only %d — this would "
                "make the check vacuously pass if every filter input were deleted" % total_hits)
        return True, ""
    check(
        "every <input type=\"search\"> this app can render, across companion/pages/*.py and "
        "companion/app.py (an ast-based source scan excluding docstrings, 3 occurrences found "
        "at plan time — history_page.py, airlines_page.py, health_page.py, one builder each), "
        "carries autocomplete=off/spellcheck=false/autocapitalize=characters — a fourth filter "
        "bar added later cannot reintroduce the Safari contact-autofill defect with nothing to "
        "catch it (quick task 260921-n2n Task 4)",
        _every_search_input_in_the_app_carries_safari_autofill_suppression_attributes)

    def _no_filter_input_id_anywhere_in_the_app_contains_a_hyphen():
        # quick task 260921-p2w Task 2: Task 1 fixed three hand-edited
        # values; without a standing check, a future filter bar — or a
        # revert of Task 1 by someone who reads this codebase's
        # hyphen-case id convention (used everywhere else) and
        # "corrects" this back — silently reintroduces the exact
        # WebKit/Safari defect the developer photographed twice: a
        # contacts icon offering the user's OWN Contacts phone numbers
        # on a text input whose name-less id contains a hyphen, a
        # heuristic Safari applies even with autocomplete="off" set.
        #
        # Two parts, one check. Part A is the real gate: every
        # `..._FILTER_INPUT_ID`-suffixed constant's VALUE, read through
        # `ast` — never grepped as raw text, deliberately: Task 1's own
        # provenance comments legitimately NAME the old hyphenated
        # values, and a text-level scan would make those very comments
        # illegal. Part B is a forward guard: a future filter bar that
        # inlines its id as a literal instead of routing it through a
        # constant would evade Part A entirely, so this also scans
        # rendered `<input type="search">` tag literals for a
        # hardcoded, non-template `id="..."`.
        files = sorted(glob.glob(os.path.join(HERE, "pages", "*.py")))
        files.append(os.path.join(HERE, "app.py"))

        def docstring_constant_ids(tree):
            # A local copy of the sibling scan's own helper just above
            # (`_every_search_input_in_the_app_carries_safari_autofill_
            # suppression_attributes`'s `docstring_constant_ids`) —
            # deliberately NOT hoisted or shared, so that check stays
            # unmodified.
            ids = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    body = getattr(node, "body", None)
                    if (body and isinstance(body[0], ast.Expr)
                            and isinstance(body[0].value, ast.Constant)
                            and isinstance(body[0].value.value, str)):
                        ids.add(id(body[0].value))
            return ids

        constant_hits = 0
        constant_bad = []
        tag_bad = []
        id_attr_re = re.compile(r'id="([^"]*)"')
        for fp in files:
            with open(fp, "r", encoding="utf-8") as fh:
                src = fh.read()
            tree = ast.parse(src, filename=fp)
            rel = os.path.relpath(fp, HERE)

            # Part A: every `..._FILTER_INPUT_ID`-suffixed assignment's
            # string constant VALUE.
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                if not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.endswith("_FILTER_INPUT_ID"):
                        constant_hits += 1
                        value = node.value.value
                        if "-" in value:
                            constant_bad.append("%s: %s = %r" % (rel, target.id, value))

            # Part B: a hardcoded (non-template) id on a literal
            # <input type="search"> tag, docstrings excluded (same
            # discipline as the sibling scan above). A tag with no
            # id= attribute, or whose id is the "%s" template form
            # every builder uses today, is skipped — this is a
            # forward guard, not a duplicate of Lot A's attribute
            # check or Part A's constant scan.
            skip_ids = docstring_constant_ids(tree)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                if id(node) in skip_ids:
                    continue
                literal = node.value
                start = 0
                while True:
                    idx = literal.find('<input type="search"', start)
                    if idx == -1:
                        break
                    end = literal.find(">", idx)
                    tag = literal[idx:end + 1] if end != -1 else literal[idx:]
                    start = idx + 1
                    m = id_attr_re.search(tag)
                    if not m:
                        continue
                    tag_id = m.group(1)
                    if tag_id == "%s":
                        continue
                    if "-" in tag_id:
                        tag_bad.append("%s: %r has hardcoded id %r" % (rel, tag, tag_id))

        mechanism = (
            "WebKit/Safari renders a contacts icon inside a text input and offers phone "
            "numbers from the user's OWN Contacts card when the field's name — or, absent "
            "a name, its id — contains a hyphen, and Safari ignores autocomplete=\"off\" "
            "in that case, which is why quick task 260921-n2n's attribute fix alone left "
            "the dropdown showing on the deployed app (the developer's 2026-09-21 report)"
        )
        if constant_bad:
            return False, (
                "%s — a hyphenated *_FILTER_INPUT_ID constant reintroduces exactly that "
                "defect: %s" % (mechanism, "; ".join(constant_bad)))
        if constant_hits < 3:
            return False, (
                "expected at least 3 *_FILTER_INPUT_ID constant assignments across "
                "companion/pages/*.py and companion/app.py (the floor known at plan time — "
                "airlines_page.py, health_page.py, history_page.py), found only %d — this "
                "would let the check pass vacuously if every filter constant were deleted"
                % constant_hits)
        if tag_bad:
            return False, (
                "%s — a hardcoded (non-template) id= on a rendered <input type=\"search\"> "
                "tag reintroduces exactly that defect, bypassing the *_FILTER_INPUT_ID "
                "constant scan entirely: %s" % (mechanism, "; ".join(tag_bad)))
        return True, ""
    check(
        "no *_FILTER_INPUT_ID constant value and no hardcoded <input type=\"search\"> id "
        "literal, across companion/pages/*.py and companion/app.py (enumerated from disk, "
        "3 constants found at plan time, a >= 3 vacuity floor so deleting the constants "
        "cannot make this pass trivially), contains a hyphen — the documented WebKit/Safari "
        "trigger that offers the user's own Contacts phone numbers on a name-less "
        "type=\"search\" field even with autocomplete=\"off\" set (quick task 260921-p2w "
        "Task 2, closing the gap Task 1's three hand-fixed values left open)",
        _no_filter_input_id_anywhere_in_the_app_contains_a_hyphen)

    def _gallery_filter_count_and_empty_body_name_the_real_total():
        tmp = _mkstate("a-filter-count-total")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            total = len(illustrations.target_airline_names())
            count_text = "%d of %d shown" % (total, total)
            if count_text not in rendered:
                return False, "expected the count text %r in the rendered filter bar" % (count_text,)
            empty_body = airlines_page._FILTER_EMPTY_BODY_TEMPLATE % total
            if empty_body not in rendered:
                return False, "expected the empty-state body to name the real card total"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery filter bar's count text and empty-state body both name the real (36) card total",
        _gallery_filter_count_and_empty_body_name_the_real_total)

    def _every_card_carries_distinct_filter_text_and_group():
        tmp = _mkstate("a-filter-per-card")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            for airline_name in illustrations.target_airline_names():
                expected_text = 'data-filter-text="%s"' % airline_name.lower()
                if expected_text not in rendered:
                    return False, "expected %r for airline %r" % (expected_text, airline_name)
            groups = re.findall(r'data-filter-group="(\d+)"', rendered)
            if len(set(groups)) != len(illustrations.target_airline_names()):
                return False, (
                    "expected as many distinct data-filter-group values as target airlines, got %d distinct of %d "
                    "total occurrences" % (len(set(groups)), len(groups)))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every card carries a data-filter-text equal to its own lower-cased airline name, and the set of "
        "data-filter-group values has the same size as the card count",
        _every_card_carries_distinct_filter_text_and_group)

    def _airlines_page_source_has_no_history_db_or_sqlite_import():
        # D-17 non-goal (unchanged half): the gallery shows the full
        # static curated list and performs no detection-history
        # cross-reference — the page module opens no SQLite database of
        # any kind. Phase 13 (13-04-PLAN.md Task 1) deliberately
        # supersedes the OTHER half of this same D-17 sentence ("reads no
        # poll state"): `unresolved_row_for_prefix()` now reads
        # `server.poll_loop.load_poll_state()` as D-11's membership test,
        # so `poll_loop` is no longer forbidden here — see
        # airlines_page.py's own module docstring for the supersession
        # note.
        with open(os.path.join(HERE, "pages", "airlines_page.py")) as fh:
            source = fh.read()
        for needle in ("history_db", "import sqlite3"):
            if needle in source:
                return False, "airlines_page.py must not import %r (D-17 non-goal)" % needle
        if "import server.poll_loop as poll_loop" not in source:
            return False, "expected airlines_page.py to import poll_loop (phase 13 D-11 supersession)"
        return True, ""
    check(
        "companion/pages/airlines_page.py imports no history-database module and no sqlite module (D-17 "
        "non-goal: no detection-history cross-reference), and imports poll_loop exactly the way phase 13's "
        "D-11 membership test deliberately supersedes the OLDER half of that same non-goal",
        _airlines_page_source_has_no_history_db_or_sqlite_import)

    def _airlines_page_no_longer_renders_registry_or_stats_headers():
        # D-13 non-goal: after this plan, exactly one page (Health)
        # renders the unresolved-prefix registry and the resolution-
        # statistics breakdown.
        tmp = _mkstate("a-no-duplicate-registry")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            for header in (
                "Prefix", "First seen", "Last seen", "Example callsign",
                "Source", "Description",
            ):
                if ("<th>%s</th>" % header) in rendered:
                    return False, "the Airlines gallery must not render the migrated %r column header (D-13)" % header
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Airlines gallery contains none of the migrated unresolved-prefix registry or "
        "resolution-statistics table column headers (D-13 non-goal)",
        _airlines_page_no_longer_renders_registry_or_stats_headers)

    def _health_page_still_renders_both_migrated_header_sets():
        # The content moved, it was not lost — Health must still render
        # both header sets the check above confirms Airlines no longer
        # does.
        tmp = _mkstate("h-still-has-headers")
        try:
            registry = {
                "ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            events = [{"ts": _iso(_now()), "hex": "abc123", "route_source": "fresh_hit"}]
            _seed_runway_events(tmp, events)
            rendered = health_page.render(_ctx(tmp))
            for header in (
                "Prefix", "First seen", "Last seen", "Example callsign",
                "Source", "Description",
            ):
                if ("<th>%s</th>" % header) not in rendered:
                    return False, "expected Health to still render the migrated %r column header" % header
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Health page still contains both migrated header sets — the content moved, it was not lost",
        _health_page_still_renders_both_migrated_header_sets)

    def _airlines_page_module_exposes_no_deleted_diagnostics_symbol():
        for name in (
            "unresolved_rows", "coverage_status", "resolution_stats",
            "STATS_UNAVAILABLE_TEXT", "RESOLUTION_WINDOW_DAYS",
            "_registry_row_html", "_registry_table_html", "_registry_section",
            "_resolved_headline_html", "_stats_table_html", "_safe_query",
        ):
            if hasattr(airlines_page, name):
                return False, "airlines_page module must no longer expose the deleted diagnostics symbol %r" % name
        return True, ""
    check(
        "importing companion.pages.airlines_page raises no error, and the module exposes none of the deleted "
        "diagnostics symbols",
        _airlines_page_module_exposes_no_deleted_diagnostics_symbol)

    # ------------------------------------------------------------------
    # quick task 260902-tli: the click-to-enlarge lightbox.
    # ------------------------------------------------------------------

    def _airline_card_zoom_button_attrs_match_expected():
        tmp = _mkstate("a-zoom-button-attrs")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            for airline_name in ("Air Caraïbes", "Air France"):
                card_slice = _card_slice(rendered, airline_name)
                zoom_buttons = re.findall(
                    r'<button type="button" class="airline-card__zoom"[^>]*>', card_slice)
                if len(zoom_buttons) != 1:
                    return False, "expected exactly one .airline-card__zoom button wrapping %r's image, got %d" % (
                        airline_name, len(zoom_buttons))
                button_tag = zoom_buttons[0]

                img_src_match = re.search(r'<img class="airline-card__image" src="([^"]+)"', card_slice)
                if not img_src_match:
                    return False, "expected an .airline-card__image with a src attribute for %r" % (airline_name,)
                img_src = img_src_match.group(1)

                src_attr_match = re.search(r'data-view-panel-src="([^"]+)"', button_tag)
                if not src_attr_match or src_attr_match.group(1) != img_src:
                    return False, (
                        "expected the zoom button's data-view-panel-src to be byte-identical to %r's card image "
                        "src (%r), got %r" % (
                            airline_name, img_src, src_attr_match.group(1) if src_attr_match else None))

                expected_caption = layout.escape_html(airlines_page.CARD_IMAGE_ALT_TEMPLATE % airline_name)
                caption_attr_match = re.search(r'data-view-panel-caption="([^"]+)"', button_tag)
                if not caption_attr_match or caption_attr_match.group(1) != expected_caption:
                    return False, "expected %r's zoom button caption attribute to equal %r, got %r" % (
                        airline_name, expected_caption, caption_attr_match.group(1) if caption_attr_match else None)

                expected_aria = layout.escape_html(airlines_page.ZOOM_LABEL_TEMPLATE % airline_name)
                aria_match = re.search(r'aria-label="([^"]+)"', button_tag)
                if not aria_match or aria_match.group(1) != expected_aria:
                    return False, "expected %r's zoom button aria-label to equal %r, got %r" % (
                        airline_name, expected_aria, aria_match.group(1) if aria_match else None)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every card wraps its image in exactly one .airline-card__zoom button whose data-view-panel-src is "
        "byte-identical to that same card's <img src>, whose data-view-panel-caption equals "
        "CARD_IMAGE_ALT_TEMPLATE %% name, and whose aria-label equals ZOOM_LABEL_TEMPLATE %% name",
        _airline_card_zoom_button_attrs_match_expected)

    def _lightbox_dialog_renders_once_wide_with_own_note_text():
        tmp = _mkstate("a-lightbox-dialog")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            dialog_count = rendered.count('id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID)
            if dialog_count != 1:
                return False, "expected exactly one #%s dialog, got %d" % (
                    airlines_page.LIGHTBOX_DIALOG_ID, dialog_count)
            if '<dialog class="lightbox lightbox--wide"' not in rendered:
                return False, "expected the dialog to carry both the lightbox and lightbox--wide classes"
            for marker in (
                "lightbox__image", "lightbox__caption", "lightbox__note",
                airlines_page._VIEW_PANEL_CLOSE_ATTR,
            ):
                if marker not in rendered:
                    return False, "expected %r in the rendered dialog markup" % (marker,)
            # Went through two rounds of live developer feedback: first
            # the width/height-naming wording was rejected as meaningless
            # implementation detail, then the reworded version was ALSO
            # rejected outright — no note is wanted here at all, unlike
            # History's own (which explains a real possible discrepancy
            # an Airlines illustration never has). LIGHTBOX_NOTE is
            # therefore the empty string; the element must still exist
            # for panel-lookup.js's shared guard clause, so it renders
            # empty rather than absent, and style.css's
            # .lightbox__note:empty rule collapses it to zero space.
            if airlines_page.LIGHTBOX_NOTE != "":
                return False, (
                    "expected airlines_page.LIGHTBOX_NOTE to be the empty string (developer's own call "
                    "that this lightbox needs no note), got %r" % (airlines_page.LIGHTBOX_NOTE,))
            if '<p class="lightbox__note text-body"></p>' not in rendered:
                return False, (
                    "expected the note element to render empty (present only for panel-lookup.js's "
                    "shared guard clause, collapsed to zero space by style.css's .lightbox__note:empty rule)")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the shared lightbox dialog is emitted exactly once, carries both the lightbox and lightbox--wide "
        "classes plus all three lightbox__* elements and the close attribute, and its note element renders "
        "empty (LIGHTBOX_NOTE is deliberately '' after two rounds of live developer feedback rejected both "
        "the original and the reworded copy; the element still exists for panel-lookup.js's shared guard "
        "clause) — quick task 260902-tli",
        _lightbox_dialog_renders_once_wide_with_own_note_text)

    def _airline_card_zoom_stylesheet_contract():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        # This file is comment-heavy — matching raw text would read prose
        # as declarations, so comment spans are stripped first, non-
        # greedily (a greedy match would eat past the first real `*/`
        # into unrelated later comments).
        stripped = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)

        zoom_rule_bodies = re.findall(r"\.airline-card__zoom\s*\{([^}]*)\}", stripped)
        if not zoom_rule_bodies:
            return False, "expected a .airline-card__zoom rule in style.css"
        base_body = zoom_rule_bodies[0]
        for expected in ("height: auto", "padding: 0", "border: none", "background: none", "cursor: zoom-in"):
            if expected not in base_body:
                return False, "expected %r inside the base .airline-card__zoom rule, got %r" % (expected, base_body)

        # An earlier version of this feature disabled the trigger's
        # pointer path on narrow portrait viewports via a
        # `pointer-events: none` declaration inside an
        # `@media (max-width: 959px) and (orientation: portrait)` block
        # — a misreading of the developer's own request (they meant the
        # ENLARGED VIEW should present the wide illustration in a
        # landscape-style layout, not that the click itself should be
        # gated behind device orientation). Removed on the same live
        # developer test that first exercised it. This check now pins
        # the removal itself: the trigger must declare no pointer-events
        # property anywhere, and that media block must not exist at all,
        # so the wrong gate cannot silently return.
        if any("pointer-events" in body for body in zoom_rule_bodies):
            return False, (
                "expected no .airline-card__zoom rule to declare pointer-events at all — the click "
                "must work unconditionally at every viewport size and orientation")
        media_marker = "@media (max-width: 959px) and (orientation: portrait)"
        if media_marker in stripped:
            return False, "expected the retired orientation gate (%r) to be fully removed" % (media_marker,)
        return True, ""
    check(
        ".airline-card__zoom neutralizes the base button rule's height/padding/border/background and declares "
        "the zoom cursor, and declares no pointer-events property anywhere — the retired orientation gate "
        "(a misreading of the developer's original request, corrected on the same live test) must not "
        "silently return",
        _airline_card_zoom_stylesheet_contract)

    def _06_6_4_1_1_03_mobile_button_override_block_and_source_order():
        # 06.6.4.1.1-03 Task 2 (D-18b): pins the mobile-only button
        # override's existence, its declared values, that the base
        # button rule's own desktop values are untouched, and — the half
        # that actually protects the behaviour — that the mobile block
        # comes AFTER the base `button` rule in source order, since
        # neither rule adds specificity beyond the bare `button` selector
        # and source order alone decides the winner.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        marker = "@media (max-width: 959.98px) {"
        if marker not in css_source:
            return False, "expected style.css to declare %r" % (marker,)

        # 22-11-PLAN.md Task 2, Rule 1 auto-fix: this check used to say
        # "the file's @media (max-width: 959.98px) block" and read
        # `css_source.index(marker)` — the FIRST such block. That premise
        # was already false when it was written (the file carries several
        # sub-960px blocks) and it survived only because the mobile
        # button override happened to be the earliest one. Adding ANY
        # sub-960px rule earlier in the file — this plan's own
        # `.illustration-grid` two-column template, X7 — silently
        # retargeted the assertion onto an unrelated block. Retargeted in
        # place and NARROWED, never loosened: every sub-960px block is
        # scanned, EXACTLY ONE must declare the bare button override
        # (two would be a real ambiguity this check should catch), and
        # that block — not merely the first — must come after the base
        # rule in source order.
        mobile_button_pattern = r"button\s*\{\s*height:\s*36px;\s*font-size:\s*14px;\s*\}"
        declaring_blocks = []
        search_at = 0
        while True:
            media_at = css_source.find(marker, search_at)
            if media_at < 0:
                break
            search_at = media_at + len(marker)
            media_close = css_source.index("\n}\n", media_at)
            if re.search(mobile_button_pattern, css_source[media_at:media_close]):
                declaring_blocks.append(media_at)
        if len(declaring_blocks) != 1:
            return False, (
                "expected exactly one %r block to declare a bare `button { height: 36px; "
                "font-size: 14px; }` rule, found %d" % (marker, len(declaring_blocks)))
        media_at = declaring_blocks[0]

        base_button_at = css_source.index("button {")
        if base_button_at > media_at:
            return False, (
                "expected the base `button {` rule to come BEFORE the "
                "%r block that overrides it, not after it" % (marker,))
        base_body = css_source[base_button_at:css_source.index("}", base_button_at)]
        if "height: 30px" not in base_body:
            return False, "expected the base button rule to still declare height: 30px"
        if "font-size: 13px" not in base_body:
            return False, "expected the base button rule to still declare font-size: 13px"
        return True, ""
    check(
        "the mobile-only button override exists as the file's @media (max-width: 959.98px) block, "
        "declares a bare `button` rule with height: 36px and font-size: 14px, sits AFTER the base "
        "`button` rule in source order (the mechanism that lets it win at equal specificity), and "
        "the base rule's own desktop values (height: 30px, font-size: 13px) are untouched "
        "(06.6.4.1.1-03 D-18b)",
        _06_6_4_1_1_03_mobile_button_override_block_and_source_order)

    def _lightbox_wide_max_width_matches_illustration_target_width():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        stripped = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)
        wide_match = re.search(r"\.lightbox--wide\s*\{([^}]*)\}", stripped)
        if not wide_match:
            return False, "expected a .lightbox--wide rule in style.css"
        width_match = re.search(r"max-width:\s*(\d+)px", wide_match.group(1))
        if not width_match:
            return False, "expected a max-width: Npx declaration inside .lightbox--wide"
        got_width = int(width_match.group(1))
        if got_width != illustration_normalize.ILLUSTRATION_TARGET_WIDTH:
            return False, (
                "expected .lightbox--wide's max-width to equal illustration_normalize.ILLUSTRATION_TARGET_WIDTH "
                "(%d), got %d" % (illustration_normalize.ILLUSTRATION_TARGET_WIDTH, got_width))
        return True, ""
    check(
        ".lightbox--wide's max-width equals illustration_normalize.ILLUSTRATION_TARGET_WIDTH — a future change "
        "to the normalized frame size cannot silently leave the dialog capped at a stale width",
        _lightbox_wide_max_width_matches_illustration_target_width)

    # ------------------------------------------------------------------
    # The illustration-replace control, relocated from a per-card
    # disclosure into the shared lightbox by quick task 260903-btu. The
    # six checks below were all retargeted from the per-card shape
    # quick task 260902-v26 originally shipped onto the new one-per-page
    # lightbox contract.
    # ------------------------------------------------------------------

    def _replace_form_action_matches_trigger_attribute_membership():
        # retargeted from the per-card disclosure (quick task 260902-v26)
        # onto the lightbox contract (quick task 260903-btu): the
        # membership guarantee is unchanged, but has moved from N form
        # `action` attributes to N trigger `data-view-panel-replace-
        # action` attributes, since the form itself is now emitted
        # exactly once.
        tmp = _mkstate("a-replace-action-membership")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
            # quick task 260903-df3: LIGHTBOX_REPLACE_ZONE_CLASS
            # ("lightbox__replace-zone") shares a prefix with
            # LIGHTBOX_REPLACE_FORM_CLASS ("lightbox__replace"), but the
            # literal below carries a trailing quote after %s
            # ('<form class="%s"') — the zone is a <div>, never a
            # <form>, so this count stays unambiguous.
            form_count = rendered.count('<form class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
            if form_count != 1:
                return False, "expected exactly one lightbox replace form, got %d" % form_count
            targets = set(illustrations.target_filenames())
            prefix = airlines_page.ILLUSTRATION_ROUTE_PREFIX
            actions = re.findall(r'data-view-panel-replace-action="([^"]+)"', rendered)
            # 29-01-PLAN.md (CFG-81), retargeted in place and NARROWED
            # BACK: the per-card "Replace picture" control (22-11-PLAN.md
            # Task 2, X7) that used to double this total is deleted
            # outright — the affordance moved into the dialog, which
            # carries no data-view-panel-replace-action attribute of its
            # own (it is the zoom trigger's target, not a second
            # trigger). So each card is back to carrying exactly one
            # replace-action trigger, the zoom trigger, and there is no
            # edit-mode/plain distinction left to test separately.
            per_airline = 1
            expected = per_airline * len(illustrations.target_airline_names())
            if len(actions) != expected:
                return False, (
                    "expected %d replace-action triggers (%d per target airline: the zoom "
                    "trigger — the per-card Replace control is deleted, CFG-81), got %d"
                    % (expected, per_airline, len(actions)))
            for action in set(actions):
                if actions.count(action) != per_airline:
                    return False, (
                        "expected each airline's replace action to appear exactly %d time(s), %r "
                        "appeared %d" % (per_airline, action, actions.count(action)))
            for action in actions:
                if not action.startswith(prefix) or not action.endswith(".png"):
                    return False, "expected every replace-action trigger to be %s{key}.png, got %r" % (
                        prefix, action)
                filename = action[len(prefix):]
                if filename not in targets:
                    return False, "%r is not a member of illustrations.target_filenames()" % (filename,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "exactly one lightbox replace form is rendered, and every card's zoom trigger carries a "
        "data-view-panel-replace-action attribute (one per illustrations.target_airline_names() entry) whose "
        "value, with the route prefix stripped, is a member of illustrations.target_filenames() — mirroring "
        "the existing image-source membership check",
        _replace_form_action_matches_trigger_attribute_membership)

    def _replace_form_declares_post_multipart_enctype_and_present_action():
        # retargeted from the per-card disclosure onto the lightbox
        # contract: now singular, since the form itself is singular.
        tmp = _mkstate("a-replace-method-enctype")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
            forms = re.findall(r'<form class="%s"[^>]*>' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, rendered)
            if len(forms) != 1:
                return False, "expected exactly one replace form, got %d" % len(forms)
            form_tag = forms[0]
            if 'method="post"' not in form_tag:
                return False, "expected method=\"post\" in %r" % (form_tag,)
            if 'enctype="multipart/form-data"' not in form_tag:
                return False, (
                    "expected enctype=\"multipart/form-data\" in %r — a form missing the enctype would "
                    "silently send the file as a filename string, a real failure mode" % (form_tag,))
            if 'action=""' not in form_tag:
                return False, (
                    "expected a literally present action=\"\" placeholder in %r — a missing (as opposed to "
                    "empty) action attribute would leave panel-lookup.js writing an attribute that was never "
                    "rendered" % (form_tag,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the single lightbox replace form declares method=\"post\", enctype=\"multipart/form-data\" — a "
        "missing enctype would silently send the file as a filename string, a real failure mode, not a "
        "formality — and a literally present action=\"\" placeholder for panel-lookup.js to overwrite",
        _replace_form_declares_post_multipart_enctype_and_present_action)

    def _replace_form_file_input_id_is_unique_and_labelled():
        # retargeted from the per-card disclosure onto the lightbox
        # contract: exactly one file input on the whole page carries the
        # static REPLACE_INPUT_ID. quick task 260903-df3 extends this
        # further: the label and the file input must both live *inside*
        # the framed zone wrapper, so a future change that lifts either
        # back out of the frame fails loudly here rather than silently.
        #
        # Phase 14 (14-02-PLAN.md Task 3) retargeted the file-input-
        # count portion of this check in place (no EXPECTED_CHECK_COUNT
        # change — same check, re-scoped): the shared dialog now also
        # renders its own resolve-upload form's file input
        # (MANUAL_UPLOAD_INPUT_ID + "-dialog"), so "exactly one file
        # input on the whole page" is no longer this check's own
        # subject — REPLACE_INPUT_ID's own uniqueness among file-input
        # ids is.
        tmp = _mkstate("a-replace-input-ids")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
            input_ids = re.findall(r'<input type="file" id="([^"]+)"', rendered)
            replace_ids = [i for i in input_ids if i == airlines_page.REPLACE_INPUT_ID]
            if len(replace_ids) != 1:
                return False, (
                    "expected exactly one file input carrying REPLACE_INPUT_ID, got %d (all file "
                    "input ids: %r)" % (len(replace_ids), input_ids))
            label_fors = set(re.findall(r'<label for="([^"]+)">', rendered))
            if airlines_page.REPLACE_INPUT_ID not in label_fors:
                return False, (
                    "expected a <label for=\"%s\"> matching the file input's id" % (
                        airlines_page.REPLACE_INPUT_ID,))
            zone_match = re.search(
                r'<div class="%s">.*?</div>' % re.escape(airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS),
                rendered, re.DOTALL)
            if not zone_match:
                return False, "expected to find the framed zone's own markup"
            zone_html = zone_match.group(0)
            if ('<label for="%s"' % airlines_page.REPLACE_INPUT_ID) not in zone_html:
                return False, "expected the <label> to live inside the framed zone wrapper"
            if '<input type="file"' not in zone_html:
                return False, "expected the file <input> to live inside the framed zone wrapper"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the whole rendered page carries exactly one <input type=\"file\"> whose id equals "
        "airlines_page.REPLACE_INPUT_ID and is the target of a label's for attribute, and both the label and "
        "the file input live inside the framed zone wrapper (quick task 260903-df3) — the accessibility "
        "contract the move from per-card to shared must not lose",
        _replace_form_file_input_id_is_unique_and_labelled)

    def _cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override():
        # extended in place (quick task 260903-btu): everything this
        # check already asserted still holds; it now additionally pins
        # that the replace-action trigger attribute stays UN-busted even
        # when the card's own <img src>/data-view-panel-src are busted —
        # the busted/un-busted split is deliberate and reads like a bug
        # to anyone who has not read the reasoning in
        # _airline_card_html()'s own comment.
        rendered_no_state = airlines_page.render(_ctx(None))
        if "?v=" in rendered_no_state:
            return False, "expected no cache-busting query string anywhere when ctx carries no effective state_dir"

        tmp = _mkstate("a-cache-buster")
        try:
            key = illustrations.normalise_airline_key("Air France")
            override_dir = os.path.join(tmp, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)
            os.makedirs(override_dir)
            override_path = os.path.join(override_dir, key + ".png")
            with open(override_path, "wb") as fh:
                fh.write(b"not a real png - only this file's own mtime matters to this check")
            mtime = int(os.stat(override_path).st_mtime)

            rendered = airlines_page.render(_ctx(tmp))
            expected_busted_url = "%s%s.png?v=%d" % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key, mtime)
            expected_unbusted_url = "%s%s.png" % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key)
            img_srcs = re.findall(r'<img class="airline-card__image" src="([^"]+)"', rendered)
            zoom_srcs = re.findall(r'data-view-panel-src="([^"]+)"', rendered)
            replace_actions = re.findall(r'data-view-panel-replace-action="([^"]+)"', rendered)
            if img_srcs.count(expected_busted_url) != 1:
                return False, "expected exactly one <img src> equal to %r, got %r" % (
                    expected_busted_url, img_srcs)
            if zoom_srcs.count(expected_busted_url) != 1:
                return False, (
                    "expected exactly one data-view-panel-src equal to %r, got %r" % (
                        expected_busted_url, zoom_srcs))
            if replace_actions.count(expected_unbusted_url) != 1:
                return False, (
                    "expected exactly one data-view-panel-replace-action equal to the UN-busted %r, got %r"
                    % (expected_unbusted_url, replace_actions))
            for src in img_srcs:
                if src != expected_busted_url and "?v=" in src:
                    return False, "expected only Air France's <img src> to carry a cache buster, found one on %r" % (src,)
            for src in zoom_srcs:
                if src != expected_busted_url and "?v=" in src:
                    return False, (
                        "expected only Air France's data-view-panel-src to carry a cache buster, found one on "
                        "%r" % (src,))
            for action in replace_actions:
                if "?v=" in action:
                    return False, (
                        "expected no data-view-panel-replace-action value anywhere to carry a cache buster, "
                        "found one on %r" % (action,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "render() with no effective state_dir produces no cache-busting query string anywhere; with a "
        "state_dir whose override directory holds Air France's override file, exactly one URL is busted, "
        "keyed on that file's own mtime, identically in both the <img src> and the zoom trigger's "
        "data-view-panel-src, every other card's URL stays unbusted, and Air France's own "
        "data-view-panel-replace-action stays the UN-busted URL while no replace-action value anywhere "
        "carries a cache buster",
        _cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override)

    def _replace_control_escapes_hostile_airline_name():
        # A hostile airline name can only reach this page through
        # illustrations.target_variants_by_airline() itself (a curated
        # in-repo list, never user input) - monkeypatched for the
        # duration of this check only, mirroring the monkeypatch-and-
        # restore technique companion/test_config_page.py's own THEME_IDS
        # checks already use.
        original_target_variants_by_airline = illustrations.target_variants_by_airline
        hostile_name = '<script>alert(1)</script>"'
        illustrations.target_variants_by_airline = lambda: [(hostile_name, [])]
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render({})
        finally:
            illustrations.target_variants_by_airline = original_target_variants_by_airline
        if hostile_name in rendered:
            return False, "the raw hostile airline name survived unescaped somewhere in the rendered page"
        if "<script>" in rendered:
            return False, "a raw '<script>' fragment from the hostile name survived into the rendered page"
        # retargeted (quick task 260903-btu): the two now-deleted
        # %s-airline-name templates are replaced by REPLACE_LABEL_TEXT,
        # which no longer interpolates a name at all — the form is
        # airline-agnostic now, so the hostile name must not appear
        # inside its markup at all. quick task 260903-df3 adds a third
        # non-interpolating constant (REPLACE_HINT_TEXT) to this same
        # airline-agnostic form, so the "no trace of the hostile name"
        # claim below now covers three constants, not two.
        escaped_label = layout.escape_html(airlines_page.REPLACE_LABEL_TEXT)
        if escaped_label not in rendered:
            return False, "expected %r in the rendered page" % (escaped_label,)
        escaped_hint = layout.escape_html(airlines_page.REPLACE_HINT_TEXT)
        if escaped_hint not in rendered:
            return False, "expected %r in the rendered page" % (escaped_hint,)
        form_match = re.search(
            r'<form class="%s".*?</form>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS),
            rendered, re.DOTALL)
        if not form_match:
            return False, "expected to find the lightbox replace form's own markup"
        if "script" in form_match.group(0).lower():
            return False, "expected no trace of the hostile name inside the airline-agnostic replace form"
        # The one genuinely new interpolation point this task creates:
        # the hostile card's own data-view-panel-replace-action value.
        hostile_action_match = re.search(r'data-view-panel-replace-action="([^"]*)"', rendered)
        if not hostile_action_match:
            return False, "expected a data-view-panel-replace-action attribute on the hostile card"
        hostile_action = hostile_action_match.group(1)
        if "<" in hostile_action or '"' in hostile_action:
            return False, (
                "expected no raw '<' or '\"' in the hostile card's data-view-panel-replace-action value, "
                "got %r" % (hostile_action,))
        return True, ""
    check(
        "a hostile airline name reaching the rendered page is escaped, never interpolated raw, including in "
        "its own data-view-panel-replace-action attribute; the now-airline-agnostic replace form's own markup "
        "(REPLACE_LABEL_TEXT and REPLACE_HINT_TEXT, quick task 260903-df3) carries no trace of the hostile "
        "name at all (extends T-06.6.4.1-05's existing discipline)",
        _replace_control_escapes_hostile_airline_name)

    def _replace_form_contains_no_revert_or_reset_control():
        # renamed and retargeted (quick task 260903-btu) from
        # _replace_disclosure_contains_no_revert_or_reset_control: the
        # revert-shaped-word scan is now scoped to the single lightbox
        # form's own markup (sliced from its opening tag to its closing
        # tag) rather than one disclosure per card, and the membership
        # half now checks the surviving copy constants
        # (REPLACE_LABEL_TEXT/REPLACE_BUTTON_TEXT), not the two deleted
        # templates. Deliberately scoped rather than a bare negative grep
        # over the whole document, which would be brittle against
        # unrelated future copy elsewhere on the page (D-04). quick task
        # 260903-df3 adds REPLACE_HINT_TEXT to the membership tuple below
        # — otherwise this scan would silently skip that task's new copy
        # constant.
        tmp = _mkstate("a-no-revert-control")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        form_match = re.search(
            r'<form class="%s".*?</form>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS),
            rendered, re.DOTALL)
        if not form_match:
            return False, "expected to find the lightbox replace form's own markup"
        form_html = form_match.group(0)
        revert_shaped_words = ("revert", "reset", "restore", "undo", "original")
        lowered = form_html.lower()
        for word in revert_shaped_words:
            if word in lowered:
                return False, (
                    "expected no revert-shaped word %r inside the replace form (D-04), found in %r"
                    % (word, form_html))
        for constant_text in (
                airlines_page.REPLACE_LABEL_TEXT, airlines_page.REPLACE_BUTTON_TEXT,
                airlines_page.REPLACE_HINT_TEXT):
            lowered_constant = constant_text.lower()
            for word in revert_shaped_words:
                if word in lowered_constant:
                    return False, "expected %r to not contain revert-shaped word %r" % (constant_text, word)
        return True, ""
    check(
        "the lightbox replace form's own markup offers no restoring or resetting of the original image (D-04, "
        "explicitly out of scope) - checked both within the form's own markup and as a membership test over "
        "this feature's surviving copy constants (REPLACE_LABEL_TEXT/REPLACE_BUTTON_TEXT/REPLACE_HINT_TEXT)",
        _replace_form_contains_no_revert_or_reset_control)

    def _replace_control_retired_from_every_surface():
        # new (quick task 260903-btu): the per-card disclosure this task
        # removed must leave no trace anywhere — not in a rendered page,
        # not in the stylesheet, not in the module's own attribute
        # surface. The searched token is built by concatenating two
        # fragments at runtime, not written as one literal, so this
        # check's own source cannot satisfy a future whole-repo grep for
        # the retired name.
        retired_token = "airline-card__" + "replace"
        tmp = _mkstate("a-retired-control-gone")
        try:
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if retired_token in rendered:
            return False, "expected the retired per-card class token to be absent from render()'s output"
        style_css_path = os.path.join(HERE, "static", "style.css")
        with open(style_css_path) as fh:
            style_css_source = fh.read()
        if retired_token in style_css_source:
            return False, "expected the retired per-card class token to be absent from companion/static/style.css"
        for retired_attr in ("_replace_control_html", "REPLACE_SUMMARY_TEMPLATE", "REPLACE_LABEL_TEMPLATE"):
            if hasattr(airlines_page, retired_attr):
                return False, "expected airlines_page to expose no %r attribute" % (retired_attr,)
        return True, ""
    check(
        "the retired per-card replace disclosure left no dead markup (a real render() call), no dead "
        "stylesheet rule (companion/static/style.css read from disk), and no dead module surface "
        "(_replace_control_html/REPLACE_SUMMARY_TEMPLATE/REPLACE_LABEL_TEMPLATE) behind",
        _replace_control_retired_from_every_surface)

    def _replace_zone_icon_comes_from_the_shared_sprite():
        # new (quick task 260903-df3): proves the framed zone's upload
        # glyph came from layout.ICON_DEFS_HTML via layout.icon_html(),
        # not from hand-written markup in this page module. The
        # "concatenated fragments, not one literal" technique below is
        # the same one _replace_control_retired_from_every_surface()
        # above already uses for its own retired token, so this check's
        # own source cannot satisfy the scan it performs.
        if "icon-upload" not in layout.ICON_IDS:
            return False, "expected 'icon-upload' to be a member of layout.ICON_IDS"
        tmp = _mkstate("a-replace-zone-icon-sprite")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # Phase 14 (14-02-PLAN.md Task 3) retargeted this count in place
        # (no EXPECTED_CHECK_COUNT change — same check, re-scoped): the
        # shared dialog now also renders its own resolve-upload form
        # (_resolve_upload_form_html(), id_suffix="-dialog"), which
        # reuses the identical icon-upload glyph via the same
        # layout.icon_html() call, so two occurrences are now expected,
        # not one.
        use_tag = "<use href=" + '"#icon-upload"'
        if rendered.count(use_tag) != 2:
            return False, "expected exactly two %r in the rendered page, got %d" % (
                use_tag, rendered.count(use_tag))
        source_path = os.path.join(HERE, "pages", "airlines_page.py")
        with open(source_path) as fh:
            page_source = fh.read()
        hand_rolled_token = "<" + "use href=" + '"#icon-upload"'
        if hand_rolled_token in page_source:
            return False, (
                "expected companion/pages/airlines_page.py to contain no hand-written glyph-element token "
                "built as one literal — the glyph must come from layout.icon_html() only")
        icon_svg_match = re.search(
            r'<svg[^>]*class="[^"]*%s[^"]*"[^>]*>' % re.escape(airlines_page.REPLACE_ICON_CLASS), rendered)
        if not icon_svg_match:
            return False, "expected REPLACE_ICON_CLASS to appear in the rendered icon's class attribute"
        return True, ""
    check(
        "the framed zone's upload glyph comes from layout.ICON_DEFS_HTML via layout.icon_html() — 'icon-upload' "
        "is a member of ICON_IDS, the rendered page carries exactly one matching <use> reference, "
        "companion/pages/airlines_page.py's own source contains no hand-written glyph-element token, and "
        "REPLACE_ICON_CLASS appears in the rendered icon's class attribute",
        _replace_zone_icon_comes_from_the_shared_sprite)

    def _replace_zone_markup_and_styling_contract():
        # new (quick task 260903-df3): the zone's own shape (exactly one
        # instance, nested inside the single replace form, its five
        # children in the specified order) and its four-file class
        # agreement (the page module's class constants actually appear
        # in the stylesheet, plus the first ::file-selector-button rule).
        tmp = _mkstate("a-replace-zone-contract")
        try:
            # 29-01-PLAN.md (CFG-81): the dialog's replace/delete forms are
            # unconditional now - no edit_mode needed.
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        zone_open_tag = '<div class="%s">' % airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS
        if rendered.count(zone_open_tag) != 1:
            return False, "expected exactly one %r, got %d" % (zone_open_tag, rendered.count(zone_open_tag))
        form_match = re.search(
            r'<form class="%s"[^>]*>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS), rendered)
        if not form_match:
            return False, "expected to find the single lightbox replace form's opening tag"
        if rendered.index(zone_open_tag) <= form_match.start():
            return False, "expected the zone <div> to be nested inside (after) the form's own opening tag"
        zone_match = re.search(
            r'<div class="%s">.*?</div>' % re.escape(airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS),
            rendered, re.DOTALL)
        if not zone_match:
            return False, "expected to find the framed zone's own markup"
        zone_html = zone_match.group(0)
        try:
            positions = [
                zone_html.index("#icon-upload"),
                zone_html.index('<label for='),
                zone_html.index(airlines_page.REPLACE_HINT_CLASS),
                zone_html.index('<input type="file"'),
                zone_html.index('<button type="submit"'),
            ]
        except ValueError as exc:
            return False, "expected all five zone children to be present: %s" % (exc,)
        if positions != sorted(positions):
            return False, (
                "expected the zone's five children (icon, label, hint, input, button) in that order, "
                "got positions %r" % (positions,))
        hint_p_match = re.search(
            r'<p class="%s">([^<]*)</p>' % re.escape(airlines_page.REPLACE_HINT_CLASS), zone_html)
        if not hint_p_match:
            return False, "expected a <p class=\"%s\"> inside the zone" % (airlines_page.REPLACE_HINT_CLASS,)
        if hint_p_match.group(1) != airlines_page.REPLACE_HINT_TEXT:
            return False, "expected the hint element's text to equal REPLACE_HINT_TEXT, got %r" % (
                hint_p_match.group(1),)
        style_css_path = os.path.join(HERE, "static", "style.css")
        with open(style_css_path) as fh:
            style_css_source = fh.read()
        for class_name in (
                airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS, airlines_page.REPLACE_HINT_CLASS,
                airlines_page.REPLACE_ICON_CLASS):
            if class_name not in style_css_source:
                return False, "expected %r to appear in companion/static/style.css" % (class_name,)
        if "::file-selector-button" not in style_css_source:
            return False, "expected a '::file-selector-button' rule in companion/static/style.css"
        return True, ""
    check(
        "exactly one .lightbox__replace-zone <div> is rendered, nested inside the single lightbox replace "
        "form; within it, the icon, label, hint, file input and Upload button appear in that order; the hint "
        "element's text equals REPLACE_HINT_TEXT; and companion/static/style.css (read from disk) contains "
        "LIGHTBOX_REPLACE_ZONE_CLASS, REPLACE_HINT_CLASS, REPLACE_ICON_CLASS and a '::file-selector-button' rule",
        _replace_zone_markup_and_styling_contract)

    # ======================================================================
    # 25-07-PLAN.md Task 1 (CFG-51/D19): THE DROP ZONE, OVER TWO UPLOAD
    # FORMS THAT DID NOT CHANGE.
    #
    # D19's whole design is that the gesture changes and the parser does
    # not: a drop assigns the File to the form's own
    # `<input type="file">` through a DataTransfer, so the bytes travel
    # the identical path a picked file travels. The three checks below
    # are what makes "identical" a measurement rather than a claim —
    # the first pins the native controls byte-for-byte, the second pins
    # that nothing the script needs renders where the script cannot run,
    # and the third pins that the preview's reserved box is
    # `illustration_normalize.py`'s own frame and not a second number.
    # ======================================================================

    def _upload_forms_native_controls_are_unchanged_by_the_drop_zone():
        # The three renderings the two shared builders produce: the
        # no-JS fallback upload form (a real action, no id suffix), the
        # dialog's copy of the same form (the `action=""` placeholder
        # panel-lookup.js overwrites, id suffix "-dialog") and the
        # single lightbox replace form.
        #
        # Every literal below is the PRE-25-07 text, retyped here on
        # purpose: that is what makes this a byte-identity pin rather
        # than a restatement of whatever the builder currently emits. A
        # future edit that "tidies" an attribute order, drops `required`
        # or renames the field fails here.
        renderings = (
            ("the no-JS fallback upload form",
             airlines_page._resolve_upload_form_html("/illustration/demo.png", ""),
             airlines_page.MANUAL_UPLOAD_INPUT_ID,
             airlines_page.MANUAL_UPLOAD_FORM_ID,
             'action="/illustration/demo.png"'),
            ("the dialog's copy of the upload form",
             airlines_page._resolve_upload_form_html("", "-dialog"),
             airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog",
             airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog",
             'action=""'),
            ("the lightbox replace form",
             airlines_page._lightbox_replace_form_html(),
             airlines_page.REPLACE_INPUT_ID,
             airlines_page.REPLACE_FORM_ID,
             'action=""'),
        )
        hint_html = '<p class="%s">%s</p>' % (
            airlines_page.REPLACE_HINT_CLASS,
            airlines_page.i18n.t(airlines_page.REPLACE_HINT_TEXT))
        for label, markup, input_id, form_id, action_attr in renderings:
            expected_input = (
                '<input type="file" id="%s" name="image" accept="image/png" required>' % input_id)
            if markup.count(expected_input) != 1:
                return False, (
                    "%s: expected exactly one %r — the drop zone changes the affordance, never "
                    "the control the form posts" % (label, expected_input))
            if markup.count('<button type="submit">') != 1:
                return False, (
                    "%s: expected exactly one bare <button type=\"submit\"> — no progress bar, no "
                    "second submitter (25-07 builds neither)" % (label,))
            if markup.count(hint_html) != 1:
                return False, "%s: expected the pre-25-07 hint paragraph %r verbatim" % (label, hint_html)
            if markup.count("<form") != 1:
                return False, (
                    "%s: expected exactly one <form — a second one would be a second upload path "
                    "with a second set of limits to keep in sync" % (label,))
            form_tag = re.search(r"<form\b[^>]*>", markup)
            if not form_tag:
                return False, "%s: expected a <form> opening tag" % (label,)
            for required in ('method="post"', 'enctype="multipart/form-data"', action_attr,
                             'id="%s"' % form_id):
                if required not in form_tag.group(0):
                    return False, (
                        "%s: expected %r in the form's opening tag %r — a missing enctype would "
                        "silently post the file as a filename string, and a missing (as opposed "
                        "to empty) action would leave panel-lookup.js writing an attribute that "
                        "was never rendered" % (label, required, form_tag.group(0)))
            # The drop zone is the form's LAST child, after the submit
            # button: an enhancement appended to a working control, never
            # spliced between the control and the button that posts it.
            drop_at = markup.find(airlines_page.UPLOAD_DROP_ATTR)
            if drop_at == -1:
                return False, "%s: renders no drop zone at all" % (label,)
            if drop_at < markup.index('<button type="submit">'):
                return False, (
                    "%s: the drop zone renders BEFORE the submit button — it is an enhancement "
                    "appended to a working form, not a layer spliced into it" % (label,))
            # And it names the input it writes into, which is the only
            # thing tying the gesture to the form (panel-lookup.js is
            # ES5-subset, with no Element.closest() to walk up with).
            expected_hook = '%s="%s"' % (airlines_page.UPLOAD_DROP_INPUT_ATTR, input_id)
            if expected_hook not in markup:
                return False, "%s: expected the drop zone to carry %r" % (label, expected_hook)
        return True, ""
    check(
        "all three upload-form renderings (the no-JS fallback's, the dialog's copy, and the "
        "lightbox replace form) keep their <input type=\"file\" ... accept=\"image/png\" "
        "required>, their single bare <button type=\"submit\">, their hint paragraph, their "
        "method/enctype/action and exactly one <form> byte-identical to their pre-25-07 output — "
        "each now also carrying its own id and, as the form's LAST child after the submit button, "
        "a drop zone naming the very input it writes into (CFG-51/D19, 25-07-PLAN.md Task 1)",
        _upload_forms_native_controls_are_unchanged_by_the_drop_zone)

    def _drop_zone_ids_are_unique_and_no_drop_markup_escapes_the_js_gate():
        # A Step-B render with edit mode on is the page's busiest state:
        # the no-JS fallback panel's own upload zone, the dialog's copy
        # of it, and the dialog's replace form all render at once. That
        # is exactly the state an id collision would appear in, and it
        # is the reason the id_suffix discipline exists at all.
        tmp = _mkstate("a-drop-gate")
        try:
            result = manual_resolutions.add_entry(tmp, "NEW", "Totally Novel Airline")
            if result != manual_resolutions.ADD_OK:
                return False, "test setup failure: add_entry returned %r" % (result,)
            rendered = airlines_page.render(
                dict(_ctx(tmp), resolve_prefix="NEW"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        ids = re.findall(r'\sid="([^"]*)"', rendered)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            return False, (
                "the Airlines page emits duplicate id(s) %r — HTML requires every id to be "
                "document-unique, and adding markup to a form that exists twice is exactly how "
                "that breaks (this is what `id_suffix` is for)" % (duplicates,))

        # POINT 3 OF 25-01's CONTRACT, AND ITS CONVERSE. Boundary-
        # anchored on both sides so `data-upload-drop-input` (a real,
        # different attribute on the same tag) can never satisfy a
        # lookup for `data-upload-drop`.
        wrapper_re = re.compile(
            r"(?<![-\w])%s(?![-\w])" % re.escape(airlines_page.UPLOAD_DROP_ATTR))
        wrappers = []
        for tag in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", rendered):
            text = tag.group(0)
            if not wrapper_re.search(text):
                continue
            class_match = re.search(r'\bclass="([^"]*)"', text)
            classes = class_match.group(1).split() if class_match else []
            if layout.JS_GATE_CLASS not in classes:
                return False, (
                    "an element carries %s OUTSIDE the %r gate — %s. A drop target that cannot "
                    "receive a drop must not advertise one: with scripts blocked it would show "
                    "permanently and do nothing, competing with the file input that works"
                    % (airlines_page.UPLOAD_DROP_ATTR, layout.JS_GATE_CLASS, text))
            wrappers.append(tag.start())
        if len(wrappers) != 3:
            return False, (
                "expected exactly three gated drop wrappers on a Step-B edit-mode render (the "
                "fallback panel's upload form, the dialog's copy, and the replace form), got %d"
                % (len(wrappers),))

        # And nothing the script paints renders outside one of those
        # three wrappers. Counting the classes is not enough — a preview
        # box rendered beside the gate rather than inside it would still
        # count correctly while being permanently visible and inert.
        outside = rendered
        for start in reversed(wrappers):
            end = rendered.index("</section>", start) + len("</section>")
            outside = outside[:start] + outside[end:]
        for token in (airlines_page.UPLOAD_DROP_PREVIEW_CLASS,
                      airlines_page.UPLOAD_DROP_IMAGE_CLASS,
                      airlines_page.UPLOAD_DROP_NOTE_CLASS,
                      airlines_page.UPLOAD_DROP_MESSAGE_CLASS,
                      airlines_page.UPLOAD_DROP_INPUT_ATTR,
                      "--upload-preview-ratio"):
            if token in outside:
                return False, (
                    "%r renders OUTSIDE every gated drop wrapper — with scripts blocked that is "
                    "markup nothing can ever fill" % (token,))
        return True, ""
    check(
        "on a Step-B edit-mode Airlines render (the fallback panel's upload form, the dialog's "
        "copy and the replace form all at once) every emitted id is document-unique, every one "
        "of the three elements carrying data-upload-drop also carries layout.JS_GATE_CLASS ON "
        "ITSELF (boundary-anchored, so data-upload-drop-input cannot satisfy it), and with those "
        "three <section> subtrees excised the rest of the document contains zero preview, image, "
        "note, message, input-hook or --upload-preview-ratio markup (CFG-51/D-09, 25-07-PLAN.md "
        "Task 1)",
        _drop_zone_ids_are_unique_and_no_drop_markup_escapes_the_js_gate)

    def _preview_box_reserves_illustration_normalize_s_own_frame():
        markup = airlines_page._resolve_upload_form_html("", "-dialog")
        ratio = re.search(r'style="--upload-preview-ratio: (\d+) / (\d+)"', markup)
        if not ratio:
            return False, (
                "the preview box carries no inline --upload-preview-ratio — without it the box "
                "reserves nothing and the card jumps when the first image arrives")
        measured = (int(ratio.group(1)), int(ratio.group(2)))
        if measured != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
            return False, (
                "the preview box reserves %r but companion/illustration_normalize.py's output "
                "frame is %r — a preview promising a shape the server does not produce is the "
                "SECOND measurement that module's own docstring exists to forbid"
                % (measured, illustration_normalize.ILLUSTRATION_TARGET_SIZE))

        style_css_path = os.path.join(HERE, "static", "style.css")
        with open(style_css_path) as fh:
            css = re.sub(r"/\*.*?\*/", " ", fh.read(), flags=re.DOTALL)
        # Deliberately matched with EITHER terminator, so a rule that
        # grew a fallback still counts as "reads it" and fails on the
        # fallback clause below with the message that explains why —
        # rather than on this one, which would be the right verdict for
        # the wrong reason (measured: an exact `var(--upload-preview-
        # ratio)` test made the fallback clause unreachable).
        if not re.search(r"var\(\s*--upload-preview-ratio\s*[,)]", css):
            return False, (
                "companion/static/style.css never reads var(--upload-preview-ratio) — the inline "
                "property and the rule that consumes it are two halves of one contract")
        if re.search(r"var\(\s*--upload-preview-ratio\s*,", css):
            return False, (
                "companion/static/style.css gives --upload-preview-ratio a FALLBACK value — a "
                "fallback would keep the box the right shape even after the inline property "
                "stopped being rendered, masking the deletion of the live value rather than "
                "guarding against it")

        # Every class and attribute this plan adds resolves to a real
        # selector, matched on a SELECTOR BOUNDARY: a plain substring
        # test would report `.upload-drop` as resolved by a future
        # `.upload-drop-inner`.
        for class_name in (airlines_page.UPLOAD_DROP_CLASS,
                           airlines_page.UPLOAD_DROP_PREVIEW_CLASS,
                           airlines_page.UPLOAD_DROP_IMAGE_CLASS,
                           airlines_page.UPLOAD_DROP_NOTE_CLASS,
                           airlines_page.UPLOAD_DROP_MESSAGE_CLASS):
            if not re.search(r"\.%s(?![-\w])" % re.escape(class_name), css):
                return False, (
                    "companion/static/style.css declares no `.%s` selector on a boundary"
                    % (class_name,))
        if not re.search(r"\[%s\]" % re.escape(airlines_page.UPLOAD_DROP_ACTIVE_ATTR), css):
            return False, (
                "companion/static/style.css declares no [%s] rule — the drag state would have "
                "nowhere to paint" % (airlines_page.UPLOAD_DROP_ACTIVE_ATTR,))

        # The block's own three standing properties, asserted over the
        # rules themselves rather than over the whole file.
        rules = [m for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css)
                 if ".upload-drop" in m.group(1)]
        if len(rules) < 5:
            return False, "expected at least five .upload-drop rules in style.css, got %d" % len(rules)
        for selector, body in ((m.group(1).strip(), m.group(2)) for m in rules):
            if ":hover" in selector:
                return False, (
                    "`%s` is a :hover rule — the drag state must be reachable by touch, which is "
                    "why it rides on [%s] instead (the ground CFG-28 used for this app's "
                    "tooltips)" % (selector, airlines_page.UPLOAD_DROP_ACTIVE_ATTR))
            literal = re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", body)
            if literal:
                return False, (
                    "`%s` declares the colour literal %r — every colour in this block must come "
                    "from a theme token so both themes stay load-bearing"
                    % (selector, literal.group(0)))
            if "@keyframes" in selector or "animation" in body:
                return False, "`%s` introduces animation; this plan adds no motion at all" % (selector,)
        return True, ""
    check(
        "the framing preview reserves companion/illustration_normalize.py's OWN output frame "
        "(read from ILLUSTRATION_TARGET_SIZE, never a retyped ratio) through an inline "
        "--upload-preview-ratio that style.css reads with NO fallback value; every .upload-drop "
        "class and the [data-upload-drop-active] state resolve to real selectors on a selector "
        "boundary; and not one .upload-drop rule uses :hover, declares a colour literal or "
        "introduces animation (CFG-51/CFG-52, 25-07-PLAN.md Task 1)",
        _preview_box_reserves_illustration_normalize_s_own_frame)

    # ------------------------------------------------------------------
    # Phase 14 (14-04-PLAN.md Task 1): the coverage-gap block (D-01,
    # D-02, D-04, D-05, D-06, D-07).
    # ------------------------------------------------------------------

    def _gap_block_threshold_sort_cap_and_overflow():
        tmp = _mkstate("a-gap-threshold-sort-cap")
        try:
            registry = {}
            for i in range(15):
                prefix = "G%02d" % i
                registry[prefix] = {
                    "count": 3 + i, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "%s123" % prefix,
                }
            _seed_unresolved_prefixes(tmp, registry)
            shown, overflow_count = airlines_page._gap_rows_for_grid(tmp)
            if len(shown) != airlines_page.GAP_BLOCK_CAP:
                return False, "expected exactly %d shown gap rows, got %d" % (
                    airlines_page.GAP_BLOCK_CAP, len(shown))
            if overflow_count != 3:
                return False, "expected an overflow count of 3 (15 eligible - 12 cap), got %d" % (
                    overflow_count,)
            expected_prefixes = [
                prefix for prefix, _ in sorted(
                    registry.items(), key=lambda item: (-item[1]["count"], item[0]))
            ][:airlines_page.GAP_BLOCK_CAP]
            actual_prefixes = [row[0] for row in shown]
            if actual_prefixes != expected_prefixes:
                return False, "expected rows sorted (-count, prefix), got %r (wanted %r)" % (
                    actual_prefixes, expected_prefixes)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        # The threshold is >=, not >: an identical prefix at count=2
        # must never earn a gap row; the same prefix at count=3 must.
        tmp2 = _mkstate("a-gap-threshold-boundary")
        try:
            _seed_unresolved_prefixes(tmp2, {
                "AT2": {"count": 2, "first_seen": "t1", "last_seen": "t2", "example_callsign": "AT2123"},
            })
            shown_low, overflow_low = airlines_page._gap_rows_for_grid(tmp2)
            if shown_low or overflow_low:
                return False, "expected count=2 (below GAP_BLOCK_THRESHOLD=3) to never render a gap row"
            _seed_unresolved_prefixes(tmp2, {
                "AT3": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "AT3123"},
            })
            shown_high, overflow_high = airlines_page._gap_rows_for_grid(tmp2)
            if [row[0] for row in shown_high] != ["AT3"]:
                return False, "expected count=3 (== GAP_BLOCK_THRESHOLD) to render exactly one gap row"
            if overflow_high != 0:
                return False, "expected zero overflow with only one eligible prefix"
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
        return True, ""
    check(
        "_gap_rows_for_grid() thresholds at >= GAP_BLOCK_THRESHOLD (3), sorts eligible rows (-count, prefix), "
        "caps at GAP_BLOCK_CAP (12), and reports the exact overflow count for the rest (D-05/D-06)",
        _gap_block_threshold_sort_cap_and_overflow)

    def _gap_card_markup_shape_and_attribute_vocabulary():
        row = ("XYZ", 5, "t1", "t2", "XYZ123")
        card_html = airlines_page._gap_card_html(0, row)
        if "<img" in card_html:
            return False, "expected zero <img> tags in a gap card"
        if "airline-card__zoom" in card_html:
            return False, "expected no nested .airline-card__zoom button in a gap card"
        if not card_html.startswith('<a class="airline-card"'):
            return False, "expected the whole card to be a real <a class=\"airline-card\"> element"
        if not card_html.rstrip().endswith("</a>"):
            return False, "expected the card to close with </a>"
        expected_href = 'href="%s?%s=XYZ"' % (
            airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
        if expected_href not in card_html:
            return False, "expected %r in the gap card's markup" % (expected_href,)
        required_attr_values = {
            airlines_page._VIEW_PANEL_SRC_ATTR: "",
            airlines_page._VIEW_PANEL_CAPTION_ATTR: "XYZ123",
            airlines_page._VIEW_PANEL_HEADING_ATTR: airlines_page.RESOLVE_HEADING,
            airlines_page._VIEW_PANEL_MODE_ATTR: airlines_page._VIEW_PANEL_MODE_GAP,
            airlines_page._VIEW_PANEL_MANUAL_ATTR: "",
            airlines_page._VIEW_PANEL_SCOPE_ATTR: airlines_page.RESOLVE_CAPTION_TEMPLATE % "XYZ",
            airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR: "XYZ",
            airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR: "t1",
            airlines_page._VIEW_PANEL_LAST_SEEN_ATTR: "t2",
            airlines_page._VIEW_PANEL_COUNT_ATTR: "5",
        }
        for attr, expected_value in required_attr_values.items():
            expected_fragment = '%s="%s"' % (attr, expected_value)
            if expected_fragment not in card_html:
                return False, "expected %r in the gap card's markup, got %r" % (expected_fragment, card_html)
        if '<span class="airline-card__placeholder" aria-hidden="true"></span>' not in card_html:
            return False, "expected the pure-CSS placeholder span"
        if '<p class="airline-card__name mono">XYZ123</p>' not in card_html:
            return False, "expected the visible callsign paragraph"
        return True, ""
    check(
        "_gap_card_html() renders the whole card as a real <a class=\"airline-card\" "
        "href=\"/airlines?resolve={prefix}\"> trigger with zero <img> tags and no nested "
        ".airline-card__zoom button, carrying every data-view-panel-* attribute UI-SPEC's Gap-card markup "
        "shape names, non-empty where that snippet shows a value (D-01/D-02/D-12)",
        _gap_card_markup_shape_and_attribute_vocabulary)

    def _gap_card_filter_group_never_collides_with_curated_integer_groups():
        source_path = os.path.join(HERE, "pages", "airlines_page.py")
        with open(source_path) as fh:
            page_source = fh.read()
        if 'data-filter-group="gap%d"' not in page_source:
            return False, "expected the literal 'data-filter-group=\"gap%d\"' format string in the source"
        row = ("XYZ", 5, "t1", "t2", "XYZ123")
        for index in (0, 1, 11):
            card_html = airlines_page._gap_card_html(index, row)
            match = re.search(r'data-filter-group="([^"]+)"', card_html)
            if not match:
                return False, "expected a data-filter-group attribute on the gap card"
            value = match.group(1)
            if not re.match(r"^gap\d+$", value):
                return False, "expected data-filter-group to match ^gap\\d+$, got %r" % (value,)
        tmp = _mkstate("a-gap-filter-group-collision")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
            })
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        curated_groups = set(re.findall(r'data-filter-group="(\d+)"', rendered))
        gap_groups = set(re.findall(r'data-filter-group="(gap\d+)"', rendered))
        if not gap_groups:
            return False, "expected at least one gap data-filter-group in the rendered page"
        for gap_group in gap_groups:
            if gap_group in curated_groups:
                return False, (
                    "expected gap group %r to never equal a curated card's own bare-integer group"
                    % (gap_group,))
        return True, ""
    check(
        "a gap card's data-filter-group value is always a string-prefixed \"gap{index}\" (never a bare "
        "integer) and never collides, as a bare string, with any curated card's own data-filter-group "
        "value on the same render (RESEARCH.md Pitfall 4, T-14-17)",
        _gap_card_filter_group_never_collides_with_curated_integer_groups)

    def _gap_overflow_html_renders_only_when_the_cap_bites():
        if airlines_page._gap_overflow_html(0) != "":
            return False, "expected the empty string when overflow_count is 0"
        overflow_html = airlines_page._gap_overflow_html(3)
        if not overflow_html.startswith('<p class="text-label section-caption">'):
            return False, "expected the overflow line's own wrapping <p>"
        if "3 other unresolved prefixes" not in overflow_html:
            return False, "expected the overflow count interpolated into the line"
        link_match = re.search(r'<a href="/health">([^<]+)</a>', overflow_html)
        if not link_match:
            return False, "expected an <a href=\"/health\"> link"
        if link_match.group(1) != airlines_page.MANUAL_OVERFLOW_LINK_TEXT:
            return False, "expected the anchor to wrap only MANUAL_OVERFLOW_LINK_TEXT, got %r" % (
                link_match.group(1),)
        if not overflow_html.endswith("</a>.</p>"):
            return False, "expected the trailing period immediately after the anchor's closing tag, outside it"
        return True, ""
    check(
        "_gap_overflow_html() returns the empty string when the cap does not bite, and otherwise the exact "
        "templated line naming the overflow count, with <a href=\"/health\"> wrapping only "
        "MANUAL_OVERFLOW_LINK_TEXT and the trailing period sitting outside the anchor (D-07)",
        _gap_overflow_html_renders_only_when_the_cap_bites)

    def _gap_card_escapes_hostile_example_callsign():
        hostile_callsign = '<script>alert(1)</script>"'
        row = ("XYZ", 5, "t1", "t2", hostile_callsign)
        card_html = airlines_page._gap_card_html(0, row)
        if hostile_callsign in card_html:
            return False, "expected the raw hostile callsign to never appear unescaped"
        if "<script>" in card_html:
            return False, "expected no raw '<script>' fragment to survive"
        escaped_callsign = layout.escape_html(hostile_callsign)
        if card_html.count(escaped_callsign) < 2:
            return False, (
                "expected the escaped callsign to appear at least twice (data-view-panel-caption attribute "
                "and the visible name paragraph), got %d" % (card_html.count(escaped_callsign),))
        return True, ""
    check(
        "an example_callsign containing '<', '>', '&' and '\"' reaching a gap card renders fully escaped, "
        "both in data-view-panel-caption and in the visible callsign paragraph, exactly once per "
        "interpolation site (T-06.6.4.1-05, T-14-16)",
        _gap_card_escapes_hostile_example_callsign)

    # ------------------------------------------------------------------
    # Phase 14 (14-06-PLAN.md Task 1, D-08/D-10/D-12 fallback
    # reachability): _airline_card_html()'s widened manual_info
    # parameter and render()'s grid-injection step.
    # ------------------------------------------------------------------

    def _airline_card_html_manual_info_none_matches_todays_plain_card_and_keeps_button():
        tmp = _mkstate("a-manual-info-none")
        try:
            card_none = airlines_page._airline_card_html(0, "Air France", [], tmp, None)
            card_omitted = airlines_page._airline_card_html(0, "Air France", [], tmp)
            if card_none != card_omitted:
                return False, "expected manual_info=None to match the default-omitted call byte-for-byte"
            if '<button type="button" class="airline-card__zoom"' not in card_none:
                return False, "expected a plain curated card (no manual_info) to still wrap a <button>"
            if "<a href=" in card_none:
                return False, "expected no <a> trigger anywhere on a plain curated card"
            if 'data-view-panel-mode="art"' not in card_none:
                return False, 'expected mode="art" for a plain curated card'
            if 'data-view-panel-manual=""' not in card_none:
                return False, "expected an empty manual attribute for a plain curated card"
            if 'data-view-panel-resolve-prefix=""' not in card_none:
                return False, "expected an empty resolve-prefix attribute for a plain curated card"
            if "airline-card__chip" in card_none:
                return False, "expected no chip at all for a shapeless, manual_info=None card"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "_airline_card_html(index, airline_name, shapes, state_dir, manual_info=None) renders byte-identically "
        "to the default-omitted call, and a plain curated card with no manual history still wraps a real "
        "<button> (never an <a>), with mode=\"art\" and every manual/resolve-prefix attribute empty "
        "(14-06-PLAN.md Task 1)",
        _airline_card_html_manual_info_none_matches_todays_plain_card_and_keeps_button)

    def _airline_card_html_active_manual_states_render_expected_attributes_and_chip():
        tmp = _mkstate("a-manual-active-states")
        try:
            # (a) active, has artwork — Air France already has real vendored art.
            card_art = airlines_page._airline_card_html(0, "Air France", [], tmp, ("ZZZ", False, False))
            expected_open = '<a href="%s?%s=ZZZ" class="airline-card__zoom"' % (
                airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
            if expected_open not in card_art:
                return False, "expected the trigger to be a real <a href> when a resolve prefix is present"
            if 'data-view-panel-mode="art"' not in card_art:
                return False, 'expected mode="art" for an active manual entry with real artwork'
            if 'data-view-panel-manual="active"' not in card_art:
                return False, 'expected manual="active"'
            if 'data-view-panel-resolve-prefix="ZZZ"' not in card_art:
                return False, "expected the resolve-prefix attribute to equal the prefix"
            expected_delete_action = airlines_page._manual_delete_action("ZZZ")
            if ('data-view-panel-delete-action="%s"' % expected_delete_action) not in card_art:
                return False, "expected the delete-action attribute to equal _manual_delete_action(prefix)"
            if 'data-view-panel-manual-note=""' not in card_art:
                return False, "expected an empty manual-note for an active (non-superseded) entry"
            if ('<span class="airline-card__chip">%s</span>' % airlines_page.MANUAL_CHIP_ACTIVE_TEXT) not in card_art:
                return False, "expected the 'Resolved by hand' chip"

            # (b) active, needs artwork — a genuinely novel name with no artwork yet.
            card_needs = airlines_page._airline_card_html(
                0, "Totally Novel Airline", [], tmp, ("XQZ", False, True))
            if 'data-view-panel-mode="needs-artwork"' not in card_needs:
                return False, 'expected mode="needs-artwork"'
            expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Totally Novel Airline"
            if ('data-view-panel-heading="%s"' % expected_heading) not in card_needs:
                return False, "expected the heading attribute to equal STEP_B_HEADING_TEMPLATE % airline_name"
            if 'data-view-panel-upload-action="/illustration/totally-novel-airline.png"' not in card_needs:
                return False, "expected the upload-action to point at /illustration/{key}.png"
            if ('<span class="airline-card__chip">%s</span>' % airlines_page.MANUAL_CHIP_ACTIVE_TEXT) not in card_needs:
                return False, "expected the 'Resolved by hand' chip on a needs-artwork active card too"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an active manual_info triple renders the real <a href> trigger, the correct mode/heading/"
        "upload-action for both the has-artwork and needs-artwork cases, the delete-action attribute from "
        "_manual_delete_action(), an empty manual-note, and the 'Resolved by hand' chip (14-06-PLAN.md "
        "Task 1)",
        _airline_card_html_active_manual_states_render_expected_attributes_and_chip)

    def _airline_card_html_needs_artwork_sighting_context_conditional_on_live_gap():
        tmp_live = _mkstate("a-manual-needs-artwork-live-gap")
        tmp_cleared = _mkstate("a-manual-needs-artwork-cleared-gap")
        try:
            _seed_unresolved_prefixes(tmp_live, {
                "XQZ": {
                    "count": 5,
                    "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-02T00:00:00+00:00",
                    "example_callsign": "XQZ123",
                },
            })
            manual_info = ("XQZ", False, True)
            card_live = airlines_page._airline_card_html(0, "Totally Novel Airline", [], tmp_live, manual_info)
            if 'data-view-panel-first-seen="2026-01-01T00:00:00+00:00"' not in card_live:
                return False, "expected first-seen populated from the live gap registry"
            if 'data-view-panel-last-seen="2026-01-02T00:00:00+00:00"' not in card_live:
                return False, "expected last-seen populated from the live gap registry"
            if 'data-view-panel-count="5"' not in card_live:
                return False, "expected count populated from the live gap registry"

            # D-14: once the live gap is cleared, all three fall back to
            # empty rather than crashing or showing stale data.
            card_cleared = airlines_page._airline_card_html(
                0, "Totally Novel Airline", [], tmp_cleared, manual_info)
            if 'data-view-panel-first-seen=""' not in card_cleared:
                return False, "expected first-seen empty once the live gap is gone"
            if 'data-view-panel-last-seen=""' not in card_cleared:
                return False, "expected last-seen empty once the live gap is gone"
            if 'data-view-panel-count=""' not in card_cleared:
                return False, "expected count empty once the live gap is gone"

            # These three attributes are only ever computed for
            # mode=needs-artwork — an art-mode card (even one carrying
            # manual_info) must never populate them, matching UI-SPEC's
            # own "wasted work, not a correctness requirement" framing.
            card_art_mode = airlines_page._airline_card_html(
                0, "Air France", [], tmp_live, ("ZZZ", False, False))
            if 'data-view-panel-count=""' not in card_art_mode:
                return False, "expected an art-mode card to leave the sighting-context attributes empty"
            return True, ""
        finally:
            shutil.rmtree(tmp_live, ignore_errors=True)
            shutil.rmtree(tmp_cleared, ignore_errors=True)
    check(
        "a needs-artwork manual card's first-seen/last-seen/count attributes are populated from "
        "unresolved_row_for_prefix() only when a live gap still exists for that prefix, fall back to empty "
        "once D-14 clears it, and stay empty on an art-mode card regardless of manual_info (14-06-PLAN.md "
        "Task 1)",
        _airline_card_html_needs_artwork_sighting_context_conditional_on_live_gap)

    def _airline_card_html_superseded_shows_built_in_state_never_operator_upload():
        tmp = _mkstate("a-manual-superseded-card")
        try:
            # AFR is a real static-table prefix (enrich._ICAO_AIRLINE_PREFIXES);
            # the entry's own stored name is deliberately distinct from
            # the real static name "Air France".
            manual_resolutions.add_entry(tmp, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
            rendered = airlines_page.render(_ctx(tmp))
            card = _card_slice(rendered, "Air France")
            if 'data-view-panel-manual="superseded"' not in card:
                return False, 'expected manual="superseded" on the Air France card'
            if ('<span class="airline-card__chip">%s</span>' % airlines_page.SUPERSEDED_MARKER_TEXT) not in card:
                return False, "expected the Superseded chip on the card"
            src_match = re.search(r'data-view-panel-src="([^"]*)"', card)
            if not src_match or not src_match.group(1).startswith("/illustration/air-france.png"):
                return False, (
                    "expected data-view-panel-src to point at the built-in Air France illustration key, "
                    "got %r" % (src_match.group(1) if src_match else None,))
            if "some-other-airline" in card.lower():
                return False, "expected the card to never derive a key from the entry's own stored name"
            note_match = re.search(r'data-view-panel-manual-note="([^"]*)"', card)
            if not note_match:
                return False, "expected a manual-note on the superseded card"
            note_text = note_match.group(1)
            if "AFR" not in note_text or "Air France" not in note_text:
                return False, "expected the manual-note to interpolate the prefix and the built-in name"
            if "Some Other Airline" not in note_text:
                return False, (
                    "expected the manual-note's third slot to name the OPERATOR's own stored name "
                    "('Some Other Airline'), not the built-in name a second time — the card's own "
                    "airline_name parameter (the built-in name, for display/key purposes) must not be "
                    "conflated with the registry entry's own stored airline_name field")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a superseded card never shows the operator's own orphaned upload: data-view-panel-src points at "
        "the built-in Air France illustration key (never a key derived from the entry's own stored name), "
        "the Superseded chip renders, and the manual-note interpolates the prefix, the built-in name, AND "
        "the operator's own originally-stored name (not the built-in name a second time) "
        "(D-10, 14-06-PLAN.md Task 1)",
        _airline_card_html_superseded_shows_built_in_state_never_operator_upload)

    def _render_grid_injection_adds_exactly_one_novel_card_and_none_for_superseded_or_curated():
        def _grid_section(rendered):
            grid_start = rendered.index('class="illustration-grid"')
            dialog_start = rendered.index('id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID, grid_start)
            return rendered[grid_start:dialog_start]

        tmp_novel = _mkstate("a-grid-injection-novel")
        tmp_none = _mkstate("a-grid-injection-none")
        try:
            # A genuinely novel active manual name gets exactly one
            # injected card.
            manual_resolutions.add_entry(tmp_novel, "XQZ", "Totally Novel Airline", now="2026-01-01T00:00:00+00:00")
            rendered_novel = airlines_page.render(_ctx(tmp_novel))
            novel_count = _grid_section(rendered_novel).count(
                '<p class="airline-card__name">Totally Novel Airline</p>')
            if novel_count != 1:
                return False, (
                    "expected exactly one injected card for a genuinely novel active manual name, "
                    "got %d" % novel_count)

            # A superseded entry needs no injection (its display name is
            # already curated); an active entry whose name is ALREADY
            # curated must not be duplicated either.
            manual_resolutions.add_entry(tmp_none, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
            manual_resolutions.add_entry(tmp_none, "OLD", "Air France", now="2026-01-01T00:00:00+00:00")
            rendered_none = airlines_page.render(_ctx(tmp_none))
            grid_none = _grid_section(rendered_none)
            af_count = grid_none.count('<p class="airline-card__name">Air France</p>')
            if af_count != 1:
                return False, (
                    "expected Air France to appear exactly once in the grid (no duplicate injection), "
                    "got %d" % af_count)
            if '<p class="airline-card__name">Some Other Airline</p>' in grid_none:
                return False, "expected no injected card for a superseded entry's own orphaned stored name"
            return True, ""
        finally:
            shutil.rmtree(tmp_novel, ignore_errors=True)
            shutil.rmtree(tmp_none, ignore_errors=True)
    check(
        "render()'s grid-injection step adds exactly one card for a genuinely novel active manual airline "
        "name not already among the curated pairs, and adds none for a superseded entry or for an active "
        "entry whose name is already curated (D-08, UI-SPEC's Grid injection, 14-06-PLAN.md Task 1)",
        _render_grid_injection_adds_exactly_one_novel_card_and_none_for_superseded_or_curated)

    # ------------------------------------------------------------------
    # Phase 13 (13-04-PLAN.md Task 1): the conditional resolve section
    # (D-03, D-10 through D-13).
    # ------------------------------------------------------------------

    def _resolve_slice(rendered):
        """Isolate everything the page renders AFTER the shared dialog —
        Phase 14 (14-04-PLAN.md) moved the resolve section from the top
        of the page (before the filter bar) to the bottom (behind the
        shared lightbox), so the old filter-bar-anchored slice boundary
        no longer isolates it. This anchors on the dialog's own id and
        its universal closing tag instead of a hardcoded index into any
        specific inner string, so it stays correct regardless of what
        any later wave adds inside the dialog.
        """
        dialog_id_marker = 'id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID
        dialog_start = rendered.index(dialog_id_marker)
        dialog_close = rendered.index("</dialog>", dialog_start)
        return rendered[dialog_close + len("</dialog>"):]

    def _resolve_section_four_states_render_correctly():
        tmp = _mkstate("a-resolve-states")
        try:
            now = _iso(_now())

            # State 1: the query prefix is not a member of the live
            # registry at all -> the stale sentence, no form of any kind.
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "ZZZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            if airlines_page.RESOLVE_STALE_BODY not in section:
                return False, "expected the stale sentence for a prefix absent from the registry"
            if airlines_page.MANUAL_NAME_INPUT_ID in section:
                return False, "expected no name input for a stale/absent prefix"
            if "<form" in section:
                return False, "expected no <form> inside the resolve section for a stale/absent prefix"

            # Seed a real coverage gap, no manual entry recorded for it yet.
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 3, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            if airlines_page.RESOLVE_HEADING not in section:
                return False, "expected the Step A heading for a seeded gap with no manual entry"
            if ('id="%s"' % airlines_page.MANUAL_NAME_INPUT_ID) not in section:
                return False, "expected the name input to render at Step A"
            if '<input type="file"' in section:
                return False, "expected no file input at Step A"

            # Record a manual entry naming a fresh airline with no artwork.
            add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
            if add_result != manual_resolutions.ADD_OK:
                return False, "expected add_entry() to accept a fresh, valid name, got %r" % (add_result,)
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Brand New Air"
            if expected_heading not in section:
                return False, "expected the Step B heading naming the stored airline, got a render missing %r" % (
                    expected_heading,)
            key = manual_resolutions.illustration_key_for_name("Brand New Air")
            expected_action = 'action="%s%s.png"' % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key)
            if expected_action not in section:
                return False, "expected the upload form action to be %r" % (expected_action,)
            if '<input type="file"' not in section:
                return False, "expected a file input at Step B"

            # Re-add the same prefix, this time naming a target airline
            # that already has artwork.
            add_result = manual_resolutions.add_entry(tmp, "XYZ", "Air France", now=now)
            if add_result != manual_resolutions.ADD_OK:
                return False, "expected add_entry() to accept overwriting the same prefix, got %r" % (add_result,)
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            expected_done = airlines_page.RESOLVE_ALREADY_DONE_TEMPLATE % "Air France"
            if expected_done not in section:
                return False, "expected the already-resolved sentence naming Air France"
            if '<input type="file"' in section:
                return False, "expected no file input once artwork already resolves for the stored name"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the resolve section renders all four server-derived states and only the right controls in each: "
        "absent-from-registry (stale sentence, no form at all), seeded-gap-no-entry (Step A heading, name "
        "input, no file input), seeded-gap-with-artless-entry (Step B heading naming the stored airline, "
        "upload form action ending /{key}.png, a file input), and seeded-gap-with-resolved-entry (the "
        "already-resolved sentence, no file input) — D-03/D-11",
        _resolve_section_four_states_render_correctly)

    def _resolve_section_datalist_contract():
        # Phase 14 (14-02-PLAN.md Task 3) retargeted this check onto
        # _resolve_slice(rendered) in place (no EXPECTED_CHECK_COUNT
        # change — same check, re-scoped): the shared dialog now
        # unconditionally renders its own copy of this datalist too
        # (_resolve_name_form_html("", "-dialog"), id "known-airlines-
        # dialog"), so a full-page option count would double to 54.
        # This check's own subject is the no-JS fallback's datalist, so
        # it slices down to that section exactly like every sibling
        # resolve-section check already does.
        tmp = _mkstate("a-resolve-datalist")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 1, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            ctx = _ctx(tmp)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            names = illustrations.target_airline_names()
            option_count = section.count("<option value=")
            if option_count != len(names):
                return False, "expected %d <option> elements (one per target airline), got %d" % (
                    len(names), option_count)
            datalist_match = re.search(r'<datalist id="([^"]+)">', section)
            if not datalist_match:
                return False, "expected a <datalist id=\"...\"> element"
            list_attr_match = re.search(r'list="([^"]+)"', section)
            if not list_attr_match or list_attr_match.group(1) != datalist_match.group(1):
                return False, "expected the name input's list attribute to equal the datalist's own id"
            for name in names:
                expected_option = '<option value="%s">' % layout.escape_html(name)
                if expected_option not in section:
                    return False, "expected an escaped %r for airline %r" % (expected_option, name)
            # 14-06-PLAN.md external gap-closure (2026-09-06, per
            # 14-05-SUMMARY.md's own documented finding):
            # _resolve_name_form_html() now emits an always-present,
            # server-side-empty <p class="lightbox__resolve-scope">
            # inside its own output — panel-lookup.js (plan 14-05)
            # writes the D-01 scope sentence into it on every dialog
            # open. Checked here (the no-JS fallback's own call site)
            # since the two calls share one rendering function.
            if '<p class="lightbox__resolve-scope"></p>' not in section:
                return False, "expected an empty <p class=\"lightbox__resolve-scope\"></p> in the rendered form"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Step A's rendered datalist carries exactly len(illustrations.target_airline_names()) (36 against "
        "today's data) <option> elements, the datalist's id matches the name input's list attribute, every "
        "airline name appears as an escaped <option value=...> exactly once (D-13), and the shared "
        "_resolve_name_form_html() output also carries an empty <p class=\"lightbox__resolve-scope\"></p> "
        "for panel-lookup.js to write into on open (14-06-PLAN.md external gap-closure)",
        _resolve_section_datalist_contract)

    def _resolve_section_escapes_hostile_values_and_distrusts_query_string():
        tmp = _mkstate("a-resolve-escaping")
        try:
            hostile_name = '<b>Evil & "quoted" name'
            hostile_callsign = '<i>XYZ</i> & "call"'
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 1, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": hostile_callsign,
                },
            })
            add_result = manual_resolutions.add_entry(tmp, "XYZ", hostile_name)
            if add_result != manual_resolutions.ADD_OK:
                return False, "expected add_entry() to accept the hostile-but-slug-safe name, got %r" % (
                    add_result,)

            now = _iso(_now())
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)

            if "<b>Evil" in rendered or "<i>XYZ</i>" in rendered:
                return False, "found an unescaped hostile tag in the rendered page"
            if re.search(r"&(?!amp;|lt;|gt;|quot;|#39;|#x27;)", rendered):
                return False, "found a raw & that is not part of an HTML entity"
            if 'value="<b>' in rendered or 'title="<b>' in rendered:
                return False, "found an unescaped hostile value inside an attribute"

            # WR-04: a resolve_prefix that differs from the stored
            # registry key only in case or surrounding whitespace
            # normalises (via unresolved_row_for_prefix()'s own
            # manual_resolutions.normalise_prefix() call) to the
            # identical prefix the write path (POST /airlines/resolve)
            # already accepts — so it must render the exact same resolve
            # section as the canonical upper-case value, never a
            # different (stale) state derived from treating the raw,
            # unnormalised query string as authoritative (D-12).
            canonical_section = _resolve_slice(rendered)
            for hostile_prefix in ("xyz", "XYZ ", " XYZ", "Xyz"):
                ctx = _ctx(tmp, now=now)
                ctx["resolve_prefix"] = hostile_prefix
                variant_rendered = airlines_page.render(ctx)
                variant_section = _resolve_slice(variant_rendered)
                if variant_section != canonical_section:
                    return False, (
                        "expected resolve_prefix=%r to normalise to the same resolve "
                        "section as the canonical 'XYZ', got a divergent render"
                        % (hostile_prefix,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a stored airline name and example callsign both containing an angle bracket, a double quote and an "
        "ampersand render fully escaped everywhere they appear (including inside an attribute value), and a "
        "resolve_prefix differing from the stored registry key only in case or surrounding whitespace "
        "normalises to the identical prefix and renders the identical resolve section (WR-04/D-12)",
        _resolve_section_escapes_hostile_values_and_distrusts_query_string)

    def _resolve_section_step_b_reachable_after_gap_cleared():
        tmp = _mkstate("a-resolve-cr02-step-b")
        try:
            now = _iso(_now())
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 1, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
            if add_result != manual_resolutions.ADD_OK:
                return False, "setup failure: add_entry() returned %r" % (add_result,)

            # CR-02: simulate D-14 — the poll loop has since cleared the
            # now-resolved prefix from the live gap registry, exactly as
            # it would on the very next cycle after Step A saved a name.
            _seed_unresolved_prefixes(tmp, {})

            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            if airlines_page.RESOLVE_STALE_BODY in section:
                return False, (
                    "CR-02: Step B must stay reachable once D-14 clears the live gap, got the "
                    "stale sentence instead")
            expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Brand New Air"
            if expected_heading not in section:
                return False, (
                    "expected the Step B heading naming the stored airline even with no live "
                    "gap, got a render missing %r" % (expected_heading,))
            if '<input type="file"' not in section:
                return False, "expected a file input at Step B even with no live gap"
            if 'class="resolve-context"' in section:
                return False, (
                    "expected no sighting-context <dl> once the gap entry that carried it is "
                    "gone — there is genuinely no data left to show")
            if airlines_page.STEP_B_SKIP_TEXT not in section:
                return False, "expected the Skip link to still render at Step B with no live gap"

            # D-07's delete-and-re-add correction path must also still
            # work with the gap gone: re-adding under a name that
            # already has artwork must reach the already-done state, not
            # a dead end.
            add_result = manual_resolutions.add_entry(tmp, "XYZ", "Air France", now=now)
            if add_result != manual_resolutions.ADD_OK:
                return False, "setup failure: add_entry() (Air France) returned %r" % (add_result,)
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            expected_done = airlines_page.RESOLVE_ALREADY_DONE_TEMPLATE % "Air France"
            if expected_done not in section:
                return False, (
                    "expected the already-resolved sentence even with no live gap, got a "
                    "render missing %r" % (expected_done,))

            # With neither a live gap NOR a manual entry, the prefix is
            # genuinely stale — this must not regress into always
            # showing Step B/already-done for any well-shaped prefix.
            manual_resolutions.delete_entry(tmp, "XYZ")
            ctx = _ctx(tmp, now=now)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
            section = _resolve_slice(rendered)
            if airlines_page.RESOLVE_STALE_BODY not in section:
                return False, (
                    "expected the stale sentence once neither a live gap nor a manual entry "
                    "exists for the prefix")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "CR-02: once D-14 clears a resolved prefix from the live gap registry, the resolve section still "
        "reaches Step B for a manual entry with no artwork yet (heading, file input, Skip link, no "
        "sighting-context <dl>), still reaches the already-resolved state once artwork exists under the "
        "re-added name (D-07's delete-and-re-add path), and still renders the stale sentence only once "
        "neither a live gap nor a manual entry exists for the prefix",
        _resolve_section_step_b_reachable_after_gap_cleared)

    def _page_composition_order_matches_ui_spec():
        # Phase 14 (14-04-PLAN.md Task 2): the one direct, permanent
        # proof that UI-SPEC's new top-to-bottom order actually shipped
        # — independent of what any individual section's own
        # content-focused check already covers. Seeds both a real gap
        # (so resolve_prefix reaches a live Step-A render) and relies on
        # the always-present curated gallery.
        tmp = _mkstate("a-page-composition-order")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 3, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            ctx = _ctx(tmp)
            ctx["resolve_prefix"] = "XYZ"
            rendered = airlines_page.render(ctx)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        try:
            filter_bar_index = rendered.index('class="filter-bar')
            grid_index = rendered.index('class="illustration-grid', filter_bar_index)
            dialog_open_index = rendered.index(
                'id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID, grid_index)
            dialog_close_index = rendered.index("</dialog>", dialog_open_index)
            back_link_index = rendered.index(
                airlines_page.RESOLVE_BACK_LINK_TEXT, dialog_close_index)
        except ValueError as exc:
            return False, "expected all five order markers to be present, in order: %s" % (exc,)
        markers = (filter_bar_index, grid_index, dialog_open_index, dialog_close_index, back_link_index)
        if list(markers) != sorted(markers):
            return False, "expected strictly increasing marker positions, got %r" % (markers,)
        return True, ""
    check(
        "the page's own top-to-bottom order is filter-bar, then illustration-grid, then the shared dialog's "
        "opening tag, then its closing tag, then (last) the resolve section's own back-link text — proving "
        "UI-SPEC's new page composition (resolve section moved to the bottom, behind the shared dialog) "
        "shipped for real",
        _page_composition_order_matches_ui_spec)

    # ------------------------------------------------------------------
    # Phase 13 (13-04-PLAN.md Task 2): the manual-resolutions management
    # list (D-06, D-07, D-08).
    # ------------------------------------------------------------------

    def _manual_summary_line_replaces_retired_management_table_copy():
        # Phase 14 plan 14-06 Task 2, item 1 (retargeted in place from
        # _manual_section_empty_and_populated_states — the standalone
        # management table this check used to exercise is gone).
        tmp = _mkstate("a-manual-empty-populated")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            # 22-11-PLAN.md Task 2 (X7), retargeted in place: the summary
            # is no longer a 12px bare link below the filter bar. It is a
            # real filter control INSIDE the bar, wearing
            # `.airline-card__chip`'s label voice with `.manual-summary`
            # kept as the interactive hover hook. The class is therefore
            # composed, not solitary — matched here through its
            # data-filter-set hook plus the composed class attribute, so
            # this check pins the NEW shape rather than merely tolerating
            # it, and would fail if the chip voice were dropped again.
            summary_open = (
                '<button type="button" class="airline-card__chip manual-summary" '
                'data-filter-set="manual">')
            if "manual-summary" in rendered:
                return False, "expected no .manual-summary element when the registry is empty"
            for retired_copy in (
                    "Manually resolved prefixes",
                    "Airlines you’ve named by hand for a prefix the frame couldn’t "
                    "otherwise identify.",
                    "No manual resolutions yet.",
                    "Resolve an unidentified flight from Health’s coverage-gap list "
                    "to add one here.",
                    "The frame’s built-in airline list now also recognizes this "
                    "prefix — its entry wins, and this manual name is no longer used.",
                    "manual-resolution__status--superseded",
            ):
                if retired_copy in rendered:
                    return False, (
                        "expected no trace of the retired management table's own copy: %r" % (retired_copy,))

            manual_resolutions.add_entry(tmp, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
            manual_resolutions.add_entry(tmp, "ZZZ", "Brand New Air", now="2026-01-02T00:00:00+00:00")
            rendered = airlines_page.render(_ctx(tmp))
            summary_count = rendered.count(summary_open)
            if summary_count != 1:
                return False, "expected the .manual-summary button to render exactly once, got %d" % summary_count
            # It sits inside the filter bar now, not between the bar and
            # the grid — the half of X7's fix a class-name check misses.
            bar = re.search(r'<div class="filter-bar">(.*?)</div>\s*<div class="empty-state"',
                            rendered, re.S)
            if bar is None or summary_open not in bar.group(1):
                return False, (
                    "expected the summary control to render INSIDE the filter bar (X7)")
            expected_text = airlines_page.MANUAL_SUMMARY_TEMPLATE % (2, 1)
            expected_button = "%s%s</button>" % (summary_open, expected_text)
            if expected_button not in rendered:
                return False, (
                    "expected the summary line's text to match MANUAL_SUMMARY_TEMPLATE with 2 total, "
                    "1 superseded")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with an empty manual-resolutions registry, render() emits no .manual-summary element and none of "
        "the retired management table's own copy; with two entries seeded (one superseded, one active), "
        ".manual-summary renders exactly once with text matching MANUAL_SUMMARY_TEMPLATE's total/superseded "
        "count (D-11, 14-06-PLAN.md Task 2 item 1)",
        _manual_summary_line_replaces_retired_management_table_copy)

    def _manual_section_supersession_symbols_retired_and_chip_still_renders():
        # Phase 14 plan 14-06 Task 2, item 2 (retargeted in place from
        # _manual_section_supersession_contract): the superseded card's
        # full attribute/note contract is already pinned by Task 1's own
        # _airline_card_html_superseded_shows_built_in_state_never_
        # operator_upload() check — this thin cross-reference only
        # proves the D-06 supersession machinery's now-orphaned symbols
        # are gone, and that the chip itself still renders end to end
        # via render(), so the two checks never test the identical
        # thing twice under different names.
        for name in ("SUPERSEDED_MARKER_TITLE", "SUPERSEDED_CAPTION", "SUPERSEDED_STATUS_CLASS"):
            if hasattr(airlines_page, name):
                return False, "expected airlines_page to no longer expose %r" % (name,)
        tmp = _mkstate("a-manual-supersession-retired")
        try:
            # AFR is a real static-table prefix (enrich._ICAO_AIRLINE_PREFIXES).
            manual_resolutions.add_entry(tmp, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
            rendered = airlines_page.render(_ctx(tmp))
            expected_chip = '<span class="airline-card__chip">%s</span>' % airlines_page.SUPERSEDED_MARKER_TEXT
            if expected_chip not in rendered:
                return False, "expected the Superseded chip to still render end to end via render()"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the retired D-06 supersession machinery's own symbols (SUPERSEDED_MARKER_TITLE, SUPERSEDED_CAPTION, "
        "SUPERSEDED_STATUS_CLASS) are gone, and the Superseded chip itself still renders end to end via "
        "render() — the card-level attribute/note contract is Task 1's own check's job, not re-tested here "
        "(14-06-PLAN.md Task 2 item 2)",
        _manual_section_supersession_symbols_retired_and_chip_still_renders)

    def _retired_management_table_symbols_are_gone():
        # Phase 14 plan 14-06 Task 2, item 3 (retargeted in place from
        # _manual_section_add_artwork_link_contract, whose own CR-02
        # add-artwork-link behaviour is now covered by
        # _airline_card_html_active_manual_states_render_expected_
        # attributes_and_chip() (Task 1) — the six retired rendering
        # functions and eight now-orphaned copy/class constants
        # _airlines_page_module_exposes_no_deleted_diagnostics_symbol()'s
        # own hasattr-scan shape is followed exactly, over a different
        # symbol list.
        for name in (
                "_manual_resolution_table_html", "_manual_resolution_cards_html",
                "_manual_resolution_row_html", "_manual_resolutions_section_html",
                "_manual_superseded_marker_html", "_manual_add_artwork_link_html",
                "MANUAL_SECTION_HEADING", "MANUAL_SECTION_CAPTION",
                "MANUAL_EMPTY_HEADING", "MANUAL_EMPTY_BODY",
                "MANUAL_RESOLUTION_HEADERS", "ADD_ARTWORK_LINK_TEXT",
                "SUPERSEDED_MARKER_TITLE", "SUPERSEDED_STATUS_CLASS",
        ):
            if hasattr(airlines_page, name):
                return False, (
                    "airlines_page module must no longer expose the retired management-table symbol %r" % name)
        return True, ""
    check(
        "importing companion.pages.airlines_page raises no error, and the module exposes none of the six "
        "retired management-table rendering functions or eight now-orphaned copy/class constants "
        "(14-06-PLAN.md Task 2 item 3)",
        _retired_management_table_symbols_are_gone)

    def _manual_section_seed_helper_end_to_end():
        # Phase 14 plan 14-01 Task 3: exercises the new
        # _seed_manual_resolutions() fixture helper end-to-end against
        # today's management table. Written to survive that table's own
        # retirement in plan 14-06 by asserting on
        # _manual_resolution_rows()'s tuples and the rendered airline
        # names, never on <table>/<tr> markup that plan deletes.
        tmp = _mkstate("a-seed-manual-resolutions-helper")
        try:
            # AFR is a real static-table prefix (enrich._ICAO_AIRLINE_PREFIXES,
            # same choice the existing supersession checks above make);
            # XQZ is not.
            _seed_manual_resolutions(tmp, [
                ("AFR", "Legacy Air France Ops"),
                ("XQZ", "Totally Novel Airline"),
            ])
            rendered = airlines_page.render(_ctx(tmp))
            if "Legacy Air France Ops" not in rendered:
                return False, "expected the AFR entry's airline name to appear in the rendered page"
            if "Totally Novel Airline" not in rendered:
                return False, "expected the XQZ entry's airline name to appear in the rendered page"

            registry = manual_resolutions.load_manual_resolutions(tmp)
            if set(registry.keys()) != {"AFR", "XQZ"}:
                return False, "expected the helper to seed exactly {AFR, XQZ}, got %r" % (sorted(registry),)

            rows = airlines_page._manual_resolution_rows(tmp, registry)
            superseded_by_prefix = {prefix: superseded for prefix, _, _, superseded, _ in rows}
            if superseded_by_prefix.get("AFR") is not True:
                return False, "expected AFR (a real static-table prefix) to report superseded=True"
            if superseded_by_prefix.get("XQZ") is not False:
                return False, "expected XQZ (not in the static table) to report superseded=False"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "_seed_manual_resolutions() seeds through manual_resolutions.add_entry() alone; both seeded "
        "airline names render on the Airlines page, and _manual_resolution_rows() reports superseded=True "
        "for exactly the static-table prefix (AFR) and False for the novel one (XQZ) (phase 14 plan 14-01 "
        "Task 3)",
        _manual_section_seed_helper_end_to_end)

    def _health_resolve_link_template_matches_airlines_route_constants():
        # WR-06: airlines_page.py's own comment above RESOLVE_ROUTE/
        # AIRLINES_ROUTE/RESOLVE_QUERY_PARAM/MANUAL_DELETE_ROUTE_PREFIX
        # claims these are "pinned by a cross-module equality check in
        # companion/test_status_pages.py" — no such check existed until
        # this one. health_page.RESOLVE_LINK_HREF_TEMPLATE
        # ("/airlines?resolve=%s") is a hand-written duplicate of
        # AIRLINES_ROUTE + "?" + RESOLVE_QUERY_PARAM + "=%s"; renaming
        # either constant without updating the other would silently break
        # D-10's per-row deep link (the only entry point into the whole
        # feature) behind a still-green suite. This check makes that
        # drift fail loudly instead.
        expected_template = "%s?%s=%%s" % (airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
        if health_page.RESOLVE_LINK_HREF_TEMPLATE != expected_template:
            return False, (
                "expected health_page.RESOLVE_LINK_HREF_TEMPLATE (%r) to equal %r, derived from "
                "airlines_page.AIRLINES_ROUTE + airlines_page.RESOLVE_QUERY_PARAM"
                % (health_page.RESOLVE_LINK_HREF_TEMPLATE, expected_template))
        return True, ""
    check(
        "health_page.RESOLVE_LINK_HREF_TEMPLATE equals the template derived from "
        "airlines_page.AIRLINES_ROUTE and airlines_page.RESOLVE_QUERY_PARAM — the cross-module equality "
        "check airlines_page.py's own comment already claims exists (WR-06)",
        _health_resolve_link_template_matches_airlines_route_constants)

    def _manual_delete_form_renders_in_both_dialog_and_no_js_fallback():
        # Phase 14 plan 14-06 Task 2, item 4 (retargeted in place from
        # _manual_section_delete_control_and_design_system_contract):
        # the D-09 amendment's permanent regression proof that this
        # phase's earlier plans built but never pinned with a lasting
        # check — one shared _manual_delete_form_html() function,
        # rendered at exactly two call sites (the dialog, always with
        # action=""; the no-JS fallback, with the real delete action)
        # whenever a manual entry exists for the prefix being viewed.
        tmp = _mkstate("a-manual-delete-two-call-sites")
        try:
            # A manual entry with no artwork yet (Step B reachable) —
            # the D-09 amendment's own precondition for the fallback
            # section to reach a branch that renders the delete form at
            # all.
            manual_resolutions.add_entry(tmp, "ZZZ", "Brand New Air", now="2026-01-01T00:00:00+00:00")
            ctx = _ctx(tmp)
            ctx["resolve_prefix"] = "ZZZ"
            rendered = airlines_page.render(ctx)

            dialog_open_index = rendered.index('id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID)
            dialog_close_index = rendered.index("</dialog>", dialog_open_index)
            dialog_section = rendered[dialog_open_index:dialog_close_index]
            fallback_section = rendered[dialog_close_index:]

            delete_form_re = re.compile(
                r'<form class="%s" method="post" action="([^"]*)">' % re.escape(airlines_page.LIGHTBOX_DELETE_CLASS))
            dialog_forms = delete_form_re.findall(dialog_section)
            if dialog_forms != [""]:
                return False, (
                    "expected exactly one delete form inside the shared dialog with action=\"\", got %r"
                    % (dialog_forms,))

            expected_action = airlines_page._manual_delete_action("ZZZ")
            fallback_forms = delete_form_re.findall(fallback_section)
            if fallback_forms != [expected_action]:
                return False, (
                    "expected exactly one delete form in the no-JS fallback section with action=%r, got %r"
                    % (expected_action, fallback_forms))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the D-09 amendment's permanent regression proof: rendering ?resolve={prefix} for a prefix with a "
        "manual entry produces exactly one _manual_delete_form_html() output inside the shared dialog "
        "(action=\"\") and exactly one inside the no-JS fallback section (the real delete action) — one "
        "shared function, two call sites (14-06-PLAN.md Task 2 item 4)",
        _manual_delete_form_renders_in_both_dialog_and_no_js_fallback)

    def _list_filter_js_gains_data_filter_set_hook():
        # Phase 14 (14-03-PLAN.md Task 1, RESEARCH.md Pitfall 5):
        # list-filter.js exposed exactly four attributes and no way for
        # an element elsewhere on the page to set the filter and re-run
        # it, so D-11's clickable summary line had no real mechanism to
        # drive. This pins the fix stays a single filtering
        # implementation, ES5-safe, and free of the file's own standing
        # network/timer bans — a source-level guard, since no harness
        # exercises client JS execution directly.
        js_path = os.path.join(HERE, "static", "list-filter.js")
        with open(js_path) as fh:
            js_source = fh.read()

        if "data-filter-set" not in js_source:
            return False, "expected the data-filter-set token in companion/static/list-filter.js"

        # Strip comment lines before any counting assertion, so the
        # header's own prose describing the new attribute cannot satisfy
        # or break a count.
        non_comment_source = "\n".join(
            line for line in js_source.splitlines()
            if not re.match(r'^\s*[/*]', line))

        if "[data-filter-set]" not in non_comment_source:
            return False, (
                "expected a querySelectorAll(\"[data-filter-set]\") lookup outside comments")

        handler_slice = non_comment_source[non_comment_source.index("[data-filter-set]"):]
        if "applyFilter()" not in handler_slice:
            return False, "expected the new [data-filter-set] handler to call applyFilter()"
        if 'getAttribute("data-filter-set")' not in handler_slice:
            return False, "expected the handler to read the clicked element's own data-filter-set attribute"

        # The single-filtering-implementation property: exactly one
        # [data-filter-text] QUERY (the bracketed attribute-selector
        # form), not a bare substring count — the existing
        # row.getAttribute("data-filter-text") read inside applyFilter()
        # is not a second query and must not make this count 2.
        text_query_count = non_comment_source.count("[data-filter-text]")
        if text_query_count != 1:
            return False, (
                "expected exactly one [data-filter-text] query, got %d" % text_query_count)

        if re.search(r'(^|[^A-Za-z_])(let|const) |=>', js_source):
            return False, "expected list-filter.js to stay inside the ES5-safe subset (no let/const/arrow)"

        if re.search(r'fetch\(|XMLHttpRequest|setTimeout|setInterval', non_comment_source):
            return False, "expected list-filter.js to introduce no network call or timer"

        return True, ""
    check(
        "companion/static/list-filter.js gains an optional, guarded [data-filter-set] lookup whose click "
        "handler sets the filter input's value from the clicked element's own attribute and calls the "
        "file's one existing applyFilter() — the file still has exactly one [data-filter-text] query, stays "
        "ES5-safe, and introduces no network call or timer (phase 14 plan 14-03 Task 1, RESEARCH.md Pitfall "
        "5, D-11's summary-line mechanism)",
        _list_filter_js_gains_data_filter_set_hook)

    def _phase14_task2_new_css_selectors_exhaustive():
        # Phase 14 (14-03-PLAN.md Task 2): the style.css DOM-contract
        # guard for every new/extended selector UI-SPEC's Component
        # Inventory names, and no more. Uses the same
        # index()-plus-window-slicing idiom this file's own cross-file
        # CSS guards already use (see
        # _quick_260901_tsa_css_dom_contract_guard above) — never a
        # regex CSS parser.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        def _rule_body(selector_open):
            # 24-04-PLAN.md Task 2: anchored at a LINE START, not by a
            # bare index(). Found by this plan breaking it: adding
            # `.battery-readout-row > .battery-readout { ... }` made the
            # plain index() resolve `.battery-readout {` to the TAIL of
            # that descendant rule and read the wrong body entirely —
            # the `.drawing-axis`-inside-`.drawing-axis-label` trap, met
            # from the other direction. Every selector these guards key
            # on opens its own rule at column 0, so requiring the
            # preceding newline distinguishes the rule from any rule
            # that merely ENDS with the same selector.
            start = css_source.index("\n" + selector_open) + 1
            brace_close = css_source.index("}", start)
            return css_source[start:brace_close]

        expectations = (
            ("a.airline-card {", ("display: block", "color: inherit", "text-decoration: none")),
            (".airline-card__placeholder {", (
                "border: 1px dashed var(--color-border)",
                "border-radius: var(--radius-control)",
                "background: var(--color-canvas)",
                "margin-bottom: var(--space-sm)",
                "display: block")),
            (".lightbox__heading:empty {", ("display: none",)),
            (".lightbox__manual-note:empty {", ("display: none",)),
        )
        for selector_open, expected_declarations in expectations:
            if selector_open not in css_source:
                return False, "expected style.css to declare %r" % (selector_open,)
            body = _rule_body(selector_open)
            for expected_declaration in expected_declarations:
                if expected_declaration not in body:
                    return False, (
                        "expected %r's rule body to contain %r" % (selector_open, expected_declaration))

        # 22-11-PLAN.md Task 2 (X7), retargeted in place. The
        # `.manual-summary {` base rule used to be pinned here with its
        # 70%-muted colour, underline and pointer — a byte-for-byte copy
        # of `.filter-bar [data-filter-clear]`'s property list, which is
        # exactly the 12px bare link the audit found unreadable as a
        # control. X7 replaces that copy with REUSE: the markup composes
        # `.airline-card__chip` (the page's own label-voice token) and
        # `.manual-summary` shrinks to the one thing a chip cannot carry,
        # a hover. The expectation is inverted rather than deleted — the
        # base rule must be GONE, so a future plan cannot quietly
        # reinstate the fork, and the reuse must be visible in the markup.
        if re.search(r"^\.manual-summary\s*\{", css_source, re.M):
            return False, (
                "expected the .manual-summary base rule to be gone — its property list was a copy "
                "of [data-filter-clear]'s, and the chip class now carries the treatment (X7)")
        if ".manual-summary:hover {" not in css_source:
            return False, "expected a .manual-summary:hover rule in style.css"
        hover_body = _rule_body(".manual-summary:hover {")
        if "color: var(--color-text)" not in hover_body:
            return False, "expected .manual-summary:hover to declare color: var(--color-text)"
        if "color-mix(in srgb, var(--color-text) 12%, transparent)" not in hover_body:
            return False, (
                "expected .manual-summary:hover to deepen to the chip's own 12% wash, not a newly "
                "invented strength")
        chip_body = _rule_body(".airline-card__chip {")
        for inherited in ("font-size: 12px", "text-transform: uppercase", "border-radius: 999px"):
            if inherited not in chip_body:
                return False, (
                    "expected .airline-card__chip to still carry %r — it is now the summary "
                    "control's whole treatment" % (inherited,))

        # .airline-card__placeholder's aspect-ratio must string-equal
        # .airline-card__image's, so grid rows stay aligned whether a
        # card holds art or a gap.
        image_ratio = re.search(r'aspect-ratio:\s*([^;]+);', _rule_body(".airline-card__image {"))
        placeholder_ratio = re.search(r'aspect-ratio:\s*([^;]+);', _rule_body(".airline-card__placeholder {"))
        if not image_ratio or not placeholder_ratio:
            return False, "expected both .airline-card__image and .airline-card__placeholder to declare aspect-ratio"
        if image_ratio.group(1) != placeholder_ratio.group(1):
            return False, (
                "expected .airline-card__placeholder's aspect-ratio (%r) to string-equal "
                ".airline-card__image's (%r)" % (placeholder_ratio.group(1), image_ratio.group(1)))

        # The three-way group: .lightbox__replace's own selector list
        # must now also name .lightbox__resolve-name and
        # .lightbox__delete, in exactly one declaration block — extend
        # the selector, never duplicate it, matching this file's own
        # .lightbox__replace-zone, .resolve-upload-zone precedent.
        #
        # 14-08 on-glass fix (2026-09-06): each selector now carries
        # `:not([hidden])` (a real-browser check found `display: block`
        # here winning its specificity tie against the UA stylesheet's
        # `[hidden] { display: none }`, so `hidden = true` stopped
        # hiding these forms the moment Phase 14 started toggling them
        # at runtime) — retargeted in place, same check, same intent.
        group_selector = (
            ".lightbox__replace:not([hidden]),\n"
            ".lightbox__resolve-name:not([hidden]),\n"
            ".lightbox__delete:not([hidden]) {"
        )
        if css_source.count(group_selector) != 1:
            return False, (
                "expected the exact three-way selector group %r exactly once in style.css, got %d"
                % (group_selector, css_source.count(group_selector)))
        group_body = _rule_body(group_selector)
        for expected_declaration in ("display: block", "padding-top: var(--space-md)", "min-width: 0"):
            if expected_declaration not in group_body:
                return False, "expected the three-way group's rule body to contain %r" % (expected_declaration,)
        # .lightbox__delete:not([hidden]) { (its own standalone rule)
        # must not exist — confirms the selector was extended, not
        # duplicated.
        if css_source.count(".lightbox__delete:not([hidden]) {") != 1:
            return False, (
                "expected .lightbox__delete:not([hidden]) { to appear exactly once "
                "(inside the shared group only), got %d"
                % css_source.count(".lightbox__delete:not([hidden]) {"))

        # Zero new accent consumer: the exhaustive header
        # accent-reservation list (the file's first block comment) must
        # mention none of this plan's new selector/class names.
        header = css_source[:css_source.index("*/")]
        for new_name in (
                "a.airline-card", "airline-card__placeholder", "lightbox__heading",
                "lightbox__manual-note", "manual-summary", "lightbox__resolve-name",
                "lightbox__delete"):
            if new_name in header:
                return False, (
                    "expected the header accent-reservation list to not mention %r — this plan "
                    "adds zero new accent consumers" % (new_name,))

        # Zero new custom property: none of this plan's own new/extended
        # rule bodies declares a `--` custom property.
        for selector_open in (
                "a.airline-card {", ".airline-card__placeholder {", ".lightbox__heading:empty {",
                ".lightbox__manual-note:empty {", ".manual-summary:hover {",
                group_selector):
            body = _rule_body(selector_open)
            if re.search(r'(^|\s)--[a-z][a-z-]*:', body):
                return False, "expected %r's rule body to declare no new custom property" % (selector_open,)

        # Phase 14 plan 14-06 Task 2 retires the management table's own
        # rendering functions and, with them, this now-orphaned
        # selector — retargeted in place (this check itself, not a new
        # one) from "still declared" to "gone" now that the retirement
        # has actually landed.
        if "manual-resolution__status--superseded" in css_source:
            return False, "expected .manual-resolution__status--superseded to be gone (phase 14 plan 14-06 Task 2)"

        return True, ""
    check(
        "style.css declares the new/extended selectors UI-SPEC's Component Inventory enumerates "
        "(a.airline-card, .airline-card__placeholder, .lightbox__heading:empty, "
        ".lightbox__manual-note:empty) with their exact declaration values, .manual-summary's own "
        "base rule is GONE with only its hover surviving on the chip's own 12% wash (X7, "
        "22-11-PLAN.md Task 2 — the copied [data-filter-clear] property list is replaced by reuse "
        "of .airline-card__chip, whose label-voice declarations are pinned here instead), "
        ".airline-card__placeholder's aspect-ratio string-equals .airline-card__image's, "
        ".lightbox__replace's selector is extended to a three-way group with "
        ".lightbox__resolve-name/.lightbox__delete in exactly one declaration block (never duplicated), "
        "the header accent-reservation list mentions none of the new selectors, none of the new/extended "
        "rule bodies declares a new custom property, and .manual-resolution__status--superseded is gone "
        "now that plan 14-06 has retired it (phase 14 plan 14-03 Task 2, retargeted in place by 14-06 Task 2)",
        _phase14_task2_new_css_selectors_exhaustive)

    # ======================================================================
    # 22-04-PLAN.md Task 1 (D-03/CFG-26, X2): the Frame strip reads the one
    # frame_state.resolve_state() result instead of re-deriving lateness
    # ======================================================================

    def _frame_strip_ctx(last_checkin_ts, device_config, now):
        return {
            "last_checkin_ts": last_checkin_ts, "device_config": device_config, "now": now,
        }

    def _frame_strip_update_cell_slice(rendered):
        # The update cell is always the LAST child of `.frame-strip__cells`
        # (rendered after both switch cells, or omitted entirely) — so its
        # own opening tag through the end of the string, minus the two
        # closing `</div>` tags for `.frame-strip__cells` and `.frame-strip`
        # itself, is exactly this cell's own markup (nested nested divs
        # inside it make a naive "next </div>" search find the wrong,
        # innermost closing tag instead).
        marker = '<div class="frame-strip__cell frame-strip__cell--update">'
        if marker not in rendered:
            return None
        start = rendered.index(marker)
        closing = "</div></div>"
        if not rendered.endswith(closing):
            return None
        return rendered[start:-len(closing)]

    def _frame_strip_nightly_regression_held_is_neutral_never_warn():
        # The exact X2 nightly false alarm (22-UI-SPEC.md §3.3 rule 6):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00,
        # Europe/Paris (a non-DST date) — the strip must render the held
        # copy with the neutral dot, no warn anywhere in its markup.
        paris = timezone(timedelta(hours=1))
        qh_config = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
        ctx = _frame_strip_ctx(checkin.isoformat(), qh_config, clock.isoformat())
        rendered = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        cell = _frame_strip_update_cell_slice(rendered)
        if cell is None:
            return False, "expected an update cell to render for a held frame"
        if "dot--off" not in cell:
            return False, "expected the held headline to carry the neutral dot--off"
        for warn_token in (
                "dot--warn", "stat-tile--warn", "status-card__headline--warn",
                "Expected since", "Attendu depuis"):
            if warn_token in rendered:
                return False, "expected zero %r in a held render, found it" % (warn_token,)
        if "Next wake around" not in cell:
            return False, "expected the held headline wording"
        return True, ""
    check(
        "the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/"
        "Paris): the Frame strip renders the held copy with the neutral dot--off and zero warn/"
        "error tokens anywhere, including no 'Expected since'/'Attendu depuis' (X2, D-03/CFG-26)",
        _frame_strip_nightly_regression_held_is_neutral_never_warn)

    def _frame_strip_due_is_identical_inside_and_outside_the_grace_window():
        # 22-UI-SPEC.md §3.3 rule 3: the grace window is invisible — the
        # SAME "Next update ≈ HH:MM" copy and classes render whether now
        # is before next_wake or up to 2x the effective interval past it.
        #
        # 23-06-PLAN.md Task 2: RETARGETED IN PLACE, and the reason is
        # worth stating because it looks like a weakening and is not.
        # This check compared the WHOLE update cell byte for byte between
        # two values of `now`, which was the same thing as "the grace
        # window is invisible" only while the cell held nothing but a
        # clock. D1's countdown is a DURATION, so it differs between any
        # two instants by construction — "in 5m" at 11:10 and "in 1m" at
        # 11:14 are the same state reported twice, not two states. What
        # rule 3 actually forbids is a STATE SIGNAL that differs, so that
        # is what is compared now: the cell with the countdown element
        # removed must be byte-identical, the countdown's own instant
        # must be the same instant in both (the wake does not move inside
        # its grace window), and neither rendering may carry a warn, late
        # or overdue token anywhere. That last clause is NEW and is
        # stricter than what it replaces.
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        checkin_iso = "2026-08-27T11:00:00+00:00"
        before_ctx = _frame_strip_ctx(checkin_iso, device_cfg, "2026-08-27T11:10:00+00:00")
        inside_grace_ctx = _frame_strip_ctx(checkin_iso, device_cfg, "2026-08-27T11:40:00+00:00")
        rendered_before = _frame_strip_update_cell_slice(
            layout.frame_strip_html(before_ctx, return_to=layout.HOME_ROUTE))
        rendered_inside_grace = _frame_strip_update_cell_slice(
            layout.frame_strip_html(inside_grace_ctx, return_to=layout.HOME_ROUTE))
        if rendered_before is None or rendered_inside_grace is None:
            return False, "expected an update cell to render in both the before and grace fixtures"
        countdown_re = re.compile(r"<time [^>]*>.*?</time>", re.S)
        without_before = countdown_re.sub("", rendered_before)
        without_grace = countdown_re.sub("", rendered_inside_grace)
        if without_before != without_grace:
            return False, (
                "expected identical copy and classes before and inside the grace window, got %r "
                "vs %r" % (without_before, without_grace))
        instants = []
        for rendered in (rendered_before, rendered_inside_grace):
            element = re.search(r'<time datetime="([^"]*)"([^>]*)>(.*?)</time>',
                                rendered, flags=re.S)
            if element is None:
                return False, (
                    "expected the countdown element in BOTH renderings — an element that "
                    "disappears once its instant passes is itself a visible grace window, got %r"
                    % (rendered,))
            instants.append(element.group(1))
            if layout.RELATIVE_COUNTDOWN_ATTR not in element.group(2):
                return False, "expected the countdown to stay marked as one in both renderings"
        if instants[0] != instants[1]:
            return False, (
                "expected the countdown to tick toward the SAME instant in both renderings — the "
                "wake does not move inside its own grace window, got %r vs %r"
                % (instants[0], instants[1]))
        for rendered, label in ((rendered_before, "before"),
                                (rendered_inside_grace, "inside grace")):
            for token in ("warn", "late", "overdue", "Expected since"):
                if token in rendered:
                    return False, (
                        "the %s rendering carries %r — a frame inside its grace window is not a "
                        "fault, and X2's nightly false alarm is what happens when it is painted "
                        "as one, got %r" % (label, token, rendered))
        if "dot--ok" not in rendered_before:
            return False, "expected the due headline to carry dot--ok"
        return True, ""
    check(
        "a due result renders byte-identical copy and classes whether 'now' is before next_wake "
        "or up to 2x the effective interval past it — the grace window is invisible (22-UI-SPEC.md "
        "§3.3 rule 3) — with the countdown present in both renderings, marked, pointed at the same "
        "instant, and neither rendering carrying a warn/late/overdue token anywhere (retargeted in "
        "place by 23-06-PLAN.md Task 2, which added the one element in that cell that is a "
        "function of `now` by construction)",
        _frame_strip_due_is_identical_inside_and_outside_the_grace_window)

    def _frame_strip_late_result_carries_warn_dot_and_plain_text_colour_class():
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        # 11:00 + 900s = 11:15 due; 2x grace = 1800s -> late from 11:45.
        ctx = _frame_strip_ctx(
            "2026-08-27T11:00:00+00:00", device_cfg, "2026-08-27T12:00:00+00:00")
        rendered = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        cell = _frame_strip_update_cell_slice(rendered)
        if cell is None:
            return False, "expected an update cell to render for a late frame"
        if "dot--warn" not in cell:
            return False, "expected the late headline to carry the warn dot"
        if "Expected since" not in cell:
            return False, "expected the late headline wording"
        if 'status-card__headline status-card__headline--warn' not in cell:
            return False, "expected the headline's own --warn class hook"
        return True, ""
    check(
        "a late result renders the warn dot and 'Expected since HH:MM', with the headline's own "
        "text-colour class staying the plain status-card__headline--warn hook (never a status "
        "colour as text, 22-UI-SPEC.md §3.3 rule 2)",
        _frame_strip_late_result_carries_warn_dot_and_plain_text_colour_class)

    # Quick task 260923-fr4 (battery-empty-screen-before-the-pack-die):
    # the parked twin of the check immediately above - same shape as the
    # frame-silent notifier's own parked/unparked control pair
    # (server/test_poll_loop.py): wake_interval_s 300 (5 min), a
    # check-in 20 minutes ago. Unparked, that crosses the 900s (3 x 300)
    # warn threshold and is late - the control below, proving this setup
    # genuinely does trigger lateness at a cadence the check above never
    # exercises. Parked (ctx["battery_critical"]=True), the 3600s
    # BATTERY_CRITICAL_SLEEP_S-derived cadence puts the same check-in
    # nowhere near its own warn threshold, so the strip must show no late
    # state at all.
    def _frame_strip_parked_suppresses_late_state():
        device_cfg = {"wake_interval_s": 300, "display_enabled": True}
        now = "2026-08-27T12:20:00+00:00"
        checkin = "2026-08-27T12:00:00+00:00"  # 20 minutes before `now`

        control_ctx = _frame_strip_ctx(checkin, device_cfg, now)
        control_rendered = layout.frame_strip_html(control_ctx, return_to=layout.HOME_ROUTE)
        control_cell = _frame_strip_update_cell_slice(control_rendered)
        if control_cell is None or "dot--warn" not in control_cell:
            return False, (
                "control (not parked): expected the late state at wake_interval_s=300 with a "
                "20-minute-old check-in, got %r" % (control_rendered,)
            )

        parked_ctx = _frame_strip_ctx(checkin, device_cfg, now)
        parked_ctx["battery_critical"] = True
        parked_rendered = layout.frame_strip_html(parked_ctx, return_to=layout.HOME_ROUTE)
        parked_cell = _frame_strip_update_cell_slice(parked_rendered)
        if parked_cell is not None:
            for token in ("dot--warn", "Expected since", "status-card__headline--warn"):
                if token in parked_cell:
                    return False, (
                        "parked: expected no late state with battery_critical=True, found %r in %r"
                        % (token, parked_cell)
                    )
        return True, ""
    check(
        "with a parked frame (ctx['battery_critical']=True), wake_interval_s 300 and a 20-minute-old "
        "check-in, the frame strip does NOT show the late state - the identical setup without the "
        "park does (quick task 260923-fr4)",
        _frame_strip_parked_suppresses_late_state)

    def _frame_strip_no_checkin_renders_no_update_cell_and_claims_no_state():
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        ctx = _frame_strip_ctx(None, device_cfg, "2026-08-27T12:00:00+00:00")
        rendered = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        if "frame-strip__cell--update" in rendered or "status-card__headline" in rendered:
            return False, "expected no update cell and no headline when there is no check-in yet"
        return True, ""
    check(
        "the Frame strip renders no update headline and claims no state when there is no check-in "
        "recorded at all (frame_state.STATE_UNKNOWN)",
        _frame_strip_no_checkin_renders_no_update_cell_and_claims_no_state)

    def _frame_strip_three_cells_share_one_row_structure_switch_cells_keep_left_edge():
        # B13: every cell — both switches and the update cell — shares
        # the SAME three-row internal grid (label/state/caption row
        # classes byte-identical across all three); only the two switch
        # cells' OUTER wrapper carries the quick-action--on/off
        # control-state left edge, never the update cell.
        device_cfg = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        ctx = _frame_strip_ctx("2026-08-27T11:00:00+00:00", device_cfg, "2026-08-27T11:10:00+00:00")
        rendered = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        # `frame-strip__cell` is the FIRST space-separated class token on
        # every cell wrapper (both switches and update alike) — matched
        # this way (not a bare substring search) so the plural container
        # `frame-strip__cells` is never mistaken for a fourth cell.
        # 23-07-PLAN.md Task 1: retargeted in place from
        # r'<div class="([^"]*)">' — the two switch cells' wrappers now
        # carry layout.QUICK_SWITCH_REGION_ATTR after their class
        # attribute (the region companion/static/quick-switch.js marks
        # pending), so a pattern requiring `>` immediately after the
        # closing quote saw one cell instead of three. The class list
        # this check is actually about is unchanged; only what may
        # follow it is.
        cell_open_re = re.compile(r'<div class="([^"]*)"[^>]*>')
        cells = [
            cls for cls in cell_open_re.findall(rendered)
            if cls.split(" ")[0] == "frame-strip__cell"]
        if len(cells) != 3:
            return False, "expected exactly three frame-strip__cell wrappers, got %d (%r)" % (
                len(cells), cells)
        row_class_re = re.compile(r'<div class="(frame-strip__row[^"]*)">')
        # Slice the rendered strip into per-cell fragments so each cell's
        # own three row classes are compared, not a flattened file-wide list.
        cell_starts = [
            m.start() for m in cell_open_re.finditer(rendered)
            if m.group(1).split(" ")[0] == "frame-strip__cell"]
        cell_starts.append(len(rendered))
        row_class_sets = []
        for i in range(3):
            fragment = rendered[cell_starts[i]:cell_starts[i + 1]]
            row_classes = row_class_re.findall(fragment)
            if len(row_classes) != 3:
                return False, "expected exactly three row divs per cell, got %d in %r" % (
                    len(row_classes), fragment)
            row_class_sets.append(row_classes)
        if row_class_sets[0] != row_class_sets[1] or row_class_sets[1] != row_class_sets[2]:
            return False, "expected byte-identical row-class lists across all three cells, got %r" % (
                row_class_sets,)
        update_cell = cells[2]
        if "quick-action--on" in update_cell or "quick-action--off" in update_cell:
            return False, "expected the update cell to never carry the switch cells' left-edge class"
        if not (cells[0].count("quick-action--on") + cells[0].count("quick-action--off") == 1
                and cells[1].count("quick-action--on") + cells[1].count("quick-action--off") == 1):
            return False, "expected each switch cell to keep its own control-state left edge"
        return True, ""
    check(
        "all three Frame-strip cells share one wrapper and one three-row internal grid (identical "
        "row-class lists), while only the two switch cells' outer wrapper keeps the quick-action--"
        "on/off control-state left edge (B13)",
        _frame_strip_three_cells_share_one_row_structure_switch_cells_keep_left_edge)

    def _frame_strip_both_switch_forms_carry_data_quick_switch_exactly_twice():
        # D-04 handshake (22-05-PLAN.md Task 3, same wave): the stable
        # hook that plan's leave-guard suppression keys on.
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        ctx = _frame_strip_ctx("2026-08-27T11:00:00+00:00", device_cfg, "2026-08-27T11:10:00+00:00")
        rendered = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
        count = rendered.count("data-quick-switch")
        if count != 2:
            return False, "expected exactly 2 occurrences of data-quick-switch, got %d" % count
        return True, ""
    check(
        "a rendered Frame strip contains exactly 2 occurrences of the literal attribute "
        "data-quick-switch, one on each strip switch form (D-04 handshake with plan 22-05)",
        _frame_strip_both_switch_forms_carry_data_quick_switch_exactly_twice)

    def _frame_strip_no_re_derived_lateness_in_source():
        source_path = os.path.join(HERE, "layout.py")
        with open(source_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        if "age_seconds(next_wake" in source:
            return False, "expected layout.py to never re-derive lateness via age_seconds(next_wake...)"
        return True, ""
    check(
        "companion/layout.py no longer computes an age_seconds(next_wake...) >= 0 warn trigger — "
        "the strip consumes frame_state.resolve_state(), it never re-derives lateness (CFG-26)",
        _frame_strip_no_re_derived_lateness_in_source)

    # ======================================================================
    # 22-04-PLAN.md Task 2 (B13, C2, C6, T9, C5): the strip's CSS — stretch
    # cells, quiet strip buttons, the demoted headline, the repaired tile
    # hover, and the one time-value role. Block-scoped source checks only —
    # a line-wise grep pipe cannot see that a declaration belongs to a
    # selector, so every check here slices the rule BLOCK first.
    # ======================================================================

    def _css_source():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            return fh.read()

    def _block(css_source, selector_needle, opening="{"):
        start = css_source.index(selector_needle)
        brace_open = css_source.index(opening, start)
        depth = 1
        i = brace_open + 1
        while depth > 0:
            nxt_open = css_source.find("{", i)
            nxt_close = css_source.find("}", i)
            if nxt_close == -1:
                raise ValueError("unterminated block for %r" % (selector_needle,))
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open + 1
            else:
                depth -= 1
                i = nxt_close + 1
        return css_source[start:i]

    def _frame_strip_cells_stretch_not_center():
        css_source = _css_source()
        block = _block(css_source, ".frame-strip__cells {")
        if "align-items: stretch" not in block:
            return False, "expected align-items: stretch inside .frame-strip__cells"
        if "align-items: center" in block:
            return False, "expected zero align-items: center inside .frame-strip__cells"
        return True, ""
    check(
        "the .frame-strip__cells block declares align-items: stretch and zero align-items: center "
        "(B13) — a block-scoped check, since a line-wise grep pipe would already read 0 on the "
        "unmodified file (the selector and declaration sit on different lines) and pass vacuously",
        _frame_strip_cells_stretch_not_center)

    def _frame_strip_cell_button_quiet_rule_after_submit_no_important_no_id():
        css_source = _css_source()
        submit_pos = css_source.index('button[type="submit"] {')
        rule_pos = css_source.index(".frame-strip__cell button {")
        if rule_pos <= submit_pos:
            return False, "expected .frame-strip__cell button to appear AFTER button[type=\"submit\"]"
        block = _block(css_source, ".frame-strip__cell button {")
        if "!important" in block:
            return False, "expected no !important in the quiet strip-button rule"
        if "#" in block.split("{", 1)[0]:
            return False, "expected no id selector in the quiet strip-button rule's own selector"
        for expected in (
                "color-mix(in srgb, var(--color-text) 4.5%, transparent)",
                "color-mix(in srgb, var(--color-text) 9%, transparent)",
                "box-shadow: none"):
            if expected not in block:
                return False, "expected the base quiet wash value %r reused verbatim" % (expected,)
        return True, ""
    check(
        "the .frame-strip__cell button quiet-button rule (C2) appears at a later line than "
        "button[type=\"submit\"], carries no !important and no id selector, and reuses the base "
        "quiet wash (4.5%/9%) verbatim — never a new wash value (T-22-13)",
        _frame_strip_cell_button_quiet_rule_after_submit_no_important_no_id)

    def _stat_tile_hover_three_edge_frame_strip_excluded():
        css_source = _css_source()
        block = _block(css_source, ".stat-tile:not(.frame-strip):hover")
        if "border-color: transparent" in block:
            return False, "expected zero border-color: transparent inside the .stat-tile hover block"
        if "border-inline-color" not in block or "border-block-end-color" not in block:
            return False, (
                "expected both border-inline-color and border-block-end-color inside the "
                ".stat-tile hover block")
        if ":not(.frame-strip)" not in block.split("{", 1)[0]:
            return False, "expected the hover reveal to be :not(.frame-strip)-scoped (T9)"
        return True, ""
    check(
        "the .stat-tile hover/focus-within block declares zero border-color: transparent and both "
        "border-inline-color and border-block-end-color (T9: the top status/accent rail survives "
        "hover), and the whole reveal is :not(.frame-strip)-scoped so the strip never lifts",
        _stat_tile_hover_three_edge_frame_strip_excluded)

    def _frame_strip_update_headline_no_heading_size_override():
        css_source = _css_source()
        if ".frame-strip__cell--update .status-card__headline" in css_source:
            return False, "expected the retired Phase 21 heading-size override to be gone (C6)"
        return True, ""
    check(
        "the Phase 21 .frame-strip__cell--update .status-card__headline heading-size override is "
        "gone — the line returns to its own 16px semibold Emphasis base (C6)",
        _frame_strip_update_headline_no_heading_size_override)

    def _time_value_role_defined_once():
        css_source = _css_source()
        block = _block(css_source, ".time-value {")
        for expected in ("var(--font-ui)", "font-variant-numeric: tabular-nums"):
            if expected not in block:
                return False, "expected %r inside the .time-value block" % (expected,)
        primary_block = _block(css_source, ".time-value--primary {")
        if "var(--font-body-size)" not in primary_block or "var(--weight-semibold)" not in primary_block:
            return False, "expected the primary modifier to use body-size + semibold (C5)"
        return True, ""
    check(
        "the one .time-value role (C5) declares --font-ui and tabular-nums, with a --primary "
        "modifier stepping up to body-size + semibold — no new token, no new family, no new size",
        _time_value_role_defined_once)

    def _accent_reservation_header_comment_no_longer_lists_strip_buttons():
        css_source = _css_source()
        header_end = css_source.index("*/")
        header = css_source[:header_end]
        if "Frame strip's two switch buttons" not in header:
            return False, "expected the header comment to record the C2 accent-reservation delta"
        if "this list LOSES two entries and gains none" not in header:
            return False, "expected the header comment to state the arithmetic, not just assert it"
        return True, ""
    check(
        "the style.css header comment's accent-reservation list is edited to record C2's delta "
        "(the Frame strip's two switch buttons are no longer accent-filled) — the arithmetic is "
        "written into the comment, not merely asserted (22-UI-SPEC.md §1)",
        _accent_reservation_header_comment_no_longer_lists_strip_buttons)

    # ======================================================================
    # 22-14-PLAN.md Task 1 (X9, D-10, 22-UI-SPEC.md §3.1): the bottom tab
    # bar's own geometry, surface, active idiom and page clearance, read
    # from the real stylesheet block by block — plus its French labels.
    # ======================================================================

    _TAB_BAR_BANNER = "The bottom tab bar (X9, 22-14-PLAN.md Task 1"

    def _tab_bar_css_geometry_surface_and_active_idiom():
        css_source = _css_source()
        region = css_source[css_source.index(_TAB_BAR_BANNER):]

        # The bar is OFF by default and only switched on below 960px, so
        # a desktop that never matches the query can never show it.
        base = _block(region, ".tab-bar {\n  display: none;")
        if "display: none" not in base:
            return False, "expected the base .tab-bar rule to be display: none"
        for banned in ("position:", "z-index", "bottom:"):
            if banned in base:
                return False, (
                    "expected the base .tab-bar rule to carry layout only inside the "
                    "media query, found %r" % (banned,))

        if "@media (max-width: 959.98px) {" not in region:
            return False, (
                "expected the tab bar to be scoped to the same fractional 959.98px "
                "boundary the sibling sub-960px rules already use")

        fixed = _block(region, ".tab-bar {\n    display: flex;")
        for needle in (
                "position: fixed", "left: 0", "right: 0", "bottom: 0",
                "z-index: 20",
                "padding-bottom: env(safe-area-inset-bottom, 0px)",
                "background: var(--color-secondary)",
                "border-top: 1px solid var(--color-border)",
                "box-shadow: var(--shadow-card-hover)"):
            if needle not in fixed:
                return False, "expected %r in the tab bar's own rule" % (needle,)
        # NO radius: --radius-card is for floating elements that do not
        # touch the viewport edge, and this bar is anchored to three.
        if "border-radius" in fixed or "radius-card" in fixed:
            return False, (
                "an edge-anchored bar must declare no border radius, got %r" % (fixed,))

        link = _block(region, ".tab-bar__link {")
        for needle in ("flex: 1 1 0", "height: 56px", "color: var(--color-text)"):
            if needle not in link:
                return False, "expected %r in .tab-bar__link" % (needle,)

        # The one active-signal idiom, byte-for-byte the same wash
        # .sidebar-link--active already declares — reused, not reinvented.
        wash = "color-mix(in srgb, var(--color-accent) 12%, transparent)"
        sidebar_active = _block(css_source, ".sidebar-link--active {")
        if wash not in sidebar_active:
            return False, (
                "expected .sidebar-link--active to still carry the 12%% accent wash this "
                "check compares against, got %r" % (sidebar_active,))
        active_pill = _block(region, ".tab-bar__link--active .tab-bar__pill {")
        if wash not in active_pill:
            return False, (
                "expected the active tab to reuse the app's one active-pill wash verbatim, "
                "got %r" % (active_pill,))
        active_text = _block(region, ".tab-bar__link--active {")
        for needle in ("color: var(--color-accent)",
                       "font-weight: var(--weight-semibold)"):
            if needle not in active_text:
                return False, "expected %r in .tab-bar__link--active" % (needle,)

        # The inactive hover must be :not()-scoped. An unscoped hover at
        # equal specificity, later in source, would erase the active tint
        # the instant the pointer crossed it — the exact failure
        # references/control-density.md names.
        hover_selector = ".tab-bar__link:not(.tab-bar__link--active):hover .tab-bar__pill {"
        if hover_selector not in region:
            return False, (
                "expected the inactive hover to be :not(.tab-bar__link--active)-scoped")
        if region.index(hover_selector) < region.index(
                ".tab-bar__link--active .tab-bar__pill {"):
            return False, (
                "expected the :not()-scoped hover to sit after the active rule in source "
                "order, so the cascade cannot be read backwards")
        for bad in (".tab-bar__link:hover {", ".tab-bar__link:hover .tab-bar__pill {"):
            if bad in region:
                return False, "expected no unscoped tab hover rule (%r)" % (bad,)

        # 11px regular, sentence case, explicitly NOT the label voice.
        label = _block(region, ".tab-bar__label {")
        if "font-size: 11px" not in label:
            return False, "expected the 11px sub-scale label size"
        if "font-weight: var(--weight-regular)" not in label:
            return False, "expected a regular-weight label"
        for voice in ("text-transform", "letter-spacing"):
            if voice in label:
                return False, (
                    "a nav destination is a destination, not a label — %r must not appear "
                    "on .tab-bar__label" % (voice,))

        # The last card must never sit under the bar, and the clearance
        # is reserved only on a page that really has one.
        clearance = _block(region, ".has-tab-bar .page-content {")
        for needle in ("padding-bottom", "56px", "env(safe-area-inset-bottom, 0px)"):
            if needle not in clearance:
                return False, "expected %r in the page-foot clearance rule" % (needle,)
        if layout.TAB_BAR_BODY_CLASS != "has-tab-bar":
            return False, (
                "the clearance selector and layout.TAB_BAR_BODY_CLASS must name the same "
                "class, got %r" % (layout.TAB_BAR_BODY_CLASS,))
        return True, ""
    check(
        "the tab bar is display:none until the 959.98px boundary, then fixed to the viewport bottom at "
        "56px plus the safe-area inset on the nav surface with a top hairline, the resting overlay shadow "
        "and NO border radius (it is edge-anchored); its cells are `flex: 1 1 0`; its active state reuses "
        "the app's one 12%-accent-wash pill idiom byte-for-byte with a :not()-scoped hover placed after it; "
        "its label is 11px regular with no label voice; and .has-tab-bar clears the bar at the page foot "
        "(X9/D-10, 22-14-PLAN.md Task 1)",
        _tab_bar_css_geometry_surface_and_active_idiom)

    # ======================================================================
    # 29-02-PLAN.md (CFG-82): the 2026-09-17 audit measured "Compagnies"
    # (10 characters) needing 65px at .tab-bar__label's 11px size, against
    # only 62px available in a 78px cell once the pill's old 8px-per-side
    # margin was subtracted — the label truncated. This check re-derives
    # every one of those numbers from the stylesheet's own live source
    # (never hardcoding 8, 65 or 78) and proves the fit as a
    # RELATIONSHIP, plus proves the 78x56px cell itself is untouched by
    # the margin edit, as a SEPARATE, independently-mutable assertion.
    # ======================================================================

    def _tab_bar_pill_horizontal_margin_lets_the_longest_label_fit():
        css_source = _css_source()
        region = css_source[css_source.index(_TAB_BAR_BANNER):]

        tokens = dict(re.findall(r"--(space-[a-z]+):\s*(\d+)px", css_source))

        pill = _block(region, ".tab-bar__pill {")
        # Accepts either the shipped `calc(var(--space-xs) / N)` form or a
        # plain `var(--space-sm)` form (mutation A below reverts to the
        # latter) — both are resolved through the SAME token map, never
        # hardcoded, so either form's real pixel value drives the check.
        margin_match = re.search(
            r"margin:\s*var\(--([a-z-]+)\)\s+(?:var\(--([a-z-]+)\)|"
            r"calc\(var\(--([a-z-]+)\)\s*/\s*(\d+)\))",
            pill)
        if not margin_match:
            return False, "could not parse .tab-bar__pill's margin shorthand: %r" % (pill,)
        _vertical_token, plain_token, calc_token, divisor = margin_match.groups()
        if plain_token:
            if plain_token not in tokens:
                return False, "margin shorthand referenced an unknown token %r" % (plain_token,)
            horizontal_margin_px = float(tokens[plain_token])
        else:
            if calc_token not in tokens:
                return False, "margin shorthand referenced an unknown token %r" % (calc_token,)
            horizontal_margin_px = float(tokens[calc_token]) / float(divisor)

        # The cell's own resolved box, asserted independently of the
        # margin above: mutating this must fail on its own, proving the
        # tap-area invariant is not merely a side effect of the fit math.
        link = _block(region, ".tab-bar__link {")
        height_match = re.search(r"height:\s*(\d+)px", link)
        if not height_match or int(height_match.group(1)) != 56:
            return False, (
                "expected .tab-bar__link's own resolved height to stay 56px (the 78x56px cell, "
                "unchanged by the pill's margin edit), got %r" % (link,))
        if "flex: 1 1 0" not in link:
            return False, (
                "expected .tab-bar__link's own width basis (flex: 1 1 0) to stay byte-identical "
                "to its pre-task value, got %r" % (link,))

        label_block = _block(region, ".tab-bar__label {")
        font_size_match = re.search(r"font-size:\s*(\d+)px", label_block)
        if not font_size_match or int(font_size_match.group(1)) != 11:
            return False, (
                "expected .tab-bar__label's font-size to still resolve to 11px, got %r"
                % (label_block,))

        unlabelled_entries = [
            (route, label) for group_label, entries in layout.NAV_GROUPS if not group_label
            for route, label in entries]
        cell_count = len(unlabelled_entries) + 1  # the everyday destinations plus one "More" cell

        # The app's own contract floor (design_direction: "Minimum
        # supported viewport width: 360 px") is the tightest case a
        # smaller viewport gives a smaller cell, so this is the worst
        # width the fit must survive, not merely the audit's own 390px
        # device — a check passing only at 390px could still truncate at
        # the app's actual supported floor.
        FLOOR_VIEWPORT_PX = 360
        cell_width_px = FLOOR_VIEWPORT_PX / cell_count
        available_px = cell_width_px - (2 * horizontal_margin_px)

        # The longest label across BOTH shipped languages — read from
        # layout.NAV_GROUPS and companion.i18n_fr.nav.CATALOG, never
        # typed literally, so a future longer label re-runs this same
        # arithmetic rather than silently going unchecked.
        candidate_labels = []
        for _route, label in unlabelled_entries:
            candidate_labels.append(label)
            candidate_labels.append(i18n_fr_nav.CATALOG.get(label, label))
        candidate_labels.append(layout.TAB_BAR_MORE_LABEL)
        candidate_labels.append(
            i18n_fr_nav.CATALOG.get(layout.TAB_BAR_MORE_LABEL, layout.TAB_BAR_MORE_LABEL))
        longest_label = max(candidate_labels, key=len)

        # Per-character advance: MEASURED, not modelled — the audit's own
        # real-browser figure for "Compagnies" (10 characters) needing
        # 65px at this 11px font-size gives 65 / 10 = 6.5px/character.
        # CFG-82's own instruction is that a measured number beats a
        # modelled one, so that measured factor (not a font-metrics
        # estimate) is what this check spends on any future longest
        # label, with the audit's own 65px kept as an explicit floor.
        PER_CHARACTER_ADVANCE_PX = 6.5
        AUDIT_MEASURED_FLOOR_PX = 65  # "Compagnies" at 11px, 2026-09-17 audit
        modelled_requirement_px = PER_CHARACTER_ADVANCE_PX * len(longest_label)
        required_px = max(modelled_requirement_px, AUDIT_MEASURED_FLOOR_PX)

        if available_px < required_px:
            return False, (
                "expected the available label width (%.1fpx = %.1fpx cell [%dpx viewport / %d "
                "cells] - 2x%.1fpx margin) to be at least %.1fpx (the longest label %r's own "
                "requirement, floored at the audit's measured %dpx) but it was not (CFG-82, "
                "29-02-PLAN.md)"
                % (available_px, cell_width_px, FLOOR_VIEWPORT_PX, cell_count,
                   horizontal_margin_px, required_px, longest_label, AUDIT_MEASURED_FLOOR_PX))
        return True, ""
    check(
        "the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm "
        "tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured "
        "6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored "
        "at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while "
        "`.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82, "
        "29-02-PLAN.md)",
        _tab_bar_pill_horizontal_margin_lets_the_longest_label_fit)

    def _tab_bar_more_sheet_opens_upward_and_reuses_the_dropdown_row():
        css_source = _css_source()
        region = css_source[css_source.index(_TAB_BAR_BANNER):]
        sheet = _block(region, ".tab-bar__more-panel {")
        for needle in ("position: absolute", "bottom: 100%", "right: 0",
                       "background: var(--color-secondary)",
                       "box-shadow: var(--shadow-card-hover)"):
            if needle not in sheet:
                return False, "expected %r in the More sheet's rule" % (needle,)
        # The absolute positioning here is NOT a reversal of the rejected
        # absolute-overlay verdict on the PRIMARY nav — the distinction
        # has to be written down where a future reader meets the rule,
        # not only in a plan document.
        region_head = region[:region.index(".tab-bar__more-panel {")]
        if "flex-basis: 100%" not in _block(css_source, ".mobile-nav {"):
            return False, (
                "the dropdown's in-flow push-down mechanism must stay exactly as it is — "
                "this plan does not reopen the 06.6.1-06 verdict")
        if "not a reversal" not in region_head.lower():
            return False, (
                "expected the stylesheet itself to record why the sheet's absolute "
                "positioning is not a reversal of the rejected-overlay verdict")
        # The sheet's rows reuse .mobile-nav__link rather than restating
        # its 44px/16px geometry, so quick task 260902-qkm's restored
        # floor cannot drift out from under them.
        if "min-height: 44px" in sheet or "font-size:" in sheet:
            return False, (
                "the sheet must REUSE .mobile-nav__link's geometry, never restate it")
        return True, ""
    check(
        "the More sheet opens upward from the fixed bar (absolute, bottom: 100%, right: 0) on the nav "
        "surface with the overlay shadow, reuses .mobile-nav__link's 44px/16px geometry rather than "
        "restating it, leaves .mobile-nav's in-flow flex-basis push-down untouched, and the stylesheet "
        "itself records why this absolute positioning is not a reversal of the rejected-overlay verdict "
        "(X9/D-10, 22-14-PLAN.md Task 1)",
        _tab_bar_more_sheet_opens_upward_and_reuses_the_dropdown_row)

    def _french_tab_bar_labels_and_landmark():
        device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = layout.page_shell(
                title="T", active="flights", body="", device_config=device_cfg)
        finally:
            prefs.set_request_prefs(lang="en")
        start = rendered.index('<nav class="tab-bar"')
        bar = rendered[start:rendered.index("</nav>", start)]
        if 'aria-label="Navigation principale"' not in bar:
            return False, (
                "expected the tab bar's landmark name in French (CFG-29 must not regress), "
                "got %r" % (bar[:120],))
        for english, french in (
                ("Home", "Accueil"), ("Display", "Affichage"), ("Flights", "Vols"),
                ("Airlines", "Compagnies"), ("More", "Plus"),
                ("Health", "\u00c9tat"), ("Device", "Appareil")):
            if ">%s<" % french not in bar:
                return False, (
                    "expected the %r cell to read %r in French, got %r"
                    % (english, french, bar))
            if ">%s<" % english in bar:
                return False, (
                    "expected no leftover English %r label under a French request" % (english,))
        return True, ""
    check(
        "under lang='fr' every tab-bar label reads French — Accueil / Affichage / Vols / Compagnies / "
        "Plus, with \u00c9tat and Appareil inside the More sheet — and the landmark name is "
        "'Navigation principale' (B16/CFG-29, 22-14-PLAN.md Task 1)",
        _french_tab_bar_labels_and_landmark)

    # ======================================================================
    # 22-14-PLAN.md Task 2 (X9/D-10, B10, T11): the dropdown reduced to
    # preferences, the reminder that stops lying, and the ONE open-state
    # max-height.
    # ======================================================================

    def _nav_status_is_a_span_on_home_and_a_link_everywhere_else():
        # B10 / 22-UI-SPEC.md §5 contract 6 / D-04. The audit's finding
        # is not the WORDING of the aria-label — it is that an element
        # promises navigation it does not perform. On Home the reminder
        # therefore stops being a link at all, which is also how D-04's
        # "stays only if it links somewhere useful" is satisfied by
        # construction rather than by copy.
        home = layout.page_shell(
            title="Home", active="home", body="", ui_theme="auto",
            device_config=_NAV_STATUS_DEVICE_CFG)
        if home.count('<span class="nav-status text-label"') != 2:
            return False, (
                "expected the reminder to render as a <span> in BOTH nav copies on Home, got %d"
                % home.count('<span class="nav-status text-label"'))
        if '<a class="nav-status text-label"' in home:
            return False, "expected no <a> reminder anywhere on Home"
        home_label = layout.i18n.t(layout.NAV_STATUS_ARIA_LABEL_TEXT)
        if home_label in home:
            return False, (
                "the destination-naming label must not survive on Home — it is the claim, "
                "not the wording, that is the defect")
        for match in re.finditer(
                r'<span class="nav-status text-label" aria-label="([^"]*)"', home):
            announced = match.group(1)
            expected = "%s%s%s" % (
                layout.i18n.t(layout.NAV_SCREEN_ON_TEXT),
                layout.NAV_STATUS_SEPARATOR_TEXT,
                layout.i18n.t(layout.NAV_QUIET_OFF_TEXT))
            if announced != expected:
                return False, (
                    "expected the Home reminder to announce only the state (%r), got %r"
                    % (expected, announced))

        elsewhere = layout.page_shell(
            title="Display", active="display", body="", ui_theme="auto",
            device_config=_NAV_STATUS_DEVICE_CFG)
        if elsewhere.count('<a class="nav-status text-label" href="%s"' % layout.HOME_ROUTE) != 2:
            return False, (
                "expected the reminder to stay a link to Home in both nav copies elsewhere")
        if '<span class="nav-status text-label"' in elsewhere:
            return False, "expected no <span> reminder off Home"
        if layout.escape_html(
                layout.i18n.t(layout.NAV_STATUS_ARIA_LABEL_TEXT)) not in elsewhere:
            return False, "expected the destination-naming label off Home"

        # The two segments are separate nowrap spans in both shapes, so
        # the line can only ever break BETWEEN them (B10).
        for rendered, shape in ((home, "span"), (elsewhere, "link")):
            if rendered.count('<span class="nav-status__segment">') != 4:
                return False, (
                    "expected two segments per nav copy in the %s shape, got %d"
                    % (shape, rendered.count('<span class="nav-status__segment">')))
        return True, ""
    check(
        "the nav state reminder renders as a <span> with no href on Home, announcing ONLY the state, "
        "and stays an <a href=\"/\" > with its destination-naming label everywhere else — in both nav "
        "copies, each with its two nowrap segments (B10/D-04, 22-14-PLAN.md Task 2)",
        _nav_status_is_a_span_on_home_and_a_link_everywhere_else)

    def _one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule():
        css_source = _css_source()
        open_state = ".js .mobile-nav--open"
        if css_source.count(open_state) != 1:
            return False, (
                "T11: expected exactly ONE open-state dropdown rule in the whole file, got %d"
                % css_source.count(open_state))
        open_block = _block(css_source, open_state + " {")
        if open_block.count("max-height") != 1:
            return False, "expected exactly one max-height declaration for the open state"
        if "max-height: 320px" not in open_block:
            return False, (
                "expected the measured single value (the reduced French content at 390px "
                "measures 165px), got %r" % (open_block,))
        if "max-height: 640px" in css_source or "max-height: 420px" in css_source:
            return False, "expected both of the contradicting values to be gone, not re-tuned"

        # The dropdown's own nav region is deleted, not left as a dead
        # selector — its rule and its .nav-group override both go.
        for dead in (".mobile-nav__nav {", ".mobile-nav__nav .nav-group {"):
            if dead in css_source:
                return False, "expected the dead selector %r to be deleted" % (dead,)
        # ...but .mobile-nav__link survives, because the tab bar's More
        # sheet reuses it verbatim.
        if ".mobile-nav__link {" not in css_source:
            return False, (
                ".mobile-nav__link must survive — the tab bar's More sheet reuses its "
                "44px/16px geometry")

        # B10's own mechanism, read from the rule rather than assumed.
        status_block = _block(css_source, ".nav-status {")
        for needle in ("display: flex", "flex-wrap: wrap", "gap: 0 var(--space-xs)"):
            if needle not in status_block:
                return False, "expected %r in .nav-status" % (needle,)
        segment_block = _block(css_source, ".nav-status__segment {")
        if "white-space: nowrap" not in segment_block:
            return False, "expected each segment to be nowrap"
        # The hover underline is scoped to the ANCHOR: a <span> that
        # underlines under the pointer claims an interactivity it does
        # not have.
        # Boundary-anchored: "a.nav-status:hover {" CONTAINS
        # ".nav-status:hover {", so a bare substring test would report
        # the scoped rule as the unscoped one it is replacing.
        if re.search(r"(?:^|[\s,])\.nav-status:hover\s*\{", css_source, re.M):
            return False, (
                "expected the hover underline scoped to a.nav-status, not every reminder")
        if not re.search(r"(?:^|[\s,])a\.nav-status:hover\s*\{", css_source, re.M):
            return False, "expected the anchor-scoped hover underline"
        return True, ""
    check(
        "exactly ONE open-state max-height governs the dropdown (320px, pinned against a measured "
        "165px of reduced French content at 390px — both the 420px and 640px values are gone, not "
        "re-tuned), the dropdown's dead nav selectors are deleted while .mobile-nav__link survives for "
        "the tab bar's sheet, and .nav-status is a wrapping flex row of nowrap segments whose hover "
        "underline is anchor-scoped (T11/B10, 22-14-PLAN.md Task 2)",
        _one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule)

    def _style_css_carries_no_stray_comment_terminator():
        """A structural guard, added by 22-14-PLAN.md Task 2 after a real
        defect this plan found and fixed.

        22-10-PLAN.md Task 1 appended a note to an existing block comment
        AFTER that comment's own closing marker, leaving a terminator
        with no opener. Everything from it to the next brace then parsed
        as part of the following selector, so the whole
        `.theme-chip--selected:not(:has(input:checked))::after` rule —
        T10's saved-chip badge — was silently dropped by every browser.
        This plan's own first draft of the B10 comment made the identical
        mistake and took `.nav-status` with it.

        No string-comparison harness could see either one: the file still
        contains every declaration such a harness asks about. The
        cheapest durable guard is structural, so it is pinned here rather
        than left to the next person who happens to open a real browser.
        """
        css_source = _css_source()
        pos = 0
        line = 1
        in_comment = False
        strays = []
        while pos < len(css_source):
            ch = css_source[pos]
            if ch == "\n":
                line += 1
                pos += 1
                continue
            if not in_comment and css_source.startswith("/*", pos):
                in_comment = True
                pos += 2
                continue
            if in_comment and css_source.startswith("*/", pos):
                in_comment = False
                pos += 2
                continue
            if not in_comment and css_source.startswith("*/", pos):
                strays.append(line)
                pos += 2
                continue
            pos += 1
        if strays:
            return False, (
                "companion/static/style.css carries %d comment terminator(s) with no opener, at "
                "line(s) %r — everything from each one to the next brace parses as a selector and "
                "silently drops the rule that follows" % (len(strays), strays))
        if in_comment:
            return False, "companion/static/style.css ends inside an unterminated block comment"
        return True, ""
    check(
        "companion/static/style.css carries zero stray comment terminators and ends outside a comment "
        "— the structural guard for a real parse-error class that drops whole rules while leaving the "
        "source text a string-comparison harness reads as correct (22-14-PLAN.md Task 2, Rule 1)",
        _style_css_carries_no_stray_comment_terminator)

    def _every_disclosure_has_a_marker_and_no_header_claims_to_stick():
        """22-15-PLAN.md Task 1 — T3 and T4.

        T3: `summary { display: flex }` stopped generating a `::marker`
        at all, so every <details> in the app lost its open/closed
        indicator. Both marker rules below it have been dead ever since
        and no harness noticed, because the file still contains them.
        The replacement is an explicit `::before` chevron that rotates
        on `[open]`.

        T4: `.data-table-wrap th` claimed `position` + sticky inside a
        wrapper with `overflow-x: auto` and no height — no vertical
        scrollport, so the claim could never engage. It is removed
        rather than made true; sticky day headers are Phase 23's D7.
        """
        css_source = _css_source()
        stripped = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)

        # --- T3: the marker exists, and it rotates ------------------
        #
        # 23-08-PLAN.md Task 2: the needle is ANCHORED now, and the
        # reason is recorded rather than fixed silently. This looked up
        # the first occurrence of "summary::before {" in the file, and
        # 23-08 added `.history-card__summary::before` — a selector that
        # ENDS in the needle and sits earlier in the stylesheet — so the
        # lookup started reading the card's own positioning override
        # instead of the global marker this check is about. The
        # assertions are unchanged; only which rule they are asked of is
        # fixed, and the anchor is what makes that unambiguous. This is
        # the same substring-collision class 23-07 hit on an attribute
        # name, and the check was right to go red.
        marker = _block(stripped, "\nsummary::before {")
        if 'content: ""' not in marker:
            return False, "expected an explicit summary::before disclosure marker (T3)"
        # And the card summary REUSES that marker rather than drawing a
        # second one. A rule of its own that redeclared the geometry
        # would be two chevrons to keep in step, which is the thing the
        # single shared rule exists to prevent.
        if ".history-card__summary::before" in stripped:
            card_marker = _block(stripped, ".history-card__summary::before {")
            for redeclared in ("content:", "width:", "height:", "border-right", "border-bottom"):
                if redeclared in card_marker:
                    return False, (
                        "expected the card summary's marker override to change only WHERE the "
                        "shared chevron sits, not to redraw it (found %r in %r) — two chevrons "
                        "is two things to keep in step (T3)" % (redeclared, card_marker))
        if "flex: none" not in marker:
            return False, (
                "expected the marker to declare flex: none — it is a flex item of the summary "
                "row and a long label would otherwise shrink it to a sliver (T3)")
        if "transform: rotate(" not in marker:
            return False, "expected the closed-state marker to be a rotated box (T3)"
        open_marker = _block(stripped, "details[open] > summary::before {")
        if "transform: rotate(" not in open_marker:
            return False, "expected the open state to rotate the marker (T3)"
        if "details[open] summary::before" in stripped:
            return False, (
                "expected a CHILD combinator on the open-state rule — a descendant one rotates a "
                "parent disclosure's marker when a nested one opens (T3)")

        # T3 reaches the tab bar's "More" summary too (22-UI-SPEC.md
        # §3.1), where it is taken out of flow so a 6px marker cannot
        # narrow a 78x56px cell's centred icon-and-label stack.
        tab_marker = _block(stripped, ".tab-bar__more > .tab-bar__link::before {")
        if "position: absolute" not in tab_marker:
            return False, (
                "expected the tab bar's More marker to be positioned out of flow — in flow it is "
                "a flex item beside .tab-bar__pill and compresses the cell (T3)")
        if ".tab-bar__more[open] > .tab-bar__link::before" not in stripped:
            return False, (
                "expected the tab bar's More marker to have its own open state — the sheet opens "
                "UPWARD, so the global right-closed/down-open convention points away from it (T3)")

        # The rotation is a transform and the fade is a transition, both
        # already covered by the single global reduced-motion override.
        # A per-rule block here would be dead code, not a safety net
        # (references/accessibility-contrast.md, "What to Avoid").
        if stripped.count("@media (prefers-reduced-motion: reduce)") != 2:
            return False, (
                "expected exactly the two pre-existing prefers-reduced-motion blocks (the global "
                "override and .js .mobile-nav's transition opt-out), got %d — T3 adds none"
                % stripped.count("@media (prefers-reduced-motion: reduce)"))

        # --- T4: the false claim is gone ----------------------------
        if ".data-table-wrap th" in stripped:
            return False, (
                "expected NO .data-table-wrap th rule at all — its sticky claim could never "
                "engage inside a wrapper with no height, and its --color-canvas background "
                "existed only to serve that claim (T4)")
        wrap = _block(stripped, ".data-table-wrap {")
        for forbidden in ("max-height", "height:"):
            if forbidden in wrap:
                return False, (
                    "expected .data-table-wrap to gain no height — T4 removes the false sticky "
                    "claim rather than adding a second nested vertical scrollbar to four tables")
        return True, ""
    check(
        "every <details> carries an explicit summary::before chevron that rotates on [open] through a "
        "child combinator — including the bottom tab bar's More summary, where it is taken out of flow "
        "so a marker cannot narrow the cell, and with its own inverted rotation because that sheet opens "
        "upward — with the prefers-reduced-motion block count unchanged at two; and no "
        ".data-table-wrap th rule survives to claim sticky positioning a wrapper with no height could "
        "never provide (T3/T4, 22-15-PLAN.md Task 1)",
        _every_disclosure_has_a_marker_and_no_header_claims_to_stick)

    def _refresh_loop_retries_with_backoff_and_says_so_neutrally():
        """22-15-PLAN.md Task 2 — T13, from the server side.

        The browser half (companion/test_browser_ux.py) proves the badge
        really appears and really clears. This half pins the things a
        running browser cannot show: that the copy exists in BOTH
        languages on every shell, that the loop's source carries a real
        bounded ladder rather than a single retry, that the in-flight
        guard and the targeted swap exist, and above all that the
        silent-stop calls are GONE from both failure paths.
        """
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path, "r", encoding="utf-8") as fh:
            js = fh.read()
        # Strip comments so this check can be neither satisfied nor
        # defeated by prose — the same discipline the CSS checks above
        # apply.
        code = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
        code = re.sub(r"^\s*//.*$", "", code, flags=re.M)

        # --- the silent stop is gone from both failure paths ---------
        if code.count("stopLoop") != 3:
            return False, (
                "expected exactly three stopLoop references in freshness.js code — its definition "
                "and its two DELIBERATE background-tab teardowns. Neither failure path may call "
                "it: that was T13's whole defect, a loop that stopped for the life of the page "
                "with nothing visible to say so. Got %d" % code.count("stopLoop"))
        for handler in ("failAndRetry", "succeed"):
            if ("function %s(" % handler) not in code:
                return False, "expected freshness.js to define %s() (T13)" % handler

        # --- a real, bounded, DECREASING-rate ladder -----------------
        if "RETRY_CEILING_MS" not in code or "Math.min(retryDelayMs * 2" not in code:
            return False, (
                "expected an exponential retry delay bounded by a stated ceiling — an unbounded "
                "ladder, or a fixed delay, is not what T-22-56 asks for")
        if "RETRY_BASE_MS = AUTO_REFRESH_INTERVAL_MS" not in code:
            return False, (
                "expected the ladder to START at the normal cadence, never below it — the whole "
                "mitigation is that a failing server sees a strictly DECREASING request rate")
        if "retryDelayMs = 0" not in code:
            return False, "expected a success to reset the backoff to zero (T13)"

        # --- the in-flight guard and the targeted swap ---------------
        if "var inFlight = false;" not in code or "if (inFlight) {" not in code:
            return False, (
                "expected an in-flight guard — without it a slow response and a visibility "
                "catch-up can race, and the LAST to resolve wins the swap (T13)")
        if "isEqualNode" not in code:
            return False, (
                "expected the swap to skip regions that did not change, compared with "
                "isEqualNode() — replacing an unchanged region destroys any focus inside it")
        if "existing.contains(active)" not in code:
            return False, (
                "expected the swap to skip any region containing the focused element (T13)")
        # The interaction-skip guard and the visibility gating are
        # unchanged by this plan and must stay that way.
        for untouched in ("userIsInteracting", "visibilitychange", "AUTO_REFRESH_INTERVAL_MS = 45000"):
            if untouched not in code:
                return False, "expected %r to survive T13 untouched" % (untouched,)

        # --- neutral, never a warning --------------------------------
        if 'dot.className = "dot dot--off";' not in code:
            return False, (
                "expected the loop-state badge's dot to be the neutral .dot--off — a browser that "
                "lost its connection is not a device fault (22-UI-SPEC.md §5 contract 9)")
        if 'badge.className = "banner__pill";' not in code:
            return False, "expected the badge to compose .banner__pill (22-UI-SPEC.md's T13 row)"
        # Scoped to the badge BUILDER's own body, not the whole file:
        # SWAP_SELECTORS legitimately names div.banner--warn as a region
        # to swap, which is a different thing entirely from the badge
        # wearing a warn token.
        builder_at = code.index("function stateBadge(")
        builder = code[builder_at:code.index("\n  }", builder_at)]
        for warn_token in ("warn", "error", "danger", "alert", "status-"):
            if warn_token in builder:
                return False, (
                    "the loop-state badge must be built from neutral classes only, found %r in "
                    "stateBadge() — T13's state is never a warning" % (warn_token,))

        # --- the [hidden] guard the badge depends on -----------------
        css_source = _css_source()
        stripped_css = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)
        if ".banner__pill[hidden] {" not in stripped_css:
            return False, (
                "expected a .banner__pill[hidden] guard — .banner__pill declares display: "
                "inline-flex, which always beats the user-agent [hidden] rule, so the badge would "
                "render even when hidden. Fourth consumer of this file's [hidden]-vs-display "
                "guard, after .dirty-bar, .refresh-pill and .login-reveal")
        guard = _block(stripped_css, ".banner__pill[hidden] {")
        if "display: none" not in guard:
            return False, "expected .banner__pill[hidden] to hide by display, not visibility"

        # --- the copy, server-rendered, in BOTH languages ------------
        if layout.REFRESH_PAUSED_TEXT != "Paused" or layout.REFRESH_RECONNECTING_TEXT != "Reconnecting…":
            return False, (
                "expected 22-UI-SPEC.md §1's own copy verbatim, got %r / %r"
                % (layout.REFRESH_PAUSED_TEXT, layout.REFRESH_RECONNECTING_TEXT))
        for text in (layout.REFRESH_PAUSED_TEXT, layout.REFRESH_RECONNECTING_TEXT):
            if layout.i18n.t_lang(text, "fr") == text:
                return False, "expected a French entry for %r" % (text,)
            if layout.i18n.t_lang(text, "en") != text:
                return False, "expected %r to round-trip unchanged in English" % (text,)
        # The English fallbacks inside the script must be byte-identical
        # to the server-side constants, or a page with no attributes
        # renders different copy from one with them.
        for text in (layout.REFRESH_PAUSED_TEXT, layout.REFRESH_RECONNECTING_TEXT):
            if ('"%s"' % text) not in code:
                return False, (
                    "expected freshness.js's own English fallback for %r to match the server "
                    "constant byte for byte" % (text,))
        try:
            for lang, expected_paused in (("en", "Paused"), ("fr", "En pause")):
                prefs.set_request_prefs(lang=lang)
                rendered = layout.page_shell(
                    title="T", active="health", body="<p>x</p>", lang=lang)
                if ('%s="%s"' % (layout.REFRESH_PAUSED_ATTR, expected_paused)) not in rendered:
                    return False, (
                        "expected the paused copy on <body> in %s, got neither" % lang)
                if ('%s="' % layout.REFRESH_RECONNECTING_ATTR) not in rendered:
                    return False, "expected the reconnecting copy on <body> in %s" % lang
        finally:
            prefs.set_request_prefs(lang="en")
        return True, ""
    check(
        "freshness.js no longer stops dead on a failure: stopLoop() survives only as its definition and "
        "its two deliberate background-tab teardowns, a bounded exponential ladder starting AT the normal "
        "cadence (so a failing server sees a strictly decreasing rate) replaces it, a success resets the "
        "backoff, an in-flight guard stops two fetches racing, the swap skips unchanged regions and any "
        "region holding focus, the state badge is .banner__pill with the NEUTRAL .dot--off and no warn "
        "token anywhere in the file, style.css carries the .banner__pill[hidden] display guard the badge "
        "depends on, and both strings render onto <body> in both languages matching the script's own "
        "English fallbacks byte for byte (T13, 22-15-PLAN.md Task 2)",
        _refresh_loop_retries_with_backoff_and_says_so_neutrally)

    def _resolve_context_hidden_guard_present_after_base_rule():
        # Quick task 260921-n2n Task 2: `.resolve-context` declares
        # `display: grid` with no `[hidden]` guard, the same collision
        # named at `.banner__pill[hidden]` above — an author `display`
        # declaration always beats the user-agent stylesheet's
        # `[hidden] { display: none }`, so panel-lookup.js's
        # `resolveContext.hidden = !count` was silently inert and every
        # ordinary illustration lightbox painted five empty label/value
        # pairs instead of nothing.
        css_source = _css_source()
        stripped_css = re.sub(r"/\*.*?\*/", "", css_source, flags=re.DOTALL)
        if stripped_css.count(".resolve-context[hidden] {") != 1:
            return False, (
                "expected exactly one .resolve-context[hidden] guard — .resolve-context declares "
                "display: grid, which always beats the user-agent [hidden] rule, so the block "
                "would render (empty) even when hidden, got %d occurrence(s)"
                % stripped_css.count(".resolve-context[hidden] {"))
        base_at = stripped_css.index(".resolve-context {")
        guard_at = stripped_css.index(".resolve-context[hidden] {")
        if guard_at <= base_at:
            return False, "expected the .resolve-context[hidden] guard to come AFTER the base rule"
        guard = _block(stripped_css, ".resolve-context[hidden] {")
        if "display: none" not in guard:
            return False, "expected .resolve-context[hidden] to hide by display: none"
        return True, ""
    check(
        "style.css declares .resolve-context[hidden] { display: none; } after the base rule — "
        "without it, an author display declaration beats the UA [hidden] rule and every ordinary "
        "illustration's resolve-context block renders empty instead of hidden (quick task 260921-n2n "
        "Task 2)",
        _resolve_context_hidden_guard_present_after_base_rule)

    def _flight_detail_row_grid_margin_never_shrinks_below_cfg70_floor():
        # Quick task 260921-n2n Task 5: CFG-70 (27-08-PLAN.md Task 3)
        # MEASURED the prior 0-margin state and found the grid's last-row
        # copy button resolved to 34x26 against its declared 44x44,
        # because two adjacent 11px pointer-target reaches need 22px of
        # clearance between their owners' visual boxes, and
        # var(--space-lg) (24px) was chosen as that clearance with a
        # couple of pixels to spare. A smaller margin here — for example
        # var(--space-md) at 16px, which the developer's own screenshot
        # of "l'écart bizarre" might tempt someone into trying — would
        # silently re-break that mutation-tested 44x44 hit-target
        # contract, and nothing else in this suite would catch it.
        #
        # This asserts the RELATIONSHIP, not the endpoint: both numbers
        # are resolved from style.css's own source (the token the grid's
        # margin references, and copy-btn::before's own inset magnitude)
        # rather than hardcoded, so a change to either token is measured
        # against the other rather than against a frozen constant.
        css_source = _css_source()
        tok = dict(re.findall(r"--(space-[a-z]+):\s*(\d+)px", css_source))
        grid_block = _block(css_source, ".flight-detail-row__grid {")
        margin_match = re.search(r"margin:\s*0\s+0\s+var\(--(space-[a-z]+)\)", grid_block)
        if not margin_match:
            return False, "could not parse .flight-detail-row__grid's margin shorthand: %r" % grid_block
        margin_bottom = int(tok[margin_match.group(1)])
        before_block = _block(css_source, ".copy-btn::before {")
        inset_match = re.search(r"inset:\s*-(\d+)px", before_block)
        if not inset_match:
            return False, "could not parse .copy-btn::before's inset: %r" % before_block
        reach = int(inset_match.group(1))
        if margin_bottom < 2 * reach:
            return False, (
                "CFG-70 floor violated: two adjacent synthesized 44x44 pointer targets need their "
                "owners' visual boxes at least 2x%dpx apart; CFG-70 measured the earlier control at "
                "34x26 when they were not, and .flight-detail-row__grid's margin-bottom is only "
                "%dpx — a smaller margin here silently shrinks a hit target nothing else in the "
                "suite would catch" % (reach, margin_bottom))
        return True, ""
    check(
        "style.css's .flight-detail-row__grid margin-bottom is at least 2x .copy-btn::before's own "
        "inset magnitude — CFG-70's measured 22px hit-target floor made executable rather than a "
        "comment; this is the check that would have failed had this quick task's own source data's "
        "'reduce to var(--space-md)' suggestion been taken (quick task 260921-n2n Task 5)",
        _flight_detail_row_grid_margin_never_shrinks_below_cfg70_floor)

    def _nav_toggle_label_now_describes_the_preferences_panel():
        if layout.NAV_TOGGLE_LABEL != "Account and preferences":
            return False, (
                "expected the toggle to name what the panel now holds, got %r"
                % (layout.NAV_TOGGLE_LABEL,))
        if layout.i18n.t_lang(layout.NAV_TOGGLE_LABEL, "fr") == layout.NAV_TOGGLE_LABEL:
            return False, "expected a French entry for the renamed toggle label"
        if layout.i18n.t_lang("Open menu", "fr") != "Open menu":
            return False, (
                "expected the retired 'Open menu' translation to be deleted, not superseded "
                "in place — it names a menu of pages the panel no longer holds")
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = layout.page_shell(
                title="T", active="display", body="", ui_theme="auto",
                device_config=_NAV_STATUS_DEVICE_CFG)
        finally:
            prefs.set_request_prefs(lang="en")
        if 'aria-label="Compte et préférences"' not in rendered:
            return False, "expected the French toggle name on a French request"
        return True, ""
    check(
        "the hamburger toggle's accessible name describes the preferences panel it now opens "
        "(\"Account and preferences\" / \"Compte et préférences\"), and the retired \"Open menu\" "
        "translation is deleted rather than orphaned (X9/D-10/B16, 22-14-PLAN.md Task 2)",
        _nav_toggle_label_now_describes_the_preferences_panel)

    # ======================================================================
    # 22-14-PLAN.md Task 3 (D-10, T7): the save bar and the tab bar,
    # geometrically apart first and unambiguously ordered second.
    # ======================================================================

    def _save_bar_geometry_is_restored_and_the_tab_bar_stacking_survives():
        # 27-04-PLAN.md (D-04/CFG-63): SUPERSEDED this check's own
        # pre-27-04 subject wholesale — the save bar this check measured
        # (its sub-960px offset gaining the tab bar's own height, its
        # z-index: 30 at both breakpoints, and its two MEASURED content-
        # clearance rules) was retired outright along with the
        # component, and style.css's own comments at each former site
        # recorded the account. What survived, unmodified by that plan,
        # was the tab bar's OWN stacking value and its OWN content
        # clearance (.has-tab-bar .page-content) — neither ever depended
        # on the save bar existing.
        #
        # 28-08-PLAN.md Task 3 (CFG-77/CFG-78), 2026-09-16: RENAMED and
        # retargeted in the OPPOSITE direction — the developer asked for
        # the bar back (ROADMAP.md's Phase 28 addendum), twice confirmed.
        # This is a file outside that plan's own declared files_modified
        # list, fixed here as a direct, unavoidable, foreseeable
        # consequence of restoring `.dirty-bar` to style.css (Rule 1: a
        # check asserting "zero occurrences of .dirty-bar" cannot
        # survive a plan whose whole point is putting .dirty-bar back).
        # `.dirty-bar` now DOES exist, with its OWN z-index: 30 at both
        # breakpoints (above the tab bar's 20, matching D-10/T7's own
        # "why the save bar wins" argument, restored verbatim in
        # style.css's own comments). `.dirty-ready`-scoped rules do NOT
        # survive — this restoration deliberately does not bring that
        # marker class back at all (28-08-PLAN.md Task 3: the CSS
        # clearance mechanism is `:has(.dirty-bar)` now, which works
        # with scripts blocked; `.dirty-ready` never would have).
        css_source = _css_source()

        if ".dirty-bar {" not in css_source:
            return False, "expected the restored .dirty-bar base rule to exist in style.css"
        dirty_bar_blocks = re.findall(r"\.dirty-bar \{[^}]*\}", css_source)
        fixed_count = sum(1 for block in dirty_bar_blocks if "position: fixed" in block)
        z30_count = sum(1 for block in dirty_bar_blocks if "z-index: 30;" in block)
        if fixed_count != 2:
            return False, (
                "expected exactly two `.dirty-bar { ... }` rule bodies to set position: fixed "
                "(one per breakpoint), got %d" % fixed_count)
        if z30_count != 2:
            return False, (
                "expected exactly two `.dirty-bar { ... }` rule bodies to set z-index: 30 (one "
                "per breakpoint), got %d" % z30_count)
        if ".dirty-ready .dashboard-main {" in css_source or ".dirty-ready .page-content {" in css_source:
            return False, (
                "expected neither .dirty-ready-scoped content-clearance rule to exist — this "
                "restoration's own clearance mechanism is :has(.dirty-bar), which (unlike "
                ".dirty-ready) works correctly with scripts blocked")

        tab_bar = _block(
            css_source[css_source.index(_TAB_BAR_BANNER):],
            ".tab-bar {\n    display: flex;")
        tab_z = re.search(r"z-index: (\d+);", tab_bar)
        if tab_z is None:
            return False, "expected the tab bar to still declare its own stacking value"
        if tab_z.group(1) != "20":
            return False, (
                "expected the tab bar's stacking value to stay at 20, unmoved by the save bar's "
                "restoration, got %r" % (tab_z.group(1),))

        # The tab bar's own content clearance survives unmoved — it is
        # now ONE of two clearance rules a phone-width settings page
        # needs (the other is the restored bar's own :has()-scoped
        # rule, asserted elsewhere by companion/test_config_page.py).
        if ".has-tab-bar .page-content {" not in css_source:
            return False, "expected the tab bar's own content-clearance rule to survive"
        clearance_body = _block(css_source, ".has-tab-bar .page-content {")
        if "padding-bottom" not in clearance_body:
            return False, "expected .has-tab-bar .page-content to declare padding-bottom"
        return True, ""
    check(
        "the save bar's own sub-960px geometry and its z-index: 30 at both breakpoints are "
        "RESTORED — the .dirty-ready marker class is not (this restoration's own clearance "
        "mechanism is :has(.dirty-bar), which works with scripts blocked) — while the tab bar's "
        "own stacking value (20) and its own content clearance are unmoved (D-10/T7, "
        "22-14-PLAN.md Task 3; retired by 27-04-PLAN.md/CFG-63, restored by 28-08-PLAN.md Task 3/"
        "CFG-77/CFG-78)",
        _save_bar_geometry_is_restored_and_the_tab_bar_stacking_survives)

    # ======================================================================
    # 22-04-PLAN.md Task 3 (D-03/CFG-26, X2): Health's Frame tile and the
    # nav notification dot read the SAME frame_state result the strip
    # does — they cannot disagree, because neither re-derives anything.
    # ======================================================================

    _PARIS_TZ = timezone(timedelta(hours=1))

    def _health_tile_clock_text(rendered_health):
        # RETARGETED IN PLACE, STRICTLY NARROWER (22-12-PLAN.md Task 1,
        # X8): the Frame tile's next-wake clock moved out of the Emphasis
        # `.stat-tile__value` paragraph into the muted detail slot, and
        # dropped the `time-value--primary` modifier with it — that
        # modifier IS the Emphasis shape, and carrying it one line under
        # a verdict already in that role was half of the double bold
        # verdict. The extractor reads the new shape, and the caller
        # below now ALSO asserts the modifier is absent, so the old shape
        # cannot silently come back.
        match = re.search(
            r'class="text-label widget-detail"><span class="time-value">'
            r'([^<]+)</span></div>',
            rendered_health)
        return match.group(1) if match else None

    def _strip_clock_text(rendered_strip):
        match = re.search(r'class="time-value time-value--primary">([^<]+)</span>', rendered_strip)
        return match.group(1) if match else None

    def _health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn():
        # The nightly regression, in full (X2, 22-UI-SPEC.md §3.3 rule 6):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00,
        # Europe/Paris — the strip renders the held copy with the neutral
        # dot; Health's Frame tile renders the SAME clock time and the
        # SAME state; the Health nav notification dot is unlit; the
        # rendered HTML contains zero occurrences of the warn dot, the
        # error dot, the warn tile modifier, the warn headline modifier,
        # and of "Expected since" / "Attendu depuis".
        qh_config = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=_PARIS_TZ)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=_PARIS_TZ)
        tmp = _mkstate("h-nightly-held")
        try:
            device_config.save_device_config(
                tmp, wake_interval_s=900, quiet_hours_enabled=True,
                quiet_hours_start="23:00", quiet_hours_end="07:00")
            _seed_device_health(tmp, [(checkin.isoformat(), 4200)])
            # The pipeline (flight-detection) signal is a genuinely
            # DIFFERENT system from the frame's own check-in cadence —
            # seeded fresh (at "now") so its own, unrelated staleness
            # thresholds do not confound this check's real subject.
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: clock.isoformat()})
            rendered_health = health_page.render(_ctx(tmp, now=clock.isoformat()))
            for warn_token in (
                    "dot--warn", "dot--error", "stat-tile--warn",
                    "status-card__headline--warn", "Expected since", "Attendu depuis"):
                if warn_token in rendered_health:
                    return False, "expected zero %r in a held Health render" % (warn_token,)
            severity = health_page.health_severity(tmp, now=clock.isoformat())
            if severity != "ok":
                return False, (
                    "expected the nav notification dot unlit (severity 'ok'), got %r" % (severity,))

            strip_ctx = _frame_strip_ctx(checkin.isoformat(), qh_config, clock.isoformat())
            rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
            strip_clock = _strip_clock_text(rendered_strip)
            tile_clock = _health_tile_clock_text(rendered_health)
            if not strip_clock or not tile_clock:
                return False, "expected a time-value clock span in both the strip and the tile"
            # 22-12-PLAN.md Task 1 (X8): the strip's headline keeps the
            # Emphasis modifier; the tile's detail must not have it.
            if "time-value--primary" not in rendered_strip:
                return False, "expected the strip's own headline to keep time-value--primary"
            if "time-value--primary" in rendered_health:
                return False, (
                    "expected zero time-value--primary on Health — the tile's clock is a muted "
                    "detail, never a second Emphasis element under its own verdict (X8)")
            if strip_clock != tile_clock:
                return False, (
                    "expected the strip's and the tile's clock text to be equal, got %r vs %r"
                    % (strip_clock, tile_clock))
            if "07:00" not in tile_clock and "07:0" not in tile_clock:
                return False, "expected the held clock to read the quiet-hours window's own end"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/"
        "Paris), pinned as ONE named check: the strip renders the held copy with the neutral dot, "
        "Health's Frame tile renders the SAME clock time, the nav notification dot is unlit, and "
        "the rendered Health HTML carries zero warn/error dots, zero warn tile/headline modifiers "
        "and neither 'Expected since' nor 'Attendu depuis' (X2, D-03/CFG-26)",
        _health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn)

    def _health_inside_grace_window_tile_and_strip_agree_normal():
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        # 11:00 + 900s = 11:15 due; 2x grace = 1800s -> still due until 11:45.
        checkin_iso = "2026-08-27T11:00:00+00:00"
        now_iso = "2026-08-27T11:30:00+00:00"
        tmp = _mkstate("h-grace-window")
        try:
            device_config.save_device_config(tmp, wake_interval_s=900)
            _seed_device_health(tmp, [(checkin_iso, 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
            state = health_page.compute_health_state(tmp, now=now_iso)
            if state["device_state"] != "ok":
                return False, "expected the tile to report 'ok' inside the grace window, got %r" % (
                    state["device_state"],)
            strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
            rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
            if "Next update ≈" not in rendered_strip:
                return False, "expected the strip to report the due copy inside the grace window"
            if "status-card__headline--warn" in rendered_strip:
                return False, "expected no warn modifier inside the grace window"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "inside the grace window with no hold, the tile reports the normal ('ok') state and the "
        "strip reports the due copy — they agree (22-UI-SPEC.md §3.3 rule 3)",
        _health_inside_grace_window_tile_and_strip_agree_normal)

    def _health_past_grace_window_both_report_late_dot_lights():
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        checkin_iso = "2026-08-27T11:00:00+00:00"
        now_iso = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("h-past-grace")
        try:
            device_config.save_device_config(tmp, wake_interval_s=900)
            _seed_device_health(tmp, [(checkin_iso, 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
            state = health_page.compute_health_state(tmp, now=now_iso)
            if state["device_state"] != "warn":
                return False, "expected the tile to report 'warn' past the grace window, got %r" % (
                    state["device_state"],)
            if state["severity"] == "ok":
                return False, "expected the nav notification dot to light past the grace window"
            strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
            rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
            if "Expected since" not in rendered_strip:
                return False, "expected the strip to report the late copy past the grace window"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "past the grace window with no hold, both the tile ('warn') and the strip ('Expected "
        "since') report late, and the nav notification dot lights",
        _health_past_grace_window_both_report_late_dot_lights)

    def _health_held_window_ended_and_grace_elapsed_both_report_late():
        # A held frame's window has already ended AND its own grace has
        # since elapsed — held cannot suppress lateness forever. The
        # check-in itself is OUTSIDE the quiet-hours window (14:00, not
        # 23:00-07:00), so next_wake_status() resolves hold_reason=None
        # for it — a real device that stopped reporting after an ordinary
        # daytime check-in, not one still inside a currently-active hold.
        device_cfg = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin_iso = "2026-08-27T14:00:00+00:00"
        now_iso = "2026-08-28T02:00:00+00:00"
        tmp = _mkstate("h-held-then-late")
        try:
            device_config.save_device_config(
                tmp, wake_interval_s=900, quiet_hours_enabled=True,
                quiet_hours_start="23:00", quiet_hours_end="07:00")
            _seed_device_health(tmp, [(checkin_iso, 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
            state = health_page.compute_health_state(tmp, now=now_iso)
            if state["device_state"] != "warn":
                return False, (
                    "expected the tile to report 'warn' once a held-then-elapsed frame is "
                    "genuinely late, got %r" % (state["device_state"],))
            strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
            rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
            if "Expected since" not in rendered_strip:
                return False, "expected the strip to also report late for the same fixture"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a frame whose (non-held) next wake has passed and whose own grace has since elapsed is "
        "reported late by both the tile and the strip — held cannot suppress lateness forever",
        _health_held_window_ended_and_grace_elapsed_both_report_late)

    def _health_render_no_new_dot_class_count_unchanged():
        # `grep -c "dot--" companion/static/style.css` reads 9 both
        # before and after this plan (Task 1/2 already landed; Task 3
        # touches no CSS at all) — recorded here as the SUMMARY's own
        # pinned "both numbers" acceptance criterion.
        css_source = _css_source()
        dot_count = css_source.count("dot--")
        if dot_count != 9:
            return False, (
                "expected grep -c 'dot--' companion/static/style.css to stay at 9 (this plan adds "
                "no dot class), got %d" % (dot_count,))
        return True, ""
    check(
        "companion/static/style.css's own dot--* class-name occurrence count is unchanged by this "
        "plan (9 before, 9 after) — this plan adds no dot class",
        _health_render_no_new_dot_class_count_unchanged)

    # ======================================================================
    # 27-08-PLAN.md Task 2 (CFG-69/D-23): the Frame strip is a SHARED
    # component — one write site (layout.frame_strip_html()'s quiet
    # cell) feeding both Home and Display. The check that proves this is
    # NOT "the link exists on Home" plus a second, separate "the link
    # exists on Display" — two per-page checks would both pass against a
    # forked component (each page's own builder rendering its own copy).
    # The property under test is IDENTITY: the same href, read off BOTH
    # real page renderers, in ONE check whose failure message names
    # whichever page it could not find on, or the two hrefs when they
    # disagree.
    # ======================================================================

    _QUIET_SCHEDULE_LINK_RE = re.compile(
        r'<a class="text-link frame-strip__schedule-link" href="([^"]+)">')

    def _the_quiet_schedule_link_is_one_write_site_reaching_both_pages():
        from companion.pages import config_page, home_page
        tmp = _mkstate("h-quiet-schedule-link")
        try:
            now_iso = _iso(_now())
            home_ctx = _home_ctx(tmp, now_iso)
            display_ctx = {
                "device_config": home_ctx["device_config"], "state_dir": tmp,
                "poll_cooldown_remaining": 0, "now": now_iso,
            }
            rendered_home = home_page.render(home_ctx)
            rendered_display = config_page.render(display_ctx, scope=config_page.SCOPE_DISPLAY)
            # Collected across BOTH pages before returning — a shared
            # write site that is missing entirely fails on both at once,
            # and the message says so by naming every page that lacked
            # it, not only whichever happened to be checked first.
            hrefs = {}
            missing = []
            for rendered, name in ((rendered_home, "Home"), (rendered_display, "Display")):
                match = _QUIET_SCHEDULE_LINK_RE.search(rendered)
                if match:
                    hrefs[name] = match.group(1)
                else:
                    missing.append(name)
            if missing:
                return False, (
                    "expected a.frame-strip__schedule-link on every page that renders the strip — "
                    "found none on: %s" % (", ".join(missing),))
            if hrefs["Home"] != hrefs["Display"]:
                return False, (
                    "expected the SAME href on both pages (one write site, D-23) — Home read %r, "
                    "Display read %r; two different hrefs is exactly what a forked component "
                    "would produce" % (hrefs["Home"], hrefs["Display"]))
            if rendered_home.count('frame-strip__schedule-link') != 1:
                return False, (
                    "expected exactly one schedule-link render on Home, got %d"
                    % rendered_home.count('frame-strip__schedule-link'))
            if rendered_display.count('frame-strip__schedule-link') != 1:
                return False, (
                    "expected exactly one schedule-link render on Display, got %d"
                    % rendered_display.count('frame-strip__schedule-link'))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the quiet cell's caption link is present on BOTH Home's and Display's own real "
        "render() output, with the IDENTICAL href on both — asserted as one check whose failure "
        "names the page missing the link or the two hrefs when they differ, never two separate "
        "per-page checks (CFG-69, D-23, 27-08-PLAN.md Task 2)",
        _the_quiet_schedule_link_is_one_write_site_reaching_both_pages)

    # --- 23-07-PLAN.md Task 1 (D2/CFG-36): the Frame strip's two
    # switches become real role="switch" controls, SERVER-rendered from
    # the saved value. The role is not a promise the script keeps — it
    # is a description of what the button does with scripts blocked too,
    # which is the whole reason the accessible state can be asserted
    # here, in a harness that runs no JavaScript at all.

    def _the_strip_renders_two_server_rendered_switches():
        now_iso = "2026-08-27T10:00:00+00:00"
        checkin_iso = "2026-08-27T09:55:00+00:00"
        # BOTH states, never one: an aria-checked hard-coded to "true"
        # satisfies a single-state assertion perfectly, and is exactly
        # the switch that lies.
        for display_on, quiet_on in ((True, False), (False, True)):
            device_cfg = {
                "display_enabled": display_on, "quiet_hours_enabled": quiet_on,
                "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
                "wake_interval_s": 900,
            }
            rendered = layout.frame_strip_html(
                _frame_strip_ctx(checkin_iso, device_cfg, now_iso),
                return_to=layout.HOME_ROUTE)
            if rendered.count('role="switch"') != 2:
                return False, (
                    "expected exactly two role=switch controls in the strip, got %d — one "
                    "control per setting is X1/D-04 and a switch beside a surviving button is "
                    "the defect that decision exists to prevent"
                    % rendered.count('role="switch"'))
            for label_id, state_id, is_on, action in (
                    (layout.QUICK_SWITCH_SCREEN_LABEL_ID, layout.QUICK_SWITCH_SCREEN_STATE_ID,
                     display_on, "/quick/display"),
                    (layout.QUICK_SWITCH_QUIET_LABEL_ID, layout.QUICK_SWITCH_QUIET_STATE_ID,
                     quiet_on, "/quick/quiet-hours")):
                expected = (
                    '<button type="submit" class="switch" role="switch" aria-checked="%s"'
                    ' aria-labelledby="%s" aria-describedby="%s" %s>'
                    % ("true" if is_on else "false", label_id, state_id,
                       layout.QUICK_SWITCH_CONTROL_ATTR))
                if expected not in rendered:
                    return False, (
                        "%s: expected the server to render %r — the accessible STATE comes from "
                        "the saved value, and the accessible NAME from the setting rather than "
                        "the action (a French action reads 'Éteindre', which cannot double as a "
                        "state)" % (action, expected))
                if ('id="%s"' % label_id) not in rendered:
                    return False, (
                        "%s: aria-labelledby points at %r but nothing on the page carries that "
                        "id — a dangling reference is an unnamed control, and no browser reports "
                        "it" % (action, label_id))
                if ('id="%s"' % state_id) not in rendered:
                    return False, (
                        "%s: aria-describedby points at %r but nothing carries that id"
                        % (action, state_id))
            # The no-JS floor is STRUCTURAL: the switch IS the form that
            # already ships. Every one of these is what the server acts
            # on when the script is not there.
            for token in ('<form method="post" action="/quick/display"',
                          '<form method="post" action="/quick/quiet-hours"',
                          "data-quick-switch",
                          '<input type="hidden" name="state"',
                          '<input type="hidden" name="return_to" value="/"'):
                if token not in rendered:
                    return False, (
                        "expected %r to survive the conversion — the script upgrades a control "
                        "that already works, it never replaces one" % token)
            # The next-state the form posts must be the OPPOSITE of the
            # rendered state, or pressing the switch with scripts blocked
            # re-asserts the state it is already in.
            display_form = rendered[rendered.index('action="/quick/display"'):]
            display_form = display_form[:display_form.index("</form>")]
            wanted = layout.QUICK_STATE_OFF if display_on else layout.QUICK_STATE_ON
            if ('name="state" value="%s"' % wanted) not in display_form:
                return False, (
                    "the Screen form posts the wrong next state for display_enabled=%r — "
                    "expected %r" % (display_on, wanted))
            # The retired ACTION wording must be gone from the markup.
            # It is the string the accessible name would otherwise have
            # been, and leaving it beside a role=switch is two claims
            # about one control.
            for retired in (layout.QUICK_ACTION_SWITCH_ON_BUTTON,
                            layout.QUICK_ACTION_SWITCH_OFF_BUTTON,
                            layout.QUICK_ACTION_QUIET_TURN_ON_BUTTON,
                            layout.QUICK_ACTION_QUIET_TURN_OFF_BUTTON):
                if (">%s<" % retired) in rendered:
                    return False, (
                        "the action wording %r is still rendered as the switch's own text — a "
                        "role=switch names the SETTING and states itself with aria-checked; an "
                        "action label beside it is the second, contradicting claim" % retired)
            # The visible state survives as BOTH wordings, one hidden,
            # so the script never has to carry a word of user-facing
            # copy and the rollback is a pure attribute flip.
            if rendered.count(layout.QUICK_STATE_ON_ATTR) != 2:
                return False, (
                    "expected one %s span per switch, got %d"
                    % (layout.QUICK_STATE_ON_ATTR, rendered.count(layout.QUICK_STATE_ON_ATTR)))
            if rendered.count(layout.QUICK_STATE_OFF_ATTR) != 2:
                return False, (
                    "expected one %s span per switch, got %d"
                    % (layout.QUICK_STATE_OFF_ATTR, rendered.count(layout.QUICK_STATE_OFF_ATTR)))
            if rendered.count(" hidden>") != 2:
                return False, (
                    "expected exactly one of each switch's two state wordings to be hidden, "
                    "got %d hidden spans" % rendered.count(" hidden>"))
            # The pending marker's own host. freshness.js skips a region
            # carrying it OR containing it; this is the region.
            if rendered.count(layout.QUICK_SWITCH_REGION_ATTR) != 2:
                return False, (
                    "expected one %s region per switch — the element the script marks pending "
                    "and plan 23-06's swap already skips, got %d"
                    % (layout.QUICK_SWITCH_REGION_ATTR,
                       rendered.count(layout.QUICK_SWITCH_REGION_ATTR)))
        return True, ""
    check(
        "layout.frame_strip_html() renders exactly two role=switch controls whose aria-checked is "
        "the SAVED value in both directions, named by the setting through aria-labelledby and "
        "described by the state span, over the unchanged <form>/state/return_to/data-quick-switch "
        "the server already acts on — with the retired action wording gone, both state wordings "
        "present with exactly one hidden, and one pending-marker region per switch (D2/CFG-36, "
        "X1/D-04, 23-07-PLAN.md Task 1)",
        _the_strip_renders_two_server_rendered_switches)

    def _the_failure_toast_is_transient_translated_and_carries_no_internal():
        try:
            return _failure_toast_body()
        finally:
            prefs.set_request_prefs(lang="en")

    def _failure_toast_body():
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            expected = layout.i18n.t(layout.QUICK_SWITCH_FAILED_TEXT)
            doc = layout.page_shell(title="T", active="home", body="<p>b</p>", lang=lang)
            body_tag = doc[doc.index("<body"):doc.index(">", doc.index("<body")) + 1]
            marker = '%s="%s"' % (layout.QUICK_SWITCH_FAILED_ATTR, layout.escape_html(expected))
            if marker not in body_tag:
                return False, (
                    "lang=%s: expected the translated failure copy on the rendered <body> tag "
                    "(%r), got %r" % (lang, marker, body_tag))
            if lang == "fr" and expected == layout.QUICK_SWITCH_FAILED_TEXT:
                return False, (
                    "the failure copy is untranslated — it reads %r in both languages"
                    % (expected,))
            # V7: an error message is an information-disclosure surface.
            # The copy is the app's own existing generic flash sentence
            # and must never acquire a status code, a URL or a route.
            for internal in ("500", "http", "/quick/", "Traceback", "Error:"):
                if internal in expected:
                    return False, (
                        "lang=%s: the failure copy carries %r — a user-facing failure message "
                        "names no status code, no URL and no server internal (V7, T-23-27)"
                        % (lang, internal))
            # A transient toast, never a permanent banner. The live
            # region is rendered EMPTY and stays in the accessibility
            # tree, because a region added to the tree at announce time
            # is a region screen readers routinely miss.
            toast = '<div class="quick-toast" %s role="alert"></div>' % layout.QUICK_TOAST_ATTR
            if toast not in doc:
                return False, (
                    "lang=%s: expected exactly the empty assertive live region %r in the shell — "
                    "D2 asks for a transient toast rather than the permanent banner this app "
                    "uses for a flash" % (lang, toast))
            if doc.count(layout.QUICK_TOAST_ATTR) != 1:
                return False, (
                    "lang=%s: expected exactly one toast region per document, got %d — a second "
                    "one is a second place a failure could be announced"
                    % (lang, doc.count(layout.QUICK_TOAST_ATTR)))
        return True, ""
    check(
        "the optimistic switch's failure copy is the app's own generic flash sentence, translated "
        "on <body> in both languages and carrying no status code, URL or server internal, and the "
        "shell renders exactly one EMPTY assertive live region for it — a transient toast, never "
        "a permanent banner (D2/CFG-36, V7/T-23-27, 23-07-PLAN.md Task 1)",
        _the_failure_toast_is_transient_translated_and_carries_no_internal)

    # --- 23-05-PLAN.md Task 2 (D22's remainder, D14/CFG-34): the live
    # indicator tells the truth. Three checks: the dot's server-rendered
    # markup, the ticking age that replaces the frozen clock, and a
    # source scan proving the breathing class is toggled from the loop's
    # OWN state rather than from a second state machine beside it.

    def _health_freshness_line_carries_a_neutral_live_dot():
        tmp = _mkstate("h-live-dot")
        try:
            rendered = health_page.render(_ctx(tmp, now=_iso(_now())))
            start = rendered.index('<p class="page-header__freshness')
            wrapper = rendered[start:rendered.index("</p>", start) + len("</p>")]
            if wrapper.count(health_page.REFRESH_LIVE_DOT_ATTR) != 1:
                return False, (
                    "expected exactly one %s inside .page-header__freshness, got %d"
                    % (health_page.REFRESH_LIVE_DOT_ATTR,
                       wrapper.count(health_page.REFRESH_LIVE_DOT_ATTR)))
            dot_at = wrapper.index(health_page.REFRESH_LIVE_DOT_ATTR)
            tag = wrapper[wrapper.rindex("<", 0, dot_at):wrapper.index(">", dot_at) + 1]
            if 'class="dot dot--off"' not in tag:
                return False, (
                    "expected the live dot to be the app's own NEUTRAL dot and nothing else — a "
                    "refresh loop that is listening is not a device verdict and must not borrow "
                    "one's colour, got %r" % (tag,))
            for verdict in ("dot--ok", "dot--warn", "dot--error", "status-warn", "accent"):
                if verdict in tag:
                    return False, (
                        "expected no status/accent token on the live dot, found %r in %r"
                        % (verdict, tag))
            if 'aria-hidden="true"' not in tag:
                return False, (
                    "expected the live dot to be aria-hidden — it is decorative, and the loop's "
                    "real state is already announced by the Paused/Reconnecting badge beside it")
            # Server-rendered STATIC. The motion is one class
            # companion/static/freshness.js adds, so a scripts-blocked
            # page shows a still dot beside an age that does not move,
            # which is exactly what is true there.
            if "is-breathing" in wrapper:
                return False, (
                    "expected the server to render the dot STILL — the breathing class is "
                    "freshness.js's to add, and a server-rendered one would breathe on a page "
                    "with no loop running at all, got %r" % (wrapper,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's freshness line carries exactly one neutral, aria-hidden live dot — the app's own "
        "off dot with no status or accent token and no breathing class at render time, because the "
        "motion belongs to the loop that knows whether it is listening (D22, 23-05-PLAN.md Task 2)",
        _health_freshness_line_carries_a_neutral_live_dot)

    def _health_freshness_clock_is_a_ticking_age_over_the_loaded_at_instant():
        tmp = _mkstate("h-ticking-age")
        try:
            now_iso = _iso(_now())
            rendered = health_page.render(_ctx(tmp, now=now_iso))
            start = rendered.index('<p class="page-header__freshness')
            wrapper = rendered[start:rendered.index("</p>", start) + len("</p>")]
            # The element, over the SAME instant data-loaded-at carries —
            # not a second instant computed beside it.
            #
            # 23-06-PLAN.md (the no-JS remainder 23-05 recorded as
            # finding 2): RETARGETED IN PLACE and strictly strengthened.
            # 23-05 rendered the LADDER's own output as this element's
            # server text, so a scripts-blocked reader saw "Updated 0s
            # ago" frozen at load — 19-09/A-20's own frozen zero,
            # reintroduced for the one reader who has no ticker to
            # advance it. The server now renders the CLOCK inside the
            # same <time data-relative> element (true forever, and the
            # value this line carried before 23-05) and the ticker
            # replaces it with the live age the moment it runs. Both
            # readers get a true statement; neither gets a frozen zero.
            clock_text = layout.local_clock_text(
                layout.parse_iso(now_iso), now_parsed=layout.parse_iso(now_iso))
            expected = layout.relative_time_html(
                now_iso, now_iso, static_text=clock_text)
            if expected not in wrapper:
                return False, (
                    "expected the freshness line's value to be layout.relative_time_html() over "
                    "the same instant data-loaded-at carries (%r), got %r" % (expected, wrapper))
            # THE ANTI-VACUITY HALF, and the reason this check is not
            # satisfied by "an element is present": what a WRONG
            # implementation does here is render an age that nothing can
            # advance. So the element's own server text is asserted to BE
            # the clock and asserted NOT to be the ladder's zero bucket,
            # in both languages — a relative age server-rendered into
            # this element is the defect, not the enhancement.
            element = re.search(r"<time ([^>]*)>(.*?)</time>", wrapper, flags=re.S)
            if element is None:
                return False, (
                    "expected a <time> element in the freshness line, got %r" % (wrapper,))
            attrs, element_text = element.group(1), element.group(2)
            if "data-relative" not in attrs or "datetime=" not in attrs:
                return False, (
                    "expected the freshness element to stay a <time datetime=... data-relative> "
                    "— the clock is the server's floor and the ticker's hook is what upgrades "
                    "it, got %r" % (attrs,))
            if element_text != layout.escape_html(clock_text):
                return False, (
                    "expected the SERVER to render the clock %r inside the <time> element — a "
                    "scripts-blocked reader has nothing to advance an age, got %r"
                    % (clock_text, element_text))
            for lang in ("en", "fr"):
                frozen_zero = layout.escape_html(layout.relative_age_text(0, lang=lang))
                if element_text == frozen_zero:
                    return False, (
                        "the freshness line server-renders the ladder's ZERO bucket (%r) — that "
                        "is A-20's own frozen zero, true at load and never again for a reader "
                        "with no scripts" % (frozen_zero,))
            # data-loaded-at stays exactly once, page-wide: freshness.js
            # reads it with a single querySelector and a second would
            # silently win.
            if rendered.count("data-loaded-at") != 1:
                return False, (
                    "expected exactly one data-loaded-at page-wide, got %d"
                    % rendered.count("data-loaded-at"))
            if rendered.count("data-refresh-pill") != 1:
                return False, (
                    "expected exactly one data-refresh-pill page-wide, got %d"
                    % rendered.count("data-refresh-pill"))
            # Nothing lost: the full Europe/Paris local timestamp is
            # still on the clock span's title (22-16's D-05/CFG-28
            # conversion), and the raw ISO still does not survive.
            expected_title = layout.escape_html(
                health_page._full_local_timestamp_text(now_iso))
            if ('title="%s"' % expected_title) not in wrapper:
                return False, (
                    "expected the absolute timestamp to stay available in the element's tooltip "
                    "(%r), got %r" % (expected_title, wrapper))
            # The <time> element is INSIDE the .page-header__freshness
            # wrapper, which is one of REFRESH_SWAP_SELECTORS' entries —
            # so the value a swap replaces and the value the ticker
            # advances are the same one.
            if ".page-header__freshness" not in health_page.REFRESH_SWAP_SELECTORS:
                return False, (
                    "expected .page-header__freshness to still be a swap target — the ticking "
                    "age is honest between swaps and reset by them")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's freshness line is a <time data-relative> over the same instant data-loaded-at "
        "carries whose SERVER text is the clock — never the ladder's zero bucket, which is the "
        "frozen age A-20 removed — with the absolute timestamp still in the element's tooltip, "
        "exactly one data-loaded-at and one data-refresh-pill page-wide, and the wrapper still a "
        "swap target (D22's remainder, 23-05-PLAN.md Task 2; the no-JS half retargeted in place "
        "by 23-06-PLAN.md)",
        _health_freshness_clock_is_a_ticking_age_over_the_loaded_at_instant)

    def _freshness_js_breathes_only_from_the_loops_own_state():
        # T-23-15: a dot that breathes while the page is not actually
        # listening is a lie the user has no way to check. The mitigation
        # is structural rather than careful — the class is DERIVED from
        # the loop's own two state variables inside one function, and
        # that function is called from the four places the loop's state
        # already changes. There is no second timer and no second
        # variable tracking liveness.
        js_path = os.path.join(HERE, "static", "freshness.js")
        with open(js_path) as fh:
            js = fh.read()
        if "function syncLiveDot()" not in js:
            return False, (
                "expected freshness.js to derive the breathing class in ONE function — two "
                "sources for one claim is this codebase's most repeated defect")
        if "intervalHandle !== null && currentState === null" not in js:
            return False, (
                "expected the breathing class to be DERIVED from the loop's own interval handle "
                "AND its own state badge — either half alone lets the dot breathe while the "
                "page is paused or failing (T-23-15)")
        # Called from every function that changes either half, and from
        # nowhere else. setState() covers both paused and reconnecting;
        # clearState() covers recovery and return-from-hidden; start/stop
        # cover the interval itself, including tick()'s own belt-and-
        # braces stop in a background tab.
        for owner, body_end in (
                ("function setState(state) {", "function clearState()"),
                ("function clearState() {", "// 23-05-PLAN.md Task 2"),
                ("function startLoop() {", "function stopLoop()"),
                ("function stopLoop() {", "document.addEventListener")):
            if owner not in js:
                return False, "expected %r in freshness.js" % owner
            region = js[js.index(owner):js.index(body_end, js.index(owner))]
            if "syncLiveDot()" not in region:
                return False, (
                    "expected syncLiveDot() to be called from %s — the breathing class must "
                    "change where the loop's own state changes, never from a second state "
                    "machine beside it" % owner)
        if js.count("syncLiveDot();") != 4:
            return False, (
                "expected exactly four syncLiveDot() call sites (setState, clearState, "
                "startLoop, stopLoop), got %d — a fifth caller is a second state machine"
                % js.count("syncLiveDot();"))
        # The loop still never paints its own failure as a device fault.
        for verdict in ("dot--warn", "dot--error", "status-warn"):
            if verdict in js:
                return False, (
                    "freshness.js must carry no status vocabulary — a browser that lost its "
                    "connection is not a device fault (22-15's own argued ground), found %r"
                    % verdict)
        # 22-15's own work, byte-for-byte present: the ladder, its
        # ceiling and the in-flight guard are NOT re-implemented here.
        for untouched in ("RETRY_BASE_MS", "RETRY_CEILING_MS = 600000",
                          "function failAndRetry()", "inFlight", "isEqualNode"):
            if untouched not in js:
                return False, (
                    "expected 22-15's own %r to survive untouched — this plan adds the two "
                    "things T13 deliberately left for Phase 23 and re-implements none of it"
                    % untouched)
        # The dot's own selector and class must agree with the Python
        # that renders the element and the CSS that animates it.
        if health_page.REFRESH_LIVE_DOT_ATTR not in js:
            return False, (
                "freshness.js does not name %r — health_page.py renders the hook and this file "
                "is the only thing that toggles it" % health_page.REFRESH_LIVE_DOT_ATTR)
        css_source = _css_source()
        if ".is-breathing {" not in css_source:
            return False, (
                "expected companion/static/style.css to declare the breathing rule freshness.js "
                "toggles — a class with no rule is motion nobody ever sees")
        return True, ""
    check(
        "freshness.js DERIVES the breathing class from its own interval handle and state badge in "
        "one function, called from exactly the four places its state already changes, carries no "
        "status vocabulary, leaves 22-15's retry ladder/ceiling/in-flight guard/targeted swap "
        "untouched, and agrees with both the Python hook and the CSS rule (T-23-15, "
        "23-05-PLAN.md Task 2)",
        _freshness_js_breathes_only_from_the_loops_own_state)

    # ======================================================================
    # Section 3: one end-to-end check — a real companion/app.py subprocess,
    # logged in, fetching both tab routes against a seeded database.
    # ======================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        now = _now()
        # quick task 260901-uzi Task 4: two readings, not one — the
        # readout element and its chart only render when at least two
        # numeric battery rows exist (_battery_section()'s own
        # len(trend_rows) >= 2 gate); a single-reading fixture would make
        # the in-place extension below fail to find the readout at all,
        # for a reason unrelated to the fix it is checking.
        _seed_device_health(harness.tmpdir, [
            (_iso(now - timedelta(minutes=1)), 4200),
            (_iso(now), 4190),
        ])
        _seed_meta(harness.tmpdir, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
        _seed_unresolved_prefixes(harness.tmpdir, {
            "ABC": {"count": 2, "first_seen": _iso(now), "last_seen": _iso(now), "example_callsign": "ABC123"},
        })
        # quick task 260901-uzi Task 4: a resolved runway event so
        # resolution_stats()'s total is non-zero and _stats_table_html()
        # actually renders a table — without this the prose modifier the
        # in-place extension below checks for would never appear in this
        # fixture, no matter what the fix does.
        _seed_runway_events(harness.tmpdir, [
            {"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}])

        def _both_tabs_ok_end_to_end():
            for path, heading in (
                    ("/health", "Health"), ("/airlines", "Airlines"),
                    # quick task 260903-btu Task 5: /history added so the
                    # served-HTML twin of Task 4's render-level History
                    # guard runs against a real running service, not only
                    # an in-process render() call.
                    ("/flights", "Flights")):
                status, _headers, body = http_request(base + path, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200 for %s, got %d" % (path, status)
                if heading.encode() not in body:
                    return False, "expected the %r heading in %s's response body" % (heading, path)
                if path == "/health":
                    # quick task 260901-tsa: the automated half of
                    # "verified against a real running service" — a
                    # real subprocess, a real login, a real seeded
                    # database, a real HTTP response, not only an
                    # in-process render() call.
                    body_text = body.decode("utf-8", errors="replace")
                    for constant in (
                            health_page.PAGE_PURPOSE_TEXT,
                            health_page.SCREEN_SECTION_DESCRIPTION,
                            health_page.SERVER_DATA_SECTION_DESCRIPTION):
                        escaped = layout.escape_html(constant)
                        if escaped not in body_text:
                            return False, (
                                "expected %r in the real /health HTTP response body" % (constant,))
                    for label in (
                            health_page.DEVICE_FRESHNESS_LABEL,
                            health_page.PIPELINE_FRESHNESS_LABEL):
                        label_count = body_text.count(label)
                        if label_count != 1:
                            return False, (
                                "expected %r exactly once in the real /health HTTP response "
                                "body, got %d" % (label, label_count))

                    # 260902-chc: the automated half of "the running
                    # service really serves the reversal" — a real
                    # subprocess, a real login, a real seeded database, a
                    # real HTTP response, proving the pill (not the
                    # retired manual Refresh link/stale banner) is what
                    # actually reaches a browser.
                    if body_text.count("data-refresh-pill") != 1:
                        return False, (
                            "expected the pill marker exactly once in the real /health HTTP "
                            "response body, got %d" % body_text.count("data-refresh-pill"))
                    pill_start = body_text.index("data-refresh-pill")
                    pill_tag = body_text[
                        body_text.rindex("<", 0, pill_start):body_text.index(">", pill_start) + 1]
                    if " hidden" not in pill_tag:
                        return False, "expected the real /health response's pill to carry the bare hidden attribute"
                    if "data-stale-banner" in body_text:
                        return False, "expected zero stale-banner markers in the real /health HTTP response body"

                    # quick task 260901-uzi Task 4: the automated half of
                    # "verified against a real running service" for the
                    # four Health fixes — a real subprocess, a real
                    # login, a real seeded database, a real HTTP
                    # response, not only an in-process render() call.
                    nested_count = body_text.count("page-section--nested")
                    if nested_count != 2:
                        return False, (
                            "expected page-section--nested exactly twice in the real "
                            "/health HTTP response body, got %d" % nested_count)
                    prose_count = body_text.count("data-table--prose")
                    if prose_count != 1:
                        return False, (
                            "expected data-table--prose exactly once in the real /health "
                            "HTTP response body, got %d" % prose_count)
                    if "battery-readout__value" not in body_text:
                        return False, "expected the readout's value span in the real /health HTTP response body"
                    if "battery-readout__detail" not in body_text:
                        return False, "expected the readout's detail span in the real /health HTTP response body"
                    readout_start = body_text.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
                    readout_end = body_text.index("</p>", readout_start) + len("</p>")
                    readout_slice = body_text[readout_start:readout_end]
                    visible = re.sub(r"<[^>]*>", "", readout_slice)
                    if re.search(r"\d{4}-\d{2}-\d{2}T", visible):
                        return False, (
                            "expected no raw ISO string in the real /health response's readout "
                            "own slice, got %r" % visible)

                    # quick task 260902-bl2 Task 3: the automated half of
                    # "verified against a real running service" for the
                    # Description-column fix — a real subprocess, a real
                    # login, a real seeded database, a real HTTP response,
                    # not only an in-process render() call.
                    desc_count = body_text.count('<td class="desc">')
                    expected_desc = len(health_page._SOURCE_ROWS)
                    if desc_count != expected_desc:
                        return False, (
                            "expected exactly %d desc-class cells in the real /health HTTP response "
                            "body, got %d" % (expected_desc, desc_count))
                    stats_at = body_text.index(health_page.STATS_SECTION_HEADING)
                    first_desc_at = body_text.index('<td class="desc">')
                    if first_desc_at < stats_at:
                        return False, (
                            "expected the desc-class cells to fall after the Resolution-statistics "
                            "heading in the real /health HTTP response body")

                elif path == "/airlines":
                    # quick task 260903-btu Task 5a: the served-HTML twin
                    # of Task 1/3's render()-level replace-form checks —
                    # a real subprocess, a real login, a real HTTP
                    # response, not only an in-process render() call.
                    body_text = body.decode("utf-8", errors="replace")
                    retired_token = "airline-card__" + "replace"
                    if retired_token in body_text:
                        return False, "expected zero occurrences of the retired per-card class token in the real /airlines HTTP response body"
                    # 29-01-PLAN.md (CFG-81): the replace/resolve-upload/
                    # delete forms are unconditional now — the second,
                    # real fetch of "?edit=1" this check used to need is
                    # deleted (it would now be byte-identical to the
                    # plain /airlines response already captured in
                    # body_text above; a second real fetch to prove that
                    # is a duplicate, not a new property).
                    #
                    # quick task 260903-df3: a bare substring count of
                    # LIGHTBOX_REPLACE_FORM_CLASS ("lightbox__replace")
                    # is no longer unambiguous — it is now also a prefix
                    # of LIGHTBOX_REPLACE_ZONE_CLASS/REPLACE_HINT_CLASS/
                    # REPLACE_ICON_CLASS (all "lightbox__replace-*"), each
                    # occurring once in the shared lightbox's own markup.
                    # The literal below carries a trailing quote after %s
                    # so only the <form class="..."> attribute value
                    # itself is counted, the same trailing-quote
                    # technique _replace_form_action_matches_trigger_attribute_membership()
                    # already uses.
                    replace_form_count = body_text.count('class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
                    if replace_form_count != 1:
                        return False, (
                            "expected airlines_page.LIGHTBOX_REPLACE_FORM_CLASS exactly once in the real "
                            "/airlines HTTP response body, got %d" % replace_form_count)
                    replace_actions = re.findall(
                        r'%s="([^"]+)"' % re.escape(airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR), body_text)
                    if not replace_actions:
                        return False, (
                            "expected at least one %r attribute in the real /airlines HTTP response body"
                            % (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR,))
                    for action in replace_actions:
                        if "?v=" in action:
                            return False, (
                                "expected no data-view-panel-replace-action value to carry a cache buster "
                                "in the real /airlines HTTP response body, found one on %r" % (action,))
                    # Phase 14 (14-02-PLAN.md Task 3) retargeted these two
                    # assertions in place (no count change to
                    # EXPECTED_CHECK_COUNT — this is the same check,
                    # re-scoped): a bare substring count of 'action=""'
                    # is no longer unambiguous now that every trigger
                    # carries the full data-view-panel-* vocabulary,
                    # including data-view-panel-upload-action="" and
                    # data-view-panel-delete-action="" on every plain
                    # curated card — both contain the literal substring
                    # 'action=""' without being a real HTML `action`
                    # attribute at all. A leading space isolates the
                    # real attribute (`<form ... action="">`) from a
                    # hyphenated data-attribute name ending in
                    # "-action" (which has no space immediately before
                    # "action"). The expected count is 3, not 1: the
                    # shared dialog now carries three real empty-action
                    # forms (replace, resolve-upload, delete) — the
                    # resolve-name form's own action is never empty (it
                    # always posts to RESOLVE_ROUTE, in both the dialog
                    # and the no-JS fallback).
                    if body_text.count(' action=""') != 3:
                        return False, (
                            "expected ' action=\"\"' exactly 3 times (replace/resolve-upload/delete "
                            "forms) in the real /airlines HTTP response body, "
                            "got %d" % body_text.count(' action=""'))
                    # Phase 14 (14-02-PLAN.md Task 3) retargeted: the
                    # dialog now also carries the resolve-upload form's
                    # own file input, alongside the pre-existing replace
                    # form's, so the expected count is 2, not 1.
                    if body_text.count('<input type="file"') != 2:
                        return False, (
                            "expected <input type=\"file\" exactly twice (replace form, resolve-upload "
                            "form) in the real /airlines HTTP response "
                            "body, got %d" % body_text.count('<input type="file"'))

                elif path == "/flights":
                    # quick task 260903-btu Task 5a: the served-HTML twin
                    # of Task 4's render()-level History guard.
                    body_text = body.decode("utf-8", errors="replace")
                    for token, label in (
                            (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS"),
                            (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR"),
                            ("enctype", "enctype"),
                            ('<input type="file"', '<input type="file"')):
                        count = body_text.count(token)
                        if count != 0:
                            return False, (
                                "expected zero occurrences of %s in the real /history HTTP response body, "
                                "got %d" % (label, count))

            # quick task 260902-bl2 Task 3: the automated half of "the new
            # CSS is actually served" — companion/app.py's pre-auth
            # STYLE_ROUTE, fetched from this same running service, proving
            # the running process hands the new/changed rules to a
            # browser, not only that the on-disk file says the right
            # thing (Checks 1/2 above already cover the on-disk half).
            css_status, _css_headers, css_body = http_request(
                base + app.STYLE_ROUTE, cookie=session_cookie)
            if css_status != 200:
                return False, "expected 200 for %s, got %d" % (app.STYLE_ROUTE, css_status)
            css_text = css_body.decode("utf-8", errors="replace")
            for needle, label in (
                    (".data-table td.desc {", "the description-column rule"),
                    ("margin-bottom: var(--space-md)", "the demotion rule's new bottom margin"),
                    (".page-section--nested > p.text-body", "the prose rhythm rule's selector")):
                if needle not in css_text:
                    return False, (
                        "expected %s (%r) in the real %s response body" % (label, needle, app.STYLE_ROUTE))

            # 260902-chc: beside the STYLE_ROUTE fetch above and
            # following its exact pattern — a real fetch of the
            # freshness-script route from this same running service,
            # proving the process hands a browser the new loop, not only
            # that the on-disk file says so.
            #
            # 19-09-PLAN.md (D-02): retargeted in place (same check name/
            # function, same "real served bytes" pattern) — required
            # needles for the fetch-and-swap DOM contract (the
            # [data-loaded-at]/[data-refresh-pill] attribute hooks), plus
            # a pass asserting every one of health_page.
            # REFRESH_SWAP_SELECTORS' own selector strings appears
            # verbatim in the real served bytes — the duplicated-not-
            # imported agreement between the page module's declared swap
            # targets and the script's own, pinned against the process
            # actually serving them, not only the two on-disk files
            # agreeing with each other.
            #
            # 21-02-PLAN.md (D-18): the [data-refresh-toggle] needle
            # 19-09-PLAN.md required is removed (the hook no longer
            # exists) and replaced with the opposite-direction regression
            # pin below — the served bytes must NOT carry the deleted
            # pause mechanism's own hooks, so the branch cannot come back
            # through the served file undetected.
            js_status, _js_headers, js_body = http_request(
                base + app.FRESHNESS_SCRIPT_ROUTE, cookie=session_cookie)
            if js_status != 200:
                return False, "expected 200 for %s, got %d" % (app.FRESHNESS_SCRIPT_ROUTE, js_status)
            js_text = js_body.decode("utf-8", errors="replace")
            for needle, label in (
                    ("AUTO_REFRESH_INTERVAL_MS", "the named interval constant"),
                    ("visibilitychange", "the visibility-change listener registration"),
                    ("[data-loaded-at]", "the loaded-at attribute hook"),
                    ("[data-refresh-pill]", "the refresh-pill attribute hook")):
                if needle not in js_text:
                    return False, (
                        "expected %s (%r) in the real %s response body"
                        % (label, needle, app.FRESHNESS_SCRIPT_ROUTE))
            for forbidden in ("data-pause-text", "wireToggle"):
                if forbidden in js_text:
                    return False, (
                        "expected zero occurrences of %r in the real %s response body — "
                        "the pause branch must not come back through the served file (D-18)"
                        % (forbidden, app.FRESHNESS_SCRIPT_ROUTE))
            for selector in health_page.REFRESH_SWAP_SELECTORS:
                if selector not in js_text:
                    return False, (
                        "expected health_page.REFRESH_SWAP_SELECTORS entry %r verbatim in the "
                        "real %s response body" % (selector, app.FRESHNESS_SCRIPT_ROUTE))
            return True, ""
        check(
            "GET /health, GET /airlines and GET /history all return 200 with their own page heading against a "
            "real running service, /health's real HTTP response body carries the page purpose, both section "
            "descriptions, no duplicated freshness label, the auto-refresh pill (hidden) and zero stale-banner "
            "markers, the nested modifier twice, the prose modifier once, both readout spans, no raw ISO in "
            "the readout's own slice, and the desc-class cells at their expected count after the "
            "Resolution-statistics heading, /airlines' real HTTP response body carries zero occurrences of "
            "the retired per-card replace class, exactly one lightbox replace form and one action=\"\" and "
            "one file input, and at least one un-busted replace-action trigger attribute, /history's real "
            "HTTP response body carries zero occurrences of the replace-form class, replace-action attribute, "
            "enctype or file input (quick task 260903-btu Task 5a), and the real served stylesheet "
            "(STYLE_ROUTE) carries the description-column rule, the demotion rule's new bottom margin and the "
            "prose rhythm rule's selector, and the real served freshness script (FRESHNESS_SCRIPT_ROUTE) "
            "carries the interval constant, the visibility-change listener, the [data-loaded-at]/"
            "[data-refresh-pill] attribute hooks, carries zero occurrences of the deleted "
            "data-pause-text/wireToggle pause-branch hooks (D-18), and every "
            "health_page.REFRESH_SWAP_SELECTORS entry verbatim (quick task 260901-tsa; extended in place by "
            "quick task 260901-uzi finding 1/2/3/4, quick task 260902-bl2 Task 3, quick task 260902-chc, "
            "quick task 260903-btu Task 5a, 19-09-PLAN.md Task 3, and 21-02-PLAN.md Task 2)",
            _both_tabs_ok_end_to_end)

        def _illustration_route_serves_normalized_bytes_end_to_end():
            # quick task 260902-req-02 Task 2: the automated half of
            # "verified against a real running service" for the
            # normalization route wiring — a real subprocess, a real
            # login, a real HTTP response, not only an in-process
            # illustration_normalize.normalized_png_bytes() call.
            key = illustrations.normalise_airline_key("Air France")
            path = illustrations.illustration_path_for_key(key)
            with open(path, "rb") as fh:
                raw_bytes = fh.read()

            status, _headers, served_bytes = http_request(
                base + app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + key + ".png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for a known illustration key, got %d" % status
            if served_bytes == raw_bytes:
                return False, "expected the served bytes to differ from the raw file bytes (normalization ran)"
            with Image.open(io.BytesIO(served_bytes)) as decoded:
                if decoded.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                    return False, "expected the served image to decode to %r, got %r" % (
                        illustration_normalize.ILLUSTRATION_TARGET_SIZE, decoded.size)

            unknown_status, _unknown_headers, _unknown_body = http_request(
                base + app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + "not-a-real-airline-key.png",
                cookie=session_cookie)
            if unknown_status != 404:
                return False, "expected 404 for an unknown illustration key, got %d" % unknown_status
            return True, ""
        check(
            "GET /illustration/{key}.png against a real running service serves normalized bytes that differ "
            "from the raw vendored file and decode to illustration_normalize.ILLUSTRATION_TARGET_SIZE, and an "
            "unknown key still 404s",
            _illustration_route_serves_normalized_bytes_end_to_end)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("status-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
