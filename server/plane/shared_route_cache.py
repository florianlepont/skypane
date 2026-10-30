"""Cross-device adsbdb answer cache.

`SharedRouteTransport` wraps an adsbdb transport (`(callsign, timeout) ->
(status_code, body)`) so devices that show the same aircraft share one
lookup. It plugs into the `transport=` argument of `enrich.resolve_route`;
the per-device enrichment cache and its TTLs are unchanged.

The cache is one JSON file in the state root, guarded by a leaf `flock`
that is never held across network I/O: the lock is taken to read, released
for the inner call, and taken again to store. Only 404 and 2xx answers are
stored (the rule the per-device cache applies); anything else, and any
cache fault, falls through to the inner transport so a cache problem can
never fail a poll cycle.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable
from typing import Any

import server.atomic_io as atomic_io
import server.plane.enrich as enrich

SHARED_CACHE_FILENAME = "adsbdb_shared_cache.json"
LOCK_FILENAME = SHARED_CACHE_FILENAME + ".lock"
LOCK_WAIT_S = 2.0

Transport = Callable[..., tuple[int, Any]]


def _is_cacheable_status(status: object) -> bool:
    return isinstance(status, int) and not isinstance(status, bool) and (
        status == 404 or 200 <= status < 300
    )


def _ttl_for(status: int) -> float:
    return enrich.CACHE_MISS_TTL_S if status == 404 else enrich.CACHE_HIT_TTL_S


def _valid_entry(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    stored_at = entry.get("stored_at")
    if isinstance(stored_at, bool) or not isinstance(stored_at, (int, float)):
        return False
    if not math.isfinite(stored_at):
        return False
    return _is_cacheable_status(entry.get("status")) and "body" in entry


def _load(path: str) -> dict[str, dict[str, Any]]:
    """Read the cache file; anything unreadable or malformed is empty."""
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: entry
        for key, entry in raw.items()
        if isinstance(key, str) and _valid_entry(entry)
    }


def _body_fits(body: object) -> bool:
    try:
        encoded = json.dumps(body)
    except (TypeError, ValueError):
        return False
    return len(encoded.encode("utf-8")) <= enrich.ADSBDB_MAX_BYTES


class SharedRouteTransport:
    """Callable `(callsign, timeout) -> (status_code, body)` backed by a
    root-level cache shared by every device and process.
    """

    def __init__(
        self,
        root: str,
        inner: Transport | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._path = os.path.join(root, SHARED_CACHE_FILENAME)
        self._lock_path = os.path.join(root, LOCK_FILENAME)
        self._inner = inner
        self._clock = clock or time.time

    def _call_inner(self, callsign: str, timeout: float) -> tuple[int, Any]:
        inner = self._inner if self._inner is not None else enrich.default_transport
        return inner(callsign, timeout)

    def _fresh(self, entry: dict[str, Any], now: float) -> bool:
        age = now - entry["stored_at"]
        return bool(0 <= age < _ttl_for(entry["status"]))

    def _lookup_cached(self, key: str, now: float) -> tuple[int, Any] | None:
        try:
            with atomic_io.exclusive_lock(self._lock_path, LOCK_WAIT_S):
                entry = _load(self._path).get(key)
        except OSError:
            return None
        if entry is not None and self._fresh(entry, now):
            return entry["status"], entry["body"]
        return None

    def _store(self, key: str, status: int, body: Any, now: float) -> None:
        if not _is_cacheable_status(status) or not _body_fits(body):
            return
        try:
            with atomic_io.exclusive_lock(self._lock_path, LOCK_WAIT_S):
                entries = _load(self._path)
                entries.pop(key, None)
                entries[key] = {"status": status, "body": body, "stored_at": now}
                if len(entries) > enrich.CACHE_MAX_ENTRIES:
                    ordered = sorted(
                        entries.items(), key=lambda item: item[1]["stored_at"],
                    )
                    keep = ordered[len(entries) - enrich.CACHE_MAX_ENTRIES:]
                    entries = dict(keep)
                atomic_io.atomic_write(
                    self._path, json.dumps(entries, separators=(",", ":")),
                    mode=0o600,
                )
        except OSError:
            return

    def __call__(
        self, callsign: str, timeout: float = enrich.DEFAULT_TIMEOUT,
    ) -> tuple[int, Any]:
        key = enrich.normalise_callsign(callsign)
        if key is None or not enrich._is_url_safe_callsign(key):
            return self._call_inner(callsign, timeout)
        now = self._clock()
        cached = self._lookup_cached(key, now)
        if cached is not None:
            return cached
        status, body = self._call_inner(callsign, timeout)
        self._store(key, status, body, self._clock())
        return status, body
