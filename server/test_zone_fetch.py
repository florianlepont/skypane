"""Behaviour tests for the budgeted zone fetch."""

from __future__ import annotations

import pytest
import requests

import server.plane.detect as detect
import server.request_budget as rb
import server.zone_fetch as zone_fetch


class FakeClock:
    def __init__(self) -> None:
        self.now = 2_000_000.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeProviders:
    def __init__(self, behaviours: dict) -> None:
        self.behaviours = behaviours
        self.calls: list[tuple] = []

    def __call__(self, name, lat, lon, radius_nm, timeout=None):
        self.calls.append((name, lat, lon, radius_nm))
        outcome = self.behaviours[name]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def ledger(tmp_path, clock):
    return rb.RequestLedger(str(tmp_path), clock=clock.time, sleep=clock.sleep)


def install(monkeypatch, behaviours) -> FakeProviders:
    fake = FakeProviders(behaviours)
    monkeypatch.setattr(detect, "query_provider", fake)
    return fake


def test_both_providers_queried_in_order(monkeypatch, ledger, clock):
    fake = install(monkeypatch, {"adsbfi": [{"hex": "a"}], "adsblol": [{"hex": "b"}]})
    result = zone_fetch.fetch_zone(ledger, 48.7, 2.3, 10.0)
    assert [c[0] for c in fake.calls] == ["adsbfi", "adsblol"]
    assert fake.calls[0][1:] == (48.7, 2.3, 10.0)
    assert result.results == (("adsbfi", [{"hex": "a"}]), ("adsblol", [{"hex": "b"}]))
    assert result.queried == ("adsbfi", "adsblol")
    assert result.failed == ()
    assert clock.now - 2_000_000.0 == pytest.approx(rb.MIN_SPACING_S)


@pytest.mark.parametrize(
    "error",
    [requests.HTTPError("429 from adsbfi"), requests.Timeout("slow"), ValueError("bad"),
     RuntimeError("unexpected"), KeyError("shape")],
)
def test_failing_provider_is_paused_and_other_still_answers(
    monkeypatch, ledger, clock, error
):
    fake = install(monkeypatch, {"adsbfi": error, "adsblol": [{"hex": "b"}]})
    result = zone_fetch.fetch_zone(ledger, 48.7, 2.3, 10.0)
    assert result.failed == ("adsbfi",)
    assert result.results == (("adsblol", [{"hex": "b"}]),)
    assert ledger.paused_until("adsbfi") == pytest.approx(clock.now + 60.0, abs=5)
    again = zone_fetch.fetch_zone(ledger, 48.7, 2.3, 10.0)
    assert again.failed == ("adsbfi",)
    assert [c[0] for c in fake.calls] == ["adsbfi", "adsblol", "adsblol"]


def test_failed_request_still_counts_against_spacing(monkeypatch, ledger, clock):
    install(monkeypatch, {"adsbfi": requests.Timeout("x"), "adsblol": []})
    start = clock.now
    zone_fetch.fetch_zone(ledger, 1.0, 2.0, 3.0)
    assert clock.now - start == pytest.approx(rb.MIN_SPACING_S)


def test_both_paused_makes_no_request(monkeypatch, ledger):
    fake = install(monkeypatch, {"adsbfi": [], "adsblol": []})
    ledger.report_failure("adsbfi")
    ledger.report_failure("adsblol")
    result = zone_fetch.fetch_zone(ledger, 1.0, 2.0, 3.0)
    assert fake.calls == []
    assert result.results == ()
    assert set(result.failed) == set(result.queried) == {"adsbfi", "adsblol"}


def test_budget_unavailable_is_a_skipped_provider(monkeypatch, ledger):
    fake = install(monkeypatch, {"adsbfi": [], "adsblol": []})

    def boom(provider):
        raise rb.BudgetUnavailable("no")

    monkeypatch.setattr(ledger, "acquire", boom)
    result = zone_fetch.fetch_zone(ledger, 1.0, 2.0, 3.0)
    assert fake.calls == []
    assert result.failed == ("adsbfi", "adsblol")


def test_deadline_stops_further_providers(monkeypatch, ledger, clock):
    fake = install(monkeypatch, {"adsbfi": [{"hex": "a"}], "adsblol": [{"hex": "b"}]})
    deadline = clock.now + 0.5
    inner = fake.__call__

    def slow(*args, **kwargs):
        clock.now += 1.0
        return inner(*args, **kwargs)

    monkeypatch.setattr(detect, "query_provider", slow)
    result = zone_fetch.fetch_zone(
        ledger, 1.0, 2.0, 3.0, clock=clock.time, deadline_at=deadline
    )
    assert [c[0] for c in fake.calls] == ["adsbfi"]
    assert result.failed == ("adsblol",)
    assert result.results == (("adsbfi", [{"hex": "a"}]),)


def test_deadline_already_passed_queries_nothing(monkeypatch, ledger, clock):
    fake = install(monkeypatch, {"adsbfi": [], "adsblol": []})
    result = zone_fetch.fetch_zone(
        ledger, 1.0, 2.0, 3.0, clock=clock.time, deadline_at=clock.now - 1
    )
    assert fake.calls == []
    assert result.failed == ("adsbfi", "adsblol")


def test_opt_in_provider_is_rejected(monkeypatch, ledger):
    fake = install(monkeypatch, {})
    with pytest.raises(ValueError):
        zone_fetch.fetch_zone(ledger, 1.0, 2.0, 3.0, providers=["airplanes"])
    assert fake.calls == []


def test_not_fetched_and_diagnostics():
    empty = zone_fetch.ZoneFetch.not_fetched()
    assert empty.results == () and empty.queried == () and empty.failed == ()
    fetch = zone_fetch.ZoneFetch((), ("adsbfi", "adsblol"), ("adsbfi",))
    diag = fetch.diagnostics()
    assert diag == {"queried": ["adsbfi", "adsblol"], "failed": ["adsbfi"]}
    diag["failed"].append("x")
    assert fetch.failed == ("adsbfi",)
