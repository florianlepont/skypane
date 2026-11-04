"""Browser checks for the quiet-hours window editor on Home and the wake-interval slider.

The quiet window is edited in the Home dialog (two native time fields, three presets, a
Save button): it saves with scripts blocked, a preset reaches disk, and every control keeps a
44px target at 360px in both themes. The wake-interval slider lives on the Device settings
page. Every check drives a real save, so each gets its own function-scoped
`make_app_server(seed=seed_state_dir, fake_providers=True)` server - sharing one server
across mutating tests would make xdist's distribution order-dependent.
"""
import json

import pytest

from companion import auth
from companion.pages import config_page
from server import device_config
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED, _assert_hit_target, _assert_js_gate,
    _commit_field, _in_both_themes, _login, _no_js_page, _operate_with_keyboard, _persist_without_js,
    _save_via_bar, _set_ui_theme, _wait_for_bar, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture
def server(make_app_server):
    """A fresh, function-scoped companion/app.py server for each check below: every one of
    them drives a real save, so no two of them may share a server."""
    return make_app_server(seed=seed_state_dir, fake_providers=True)


WINDOW_LINK = "a.home-switch__window"
DIALOG = "dialog#dlg-quiet-hours"
START = "#quiet-window-start"
END = "#quiet-window-end"
SAVE = DIALOG + " button[type=submit]"
PRESETS = DIALOG + " .quiet-preset-row button"
MIN_PX = 43.5

# Finite animations only: the live pulse never ends and must not hold the test.
_AT_REST = (
    "document.getAnimations().every((a) => a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")


def _quiet_hours_on_disk(state_dir):
    config = device_config.load_device_config(state_dir)
    return (config["quiet_hours_start"], config["quiet_hours_end"])


def _wait_at_rest(page, selector):
    """Wait until the document is complete, the finite animations ended and `selector` owns
    its own centre (right after a navigation a view transition answers with the root)."""
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        """sel => {
          if (!(%s)) return false;
          const e = document.querySelector(sel);
          if (!e) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!hit && (hit === e || e.contains(hit));
        }""" % _AT_REST, arg=selector, timeout=10000)


def _open_dialog(page, base_url):
    page.goto(base_url + "/")
    _wait_at_rest(page, WINDOW_LINK)
    page.click(WINDOW_LINK)
    page.wait_for_function(
        "() => { const d = document.querySelector('%s');"
        " return d.open && document.activeElement && document.activeElement.id === "
        "'quiet-window-start'; }" % DIALOG, timeout=10000)
    _wait_at_rest(page, START)


def _save_window(page, base_url, state_dir, start, end):
    """Set both ends in the dialog and save, then wait for the stored window."""
    _open_dialog(page, base_url)
    page.fill(START, start)
    page.fill(END, end)
    with page.expect_navigation():
        page.click(SAVE)
    assert _quiet_hours_on_disk(state_dir) == (start, end)


def test_the_quiet_window_saves_with_scripts_blocked_through_the_dialog(new_context, server):
    """The quiet window still saves with scripts blocked: both ends set natively in the
    dialog the schedule link opens, submitted through the real form, re-read from disk and
    restored the same way, at 360px and in both shipped languages."""
    base_url = server.base_url()
    before = _quiet_hours_on_disk(server.tmpdir)
    for lang in ("en", "fr"):
        cookies = [{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}]
        with _no_js_page(new_context, base_url, "/", viewport=VIEWPORT_MIN_SUPPORTED,
                         cookies=cookies, reduced_motion="reduce") as page:
            page.click(WINDOW_LINK)
            page.wait_for_selector(DIALOG + ":target", state="visible", timeout=10000)
            assert page.locator(START).count() == 1 and page.locator(PRESETS).count() == 3
            page.fill(START, "21:45")
            page.fill(END, "06:15")
            with page.expect_navigation():
                page.click(SAVE)
        assert _quiet_hours_on_disk(server.tmpdir) == ("21:45", "06:15"), lang
        with _no_js_page(new_context, base_url, "/", viewport=VIEWPORT_MIN_SUPPORTED,
                         cookies=cookies, reduced_motion="reduce") as page:
            page.click(WINDOW_LINK)
            page.wait_for_selector(DIALOG + ":target", state="visible", timeout=10000)
            page.fill(START, before[0])
            page.fill(END, before[1])
            with page.expect_navigation():
                page.click(SAVE)
        assert _quiet_hours_on_disk(server.tmpdir) == before, lang


def test_a_preset_reaches_disk_through_the_dialog(new_context, server):
    """A preset fills both fields (the night preset wraps through midnight) and the saved
    window reaches disk; the original window is restored afterwards."""
    base_url = server.base_url()
    before = _quiet_hours_on_disk(server.tmpdir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    page = context.new_page()
    try:
        _login(page, base_url)
        _save_window(page, base_url, server.tmpdir, "08:00", "18:00")
        _open_dialog(page, base_url)
        page.locator(PRESETS).nth(0).click()
        page.wait_for_function(
            "() => document.querySelector('%s').value === '23:00'"
            " && document.querySelector('%s').value === '07:00'" % (START, END), timeout=10000)
        with page.expect_navigation():
            page.click(SAVE)
        assert _quiet_hours_on_disk(server.tmpdir) == ("23:00", "07:00")
        _save_window(page, base_url, server.tmpdir, before[0], before[1])
    finally:
        context.close()


def test_the_dialog_controls_meet_their_floors_at_360px_in_both_themes(new_context, server):
    """Both time fields, the three presets and Save are at least 44px targets that own their
    centre, inside the viewport, in both themes at 360px."""
    base_url = server.base_url()
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    page = context.new_page()
    try:
        _login(page, base_url)
        _open_dialog(page, base_url)
        for _theme in _in_both_themes(page):
            _wait_at_rest(page, START)
            problems = page.evaluate(
                """args => args.selectors.map((sel) => {
                  const nodes = Array.from(document.querySelectorAll(sel));
                  if (!nodes.length) return [sel, 'missing'];
                  return nodes.map((el) => {
                    el.scrollIntoView({block: 'center'});
                    const r = el.getBoundingClientRect();
                    if (r.width < args.min || r.height < args.min) {
                      return [sel, 'size ' + r.width.toFixed(1) + 'x' + r.height.toFixed(1)];
                    }
                    if (r.left < 0 || r.right > document.documentElement.clientWidth) {
                      return [sel, 'outside the viewport'];
                    }
                    const hit = document.elementFromPoint(
                      r.left + r.width / 2, r.top + r.height / 2);
                    return hit && (el === hit || el.contains(hit)) ? null : [sel, 'covered'];
                  }).filter(Boolean);
                }).flat()""",
                {"selectors": [START, END, PRESETS, SAVE], "min": MIN_PX})
            assert problems == [], problems
    finally:
        context.close()


WAKE_SLIDER_SEL = ".wake-slider"
WAKE_RANGE_SEL = ".wake-slider__input"
WAKE_NUMBER_SEL = 'input[name="wake_interval_s"]'
WAKE_FRESHNESS_SEL = "#" + config_page.WAKE_GAUGE_FRESHNESS_ID
WAKE_BATTERY_SEL = "#" + config_page.WAKE_GAUGE_BATTERY_ID
WAKE_CAPTION_SEL = "#" + config_page.WAKE_INTERVAL_SECTION_CAPTION_ID


def _wake_interval_on_disk(state_dir):
    config = device_config.load_device_config(state_dir)
    return config.get("wake_interval_s")


def _assert_no_gauge_sentences(page):
    """The aircraft-delay and battery-history sentences are retired from the wake card."""
    present = page.locator("%s, %s" % (WAKE_FRESHNESS_SEL, WAKE_BATTERY_SEL)).count()
    if present:
        raise AssertionError(
            "the wake interval card rendered %d retired gauge sentence(s)" % present)


# Set the interval through the real UI and save, so every arrangement measured below is
# reached the way a visitor reaches it. Raises on failure.
def _set_interval(page, base_url, state_dir, seconds):
    # Commits reveal the bar; only a click on its own Save persists. Playwright's `.fill()`
    # dispatches `input` only, never `change` (the trigger the bar's document-level listener
    # needs), so `_commit_field()` fires the real event a blur would.
    #
    # Idempotent: "set it to what it already is" fires no `change` at all, so the bar never
    # reveals and _wait_for_bar() below would time out waiting for a reveal that correctly
    # never comes.
    page.goto(base_url + "/device")
    if _wake_interval_on_disk(state_dir) == seconds:
        return
    page.fill(WAKE_NUMBER_SEL, str(seconds))
    _commit_field(page, WAKE_NUMBER_SEL)
    _wait_for_bar(page)
    _save_via_bar(page)
    stored = _wake_interval_on_disk(state_dir)
    if stored != seconds:
        raise AssertionError(
            "setting the interval to %r through the UI stored %r"
            % (seconds, stored))
    page.goto(base_url + "/device")



def test_the_wake_interval_still_saves_with_scripts_blocked_through_the_slider(new_context, server):
    """The wake interval still saves with scripts blocked beside the slider: typed
    natively, submitted through the real form, re-read from disk after a fresh GET and
    restored the same way, at 360px and in both shipped languages; the gated range has
    zero height and no keyboard can reach into it with scripts blocked while it occupies
    space with them; the scripts-blocked page still renders exactly one number input with
    its unit and the saved value, asserted after the save so they cannot stand in for it;
    and the out-of-range trap is re-proven end to end: with 30 s on disk the number input
    carries no value attribute, no range renders at all, and the whole Settings form still
    saves a corrected value.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)
    recorded = {}

    def read_back():
        return _wake_interval_on_disk(server.tmpdir)

    # It still reaches disk with scripts blocked, at 360px and in both shipped languages.
    # The page's own controls are asserted only after the save, so they can never stand in for it.
    saved = {}
    for lang in ("en", "fr"):
        cookies = [{"name": auth.UI_LANG_COOKIE_NAME,
                    "value": lang, "url": base_url}]
        saved[lang] = _persist_without_js(
            new_context, base_url, "/device", "wake_interval_s",
            "900", read_back,
            viewport=VIEWPORT_MIN_SUPPORTED, cookies=cookies)
    recorded["persisted"] = {
        lang: (r["set"], r["stored"], r["reloaded"])
        for lang, r in saved.items()}
    for lang, result in saved.items():
        if str(result["stored"]) != str(result["set"]):
            raise AssertionError(
                "%s: the typed interval did not reach disk, it reads %r"
                % (lang, result["stored"]))
    if _wake_interval_on_disk(server.tmpdir) != before:
        raise AssertionError(
            "the scripts-blocked saves left the interval at %r; it started at "
            "%r — a harness that changes a real setting is a test that edits "
            "its neighbours' subject" % (_wake_interval_on_disk(server.tmpdir), before))

    # The gate, in both directions: asserting only the blocked half passes against a gate
    # stuck shut; asserting only the enabled half is the "renders and does nothing" defect.
    gate = _assert_js_gate(
        new_context, base_url, "/device", WAKE_SLIDER_SEL,
        viewport=VIEWPORT_MIN_SUPPORTED)
    recorded["gate"] = gate

    with _no_js_page(new_context, base_url, "/device",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        blocked_number = page.locator(WAKE_NUMBER_SEL).count()
        blocked_unit = page.locator(".field-inline-value").count()
        blocked_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
        _assert_no_gauge_sentences(page)
    if blocked_number != 1 or blocked_unit < 1:
        raise AssertionError(
            "with scripts blocked the card renders %d number input(s) and %d "
            "unit sibling(s); it owes one of each"
            % (blocked_number, blocked_unit))
    if str(blocked_value) != str(before):
        raise AssertionError(
            "with scripts blocked the number input shows %r, not the saved %r"
            % (blocked_value, before))
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
    config_path = device_config.device_config_path(server.tmpdir)
    with open(config_path, encoding="utf-8") as fh:
        original_bytes = fh.read()
    try:
        doc = json.loads(original_bytes)
        doc["wake_interval_s"] = 30
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        with _no_js_page(new_context, base_url, "/device",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            below_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
            below_ranges = page.locator(WAKE_RANGE_SEL).count()
        recorded["below_floor"] = (below_value, below_ranges)
        if below_value is not None:
            raise AssertionError(
                "with 30 s stored the number input carries value=%r — an "
                "out-of-range value fails HTML5 constraint validation and "
                "blocks submission of the ENTIRE Settings form" % below_value)
        if below_ranges:
            raise AssertionError(
                "with 30 s stored the card rendered %d range(s) "
                "— a range with no usable value sits at the midpoint of its own "
                "band, which is a number nobody chose"
                % (below_ranges,))
        # AND THE WHOLE FORM STILL SUBMITS. This is the
        # half that matters: the page is still usable
        # with a below-floor value on disk.
        corrected = _persist_without_js(
            new_context, base_url, "/device", "wake_interval_s", "1200",
            read_back, viewport=VIEWPORT_MIN_SUPPORTED,
            restore=False)
        recorded["corrected"] = (corrected["set"], corrected["stored"])
        if str(corrected["stored"]) != "1200":
            raise AssertionError(
                "with a below-floor value on disk the Settings form did not "
                "save a corrected one; disk reads %r" % (corrected["stored"],))
    finally:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(original_bytes)
    if _wake_interval_on_disk(server.tmpdir) != before:
        raise AssertionError(
            "this check left the interval at %r; it started at %r"
            % (_wake_interval_on_disk(server.tmpdir), before))
    _ = recorded


def test_dragging_and_keying_the_wake_range_reach_disk(new_context, server):
    """Dragging the wake-interval range moves the native <input type="number"> the form
    posts, reveals the bar and persists to disk once Enregistrer is clicked; one
    ArrowRight moves exactly one stated step and End/Home reach device_config's own
    ceiling and floor with zero pointer events fired and the recorder proving itself;
    typing into the number input moves the range back; and the retired aircraft-delay and
    battery-history sentences never render beside the control.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    recorded = {}
    page = None
    try:
        page = context.new_page()
        _login(page, base_url)
        _set_interval(page, base_url, server.tmpdir, 600)
        _assert_no_gauge_sentences(page)

        # The drag: aimed at a point well along the track rather than at a value computed
        # from the thumb geometry, since a native range maps its value across (width -
        # thumbWidth), an engine detail this check has no business predicting. What it
        # asserts is that the number input moved to a whole number of stated steps.
        #
        # Scrolled to the middle of the viewport first: at 360px this page is long and its
        # tab bar is fixed to the bottom, so a coordinate gesture taken wherever the page
        # happened to be scrolled would land somewhere else.
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
            raise AssertionError(
                "dragging the range across %.0fpx of its own track left the "
                "number input at %r — the range steers the control that already "
                "existed, or it steers nothing" % (box[2] * 0.55, dragged))
        dragged_s = int(dragged)
        if dragged_s % config_page.WAKE_SLIDER_STEP_S:
            raise AssertionError(
                "a drag produced %r, which is not a whole number of the stated "
                "%d-second steps" % (dragged, config_page.WAKE_SLIDER_STEP_S))
        # value-controls.js's notify() is the same real `change` event the bar's own
        # document-level listener reacts to, so the drag revealing the bar is the proof
        # the event fired; the edit only reaches disk once Enregistrer is clicked.
        _wait_for_bar(page)
        _save_via_bar(page)
        recorded["dragged_stored"] = _wake_interval_on_disk(server.tmpdir)
        if recorded["dragged_stored"] != dragged_s:
            raise AssertionError(
                "the dragged value did not reach disk; it reads %r"
                % (recorded["dragged_stored"],))
        page.goto(base_url + "/device")
        if page.input_value(WAKE_NUMBER_SEL) != dragged:
            raise AssertionError("the reloaded page does not show the dragged value")

        # The keyboard alone, with the pointer-free claim measured rather than promised.
        # One ArrowRight is one stated step.
        _set_interval(page, base_url, server.tmpdir, 600)
        keyed = _operate_with_keyboard(
            page, WAKE_RANGE_SEL, ["ArrowRight"])
        after_key = page.input_value(WAKE_NUMBER_SEL)
        recorded["after_arrow"] = after_key
        if int(after_key) != 600 + config_page.WAKE_SLIDER_STEP_S:
            raise AssertionError(
                "one ArrowRight moved the interval from 600 to %r; the stated "
                "step is %d seconds"
                % (after_key, config_page.WAKE_SLIDER_STEP_S))
        if keyed["pointer_events"]:
            raise AssertionError(
                "a pointer event fired during the keyboard sequence: %r"
                % (keyed["pointer_events"],))
        if not keyed["recorder_proved"]:
            raise AssertionError("the pointer recorder could not prove itself")
        # HOME AND END REACH THE CONFIGURED BAND'S OWN
        # ENDS — the floor as well as the ceiling.
        page.keyboard.press("End")
        recorded["after_end"] = page.input_value(WAKE_NUMBER_SEL)
        if int(recorded["after_end"]) != device_config.WAKE_INTERVAL_MAX_S:
            raise AssertionError(
                "End put %r into the field; the band's ceiling is %d"
                % (recorded["after_end"], device_config.WAKE_INTERVAL_MAX_S))
        page.keyboard.press("Home")
        recorded["after_home"] = page.input_value(WAKE_NUMBER_SEL)
        if int(recorded["after_home"]) != device_config.WAKE_INTERVAL_MIN_S:
            raise AssertionError(
                "Home put %r into the field; the band's floor is %d"
                % (recorded["after_home"], device_config.WAKE_INTERVAL_MIN_S))
        # Typing in the number input moves the range, the direction a repaint has to cover
        # and the one a drag test is blind to.
        _set_interval(page, base_url, server.tmpdir, 600)
        page.fill(WAKE_NUMBER_SEL, "1800")
        page.eval_on_selector(
            WAKE_NUMBER_SEL,
            "el => el.dispatchEvent(new Event('input', {bubbles: true}))")
        recorded["range_after_typing"] = page.input_value(WAKE_RANGE_SEL)
        if recorded["range_after_typing"] != "1800":
            raise AssertionError(
                "typing 1800 into the number input left the range at %r — the "
                "slider would then show a value that is no longer there while "
                "the field beside it shows the real one"
                % (recorded["range_after_typing"],))
        # Restored through the same UI sequence, never a direct write to the state directory.
        _set_interval(page, base_url, server.tmpdir, before)
        if _wake_interval_on_disk(server.tmpdir) != before:
            raise AssertionError(
                "this check left the interval at %r; it started at %r"
                % (_wake_interval_on_disk(server.tmpdir), before))
        _ = recorded
    finally:
        # Best effort only, and deliberately silent: a restore that raised here would mask
        # the failure it is cleaning up after.
        try:
            _set_interval(page, base_url, server.tmpdir, before)
        except Exception:
            pass
        context.close()


def test_the_wake_slider_meets_its_floors_at_360px_in_both_themes(new_context, server):
    """The wake-interval slider meets its floors at 360px: its hit area clears the 44px
    target by real hit-testing in its own container (never inherited from a class), it
    measures wider than the number input it steers and no wider than the card holding it
    by getBoundingClientRect rather than clientWidth, its wrapper keeps a real top margin
    off the field's own row, the Device page does not scroll sideways at that width (its
    own baseline, not the Display page's), and the paint is a floor not a ceiling: the
    card's caption and the control's own accent and surface all differ between the two
    themes and the caption is not painted in the canvas colour.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    recorded = {}
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/device")

        # The hit target, in this control's own container: a class-level measurement is
        # worth nothing here, since a declared box can resolve much smaller once
        # neighbours cover the pseudo-element that synthesises it.
        recorded["hit"] = _assert_hit_target(
            page, WAKE_RANGE_SEL, "the wake-interval slider on /device")

        # The geometry, by getBoundingClientRect and never clientWidth, which rounds to an
        # integer and can fail a correct drawing.
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
            raise AssertionError(
                "the range measures %.2fpx inside a %.2fpx content box (the "
                "number input beside it is %.2fpx) — a range input's intrinsic "
                "width is about 129px, and at the 360px floor that is a sweep "
                "of the whole 60..3600 band in a third of the card"
                % (measured["range"][0], measured["content"],
                   measured["number"]))
        if measured["range"][0] <= measured["number"]:
            raise AssertionError(
                "the range (%.2fpx) is no wider than the number input it steers "
                "(%.2fpx)" % (measured["range"][0], measured["number"]))
        if measured["range"][0] > measured["card"][0]:
            raise AssertionError(
                "the range (%.2fpx) is wider than the card holding it (%.2fpx)"
                % (measured["range"][0], measured["card"][0]))
        if not measured["marginTop"].endswith("px") or float(
                measured["marginTop"][:-2]) <= 0:
            raise AssertionError(
                "the slider's wrapper computes margin-top %r — without it the "
                "range sits flush against the number input's own row"
                % measured["marginTop"])
        width_at_360 = page.evaluate(
            "() => [document.body.scrollWidth, document.body.clientWidth,"
            "       document.documentElement.scrollWidth,"
            "       document.documentElement.clientWidth]")
        recorded["page_width"] = width_at_360
        if width_at_360[0] > width_at_360[1] or width_at_360[2] > width_at_360[3]:
            raise AssertionError(
                "the Device page scrolls sideways at 360px: %r — a full-width "
                "control is the most likely cause and this is its own page's "
                "baseline, not the Display page's" % (width_at_360,))

        # The paint, in both themes, as a floor rather than a ceiling: a caption is only a
        # caption if it can be read, so it and the control's own accent have to
        # change with the theme, or one of the two modes is showing ink on ink.
        #
        # The theme switch starts a transition, and the read has to wait for the browser's
        # own "it has finished" signal rather than a guessed instant: a getComputedStyle
        # taken straight after the attribute flip can read an interpolation frame and
        # report a token as not inverting when it does. Never a timer: an element with
        # nothing running returns an empty list and resolves at once.
        _SETTLE_SLIDER = (
            "async () => {"
            "  const els = [...document.querySelectorAll("
            "    '.wake-slider, .wake-slider *, .section-caption, body')];"
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
                "  return {caption: read(sels.caption, 'color'),"
                "          accent: read(sels.range, 'accent-color'),"
                "          surface: read(sels.range, 'background-color'),"
                "          canvas: getComputedStyle(document.body)"
                "            .backgroundColor};"
                "}", {"caption": WAKE_CAPTION_SEL,
                      "range": WAKE_RANGE_SEL})
        recorded["paints"] = paints
        light, dark = paints["light"], paints["dark"]
        for key in ("caption", "accent", "surface"):
            if light[key] == dark[key]:
                raise AssertionError(
                    "the slider card's %s paints identically in both themes "
                    "(%r) — a token that does not invert is a literal, and one "
                    "of the two modes is wrong" % (key, light[key]))
        for theme, sampled in paints.items():
            if sampled["caption"] == sampled["canvas"]:
                raise AssertionError(
                    "%s: the caption's text is the canvas colour (%r) — it "
                    "is not legible at all" % (theme, sampled["caption"]))
        _set_ui_theme(page, "light")
        if _wake_interval_on_disk(server.tmpdir) != before:
            raise AssertionError(
                "this check changed the stored interval (%r, started at %r)"
                % (_wake_interval_on_disk(server.tmpdir), before))
        _ = recorded
    finally:
        context.close()
