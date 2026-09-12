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
`EXPECTED_CHECK_COUNT`, and a `main()` returning 0 or 1 — so
`scripts/run_all_tests.py` needs zero special-casing for this file.

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
itself launched via `companion.test_companion_app.Harness`. No external
URL is ever constructed or navigated to anywhere in this file.

Reuses `companion.test_companion_app.Harness` for the subprocess-under-
test rather than inventing a second subprocess pattern (22-RESEARCH.md
Pattern 3): free port via `socket.bind(("127.0.0.1", 0))`, an isolated
`tempfile.mkdtemp()` state directory, a real `companion/app.py`
subprocess, a startup readiness poll, and a `stop()` that `terminate()`s
then `kill()`s.

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
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion.test_companion_app import Harness, TEST_PASSWORD  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import colour_rules, manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

EXPECTED_CHECK_COUNT = 5  # 22-01-PLAN.md Task 1: one check (the Flights
# detail row), proving the harness itself (subprocess, seed, real
# browser, real selectors) against a behaviour that already works today.
# 22-01-PLAN.md Task 3: +4 (Display reveal/persist across all four
# form=-attached field kinds, the identical Device round trip, the
# fallback-Save-stays-reachable-until-proven-live contract, and Cancel/
# T1/T8 together). 1 + 4 = 5, recomputed directly against the real
# on-disk check(...) call count at execution time (5/5 pass), not
# trusted from arithmetic alone.

# Fixed, deterministic — never datetime.now(). 06:00 UTC so the 17h runway
# window (06:00-23:00) and a 23:00-07:00 quiet-hours window share no
# overlap with each other by construction, keeping the two concerns
# independent in the seeded fixture.
SEED_BASE_TS = datetime(2026, 8, 1, 6, 0, 0, tzinfo=timezone.utc)


def seed_state_dir(state_dir, base_ts=SEED_BASE_TS):
    """Write 22-AUDIT.md's own methodology fixture into a fresh temp
    state directory, through the same modules companion/app.py and
    server/poll_loop.py use to write this data themselves — see this
    file's own module docstring for the full rationale and the one
    deliberate deviation (battery cadence).
    """
    runway_ids = device_config.RUNWAY_IDS
    theme_ids = device_config.THEME_IDS

    with history_db.open_db(state_dir) as conn:
        # 36 runway events over 17h.
        step = timedelta(hours=17) / 36
        for i in range(36):
            ts = base_ts + step * i
            history_db.record_runway_event(
                conn,
                ts=ts.isoformat(),
                hex="39%04x" % (0x9000 + i),
                callsign="AFR%03d" % (100 + i),
                aircraft_type="A320",
                confirmed_state="confirmed",
                corroborated=(i % 3 != 0),
                route_source="adsb" if i % 2 == 0 else "schedule",
                airline="Air France",
                origin="LFPO",
                destination="LFPG",
                tracked_runway=runway_ids[i % len(runway_ids)],
            )

        # ~40 days of battery readings, one reading per day (see the
        # module docstring's cadence note).
        for day in range(40, 0, -1):
            ts = base_ts - timedelta(days=day)
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=4200 - day * 3,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")

    device_config.save_device_config(
        state_dir, theme=theme_ids[0], tracked_runway=runway_ids[0],
        wake_interval_s=300, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00",
        display_enabled=True,
    )

    now_iso = base_ts.isoformat()

    # 2 unresolved prefixes — same registry shape
    # companion/test_status_pages.py's own _seed_unresolved_prefixes()
    # helper writes, through the identical save_poll_state() call.
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": {
        "TVF": {
            "count": 5, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "TVF123",
        },
        "EZY": {
            "count": 2, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "EZY456",
        },
    }})

    # 1 manual resolution.
    manual_resolutions.add_entry(state_dir, "RYR", "Ryanair", now=now_iso)

    # 2 colour rules.
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_PREFIX, "AFR", theme_ids[0], now=now_iso)
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_CALLSIGN, "EZY456", theme_ids[-1], now=now_iso)

    # 3 gallery renders, archived through poll_loop's own writer — never a
    # hand-written PNG dropped straight into the gallery directory, so the
    # on-disk filename/format contract can never drift from what a real
    # poll cycle produces.
    from PIL import Image
    canvas = Image.new("RGB", (8, 8), "white")
    for i in range(3):
        render_ts = (base_ts + timedelta(minutes=i)).isoformat()
        poll_loop._save_to_gallery(state_dir, canvas, render_ts)


def _login(page, base_url):
    """Drive the real login form through the UI (never a bare HTTP POST —
    this file exists specifically to exercise the browser), and wait for
    the post-login redirect to land.
    """
    page.goto(base_url + "/login")
    page.fill("#password", TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def _click_control(page, selector):
    """Click a checkbox/radio input through the browser's own native
    .click() method (JS-level, not Playwright's mouse-coordinate click).

    Every checkbox/radio this file's checks click below is visually
    hidden (config_page.py's own selectable-card idiom: a
    visually-hidden native input wrapped in a full-card <label>), via
    `clip-path: inset(50%)` (companion/static/style.css's own
    .visually-hidden rule) — which clips the element's paintable AND
    hit-testable area to nothing. A coordinate-based click (Playwright's
    own `locator.click()`, even with `force=True`) dispatches at that
    point and can silently land on whatever the browser's hit-test
    resolves to there instead (confirmed live: it left the target
    control unchecked with no error). `element.click()` is the DOM's own
    "activation behaviour" algorithm — it runs regardless of paint/hit-
    test visibility and is what every real assistive-technology/keyboard
    activation path already relies on for this exact selectable-card
    pattern, so it is the correct thing to call here, not a workaround.
    """
    page.eval_on_selector(selector, "el => el.click()")


def _guard_armed(page):
    """T1: whether dirty-state.js's beforeunload guard is currently
    armed, tested by constructing a real, cancelable `beforeunload`
    Event object in-page and dispatching it directly on window, then
    reading `defaultPrevented` — never by trying to trigger an actual
    navigation and observe a native "leave site?" dialog, which
    Chromium suppresses/auto-resolves under Playwright and which
    Playwright's own `dialog` event does not reliably surface for
    beforeunload specifically. Dispatching the Event directly still
    exercises dirty-state.js's own real listener (the one registered via
    `window.addEventListener("beforeunload", ...)`) with no change to
    that file — this is a black-box behavioural probe, not an internal
    read of the private `suppressGuard` variable.
    """
    return page.evaluate(
        "() => { var e = new Event('beforeunload', {cancelable: true}); "
        "window.dispatchEvent(e); return e.defaultPrevented; }")


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
                def _flights_detail_row_expands_and_collapses():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/flights")
                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        if toggle.get_attribute("aria-expanded") != "false":
                            return False, "expected the first row-toggle to start collapsed (aria-expanded=false)"
                        controls_id = toggle.get_attribute("aria-controls")
                        if not controls_id:
                            return False, "expected the row-toggle to carry aria-controls"
                        detail_row = page.locator("#" + controls_id)
                        if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row to start collapsed"

                        toggle.click()
                        if toggle.get_attribute("aria-expanded") != "true":
                            return False, "expected aria-expanded to flip to true after a click"
                        if "flight-detail-row--collapsed" in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row's collapsed class to be removed after expanding"

                        toggle.click()
                        if toggle.get_attribute("aria-expanded") != "false":
                            return False, "expected aria-expanded to flip back to false after a second click"
                        if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row's collapsed class to return after collapsing"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Flights detail row expands and collapses, flipping aria-expanded and toggling the "
                    "row aria-controls resolves to",
                    _flights_detail_row_expands_and_collapses)

                # ----------------------------------------------------------------
                # 22-01-PLAN.md Task 3 (D-01/D-02, B1/T1/T8): the four checks
                # this whole plan exists to make possible.
                # ----------------------------------------------------------------

                def _display_reveal_and_persist_across_all_field_kinds():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        theme_ids = device_config.THEME_IDS
                        runway_ids = device_config.RUNWAY_IDS

                        # 1. Theme chip (Frame colours card, form=-attached,
                        # rendered as a sibling of <form id="settings-form">):
                        # reveal, name the section, submit, persist.
                        page.goto(base_url + "/display")
                        target_theme = theme_ids[1]
                        theme_sel = 'input[name="theme"][value="%s"]' % target_theme
                        _click_control(page, theme_sel)
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a theme chip click"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Frame colours" not in count_text:
                            return False, "expected the bar to name Frame colours, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if not page.eval_on_selector(theme_sel, "el => el.checked"):
                            return False, "expected the saved theme chip to be checked after reload"

                        # 2. Runway card (also a sibling of the form).
                        page.goto(base_url + "/display")
                        target_runway = runway_ids[1]
                        runway_sel = 'input[name="tracked_runway"][value="%s"]' % target_runway
                        _click_control(page, runway_sel)
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a runway card click"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Runway" not in count_text:
                            return False, "expected the bar to name Runway, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if not page.eval_on_selector(runway_sel, "el => el.checked"):
                            return False, "expected the saved runway card to be checked after reload"

                        # 3. Enable-display checkbox (a sibling of the form).
                        page.goto(base_url + "/display")
                        display_sel = 'input[name="display_enabled"]'
                        was_checked = page.eval_on_selector(display_sel, "el => el.checked")
                        _click_control(page, display_sel)
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after the Enable-display checkbox"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Screen on / off" not in count_text:
                            return False, "expected the bar to name Screen on / off, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        now_checked = page.eval_on_selector(display_sel, "el => el.checked")
                        if now_checked == was_checked:
                            return False, "expected the Enable-display checkbox to have flipped and persisted"

                        # 4. Quiet-hours time field (a sibling of the form).
                        page.goto(base_url + "/display")
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.fill(quiet_sel, "22:15")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a quiet-hours time edit"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Quiet hours" not in count_text:
                            return False, "expected the bar to name Quiet hours, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if page.eval_on_selector(quiet_sel, "el => el.value") != "22:15":
                            return False, "expected the saved quiet-hours start time to persist after reload"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Display: a theme chip, a runway card, the Enable-display checkbox and a quiet-hours "
                    "time field each reveal the save bar, name their own section, and persist on save "
                    "(B1, all four form=-attached field kinds)",
                    _display_reveal_and_persist_across_all_field_kinds)

                def _device_reveal_and_persist_stays_in_step_with_display():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/device")
                        led_sel = 'input[name="led_enabled"]'
                        was_checked = page.eval_on_selector(led_sel, "el => el.checked")
                        _click_control(page, led_sel)
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible on Device too"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Diagnostic LED" not in count_text:
                            return False, "expected the bar to name Diagnostic LED, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/device")
                        now_checked = page.eval_on_selector(led_sel, "el => el.checked")
                        if now_checked == was_checked:
                            return False, "expected the Diagnostic LED checkbox to have flipped and persisted"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Device: the same reveal-and-persist round trip proves the two scopes stay in step (B1)",
                    _device_reveal_and_persist_stays_in_step_with_display)

                def _fallback_save_reachable_until_bar_proven_live():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()

                        # With the bar never revealed, the fallback stays visible
                        # and submitting it saves (D-01: the fallback is the only
                        # write path a broken/blocked script leaves behind).
                        page.goto(base_url + "/display")
                        fallback = page.locator("[data-static-save-fallback]")
                        if not fallback.is_visible():
                            return False, "expected the fallback Save button to be visible before the bar is ever shown"
                        with page.expect_navigation():
                            fallback.click()
                        if "/display" not in page.url:
                            return False, "expected the fallback Save button to actually submit the form"

                        # Once the bar has been revealed once, the fallback hides.
                        page.goto(base_url + "/display")
                        fallback = page.locator("[data-static-save-fallback]")
                        if not fallback.is_visible():
                            return False, "expected the fallback Save button to still be visible before any edit on a fresh load"
                        theme_ids = device_config.THEME_IDS
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_ids[2])
                        if page.locator("[data-dirty-bar]").is_hidden():
                            return False, "expected the save bar to become visible after the edit"
                        if fallback.is_visible():
                            return False, "expected the fallback Save button to hide once the bar has genuinely been shown"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the fallback Save button stays reachable and functional until the bar has actually been "
                    "shown once, then hides (D-01: the no-way-to-save-at-all fix)",
                    _fallback_save_reachable_until_bar_proven_live)

                def _cancel_restores_preview_and_rearms_guard():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/display")
                        theme_ids = device_config.THEME_IDS
                        original_sel = 'input[name="theme"]:checked'
                        original_value = page.eval_on_selector(original_sel, "el => el.value")
                        original_src = page.locator(".theme-live-preview__image").get_attribute("src")

                        if _guard_armed(page):
                            return False, "expected the leave-guard to start disarmed on a clean page load"

                        other_theme = next(t for t in theme_ids if t != original_value)
                        _click_control(page, 'input[name="theme"][value="%s"]' % other_theme)
                        new_src = page.locator(".theme-live-preview__image").get_attribute("src")
                        if new_src == original_src:
                            return False, "expected the live preview to change immediately after the edit"
                        if not _guard_armed(page):
                            return False, "expected the leave-guard to be armed after a real edit"

                        page.locator("[data-dirty-cancel]").click()
                        # T8: Cancel restores both the form value AND the live
                        # preview - form.reset() alone only restores the former.
                        if not page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % original_value, "el => el.checked"):
                            return False, "expected Cancel to restore the original theme chip's checked state"
                        restored_src = page.locator(".theme-live-preview__image").get_attribute("src")
                        if restored_src != original_src:
                            return False, (
                                "expected Cancel to restore the live preview to its original src, got %r "
                                "(T8)" % (restored_src,))
                        if _guard_armed(page):
                            return False, "expected Cancel to disarm the leave-guard"

                        # T1: the NEXT edit re-arms the guard - it must not stay
                        # disarmed for the rest of the page's life after Cancel.
                        _click_control(page, 'input[name="theme"][value="%s"]' % other_theme)
                        if not _guard_armed(page):
                            return False, "expected a subsequent edit after Cancel to re-arm the leave-guard (T1)"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Cancel restores the form value AND the live theme preview (T8), and a subsequent edit "
                    "re-arms the leave-guard (T1)",
                    _cancel_restores_preview_and_rearms_guard)
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
