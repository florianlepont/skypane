"""The on-disk `calendar_rules.json` registry and `calendar_url.secret`
accessor pair: file paths, the cross-process lock, load/write/save,
retention windowing/capping, the throttle predicate and the secret-file
permission checks.

Imports `ics` for the allowlists shared with feed parsing
(`_AIRLINE_IATA_RE`, `_AIRPORT_IATA_RE`) and the raw-examination bound
(`CALENDAR_MAX_RAW_EXAMINED`) — never the reverse, and never `match`, so
the three submodules stay acyclic under the package `__init__`.
"""
import contextlib
import json
import math
import os
import stat
import sys
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

from server import atomic_io

from .ics import CALENDAR_MAX_RAW_EXAMINED, _AIRLINE_IATA_RE, _AIRPORT_IATA_RE

# On-disk registry filename, mirroring colour_rules.py's naming.
CALENDAR_RULES_FILENAME = "calendar_rules.json"

# On-disk path for the calendar feed URL — this project's first runtime
# secret outside companion/auth.py. Lives in state_dir like other durable
# state so it survives a redeploy. See save_calendar_url() for why its
# file mode is not a umask default.
CALENDAR_SECRET_FILENAME = "calendar_url.secret"

# Distinct lock-file path for _calendar_registry_lock(); must never
# collide with the rules or secret filenames, or a lock on one file would
# silently also gate the other.
CALENDAR_REGISTRY_LOCK_FILENAME = "calendar_rules.lock"

# Sentinel meaning "clear the stored value", since None already means
# "not supplied, carry forward" everywhere on this write path. Compared
# by identity only, never equality or truthiness.
CLEAR_CALENDAR_URL = object()

# Hard cap on entries surviving the retention window (see
# select_window_entries()) — a defence against a hostile/malformed feed,
# not a plausible real one (a real 48h roster runs well under ten
# events).
CALENDAR_MAX_ENTRIES = 200

# Minimum seconds between fetch *attempts*. A crew roster republishes at
# most a few times a day, well below this interval.
CALENDAR_FETCH_INTERVAL_S = 1800

# Rolling-window retention width in seconds: today plus 48h forward.
CALENDAR_WINDOW_FORWARD_S = 172800

# A connected feed whose last successful read is older than this is
# reported as out of date. Four missed fetch intervals (two hours): one
# or two failed fetches are a blip the 48h window absorbs without the
# frame showing anything wrong, four in a row mean the feed or the poll
# has stopped.
CALENDAR_STALE_AFTER_S = 4 * CALENDAR_FETCH_INTERVAL_S

# --- Registry file contract -------------------------------------------------

# The exact five-key shape parse_ics_events() emits, declared once so the
# loader's key-set validation and this module's fixtures share a single
# definition of "a well-shaped entry".
CALENDAR_REGISTRY_KEYS = (
    "airline_iata", "origin_iata", "destination_iata", "start_at", "end_at",
)

# Fetch-outcome result codes for poll_loop.py. Not flash keys —
# companion/ never sees these. Every caller compares only against
# FETCH_OK; any other code is "did not sync this cycle", so a new code
# here never requires a caller change.
FETCH_OK = "fetch_ok"
FETCH_SKIPPED_UNCONFIGURED = "fetch_skipped_unconfigured"
FETCH_SKIPPED_THROTTLED = "fetch_skipped_throttled"
FETCH_REJECTED_URL = "fetch_rejected_url"
FETCH_FAILED = "fetch_failed"
# connect_calendar_url() only: the candidate URL answered but the secret
# could not be stored (nothing changed), or it was stored but the first
# registry write failed (the next poll cycle reads the feed).
FETCH_SAVE_FAILED = "fetch_save_failed"
FETCH_SAVED_UNREAD = "fetch_saved_unread"
# A companion save/clear changed the configured URL while this cycle's
# fetch was in flight (see refresh_calendar_registry()) - the stale
# fetch result is discarded rather than persisted, since the newer URL
# always wins.
FETCH_SUPERSEDED = "fetch_superseded"

# In-process write lock guarding the final tmp-write. Defence in depth
# only: this file's actual cross-process race (the poll oneshot's own
# process vs. companion's process) is closed by _calendar_registry_lock()
# below, not by this threading.Lock, which is invisible across processes.
_WRITE_LOCK = threading.Lock()

# Bounded wait for _calendar_registry_lock() below. Set comfortably above
# the calendar fetch's own per-request timeout so a save arriving
# mid-poll-cycle almost always succeeds once the cycle's own fetch
# finishes. Generous now that the fetch itself no longer runs under this
# lock (see refresh_calendar_registry()) - this timeout only ever bounds
# the brief load/throttle or reload/compare steps, never the network
# call.
CALENDAR_REGISTRY_LOCK_TIMEOUT_S = 15.0


def _calendar_registry_lock_path(state_dir):
    return os.path.join(state_dir, CALENDAR_REGISTRY_LOCK_FILENAME)


@contextlib.contextmanager
def _calendar_registry_lock(state_dir):
    """Cross-process advisory lock over calendar_rules.json's read-
    modify-write steps — a `threading.Lock` cannot cross the poll
    oneshot's and companion's separate processes.

    Delegates to `atomic_io`'s own `exclusive_lock()` (POSIX-only
    `fcntl.flock()` under the hood, degrading to no locking on a
    platform without `fcntl`), bounded by
    `CALENDAR_REGISTRY_LOCK_TIMEOUT_S`. Raises `TimeoutError` (via
    `LockBusy`, a subclass) rather than proceeding unlocked when the wait
    expires. Kept as this module's own name/contract since every caller
    here already expects it; the generalised lock now lives in
    `atomic_io` alongside `poll.lock` and `device_config.lock`.
    """
    with atomic_io.exclusive_lock(
            _calendar_registry_lock_path(state_dir), CALENDAR_REGISTRY_LOCK_TIMEOUT_S):
        yield


def calendar_rules_path(state_dir):
    """Join `state_dir` and `CALENDAR_RULES_FILENAME`. Lives outside the
    git-tracked tree, so `deploy/deploy.sh`'s rsync `--delete` never
    touches it.
    """
    return os.path.join(state_dir, CALENDAR_RULES_FILENAME)


def calendar_secret_path(state_dir):
    """Join `state_dir` and `CALENDAR_SECRET_FILENAME`. The filename is a
    fixed module constant, never derived from caller input, so a
    path-traversal payload in a submitted calendar URL is structurally
    impossible here.
    """
    return os.path.join(state_dir, CALENDAR_SECRET_FILENAME)


def calendar_is_configured(state_dir):
    """Return whether a calendar URL is on file, as a genuine `bool`.

    A permission-drifted file resolves to `False`, the same as an absent
    one — the feature is off either way. Widening this into a richer
    status would make every existing truthiness call site silently treat
    a drift as "configured". The one caller that needs "off because it
    drifted" apart from plain "off" uses the separate
    `calendar_secret_mode_is_unsafe()` predicate.
    """
    return configured_calendar_url(state_dir) is not None


def configured_calendar_url(state_dir):
    """Return the stripped calendar URL from
    `calendar_secret_path(state_dir)`, or `None`. The sole accessor of
    the value.

    Reads the file on every call, no cache, so a mid-session permission
    or content change is visible immediately. Checks
    `_calendar_secret_mode_is_safe()` before ever opening the file and
    refuses unless it is exactly `True` — checking the mode after opening
    would mean a drifted file's value was already read into memory by the
    time the drift was noticed. An `OSError` on open is treated as
    absent.

    This project's first on-disk secret outside `companion/auth.py`:
    never logged, never interpolated into an exception message, never
    written elsewhere. No `companion/` rendering, logging or flash call
    site ever touches this value.
    """
    path = calendar_secret_path(state_dir)
    if _calendar_secret_mode_is_safe(path) is not True:
        return None
    try:
        with open(path) as fh:
            raw = fh.read()
    except OSError:
        return None
    stripped = raw.strip()
    return stripped or None


def _normalise_calendar_entry(entry):
    """Rebuild one candidate registry entry from scratch into a
    well-shaped dict, or `None`. Never raises.

    Re-applies the same allowlists `ics.parse_ics_events()` used at parse
    time — key set must equal `CALENDAR_REGISTRY_KEYS` exactly, both
    airport codes and the airline code must match their regexes, both
    timestamps must be real numbers (`bool` rejected explicitly, since it
    is an `int` subclass), and `end_at` must not precede `start_at`.
    `calendar_rules.json` is operator-inspectable on the VPS, so every
    read re-validates rather than trusting a previous write.
    """
    if not isinstance(entry, dict) or set(entry.keys()) != set(CALENDAR_REGISTRY_KEYS):
        return None

    airline_iata = entry.get("airline_iata")
    origin_iata = entry.get("origin_iata")
    destination_iata = entry.get("destination_iata")
    start_at = entry.get("start_at")
    end_at = entry.get("end_at")

    if not isinstance(airline_iata, str) or not _AIRLINE_IATA_RE.match(airline_iata):
        return None
    if not isinstance(origin_iata, str) or not _AIRPORT_IATA_RE.match(origin_iata):
        return None
    if not isinstance(destination_iata, str) or not _AIRPORT_IATA_RE.match(destination_iata):
        return None
    if isinstance(start_at, bool) or not isinstance(start_at, (int, float)):
        return None
    if isinstance(end_at, bool) or not isinstance(end_at, (int, float)):
        return None

    start_at = float(start_at)
    end_at = float(end_at)
    # NaN/+-Infinity must be rejected explicitly: json parses them,
    # isinstance(nan, float) is True, and every comparison against NaN is
    # False, so the ordering guard below would silently pass them and a
    # NaN-timestamped hand-edited entry would become a permanent match.
    if not math.isfinite(start_at) or not math.isfinite(end_at):
        return None
    if end_at < start_at:
        return None

    return {
        "airline_iata": airline_iata,
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
        "start_at": start_at,
        "end_at": end_at,
    }


def _resolve_retention_now(now):
    """Resolve the retention clock for `_rebuild_capped_entries()`: return
    `time.time()` for `None`, a `bool`, a non-numeric value, a non-finite
    value, or a finite value that still cannot convert to a UTC datetime
    (e.g. `1e300` overflows `datetime.fromtimestamp()`); otherwise return
    `float(now)`.

    Without this guard, a hostile or absent `now` reaching
    `_rebuild_capped_entries()` would erase a valid registry (via
    `select_window_entries()`'s own `[]`-on-bad-`now` behaviour) instead
    of merely trimming it. Proves convertibility with the same
    `datetime.fromtimestamp(now, tz=timezone.utc)` call
    `_window_filtered_entries()` uses, rather than trusting
    `math.isfinite()` alone as a proxy.
    """
    if isinstance(now, bool) or not isinstance(now, (int, float)):
        return time.time()
    now = float(now)
    if not math.isfinite(now):
        return time.time()
    try:
        datetime.fromtimestamp(now, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return time.time()
    return now


def _rebuild_capped_entries(raw_entries, context, now):
    """Rebuild every entry via `_normalise_calendar_entry()`, window, then
    cap the survivors at `CALENDAR_MAX_ENTRIES`, printing (never raising)
    a drop-count warning naming `context` when anything anomalous was
    dropped. `now` is required, resolved via `_resolve_retention_now()`.

    Windows first, then caps: capping raw entries in file order before
    windowing can discard every future flight when a feed lists history
    first. Raw examination is separately bounded by
    `CALENDAR_MAX_RAW_EXAMINED` before normalisation, since a hand-edited
    file's size is otherwise unbounded. The drop count excludes entries
    merely outside the window — that is routine, not an anomaly.
    """
    if not isinstance(raw_entries, list):
        return []

    examined = raw_entries[:CALENDAR_MAX_RAW_EXAMINED]
    examined_remainder = len(raw_entries) - len(examined)

    survivors = []
    rejected = 0
    for raw_entry in examined:
        normalised = _normalise_calendar_entry(raw_entry)
        if normalised is None:
            rejected += 1
            continue
        survivors.append(normalised)

    resolved_now = _resolve_retention_now(now)
    windowed_all = _window_filtered_entries(survivors, resolved_now)
    cap_remainder = max(0, len(windowed_all) - CALENDAR_MAX_ENTRIES)

    dropped = rejected + examined_remainder + cap_remainder
    if dropped:
        print(
            "calendar_rules: %s dropped %d entr%s (malformed/unsafe, beyond "
            "the %d-entry raw-examination ceiling, or beyond the %d-entry "
            "cap after windowing)"
            % (context, dropped, "y" if dropped == 1 else "ies",
               CALENDAR_MAX_RAW_EXAMINED, CALENDAR_MAX_ENTRIES),
            file=sys.stderr,
        )
    return windowed_all[:CALENDAR_MAX_ENTRIES]


def load_calendar_registry(state_dir, now=None):
    """Read `{state_dir}/calendar_rules.json`. Never raises.

    A missing/unreadable file, invalid JSON, or any shape other than a
    dict all yield the empty shape: `entries: []`, `last_attempt_at:
    None`, `last_synced_at: None`. Every entry is rebuilt from scratch via
    `_rebuild_capped_entries()` — never the parsed dict reused directly —
    since this file is operator-inspectable and a hand-edited entry is a
    tamper vector. `now` (default: real current time) is the retention
    clock threaded through to the same windowing `write_calendar_registry()`
    uses, so loader and writer agree on the window by construction.

    Two timestamps, two domains: `last_attempt_at` is a float epoch used
    by `calendar_fetch_is_due()`'s throttle arithmetic; `last_synced_at`
    is an ISO-8601 string used only by the companion's status display,
    and updates only on a successful parse. Conflating them would either
    hammer a broken feed every cycle or hide a persistently failing
    feed's staleness from the operator.
    """
    try:
        with open(calendar_rules_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    entries = _rebuild_capped_entries(data.get("entries"), "load_calendar_registry()", now)

    last_attempt_at = data.get("last_attempt_at")
    if isinstance(last_attempt_at, bool) or not isinstance(last_attempt_at, (int, float)):
        last_attempt_at = None
    else:
        last_attempt_at = float(last_attempt_at)

    last_synced_at = data.get("last_synced_at")
    if not isinstance(last_synced_at, str):
        last_synced_at = None

    return {
        "entries": entries,
        "last_attempt_at": last_attempt_at,
        "last_synced_at": last_synced_at,
    }


def write_calendar_registry(state_dir, entries, last_attempt_at, last_synced_at, now=None):
    """Replace `{state_dir}/calendar_rules.json` whole with `entries`,
    `last_attempt_at` and `last_synced_at`. Returns `True`/`False`, never
    raises.

    Replaces, never merges or appends — a past flight expires by
    replacement, not by a cleanup pass; merging would resurrect entries
    the rolling window exists to drop. `entries` are rebuilt through the
    same gates `load_calendar_registry()` applies (via
    `_rebuild_capped_entries()`), so a caller can never persist what the
    loader would only drop again on the next read. Written through
    `atomic_io.atomic_write()` (a unique-name temp file, fsynced, then
    `os.replace()`), tolerating any failure — an unsupported data shape,
    a write error, a failed rename — by leaving the previous file
    untouched.

    `now` is the retention clock (distinct from `last_attempt_at`, the
    throttle clock, which is recorded verbatim and may be `None` or in
    the past).
    """
    with _WRITE_LOCK:
        capped_entries = _rebuild_capped_entries(
            entries if isinstance(entries, list) else [], "write_calendar_registry()", now)

        if isinstance(last_attempt_at, bool) or not isinstance(last_attempt_at, (int, float)):
            normalised_attempt = None
        else:
            normalised_attempt = float(last_attempt_at)
        normalised_synced = last_synced_at if isinstance(last_synced_at, str) else None

        registry = {
            "entries": capped_entries,
            "last_attempt_at": normalised_attempt,
            "last_synced_at": normalised_synced,
        }

        path = calendar_rules_path(state_dir)
        try:
            os.makedirs(state_dir, exist_ok=True)
            atomic_io.atomic_write(path, json.dumps(registry, indent=1))
        except Exception:
            return False

    return True


def save_calendar_url(state_dir, value, now=None):
    """Write, replace, or clear the calendar URL at
    `calendar_secret_path(state_dir)`. Returns `True`/`False`, never
    raises.

    `value is CLEAR_CALENDAR_URL` (identity only) erases the registry
    first, then removes the file, tolerating only `FileNotFoundError` —
    "disconnected" must mean nothing of the schedule remains even if
    removal then fails. Any other value must be non-empty after strip,
    else this returns `False` with no side effect. The set/replace branch
    stages the new secret through `atomic_io.staged_write(mode=0o600)` —
    written, fsynced and 0600 from creation before any byte is visible at
    the final path — then erases the registry inside that staged write's
    block, publishing the new secret with `commit()` only once the erase
    succeeded; not calling `commit()` leaves the previous secret and
    registry untouched.

    Runs under `_calendar_registry_lock()` (not `_WRITE_LOCK`, already
    held non-reentrantly by `write_calendar_registry()`) around the whole
    sequence. Stores `_normalise_calendar_url()`'s output, never the raw
    input, and never logs the value on any path.
    """
    if value is CLEAR_CALENDAR_URL:
        clearing = True
    elif isinstance(value, str) and value.strip():
        clearing = False
    else:
        return False

    path = calendar_secret_path(state_dir)

    try:
        with _calendar_registry_lock(state_dir):
            if clearing:
                if not write_calendar_registry(state_dir, [], None, None, now=now):
                    return False
                try:
                    os.remove(path)
                except FileNotFoundError:
                    # Already absent — the one tolerated case; any other
                    # OSError falls through as a failure below.
                    pass
                except OSError:
                    return False
                return True

            # set/replace: stage the new secret first (written, fsynced,
            # 0600 at creation — caddy is in this file's group via
            # setgid on state_dir, so a umask-created file would be
            # group-readable, which is why the mode is set at creation
            # rather than a follow-up chmod), then erase the registry,
            # publishing the secret only if the erase succeeds.
            try:
                os.makedirs(state_dir, exist_ok=True)
                with atomic_io.staged_write(
                        path, _normalise_calendar_url(value.strip()), mode=0o600) as commit:
                    # The new secret is verified-written and durable at
                    # its temp file — only now does the previous
                    # calendar's registry get erased.
                    if not write_calendar_registry(state_dir, [], None, None, now=now):
                        return False
                    commit()
            except Exception:
                return False

            return True
    except TimeoutError:
        # The cross-process lock could not be acquired in time — report
        # the honest failure rather than proceed unlocked.
        return False


def _calendar_secret_mode_is_safe(path):
    """Read `path`'s permission bits without opening its contents.

    Returns `None` when the path does not exist (not a permission
    problem), `True` when the mode carries no group/other bits
    (owner-only), `False` otherwise. The absent case stays distinct from
    both booleans so a caller can tell "feature is off" apart from
    "feature is off because permissions drifted".
    """
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None
    return not (mode & (stat.S_IRWXG | stat.S_IRWXO))


def calendar_secret_mode_is_unsafe(state_dir):
    """`True` only when the secret file exists AND its mode carries a
    group or other bit. `False` both when it is owner-only and when it
    does not exist.

    Compares `is False` against `_calendar_secret_mode_is_safe()`'s
    three-valued result, never a bare negation — `not None` is `True` in
    Python, which would misreport an absent file as a permission problem.

    Deliberately narrow: stays a separate predicate from
    `calendar_is_configured()` rather than widening that function's bool
    contract, and does not repair the mode — a silent re-tightening would
    destroy the only evidence the secret was ever exposed.
    """
    return _calendar_secret_mode_is_safe(calendar_secret_path(state_dir)) is False


# --- Rolling window and throttle ---------------------------------------------


def calendar_fetch_is_due(last_attempt_at, now, min_interval_s=None):
    """May the throttled calendar fetch run on this cycle?

    Every pacing decision in this codebase is arithmetic over a persisted
    timestamp rather than an in-process scheduler, since the poll oneshot
    restarts fresh every cycle with no state of its own.

    Reads only `last_attempt_at` — updated on every attempt whether it
    succeeded or not, so an unreachable feed is contacted at most once
    per `min_interval_s`, never every cycle. Deliberately ignores
    `last_synced_at`, which tracks successful syncs for the companion's
    status display only.

    Defaults `min_interval_s` to `CALENDAR_FETCH_INTERVAL_S`. Returns
    `True` for a `None`/non-numeric `last_attempt_at`, or when elapsed
    time is negative (a clock step backwards must not wedge the throttle
    shut).
    """
    if min_interval_s is None:
        min_interval_s = CALENDAR_FETCH_INTERVAL_S
    if (last_attempt_at is None
            or isinstance(last_attempt_at, bool)
            or not isinstance(last_attempt_at, (int, float))):
        return True
    elapsed = now - last_attempt_at
    if elapsed < 0:
        return True
    return elapsed >= min_interval_s


def _window_filtered_entries(entries, now):
    """Shared window-filter-and-sort core behind `select_window_entries()`:
    the start of the current UTC day through
    `now + CALENDAR_WINDOW_FORWARD_S`, sorted ascending by `start_at`.
    Deliberately not capped at `CALENDAR_MAX_ENTRIES` — callers apply
    that themselves, since `_rebuild_capped_entries()` also needs the
    pre-cap count for its drop-count warning.

    Never mutates `entries`. Never raises — a malformed entry is skipped.
    """
    if not isinstance(entries, list):
        return []

    try:
        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        day_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    except (OverflowError, OSError, ValueError, TypeError):
        return []
    forward_edge = now + CALENDAR_WINDOW_FORWARD_S

    kept = []
    for entry in entries:
        normalised = _normalise_calendar_entry(entry)
        if normalised is None:
            continue
        if normalised["end_at"] < day_start:
            continue
        if normalised["start_at"] > forward_edge:
            continue
        kept.append(normalised)

    kept.sort(key=lambda entry: entry["start_at"])
    return kept


def select_window_entries(entries, now):
    """Reduce `entries` to the rolling window: the start of the current
    UTC day through `now + CALENDAR_WINDOW_FORWARD_S`. Returns a new
    list, sorted ascending by `start_at`, capped at `CALENDAR_MAX_ENTRIES`.
    Never mutates `entries`, never raises.

    The back edge (day-start, not a shorter look-back) is always further
    back than the match tolerance `match.py` applies, so no entry is
    ever dropped from the window while `match_calendar_theme()` would
    still consider it in range. A narrower window is otherwise preferred,
    since this data is a named person's near-term work schedule.
    """
    return _window_filtered_entries(entries, now)[:CALENDAR_MAX_ENTRIES]


def _normalise_calendar_url(url):
    """Rewrite a `webcal://` scheme to `https://`; every other URL,
    including one `urlparse()` cannot parse, is returned unchanged. Never
    raises.

    `webcal://` is Apple Calendar's share-link convention for "subscribe
    to this iCal feed" — the actual fetch is ordinary HTTPS. Runs before
    the package's `safe_fetch.url_is_safe()` gate, which stays a single
    unweakened `== "https"` check rather than growing a second accepted
    scheme. Never maps to plain `http`: the URL frequently carries an
    access token in its query string, and `webcal://` implies TLS in
    every client that emits it.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return url
    if parsed.scheme.lower() != "webcal":
        return url
    return urlunparse(parsed._replace(scheme="https"))
