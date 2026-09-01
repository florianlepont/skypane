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
EXPECTED_CHECK_COUNT = 60


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

    def _render_shape_read_only_theme_runway_cards_led_group_and_save_button():
        # 06.6.4.1 (D-05): with the real (unmodified) single-member
        # THEME_IDS registry, Theme renders as the read-only .theme-status
        # block (no <fieldset>), Runway as a .theme-status-wrapped
        # .runway-card list (also no <fieldset>), and LED now renders as
        # a third .theme-status-wrapped group (led_group()) instead of
        # its own <fieldset>/<legend>-carrying <section> — render()'s
        # output carries zero <fieldset occurrences.
        ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset occurrences, got %d" % rendered.count("<fieldset")
        if rendered.count('class="theme-status"') != 3:
            return False, "expected exactly 3 theme-status-wrapped groups (Theme/Runway/Diagnostic LED), got %d" % rendered.count('class="theme-status"')
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if "Save Settings" not in rendered:
            return False, "expected the 'Save Settings' submit button copy"
        return True, ""
    check(
        "render() emits the read-only theme-status block, three runway-card labels, the LED group, and a Save Settings submit button, with zero <fieldset occurrences",
        _render_shape_read_only_theme_runway_cards_led_group_and_save_button)

    def _led_group_carries_classed_label_and_unchanged_input_attrs():
        # quick task 260901-qif: pins the led-checkbox label class and
        # guards the input's name/value/checked attribute sequence against
        # a future markup edit silently reordering it - the two live-HTTP
        # LED checks further down this file match on that exact sequence.
        checked_html = config_page.led_group(True)
        unchecked_html = config_page.led_group(False)
        label_open = '<label class="led-checkbox">'
        if checked_html.count(label_open) != 1:
            return False, "expected led_group(True) to carry exactly one <label class=\"led-checkbox\"> occurrence"
        if unchecked_html.count(label_open) != 1:
            return False, "expected led_group(False) to carry exactly one <label class=\"led-checkbox\"> occurrence"
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
        "led_group() emits the led-checkbox label class and preserves the input's name/value/checked attribute sequence",
        _led_group_carries_classed_label_and_unchanged_input_attrs)

    def _every_settings_group_is_named_at_one_heading_level():
        # heading-color-consistency debug session, extended by 06.6.4.1
        # (D-05): Config carries four settings groups. Before D-05's LED
        # merge, three used <h2 class="text-heading"> (Theme/Runway/Poll)
        # while Diagnostic LED alone kept a <legend> inside its own
        # <fieldset> (its own independently-submittable <form>, D-06).
        # Now that the LED group is a sibling inside the single merged
        # form, it drops the <fieldset>/<legend> for the same <h2>
        # role its three siblings already use — render()'s output
        # carries zero <legend> elements, and all four groups are named
        # exactly once at one consistent heading level.
        ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
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
                "expected zero <legend elements in render()'s output now "
                "that the LED group has no <fieldset> wrapper of its own")
        # The old label-paragraph shape must not come back alongside the
        # heading — that would name the Theme group twice.
        if '<p class="text-label">Theme</p>' in rendered:
            return False, (
                "the Theme group is named twice: the superseded "
                "text-label paragraph is still present next to the <h2>")
        return True, ""
    check(
        "all four Config settings groups (Theme/Runway/Diagnostic LED/Poll) are named "
        "exactly once, at one consistent heading level, with zero <legend> elements",
        _every_settings_group_is_named_at_one_heading_level)

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
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
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
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
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
        if "Save Settings" not in form_segment:
            return False, "expected the always-visible bottom Save Settings fallback button to still appear inside the form"
        save_button_marker = 'class="dirty-bar__save" form="%s"' % config_page.SETTINGS_FORM_ID
        if save_button_marker not in rendered:
            return False, "expected the dirty-bar's own save button to carry form=%r" % (config_page.SETTINGS_FORM_ID,)
        return True, ""
    check(
        "render()'s dirty-state bar is a sibling of the config-form <form>, emitted last on the page after both </form> and the Poll section, with its save button carrying form=SETTINGS_FORM_ID (quick task 260901-re6)",
        _render_dirty_bar_is_sibling_of_form_last_on_page)

    def _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex():
        # D-04, Task 2 Test 1: with the real (unmodified) single-member
        # THEME_IDS registry, theme_fieldset() renders the read-only
        # status block — zero <input> occurrences — showing "{label} ·
        # current" and swatch chip hex values computed at test time from
        # panel_format.PALETTE_RGB, not hardcoded expected strings.
        rendered = config_page.theme_fieldset(device_config.DEFAULT_THEME_ID)
        if "<input" in rendered:
            return False, "expected zero <input occurrences in the read-only branch"
        expected_label = "%s · current" % device_config.theme_label(device_config.DEFAULT_THEME_ID)
        if expected_label not in rendered:
            return False, "expected %r in the rendered output" % (expected_label,)
        theme = device_config.THEMES[device_config.DEFAULT_THEME_ID]
        departing_hex = config_page._palette_hex(theme["departing_index"])
        arriving_hex = config_page._palette_hex(theme["arriving_index"])
        if ("background:%s" % departing_hex) not in rendered:
            return False, "expected the departing swatch hex %r derived from PALETTE_RGB" % (departing_hex,)
        if ("background:%s" % arriving_hex) not in rendered:
            return False, "expected the arriving swatch hex %r derived from PALETTE_RGB" % (arriving_hex,)
        if "Phase 7" in rendered:
            return False, "expected no leaked internal 'Phase 7' planning reference (UXA-05)"
        return True, ""
    check(
        "theme_fieldset() renders the read-only theme-status block with real panel-color swatch hex values when THEME_IDS has one member (D-04)",
        _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex)

    def _theme_fieldset_falls_back_to_radio_group_when_multiple_themes_registered():
        # D-04, Task 2 Test 2: a synthetic 2-member THEME_IDS (monkeypatched
        # for the duration of this check only) makes theme_fieldset() fall
        # back to the original editable radio-group markup — a len()
        # check, not a hardcoded single-theme assumption.
        original_themes = device_config.THEMES
        original_ids = device_config.THEME_IDS
        device_config.THEMES = dict(original_themes)
        device_config.THEMES["dusk"] = {
            "departing_index": original_themes[device_config.DEFAULT_THEME_ID]["departing_index"],
            "arriving_index": original_themes[device_config.DEFAULT_THEME_ID]["arriving_index"],
            "ink_index": original_themes[device_config.DEFAULT_THEME_ID]["ink_index"],
            "label": "Dusk",
        }
        device_config.THEME_IDS = tuple(device_config.THEMES)
        try:
            rendered = config_page.theme_fieldset(device_config.DEFAULT_THEME_ID)
        finally:
            device_config.THEMES = original_themes
            device_config.THEME_IDS = original_ids
        # 06.6.4.1 (D-05): the <fieldset> now also carries
        # data-dirty-section="Theme" (escaped literal), so this no longer
        # matches the bare "<fieldset>" substring exactly — check for the
        # element's presence and its attribute instead.
        if "<fieldset" not in rendered or "<legend>Theme</legend>" not in rendered:
            return False, "expected the original fieldset/legend radio-group markup once >1 theme is registered"
        if ('%s="%s"' % (config_page.DIRTY_SECTION_ATTR, escape_html("Theme"))) not in rendered:
            return False, "expected the fallback fieldset to carry data-dirty-section=\"Theme\""
        if rendered.count('name="theme"') != 2:
            return False, "expected 2 theme radios, got %d" % rendered.count('name="theme"')
        return True, ""
    check(
        "theme_fieldset() falls back to the editable radio group the moment a second theme is registered (D-04)",
        _theme_fieldset_falls_back_to_radio_group_when_multiple_themes_registered)

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

    def _render_exactly_three_dirty_sections_in_order():
        # Acceptance criterion: the rendered output contains exactly
        # three elements carrying data-dirty-section, whose attribute
        # values in document order are "Theme", "Runway", "Diagnostic LED".
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        found = re.findall(
            r'%s="([^"]*)"' % re.escape(config_page.DIRTY_SECTION_ATTR), rendered)
        expected = ["Theme", "Runway", "Diagnostic LED"]
        if found != expected:
            return False, "expected %r in document order, got %r" % (expected, found)
        return True, ""
    check(
        "render() carries exactly three data-dirty-section elements, in document order Theme/Runway/Diagnostic LED",
        _render_exactly_three_dirty_sections_in_order)

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
        # index falling after the group's </h2> and before the group's
        # control.
        theme_rendered = config_page.theme_fieldset("sky")
        runway_rendered = config_page.runway_fieldset("3")
        led_rendered = config_page.led_group(True)
        groups = (
            ("theme_fieldset()", theme_rendered, "theme-status__row"),
            ("runway_fieldset()", runway_rendered, "runway-row"),
            ("led_group()", led_rendered, "led-checkbox"),
        )
        for name, rendered, control_marker in groups:
            if rendered.count("<p") != 1:
                return False, "expected %s to emit exactly one <p element, got %d" % (name, rendered.count("<p"))
            if rendered.count("section-caption") != 1:
                return False, "expected %s to emit exactly one section-caption occurrence, got %d" % (name, rendered.count("section-caption"))
            heading_close = rendered.index("</h2>")
            caption_pos = rendered.index("section-caption")
            control_pos = rendered.index(control_marker)
            if not (heading_close < caption_pos < control_pos):
                return False, "expected %s's caption to fall after </h2> and before its control (%r)" % (name, control_marker)
        return True, ""
    check(
        "theme_fieldset()/runway_fieldset()/led_group() each emit exactly one section-caption <p> element, positioned between the group heading and the group control (quick task 260901-re6)",
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
            r'<button\b[^>]*%s[^>]*>Save Settings</button>'
            % re.escape(config_page.STATIC_SAVE_FALLBACK_ATTR), rendered)
        if not button_match:
            return False, "expected the fallback attribute on a type=\"submit\" Save Settings button"
        if 'type="submit"' not in button_match.group(0):
            return False, "expected the fallback button to carry type=\"submit\""
        return True, ""
    check(
        "render()'s bottom Save Settings button carries data-static-save-fallback exactly once (D-04)",
        _bottom_save_button_carries_static_fallback_attr)

    def _section_captions_appear_escaped_verbatim_exactly_once():
        # quick task 260901-re6: retargeted onto all three merged caption
        # constants, strengthened from "is present" to "appears exactly
        # once" for each.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        theme_caption = escape_html(config_page.THEME_SECTION_CAPTION)
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        led_caption = escape_html(config_page.LED_SECTION_CAPTION)
        if rendered.count(theme_caption) != 1:
            return False, "expected THEME_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(theme_caption)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(runway_caption)
        if rendered.count(led_caption) != 1:
            return False, "expected LED_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(led_caption)
        return True, ""
    check(
        "the theme, runway, and LED section captions all appear escaped-verbatim exactly once in render()'s output (quick task 260901-re6)",
        _section_captions_appear_escaped_verbatim_exactly_once)

    def _current_theme_and_runway_are_selected():
        # 06.6.3-03: with THEME_IDS at its real single-member size, Theme
        # has no radio at all (D-04's read-only status block) — the
        # selection assertion is scoped to Runway's card markup, whose
        # native radio's checked attribute now sits after a class
        # attribute (`value="{id}" class="visually-hidden"{checked}>`),
        # not immediately after value= like the old radio-group markup.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "06-24"},
            "poll_cooldown_remaining": 0,
        })
        if 'value="06-24" class="visually-hidden" checked' not in rendered:
            return False, "expected the non-default saved runway (06-24) to be marked selected"
        if 'value="3" class="visually-hidden" checked' in rendered:
            return False, "expected runway 3 (not the saved value) to NOT be marked selected"
        if rendered.count("runway-card--selected") != 1:
            return False, "expected exactly one runway-card--selected modifier"
        if "Sky (default) · current" not in rendered:
            return False, "expected the saved theme (sky) to be shown as the read-only current theme"
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
        if "Trigger Poll Now" not in rendered:
            return False, "expected the Trigger Poll Now button copy"
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
        if "Trigger Poll Now" not in rendered:
            return False, "expected the Trigger Poll Now button copy"
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
                {"theme": "sky", "tracked_runway": "06-24"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            # 06.6.4.1 (D-05): led_enabled is now resolved by handle_post()
            # itself, with checkbox-absent-means-False semantics (never
            # carried forward like theme/runway) — this posted form omits
            # led_enabled entirely, so the persisted value is False, not
            # DEFAULT_LED_ENABLED (True).
            if on_disk != {"theme": "sky", "tracked_runway": "06-24", "led_enabled": False}:
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
            _write_device_config(tmpdir, "sky", "3")
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
            _write_device_config(tmpdir, "sky", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky", "tracked_runway": "not-a-real-runway"}, ctx)
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
            _write_device_config(tmpdir, "sky", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "sky"}, ctx)
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
            _write_device_config(tmpdir, "sky", "3")
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
            _write_device_config(tmpdir, "sky", "3")
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
                    {"theme": "sky", "tracked_runway": "3"}, ctx)
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
            _write_device_config(tmpdir, "sky", "3", led_enabled=True)
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
            "device_config": {"theme": "sky", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
            "runway_images": {"06-24"},
        })
        if "/runway-image/06-24.png" not in rendered:
            return False, "expected render() to forward ctx['runway_images'] into the <img> src"
        if rendered.count("<img") != 1:
            return False, "expected exactly one <img occurrence, got %d" % rendered.count("<img")
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

    def _style_css_carries_theme_status_runway_row_and_led_checkbox_selectors():
        # quick task 260901-qif: the third new cross-file guard - unlike
        # DIRTY_SECTION_ATTR/STATIC_SAVE_FALLBACK_ATTR above, no Python
        # constant carries these three class-name literals, so they are
        # asserted directly here. Same index-plus-window technique the
        # neighbouring guards use, never a regex CSS parser. Keeps
        # style.css's .theme-status/.runway-row/.led-checkbox rules from
        # silently drifting out of sync with the markup config_page.py's
        # runway_fieldset()/led_group() now emit.
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

        checkbox_selector = '.led-checkbox input[type="checkbox"] {'
        if checkbox_selector not in source:
            return False, "expected style.css to declare a %r rule" % (checkbox_selector,)
        idx = source.index(checkbox_selector)
        window = source[idx:idx + 400]
        if "min-height: 0" not in window:
            return False, "expected .led-checkbox input[type=\"checkbox\"]'s rule body to clear the global rule's min-height"
        return True, ""
    check(
        "style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex display), and .led-checkbox input[type=\"checkbox\"] (cleared min-height) - the selectors config_page.py's new markup depends on",
        _style_css_carries_theme_status_runway_row_and_led_checkbox_selectors)

    def _style_css_carries_section_caption_and_restyled_fixed_dirty_bar():
        # quick task 260901-re6 Task 3: the third new cross-file guard,
        # following the same index-plus-window technique the neighbouring
        # guards above use (never a regex CSS parser).
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

        # (b) the base (non-media-query) .dirty-bar rule carries the
        # dominant surface and a top hairline, and no longer carries the
        # old muted --color-secondary surface.
        base_match = re.search(r'^\.dirty-bar \{(.*?)^\}', source, re.MULTILINE | re.DOTALL)
        if not base_match:
            return False, "expected a top-level (non-media-query) .dirty-bar rule"
        base_body = base_match.group(1)
        if "var(--color-dominant)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry var(--color-dominant)"
        if "border-top:" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry a border-top: declaration"
        if "var(--color-secondary)" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry var(--color-secondary)"

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
        # duplicated-not-imported must-equal pair with no shared token.
        if "grid-template-columns: 240px" not in source:
            return False, "expected style.css to declare grid-template-columns: 240px on .dashboard-shell"
        if "calc(240px + var(--space-xl))" not in media_body:
            return False, "expected the >=960px .dirty-bar rule's left offset to be calc(240px + var(--space-xl))"
        return True, ""
    check(
        "style.css declares .section-caption (70% muted color-mix), the restyled base .dirty-bar (dominant surface, top hairline, no --color-secondary), the fixed-not-sticky >=960px .dirty-bar rule, and the 240px<->grid-template-columns must-equal pair (quick task 260901-re6)",
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
                    {"theme": "sky", "tracked_runway": "06-24"}).encode())
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
