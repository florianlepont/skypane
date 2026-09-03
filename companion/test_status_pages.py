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
from companion import auth, illustration_normalize, layout  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import illustrations  # noqa: E402
from server.plane import render as panel_render  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

TEST_PASSWORD = "status-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
# 44 (pre-06.6-01) + 2 (06.6-01 Task 1: layout timestamp-helper promotion
# checks) + 1 (06.6-01 Task 2: Battery Trend absolute+relative timestamp check)
# 49 (pre-06.6.3-04) + 5 (06.6.3-04 Task 1: readings-disclosure ordering, D-10
# window label, specific anomaly-category banner, corroboration
# no-decision-ID-leak, Device/pipeline concise-timestamp format)
# 54 + 0 (06.6.3-04 Task 2: roving tabindex — an existing pinned check was
# retargeted in place, not counted as new)
# 54 + 1 (06.6.3-04 Task 3: freshness Refresh action + stale-view banner) —
# the pre-existing four-icon check is retargeted in place (five icon
# instances now: four Health signals + one Refresh action), not counted as new
# 55 + 3 (06.6.3-06 Airlines: promoted-headline document-order check, concise-
# timestamp + filter-bar-markers check, filter-bar-has-no-button/form check) —
# two pre-existing Airlines checks (the iconless check, the two-tiles/Coverage-
# heading check) are retargeted in place for this plan's own D-18/D-20 changes,
# not counted as new
# 59 (pre-06.6.4.1-04) + 5 (06.6.4.1-04 Task 1: anomaly-banner category-
# pill checks x3, corroboration-disclosure checks x2)
# 64 + 3 (06.6.4.1-04 Task 2: sparkline axis-label check, seeded-readout
# check, single-reading-still-no-chart regression guard)
# 67 + 5 (06.6.4.1-04 Task 3: Server & data grid/migrated-cards check,
# Resolution-rate tile check, registry-card filter/note/Clear check,
# migrated-cards failure-isolation check, _read_health_inputs() no-new-
# key source assertion) — the old dashboard-grid/Overview check was
# retargeted in place onto the new two-section heading structure, not
# counted as new
# 72 - 15 + 6 (06.6.4.1-06 Task 1: Airlines' CFG-04/CFG-08 diagnostics
# checks deleted — render() stops emitting that content from this task
# onward (their Health-side equivalents already exist, added by plan 04);
# 6 new gallery checks added — card count, image-source route-membership,
# Air Caraïbes' three chips, no-chips-container for a primary-only
# airline, variant_chip_label()'s two display domains, and the
# ILLUSTRATION_ROUTE_PREFIX cross-module equality). One pre-existing
# check (page_header presence) is unchanged/retargeted in place, not
# counted as new or deleted.
# 63 + 5 (06.6.4.1-06 Task 2: gallery filter-bar four-marker check, Clear
# is a real <button> check, label-for/input-id check, count/empty-body
# real-total check, per-card data-filter-text/-group check)
# 68 + 4 (06.6.4.1-06 Task 3: D-17 no-history_db/poll_loop/sqlite-import
# source guard, D-13 Airlines-no-longer-renders-migrated-headers guard,
# Health-still-renders-both-header-sets guard, no-deleted-diagnostics-
# symbol-exposed guard) — every check that exercised a now-deleted
# Airlines diagnostics symbol was already removed in Task 1, pulled
# forward from this task by the per-task green-suite verification loop;
# their Health-side equivalents were added by plan 04.
# 72 + 5 (quick task 260901-tsa Task 3: page-purpose-after-Refresh check,
# both section-intros pair-heading-with-description check, Device/
# Pipeline no-duplicated-label + real stat-tile__value check, battery
# readout precedes-chart/class-list/live-region check, cross-file CSS
# DOM-contract guard for .section-intro/.section-intro > p/
# .stat-tile__value .mono/.battery-readout). Task 2's three retargets
# (independent-thresholds, battery-badge, Server & data grid) and this
# task's live-HTTP extension of _both_tabs_ok_end_to_end() were all done
# in place — no count change from either.
# 77 + 5 (quick task 260901-uzi Task 4: .dashboard-grid stretch stylesheet
# guard, nested-heading-tier markup+stylesheet check, prose-table-opts-
# out-alone markup+stylesheet check, humanised-readout end-to-end
# markup+cross-file-JS check, readout typographic-split stylesheet
# guard). Tasks 1-3's in-place retargets (the Server & data grid check,
# the CSS DOM-contract guard's .stat-tile__value .mono literal, the
# seeded-readout and readout-position/class-list checks) and this task's
# live-HTTP extension of _both_tabs_ok_end_to_end() (the nested/prose
# modifier counts, both readout spans, the no-raw-ISO-in-readout
# assertion, plus a resolved runway event added to the fixture so the
# prose table actually renders) were all done in place — no count change
# from either. Finding 5 (the readings-history disclosure header
# clipping) shipped no code change and therefore adds no check; its
# verdict is recorded in the SUMMARY, not the harness.
# 82 + 2 (quick task 260902-bl2 Task 3: Check 1 — the Description column
# is the only muted column end to end (markup + builder + stylesheet);
# Check 2 — all three nested cards show one heading-to-content rhythm,
# in both the empty and seeded state (markup + stylesheet)). Tasks 1-2's
# in-place retargets (none were needed — no pre-existing check keyed on
# a bare Description <td> or on the pre-fix heading-to-content gap) and
# this task's live-HTTP extension of _both_tabs_ok_end_to_end() (the
# desc-class cell count/position, plus a real STYLE_ROUTE fetch proving
# the served stylesheet carries the description-column rule, the
# demotion rule's new bottom margin and the prose rhythm rule's
# selector) were done in place — no count change from either.
# 84 + 5 (quick task 260902-chc Task 3: the D-12 reversal is recorded in
# both prose files it touches, the auto-refresh loop's own contract from
# freshness.js's shipped source, the pill's markup contract on a real
# render — both seeded and on a fresh state directory with no readings —
# the pill's stylesheet contract, and the interaction-skip guard's
# cross-file DOM contract). Tasks 1-2's in-place retargets (the D-12
# refresh/stale-banner check rewritten as the reversal's own guard, the
# page-purpose ordering check's lookup retargeted onto the pill's marker
# attribute, the five-icon check's comment/message updated from "Refresh
# action" to "pill") and this task's live-HTTP extension of
# _both_tabs_ok_end_to_end() (the pill hidden-by-default + zero
# stale-banner assertions on the real /health response, plus a real fetch
# of FRESHNESS_SCRIPT_ROUTE proving the served script carries the
# interval constant and the visibility-change listener) were all done in
# place — no count change from either.
# 89 + 1 (quick task 260902-dng Task 1: the battery-trend chart's
# scale-bound check — viewBox/width/height/preserveAspectRatio parsed
# off a real battery_sparkline_svg() return, the CSS declared height
# parsed off style.css and asserted equal to the SVG's own height
# attribute, min(containerWidth/viewBoxWidth, 1) computed at the five
# derived real container widths and asserted within [0.80, 1.00], and
# every emitted coordinate asserted inside the viewBox). The three
# pre-existing sparkline checks pin no coordinate literals, so the
# _AXIS_LEFT_GUTTER/plot_width/plot_height resize needed no retarget.
# 90 + 1 (quick task 260902-dng Task 2: .data-table th's padding
# shorthand parsed from style.css, asserting a non-zero top value and
# (by construction of the two-value shorthand) top/bottom symmetry —
# closes 260901-uzi Finding 5 candidate (a), shipped no check of its
# own at the time).
# 91 + 1 (quick task 260902-dng Task 3: .stat-tile__caption's new
# --weight-semibold declaration (with no font-size of its own, so no
# fifth size), plus the Server & data region's four text roles —
# section heading (20/regular), stat-tile caption (14/semibold), tile
# value (16/semibold), nested card title (16/semibold) — still forming
# a coherent, strictly-size-ordered set against the real token values).
# 92 + 0 (quick task 260902-ep7 Task 1: BUG 1's out-of-flow pill fix —
# _quick_260902_chc_pill_stylesheet_contract() strengthened IN PLACE to
# also pin .page-header's containing block and the .page-header-scoped
# .refresh-pill absolute-position rule; no new check, no count change).
# 92 + 1 (quick task 260902-ep7 Task 2 Commit A: BUG 2's card-to-card vs.
# section-to-section spacing split, pinned as a pair — .dashboard-grid's
# margin-bottom must equal .page-section's own card-to-card value while
# staying smaller than .battery-trend-section's untouched section-
# transition value).
# 93 + 1 (quick task 260902-ep7 Task 2 Commit B: BUG 3's disclosure-
# summary accent broadening, pinned as a pair — the bare summary rule
# declares var(--color-accent), and style.css's own exhaustive
# accent-reservation list explicitly names the summary's label text, not
# just its ::marker).
# 94 + 1 (quick task 260902-ep7 Task 3: BUG 4's real axis chrome — at
# least one full-height vertical axis <rect>, at least one full-width
# horizontal axis <rect>, and at least two tick <rect> elements, all
# aria-hidden. The six pre-existing <polyline-based "a chart rendered"
# markers, the axis-label lookup, the scale-bound check, and the
# readout-precedes-chart sparkline marker were all retargeted/rewritten
# IN PLACE — no count change from any of them).
# 95 + 1 (quick task 260902-gjj Task 1: the muted-caption pair — both the
# battery heading's trailing span and the Unresolved-prefixes read-only
# note compose section-caption with their existing sizing class, plus the
# CSS half pinning .section-caption to a single 70%-muted declaration).
# 96 + 2 (quick task 260902-gjj Task 2 Commit A: the battery-trend/
# Unresolved-prefixes cards render the correct card_status_class()
# modifier off battery_status()/coverage_status()'s own real value, the
# Resolution-statistics card carries none, and every doubled-form status
# selector sits after its own component's hover rule in source order).
# 98 + 1 (quick task 260902-gjj Task 2 Commit B: the two dot removals are
# scoped to the battery-trend/Unresolved-prefixes cards — the surviving
# Corroboration dots are asserted present, not just the two removals
# asserted absent — and BATTERY_STATUS_LABEL/_battery_badge_block are
# both confirmed retired via hasattr).
# 99 + 1 (quick task 260902-iag Task 3: the two-tier-hierarchy-carried-
# by-layout check — Health's D-10 section headings vs. the cards nested
# inside them now read apart via containment, spacing and adjacency
# instead of font-size. Markup half: every level-2 heading sits inside a
# bordered card <section>, both level-1 headings sit inside the plain
# .section-intro row with no card class, and a .dashboard-grid always
# intervenes between a level-1 heading and its section's first level-2
# card, in both the empty and seeded state. Stylesheet half: the four
# spacing tiers that now carry the distinction — .battery-trend-section's
# section-transition margin, .page-section's/.dashboard-grid's shared
# same-section card-to-card margin, the reverted nested-heading rule's
# retained heading-to-content margin, and the heading-rhythm rule's own
# margin — stay strictly ordered against their real :root token values.
# Task 1's two retargets (the demotion check inverted to assert the
# reversal, and the caption/four-role check's nested-title assertions
# corrected) and Task 2's full contract rewrite of the caption check
# were all done in place — no count change from either).
# 100 + 3 (quick task 260902-l0b Task 2: the multi-day daily-average
# end-to-end check — including the negative half proving no raw reading
# value is a plotted point — the same-day/day-1 fallback regression
# guard, and the mode-honest caption check across empty/multi-day/
# same-day renders). Two gates were retargeted in place, both zero count
# change: _battery_trend_timestamps_show_concise_format()'s exact
# single-argument pin, now the positional-arity property it actually
# meant; and _read_health_inputs_gained_no_new_key(), renamed
# _read_health_inputs_keeps_registry_stats_separate() now that
# daily_rows makes "no new key" untrue, restating D-11's real intent.
# _battery_trend_heading_shows_d10_window_label() was also retargeted in
# place onto the 3-month default caption (an empty render has no chart
# at all now, so the retired "Latest 20 readings" label it pinned no
# longer applies) — zero count change.
# 103 + 3 (quick task 260902-l0b Task 3: the daily-mode date-endpoint-
# label check, the daily point's data-when day/average/reading-count
# check, and the density-rule check — both sides of the derived
# threshold boundary plus the below-threshold non-daily regression guard
# folded into that one check, since all three assert the same threshold-
# gated property from different angles). battery_sparkline_svg()'s
# widened signature (a third, defaulted `daily` parameter) needed no gate
# retarget — no pre-existing check pinned its arity.
# 106 + 4 (quick task 260902-tli Task 1: every card's zoom-button
# source/caption/aria-label attributes check, the once-per-page
# lightbox--wide dialog markup + own-note-text check, the style.css
# comment-stripped .airline-card__zoom-neutralizes-the-base-button-rule
# check (rewritten in place, same live test, once the click-gating media
# block it originally also pinned was found to be a misreading of the
# developer's own request and removed outright), and the
# .lightbox--wide max-width cross-file pin against
# illustration_normalize.ILLUSTRATION_TARGET_WIDTH).
# quick task 260902-v2v (2026-09-02): 1 new — pins the UIR-03/07/12/13 one-line fixes (banner wrap +
# banner__label nowrap + banner__pill min-width, airline-card__image height: auto, data-table--prose
# first-column nowrap placement, battery-trend em dash spacing) together in one check.
# quick task 260903-btu (2026-09-03): 1 new — the six 260902-v26 Task 3
# checks (replace-form membership, method/enctype/present-action, unique
# labelled file-input id, cache-buster absent/present-and-mtime-keyed,
# hostile-name escaping, no-revert-control) were retargeted or extended
# IN PLACE onto the relocated shared-lightbox form, contributing zero to
# the count; the +1 is the single new check pinning that the retired
# per-card control left no dead markup, no dead stylesheet rule and no
# dead module surface behind.
EXPECTED_CHECK_COUNT = 133  # 130 + 3 (quick 260903-peo Task 2: UIR-14's
# pipeline tile second-line checks — the seeded META_LAST_DETECTION render
# and the absent-detection honest-fallback render — plus UIR-18's
# persistent freshness-note structural-contract check; the pre-existing
# _read_health_inputs() six-key guard was retargeted in place to seven
# keys, and the pre-existing .dashboard-grid align-items:stretch guard
# already fully covered UIR-14's "unedited" requirement with no change
# needed — neither counted as new)
# 130 = 47 + 2 (06.6.2-04: Health and Airlines page_header() shared component checks) + 1 (heading-color-consistency: acronym-safe anomaly category joining) + 4 (quick 260902-req-02 Task 1: illustration_normalize.py normalization checks) + 2 (quick 260902-req-02 Task 2: route-wiring + card-markup dimension checks) + 4 (quick 260902-tli Task 1: click-to-enlarge lightbox checks) + 1 (quick 260902-v2v: UIR-03/07/12/13 one-line fixes pinned together) + 6 (quick 260902-v26 Task 3: replace-form membership, method/enctype, unique labelled file-input ids, cache-buster absent/present-and-mtime-keyed, hostile-name escaping, and no-revert-control checks) + 1 (quick 260903-btu Task 3: the retired-per-card-control-gone-from-every-surface check; the six 260902-v26 checks were retargeted/extended in place onto the relocated lightbox form, no count change from any of them) + 2 (quick 260903-df3 Task 2: framed-zone sprite-provenance and markup/styling-contract checks; the four pre-existing replace-form checks were updated in place, no count change from any of them) + 2 (quick 260903-ghy Task 1: the Resolution-statistics table's mobile .data-cards completeness check, and the .data-cards toggle-contract/untouched-rules check; the pre-existing nested-card heading-rhythm check's own allowlist was extended in place for the new `<ul class="data-cards">` element, no count change from it) + 2 (quick 260903-ghy Task 2: the registry's mobile-card/table filter-pairing check, and the no-chrome-with-no-data/no-cross-page-leak check; the pre-existing anomaly-detail-list-markup check was retargeted in place from a page-wide <ul>/<li> ban onto the anomaly banner's own element slice, no count change from it) — re-derived from the real on-disk check() count at merge time, not carried forward from either branch's own arithmetic


# --- fixture helpers ---------------------------------------------------


def _mkstate(prefix):
    return tempfile.mkdtemp(prefix="skypane-status-pages-%s-" % prefix)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


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


def _ctx(state_dir, now=None):
    return {"state_dir": state_dir, "now": now or _iso(_now())}


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

    def _both_freshness_labels_present():
        tmp = _mkstate("h-labels")
        try:
            rendered = health_page.render(_ctx(tmp))
            if health_page.DEVICE_FRESHNESS_LABEL not in rendered:
                return False, "missing the device freshness label"
            if health_page.PIPELINE_FRESHNESS_LABEL not in rendered:
                return False, "missing the pipeline freshness label"
            if health_page.DEVICE_FRESHNESS_LABEL == health_page.PIPELINE_FRESHNESS_LABEL:
                return False, "the two labels must be distinct strings"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "render() shows two distinct, separately-labelled freshness signals",
        _both_freshness_labels_present)

    def _staleness_status_boundaries():
        warn_s, error_s = 100, 200
        if health_page.staleness_status(50, warn_s, error_s) != "ok":
            return False, "expected ok below the warn threshold"
        if health_page.staleness_status(warn_s, warn_s, error_s) != "warn":
            return False, "expected warn exactly at the warn threshold"
        if health_page.staleness_status(error_s, warn_s, error_s) != "error":
            return False, "expected error exactly at the error threshold"
        if health_page.staleness_status(None, warn_s, error_s) != "warn":
            return False, "expected warn (not error/ok) for a never-seen signal"
        return True, ""
    check(
        "staleness_status() returns ok/warn/error at the right boundaries, warn for a never-seen signal",
        _staleness_status_boundaries)

    def _layout_absolute_and_relative_covers_every_documented_case():
        if layout.absolute_and_relative(
                "2026-08-28T13:58:02+00:00", "2026-08-28T14:01:02+00:00") != (
                "2026-08-28T13:58:02+00:00 (3m ago)"):
            return False, "expected the +00:00/+00:00 pair to format as absolute-first with a 3m relative age"
        if not layout.absolute_and_relative(
                "2026-08-28T13:58:02Z", "2026-08-28T13:58:32+00:00").endswith("(30s ago)"):
            return False, "expected the Z/+00:00 pair to parse and subtract cleanly, ending in (30s ago)"
        if layout.absolute_and_relative(None, "2026-08-28T14:01:02+00:00") != "no reading yet":
            return False, "expected the default fallback for a falsy timestamp"
        if layout.absolute_and_relative(
                "", "2026-08-28T14:01:02+00:00", fallback="") != "":
            return False, "expected the explicit empty-string fallback to be honoured"
        if layout.absolute_and_relative(
                "not-a-date", "2026-08-28T14:01:02+00:00") != "not-a-date":
            return False, "expected an unparseable timestamp to degrade to the absolute string, not raise"
        if layout.absolute_and_relative("2026-08-28T13:58:02+00:00", None) != (
                "2026-08-28T13:58:02+00:00"):
            return False, "expected a missing now_ts to still return the absolute value unchanged"
        return True, ""
    check(
        "layout.absolute_and_relative() covers every documented case: ordering, Z-suffix parsing, "
        "default/explicit fallback, unparseable-timestamp degradation, missing now_ts",
        _layout_absolute_and_relative_covers_every_documented_case)

    def _timestamp_helpers_promoted_not_duplicated():
        for name in ("_parse_iso", "_age_seconds", "_relative_age_text"):
            if hasattr(health_page, name):
                return False, "health_page still defines %r — helpers were copied, not promoted" % name
        tmp = _mkstate("h-promotion-regression")
        try:
            now = _now()
            ts = _iso(now - timedelta(minutes=3))
            _seed_device_health(tmp, [(ts, 4200)])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if ts not in rendered:
                return False, "expected the seeded ISO string to appear on the rendered page"
            if " ago)" not in rendered:
                return False, "expected a parenthesised relative age suffix on the rendered page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "health_page's private timestamp helpers are gone (a move, not a copy) and the Device row still "
        "renders the absolute-plus-relative format",
        _timestamp_helpers_promoted_not_duplicated)

    def _independent_thresholds_one_warn_one_ok():
        # quick task 260901-tsa (finding C): the Device/Pipeline tiles no
        # longer carry an in-body status_dot() — since that removal, each
        # tile's own stat-tile--ok/warn/error border modifier is the ONLY
        # carrier of this signal, so this check now locates each tile by
        # its own caption constant (never the wrong tile) and asserts the
        # modifier on its wrapper directly, instead of counting dot
        # classes that no longer exist on these two tiles.
        tmp = _mkstate("h-independent")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            device_at = rendered.index(health_page.DEVICE_FRESHNESS_LABEL)
            device_tile_open = rendered.rindex('<div class="stat-tile ', 0, device_at)
            device_tile_tag = rendered[device_tile_open:rendered.index(">", device_tile_open)]
            if "stat-tile--error" not in device_tile_tag:
                return False, (
                    "expected the Device tile's wrapper to carry the error modifier "
                    "(STALE_DEVICE_ERROR_S + 60 is past the error threshold), got %r" % device_tile_tag)

            pipeline_at = rendered.index(health_page.PIPELINE_FRESHNESS_LABEL)
            pipeline_tile_open = rendered.rindex('<div class="stat-tile ', 0, pipeline_at)
            pipeline_tile_tag = rendered[pipeline_tile_open:rendered.index(">", pipeline_tile_open)]
            if "stat-tile--ok" not in pipeline_tile_tag:
                return False, (
                    "expected the Pipeline tile's wrapper to carry the ok modifier "
                    "(just-seeded META_LAST_PIPELINE_RUN is fresh), got %r" % pipeline_tile_tag)

            # quick task 260902-gjj (ISSUE 2): retargeted — the Battery
            # badge and the registry card's own Coverage dot, the two
            # dots this fixture used to carry, are both retired outright
            # (their state now lives on each card's own top edge
            # instead). This fixture seeds no Corroboration rows either
            # (the only surviving dot consumer), so NO dot classes of any
            # colour should remain anywhere on the page — re-derived from
            # this fixture's own seeded data, not adjusted by a fixed
            # offset.
            if rendered.count("dot--ok") != 0 or "dot--warn" in rendered or "dot--error" in rendered:
                return False, (
                    "expected zero dot classes of any colour in this fixture (no Corroboration "
                    "rows seeded, and both the battery/registry dots are retired), got dot--ok=%d"
                    % rendered.count("dot--ok"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a stale device and a fresh pipeline read as independent per-tile modifiers (error vs ok) on their own "
        "wrappers, not a blended verdict, with only the dots that legitimately remain still healthy",
        _independent_thresholds_one_warn_one_ok)

    def _health_page_device_pipeline_tiles_have_no_duplicated_label():
        # quick task 260901-tsa (finding C): pins the whole fix — the
        # tile caption still carries the freshness label exactly once,
        # and the tile body is now a real stat-tile__value timestamp,
        # not a second copy of the label via status_dot()'s dot-label
        # span.
        tmp = _mkstate("h-no-dup-label")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            for label in (health_page.DEVICE_FRESHNESS_LABEL, health_page.PIPELINE_FRESHNESS_LABEL):
                label_count = rendered.count(label)
                if label_count != 1:
                    return False, (
                        "%r must appear exactly once on the whole rendered page, got %d"
                        % (label, label_count))
                at = rendered.index(label)
                tile_open = rendered.rindex('<div class="stat-tile ', 0, at)
                tile_close = rendered.index("</div>", tile_open) + len("</div>")
                tile_slice = rendered[tile_open:tile_close]
                if tile_slice.count('class="stat-tile__value"') != 1:
                    return False, (
                        "%r's tile must carry exactly one stat-tile__value paragraph, got %d"
                        % (label, tile_slice.count('class="stat-tile__value"')))
                if 'class="mono"' not in tile_slice:
                    return False, "%r's tile must carry a mono timestamp span" % (label,)
                if "dot-label" in tile_slice:
                    return False, (
                        "%r's tile must carry no dot-label — the redundant body dot was removed"
                        % (label,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Device and Pipeline tiles carry their freshness label exactly once (caption only) plus a real "
        "stat-tile__value timestamp, with no leftover dot-label (quick task 260901-tsa, finding C)",
        _health_page_device_pipeline_tiles_have_no_duplicated_label)

    # 06.6.1-04: "no <svg" stopped being a valid proxy for "no sparkline"
    # the moment the page gained four icon instances (D-02) — a plain
    # <svg> count would now always be non-zero. Retargeted to assert on
    # the sparkline specifically (zero trend-line segments, zero
    # SPARKLINE_DOT_CLASS), which is what this check always actually
    # meant. quick task 260902-ep7 (BUG 4): retargeted IN PLACE again,
    # from the retired <polyline marker (a single <polyline> no longer
    # exists in the redesigned chart at all — replaced by n - 1
    # <line class="sparkline-line"> segments) onto SPARKLINE_LINE_CLASS.
    # This is one of the plan's two NEGATIVE assertions on this marker —
    # left pointing at a marker that no longer exists anywhere, it would
    # pass vacuously, silently gutting the check, so retargeting is
    # mandatory here, not cosmetic.
    def _battery_empty_state_no_sparkline():
        tmp = _mkstate("h-battery-empty")
        try:
            rendered = health_page.render(_ctx(tmp))
            if "No battery readings yet." not in rendered:
                return False, "expected the battery good-news empty-state heading"
            if health_page.SPARKLINE_LINE_CLASS in rendered:
                return False, "did not expect a sparkline trend-line segment with zero battery rows"
            if health_page.SPARKLINE_DOT_CLASS in rendered:
                return False, "did not expect a sparkline dot with zero battery rows"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "zero battery rows render the good-news empty state and no sparkline",
        _battery_empty_state_no_sparkline)

    def _battery_trend_shows_all_readings_and_one_sparkline():
        tmp = _mkstate("h-battery-trend")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            for _ts, mv in readings:
                if str(mv) not in rendered:
                    return False, "expected battery_mv=%d to appear (a trend, not just the latest)" % mv
            # 06.6.1-04: the page now also carries four icon <svg>
            # instances (D-02), so a bare "<svg" count of 1 no longer
            # proves "one sparkline" — subtract the icon <use>
            # references (one per icon <svg>) to isolate the sparkline's
            # own non-icon <svg>. quick task 260902-ep7 (BUG 4): the
            # trend-line assertion below is retargeted in place from the
            # retired single-<polyline> marker onto SPARKLINE_LINE_CLASS —
            # a percentage-coordinate <polyline> can't exist (percentages
            # aren't permitted in a `points` list), so the redesigned
            # chart emits n - 1 <line> segments instead of one polyline;
            # for this 3-row fixture that is 2 segments.
            non_icon_svg_count = rendered.count("<svg") - rendered.count("<use")
            if non_icon_svg_count != 1:
                return False, "expected exactly one non-icon <svg, got %d" % non_icon_svg_count
            if rendered.count(health_page.SPARKLINE_LINE_CLASS) != 2:
                return False, (
                    "expected exactly 2 trend-line segments (n - 1 for 3 points), got %d"
                    % rendered.count(health_page.SPARKLINE_LINE_CLASS))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "three battery rows render the full trend (not just the latest value) and exactly one <svg> with "
        "exactly n - 1 trend-line segments (260902-ep7: retargeted from the retired single-<polyline> marker)",
        _battery_trend_shows_all_readings_and_one_sparkline)

    def _battery_trend_timestamps_show_concise_format():
        # 06.6.3-04 (D-09): the Battery Trend table's Timestamp column now
        # renders via layout.concise_timestamp_html() — a <span
        # class="mono" title="<full ISO>"> with the full ISO demoted to
        # the title attribute, not the old bare "ISO (Nm ago)" plain-text
        # shape (which this check pinned before D-09) — and
        # _battery_section() must stay single-argument (06.5-02's own
        # pinned automated gate).
        # 260902-l0b: retargeted in place from 06.5-02's original exact
        # single-argument pin, which stopped holding once daily_rows
        # joined this signature as a second, defaulted keyword parameter.
        # 06.5-02's own concurrent-execution window closed long ago, and a
        # defaulted keyword parameter, unlike a required one, cannot
        # break the pinned call site `battery_html, battery_state =
        # _battery_section(trend_rows)` — the real property this gate
        # protects is positional arity, not parameter count.
        battery_section_params = list(inspect.signature(health_page._battery_section).parameters.values())
        if not battery_section_params:
            return False, "_battery_section must take at least one parameter"
        if any(p.default is inspect.Parameter.empty for p in battery_section_params[1:]):
            return False, (
                "_battery_section must stay callable with exactly one positional argument — "
                "every parameter after the first needs a default")
        tmp = _mkstate("h-battery-trend-timestamps")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            for ts, _mv in readings:
                if ('<span class="mono" title="%s">' % ts) not in rendered:
                    return False, (
                        "expected %r inside a concise_timestamp_html() title attribute "
                        "in the rendered Battery Trend table" % ts)
            if " ago)" not in rendered:
                return False, "expected at least one parenthesised relative age in the Battery Trend table"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Battery Trend's Timestamp column shows the D-09 concise format (full ISO demoted to title), "
        "matching the Device/pipeline rows, and _battery_section() stays single-argument",
        _battery_trend_timestamps_show_concise_format)

    def _battery_readings_collapsed_behind_closed_disclosure_after_chart():
        # D-08: the readings table is collapsed behind a closed-by-default
        # <details> disclosure, and the chart (when present) precedes it
        # in both DOM and visual order.
        tmp = _mkstate("h-readings-disclosure")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if '<details class="readings-disclosure"' not in rendered:
                return False, "expected a readings-disclosure <details> element"
            details_tag = rendered[rendered.index('<details class="readings-disclosure"'):]
            details_open_tag = details_tag[:details_tag.index(">") + 1]
            if " open" in details_open_tag:
                return False, "expected the readings disclosure to be closed by default"
            if "View 3 readings" not in rendered:
                return False, "expected the disclosure summary to name the real plotted-row count"
            svg_index = rendered.index("<svg")
            details_index = rendered.index('<details class="readings-disclosure"')
            if not (svg_index < details_index):
                return False, "expected the chart to precede the collapsed readings table"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the readings table is collapsed behind a closed-by-default disclosure, and the chart precedes it (D-08)",
        _battery_readings_collapsed_behind_closed_disclosure_after_chart)

    def _battery_trend_heading_shows_d10_window_label():
        # 260902-l0b: retargeted in place — an empty state dir renders no
        # chart at all now that the chart's primary mode is the 90-day
        # daily series, so the D-10 window label this check originally
        # pinned ("Latest 20 readings") no longer describes what an empty
        # render shows. The honest default framing on an empty render is
        # the 3-month window instead (see _battery_trend_caption()) — it
        # is what this page WILL show once data exists, and there is no
        # chart of any kind on screen to be honest ABOUT otherwise.
        tmp = _mkstate("h-d10-label")
        try:
            rendered = health_page.render(_ctx(tmp))
            if "Last 3 months" not in rendered:
                return False, "expected the default 3-month window framing in the Battery trend heading on an empty render"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Battery trend heading shows the default 3-month window framing on an empty render (260902-l0b, "
        "retargeted from the retired D-10 'Latest 20 readings' label)",
        _battery_trend_heading_shows_d10_window_label)

    def _battery_chart_plots_daily_averages_not_raw_readings():
        # 260902-l0b: the chart's primary mode plots one point per UTC
        # calendar day, sourced from history_db.daily_battery_averages()
        # via battery_daily_rows() — not the raw per-reading series
        # battery_trend_rows() still feeds to the readout/table/anomaly
        # scan. The negative half below (no raw reading appears as a
        # plotted point) is this check's substance — without it the check
        # would pass on a chart still plotting raw readings.
        tmp = _mkstate("h-daily-series")
        try:
            base = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
            readings = []
            day_values = [[4000, 4100, 4200], [4001, 4101, 4201], [4002, 4102, 4202]]
            for day, values in enumerate(day_values):
                for hour, mv in zip((2, 14, 23), values):
                    ts = _iso((base - timedelta(days=day)).replace(hour=hour))
                    readings.append((ts, mv))
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            for expected_mean in ("4100", "4101", "4102"):
                if ('data-mv="%s"' % expected_mean) not in rendered:
                    return False, "expected the daily average %s to appear as a plotted point's data-mv" % expected_mean
            for raw in (4000, 4001, 4002, 4200, 4201, 4202):
                if ('data-mv="%d"' % raw) in rendered:
                    return False, "raw reading %d must not be a plotted point once the chart is aggregated" % raw
            if rendered.count(health_page.SPARKLINE_LINE_CLASS) != 2:
                return False, (
                    "three daily points means two trend-line segments, got %d"
                    % rendered.count(health_page.SPARKLINE_LINE_CLASS))
            for _ts, mv in readings:
                if str(mv) not in rendered:
                    return False, "raw reading %d missing from the disclosure table" % mv
            if "Last 3 months" not in rendered:
                return False, "expected the 3-month caption when the daily series is on screen"
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "the latest computed reading must still be on the page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a multi-day seeded render plots the three DAILY AVERAGES (never any raw reading value) as points, "
        "keeps every raw reading visible in the disclosure table, and names the 3-month window (260902-l0b)",
        _battery_chart_plots_daily_averages_not_raw_readings)

    def _battery_chart_falls_back_to_raw_series_on_day_one():
        # 260902-l0b: a device with fewer than two UTC calendar days of
        # history must keep exactly the chart and readout it had before
        # this task — the day-1 regression guard for the fallback this
        # plan's own must-haves call "not a reduced first version of the
        # feature", named against the `if sparkline_html:` guard that
        # gates the readout and script tag together.
        tmp = _mkstate("h-day-one-fallback")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=2)), 4200),
                (_iso(base - timedelta(minutes=1)), 4190),
                (_iso(base), 4180),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if rendered.count(health_page.SPARKLINE_LINE_CLASS) != 2:
                return False, (
                    "a same-day device must still get its raw-readings chart, got %d segments"
                    % rendered.count(health_page.SPARKLINE_LINE_CLASS))
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "the readout must not disappear on a device younger than two calendar days"
            if ("Latest %d readings" % health_page.BATTERY_TREND_LIMIT) not in rendered:
                return False, "the fallback chart must be captioned as readings, not as the 3-month window"
            if "Last 3 months" in rendered:
                return False, "the caption must never describe a window the chart is not actually showing"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a same-day (fewer than two calendar days) seeded render still produces a chart and a readout, "
        "captioned honestly as readings rather than the 3-month window — the day-1 regression guard (260902-l0b)",
        _battery_chart_falls_back_to_raw_series_on_day_one)

    def _battery_caption_is_mode_honest_across_renders():
        # 260902-l0b: one check, three renders — the caption must never
        # describe a window the chart is not actually showing.
        tmp_empty = _mkstate("h-caption-empty")
        tmp_multiday = _mkstate("h-caption-multiday")
        tmp_sameday = _mkstate("h-caption-sameday")
        try:
            base = _now()
            empty_rendered = health_page.render(_ctx(tmp_empty, now=_iso(base)))
            if "Last 3 months" not in empty_rendered:
                return False, "expected the default 3-month framing on an empty render"

            multiday_readings = [
                (_iso(base - timedelta(days=1)), 4100),
                (_iso(base - timedelta(days=2)), 4200),
            ]
            _seed_device_health(tmp_multiday, multiday_readings)
            multiday_rendered = health_page.render(_ctx(tmp_multiday, now=_iso(base)))
            if "Last 3 months" not in multiday_rendered:
                return False, "expected the 3-month framing when the daily series is on screen"

            sameday_readings = [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ]
            _seed_device_health(tmp_sameday, sameday_readings)
            sameday_rendered = health_page.render(_ctx(tmp_sameday, now=_iso(base)))
            if ("Latest %d readings" % health_page.BATTERY_TREND_LIMIT) not in sameday_rendered:
                return False, "expected the readings-count framing on the same-day fallback"
            if "Last 3 months" in sameday_rendered:
                return False, "the same-day fallback must not claim the 3-month framing"
            return True, ""
        finally:
            shutil.rmtree(tmp_empty, ignore_errors=True)
            shutil.rmtree(tmp_multiday, ignore_errors=True)
            shutil.rmtree(tmp_sameday, ignore_errors=True)
    check(
        "the Battery trend caption is mode-honest across three renders — empty (3-month default), multi-day "
        "(3-month, daily average), and same-day (readings count) (260902-l0b)",
        _battery_caption_is_mode_honest_across_renders)

    def _anomaly_banner_names_real_categories_not_generic_only():
        tmp = _mkstate("h-anomaly-specific")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": False}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "ADS-B sources disagreed" not in rendered:
                return False, "expected the anomaly banner to name the real failing category"
            if health_page.ANOMALY_BANNER_TEXT not in rendered:
                return False, "expected ANOMALY_BANNER_TEXT to remain present as the banner's fallback tail"
            # 06.6.4.1-04 (D-07): the real failing category now also
            # renders as a pill, not only inside the accessible tail.
            if 'class="banner__pill"' not in rendered:
                return False, "expected the anomaly banner to render banner__pill markup for the new pill-based category naming"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the anomaly banner names the real failing category (a disagreement), not only the generic "
        "fallback text (UXA-06)",
        _anomaly_banner_names_real_categories_not_generic_only)

    def _anomaly_categories_never_lowercase_a_leading_acronym():
        # heading-color-consistency debug session.
        # _anomaly_category_text() lower-cases each phrase after the
        # first so they read mid-sentence. Two of collect_anomalies()'s
        # four literals begin with "ADS-B", and the transformation had no
        # acronym guard, so any banner listing one of them in a
        # non-first position rendered the visible nonsense "aDS-B ...".
        # Driven through the real collect_anomalies() strings, in the
        # real order, rather than hand-written fixtures — so the check
        # cannot drift away from the copy it is protecting.
        anomalies = health_page.collect_anomalies(
            device_state="warn", pipeline_state="warn",
            battery_state="ok", disagreement_warn=True)
        text = health_page._anomaly_category_text(anomalies)
        if "aDS-B" in text:
            return False, (
                "a leading acronym was lower-cased for mid-sentence "
                "joining, producing %r" % (text,))
        if text.count("ADS-B") != 2:
            return False, (
                "expected both ADS-B categories to survive intact, got %r"
                % (text,))
        # The guard must be narrow: an ordinary sentence-initial word in
        # a non-first position still lower-cases, or the joined clause
        # reads as a run of sentences again.
        ordinary = health_page._anomaly_category_text(
            ["Device check-in is stale.",
             "A battery reading shows an abnormal drop."])
        if "a battery reading" not in ordinary:
            return False, (
                "expected an ordinary non-acronym phrase to still be "
                "lower-cased mid-sentence, got %r" % (ordinary,))
        return True, ""
    check(
        "_anomaly_category_text() lower-cases ordinary mid-sentence phrases "
        "but never a leading acronym (no 'aDS-B')",
        _anomaly_categories_never_lowercase_a_leading_acronym)

    def _anomaly_category_labels_are_pill_text_not_full_sentences():
        # 06.6.4.1-04 (D-07): _anomaly_category_labels() is the pill-
        # shaped counterpart to _anomaly_category_text()'s joined
        # clause — one label per anomaly, period-stripped, never the
        # full literal sentence collect_anomalies() returns.
        anomalies = health_page.collect_anomalies(
            device_state="error", pipeline_state="error",
            battery_state="ok", disagreement_warn=False)
        labels = health_page._anomaly_category_labels(anomalies)
        if len(labels) != len(anomalies):
            return False, "expected one label per anomaly, got %d labels for %d anomalies" % (len(labels), len(anomalies))
        for label, anomaly in zip(labels, anomalies):
            if label == anomaly:
                return False, "expected a pill label to differ from collect_anomalies()'s full literal sentence, got %r" % (label,)
            if label.endswith("."):
                return False, "expected a pill label's trailing period to be stripped, got %r" % (label,)
        return True, ""
    check(
        "_anomaly_category_labels() returns one period-stripped label per anomaly, distinct from "
        "collect_anomalies()'s own full literal sentences (D-07)",
        _anomaly_category_labels_are_pill_text_not_full_sentences)

    def _anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping():
        # 06.6.4.1-04 (D-07): _anomaly_banner_html() must reproduce
        # layout.anomaly_banner()'s exact severity-to-class/role mapping.
        anomalies = ["Device check-in is stale."]
        error_banner = health_page._anomaly_banner_html("error", anomalies)
        if 'class="banner banner--anomaly"' not in error_banner or 'role="alert"' not in error_banner:
            return False, "expected error severity to render banner--anomaly + role=\"alert\""
        warn_banner = health_page._anomaly_banner_html("warn", anomalies)
        if 'class="banner banner--warn"' not in warn_banner or 'role="status"' not in warn_banner:
            return False, "expected warn severity to render banner--warn + role=\"status\""
        if warn_banner.count('class="banner__pill"') != 1:
            return False, "expected exactly one banner__pill for a single-anomaly fixture"
        if health_page.ANOMALY_BANNER_TEXT not in warn_banner:
            return False, "expected ANOMALY_BANNER_TEXT to remain present as the banner's accessible tail"
        return True, ""
    check(
        "_anomaly_banner_html() reproduces layout.anomaly_banner()'s exact severity-to-class/role mapping, and "
        "carries one banner__pill per anomaly plus the accessible ANOMALY_BANNER_TEXT tail (D-07)",
        _anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping)

    def _anomaly_banner_renders_one_pill_per_anomaly_on_the_page():
        tmp = _mkstate("h-banner-pills-page")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN: _ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if rendered.count('<div class="banner ') != 1:
                return False, "expected exactly one banner element"
            if rendered.count('class="banner__pill"') != 2:
                return False, (
                    "expected exactly two banner__pill elements for this two-anomaly "
                    "fixture (stale device + stale pipeline), got %d"
                    % rendered.count('class="banner__pill"'))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a two-anomaly fixture renders exactly two banner__pill elements inside one banner element on the real "
        "page (D-07)",
        _anomaly_banner_renders_one_pill_per_anomaly_on_the_page)

    def _corroboration_rows_compact_explanations_in_closed_disclosure():
        tmp = _mkstate("h-corrob-disclosure")
        try:
            now = _now()
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": True},
                {"ts": _iso(now), "hex": "def456", "corroborated": None},
                {"ts": _iso(now), "hex": "ghi789", "corroborated": False},
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
                if explanation not in rendered:
                    return False, "expected explanation %r to survive somewhere in the rendered page" % explanation
            details_start = rendered.index('<details class="readings-disclosure"')
            compact_rows_html = rendered[:details_start]
            for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
                if explanation in compact_rows_html:
                    return False, "expected the compact corroboration rows to no longer carry the explanation clause inline: %r" % explanation
            details_tag = rendered[details_start:]
            details_open_tag = details_tag[:details_tag.index(">") + 1]
            if " open" in details_open_tag:
                return False, "expected the corroboration disclosure to be closed by default"
            if "<dl>" not in rendered or "<dt>" not in rendered or "<dd>" not in rendered:
                return False, "expected the disclosure's explanations to render as a <dl> of <dt>/<dd> pairs"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Corroboration's three rows stay compact (dot/label/count only) and their explanations move into a "
        "closed-by-default disclosure (D-08)",
        _corroboration_rows_compact_explanations_in_closed_disclosure)

    def _corroboration_section_disagreement_flag_unchanged():
        _, has_disagreement = health_page._corroboration_section(
            {"True": 1, "None": 0, "False": 2})
        if has_disagreement is not True:
            return False, "expected the disagreement flag to be True when the False bucket is non-zero"
        _, no_disagreement = health_page._corroboration_section(
            {"True": 1, "None": 2, "False": 0})
        if no_disagreement is not False:
            return False, "expected the disagreement flag to be False when the False bucket is zero"
        return True, ""
    check(
        "_corroboration_section()'s second return value (the disagreement flag) is unchanged by the D-08 "
        "disclosure rewrite",
        _corroboration_section_disagreement_flag_unchanged)

    def _corroboration_copy_has_no_decision_id_leak():
        for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
            if "(D-" in explanation:
                return False, "found a decision-ID leak in a corroboration row's explanation: %r" % explanation
        return True, ""
    check(
        "no corroboration row's explanation leaks a bare decision-ID parenthetical (UXA-05)",
        _corroboration_copy_has_no_decision_id_leak)

    def _device_and_pipeline_rows_use_concise_timestamp_format():
        tmp = _mkstate("h-concise-device-pipeline")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if rendered.count('<span class="mono" title=') < 2:
                return False, "expected at least two concise_timestamp_html() spans (Device + Pipeline rows)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Device check-in and ADS-B pipeline rows render via the D-09 concise timestamp format",
        _device_and_pipeline_rows_use_concise_timestamp_format)

    def _health_pill_reversal_guard():
        # 260902-chc: D-12's manual Refresh link + stale-view banner
        # pattern is reversed for Health (see health_page.py's own
        # reversal record above _read_health_inputs()). This check pins
        # the reversal's own rendered result — not the module source —
        # and positively asserts both retired literals (derived from the
        # pre-260902-chc file, not re-typed from a plan) are truly gone.
        # An unrecorded reversal reads to the next reader as a violation
        # of a rule still presented as current; this check exists so a
        # later refactor cannot silently un-reverse it either.
        tmp = _mkstate("h-refresh-pill")
        try:
            now_iso = _iso(_now())
            rendered = health_page.render(_ctx(tmp, now=now_iso))
            if rendered.count("data-loaded-at") != 1:
                return False, "expected exactly one data-loaded-at attribute"
            if ('data-loaded-at="%s"' % now_iso) not in rendered:
                return False, "expected data-loaded-at to carry the real, request-scoped now ISO value"
            if rendered.count('<h1 class="page-title"') != 1:
                return False, "expected page_header() to be called exactly once"
            if "data-stale-banner" in rendered:
                return False, "expected the retired stale-view banner marker to be gone from the rendered page"
            if "may be out of date" in rendered:
                return False, "expected the retired stale-view banner's copy to be gone from the rendered page"
            if "freshness-refresh" in rendered:
                return False, "expected the retired manual Refresh link's class to be gone from the rendered page"
            if hasattr(health_page, "_STALE_VIEW_BANNER_HTML"):
                return False, "expected health_page to no longer define the retired _STALE_VIEW_BANNER_HTML constant"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's D-12 reversal: a live data-loaded-at timestamp survives, page_header() is called exactly "
        "once, and the retired stale-view banner marker/copy and manual Refresh-link class are gone from "
        "both the rendered page and the module itself (260902-chc)",
        _health_pill_reversal_guard)

    def _battery_section_healthy_card_border_on_normal_trend():
        tmp = _mkstate("h-battery-badge-ok")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4190),
            ]
            _seed_device_health(tmp, readings)
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            # quick task 260902-gjj (ISSUE 2): retargeted — the badge
            # this check used to look for is retired. The card's own top
            # edge now carries the healthy verdict instead.
            battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
            if "battery-trend-section--ok" not in battery_tag:
                return False, (
                    "expected the battery-trend section's own tag to carry the ok status "
                    "modifier, got %r" % battery_tag)
            # quick task 260901-tsa (finding C) / 260902-gjj: no dot of any
            # colour should remain in this fixture — Device/Pipeline lost
            # theirs under finding C, and the battery/registry badges are
            # now retired outright (260902-gjj); no Corroboration rows are
            # seeded either.
            if rendered.count("dot--ok") != 0 or "dot--warn" in rendered or "dot--error" in rendered:
                return False, (
                    "expected zero dot classes of any colour in this fixture, got dot--ok=%d"
                    % rendered.count("dot--ok"))
            for label, expect_class in (
                    (health_page.DEVICE_FRESHNESS_LABEL, "stat-tile--ok"),
                    (health_page.PIPELINE_FRESHNESS_LABEL, "stat-tile--ok")):
                at = rendered.index(label)
                tile_open = rendered.rindex('<div class="stat-tile ', 0, at)
                tile_tag = rendered[tile_open:rendered.index(">", tile_open)]
                if expect_class not in tile_tag:
                    return False, (
                        "expected the %r tile's wrapper to carry %r, got %r"
                        % (label, expect_class, tile_tag))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Battery trend renders a healthy status-coloured card border on a normal trend, in place of the "
        "retired status_dot() badge (D-01 reversal, quick task 260902-gjj)",
        _battery_section_healthy_card_border_on_normal_trend)

    def _battery_empty_history_ok_badge_no_anomaly_banner():
        # 06.5-RESEARCH.md Pitfall 2: the empty-history branch must stay
        # "ok" (Assumption A1), or a freshly-provisioned device with zero
        # readings would display "A battery reading shows an abnormal
        # drop." — factually wrong copy. This check is a permanent
        # regression guard against that switch.
        #
        # Direct unit-level proof that _battery_section([]) itself never
        # produces an error badge or the abnormal-drop copy:
        markup, state = health_page._battery_section([])
        if state != "ok":
            return False, "expected _battery_section([]) to return state 'ok', got %r" % (state,)
        # quick task 260902-gjj (ISSUE 2): retargeted — the badge label
        # this check used to require is retired outright (hasattr, not a
        # source grep, per this file's own precedent — see the dedicated
        # retirement check below); a real positive replaces it: the
        # empty-state heading this branch renders instead.
        if "No battery readings yet." not in markup:
            return False, "expected the empty-history empty-state heading in the markup"
        if "dot--error" in markup or "dot--warn" in markup or "dot--ok" in markup:
            return False, (
                "did not expect any status-dot class in the empty-history markup — the badge "
                "is retired; this card's status now lives on its wrapping section's own edge")
        # Page-level proof that a fresh device with no meaningful battery
        # readings (device/pipeline both healthy, no drop possible) never
        # surfaces the abnormal-drop anomaly or the banner it drives —
        # device_health and battery trend share one table, so a page-level
        # "zero device_health rows at all" fixture would also make Device
        # check-in read as stale for an unrelated reason; this fixture
        # isolates the battery-specific guarantee instead.
        tmp = _mkstate("h-battery-empty-badge")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "dot--error" in rendered:
                return False, "did not expect an error status class with a single battery reading"
            battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
            if "battery-trend-section--ok" not in battery_tag:
                return False, (
                    "expected the battery-trend section's own tag to carry the ok status "
                    "modifier with a single, healthy battery reading, got %r" % battery_tag)
            if health_page.ANOMALY_BANNER_TEXT in rendered:
                return False, "did not expect the anomaly banner with a single, healthy battery reading"
            if "A battery reading shows an abnormal drop." in rendered:
                return False, "did not expect the abnormal-drop copy with a single battery reading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an empty/single-reading battery trend renders an ok badge and no anomaly banner (Assumption A1 regression guard)",
        _battery_empty_history_ok_badge_no_anomaly_banner)

    # 06.6.1-UI-SPEC.md's "Anomaly detail list (removed)" row: the <ul>
    # detail list this check used to assert on is gone this plan, so the
    # abnormal-drop copy must now be ABSENT from the rendered page while
    # collect_anomalies() called directly still returns it — the badge
    # and banner assertions (the check's real meaning: one signal drives
    # both) are kept exactly as they were.
    def _battery_drop_drives_badge_and_banner_detail_copy_not_rendered():
        tmp = _mkstate("h-battery-drop-badge")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
            ]
            _seed_device_health(tmp, readings)
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            # quick task 260902-gjj (ISSUE 2): retargeted onto the battery
            # card's own error modifier — the "dot--error" badge this
            # check used to look for is retired outright; this is the
            # BREAKS-LOUDLY retarget the plan calls for, not a silent
            # pass-through.
            battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
            if "battery-trend-section--error" not in battery_tag:
                return False, (
                    "expected the battery-trend section's own tag to carry the error status "
                    "modifier for a drop >= BATTERY_DROP_WARN_MV, got %r" % battery_tag)
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            if "A battery reading shows an abnormal drop." in rendered:
                return False, "the abnormal-drop detail copy must no longer be rendered on the page"
            if health_page.collect_anomalies("ok", "ok", "error", False) != [
                    "A battery reading shows an abnormal drop."]:
                return False, "collect_anomalies() must still compute the abnormal-drop item directly"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real battery drop drives both the card's own error border (retargeted from the retired badge, "
        "quick task 260902-gjj) and the banner; the detail copy is no longer rendered",
        _battery_drop_drives_badge_and_banner_detail_copy_not_rendered)

    def _anomaly_detail_list_markup_is_gone():
        # Retargeted in place by quick task 260903-ghy: this check used to
        # assert zero <ul>/<li> occurrences across the WHOLE rendered page.
        # That happened to still pass after this task's own .data-cards
        # mechanism landed only because this fixture seeds neither runway
        # events nor unresolved prefixes (so neither new card list ever
        # renders) — a page-wide list ban was always a fragile proxy for
        # this check's real subject (the retired anomaly detail list), and
        # would have wrongly failed the moment a legitimate card list
        # coexisted with an anomaly banner on the same fixture. Scoped now
        # to the anomaly banner element's own slice — the one element this
        # check actually cares about — rather than the whole page.
        tmp = _mkstate("h-no-list-markup")
        try:
            now = _now()
            _seed_device_health(tmp, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            banner_at = rendered.index('<div class="banner ')
            banner_end = rendered.index("</div>", banner_at) + len("</div>")
            banner_slice = rendered[banner_at:banner_end]
            if banner_slice.count("<ul") != 0:
                return False, "expected zero <ul occurrences inside the anomaly banner — the detail list must be gone"
            if banner_slice.count("<li") != 0:
                return False, "expected zero <li occurrences inside the anomaly banner — the detail list must be gone"
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an unhealthy fixture renders the anomaly banner with zero <ul/<li list markup inside its own "
        "element slice (retargeted from a page-wide ban by quick task 260903-ghy, to stop it colliding "
        "with a legitimate .data-cards list elsewhere on the page)",
        _anomaly_detail_list_markup_is_gone)

    def _none_of_the_four_anomaly_item_strings_render():
        tmp = _mkstate("h-all-four-anomalies")
        try:
            now = _now()
            # Trip all four D-14 signals at once: stale device, stale
            # pipeline, an abnormal battery drop, and a disagreement
            # recorded within the corroboration window.
            _seed_device_health(tmp, [
                (_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4200),
                (_ago(health_page.STALE_DEVICE_ERROR_S + 30),
                 4200 - health_page.BATTERY_DROP_WARN_MV),
            ])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN:
                    _ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": False}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            expected_items = health_page.collect_anomalies("error", "error", "error", True)
            if len(expected_items) != 4:
                return False, "expected collect_anomalies() to return all four items, got %r" % (expected_items,)
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            for item in expected_items:
                if item in rendered:
                    return False, "anomaly item copy leaked into the rendered page: %r" % item
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with all four D-14 signals unhealthy, none of collect_anomalies()'s four item strings is rendered",
        _none_of_the_four_anomaly_item_strings_render)

    # This check's scope is narrower than it first appears — it exercises
    # only battery_sparkline_svg()'s own return value, which still never
    # gains a script/url/image reference after Task 2's D-02 markup was
    # added. The page-level "exactly one scoped script" guarantee is
    # carried by _page_allows_exactly_one_scoped_script_no_inline_handlers()
    # below, added additively rather than by relaxing this one.
    def _sparkline_has_no_external_reference():
        rows = [
            {"ts": "t1", "battery_mv": 4200},
            {"ts": "t2", "battery_mv": 4100},
            {"ts": "t3", "battery_mv": 4050},
        ]
        svg = health_page.battery_sparkline_svg(rows)
        for forbidden in ("url(", "<image", "<script"):
            if forbidden in svg:
                return False, "found forbidden %r in the sparkline SVG" % forbidden
        return True, ""
    check(
        "battery_sparkline_svg() emits no url(, <image, or <script — no external reference at all",
        _sparkline_has_no_external_reference)

    def _sparkline_svg_has_per_point_interactive_markup():
        rows = [
            {"ts": "2024-01-03T00:00:00", "battery_mv": 4050},
            {"ts": "2024-01-02T00:00:00", "battery_mv": 4100},
            {"ts": "2024-01-01T00:00:00", "battery_mv": 4200},
        ]
        svg = health_page.battery_sparkline_svg(rows)
        if svg.count(health_page.SPARKLINE_HIT_CLASS) != 3:
            return False, "expected exactly 3 hit-target circles, got %d" % svg.count(health_page.SPARKLINE_HIT_CLASS)
        if svg.count(health_page.SPARKLINE_DOT_CLASS) != 3:
            return False, "expected exactly 3 cosmetic dot circles, got %d" % svg.count(health_page.SPARKLINE_DOT_CLASS)
        if svg.count("data-mv=") != 3:
            return False, "expected exactly 3 data-mv attributes, got %d" % svg.count("data-mv=")
        if svg.count("data-ts=") != 3:
            return False, "expected exactly 3 data-ts attributes, got %d" % svg.count("data-ts=")
        if svg.count("<title") != 3:
            return False, "expected exactly 3 <title elements, got %d" % svg.count("<title")
        # 06.6.3-04 (D-13/UXA-11): roving tabindex — exactly one hit
        # target is a normal Tab stop (the chronologically-latest point),
        # the rest are removed from the natural Tab order.
        if svg.count('tabindex="0"') != 1:
            return False, "expected exactly 1 tabindex=\"0\" hit target (roving tabindex), got %d" % svg.count('tabindex="0"')
        if svg.count('tabindex="-1"') != 2:
            return False, "expected exactly 2 tabindex=\"-1\" hit targets, got %d" % svg.count('tabindex="-1"')
        # quick task 260902-ep7 (BUG 4): retargeted in place from the
        # retired single-<polyline> marker onto SPARKLINE_LINE_CLASS — a
        # percentage-coordinate <polyline> can't exist (percentages
        # aren't permitted in a `points` list), so this 3-row fixture now
        # emits n - 1 = 2 <line> segments instead of one polyline.
        if svg.count(health_page.SPARKLINE_LINE_CLASS) != 2:
            return False, (
                "expected exactly 2 trend-line segments (n - 1 for 3 points), got %d"
                % svg.count(health_page.SPARKLINE_LINE_CLASS))
        for _ts, mv in [(r["ts"], r["battery_mv"]) for r in rows]:
            if ('data-mv="%d"' % mv) not in svg:
                return False, "expected battery_mv=%d to appear inside a data-mv attribute" % mv
        oldest_index = svg.find("2024-01-01T00:00:00")
        middle_index = svg.find("2024-01-02T00:00:00")
        newest_index = svg.find("2024-01-03T00:00:00")
        if not (oldest_index < middle_index < newest_index):
            return False, "expected timestamps in chronological (oldest-first) order, matching the trend line's own left-to-right ordering"
        # The tabindex="0" hit target must belong to the newest point
        # (data-ts="2024-01-03..."), not merely appear somewhere.
        newest_circle_start = svg.rfind("<circle", 0, newest_index)
        newest_circle_end = svg.index(">", newest_index)
        newest_circle = svg[newest_circle_start:newest_circle_end]
        if 'tabindex="0"' not in newest_circle:
            return False, "expected the chronologically-latest point's hit target to carry tabindex=\"0\""
        return True, ""
    check(
        "battery_sparkline_svg() emits per-point interactive hit targets with data-mv/data-ts/<title>, in "
        "chronological order, with roving tabindex on the latest point only",
        _sparkline_svg_has_per_point_interactive_markup)

    def _sparkline_axis_labels_present_with_real_min_max():
        # 06.6.4.1-04 (D-09/§5.3): four aria-hidden axis-label elements,
        # two carrying the fixture's real min/max mV values. quick task
        # 260902-ep7 (BUG 4): retargeted in place from SVG `<text
        # class="sparkline-axis-label"` onto HTML `<span
        # class="sparkline-axis-label"` — the labels moved out of the
        # SVG's scaled coordinate space entirely, into an HTML grid
        # column/row sized by the browser's own real text measurement.
        # The per-tag aria-hidden assertion, the four-label count and the
        # real-min/max-value assertions are otherwise unchanged.
        rows = [
            {"ts": "2024-01-01T08:00:00", "battery_mv": 4200},
            {"ts": "2024-01-01T09:00:00", "battery_mv": 3850},
            {"ts": "2024-01-01T10:00:00", "battery_mv": 4000},
        ]
        svg = health_page.battery_sparkline_svg(rows)
        tag_start = 0
        label_count = 0
        while True:
            idx = svg.find('<span class="sparkline-axis-label"', tag_start)
            if idx == -1:
                break
            tag_end = svg.index(">", idx)
            tag = svg[idx:tag_end + 1]
            if 'aria-hidden="true"' not in tag:
                return False, "expected every sparkline-axis-label <span> to carry aria-hidden=\"true\" on its own tag"
            label_count += 1
            tag_start = tag_end
        if label_count != 4:
            return False, "expected exactly four sparkline-axis-label elements, got %d" % label_count
        if "4200 mV" not in svg:
            return False, "expected the real maximum mV value in an axis label"
        if "3850 mV" not in svg:
            return False, "expected the real minimum mV value in an axis label"
        # quick task 260902-ep7 (BUG 4): retargeted in place from the
        # retired single-<polyline> marker onto SPARKLINE_LINE_CLASS — 2
        # trend-line segments (n - 1) for this 3-row fixture.
        if svg.count(health_page.SPARKLINE_LINE_CLASS) != 2:
            return False, (
                "expected exactly 2 trend-line segments (n - 1 for 3 points) after adding axis labels, got %d"
                % svg.count(health_page.SPARKLINE_LINE_CLASS))
        for forbidden in ("url(", "<image", "<script"):
            if forbidden in svg:
                return False, "found forbidden %r in the axis-labeled sparkline SVG" % forbidden
        return True, ""
    check(
        "battery_sparkline_svg() emits exactly four aria-hidden axis-label text nodes carrying the fixture's real "
        "min/max mV values, with every prior no-external-reference guarantee intact (D-09)",
        _sparkline_axis_labels_present_with_real_min_max)

    def _sparkline_scale_bounded_at_one_across_real_container_widths():
        # quick task 260902-dng (bug 1) wrote this check to prove a
        # min(containerWidth/viewBoxWidth, 1) scale-bound mechanism from
        # source, across the real container-width range derived below
        # (kept here as HISTORY — the reason that mechanism existed and
        # what it was verified against — not because anything below still
        # depends on it). That derivation, reproduced for the record:
        # >= 960px, .dashboard-shell's 240px + --space-xl (32px)
        # column-gap leaves `viewport - 272` for the main column;
        # .dashboard-main caps at min(1440px, 100%) and adds
        # --space-2xl/--space-3xl (48/64px) padding, giving content width
        # `min(1440, column) - 128`; .battery-trend-section's own
        # --space-md (16px) padding plus its 1px border on each side
        # subtracts 34 more. Below 960px, .page-content's --space-xl/
        # --space-lg (32/24px) padding leaves `viewport - 48` for
        # content, then another 34 for the section's own padding+border.
        # Evaluated: 375px viewport -> 293px; 959px -> 877px; **960px ->
        # 526px** (a real discontinuity — the container drops as the
        # sidebar appears); 1280px -> 846px; >= 1568px -> 1278px (the
        # 1440px max-width caps it).
        #
        # quick task 260902-ep7 (BUG 4) rewrites this check IN PLACE (no
        # count change) as the NO-SCALE-FACTOR check it becomes once the
        # viewBox is deleted outright: there is no longer a scale factor
        # to bound, so the check now proves there is no scale factor
        # anywhere in the pipeline, and pins the one new hazard this
        # design introduces in its place (the canvas height must be
        # declared exactly once, never inside a media query).
        rows = [
            {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
            for i in range(5)]
        svg = health_page.battery_sparkline_svg(rows)

        svg_tag = svg[svg.index("<svg"):svg.index(">", svg.index("<svg"))]
        if "viewBox" in svg_tag:
            return False, "expected no viewBox attribute on the sparkline <svg> — a scaling transform must not exist"
        if "preserveAspectRatio" in svg_tag:
            return False, "expected no preserveAspectRatio attribute on the sparkline <svg> — there is no scaled canvas to apply it to"

        cx_values = re.findall(r'cx="([\d.]+)%"', svg)
        cy_values = re.findall(r'cy="([\d.]+)%"', svg)
        if len(cx_values) != 10 or len(cy_values) != 10:
            return False, (
                "expected 10 percentage cx and 10 percentage cy values (5 markers + 5 hit "
                "targets for a 5-row fixture), got %d/%d" % (len(cx_values), len(cy_values)))
        for value in cx_values + cy_values:
            if not (0.0 <= float(value) <= 100.0):
                return False, "expected every cx/cy percentage inside [0, 100], got %r" % value

        # Document order interleaves each point's marker then its own hit
        # target (both at the same x), so every other cx value (starting
        # at index 0) is the chronological run of marker x-positions —
        # this replaces the old "every emitted coordinate inside the
        # viewBox" sweep with the equivalent left-to-right ordering proof
        # that mattered from it.
        marker_xs = [float(v) for v in cx_values[::2]]
        if marker_xs != sorted(marker_xs) or len(set(marker_xs)) != len(marker_xs):
            return False, "expected strictly increasing, distinct marker x-positions (chronological order), got %r" % marker_xs

        if svg.count('r="3"') != 5 or svg.count('r="8"') != 5:
            return False, (
                "expected the unchanged absolute marker radius (r=\"3\", x5) and hit-target "
                "radius (r=\"8\", x5) — got r=\"3\" x%d, r=\"8\" x%d"
                % (svg.count('r="3"'), svg.count('r="8"')))

        css = open(os.path.join(HERE, "static", "style.css")).read()
        rule_match = re.search(
            r'\.battery-trend-section svg:not\(\.icon\)\s*\{([^}]*)\}', css)
        if rule_match is None:
            return False, "expected a `.battery-trend-section svg:not(.icon)` rule in style.css"
        if re.search(r'height:\s*\d', rule_match.group(1)) is None:
            return False, "expected a fixed px height declaration on `.battery-trend-section svg:not(.icon)`"

        # The new hazard this design introduces: every point coordinate
        # is a percentage of this declared height, so a responsive height
        # inside a media query would silently move every point with no
        # other visual signal. Scan every @media block in the file (a
        # nested-brace-aware walk, since a naive `[^}]*` regex would stop
        # at the FIRST inner rule's own closing brace) and confirm none
        # of them re-declares a height for this selector.
        media_start = 0
        while True:
            at_media = css.find("@media", media_start)
            if at_media == -1:
                break
            block_open = css.index("{", at_media)
            depth = 1
            cursor = block_open + 1
            while depth > 0:
                nxt_open = css.find("{", cursor)
                nxt_close = css.find("}", cursor)
                if nxt_close == -1:
                    return False, "unterminated @media block while scanning style.css"
                if nxt_open != -1 and nxt_open < nxt_close:
                    depth += 1
                    cursor = nxt_open + 1
                else:
                    depth -= 1
                    cursor = nxt_close + 1
            media_block = css[block_open:cursor]
            if ".battery-trend-section svg:not(.icon)" in media_block and re.search(r'height:\s*\d', media_block):
                return False, (
                    "expected .battery-trend-section svg:not(.icon) to declare no height inside any "
                    "@media block — every point coordinate is a percentage of the single declared "
                    "height, so a responsive height would silently move every point")
            media_start = cursor

        return True, ""
    check(
        "battery_sparkline_svg()'s <svg> carries no viewBox/preserveAspectRatio (no scale factor exists), "
        "every cx/cy is a percentage inside [0, 100] with strictly increasing chronological marker "
        "x-positions, marker/hit-target radii stay the unchanged absolute 3/8, and style.css declares the "
        "canvas height exactly once for this selector and never inside a @media block (quick task 260902-ep7 "
        "BUG 4, rewritten in place from 260902-dng's retired scale-bound mechanism)",
        _sparkline_scale_bounded_at_one_across_real_container_widths)

    def _sparkline_axis_chrome_present():
        # quick task 260902-ep7 (BUG 4): the new check for the drawn axis
        # lines and ticks — real <rect class="sparkline-axis"> elements,
        # not just the four floating text labels 06.6.4.1-UI-SPEC.md
        # §5.3 previously called sufficient. Same per-tag aria-hidden
        # discipline _sparkline_axis_labels_present_with_real_min_max()
        # above already uses, not a document-wide substring search.
        rows = [
            {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
            for i in range(5)]
        svg = health_page.battery_sparkline_svg(rows)

        axis_rects = []
        tag_start = 0
        while True:
            idx = svg.find('<rect class="%s"' % health_page.SPARKLINE_AXIS_CLASS, tag_start)
            if idx == -1:
                break
            tag_end = svg.index(">", idx)
            tag = svg[idx:tag_end + 1]
            if 'aria-hidden="true"' not in tag:
                return False, "expected every sparkline-axis <rect> to carry aria-hidden=\"true\" on its own tag"
            axis_rects.append(tag)
            tag_start = tag_end

        vertical = [t for t in axis_rects if 'height="100%"' in t]
        horizontal = [t for t in axis_rects if 'width="100%"' in t]
        if not vertical:
            return False, "expected at least one full-height vertical axis <rect> (height=\"100%\")"
        if not horizontal:
            return False, "expected at least one full-width horizontal axis <rect> (width=\"100%\")"

        ticks = [t for t in axis_rects if t not in vertical and t not in horizontal]
        if len(ticks) < 2:
            return False, "expected at least two tick <rect> elements (neither full-height nor full-width), got %d" % len(ticks)

        return True, ""
    check(
        "battery_sparkline_svg() draws real axis chrome — at least one full-height vertical axis <rect>, at "
        "least one full-width horizontal axis <rect>, and at least two tick <rect> elements, all carrying "
        "SPARKLINE_AXIS_CLASS and aria-hidden=\"true\" on their own tags (quick task 260902-ep7 BUG 4)",
        _sparkline_axis_chrome_present)

    def _sparkline_daily_mode_shows_date_endpoints_not_clock():
        # 260902-l0b: in daily mode, the X-axis endpoints must be
        # day-plus-month date labels (_axis_day_label()), never the
        # clock-format labels a day string would otherwise silently
        # render as ("00:00" — see _axis_day_label()'s own docstring for
        # why _axis_clock_label() would "work" but lie here).
        rows = [
            {"ts": "2026-09-02", "battery_mv": 4100, "reading_count": 12},
            {"ts": "2026-09-01", "battery_mv": 4101, "reading_count": 9},
            {"ts": "2026-08-31", "battery_mv": 4102, "reading_count": 1},
        ]
        svg = health_page.battery_sparkline_svg(rows, now="2026-09-02T12:00:00+00:00", daily=True)
        labels = re.findall(r'<span class="sparkline-axis-label"[^>]*>([^<]*)</span>', svg)
        if len(labels) != 4:
            return False, "expected exactly four axis labels (2 Y, 2 X), got %r" % (labels,)
        x_labels = labels[2:]
        if x_labels != ["31 Aug", "2 Sep"]:
            return False, "expected the oldest-then-newest date endpoints '31 Aug'/'2 Sep', got %r" % (x_labels,)
        if re.search(r">\d{2}:\d{2}<", svg):
            return False, "found a clock-format (HH:MM) label — a day string must never render through the clock formatter"
        return True, ""
    check(
        "battery_sparkline_svg(daily=True) renders day-plus-month date endpoint labels ('31 Aug'/'2 Sep'), "
        "never the clock-format labels a day string would otherwise silently print (260902-l0b)",
        _sparkline_daily_mode_shows_date_endpoints_not_clock)

    def _sparkline_daily_point_label_names_day_and_average_count():
        # 260902-l0b: each daily point's hover/tap label must say it is an
        # average and how many readings formed it — the only thing on the
        # page that tells the developer the readout switched from a raw
        # reading (at rest) to an average (on hover/tap).
        rows = [
            {"ts": "2026-09-02", "battery_mv": 4100, "reading_count": 12},
            {"ts": "2026-09-01", "battery_mv": 4101, "reading_count": 9},
            {"ts": "2026-08-31", "battery_mv": 4102, "reading_count": 1},
        ]
        svg = health_page.battery_sparkline_svg(rows, now="2026-09-02T12:00:00+00:00", daily=True)
        whens = re.findall(r'data-when="([^"]*)"', svg)
        if len(whens) != 3:
            return False, "expected one humanised label per point, got %r" % (whens,)
        newest = whens[-1]
        if "2 Sep" not in newest or "12" not in newest:
            return False, "expected the newest point's label to name its day and its 12-reading count: %r" % newest
        if "average" not in newest.lower():
            return False, "expected the newest point's label to say it is a daily average: %r" % newest
        oldest = whens[0]
        if not re.search(r"\b1 reading\b", oldest):
            return False, "expected a single-reading day to read singular ('1 reading', not '1 readings'): %r" % oldest
        return True, ""
    check(
        "each daily chart point's data-when names its day, says it is a daily average, and gives the singular/"
        "plural-correct contributing reading count (260902-l0b)",
        _sparkline_daily_point_label_names_day_and_average_count)

    def _sparkline_density_rule_suppresses_dots_only_above_threshold():
        # 260902-l0b: the density rule is threshold-gated, not
        # unconditional — below the derived threshold every point still
        # gets its cosmetic dot and full-size hit target; at/above it,
        # dots stop being emitted but every hit target survives (at the
        # smaller dense radius), so no point becomes unreachable.
        threshold_names = [name for name in dir(health_page) if "DENSE" in name]
        if not threshold_names:
            return False, "expected a named, documented DENSE* density-threshold constant, not a literal in the loop"
        threshold = max(
            getattr(health_page, name) for name in threshold_names
            if isinstance(getattr(health_page, name), int) and getattr(health_page, name) > 10)

        dense_rows = [
            {"ts": "2026-06-%02d" % ((i % 28) + 1), "battery_mv": 4000 + i}
            for i in range(threshold + 5)]
        dense_svg = health_page.battery_sparkline_svg(
            dense_rows, now="2026-09-02T12:00:00+00:00", daily=True)
        if health_page.SPARKLINE_DOT_CLASS in dense_svg:
            return False, "expected no cosmetic dots above the density threshold"
        if dense_svg.count(health_page.SPARKLINE_HIT_CLASS) != len(dense_rows):
            return False, "expected every point to keep its own hit target above the density threshold"
        if 'r="8"' in dense_svg:
            return False, "expected the reduced dense hit radius above the threshold, not the normal r=\"8\""
        if dense_svg.count(health_page.SPARKLINE_LINE_CLASS) != len(dense_rows) - 1:
            return False, "expected the thin trend line to still carry one segment per adjacent pair above the threshold"

        just_under_rows = [
            {"ts": "2026-06-%02d" % ((i % 28) + 1), "battery_mv": 4000 + i}
            for i in range(threshold - 1)]
        just_under_svg = health_page.battery_sparkline_svg(
            just_under_rows, now="2026-09-02T12:00:00+00:00", daily=True)
        if health_page.SPARKLINE_DOT_CLASS not in just_under_svg:
            return False, "expected cosmetic dots to survive just below the density threshold"
        if 'r="8"' not in just_under_svg:
            return False, "expected the normal, full-size hit radius just below the density threshold"

        sparse_rows = [{"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4200 - i * 10} for i in range(3)]
        sparse_svg = health_page.battery_sparkline_svg(sparse_rows)
        if health_page.SPARKLINE_DOT_CLASS not in sparse_svg:
            return False, "a below-threshold, non-daily call must keep its cosmetic dots (regression guard)"
        if 'r="8"' not in sparse_svg:
            return False, "a below-threshold, non-daily call must keep its normal hit radius (regression guard)"
        if not re.search(r">\d{2}:\d{2}<", sparse_svg):
            return False, "a below-threshold, non-daily call must keep its clock endpoint labels (regression guard)"
        return True, ""
    check(
        "the density rule suppresses cosmetic dots only at/above the derived threshold (every hit target "
        "still reachable, at the reduced radius), survives untouched just below it, and a below-threshold "
        "non-daily call stays byte-for-byte what it is today (260902-l0b)",
        _sparkline_density_rule_suppresses_dots_only_above_threshold)

    def _battery_readout_seeded_with_latest_reading_not_placeholder():
        # quick task 260901-uzi (finding 3): rebuilds the expected markup
        # from the same helper the page itself calls
        # (health_page._battery_reading_parts()) rather than re-typing a
        # format string into the harness — the harness must not become a
        # second place this format lives.
        #
        # health_page._battery_section() deliberately computes its own
        # `now` via history_db.utc_now_iso() (06.6-01, D-02 — see that
        # function's own comment) rather than accepting the render() ctx's
        # injected `now`, so the real wall clock — not the seeded `base`
        # below — is what actually humanises the readout's "ago" text.
        # Left unpatched, this check races the real clock: any elapsed
        # time between capturing `base` and _battery_section()'s own
        # history_db.utc_now_iso() call that crosses a whole-second
        # boundary flips the rendered "(0s ago)" to "(1s ago)", a genuine
        # CI flake (observed 2026-09-03) unrelated to any production
        # defect. Pinning history_db.utc_now_iso() to `base` for the
        # duration of this render() call — monkeypatch-and-restore,
        # mirroring illustrations.target_variants_by_airline()'s own
        # precedent above — makes the two `now` values identical by
        # construction instead of by luck.
        tmp = _mkstate("h-readout-seeded")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ]
            _seed_device_health(tmp, readings)
            original_utc_now_iso = history_db.utc_now_iso
            history_db.utc_now_iso = lambda: _iso(base)
            try:
                rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            finally:
                history_db.utc_now_iso = original_utc_now_iso
            value_text, when_text = health_page._battery_reading_parts(
                4190, _iso(base), _iso(base))
            expected_inner = (
                '<span class="battery-readout__value mono">%s</span>'
                '<span class="battery-readout__detail" title="%s"> — %s</span>'
            ) % (
                health_page.escape_html(value_text),
                health_page.escape_html(_iso(base)),
                health_page.escape_html(when_text),
            )
            readout_start = rendered.index('id="%s"' % health_page.BATTERY_READOUT_ID)
            readout_tag_end = rendered.index(">", readout_start)
            readout_text_end = rendered.index("</p>", readout_tag_end)
            readout_inner = rendered[readout_tag_end + 1:readout_text_end]
            if readout_inner != expected_inner:
                return False, (
                    "expected the readout's inner markup to equal the humanised (value, when) pair "
                    "built by _battery_reading_parts(), got %r" % (readout_inner,))
            if "Tap or hover a point" in rendered:
                return False, "did not expect the retired BATTERY_READOUT_PLACEHOLDER prompt text anywhere on the page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery readout's initial markup equals the humanised (value, when) pair the latest reading's own "
        "helper builds, split across its value/detail spans, and the retired placeholder prompt no longer "
        "appears (D-09, quick task 260901-uzi finding 3)",
        _battery_readout_seeded_with_latest_reading_not_placeholder)

    def _single_reading_still_no_chart_no_readout_no_script():
        if health_page.battery_sparkline_svg(
                [{"ts": "t1", "battery_mv": 4200}]) != "":
            return False, "expected battery_sparkline_svg() to return '' for a single-row input"
        tmp = _mkstate("h-single-reading-no-chart")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "<script" in rendered:
                return False, "did not expect a <script tag with only one battery reading"
            if health_page.BATTERY_READOUT_ID in rendered:
                return False, "did not expect the readout element id with only one battery reading"
            # quick task 260902-ep7 (BUG 4): retargeted in place from the
            # retired <polyline marker (see _battery_empty_state_no_sparkline()
            # above for why retargeting this negative assertion is
            # mandatory, not cosmetic).
            if health_page.SPARKLINE_LINE_CLASS in rendered:
                return False, "did not expect a sparkline trend-line segment with only one battery reading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "battery_sparkline_svg() still returns '' for fewer than two numeric readings, and the page emits neither "
        "a readout element nor a chart script tag (D-09 regression guard)",
        _single_reading_still_no_chart_no_readout_no_script)

    def _page_allows_exactly_one_scoped_script_no_inline_handlers():
        tmp = _mkstate("h-script-scope")
        try:
            base = _now()
            _seed_device_health(tmp, [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if rendered.count("<script") != 1:
                return False, "expected exactly one <script tag, got %d" % rendered.count("<script")
            if health_page.BATTERY_TREND_SCRIPT_SRC not in rendered:
                return False, "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>"
            for forbidden in ("onclick=", "onmouseover=", "ontouchstart=", "onfocus=", "onload="):
                if forbidden in rendered:
                    return False, "found forbidden inline event-handler attribute %r" % forbidden
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a chart-bearing page emits exactly one scoped <script src> and zero inline event-handler attributes",
        _page_allows_exactly_one_scoped_script_no_inline_handlers)

    def _empty_battery_history_stays_script_free():
        tmp = _mkstate("h-empty-script-free")
        try:
            rendered = health_page.render(_ctx(tmp))
            if "<script" in rendered:
                return False, "did not expect any <script tag with zero battery rows"
            # 06.6.1-04: "no <svg" stopped being a valid proxy for "no
            # sparkline" once the page gained four icon instances (D-02)
            # — retargeted to the sparkline-specific markers, same fix
            # as _battery_empty_state_no_sparkline() above. quick task
            # 260902-ep7 (BUG 4): retargeted in place again, from the
            # retired <polyline marker onto SPARKLINE_LINE_CLASS — another
            # negative assertion that would pass vacuously if left
            # pointing at a marker that no longer exists. The
            # <script>/readout assertions below are unaffected and are
            # this check's real, unchanged subject.
            if health_page.SPARKLINE_LINE_CLASS in rendered:
                return False, "did not expect a sparkline trend-line segment with zero battery rows"
            if health_page.SPARKLINE_DOT_CLASS in rendered:
                return False, "did not expect a sparkline dot with zero battery rows"
            if health_page.BATTERY_READOUT_ID in rendered:
                return False, "did not expect the readout element id with zero battery rows"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the empty-history battery path stays script-free — no <script, no <svg, no readout element",
        _empty_battery_history_stays_script_free)

    def _hostile_timestamp_is_escaped_in_chart_markup():
        tmp = _mkstate("h-hostile-ts")
        try:
            base = _now()
            hostile_ts = '2024-01-01T00:00:00Z"><script>alert(1)</script>'
            _seed_device_health(tmp, [
                (hostile_ts, 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if hostile_ts in rendered:
                return False, "the raw hostile timestamp fragment survived unescaped into the output"
            if '"><script>alert(1)</script>' in rendered:
                return False, "the raw quote-and-tag fragment survived unescaped into a double-quoted attribute"
            escaped_ts = health_page.escape_html(hostile_ts)
            if escaped_ts not in rendered:
                return False, "expected the escaped form of the hostile timestamp to appear"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a hostile timestamp reaching data-ts/<title> is escaped, never interpolated raw",
        _hostile_timestamp_is_escaped_in_chart_markup)

    def _cross_file_contract_drift_guard():
        import companion.app as app_module
        if app_module.SCRIPT_ROUTE != health_page.BATTERY_TREND_SCRIPT_SRC:
            return False, "companion.app.SCRIPT_ROUTE and health_page.BATTERY_TREND_SCRIPT_SRC have drifted apart"
        js_path = os.path.join(HERE, "static", "battery-trend.js")
        with open(js_path) as fh:
            js_source = fh.read()
        if health_page.BATTERY_READOUT_ID not in js_source:
            return False, "battery-trend.js no longer references BATTERY_READOUT_ID's literal value"
        if health_page.SPARKLINE_HIT_CLASS not in js_source:
            return False, "battery-trend.js no longer references SPARKLINE_HIT_CLASS's literal value"
        tmp = _mkstate("h-contract-drift")
        try:
            base = _now()
            _seed_device_health(tmp, [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "expected BATTERY_READOUT_ID in a rendered chart-bearing page"
            if health_page.SPARKLINE_HIT_CLASS not in rendered:
                return False, "expected SPARKLINE_HIT_CLASS in a rendered chart-bearing page"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Python/CSS/JS three-file contract (route + DOM literals) is guarded against silent drift",
        _cross_file_contract_drift_guard)

    def _battery_drop_flags_anomaly_gentle_decline_does_not():
        # battery_status() takes newest-first rows (matching
        # battery_trend_rows()'s/recent_device_health()'s own ordering) —
        # t2 (newer) sorts before t1 (older) in both fixtures below.
        drop_rows = [
            {"ts": "t2", "battery_mv": 4200 - health_page.BATTERY_DROP_WARN_MV},
            {"ts": "t1", "battery_mv": 4200},
        ]
        if health_page.battery_status(drop_rows) != "error":
            return False, "expected a drop >= BATTERY_DROP_WARN_MV to flag the battery anomaly"
        gentle_rows = [
            {"ts": "t3", "battery_mv": 4190},
            {"ts": "t2", "battery_mv": 4195},
            {"ts": "t1", "battery_mv": 4200},
        ]
        if health_page.battery_status(gentle_rows) != "ok":
            return False, "expected a gentle monotonic decline to not flag the battery anomaly"
        return True, ""
    check(
        "a large consecutive-reading drop flags the battery anomaly; a gentle monotonic decline does not",
        _battery_drop_flags_anomaly_gentle_decline_does_not)

    def _corroboration_unknown_only_no_error_or_warn():
        tmp = _mkstate("h-corrob-unknown")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [
                {"ts": _iso(now), "hex": "abc123", "corroborated": None},
                {"ts": _iso(now), "hex": "abc123", "corroborated": None},
            ])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if "dot--error" in rendered:
                return False, "expected no error status class for an unknown-state-only corroboration count"
            if "dot--warn" in rendered:
                return False, "expected no warn status class either — this fixture is fully healthy otherwise"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "corroboration counts made only of the unknown state produce no error status class",
        _corroboration_unknown_only_no_error_or_warn)

    def _no_anomaly_banner_when_all_healthy():
        tmp = _mkstate("h-no-anomaly")
        try:
            now = _now()
            _seed_device_health(tmp, [
                (_iso(now - timedelta(minutes=2)), 4200),
                (_iso(now), 4198),
            ])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            _seed_runway_events(tmp, [{"ts": _iso(now), "hex": "abc123", "corroborated": True}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if health_page.ANOMALY_BANNER_TEXT in rendered:
                return False, "did not expect the anomaly banner when every signal is healthy"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-healthy fixture renders no anomaly banner at all",
        _no_anomaly_banner_when_all_healthy)

    def _stale_pipeline_shows_banner_exactly_once():
        tmp = _mkstate("h-stale-pipeline")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{
                history_db.META_LAST_PIPELINE_RUN: _ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
            if count != 1:
                return False, "expected the anomaly banner copy exactly once, found %d" % count
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a stale ADS-B pipeline shows the anomaly banner copy exactly once",
        _stale_pipeline_shows_banner_exactly_once)

    def _unreadable_database_degrades_without_raising():
        base = tempfile.mkdtemp(prefix="skypane-status-pages-blocked-")
        blocked_state_dir = os.path.join(base, "blocked")
        try:
            with open(blocked_state_dir, "w") as fh:
                fh.write("this is a file, not a directory")
            rendered = health_page.render(_ctx(blocked_state_dir))
            if health_page.HEALTH_UNAVAILABLE_TEXT not in rendered:
                return False, "expected the health-unavailable copy when the database cannot be opened"
            return True, ""
        finally:
            shutil.rmtree(base, ignore_errors=True)
    check(
        "a state directory that cannot hold a database renders the health-unavailable copy without raising",
        _unreadable_database_degrades_without_raising)

    def _source_fault_set_shows_landing_explanation():
        tmp = _mkstate("h-source-fault-set")
        try:
            _seed_meta(tmp, **{history_db.META_SOURCE_FAULT: "True"})
            rendered = health_page.render(_ctx(tmp))
            if health_page.SOURCE_FAULT_HEADING not in rendered:
                return False, "expected the CFG-05 landing explanation when the source-fault flag is set"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with the source-fault meta key set, the CFG-05 landing explanation appears",
        _source_fault_set_shows_landing_explanation)

    def _source_fault_unset_hides_landing_explanation():
        tmp = _mkstate("h-source-fault-unset")
        try:
            rendered = health_page.render(_ctx(tmp))
            if health_page.SOURCE_FAULT_HEADING in rendered:
                return False, "did not expect the CFG-05 landing explanation with no source-fault flag set"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with the source-fault meta key unset, the CFG-05 landing explanation is absent",
        _source_fault_unset_hides_landing_explanation)

    def _health_page_never_imports_html_module():
        with open(os.path.join(HERE, "pages", "health_page.py")) as fh:
            source = fh.read()
        for line in source.splitlines():
            if line.strip() == "import html":
                return False, "health_page.py must never import the stdlib html module directly"
        return True, ""
    check(
        "companion/pages/health_page.py never imports the stdlib html module directly",
        _health_page_never_imports_html_module)

    def _health_page_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): Health's top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        tmp = _mkstate("h-page-header")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if '<h1 class="page-title">Health</h1>' not in rendered:
                return False, "expected the page_header()-rendered <h1 class=\"page-title\">Health</h1>"
            if '<h1 class="text-heading">' in rendered:
                return False, "expected no bare <h1 class=\"text-heading\"> heading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health opens with the shared layout.page_header() component, not a bare <h1>",
        _health_page_opens_with_shared_page_header)

    def _health_page_purpose_sentence_present_after_refresh():
        # quick task 260901-tsa (finding A): PAGE_PURPOSE_TEXT reaches
        # layout.page_header()'s `purpose` parameter, renders inside
        # .page-header, and — per that component's own reordered
        # emission (Task 1) — follows the Refresh link, matching the
        # validated sketch's own DOM order.
        tmp = _mkstate("h-page-purpose")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            escaped_purpose = layout.escape_html(health_page.PAGE_PURPOSE_TEXT)
            if rendered.count(escaped_purpose) != 1:
                return False, (
                    "expected the escaped page-purpose sentence exactly once, got %d"
                    % rendered.count(escaped_purpose))
            header_start = rendered.index('<div class="page-header">')
            header_end = rendered.index("</div>", header_start) + len("</div>")
            header_slice = rendered[header_start:header_end]
            if escaped_purpose not in header_slice:
                return False, "expected the purpose sentence inside the .page-header div, not elsewhere on the page"
            # 260902-chc: retargeted from the retired "freshness-refresh"
            # link class onto the pill's own marker attribute — the
            # ordering property this check tests (the header's action
            # slot precedes the purpose sentence) is unchanged by that
            # reversal.
            refresh_at = rendered.index("data-refresh-pill")
            purpose_at = rendered.index(escaped_purpose)
            if refresh_at >= purpose_at:
                return False, (
                    "expected the purpose sentence to follow the pill, matching the "
                    "validated sketch's own DOM order")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's .page-header carries a one-sentence purpose after the auto-refresh pill (quick task "
        "260901-tsa, finding A; retargeted in place by 260902-chc)",
        _health_page_purpose_sentence_present_after_refresh)

    def _health_page_two_id_anchored_sections_correct_order_no_overview():
        # 06.6.4.1-04 (D-10): Health's body is now two id-anchored
        # sections, Screen then Server & data, replacing the single
        # "Overview" heading + one dashboard-grid shape.
        tmp = _mkstate("h-two-sections")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if rendered.count(">Overview<") != 0:
                return False, "expected the old 'Overview' heading to be gone"
            screen_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
                health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING)
            server_data_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
                health_page.SERVER_DATA_SECTION_ID,
                layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING))
            if screen_heading not in rendered:
                return False, "expected the Screen section's id-anchored <h2>"
            if server_data_heading not in rendered:
                return False, "expected the Server & data section's id-anchored <h2>"
            if rendered.index(screen_heading) >= rendered.index(server_data_heading):
                return False, "expected the Screen section to precede the Server & data section"
            if rendered.count('<h2 id="') != 2:
                return False, "expected exactly two id-anchored <h2> elements"
            # quick task 260902-gjj: retargeted from
            # rendered.count(BATTERY_SECTION_CLASS) — once the section's
            # own class attribute also carries a status modifier
            # (BATTERY_SECTION_CLASS + "--ok"/"--warn"/"--error"), the
            # bare class-name substring appears TWICE inside that one
            # attribute, so the old literal count would silently stop
            # meaning "one section" the moment a modifier landed. The
            # open-tag prefix counts sections, not substrings.
            if rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS) != 1:
                return False, (
                    "expected exactly one battery-trend section, got %d"
                    % rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS))
            if rendered.index(health_page.BATTERY_SECTION_CLASS) <= rendered.index(screen_heading):
                return False, "expected the battery-trend section to follow the Screen heading"
            if rendered.index(health_page.BATTERY_SECTION_CLASS) >= rendered.index(server_data_heading):
                return False, "expected the battery-trend section to stay inside the Screen section, before Server & data"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Health's body is two id-anchored sections (Screen, then Server & data), and the old 'Overview' heading "
        "is gone (D-10)",
        _health_page_two_id_anchored_sections_correct_order_no_overview)

    def _health_page_section_intros_pair_heading_with_description():
        # quick task 260901-tsa (finding B): each section's <h2> is now
        # paired with its own muted description inside a .section-intro
        # wrapper. Slices each wrapper individually (rather than
        # searching the whole page) so the check cannot pass by finding
        # the right description next to the wrong heading.
        tmp = _mkstate("h-section-intro")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            wrapper_count = rendered.count('<div class="section-intro">')
            if wrapper_count != 2:
                return False, "expected exactly two section-intro wrappers, got %d" % wrapper_count

            screen_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
                health_page.SCREEN_SECTION_ID,
                layout.escape_html(health_page.SCREEN_SECTION_HEADING))
            server_data_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
                health_page.SERVER_DATA_SECTION_ID,
                layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING))
            # Every expected substring is built through escape_html() —
            # never re-typed as a raw literal. The Screen description
            # contains an apostrophe ("how's the battery"), which
            # escape_html(..., quote=True) encodes; a raw-constant
            # comparison would fail here for a reason that has nothing
            # to do with the markup being wrong. This is the single
            # likeliest way this check gets "fixed" wrongly later.
            screen_description = layout.escape_html(health_page.SCREEN_SECTION_DESCRIPTION)
            server_data_description = layout.escape_html(health_page.SERVER_DATA_SECTION_DESCRIPTION)

            first_open = rendered.index('<div class="section-intro">')
            first_close = rendered.index("</div>", first_open) + len("</div>")
            first_wrapper = rendered[first_open:first_close]
            second_open = rendered.index('<div class="section-intro">', first_close)
            second_close = rendered.index("</div>", second_open) + len("</div>")
            second_wrapper = rendered[second_open:second_close]

            if screen_heading not in first_wrapper or screen_description not in first_wrapper:
                return False, "expected the first section-intro wrapper to hold the Screen heading and description"
            if first_wrapper.index(screen_heading) >= first_wrapper.index(screen_description):
                return False, "expected the Screen heading to precede its own description"

            if server_data_heading not in second_wrapper or server_data_description not in second_wrapper:
                return False, (
                    "expected the second section-intro wrapper to hold the Server & data heading and description")
            if second_wrapper.index(server_data_heading) >= second_wrapper.index(server_data_description):
                return False, "expected the Server & data heading to precede its own description"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "each of Health's two section headings is paired, in its own baseline-aligned .section-intro wrapper, "
        "with its own muted description (quick task 260901-tsa, finding B)",
        _health_page_section_intros_pair_heading_with_description)

    def _server_data_grid_holds_three_tiles_migrated_cards_outside_grid():
        tmp = _mkstate("h-server-data-grid")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: _iso(now)})
            registry = {
                "ABC": {"count": 1, "first_seen": _iso(now), "last_seen": _iso(now), "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            events = [{"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}]
            _seed_runway_events(tmp, events)
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            # quick task 260901-tsa (finding E): the Screen section now
            # also wraps its own single Device tile in a dashboard-grid,
            # so the page carries TWO dashboard-grid divs, not one. This
            # check's own dashboard-grid lookup is deliberately anchored
            # to the Server & data heading's own offset below, never a
            # first-occurrence index — a first-occurrence index would now
            # silently measure the Screen section's grid instead of the
            # Server & data one, the exact trap finding E introduces.
            if rendered.count('<div class="dashboard-grid">') != 2:
                return False, (
                    "expected exactly two dashboard-grid divs (Screen's single-tile "
                    "grid + Server & data's three-tile grid), got %d"
                    % rendered.count('<div class="dashboard-grid">'))
            # Trailing space distinguishes a stat-tile wrapper div's own
            # class attribute (always "stat-tile <modifier>") from the
            # Resolution-rate tile's inner <p class="stat-tile__value">
            # figure, which this fixture's 100%-resolved stats also emit.
            if rendered.count('class="stat-tile ') != 4:
                return False, (
                    "expected exactly four stat-tile occurrences (Device in the Screen "
                    "grid + Pipeline/Corroboration/Resolution-rate in the Server & data "
                    "grid), got %d" % rendered.count('class="stat-tile '))

            server_data_heading_at = rendered.index(
                '<h2 id="%s" class="text-heading">' % health_page.SERVER_DATA_SECTION_ID)
            screen_grid_open = rendered.index('<div class="dashboard-grid">')
            server_data_grid_open = rendered.index(
                '<div class="dashboard-grid">', server_data_heading_at)
            if server_data_grid_open == screen_grid_open:
                return False, (
                    "expected two distinct dashboard-grid divs, found only one "
                    "after the Server & data heading")

            # The new invariant finding E introduces: the Screen section's
            # own grid holds exactly one tile — checked beside the Server
            # & data grid's own three-tile invariant below.
            screen_grid_slice = rendered[screen_grid_open:server_data_heading_at]
            if screen_grid_slice.count('class="stat-tile ') != 1:
                return False, (
                    "expected exactly one stat-tile occurrence inside the Screen "
                    "section's dashboard-grid, got %d"
                    % screen_grid_slice.count('class="stat-tile '))

            # quick task 260901-uzi (finding 4): both migrated cards now
            # carry an additive `page-section--nested` modifier, so the
            # bare `'<section class="page-section">'` literal this check
            # used to key on no longer matches either — retargeted onto
            # the modifier-bearing literal below.
            #
            # quick task 260902-gjj (ISSUE 2): retargeted AGAIN, from the
            # exact-literal '<section class="page-section page-section--
            # nested">' onto this open-ended prefix — the registry card's
            # class attribute now also carries a status modifier
            # (coverage_status()'s own "--ok"/"--warn"), so the closing
            # quote no longer immediately follows "page-section--nested"
            # on that card (the Resolution-statistics card, which carries
            # no status modifier, still matches the old exact literal —
            # only the registry card moved). The lookup now STRENGTHENS
            # rather than merely survives: the slice-and-check just below
            # confirms which of the two cards this prefix actually found.
            first_section_open = rendered.index(
                '<section class="page-section page-section--nested')
            first_section_close = rendered.index("</section>", first_section_open) + len("</section>")
            first_section_slice = rendered[first_section_open:first_section_close]
            if health_page.UNRESOLVED_SECTION_HEADING not in first_section_slice:
                return False, (
                    "expected the first nested page-section card (found via its own "
                    "open-tag prefix) to be the Unresolved-prefixes card, got %r"
                    % first_section_slice[:120])
            if first_section_open <= server_data_grid_open:
                return False, (
                    "expected the first migrated page-section card to follow the "
                    "Server & data dashboard-grid")
            grid_slice = rendered[server_data_grid_open:first_section_open]
            if grid_slice.count('class="stat-tile ') != 3:
                return False, (
                    "expected exactly three stat-tile occurrences inside the Server "
                    "& data dashboard-grid, got %d" % grid_slice.count('class="stat-tile '))
            if health_page.UNRESOLVED_SECTION_HEADING in grid_slice:
                return False, "the Unresolved-prefixes card must not appear inside the dashboard-grid"
            if health_page.STATS_SECTION_HEADING in grid_slice:
                return False, "the Resolution-statistics card must not appear inside the dashboard-grid"
            if rendered.count('<section class="page-section page-section--nested') != 2:
                return False, (
                    "expected exactly two nested page-section cards (registry + stats), got %d"
                    % rendered.count('<section class="page-section page-section--nested'))
            # The new invariant part B introduces: the source-fault
            # block's own page-section (rendered only when
            # META_SOURCE_FAULT is set, not seeded by this fixture) must
            # never carry the nested modifier — checked unconditionally
            # against the whole page rather than gated on the fixture,
            # since the modifier-bearing count assertion above already
            # proves no OTHER page-section carries it either.
            if 'class="page-section banner banner--anomaly page-section--nested"' in rendered:
                return False, "the source-fault block must never carry the nested modifier"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Screen section's dashboard-grid holds exactly one tile, the Server & data dashboard-grid holds "
        "exactly three, the two migrated cards render as nested page-section elements outside both, and the "
        "source-fault block never carries that modifier (D-11/finding E, quick task 260901-uzi finding 4)",
        _server_data_grid_holds_three_tiles_migrated_cards_outside_grid)

    def _resolution_rate_tile_renders_percentage_and_window():
        tmp = _mkstate("h-resolution-rate-tile")
        try:
            now = _now()
            events = []
            for source in ("fresh_hit", "fresh_hit", "cache_hit", "miss"):
                events.append({"ts": _iso(now), "hex": "abc123", "route_source": source})
            _seed_runway_events(tmp, events)
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))
            if health_page.RESOLUTION_RATE_LABEL not in rendered:
                return False, "expected the Resolution rate tile's caption"
            if "75.0%" not in rendered:
                return False, "expected the resolved percentage in the tile's stat-tile__value"
            if ("over the last %d days, 4 events" % health_page.RESOLUTION_WINDOW_DAYS) not in rendered:
                return False, "expected the window/event-count text-label line"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        tmp_empty = _mkstate("h-resolution-rate-tile-empty")
        try:
            rendered_empty = health_page.render(_ctx(tmp_empty))
            if health_page._NO_STATS_HEADING not in rendered_empty:
                return False, "expected the no-stats empty-state heading with zero resolution history"
            return True, ""
        finally:
            shutil.rmtree(tmp_empty, ignore_errors=True)
    check(
        "the Resolution-rate tile renders the resolved percentage and the window/event-count line for a seeded "
        "fixture, and the no-stats empty state for an empty one (D-10/D-11)",
        _resolution_rate_tile_renders_percentage_and_window)

    def _registry_card_keeps_filter_bar_note_and_non_button_clear():
        tmp = _mkstate("h-registry-card")
        try:
            registry = {
                "ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
            }
            _seed_unresolved_prefixes(tmp, registry)
            rendered = health_page.render(_ctx(tmp))
            for marker in ("data-filter-input", "data-filter-count", "data-filter-clear", "data-filter-empty"):
                if marker not in rendered:
                    return False, "expected the migrated filter bar's %r marker to survive the move" % marker
            if health_page._READ_ONLY_NOTE not in rendered:
                return False, "expected the read-only note to survive the move verbatim"
            section_start = rendered.index(
                '<h2 class="text-heading">%s</h2>' % health_page.UNRESOLVED_SECTION_HEADING)
            section_slice = rendered[section_start:section_start + 4000]
            if "<button" in section_slice:
                return False, "the migrated registry card's Clear control must not be a <button>"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the migrated Unresolved-prefixes card keeps its filter bar, read-only note, and non-button Clear "
        "control (D-12)",
        _registry_card_keeps_filter_bar_note_and_non_button_clear)

    def _quick_260902_gjj_muted_captions_compose_section_caption():
        # quick task 260902-gjj (ISSUE 1): pins the markup pair (both
        # fragments compose `section-caption` onto their existing sizing
        # class) AND the single muted strength (style.css's
        # .section-caption still declares exactly one property, the same
        # 70% color-mix), together — so a future edit cannot satisfy the
        # markup half while quietly forking a second muted value.
        tmp = _mkstate("h-muted-captions")
        try:
            rendered = health_page.render(_ctx(tmp))
            heading_at = rendered.index(">%s" % health_page.BATTERY_SECTION_HEADING)
            heading_close = rendered.index("</h2>", heading_at) + len("</h2>")
            heading_html = rendered[heading_at:heading_close]
            if 'class="text-label section-caption"' not in heading_html:
                return False, (
                    "expected the battery heading's trailing span to compose "
                    "text-label with section-caption, got %r" % heading_html)

            note_at = rendered.index(health_page._READ_ONLY_NOTE)
            note_open = rendered.rindex("<p", 0, note_at)
            note_tag = rendered[note_open:rendered.index(">", note_open) + 1]
            if 'class="text-body section-caption"' not in note_tag:
                return False, (
                    "expected the read-only note's own <p> to compose text-body "
                    "with section-caption, got %r" % note_tag)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        i = css_source.index(".section-caption {")
        body = css_source[i:css_source.index("}", i)]
        if body.count(";") != 1 or (
                "color-mix(in srgb, var(--color-text) 70%, transparent)" not in body):
            return False, (
                "expected .section-caption to still declare exactly one property, "
                "the file's single 70%% muted color-mix, got %r" % body)
        return True, ""
    check(
        "the battery heading's trailing span and the Unresolved-prefixes read-only note both compose "
        "section-caption with their existing sizing class, and style.css's .section-caption still declares "
        "exactly one property at the file's single 70% muted strength (quick task 260902-gjj, ISSUE 1)",
        _quick_260902_gjj_muted_captions_compose_section_caption)

    def _migrated_cards_have_independent_failure_isolation():
        # D-11: the registry read (poll_loop.load_poll_state(), a
        # filesystem/JSON failure mode) and the stats read
        # (_safe_query(), a SQLite failure mode) must degrade
        # independently — corrupting one source must never take down
        # the other card.
        tmp_db_broken = _mkstate("h-isolation-db-broken")
        try:
            with history_db.open_db(tmp_db_broken):
                pass
            dbs = [f for f in os.listdir(tmp_db_broken) if f.endswith(".db")]
            if not dbs:
                return False, "expected a database file to have been created"
            with open(os.path.join(tmp_db_broken, dbs[0]), "wb") as fh:
                fh.write(b"not a sqlite file at all")
            _seed_unresolved_prefixes(tmp_db_broken, {
                "ABC": {"count": 2, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
            })
            rendered = health_page.render(_ctx(tmp_db_broken))
            if "ABC" not in rendered:
                return False, "expected the registry rows to still render when only the database is broken"
            if health_page.HEALTH_UNAVAILABLE_TEXT not in rendered:
                return False, "expected the stats card to show the unavailable copy when the database is broken"
        finally:
            shutil.rmtree(tmp_db_broken, ignore_errors=True)

        tmp_registry_broken = _mkstate("h-isolation-registry-broken")
        try:
            now = _now()
            events = [{"ts": _iso(now), "hex": "abc123", "route_source": "fresh_hit"}]
            _seed_runway_events(tmp_registry_broken, events)
            poll_state_path = os.path.join(tmp_registry_broken, "poll_state.json")
            with open(poll_state_path, "w") as fh:
                fh.write("not valid json {")
            rendered = health_page.render(_ctx(tmp_registry_broken, now=_iso(now)))
            if "100.0% resolved" not in rendered:
                return False, "expected the resolution-rate stats to still render when only the registry file is malformed"
            if health_page._NO_GAPS_HEADING not in rendered:
                return False, "expected the registry to degrade to its empty/no-gaps state, not crash the page"
            return True, ""
        finally:
            shutil.rmtree(tmp_registry_broken, ignore_errors=True)
    check(
        "corrupting only the database leaves the registry card rendering while the stats card degrades, and "
        "vice versa (D-11)",
        _migrated_cards_have_independent_failure_isolation)

    def _read_health_inputs_keeps_registry_stats_separate():
        # 260902-l0b: renamed from _read_health_inputs_gained_no_new_key()
        # — that name stopped being true the moment daily_rows joined
        # trend_rows in this dict (a battery-health read, same table, same
        # section builder, same request). Quick task 260903-peo (UIR-14)
        # retargets this check in place again, six keys to seven:
        # last_detection joins pipeline_ts for the identical reason (same
        # section builder, same table, same request). D-11's real intent
        # survives, restated explicitly: the migrated registry/stats
        # reads must stay their own independent calls in render(), never
        # folded into _read_health_inputs()'s single dict — that is what
        # the negative assertion below checks directly, not just the key
        # count.
        tmp = _mkstate("h-inputs-keys")
        try:
            inputs = health_page._read_health_inputs(tmp, _iso(_now()))
            expected_keys = {
                "device_health", "pipeline_ts", "last_detection", "source_fault_raw",
                "trend_rows", "daily_rows", "corroboration_counts",
            }
            if set(inputs.keys()) != expected_keys:
                return False, (
                    "expected _read_health_inputs() to carry exactly these seven keys, got %r"
                    % (set(inputs.keys()),))
            if any("registr" in k or "stat" in k for k in inputs.keys()):
                return False, "D-11: the registry/stats reads must stay separate calls in render(), not join this dict"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "_read_health_inputs() carries exactly seven keys — last_detection joins pipeline_ts in the one "
        "atomic snapshot (quick task 260903-peo, UIR-14) — while the migrated registry/stats reads stay "
        "separate calls in render() (D-11)",
        _read_health_inputs_keeps_registry_stats_separate)

    def _battery_section_keeps_everything_after_the_move():
        tmp = _mkstate("h-battery-section-intact")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            if ">%s<" % health_page.BATTERY_SECTION_HEADING not in rendered:
                return False, "expected BATTERY_SECTION_HEADING inside an <h2>"
            # quick task 260902-gjj (ISSUE 2): retargeted — the badge
            # label this check used to require survived the D-02 move; it
            # is now retired outright, and the card's own status-modifier
            # class is what survives the move instead.
            if "battery-trend-section--ok" not in rendered:
                return False, "expected the battery-trend section's own healthy status modifier to survive the move"
            if health_page.BATTERY_READOUT_ID not in rendered:
                return False, "expected the readout element id to survive the move"
            if rendered.count("<script") != 1:
                return False, "expected exactly one <script occurrence, got %d" % rendered.count("<script")
            if health_page.BATTERY_TREND_SCRIPT_SRC not in rendered:
                return False, "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>"
            # Slice to the battery section's own boundaries (its own
            # matching </section>, not "rest of the page") — the
            # surviving tiles elsewhere on the page (06.6.4.1-04: now
            # including the Server & data section that follows this one)
            # would otherwise make a whole-tail "no stat-tile" search
            # trivially fail. quick task 260902-gjj: retargeted from the
            # exact-literal '<section class="%s">' onto this open-ended
            # prefix — the class attribute now also carries a status
            # modifier, so the closing quote no longer immediately
            # follows BATTERY_SECTION_CLASS.
            section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            section_end = rendered.index("</section>", section_start) + len("</section>")
            section_html = rendered[section_start:section_end]
            if "stat-tile" in section_html:
                return False, "the battery-trend section must carry no stat-tile class"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery-trend section keeps its own status modifier (retargeted from the retired badge, quick "
        "task 260902-gjj), readout, and single script tag after moving out of the grid",
        _battery_section_keeps_everything_after_the_move)

    def _battery_readout_precedes_chart_class_list_and_live_region():
        # quick task 260901-tsa (finding D): the readout is now the
        # section's scannable headline number, ahead of the chart.
        # Slices to the battery-trend section's own boundaries — the
        # same technique _battery_section_keeps_everything_after_the_move()
        # above already uses — rather than the whole page, which also
        # carries icon <svg> instances ahead of the chart (the section
        # heading's own icon-battery glyph, inside this very section).
        tmp = _mkstate("h-battery-readout-position")
        try:
            base = _now()
            readings = [
                (_iso(base - timedelta(minutes=1)), 4200),
                (_iso(base), 4190),
            ]
            _seed_device_health(tmp, readings)
            rendered = health_page.render(_ctx(tmp, now=_iso(base)))
            section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            section_end = rendered.index("</section>", section_start) + len("</section>")
            section_html = rendered[section_start:section_end]

            readout_open = section_html.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
            readout_tag_close = section_html.index(">", readout_open) + 1
            readout_tag = section_html[readout_open:readout_tag_close]
            readout_close = section_html.index("</p>", readout_open) + len("</p>")
            readout_html = section_html[readout_open:readout_close]
            # The sparkline SVG (battery_sparkline_svg()'s own opening) is
            # distinguishable from the section heading's icon-battery
            # <svg class="icon"> by its own '<svg class="sparkline__canvas"'
            # opening — the heading icon carries no such class — so this
            # is what makes "the chart" unambiguous. quick task 260902-ep7
            # (BUG 4): retargeted in place from the retired
            # '<svg viewBox="0 0' marker, which no longer exists now that
            # the chart's <svg> carries no viewBox at all.
            sparkline_at = section_html.index('<svg class="sparkline__canvas"')
            script_at = section_html.index("<script")
            if not (readout_open < sparkline_at < script_at):
                return False, (
                    "expected the readout to precede the sparkline, and the sparkline "
                    "to precede the script tag, inside the battery-trend section")

            # quick task 260901-uzi (finding 3): the readout's class list
            # dropped "mono" (moved onto the new value span) — retargeted
            # onto the new single-class literal, extended with the two
            # spans this task adds.
            if 'class="battery-readout"' not in readout_tag:
                return False, (
                    "expected the readout's class list to be exactly 'battery-readout', got %r"
                    % readout_tag)
            if 'role="status"' not in readout_tag:
                return False, "expected role=\"status\" on the readout"
            if 'battery-readout__value' not in readout_html:
                return False, "expected the readout's value span inside the readout"
            if 'battery-readout__detail' not in readout_html:
                return False, "expected the readout's detail span inside the readout"

            js_path = os.path.join(HERE, "static", "battery-trend.js")
            with open(js_path) as fh:
                js_source = fh.read()
            if health_page.BATTERY_READOUT_ID not in js_source:
                return False, (
                    "expected battery-trend.js to still look up BATTERY_READOUT_ID's literal "
                    "value — that property is what makes the reposition safe")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery readout precedes the chart and the script tag inside the battery-trend section, carries "
        "its single expected class plus role=\"status\" plus both value/detail spans, and battery-trend.js "
        "still looks it up by id (quick task 260901-tsa finding D, retargeted by quick task 260901-uzi "
        "finding 3)",
        _battery_readout_precedes_chart_class_list_and_live_region)

    def _battery_section_class_is_styled_in_stylesheet():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        if health_page.BATTERY_SECTION_CLASS not in css_source:
            return False, "companion/static/style.css no longer styles BATTERY_SECTION_CLASS"
        return True, ""
    check(
        "health_page.BATTERY_SECTION_CLASS is guarded against silent drift from companion/static/style.css",
        _battery_section_class_is_styled_in_stylesheet)

    def _quick_260902_gjj_card_status_borders_render_correct_modifiers():
        # quick task 260902-gjj (ISSUE 2): a real rendered page, with a
        # seeded battery drop (battery_status() -> "error") and a seeded
        # non-empty registry (coverage_status() -> "warn"), proves the
        # battery-trend and Unresolved-prefixes cards each carry the
        # modifier layout.card_status_class() derives from the SAME
        # function that used to drive their now-retired status_dot()
        # badge, and that the Resolution-statistics card carries none.
        # Each section is located by its own heading constant, never a
        # document-wide substring search.
        tmp = _mkstate("h-card-status-borders")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
            ]
            _seed_device_health(tmp, readings)
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 1, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            battery_state = health_page.battery_status([
                {"ts": _iso(now), "battery_mv": readings[1][1]},
                {"ts": _iso(now - timedelta(minutes=1)), "battery_mv": readings[0][1]},
            ])
            if battery_state != "error":
                return False, "expected the seeded battery fixture to compute an error verdict"
            battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
            expected_battery_modifier = layout.card_status_class(
                health_page.BATTERY_SECTION_CLASS, battery_state)
            if expected_battery_modifier not in battery_tag:
                return False, (
                    "expected the battery-trend section's own tag to carry %r, got %r"
                    % (expected_battery_modifier, battery_tag))

            coverage_state = health_page.coverage_status([("ABC", 1, "", "", "")])
            if coverage_state != "warn":
                return False, "expected the seeded registry fixture to compute a warn verdict"
            registry_heading_at = rendered.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
            registry_open = rendered.rindex('<section class="', 0, registry_heading_at)
            registry_tag = rendered[registry_open:rendered.index(">", registry_open) + 1]
            expected_registry_modifier = layout.card_status_class("page-section", coverage_state)
            if expected_registry_modifier not in registry_tag:
                return False, (
                    "expected the Unresolved-prefixes section's own tag to carry %r, got %r"
                    % (expected_registry_modifier, registry_tag))
            if "page-section--nested" not in registry_tag:
                return False, "expected the registry card to keep its pre-existing nested modifier"

            stats_heading_at = rendered.index(">%s</h2>" % health_page.STATS_SECTION_HEADING)
            stats_open = rendered.rindex('<section class="', 0, stats_heading_at)
            stats_tag = rendered[stats_open:rendered.index(">", stats_open) + 1]
            if stats_tag != '<section class="page-section page-section--nested">':
                return False, (
                    "expected the Resolution-statistics card to carry no status modifier "
                    "at all (it computes no verdict), got %r" % stats_tag)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        for comp in ("battery-trend-section", "page-section"):
            for status in ("ok", "warn", "error"):
                sel = ".%s.%s--%s" % (comp, comp, status)
                sel_at = css_source.find(sel)
                if sel_at == -1:
                    return False, "expected the doubled-form status rule %r in style.css" % sel
                body = css_source[css_source.index("{", sel_at):css_source.index("}", sel_at)]
                if "var(--color-status-%s)" % status not in body or "3px" not in body:
                    return False, (
                        "expected %r's rule body to declare a 3px border in var(--color-status-%s), "
                        "got %r" % (sel, status, body))
        return True, ""
    check(
        "the battery-trend and Unresolved-prefixes cards each carry the status modifier "
        "layout.card_status_class() derives from battery_status()/coverage_status()'s own real return "
        "value on the same rows, the Resolution-statistics card carries none, and style.css declares all "
        "three doubled-form status rules for both card components (quick task 260902-gjj, ISSUE 2)",
        _quick_260902_gjj_card_status_borders_render_correct_modifiers)

    # quick task 260902-gjj Task 3 extends this component list with
    # "stat-tile" (its own four modifiers: ok/warn/error/accent, one more
    # than the two page-level cards' three) in place — this stays the one
    # check covering every card-status/hover-vs-status source-order fact
    # in the file, rather than a second near-duplicate check. An in-place
    # strengthening: no count change.
    _CARD_STATUS_HOVER_ORDER_COMPONENTS = (
        ("battery-trend-section", ("ok", "warn", "error")),
        ("page-section", ("ok", "warn", "error")),
        ("stat-tile", ("ok", "warn", "error", "accent")),
    )

    def _card_status_modifiers_survive_hover_source_order():
        # quick task 260902-gjj (ISSUE 2, extended by Task 3 to cover
        # .stat-tile): the load-bearing fact every card-status-border rule
        # depends on — each doubled-form status modifier selector
        # (".COMPONENT.COMPONENT--STATUS") must sit AFTER that
        # component's own ":hover, :focus-within" rule in style.css's
        # source order, or the hover rule's `border-color: transparent`
        # shorthand (equal (0,2,0) specificity, later rule wins) silently
        # erases the status colour the moment the card is hovered or a
        # keyboard user focuses a chart point inside it. Task 3 found
        # this exact defect already latent in `.stat-tile` itself (the
        # rule this pattern was modelled on) and fixed it the same way.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        for comp, statuses in _CARD_STATUS_HOVER_ORDER_COMPONENTS:
            hover_at = css_source.index(".%s:hover" % comp)
            for status in statuses:
                sel = ".%s.%s--%s" % (comp, comp, status)
                sel_at = css_source.index(sel)
                if sel_at <= hover_at:
                    return False, (
                        "%r must come after %r in style.css's source order, or hovering/"
                        "focusing the card erases its status border" % (sel, ".%s:hover" % comp))
        return True, ""
    check(
        "every card-status modifier selector (battery-trend-section, page-section, and — quick task "
        "260902-gjj Task 3 — stat-tile) sits after that component's own :hover/:focus-within rule in "
        "style.css's source order, so the status border survives hover and keyboard focus rather than "
        "losing to the hover shorthand",
        _card_status_modifiers_survive_hover_source_order)

    def _quick_260902_gjj_dot_removal_scoped_not_global():
        # quick task 260902-gjj (ISSUE 2): proves the two dot removals are
        # SCOPED to the battery-trend and Unresolved-prefixes cards, not a
        # global regression that happens to also strip the three
        # surviving Corroboration dots. Without the third (positive)
        # assertion below, the first two (negative) assertions would pass
        # even if status_dot() itself had been broken everywhere — the
        # exact vacuous-pass failure mode this task's own plan warns
        # about.
        tmp = _mkstate("h-dot-removal-scoped")
        try:
            now = _now()
            readings = [
                (_iso(now - timedelta(minutes=1)), 4200),
                (_iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
            ]
            _seed_device_health(tmp, readings)
            _seed_unresolved_prefixes(tmp, {
                "ABC": {"count": 1, "first_seen": _iso(now), "last_seen": _iso(now),
                        "example_callsign": "ABC123"},
            })
            _seed_runway_events(tmp, [{"ts": _iso(now), "hex": "abc123", "corroborated": True}])
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
            battery_close = rendered.index("</section>", battery_open) + len("</section>")
            battery_slice = rendered[battery_open:battery_close]
            if "dot-label" in battery_slice:
                return False, "the battery-trend card must render no dot-label — its own badge is retired"

            registry_heading_at = rendered.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
            registry_open = rendered.rindex('<section class="', 0, registry_heading_at)
            registry_close = rendered.index("</section>", registry_open) + len("</section>")
            registry_slice = rendered[registry_open:registry_close]
            if "dot-label" in registry_slice:
                return False, "the Unresolved-prefixes card must render no dot-label — its own dot is retired"

            corrob_at = rendered.index(">Corroboration<")
            corrob_open = rendered.rindex('<div class="stat-tile ', 0, corrob_at)
            corrob_close = rendered.index("</div>", corrob_open) + len("</div>")
            corrob_slice = rendered[corrob_open:corrob_close]
            if "dot-label" not in corrob_slice:
                return False, (
                    "expected the Corroboration tile's own dots to survive untouched — this check "
                    "must fail if status_dot() itself breaks, not only if the two removals are wrong")

            if hasattr(health_page, "BATTERY_STATUS_LABEL"):
                return False, "expected health_page to no longer define the retired BATTERY_STATUS_LABEL"
            if hasattr(health_page, "_battery_badge_block"):
                return False, "expected health_page to no longer define the retired _battery_badge_block"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the battery-trend and Unresolved-prefixes cards render no dot-label anywhere inside their own "
        "boundaries, the Corroboration tile's three dots survive untouched (proving the removal is scoped, "
        "not global), and BATTERY_STATUS_LABEL/_battery_badge_block are both gone via hasattr, never a "
        "source grep (quick task 260902-gjj, ISSUE 2)",
        _quick_260902_gjj_dot_removal_scoped_not_global)

    def _quick_260901_tsa_css_dom_contract_guard():
        # quick task 260901-tsa (Check 5): the cross-file guard for
        # every new/edited style.css rule this task's markup depends on
        # — the same index()-plus-window-slicing idiom
        # companion/test_config_page.py's own cross-file DOM-contract
        # guard block uses (locate a selector via source.index(...),
        # slice to the next closing brace, assert the expected
        # declaration is inside the slice — never a regex CSS parser).
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        def _rule_body(selector_open):
            start = css_source.index(selector_open)
            brace_close = css_source.index("}", start)
            return css_source[start:brace_close]

        expectations = (
            ('.section-intro {', "display: flex"),
            ('.section-intro > p {', "margin: 0"),
            # quick task 260901-uzi: .stat-tile__value .mono became a
            # two-selector list (.battery-readout .mono joined it), so
            # the literal this guard keys on no longer ends in " {" —
            # retargeted onto the selector's own first line, which
            # _rule_body()'s index()-to-next-"}" slice still resolves to
            # the same rule body.
            ('.stat-tile__value .mono,', "font-weight: inherit"),
            ('.battery-readout {', "font-weight: var(--weight-semibold)"),
        )
        for selector_open, expected_declaration in expectations:
            if selector_open not in css_source:
                return False, "expected style.css to declare %r" % (selector_open,)
            body = _rule_body(selector_open)
            if expected_declaration not in body:
                return False, (
                    "expected %r's rule body to contain %r, got %r"
                    % (selector_open, expected_declaration, body))

        # The one source-order fact the Emphasis promotion actually
        # rests on: moving .battery-readout above .mono in this file
        # would silently return the readout to regular weight, since
        # the promotion wins by SOURCE ORDER (a later same-specificity
        # rule), not by selector specificity.
        if css_source.index(".mono {") >= css_source.index(".battery-readout {"):
            return False, (
                "expected .mono's rule to precede .battery-readout's in style.css — moving "
                ".battery-readout above .mono would silently return the readout to regular weight")
        return True, ""
    check(
        "style.css's .section-intro / .section-intro > p / .stat-tile__value .mono / .battery-readout rules "
        "each carry their load-bearing declaration, and .mono precedes .battery-readout in source order "
        "(quick task 260901-tsa)",
        _quick_260901_tsa_css_dom_contract_guard)

    def _dashboard_grid_stretches_same_row_tiles():
        # quick task 260901-uzi Task 4 (Check 1): finding 1's stylesheet
        # guard. .dashboard-grid must declare the stretch alignment (the
        # UXA-06 reversal) and must not declare the start alignment, and
        # the file's only remaining start-aligned declaration must be the
        # desktop .dashboard-shell rule's own — a different selector D-21's
        # sticky sidebar depends on.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        grid_start = css_source.index(".dashboard-grid {")
        grid_end = css_source.index("}", grid_start)
        grid_body = css_source[grid_start:grid_end]
        if "align-items: stretch" not in grid_body:
            return False, (
                "expected .dashboard-grid to declare align-items: stretch — a "
                "start-aligned .dashboard-grid returns the ragged-height tiles "
                "the developer measured (107.7 / 261.8 / 140.4px in one row)")
        if "align-items: start" in grid_body:
            return False, "expected .dashboard-grid to no longer declare align-items: start"

        start_count = css_source.count("align-items: start")
        if start_count != 1:
            return False, (
                "expected exactly one remaining align-items: start declaration "
                "in the whole file, got %d" % start_count)
        shell_start = css_source.index(".dashboard-shell {")
        shell_end = css_source.index("}", shell_start)
        if "align-items: start" not in css_source[shell_start:shell_end]:
            return False, (
                "expected the one remaining align-items: start to be inside "
                ".dashboard-shell — D-21's sticky sidebar needs it; a different "
                "selector holding it would mean the UXA-06 reversal missed "
                "something")
        return True, ""
    check(
        "style.css's .dashboard-grid declares an explicit cross-axis stretch (the UXA-06 reversal) and no "
        "longer declares start, and .dashboard-shell's own separate start-aligned declaration (D-21's sticky "
        "sidebar) is the file's only remaining one (quick task 260901-uzi finding 1)",
        _dashboard_grid_stretches_same_row_tiles)

    def _data_table_th_has_symmetric_nonzero_padding():
        # quick task 260902-dng (bug 2, closes 260901-uzi Finding 5
        # candidate (a)): pins both halves of the contract so a future
        # edit cannot silently return the top to zero (reintroducing the
        # opaque-background-starts-at-the-glyph-tops defect) or drift the
        # top and bottom values apart (breaking the header's centred
        # optical balance). Parses the declaration rather than
        # string-matching the whole rule body, so this check survives an
        # unrelated reformat of the rule.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()
        rule_match = re.search(r'\.data-table th \{([^}]*)\}', css_source)
        if rule_match is None:
            return False, "expected a `.data-table th { ... }` rule in style.css"
        padding_match = re.search(r'padding:\s*([^;]+);', rule_match.group(1))
        if padding_match is None:
            return False, "expected a `padding` declaration inside `.data-table th`"
        parts = padding_match.group(1).split()
        if len(parts) != 2:
            return False, (
                "expected a two-value (vertical horizontal) padding shorthand, "
                "got %r" % (padding_match.group(1),))
        top_raw, _horizontal = parts
        if not top_raw.endswith("px") or not top_raw[:-2].isdigit():
            return False, "expected the top/bottom padding value to be a bare px literal, got %r" % top_raw
        top_px = int(top_raw[:-2])
        if top_px <= 0:
            return False, (
                "expected a non-zero top padding on .data-table th — zero top "
                "padding is the real mechanism behind the sticky header's "
                "opaque background starting exactly at the glyph tops")
        # The two-value shorthand `padding: Npx Mpx` applies Npx to both
        # top AND bottom, so parsing one value already proves symmetry —
        # this assertion protects against a future rewrite to the
        # four-value form (`padding: T R B L`) silently reintroducing an
        # asymmetric top/bottom split without this check's knowledge.
        if "padding:" not in rule_match.group(1) or len(re.findall(r'padding-top|padding-bottom', rule_match.group(1))) > 0:
            return False, "expected the two-value shorthand form, not separate padding-top/padding-bottom declarations"
        return True, ""
    check(
        "style.css's .data-table th declares a symmetric, non-zero vertical padding via the two-value shorthand "
        "(quick task 260902-dng bug 2, closes 260901-uzi Finding 5 candidate (a))",
        _data_table_th_has_symmetric_nonzero_padding)

    def _nested_heading_tier_reverted_to_standard_heading_role():
        # quick task 260901-uzi Task 4 (Check 2): finding 4's markup half
        # (exactly the two migrated cards carry page-section--nested,
        # located from each card's own heading constant rather than a
        # first-occurrence index; the source-fault block never carries it,
        # even when it renders; both .section-intro headings are
        # untouched) — UNCHANGED, this half is still true.
        #
        # quick task 260902-iag retargets the stylesheet half IN PLACE:
        # the rule this check inspects no longer demotes the nested tier
        # (the developer's explicit, same-day reversal of the demotion
        # this check used to pin — see the rule's own comment in
        # style.css). It now asserts the opposite: the rule declares no
        # font-size, no font-weight and (still) no font-family of its
        # own, and it still declares the retained 260902-bl2 bottom
        # margin. A positive half is added so the check stays meaningful
        # after the reversal: `.text-heading` itself must still declare
        # the 20px heading size and the regular weight this tier now
        # inherits, and `--font-heading-size` must still be 20px in
        # :root — so this check fails loudly if the treatment the nested
        # tier now relies on ever moves out from under it.
        tmp = _mkstate("h-nested-heading-tier")
        try:
            now = _now()
            _seed_device_health(tmp, [(_iso(now), 4200)])
            _seed_meta(tmp, **{history_db.META_SOURCE_FAULT: "True"})
            rendered = health_page.render(_ctx(tmp, now=_iso(now)))

            if rendered.count("page-section--nested") != 2:
                return False, (
                    "expected exactly two page-section--nested occurrences "
                    "(the two migrated cards), got %d" % rendered.count("page-section--nested"))

            for heading in (health_page.UNRESOLVED_SECTION_HEADING, health_page.STATS_SECTION_HEADING):
                heading_marker = ">%s</h2>" % heading
                heading_at = rendered.index(heading_marker)
                section_open = rendered.rindex('<section class="', 0, heading_at)
                section_tag = rendered[section_open:rendered.index(">", section_open) + 1]
                if "page-section--nested" not in section_tag:
                    return False, (
                        "expected the <section> carrying %r to declare "
                        "page-section--nested, got %r" % (heading, section_tag))

            if '<section class="page-section banner banner--anomaly">' not in rendered:
                return False, "expected the source-fault block itself to render for this fixture"
            if 'class="page-section banner banner--anomaly page-section--nested"' in rendered:
                return False, "the source-fault block must never carry page-section--nested"

            for section_id, heading in (
                    (health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING),
                    (health_page.SERVER_DATA_SECTION_ID, health_page.SERVER_DATA_SECTION_HEADING)):
                intro_marker = '<h2 id="%s" class="text-heading">%s</h2>' % (
                    section_id, layout.escape_html(heading))
                if intro_marker not in rendered:
                    return False, "expected %r's own .section-intro heading to be unmodified" % heading

            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css_source = fh.read()
            selector_at = css_source.index(".page-section--nested > h2,")
            body_open = css_source.index("{", selector_at)
            body_close = css_source.index("}", body_open)
            selector_list = css_source[selector_at:body_open]
            nested_body = css_source[body_open:body_close]
            if ".battery-trend-section > h2" not in selector_list:
                return False, "expected the reverted rule's selector list to still cover .battery-trend-section > h2"
            if "margin-bottom: var(--space-md)" not in nested_body:
                return False, (
                    "expected the reverted rule to still declare its retained 260902-bl2 bottom "
                    "margin — a missing bottom margin means the revert over-reached and took the "
                    "independently-justified spacing fix with it")
            if "font-size" in nested_body:
                return False, (
                    "the reverted rule must declare no font-size of its own — a font-size "
                    "reappearing here is the 260901-uzi demotion returning")
            if "font-weight" in nested_body:
                return False, (
                    "the reverted rule must declare no font-weight of its own — a font-weight "
                    "reappearing here is the 260901-uzi demotion returning")
            if "font-family" in nested_body:
                return False, (
                    "the reverted rule must set no font family — .text-heading already "
                    "supplies the serif treatment")

            heading_body = css_source[css_source.index(".text-heading {"):]
            heading_body = heading_body[heading_body.index("{"):heading_body.index("}")]
            if "font-size: var(--font-heading-size)" not in heading_body:
                return False, (
                    "expected .text-heading to still declare --font-heading-size — the reverted "
                    "nested tier now inherits this treatment and has no fallback of its own")
            if "font-weight: var(--weight-regular)" not in heading_body:
                return False, (
                    "expected .text-heading to still declare --weight-regular — the reverted "
                    "nested tier now inherits this treatment and has no fallback of its own")
            root_body = css_source[css_source.index(":root"):css_source.index(":root") + 900]
            token_match = re.search(r"--font-heading-size:\s*(\S+);", root_body)
            if token_match is None or token_match.group(1) != "20px":
                return False, (
                    "expected --font-heading-size to still be 20px in :root — the value the "
                    "developer's Settings comparison and this reversal both depend on")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "exactly the two migrated cards carry page-section--nested (located by their own heading constants), "
        "the source-fault block never carries it even when it renders, both .section-intro headings are "
        "untouched, and style.css's nested-heading rule — reverted by quick task 260902-iag — declares no "
        "font-size, no font-weight and no font-family of its own (only its retained 260902-bl2 bottom margin), "
        "inheriting .text-heading's 20px regular treatment, which the check confirms is still 20px/regular at "
        "the token level too (quick task 260901-uzi finding 4, Check 2; reverted in place by quick task "
        "260902-iag)",
        _nested_heading_tier_reverted_to_standard_heading_role)

    def _stat_tile_caption_weight_reverted_and_four_role_scale_hold():
        # SUPERSEDED (quick task 260902-dng, Task 3): this check used to
        # pin .stat-tile__caption declaring --weight-semibold, and the
        # region's four text roles sharing a caption/value/nested-title
        # semibold trio below one regular-weight section heading. quick
        # task 260902-iag rewrote this check's whole contract in place —
        # not just the assertions — because 260901-uzi's finding 4 (the
        # nested card title's 16px semibold demotion) was itself reverted
        # by quick task 260902-iag Task 1, and 260902-dng's promotion's
        # only stated reason was matching that now-reverted title. Task 2
        # re-adjudicated the promotion against both a premise test and an
        # inversion test (see .stat-tile__caption's own comment in
        # style.css for the full reasoning) and reverted it: the caption
        # is back to the plain Label role it held before 260902-dng.
        #
        # This check's post-reversal contract: the four roles' sizes
        # still form a coherent, source-grounded set against the real
        # :root token values (caption 14px, strictly below the tile value
        # and the nested card title at 16px and 20px respectively, both
        # at or below the 20px section heading — no fifth size anywhere);
        # the caption declares no size of its own and keeps its named
        # serif exception; the tile value keeps its own D-09 Emphasis-role
        # size and weight, untouched by this adjudication; the nested
        # card title and the section heading both declare regular weight
        # or inherit it with no override; and the caption declares no
        # font-weight of its own either, inheriting .text-label's
        # regular weight — the verdict Task 2 shipped, asserted
        # explicitly in that direction.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        def _rule_body(selector_needle):
            selector_at = css_source.index(selector_needle)
            body_open = css_source.index("{", selector_at)
            body_close = css_source.index("}", body_open)
            return css_source[body_open:body_close]

        caption_body = _rule_body(".stat-tile__caption {")
        if "font-weight" in caption_body:
            return False, (
                "expected .stat-tile__caption to declare no font-weight of its own — quick "
                "task 260902-iag Task 2 reverted the semibold promotion back to .text-label's "
                "inherited regular weight; a font-weight reappearing here is that promotion "
                "returning without the fresh, non-circular justification the revert requires")
        if "font-size" in caption_body:
            return False, (
                "expected .stat-tile__caption to declare no font-size of its own "
                "(it must keep inheriting .text-label's 14px) — a fifth size "
                "would violate D-09's four-size scale")
        if "var(--font-serif)" not in caption_body:
            return False, "expected .stat-tile__caption to keep its named serif exception"

        value_body = _rule_body(".stat-tile__value {")
        if "font-size: var(--font-body-size)" not in value_body:
            return False, "expected .stat-tile__value to stay on the Body size (16px) — Finding 4's own contract"
        if "font-weight: var(--weight-semibold)" not in value_body:
            return False, "expected .stat-tile__value to stay semibold — Finding 4's own contract"

        # quick task 260902-iag Task 1: the nested card title's demotion
        # was reverted, so it now inherits 20px regular from
        # .text-heading and declares neither a font-size nor a
        # font-weight of its own.
        nested_body = _rule_body(".page-section--nested > h2,")
        if "font-size" in nested_body:
            return False, (
                "expected the nested card title to declare no font-size of its own — it now "
                "inherits .text-heading's 20px (quick task 260902-iag reverted the demotion)")
        if "font-weight" in nested_body:
            return False, (
                "expected the nested card title to declare no font-weight of its own — it now "
                "inherits .text-heading's regular weight (quick task 260902-iag reverted the demotion)")

        heading_body = _rule_body("h1,\nh2,\nh3,\nlegend,\n.text-heading {")
        if "font-weight: var(--weight-regular)" not in heading_body:
            return False, (
                "expected the h1/h2/h3/legend/.text-heading rule to stay regular weight — "
                "the section heading and the reverted nested card title both inherit this, "
                "and neither should ever carry its own weight override again")

        # Token values themselves, so this check fails loudly (not
        # silently) if a future edit changes what 14/16/20 actually mean.
        tokens_body = css_source[css_source.index(":root"):css_source.index(":root") + 800]
        for name, expected in (
                ("--font-label-size", "14px"),
                ("--font-body-size", "16px"),
                ("--font-heading-size", "20px")):
            token_match = re.search(r"%s:\s*(\S+);" % re.escape(name), tokens_body)
            if token_match is None or token_match.group(1) != expected:
                return False, "expected %s to be %s in :root" % (name, expected)

        return True, ""
    check(
        "style.css's four Server & data text roles form a coherent, source-grounded set after both the nested "
        "card title's reversal and the stat-tile caption's re-adjudication (quick task 260902-iag): the caption "
        "(14px, no font-size or font-weight of its own, keeping its named serif exception) declares no weight "
        "promotion — reverted back to .text-label's inherited regular, since its only stated reason (matching "
        "the now-reverted 16px-semibold nested title) evaporated and would otherwise recreate the same weight-"
        "vs-size inversion this session has repeatedly fixed — while .stat-tile__value keeps its own untouched "
        "D-09 Emphasis-role size/weight, and both the nested card title and the section heading inherit "
        ".text-heading's 20px regular treatment with no override (quick task 260902-dng Task 3, whose promotion "
        "and reasoning are superseded, not deleted, by quick task 260902-iag Task 2)",
        _stat_tile_caption_weight_reverted_and_four_role_scale_hold)

    def _two_tier_hierarchy_carried_by_layout_not_type():
        # quick task 260902-iag Task 3: with font-size no longer
        # distinguishing Health's two structural tiers (D-10's section
        # headings vs. the cards nested inside them), this check pins the
        # mechanism that replaced it — containment and spacing, read from
        # the real rendered DOM and the real cascade, not asserted from
        # memory. A failure here means the two tiers may have stopped
        # reading apart, not merely that a number moved.
        #
        # Markup half, both empty and seeded: every level-2 heading
        # (Battery trend, Unresolved prefixes, Resolution statistics) is
        # the child of a <section> carrying a card class (the nested
        # modifier or the battery-trend class); both level-1 headings
        # (Screen, Server & data) are inside the plain .section-intro row
        # and carry no card class at all. Every heading is located from
        # its own module constant, never a positional index.
        for seeded in (False, True):
            tmp = _mkstate("h-two-tier-hierarchy-%s" % seeded)
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

                for section_id, heading in (
                        (health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING),
                        (health_page.SERVER_DATA_SECTION_ID, health_page.SERVER_DATA_SECTION_HEADING)):
                    marker = '<h2 id="%s" class="text-heading">%s</h2>' % (
                        section_id, layout.escape_html(heading))
                    marker_at = rendered.index(marker)
                    wrapper_open = rendered.rindex("<div class=\"", 0, marker_at)
                    wrapper_tag = rendered[wrapper_open:rendered.index(">", wrapper_open) + 1]
                    if "section-intro" not in wrapper_tag:
                        return False, (
                            "seeded=%s: expected %r's <h2> to sit inside the plain "
                            ".section-intro row, got wrapper %r" % (seeded, heading, wrapper_tag))
                    if "page-section" in wrapper_tag or "battery-trend-section" in wrapper_tag:
                        return False, (
                            "seeded=%s: %r's own wrapper must carry no card class, got %r"
                            % (seeded, heading, wrapper_tag))

                for heading in (
                        health_page.BATTERY_SECTION_HEADING,
                        health_page.UNRESOLVED_SECTION_HEADING,
                        health_page.STATS_SECTION_HEADING):
                    heading_marker_at = rendered.index(">%s" % heading)
                    section_open = rendered.rindex("<section class=\"", 0, heading_marker_at)
                    section_tag = rendered[section_open:rendered.index(">", section_open) + 1]
                    if not (
                            "page-section--nested" in section_tag
                            or health_page.BATTERY_SECTION_CLASS in section_tag):
                        return False, (
                            "seeded=%s: expected %r's enclosing <section> to carry a card "
                            "class (page-section--nested or %s), got %r"
                            % (seeded, heading, health_page.BATTERY_SECTION_CLASS, section_tag))

                # Adjacency: a .dashboard-grid always sits between a
                # level-1 heading's own .section-intro row and the first
                # level-2 card in that same section — the two tiers are
                # never immediately adjacent on screen.
                screen_intro_at = rendered.index('id="%s"' % health_page.SCREEN_SECTION_ID)
                screen_intro_close = rendered.index("</div>", screen_intro_at) + len("</div>")
                after_screen_intro = rendered[screen_intro_close:screen_intro_close + 40]
                if not after_screen_intro.startswith('<div class="dashboard-grid">'):
                    return False, (
                        "seeded=%s: expected a .dashboard-grid immediately after the Screen "
                        "section-intro row, got %r" % (seeded, after_screen_intro))
                server_intro_at = rendered.index('id="%s"' % health_page.SERVER_DATA_SECTION_ID)
                server_intro_close = rendered.index("</div>", server_intro_at) + len("</div>")
                after_server_intro = rendered[server_intro_close:server_intro_close + 40]
                if not after_server_intro.startswith('<div class="dashboard-grid">'):
                    return False, (
                        "seeded=%s: expected a .dashboard-grid immediately after the Server & "
                        "data section-intro row, got %r" % (seeded, after_server_intro))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        # Stylesheet half: the four spacing values that now carry the
        # hierarchy, read from their own rules by selector and asserted
        # to form the strictly ordered set the layout inspection derived
        # — section-transition > same-section card-to-card > heading-to-
        # content inside a card > a section-intro heading's own rhythm —
        # against :root's real token values, so a future edit that
        # flattens any one of them fails here instead of silently
        # dissolving the distinction that replaced font-size.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        def _decl_px(selector_needle, prop):
            selector_at = css_source.index(selector_needle)
            body_open = css_source.index("{", selector_at)
            body_close = css_source.index("}", body_open)
            body = css_source[body_open:body_close]
            # Matches both a bare `prop: var(--token);` declaration and a
            # shorthand form with leading values before the var(), e.g.
            # the heading-rhythm rule's `margin: 0 0 var(--space-sm);` —
            # in the shorthand case this captures the LAST var() in the
            # declaration, which is the bottom-margin component both
            # `margin: 0 0 var(...)` and this rule's own longhand usage
            # agree on.
            m = re.search(r"%s:\s*[^;]*?var\(--([a-z0-9-]+)\)[^;]*;" % re.escape(prop), body)
            if m is None:
                return None, None
            token_name = "--" + m.group(1)
            root_body = css_source[css_source.index(":root"):css_source.index(":root") + 900]
            token_match = re.search(r"%s:\s*(\d+)px;" % re.escape(token_name), root_body)
            if token_match is None:
                return token_name, None
            return token_name, int(token_match.group(1))

        section_token, section_gap = _decl_px(".battery-trend-section {", "margin-bottom")
        card_token, card_gap = _decl_px(".page-section {", "margin-bottom")
        grid_token, grid_gap = _decl_px(".dashboard-grid {", "margin-bottom")
        head_token, head_gap = _decl_px(".page-section--nested > h2,", "margin-bottom")
        intro_token, intro_gap = _decl_px("h1,\nh2,\nh3,\n.text-heading {", "margin")

        if None in (section_gap, card_gap, grid_gap, head_gap, intro_gap):
            return False, (
                "expected all four spacing rules (.battery-trend-section, .page-section, "
                ".dashboard-grid, .page-section--nested > h2, the heading-rhythm rule) to "
                "resolve to real px token values, got tokens %r"
                % ((section_token, card_token, grid_token, head_token, intro_token),))
        if card_gap != grid_gap:
            return False, (
                "expected .page-section and .dashboard-grid to share one same-section "
                "card-to-card value (%s=%dpx vs %s=%dpx) — the pair 260902-ep7 pinned"
                % (card_token, card_gap, grid_token, grid_gap))
        if not (section_gap > card_gap > head_gap > intro_gap):
            return False, (
                "expected the layout hierarchy's four spacing tiers to stay strictly ordered "
                "(section-transition %dpx > card-to-card %dpx > heading-to-content %dpx > "
                "section-intro rhythm %dpx) — this ordering is what now carries the two-tier "
                "hierarchy quick task 260902-iag removed the type-scale distinction from"
                % (section_gap, card_gap, head_gap, intro_gap))
        return True, ""
    check(
        "Health's two-tier hierarchy (D-10 section headings vs. the cards nested inside them) still reads "
        "apart with no font-size or font-weight distinction between the tiers: every level-2 heading (Battery "
        "trend, Unresolved prefixes, Resolution statistics) sits inside a bordered card <section>, both level-1 "
        "headings (Screen, Server & data) sit inside the plain .section-intro row with no card class, a "
        ".dashboard-grid always intervenes between a level-1 heading and the first level-2 card in its own "
        "section, and the four spacing tiers that now carry the distinction stay strictly ordered against "
        "their real :root token values — in both the empty and seeded state (quick task 260902-iag Task 3)",
        _two_tier_hierarchy_carried_by_layout_not_type)

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
        allowed = (
            '<p class="text-body">', '<p class="text-body section-caption">',
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
                for heading in (
                        health_page.BATTERY_SECTION_HEADING,
                        health_page.UNRESOLVED_SECTION_HEADING,
                        health_page.STATS_SECTION_HEADING):
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
            readings_at = rendered.index(health_page.BATTERY_SECTION_HEADING)
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
            battery_at = rendered.index(health_page.BATTERY_SECTION_HEADING)
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

            for prefix, count, first_seen, last_seen, example_callsign in rows:
                first_html = layout.concise_timestamp_html(first_seen, now_iso, fallback="")
                last_html = layout.concise_timestamp_html(last_seen, now_iso, fallback="")
                if rendered.count(first_html) != 2:
                    return False, (
                        "expected First seen markup %r byte-identical in both representations (found "
                        "%d occurrences, want 2)" % (first_html, rendered.count(first_html)))
                if rendered.count(last_html) != 2:
                    return False, (
                        "expected Last seen markup %r byte-identical in both representations (found "
                        "%d occurrences, want 2)" % (last_html, rendered.count(last_html)))
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
        "(data-filter-text, data-filter-group), byte-identical on First/Last seen timestamp markup, "
        "positioned between the filter bar and the table wrap, and every column (prefix, count, both "
        "timestamps, example callsign) is reachable in the card slice (quick task 260903-ghy Task 2, "
        "Check C / UIR-11)",
        _registry_mobile_cards_paired_with_table)

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
            stats_at = rendered_empty.index(">%s</h2>" % health_page.STATS_SECTION_HEADING)
            section_slice = rendered_empty[unresolved_at:stats_at]
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
        # (the readout's id/role/spans, the humanised visible detail, the
        # machine-precise tooltip) plus the cross-file half (every chart
        # hit target carries data-when, and battery-trend.js's shipped
        # source reads that attribute name, both span class names, and
        # still looks the readout up by its id literal) — a server-side
        # format change the script does not read is the exact regression
        # this check exists to catch.
        tmp = _mkstate("h-humanised-readout-e2e")
        try:
            base = _now()
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
            visible = re.sub(r"<[^>]*>", "", readout_html)
            if re.search(r"\d{4}-\d{2}-\d{2}T", visible):
                return False, "expected no raw ISO string in the readout's visible text, got %r" % visible
            if not re.search(r"\d{4}-\d{2}-\d{2}T", readout_html):
                return False, "expected the machine-precise ISO to survive in the detail span's title tooltip"

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
            stale_device, [(_ago(health_page.STALE_DEVICE_ERROR_S + 60), 4000)])
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

    def _anomaly_active_never_raises_on_hostile_inputs():
        # anomaly_active() runs on every authenticated page render via
        # page_context() (companion/app.py) — it may never fault a page
        # that has nothing to do with Health. Precedent:
        # runway_images_available() (Phase 06.4)'s own never-raises
        # contract for the same reason.
        #
        # Three of the four hostile inputs below make the database
        # itself unopenable, which _safe_query() maps to _DB_UNAVAILABLE
        # for every read — and every section builder's _DB_UNAVAILABLE
        # branch returns state "ok", so collect_anomalies() correctly
        # returns False for all three. A genuinely empty-but-writable
        # directory is different: open_db() succeeds there (it creates
        # the schema), so Device/Pipeline legitimately read as "warn"
        # (D-12's documented "never seen" default) — the same "warn" a
        # freshly-provisioned deployment already shows on the page via
        # render() itself (confirmed by direct execution: render()
        # already shows ANOMALY_BANNER_TEXT for a truly empty state_dir,
        # unrelated to and predating this plan). That case is asserted
        # for "does not raise" and "agrees with render()", not for a
        # specific boolean value.
        if health_page.anomaly_active("/nonexistent/definitely-not-here") is not False:
            return False, "expected False for a non-existent state_dir path"

        empty = tempfile.mkdtemp(prefix="skypane-status-pages-anomaly-empty-")
        try:
            empty_verdict = health_page.anomaly_active(empty)
            if not isinstance(empty_verdict, bool):
                return False, "expected a bool (no raise) for an empty temporary directory, got %r" % (empty_verdict,)
            rendered = health_page.render(_ctx(empty))
            if empty_verdict != (health_page.ANOMALY_BANNER_TEXT in rendered):
                return False, "anomaly_active() disagreed with render()'s banner for an empty directory"
            with history_db.open_db(empty):
                pass
            dbs = [f for f in os.listdir(empty) if f.endswith(".db")]
            if not dbs:
                return False, "expected a database file to have been created"
            with open(os.path.join(empty, dbs[0]), "wb") as fh:
                fh.write(b"not a sqlite file at all")
            if health_page.anomaly_active(empty) is not False:
                return False, "expected False for a corrupt database, not a raise"
        finally:
            shutil.rmtree(empty, ignore_errors=True)

        fd, path = tempfile.mkstemp(prefix="skypane-status-pages-anomaly-file-")
        os.close(fd)
        try:
            if health_page.anomaly_active(path) is not False:
                return False, "expected False for a state_dir that is a regular file, not a directory"
        finally:
            os.unlink(path)
        return True, ""
    check(
        "anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely",
        _anomaly_active_never_raises_on_hostile_inputs)

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
            if '<table class="data-table">' not in rendered:
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

        def _headings_carry_no_glyph(rendered, context_label):
            heads = re.findall(r"<h2\b.*?</h2>", rendered, re.S)
            if len(heads) != 5:
                return "expected Health (%s) to still render five headings, got %d" % (context_label, len(heads))
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
            failure = _headings_carry_no_glyph(empty_rendered, "empty render")
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
            failure = _headings_carry_no_glyph(seeded_rendered, "seeded render")
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
        if "location.reload()" not in js:
            return False, "expected the no-argument location.reload() form"

        # test_config_page.py's own _FORBIDDEN_SCRIPT_SINKS tuple,
        # copied here (not imported — it is a function-local inside that
        # harness's main()) from the real source read at plan time. If
        # that tuple's membership ever changes, this copy needs updating
        # too.
        forbidden_sinks = (
            "innerHTML", "outerHTML", "insertAdjacentHTML",
            "document.write", "eval(", "fetch(", "XMLHttpRequest",
        )
        for sink in forbidden_sinks:
            if sink in js:
                return False, "forbidden sink discipline broken: %r found in freshness.js" % sink
        for nav in ("location.href =", "location.assign", "location.replace"):
            if nav in js:
                return False, "URL-taking navigation form found in freshness.js: %r" % nav

        # The ES5-safe-subset portion of test_companion_app.py's own
        # nav-dropdown.js/panel-lookup.js `banned` tuples, copied here
        # (not imported, same reason as forbidden_sinks above) from the
        # real source read at plan time.
        for token in ("let ", "const ", "=>", "`"):
            if token in js:
                return False, "ES5-safe subset broken: %r found in freshness.js" % token

        # Deliberate asymmetry, and the whole point of this task: unlike
        # the sibling nav-dropdown.js/panel-lookup.js guards, setTimeout
        # and setInterval must NOT be banned here — the timer ban is the
        # ONLY discipline this task lifts on this file, and both timers
        # must actually be present for the loop to exist at all.
        for timer in ("setTimeout", "setInterval"):
            if timer not in js:
                return False, (
                    "expected %r to be present — this task deliberately lifts the timer ban this "
                    "file used to carry, the only discipline it lifts" % timer)
        return True, ""
    check(
        "freshness.js's shipped source carries the loop's own contract — a named interval constant "
        "inside the 30-60s band, both halves of pause (setInterval+clearInterval) and visibility "
        "(visibilitychange+document.hidden), the double-start guard, and the no-argument reload form — "
        "while every pre-existing discipline except the timer ban (forbidden sinks, no URL-taking "
        "navigation form, the ES5-safe subset) still holds; the timer ban is the ONLY thing this task "
        "lifted",
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
        # UIR-18: a persistent, server-rendered liveness note joins the
        # existing hidden refresh pill inside ONE block-level wrapper —
        # the anonymous-block-box guard from 260902-ep7 (BUG 1). Pins the
        # structural contract (the wrapper is the .page-header's next
        # child right after the <h1>, and the pill's own markup is
        # untouched inside it), not just the note's text.
        tmp = _mkstate("h-persistent-freshness")
        try:
            now_iso = _iso(_now())
            rendered = health_page.render(_ctx(tmp, now=now_iso))

            expected_note = layout.concise_timestamp_html(now_iso, now_iso)
            if expected_note not in rendered:
                return False, (
                    "expected the persistent note to render "
                    "concise_timestamp_html(now, now) byte-identically")
            prefix = layout.escape_html(health_page.PERSISTENT_FRESHNESS_PREFIX_TEXT)
            if prefix not in rendered:
                return False, "expected the persistent note's prefix text in the rendered page"

            if '<p class="page-header__freshness' not in rendered:
                return False, "expected a block-level .page-header__freshness wrapper"
            wrapper_start = rendered.index('<p class="page-header__freshness')
            wrapper_end = rendered.index("</p>", wrapper_start) + len("</p>")
            wrapper_slice = rendered[wrapper_start:wrapper_end]
            if "data-refresh-pill" not in wrapper_slice:
                return False, "expected the hidden refresh pill inside the freshness wrapper"
            if expected_note not in wrapper_slice:
                return False, "expected the persistent note inside the same freshness wrapper as the pill"

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
        "Health's header renders a persistent server-rendered liveness note beside the "
        "unchanged hidden refresh pill, both inside one block-level .page-header__freshness "
        "wrapper that is the .page-header's next child right after the <h1> (quick task "
        "260903-peo, UIR-18)",
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
        # aspect-ratio.
        image_start = css_source.index(".airline-card__image {")
        image_body = css_source[image_start:css_source.index("}", image_start)]
        if "height: auto" not in image_body:
            return False, "expected .airline-card__image to declare height: auto (UIR-07)"
        if "aspect-ratio: 900 / 263" not in image_body:
            return False, "expected .airline-card__image to still declare its aspect-ratio (UIR-07)"

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

        # UIR-12 markup half: the Battery trend caption span opens with a
        # space before its em dash.
        tmp2 = _mkstate("h-v2v-em-dash")
        try:
            rendered2 = health_page.render(_ctx(tmp2))
            if 'section-caption"> — ' not in rendered2:
                return False, (
                    "expected the Battery trend caption span to open with a space before its "
                    "em dash (UIR-12)")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        return True, ""
    check(
        "the four UIR-03/07/12/13 one-line fixes hold together: .banner wraps with a nowrap "
        ".banner__label rendered on the anomaly banner's lead span, .banner__pill gains min-width: 0 "
        "while keeping flex: none and its source position before .refresh-pill, .airline-card__image "
        "gains height: auto alongside its surviving aspect-ratio, the .data-table--prose first-column "
        "nowrap rule exists after the base rule, and the rendered Battery trend heading carries a space "
        "before its em dash (quick task 260902-v2v)",
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
        # page simply begins reloading out from under a user
        # mid-interaction — so this is the only thing that would notice.
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
        if "details[open]" not in js:
            return False, "freshness.js no longer checks for an open <details> disclosure"
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
        "checks for an open <details>, a focused INPUT/SUMMARY, and health_page.SPARKLINE_HIT_CLASS's "
        "own literal value — this guard's failure mode is silence, so this check is the only thing "
        "that would notice a drift",
        _quick_260902_chc_skip_guard_cross_file_contract)

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

    def _all_43_normalized_outputs_share_identical_pixel_dimensions():
        if len(_VENDORED_ILLUSTRATION_PATHS) != 43:
            return False, "expected 43 vendored illustration files, got %d" % len(_VENDORED_ILLUSTRATION_PATHS)
        for path in _VENDORED_ILLUSTRATION_PATHS:
            png_bytes = illustration_normalize.normalized_png_bytes(path)
            with Image.open(io.BytesIO(png_bytes)) as out:
                if out.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                    return False, "%s normalized to %r, expected %r" % (
                        os.path.basename(path), out.size, illustration_normalize.ILLUSTRATION_TARGET_SIZE)
        return True, ""
    check(
        "all 43 vendored illustrations normalize to the exact same pixel dimensions "
        "(illustration_normalize.ILLUSTRATION_TARGET_SIZE)",
        _all_43_normalized_outputs_share_identical_pixel_dimensions)

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
        "all 43 vendored illustrations normalize with their painted content centred within 1px on both "
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
        "(27 against today's data)",
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
            if airlines_page._FILTER_INPUT_ID != "airlines-gallery-filter-input":
                return False, "expected the UI-SPEC-pinned input id, got %r" % (airlines_page._FILTER_INPUT_ID,)
            expected_label = '<label class="text-label" for="%s">' % airlines_page._FILTER_INPUT_ID
            if expected_label not in rendered:
                return False, "expected the filter label's for= to equal the search input's id"
            if '<input type="search" id="%s" data-filter-input>' % airlines_page._FILTER_INPUT_ID not in rendered:
                return False, "expected the search input to carry the same id"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the gallery filter label's for attribute equals the search input's id, and that id is the "
        "UI-SPEC-pinned value",
        _gallery_filter_label_for_matches_input_id)

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
        "the gallery filter bar's count text and empty-state body both name the real (27) card total",
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

    def _airlines_page_source_has_no_history_db_poll_loop_or_sqlite_import():
        # D-17 non-goal: the gallery shows the full static curated list
        # and performs no detection-history cross-reference — the page
        # module opens no database and reads no poll state.
        with open(os.path.join(HERE, "pages", "airlines_page.py")) as fh:
            source = fh.read()
        for needle in ("history_db", "poll_loop", "import sqlite3"):
            if needle in source:
                return False, "airlines_page.py must not import %r (D-17 non-goal)" % needle
        return True, ""
    check(
        "companion/pages/airlines_page.py imports no history-database module, no poll-state module, and no "
        "sqlite module (D-17 non-goal: no detection-history cross-reference)",
        _airlines_page_source_has_no_history_db_poll_loop_or_sqlite_import)

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
            expected = len(illustrations.target_airline_names())
            if len(actions) != expected:
                return False, "expected %d replace-action triggers (one per target airline), got %d" % (
                    expected, len(actions))
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
        # contract: now exactly one file input on the whole page, whose
        # id is the static REPLACE_INPUT_ID. quick task 260903-df3
        # extends this further: the label and the file input must both
        # live *inside* the framed zone wrapper, so a future change that
        # lifts either back out of the frame fails loudly here rather
        # than silently.
        tmp = _mkstate("a-replace-input-ids")
        try:
            rendered = airlines_page.render(_ctx(tmp))
            input_ids = re.findall(r'<input type="file" id="([^"]+)"', rendered)
            if len(input_ids) != 1:
                return False, "expected exactly one file input, got %d" % len(input_ids)
            if input_ids[0] != airlines_page.REPLACE_INPUT_ID:
                return False, "expected the file input's id to equal REPLACE_INPUT_ID, got %r" % (input_ids[0],)
            label_fors = set(re.findall(r'<label for="([^"]+)">', rendered))
            if input_ids[0] not in label_fors:
                return False, "expected a <label for=\"%s\"> matching the file input's id" % (input_ids[0],)
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
        "the whole rendered page carries exactly one <input type=\"file\">, whose id equals "
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
            rendered = airlines_page.render(_ctx(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        use_tag = "<use href=" + '"#icon-upload"'
        if rendered.count(use_tag) != 1:
            return False, "expected exactly one %r in the rendered page, got %d" % (
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
                    ("/history", "History")):
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
                    if body_text.count('action=""') != 1:
                        return False, (
                            "expected action=\"\" exactly once in the real /airlines HTTP response body, "
                            "got %d" % body_text.count('action=""'))
                    if body_text.count('<input type="file"') != 1:
                        return False, (
                            "expected <input type=\"file\" exactly once in the real /airlines HTTP response "
                            "body, got %d" % body_text.count('<input type="file"'))

                elif path == "/history":
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
            js_status, _js_headers, js_body = http_request(
                base + app.FRESHNESS_SCRIPT_ROUTE, cookie=session_cookie)
            if js_status != 200:
                return False, "expected 200 for %s, got %d" % (app.FRESHNESS_SCRIPT_ROUTE, js_status)
            js_text = js_body.decode("utf-8", errors="replace")
            for needle, label in (
                    ("AUTO_REFRESH_INTERVAL_MS", "the named interval constant"),
                    ("visibilitychange", "the visibility-change listener registration")):
                if needle not in js_text:
                    return False, (
                        "expected %s (%r) in the real %s response body"
                        % (label, needle, app.FRESHNESS_SCRIPT_ROUTE))
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
            "carries the interval constant and the visibility-change listener (quick task 260901-tsa; "
            "extended in place by quick task 260901-uzi finding 1/2/3/4, quick task 260902-bl2 Task 3, quick "
            "task 260902-chc, and quick task 260903-btu Task 5a)",
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
