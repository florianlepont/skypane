# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the rule "an airline without artwork is listed in the missing-illustrations
section": an airline the owner named by hand, or by accepting a suggestion, has a header with its
menu there (not a row in the table of airlines with artwork); the title, the chip and the rows
agree; adding artwork moves it to the table; removing the name is reachable from its header. English
and French, at 320, 390 and 1440 px."""
import json
import os

import animation_settle
import pytest
from fake_anthropic import FakeAnthropic

import companion.test_status_pages_helpers as shp
from companion import auth
from companion.test_browser_ux_helpers import (
    _assert_no_page_overflow, _login, seed_state_dir,
)
from server.plane import airline_suggest as ais
from server.plane import illustrations, manual_resolutions

pytestmark = pytest.mark.browser

STAMP = "2026-11-17T10:29:00+00:00"
_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
KNOWN = ".airlines-missing__airline"
ITEMS = ".airlines-missing__item"
TABLE_ROWS = "tbody.airline-group:not(.airline-group--gap)"
SIZES = ((320, 700), (390, 844), (1440, 900))
_SETTLED = animation_settle.SETTLED_APART_FROM_TOASTS
FLASH = {"en": "Airline name saved", "fr": "Nom de compagnie enregistré"}
CHIP = {"en": "Missing illustrations", "fr": "Illustrations manquantes"}
DELETE = {"en": "Delete my name", "fr": "Supprimer mon nom"}


def _seed(state_dir):
    seed_state_dir(state_dir)
    shp.seed_unresolved_prefixes(state_dir, {
        prefix: {"count": count, "first_seen": STAMP, "last_seen": STAMP, "example_callsign": prefix + "1"}
        for prefix, count in (("ITI", 8), ("CMA", 6))})
    entries = {"ITI": {"state": "suggested", "name": "Itavia Express", "model": ais.MODEL_ID, "asked_at": STAMP}}
    with open(ais.cache_path(state_dir), "w") as handle:
        json.dump({"entries": entries, "calls": []}, handle)
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")


def _open(new_context, server, size, lang="en", theme="light", path="/airlines/manage"):
    context = new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=theme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


def _known_names(page):
    return page.locator(KNOWN + " .airlines-missing__name").all_inner_texts()


def _assert_consistent(page, lang):
    """The title, the chip and the rows of the section agree; the chips split the rest."""
    rows = page.locator(ITEMS).count()
    assert page.locator("#airlines-missing-title").inner_text() == "%s · %d" % (CHIP[lang], rows)
    labels = page.locator(".filter-chip__text").all_inner_texts()
    counts = [int(c) for c in page.locator(".filter-chip__count").all_inner_texts()]
    chips = dict(zip(labels, counts))
    assert chips[CHIP[lang]] == rows, chips
    table = page.locator(TABLE_ROWS).count()
    gaps = page.locator("tbody.airline-group--gap").count()
    assert counts[0] == rows + table + gaps, (counts, rows, table, gaps)
    assert sum(counts[-2:]) == table, (counts, table)
    assert len(labels) == 5 and "No artwork" not in labels and "Sans illustration" not in labels, labels


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_an_airline_named_by_hand_is_in_the_block_and_not_in_the_table(new_context, make_app_server, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (1440, 900), lang, "dark" if lang == "fr" else "light")
    try:
        assert "Zephyr Air" in _known_names(page)
        row = page.locator(KNOWN, has_text="Zephyr Air")
        assert row.locator(".airlines-missing__prefix").inner_text() == "ZPH"
        assert row.locator(".airlines-missing__add").count() == 1
        assert page.locator(TABLE_ROWS, has_text="Zephyr Air").count() == 0
        _assert_consistent(page, lang)
        page.locator("label.filter-chip", has_text=CHIP[lang]).click()
        page.wait_for_function(
            "n => document.querySelectorAll('.airlines-missing__item:not([hidden])').length === n",
            arg=page.locator(ITEMS).count(), timeout=10000)
        assert "Zephyr Air" in page.locator(
            ".airlines-missing__head:not([hidden]) .airlines-missing__name").all_inner_texts()
    finally:
        context.close()


@pytest.fixture
def fake():
    server = FakeAnthropic("Itavia Express").start()
    yield server
    server.stop()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_a_validated_suggestion_lands_in_the_block_with_the_usual_flash(
        new_context, make_app_server, fake, lang):
    server = make_app_server(seed=_seed, fake_providers=True, env_overrides=fake.env())
    context, page = _open(new_context, server, (390, 844), lang)
    try:
        before = page.locator(KNOWN).count()
        assert "Itavia Express" not in _known_names(page)
        with page.expect_navigation():
            page.locator(".airlines-check").first.click()
        page.locator(".toast").first.wait_for(state="visible")
        assert FLASH[lang] in page.locator(".toast").first.inner_text()
        assert page.locator("tbody.airline-group--gap", has_text="ITI").count() == 0
        assert "Itavia Express" in _known_names(page)
        assert page.locator(KNOWN).count() == before + 1
        assert page.locator(TABLE_ROWS, has_text="Itavia Express").count() == 0
        _assert_consistent(page, lang)
    finally:
        context.close()


def test_a_name_typed_by_hand_lands_in_the_block(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (1440, 900))
    try:
        page.locator("tbody.airline-group--gap", has_text="CMA").locator("[data-modal-open]").click()
        dialog = page.locator("dialog[open]")
        dialog.wait_for(state="visible")
        dialog.locator("input[name=airline_name]").fill("Cimarron Air")
        with page.expect_navigation():
            dialog.locator("button[type=submit]").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "Cimarron Air" in _known_names(page)
        assert page.locator(TABLE_ROWS, has_text="Cimarron Air").count() == 0
        _assert_consistent(page, "en")
    finally:
        context.close()


def test_artwork_added_from_the_row_moves_the_airline_to_the_table(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (390, 844))
    try:
        before = page.locator(ITEMS).count()
        page.locator(KNOWN, has_text="Zephyr Air").locator(".airlines-missing__add").click()
        upload = page.locator("#manual-illustration-input-dialog")
        upload.wait_for(state="attached")
        upload.set_input_files(_PNG)
        page.locator("#airline_artwork_type").select_option("A333")
        with page.expect_navigation():
            page.locator("#panel-lookup-dialog .lightbox__upload").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "Zephyr Air" not in _known_names(page)
        assert page.locator(ITEMS).count() == before - 1
        moved = page.locator("#airline-zephyr-air")
        assert moved.count() == 1 and moved.evaluate("el => el.tagName") == "TBODY"
        assert "ZPH" in moved.inner_text()
        _assert_consistent(page, "en")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_removing_the_name_is_reachable_from_the_row(new_context, make_app_server, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (390, 844), lang)
    try:
        row = page.locator(KNOWN, has_text="Zephyr Air")
        row.locator(".row-menu__toggle").click()
        button = row.locator("form button", has_text=DELETE[lang])
        button.wait_for(state="visible")
        assert button.bounding_box()["height"] >= 44
        with page.expect_navigation():
            button.click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "Zephyr Air" not in _known_names(page)
        assert "ZPH" not in manual_resolutions.load_manual_resolutions(server.state_dir)
        _assert_consistent(page, lang)
    finally:
        context.close()


@pytest.mark.parametrize("lang,theme", (("en", "light"), ("fr", "dark")))
@pytest.mark.parametrize("size", SIZES, ids=[str(s[0]) for s in SIZES])
def test_the_block_fits_and_its_controls_are_44px_targets(new_context, make_app_server, size, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, size, lang, theme)
    try:
        _assert_no_page_overflow(page, "the Airlines editor", expected_width=size[0])
        row = page.locator(KNOWN, has_text="Zephyr Air")
        for control in (row.locator(".airlines-missing__add"), row.locator(".row-menu__toggle")):
            box = control.bounding_box()
            assert box["width"] >= 44 and box["height"] >= 44 and box["x"] + box["width"] <= size[0], box
        row.locator(".row-menu__toggle").click()
        panel = row.locator(".row-menu__panel").bounding_box()
        assert panel["x"] >= 0 and panel["x"] + panel["width"] <= size[0], panel
    finally:
        context.close()
