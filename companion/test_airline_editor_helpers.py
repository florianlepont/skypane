# SPDX-License-Identifier: AGPL-3.0-only
"""The airline editor's HTTP rig, shared by its test modules."""
__test__ = False

import os
import urllib.parse

import companion.test_companion_app_helpers as cah
from companion import device_scope
from companion_app_server import http_request, with_csrf, with_csrf_part

VENDORED = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "assets", "icons", "illustrations")
EDITOR = "/airlines/manage"


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)
        self.frame = "/devices/%s" % seed.owned_id

    def get(self, who, path):
        status, headers, body = http_request(self.server.url(path), cookie=self.cookies.get(who))
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, path, form):
        cookie = self.cookies.get(who)
        status, headers, body = http_request(
            self.server.url(path), method="POST", cookie=cookie,
            data=with_csrf(cookie, form), extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def upload(self, who, path, payload):
        body, content_type = with_csrf_part(
            self.cookies.get(who), *cah.encode_multipart(payload, field_name="illustration"))
        status, headers, _b = http_request(
            self.server.url(path), method="POST", data=body,
            cookie=self.cookies.get(who), content_type=content_type,
            extra_headers={"Origin": self.server.base_url()})
        return status, headers

    def stored(self):
        """Every file the editing flows write, by relative path with its bytes:
        the frame's own files plus the fleet artwork directory at the root."""
        found = {}
        fleet_art = os.path.join(self.server.state_dir, "illustration_overrides")
        for base, anchor in ((self.owned_dir, self.owned_dir), (fleet_art, self.server.state_dir)):
            for root, _dirs, names in os.walk(base):
                for name in names:
                    if name.endswith((".json", ".png")):
                        path = os.path.join(root, name)
                        with open(path, "rb") as handle:
                            found[os.path.relpath(path, anchor)] = handle.read()
        return found


def query_of(headers):
    parts = urllib.parse.urlsplit(headers["Location"])
    return parts.path, urllib.parse.parse_qs(parts.query)


def override(rig, key):
    """A fleet-wide upload under `key`, the vendored Vueling picture's bytes."""
    folder = os.path.join(rig.server.state_dir, "illustration_overrides")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, key + ".png")
    with open(os.path.join(VENDORED, "vueling-airlines.png"), "rb") as handle:
        data = handle.read()
    with open(path, "wb") as handle:
        handle.write(data)
    return path
