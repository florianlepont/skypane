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
EXPECTED_CHECK_COUNT = 25  # 73 - 48 (33-30: part 06's 48 checks), re-derived
# by RUNNING (73/73 pass).


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

    # --- shared helpers still used by later (not yet migrated) checks
    # below, kept here after 33-30 removed the checks that used to define
    # them alongside their own first use ----------------------------------

    def _frame_strip_ctx(last_checkin_ts, device_config, now):
        return {
            "last_checkin_ts": last_checkin_ts, "device_config": device_config, "now": now,
        }

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

    _TAB_BAR_BANNER = "The bottom tab bar (X9, 22-14-PLAN.md Task 1"


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
