"""Real-browser checks of the Editor's "Missing illustrations" section: a row per airline x aircraft
family under a small airline header, a 44px "+ Illustration" button that opens the add dialog with
the family fixed (or the type select first for an airline with no sighting), an upload that removes
the row, the filter chips and search agreeing with the title, and no horizontal overflow on a
phone. English and French, light and dark, at 360, 390 and 1280 px; without a script every row
offers a plain upload form."""
import os
import re

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, _assert_no_page_overflow, _login, _no_js_page)
from server import history_db
from server.plane import illustrations, manual_resolutions

pytestmark = pytest.mark.browser

_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
_SETTLED = animation_settle.SETTLED
SECTION = "#airlines-missing"
ITEM = SECTION + " .airlines-missing__item"
DIALOG = "#panel-lookup-dialog"
SIZES = ((360, 740), (390, 844), (1280, 900))
TITLE = {"en": "Missing illustrations", "fr": "Illustrations manquantes"}
SIGHTINGS = (("Emirates", "A388", 4), ("Emirates", "B77W", 2), ("Korean Air", "AN24", 1))


def _seed(state_dir):
    from datetime import datetime, timedelta, timezone
    seed_airline_editor(state_dir)
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    now = datetime.now(timezone.utc)
    number = 0
    with history_db.open_db(state_dir) as conn:
        for airline, code, count in SIGHTINGS:
            for _ in range(count):
                number += 1
                history_db.record_runway_event(
                    conn, ts=(now - timedelta(hours=number)).isoformat(), hex="bm%04d" % number,
                    callsign="XXX%03d" % number, aircraft_type=code,
                    confirmed_state="departing", airline=airline)


def _open(new_context, server, size, lang="en", theme="light"):
    context = new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=theme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


def _rows(page):
    return page.locator(ITEM).count()


def _title_count(page):
    return int(re.search(r"(\d+)$", page.locator("#airlines-missing-title").inner_text()).group(1))


@pytest.mark.parametrize("lang,theme,size", (
    ("en", "light", SIZES[0]), ("fr", "dark", SIZES[1]), ("fr", "light", SIZES[2]),
    ("en", "dark", SIZES[2]), ("fr", "light", SIZES[0])))
def test_the_section_fits_the_screen_with_44px_buttons(new_context, make_app_server, lang, theme, size):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, size, lang, theme)
    try:
        assert page.locator("#airlines-missing-title").inner_text().startswith(TITLE[lang])
        assert _title_count(page) == _rows(page) > 0
        assert not _assert_no_page_overflow(page, "missing illustrations", size[0])
        boxes = page.evaluate(
            """sel => [...document.querySelectorAll(sel + ' .airlines-missing__add')].map(
              e => { const b = e.getBoundingClientRect();
                     return [b.width, b.height, b.left, b.right]; })""", SECTION)
        assert boxes and all(w >= 44 - 0.5 and h >= 44 - 0.5 for w, h, _l, _r in boxes), boxes
        assert all(left >= 0 and right <= size[0] + 0.5 for _w, _h, left, right in boxes), boxes
        inside = page.evaluate(
            """sel => { const list = document.querySelector(sel + ' .airlines-missing__list').getBoundingClientRect();
              return [...document.querySelectorAll(sel + ' li')].every(li => {
                const b = li.getBoundingClientRect(); return b.left >= list.left - 0.5 && b.right <= list.right + 0.5; }); }""",
            SECTION)
        assert inside
    finally:
        context.close()


def test_the_title_chips_and_filter_count_agree_and_follow_the_filter(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, SIZES[2])
    try:
        rows = _rows(page)
        labels = page.locator(".filter-chip__text").all_inner_texts()
        counts = [int(c) for c in page.locator(".filter-chip__count").all_inner_texts()]
        chips = dict(zip(labels, counts))
        assert chips[TITLE["en"]] == rows == _title_count(page)
        table = page.locator("tbody.airline-group:not(.airline-group--gap)").count()
        gaps = page.locator("tbody.airline-group--gap").count()
        assert counts[0] == rows + table + gaps, (counts, rows, table, gaps)
        page.locator("label.filter-chip", has_text=TITLE["en"]).click()
        page.wait_for_function(
            "n => document.querySelectorAll('%s:not([hidden])').length === n" % ITEM.replace("'", ""),
            arg=rows, timeout=10000)
        assert page.locator("tbody.airline-group:not([hidden])").count() == 0
        page.locator("label.filter-chip", has_text=re.compile("^Seen")).click()
        page.wait_for_function(
            "() => document.querySelectorAll('#airlines-missing li:not([hidden])').length === 0", timeout=10000)
        assert page.locator(SECTION).is_hidden()
        page.locator("label.filter-chip", has_text="All").first.click()
        page.locator("input[type=search]").fill("emirates")
        page.wait_for_function(
            "() => [...document.querySelectorAll('#airlines-missing .airlines-missing__item:not([hidden])')].length === 2",
            timeout=10000)
        visible_heads = page.locator(SECTION + " .airlines-missing__head:not([hidden])")
        assert visible_heads.count() == 1 and "Emirates" in visible_heads.first.inner_text()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_a_family_row_opens_the_dialog_with_the_family_fixed(new_context, make_app_server, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, SIZES[2], lang)
    try:
        row = page.locator(ITEM + '[data-filter-text*="a388"]')
        row.locator(".airlines-missing__add").click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert dialog.locator(".lightbox__caption").inner_text() == "Emirates · A388"
        chip = dialog.locator("[data-upload-type-chip]")
        assert chip.is_visible() and chip.inner_text().startswith("Airbus A380")
        assert dialog.locator("#airline_artwork_type").is_hidden()
        assert dialog.locator(".lightbox__upload").is_disabled()
    finally:
        context.close()


def test_the_row_without_sighting_asks_the_type_and_an_upload_removes_the_row(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, SIZES[2])
    try:
        before = _rows(page)
        row = page.locator(ITEM, has_text="Choose type").first
        name = row.evaluate(
            "li => { let e = li.previousElementSibling; while (!e.classList.contains('airlines-missing__head')) e = e.previousElementSibling;"
            " return e.querySelector('.airlines-missing__name').textContent; }")
        row.locator(".airlines-missing__add").click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        select = dialog.locator("#airline_artwork_type")
        assert select.is_visible() and dialog.locator("[data-upload-type-chip]").is_hidden()
        dialog.locator("#manual-illustration-input-dialog").set_input_files(_PNG)
        assert dialog.locator(".lightbox__upload").is_disabled()
        select.select_option("A333")
        page.wait_for_function(
            "() => !document.querySelector('.lightbox__upload').disabled", timeout=10000)
        with page.expect_navigation():
            dialog.locator(".lightbox__upload").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert _rows(page) == before - 1 == _title_count(page)
        names = page.locator(SECTION + " .airlines-missing__name").all_inner_texts()
        assert name not in names
    finally:
        context.close()


def test_the_menu_of_a_hand_named_airline_opens_from_its_header(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, SIZES[1])
    try:
        head = page.locator(SECTION + " .airlines-missing__head", has_text="Zephyr Air")
        assert head.locator("summary.row-menu__toggle").count() == 1
        assert page.locator(ITEM + " .row-menu").count() == 0
        head.locator("summary.row-menu__toggle").click()
        assert head.locator(".row-menu__item", has_text="Rename").is_visible()
        assert head.locator("button.row-menu__item", has_text="Delete my name").is_visible()
        box = head.locator(".row-menu__toggle").bounding_box()
        assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5
        assert not _assert_no_page_overflow(page, "header menu", SIZES[1][0])
    finally:
        context.close()


def test_without_a_script_every_row_has_a_plain_upload_form(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/airlines/manage", viewport=VIEWPORT_DESKTOP) as page:
        rows = page.locator(ITEM)
        assert rows.count() > 0
        for index in range(rows.count()):
            row = rows.nth(index)
            assert row.locator("button.airlines-missing__add").is_hidden()
            assert row.locator("form.airlines-art input[type=file]").count() == 1
        asking = page.locator(ITEM, has_text="Choose type").first
        assert asking.locator("select[name=default_type]").is_visible()
        assert asking.locator("select").evaluate("s => s.required")
