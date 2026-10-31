"""Behaviour tests for the persisted ADS-B request ledger."""

from __future__ import annotations

import json
import os
import threading

import pytest

import server.atomic_io as atomic_io
import server.plane.detect as detect
import server.request_budget as rb


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []
        self._mutex = threading.Lock()

    def time(self) -> float:
        with self._mutex:
            return self.now

    def sleep(self, seconds: float) -> None:
        with self._mutex:
            self.sleeps.append(seconds)
            self.now += seconds


def make(tmp_path, clock: FakeClock) -> rb.RequestLedger:
    return rb.RequestLedger(str(tmp_path), clock=clock.time, sleep=clock.sleep)


def write_doc(tmp_path, doc) -> None:
    text = doc if isinstance(doc, str) else json.dumps(doc)
    (tmp_path / rb.LEDGER_FILENAME).write_text(text)


def test_spacing_constant_matches_detect():
    assert rb.MIN_SPACING_S == detect.MIN_SECONDS_BETWEEN_CALLS


def test_first_acquire_does_not_sleep(tmp_path):
    clock = FakeClock()
    assert make(tmp_path, clock).acquire("adsbfi") is True
    assert clock.sleeps == []


def test_second_acquire_waits_out_spacing_across_instances(tmp_path):
    clock = FakeClock()
    make(tmp_path, clock).acquire("adsbfi")
    clock.now += 0.3
    assert make(tmp_path, clock).acquire("adsblol") is True
    assert clock.sleeps == [pytest.approx(0.8)]


def test_no_wait_after_spacing_elapsed(tmp_path):
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    ledger.acquire("adsbfi")
    clock.now += 5
    ledger.acquire("adsbfi")
    assert clock.sleeps == []


def test_failure_pauses_provider_for_sixty_seconds(tmp_path):
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    ledger.report_failure("adsbfi")
    before = clock.now
    assert ledger.acquire("adsbfi") is False
    assert clock.sleeps == []
    assert ledger.acquire("adsblol") is True
    clock.now = before + 59
    assert ledger.acquire("adsbfi") is False
    clock.now = before + 60
    assert ledger.acquire("adsbfi") is True


def test_paused_acquire_does_not_stamp(tmp_path):
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    ledger.report_failure("adsbfi")
    ledger.acquire("adsbfi")
    assert ledger.acquire("adsblol") is True
    assert clock.sleeps == []


def test_pause_is_honoured_by_another_instance(tmp_path):
    clock = FakeClock()
    make(tmp_path, clock).report_failure("adsblol")
    other = make(tmp_path, clock)
    assert other.acquire("adsblol") is False
    assert other.paused_until("adsblol") == pytest.approx(clock.now + 60.0)


def test_unknown_provider_failure_is_ignored(tmp_path):
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    ledger.report_failure("airplanes")
    assert ledger.paused_until("airplanes") is None
    assert not (tmp_path / rb.LEDGER_FILENAME).exists()


def test_future_last_request_never_waits_more_than_spacing(tmp_path):
    clock = FakeClock()
    write_doc(tmp_path, {"last_request_at": clock.now + 36000})
    assert make(tmp_path, clock).acquire("adsbfi") is True
    assert max(clock.sleeps) <= rb.MIN_SPACING_S + 1e-9


def test_future_pause_is_clamped_to_one_minute(tmp_path):
    clock = FakeClock()
    start = clock.now
    write_doc(tmp_path, {"providers": {"adsbfi": {"pause_until": start + 36000}}})
    ledger = make(tmp_path, clock)
    assert ledger.acquire("adsbfi") is False
    clock.now = start + 60
    assert ledger.acquire("adsbfi") is True


@pytest.mark.parametrize(
    "doc",
    [
        "{not json",
        '{"last_request_at": NaN, "providers": {"adsbfi": {"pause_until": Infinity}}}',
        '{"last_request_at": -Infinity}',
        {"last_request_at": True, "providers": {"adsbfi": {"pause_until": False}}},
        {"last_request_at": "soon", "providers": {"adsbfi": {"pause_until": "x"}}},
        {"last_request_at": -5, "providers": {"adsbfi": {"pause_until": -5}}},
        [1, 2, 3],
        "null",
        {"providers": ["adsbfi"], "zones": ["a"]},
        {"providers": {"nonsense": {"pause_until": 9e18}}},
        {"providers": {"adsbfi": 7}},
    ],
)
def test_hostile_documents_never_raise_or_stall(tmp_path, doc):
    clock = FakeClock()
    write_doc(tmp_path, doc)
    ledger = make(tmp_path, clock)
    assert ledger.acquire("adsbfi") is True
    assert all(s <= rb.MIN_SPACING_S + 1e-9 for s in clock.sleeps)
    assert ledger.zone_last_served() == {}


def test_zone_round_trip_and_bounds(tmp_path):
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    ledger.mark_zone_served("zone-a", 10.0)
    assert ledger.zone_last_served() == {"zone-a": 10.0}
    for index in range(rb.MAX_ZONE_ENTRIES + 10):
        ledger.mark_zone_served("z%d" % index, 100.0 + index)
    zones = ledger.zone_last_served()
    assert len(zones) == rb.MAX_ZONE_ENTRIES
    assert "zone-a" not in zones
    newest = "z%d" % (rb.MAX_ZONE_ENTRIES + 9)
    assert zones[newest] == 100.0 + rb.MAX_ZONE_ENTRIES + 9


def test_oversized_or_invalid_zone_key_rejected(tmp_path):
    ledger = make(tmp_path, FakeClock())
    with pytest.raises(ValueError):
        ledger.mark_zone_served("k" * (rb.MAX_ZONE_KEY_LEN + 1), 1.0)
    with pytest.raises(ValueError):
        ledger.mark_zone_served("", 1.0)
    with pytest.raises(ValueError):
        ledger.mark_zone_served("ok", float("nan"))
    assert ledger.zone_last_served() == {}


def test_lock_contention_raises_budget_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "LOCK_WAIT_S", 0.05)
    clock = FakeClock()
    ledger = make(tmp_path, clock)
    with atomic_io.exclusive_lock(str(tmp_path / rb.LOCK_FILENAME), 1.0):
        with pytest.raises(rb.BudgetUnavailable):
            ledger.acquire("adsbfi")
    assert clock.sleeps == []


def test_unwritable_ledger_raises_budget_unavailable(tmp_path):
    clock = FakeClock()
    (tmp_path / rb.LEDGER_FILENAME).mkdir()
    with pytest.raises(rb.BudgetUnavailable):
        make(tmp_path, clock).acquire("adsbfi")


def test_files_are_private_and_stay_under_root(tmp_path):
    clock = FakeClock()
    make(tmp_path, clock).acquire("adsbfi")
    for name in (rb.LEDGER_FILENAME, rb.LOCK_FILENAME):
        assert os.stat(tmp_path / name).st_mode & 0o777 == 0o600
    assert sorted(os.listdir(tmp_path)) == [rb.LEDGER_FILENAME, rb.LOCK_FILENAME]


def test_threads_sharing_a_clock_stay_spaced(tmp_path):
    clock = FakeClock()
    stamps: list[float] = []
    stamp_mutex = threading.Lock()

    def worker(provider: str) -> None:
        ledger = make(tmp_path, clock)
        for _ in range(5):
            if ledger.acquire(provider):
                with stamp_mutex:
                    stamps.append(clock.time())

    threads = [
        threading.Thread(target=worker, args=(name,))
        for name in ("adsbfi", "adsblol", "adsbfi")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    stamps.sort()
    assert len(stamps) == 15
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert min(gaps) >= rb.MIN_SPACING_S - 1e-6
