"""A device's home position leaves the host only rounded to two decimals."""

from __future__ import annotations

import pytest

import server.detection as detection
import server.plane.enrich as enrich
import server.request_budget as rb
import server.zone_fetch as zone_fetch
from server import http_fetch

_CFG = {"detection": {"mode": "position", "radius_km": 9}}
_FORBIDDEN = ("48.8566", "2.3522", "48.85661", "2.35222")


class _Clock:
    def __init__(self) -> None:
        self.now = 3_000_000.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return _Clock()


@pytest.fixture
def ledger(tmp_path, clock):
    return rb.RequestLedger(str(tmp_path), clock=clock.time, sleep=clock.sleep)


@pytest.fixture
def captured_urls(monkeypatch):
    urls: list[str] = []

    def fake_get(url, headers=None, timeout=None, deadline_s=None, max_bytes=None):
        urls.append(url)
        return http_fetch.FetchResult(200, b'{"aircraft": [], "ac": []}', {})

    monkeypatch.setattr(http_fetch, "bounded_get", fake_get)
    return urls


def _fetch(ledger, location):
    spec = detection.spec_for(_CFG, location=location)
    zone = spec.zone
    return zone_fetch.fetch_zone(ledger, zone.lat, zone.lon, zone.radius_nm)


def test_url_guard_provider_urls_use_rounded_zone(ledger, captured_urls, capsys, caplog):
    _fetch(ledger, (48.85661, 2.35222))
    assert len(captured_urls) == 2
    assert "/lat/48.86/lon/2.35/dist/4.86" in captured_urls[0]
    assert "/point/48.86/2.35/4.86" in captured_urls[1]
    captured = capsys.readouterr()
    logs = captured.out + captured.err + caplog.text
    for text in list(captured_urls) + [logs]:
        for forbidden in _FORBIDDEN:
            assert forbidden not in text


def test_url_guard_adsbdb_url_carries_no_coordinates():
    url = enrich.ADSBDB_URL.format(callsign="AFR123")
    assert url == "https://api.adsbdb.com/v0/callsign/AFR123"
    assert "lat" not in url and "lon" not in url


def test_shared_zone_two_devices_one_fetch(ledger, captured_urls):
    first = detection.spec_for(_CFG, location=(48.8566, 2.3522))
    second = detection.spec_for(_CFG, location=(48.8601, 2.3500))
    assert first.zone.key == second.zone.key
    zones = {spec.zone.key: spec.zone for spec in (first, second)}
    assert len(zones) == 1
    for zone in zones.values():
        zone_fetch.fetch_zone(ledger, zone.lat, zone.lon, zone.radius_nm)
    assert len(captured_urls) == 2
