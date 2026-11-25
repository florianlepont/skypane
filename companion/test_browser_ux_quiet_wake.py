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


WINDOW_LINK = "a.home-pill--quiet"
DIALOG = "dialog#dlg-quiet-hours"
START = "#quiet-window-start"
END = "#quiet-window-end"
SAVE = DIALOG + " button[type=submit]"
PRESETS = DIALOG + " .quiet-cards button"
MIN_PX = 43.5

# Finite animations that act on the element, one of its ancestors (the dialog's rise, a view
# transition on the root) or one of its descendants. An ambient pulse elsewhere on the page
# (the countdown on Home breathes for thirty seconds once its target has passed) neither
# moves the element nor covers it, so it must not hold the test.
_MOVING_NEAR = (
    "(e) => document.getAnimations().some((a) => {"
    " if (a.playState !== 'running' || !a.effect"
    " || a.effect.getComputedTiming().iterations === Infinity) return false;"
    " const t = a.effect.target;"
    " return !!t && (t.contains(e) || e.contains(t)); })")


def _quiet_hours_on_disk(state_dir):
    config = device_config.load_device_config(state_dir)
    return (config["quiet_hours_start"], config["quiet_hours_end"])


def _wait_at_rest(page, selector):
    """Wait until the document is complete, no finite animation on or around `selector` runs
    and it owns its own centre (right after a navigation a view transition answers with the
    root)."""
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        """sel => {
          const e = document.querySelector(sel);
          if (!e) return false;
          if ((%s)(e)) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!hit && (hit === e || e.contains(hit));
        }""" % _MOVING_NEAR, arg=selector, timeout=10000)


def _open_dialog(page, base_url):
    page.goto(base_url + "/")
    _wait_at_rest(page, WINDOW_LINK)
    page.click(WINDOW_LINK)
    page.wait_for_function(
        "() => { const d = document.querySelector('%s');"
        " return d.open && document.activeElement"
        " && document.activeElement.matches('%s .modal__title'); }" % (DIALOG, DIALOG),
        timeout=10000)
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
            assert page.locator(START).count() == 1 and page.locator(PRESETS).count() == 2
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


WAKE_STEP_SEL = "[data-minutes-step]"
WAKE_NUMBER_SEL = 'input[name="wake_interval_min"]'
WAKE_SECONDS_SEL = 'input[name="wake_interval_s"]'
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


# Set the interval (a whole number of minutes) through the real UI and save, so every arrangement measured below is
# reached the way a visitor reaches it. Raises on failure.
def _set_interval(page, base_url, state_dir, seconds):
    # Commits reveal the bar; only a click on its own Save persists. Playwright's `.fill()`
    # dispatches `input` only, never `change` (the trigger the bar's document-level listener
    # needs), so `_commit_field()` fires the real event a blur would.
    #
    # Idempotent: "set it to what it already is" fires no `change` at all, so the bar never
    # reveals and _wait_for_bar() below would time out waiting for a reveal that correctly
    # never comes.
    page.goto(base_url + "/fleet?frame=live&tab=settings")
    if _wake_interval_on_disk(state_dir) == seconds:
        return
    page.fill(WAKE_NUMBER_SEL, str(seconds // 60))
    _commit_field(page, WAKE_NUMBER_SEL)
    _wait_for_bar(page)
    _save_via_bar(page)
    stored = _wake_interval_on_disk(state_dir)
    if stored != seconds:
        raise AssertionError(
            "setting the interval to %r through the UI stored %r"
            % (seconds, stored))
    page.goto(base_url + "/fleet?frame=live&tab=settings")



def test_the_wake_interval_still_saves_with_scripts_blocked_through_the_minutes_field(
        new_context, server):
    """The wake interval still saves with scripts blocked: the minutes typed natively,
    submitted through the real form, re-read from disk after a fresh GET and restored the same
    way, at 360px and in both shipped languages; the script-only step buttons are gated shut
    without a script and open with one; the scripts-blocked page still renders exactly one
    number input with its unit and the saved minutes; and the out-of-range trap is re-proven
    end to end: with 30 s on disk the number input carries no value attribute and the whole
    Settings form still saves a corrected value.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)

    def read_back():
        """The stored interval in minutes, the unit the field is typed in."""
        seconds = _wake_interval_on_disk(server.tmpdir)
        return None if seconds is None else seconds // 60

    for lang in ("en", "fr"):
        cookies = [{"name": auth.UI_LANG_COOKIE_NAME,
                    "value": lang, "url": base_url}]
        result = _persist_without_js(
            new_context, base_url, "/fleet?frame=live&tab=settings", "wake_interval_min",
            "15", read_back, viewport=VIEWPORT_MIN_SUPPORTED, cookies=cookies,
            shows_back=False)
        if str(result["stored"]) != "15":
            raise AssertionError(
                "%s: 15 typed minutes did not reach disk as 900 s, it reads %r"
                % (lang, result["stored"]))
    if _wake_interval_on_disk(server.tmpdir) != before:
        raise AssertionError(
            "the scripts-blocked saves left the interval at %r; it started at %r"
            % (_wake_interval_on_disk(server.tmpdir), before))

    _assert_js_gate(
        new_context, base_url, "/fleet?frame=live&tab=settings", WAKE_STEP_SEL,
        viewport=VIEWPORT_MIN_SUPPORTED)

    with _no_js_page(new_context, base_url, "/fleet?frame=live&tab=settings",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        blocked_number = page.locator(WAKE_NUMBER_SEL).count()
        blocked_unit = page.locator(".fleet-unit").count()
        blocked_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
        _assert_no_gauge_sentences(page)
    if blocked_number != 1 or blocked_unit < 1:
        raise AssertionError(
            "with scripts blocked the tile renders %d number input(s) and %d unit sibling(s); "
            "it owes one of each" % (blocked_number, blocked_unit))
    if str(blocked_value) != str(-(-before // 60)):
        raise AssertionError(
            "with scripts blocked the minutes input shows %r, not the saved %r minutes"
            % (blocked_value, -(-before // 60)))

    # The one defect on this tile that takes down the WHOLE page: an out-of-range `value` on
    # a native numeric input fails HTML5 constraint validation, which blocks submission of the
    # entire Settings form. The below-floor state is written to the config file directly,
    # since save_device_config() raises on 30; the file's exact bytes are restored.
    config_path = device_config.device_config_path(server.tmpdir)
    with open(config_path, encoding="utf-8") as fh:
        original_bytes = fh.read()
    try:
        doc = json.loads(original_bytes)
        doc["wake_interval_s"] = 30
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        with _no_js_page(new_context, base_url, "/fleet?frame=live&tab=settings",
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            below_value = page.get_attribute(WAKE_NUMBER_SEL, "value")
        if below_value is not None:
            raise AssertionError(
                "with 30 s stored the minutes input carries value=%r — an out-of-range value "
                "fails HTML5 constraint validation and blocks submission of the ENTIRE "
                "Settings form" % below_value)
        corrected = _persist_without_js(
            new_context, base_url, "/fleet?frame=live&tab=settings", "wake_interval_min", "20",
            read_back, viewport=VIEWPORT_MIN_SUPPORTED, restore=False, shows_back=False)
        if str(corrected["stored"]) != "20":
            raise AssertionError(
                "with a below-floor value on disk the Settings form did not save a corrected "
                "one; disk reads %r" % (corrected["stored"],))
    finally:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(original_bytes)
    if _wake_interval_on_disk(server.tmpdir) != before:
        raise AssertionError(
            "this check left the interval at %r; it started at %r"
            % (_wake_interval_on_disk(server.tmpdir), before))


def test_stepping_and_typing_the_wake_minutes_reach_disk(new_context, server):
    """The step buttons and shortcuts move the minutes field and the seconds the form posts,
    reveal the bar and persist to disk once Enregistrer is clicked; the keyboard alone (the
    field's own arrow keys, no pointer event) moves exactly one minute; typing in the field
    moves the posted seconds; and the retired aircraft-delay and battery-history sentences
    never render beside the control.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    page = None
    try:
        page = context.new_page()
        _login(page, base_url)
        _set_interval(page, base_url, server.tmpdir, 600)
        _assert_no_gauge_sentences(page)

        page.eval_on_selector(
            "[data-minutes-step='1']", "el => el.scrollIntoView({block: 'center'})")
        page.click("[data-minutes-step='1']")
        page.click("[data-minutes-step='1']")
        if page.input_value(WAKE_NUMBER_SEL) != "12" or page.input_value(WAKE_SECONDS_SEL) != "720":
            raise AssertionError("two presses of + did not move 10 min to 12 min / 720 s")
        _wait_for_bar(page)
        _save_via_bar(page)
        if _wake_interval_on_disk(server.tmpdir) != 720:
            raise AssertionError(
                "the stepped value did not reach disk; it reads %r"
                % (_wake_interval_on_disk(server.tmpdir),))
        page.goto(base_url + "/fleet?frame=live&tab=settings")
        if page.input_value(WAKE_NUMBER_SEL) != "12":
            raise AssertionError("the reloaded page does not show the stepped value")

        # The keyboard alone: one ArrowUp in the field is one minute.
        keyed = _operate_with_keyboard(page, WAKE_NUMBER_SEL, ["ArrowUp"])
        if page.input_value(WAKE_NUMBER_SEL) != "13" or page.input_value(WAKE_SECONDS_SEL) != "780":
            raise AssertionError("one ArrowUp did not move 12 min to 13 min / 780 s")
        if keyed["pointer_events"]:
            raise AssertionError(
                "a pointer event fired during the keyboard sequence: %r" % (keyed["pointer_events"],))
        if not keyed["recorder_proved"]:
            raise AssertionError("the pointer recorder could not prove itself")

        # Typing moves the posted seconds with it.
        page.fill(WAKE_NUMBER_SEL, "30")
        if page.input_value(WAKE_SECONDS_SEL) != "1800":
            raise AssertionError(
                "typing 30 into the minutes field left the posted seconds at %r"
                % (page.input_value(WAKE_SECONDS_SEL),))
        _set_interval(page, base_url, server.tmpdir, before - before % 60 or 60)
        _ = keyed
    finally:
        try:
            if page is not None:
                _set_interval(page, base_url, server.tmpdir, before - before % 60 or 60)
        except Exception:
            pass
        context.close()


def test_the_wake_tile_meets_its_floors_at_360px_in_both_themes(new_context, server):
    """The wake-interval tile meets its floors at 360px: the step buttons clear the 44px
    target by real hit-testing in their own container, the whole tile fits inside the page
    (which does not scroll sideways), and the paint is a floor not a ceiling: the tile's
    caption and surface differ between the two themes and the caption is not painted in the
    canvas colour.
    """
    base_url = server.base_url()
    before = _wake_interval_on_disk(server.tmpdir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/fleet?frame=live&tab=settings")
        for selector in ("[data-minutes-step='-1']", "[data-minutes-step='1']"):
            _assert_hit_target(page, selector, "the wake-interval step button on /fleet")
        width_at_360 = page.evaluate(
            "() => [document.body.scrollWidth, document.body.clientWidth,"
            "       document.documentElement.scrollWidth,"
            "       document.documentElement.clientWidth]")
        if width_at_360[0] > width_at_360[1] or width_at_360[2] > width_at_360[3]:
            raise AssertionError("the frame page scrolls sideways at 360px: %r" % (width_at_360,))
        inside = page.evaluate(
            "() => { const tile = document.querySelector('.fleet-tile--control')"
            ".getBoundingClientRect();"
            " return [...document.querySelectorAll('.fleet-tile--control input, "
            ".fleet-tile--control button')].every(e => { const r = e.getBoundingClientRect();"
            " return r.width === 0 || (r.left >= tile.left - 0.5 && r.right <= tile.right + 0.5); }); }")
        if not inside:
            raise AssertionError("a control of the wake-interval tile sticks out of the tile")
        settle = (
            "async () => {"
            "  const els = [...document.querySelectorAll("
            "    '.fleet-tile--control, .fleet-tile--control *, body')];"
            "  await Promise.all(els.flatMap("
            "    e => e.getAnimations().map(a => a.finished.catch(() => {}))));"
            "  return els.length;"
            "}")
        paints = {}
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            page.evaluate(settle)
            paints[theme] = page.evaluate(
                "sels => {"
                "  const read = (s, p) =>"
                "    getComputedStyle(document.querySelector(s)).getPropertyValue(p).trim();"
                "  return {caption: read(sels.caption, 'color'),"
                "          surface: read(sels.tile, 'background-color'),"
                "          canvas: getComputedStyle(document.body).backgroundColor};"
                "}", {"caption": WAKE_CAPTION_SEL, "tile": ".fleet-tile--control"})
        light, dark = paints["light"], paints["dark"]
        for key in ("caption", "surface"):
            if light[key] == dark[key]:
                raise AssertionError(
                    "the tile's %s paints identically in both themes (%r) — a token that does "
                    "not invert is a literal, and one of the two modes is wrong"
                    % (key, light[key]))
        for theme, sampled in paints.items():
            if sampled["caption"] == sampled["canvas"]:
                raise AssertionError(
                    "%s: the caption's text is the canvas colour (%r) — it is not legible"
                    % (theme, sampled["caption"]))
        _set_ui_theme(page, "light")
        if _wake_interval_on_disk(server.tmpdir) != before:
            raise AssertionError(
                "this check changed the stored interval (%r, started at %r)"
                % (_wake_interval_on_disk(server.tmpdir), before))
    finally:
        context.close()
