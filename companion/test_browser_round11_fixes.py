"""Real-browser checks of the owner's round 11 fixes: the Users Active switch is a whole standard
switch (the knob inside a track whose colour tells on from off), the Airlines editor's type rows
line up with the airline rows without any cell overlapping another, the Flights sort is the
Airlines collection's sort menu, the look picker's segmented controls centre their labels in
equal cells, the Calendar look is a page of its own, the Location search lists airports and
places in one list as the text is typed, the shared save bar is readable over the Location map
in both themes, and the Fleet firmware table has a column per fact.

State is always waited for (settled page, owned centres), never read right after an input."""
import re
from datetime import datetime, timedelta, timezone

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _no_js_page, _set_ui_theme,
    seed_state_dir, seed_two_releases)
from place_map_support import Hosts, open_details, seed as _place_seed
from server import device_config, history_db

pytestmark = pytest.mark.browser

TRANSAVIA = 'tbody.airline-group:has(input[value="Transavia France"])'
THEMES = ("light", "dark")
LANGS = ("en", "fr")
TABLET = {"width": 768, "height": 900}

_COMPLETE = "() => document.readyState === 'complete'"
_ANIMATIONS_DONE = (
    "() => document.getAnimations().every(a => (a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity) || a.playState !== 'running')")


def _airline_seed(state_dir):
    """Transavia seen on two A320 and one B738, so its type rows are three."""
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("A320", "A320", "B738")):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(days=index + 1)).isoformat(), hex="tv%04d" % index,
                callsign="TVF%03d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Transavia France")


def _look_seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme="band_red_field")


def _open(new_context, server, path, viewport, lang="en", theme="light"):
    context = new_context(viewport=viewport, color_scheme=theme)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_COMPLETE, timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)
    return context, page


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _rgba(css):
    numbers = [float(n) for n in re.findall(r"[-\d.]+", css)]
    return (numbers + [1.0])[:4] if len(numbers) == 3 else numbers[:4]


def _contrast(foreground, background):
    """WCAG ratio of a text colour over an opaque background (both computed `rgb()` strings)."""
    fg, bg = _rgba(foreground), _rgba(background)
    assert bg[3] == 1.0, "the surface under the text is not opaque: %r" % background
    blended = [fg[3] * c + (1 - fg[3]) * b for c, b in zip(fg[:3], bg[:3])]
    lighter, darker = sorted((_luminance(blended), _luminance(bg[:3])), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# --- Users: the Active switch ---------------------------------------------------------


_SWITCH_GEOMETRY = (
    "() => [...document.querySelectorAll('.users-table .switch')].map(b => {"
    " const t = b.querySelector('.switch__track').getBoundingClientRect();"
    " const k = b.querySelector('.switch__thumb').getBoundingClientRect();"
    " return {on: b.getAttribute('aria-checked') === 'true', disabled: b.disabled,"
    "  track: [t.width, t.height], inside: k.left >= t.left && k.right <= t.right"
    "   && k.top >= t.top && k.bottom <= t.bottom, knob: [k.width, k.height],"
    "  fill: getComputedStyle(b.querySelector('.switch__track')).backgroundColor,"
    "  knobFill: getComputedStyle(b.querySelector('.switch__thumb')).backgroundColor,"
    "  right: k.left - t.left > 12}; })")


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED], ids=["1280", "360"])
def test_the_users_active_switch_is_a_whole_standard_switch(
        new_context, app_server_in_process, viewport, theme):
    """The knob sits inside a 52x32 track at both ends, a round 24px, and an off switch has
    another fill than an on one (also after the in-place flip), in both themes."""
    fx.seed_users(app_server_in_process.state_dir)
    context, page = _open(new_context, app_server_in_process, "/users", viewport, theme=theme)
    try:
        before = page.evaluate(_SWITCH_GEOMETRY)
        assert len(before) == 4 and any(row["disabled"] for row in before), before
        for row in before:
            assert row["track"] == [52, 32] and row["knob"] == [24, 24], row
            assert row["inside"] and row["on"] and row["right"], row
        target = page.locator(".users-table button.switch:not(:disabled)").first
        target.scroll_into_view_if_needed()
        target.click()
        page.wait_for_function(
            "() => document.querySelectorAll('.users-table .switch[aria-checked=false]').length === 1",
            timeout=10000)
        page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)
        page.wait_for_function(
            "() => { const s = document.querySelector('.users-table .switch[aria-checked=false]"
            " .switch__thumb'); const t = s.parentNode.getBoundingClientRect();"
            " return s.getBoundingClientRect().left - t.left < 12; }", timeout=10000)
        after = page.evaluate(_SWITCH_GEOMETRY)
        off = [row for row in after if not row["on"]]
        on = [row for row in after if row["on"] and not row["disabled"]]
        assert len(off) == 1 and on, after
        assert off[0]["inside"] and off[0]["track"] == [52, 32] and not off[0]["right"], off
        assert off[0]["fill"] != on[0]["fill"], (off, on)
        assert off[0]["knobFill"] != "rgba(0, 0, 0, 0)", off
    finally:
        context.close()


# --- Airlines: the type rows ------------------------------------------------------------


_CELL_BOXES = (
    "(group) => { const g = document.querySelector(group);"
    " const box = e => { const r = e.getBoundingClientRect();"
    "  return {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height,"
    "   over: (() => { let m = r.right; const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);"
    "    for (let n = w.nextNode(); n; n = w.nextNode()) { if (!n.textContent.trim()) continue;"
    "     const p = n.parentElement; if (p !== e && p.getBoundingClientRect().width <= 2) continue;"
    "     const q = document.createRange(); q.selectNodeContents(n); m = Math.max(m, q.getBoundingClientRect().right); }"
    "    for (const x of e.querySelectorAll('*')) { const b = x.getBoundingClientRect();"
    "     if (b.width > 2 && b.height > 2) m = Math.max(m, b.right); }"
    "    return m - r.right; })(), cls: e.className}; };"
    " const rows = [...g.querySelectorAll('tr.airlines-row, tr.airlines-subrow')];"
    " return rows.filter(r => r.getClientRects().length).map(r => "
    "  [...r.children].filter(c => c.getClientRects().length && c.getBoundingClientRect().width > 0)"
    "   .map(box)); }")


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, TABLET, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "768", "360"])
def test_the_airline_type_rows_align_with_the_airline_row_and_nothing_overlaps(
        new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_airline_seed, fake_providers=True)
    context, page = _open(new_context, server, "/airlines/manage", viewport, lang=lang, theme=theme)
    try:
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        page.wait_for_function(
            "g => document.querySelectorAll(g + ' tr.airlines-subrow').length > 0 && "
            "[...document.querySelectorAll(g + ' tr.airlines-subrow')].every(r => r.getClientRects().length)",
            arg=TRANSAVIA, timeout=10000)
        rows = page.evaluate(_CELL_BOXES, TRANSAVIA)
        assert len(rows) >= 3, rows
        for at, cells in enumerate(rows):
            for first in range(len(cells)):
                for second in range(first + 1, len(cells)):
                    one, two = cells[first], cells[second]
                    apart = (one["r"] <= two["l"] + 1 or two["r"] <= one["l"] + 1
                             or one["b"] <= two["t"] + 1 or two["b"] <= one["t"] + 1)
                    assert apart, ("cells overlap", one, two)
            for cell in cells if at else ():
                assert cell["over"] <= 1, "a cell overflows: %r" % (cell,)
        if viewport["width"] >= 1120:
            head, subs = rows[0], rows[1:]
            assert len(head) == 6 and all(len(sub) == 6 for sub in subs), rows
            for sub in subs:
                for column in range(6):
                    assert abs(sub[column]["l"] - head[column]["l"]) <= 1, (column, sub, head)
                    assert abs(sub[column]["r"] - head[column]["r"]) <= 1, (column, sub, head)
        else:
            head, subs = rows[0], rows[1:]
            menu = [c for c in head if "airlines-cell--menu" in c["cls"]][0]
            for sub in subs:
                sub_menu = [c for c in sub if "airlines-cell--menu" in c["cls"]]
                assert sub_menu and abs(sub_menu[0]["r"] - menu["r"]) <= 1, (sub, menu)
    finally:
        context.close()


# --- Flights: the sort is the collection's sort menu -----------------------------------


_TOGGLE_STYLE = (
    "() => { const e = document.querySelector('.collection-sort > summary');"
    " const s = getComputedStyle(e); const r = e.getBoundingClientRect();"
    " return {cls: e.className, w: r.width, h: r.height, border: s.borderTopColor,"
    "  bg: s.backgroundColor, radius: s.borderTopLeftRadius, panel: !!e.parentNode"
    "   .querySelector('.collection-sort__panel'), radios: e.parentNode"
    "   .querySelectorAll('input[type=radio][name=sort]').length}; }")


@pytest.mark.parametrize("theme", THEMES)
def test_the_flights_sort_looks_like_the_airlines_collection_sort(
        new_context, make_app_server, theme):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, "/flights", VIEWPORT_DESKTOP, theme=theme)
    try:
        page.locator(".collection-sort > summary").wait_for(state="visible")
        flights = page.evaluate(_TOGGLE_STYLE)
        page.goto(server.base_url() + "/airlines")
        page.wait_for_function(_COMPLETE, timeout=15000)
        _set_ui_theme(page, theme)
        page.locator(".collection-sort > summary").wait_for(state="visible")
        airlines = page.evaluate(_TOGGLE_STYLE)
        assert flights["panel"] and flights["radios"] == 4, flights
        assert {k: v for k, v in flights.items() if k != "radios"} == {
            k: v for k, v in airlines.items() if k != "radios"}, (flights, airlines)
        assert flights["w"] >= 44 and flights["h"] >= 44, flights
    finally:
        context.close()


def test_the_flights_sort_menu_works_without_scripts(new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/flights",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.locator(".collection-sort > summary").click()
        page.locator('.collection-sort__option:has(input[value="airline"])').click()
        page.locator(".history-controls__apply").click()
        page.wait_for_url("**sort=airline*")
        assert page.locator("input[name=sort][value=airline]:checked").count() == 1


# --- Look picker: segmented controls ----------------------------------------------------


_SEGMENTS = (
    "() => [...document.querySelectorAll('[data-look-sheet] .look-seg')].map(seg => {"
    " const t = seg.getBoundingClientRect();"
    " return {w: t.width, top: t.top, bottom: t.bottom, options: [...seg.querySelectorAll("
    "  '.look-seg__option')].filter(o => o.getClientRects().length).map(o => {"
    "   const r = o.getBoundingClientRect(); const range = document.createRange();"
    "   range.selectNodeContents(o); const c = range.getBoundingClientRect();"
    "   const pill = getComputedStyle(o, '::before');"
    "   return {w: r.width, h: r.height, top: r.top, bottom: r.bottom,"
    "    dx: (c.left + c.right) / 2 - (r.left + r.right) / 2,"
    "    dy: (c.top + c.bottom) / 2 - (r.top + r.bottom) / 2,"
    "    pillTop: parseFloat(pill.top), pillHeight: parseFloat(pill.height)}; })}; })")


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED], ids=["1280", "360"])
def test_the_look_segments_have_equal_cells_with_centred_labels_and_pills(
        new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_look_seed, fake_providers=True)
    context, page = _open(new_context, server, "/display", viewport, lang=lang, theme=theme)
    try:
        segments = page.evaluate(_SEGMENTS)
        assert len(segments) == 2, segments
        for seg in segments:
            assert len(seg["options"]) == 3, seg
            widths = [o["w"] for o in seg["options"]]
            assert max(widths) - min(widths) <= 1, seg
            for option in seg["options"]:
                assert abs(option["dx"]) <= 1 and abs(option["dy"]) <= 1, option
                assert option["h"] >= 44 - 0.5, option
                # The 44px option is centred on its track (a margin once pushed it 4px up).
                assert abs((option["top"] + option["bottom"]) / 2
                           - (seg["top"] + seg["bottom"]) / 2) <= 0.5, (seg, option)
                # The pill is centred in its option.
                assert abs(option["pillTop"] * 2 + option["pillHeight"] - option["h"]) <= 1, option
    finally:
        context.close()


# --- Calendar look: a page of its own ---------------------------------------------------


CALENDAR_LOOK = "/display/calendar-look"


@pytest.mark.parametrize("lang,title,back", [
    ("en", "Calendar flights look", "Calendar"), ("fr", "Allure des vols du calendrier", "Calendrier")])
def test_the_calendar_row_links_to_a_look_page_with_its_own_save_bar(
        new_context, make_app_server, lang, title, back):
    server = make_app_server(seed=_look_seed, fake_providers=True)
    context, page = _open(new_context, server, "/display/calendar", VIEWPORT_DESKTOP, lang=lang)
    try:
        assert page.locator("[data-look-open]").count() == 0
        assert page.locator("[data-look-sheet]").count() == 0
        page.locator("a.special-row__edit").click()
        page.wait_for_url("**" + CALENDAR_LOOK)
        # The Save bar is in the page but waits for an edit.
        page.wait_for_function("() => document.querySelector('.dirty-bar').hidden")
        assert page.locator(".dirty-bar__message").text_content() == title
        assert page.locator("a.form-back").inner_text().strip() == back
        assert page.locator(".personalisation-nav__link[aria-current=page]").get_attribute(
            "data-pers-view") == "calendar"
        page.locator("[data-look-same]").click()
        page.locator(
            '.look-seg__option:has(input[data-look-axis="background"][value="full"])').click()
        page.locator(".dirty-bar").wait_for(state="visible")
        page.locator(".dirty-bar__save").click()
        page.wait_for_url("**/display/calendar")
        saved = device_config.load_device_config(server.state_dir)["calendar_theme_id"]
        assert saved in device_config.THEME_IDS, saved
        assert saved != device_config.load_device_config(server.state_dir)["theme"], saved
        page.locator("a.special-row__edit").click()
        page.wait_for_url("**" + CALENDAR_LOOK)
        page.locator("[data-look-same]").click()
        page.locator("a.dirty-bar__cancel").wait_for(state="visible")
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("a.dirty-bar__cancel").click()
        page.wait_for_url("**/display/calendar")
    finally:
        context.close()


def test_the_calendar_look_page_saves_without_scripts(new_context, make_app_server):
    server = make_app_server(seed=_look_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), CALENDAR_LOOK,
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.locator("summary.look-edit__summary").click()
        page.locator("label.look-option:has(input[name=calendar_theme_id]:not([value='']))").first.click()
        page.locator(".dirty-bar__save").click()
        page.wait_for_url("**/display/calendar*")
    assert device_config.load_device_config(server.state_dir)["calendar_theme_id"]


# --- Location: one search, and the save bar over the map ------------------------------


def _open_place(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", theme="light"):
    context = new_context(viewport=viewport, color_scheme=theme)
    hosts = Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    page.wait_for_function(
        "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1",
        timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)
    return context, page, hosts


@pytest.mark.parametrize("lang,airports,places", [
    ("en", "Airports", "Places and addresses"), ("fr", "Aéroports", "Lieux et adresses")])
def test_typing_lists_airports_and_places_in_one_grouped_list(
        new_context, make_app_server, lang, airports, places):
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context, page, hosts = _open_place(new_context, server, lang=lang)
    try:
        page.locator("#place-search").press_sequentially("Lyon")
        page.wait_for_function(
            "() => document.querySelectorAll('#place-results [data-place]').length >= 1",
            timeout=10000)
        headings = page.locator("#place-results .place-results__group").all_inner_texts()
        assert headings == [airports, places], headings
        assert len(hosts.search_requests) == 1, hosts.search_requests
        # Airports come first, then the places: the headings split one list.
        order = page.evaluate(
            "() => [...document.querySelectorAll('#place-results li')].map(li =>"
            " li.hasAttribute('data-group') ? li.getAttribute('data-group')"
            " : li.hasAttribute('data-place') ? 'place' : 'airport')")
        assert order[0] == "airports" and order.index("places") > order.index("airport"), order
        page.locator("#place-results [data-place] button").first.click()
        page.wait_for_function(
            "() => document.getElementById('place-results').hidden", timeout=5000)
        page.wait_for_function(
            "() => Math.abs(parseFloat(document.getElementById('place-lat').value) - 48.8606)"
            " < 0.01", timeout=5000)
    finally:
        context.close()


def test_typing_only_asks_the_search_service_after_a_pause(new_context, make_app_server):
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context, page, hosts = _open_place(new_context, server)
    try:
        page.locator("#place-search").press_sequentially("Lyon", delay=20)
        assert not hosts.search_requests
        page.wait_for_function(
            "() => document.querySelectorAll('#place-results [data-place]').length >= 1",
            timeout=10000)
        assert len(hosts.search_requests) == 1
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED], ids=["1280", "360"])
def test_the_save_bar_over_the_map_is_opaque_and_readable(
        new_context, make_app_server, viewport, theme):
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context, page, _hosts = _open_place(new_context, server, viewport=viewport, theme=theme)
    try:
        open_details(page)
        page.fill("#place-lat", "45.7578")
        page.locator("[data-dirty-bar]").wait_for(state="visible")
        page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)
        # On a phone the bar is the two buttons of the compact card: the card is what must be
        # opaque, and the message is read aloud rather than drawn.
        paint = page.evaluate(
            "() => { const bar = document.querySelector('[data-dirty-bar]');"
            " const c = e => getComputedStyle(e).color;"
            " const bg = e => getComputedStyle(e).backgroundColor;"
            " const inline = innerWidth < 960;"
            " return {bar: bg(inline ? document.querySelector('.place-sheet') : bar),"
            "  message: c(bar.querySelector('.dirty-bar__message')), inline: inline,"
            "  cancel: c(bar.querySelector('.dirty-bar__cancel')),"
            "  save: c(bar.querySelector('.dirty-bar__save')),"
            "  saveBg: bg(bar.querySelector('.dirty-bar__save'))}; }")
        assert _rgba(paint["bar"])[3] == 1.0, paint
        if not paint["inline"]:
            assert _contrast(paint["message"], paint["bar"]) >= 4.5, paint
        assert _contrast(paint["cancel"], paint["bar"]) >= 4.5, paint
        assert _contrast(paint["save"], paint["saveBg"]) >= 4.5, paint
    finally:
        context.close()


# --- Fleet: the firmware version history ------------------------------------------------


@pytest.mark.parametrize("lang,installed", [("en", "Installed"), ("fr", "Installée")])
@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED], ids=["1280", "360"])
def test_the_firmware_history_lines_up_its_dot_version_and_chip_down_the_list(
        new_context, app_server_in_process, viewport, lang, installed):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    seed_two_releases(app_server_in_process.state_dir)
    context, page = _open(
        new_context, app_server_in_process, "/fleet?frame=" + seed.live_id, viewport, lang=lang)
    try:
        page.locator("ul.update-hist__list").scroll_into_view_if_needed()
        rows = page.evaluate(
            "() => [...document.querySelectorAll('li.update-item')].map(r => {"
            " const box = s => { const e = r.querySelector(s); if (!e) return null;"
            "  const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, t: b.top, b: b.bottom}; };"
            " return {dot: box('.update-item__dot'), version: box('.update-item__version'),"
            "  chip: box('.banner__pill'), row: box(':scope'), meta: box('.update-item__meta'),"
            "  summary: box('.update-item__summary')}; })")
        assert len(rows) == 2, rows
        first, second = rows
        assert abs(first["dot"]["l"] - second["dot"]["l"]) <= 1, rows
        assert abs(first["version"]["l"] - second["version"]["l"]) <= 1, rows
        chips = [row["chip"] for row in rows if row["chip"]]
        assert chips and all(chip["r"] <= row["summary"]["r"] + 1
                             for row in rows if row["chip"] for chip in [row["chip"]]), rows
        # Chips sit on one right edge down the list.
        assert max(chip["r"] for chip in chips) - min(chip["r"] for chip in chips) <= 1, rows
        assert all(row["dot"]["r"] <= row["version"]["l"] for row in rows), rows
        page_width = page.evaluate("() => document.documentElement.clientWidth")
        assert all(0 <= row["summary"]["l"] and row["summary"]["r"] <= page_width for row in rows), rows
        badge = page.locator("li.update-item--running .banner__pill")
        assert badge.is_visible() and badge.text_content().strip() == installed
    finally:
        context.close()
