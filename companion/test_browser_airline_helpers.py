"""Seed shared by the airline editor's browser tests."""
__test__ = False

import os
import shutil
from datetime import datetime, timedelta, timezone

import companion.test_status_pages_helpers as shp
from companion.test_browser_ux_helpers import seed_state_dir
from server import history_db
from server.plane import illustrations, manual_resolutions, name_overrides


def seed_airline_editor(state_dir):
    """An owner-like state: Transavia seen on an A320 (its own artwork slot) and a B738 (none),
    a renamed TAP, an owner-named airline without artwork and one unidentified prefix."""
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("A320", "A320", "B738")):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(days=index + 1)).isoformat(), hex="tv%04d" % index,
                callsign="TVF%03d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Transavia France")
    manual_resolutions.add_entry(state_dir, "DLH", "Lufthansa")
    name_overrides.set_names(state_dir, ["TAP"], "TAP Air Portugal", own_builtin_name="TAP Portugal")
    target = os.path.join(state_dir, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)
    os.makedirs(target, exist_ok=True)
    shutil.copy(os.path.join(illustrations.ILLUSTRATION_DIR, "tap-portugal.png"),
                os.path.join(target, "tap-air-portugal.png"))
    shp.seed_unresolved_prefixes(state_dir, {
        "XYZ": {"count": 5, "first_seen": "2026-01-01T00:00:00+00:00",
                "last_seen": "2026-01-02T00:00:00+00:00", "example_callsign": "XYZ123"}})
