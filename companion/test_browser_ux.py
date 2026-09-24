#!/usr/bin/env python3
"""companion/test_browser_ux.py — the D-02 browser-level harness
(22-01-PLAN.md Task 1/3, 22-CONTEXT.md D-01/D-02).

Every other harness in this repository compares rendered HTML strings.
None of them parses the real DOM, runs any JavaScript, or fires a real
`click`/`change` event — which is exactly why B1 (companion/static/
dirty-state.js listening on `<form>` itself, never seeing a `change`
from a field attached to it only via `form="settings-form"`) shipped
undetected: every field the bug affected still round-tripped correctly
through `form.elements` in a string-comparison harness, because that
collection is server-side-invisible. This file is the first harness in
the project that drives a real Chromium tab against a real running
`companion/app.py` subprocess, so this exact class of defect can be
pinned by a machine.

Follows every sibling harness's own conventions exactly: a `check(name,
fn)` helper with the same result-collecting shape, a module-level
`EXPECTED_CHECK_COUNT`, and a `main()` returning 0 or 1 — so the pytest
legacy-harness shim (companion/test_legacy_harness_shim.py, 32-13-PLAN.md)
needs zero special-casing for this file.

Two skip gates, both returning exit 0 with a printed `SKIP` line naming
this file and the exact remedy — never a failure — mirroring how the
suite already tolerates the documented macOS Pillow/FreeType digest
mismatch: a missing OPTIONAL capability is a skip, not a red build.
  1. `playwright` itself is not installed (a dev-only dependency, see
     server/requirements-dev.txt's own header comment).
  2. `playwright` is installed but no Chromium binary has been
     downloaded (`python -m playwright install chromium` was never run).

Security constraint, enforced by this file's own code, not only stated
here: every check below navigates ONLY to `Harness.base_url()` — a
`127.0.0.1:<ephemeral-port>` URL naming the exact subprocess this file
itself launched via `companion_app_server.LegacyHarness`. No external
URL is ever constructed or navigated to anywhere in this file.

Reuses `companion_app_server.LegacyHarness` for the subprocess-under-
test rather than inventing a second subprocess pattern (22-RESEARCH.md
Pattern 3): a free loopback port, an isolated `tempfile.mkdtemp()` state
directory, a real `companion/app.py` subprocess, a startup readiness
poll, and a `stop()` that SIGTERMs then SIGKILLs the process group
(33-19-PLAN.md Task 1: repointed from the retired copy of `Harness` the
companion-app harness used to export).

`seed_state_dir()` below reproduces 22-AUDIT.md's own methodology
fixture (36 runway events over 17h, ~40 days of battery history, 3
gallery renders, 2 unresolved prefixes, 1 manual resolution, 2 colour
rules, wake_interval_s 300, quiet hours 23:00-07:00) through the exact
modules companion/app.py and server/poll_loop.py themselves use to
write this data (server/history_db.py, server/device_config.py,
server/plane/manual_resolutions.py, server/plane/colour_rules.py,
server/poll_loop.py's own `_save_to_gallery()`) — never a hand-written
JSON/SQL fixture, which would silently drift from the real writers'
on-disk shape. Deterministic: every timestamp is derived from one fixed
`SEED_BASE_TS`, never `datetime.now()` captured twice.

Battery cadence note: 22-AUDIT.md's own methodology paragraph used a
3h-then-5min cadence across 40 days (order of 10,000 rows) — this
harness instead writes one reading per day across the same 40-day span.
Nothing this plan's checks assert reads the battery trend at all: the
higher-fidelity cadence would only slow every future run of this
already-the-slowest-harness-by-construction file for no assertion
gained. The 40-DAY SPAN itself (not the sub-day cadence) is what
several `server/history_db.py` call sites and `companion/pages/
health_page.py`'s own windowing logic key off, and that is preserved
exactly.

Stdlib + playwright (dev-only, see server/requirements-dev.txt) + PIL
(already a server dependency, transitively imported via
server.plane.render — used here only to hand a real `Image` to
`poll_loop._save_to_gallery()`, never to build a fixture PNG by another
path). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_browser_ux.py
"""
import collections
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# test-support/ (companion_app_server, for LegacyHarness/TEST_PASSWORD) -
# this file runs as a standalone script (server/.venv/bin/python3
# companion/test_browser_ux.py), never through pytest, so conftest.py's
# own sys.path insert never runs for it.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from companion import auth, i18n, layout  # noqa: E402
from companion_app_server import LegacyHarness as Harness  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page, config_page, history_page)
from server import device_config, history_db  # noqa: E402
from companion import illustration_normalize  # noqa: E402
from server.plane import illustrations, manual_resolutions  # noqa: E402
# 31-01-PLAN.md Task 3: everything below was module-level in this file
# through 31-01's own predecessor commit; it now lives in
# companion.test_browser_ux_helpers so plans 02/03's extracted sibling
# harnesses can import it too, without duplicating ~2,600 lines.
# 31-02-PLAN.md: VIEWPORT_WIDTH_NARROW, _RING_INK_PROBE and
# _TILE_CONTENT_PROBE dropped from this import — their only call sites
# left with the drawings group for
# companion/test_browser_ux_health_drawings.py.
# MERGE NOTE (origin/main -> claude/phase-30-aspect-rebuilt): two names
# move relative to origin/main's own version of this list, both because
# Phase 30 changed WHO CALLS WHAT in this file and for no other reason.
# _SUBMIT_PROBE is ADDED: 31-01 left it out because this file's only
# remaining consumer at the time was inside the extracted preamble, and
# 30-04's calendar-row check (which resolves the calendar palette radio's
# own .form property in a live browser) is a new consumer that stayed
# behind. _operate_with_keyboard is REMOVED: all three of its call sites
# in origin/main's version of this file were the carousel keyboard/pager
# checks 30-03 retired and ledgered to 30-08, whose accordion-shaped
# replacements drive the keyboard through the native radiogroup instead —
# grepped whole-file before dropping it, zero remaining consumers, the
# same retire-with-your-last-consumer discipline 30-03 applied to the
# carousel selector/probe block. It remains exported by the helpers
# module for the two extracted sibling harnesses that still call it.
from companion.test_browser_ux_helpers import (  # noqa: E402
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _await_upload_zone, _bar_text, _click_control,
    _commit_field, _display_page_height, _drop_files,
    _handle_sel, _in_both_themes, _login, _no_js_page,
    _persist_without_js, _quiet_arc_minutes, _save_via_bar, _SUBMIT_PROBE,
    _set_ui_theme, _upload_without_js, _upload_zone_state, _wait_for_bar,
    _wait_for_bar_hidden, seed_state_dir,
)

EXPECTED_CHECK_COUNT = 38


# --- The view-transition names this app declares (23-04-PLAN.md Task 2,
# D10/CFG-33) and, for each, the authenticated routes on which EXACTLY
# ONE element must carry it. Both halves are asserted: the declared set
# is compared against what the served stylesheet actually declares (so a
# name added, renamed or dropped there fails here rather than silently
# widening the contract), and the routes are compared against the
# rendered documents.
#
# The route lists are structural facts, not preferences, and each one is
# the REASON its selector was chosen over an obvious alternative:
#   .dashboard-sidebar  the <aside>, rendered once per authenticated
#                       document. NOT a shared navigation class: three
#                       navigation copies (sidebar, preferences panel,
#                       tab bar) are in the DOM of every one of these
#                       pages simultaneously, hidden from each other only
#                       by a media query, so a name on a class they share
#                       would be declared three times in one document.
#   .page-title         page_header()'s single <h1>.
#   .preview-frame__image  Home's frame picture, the app's ONLY render
#                       site of that class — hence the one-route list,
#                       which a plan that renders it elsewhere must widen
#                       here on purpose.


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "SKIP companion/test_browser_ux.py — playwright not installed "
            "(dev-only dependency; run "
            "`pip install -r server/requirements-dev.txt` to enable this harness)")
        return 0

    try:
        with sync_playwright() as p:
            probe = p.chromium.launch()
            probe.close()
    except Exception as exc:
        print(
            "SKIP companion/test_browser_ux.py — Chromium launch failed (%r); "
            "run `python -m playwright install chromium`" % (exc,))
        return 0

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

    harness = Harness()
    seed_state_dir(harness.tmpdir)
    harness.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                # 23-05-PLAN.md Task 3 (D14/CFG-34): the freshness line's
                # own selector and its settle window, shared by the
                # remaining ticker-family checks below (33-22-PLAN.md
                # moved the checks that used to sit beside this
                # definition into companion/test_browser_ux_02.py, but
                # this one still reads the same element).
                TICK_SETTLE_MS = 2200
                FRESHNESS_AGE = ".page-header__freshness time[data-relative]"

                def _an_expired_countdown_reads_waiting_and_never_a_warning():
                    # No page renders a countdown yet — 23-06's next-wake
                    # line is relative_time_html(countdown=True)'s first
                    # consumer — so the element is seeded into a real
                    # rendered page here rather than waited for. That is
                    # deliberate and it is not a weaker test of THIS
                    # plan's subject: the script re-queries the document
                    # on every tick, so a seeded element goes through the
                    # shipped code path exactly as a server-rendered one
                    # will. The SERVER half (an expired countdown renders
                    # the waiting wording with no JS at all) is pinned in
                    # the companion-app harness instead, where the
                    # renderer can be called directly.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page = context.new_page()
                            _login(page, base_url)
                            page.goto(base_url + "/health")
                            page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
                            page.evaluate(
                                "() => {"
                                "  var el = document.createElement('time');"
                                "  el.setAttribute('id', 'seeded-countdown');"
                                "  el.setAttribute('data-relative', '');"
                                "  el.setAttribute('data-relative-countdown', '');"
                                "  el.setAttribute('datetime',"
                                "    new Date(Date.now() - 120000).toISOString());"
                                "  el.textContent = 'seeded';"
                                "  document.querySelector('main').appendChild(el);"
                                "}")
                            page.wait_for_timeout(TICK_SETTLE_MS)
                            seen = page.eval_on_selector(
                                "#seeded-countdown",
                                "el => [el.textContent, el.getAttribute('class') || '']")
                            text, klass = seen[0], seen[1]
                            expected = page.eval_on_selector(
                                "body",
                                "el => el.getAttribute('data-relative-waiting')")
                            if not expected:
                                return False, (
                                    "lang=%s: the page renders no waiting wording on <body> for "
                                    "the script to read" % lang)
                            if text != expected:
                                return False, (
                                    "lang=%s: expected a countdown whose instant has passed to "
                                    "read the server's own waiting wording %r, got %r — it must "
                                    "not turn itself into an age"
                                    % (lang, expected, text))
                            if " ago" in text or "il y a" in text:
                                return False, (
                                    "lang=%s: an expired countdown became an age: %r"
                                    % (lang, text))
                            if "is-breathing" not in klass.split():
                                return False, (
                                    "lang=%s: expected an expired countdown to breathe, got "
                                    "class=%r" % (lang, klass))
                            for verdict in ("warn", "error", "alert", "danger", "late"):
                                if verdict in klass:
                                    return False, (
                                        "lang=%s: an expired countdown carries NO warn class — "
                                        "a wake that has not happened yet is not a fault (the "
                                        "false alarm X2 removed), got class=%r" % (lang, klass))
                            # And the breathing is motion this app's own
                            # reduced-motion floor already covers: the
                            # class resolves to the one animation the
                            # stylesheet defines.
                            animation = page.eval_on_selector(
                                "#seeded-countdown",
                                "el => getComputedStyle(el).animationName")
                            if animation != "skypane-pulse":
                                return False, (
                                    "lang=%s: expected the breathing class to resolve to the "
                                    "stylesheet's one animation, got %r" % (lang, animation))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a countdown whose instant has already passed reads the server's own "
                    "translated waiting wording in BOTH languages, never an age, gains the "
                    "breathing class and no warn/error/alert class at all, and that class "
                    "resolves to the one animation the stylesheet defines (D14/CFG-34, "
                    "23-05-PLAN.md Task 3)",
                    _an_expired_countdown_reads_waiting_and_never_a_warning)

                # --- 23-06-PLAN.md Task 3 (D1/CFG-35): the three skips,
                # and the number D-12 was written to protect.
                #
                # HOW A REFRESH IS FORCED, once, for every check below.
                # The loop's own cadence is 45 seconds and no test may
                # wait that long, so these checks drive the loop's
                # CATCH-UP path instead: freshness.js re-arms on
                # visibilitychange and refetches immediately when more
                # than one interval has passed since the document was
                # generated. Date.now is shifted forward for the
                # duration of the dispatch and restored on the next
                # statement — doRefresh() is called synchronously inside
                # the listener, so the shift is over before anything
                # else can observe it. What is simulated is the CLOCK;
                # what is exercised is the shipped script's own
                # listener, its own elapsed comparison and its own
                # guards, unmodified.
                #
                # Every request assertion COUNTS REQUESTS rather than
                # reading the DOM. "Zero requests" is the contract D-12
                # protects, and a DOM-based proxy would pass on a page
                # that fetched and then declined to swap — a different
                # and much worse behaviour.

                REFRESH_SETTLE_MS = 1200

                def _force_refresh(page):
                    page.evaluate(
                        "() => {"
                        "  var real = Date.now;"
                        "  Date.now = function () { return real() + 600000; };"
                        "  try {"
                        "    document.dispatchEvent(new Event('visibilitychange'));"
                        "  } finally {"
                        "    Date.now = real;"
                        "  }"
                        "}")

                def _count_document_requests(page, url):
                    """A live counter of fetches of `url` made by the page
                    itself. Returns a zero-argument reader."""
                    seen = []
                    page.on("request", lambda request: (
                        seen.append(request.url)
                        if request.url.split("?")[0] == url else None))
                    return lambda: len(seen)

                def _mark(page, selector, name):
                    """Tag a live node with a JS expando — the only handle
                    that proves NODE IDENTITY across a swap. An attribute
                    would not do: the replacement comes from a second
                    document and would never carry it, so an
                    attribute-based check could not tell "this node
                    survived" from "a node matching the same selector is
                    here"."""
                    page.eval_on_selector(
                        selector, "el => { el.__skypaneProbe = %r; }" % name)

                def _marked(page, selector, name):
                    return page.eval_on_selector(
                        selector, "el => el.__skypaneProbe === %r" % name)

                def _dirty_the_region(page, selector):
                    """Make a live region DIFFER from its freshly-fetched
                    counterpart, so the "this region did not change" skip
                    cannot be what leaves it alone.

                    Without this these checks would be vacuous in the
                    quietest possible way: on a page nothing has changed
                    on, isEqualNode() skips every region anyway, and an
                    assertion that a region survived would pass on a loop
                    with no focus rule and no pending rule at all.
                    """
                    page.eval_on_selector(
                        selector, "el => el.setAttribute('data-probe-dirty', '1')")

                def _a_swap_leaves_the_region_holding_focus_alone():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        region = ".frame-strip"
                        focus_target = ".frame-strip button[type=\"submit\"]"
                        page.eval_on_selector(focus_target, "el => el.focus()")
                        _mark(page, region, "focused-region")
                        _mark(page, focus_target, "focused")
                        _dirty_the_region(page, region)
                        # THE FIRST CONTROL: a refresh that swapped
                        # NOTHING would satisfy "the region survived"
                        # perfectly. The freshness line differs on every
                        # cycle by construction (its pill carries
                        # data-loaded-at, a new instant each time), so it
                        # is the honest witness that a swap happened.
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the focus assertion "
                                "below would prove nothing — the freshness line's own node "
                                "survived a refresh it should not have")
                        if not _marked(page, region, "focused-region"):
                            return False, (
                                "the region holding keyboard focus was REPLACED — a refresh that "
                                "silently moves focus to the top of the document while someone "
                                "is tabbing through a card is A-20's own harm, smaller (D1)")
                        active = page.evaluate(
                            "() => document.activeElement.__skypaneProbe === 'focused'")
                        if not active:
                            return False, (
                                "focus left the element the user was in: document.activeElement "
                                "is no longer that node")
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about FOCUS rather than about that
                        # region: blur, change the region in the same way
                        # again, and it must now be replaced.
                        page.evaluate("() => document.activeElement.blur()")
                        _mark(page, region, "unfocused-region")
                        _dirty_the_region(page, region)
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, region, "unfocused-region"):
                            return False, (
                                "control: the same changed region survived with NOTHING focused "
                                "inside it, so the assertion above was not measuring the focus "
                                "rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Home refresh swaps the regions that changed while leaving the one holding "
                    "keyboard focus untouched — asserted on NODE IDENTITY through a JS expando, "
                    "not on a selector match, because a replaced node matching the same selector "
                    "is exactly the defect — against a control proving another region really was "
                    "swapped in the same cycle (D1/CFG-35, 23-06-PLAN.md Task 3)",
                    _a_swap_leaves_the_region_holding_focus_alone)

                def _a_swap_leaves_a_pending_region_alone():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        # The marker is injected here because plan 23-07
                        # is what sets it in production — the swap rule
                        # lands first, on purpose, so that plan only has
                        # to mark its own control. The element goes
                        # INSIDE the region, not on it, which is the
                        # harder of the two cases the skip handles.
                        region = ".home-status-grid"
                        page.eval_on_selector(
                            region,
                            "el => { var probe = document.createElement('span');"
                            "  probe.setAttribute('data-pending', '');"
                            "  el.appendChild(probe); el.__skypaneProbe = 'pending'; }")
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the pending assertion "
                                "below would prove nothing")
                        if not _marked(page, region, "pending"):
                            return False, (
                                "a region holding an element marked data-pending was replaced — "
                                "that repaints an optimistic control with the server's older "
                                "answer and makes it bounce back under the user's finger "
                                "(T-23-21, the D1-races-D2 rule plan 23-07 depends on)")
                        still_there = page.eval_on_selector_all(
                            region + " [data-pending]", "els => els.length")
                        if still_there != 1:
                            return False, (
                                "expected the pending marker itself to survive the cycle, found "
                                "%d" % (still_there,))
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about the MARKER: drop it, change
                        # the region the same way, and it must now be
                        # replaced. Without this the check passes on a
                        # loop that never swaps that region for any
                        # reason at all.
                        page.eval_on_selector(
                            region,
                            "el => { el.querySelector('[data-pending]').removeAttribute("
                            "  'data-pending');"
                            "  el.__skypaneProbe = 'unmarked'; }")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, region, "unmarked"):
                            return False, (
                                "control: the same changed region survived with the marker "
                                "REMOVED, so the assertion above was not measuring the pending "
                                "rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a region containing a [data-pending] element survives a refresh untouched, by "
                    "node identity, while another region on the same page is swapped in the same "
                    "cycle — the reconciliation rule plan 23-07 sets its marker for, proven before "
                    "it has a marker to set (T-23-21, 23-06-PLAN.md Task 3)",
                    _a_swap_leaves_a_pending_region_alone)

                def _a_dirty_settings_form_stands_the_whole_cycle_down():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")
                        page.wait_for_load_state("networkidle")
                        count = _count_document_requests(page, base_url + "/display")
                        # CONTROL FIRST: with the form clean, the very
                        # same trigger DOES fetch. Without this the
                        # assertion below passes on a page whose loop
                        # never ran for any reason at all.
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        clean_requests = count()
                        if clean_requests < 1:
                            return False, (
                                "control: a clean Display page issued no request at all (%d), so "
                                "the dirty-form assertion below would measure nothing"
                                % (clean_requests,))
                        # 27-04-PLAN.md Task 4 (CFG-63): RETARGETED — a
                        # radio commits (fires change) the instant it is
                        # clicked, which now means the form is clean again
                        # a moment later (auto-save's own optimistic
                        # snapshot advance) — a radio click can no longer
                        # hold this check's own precondition open. The
                        # genuinely uncommitted state this check needs is
                        # a value typed but not yet blurred, read through
                        # window.SkyPaneDirtyState.hasUncommittedEdits() —
                        # the exact predicate freshness.js's own gate now
                        # reads (this plan's own deviation, replacing the
                        # retired bar's liveness+visibility gate).
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.eval_on_selector(quiet_sel, "el => el.focus()")
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.type("03:33")
                        uncommitted = page.evaluate(
                            "() => !!(window.SkyPaneDirtyState "
                            "&& window.SkyPaneDirtyState.hasUncommittedEdits())")
                        if not uncommitted:
                            return False, (
                                "expected the typed-but-uncommitted edit to report unsaved edits "
                                "— this check gates on that same predicate, so a page that never "
                                "reports one would make it vacuous")
                        before = count()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        during_edit = count() - before
                        if during_edit != 0:
                            return False, (
                                "expected ZERO requests while the settings form has unsaved "
                                "edits, counted %d — a page mid-edit should not be fetching and "
                                "diffing itself at all, and a swap landing on a half-edited form "
                                "is B1 with a new cause" % (during_edit,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Display page with a typed-but-uncommitted edit issues ZERO requests when "
                    "the same trigger that fetched on the clean page fires — counted as REQUESTS, "
                    "not inferred from the DOM, because a page that fetched and then declined to "
                    "swap is a different and worse behaviour — against a control proving the clean "
                    "page does fetch (T-23-20/T-23-21, 23-06-PLAN.md Task 3; retargeted from the "
                    "retired save bar's own gate by 27-04-PLAN.md Task 4, CFG-63)",
                    _a_dirty_settings_form_stands_the_whole_cycle_down)

                def _a_hidden_tab_issues_zero_requests_on_all_three_pages():
                    base_url = harness.base_url()
                    for route in ("/", "/display", "/health"):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            page.goto(base_url + route)
                            page.wait_for_load_state("networkidle")
                            count = _count_document_requests(page, base_url + route)
                            # CONTROL: the page really is running a loop.
                            _force_refresh(page)
                            page.wait_for_timeout(REFRESH_SETTLE_MS)
                            if count() < 1:
                                return False, (
                                    "control: %s issued no request when visible (%d), so the "
                                    "hidden-tab assertion below would measure nothing — this "
                                    "page is not running the loop at all"
                                    % (route, count()))
                            # The same limitation 23-05 recorded applies:
                            # neither a second page taking focus nor CDP's
                            # visibility override works in this harness, so
                            # the page's own report is overridden in-page
                            # and a real visibilitychange Event dispatched.
                            # What is simulated is the BROWSER'S REPORT;
                            # what is exercised is the shipped script's own
                            # listener and its own document.hidden reads.
                            page.evaluate(
                                "() => {"
                                "  Object.defineProperty(document, 'hidden',"
                                "    {configurable: true, get: () => true});"
                                "  Object.defineProperty(document, 'visibilityState',"
                                "    {configurable: true, get: () => 'hidden'});"
                                "}")
                            before = count()
                            _force_refresh(page)
                            page.wait_for_timeout(REFRESH_SETTLE_MS)
                            hidden_requests = count() - before
                            if hidden_requests != 0:
                                return False, (
                                    "%s issued %d request(s) while reporting itself hidden — "
                                    "zero from a backgrounded tab is the number D-12 was written "
                                    "to protect, and three pages polling instead of one is only "
                                    "acceptable because of it (T-23-20)"
                                    % (route, hidden_requests))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a tab reporting itself hidden issues ZERO requests on ALL THREE pages that "
                    "now run the loop — counted as requests, each against a control proving the "
                    "same page and the same trigger DO fetch while visible — which is the number "
                    "D-12 was written to protect and the reason three pages polling is acceptable "
                    "at all (T-23-20, 23-06-PLAN.md Task 3)",
                    _a_hidden_tab_issues_zero_requests_on_all_three_pages)

                def _the_picture_fades_only_when_the_picture_changed():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        image = ".preview-frame__image"
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: nothing was swapped, so 'it did not fade' below would "
                                "prove nothing")
                        klass = page.eval_on_selector(
                            image, "el => el.getAttribute('class') || ''")
                        if "is-fading-in" in klass.split():
                            return False, (
                                "the picture faded in on a cycle that brought back the SAME "
                                "picture (class=%r) — a flash every 45 seconds for no "
                                "information is worse than no fade at all" % (klass,))
                        # And now a genuinely different picture: the live
                        # src is changed so the fetched one differs from
                        # it, which is exactly the state a new render
                        # produces.
                        page.eval_on_selector(
                            image, "el => { el.setAttribute('src', el.getAttribute('src')"
                                   " + '?stale=1'); }")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        klass = page.eval_on_selector(
                            image, "el => el.getAttribute('class') || ''")
                        if "is-fading-in" not in klass.split():
                            return False, (
                                "a NEW picture arrived and did not fade in (class=%r) — the fade "
                                "is the only thing that says a render happened" % (klass,))
                        animation = page.eval_on_selector(
                            image, "el => getComputedStyle(el).animationName")
                        if animation != "skypane-fade-in":
                            return False, (
                                "expected the fade class to resolve to the stylesheet's own "
                                "fade-in block, got %r" % (animation,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the frame picture fades in when a NEW render arrives and does NOT animate "
                    "when the same picture is swapped back in — both phases in one check, against "
                    "a control proving a swap happened at all, with the class proven to resolve to "
                    "the stylesheet's own fade-in block (D1+D3, 23-06-PLAN.md Task 3)",
                    _the_picture_fades_only_when_the_picture_changed)

                def _display_still_saves_with_scripts_blocked_at_360px():
                    # THE ONE ASSERTION IN THIS PLAN THAT WOULD CATCH THE
                    # PHASE 22 P0 RECURRING, which is why it lives at
                    # this plan's own commit rather than in the closing
                    # sweep: this plan adds markup to Display's header,
                    # and a wrapper that broke the form= association B1
                    # depends on would make the page unsaveable with
                    # scripts blocked, exactly as B1 did with them on.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")
                            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                return False, "expected the measurement at the 360px contract floor"
                            current = device_config.load_device_config(harness.tmpdir)["theme"]
                            other = next(
                                t for t in device_config.THEME_IDS if t != current)
                            page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % other,
                                "el => el.checked = true")
                            save = page.query_selector(
                                "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                            if save is None:
                                return False, (
                                    "lang=%s: the fallback Save is the ONLY way to save this page "
                                    "with scripts blocked, and it is not rendered" % (lang,))
                            # 28-10-PLAN.md (CFG-77/CFG-78), a direct
                            # consequence of 28-08's own restoration: the
                            # relocated Save button is now inside
                            # .dirty-bar, whose entrance `animation:
                            # skypane-bar-arrive` (style.css) is on the
                            # BASE rule, unconditional on script — it
                            # fires on the very first paint regardless of
                            # scripts being blocked, since CSS animations
                            # are independent of JS. Well past
                            # var(--motion-fast) (180ms): a coordinate
                            # click during that window fails Playwright's
                            # own stability check against a button that
                            # is still translating into place.
                            page.wait_for_timeout(600)
                            with page.expect_navigation():
                                save.click()
                            saved = device_config.load_device_config(harness.tmpdir)["theme"]
                            if saved != other:
                                return False, (
                                    "lang=%s: a Display save did not persist with scripts blocked "
                                    "at 360px — expected theme %r, got %r. This is the P0 Phase "
                                    "22 existed to fix" % (lang, other, saved))
                            # The freshness line this plan added renders
                            # there too, and renders NOTHING that moves.
                            if page.locator(".page-header__freshness").count() != 1:
                                return False, (
                                    "lang=%s: expected exactly one freshness line on a "
                                    "scripts-blocked Display page" % (lang,))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, a Display setting still "
                    "saves through the fallback Save and persists to disk, with the freshness line "
                    "this plan added rendering beside it — the one assertion here that would catch "
                    "the Phase 22 P0 recurring (B1/CFG-38, 23-06-PLAN.md Task 3)",
                    _display_still_saves_with_scripts_blocked_at_360px)

                # --- 23-07-PLAN.md Task 3 (D2/CFG-36): the optimistic
                # switch, proven in a real browser. Three properties no
                # string-comparison harness can see — that the flip
                # lands BEFORE the answer, that it comes back when the
                # answer is bad, and that a refresh arriving mid-flight
                # does not repaint it — plus the scripts-blocked floor
                # for all three switches at 360px in both languages.
                #
                # HOW "BEFORE THE ANSWER" IS MADE A REAL MOMENT. The
                # page's own window.fetch is wrapped in a promise this
                # harness releases by hand, so there is no sleep, no
                # race and no timing assumption anywhere below: between
                # the click and the release the request has genuinely
                # been issued and genuinely has no answer. This is the
                # same discipline the clock override above uses — what
                # is simulated is the TRANSPORT; what is exercised is
                # the shipped script's own ordering, its own attribute
                # writes and its own terminal branches, unmodified.

                SWITCH_SEL = 'form[action="/quick/display"] button[role="switch"]'

                def _hold_fetch(page):
                    """Wrap window.fetch so the next POST hangs until
                    _release_fetch() is called. Returns nothing; the
                    release hook lives on window.

                    POSTs ONLY, and that is load-bearing rather than
                    tidy: freshness.js's refresh loop is a GET through
                    the same window.fetch, and holding it too would stop
                    the very refresh the race check below has to land.
                    Found by that check timing out, not reasoned about
                    in advance."""
                    page.evaluate(
                        "() => {"
                        "  var realFetch = window.fetch;"
                        "  window.__skypaneHeld = null;"
                        "  window.fetch = function (url, opts) {"
                        "    if (!opts || opts.method !== 'POST') {"
                        "      return realFetch(url, opts);"
                        "    }"
                        "    return new Promise(function (resolve, reject) {"
                        "      window.__skypaneHeld = function () {"
                        "        realFetch(url, opts).then(resolve, reject);"
                        "      };"
                        "    });"
                        "  };"
                        "}")

                def _fetch_was_issued(page):
                    return page.evaluate("() => !!window.__skypaneHeld")

                def _release_fetch(page):
                    page.evaluate("() => { window.__skypaneHeld(); }")

                def _switch_state(page, selector=None):
                    return page.eval_on_selector(
                        selector or SWITCH_SEL, "el => el.getAttribute('aria-checked')")

                def _a_switch_flips_before_the_server_answers():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        before = _switch_state(page)
                        if before not in ("true", "false"):
                            return False, (
                                "expected a server-rendered aria-checked on the Screen switch, "
                                "got %r" % (before,))
                        on_disk_before = device_config.load_device_config(
                            harness.tmpdir)["display_enabled"]
                        _hold_fetch(page)
                        page.click(SWITCH_SEL)
                        # THE CONTROL for this check: a request really was
                        # issued. Without it, "the attribute already
                        # changed" would also be satisfied by a script
                        # that flipped the switch and never talked to the
                        # server at all — which is a worse bug than the
                        # one this check is about.
                        if not _fetch_was_issued(page):
                            return False, (
                                "control: no fetch was issued at all, so the assertion below "
                                "would prove nothing about ORDER")
                        during = _switch_state(page)
                        if during == before:
                            return False, (
                                "aria-checked was still %r while the request had no answer — the "
                                "flip is not optimistic, it is waiting for the server, which is "
                                "the whole of what D2 asks for (23-07-PLAN.md Task 3)" % (during,))
                        # The server has NOT been told yet, which is what
                        # makes the line above a statement about order.
                        if device_config.load_device_config(
                                harness.tmpdir)["display_enabled"] is not on_disk_before:
                            return False, (
                                "the stored value changed before the held request was released — "
                                "the hold is not holding and this check is measuring nothing")
                        # In flight: the region is marked, which is the
                        # one thing plan 23-06's swap reads.
                        pending = page.eval_on_selector_all(
                            ".frame-strip [data-pending]", "els => els.length")
                        if pending != 1:
                            return False, (
                                "expected exactly one pending-marked region while the request is "
                                "in flight, found %d — this is the marker 23-06's swap skips and "
                                "the only thing this plan owes that contract" % (pending,))
                        _release_fetch(page)
                        page.wait_for_timeout(600)
                        if _switch_state(page) != during:
                            return False, (
                                "a CONFIRMED flip must stay where it was put, got %r"
                                % _switch_state(page))
                        if page.eval_on_selector_all(
                                ".frame-strip [data-pending]", "els => els.length") != 0:
                            return False, (
                                "the pending marker survived a successful answer — a region whose "
                                "control is settled must go back to being refreshable")
                        if device_config.load_device_config(
                                harness.tmpdir)["display_enabled"] is on_disk_before:
                            return False, "expected the confirmed flip to have persisted to disk"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a switch flips its aria-checked BEFORE the server answers — proven against a "
                    "held request that has genuinely been issued and genuinely has no answer, with "
                    "the stored value still unchanged at that instant — marks exactly one region "
                    "pending while in flight, and on a 204 keeps the flip and clears the marker "
                    "(D2/CFG-36, 23-07-PLAN.md Task 3)",
                    _a_switch_flips_before_the_server_answers)

                def _a_switch_rolls_back_and_announces_on_both_failure_branches():
                    base_url = harness.base_url()
                    for lang, failure_copy in (
                            ("en", layout.QUICK_SWITCH_FAILED_TEXT),
                            ("fr", i18n.t_lang(layout.QUICK_SWITCH_FAILED_TEXT, "fr"))):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/")
                            page.wait_for_load_state("networkidle")
                            # THE CONTROL PHASE. An assertion that a flip
                            # came BACK proves nothing unless the flip
                            # goes out in the first place, and a switch
                            # that never moves satisfies "it was restored"
                            # perfectly. So: prove it lands, then break
                            # the server and prove it returns.
                            start = _switch_state(page)
                            page.click(SWITCH_SEL)
                            page.wait_for_timeout(600)
                            landed = _switch_state(page)
                            if landed == start:
                                return False, (
                                    "lang=%s control: the switch did not move on a WORKING "
                                    "request, so the rollback assertions below would pass on a "
                                    "control that simply never flips" % (lang,))
                            toast_sel = "[%s]" % layout.QUICK_TOAST_ATTR
                            if page.eval_on_selector(toast_sel, "el => el.textContent") != "":
                                return False, (
                                    "lang=%s control: the toast announced something on a "
                                    "SUCCESSFUL flip — it is a failure announcement only"
                                    % (lang,))
                            # Branch 1: a non-OK status.
                            for branch, handler in (
                                    ("a 500 from the server",
                                     lambda route: route.fulfill(status=500, body="")),
                                    ("a network-level failure",
                                     lambda route: route.abort())):
                                page.goto(base_url + "/")
                                page.wait_for_load_state("networkidle")
                                page.route("**/quick/display", handler)
                                try:
                                    known = _switch_state(page)
                                    stored = device_config.load_device_config(
                                        harness.tmpdir)["display_enabled"]
                                    page.click(SWITCH_SEL)
                                    page.wait_for_timeout(800)
                                    if _switch_state(page) != known:
                                        return False, (
                                            "lang=%s, %s: aria-checked stayed at %r instead of "
                                            "rolling back to %r — an optimistic switch that keeps "
                                            "a state the server never accepted is a switch that "
                                            "lies (T-23-26)"
                                            % (lang, branch, _switch_state(page), known))
                                    if page.eval_on_selector_all(
                                            ".frame-strip [data-pending]",
                                            "els => els.length") != 0:
                                        return False, (
                                            "lang=%s, %s: the pending marker was left behind — a "
                                            "region whose control never confirmed would hold "
                                            "itself stale forever" % (lang, branch))
                                    if device_config.load_device_config(
                                            harness.tmpdir)["display_enabled"] is not stored:
                                        return False, (
                                            "lang=%s, %s: the stored value moved on a failed "
                                            "request" % (lang, branch))
                                    announced = page.eval_on_selector(
                                        toast_sel, "el => el.textContent")
                                    if announced != failure_copy:
                                        return False, (
                                            "lang=%s, %s: expected the translated failure copy "
                                            "%r in the toast, got %r"
                                            % (lang, branch, failure_copy, announced))
                                    # V7/T-23-27: no server internal ever.
                                    for internal in ("500", "http", "/quick/", "TypeError"):
                                        if internal in announced:
                                            return False, (
                                                "lang=%s, %s: the toast carries %r — a user-facing "
                                                "failure names no status code, no URL and no "
                                                "server internal" % (lang, branch, internal))
                                    visible = page.eval_on_selector(
                                        toast_sel,
                                        "el => getComputedStyle(el).opacity")
                                    if visible == "0":
                                        return False, (
                                            "lang=%s, %s: the toast carries the right words but "
                                            "is not visible — a live region nobody can see is "
                                            "half an announcement" % (lang, branch))
                                finally:
                                    page.unroute("**/quick/display")
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a switch rolls its aria-checked back, clears its pending marker, leaves the "
                    "stored value alone and announces the TRANSLATED generic failure in a visible "
                    "toast — on a 500 AND on a network-level failure, in English and in French, "
                    "each against a control phase proving the same switch DOES flip and does NOT "
                    "announce on a working request (D2/CFG-36, T-23-26/T-23-27, 23-07-PLAN.md "
                    "Task 3)",
                    _a_switch_rolls_back_and_announces_on_both_failure_branches)

                def _a_refresh_landing_mid_flip_does_not_repaint_the_switch():
                    # THE D1-RACES-D2 RULE, asserted from the D2 side.
                    # 23-06 proved its swap skips a [data-pending] region
                    # using a marker this harness injected by hand; this
                    # is the same rule measured against the marker the
                    # SHIPPED script sets, which is the half 23-06 could
                    # not reach.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        before = _switch_state(page)
                        _hold_fetch(page)
                        page.click(SWITCH_SEL)
                        if not _fetch_was_issued(page):
                            return False, "control: no fetch was issued, so nothing is in flight"
                        optimistic = _switch_state(page)
                        if optimistic == before:
                            return False, "control: the switch did not flip, so nothing is pending"
                        # Focus must leave the strip first. freshness.js
                        # ALSO skips the region holding the active
                        # element, and with focus still on the switch this
                        # check would pass on a loop with no pending rule
                        # at all — vacuous in the quietest possible way.
                        page.evaluate("() => document.activeElement.blur()")
                        _mark(page, ".frame-strip", "strip")
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        # THE CONTROL: a cycle that swapped nothing would
                        # satisfy everything below for free.
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the assertions below "
                                "would prove nothing")
                        if not _marked(page, ".frame-strip", "strip"):
                            return False, (
                                "the strip was REPLACED while a flip was unconfirmed — the "
                                "fetched document still carries the server's older state, so the "
                                "switch would bounce back under the user's finger (T-23-26, the "
                                "D1-races-D2 rule)")
                        if _switch_state(page) != optimistic:
                            return False, (
                                "the optimistic state was repainted by a refresh: expected %r, "
                                "got %r" % (optimistic, _switch_state(page)))
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about the MARKER rather than about
                        # the strip: release, let the marker clear, dirty
                        # the region the same way, and it must now be
                        # replaced.
                        _release_fetch(page)
                        page.wait_for_timeout(600)
                        if page.eval_on_selector_all(
                                ".frame-strip [data-pending]", "els => els.length") != 0:
                            return False, "expected the marker to clear once the answer arrived"
                        _mark(page, ".frame-strip", "settled-strip")
                        _dirty_the_region(page, ".frame-strip")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".frame-strip", "settled-strip"):
                            return False, (
                                "control: the same changed strip survived with NO marker on it, "
                                "so the assertion above was not measuring the pending rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Home refresh landing while a flip is unconfirmed leaves the Frame strip "
                    "untouched — by NODE IDENTITY and by the optimistic aria-checked surviving — "
                    "against one control proving another region really was swapped in the same "
                    "cycle and a second proving the same changed strip IS replaced once the marker "
                    "has cleared, with focus deliberately moved off the strip so the focus skip "
                    "cannot be what satisfies it (D1+D2, T-23-26, 23-07-PLAN.md Task 3)",
                    _a_refresh_landing_mid_flip_does_not_repaint_the_switch)

                def _all_three_switches_still_post_with_scripts_blocked_at_360px():
                    # THE FLOOR, and the reason this plan built the switch
                    # AS the shipped form rather than beside it. A control
                    # that renders and silently does nothing with scripts
                    # blocked is the exact defect Phase 22 found on the
                    # login page; the only assertion that catches it is
                    # one that submits and then reads the DISK.
                    base_url = harness.base_url()
                    switches = (
                        ("/", "display_enabled", 'form[action="/quick/display"] button[role="switch"]'),
                        ("/", "quiet_hours_enabled",
                         'form[action="/quick/quiet-hours"] button[role="switch"]'),
                        ("/device", "led_enabled",
                         'button[role="switch"][form="%s"]' % config_page.QUICK_LED_FORM_ID),
                    )
                    for lang in ("en", "fr"):
                        for route, field, selector in switches:
                            with _no_js_page(browser.new_context, base_url, route,
                                             viewport=VIEWPORT_MIN_SUPPORTED) as page:
                                page.context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + route)
                                if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                    return False, "expected the 360px contract floor"
                                control = page.query_selector(selector)
                                if control is None:
                                    return False, (
                                        "lang=%s, %s: the %s switch does not render at all with "
                                        "scripts blocked" % (lang, route, field))
                                # The accessible state is SERVER-rendered,
                                # so it is correct on this page too.
                                stored = device_config.load_device_config(harness.tmpdir)[field]
                                rendered = control.get_attribute("aria-checked")
                                if rendered != ("true" if stored is True else "false"):
                                    return False, (
                                        "lang=%s, %s: the scripts-blocked page claims "
                                        "aria-checked=%r for a stored %r — role=switch is a "
                                        "description of what the button does, not a promise the "
                                        "script keeps" % (lang, field, rendered, stored))
                                # Centred first. At 360px the fixed tab
                                # bar owns the bottom 56px of the
                                # viewport, and a switch that happens to
                                # land under it fails the click with a
                                # pointer-interception error that says
                                # nothing about this plan. Centring is
                                # what a real thumb would do too.
                                page.eval_on_selector(
                                    selector, "el => el.scrollIntoView({block: 'center'})")
                                # 44px in BOTH axes, met directly.
                                box = control.bounding_box()
                                if box["width"] < 44 or box["height"] < 44:
                                    return False, (
                                        "lang=%s, %s: the switch measures %sx%s at 360px, under "
                                        "the 44px touch floor"
                                        % (lang, field, box["width"], box["height"]))
                                with page.expect_navigation():
                                    control.click()
                                after = device_config.load_device_config(harness.tmpdir)[field]
                                if after is stored:
                                    return False, (
                                        "lang=%s, %s: the switch did NOT persist with scripts "
                                        "blocked — it rendered and did nothing, which is the "
                                        "exact defect Phase 22 found on the login page (CFG-38)"
                                        % (lang, field))
                                # And the server's own flash is what tells
                                # this reader it worked: there is no
                                # toast without a script.
                                if page.locator("[%s]" % layout.QUICK_TOAST_ATTR).count() != 1:
                                    return False, (
                                        "lang=%s, %s: expected the toast region to still render "
                                        "(inert) with scripts blocked" % (lang, field))
                                if page.eval_on_selector(
                                        "[%s]" % layout.QUICK_TOAST_ATTR,
                                        "el => el.textContent") != "":
                                    return False, (
                                        "lang=%s, %s: the toast announced something on a page "
                                        "with no script at all" % (lang, field))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, all THREE switches render "
                    "with the server's own aria-checked, clear the 44px touch floor in both axes, "
                    "submit their real form and PERSIST to disk — the assertion that would catch a "
                    "control that renders and silently does nothing (D2/CFG-36, CFG-38, "
                    "23-07-PLAN.md Task 3)",
                    _all_three_switches_still_post_with_scripts_blocked_at_360px)

                # --- 23-08-PLAN.md Task 3 (D7/CFG-37 + D3's two Flights
                # clauses): the live list, proven live -----------------
                #
                # The refresh is forced the same way every 23-06 check
                # above forces it (_force_refresh + REFRESH_SETTLE_MS):
                # the loop's own visibilitychange catch-up, against a
                # shifted Date.now, with the shipped guards unmodified.

                FLIGHT_ID_ATTR = layout.REFRESH_ROW_ID_ATTR
                NEW_ROW_CLASS = layout.REFRESH_NEW_ROW_CLASS

                def _record_a_new_detection(callsign, hex_value, ts):
                    """One more runway_events row, written through the
                    same module server/poll_loop.py writes them with —
                    never a hand-built INSERT, so the row this check
                    calls "a new detection" is the shape a real detection
                    has."""
                    with history_db.open_db(harness.tmpdir) as conn:
                        history_db.record_runway_event(
                            conn, ts=ts, hex=hex_value, callsign=callsign,
                            aircraft_type="A320", confirmed_state="confirmed",
                            corroborated=True, route_source="adsb",
                            airline="Air France", origin="LFPO", destination="LFPG",
                            tracked_runway=device_config.RUNWAY_IDS[0])

                def _row_ids(page):
                    return page.evaluate(
                        "(attr) => [...document.querySelectorAll('tr[data-flight-row][' + attr"
                        " + ']')].map(el => el.getAttribute(attr))", FLIGHT_ID_ATTR)

                def _highlighted(page):
                    return page.evaluate(
                        "(cls) => [...document.querySelectorAll('.' + cls)].length",
                        NEW_ROW_CLASS)

                def _a_new_detection_is_highlighted_and_an_existing_row_is_not():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")

                        before_ids = _row_ids(page)
                        if len(before_ids) < 2:
                            return False, (
                                "expected the seeded fixture to render several rows, got %d — "
                                "with fewer this check measures nothing" % len(before_ids))
                        if len(set(before_ids)) != len(before_ids):
                            return False, (
                                "expected every rendered row identity to be distinct, got %r"
                                % (before_ids,))
                        if _highlighted(page):
                            return False, (
                                "a freshly LOADED page already highlights %d element(s) — the "
                                "highlight means 'this arrived while you were watching', and on "
                                "first paint nothing did" % _highlighted(page))

                        # PHASE 1 — a refresh with nothing new. The known
                        # set was taken from the page as first rendered,
                        # so this cycle must announce nothing. This is
                        # the clause that reddens when the set starts
                        # empty: every row would read as new.
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _highlighted(page):
                            return False, (
                                "a refresh that brought nothing new highlighted %d element(s) — "
                                "a list that announces itself every cycle has told the reader "
                                "nothing, and is how they learn to ignore it"
                                % _highlighted(page))

                        # PHASE 2 — a genuinely new detection, written to
                        # the same database the page reads, between two
                        # swaps.
                        _record_a_new_detection(
                            "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)

                        after_ids = _row_ids(page)
                        # 29-03-PLAN.md (CFG-83): Vols is now paginated to
                        # history_page.FLIGHTS_PAGE_SIZE by default, so
                        # "grows by exactly one" only holds BELOW that
                        # cap — at or above it (this harness's own
                        # realistic fixture already renders a full page),
                        # a new detection arriving pushes the oldest
                        # visible row off-page and the count holds flat.
                        # Both shapes are the SAME real behaviour; the
                        # invariant that survives pagination is the one
                        # `arrived`/`marked` below actually test: exactly
                        # one identity is new, and it is at the top.
                        want_after = min(
                            len(before_ids) + 1, history_page.FLIGHTS_PAGE_SIZE)
                        if len(after_ids) != want_after:
                            return False, (
                                "expected the swap to bring the new detection into the live "
                                "list: %d rows before, %d after, wanted %d (min(before+1, "
                                "FLIGHTS_PAGE_SIZE=%d)) — with no new row this check "
                                "would be asserting a highlight on nothing"
                                % (len(before_ids), len(after_ids), want_after,
                                   history_page.FLIGHTS_PAGE_SIZE))
                        arrived = [rid for rid in after_ids if rid not in before_ids]
                        if len(arrived) != 1:
                            return False, (
                                "expected exactly one identity to be new after the swap, got %r"
                                % (arrived,))
                        if after_ids[0] != arrived[0]:
                            return False, (
                                "expected the new detection at the TOP of the list, got %r at "
                                "the top and %r as the new identity" % (after_ids[0], arrived[0]))

                        # BOTH DIRECTIONS. A check that only asserted the
                        # presence of a highlight would pass on an
                        # implementation that highlights everything —
                        # which is the likelier bug, and the more
                        # damaging one.
                        marked = page.evaluate(
                            "([attr, cls]) => [...document.querySelectorAll("
                            "'tr[data-flight-row].' + cls)].map(el => el.getAttribute(attr))",
                            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
                        if marked != arrived:
                            return False, (
                                "expected exactly the arrived row %r to carry the highlight, "
                                "got %r — a highlight on a row that was already there is a "
                                "claim that it just landed, which is false" % (arrived, marked))
                        # And the phone card for the same event is
                        # marked too: Flights renders every flight twice
                        # and a reader on a phone must get the same
                        # signal a reader on a desktop does.
                        card_marked = page.evaluate(
                            "([attr, cls]) => [...document.querySelectorAll("
                            "'li.history-card.' + cls)].map(el => el.getAttribute(attr))",
                            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
                        if card_marked != arrived:
                            return False, (
                                "expected the phone card for the same event to be marked too, "
                                "got %r" % (card_marked,))
                        # The animation is the stylesheet's own, once,
                        # on the phase's ambient token.
                        animation = page.eval_on_selector(
                            "tr[data-flight-row]." + NEW_ROW_CLASS,
                            "el => [getComputedStyle(el).animationName,"
                            " getComputedStyle(el).animationIterationCount,"
                            " getComputedStyle(el).animationDuration]")
                        if animation[0] != "skypane-row-arrive":
                            return False, (
                                "expected the highlight class to resolve to the stylesheet's own "
                                "arrival block, got %r" % (animation[0],))
                        if animation[1] != "1":
                            return False, (
                                "expected the highlight to run exactly once, got %r iterations"
                                % (animation[1],))
                        if animation[2] != "2s":
                            return False, (
                                "expected the highlight to spend --motion-slow (2s), got %r — a "
                                "180ms flash on a row nobody was looking at is no signal at all"
                                % (animation[2],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a detection recorded while the Flights page is open arrives at the top of the "
                    "live list on the next refresh and is the ONLY thing highlighted — in both the "
                    "table and the phone card list — while a row that was already there is not, "
                    "nothing at all is highlighted on first load, and a refresh that brings nothing "
                    "new announces nothing; the class resolves to the stylesheet's own single-run "
                    "arrival animation on --motion-slow (D7/CFG-37, 23-08-PLAN.md Task 3)",
                    _a_new_detection_is_highlighted_and_an_existing_row_is_not)

                def _a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened():
                    # The half a swapped list gets wrong silently. The
                    # SERVER renders every detail row VISIBLE — that is
                    # D-15's locked no-JS floor and it carries no
                    # open/closed state at all — so a refresh arrives
                    # with every row expanded and every toggle reading
                    # aria-expanded="false". Without flight-rows.js
                    # re-deriving its own state after the swap, one
                    # refresh unfolds the whole table; with a record
                    # keyed to the row's POSITION instead of its event
                    # identity, a detection arriving at the top reopens
                    # the wrong row.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")

                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        opened_id = page.eval_on_selector(
                            "#" + toggle.get_attribute("aria-controls"),
                            "(el, attr) => el.getAttribute(attr)", FLIGHT_ID_ATTR)
                        if not opened_id:
                            return False, "expected the detail row to carry its event identity"
                        toggle.click()

                        # BLURRED ON PURPOSE. The click leaves focus on
                        # the toggle, and freshness.js skips any region
                        # containing the active element — so with focus
                        # still there this check would pass against a
                        # script that re-derives nothing at all.
                        page.evaluate("() => document.activeElement.blur()")

                        _record_a_new_detection(
                            "OPENSRV", "39fffe", "2026-08-02T00:15:00+00:00")
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)

                        seen = page.evaluate(
                            "([idAttr, openId]) => {"
                            "  const details = [...document.querySelectorAll("
                            "    'tr.flight-detail-row')];"
                            "  const open = details.filter(el =>"
                            "    el.className.indexOf('flight-detail-row--collapsed') === -1);"
                            "  return {total: details.length,"
                            "          open: open.map(el => el.getAttribute(idAttr)),"
                            "          expanded: [...document.querySelectorAll("
                            "            '[data-row-toggle][aria-expanded=\\\"true\\\"]')].length,"
                            "          stillThere: !!document.querySelector("
                            "            'tr.flight-detail-row[' + idAttr + '=\\\"' + openId"
                            "            + '\\\"]')};"
                            "}", [FLIGHT_ID_ATTR, opened_id])
                        if seen["total"] < 2:
                            return False, (
                                "expected the swapped list to still render its detail rows, got "
                                "%d — with fewer this check measures nothing" % seen["total"])
                        if not seen["stillThere"]:
                            return False, (
                                "the row that was opened is no longer in the list at all, so "
                                "nothing below is a statement about it")
                        if seen["open"] != [opened_id]:
                            return False, (
                                "after a refresh %d of %d detail rows are open (%r), expected "
                                "exactly the one that was opened (%r). Every row open is the "
                                "server's own markup arriving un-collapsed; the WRONG row open "
                                "is a record keyed to a position that just renumbered"
                                % (len(seen["open"]), seen["total"], seen["open"], opened_id))
                        if seen["expanded"] != 1:
                            return False, (
                                "expected exactly one toggle to report aria-expanded=true after "
                                "the refresh, got %d — the class and the announced state are "
                                "written in one place precisely so they cannot drift"
                                % seen["expanded"])
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a refresh neither unfolds the Flights table nor closes the row you opened: "
                    "with focus deliberately blurred off the toggle (so the loop's focus skip "
                    "cannot be what passes this) and a new detection renumbering every row below "
                    "it, exactly the row that was opened is still open — by EVENT identity, not by "
                    "position — and exactly one toggle still announces it (D7/CFG-37, "
                    "23-08-PLAN.md Task 3)",
                    _a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened)

                def _a_refresh_never_interrupts_or_undoes_the_filter():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")
                        requests = _count_document_requests(page, base_url + "/flights")

                        # 29-03-PLAN.md (CFG-83): Vols is now paginated
                        # to history_page.FLIGHTS_PAGE_SIZE by default, so
                        # a hardcoded callsign from seed_state_dir()'s own
                        # 36-flight fixture is no longer guaranteed to be
                        # among the rows the SERVER actually sent — this
                        # reads the first rendered row's own
                        # data-filter-text (unique per row: "{callsign
                        # lowercased} {hex}") straight off the page
                        # instead, so the query always targets a row
                        # that is genuinely there, whatever the default
                        # page size is.
                        query = page.eval_on_selector(
                            "tr[data-flight-row]", "el => el.getAttribute('data-filter-text')")
                        if not query:
                            return False, (
                                "expected the first rendered row to carry a non-empty "
                                "data-filter-text to filter by — with none, this check has "
                                "nothing to type")
                        page.click("[data-filter-input]")
                        page.type("[data-filter-input]", query)
                        visible = page.evaluate(
                            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
                            ".filter(el => !el.hidden).length")
                        if visible != 1:
                            return False, (
                                "expected the query to narrow the table to one row before "
                                "anything else is measured, got %d" % visible)
                        count_text = page.eval_on_selector(
                            "[data-filter-count]", "el => el.textContent")

                        # PHASE 1 — with the caret still in the box, the
                        # whole cycle stands down. Counted as REQUESTS,
                        # not as DOM state: a page that fetched and then
                        # declined to swap is a different behaviour.
                        before = requests()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if requests() != before:
                            return False, (
                                "the loop fetched while the caret was in the filter box — "
                                "userIsInteracting() exists so a half-typed query is never "
                                "swapped out from under the person typing it (%d request(s))"
                                % (requests() - before))

                        # CONTROL — the same trigger, focus moved off the
                        # input, MUST fetch. Without this phase 1 would
                        # pass on a page whose loop never runs at all.
                        page.evaluate("() => document.activeElement.blur()")
                        before = requests()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if requests() == before:
                            return False, (
                                "control: the same trigger issued no request with focus off the "
                                "input either — this page's loop is not running, so phase 1 "
                                "proved nothing")

                        # PHASE 2 — and that swap must not have undone
                        # the query. The SERVER renders the list
                        # unfiltered; it knows nothing about what was
                        # typed here.
                        visible = page.evaluate(
                            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
                            ".filter(el => !el.hidden).length")
                        if visible != 1:
                            return False, (
                                "a refresh handed back %d visible rows under a query that "
                                "matches one — the server renders the list unfiltered, so a swap "
                                "that is not followed by a re-filter silently undoes what the "
                                "reader asked for" % visible)
                        if page.eval_on_selector(
                                "[data-filter-count]", "el => el.textContent") != count_text:
                            return False, (
                                "the live count reverted to the server's own unfiltered sentence "
                                "after a refresh, expected it to still read %r" % (count_text,))
                        if page.eval_on_selector(
                                "[data-filter-input]", "el => el.value") != query:
                            return False, "the typed query itself did not survive the refresh"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a refresh never interrupts the filter and never undoes it: with the caret in "
                    "the box the loop issues ZERO requests (counted, against a control proving the "
                    "same trigger does fetch with focus moved off), and the swap that then happens "
                    "leaves the typed query applied — same visible rows, same live count, same "
                    "input value — because the server renders the list unfiltered (D7/CFG-37, "
                    "23-08-PLAN.md Task 3)",
                    _a_refresh_never_interrupts_or_undoes_the_filter)

                def _a_collapsed_detail_row_cannot_be_reached_by_keyboard():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        detail_id = toggle.get_attribute("aria-controls")

                        # Every focusable thing inside the row is asked
                        # to take focus, one at a time, and must fail to.
                        # This is the keyboard question asked directly
                        # rather than through a proxy: an element that
                        # cannot become document.activeElement is an
                        # element Tab cannot land on, and display:none is
                        # also what keeps it out of the accessibility
                        # tree.
                        probe = (
                            "(id) => {"
                            "  const row = document.getElementById(id);"
                            "  const kids = [...row.querySelectorAll("
                            "    'a[href], button, input, select, textarea, [tabindex]')];"
                            "  const reached = [];"
                            "  kids.forEach(el => { el.focus();"
                            "    if (document.activeElement === el) reached.push("
                            "      el.tagName + '.' + (el.className || ''));"
                            "    el.blur(); });"
                            "  return {kids: kids.length, reached: reached};"
                            "}")
                        seen = page.evaluate(probe, detail_id)
                        if not seen["kids"]:
                            return False, (
                                "expected the seeded detail row to contain focusable controls "
                                "(its copy buttons) — with none, this check measures nothing")
                        if seen["reached"]:
                            return False, (
                                "a COLLAPSED detail row let %d of its %d controls take focus "
                                "(%r) — a row held present at zero height is still in the tab "
                                "order and still in the accessibility tree, so a keyboard user "
                                "walks into a row nobody can see (T-23-32)"
                                % (len(seen["reached"]), seen["kids"], seen["reached"]))

                        # CONTROL — open the row and the SAME controls
                        # must become reachable. Without this the check
                        # would pass just as well on a page that renders
                        # no detail row at all.
                        toggle.click()
                        seen = page.evaluate(probe, detail_id)
                        if not seen["reached"]:
                            return False, (
                                "control: an OPEN detail row's %d controls were still "
                                "unreachable — so the assertion above is about the page being "
                                "empty, not about the row being closed" % seen["kids"])

                        # And the opening really is a height animation,
                        # on the wrapper rather than on the row box.
                        style = page.eval_on_selector(
                            "#" + detail_id + " .flight-detail-row__reveal",
                            "el => [getComputedStyle(el).display,"
                            " getComputedStyle(el).transitionProperty,"
                            " getComputedStyle(el).transitionDuration]")
                        if style[0] != "grid":
                            return False, (
                                "expected the reveal wrapper to be a grid, got %r" % (style[0],))
                        if "grid-template-rows" not in style[1]:
                            return False, (
                                "expected grid-template-rows to be the transitioned property, "
                                "got %r — a guessed max-height either clips tall content or "
                                "animates through empty space, and interpolate-size is "
                                "Chromium-only" % (style[1],))
                        if style[2] != "0.18s":
                            return False, (
                                "expected the reveal to spend --motion-fast (180ms), got %r"
                                % (style[2],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a COLLAPSED Flights detail row lets none of its own controls take focus — the "
                    "deliberate display:none end state, asked as the keyboard question directly — "
                    "against a control phase proving the same controls ARE reachable once the row "
                    "is open, and the opening really animates grid-template-rows on a grid wrapper "
                    "at --motion-fast (D3/CFG-32, T-23-32, 23-08-PLAN.md Task 3)",
                    _a_collapsed_detail_row_cannot_be_reached_by_keyboard)

                def _a_phone_card_opens_from_a_tap_anywhere_with_and_without_scripts():
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        card = page.locator("li.history-card").first
                        card.wait_for(state="visible")
                        details = card.locator("details.history-card__details")
                        if details.evaluate("el => el.open"):
                            return False, (
                                "expected the card to start closed — with it open this check "
                                "cannot tell a tap that worked from a card that was never shut")
                        # The "anywhere" property, measured: the summary's
                        # own box must cover the card's whole face,
                        # padding included. A summary that stopped at the
                        # padding's inner edge would leave a rim that
                        # looks tappable and is not.
                        boxes = page.evaluate(
                            "() => {"
                            "  const li = document.querySelector('li.history-card');"
                            "  const s = li.querySelector('summary.history-card__summary');"
                            "  const a = li.getBoundingClientRect();"
                            "  const b = s.getBoundingClientRect();"
                            "  return [a.width, b.width, a.top, b.top];"
                            "}")
                        if boxes[1] < boxes[0] - 2.5:
                            return False, (
                                "the card's summary is %spx wide inside a %spx card — a tap on "
                                "the rim between them lands on nothing, which reads as a broken "
                                "control rather than as a boundary" % (boxes[1], boxes[0]))
                        # Tapped on the secondary line, which is not a
                        # control and never was: the route and the state.
                        card.locator(".history-card__secondary").click()
                        if not details.evaluate("el => el.open"):
                            return False, (
                                "a tap on the card's own face away from every control did not "
                                "open it — D7 asks for a card you tap anywhere, through the "
                                "native disclosure it already contained")
                        # Nothing nested inside the summary can steal
                        # that activation, because nothing is nested in
                        # it: the one-hop resolve link sits outside.
                        nested = page.eval_on_selector(
                            "summary.history-card__summary",
                            "el => el.querySelectorAll('a[href], button').length")
                        if nested:
                            return False, (
                                "expected no control nested inside the card's summary, found %d"
                                % nested)
                    finally:
                        context.close()

                    # And with no script at all, at the same 360px floor.
                    # The disclosure is native, so this is not a fallback
                    # path that could rot — it is the same control.
                    with _no_js_page(browser.new_context, harness.base_url(), "/flights",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        card = page.locator("li.history-card").first
                        card.wait_for(state="visible")
                        details = card.locator("details.history-card__details")
                        if details.evaluate("el => el.open"):
                            return False, "expected the scripts-blocked card to start closed too"
                        card.locator(".history-card__secondary").click()
                        if not details.evaluate("el => el.open"):
                            return False, (
                                "the phone card did not open with scripts blocked — the whole "
                                "point of building this on the <details> the card already had is "
                                "that it needs no script (CFG-38)")
                        # The detail ROW floor, in the same context: with
                        # no script nothing is collapsed and every detail
                        # is on screen, exactly as before this plan.
                        collapsed = page.evaluate(
                            "() => document.querySelectorAll("
                            "'.flight-detail-row--collapsed').length")
                        if collapsed:
                            return False, (
                                "%d detail row(s) are collapsed on a page with no script — the "
                                "collapsing class has exactly one writer and it cannot run here "
                                "(D-15, locked)" % collapsed)
                        live = page.evaluate(
                            "() => document.documentElement.className.indexOf("
                            "'flight-rows-live') !== -1")
                        if live:
                            return False, (
                                "the live-script class is on <html> with no script running — the "
                                "height animation is keyed on it precisely so a scripts-blocked "
                                "page animates nothing")
                    return True, ""
                check(
                    "a phone card at 360px opens from a tap on its own face away from every "
                    "control, through the native disclosure it already contained, with its summary "
                    "box covering the whole card and no control nested inside it — and it does the "
                    "same with SCRIPTS BLOCKED, where no detail row is collapsed and the "
                    "live-script class the height animation is keyed on is absent (D7/CFG-37, "
                    "CFG-38, 23-08-PLAN.md Task 3)",
                    _a_phone_card_opens_from_a_tap_anywhere_with_and_without_scripts)

                # --- 23-09-PLAN.md Task 3 (D3/CFG-32): the save bar,
                # the app's most-iterated component and the one that
                # carried B1, gaining motion and a label. Everything
                # below is a regression surface before it is a feature:
                # the bar's own checks above (reveal-and-persist on both
                # scopes, the fallback's visibility contract, Cancel and
                # the leave-guard, the tab-bar geometry, the
                # double-submit guard) were run and recorded GREEN
                # before a line of this plan's CSS or JS was written.

                def _the_dirty_count_arrives_and_moves_only_when_the_word_does():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not a
                    # mechanical swap — this check's own subject
                    # ([data-save-status] and its exact [saving, saved]
                    # text sequence) is deleted outright with the auto-save
                    # model, and a straight deletion would silently drop
                    # real coverage. One genuinely valuable idea survives:
                    # clicking an ALREADY-CHECKED radio fires no native
                    # `change`, so a role="status" element must announce
                    # nothing for it — a live-region hygiene contract the
                    # restored bar shares (it is role="status" too).
                    # Retargeted onto [data-dirty-count], with a
                    # MutationObserver installed BEFORE the first edit so
                    # the exact sequence of writes is recorded rather than
                    # sampled at the end.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")
                        current_theme = page.eval_on_selector(
                            'input[name="theme"]:checked', "el => el.value")
                        theme_target, theme_target2 = [
                            t for t in device_config.THEME_IDS if t != current_theme][:2]

                        page.evaluate(
                            "() => {"
                            " window.__countWords = [];"
                            " var el = document.querySelector('[data-dirty-count]');"
                            " new MutationObserver(function () {"
                            "   window.__countWords.push(el.textContent);"
                            " }).observe(el, {childList: true, characterData: true,"
                            "                 subtree: true});"
                            "}")

                        # a. THE SURVIVING CONTROL PHASE: clicking the
                        # ALREADY-CHECKED radio fires no native `change`
                        # (the checked state does not change), so
                        # countDifferences() stays at 0 and the count
                        # element must not be written AT ALL — this is now
                        # testing setCountText()'s own changed-text gate,
                        # the mechanism that makes a no-op click produce no
                        # write.
                        _click_control(page, 'input[name="theme"][value="%s"]' % current_theme)
                        page.wait_for_timeout(150)
                        after_noop = page.evaluate("() => window.__countWords.slice()")
                        if after_noop:
                            return False, (
                                "re-clicking the ALREADY-selected theme wrote to "
                                "[data-dirty-count]: %r — a click that changed no value must not "
                                "announce one" % (after_noop,))

                        # b. A REAL CHANGE — exactly ONE text mutation, to
                        # the section's own name, read off the bar's OWN
                        # data-dirty-changed-suffix and the field's own
                        # data-dirty-section wrapper, never hardcoded in
                        # English (this file's own D-06 idiom).
                        expected_label = page.evaluate(
                            "() => {"
                            " var field = document.querySelector('input[name=\"theme\"]');"
                            " var wrapper = field.closest('[data-dirty-section]');"
                            " var bar = document.querySelector('[data-dirty-bar]');"
                            " return wrapper.getAttribute('data-dirty-section')"
                            "   + bar.getAttribute('data-dirty-changed-suffix');"
                            "}")
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target)
                        _wait_for_bar(page)
                        words = page.evaluate("() => window.__countWords.slice()")
                        if len(words) != 1:
                            return False, (
                                "expected exactly ONE text mutation to [data-dirty-count] for a "
                                "real change, got %r" % (words,))
                        if words[0] != expected_label:
                            return False, (
                                "expected [data-dirty-count] to read %r after the real change, "
                                "got %r" % (expected_label, words[0]))
                        if "is-fading-in" not in (
                                page.locator("[data-dirty-count]").get_attribute("class") or ""):
                            return False, (
                                "expected [data-dirty-count] to carry the changed-value class "
                                "after a real change")

                        # c. A DIFFERENT VALUE, SAME RENDERED LABEL — the
                        # gate genuinely exercised. MEASURED, not
                        # assumed: re-selecting the value a radio already
                        # holds fires NO native `change` at all
                        # (confirmed live — a checked-state no-op never
                        # reaches this listener), so phase (a)'s own
                        # already-checked click can never reach
                        # setCountText() either, regardless of its own
                        # gate. The gate this check's own mutation names
                        # is only reachable when updateBar() genuinely
                        # RUNS (a real change fires) but resolves to the
                        # SAME text as before — which a second, DIFFERENT
                        # theme inside the identical data-dirty-section
                        # wrapper produces: a real change (a different
                        # radio becomes checked), yet dirtySectionLabels()
                        # names the same section, so setCountText()
                        # receives the identical string and the gate is
                        # what decides whether that write happens.
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target2)
                        page.wait_for_timeout(150)
                        after_second = page.evaluate("() => window.__countWords.slice()")
                        if after_second != words:
                            return False, (
                                "changing to a DIFFERENT theme inside the same section wrote a "
                                "new mutation to [data-dirty-count]: %r became %r — the two "
                                "renders are textually IDENTICAL, so a write here is "
                                "setCountText()'s own changed-text gate failing to suppress a "
                                "no-op text assignment" % (words, after_second))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "[data-dirty-count] ARRIVES rather than appearing, and stays silent for "
                    "anything that is not a genuine change: clicking an ALREADY-CHECKED radio "
                    "writes nothing (the surviving control-phase idea from the retired "
                    "save-status region — MEASURED live to fire no native change at all, never "
                    "reaching updateBar()); a REAL change writes the section's own name EXACTLY "
                    "ONCE, read off the bar's own data-* attributes never hardcoded in English, "
                    "and carries the changed-value class; and changing to a SECOND, DIFFERENT "
                    "theme inside the identical data-dirty-section wrapper — a real change that "
                    "resolves to the textually IDENTICAL label — writes nothing further, which "
                    "is setCountText()'s own changed-text gate genuinely exercised (a same-value "
                    "re-click, tried first, never reaches the listener at all and so cannot "
                    "prove the gate) — a new phase this check gains over its retired predecessor "
                    "(D3/CFG-32, 23-09-PLAN.md Task 3; retargeted from the retired save-status "
                    "region onto the restored bar by 28-10-PLAN.md Task 2, CFG-77/CFG-78)",
                    _the_dirty_count_arrives_and_moves_only_when_the_word_does)

                def _the_bars_save_persists_every_field_never_only_the_touched_one():
                    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED —
                    # the subject moved from a request body to disk. A
                    # native form submission posts every named field by
                    # construction (the browser builds the body from
                    # every form control, form=-attached or not), so
                    # intercepting the request and reading its body would
                    # be testing the BROWSER, not this app. What still
                    # matters and can still regress is CFG-36's own
                    # hazard: a single field's save must never silently
                    # clobber every OTHER field's on-disk value. Proven
                    # here against disk instead of a request body — a
                    # STRONGER surface, not a weaker one: a server that
                    # posts the whole form correctly but then only WRITES
                    # the touched key would still pass the retired
                    # request-body check and still fail this one.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            # tracked_runway: a cross-DOM form=-attached
                            # field living OUTSIDE the physical <form> —
                            # the exact shape CFG-36's own hazard was
                            # found in — on a scope (Display) with
                            # several OTHER fields for the assertion to
                            # have something to catch.
                            before = device_config.load_device_config(harness.tmpdir)
                            target = next(
                                r for r in device_config.RUNWAY_IDS
                                if str(r) != str(before["tracked_runway"]))

                            page.goto(base_url + "/display")
                            _click_control(
                                page, 'input[name="tracked_runway"][value="%s"]' % target)
                            _wait_for_bar(page)
                            _save_via_bar(page)

                            after = device_config.load_device_config(harness.tmpdir)
                            if str(after["tracked_runway"]) != str(target):
                                return False, (
                                    "lang=%s: the save did not persist — expected "
                                    "tracked_runway %r, got %r"
                                    % (lang, target, after["tracked_runway"]))
                            changed_keys = [k for k in before if before[k] != after.get(k)]
                            if changed_keys != ["tracked_runway"]:
                                return False, (
                                    "lang=%s: saving ONE field (tracked_runway) changed %r on "
                                    "disk — a save that clobbers an untouched field is CFG-36's "
                                    "own hazard; before=%r after=%r"
                                    % (lang, changed_keys, before, after))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the bar's own Save persists EVERY field to disk, never only the touched one: "
                    "reading the FULL on-disk config before and after a single-field "
                    "(tracked_runway) save, in both languages, and asserting the two dicts "
                    "differ in EXACTLY the one key touched — a STRONGER surface than the retired "
                    "request-body capture, since a server that posts the whole form but only "
                    "writes the touched key would still pass that check and fail this one "
                    "(T-27-04-D, CFG-36's own hazard; retargeted from the request body onto disk "
                    "by 28-10-PLAN.md Task 3, CFG-77/CFG-78; 27-04-PLAN.md Task 4, CFG-63; "
                    "supersedes the retired Save-button relabel check, T14's deferred label, "
                    "23-09-PLAN.md Task 3/D3/CFG-32)",
                    _the_bars_save_persists_every_field_never_only_the_touched_one)

                def _with_no_script_the_fallback_save_is_the_only_way():
                    # 27-04-PLAN.md Task 4 (CFG-63): SUPERSEDES this
                    # check's own pre-27-04 subject — THE FLOOR THIS
                    # COMPONENT BROKE ONCE (B1: the save bar never
                    # appeared, and the fallback had already hidden
                    # itself). The bar and both of its former liveness
                    # markers (dirty-ready/dirty-shown) are retired
                    # outright, so there is nothing left on <html> or in
                    # the DOM for a scripts-blocked page to prove absent
                    # — what survives is the floor itself: the fallback
                    # Save is VISIBLE, has a real box, and still saves.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            # quick-260923-em4: the ROOT CAUSE the 260923-9na partial fix
                            # below was circling. Clicking the fallback while the bar's
                            # `skypane-bar-arrive` entrance animation is still running stalls
                            # Playwright's `stable` actionability leg in this scripts-blocked
                            # context: measured ~0.7-1.0s per click in isolation (vs ~0.06s with
                            # motion reduced) and, inside this full harness, a hang for the whole
                            # 30000ms budget — no request and no navigation fired during it
                            # (traced with framenavigated/request listeners), so the click never
                            # happened at all. Reduced motion zeroes the entrance through the
                            # stylesheet's own `prefers-reduced-motion: reduce` override. This
                            # check's subject is that the fallback is visible, has a box and
                            # SAVES, not the entrance animation, so nothing it asserts is lost.
                            # Every local full-harness run failed here without this; 2/2 pass
                            # with it.
                            page.emulate_media(reduced_motion="reduce")
                            page.goto(base_url + "/display")
                            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                return False, "expected the measurement at the 360px contract floor"
                            fallback = page.locator(
                                "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                            if fallback.count() != 1:
                                return False, (
                                    "lang=%s: expected exactly one fallback Save, got %d — with "
                                    "no script it is the ONLY way to save this page"
                                    % (lang, fallback.count()))
                            if not fallback.is_visible():
                                return False, (
                                    "lang=%s: the fallback Save is rendered but not visible — "
                                    "which is precisely the shape B1 took, and a check that only "
                                    "asked whether it EXISTS would have passed through it"
                                    % (lang,))
                            box = fallback.bounding_box()
                            if not box or box["width"] <= 0 or box["height"] <= 0:
                                return False, (
                                    "lang=%s: the fallback Save has no box at 360px (%r)"
                                    % (lang, box))
                            current = device_config.load_device_config(harness.tmpdir)["theme"]
                            target = next(
                                t for t in device_config.THEME_IDS if t != current)
                            page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % target,
                                "el => el.checked = true")
                            # quick-260923-9na: expect_navigation()'s 30000ms clock
                            # starts the instant this `with` is entered — BEFORE
                            # click()'s own actionability poll (visible/stable/
                            # receives-events/enabled) has even begun, so under CI
                            # load that poll silently eats the SAME budget the
                            # navigation wait needs. Real CI (run 35818514258 on
                            # main, 2026-09-23) recorded `TimeoutError('Timeout
                            # 31ms exceeded ... "domcontentloaded" event fired')` —
                            # the actionability poll had already burned 29969ms of
                            # the 30000ms before navigation got a look-in. Waiting
                            # for visibility here, on its OWN clock, before the
                            # `with` block starts, removes that portion of the
                            # overlap without widening any timeout.
                            fallback.wait_for(state="visible")
                            with page.expect_navigation():
                                fallback.click()
                            saved = device_config.load_device_config(harness.tmpdir)["theme"]
                            if saved != target:
                                return False, (
                                    "lang=%s: a Display save did not persist through the "
                                    "fallback Save with scripts blocked at 360px — expected "
                                    "theme %r, got %r. This is the P0 Phase 22 existed to fix"
                                    % (lang, target, saved))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, the fallback Save is "
                    "VISIBLE with a real box and still saves to disk — B1's floor re-asserted "
                    "after the bar and both its former liveness markers are retired outright "
                    "(B1/CFG-38, 23-09-PLAN.md Task 3; retargeted by 27-04-PLAN.md Task 4, CFG-63)",
                    _with_no_script_the_fallback_save_is_the_only_way)

                # ----------------------------------------------------------
                # 27-05-PLAN.md Task 3 (CFG-66): CFG-47's schematic runway
                # map RETIRED. The three checks 25-03-PLAN.md Task 3 added
                # here — the map's own save-corroboration, its keyboard/
                # paint proof, and its 360px floor measurement — are GONE,
                # named in 27-05-SUMMARY.md, along with the `_runway_ids()`
                # and `_SETTLE_STRIPS` helpers only they used.
                #
                # The radios' OWN scripts-blocked save-to-disk proof —
                # `_the_floor_saves_to_disk_with_scripts_blocked_after_the_
                # gate_simplifies` (CFG-64, 27-03-PLAN.md Task 3), further
                # down this file — never depended on the map's presence
                # and is UNCHANGED by this removal; it is the mitigation
                # T-27-05-A names.
                #
                # ONE check replaces the three: the map is gone, the
                # radios and the photographs are not — asserted as a
                # RELATIONSHIP (D-32) rather than as three separate facts,
                # because "the drawing is gone" alone would also pass on a
                # card that lost the control or the pictures with it. And
                # the touch target the map's own card used to provide is
                # measured rather than assumed, in the control's own
                # container, at 360px, in BOTH themes (T-27-05-B) — the
                # box changed when the drawing came out, and nobody had
                # re-measured it until now.
                # ----------------------------------------------------------

                def _the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor():
                    base_url = harness.base_url()
                    ids = device_config.RUNWAY_IDS
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        # THE RELATIONSHIP, IN ONE PLACE: the drawing is
                        # gone AND the control is not AND the photographs
                        # are not — three clauses about one rendering,
                        # because a check that only asked the first would
                        # pass against a card that lost everything else
                        # with it.
                        maps = page.locator(".runway-card .runway-map").count()
                        if maps != 0:
                            return False, (
                                "expected ZERO .runway-map elements on /display after CFG-66's "
                                "removal, found %d — the drawing is supposed to be gone" % (maps,))
                        radios = page.locator('input[name="tracked_runway"]').count()
                        if radios != len(ids):
                            return False, (
                                "expected %d tracked_runway radios, found %d — the map coming "
                                "out must not take the control it was wrapped around with it"
                                % (len(ids), radios))
                        photos = page.locator(".runway-card .runway-card__image").count()
                        if photos != len(ids):
                            return False, (
                                "expected %d runway photographs (.runway-card__image), found %d "
                                "— the developer objected to the drawn map, not to the "
                                "pictures, and this relationship must also fail if they vanish"
                                % (len(ids), photos))

                        message = _assert_no_page_overflow(
                            page, "the runway row on /display",
                            VIEWPORT_MIN_SUPPORTED["width"])
                        if message:
                            return False, message

                        # THE HIT TARGET THE MAP'S OWN CARD USED TO
                        # PROVIDE, MEASURED RATHER THAN ASSUMED (T-27-05-B).
                        # `.runway-row > .runway-card` is the SAME
                        # container the retired map check measured — only
                        # the box inside it changed, from a drawing plus a
                        # number to a number, a photograph and a check
                        # glyph. IN ITS OWN CONTAINER, never inherited from
                        # a class, and in BOTH themes: a card that only
                        # cleared the floor in one theme's box model would
                        # still fail a visitor using the other.
                        themes_measured = []
                        for state in _in_both_themes(page):
                            for index in range(len(ids)):
                                selector = (
                                    ".runway-row > .runway-card:nth-child(%d)" % (index + 1))
                                _assert_hit_target(
                                    page, selector,
                                    "the runway card %d of %d on /display in the %s theme, "
                                    "now that its map is gone"
                                    % (index + 1, len(ids), state["theme"]))
                            themes_measured.append(state["theme"])
                        if len(themes_measured) != 2:
                            return False, (
                                "expected a hit-target measurement in each of two themes, got "
                                "%d (%r)" % (len(themes_measured), themes_measured))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "CFG-66: the map is gone, the radios and the photographs are not — asserted "
                    "as ONE relationship rather than three separate facts: zero .runway-map "
                    "elements resolve on /display, exactly RUNWAY_IDS' own count of "
                    "tracked_runway radios and of .runway-card__image photographs still "
                    "resolve, the runway row does not scroll the page sideways at 360px, and "
                    "every runway card clears the 44px hit-target floor in ITS OWN container at "
                    "360px in BOTH themes — measured, not assumed, now that the map strip no "
                    "longer provides the box (CFG-66/D-32/T-27-05-B, retiring CFG-47's three "
                    "checks named in 27-05-SUMMARY.md)",
                    _the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor)

                # 30-03-PLAN.md Task 3 (CFG-85): THEME_STRIP_SEL,
                # THEME_PAGERS_SEL, THEME_DETAILS_SEL, _STRIP_PROBE,
                # _SETTLE_CAROUSEL, _CAROUSEL_INSTANCE_PROBE and
                # _TOGGLE_OWN_DISCLOSURE (the whole shared carousel
                # selector/probe block that used to live here) are
                # RETIRED WITH THEIR LAST CONSUMER
                # (_the_carousel_meets_its_floors_at_360px_in_both_
                # themes, ledgered above) — grepped whole-file before
                # deletion, zero remaining consumers of any of the
                # seven. THEME_PREVIEW_SEL SURVIVES — the live preview
                # element (`.theme-live-preview__image`) is unchanged by
                # this phase, and
                # _cancel_restores_the_field_the_preview_and_the_dial_
                # from_the_resulting_dom (below) still reads it.
                THEME_PREVIEW_SEL = ".theme-live-preview__image"

                # --- 25-06-PLAN.md Task 1 (CFG-50): the number this
                # plan is judged against, taken before there was any
                # incentive to like it. See _display_page_height() for
                # why this is an instrument rather than a sentence in a
                # document, and for what it refuses to measure.
                def _displays_page_height_is_recorded_at_both_phone_widths():
                    base_url = harness.base_url()
                    heights = {}
                    for viewport in (VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED):
                        seen = _display_page_height(browser.new_context, base_url, viewport)
                        heights[viewport["width"]] = seen["height"]
                        print(
                            "        [25-06 T1] Display document height at %dpx: "
                            "%d px (client %dx%d, %d theme radios)"
                            % (viewport["width"], seen["height"],
                               seen["clientWidth"], seen["clientHeight"],
                               seen["themeRadios"]))
                    # NO TARGET IS ASSERTED HERE, DELIBERATELY. 22-10
                    # recorded X6's height target as not met and not
                    # reachable by density alone; whether THIS plan
                    # reaches it is stated in that plan's own SUMMARY
                    # from these numbers, in either direction.
                    #
                    # AND NO CROSS-WIDTH RELATIONSHIP EITHER, BECAUSE THE
                    # OBVIOUS ONE IS FALSE ON THIS PAGE AND WAS MEASURED
                    # TO BE. The first version of this check asserted
                    # that a narrower viewport cannot make a reflowing
                    # page shorter. Run before a byte of this plan's
                    # markup existed, Display measured 4276 px at 390px
                    # and 4269 px at 360px — SEVEN PIXELS SHORTER at the
                    # narrower width — and the check duly failed against
                    # a page with nothing whatever wrong with it. The
                    # cause is ordinary: this page is a stack of cards
                    # whose rows each round independently, and a handful
                    # of them land on a different line count at one width
                    # than the other. The clause was removed rather than
                    # loosened to a tolerance, because a tolerance would
                    # have been a number invented to make a wrong belief
                    # pass. What is asserted instead is everything
                    # `_display_page_height()` asserts about WHERE the
                    # number came from, which is the property that makes
                    # a recorded height worth anything.
                    if not heights:
                        return False, "no viewport was measured at all"
                    return True, ""
                check(
                    "Display's full rendered document height is recorded at 390px and at 360px "
                    "by one instrument — proved to be pointed at the authenticated Display page "
                    "(its Aspect heading AND a full THEME_IDS-sized departures "
                    "radiogroup, never merely 'a page rendered'), at the width the caller asked "
                    "for, and taller than the viewport — asserting NO target, because the "
                    "number IS the criterion and 25-06 states in its own SUMMARY whether it is "
                    "met, and no cross-width relationship either, because the obvious one "
                    "(narrower cannot be shorter) was MEASURED FALSE on this page before the "
                    "plan changed anything (CFG-50, 25-06-PLAN.md Task 1)",
                    _displays_page_height_is_recorded_at_both_phone_widths)

                # --- 25-06-PLAN.md Task 4 (CFG-50/D-09) ---------------

                def _the_theme_still_saves_with_scripts_blocked():
                    # 30-03-PLAN.md Task 3 (CFG-85): NARROWED, not
                    # deleted. This is the markup-agnostic half of
                    # CFG-85's own named proof — it drives by field
                    # NAME and reads back from disk, never a strip/
                    # pager/disclosure selector — so it survives the
                    # rebuild verbatim. The trailing strip-probe half
                    # (carousel chip count, overflow, keyboard-arrow
                    # selection through the strip, the <details>
                    # disclosure, the pager gate) is LEDGERED to 30-08
                    # — see _ASPECT_REPIN_LEDGER below.
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(harness.tmpdir)["theme"]

                    before = read_back()
                    target = next(t for t in device_config.THEME_IDS if t != before)
                    seen = {}
                    # BOTH SHIPPED LANGUAGES: the UI language is a cookie
                    # the FIRST rendered document has to honour, and "it
                    # saves in English" is not the D-09 floor.
                    for lang in ("en", "fr"):
                        seen[lang] = _persist_without_js(
                            browser.new_context, base_url, "/display", "theme", target, read_back,
                            viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                      "value": lang, "url": base_url}])
                    after = read_back()
                    if str(after) != str(before):
                        return False, (
                            "the scripts-blocked save left the theme at %r, it started at %r — "
                            "a harness that changes a real setting edits its neighbours' "
                            "subject" % (after, before))
                    for lang, result in seen.items():
                        if str(result["stored"]) != str(target):
                            return False, (
                                "lang=%s: the theme did not reach disk, it reads %r"
                                % (lang, result["stored"]))
                        if str(result["restored"]) != str(before):
                            return False, (
                                "lang=%s: the restore leg did not put %r back, disk reads %r"
                                % (lang, before, result["restored"]))

                    # 30-08-PLAN.md Task 2 (CFG-85): the property plan
                    # 30-03 ledgered off this narrowed check ("every
                    # registry theme's radio is present") — restated for
                    # the accordion: every registry theme renders
                    # server-side and owes nothing to a script, whether
                    # its own row is OPEN (departures) or CLOSED
                    # (calendar) at load.
                    n_themes = len(device_config.THEME_IDS)
                    with _no_js_page(browser.new_context, base_url, "/display",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        # calendar_theme_id's own group also carries the
                        # leading "Same as departures" radio (D-09) - one
                        # MORE than the registry, unlike theme, which has
                        # no leading option at all.
                        for field, usage, state, expected in (
                                ("theme", "departures", "open", n_themes),
                                ("calendar_theme_id", "calendar", "closed", n_themes + 1)):
                            count = page.eval_on_selector_all(
                                'input[name="%s"]' % field, "els => els.length")
                            if count != expected:
                                return False, (
                                    "with scripts blocked, expected %d radios named %r (the "
                                    "%s row's own palette, %s by default) with no script "
                                    "involvement in rendering it - found %d"
                                    % (expected, field, usage, state, count))
                    return True, ""
                check(
                    "the theme still SAVES with scripts blocked, at 360px and in BOTH shipped "
                    "languages — operated natively by field name, submitted through the real "
                    "form, re-read FROM DISK after a fresh GET and restored the same way "
                    "(CFG-50/D-09/CFG-85, 25-06-PLAN.md Task 4, narrowed by 30-03-PLAN.md Task 3)",
                    _the_theme_still_saves_with_scripts_blocked)

                # --- 27-07-PLAN.md Task 2 (CFG-68): arrivals and
                # calendar fold the same way, and the arrivals grid gets
                # this plan's OWN scripts-blocked save proof — the
                # <no_js_floor> in 27-07-PLAN.md requires proving the
                # fold did not trap a no-JS reader, not merely that it
                # renders. ------------------------------------------

                def _arrivals_still_saves_with_scripts_blocked():
                    # 30-03-PLAN.md Task 3 (CFG-85): NARROWED, not
                    # deleted, same treatment as the departures twin
                    # above. The trailing strip-probe half (arrivals
                    # carousel chip count, overflow, its own disclosure
                    # opening) is LEDGERED to 30-08 — see
                    # _ASPECT_REPIN_LEDGER below.
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir).get("theme_arriving")

                    original_arriving = read_back()
                    # SEED A KNOWN, NON-NONE STARTING VALUE, through the
                    # validated server API (never a raw file write).
                    # theme_arriving's valid value set includes None
                    # ("Same as departures"), and _persist_once()'s own
                    # "stored is None" guard exists to catch a control
                    # that saves NOTHING — it cannot tell that apart
                    # from a deliberate restore-to-None, so starting
                    # from None would make _persist_without_js()'s own
                    # restore leg raise against a CORRECT outcome.
                    # Cleared back to None (via CLEAR_THEME_ARRIVING) as
                    # this check's LAST act if that is where it started.
                    current_theme = device_config.load_device_config(
                        harness.tmpdir)["theme"]
                    seed = next(
                        t for t in device_config.THEME_IDS if t != current_theme)
                    device_config.save_device_config(harness.tmpdir, theme_arriving=seed)
                    before = read_back()
                    if before != seed:
                        return False, (
                            "the seeded theme_arriving did not read back as written: %r"
                            % (before,))
                    target = next(t for t in device_config.THEME_IDS if t != before)

                    try:
                        seen = {}
                        for lang in ("en", "fr"):
                            seen[lang] = _persist_without_js(
                                browser.new_context, base_url, "/display", "theme_arriving", target,
                                read_back, viewport=VIEWPORT_MIN_SUPPORTED,
                                cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                          "value": lang, "url": base_url}])
                        after = read_back()
                        if str(after) != str(before):
                            return False, (
                                "the scripts-blocked save left theme_arriving at %r, it "
                                "started (seeded) at %r — a harness that changes a real "
                                "setting edits its neighbours' subject" % (after, before))
                        for lang, result in seen.items():
                            if str(result["stored"]) != str(target):
                                return False, (
                                    "lang=%s: theme_arriving did not reach disk, it reads %r"
                                    % (lang, result["stored"]))
                            if str(result["restored"]) != str(before):
                                return False, (
                                    "lang=%s: the restore leg did not put %r back, disk "
                                    "reads %r" % (lang, before, result["restored"]))

                        # 30-08-PLAN.md Task 2 (CFG-85): the property
                        # plan 30-03 ledgered off this narrowed check —
                        # restated for the accordion, from the arrivals
                        # twin's own perspective: every registry theme
                        # renders server-side with no script involvement
                        # whether its own row is CLOSED (arrivals, the
                        # default) or OPEN (departures).
                        n_themes = len(device_config.THEME_IDS)
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            # theme_arriving's own group also carries the
                            # leading "Same as departures" radio (D-09) -
                            # one MORE than the registry, unlike theme,
                            # which has no leading option at all.
                            for field, usage, state, expected in (
                                    ("theme_arriving", "arrivals", "closed", n_themes + 1),
                                    ("theme", "departures", "open", n_themes)):
                                count = page.eval_on_selector_all(
                                    'input[name="%s"]' % field, "els => els.length")
                                if count != expected:
                                    return False, (
                                        "with scripts blocked, expected %d radios named %r "
                                        "(the %s row's own palette, %s by default) with no "
                                        "script involvement in rendering it - found %d"
                                        % (expected, field, usage, state, count))

                        return True, ""
                    finally:
                        # LAST ACT: put theme_arriving back exactly
                        # where this check found it, through the SAME
                        # validated server API it was seeded with.
                        if original_arriving is None:
                            device_config.save_device_config(
                                harness.tmpdir,
                                theme_arriving=device_config.CLEAR_THEME_ARRIVING)
                        else:
                            device_config.save_device_config(
                                harness.tmpdir, theme_arriving=original_arriving)
                        final = read_back()
                        if final != original_arriving:
                            raise AssertionError(
                                "restoring theme_arriving failed: wanted %r, disk reads %r"
                                % (original_arriving, final))
                check(
                    "the arrivals grid still SAVES with scripts blocked, at 360px and in BOTH "
                    "shipped languages — operated natively by field name, submitted through "
                    "the real form, re-read FROM DISK after a fresh GET and restored the same "
                    "way (seeded through the validated save_device_config() API rather than a "
                    "raw file write, since theme_arriving's own None state would otherwise "
                    "defeat the shared helper's stored-is-None save-floor guard) (CFG-68/"
                    "CFG-85, 27-07-PLAN.md Task 2, narrowed by 30-03-PLAN.md Task 3)",
                    _arrivals_still_saves_with_scripts_blocked)

                # 30-03-PLAN.md Task 3 (CFG-85): two checks used to live
                # here — _each_carousels_own_disclosure_toggles_only_
                # its_own_strip and _arrivals_and_calendar_keep_the_
                # focused_chip_in_view_when_keyed — both drove real
                # scroll-snap-strip/pager/disclosure interactions that
                # have no equivalent in a wrapping grid. RETIRED
                # OUTRIGHT — no ledger row; scroll-into-view and
                # per-carousel disclosure toggling have no meaning once
                # the strip becomes a native accordion over a static
                # grid.

                # ==========================================================
                # 30-08-PLAN.md Task 2 (CFG-85): the phase's closing
                # browser proofs — the last unproven behaviour (hover/
                # focus preview-follow), the accordion's own scripts-
                # blocked operability, and the measured touch-target
                # floors. Clears every remaining _ASPECT_REPIN_LEDGER row
                # in this file.
                # ==========================================================

                def _keying_the_palette_moves_the_preview():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _keying_the_strip_selects_scrolls_into_view_and_
                    # moves_the_preview. The scroll-into-view and pager
                    # halves of that check's own property have no
                    # equivalent over a static wrapping grid; what
                    # survives, and is proven here, is the part that
                    # never depended on a strip at all: native radiogroup
                    # keyboard navigation (ArrowDown) still moves the
                    # SELECTION, and theme-preview.js's own delegated
                    # change listener still follows it to the live
                    # preview, settled fully opaque.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        checked_value = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"]:checked', "el => el.value")
                        page.focus(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"][value="%s"]' % checked_value)
                        page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(200)
                        new_value = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"]:checked', "el => el.value")
                        if new_value == checked_value:
                            return False, (
                                "ArrowDown inside the departures palette's native radiogroup "
                                "did not move the checked selection off %r" % (checked_value,))
                        expected_src = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"][value="%s"]' % new_value,
                            "el => el.closest('.palette-chip').getAttribute('data-preview-src')")
                        try:
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected"
                                " && parseFloat(getComputedStyle(img).opacity) === 1; }",
                                arg={"sel": THEME_PREVIEW_SEL, "expected": expected_src},
                                timeout=3000)
                        except Exception:
                            live_src = page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")
                            return False, (
                                "expected the live preview to settle on %r (the newly "
                                "ArrowDown-selected chip's own data-preview-src), fully opaque, "
                                "after keying the palette with no click at all - it reads %r"
                                % (expected_src, live_src))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "arrow-keying the departures palette's native radiogroup (no click at all) "
                    "still moves the checked selection, and the live preview still follows it "
                    "via theme-preview.js's own delegated change listener, settled fully opaque "
                    "- the one property _keying_the_strip_selects_scrolls_into_view_and_moves_"
                    "the_preview proved that survives a static wrapping grid with no strip/"
                    "scroll/pager to key through (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, "
                    "CFG-85)",
                    _keying_the_palette_moves_the_preview)

                def _the_preview_follows_hover_and_focus_and_selects_nothing():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _scrolling_a_strip_moves_its_own_preview_to_the_
                    # centered_chip_and_selects_nothing. The scroll-to-
                    # centred-chip mechanism that retired check measured
                    # has no meaning once there is nothing to scroll; the
                    # SAME underlying property (the preview can show
                    # something other than the saved selection, non-
                    # destructively) is re-keyed here onto hover and
                    # keyboard focus - theme-preview.js's own genuinely
                    # NEW interaction (30-RESEARCH.md Pitfall 4: there was
                    # no existing hover/focus code to "re-key", this is
                    # new code proven here for the first time).
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        def read_back():
                            return device_config.load_device_config(harness.tmpdir)["theme"]

                        def preview_src():
                            return page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

                        def checked_value():
                            return page.eval_on_selector(
                                'details.usage-row[data-usage="departures"] '
                                'input[name="theme"]:checked', "el => el.value")

                        # TWO selectors, deliberately, not one: the radio
                        # itself is visually-hidden via `clip-path:
                        # inset(50%)` (this app's own selectable-card
                        # idiom, `_click_control()`'s own docstring),
                        # which clips its hit-testable area to nothing -
                        # a REAL pointer hover (unlike page.focus(), which
                        # does not require actionability) can only ever
                        # land on the wrapping, visible <label>.
                        def chip_label_selector(value):
                            return (
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:has('
                                'input[type=radio][value="%s"])' % value)

                        def chip_selector(value):
                            return (
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip input[type=radio][value="%s"]' % value)

                        def wait_for_src(expected):
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected; }",
                                arg={"sel": THEME_PREVIEW_SEL, "expected": expected},
                                timeout=3000)

                        before_disk = read_back()
                        chips = page.evaluate(
                            "() => [...document.querySelectorAll("
                            "'details.usage-row[data-usage=\"departures\"] "
                            "label.palette-chip')]"
                            ".map(c => ({value: c.querySelector('input[type=radio]').value,"
                            " checked: c.querySelector('input[type=radio]').checked,"
                            " src: c.getAttribute('data-preview-src')}))")
                        checked_chip = next((c for c in chips if c["checked"]), None)
                        unchecked = [c for c in chips if not c["checked"]]
                        if checked_chip is None or len(unchecked) < 2:
                            return False, (
                                "expected one checked departures chip and at least 2 unchecked "
                                "siblings to hover, got checked=%r unchecked=%d"
                                % (checked_chip, len(unchecked)))
                        chip_a, chip_b = unchecked[0], unchecked[1]

                        # --- 1. hovering an unchecked chip previews it,
                        #        and selects nothing -------------------
                        page.hover(chip_label_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        if checked_value() != checked_chip["value"]:
                            return False, (
                                "hovering an unchecked chip changed the CHECKED radio from %r "
                                "to %r - a preview must never become a selection"
                                % (checked_chip["value"], checked_value()))
                        if read_back() != before_disk:
                            return False, "hovering an unchecked chip changed the value ON DISK"

                        # --- moving away reverts to the checked chip ---
                        page.hover("body", position={"x": 2, "y": 2})
                        wait_for_src(checked_chip["src"])

                        # --- 2. the same pair, via keyboard focus ------
                        page.focus(chip_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        if checked_value() != checked_chip["value"]:
                            return False, (
                                "keyboard-focusing an unchecked chip changed the CHECKED radio "
                                "from %r to %r" % (checked_chip["value"], checked_value()))
                        page.eval_on_selector(chip_selector(chip_a["value"]), "el => el.blur()")
                        wait_for_src(checked_chip["src"])

                        # --- 3. chip A -> chip B never flashes the
                        #        checked selection's own src in between -
                        page.hover(chip_label_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        page.evaluate(
                            "sel => { var img = document.querySelector(sel);"
                            " window.__paletteHoverFrames = [];"
                            " window.__paletteHoverObserver = new MutationObserver("
                            "   function () {"
                            "     window.__paletteHoverFrames.push(img.getAttribute('src'));"
                            "   });"
                            " window.__paletteHoverObserver.observe("
                            "   img, {attributes: true, attributeFilter: ['src']}); }",
                            THEME_PREVIEW_SEL)
                        page.hover(chip_label_selector(chip_b["value"]))
                        wait_for_src(chip_b["src"])
                        page.wait_for_timeout(200)
                        frames = page.evaluate(
                            "() => { window.__paletteHoverObserver.disconnect();"
                            " return window.__paletteHoverFrames; }")
                        if checked_chip["src"] in frames:
                            return False, (
                                "hovering directly from chip A to chip B passed THROUGH the "
                                "checked selection's own src %r before settling on chip B's own "
                                "%r - frames observed: %r"
                                % (checked_chip["src"], chip_b["src"], frames))
                        final_src = preview_src()
                        if final_src != chip_b["src"]:
                            return False, (
                                "expected the preview to end on chip B's own src %r after "
                                "hovering straight from chip A to chip B, got %r"
                                % (chip_b["src"], final_src))

                        # --- disk is unchanged, start to finish --------
                        if read_back() != before_disk:
                            return False, (
                                "the value on disk changed over the course of this check - "
                                "hovering/focusing must never write a selection")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "hovering or keyboard-focusing an unchecked palette chip previews that "
                    "chip's own theme in the ONE live preview, writing NO radio's checked state "
                    "and NO value on disk; moving the pointer/focus away reverts the preview to "
                    "the checked chip's own src; hovering straight from chip A to chip B never "
                    "passes through the checked selection's own src in between (observed via a "
                    "live MutationObserver on the preview's src attribute), settling on B; and "
                    "the value on disk is unchanged start to finish - the genuinely new "
                    "interaction this phase adds, with no existing hover/focus precedent to "
                    "re-key (30-RESEARCH.md Pitfall 4, _ASPECT_REPIN_LEDGER, 30-08-PLAN.md "
                    "Task 1+2, CFG-85)",
                    _the_preview_follows_hover_and_focus_and_selects_nothing)

                def _the_accordion_is_operable_and_saves_with_scripts_blocked():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _the_no_js_floor_holds_for_both_settings_pages (and,
                    # for the "a closed row's radios still reach disk"
                    # half, for _the_theme_still_saves_with_scripts_
                    # blocked_through_the_carousel/_arrivals_still_saves_
                    # with_scripts_blocked_through_its_own_carousel's own
                    # "the <details> disclosure opens on a click" clause).
                    #
                    # CFG-85's own requirement text reads "every row open
                    # with scripts blocked". A grouped <details
                    # name="aspect-rows"> set is mutually exclusive BY
                    # BROWSER CONSTRUCTION, so that literal wording is
                    # UNACHIEVABLE alongside the zero-script accordion the
                    # developer already approved (30-04-SUMMARY.md's own
                    # <two_recorded_deviations> item 2; 30-03-SUMMARY.md's
                    # own <no_js_floor_note>). What is proved here
                    # instead, and is STRONGER than a visible stack:
                    #   1. all four rows are present, each with its own
                    #      <summary>;
                    #   2. every theme radiogroup is present in the DOM
                    #      at FULL REGISTRY SIZE, including inside CLOSED
                    #      rows - the fact that makes a closed row
                    #      harmless;
                    #   3. a closed row's own <summary> is natively
                    #      activatable by a REAL pointer click with
                    #      scripts blocked, and opening it closes the
                    #      previously-open sibling - the native grouped-
                    #      <details> mechanism CFG-85's zero-script floor
                    #      actually rests on;
                    #   4. a palette selection made INSIDE a row the
                    #      visitor opened THEMSELVES reaches disk, read
                    #      back via device_config.load_device_config(),
                    #      with the restore leg putting the old value
                    #      back.
                    # A check that quietly asserted something weaker than
                    # its own requirement's words is the failure shape
                    # this comment exists to head off.
                    base_url = harness.base_url()
                    n_themes = len(device_config.THEME_IDS)

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir).get("calendar_theme_id")

                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            # --- 1. every row, every summary ----------
                            rows = page.query_selector_all("details.usage-row")
                            if len(rows) != 4:
                                return False, (
                                    "lang=%s: expected 4 usage rows, found %d"
                                    % (lang, len(rows)))
                            for row in rows:
                                if row.query_selector("summary") is None:
                                    return False, (
                                        "lang=%s: a usage row carries no <summary>" % (lang,))

                            # --- 2. full registry size, even closed ---
                            # theme_arriving/calendar_theme_id each also
                            # carry the leading "Same as departures"
                            # radio (D-09) inside the SAME name group -
                            # one MORE than the registry; theme/
                            # rule_theme_id have no leading option.
                            for field, expected in (
                                    ("theme", n_themes),
                                    ("theme_arriving", n_themes + 1),
                                    ("calendar_theme_id", n_themes + 1),
                                    ("rule_theme_id", n_themes)):
                                count = page.eval_on_selector_all(
                                    'input[name="%s"]' % field, "els => els.length")
                                if count != expected:
                                    return False, (
                                        "lang=%s: expected %d radios named %r in the DOM "
                                        "regardless of which row is open, found %d"
                                        % (lang, expected, field, count))

                            # --- 3. grouped exclusivity, real click ---
                            calendar_row = page.query_selector(
                                'details.usage-row[data-usage="calendar"]')
                            departures_row = page.query_selector(
                                'details.usage-row[data-usage="departures"]')
                            if calendar_row.get_attribute("open") is not None:
                                return False, (
                                    "lang=%s: expected the calendar row closed at load"
                                    % (lang,))
                            if departures_row.get_attribute("open") is None:
                                return False, (
                                    "lang=%s: expected the departures row open at load"
                                    % (lang,))
                            calendar_row.query_selector("summary").click()
                            if calendar_row.get_attribute("open") is None:
                                return False, (
                                    "lang=%s: a real pointer click on a closed row's own "
                                    "<summary> did not open it, with scripts blocked" % (lang,))
                            if departures_row.get_attribute("open") is not None:
                                return False, (
                                    "lang=%s: opening the calendar row did not close its "
                                    "previously-open sibling - the native grouped-<details> "
                                    "behaviour CFG-85's zero-script floor rests on" % (lang,))

                            # --- 4. a selection made in the row the
                            #        visitor just opened reaches disk ---
                            before = read_back()
                            target = next(
                                t for t in device_config.THEME_IDS if t != before)
                            _click_control(
                                page,
                                'input[name="calendar_theme_id"][value="%s"]' % target)
                            held = page.eval_on_selector(
                                'input[name="calendar_theme_id"][value="%s"]' % target,
                                "el => el.checked")
                            if not held:
                                return False, (
                                    "lang=%s: the browser refused to check calendar_theme_id=%r "
                                    "with scripts blocked" % (lang, target))
                            # ARMED before the click, matching
                            # _persist_once()'s own established sequence
                            # — a wait AFTER the click races the
                            # navigation the click itself starts, and
                            # this context's own close() below can abort
                            # an in-flight request that lost that race.
                            with page.expect_navigation():
                                via = page.evaluate(
                                    _SUBMIT_PROBE, {"field": "calendar_theme_id"})

                        stored = read_back()
                        if str(stored) != str(target):
                            return False, (
                                "lang=%s: a selection made inside a row the visitor opened "
                                "themselves (via the %s) did NOT reach disk - expected %r, "
                                "got %r" % (lang, via, target, stored))

                        # --- restore, through the validated server API -
                        # calendar_theme_id=None means "not supplied,
                        # carry forward" at the WRITE path (unlike the
                        # READ path's own normalise_calendar_theme_id(),
                        # which degrades a non-member value TO None) - so
                        # restoring an originally-unset value needs the
                        # empty string, its own documented clear signal,
                        # never the bare None a "leave unchanged" write
                        # would silently no-op against.
                        device_config.save_device_config(
                            harness.tmpdir,
                            calendar_theme_id=before if before is not None else "")
                        restored = read_back()
                        if restored != before:
                            raise AssertionError(
                                "restoring calendar_theme_id failed: wanted %r, disk reads %r"
                                % (before, restored))
                    return True, ""
                check(
                    "with scripts blocked, in BOTH languages, at 360px: all 4 usage rows carry "
                    "their own <summary>; every registry theme's radio (theme/theme_arriving/"
                    "calendar_theme_id/rule_theme_id) is present in the DOM at full registry "
                    "size regardless of which row is open; a REAL pointer click on a closed "
                    "row's own <summary> opens it and closes the previously-open sibling (the "
                    "native grouped <details name=\"aspect-rows\"> mechanism); and a palette "
                    "selection made INSIDE the row the visitor just opened themselves reaches "
                    "disk, read back via device_config.load_device_config(), with the restore "
                    "leg putting the old value back - CFG-85's own \"every row open\" wording is "
                    "unachievable alongside the grouped, mutually-exclusive accordion the "
                    "developer already approved, and this check's own comment states that "
                    "discrepancy plainly rather than narrowing the claim "
                    "(_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)",
                    _the_accordion_is_operable_and_saves_with_scripts_blocked)

                def _the_palette_meets_its_floors_at_360px_in_both_themes():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _the_carousel_meets_its_floors_at_360px_in_both_
                    # themes. Every geometry/paint assertion the retired
                    # check made was read off the retiring strip/pager
                    # DOM shape directly; this is 30-UI-SPEC.md's own
                    # Touch Targets table, MEASURED (never declared)
                    # fresh against the real .palette-chip/.usage-row/
                    # .leading-option/.rule-add markup.
                    base_url = harness.base_url()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        def open_row(usage):
                            # IDEMPOTENT, deliberately: a grouped
                            # <details name="aspect-rows"> summary click
                            # TOGGLES, so clicking an ALREADY-open row
                            # (departures, the server's own default)
                            # would CLOSE it rather than leave it open -
                            # measured directly on this tree: a closed
                            # row's own content keeps a real, non-zero
                            # getBoundingClientRect() in this browser
                            # (layout is retained for cheap re-display)
                            # while its PAINT and HIT-TEST are
                            # suppressed, so an unconditional click here
                            # would make _assert_hit_target() report a
                            # spurious "occluded" failure against a row
                            # that was never meant to be closed.
                            row = page.query_selector(
                                'details.usage-row[data-usage="%s"]' % usage)
                            if row.get_attribute("open") is None:
                                row.query_selector("summary").click()

                        for theme in UI_THEMES_EXPLICIT:
                            _set_ui_theme(page, theme)
                            theme_record = {}

                            # --- the open row's FIRST/LAST palette-chip
                            open_row("departures")
                            chip_count = page.eval_on_selector_all(
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip', "els => els.length")
                            if chip_count < 2:
                                return False, (
                                    "theme=%s: expected at least 2 .palette-chip in the open "
                                    "departures row, found %d" % (theme, chip_count))
                            theme_record["chip_first"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:first-of-type',
                                "theme=%s: the FIRST palette-chip in the open departures row"
                                % theme)
                            theme_record["chip_last"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:last-of-type',
                                "theme=%s: the LAST palette-chip in the open departures row"
                                % theme)

                            # --- the usage-row <summary> (always visible)
                            theme_record["row_summary"] = _assert_hit_target(
                                page, 'details.usage-row[data-usage="departures"] > summary',
                                "theme=%s: the departures row's own <summary>" % theme)

                            # --- the arrivals row's leading option -----
                            open_row("arrivals")
                            theme_record["leading_option"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="arrivals"] .leading-option',
                                "theme=%s: the arrivals row's \"Same as departures\" leading "
                                "option" % theme)

                            # --- the nested rule-add <summary> ---------
                            open_row("rules")
                            theme_record["rule_add_summary"] = _assert_hit_target(
                                page, ".rule-add > summary",
                                "theme=%s: the nested \"+ Add rule\" disclosure's own <summary>"
                                % theme)

                            # --- the palette grid never scrolls sideways
                            for usage in ("departures", "arrivals"):
                                open_row(usage)
                                grid = page.eval_on_selector(
                                    'details.usage-row[data-usage="%s"] .palette' % usage,
                                    "el => ({scrollWidth: el.scrollWidth,"
                                    " clientWidth: el.clientWidth})")
                                if grid["scrollWidth"] > grid["clientWidth"]:
                                    return False, (
                                        "theme=%s: the %s row's own .palette grid scrolls "
                                        "horizontally - scrollWidth %r > clientWidth %r, "
                                        "exactly the strip CFG-85 retires"
                                        % (theme, usage, grid["scrollWidth"],
                                           grid["clientWidth"]))

                            # --- the page itself never overflows sideways
                            msg = _assert_no_page_overflow(
                                page, "the Aspect card on /display (theme=%s)" % theme,
                                VIEWPORT_MIN_SUPPORTED["width"])
                            if msg:
                                return False, msg

                            # --- the swatch paints distinct from its
                            #     own surrounding chip surface ----------
                            # Deliberately the "black" theme, not the
                            # FIRST chip: THEME_IDS[0] is "white" (a
                            # solid #FFFFFF fill), and --color-dominant
                            # is ALSO #FFFFFF in light mode (style.css) -
                            # a white swatch on a white card surface is
                            # a REAL, correct product fact (the chip's
                            # own border is what distinguishes it there),
                            # never the "invisible swatch" defect this
                            # clause exists to catch. "black" fills
                            # #000000, which differs from BOTH themes'
                            # own --color-dominant (#FFFFFF light,
                            # #151922 dark).
                            open_row("departures")
                            paint = page.eval_on_selector(
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:has(input[type=radio][value="black"])',
                                "el => { var swatch = el.querySelector('.palette-swatch');"
                                " var chip = getComputedStyle(el);"
                                " return {swatch: getComputedStyle(swatch).backgroundColor,"
                                " chipSurface: chip.backgroundColor}; }")
                            if paint["swatch"] == paint["chipSurface"]:
                                return False, (
                                    "theme=%s: the 'black' palette-chip's own swatch paints "
                                    "IDENTICALLY to its surrounding chip surface (%r) - a "
                                    "swatch invisible against its own card is the defect a "
                                    "hit-target measurement cannot see" % (theme, paint["swatch"]))
                            theme_record["paint"] = paint

                            recorded[theme] = theme_record
                        # 30-08-PLAN.md Task 2's own required artifact:
                        # every measured box, printed for the SUMMARY -
                        # a measurement nobody can read back off the
                        # check's own PASS line otherwise.
                        for theme, rec in recorded.items():
                            for control in (
                                    "chip_first", "chip_last", "row_summary",
                                    "leading_option", "rule_add_summary"):
                                seen = rec[control]
                                print(
                                    "        [30-08 T2] theme=%s %s: hit=%r visual=%r"
                                    % (theme, control, seen["hit"], seen["visual"]))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "30-UI-SPEC.md's Touch Targets table, MEASURED (never declared) in each "
                    "control's own container, in both UI themes, at the 360px contract floor: "
                    "the open row's first and last .palette-chip, the usage-row's own <summary>, "
                    "the arrivals row's leading \"Same as departures\" option, and the nested "
                    "rule-add disclosure's own <summary> all clear 44px; the palette grid never "
                    "scrolls horizontally, the page itself never overflows sideways, and the "
                    "swatch paints visibly distinct from its own surrounding chip surface in "
                    "both themes (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)",
                    _the_palette_meets_its_floors_at_360px_in_both_themes)

                # --- 27-03-PLAN.md Task 3 (CFG-64) -----------------------

                def _the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies():
                    """CFG-64: 27-03-PLAN.md Task 2 reverted the
                    fallback-hide rule from the two-marker
                    `.dirty-ready.dirty-shown` gate to the plain `.js`
                    gate 06.6.4.1-01 originally shipped. This is the
                    proof that the floor UNDER that change still holds —
                    a value on DISK, never a rendering — using
                    tracked_runway, the same field and the same
                    form="settings-form" mutation 25-03's own M20
                    recorded (25-03-SUMMARY.md), because the subject
                    under test is the identical no-JS save path, now
                    reached through a simplified gate rather than a
                    proven-live save bar.

                    Unlike 25-03's own check, which corroborates with the
                    runway MAP's presence, this one asserts the SUBMIT
                    itself — the element the simplified gate actually
                    governs — is present and VISIBLE AFTER the save. A
                    check that only asked whether it renders would pass
                    against the exact defect Phase 22's P0 found; a check
                    that only asked whether it renders would ALSO pass
                    against a submit whose value never reaches disk. This
                    check carries both facts about the one relationship
                    that matters, deliberately never split into two.
                    """
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"]

                    before = read_back()
                    target = next(r for r in device_config.RUNWAY_IDS if r != before)
                    seen = {}
                    # BOTH SHIPPED LANGUAGES, at the 360px floor: the UI
                    # language is a cookie the FIRST rendered document
                    # already has to honour, and "it saves in English" is
                    # not the D-09 floor.
                    for lang in ("en", "fr"):
                        seen[lang] = _persist_without_js(
                            browser.new_context, base_url, "/display", "tracked_runway",
                            target, read_back, viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                      "value": lang, "url": base_url}])
                    after = read_back()
                    if str(after) != str(before):
                        return False, (
                            "the scripts-blocked save left tracked_runway at %r, it started at "
                            "%r — a harness that changes a real setting is a test that edits "
                            "its neighbours' subject" % (after, before))
                    for lang, result in seen.items():
                        if str(result["stored"]) != str(target):
                            return False, (
                                "lang=%s: tracked_runway did not reach disk, it reads %r"
                                % (lang, result["stored"]))
                        if str(result["restored"]) != str(before):
                            return False, (
                                "lang=%s: the restore leg did not put %r back, disk reads %r"
                                % (lang, before, result["restored"]))

                    # AND THE SUBMIT ITSELF, ASSERTED AFTER THE SAVE
                    # ABOVE — never before, and never in its place. A
                    # rendering can never stand in for the save this
                    # check just proved.
                    with _no_js_page(browser.new_context, base_url, "/display",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        submit = page.locator(
                            "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                        if submit.count() != 1:
                            return False, (
                                "expected exactly one fallback submit with scripts blocked "
                                "AFTER the save above, found %d" % submit.count())
                        if not submit.is_visible():
                            return False, (
                                "the fallback submit rendered but is not VISIBLE with scripts "
                                "blocked after the save — this is precisely the shape Phase "
                                "22's P0 took")
                    return True, ""
                check(
                    "the no-JS floor still SAVES TO DISK after the gate simplifies to the "
                    "plain .js rule (CFG-64) — tracked_runway operated natively, submitted "
                    "through the real form, re-read FROM DISK after a fresh GET, in BOTH "
                    "shipped languages, at 360px, restored as the last act (the same field and "
                    "mutation 25-03's own M20 recorded) — and the data-static-save-fallback "
                    "submit is present and VISIBLE on that scripts-blocked page AFTER the save, "
                    "so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3)",
                    _the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies)

                # ==========================================================
                # 27-04-PLAN.md Task 4 (CFG-63/CFG-71): THE two checks —
                # a scripted save proven on disk, and its failure proven
                # honest. Two endpoints (a DOM read and a disk read) are
                # not a relationship; this plan's whole discipline is to
                # assert them as ONE.
                # ==========================================================

                def _the_bar_settles_the_field_disk_agree_and_the_bar_hides():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not
                    # a mechanical swap — this check's own retired-region
                    # ordering clause is gone with the region, and its
                    # never-visible-save-button clauses asserted CFG-63's
                    # own "no save button" contract verbatim, which THIS
                    # phase reverses. Left mechanical, it would either fail
                    # immediately or, worse, "fixed" by loosening the
                    # selector, pass while asserting the opposite of the
                    # current requirement. Rewritten as the bar's own
                    # settle contract, keeping the three-way agreement
                    # shape (field / bar / disk) that was worth
                    # preserving, on different surfaces.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/display")

                        # Precondition: the bar starts hidden (script has
                        # proven itself live).
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_visible():
                            return False, "expected the bar to be hidden before any edit"

                        before = str(device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"])
                        target = next(
                            r for r in device_config.RUNWAY_IDS if r != before)

                        # a. CHANGE A FIELD: the bar reveals, the count
                        # names the section, the field shows the new
                        # value, and disk STILL shows the OLD value — the
                        # bar means *unsaved*, and asserting disk is
                        # untouched at this point is strictly stronger
                        # than anything the retired check ever asserted.
                        _click_control(page, 'input[name="tracked_runway"][value="%s"]' % target)
                        _wait_for_bar(page)
                        if not _bar_text(page):
                            return False, (
                                "expected [data-dirty-count] to name the changed section once "
                                "the bar reveals")
                        field_now = str(page.eval_on_selector(
                            'input[name="tracked_runway"]:checked', "el => el.value"))
                        if field_now != target:
                            return False, (
                                "expected the field's own DOM value to already read %r, got %r"
                                % (target, field_now))
                        disk_before_save = str(device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"])
                        if disk_before_save != before:
                            return False, (
                                "expected disk to still read %r while the bar is visible and "
                                "unsaved, got %r — the bar means UNSAVED" % (before, disk_before_save))

                        # b. CLICK ENREGISTRER — a real navigation.
                        _save_via_bar(page)

                        # c. AFTER THE NAVIGATION: field, bar and disk all
                        # agree on the new value — three surfaces, same
                        # shape as the retired check's own field/disk
                        # agreement, now including the bar's own hidden
                        # state as the third.
                        _assert_surfaces_agree(
                            page,
                            {
                                "the field's own DOM value": lambda: str(page.eval_on_selector(
                                    'input[name="tracked_runway"]:checked', "el => el.value")),
                                "the value on disk": lambda: str(device_config.load_device_config(
                                    harness.tmpdir)["tracked_runway"]),
                            },
                            requested=target, before=before,
                            where="Display's runway card after the bar's own save settles")
                        if page.locator("[data-dirty-bar]").is_visible():
                            return False, (
                                "expected the bar to be HIDDEN after the navigation lands — a "
                                "bar still visible after a successful save means the save was "
                                "never recorded as settled")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the bar's own settle contract: changing a field REVEALS the bar, names the "
                    "changed section, updates the field's own DOM value, and leaves DISK "
                    "UNTOUCHED (the bar means unsaved, stronger than anything the retired check "
                    "asserted); clicking Enregistrer causes a real navigation; and after it lands "
                    "the field, the bar (now HIDDEN) and disk all agree on the requested value — "
                    "three surfaces, on different surfaces than before (CFG-63/CFG-71/CFG-77/"
                    "CFG-78, 27-04-PLAN.md Task 4; retargeted onto the restored bar by "
                    "28-10-PLAN.md Task 2, which also retires the CFG-63 'no save button visible' "
                    "clause this check used to assert)",
                    _the_bar_settles_the_field_disk_agree_and_the_bar_hides)

                def _a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched():
                    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED —
                    # the failure surface changed from a toast to an
                    # inline error. The settings form no longer raises
                    # .quick-toast at all; announceFailure() is
                    # EXCLUSIVELY quick-switch.js's now, serving the
                    # three role="switch" controls. A rejected value
                    # re-renders the SAME page at 200 with the field's
                    # OWN inline error (_field_error_html()'s existing
                    # D-07 shape), echoes the user's rejected text back
                    # so they can fix it rather than retype it, and
                    # leaves disk untouched — the two surviving clauses
                    # ("claims nothing", "disk is untouched") kept at
                    # full strength; the toast clause replaced with the
                    # inline-error one, plus an explicit NEGATIVE that no
                    # toast appears on this path at all, so the two
                    # failure mechanisms (this one and quick-switch.js's
                    # own) cannot be accidentally re-merged later.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/device")

                        before = str(device_config.load_device_config(
                            harness.tmpdir)["wake_interval_s"])
                        # Below server/device_config.py's own WAKE_INTERVAL_MIN_S
                        # (60) — a genuine server-side rejection, exercising
                        # the 200-is-not-a-redirect branch, never a
                        # client-side shortcut.
                        rejected = "30"

                        wake_sel = 'input[name="wake_interval_s"]'
                        page.eval_on_selector(wake_sel, "el => el.focus()")
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.type(rejected)
                        page.keyboard.press("Tab")
                        _wait_for_bar(page)
                        # config_page.py's own wake_interval_group()
                        # comment documents this exact hazard: the native
                        # <input type="number" min="%d" max="%d"> means an
                        # out-of-range value fails HTML5 constraint
                        # validation, which blocks the browser from ever
                        # SUBMITTING the form at all — no request reaches
                        # the server, so this check's own subject (the
                        # SERVER's own rejection path) would never run.
                        # The real production hazard this validates
                        # against is a pre-existing out-of-range value
                        # already on disk/env (config_page.py's own
                        # comment names SKYPANE_SLEEP_S=30), which never
                        # goes through this client-side gate at all.
                        # noValidate disables only the BROWSER's own
                        # pre-flight check for this one native submit —
                        # the request that follows is still a REAL native
                        # POST, never a fetch shortcut, so the server's
                        # own validation is what is actually exercised.
                        page.eval_on_selector(
                            "#%s" % config_page.SETTINGS_FORM_ID,
                            "el => { el.noValidate = true; }")
                        _save_via_bar(page)

                        # 1. THE INLINE ERROR IS PRESENT AND NAMES THE
                        # FIELD — the field's own aria-describedby points
                        # at it (programmatic association, D-07/
                        # _field_error_attrs(), never merely visual
                        # adjacency), and its own text is non-empty.
                        described_by = page.get_attribute(wake_sel, "aria-describedby") or ""
                        if "wake-interval-s-error" not in described_by:
                            return False, (
                                "expected %r's own aria-describedby to name its error anchor "
                                "(wake-interval-s-error), got %r" % (wake_sel, described_by))
                        error_el = page.locator("#wake-interval-s-error")
                        if not error_el.count() or not (error_el.inner_text() or "").strip():
                            return False, (
                                "expected a non-empty inline error at #wake-interval-s-error")

                        # 2. THE USER'S REJECTED INPUT IS ECHOED BACK —
                        # not the on-disk value — so they can fix it
                        # rather than retype it (D-07's echo rule).
                        echoed = page.input_value(wake_sel)
                        if echoed != rejected:
                            return False, (
                                "expected the field to echo back the user's own rejected input "
                                "%r, got %r" % (rejected, echoed))

                        # 3. DISK IS UNTOUCHED — kept at full strength
                        # from the retired check.
                        stored = str(device_config.load_device_config(
                            harness.tmpdir)["wake_interval_s"])
                        if stored == rejected:
                            return False, (
                                "the rejected value %r reached disk — a validation failure must "
                                "never be mistaken for a save" % (rejected,))
                        if stored != before:
                            return False, (
                                "expected the stored wake interval to stay UNCHANGED at %r after "
                                "a rejected save, got %r" % (before, stored))

                        # 4. THE EXPLICIT NEGATIVE — no .quick-toast on
                        # this path at all. quick-switch.js's own
                        # TOAST_ATTR element renders PRESENT but
                        # class="quick-toast" (no "is-visible") by
                        # default — Playwright's own is_visible() would
                        # still call that VISIBLE (a non-empty box at
                        # opacity: 0 is not display:none/visibility:
                        # hidden), so the class itself, the same idiom
                        # announceFailure() uses to reveal it, is what
                        # this check has to read.
                        toast_class = page.eval_on_selector(
                            "body", "el => { var t = el.querySelector('[data-quick-toast]'); "
                            "return t ? t.className : null; }")
                        if toast_class and "is-visible" in toast_class.split():
                            return False, (
                                "expected NO .quick-toast on the settings form's own "
                                "rejected-value path — announceFailure() is exclusively "
                                "quick-switch.js's now, got class=%r" % (toast_class,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a value the server's own validation rejects (wake_interval_s below its "
                    "floor) re-renders the SAME page with the field's OWN inline error, "
                    "programmatically associated via aria-describedby and naming the field; "
                    "echoes the user's rejected input back into the field rather than the "
                    "on-disk value (D-07's echo rule); leaves disk UNCHANGED; and raises NO "
                    ".quick-toast at all on this path — the explicit negative that keeps this "
                    "failure surface and quick-switch.js's own toast from merging (CFG-63/"
                    "CFG-71, 27-04-PLAN.md Task 4; retargeted from the toast onto the native "
                    "inline-error path by 28-10-PLAN.md Task 3, CFG-77/CFG-78)",
                    _a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched)

                # 30-03-PLAN.md Task 3 (CFG-85): two checks used to live
                # here — _keying_the_strip_selects_scrolls_into_view_and_
                # moves_the_preview and _scrolling_a_strip_moves_its_own_
                # preview_to_the_centered_chip_and_selects_nothing — both
                # drove real scroll-snap-strip geometry (scroll-into-view
                # on arrow-key selection, geometric-centre scroll-tracking
                # for the preview) that has no equivalent over a static
                # wrapping grid. RETIRED, and LEDGERED to 30-08: keying's
                # surviving half (arrow-keying the radiogroup still moves
                # the preview) and scrolling's surviving half (preview-is-
                # not-selection: hover/focus previews a theme and never
                # writes a radio, a change event or a form value) — see
                # _ASPECT_REPIN_LEDGER below.


                # --- 28-11-PLAN.md Task 1 (CFG-77): the section-naming
                # relationship — CFG-77 says the bar names the changed
                # section(s), in document order, not click order. A check
                # that merely asserted the bar became visible would pass
                # against a bar stuck on its raw-count fallback branch
                # ("1 unsaved change" forever, dirty-state.js's own
                # updateBar()), which is not this clause.
                def _section_naming_reflects_the_fields_actually_changed_in_document_order():
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            def wait_for_bar_text(expected, timeout=5000):
                                page.wait_for_function(
                                    "args => {"
                                    " var el = document.querySelector('[data-dirty-count]');"
                                    " return !!el && el.textContent === args.expected;}",
                                    arg={"expected": expected}, timeout=timeout)

                            runway_sel = 'input[name="tracked_runway"]'
                            current_runway = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            target_runway = next(
                                r for r in device_config.RUNWAY_IDS if r != current_runway)

                            current_quiet_start = page.input_value(
                                'input[name="quiet_hours_start"]')
                            target_quiet_start = (
                                "05:00" if current_quiet_start != "05:00" else "06:00")

                            # Built from the bar's OWN data-dirty-* words
                            # and each section wrapper's OWN label —
                            # never a hardcoded English/French literal, so
                            # this check works unchanged in either
                            # language (the suite's existing D-06 idiom).
                            runway_label = page.eval_on_selector(
                                runway_sel,
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            quiet_label = page.eval_on_selector(
                                'input[name="quiet_hours_start"]',
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            changed_suffix = page.eval_on_selector(
                                "[data-dirty-bar]",
                                "el => el.getAttribute('data-dirty-changed-suffix')")
                            and_word = page.eval_on_selector(
                                "[data-dirty-bar]", "el => el.getAttribute('data-dirty-and')")

                            expected_one = runway_label + changed_suffix
                            expected_two = (
                                runway_label + and_word + quiet_label + changed_suffix)

                            # Phase A: ONE changed field (Runway). The bar
                            # names ONLY it.
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))
                            _wait_for_bar(page)
                            actual_one = _bar_text(page)
                            if actual_one != expected_one:
                                return False, (
                                    "lang=%s: expected [data-dirty-count] to read %r for a "
                                    "single changed field (Runway), got %r"
                                    % (lang, expected_one, actual_one))

                            # Phase B: ALSO change a Quiet hours field.
                            # The bar names BOTH, Runway before Quiet
                            # hours — DOCUMENT order (Runway's own
                            # [data-dirty-section] wrapper precedes Quiet
                            # hours' on the Display page). Runway was
                            # clicked first in THIS pass too, so this
                            # alone cannot distinguish document order from
                            # click order — the reversed pass below does.
                            page.fill(
                                'input[name="quiet_hours_start"]', target_quiet_start)
                            _commit_field(page, 'input[name="quiet_hours_start"]')
                            wait_for_bar_text(expected_two)

                            # Fresh load, REVERSED click order: Quiet
                            # hours first, Runway second. dirtySection
                            # Labels() walks the DOCUMENT, so the bar must
                            # still read Runway before Quiet hours — a
                            # CLICK-order implementation would pass the
                            # first ordering above and fail THIS one.
                            page.goto(base_url + "/display")
                            page.fill(
                                'input[name="quiet_hours_start"]', target_quiet_start)
                            _commit_field(page, 'input[name="quiet_hours_start"]')
                            _wait_for_bar(page)
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))
                            wait_for_bar_text(expected_two)
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the bar's own [data-dirty-count] names which section(s) actually changed, "
                    "built from the bar's own data-dirty-* attributes plus each section "
                    "wrapper's own label — never hardcoded English/French, never merely 'the "
                    "bar is visible' or 'the text is non-empty': a single changed Runway field "
                    "reads exactly that wrapper's own label plus the changed-suffix, and a "
                    "second, different-section change (Quiet hours) reads the two-item join "
                    "with Runway BEFORE Quiet hours in BOTH click orders — the reversed-order "
                    "pass is what proves DOCUMENT order rather than click order, since "
                    "dirtySectionLabels() walks the document and Runway's own wrapper precedes "
                    "Quiet hours' on Display regardless of which the visitor touches first; run "
                    "in both site languages (CFG-77, 28-11-PLAN.md Task 1)",
                    _section_naming_reflects_the_fields_actually_changed_in_document_order)

                # --- 28-11-PLAN.md Task 2 (CFG-77): Cancel's side
                # effects, read off the RESULTING DOM — never by spying on
                # refresh()/repaintAll(). 28-08 built the mechanism (a
                # single setTimeout(fn, 0) deferred tick inside
                # dirty-state.js's reset handler, calling BOTH
                # window.SkyPaneLivePreview.refresh() and
                # value-controls.js's exported repaintAll() once the
                # native reset has actually restored the fields); this
                # check proves the DOM STATE that mechanism produces.
                #
                # CONTEXT.md separately claimed the quiet-hours dial
                # repaints "for free" because value-controls.js's
                # document-level click listener fires on the Cancel
                # button's own click. That claim is FALSE BY
                # SPECIFICATION, already refuted in writing by 28-08: a
                # click on a <button type="reset"> dispatches and bubbles
                # to COMPLETION before the button's own default action —
                # the reset — runs, so that listener repaints the dial
                # from the EDITED values the user just asked to discard.
                # This check does not re-open that as an empirical
                # question; Mutation 2 (see this plan's own SUMMARY)
                # records the stale-repaint observation as CORROBORATION
                # of 28-08's spec argument, never as a fresh finding.
                def _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        def handle_values():
                            return (
                                int(page.get_attribute(
                                    _handle_sel("quiet_hours_start"), "aria-valuenow")),
                                int(page.get_attribute(
                                    _handle_sel("quiet_hours_end"), "aria-valuenow")),
                            )

                        def preview_src():
                            return page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

                        # --- Setup: record the pre-edit state of every
                        # surface, off the DOM.
                        original_theme = page.eval_on_selector(
                            'input[name="theme"]:checked', "el => el.value")
                        original_preview_src = preview_src()
                        original_arc = _quiet_arc_minutes(page, "before the edit")
                        original_handles = handle_values()

                        target_theme = next(
                            t for t in device_config.THEME_IDS if t != original_theme)
                        # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from
                        # .theme-chip to .palette-chip - the departures
                        # radio's own wrapping label class changed under
                        # the accordion rebuild, the data-preview-src
                        # attribute it carries did not.
                        target_preview_src = page.eval_on_selector(
                            'input[name="theme"][value="%s"]' % target_theme,
                            "el => el.closest('.palette-chip')"
                            ".getAttribute('data-preview-src')")

                        current_start = page.input_value(
                            'input[name="quiet_hours_start"]')
                        target_start = "05:00" if current_start != "05:00" else "06:00"

                        # --- Edit: a DIFFERENT theme via a carousel chip,
                        # AND a different quiet-hours window. Confirm both
                        # surfaces actually MOVED before Cancel — a no-op
                        # edit would make every assertion below vacuous.
                        _click_control(
                            page, 'input[name="theme"][value="%s"]' % target_theme)
                        _wait_for_bar(page)
                        page.wait_for_function(
                            "args => { var img = document.querySelector(args.sel);"
                            " return !!img && img.getAttribute('src') === args.expected; }",
                            arg={"sel": THEME_PREVIEW_SEL, "expected": target_preview_src})

                        page.fill('input[name="quiet_hours_start"]', target_start)
                        _commit_field(page, 'input[name="quiet_hours_start"]')

                        moved_arc = _quiet_arc_minutes(page, "after the edit, before Cancel")
                        moved_handles = handle_values()
                        if moved_arc == original_arc or moved_handles == original_handles:
                            return False, (
                                "the quiet-hours edit did not move the dial before Cancel: arc "
                                "%r -> %r, handles %r -> %r — a no-op edit proves nothing about "
                                "Cancel"
                                % (original_arc, moved_arc, original_handles, moved_handles))

                        # --- Cancel: a real click on the native
                        # type="reset" button, exercising both the native
                        # reset and 28-08's scripted enhancement at once.
                        page.click("[data-dirty-cancel]")
                        _wait_for_bar_hidden(page)

                        # a. The theme chip's checked state is back to
                        #    the original.
                        try:
                            page.wait_for_function(
                                "args => {"
                                " var f = document.querySelector("
                                "   'input[name=\"theme\"]:checked');"
                                " return !!f && f.value === args.expected; }",
                                arg={"expected": original_theme}, timeout=3000)
                        except Exception:
                            restored_theme = page.eval_on_selector(
                                'input[name="theme"]:checked', "el => el.value")
                            return False, (
                                "expected the theme radio to be restored to %r after Annuler, "
                                "got %r" % (original_theme, restored_theme))

                        # b. The live preview's <img> resolved src is back
                        #    to the ORIGINALLY-selected theme's own — the
                        #    clause that proves
                        #    window.SkyPaneLivePreview.refresh() actually
                        #    ran, since form.reset() fires no change event
                        #    and the preview cannot repaint on its own.
                        #    Waited for on the deferred tick, never read
                        #    synchronously right after the click.
                        try:
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected; }",
                                arg={
                                    "sel": THEME_PREVIEW_SEL, "expected": original_preview_src},
                                timeout=3000)
                        except Exception:
                            return False, (
                                "expected the live preview's src to be back to the "
                                "originally-selected theme's own %r after Annuler (proving "
                                "window.SkyPaneLivePreview.refresh() actually ran), it still "
                                "reads %r" % (original_preview_src, preview_src()))

                        # c. The quiet-hours dial's decoded arc AND its
                        #    handles' aria-valuenow are back to the
                        #    PRE-EDIT window — 28-08's own explicit
                        #    deferred repaint of value-controls.js's
                        #    repaintAll(), proven by the DOM STATE it
                        #    produces, never by asserting the function was
                        #    called.
                        try:
                            page.wait_for_function(
                                "args => {"
                                " var s = document.querySelector(args.sSel);"
                                " var e = document.querySelector(args.eSel);"
                                " return !!s && !!e"
                                "   && s.getAttribute('aria-valuenow') === String(args.s)"
                                "   && e.getAttribute('aria-valuenow') === String(args.e); }",
                                arg={
                                    "sSel": _handle_sel("quiet_hours_start"),
                                    "eSel": _handle_sel("quiet_hours_end"),
                                    "s": original_handles[0], "e": original_handles[1]},
                                timeout=3000)
                        except Exception:
                            return False, (
                                "expected the quiet-hours handles' aria-valuenow to be back to "
                                "%r after Annuler (28-08's deferred repaint of "
                                "value-controls.js's repaintAll()), still read %r"
                                % (original_handles, handle_values()))
                        restored_arc = _quiet_arc_minutes(
                            page, "after Annuler, once the deferred tick has run")
                        if restored_arc != original_arc:
                            return False, (
                                "expected the quiet-hours dial's decoded arc to be back to %r "
                                "after Annuler, got %r" % (original_arc, restored_arc))

                        # d. The bar is hidden — asserted above via
                        #    _wait_for_bar_hidden(), the SYNCHRONOUS half
                        #    of the reset handler.
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a real Annuler click restores every surface, read off the RESULTING DOM: "
                    "the theme chip's checked state is back to the original, the live preview "
                    "<img>'s resolved src is back to the ORIGINALLY-selected theme's own (never "
                    "the discarded one) — proving window.SkyPaneLivePreview.refresh() actually "
                    "ran, since form.reset() fires no change event — and the quiet-hours dial's "
                    "decoded arc and its handles' aria-valuenow are back to the pre-edit window, "
                    "proving 28-08's own explicit deferred repaint of value-controls.js's "
                    "repaintAll() landed; both edits are confirmed to have actually MOVED both "
                    "surfaces before Cancel is ever clicked, and every post-Cancel read waits "
                    "for 28-08's setTimeout(fn, 0) deferred tick rather than reading "
                    "synchronously after the click; asserting that refresh()/repaintAll() was "
                    "CALLED is explicitly not acceptable and this check never does — the "
                    "dial-repaints-for-free claim CONTEXT.md made is false by specification "
                    "(already refuted in writing by 28-08) and this check does not re-litigate "
                    "it (CFG-77, 28-11-PLAN.md Task 2; re-pointed to .palette-chip by "
                    "30-08-PLAN.md Task 2, CFG-85)",
                    _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom)

                # 30-03-PLAN.md Task 3 (CFG-85): the check that used to
                # live here — _the_carousel_meets_its_floors_at_360px_
                # in_both_themes — measured the strip/pager control's
                # touch targets, geometry, overflow and paint floors.
                # LEDGERED to 30-08 (replacement:
                # _the_palette_meets_its_floors_at_360px_in_both_themes)
                # — the replacement measures the four controls in
                # 30-UI-SPEC.md's Touch Targets table by real
                # hit-testing in their own containers, the same
                # discipline this check used. See _ASPECT_REPIN_LEDGER
                # below. This is also the shared selector block's LAST
                # consumer of THEME_STRIP_SEL/THEME_PAGERS_SEL/
                # THEME_DETAILS_SEL/_STRIP_PROBE/_SETTLE_CAROUSEL —
                # deleted below, together with it.

                # ==========================================================
                # 28-04-PLAN.md Task 2 (CFG-72): THE real proof. 27-06's own
                # markup-level inventory (test_config_page.py's structural
                # check) is explicitly insufficient — that is CFG-72's whole
                # lesson, and it is exactly how this defect shipped in the
                # first place: 27-06 counted class names and never once
                # rendered Display and Device side by side to read what the
                # browser actually painted. This check does that: ONE probe
                # loads both settings pages in one session, reads
                # getComputedStyle on every settings-card title, and asserts
                # the two pages' sets are equal.
                # ==========================================================

                _SETTINGS_CARD_TITLE_SELECTOR = (
                    ".theme-status > h2.text-heading, .page-section > h2.text-heading")

                def _settings_card_title_probe(page):
                    """Every settings-card title on the CURRENTLY LOADED
                    settings page, addressed by STRUCTURAL POSITION — the
                    `<h2>` that is a direct child of a `.theme-status`/
                    `.page-section` settings-card wrapper — never by class
                    name. Addressing by class name is the exact move that
                    let 27-06 miss this defect (its own inventory grouped
                    by `.text-heading`, which every h2 on this page
                    carries, card title and supersection intro alike).

                    A supersection's own intro heading
                    (`.section-intro > h2`) is EXCLUDED, structurally
                    rather than by an explicit `:not()`: it lives under
                    `.section-intro`, never directly under
                    `.theme-status`/`.page-section`, so the selector above
                    never reaches it. That exclusion is deliberate — a
                    supersection intro is a different, generically-worded
                    role (companion/test_config_page.py's own title-form
                    inventory, 27-06-PLAN.md Task 1, and SKILL.md's
                    three-rung heading ladder both document why) — not an
                    oversight this check should "fix" into asserting the
                    ladder away.
                    """
                    return page.evaluate(
                        "sel => Array.from(document.querySelectorAll(sel)).map(h => {"
                        "  var s = getComputedStyle(h);"
                        "  return {text: h.textContent, fontSize: s.fontSize,"
                        "          fontWeight: s.fontWeight, fontFamily: s.fontFamily};"
                        "})", _SETTINGS_CARD_TITLE_SELECTOR)

                def _a_settings_card_title_renders_identically_on_both_settings_pages():
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()

                        # Every (page, theme) combination this app can
                        # paint a settings-card title in, all folded into
                        # ONE combined set below — never compared pairwise,
                        # so a third, page-local variant cannot hide.
                        entries = []
                        by_page = {"/display": [], "/device": []}
                        for theme in UI_THEMES_EXPLICIT:
                            for route in ("/display", "/device"):
                                page.goto(base_url + route)
                                _set_ui_theme(page, theme)
                                for title in _settings_card_title_probe(page):
                                    triple = (
                                        title["fontSize"], title["fontWeight"],
                                        title["fontFamily"])
                                    entry = {
                                        "page": route, "theme": theme,
                                        "text": title["text"], "triple": triple}
                                    entries.append(entry)
                                    by_page[route].append(entry)

                        # Clause (a): BOTH sides non-empty, naming the
                        # empty one — a comparator with an empty side
                        # passes vacuously, which is how a grep-level
                        # check misses a rendering defect.
                        for route, side in by_page.items():
                            if not side:
                                return False, (
                                    "expected at least one settings-card title on %s, got "
                                    "NONE — a comparator with an empty side would pass "
                                    "vacuously" % route)

                        # Device must contribute exactly the four NAMED
                        # cards — a probe that silently missed the Poll
                        # card (which reaches the page by a different
                        # route from the other three, outside `builders`
                        # entirely, through a `.page-section` wrapper
                        # rather than `.theme-status` like its siblings)
                        # would pass this check while leaving CFG-72
                        # unmet on a card the developer can see — the
                        # shape of miss 27-06 made. Two properties, NOT
                        # an exact-four-count: (i) every title found is
                        # one of the four canonical names (no unrelated
                        # heading — e.g. a supersection intro — leaked
                        # in), and (ii) the Poll card's OWN title is
                        # specifically among them, proving the probe's
                        # reach extends past the three `.theme-status`
                        # cards to the one `.page-section` card too.
                        # Deliberately NOT "exactly four": M-C
                        # (28-04-PLAN.md Task 2) removes one Device card
                        # from `builders` on purpose and this check must
                        # still PASS on the genuinely smaller set that
                        # produces — proof the comparator is not
                        # secretly COUNTING rather than comparing.
                        allowed_device_texts = {
                            config_page.LED_SECTION_HEADING,
                            config_page.WAKE_INTERVAL_SECTION_HEADING,
                            config_page.NOTIFICATIONS_SECTION_HEADING,
                            config_page.POLL_SECTION_HEADING}
                        device_texts = {e["text"] for e in by_page["/device"]}
                        unexpected = device_texts - allowed_device_texts
                        if unexpected:
                            return False, (
                                "expected every Device settings-card title to be one of %r, "
                                "found unexpected title(s) %r — a probe addressing titles by "
                                "class name rather than structural position would pick up "
                                "supersection intro headings too, which is exactly the "
                                "27-06-shaped mistake this check exists to avoid"
                                % (sorted(allowed_device_texts), sorted(unexpected)))
                        if config_page.POLL_SECTION_HEADING not in device_texts:
                            return False, (
                                "expected the Poll card's own title (%r) among Device's "
                                "settings-card titles — it reaches the page through a "
                                ".page-section wrapper, not .theme-status like the other "
                                "three, and a probe that silently misses it would pass this "
                                "check while leaving CFG-72 unmet on a card the developer "
                                "can see" % config_page.POLL_SECTION_HEADING)

                        # Clause (b): the combined set's own cardinality is
                        # 1 — one typographic form for a settings-card
                        # title, CFG-72's literal wording.
                        triples = sorted({e["triple"] for e in entries})
                        if len(triples) != 1:
                            majority = collections.Counter(
                                e["triple"] for e in entries).most_common(1)[0][0]
                            offender = next(
                                e for e in entries if e["triple"] != majority)
                            # Clause (c): the message names the offending
                            # page, the offending title's text, and BOTH
                            # triples — "titles differ" is not diagnostic.
                            return False, (
                                "expected exactly one (font-size, font-weight, font-family) "
                                "triple across every settings-card title on both settings "
                                "pages, got %d distinct triples — %r on %s (theme=%s) "
                                "renders %r, while the rest render %r"
                                % (len(triples), offender["text"], offender["page"],
                                   offender["theme"], offender["triple"], majority))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "THE real proof, not a grep: ONE probe renders BOTH settings pages "
                    "(Display and Device) in one session, addresses every settings-card title "
                    "by STRUCTURAL POSITION rather than by class name, reads its "
                    "getComputedStyle font-size/font-weight/font-family, and asserts the "
                    "combined set across both pages has cardinality 1 — CFG-72's literal "
                    "wording. Fails naming the empty side if either page contributes zero "
                    "titles; every Device title must be one of the four named cards "
                    "(Diagnostic LED, Wake interval, Notifications, Manual refresh) and the "
                    "Poll card's own title specifically must be among them — proving the "
                    "probe's reach extends to the one .page-section card, not just the three "
                    ".theme-status ones — while a genuinely SMALLER set (one Device card "
                    "removed from `builders`) still passes, proving the comparator is not "
                    "secretly counting; the failure message names the offending page, the "
                    "offending title's text and BOTH triples. Supersection intro headings "
                    "(.section-intro > h2) are excluded structurally, deliberately — a "
                    "different, generically-worded tier (27-06-PLAN.md Task 1, SKILL.md's "
                    "three-rung heading ladder), not an inconsistency this check should assert "
                    "away. Both themes exercised via _set_ui_theme(), at the 360px floor "
                    "(CFG-72, 28-04-PLAN.md Task 2)",
                    _a_settings_card_title_renders_identically_on_both_settings_pages)

                # --- 28-09-PLAN.md Task 1 (CFG-78): the single-affordance
                # audit. "Exactly one save affordance" has been true BY
                # CONSTRUCTION since 28-08 relocated the native submit into
                # the bar and 28-08 Task 2 deleted the `.js`-hide rule — but
                # "by construction" is exactly what 27-06 said about the
                # title form, and it was wrong (CFG-65's own investigation).
                # This check resolves every submit-shaped control's OWN
                # `.form` property in a live browser — never a hand-
                # maintained allow-list of expected buttons, never a count
                # of `<button` occurrences in the HTML string — and
                # requires exactly one whose form id is
                # config_page.SETTINGS_FORM_ID.
                #
                # "Submit-shaped" is `input[type="submit"]`,
                # `button[type="submit"]`, AND a bare `<button>` with no
                # `type` attribute — the HTML default IS submit, and a
                # check that only looked at explicit `type="submit"` would
                # miss the exact regression class it exists to catch (a
                # button added without a type, inside the form, silently
                # becoming a second save affordance).
                #
                # THE ONE DELIBERATE EXCLUSION: the bar's own Cancel is a
                # native `<button type="reset" form="settings-form">`
                # (28-08-PLAN.md Task 1). It IS form-ASSOCIATED with the
                # settings form — exactly what this audit hunts for — but
                # it is not submit-SHAPED (an explicit `type="reset"`
                # excludes it from every branch of the selector below) and
                # it saves nothing. Recorded here because "a second control
                # inside the bar that points at the settings form" looks
                # exactly like the regression this audit exists to catch,
                # and the next reader deserves to know it was considered,
                # not missed.
                def _submit_shaped_controls(page):
                    return page.evaluate(
                        "() => {"
                        " var sel = 'input[type=\"submit\"], button[type=\"submit\"], "
                        "button:not([type])';"
                        " var els = Array.prototype.slice.call(document.querySelectorAll(sel));"
                        " return els.map(function (el) {"
                        "   var text = (el.textContent || el.value || '').trim().slice(0, 60);"
                        "   return {"
                        "     tag: el.tagName.toLowerCase(),"
                        "     type: el.getAttribute('type') || '(default submit)',"
                        "     formId: el.form ? el.form.id : null,"
                        "     text: text,"
                        "     fallback: el.hasAttribute('%s'),"
                        "     inBar: !!el.closest('[data-dirty-bar]')"
                        "   };"
                        " });"
                        "}" % config_page.STATIC_SAVE_FALLBACK_ATTR)

                def _exactly_one_submit_shaped_control_resolves_to_the_settings_form():
                    base_url = harness.base_url()
                    for scope_route in ("/display", "/device"):
                        for lang in ("en", "fr"):
                            context = browser.new_context()
                            try:
                                page = context.new_page()
                                _login(page, base_url)
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + scope_route)

                                controls = _submit_shaped_controls(page)
                                settings_controls = [
                                    c for c in controls
                                    if c["formId"] == config_page.SETTINGS_FORM_ID]

                                if len(controls) < 2:
                                    return False, (
                                        "%s lang=%s: expected MORE than one submit-shaped "
                                        "control on the page (the bar's own Save plus at "
                                        "least one other form's own submit control), found "
                                        "only %r — with only one candidate ever considered "
                                        "the exactly-one assertion below would be vacuous"
                                        % (scope_route, lang, controls))

                                if len(settings_controls) != 1:
                                    offenders = "; ".join(
                                        "%s[type=%s] form=%r text=%r"
                                        % (c["tag"], c["type"], c["formId"], c["text"])
                                        for c in controls)
                                    return False, (
                                        "%s lang=%s: expected exactly ONE submit-shaped "
                                        "control whose own .form.id resolves to %r, got %d "
                                        "— every collected submit-shaped control on this "
                                        "page: %s"
                                        % (scope_route, lang, config_page.SETTINGS_FORM_ID,
                                           len(settings_controls), offenders))

                                the_one = settings_controls[0]
                                if not the_one["fallback"]:
                                    return False, (
                                        "%s lang=%s: the one settings-form submit control "
                                        "does not carry %s — %r"
                                        % (scope_route, lang,
                                           config_page.STATIC_SAVE_FALLBACK_ATTR, the_one))
                                if not the_one["inBar"]:
                                    return False, (
                                        "%s lang=%s: the one settings-form submit control "
                                        "is not a descendant of [data-dirty-bar] — %r"
                                        % (scope_route, lang, the_one))

                                # The complement — the relationship half,
                                # not merely the endpoint: every OTHER
                                # submit-shaped control this scope renders
                                # (whichever of calendar/rules/
                                # notifications-test/quick-LED/quick-switch
                                # actually appear on THIS page — Airlines'
                                # own "Enregistrer le nom" form is excluded
                                # by construction too, trivially, since
                                # this check never navigates to that page)
                                # resolves to a form id that is NOT the
                                # settings form. Already implied by the
                                # exactly-one assertion above, but named
                                # per-control here so a regression that
                                # somehow gave TWO controls the settings-
                                # form id would still be caught with each
                                # offender's own identity in the message —
                                # the developer's own confirmed scope
                                # boundary ("laisser ces deux-la tels
                                # quels") expressed as a contract, not a
                                # comment.
                                bad = [
                                    c for c in controls
                                    if c is not the_one
                                    and c["formId"] == config_page.SETTINGS_FORM_ID]
                                if bad:
                                    return False, (
                                        "%s lang=%s: expected every OTHER submit-shaped "
                                        "control to resolve to a NON-settings-form id, "
                                        "found a second one pointed at settings-form: %r"
                                        % (scope_route, lang, bad))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "exactly ONE submit-shaped control on the whole settings page resolves "
                    "its own .form.id to config_page.SETTINGS_FORM_ID, on both /display and "
                    "/device, in both site languages — resolved via the browser's OWN .form "
                    "property, never a count of <button occurrences in the HTML string and "
                    "never a hand-maintained allow-list; covers input[type=submit], "
                    "button[type=submit] AND a bare <button> with no type attribute (the "
                    "HTML default IS submit); the bar's native type=\"reset\" Cancel is "
                    "deliberately excluded (form-associated but not submit-shaped, and it "
                    "saves nothing); the one settings-form control must carry "
                    "data-static-save-fallback and be a descendant of [data-dirty-bar]; the "
                    "failure message NAMES every collected control as a tagName/type/form-"
                    "id/text tuple so a regression says WHICH control drifted; and the "
                    "complement is asserted too — calendar/rules/notifications-test/quick-"
                    "LED/quick-switch controls, whichever this scope renders, each resolve "
                    "to a NON-settings-form id (CFG-78, 28-09-PLAN.md Task 1)",
                    _exactly_one_submit_shaped_control_resolves_to_the_settings_form)

                # --- 28-09-PLAN.md Task 1 (CFG-74(c)/CFG-78): the runway
                # radios' cross-tree form="settings-form" regression check
                # — the developer's ORIGINAL, narrower report ("Quand je
                # fais un changement de parametre (comme la piste) je ne
                # vois pas le bouton enregistrer apparaitre") that carries
                # forward from the superseded CFG-74 with its value intact.
                # The runway radios live OUTSIDE <form id="settings-form">
                # (runway_fieldset()'s own docstring) and reach it only
                # through a form="settings-form" attribute on each radio —
                # a form element never receives a `change` event from a
                # control that is merely form=-associated with it, which is
                # exactly the B1 defect dirty-state.js's document-level
                # delegation exists to handle. This proves the whole path
                # end to end, against the restored bar's real POST rather
                # than the retired fetch.
                def _the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end():
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            # 1. Fresh load: script has run, nothing dirty.
                            _wait_for_bar_hidden(page)

                            runway_sel = 'input[name="tracked_runway"]'
                            current_runway = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            target_runway = next(
                                r for r in device_config.RUNWAY_IDS
                                if r != current_runway)

                            # Built from the bar's OWN data-dirty-*
                            # attribute plus the runway wrapper's own
                            # [data-dirty-section] label — never a
                            # hardcoded English/French literal (the
                            # suite's existing D-06 idiom, reused verbatim
                            # from 28-11's section-naming check).
                            runway_label = page.eval_on_selector(
                                runway_sel,
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            changed_suffix = page.eval_on_selector(
                                "[data-dirty-bar]",
                                "el => el.getAttribute('data-dirty-changed-suffix')")
                            expected = runway_label + changed_suffix

                            # 2. Select a runway radio whose value differs
                            #    from disk, via the same real
                            #    element.click() every other visually-
                            #    hidden selectable-card radio on this page
                            #    uses (_click_control()'s own docstring
                            #    warns a coordinate click can silently
                            #    land elsewhere).
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))

                            # 3. The bar becomes visible AND names EXACTLY
                            #    Runway — proving the cross-tree form=
                            #    association actually reached
                            #    dirtySectionLabels()'s own
                            #    [data-dirty-section] walk, not merely
                            #    that "something" became dirty. Asserting
                            #    visibility alone would not prove this.
                            _wait_for_bar(page)
                            actual = _bar_text(page)
                            if actual != expected:
                                return False, (
                                    "lang=%s: expected [data-dirty-count] to read %r after "
                                    "selecting a cross-tree form=-associated runway radio, "
                                    "got %r — the section-naming walk must resolve this "
                                    "control's own [data-dirty-section] ancestor even though "
                                    "the radio is not a literal descendant of <form "
                                    "id=\"settings-form\">"
                                    % (lang, expected, actual))

                            # 4. Click Enregistrer, wait for the REAL
                            #    navigation.
                            _save_via_bar(page)

                            # 5. Re-read tracked_runway OFF DISK.
                            saved = device_config.load_device_config(
                                harness.tmpdir)["tracked_runway"]
                            if saved != target_runway:
                                return False, (
                                    "lang=%s: expected tracked_runway on disk to be %r "
                                    "after a real Enregistrer navigation through the "
                                    "runway's own cross-tree form= path, got %r"
                                    % (lang, target_runway, saved))

                            # Reload: the round trip, not just the write.
                            page.goto(base_url + "/display")
                            checked = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            if checked != target_runway:
                                return False, (
                                    "lang=%s: expected the reloaded page's checked runway "
                                    "radio to be %r, got %r"
                                    % (lang, target_runway, checked))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the runway radios' cross-tree form=\"settings-form\" wiring drives the "
                    "SAME bar-appears -> Enregistrer -> persisted-to-disk path every "
                    "natively-nested control does — closing the path CFG-74(c) named before "
                    "it was superseded, now against the real POST instead of the retired "
                    "fetch: selecting a runway radio (rendered OUTSIDE the settings form) "
                    "reveals the bar naming exactly its own Runway/Piste label, a real "
                    "Enregistrer navigation writes tracked_runway to disk, and a reload "
                    "shows the radio reflecting the saved value — both site languages "
                    "(CFG-74(c)/CFG-78, 28-09-PLAN.md Task 1)",
                    _the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end)

                # ==========================================================
                # 25-07-PLAN.md Task 3 (CFG-51/D19): THE ARTWORK DROP ZONE.
                #
                # ITS OWN ISOLATED Harness(), for the reason 25-02's own
                # helper docstring gives about T-25-02-A: these checks
                # UPLOAD an illustration and add a manual resolution, and
                # the shared fixture is the subject of forty other checks
                # in this file. Every one of them below also deletes the
                # override file it wrote, so the block leaves its own
                # fixture as it found it too.
                #
                # THE SUBJECT IS A MANUAL ENTRY WITH NO ARTWORK YET —
                # Step B — because that is the one state where BOTH copies
                # of the upload form render at once: the in-page no-JS
                # fallback panel (a real action, the scriptless floor) and
                # the dialog's copy (the placeholder action panel-lookup.js
                # rewrites). The two are the same builder's output.
                # ==========================================================
                artwork_harness = Harness()
                seed_state_dir(artwork_harness.tmpdir)
                ARTWORK_PREFIX = "NEW"
                ARTWORK_NAME = "Totally Novel Airline"
                if manual_resolutions.add_entry(
                        artwork_harness.tmpdir, ARTWORK_PREFIX,
                        ARTWORK_NAME) != manual_resolutions.ADD_OK:
                    raise AssertionError("could not seed the Step-B manual entry")
                ARTWORK_KEY = manual_resolutions.illustration_key_for_name(ARTWORK_NAME)
                ARTWORK_ROUTE = "/airlines?resolve=" + ARTWORK_PREFIX
                ARTWORK_SERVE = "/illustration/%s.png" % ARTWORK_KEY
                FALLBACK_ZONE = "[data-resolve-fallback] [data-upload-drop]"
                # 29-01-PLAN.md (CFG-81): the dialog's Replace form now
                # renders UNCONDITIONALLY (edit_mode is gone), so the
                # shared #panel-lookup-dialog carries BOTH upload-drop
                # zones at once from here on — this one (the needs-
                # artwork resolve zone, id_suffix="-dialog") and
                # REPLACE_INPUT_ID's own ("airline-replace-input"),
                # panel-lookup.js's `mode` gate hides whichever does not
                # apply, but both are always present in the DOM, so a
                # bare "[data-upload-drop]" now matches two elements —
                # this check's own subject is the needs-artwork one,
                # disambiguated by the same UPLOAD_DROP_INPUT_ATTR value
                # panel-lookup.js itself reads to decide which to hide.
                DIALOG_ZONE = "#panel-lookup-dialog [%s='%s']" % (
                    airlines_page.UPLOAD_DROP_INPUT_ATTR,
                    airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog",
                )

                art_dir = tempfile.mkdtemp(prefix="skypane-browser-ux-artwork-")
                artwork_harness.start()
                try:
                    from PIL import Image as _ArtImage

                    # A real, plausible illustration: a landscape PNG with
                    # transparent padding, the shape every vendored file
                    # has and the shape illustration_normalize.py crops.
                    art_path = os.path.join(art_dir, "artwork.png")
                    art = _ArtImage.new("RGBA", (1200, 300), (0, 0, 0, 0))
                    for ax in range(200, 1000):
                        for ay in range(80, 220):
                            art.putpixel((ax, ay), (200, 40, 40, 255))
                    art.save(art_path)

                    # Not an image at all, and over the server's own cap.
                    # The oversized one is INCOMPRESSIBLE NOISE on purpose:
                    # a large flat PNG compresses to nothing and would sail
                    # under a cap this check exists to reach.
                    not_png_path = os.path.join(art_dir, "not-an-image.txt")
                    with open(not_png_path, "wb") as fh:
                        fh.write(b"this is not a png\n")
                    oversized_path = os.path.join(art_dir, "oversized.png")
                    _ArtImage.frombytes(
                        "RGBA", (1200, 1200), os.urandom(1200 * 1200 * 4)
                    ).save(oversized_path)
                    OVERSIZED_BYTES = os.path.getsize(oversized_path)
                    ART_BYTES = os.path.getsize(art_path)

                    def _override_path():
                        return illustrations.override_path_for_key(
                            ARTWORK_KEY, artwork_harness.tmpdir)

                    def _stored_artwork():
                        """The stored override's BYTES, or None. The
                        verdict for every upload below, read off the real
                        state directory rather than off the page — a POST
                        this app rejected redirects to a page that looks
                        exactly like success."""
                        path = _override_path()
                        if not path or not os.path.isfile(path):
                            return None
                        with open(path, "rb") as fh:
                            return fh.read()

                    def _clear_stored_artwork():
                        path = _override_path()
                        if path and os.path.isfile(path):
                            os.unlink(path)

                    def _artwork_uploads_and_is_served_with_scripts_blocked():
                        try:
                            # BOTH DIRECTIONS OF THE GATE FIRST, because
                            # a successful upload moves this entry out of
                            # Step B and the fallback panel stops
                            # rendering the zone at all.
                            #
                            # `prepare` un-hides the in-page fallback on
                            # BOTH pages, and that is not a poke to make a
                            # check pass: a ?resolve= deep link auto-opens
                            # the dialog and panel-lookup.js hides the
                            # in-page copy as a duplicate sitting behind
                            # the backdrop (Phase 18 audit). Without this
                            # the two directions would measure two
                            # different elements. It is applied identically
                            # to both pages, which is the helper's own
                            # stated requirement.
                            def unhide_fallback(page):
                                page.evaluate(
                                    "() => { const f = document.querySelector("
                                    "'[data-resolve-fallback]'); if (f) f.hidden = false; }")
                            gate = _assert_js_gate(
                                browser.new_context, artwork_harness.base_url(), ARTWORK_ROUTE,
                                FALLBACK_ZONE, viewport=VIEWPORT_MIN_SUPPORTED,
                                prepare=unhide_fallback)
                            if gate["blocked"]["candidates"] != 0:
                                return False, (
                                    "the drop zone holds %d focusable descendant(s) — it is a "
                                    "hint, a preview and a message, and nothing in it should be "
                                    "reachable at all" % gate["blocked"]["candidates"])

                            before = _stored_artwork()
                            if before is not None:
                                return False, (
                                    "the fixture already has stored artwork for %r, so an upload "
                                    "could not be told from the state before it" % ARTWORK_KEY)
                            seen = _upload_without_js(
                                browser.new_context, artwork_harness.base_url(), ARTWORK_ROUTE,
                                "#%s" % airlines_page.MANUAL_UPLOAD_INPUT_ID,
                                "#%s button[type=\"submit\"]" % airlines_page.MANUAL_UPLOAD_FORM_ID,
                                art_path, _stored_artwork, ARTWORK_SERVE,
                                viewport=VIEWPORT_MIN_SUPPORTED)
                            # "Stored and served" is two claims. The
                            # second one is what a visitor sees, so it is
                            # measured as an IMAGE rather than as 200 plus
                            # a byte count: the route normalises on the
                            # way out, and the size it normalises to is
                            # illustration_normalize.py's own frame.
                            served = _ArtImage.open(io.BytesIO(seen["served"]))
                            if served.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                                return False, (
                                    "%s serves a %r image after a scripts-blocked upload, but "
                                    "companion/illustration_normalize.py's frame is %r — the "
                                    "route is not the normaliser's output"
                                    % (ARTWORK_SERVE, served.size,
                                       illustration_normalize.ILLUSTRATION_TARGET_SIZE))
                            _ = (seen["stored_len"], gate)
                            return True, ""
                        finally:
                            _clear_stored_artwork()
                    check(
                        "with scripts blocked at 360px, an artwork file chosen through the native "
                        "<input type=\"file\"> and submitted through the fallback panel's own form "
                        "is STORED (read back off the real state directory, never off the page — a "
                        "rejected upload redirects to a page that looks like success) and SERVED "
                        "back by the illustration route as an image at "
                        "illustration_normalize.ILLUSTRATION_TARGET_SIZE; and the drop zone beside "
                        "it measures zero height and holds zero focusable descendants with scripts "
                        "blocked while occupying a real box with them on (CFG-51/D-09, "
                        "25-07-PLAN.md Task 3)",
                        _artwork_uploads_and_is_served_with_scripts_blocked)

                    def _dropped_and_picked_files_are_stored_identically():
                        context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                        try:
                            if _stored_artwork() is not None:
                                return False, (
                                    "stored artwork for %r was already on disk when this check "
                                    "started — the previous check did not restore the fixture, "
                                    "and this entry would render as `art` rather than "
                                    "`needs-artwork`, hiding the upload zone entirely"
                                    % (ARTWORK_KEY,))
                            page = context.new_page()
                            _login(page, artwork_harness.base_url())
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)
                            submit = "#%s button[type=\"submit\"]" % (
                                airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog")

                            def upload_current_selection():
                                """Submit, then read the stored bytes and
                                put the fixture BACK into Step B.

                                The reset is not tidiness, it is what
                                makes the next upload possible at all: a
                                successful upload moves this entry from
                                `needs-artwork` to `art`, and
                                panel-lookup.js hides the dialog's upload
                                zone in every mode but the first. It is
                                also what makes the byte comparison mean
                                anything — with the previous file left in
                                place, a drop that never reached the
                                server would leave it there and compare
                                equal to itself.
                                """
                                with page.expect_navigation():
                                    page.click(submit)
                                written = _stored_artwork()
                                _clear_stored_artwork()
                                page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                                _await_upload_zone(page, DIALOG_ZONE)
                                return written

                            # THE FIXTURES, PROVED NON-VACUOUS AGAINST THE
                            # APP'S OWN NUMBER before anything is dropped.
                            # An "oversized" file that is not actually
                            # over the cap tests nothing while reading
                            # exactly like a passing check, and the cap is
                            # companion/app.py's, rendered into the page,
                            # never retyped here.
                            cap = int(page.locator(DIALOG_ZONE).get_attribute(
                                "data-upload-drop-max-bytes"))
                            if OVERSIZED_BYTES <= cap:
                                return False, (
                                    "the oversized fixture is %d bytes and the app's own cap is "
                                    "%d — the oversized case would be measuring nothing"
                                    % (OVERSIZED_BYTES, cap))
                            if ART_BYTES >= cap:
                                return False, (
                                    "the valid-artwork fixture is %d bytes, at or over the app's "
                                    "own %d cap — every acceptance below would be measuring the "
                                    "wrong thing" % (ART_BYTES, cap))

                            # --- THE FLOOR, MEASURED BEFORE THE CEILING ---
                            # A drop zone that silently accepts what the
                            # picker would reject is a defect, so every
                            # refusal is measured against the INPUT, not
                            # against a message: the question is whether
                            # anything was assigned.
                            floor = {}
                            _drop_files(page, DIALOG_ZONE, [])
                            floor["zero-files"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [not_png_path])
                            floor["wrong-type"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [art_path, art_path])
                            floor["several"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [oversized_path])
                            floor["oversized"] = _upload_zone_state(page, DIALOG_ZONE)
                            for label, state in floor.items():
                                if state["files"] != 0:
                                    return False, (
                                        "a %s drop assigned %d file(s) to the form's input — the "
                                        "refusal has to happen BEFORE the assignment or it "
                                        "refuses nothing (%r)" % (label, state["files"], state))
                                if not state["message"]:
                                    return False, (
                                        "a %s drop was refused silently — a drop target that "
                                        "declines without saying so is indistinguishable from one "
                                        "that is broken (%r)" % (label, state))
                                if not state["imageHidden"]:
                                    return False, (
                                        "a %s drop still rendered a preview (%r)" % (label, state))
                                # AND THE SRC IS GONE, not merely hidden.
                                # A hidden <img> still holding a data:
                                # URL keeps the whole decoded file alive
                                # for the life of the document — the same
                                # leak an unrevoked object URL would have
                                # been, and invisible to a check that only
                                # asks whether the preview is showing.
                                if state["imageScheme"] != "":
                                    return False, (
                                        "after a %s drop the preview <img> still holds a %r src — "
                                        "hidden is not released, and the whole decoded file stays "
                                        "in the document (%r)"
                                        % (label, state["imageScheme"], state))
                            if floor["oversized"]["message"] == floor["wrong-type"]["message"]:
                                return False, (
                                    "the oversized drop and the wrong-type drop say the same "
                                    "thing (%r) — the visitor cannot tell which rule they hit"
                                    % (floor["oversized"]["message"],))
                            if floor["several"]["message"] == floor["wrong-type"]["message"]:
                                return False, (
                                    "a several-files drop and a wrong-type drop say the same "
                                    "thing (%r)" % (floor["several"]["message"],))

                            # REPLACING A PREVIEW AND THEN BEING REFUSED,
                            # which is the only sequence in which "the
                            # preview is released" can be measured at
                            # all: every drop above was refused with no
                            # preview on screen to release, so an <img>
                            # that never let go of its data: URL would
                            # have passed all four of them.
                            _drop_files(page, DIALOG_ZONE, [art_path])
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            shown = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [not_png_path])
                            after = _upload_zone_state(page, DIALOG_ZONE)
                            if after["imageScheme"] != "":
                                return False, (
                                    "a refused drop left the previous preview's %r src on the "
                                    "<img> (%r) — the decoded file stays in the document for as "
                                    "long as the page does"
                                    % (after["imageScheme"], after))
                            if after["files"] != 1 or after["size"] != shown["size"]:
                                return False, (
                                    "a refused drop discarded the file the visitor had already "
                                    "chosen (%r was holding %r, now %r) — declining to perform "
                                    "its own act is the script doing nothing; removing somebody "
                                    "else's choice is the script doing harm"
                                    % (shown["name"], shown["size"], after))
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)

                            # --- THE EQUIVALENCE, WHICH IS THE WHOLE POINT ---
                            # The same source file, uploaded twice: once
                            # picked, once dropped. The stored result must
                            # be byte-identical, because the ONLY thing
                            # between the file and the route is a
                            # DataTransfer assignment — no crop, no
                            # resize, no re-encode.
                            _clear_stored_artwork()
                            page.set_input_files(
                                "#%s" % (airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog"),
                                art_path)
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            picked_state = _upload_zone_state(page, DIALOG_ZONE)
                            picked_bytes = upload_current_selection()
                            if picked_bytes is None:
                                return False, (
                                    "picking the file and submitting stored nothing — before "
                                    "comparing two paths, one of them has to work")
                            if _stored_artwork() is not None:
                                return False, "could not clear the stored artwork between uploads"
                            dragged = _drop_files(page, DIALOG_ZONE, [art_path])
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            dropped_state = _upload_zone_state(page, DIALOG_ZONE)
                            if dropped_state["files"] != 1:
                                return False, (
                                    "a trusted drop of a valid PNG assigned %d file(s) (%r)"
                                    % (dropped_state["files"], dropped_state))
                            dropped_bytes = upload_current_selection()
                            if dropped_bytes is None:
                                return False, (
                                    "dropping the same file and submitting stored NOTHING, while "
                                    "picking it stored %d bytes — the drop path does not reach "
                                    "the server the picked file reaches" % (len(picked_bytes),))
                            if dropped_bytes != picked_bytes:
                                return False, (
                                    "the SAME source file stored %d bytes when picked and %d when "
                                    "dropped — a second transform crept into the drop path, which "
                                    "is exactly the drift no client-side crop was written to "
                                    "avoid" % (len(picked_bytes), len(dropped_bytes)))
                            if picked_state["size"] != dropped_state["size"]:
                                return False, (
                                    "the picked file measured %r bytes in the input and the "
                                    "dropped one %r — the script altered the file on the way in"
                                    % (picked_state["size"], dropped_state["size"]))
                            if dropped_state["imageScheme"] != "data":
                                return False, (
                                    "the preview's src scheme is %r — this app's own "
                                    "Content-Security-Policy is img-src 'self' data:, under which "
                                    "a blob: preview is blocked outright"
                                    % (dropped_state["imageScheme"],))
                            if dropped_state["natural"] != [1200, 300]:
                                return False, (
                                    "the preview decoded to %r, not the source file's own "
                                    "1200x300 — the preview is the file, not a redrawing of it"
                                    % (dropped_state["natural"],))

                            # A SYNTHETIC drop, the one a page script can
                            # construct, must change nothing.
                            _clear_stored_artwork()
                            page.evaluate(
                                "sel => { const z = document.querySelector(sel);"
                                "  const dt = new DataTransfer();"
                                "  const ev = new DragEvent('drop',"
                                "    {bubbles: true, cancelable: true, dataTransfer: dt});"
                                "  z.dispatchEvent(ev); }", DIALOG_ZONE)
                            synthetic = _upload_zone_state(page, DIALOG_ZONE)
                            if synthetic["message"]:
                                return False, (
                                    "a synthetic (isTrusted: false) drop reached the handler and "
                                    "produced %r — the only way into it should be a gesture a "
                                    "person performed" % (synthetic["message"],))

                            # And the drag state was really on, DURING the
                            # drag, and really off after it.
                            if not dragged["active_during_drag"]:
                                return False, (
                                    "the drag-over state never appeared while the browser was in "
                                    "a drag — sampled between dragOver and drop, %r" % (dragged,))
                            if dragged["active_after_drop"]:
                                return False, "the drag-over state survived the drop (%r)" % (dragged,)
                            if dragged["paint_during_drag"] == dragged["paint_at_rest"]:
                                return False, (
                                    "the zone paints identically at rest and mid-drag (%r) — the "
                                    "state is set but invisible, which is the same as not having "
                                    "one" % (dragged["paint_at_rest"],))
                            return True, ""
                        finally:
                            _clear_stored_artwork()
                            context.close()
                    check(
                        "the SAME source file stored byte-identically whether it was PICKED or "
                        "DROPPED (with the stored file deleted between the two uploads, so a drop "
                        "that never reached the server could not pass on the picked file left "
                        "behind), the preview decoding to the source's own 1200x300 through a "
                        "data: URL (a blob: one is blocked by this app's own CSP); and the FLOOR "
                        "measured against the INPUT rather than against a message — zero files, a "
                        "wrong type, several at once and an oversized file each assign nothing, "
                        "each say something, and each say something different, while a synthetic "
                        "drop changes nothing at all and the drag-over state is sampled visible "
                        "BETWEEN dragOver and drop (CFG-51/D19, 25-07-PLAN.md Task 3)",
                        _dropped_and_picked_files_are_stored_identically)

                    def _drop_zone_meets_its_floors_at_360px_in_both_themes():
                        context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                        try:
                            page = context.new_page()
                            _login(page, artwork_harness.base_url())
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)

                            # THE HIT TARGET, MEASURED IN THIS CONTROL'S
                            # OWN CONTAINER rather than inherited from a
                            # class — 25-06's pagers measured 30x45 in
                            # theirs while the same class measured 45x45
                            # elsewhere.
                            hit = _assert_hit_target(
                                page, DIALOG_ZONE, "the artwork drop zone on Airlines at 360px")
                            msg = _assert_no_page_overflow(
                                page, "the artwork drop zone on Airlines",
                                VIEWPORT_MIN_SUPPORTED["width"])
                            if msg:
                                return False, msg

                            # THE RESERVED BOX, before any image exists.
                            # A ratio, not a size: the box is fluid and
                            # the promise is its SHAPE. getBoundingClientRect,
                            # never clientWidth, which rounds to an integer
                            # and can fail a correct drawing.
                            at_rest = _upload_zone_state(page, DIALOG_ZONE)
                            want = (illustration_normalize.ILLUSTRATION_TARGET_WIDTH
                                    / illustration_normalize.ILLUSTRATION_TARGET_HEIGHT)
                            got = at_rest["preview"][0] / at_rest["preview"][1]
                            if abs(got - want) > 0.02:
                                return False, (
                                    "the preview box reserves %.4f:1 (%r) before any image "
                                    "exists, but illustration_normalize.py's frame is %.4f:1 — a "
                                    "box reserved at the wrong shape still makes the card jump"
                                    % (got, at_rest["preview"], want))
                            if not at_rest["imageHidden"]:
                                return False, (
                                    "the preview <img> is showing before a file was chosen (%r)"
                                    % (at_rest,))

                            painted = []
                            for measured in _in_both_themes(page):
                                paint = page.evaluate(
                                    "sel => { const z = document.querySelector(sel);"
                                    "  const n = z.querySelector('.upload-drop__note');"
                                    "  const p = z.querySelector('.upload-drop__preview');"
                                    "  return {note: getComputedStyle(n).color,"
                                    "          frame: getComputedStyle(p).borderTopColor,"
                                    "          surface: getComputedStyle(p).backgroundColor}; }",
                                    DIALOG_ZONE)
                                if paint["note"] == measured["canvas"]:
                                    return False, (
                                        "%s: the drop zone's hint text is the canvas colour (%r) "
                                        "— an invisible instruction is no instruction"
                                        % (measured["theme"], paint["note"]))
                                if paint["frame"] == paint["surface"]:
                                    return False, (
                                        "%s: the preview frame (%r) is its own fill, so the "
                                        "reserved box has no visible edge before an image arrives"
                                        % (measured["theme"], paint["frame"]))
                                painted.append((measured["theme"], paint))
                            if painted[0][1] == painted[1][1]:
                                return False, (
                                    "the drop zone paints identically in both themes (%r) — one "
                                    "of them is not reading the theme's tokens"
                                    % (painted[0][1],))
                            _set_ui_theme(page, "light")
                            _ = hit
                            return True, ""
                        finally:
                            context.close()
                    check(
                        "the artwork drop zone clears the 44px target by real hit-testing in ITS "
                        "OWN container at 360px, the Airlines page does not scroll sideways there, "
                        "the preview box reserves illustration_normalize.py's own aspect ratio "
                        "(by getBoundingClientRect, never clientWidth) BEFORE any image exists "
                        "with the <img> still hidden, and the paint is a FLOOR not a ceiling: the "
                        "hint text is never the canvas colour, the preview frame is never its own "
                        "fill, and the whole zone paints differently in the two themes (CFG-51/"
                        "CFG-52, 25-07-PLAN.md Task 3)",
                        _drop_zone_meets_its_floors_at_360px_in_both_themes)
                finally:
                    artwork_harness.stop()
                    artwork_harness.cleanup()
                    shutil.rmtree(art_dir, ignore_errors=True)

            finally:
                browser.close()
    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("browser-ux: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
