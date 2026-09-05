#!/usr/bin/env python3
"""Contract harness for companion/pages/config_page.py — CFG-01's theme
picker, CFG-12's runway picker, and CFG-07's manual poll-trigger control
(06-CONTEXT.md).

Covers: render() emitting both fieldsets from server.device_config's own
registries with the current values pre-selected, both helper texts
appearing escaped-verbatim, the poll-trigger button's enabled/disabled
states, handle_post()'s server-side membership-test validation (a
non-member theme or runway writes nothing and reports the save-failure
flash key, a partial-field post carries the other setting forward
unchanged, two adversarial path-traversal/SQL-shaped payloads are
rejected by the same membership test), and one end-to-end HTTP round
trip proving the D-07 confirmation copy reaches a real browser response
after a real save.

Stdlib-only (json, os, shutil, socket, subprocess, sys, tempfile, time,
urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_config_page.py
"""
import json
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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import app as companion_app  # noqa: E402
from companion import auth  # noqa: E402
from companion.layout import escape_html  # noqa: E402
from companion.pages import config_page  # noqa: E402
from server import device_config  # noqa: E402

TEST_PASSWORD = "config-page-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
# 06.6.3-03: 39 (pre-plan baseline) -> 42 (Task 1: D-02/D-06 LED copy
# rename + heading-dedup checks, +3) -> 45 (Task 2: D-04/D-05 theme/runway
# checks, net +3 — the old "theme_fieldset() emits one radio per THEMES
# registry entry" check was replaced outright, its own assumption no
# longer true for the real single-theme registry, by two new checks plus
# two new runway-card checks) -> 46 (Task 3: D-03 dirty-state bar
# nesting/ordering check, +1) -> 47 (heading-color-consistency: one
# consistent heading level for all four settings groups, +1).
# 06.6.4.1-03: 47 (pre-plan baseline) -> 51 (Task 1: D-01/D-02/D-05 form
# half/D-26 single-column three-wrapped-section merged-form shape, +4 —
# the three-dirty-sections-in-order check, the single-top-level-div
# runway_fieldset() check, the Theme/Runway description-sentence check,
# and the bottom-button static-fallback-attribute check; several
# pre-existing checks were retargeted in place onto the new markup shape
# without changing the total, per this file's own established
# discipline) -> 56 (Task 2: D-05 handle_post() LED-merge behaviour, +5,
# one check per <behavior> bullet) -> 60 (Task 3: D-03/D-04/D-06
# cross-file DOM-contract guards between config_page.py's constants and
# dirty-state.js/style.css, +4).
# 06.6.4.1-07: 60 (pre-plan baseline) -> heading text and every /config
# route literal retargeted to /settings in place, no count change (Task
# 1) -> 54 (Task 2, D-05: the 8 checks exercising the now-deleted
# led_fieldset()/led_section()/handle_led_post() were deleted outright
# (-8; their coverage is superseded by the pre-existing handle_post()
# LED-merge checks and the render() shape check, confirmed before
# deleting, not re-added) plus 1 new source-assertion check that
# config_page exposes none of the three retired symbols (+1); the two
# live-HTTP LED checks were retargeted in place from /config-led onto
# SETTINGS_ROUTE (no count change) and 1 new check pins the retired
# /config-led route now 404s (+1); net -6).
# quick task 260901-qif: 54 (pre-plan baseline) -> 57 (Task 3, +3: the
# .runway-row containment/ordering check, the led-checkbox label class +
# unchanged input-attribute-sequence check, and the third cross-file
# DOM-contract guard proving style.css actually styles .theme-status/
# .runway-row/.led-checkbox. Task 2's retarget of
# _runway_fieldset_returns_single_top_level_div() (one div pair -> two)
# was in place, no count change).
# quick task 260901-re6: 57 (pre-plan baseline) -> 57 (Task 1, no count
# change: the runway-row containment/ordering check, the section-
# captions-appear-once check, and the helper-texts-appear-verbatim check
# were all retargeted in place onto the merged THEME/RUNWAY/LED
# _SECTION_CAPTION constants and restyled markup, per this file's own
# established retarget-without-recounting discipline) -> 57 (Task 2, no
# count change: the form-class-hook check gained the SETTINGS_FORM_ID
# assertion in place, and the dirty-bar-nested-inside-form check was
# inverted wholesale into a dirty-bar-is-sibling-of-form check, both
# retargeted onto the moved/restyled save bar with no count change) -> 60
# (Task 3, +3: observed on-disk baseline was 57 before this task; added
# the one-caption-per-group position-assertion check, the retired-
# helper/description-symbol source assertion check, and the cross-file
# CSS DOM contract guard covering .section-caption, the restyled
# .dirty-bar, fixed-not-sticky positioning, and the 240px must-equal
# pair).
# quick task 260901-s5o: observed on-disk baseline was 60 before this
# task. Task 1 (+1): added the Poll-caption both-branches-and-position
# check, and widened _section_captions_appear_escaped_verbatim_exactly_once()
# in place to cover a fourth constant (POLL_SECTION_CAPTION), no count
# change for that widening. Task 2 (no count change): the cross-file CSS
# guard (_style_css_carries_section_caption_and_restyled_fixed_dirty_bar())
# was retargeted and extended in place onto the floating-card save-bar
# treatment.
# merge of origin/main (Phase 8 six-Spectra-6-colour theme rework, 19
# real theme entries replacing the single "sky" placeholder): main's own
# _theme_fieldset_one_radio_per_registry_entry() check is reinstated (see
# that check's own comment for why), and three checks testing main's
# still-pre-06.6.4.1-07 dual-form LED architecture (led_fieldset()/a
# second /config-led form) were dropped as testing functionality this
# branch already retired. No further checks were added or removed fixing
# the 5 newly-surfaced post-merge failures in the existing (pre-conflict,
# cleanly-inherited-from-HEAD) theme_fieldset()-isolation checks — those
# were in-place rewrites. Recomputed directly against the real on-disk
# check(...) call count at merge-resolution time rather than trusting the
# incremental arithmetic above, which had drifted from actual: 64.
# 10-05-PLAN.md: 64 (pre-plan baseline) -> 68 (Task 3, +4: markup/field-
# order/escaping checks for quiet_hours_group() plus the render()-wiring
# check) -> 73 (Task 3, +5: handle_post()'s quiet-hours save-checkbox-on,
# save-checkbox-absent-still-persists-times, reject-malformed-time,
# reject-crafted-checkbox-value, and all-or-nothing-across-groups checks).
# Five pre-existing checks were retargeted in place (the theme-status
# count 2->3, the dirty-section count 3->4, and three class-literal
# renames from led-checkbox to settings-checkbox) with no count change,
# per this file's own established retarget-without-recounting discipline.
# 11-03: +6 (Task 1, no count change: two pre-existing count-shaped
# checks — the theme-status count 3->4 and the five-dirty-section-order
# check 4->5 — were retargeted in place, per this file's own
# retarget-without-recounting discipline; the round-trip dict-equality
# literal gained "wake_interval_s": None in place too, no count change.
# Task 2, +6: wake_interval_group() markup, wake_interval_group()'s
# value-attribute-only-for-in-range-non-bool-int empty-state check,
# render()'s five-group placement/pre-fill-resolution check,
# handle_post()'s string-to-int conversion/persistence check, its
# rejection-paths-byte-identical check, and its
# empty-or-absent-leaves-unchanged check).
EXPECTED_CHECK_COUNT = 79
EXPECTED_CHECK_COUNT = 65  # + 1 (quick task 260903-peo Task 4: UIR-19's
# save-round-trip check pinning the server-side PRG redirect unchanged
# (SETTINGS_ROUTE?flash=saved) and the rendered redirect target carrying
# both the flash banner and flash-cleanup.js's deferred script tag)
# 06.6.4.1.1-05: 65 (pre-plan baseline, observed on-disk at plan start) ->
# 69 (Task 3, +4: the theme-chip preview-route contract check, the
# real-palette swatch-dot check, the hidden-radio + check-glyph markup
# check, and the zero-fieldset/three-dirty-section page-shape check — one
# new check per <behavior> bullet the plan's Task 3 lists. Seven
# pre-existing checks testing the retired fieldset/radio-list contract
# were retargeted in place onto the D-01 chip-grid markup with no count
# change, per this file's own established retarget-without-recounting
# discipline, and the cross-file CSS guard was extended in place with the
# four new .theme-chip* selector assertions, also no count change).
# 06.6.4.1.1-06 (developer checkpoint follow-up, after the developer's
# real-device review reported the selected element was hard to see): 69
# -> 70 (+1: the background-wash check proving both .runway-card--selected
# and .theme-chip--selected .theme-chip__body carry the same 12%-accent
# color-mix wash .theme-form .theme-option--active already uses).
# quick task 260904-bbi (selected state must follow the LIVE :checked
# choice, not the saved config): 70 -> 72 (+2, RED run confirmed 70/72
# with both new checks failing for the expected reason before any CSS
# was written: the strong-treatment-keyed-to-:has(input:checked) check,
# and the saved-card-degrades-to-a-quiet-marker check).
EXPECTED_CHECK_COUNT = 87  # merge of HEAD (79: Phase 10/11's Quiet hours +
# Wake interval groups) with origin/main (72: 06.6.4.1.1's theme-chip grid +
# quick task 260904-bbi's live-selection re-key) — both branches started
# from the same 64-check common-ancestor baseline (see the merge-of-
# origin/main comment above) and added 15 and 8 checks respectively with no
# overlap, so 64 + 15 + 8 = 87. Recomputed directly against the real
# on-disk check(...) call count at merge-resolution time (87/87 pass),
# not trusted from arithmetic alone, per this file's own established
# discipline.
# 12-05: +5 (Display settings group markup/checked-count check, its
# locked-caption exact-equality check, render()'s D-09 empty-config-
# checked / saved-False-unchecked prefill check, handle_post()'s
# three-checkbox-shape resolution check (absent/exact-constant/crafted,
# with byte-identity on rejection), and the cross-file guard proving
# style.css needs no new selector for the group — one new check per
# Task 2 behavior bullet. Three pre-existing fail-closed checks (the
# theme-status count 5->6, the dirty-section order 5-entry->6-entry list,
# and the DIRTY_SECTION_ATTR occurrence count 5->6) were retargeted in
# place with no count change, per this file's own established retarget-
# without-recounting discipline; the round-trip dict-equality literal
# gained "display_enabled": False in place too, no count change.
# 87 + 5 = 92, recomputed directly against the real on-disk check(...)
# call count at execution time (92/92 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 92


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Same rationale as companion/test_companion_app.py's own copy: the
    end-to-end check below needs to see the real 303 and its Location
    header (to follow the save redirect by hand), not have it silently
    auto-followed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    """Minimal stdlib HTTP client, mirroring
    companion/test_companion_app.py's own http_request()."""
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
    """Owns the companion/app.py subprocess lifecycle — structurally
    identical to companion/test_companion_app.py's own Harness class.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-")
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

    def state_path(self, *parts):
        return os.path.join(self.tmpdir, *parts)

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


def _write_device_config(state_dir, theme, tracked_runway, led_enabled=None):
    os.makedirs(state_dir, exist_ok=True)
    doc = {"theme": theme, "tracked_runway": tracked_runway}
    if led_enabled is not None:
        doc["led_enabled"] = led_enabled
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump(doc, fh)


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
    # Section 1: unit checks against render()/theme_fieldset()/
    # runway_fieldset()/poll_trigger_section() (Task 1 behavior bullets)
    # and handle_post() (Task 2 behavior bullets), each driven against a
    # temporary state directory and a hand-built ctx dict.
    # ==================================================================

    def _render_shape_theme_chip_grid_runway_cards_groups_and_save_button():
        # merge of origin/main (06.6.4.1.1-05, D-01/D-02/D-08, sketch 004
        # variant B): Theme's own <fieldset>/<legend> radio group is retired
        # outright in favour of a .theme-chip-grid inside the same
        # .theme-status card idiom every other Settings group already uses —
        # the whole rendered Settings page now emits zero <fieldset> and zero
        # <legend> anywhere. This supersedes the pre-06.6.4.1.1-05 version of
        # this check (itself the result of the earlier merge of origin/main's
        # Phase 8 six-colour theme rework), which asserted the OPPOSITE:
        # exactly one <fieldset>, Theme's own.
        #
        # 10-05-PLAN.md Task 3 / 11-03: Quiet hours and Wake interval join
        # Theme/Runway/Diagnostic LED as the fourth and fifth .theme-status-
        # wrapped groups — the count below is 5, not the pre-Phase-10/11
        # value of 3, for that reason alone, not a rename.
        #
        # 12-05-PLAN.md: Display joins as the sixth and last .theme-status-
        # wrapped group — the count below is 6, not 5, for that reason
        # alone, not a rename.
        ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements anywhere on the page, found one"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements anywhere on the page, found one"
        if rendered.count('class="theme-status"') != 6:
            return False, "expected exactly 6 theme-status-wrapped groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display), got %d" % rendered.count('class="theme-status"')
        if "theme-chip-grid" not in rendered:
            return False, "expected the Theme group to render a .theme-chip-grid"
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if "Save settings" not in rendered:
            return False, "expected the 'Save settings' submit button copy"
        return True, ""
    check(
        "render() emits Theme's .theme-chip-grid (no <fieldset>, D-01), six theme-status-wrapped groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display), three runway-card labels, and a Save settings submit button",
        _render_shape_theme_chip_grid_runway_cards_groups_and_save_button)

    def _led_group_carries_classed_label_and_unchanged_input_attrs():
        # quick task 260901-qif: pins the settings-checkbox label class
        # (renamed from led-checkbox by 10-05-PLAN.md Task 2) and guards
        # the input's name/value/checked attribute sequence against a
        # future markup edit silently reordering it - the two live-HTTP
        # LED checks further down this file match on that exact sequence.
        checked_html = config_page.led_group(True)
        unchecked_html = config_page.led_group(False)
        label_open = '<label class="settings-checkbox">'
        if checked_html.count(label_open) != 1:
            return False, "expected led_group(True) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        if unchecked_html.count(label_open) != 1:
            return False, "expected led_group(False) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        led_value = escape_html(config_page.LED_CHECKBOX_VALUE)
        expected_checked = 'name="led_enabled" value="%s" checked' % led_value
        if expected_checked not in checked_html:
            return False, "expected led_group(True) to carry %r" % (expected_checked,)
        expected_unchecked = 'name="led_enabled" value="%s">' % led_value
        if expected_unchecked not in unchecked_html:
            return False, "expected led_group(False) to carry %r with no checked flag" % (expected_unchecked,)
        if "checked" in unchecked_html:
            return False, "expected led_group(False) to carry no checked flag at all"
        return True, ""
    check(
        "led_group() emits the settings-checkbox label class and preserves the input's name/value/checked attribute sequence",
        _led_group_carries_classed_label_and_unchanged_input_attrs)

    # ------------------------------------------------------------------
    # 10-05-PLAN.md Task 3: quiet_hours_group() markup/field-order/
    # escaping and render() wiring checks (D-03/D-04, 10-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _quiet_hours_group_markup_checkbox_and_time_inputs():
        checked_html = config_page.quiet_hours_group(True, "23:00", "07:00")
        unchecked_html = config_page.quiet_hours_group(False, "23:00", "07:00")
        label_open = '<label class="settings-checkbox">'
        if checked_html.count(label_open) != 1:
            return False, "expected quiet_hours_group(True, ...) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        if 'name="quiet_hours_start"' not in checked_html or 'type="time"' not in checked_html:
            return False, "expected a type=\"time\" input named quiet_hours_start"
        if 'value="23:00"' not in checked_html:
            return False, "expected quiet_hours_start's value to be 23:00"
        if 'name="quiet_hours_end"' not in checked_html:
            return False, "expected an input named quiet_hours_end"
        if 'value="07:00"' not in checked_html:
            return False, "expected quiet_hours_end's value to be 07:00"
        if checked_html.count("checked") != 1:
            return False, "expected quiet_hours_group(True, ...) to carry exactly one checked flag, got %d" % checked_html.count("checked")
        if "checked" in unchecked_html:
            return False, "expected quiet_hours_group(False, ...) to carry no checked flag at all"
        if "theme-status__row" in checked_html:
            return False, "expected no theme-status__row wrapper — Start/End must stack vertically (10-UI-SPEC.md)"
        if "disabled" in checked_html or "disabled" in unchecked_html:
            return False, "expected no disabled attribute on either branch — the time inputs are never disabled (10-UI-SPEC.md)"
        return True, ""
    check(
        "quiet_hours_group() emits the settings-checkbox label, one type=\"time\" input each for Start/End with their current values, exactly one checked flag when enabled and none when disabled, no theme-status__row, and no disabled attribute",
        _quiet_hours_group_markup_checkbox_and_time_inputs)

    def _quiet_hours_group_field_order_heading_caption_checkbox_start_end():
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
        heading_close = rendered.index("</h2>")
        caption_pos = rendered.index("section-caption")
        checkbox_pos = rendered.index('name="quiet_hours_enabled"')
        start_pos = rendered.index('name="quiet_hours_start"')
        end_pos = rendered.index('name="quiet_hours_end"')
        if not (heading_close < caption_pos < checkbox_pos < start_pos < end_pos):
            return False, (
                "expected heading < caption < checkbox < start < end in document order, got positions %r"
                % ((heading_close, caption_pos, checkbox_pos, start_pos, end_pos),))
        return True, ""
    check(
        "quiet_hours_group()'s field order is heading, then caption, then the enable checkbox, then Start, then End, in document order (10-UI-SPEC.md's locked field order)",
        _quiet_hours_group_field_order_heading_caption_checkbox_start_end)

    def _quiet_hours_group_escapes_crafted_current_values():
        rendered = config_page.quiet_hours_group(True, '"><script>', "07:00")
        if "<script>" in rendered:
            return False, "expected the crafted current_start value to be escaped, found a raw <script> substring"
        return True, ""
    check(
        "quiet_hours_group() escapes a crafted current_start value — no raw <script> substring reaches the markup",
        _quiet_hours_group_escapes_crafted_current_values)

    def _render_wires_quiet_hours_group_after_led_before_save_button():
        rendered = config_page.render({
            "device_config": {
                "theme": "black", "tracked_runway": "3", "led_enabled": True,
                "quiet_hours_enabled": True, "quiet_hours_start": "22:30",
                "quiet_hours_end": "06:15",
            },
            "poll_cooldown_remaining": 0,
        })
        if 'value="22:30"' not in rendered or 'value="06:15"' not in rendered:
            return False, "expected the current quiet-hours times to appear in the rendered page"
        if 'name="quiet_hours_enabled"' not in rendered:
            return False, "expected the quiet-hours enable checkbox to appear in the rendered page"
        led_heading_pos = rendered.index(config_page.LED_SECTION_HEADING)
        quiet_heading_pos = rendered.index(config_page.QUIET_HOURS_SECTION_HEADING)
        save_button_pos = rendered.index("Save settings")
        if not (led_heading_pos < quiet_heading_pos < save_button_pos):
            return False, "expected the Quiet hours group to render after Diagnostic LED and before the Save settings button"
        return True, ""
    check(
        "render() wires quiet_hours_group() with the saved current values, positioned after Diagnostic LED and before the Save settings button",
        _render_wires_quiet_hours_group_after_led_before_save_button)

    # ------------------------------------------------------------------
    # 11-03-PLAN.md Task 1/Task 2: wake_interval_group() markup/empty-state
    # and render() placement/pre-fill-resolution checks (11-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _wake_interval_group_markup_in_range_value():
        rendered = config_page.wake_interval_group(120)
        if rendered.count('class="theme-status"') != 1:
            return False, "expected exactly one .theme-status wrapper"
        if config_page.DIRTY_SECTION_ATTR not in rendered:
            return False, "expected the wrapper to carry DIRTY_SECTION_ATTR"
        expected_heading = (
            '<h2 class="text-heading">%s</h2>'
            % escape_html(config_page.WAKE_INTERVAL_SECTION_HEADING))
        if rendered.count(expected_heading) != 1:
            return False, "expected exactly one heading %r" % (expected_heading,)
        expected_caption = (
            '<p class="text-label section-caption">%s</p>'
            % escape_html(config_page.WAKE_INTERVAL_SECTION_CAPTION))
        if rendered.count(expected_caption) != 1:
            return False, "expected exactly one caption %r" % (expected_caption,)
        if rendered.count('<input type="number" name="wake_interval_s"') != 1:
            return False, "expected exactly one <input type=\"number\" name=\"wake_interval_s\">"
        if 'min="%d"' % device_config.WAKE_INTERVAL_MIN_S not in rendered:
            return False, "expected min to equal device_config.WAKE_INTERVAL_MIN_S"
        if 'max="%d"' % device_config.WAKE_INTERVAL_MAX_S not in rendered:
            return False, "expected max to equal device_config.WAKE_INTERVAL_MAX_S"
        if 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT not in rendered:
            return False, "expected the locked placeholder text"
        if 'value="120"' not in rendered:
            return False, "expected the matching value attribute"
        if "<fieldset" in rendered:
            return False, "expected no <fieldset> — these sibling groups deliberately don't use one"
        if "<legend" in rendered:
            return False, "expected no <legend> — a <legend> only has accessible-name semantics inside a <fieldset>"
        if "settings-checkbox" in rendered:
            return False, "expected no settings-checkbox class — that class normalises a checkbox, not a numeric input"
        return True, ""
    check(
        "wake_interval_group(120) emits one .theme-status[data-dirty-section] wrapper, the locked heading/caption, one type=\"number\" input with min/max from device_config and the locked placeholder and a matching value, and none of <fieldset>/<legend>/settings-checkbox",
        _wake_interval_group_markup_in_range_value)

    def _wake_interval_group_value_attribute_only_for_in_range_non_bool_int():
        # An out-of-range or wrong-typed value attribute would fail native
        # HTML5 constraint validation and block submission of the entire
        # Settings form, not just this field (11-UI-SPEC.md, T-11-03-03) —
        # this is the direct regression guard for that risk.
        no_value_cases = (None, True, False, "120", 30, 59, 3601, 7200)
        for case in no_value_cases:
            if "value=" in config_page.wake_interval_group(case):
                return False, "expected wake_interval_group(%r) to emit no value attribute" % (case,)
        for case, expected in ((60, 60), (3600, 3600), (120, 120)):
            rendered = config_page.wake_interval_group(case)
            if 'value="%d"' % expected not in rendered:
                return False, "expected wake_interval_group(%r) to emit value=\"%d\"" % (case, expected)
        return True, ""
    check(
        "wake_interval_group() emits a value attribute only for an in-range, non-bool int (None/True/False/a str/30/59/3601/7200 all emit none; 60/3600/120 each emit theirs) — an out-of-range or wrong-typed value would fail native constraint validation and block the whole form",
        _wake_interval_group_value_attribute_only_for_in_range_non_bool_int)

    def _render_places_wake_interval_last_and_resolves_prefill():
        base_ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(base_ctx)
        headings = [
            "Theme", "Runway", config_page.LED_SECTION_HEADING,
            config_page.QUIET_HOURS_SECTION_HEADING,
            config_page.WAKE_INTERVAL_SECTION_HEADING,
        ]
        positions = [rendered.index(h) for h in headings]
        if positions != sorted(positions):
            return False, "expected the five settings groups in locked order Theme/Runway/Diagnostic LED/Quiet hours/Wake interval, got positions %r" % (positions,)
        if "value=" in rendered.split('name="wake_interval_s"')[1].split(">")[0]:
            return False, "expected no value attribute when neither on-disk nor ctx fallback is present"

        on_disk_ctx = dict(base_ctx)
        on_disk_ctx["device_config"] = dict(
            base_ctx["device_config"], wake_interval_s=180)
        on_disk_ctx["wake_interval_env_default"] = 900
        rendered = config_page.render(on_disk_ctx)
        if 'value="180"' not in rendered:
            return False, "expected the on-disk wake_interval_s to win over the ctx fallback"

        fallback_ctx = dict(base_ctx)
        fallback_ctx["wake_interval_env_default"] = 900
        rendered = config_page.render(fallback_ctx)
        if 'value="900"' not in rendered:
            return False, "expected the ctx fallback to be used when the on-disk value is None"
        return True, ""
    check(
        "render() places Wake interval last in the locked five-group order, resolves no value attribute when neither source is present, prefers an on-disk wake_interval_s over ctx['wake_interval_env_default'], and falls back to the ctx default when the on-disk value is None",
        _render_places_wake_interval_last_and_resolves_prefill)

    # ------------------------------------------------------------------
    # 12-05-PLAN.md Task 1/Task 2: display_group() markup, its caption's
    # locked copy, render()'s D-09 prefill default, and handle_post()'s
    # three-shape checkbox resolution ladder (12-UI-SPEC.md, 12-CONTEXT.md
    # D-02/D-08/D-09).
    # ------------------------------------------------------------------

    def _display_group_markup_shape_checked_and_unchecked():
        # Bullet 1: display_group(True) emits one .theme-status[data-dirty-
        # section] wrapper, the locked heading and caption, one
        # .settings-checkbox label, exactly one checkbox input named for
        # the field, exactly one checked flag; display_group(False) emits
        # none; and neither emits <fieldset>/<legend>/type="time"/
        # type="number"/disabled - this group has no dependent fields and
        # must not grow any.
        checked_html = config_page.display_group(True)
        unchecked_html = config_page.display_group(False)
        for rendered in (checked_html, unchecked_html):
            if rendered.count('class="theme-status"') != 1:
                return False, "expected exactly one .theme-status wrapper"
            if config_page.DIRTY_SECTION_ATTR not in rendered:
                return False, "expected the wrapper to carry DIRTY_SECTION_ATTR"
            expected_heading = (
                '<h2 class="text-heading">%s</h2>'
                % escape_html(config_page.DISPLAY_SECTION_HEADING))
            if rendered.count(expected_heading) != 1:
                return False, "expected exactly one heading %r" % (expected_heading,)
            expected_caption = (
                '<p class="text-label section-caption">%s</p>'
                % escape_html(config_page.DISPLAY_SECTION_CAPTION))
            if rendered.count(expected_caption) != 1:
                return False, "expected exactly one caption %r" % (expected_caption,)
            if rendered.count('<label class="settings-checkbox">') != 1:
                return False, "expected exactly one <label class=\"settings-checkbox\">"
            if rendered.count('<input type="checkbox" name="display_enabled"') != 1:
                return False, "expected exactly one checkbox input named display_enabled"
            if "<fieldset" in rendered:
                return False, "expected no <fieldset> - this group deliberately doesn't use one"
            if "<legend" in rendered:
                return False, "expected no <legend> - a <legend> only has accessible-name semantics inside a <fieldset>"
            if 'type="time"' in rendered:
                return False, "expected no type=\"time\" input - this group has no dependent fields"
            if 'type="number"' in rendered:
                return False, "expected no type=\"number\" input - this group has no dependent fields"
            if "disabled" in rendered:
                return False, "expected no disabled attribute - no sibling control's enabled state depends on this one"
        if checked_html.count(" checked") != 1:
            return False, "expected display_group(True) to carry exactly one checked flag"
        if unchecked_html.count(" checked") != 0:
            return False, "expected display_group(False) to carry zero checked flags"
        return True, ""
    check(
        "display_group(True)/display_group(False) emit exactly one .theme-status[data-dirty-section] wrapper, the locked heading/caption, one .settings-checkbox label, one checkbox input named display_enabled, and the correct checked count, with none of <fieldset>/<legend>/type=\"time\"/type=\"number\"/disabled",
        _display_group_markup_shape_checked_and_unchecked)

    def _display_section_caption_locked_verbatim():
        # Bullet 2: exact equality is a stronger gate here than a
        # word-level absence rule (e.g. "instant"/"immediate" not present)
        # and does not risk pinning fragile phrasing beyond the locked
        # sentence itself (12-UI-SPEC.md Copywriting Contract, D-02).
        expected = (
            "Turns the physical panel off remotely, without touching the "
            "hardware. Takes effect within about 5 minutes, both "
            "switching off and back on.")
        if config_page.DISPLAY_SECTION_CAPTION != expected:
            return False, "expected DISPLAY_SECTION_CAPTION to equal the locked sentence, got %r" % (config_page.DISPLAY_SECTION_CAPTION,)
        return True, ""
    check(
        "DISPLAY_SECTION_CAPTION equals 12-UI-SPEC.md's locked sentence exactly, stating the ~5-minute apply latency in both directions and never claiming immediacy (D-02)",
        _display_section_caption_locked_verbatim)

    def _render_display_prefill_defaults_checked_and_honors_saved_false():
        # Bullet 3: render() with an empty device_config produces a
        # checked box (D-09 reaching the page, not just the loader), and
        # {"display_enabled": False} produces an unchecked one.
        rendered = config_page.render({"device_config": {}, "state_dir": "/tmp"})
        if rendered.count('name="display_enabled"') != 1:
            return False, "expected exactly one display_enabled input"
        segment = rendered[rendered.index('%s="Display"' % config_page.DIRTY_SECTION_ATTR):]
        segment = segment[:segment.index("</div>")]
        if " checked" not in segment:
            return False, "expected an empty device_config to render the Display box checked (D-09)"

        rendered_off = config_page.render({
            "device_config": {"display_enabled": False}, "state_dir": "/tmp"})
        segment_off = rendered_off[rendered_off.index('%s="Display"' % config_page.DIRTY_SECTION_ATTR):]
        segment_off = segment_off[:segment_off.index("</div>")]
        if " checked" in segment_off:
            return False, "expected device_config={'display_enabled': False} to render the box unchecked"
        return True, ""
    check(
        "render() with an empty device_config renders the Display checkbox checked (D-09), and with display_enabled explicitly False renders it unchecked",
        _render_display_prefill_defaults_checked_and_honors_saved_false)

    def _handle_post_display_enabled_three_shapes():
        # Bullet 4: all three checkbox shapes - absent means off and is
        # persisted as off; the exact constant means on; a crafted value
        # returns the generic save-failed flash and leaves a pre-existing
        # device_config.json byte-identical, proving all-or-nothing
        # rejection still holds across all eight fields.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for an absent display_enabled, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["display_enabled"] is not False:
                return False, "expected display_enabled False on disk, got %r" % (on_disk["display_enabled"],)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"display_enabled": config_page.DISPLAY_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the exact checkbox constant, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["display_enabled"] is not True:
                return False, "expected display_enabled True on disk, got %r" % (on_disk["display_enabled"],)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3", led_enabled=True)
            with open(device_config.device_config_path(tmpdir), "r") as fh:
                doc = json.load(fh)
            doc["display_enabled"] = True
            with open(device_config.device_config_path(tmpdir), "w") as fh:
                json.dump(doc, fh)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"display_enabled": "<crafted>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted display_enabled value, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() resolves display_enabled through all three checkbox shapes: absent persists False, DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key and leaves a pre-existing device_config.json byte-identical",
        _handle_post_display_enabled_three_shapes)

    def _every_settings_group_is_named_exactly_once():
        # heading-color-consistency debug session, extended by 06.6.4.1
        # (D-05) and 06.6.4.1.1-05 (D-01): Config carries four settings
        # groups. D-05 already merged Diagnostic LED off its own
        # <fieldset>/<legend> onto the shared <h2 class="text-heading">
        # role Theme/Runway/Poll used. The merge of origin/main (Phase 8)
        # briefly reopened a second <legend> — D-04's read-only-vs-editable
        # fallback took the editable <fieldset><legend>Theme</legend>
        # branch once THEME_IDS held more than one real entry.
        # 06.6.4.1.1-05 closes that gap for good: the multi-theme branch
        # is now the D-01 chip grid inside a .theme-status card, so all
        # four groups are named by the same <h2 class="text-heading">
        # element, at one consistent heading level, with zero <legend>
        # anywhere on the page.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        for name in ("Theme", "Runway", "Diagnostic LED", "Poll"):
            heading = '<h2 class="text-heading">%s</h2>' % name
            if rendered.count(heading) != 1:
                return False, (
                    "expected exactly one %r group heading, got %d"
                    % (heading, rendered.count(heading)))
        if "<legend" in rendered:
            return False, (
                "expected zero <legend> elements anywhere on the page — "
                "Theme's own <fieldset>/<legend> radio group is retired "
                "(06.6.4.1.1-05, D-01)")
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements anywhere on the page"
        # The old label-paragraph shape must not come back alongside
        # Theme's own naming — that would name the Theme group twice.
        if '<p class="text-label">Theme</p>' in rendered:
            return False, (
                "the Theme group is named twice: the superseded "
                "text-label paragraph is still present next to its own naming element")
        return True, ""
    check(
        "all four Config settings groups (Theme/Runway/Diagnostic LED/Poll) are named "
        "exactly once, all via the shared <h2 class=\"text-heading\"> role, with zero "
        "<legend> and zero <fieldset> anywhere on the page (06.6.4.1.1-05, D-01)",
        _every_settings_group_is_named_exactly_once)

    def _render_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): Settings' top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        # 06.6.4.1-07 (D-26): the heading text itself was retargeted from
        # "Config" to "Settings", matching the route rename and the nav
        # label — the page's own on-screen name must agree with both.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if '<h1 class="page-title">Settings</h1>' not in rendered:
            return False, "expected the page_header()-rendered <h1 class=\"page-title\">Settings</h1>"
        if '<h1 class="text-heading">' in rendered:
            return False, "expected no bare <h1 class=\"text-heading\"> heading"
        return True, ""
    check(
        "Settings opens with the shared layout.page_header() component, not a bare <h1>",
        _render_opens_with_shared_page_header)

    def _settings_form_carries_config_form_class_hook():
        # D-01 stable class hook: the settings form (POST /config) needs a
        # class attribute so plan 06.3-02's desktop two-column fieldset
        # grid rule (companion/static/style.css's 960px breakpoint) can
        # target it without a brittle attribute selector.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'class="config-form"' not in rendered:
            return False, "expected the settings form to carry class=\"config-form\""
        # 06.6.3-03 (D-03): the form tag also carries data-dirty-form now,
        # the DOM-attribute hook dirty-state.js (06.6.3-01) reads.
        # 06.6.4.1 (D-05): the action is now config_page.SETTINGS_ROUTE
        # ("/settings"), not the old "/config" literal — the single
        # definition of that route lives in config_page, never re-typed
        # here as a literal.
        # quick task 260901-re6: the form tag also carries an id now
        # (config_page.SETTINGS_FORM_ID), interpolated the same way
        # SETTINGS_ROUTE already is — never re-typed as a literal — so
        # the dirty-bar's save button (now a sibling of the form) can
        # associate with it via a `form=` attribute.
        expected_tag = (
            '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
            % (config_page.SETTINGS_FORM_ID, config_page.SETTINGS_ROUTE))
        if expected_tag not in rendered:
            return False, "expected the config-form class, id, data-dirty-form, method=\"post\", and action=%r on the same form tag" % (config_page.SETTINGS_ROUTE,)
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form in render()'s output, got %d" % rendered.count('<form class="config-form"')
        return True, ""
    check(
        "the settings form keeps the stable config-form class hook the desktop two-column fieldset layout targets",
        _settings_form_carries_config_form_class_hook)

    def _render_dirty_bar_is_sibling_of_form_last_on_page():
        # quick task 260901-re6: inverted wholesale from the pre-merge
        # version of this check (which asserted the bar was a genuine
        # descendant of the form). `position: sticky` resolved against
        # the form's own short box, so the bar detached from the
        # viewport bottom on a tall page — the fix moves the bar to be a
        # sibling of the form, emitted last on the page (after both
        # </form> and the Poll section), submitting via a form= attribute
        # instead of native DOM nesting.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form>, no duplicate"
        if "</form>" not in rendered:
            return False, "expected a closing </form> tag"
        form_end = rendered.index("</form>")
        if "data-dirty-bar" not in rendered:
            return False, "expected data-dirty-bar to appear in render()'s output"
        bar_pos = rendered.index("data-dirty-bar")
        if bar_pos <= form_end:
            return False, "expected data-dirty-bar to appear AFTER </form> closes, not inside it"
        poll_heading = '<h2 class="text-heading">Poll</h2>'
        if poll_heading not in rendered:
            return False, "expected the Poll section heading to be present"
        poll_pos = rendered.index(poll_heading)
        if bar_pos <= poll_pos:
            return False, "expected data-dirty-bar to appear after the Poll section heading too, so the bar is genuinely last on the page"
        form_start = rendered.index('<form class="config-form"')
        form_segment = rendered[form_start:form_end]
        if "Save settings" not in form_segment:
            return False, "expected the always-visible bottom Save settings fallback button to still appear inside the form"
        save_button_marker = 'class="dirty-bar__save" form="%s"' % config_page.SETTINGS_FORM_ID
        if save_button_marker not in rendered:
            return False, "expected the dirty-bar's own save button to carry form=%r" % (config_page.SETTINGS_FORM_ID,)
        return True, ""
    check(
        "render()'s dirty-state bar is a sibling of the config-form <form>, emitted last on the page after both </form> and the Poll section, with its save button carrying form=SETTINGS_FORM_ID (quick task 260901-re6)",
        _render_dirty_bar_is_sibling_of_form_last_on_page)

    def _theme_fieldset_one_radio_per_registry_entry():
        # merge of origin/main (Phase 8): this exact check existed pre-
        # 06.6.3-03, was retired outright when the registry briefly held
        # just "sky" (a one-option radio group has no real decision
        # value — D-04's read-only-status branch took over that case),
        # and is reinstated here now that the merged registry holds 19
        # real entries again — theme_fieldset()'s existing len()==1
        # fallback (unmodified by this merge) means this assertion is
        # exercising real, currently-live markup, not a retired code path.
        rendered = config_page.theme_fieldset("black")
        radio_count = rendered.count('name="theme"')
        if radio_count != len(device_config.THEMES):
            return False, (
                "expected %d theme radios (len(THEMES)), got %d"
                % (len(device_config.THEMES), radio_count))
        return True, ""
    check(
        "theme_fieldset() emits one radio per THEMES registry entry now that the registry holds more than one theme (merge of origin/main, Phase 8)",
        _theme_fieldset_one_radio_per_registry_entry)

    def _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex():
        # D-04, Task 2 Test 1: with a synthetic single-member THEME_IDS
        # registry (monkeypatched for the duration of this check only),
        # theme_fieldset() renders the read-only status block — zero
        # <input> occurrences — showing "{label} · current" and swatch
        # chip hex values computed at test time from
        # panel_format.PALETTE_RGB, not hardcoded expected strings.
        #
        # merge of origin/main (Phase 8): the real global THEME_IDS
        # registry now permanently holds 19 entries, so this check can no
        # longer rely on "the real (unmodified) registry" to exercise the
        # len()==1 branch — it monkeypatches a clean, isolated one-member
        # registry instead, mirroring the pattern the sibling
        # multi-theme-fallback check below already uses.
        original_themes = device_config.THEMES
        original_ids = device_config.THEME_IDS
        default_id = device_config.DEFAULT_THEME_ID
        device_config.THEMES = {default_id: dict(original_themes[default_id])}
        device_config.THEME_IDS = tuple(device_config.THEMES)
        try:
            rendered = config_page.theme_fieldset(default_id)
            if "<input" in rendered:
                return False, "expected zero <input occurrences in the read-only branch"
            expected_label = "%s · current" % device_config.theme_label(default_id)
            if expected_label not in rendered:
                return False, "expected %r in the rendered output" % (expected_label,)
            theme = device_config.THEMES[default_id]
            departing_hex = config_page._palette_hex(theme["departing_index"])
            arriving_hex = config_page._palette_hex(theme["arriving_index"])
            if ("background:%s" % departing_hex) not in rendered:
                return False, "expected the departing swatch hex %r derived from PALETTE_RGB" % (departing_hex,)
            if ("background:%s" % arriving_hex) not in rendered:
                return False, "expected the arriving swatch hex %r derived from PALETTE_RGB" % (arriving_hex,)
            if "Phase 7" in rendered:
                return False, "expected no leaked internal 'Phase 7' planning reference (UXA-05)"
        finally:
            device_config.THEMES = original_themes
            device_config.THEME_IDS = original_ids
        return True, ""
    check(
        "theme_fieldset() renders the read-only theme-status block with real panel-color swatch hex values when THEME_IDS has one member (D-04)",
        _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex)

    def _theme_fieldset_falls_back_to_chip_grid_when_multiple_themes_registered():
        # D-04, Task 2 Test 2: a synthetic 2-member THEME_IDS (monkeypatched
        # for the duration of this check only) makes theme_fieldset() fall
        # back to the editable chip-grid markup (06.6.4.1.1-05, D-01) — a
        # len() check, not a hardcoded single-theme assumption.
        #
        # merge of origin/main (Phase 8): THEMES is now REPLACED with a
        # clean 2-entry dict rather than dict(original_themes) plus one
        # more key — copying the real registry would now start from 19
        # entries, not 1, breaking this test's own "exactly 2 theme radios"
        # assertion below.
        original_themes = device_config.THEMES
        original_ids = device_config.THEME_IDS
        default_id = device_config.DEFAULT_THEME_ID
        device_config.THEMES = {
            default_id: dict(original_themes[default_id]),
            "dusk": {
                "departing_index": original_themes[default_id]["departing_index"],
                "arriving_index": original_themes[default_id]["arriving_index"],
                "ink_index": original_themes[default_id]["ink_index"],
                "label": "Dusk",
            },
        }
        device_config.THEME_IDS = tuple(device_config.THEMES)
        try:
            rendered = config_page.theme_fieldset(default_id)
        finally:
            device_config.THEMES = original_themes
            device_config.THEME_IDS = original_ids
        # 06.6.4.1.1-05: the fallback branch no longer emits a
        # <fieldset>/<legend> radio group — it emits a .theme-chip-grid
        # inside the same .theme-status card idiom Runway/Diagnostic LED
        # use, carrying data-dirty-section="Theme" on that wrapper.
        if "<fieldset" in rendered or "<legend" in rendered:
            return False, "expected zero <fieldset>/<legend> once >1 theme is registered (D-01 retires the radio-list markup)"
        if "theme-chip-grid" not in rendered:
            return False, "expected the fallback branch to render a .theme-chip-grid"
        if ('%s="%s"' % (config_page.DIRTY_SECTION_ATTR, escape_html("Theme"))) not in rendered:
            return False, "expected the fallback .theme-status card to carry data-dirty-section=\"Theme\""
        if rendered.count('name="theme"') != 2:
            return False, "expected 2 theme radios, got %d" % rendered.count('name="theme"')
        return True, ""
    check(
        "theme_fieldset() falls back to the editable D-01 chip grid the moment a second theme is registered (D-04, 06.6.4.1.1-05)",
        _theme_fieldset_falls_back_to_chip_grid_when_multiple_themes_registered)

    def _theme_fieldset_covers_every_registered_theme_with_own_id_and_label():
        # 08-CONTEXT.md D-01/D-02/D-03/D-04, widened by the 08-06 on-glass
        # session (5 themes -> 11): proves the CFG-01 picker absorbs every
        # registered theme purely through the registry - driven from
        # THEME_IDS/theme_label(), not a hardcoded list or count, so this
        # stays true for a future twelfth theme with zero test-file change
        # needed. Deliberately no `len(theme_ids) != N` assertion - that
        # exact literal is what broke every time this registry's membership
        # changed; the real invariant is "every id THEME_IDS actually
        # holds renders its own radio+label", checked below instead.
        rendered = config_page.theme_fieldset("white")
        theme_ids = device_config.THEME_IDS
        if not theme_ids:
            return False, "THEME_IDS is empty - nothing to render"
        for theme_id in theme_ids:
            value_needle = 'value="%s"' % escape_html(theme_id)
            if value_needle not in rendered:
                return False, "expected a radio carrying value=%r, not found in rendered fieldset" % (theme_id,)
            label_needle = escape_html(device_config.theme_label(theme_id))
            if label_needle not in rendered:
                return False, "expected theme %r's plain label %r as visible text, not found" % (theme_id, label_needle)
        return True, ""
    check(
        "theme_fieldset() renders one radio per registered theme, each carrying its own registry id as value and its own plain "
        "label as visible text, with zero hardcoded ids/labels/counts in the assertion itself",
        _theme_fieldset_covers_every_registered_theme_with_own_id_and_label)

    def _theme_fieldset_default_selects_exactly_the_white_option():
        rendered = config_page.theme_fieldset(device_config.DEFAULT_THEME_ID)
        if rendered.count(" checked") != 1:
            return False, "expected exactly one selected radio, found %d" % rendered.count(" checked")
        # 06.6.4.1.1-05: the chip's radio carries class="visually-hidden"
        # between value= and checked (matching .runway-card's own radio
        # attribute sequence), so the needle grows an intervening
        # attribute compared to the retired bare radio-list markup.
        white_option_needle = 'value="white" class="visually-hidden" checked'
        if white_option_needle not in rendered:
            return False, "the selected option is not the white one (expected %r substring)" % (white_option_needle,)
        if 'theme-chip theme-chip--selected' not in rendered:
            return False, "expected the White chip's <label> to carry theme-chip--selected"
        return True, ""
    check(
        "theme_fieldset() rendered with the new default theme id marks exactly one option selected, and it is White",
        _theme_fieldset_default_selects_exactly_the_white_option)

    def _runway_fieldset_exactly_three_radios():
        rendered = config_page.runway_fieldset("3")
        radio_count = rendered.count('name="tracked_runway"')
        if radio_count != 3:
            return False, "expected exactly 3 runway radios, got %d" % radio_count
        return True, ""
    check(
        "runway_fieldset() emits exactly three runway radio inputs",
        _runway_fieldset_exactly_three_radios)

    def _runway_fieldset_cards_visually_hidden_radio_and_selected_class():
        # D-05, Task 2 Test 3: three .runway-card <label>s, each wrapping a
        # visually-hidden (not display:none) native radio, with only the
        # "3" card carrying runway-card--selected.
        rendered = config_page.runway_fieldset("3", images_available=())
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if rendered.count("runway-card--selected") != 1:
            return False, "expected exactly one runway-card--selected modifier"
        if 'value="3" class="visually-hidden" checked' not in rendered:
            return False, "expected the selected card's radio to carry class=\"visually-hidden\" and checked"
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('class="visually-hidden"') < 3:
            return False, "expected every card's radio to carry the visually-hidden class"
        return True, ""
    check(
        "runway_fieldset('3') renders three selectable cards, each wrapping a visually-hidden radio, with only the '3' card selected (D-05)",
        _runway_fieldset_cards_visually_hidden_radio_and_selected_class)

    def _runway_fieldset_cards_image_rendering_per_card():
        # D-05, Task 2 Test 4: an <img> renders inside exactly the cards
        # named in images_available, none inside any other card.
        rendered = config_page.runway_fieldset("3", images_available=("3", "06-24"))
        if rendered.count("<img") != 2:
            return False, "expected exactly 2 <img occurrences, got %d" % rendered.count("<img")
        if "/runway-image/3.png" not in rendered or "/runway-image/06-24.png" not in rendered:
            return False, "expected <img> src pointing at both supplied runway images"
        if "/runway-image/02-20.png" in rendered:
            return False, "expected no <img> for the runway not in images_available"
        return True, ""
    check(
        "runway_fieldset('3', images_available=('3', '06-24')) renders an <img> inside exactly those two cards, none in the third (D-05)",
        _runway_fieldset_cards_image_rendering_per_card)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 1 (D-01, D-02, D-05 form half, D-26): the new
    # single-column, three-wrapped-section, one-merged-form shape.
    # ------------------------------------------------------------------

    def _render_exactly_five_dirty_sections_in_order():
        # Acceptance criterion: the rendered output contains exactly
        # six elements carrying data-dirty-section, whose attribute
        # values in document order are "Theme", "Runway", "Diagnostic
        # LED", "Quiet hours", "Wake interval", "Display" — 10-05-PLAN.md
        # Task 1 wired Quiet hours in as the fourth group after
        # Diagnostic LED, 11-03-PLAN.md Task 1 wired Wake interval in as
        # the fifth, after Quiet hours, and 12-05-PLAN.md Task 1 wires
        # Display in as the sixth and last, after Wake interval.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        found = re.findall(
            r'%s="([^"]*)"' % re.escape(config_page.DIRTY_SECTION_ATTR), rendered)
        expected = ["Theme", "Runway", "Diagnostic LED", "Quiet hours", "Wake interval", "Display"]
        if found != expected:
            return False, "expected %r in document order, got %r" % (expected, found)
        return True, ""
    check(
        "render() carries exactly six data-dirty-section elements, in document order Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display",
        _render_exactly_five_dirty_sections_in_order)

    def _runway_fieldset_returns_single_top_level_div():
        # Acceptance criterion: runway_fieldset(...) returns a string
        # that starts with a single opening div tag and ends with its
        # matching closing tag — one top-level element, not five siblings
        # (D-01's root-cause fix). Retargeted in place (quick task
        # 260901-qif): the count moved from one div pair to two because a
        # nested `.runway-row` layout container was introduced around just
        # the cards — the original "exactly one <div> pair" wording was a
        # proxy for the top-level invariant rather than the invariant
        # itself. The startswith/endswith assertions are untouched; those
        # are the ones that actually prove the single-top-level-element
        # invariant.
        rendered = config_page.runway_fieldset("3")
        if not rendered.startswith('<div class="theme-status"'):
            return False, "expected runway_fieldset() to start with a single <div class=\"theme-status\"> wrapper"
        if not rendered.endswith("</div>"):
            return False, "expected runway_fieldset() to end with the wrapper's matching </div>"
        if rendered.count("<div") != 2 or rendered.count("</div>") != 2:
            return False, "expected exactly two div pairs - the top-level .theme-status wrapper and the nested .runway-row layout container"
        return True, ""
    check(
        "runway_fieldset() returns exactly two div pairs - the top-level .theme-status wrapper and the nested .runway-row layout container, not five flat siblings (D-01)",
        _runway_fieldset_returns_single_top_level_div)

    def _runway_row_starts_after_caption_and_nothing_follows_it():
        # quick task 260901-re6: inverted from the pre-merge version of
        # this check (which asserted a trailing helper paragraph rendered
        # AFTER .runway-row closed). Now asserts RUNWAY_SECTION_CAPTION
        # renders BEFORE .runway-row opens, and that no <p element
        # appears anywhere after the row closes inside the wrapper — the
        # actual proof the second paragraph is gone, not merely moved.
        rendered = config_page.runway_fieldset("3")
        caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        row_open = '<div class="runway-row">'
        if rendered.count(row_open) != 1:
            return False, "expected exactly one <div class=\"runway-row\"> opening tag, got %d" % rendered.count(row_open)
        caption_pos = rendered.index(caption)
        row_start = rendered.index(row_open)
        if caption_pos >= row_start:
            return False, "expected RUNWAY_SECTION_CAPTION to render before .runway-row opens"
        row_close = rendered.index("</div>", row_start)
        card_positions = [m.start() for m in re.finditer(r'<label class="runway-card', rendered)]
        if len(card_positions) != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % len(card_positions)
        if not all(row_start < pos < row_close for pos in card_positions):
            return False, "expected all three runway-card labels to fall inside the .runway-row container"
        after_row = rendered[row_close + len("</div>"):]
        if "<p" in after_row:
            return False, "expected no <p element anywhere after .runway-row closes - the retired trailing helper paragraph must be gone, not merely moved"
        return True, ""
    check(
        "runway_fieldset() renders RUNWAY_SECTION_CAPTION before .runway-row opens, and no <p element after .runway-row closes (quick task 260901-re6)",
        _runway_row_starts_after_caption_and_nothing_follows_it)

    def _theme_and_runway_section_captions_appear_exactly_once():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        theme_caption = escape_html(config_page.THEME_SECTION_CAPTION)
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        if rendered.count(theme_caption) != 1:
            return False, "expected THEME_SECTION_CAPTION exactly once, got %d" % rendered.count(theme_caption)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once, got %d" % rendered.count(runway_caption)
        return True, ""
    check(
        "render() carries THEME_SECTION_CAPTION and RUNWAY_SECTION_CAPTION exactly once each (quick task 260901-re6)",
        _theme_and_runway_section_captions_appear_exactly_once)

    def _each_group_emits_exactly_one_caption_between_heading_and_control():
        # quick task 260901-re6 Task 3: the direct proof of the merge and
        # of the position — the check that would have caught this bug.
        # Calls theme_fieldset()/runway_fieldset()/led_group() directly
        # and asserts each returns markup with exactly one <p occurrence
        # and exactly one section-caption occurrence, with the caption's
        # index falling after the group's own naming element and before
        # the group's control.
        #
        # 06.6.4.1.1-05: theme_fieldset("black") (any valid theme id —
        # "sky" no longer exists post-merge of origin/main) now returns
        # the D-01 chip-grid branch, named by the same <h2 class=
        # "text-heading"> element runway_fieldset()/led_group() already
        # use — its control marker is "theme-chip-grid", not the retired
        # radio-list's bare "options" skip-marker.
        theme_rendered = config_page.theme_fieldset("black")
        runway_rendered = config_page.runway_fieldset("3")
        led_rendered = config_page.led_group(True)
        groups = (
            ("theme_fieldset()", theme_rendered, "</h2>", "theme-chip-grid"),
            ("runway_fieldset()", runway_rendered, "</h2>", "runway-row"),
            ("led_group()", led_rendered, "</h2>", "settings-checkbox"),
        )
        for name, rendered, heading_close_marker, control_marker in groups:
            if rendered.count("<p") != 1:
                return False, "expected %s to emit exactly one <p element, got %d" % (name, rendered.count("<p"))
            if rendered.count("section-caption") != 1:
                return False, "expected %s to emit exactly one section-caption occurrence, got %d" % (name, rendered.count("section-caption"))
            heading_close = rendered.index(heading_close_marker)
            caption_pos = rendered.index("section-caption")
            if not (heading_close < caption_pos):
                return False, "expected %s's caption to fall after %s" % (name, heading_close_marker)
            if control_marker not in rendered:
                return False, "expected %s's control marker %r to be present" % (name, control_marker)
            control_pos = rendered.index(control_marker)
            if not (caption_pos < control_pos):
                return False, "expected %s's caption to fall before its control (%r)" % (name, control_marker)
        return True, ""
    check(
        "theme_fieldset()/runway_fieldset()/led_group() each emit exactly one section-caption <p> element, positioned after the group's own naming element and before its control (quick task 260901-re6, merge of origin/main)",
        _each_group_emits_exactly_one_caption_between_heading_and_control)

    def _bottom_save_button_carries_static_fallback_attr():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR) != 1:
            return False, (
                "expected exactly one data-static-save-fallback occurrence, got %d"
                % rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR))
        button_match = re.search(
            r'<button\b[^>]*%s[^>]*>Save settings</button>'
            % re.escape(config_page.STATIC_SAVE_FALLBACK_ATTR), rendered)
        if not button_match:
            return False, "expected the fallback attribute on a type=\"submit\" Save settings button"
        if 'type="submit"' not in button_match.group(0):
            return False, "expected the fallback button to carry type=\"submit\""
        return True, ""
    check(
        "render()'s bottom Save settings button carries data-static-save-fallback exactly once (D-04)",
        _bottom_save_button_carries_static_fallback_attr)

    def _section_captions_appear_escaped_verbatim_exactly_once():
        # quick task 260901-re6: retargeted onto all three merged caption
        # constants, strengthened from "is present" to "appears exactly
        # once" for each. quick task 260901-s5o: widened in place to a
        # fourth constant, POLL_SECTION_CAPTION - same check, same
        # assertion shape, one more constant, no new check added.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        theme_caption = escape_html(config_page.THEME_SECTION_CAPTION)
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        led_caption = escape_html(config_page.LED_SECTION_CAPTION)
        poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
        if rendered.count(theme_caption) != 1:
            return False, "expected THEME_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(theme_caption)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(runway_caption)
        if rendered.count(led_caption) != 1:
            return False, "expected LED_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(led_caption)
        if rendered.count(poll_caption) != 1:
            return False, "expected POLL_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(poll_caption)
        return True, ""
    check(
        "the theme, runway, LED, and poll section captions all appear escaped-verbatim exactly once in render()'s output (quick task 260901-re6, quick task 260901-s5o)",
        _section_captions_appear_escaped_verbatim_exactly_once)

    def _current_theme_and_runway_are_selected():
        # merge of origin/main (Phase 8): the Runway assertions below
        # predate this merge and are unaffected by it.
        #
        # 06.6.4.1.1-05: Theme's chip radio now carries
        # class="visually-hidden" between value= and checked — the same
        # attribute sequence Runway's own card markup already uses — so
        # the needle grows the intervening class attribute compared to
        # the retired bare radio-list markup.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "06-24"},
            "poll_cooldown_remaining": 0,
        })
        if 'value="06-24" class="visually-hidden" checked' not in rendered:
            return False, "expected the non-default saved runway (06-24) to be marked selected"
        if 'value="3" class="visually-hidden" checked' in rendered:
            return False, "expected runway 3 (not the saved value) to NOT be marked selected"
        if rendered.count("runway-card--selected") != 1:
            return False, "expected exactly one runway-card--selected modifier"
        if 'value="black" class="visually-hidden" checked' not in rendered:
            return False, "expected the saved theme (black) to be marked selected via its radio input"
        if rendered.count("theme-chip--selected") != 1:
            return False, "expected exactly one theme-chip--selected modifier"
        return True, ""
    check(
        "the currently-saved theme is shown current and the (non-default) saved runway card is the one marked selected",
        _current_theme_and_runway_are_selected)

    def _poll_trigger_enabled_at_zero_cooldown():
        rendered = config_page.poll_trigger_section(0)
        # UXA-15 (06.6.2-02): scoped to the <button ...> tag itself, not
        # a bare substring search — the zero-cooldown branch's own
        # submit-affordance script now legitimately contains the word
        # "disabled" as a JS property name (`btn.disabled = true;`),
        # which a whole-document substring check would false-positive
        # on.
        button_tag = re.search(r"<button\b[^>]*>", rendered)
        if not button_tag:
            return False, "expected a <button> tag to extract"
        if "disabled" in button_tag.group(0):
            return False, "expected no disabled attribute at zero cooldown"
        if "Trigger poll now" not in rendered:
            return False, "expected the Trigger poll now button copy"
        return True, ""
    check(
        "poll_trigger_section(0) renders an enabled button",
        _poll_trigger_enabled_at_zero_cooldown)

    def _poll_trigger_disabled_with_remaining_seconds():
        rendered = config_page.poll_trigger_section(17)
        if "disabled" not in rendered:
            return False, "expected a disabled attribute at a non-zero cooldown"
        if "17" not in rendered:
            return False, "expected the remaining-seconds figure (17) in the visible copy"
        return True, ""
    check(
        "poll_trigger_section(17) renders a disabled button and the remaining-seconds copy",
        _poll_trigger_disabled_with_remaining_seconds)

    def _poll_section_caption_renders_on_both_branches_under_the_heading():
        # quick task 260901-s5o: the Poll section's own new caption check
        # — the group Task 1's non-goal explicitly excludes from
        # _each_group_emits_exactly_one_caption_between_heading_and_control()
        # (Poll's heading lives in render(), not in poll_trigger_section(),
        # and its disabled branch legitimately emits a second <p>).
        poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
        for cooldown_remaining in (0, 17):
            rendered = config_page.poll_trigger_section(cooldown_remaining)
            if rendered.count("section-caption") != 1:
                return False, (
                    "expected poll_trigger_section(%d) to emit exactly one "
                    "section-caption occurrence, got %d"
                    % (cooldown_remaining, rendered.count("section-caption")))
            if rendered.count(poll_caption) != 1:
                return False, (
                    "expected poll_trigger_section(%d) to carry "
                    "POLL_SECTION_CAPTION escaped-verbatim exactly once, got %d"
                    % (cooldown_remaining, rendered.count(poll_caption)))
            caption_pos = rendered.index("section-caption")
            trigger_pos = rendered.index('<form method="post" action="/poll-now">')
            if not caption_pos < trigger_pos:
                return False, (
                    "expected poll_trigger_section(%d)'s caption to precede "
                    "the poll-trigger form" % cooldown_remaining)

        # The render()-level position proof: the heading is emitted by
        # render(), the caption by poll_trigger_section() — two different
        # functions whose relative order nothing else guards.
        page = config_page.render({
            "device_config": {
                "theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if page.count(poll_caption) != 1:
            return False, (
                "expected render() to carry POLL_SECTION_CAPTION "
                "escaped-verbatim exactly once, got %d" % page.count(poll_caption))
        heading_pos = page.index('<h2 class="text-heading">Poll</h2>')
        page_caption_pos = page.index(poll_caption)
        poll_now_pos = page.index('action="/poll-now"')
        if not heading_pos < page_caption_pos < poll_now_pos:
            return False, (
                "expected the Poll caption to fall between the Poll <h2> "
                "heading and the poll-trigger form's action attribute")
        return True, ""
    check(
        "poll_trigger_section() emits POLL_SECTION_CAPTION exactly once on both the enabled and disabled branches, before the poll-trigger form, and render() places it directly under the Poll <h2> heading (quick task 260901-s5o)",
        _poll_section_caption_renders_on_both_branches_under_the_heading)

    def _poll_trigger_live_countdown_seeded_from_server_value():
        # D-01: the disabled branch must ship exactly one inline <script>,
        # carrying id="poll-trigger-btn"/id="poll-cooldown-text", the
        # unchanged server-rendered no-JS copy, and every value the
        # script needs emitted through config_page._js_literal() — never
        # a hardcoded quoted string, so this check stays correct if the
        # id/token constants are ever changed deliberately.
        d17 = config_page.poll_trigger_section(17)
        d5 = config_page.poll_trigger_section(5)
        z = config_page.poll_trigger_section(0)

        if d17.count("<script") != 1:
            return False, "expected exactly one <script occurrence at cooldown=17, got %d" % d17.count("<script")
        # UXA-15 (06.6.2-02): the zero-cooldown branch now legitimately
        # ships its own, different <script> (the submit-affordance
        # script, _poll_submit_script()) — no longer zero. Distinguish
        # it from the countdown script by absence of countdown-only
        # markers.
        if z.count("<script") != 1:
            return False, "expected exactly one <script occurrence at cooldown=0 (the submit-affordance script), got %d" % z.count("<script")
        if "setInterval" in z or "removeAttribute" in z:
            return False, "expected the zero-cooldown script to be the submit-affordance script, not the countdown script"
        if ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) not in d17:
            return False, "expected the button's id attribute"
        if ('id="%s"' % config_page.POLL_COOLDOWN_TEXT_ID) not in d17:
            return False, "expected the paragraph's id attribute"

        visible_copy = escape_html(
            config_page.POLL_COOLDOWN_HELPER_TEXT.format(n=17))
        if visible_copy not in d17:
            return False, "expected the unchanged, server-rendered no-JS copy"

        body17_match = re.search(r"<script>(.*?)</script>", d17, re.S)
        if not body17_match:
            return False, "expected a <script>...</script> body to extract"
        body17 = body17_match.group(1)

        expected_literals = [
            config_page._js_literal(17),
            config_page._js_literal(config_page.POLL_TRIGGER_BUTTON_ID),
            config_page._js_literal(config_page.POLL_COOLDOWN_TEXT_ID),
            config_page._js_literal(config_page.POLL_COOLDOWN_TEMPLATE_TOKEN),
            config_page._js_literal(
                config_page.POLL_COOLDOWN_HELPER_TEXT.format(
                    n=config_page.POLL_COOLDOWN_TEMPLATE_TOKEN)),
        ]
        for literal in expected_literals:
            if literal not in body17:
                return False, "expected seeded literal %r in the script body" % (literal,)

        body5_match = re.search(r"<script>(.*?)</script>", d5, re.S)
        if not body5_match:
            return False, "expected a <script>...</script> body to extract at cooldown=5"
        body5 = body5_match.group(1)
        if body5 == body17:
            return False, "expected a different seed to produce a different script body"
        if config_page._js_literal(5) not in body5:
            return False, "expected the seed to come from the argument (5), not a hardcoded value"

        if "</" in config_page._js_literal("</script>"):
            return False, "expected _js_literal() to break the script-closing sequence"

        return True, ""
    check(
        "poll_trigger_section() ships a live countdown script on the disabled branch, seeded exclusively via _js_literal(), and a different submit-affordance script on the zero-cooldown branch (D-01, UXA-15)",
        _poll_trigger_live_countdown_seeded_from_server_value)

    def _poll_trigger_zero_cooldown_ships_submit_affordance_script():
        # UXA-15 (06.6.2-02): supersedes the pre-existing "no script at
        # zero cooldown" regression guard this check used to assert —
        # that invariant is no longer true by design. Pins the new one
        # instead: poll_trigger_section(0) carries id="poll-trigger-btn"
        # and exactly one <script> (the submit-affordance script, not
        # the countdown script), while poll_trigger_section(30)'s own
        # pre-existing _poll_cooldown_script() output stays unchanged.
        rendered = config_page.poll_trigger_section(0)
        if "Trigger poll now" not in rendered:
            return False, "expected the Trigger poll now button copy"
        # Scoped to the <button ...> tag, not a bare substring search —
        # see _poll_trigger_enabled_at_zero_cooldown()'s own comment on
        # why (_poll_submit_script()'s body legitimately contains
        # "disabled" as a JS property name).
        button_tag = re.search(r"<button\b[^>]*>", rendered)
        if not button_tag:
            return False, "expected a <button> tag to extract"
        if "disabled" in button_tag.group(0):
            return False, "expected no disabled attribute at zero cooldown"
        if ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) not in rendered:
            return False, "expected the button's id attribute"
        if rendered.count("<script") != 1:
            return False, "expected exactly one <script occurrence at zero cooldown"
        if "setInterval" in rendered or "removeAttribute" in rendered:
            return False, "expected the zero-cooldown script to be the submit-affordance script, not the countdown script"

        nonzero = config_page.poll_trigger_section(30)
        if config_page._poll_cooldown_script(30) not in nonzero:
            return False, (
                "expected poll_trigger_section(30) to still carry its own "
                "pre-existing _poll_cooldown_script() output unchanged")
        return True, ""
    check(
        "poll_trigger_section(0) ships id=\"poll-trigger-btn\" and exactly one <script> (the UXA-15 submit-affordance script), while poll_trigger_section(30) still carries its unchanged countdown script",
        _poll_trigger_zero_cooldown_ships_submit_affordance_script)

    # The whole forbidden-sink family in one place, so a future reader
    # can see it at a glance (06.5-01-PLAN.md's own sink-safety gate for
    # companion/static/battery-trend.js established this pattern first).
    _FORBIDDEN_SCRIPT_SINKS = (
        "innerHTML", "outerHTML", "insertAdjacentHTML",
        "document.write", "eval(", "fetch(", "XMLHttpRequest",
    )
    _REQUIRED_SCRIPT_OPERATIONS = (
        "use strict", "textContent", "removeAttribute",
        "setInterval", "clearInterval",
    )

    def _poll_cooldown_script_has_no_forbidden_sink():
        rendered = config_page.poll_trigger_section(17)
        body_match = re.search(r"<script>(.*?)</script>", rendered, re.S)
        if not body_match:
            return False, "expected a <script>...</script> body to extract"
        body = body_match.group(1)
        for forbidden in _FORBIDDEN_SCRIPT_SINKS:
            if forbidden in body:
                return False, "forbidden sink found in the inline script: %r" % (forbidden,)
        for required in _REQUIRED_SCRIPT_OPERATIONS:
            if required not in body:
                return False, "expected required operation %r in the inline script" % (required,)
        return True, ""
    check(
        "the inline countdown script contains none of the forbidden HTML-writing/eval/network sinks and does contain strict mode plus the permitted DOM/timer operations",
        _poll_cooldown_script_has_no_forbidden_sink)

    def _poll_submit_script_has_no_forbidden_sink():
        rendered = config_page.poll_trigger_section(0)
        body_match = re.search(r"<script>(.*?)</script>", rendered, re.S)
        if not body_match:
            return False, "expected a <script>...</script> body to extract"
        body = body_match.group(1)
        for forbidden in _FORBIDDEN_SCRIPT_SINKS:
            if forbidden in body:
                return False, "forbidden sink found in the inline script: %r" % (forbidden,)
        if config_page._js_literal(config_page.POLL_TRIGGER_BUTTON_ID) not in body:
            return False, "expected the button id to be seeded via _js_literal(), not hardcoded"
        if config_page._js_literal(config_page.POLL_SUBMIT_PENDING_TEXT) not in body:
            return False, "expected the pending-label text to be seeded via _js_literal(), not hardcoded"
        if "use strict" not in body:
            return False, "expected strict mode"
        if "addEventListener" not in body:
            return False, "expected a submit event listener"
        return True, ""
    check(
        "the inline submit-affordance script contains none of the forbidden HTML-writing/eval/network sinks, seeds every interpolated value via _js_literal(), and attaches a submit listener (UXA-15)",
        _poll_submit_script_has_no_forbidden_sink)

    def _valid_save_writes_both_and_returns_saved_key():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "black", "tracked_runway": "06-24"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            # 06.6.4.1 (D-05): led_enabled is now resolved by handle_post()
            # itself, with checkbox-absent-means-False semantics (never
            # carried forward like theme/runway) — this posted form omits
            # led_enabled entirely, so the persisted value is False, not
            # DEFAULT_LED_ENABLED (True). The theme value itself is
            # "black", matching what the fixture above actually posted —
            # pre-merge this assertion read "sky" because "black" wasn't
            # yet a valid THEME_IDS entry and handle_post()'s validation
            # silently kept the prior/default value instead; the merged
            # Phase 8 registry (19 real entries) makes "black" valid, so
            # it now persists as posted.
            if on_disk != {"theme": "black", "tracked_runway": "06-24", "led_enabled": False, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": False}:
                return False, "on-disk config does not match the posted values: %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a valid theme and runway writes both and returns the saved flash key",
        _valid_save_writes_both_and_returns_saved_key)

    def _nonmember_theme_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "not-a-real-theme", "tracked_runway": "06-24"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member theme writes nothing and returns the save-failure flash key",
        _nonmember_theme_writes_nothing)

    def _nonmember_runway_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "black", "tracked_runway": "not-a-real-runway"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member runway writes nothing and returns the save-failure flash key",
        _nonmember_runway_writes_nothing)

    def _theme_only_post_carries_runway_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "black"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a theme but no runway field carries the existing runway forward unchanged",
        _theme_only_post_carries_runway_forward)

    def _path_traversal_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "../../etc/passwd", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a path-traversal-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a directory-traversal-shaped theme value is rejected by the membership test",
        _path_traversal_theme_rejected)

    def _sql_fragment_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky'; DROP TABLE flights; --", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a SQL-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a SQL-fragment-shaped theme value is rejected by the membership test",
        _sql_fragment_theme_rejected)

    def _save_oserror_returns_failure_key_not_raise():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            original_save = device_config.save_device_config

            def _raising_save(*args, **kwargs):
                raise OSError("simulated disk failure")

            device_config.save_device_config = _raising_save
            try:
                flash_key = config_page.handle_post(
                    {"theme": "black", "tracked_runway": "3"}, ctx)
            finally:
                device_config.save_device_config = original_save
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED when save_device_config() raises OSError, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a save that raises OSError returns the save-failure flash key rather than propagating",
        _save_oserror_returns_failure_key_not_raise)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 2 (D-05): handle_post() absorbs LED validation as one
    # all-or-nothing submission — one check per <behavior> bullet.
    # ------------------------------------------------------------------

    # merge of origin/main (Phase 8): main's own version of this section
    # still tested the pre-06.6.4.1-07 dual-form architecture —
    # led_fieldset() as a standalone function, and a second, distinct
    # <form action="/config-led"> — because main never received that
    # plan's LED-into-the-single-Settings-form merge (see that plan's own
    # SUMMARY: "the 8 checks exercising the now-deleted led_fieldset()/
    # led_section()/handle_led_post() were deleted outright ... 1 new
    # check pins the retired /config-led route now 404s"). Those three
    # functions (_led_fieldset_checked_true, _led_fieldset_unchecked_false,
    # _render_has_second_form_for_led_route) tested functions/routes that
    # no longer exist on this side and are dropped, not reconciled — this
    # is the same retirement 06.6.4.1-07 already made, main just hadn't
    # merged it yet. The unified-form behaviour they were partially
    # re-covering is already exercised by the bullet-per-behaviour checks
    # below (_handle_post_empty_form_persists_led_false and its
    # siblings), so no coverage gap is left behind.
    def _handle_post_empty_form_persists_led_false():
        # Bullet 1: the shape a browser sends when nothing is checked and
        # nothing is selected.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected led_enabled False on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({}, ctx) - the shape a browser sends when nothing is checked and nothing is selected - persists led_enabled False and returns the saved flash key",
        _handle_post_empty_form_persists_led_false)

    def _handle_post_led_checkbox_value_persists_led_true():
        # Bullet 2.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"led_enabled": config_page.LED_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not True:
                return False, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True",
        _handle_post_led_checkbox_value_persists_led_true)

    def _handle_post_crafted_led_value_rejected_byte_identical():
        # Bullet 3.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3", led_enabled=True)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"led_enabled": "<crafted>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"led_enabled\": \"<crafted>\"}, ctx) returns the save-failed flash key and leaves device_config.json byte-identical",
        _handle_post_crafted_led_value_rejected_byte_identical)

    def _handle_post_invalid_theme_rejects_led_half_too():
        # Bullet 4: an invalid theme rejects the LED half too - proving
        # the merge stays all-or-nothing across all three fields.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3", led_enabled=False)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "not-a-real-theme", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"theme\": \"<not a registered theme>\", \"led_enabled\": LED_CHECKBOX_VALUE}, ctx) returns save-failed and leaves the file byte-identical (an invalid theme rejects the LED half too)",
        _handle_post_invalid_theme_rejects_led_half_too)

    def _handle_post_valid_runway_and_led_persist_together_one_call():
        # Bullet 5: persists both in one call.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"tracked_runway": "06-24", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected tracked_runway 06-24 on disk, got %r" % (on_disk["tracked_runway"],)
            if on_disk["led_enabled"] is not True:
                return False, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"tracked_runway\": <a real runway id>, \"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists both in one call and returns the saved flash key",
        _handle_post_valid_runway_and_led_persist_together_one_call)

    # ------------------------------------------------------------------
    # 10-05-PLAN.md Task 3: handle_post()'s quiet-hours save/reject paths
    # (D-03/D-04, 10-UI-SPEC.md's unchecked-checkbox-still-saves-times
    # semantics — the resolution of 10-RESEARCH.md Assumption A1).
    # ------------------------------------------------------------------

    def _handle_post_quiet_hours_checkbox_on_persists_all_three():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "quiet_hours_enabled": config_page.QUIET_HOURS_CHECKBOX_VALUE,
                    "quiet_hours_start": "22:30", "quiet_hours_end": "06:15",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_enabled"] is not True:
                return False, "expected quiet_hours_enabled True on disk, got %r" % (on_disk["quiet_hours_enabled"],)
            if on_disk["quiet_hours_start"] != "22:30" or on_disk["quiet_hours_end"] != "06:15":
                return False, "expected the submitted times to persist, got %r/%r" % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"])
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with quiet_hours_enabled=QUIET_HOURS_CHECKBOX_VALUE and both times persists all three quiet-hours fields and returns the saved flash key",
        _handle_post_quiet_hours_checkbox_on_persists_all_three)

    def _handle_post_quiet_hours_checkbox_absent_still_persists_times():
        # The direct pin of 10-UI-SPEC.md's resolution of 10-RESEARCH.md
        # Assumption A1 / Open Question 2: a user can pre-configure a
        # window before ever turning it on. Must not be dropped or
        # inverted.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"quiet_hours_start": "22:30", "quiet_hours_end": "06:15"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_enabled"] is not False:
                return False, "expected quiet_hours_enabled False on disk (checkbox absent), got %r" % (on_disk["quiet_hours_enabled"],)
            if on_disk["quiet_hours_start"] != "22:30" or on_disk["quiet_hours_end"] != "06:15":
                return False, "expected the edited times to persist even though the checkbox was left unchecked, got %r/%r" % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"])
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with quiet_hours_enabled absent but both times submitted persists quiet_hours_enabled False and the edited times (a user can pre-configure a window before enabling it)",
        _handle_post_quiet_hours_checkbox_absent_still_persists_times)

    def _handle_post_malformed_quiet_hours_time_rejected_byte_identical():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"quiet_hours_start": "24:00"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a malformed HH:MM, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"quiet_hours_start\": \"24:00\"}, ctx) against a legitimately-saved config returns the save-failed flash key and leaves device_config.json byte-identical",
        _handle_post_malformed_quiet_hours_time_rejected_byte_identical)

    def _handle_post_crafted_quiet_hours_checkbox_value_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"quiet_hours_enabled": "yes"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted quiet_hours_enabled value, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"quiet_hours_enabled\": \"yes\"}, ctx) returns the save-failed flash key, matching the LED field's own third shape",
        _handle_post_crafted_quiet_hours_checkbox_value_rejected)

    def _handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "quiet_hours_end": "24:00"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical (the theme must not persist either), it changed"
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme"] != "black":
                return False, "expected the pre-existing theme to be unchanged, got %r" % (on_disk["theme"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a valid theme AND a malformed quiet_hours_end returns save-failed and persists neither — the theme on disk is unchanged (all-or-nothing across groups)",
        _handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing)

    # ------------------------------------------------------------------
    # 11-03-PLAN.md Task 2: handle_post()'s wake_interval_s conversion,
    # rejection, and leave-unchanged checks (D-05, 11-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _handle_post_wake_interval_string_converts_to_int_and_persists():
        # The direct regression guard for 11-RESEARCH.md Pitfall 1: a
        # stored string would round-trip through load_device_config() as
        # None (normalise_wake_interval_s() rejects non-int values) and
        # silently look like "unset" instead of like a bug — asserting
        # isinstance(..., int) explicitly is what catches that.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if not isinstance(on_disk["wake_interval_s"], int):
                return False, "expected the submitted string \"120\" to convert to an int, got %r" % (on_disk["wake_interval_s"],)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s 120 on disk, got %r" % (on_disk["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"wake_interval_s\": \"120\"}, ctx) explicitly string-to-int converts before persisting, stores the int (not a string) 120, and returns the saved flash key (11-RESEARCH.md Pitfall 1 regression guard)",
        _handle_post_wake_interval_string_converts_to_int_and_persists)

    def _handle_post_wake_interval_rejection_paths_byte_identical():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if seed_flash != config_page.FLASH_SAVED:
                return False, "expected the seeding save to succeed, got %r" % (seed_flash,)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            # "abc"/"1.5" fail at this handler's own int() gate; "59"/
            # "3601"/"-1" are syntactically valid ints but fail inside
            # save_device_config()'s bounded-range check.
            for bad in ("abc", "1.5", "59", "3601", "-1"):
                flash_key = config_page.handle_post({"wake_interval_s": bad}, ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for wake_interval_s=%r, got %r" % (bad, flash_key)
                if before != after:
                    return False, "expected device_config.json to stay byte-identical after rejecting wake_interval_s=%r" % (bad,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post rejects \"abc\"/\"1.5\" (handler's int() gate) and \"59\"/\"3601\"/\"-1\" (save_device_config()'s bounded-range check), each returning the save-failed flash key and leaving a pre-existing device_config.json byte-identical",
        _handle_post_wake_interval_rejection_paths_byte_identical)

    def _handle_post_wake_interval_empty_or_absent_leaves_unchanged():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if seed_flash != config_page.FLASH_SAVED:
                return False, "expected the seeding save to succeed, got %r" % (seed_flash,)
            empty_flash = config_page.handle_post({"wake_interval_s": ""}, ctx)
            if empty_flash != config_page.FLASH_SAVED:
                return False, "expected an empty-string wake_interval_s to succeed (leave unchanged), got %r" % (empty_flash,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s to remain 120 after an empty-string submission, got %r" % (on_disk["wake_interval_s"],)
            absent_flash = config_page.handle_post({}, ctx)
            if absent_flash != config_page.FLASH_SAVED:
                return False, "expected an absent wake_interval_s key to succeed (leave unchanged), got %r" % (absent_flash,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s to remain 120 after an absent-key submission, got %r" % (on_disk["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "after a save that stored wake_interval_s 120, a later submission with wake_interval_s as the empty string, and another with the key absent entirely, both return the saved flash key and leave the stored value at 120 (11-RESEARCH.md Open Question 2)",
        _handle_post_wake_interval_empty_or_absent_leaves_unchanged)

    # ------------------------------------------------------------------
    # 06.6.4.1-07 (D-05): led_fieldset()/led_section()/handle_led_post()
    # and the separate POST /config-led route were retired outright —
    # the eight checks that used to exercise them directly were deleted
    # here (they would now raise AttributeError against the deleted
    # symbols). Their coverage is superseded, not lost: the merged
    # led_group()/handle_post() checks above (D-05 handle_post() bullets)
    # and _render_shape_read_only_theme_runway_cards_led_group_and_save_button()
    # near the top of this file already cover the same three submitted-
    # value shapes, the cross-field all-or-nothing rejection, and the
    # single-heading-level/no-<fieldset> markup contract.
    # ------------------------------------------------------------------

    def _render_has_no_action_pointing_at_retired_led_route():
        # 06.6.4.1 (D-05), retired route confirmed 06.6.4.1-07: the LED
        # group is merged into the single settings form — render() must
        # never emit a second, independently-submittable
        # <form action="/config-led"> at all. The separate POST
        # /config-led route and its handler no longer exist anywhere in
        # the app, so this is now a pure markup regression guard.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'action="%s"' % config_page.SETTINGS_ROUTE not in rendered:
            return False, "expected the settings form action to be present"
        if 'action="/config-led"' in rendered:
            return False, "expected no action=\"/config-led\" in render()'s output (D-05 merge)"
        return True, ""
    check(
        "render() emits no action pointing at the retired separate LED form path (D-05)",
        _render_has_no_action_pointing_at_retired_led_route)

    def _config_page_exposes_no_retired_led_symbols():
        # 06.6.4.1-07 (D-05): source assertion that the deleted handler,
        # section wrapper, and markup builder are genuinely gone, not
        # merely unreferenced.
        for name in ("led_fieldset", "led_section", "handle_led_post"):
            if hasattr(config_page, name):
                return False, "expected config_page to expose no %r attribute" % name
        return True, ""
    check(
        "companion.pages.config_page exposes neither led_fieldset, led_section, nor "
        "handle_led_post (all three retired, D-05)",
        _config_page_exposes_no_retired_led_symbols)

    def _config_page_exposes_no_retired_helper_or_description_symbols():
        # quick task 260901-re6 Task 3: source assertion that the five
        # constants retired by Task 1 (THEME_HELPER_TEXT,
        # THEME_SECTION_DESCRIPTION, RUNWAY_HELPER_TEXT,
        # RUNWAY_SECTION_DESCRIPTION, LED_HELPER_TEXT) are genuinely gone,
        # not merely unreferenced — same precedent
        # _config_page_exposes_no_retired_led_symbols() above set for the
        # 06.6.4.1-07 LED-route retirement.
        retired = (
            "THEME_HELPER_TEXT", "THEME_SECTION_DESCRIPTION",
            "RUNWAY_HELPER_TEXT", "RUNWAY_SECTION_DESCRIPTION",
            "LED_HELPER_TEXT")
        for name in retired:
            if hasattr(config_page, name):
                return False, "expected config_page to expose no %r attribute" % name
        return True, ""
    check(
        "companion.pages.config_page exposes none of THEME_HELPER_TEXT/THEME_SECTION_DESCRIPTION/"
        "RUNWAY_HELPER_TEXT/RUNWAY_SECTION_DESCRIPTION/LED_HELPER_TEXT (all five retired, quick task 260901-re6)",
        _config_page_exposes_no_retired_helper_or_description_symbols)

    # ------------------------------------------------------------------
    # Runway-image existence detection (Task 1, D-03) - each check uses
    # its own tempfile.mkdtemp() image_dir and never touches the real
    # companion/static/ (06.4-RESEARCH.md Pitfall 1).
    # ------------------------------------------------------------------

    def _runway_images_available_empty_dir_yields_empty_set():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != set():
                return False, "expected an empty set for an empty directory, got %r" % (result,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() returns the empty set when the image directory has no files",
        _runway_images_available_empty_dir_yields_empty_set)

    def _runway_images_available_detects_single_present_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            with open(os.path.join(tmpdir, "runway-3.png"), "wb") as fh:
                fh.write(b"not-a-real-png-just-test-bytes")
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != {"3"}:
                return False, "expected {'3'}, got %r" % (result,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() returns exactly {'3'} when only runway-3.png exists",
        _runway_images_available_detects_single_present_file)

    def _runway_images_available_missing_dir_yields_empty_set_no_raise():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        nonexistent = os.path.join(tmpdir, "does-not-exist")
        shutil.rmtree(tmpdir, ignore_errors=True)
        result = companion_app.runway_images_available(image_dir=nonexistent)
        if result != set():
            return False, "expected an empty set for a non-existent directory, got %r" % (result,)
        return True, ""
    check(
        "runway_images_available() returns the empty set (does not raise) when image_dir does not exist",
        _runway_images_available_missing_dir_yields_empty_set_no_raise)

    def _runway_images_available_bounded_by_registry_not_directory_listing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            with open(os.path.join(tmpdir, "runway-99.png"), "wb") as fh:
                fh.write(b"not-a-registry-member")
            with open(os.path.join(tmpdir, "style.css"), "w") as fh:
                fh.write("/* not a runway image */")
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != set():
                return False, (
                    "expected an empty set (non-registry files must be ignored), got %r"
                    % (result,))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() ignores files that are not RUNWAY_IDS members, proving it is registry-bounded not directory-listing-bounded",
        _runway_images_available_bounded_by_registry_not_directory_listing)

    # ------------------------------------------------------------------
    # runway_fieldset() image emission (Task 2, D-01/D-03) - unit checks
    # against the string output only, no filesystem/subprocess involved.
    # ------------------------------------------------------------------

    def _runway_fieldset_emits_img_only_for_available_runway():
        rendered = config_page.runway_fieldset("3", {"3"})
        if rendered.count("<img") != 1:
            return False, "expected exactly one <img occurrence, got %d" % rendered.count("<img")
        if "/runway-image/3.png" not in rendered:
            return False, "expected the src to point at /runway-image/3.png"
        if "runway-image/06-24" in rendered or "runway-image/02-20" in rendered:
            return False, "expected no image reference for runways not in images_available"
        return True, ""
    check(
        "runway_fieldset(images_available={'3'}) emits exactly one <img, for runway 3 only",
        _runway_fieldset_emits_img_only_for_available_runway)

    def _runway_fieldset_graceful_fallback_no_images():
        rendered = config_page.runway_fieldset("3", set())
        if "<img" in rendered:
            return False, "expected zero <img occurrences with an empty images_available set"
        if rendered.count('name="tracked_runway"') != 3:
            return False, "expected all three runway radios still present"
        for runway_id in device_config.RUNWAY_IDS:
            if escape_html(device_config.runway_label(runway_id)) not in rendered:
                return False, "expected the label text for runway %r" % (runway_id,)
        return True, ""
    check(
        "runway_fieldset(images_available=set()) renders zero <img tags and all three number/heading labels (D-03 graceful fallback)",
        _runway_fieldset_graceful_fallback_no_images)

    def _render_forwards_ctx_runway_images_key():
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
            "runway_images": {"06-24"},
        })
        if "/runway-image/06-24.png" not in rendered:
            return False, "expected render() to forward ctx['runway_images'] into the <img> src"
        # 06.6.4.1.1-05: scoped to the runway-card image class specifically
        # — the page now also carries one theme-chip preview <img> per
        # THEME_IDS entry, so a bare "<img" count is no longer exclusive
        # to the runway picker.
        if rendered.count('<img class="runway-card__image"') != 1:
            return False, (
                "expected exactly one runway-card__image <img occurrence, got %d"
                % rendered.count('<img class="runway-card__image"'))
        return True, ""
    check(
        "render() forwards ctx['runway_images'] to runway_fieldset() rather than relying on the parameter default",
        _render_forwards_ctx_runway_images_key)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 3 (D-03, D-04, D-06): cross-file DOM-contract guards
    # between config_page.py's constants and the two static assets that
    # read them by literal value, dirty-state.js and style.css. Neither
    # static file imports this module — these checks are what keeps the
    # three in sync.
    # ------------------------------------------------------------------

    _STATIC_DIR = os.path.join(REPO_ROOT, "companion", "static")

    def _read_static(name):
        with open(os.path.join(_STATIC_DIR, name)) as fh:
            return fh.read()

    def _dirty_state_js_references_dirty_section_attr_and_has_no_forbidden_syntax():
        source = _read_static("dirty-state.js")
        if config_page.DIRTY_SECTION_ATTR not in source:
            return False, "expected dirty-state.js to reference the literal value of DIRTY_SECTION_ATTR"
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references config_page.DIRTY_SECTION_ATTR's literal value and contains none of innerHTML/let /const /=>/backtick",
        _dirty_state_js_references_dirty_section_attr_and_has_no_forbidden_syntax)

    def _style_css_references_static_save_fallback_attr():
        source = _read_static("style.css")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in source:
            return False, "expected style.css to reference the literal value of STATIC_SAVE_FALLBACK_ATTR"
        idx = source.index(config_page.STATIC_SAVE_FALLBACK_ATTR)
        window = source[idx:idx + 120]
        if "display: none" not in window and "display:none" not in window:
            return False, "expected the fallback-hide rule to set display: none near the attribute reference"
        return True, ""
    check(
        "style.css contains the .js-gated fallback-hide rule referencing config_page.STATIC_SAVE_FALLBACK_ATTR's literal value",
        _style_css_references_static_save_fallback_attr)

    def _style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors():
        # quick task 260901-qif: the third new cross-file guard - unlike
        # DIRTY_SECTION_ATTR/STATIC_SAVE_FALLBACK_ATTR above, no Python
        # constant carries these three class-name literals, so they are
        # asserted directly here. Same index-plus-window technique the
        # neighbouring guards use, never a regex CSS parser. Keeps
        # style.css's .theme-status/.runway-row/.settings-checkbox rules
        # from silently drifting out of sync with the markup
        # config_page.py's runway_fieldset()/led_group()/
        # quiet_hours_group() now emit. 10-05-PLAN.md Task 2 renamed the
        # third selector from .led-checkbox to .settings-checkbox.
        source = _read_static("style.css")

        if ".theme-status {" not in source:
            return False, "expected style.css to declare a .theme-status rule"
        idx = source.index(".theme-status {")
        window = source[idx:idx + 400]
        if "var(--color-dominant)" not in window:
            return False, "expected .theme-status's rule body to carry the --color-dominant card-surface token"
        if ".theme-status:hover" not in source:
            return False, "expected style.css to declare a .theme-status:hover selector"

        if ".runway-row {" not in source:
            return False, "expected style.css to declare a .runway-row rule"
        idx = source.index(".runway-row {")
        window = source[idx:idx + 200]
        if "display: flex" not in window:
            return False, "expected .runway-row's rule body to set display: flex"

        checkbox_selector = '.settings-checkbox input[type="checkbox"] {'
        if checkbox_selector not in source:
            return False, "expected style.css to declare a %r rule" % (checkbox_selector,)
        idx = source.index(checkbox_selector)
        window = source[idx:idx + 400]
        if "min-height: 0" not in window:
            return False, "expected .settings-checkbox input[type=\"checkbox\"]'s rule body to clear the global rule's min-height"

        # 06.6.4.1.1-05: the fourth cross-file guard, same index-plus-
        # window technique, covering the new .theme-chip* selectors
        # theme_fieldset()'s D-01 chip-grid markup now depends on.
        if ".theme-chip-grid {" not in source:
            return False, "expected style.css to declare a .theme-chip-grid rule"
        idx = source.index(".theme-chip-grid {")
        window = source[idx:idx + 200]
        if "display: flex" not in window:
            return False, "expected .theme-chip-grid's rule body to set display: flex"

        if ".theme-chip {" not in source:
            return False, "expected style.css to declare a .theme-chip rule"
        idx = source.index(".theme-chip {")
        window = source[idx:idx + 700]
        if "var(--color-dominant)" not in window:
            return False, "expected .theme-chip's rule body to carry the --color-dominant card-surface token"
        if "width: 160px" not in window:
            return False, "expected .theme-chip's rule body to set width: 160px"

        if ".theme-chip--selected {" not in source:
            return False, "expected style.css to declare a .theme-chip--selected rule"
        idx = source.index(".theme-chip--selected {")
        window = source[idx:idx + 100]
        if "var(--color-accent)" not in window:
            return False, "expected .theme-chip--selected's rule body to carry var(--color-accent)"

        if ".theme-chip__preview {" not in source:
            return False, "expected style.css to declare a .theme-chip__preview rule"
        idx = source.index(".theme-chip__preview {")
        window = source[idx:idx + 200]
        if "height: 56px" not in window:
            return False, "expected .theme-chip__preview's rule body to set height: 56px"
        return True, ""
    check(
        "style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex display), "
        '.settings-checkbox input[type="checkbox"] (cleared min-height), and .theme-chip-grid/.theme-chip/'
        ".theme-chip--selected/.theme-chip__preview (flex display, card surface + 160px width, accent border, "
        "56px preview band) - the selectors config_page.py's new markup depends on",
        _style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors)

    def _style_css_needs_no_new_selector_for_display_group():
        # 12-05-PLAN.md Task 2 bullet 5: a cross-file guard that style.css
        # needs no new selector for the Display group - both classes
        # display_group() depends on (.theme-status, .settings-checkbox)
        # are already declared above, matching led_group()'s/
        # quiet_hours_group()'s own precedent (12-UI-SPEC.md: zero new
        # selectors, zero new declarations, zero new design tokens).
        source = _read_static("style.css")
        if ".theme-status {" not in source:
            return False, "expected style.css to already declare a .theme-status rule"
        checkbox_selector = '.settings-checkbox input[type="checkbox"] {'
        if checkbox_selector not in source:
            return False, "expected style.css to already declare a %r rule" % (checkbox_selector,)
        return True, ""
    check(
        "style.css already declares .theme-status and .settings-checkbox - the Display group introduces zero new CSS selectors",
        _style_css_needs_no_new_selector_for_display_group)

    def _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
        # 06.6.4.1.1-05: the cross-module route contract — every chip's
        # <img src> is built from theme_preview.THEME_PREVIEW_ROUTE_PREFIX
        # (rebound as config_page.THEME_PREVIEW_ROUTE_PREFIX) plus the
        # theme's own registry id, asserted against the constant rather
        # than a re-typed literal, for every entry in THEME_IDS.
        rendered = config_page.theme_fieldset("white")
        for theme_id in device_config.THEME_IDS:
            expected_src = 'src="%s%s.png"' % (
                config_page.THEME_PREVIEW_ROUTE_PREFIX, escape_html(theme_id))
            if expected_src not in rendered:
                return False, "expected chip %r to carry %r" % (theme_id, expected_src)
        return True, ""
    check(
        "every theme chip's <img src> points at THEME_PREVIEW_ROUTE_PREFIX + the theme's own registry id, "
        "for every entry in device_config.THEME_IDS (06.6.4.1.1-05)",
        _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme)

    def _theme_chip_swatch_dots_carry_real_palette_hex_values():
        # 06.6.4.1.1-05: each chip carries exactly two .theme-chip__dot
        # spans whose inline background values are computed from
        # _palette_hex() against the theme's own departing_index/
        # arriving_index — real panel palette colours, never hardcoded.
        rendered = config_page.theme_fieldset("white")
        if rendered.count("theme-chip__dot") != len(device_config.THEME_IDS) * 2:
            return False, (
                "expected exactly %d .theme-chip__dot occurrences (2 per theme), got %d"
                % (len(device_config.THEME_IDS) * 2, rendered.count("theme-chip__dot")))
        for theme_id in device_config.THEME_IDS:
            theme = device_config.THEMES[theme_id]
            departing_hex = config_page._palette_hex(theme["departing_index"])
            arriving_hex = config_page._palette_hex(theme["arriving_index"])
            if ('theme-chip__dot" style="background:%s"' % departing_hex) not in rendered:
                return False, "expected theme %r's departing swatch dot to carry %r" % (theme_id, departing_hex)
            if ('theme-chip__dot" style="background:%s"' % arriving_hex) not in rendered:
                return False, "expected theme %r's arriving swatch dot to carry %r" % (theme_id, arriving_hex)
        return True, ""
    check(
        "every theme chip carries exactly two .theme-chip__dot swatches whose inline background values equal "
        "_palette_hex() computed from that theme's own departing_index/arriving_index (06.6.4.1.1-05)",
        _theme_chip_swatch_dots_carry_real_palette_hex_values)

    def _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
        # 06.6.4.1.1-05: the markup half of the CSS-only selection reveal
        # — every chip's radio is visually-hidden (never display:none, so
        # keyboard/no-JS selection keeps working natively), and every chip
        # carries a .theme-chip__check glyph with its visually-hidden
        # "Selected" text, present on all 16 chips regardless of which one
        # is actually selected.
        rendered = config_page.theme_fieldset("white")
        theme_count = len(device_config.THEME_IDS)
        if rendered.count('name="theme" value="') != theme_count:
            return False, "expected %d theme radios, got %d" % (theme_count, rendered.count('name="theme" value="'))
        if rendered.count('class="visually-hidden"') < theme_count:
            return False, "expected every chip's radio to carry class=\"visually-hidden\""
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('<span class="theme-chip__check">') != theme_count:
            return False, (
                "expected exactly %d .theme-chip__check occurrences (one per chip, regardless of selection), got %d"
                % (theme_count, rendered.count('<span class="theme-chip__check">')))
        if rendered.count('<span class="visually-hidden">Selected</span>') != theme_count:
            return False, "expected every chip's check glyph to carry the visually-hidden \"Selected\" text"
        return True, ""
    check(
        "every theme chip's radio carries class=\"visually-hidden\" (never display:none) and every chip carries a "
        ".theme-chip__check glyph with visually-hidden \"Selected\" text, present on all chips regardless of "
        "selection (06.6.4.1.1-05)",
        _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip)

    def _settings_page_has_zero_fieldsets_and_five_dirty_sections():
        # 06.6.4.1.1-05: the rendered Settings page contains no <fieldset
        # and no <legend anywhere — so dirty-state.js's section-aware walk
        # still finds Theme as one addressable unit after the rewrite.
        # merge of Phase 10/11: the data-dirty-section count is 5, not
        # 06.6.4.1.1-05's own 3 (Theme/Runway/Diagnostic LED), now that
        # Quiet hours and Wake interval each joined as a fourth and fifth
        # group — not a rename of this check's own premise.
        # 12-05-PLAN.md: the count is 6, not 5, now that Display joined as
        # the sixth and last group — again not a rename of this check's
        # own premise.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements on the rendered Settings page"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements on the rendered Settings page"
        if rendered.count(config_page.DIRTY_SECTION_ATTR) != 6:
            return False, (
                "expected exactly 6 %s occurrences (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display), got %d"
                % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))
        return True, ""
    check(
        "the rendered Settings page contains no <fieldset> and no <legend>, and exactly six "
        "data-dirty-section groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display)",
        _settings_page_has_zero_fieldsets_and_five_dirty_sections)

    def _selected_runway_card_and_theme_chip_carry_a_background_wash():
        # 06.6.4.1.1-06 (developer checkpoint follow-up): the developer
        # reported that, across the whole site, the selected element was
        # "very hard to see" — a border-only + check-glyph treatment was
        # too subtle at density. The fix adds a background wash matching
        # `.theme-form .theme-option--active`'s own established idiom
        # (color-mix(in srgb, var(--color-accent) 12%, transparent)) to
        # BOTH selectable-card components, alongside their existing
        # border and check glyph, not replacing either.
        source = _read_static("style.css")
        wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

        runway_selector = ".runway-card--selected {"
        if runway_selector not in source:
            return False, "expected style.css to still declare a .runway-card--selected rule"
        idx = source.index(runway_selector)
        window = source[idx:idx + 1600]
        if "border: 2px solid var(--color-accent);" not in window:
            return False, ".runway-card--selected must keep its existing 2px accent border"
        if wash not in window:
            return False, (
                "expected .runway-card--selected to carry the same 12%-accent background wash "
                ".theme-form .theme-option--active uses")

        # .theme-chip--selected itself must stay border-only (no
        # background) — the wash must be scoped to .theme-chip__body
        # only, so it never sits behind the rendered preview band and
        # tints it. Isolate this rule's own body precisely (up to its
        # closing brace), not an arbitrary fixed-size window, so a
        # background declared just after the rule can't false-positive.
        chip_selected_selector = ".theme-chip--selected {"
        if chip_selected_selector not in source:
            return False, "expected style.css to still declare a .theme-chip--selected rule"
        idx = source.index(chip_selected_selector) + len(chip_selected_selector)
        rule_body = source[idx:source.index("}", idx)]
        if "background:" in rule_body:
            return False, (
                "expected .theme-chip--selected itself to stay border-only — the wash must be "
                "scoped to .theme-chip__body, not the whole chip (which would tint the preview band)")

        theme_chip_body_selector = ".theme-chip--selected .theme-chip__body {"
        if theme_chip_body_selector not in source:
            return False, "expected style.css to declare a %r rule" % (theme_chip_body_selector,)
        idx = source.index(theme_chip_body_selector)
        window = source[idx:idx + 200]
        if wash not in window:
            return False, (
                "expected .theme-chip--selected .theme-chip__body to carry the same 12%-accent "
                "background wash .theme-form .theme-option--active uses")
        return True, ""
    check(
        "both .runway-card--selected and .theme-chip--selected .theme-chip__body carry a 12%-accent "
        "background wash (color-mix), matching .theme-form .theme-option--active's established active-state "
        "idiom, added alongside (not replacing) their existing border and check glyph (06.6.4.1.1-06)",
        _selected_runway_card_and_theme_chip_carry_a_background_wash)

    def _strong_selected_treatment_is_keyed_to_the_live_checked_radio():
        # quick task 260904-bbi: the developer found that the strong
        # "this is your selection" treatment followed the SAVED config,
        # not the user's LIVE choice, because every selected-state rule
        # keyed off the server-computed --selected class alone. This
        # check proves the strong treatment is now driven by live
        # :has(input:checked) state, inside a single
        # @supports selector(:has(*)) feature-query block, for BOTH
        # selectable-card components — and that the D-03a hover guard
        # (which would otherwise clear the newly-checked chip's border,
        # since it is keyed to :not(--selected) which still matches the
        # newly-checked-but-not-yet-saved chip) is answered with a
        # positive restore rule rather than a re-scoped guard.
        source = _read_static("style.css")

        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block, got %d" % (supports_marker, source.count(supports_marker)))
        supports_idx = source.index(supports_marker)

        wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

        def _rule_body(selector):
            if selector not in source:
                return None, "expected style.css to declare %r" % (selector,)
            idx = source.index(selector)
            if idx < supports_idx:
                return None, "expected %r to live inside the @supports selector(:has(*)) block" % (selector,)
            body = source[idx + len(selector):source.index("}", idx)]
            return body, ""

        # Theme chip: strong border, body wash, check glyph shown.
        body, err = _rule_body(".theme-chip:has(input:checked) {")
        if body is None:
            return False, err
        if "border: 2px solid var(--color-accent);" not in body:
            return False, ".theme-chip:has(input:checked) must carry the 2px accent border"

        body, err = _rule_body(".theme-chip:has(input:checked) .theme-chip__body {")
        if body is None:
            return False, err
        if wash not in body:
            return False, ".theme-chip:has(input:checked) .theme-chip__body must carry the 12%-accent wash"

        body, err = _rule_body(".theme-chip:has(input:checked) .theme-chip__check {")
        if body is None:
            return False, err
        if "display: inline-flex;" not in body:
            return False, ".theme-chip:has(input:checked) .theme-chip__check must be shown"

        # Theme chip hover/focus-within restore (D-03a transferred to
        # live state) - a POSITIVE rule, not a re-scoped guard.
        hover_selector = ".theme-chip:has(input:checked):hover,"
        if hover_selector not in source:
            return False, "expected a live-state hover restore selector for .theme-chip"
        idx = source.index(hover_selector)
        if idx < supports_idx:
            return False, "expected the .theme-chip live-state hover restore rule inside @supports"
        window = source[idx:idx + 250]
        if "border-color: var(--color-accent);" not in window:
            return False, ".theme-chip:has(input:checked):hover must restore the accent border-color"
        if "box-shadow: none;" not in window:
            return False, ".theme-chip:has(input:checked):hover must clear the hover shadow"

        # Runway card: strong border + wash on one rule (no body wrapper),
        # check glyph shown.
        body, err = _rule_body(".runway-card:has(input:checked) {")
        if body is None:
            return False, err
        if "border: 2px solid var(--color-accent);" not in body:
            return False, ".runway-card:has(input:checked) must carry the 2px accent border"
        if wash not in body:
            return False, ".runway-card:has(input:checked) must carry the 12%-accent wash directly (no body wrapper)"

        body, err = _rule_body(".runway-card:has(input:checked) .runway-card__check {")
        if body is None:
            return False, err
        if "display: inline-flex;" not in body:
            return False, ".runway-card:has(input:checked) .runway-card__check must be shown"

        hover_selector = ".runway-card:has(input:checked):hover,"
        if hover_selector not in source:
            return False, "expected a live-state hover restore selector for .runway-card"
        idx = source.index(hover_selector)
        if idx < supports_idx:
            return False, "expected the .runway-card live-state hover restore rule inside @supports"
        window = source[idx:idx + 250]
        if "border-color: var(--color-accent);" not in window:
            return False, ".runway-card:has(input:checked):hover must restore the accent border-color"
        if "box-shadow: none;" not in window:
            return False, ".runway-card:has(input:checked):hover must clear the hover shadow"

        # Fallback intact: all four pre-existing server-class rules must
        # still exist verbatim (source.index would already have raised/
        # returned an error above via the wash check, but assert the two
        # not otherwise touched here too).
        for selector in (
            ".theme-chip--selected {",
            ".theme-chip--selected .theme-chip__body {",
            ".runway-card--selected {",
            ".theme-chip--selected .theme-chip__check {",
            ".runway-card--selected .runway-card__check {",
        ):
            if selector not in source:
                return False, "expected the pre-existing fallback rule %r to survive verbatim" % (selector,)

        return True, ""
    check(
        "the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore) is keyed to "
        "live :has(input:checked) state inside one @supports selector(:has(*)) block, for both .theme-chip and "
        ".runway-card, with every pre-existing --selected fallback rule surviving verbatim (quick task 260904-bbi)",
        _strong_selected_treatment_is_keyed_to_the_live_checked_radio)

    def _saved_but_unchecked_card_degrades_to_a_quiet_current_marker():
        # quick task 260904-bbi: the server-rendered --selected class is
        # demoted from driving the strong treatment to an honest, quiet
        # "this is what is saved" marker once it is no longer the live
        # choice: an accent-free dashed 70%-muted-text ring, its wash and
        # check glyph cleared, and an English "Current" tag rendered as a
        # ::after pseudo-element (see PLAN.md's
        # <current_tag_markup_decision> for why a pseudo-element and not
        # a <span>).
        source = _read_static("style.css")
        muted = "color-mix(in srgb, var(--color-text) 70%, transparent)"

        for prefix in (".theme-chip--selected:not(:has(input:checked))", ".runway-card--selected:not(:has(input:checked))"):
            base_selector = prefix + " {"
            if base_selector not in source:
                return False, "expected style.css to declare %r" % (base_selector,)
            idx = source.index(base_selector)
            body = source[idx + len(base_selector):source.index("}", idx)]
            if "dashed" not in body:
                return False, "%r must use a dashed ring, not a solid one" % (base_selector,)
            if muted not in body:
                return False, "%r must use the established 70%%-muted-text colour, not a new strength" % (base_selector,)
            if "var(--color-accent)" in body:
                return False, "%r must be accent-free - the quiet marker signals 'saved', not 'selected'" % (base_selector,)

        chip_body_selector = ".theme-chip--selected:not(:has(input:checked)) .theme-chip__body {"
        if chip_body_selector not in source:
            return False, "expected style.css to declare %r" % (chip_body_selector,)
        idx = source.index(chip_body_selector)
        window = source[idx:idx + 100]
        if "background: transparent;" not in window:
            return False, "%r must clear the wash back to transparent" % (chip_body_selector,)

        for check_selector in (
            ".theme-chip--selected:not(:has(input:checked)) .theme-chip__check {",
            ".runway-card--selected:not(:has(input:checked)) .runway-card__check {",
        ):
            if check_selector not in source:
                return False, "expected style.css to declare %r" % (check_selector,)
            idx = source.index(check_selector)
            window = source[idx:idx + 100]
            if "display: none;" not in window:
                return False, "%r must hide the check glyph" % (check_selector,)

        current_literal = 'content: "Current";'
        if source.count(current_literal) != 2:
            return False, (
                "expected exactly 2 occurrences of %r, got %d" % (current_literal, source.count(current_literal)))

        for after_selector in (
            ".theme-chip--selected:not(:has(input:checked))::after {",
            ".runway-card--selected:not(:has(input:checked))::after {",
        ):
            if after_selector not in source:
                return False, "expected style.css to declare %r" % (after_selector,)
            idx = source.index(after_selector)
            window = source[idx:idx + 250]
            if current_literal not in window:
                return False, "%r must render the English 'Current' tag" % (after_selector,)

        if "actuel" in source.lower():
            return False, "expected zero occurrences of the French word for 'current' - DP-2 requires English copy"

        muted_count = source.count(muted)
        if muted_count < 17:
            return False, (
                "expected the established 70%%-muted-text mix to appear at least 17 times (16 pre-existing plus "
                "the new quiet-marker rules), got %d - a new muted strength must not be invented" % (muted_count,))

        return True, ""
    check(
        "the saved-but-no-longer-live --selected card degrades to an accent-free dashed 70%-muted ring with its "
        "wash/check glyph cleared and an English \"Current\" ::after tag (exactly 2 occurrences site-wide, zero "
        "French copy), reusing the established muted-text strength rather than inventing a new one "
        "(quick task 260904-bbi)",
        _saved_but_unchecked_card_degrades_to_a_quiet_current_marker)

    def _style_css_carries_section_caption_and_restyled_fixed_dirty_bar():
        # quick task 260901-re6 Task 3: the third new cross-file guard,
        # following the same index-plus-window technique the neighbouring
        # guards above use (never a regex CSS parser). quick task
        # 260901-s5o: retargeted and extended in place (no count change)
        # onto the floating-card treatment.
        source = _read_static("style.css")

        # (a) .section-caption declares only the file's existing 70%
        # muted color-mix idiom.
        caption_selector = ".section-caption {"
        if caption_selector not in source:
            return False, "expected style.css to declare a .section-caption rule"
        idx = source.index(caption_selector)
        window = source[idx:idx + 200]
        if "color-mix(in srgb, var(--color-text) 70%, transparent)" not in window:
            return False, "expected .section-caption's rule body to carry the 70% color-mix muted idiom"

        # (b) the base (non-media-query) .dirty-bar rule is a fully-bordered
        # floating card: dominant surface, a full border (no top-only
        # hairline), the card radius token, and a token-based shadow (no
        # upward-only literal), and no longer carries the old muted
        # --color-secondary surface.
        base_match = re.search(r'^\.dirty-bar \{(.*?)^\}', source, re.MULTILINE | re.DOTALL)
        if not base_match:
            return False, "expected a top-level (non-media-query) .dirty-bar rule"
        base_body = base_match.group(1)
        if "var(--color-dominant)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry var(--color-dominant)"
        if "border: 1px solid var(--color-border)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry a full border: 1px solid var(--color-border) declaration"
        if "border-top:" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry a border-top: declaration"
        if "var(--color-secondary)" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry var(--color-secondary)"
        if "border-radius: var(--radius-card)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry border-radius: var(--radius-card), now load-bearing at every width"
        if "box-shadow: var(--shadow-card-hover)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry box-shadow: var(--shadow-card-hover) as its first shadow layer"
        if "box-shadow: 0 -" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry the retired upward-only literal shadow"

        # (c) the >=960px .dirty-bar rule is fixed, not sticky, and no
        # .dirty-bar rule body anywhere still says position: sticky.
        media_match = re.search(r'^  \.dirty-bar \{(.*?)^  \}', source, re.MULTILINE | re.DOTALL)
        if not media_match:
            return False, "expected an indented (>=960px media query) .dirty-bar rule"
        media_body = media_match.group(1)
        if "position: fixed" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry position: fixed"
        if "position: sticky" in base_body or "position: sticky" in media_body:
            return False, "expected no .dirty-bar rule body to carry position: sticky anywhere"

        # (d) the 240px literal the fixed rule's left uses still equals
        # .dashboard-shell's grid-template-columns first track - a
        # duplicated-not-imported must-equal pair with no shared token,
        # now a three-term left expression with the inset as a third addend.
        if "grid-template-columns: 240px" not in source:
            return False, "expected style.css to declare grid-template-columns: 240px on .dashboard-shell"
        if "calc(240px + var(--space-xl) + var(--space-md))" not in media_body:
            return False, "expected the >=960px .dirty-bar rule's left offset to be calc(240px + var(--space-xl) + var(--space-md))"

        # (e) the inset itself: right pulled in by var(--space-md), bottom
        # by the larger var(--space-lg) (260901-s5o direct follow-up: a
        # bigger edge gap reads more clearly as "floating"), max-width
        # reduced by twice the var(--space-md) inset so the cap doesn't
        # silently cancel it above roughly 1712px (where min(1440px, 100%)
        # alone would size the box, flush with .dashboard-main on both
        # sides), and no corner-squaring override left to re-dock the bar.
        if "bottom: var(--space-lg)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry bottom: var(--space-lg)"
        if "right: var(--space-md)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry right: var(--space-md)"
        if "calc(min(1440px, 100%) - var(--space-md) * 2)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule's max-width to be calc(min(1440px, 100%) - var(--space-md) * 2)"
        if "border-radius: 0" in media_body:
            return False, "expected the >=960px .dirty-bar rule body to no longer carry a corner-squaring border-radius: 0 override"

        # (f) 260901-s5o direct follow-up: developer feedback after seeing
        # the floating card live was "correct shape, too wide, not visible
        # enough." `width: fit-content` is the fix for "too wide" - without
        # it, `width:auto` plus both `left` and `right` set non-auto makes
        # the box stretch to fill the whole positioning region (full
        # .dashboard-main width) per the CSS2.1 abs/fixed sizing rules.
        # The >=960px padding override is gone outright now that the bar
        # is compact rather than full-width - it existed only to align a
        # full-width bar's controls with the content gutter, so the base
        # rule's plain padding: var(--space-md) now governs unmodified.
        if "width: fit-content" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry width: fit-content, so it sizes to its own content instead of stretching the full column"
        if "padding:" in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry no padding override - the base rule's padding: var(--space-md) should apply unmodified now that the bar is compact"
        return True, ""
    check(
        "style.css declares .section-caption (70% muted color-mix), the restyled base .dirty-bar as a floating rounded card (full border, radius token, surrounding token-based shadow, no --color-secondary), and the fixed-not-sticky >=960px .dirty-bar rule: inset by var(--space-md)/var(--space-lg) with a correspondingly reduced max-width, no corner-squaring, and width: fit-content so it sizes to its own content instead of stretching the full column (quick task 260901-re6, quick task 260901-s5o, 260901-s5o direct follow-up)",
        _style_css_carries_section_caption_and_restyled_fixed_dirty_bar)

    def _dirty_state_js_has_no_hardcoded_section_names():
        source = _read_static("dirty-state.js")
        for literal in ("Theme", "Runway", "Diagnostic LED"):
            if literal in source:
                return False, "expected no hardcoded occurrence of %r - section labels must come from the DOM" % (literal,)
        return True, ""
    check(
        "dirty-state.js contains no hardcoded occurrence of \"Theme\", \"Runway\", or \"Diagnostic LED\" (labels come from the DOM)",
        _dirty_state_js_has_no_hardcoded_section_names)

    def _dirty_state_js_still_has_no_network_or_timer_sinks():
        source = _read_static("dirty-state.js")
        for forbidden in ("fetch(", "XMLHttpRequest", "setInterval", "setTimeout"):
            if forbidden in source:
                return False, "forbidden network/timer construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js still contains no fetch/XMLHttpRequest/setInterval/setTimeout",
        _dirty_state_js_still_has_no_network_or_timer_sinks)

    # ==================================================================
    # Section 2: one end-to-end check — launches the real companion/app.py
    # subprocess, logs in, posts a valid theme-and-runway pair, follows
    # the redirect, and asserts the rendered page carries D-07's
    # confirmation copy verbatim and shows the newly-saved runway
    # selected. No unit check can establish that the router, this page
    # module, and the persistence layer actually agree end to end.
    # ==================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        def _save_round_trip_shows_confirmation_and_new_selection():
            # 06.6.4.1-07 (D-26): posts to the live SETTINGS_ROUTE
            # ("/settings") now that companion/app.py actually dispatches
            # it — the old "/config" path 404s by design (no redirect).
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode(
                    {"theme": "black", "tracked_runway": "06-24"}).encode())
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            redirect_status, _redirect_headers, body = http_request(
                base + location, cookie=session_cookie)
            if redirect_status != 200:
                return False, "expected 200 following the save redirect, got %d" % redirect_status
            # D-07's confirmation sentence is defined exactly once in the
            # repository, in companion/app.py's FLASH_MESSAGES mapping —
            # referenced here rather than re-typed, so this file is never
            # a second place that literal sentence lives.
            confirmation = escape_html(
                companion_app.FLASH_MESSAGES[companion_app.FLASH_KEY_SAVED])
            if confirmation.encode() not in body:
                return False, "expected D-07's exact confirmation copy in the response body"
            if b'value="06-24" class="visually-hidden" checked' not in body:
                return False, "expected the newly-saved runway (06-24) to be shown selected"
            return True, ""
        check(
            "a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway selected",
            _save_round_trip_shows_confirmation_and_new_selection)

        def _settings_save_redirect_carries_flash_banner_and_cleanup_script():
            # Quick task 260903-peo (UIR-19): the server-side PRG redirect
            # itself is unchanged by this task — this pins the pairing
            # that makes the client-side cleanup reachable: the rendered
            # redirect target carries BOTH the flash banner
            # flash-cleanup.js looks for (.banner--flash) AND
            # flash-cleanup.js's own deferred <script> tag.
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode(
                    {"theme": "black", "tracked_runway": "06-24"}).encode())
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            expected_location = "%s?flash=saved" % config_page.SETTINGS_ROUTE
            if location != expected_location:
                return False, (
                    "expected the PRG redirect target to stay exactly %r, got %r — "
                    "the server-side redirect must be unchanged by this task"
                    % (expected_location, location))
            redirect_status, _redirect_headers, body = http_request(
                base + location, cookie=session_cookie)
            if redirect_status != 200:
                return False, "expected 200 following the save redirect, got %d" % redirect_status
            body_text = body.decode("utf-8", errors="replace")
            if "banner--flash" not in body_text:
                return False, "expected the rendered redirect target to carry the flash banner"
            expected_script_tag = (
                '<script src="%s" defer></script>' % companion_app.FLASH_CLEANUP_SCRIPT_ROUTE)
            if expected_script_tag not in body_text:
                return False, (
                    "expected the rendered redirect target to carry flash-cleanup.js's own "
                    "deferred <script> tag — the pairing that makes the client-side cleanup "
                    "reachable")
            return True, ""
        check(
            "a real HTTP save round trip keeps the server-side PRG redirect exactly "
            "SETTINGS_ROUTE?flash=saved, and the rendered redirect target carries BOTH the "
            "flash banner and flash-cleanup.js's deferred script tag (quick task 260903-peo, "
            "UIR-19)",
            _settings_save_redirect_carries_flash_banner_and_cleanup_script)

        def _settings_post_empty_body_persists_led_false_and_renders_unchecked():
            # 06.6.4.1-07 (D-05): the separate LED route is retired — this
            # is the live-HTTP successor to the old "empty-body POST
            # /config-led" check, now posting to the single merged
            # SETTINGS_ROUTE with nothing submitted at all (the shape a
            # browser sends when nothing is checked/selected). Same
            # persisted outcome, same redirect-with-flash shape.
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=b"")
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected on-disk led_enabled False after an empty-body POST, got %r" % (on_disk["led_enabled"],)
            get_status, _get_headers, body = http_request(
                base + config_page.SETTINGS_ROUTE, cookie=session_cookie)
            if get_status != 200:
                return False, "expected 200 on the follow-up GET %s, got %d" % (
                    config_page.SETTINGS_ROUTE, get_status)
            if b'name="led_enabled" value="on" checked' in body:
                return False, "expected the LED checkbox to render unchecked after saving False"
            return True, ""
        check(
            "a live authenticated POST %s with an empty body 303-redirects to %s?flash=saved, "
            "persists led_enabled False, and a follow-up GET renders the control unchecked"
            % (config_page.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE),
            _settings_post_empty_body_persists_led_false_and_renders_unchecked)

        def _settings_post_unauthenticated_redirects_to_login_and_writes_nothing():
            # 06.6.4.1-07 (D-05): live-HTTP successor to the old
            # "unauthenticated POST /config-led" check — same target
            # (now SETTINGS_ROUTE), same no-write assertion.
            config_path = device_config.device_config_path(harness.tmpdir)
            existed_before = os.path.exists(config_path)
            before = open(config_path, "rb").read() if existed_before else None
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            exists_after = os.path.exists(config_path)
            if not existed_before and exists_after:
                return False, "an unauthenticated POST %s created device_config.json" % config_page.SETTINGS_ROUTE
            if existed_before:
                after = open(config_path, "rb").read()
                if before != after:
                    return False, "an unauthenticated POST %s modified device_config.json" % config_page.SETTINGS_ROUTE
            return True, ""
        check(
            "an unauthenticated POST %s redirects to /login and writes nothing" % config_page.SETTINGS_ROUTE,
            _settings_post_unauthenticated_redirects_to_login_and_writes_nothing)

        def _led_route_retired_returns_404():
            # 06.6.4.1-07 (D-05): the separate LED POST route no longer
            # exists anywhere in the app — an authenticated POST to it
            # now falls through to the standard 404, same as any other
            # unrouted path.
            status, _headers, _body = http_request(
                base + "/config-led", method="POST", cookie=session_cookie, data=b"")
            if status != 404:
                return False, "expected 404 for the retired /config-led route, got %d" % status
            return True, ""
        check(
            "an authenticated POST to the retired /config-led route returns 404 (D-05)",
            _led_route_retired_returns_404)

        def _runway_image_route_requires_session():
            status, headers, _ = http_request(base + "/runway-image/3.png")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if location != "/login":
                return False, "expected a Location of /login, got %r" % location
            return True, ""
        check(
            "an unauthenticated GET /runway-image/3.png redirects to /login",
            _runway_image_route_requires_session)

        def _runway_image_route_honest_present_or_absent():
            path = companion_app._runway_image_path("3")
            status, headers, _ = http_request(
                base + "/runway-image/3.png", cookie=session_cookie)
            if os.path.isfile(path):
                if status != 200:
                    return False, "expected 200 when the file exists, got %d" % status
                if headers.get("Content-Type") != "image/png":
                    return False, "expected Content-Type image/png, got %r" % headers.get("Content-Type")
            else:
                if status != 404:
                    return False, "expected 404 when the file is absent (D-02 shipped state), got %d" % status
            return True, ""
        check(
            "a session-authenticated GET /runway-image/3.png returns the branch matching real on-disk state (never 500)",
            _runway_image_route_honest_present_or_absent)

        def _runway_image_route_path_traversal_rejected():
            adversarial_paths = [
                "/runway-image/..%2F..%2Fetc%2Fpasswd.png",
                "/runway-image/../../../etc/passwd.png",
                "/runway-image/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, _ = http_request(
                    base + adversarial_path, cookie=session_cookie)
                if status not in (404,):
                    return False, (
                        "expected 404 for adversarial path %r, got %d"
                        % (adversarial_path, status))
            return True, ""
        check(
            "session-authenticated GET requests for three adversarial runway-image paths all return 404, never 200/500",
            _runway_image_route_path_traversal_rejected)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-page: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
