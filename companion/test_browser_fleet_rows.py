"""Real-browser checks of the Fleet page from 960px: the frame's detail groups (device and
version, the versions list, the wake interval and other settings, access, the other frames) are
summary rows with a chevron that open a dialog; the dialog is opaque, closes with Escape and the
settings dialog's Save persists the value and its Cancel restores it. Without scripts a row links
to its dialog and the dialog shows as a card. A phone keeps its sub-tabs and shows no summary row.

State is always waited for (settled page, an open dialog), never read right after an input."""
import pytest

import fleet_console_support as fx
from companion import auth
from server import device_config
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _set_ui_theme)

pytestmark = pytest.mark.browser

LAPTOP = {"width": 960, "height": 800}
ROW = "a.fleet-sum"
DIALOGS = ("dlg-fleet-device", "dlg-fleet-versions", "dlg-fleet-settings", "dlg-fleet-others")
LABELS = {
    "en": ["Device and version", "Version history", "Wake interval", "Access", "Other frames"],
    "fr": ["Appareil et version", "Historique des versions", "Intervalle de réveil", "Accès",
           "Autres cadres"]}
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", theme="light", **args):
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    context = new_context(viewport=viewport, **args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.live_id)
    page.locator("main").wait_for(state="visible")
    if args.get("java_script_enabled", True):
        page.wait_for_function(_SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        page.wait_for_function(_SETTLED, timeout=15000)
        if viewport["width"] >= 960:
            page.wait_for_function(_OWNS_CENTRE, arg=ROW, timeout=10000)
    return context, page, seed


def _open_dialog(page, dialog_id):
    page.locator("%s[href='#%s']" % (ROW, dialog_id)).click()
    page.wait_for_function(
        "id => document.getElementById(id).open", arg=dialog_id, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=15000)


@pytest.mark.parametrize("scheme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [LAPTOP, VIEWPORT_DESKTOP], ids=["960", "1280"])
def test_the_groups_are_summary_rows_that_open_opaque_dialogs(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page, seed = _open(new_context, app_server_in_process, viewport, lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, "fleet-rows", viewport["width"])
        rows = page.locator(ROW)
        assert [rows.nth(i).locator(".fleet-sum__label").inner_text()
                for i in range(rows.count())] == LABELS[lang]
        for index in range(rows.count()):
            box = rows.nth(index).bounding_box()
            assert box["height"] >= 44 and box["width"] >= 200, box
            assert rows.nth(index).locator(".fleet-sum__chevron").count() == 1
            assert rows.nth(index).locator(".fleet-sum__value").inner_text().strip()
        # The groups themselves are not on the page any more, only State and the rows.
        assert page.locator(".fleet-block--settings").is_hidden()
        assert page.locator("#wake-interval-s").is_hidden()
        access = "dlg-access-" + seed.live_id.lower().replace("_", "-")
        for dialog_id in DIALOGS + (access,):
            _open_dialog(page, dialog_id)
            opaque = page.evaluate(
                "id => { const d = document.getElementById(id); const s = getComputedStyle(d);"
                " const m = s.backgroundColor.match(/[\\d.]+/g).map(Number);"
                " const r = d.getBoundingClientRect();"
                " return {alpha: m.length > 3 ? m[3] : 1, blur: s.backdropFilter,"
                " left: r.left, right: r.right, top: r.top, bottom: r.bottom,"
                " vw: innerWidth, vh: innerHeight}; }", dialog_id)
            assert opaque["alpha"] == 1 and opaque["blur"] == "none", (dialog_id, opaque)
            assert opaque["left"] > 0 and opaque["right"] < opaque["vw"], (dialog_id, opaque)
            assert opaque["top"] >= 0 and opaque["bottom"] <= opaque["vh"], (dialog_id, opaque)
            page.keyboard.press("Escape")
            page.wait_for_function(
                "id => !document.getElementById(id).open", arg=dialog_id, timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("lang,save", [("en", "Save"), ("fr", "Enregistrer")])
def test_the_settings_dialog_saves_the_wake_interval(
        new_context, app_server_in_process, lang, save):
    context, page, _seed = _open(new_context, app_server_in_process, lang=lang)
    try:
        _open_dialog(page, "dlg-fleet-settings")
        field = page.locator("#wake-interval-s")
        field.wait_for(state="visible")
        assert field.input_value() == "600"
        field.fill("900")
        page.locator("#dlg-fleet-settings .modal__actions button[data-modal-submit]").click()
        page.wait_for_url("**/fleet?frame=*")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator("a.fleet-sum[href='#dlg-fleet-settings'] .fleet-sum__value"
                            ).inner_text() in ("Every 15 min", "Toutes les 15 minutes")
        page.reload()
        page.wait_for_function(_SETTLED, timeout=15000)
        _open_dialog(page, "dlg-fleet-settings")
        assert page.locator("#wake-interval-s").input_value() == "900"
        assert page.locator(
            "#dlg-fleet-settings .modal__actions button[data-modal-submit]").inner_text() == save
    finally:
        context.close()


def test_cancel_in_the_settings_dialog_restores_the_value_and_closes_it(
        new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process)
    try:
        _open_dialog(page, "dlg-fleet-settings")
        page.locator("#wake-interval-s").fill("1200")
        page.locator("#dlg-fleet-settings .modal__actions button[type=reset]").click()
        page.wait_for_function(
            "() => !document.getElementById('dlg-fleet-settings').open", timeout=10000)
        assert page.locator("[data-dirty-bar]").is_hidden()
        _open_dialog(page, "dlg-fleet-settings")
        assert page.locator("#wake-interval-s").input_value() == "600"
    finally:
        context.close()


def test_a_change_left_in_the_dialog_shows_the_unsaved_changes_bar_and_it_saves(
        new_context, app_server_in_process):
    context, page, _seed = _open(new_context, app_server_in_process)
    try:
        _open_dialog(page, "dlg-fleet-settings")
        page.locator("#wake-interval-s").fill("1200")
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.getElementById('dlg-fleet-settings').open", timeout=10000)
        bar = page.locator("[data-dirty-bar]")
        bar.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.wait_for_function(_OWNS_CENTRE, arg="[data-dirty-bar] .dirty-bar__save", timeout=10000)
        page.locator("[data-dirty-bar] .dirty-bar__save").click()
        page.wait_for_url("**/fleet?frame=*")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator("a.fleet-sum[href='#dlg-fleet-settings'] .fleet-sum__value"
                            ).inner_text() == "Every 20 min"
    finally:
        context.close()


def test_the_other_frames_dialog_lists_them_and_keeps_their_actions(
        new_context, app_server_in_process):
    context, page, seed = _open(new_context, app_server_in_process)
    try:
        _open_dialog(page, "dlg-fleet-others")
        rows = page.locator("#dlg-fleet-others li.entity-row")
        assert rows.count() == 2
        rows.filter(has_text="Attic").locator("summary.row-menu__toggle").click()
        item = rows.filter(has_text="Attic").locator(".row-menu__item")
        item.wait_for(state="visible")
        assert item.inner_text() == "Re-activate"
    finally:
        context.close()


def test_without_scripts_a_row_links_to_its_dialog_and_the_page_save_bar_saves(
        new_context, app_server_in_process):
    context, page, _seed = _open(
        new_context, app_server_in_process, java_script_enabled=False)
    try:
        page.locator("%s[href='#dlg-fleet-settings']" % ROW).click()
        page.locator("#dlg-fleet-settings").wait_for(state="visible")
        field = page.locator("#wake-interval-s")
        field.wait_for(state="visible")
        field.fill("900")
        # The page's own Save bar is the one submit control of the form, and shows without script.
        page.locator("[data-dirty-bar] button[type=submit]").click()
        page.wait_for_url("**/fleet?frame=*")
        assert page.locator("a.fleet-sum[href='#dlg-fleet-settings'] .fleet-sum__value"
                            ).inner_text() == "Every 15 min"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, {"width": 390, "height": 844}],
                         ids=["360", "390"])
def test_a_phone_keeps_its_tabs_and_shows_no_summary_row(
        new_context, app_server_in_process, viewport):
    context, page, _seed = _open(new_context, app_server_in_process, viewport)
    try:
        assert page.locator("nav.fleet-tabs").is_visible()
        assert page.locator(ROW).count() == 5
        assert all(not page.locator(ROW).nth(i).is_visible() for i in range(5))
        assert page.locator(".fleet-block--state").first.is_visible()
        page.locator("nav.fleet-tabs a", has_text="Settings").click()
        page.wait_for_url("**tab=settings")
        page.locator("#wake-interval-s").wait_for(state="visible")
        assert page.locator("#dlg-fleet-settings .modal__head").is_hidden()
        assert page.locator("#dlg-fleet-settings .modal__actions").is_hidden()
    finally:
        context.close()


def test_the_frame_and_system_addresses_still_select_their_view(
        new_context, app_server_in_process):
    context, page, seed = _open(new_context, app_server_in_process)
    try:
        assert page.locator(".fleet-detail-head h2").inner_text()
        page.goto(app_server_in_process.base_url() + "/fleet?view=system")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(ROW).count() == 0
        assert page.locator(".fleet-blocks--system").is_visible()
    finally:
        context.close()
