"""Browser proof of the Quiet hours dialog on Home: it opens from the schedule link on its title (no
field takes the focus), Tab stays inside it, Esc closes it and returns focus to the schedule link, the presets
fill both fields, saving writes only the three quiet-hours keys and updates Home, a refused value
reopens the dialog with the error beside the field, a background refresh while it is open leaves it
and a half-typed time intact, and it works with scripts blocked. Layout is measured at 360 and
1280 px, in English and French, in both themes.

Boxes are measured only after the finite animations have ended and the page owns its controls:
right after a navigation a cross-document view transition is still running and `elementFromPoint`
answers the root element. Focus and DOM state is always waited for, never read straight after a key.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _in_both_themes,
    _login,
    _no_js_page,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

THREE_KEYS = ("quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end")
LINK = "a.home-switch__window"
DIALOG = "dialog#dlg-quiet-hours"
START = "#quiet-window-start"
END = "#quiet-window-end"
ENABLED = "#quiet-window-enabled"
SAVE = DIALOG + " button[type=submit]"
CARDS = DIALOG + " .quiet-cards button"
PRESSED = CARDS + "[aria-pressed=true]"
MIN_PX = 43.5
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))

# Finite animations only: the live pulse never ends and must not hold the test.
_ANIMATIONS_DONE = (
    "document.getAnimations().every((a) => a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")

# A control passes when it is at least 44x44 and owns its own centre.
_HIT_PROBE = """args => args.selectors.map((sel) => {
  const el = document.querySelector(sel);
  if (!el) return [sel, 'missing'];
  const r = el.getBoundingClientRect();
  if (r.width < args.min || r.height < args.min) {
    return [sel, 'size ' + r.width.toFixed(1) + 'x' + r.height.toFixed(1)];
  }
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  if (!hit || !(el === hit || el.contains(hit))) {
    return [sel, 'covered by ' + (hit ? hit.tagName + '.' + hit.className : 'nothing')];
  }
  return null;
}).filter(Boolean)"""

_DIALOG_BOUNDS = """() => {
  const d = document.querySelector('dialog#dlg-quiet-hours');
  const r = d.getBoundingClientRect();
  return {scrollWidth: d.scrollWidth, clientWidth: d.clientWidth,
          left: r.left, right: r.right, viewport: document.documentElement.clientWidth};
}"""


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00", wake_interval_s=600)


def _open_home(new_context, base_url, lang="en", viewport=VIEWPORT_DESKTOP, install_clock=False):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    if install_clock:
        page.clock.install()
    _login(page, base_url)
    page.goto(base_url + "/")
    page.locator(LINK).wait_for(state="visible")
    _wait_at_rest(page, LINK)
    return context, page


def _wait_at_rest(page, selector):
    """Wait until the finite animations ended and `selector` owns its own centre.
    The element is first scrolled into view: a notification above the state card
    can push it below the fold on a phone."""
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        """sel => {
          if (!(%s)) return false;
          const e = document.querySelector(sel);
          if (!e) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!hit && (hit === e || e.contains(hit));
        }""" % _ANIMATIONS_DONE, arg=selector, timeout=10000)


def _open_dialog(page):
    page.click(LINK)
    page.wait_for_function(
        "() => { const d = document.querySelector('%s');"
        " return d.open && d.classList.contains('is-modal')"
        " && document.activeElement && document.activeElement.matches('%s .modal__title'); }"
        % (DIALOG, DIALOG), timeout=10000)
    _wait_at_rest(page, START)


def _value(page, selector):
    return page.eval_on_selector(selector, "el => el.value")


def _wait_value(page, selector, expected):
    page.wait_for_function(
        "arg => document.querySelector(arg[0]).value === arg[1]",
        arg=[selector, expected], timeout=5000)


def _config(server):
    return device_config.load_device_config(server.state_dir)


# --- opening, focus, closing ---------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_link_opens_the_dialog_on_its_title_and_esc_returns_to_the_link(
        new_context, make_app_server, lang, viewport_name, viewport):
    """The schedule link is a 44px target; a click opens the modal on its title, not on a field;
    Tab never leaves it; Esc closes it and focus returns to the schedule link."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        box = page.locator(LINK).bounding_box()
        assert box["height"] >= MIN_PX and box["width"] >= MIN_PX, box
        assert not page.evaluate(_HIT_PROBE, {"selectors": [LINK], "min": MIN_PX})
        _open_dialog(page)
        # Focus is trapped: it is always on a control inside the dialog, never on the page
        # behind, the body or the browser chrome.
        page.evaluate(
            """() => { window.__inside = [];
              const dialog = document.querySelector('%s');
              document.addEventListener('focusin', (e) => window.__inside.push(
                dialog.contains(e.target))); }""" % DIALOG)
        inside_or_nowhere = (
            "() => { const a = document.activeElement;"
            " return !!a && a !== document.body"
            " && document.querySelector('%s').contains(a); }" % DIALOG)
        for key in ["Tab"] * 14 + ["Shift+Tab"] * 3:
            page.keyboard.press(key)
            page.wait_for_function(inside_or_nowhere, timeout=5000)
        page.wait_for_function(
            "() => window.__inside.length >= 4 && window.__inside.every(Boolean)", timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('%s').open"
            " && document.activeElement && document.activeElement.matches('%s')"
            % (DIALOG, LINK), timeout=10000)
        assert "#" not in page.url
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_dialog_and_row_fit_and_every_control_is_44px_in_both_themes(
        new_context, make_app_server, lang, viewport_name, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        selectors = [
            DIALOG + " a.modal__close", START, END, DIALOG + " label.quiet-tile",
            CARDS + ":nth-child(1)", CARDS + ":nth-child(2)", DIALOG + " .quiet-timezone-note a",
            SAVE, DIALOG + " a.modal__dismiss"]
        for _theme in _in_both_themes(page):
            _wait_at_rest(page, LINK)
            failure = _assert_no_page_overflow(page, "/ " + lang, viewport["width"])
            assert not failure, failure
            assert not page.evaluate(_HIT_PROBE, {"selectors": [LINK], "min": MIN_PX})
            _open_dialog(page)
            bounds = page.evaluate(_DIALOG_BOUNDS)
            assert bounds["scrollWidth"] <= bounds["clientWidth"], bounds
            assert bounds["left"] >= -0.5 and bounds["right"] <= bounds["viewport"] + 0.5, bounds
            failures = page.evaluate(_HIT_PROBE, {"selectors": selectors, "min": MIN_PX})
            assert not failures, (viewport_name, lang, failures)
            page.keyboard.press("Escape")
            page.wait_for_function(
                "() => !document.querySelector('%s').open" % DIALOG, timeout=10000)
    finally:
        context.close()


# --- presets and saving -------------------------------------------------------


def _wait_pressed(page, expected_index):
    """Wait until exactly the card at `expected_index` (or none for None) is selected."""
    page.wait_for_function(
        """arg => { const cards = Array.from(document.querySelectorAll(arg[0]));
          const on = cards.map((c, i) => c.getAttribute('aria-pressed') === 'true' ? i : -1)
            .filter((i) => i >= 0);
          return arg[1] < 0 ? on.length === 0 : (on.length === 1 && on[0] === arg[1]); }""",
        arg=[CARDS, -1 if expected_index is None else expected_index], timeout=5000)


def test_preset_cards_fill_both_fields_and_there_is_no_always_active_card(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url())
    try:
        _open_dialog(page)
        buttons = page.locator(CARDS)
        assert buttons.count() == 2
        assert "Always" not in page.locator(DIALOG).inner_text()
        _wait_pressed(page, 0)                      # the stored 23:00-07:00 is Night
        buttons.nth(1).click()
        _wait_value(page, START, "08:00")
        _wait_value(page, END, "18:00")
        _wait_pressed(page, 1)
        buttons.nth(0).click()
        _wait_value(page, START, "23:00")
        _wait_value(page, END, "07:00")
        assert page.is_checked(ENABLED)
        _wait_pressed(page, 0)
        # Choosing a window turns quiet hours on.
        buttons.nth(0).click()
        page.wait_for_function(
            "() => document.querySelector('%s').checked" % ENABLED, timeout=5000)
        _wait_pressed(page, 0)
        # Editing a tile by hand to hours no card holds selects no window card.
        buttons.nth(0).click()
        page.fill(START, "21:15")
        _wait_pressed(page, None)
        # The presets are buttons, not submits: nothing was posted.
        assert "flash" not in page.url
        assert _config(server)["quiet_hours_start"] == "23:00"
    finally:
        context.close()


def test_the_preset_cards_and_tiles_follow_the_sketch_in_both_themes(
        new_context, make_app_server):
    """The selected card has the accent border (no check mark on a phone); the tiles are filled blocks with a
    large time; the enable checkbox row is out of the layout with a script."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_MIN_SUPPORTED)
    try:
        for _theme in _in_both_themes(page):
            _open_dialog(page)
            look = page.evaluate(
                """arg => { const on = document.querySelector(arg[0]);
                  const off = document.querySelectorAll(arg[1])[1];
                  const root = getComputedStyle(document.documentElement);
                  const accent = document.createElement('i');
                  accent.style.color = root.getPropertyValue('--color-accent');
                  document.body.appendChild(accent);
                  const accentRgb = getComputedStyle(accent).color; accent.remove();
                  const check = on.querySelector('.quiet-card__check');
                  const time = document.querySelector(arg[2]);
                  const tile = time.closest('.quiet-tile');
                  const enabled = document.querySelector(arg[3]);
                  return {border: getComputedStyle(on).borderTopColor, accent: accentRgb,
                    checkShown: getComputedStyle(check).display !== 'none',
                    offCheckShown: getComputedStyle(
                      off.querySelector('.quiet-card__check')).display !== 'none',
                    timeSize: parseFloat(getComputedStyle(time).fontSize),
                    tileFill: getComputedStyle(tile).backgroundColor,
                    enabledHidden: enabled.getClientRects().length === 0};
                }""", [PRESSED, CARDS, START, ENABLED])
            assert look["border"] == look["accent"], look
            # On a phone the check gives way to the accent border and the filled icon, so both
            # presets and both times fit one row each.
            assert not look["checkShown"] and not look["offCheckShown"], look
            assert look["timeSize"] >= 20, look
            assert look["tileFill"] != "rgba(0, 0, 0, 0)", look
            assert look["enabledHidden"], look
            page.keyboard.press("Escape")
            page.wait_for_function(
                "() => !document.querySelector('%s').open" % DIALOG, timeout=10000)
    finally:
        context.close()


def test_saving_in_three_taps_changes_only_the_three_keys_and_home_follows(
        new_context, make_app_server):
    """Tap the schedule, choose the start time, Save quiet hours: three actions; the toast names
    the window, the Home link shows it and no other stored setting moved."""
    server = make_app_server(seed=_seed, fake_providers=True)
    before = _config(server)
    context, page = _open_home(new_context, server.base_url())
    try:
        _open_dialog(page)                                  # 1: tap the schedule
        page.fill(START, "21:15")                           # 2: choose the start time
        with page.expect_navigation():
            page.click(SAVE)                                # 3: Save quiet hours
        page.wait_for_function(
            "() => document.querySelector('.toast-region--flash .toast')"
            " && document.querySelector('.toast-region--flash .toast').textContent"
            ".indexOf('21:15 to 07:00') !== -1", timeout=10000)
        page.wait_for_function(
            "() => document.querySelector('%s').textContent.indexOf('21:15 – 07:00') !== -1"
            % LINK, timeout=10000)
        after = _config(server)
        assert after["quiet_hours_start"] == "21:15" and after["quiet_hours_end"] == "07:00"
        moved = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        assert moved == {"quiet_hours_start"}, moved
        assert not _dialog_open(page)
    finally:
        context.close()


def test_a_schedule_stored_off_with_custom_hours_opens_with_no_card_selected(
        new_context, make_app_server):
    def seed_off(state_dir):
        seed_state_dir(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=True, quiet_hours_enabled=False,
            quiet_hours_start="21:00", quiet_hours_end="05:30", wake_interval_s=600)

    server = make_app_server(seed=seed_off, fake_providers=True)
    context, page = _open_home(new_context, server.base_url())
    try:
        _open_dialog(page)
        assert page.locator(CARDS).count() == 2
        _wait_pressed(page, None)
        _wait_value(page, START, "21:00")
        _wait_value(page, END, "05:30")
        assert not page.is_checked(ENABLED)
    finally:
        context.close()


def _dialog_open(page):
    return page.eval_on_selector(DIALOG, "el => el.open")


def test_a_refused_value_reopens_the_dialog_with_the_error_beside_the_field(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    before = _config(server)
    context, page = _open_home(new_context, server.base_url(), "en", VIEWPORT_MIN_SUPPORTED)
    try:
        _open_dialog(page)
        page.fill(START, "")
        page.eval_on_selector(DIALOG + " form", "form => { form.noValidate = true; }")
        with page.expect_navigation() as info:
            page.click(SAVE)
        assert info.value.status == 400
        page.wait_for_function(
            "() => { const d = document.querySelector('%s');"
            " return d.open && document.activeElement && document.activeElement.id === "
            "'quiet-window-start'; }" % DIALOG, timeout=10000)
        _wait_at_rest(page, START)
        assert page.get_attribute(START, "aria-invalid") == "true"
        error = page.locator("#quiet-window-start-error")
        error.wait_for(state="visible")
        assert "HH:MM" in error.inner_text()
        field_box = page.locator(START).bounding_box()
        error_box = error.bounding_box()
        assert error_box["y"] >= field_box["y"] + field_box["height"] - 1
        assert abs(error_box["x"] - field_box["x"]) < 24
        assert _config(server) == before
        failure = _assert_no_page_overflow(page, "/ refused", 360)
        assert not failure, failure
    finally:
        context.close()


# --- background refresh --------------------------------------------------------


def test_a_background_refresh_leaves_the_open_dialog_and_a_half_typed_time(
        new_context, make_app_server):
    """The refresh replaces the status card (and with it the schedule link) but the dialog sits
    outside every swapped region: it stays open, the typed time stays, and Esc still returns focus
    to the schedule link, now the new one."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), install_clock=True)
    try:
        _open_dialog(page)
        page.fill(START, "20:05")
        page.evaluate(
            "() => { document.querySelector('%s').__kept = true;"
            " document.querySelector('%s').__old = true; }" % (DIALOG, LINK))
        # The focus leaves the field (a refresh never runs while a field has it) but the dialog
        # keeps its typed value.
        page.focus(DIALOG + " a.modal__dismiss")
        page.wait_for_function(
            "() => document.activeElement.matches('%s a.modal__dismiss')" % DIALOG, timeout=5000)
        # A stored change makes the next refresh carry a different page.
        device_config.save_device_config(server.state_dir, display_enabled=False)
        page.clock.run_for(46000)
        page.wait_for_function(
            "() => { const l = document.querySelector('%s'); return !!l && !l.__old; }" % LINK,
            timeout=15000)
        assert page.evaluate(
            "() => { const d = document.querySelector('%s');"
            " return d.__kept === true && d.open && d.classList.contains('is-modal'); }" % DIALOG)
        assert _value(page, START) == "20:05"
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('%s').open"
            " && document.activeElement && document.activeElement.matches('%s')"
            " && !document.activeElement.__old" % (DIALOG, LINK), timeout=10000)
    finally:
        context.close()


# --- scripts blocked -------------------------------------------------------------


def test_with_scripts_blocked_the_hash_link_shows_the_form_and_the_submit_posts(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/", VIEWPORT_MIN_SUPPORTED,
                     reduced_motion="reduce") as page:
        page.click(LINK)
        page.wait_for_selector(DIALOG + ":target", state="visible", timeout=10000)
        # Without a script the inert cards are hidden and the checkbox is the visible control.
        assert page.is_visible(ENABLED) and not page.is_visible(CARDS + ":nth-child(1)")
        page.fill(END, "06:30")
        with page.expect_navigation():
            page.click(SAVE)
        assert page.url.endswith("/?flash=quiet_window_saved")
    after = _config(server)
    assert (after["quiet_hours_start"], after["quiet_hours_end"]) == ("23:00", "06:30")


SMALL_PHONES = (("390x844", {"width": 390, "height": 844}),
                ("375x667", {"width": 375, "height": 667}))

@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", SMALL_PHONES, ids=[v[0] for v in SMALL_PHONES])
def test_the_quiet_hours_sheet_fits_a_small_phone_without_scrolling(
        new_context, make_app_server, lang, name, viewport):
    """Everything (both presets, both times, Save and Close) is visible at once on a 390x844
    and a 375x667 phone, the presets side by side and the times side by side."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        _open_dialog(page)
        probe = page.evaluate(
            """() => {
                const d = document.querySelector('dialog#dlg-quiet-hours');
                const r = e => e.getBoundingClientRect();
                const cards = [...d.querySelectorAll('.quiet-card')].map(r);
                const times = [...d.querySelectorAll('.quiet-tile')].map(r);
                const save = r(d.querySelector('button[type=submit]'));
                const close = [...d.querySelectorAll('button, a')].filter(
                    e => e.textContent.trim() === (document.documentElement.lang === 'fr'
                        ? 'Fermer' : 'Close')).map(r)[0];
                const scrolls = [d, ...d.querySelectorAll('*')].filter(
                    e => e.scrollHeight > e.clientHeight + 1
                        && ['auto', 'scroll'].includes(getComputedStyle(e).overflowY));
                const clipped = [...d.querySelectorAll('input[type=time]')].filter(
                    e => e.scrollWidth > e.clientWidth + 1).length;
                return {cards, times, save: save.bottom, close: close.bottom, top: r(d).top,
                        height: innerHeight, scrolls: scrolls.length, clipped};
            }""")
        assert probe["scrolls"] == 0 and probe["clipped"] == 0
        assert probe["top"] >= 0
        assert probe["save"] <= probe["height"] and probe["close"] <= probe["height"]
        assert len(probe["cards"]) == 2 and len(probe["times"]) == 2
        for pair in (probe["cards"], probe["times"]):
            assert abs(pair[0]["top"] - pair[1]["top"]) < 2
            assert pair[0]["right"] <= pair[1]["left"] + 0.5
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_twelve_hour_browser_shows_each_time_once_in_24_hour_form(
        new_context, make_app_server, lang):
    """The browser here shows a 12-hour clock in its time fields; each tile then draws the
    24-hour time over the field's own text (the form the rest of the page uses), so the value
    is told once, and it follows an edit."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, VIEWPORT_MIN_SUPPORTED)
    try:
        _open_dialog(page)
        page.wait_for_function(
            "() => [...document.querySelectorAll('%s .quiet-tile .field-inline-value')]"
            ".map(e => e.textContent.trim()).join('|') === '23:00|07:00'" % DIALOG, timeout=5000)
        assert page.evaluate(
            "() => [...document.querySelectorAll('%s .quiet-tile .field-inline-value')]"
            ".every(e => e.getBoundingClientRect().height > 0)" % DIALOG)
        assert page.evaluate(
            "() => [...document.querySelectorAll('%s .quiet-tile input[type=time]')]"
            ".every(i => getComputedStyle(i).color === 'rgba(0, 0, 0, 0)')" % DIALOG)
        page.fill(START, "21:30")
        page.wait_for_function(
            "() => document.querySelector('%s .quiet-tile .field-inline-value')"
            ".textContent.trim() === '21:30'" % DIALOG, timeout=5000)
    finally:
        context.close()
