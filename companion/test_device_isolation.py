"""End to end: the companion and the BYOS server run over one seeded state
directory. Polling or configuring one device changes what the BYOS serves that
device and nothing about another device or the live frame, and no request is
ever answered with the shared default image.
"""
import os

import pytest

from companion.test_device_helpers import SIM_ENV, get, post, snapshot, start_fleet_app
from companion_app_server import http_request
from skypane_frame_server import IMAGE_BYTES, FrameServer
from skypane_two_device_fleet import device_headers

from server import device_dirs, device_config, fleet_db

MARTINIQUE = {"timezone": "America/Martinique"}


def _prefix(device):
    return "/devices/%s" % device.id


class Stack:
    """The companion app and a BYOS server over the same state directory."""

    def __init__(self, app, byos):
        self.app = app
        self.byos = byos
        self.fleet = app.fleet

    def display(self, device):
        status, body = self.byos.display(device.token, device_headers(device))
        return status, body

    def image(self, url):
        path = url.split("//", 1)[1].split("/", 1)[1]
        status, _headers, body = http_request(self.byos.base_url + "/" + path)
        return status, body

    def served(self, device):
        """What the BYOS answers `device`: (hash, image_url, sleep_s, image bytes)."""
        status, body = self.display(device)
        assert status == 200, (device.id, status, body)
        image_status, image = self.image(body["image_url"])
        assert image_status == 200
        return body["image_hash"], body["image_url"], body["sleep_s"], image

    def all_snapshots(self):
        return {
            "live": snapshot(self.app.server.state_dir),
            "a": snapshot(self.fleet.dev_a.state_dir),
            "b": snapshot(self.fleet.dev_b.state_dir),
            "landscape": snapshot(self.fleet.landscape.state_dir),
        }


def _start_stack(make_app_server, fake_providers):
    app = start_fleet_app(make_app_server, fake_providers=fake_providers)
    byos = FrameServer(app.server.state_dir, env_overrides=SIM_ENV)
    byos.start()
    # The first requests create fleet.db's SQLite sidecars and initialise the
    # history databases; snapshots are taken after them.
    get(app, _prefix(app.fleet.dev_a) + "/health")
    get(app, "/health")
    return Stack(app, byos)


@pytest.fixture(scope="module")
def stack(module_app_server_factory):
    built = _start_stack(module_app_server_factory, fake_providers=True)
    yield built
    built.byos.stop()


@pytest.fixture
def byos_only(make_app_server):
    built = _start_stack(make_app_server, fake_providers=False)
    yield built
    built.byos.stop()


def test_settings_isolation_end_to_end(stack):
    fleet = stack.fleet
    served_b = stack.served(fleet.dev_b)
    served_live = stack.served(fleet.live)
    snapshots = stack.all_snapshots()
    status, headers, _ = post(stack.app, _prefix(fleet.dev_a) + "/settings", MARTINIQUE)
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")
    config = device_config.load_device_config(fleet.dev_a.state_dir)
    assert config["timezone"] == "America/Martinique"
    after = stack.all_snapshots()
    assert after["b"] == snapshots["b"]
    assert after["landscape"] == snapshots["landscape"]
    assert after["live"] == snapshots["live"]
    assert after["a"] != snapshots["a"]
    assert stack.served(fleet.dev_b) == served_b
    assert stack.served(fleet.live) == served_live


def test_live_frame_still_gets_the_raw_live_image(stack):
    live = stack.fleet.live
    status, body = stack.display(live)
    assert status == 200
    digest = body["image_hash"].split(":", 1)[1]
    assert body["image_url"].endswith("/img/%s.bin" % digest)
    assert "/devices/" not in body["image_url"]
    image_status, image = stack.image(body["image_url"])
    assert image_status == 200
    assert len(image) == IMAGE_BYTES


def test_unknown_token_is_401(stack):
    status, body = stack.byos.display("no-such-token")
    assert status == 401
    assert "image_url" not in (body or {})


def test_unknown_device_is_404_on_the_companion_and_the_image_route(stack):
    for path in ("/devices/d_00000000/", "/devices/d_00000000/health",
                 "/devices/d_00000000/display"):
        status, _headers, _ = get(stack.app, path)
        assert status == 404, path
    status, _headers, _ = post(stack.app, "/devices/d_00000000/poll-now")
    assert status == 404
    digest = stack.served(stack.fleet.live)[0].split(":", 1)[1]
    status, _headers, _ = http_request(
        stack.byos.base_url + "/img/d_00000000/%s.bin" % digest)
    assert status == 404


def test_removed_fleet_row_is_401_and_never_the_live_image(byos_only):
    fleet = byos_only.fleet
    assert byos_only.display(fleet.dev_a)[0] == 200
    conn = fleet_db.connect(byos_only.app.server.state_dir)
    try:
        with fleet_db.transaction(conn):
            assert fleet_db.remove_device(conn, fleet.dev_a.mac)
    finally:
        conn.close()
    status, body = byos_only.display(fleet.dev_a)
    assert status == 401
    assert "image_url" not in (body or {})


def test_removed_panel_file_is_503_and_never_the_live_image(byos_only):
    fleet = byos_only.fleet
    assert byos_only.display(fleet.dev_a)[0] == 200
    os.remove(os.path.join(fleet.dev_a.state_dir, device_dirs.PANEL_FILENAME))
    status, body = byos_only.display(fleet.dev_a)
    assert status == 503
    assert "image_url" not in (body or {})
    assert byos_only.display(fleet.dev_b)[0] == 200
