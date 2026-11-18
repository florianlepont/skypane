#!/usr/bin/env python3
"""Real-browser checks of the Console Airlines editor table: at 360 and 1280 px, in English and
French and in both themes, nothing overflows and every control (the chevron, the artwork, the "..."
menu, "Name it") is at least 44 px and owns its centre; the chevron expands the aircraft-type
sub-rows (one upload entry per type: Add artwork, or Change artwork when a picture exists);
"Rename" in the "..." menu opens a dialog (a bottom sheet on a phone, a centred card on a desktop)
that saves through the real route, and the menu resets the name; an unidentified prefix is one
compact row at the top named in a dialog, with no Ignore and no aircraft-type field; tapping a
thumbnail enlarges it; the "..." menu holds only its items and Escape closes it; the filter finds
an airline by name, type or prefix and its chips filter by kind. With scripts blocked the
chevron, the Rename dialog and the Upload button still work.

State is always waited for (settled page, owned centres, focus), never read right after an input.
"""
import os

import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target, _assert_no_page_overflow,
    _in_both_themes, _login, _no_js_page,
)
from server.plane import airline_default_types, illustrations, manual_resolutions

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
DIALOG = "#panel-lookup-dialog"
GAP = "tbody.airline-group--gap"
GAP_OPEN = GAP + " a[data-modal-open]"
GAP_DIALOG = GAP + " dialog"
GAP_NAME = GAP_DIALOG + ' input[name="airline_name"]'
FRANCE = "#airline-air-france"
FRANCE_NAME = FRANCE + " .airlines-name"
FRANCE_MENU = FRANCE + " .airlines-row .row-menu__toggle"
FRANCE_DIALOG = FRANCE + " dialog"
IBERIA = "#airline-iberia-airlines"
IBERIA_MENU = IBERIA + " .airlines-row .row-menu__toggle"
FRANCE_FIELD = FRANCE_DIALOG + ' input[name="airline_name"]'
TRANSAVIA = "#airline-transavia-france"
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


_seed = seed_airline_editor


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


def _open_dialog(page, trigger, dialog):
    _settle(page, trigger)
    page.locator(trigger).click()
    page.locator(dialog).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)


def _open_rename(page):
    _settle(page, FRANCE_MENU)
    page.locator(FRANCE_MENU).click()
    page.locator(FRANCE + " .airlines-row .row-menu__panel a.row-menu__item").click()
    page.locator(FRANCE_DIALOG).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_name_it_opens_a_sheet_on_a_phone_and_a_centred_card_on_a_desktop(
        new_context, server, name, viewport):
    """the name is typed in a dialog, not in the row: a bottom sheet on a phone (against the
    bottom edge), a centred card on a desktop, with the name field focused and no aircraft-type
    field"""
    context, page = _open(new_context, server, viewport)
    try:
        _open_dialog(page, GAP_OPEN, GAP_DIALOG)
        box = page.locator(GAP_DIALOG).bounding_box()
        width, height = viewport["width"], viewport["height"]
        if width < 700:
            assert box["y"] + box["height"] >= height - 1 and box["width"] >= width - 2, box
        else:
            assert abs(box["x"] + box["width"] / 2 - width / 2) < 2, box
            assert abs(box["y"] + box["height"] / 2 - height / 2) < 4, box
            assert 300 <= box["width"] <= 640, box
        assert page.evaluate(
            "sel => document.activeElement === document.querySelector(sel)", GAP_NAME)
        assert page.locator(GAP_DIALOG + " select").count() == 0
        page.keyboard.press("Escape")
        page.locator(GAP_DIALOG).wait_for(state="hidden")
    finally:
        context.close()


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
                    TRANSAVIA + " .airlines-expand > summary",
                    TRANSAVIA + " .airlines-thumb", TRANSAVIA + " .airlines-row .row-menu__toggle",
                    GAP_OPEN):
                _settle(page, selector)
                _assert_hit_target(page, selector, "airlines %s %s" % (name, lang))
    finally:
        context.close()


def test_an_unidentified_row_is_one_compact_line_plus_its_button_on_a_phone(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        _settle(page, GAP_OPEN)
        row = page.locator(GAP + " .airlines-gap").bounding_box()
        button = page.locator(GAP_OPEN).bounding_box()
        assert row["height"] <= 130, row
        assert button["x"] + button["width"] <= VIEWPORT_MIN_SUPPORTED["width"], button
        assert not _assert_no_page_overflow(page, "gap", VIEWPORT_MIN_SUPPORTED["width"])
    finally:
        context.close()


def test_the_unidentified_prefix_is_a_compact_row_on_top_named_in_a_dialog(
        new_context, make_app_server):
    """the prefix is one compact row (prefix, what was seen, a Name it button): the name is typed
    in its dialog and Validate turns the row into an identified, hand-named one; no aircraft type
    is asked or stored"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        first = page.locator("tbody.airline-group").first
        assert "airline-group--gap" in first.get_attribute("class")
        assert "XYZ" in first.inner_text() and "5 views" in first.inner_text()
        assert page.locator(GAP + " .airlines-gap input").count() == 0
        assert page.locator(GAP_OPEN).inner_text() == "Name it"
        _open_dialog(page, GAP_OPEN, GAP_DIALOG)
        page.locator(GAP_NAME).fill("Xyz Wings")
        with page.expect_navigation():
            page.locator(GAP_DIALOG + " button[type=submit]").click()
        page.wait_for_function(
            "() => document.readyState === 'complete' && !document.querySelector("
            "'tbody.airline-group--gap')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(DIALOG + "[open]").count() == 0
        row = 'tbody.airline-group:has(.airlines-name--fixed:text-is("Xyz Wings"))'
        assert page.locator(row + " .airlines-pill").inner_text() == "Named by hand"
        assert page.locator(row + " .airlines-pill").is_visible()
        saved = manual_resolutions.load_manual_resolutions(server.state_dir)
        assert saved["XYZ"]["airline_name"] == "Xyz Wings"
        assert airline_default_types.load_default_types(server.state_dir) == {}
    finally:
        context.close()


def test_there_is_no_ignore_action_on_an_unidentified_prefix(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_dialog(page, GAP_OPEN, GAP_DIALOG)
        assert page.locator("body").inner_text().count("Ignore") == 0
        assert page.locator(GAP + " button[type=reset]").count() == 0
        page.locator(GAP_NAME).fill("Never Saved Air")
        page.locator(GAP_DIALOG + " a.modal__dismiss").click()
        page.locator(GAP_DIALOG).wait_for(state="hidden")
        assert "XYZ" not in manual_resolutions.load_manual_resolutions(server.state_dir)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_chevron_expands_the_aircraft_type_sub_rows(new_context, server, name, viewport):
    """one sub-row per type seen, every one editable: an A320 (a picture of its own: a tappable
    thumbnail, Change artwork) and a B738 (the default type's picture, Add artwork); a type
    with nothing to set or delete has no menu; a mouse click and the keyboard both toggle it"""
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
        # A type row keeps the height of the airline row: its picture column is one line,
        # whether the type has its own picture or shows the default type's.
        parent_art = page.locator(TRANSAVIA + " .airlines-row .airlines-cell--art")
        limit = parent_art.bounding_box()["height"] + 8
        for sub in (first, second):
            art = sub.locator(".airlines-cell--art")
            assert art.bounding_box()["height"] <= limit, (name, art.bounding_box(), limit)
        assert first.locator("th").inner_text().startswith("A320")
        assert first.locator("a.airlines-thumb").is_visible()
        assert first.locator(".row-menu__toggle").is_visible()
        assert "Uses the default type’s artwork" in second.inner_text()
        assert second.locator(".airlines-act").inner_text() == "Add artwork"
        assert first.locator(".airlines-act").inner_text() == "Change artwork"
        assert "Own artwork" in first.inner_text()
        assert second.locator("th").inner_text().startswith("B738")
        assert "2 views" in first.inner_text() and "1 view" in second.inner_text()
        page.locator(chevron).press("Enter")
        page.locator(subrows).first.wait_for(state="hidden")
        page.locator(chevron).press("Space")
        page.locator(subrows).first.wait_for(state="visible")
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_an_opened_airline_does_not_overlap_the_next_row(new_context, server, name, viewport):
    context, page = _open(new_context, server, viewport)
    try:
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        overlaps = page.evaluate("""g => {
            const rows = [...document.querySelectorAll(g + ' tr'), ...(
                document.querySelector(g).nextElementSibling
                    ? document.querySelector(g).nextElementSibling.querySelectorAll('tr') : [])];
            const boxes = rows.map(r => r.getBoundingClientRect()).filter(b => b.height > 0);
            const bad = [];
            for (let i = 1; i < boxes.length; i++)
                if (boxes[i].top < boxes[i - 1].bottom - 1) bad.push([i, boxes[i - 1], boxes[i]]);
            return bad.length;
        }""", TRANSAVIA)
        assert overlaps == 0
    finally:
        context.close()


def test_opening_an_airline_among_the_full_list_is_quick(new_context, server):
    """with every airline of the list on the page (36 curated plus the named ones) the type rows
    of one airline are fetched and shown within a generous bound, and only that airline's rows
    were added to the page"""
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        assert page.locator("tbody.airline-group").count() >= 36
        before = page.locator(".airlines-subrow").count()
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        started = page.evaluate("() => performance.now()")
        page.locator(chevron).click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        elapsed = page.evaluate("t => performance.now() - t", started)
        assert elapsed < 1500, elapsed
        assert page.locator(".airlines-subrow").count() == before + 2
    finally:
        context.close()


def test_renaming_opens_a_dialog_and_the_menu_resets_the_name(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        _open_rename(page)
        field = page.locator(FRANCE_FIELD)
        assert field.input_value() == "Air France"
        field.fill("Skyline Air")
        with page.expect_navigation():
            field.press("Enter")
        page.wait_for_function(
            "() => document.body.innerText.includes('Airline name saved')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        renamed = "#airline-skyline-air"
        assert page.locator(renamed + " .airlines-name").inner_text() == "Skyline Air"
        _settle(page, renamed + " .airlines-row .row-menu__toggle")
        page.locator(renamed + " .airlines-row .row-menu__toggle").click()
        items = page.locator(renamed + " .airlines-row .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == [
            "Rename", "Reset to the original name"]
        with page.expect_navigation():
            items.nth(1).click()
        page.wait_for_function(
            "() => document.readyState === 'complete' && !document.querySelector("
            "'#airline-skyline-air')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(FRANCE_NAME).inner_text() == "Air France"
    finally:
        context.close()


def test_a_refused_name_returns_with_the_dialog_open_on_that_airline(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        _open_rename(page)
        page.evaluate("() => document.querySelector('%s').removeAttribute('maxlength')" % FRANCE_FIELD)
        field = page.locator(FRANCE_FIELD)
        field.fill("x" * 101)
        with page.expect_navigation():
            field.press("Enter")
        page.wait_for_function(
            "() => location.search.includes('sheet=air-france')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator(FRANCE_DIALOG).wait_for(state="visible")
        page.wait_for_function(
            "sel => document.activeElement === document.querySelector(sel)", arg=FRANCE_FIELD,
            timeout=10000)
        assert page.locator(FRANCE_FIELD).input_value() == "Air France"
        assert page.locator(".toast").count() >= 1
    finally:
        context.close()


def test_the_artwork_uploads_through_the_real_routes_for_an_airline_and_a_type(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    png = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    requested = []
    page.on("request", lambda request: requested.append(request.url))
    try:
        form = page.locator('form[action^="/illustration/iberia-airlines.png"]')
        assert "csrf_token" not in form.get_attribute("action")
        assert form.locator('input[name="csrf_token"]').get_attribute("value")
        with page.expect_navigation():
            form.locator("input[type=file]").set_input_files(png)
        assert [url for url in requested if "csrf_token" in url] == []
        page.locator(".toast").first.wait_for(state="visible")
        assert os.path.isfile(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, "iberia-airlines.png"))
        page.wait_for_function(_SETTLED, timeout=15000)
        _settle(page, TRANSAVIA + " .airlines-expand > summary")
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        slot = 'form[action^="/illustration/transavia-france-a320.png"] input[type=file]'
        page.locator(slot).wait_for(state="attached")
        with page.expect_navigation():
            page.locator(slot).set_input_files(png)
        page.locator(".toast").first.wait_for(state="visible")
        assert os.path.isfile(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME,
            "transavia-france-a320.png"))
    finally:
        context.close()


def test_a_refused_picture_names_its_airline_and_the_page_opens_on_that_row(
        new_context, make_app_server, tmp_path):
    server = make_app_server(seed=_seed, fake_providers=True)
    bad = tmp_path / "notes.txt"
    bad.write_text("not an image")
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        form = page.locator('form[action^="/illustration/iberia-airlines.png"]')
        with page.expect_navigation():
            form.locator("input[type=file]").set_input_files(str(bad))
        page.locator(".toast").first.wait_for(state="visible")
        assert "Iberia Airlines: Couldn't use that file" in page.locator(".toast").first.inner_text()
        assert page.url.endswith("#airline-iberia-airlines")
        page.wait_for_function(
            "() => { const r = document.querySelector('#airline-iberia-airlines')"
            ".getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }",
            timeout=10000)
    finally:
        context.close()


def test_the_menu_holds_only_its_items_and_escape_closes_it(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        group = TRANSAVIA + " .airlines-row"
        toggle = group + " .row-menu__toggle"
        _settle(page, toggle)
        page.locator(toggle).click()
        items = page.locator(group + " .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Rename"]
        page.keyboard.press("Escape")
        page.wait_for_function(
            "sel => !document.querySelector(sel).open", arg=group + " details.row-menu", timeout=5000)
        # An airline with no aircraft-type row keeps an upload entry of its own.
        _settle(page, IBERIA_MENU)
        page.locator(IBERIA_MENU).click()
        items = page.locator(IBERIA + " .airlines-row .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Rename", "Change artwork"]
        with page.expect_file_chooser():
            items.nth(1).click()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_menu_has_even_padding_and_44px_items(new_context, server, name, viewport):
    context, page = _open(new_context, server, viewport)
    try:
        _settle(page, FRANCE_MENU)
        page.locator(FRANCE_MENU).click()
        items = page.locator(FRANCE + " .airlines-row .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        measured = page.evaluate("""g => {
            const panel = document.querySelector(g + ' .row-menu__panel').getBoundingClientRect();
            const boxes = [...document.querySelectorAll(g + ' .row-menu__panel .row-menu__item')]
                .map(e => e.getBoundingClientRect());
            return {heights: boxes.map(b => b.height),
                    top: boxes[0].top - panel.top, bottom: panel.bottom - boxes[boxes.length - 1].bottom,
                    left: boxes[0].left - panel.left, right: panel.right - boxes[0].right};
        }""", FRANCE + " .airlines-row")
        assert all(h >= 43.5 for h in measured["heights"]), measured
        edges = [measured[k] for k in ("top", "bottom", "left", "right")]
        assert max(edges) - min(edges) <= 6, measured
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_tapping_a_thumbnail_enlarges_the_artwork_of_the_airline_and_of_a_type(
        new_context, server, name, viewport):
    context, page = _open(new_context, server, viewport)
    try:
        thumb = TRANSAVIA + " .airlines-row a.airlines-thumb"
        _settle(page, thumb)
        page.locator(thumb).click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        assert "/illustration/transavia-france.png" in dialog.locator(".lightbox__image").get_attribute("src")
        assert dialog.locator(".lightbox__heading").inner_text() == "Transavia France"
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        sub_thumb = TRANSAVIA + " .airlines-subrow a.airlines-thumb"
        _settle(page, sub_thumb)
        page.locator(sub_thumb).click()
        dialog.wait_for(state="visible")
        assert "/illustration/transavia-france-a320.png" in dialog.locator(
            ".lightbox__image").get_attribute("src")
    finally:
        context.close()


_NAMES = VISIBLE_GROUPS + " .airlines-row .airlines-name--fixed"


def _visible_group_count_is(page, count):
    page.wait_for_function(
        "n => document.querySelectorAll('tbody.airline-group:not([hidden])').length === n",
        arg=count, timeout=5000)


def test_the_filter_finds_an_airline_by_name_type_or_prefix(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        field = page.locator("[data-filter-input]")
        total = page.locator("tbody.airline-group").count()
        for text, expected in (("tfv", ["Transavia France"]), ("b738", ["Transavia France"]),
                               ("tap portugal", ["TAP Air Portugal"])):
            field.fill(text)
            _visible_group_count_is(page, len(expected))
            assert page.locator(_NAMES).all_inner_texts() == expected, text
        field.fill("zzzz-nothing")
        _visible_group_count_is(page, 0)
        page.locator("[data-filter-empty]").wait_for(state="visible")
        field.fill("")
        _visible_group_count_is(page, total)
        page.locator("[data-filter-empty]").wait_for(state="hidden")
    finally:
        context.close()


def _chip(page, label):
    return page.locator("label.filter-chip", has_text=label).first


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_chips_filter_by_kind_and_clearing_restores_every_row(
        new_context, server, name, viewport):
    """the chips carry their counts: Unidentified shows the prefix rows, No artwork the airlines
    without a picture, Seen and Not seen yet split by sightings; All brings everything back"""
    context, page = _open(new_context, server, viewport)
    try:
        total = page.locator("tbody.airline-group").count()
        labels = page.locator(".filter-chip__text").all_inner_texts()
        assert labels[0] == "All (%d)" % total and labels[1] == "Unidentified (1)", labels
        seen = int(labels[3].split("(")[1].rstrip(")"))
        unseen = int(labels[4].split("(")[1].rstrip(")"))
        assert seen >= 1 and seen + unseen == total - 1, labels
        _chip(page, "Unidentified").click()
        _visible_group_count_is(page, 1)
        assert page.locator(GAP).is_visible()
        _chip(page, "Seen").click()
        _visible_group_count_is(page, seen)
        assert page.locator(TRANSAVIA).is_visible() and page.locator(GAP).is_hidden()
        _chip(page, "Not seen yet").click()
        _visible_group_count_is(page, unseen)
        assert page.locator(TRANSAVIA).is_hidden()
        _chip(page, "No artwork").click()
        assert "Lufthansa" in page.locator(_NAMES).all_inner_texts()
        _chip(page, "All").click()
        _visible_group_count_is(page, total)
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


def test_without_scripts_the_chevron_the_rename_dialog_and_the_upload_button_work(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/airlines/manage", viewport=VIEWPORT_DESKTOP,
            reduced_motion="reduce") as page:
        _settle(page, FRANCE_NAME)
        # Without a script the type rows come with the page's "show every
        # airline's types" view.
        with page.expect_navigation():
            page.get_by_role("link", name="Show the aircraft types of every airline").click()
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        upload = 'form[action^="/illustration/iberia-airlines.png"] .airlines-art__upload'
        assert page.locator(upload).is_hidden()
        page.locator(IBERIA_MENU).click()
        assert page.locator(upload).is_visible()
        page.locator(IBERIA_MENU).click()
        page.locator(FRANCE_MENU).click()
        page.locator(FRANCE + " .airlines-row .row-menu__panel a.row-menu__item").click()
        page.locator(FRANCE_FIELD).wait_for(state="visible")
        page.locator(FRANCE_FIELD).fill("Skyline Air")
        with page.expect_navigation():
            page.locator(FRANCE_DIALOG + " button[type=submit]").click()
        page.wait_for_url("**/airlines/manage?flash=airline_renamed")
        assert page.locator("#airline-skyline-air .airlines-name").inner_text() == "Skyline Air"


_CLIPPED_NAMES = (
    "() => [...document.querySelectorAll('tbody.airline-group:not([hidden]) .airlines-row"
    " .airlines-name--fixed')]"
    ".filter(n => n.scrollWidth > n.clientWidth + 1).map(n => n.textContent)")
_WRAPPED_CELLS = (
    "() => [...document.querySelectorAll('.airlines-row .airlines-cell--views,"
    " .airlines-row .airlines-cell--seen')].filter(td => {"
    " const tops = new Set();"
    " const walker = document.createTreeWalker(td, NodeFilter.SHOW_TEXT);"
    " for (let n = walker.nextNode(); n; n = walker.nextNode()) {"
    "  if (!n.textContent.trim() || n.parentElement.closest('.visually-hidden')) continue;"
    "  const range = document.createRange(); range.selectNodeContents(n);"
    "  for (const r of range.getClientRects()) if (r.width > 0) tops.add(Math.round(r.top)); }"
    " return tops.size > 1; }).map(td => td.innerText)")


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_on_a_desktop_no_airline_name_is_clipped_and_counts_stay_on_one_line(
        new_context, server, lang):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang)
    try:
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(VISIBLE_GROUPS).count() >= 30
        assert page.evaluate(_CLIPPED_NAMES) == []
        wrapped = page.evaluate(_WRAPPED_CELLS)
        assert wrapped == [], wrapped
    finally:
        context.close()


B738_ROW = TRANSAVIA + " .airlines-subrow:nth-child(3)"  # the airline row, A320, then B738
_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")


def _audit_actions(state_dir):
    from server import fleet_db
    conn = fleet_db.connect(state_dir)
    try:
        return [row["action"] for row in fleet_db.list_audit(conn, "all", 50, 0)]
    finally:
        conn.close()


def _expand_transavia(page):
    chevron = TRANSAVIA + " .airlines-expand > summary"
    _settle(page, chevron)
    page.locator(chevron).click()
    page.locator(B738_ROW).wait_for(state="visible")


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_type_row_is_given_a_picture_then_its_artwork_is_deleted(
        new_context, make_app_server, name, viewport):
    """a type that follows the default type's picture gets one through its one upload entry
    (Add artwork, then Change artwork); "Delete the artwork" in its menu removes it again and the
    row returns to the default type's picture; both are audited"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport)
    try:
        _expand_transavia(page)
        slot = os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME,
            "transavia-france-b737.png")
        assert not os.path.exists(slot)
        assert page.locator(B738_ROW + " .row-menu__toggle").count() == 1
        with page.expect_navigation():
            page.locator(B738_ROW + " .airlines-act input[type=file]").set_input_files(_PNG)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert os.path.isfile(slot)
        _expand_transavia(page)
        assert "Own artwork" in page.locator(B738_ROW).inner_text()
        assert page.locator(B738_ROW + " .airlines-act").inner_text() == "Change artwork"
        toggle = B738_ROW + " .row-menu__toggle"
        _settle(page, toggle)
        page.locator(toggle).click()
        delete = page.locator(B738_ROW + " .row-menu__panel button.row-menu__item", has_text="Delete the artwork")
        delete.wait_for(state="visible")
        with page.expect_navigation():
            delete.click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert not os.path.exists(slot)
        _expand_transavia(page)
        assert "Uses the default type’s artwork" in page.locator(B738_ROW).inner_text()
        assert page.locator(B738_ROW + " .airlines-act").inner_text() == "Add artwork"
        assert "airline.artwork_delete" in _audit_actions(server.state_dir)
    finally:
        context.close()


def test_the_type_menu_sets_the_default_type_and_deletes_only_an_uploaded_picture(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _expand_transavia(page)
        items = page.locator(B738_ROW + " .row-menu__panel .row-menu__item")
        page.locator(B738_ROW + " .row-menu__toggle").click()
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Set as default type"]
        page.keyboard.press("Escape")
        with page.expect_navigation():
            page.locator(B738_ROW + " .airlines-act input[type=file]").set_input_files(_PNG)
        page.wait_for_function(_SETTLED, timeout=15000)
        _expand_transavia(page)
        page.locator(B738_ROW + " .row-menu__toggle").click()
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Set as default type", "Delete the artwork"]
        with page.expect_navigation():
            items.nth(0).click()
        page.wait_for_function(_SETTLED, timeout=15000)
        _expand_transavia(page)
        star = B738_ROW + " .airlines-pill--star"
        assert page.locator(star).inner_text() == "Default type"
        assert airline_default_types.load_default_types(server.state_dir) == {
            "transavia-france": "B738"}
        # The airline row now shows the default type's code and its own picture.
        assert page.locator(TRANSAVIA + " .airlines-row .airlines-deftype").inner_text() == "B738"
        assert page.locator(TRANSAVIA + " .airlines-row .airlines-thumb__image").get_attribute(
            "src").startswith("/illustration/transavia-france-b737.png")
        page.locator(B738_ROW + " .row-menu__toggle").click()
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Remove as the default type", "Delete the artwork"]
        with page.expect_navigation():
            items.nth(1).click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert not os.path.exists(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME,
            "transavia-france-b737.png"))
        assert {"airline.default_type", "airline.artwork_delete"} <= set(
            _audit_actions(server.state_dir))
    finally:
        context.close()


def test_every_type_of_a_fully_identified_airline_is_editable(new_context, server):
    """Air France is a built-in airline with a name and a picture: none of its type rows is
    a dead end, each offers one upload entry"""
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        group = FRANCE
        chevron = group + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        subrows = page.locator(group + " .airlines-subrow")
        subrows.first.wait_for(state="visible")
        for index in range(subrows.count()):
            row = subrows.nth(index)
            assert row.locator(".airlines-act").count() == 1
            assert row.locator(".airlines-state").count() == 1
    finally:
        context.close()


def test_naming_a_prefix_is_audited(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_dialog(page, GAP_OPEN, GAP_DIALOG)
        page.locator(GAP_NAME).fill("Audit Air")
        with page.expect_navigation():
            page.locator(GAP_DIALOG + " button[type=submit]").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "airline.resolve" in _audit_actions(server.state_dir)
    finally:
        context.close()
