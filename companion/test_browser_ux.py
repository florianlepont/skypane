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

from companion import auth  # noqa: E402
from companion_app_server import LegacyHarness as Harness  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page, config_page)
from server import device_config  # noqa: E402
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
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _await_upload_zone, _bar_text, _click_control,
    _commit_field, _drop_files,
    _handle_sel, _in_both_themes, _login, _no_js_page,
    _persist_without_js, _quiet_arc_minutes, _save_via_bar, _SUBMIT_PROBE,
    _set_ui_theme, _upload_without_js, _upload_zone_state, _wait_for_bar,
    _wait_for_bar_hidden, seed_state_dir,
)

EXPECTED_CHECK_COUNT = 13


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
