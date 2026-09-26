"""Behaviour tests for server/http_fetch.py's bounded_get: a total
wall-clock deadline and a byte cap over a streamed requests.get(), proven
against a fake requests.get (no network). pinned_request's own tests live
alongside these once that primitive lands.
"""

import json

import pytest
import requests

from server import http_fetch


class _FakeStreamResponse:
    """Stands in for a requests.Response: only the bounded_get() surface
    (status_code, headers, iter_content, close). Each chunk yielded
    advances a shared fake clock by one second, simulating a slow
    trickle upstream one read at a time.
    """

    def __init__(self, clock_state, status_code=200, headers=None, chunk_count=20):
        self.status_code = status_code
        self.headers = headers if headers is not None else {}
        self.closed = False
        self.chunks_yielded = 0
        self._clock_state = clock_state
        self._chunk_count = chunk_count

    def iter_content(self, chunk_size=8192):
        for _ in range(self._chunk_count):
            self._clock_state["t"] += 1.0
            self.chunks_yielded += 1
            yield b"x"

    def close(self):
        self.closed = True


def _fixed_body_response(body_bytes, headers=None, status_code=200):
    class _Response:
        def __init__(self):
            self.status_code = status_code
            self.headers = headers if headers is not None else {}
            self.closed = False

        def iter_content(self, chunk_size=8192):
            yield body_bytes

        def close(self):
            self.closed = True

    return _Response()


def test_bounded_get_raises_deadline_exceeded_on_slow_trickle(monkeypatch):
    clock_state = {"t": 0.0}
    fake_response = _FakeStreamResponse(clock_state)
    monkeypatch.setattr(
        requests, "get", lambda *a, **k: fake_response
    )

    with pytest.raises(http_fetch.DeadlineExceeded):
        http_fetch.bounded_get(
            "https://example.invalid/data",
            timeout=2,
            deadline_s=5,
            max_bytes=1_000_000,
            clock=lambda: clock_state["t"],
        )

    assert fake_response.closed is True
    assert fake_response.chunks_yielded <= 6


def test_deadline_exceeded_is_a_requests_timeout_and_request_exception():
    assert issubclass(http_fetch.DeadlineExceeded, requests.exceptions.Timeout)
    assert issubclass(http_fetch.DeadlineExceeded, requests.exceptions.RequestException)


def test_response_too_large_is_a_request_exception():
    assert issubclass(http_fetch.ResponseTooLarge, requests.exceptions.RequestException)


def test_bounded_get_raises_response_too_large_ignoring_content_length(monkeypatch):
    fake = _fixed_body_response(b"x" * 11, headers={"Content-Length": "1"})
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    with pytest.raises(http_fetch.ResponseTooLarge):
        http_fetch.bounded_get(
            "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
        )

    assert fake.closed is True


def test_bounded_get_allows_exactly_max_bytes(monkeypatch):
    fake = _fixed_body_response(b"x" * 10)
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    result = http_fetch.bounded_get(
        "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
    )

    assert result.content == b"x" * 10
    assert result.status_code == 200
    assert fake.closed is True


@pytest.mark.parametrize("status", [404, 503])
def test_bounded_get_returns_non_2xx_without_raising(monkeypatch, status):
    fake = _fixed_body_response(b"", status_code=status)
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    result = http_fetch.bounded_get(
        "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
    )

    assert result.status_code == status
    assert fake.closed is True


def test_bounded_get_calls_requests_get_with_stream_and_timeout(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, timeout=None, stream=None):
        captured.update(url=url, headers=headers, timeout=timeout, stream=stream)
        return _fixed_body_response(b"ok")

    monkeypatch.setattr(requests, "get", fake_get)

    http_fetch.bounded_get(
        "https://example.invalid/data",
        headers={"X-Test": "1"},
        timeout=3,
        deadline_s=5,
        max_bytes=100,
    )

    assert captured["stream"] is True
    assert captured["timeout"] == 3
    assert captured["headers"] == {"X-Test": "1"}


def test_bounded_get_streams_fake_provider_response(fake_providers):
    result = http_fetch.bounded_get(
        "https://opendata.adsb.fi/v2/point/1/1/1",
        timeout=5,
        deadline_s=5,
        max_bytes=100_000,
    )

    assert result.status_code == 200
    assert result.content == json.dumps({"aircraft": []}).encode("utf-8")
