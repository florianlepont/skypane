#!/usr/bin/env python3
"""The quiet-hours dial and wake-interval slider scenario group split out
of `companion/test_browser_ux.py` (31-03-PLAN.md, D-04) into its own
standalone harness.

Covers the 25-04/25-05 widget family: D17's quiet-hours dial on the
Display settings page and its wake-interval slider sibling on the
Device settings page. These nine checks were D-04's second mandatory
extraction and RESEARCH.md's rank-2 candidate — the single largest
fully-contiguous block outside the settings mega-cluster, one coherent
widget family, three `_in_both_themes()` loops.

Split out of `companion/test_browser_ux.py` in phase 31 so the suite's
worker pool can run this harness concurrently with the rest of the
browser-level checks, cutting wall time without changing behaviour. Like
its parent, this file drives a real headless Chromium against a real
`companion/app.py` subprocess, and it never constructs or navigates to
any URL outside `Harness.base_url()` — a `127.0.0.1:<ephemeral-port>`
origin this file itself created.

Follows the same conventions as every sibling harness: a `check(name,
fn)` helper with the same result-collecting shape, a module-level
`EXPECTED_CHECK_COUNT`, and a `main()` returning 0 or 1 — so
`scripts/run_all_tests.py` needs zero special-casing for this file.

Two skip gates, both returning exit 0 with a printed `SKIP` line naming
THIS file (not its parent) and the exact remedy — never a failure:
  1. `playwright` itself is not installed (a dev-only dependency, see
     server/requirements-dev.txt's own header comment).
  2. `playwright` is installed but no Chromium binary has been
     downloaded (`python -m playwright install chromium` was never run).

Usage:
    server/.venv/bin/python3 companion/test_browser_ux_quiet_wake.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth  # noqa: E402
from companion.pages import config_page  # noqa: E402
from companion.test_companion_app import Harness  # noqa: E402
from server import device_config  # noqa: E402
# 31-03-PLAN.md Task 1: shared constants and helpers live in
# companion.test_browser_ux_helpers (31-01-PLAN.md Task 3), so this file
# imports them rather than duplicating them. The quiet-dial decoder
# cluster and `_handle_sel` were promoted there by plan 01 precisely so
# this file and the reduced parent can each import one definition
# instead of duplicating it.
from companion.test_browser_ux_helpers import (  # noqa: E402
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED, _QUIET_READOUT_SELECTOR,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _commit_field, _computed_paint,
    _expected_quiet_duration_text, _handle_sel, _hit_area, _in_both_themes,
    _login, _no_js_page, _operate_with_keyboard, _persist_without_js,
    _quiet_arc_minutes, _quiet_caption_minutes, _quiet_caption_shape,
    _quiet_duration_span_text, _save_via_bar, _set_ui_theme, _wait_for_bar,
    seed_state_dir,
)

# 31-03-PLAN.md Task 1: 9 checks — the complete 25-04/25-05 quiet-hours
# dial and wake-interval slider series — moved verbatim out of
# companion/test_browser_ux.py, re-derived by RUNNING this file, never
# by arithmetic.
EXPECTED_CHECK_COUNT = 9


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "SKIP companion/test_browser_ux_quiet_wake.py — playwright not installed "
            "(dev-only dependency; run "
            "`pip install -r server/requirements-dev.txt` to enable this harness)")
        return 0

    try:
        with sync_playwright() as p:
            probe = p.chromium.launch()
            probe.close()
    except Exception as exc:
        print(
            "SKIP companion/test_browser_ux_quiet_wake.py — Chromium launch failed (%r); "
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
                # ----------------------------------------------------------
                # 25-04-PLAN.md Task 4 (CFG-48): D17's quiet-hours dial,
                # measured at 360px, from the keyboard, and with its
                # fallback proven by SAVING rather than by rendering.
                #
                # None of the three checks below asserts that the dial
                # renders. "Rendered" is not "usable" (Phase 22's P0) and
                # "the field shows the value" is not "the value was
                # stored" — this card ECHOES a rejected submission back
                # into its own fields by design (D-07), so a DOM read
                # would pass against a save that stored nothing. The
                # verdicts here are: what reaches DISK with scripts
                # blocked, what a drag and a keystroke do to the native
                # input and to the save bar, and what the browser's own
                # hit test and cascade answer at 360px in both themes.
                # ----------------------------------------------------------

                QUIET_DIAL_SEL = ".quiet-dial"
                QUIET_ARC_SEL = ".quiet-dial__arc"
                QUIET_HANDLES_SEL = ".quiet-dial__handles"
                QUIET_READOUT_SEL = ".quiet-dial__readout"

                def _quiet_hours_on_disk():
                    config = device_config.load_device_config(harness.tmpdir)
                    return (config["quiet_hours_start"], config["quiet_hours_end"])

                # Set both ends through the real UI and save, so every
                # arrangement this file measures is reached the way a
                # visitor reaches it. Returns nothing; raises on failure.
                def _set_window(page, base_url, start, end):
                    # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED from
                    # auto-save onto the restored bar — commits reveal the
                    # bar; only a click on its own Save persists. MEASURED,
                    # not assumed: Playwright's own .fill() dispatches
                    # `input` only (its documented contract), never
                    # `change` — the trigger the bar's own document-level
                    # listener needs — so _commit_field() fires the real
                    # event a blur would, on each field, the same way
                    # value-controls.js's own notify() does for a
                    # drag/keyboard interaction.
                    #
                    # IDEMPOTENT, and now a REAL requirement rather than a
                    # borrowed convenience: under the bar, disk only ever
                    # moves via an explicit Save (never a bare `change`
                    # any more), so a caller's own drag/preset work
                    # in-between two _set_window() calls no longer keeps
                    # disk (and therefore the next fresh load's own
                    # snapshot) drifting on its own — reload here can
                    # genuinely already match the requested (start, end),
                    # and filling both fields with their own current
                    # values fires no DIFFERENCE at all, so the bar never
                    # reveals and _wait_for_bar() below would time out
                    # waiting for one that correctly never comes (the
                    # exact failure mode _set_interval()'s own identical
                    # guard, below, already documents for its own field).
                    page.goto(base_url + "/display")
                    if _quiet_hours_on_disk() == (start, end):
                        return
                    page.fill('input[name="quiet_hours_start"]', start)
                    _commit_field(page, 'input[name="quiet_hours_start"]')
                    page.fill('input[name="quiet_hours_end"]', end)
                    _commit_field(page, 'input[name="quiet_hours_end"]')
                    _wait_for_bar(page)
                    _save_via_bar(page)
                    stored = _quiet_hours_on_disk()
                    if stored != (start, end):
                        raise AssertionError(
                            "setting the window to %r through the UI stored %r"
                            % ((start, end), stored))
                    page.goto(base_url + "/display")

                # Every rule this component adds is a plain paint or a
                # placement, so nothing here transitions today — but the
                # theme switch starts transitions elsewhere on the page,
                # and 25-03 already lost a paint measurement to an
                # interpolation frame read at a guessed instant. This is
                # the browser's OWN "it has finished" signal, never a
                # timer: an element with nothing running returns an empty
                # list and resolves at once.
                _SETTLE_DIAL = (
                    "async () => {"
                    "  const els = [...document.querySelectorAll("
                    "    '.quiet-dial, .quiet-dial *')];"
                    "  await Promise.all(els.flatMap("
                    "    e => e.getAnimations().map("
                    "      a => a.finished.catch(() => {}))));"
                    "  return els.length;"
                    "}")

                def _the_window_still_saves_with_scripts_blocked_through_the_dial():
                    base_url = harness.base_url()
                    before = _quiet_hours_on_disk()

                    def read_start():
                        return _quiet_hours_on_disk()[0]

                    def read_end():
                        return _quiet_hours_on_disk()[1]

                    # BOTH ENDS AND BOTH SHIPPED LANGUAGES. The UI
                    # language is a cookie the first rendered document
                    # already has to honour, and "it saves in English" is
                    # not the D-09 floor.
                    saved = {}
                    for lang in ("en", "fr"):
                        cookies = [{"name": auth.UI_LANG_COOKIE_NAME,
                                    "value": lang, "url": base_url}]
                        saved[(lang, "start")] = _persist_without_js(
                            browser, base_url, "/display", "quiet_hours_start",
                            "21:45", read_start, viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=cookies)
                        saved[(lang, "end")] = _persist_without_js(
                            browser, base_url, "/display", "quiet_hours_end",
                            "06:15", read_end, viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=cookies)
                    after = _quiet_hours_on_disk()
                    if after != before:
                        return False, (
                            "the scripts-blocked saves left the window at %r; it started at "
                            "%r — a harness that changes a real setting is a test that edits "
                            "its neighbours' subject" % (after, before))
                    for key, result in saved.items():
                        if str(result["stored"]) != str(result["set"]):
                            return False, (
                                "%s: %s did not reach disk, it reads %r"
                                % (key, result["field"], result["stored"]))

                    # THE GATE, IN BOTH DIRECTIONS. Asserting only the
                    # blocked half passes against a gate stuck shut;
                    # asserting only the enabled half is the "renders and
                    # does nothing" defect. 25-02's helper owns both.
                    gate = _assert_js_gate(
                        browser, base_url, "/display", QUIET_HANDLES_SEL,
                        viewport=VIEWPORT_MIN_SUPPORTED)

                    # AND THE ARC IS PRESENT IN BOTH — which is what makes
                    # this dial's fallback a FEATURE rather than an
                    # absence. A check that skipped it would let a later
                    # refactor move the whole drawing behind the gate
                    # unnoticed, and nothing else here would object.
                    with _no_js_page(browser, base_url, "/display",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        # MEASURED, NOT COUNTED. locator.count() counts
                        # elements in the DOM whatever their box is, so
                        # it passes against an arc moved behind the gate
                        # — the exact refactor this clause exists to
                        # notice. The verdict is the rendered box.
                        blocked_arc = page.locator(QUIET_ARC_SEL).count()
                        blocked_arc_box = (
                            page.locator(QUIET_ARC_SEL).bounding_box()
                            if blocked_arc else None)
                        blocked_readout = page.locator(QUIET_READOUT_SEL).inner_text()
                        blocked_inputs = page.locator(
                            'input[name="quiet_hours_start"], '
                            'input[name="quiet_hours_end"]').count()
                        blocked_presets = page.locator("[data-quiet-preset]").count()
                        blocked_siblings = page.locator(
                            ".field-inline-value").count()
                    if blocked_arc != 1:
                        return False, (
                            "the quiet arc is not drawn with scripts blocked (%d found) — the "
                            "ring is SERVER-drawn and only the dragging is script"
                            % blocked_arc)
                    if not blocked_arc_box or blocked_arc_box["width"] <= 0 \
                            or blocked_arc_box["height"] <= 0:
                        return False, (
                            "the quiet arc is in the scripts-blocked document but occupies no "
                            "space (%r) — rendered is not drawn, and an arc behind the gate is "
                            "the refactor this clause exists to notice" % (blocked_arc_box,))
                    if blocked_inputs != 2 or blocked_presets != 3:
                        return False, (
                            "with scripts blocked the card renders %d time input(s) and %d "
                            "preset(s); it owes two and three"
                            % (blocked_inputs, blocked_presets))
                    if blocked_siblings < 2:
                        return False, (
                            "B14's visible 24h siblings are missing with scripts blocked "
                            "(%d found) — a browser in en-US renders the stored 23:00 as "
                            "'11:00 PM' beside a preset labelled 'Night (23:00-07:00)'"
                            % blocked_siblings)
                    if ":" not in blocked_readout:
                        return False, (
                            "the scripts-blocked readout says %r — the saved window has to be "
                            "legible without a script" % blocked_readout)
                    _ = gate
                    return True, ""
                check(
                    "the quiet window still SAVES with scripts blocked through the dial — both "
                    "ends set natively, submitted through the real form, re-read FROM DISK "
                    "after a fresh GET and restored the same way, at 360px and in BOTH shipped "
                    "languages; the gated handle layer has zero height and no keyboard can "
                    "reach into it with scripts blocked while it occupies space with them; and "
                    "the server-drawn ARC, the readout, both time inputs, B14's two 24h "
                    "siblings and the three presets are all present on the scripts-blocked "
                    "page, asserted after the save so none of them can stand in for it "
                    "(D-09/CFG-48, 25-04-PLAN.md Task 4)",
                    _the_window_still_saves_with_scripts_blocked_through_the_dial)

                def _dragging_and_keying_a_handle_reach_disk():
                    base_url = harness.base_url()
                    before = _quiet_hours_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        _set_window(page, base_url, "23:00", "07:00")

                        # 1. THE DRAG. Aimed at six o'clock on the ring,
                        # which is 12:00 — a point this check can compute
                        # without trusting the control's own arithmetic.
                        #
                        # SCROLLED TO THE MIDDLE OF THE VIEWPORT FIRST,
                        # for `_hit_area()`'s own recorded reason: at
                        # 360px this page is long and its tab bar is
                        # fixed to the bottom, so a coordinate gesture
                        # taken wherever the page happened to be scrolled
                        # is a gesture that lands somewhere else.
                        page.eval_on_selector(
                            QUIET_DIAL_SEL, "el => el.scrollIntoView({block: 'center'})")
                        box = page.evaluate(
                            "sel => { const r = document.querySelector(sel)"
                            "  .getBoundingClientRect();"
                            "  return [r.left + r.width / 2, r.top + r.height / 2,"
                            "          r.width, r.height]; }", QUIET_DIAL_SEL)
                        grip = page.evaluate(
                            "sel => { const r = document.querySelector(sel)"
                            "  .getBoundingClientRect();"
                            "  return [r.left + r.width / 2, r.top + r.height / 2]; }",
                            _handle_sel("quiet_hours_start"))
                        page.mouse.move(grip[0], grip[1])
                        page.mouse.down()
                        # The steering script focuses the handle it
                        # captured, so this is the page's own answer to
                        # "did the press reach the control", and it turns
                        # a silent no-op into a named diagnostic.
                        if not page.evaluate(
                                "sel => document.activeElement"
                                "  === document.querySelector(sel)",
                                _handle_sel("quiet_hours_start")):
                            page.mouse.up()
                            return False, (
                                "a pointer-down at the start handle's own centre (%r, dial box "
                                "%r) did not reach the steering script — nothing below measured "
                                "a drag" % (grip, box))
                        page.mouse.move(box[0], box[1] + box[3] / 2 - 8, steps=8)
                        page.mouse.up()
                        dragged = page.input_value('input[name="quiet_hours_start"]')
                        recorded["dragged_to"] = dragged
                        if dragged != "12:00":
                            return False, (
                                "dragging the start handle to six o'clock on the ring put %r "
                                "into quiet_hours_start; the bottom of a 24h dial is 12:00"
                                % dragged)
                        # THE ANNOUNCEMENT FOLLOWED THE DRAG, AND IT IS
                        # THE HANDLE THAT CARRIES IT. A wrapper holding
                        # role="slider" while the <button> inside takes
                        # the focus announces the saved value forever.
                        announced = page.get_attribute(
                            _handle_sel("quiet_hours_start"), "aria-valuetext")
                        if announced != dragged:
                            return False, (
                                "the handle announces %r while its own input now holds %r — a "
                                "screen-reader visitor is being told the value it had before "
                                "the drag" % (announced, dragged))
                        if page.get_attribute(
                                '[data-value-field="quiet_hours_start"]',
                                "aria-valuenow") is not None:
                            return False, (
                                "the wrapper carries aria-valuenow; the element a keyboard "
                                "visitor lands on is the button inside it, and two elements "
                                "announcing one value is how the stale one gets read")
                        # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED
                        # from auto-save onto the restored bar — a control
                        # that changes a value without notify()'s own real
                        # `change` event would lose the edit silently
                        # (value-controls.js's own notify() comment: "the
                        # bubbling notification dirty-state.js's delegated
                        # document-level listener is waiting for" —
                        # unchanged by this plan), so the drag REVEALING
                        # the bar is still the proof the event fired; the
                        # edit only reaches disk once Enregistrer is
                        # clicked.
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        recorded["dragged_stored"] = _quiet_hours_on_disk()[0]
                        if recorded["dragged_stored"] != "12:00":
                            return False, (
                                "the dragged value did not reach disk; it reads %r"
                                % (recorded["dragged_stored"],))
                        page.goto(base_url + "/display")
                        if page.input_value('input[name="quiet_hours_start"]') != "12:00":
                            return False, "the reloaded page does not show the dragged value"

                        # 2. THE KEYBOARD ALONE, with the pointer-free
                        # claim MEASURED rather than promised. One
                        # ArrowRight is one step, and the step is stated.
                        _set_window(page, base_url, "23:00", "07:00")
                        keyed = _operate_with_keyboard(
                            page, _handle_sel("quiet_hours_start"), ["ArrowRight"])
                        after_key = page.input_value('input[name="quiet_hours_start"]')
                        recorded["after_arrow"] = after_key
                        if after_key != "23:15":
                            return False, (
                                "one ArrowRight moved the start from 23:00 to %r; the stated "
                                "step is %d minutes" % (after_key, 15))
                        if keyed["pointer_events"]:
                            return False, "a pointer event fired during the keyboard sequence"
                        # HOME AND END REACH THE DAY'S OWN ENDS.
                        page.keyboard.press("End")
                        recorded["after_end"] = page.input_value(
                            'input[name="quiet_hours_start"]')
                        if recorded["after_end"] != "23:59":
                            return False, (
                                "End put %r into the start field; the day's last minute is "
                                "23:59" % (recorded["after_end"],))
                        page.keyboard.press("Home")
                        recorded["after_home"] = page.input_value(
                            'input[name="quiet_hours_start"]')
                        if recorded["after_home"] != "00:00":
                            return False, (
                                "Home put %r into the start field" % (recorded["after_home"],))

                        # 3. A PRESET MOVES BOTH HANDLES — the cheapest
                        # available proof that the two native inputs are
                        # the ONE source of truth: the presets write into
                        # those fields and know nothing about this
                        # control. (27-02-PLAN.md Task 4, CFG-71: what
                        # used to live here as sections 3-4 — this
                        # endpoint-only "the handles moved" claim and a
                        # separate "the readout names the window" claim —
                        # is SUPERSEDED by
                        # _the_arc_the_handles_and_the_caption_agree_
                        # after_an_interaction() below, which asserts
                        # agreement across all four surfaces after both a
                        # drag AND a preset, rather than four endpoint
                        # checks that can each be individually right
                        # while the page as a whole lies. This clause
                        # stays, narrowed to what it alone still proves:
                        # a preset is a SILENT script write with no
                        # event of its own, so it is a distinct code path
                        # from a drag and worth its own cheap proof that
                        # both handles still follow it.
                        _set_window(page, base_url, "12:00", "13:00")
                        fractions = page.evaluate(
                            "() => [...document.querySelectorAll('[data-value-control]')]"
                            "  .map(e => e.style.getPropertyValue('--value-fraction'))")
                        page.locator(
                            '[data-preset-start="08:00"]').click()
                        moved = page.evaluate(
                            "() => [...document.querySelectorAll('[data-value-control]')]"
                            "  .map(e => e.style.getPropertyValue('--value-fraction'))")
                        recorded["preset_fractions"] = (fractions, moved)
                        if len(moved) != 2 or moved == fractions:
                            return False, (
                                "a preset click left the handles at %r (they were at %r) — the "
                                "presets write into the two time inputs, so a handle driven BY "
                                "those inputs moves for free; one that did not is holding a "
                                "value of its own" % (moved, fractions))
                        if moved[0] == fractions[0] or moved[1] == fractions[1]:
                            return False, (
                                "a preset click moved only one handle: %r -> %r"
                                % (fractions, moved))
                        # RESTORED THROUGH THE SAME UI SEQUENCE, never
                        # a direct write to the state directory — a
                        # harness that changes a real setting is a test
                        # that edits its neighbours' subject.
                        _set_window(page, base_url, before[0], before[1])
                        if _quiet_hours_on_disk() != before:
                            return False, (
                                "this check left the window at %r; it started at %r"
                                % (_quiet_hours_on_disk(), before))
                        _ = recorded
                        return True, ""
                    finally:
                        # Best effort only, and deliberately silent: a
                        # restore that raised here would mask the failure
                        # it is cleaning up after. The happy path asserts
                        # the restore above.
                        try:
                            _set_window(page, base_url, before[0], before[1])
                        except Exception:
                            pass
                        context.close()
                check(
                    "dragging a quiet-hours handle changes its own native <input type=\"time\">, "
                    "moves the announcement ON THE HANDLE rather than on the wrapper, REVEALS the "
                    "bar and PERSISTS to disk once Enregistrer is clicked; one ArrowRight "
                    "moves exactly one stated step and End/Home reach 23:59 and 00:00 with zero "
                    "pointer events fired and the recorder proving itself; and a preset click moves "
                    "BOTH handles, which is what proves the two native inputs are the one source "
                    "of truth (the arc/caption AGREEMENT claim this check used to also carry is "
                    "superseded by "
                    "_the_arc_the_handles_and_the_caption_agree_after_an_interaction(), CFG-71, "
                    "27-02-PLAN.md Task 4) (CFG-48, 25-04-PLAN.md Task 4; retargeted from the "
                    "retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, "
                    "CFG-77/CFG-78)",
                    _dragging_and_keying_a_handle_reach_disk)

                # ----------------------------------------------------------
                # 27-02-PLAN.md Task 4 (CFG-62/CFG-71/D-32): THE ONE CHECK
                # that D17 shipped without. Three correct halves — the arc
                # asserted correct SERVER-SIDE for the saved value, the
                # handles asserted to MOVE, the value asserted to PERSIST —
                # and nothing ever asserted that the arc agrees with the
                # handles AFTER an interaction. Not four endpoint checks:
                # ONE check whose subject is agreement between all four
                # surfaces, covering BOTH the drag path and the preset
                # path, using 27-01's own `_assert_surfaces_agree()`.
                # ----------------------------------------------------------

                def _quiet_surfaces(page, where):
                    """The four surfaces `_assert_surfaces_agree()` decodes
                    for `page`, closed over the CURRENT `where` label so
                    every raised AssertionError names which path (drag or
                    preset, which theme) produced it.
                    """
                    def native_inputs():
                        return (
                            config_page.quiet_window_minute_of_day(
                                page.input_value('input[name="quiet_hours_start"]')),
                            config_page.quiet_window_minute_of_day(
                                page.input_value('input[name="quiet_hours_end"]')),
                        )

                    def handles_aria_valuenow():
                        return (
                            int(page.get_attribute(
                                _handle_sel("quiet_hours_start"), "aria-valuenow")),
                            int(page.get_attribute(
                                _handle_sel("quiet_hours_end"), "aria-valuenow")),
                        )

                    def arc_resolved_geometry():
                        return _quiet_arc_minutes(page, where)

                    def caption_text():
                        return _quiet_caption_minutes(page, where)

                    # An ORDERED mapping, so a disagreement's message lists
                    # the four surfaces in the same order a reader would
                    # look at the card: the fields, then the handles, then
                    # the drawing, then the sentence under it.
                    return {
                        "the two native <input type=\"time\"> fields": native_inputs,
                        "the two handles' aria-valuenow": handles_aria_valuenow,
                        "the arc's resolved geometry": arc_resolved_geometry,
                        "the caption's text": caption_text,
                    }

                def _the_arc_the_handles_and_the_caption_agree_after_an_interaction():
                    base_url = harness.base_url()
                    before_on_disk = _quiet_hours_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)

                        # A KNOWN, DETERMINISTIC STARTING WINDOW —
                        # 08:00-23:00 — chosen so the drag below only has
                        # to move the END handle to reach the developer's
                        # own recording (08:00-18:00): the start is
                        # already right. _set_window() saves and reloads,
                        # so this is real, on-disk state exactly like
                        # every neighbouring dial check reaches it.
                        #
                        # 27-04-PLAN.md Task 4 (CFG-63): SUPERSEDES this
                        # paragraph's own former "once, before the loop,
                        # not inside it" instruction — that reasoning
                        # depended on "neither the drag nor the preset
                        # below ever clicks Save", which auto-save makes
                        # FALSE: both value-controls.js's own notify()
                        # (the drag) and dirty-state.js's preset handler
                        # now fire a real `change` that saves to disk
                        # immediately, same as every other committing
                        # interaction in this app. So the baseline is
                        # reset INSIDE the loop instead, once per theme,
                        # or the second iteration would start from
                        # whatever the FIRST iteration's own preset left
                        # on disk (23:00-07:00) rather than the known
                        # 08:00-23:00 this check's own arithmetic assumes.
                        for theme in UI_THEMES_EXPLICIT:
                            _set_window(page, base_url, "08:00", "23:00")
                            _set_ui_theme(page, theme)

                            # 1. THE DRAG PATH. Aimed at nine o'clock on the
                            # ring, which is 18:00 — the same
                            # scroll-into-view-first, box-relative aiming
                            # `_dragging_and_keying_a_handle_reach_disk()`
                            # above already uses and for the same reason
                            # (the page is long and its tab bar is fixed to
                            # the bottom at this viewport).
                            page.eval_on_selector(
                                QUIET_DIAL_SEL, "el => el.scrollIntoView({block: 'center'})")
                            box = page.evaluate(
                                "sel => { const r = document.querySelector(sel)"
                                "  .getBoundingClientRect();"
                                "  return [r.left + r.width / 2, r.top + r.height / 2,"
                                "          r.width, r.height]; }", QUIET_DIAL_SEL)
                            grip = page.evaluate(
                                "sel => { const r = document.querySelector(sel)"
                                "  .getBoundingClientRect();"
                                "  return [r.left + r.width / 2, r.top + r.height / 2]; }",
                                _handle_sel("quiet_hours_end"))
                            page.mouse.move(grip[0], grip[1])
                            page.mouse.down()
                            if not page.evaluate(
                                    "sel => document.activeElement"
                                    "  === document.querySelector(sel)",
                                    _handle_sel("quiet_hours_end")):
                                page.mouse.up()
                                return False, (
                                    "%s: a pointer-down at the end handle's own centre (%r, dial "
                                    "box %r) did not reach the steering script"
                                    % (theme, grip, box))
                            page.mouse.move(box[0] - box[2] / 2 + 8, box[1], steps=8)
                            page.mouse.up()
                            dragged_end = page.input_value('input[name="quiet_hours_end"]')
                            recorded["%s/dragged_end" % theme] = dragged_end
                            if dragged_end != "18:00":
                                return False, (
                                    "%s: dragging the end handle to nine o'clock on the ring put "
                                    "%r into quiet_hours_end; nine o'clock on this 24h dial is "
                                    "18:00" % (theme, dragged_end))

                            requested_drag = (8 * 60, 18 * 60)
                            before_drag = (8 * 60, 23 * 60)
                            agreed_drag = _assert_surfaces_agree(
                                page, _quiet_surfaces(page, "%s theme, drag path" % theme),
                                requested_drag, before_drag,
                                "%s theme, drag path" % theme)
                            recorded["%s/drag" % theme] = agreed_drag

                            # 2. THE PRESET PATH, from wherever the drag
                            # above left the pair. Both paths were reported
                            # working for the handles and broken for the
                            # arc, so both belong to the SAME agreement
                            # assertion — two separate checks would
                            # re-create the very split this phase exists to
                            # close.
                            page.locator('[data-preset-start="23:00"]').click()
                            requested_preset = (23 * 60, 7 * 60)
                            agreed_preset = _assert_surfaces_agree(
                                page, _quiet_surfaces(page, "%s theme, preset path" % theme),
                                requested_preset, requested_drag,
                                "%s theme, preset path" % theme)
                            recorded["%s/preset" % theme] = agreed_preset

                            # 29-04-PLAN.md Task 3 (CFG-80), added to
                            # THIS existing check rather than as a new
                            # `check(...)` call — folded in per the
                            # plan's own instruction not to move this
                            # file's EXPECTED_CHECK_COUNT for an
                            # assertion nobody in this worktree could
                            # verify (playwright is not installed here;
                            # this whole file reports SKIPPED, never a
                            # pass, until it is). A FIFTH surface, after
                            # the same preset click the four above just
                            # agreed on: each twin's OWN visibility must
                            # match the browser's own resolved hour
                            # cycle — hidden when it is unambiguously
                            # 24h, visible otherwise — read from the
                            # live DOM's `.hidden` property, never from
                            # the served HTML (which is a SEPARATE,
                            # runnable proof in test_config_page.py).
                            resolved_hour12 = page.evaluate(
                                "() => { try { return new Intl.DateTimeFormat("
                                "undefined, {hour: 'numeric'})"
                                ".resolvedOptions().hour12; } catch (e) { return null; } }")
                            expect_hidden = resolved_hour12 is False
                            for field in ("quiet_hours_start", "quiet_hours_end"):
                                twin_hidden = page.eval_on_selector(
                                    'input[name="%s"] ~ [%s]'
                                    % (field, config_page.QUIET_NORMALISED_TIME_ATTR),
                                    "el => el.hidden")
                                if twin_hidden != expect_hidden:
                                    return False, (
                                        "%s theme, preset path: this browser's own resolved "
                                        "hour12 is %r (expected twin hidden=%r) but %s's "
                                        "normalised-time twin is hidden=%r — a false negative "
                                        "here (hidden=True on a browser that in fact paints "
                                        "12h) reopens the exact defect B14 exists to prevent"
                                        % (theme, resolved_hour12, expect_hidden, field,
                                           twin_hidden))
                            recorded["%s/twin_visibility" % theme] = (
                                resolved_hour12, expect_hidden)

                        # 3. THE SCRIPTS-BLOCKED HALF. 27-04-PLAN.md
                        # (CFG-63): SUPERSEDES this paragraph's own former
                        # claim that neither interaction above reaches
                        # disk — under auto-save, the PRESET path's own
                        # commit is the last thing either loop iteration
                        # does, so disk now holds whatever that preset
                        # last wrote (23:00-07:00), not the 08:00-23:00
                        # baseline. `saved` below is read FRESH, right
                        # here, so it already reflects that correctly —
                        # only this comment's account was stale. A FRESH,
                        # scripts-blocked load must still draw whatever
                        # window is actually saved, from the presentation
                        # attributes alone.
                        saved = _quiet_hours_on_disk()
                        saved_minutes = (
                            config_page.quiet_window_minute_of_day(saved[0]),
                            config_page.quiet_window_minute_of_day(saved[1]))
                        with _no_js_page(browser, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as no_js_page:
                            dash_attr = no_js_page.get_attribute(QUIET_ARC_SEL, "stroke-dasharray")
                            transform_attr = no_js_page.get_attribute(QUIET_ARC_SEL, "transform")
                            if not dash_attr or not transform_attr:
                                return False, (
                                    "scripts-blocked: the arc is missing stroke-dasharray/"
                                    "transform (%r, %r) — the no-JS floor requires the server-"
                                    "drawn presentation attributes to be present with no script "
                                    "running at all" % (dash_attr, transform_attr))
                            static_minutes = _quiet_arc_minutes(
                                no_js_page, "scripts-blocked, no .js override in force")
                        recorded["scripts_blocked"] = (saved, static_minutes)
                        if static_minutes != saved_minutes:
                            return False, (
                                "scripts-blocked: the arc's presentation attributes decode to %r, "
                                "but the saved window on disk is %r (%r) — the server-rendered arc "
                                "must stay authoritative for the saved value with no script "
                                "running at all" % (static_minutes, saved_minutes, saved))

                        # RESTORED THROUGH THE SAME UI SEQUENCE, never a
                        # direct write to the state directory.
                        _set_window(page, base_url, before_on_disk[0], before_on_disk[1])
                        if _quiet_hours_on_disk() != before_on_disk:
                            return False, (
                                "this check left the window at %r; it started at %r"
                                % (_quiet_hours_on_disk(), before_on_disk))
                        _ = recorded
                        return True, ""
                    finally:
                        try:
                            _set_window(page, base_url, before_on_disk[0], before_on_disk[1])
                        except Exception:
                            pass
                        context.close()
                check(
                    "THE arc/handles/caption agreement check (CFG-62/CFG-71/D-32, "
                    "27-02-PLAN.md Task 4): in BOTH themes, after dragging the end handle to "
                    "reach the developer's own recorded window (08:00→18:00) AND, in the "
                    "same check, after pressing a preset (23:00→07:00, the wrap through "
                    "midnight) from wherever the drag left it, all FOUR surfaces — the two "
                    "native <input type=\"time\"> fields, the two handles' aria-valuenow, the "
                    "arc's RESOLVED geometry (read back through getComputedStyle, not the "
                    "static attribute), and the caption's own text — decode to the SAME "
                    "canonical (start_minute, end_minute) pair, which equals what the "
                    "interaction requested and differs from what was there before; AND, after "
                    "the same preset click, each B14 twin's own live .hidden property matches "
                    "this browser's resolved hour12 (CFG-80, 29-04-PLAN.md Task 3, folded into "
                    "this existing check rather than a new one so EXPECTED_CHECK_COUNT does not "
                    "move for an assertion this worktree has never run); separately, "
                    "with scripts blocked, the arc still carries both presentation attributes "
                    "and they still decode to whatever window is actually saved on disk — under "
                    "auto-save that is the preset's own commit, read fresh rather than assumed "
                    "(27-04-PLAN.md Task 4, CFG-63)",
                    _the_arc_the_handles_and_the_caption_agree_after_an_interaction)

                def _the_dial_caption_keeps_its_form_after_every_interaction_kind():
                    # 28-03-PLAN.md Task 3 (CFG-73 Bug A): the developer's
                    # own report was that the caption reverts to a raw,
                    # blank-duration form after EVERY interaction, not
                    # just a drag — so this check drives all FOUR kinds
                    # (drag, keyboard, typed field edit, preset), in this
                    # order, on the SAME page, and reads the caption's
                    # ACTUAL DISPLAYED TEXT after each one.
                    base_url = harness.base_url()
                    before = _quiet_hours_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        for lang in ("en", "fr"):
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            # A KNOWN, DETERMINISTIC STARTING WINDOW,
                            # reset EVERY language pass for the identical
                            # reason 27-02-PLAN.md Task 4's own agreement
                            # check resets inside its loop: auto-save
                            # means the second language pass would
                            # otherwise start from whatever the FIRST
                            # pass's own preset left on disk.
                            _set_window(page, base_url, "08:00", "23:00")

                            # THE REFERENCE SHAPE — captured from the
                            # server-rendered page, BEFORE any
                            # interaction, on THIS language pass.
                            reference_text = page.locator(
                                _QUIET_READOUT_SELECTOR).text_content()
                            reference_shape = _quiet_caption_shape(reference_text)
                            recorded["%s/reference" % lang] = reference_text

                            def _assert_after(requested, kind):
                                caption_text = page.locator(
                                    _QUIET_READOUT_SELECTOR).text_content()
                                decoded = _quiet_caption_minutes(
                                    page, "%s/%s" % (lang, kind))
                                if decoded != requested:
                                    return (
                                        "%s/%s: the caption decodes to %r; the interaction "
                                        "requested %r" % (lang, kind, decoded, requested))
                                duration_text = _quiet_duration_span_text(
                                    page, "%s/%s" % (lang, kind))
                                if not duration_text:
                                    return (
                                        "%s/%s: the duration segment is EMPTY after this "
                                        "interaction — this is the exact regression the "
                                        "developer reported" % (lang, kind))
                                expected_duration = _expected_quiet_duration_text(
                                    page, requested, "%s/%s" % (lang, kind))
                                if duration_text != expected_duration:
                                    return (
                                        "%s/%s: the duration segment reads %r; the wrapped-"
                                        "difference computation, worded from the page's own "
                                        "layout.DURATION_ATTRS, expects %r"
                                        % (lang, kind, duration_text, expected_duration))
                                shape = _quiet_caption_shape(caption_text)
                                if shape != reference_shape:
                                    return (
                                        "%s/%s: the caption's FORM changed — the server-"
                                        "rendered reference is %r (shape %r), the live caption "
                                        "after this interaction is %r (shape %r)"
                                        % (lang, kind, reference_text, reference_shape,
                                           caption_text, shape))
                                return None

                            # 1. DRAG the end handle to nine o'clock,
                            # which is 18:00 — the same aiming
                            # `_the_arc_the_handles_and_the_caption_
                            # agree_after_an_interaction()` above uses.
                            page.eval_on_selector(
                                QUIET_DIAL_SEL,
                                "el => el.scrollIntoView({block: 'center'})")
                            box = page.evaluate(
                                "sel => { const r = document.querySelector(sel)"
                                "  .getBoundingClientRect();"
                                "  return [r.left + r.width / 2, r.top + r.height / 2,"
                                "          r.width, r.height]; }", QUIET_DIAL_SEL)
                            grip = page.evaluate(
                                "sel => { const r = document.querySelector(sel)"
                                "  .getBoundingClientRect();"
                                "  return [r.left + r.width / 2, r.top + r.height / 2]; }",
                                _handle_sel("quiet_hours_end"))
                            page.mouse.move(grip[0], grip[1])
                            page.mouse.down()
                            if not page.evaluate(
                                    "sel => document.activeElement"
                                    "  === document.querySelector(sel)",
                                    _handle_sel("quiet_hours_end")):
                                page.mouse.up()
                                return False, (
                                    "%s: a pointer-down at the end handle's own centre did not "
                                    "reach the steering script" % lang)
                            page.mouse.move(box[0] - box[2] / 2 + 8, box[1], steps=8)
                            page.mouse.up()
                            requested_drag = (8 * 60, 18 * 60)
                            problem = _assert_after(requested_drag, "drag")
                            if problem:
                                return False, problem

                            # 2. KEYBOARD: one ArrowRight on the START
                            # handle — QUIET_DIAL_HANDLE_STEP is 15
                            # minutes.
                            _operate_with_keyboard(
                                page, _handle_sel("quiet_hours_start"), ["ArrowRight"])
                            requested_keyboard = (8 * 60 + 15, 18 * 60)
                            problem = _assert_after(requested_keyboard, "keyboard step")
                            if problem:
                                return False, problem

                            # 3. TYPED FIELD EDIT: the `.fill()` shape,
                            # committed the same way `_set_window()`
                            # commits each field.
                            page.fill('input[name="quiet_hours_end"]', "19:00")
                            _commit_field(page, 'input[name="quiet_hours_end"]')
                            requested_typed = (8 * 60 + 15, 19 * 60)
                            problem = _assert_after(requested_typed, "typed field edit")
                            if problem:
                                return False, problem

                            # 4. PRESET CLICK — a silent script write
                            # with no event of its own, and the ONE
                            # interaction kind here that crosses
                            # midnight (23:00 -> 07:00), so the wrapped-
                            # difference duration computation is
                            # genuinely exercised, not merely stated.
                            page.locator('[data-preset-start="23:00"]').click()
                            requested_preset = (23 * 60, 7 * 60)
                            problem = _assert_after(requested_preset, "preset click")
                            if problem:
                                return False, problem

                        _set_window(page, base_url, before[0], before[1])
                        if _quiet_hours_on_disk() != before:
                            return False, (
                                "this check left the window at %r; it started at %r"
                                % (_quiet_hours_on_disk(), before))
                        _ = recorded
                        return True, ""
                    finally:
                        try:
                            _set_window(page, base_url, before[0], before[1])
                        except Exception:
                            pass
                        context.close()
                check(
                    "the dial caption keeps the SAME FORM the server emits at load after EACH "
                    "of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 "
                    "Bug A, 28-03-PLAN.md Task 3): after every one, the caption's two \"HH:MM\" "
                    "tokens decode to what the interaction requested, its duration segment is "
                    "NON-EMPTY and equals the wrapped-difference computation worded from the "
                    "page's own layout.DURATION_ATTRS (never a hardcoded unit literal), and the "
                    "whole caption's structural shape (separators, spacing, token order) "
                    "matches the server-rendered reference captured before any interaction — in "
                    "BOTH shipped languages, with the preset step crossing midnight",
                    _the_dial_caption_keeps_its_form_after_every_interaction_kind)

                def _the_dial_meets_its_floors_at_360px_in_both_themes():
                    base_url = harness.base_url()
                    before = _quiet_hours_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)

                        # 1. THE HIT TARGETS, IN THIS CONTROL'S OWN
                        # CONTAINER. A class-level measurement is worth
                        # nothing here: 25-02 measured `.copy-btn`'s
                        # declared 44x44 at a real 34x26 because its
                        # neighbours covered the ::before that synthesises
                        # it. Two windows: ends far apart (the control)
                        # and ends close together (the real test).
                        # WHY "CLOSE" IS FOUR HOURS AND NOT FIFTEEN
                        # MINUTES, stated rather than tuned: two 44px
                        # targets on ONE ring cannot both clear the floor
                        # at every separation, and that is geometry, not
                        # a defect to fix. Each target is a 46px box, so
                        # neither may intrude within 22px of the other's
                        # centre — which needs about 45px between the two
                        # centres on one axis, and in the worst (45°)
                        # orientation that is 45*sqrt(2) of chord. On
                        # this 176px ring (radius 78) that is about 3h12;
                        # on the 128px ring this control started as it
                        # was about 4h49, which is what moved the size.
                        # Four hours is inside the reachable band with
                        # room to spare and is a window a person really
                        # sets. The genuinely overlapping case is
                        # measured below, and answered by a decision.
                        for label, (start, end) in (("far", ("23:00", "07:00")),
                                                    ("close", ("23:00", "03:00"))):
                            _set_window(page, base_url, start, end)
                            for field in ("quiet_hours_start", "quiet_hours_end"):
                                seen = _assert_hit_target(
                                    page, _handle_sel(field),
                                    "the %s handle with the window's ends %s apart"
                                    % (field, label))
                                recorded["%s/%s" % (label, field)] = (
                                    seen["visual"], seen["hit"], seen["reach"])

                        # AND THE OVERLAP CASE, RECORDED RATHER THAN
                        # ASSERTED AWAY. There is deliberately no minimum
                        # separation in the VALUE — a zero-length window
                        # is a real, defined state that
                        # server.device_config's own arithmetic calls
                        # never-active, and refusing it here would make a
                        # state reachable by typing unreachable by
                        # dragging. What happens instead is a decision:
                        # z-order is DOCUMENT order, the end handle is
                        # emitted second, so the END handle wins a
                        # pointer-down in the overlap. That is sufficient
                        # rather than arbitrary — moving either end
                        # separates the pair, and the start handle stays
                        # its own tab stop whatever it is painted under.
                        _set_window(page, base_url, "23:00", "23:15")
                        overlap = _assert_hit_target(
                            page, _handle_sel("quiet_hours_end"),
                            "the end handle with the two ends 15 minutes apart")
                        recorded["overlap/quiet_hours_end"] = (
                            overlap["visual"], overlap["hit"])
                        try:
                            _hit_area(page, _handle_sel("quiet_hours_start"))
                            recorded["overlap/quiet_hours_start"] = "reachable"
                        except AssertionError as exc:
                            recorded["overlap/quiet_hours_start"] = "occluded"
                            if "hit-tests to" not in str(exc):
                                return False, (
                                    "the start handle failed the overlap measurement for a "
                                    "reason other than the stated z-order: %s" % exc)
                        focusable = page.evaluate(
                            "sel => { const el = document.querySelector(sel);"
                            "  el.focus(); return document.activeElement === el; }",
                            _handle_sel("quiet_hours_start"))
                        if not focusable:
                            return False, (
                                "with the two ends overlapping, the start handle cannot take "
                                "focus — the stated escape from an overlap is that it stays "
                                "its own tab stop whatever it is painted under")

                        # 2. THE GEOMETRY, MEASURED WITH
                        # getBoundingClientRect AND NOT clientWidth.
                        # clientWidth rounds to an integer and can fail a
                        # correct drawing; this control's own card carries
                        # no scale, but the rule is the file's.
                        _set_window(page, base_url, "23:00", "07:00")
                        geometry = page.evaluate(
                            "args => {"
                            "  const dial = document.querySelector(args.dial);"
                            "  const svg = dial.querySelector('svg');"
                            "  const parent = dial.parentElement;"
                            "  const pr = parent.getBoundingClientRect();"
                            "  const ps = getComputedStyle(parent);"
                            "  const dr = dial.getBoundingClientRect();"
                            "  const readout = document.querySelector(args.readout);"
                            "  const rs = getComputedStyle(readout);"
                            "  const range = document.createRange();"
                            "  range.selectNodeContents(readout);"
                            "  const tr = range.getBoundingClientRect();"
                            "  const rr = readout.getBoundingClientRect();"
                            "  const hours = {};"
                            "  for (const h of ['0', '6', '12', '18']) {"
                            "    const el = document.querySelector("
                            "      '.quiet-dial__hour--' + h);"
                            "    if (!el) { hours[h] = null; continue; }"
                            "    const b = el.getBoundingClientRect();"
                            "    hours[h] = [b.left + b.width / 2 - (dr.left + dr.width / 2),"
                            "                b.top + b.height / 2 - (dr.top + dr.height / 2)];"
                            "  }"
                            "  return {"
                            "    dial: [dr.width, dr.height],"
                            "    svgDisplay: getComputedStyle(svg).display,"
                            "    dialCentre: dr.left + dr.width / 2,"
                            "    contentCentre: pr.left + parseFloat(ps.paddingLeft)"
                            "      + (pr.width - parseFloat(ps.paddingLeft)"
                            "         - parseFloat(ps.paddingRight)) / 2,"
                            "    readoutMargins: [rs.marginTop, rs.marginBottom],"
                            "    readoutTextCentre: tr.left + tr.width / 2,"
                            "    readoutBoxCentre: rr.left + rr.width / 2,"
                            "    hours: hours};"
                            "}", {"dial": QUIET_DIAL_SEL, "readout": QUIET_READOUT_SEL})
                        recorded["geometry"] = geometry
                        width, height = geometry["dial"]
                        drawn = config_page.QUIET_DIAL_SIZE
                        if abs(width - drawn) > 0.5 or abs(height - drawn) > 0.5:
                            return False, (
                                "the dial measures %.2fx%.2f; its emitter draws a %dpx canvas "
                                "and the handles are thrown out to a radius derived from it"
                                % (width, height, drawn))
                        if geometry["svgDisplay"] != "block":
                            return False, (
                                "the ring computes display:%s — a replaced-inline <svg> sits on "
                                "a text baseline and leaves a descender gap under a drawing "
                                "that has already ended" % geometry["svgDisplay"])
                        if abs(geometry["dialCentre"] - geometry["contentCentre"]) > 2:
                            return False, (
                                "the dial's centre is %.2f and its card's content centre is "
                                "%.2f — a drawing captioned by a centred readout has to be "
                                "centred itself"
                                % (geometry["dialCentre"], geometry["contentCentre"]))
                        if geometry["readoutMargins"][0] != "0px":
                            return False, (
                                "the readout computes margin-top:%s — a <p>'s own 1em margin "
                                "opens a gap between a picture and its caption"
                                % geometry["readoutMargins"][0])
                        if geometry["readoutMargins"][1] == "0px":
                            return False, (
                                "the readout computes no bottom margin, so it sits hard against "
                                "the preset row under it")
                        if abs(geometry["readoutTextCentre"]
                               - geometry["readoutBoxCentre"]) > 1:
                            return False, (
                                "the readout's text is not centred in its own box (%.2f against "
                                "%.2f) — a left-aligned caption under a centred drawing reads "
                                "as a stray sentence"
                                % (geometry["readoutTextCentre"],
                                   geometry["readoutBoxCentre"]))

                        # 3. THE FOUR ANCHOR HOURS ARE WHERE THEY CLAIM TO
                        # BE. Each is placed by its own edge and then
                        # pulled back by half of itself; dropping either
                        # half puts a numeral off its own axis, which no
                        # string assertion can see.
                        for hour, (want_dx, want_dy) in (
                                ("0", (0, -1)), ("6", (1, 0)),
                                ("12", (0, 1)), ("18", (-1, 0))):
                            offset = geometry["hours"][hour]
                            if offset is None:
                                return False, "the %s label is missing from the dial" % hour
                            dx, dy = offset
                            along = dx if want_dx else dy
                            across = dy if want_dx else dx
                            if (want_dx or want_dy) > 0 and along < 20:
                                return False, (
                                    "the %s label sits %.2f along its own axis from the dial's "
                                    "centre; it belongs on the far side" % (hour, along))
                            if (want_dx or want_dy) < 0 and along > -20:
                                return False, (
                                    "the %s label sits %.2f along its own axis from the dial's "
                                    "centre; it belongs on the far side" % (hour, along))
                            if abs(across) > 4:
                                return False, (
                                    "the %s label is %.2fpx off the axis it is meant to be "
                                    "centred on — the half-of-itself pull-back is not being "
                                    "applied" % (hour, across))

                        # 4. NO SIDEWAYS PAGE SCROLL at the narrowest
                        # supported screen. 24-02's helper, not a second
                        # convention about what "the page" means.
                        message = _assert_no_page_overflow(
                            page, "the quiet dial on /display",
                            VIEWPORT_MIN_SUPPORTED["width"])
                        if message:
                            return False, message
                        recorded["page"] = page.evaluate(
                            "() => [document.documentElement.scrollWidth,"
                            "       document.documentElement.clientWidth]")

                        # 5. THE PAINT, IN BOTH THEMES, AS A FLOOR AND NOT
                        # ONLY A CEILING. "Not the SVG default" passes
                        # against a ring where the day and the window are
                        # the same flat grey; the floor is that they are
                        # two different paints and that each differs
                        # between the themes.
                        samples = {
                            "day": (".quiet-dial__day", "stroke"),
                            "arc": (".quiet-dial__arc", "stroke"),
                            "hour": (".quiet-dial__hour", "color"),
                            "grip": (".quiet-dial__handle", "background-color"),
                            "grip-edge": (".quiet-dial__handle", "border-top-color"),
                        }
                        paints = []
                        for measured in _in_both_themes(page):
                            if not page.evaluate(_SETTLE_DIAL):
                                return False, (
                                    "%s: nothing matched the settle probe, so nothing below "
                                    "measured anything" % (measured["theme"],))
                            sample = {}
                            for name, (selector, prop) in samples.items():
                                seen = _computed_paint(page, selector, props=(prop,))
                                if prop in seen["svg_default"]:
                                    return False, (
                                        "%s: the %s shape's %s is %r, indistinguishable from "
                                        "the SVG initial value — it takes no colour from the "
                                        "stylesheet at all"
                                        % (measured["theme"], name, prop, seen[prop]))
                                sample[name] = seen[prop]
                            if sample["day"] == sample["arc"]:
                                return False, (
                                    "%s: the whole day and the quiet window paint identically "
                                    "(%r) — the ring shows nothing"
                                    % (measured["theme"], sample["arc"]))
                            if sample["arc"] == sample["hour"]:
                                return False, (
                                    "%s: the quiet window and the hour labels that orient it "
                                    "paint identically (%r) — the labels are context and must "
                                    "not compete with the reading"
                                    % (measured["theme"], sample["arc"]))
                            if sample["grip"] == sample["grip-edge"]:
                                return False, (
                                    "%s: the handle's fill and its edge are the same colour "
                                    "(%r), so the grip is a flat dot with no edge"
                                    % (measured["theme"], sample["grip"]))
                            paints.append((measured["theme"], sample))
                        if len(paints) != 2:
                            return False, (
                                "expected a measurement in each theme, got %d" % len(paints))
                        light, dark = paints[0][1], paints[1][1]
                        for name in sorted(samples):
                            if light[name] == dark[name]:
                                return False, (
                                    "the %s paint is %r in BOTH themes — it is not coming from "
                                    "a token that inverts, so one of the two themes is wrong"
                                    % (name, light[name]))
                        recorded["paints"] = paints
                        _set_window(page, base_url, before[0], before[1])
                        if _quiet_hours_on_disk() != before:
                            return False, (
                                "this check left the window at %r; it started at %r"
                                % (_quiet_hours_on_disk(), before))
                        return True, ""
                    finally:
                        # Best effort only — see the neighbouring check.
                        try:
                            _set_window(page, base_url, before[0], before[1])
                        except Exception:
                            pass
                        context.close()
                check(
                    "the quiet dial meets its floors at 360px — BOTH handles clear the 44px "
                    "touch target by real hit-testing in THEIR OWN container with the window's "
                    "ends far apart AND close together, with the overlapping case measured and "
                    "its document-order z-rule confirmed (the end handle grabbable, the start "
                    "handle still focusable); the drawing measures its emitter's own declared size by "
                    "getBoundingClientRect rather than clientWidth, computes display:block, is "
                    "centred in its card and captioned by a centred readout with no top margin; "
                    "the four anchor hours each sit on their own axis; the page does not scroll "
                    "sideways; and the paint is a FLOOR not a ceiling — the day and the window "
                    "are different colours, the labels that orient it are weaker than it is, the grip "
                    "has an edge, and every one of the five "
                    "differs between the two themes (CFG-48/CFG-52, 25-04-PLAN.md Task 4)",
                    _the_dial_meets_its_floors_at_360px_in_both_themes)

                # ----------------------------------------------------------
                # 28-02-PLAN.md Task 2 (CFG-73, Bug B): THE check the bug's
                # own before/after recovery let every earlier check miss.
                # `.quiet-dial__handle` measured 78px from the dial's
                # centre (correct, on the ring) at press, collapsing to
                # 14-16px (the centre) within 90-150ms as the base `button`
                # rule's `transition: transform .15s ease` animated the
                # collapse, then recovering to 78px ~200ms after release —
                # so an endpoint-only check (before/after) passes on the
                # broken stylesheet. This is this project's own "assert
                # relationships, not just endpoints" contract applied to a
                # time axis instead of a surface axis: it SAMPLES the
                # handle's resolved distance from the dial's own centre
                # continuously across a held press, rather than reading the
                # two ends of it.
                # ----------------------------------------------------------

                def _the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press():
                    """A PRESS, NOT A DRAG: the pointer never moves after
                    mouse.down(), so the value the control reports must be
                    byte-identical before and after — a fix that ever gets
                    "helped along" by suppressing the handle's pointer
                    handling would fail this clause even while passing the
                    geometry one.
                    """
                    base_url = harness.base_url()
                    before_on_disk = _quiet_hours_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        # Set ONCE, outside the loop — unlike the
                        # neighbouring drag/preset checks, a plain
                        # press-and-hold with no drag changes NOTHING
                        # (that is this check's own value-identity
                        # clause below), so calling _set_window() again
                        # inside the loop with the SAME values would ask
                        # the app to "save" a value it already holds;
                        # dirty-state.js's own countDifferences() would
                        # read zero, the bar would never reveal itself,
                        # and _wait_for_bar() would time out waiting for a
                        # reveal that correctly never comes — 28-10-PLAN.md
                        # Task 1 (CFG-77/CFG-78): the identical reason
                        # _set_window() itself now guards on this, measured
                        # live, not guessed.
                        _set_window(page, base_url, "23:00", "07:00")
                        for theme in UI_THEMES_EXPLICIT:
                            _set_ui_theme(page, theme)

                            page.eval_on_selector(
                                QUIET_DIAL_SEL, "el => el.scrollIntoView({block: 'center'})")
                            grip = page.evaluate(
                                "sel => { const r = document.querySelector(sel)"
                                "  .getBoundingClientRect();"
                                "  return [r.left + r.width / 2, r.top + r.height / 2]; }",
                                _handle_sel("quiet_hours_start"))
                            before_value = page.input_value(
                                'input[name="quiet_hours_start"]')

                            page.mouse.move(grip[0], grip[1])
                            page.mouse.down()
                            if not page.evaluate(
                                    "sel => document.activeElement"
                                    "  === document.querySelector(sel)",
                                    _handle_sel("quiet_hours_start")):
                                page.mouse.up()
                                return False, (
                                    "%s: a pointer-down at the start handle's own centre (%r) "
                                    "did not reach the steering script — nothing below sampled "
                                    "a held press" % (theme, grip))

                            # THE SAMPLE, taken while the button is STILL
                            # DOWN. One page.evaluate, one rAF loop, so the
                            # whole window is sampled with no Python-side
                            # round trip resetting the clock between
                            # frames (a round trip here would widen the
                            # very gaps a frame-timed bug hides in). >=
                            # 400ms because the measured collapse completes
                            # by 90-150ms and the recovery lands ~200ms
                            # after release — a shorter window would
                            # reproduce the exact blind spot this check
                            # exists to close. The ring radius is read
                            # from --quiet-dial-radius, the SAME custom
                            # property the handle's own transform reads,
                            # never hardcoded as 78.
                            sampled = page.evaluate(
                                "async (args) => {"
                                "  const handle = document.querySelector(args.handleSel);"
                                "  const dial = document.querySelector(args.dialSel);"
                                "  const radiusRaw = getComputedStyle(dial)"
                                "    .getPropertyValue('--quiet-dial-radius');"
                                "  const radius = parseFloat(radiusRaw);"
                                "  const samples = [];"
                                "  const t0 = performance.now();"
                                "  while (performance.now() - t0 < args.durationMs) {"
                                "    const hr = handle.getBoundingClientRect();"
                                "    const dr = dial.getBoundingClientRect();"
                                "    const hcx = hr.left + hr.width / 2;"
                                "    const hcy = hr.top + hr.height / 2;"
                                "    const dcx = dr.left + dr.width / 2;"
                                "    const dcy = dr.top + dr.height / 2;"
                                "    samples.push({"
                                "      t: performance.now() - t0,"
                                "      dist: Math.hypot(hcx - dcx, hcy - dcy)});"
                                "    await new Promise(r => requestAnimationFrame(r));"
                                "  }"
                                # windowMs is measured AFTER the loop exits,
                                # not read off the last sample's own `t` —
                                # that timestamp is necessarily taken
                                # BEFORE the loop's own exit check runs
                                # (the sample is pushed, THEN one more
                                # frame is awaited, THEN the condition is
                                # re-tested), so the last sample's `t` is
                                # always at least one frame short of the
                                # loop's real elapsed time. Gating on the
                                # sample's own `t` instead of this value
                                # made the check fail on a correct run.
                                "  const windowMs = performance.now() - t0;"
                                "  return {radius: radius, radiusRaw: radiusRaw,"
                                "          samples: samples, windowMs: windowMs};"
                                "}",
                                {"handleSel": _handle_sel("quiet_hours_start"),
                                 "dialSel": QUIET_DIAL_SEL, "durationMs": 400})

                            page.mouse.up()
                            after_value = page.input_value(
                                'input[name="quiet_hours_start"]')

                            # ONE FINAL SAMPLE, after release — the
                            # recovery state, which is the ONLY state
                            # today's broken code already gets right and
                            # therefore the one that must not be mistaken
                            # for the whole proof: a check that only read
                            # this would pass against the exact bug this
                            # check exists to catch.
                            released = page.evaluate(
                                "args => {"
                                "  const handle = document.querySelector(args.handleSel);"
                                "  const dial = document.querySelector(args.dialSel);"
                                "  const hr = handle.getBoundingClientRect();"
                                "  const dr = dial.getBoundingClientRect();"
                                "  return Math.hypot("
                                "    (hr.left + hr.width / 2) - (dr.left + dr.width / 2),"
                                "    (hr.top + hr.height / 2) - (dr.top + dr.height / 2));"
                                "}",
                                {"handleSel": _handle_sel("quiet_hours_start"),
                                 "dialSel": QUIET_DIAL_SEL})

                            samples = sampled["samples"]
                            radius = sampled["radius"]
                            window_ms = sampled["windowMs"]
                            recorded["%s/samples" % theme] = len(samples)
                            recorded["%s/window_ms" % theme] = window_ms
                            if len(samples) < 10:
                                return False, (
                                    "%s: only %d sample(s) were collected across the held "
                                    "press (window %.1fms) — at least 10 are required, or this "
                                    "is a third endpoint rather than a sampling"
                                    % (theme, len(samples), window_ms))
                            if window_ms < 400:
                                return False, (
                                    "%s: the sampling window only covered %.1fms; the measured "
                                    "collapse completes by 90-150ms and the recovery lands "
                                    "~200ms after release, so a window under 400ms would "
                                    "reproduce the exact blind spot this check exists to close"
                                    % (theme, window_ms))
                            if not radius or radius <= 0:
                                return False, (
                                    "%s: --quiet-dial-radius resolved to %r on .quiet-dial — "
                                    "the ring radius must be read from rendered geometry, and "
                                    "an empty/zero value means it could not be"
                                    % (theme, sampled["radiusRaw"]))
                            tolerance = 4.0
                            worst_index, worst = max(
                                enumerate(samples),
                                key=lambda pair: abs(pair[1]["dist"] - radius))
                            if abs(worst["dist"] - radius) > tolerance:
                                return False, (
                                    "%s: sample #%d (of %d, at %.1fms into the press) resolved "
                                    "%.2fpx from the dial's centre; the ring radius is %.2fpx "
                                    "and the stated tolerance is %.2fpx — the handle left its "
                                    "ring DURING the press, which is exactly the collapse "
                                    "toward the centre the pre-fix stylesheet produced"
                                    % (theme, worst_index, len(samples), worst["t"],
                                       worst["dist"], radius, tolerance))
                            recorded["%s/worst" % theme] = (
                                worst_index, worst["dist"], radius)

                            if after_value != before_value:
                                return False, (
                                    "%s: a plain press-and-hold with no drag changed "
                                    "quiet_hours_start from %r to %r — a press is not a drag, "
                                    "and this control must not move the value it did not "
                                    "steer anywhere" % (theme, before_value, after_value))

                            if abs(released - radius) > tolerance:
                                return False, (
                                    "%s: %.2fpx after release; the ring radius is %.2fpx and "
                                    "the tolerance is %.2fpx — even the recovery state, the ONE "
                                    "state the pre-fix code already got right, regressed"
                                    % (theme, released, radius, tolerance))
                            recorded["%s/released" % theme] = released

                        _set_window(page, base_url, before_on_disk[0], before_on_disk[1])
                        if _quiet_hours_on_disk() != before_on_disk:
                            return False, (
                                "this check left the window at %r; it started at %r"
                                % (_quiet_hours_on_disk(), before_on_disk))
                        _ = recorded
                        return True, ""
                    finally:
                        try:
                            _set_window(page, base_url, before_on_disk[0], before_on_disk[1])
                        except Exception:
                            pass
                        context.close()
                check(
                    "THE handle-stays-on-its-ring check (CFG-73 Bug B, 28-02-PLAN.md Task 2): "
                    "holding the quiet-hours start handle down with no drag samples its "
                    "resolved distance from the dial's own centre at least 10 times across at "
                    "least 400ms — long enough to cover the measured 90-150ms collapse — and "
                    "asserts EVERY sample stays within a stated tolerance of the dial's own "
                    "--quiet-dial-radius (read from rendered geometry, never hardcoded), naming "
                    "the worst sample's distance and index on failure; the control's reported "
                    "value is asserted IDENTICAL before mouse.down() and after mouse.up() (a "
                    "press is not a drag); a final post-release sample is asserted on the ring "
                    "too, with the source recording that this is the ONE state the pre-fix "
                    "code already got right and therefore not sufficient alone; and the whole "
                    "check runs in BOTH themes at the 360px floor",
                    _the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press)

                # ----------------------------------------------------------
                # 25-05-PLAN.md Task 3 (CFG-49/CFG-52): D18's wake-interval
                # slider, measured at 360px, from the keyboard, and with
                # its fallback proven by SAVING rather than by rendering.
                #
                # None of the three checks below asserts that the slider
                # renders. The verdicts are: what reaches DISK with
                # scripts blocked, what a drag and a keystroke do to the
                # native number input and to the save bar, what the
                # battery gauge refuses to say at any drag position, and
                # what the browser's own hit test and cascade answer at
                # 360px in both themes.
                #
                # A DOM read would prove nothing here in particular: this
                # card ECHOES a rejected submission back into its own
                # field by design (D-07), so "the reloaded page shows the
                # value" passes against a save that stored nothing. That
                # is the exact case 25-02's helper was built for.
                # ----------------------------------------------------------

                WAKE_SLIDER_SEL = ".wake-slider"
                WAKE_RANGE_SEL = ".wake-slider__input"
                WAKE_NUMBER_SEL = 'input[name="wake_interval_s"]'
                WAKE_FRESHNESS_SEL = "#" + config_page.WAKE_GAUGE_FRESHNESS_ID
                WAKE_BATTERY_SEL = "#" + config_page.WAKE_GAUGE_BATTERY_ID

                def _wake_interval_on_disk():
                    config = device_config.load_device_config(harness.tmpdir)
                    return config.get("wake_interval_s")

                def _gauge_texts(page):
                    return (page.locator(WAKE_FRESHNESS_SEL).inner_text(),
                            page.locator(WAKE_BATTERY_SEL).inner_text())

                # Set the interval through the real UI and save, so every
                # arrangement measured below is reached the way a visitor
                # reaches it. Raises on failure.
                def _set_interval(page, base_url, seconds):
                    # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED from
                    # auto-save onto the restored bar — commits reveal the
                    # bar; only a click on its own Save persists. MEASURED,
                    # not assumed: Playwright's own .fill() dispatches
                    # `input` only (its documented contract), never
                    # `change` — the trigger the bar's own document-level
                    # listener needs — so _commit_field() fires the real
                    # event a blur would.
                    #
                    # IDEMPOTENT, still not a mere convenience: "set it to
                    # what it already is" fires no `change` at all (the
                    # value never differs), so the bar never reveals and
                    # _wait_for_bar() below would time out waiting for a
                    # reveal that correctly never comes.
                    page.goto(base_url + "/device")
                    if _wake_interval_on_disk() == seconds:
                        return
                    page.fill(WAKE_NUMBER_SEL, str(seconds))
                    _commit_field(page, WAKE_NUMBER_SEL)
                    _wait_for_bar(page)
                    _save_via_bar(page)
                    stored = _wake_interval_on_disk()
                    if stored != seconds:
                        raise AssertionError(
                            "setting the interval to %r through the UI stored %r"
                            % (seconds, stored))
                    page.goto(base_url + "/device")

                # A days figure in EITHER shipped language, which is what
                # the battery gauge may not print unless this frame's own
                # observed history supports one.
                _DAYS_FIGURE_RE = re.compile(r"\d+\s*(?:day|jour)", re.I)

                def _the_interval_still_saves_with_scripts_blocked_through_the_slider():
                    base_url = harness.base_url()
                    before = _wake_interval_on_disk()
                    recorded = {}

                    # 1. IT STILL REACHES DISK WITH SCRIPTS BLOCKED, at
                    #    360px and in BOTH shipped languages. The gauges
                    #    are asserted present only AFTER the save, so
                    #    they can never stand in for it.
                    saved = {}
                    for lang in ("en", "fr"):
                        cookies = [{"name": auth.UI_LANG_COOKIE_NAME,
                                    "value": lang, "url": base_url}]
                        saved[lang] = _persist_without_js(
                            browser, base_url, "/device", "wake_interval_s",
                            "900", _wake_interval_on_disk,
                            viewport=VIEWPORT_MIN_SUPPORTED, cookies=cookies)
                    recorded["persisted"] = {
                        lang: (r["set"], r["stored"], r["reloaded"])
                        for lang, r in saved.items()}
                    for lang, result in saved.items():
                        if str(result["stored"]) != str(result["set"]):
                            return False, (
                                "%s: the typed interval did not reach disk, it reads %r"
                                % (lang, result["stored"]))
                    if _wake_interval_on_disk() != before:
                        return False, (
                            "the scripts-blocked saves left the interval at %r; it started at "
                            "%r — a harness that changes a real setting is a test that edits "
                            "its neighbours' subject" % (_wake_interval_on_disk(), before))

                    # 2. THE GATE, IN BOTH DIRECTIONS. Asserting only the
                    #    blocked half passes against a gate stuck shut;
                    #    asserting only the enabled half is the "renders
                    #    and does nothing" defect.
                    gate = _assert_js_gate(
                        browser, base_url, "/device", WAKE_SLIDER_SEL,
                        viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded["gate"] = gate

                    # 3. AND BOTH GAUGES ARE THERE WITHOUT A SCRIPT —
                    #    which is what makes this card's fallback a
                    #    feature rather than an absence. MEASURED, not
                    #    counted: locator.count() counts elements
                    #    whatever their box is, so it passes against a
                    #    gauge moved behind the gate, which is the exact
                    #    refactor this clause exists to notice.
                    with _no_js_page(browser, base_url, "/device",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        boxes = {}
                        texts = {}
                        for name, sel in (("freshness", WAKE_FRESHNESS_SEL),
                                          ("battery", WAKE_BATTERY_SEL)):
                            locator = page.locator(sel)
                            boxes[name] = locator.bounding_box() if locator.count() else None
                            texts[name] = locator.inner_text() if locator.count() else None
                        blocked_number = page.locator(WAKE_NUMBER_SEL).count()
                        blocked_unit = page.locator(".field-inline-value").count()
                        blocked_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
                    recorded["blocked_boxes"] = boxes
                    recorded["blocked_texts"] = texts
                    for name in ("freshness", "battery"):
                        box = boxes[name]
                        if not box or box["width"] <= 0 or box["height"] <= 0:
                            return False, (
                                "the %s gauge occupies no space with scripts blocked (%r) — "
                                "rendered is not read, and a gauge behind the gate is the "
                                "refactor this clause exists to notice" % (name, box))
                    if blocked_number != 1 or blocked_unit < 1:
                        return False, (
                            "with scripts blocked the card renders %d number input(s) and %d "
                            "unit sibling(s); it owes one of each"
                            % (blocked_number, blocked_unit))
                    if str(blocked_value) != str(before):
                        return False, (
                            "with scripts blocked the number input shows %r, not the saved %r"
                            % (blocked_value, before))
                    if "at most" not in texts["freshness"] and "au plus" not in texts["freshness"]:
                        return False, (
                            "the scripts-blocked freshness gauge reads %r — the bound has to be "
                            "legible without a script" % texts["freshness"])

                    # 4. THE OUT-OF-RANGE TRAP, END TO END, and it is the
                    #    one defect on this card that takes down the
                    #    WHOLE page rather than one field: an
                    #    out-of-range `value` on a native numeric input
                    #    fails HTML5 constraint validation, which blocks
                    #    submission of the entire Settings form. A slider
                    #    added beside that input is exactly the change
                    #    that could reintroduce a fabricated value.
                    #
                    #    The below-floor state is written to the config
                    #    file DIRECTLY — the only direct state write in
                    #    this check, and it is unavoidable rather than a
                    #    shortcut: save_device_config() raises on 30
                    #    ("must be an int in [60, 3600]"), so the UI
                    #    cannot produce the state this clause is about.
                    #    The file's exact previous bytes are restored.
                    config_path = device_config.device_config_path(harness.tmpdir)
                    with open(config_path, encoding="utf-8") as fh:
                        original_bytes = fh.read()
                    try:
                        doc = json.loads(original_bytes)
                        doc["wake_interval_s"] = 30
                        with open(config_path, "w", encoding="utf-8") as fh:
                            json.dump(doc, fh)
                        with _no_js_page(browser, base_url, "/device",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            below_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
                            below_ranges = page.locator(WAKE_RANGE_SEL).count()
                            below_gauges = page.locator(WAKE_FRESHNESS_SEL).count()
                        recorded["below_floor"] = (below_value, below_ranges, below_gauges)
                        if below_value is not None:
                            return False, (
                                "with 30 s stored the number input carries value=%r — an "
                                "out-of-range value fails HTML5 constraint validation and "
                                "blocks submission of the ENTIRE Settings form" % below_value)
                        if below_ranges or below_gauges:
                            return False, (
                                "with 30 s stored the card rendered %d range(s) and %d gauge(s) "
                                "— a range with no usable value sits at the midpoint of its own "
                                "band, which is a number nobody chose"
                                % (below_ranges, below_gauges))
                        # AND THE WHOLE FORM STILL SUBMITS. This is the
                        # half that matters: the page is still usable
                        # with a below-floor value on disk.
                        corrected = _persist_without_js(
                            browser, base_url, "/device", "wake_interval_s", "1200",
                            _wake_interval_on_disk, viewport=VIEWPORT_MIN_SUPPORTED,
                            restore=False)
                        recorded["corrected"] = (corrected["set"], corrected["stored"])
                        if str(corrected["stored"]) != "1200":
                            return False, (
                                "with a below-floor value on disk the Settings form did not "
                                "save a corrected one; disk reads %r" % (corrected["stored"],))
                    finally:
                        with open(config_path, "w", encoding="utf-8") as fh:
                            fh.write(original_bytes)
                    if _wake_interval_on_disk() != before:
                        return False, (
                            "this check left the interval at %r; it started at %r"
                            % (_wake_interval_on_disk(), before))
                    _ = recorded
                    return True, ""
                check(
                    "the wake interval still SAVES with scripts blocked beside the slider — "
                    "typed natively, submitted through the real form, re-read FROM DISK after a "
                    "fresh GET and restored the same way, at 360px and in BOTH shipped "
                    "languages; the gated range has zero height and no keyboard can reach into "
                    "it with scripts blocked while it occupies space with them; both gauges are "
                    "MEASURED (not counted) present on the scripts-blocked page, asserted after "
                    "the save so neither can stand in for it; and the out-of-range trap is "
                    "re-proven end to end — with 30 s on disk the number input carries NO value "
                    "attribute, no range and no gauge render at all, and the whole Settings "
                    "form still saves a corrected value (D-09/CFG-49/T-25-05-B, 25-05-PLAN.md "
                    "Task 3)",
                    _the_interval_still_saves_with_scripts_blocked_through_the_slider)

                def _dragging_and_keying_the_range_reach_disk():
                    base_url = harness.base_url()
                    before = _wake_interval_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    page = None
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        _set_interval(page, base_url, 600)
                        started = _gauge_texts(page)
                        recorded["at_600"] = started

                        # 1. THE DRAG. Aimed at a point well along the
                        #    track rather than at a value computed from
                        #    the thumb geometry: a native range maps its
                        #    value across (width - thumbWidth), which is
                        #    an engine detail this check has no business
                        #    predicting. What it asserts is what the plan
                        #    asks — that the number input and BOTH gauge
                        #    sentences moved together, and that what the
                        #    script rendered is what the SERVER would
                        #    have rendered for the same value.
                        #
                        #    Scrolled to the middle of the viewport
                        #    first, for _hit_area()'s own recorded
                        #    reason: at 360px this page is long and its
                        #    tab bar is fixed to the bottom, so a
                        #    coordinate gesture taken wherever the page
                        #    happened to be scrolled lands somewhere
                        #    else.
                        page.eval_on_selector(
                            WAKE_SLIDER_SEL, "el => el.scrollIntoView({block: 'center'})")
                        box = page.evaluate(
                            "sel => { const r = document.querySelector(sel)"
                            "  .getBoundingClientRect();"
                            "  return [r.left, r.top, r.width, r.height]; }", WAKE_RANGE_SEL)
                        page.mouse.move(box[0] + box[2] * 0.25, box[1] + box[3] / 2)
                        page.mouse.down()
                        page.mouse.move(box[0] + box[2] * 0.8, box[1] + box[3] / 2, steps=8)
                        page.mouse.up()
                        dragged = page.input_value(WAKE_NUMBER_SEL)
                        recorded["dragged_to"] = dragged
                        if dragged == str(600):
                            return False, (
                                "dragging the range across %.0fpx of its own track left the "
                                "number input at %r — the range steers the control that already "
                                "existed, or it steers nothing" % (box[2] * 0.55, dragged))
                        dragged_s = int(dragged)
                        if dragged_s % config_page.WAKE_SLIDER_STEP_S:
                            return False, (
                                "a drag produced %r, which is not a whole number of the stated "
                                "%d-second steps" % (dragged, config_page.WAKE_SLIDER_STEP_S))
                        moved = _gauge_texts(page)
                        recorded["after_drag"] = moved
                        if moved[0] == started[0]:
                            return False, (
                                "the freshness gauge still reads %r after the value moved from "
                                "600 to %s — a gauge that does not move is a gauge that is "
                                "wrong from the first drag" % (moved[0], dragged))
                        if moved[1] == started[1]:
                            return False, (
                                "the battery gauge still reads %r after the value moved from "
                                "600 to %s" % (moved[1], dragged))
                        # WHAT THE SCRIPT SAYS IS WHAT THE SERVER WOULD
                        # HAVE SAID. The relative clause has exactly one
                        # definition in Python, and this is what makes
                        # "the script carries no copy of its own" a
                        # measurement rather than a claim.
                        expected_clause = config_page.wake_battery_relative_text(dragged_s, 600)
                        recorded["expected_clause"] = expected_clause
                        if not expected_clause or expected_clause not in moved[1]:
                            return False, (
                                "the battery gauge reads %r; the server's own wording for the "
                                "same two cadences is %r" % (moved[1], expected_clause))
                        expected_bound = config_page.wake_freshness_text(dragged_s)
                        if moved[0] != expected_bound:
                            return False, (
                                "the freshness gauge reads %r; the server's own wording for %s "
                                "seconds is %r" % (moved[0], dragged, expected_bound))
                        # THE HONESTY CLAUSE, IN THE BROWSER. This
                        # fixture's battery series is RISING (the device
                        # was charged), so companion/battery.py refuses a
                        # figure — and no drag position may produce one.
                        if _DAYS_FIGURE_RE.search(moved[1]):
                            return False, (
                                "the battery gauge produced a days figure (%r) from a rising "
                                "series — the per-wake energy cost has never been measured and "
                                "the script has no template that could state one" % moved[1])
                        # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED
                        # — see the identical comment on the quiet-hours
                        # dial's own drag check: value-controls.js's
                        # notify() is the same real `change` event the
                        # bar's own document-level listener reacts to, so
                        # the drag REVEALING the bar is still the proof
                        # the event fired; the edit only reaches disk once
                        # Enregistrer is clicked.
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        recorded["dragged_stored"] = _wake_interval_on_disk()
                        if recorded["dragged_stored"] != dragged_s:
                            return False, (
                                "the dragged value did not reach disk; it reads %r"
                                % (recorded["dragged_stored"],))
                        page.goto(base_url + "/device")
                        if page.input_value(WAKE_NUMBER_SEL) != dragged:
                            return False, "the reloaded page does not show the dragged value"

                        # 2. THE KEYBOARD ALONE, with the pointer-free
                        #    claim MEASURED rather than promised. One
                        #    ArrowRight is one stated step — and the
                        #    model is the one 25-04's dial recorded,
                        #    inherited rather than re-decided.
                        _set_interval(page, base_url, 600)
                        keyed = _operate_with_keyboard(
                            page, WAKE_RANGE_SEL, ["ArrowRight"])
                        after_key = page.input_value(WAKE_NUMBER_SEL)
                        recorded["after_arrow"] = after_key
                        if int(after_key) != 600 + config_page.WAKE_SLIDER_STEP_S:
                            return False, (
                                "one ArrowRight moved the interval from 600 to %r; the stated "
                                "step is %d seconds"
                                % (after_key, config_page.WAKE_SLIDER_STEP_S))
                        if keyed["pointer_events"]:
                            return False, (
                                "a pointer event fired during the keyboard sequence: %r"
                                % (keyed["pointer_events"],))
                        if not keyed["recorder_proved"]:
                            return False, "the pointer recorder could not prove itself"
                        # HOME AND END REACH THE CONFIGURED BAND'S OWN
                        # ENDS — the floor as well as the ceiling.
                        page.keyboard.press("End")
                        recorded["after_end"] = page.input_value(WAKE_NUMBER_SEL)
                        if int(recorded["after_end"]) != device_config.WAKE_INTERVAL_MAX_S:
                            return False, (
                                "End put %r into the field; the band's ceiling is %d"
                                % (recorded["after_end"], device_config.WAKE_INTERVAL_MAX_S))
                        recorded["at_max"] = _gauge_texts(page)
                        page.keyboard.press("Home")
                        recorded["after_home"] = page.input_value(WAKE_NUMBER_SEL)
                        if int(recorded["after_home"]) != device_config.WAKE_INTERVAL_MIN_S:
                            return False, (
                                "Home put %r into the field; the band's floor is %d"
                                % (recorded["after_home"], device_config.WAKE_INTERVAL_MIN_S))
                        recorded["at_min"] = _gauge_texts(page)
                        # THE FLOOR AND THE CEILING BOTH READ TRUE, and
                        # neither produces a days figure.
                        for where, texts, seconds in (
                                ("the band's floor", recorded["at_min"],
                                 device_config.WAKE_INTERVAL_MIN_S),
                                ("the band's ceiling", recorded["at_max"],
                                 device_config.WAKE_INTERVAL_MAX_S)):
                            if texts[0] != config_page.wake_freshness_text(seconds):
                                return False, (
                                    "at %s the freshness gauge reads %r, not the server's own "
                                    "%r" % (where, texts[0],
                                            config_page.wake_freshness_text(seconds)))
                            if _DAYS_FIGURE_RE.search(texts[1]):
                                return False, (
                                    "at %s the battery gauge produced a days figure: %r"
                                    % (where, texts[1]))

                        # 3. TYPING IN THE NUMBER INPUT MOVES THE RANGE,
                        #    which is the direction a repaint has to
                        #    cover and the one a drag test is blind to.
                        _set_interval(page, base_url, 600)
                        page.fill(WAKE_NUMBER_SEL, "1800")
                        page.eval_on_selector(
                            WAKE_NUMBER_SEL,
                            "el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                        recorded["range_after_typing"] = page.input_value(WAKE_RANGE_SEL)
                        if recorded["range_after_typing"] != "1800":
                            return False, (
                                "typing 1800 into the number input left the range at %r — the "
                                "slider would then show a value that is no longer there while "
                                "the field beside it shows the real one"
                                % (recorded["range_after_typing"],))
                        # RESTORED THROUGH THE SAME UI SEQUENCE, never a
                        # direct write to the state directory.
                        _set_interval(page, base_url, before)
                        if _wake_interval_on_disk() != before:
                            return False, (
                                "this check left the interval at %r; it started at %r"
                                % (_wake_interval_on_disk(), before))
                        _ = recorded
                        return True, ""
                    finally:
                        # Best effort only, and deliberately silent: a
                        # restore that raised here would mask the failure
                        # it is cleaning up after.
                        try:
                            _set_interval(page, base_url, before)
                        except Exception:
                            pass
                        context.close()
                check(
                    "dragging the wake-interval range moves the native <input type=\"number\"> "
                    "the form posts, moves BOTH gauge sentences with it, REVEALS the bar and "
                    "PERSISTS to disk once Enregistrer is clicked — with the script's own "
                    "wording asserted EQUAL to the server's for the same two cadences, so the "
                    "script provably carries no copy of its own; one ArrowRight moves exactly "
                    "one stated step and End/Home reach device_config's own ceiling and floor "
                    "with zero pointer events fired and the recorder proving itself; typing into "
                    "the number input moves the range back; and at no position — dragged, keyed, "
                    "at the floor or at the ceiling — does the battery gauge produce a days "
                    "figure from this fixture's RISING series (CFG-49/CFG-52/T-25-05-C, "
                    "25-05-PLAN.md Task 3; retargeted from the retired auto-save onto the "
                    "restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78)",
                    _dragging_and_keying_the_range_reach_disk)

                def _the_slider_meets_its_floors_at_360px_in_both_themes():
                    base_url = harness.base_url()
                    before = _wake_interval_on_disk()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        page.goto(base_url + "/device")

                        # 1. THE HIT TARGET, IN THIS CONTROL'S OWN
                        #    CONTAINER. A class-level measurement is
                        #    worth nothing: 25-02 measured `.copy-btn`'s
                        #    declared 44x44 at a real 34x26 because its
                        #    neighbours covered the ::before that
                        #    synthesises it.
                        recorded["hit"] = _assert_hit_target(
                            page, WAKE_RANGE_SEL, "the wake-interval slider on /device")

                        # 2. THE GEOMETRY, by getBoundingClientRect and
                        #    never clientWidth — which rounds to an
                        #    integer and can fail a correct drawing
                        #    (54.41 in a "53.00" box).
                        measured = page.evaluate(
                            "sels => {"
                            "  const el = document.querySelector(sels.range);"
                            "  const card = el.closest('.theme-status');"
                            "  const r = el.getBoundingClientRect();"
                            "  const c = card.getBoundingClientRect();"
                            "  const wrap = document.querySelector(sels.wrap);"
                            "  const cs = getComputedStyle(wrap);"
                            "  const cc = getComputedStyle(card);"
                            "  const content = card.clientWidth"
                            "    - parseFloat(cc.paddingLeft) - parseFloat(cc.paddingRight);"
                            "  return {range: [r.width, r.height], card: [c.width, c.height],"
                            "          content: content, marginTop: cs.marginTop,"
                            "          number: document.querySelector(sels.number)"
                            "                    .getBoundingClientRect().width};"
                            "}", {"range": WAKE_RANGE_SEL, "wrap": WAKE_SLIDER_SEL,
                                  "number": WAKE_NUMBER_SEL})
                        recorded["measured"] = measured
                        # COMPARED AGAINST THE CARD'S CONTENT BOX, NOT
                        # AGAINST THE NUMBER INPUT BESIDE IT. The first
                        # version asked only that the range was wider
                        # than the 96px number field — which a range
                        # with NO width rule passes, because its
                        # intrinsic width is about 129px. Measured:
                        # `width: auto` failed nothing at all. The
                        # property under test is "full width", so full
                        # width is what is measured.
                        if measured["range"][0] < measured["content"] - 1:
                            return False, (
                                "the range measures %.2fpx inside a %.2fpx content box (the "
                                "number input beside it is %.2fpx) — a range input's intrinsic "
                                "width is about 129px, and at the 360px floor that is a sweep "
                                "of the whole 60..3600 band in a third of the card"
                                % (measured["range"][0], measured["content"],
                                   measured["number"]))
                        if measured["range"][0] <= measured["number"]:
                            return False, (
                                "the range (%.2fpx) is no wider than the number input it steers "
                                "(%.2fpx)" % (measured["range"][0], measured["number"]))
                        if measured["range"][0] > measured["card"][0]:
                            return False, (
                                "the range (%.2fpx) is wider than the card holding it (%.2fpx)"
                                % (measured["range"][0], measured["card"][0]))
                        if not measured["marginTop"].endswith("px") or float(
                                measured["marginTop"][:-2]) <= 0:
                            return False, (
                                "the slider's wrapper computes margin-top %r — without it the "
                                "range sits flush against the number input's own row"
                                % measured["marginTop"])
                        width_at_360 = page.evaluate(
                            "() => [document.body.scrollWidth, document.body.clientWidth,"
                            "       document.documentElement.scrollWidth,"
                            "       document.documentElement.clientWidth]")
                        recorded["page_width"] = width_at_360
                        if width_at_360[0] > width_at_360[1] or width_at_360[2] > width_at_360[3]:
                            return False, (
                                "the Device page scrolls sideways at 360px: %r — a full-width "
                                "control is the most likely cause and this is its own page's "
                                "baseline, not the Display page's" % (width_at_360,))

                        # 3. THE PAINT, IN BOTH THEMES, AND AS A FLOOR
                        #    RATHER THAN A CEILING. A gauge is only a
                        #    gauge if it can be read: both sentences and
                        #    the control's own accent have to change with
                        #    the theme, or one of the two modes is
                        #    showing ink on ink.
                        # THE THEME SWITCH STARTS A TRANSITION, AND THE
                        # READ HAS TO WAIT FOR THE BROWSER'S OWN "it has
                        # finished" SIGNAL RATHER THAN A GUESSED INSTANT.
                        # The global `input, select` rule declares
                        # `transition: background-color .15s ease`, so a
                        # getComputedStyle taken straight after the
                        # attribute flip reads an INTERPOLATION FRAME —
                        # measured here: the range's surface reported the
                        # LIGHT value in both themes and this check
                        # failed, claiming a token that does not invert
                        # when it does. 25-03 lost a paint measurement to
                        # exactly this and fixed it the same way. Never a
                        # timer: an element with nothing running returns
                        # an empty list and resolves at once.
                        _SETTLE_SLIDER = (
                            "async () => {"
                            "  const els = [...document.querySelectorAll("
                            "    '.wake-slider, .wake-slider *, .wake-gauge, body')];"
                            "  await Promise.all(els.flatMap("
                            "    e => e.getAnimations().map("
                            "      a => a.finished.catch(() => {}))));"
                            "  return els.length;"
                            "}")
                        paints = {}
                        for theme in UI_THEMES_EXPLICIT:
                            _set_ui_theme(page, theme)
                            recorded["settled_" + theme] = page.evaluate(_SETTLE_SLIDER)
                            paints[theme] = page.evaluate(
                                "sels => {"
                                "  const read = (s, p) =>"
                                "    getComputedStyle(document.querySelector(s))"
                                "      .getPropertyValue(p).trim();"
                                "  return {freshness: read(sels.freshness, 'color'),"
                                "          battery: read(sels.battery, 'color'),"
                                "          accent: read(sels.range, 'accent-color'),"
                                "          surface: read(sels.range, 'background-color'),"
                                "          canvas: getComputedStyle(document.body)"
                                "            .backgroundColor};"
                                "}", {"freshness": WAKE_FRESHNESS_SEL,
                                      "battery": WAKE_BATTERY_SEL,
                                      "range": WAKE_RANGE_SEL})
                        recorded["paints"] = paints
                        light, dark = paints["light"], paints["dark"]
                        for key in ("freshness", "battery", "accent", "surface"):
                            if light[key] == dark[key]:
                                return False, (
                                    "the slider card's %s paints identically in both themes "
                                    "(%r) — a token that does not invert is a literal, and one "
                                    "of the two modes is wrong" % (key, light[key]))
                        for theme, sampled in paints.items():
                            for key in ("freshness", "battery"):
                                if sampled[key] == sampled["canvas"]:
                                    return False, (
                                        "%s: the %s gauge's text is the canvas colour (%r) — it "
                                        "is not legible at all" % (theme, key, sampled[key]))
                        _set_ui_theme(page, "light")
                        if _wake_interval_on_disk() != before:
                            return False, (
                                "this check changed the stored interval (%r, started at %r)"
                                % (_wake_interval_on_disk(), before))
                        _ = recorded
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the wake-interval slider meets its floors at 360px — its hit area clears "
                    "the 44px target by real hit-testing in ITS OWN container (never inherited "
                    "from a class), it measures wider than the number input it steers and no "
                    "wider than the card holding it by getBoundingClientRect rather than "
                    "clientWidth, its wrapper keeps a real top margin off the field's own row, "
                    "the Device page does not scroll sideways at that width (its own baseline, "
                    "not the Display page's), and the paint is a FLOOR not a ceiling: both gauge "
                    "sentences and the control's own accent and surface all differ between the "
                    "two themes and neither sentence is painted in the canvas colour "
                    "(CFG-49/CFG-52, 25-05-PLAN.md Task 3)",
                    _the_slider_meets_its_floors_at_360px_in_both_themes)

            finally:
                browser.close()
    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("browser-ux-quiet-wake: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
