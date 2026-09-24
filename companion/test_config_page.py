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
import ast
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import tokenize
import io
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import app as companion_app  # noqa: E402
from companion import battery  # noqa: E402
from companion import frame_state  # noqa: E402
from companion import i18n  # noqa: E402
from companion import auth  # noqa: E402
import companion.i18n_fr as i18n_fr  # noqa: E402
import companion.layout as layout  # noqa: E402
from companion.layout import escape_html  # noqa: E402
import companion.prefs as prefs  # noqa: E402
from companion.pages import config_page  # noqa: E402
import companion.i18n_fr.display as i18n_fr_display  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import calendar_rules, colour_rules  # noqa: E402

TEST_PASSWORD = "config-page-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 192


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


def _python_identifiers(path):
    """Every NAME token in the Python file at `path`, as a set.

    25-05-PLAN.md Task 1 (CFG-49). Tokenised rather than grepped, for
    this project's own standing reason, and the tokeniser gives it for
    free in BOTH directions: a NAME token can never come from a comment,
    a docstring or a string literal, so the prose explaining a rule can
    neither satisfy nor break it — and reading a key back out of a dict
    (`estimate["days_remaining"]`) is a STRING token, which is exactly
    the one shape a page module is allowed to use.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    names = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME:
            names.add(token.string)
    return names


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

    # 30-05-PLAN.md Task 1 (CFG-85): two shared helpers every Aspect-card
    # check below uses, defined once near the top of main() so every
    # `check(...)` call site below (which runs its check function
    # IMMEDIATELY, in source order) can already see them by name.
    #
    # Every mechanism the accordion rebuild retires outright — grepped
    # whole-repo for a surviving consumer before 30-04-PLAN.md's own
    # commit landed. Kept here as its own named tuple, not six inline
    # `in` checks, so a future reader can see exactly what "retired
    # mechanism" means without re-deriving it, and so
    # `_aspect_card_full_shape_checklist()` below can assert their
    # absence as one relationship rather than six separate assertions.
    _ASPECT_RETIRED_MARKUP_TOKENS = (
        "theme-carousel", "frame-colours", "colour_usage", "usage-panel",
        "__dots", "theme-chip-grid--strip",
    )

    def _aspect_usage_row_bounds(rendered, usage):
        """The `[start, end)` slice of `rendered` covering exactly one
        Aspect accordion row (its own `<details ... data-usage=
        "{usage}">` through the next row's opening tag, or — for the
        last row in `config_page.COLOUR_USAGES` — through the "What it
        watches" supersection's own id-anchored heading, which always
        renders unconditionally right after the Aspect card (and its
        sibling calendar disconnect form, when present) on the Display
        scope every caller below renders through. 30-05-PLAN.md Task 1
        (CFG-85): a shared helper so every row-scoped check below
        locates a row the same way, exactly once.

        30-06-PLAN.md Task 3: the last-row fallback is REPOINTED. It
        used to search for the separate Calendar card's own nested-
        wrapper `<div class="page-section page-section--nested" ...>`
        — that card is retired outright (its connection block is now
        INSIDE this same Aspect card's own Calendar row), so nothing on
        the page matches that literal any more; worse, every OTHER
        Display-scope card (Runway, Quiet hours) is wrapped with the
        `theme-status`/`theme-status--nested` base class, never
        `page-section`, so that literal was never a safe "next card"
        anchor even coincidentally. `DISPLAY_WATCHES_SECTION_ID` is a
        landmark id every caller's own `config_page.render(...,
        scope=config_page.SCOPE_DISPLAY)` render always carries,
        regardless of whether Runway itself is present.
        """
        usages = list(config_page.COLOUR_USAGES)
        idx = usages.index(usage)
        start = rendered.index('data-usage="%s"' % usage)
        if idx + 1 < len(usages):
            end = rendered.index('data-usage="%s"' % usages[idx + 1], start)
        else:
            end = rendered.index('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID, start)
        return start, end

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
    # 19-07-PLAN.md Task 1 (D-07/A-25): handle_post()'s new optional
    # `errors` dict parameter — the legacy no-errors callers stay
    # byte-identical, and each new field-level pre-check fills exactly
    # one keyed message without changing the returned flash-key string.
    # ------------------------------------------------------------------

    def _handle_post_no_errors_arg_returns_identical_flash_keys():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            valid_flash = config_page.handle_post({"theme": "white"}, ctx)
            if valid_flash != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for a representative valid save, got %r" % (valid_flash,)
            invalid_flash = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
            if invalid_flash != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a representative invalid save, got %r" % (invalid_flash,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx) with no errors argument still returns exactly the same flash keys it did "
        "before this plan, for both a representative valid save and a representative invalid save",
        _handle_post_no_errors_arg_returns_identical_flash_keys)

    def _handle_post_errors_dict_filled_for_each_real_user_error_field():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            cases = (
                ({"wake_interval_s": "7"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
                ({"wake_interval_s": "abc"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
                ({"quiet_hours_start": "24:00"}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                ({"quiet_hours_start": ""}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                ({"quiet_hours_end": "not-a-time"}, "quiet_hours_end", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                (
                    {
                        "calendar_url": "https://example.com/feed.ics",
                        "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
                    },
                    "calendar_url", config_page.ERROR_CALENDAR_URL_INVALID,
                ),
            )
            for form, field, expected_message in cases:
                errors = {}
                flash_key = config_page.handle_post(form, ctx, errors=errors)
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for form=%r, got %r" % (form, flash_key)
                if errors != {field: expected_message}:
                    return False, "expected errors == {%r: %r} for form=%r, got %r" % (
                        field, expected_message, form, errors)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx, errors=d) fills d with exactly one field-keyed message for each real-user-error "
        "case (wake_interval_s non-numeric/out-of-range, quiet_hours_start/quiet_hours_end malformed including "
        "empty, and a contradictory calendar_url+calendar_disconnect submission)",
        _handle_post_errors_dict_filled_for_each_real_user_error_field)

    def _handle_post_errors_dict_stays_empty_on_a_valid_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            errors = {}
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "quiet_hours_start": "22:30",
                    "quiet_hours_end": "06:15", "wake_interval_s": "120",
                },
                ctx, errors=errors)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if errors != {}:
                return False, "expected errors to stay empty on a valid save, got %r" % (errors,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx, errors=d) leaves d empty when the save succeeds",
        _handle_post_errors_dict_stays_empty_on_a_valid_save)

    def _handle_post_empty_quiet_hours_start_writes_nothing():
        # The all-or-nothing contract's own direct pin for the NEW
        # pre-check: an empty quiet_hours_start must reject before
        # save_device_config() is ever called, leaving a pre-existing
        # config byte-identical - not merely returning the right flash
        # key.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            errors = {}
            flash_key = config_page.handle_post(
                {"theme": "white", "quiet_hours_start": ""}, ctx, errors=errors)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for an empty quiet_hours_start, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to stay byte-identical, it changed"
            if errors != {"quiet_hours_start": config_page.ERROR_QUIET_HOURS_TIME_SHAPE}:
                return False, "expected exactly one quiet_hours_start error, got %r" % (errors,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"theme\": \"white\", \"quiet_hours_start\": \"\"}, ctx, errors=d) rejects the whole save, "
        "writes nothing (the theme must not persist either), and reports the error on quiet_hours_start alone",
        _handle_post_empty_quiet_hours_start_writes_nothing)

    def _local_quiet_hours_regex_agrees_with_save_device_config():
        # 19-07-PLAN.md Task 1: this module's own local HH:MM shape gate
        # (_QUIET_HOURS_TIME_RE) is a UX pre-check only -
        # save_device_config()'s identical gate stays authoritative. This
        # pins the two never silently drifting apart, over the exact
        # table of inputs the plan names.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            for candidate in ("", "7:00", "07:00", "24:00", "abc", "23:59", "00:00"):
                pre_check_says_ok = bool(config_page._QUIET_HOURS_TIME_RE.match(candidate))
                try:
                    device_config.save_device_config(
                        tmpdir, quiet_hours_start=candidate)
                    save_device_config_says_ok = True
                except ValueError:
                    save_device_config_says_ok = False
                if pre_check_says_ok != save_device_config_says_ok:
                    return False, (
                        "disagreement for %r: pre-check says ok=%r, save_device_config() says ok=%r"
                        % (candidate, pre_check_says_ok, save_device_config_says_ok))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "config_page._QUIET_HOURS_TIME_RE agrees with server.device_config.save_device_config()'s own HH:MM "
        "shape gate over the table \"\"/\"7:00\"/\"07:00\"/\"24:00\"/\"abc\"/\"23:59\"/\"00:00\"",
        _local_quiet_hours_regex_agrees_with_save_device_config)

    # ------------------------------------------------------------------
    # 19-07-PLAN.md Task 2 (D-07/A-25): render() repopulates every
    # control from a rejected save's own submission and renders each
    # field's error message and aria wiring — while staying byte-
    # identical to today whenever errors/submitted are not passed.
    # ------------------------------------------------------------------

    _TASK2_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "now": "2026-09-07T09:12:04+00:00",
    }

    def _render_no_new_args_byte_identical_and_no_field_error_markup():
        plain = config_page.render(_TASK2_BASE_CTX)
        explicit_none = config_page.render(_TASK2_BASE_CTX, errors=None, submitted=None)
        if plain != explicit_none:
            return False, "expected render(ctx) to be byte-identical to render(ctx, errors=None, submitted=None)"
        if "field-error" in plain:
            return False, "expected no field-error markup when no errors are passed"
        return True, ""
    check(
        "render(ctx) with no new arguments is byte-identical to render(ctx, errors=None, submitted=None) and "
        "contains no field-error markup",
        _render_no_new_args_byte_identical_and_no_field_error_markup)

    def _render_wake_interval_error_shows_message_value_and_aria():
        rendered = config_page.render(
            _TASK2_BASE_CTX, errors={"wake_interval_s": "msg"},
            submitted={"wake_interval_s": "7"})
        if rendered.count("msg") != 1:
            return False, "expected the error message to render exactly once, got %d" % rendered.count("msg")
        if 'value="7"' not in rendered:
            return False, "expected the submitted value 7 to be echoed back into the input"
        # 22-10-PLAN.md Task 3 (B17): retargeted in place for the new id=.
        input_match = re.search(
            r'<input type="number" id="[^"]*" name="wake_interval_s"[^>]*>', rendered)
        if not input_match:
            return False, "expected the wake_interval_s input to still be present"
        if 'aria-invalid="true"' not in input_match.group(0):
            return False, "expected aria-invalid=\"true\" on the errored input"
        describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
        if not describedby_match:
            return False, "expected an aria-describedby attribute on the errored input"
        # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - the
        # value is now a SPACE-SEPARATED list (the hint id first, then
        # the error id), not a single id, so each token must be checked
        # individually against the rendered page's own ids.
        ids = describedby_match.group(1).split(" ")
        if len(ids) != 2:
            return False, "expected exactly two space-separated ids (hint, then error), got %r" % (ids,)
        if ids[0] != config_page.WAKE_INTERVAL_SECTION_CAPTION_ID:
            return False, "expected the hint id to come first, got %r" % (ids,)
        for token in ids:
            if ('id="%s"' % token) not in rendered:
                return False, "expected an element carrying id=%r matching aria-describedby" % (token,)
        return True, ""
    check(
        "render(ctx, errors={\"wake_interval_s\": \"msg\"}, submitted={\"wake_interval_s\": \"7\"}) renders the "
        "message once, echoes value=\"7\" back into the input, and sets aria-invalid plus a matching "
        "aria-describedby",
        _render_wake_interval_error_shows_message_value_and_aria)

    def _render_submitted_theme_id_checked_even_when_differs_from_stored():
        rendered = config_page.render(
            dict(_TASK2_BASE_CTX, device_config={"theme": "white", "tracked_runway": "3"}),
            submitted={"theme": "black"}, scope=config_page.SCOPE_DISPLAY)
        if not re.search(r'name="theme" value="black"[^>]*checked', rendered):
            return False, "expected the submitted theme (black) to render checked even though the stored theme is white"
        if re.search(r'name="theme" value="white"[^>]*checked', rendered):
            return False, "expected the stored theme (white) to NOT render checked once a different submission is being repopulated"
        return True, ""
    check(
        "a submitted theme id is rendered as the CHECKED radio even when it differs from the stored theme "
        "(D-07 repopulation)",
        _render_submitted_theme_id_checked_even_when_differs_from_stored)

    def _render_both_quiet_hours_time_inputs_carry_required():
        rendered = config_page.render(_TASK2_BASE_CTX)
        start_match = re.search(r'<input type="time" name="quiet_hours_start"[^>]*>', rendered)
        end_match = re.search(r'<input type="time" name="quiet_hours_end"[^>]*>', rendered)
        if not start_match or "required" not in start_match.group(0):
            return False, "expected the quiet_hours_start input to carry required"
        if not end_match or "required" not in end_match.group(0):
            return False, "expected the quiet_hours_end input to carry required"
        return True, ""
    check(
        "both quiet-hours time inputs carry required in the rendered Settings page",
        _render_both_quiet_hours_time_inputs_carry_required)

    def _calendar_connection_url_error_never_echoes_the_submitted_secret():
        # 20-09-PLAN.md Task 1 (D-14c), retargeted by 21-07-PLAN.md
        # Task 1 (D-13), retargeted again by 30-06-PLAN.md Task 3 after
        # _calendar_connection_html()'s own retirement: the write-only calendar_url
        # field's own `errors` parameter now lives directly on
        # _calendar_connection_html() — it never accepts `submitted` at
        # all (nothing to repopulate: the one field it renders is
        # write-only), so there is no submitted URL for it to echo in
        # the first place. The property is unchanged from the retired
        # check; only the call site and its tuple return shape move.
        rendered, _disconnect_form_html = config_page._calendar_connection_html(
            False, False, None, None, "2026-09-07T09:12:04+00:00", 0,
            errors={"calendar_url": "msg"})
        if "msg" not in rendered:
            return False, "expected the calendar_url error message to render"
        if 'name="calendar_url"' not in rendered:
            return False, "expected the calendar_url field itself to still render"
        after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
        if "value=" in after_name:
            return False, "expected no value attribute on the calendar_url field even with an error present"
        return True, ""
    check(
        "_calendar_connection_html(..., errors={\"calendar_url\": \"msg\"}) renders the error message "
        "under the field while the write-only field itself still carries no value attribute at all "
        "(D-07/T-19-12/D-13, retargeted after _calendar_connection_html()'s retirement, 30-06-PLAN.md Task 3)",
        _calendar_connection_url_error_never_echoes_the_submitted_secret)

    def _style_css_styles_field_error():
        style_path = os.path.join(REPO_ROOT, "companion", "static", "style.css")
        with open(style_path, encoding="utf-8") as fh:
            css = fh.read()
        idx = css.find(".field-error")
        if idx == -1:
            return False, "expected a .field-error rule in companion/static/style.css"
        window = css[idx:idx + 400]
        if "--color-status-error" not in window:
            return False, "expected .field-error to read the existing --color-status-error token"
        return True, ""
    check(
        "companion/static/style.css styles .field-error using the existing --color-status-error token "
        "(cross-file DOM contract guard)",
        _style_css_styles_field_error)

    # ------------------------------------------------------------------
    # 19-07-PLAN.md Task 3 (D-07/A-25): the legacy no-errors-arg contract
    # is intact even for a rejected save — companion/app.py's own
    # errors-branch (which now ALSO fires whenever errors is non-empty)
    # depends on handle_post() still returning FLASH_SAVE_FAILED, not
    # some new sentinel, when no errors dict is passed at all.
    # ------------------------------------------------------------------

    def _handle_post_rejected_save_without_errors_arg_still_returns_save_failed():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED with no errors argument, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a rejected save still returns FLASH_SAVE_FAILED from handle_post() when no errors dict is passed "
        "(the legacy contract is intact)",
        _handle_post_rejected_save_without_errors_arg_still_returns_save_failed)

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

    def _dirty_state_js_delegates_change_and_input_at_document_level_and_has_no_forbidden_syntax():
        # 27-04-PLAN.md Task 2 (CFG-63): SUPERSEDED this check's own
        # pre-27-04 subject — DIRTY_SECTION_ATTR and the dirty-ready
        # marker were both retired along with the bar that read them.
        #
        # 28-08-PLAN.md Task 3 (CFG-77/CFG-78), 2026-09-16: RENAMED and
        # retargeted in the OPPOSITE direction, outside this plan's own
        # named three JS-contract checks but broken as a direct,
        # unavoidable consequence of restoring dirtySectionLabels() and
        # the dual change/input delegation (Rule 1: a check asserting
        # "references neither DIRTY_SECTION_ATTR nor dirty-ready" cannot
        # survive a plan whose whole point is restoring
        # dirtySectionLabels()'s own [data-dirty-section] reader).
        # DIRTY_SECTION_ATTR's value DOES appear again now — restored,
        # as dirtySectionLabels()'s own wrapper-lookup attribute. The
        # dirty-ready/dirty-shown MARKERS still do NOT survive — this
        # restoration deliberately does not bring either one back at all
        # (28-08-PLAN.md Task 3: the CSS clearance mechanism is
        # :has(.dirty-bar) now, which needs no script-written marker).
        # B1's own fix (22-01-PLAN.md Task 2, D-01) survives unchanged:
        # no form.addEventListener("change"/"input" registration may
        # return, and the delegation must stay at the document level
        # gated on the control's own .form property — and D-04's own
        # change-only restriction is ITSELF superseded: the restored
        # bar listens for BOTH change and input again (6dea46a's own
        # pre-27-04 shape — a keystroke in the wake-interval/quiet-hours
        # fields updates the bar's live count as it's typed, the same
        # way it did before 27-04 ever ran).
        source = _read_static("dirty-state.js")
        if config_page.DIRTY_SECTION_ATTR not in source:
            return False, (
                "expected dirty-state.js to reference DIRTY_SECTION_ATTR's value again — "
                "dirtySectionLabels() is restored and reads it")
        if "dirty-ready" in source or "dirty-shown" in source:
            return False, (
                "expected dirty-state.js to carry neither the dirty-ready nor the dirty-shown "
                "marker — this restoration's own clearance mechanism is :has(.dirty-bar), which "
                "needs no script-written marker class")
        if 'form.addEventListener("change"' in source or 'form.addEventListener("input"' in source:
            return False, (
                "expected no surviving form.addEventListener(\"change\"/\"input\" registration "
                "(B1 regression) — delegation must stay document-level")
        for kind in ("change", "input"):
            call = 'document.addEventListener("%s"' % kind
            if call not in source:
                return False, "expected a document.addEventListener(%r registration" % (kind,)
        if "e.target.form === form" not in source and "e.target.form===form" not in source:
            return False, "expected the document-level delegation to gate on e.target.form === form"
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references DIRTY_SECTION_ATTR again (dirtySectionLabels() restored) but "
        "carries neither the retired dirty-ready nor dirty-shown marker, delegates BOTH change AND "
        "input at document level gated on e.target.form === form with no surviving "
        "form.addEventListener(\"change\"/\"input\" registration (B1), and contains none of "
        "innerHTML/let /const /=>/backtick (CFG-77/CFG-78, 28-08-PLAN.md Task 3)",
        _dirty_state_js_delegates_change_and_input_at_document_level_and_has_no_forbidden_syntax)

    def _live_preview_crossfades_through_one_class_shared_by_css_and_js():
        """23-10-PLAN.md Task 2 (D3/CFG-32): the live theme preview
        crossfades instead of cutting.

        The same cross-file DOM-contract shape the checks above already
        hold: one class literal, declared in style.css and driven from
        theme-preview.js, with neither file importing the other. The
        literal is written out here rather than imported, which is the
        point — if either side renames it, this check is what says so.

        The mechanism must be EVENT-DRIVEN, never timed. theme-preview.js
        carries a standing no-timer rule in its own header (and
        test_companion_app.py enforces it), and a crossfade on a timer is
        the specific way this goes wrong: the swap and the fade drift
        apart, and the preview settles on whichever the timer happened to
        win. `transitionend` is when the fade-out is genuinely over, and
        the image's own `load`/`error` is when the new frame is genuinely
        there.
        """
        fade_class = "theme-live-preview__image--swapping"
        css = _read_static("style.css")
        # Comment-stripped, and this was NOT a precaution: the first
        # version of the timer ban below was answered by this file's own
        # new paragraph explaining that the crossfade must never use a
        # timer. A scan over raw source is satisfied by a comment that
        # promises a rule nobody wrote, and broken by a comment that
        # explains one correctly - the same idiom test_companion_app.py's
        # motion-budget guard already records for style.css.
        js = re.sub(
            r"/\*.*?\*/|//[^\n]*", "", _read_static("theme-preview.js"), flags=re.DOTALL)

        base_marker = "\n.theme-live-preview__image {"
        if base_marker not in css:
            return False, "expected style.css to declare .theme-live-preview__image"
        base_idx = css.index(base_marker) + len(base_marker)
        base = css[base_idx:css.index("}", base_idx)]
        if "transition:" not in base:
            return False, (
                "expected .theme-live-preview__image to declare the crossfade transition on its "
                "own base rule, so the fade runs in BOTH directions from one declaration")
        decl = base[base.index("transition:"):]
        decl = decl[:decl.index(";") + 1]
        if "opacity" not in decl:
            return False, (
                "expected the live preview's transition to name opacity, got %r" % (decl,))
        if "var(--motion-fast)" not in decl:
            return False, (
                "expected the live preview crossfade to spend var(--motion-fast) — somebody just "
                "clicked a chip and is watching for the preview to answer, got %r" % (decl,))

        fade_marker = "\n.%s {" % fade_class
        if fade_marker not in css:
            return False, "expected style.css to declare .%s" % (fade_class,)
        fade_idx = css.index(fade_marker) + len(fade_marker)
        fade_body = css[fade_idx:css.index("}", fade_idx)]
        if "opacity: 0" not in fade_body:
            return False, (
                "expected .%s to be the opacity-0 half of the crossfade, got %r"
                % (fade_class, fade_body.strip()))

        if fade_class not in js:
            return False, (
                "theme-preview.js must drive the crossfade through the same %r class style.css "
                "declares — neither file imports the other, and this literal is the only thing "
                "keeping them in step" % (fade_class,))
        for token in ("transitionend", '"load"', '"error"'):
            if token not in js:
                return False, (
                    "expected theme-preview.js to listen for %s — the crossfade must be driven "
                    "by the events that actually mark the fade-out ending and the new frame "
                    "arriving, never by a timer" % (token,))
        # The one stall an event-driven crossfade can have, pinned as a
        # structural fact because its browser-level reproduction is
        # probabilistic (measured 4 stalls in 14 runs before the fix, 0
        # in 14 after). A transitionend only arrives if a transition
        # actually RAN, and it does not run when the image is already
        # invisible, nor when the class is removed and re-added without a
        # style recalculation in between - an image load and a click
        # landing in the same frame does exactly that. The preview then
        # sits at opacity 0 on the discarded theme forever. Consulting
        # the COMPUTED opacity is what lets the script tell "a fade is
        # about to run" from "there is nothing left to fade", so a swap
        # can never be waiting on an event that will not come.
        if "getComputedStyle" not in js:
            return False, (
                "theme-preview.js must consult the COMPUTED opacity before waiting on "
                "transitionend: a transition that never runs never ends, and the preview then "
                "sits invisible on the discarded theme forever (measured: 4 stalls in 14 runs "
                "without this)")
        for banned in ("setTimeout", "setInterval", "requestAnimationFrame"):
            if banned in js:
                return False, (
                    "theme-preview.js must stay timer-free (%r found): a timed crossfade lets the "
                    "swap and the fade drift apart, and the preview settles on whichever won"
                    % (banned,))
        # T8 survives: dirty-state.js's Cancel handler calls this, and a
        # crossfade that bypassed refresh() would leave Cancel showing
        # the discarded theme again — the exact defect T8 closed.
        if "SkyPaneLivePreview" not in js or "refresh" not in js:
            return False, (
                "expected theme-preview.js to keep exposing window.SkyPaneLivePreview.refresh() "
                "— dirty-state.js's Cancel handler calls it after form.reset(), and T8 exists "
                "because reset() fires no change event")
        return True, ""
    check(
        "the live theme preview CROSSFADES rather than cuts: .theme-live-preview__image declares an "
        "opacity transition at var(--motion-fast) on its own base rule, a .theme-live-preview__image--swapping "
        "class carries the opacity-0 half, theme-preview.js drives that same class literal from transitionend "
        "and the image's own load/error (never a timer) while consulting the computed opacity so a swap can "
        "never wait on a transition that never runs, and T8's window.SkyPaneLivePreview.refresh() survives "
        "(D3/CFG-32, 23-10-PLAN.md Task 2)",
        _live_preview_crossfades_through_one_class_shared_by_css_and_js)

    # ------------------------------------------------------------------
    # 19-10-PLAN.md Task 2 (D-10/A-28): a beforeunload guard, keyed on
    # the existing countDifferences() predicate, warns before a real
    # navigation discards unsaved settings edits.
    # ------------------------------------------------------------------

    def _dirty_state_js_beforeunload_guard_reuses_count_differences():
        source = _read_static("dirty-state.js")
        if "beforeunload" not in source:
            return False, "expected dirty-state.js to register a beforeunload listener"
        if "returnValue" not in source:
            return False, "expected dirty-state.js's beforeunload guard to set evt.returnValue"
        if "preventDefault" not in source:
            return False, "expected dirty-state.js's beforeunload guard to call evt.preventDefault()"
        # 27-04-PLAN.md (CFG-63): located by the LISTENER REGISTRATION
        # itself, not the bare word — this file's own header prose now
        # discusses the leave-guard by name before the registration
        # appears in source, and a bare-word search would find that prose
        # instead of the real listener body.
        listener_marker = 'addEventListener("beforeunload"'
        if listener_marker not in source:
            return False, "expected dirty-state.js to call addEventListener(\"beforeunload\", ...)"
        beforeunload_idx = source.index(listener_marker)
        # The guard's own listener body must reference countDifferences -
        # reused, never reimplemented as a separate flag that can drift
        # from the form's own dirty state.
        listener_body = source[beforeunload_idx:beforeunload_idx + 400]
        if "countDifferences" not in listener_body:
            return False, "expected the beforeunload listener's body to reference countDifferences"
        if 'addEventListener("submit"' not in source:
            return False, "expected dirty-state.js to register a submit listener on the form"
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js registers a beforeunload listener whose body references countDifferences and sets "
        "returnValue/calls preventDefault, and a submit listener clears the guard; contains none of "
        "innerHTML/let /const /=>/backtick",
        _dirty_state_js_beforeunload_guard_reuses_count_differences)

    # ------------------------------------------------------------------
    # 19-10-PLAN.md Task 3 (D-14/S-04): cross-file guard keeping
    # dirty-state.js's preset reader in agreement with config_page.py's
    # QUIET_HOURS_PRESET_ATTR/data-preset-* markup.
    # ------------------------------------------------------------------

    def _dirty_state_js_references_quiet_preset_attrs():
        source = _read_static("dirty-state.js")
        for literal in (
                config_page.QUIET_HOURS_PRESET_ATTR, "data-preset-start",
                "data-preset-end", "data-preset-enabled"):
            if literal not in source:
                return False, "expected dirty-state.js to reference the literal %r" % (literal,)
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references config_page.QUIET_HOURS_PRESET_ATTR's literal value and the three "
        "data-preset-* attribute names, and contains none of innerHTML/let /const /=>/backtick",
        _dirty_state_js_references_quiet_preset_attrs)

    def _style_css_carries_no_hide_rule_for_static_save_fallback_attr():
        # 19-10-PLAN.md (D-09/A-27): retargeted from .js to .dirty-ready;
        # 22-01-PLAN.md Task 2 (D-01/B1) retargeted it AGAIN, to require
        # BOTH .dirty-ready and .dirty-shown (proven liveness rather than
        # mere element presence). 27-03-PLAN.md Task 2 (CFG-64) retargeted
        # it a THIRD time, in the opposite direction: the floor is kept
        # by render()'s emission being unconditional now (Task 1's own
        # source proof), so the two narrowing markers had nothing left
        # to prove on THIS rule and the selector reverted to the plain
        # script-presence gate it originally shipped as.
        #
        # 28-08-PLAN.md Task 2 (CFG-77/CFG-78), 2026-09-16: RENAMED and
        # retargeted a FOURTH time, in a direction none of the three
        # above anticipated — the hide rule itself is GONE, not merely
        # re-keyed, because the button it hid is now the restored bar's
        # own visible Save (relocated by Task 1) and its visibility is
        # the bar's OWN `hidden` attribute, never a second, independent
        # CSS hide mechanism for the same element (the exact orphan
        # CFG-78 forbids). This check now asserts the new contract: NO
        # RULE SELECTOR anywhere in style.css still contains
        # STATIC_SAVE_FALLBACK_ATTR's literal value — comments MAY
        # (indeed do) still name it in prose, recording the history —
        # while the three original B1/P0 sentences, the dated
        # 27-03-PLAN.md SUPERSEDED paragraph, AND a new dated 28-08
        # paragraph all survive. `grep -c 'data-static-save-fallback'
        # companion/static/style.css` is >1 both before and after this
        # plan (prose mentions inside comment blocks) — asserting "0
        # occurrences" would be wrong on both sides of the change, so
        # this check asserts the RELATIONSHIP (no occurrence sits inside
        # a rule selector) rather than a raw count.
        source = _read_static("style.css")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in source:
            return False, "expected style.css to still mention STATIC_SAVE_FALLBACK_ATTR's literal value somewhere (in prose, recording the history)"
        # Strip comments first (this file's own established idiom, used
        # by the motion-budget check and others), then check every
        # remaining occurrence sits OUTSIDE a rule selector — i.e. a
        # comment-stripped occurrence would only ever appear if a live
        # rule still targeted the attribute.
        stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        if config_page.STATIC_SAVE_FALLBACK_ATTR in stripped:
            idx = stripped.index(config_page.STATIC_SAVE_FALLBACK_ATTR)
            return False, (
                "expected NO rule selector anywhere in style.css (comments stripped) to still "
                "reference %r, but found one — the hide rule this check used to require is "
                "retired outright (28-08-PLAN.md Task 2, CFG-77/CFG-78); context: %r"
                % (config_page.STATIC_SAVE_FALLBACK_ATTR, stripped[max(0, idx - 60):idx + 60]))
        # THE SUPERSEDED CONTRACT IS AMENDED IN WRITING, NOT ERASED: the
        # original comment's own distinctive sentences must still be
        # present (its history survives), and both a dated Phase 27
        # paragraph AND a dated Phase 28 paragraph must follow it naming
        # what replaced it, each time.
        for distinctive in (
                "PROVEN its own replacement bar is actually live",
                "turned out to still be element PRESENCE, not proven liveness (B1)",
                "B1's proven-liveness fix"):
            if distinctive not in source:
                return False, (
                    "expected the ORIGINAL comment's own sentence %r to survive verbatim — "
                    "the B1/P0 contract must be superseded in writing, not deleted" % (distinctive,))
        if "27-03-PLAN.md" not in source or "SUPERSEDED" not in source:
            return False, (
                "expected a dated 27-03-PLAN.md paragraph stating the contract is SUPERSEDED, "
                "not merely that the rule changed")
        if "28-08-PLAN.md Task 2" not in source:
            return False, (
                "expected a dated 28-08-PLAN.md Task 2 paragraph stating the hide rule itself is "
                "now retired — the button it hid became the bar's own visible Save")
        return True, ""
    check(
        "style.css carries NO rule selector referencing STATIC_SAVE_FALLBACK_ATTR any more — the "
        "hide rule is retired outright, its button now the restored bar's own visible Save — "
        "while the B1/P0 contract and the dated 27-03/28-08 SUPERSEDED paragraphs all survive in "
        "writing (CFG-77/CFG-78, 28-08-PLAN.md Task 2)",
        _style_css_carries_no_hide_rule_for_static_save_fallback_attr)

    def _style_css_carries_no_rule_for_the_retired_save_status_region():
        # 28-09-PLAN.md Task 1 (CFG-78): the check immediately above
        # (28-08-PLAN.md Task 2) already proves the STATIC_SAVE_FALLBACK_
        # ATTR half of the orphan-rule clause — no rule selector still
        # targets the retired hide mechanism. This check proves the OTHER
        # half: `.save-status`, the retired auto-save status region's own
        # selector (27-04-PLAN.md, CFG-63 — deleted outright, not
        # relocated), carries no live RULE anywhere in style.css either,
        # while the comment prose that narrates its own retirement
        # survives. Re-derived live on the finished tree rather than
        # pasted from planning time: `grep -n 'save-status'
        # companion/static/style.css` is 6 hits today, every one inside a
        # `/* ... */` block comment (none a rule selector) — the
        # planning-time interfaces figure (a stale 5) is a baseline for
        # spotting a miscount, never an expectation asserted here as a
        # literal count.
        source = _read_static("style.css")
        if "save-status" not in source:
            return False, (
                "expected style.css to still mention save-status somewhere, in prose, "
                "narrating its own retirement")
        # Strip comments first (this file's own established idiom, used
        # by the motion-budget check and the STATIC_SAVE_FALLBACK_ATTR
        # check above), then require zero RULE selectors containing
        # .save-status. A rule selector reads as `.save-status` followed
        # eventually by `{` with no intervening `{`/`}` — distinct from a
        # bare substring match, which strip-then-`in` alone cannot tell
        # apart from (e.g.) a comment fragment that survived stripping
        # incorrectly.
        stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        rule_match = re.search(r"\.save-status\b[^{}]*\{", stripped)
        if rule_match:
            idx = rule_match.start()
            return False, (
                "expected NO rule selector anywhere in style.css (comments stripped) to "
                "still target .save-status — its own retired region is gone outright "
                "(27-04-PLAN.md, CFG-63) and no rule should still reach for it; context: %r"
                % (stripped[max(0, idx - 60):idx + 60],))
        return True, ""
    check(
        "style.css carries no live RULE selector for the retired .save-status auto-save "
        "status region (comments stripped before scanning) while the comment prose "
        "narrating its own retirement survives verbatim — the .save-status half of the "
        "orphan-rule clause the STATIC_SAVE_FALLBACK_ATTR check above does not already "
        "cover, re-derived on the finished tree rather than pasted from planning time "
        "(CFG-78, 28-09-PLAN.md Task 1)",
        _style_css_carries_no_rule_for_the_retired_save_status_region)

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

    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the check that used to live
    # here (_style_css_needs_no_new_selector_for_display_group) is deleted
    # outright along with display_group() itself — there is no longer a
    # Display group for style.css to need, or not need, a new selector for.

    def _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
        # 06.6.4.1.1-05: the cross-module route contract — every chip's
        # <img src> is built from theme_preview.THEME_PREVIEW_ROUTE_PREFIX
        # (rebound as config_page.THEME_PREVIEW_ROUTE_PREFIX) plus the
        # theme's own registry id, asserted against the constant rather
        # than a re-typed literal, for every entry in THEME_IDS.
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() directly onto the ONE low-level chip-grid
        # renderer it used to call twice — _theme_chip_grid_html()'s own
        # per-chip output shape is unchanged by this plan.
        rendered = config_page._theme_chip_grid_html("theme", "white")
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
        #
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() (which used to call this grid builder twice)
        # onto a single _theme_chip_grid_html() call directly — the
        # per-chip dot count this check pins is a property of that one
        # low-level function, unaffected by how many usage panels the
        # Frame colours card now composes it into.
        rendered = config_page._theme_chip_grid_html("theme", "white")
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
        "every theme chip carries exactly two .theme-chip__dot swatches whose inline background values "
        "equal _palette_hex() computed from that theme's own departing_index/arriving_index "
        "(06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by 21-05-PLAN.md Task 1 D-06 "
        "once theme_fieldset() is retired)",
        _theme_chip_swatch_dots_carry_real_palette_hex_values)

    def _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
        # 06.6.4.1.1-05: the markup half of the CSS-only selection reveal
        # — every chip's radio is visually-hidden (never display:none, so
        # keyboard/no-JS selection keeps working natively), and every chip
        # carries a .theme-chip__check glyph with its visually-hidden
        # "Selected" text, present on all 16 chips regardless of which one
        # is actually selected.
        #
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() onto a single _theme_chip_grid_html() call —
        # this low-level function's own per-chip markup shape (and this
        # check's premise) is unaffected by the Frame colours card's own
        # multi-panel composition above it.
        rendered = config_page._theme_chip_grid_html("theme", "white")
        theme_count = len(device_config.THEME_IDS)
        if rendered.count('name="theme" value="') != theme_count:
            return False, "expected %d theme radios, got %d" % (theme_count, rendered.count('name="theme" value="'))
        if rendered.count('class="visually-hidden"') < theme_count:
            return False, "expected every chip's radio to carry class=\"visually-hidden\""
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('<span class="theme-chip__check">') != theme_count:
            return False, (
                "expected exactly %d .theme-chip__check occurrences (one per chip, regardless of selection), "
                "got %d"
                % (theme_count, rendered.count('<span class="theme-chip__check">')))
        if rendered.count('<span class="visually-hidden">Selected</span>') != theme_count:
            return False, "expected every chip's check glyph to carry the visually-hidden \"Selected\" text"
        return True, ""
    check(
        "every theme chip's radio carries class=\"visually-hidden\" (never display:none) and every chip "
        "carries a .theme-chip__check glyph with visually-hidden \"Selected\" text, present on all chips "
        "regardless of selection (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by "
        "21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired)",
        _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip)

    # ------------------------------------------------------------------
    # 15-04-PLAN.md (D-04/D-05): the arrivals-override checkbox, its
    # revealed second chip grid, and handle_post()'s clearable-checkbox
    # contract (15-VALIDATION.md row 7).
    # ------------------------------------------------------------------

    def _aspect_arrivals_row_carries_leading_option_no_checkbox():
        # 30-05-PLAN.md Task 1 (CFG-85): replaces the retired
        # _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox.
        # This control used to be a checkbox; the empty-string radio is
        # what keeps the clear signal honest now — kept as a comment
        # here for the same reason the old check carried it.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        leading_needle = (
            '<label class="leading-option">'
            '<input type="radio" name="theme_arriving" value="" class="visually-hidden" form="%s"'
            % config_page.SETTINGS_FORM_ID)
        if leading_needle not in rendered:
            return False, (
                "expected the arrivals row's leading option to carry class=\"leading-option\" and "
                "form=%r" % (config_page.SETTINGS_FORM_ID,))
        if 'type="checkbox"' in rendered:
            return False, "expected no <input type=\"checkbox\"> anywhere in the Aspect card"
        return True, ""
    check(
        "the arrivals row carries a leading Same-as-departures option submitting the empty string "
        "(class=\"leading-option\", form=settings-form), and no checkbox-based override control "
        "exists anywhere on the page (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired "
        "_frame_colours_arrivals_grid_carries_leading_chip_no_checkbox)",
        _aspect_arrivals_row_carries_leading_option_no_checkbox)

    def _aspect_arrivals_override_preselects_the_override_not_same_as_departures():
        # 30-05-PLAN.md Task 1 (CFG-85): replaces the retired
        # _frame_colours_arrivals_override_preselects_the_override_not_
        # same_as_departures. Locates the arrivals row by its own
        # data-usage attribute (never COLOUR_USAGE_PANEL_TARGET_ATTR,
        # retired), and asserts the calendar row is unaffected in the
        # same render — that cross-row independence is the relationship
        # the old check was really protecting.
        rendered = config_page.render({
            "device_config": {
                "theme": "white", "tracked_runway": "3", "theme_arriving": "black"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        arrivals_start, arrivals_end = _aspect_usage_row_bounds(
            rendered, config_page.COLOUR_USAGE_ARRIVALS)
        arrivals_segment = rendered[arrivals_start:arrivals_end]
        if not re.search(r'name="theme_arriving" value="black"[^>]*checked', arrivals_segment):
            return False, "expected the arrivals row's checked radio to be the stored override (black)"
        if re.search(r'name="theme_arriving" value=""[^>]*checked', arrivals_segment):
            return False, (
                "expected the leading Same-as-departures option to NOT be checked once an "
                "override is set")
        if re.search(r'name="theme_arriving" value="white"[^>]*checked', arrivals_segment):
            return False, (
                "expected the departures theme (white) to NOT be marked selected in the arrivals "
                "row once an override is set")
        summary_segment = arrivals_segment.split("</summary>", 1)[0]
        override_label = escape_html(i18n.t(device_config.theme_label("black")))
        if override_label not in summary_segment:
            return False, "expected the arrivals row's summary meta to name the override's own label"
        same_as_label = escape_html(i18n.t(config_page.SAME_AS_DEPARTURES_LABEL))
        if same_as_label in summary_segment:
            return False, (
                "expected the arrivals row's summary meta to NOT read Same-as-departures once an "
                "override is set")
        calendar_start, calendar_end = _aspect_usage_row_bounds(
            rendered, config_page.COLOUR_USAGE_CALENDAR)
        calendar_segment = rendered[calendar_start:calendar_end]
        if not re.search(r'name="calendar_theme_id" value=""[^>]*checked', calendar_segment):
            return False, (
                "expected the calendar row's leading Same-as-departures option to still be "
                "checked, unaffected by the arrivals override")
        return True, ""
    check(
        "a stored theme_arriving override pre-selects the OVERRIDE (not Same-as-departures, not the "
        "departures theme) in the arrivals row, names the override's own label in the row's summary "
        "meta, and leaves the calendar row's own Same-as-departures state unaffected in the same "
        "render (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired "
        "_frame_colours_arrivals_override_preselects_the_override_not_same_as_departures)",
        _aspect_arrivals_override_preselects_the_override_not_same_as_departures)

    def _handle_post_theme_arriving_valid_id_persists_chosen_id():
        # 21-05-PLAN.md Task 2 (D-09/R-07): retargeted — no checkbox
        # exists any more; submitting a real, membership-checked
        # theme_arriving id persists it outright.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "black",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme_arriving"] != "black":
                return False, "expected theme_arriving 'black' on disk, got %r" % (on_disk["theme_arriving"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a valid theme_arriving id persists it, with no checkbox field involved (D-06/D-09, "
        "retargeted from the retired arrivals-override checkbox)",
        _handle_post_theme_arriving_valid_id_persists_chosen_id)

    def _handle_post_theme_arriving_empty_string_clears_previous_override():
        # 21-05-PLAN.md Task 2 (D-09/R-07): retargeted — the clear
        # signal is now theme_arriving="" (the Frame colours card's own
        # leading "Same as departures" chip, Task 1), never
        # checkbox-absence.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "black",
                },
                ctx)
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "submitting theme_arriving='' failed to clear the override, got %r"
                    % (on_disk["theme_arriving"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with theme_arriving='' clears a previously-set override back to None (D-06/D-09, "
        "retargeted from the retired arrivals-override checkbox's own absence)",
        _handle_post_theme_arriving_empty_string_clears_previous_override)

    def _handle_post_calendar_theme_id_empty_string_saves_as_none():
        # 21-05-PLAN.md Task 2 (D-09/R-07): the parallel, lower-risk
        # half — calendar_theme_id never had a checkbox, so once its
        # gate exempts "", the existing pass-through plus
        # normalise_calendar_theme_id("")'s own documented None-degrade
        # already does the right thing (no second resolution block
        # needed).
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            config_page.handle_post({"calendar_theme_id": "white"}, {"state_dir": tmpdir})
            flash_key = config_page.handle_post({"calendar_theme_id": ""}, {"state_dir": tmpdir})
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] is not None:
                return False, (
                    "submitting calendar_theme_id='' failed to clear the override, got %r"
                    % (on_disk["calendar_theme_id"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with calendar_theme_id='' saves and reads back as None, mirroring theme_arriving's own "
        "empty-string clear signal (D-06/D-09)",
        _handle_post_calendar_theme_id_empty_string_saves_as_none)

    def _handle_post_crafted_non_member_theme_and_calendar_values_still_rejected():
        # 21-05-PLAN.md Task 2 (Pitfall 1): the empty string is carved
        # out of both gates, but every OTHER non-member value (a plain
        # invalid id, a value that merely looks close to a real one, a
        # bare space) is still rejected exactly as before — the gate is
        # widened, not weakened. Replaces the retired crafted-checkbox-
        # value check (that field no longer exists).
        for field, payload in (
                ("theme_arriving", "nope"), ("theme_arriving", " "),
                ("theme_arriving", "WHITE "), ("calendar_theme_id", "nope"),
                ("calendar_theme_id", " "), ("calendar_theme_id", "WHITE ")):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                flash_key = config_page.handle_post({field: payload}, {"state_dir": tmpdir})
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for %s=%r, got %r" % (field, payload, flash_key)
                if before != after:
                    return False, "expected device_config.json to be byte-identical for %s=%r, it changed" % (
                        field, payload)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post still rejects a crafted non-member theme_arriving/calendar_theme_id value (a plain "
        "invalid id, a bare space, a near-miss uppercase/trailing-space variant) and writes nothing — the "
        "empty-string exemption does not widen the gate to anything else (D-09/Pitfall 1)",
        _handle_post_crafted_non_member_theme_and_calendar_values_still_rejected)

    def _handle_post_nonmember_theme_arriving_rejected():
        # Task 2 <behavior> bullet 4, including a path-traversal-shaped
        # and a SQL-shaped payload, matching theme's own adversarial
        # coverage.
        for payload in ("chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post(
                    {"theme_arriving": payload},
                    ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for theme_arriving=%r, got %r" % (payload, flash_key)
                if before != after:
                    return False, "expected device_config.json to be byte-identical for theme_arriving=%r, it changed" % (payload,)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post with a non-member theme_arriving (a plain invalid id, a path-traversal-shaped payload, and a "
        "SQL-shaped payload) rejects the whole submission and writes nothing — '' is explicitly exempted from "
        "this rejection (D-09)",
        _handle_post_nonmember_theme_arriving_rejected)

    def _handle_post_theme_arriving_partial_post_still_carries_other_fields():
        # Task 2 <behavior> bullet 5: every other field's behaviour is
        # unchanged - a partial-field post still carries the other
        # settings forward. Retargeted from the retired checkbox onto
        # the plain theme_arriving field alone.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme_arriving": "white"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,)
            if on_disk["theme"] != "black":
                return False, "expected the existing theme to be carried forward unchanged, got %r" % (on_disk,)
            if on_disk["theme_arriving"] != "white":
                return False, "expected theme_arriving 'white' on disk, got %r" % (on_disk["theme_arriving"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post carrying only theme_arriving still carries the existing theme/runway forward unchanged "
        "(retargeted from the retired arrivals-override checkbox, D-09)",
        _handle_post_theme_arriving_partial_post_still_carries_other_fields)

    def _theme_arriving_clearable_contract_full_round_trip():
        # 15-VALIDATION.md row 7 - the acceptance criterion the whole plan
        # exists for. Named so a failure says plainly that the empty-
        # string clear signal stopped working. Proves the full sequence:
        # save with a chosen arrivals theme (confirm it persisted), save
        # again with theme_arriving="" (confirm theme_arriving comes back
        # None), and confirm every other setting from the first save
        # survived the second save unchanged. 21-05-PLAN.md Task 2
        # (D-09/R-07): retargeted from the retired checkbox's own
        # absence onto the new empty-string clear signal.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            first = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                },
                ctx)
            if first != config_page.FLASH_SAVED:
                return False, "expected the first save to return FLASH_SAVED, got %r" % (first,)
            after_first = device_config.load_device_config(tmpdir)
            if after_first["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' to persist after the first save, got %r"
                    % (after_first["theme_arriving"],))

            second = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving": "",
                },
                ctx)
            if second != config_page.FLASH_SAVED:
                return False, "expected the second (clearing) save to return FLASH_SAVED, got %r" % (second,)
            after_second = device_config.load_device_config(tmpdir)
            if after_second["theme_arriving"] is not None:
                return False, (
                    "theme_arriving='' failed to clear the override - expected theme_arriving "
                    "None, got %r" % (after_second["theme_arriving"],))
            if (
                after_second["theme"] != "white"
                or after_second["tracked_runway"] != "06-24"
                or after_second["led_enabled"] is not True
            ):
                return False, "expected every other setting to survive the second save unchanged, got %r" % (after_second,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "the clearable contract (15-VALIDATION.md row 7): a save with a chosen arrivals theme persists it, "
        "then a save with theme_arriving='' clears it back to None while every other setting survives "
        "unchanged (D-06/D-09, retargeted from the retired arrivals-override checkbox's own absence)",
        _theme_arriving_clearable_contract_full_round_trip)

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
        # 16-05-PLAN.md: the count is 7, not 6, now that Calendar joined
        # as the seventh and last group — again not a rename of this
        # check's own premise.
        # 20-11-PLAN.md Task 1: the count was 8, not 7, now that
        # Notifications joined as the eighth and last group — again not
        # a rename of this check's own premise. 21-05-PLAN.md Task 1
        # (D-06): the count drops back to 7 — theme_fieldset() (Theme's
        # own data-dirty-section) is retired outright, and its
        # replacement (the Frame colours card) only ever renders on the
        # Display scope, never on this legacy SCOPE_ALL render.
        # 21-07-PLAN.md Task 1 (D-13/Pitfall 2): the count drops to 6 —
        # the merged _calendar_connection_html() now embeds a real connect/replace
        # <form> in every state, which would nest inside <form id=
        # "settings-form"> on this legacy render, so it has no entry in
        # `builders` here any more either (Calendar's own data-dirty-
        # section entry only ever renders on the Display scope now,
        # exactly like Theme's).
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the count drops to 5 —
        # display_group() is retired outright and screens.GROUP_DISPLAY
        # is no longer a member of any screen type's own group tuple, so
        # this legacy render no longer contributes a Display entry either
        # (+0/-1: "Display" removed from the expected-groups comment).
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements on the rendered Settings page"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements on the rendered Settings page"
        if rendered.count(config_page.DIRTY_SECTION_ATTR) != 5:
            return False, (
                "expected exactly 5 %s occurrences (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications), got %d"
                % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))
        return True, ""
    check(
        "the rendered Settings page contains no <fieldset> and no <legend>, and exactly five "
        "data-dirty-section groups (Runway/Diagnostic LED/Quiet hours/Wake interval/"
        "Notifications — Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 "
        "D-06; Calendar's own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/"
        "Pitfall 2; Display's own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1)",
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
        # RETARGETED by 22-15-PLAN.md Task 1 (T6). This clause used to
        # read `border: 2px solid var(--color-accent);`. T6 is the
        # defect that selection shifted layout by 2px: under
        # `box-sizing: border-box` a 2px border still widens the OUTER
        # box of a `flex: 1 1 0` card (measured 98.67px against
        # 96.66/96.67px at 390px), so a selected card was a different
        # size from its siblings. The border is now constant at 1px and
        # only recolours; the 2px accent signal moved to an inset ring,
        # which occupies no layout space at all. Strictly narrower than
        # the clause it replaces: it pins BOTH halves of the new
        # treatment and additionally forbids the 2px border returning.
        if "border-color: var(--color-accent);" not in window:
            return False, ".runway-card--selected must recolour its constant 1px border to the accent"
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".runway-card--selected must carry T6's inset accent ring — the selection signal "
                "that replaced the layout-shifting 2px border")
        if "border: 2px" in window:
            return False, (
                ".runway-card--selected must never declare a 2px border again — that is T6, the "
                "2px layout shift this treatment exists to avoid")
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
        "idiom, added alongside (not replacing) their check glyph and their now-constant 1px border, whose "
        "2px accent signal moved to an inset ring (06.6.4.1.1-06, retargeted by 22-15-PLAN.md Task 1 for T6)",
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

        # Phase 15 D-05 used to add a SECOND @supports selector(:has(*))
        # block — the arrivals-checkbox CSS-only reveal — placed after
        # this one (the live-selection-state block quick task 260904-bbi
        # added); that block's own arrivals-reveal rule was later
        # retired outright by 21-05-PLAN.md Task 1 (D-06/D-09), but the
        # block itself survived one more phase because a SECOND,
        # unrelated rule (20-04-PLAN.md's Calendar-card fusion) still
        # lived inside it. 21-07-PLAN.md Task 3 (D-13/R-08/Pitfall 2)
        # retires that fusion rule too — with no rule left inside it,
        # the block itself is deleted outright, moving the file's own
        # total block count from 2 to 1. index() below still resolves to
        # this (the only remaining) block's own opening brace, so every
        # selector-position assertion below (idx < supports_idx meaning
        # "lives inside this block") is unaffected.
        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block (the live-selection-state one — the Calendar-card "
                "fusion block that used to follow it is retired outright by 21-07-PLAN.md Task 3), "
                "got %d" % (supports_marker, source.count(supports_marker)))
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

        # T6 (22-15-PLAN.md Task 1) retargets every "2px accent border"
        # clause in this check to the constant-1px-plus-inset-ring
        # treatment that replaced it, and additionally forbids the 2px
        # border ever returning. See
        # _selected_runway_card_and_theme_chip_carry_a_background_wash()
        # above for the measurement and the full reasoning. Both halves
        # of the live-state treatment must match the `--selected`
        # fallback exactly, or a browser without :has() renders a
        # different-sized card.
        def _carries_the_constant_border_and_inset_ring(body, label):
            if "border-color: var(--color-accent);" not in body:
                return "%s must recolour its constant 1px border to the accent" % (label,)
            if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in body:
                return "%s must carry T6's inset accent ring" % (label,)
            if "border: 2px" in body:
                return "%s must never declare a 2px border again (T6's layout shift)" % (label,)
            return None

        # Theme chip: strong border, body wash, check glyph shown.
        body, err = _rule_body(".theme-chip:has(input:checked) {")
        if body is None:
            return False, err
        err = _carries_the_constant_border_and_inset_ring(
            body, ".theme-chip:has(input:checked)")
        if err:
            return False, err

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
        # RETARGETED by 22-15-PLAN.md Task 1 (T6): this clause used to
        # require `box-shadow: none;`, whose only job was to suppress
        # the hover elevation shadow. Once selection IS a box-shadow,
        # `none` erases the selection ring the instant a pointer crosses
        # a selected chip. Restating the ring suppresses the elevation
        # just as completely (box-shadow is one property) while keeping
        # the signal — and this clause is narrower, because it now
        # forbids the erasure as well as requiring the suppression.
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".theme-chip:has(input:checked):hover must RESTATE T6's inset ring, which "
                "suppresses the hover elevation without erasing the selection signal")
        if "box-shadow: none;" in window:
            return False, (
                ".theme-chip:has(input:checked):hover must not clear the shadow — that would "
                "erase T6's selection ring on hover")

        # Runway card: strong border + wash on one rule (no body wrapper),
        # check glyph shown.
        body, err = _rule_body(".runway-card:has(input:checked) {")
        if body is None:
            return False, err
        err = _carries_the_constant_border_and_inset_ring(
            body, ".runway-card:has(input:checked)")
        if err:
            return False, err
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
        # Same T6 retarget as the chip's own hover clause above.
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".runway-card:has(input:checked):hover must RESTATE T6's inset ring rather than "
                "clearing the shadow")
        if "box-shadow: none;" in window:
            return False, (
                ".runway-card:has(input:checked):hover must not clear the shadow — that would "
                "erase T6's selection ring on hover")

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

        # --- 23-10-PLAN.md Task 1 (D3/CFG-32): SELECTION ANSWERS -----
        # D3's clause is that selecting a chip or a card answers with a
        # small scale and a wash that fades in, rather than switching
        # state instantly. The entire risk in that sentence is the
        # feature-query block count above: the live treatment lives
        # inside @supports, so the obvious way to animate it is a second
        # @supports block, which is what Phase 15's D-05 did and had
        # retired, and what 23-RESEARCH.md names as the single largest
        # threat to this count in the whole phase.
        #
        # It is not needed, and this is the assertion that keeps the
        # next editor from reaching for it anyway: a `transition` is a
        # property of the ELEMENT, not of the state. Declared on the
        # BASE rule it animates the property however the state that
        # changes it is reached — live `:has(input:checked)` inside the
        # query, and the server-rendered `--selected` fallback outside
        # it, from one declaration. So this check asserts BOTH halves in
        # one place: the transitions exist on the base rules (outside
        # the query), AND the query itself contains no `transition` at
        # all. Both live in this ONE check function on purpose, so that
        # "helpfully" moving a transition inside the block fails exactly
        # once rather than twice.
        def _base_rule_body(selector):
            # Newline-anchored, not a bare substring search:
            # ".theme-chip__body {" also occurs inside
            # ".theme-chip--selected .theme-chip__body {", which sits
            # EARLIER in the file, so str.index() on the bare selector
            # would silently measure the wrong rule.
            anchored = "\n" + selector
            if anchored not in source:
                return None, "expected style.css to declare the base rule %r" % (selector,)
            idx = source.index(anchored)
            if idx > supports_idx:
                return None, (
                    "expected the base rule %r to be declared BEFORE (outside) the one "
                    "@supports selector(:has(*)) block" % (selector,))
            start = idx + len(anchored)
            return source[start:source.index("}", start)], ""

        def _carries_transition(body, label, properties):
            if "transition:" not in body:
                return (
                    "%s must declare the selection transition on its OWN base rule — a "
                    "transition declared on the base rule animates the property however the "
                    "state is reached, which is why the live :has() treatment needs no second "
                    "feature query (D3, 23-10-PLAN.md Task 1)" % (label,))
            decl = body[body.index("transition:"):]
            decl = decl[:decl.index(";") + 1] if ";" in decl else decl
            for prop in properties:
                if prop not in decl:
                    return (
                        "%s's transition must name %r — it is one of the properties that "
                        "actually changes on selection, and a property absent from the list "
                        "switches instantly (got %r)" % (label, prop, decl.strip()))
            if "var(--motion-fast)" not in decl:
                return (
                    "%s's transition must spend var(--motion-fast), the phase's REACTION token "
                    "— a selection is a state change the user just caused and is watching for "
                    "confirmation of (got %r)" % (label, decl.strip()))
            return None

        for selector, properties in (
            (".theme-chip {", ("transform", "border-color", "box-shadow")),
            (".theme-chip__body {", ("background-color",)),
            (".runway-card {",
             ("transform", "border-color", "box-shadow", "background-color")),
        ):
            body, err = _base_rule_body(selector)
            if body is None:
                return False, err
            err = _carries_transition(body, selector.rstrip(" {"), properties)
            if err:
                return False, err

        # The scale itself, and the fallback parity that is the whole
        # reason one transition declaration is enough: the live rule and
        # the --selected fallback must carry the SAME transform, or a
        # browser without :has() gets a differently-sized selected card
        # — the identical contract T6 already holds for the border and
        # the ring.
        def _scale_of(selector, inside):
            if selector not in source:
                return None, "expected style.css to declare %r" % (selector,)
            idx = source.index(selector)
            if inside and idx < supports_idx:
                return None, "expected %r to live inside the feature query" % (selector,)
            if not inside and idx > supports_idx:
                return None, "expected %r to live outside the feature query" % (selector,)
            start = idx + len(selector)
            body = source[start:source.index("}", start)]
            match = re.search(r"transform:\s*scale\(([^)]+)\)", body)
            if not match:
                return None, (
                    "expected %r to carry the selection scale (`transform: scale(...)`) — the "
                    "wash's fade is the primary signal and the scale is its punctuation, and a "
                    "transform changes no layout box so T6 cannot recur through it" % (selector,))
            return match.group(1).strip(), ""

        scales = {}
        for selector, inside in (
            (".theme-chip:has(input:checked) {", True),
            (".theme-chip--selected {", False),
            (".runway-card:has(input:checked) {", True),
            (".runway-card--selected {", False),
        ):
            value, err = _scale_of(selector, inside)
            if value is None:
                return False, err
            scales[selector] = value
        if len(set(scales.values())) != 1:
            return False, (
                "the live :has(input:checked) rules and their --selected fallbacks must carry "
                "the SAME scale, or a browser without :has() renders a different-sized selected "
                "card — the identical parity contract T6 already holds for the border and the "
                "ring, got %r" % (scales,))

        # Saved-but-not-live must CLEAR the scale, exactly as it already
        # clears the accent ring and the wash: a chip can be saved while
        # its neighbour is the live choice, and two scaled chips would
        # claim two selections.
        for selector in (
            ".theme-chip--selected:not(:has(input:checked)) {",
            ".runway-card--selected:not(:has(input:checked)) {",
        ):
            if selector not in source:
                return False, "expected style.css to declare %r" % (selector,)
            start = source.index(selector) + len(selector)
            body = source[start:source.index("}", start)]
            if "transform: none;" not in body:
                return False, (
                    "%s must clear the selection scale with `transform: none;` — it already "
                    "clears the accent ring and the wash for the same reason, and a saved-but-"
                    "not-live chip that stays scaled claims a selection it does not have"
                    % (selector,))

        # And the block itself carries NO transition. Measured on
        # comment-stripped source, because the paragraphs inside that
        # block (and the one this plan adds above it) discuss the very
        # word this scan counts — a raw scan would be tripped by the
        # comment that explains why the rule is not there.
        stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        if stripped.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block in comment-stripped source, got %d"
                % (supports_marker, stripped.count(supports_marker)))
        open_idx = stripped.index(supports_marker) + len(supports_marker) - 1
        depth = 0
        close_idx = None
        for pos in range(open_idx, len(stripped)):
            if stripped[pos] == "{":
                depth += 1
            elif stripped[pos] == "}":
                depth -= 1
                if depth == 0:
                    close_idx = pos
                    break
        if close_idx is None:
            return False, "the @supports selector(:has(*)) block is never closed"
        if "transition" in stripped[open_idx:close_idx]:
            return False, (
                "the ONE @supports selector(:has(*)) block declares a `transition` — it must "
                "not. A transition belongs on each selectable surface's BASE rule, where it "
                "animates the live :has() treatment and the --selected fallback identically "
                "from one declaration; moving it inside the query is the first step toward the "
                "second feature-query block Phase 15's D-05 already had retired (D3, "
                "23-10-PLAN.md Task 1)")

        return True, ""
    check(
        "the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore) is keyed to "
        "live :has(input:checked) state inside one @supports selector(:has(*)) block, for both .theme-chip and "
        ".runway-card, with every pre-existing --selected fallback rule surviving verbatim (quick task 260904-bbi) "
        "— and, since 23-10-PLAN.md Task 1 (D3/CFG-32), selection ANSWERS: a fast transition naming the transform, "
        "the border colour, the shadow and the wash is declared on each selectable surface's BASE rule, the live "
        "rules and their --selected fallbacks carry the SAME scale, saved-but-not-live clears it, and the ONE "
        "feature-query block declares no transition at all — asserted together so moving one inside fails once",
        _strong_selected_treatment_is_keyed_to_the_live_checked_radio)

    # 30-03-PLAN.md Task 1 (CFG-85): the check that used to live here —
    # _destructive_disconnect_is_secondary_and_selection_is_free_and_
    # focusable (22-15-PLAN.md Task 1's T2/T6/T15 structural scan) —
    # carried TWO properties in one function: the destructive Disconnect
    # control's specificity/placement (T2, survives untouched by CFG-85
    # — 30-06's subject, not ledgered here) and the `input:checked +
    # .frame-colours__row` selector (T6, CFG-85 retires .frame-colours__
    # row itself). LEDGERED WHOLE to 30-07 rather than split, with a note
    # that 30-06 owes the T2/T15 half back — see _ASPECT_REPIN_LEDGER.
    #
    # 30-07-PLAN.md Task 3: re-pinned below, landing under a name that
    # diverges from the ledger's own predicted "replacement" — that
    # predicted name is IDENTICAL to this row's own "retired" name
    # (30-03's same-name-repoint convention), which would trip
    # _every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()'s
    # own unconditional "retired name has no def" clause the instant a
    # same-named def landed here — the identical guard-collision
    # 30-05-SUMMARY.md/30-06-SUMMARY.md already documented twice, at
    # different rows. Resolved the same way: append
    # "_after_the_accordion_rebuild" to the landing name. Re-proves BOTH
    # halves: (a) the destructive control's specificity RELATIONSHIP —
    # `button.calendar-disconnect-btn` is element-qualified, (0,1,1), and
    # placed AFTER `button[type="submit"]` in source order, so it wins on
    # source order at equal specificity rather than on a higher one (the
    # T2/T15 half, unaffected by CFG-85, never actually broken); and (b)
    # the selection-is-free-and-focusable half, RE-KEYED from the retired
    # `input:checked + .frame-colours__row` sibling selector to the new
    # mechanism, which is now `.palette-chip:has(input:checked)` inside
    # the file's one `@supports selector(:has(*))` block (the T6 half,
    # the one CFG-85 genuinely retires the OLD selector for).

    def _destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild():
        source = _read_static("style.css")

        # (a) T2/T15: the specificity RELATIONSHIP, not merely presence.
        # `button[type="submit"]` and `button.calendar-disconnect-btn`
        # are both (0,1,1) — equal specificity — so which one wins is
        # decided by SOURCE ORDER alone. The recorded defect (22-UI-
        # SPEC.md, this file's own header comment) was a rule whose every
        # declaration was dead for a phase and a half because the
        # selector was only (0,1,0) against the submit rule's (0,1,1);
        # asserting the element qualifier alone would not catch a
        # regression back to that bug if the ORDER also regressed, so
        # both are asserted together.
        submit_selector = 'button[type="submit"] {'
        disconnect_selector = "button.calendar-disconnect-btn {"
        if submit_selector not in source:
            return False, "expected style.css to declare %r" % (submit_selector,)
        if disconnect_selector not in source:
            return False, (
                "expected style.css to declare %r (element-qualified — a bare "
                "'.calendar-disconnect-btn' is only (0,1,0) and loses to "
                "button[type=\"submit\"]'s (0,1,1) regardless of source order)"
                % (disconnect_selector,))
        submit_idx = source.index(submit_selector)
        disconnect_idx = source.index(disconnect_selector)
        if disconnect_idx < submit_idx:
            return False, (
                "expected %r to appear AFTER %r in source order — at equal "
                "(0,1,1) specificity the LATER rule wins, and this is the exact "
                "relationship that let the destructive control render as the "
                "page's primary accent-filled CTA for a phase and a half"
                % (disconnect_selector, submit_selector))

        # (b) T6, re-keyed: the palette chip's checked-state declarations
        # must live inside the ONE @supports selector(:has(*)) block —
        # the new selection mechanism, replacing the retired
        # `input:checked + .frame-colours__row` sibling selector.
        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block, got %d"
                % (supports_marker, source.count(supports_marker)))
        supports_idx = source.index(supports_marker)

        def _rule_body(selector):
            if selector not in source:
                return None, "expected style.css to declare %r" % (selector,)
            idx = source.index(selector)
            if idx < supports_idx:
                return None, (
                    "expected %r to live inside the @supports selector(:has(*)) "
                    "block" % (selector,))
            return source[idx + len(selector):source.index("}", idx)], ""

        base_body, err = _rule_body(".palette-chip:has(input:checked) {")
        if base_body is None:
            return False, err
        if "border-color: var(--color-accent);" not in base_body:
            return False, ".palette-chip:has(input:checked) must recolour its own border to accent"
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in base_body:
            return False, ".palette-chip:has(input:checked) must carry the inset accent ring"

        name_body, err = _rule_body(".palette-chip:has(input:checked) .palette-chip__name {")
        if name_body is None:
            return False, err
        if "background: color-mix(in srgb, var(--color-accent) 12%, transparent);" not in name_body:
            return False, "expected the 12%% accent wash on .palette-chip__name"

        check_body, err = _rule_body(".palette-chip:has(input:checked) .palette-chip__check {")
        if check_body is None:
            return False, err
        if "display: inline-flex;" not in check_body:
            return False, "expected the check glyph to switch to inline-flex"

        return True, ""
    check(
        "the destructive Disconnect control keeps its secondary, element-qualified specificity "
        "AND its source-order relationship against button[type=\"submit\"] (T2/T15, re-proven as a "
        "RELATIONSHIP rather than a bare presence check, since the recorded defect was a rule whose "
        "every declaration was dead for a phase and a half), and the selected-chip mechanism is "
        "re-keyed from the retired 'input:checked + .frame-colours__row' sibling selector to "
        ".palette-chip:has(input:checked) inside the file's one @supports selector(:has(*)) block, "
        "carrying the accent border, inset ring, 12%% wash and check-glyph declarations (T6, "
        "30-07-PLAN.md Task 3)",
        _destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild)

    def _calendar_fusion_css_retired_from_the_stylesheet():
        # 21-07-PLAN.md Task 3 (D-13/R-08/Pitfall 2): both retired
        # fusion rules must be gone from the real stylesheet, not merely
        # dead-but-present — a plan that deletes the merged card's
        # separate-siblings markup while leaving this CSS behind would
        # ship dead rules that no longer match anything (Pitfall 2).
        source = _read_static("style.css")
        for retired_selector in (
                ".page-section:has(+ .calendar-disconnect-form)",
                ".calendar-disconnect-form {"):
            if retired_selector in source:
                return False, "expected %r to be retired from style.css entirely" % (retired_selector,)
        return True, ""
    check(
        "style.css carries neither retired Calendar-card fusion selector "
        "(.page-section:has(+ .calendar-disconnect-form), .calendar-disconnect-form) anywhere "
        "(D-13/R-08/Pitfall 2)",
        _calendar_fusion_css_retired_from_the_stylesheet)

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

        # 22-10-PLAN.md Task 1 (T10): retargeted in place. The badge's
        # text used to be the hard-coded English literal
        # `content: "Current";`, twice, in an app that ships in two
        # languages. It is now `content: attr(data-current-label)`, with
        # the translated string server-rendered onto the element. The
        # pseudo-element itself is unchanged, so every other assertion in
        # this check still holds verbatim; only the source of the text
        # moved. The English literal must now be ABSENT.
        current_literal = "content: attr(%s)" % config_page.CURRENT_BADGE_ATTR
        if source.count(current_literal) != 2:
            return False, (
                "expected exactly 2 occurrences of %r, got %d" % (current_literal, source.count(current_literal)))
        hard_coded = 'content: "Current"'
        # Comment-filtered deliberately, and this filter is load-bearing
        # rather than convenient: the DECLARATION is gone, but the rule's
        # own comment block still quotes `content: "Current"` while
        # recording the four-point justification for keeping a
        # pseudo-element instead of a <span>. 22-UI-SPEC.md §2's T10 row
        # says that justification is unchanged, so the comment must
        # survive — deleting prose to satisfy a grep is the defect this
        # filter exists to prevent. Same filter shape as this plan's own
        # acceptance criterion (`grep -v '^ *[*/]'`).
        declarations = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith(("*", "/")))
        if hard_coded in declarations:
            return False, (
                "expected zero hard-coded English %r DECLARATIONS - T10 moves the badge's "
                "text to a server-rendered, translated attribute" % (hard_coded,))

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
        "wash/check glyph cleared and a \"Current\" ::after tag whose text is read from the server-rendered, "
        "translated data-current-label attribute (exactly 2 occurrences site-wide, zero hard-coded English "
        "declarations, zero French copy in the stylesheet), reusing the established muted-text strength rather "
        "than inventing a new one (quick task 260904-bbi; retargeted by 22-10-PLAN.md Task 1, T10)",
        _saved_but_unchecked_card_degrades_to_a_quiet_current_marker)

    def _style_css_carries_section_caption_and_the_restored_dirty_bar_rules():
        # 27-04-PLAN.md (D-04/CFG-63): SUPERSEDED this check's own
        # pre-27-04 subject — quick task 260901-re6/260901-s5o's floating-
        # card restyle and its >=960px fixed positioning were both deleted
        # wholesale along with `.dirty-bar` itself. (a) below is the one
        # assertion that survived unchanged then and survives unchanged
        # now: `.section-caption` is unrelated to the bar and this is its
        # only test site.
        #
        # 28-08-PLAN.md Task 2 (CFG-77/CFG-78), 2026-09-16: RENAMED and
        # retargeted in the OPPOSITE direction from 27-04's own retarget
        # — the developer asked for the bar back, so "zero occurrences of
        # .dirty-bar" is now the wrong assertion; this check instead
        # proves `.dirty-bar` genuinely exists, is fixed-positioned at
        # BOTH breakpoints (never left `position: static` at one of
        # them), and carries its `[hidden]` override and its Cancel
        # button's own quiet-wash override.
        source = _read_static("style.css")

        caption_selector = ".section-caption {"
        if caption_selector not in source:
            return False, "expected style.css to declare a .section-caption rule"
        idx = source.index(caption_selector)
        window = source[idx:idx + 200]
        if "color-mix(in srgb, var(--color-text) 70%, transparent)" not in window:
            return False, "expected .section-caption's rule body to carry the 70% color-mix muted idiom"

        # Three `.dirty-bar {` rule bodies: the base rule (flex row,
        # entrance animation — no position declared) plus one per
        # breakpoint (each setting position: fixed with its own
        # geometry). Assert the COUNT that actually carries
        # position: fixed is exactly two — never zero (a breakpoint left
        # `position: static`) and never three (the base rule itself
        # should not be the one setting it).
        dirty_bar_blocks = re.findall(r"\.dirty-bar \{[^}]*\}", source)
        if len(dirty_bar_blocks) != 3:
            return False, (
                "expected exactly three `.dirty-bar { ... }` rule bodies (the base rule plus one "
                "per breakpoint), got %d" % len(dirty_bar_blocks))
        fixed_count = sum(1 for block in dirty_bar_blocks if "position: fixed" in block)
        if fixed_count != 2:
            return False, (
                "expected exactly two of the three `.dirty-bar { ... }` rule bodies to set "
                "position: fixed (one per breakpoint), got %d" % fixed_count)
        if ".dirty-bar[hidden]" not in source:
            return False, "expected the `.dirty-bar[hidden] { display: none; }` override to survive"
        if ".dirty-bar__cancel {" not in source:
            return False, "expected `.dirty-bar__cancel`'s own quiet-wash override to survive"
        return True, ""
    check(
        "style.css declares .section-caption (70% muted color-mix) AND the restored .dirty-bar — "
        "fixed-positioned at both breakpoints, its [hidden] override and its Cancel button's own "
        "quiet-wash override all present (CFG-77/CFG-78, 28-08-PLAN.md Task 2)",
        _style_css_carries_section_caption_and_the_restored_dirty_bar_rules)

    def _skypane_bar_arrive_keyframes_is_referenced_again_by_the_restored_bar():
        # 27-04-PLAN.md (D-04/CFG-63): the save bar's own entrance
        # (23-09-PLAN.md Task 1, D3/CFG-32) animated from this block, and
        # every rule that referenced it was retired along with the bar.
        # The @keyframes DEFINITION was kept rather than deleted —
        # deliberately ORPHANED, no rule anywhere referencing it — so
        # this file's own pinned @keyframes count of 4 would not need to
        # move for a component that might return.
        #
        # 28-08-PLAN.md Task 2 (CFG-77/CFG-78), 2026-09-16: it has
        # returned. RENAMED and retargeted to assert the OPPOSITE of
        # what it asserted before: the block is REFERENCED again, by the
        # restored `.dirty-bar` base rule's own `animation:` declaration
        # — REUSED, not reinvented (the plan's own explicit instruction:
        # "reuse the stylesheet's existing motion vocabulary" rather than
        # reintroduce a deleted block). The file's pinned @keyframes
        # count stays at 4 either way, since this is the SAME block
        # gaining a consumer, never a new one — re-verified by a
        # separate check below, by RUNNING.
        source = _read_static("style.css")
        keyframes_marker = "@keyframes skypane-bar-arrive {"
        if source.count(keyframes_marker) != 1:
            return False, (
                "expected exactly one %s block (still the same one, never duplicated), got %d"
                % (keyframes_marker, source.count(keyframes_marker)))
        if "animation: skypane-bar-arrive" not in source:
            return False, (
                "expected the restored .dirty-bar base rule to declare "
                "animation: skypane-bar-arrive var(--motion-fast) ease-out — REUSING the block "
                "27-04 deliberately kept orphaned for exactly this restoration, rather than "
                "leaving the bar with no entrance or reinventing a second block")
        if source.count("animation: skypane-bar-arrive") != 1:
            return False, (
                "expected exactly ONE rule to reference animation: skypane-bar-arrive, got %d — "
                "a second consumer would be a genuinely new use this plan did not intend"
                % source.count("animation: skypane-bar-arrive"))
        return True, ""
    check(
        "the @keyframes skypane-bar-arrive block — kept deliberately orphaned by 27-04 specifically "
        "so a future restoration would not need to move the file's pinned @keyframes count — is "
        "REFERENCED again by the restored .dirty-bar base rule's own animation: declaration, reused "
        "rather than reinvented (CFG-77/CFG-78, 28-08-PLAN.md Task 2)",
        _skypane_bar_arrive_keyframes_is_referenced_again_by_the_restored_bar)

    def _dirty_state_js_has_no_hardcoded_section_names():
        source = _read_static("dirty-state.js")
        for literal in ("Theme", "Runway", "Diagnostic LED"):
            if literal in source:
                return False, "expected no hardcoded occurrence of %r - section labels must come from the DOM" % (literal,)
        return True, ""
    check(
        "dirty-state.js contains no hardcoded occurrence of \"Theme\", \"Runway\", or \"Diagnostic LED\" (labels come from the DOM)",
        _dirty_state_js_has_no_hardcoded_section_names)

    def _dirty_state_js_is_network_free_again_with_one_named_timer_exception():
        # 27-04-PLAN.md Task 2 (CFG-63): SUPERSEDED this check's own
        # pre-27-04 ban — dirty-state.js became the settings form's
        # auto-save driver and fetch( was exactly how it saved, the
        # identical model quick-switch.js already ships.
        #
        # 28-08-PLAN.md Task 3 (CFG-77/CFG-78), 2026-09-16: RENAMED and
        # INVERTED — the developer asked for the bar back
        # (ROADMAP.md's Phase 28 addendum), so this file is back to
        # being network-free and poll-free. Forbidden OUTRIGHT: fetch(,
        # XMLHttpRequest, setInterval, requestAnimationFrame.
        #
        # setTimeout is permitted EXACTLY ONCE, and pinned STRUCTURALLY,
        # not by count alone: the single occurrence must be a
        # setTimeout(fn, 0) — a literal zero delay, never a duration —
        # scheduled from INSIDE the form's own reset-event handler
        # (form.addEventListener("reset", function () { ... })) and
        # nowhere else in the file. This is a reset-event side-effect
        # flush, not a poll and not a debounce: the reset event fires
        # BEFORE the browser restores the form's fields (the restore is
        # that event's own cancelable default action), so the theme-
        # preview refresh and the dial repaint must run on the next tick
        # to read restored values — a synchronous call would read stale
        # ones. This file's pre-27-04 shape also permitted exactly one
        # setTimeout, then scoped to the toast's own dismissal — the
        # toast's removal retires that one and this replaces it, so
        # "exactly one, narrowly scoped" is this file's own existing
        # convention, not a new liberty.
        source = _read_static("dirty-state.js")
        for forbidden in ("fetch(", "XMLHttpRequest", "setInterval", "requestAnimationFrame"):
            if forbidden in source:
                return False, "forbidden network/timer construct found in dirty-state.js: %r" % (forbidden,)
        if source.count("setTimeout") != 1:
            return False, (
                "expected exactly one setTimeout occurrence anywhere in the file (the reset-event "
                "side-effect flush), got %d" % source.count("setTimeout"))
        # Locate the reset-event handler's own function body by reading,
        # from its opening brace to its matching close — never by a
        # file-wide grep, which would not prove CONTAINMENT.
        handler_marker = 'form.addEventListener("reset", function () {'
        if handler_marker not in source:
            return False, "expected a form.addEventListener(\"reset\", function () { ... }) handler"
        body_start = source.index(handler_marker) + len(handler_marker)
        depth = 1
        i = body_start
        while depth > 0:
            if i >= len(source):
                return False, "reset handler's opening brace was never matched by a closing one"
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
            i += 1
        handler_body = source[body_start:i - 1]
        if "setTimeout" not in handler_body:
            return False, (
                "expected the file's one setTimeout occurrence to sit INSIDE the reset handler's "
                "own function body, but it was found outside it")
        timeout_idx = handler_body.index("setTimeout")
        timeout_call = handler_body[timeout_idx:timeout_idx + 400]
        if not re.search(r"setTimeout\(function \(\) \{.*?\}, 0\);", timeout_call, re.DOTALL):
            return False, (
                "expected the reset handler's own setTimeout call to read "
                "setTimeout(function () { ... }, 0) — a literal zero delay, never a duration; "
                "got %r" % (timeout_call[:120],))
        if "preventDefault" in handler_body or "returnValue" in handler_body:
            return False, (
                "expected the reset handler's own function body to contain neither "
                "preventDefault nor returnValue — cancelling the reset event's own default "
                "action would silently turn Annuler into a no-op for every JS-running visitor")
        # The header carries BOTH halves of the constraint — the ban and
        # the named exception — never a blanket claim the code
        # contradicts.
        if "never introduce a network call" not in source:
            return False, "expected the header to restore its 'never introduce a network call' constraint"
        if "ONE NAMED EXCEPTION" not in source:
            return False, "expected the header to name the ONE timer exception explicitly, in the same breath as the constraint"
        return True, ""
    check(
        "dirty-state.js is network-free and poll-free again (no fetch(/XMLHttpRequest/setInterval/"
        "requestAnimationFrame anywhere) with exactly ONE setTimeout in the whole file — a literal "
        "setTimeout(fn, 0) sitting INSIDE the form's own reset-event handler, never cancelling that "
        "event's own default action — and the file's header states both the standing constraint AND "
        "this one named exception in the same breath (CFG-77/CFG-78, 28-08-PLAN.md Task 3)",
        _dirty_state_js_is_network_free_again_with_one_named_timer_exception)

    # ==================================================================
    # 15-05-PLAN.md Task 3 (D-10, D-11, 15-VALIDATION.md row 10): the
    # per-flight colour-rules editor's markup/copy checks.
    # ==================================================================

    # 21-05-PLAN.md Task 1 (D-06/D-10): the rules editor is no longer a
    # standalone sibling section — it relocated into the Frame colours
    # card's own "Per-flight rules" usage panel, which only the
    # SCOPE_DISPLAY render carries (Frame colours is never rendered on
    # SCOPE_ALL/SCOPE_DEVICE any more). Every check below is retargeted
    # to render at SCOPE_DISPLAY and to bound the rules panel's own
    # segment via its data-usage-panel-target attribute through to the
    # next section (the Calendar card, which always follows it), rather
    # than the retired RULES_SECTION_HEADING/POLL_SECTION_HEADING pair
    # (Display never renders Poll at all).
    def _rules_row_segment(rendered):
        """30-05-PLAN.md Task 2 (CFG-85): renamed from
        `_rules_panel_segment()` — the retired
        `COLOUR_USAGE_PANEL_TARGET_ATTR` locator is replaced by the
        rules row's own `data-usage` attribute, the same attribute
        `theme-preview.js`'s `openRow()`/`departuresRow()` already key
        off (30-04-PLAN.md Task 3). Every surviving caller below is
        otherwise unchanged — this is a locator repoint, not a
        rewrite: the property each caller protects still holds against
        the real accordion markup, only the way this helper FINDS the
        rules row's own segment changes.

        30-06-PLAN.md Task 3: delegates its own end-boundary to
        `_aspect_usage_row_bounds()` rather than duplicating that
        helper's own (now repointed) last-row fallback a second time —
        see that function's own docstring for why the former Calendar-
        card-nested-wrapper literal no longer matches anything.
        """
        start, end = _aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
        return rendered[start:end]

    def _aspect_card_full_shape_checklist():
        # 30-05-PLAN.md Task 1 (CFG-85): the relationship check
        # replacing the retired _frame_colours_card_full_shape_
        # checklist — every bullet below asserts a RELATIONSHIP (order,
        # uniqueness, adjacency) derived from the registry/COLOUR_USAGES
        # at check time, never a restated literal.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)

        # Exactly one Aspect card, positioned after the Look section intro.
        look_pos = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        if rendered.count('class="page-section aspect-card') != 1:
            return False, (
                "expected exactly one .aspect-card, got %d"
                % rendered.count('class="page-section aspect-card'))
        aspect_pos = rendered.index('class="page-section aspect-card')
        if not (look_pos < aspect_pos):
            return False, "expected the Aspect card after the Look section intro"

        # Exactly len(COLOUR_USAGES) accordion rows, data-usage values in
        # document order equal to COLOUR_USAGES itself — the locked-order
        # property the retired colour_usage radiogroup check used to hold.
        row_pattern = re.compile(
            r'<details class="([^"]*)" name="%s" data-usage="([^"]*)"( open)?>'
            % re.escape(config_page.ASPECT_ROWS_GROUP_NAME))
        rows = row_pattern.findall(rendered)
        usages_in_order = [usage for _cls, usage, _open in rows]
        if usages_in_order != list(config_page.COLOUR_USAGES):
            return False, (
                "expected the accordion rows' data-usage values, in document order, to equal "
                "COLOUR_USAGES exactly, got %r" % (usages_in_order,))

        # Exactly one row carries `open`, and it is departures.
        open_usages = [usage for _cls, usage, is_open in rows if is_open]
        if open_usages != [config_page.COLOUR_USAGE_DEPARTURES]:
            return False, (
                "expected only the departures row open by default, got %r" % (open_usages,))

        # The last row, and only it, carries usage-row--secondary.
        secondary_usages = [
            usage for cls, usage, _open in rows if "usage-row--secondary" in cls.split()]
        if secondary_usages != [config_page.COLOUR_USAGES[-1]]:
            return False, (
                "expected only the last row (%r) to carry usage-row--secondary, got %r"
                % (config_page.COLOUR_USAGES[-1], secondary_usages))

        # Each of the three theme rows holds exactly one .palette grid;
        # the rules row holds none.
        for usage in config_page.COLOUR_USAGES:
            start, end = _aspect_usage_row_bounds(rendered, usage)
            palette_count = rendered[start:end].count('class="palette" role="radiogroup"')
            expected = 0 if usage == config_page.COLOUR_USAGE_RULES else 1
            if palette_count != expected:
                return False, (
                    "expected %d .palette grid(s) inside the %r row, got %d"
                    % (expected, usage, palette_count))

        # Zero occurrences of every retired mechanism's own markup, page-wide.
        for token in _ASPECT_RETIRED_MARKUP_TOKENS:
            count = rendered.count(token)
            if count != 0:
                return False, (
                    "expected zero occurrences of the retired token %r, got %d" % (token, count))

        # The <h2> immediately inside the card is ASPECT_HEADING at
        # ASPECT_HEADING_ID, and the element right after it is NOT a
        # section-caption paragraph — the no-caption half of CFG-85.
        heading_needle = '<h2 class="text-heading" id="%s">%s</h2>' % (
            config_page.ASPECT_HEADING_ID, escape_html(i18n.t(config_page.ASPECT_HEADING)))
        if heading_needle not in rendered:
            return False, "expected the Aspect <h2> at ASPECT_HEADING_ID"
        after_heading = rendered[rendered.index(heading_needle) + len(heading_needle):]
        if after_heading.startswith('<p class="text-label section-caption"'):
            return False, (
                "expected no section-caption paragraph immediately after the Aspect heading — "
                "CFG-85 retires the caption")
        return True, ""
    check(
        "the Aspect card's full shape, as a relationship rather than a list of endpoints: one card "
        "after the Look section intro, its four accordion rows' data-usage values in COLOUR_USAGES' "
        "own locked order, exactly one row open (departures), only the last row secondary, exactly "
        "one .palette grid per theme row and none in the rules row, zero occurrences of any retired "
        "mechanism's markup, and no section-caption paragraph immediately after the heading (CFG-85, "
        "30-05-PLAN.md Task 1, replacing the retired _frame_colours_card_full_shape_checklist)",
        _aspect_card_full_shape_checklist)

    def _rules_row_renders_inside_aspect_after_form():
        # 30-05-PLAN.md Task 2 (CFG-85): replaces the retired
        # _rules_section_renders_inside_frame_colours_after_form. The
        # rules row holds real <form> elements (the add form), and HTML
        # forbids a nested <form>, so the whole Aspect card must be a
        # sibling of #settings-form while every theme radio still
        # reaches it through form="settings-form" — all three facts
        # asserted together, for the same original reason.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        # The settings form's OWN closing tag — never the bare first
        # `</form>` in the whole document, which would instead match
        # the Frame strip's own quick-switch <form>...</form> (it
        # renders BEFORE <form id="settings-form"> opens) and pass
        # vacuously regardless of where the real form actually closes.
        form_start = rendered.index('<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
        form_end = rendered.index("</form>", form_start)
        aspect_pos = rendered.index('class="page-section aspect-card')
        rules_start, rules_end = _aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
        if not (form_end < aspect_pos < rules_start):
            return False, (
                "expected </form> < the Aspect card < the rules row, got positions %d/%d/%d"
                % (form_end, aspect_pos, rules_start))
        for field in ("theme", "theme_arriving", "calendar_theme_id"):
            total = rendered.count('name="%s" value="' % field)
            with_form = len(re.findall(
                r'name="%s" value="[^"]*" class="visually-hidden"( form="%s")'
                % (re.escape(field), re.escape(config_page.SETTINGS_FORM_ID)), rendered))
            if with_form != total:
                return False, (
                    "expected every %s radio to carry form=%r, got %d/%d"
                    % (field, config_page.SETTINGS_FORM_ID, with_form, total))
        return True, ""
    check(
        "render() places the Aspect card, holding the rules row, after the settings </form> and "
        "before the Calendar card, with every theme/theme_arriving/calendar_theme_id radio still "
        "carrying form=settings-form (Phase 15 D-10, replacing the retired "
        "_rules_section_renders_inside_frame_colours_after_form)",
        _rules_row_renders_inside_aspect_after_form)

    def _rules_section_empty_state_then_list_once_a_rule_exists():
        empty_ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(empty_ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        if config_page.RULES_EMPTY_HEADING not in rules_segment:
            return False, "expected the empty-state heading with no rules"
        # 20-09-PLAN.md Task 3 (D-15c/d): the retired table/card split is
        # gone outright — a plain .rule-list, never a table.
        if "rule-list" in rules_segment or "<table" in rules_segment:
            return False, "expected no list markup in the empty-state branch"

        tmp = tempfile.mkdtemp(prefix="skypane-rules-markup-")
        try:
            result = colour_rules.add_rule(
                tmp, "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
            if result != colour_rules.ADD_OK_NEW:
                return False, "test setup failure: add_rule() returned %r" % (result,)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        filled_ctx = dict(empty_ctx)
        filled_ctx["colour_rules"] = registry
        filled_ctx["now"] = "2026-01-02T00:00:00+00:00"
        rendered = config_page.render(filled_ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        if config_page.RULES_EMPTY_HEADING in rules_segment:
            return False, "expected the empty state to be replaced once a rule exists"
        if '<ul class="rule-list">' not in rules_segment:
            return False, "expected the .rule-list once a rule exists"
        if "AFR1234" not in rules_segment:
            return False, "expected the seeded rule's key to appear in the rendered list"
        return True, ""
    check(
        "the rules section renders the empty state with no rules, and the empty state is replaced by "
        "the .rule-list once a rule exists (D-15c/d, retargeted from the retired cards-then-table shape)",
        _rules_section_empty_state_then_list_once_a_rule_exists)

    def _rules_list_orders_most_specific_first_then_alphabetically():
        # D-15c: rows ordered callsign, then hex, then prefix - and
        # alphabetically within each kind. colour_rules.rule_rows() itself
        # already guarantees this order (RULE_KINDS order, then sorted
        # value) - this check pins _rule_list_html()'s own consumption of
        # that order at the rendered-markup level, not just at the data
        # layer.
        tmp = tempfile.mkdtemp(prefix="skypane-rules-order-")
        try:
            for kind, value, theme_id in (
                ("prefix", "AFR", "red"),
                ("callsign", "BAW1234", "blue"),
                ("hex", "3944F2", "white"),
                ("callsign", "AFR1234", "black"),
            ):
                result = colour_rules.add_rule(
                    tmp, kind, value, theme_id, now="2026-01-01T00:00:00+00:00")
                if result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule(%r) returned %r" % (kind, result)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": registry,
            "poll_cooldown_remaining": 0,
            "now": "2026-01-02T00:00:00+00:00",
        }, scope=config_page.SCOPE_DISPLAY)
        list_match = re.search(r'<ul class="rule-list">(.*?)</ul>', rendered, re.S)
        if not list_match:
            return False, "expected a .rule-list"
        list_segment = list_match.group(1)
        expected_order = ["AFR1234", "BAW1234", "3944F2", "AFR"]
        positions = [
            list_segment.index('<span class="rule-row__key mono">%s</span>' % value)
            for value in expected_order
        ]
        if positions != sorted(positions):
            return False, (
                "expected callsign(alpha)/hex/prefix order %r, got positions %r"
                % (expected_order, positions))
        return True, ""
    check(
        "a seeded set of rules of every kind renders most-specific first (callsign, then hex, then "
        "prefix), alphabetically within each kind (D-15c)",
        _rules_list_orders_most_specific_first_then_alphabetically)

    def _aspect_rules_copy_appears_escaped_verbatim():
        # 30-05-PLAN.md Task 3 (CFG-85): replaces the retired
        # _rules_copy_appears_escaped_verbatim. DIVERGENCE FROM THE
        # LEDGER'S OWN "why": 30-03's ledger row states this check
        # "reads config_page.FRAME_COLOURS_ROW_LABELS, the constant
        # CFG-85's rebuild renames" — but 30-04-PLAN.md Task 1 kept
        # FRAME_COLOURS_ROW_LABELS' own name deliberately (30-UI-SPEC.md's
        # Copywriting Contract cites it by this exact name), so that
        # premise turns out to be stale. The property itself is
        # unaffected either way; this check's own body is otherwise
        # byte-identical to the retired one, renamed to match this
        # phase's own Aspect naming convention.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        copy_strings = (
            config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],
            config_page.RULES_SECTION_CAPTION,
            config_page.RULE_KIND_FIELD_LABEL,
            config_page.RULE_VALUE_FIELD_LABEL,
            config_page.RULE_ADD_BUTTON_TEXT,
            config_page.RULES_EMPTY_HEADING,
            config_page.RULES_EMPTY_BODY,
            config_page.RULES_HOW_RULES_COMBINE_SUMMARY,
            config_page.RULES_HOW_RULES_COMBINE_BODY,
        )
        for text in copy_strings:
            if escape_html(text) not in rendered:
                return False, "expected %r to appear escaped-verbatim in the rendered page" % (text,)
        for kind, label in config_page.RULE_KIND_LABELS.items():
            if escape_html(label) not in rendered:
                return False, "expected the kind label %r (for %r) to appear escaped-verbatim" % (label, kind)
        for kind, title in config_page.RULE_KIND_TITLES.items():
            if escape_html(title) not in rendered:
                return False, "expected the kind title %r (for %r) to appear escaped-verbatim" % (title, kind)
        return True, ""
    check(
        "every rules-editor copy string — heading, caption, field labels, kind labels/titles, "
        "empty-state heading/body, and the How-rules-combine disclosure — appears escaped-verbatim, "
        "matching 20-UI-SPEC.md's Copywriting Contract byte for byte (30-05-PLAN.md Task 3, "
        "replacing the retired _rules_copy_appears_escaped_verbatim)",
        _aspect_rules_copy_appears_escaped_verbatim)

    def _aspect_rules_row_label_locked_verbatim():
        # 30-05-PLAN.md Task 2 (CFG-85): replaces the retired
        # _frame_colours_rules_row_label_locked_verbatim. Keeps the
        # original lock — FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_RULES]
        # is still exactly "Per-flight rules" — and adds a second lock
        # 30-UI-SPEC.md's own copy table corrects: the rules row's
        # empty-state meta must read FRAME_COLOURS_RULES_EMPTY_META's
        # real value ("No rules yet"), never ROADMAP's own plausible-
        # sounding paraphrase "Aucune règle · Ajouter" — precisely the
        # kind of copy a later editorial pass would "restore" without
        # this check catching it.
        if config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES] != "Per-flight rules":
            return False, (
                "expected the rules row label to equal the locked \"Per-flight rules\" text exactly, "
                "got %r" % (config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],))
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_start, rules_end = _aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
        summary_segment = rendered[rules_start:rules_end].split("</summary>", 1)[0]
        empty_meta_needle = escape_html(config_page.FRAME_COLOURS_RULES_EMPTY_META)
        if empty_meta_needle not in summary_segment:
            return False, (
                "expected the rules row's empty-state meta to read FRAME_COLOURS_RULES_EMPTY_META "
                "(%r) verbatim, not a paraphrase" % (config_page.FRAME_COLOURS_RULES_EMPTY_META,))
        if "Aucune règle" in summary_segment:
            return False, (
                "expected the rules row's meta to NEVER read ROADMAP's own paraphrase "
                "'Aucune règle · Ajouter'")
        return True, ""
    check(
        "the rules row label equals 21-UI-SPEC.md's locked \"Per-flight rules\" text exactly, and its "
        "empty-state meta reads FRAME_COLOURS_RULES_EMPTY_META's real value, never ROADMAP's own "
        "paraphrase (D-06/D-07, 30-05-PLAN.md Task 2, replacing the retired "
        "_frame_colours_rules_row_label_locked_verbatim)",
        _aspect_rules_row_label_locked_verbatim)

    def _rules_no_select_and_three_named_radios_one_checked():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        if "<select" in rules_segment:
            return False, "expected no <select> anywhere in the Flight-colours section (D-15b)"
        radio_count = rules_segment.count('name="rule_kind"')
        if radio_count != len(colour_rules.RULE_KINDS):
            return False, "expected %d rule_kind radios, got %d" % (len(colour_rules.RULE_KINDS), radio_count)
        for kind in colour_rules.RULE_KINDS:
            if 'id="rule-kind-%s"' % kind not in rules_segment:
                return False, "expected a rule_kind radio with id rule-kind-%s" % kind
            if 'title="%s"' % escape_html(config_page.RULE_KIND_TITLES[kind]) not in rules_segment:
                return False, "expected the %s radio's label to carry the technical title" % kind
        # Scoped to just the three rule_kind <input> tags themselves — the
        # compact theme-chip grid immediately below also uses " checked"
        # for its own selected chip, which a whole-segment count would
        # wrongly fold in.
        kind_inputs = re.findall(r'<input type="radio" name="rule_kind"[^>]*>', rules_segment)
        if len(kind_inputs) != len(colour_rules.RULE_KINDS):
            return False, "expected %d rule_kind <input> tags, got %d" % (
                len(colour_rules.RULE_KINDS), len(kind_inputs))
        checked_inputs = [tag for tag in kind_inputs if " checked" in tag]
        if len(checked_inputs) != 1:
            return False, "expected exactly one checked rule_kind radio by default, got %d" % len(checked_inputs)
        if 'value="%s"' % colour_rules.RULE_KIND_CALLSIGN not in checked_inputs[0]:
            return False, "expected the callsign/Flight radio to be the one checked by default"
        return True, ""
    check(
        "the Flight-colours section carries no <select>, and its add form's three rule_kind radios "
        "carry the three kind ids and the three technical titles, exactly one checked by default "
        "(D-15b)",
        _rules_no_select_and_three_named_radios_one_checked)

    def _rules_row_carries_pill_badge_and_confirmed_remove_form():
        tmp = tempfile.mkdtemp(prefix="skypane-rules-row-")
        try:
            result = colour_rules.add_rule(
                tmp, "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
            if result != colour_rules.ADD_OK_NEW:
                return False, "test setup failure: add_rule() returned %r" % (result,)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": registry,
            "poll_cooldown_remaining": 0,
            "now": "2026-01-02T00:00:00+00:00",
        }, scope=config_page.SCOPE_DISPLAY)
        row_match = re.search(r'<li class="rule-row">(.*?)</li>', rendered, re.S)
        if not row_match:
            return False, "expected a .rule-row list item"
        row = row_match.group(1)
        if 'class="rule-row__kind banner__pill"' not in row:
            return False, "expected the kind badge to compose .banner__pill"
        if escape_html(config_page.RULE_KIND_LABELS["callsign"]) not in row:
            return False, "expected the plain-language kind word in the badge"
        if "data-confirm=" not in row:
            return False, "expected the Remove form to carry data-confirm (D-15c, locked)"
        if escape_html(config_page.RULE_REMOVE_BUTTON_TEXT) not in row:
            return False, "expected the Remove button's own text, not the airlines gallery's Delete"
        expected_hex = config_page._palette_hex(device_config.THEMES["white"]["departing_index"])
        if 'class="theme-chip__dot" style="background:%s"' % escape_html(expected_hex) not in row:
            return False, "expected the row's swatch dot to carry the real _palette_hex() value"
        return True, ""
    check(
        "a rendered rule row carries a .banner__pill kind badge with the plain-language word, a "
        "computed _palette_hex() swatch dot, and a data-confirm Remove form (D-15c)",
        _rules_row_carries_pill_badge_and_confirmed_remove_form)

    def _rules_empty_state_carries_no_heading_element():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        empty_match = re.search(r'<div class="empty-state-plain">(.*?)</div>', rules_segment, re.S)
        if not empty_match:
            return False, "expected the .empty-state-plain wrapper"
        if "<h" in empty_match.group(1):
            return False, "expected the empty state to carry no heading element, muted sans only (D-15d)"
        if escape_html(config_page.RULES_EMPTY_HEADING) not in empty_match.group(1):
            return False, "expected the empty-state heading sentence"
        return True, ""
    check(
        "the empty state is muted sans copy in .empty-state-plain and carries no <h*> heading element, "
        "never the serif empty_state() heading (D-15d)",
        _rules_empty_state_carries_no_heading_element)

    def _rules_suggestion_chips_present_with_data_and_absent_with_no_events():
        tmpdir = tempfile.mkdtemp(prefix="skypane-rules-suggestions-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            rendered = config_page.render({
                "device_config": {"theme": "white", "tracked_runway": "3"},
                "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
                "poll_cooldown_remaining": 0,
                "state_dir": tmpdir,
            }, scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        rules_segment = _rules_row_segment(rendered)
        if 'class="rule-suggestion-chip" data-kind="callsign" data-value="AFR1380"' not in rules_segment:
            return False, "expected a suggestion chip for the seeded callsign"

        empty_rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
            "state_dir": None,
        }, scope=config_page.SCOPE_DISPLAY)
        empty_segment = _rules_row_segment(empty_rendered)
        if "rule-suggestion-chip" in empty_segment:
            return False, "expected no suggestion chips when there are no recent events"
        return True, ""
    check(
        "up to five suggestion chips render with data-kind/data-value from recent runway events, and "
        "none render when there are no events (D-15e)",
        _rules_suggestion_chips_present_with_data_and_absent_with_no_events)

    def _plain_render_carries_both_disclosures_in_full_never_collapsed():
        """D-17 (21-01-PLAN.md Task 2): the display mode that used to
        collapse both disclosures to one plain sentence is deleted —
        replaces a deleted check that tested that now-removed
        mechanism.
        """
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        if escape_html(config_page.RULES_HOW_RULES_COMBINE_SUMMARY) not in rules_segment:
            return False, "expected the full 'How rules combine' <details> disclosure"
        if "<details>" not in rules_segment:
            return False, "expected a <details> disclosure for rules"
        # 30-06-PLAN.md Task 3: the Calendar heading id constant is
        # retired (the connection block has no <h2> of its own any
        # more) — locate the Calendar row itself via
        # _aspect_usage_row_bounds() instead.
        calendar_start, calendar_end = _aspect_usage_row_bounds(
            rendered, config_page.COLOUR_USAGE_CALENDAR)
        calendar_segment = rendered[calendar_start:calendar_end]
        if escape_html(config_page.CALENDAR_HOW_IT_WORKS_SUMMARY) not in calendar_segment:
            return False, "expected the full Calendar 'How it works' <details> disclosure"
        # D-17: neither collapsed one-sentence variant may appear anywhere in
        # the rendered body — their exact punctuation ("wins." / "screen.")
        # never occurs as a substring of the full <details> body text above
        # ("wins — a flight..." / "colour a flight that happens..."), so this
        # is an unambiguous check, not a coincidental prefix match.
        if "It only colours a flight already on screen." in rendered:
            return False, "expected no collapsed one-sentence Calendar disclosure anywhere"
        if "The most specific match wins." in rendered:
            return False, "expected no collapsed one-sentence rules disclosure anywhere"
        return True, ""
    check(
        "a plain Display render always carries the full 'How rules combine' and Calendar "
        "'How it works' <details> disclosures, never a collapsed one-sentence variant (D-17)",
        _plain_render_carries_both_disclosures_in_full_never_collapsed)

    def _rules_section_carries_no_dirty_section_attr():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_row_segment(rendered)
        if config_page.DIRTY_SECTION_ATTR in rules_segment:
            return False, "expected the rules panel to carry no data-dirty-section attribute"
        return True, ""
    check(
        "the rules panel, inside the Frame colours card, carries no data-dirty-section attribute of "
        "its own — the card's OWN outer wrapper carries the one attribute for all four usages, "
        "exactly like the Poll section carries none",
        _rules_section_carries_no_dirty_section_attr)

    def _rules_french_render_shows_french_row_label_and_button():
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # "Couleurs de vol" heading (RULES_SECTION_HEADING) to the
        # rules row's own French label, "Règles par vol" — the
        # replacement naming text now rendered both by the assignment
        # row and by the panel's own <legend>.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if "Règles par vol" not in rendered:
            return False, "expected the French rules row label 'Règles par vol'"
        if "Ajouter la règle" not in rendered:
            return False, "expected the French Add-rule button 'Ajouter la règle'"
        return True, ""
    check(
        "a French Display render of the Frame colours card's rules row/panel shows 'Règles par vol' "
        "and 'Ajouter la règle' (D-05, retargeted from the retired Flight-colours heading)",
        _rules_french_render_shows_french_row_label_and_button)

    # ==================================================================
    # Section 1b (16-05-PLAN.md Task 3): the Calendar settings group -
    # render() copy/status/theme-select checks, plus handle_post()'s
    # calendar_theme_id membership gate. 16-VALIDATION.md's registry row
    # (D-01) and T-16-SECRET row are both covered here.
    # ==================================================================

    _CALENDAR_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "now": "2026-09-07T09:12:04+00:00",
    }

    def _calendar_status_parts(rendered):
        # 20-09-PLAN.md Task 1 (D-14b): the status sentence is now
        # layout.status_row()'s verdict/detail pair, not a single
        # <p class="calendar-status"> (retired).
        match = re.search(
            r'<span class="status-row__verdict">(.*?)</span>'
            r'<span class="status-row__detail">(.*?)</span>',
            rendered, re.S)
        if not match:
            raise AssertionError("expected a .status-row element")
        return match.group(1), match.group(2)

    _CALENDAR_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_CONNECTED_VERDICT, quote=True)
    _CALENDAR_NOT_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT, quote=True)

    def _calendar_status_not_configured_is_exclusive():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_NOT_CONNECTED_ESCAPED:
            return False, "expected the 'Not connected' verdict, got %r" % (verdict,)
        if detail:
            return False, "expected an empty detail when not configured, got %r" % (detail,)
        return True, ""
    check(
        "with no calendar configured, render() emits the 'Not connected' verdict with an empty detail "
        "(D-14b)",
        _calendar_status_not_configured_is_exclusive)

    def _calendar_status_configured_pending_is_exclusive():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail:
            return False, (
                "expected an empty detail when configured with no attempt recorded yet, got %r" % (detail,))
        return True, ""
    check(
        "with a calendar configured and no fetch attempt recorded yet, render() emits the 'Connected' "
        "verdict with an empty detail (D-14b)",
        _calendar_status_configured_pending_is_exclusive)

    def _calendar_status_configured_fetch_failed_is_exclusive():
        # D-14b/T-20-30: at least one attempt recorded with no usable
        # sync yet is the one derivable failed-fetch category — the
        # fixed, mapped sentence, never a caught exception's own text.
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None,
            calendar_last_attempt_at=1893456000.0)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail != escape_html(config_page.CALENDAR_STATUS_FETCH_FAILED_DETAIL):
            return False, "expected the mapped fetch-failed sentence, got %r" % (detail,)
        return True, ""
    check(
        "with a calendar configured, an attempt recorded, and no usable sync, render() emits the mapped "
        "'The feed could not be read' detail — never an exception's own text (D-14b/T-20-30)",
        _calendar_status_configured_fetch_failed_is_exclusive)

    def _calendar_status_configured_synced_is_exclusive_with_relative_age():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True,
            calendar_last_synced_at="2026-09-07T09:00:00+00:00", calendar_entry_count=12)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if "12" not in detail:
            return False, "expected the entry count '12' in the detail, got %r" % (detail,)
        if "ago" not in detail:
            return False, "expected a relative-age fragment, proving relative_age_text() was used"
        return True, ""
    check(
        "with a calendar configured and a last_synced_at present, render() emits the 'Connected' verdict "
        "with a detail carrying the entry count and a relative-age fragment, never a bare ISO string "
        "(D-14b)",
        _calendar_status_configured_synced_is_exclusive_with_relative_age)

    def _calendar_status_unparseable_synced_falls_back_to_no_detail():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True,
            calendar_last_synced_at="not-a-real-timestamp")
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail:
            return False, "expected an empty detail for an unparseable stored value, got %r" % (detail,)
        return True, ""
    check(
        "with a calendar configured and a last_synced_at that is present but unparseable, the empty "
        "detail is used rather than a fabricated time (D-14b)",
        _calendar_status_unparseable_synced_falls_back_to_no_detail)

    def _calendar_copy_fidelity_against_ui_spec():
        # 30-06-PLAN.md Task 3: the connection block's own caption
        # constant is dropped from this list — it is deleted outright
        # (folded into the Calendar row, which has no caption), so there
        # is no longer a value to fidelity-check against the spec for it.
        # Every other constant this check pins is unchanged.
        spec_path = os.path.join(
            REPO_ROOT, ".planning", "phases",
            "20-companion-suggestions-from-the-audit-french-localisation-liv",
            "20-UI-SPEC.md")
        with open(spec_path, encoding="utf-8") as fh:
            spec = fh.read()
        for name in (
                "CALENDAR_STATUS_DETAIL_TEMPLATE",
                "CALENDAR_STATUS_FETCH_FAILED_DETAIL",
                "CALENDAR_CONNECT_BUTTON_TEXT",
                "CALENDAR_REPLACE_URL_SUMMARY"):
            value = getattr(config_page, name)
            if value not in spec:
                return False, "%s is not a contiguous substring of 20-UI-SPEC.md: %r" % (name, value)
        return True, ""
    check(
        "the status detail template, the fetch-failed sentence, the Connect button text, and the "
        "Replace-URL disclosure summary are each a contiguous substring of 20-UI-SPEC.md, so a "
        "paraphrase fails rather than merely looking different (D-14a..c)",
        _calendar_copy_fidelity_against_ui_spec)

    def _calendar_merged_button_copy_fidelity_against_21_ui_spec():
        # 21-07-PLAN.md Task 1 (D-13/D-14): the two new short button-
        # text constants the merge introduces — pinned against phase
        # 21's own UI-SPEC, matching _calendar_copy_fidelity_against_
        # ui_spec()'s established discipline for the phase-20 strings.
        spec_path = os.path.join(
            REPO_ROOT, ".planning", "phases",
            "21-companion-feedback-round-3-frame-controls-up-front-home-with",
            "21-UI-SPEC.md")
        with open(spec_path, encoding="utf-8") as fh:
            spec = fh.read()
        for name in ("CALENDAR_REPLACE_BUTTON_TEXT", "CALENDAR_DISCONNECT_BUTTON_TEXT"):
            value = getattr(config_page, name)
            if value not in spec:
                return False, "%s is not a contiguous substring of 21-UI-SPEC.md: %r" % (name, value)
        return True, ""
    check(
        "the merged card's own two new short button-text constants (the connected-state Replace "
        "button, the small grey Disconnect button) are each a contiguous substring of 21-UI-SPEC.md "
        "(D-13/D-14)",
        _calendar_merged_button_copy_fidelity_against_21_ui_spec)

    def _calendar_forbidden_vocabulary_absent():
        # 16-UI-SPEC.md's own "What this section deliberately does NOT
        # say" section (carried forward, unaffected by this plan's
        # rewording) bans AFFIRMATIVE real-time-awareness claims and
        # person/role/employer/crew-function nouns.
        #
        # 30-06-PLAN.md Task 3: the connection block's own heading and
        # caption constants are retired (it folds into the Calendar
        # row, which has no heading or caption of its own any more) —
        # the row label that names the row now, FRAME_COLOURS_ROW_
        # LABELS[COLOUR_USAGE_CALENDAR], takes their place in the blob
        # this check scans; every other live calendar-copy constant is
        # kept.
        blob = " ".join([
            config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_CALENDAR],
            config_page.CALENDAR_HOW_IT_WORKS_BODY,
            config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT,
            config_page.CALENDAR_STATUS_CONNECTED_VERDICT,
        ]).lower()
        forbidden_phrases = (
            "watches", "watch for", "follows", "monitors", "notifies",
            "currently flying", "in the air now", "on duty", "crew",
            "roster", "pilot", "duty roster",
        )
        bad = [phrase for phrase in forbidden_phrases if phrase in blob]
        if bad:
            return False, "forbidden vocabulary found: %r" % (bad,)
        if re.search(r"\btracks\b|\bis tracking\b|\bwatching\b|\bmonitoring\b", blob):
            return False, "found an affirmative tracking/watching/monitoring claim"
        if "does not track" not in blob:
            return False, "expected the mandated negated 'does not track ... on its own' construction"
        return True, ""
    check(
        "the Calendar card's copy carries none of the phase's banned affirmative real-time-awareness or "
        "crew-role vocabulary, while still carrying the mandated negated 'does not track' construction "
        "verbatim",
        _calendar_forbidden_vocabulary_absent)

    def _calendar_secret_never_reaches_render_function():
        # 21-07-PLAN.md Task 2 (D-14/R-10): EXTENDED, not replaced — this
        # check now also exercises the masked-URL line (state_dir wired
        # through), asserting the host + "…" fragment DOES appear (proof
        # the masking helper actually ran) while the token, path, query-
        # parameter name and the whole raw URL still never do.
        token = "sk1-distinctive-token-2rv9"
        host = "private-crew-calendar.example.internal"
        path = "feeds/roster-export"
        query_param = "auth_token"
        url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            assert calendar_rules.save_calendar_url(tmpdir, url) is True
            configured = calendar_rules.calendar_is_configured(tmpdir)
            if not configured:
                return False, "expected calendar_is_configured() to report True with the secret file written"
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=configured,
                calendar_last_synced_at=None, state_dir=tmpdir)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        if escape_html("%s…" % host) not in rendered:
            return False, "expected the masked host + ellipsis fragment to appear once connected"
        for needle in (token, path, query_param, url):
            if needle in rendered:
                return False, "expected %r never to appear in the rendered page" % (needle,)
        return True, ""
    check(
        "with the calendar secret file holding a URL carrying a distinctive token, render() emits the "
        "masked host + ellipsis fragment but never the token, the path segment, the query-parameter "
        "name, or the whole raw URL (T-16-SECRET, extended by 21-07-PLAN.md Task 2 for the new masked-"
        "URL line, D-14/R-10)",
        _calendar_secret_never_reaches_render_function)

    def _calendar_no_preview_no_count_in_rendered_page():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            entries = [
                {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                 "start_at": 1893456000.0, "end_at": 1893459600.0},
                {"airline_iata": "AF", "origin_iata": "NCE", "destination_iata": "ORY",
                 "start_at": 1893484800.0, "end_at": 1893488400.0},
                {"airline_iata": "BA", "origin_iata": "LHR", "destination_iata": "ORY",
                 "start_at": 1893500000.0, "end_at": 1893503600.0},
            ]
            # This check's subject is the Settings page's rendered copy, not
            # retention - an explicit `now` bracketing the 2030-dated
            # fixture entries keeps them in-window regardless of the wall
            # clock (render() itself never reads this file back, so this
            # has no effect on the assertions below, but it keeps the write
            # path exercised the same way every run).
            now = 1893456000.0
            if not calendar_rules.write_calendar_registry(
                    tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now):
                return False, "expected the fixture registry write to succeed"
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=True,
                calendar_last_synced_at="2026-09-07T09:00:00+00:00",
                calendar_entry_count=len(entries),
                colour_rules={kind: {} for kind in colour_rules.RULE_KINDS})
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            for code_pattern in (r"\bORY\b", r"\bTLS\b", r"\bNCE\b", r"\bLHR\b", r"\bAF\b", r"\bBA\b"):
                if re.search(code_pattern, rendered):
                    return False, "expected no calendar-derived code matching %r anywhere on the rendered page" % (code_pattern,)
            # D-14b (this plan's own status row) deliberately DOES show a
            # derived flight count now — the old prohibition on a count
            # is retired; only the specific airport/airline codes stay
            # forbidden (16-UI-SPEC.md's own D-01 isolation, unaffected).
            if not re.search(r"\b3\s+upcoming\s+flights?\b", rendered.lower()):
                return False, "expected the D-14b status detail's own flight-count phrase"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a populated calendar registry (real-shaped routes/airline codes) never surfaces any airport "
        "code or airline code, while the status row's own entry count DOES appear (D-14b; 16-UI-SPEC.md "
        "D-01's code-isolation half carried forward, its count-prohibition half retired)",
        _calendar_no_preview_no_count_in_rendered_page)

    def _calendar_d01_registry_entries_never_appear_in_rules_list():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            entries = [
                {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                 "start_at": 1893456000.0, "end_at": 1893459600.0},
            ]
            # This check's subject is D-01 isolation from the rules list, not
            # retention - an explicit `now` bracketing the 2030-dated
            # fixture entry keeps it in-window regardless of the wall clock,
            # for the same reason given in the check above.
            now = 1893456000.0
            if not calendar_rules.write_calendar_registry(
                    tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now):
                return False, "expected the fixture registry write to succeed"
            result = colour_rules.add_rule(
                tmpdir, colour_rules.RULE_KIND_CALLSIGN, "AFR1234", "black")
            if result not in (colour_rules.ADD_OK_NEW, colour_rules.ADD_OK_REPLACED):
                return False, "expected the manual rule to be added, got %r" % (result,)
            registry = colour_rules.load_colour_rules(tmpdir)
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=True,
                calendar_last_synced_at="2026-09-07T09:00:00+00:00",
                colour_rules=registry)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            rules_segment = _rules_row_segment(rendered)
            if "AFR1234" not in rules_segment:
                return False, "expected the manually-added rule's key to appear in the rules list"
            for code_pattern in (r"\bORY\b", r"\bTLS\b"):
                if re.search(code_pattern, rules_segment):
                    return False, "expected no calendar-sourced row (matching %r) in the rules editor" % (code_pattern,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "with both a populated calendar registry and one hand-added colour rule, the rendered rules list "
        "shows exactly the manual rule and no calendar-sourced row (16-VALIDATION.md registry row, D-01)",
        _calendar_d01_registry_entries_never_appear_in_rules_list)

    def _aspect_calendar_row_palette_populated_in_order():
        # 30-05-PLAN.md Task 1 (CFG-85): replaces the retired
        # _calendar_theme_chip_grid_exactly_one_compact_radiogroup_
        # populated_in_order. The calendar row's palette is a real
        # role="radiogroup", populated in registry order with
        # name="calendar_theme_id", carrying no id attribute — the
        # no-id clause is load-bearing: _palette_grid_html() has three
        # call sites on one page, and an id emitted inside it would be
        # three identical ids.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        start, end = _aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_CALENDAR)
        calendar_segment = rendered[start:end]
        grid_match = re.search(r'<div class="palette" role="radiogroup"[^>]*>', calendar_segment)
        if not grid_match:
            return False, "expected a .palette role=radiogroup grid inside the calendar row"
        if ' id="' in grid_match.group(0):
            return False, (
                "expected the calendar row's palette to carry no id attribute, got %r"
                % (grid_match.group(0),))
        radio_values = re.findall(
            r'name="calendar_theme_id" value="([^"]*)"', calendar_segment)
        real_ids = [rid for rid in radio_values if rid]
        if real_ids != list(device_config.THEME_IDS):
            return False, (
                "expected the calendar palette populated in registry order, got %r" % (real_ids,))
        leading_count = len(radio_values) - len(real_ids)
        if leading_count != 1:
            return False, (
                "expected exactly one leading Same-as-departures option, got %d" % leading_count)
        return True, ""
    check(
        "the calendar row's palette carries one leading Same-as-departures option plus exactly one "
        "entry per registered theme, in registry order, with no id attribute of its own (D-06/D-09, "
        "30-05-PLAN.md Task 1, replacing the retired "
        "_calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order)",
        _aspect_calendar_row_palette_populated_in_order)

    def _calendar_theme_chip_grid_saved_value_is_checked():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], calendar_theme_id="black")
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        # D-12 fix (20-REVIEW.md verification gap): every calendar_theme_id
        # radio now also carries a form="settings-form" attribute between
        # class="visually-hidden" and checked - see the Display <h2>-order
        # check further below for the full form= assertion.
        checked_ids = re.findall(
            r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
            rendered)
        if checked_ids != ["black"]:
            return False, "expected exactly the saved calendar_theme_id ('black') checked, got %r" % (checked_ids,)
        return True, ""
    check(
        "with a saved calendar_theme_id, that chip's radio carries checked and no other calendar_theme_id "
        "radio (including the leading 'Same as departures' chip) does (D-06/D-09)",
        _calendar_theme_chip_grid_saved_value_is_checked)

    def _calendar_theme_chip_grid_same_as_departures_checked_when_unset():
        # 21-05-PLAN.md Task 1 (D-09): R-07's own new semantics — an
        # unset calendar_theme_id now checks the leading "Same as
        # departures" chip (submitting the empty string), never the
        # chip matching the base theme itself. This REPLACES the old
        # (pre-D-09) "defaults to the base theme" visual behaviour that
        # test used to pin — the server-side storage semantics
        # (device_config.normalise_calendar_theme_id("") -> None) are
        # unaffected; only which chip's radio is marked `checked`
        # changes.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], theme="black")
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        checked_ids = re.findall(
            r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
            rendered)
        if checked_ids != [""]:
            return False, (
                "expected only the leading 'Same as departures' chip (value='') checked when "
                "calendar_theme_id is unset, got %r" % (checked_ids,))
        return True, ""
    check(
        "with no saved calendar_theme_id, only the leading 'Same as departures' chip is checked — "
        "never the chip matching the currently-selected base theme (D-06/D-09, replacing the retired "
        "pre-D-09 default-to-base-theme behaviour)",
        _calendar_theme_chip_grid_same_as_departures_checked_when_unset)

    # 30-03-PLAN.md Task 1 (CFG-85): the two checks that used to live
    # here — the calendar-placement-and-dirty-attr check and the
    # calendar-no-inline-JS/chip-grid-cross-submits check (see
    # _ASPECT_REPIN_LEDGER below for both rows' own respelled "retired"
    # labels, 30-06-PLAN.md Task 3) — both asserted against
    # FRAME_COLOURS_HEADING_ID/COLOUR_USAGE_PANEL_TARGET_ATTR, both
    # retired by CFG-85's rebuild. Paid back — see below.

    def _handle_post_calendar_theme_id_valid_persists_and_carries_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"calendar_theme_id": "white"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] != "white":
                return False, (
                    "expected calendar_theme_id 'white' on disk, got %r"
                    % (on_disk["calendar_theme_id"],))
            if on_disk["theme"] != "black":
                return False, (
                    "expected the existing theme 'black' to be carried forward unchanged, got %r"
                    % (on_disk["theme"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a valid calendar_theme_id persists it and carries every other field forward",
        _handle_post_calendar_theme_id_valid_persists_and_carries_forward)

    def _handle_post_calendar_theme_id_adversarial_rejected():
        # 21-05-PLAN.md Task 2 (D-09/R-07): "" is retargeted OUT of this
        # adversarial list — it is now the Frame colours card's own
        # legitimate "Same as departures" clear signal, covered by its
        # own dedicated round-trip check elsewhere in this file.
        for payload in ("chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post({"calendar_theme_id": payload}, ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, (
                        "expected FLASH_SAVE_FAILED for calendar_theme_id=%r, got %r"
                        % (payload, flash_key))
                if before != after:
                    return False, (
                        "expected device_config.json to be byte-identical for calendar_theme_id=%r, it changed"
                        % (payload,))
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post with a non-member calendar_theme_id (a plain invalid id, a path-traversal-shaped "
        "payload, and a SQL-shaped payload) rejects the whole submission and writes nothing — '' is "
        "explicitly exempted from this rejection (D-09)",
        _handle_post_calendar_theme_id_adversarial_rejected)

    def _handle_post_calendar_theme_id_absent_leaves_unchanged():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            device_config.save_device_config(tmpdir, calendar_theme_id="green")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] != "green":
                return False, (
                    "expected calendar_theme_id to remain 'green' when the field is absent, got %r"
                    % (on_disk["calendar_theme_id"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with no calendar_theme_id field at all leaves an already-saved value untouched",
        _handle_post_calendar_theme_id_absent_leaves_unchanged)

    # ==================================================================
    # Section 1c (17-03-PLAN.md Task 3, D-01/D-02/D-07): the write-only
    # calendar_url field, the disconnect checkbox, the fourth (drift)
    # status state, and handle_post()'s three-way calendar resolution.
    # The empty-field-with-no-checkbox regression check below is the
    # single most important check in this plan (17-03-PLAN.md Task 3
    # item 6) — it is the regression the checkbox exists to prevent, and
    # it is invisible to any check that only exercises the calendar
    # fields deliberately.
    # ==================================================================

    # Four distinguishable _calendar_connection_html() states, matching Task 1's
    # own <behavior> bullets: (configured, drift, last_synced_at).
    _CALENDAR_GROUP_STATES = (
        (False, False, None),
        (True, False, None),
        (True, False, "2026-09-07T09:00:00+00:00"),
        (False, True, None),
    )

    def _calendar_connection_call(configured, drift, last_synced_at):
        # 20-09-PLAN.md Task 1: _calendar_connection_html()'s widened signature —
        # last_attempt_at/entry_count are the two new parameters D-14b
        # needs, both harmlessly None/0 for these markup-shape checks.
        #
        # 30-06-PLAN.md Task 3: _calendar_connection_html() is retired; its
        # replacement, _calendar_connection_html(), returns a
        # (row_body_html, disconnect_form_html) TUPLE rather than one
        # concatenated string (the row body nests inside a <details>,
        # the disconnect <form> must not — 30-PATTERNS.md). Every check
        # below that calls this helper treats its return value as ONE
        # string, exactly matching _calendar_connection_html()'s own retired
        # shape — string-joining the tuple here, once, preserves every
        # one of those checks unmodified.
        return "".join(config_page._calendar_connection_html(
            configured, drift, last_synced_at, None, "2026-09-07T09:12:04+00:00",
            0, None, "white"))

    def _calendar_connect_field_never_carries_value_in_either_state():
        # 21-07-PLAN.md Task 1 (D-13/D-14): the write-only feed-URL field
        # is now merged INTO _calendar_connection_html() itself — the not-connected
        # branch renders it unwrapped, the connected branch renders the
        # SAME field inside the Replace disclosure. Either way the field
        # never carries a value attribute (T-20-12).
        for configured in (False, True):
            html = _calendar_connection_call(configured, False, None)
            if 'name="calendar_url"' not in html:
                return False, "expected the calendar_url field when configured=%r" % (configured,)
            after_name = html.split('name="calendar_url"', 1)[1].split(">", 1)[0]
            if "value=" in after_name:
                return False, (
                    "expected no value attribute on the calendar_url field when configured=%r"
                    % (configured,))
        return True, ""
    check(
        "the write-only calendar_url field renders in the merged _calendar_connection_html()'s own markup for "
        "both the connected and not-connected states and never carries a value attribute (D-13/D-14, "
        "retargeted after calendar_connect_section()'s retirement)",
        _calendar_connect_field_never_carries_value_in_either_state)

    def _calendar_connect_wraps_in_details_only_when_configured():
        # D-13/D-14: "While connected, the URL input is hidden behind a
        # 'Replace the feed URL' disclosure; while not connected, render
        # it unwrapped." The merged card ALSO always renders a second,
        # unrelated <details> ("How it works") in every state, so this
        # check scans for the Replace disclosure's own specific class
        # rather than a bare "<details" substring, which would always
        # be true now (Pitfall of the merge, not of the original check).
        connected_html = _calendar_connection_call(True, False, None)
        if 'class="calendar-url-disclosure"' not in connected_html:
            return False, "expected the connect form wrapped in <details class=calendar-url-disclosure> when configured"
        if escape_html(config_page.CALENDAR_REPLACE_URL_SUMMARY) not in connected_html:
            return False, "expected the Replace-the-feed-URL summary when configured"
        not_connected_html = _calendar_connection_call(False, False, None)
        if 'class="calendar-url-disclosure"' in not_connected_html:
            return False, "expected the connect form unwrapped (no calendar-url-disclosure) when not configured"
        if 'action="%s"' % config_page.CALENDAR_CONNECT_ROUTE not in not_connected_html:
            return False, "expected the connect form to post to CALENDAR_CONNECT_ROUTE either way"
        return True, ""
    check(
        "the merged _calendar_connection_html() wraps its connect form in <details class=calendar-url-disclosure> "
        "'Replace the feed URL' only when configured, and renders it unwrapped, posting to "
        "CALENDAR_CONNECT_ROUTE, when not (D-13/D-14, retargeted after calendar_connect_section()'s "
        "retirement)",
        _calendar_connect_wraps_in_details_only_when_configured)

    def _calendar_containment_at_the_renderer_five_needles():
        # The same five needles _calendar_secret_never_reaches_served_
        # http_bytes() (Section 3, below) uses, applied directly at the
        # merged _calendar_connection_html() — the one function that now renders
        # everything the Calendar card shows, including the connect/
        # replace form and the disconnect button — rather than only at
        # the served-HTTP-bytes boundary or the whole-page render()
        # boundary the two other T-17-SECRET checks already cover.
        # 21-07-PLAN.md Task 1: _calendar_connection_html() itself still never
        # receives the raw URL as of this task (Task 2 widens that
        # contract, narrowly, for the masked-URL line only — see that
        # task's own extended coverage of the two checks named above).
        token = "sk1-distinctive-token-9fq2"
        host = "private-roster-calendar.example.internal"
        path = "feeds/duty-export"
        query_param = "auth_token"
        url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            assert calendar_rules.save_calendar_url(tmpdir, url) is True
            configured = calendar_rules.calendar_is_configured(tmpdir)
            drift = calendar_rules.calendar_secret_mode_is_unsafe(tmpdir)
            group_html = _calendar_connection_call(configured, drift, None)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        for needle in (token, host, path, query_param, url):
            if needle in group_html:
                return False, "expected %r never to appear in the merged _calendar_connection_html()'s own markup" % (needle,)
        return True, ""
    check(
        "the merged _calendar_connection_html(), called directly rather than through render(), never emits the "
        "token, host, path segment, query-parameter name, or whole URL of a configured calendar, even "
        "though it now also renders the connect/replace form and the disconnect button (T-17-SECRET, "
        "retargeted after calendar_connect_section()'s retirement)",
        _calendar_containment_at_the_renderer_five_needles)

    def _calendar_disconnect_checkbox_never_appears_in_calendar_connection():
        # 19-11-PLAN.md Task 1 (D-08/A-26): the in-form disconnect
        # checkbox is retired outright from _calendar_connection_html() in EVERY
        # one of its four distinguishable states — disconnecting is now
        # its own standalone, confirmed form, checked separately below.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_connection_call(configured, drift, last_synced_at)
            if 'name="calendar_disconnect"' in html:
                return False, (
                    "state %r: expected _calendar_connection_html() to render no calendar_disconnect "
                    "checkbox at all (D-08 retires it)" % ((configured, drift),))
        return True, ""
    check(
        "_calendar_connection_html() renders no calendar_disconnect checkbox in any of its four states "
        "(D-08/A-26: disconnecting is now its own standalone form, not an in-form checkbox)",
        _calendar_disconnect_checkbox_never_appears_in_calendar_connection)

    def _calendar_disconnect_form_appears_only_when_expected():
        # 21-07-PLAN.md Task 1 (D-14): retargeted after calendar_
        # disconnect_section()'s retirement — the disconnect form is now
        # a data-only sibling fragment the merged _calendar_connection_html()
        # concatenates onto its own card, under the same predicate
        # (configured or drift) the retired standalone function used.
        # Drift additionally gets a visible small Disconnect button
        # (with no Replace disclosure — drift's own verdict already
        # reads "Not connected") so a drifted, unreadable stored link
        # can still be cleared.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_connection_call(configured, drift, last_synced_at)
            has_form = (
                '<form id="%s" method="post" action="%s"'
                % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE)
            ) in html
            expected = configured or drift
            if has_form != expected:
                return False, (
                    "state %r: expected disconnect-form presence %r, got %r"
                    % ((configured, drift), expected, has_form))
            if has_form:
                if 'data-confirm-field' not in html:
                    return False, "expected the hidden confirm field to carry data-confirm-field"
                if 'name="%s" value=""' % config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD not in html:
                    return False, "expected the hidden confirm field to render with an EMPTY value"
                if "data-confirm=" not in html:
                    return False, "expected a data-confirm attribute carrying the confirm question"
                if (
                    'form="%s" class="calendar-disconnect-btn"' % config_page.CALENDAR_DISCONNECT_FORM_ID
                ) not in html:
                    return False, "expected a visible Disconnect button cross-submitting via form="
            else:
                # D-13: a plain not-connected render (no drift either)
                # shows the URL field and the primary Connect button —
                # and no Replace disclosure, no Disconnect button, no
                # data-confirm attribute at all.
                if "calendar-disconnect-btn" in html:
                    return False, "expected no Disconnect button when neither configured nor drifted"
                if "data-confirm=" in html:
                    return False, "expected no data-confirm attribute when neither configured nor drifted"
                if 'class="calendar-url-disclosure"' in html:
                    return False, "expected no Replace disclosure when neither configured nor drifted"
        return True, ""
    check(
        "the merged _calendar_connection_html() renders its disconnect form only when the calendar is connected "
        "or drifted, posting to CALENDAR_DISCONNECT_ROUTE with a hidden, empty, data-confirm-field-"
        "carrying confirm field, alongside a visible small Disconnect button cross-submitting via "
        "form= (D-08/A-26/D-14, retargeted after calendar_disconnect_section()'s retirement)",
        _calendar_disconnect_form_appears_only_when_expected)

    def _look_supersection_carries_exactly_one_dirty_section_named_aspect():
        # 30-06-PLAN.md Task 3 (CFG-85): REPLACES the retired D-13 check
        # that counted `data-dirty-section="Calendar"` — that property
        # itself changed shape, not merely its locator. Display's Look
        # supersection used to carry TWO `data-dirty-section` cards
        # (the former "Frame colours"/"Aspect" card and the separate
        # "Calendar" card); since 30-06-PLAN.md folds the calendar's
        # connection block INTO the Aspect card's own Calendar row,
        # there is now exactly ONE, "Aspect" — the correct arithmetic
        # for "one tile is one section" (CFG-85's own stated goal), not
        # a narrowed count check that would pass vacuously against a
        # missing second card. Checked in both the connected and
        # not-connected states, since the connected state additionally
        # concatenates a data-only sibling disconnect `<form>` fragment
        # that must never itself carry a data-dirty-section attribute.
        for configured in (False, True):
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=configured, calendar_last_synced_at=None)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            look_start = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
            look_end = rendered.index('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID, look_start)
            look_segment = rendered[look_start:look_end]
            count = look_segment.count(config_page.DIRTY_SECTION_ATTR + "=")
            if count != 1:
                return False, (
                    "configured=%r: expected exactly one data-dirty-section card under Look, got %d"
                    % (configured, count))
            expected_attr = '%s="%s"' % (
                config_page.DIRTY_SECTION_ATTR, escape_html(i18n.t(config_page.ASPECT_HEADING)))
            if expected_attr not in look_segment:
                return False, (
                    "configured=%r: expected the one Look card's dirty-section attribute to name "
                    "the Aspect heading" % (configured,))
        return True, ""
    check(
        "Display's Look supersection carries exactly ONE data-dirty-section card (named 'Aspect'), "
        "in both the connected and not-connected states — down from the two ('Aspect'/'Calendar') "
        "it carried before the calendar's connection block folded into the Aspect card's own "
        "Calendar row (CFG-85, replacing the retired data-dirty-section=\"Calendar\" count check, "
        "whose own property this merge changes rather than merely relocates)",
        _look_supersection_carries_exactly_one_dirty_section_named_aspect)

    def _calendar_connection_never_nests_a_form_inside_another_in_either_state():
        # D-13/Pitfall 2: the merged card's own connect/replace <form>
        # and its data-only disconnect-form sibling must never nest one
        # inside the other, in either the connected or not-connected
        # state — the same depth-tracking algorithm the Frame colours
        # card's own full-shape checklist uses, applied directly at the
        # merged _calendar_connection_html()'s own return value (card + sibling
        # disconnect form) rather than only at the whole-page boundary.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_connection_call(configured, drift, last_synced_at)
            depth = 0
            pos = 0
            while True:
                open_pos = html.find("<form", pos)
                close_pos = html.find("</form>", pos)
                if open_pos == -1 and close_pos == -1:
                    break
                if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                    if depth >= 1:
                        return False, (
                            "state %r: expected no <form> nested inside another <form>"
                            % ((configured, drift),))
                    depth += 1
                    pos = open_pos + len("<form")
                else:
                    depth -= 1
                    pos = close_pos + len("</form>")
        return True, ""
    check(
        "the merged _calendar_connection_html()'s own return value (the card plus its data-only disconnect-form "
        "sibling) never nests one <form> inside another, in any of its four distinguishable states "
        "(D-13/Pitfall 2)",
        _calendar_connection_never_nests_a_form_inside_another_in_either_state)

    def _calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr():
        # 30-06-PLAN.md Task 3 (CFG-85): replaces the retired
        # _calendar_placement_after_display_form_close_with_dirty_attr
        # (_ASPECT_REPIN_LEDGER row, owed_by 30-06). The calendar's
        # connection block used to render as its own SEPARATE card,
        # after the settings form's own closing tag and after the
        # Aspect card's own heading. It now renders INSIDE the Calendar
        # row itself — this check asserts the RELATIONSHIP rather than
        # the three endpoints separately: the connection block's own
        # status row renders inside the Calendar row's own data-usage
        # segment, AFTER that row's palette; the visible Disconnect
        # button lives inside the row; the disconnect <form> it
        # cross-submits to is a sibling of the WHOLE Aspect card, never
        # nested inside the row or the card; and the button's own
        # form= attribute names that exact sibling form's id — a check
        # that only asserted all three pieces existed separately would
        # pass even if the button pointed at nothing.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        form_start = rendered.index('<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
        form_end = rendered.index("</form>", form_start)
        aspect_heading_pos = rendered.index('id="%s">%s</h2>' % (
            config_page.ASPECT_HEADING_ID, escape_html(i18n.t(config_page.ASPECT_HEADING))))
        calendar_start, calendar_end = _aspect_usage_row_bounds(
            rendered, config_page.COLOUR_USAGE_CALENDAR)
        if not (form_end < aspect_heading_pos < calendar_start):
            return False, (
                "expected </form> < the Aspect heading < the Calendar row, got %d/%d/%d"
                % (form_end, aspect_heading_pos, calendar_start))
        calendar_segment = rendered[calendar_start:calendar_end]
        palette_pos = calendar_segment.index('class="palette"')
        status_row_pos = calendar_segment.index('class="status-row')
        if not (palette_pos < status_row_pos):
            return False, "expected the palette to precede the connection block's own status row"
        disconnect_btn_match = re.search(
            r'<button type="submit" form="([^"]*)" class="calendar-disconnect-btn">',
            calendar_segment)
        if not disconnect_btn_match:
            return False, "expected the Disconnect button inside the Calendar row"
        disconnect_form_needle = '<form id="%s"' % config_page.CALENDAR_DISCONNECT_FORM_ID
        if disconnect_form_needle in calendar_segment:
            return False, "expected the disconnect form OUTSIDE the Calendar row, found it inside"
        if disconnect_btn_match.group(1) != config_page.CALENDAR_DISCONNECT_FORM_ID:
            return False, (
                "expected the Disconnect button's form= to name %r, got %r"
                % (config_page.CALENDAR_DISCONNECT_FORM_ID, disconnect_btn_match.group(1)))
        if disconnect_form_needle not in rendered[calendar_end:]:
            return False, "expected the disconnect form as a sibling of the whole Aspect card"
        if config_page.DIRTY_SECTION_ATTR not in rendered[:calendar_start]:
            return False, "expected the Aspect card's own dirty-section tracking attribute to precede the row"
        return True, ""
    check(
        "the calendar connection block renders inside the Calendar row, after that row's own palette, "
        "after the settings form's own closing tag and the Aspect card's own heading, still under the "
        "Aspect card's own dirty-section tracking attribute — with the Disconnect button inside the "
        "row and the disconnect form OUTSIDE the card, the button's form= naming that exact sibling "
        "(CFG-85, replacing the retired _calendar_placement_after_display_form_close_with_dirty_attr)",
        _calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr)

    def _calendar_row_no_inline_js_and_palette_cross_submits_form():
        # 30-06-PLAN.md Task 3 (CFG-85): replaces the retired
        # calendar-card no-inline-JS/chip-grid-cross-submits check
        # (_ASPECT_REPIN_LEDGER row, owed_by 30-06 — the row's own
        # "retired" label is respelled, see that row's own comment).
        # The property is unchanged: the calendar row renders no inline
        # event-handler attribute and no <script> tag, and every
        # calendar_theme_id radio cross-submits into the settings form
        # via form=settings-form — only the locator (the row's own
        # data-usage attribute, not the retired COLOUR_USAGE_PANEL_
        # TARGET_ATTR) and the palette markup (calendar_theme_id radios
        # now render inside a .palette grid, not the retired compact
        # chip strip) change.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        calendar_start, calendar_end = _aspect_usage_row_bounds(
            rendered, config_page.COLOUR_USAGE_CALENDAR)
        calendar_segment = rendered[calendar_start:calendar_end]
        if "<script" in calendar_segment:
            return False, "expected no <script> tag inside the Calendar row"
        if re.search(r'\son\w+="', calendar_segment):
            return False, "expected no inline on*= event-handler attribute inside the Calendar row"
        radio_count = calendar_segment.count('name="calendar_theme_id"')
        with_form = len(re.findall(
            r'name="calendar_theme_id" value="[^"]*"[^>]*form="%s"'
            % re.escape(config_page.SETTINGS_FORM_ID), calendar_segment))
        if radio_count == 0:
            return False, "expected at least one calendar_theme_id radio in the Calendar row"
        if with_form != radio_count:
            return False, (
                "expected every calendar_theme_id radio (%d) to cross-submit via form=%r, got %d"
                % (radio_count, config_page.SETTINGS_FORM_ID, with_form))
        return True, ""
    check(
        "the calendar row renders no inline event-handler attribute and no <script> tag, and every "
        "calendar_theme_id radio in its palette cross-submits into the settings form via "
        "form=settings-form (CFG-85, replacing the retired calendar-card no-inline-JS/chip-grid "
        "cross-submits check)",
        _calendar_row_no_inline_js_and_palette_cross_submits_form)

    def _calendar_disconnect_confirm_page_posts_back_with_confirm_preset():
        rendered = config_page.calendar_disconnect_confirm_page({})
        expected_form = (
            '<form method="post" action="%s">'
            '<input type="hidden" name="%s" value="%s">'
        ) % (
            config_page.CALENDAR_DISCONNECT_ROUTE,
            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD,
            html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE, quote=True),
        )
        if expected_form not in rendered:
            return False, "expected the confirm page's form to post to the same route with the confirm field pre-set"
        # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
        # Display this phase, so the cancel link now points back to the
        # page the disconnect action itself lives on.
        if 'href="%s"' % layout.DISPLAY_ROUTE not in rendered:
            return False, "expected a cancel link back to the Display page"
        if "<fieldset" in rendered or "<legend" in rendered:
            return False, "expected no <fieldset>/<legend> on the confirm page"
        return True, ""
    check(
        "calendar_disconnect_confirm_page() renders a form posting to CALENDAR_DISCONNECT_ROUTE with the "
        "confirm field pre-set to the accepted value, plus a plain cancel link to Display (D-08/A-26, "
        "retargeted from Device by 20-07-PLAN.md Task 1/D-11)",
        _calendar_disconnect_confirm_page_posts_back_with_confirm_preset)

    def _calendar_disconnect_form_is_not_inside_settings_form_on_display_scope():
        # 20-07-PLAN.md Task 1 (D-11): Calendar (and its disconnect
        # action) moved from Device to Display this phase — retargeted
        # from SCOPE_DEVICE to SCOPE_DISPLAY in place. 21-07-PLAN.md
        # Task 1 (D-14): the disconnect form's own opening tag now
        # carries an id attribute FIRST (id, method, action, data-
        # confirm, data-confirm-value, per 21-UI-SPEC.md §E's own given
        # markup order) — the literal search below is updated to match.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        settings_form_close = rendered.find("</form>")
        disconnect_form_open = rendered.find(
            '<form id="%s" method="post" action="%s"'
            % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE))
        if settings_form_close == -1:
            return False, "expected the settings form to be present"
        if disconnect_form_open == -1:
            return False, "expected the disconnect form to be present on the Display scope"
        if disconnect_form_open < settings_form_close:
            return False, "expected the disconnect form's opening tag to appear AFTER the settings form's closing tag"
        return True, ""
    check(
        "on the Display scope, the calendar disconnect form's opening tag appears after the settings "
        "form's own closing tag — it is a sibling, never a descendant (D-08/A-26, retargeted from "
        "Device by 20-07-PLAN.md Task 1/D-11, and again by 21-07-PLAN.md Task 1/D-14 for the id-first "
        "attribute order)",
        _calendar_disconnect_form_is_not_inside_settings_form_on_display_scope)

    def _calendar_connect_form_appears_before_the_runway_card_on_display_scope():
        # Polish fix 4 (D-14c): the connect/replace form used to render
        # after the WHOLE Display scope — below Runway and Flight
        # colours — far from the Calendar row. It now renders inside
        # the merged _calendar_connection_html()'s own connected-state Replace
        # disclosure (21-07-PLAN.md Task 1, D-13/D-14), which itself
        # renders after </form> closes (which itself now closes right
        # after the Aspect card, since "What it watches"/Runway moved
        # to a later sibling supersection), so its own <form>'s opening
        # tag still appears strictly BEFORE the Runway card's own radio
        # input in document order.
        #
        # 30-06-PLAN.md Task 3: the Calendar row has no `<h2>` of its
        # own any more (retired alongside the separate Calendar card) —
        # its `data-usage="calendar"` attribute is the landmark now.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        calendar_row_index = rendered.index(
            'data-usage="%s"' % config_page.COLOUR_USAGE_CALENDAR)
        connect_form_index = rendered.index(
            '<form method="post" action="%s"' % config_page.CALENDAR_CONNECT_ROUTE)
        runway_index = rendered.index('name="tracked_runway"')
        if not (calendar_row_index < connect_form_index < runway_index):
            return False, (
                "expected Calendar row < connect form < Runway card, got %d, %d, %d"
                % (calendar_row_index, connect_form_index, runway_index))
        return True, ""
    check(
        "on the Display scope, the calendar connect/replace form's own <form> opening tag renders "
        "immediately after the Calendar row and strictly before the Runway card's own radio "
        "input, never after the whole page's groups (Polish fix 4, D-14c)",
        _calendar_connect_form_appears_before_the_runway_card_on_display_scope)

    def _calendar_disconnect_form_absent_when_not_configured_or_on_device_scope():
        # 20-07-PLAN.md Task 1 (D-11): Calendar never renders on Device
        # any more — retargeted in place (was: "...or on Display scope,
        # which never renders Calendar", the exact inverse, before this
        # phase moved the group).
        not_connected_ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        display_rendered = config_page.render(not_connected_ctx, scope=config_page.SCOPE_DISPLAY)
        if config_page.CALENDAR_DISCONNECT_ROUTE in display_rendered:
            return False, "expected no disconnect form when the calendar is not configured or drifted"
        connected_ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        device_rendered = config_page.render(connected_ctx, scope=config_page.SCOPE_DEVICE)
        if config_page.CALENDAR_DISCONNECT_ROUTE in device_rendered:
            return False, "expected no disconnect form on the Device scope, which never renders Calendar"
        return True, ""
    check(
        "the disconnect form is absent when the calendar is neither configured nor drifted, and absent "
        "from the Device scope, which never renders the Calendar group at all (D-08/A-26, retargeted "
        "from Display by 20-07-PLAN.md Task 1/D-11)",
        _calendar_disconnect_form_absent_when_not_configured_or_on_device_scope)

    def _calendar_status_drift_is_exclusive_and_precedes_not_configured():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None,
            calendar_drift=True)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_NOT_CONNECTED_ESCAPED:
            return False, "expected the 'Not connected' verdict when drifted, got %r" % (verdict,)
        if detail != escape_html(config_page.CALENDAR_STATUS_PERMISSION_UNSAFE):
            return False, "expected the drift detail sentence, got %r" % (detail,)
        return True, ""
    check(
        "with the stored calendar link's permissions drifted, render() emits the 'Not connected' verdict "
        "with the drift detail sentence — the drift branch, checked before 'not configured', still wins "
        "(D-02 ordering, D-14b)",
        _calendar_status_drift_is_exclusive_and_precedes_not_configured)

    def _calendar_status_drift_names_remedy_and_nothing_forbidden():
        text = config_page.CALENDAR_STATUS_PERMISSION_UNSAFE
        if "/" in text or "\\" in text:
            return False, "expected no path separator in the drift status string"
        if ".json" in text or ".ics" in text or "calendar_rules" in text:
            return False, "expected no filename in the drift status string"
        if "http" in text.lower():
            return False, "expected no part of a URL in the drift status string"
        if "paste" not in text.lower() or "feed url" not in text.lower():
            return False, "expected the drift status to name the remedy (paste the feed URL again)"
        return True, ""
    check(
        "the permission-drift status string names the remedy (paste the feed URL again) and names no path "
        "separator, filename, or part of a URL (D-02, 17-CONTEXT.md prohibitions)",
        _calendar_status_drift_names_remedy_and_nothing_forbidden)

    def _handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            for _ in range(2):
                flash_key = config_page.handle_post(
                    {"theme": "white", "calendar_url": ""}, ctx)
                if flash_key != config_page.FLASH_SAVED:
                    return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if not calendar_rules.calendar_is_configured(tmpdir):
                return False, "expected the calendar to remain configured after two unrelated saves"
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if len(registry["entries"]) != 1:
                return False, (
                    "expected the fetched entry to survive untouched, got %r" % (registry["entries"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "the single most important check in this plan (D-07): a form that changes an unrelated setting "
        "and carries an empty calendar_url field with no checkbox, submitted twice in a row via "
        "handle_post(), leaves a configured calendar and its fetched entries completely untouched",
        _handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves)

    def _handle_post_disconnect_clears_url_and_registry():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if calendar_rules.calendar_is_configured(tmpdir):
                return False, "expected the calendar to be disconnected"
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if registry["entries"]:
                return False, "expected zero entries after disconnect, got %r" % (registry["entries"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with the disconnect checkbox at its expected value succeeds, disconnects the "
        "calendar, and empties its fetched-entries registry (D-04)",
        _handle_post_disconnect_clears_url_and_registry)

    def _handle_post_replace_url_stores_new_value_and_clears_registry():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/old.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"calendar_url": "https://example.invalid/new.ics"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            new_url = calendar_rules.configured_calendar_url(tmpdir)
            if new_url != "https://example.invalid/new.ics":
                return False, "expected the new URL to be stored, got %r" % (new_url,)
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if registry["entries"]:
                return False, (
                    "expected zero entries after replacing the URL, got %r" % (registry["entries"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a different non-empty URL stores the new URL and clears the previous "
        "calendar's fetched-entries registry (D-05)",
        _handle_post_replace_url_stores_new_value_and_clears_registry)

    def _handle_post_contradiction_rejects_whole_save_including_unrelated_field():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme": "white",
                    "calendar_url": "https://example.invalid/other.ics",
                    "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
                },
                ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a non-empty URL together with the disconnect checkbox, plus a changed "
        "unrelated setting, rejects the whole save - neither the calendar nor the unrelated setting is "
        "written (D-07 contradiction, all-or-nothing)",
        _handle_post_contradiction_rejects_whole_save_including_unrelated_field)

    def _handle_post_crafted_disconnect_value_rejects_whole_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "calendar_disconnect": "yes"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a crafted calendar_disconnect value rejects the whole save - neither the "
        "calendar nor the unrelated setting is written",
        _handle_post_crafted_disconnect_value_rejects_whole_save)

    def _handle_post_overlength_url_rejects_whole_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            overlength = "https://example.invalid/" + "a" * (config_page.CALENDAR_URL_MAX_LEN + 100)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "calendar_url": overlength}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a calendar_url longer than CALENDAR_URL_MAX_LEN rejects the whole save - "
        "neither the calendar nor the unrelated setting is written",
        _handle_post_overlength_url_rejects_whole_save)

    # ==================================================================
    # Section 2: one end-to-end check — launches the real companion/app.py
    # subprocess, logs in, posts a valid theme-and-runway pair, follows
    # the redirect, and asserts the rendered page carries D-07's
    # confirmation copy verbatim and shows the newly-saved runway
    # selected. No unit check can establish that the router, this page
    # module, and the persistence layer actually agree end to end.
    # ==================================================================

    # --- Phase 18: page scopes and the screen-type registry ---------------

    def _scope_groups_follow_the_screen_registry():
        from companion import screens
        screen = screens.screen_type()
        if config_page.scope_groups(config_page.SCOPE_DISPLAY) != tuple(screen["everyday_groups"]):
            return False, "expected the display scope to render the screen's everyday groups"
        if config_page.scope_groups(config_page.SCOPE_DEVICE) != tuple(screen["advanced_groups"]):
            return False, "expected the device scope to render the screen's advanced groups"
        everyday = set(config_page.scope_groups(config_page.SCOPE_DISPLAY))
        advanced = set(config_page.scope_groups(config_page.SCOPE_DEVICE))
        if everyday & advanced:
            return False, "expected no settings group on both pages, got %r" % (everyday & advanced,)
        if set(config_page.scope_groups(config_page.SCOPE_ALL)) != everyday | advanced:
            return False, "expected the legacy all-scope to be exactly the union of the two pages"
        if screens.screen_type("no-such-screen") is not screens.screen_type():
            return False, "expected an unknown screen id to fall back to the default screen"
        if screens.current_screen_id({"screen_id": "no-such-screen"}) != screens.DEFAULT_SCREEN_ID:
            return False, "expected a hostile ctx screen_id to resolve to the default screen"
        return True, ""
    check(
        "scope_groups() renders the display/device pages from companion/screens.py's per-screen "
        "declaration — disjoint, together equal to the legacy single page — and unknown screen ids "
        "fall back to the default screen",
        _scope_groups_follow_the_screen_registry)

    # --- 23-07-PLAN.md Task 2 (D2/CFG-36, X1/D-04): the Diagnostic LED
    # becomes the third real switch. ONE control for the setting
    # afterwards — a switch beside a surviving checkbox is exactly the
    # defect X1/D-04 was written to remove.

    def _the_led_group_renders_one_switch_and_no_surviving_checkbox():
        for stored in (True, False):
            rendered = config_page.led_group(stored)
            if 'name="led_enabled"' in rendered:
                return False, (
                    "stored=%r: an input named led_enabled still renders in the LED group — the "
                    "switch and a surviving checkbox would be TWO controls for one setting, the "
                    "exact defect X1/D-04 exists to remove" % (stored,))
            expected = (
                '<button type="submit" class="switch" role="switch" aria-checked="%s"'
                ' aria-labelledby="%s" aria-describedby="%s %s" %s form="%s">'
                % ("true" if stored else "false",
                   config_page.QUICK_LED_LABEL_ID, config_page.QUICK_LED_STATE_ID,
                   config_page.LED_SECTION_CAPTION_ID, layout.QUICK_SWITCH_CONTROL_ATTR,
                   config_page.QUICK_LED_FORM_ID))
            if expected not in rendered:
                return False, (
                    "stored=%r: expected the server-rendered switch %r — aria-checked is the "
                    "SAVED value, the name is the setting, and the group's own caption stays "
                    "reachable as a description; got %r"
                    % (stored, expected, rendered))
            if rendered.count('role="switch"') != 1:
                return False, (
                    "stored=%r: expected exactly ONE control in the LED group, got %d role=switch "
                    "elements" % (stored, rendered.count('role="switch"')))
            # The button is attached ACROSS the DOM to a form that is a
            # sibling of #settings-form: the group renders INSIDE the
            # settings form, and a <form> can never nest inside another.
            if ('form="%s"' % config_page.QUICK_LED_FORM_ID) not in rendered:
                return False, (
                    "stored=%r: the switch must reach its own form through a form= attribute — "
                    "the cross-DOM idiom the Send-a-test button already uses, because this card "
                    "renders inside <form id=\"settings-form\">" % (stored,))
            if config_page.LED_SECTION_CAPTION_ID not in rendered:
                return False, "stored=%r: the group's caption id is gone" % (stored,)
            # The pending-marker host and both translated state wordings.
            if layout.QUICK_SWITCH_REGION_ATTR not in rendered:
                return False, (
                    "stored=%r: the LED card carries no %s — quick-switch.js has nothing to mark "
                    "pending" % (stored, layout.QUICK_SWITCH_REGION_ATTR))
            if (layout.QUICK_STATE_ON_ATTR not in rendered
                    or layout.QUICK_STATE_OFF_ATTR not in rendered):
                return False, "stored=%r: expected both state wordings server-rendered" % (stored,)
        return True, ""
    check(
        "config_page.led_group() renders exactly ONE control for the setting — a server-rendered "
        "role=switch whose aria-checked is the stored value in both directions, named by the "
        "setting, described by its state span AND the group's own caption, attached across the DOM "
        "to its own /quick/led form — and no input[name=\"led_enabled\"] checkbox survives beside "
        "it (D2/CFG-36, X1/D-04, 23-07-PLAN.md Task 2)",
        _the_led_group_renders_one_switch_and_no_surviving_checkbox)

    def _the_quick_led_form_is_a_sibling_of_the_settings_form():
        # The <form> must never nest inside <form id="settings-form">:
        # HTML forbids it and the browser silently drops the inner one,
        # which would make the switch post the SETTINGS route instead —
        # a partial settings save, the exact shape T-23-25 is about.
        section = config_page.quick_led_form_html(True)
        if not section.startswith('<form method="post" action="/quick/led" '):
            return False, (
                "expected the LED quick form to open with its own literal method/action, got %r"
                % (section[:120],))
        if ('id="%s"' % config_page.QUICK_LED_FORM_ID) not in section:
            return False, "expected the form to carry the id the switch's form= attribute names"
        if "data-quick-switch" not in section:
            return False, (
                "expected the D-04 handshake attribute on the form — dirty-state.js and "
                "quick-switch.js both key on it")
        for token in ('<input type="hidden" name="state" value="off">',
                      '<input type="hidden" name="return_to" value="/device">'):
            if token not in section:
                return False, "expected %r in the LED quick form, got %r" % (token, section)
        if config_page.quick_led_form_html(False).count('name="state" value="on"') != 1:
            return False, (
                "the posted state must be the OPPOSITE of the stored one, or pressing the switch "
                "with scripts blocked re-asserts the state it is already in")
        if "<button" in section:
            return False, (
                "the form stays EMPTY — its button lives in the LED card and reaches it across "
                "the DOM, mirroring notifications_test_section()'s own shape")
        # And on a real Device render it is a sibling, not a descendant.
        tmp = tempfile.mkdtemp(prefix="skypane-quick-led-")
        try:
            device_config.save_device_config(tmp, led_enabled=True)
            ctx = {"state_dir": tmp, "device_config": device_config.load_device_config(tmp)}
            device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
            form_open = device.index('<form class="config-form"')
            form_close = device.index("</form>", form_open)
            quick_at = device.index('action="/quick/led"')
            if form_open < quick_at < form_close:
                return False, (
                    "the LED quick form renders INSIDE <form id=\"settings-form\"> — a nested "
                    "<form> is dropped by every browser and the switch would post /settings "
                    "instead, which is a partial settings save (T-23-25)")
            display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            if "/quick/led" in display:
                return False, "expected no LED quick form on the Display scope, which has no LED group"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "config_page.quick_led_form_html() is an EMPTY form carrying its own method/action/id, the "
        "D-04 handshake attribute and the two hidden fields with the posted state inverted from the "
        "stored one — and render() places it as a SIBLING of the settings form on the Device scope "
        "and not at all on Display (D2/CFG-36, 23-07-PLAN.md Task 2)",
        _the_quick_led_form_is_a_sibling_of_the_settings_form)

    def _display_scope_carries_runway_and_calendar_device_carries_neither():
        # 20-07-PLAN.md Task 1 (D-10/D-11): the group move itself, at the
        # registry level.
        display_groups = config_page.scope_groups(config_page.SCOPE_DISPLAY)
        device_groups = config_page.scope_groups(config_page.SCOPE_DEVICE)
        from companion import screens
        if screens.GROUP_RUNWAY not in display_groups or screens.GROUP_CALENDAR not in display_groups:
            return False, "expected Runway and Calendar in scope_groups(SCOPE_DISPLAY), got %r" % (display_groups,)
        if screens.GROUP_RUNWAY in device_groups or screens.GROUP_CALENDAR in device_groups:
            return False, "expected neither Runway nor Calendar in scope_groups(SCOPE_DEVICE), got %r" % (device_groups,)
        return True, ""
    check(
        "scope_groups(SCOPE_DISPLAY) contains Runway and Calendar, and scope_groups(SCOPE_DEVICE) "
        "contains neither (D-10/D-11)",
        _display_scope_carries_runway_and_calendar_device_carries_neither)

    def _display_render_carries_three_section_intros_in_locked_order():
        # 20-07-PLAN.md Task 1 (D-12): Look, What it watches, When it is
        # on, in that document order.
        #
        # RETARGETED (28-04-PLAN.md Task 1, CFG-72): this check used to
        # also assert "and nowhere on the Device scope" — Device's own
        # intro sentence/caption were unchanged by D-12, so Device had no
        # supersection tier at all. CFG-72 gives Device two supersections
        # of its own ("When it wakes"/"How it tells you") plus a third,
        # one-card supersection introducing the Poll card ("When you
        # can't wait") — Device now renders three section-intro headings
        # too, in that locked order. The Display half of this check is
        # untouched; only the Device assertion is retargeted, from
        # "absent" to "present, exactly three, in order".
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        if display.count("section-intro") != 3:
            return False, "expected exactly three section-intro occurrences on Display, got %d" % display.count("section-intro")
        look_pos = display.find('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        watches_pos = display.find('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID)
        on_pos = display.find('id="%s"' % config_page.DISPLAY_ON_SECTION_ID)
        if -1 in (look_pos, watches_pos, on_pos):
            return False, "expected all three supersection heading ids to be present"
        if not (look_pos < watches_pos < on_pos):
            return False, "expected Look < What it watches < When it is on in document order"
        if device.count("section-intro") != 3:
            return False, "expected exactly three section-intro occurrences on Device, got %d" % device.count("section-intro")
        wakes_pos = device.find('id="%s"' % config_page.DEVICE_WAKES_SECTION_ID)
        tells_pos = device.find('id="%s"' % config_page.DEVICE_TELLS_SECTION_ID)
        poll_pos = device.find('id="%s"' % config_page.DEVICE_POLL_SECTION_ID)
        if -1 in (wakes_pos, tells_pos, poll_pos):
            return False, "expected all three Device supersection heading ids to be present"
        if not (wakes_pos < tells_pos < poll_pos):
            return False, "expected When it wakes < How it tells you < When you can't wait in document order"
        return True, ""
    check(
        "the Display scope renders exactly three section-intro headings, in the locked Look/What it "
        "watches/When it is on order, and the Device scope renders exactly three of its own, in the "
        "locked When it wakes/How it tells you/When you can't wait order (D-12, retargeted by "
        "28-04-PLAN.md Task 1/CFG-72 from 'the Device scope renders none')",
        _display_render_carries_three_section_intros_in_locked_order)

    def _every_grouped_card_under_a_display_supersection_carries_nested_class():
        # 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C):
        # Theme, Calendar, Runway, Display and Quiet hours each gain the
        # --nested modifier so their own <h2> renders at the extended
        # .theme-status--nested/.page-section--nested > h2 tier
        # (20-04-PLAN.md Task 1's own CSS selector).
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the floor drops from 5 to
        # 4 — Display's own nested card (theme-status--nested) is retired
        # outright along with display_group() itself, leaving Frame
        # colours/Calendar (page-section--nested) and Runway/Quiet hours
        # (theme-status--nested).
        #
        # 30-06-PLAN.md Task 3 (CFG-85): the floor drops again, 4 -> 3,
        # and the literal needle changes shape — a genuine property
        # change, not a locator repoint. The separate Calendar card
        # (its own bare "page-section page-section--nested" wrapper) is
        # retired outright; its connection block folds into the Aspect
        # card's own Calendar row, so the ONE remaining page-section--
        # nested wrapper on Display is the Aspect card's own —
        # `_nested_wrapper_html(..., "page-section aspect-card", ...)`
        # inserts the modifier AFTER "aspect-card", producing
        # `class="page-section aspect-card page-section--nested"`,
        # never the bare `"page-section page-section--nested"` two-
        # class literal this check used to search for.
        ctx = {
            "device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        for needle in (
                "theme-status theme-status--nested",
                'class="page-section aspect-card page-section--nested"'):
            if needle not in display:
                return False, "expected %r on the Display scope" % (needle,)
        if display.count('class="page-section page-section--nested"') != 0:
            return False, (
                "expected no bare page-section page-section--nested wrapper on Display — the "
                "Calendar card that used to emit it is retired")
        nested_count = display.count("theme-status--nested") + display.count("page-section--nested")
        if nested_count != 3:
            return False, "expected exactly 3 --nested occurrences on Display, got %d" % nested_count
        return True, ""
    check(
        "every grouped card the Display scope renders under one of its three supersections carries "
        "a --nested modifier class — down to 3 occurrences (Aspect's page-section--nested, Runway's "
        "and Quiet hours' theme-status--nested) now that the Calendar card's own separate "
        "page-section--nested wrapper is retired (D-12, CFG-85)",
        _every_grouped_card_under_a_display_supersection_carries_nested_class)

    # 30-03-PLAN.md Task 1 (CFG-85): three checks used to live in this
    # region — _display_h2_order_matches_d12_after_calendar_placement_
    # fix, _title_form_inventory_classifies_every_h2_text_heading_on_
    # both_routes (with its own long CFG-65/CFG-72 history banner) and
    # _no_card_builder_function_ever_calls_section_intro_html (with its
    # own CFG-65 Task 2 banner) — all three pinned FRAME_COLOURS_HEADING/
    # _frame_colours_card_html by name or by counted <h2> position, both
    # retired by CFG-85's rebuild. All three DELETED WITH THEIR OWN
    # HISTORY COMMENTS (a comment arguing a deleted check is a comment
    # about nothing) and LEDGERED — see _ASPECT_REPIN_LEDGER below.
    # 30-06-PLAN.md Task 3 (CFG-85) pays all three back, immediately
    # below, now that the Calendar card's own separate heading is ALSO
    # retired (folded into the Aspect card's Calendar row).

    def _display_h2_order_matches_the_merged_aspect_card_placement():
        # Replaces _display_h2_order_matches_d12_after_calendar_
        # placement_fix (_ASPECT_REPIN_LEDGER row, owed_by 30-06). The
        # exact same D-12 property this check always asserted — the
        # Display scope's <h2> order, and every calendar_theme_id radio
        # still carrying form=settings-form — re-derived for the merged
        # shape: the separate Calendar heading this list used to name
        # is gone outright (not merely renamed, the way Frame colours ->
        # Aspect was); the expected sequence is built from the module's
        # own heading constants, never a retyped literal list.
        ctx = {
            "device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        headings = re.findall(r'<h2[^>]*>(.*?)</h2>', display)
        expected = [
            layout.FRAME_STRIP_HEADING,
            config_page.DISPLAY_LOOK_HEADING, config_page.ASPECT_HEADING,
            config_page.DISPLAY_WATCHES_HEADING,
            "Runway", config_page.DISPLAY_ON_HEADING,
            config_page.QUIET_HOURS_SECTION_HEADING,
        ]
        if headings != expected:
            return False, "expected <h2> order %r, got %r" % (expected, headings)
        calendar_radio_count = display.count('name="calendar_theme_id"')
        calendar_radio_with_form_count = len(
            re.findall(r'name="calendar_theme_id"[^>]*form="%s"' % config_page.SETTINGS_FORM_ID, display))
        if calendar_radio_count == 0 or calendar_radio_with_form_count != calendar_radio_count:
            return False, (
                "expected every one of the %d calendar_theme_id radios to carry form=\"%s\", got %d"
                % (calendar_radio_count, config_page.SETTINGS_FORM_ID, calendar_radio_with_form_count))
        return True, ""
    check(
        "the Display scope's rendered <h2> order is exactly Look, Aspect, What it watches, Runway, "
        "When it is on, Quiet hours — the separate Calendar heading this order used to also name is "
        "retired outright now that its connection block folds into the Aspect card's own Calendar "
        "row — and every calendar_theme_id radio still carries a form=\"settings-form\" attribute "
        "(CFG-85, replacing the retired _display_h2_order_matches_d12_after_calendar_placement_fix)",
        _display_h2_order_matches_the_merged_aspect_card_placement)

    def _title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge():
        # Replaces _title_form_inventory_classifies_every_h2_text_
        # heading_on_both_routes (_ASPECT_REPIN_LEDGER row, owed_by
        # 30-06). The classification itself still holds — settings-card
        # titles (form A) vs. supersection intros (form B) vs.
        # unclassified — with one fewer form-A card title on Display now
        # that Calendar's own separate heading is retired: the tallies
        # are RECOMPUTED from the real render below, never restated as
        # the old 8/4/3/1 literal.
        ctx_display = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        ctx_device = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 5,
        }
        display = config_page.render(ctx_display, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx_device, scope=config_page.SCOPE_DEVICE)

        counts = {}
        for label, rendered in (("display", display), ("device", device)):
            total = rendered.count('class="text-heading"')
            form_a = rendered.count('%s="' % config_page.DIRTY_SECTION_ATTR)
            form_b = rendered.count("section-intro")
            counts[label] = (total, form_a, form_b, total - form_a - form_b)
        # RE-DERIVED BY RUNNING (30-06-PLAN.md Task 3, CFG-85): Display's
        # own tuple moves from (8, 4, 3, 1) to (7, 3, 3, 1) — one fewer
        # h2.text-heading instance and one fewer form-A card title, both
        # for the identical reason (the Calendar card's own separate
        # heading is retired outright). Device's own tuple is untouched.
        expected = {"display": (7, 3, 3, 1), "device": (7, 3, 3, 1)}
        if counts != expected:
            return False, (
                "expected {route: (total h2.text-heading, form-A card titles, form-B "
                "supersection intros, unclassified)} == %r, measured %r by running" % (expected, counts))

        card_title_headings = {
            "display": (
                config_page.ASPECT_HEADING, "Runway", config_page.QUIET_HOURS_SECTION_HEADING),
            "device": (
                config_page.LED_SECTION_HEADING, config_page.WAKE_INTERVAL_SECTION_HEADING,
                config_page.NOTIFICATIONS_SECTION_HEADING),
        }
        for route, rendered in (("display", display), ("device", device)):
            for heading in card_title_headings[route]:
                needle = ">%s</h2>" % escape_html(heading)
                if needle not in rendered:
                    return False, (
                        "expected the settings-card heading %r to render inside its own "
                        "[data-dirty-section] tile on the %s scope, and it did not"
                        % (heading, route))
            if len(card_title_headings[route]) != counts[route][1]:
                return False, (
                    "expected exactly %d form-A card titles named on %s, the allowlist names %d"
                    % (counts[route][1], route, len(card_title_headings[route])))

        # The two unclassified instances, identified by name — neither
        # is a settings card or a supersection intro. Unchanged by the
        # merge (both survive it untouched).
        frame_strip_needle = ">%s</h2>" % escape_html(layout.FRAME_STRIP_HEADING)
        if frame_strip_needle not in display or frame_strip_needle in device:
            return False, (
                "expected the Frame strip's own <h2> (Display's unclassified instance) to "
                "render on Display and never on Device")
        poll_needle = '<h2 class="text-heading">%s</h2>' % escape_html(
            config_page.POLL_SECTION_HEADING)
        if poll_needle not in device or poll_needle in display:
            return False, (
                "expected Poll's own <h2> (Device's unclassified instance) to render on Device "
                "and never on Display (Display never renders Poll)")

        # OUTCOME 2 still holds: the two label vocabularies never
        # overlap.
        overlap = (
            set(card_title_headings["display"]) | set(card_title_headings["device"])
        ) & {
            config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
            config_page.DISPLAY_ON_HEADING, config_page.DEVICE_WAKES_HEADING,
            config_page.DEVICE_TELLS_HEADING, config_page.DEVICE_POLL_HEADING,
        }
        if overlap:
            return False, (
                "expected the settings-card vocabulary and the supersection-label vocabulary "
                "to share no text — found %r in both, which would mean a card's own identity "
                "and a group's own label had collapsed into the same word" % (overlap,))
        return True, ""
    check(
        "the title-form inventory, re-run after the calendar merge: both settings routes' "
        "h2.text-heading instances count and classify as 6 settings-card titles (form A, 3 on "
        "Device + 3 on Display, down from 4 now that Calendar's own separate heading is retired) "
        "+ 3 supersection intros (form B) + 2 unrelated headings, with the counts re-derived by "
        "RUNNING rather than restated as the pre-merge 8/4/3/1 literal, and the two label "
        "vocabularies still never overlapping (CFG-85, replacing the retired "
        "_title_form_inventory_classifies_every_h2_text_heading_on_both_routes)",
        _title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge)

    def _no_card_builder_function_ever_calls_section_intro_html_after_the_merge():
        # Re-lands here (_ASPECT_REPIN_LEDGER row, owed_by 30-06,
        # replacement == retired — the same function, its own AST
        # allowlist updated for the merge): the settings-card builder
        # set loses _frame_colours_card_html (retired by 30-04-PLAN.md)
        # and the calendar card's own former builder function (retired
        # by this plan's own Task 1), and gains _aspect_card_html — the
        # one merged builder that now covers everything both of those
        # used to.
        card_builder_names = (
            "_aspect_card_html", "runway_fieldset", "led_group",
            "quiet_hours_group", "wake_interval_group", "notifications_group",
        )
        with open(os.path.join(HERE, "pages", "config_page.py")) as fh:
            source = fh.read()
        tree = ast.parse(source)
        found_names = {
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name in card_builder_names}
        if found_names != set(card_builder_names):
            return False, (
                "expected to find all %d card-builder functions by name in config_page.py, "
                "missing %r — this check's own allowlist is stale"
                % (len(card_builder_names), set(card_builder_names) - found_names))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in card_builder_names:
                for call in ast.walk(node):
                    if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                            and call.func.attr == "section_intro_html"):
                        offenders.append(node.name)
        if offenders:
            return False, (
                "expected ZERO of the %d settings-card builder functions to call "
                "layout.section_intro_html() (form B) for their own <h2> — found it called "
                "from %r. A card's own title must stay form A, never borrow the shared "
                "supersection builder" % (len(card_builder_names), offenders))
        return True, ""
    check(
        "none of the settings-card builder functions (_aspect_card_html/runway_fieldset/"
        "led_group/quiet_hours_group/wake_interval_group/notifications_group — one fewer than "
        "before the merge, since _aspect_card_html now covers what _frame_colours_card_html and "
        "the calendar card's own former builder function used to split between them) ever calls "
        "layout.section_intro_html() for their own heading — the losing form (a card title "
        "produced through the "
        "supersection-intro shape) is ZERO, enforced at the source level, its allowlist length "
        "checked against the real builder-name set rather than a literal (CFG-85, replacing the "
        "retired-and-relanded _no_card_builder_function_ever_calls_section_intro_html)",
        _no_card_builder_function_ever_calls_section_intro_html_after_the_merge)

    # ==================================================================
    # 28-04-PLAN.md Task 2 (CFG-72): the cheap structural guard. THIS IS
    # NOT THE PROOF — companion/test_browser_ux.py's cross-page
    # getComputedStyle comparator is, and that is stated here rather
    # than left implicit, so nobody later mistakes this check for a
    # substitute (that exact mistake is how 27-06 shipped in the first
    # place). This only asserts that the Device scope's rendered markup
    # wraps every one of its four settings cards with the --nested
    # modifier and that zero unmodified settings-card wrappers of either
    # base class survive on that page.
    # ==================================================================

    def _device_scope_wraps_all_four_settings_cards_with_the_nested_modifier():
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        nested_theme_status = device.count('class="theme-status theme-status--nested"')
        if nested_theme_status != 3:
            return False, (
                "expected exactly 3 theme-status--nested settings-card wrappers on Device "
                "(LED, wake interval, notifications), got %d" % nested_theme_status)
        nested_page_section = device.count('class="page-section page-section--nested"')
        if nested_page_section != 1:
            return False, (
                "expected exactly 1 page-section--nested settings-card wrapper on Device "
                "(Poll), got %d" % nested_page_section)
        bare_theme_status = device.count('class="theme-status"')
        if bare_theme_status != 0:
            return False, (
                "expected zero unmodified .theme-status settings-card wrappers on Device, "
                "got %d" % bare_theme_status)
        bare_page_section = device.count('class="page-section"')
        if bare_page_section != 0:
            return False, (
                "expected zero unmodified .page-section settings-card wrappers on Device, "
                "got %d" % bare_page_section)
        return True, ""
    check(
        "the cheap structural guard, NOT the real proof (that is test_browser_ux.py's "
        "cross-page getComputedStyle comparator): the Device scope's rendered output wraps "
        "all four of its settings cards with the --nested modifier (three "
        "theme-status--nested, one page-section--nested) and carries zero unmodified "
        "settings-card wrappers of either base class (CFG-72, 28-04-PLAN.md Task 2)",
        _device_scope_wraps_all_four_settings_cards_with_the_nested_modifier)

    # ==================================================================
    # 20-07-PLAN.md Task 2 (D-19/Pitfall 1): the instant switches, and
    # the form restructure that makes them valid HTML.
    # ==================================================================

    _TASK2_BASE_CTX = {
        "device_config": {
            "display_enabled": True, "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        },
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
    }

    def _display_render_carries_exactly_two_quick_action_forms():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        if rendered.count('action="%s"' % config_page.QUICK_DISPLAY_ROUTE) != 1:
            return False, "expected exactly one action=\"/quick/display\" form"
        if rendered.count('action="%s"' % config_page.QUICK_QUIET_HOURS_ROUTE) != 1:
            return False, "expected exactly one action=\"/quick/quiet-hours\" form"
        return True, ""
    check(
        "a Display render contains exactly one action=\"/quick/display\" form and one "
        "action=\"/quick/quiet-hours\" form (D-19)",
        _display_render_carries_exactly_two_quick_action_forms)

    def _quick_action_forms_are_not_descendants_of_settings_form():
        # 21-04-PLAN.md Task 1 (D-01/D-02): retargeted — both instant-
        # switch forms now render inside the shared Frame strip, BEFORE
        # the settings form even opens, not after it closes.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        settings_form_open = rendered.index('<form class="config-form"')
        for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
            quick_form_pos = rendered.index('action="%s"' % route)
            if quick_form_pos >= settings_form_open:
                return False, (
                    "expected the %s instant-switch form to appear in the Frame strip, "
                    "before the settings form even opens, not nested inside it" % route)
        return True, ""
    check(
        "neither instant-switch form is a descendant of <form id=settings-form> — both render in "
        "the shared Frame strip, before the settings form even opens (D-01/D-02/Pitfall 1)",
        _quick_action_forms_are_not_descendants_of_settings_form)

    def _display_render_carries_no_form_nested_inside_a_form():
        # The pinned regression test for Pitfall 1: a whole-body scan
        # for any "<form" whose nearest preceding unclosed "<form" has
        # not yet been closed — i.e. no <form> is ever a descendant of
        # another <form> anywhere in the rendered Display page.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        depth = 0
        pos = 0
        while True:
            open_pos = rendered.find("<form", pos)
            close_pos = rendered.find("</form>", pos)
            if open_pos == -1 and close_pos == -1:
                break
            if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                if depth >= 1:
                    return False, (
                        "expected no <form> nested inside another <form>, found one "
                        "opening at offset %d" % open_pos)
                depth += 1
                pos = open_pos + len("<form")
            else:
                depth -= 1
                pos = close_pos + len("</form>")
        if depth != 0:
            return False, "expected every <form> to be closed, got an unbalanced depth of %d" % depth
        return True, ""
    check(
        "the rendered Display page contains no <form> nested inside another <form> anywhere "
        "(D-19/Pitfall 1, the required structural fix)",
        _display_render_carries_no_form_nested_inside_a_form)

    def _two_scheduled_inputs_carry_form_settings_form():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): retargeted from four
        # scheduled inputs to two — the display_enabled and
        # quiet_hours_enabled checkboxes this check used to pin are
        # retired outright, along with display_group() and
        # quiet_hours_group()'s own on/off checkbox. Only the Quiet
        # hours schedule itself (Start/End) still cross-submits via
        # form="settings-form" now.
        # 22-10-PLAN.md Task 2 (B14): retargeted again, in place — each
        # time input now also carries `lang` (the site language) between
        # `required` and `form=`. The form= contract this check exists
        # for is unchanged; only the literal it greps had to absorb the
        # new attribute.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for needle in (
                '<input type="time" name="quiet_hours_start" value="22:00" required'
                ' lang="en" form="settings-form"',
                '<input type="time" name="quiet_hours_end" value="06:00" required'
                ' lang="en" form="settings-form"'):
            if needle not in rendered:
                return False, "expected %r in the rendered Display page" % (needle,)
        if 'name="display_enabled"' in rendered or 'name="quiet_hours_enabled"' in rendered:
            return False, "expected no display_enabled/quiet_hours_enabled input on the Display page"
        return True, ""
    # ==================================================================
    # 21-04-PLAN.md Task 1 (D-01/D-02): the Frame strip replaces the two
    # cards' own instant switches — one .quick-action--on/--off pair,
    # inside .frame-strip; neither schedule card carries any
    # quick-action markup any more; each switch's return_to hidden
    # field carries the Display route; the strip sits right after the
    # page header, before the first .section-intro.
    # ==================================================================

    def _display_render_has_exactly_one_quick_action_pair_inside_the_strip():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        on_off_count = (
            rendered.count('quick-action quick-action--on')
            + rendered.count('quick-action quick-action--off'))
        if on_off_count != 2:
            return False, "expected exactly two .quick-action--on/--off cells (Screen + Quiet hours), got %d" % (
                on_off_count,)
        strip_start = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
        strip_end = rendered.index('<form class="config-form"', strip_start)
        strip_segment = rendered[strip_start:strip_end]
        if (
            strip_segment.count('quick-action quick-action--on')
            + strip_segment.count('quick-action quick-action--off') != 2
        ):
            return False, "expected both quick-action cells to sit inside .frame-strip"
        return True, ""
    check(
        "a Display render carries exactly one .quick-action--on/--off pair per switch, both inside "
        ".frame-strip (D-01/D-02)",
        _display_render_has_exactly_one_quick_action_pair_inside_the_strip)

    def _schedule_cards_carry_no_quick_action_markup():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): retargeted to Quiet hours
        # only — the Screen on/off card this loop used to also check is
        # retired outright along with display_group() itself, so there is
        # no longer a second card to check here.
        # 27-08-PLAN.md Task 1 (CFG-69): the literal absorbs the heading's
        # new id="{QUIET_HOURS_GROUP_HEADING_ID}" — the quick-action
        # contract this check exists for is unchanged; only the markup it
        # greps had to grow the new attribute.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for heading in (config_page.QUIET_HOURS_SECTION_HEADING,):
            start = rendered.index(
                '<h2 class="text-heading" id="%s">%s</h2>'
                % (config_page.QUIET_HOURS_GROUP_HEADING_ID, heading))
            next_heading = rendered.find('<h2 class="text-heading"', start + 1)
            segment = rendered[start:next_heading] if next_heading != -1 else rendered[start:]
            if "quick-action" in segment:
                return False, "expected the %r card to carry no quick-action markup" % (heading,)
        return True, ""
    check(
        "the Quiet hours card carries no quick-action markup any more — its switch moved into the "
        "shared Frame strip (D-01/D-02); the Screen on/off card this check used to also cover is "
        "retired outright by 22-05-PLAN.md Task 1 (X1/D-04/D-12.1)",
        _schedule_cards_carry_no_quick_action_markup)

    def _quick_action_forms_carry_return_to_the_display_route():
        # A DIFFERENT, pre-existing "return_to" hidden field also lives
        # inside <form id="settings-form"> itself (_scope_fields_html(),
        # D-10's own scope-aware save-and-return-to-the-same-page
        # mechanism) — same field NAME, different form, different
        # route, no collision in what either POST body actually
        # carries. Scoped to each quick-action <form>...</form> block
        # specifically, not a whole-page substring count, so this check
        # cannot be confused by that unrelated field.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        needle = '<input type="hidden" name="return_to" value="%s">' % layout.DISPLAY_ROUTE
        for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
            form_start = rendered.index('action="%s"' % route)
            form_end = rendered.index("</form>", form_start)
            if needle not in rendered[form_start:form_end]:
                return False, "expected %r inside the %s form" % (needle, route)
        return True, ""
    check(
        "both instant-switch forms on Display carry a return_to hidden input whose value is the "
        "Display route (R-02)",
        _quick_action_forms_carry_return_to_the_display_route)

    def _frame_strip_renders_after_header_before_first_section_intro():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        header_pos = rendered.index('<h1 class="page-title">')
        strip_pos = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
        intro_pos = rendered.index('class="section-intro"')
        if not (header_pos < strip_pos < intro_pos):
            return False, (
                "expected the page header, then the Frame strip, then the first "
                "section-intro, got positions %d, %d, %d" % (header_pos, strip_pos, intro_pos))
        return True, ""
    check(
        "the Frame strip renders immediately after the page header and before the first "
        "section-intro on Display (D-02)",
        _frame_strip_renders_after_header_before_first_section_intro)

    check(
        "the two remaining scheduled inputs (quiet_hours_start, quiet_hours_end) carry "
        "form=\"settings-form\" via the SETTINGS_FORM_ID constant (D-19), and neither "
        "display_enabled nor quiet_hours_enabled renders on the Display page any more "
        "(22-05-PLAN.md Task 1, X1/D-04/D-12.1)",
        _two_scheduled_inputs_carry_form_settings_form)

    def _applies_next_wake_sentence_appears_exactly_twice():
        # 21-04-PLAN.md Task 1 (D-01/D-02): the constant moved to
        # companion/layout.py along with the switch markup it captions.
        # 22-05-PLAN.md Task 2 (D-04) widened this from "exactly twice"
        # to "exactly three times" once the Quiet hours card's own
        # caption started appending the same computed delay sentence.
        #
        # 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: retargeted BACK to
        # "exactly twice" — quiet_hours_group() no longer appends a
        # delay sentence to its own caption at all (see that function's
        # own docstring), so the THIRD occurrence this check used to
        # require is gone, and CFG-79's whole point is that it should
        # be: the apply-timing sentence now renders in exactly one
        # place per page — the Frame strip, which is what these
        # remaining two occurrences are (one per instant switch cell).
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        count = rendered.count(escape_html(layout.QUICK_ACTION_APPLIES_SENTENCE))
        if count != 2:
            return False, (
                "expected the shared instant-switch delay sentence to appear exactly twice (once "
                "per Frame-strip switch cell, and nowhere under the Quiet hours card any more), "
                "got %d" % count)
        return True, ""
    check(
        "the shared \"Applies the next time the frame wakes up.\" sentence appears exactly twice "
        "on the Display page — once per Frame-strip instant switch, and no longer a third time "
        "under the Quiet hours card's own caption now that CFG-79 confines it to one place per "
        "page (29-05-PLAN.md Task 2; widened to three by 22-05-PLAN.md Task 2 D-04, narrowed back "
        "here)",
        _applies_next_wake_sentence_appears_exactly_twice)

    def _handle_post_same_field_set_after_restructure_saves_the_same_config():
        # D-13: only the DOM position of display_group()/quiet_hours_
        # group() changed — handle_post()'s own field set and its
        # absent-checkbox carry-forward are untouched, so a POST with
        # the same field set as before this task still saves identically.
        tmp = tempfile.mkdtemp(prefix="skypane-config-task2-")
        try:
            key = config_page.handle_post(
                {
                    "scope": "display", "theme": "black", "display_enabled": "on",
                    "quiet_hours_enabled": "on", "quiet_hours_start": "23:00",
                    "quiet_hours_end": "07:00",
                },
                {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (key,)
            cfg = device_config.load_device_config(tmp)
            if (
                cfg["theme"] != "black" or cfg["display_enabled"] is not True
                or cfg["quiet_hours_enabled"] is not True
                or cfg["quiet_hours_start"] != "23:00" or cfg["quiet_hours_end"] != "07:00"
            ):
                return False, "expected the same field set to persist identically, got %r" % (cfg,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a POST through handle_post() with the same field set as before the Task 2 restructure "
        "still produces the same saved config (D-13/T-20-26)",
        _handle_post_same_field_set_after_restructure_saves_the_same_config)

    # ==================================================================
    # 20-07-PLAN.md Task 3 (D-05): config_page.py through t(), and its
    # French catalogue (companion/i18n_fr/display.py).
    # ==================================================================

    _TASK3_I18N_CTX = {
        "device_config": {
            "display_enabled": True, "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        },
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        "calendar_configured": True, "calendar_last_synced_at": None,
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    }

    def _french_display_render_carries_french_headings_no_english():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        for french_text in ("Aspect", "Ce qu’il surveille", "Quand il est allumé",
                             "Tout ce que le cadre affiche, et quand.",
                             "S’applique au prochain réveil du cadre."):
            if french_text not in fr_rendered:
                return False, "expected %r in the French Display render" % (french_text,)
        for english_text in ("Look", "What it watches", "When it is on",
                              "Everything about what the frame shows and when.",
                              "Applies the next time the frame wakes up."):
            if english_text in fr_rendered:
                return False, "expected %r to be absent from the French Display render" % (english_text,)
        return True, ""
    check(
        "a French Display render (prefs.set_request_prefs(lang='fr')) carries the three "
        "supersection headings, the purpose sentence and the instant-switch sentence in French, "
        "and none of their English counterparts (D-05)",
        _french_display_render_carries_french_headings_no_english)

    def _french_display_and_device_render_translate_registry_labels():
        # Polish fix 5 (D-05): device_config.theme_label()/runway_
        # label()'s registry text and screens.py's screen label are
        # translated at their config_page.py display sites via
        # i18n.t(), backed by companion/i18n_fr/registry.py — the
        # default theme ("white" -> "White"/"Blanc") and default
        # runway ("3" -> "Runway 3 (07/25)"/"Piste 3 (07/25)") both
        # apply here since _TASK3_I18N_CTX's device_config carries
        # neither key. The ids themselves ("white", "3") are never
        # translated, so they must still appear as attribute values.
        try:
            prefs.set_request_prefs(lang="fr")
            fr_display = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
            fr_device = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DEVICE)
        finally:
            prefs.set_request_prefs(lang="en")
        for french_text in ("Blanc", "Piste 3 (07/25)", "Cadre avion"):
            if french_text not in fr_display:
                return False, "expected the French %r in the French Display render" % (french_text,)
        if "Cadre avion" not in fr_device:
            return False, "expected the French screen label in the French Device render"
        for english_text in ("Runway 3 (07/25)",):
            if english_text in fr_display:
                return False, "expected %r to be absent from the French Display render" % (english_text,)
        if 'value="white"' not in fr_display or 'value="3"' not in fr_display:
            return False, "expected the theme/runway ids themselves to stay untranslated attribute values"
        return True, ""
    check(
        "a French Display render translates the default theme name ('White' -> 'Blanc') and "
        "default runway label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), and both scopes' screen "
        "caption translates 'Plane frame' -> 'Cadre avion', while the theme/runway ids stay "
        "untranslated attribute values (Polish fix 5, D-05)",
        _french_display_and_device_render_translate_registry_labels)

    def _aspect_display_render_still_carries_every_pinned_english_string():
        # 30-05-PLAN.md Task 2 (CFG-85): replaces the retired
        # _english_display_render_still_carries_every_pinned_english_
        # string. The pinned set loses FRAME_COLOURS_CAPTION (deleted
        # outright by 30-04-PLAN.md Task 1) and gains ASPECT_HEADING;
        # every other member of the old set was kept unthinned at the
        # time — a pin that shrinks for convenience is not a pin.
        #
        # 30-06-PLAN.md Task 3 (CFG-85): the connection block's own
        # caption constant is now dropped too — it is deleted outright
        # by this plan's own Task 1 (the connection block folds into
        # the Calendar row, which has no caption of its own), so there
        # is no longer a value for this pin to assert;
        # CALENDAR_HOW_IT_WORKS_SUMMARY (a live calendar string,
        # unaffected by the merge) takes its place in the set so the
        # calendar's own copy stays represented here.
        rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
        for english_text in (
                config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
                config_page.DISPLAY_ON_HEADING, config_page.DISPLAY_PAGE_PURPOSE,
                layout.QUICK_ACTION_APPLIES_SENTENCE, config_page.ASPECT_HEADING,
                config_page.RUNWAY_SECTION_CAPTION, config_page.CALENDAR_HOW_IT_WORKS_SUMMARY):
            if escape_html(english_text) not in rendered:
                return False, "expected the English constant %r to still render verbatim" % (english_text,)
        return True, ""
    check(
        "an English (default) Display render still contains every pre-existing English string this "
        "file's own checks assert, updated for CFG-85's rebuild (both the former Frame colours "
        "card's and the calendar connection block's own caption constants dropped, ASPECT_HEADING "
        "gained, everything else kept) — t() never touches the default-language render (D-05, "
        "30-05-PLAN.md Task 2/30-06-PLAN.md Task 3, "
        "replacing the retired _english_display_render_still_carries_every_pinned_english_string)",
        _aspect_display_render_still_carries_every_pinned_english_string)

    def _device_render_carries_no_edit_artwork_markup_in_either_language():
        for lang in ("en", "fr"):
            try:
                prefs.set_request_prefs(lang=lang)
                rendered = config_page.render(
                    {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0},
                    scope=config_page.SCOPE_DEVICE)
            finally:
                prefs.set_request_prefs(lang="en")
            if "edit-artwork" in rendered:
                return False, "lang=%r: expected no edit-artwork markup on the Device page (D-36)" % (lang,)
            if "?edit=1" in rendered:
                return False, "lang=%r: expected no ?edit=1 link on the Device page (D-36)" % (lang,)
        return True, ""
    check(
        "the Device render contains no edit-artwork markup and no ?edit=1 link, in either language "
        "(D-36)",
        _device_render_carries_no_edit_artwork_markup_in_either_language)

    def _every_display_catalogue_key_is_a_key_of_the_merged_catalog():
        missing = [key for key in i18n_fr_display.CATALOG if key not in i18n_fr.CATALOG]
        if missing:
            return False, "expected every companion/i18n_fr/display.py key in the merged CATALOG, missing %r" % (missing,)
        return True, ""
    check(
        "every key of companion/i18n_fr/display.py is a key of the merged companion.i18n_fr.CATALOG "
        "(the auto-merge package actually picked this module up)",
        _every_display_catalogue_key_is_a_key_of_the_merged_catalog)

    def _submitted_scope_and_return_route_are_allowlisted():
        if config_page.submitted_scope({}) != config_page.SCOPE_ALL:
            return False, "expected a form without a scope field to resolve to the legacy all-scope"
        if config_page.submitted_scope({"scope": "device"}) != config_page.SCOPE_DEVICE:
            return False, "expected scope=device to resolve to SCOPE_DEVICE"
        if config_page.submitted_scope({"scope": "<script>"}) != config_page.SCOPE_ALL:
            return False, "expected a crafted scope to degrade to the all-scope, never be echoed"
        if config_page.submitted_return_route({"return_to": "/device"}) != "/device":
            return False, "expected /device to be an allowed return route"
        for hostile in ("https://evil.example", "//evil.example", "/settings", "/login", ""):
            if config_page.submitted_return_route({"return_to": hostile}) != "/display":
                return False, "expected %r to fall back to /display" % hostile
        return True, ""
    check(
        "submitted_scope() and submitted_return_route() are strict allowlists: unknown scopes degrade "
        "to the legacy all-scope and any non-member return_to falls back to /display",
        _submitted_scope_and_return_route_are_allowlisted)

    def _aspect_scoped_render_carries_hidden_fields_and_omits_other_groups():
        # 30-05-PLAN.md Task 2 (CFG-85): replaces the retired
        # _scoped_render_carries_hidden_fields_and_omits_other_groups.
        # Locates the rules row via its own data-usage attribute (never
        # the retired COLOUR_USAGE_PANEL_TARGET_ATTR); every other
        # assertion is otherwise unchanged from the retired check.
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        legacy = config_page.render(ctx)
        if 'name="scope" value="display"' not in display or 'name="return_to" value="/display"' not in display:
            return False, "expected the display scope's hidden scope/return_to fields"
        if 'name="scope" value="device"' not in device or 'name="return_to" value="/device"' not in device:
            return False, "expected the device scope's hidden scope/return_to fields"
        if 'name="scope"' in legacy:
            return False, "expected the legacy all-scope render to carry no scope field"
        if 'name="led_enabled"' in display:
            return False, "expected no LED group on the Display page"
        if 'name="tracked_runway"' not in display:
            return False, "expected the runway group to render on the Display page (D-10)"
        if 'name="tracked_runway"' in device:
            return False, "expected no runway group on the Device page (D-10)"
        if 'name="quiet_hours_enabled"' in device:
            return False, "expected no quiet-hours group on the Device page"
        if display.count('<h1 class="page-title">Display</h1>') != 1:
            return False, "expected the Display page title"
        if device.count('<h1 class="page-title">Device</h1>') != 1:
            return False, "expected the Device page title"
        if config_page.POLL_SECTION_HEADING in display:
            return False, "expected the manual-refresh section off the Display page"
        rules_row_marker = 'data-usage="%s"' % config_page.COLOUR_USAGE_RULES
        if rules_row_marker not in display:
            return False, "expected the rules row, inside the Aspect card, on the Display page (D-11)"
        if config_page.POLL_SECTION_HEADING not in device:
            return False, "expected the manual-refresh section on the Device page"
        if rules_row_marker in device:
            return False, "expected the rules row off the Device page (D-11)"
        hostile = config_page.render(ctx, scope="<script>")
        if 'name="scope"' in hostile or "&lt;script&gt;" in hostile:
            return False, "expected a hostile scope value to degrade to the legacy all-scope, never to be echoed"
        return True, ""
    check(
        "render(scope=display/device) carries the matching hidden fields and only its own groups, "
        "including locating the rules row (inside the Aspect card) by its own data-usage attribute; "
        "the legacy render(ctx) carries no scope field; a hostile scope never reaches the markup "
        "(30-05-PLAN.md Task 2, replacing the retired "
        "_scoped_render_carries_hidden_fields_and_omits_other_groups)",
        _aspect_scoped_render_carries_hidden_fields_and_omits_other_groups)

    def _handle_post_scope_carries_out_of_scope_checkboxes_forward():
        tmp = tempfile.mkdtemp(prefix="skypane-config-scope-")
        try:
            device_config.save_device_config(
                tmp, led_enabled=True, display_enabled=True, quiet_hours_enabled=True,
                theme="white", tracked_runway="3")
            # Display-page save: no LED field on the page -> LED stays True.
            key = config_page.handle_post(
                {"scope": "display", "theme": "black", "display_enabled": "on",
                 "quiet_hours_enabled": "on"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the display-page save, got %r" % key
            cfg = device_config.load_device_config(tmp)
            if cfg["led_enabled"] is not True or cfg["theme"] != "black":
                return False, "expected led_enabled carried forward and theme persisted, got %r" % (cfg,)
            # Device-page save: no display/quiet fields -> both stay True.
            # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25):
            # RETARGETED IN PLACE. This clause used to read "its own
            # absent LED box -> False", which was the correct reading
            # while the Device page still rendered an led_enabled
            # checkbox. It does not any more — the LED's control is a
            # role="switch" posting to /quick/led — so an absent
            # led_enabled here means the same thing display_enabled's
            # absence has meant since 22-05: leave it alone. The LED is
            # seeded True above and must still be True after a Device
            # save that never mentions it; the pre-23-07 handler would
            # have switched the physical LED off on this exact call.
            key = config_page.handle_post(
                {"scope": "device", "tracked_runway": "06-24"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the device-page save, got %r" % key
            cfg = device_config.load_device_config(tmp)
            if cfg["display_enabled"] is not True or cfg["quiet_hours_enabled"] is not True:
                return False, "expected display/quiet-hours carried forward on a device-page save, got %r" % (cfg,)
            if cfg["led_enabled"] is not True or cfg["tracked_runway"] != "06-24":
                return False, (
                    "expected a Device save that names no led_enabled to LEAVE it True and to "
                    "persist its own runway, got %r" % (cfg,))
            # And the explicit value is still honoured, which is what
            # makes the clause above a statement about ABSENCE rather
            # than about led_enabled having stopped being writable here.
            key = config_page.handle_post(
                {"scope": "device", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                {"state_dir": tmp})
            if key != config_page.FLASH_SAVED or device_config.load_device_config(
                    tmp)["led_enabled"] is not True:
                return False, "expected an explicit led_enabled value to still be honoured"
            # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
            # Display's everyday_groups this phase — a device-page
            # submission now ignores even a stray calendar_disconnect
            # field (its own scope no longer renders the Calendar group
            # at all), while a display-page submission's calendar
            # fields are live, resolving per submitted_calendar_signal()'s
            # own per-field gates. Retargeted in place from the exact
            # inverse (pre-phase, Calendar was Device-only).
            if config_page.submitted_calendar_signal({"scope": "device"}) != config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD:
                return False, "expected a device-page submission without calendar fields to carry the calendar forward"
            if config_page.submitted_calendar_signal({"scope": "device", "calendar_disconnect": "on"}) != config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD:
                return False, "expected a device-page submission to ignore a stray calendar_disconnect field (D-11)"
            if config_page.submitted_calendar_signal({"scope": "display", "calendar_disconnect": "on"}) != config_page.CALENDAR_URL_SIGNAL_CLEAR:
                return False, "expected a display-page submission's calendar_disconnect field to resolve clear now that Calendar renders there (D-11)"
            # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1, T-22-16): inverted from
            # the pre-22-05 "the legacy unscoped body keeps its
            # absent-means-False contract" — display_enabled and
            # quiet_hours_enabled now resolve absent to "leave unchanged"
            # UNCONDITIONALLY, including on this legacy unscoped
            # SCOPE_ALL path, which is precisely the regression this
            # plan exists to close: before this fix, this exact call
            # would have silently switched the screen back off.
            key = config_page.handle_post({"theme": "white"}, {"state_dir": tmp})
            cfg = device_config.load_device_config(tmp)
            if key != config_page.FLASH_SAVED or cfg["display_enabled"] is not True:
                return False, (
                    "expected the legacy unscoped save to LEAVE display_enabled unchanged (True), "
                    "got %r" % (cfg["display_enabled"],))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "handle_post() treats a checkbox absent from an out-of-scope group as 'leave unchanged' (a "
        "Display save never flips the LED, a Device save never flips the screen or quiet hours), "
        "leaves display_enabled/quiet_hours_enabled/led_enabled unchanged even in-scope and on the "
        "legacy unscoped form while still honouring an explicit value, and a scoped submission "
        "without the Calendar group always carries the calendar forward (D-12.1, 22-05-PLAN.md "
        "Task 1; the led_enabled half retargeted in place from absent-means-False by "
        "23-07-PLAN.md Task 2)",
        _handle_post_scope_carries_out_of_scope_checkboxes_forward)

    # --- 19-12-PLAN.md Task 2 (D-23/D-22): the conditional screen selector
    # and the Device-page Edit artwork link -------------------------------

    def _screen_selector_empty_for_the_real_single_member_registry():
        html = config_page._screen_selector_html("plane-frame")
        if html != "":
            return False, "expected the empty string for today's single-member registry, got %r" % (html,)
        return True, ""
    check(
        "_screen_selector_html() returns the empty string for the real single-member screens registry",
        _screen_selector_empty_for_the_real_single_member_registry)

    def _screen_selector_renders_for_a_multi_member_registry():
        from companion import screens
        saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
        try:
            screens.SCREEN_TYPES["rer-board"] = {
                "label": "RER board", "description": "d",
                "everyday_groups": (), "advanced_groups": (),
                "has_colour_rules": False, "has_manual_poll": False,
            }
            screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
            html = config_page._screen_selector_html("plane-frame")
            if '<select name="screen_id"' not in html:
                return False, "expected a <select name=\"screen_id\"> once a second screen type is registered"
            if html.count("<option") != 2:
                return False, "expected exactly one <option> per registered screen type, got %r" % (html,)
            if 'value="plane-frame" selected' not in html:
                return False, "expected the current screen id's option to carry the selected attribute"
            if 'value="rer-board" selected' in html:
                return False, "expected only the current screen id's option to carry selected"
            if "<label" not in html or 'for="screen-id-selector"' not in html:
                return False, "expected a <label for=...> supplying the control's accessible name"
            return True, ""
        finally:
            screens.SCREEN_TYPES.clear()
            screens.SCREEN_TYPES.update(saved_types)
            screens.SCREEN_IDS = saved_ids
    check(
        "_screen_selector_html() emits exactly one <select name=\"screen_id\"> with one <option> per "
        "registered screen type, the current one selected, and a non-empty accessible name once a "
        "second screen type is registered",
        _screen_selector_renders_for_a_multi_member_registry)

    def _render_carries_no_screen_selector_today():
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        if '<select name="screen_id"' in display or '<select name="screen_id"' in device:
            return False, "expected no screen selector with today's single-member registry"
        return True, ""
    check(
        "render() at Display and Device scope contains no <select name=\"screen_id\"> today (a "
        "single-member registry has no real choice to offer)",
        _render_carries_no_screen_selector_today)

    def _handle_post_rejects_a_crafted_screen_id():
        tmp = tempfile.mkdtemp(prefix="skypane-config-screen-id-")
        try:
            device_config.save_device_config(tmp, theme="white")
            errors = {}
            key = config_page.handle_post(
                {"theme": "black", "screen_id": "not-a-real-screen"}, {"state_dir": tmp}, errors=errors)
            if key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted screen_id, got %r" % (key,)
            if "screen_id" not in errors:
                return False, "expected a field error noted for screen_id"
            cfg = device_config.load_device_config(tmp)
            if cfg["theme"] != "white":
                return False, "expected the whole save rejected — theme must not have changed to 'black'"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "handle_post() rejects a crafted screen_id with FLASH_SAVE_FAILED, notes a field error, and "
        "writes nothing (all-or-nothing)",
        _handle_post_rejects_a_crafted_screen_id)

    def _valid_screen_id_round_trips():
        tmp = tempfile.mkdtemp(prefix="skypane-config-screen-id-")
        try:
            key = config_page.handle_post({"screen_id": "plane-frame"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for a valid screen_id, got %r" % (key,)
            cfg = device_config.load_device_config(tmp)
            if cfg["screen_id"] != "plane-frame":
                return False, "expected screen_id='plane-frame' to round-trip, got %r" % (cfg["screen_id"],)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a valid screen_id round-trips through save_device_config()",
        _valid_screen_id_round_trips)

    def _screen_selector_renders_the_field_error_message():
        # WR-01 (19-REVIEW.md): _screen_selector_html() is the only
        # render call site for screen_id and, unlike every sibling field
        # this plan touches, never rendered its own _field_error_html()
        # message. Only reachable through a multi-member registry, same
        # as the sibling checks above.
        from companion import screens
        saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
        try:
            screens.SCREEN_TYPES["rer-board"] = {
                "label": "RER board", "description": "d",
                "everyday_groups": (), "advanced_groups": (),
                "has_colour_rules": False, "has_manual_poll": False,
            }
            screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
            errors = {"screen_id": config_page.ERROR_INVALID_CHOICE}
            html_out = config_page._screen_selector_html("plane-frame", errors=errors)
            expected = escape_html(config_page.ERROR_INVALID_CHOICE)
            if html_out.count(expected) != 1:
                return False, (
                    "expected the screen_id field-error message to appear exactly once, got %r"
                    % (html_out,))
            return True, ""
        finally:
            screens.SCREEN_TYPES.clear()
            screens.SCREEN_TYPES.update(saved_types)
            screens.SCREEN_IDS = saved_ids
    check(
        "_screen_selector_html() renders the screen_id field-level error message exactly once when "
        "errors carries one",
        _screen_selector_renders_the_field_error_message)

    def _neither_scope_renders_an_edit_artwork_link():
        # 20-07-PLAN.md Task 3 (D-36): the Device page's "Edit artwork"
        # link is deleted outright — retargeted in place from "the
        # Device scope renders exactly one... Display renders none" to
        # its own inverse, now that neither scope renders it at all.
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        href_fragment = "/airlines?edit=1"
        if href_fragment in display:
            return False, "expected no Edit-artwork link on the Display page"
        if href_fragment in device:
            return False, "expected no Edit-artwork link on the Device page (D-36)"
        if "edit-artwork" in display or "edit-artwork" in device:
            return False, "expected no edit-artwork markup on either scope (D-36)"
        if "_edit_artwork_link_html" in dir(config_page):
            return False, "expected _edit_artwork_link_html() to be deleted outright (D-36)"
        return True, ""
    check(
        "neither the Display nor the Device scope renders an Edit-artwork link or markup any more — "
        "the link and its builder are deleted outright (D-36)",
        _neither_scope_renders_an_edit_artwork_link)

    # --- 19-12-PLAN.md Task 3 (D-13/S-02): "next wake ≈ HH:MM" caption
    # suffixes on Display/Device -------------------------------------------

    def _with_next_wake_helper_contract():
        if config_page._with_next_wake("caption.", None) != "caption.":
            return False, "expected the caption unchanged for a falsy next_wake_clock"
        if config_page._with_next_wake("caption.", "") != "caption.":
            return False, "expected the caption unchanged for an empty-string next_wake_clock"
        got = config_page._with_next_wake("caption.", "14:10")
        if got != "caption. (next wake ≈ 14:10)":
            return False, "expected the suffix appended when next_wake_clock is known, got %r" % (got,)
        return True, ""
    check(
        "_with_next_wake() returns the caption byte-identical for a falsy clock and appends "
        "'(next wake ≈ HH:MM)' when the clock is known",
        _with_next_wake_helper_contract)

    def _affected_captions_gain_the_suffix_only_when_known():
        known_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        unknown_ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        known_display = config_page.render(known_ctx, scope=config_page.SCOPE_DISPLAY)
        known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
        unknown_display = config_page.render(unknown_ctx, scope=config_page.SCOPE_DISPLAY)
        unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
        # 21-05-PLAN.md Task 1 (D-06): THEME_SECTION_CAPTION is retired
        # along with theme_fieldset() — its replacement, the Frame
        # colours card's own FRAME_COLOURS_CAPTION, is a fixed, complete,
        # locked sentence (21-UI-SPEC.md §D) that never gains this
        # suffix, so it is deliberately NOT added to this list.
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): QUIET_HOURS_SECTION_
        # CAPTION is ALSO removed from this list — it no longer ends on
        # the generic "applies on the next scheduled poll" clause this
        # suffix mechanism augments; Task 2 gives it its own one computed
        # delay sentence (companion/frame_state.py) instead, pinned by
        # its own dedicated check below.
        for caption in (
                config_page.RUNWAY_SECTION_CAPTION,
                config_page.LED_SECTION_CAPTION,
                config_page.WAKE_INTERVAL_SECTION_CAPTION):
            # escape_html() is what the render pipeline actually applies —
            # several of these captions carry an apostrophe (e.g. "the
            # device's"), so the RAW constant never appears verbatim in the
            # rendered HTML; every comparison below must go through the
            # same escaping the render call site itself uses.
            escaped_caption = escape_html(caption)
            escaped_suffix = config_page.NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % "14:10"
            if (escaped_caption + escaped_suffix) not in known_display and (escaped_caption + escaped_suffix) not in known_device:
                return False, "expected %r to gain the suffix when the next-wake value is known" % (caption,)
            if escaped_caption not in (unknown_display + unknown_device):
                return False, "expected %r to render byte-identical to its own constant when unknown" % (caption,)
            if (escaped_caption + " (next wake") in (unknown_display + unknown_device):
                return False, "expected %r to carry no suffix when the next-wake value is unknown" % (caption,)
        return True, ""
    check(
        "each of Runway/LED/Wake-interval's own caption gains the '(next wake ≈ "
        "HH:MM)' suffix when the value is known, and is byte-identical to its own constant when it "
        "is not (D-13; narrowed by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/"
        "theme_fieldset() are retired, and by 22-05-PLAN.md Task 1 X1/D-04/D-12.1 once Quiet hours' "
        "own caption moves to its own computed delay sentence instead — the Frame colours card's own "
        "caption never gains this suffix either)",
        _affected_captions_gain_the_suffix_only_when_known)

    def _device_header_shows_next_wake_line_when_known():
        known_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        unknown_ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
        if "Next wake" not in known_device or "≈ 14:10" not in known_device:
            return False, "expected the Device header to carry a Next wake ≈ HH:MM line when known"
        unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
        if "Next wake" in unknown_device:
            return False, "expected no Next wake line in the Device header when the value is unknown"
        return True, ""
    check(
        "the Device page header carries a 'Next wake ≈ HH:MM' line when the value is known and "
        "none at all when it is not (D-13's 'Home and Device show' wording)",
        _device_header_shows_next_wake_line_when_known)

    # ==================================================================
    # 22-05-PLAN.md Task 2 (D-04): the one computed delay sentence, in
    # its three branches, for the Quiet hours caption AND the post-save
    # flash — pinned against the SAME frame_state.py source of truth the
    # Frame strip itself reads (22-04-PLAN.md).
    #
    # 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: RETARGETED, all three.
    # quiet_hours_group() no longer appends the computed delay sentence
    # to its own caption at all — that property is gone, not merely
    # relocated inside this card. What survives, and what these three
    # checks now assert instead: (a) the delay sentence still renders,
    # once per branch, inside the Frame strip's own markup slice
    # (proven by locating that slice the same way
    # `_display_render_has_exactly_one_quick_action_pair_inside_the_strip`
    # already does, above), (b) the Quiet hours card's OWN caption
    # element carries NO delay sentence at all, in every branch, and
    # (c) the post-save flash text is untouched by this plan (a
    # different code path, companion/app.py's _resolve_flash_text(),
    # unaffected by quiet_hours_group()'s own signature change).
    # ==================================================================

    def _quiet_hours_caption_and_flash_agree_on_the_due_branch():
        ctx = {
            "device_config": {"wake_interval_s": 900, "quiet_hours_enabled": False},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_delay_fragment = escape_html("Applies at the next wake, around 14:10.")
        strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
        strip_end = display.index('<form class="config-form"', strip_start)
        if display.count(expected_delay_fragment) != 2:
            return False, (
                "expected the DUE delay sentence to appear exactly twice (once per Frame-strip "
                "switch cell), got %d in %r" % (display.count(expected_delay_fragment), display))
        if expected_delay_fragment not in display[strip_start:strip_end]:
            return False, "expected the DUE delay sentence inside the Frame strip's own slice"
        caption = re.search(
            r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
            % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
        if not caption:
            return False, "the Quiet hours card's own caption is gone"
        if expected_delay_fragment in caption.group(1):
            return False, (
                "expected the Quiet hours card's OWN caption to carry NO delay sentence any "
                "more (CFG-79) — found it in %r" % (caption.group(1),))
        flash = companion_app._resolve_flash_text(
            companion_app.FLASH_KEY_SAVED, "/tmp",
            last_checkin_ts=ctx["last_checkin_ts"], device_cfg=ctx["device_config"])
        if flash != "Saved — applies at the next wake, around 14:10.":
            return False, "expected the DUE flash text, got %r" % (flash,)
        return True, ""
    check(
        "with a due result, the Frame strip carries the DUE delay sentence exactly twice (once per "
        "switch cell), the Quiet hours card's own caption carries NO delay sentence any more "
        "(29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the DUE delay "
        "sentence naming the same computed time, unaffected by the caption change (D-04)",
        _quiet_hours_caption_and_flash_agree_on_the_due_branch)

    def _quiet_hours_caption_and_flash_agree_on_the_held_branch():
        # The nightly regression fixture (22-UI-SPEC.md §3.3 binding rule
        # 6, 22-02-PLAN.md Task 2's own pinned example): quiet hours
        # 23:00-07:00 Europe/Paris, last check-in 22:58, clock 02:00 the
        # next morning (a non-DST January date) — held, never late.
        device_cfg = {
            "wake_interval_s": 900, "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        ctx = {
            "device_config": device_cfg,
            "last_checkin_ts": "2026-01-15T22:58:00+01:00", "now": "2026-01-16T02:00:00+01:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_delay_fragment = escape_html("Applies when quiet hours end, around 07:00.")
        strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
        strip_end = display.index('<form class="config-form"', strip_start)
        if display.count(expected_delay_fragment) != 2:
            return False, (
                "expected the HELD delay sentence to appear exactly twice (once per Frame-strip "
                "switch cell), got %d in %r" % (display.count(expected_delay_fragment), display))
        if expected_delay_fragment not in display[strip_start:strip_end]:
            return False, "expected the HELD delay sentence inside the Frame strip's own slice"
        caption = re.search(
            r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
            % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
        if not caption:
            return False, "the Quiet hours card's own caption is gone"
        if expected_delay_fragment in caption.group(1):
            return False, (
                "expected the Quiet hours card's OWN caption to carry NO delay sentence any "
                "more (CFG-79) — found it in %r" % (caption.group(1),))
        flash = companion_app._resolve_flash_text(
            companion_app.FLASH_KEY_SAVED, "/tmp",
            last_checkin_ts=ctx["last_checkin_ts"], device_cfg=device_cfg)
        if flash != "Saved — applies when quiet hours end, around 07:00.":
            return False, "expected the HELD flash text, got %r" % (flash,)
        return True, ""
    check(
        "with a held result (the nightly regression fixture), the Frame strip carries the HELD "
        "delay sentence exactly twice (once per switch cell), the Quiet hours card's own caption "
        "carries NO delay sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save "
        "flash still reads the HELD delay sentence naming the window's own end, never the generic "
        "due wording (D-04, 22-UI-SPEC.md §3.3 binding rule 6)",
        _quiet_hours_caption_and_flash_agree_on_the_held_branch)

    def _quiet_hours_caption_and_flash_agree_on_the_unknown_branch():
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_delay_fragment = escape_html("Applies the next time the frame wakes up.")
        strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
        strip_end = display.index('<form class="config-form"', strip_start)
        if display.count(expected_delay_fragment) != 2:
            return False, (
                "expected the UNKNOWN delay sentence to appear exactly twice (once per "
                "Frame-strip switch cell), got %d in %r"
                % (display.count(expected_delay_fragment), display))
        if expected_delay_fragment not in display[strip_start:strip_end]:
            return False, "expected the UNKNOWN delay sentence inside the Frame strip's own slice"
        caption = re.search(
            r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
            % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
        if not caption:
            return False, "the Quiet hours card's own caption is gone"
        if expected_delay_fragment in caption.group(1):
            return False, (
                "expected the Quiet hours card's OWN caption to carry NO delay sentence any "
                "more (CFG-79) — found it in %r" % (caption.group(1),))
        flash = companion_app._resolve_flash_text(companion_app.FLASH_KEY_SAVED, "/tmp")
        if flash != "Saved — applies the next time the frame wakes up.":
            return False, "expected the UNKNOWN flash text, got %r" % (flash,)
        return True, ""
    check(
        "with no check-in at all, the Frame strip carries the UNKNOWN delay sentence exactly "
        "twice (once per switch cell), the Quiet hours card's own caption carries NO delay "
        "sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads "
        "the UNKNOWN delay sentence, which names no time (D-04)",
        _quiet_hours_caption_and_flash_agree_on_the_unknown_branch)

    def _retired_delay_wordings_appear_nowhere_under_companion_or_server():
        # The three literal wordings this plan retires — deliberately NOT
        # typed as a single searchable constant here, so this check's own
        # source is a real, independent occurrence check, not a
        # tautology. Excludes this repository's own test_*.py harnesses
        # (which necessarily name these exact strings, including this
        # very check, to prove their absence) and, deliberately, includes
        # companion/frame_state.py's own source (that module documents
        # the retirement in prose without retyping any of the three
        # literals — see its own comment).
        retired = (
            "Takes effect within about 5 minutes",
            "Applies on the next scheduled poll, which may now be hours away",
            "Saved — will apply on the frame's next scheduled refresh",
        )
        for root in ("companion", "server"):
            for dirpath, _dirnames, filenames in os.walk(root):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    if filename.startswith("test_"):
                        continue
                    path = os.path.join(dirpath, filename)
                    with open(path, encoding="utf-8") as fh:
                        source = fh.read()
                    for wording in retired:
                        if wording in source:
                            return False, "found retired wording %r in %s" % (wording, path)
        return True, ""
    check(
        "none of the three retired delay wordings ('Takes effect within about 5 minutes', "
        "'Applies on the next scheduled poll, which may now be hours away', 'Saved — will apply "
        "on the frame's next scheduled refresh') appears anywhere under companion/ or server/, "
        "excluding this repository's own test_*.py harnesses (D-04)",
        _retired_delay_wordings_appear_nowhere_under_companion_or_server)

    # ==================================================================
    # 29-05-PLAN.md Task 3 (CFG-79), 2026-09-22: the settings-pages
    # editorial floor — render-level, both pages, both languages. The
    # ONE new check in this section replaces a source-level scan with a
    # measurement of what `config_page.render()` actually produces,
    # matching CFG-79's own "enforced by a harness check measuring
    # RENDERED caption length" requirement text.
    # ==================================================================

    # A realistic, worst-case-length fixture: a real last_checkin_ts/now
    # pair so every "(next wake ≈ HH:MM)" suffix (`_with_next_wake()`)
    # actually renders on Runway/LED/Wake-interval — the LONGEST form
    # each of those captions ever reaches, which is the form this floor
    # must hold against, not the shorter unknown-value fallback.
    _FLOOR_CTX = {
        "device_config": {
            "wake_interval_s": 900, "led_enabled": True,
            "quiet_hours_enabled": False,
        },
        "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
    }
    # Minimums pinned a little below the observed figures — re-derived
    # by RUNNING this exact fixture through this exact selector,
    # 30-05-PLAN.md Task 3 (CFG-85): the old 16-measured-on-/display
    # baseline dropped to 12 once FRAME_COLOURS_CAPTION (the caption
    # paragraph) and the old per-grid swatch legends (three of them —
    # the departures/arrivals/calendar rows now use _palette_grid_html(),
    # which renders no legend at all) both disappeared from the Aspect
    # card's rebuild; /device is untouched by CFG-85 and stays at its
    # own previously-observed 8. Enough margin for an unrelated future
    # caption to be added or removed without retuning this number, not
    # so much margin that a badly narrowed selector could still clear it.
    _FLOOR_MIN_MEASURED = {"display": 10, "device": 6}
    # /display carries exactly the four Aspect exemptions (Phase 30's
    # own card); /device carries none of them (Aspect is Display-only).
    _FLOOR_EXPECTED_SKIPS = {"display": len(config_page.ASPECT_CAPTION_EXEMPTIONS), "device": 0}

    def _caption_word_count_text(fragment):
        """THE ONE COUNTING RULE this whole floor applies, stated once
        here rather than left to be inferred from arithmetic: strip
        tags, unescape HTML entities (so `&#x27;` counts as the one
        character it renders, not five), collapse internal whitespace,
        then strip a single leading em dash and its following space —
        `layout.section_intro_html()`'s own intro sentences (rendering
        DISPLAY_LOOK_INTRO/DISPLAY_WATCHES_INTRO/DISPLAY_ON_INTRO/
        DEVICE_WAKES_INTRO/DEVICE_TELLS_INTRO/DEVICE_POLL_INTRO)
        legitimately open with "— ", and that leading mark is not a
        WORD by any reading of "at most 12 words" — matching
        RESEARCH.md's own measurement method exactly, so its offender
        table's word counts are directly comparable to this check's.
        """
        stripped = re.sub(r"<[^>]*>", "", fragment)
        text = html.unescape(stripped).strip()
        if text.startswith("— "):
            text = text[2:]
        return re.sub(r"\s+", " ", text).strip()

    def _measured_section_captions(rendered):
        """Every `<p class="...">...</p>` element whose class list
        contains the token "section-caption" and NO token beyond
        "text-label"/"section-caption" themselves — a plain editorial
        caption, never a live data readout.

        THE ONE EXCLUSION THIS RULE MAKES ON THESE TWO PAGES, and the
        reason it is a selector decision rather than a THIRD member of
        ASPECT_CAPTION_EXEMPTIONS: `wake_gauges_html()`'s two elements
        additionally carry a `wake-gauge` class token. Both are
        COMPUTED QUANTITIES with a `data-value-readout` JS-substitution
        hook, re-derived live from the slider's own position — not
        descriptive prose about what a control does, the same
        "status/error message, not a caption" distinction RESEARCH.md
        itself draws for `MANUAL_SUPERSEDED_NOTE_TEMPLATE` elsewhere in
        this app. `ASPECT_CAPTION_EXEMPTIONS` is reserved for Phase
        30's own Aspect-section copy specifically (CFG-79's own
        exemption, argued in that tuple's comment) — a structurally
        different kind of element does not belong in that same list,
        and folding it in would let the exemption's own reachability
        assertion below (exactly 4 skips on /display, exactly 0 on
        /device) silently stop proving what it claims to.

        Returns a list of `(start, end, raw_fragment)` triples — the
        MATCH's own span, not just its text, so a caller can locate an
        element relative to another slice (the Frame strip's own
        markup) without a second pass over the document.
        """
        out = []
        for m in re.finditer(r'<p\s+class="([^"]*)"[^>]*>(.*?)</p>', rendered, re.DOTALL):
            classes = m.group(1).split()
            if "section-caption" not in classes:
                continue
            if set(classes) - {"text-label", "section-caption"}:
                continue
            out.append((m.start(), m.end(), m.group(2)))
        return out

    def _settings_pages_editorial_floor_render_level_both_languages():
        exempt_by_lang = {
            lang: {
                _caption_word_count_text(i18n.t_lang(text, lang))
                for text in config_page.ASPECT_CAPTION_EXEMPTIONS
            }
            for lang in ("en", "fr")
        }
        # THE ONCE-PER-PAGE RELATIONSHIP's own source constants — never a
        # hand-typed English phrase. frame_state.DELAY_DUE/DELAY_HELD
        # carry a "%s" clock placeholder; DELAY_UNKNOWN does not.
        apply_timing_templates = (
            frame_state.DELAY_DUE, frame_state.DELAY_HELD, frame_state.DELAY_UNKNOWN)

        any_inside_strip = False
        for page_name, scope in (
                ("display", config_page.SCOPE_DISPLAY), ("device", config_page.SCOPE_DEVICE)):
            for lang in ("en", "fr"):
                prefs.set_request_prefs(lang=lang)
                try:
                    rendered = config_page.render(_FLOOR_CTX, scope=scope)
                finally:
                    prefs.set_request_prefs(lang="en")

                captions = _measured_section_captions(rendered)
                if len(captions) < _FLOOR_MIN_MEASURED[page_name]:
                    return False, (
                        "%s/%s: only %d .section-caption element(s) were measured, expected at "
                        "least %d — a narrowed selector could pass over an empty set"
                        % (page_name, lang, len(captions), _FLOOR_MIN_MEASURED[page_name]))

                skip_count = 0
                for _start, _end, fragment in captions:
                    text = _caption_word_count_text(fragment)
                    if text in exempt_by_lang[lang]:
                        skip_count += 1
                        continue
                    words = text.split()
                    if len(words) > 12:
                        return False, (
                            "%s/%s: a non-exempt section-caption renders %d word(s) (max 12): %r"
                            % (page_name, lang, len(words), text))
                if skip_count != _FLOOR_EXPECTED_SKIPS[page_name]:
                    return False, (
                        "%s/%s: expected exactly %d Aspect-exemption skip(s), got %d — either "
                        "the exemption is unreachable from this page or it silently swallowed a "
                        "caption it should not have"
                        % (page_name, lang, _FLOOR_EXPECTED_SKIPS[page_name], skip_count))

                # THE ONCE-PER-PAGE RELATIONSHIP, checked as a REGION
                # invariant rather than a literal single-element count.
                # The Frame strip's own two switch cells (Screen, Quiet
                # hours) share ONE computed sentence by design
                # (companion/layout.py's frame_strip_html(), unmodified
                # by this plan — git diff --stat companion/layout.py is
                # empty) — so up to two elements legitimately carry it
                # INSIDE that one region on /display. What CFG-79
                # actually forbids, and what this assertion actually
                # proves, is the sentence appearing in any element
                # OUTSIDE the Frame strip's own slice — exactly the
                # property Task 2 of this plan established for the
                # Quiet hours card, and exactly what Mutation C (see
                # SUMMARY) re-breaks to prove this assertion is live.
                strip_start = rendered.find(
                    '<div class="frame-strip stat-tile stat-tile--accent"')
                strip_end = (
                    rendered.find('<form class="config-form"', strip_start)
                    if strip_start != -1 else -1)
                outside_matches = []
                for start, _end, fragment in captions:
                    text = _caption_word_count_text(fragment)
                    for template in apply_timing_templates:
                        translated = i18n.t_lang(template, lang)
                        if "%s" in translated:
                            pattern = re.escape(translated).replace(re.escape("%s"), r".+?")
                        else:
                            pattern = re.escape(translated)
                        if not re.search(pattern, text):
                            continue
                        if strip_start != -1 and strip_start <= start < strip_end:
                            any_inside_strip = True
                        else:
                            outside_matches.append(
                                "%s/%s at offset %d (%r): %r"
                                % (page_name, lang, start, text[:80], text))
                        break
                if outside_matches:
                    return False, (
                        "%s/%s: the apply-timing sentence rendered outside the Frame strip's own "
                        "slice — CFG-79 confines it to exactly one place per page: %s"
                        % (page_name, lang, "; ".join(outside_matches)))
        if not any_inside_strip:
            return False, (
                "the apply-timing relationship never matched INSIDE the Frame strip either — "
                "this assertion is vacuous unless it is proven to fire on the strip's own, "
                "untouched markup at least once")
        return True, ""
    check(
        "the settings-pages editorial floor, measured on the RENDERED page (never a source scan): "
        "every non-exempt .section-caption element on /display and /device is at most 12 "
        "whitespace-split words in both languages; ASPECT_CAPTION_EXEMPTIONS is skipped exactly "
        "4 times on /display and exactly 0 times on /device (proving the exemption reachable and "
        "not silently over-broad); and the apply-timing sentence — read from frame_state.py's own "
        "DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN constants — never renders outside the Frame strip's "
        "own markup slice, proven to actually fire inside it at least once so the assertion is "
        "not vacuous (CFG-79, 29-05-PLAN.md Task 3)",
        _settings_pages_editorial_floor_render_level_both_languages)

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
            #
            # 22-05-PLAN.md Task 2 (D-04): FLASH_MESSAGES[FLASH_KEY_SAVED]
            # is now a template ("Saved — %s"), never the whole fixed
            # sentence — the confirmation body actually served is what
            # companion_app._resolve_flash_text() resolves it to, given
            # the SAME facts (no check-in yet recorded on this harness's
            # own fresh state dir) the real request itself reads.
            confirmation = escape_html(
                companion_app._resolve_flash_text(
                    companion_app.FLASH_KEY_SAVED, harness.tmpdir,
                    last_checkin_ts=None, device_cfg={}))
            if confirmation.encode() not in body:
                return False, "expected D-07's exact confirmation copy in the response body"
            # 20-07-PLAN.md Task 1 (D-10): the runway group moved from
            # Device to Display this phase, so the newly-saved selection
            # is read back from there now (retargeted from DEVICE_ROUTE).
            _s, _h, body = http_request(
                base + companion_app.DISPLAY_ROUTE, cookie=session_cookie)
            # Polish fix 4 (D-14c): each runway radio now also carries an
            # explicit form="settings-form" attribute.
            if (b'value="06-24" class="visually-hidden" form="%s" checked'
                    % config_page.SETTINGS_FORM_ID.encode()) not in body:
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
            # Phase 18: a POST with no return_to field lands on the
            # Display page, the default return route.
            expected_location = "%s?flash=saved" % companion_app.DISPLAY_ROUTE
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
            # Seeded rather than assumed: this check is about an empty
            # body LEAVING the stored value alone, so it needs a known
            # starting value it can then read back, and the follow-up GET
            # below asserts the rendered control agrees with it.
            device_config.save_device_config(harness.tmpdir, led_enabled=False)
            led_before = False
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=b"")
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25):
            # RETARGETED IN PLACE from "persists led_enabled False". The
            # field's absence now means "leave unchanged", so what this
            # live round trip must show is that whatever was stored
            # BEFORE the empty POST is still stored after it.
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["led_enabled"] is not led_before:
                return False, (
                    "expected an empty-body POST to LEAVE the stored led_enabled %r unchanged, "
                    "got %r" % (led_before, on_disk["led_enabled"]))
            get_status, _get_headers, body = http_request(
                base + companion_app.DEVICE_ROUTE, cookie=session_cookie)
            if get_status != 200:
                return False, "expected 200 on the follow-up GET %s, got %d" % (
                    companion_app.DEVICE_ROUTE, get_status)
            if b'name="led_enabled" value="on" checked' in body:
                return False, "expected the LED checkbox to render unchecked after saving False"
            return True, ""
        check(
            "a live authenticated POST %s with an empty body 303-redirects to %s?flash=saved, "
            "LEAVES the stored led_enabled exactly as it was, and a follow-up GET renders the "
            "control in that same off state (retargeted in place from absent-means-False by "
            "23-07-PLAN.md Task 2)"
            % (config_page.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE),
            _settings_post_empty_body_persists_led_false_and_renders_unchecked)

        def _settings_form_raw_post_no_js_clears_and_sets_theme_arriving():
            # 15-VALIDATION.md row 11 (the Settings-form half this plan
            # owns): a raw, URL-encoded POST to the live SETTINGS_ROUTE -
            # no client script involved - once with a real theme_arriving
            # id, once with theme_arriving="" (the Frame colours card's
            # own leading "Same as departures" chip's real submitted
            # shape), proving the set/clear contract holds over the real
            # HTTP path, not just in-process. 21-05-PLAN.md Task 2
            # (D-09/R-07): retargeted from the retired arrivals-override
            # checkbox onto the new empty-string clear signal.
            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving": "black",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the set save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' after the set raw POST, got %r"
                    % (on_disk["theme_arriving"],))

            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving": "",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the clearing save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "expected theme_arriving None after the theme_arriving='' raw POST, got %r"
                    % (on_disk["theme_arriving"],))
            return True, ""
        check(
            "a raw, URL-encoded no-JS POST to SETTINGS_ROUTE sets theme_arriving to a real id and clears it "
            "back to None via theme_arriving='', over the real HTTP path (15-VALIDATION.md row 11, the "
            "Settings-form half; D-06/D-09, retargeted from the retired arrivals-override checkbox)",
            _settings_form_raw_post_no_js_clears_and_sets_theme_arriving)

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

    # ==================================================================
    # Section 3 (16-05-PLAN.md Task 3, T-16-SECRET; rewritten by phase 17
    # plan 02, D-03): a second, dedicated harness with a calendar
    # configured, proving the secret never reaches the SERVED HTTP bytes —
    # not just render()'s in-process return value (Section 1b's own check
    # above covers that half). A separate subprocess keeps this one
    # specific scenario isolated from every assertion the main Section 2
    # harness already covers, rather than for any environment-snapshot
    # reason — the secret now lives in this harness's own state directory
    # on disk, which the running companion process reads fresh on every
    # request (calendar_rules.configured_calendar_url()'s per-call,
    # nothing-cached contract), so it could equally be written before or
    # after the process starts.
    # ==================================================================

    calendar_token = "sk1-distinctive-token-2rv9"
    calendar_host = "private-crew-calendar.example.internal"
    calendar_path = "feeds/roster-export"
    calendar_query_param = "auth_token"
    calendar_url = "https://%s/%s?%s=%s" % (
        calendar_host, calendar_path, calendar_query_param, calendar_token)

    calendar_harness = Harness()
    assert calendar_rules.save_calendar_url(calendar_harness.tmpdir, calendar_url) is True
    try:
        calendar_harness.start()
        calendar_base = calendar_harness.base_url()
        calendar_cookie = _login(calendar_harness)

        def _calendar_secret_never_reaches_served_http_bytes():
            # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
            # Display this phase — retargeted from DEVICE_ROUTE.
            # 21-07-PLAN.md Task 2 (D-14/R-10): EXTENDED, not replaced —
            # the served bytes now legitimately carry the masked host +
            # "…" fragment (the whole point of D-14); the token, path,
            # query-parameter name and the whole raw URL still never do.
            status, _headers, body = http_request(
                calendar_base + companion_app.DISPLAY_ROUTE, cookie=calendar_cookie)
            if status != 200:
                return False, "expected 200 on the authenticated Display page, got %d" % status
            body_text = body.decode("utf-8", errors="replace")
            # 20-09-PLAN.md Task 1 (D-14b): the old one-piece "pending"
            # sentence is retired — a configured calendar with no sync
            # recorded yet now renders the bare "Connected" verdict.
            if config_page.CALENDAR_STATUS_CONNECTED_VERDICT not in body_text:
                return False, "expected the 'Connected' verdict (no sync recorded yet)"
            if escape_html("%s…" % calendar_host) not in body_text:
                return False, "expected the masked host + ellipsis fragment to be served once connected"
            for needle in (calendar_token, calendar_path, calendar_query_param, calendar_url):
                if needle in body_text:
                    return False, "expected %r never to appear in the served response body" % (needle,)
            return True, ""
        check(
            "with a calendar configured via its secret file to a URL carrying a distinctive token, a real "
            "authenticated HTTP GET of the Settings page serves the masked host + ellipsis fragment but "
            "never the token, the path segment, the query-parameter name, or the whole raw URL in the "
            "response body (T-16-SECRET, real HTTP round trip, extended by 21-07-PLAN.md Task 2 for the "
            "new masked-URL line, D-14/R-10)",
            _calendar_secret_never_reaches_served_http_bytes)

        def _calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing():
            # 21-07-PLAN.md Task 2 (D-14/R-10): a stored value that
            # cannot be parsed into a meaningful host must never crash
            # the page and must never render a fabricated placeholder —
            # the whole masked-URL <p> is simply omitted.
            for hostile in ("not a url", "", "javascript:alert(1)"):
                hostile_tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
                try:
                    assert calendar_rules.save_calendar_url(hostile_tmpdir, hostile) is not None
                    ctx = dict(
                        _CALENDAR_BASE_CTX, calendar_configured=True,
                        calendar_last_synced_at=None, state_dir=hostile_tmpdir)
                    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
                finally:
                    shutil.rmtree(hostile_tmpdir, ignore_errors=True)
                if "calendar-masked-url" in rendered:
                    return False, (
                        "hostile value %r: expected no calendar-masked-url line at all" % (hostile,))
            return True, ""
        check(
            "a hostile or unparseable stored calendar URL ('not a url', the empty string, a "
            "javascript: URI) renders no calendar-masked-url line at all and raises nothing (D-14/R-10, "
            "_masked_calendar_url()'s own fail-soft, never-fabricate contract)",
            _calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing)
    finally:
        calendar_harness.stop()
        calendar_harness.cleanup()

    # ==================================================================
    # 19-11-PLAN.md Task 3 (D-12/A-30): the two chip grids and the
    # runway row as named radiogroups, and every hint linked to its
    # control via aria-describedby - no dangling ARIA reference, no
    # empty aria-describedby, and hint+error ids coexisting in order.
    # ==================================================================

    _TASK3_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }

    def _display_scope_has_three_radiogroups_device_has_none():
        # 20-07-PLAN.md Task 1 (D-10): Runway moved from Device to
        # Display this phase — Display now carries Theme's two chip
        # grids PLUS the Runway row's own radiogroup (three), while
        # Device (LED, Wake interval only) carries none. Retargeted from
        # "Display >= 2, Device >= 1 (the Runway row)" in place.
        display_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        device_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        display_count = display_rendered.count('role="radiogroup"')
        if display_count < 3:
            return False, (
                "expected at least three role=\"radiogroup\" occurrences on the Display "
                "scope (Theme's two chip grids plus the Runway row), got %d" % display_count)
        device_count = device_rendered.count('role="radiogroup"')
        if device_count != 0:
            return False, (
                "expected no role=\"radiogroup\" occurrence on the Device scope "
                "(LED and Wake interval have no radio groups), got %d" % device_count)
        return True, ""
    check(
        "the Display scope renders at least three role=\"radiogroup\" elements (Theme's departures and "
        "arrivals chip grids, plus the Runway row) and the Device scope renders none (D-12/A-30, "
        "retargeted by 20-07-PLAN.md Task 1/D-10)",
        _display_scope_has_three_radiogroups_device_has_none)

    _ID_RE = re.compile(r'\bid="([^"]*)"')
    _LABELLEDBY_RE = re.compile(r'aria-labelledby="([^"]*)"')
    _DESCRIBEDBY_RE = re.compile(r'aria-describedby="([^"]*)"')

    def _every_aria_reference_resolves_and_none_is_empty():
        for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
            rendered = config_page.render(_TASK3_BASE_CTX, scope=scope)
            existing_ids = set(_ID_RE.findall(rendered))
            for value in _DESCRIBEDBY_RE.findall(rendered):
                if not value:
                    return False, "scope %r: expected no empty aria-describedby, found one" % (scope,)
                for token in value.split(" "):
                    if token not in existing_ids:
                        return False, (
                            "scope %r: aria-describedby token %r does not match any id "
                            "the same output emits" % (scope, token))
            for value in _LABELLEDBY_RE.findall(rendered):
                if not value:
                    return False, "scope %r: expected no empty aria-labelledby, found one" % (scope,)
                for token in value.split(" "):
                    if token not in existing_ids:
                        return False, (
                            "scope %r: aria-labelledby token %r does not match any id "
                            "the same output emits" % (scope, token))
        return True, ""
    check(
        "every aria-labelledby and aria-describedby value render() emits, at every scope, resolves to "
        "an id the same output actually carries, and no element emits an empty aria-describedby or "
        "aria-labelledby (D-12/A-30)",
        _every_aria_reference_resolves_and_none_is_empty)

    def _control_with_both_hint_and_error_carries_both_ids_in_order():
        rendered = config_page.render(
            _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE,
            errors={"led_enabled": "msg"}, submitted={})
        # 23-07-PLAN.md Task 2 (D2/CFG-36): retargeted in place from the
        # led_enabled CHECKBOX to the role="switch" that replaced it. The
        # contract is unchanged and now has a third id to keep in order:
        # the switch's own state span, then the group's caption (the hint
        # the checkbox carried through _field_error_attrs()'s hint_id),
        # then the error anchor — hint still before error, and none of
        # the three overwriting another.
        input_match = re.search(r'<button type="submit" class="switch"[^>]*>', rendered)
        if not input_match:
            return False, "expected the led_enabled switch to render"
        describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
        if not describedby_match:
            return False, "expected an aria-describedby on the errored led_enabled switch"
        ids = describedby_match.group(1).split(" ")
        if ids != [config_page.QUICK_LED_STATE_ID, config_page.LED_SECTION_CAPTION_ID,
                   "led-enabled-error"]:
            return False, (
                "expected the state id, then the hint id, then the error id, got %r" % (ids,))
        # And with no error the third id simply is not there — so the
        # clause above is about the ERROR rather than about a constant
        # three-id string.
        clean = config_page.render(
            _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE, errors={}, submitted={})
        clean_match = re.search(r'<button type="submit" class="switch"[^>]*>', clean)
        if not clean_match or "led-enabled-error" in clean_match.group(0):
            return False, (
                "expected no error id on the switch's aria-describedby when there is no error")
        return True, ""
    check(
        "a control carrying both a hint and an error (led_enabled's switch, rendered with an errors "
        "dict) has its state, hint and error ids in its aria-describedby, hint still before error, "
        "never one overwriting another, and no error id at all when there is no error (D-12/A-30; "
        "retargeted in place from the retired checkbox by 23-07-PLAN.md Task 2)",
        _control_with_both_hint_and_error_carries_both_ids_in_order)

    # ==================================================================
    # 20-11-PLAN.md Task 1 (D-26/D-28): the Notifications group — a
    # write-only topic URL, two checkboxes, no language selector.
    # ==================================================================

    def _notifications_group_status_row_configured_vs_not_and_write_only_url():
        rendered_unconfigured = config_page.render(
            {"device_config": {}, "poll_cooldown_remaining": 0}, scope=config_page.SCOPE_DEVICE)
        if config_page.NOTIFICATIONS_SECTION_HEADING not in rendered_unconfigured:
            return False, "expected the Notifications heading on the Device scope"
        if config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT not in rendered_unconfigured:
            return False, "expected the 'Not configured' verdict with no topic URL stored"
        if config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT in rendered_unconfigured:
            return False, "expected no 'Configured' verdict with no topic URL stored"

        seeded_url = "https://ntfy.sh/skypane-secret-token-xyz"
        rendered_configured = config_page.render(
            {
                "device_config": {
                    "notifications": {
                        "topic_url": seeded_url, "battery_low": True,
                        "frame_silent": False, "lang": "en"}},
                "poll_cooldown_remaining": 0,
            },
            scope=config_page.SCOPE_DEVICE)
        if config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT not in rendered_configured:
            return False, "expected the 'Configured' verdict with a topic URL stored"
        if config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT in rendered_configured:
            return False, "expected no 'Not configured' verdict with a topic URL stored"
        if seeded_url in rendered_configured or "secret-token-xyz" in rendered_configured:
            return False, "expected no substring of the stored topic URL anywhere in the rendered page"
        for rendered in (rendered_unconfigured, rendered_configured):
            match = re.search(r'<input[^>]*name="notifications_topic_url"[^>]*>', rendered)
            if not match:
                return False, "expected the notifications_topic_url input to render"
            if "value=" in match.group(0):
                return False, "expected no value attribute on the write-only topic-URL input"
        return True, ""
    check(
        "notifications_group()'s status row reads 'Not configured' with no URL stored and "
        "'Configured' with one, the topic-URL input never carries a value attribute in either "
        "state, and no substring of a seeded URL appears anywhere in the rendered page (T-20-12)",
        _notifications_group_status_row_configured_vs_not_and_write_only_url)

    def _notifications_checkboxes_reflect_stored_state():
        rendered = config_page.render(
            {
                "device_config": {
                    "notifications": {
                        "topic_url": "https://ntfy.sh/x", "battery_low": False,
                        "frame_silent": True, "lang": "fr"}},
                "poll_cooldown_remaining": 0,
            },
            scope=config_page.SCOPE_DEVICE)
        battery_match = re.search(
            r'<input type="checkbox" name="notifications_battery"[^>]*>', rendered)
        silent_match = re.search(
            r'<input type="checkbox" name="notifications_silent"[^>]*>', rendered)
        if not battery_match or not silent_match:
            return False, "expected both notifications checkboxes to render"
        if " checked" in battery_match.group(0):
            return False, "expected notifications_battery unchecked when stored False"
        if " checked" not in silent_match.group(0):
            return False, "expected notifications_silent checked when stored True"
        return True, ""
    check(
        "notifications_group()'s two checkboxes reflect the stored battery_low/frame_silent "
        "booleans",
        _notifications_checkboxes_reflect_stored_state)

    def _notifications_group_has_no_lang_selector():
        rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        if "notifications_lang" in rendered:
            return False, "expected no notifications_lang control anywhere on the page"
        return True, ""
    check(
        "the Device page contains no notifications_lang control anywhere (D-28: lang travels "
        "silently, never through a <select>)",
        _notifications_group_has_no_lang_selector)

    def _handle_post_notifications_round_trip_writes_lang_from_ctx():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir, "lang": "fr"}
            flash_key = config_page.handle_post(
                {
                    "scope": config_page.SCOPE_DEVICE,
                    "notifications_topic_url": "https://ntfy.sh/skypane-abc123",
                    "notifications_battery": config_page.NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
                    "notifications_silent": config_page.NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)["notifications"]
            expected = {
                "topic_url": "https://ntfy.sh/skypane-abc123",
                "battery_low": True, "frame_silent": True, "lang": "fr"}
            if on_disk != expected:
                return False, "expected %r, got %r" % (expected, on_disk)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() with scope=device, a topic URL and both checkboxes persists the whole "
        "notifications group and writes lang from ctx['lang'] (D-26/D-28)",
        _handle_post_notifications_round_trip_writes_lang_from_ctx)

    def _handle_post_empty_notifications_url_leaves_stored_url_intact():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            device_config.save_device_config(
                tmpdir, notifications={
                    "topic_url": "https://ntfy.sh/skypane-seeded",
                    "battery_low": True, "frame_silent": True, "lang": "en"})
            flash_key = config_page.handle_post(
                {"scope": config_page.SCOPE_DEVICE, "notifications_topic_url": ""}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)["notifications"]
            if on_disk["topic_url"] != "https://ntfy.sh/skypane-seeded":
                return False, (
                    "expected the stored URL to survive an empty submission, got %r"
                    % (on_disk["topic_url"],))
            if on_disk["battery_low"] is not False or on_disk["frame_silent"] is not False:
                return False, "expected both checkboxes to resolve absent-means-False"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() with an empty notifications_topic_url leaves the previously stored URL "
        "unchanged (D-26: empty means 'leave unchanged', never 'clear it')",
        _handle_post_empty_notifications_url_leaves_stored_url_intact)

    # ==================================================================
    # 20-11-PLAN.md Task 2 (D-22..D-24): the live theme preview above
    # the chip grid.
    # ==================================================================

    def _aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions():
        # 30-05-PLAN.md Task 2 (CFG-85): replaces the retired
        # _display_render_has_exactly_one_live_preview_figure_eager_
        # with_dimensions. The figure now wears aspect-card__preview
        # (was frame-colours__preview) — retargeted from the old class
        # attribute to the new one. Also asserts the figure's own index
        # precedes the first name="aspect-rows" row's — the preview is
        # ABOVE the rows (ROADMAP point 1), a relationship a
        # class-presence check alone would miss.
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
            scope=config_page.SCOPE_DISPLAY)
        figure_needle = 'class="theme-live-preview aspect-card__preview"'
        if rendered.count(figure_needle) != 1:
            return False, (
                "expected exactly one .theme-live-preview.aspect-card__preview figure, got %d"
                % rendered.count(figure_needle))
        figure_pos = rendered.index(figure_needle)
        first_row_pos = rendered.index('name="%s"' % config_page.ASPECT_ROWS_GROUP_NAME)
        if not (figure_pos < first_row_pos):
            return False, "expected the live preview figure ABOVE the first accordion row"
        match = re.search(r'<img class="theme-live-preview__image"[^>]*>', rendered)
        if not match:
            return False, "expected the live preview's own <img> element"
        tag = match.group(0)
        if 'src="%sblue.png?live=1"' % config_page.THEME_PREVIEW_ROUTE_PREFIX not in tag:
            return False, "expected the live preview's src to end in the saved theme's ?live=1 URL"
        if 'loading="eager"' not in tag:
            return False, 'expected the live preview\'s own <img> to carry loading="eager"'
        if 'width="%d"' % config_page.THEME_LIVE_PREVIEW_WIDTH not in tag:
            return False, "expected an explicit width attribute"
        if 'height="%d"' % config_page.THEME_LIVE_PREVIEW_HEIGHT not in tag:
            return False, "expected an explicit height attribute"
        return True, ""
    check(
        "a Display render contains exactly one .theme-live-preview.aspect-card__preview figure whose "
        "<img> src ends in the saved theme's ?live=1 URL, carries loading=\"eager\" and explicit "
        "width/height, positioned ABOVE the first accordion row (D-22..D-24, 30-05-PLAN.md Task 2, "
        "replacing the retired "
        "_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions)",
        _aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions)

    def _every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy():
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
            scope=config_page.SCOPE_DISPLAY)
        labels = re.findall(r'<label class="theme-chip[^>]*data-preview-src="([^"]+)"', rendered)
        if len(labels) < len(device_config.THEME_IDS):
            return False, (
                "expected at least one data-preview-src per registered theme, got %d"
                % len(labels))
        for src in labels:
            if not src.endswith(".png?live=1"):
                return False, "expected every data-preview-src to end in .png?live=1, got %r" % (src,)
        chip_images = re.findall(r'<img class="theme-chip__preview"[^>]*>', rendered)
        if not chip_images:
            return False, "expected at least one chip <img>"
        for tag in chip_images:
            if 'loading="lazy"' not in tag:
                return False, 'expected every chip <img> to keep loading="lazy"'
            if "?live=1" in tag:
                return False, "expected the chip's own <img> src to stay the fixed, non-live preview"
        return True, ""
    check(
        'every chip\'s own <label> carries a data-preview-src ending in .png?live=1, while each '
        'chip\'s own <img> keeps loading="lazy" and the fixed, non-live src (D-24)',
        _every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy)

    def _live_preview_caption_names_seeded_callsign_and_falls_back_to_sample():
        tmpdir = tempfile.mkdtemp(prefix="skypane-theme-live-preview-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            with_event = config_page.render(
                {
                    "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                    "state_dir": tmpdir,
                },
                scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        expected_caption = (
            config_page.THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE % "AFR1380")
        if escape_html(expected_caption) not in with_event:
            return False, "expected the caption to name the seeded event's callsign"

        without_event = config_page.render(
            {
                "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                "state_dir": None,
            },
            scope=config_page.SCOPE_DISPLAY)
        if escape_html(config_page.THEME_LIVE_PREVIEW_CAPTION_SAMPLE) not in without_event:
            return False, "expected the sample-flight caption with no events/no state_dir"
        return True, ""
    check(
        "the live preview's caption names the seeded event's callsign, and falls back to the "
        "sample-flight wording with no events (D-24)",
        _live_preview_caption_names_seeded_callsign_and_falls_back_to_sample)

    def _french_display_render_shows_the_live_preview_caption_with_flight_in_french():
        tmpdir = tempfile.mkdtemp(prefix="skypane-theme-live-preview-fr-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            prefs.set_request_prefs(lang="fr")
            try:
                rendered = config_page.render(
                    {
                        "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                        "state_dir": tmpdir,
                    },
                    scope=config_page.SCOPE_DISPLAY)
            finally:
                prefs.set_request_prefs(lang="en")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        if "Aperçu avec votre dernier vol : AFR1380" not in rendered:
            return False, "expected the French live-preview caption naming the seeded callsign"
        return True, ""
    check(
        "a French Display render's live preview shows ‘Aperçu avec votre dernier "
        "vol : ’ followed by the seeded event's callsign (D-24/D-05)",
        _french_display_render_shows_the_live_preview_caption_with_flight_in_french)

    # --- 22-10-PLAN.md Task 1 (X6, T10, T12, C1) ----------------------

    def _display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend():
        # 30-05-PLAN.md Task 3 (CFG-85), UPDATED IN PLACE from the
        # retired _display_renders_one_chip_density_and_a_swatch_
        # legend_under_every_grid: that check's own property (four
        # identical .theme-chip-grid grids, one legend each) is the
        # LITERAL thing CFG-85's accordion redesign retires by design.
        # There is now exactly one .theme-chip-grid on Display (the
        # rule-add form's own compact grid, unaffected by CFG-85 — see
        # its own call site's comment for why it deliberately stays a
        # theme-chip-grid) plus three .palette grids (departures/
        # arrivals/calendar), which carry no legend at all —
        # _palette_swatch_html() reads only departing_index/band_index,
        # never needing a two-dot legend to explain a single dot.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)

        grid_classes = re.findall(r'<div class="(theme-chip-grid[^"]*)"', rendered)
        if len(grid_classes) != 1:
            return False, (
                "expected exactly one .theme-chip-grid on Display (the rule-add form's own "
                "compact grid), got %d" % len(grid_classes))
        if "theme-chip-grid--compact" not in grid_classes[0]:
            return False, (
                "expected the remaining chip grid to carry the compact modifier, got %r"
                % (grid_classes[0],))

        theme_count = len(device_config.THEME_IDS)
        chip_classes = re.findall(r'<label class="(theme-chip[^"]*)"', rendered)
        if len(chip_classes) != theme_count:
            return False, (
                "expected %d .theme-chip labels (the rule-add form's grid alone, no leading "
                "chip), got %d" % (theme_count, len(chip_classes)))
        for cls in chip_classes:
            if "theme-chip--compact" not in cls:
                return False, "expected every remaining chip to carry the compact modifier, got %r" % (cls,)

        palette_count = rendered.count('class="palette" role="radiogroup"')
        if palette_count != 3:
            return False, (
                "expected exactly 3 .palette grids (departures/arrivals/calendar), got %d"
                % palette_count)
        palette_chip_count = rendered.count('class="palette-chip"')
        expected_palette_chips = theme_count * 3
        if palette_chip_count != expected_palette_chips:
            return False, (
                "expected %d .palette-chip entries (%d themes x 3 palettes), got %d"
                % (expected_palette_chips, theme_count, palette_chip_count))

        # The legend: exactly once, under the ONE remaining chip-grid —
        # never duplicated across the three legend-free palette grids.
        legend = escape_html(config_page.THEME_CHIP_SWATCH_LEGEND)
        if rendered.count(legend) != 1:
            return False, (
                "expected the swatch legend exactly once (only the rule-add form's grid renders "
                "one; the palette grids carry none), got %d" % rendered.count(legend))
        legend_html = '<p class="text-label section-caption">%s</p>' % legend
        if legend_html not in rendered:
            return False, (
                "expected the legend to carry .text-label section-caption's exact declaration set")
        if ("</label></div>" + legend_html) not in rendered:
            return False, "expected the legend to render as a sibling AFTER the grid, not inside it"
        return True, ""
    check(
        "Display renders exactly one .theme-chip-grid (the rule-add form's own compact grid, "
        "unaffected by CFG-85), followed by exactly one swatch legend in .text-label section-caption's "
        "own declaration set outside the radiogroup, and exactly 3 .palette grids "
        "(departures/arrivals/calendar) carrying no legend at all (22-10-PLAN.md Task 1, updated by "
        "30-05-PLAN.md Task 3 for CFG-85's accordion rebuild)",
        _display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend)

    # ------------------------------------------------------------------
    # 27-07-PLAN.md Task 3 (CFG-70): the legend stops naming a
    # distinction the registry does not carry.
    # ------------------------------------------------------------------

    def _the_swatch_legend_names_as_many_things_as_the_registry_carries():
        # THE RELATIONSHIP, COMPUTED FROM THE REGISTRY AT CHECK TIME —
        # never the literal string "Departures & arrivals". A literal
        # check would go stale silently the day a theme makes departures
        # and arrivals differ, pinning a lie in place exactly like the
        # defect this task fixes wore a different hat. "·" is the
        # separator the PREVIOUS copy used to name two things
        # ("Departures · Arrivals"); splitting on it is how this check
        # counts how many things the CURRENT copy names, whatever that
        # copy's own wording turns out to be.
        legend = config_page.THEME_CHIP_SWATCH_LEGEND
        labels = [part.strip() for part in legend.split("·") if part.strip()]
        label_count = len(labels)
        for theme_id in device_config.THEME_IDS:
            theme = device_config.THEMES[theme_id]
            colours = {
                config_page._palette_hex(theme["departing_index"]),
                config_page._palette_hex(theme["arriving_index"]),
            }
            expected = len(colours)
            if label_count != expected:
                return False, (
                    "theme=%r: the registry gives this theme %d distinct swatch colour(s) "
                    "(departing_index=%r, arriving_index=%r) but the shared legend %r names "
                    "%d label(s) — the legend is ONE line shown for every theme's chip, so it "
                    "must name exactly as many things as the registry gives that theme"
                    % (theme_id, expected, theme["departing_index"], theme["arriving_index"],
                       legend, label_count))
        return True, ""
    check(
        "the chip swatch legend names exactly as many things as the registry gives EVERY "
        "theme — computed from _palette_hex(departing_index)/_palette_hex(arriving_index) at "
        "check time, never a restated literal, so a future theme that DOES give departures "
        "and arrivals different inks would make this check demand two labels on its own "
        "(CFG-70, 27-07-PLAN.md Task 3)",
        _the_swatch_legend_names_as_many_things_as_the_registry_carries)

    def _the_current_badge_reads_a_server_rendered_translated_attribute():
        # T10: the badge's text used to be hard-coded English inside
        # style.css. It is now rendered onto the saved chip/card only -
        # the only element `--selected:not(:has(input:checked))::after`
        # can match - and read back with content: attr(...).
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        attr = config_page.CURRENT_BADGE_ATTR
        en = '%s="%s"' % (attr, escape_html(config_page.CURRENT_BADGE_LABEL))
        # One saved runway card, plus the saved theme chip in each of the
        # four grids that has "white" as its effective selection. Assert
        # the invariant that matters instead of a brittle total: every
        # element carrying the attribute also carries a --selected class,
        # and every --selected element carries the attribute.
        if rendered.count(attr + "=") == 0:
            return False, "expected the saved chip/card to carry the %s attribute" % attr
        if rendered.count(en) != rendered.count(attr + "="):
            return False, "expected every %s value to be the translated badge label" % attr
        for tag in re.findall(r"<label class=\"[^\"]*\"[^>]*>", rendered):
            has_attr = (attr + "=") in tag
            is_selected = "--selected" in tag
            if has_attr != is_selected:
                return False, (
                    "the %s attribute must be emitted on exactly the --selected elements, got %r"
                    % (attr, tag))

        prefs.set_request_prefs(lang="fr")
        try:
            fr_rendered = config_page.render({
                "device_config": {"theme": "white", "tracked_runway": "3"},
                "poll_cooldown_remaining": 0,
            }, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if ('%s="Actuel"' % attr) not in fr_rendered:
            return False, "expected the French render to carry the translated badge text"
        if ('%s="Current"' % attr) in fr_rendered:
            return False, "expected no English badge text in a French render"
        return True, ""
    check(
        "the 'Current' badge's text is server-rendered as a translated data-current-label attribute "
        "on exactly the --selected chip/card (never on any other), and the French render carries the "
        "French text (T10/B16, 22-10-PLAN.md Task 1)",
        _the_current_badge_reads_a_server_rendered_translated_attribute)

    # 30-03-PLAN.md Task 1 (CFG-85): the check that used to live here —
    # _segmented_control_resets_the_global_label_margin_and_the_legend_
    # leaves_the_serif — carried TWO properties: T12 (the rule-kind
    # segmented control's own label margin/height, unrelated to Aspect,
    # `.theme-form input[type="radio"] + label`) and C1 (the
    # `.frame-colours__panel-legend` serif-leak fix, which has no legend
    # to point at once the usage panels go). LEDGERED WHOLE to 30-07 —
    # its replacement must re-prove T12 verbatim (unaffected by CFG-85)
    # alongside whatever locator C1's property becomes. See
    # _ASPECT_REPIN_LEDGER below.
    #
    # 30-07-PLAN.md Task 3: C1's own half is RETIRED outright, not
    # repointed — the usage panels and their <legend> elements are gone,
    # and the rule-add form's "Match by" segmented control never had a
    # <legend> of its own to begin with (it labels itself via a
    # visually-hidden <span> plus aria-labelledby, confirmed at
    # config_page.py:4910-4912) — there is genuinely nothing left for a
    # legend-serif assertion to point at. This NARROWS the serif
    # boundary's own documented non-serif-exception set by one (the
    # sketch-findings-skypane skill's Typography section records
    # `.frame-colours__panel-legend` as its "Second non-serif exception";
    # that exception retires with its selector). Only T12 survives, and
    # is re-pinned below under a landing name that diverges from the
    # ledger's own predicted "replacement" — identical to "retired"
    # (30-03's same-name-repoint convention), which would trip the
    # ledger guard's own "retired name has no def" clause. Resolved the
    # same way as the row above: append "_after_the_panel_legend_
    # retires" to the landing name.

    def _segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif_after_the_panel_legend_retires():
        source = _read_static("style.css")

        # T12, unaffected by CFG-85: the rule-kind segmented control
        # ("Match by", inside the rule-add form's own .theme-form div,
        # config_page.py:4913) still resets the global `label` rule's
        # own 8px bottom margin and sits at its own 28px row height.
        selector = 'input[type="radio"] + label {'
        needle = ".theme-form " + selector
        if needle not in source:
            return False, "expected style.css to declare %r" % (needle,)
        idx = source.index(needle)
        body = source[idx + len(needle):source.index("}", idx)]
        if "margin-bottom: 0;" not in body:
            return False, (
                "%r must reset the global label rule's own margin-bottom "
                "(T12) — without it each 28px segment carries an 8px tail "
                "inside the 2px-padded .theme-form container" % (needle,))
        if "height: 28px;" not in body:
            return False, "%r must keep its own 28px row height (T12)" % (needle,)

        # C1's own selector is genuinely gone — the narrowed serif
        # exception set is a design-system fact, not merely an absence.
        # Comment-stripped: a historical comment naming the retired
        # selector (this plan's own repointed cross-reference, and this
        # very check's own docstring/comment above) must not fail this
        # gate — the established fix for exactly this collision
        # (companion/static/style.css's own header comment convention;
        # see this file's _strong_selected_treatment_is_keyed_to_the_
        # live_checked_radio() for the identical idiom).
        stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        if ".frame-colours__panel-legend" in stripped:
            return False, (
                "expected .frame-colours__panel-legend to be retired from style.css "
                "entirely (comment-stripped) — its own usage panels and <legend> "
                "elements no longer render anywhere on the page")

        return True, ""
    check(
        "the rule-kind segmented control (config_page.py's 'Match by' <div class=\"theme-form\">, "
        "unaffected by CFG-85) keeps its own global label-margin reset and 28px row height (T12), "
        "and .frame-colours__panel-legend is confirmed retired outright rather than repointed — the "
        "usage panels and their <legend> elements are gone, the rule-add form's own segmented "
        "control never had a <legend> to begin with, and this genuinely NARROWS the serif "
        "boundary's own documented non-serif-exception set by one (C1, 30-07-PLAN.md Task 3)",
        _segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif_after_the_panel_legend_retires)

    def _the_rules_add_form_is_one_left_aligned_centre_aligned_row():
        source = _read_static("style.css")
        selector = ".rule-add-form--inline {"
        if selector not in source:
            return False, "expected style.css to declare %r" % (selector,)
        body = source[source.index(selector) + len(selector):source.index("}", source.index(selector))]
        # The real defect: this modifier never reset .rule-add-form's own
        # flex-direction: column, so `align-items: flex-end` aligned every
        # child to the RIGHT of an 830px form, each on its own line.
        if "flex-direction: row" not in body:
            return False, (
                "%r must reset .rule-add-form's own flex-direction: column - that, not a "
                "margin-left: auto, is what right-aligned this form" % (selector,))
        if "align-items: center" not in body:
            return False, (
                "%r must centre-align its four separate controls (C4's composition rule)" % (selector,))
        if "flex-end" in body:
            return False, "%r must not keep the flex-end cross-axis alignment" % (selector,)
        if "margin-left: auto" in body:
            return False, "%r must declare no auto left margin" % (selector,)
        return True, ""
    check(
        "the rules add-form renders as one left-aligned, centre-aligned flex ROW (X6/C4) - the "
        "flex-direction: column it never reset, not an auto margin, is what pushed 'Add rule' to the "
        "far right (22-10-PLAN.md Task 1)",
        _the_rules_add_form_is_one_left_aligned_centre_aligned_row)

    # --- 22-10-PLAN.md Task 2 (B9, B14, B15, B7/C3) -------------------

    def _each_time_input_carries_the_site_language_and_a_visible_24h_sibling():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for name, value in (("quiet_hours_start", "22:00"), ("quiet_hours_end", "06:00")):
            needle = '<input type="time" name="%s" value="%s"' % (name, value)
            if needle not in rendered:
                return False, "expected %r in the rendered Display page" % (needle,)
            idx = rendered.index(needle)
            tail = rendered[idx:idx + 400]
            if 'lang="en"' not in tail:
                return False, "%s must carry the site language as lang= (B14)" % name
            # Built from the real emitter rather than a hand-typed literal
            # so this check does not go stale the moment the span grows a
            # new attribute (29-04-PLAN.md Task 2, CFG-80, added the
            # QUIET_NORMALISED_TIME_ATTR hook) — it asserts the SIBLING
            # renders, not one frozen shape of it.
            sibling = config_page._normalised_time_html(value)
            if sibling not in tail:
                return False, (
                    "%s must be followed by a VISIBLE sibling showing the normalised 24h value, "
                    "not a placeholder and not a title (B14)" % name)
            # The value must not have been smuggled into a placeholder or
            # a title instead - both are what B14's fix column rules out.
            input_tag = rendered[idx:rendered.index(">", idx)]
            if "placeholder=" in input_tag or "title=" in input_tag:
                return False, "%s must carry neither a placeholder nor a title (B14)" % name

        prefs.set_request_prefs(lang="fr")
        try:
            fr_rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if 'lang="fr"' not in fr_rendered:
            return False, "expected a French render to set lang=\"fr\" on its time inputs"
        if 'type="time" name="quiet_hours_start" value="22:00" required lang="en"' in fr_rendered:
            return False, "expected no lang=\"en\" time input in a French render"
        return True, ""
    check(
        "each <input type=\"time\"> carries the site language and a visible sibling showing the "
        "normalised 24h value (never a placeholder, never a title), in both languages "
        "(B14, 22-10-PLAN.md Task 2)",
        _each_time_input_carries_the_site_language_and_a_visible_24h_sibling)

    def _style_css_carries_the_b9_b15_and_b7_geometry_rules():
        source = _read_static("style.css")

        # B9: three equal runway cards on one line, never a 2 + 1 orphan.
        # A zero basis with no minimum is what makes wrapping structurally
        # impossible for three items; the 150px/140px pair it replaces is
        # exactly what produced the measured orphan at 390px.
        selector = ".runway-card {"
        idx = source.index(selector)
        body = source[idx + len(selector):source.index("\n}", idx)]
        if "flex: 1 1 0;" not in body:
            return False, ".runway-card must take a zero flex basis (B9)"
        if "min-width: 0;" not in body:
            return False, ".runway-card must take no minimum width (B9)"
        # Comment-filtered: the rule keeps a SUPERSEDED comment naming the
        # 150px/140px pair it replaces and why that pair produced the
        # orphan. That prose is the record of the change and must not be
        # deleted to satisfy a grep - so only DECLARATION lines are read.
        declarations = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith(("*", "/")))
        if "150px" in declarations or "140px" in declarations:
            return False, ".runway-card must not keep the 150px basis / 140px floor that wrapped 2 + 1"
        # .runway-row has a SECOND consumer (the quiet-hours preset row),
        # which must keep wrapping - so the fix must not sit on the row.
        row_idx = source.index(".runway-row {")
        row_body = source[row_idx + len(".runway-row {"):source.index("\n}", row_idx)]
        if "nowrap" in row_body:
            return False, (
                ".runway-row must keep flex-wrap: wrap - quiet_hours_group()'s preset row shares "
                "this class and must still be allowed to wrap")

        # B15: the calendar Connect/Replace button is content-width and
        # left-aligned, and keeps its accent fill (geometry only).
        b15 = '.rule-add-form:not(.rule-add-form--inline) > button[type="submit"] {'
        if b15 not in source:
            return False, "expected style.css to declare %r (B15)" % (b15,)
        b15_body = source[source.index(b15) + len(b15):source.index("\n}", source.index(b15))]
        if "align-self: flex-start" not in b15_body:
            return False, "%r must opt the button out of the column's stretch (B15)" % (b15,)
        if "width: auto" not in b15_body:
            return False, "%r must declare an automatic width (B15)" % (b15,)
        for banned in ("width: 100%", "display: block", "flex: 1"):
            if banned in b15_body:
                return False, "%r must declare no full-width treatment, found %r" % (b15, banned)

        # B7/C3: the selected-and-hovered segment restore rule, at the
        # register's own 12% accent wash - no new percentage.
        b7 = ".theme-form .theme-option--active:hover {"
        if b7 not in source:
            return False, "expected style.css to declare %r (B7/C3)" % (b7,)
        b7_body = source[source.index(b7) + len(b7):source.index("\n}", source.index(b7))]
        if "color-mix(in srgb, var(--color-accent) 12%, transparent)" not in b7_body:
            return False, (
                "%r must restore the register's own 12%% accent wash, not a new percentage "
                "(22-AUDIT.md's '12-18%%' is a suggestion; the register is the contract)" % (b7,))
        if "color: var(--color-accent)" not in b7_body:
            return False, "%r must restore the active segment's accent text" % (b7,)
        # Its :not()-scoped partner must still exist, or a hover on a
        # non-active segment would fall through to the primary fill.
        partner = ".theme-form .theme-option:not(.theme-option--active):hover {"
        if partner not in source:
            return False, "expected the :not()-scoped non-active hover rule to stay (B7/C3)"
        if source.index(partner) > source.index(b7):
            return False, "the :not()-scoped rule must stay ahead of the active restore rule"
        return True, ""
    check(
        "style.css carries B9's zero-basis runway card (with .runway-row still wrapping for its "
        "second consumer), B15's content-width left-aligned calendar button with its accent kept, "
        "and B7/C3's active-segment hover restore at the register's own 12% accent wash "
        "(22-10-PLAN.md Task 2)",
        _style_css_carries_the_b9_b15_and_b7_geometry_rules)

    # --- 22-10-PLAN.md Task 3 (B8, B17) -------------------------------

    def _send_a_test_lives_inside_the_notifications_card_via_the_form_idiom():
        # B8: the button used to render after </form> closed, as an
        # orphan floating between the Notifications card and the next
        # card. It now renders inside the card and reaches its own empty
        # <form> across the DOM.
        card = config_page.notifications_group(True, False, False)
        button = '<button type="submit" form="notifications-test">%s</button>' % escape_html(
            config_page.NOTIFICATIONS_TEST_BUTTON_TEXT)
        if button not in card:
            return False, "expected the test button INSIDE the Notifications card (B8)"
        if not card.rstrip().endswith("</div>"):
            return False, "expected the card to still close its own wrapper last"

        section = config_page.notifications_test_section()
        expected_form = (
            '<form method="post" action="/settings/notifications/test" '
            'id="notifications-test" class="notifications-test-form"></form>')
        if section != expected_form:
            return False, (
                "expected notifications_test_section() to render an EMPTY form carrying the id "
                "the button's form= names, got %r" % (section,))
        if "<button" in section:
            return False, "the sibling form must hold no control of its own (B8)"

        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        if rendered.count('form="notifications-test"') != 1:
            return False, "expected exactly one cross-DOM attachment to the test form"
        if rendered.count('id="notifications-test"') != 1:
            return False, "expected exactly one element carrying that id"
        # Nothing renders between the settings form's own close and the
        # empty form: the two are adjacent, with no control in between.
        if "</form><form" not in rendered.replace("\n", ""):
            return False, (
                "expected the empty test form to render immediately after the settings form, "
                "with no orphaned control between the two cards (B8)")
        # And the button is inside the card, not after it.
        card_end = rendered.index('id="notifications-test"')
        if rendered.index('form="notifications-test"') > card_end:
            return False, "expected the button to render BEFORE the empty form, inside its card"
        # The action and its handler are untouched by the move - form
        # ownership comes from the attribute, not from proximity (T-22-34).
        if config_page.NOTIFICATIONS_TEST_ROUTE not in rendered:
            return False, "expected the test form to keep its own action route"
        return True, ""
    check(
        "'Send a test' renders inside the Notifications card and reaches its own EMPTY sibling "
        "<form> through the cross-DOM form= idiom's fifth consumer - no control renders between "
        "two cards, and the form keeps its own action (B8, 22-10-PLAN.md Task 3)",
        _send_a_test_lives_inside_the_notifications_card_via_the_form_idiom)

    def _the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input():
        # B17: the label used to WRAP the input, which put both on one
        # line and started the control at x=515 while every other Device
        # field started at x=361.
        rendered = config_page.wake_interval_group(300)
        label = '<label for="%s">%s</label>' % (
            config_page.WAKE_INTERVAL_INPUT_ID,
            escape_html(config_page.i18n.t("Wake interval (seconds)")))
        if label not in rendered:
            return False, "expected the label to be its own element above the control (B17)"
        if "</label><input" not in rendered:
            return False, "expected the input to be the label's SIBLING, not its child (B17)"
        unit = (
            '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
            % config_page.WAKE_INTERVAL_UNIT_LABEL)
        if unit not in rendered:
            return False, "expected the unit as a sibling label, not a placeholder (B17)"
        input_tag = rendered[rendered.index('<input type="number"'):]
        input_tag = input_tag[:input_tag.index(">") + 1]
        # The unit must be a SIBLING, never the control's own placeholder
        # or title - both are what B17's fix column rules out, and the
        # placeholder slot is already spoken for by the locked
        # "Uses server default" empty-state text.
        if 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT not in input_tag:
            return False, "expected the locked placeholder text to survive untouched"
        if "title=" in input_tag:
            return False, "the unit must not be carried as a title on the control (B17)"

        source = _read_static("style.css")
        selector = '.config-form input[name="wake_interval_s"] {'
        if selector not in source:
            return False, "expected style.css to declare %r (B17)" % (selector,)
        body = source[source.index(selector) + len(selector):source.index("}", source.index(selector))]
        if "width: 8ch" not in body:
            return False, "%r must declare a character-based width (B17)" % (selector,)
        if "min-width: 96px" not in body:
            return False, "%r must declare a pixel minimum (B17)" % (selector,)
        if "height" in body:
            return False, (
                "%r must declare NO height - the global input/select 44px min-height is the touch-"
                "target register's 'kept' entry for <input type=\"number\"> and stays untouched"
                % (selector,))
        # It must beat, not merely follow, the phase-18 width rule.
        competitor = '.config-form input[type="number"],'
        if source.index(competitor) > source.index(selector):
            return False, (
                "the content-fit rule must come AFTER .config-form input[type=\"number\"]'s own "
                "width: 100% at equal specificity, or it silently loses")
        return True, ""
    check(
        "the wake-interval field puts its label on its own line above a content-sized input (8ch "
        "with a 96px minimum, no height declared so the 44px touch-target floor is untouched) with "
        "the unit as a sibling label (B17, 22-10-PLAN.md Task 3)",
        _the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input)

    def _the_calendar_status_detail_has_a_singular_form():
        # D-06/B16/CFG-29: this string read "1 upcoming flights" whenever
        # the feed held exactly one. 22-08-PLAN.md found it and left it
        # because that plan does not own this file.
        synced = "2026-09-13T09:00:00+00:00"
        now = "2026-09-13T09:05:00+00:00"

        def detail_for(count):
            row_body_html, _disconnect_form_html = config_page._calendar_connection_html(
                True, False, synced, None, now, count)
            return row_body_html

        one = detail_for(1)
        if "1 upcoming flights" in one:
            return False, "expected a singular form for exactly one upcoming flight"
        if escape_html(config_page.CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE.split(" ·")[0]) not in one:
            return False, "expected the singular template's own text at a count of 1"
        for count in (0, 2, 7):
            many = detail_for(count)
            if "%d upcoming flights" % count not in many:
                return False, "expected the plural form at a count of %d" % count
        # Both forms must be translatable, and both must be real
        # catalogue keys (test_i18n.py's own completeness scan proves the
        # second half; this proves the call site reaches both).
        prefs.set_request_prefs(lang="fr")
        try:
            fr_one = detail_for(1)
            fr_many = detail_for(3)
        finally:
            prefs.set_request_prefs(lang="en")
        if "1 vol à venir" not in fr_one:
            return False, "expected the French singular form"
        if "3 vols à venir" not in fr_many:
            return False, "expected the French plural form"
        return True, ""
    check(
        "the Calendar status detail has a singular form, so a feed holding exactly one flight "
        "never reads '1 upcoming flights', in both languages (D-06/B16/CFG-29, 22-10-PLAN.md "
        "Task 3 — found by 22-08, landed here because this plan owns config_page.py)",
        _the_calendar_status_detail_has_a_singular_form)

    # --- 23-06-PLAN.md Task 2 (D1/CFG-35): the Display scope joins the
    # refresh loop, and its form does not move ---------------------------

    def _display_ctx(now=None):
        ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True,
                              "wake_interval_s": 900, "display_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        }
        if now is not None:
            ctx["now"] = now
        return ctx

    def _the_display_scope_refreshes_itself_from_the_same_builder():
        now = "2026-08-27T12:00:00+00:00"
        rendered = config_page.render(_display_ctx(now), scope=config_page.SCOPE_DISPLAY)
        built = layout.freshness_line_html(now)
        if built not in rendered:
            return False, (
                "expected the Display scope's freshness line to be layout.freshness_line_html()'s "
                "own output verbatim — the same builder Health and Home call, so the three pages "
                "cannot disagree about what a freshness line is. Built:\n%r" % (built,))
        for attr, want in (("data-loaded-at", 1), ("data-refresh-pill", 1)):
            if rendered.count(attr) != want:
                return False, (
                    "expected exactly %d %s on the Display scope — freshness.js reads the first "
                    "with a single querySelector and a second would silently win, got %d"
                    % (want, attr, rendered.count(attr)))
        # The loop's own gate: without the marker there is no loop, and
        # with a page key that declares no regions there is no swap.
        if layout.REFRESH_PAGE_DISPLAY not in layout.REFRESH_SWAP_SELECTORS_BY_PAGE:
            return False, "expected the Display scope to declare its own swap regions"
        shell = layout.page_shell(
            title="Display", active=layout.REFRESH_PAGE_DISPLAY, body=rendered)
        if ('%s="%s"' % (layout.REFRESH_PAGE_ATTR, layout.REFRESH_PAGE_DISPLAY)) not in shell:
            return False, "expected the Display document to carry its own page key on <body>"
        # A ctx with no render instant renders no freshness line at all
        # rather than an element carrying an empty or invented one — the
        # same degrade frame_strip_html() applies to a missing next wake.
        bare = config_page.render(_display_ctx(), scope=config_page.SCOPE_DISPLAY)
        if "data-loaded-at" in bare:
            return False, (
                "expected no freshness marker at all when the caller has no render instant — an "
                "element carrying an empty instant reads as a correct time to a script and is "
                "worse than no element")
        return True, ""
    check(
        "the Display scope renders layout.freshness_line_html()'s own output verbatim with exactly "
        "one data-loaded-at and one data-refresh-pill, declares its own swap regions, carries its "
        "page key on <body>, and renders no freshness marker at all when the caller has no render "
        "instant (D1/CFG-35, 23-06-PLAN.md Task 2)",
        _the_display_scope_refreshes_itself_from_the_same_builder)

    def _the_display_form_is_untouched_by_the_refresh_loop():
        # The one thing a swap must never touch. Display is a settings
        # page, and 22-01/B1 — this page rendered unsaveable with JS on —
        # is the defect of record this clause exists to keep closed.
        now = "2026-08-27T12:00:00+00:00"
        rendered = config_page.render(_display_ctx(now), scope=config_page.SCOPE_DISPLAY)
        for selector in layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_DISPLAY]:
            for banned in ("form", config_page.SETTINGS_FORM_ID, "dirty", "save"):
                if banned in selector:
                    return False, (
                        "the Display scope declares the swap region %r, which names %r — a swap "
                        "that lands on this page's form is the P0 Phase 22 existed to fix"
                        % (selector, banned))
        # The form, its cross-DOM attachment and the fallback Save are
        # all still rendered, unchanged by this plan's header edit.
        if ('<form class="config-form" method="post" id="%s"' % config_page.SETTINGS_FORM_ID) \
                not in rendered and ('id="%s"' % config_page.SETTINGS_FORM_ID) not in rendered:
            return False, "expected the settings form to still render on the Display scope"
        if ('form="%s"' % config_page.SETTINGS_FORM_ID) not in rendered:
            return False, (
                "expected the cross-DOM form= attachment B1 depends on to survive — every saved "
                "theme radio submits through it")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in rendered:
            return False, (
                "expected the fallback Save button to stay reachable — with scripts blocked it "
                "is the ONLY way to save this page")
        # The freshness line is in the page HEADER, above the form, and
        # the form is not inside it.
        header_at = rendered.index("page-header__freshness")
        form_at = rendered.index('id="%s"' % config_page.SETTINGS_FORM_ID)
        if header_at > form_at:
            return False, (
                "expected the freshness line in the page header, above the settings form, got "
                "it at %d with the form at %d" % (header_at, form_at))
        return True, ""
    check(
        "no Display swap region names a form, a dirty marker or a save control, and the settings "
        "form, its cross-DOM form= attachment and the fallback Save all still render with the "
        "freshness line above them in the page header — a swap landing on this page's form is the "
        "P0 Phase 22 existed to fix (B1/D1, 23-06-PLAN.md Task 2)",
        _the_display_form_is_untouched_by_the_refresh_loop)

    # ------------------------------------------------------------------
    # 25-05-PLAN.md Task 1 (CFG-49): D18's two gauges, server-rendered.
    #
    # The card showed neither side of the trade-off it exists for. These
    # three checks are about what the two new sentences may CLAIM, not
    # about whether they render: one of them can be true today and the
    # other one cannot, and the whole subject here is that the second
    # one says so.
    # ------------------------------------------------------------------

    # A daily-average battery series in server/history_db.py's own row
    # shape, oldest first (order does not matter — battery.py sorts).
    def _battery_series(*pairs):
        return [{"ts": ts, "battery_mv": mv, "reading_count": 3}
                for ts, mv in pairs]

    # Six shapes, each named for the answer it must produce. The three
    # that support NO figure are the point of the fixture: a series that
    # is rising (the device was charged), one whose span is a single day
    # (inside this series' own noise) and one with nothing in it at all.
    _FALLING = _battery_series(
        ("2026-09-01", 4100), ("2026-09-04", 3800), ("2026-09-07", 3600))
    _FALLING_ONE_DAY_LEFT = _battery_series(
        ("2026-09-05", 3600), ("2026-09-07", 3400))
    _RISING = _battery_series(
        ("2026-09-01", 3400), ("2026-09-04", 3700), ("2026-09-07", 4100))
    _ONE_DAY_SPAN = _battery_series(("2026-09-06", 4100), ("2026-09-07", 3900))
    _EMPTY = []

    def _the_two_gauges_claim_exactly_what_the_data_supports():
        """CFG-49 (25-05-PLAN.md Task 1): the freshness sentence is a
        BOUND and the battery sentence is an OBSERVATION — and the
        second one has to be able to say that it has nothing to say.

        The audit asked for "estimated battery life ≈ 38 days". That
        figure does not exist anywhere in this codebase: computing it
        needs a per-wake energy cost this project has never measured
        (DEVICE-05's discharge run is still open), so the only absolute
        figure permitted here is one derived from this device's OWN
        observed discharge slope, and every other case renders a named
        state instead.
        """
        min_s = device_config.WAKE_INTERVAL_MIN_S
        max_s = device_config.WAKE_INTERVAL_MAX_S

        # 1. THE BOUND, at both ends of the configured band and in the
        #    middle — and the words "at most" are part of the claim, not
        #    decoration: without them the sentence becomes a statement
        #    about TYPICAL behaviour, which nothing measures.
        bound_words = config_page.WAKE_FRESHNESS_TEXT.split(
            layout.VALUE_CONTROL_TEXT_TOKEN)[0].strip()
        if "at most" not in bound_words:
            return False, (
                "the freshness wording %r does not say 'at most' before its quantity — a bound "
                "stated without it is a claim about typical behaviour, and nothing in this "
                "project measures that" % config_page.WAKE_FRESHNESS_TEXT)
        for seconds, minutes in ((min_s, 1), (max_s, 60), (600, 10), (90, 2), (1800, 30)):
            said = config_page.wake_freshness_text(seconds)
            if bound_words not in said:
                return False, "wake_freshness_text(%d) = %r drops the bound" % (seconds, said)
            numbers = re.findall(r"\d+", said)
            if numbers != [str(minutes)]:
                return False, (
                    "wake_freshness_text(%d) names %r; %d seconds is %d whole minutes — and it "
                    "must round UP, because 'at most 1 min' is FALSE for a 90-second cadence"
                    % (seconds, numbers, seconds, minutes))

        # 2. THE ABSOLUTE FIGURE, AND IT IS battery.py's OWN. Recomputed
        #    from the estimator and required to appear verbatim, so a
        #    second days-remaining computation in the page module would
        #    have to agree with the first one to pass — and the fixture
        #    is checked to actually PRODUCE a figure first, or this
        #    whole clause would be vacuous.
        estimate = battery.battery_life_estimate(_FALLING, 600, 600)
        days = estimate["days_remaining"]
        if estimate["trend"] != battery.LIFE_TREND_FALLING or not isinstance(days, int):
            return False, (
                "the falling fixture no longer produces a figure (%r) — the clause below would "
                "pass against a card that never prints one" % (estimate,))
        said = config_page.wake_battery_observed_text(600, _FALLING)
        if str(days) not in re.findall(r"\d+", said):
            return False, (
                "the battery sentence %r does not carry battery_life_estimate()'s own figure "
                "(%d days) — the one estimate lives in companion/battery.py" % (said, days))
        if "≈" not in said:
            return False, (
                "the battery sentence %r drops the ≈ honesty marker this app already wears on "
                "the battery percentage — an observed projection is not a datasheet figure"
                % said)

        # THE SINGULAR, which is reachable (a nearly-empty battery) and
        # is the plural defect this project's i18n harness has caught
        # before.
        one_day = battery.battery_life_estimate(_FALLING_ONE_DAY_LEFT, 600, 600)
        if one_day["days_remaining"] != 1:
            return False, (
                "the one-day fixture reports %r days — the singular wording below would never "
                "be exercised" % (one_day["days_remaining"],))
        singular = config_page.wake_battery_observed_text(600, _FALLING_ONE_DAY_LEFT)
        if singular != i18n.t(config_page.WAKE_BATTERY_DAY_TEXT).replace(
                layout.VALUE_CONTROL_TEXT_TOKEN, "1"):
            return False, (
                "a one-day estimate renders %r rather than the singular wording — '1 days' is "
                "the missing-plural defect" % singular)

        # 3. THE THREE SHAPES THAT SUPPORT NO FIGURE AT ALL, each
        #    required to render the NAMED state — a real sentence, never
        #    a blank, and never a number.
        unknown = i18n.t(config_page.WAKE_BATTERY_UNKNOWN_TEXT)
        for name, rows in (("rising (the device was charged)", _RISING),
                           ("a one-day span", _ONE_DAY_SPAN),
                           ("no history at all", _EMPTY)):
            said = config_page.wake_battery_observed_text(600, rows)
            if said != unknown:
                return False, (
                    "with %s the battery sentence reads %r; it owes the named 'not enough "
                    "history yet' state, which is a rendered sentence rather than a blank"
                    % (name, said))
            if re.search(r"\d", said):
                return False, (
                    "with %s the battery sentence carries a number (%r) — a figure the data "
                    "cannot support is the dishonest state Phase 22 spent a phase removing"
                    % (name, said))
            if "-" in said.replace("—", "") and re.search(r"-\d", said):
                return False, "with %s the battery sentence carries a negative (%r)" % (name, said)

        # 4. NEITHER SENTENCE INVENTS A SUBJECT. No saved interval, no
        #    gauges — the same omit-don't-fabricate rule the `value`
        #    attribute and 25-04's handles already follow.
        for absent in (None, 0, True, "", "300"):
            if config_page.wake_gauge_interval_s(absent) is not None:
                return False, (
                    "wake_gauge_interval_s(%r) resolved to an interval — only a real int inside "
                    "the configured band is one" % (absent,))
        if config_page.wake_gauges_html(None, _FALLING) != "":
            return False, "the gauges rendered with no interval to describe"
        for out_of_band in (min_s - 1, max_s + 1):
            if config_page.wake_gauge_interval_s(out_of_band) is not None:
                return False, (
                    "wake_gauge_interval_s(%d) accepted a value outside [%d, %d]"
                    % (out_of_band, min_s, max_s))

        # 5. D-07's ECHO, AND ITS FLOOR. A rejected save's raw string is
        #    what the gauges describe — but only when it is a usable
        #    interval, because "at most 0 min" for a submitted "7" would
        #    describe a cadence this device cannot be configured to use.
        if config_page.wake_gauge_interval_s(600, {"wake_interval_s": "900"}) != 900:
            return False, (
                "a rejected save's echoed 900 is not what the gauges describe — the picture and "
                "the field must not disagree on the screen where a mistake is being fixed")
        for junk in ("7", "", "abc", "99999", "60.5", None):
            if config_page.wake_gauge_interval_s(600, {"wake_interval_s": junk}) is not None:
                return False, (
                    "an echoed %r produced a gauge subject — a gauge about a value this device "
                    "cannot use is a gauge about nothing" % (junk,))

        # 6. THE SCREEN-OFF CLAUSE, which is what keeps BOTH sentences
        #    from over-claiming: neither is in force while the screen is
        #    off, because server/wake.py pins DISPLAY_OFF_SLEEP_S ahead
        #    of this field entirely.
        off = config_page.wake_screen_off_text()
        if layout.duration_text(device_config.DISPLAY_OFF_SLEEP_S) not in off:
            return False, (
                "the screen-off clause %r does not name device_config.DISPLAY_OFF_SLEEP_S (%d s) "
                "through the app's own duration ladder"
                % (off, device_config.DISPLAY_OFF_SLEEP_S))
        card = config_page.wake_gauges_html(600, _FALLING)
        if escape_html(off) not in card:
            return False, (
                "the rendered gauges do not carry the screen-off clause — a visitor who has "
                "turned the screen off reads a battery claim that does not apply to their frame")
        return True, ""
    check(
        "the freshness gauge states a BOUND (\"at most\", rounded UP) naming the same whole "
        "minutes the interval implies at the band's minimum, its maximum and in between; the "
        "battery gauge prints an absolute figure ONLY when companion/battery.py's own estimate "
        "supports one — recomputed from the estimator, singular and plural both — and renders "
        "the NAMED \"not enough history yet\" sentence with no number at all for a rising, a "
        "one-day and an empty series; neither gauge renders without a usable interval, D-07's "
        "echo is honoured only where it is usable, and the screen-off cadence is stated "
        "(CFG-49, 25-05-PLAN.md Task 1)",
        _the_two_gauges_claim_exactly_what_the_data_supports)

    def _no_days_remaining_arithmetic_lives_outside_companion_battery():
        """CFG-49 (25-05-PLAN.md Task 1): the page module CALLS the
        estimate; it never computes one.

        `test_companion_app.py`'s one-home guard already catches a second
        estimate by NAME and by the millivolt-endpoint pair. This is the
        third net and the narrow one: the arithmetic itself — a division
        by an observed slope, or a distance to the empty endpoint or the
        SEED-006 curve table itself (quick 260923-gaf) — appearing
        anywhere under `companion/pages/`. Comments and docstrings are
        stripped first, for this file's own standing reason: the prose
        that explains the rule must neither satisfy nor break it.
        """
        banned = ("days_remaining", "mv_per_day", "BATTERY_EMPTY_MV",
                  "BATTERY_FULL_MV", "observed_span_days", "BATTERY_DISCHARGE_CURVE")
        pages_dir = os.path.join(HERE, "pages")
        for name in sorted(os.listdir(pages_dir)):
            if not name.endswith(".py"):
                continue
            for used in _python_identifiers(os.path.join(pages_dir, name)):
                if used in banned:
                    return False, (
                        "companion/pages/%s uses %r as an IDENTIFIER — the days-remaining "
                        "arithmetic has exactly one home and companion/pages is not it. "
                        "(Reading the estimator's own returned key back out of its dict is a "
                        "STRING, not an identifier, and is the one permitted shape.)"
                        % (name, used))
        # And the call itself is QUALIFIED, per references/
        # data-density.md: a bare `from companion.battery import
        # battery_life_estimate` makes the estimate read as the page's
        # own, which is the drift the shared module exists to prevent.
        names = _python_identifiers(os.path.join(HERE, "pages", "config_page.py"))
        if "battery_life_estimate" not in names:
            return False, (
                "config_page.py never names battery_life_estimate() — the battery gauge would "
                "then be reading its figure from somewhere else")
        import ast
        with open(os.path.join(HERE, "pages", "config_page.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("battery"):
                return False, (
                    "config_page.py imports %r OUT of companion.battery — the estimator is "
                    "called QUALIFIED so it can never read as this page's own "
                    "(references/data-density.md)"
                    % [alias.name for alias in node.names])
        # Every template this plan added carries the quantity mark the
        # script substitutes into, and is a real catalogue key.
        for template in (config_page.WAKE_FRESHNESS_TEXT,
                         config_page.WAKE_BATTERY_DAY_TEXT,
                         config_page.WAKE_BATTERY_DAYS_TEXT,
                         config_page.WAKE_BATTERY_INSTEAD_TEXT):
            if layout.VALUE_CONTROL_TEXT_TOKEN not in template:
                return False, (
                    "the template %r carries no %r — the script substitutes the quantity into it "
                    "and would render the sentence unchanged"
                    % (template, layout.VALUE_CONTROL_TEXT_TOKEN))
            for artefact in ("%s", "{}"):
                if artefact in template:
                    return False, (
                        "the template %r carries %r — these reach the browser as attribute "
                        "values and companion/test_i18n.py's Check 3 scans every French render "
                        "for exactly that artefact" % (template, artefact))
            if template not in i18n_fr.CATALOG:
                return False, "the template %r has no French sibling" % template
        return True, ""
    check(
        "no days-remaining arithmetic exists anywhere under companion/pages/ — every one of "
        "days_remaining/mv_per_day/observed_span_days/the two millivolt endpoints/the SEED-006 "
        "BATTERY_DISCHARGE_CURVE table appears only as a read of the estimator's own returned "
        "dict, comments and docstrings stripped first — the estimate is called QUALIFIED off "
        "companion.battery, and every quantity template this card adds carries the \"#\" mark "
        "rather than a format artefact and has a French sibling (CFG-49/D-27, 25-05-PLAN.md "
        "Task 1, quick 260923-gaf)",
        _no_days_remaining_arithmetic_lives_outside_companion_battery)

    # ==================================================================
    # 27-06-PLAN.md Task 3 (CFG-67): the three texts, cut against
    # 27-01-SUMMARY.md's own recorded baselines (measured 360px,
    # rendered, both languages). Each check is ONE read of the region,
    # with every assertion made against that SAME read — "shorter" and,
    # where the honesty contract applies, "still refuses" are proven
    # about one rendering, never two separate ones (T-27-06-A).
    #
    # The forbidden pattern is scoped to the DAYS-CLAIM SHAPE itself
    # ("≈ <digits> day(s)/jour(s)"), never to "≈" near any digit —
    # 27-01-SUMMARY.md found the naive `≈\s*\d` pattern false-positives
    # on the wake-interval caption's own legitimate "(next wake ≈ 31
    # Jul 08:05)" text, a real derivable timestamp, not an invented
    # figure. That caption is a SEPARATE region from the gauges below in
    # any case, but the pattern is scoped correctly regardless.
    # ==================================================================

    _DAYS_FIGURE_PATTERN = re.compile(r"≈\s*\d+\s*(?:day|days|jour|jours)\b")

    def _html_region_text(fragment):
        """Strip tags, unescape entities, collapse whitespace — the
        python-side equivalent of reading `.textContent` off a rendered
        element, without a browser.
        """
        stripped = re.sub(r"<[^>]*>", "", fragment)
        return re.sub(r"\s+", " ", html.unescape(stripped)).strip()

    def _wake_interval_caption_is_shortened_in_both_languages():
        baseline = 220
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.wake_interval_group(
                    300, next_wake_clock="31 Jul 08:05")
            finally:
                prefs.set_request_prefs(lang="en")
            m = re.search(
                r'<p class="text-label section-caption" id="%s">(.*?)</p>'
                % re.escape(config_page.WAKE_INTERVAL_SECTION_CAPTION_ID), rendered)
            if not m:
                return False, "%s: #%s is missing from wake_interval_group()'s own markup" % (
                    lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID)
            text = _html_region_text(m.group(1))
            if len(text) >= baseline:
                return False, (
                    "%s: #%s renders %d character(s), against a recorded baseline of %d "
                    "(27-01-SUMMARY.md). The copy was not cut. It reads %r"
                    % (lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID, len(text), baseline,
                       text))
        return True, ""
    check(
        "the wake-interval caption (#wake-interval-caption) is materially shorter than "
        "27-01-SUMMARY.md's recorded 220-char baseline in BOTH languages — the mechanism and "
        "apply-timing sentences are cut, the derived \"(next wake ≈ ...)\" suffix (a real "
        "timestamp, not an invented figure) is untouched (CFG-67, 27-06-PLAN.md Task 3)",
        _wake_interval_caption_is_shortened_in_both_languages)

    def _wake_gauges_are_shortened_and_the_battery_refusal_survives_in_both_languages():
        baseline = 254
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                # No battery_rows: the insufficient-history state — the
                # one 27-01-SUMMARY.md's baseline was measured against,
                # and the one whose refusal this check must prove
                # survives on the SAME reading as the length.
                rendered = config_page.wake_gauges_html(300)
            finally:
                prefs.set_request_prefs(lang="en")
            segments = re.findall(
                r'<p class="[^"]*\bwake-gauge\b[^"]*"[^>]*>(.*?)</p>', rendered, re.S)
            if len(segments) != 2:
                return False, (
                    "%s: expected 2 .wake-gauge elements, found %d" % (lang, len(segments)))
            text = " ".join(_html_region_text(seg) for seg in segments)
            text = re.sub(r"\s+", " ", text).strip()
            # ONE READ, TWO ASSERTIONS, per T-27-06-A — both against
            # `text` as measured above, never a second re-render.
            if len(text) >= baseline:
                return False, (
                    "%s: .wake-gauge renders %d character(s) across %d element(s), against a "
                    "recorded baseline of %d (27-01-SUMMARY.md). The copy was not cut. It "
                    "reads %r" % (lang, len(text), len(segments), baseline, text))
            found = _DAYS_FIGURE_PATTERN.search(text)
            if found:
                return False, (
                    "%s: .wake-gauge did get shorter (%d character(s), under the %d baseline) "
                    "but the insufficient-history state now matches %r at %r — a shorter "
                    "sentence that starts claiming a figure this frame's own history cannot "
                    "support is a regression, not a cut. The whole region reads %r"
                    % (lang, len(text), baseline, _DAYS_FIGURE_PATTERN.pattern,
                       found.group(0), text))
        return True, ""
    check(
        "the two wake gauges (.wake-gauge) are materially shorter than 27-01-SUMMARY.md's "
        "recorded 254-char combined baseline in BOTH languages, and the insufficient-history "
        "state still prints NO absolute battery figure — asserted about the SAME reading the "
        "length is measured from, with the forbidden pattern scoped to the days-claim shape "
        "itself so it does not false-positive on an unrelated ≈-bearing timestamp (D18's "
        "honesty contract, CFG-67, 27-06-PLAN.md Task 3)",
        _wake_gauges_are_shortened_and_the_battery_refusal_survives_in_both_languages)

    def _quiet_hours_caption_is_shortened_and_carries_no_delay_sentence_in_either_language():
        # 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: RETARGETED.
        # quiet_hours_group() no longer accepts a `delay_sentence`
        # keyword at all — the old call below would now raise
        # TypeError, which is itself proof the parameter is gone (a
        # regression back to accepting it would fail this check by
        # crashing it, not by a silent pass). What this check asserts
        # instead: the caption renders as EXACTLY
        # QUIET_HOURS_SECTION_CAPTION's own translated text, nothing
        # appended, in both languages — materially shorter than the
        # 27-01-SUMMARY.md 188-char baseline this check has pinned
        # since CFG-67, and now for a stronger reason (no second
        # sentence AT ALL, not merely a shortened one).
        baseline = 188
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.quiet_hours_group("23:00", "07:00")
            finally:
                prefs.set_request_prefs(lang="en")
            m = re.search(
                r'<p class="text-label section-caption" id="%s">(.*?)</p>'
                % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), rendered)
            if not m:
                return False, "%s: #%s is missing from quiet_hours_group()'s own markup" % (
                    lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID)
            text = _html_region_text(m.group(1))
            if len(text) >= baseline:
                return False, (
                    "%s: #%s renders %d character(s), against a recorded baseline of %d "
                    "(27-01-SUMMARY.md). The copy was not cut. It reads %r"
                    % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, len(text), baseline,
                       text))
            expected = i18n.t_lang(config_page.QUIET_HOURS_SECTION_CAPTION, lang)
            if text != expected:
                return False, (
                    "%s: #%s expected to render as EXACTLY %r (no appended delay sentence), "
                    "got %r" % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, expected, text))
        return True, ""
    check(
        "the Quiet hours paragraph (#quiet-hours-caption) is materially shorter than "
        "27-01-SUMMARY.md's recorded 188-char baseline in BOTH languages, and renders as EXACTLY "
        "QUIET_HOURS_SECTION_CAPTION's own translated text with no delay sentence appended at "
        "all any more — quiet_hours_group() no longer accepts a delay_sentence keyword (CFG-79, "
        "29-05-PLAN.md Task 2, narrowing CFG-67's 27-06-PLAN.md Task 3 cut)",
        _quiet_hours_caption_is_shortened_and_carries_no_delay_sentence_in_either_language)

    def _the_gauges_are_an_addition_and_the_number_input_is_untouched():
        """CFG-49 (25-05-PLAN.md Task 1): the `<input type="number">` is
        the ONLY thing on this card that posts, and its `value`-attribute
        guard is load-bearing in a way no other field's is.

        An out-of-range `value` on a native numeric input fails HTML5
        constraint validation, which blocks submission of the ENTIRE
        Settings form — not just this field. That is live rather than
        hypothetical: `deploy/skypane.env.example` ships
        SKYPANE_SLEEP_S=30, below the 60 s floor, and plan 11-04 feeds
        that value in as the pre-fill fallback.

        The byte-identical diff against the pre-task builder was taken
        once, by hand, across four argument shapes (recorded in the
        SUMMARY). What lives here is the durable half.
        """
        min_s = device_config.WAKE_INTERVAL_MIN_S
        max_s = device_config.WAKE_INTERVAL_MAX_S
        expected_head = (
            '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
            ' placeholder="%s"' % (
                escape_html(config_page.WAKE_INTERVAL_INPUT_ID), min_s, max_s,
                escape_html(i18n.t(config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT))))
        # The fifth column is whether the gauges are owed at all: they
        # describe the value the FIELD will hold, so every shape where
        # the field deliberately shows nothing is a shape where the
        # gauges must show nothing either.
        cases = (
            ("saved, in band", 600, None, ' value="600"', True),
            ("stored BELOW the floor", 30, None, "", False),
            ("stored above the ceiling", max_s + 1, None, "", False),
            ("never set", None, None, "", False),
            ("a rejected save's raw echo", 600, {"wake_interval_s": "7"},
             ' value="7"', False),
            ("a rejected save echoing a usable value", 600,
             {"wake_interval_s": "900"}, ' value="900"', True),
        )
        for name, current, submitted, value_attr, owes_gauges in cases:
            markup = config_page.wake_interval_group(
                current, submitted=submitted, battery_rows=_FALLING)
            tag = re.search(r'<input type="number"[^>]*>', markup)
            if not tag:
                return False, "%s: no <input type=\"number\"> at all" % name
            element = tag.group(0)
            if not element.startswith(expected_head):
                return False, (
                    "%s: the number input is no longer byte-identical to its pre-plan output.\n"
                    "  expected it to start %r\n  got %r" % (name, expected_head, element))
            if value_attr and value_attr not in element:
                return False, "%s: expected %r in %s" % (name, value_attr, element)
            if not value_attr and " value=" in element:
                return False, (
                    "%s: the number input carries a value attribute (%s) — an out-of-range value "
                    "fails HTML5 constraint validation and blocks submission of the WHOLE "
                    "Settings form, not just this field" % (name, element))
            # THE LABEL, THE UNIT SIBLING AND THE ERROR BLOCK, in their
            # B17 order: label ABOVE the control, unit sibling directly
            # after it. The gauges are APPENDED after all of them.
            label = '<label for="%s">%s</label>' % (
                escape_html(config_page.WAKE_INTERVAL_INPUT_ID),
                escape_html(i18n.t("Wake interval (seconds)")))
            unit = ('<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
                    % escape_html(config_page.WAKE_INTERVAL_UNIT_LABEL))
            if label not in markup or unit not in markup:
                return False, "%s: the B17 label or the unit sibling changed" % name
            if markup.index(label) > markup.index(element):
                return False, "%s: the label is no longer ABOVE the control (B17)" % name
            if markup.index(unit) != markup.index(element) + len(element):
                return False, (
                    "%s: the unit sibling no longer sits immediately after the input — something "
                    "was inserted between them" % name)
            gauge_at = markup.find('id="%s"' % config_page.WAKE_GAUGE_FRESHNESS_ID)
            if owes_gauges and gauge_at == -1:
                return False, "%s: the gauges did not render" % name
            if not owes_gauges and gauge_at != -1:
                return False, (
                    "%s: a gauge rendered for a value the field itself refuses to show — that "
                    "is the card inventing a subject" % name)
            if gauge_at != -1 and gauge_at < markup.index(unit):
                return False, (
                    "%s: a gauge renders BEFORE the control it describes — they are appended "
                    "after the error block, which is what makes the rest of the card an "
                    "untouched prefix" % name)
        # A STORED value below the floor still renders both gauges off
        # the value the FIELD will hold, which is nothing — so nothing
        # claims a cadence that was never set.
        # The error block still attaches to the field, with the gauges
        # after it.
        with_error = config_page.wake_interval_group(
            600, errors={"wake_interval_s": "Enter a whole number of seconds."},
            submitted={"wake_interval_s": "900"}, battery_rows=_FALLING)
        # LOCATED BY ITS OWN ELEMENT, never by the bare id string: the
        # input's aria-describedby NAMES that id too, and the first
        # version of this clause found THAT — so it read a position
        # inside the input tag and passed against the gauges rendered
        # between the input and its error message, which is the one
        # arrangement it exists to refuse (measured; see the SUMMARY's
        # vacuity section).
        error_block = re.search(
            r'<p class="field-error[^"]*" id="wake-interval-s-error"', with_error)
        if not error_block:
            return False, "the field error block no longer renders"
        gauge_at = with_error.find('id="%s"' % config_page.WAKE_GAUGE_BATTERY_ID)
        if gauge_at == -1:
            return False, "the gauges did not render beside a rejected save's usable echo"
        if gauge_at < error_block.start():
            return False, (
                "a gauge renders between the input and its own error message (gauge at %d, "
                "error block at %d) — the message has to read as attached to the control it is "
                "about" % (gauge_at, error_block.start()))
        return True, ""
    check(
        "the two gauges are an ADDITION: across five argument shapes (in band, stored below the "
        "60s floor, stored above the ceiling, never set, and a rejected save's raw echo) the "
        "<input type=\"number\"> is byte-identical to its pre-plan output — same id, name, min, "
        "max and placeholder, the value attribute present exactly when the guard admits it and "
        "absent otherwise (an out-of-range value blocks submission of the ENTIRE form) — with "
        "B17's label still above it, the unit sibling still immediately after it, the error "
        "block still attached, and both gauges appended after all of them "
        "(CFG-49/D-07/B17, 25-05-PLAN.md Task 1)",
        _the_gauges_are_an_addition_and_the_number_input_is_untouched)

    # ------------------------------------------------------------------
    # 25-05-PLAN.md Task 2 (CFG-49/CFG-52): the gated range, and the
    # seam it shares with the one script.
    # ------------------------------------------------------------------

    def _the_range_is_gated_nameless_and_bounded_by_device_config():
        """CFG-49/CFG-52 (25-05-PLAN.md Task 2): the range may never
        become a second source of truth, and it may never widen what the
        number input enforces.

        `name` is the attribute a future editor adds by reflex — it is
        what every other input on this page carries — and a named range
        would post a SECOND `wake_interval_s` on every save, with
        whichever arrived last winning, silently. So it is asserted
        directly rather than inferred from "the form posts one value".
        """
        markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
        tag = re.search(r'<input type="range"[^>]*>', markup)
        if not tag:
            return False, "no <input type=\"range\"> renders on the card"
        element = tag.group(0)
        if re.search(r"\bname=", element):
            return False, (
                "the range carries a name (%s) — it would post a second value for the same "
                "setting and whichever arrived last would win, silently" % element)
        if "role=" in element:
            return False, (
                "the range carries a role (%s) — a native range input IS a slider, with its own "
                "aria-valuenow and its own keyboard model; role=\"slider\" on top of that is the "
                "double-role error" % element)
        # THE BOUNDS ARE READ FROM THE MODULE, never restated: one
        # control must not accept what the other, and
        # save_device_config()'s own server-side re-check, reject.
        for attr, expected in (("min", device_config.WAKE_INTERVAL_MIN_S),
                               ("max", device_config.WAKE_INTERVAL_MAX_S),
                               ("step", config_page.WAKE_SLIDER_STEP_S),
                               ("value", 600)):
            if ('%s="%d"' % (attr, expected)) not in element:
                return False, (
                    "the range's %s is not %d — %s" % (attr, expected, element))
        if config_page.WAKE_SLIDER_STEP_S != config_page.WAKE_GAUGE_SECONDS_PER_MINUTE:
            return False, (
                "the slider steps by %d s while the gauges speak in %d-second minutes — every "
                "position the slider can reach has to be a whole number of minutes, or the "
                "sentences round and the reader sees a number that does not match the field"
                % (config_page.WAKE_SLIDER_STEP_S, config_page.WAKE_GAUGE_SECONDS_PER_MINUTE))
        # The accessible name is its OWN, and it points at the gauges.
        for needed in ('aria-label="%s"' % escape_html(i18n.t(config_page.WAKE_SLIDER_LABEL)),
                       'aria-describedby="%s %s"' % (config_page.WAKE_GAUGE_FRESHNESS_ID,
                                                     config_page.WAKE_GAUGE_BATTERY_ID)):
            if needed not in element:
                return False, "the range is missing %r — %s" % (needed, element)
        if i18n.t(config_page.WAKE_SLIDER_LABEL) == i18n.t("Wake interval (seconds)"):
            return False, (
                "the range and the number input share one accessible name — a screen-reader "
                "visitor cannot tell which of the two they are on")
        # EVERY element carrying the wrapper attribute carries the gate
        # class, AND the range itself lives inside one. The second half
        # is what a wrapper-only scan is blind to.
        for tag_match in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
            text = tag_match.group(0)
            if layout.VALUE_CONTROL_ATTR not in text:
                continue
            if layout.JS_GATE_CLASS not in text:
                return False, (
                    "an element carries %s outside the %r gate: %s"
                    % (layout.VALUE_CONTROL_ATTR, layout.JS_GATE_CLASS, text))
        gate_at = markup.find(layout.JS_GATE_CLASS)
        gate_end = markup.find("</div>", gate_at)
        if not (gate_at != -1 and gate_at < markup.index(element) < gate_end):
            return False, (
                "the range is rendered outside the gated wrapper (gate at %d, range at %d, "
                "wrapper closes at %d) — a script-only affordance rendered without the gate "
                "shows permanently whenever the script does not run"
                % (gate_at, markup.index(element), gate_end))
        if markup.count('<input type="range"') != 1:
            return False, "the card renders %d ranges" % markup.count('<input type="range"')
        # NOT A LIVE REGION, anywhere on this card (CFG-52): the gauges
        # change on every step of a drag, and a live region would
        # re-announce the identical phrase continuously — the defect
        # Phase 23 hit with its three switches.
        # (`role="alert"` is deliberately NOT in this list: the field's
        # own error message wears it, renders only on a rejected save,
        # and says something once rather than on every step.)
        for banned in ("aria-live", 'role="status"'):
            if banned in markup:
                return False, (
                    "the wake-interval card carries %r — the gauges move on every step of a "
                    "drag and would flood a screen reader" % banned)
        # AND NOTHING AT ALL when there is no saved interval: the range
        # would otherwise default to the midpoint of its own band, which
        # is a fabricated position a drag would then SAVE.
        empty = config_page.wake_interval_group(None, battery_rows=_FALLING)
        if "<input type=\"range\"" in empty or layout.VALUE_CONTROL_ATTR in empty:
            return False, (
                "a range renders with no saved interval — a range with no value attribute sits "
                "at the midpoint of its band, which is a number nobody chose and which one drag "
                "would save")
        return True, ""
    check(
        "the wake-interval range is NAMELESS (a named one would post a second value for the "
        "same setting and the last to arrive would win), carries no role=\"slider\" on top of a "
        "native slider, takes its min/max from server.device_config rather than a literal, steps "
        "by exactly the minute both gauges speak in, has its own accessible name and describes "
        "itself by the two gauges, renders ONLY inside 25-01's .js gate and only when there is a "
        "saved interval to start from, and nothing on the card is a live region "
        "(CFG-49/CFG-52/T-25-05-D, 25-05-PLAN.md Task 2)",
        _the_range_is_gated_nameless_and_bounded_by_device_config)

    def _the_readout_seam_this_card_declares_is_the_one_the_script_reads():
        """CFG-49 (25-05-PLAN.md Task 2): both halves of a seam, pinned
        together — the markup this page emits and the script that
        consumes it.

        A rename on either side alone is a gauge that renders once and
        then never moves again, which no string comparison on the
        rendered page would notice: the sentence would be perfectly
        correct at load and permanently stale afterwards.
        """
        markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
        with open(os.path.join(HERE, "static", "value-controls.js"),
                  encoding="utf-8") as fh:
            script = fh.read()
        # 1. Every attribute this card emits is one the script names.
        for attr in (layout.VALUE_CONTROL_INPUT_ATTR, layout.VALUE_CONTROL_READOUT_ATTR,
                     layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
                     layout.VALUE_CONTROL_READOUT_SCALE_ATTR,
                     layout.VALUE_CONTROL_READOUT_BASE_ATTR):
            if attr not in markup:
                return False, "the card emits no %r" % attr
            if ('"%s"' % attr) not in script:
                return False, (
                    "value-controls.js never names %r, so the markup's own attribute is read by "
                    "nothing and the gauge is correct at load and stale for ever after" % attr)
        # 2. The readouts name the field the form actually posts.
        for match in re.finditer(
                r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR), markup):
            if match.group(1) != config_page.WAKE_INTERVAL_FIELD_NAME:
                return False, (
                    "a readout describes %r, which is not the field this form posts (%r)"
                    % (match.group(1), config_page.WAKE_INTERVAL_FIELD_NAME))
        # 3. THE SCRIPT ROUNDS THE SAME WAY THE SERVER DOES. Both state
        #    a BOUND, so both take the CEILING; a floor on either side
        #    would print "at most 1 min" for a 90-second cadence, which
        #    is false.
        if "Math.ceil(value / scale)" not in script:
            return False, (
                "value-controls.js does not take the CEILING of value/scale — the server does "
                "(_wake_minutes()), and a script that floored it would print a bound that is "
                "not true")
        # 4. A WRAPPER WITH A MIRROR TAKES NO GESTURES FROM THE SCRIPT.
        #    Without this the pointerdown handler's own preventDefault()
        #    cancels the native thumb drag and the slider is immovable by
        #    pointer, with every string comparison still green.
        if "function steeredHere(wrapper)" not in script:
            return False, (
                "value-controls.js has no mirror guard — its pointerdown handler calls "
                "preventDefault(), which cancels a native range's own thumb drag outright")
        for listener in ("keydown", "pointerdown", "pointermove"):
            block = script[script.index('document.addEventListener("%s"' % listener):]
            block = block[:block.index("});")]
            if "steeredHere(wrapper)" not in block:
                return False, (
                    "value-controls.js's %s listener does not stand aside for a wrapper with a "
                    "mirror — a native range would be stepped twice per key or pinned in place "
                    "by a prevented default" % listener)
        # 5. The BASE is the saved interval, so the relative clause says
        #    nothing at all until the visitor proposes something else —
        #    which is what every page load and every scripts-blocked
        #    render is.
        base = re.search(r'%s="(\d+)"' % re.escape(layout.VALUE_CONTROL_READOUT_BASE_ATTR),
                         markup)
        if not base or int(base.group(1)) != 600:
            return False, (
                "the relative readout's base is %r, not the saved interval — a readout with no "
                "base compares the saved value with itself on every page load"
                % (base.group(1) if base else None,))
        span = re.search(
            r'<span %s="[^"]*"[^>]*></span>' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR),
            markup)
        if not span:
            return False, (
                "the relative clause is not EMPTY at the saved value — the server renders the "
                "saved interval against itself, and 'every 10 min instead of every 10 min' "
                "would be noise on every page load")
        # 6. THE HONESTY CLAUSE, structural: no readout template on this
        #    card contains a days figure or its wording, so no script
        #    that only substitutes into templates can invent one.
        days_words = [w for w in (i18n.t(config_page.WAKE_BATTERY_DAYS_TEXT),
                                  i18n.t(config_page.WAKE_BATTERY_DAY_TEXT))]
        for match in re.finditer(
                r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_TEXT_ATTR), markup):
            template = html.unescape(match.group(1))
            for wording in days_words:
                stem = wording.split(layout.VALUE_CONTROL_TEXT_TOKEN)[-1].strip()
                if stem and stem in template:
                    return False, (
                        "a readout template carries the days wording (%r) — the absolute figure "
                        "is server-rendered from observed history, and a template containing it "
                        "is a script that can invent one" % template)
        return True, ""
    check(
        "the readout seam is pinned from BOTH sides: every attribute this card emits is named in "
        "companion/static/value-controls.js and vice versa, every readout describes the field "
        "the form actually posts, the script takes the same CEILING the server does (a floor "
        "would print a bound that is false), all three gesture listeners stand aside for a "
        "wrapper holding a native mirror (without which preventDefault cancels the thumb drag), "
        "the relative clause's base is the saved interval so it renders EMPTY until something "
        "else is proposed, and no readout template contains the days wording at all — so a "
        "script that only substitutes into templates cannot invent a figure the server declined "
        "to state (CFG-49/T-25-05-C, 25-05-PLAN.md Task 2)",
        _the_readout_seam_this_card_declares_is_the_one_the_script_reads)

    # 30-03-PLAN.md Task 1 (CFG-85): three checks used to live in this
    # region — _the_departures_grid_is_the_one_renderer_presented_as_a_
    # strip, _the_carousel_dots_are_real_colours_and_the_strip_rules_
    # are_declared, and _the_full_grid_sits_behind_a_native_details_and_
    # the_pagers_behind_the_gate — all three pinned the retiring
    # scroll-snap-strip/pager/dots-row carousel markup directly
    # (THEME_CAROUSEL_*, .theme-chip-grid--strip, .theme-carousel__*).
    # RETIRED OUTRIGHT (no ledger row — the strip/pager/dots-row shape
    # itself has no surviving property once CFG-85's accordion replaces
    # it), EXCEPT for one property re-homed here as a new check: the
    # whole Display page must carry exactly len(THEME_IDS) radios named
    # "theme" (ONE set, so the page can never show one setting in two
    # disagreeing places) — written with no reference to a strip, a
    # pager, a gate or a disclosure, so it survives the rebuild.

    def _the_display_page_carries_exactly_one_radio_set_per_theme_field():
        page = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        theme_count = len(device_config.THEME_IDS)
        posted = len(re.findall(r'<input type="radio" name="theme" ', page))
        if posted != theme_count:
            return False, (
                "the Display page renders %d radios named 'theme', expected exactly %d — a "
                "second set sharing that name would still post one value while showing the "
                "setting in two disagreeing places" % (posted, theme_count))
        return True, ""
    check(
        "the whole rendered Display page carries exactly len(device_config.THEME_IDS) radios "
        "named 'theme' — ONE set, computed from the registry at check time, re-homed from the "
        "retiring carousel's own equivalent guard so the page can never show one setting in two "
        "disagreeing places (CFG-85, 30-03-PLAN.md Task 1)",
        _the_display_page_carries_exactly_one_radio_set_per_theme_field)


    # ------------------------------------------------------------------
    # 27-07-PLAN.md Task 1 (CFG-68): THE TRAP CHECK. THEME_CAROUSEL_
    # STRIP_ID used to be a single id literal serving as both the
    # departures strip's own id AND what both pagers' aria-controls
    # named — fine with one carousel, but a SECOND carousel built from
    # the same literal (or from a helper that still defaulted to it)
    # would render two elements sharing one id, which is invalid HTML,
    # and every pager on the page would drive only the FIRST match.
    # _theme_carousel_html() now takes strip_id as a required argument
    # instead (no shared default), which makes that specific collision
    # impossible BY CONSTRUCTION — this check is the proof that holds
    # for every OTHER way a duplicate id could still reach the page
    # (a typo, a copy-pasted call site, anything), because it asserts
    # the property the trap violates directly: id uniqueness across the
    # whole rendered page, not "the carousel ids I expect differ".
    # ------------------------------------------------------------------

    def _the_rendered_settings_page_carries_no_duplicate_id():
        page = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        ids = re.findall(r'\bid="([^"]*)"', page)
        if not ids:
            return False, (
                "found no id=\"...\" attributes at all on the rendered Display page — this scan "
                "would pass against a page with none, which measures nothing")
        seen = {}
        for value in ids:
            seen[value] = seen.get(value, 0) + 1
        duplicates = {value: count for value, count in seen.items() if count > 1}
        if duplicates:
            # ONE named example, not the whole dict — a message a future
            # reader can act on immediately, matching this file's own
            # convention of naming the ACTUAL offending value rather
            # than a summary of how many things are wrong.
            dup_id, dup_count = sorted(duplicates.items())[0]
            return False, (
                "id=%r appears %d times on the rendered Display page — every id-based lookup "
                "(aria-controls, a <label for=>, aria-labelledby, document.getElementById) "
                "resolves to the FIRST match silently, so a duplicate id is not a cosmetic "
                "defect: whichever control names %r second is driving or describing the FIRST "
                "one instead of itself" % (dup_id, dup_count, dup_id))
        return True, ""
    check(
        "the rendered Display page carries no duplicate id anywhere — asserted as page-wide id "
        "uniqueness (THE property the THEME_CAROUSEL_STRIP_ID trap violates), never as 'the "
        "carousel ids I expect differ', with a failure message naming the duplicated id and how "
        "many times it appeared (CFG-68, 27-07-PLAN.md Task 1)",
        _the_rendered_settings_page_carries_no_duplicate_id)

    # --- 27-03-PLAN.md Task 1 (CFG-64) -------------------------------

    def _the_native_submit_is_emitted_unconditionally_on_every_render():
        """CFG-64: the no-JS floor is kept BY CONSTRUCTION, not by a
        visibility rule — the native submit carrying
        STATIC_SAVE_FALLBACK_ATTR must be reachable through every code
        path render() has, with no conditional of any kind governing its
        presence. Two proofs, not one, because a rendering-only proof
        would pass against a page whose SOURCE has a branch that merely
        never gets exercised by today's three scopes, and a source-only
        proof would pass against a render() that formats the attribute
        into a sub-template some caller forgets to include.

        THE SOURCE PROOF: render() has exactly one `return` statement (a
        second return would be a second, unproven code path), that
        return is a direct statement of the function's own body — never
        nested inside an `if`/`for`/`while`/`try` — and
        STATIC_SAVE_FALLBACK_ATTR appears exactly once inside it as a
        bare name, never behind an `ast.IfExp` (a ternary), which is the
        one shape that would make its presence depend on a runtime
        condition.

        THE RENDER PROOF: render() is actually called for every scope
        the page supports (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) and
        each rendering carries EXACTLY ONE `data-static-save-fallback`
        occurrence — never zero (the submit is missing) and never two or
        more (a second, competing save control). One check over all
        three scopes, not one per scope: the relationship under test is
        "every scope has it", and a per-scope check would let a future
        fourth scope ship with no proof at all.
        """
        with open(os.path.join(HERE, "pages", "config_page.py"), encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source)
        render_fn = next(
            (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "render"),
            None)
        if render_fn is None:
            return False, "config_page.py defines no top-level render() function any more"
        returns = [n for n in ast.walk(render_fn) if isinstance(n, ast.Return)]
        if len(returns) != 1:
            return False, (
                "expected exactly one return statement inside render(), found %d — a second "
                "return is a second code path, and the one that reaches "
                "STATIC_SAVE_FALLBACK_ATTR would no longer be the only one" % len(returns))
        only_return = returns[0]
        if only_return not in render_fn.body:
            return False, (
                "render()'s one return statement is NESTED inside a conditional/loop/try block "
                "of the function body — the submit's emission would then be reachable on some "
                "paths and not others, exactly the branch this check exists to rule out")
        carriers = [
            n for n in ast.walk(only_return.value)
            if isinstance(n, ast.Name) and n.id == "STATIC_SAVE_FALLBACK_ATTR"]
        if not carriers:
            return False, (
                "render()'s one return statement never names STATIC_SAVE_FALLBACK_ATTR at all "
                "— the submit is not part of what this function returns")
        if len(carriers) != 1:
            return False, (
                "STATIC_SAVE_FALLBACK_ATTR appears %d times in render()'s return — expected "
                "exactly one submit" % len(carriers))
        for node in ast.walk(only_return.value):
            if isinstance(node, ast.IfExp) and carriers[0] in ast.walk(node):
                return False, (
                    "STATIC_SAVE_FALLBACK_ATTR is reached through a ternary inside render()'s "
                    "return — its presence would then depend on a runtime condition, never "
                    "unconditional")
        base_ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
            rendered = config_page.render(base_ctx, scope=scope)
            count = rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR)
            if count != 1:
                return False, (
                    "expected exactly one %r occurrence on scope=%r, found %d — the native "
                    "submit must render unconditionally, once, on every scope"
                    % (config_page.STATIC_SAVE_FALLBACK_ATTR, scope, count))
        return True, ""
    check(
        "the native submit carrying STATIC_SAVE_FALLBACK_ATTR is emitted UNCONDITIONALLY — "
        "render() has exactly one return statement, it is never nested inside a branch, and "
        "the attribute reaches it as a bare name rather than through a ternary — AND every one "
        "of the three scopes (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) renders it exactly once, so "
        "there is no code path, past or future, that can omit the no-JS save floor (CFG-64, "
        "27-03-PLAN.md Task 1)",
        _the_native_submit_is_emitted_unconditionally_on_every_render)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-page: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
