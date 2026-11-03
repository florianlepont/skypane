"""The vendored Leaflet files: served publicly, byte-pinned, free of dynamic-code
and network primitives, and without the library's marker images."""
import hashlib
import re

import pytest

from companion_app_server import http_request

_BASE = "/static/vendor/leaflet/"
_PINNED = {
    "leaflet.js": (
        "text/javascript", 147552,
        "db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a"),
    "leaflet.css": (
        "text/css", 14806,
        "a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6"),
    "LICENSE": (
        "text/plain", 1395,
        "53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb"),
}
_FORBIDDEN = (
    "eval(", "new Function", "XMLHttpRequest", "fetch(", "navigator.sendBeacon",
    "process.env", "document.write")
_ALLOWED_URLS = {"http://www.w3.org/2000/svg", "https://leafletjs.com"}


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


@pytest.mark.parametrize("name", sorted(_PINNED))
def test_each_vendored_file_is_served_publicly_with_the_pinned_bytes(server, name):
    content_type, size, digest = _PINNED[name]
    status, headers, body = http_request(server.base_url() + _BASE + name)
    assert status == 200
    assert headers["Content-Type"].split(";")[0] == content_type
    assert len(body) == size
    assert hashlib.sha256(body).hexdigest() == digest


def test_the_served_script_has_no_dynamic_code_or_network_primitive(server):
    _status, _headers, body = http_request(server.base_url() + _BASE + "leaflet.js")
    text = body.decode("utf-8")
    for needle in _FORBIDDEN:
        assert needle not in text, needle
    urls = set(re.findall(r"https?://[^\s\"'`)]+", text))
    assert urls <= _ALLOWED_URLS, urls - _ALLOWED_URLS


@pytest.mark.parametrize("name", ["marker-icon.png", "layers.png", "marker-shadow.png"])
def test_the_marker_images_are_not_served(server, name):
    status, _headers, _body = http_request(server.base_url() + _BASE + "images/" + name)
    assert status == 404
