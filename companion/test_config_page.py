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
from server import device_config, history_db  # noqa: E402
from server.plane import calendar_rules  # noqa: E402

TEST_PASSWORD = "config-page-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 48


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

    _STATIC_DIR = os.path.join(REPO_ROOT, "companion", "static")

    def _read_static(name):
        with open(os.path.join(_STATIC_DIR, name)) as fh:
            return fh.read()

    # Base render() contexts still used by part 05's own checks below (parts
    # 01-04 of this chain used to define these too - kept here, unmodified,
    # now that migration has moved their own callers into native pytest
    # modules; 33-MIGRATION-RULES.md section 1: "setup that remaining checks
    # still need stays").
    _CALENDAR_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "now": "2026-09-07T09:12:04+00:00",
    }

    _TASK2_BASE_CTX = {
        "device_config": {
            "display_enabled": True, "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        },
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
    }

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
