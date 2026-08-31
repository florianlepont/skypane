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
# nesting/ordering check, +1).
EXPECTED_CHECK_COUNT = 47  # 46 + 1 (heading-color-consistency: one consistent heading level for all four settings groups)


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

    def _render_shape_read_only_theme_runway_cards_led_fieldset_and_save_button():
        # 06.6.3-03: with the real (unmodified) single-member THEME_IDS
        # registry, Theme renders as the read-only .theme-status block
        # (no <fieldset>) and Runway renders as .runway-card labels (also
        # no <fieldset>) — the sole remaining <fieldset> in render()'s
        # output is the LED section's.
        ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if rendered.count("<fieldset") != 1:
            return False, "expected exactly 1 <fieldset occurrence (LED only), got %d" % rendered.count("<fieldset")
        if 'class="theme-status"' not in rendered:
            return False, "expected the read-only theme-status block"
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if "Save Settings" not in rendered:
            return False, "expected the 'Save Settings' submit button copy"
        return True, ""
    check(
        "render() emits the read-only theme-status block, three runway-card labels, the LED fieldset, and a Save Settings submit button",
        _render_shape_read_only_theme_runway_cards_led_fieldset_and_save_button)

    def _every_settings_group_is_named_at_one_heading_level():
        # heading-color-consistency debug session. Config carries four
        # settings groups, and before this session they were named four
        # different ways: Theme by a <p class="text-label">, Runway by
        # nothing at all (three unlabelled runway cards), Diagnostic LED
        # by a <legend>, and Poll by an <h2 class="text-heading">. Every
        # group now has exactly one name, and all four render at the
        # same heading level — <h2 class="text-heading"> for the three
        # groups D-04/D-05 stripped of their <fieldset>, <legend> for
        # the one group that still has a <fieldset> (D-06 requires the
        # legend there and forbids a duplicate <h2> alongside it), and
        # style.css's serif rule now renders the two identically.
        ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        for name in ("Theme", "Runway", "Poll"):
            heading = '<h2 class="text-heading">%s</h2>' % name
            if rendered.count(heading) != 1:
                return False, (
                    "expected exactly one %r group heading, got %d"
                    % (heading, rendered.count(heading)))
        if rendered.count("<legend>Diagnostic LED</legend>") != 1:
            return False, (
                "expected the LED group to keep its <legend> as its sole "
                "accessible group name (D-06)")
        # The old label-paragraph shape must not come back alongside the
        # heading — that would name the Theme group twice.
        if '<p class="text-label">Theme</p>' in rendered:
            return False, (
                "the Theme group is named twice: the superseded "
                "text-label paragraph is still present next to the <h2>")
        return True, ""
    check(
        "all four Config settings groups (Theme/Runway/LED/Poll) are named "
        "exactly once, at one consistent heading level",
        _every_settings_group_is_named_at_one_heading_level)

    def _render_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): Config's top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if '<h1 class="page-title">Config</h1>' not in rendered:
            return False, "expected the page_header()-rendered <h1 class=\"page-title\">Config</h1>"
        if '<h1 class="text-heading">' in rendered:
            return False, "expected no bare <h1 class=\"text-heading\"> heading"
        return True, ""
    check(
        "Config opens with the shared layout.page_header() component, not a bare <h1>",
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
        if '<form class="config-form" data-dirty-form method="post" action="/config">' not in rendered:
            return False, "expected the config-form class, data-dirty-form, method=\"post\", and action=\"/config\" on the same form tag"
        return True, ""
    check(
        "the settings form keeps the stable config-form class hook the desktop two-column fieldset layout targets",
        _settings_form_carries_config_form_class_hook)

    def _render_dirty_bar_nested_inside_form_after_fieldsets_before_bottom_button():
        # D-03 (06.6.3-03 Task 3): the dirty-state bar is a genuine
        # descendant of the same <form> the always-visible bottom Save
        # Settings button belongs to — not a sibling, not a second form —
        # sitting between the two fieldsets and that bottom button.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form>, no duplicate"
        form_start = rendered.index('<form class="config-form"')
        form_end = rendered.index("</form>", form_start)
        segment = rendered[form_start:form_end]
        for marker in ("data-dirty-bar", "data-dirty-count", "data-dirty-cancel"):
            if marker not in segment:
                return False, "expected %r inside the config-form <form>...</form> segment" % (marker,)
        if "Save Settings" not in segment:
            return False, "expected the always-visible bottom Save Settings button inside the same form"
        if segment.index("data-dirty-bar") > segment.index("Save Settings"):
            return False, "expected the dirty-bar to appear before the bottom Save Settings button in document order"
        return True, ""
    check(
        "render()'s dirty-state bar is nested inside the config-form <form>, before the always-visible bottom Save Settings button, with no duplicate form (D-03)",
        _render_dirty_bar_nested_inside_form_after_fieldsets_before_bottom_button)

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
        if "<fieldset>" not in rendered or "<legend>Theme</legend>" not in rendered:
            return False, "expected the original fieldset/legend radio-group markup once >1 theme is registered"
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

    def _helper_texts_appear_escaped_verbatim():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        if escape_html(config_page.THEME_HELPER_TEXT) not in rendered:
            return False, "theme helper text missing (escaped-verbatim)"
        if escape_html(config_page.RUNWAY_HELPER_TEXT) not in rendered:
            return False, "runway helper text missing (escaped-verbatim)"
        if escape_html(config_page.LED_HELPER_TEXT) not in rendered:
            return False, "LED helper text missing (escaped-verbatim)"
        return True, ""
    check(
        "the theme, runway, and LED helper texts all appear escaped-verbatim in render()'s output",
        _helper_texts_appear_escaped_verbatim)

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
            if on_disk != {"theme": "sky", "tracked_runway": "06-24", "led_enabled": True}:
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
    # LED section checks (Task 2, D-01/D-02/T-06.2-02) - a-f are unit
    # checks; g-h (below, inside the Harness block) drive real HTTP.
    # ------------------------------------------------------------------

    def _led_fieldset_checked_true():
        rendered = config_page.led_fieldset(True)
        if "checked" not in rendered:
            return False, "expected a checked attribute for led_fieldset(True)"
        if rendered.count('name="led_enabled"') != 1:
            return False, "expected exactly one name=\"led_enabled\" input"
        return True, ""
    check(
        "led_fieldset(True) contains a checked attribute and one name=\"led_enabled\" input",
        _led_fieldset_checked_true)

    def _led_fieldset_unchecked_false():
        rendered = config_page.led_fieldset(False)
        if "checked" in rendered:
            return False, "expected no checked attribute for led_fieldset(False)"
        return True, ""
    check(
        "led_fieldset(False) contains no checked attribute",
        _led_fieldset_unchecked_false)

    # ------------------------------------------------------------------
    # D-02/D-06 (06.6.3-03 Task 1): the LED section's user-facing copy
    # renamed "bring-up" -> "diagnostic", and the section's duplicate
    # heading (an independent <h2> alongside the fieldset's own <legend>)
    # removed, leaving the <legend> as the sole accessible group name.
    # ------------------------------------------------------------------

    def _led_section_no_stale_bring_up_led_string():
        rendered = config_page.led_section(True)
        if "bring-up" in rendered.lower():
            return False, "expected no case-insensitive 'bring-up' substring in led_section()'s output"
        return True, ""
    check(
        "led_section(True) contains no stale 'Bring-up LED' internal-identifier string (D-02)",
        _led_section_no_stale_bring_up_led_string)

    def _led_section_single_accessible_group_name_no_duplicate_heading():
        rendered = config_page.led_section(True)
        if rendered.count("Diagnostic LED") != 1:
            return False, (
                "expected exactly one 'Diagnostic LED' accessible group name, got %d"
                % rendered.count("Diagnostic LED"))
        if "<h2" in rendered:
            return False, "expected no <h2> in led_section()'s output (the legend is the sole group name)"
        if "<legend>Diagnostic LED</legend>" not in rendered:
            return False, "expected the fieldset legend to carry the group name"
        return True, ""
    check(
        "led_section(True) has exactly one accessible group name (the <legend>), no duplicate <h2> (D-06)",
        _led_section_single_accessible_group_name_no_duplicate_heading)

    def _led_fieldset_checkbox_label_reads_enable_diagnostic_led():
        rendered = config_page.led_fieldset(True)
        if "Enable diagnostic LED" not in rendered:
            return False, "expected the checkbox label to read 'Enable diagnostic LED'"
        if "Enable bring-up LED" in rendered:
            return False, "expected the stale 'Enable bring-up LED' label to be gone"
        return True, ""
    check(
        "led_fieldset(True)'s checkbox label reads 'Enable diagnostic LED' (D-02)",
        _led_fieldset_checkbox_label_reads_enable_diagnostic_led)

    def _render_has_second_form_for_led_route():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'action="/config"' not in rendered:
            return False, "expected the /config form action to be present"
        if 'action="/config-led"' not in rendered:
            return False, "expected a second, distinct /config-led form action"
        return True, ""
    check(
        "render() emits a second <form whose action is the LED route, distinct from the /config form",
        _render_has_second_form_for_led_route)

    def _handle_led_post_unchecked_persists_false():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected led_enabled False on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_led_post({}, ctx) - the shape a browser sends for an unchecked checkbox - persists led_enabled False and returns the saved flash key",
        _handle_led_post_unchecked_persists_false)

    def _handle_led_post_checked_persists_true():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post(
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
        "handle_led_post({\"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True and returns the saved flash key",
        _handle_led_post_checked_persists_true)

    def _handle_led_post_crafted_value_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3", led_enabled=True)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post(
                {"led_enabled": "<script>alert(1)</script>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted led_enabled value, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_led_post with a crafted non-checkbox value returns FLASH_SAVE_FAILED and leaves device_config.json byte-identical",
        _handle_led_post_crafted_value_rejected)

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
            status, headers, _ = http_request(
                base + "/config", method="POST", cookie=session_cookie,
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

        def _led_post_empty_body_saves_false_and_renders_unchecked():
            status, headers, _ = http_request(
                base + "/config-led", method="POST", cookie=session_cookie,
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
                base + "/config", cookie=session_cookie)
            if get_status != 200:
                return False, "expected 200 on the follow-up GET /config, got %d" % get_status
            if b'name="led_enabled" value="on" checked' in body:
                return False, "expected the LED checkbox to render unchecked after saving False"
            return True, ""
        check(
            "a live authenticated POST /config-led with an empty body 303-redirects to /config?flash=saved, persists led_enabled False, and a follow-up GET /config renders the control unchecked",
            _led_post_empty_body_saves_false_and_renders_unchecked)

        def _led_post_unauthenticated_redirects_to_login_and_writes_nothing():
            config_path = device_config.device_config_path(harness.tmpdir)
            existed_before = os.path.exists(config_path)
            before = open(config_path, "rb").read() if existed_before else None
            status, headers, _ = http_request(
                base + "/config-led", method="POST", data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            exists_after = os.path.exists(config_path)
            if not existed_before and exists_after:
                return False, "an unauthenticated POST /config-led created device_config.json"
            if existed_before:
                after = open(config_path, "rb").read()
                if before != after:
                    return False, "an unauthenticated POST /config-led modified device_config.json"
            return True, ""
        check(
            "an unauthenticated POST /config-led redirects to /login and writes nothing",
            _led_post_unauthenticated_redirects_to_login_and_writes_nothing)

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
