"""Persisted global ADS-B request budget shared by every process.

The fleet may send at most one ADS-B request per second in total, whatever
the provider, the zone or the process that spends it. `RequestLedger` keeps
the time of the last request, a per-provider "paused until" time and the
per-zone last-served times in one small JSON file inside the state root,
guarded by an exclusive `flock`.

`acquire` sleeps out the remaining spacing while holding the lock: that is
what makes the spacing exact across processes. The wait is at most
`MIN_SPACING_S`, so the lock is never held long. The caller makes the HTTP
request after `acquire` returns, outside the lock.

Lock-order invariant: the ledger lock is a leaf lock. It is never held while
taking poll.lock or any other lock, and never held across a network call.

The file is untrusted input: every field is sanitised on read (finite floats
only, clamped against the current clock) so a corrupt, hand-edited or
clock-skewed ledger can neither raise nor stall a caller for more than one
spacing interval or one pause.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable

import server.atomic_io as atomic_io
import server.plane.detect as detect

LEDGER_FILENAME = "request_ledger.json"
LOCK_FILENAME = "request_ledger.lock"

# Minimum wall-clock gap between any two ADS-B requests.
MIN_SPACING_S = 1.1
# How long a provider that just failed is left alone.
PROVIDER_PAUSE_S = 60.0
# Longest wait for the ledger lock before the caller gives up on the budget.
LOCK_WAIT_S = 5.0
MAX_ZONE_ENTRIES = 256
MAX_ZONE_KEY_LEN = 128

_LEDGER_VERSION = 1


class BudgetUnavailable(RuntimeError):
    """The budget could not be read, locked or recorded: make no request."""


def _finite(value: object) -> float | None:
    """Return `value` as a float when it is a real finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _sanitise_providers(raw: object, now: float) -> tuple[dict[str, float], bool]:
    """Pause-until time per known provider, capped at now + one pause.

    The flag reports whether any stored value had to be capped, so the
    caller can persist the cap and a future-dated pause cannot be
    re-extended on every read.
    """
    out: dict[str, float] = {}
    capped = False
    if not isinstance(raw, dict):
        return out, capped
    for name, entry in raw.items():
        if name not in detect.PROVIDERS or not isinstance(entry, dict):
            continue
        until = _finite(entry.get("pause_until"))
        if until is not None:
            limit = now + PROVIDER_PAUSE_S
            capped = capped or until > limit
            out[name] = min(until, limit)
    return out, capped


def _sanitise_zones(raw: object) -> dict[str, float]:
    """Zone last-served map with bounded key length and entry count."""
    out: dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        served = _finite(value)
        if (
            isinstance(key, str)
            and 0 < len(key) <= MAX_ZONE_KEY_LEN
            and served is not None
        ):
            out[key] = served
    return _newest(out)


def _newest(zones: dict[str, float]) -> dict[str, float]:
    """Keep only the MAX_ZONE_ENTRIES most recently served zones."""
    if len(zones) <= MAX_ZONE_ENTRIES:
        return zones
    ranked = sorted(zones.items(), key=lambda item: item[1], reverse=True)
    return dict(ranked[:MAX_ZONE_ENTRIES])


def parse_ledger(text: str | None, now: float) -> dict[str, object]:
    """Turn raw file text into a sanitised ledger document.

    Anything unreadable yields the empty ledger. `last_request_at` is capped
    at `now` and each `pause_until` at `now + PROVIDER_PAUSE_S`.
    """
    doc: object = None
    if text:
        try:
            doc = json.loads(text)
        except ValueError:
            doc = None
    if not isinstance(doc, dict):
        doc = {}
    last = _finite(doc.get("last_request_at"))
    providers, capped = _sanitise_providers(doc.get("providers"), now)
    return {
        "last_request_at": None if last is None else min(last, now),
        "providers": providers,
        "zones": _sanitise_zones(doc.get("zones")),
        "capped": capped,
    }


def _serialise(doc: dict[str, object]) -> str:
    providers = doc["providers"]
    assert isinstance(providers, dict)
    return json.dumps(
        {
            "version": _LEDGER_VERSION,
            "last_request_at": doc["last_request_at"],
            "providers": {
                name: {"pause_until": until} for name, until in providers.items()
            },
            "zones": doc["zones"],
        },
        sort_keys=True,
    )


class RequestLedger:
    """Flock-guarded spacing, provider pause and zone aging for one root."""

    def __init__(
        self,
        root: str,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
        spacing_s: float = MIN_SPACING_S,
    ) -> None:
        self._ledger_path = os.path.join(root, LEDGER_FILENAME)
        self._lock_path = os.path.join(root, LOCK_FILENAME)
        self._clock: Callable[[], float] = clock if clock is not None else time.time
        self._sleep: Callable[[float], None] = (
            sleep if sleep is not None else time.sleep
        )
        self._spacing_s = spacing_s

    def _read(self, now: float) -> dict[str, object]:
        try:
            with open(self._ledger_path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, ValueError):
            text = None
        return parse_ledger(text, now)

    def _write(self, doc: dict[str, object]) -> None:
        try:
            atomic_io.atomic_write(self._ledger_path, _serialise(doc), mode=0o600)
        except OSError as exc:
            raise BudgetUnavailable("request ledger is not writable") from exc

    def _locked(self) -> _LedgerLock:
        return _LedgerLock(self._lock_path)

    def acquire(self, provider: str) -> bool:
        """Spend one request slot for `provider`.

        Returns False, without stamping, while the provider is paused.
        Otherwise waits out the spacing, records the request time and
        returns True. Raises BudgetUnavailable when the budget cannot be
        locked or recorded.
        """
        with self._locked():
            now = self._clock()
            doc = self._read(now)
            providers = doc["providers"]
            assert isinstance(providers, dict)
            if providers.get(provider, 0.0) > now:
                if doc["capped"]:
                    self._write(doc)
                return False
            last = doc["last_request_at"]
            if isinstance(last, float):
                wait = min(max(last + self._spacing_s - now, 0.0), self._spacing_s)
                if wait > 0.0:
                    self._sleep(wait)
            doc["last_request_at"] = self._clock()
            self._write(doc)
            return True

    def report_failure(self, provider: str) -> None:
        """Pause `provider` for PROVIDER_PAUSE_S for every process."""
        if provider not in detect.PROVIDERS:
            return
        with self._locked():
            now = self._clock()
            doc = self._read(now)
            providers = doc["providers"]
            assert isinstance(providers, dict)
            providers[provider] = now + PROVIDER_PAUSE_S
            self._write(doc)

    def paused_until(self, provider: str) -> float | None:
        """Pause end time when `provider` is paused now, else None."""
        now = self._clock()
        providers = self._read(now)["providers"]
        assert isinstance(providers, dict)
        until = providers.get(provider)
        return until if isinstance(until, float) and until > now else None

    def zone_last_served(self) -> dict[str, float]:
        """Last-served time per zone key."""
        zones = self._read(self._clock())["zones"]
        assert isinstance(zones, dict)
        return dict(zones)

    def mark_zone_served(self, zone_key: str, when: float) -> None:
        """Record that `zone_key` was served at `when`."""
        if not isinstance(zone_key, str) or not 0 < len(zone_key) <= MAX_ZONE_KEY_LEN:
            raise ValueError("zone key must be 1 to %d characters" % MAX_ZONE_KEY_LEN)
        served = _finite(when)
        if served is None:
            raise ValueError("zone served time must be finite")
        with self._locked():
            doc = self._read(self._clock())
            zones = doc["zones"]
            assert isinstance(zones, dict)
            zones[zone_key] = served
            doc["zones"] = _newest(zones)
            self._write(doc)


class _LedgerLock:
    """Context manager taking the ledger flock, mapping contention to
    BudgetUnavailable."""

    def __init__(self, lock_path: str) -> None:
        self._lock_path = lock_path
        self._cm = atomic_io.exclusive_lock(lock_path, LOCK_WAIT_S)

    def __enter__(self) -> None:
        try:
            self._cm.__enter__()
        except (atomic_io.LockBusy, OSError) as exc:
            raise BudgetUnavailable("request ledger lock is busy") from exc

    def __exit__(self, *exc_info: object) -> None:
        self._cm.__exit__(*exc_info)  # type: ignore[arg-type]
