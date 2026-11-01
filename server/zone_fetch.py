"""Budgeted fetch of one zone from the fleet's ADS-B providers.

`fetch_zone` is the only way the fleet reads a zone. It queries the default
providers one after the other, spends one request slot from the shared
`RequestLedger` before each call, and degrades to a single-source or empty
result instead of raising: a paused, failing or over-deadline provider is
reported in `failed` and the zone carries on with whichever providers
answered. Selecting a flight from the raw lists is a separate, pure step.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import server.plane.detect as detect
import server.request_budget as request_budget


@dataclass(frozen=True)
class ZoneFetch:
    """Raw aircraft lists per answering provider, plus what was tried."""

    # Providers that answered, in provider order, with their raw aircraft.
    results: tuple[tuple[str, list[dict[str, Any]]], ...] = ()
    # Every provider considered, in order.
    queried: tuple[str, ...] = ()
    # Providers that failed, were paused, had no budget or ran out of time.
    failed: tuple[str, ...] = ()
    # Key of the zone these aircraft were fetched for; None when unstamped.
    zone_key: str | None = None

    def diagnostics(self) -> dict[str, list[str]]:
        """The `queried` / `failed` keys the source-fault rule reads."""
        return {"queried": list(self.queried), "failed": list(self.failed)}

    @classmethod
    def not_fetched(cls) -> ZoneFetch:
        """A zone that was never attempted: no results, nothing failed."""
        return cls()


def _check_providers(providers: Sequence[str] | None) -> tuple[str, ...]:
    allowed = detect.DEFAULT_PROVIDER_ORDER
    chosen = tuple(allowed if providers is None else providers)
    for name in chosen:
        if name not in allowed:
            raise ValueError("provider %r is not allowed for fleet zones" % (name,))
    return chosen


def _query_one(
    ledger: request_budget.RequestLedger,
    name: str,
    lat: float,
    lon: float,
    radius_nm: float,
    timeout: float,
) -> list[dict[str, Any]] | None:
    """One budgeted request; None when it was skipped or failed."""
    try:
        if not ledger.acquire(name):
            return None
    except request_budget.BudgetUnavailable:
        return None
    try:
        # Looked up at call time so tests can substitute the provider call.
        aircraft: list[dict[str, Any]] = detect.query_provider(
            name, lat, lon, radius_nm, timeout
        )
    except Exception as exc:
        # Any provider-side failure, expected or not, spends the slot and
        # pauses the provider so a persistent fault is not retried every cycle.
        print(
            "detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc),
            file=sys.stderr,
        )
        try:
            ledger.report_failure(name)
        except request_budget.BudgetUnavailable:
            pass
        return None
    return aircraft


def fetch_zone(
    ledger: request_budget.RequestLedger,
    lat: float,
    lon: float,
    radius_nm: float,
    providers: Sequence[str] | None = None,
    timeout: float | None = None,
    clock: Callable[[], float] | None = None,
    deadline_at: float | None = None,
) -> ZoneFetch:
    """Query `providers` sequentially for the zone centred on (lat, lon).

    `deadline_at` is an absolute time on `clock`; once it has passed no
    further provider is queried. Coordinates are sent exactly as given.
    """
    names = _check_providers(providers)
    now = clock if clock is not None else time.time
    per_call = detect.PROVIDER_TIMEOUT_S if timeout is None else timeout
    results: list[tuple[str, list[dict[str, Any]]]] = []
    failed: list[str] = []
    for name in names:
        if deadline_at is not None and now() >= deadline_at:
            failed.append(name)
            continue
        aircraft = _query_one(ledger, name, lat, lon, radius_nm, per_call)
        if aircraft is None:
            failed.append(name)
        else:
            results.append((name, aircraft))
    return ZoneFetch(tuple(results), names, tuple(failed))
