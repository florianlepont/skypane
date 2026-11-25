"""Two users, two frames and one administrator, each frame with its own
sightings and unresolved callsign prefixes: the shared world of the
role-split Airlines tests."""
import io
import os

import fleet_console_support as fx
from PIL import Image
from companion import device_scope
from server import fleet_db, history_db, state_store
from server.plane import illustrations, manual_resolutions

NOW_ISO = "2026-03-10T12:00:00+00:00"
MAC_B = "aa:bb:cc:00:00:b2"

# (airline, aircraft type, callsign) sightings of each frame, oldest first.
SIGHTINGS_A = (
    ("Air France", "A320", "AFR1001"), ("Air France", "A320", "AFR1002"),
    ("Zorro Air", "B738", "ZOR1"))
SIGHTINGS_B = (
    ("Vueling Airlines", "A320", "VLG2001"), ("Quux Air", "E190", "QUX1"),
    ("Quux Air", "E190", "QUX2"), ("Air France", "A21N", "AFR2001"))
SIGHTINGS_LIVE = (("Volotea", "A319", "VOE3001"),)


def _gap(count, last, example):
    return {"count": count, "first_seen": "2026-03-01T08:00:00+00:00",
            "last_seen": last, "example_callsign": example}


GAPS_A = {"AAA": _gap(5, "2026-03-09T10:00:00+00:00", "AAA101"),
          "CCC": _gap(2, "2026-03-08T10:00:00+00:00", "CCC201")}
GAPS_B = {"BBB": _gap(4, "2026-03-09T11:00:00+00:00", "BBB301"),
          "CCC": _gap(2, "2026-03-09T09:00:00+00:00", "CCC302"),
          "DDD": _gap(2, "2026-03-09T09:30:00+00:00", "DDD401"),
          "EEE": _gap(9, "2026-03-09T09:45:00+00:00", "EEE501")}
GAPS_LIVE = {"LLL": _gap(3, "2026-03-07T10:00:00+00:00", "LLL601")}


def artwork_png():
    """A valid override picture, as wide as the upload minimum."""
    buffer = io.BytesIO()
    Image.new("RGBA", (illustrations.ILLUSTRATION_MIN_WIDTH, 400), (200, 30, 30, 128)).save(
        buffer, format="PNG")
    return buffer.getvalue()


class World:
    """Seeded fleet: `owner` (user A) owns frame A, `plain` (user B) owns
    frame B, the administrator owns the live frame at the root."""

    def __init__(self, root):
        self.root = root
        self.seed = fx.seed_fleet(root)
        conn = fleet_db.connect(root)
        try:
            self.b_id = fleet_db.add_device(
                conn, MAC_B, fx.SECRET_HASH, fx.hardware.LEGACY_KEY, self.seed.user_id,
                name="Balcony", state_path="auto")
        finally:
            conn.close()
        devices = {d.id: d for d in device_scope.load_devices(root)}
        self.a_id = self.seed.owned_id
        self.a_dir = devices[self.a_id].state_dir
        self.b_dir = devices[self.b_id].state_dir
        for directory in (self.a_dir, self.b_dir):
            os.makedirs(directory, exist_ok=True)
        for directory, sightings, gaps in (
                (self.a_dir, SIGHTINGS_A, GAPS_A), (self.b_dir, SIGHTINGS_B, GAPS_B),
                (root, SIGHTINGS_LIVE, GAPS_LIVE)):
            self._seed_frame(directory, sightings, gaps)
        manual_resolutions.add_entry(root, "EEE", "Echo Air", now=NOW_ISO)
        self.admin = fx.admin_cookie(root)
        self.user_a = fx.user_cookie(root, fx.OWNER_EMAIL)
        self.user_b = fx.user_cookie(root, fx.USER_EMAIL)

    @staticmethod
    def _seed_frame(directory, sightings, gaps):
        with history_db.open_db(directory) as conn:
            for index, (airline, aircraft, callsign) in enumerate(sightings):
                history_db.record_runway_event(
                    conn, ts="2026-03-0%dT10:%02d:00+00:00" % (1 + index, index),
                    hex="%s%02d" % (callsign[:3].lower(), index), callsign=callsign,
                    aircraft_type=aircraft, confirmed_state="departing", airline=airline)
        state_store.save_poll_state(directory, {"unresolved_prefixes": gaps})
