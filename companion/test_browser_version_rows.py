"""Real-browser check that the status chip of a version row sits in the same place on every row:
on the version's own line, a fixed gap to its right, whatever the chip's width (Newest, Running)
and the language, from the narrowest supported phone to a desktop."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login
from server import atomic_io, firmware_registry as fr
from skypane_fw_image import build_image

pytestmark = pytest.mark.browser

_ROWS = (
    "() => [...document.querySelectorAll('.fleet-versions li.update-item')].map(li => {"
    " const v = li.querySelector('.update-item__version').getBoundingClientRect();"
    " const c = li.querySelector('.banner__pill');"
    " const a = li.querySelector('.update-item__action button');"
    " const n = li.querySelector('.update-item__count');"
    " const cr = c && c.getBoundingClientRect(); const nr = n && n.getBoundingClientRect();"
    " return {chip: c && c.textContent.trim(),"
    "  gap: cr && cr.left - v.right, dy: cr && (cr.top + cr.height / 2) - (v.top + v.height / 2),"
    "  chipWidth: cr && cr.width, notesLeft: nr && nr.left, notesTop: nr && nr.top - v.top,"
    "  actionRight: a ? a.getBoundingClientRect().right : null}; })")


def _open(new_context, server, viewport, lang):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.live_id + "&view=versions")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(
        "() => document.readyState === 'complete' && document.getAnimations().every("
        "a => !a.effect || a.effect.getTiming().iterations === Infinity"
        " || a.playState !== 'running')", timeout=15000)
    return context, page


def _seed_four_releases(state_dir):
    """Four releases, the third running: a Newest row, a Running row and two older rows
    (Revert), all with release notes."""
    now = datetime.now(timezone.utc)
    for version, age in (("fw-v1.4.0", 55), ("fw-v1.4.1", 51), ("fw-v1.4.2", 36),
                         ("fw-v1.4.3", 2)):
        when = (now - timedelta(days=age)).isoformat()
        path = os.path.join(str(state_dir), version + ".bin")
        image = build_image(version)
        with open(path, "wb") as fh:
            fh.write(image)
        manifest = {
            "version": version, "sha256": hashlib.sha256(image).hexdigest(), "size": len(image),
            "released_at": when, "commit": "a" * 40, "hardware_type": fr.hardware.LEGACY_KEY,
            "notes": ["Battery reading fix", "A second note"]}
        fr.publish_release(str(state_dir), manifest, path, now=when)
    report = {"schema": 1, "next_seq": 1, "devices": {"dev1": {
        "fw_version": "fw-v1.4.2", "reported_at": now.isoformat(), "events": []}}}
    atomic_io.atomic_write(fr.device_report_path(str(state_dir)), json.dumps(report))


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [360, 390, 1280])
def test_every_status_chip_sits_beside_its_version_at_the_same_offset(
        new_context, app_server_in_process, width, lang):
    _seed_four_releases(app_server_in_process.state_dir)
    context, page = _open(
        new_context, app_server_in_process, {"width": width, "height": 900}, lang)
    try:
        rows = page.evaluate(_ROWS)
        chips = [row for row in rows if row["chip"]]
        assert {row["chip"] for row in chips} >= (
            {"Newest", "Running"} if lang == "en" else {"Plus récente", "En cours"}), rows
        assert len({round(row["chipWidth"]) for row in chips}) == 2, "chips must differ in width"
        for row in chips:
            assert row["gap"] == pytest.approx(chips[0]["gap"], abs=0.5), rows
            assert row["gap"] > 0, "the chip must be to the right of the version: %r" % rows
            assert abs(row["dy"]) <= 1.5, "the chip must share the version's line: %r" % rows
        actions = [row["actionRight"] for row in rows if row["actionRight"] is not None]
        assert len(actions) == 2 and actions[0] == pytest.approx(actions[1], abs=0.5), rows
        notes = [row for row in rows if row["notesLeft"] is not None]
        for row in notes:
            assert row["notesLeft"] == pytest.approx(notes[0]["notesLeft"], abs=0.5), rows
            assert row["notesTop"] == pytest.approx(notes[0]["notesTop"], abs=0.5), rows
    finally:
        context.close()
