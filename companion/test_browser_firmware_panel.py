"""Browser checks for the Fleet device page's "Device and version" panel: the
summary of what is on the frame, the one update card, the flat version history
and its release-notes disclosure, at phone and desktop widths, in both
languages and both themes, with realistic data.

Real Playwright browser throughout (companion/test_suite_guards.py's
behaviour-over-source rule). The panel is display only: the install and
revert POST flow is covered by companion/test_browser_update.py.
"""
import functools
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login
from server import atomic_io
from server import firmware_registry as fr
from skypane_fw_image import build_image

pytestmark = pytest.mark.browser

FLEET_ROUTE = "/fleet"
WIDTHS = (360, 1280)
THEMES = ("light", "dark")
LANGS = ("en", "fr")

# Version, age in days, number of notes: five releases, the frame on the fourth.
_HISTORY = (
    ("fw-v1.0.0", 45, 28), ("fw-v1.0.1", 45, 1), ("fw-v1.0.2", 44, 1),
    ("fw-v1.0.3", 9, 4), ("fw-v1.0.4", 3, 1),
)
_RELEASE_TITLE = "Plane screen design exploration (DRAFT - do not merge)"


def _seed_history(state_dir, running="fw-v1.0.3", count=5):
    """`count` releases (the oldest of _HISTORY dropped first) with `running`
    reported by the frame and installed one day ago."""
    os.makedirs(str(state_dir), exist_ok=True)
    now = datetime.now(timezone.utc)
    for index, (version, age_days, note_count) in enumerate(_HISTORY):
        if index < len(_HISTORY) - count:
            continue
        # An hour apart so releases of one day keep a stable order.
        released = (now - timedelta(days=age_days) + timedelta(hours=index)).replace(
            microsecond=0).isoformat()
        notes = ["Note %d of %s" % (n, version) for n in range(note_count)]
        if version == "fw-v1.0.4":
            notes = [_RELEASE_TITLE]
        image_path = os.path.join(str(state_dir), version + ".bin")
        image_bytes = build_image(version)
        with open(image_path, "wb") as fh:
            fh.write(image_bytes)
        fr.publish_release(str(state_dir), {
            "version": version, "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "size": len(image_bytes), "released_at": released, "commit": "a" * 40,
            "hardware_type": fr.hardware.LEGACY_KEY, "notes": notes,
        }, image_path, now=released)
    registry = fr.load_registry(str(state_dir))
    for release in registry["releases"]:
        if release["version"] == running:
            release["installed_at"] = [
                (now - timedelta(days=1)).replace(microsecond=0).isoformat()]
    fr._save_registry(str(state_dir), registry)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {"dev1": {
            "fw_version": running, "reported_at": now.replace(microsecond=0).isoformat(),
            "events": []}},
    }
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(device_report))


_SCENARIOS = {
    "update": _seed_history,
    "current": functools.partial(_seed_history, running="fw-v1.0.4"),
    "single": functools.partial(_seed_history, running="fw-v1.0.4", count=1),
}


@pytest.fixture(scope="module")
def servers(module_app_server_factory):
    return {name: module_app_server_factory(seed=seed) for name, seed in _SCENARIOS.items()}


def open_panel(new_context, server, width, lang, theme):
    """The Fleet page of the seeded frame, settled; returns (context, page)."""
    context = new_context(
        viewport={"width": width, "height": 900}, color_scheme=theme, reduced_motion="reduce")
    page = context.new_page()
    base_url = server.base_url()
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    _login(page, base_url)
    page.goto(base_url + FLEET_ROUTE)
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_selector(".fleet-block--device")
    return context, page


def no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 0.5")


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
def test_summary_names_what_is_on_the_frame_and_its_state(
        new_context, servers, width, lang, theme):
    """The panel opens with what the frame runs (label, large monospace version, when it was
    installed and the model) and one state chip on the right: an update is on offer, or the
    frame is up to date. The model is no longer a row of its own."""
    labels = {
        "en": ("On the frame", "Update available", "Up to date", "Installed"),
        "fr": ("Sur le cadre", "Mise à jour disponible", "À jour", "Installée"),
    }[lang]
    for scenario, chip_text in (("update", labels[1]), ("current", labels[2])):
        context, page = open_panel(new_context, servers[scenario], width, lang, theme)
        try:
            where = "%s %dpx/%s/%s" % (scenario, width, lang, theme)
            summary = page.locator(".fleet-block--device .update-sum")
            assert summary.count() == 1 and summary.is_visible(), where
            assert summary.locator(".update-sum__label").text_content().strip() == labels[0]
            version = summary.locator(".update-sum__version")
            assert version.inner_text().strip() == (
                "fw-v1.0.3" if scenario == "update" else "fw-v1.0.4")
            style = version.evaluate(
                "el => { const s = getComputedStyle(el);"
                " return [parseFloat(s.fontSize), s.fontFamily]; }")
            assert style[0] >= 19, "version too small at %s: %r" % (where, style)
            assert "mono" in style[1].lower(), "version not monospace at %s" % where
            meta = summary.locator(".update-sum__meta").inner_text()
            assert labels[3] in meta and "XIAO" in meta, "%s: %r" % (where, meta)
            chip = summary.locator(".banner__pill")
            assert chip.inner_text().strip() == chip_text, where
            version_box, chip_box = version.bounding_box(), chip.bounding_box()
            if width >= 1280:
                assert chip_box["x"] > version_box["x"] + version_box["width"], where
            assert page.locator(".fleet-block__fact").count() == 0, where
            assert no_horizontal_overflow(page), "overflow at %s" % where
            colours = chip.evaluate(
                "el => { const s = getComputedStyle(el);"
                " return [s.color, s.backgroundColor]; }")
            assert colours[0] != colours[1], where
        finally:
            context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
def test_one_update_card_with_one_install_button_when_an_update_is_offered(
        new_context, servers, width, lang, theme):
    """An offered update is one card: version and release age, the release title without the
    raw GitHub draft text, and the only Install button of the panel (the list row carries
    none). The button is a full-width 44px target on a phone. A frame that is up to date has
    no card at all."""
    install = {"en": "Install fw-v1.0.4", "fr": "Installer fw-v1.0.4"}[lang]
    released = {"en": "Released", "fr": "Sortie"}[lang]
    context, page = open_panel(new_context, servers["update"], width, lang, theme)
    try:
        where = "%dpx/%s/%s" % (width, lang, theme)
        card = page.locator(".fleet-block--device .update-offer")
        assert card.count() == 1 and card.is_visible(), where
        title = card.locator(".update-offer__title")
        assert "fw-v1.0.4" in title.inner_text() and released in title.inner_text(), where
        assert card.locator("time").count() == 1, where
        note = card.locator(".update-offer__note").inner_text()
        assert note == "Plane screen design exploration", (where, note)
        assert "DRAFT" not in card.inner_text(), where
        buttons = page.locator(
            'main form[action="/update/install"] input[value="fw-v1.0.4"] ~ button')
        assert buttons.count() == 1, "one Install button for the offered version at %s" % where
        button = card.locator("form button[type=submit]")
        assert button.inner_text().strip() == install, where
        box = button.bounding_box()
        assert box["height"] >= 44 - 0.5, where
        if width <= 360:
            card_box = card.bounding_box()
            assert box["width"] >= card_box["width"] - 2 * 24 - 1, (
                "button not full width at %s: %r in %r" % (where, box, card_box))
        assert box["x"] >= -0.5 and box["x"] + box["width"] <= width + 0.5, where
        assert no_horizontal_overflow(page), "overflow at %s" % where
    finally:
        context.close()
    for scenario in ("current", "single"):
        context, page = open_panel(new_context, servers[scenario], width, lang, theme)
        try:
            assert page.locator(".fleet-block--device .update-offer").count() == 0
            assert page.locator("main form[action='/update/install']").count() == (
                0 if scenario == "single" else 4)
        finally:
            context.close()


_PROBE_ROWS = """() => [...document.querySelectorAll('.fleet-block--device .update-item')].map((li) => {
  const rect = (el) => { const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
  const version = li.querySelector('.update-item__version');
  const range = document.createRange();
  range.selectNodeContents(version);
  const button = li.querySelector('form button[type=submit]');
  const dot = li.querySelector('.update-item__dot');
  return {
    version: version.textContent.trim(),
    cls: li.className,
    versionLines: new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size,
    meta: li.querySelector('.update-item__meta').textContent.replace(/\\s+/g, ' ').trim(),
    chip: (li.querySelector('.banner__pill') || {textContent: ''}).textContent.trim(),
    button: button ? {text: button.textContent.trim(), rect: rect(button),
      bg: getComputedStyle(button).backgroundColor} : null,
    dotShape: dot ? [dot.getBoundingClientRect().width, getComputedStyle(dot).borderRadius] : null,
    box: rect(li),
    shadow: getComputedStyle(li).boxShadow,
  };
})"""


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
def test_history_is_a_flat_list_with_status_chips_and_a_quiet_revert(
        new_context, servers, width, lang, theme):
    """The history is a flat list, no table and no card inside the card: a status dot, the
    version in monospace and a date, age and notes line per row; "Newest" and "Installed"
    chips; a quiet text-style Revert (still a 44px target) on every older version."""
    words = {
        "en": ("Versions", "Newest", "Installed", "Roll back", "Notes (4)"),
        "fr": ("Versions", "Plus récente", "Installée", "Revenir", "Notes (4)"),
    }[lang]
    context, page = open_panel(new_context, servers["update"], width, lang, theme)
    try:
        where = "%dpx/%s/%s" % (width, lang, theme)
        assert page.locator(".fleet-block--device table").count() == 0, where
        head = page.locator(".fleet-block--device .update-hist__head")
        assert words[0] in head.text_content() and "5" in head.locator(".banner__pill").inner_text()
        rows = page.evaluate(_PROBE_ROWS)
        assert [row["version"] for row in rows] == [
            "fw-v1.0.4", "fw-v1.0.3", "fw-v1.0.2", "fw-v1.0.1", "fw-v1.0.0"], where
        accent_bg = page.evaluate(
            "() => { const p = document.createElement('div');"
            " p.style.backgroundColor = 'var(--color-accent)'; document.body.appendChild(p);"
            " const c = getComputedStyle(p).backgroundColor; p.remove(); return c; }")
        for row in rows:
            assert row["versionLines"] == 1, "version wrapped at %s: %r" % (where, row)
            assert row["shadow"] == "none", where
            assert row["dotShape"][0] == 10, where
            assert row["box"][0] >= -0.5 and row["box"][0] + row["box"][2] <= width + 0.5, where
        newest, installed, *older = rows
        assert newest["chip"] == words[1] and newest["button"] is None, (where, newest)
        assert installed["chip"] == words[2] and installed["button"] is None, (where, installed)
        assert "update-item--running" in installed["cls"], where
        assert words[4] in installed["meta"], (where, installed["meta"])
        assert installed["meta"].count("·") == 2, (where, installed["meta"])
        for row in older:
            assert row["chip"] == "", where
            button = row["button"]
            assert button["text"] == words[3], where
            assert button["rect"][3] >= 44 - 0.5, "revert under 44px at %s" % where
            assert button["rect"][0] + button["rect"][2] <= width + 0.5, where
            assert button["bg"] != accent_bg, "revert must stay quiet at %s" % where
            assert button["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), (
                "revert is text-style at %s: %r" % (where, button["bg"]))
        assert no_horizontal_overflow(page), "overflow at %s" % where
    finally:
        context.close()


def test_a_single_version_is_a_list_of_one_row_without_an_action(new_context, servers):
    context, page = open_panel(new_context, servers["single"], 360, "en", "light")
    try:
        rows = page.evaluate(_PROBE_ROWS)
        assert [row["version"] for row in rows] == ["fw-v1.0.4"]
        assert rows[0]["chip"] == "Installed" and rows[0]["button"] is None
        assert "1" in page.locator(".update-hist__head .banner__pill").inner_text()
    finally:
        context.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
def test_release_notes_open_from_the_row_by_pointer_and_keyboard(
        new_context, servers, width, lang, theme):
    """The row itself is the disclosure: a closed native <details> whose summary (the dot,
    the version and its date line, the chip, a chevron) is at least 44px tall and keyboard
    operable. Opening it lists every note, including the full release text the update card
    trims, inside the viewport, and the Revert button beside it stays outside the summary."""
    context, page = open_panel(new_context, servers["update"], width, lang, theme)
    try:
        where = "%dpx/%s/%s" % (width, lang, theme)
        newest = page.locator(".update-item").nth(0).locator("details")
        oldest = page.locator(".update-item").nth(4).locator("details")
        for details in (newest, oldest):
            assert details.evaluate("el => el.open") is False, where
            assert not details.locator("ul").is_visible(), where
            box = details.locator("summary").bounding_box()
            assert box["height"] >= 44 - 0.5, "summary under 44px at %s" % where
        assert newest.locator("summary").get_attribute("aria-label") is None
        assert newest.locator("summary svg, summary .icon").count() == 1, where

        newest.locator("summary .update-item__version").click()
        page.wait_for_function("d => d.open", arg=newest.element_handle())
        assert newest.locator("li").all_inner_texts() == [_RELEASE_TITLE], where
        newest.locator("summary").focus()
        page.keyboard.press("Enter")
        page.wait_for_function("d => !d.open", arg=newest.element_handle())

        oldest.locator("summary").focus()
        page.keyboard.press("Space")
        page.wait_for_function("d => d.open", arg=oldest.element_handle())
        assert oldest.locator("li").count() == 28, where
        list_box = oldest.locator("ul").bounding_box()
        assert list_box["x"] >= -0.5 and list_box["x"] + list_box["width"] <= width + 0.5, where
        assert no_horizontal_overflow(page), "overflow with notes open at %s" % where
        row_box = page.locator(".update-item").nth(4).locator("form button").bounding_box()
        assert row_box["x"] + row_box["width"] <= width + 0.5, where
        assert oldest.locator("form").count() == 0, "the action stays outside the summary"
        outline = oldest.locator("summary").evaluate(
            "el => { const s = getComputedStyle(el); return s.outlineStyle; }")
        assert outline != "none", "no focus ring on the row at %s" % where
    finally:
        context.close()


def test_release_notes_open_with_scripts_blocked(new_context, servers):
    from companion.test_browser_ux_helpers import _no_js_page
    with _no_js_page(
            new_context, servers["update"].base_url(), FLEET_ROUTE,
            viewport={"width": 360, "height": 900}, reduced_motion="reduce") as page:
        oldest = page.locator(".update-item").nth(4).locator("details")
        assert oldest.evaluate("el => el.open") is False
        oldest.locator("summary").click()
        assert oldest.evaluate("el => el.open") is True
        assert oldest.locator("li").first.is_visible()
