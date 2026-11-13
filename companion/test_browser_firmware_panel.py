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
    for version, age_days, note_count in _HISTORY[len(_HISTORY) - count:]:
        released = (now - timedelta(days=age_days)).replace(microsecond=0).isoformat()
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
