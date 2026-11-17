#!/usr/bin/env python3
"""Real-browser checks of the Console Airlines editor table: at 360 and 1280 px, in English and
French and in both themes, nothing overflows and every control (the name field, the chevron, the
artwork, the "..." menu, "Name it") is at least 44 px and owns its centre; the chevron expands
the aircraft-type sub-rows (a type with its own artwork offers Replace, any other says it uses
the airline's artwork); renaming saves on change through the real route and the "..." menu resets
it; tapping a thumbnail enlarges it and "Change artwork" in the "..." menu uploads through the
real routes; the "..." menu holds only its items and Escape closes it; the filter finds an airline by name, type or prefix; an unidentified prefix is
a highlighted row at the top. With scripts blocked the chevron, the Save button and the Upload
button still work.

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
GAP_NAME = GAP + ' input[name="airline_name"]'
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


def test_the_resolve_fields_are_short_and_share_a_row_on_a_wide_screen(new_context, server):
    """the inline resolve row keeps its name field near 280px and the type select near 180px
    (never stretched across the row), the two side by side with the buttons after them"""
    context, page = _open(new_context, server, VIEWPORTS[-1][1], "en")
    try:
        page.wait_for_function(_SETTLED, timeout=15000)
        _settle(page, GAP_NAME)
        boxes = page.evaluate("""args => {
            const r = s => document.querySelector(s).getBoundingClientRect();
            return {name: r(args[0]), select: r(args[1]), ok: r(args[2])};
        }""", [GAP_NAME, GAP + " select", GAP + " .airlines-resolve__actions button[type=submit]"])
        assert 200 <= boxes["name"]["width"] <= 281, boxes
        assert 120 <= boxes["select"]["width"] <= 181, boxes
        assert abs(boxes["name"]["top"] - boxes["select"]["top"]) < 2, boxes
        assert boxes["select"]["right"] <= boxes["ok"]["left"] + 1, boxes
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
                    FRANCE_NAME, TRANSAVIA + " .airlines-expand > summary",
                    TRANSAVIA + " .airlines-thumb", TRANSAVIA + " .airlines-row .row-menu__toggle",
                    GAP_NAME, GAP + " select", GAP + " .airlines-resolve__actions button[type=submit]",
                    GAP + " .airlines-resolve__actions button[type=reset]"):
                _settle(page, selector)
                _assert_hit_target(page, selector, "airlines %s %s" % (name, lang))
    finally:
        context.close()


def test_the_unidentified_prefix_is_a_highlighted_row_on_top_resolved_in_place(
        new_context, make_app_server):
    """the prefix is named in its own row (name, aircraft type, Validate): saving turns it into
    an identified, hand-named row and no dialog opens"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        first = page.locator("tbody.airline-group").first
        assert "airline-group--gap" in first.get_attribute("class")
        assert "XYZ" in first.inner_text()
        assert page.locator("a.airlines-name-it").count() == 0
        _settle(page, GAP_NAME)
        page.locator(GAP_NAME).fill("Xyz Wings")
        page.locator(GAP + " select").select_option("A320")
        with page.expect_navigation():
            page.locator(GAP + " .airlines-resolve__actions button[type=submit]").click()
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
        assert airline_default_types.load_default_types(server.state_dir) == {"xyz-wings": "A320"}
    finally:
        context.close()


def test_ignore_clears_the_row_without_saving(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _settle(page, GAP_NAME)
        page.locator(GAP_NAME).fill("Never Saved Air")
        page.locator(GAP + " .airlines-resolve__actions button[type=reset]").click()
        page.wait_for_function(
            "sel => document.querySelector(sel).value === ''", arg=GAP_NAME, timeout=5000)
        assert "XYZ" not in manual_resolutions.load_manual_resolutions(server.state_dir)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_chevron_expands_the_aircraft_type_sub_rows(new_context, server, name, viewport):
    """one sub-row per type seen, every one editable: an A320 (a picture of its own: a tappable
    thumbnail) and a B738 (the airline's picture by default, with a Customise action); each has
    its own "..." menu; a mouse click and the keyboard both toggle it"""
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
        # whether the type has its own picture or shows the airline's.
        parent_art = page.locator(TRANSAVIA + " .airlines-row .airlines-cell--art")
        limit = parent_art.bounding_box()["height"] + 8
        for sub in (first, second):
            art = sub.locator(".airlines-cell--art")
            assert art.bounding_box()["height"] <= limit, (name, art.bounding_box(), limit)
        assert first.locator("th").inner_text().startswith("A320")
        assert first.locator("a.airlines-thumb").is_visible()
        assert first.locator(".row-menu__toggle").is_visible()
        assert second.locator(".row-menu__toggle").is_visible()
        assert "Same as the airline" in second.inner_text()
        assert second.locator(".airlines-act").inner_text() == "Customise"
        assert "Own artwork" in first.inner_text()
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
        _settle(page, renamed + " .airlines-row .row-menu__toggle")
        page.locator(renamed + " .airlines-row .row-menu__toggle").click()
        items = page.locator(renamed + " .airlines-row .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == [
            "Change artwork", "Back to the default", "Delete the illustration",
            "Reset to the original name"]
        with page.expect_navigation():
            items.nth(3).click()
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
    requested = []
    page.on("request", lambda request: requested.append(request.url))
    try:
        form = page.locator('form[action^="/illustration/air-france.png"]')
        assert "csrf_token" not in form.get_attribute("action")
        assert form.locator('input[name="csrf_token"]').get_attribute("value")
        with page.expect_navigation():
            form.locator("input[type=file]").set_input_files(png)
        assert [url for url in requested if "csrf_token" in url] == []
        page.locator(".toast").first.wait_for(state="visible")
        assert os.path.isfile(os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, "air-france.png"))
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
        form = page.locator('form[action^="/illustration/transavia-france.png"]')
        with page.expect_navigation():
            form.locator("input[type=file]").set_input_files(str(bad))
        page.locator(".toast").first.wait_for(state="visible")
        assert "Transavia France: Couldn't use that file" in page.locator(".toast").first.inner_text()
        assert page.url.endswith("#airline-transavia-france")
        page.wait_for_function(
            "() => { const r = document.querySelector('#airline-transavia-france')"
            ".getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }",
            timeout=10000)
    finally:
        context.close()


def test_the_menu_holds_only_change_artwork_and_escape_closes_it(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        group = TRANSAVIA + " .airlines-row"
        toggle = group + " .row-menu__toggle"
        _settle(page, toggle)
        page.locator(toggle).click()
        items = page.locator(group + " .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == ["Change artwork"]
        page.keyboard.press("Escape")
        page.wait_for_function(
            "sel => !document.querySelector(sel).open", arg=group + " details.row-menu", timeout=5000)
        page.locator(toggle).click()
        items.first.wait_for(state="visible")
        with page.expect_file_chooser():
            items.first.click()
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
        # Without a script the type rows come with the page's "show every
        # airline's types" view.
        with page.expect_navigation():
            page.get_by_role("link", name="Show the aircraft types of every airline").click()
        chevron = TRANSAVIA + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        page.locator(TRANSAVIA + " .airlines-subrow").first.wait_for(state="visible")
        save = 'form.airlines-name:has(input[value="Air France"]) .airlines-name__save'
        upload = 'form[action^="/illustration/air-france.png"] .airlines-art__upload'
        assert page.locator(save).is_visible()
        assert page.locator(upload).is_hidden()
        page.locator('tbody.airline-group:has(input[value="Air France"]) .airlines-row .row-menu__toggle').click()
        assert page.locator(upload).is_visible()
        page.locator(FRANCE_NAME).fill("Skyline Air")
        with page.expect_navigation():
            page.locator(save).click()
        page.wait_for_url("**/airlines/manage?flash=airline_renamed")
        assert page.locator('.airlines-name input[value="Skyline Air"]').count() == 1


_CLIPPED_NAMES = (
    "() => [...document.querySelectorAll('tbody.airline-group:not([hidden]) .airlines-row"
    " .airlines-name input[name=\"airline_name\"]')]"
    ".filter(i => i.scrollWidth > i.clientWidth + 1).map(i => i.value)")
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
def test_a_type_row_is_customised_then_deleted_back_to_the_default(
        new_context, make_app_server, name, viewport):
    """a type that follows the airline's picture can be given one of its own; "Back to the
    default" removes it again and the row returns to "Same as the airline"; both are audited"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport)
    try:
        _expand_transavia(page)
        slot = os.path.join(
            server.state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME,
            "transavia-france-b737.png")
        assert not os.path.exists(slot)
        with page.expect_navigation():
            page.locator(B738_ROW + " .airlines-act input[type=file]").set_input_files(_PNG)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert os.path.isfile(slot)
        _expand_transavia(page)
        assert "Own artwork" in page.locator(B738_ROW).inner_text()
        revert = B738_ROW + " .airlines-act"
        _settle(page, revert)
        assert page.locator(revert).inner_text() == "Back to the default"
        with page.expect_navigation():
            page.locator(revert).click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert not os.path.exists(slot)
        _expand_transavia(page)
        assert "Same as the airline" in page.locator(B738_ROW).inner_text()
        assert page.locator(B738_ROW + " .airlines-act").inner_text() == "Customise"
        assert "airline.artwork_delete" in _audit_actions(server.state_dir)
    finally:
        context.close()


def test_the_menu_deletes_an_uploaded_artwork_and_stars_the_default_type(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _expand_transavia(page)
        with page.expect_navigation():
            page.locator(B738_ROW + " .airlines-act input[type=file]").set_input_files(_PNG)
        page.wait_for_function(_SETTLED, timeout=15000)
        _expand_transavia(page)
        page.locator(B738_ROW + " .row-menu__toggle").click()
        items = page.locator(B738_ROW + " .row-menu__panel .row-menu__item")
        items.first.wait_for(state="visible")
        assert items.all_inner_texts() == [
            "Change artwork", "Back to the default", "Set as the default type",
            "Delete the illustration"]
        with page.expect_navigation():
            items.nth(2).click()
        page.wait_for_function(_SETTLED, timeout=15000)
        _expand_transavia(page)
        star = B738_ROW + " .airlines-pill--star"
        assert page.locator(star).inner_text() == "Default type"
        assert airline_default_types.load_default_types(server.state_dir) == {
            "transavia-france": "B738"}
        page.locator(B738_ROW + " .row-menu__toggle").click()
        items.first.wait_for(state="visible")
        assert "Remove as the default type" in items.all_inner_texts()
        with page.expect_navigation():
            items.nth(3).click()
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
    a dead end, each offers Customise (or its own picture) and a menu"""
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        group = 'tbody.airline-group:has(input[value="Air France"])'
        chevron = group + " .airlines-expand > summary"
        _settle(page, chevron)
        page.locator(chevron).click()
        subrows = page.locator(group + " .airlines-subrow")
        subrows.first.wait_for(state="visible")
        assert subrows.count() >= 1
        for index in range(subrows.count()):
            row = subrows.nth(index)
            assert row.locator(".row-menu__toggle").count() == 1
            assert "Uses the airline’s artwork" not in row.inner_text()
            assert row.locator(".airlines-state").count() == 1
    finally:
        context.close()


def test_naming_a_prefix_is_audited(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _settle(page, GAP_NAME)
        page.locator(GAP_NAME).fill("Audit Air")
        with page.expect_navigation():
            page.locator(GAP + " .airlines-resolve__actions button[type=submit]").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "airline.resolve" in _audit_actions(server.state_dir)
    finally:
        context.close()
