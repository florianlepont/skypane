"""Real-browser checks of the Fleet page from 960px: one centred column of section cards (State,
Device and version, Settings, Access, Other frames), each present once and in that order at 1280
and 1440px, every fact shown once, every setting edited inline (no dialog) and saved through the
page's unsaved-changes bar, the version history collapsed in a native disclosure, and Retire this
frame as the only confirmation dialog. A phone keeps its State / Settings / Access tabs.

State is always waited for (settled page, an open dialog), never read right after an input."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    RELEASE_SEED_AVAILABLE_VERSION, RELEASE_SEED_RUNNING_VERSION, UI_THEMES_EXPLICIT,
    VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme,
    seed_two_releases)
from server import device_config

pytestmark = pytest.mark.browser

DESKTOP_1280 = {"width": 1280, "height": 900}
DESKTOP_1440 = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}
HEADINGS = {
    "en": ["State", "Device and version", "Settings", "Access", "Other frames (2)"],
    "fr": ["État", "Appareil et version", "Réglages", "Accès", "Autres cadres (2)"]}
MODEL = "XIAO ePaper EE02 13.3in Spectra 6"
COLUMN = ".fleet-frame"
BAR = "[data-dirty-bar]"
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_SECTIONS = (
    "() => [...document.querySelectorAll('.fleet-frame .fleet-blocks > section.fleet-block')]"
    ".filter(s => s.getClientRects().length > 0).map(s => {"
    " const b = s.getBoundingClientRect();"
    " return {title: s.querySelector(':scope > h2.section-label').textContent.trim(),"
    "  x: b.left, y: b.top, w: b.width, right: b.right}; })")


def _open(new_context, server, viewport=DESKTOP_1280, lang="en", theme="light",
          query="", releases=False, **args):
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    if releases:
        seed_two_releases(server.state_dir)
    context = new_context(viewport=viewport, **args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.live_id + query)
    page.locator("main").wait_for(state="visible")
    if args.get("java_script_enabled", True):
        page.wait_for_function(_SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        page.wait_for_function(_SETTLED, timeout=15000)
        page.wait_for_function(_OWNS_CENTRE, arg=COLUMN + " h2.section-label", timeout=10000)
    return context, page, seed


@pytest.mark.parametrize("scheme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [DESKTOP_1280, DESKTOP_1440], ids=["1280", "1440"])
def test_the_sections_are_one_content_wide_column_present_once_and_in_order(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, _seed = _open(new_context, app_server_in_process, viewport, lang, scheme)
    where = "fleet-sections/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        sections = page.evaluate(_SECTIONS)
        assert [s["title"] for s in sections] == HEADINGS[lang], where
        for upper, lower in zip(sections, sections[1:]):
            assert abs(lower["x"] - upper["x"]) < 1 and lower["y"] > upper["y"], (where, sections)
            assert abs(lower["w"] - upper["w"]) < 1, (where, sections)
        assert sections[0]["w"] >= 640, (where, sections[0])
        # The column runs the width of the page's content: it starts where the title starts and
        # ends where the frame button ends, like every other page.
        column = page.locator(COLUMN).bounding_box()
        title = page.locator("main h1").first.bounding_box()
        button = page.locator("details.frame-menu > summary").bounding_box()
        assert abs(column["x"] - title["x"]) <= 2, (where, column, title)
        assert abs(column["x"] + column["width"] - (button["x"] + button["width"])) <= 2, (
            where, column, button)
        # No summary row and no tab bar of sub-tabs: the groups are on the page.
        assert page.locator("a.fleet-sum").count() == 0
        assert page.locator("nav.fleet-tabs").is_hidden()
        assert page.locator("#wake-interval-s").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [DESKTOP_1280, DESKTOP_1440], ids=["1280", "1440"])
def test_no_fact_is_shown_twice_in_the_column(new_context, app_server_in_process, viewport):
    context, page, _seed = _open(
        new_context, app_server_in_process, viewport, releases=True)
    try:
        text = page.locator(COLUMN).inner_text()
        assert text.count(MODEL) == 1, text
        # The frame's name is the frame button's label above the column, not repeated in it.
        assert text.count("Orly frame") == 0, text
        for heading in ("Wake interval", "Diagnostic LED"):
            assert page.locator(COLUMN).get_by_role("heading", name=heading).count() == 1
        # The owner is named once (the Reassign picker's options are choices, not facts).
        owners = page.locator(COLUMN + " .co-manager__email").all_inner_texts()
        assert owners == [fx.ADMIN_EMAIL], owners
        # A firmware version is named once as a fact (the Install button's label repeats the
        # version it installs, and the seeded release note quotes it).
        facts = page.locator(COLUMN + " .mono:not(.update-table .mono)").all_inner_texts()
        for version in (RELEASE_SEED_RUNNING_VERSION, RELEASE_SEED_AVAILABLE_VERSION):
            assert facts.count(version) == 1, (version, facts)
        # The card names it once as what the frame runs and the version table once as a row.
        assert text.count(RELEASE_SEED_RUNNING_VERSION) == 2, text
    finally:
        context.close()


def test_the_version_history_is_a_table_with_the_action_in_every_row(
        new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process, releases=True)
    try:
        assert page.locator("details.update-all").count() == 0
        heading = page.locator(".update-versions .text-heading")
        assert heading.inner_text().split()[0] == "Versions"
        assert page.locator(".update-versions__count").inner_text().strip() == "2"
        rows = page.locator("table.update-table tbody tr")
        assert rows.count() == 2 and rows.first.is_visible()
        running, available = (rows.nth(0), rows.nth(1))
        # The running version has no action; the newer one is installable without opening anything.
        assert running.locator("form").count() == 0
        button = available.locator("form button[type=submit]")
        assert button.is_visible() and button.inner_text() == "Install"
        assert button.bounding_box()["height"] >= 44 - 0.5
        # The cells of a row line up on one line: version, date and action share a band.
        tops = [r.bounding_box() for r in (
            available.locator("th"), available.locator("td.update-table__when"), button)]
        centres = [box["y"] + box["height"] / 2 for box in tops]
        assert max(centres) - min(centres) < 30, centres
    finally:
        context.close()


def test_the_version_table_headings_are_in_french(new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process, lang="fr", releases=True)
    try:
        heads = page.locator("table.update-table thead th").all_inner_texts()
        assert [h.strip() for h in heads[:3]] == ["Version", "État", "Sortie"]
        assert page.locator("table.update-table tbody button").last.inner_text() == "Installer"
    finally:
        context.close()


def test_settings_are_edited_inline_and_saved_through_the_bar(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server)
    try:
        field = page.locator("#wake-interval-s")
        field.fill("900")
        page.locator(BAR).wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        # Editing never opens a dialog.
        assert page.locator("dialog[open]").count() == 0
        page.wait_for_function(_OWNS_CENTRE, arg=BAR + " .dirty-bar__save", timeout=10000)
        page.locator(BAR + " .dirty-bar__save").click()
        page.wait_for_function(
            "() => { const f = document.querySelector('#wake-interval-s');"
            " return document.readyState === 'complete' && !!f && f.value === '900'; }",
            timeout=15000)
        assert device_config.load_device_config(server.state_dir)["wake_interval_s"] == 900
    finally:
        context.close()


def test_retire_this_frame_is_the_only_dialog_and_asks_before_acting(
        new_context, app_server_in_process):
    server = app_server_in_process
    context = None
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=DESKTOP_1280)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
        page.wait_for_function(_SETTLED, timeout=15000)
        page.wait_for_function(_OWNS_CENTRE, arg=COLUMN + " h2.section-label", timeout=10000)
        # Every other control of the page is inline: nothing but the confirmation is a dialog
        # that can open from the Access section.
        assert page.locator("dialog[open]").count() == 0
        link = page.locator("a.fleet-retire__link")
        assert link.count() == 1
        link.click()
        page.wait_for_function(
            "() => document.querySelectorAll('dialog[open]').length === 1", timeout=10000)
        dialog = page.locator("dialog[open]")
        assert "Retire" in dialog.inner_text()
        assert dialog.locator("button[type=submit]").count() == 1
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('dialog[open]')", timeout=10000)
    finally:
        context.close()


def test_the_served_frame_offers_no_retire_row(new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process)
    try:
        assert page.locator("a.fleet-retire__link").count() == 0
    finally:
        context.close()


def test_the_sections_work_without_scripts(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(
        new_context, server, java_script_enabled=False)
    try:
        assert page.locator("#wake-interval-s").is_visible()
        assert page.locator("details.update-all").count() in (0, 1)
        page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
        link = page.locator("a.fleet-retire__link")
        link.click()
        assert page.locator("dialog.modal:target, dialog.modal[open]").first.is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_phone_keeps_its_three_tabs_with_the_same_sections(
        new_context, app_server_in_process, lang):
    context, page, _seed = _open(
        new_context, app_server_in_process, PHONE, lang)
    try:
        assert page.locator("nav.fleet-tabs").is_visible()
        labels = {"en": ["State", "Settings", "Access"], "fr": ["État", "Réglages", "Accès"]}
        assert page.locator("nav.fleet-tabs a span").all_inner_texts() == labels[lang]
        shown = page.evaluate(_SECTIONS)
        # State tab: State, Device and version, and the pending and retired frames.
        assert [s["title"] for s in shown] == [
            HEADINGS[lang][0], HEADINGS[lang][1], HEADINGS[lang][4]]
        assert not _assert_no_page_overflow(page, "phone-tabs", PHONE["width"])
        page.locator("nav.fleet-tabs a").nth(2).click()
        page.wait_for_url("**tab=access")
        page.wait_for_function(_SETTLED, timeout=15000)
        shown = page.evaluate(_SECTIONS)
        assert [s["title"] for s in shown] == [HEADINGS[lang][3]]
    finally:
        context.close()


def test_the_column_fits_at_360(new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED)
    try:
        assert not _assert_no_page_overflow(page, "sections-360", 360)
    finally:
        context.close()
