#!/usr/bin/env python3
"""Real-browser checks of the Console Airlines editor table: at 360 and 1280 px, in English and
French and in both themes, nothing overflows and every control (the name field, the chevron, the
artwork, the "..." menu, "Name it") is at least 44 px and owns its centre; the chevron expands
the aircraft-type sub-rows (a type with its own artwork offers Replace, any other says it uses
the airline's artwork); renaming saves on change through the real route and the "..." menu resets
it; the artwork uploads through the real routes; the "..." menu holds only its two items and
Escape closes it; the filter finds an airline by name, type or prefix; an unidentified prefix is
a highlighted row at the top. With scripts blocked the chevron, the Save button and the Upload
button still work.

State is always waited for (settled page, owned centres, focus), never read right after an input.
"""
import os
import shutil
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
import companion.test_status_pages_helpers as shp
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target, _assert_no_page_overflow,
    _in_both_themes, _login, _no_js_page, seed_state_dir,
)
from server import history_db
from server.plane import illustrations, manual_resolutions, name_overrides

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
DIALOG = "#panel-lookup-dialog"
FRANCE_NAME = '.airlines-name input[name="airline_name"][value="Air France"]'
TRANSAVIA = 'tbody.airline-group:has(input[value="Transavia France"])'
VISIBLE_GROUPS = "tbody.airline-group:not([hidden])"

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    """An owner-like state: Transavia seen on an A320 (its own artwork slot) and a B738 (none),
    a renamed TAP, an owner-named airline without artwork and one unidentified prefix."""
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


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _settle(page, selector):
    page.locator(selector).first.wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(_OWNS_CENTRE, arg=selector, timeout=10000)


def _open(new_context, server, viewport, lang="en", **context_args):
    context = new_context(viewport=viewport, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    _settle(page, FRANCE_NAME)
    return context, page


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_table_fits_and_every_control_is_a_44px_target_in_both_themes(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        wide = viewport["width"] >= 1120
        assert page.locator("thead").is_visible() == wide
        for _paint in _in_both_themes(page):
            page.wait_for_function(_SETTLED, timeout=15000)
            assert not _assert_no_page_overflow(page, "airlines", viewport["width"])
            for selector in (
                    FRANCE_NAME, TRANSAVIA + " .airlines-expand > summary",
                    TRANSAVIA + " .airlines-thumb", TRANSAVIA + " .row-menu__toggle",
                    "a.airlines-name-it"):
                _settle(page, selector)
                _assert_hit_target(page, selector, "airlines %s %s" % (name, lang))
    finally:
        context.close()


def test_the_unidentified_prefix_is_a_highlighted_row_on_top_with_a_name_it_action(
        new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        first = page.locator("tbody.airline-group").first
        assert "airline-group--gap" in first.get_attribute("class")
        assert "XYZ" in first.inner_text()
        link = first.locator("a.airlines-name-it")
        _settle(page, "a.airlines-name-it")
        link.click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        assert dialog.locator("form.lightbox__resolve-name").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_chevron_expands_the_aircraft_type_sub_rows(new_context, server, name, viewport):
    """one sub-row per type seen: an A320 (own artwork, Replace) and a B738 (the airline's
    artwork); a mouse click and the keyboard both toggle it"""
    context, page = _open(new_context, server, viewport)
    try:
        chevron = TRANSAVIA + " .airlines-expand > summary"
        subrows = TRANSAVIA + " .airlines-subrow"
        _settle(page, chevron)
        assert page.locator(subrows).first.is_hidden()
        page.locator(chevron).click()
        page.locator(subrows).first.wait_for(state="visible")
        rows = page.locator(subrows)
        assert rows.count() == 2
        first, second = rows.nth(0), rows.nth(1)
        assert first.locator("th").inner_text().startswith("A320")
        assert first.locator(".airlines-art__replace").is_visible()
        assert "Uses the airline’s artwork" in second.inner_text()
        assert second.locator("th").inner_text().startswith("B738")
        assert "2 views" in first.inner_text() and "1 view" in second.inner_text()
        page.locator(chevron).press("Enter")
        page.locator(subrows).first.wait_for(state="hidden")
        page.locator(chevron).press("Space")
        page.locator(subrows).first.wait_for(state="visible")
    finally:
        context.close()


def test_renaming_saves_on_change_and_the_menu_resets_it(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        field = page.locator(FRANCE_NAME)
        field.fill("Skyline Air")
        with page.expect_navigation():
            field.press("Enter")
        page.wait_for_function(
            "() => document.body.innerText.includes('Airline name saved')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        renamed = 'tbody.airline-group:has(input[value="Skyline Air"])'
        _settle(page, renamed + " .row-menu__toggle")
        page.locator(renamed + " .row-menu__toggle").click()
        items = page.locator(renamed + " .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Reset to the original name", "Enlarge the artwork"]
        with page.expect_navigation():
            items.first.click()
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.querySelectorAll("
            "'.airlines-name input[value=\"Skyline Air\"]').length === 0", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(FRANCE_NAME).count() == 1
        assert page.locator('.airlines-name input[value="Skyline Air"]').count() == 0
    finally:
        context.close()


def test_a_refused_name_returns_to_the_editor_with_focus_in_that_field(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page.evaluate("() => document.querySelector('%s').removeAttribute('maxlength')" % FRANCE_NAME)
        field = page.locator(FRANCE_NAME)
        field.fill("x" * 101)
        with page.expect_navigation():
            field.press("Enter")
        page.wait_for_function(
            "() => location.search.includes('sheet=air-france')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator(".toast").first.wait_for(state="visible")
        page.wait_for_function(
            "sel => document.activeElement === document.querySelector(sel)", arg=FRANCE_NAME,
            timeout=10000)
        assert page.locator(FRANCE_NAME).input_value() == "Air France"
    finally:
        context.close()


def test_the_artwork_uploads_through_the_real_routes_for_an_airline_and_a_type(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    png = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        with page.expect_navigation():
            page.locator('form[action="/illustration/air-france.png"] input[type=file]').set_input_files(png)
        page.locator(".toast").first.wait_for(state="visible")
        assert os.path.isfile(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, "air-france.png"))
        page.wait_for_function(_SETTLED, timeout=15000)
        _settle(page, TRANSAVIA + " .airlines-expand > summary")
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        slot = 'form[action="/illustration/transavia-france-a320.png"] input[type=file]'
        page.locator(slot).wait_for(state="attached")
        with page.expect_navigation():
            page.locator(slot).set_input_files(png)
        page.locator(".toast").first.wait_for(state="visible")
        assert os.path.isfile(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME,
            "transavia-france-a320.png"))
    finally:
        context.close()


def test_the_menu_holds_only_its_items_escape_closes_it_and_enlarge_opens_the_lightbox(
        new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        group = TRANSAVIA
        toggle = group + " .row-menu__toggle"
        _settle(page, toggle)
        page.locator(toggle).click()
        items = page.locator(group + " .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Enlarge the artwork"]
        page.keyboard.press("Escape")
        page.wait_for_function(
            "sel => !document.querySelector(sel).open", arg=group + " details.row-menu", timeout=5000)
        page.locator(toggle).click()
        items.first.wait_for(state="visible")
        items.first.click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        assert "/illustration/transavia-france.png" in dialog.locator(".lightbox__image").get_attribute("src")
        assert dialog.locator(".lightbox__heading").inner_text() == "Transavia France"
    finally:
        context.close()


def test_the_filter_finds_an_airline_by_name_type_or_prefix(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        field = page.locator("[data-filter-input]")
        total = page.locator("tbody.airline-group").count()
        names = (VISIBLE_GROUPS + " .airlines-name input[name=airline_name], "
                 + VISIBLE_GROUPS + " .airlines-name--fixed")
        for text, expected in (("tfv", ["Transavia France"]), ("b738", ["Transavia France"]),
                               ("tap portugal", ["TAP Air Portugal"])):
            field.fill(text)
            page.wait_for_function(
                "n => document.querySelectorAll('tbody.airline-group:not([hidden])').length === n",
                arg=len(expected), timeout=5000)
            shown = page.locator(names).evaluate_all(
                "els => els.map(e => e.tagName === 'INPUT' ? e.value : e.textContent.trim())")
            assert shown == expected, text
        field.fill("")
        page.wait_for_function(
            "n => document.querySelectorAll('tbody.airline-group:not([hidden])').length === n",
            arg=total, timeout=5000)
    finally:
        context.close()


def test_a_needs_artwork_airline_opens_the_add_artwork_step(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        link = 'a.airlines-thumb[href$="resolve=DLH"]'
        _settle(page, link)
        page.locator(link).click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        assert dialog.locator(".lightbox__heading").inner_text() == "Add an illustration for Lufthansa"
        assert dialog.locator(".resolve-upload-zone").is_visible()
        assert dialog.locator("form.lightbox__delete").is_visible()
    finally:
        context.close()


def test_without_scripts_the_chevron_the_save_button_and_the_upload_button_work(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/airlines/manage", viewport=VIEWPORT_DESKTOP,
            reduced_motion="reduce") as page:
        _settle(page, FRANCE_NAME)
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        save = 'form.airlines-name:has(input[value="Air France"]) .airlines-name__save'
        upload = 'form[action="/illustration/air-france.png"] .airlines-art__upload'
        assert page.locator(save).is_visible() and page.locator(upload).is_visible()
        page.locator(FRANCE_NAME).fill("Skyline Air")
        with page.expect_navigation():
            page.locator(save).click()
        page.wait_for_url("**/airlines/manage?flash=airline_renamed")
        assert page.locator('.airlines-name input[value="Skyline Air"]').count() == 1


def test_the_resolve_dialog_still_focuses_its_name_field(new_context, server):
    """naming an unidentified prefix opens the shared dialog with the focus in its name field"""
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        _settle(page, "a.airlines-name-it")
        page.locator("a.airlines-name-it").click()
        page.locator(DIALOG + "[open]").wait_for()
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.id === 'manual-airline-name-dialog'",
            timeout=10000)
    finally:
        context.close()
