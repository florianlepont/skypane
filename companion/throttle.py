"""A failure-count lockout throttle for guessable secrets (pairing codes).

State is in memory and per process: a companion restart forgets every
count and every lockout. The table is bounded so a caller cannot grow it
without limit by rotating keys.
"""
import collections
import math
import threading
import time

DEFAULT_MAX_KEYS = 4096


class _Entry:
    """Failure count, lockout deadline and last-failure time of one key."""

    __slots__ = ("failures", "locked_until", "last_failure")

    def __init__(self):
        self.failures = 0
        self.locked_until = 0.0
        self.last_failure = 0.0


class LockoutThrottle:
    """Locks a key for `lockout_s` seconds after `limit` failures.

    A failure count that is not followed by a lockout lapses after
    `lockout_s` without a further failure, so an occasional typo never
    accumulates. A failure recorded while a key is locked changes nothing
    (the lockout is not extended). Past `max_keys` keys, entries that are
    not locked go first (oldest first), then the least recently seen.
    """

    def __init__(self, limit, lockout_s, max_keys=DEFAULT_MAX_KEYS, clock=time.time):
        self._limit = limit
        self._lockout_s = lockout_s
        self._max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._entries = collections.OrderedDict()

    def locked_for(self, key):
        """Whole seconds left on `key`'s lockout (rounded up), or 0."""
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 0
            remaining = entry.locked_until - now
            if remaining <= 0:
                return 0
            return max(1, math.ceil(remaining))

    def record_failure(self, key):
        """Count one failure for `key`. True when this failure started a
        lockout.
        """
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._make_room(now)
                entry = self._entries[key] = _Entry()
            else:
                self._entries.move_to_end(key)
            if entry.locked_until > now:
                return False
            if entry.locked_until:
                # The previous lockout has run out: start from zero.
                entry.failures = 0
                entry.locked_until = 0.0
            elif entry.failures and now - entry.last_failure >= self._lockout_s:
                entry.failures = 0
            entry.failures += 1
            entry.last_failure = now
            if entry.failures >= self._limit:
                entry.locked_until = now + self._lockout_s
                return True
            return False

    def record_success(self, key):
        """Forget `key` entirely (count and lockout)."""
        with self._lock:
            self._entries.pop(key, None)

    def reset(self):
        """Forget every key."""
        with self._lock:
            self._entries.clear()

    def key_count(self):
        """How many keys the table holds right now."""
        with self._lock:
            return len(self._entries)

    def _make_room(self, now):
        """Free one slot for a new key. Caller holds the lock."""
        if len(self._entries) < self._max_keys:
            return
        for key in list(self._entries):
            if len(self._entries) < self._max_keys:
                return
            if self._entries[key].locked_until <= now:
                del self._entries[key]
        while len(self._entries) >= self._max_keys:
            self._entries.popitem(last=False)
