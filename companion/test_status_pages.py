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
import companion.i18n_fr.nav as i18n_fr_nav  # noqa: E402
from companion.pages import airlines_page, health_page  # noqa: E402
import companion.wake as wake  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import illustrations  # noqa: E402
from server.plane import manual_resolutions  # noqa: E402
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
EXPECTED_CHECK_COUNT = 73  # 146 - 73 (33-29: part 05's 73 checks), re-derived
# by RUNNING (146/146 pass).


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

    # --- shared helpers still used by later (not yet migrated) checks
    # below, kept here after 33-29 removed the Section 1/Section 2 checks
    # that used to define them alongside their own first use ------------

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

    _NAV_STATUS_DEVICE_CFG = {"display_enabled": True, "quiet_hours_enabled": False}

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
