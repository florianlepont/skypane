#!/usr/bin/env python3
"""Real-browser checks of the Airlines list: every row is one fixed height at every supported
width (two-line names included), nothing overflows, the aircraft types are named and the retired
status labels never come back, the filter finds a row by name, type or prefix, and the sheet
opened from a row carries the state an owner can act on (needs-artwork, renamed, built-in name
winning over their own, replaced picture), in both languages and both themes.
"""
import os
import shutil

import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_hit_target,
    _assert_no_page_overflow, _in_both_themes, _login,
)
from server.plane import illustrations, manual_resolutions, name_overrides

pytestmark = pytest.mark.browser

DIALOG = "#panel-lookup-dialog"
ROW_HEIGHT = 76
WIDTHS = (360, 390, 700, 1024, 1280)

# What no row, in either language, may say any more: the status chips and the any-aircraft label.
RETIRED_LABELS = (
    "Any aircraft", "Tout appareil", "Replaced artwork", "Illustration remplacée",
    "Your artwork", "Votre illustration", "Built-in name used", "Nom intégré utilisé",
    "Renamed", "Renommée", "Resolved by hand", "Résolue à la main", "No artwork yet",
    "Pas encore d’illustration",
)


def _override(state_dir, key, source_key):
    target = os.path.join(state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)
    os.makedirs(target, exist_ok=True)
    shutil.copy(
        os.path.join(illustrations.ILLUSTRATION_DIR, source_key + ".png"),
        os.path.join(target, key + ".png"))


def _seed_owner_state(state_dir):
    """An owner-like state: replaced artwork, a renamed airline, a hand-typed name the built-in
    list now overrides, one airline still needing artwork and one with the owner's own picture."""
    _override(state_dir, "air-france", "air-france")
    manual_resolutions.add_entry(state_dir, "IBE", "Iberia Express")
    manual_resolutions.add_entry(state_dir, "DLH", "Lufthansa")
    manual_resolutions.add_entry(state_dir, "EXS", "Jet2")
    _override(state_dir, "jet2", "wizz-air")
    name_overrides.set_names(state_dir, ["TAP"], "TAP Air Portugal", own_builtin_name="TAP Portugal")
    _override(state_dir, "tap-air-portugal", "tap-portugal")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_owner_state, fake_providers=True)


def _open(new_context, server, viewport, lang="en", **context_args):
    context = new_context(viewport=viewport, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines")
    page.locator(".airline-row").first.wait_for(state="visible")
    return context, page


def _row(page, name):
    return page.locator(".airline-list__item").filter(
        has=page.locator('.airline-row__name:text-is("%s")' % name))


@pytest.mark.parametrize("width", WIDTHS)
def test_every_row_is_one_height_and_nothing_overflows(new_context, server, width):
    """at 360, 390, 700, 1024 and 1280 px every row is exactly 76px tall - rows whose name wraps
    to two lines and rows with four aircraft types included - no row's text leaves its row, the
    page has no horizontal overflow and each row is a 44px-plus touch target"""
    viewport = {"width": width, "height": 900}
    context, page = _open(new_context, server, viewport)
    try:
        rows = page.eval_on_selector_all(
            ".airline-row",
            "els => els.map(el => { const r = el.getBoundingClientRect();"
            " const n = el.querySelector('.airline-row__name');"
            " const t = el.querySelector('.airline-row__types');"
            " const nr = n.getBoundingClientRect(); const tr = t.getBoundingClientRect();"
            " return {height: r.height, width: r.width, name: n.textContent,"
            "  lines: Math.round(nr.height / parseFloat(getComputedStyle(n).lineHeight)),"
            "  textBottom: Math.max(nr.bottom, tr.bottom) - r.bottom,"
            "  textRight: Math.max(nr.right, tr.right) - r.right}; })")
        assert len(rows) >= 38, len(rows)
        assert {row["height"] for row in rows} == {ROW_HEIGHT}, sorted({row["height"] for row in rows})
        for row in rows:
            assert row["textBottom"] <= 0 and row["textRight"] <= 0, row
            assert row["lines"] in (1, 2), row
        if width <= 390:
            assert any(row["lines"] == 2 for row in rows), (
                "no two-line name measured at %dpx: the equal-height claim would be vacuous" % width)
        problem = _assert_no_page_overflow(page, "airlines list at %d" % width)
        assert not problem, problem
        _assert_hit_target(page, ".airline-row", "airline row at %d" % width)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_rows_name_the_aircraft_and_carry_no_status_label(new_context, server, lang):
    """every state of the seeded page reads as its aircraft: the airframe of the picture first
    (B737 · A320 for Transavia, E190/E145 for the Embraer secondaries, +2 on four types), the
    owner-named airlines read All types, and none of the retired labels appears anywhere in the
    page text, in either language"""
    context, page = _open(new_context, server, VIEWPORT_PHONE, lang)
    try:
        everywhere = page.locator("main").inner_text()
        for label in RETIRED_LABELS:
            assert label not in everywhere, label
        all_types = "All types" if lang == "en" else "Tous types"
        expected = {
            "Transavia France": "B737 · A320", "Air France": "A320",
            "Royal Air Maroc": "B737 · E190", "Amelia": "A320 · E145",
            "Air Caraïbes": "A350-900 · A330 · +2", "TAP Air Portugal": "A321",
            "Lufthansa": all_types, "Jet2": all_types, "Iberia Airlines": "A320",
            "Air France Hop": "E190 · ATR72",
        }
        for name, types in expected.items():
            line = _row(page, name).locator(".airline-row__types").inner_text()
            assert line.upper() == types.upper() or line == types, (name, line)
            assert _row(page, name).locator(".airline-card__chip").count() == 0
        # A row for an airline without artwork shows the dashed frame, not a broken picture.
        needs = _row(page, "Lufthansa")
        assert needs.locator(".airline-card__placeholder").count() == 1
        assert needs.locator("img").count() == 0
    finally:
        context.close()


def test_the_filter_finds_a_row_by_name_type_or_prefix(new_context, server):
    """typing a name, an aircraft designator or a callsign prefix narrows the list to the rows
    that carry it, the count follows, and clearing the field brings every row back"""
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        field = page.locator("[data-filter-input]")
        total = page.locator(".airline-list__item").count()
        visible = ".airline-list__item:not([hidden])"
        field.fill("air france")
        names = page.locator(visible + " .airline-row__name").all_text_contents()
        assert names == ["Air France", "Air France Hop"], names
        field.fill("a350")
        names = page.locator(visible + " .airline-row__name").all_text_contents()
        assert names == ["Air Caraïbes", "French Bee"], names
        field.fill("afr")
        names = page.locator(visible + " .airline-row__name").all_text_contents()
        assert names == ["Air France"], names
        field.fill("tap portugal")
        assert page.locator(visible + " .airline-row__name").all_text_contents() == [
            "TAP Air Portugal"], "the built-in name still finds a renamed airline"
        field.fill("")
        assert page.locator(visible).count() == total
    finally:
        context.close()


def test_the_needs_artwork_row_opens_the_add_artwork_step(new_context, server):
    """the row of an airline without artwork opens the sheet on its upload zone with the add
    heading, never the replace zone, and the delete form of its manual name"""
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        _row(page, "Lufthansa").locator(".airline-row").click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        assert dialog.locator(".lightbox__heading").inner_text() == "Add an illustration for Lufthansa"
        assert dialog.locator(".resolve-upload-zone").is_visible()
        assert dialog.locator("form.lightbox__replace").is_hidden()
        assert dialog.locator("form.lightbox__delete").is_visible()
        assert dialog.locator(".lightbox__caption").is_hidden()
    finally:
        context.close()


def test_the_sheet_states_that_an_owner_can_act_on(new_context, server):
    """a renamed airline's sheet offers the reset to SkyPane's name, a hand-typed name the
    built-in list overrides says so in one sentence beside the delete form, a replaced picture
    is the one the sheet shows (cache-busted), and none of them adds a label to the title"""
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        dialog = page.locator(DIALOG)
        _row(page, "TAP Air Portugal").locator(".airline-row").click()
        dialog.wait_for(state="visible")
        assert dialog.locator(".lightbox__heading").inner_text() == "TAP Air Portugal"
        assert dialog.locator(".airline-sheet__reset").is_visible()
        assert "TAP Portugal" in dialog.locator(".airline-sheet__reset p").inner_text()
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")

        _row(page, "Iberia Airlines").locator(".airline-row").click()
        dialog.wait_for(state="visible")
        note = dialog.locator(".lightbox__manual-note").inner_text()
        assert "Iberia Express" in note and "IBE" in note and "Iberia Airlines" in note, note
        assert dialog.locator("form.lightbox__delete").is_visible()
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")

        _row(page, "Air France").locator(".airline-row").click()
        dialog.wait_for(state="visible")
        assert "?v=" in dialog.locator(".lightbox__image").get_attribute("src")
        assert dialog.locator(".airline-sheet__reset").is_hidden()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, VIEWPORT_DESKTOP],
                         ids=["360", "390", "1280"])
def test_a_four_type_sheet_fits_in_both_themes(new_context, server, viewport, lang):
    """the Air Caraïbes sheet (four type tabs that wrap onto a second line on a phone) keeps one
    title, every tab a 44px target, the dialog inside the viewport and nothing overflowing, in
    light and dark, and switching to the A350-1000 tab shows that type's picture"""
    context, page = _open(new_context, server, viewport, lang)
    try:
        _row(page, "Air Caraïbes").locator(".airline-row").click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        page.wait_for_function(
            "() => getComputedStyle(document.getElementById('panel-lookup-dialog'))"
            ".transform === 'none'")
        tabs = dialog.locator("a.airline-sheet__type")
        assert tabs.all_text_contents() == ["A350-900", "A330", "A350-1000", "ATR72"]
        tabs.nth(2).click()
        assert dialog.locator(".lightbox__image").get_attribute("src").startswith(
            "/illustration/air-caraibes-a350-1000.png")
        for theme in _in_both_themes(page):
            for index in range(4):
                box = tabs.nth(index).bounding_box()
                assert box["height"] >= 44 and box["width"] >= 44, (theme, index, box)
            box = dialog.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], box
            assert dialog.evaluate("e => e.scrollWidth - e.clientWidth") <= 0
            assert dialog.locator("h2:visible").count() == 1
    finally:
        context.close()
