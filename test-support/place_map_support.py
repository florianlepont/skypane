"""Shared rig for the Location and detection page's browser tests.

Both external map hosts are answered from the test, never from the network:
the tile host with one fixed 256x256 PNG and the search host with canned
jsonv2. Every request to either is recorded with the headers the browser sent,
so a test can assert the Referer. A host can also be told to abort, which is
what a blocked network or a content blocker looks like to the page.
"""
import json
import struct
import zlib

from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from server import device_config, device_dirs, fleet_db, hardware

TILE_PATTERN = "https://tile.openstreetmap.org/**"
SEARCH_PATTERN = "https://nominatim.openstreetmap.org/**"
LEAFLET_IMAGES = "/static/vendor/leaflet/images/"

# A canned jsonv2 answer: a street-level result and a city result.
RESULTS = (
    {"name": "Rue de Rivoli", "display_name": "Rue de Rivoli, Paris, Île-de-France, France",
     "lat": "48.8606", "lon": "2.3376", "type": "residential", "addresstype": "road"},
    {"name": "Lyon", "display_name": "Lyon, Métropole de Lyon, Auvergne-Rhône-Alpes, France",
     "lat": "45.7578", "lon": "4.8320", "type": "administrative", "addresstype": "city"},
)


def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def tile_png():
    """A 256x256 mid-grey PNG built with the standard library."""
    row = b"\x00" + b"\xcc" * 256
    raw = row * 256
    header = struct.pack(">IIBBBBB", 256, 256, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b""))


class Hosts:
    """Routes both hosts on `context` and records what the page asked for."""

    def __init__(self, context, tiles="ok", search="ok", results=RESULTS):
        self.tile_requests = []
        self.search_requests = []
        self.image_requests = []
        self.tiles = tiles
        self.search = search
        self.results = results
        self._png = tile_png()
        context.route(TILE_PATTERN, self._tile)
        context.route(SEARCH_PATTERN, self._search)
        context.on("request", self._watch)

    def _watch(self, request):
        if LEAFLET_IMAGES in request.url:
            self.image_requests.append(request.url)

    def _tile(self, route):
        request = route.request
        self.tile_requests.append((request.url, dict(request.headers)))
        if self.tiles == "abort":
            route.abort()
            return
        route.fulfill(status=200, content_type="image/png", body=self._png)

    def _search(self, route):
        request = route.request
        self.search_requests.append((request.url, dict(request.headers)))
        if self.search == "abort":
            route.abort()
            return
        if isinstance(self.search, int):
            route.fulfill(
                status=self.search, content_type="text/plain",
                headers={"access-control-allow-origin": "*"}, body="error")
            return
        route.fulfill(
            status=200, content_type="application/json",
            headers={"access-control-allow-origin": "*"},
            body=json.dumps(list(self.results)))


MIN_PX = 44

# The part of the map the floating controls and the panel leave clear: right of the card on a wide
# screen, between the mode chips and the sheet on a phone.
CLEAR_BOX = (
    "() => { const m = document.getElementById('place-map').getBoundingClientRect();"
    " if (window.matchMedia('(min-width: 960px)').matches) {"
    "   const c = document.querySelector('.place-card').getBoundingClientRect();"
    "   return {x: c.right, y: m.top, width: m.right - c.right, height: m.height}; }"
    " const top = Math.max(document.querySelector('.place-search').getBoundingClientRect().bottom,"
    "   document.querySelector('.place-modes').getBoundingClientRect().bottom);"
    " const s = document.querySelector('.place-sheet').getBoundingClientRect();"
    " return {x: m.left, y: top, width: m.width, height: s.top - top}; }")

# Whether the details card of the Location page (coordinates, label, time zone) shows: with the map
# running it is a card over the map that the `#details` link brings up.
DETAILS_SHOWN = (
    "() => { const d = document.getElementById('details');"
    " return d.open && getComputedStyle(d).display !== 'none'"
    " && d.getBoundingClientRect().height > 0; }")

# Scrolls an element `el` to the middle, as scrollIntoView does, except the window itself when the
# page has the map's lead (a phone): that page is one window resting scrolled past the lead, which
# it would only settle back to a moment later; the boxes inside it still scroll.
_TO_MIDDLE = (
    " const lead = parseFloat(getComputedStyle(document.documentElement)"
    "   .getPropertyValue('--place-lead')) || 0;"
    " const rest = window.scrollY; el.scrollIntoView({block: 'center'});"
    " if (lead) window.scrollTo(0, rest);")

# Whether the page is at rest and a known control owns its own centre: the search field with the
# map running, the airport filter of the plain form without it.
SETTLED = (
    "() => {"
    " if (document.getAnimations().some((a) => a.playState === 'running')) return false;"
    " const el = ['#place-search', '#airport-filter'].map((s) => document.querySelector(s))"
    "   .find((e) => e && e.getBoundingClientRect().width > 0);"
    " if (!el) return false;" + _TO_MIDDLE +
    " const r = el.getBoundingClientRect();"
    " return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el; }")

# How much taller the document is than the window, less the map's lead above the page and its tail
# below it (none where the page has no lead): above 0, something else than the map runs past the
# window.
PAGE_OVERFLOW = (
    "() => { const s = getComputedStyle(document.documentElement);"
    " const extra = (name) => parseFloat(s.getPropertyValue(name)) || 0;"
    " return document.scrollingElement.scrollHeight - innerHeight"
    "  - extra('--place-lead') - extra('--place-tail'); }")

# For each selector, the first matching element is scrolled to the middle (_TO_MIDDLE) and
# measured; a control fails when it is smaller than the floor or something else owns its centre.
HIT_PROBE = (
    "args => args.selectors.map((sel) => {"
    " const el = document.querySelector(sel);"
    " if (!el) return [sel, 'missing'];" + _TO_MIDDLE +
    " const r = el.getBoundingClientRect();"
    " if (r.width < args.min || r.height < args.min) {"
    "   return [sel, 'size ' + r.width.toFixed(1) + 'x' + r.height.toFixed(1)]; }"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " if (!hit || !(el === hit || el.contains(hit) || hit.contains(el))) {"
    "   return [sel, 'covered by ' + (hit ? hit.tagName + '.' + hit.className : 'nothing')]; }"
    " return null; }).filter(Boolean)")


def seed(state_dir):
    """One live frame owned by the test administrator."""
    session_cookie_for_state_dir(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        owner = fleet_db.get_user_by_email(conn, TEST_ADMIN_EMAIL)["id"]
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:04", "d" * 64, hardware.LEGACY_KEY, owner,
            name="Live frame", state_path=device_dirs.LIVE_STATE_PATH)
    finally:
        conn.close()


def stored(server):
    """The detection setting on disk for the server's frame."""
    return device_config.load_device_config(server.state_dir).get("detection")


def saved_place(server):
    """The frame's own position row, or None."""
    conn = fleet_db.connect(server.state_dir)
    try:
        device = conn.execute("SELECT id FROM devices").fetchone()["id"]
        return fleet_db.frame_position(conn, device)
    finally:
        conn.close()


def open_details(page):
    """Brings the details card up the way the Quiet hours note does: by its `#details` target."""
    page.evaluate("() => { window.location.hash = 'details'; }")
    page.wait_for_function(DETAILS_SHOWN, timeout=5000)
