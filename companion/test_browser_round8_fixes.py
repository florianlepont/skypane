"""Real-browser checks of the owner's round 8 straight fixes: opaque dialogs with a Save that is
reachable without scrolling, the Flights search clear of the frame button, the Location sheet's
runway cards and mode switch, the Fleet sub-tab thumb, the picture dialog's backdrop, the
tab bar's stable fill and its fitting first cell, the Users self row, the
look picker offering only existing combinations, the Personalisation look views' entrance, and the
fields that must not be autofilled.

State is always waited for (settled page, owned centres), never read right after an input.
"""
import os
import shutil
from datetime import datetime, timedelta, timezone

import pytest

import companion.test_status_pages_helpers as shp
import companion.test_view_pages_helpers as vp
import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme, seed_state_dir)
from place_map_support import Hosts, seed as _place_seed
from server import airports, device_config, history_db
from server.plane import illustrations, manual_resolutions, name_overrides

pytestmark = pytest.mark.browser

QUIET_DIALOG = "dialog#dlg-quiet-hours"
QUIET_SAVE = QUIET_DIALOG + " button[type=submit]"
FRANCE_NAME = '.airlines-name input[name="airline_name"][value="Air France"]'
PHONES = (({"width": 390, "height": 844}, "390x844"), ({"width": 360, "height": 740}, "360x740"))
THEMES = ("light", "dark")

_COMPLETE = "() => document.readyState === 'complete'"
_ANIMATIONS_DONE = (
    "() => document.getAnimations().every(a => a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "s => { const e = document.querySelector(s); if (!e) return false;"
    " const r = e.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === e || e.contains(hit)); }")


def _page(new_context, server, path, viewport, lang="en", theme="light", cookies=()):
    context = new_context(viewport=viewport, color_scheme=theme)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()},
        *cookies])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_COMPLETE, timeout=15000)
    _set_ui_theme(page, theme)
    return context, page


def _airline_seed(state_dir):
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("A320", "A320", "B738")):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(days=index + 1)).isoformat(), hex="tv%04d" % index,
                callsign="TVF%03d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Transavia France")
    manual_resolutions.add_entry(state_dir, "DLH", "Lufthansa")
    name_overrides.set_names(state_dir, ["TAP"], "TAP Air Portugal", own_builtin_name="TAP Portugal")
    target = os.path.join(state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)
    os.makedirs(target, exist_ok=True)
    shutil.copy(os.path.join(illustrations.ILLUSTRATION_DIR, "tap-portugal.png"),
                os.path.join(target, "tap-air-portugal.png"))
    shp.seed_unresolved_prefixes(state_dir, {
        "XYZ": {"count": 5, "first_seen": "2026-01-01T00:00:00+00:00",
                "last_seen": "2026-01-02T00:00:00+00:00", "example_callsign": "XYZ123"}})


def _settle_on(page, selector):
    page.locator(selector).first.wait_for(state="visible")
    page.wait_for_function(_ANIMATIONS_DONE, timeout=15000)
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(_OWNS_CENTRE, arg=selector, timeout=10000)


# --- Dialogs: opaque surface, Save reachable without scrolling -----------------


def _quiet_seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00", wake_interval_s=600)


def _open_quiet_dialog(page):
    link = "a.home-switch__window"
    page.locator(link).wait_for(state="visible")
    page.wait_for_function(_ANIMATIONS_DONE, timeout=15000)
    page.eval_on_selector(link, "el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(_OWNS_CENTRE, arg=link, timeout=10000)
    page.click(link)
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open"
        " && d.classList.contains('is-modal'); }", arg=QUIET_DIALOG, timeout=10000)
    page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)


_DIALOG_SURFACE = """sel => { const d = document.querySelector(sel); const s = getComputedStyle(d);
  const m = /rgba?\\(([^)]+)\\)/.exec(s.backgroundColor);
  const alpha = m ? (m[1].split(',').length > 3 ? parseFloat(m[1].split(',')[3]) : 1) : 0;
  const b = getComputedStyle(d, '::backdrop');
  return {alpha: alpha, filter: s.backdropFilter || s.webkitBackdropFilter || 'none',
          backdrop: b.backgroundColor}; }"""


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("viewport,name", PHONES + ((VIEWPORT_DESKTOP, "1280"),))
def test_the_quiet_hours_dialog_is_opaque_and_its_save_button_needs_no_scrolling(
        new_context, make_app_server, viewport, name, theme):
    server = make_app_server(seed=_quiet_seed, fake_providers=True)
    context, page = _page(new_context, server, "/", viewport, theme=theme)
    try:
        _open_quiet_dialog(page)
        page.eval_on_selector(QUIET_DIALOG, "d => { d.scrollTop = 0; }")
        page.wait_for_function(
            "s => document.querySelector(s).scrollTop === 0", arg=QUIET_DIALOG, timeout=5000)
        surface = page.evaluate(_DIALOG_SURFACE, QUIET_DIALOG)
        assert surface["alpha"] == 1, surface
        assert surface["filter"] == "none", surface
        assert surface["backdrop"] != "rgba(0, 0, 0, 0)", surface
        save = page.locator(QUIET_SAVE).bounding_box()
        dialog = page.locator(QUIET_DIALOG).bounding_box()
        assert save["y"] >= dialog["y"] - 0.5, (save, dialog)
        assert save["y"] + save["height"] <= min(
            dialog["y"] + dialog["height"], viewport["height"]) + 0.5, (save, dialog)
    finally:
        context.close()


# --- Flights: the search keeps clear of the frame button -----------------------


@pytest.mark.parametrize("width", (960, 1100, 1280, 1440))
def test_the_flights_search_never_overlaps_the_frame_button_or_the_title(
        new_context, make_app_server, width):
    server = make_app_server(seed=vp.seed_flight_card_variety, fake_providers=True)
    context, page = _page(new_context, server, "/history", {"width": width, "height": 800})
    try:
        _settle_on(page, ".frame-menu__button")
        boxes = page.evaluate(
            """() => { const f = e => (r => ({l: r.left, r: r.right, t: r.top, b: r.bottom}))(
                e.getBoundingClientRect());
              return {search: f(document.querySelector('.filter-bar--title')),
                      button: f(document.querySelector('.frame-menu__button')),
                      title: f(document.querySelector('.page-title'))}; }""")

        def overlap(a, b):
            return a["l"] < b["r"] and b["l"] < a["r"] and a["t"] < b["b"] and b["t"] < a["b"]

        assert not overlap(boxes["search"], boxes["button"]), boxes
        assert not overlap(boxes["search"], boxes["title"]), boxes
    finally:
        context.close()


# --- Location: runway cards, mode switch, opaque card --------------------------


def _open_place(new_context, server, viewport, lang, theme):
    context = new_context(viewport=viewport)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    largest = max(airports.load_catalogue().values(), key=lambda a: len(a.runways))
    page.goto(server.base_url() + "/detection?airport=" + largest.icao)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_COMPLETE, timeout=15000)
    page.wait_for_function(_ANIMATIONS_DONE, timeout=15000)
    return context, page


_PLACE_PROBE = """() => {
  const r = e => e.getBoundingClientRect();
  const cards = [...document.querySelectorAll('.place-sheet .runway-card')].map(card => {
    const c = r(card);
    const texts = [...card.querySelectorAll('.runway-card__number, .runway-card__detail')]
      .filter(t => t.getClientRects().length).map(r);
    const check = card.querySelector('.runway-card__check');
    const k = check && check.getClientRects().length ? r(check) : null;
    const overlap = k ? texts.some(t => k.left < t.right && t.left < k.right
      && k.top < t.bottom && t.top < k.bottom) : false;
    const inside = texts.every(t => t.left >= c.left - 0.5 && t.right <= c.right + 0.5
      && t.top >= c.top - 0.5 && t.bottom <= c.bottom + 0.5);
    const centred = texts.every(t => Math.abs((t.left + t.right) / 2 - (c.left + c.right) / 2) < 2);
    return {inside, overlap, centred, shown: !!k};
  });
  const modes = document.querySelector('.place-modes');
  const m = r(modes);
  const kids = [...modes.querySelectorAll('.place-mode')].map(r);
  const card = getComputedStyle(document.querySelector('.place-card'));
  const heading = r(document.querySelector('#runway-group-heading'));
  const chosen = r(document.querySelector('.place-chosen'));
  return {cards, track: {left: kids[0].left - m.left, right: m.right - kids[kids.length - 1].right,
    top: kids[0].top - m.top, bottom: m.bottom - kids[0].bottom},
    cardBackground: card.backgroundColor, gap: heading.top - chosen.bottom};
}"""


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("width", (960, 1280, 1440))
def test_the_location_card_is_opaque_and_its_runway_cards_and_mode_switch_are_tidy(
        new_context, make_app_server, width, lang, theme):
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context, page = _open_place(
        new_context, server, {"width": width, "height": 900}, lang, theme)
    try:
        page.locator(".place-sheet .runway-card").first.wait_for(state="visible")
        probe = page.evaluate(_PLACE_PROBE)
        assert probe["cards"], probe
        for card in probe["cards"]:
            assert card["inside"] and card["centred"] and not card["overlap"], probe
        assert any(card["shown"] for card in probe["cards"]), probe
        track = probe["track"]
        assert abs(track["left"] - track["right"]) < 1.5, probe
        assert abs(track["top"] - track["bottom"]) < 1.5, probe
        assert probe["cardBackground"].startswith("rgb(") and "rgba" not in probe[
            "cardBackground"], probe
        assert probe["gap"] >= 12, probe
    finally:
        context.close()


# --- Fleet sub-tabs, tab bar -----------------------------------------------------


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport,name", PHONES)
def test_the_fleet_tab_thumb_fills_its_segment_and_every_tab_bar_label_fits_its_pill(
        new_context, app_server_in_process, viewport, name, lang):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    context, page = _page(
        new_context, app_server_in_process, "/fleet?frame=" + seed.owned_id, viewport, lang)
    try:
        _settle_on(page, ".fleet-tabs .personalisation-nav__link")
        probe = page.evaluate(
            """() => { const link = document.querySelector(
                '.fleet-tabs .personalisation-nav__link[aria-current="page"]');
              const l = link.getBoundingClientRect();
              const s = link.querySelector('span').getBoundingClientRect();
              const labels = [...document.querySelectorAll('.tab-bar__label')].map((label) => ({
                fits: label.scrollWidth <= label.clientWidth,
                room: label.closest('.tab-bar__pill').getBoundingClientRect().width
                  - label.getBoundingClientRect().width}));
              const barStyle = getComputedStyle(document.querySelector('.tab-bar'));
              const bar = {backgroundColor: barStyle.backgroundColor};
              const named = barStyle.viewTransitionName;
              return {segment: l.width, thumb: s.width, labels: labels,
                      fill: bar.backgroundColor, named: named}; }""")
        assert probe["thumb"] >= probe["segment"] - 8, probe
        assert len(probe["labels"]) == 5, probe
        assert all(label["fits"] and label["room"] >= 4 for label in probe["labels"]), probe
        assert probe["fill"].startswith("rgb(") and "rgba" not in probe["fill"], probe
        assert probe["named"] == "skypane-tab-bar", probe
    finally:
        context.close()


# --- Picture dialog backdrop -----------------------------------------------------


@pytest.mark.parametrize("viewport,name", PHONES)
def test_the_picture_dialog_dims_the_whole_viewport_with_no_blurred_band(
        new_context, make_app_server, viewport, name):
    server = make_app_server(seed=vp.seed_flight_card_variety, fake_providers=True)
    context, page = _page(new_context, server, "/history", viewport)
    try:
        thumb = ".history-card__thumb:visible, td [data-view-panel-src]:visible"
        page.locator(thumb).first.wait_for(state="visible")
        page.locator(thumb).first.click()
        dialog = "#panel-lookup-dialog"
        page.wait_for_function(
            "s => { const d = document.querySelector(s); return d.open"
            " && document.getAnimations().every(a => a.playState !== 'running'); }",
            arg=dialog, timeout=10000)
        surface = page.evaluate(_DIALOG_SURFACE, dialog)
        assert surface["filter"] == "none", surface
        assert surface["alpha"] == 1, surface
        assert surface["backdrop"] != "rgba(0, 0, 0, 0)", surface
        # Every pixel row of the viewport, tab bar and caption area included, is dimmed alike:
        # the page behind is light, so a dimmed pixel is clearly darker than the page canvas.
        image = page.screenshot()
        from io import BytesIO
        from PIL import Image
        shot = Image.open(BytesIO(image)).convert("RGB")
        for y in (viewport["height"] - 20, viewport["height"] - 90, viewport["height"] - 160):
            red, green, blue = shot.getpixel((8, y))
            assert max(red, green, blue) < 170, (y, (red, green, blue))
    finally:
        context.close()


# --- Users self row ----------------------------------------------------------------


def test_the_users_self_row_is_not_wide_and_frames_never_wrap_on_desktop(
        new_context, app_server_in_process):
    fx.seed_users(app_server_in_process.state_dir)
    context, page = _page(new_context, app_server_in_process, "/users", VIEWPORT_DESKTOP)
    try:
        _settle_on(page, "tr.users-row")
        probe = page.evaluate(
            """() => { const rows = [...document.querySelectorAll('tr.users-row')];
              const self = rows.find(r => r.querySelector('.users-role-fixed'));
              const heights = rows.map(r => r.getBoundingClientRect().height);
              const frames = rows.map(r => {
                const c = r.querySelector('.users-cell--frames');
                const range = document.createRange(); range.selectNodeContents(c);
                return range.getBoundingClientRect().height < 26 && c.scrollWidth <= c.clientWidth + 1; });
              const fixed = self.querySelector('.users-role-fixed');
              const visibleGuard = [...self.querySelectorAll('.users-guard')].some(
                g => g.getBoundingClientRect().width > 2 && g.getBoundingClientRect().height > 2);
              return {self: self.getBoundingClientRect().height, max: Math.max(...heights),
                      min: Math.min(...heights), frames: frames, title: fixed.title,
                      visibleGuard: visibleGuard}; }""")
        assert probe["self"] <= probe["min"] + 8, probe
        assert all(probe["frames"]), probe
        assert probe["title"], probe
        assert not probe["visibleGuard"], probe
    finally:
        context.close()


# --- Look picker offers only existing combinations ---------------------------------


def test_personalisation_look_views_enter_like_the_other_views(
        new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, reduced_motion="no-preference")
    # The entrance is played once and its rule leaves with the page opening,
    # so it is read from the animations the block really started.
    context.add_init_script(
        "window.__entered = [];"
        "document.addEventListener('animationstart', (e) => {"
        " if (e.animationName.indexOf('skypane-reveal') === 0"
        " && e.target.matches('.personalisation-look, .personalisation-card'))"
        " { window.__entered.push(e.animationName); } }, true);")
    page = context.new_page()
    _login(page, server.base_url())
    try:
        for route in ("/display", "/display/special-looks"):
            page.goto(server.base_url() + route)
            page.wait_for_function(_COMPLETE, timeout=15000)
            page.wait_for_function("() => window.__entered.length > 0", timeout=10000)
            names = page.evaluate("() => window.__entered")
            assert "skypane-reveal" in names and "skypane-reveal-fade" in names, (route, names)
    finally:
        context.close()


# --- Fields that must not be autofilled ---------------------------------------------


_NO_AUTOFILL = """sel => { const e = document.querySelector(sel);
  return {autocomplete: e.getAttribute('autocomplete'), onepassword: e.hasAttribute('data-1p-ignore'),
          lastpass: e.getAttribute('data-lpignore'), type: e.type}; }"""


def _assert_no_autofill(page, selector, kind):
    probe = page.evaluate(_NO_AUTOFILL, selector)
    assert probe["autocomplete"] == "off", probe
    assert probe["onepassword"] and probe["lastpass"] == "true", probe
    assert probe["type"] == kind, probe


def test_the_invite_and_pairing_fields_are_not_autofilled(new_context, app_server_in_process):
    fx.seed_users(app_server_in_process.state_dir)
    context, page = _page(new_context, app_server_in_process, "/users", VIEWPORT_DESKTOP)
    try:
        _assert_no_autofill(page, "#invite-email", "email")
        page.goto(app_server_in_process.base_url() + "/pair-frame")
        page.wait_for_function(_COMPLETE, timeout=15000)
        _assert_no_autofill(page, "#pair-code", "text")
    finally:
        context.close()


def test_the_add_co_manager_field_is_not_autofilled(new_context, app_server_in_process):
    from co_manager_browser_support import Rig, _open
    rig = Rig(app_server_in_process)
    context, page = _open(
        new_context, rig, "owner", path="/account", viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page.wait_for_function(_COMPLETE, timeout=15000)
        _assert_no_autofill(page, ".access-sheet input[type=email]", "email")
        assert page.locator(".access-sheet form.row__form").first.get_attribute(
            "autocomplete") == "off"
    finally:
        context.close()
