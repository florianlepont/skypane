"""Behaviour tests for the cross-device adsbdb answer cache."""

from __future__ import annotations

import json
import os
import stat

import pytest

import server.atomic_io as atomic_io
import server.plane.enrich as enrich
import server.plane.shared_route_cache as src

BODY = {"response": {"flightroute": {"airline": {"name": "Air France"}}}}


class Inner:
    def __init__(self, status: int = 200, body: object = BODY) -> None:
        self.calls: list[str] = []
        self.status = status
        self.body = body

    def __call__(self, callsign: str, timeout: float) -> tuple[int, object]:
        self.calls.append(callsign)
        return self.status, self.body


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def make(root, inner, clock=None):
    return src.SharedRouteTransport(str(root), inner=inner, clock=clock or Clock())


def test_same_callsign_across_instances_costs_one_request(tmp_path):
    inner = Inner()
    first = make(tmp_path, inner)
    second = make(tmp_path, inner)
    assert first("AFR123", 5.0) == (200, BODY)
    assert second("AFR123", 5.0) == (200, BODY)
    assert inner.calls == ["AFR123"]


def test_callsign_is_normalised_for_the_key(tmp_path):
    inner = Inner()
    transport = make(tmp_path, inner)
    transport(" afr123 ", 5.0)
    transport("AFR123", 5.0)
    assert len(inner.calls) == 1


def test_cache_file_mode_and_name(tmp_path):
    make(tmp_path, Inner())("AFR123", 5.0)
    path = tmp_path / src.SHARED_CACHE_FILENAME
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_404_is_shared_and_expires_after_miss_ttl(tmp_path):
    clock = Clock()
    inner = Inner(status=404, body=None)
    transport = make(tmp_path, inner, clock)
    assert transport("AFR123", 5.0) == (404, None)
    clock.now += enrich.CACHE_MISS_TTL_S - 1
    transport("AFR123", 5.0)
    assert len(inner.calls) == 1
    clock.now += 2
    transport("AFR123", 5.0)
    assert len(inner.calls) == 2


def test_positive_answer_lives_for_hit_ttl(tmp_path):
    clock = Clock()
    inner = Inner()
    transport = make(tmp_path, inner, clock)
    transport("AFR123", 5.0)
    clock.now += enrich.CACHE_HIT_TTL_S - 1
    transport("AFR123", 5.0)
    assert len(inner.calls) == 1
    clock.now += 2
    transport("AFR123", 5.0)
    assert len(inner.calls) == 2


@pytest.mark.parametrize("status", [429, 500, 503, 403, 400])
def test_transient_statuses_are_never_stored(tmp_path, status):
    inner = Inner(status=status, body=None)
    transport = make(tmp_path, inner)
    assert transport("AFR123", 5.0) == (status, None)
    transport("AFR123", 5.0)
    assert len(inner.calls) == 2
    assert not (tmp_path / src.SHARED_CACHE_FILENAME).exists()


def test_inner_exception_propagates_and_nothing_is_written(tmp_path):
    def boom(callsign, timeout):
        raise RuntimeError("down")

    transport = make(tmp_path, boom)
    with pytest.raises(RuntimeError):
        transport("AFR123", 5.0)
    assert not (tmp_path / src.SHARED_CACHE_FILENAME).exists()


@pytest.mark.parametrize("callsign", ["AF/../1", "A B", "", "AF?x=1"])
def test_invalid_callsigns_bypass_the_cache(tmp_path, callsign):
    inner = Inner()
    transport = make(tmp_path, inner)
    transport(callsign, 5.0)
    transport(callsign, 5.0)
    assert len(inner.calls) == 2
    assert not (tmp_path / src.SHARED_CACHE_FILENAME).exists()


def test_oversized_body_is_not_stored(tmp_path):
    big = {"x": "a" * (enrich.ADSBDB_MAX_BYTES + 10)}
    inner = Inner(body=big)
    transport = make(tmp_path, inner)
    assert transport("AFR123", 5.0) == (200, big)
    transport("AFR123", 5.0)
    assert len(inner.calls) == 2


def test_entry_count_is_bounded_oldest_stored_evicted(tmp_path):
    clock = Clock()
    inner = Inner()
    transport = make(tmp_path, inner, clock)
    for index in range(enrich.CACHE_MAX_ENTRIES + 5):
        clock.now += 1
        transport("AFR%d" % index, 5.0)
    stored = json.loads((tmp_path / src.SHARED_CACHE_FILENAME).read_text())
    assert len(stored) == enrich.CACHE_MAX_ENTRIES
    assert "AFR0" not in stored
    assert "AFR%d" % (enrich.CACHE_MAX_ENTRIES + 4) in stored


@pytest.mark.parametrize("content", ["not json", "[1, 2]", "null", '{"AFR123": 7}'])
def test_corrupt_file_loads_as_empty(tmp_path, content):
    (tmp_path / src.SHARED_CACHE_FILENAME).write_text(content)
    inner = Inner()
    transport = make(tmp_path, inner)
    assert transport("AFR123", 5.0) == (200, BODY)
    assert transport("AFR123", 5.0) == (200, BODY)
    assert len(inner.calls) == 1


def test_bad_entries_are_dropped_and_good_ones_kept(tmp_path):
    clock = Clock()
    doc = {
        "AFR123": {"status": 200, "body": BODY, "stored_at": clock.now},
        "BAD1": {"status": 200, "body": BODY, "stored_at": "x"},
        "BAD2": {"status": 500, "body": None, "stored_at": clock.now},
        "BAD3": {"status": 200, "body": BODY, "stored_at": float("inf")},
    }
    (tmp_path / src.SHARED_CACHE_FILENAME).write_text(json.dumps(doc))
    inner = Inner()
    transport = make(tmp_path, inner, clock)
    transport("AFR123", 5.0)
    assert inner.calls == []
    transport("BAD1", 5.0)
    transport("BAD2", 5.0)
    transport("BAD3", 5.0)
    assert len(inner.calls) == 3


def test_future_stored_at_is_stale(tmp_path):
    clock = Clock()
    doc = {"AFR123": {"status": 200, "body": BODY, "stored_at": clock.now + 999}}
    (tmp_path / src.SHARED_CACHE_FILENAME).write_text(json.dumps(doc))
    inner = Inner()
    make(tmp_path, inner, clock)("AFR123", 5.0)
    assert len(inner.calls) == 1


def test_lock_timeout_falls_back_to_inner(tmp_path, monkeypatch):
    def busy(*args, **kwargs):
        raise atomic_io.LockBusy("busy")

    monkeypatch.setattr(atomic_io, "exclusive_lock", busy)
    inner = Inner()
    transport = make(tmp_path, inner)
    assert transport("AFR123", 5.0) == (200, BODY)
    assert transport("AFR123", 5.0) == (200, BODY)
    assert len(inner.calls) == 2


def test_unwritable_root_falls_back_to_inner(tmp_path):
    missing = tmp_path / "file"
    missing.write_text("x")
    inner = Inner()
    transport = make(missing, inner)
    assert transport("AFR123", 5.0) == (200, BODY)
    assert len(inner.calls) == 1


def test_inner_call_happens_outside_the_lock(tmp_path):
    lock_path = os.path.join(str(tmp_path), src.LOCK_FILENAME)

    def inner(callsign, timeout):
        with atomic_io.exclusive_lock(lock_path, 0.0, blocking=False):
            return 200, BODY

    assert make(tmp_path, inner)("AFR123", 5.0) == (200, BODY)


def test_default_inner_is_looked_up_at_call_time(tmp_path, monkeypatch):
    inner = Inner()
    monkeypatch.setattr(enrich, "default_transport", inner)
    transport = src.SharedRouteTransport(str(tmp_path))
    transport("AFR123", 5.0)
    assert inner.calls == ["AFR123"]
