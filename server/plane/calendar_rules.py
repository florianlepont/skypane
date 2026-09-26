#!/usr/bin/env python3
"""Calendar-sourced theme input: parses an operator's iCal feed into a
bounded list of match candidates for `match_calendar_theme()`.

Leaf module: stdlib + `requests` + `server.device_config` only. Never
import `colour_rules`, `enrich`, `detect`, `illustrations`,
`manual_resolutions` or `render` — `poll_loop.py` calls this module before
`colour_rules`, so a back-import would create an import cycle.

The registry (`{state_dir}/calendar_rules.json`) lives outside the
git-tracked tree so it survives a redeploy. Persisted entries carry only
five keys (airline, origin, destination, start, end) — this data is a
named person's work schedule, so nothing else is retained.
"""
import contextlib
import json
import math
import os
import re
import socket
import stat
import sys
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse

from server import atomic_io, device_config, http_fetch

# --- Constants -------------------------------------------------------------

# Self-identification for this module's one outbound call, matching
# detect.py's/enrich.py's own USER_AGENT convention.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 16 calendar-linked flight highlighting; "
    "see server/README.md for what this traffic is)"
)

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

# Ceiling on how many raw candidates (VEVENT blocks in parse_ics_events(),
# raw registry entries in _rebuild_capped_entries()) are examined before
# CALENDAR_MAX_ENTRIES is applied — and applied only to what survives the
# retention window, never to raw feed/file order. A cap applied in raw
# order before windowing can discard every future flight when a feed
# lists history first; this bound only guards against pathological feed
# size.
CALENDAR_MAX_RAW_EXAMINED = 5000

# Minimum seconds between fetch *attempts*. A crew roster republishes at
# most a few times a day, well below this interval.
CALENDAR_FETCH_INTERVAL_S = 1800

# Per-request (connect/read) timeout, clamped further per hop to the
# time left under CALENDAR_FETCH_DEADLINE_S below - generous for a small
# iCal feed, short enough that a hung upstream never meaningfully delays
# the 30s poll cycle.
CALENDAR_FETCH_TIMEOUT_S = 5.0

# Total wall-clock deadline across every hop of one fetch_ics() call
# (the original request plus every redirect it follows) - CALENDAR_FETCH_
# TIMEOUT_S alone only bounds a single connect/read, so a feed trickling
# one byte at a time across several hops could otherwise run far longer
# than that. Worst case per call is this plus one more read timeout: the
# chunk in flight when the deadline check fires can still take up to
# CALENDAR_FETCH_TIMEOUT_S to arrive before the loop notices.
CALENDAR_FETCH_DEADLINE_S = 10.0

# Hard response-size cap, enforced by streaming rather than trusting a
# response's own declared-length header, which a hostile or misconfigured
# server can omit, understate or exceed. 2 MiB comfortably exceeds any
# plausible multi-month roster export.
CALENDAR_MAX_RESPONSE_BYTES = 2 * 1024 * 1024

# Bounded redirect-following; each hop is re-validated against the same
# SSRF gate as the original URL, never trusted transitively.
CALENDAR_MAX_REDIRECTS = 5

# Rolling-window retention width in seconds: today plus 48h forward.
CALENDAR_WINDOW_FORWARD_S = 172800

# Per-match tolerance in seconds around a calendar entry's DTSTART/DTEND:
# generous enough to absorb ordinary delay, tight enough that same-route
# rotations roughly eight hours apart are never ambiguously close.
CALENDAR_MATCH_TOLERANCE_S = 5400

# The one CATEGORIES value that marks a VEVENT as a flight rather than
# duty-roster noise.
CATEGORY_FLIGHT = "FLT"

# STATUS value carried by cancelled/placeholder junk events; filtered
# before their (deliberately invalid) dates are ever parsed.
STATUS_CANCELLED = "CANCELLED"

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
# CALENDAR_FETCH_TIMEOUT_S so a save arriving mid-poll-cycle almost always
# succeeds once the cycle's own fetch finishes. Generous now that the
# fetch itself no longer runs under this lock (see refresh_calendar_
# registry()) - this timeout only ever bounds the brief load/throttle or
# reload/compare steps, never the network call.
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

# --- Compiled positive allowlists -------------------------------------------
#
# Each allowlist validates one untrusted feed value before it can reach a
# parsed entry.

# Matches "{flight token} {origin}-{destination}" with an optional
# trailing signed UTC-offset suffix. The offset is captured but unused —
# DTSTART/DTEND are already UTC, so it is informational only in this
# producer.
_SUMMARY_ROUTE_RE = re.compile(
    r"^(?P<flight>[A-Z0-9]{2,8})\s+(?P<origin>[A-Z]{3})-(?P<destination>[A-Z]{3})"
    r"(?:\((?P<offset>[+-]\d{4})\))?$"
)

# Two [A-Z0-9] characters with at least one letter, so an all-digit pair
# (never a real IATA airline code) is not mistaken for one.
_AIRLINE_IATA_RE = re.compile(r"^(?=.*[A-Z])[A-Z0-9]{2}$")

# Three uppercase letters: an IATA airport code.
_AIRPORT_IATA_RE = re.compile(r"^[A-Z]{3}$")

# This producer's only DTSTART/DTEND shape: bare UTC YYYYMMDDTHHMMSSZ.
# Anything else (e.g. a TZID-qualified value) is rejected, never guessed
# at.
_ICAL_UTC_RE = re.compile(r"^\d{8}T\d{6}Z$")

# Properties recorded per VEVENT block; every other property, including
# unknown X- extensions, is read and silently ignored.
_TRACKED_PROPERTIES = ("SUMMARY", "CATEGORIES", "STATUS", "DTSTART", "DTEND")


def unfold_ics_lines(raw_text):
    """RFC 5545 section 3.1 unfolding: rejoin a content line folded across
    physical lines into one logical line, before any property is split
    out of it. Must run first — splitting into properties off raw
    physical lines corrupts a folded continuation, which looks like a new
    malformed property instead of the previous one's tail.

    Normalises CRLF to LF. A continuation-shaped line with no previous
    logical line to join is kept as its own line. Non-string input
    returns `[]`. Never raises.
    """
    if not isinstance(raw_text, str):
        return []
    normalised = raw_text.replace("\r\n", "\n")
    logical_lines = []
    for line in normalised.split("\n"):
        if line[:1] in (" ", "\t") and logical_lines:
            logical_lines[-1] += line[1:]
        else:
            logical_lines.append(line)
    return logical_lines


def split_property(line):
    """Split one already-unfolded logical line into `(name, params, value)`.

    Partitions on the first colon: `DTSTART;VALUE=DATE-TIME:20260901T060000Z`
    yields name `DTSTART`, params `VALUE=DATE-TIME`, value
    `20260901T060000Z` — colons inside the value are left intact. A line
    with no colon returns `(None, None, None)`.
    """
    if not isinstance(line, str) or ":" not in line:
        return None, None, None
    name_and_params, _, value = line.partition(":")
    segments = name_and_params.split(";", 1)
    name = segments[0].strip().upper()
    params = segments[1] if len(segments) > 1 else ""
    return name, params, value


def parse_ics_datetime(value):
    """Parse this producer's one accepted DTSTART/DTEND shape — bare UTC
    `YYYYMMDDTHHMMSSZ` — into a float epoch. Returns `None` for anything
    else, including a calendrically impossible value (e.g. month 13).
    Never raises.
    """
    if not isinstance(value, str) or not _ICAL_UTC_RE.match(value):
        return None
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return parsed.timestamp()


def _build_entry(props):
    """Turn one closed VEVENT block's accumulated property dict into a
    five-key entry, or reject it. Returns `(entry_or_None, reason)`:
    `"date_form"` when the event was otherwise valid but its
    DTSTART/DTEND was not the bare-UTC form `parse_ics_datetime()`
    accepts, `"other"` for any other rejection, or `None` when accepted.

    Gate order is load-bearing: category, then STATUS, then SUMMARY
    shape, and only then the dates — an all-day event carrying a
    VALUE=DATE date must be rejected by the category gate before the date
    parser ever sees it, or it inflates the rejection count on an
    otherwise healthy feed.
    """
    categories_raw = props.get("CATEGORIES")
    categories = (
        [c.strip() for c in categories_raw.upper().split(",")]
        if isinstance(categories_raw, str)
        else []
    )
    if CATEGORY_FLIGHT not in categories:
        return None, "other"

    status_raw = props.get("STATUS")
    if isinstance(status_raw, str) and status_raw.strip().upper() == STATUS_CANCELLED:
        return None, "other"

    summary_raw = props.get("SUMMARY")
    if not isinstance(summary_raw, str):
        return None, "other"
    match = _SUMMARY_ROUTE_RE.match(summary_raw.strip())
    if match is None:
        return None, "other"

    flight = match.group("flight")
    origin = match.group("origin")
    destination = match.group("destination")
    if not _AIRLINE_IATA_RE.match(flight[:2]):
        return None, "other"
    if not _AIRPORT_IATA_RE.match(origin) or not _AIRPORT_IATA_RE.match(destination):
        return None, "other"

    # Dates are parsed only after category/status/summary have already
    # passed.
    start_at = parse_ics_datetime(props.get("DTSTART"))
    end_at = parse_ics_datetime(props.get("DTEND"))
    if start_at is None or end_at is None:
        return None, "date_form"
    if end_at < start_at:
        return None, "other"

    entry = {
        "airline_iata": flight[:2],
        "origin_iata": origin,
        "destination_iata": destination,
        "start_at": start_at,
        "end_at": end_at,
    }
    return entry, None


def parse_ics_events(raw_text):
    """Parse an untrusted iCal feed body into a bounded, sorted list of
    match-candidate entries (ascending by `start_at`). Never raises.

    Unfolds first, then walks logical lines accumulating one property
    dict per `BEGIN:VEVENT` .. `END:VEVENT` block, tracking
    nested-component depth so a nested VALARM's own END never closes the
    VEVENT early and its properties never overwrite the parent's. A block
    opened but never closed is discarded. Each closed block goes through
    `_build_entry()`'s ordered gates before its dates are parsed; a
    surviving entry is rebuilt from scratch as a five-key dict, never the
    raw property dict, so no unvalidated key or free-text field can reach
    the result.

    Stops the instant `CALENDAR_MAX_RAW_EXAMINED` surviving entries have
    been collected (a DoS bound, well above any plausible feed size).
    Rejections are counted in two buckets (`date_form`, `other`) and, if
    either is non-zero, one line naming both counts — never a rejected
    value or a DTSTART — is printed to stderr, since a rejected flight
    time is a named person's schedule.
    """
    if not isinstance(raw_text, str):
        return []

    try:
        lines = unfold_ics_lines(raw_text)
    except Exception:
        return []

    entries = []
    rejected_date_form = 0
    rejected_other = 0
    in_event = False
    current = None
    # Depth of any component nested inside the open VEVENT (e.g. a VALARM
    # Apple Calendar attaches to an event with an alert). Tracking depth
    # keeps a nested END from closing the VEVENT early and keeps a nested
    # property (e.g. the VALARM's own DESCRIPTION) from overwriting the
    # parent's.
    nested_depth = 0

    try:
        for line in lines:
            name, _params, value = split_property(line)
            if name is None:
                continue
            value_upper = value.strip().upper() if isinstance(value, str) else ""

            if name == "BEGIN":
                if value_upper == "VEVENT":
                    in_event = True
                    current = {}
                    nested_depth = 0
                elif in_event:
                    nested_depth += 1
                continue

            if name == "END":
                if value_upper != "VEVENT":
                    # A non-VEVENT END: never ends the VEVENT, never
                    # discards `current`.
                    if in_event and nested_depth > 0:
                        nested_depth -= 1
                    continue
                if in_event and current is not None:
                    entry, reason = _build_entry(current)
                    if entry is not None:
                        entries.append(entry)
                    elif reason == "date_form":
                        rejected_date_form += 1
                    elif reason == "other":
                        rejected_other += 1
                in_event = False
                current = None
                nested_depth = 0
                if len(entries) >= CALENDAR_MAX_RAW_EXAMINED:
                    break
                continue

            # nested_depth == 0 keeps a nested component's own properties
            # out of the parent event.
            if in_event and current is not None and nested_depth == 0 and name in _TRACKED_PROPERTIES:
                current[name] = value
    except Exception:
        # Defence in depth: every branch above is already guarded, but a
        # hostile/malformed feed must never abort the poll cycle no
        # matter what — degrade to whatever survived so far.
        pass

    if rejected_date_form or rejected_other:
        print(
            "calendar_rules: parse_ics_events() dropped %d event(s) "
            "(%d rejected for an unrecognised date form, %d for another reason)"
            % (rejected_date_form + rejected_other, rejected_date_form, rejected_other),
            file=sys.stderr,
        )

    entries.sort(key=lambda entry: entry["start_at"])
    return entries


# --- Registry file contract -------------------------------------------------


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

    Re-applies the same allowlists `parse_ics_events()` used at parse
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
    back than `CALENDAR_MATCH_TOLERANCE_S`, so no entry is ever dropped
    from the window while `match_calendar_theme()` would still consider
    it in range. A narrower window is otherwise preferred, since this
    data is a named person's near-term work schedule.
    """
    return _window_filtered_entries(entries, now)[:CALENDAR_MAX_ENTRIES]


# --- Bounded, SSRF-hardened fetch --------------------------------------------
#
# This project's first outbound request to an operator-chosen host, and
# its first runtime secret outside companion/auth.py. Four independent
# bounds apply together: the resolved address must be public on every
# redirect hop (not only the configured URL), the response body is
# capped while streamed, the request has a hard timeout, and redirects
# are bounded. Exception logging here deliberately logs only the
# exception type, never the exception object — several requests
# exceptions embed the request URL, which carries the calendar's access
# token, in their default string form.


def _address_is_public(ip_text):
    """`True` when `ip_text` parses as a public unicast address, `False`
    otherwise — including on a parse failure.

    Delegates to `http_fetch.address_is_public()` — the identical
    classification `pinned_request()`'s own resolution check applies, so
    this early gate and the real connection agree by construction on
    what counts as public.
    """
    return http_fetch.address_is_public(ip_text)


def _host_is_safe(hostname, port=None):
    """`True` only when every address `hostname` resolves to is a public
    unicast address; `False` on a resolution failure or if even one
    resolved address is not public.

    An early refusal only — this resolution is never reused by the real
    connection. The actual protection against a changed DNS answer (DNS
    rebinding) is that `default_calendar_transport()` goes through
    `http_fetch`'s own pinned request primitive, which resolves once more
    of its own accord, checks every address that second resolution
    returns, and connects only to one it already checked — never
    re-resolving between the check and the connect. This function's own
    resolve-then-check is
    still useful as a cheap, early "obviously unsafe" refusal (e.g. a
    literal loopback/private/link-local address needs no network fetch to
    reject), and every redirect hop repeats it before ever calling the
    transport. Never raises.
    """
    try:
        infos = socket.getaddrinfo(hostname, port)
    except (socket.gaierror, UnicodeError, OSError):
        return False
    if not infos:
        return False
    for info in infos:
        sockaddr = info[4]
        address_text = sockaddr[0]
        if not _address_is_public(address_text):
            return False
    return True


def _normalise_calendar_url(url):
    """Rewrite a `webcal://` scheme to `https://`; every other URL,
    including one `urlparse()` cannot parse, is returned unchanged. Never
    raises.

    `webcal://` is Apple Calendar's share-link convention for "subscribe
    to this iCal feed" — the actual fetch is ordinary HTTPS. Runs before
    `_url_is_safe()`, which stays a single unweakened `== "https"` check
    rather than growing a second accepted scheme. Never maps to plain
    `http`: the URL frequently carries an access token in its query
    string, and `webcal://` implies TLS in every client that emits it.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return url
    if parsed.scheme.lower() != "webcal":
        return url
    return urlunparse(parsed._replace(scheme="https"))


def _url_is_safe(url):
    """`True` only when `url`'s scheme is exactly `https`, it has a
    hostname, and `_host_is_safe()` accepts every address that hostname
    resolves to. Never raises.

    Deliberately does not recognise `webcal` or any non-`https` scheme —
    every caller reaching this gate already runs `_normalise_calendar_url()`
    first, keeping "acceptable scheme" defined in one place.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    return _host_is_safe(hostname, port)


def default_calendar_transport(url, timeout):
    """GET `url` with this module's `USER_AGENT` through `http_fetch.
    pinned_request()`, returning the response object unread.

    `pinned_request()` resolves the hostname once, refuses the whole
    host unless every resolved address is public, and connects only to
    an address it already checked — closing the gap where a plain HTTP
    client call would re-resolve the hostname again at connect time (DNS
    rebinding: the address `_url_is_safe()` checked and the address the
    socket actually reaches could otherwise differ). It
    never follows a redirect itself, so `fetch_ics()` can re-validate
    each `Location` target through `_url_is_safe()` before following it
    — a hook a self-following client has no equivalent for. Bounded by
    `CALENDAR_FETCH_DEADLINE_S` (the total deadline across every hop —
    see `fetch_ics()`), on top of this call's own `timeout`. The
    injectable `transport` parameter lets tests replace this with a
    hermetic fake.
    """
    return http_fetch.pinned_request(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        deadline_s=CALENDAR_FETCH_DEADLINE_S,
    )


def fetch_ics(url, timeout=None, transport=None, max_redirects=None, max_bytes=None,
              deadline_s=None, clock=None):
    """Fetch `url` and return its decoded body text, or `None` on any
    refusal or failure. Never raises.

    Five independent bounds, all defaulting from this module's
    constants: `_url_is_safe()` re-checked on every redirect hop; one
    total wall-clock `deadline_s` across every hop combined (not just a
    per-request `timeout`) — checked before each hop and after every
    chunk, so a feed trickling one byte at a time across several
    redirects cannot run far longer than the deadline; the response is
    read in chunks with a running byte count, aborting past `max_bytes`
    rather than trusting a declared length; a per-hop `timeout`, clamped
    to `min(timeout, time left under the deadline)`; and at most
    `max_redirects` hops. Redirects are never followed automatically
    (`default_calendar_transport()`'s underlying `pinned_request()` never
    follows one) — each `Location` target is re-validated before being
    requested.

    The only paths that log are the transport-exception and deadline-
    exceeded catches, which log `type(exc).__name__` only, never the
    exception object — several `requests.exceptions.*` subclasses embed
    the request URL, which carries the calendar's access token, in their
    default string form.

    `url` is normalised once, before the redirect loop, so a hand-edited
    secret file (bypassing `save_calendar_url()`'s own normalisation)
    still resolves a `webcal://` scheme. Redirect targets are not
    separately normalised — a `Location` header is a live HTTP response,
    never a calendar-client convention.
    """
    if timeout is None:
        timeout = CALENDAR_FETCH_TIMEOUT_S
    if max_redirects is None:
        max_redirects = CALENDAR_MAX_REDIRECTS
    if max_bytes is None:
        max_bytes = CALENDAR_MAX_RESPONSE_BYTES
    if deadline_s is None:
        deadline_s = CALENDAR_FETCH_DEADLINE_S
    if clock is None:
        clock = time.monotonic
    if transport is None:
        transport = default_calendar_transport

    deadline = clock() + deadline_s
    current_url = _normalise_calendar_url(url)
    for _ in range(max_redirects + 1):
        if not _url_is_safe(current_url):
            return None

        try:
            time_left = deadline - clock()
            if time_left <= 0:
                raise http_fetch.DeadlineExceeded(
                    "fetch_ics: total deadline exceeded before a hop")
            response = transport(current_url, min(timeout, time_left))
        except Exception as exc:
            # Deliberately broad: a caller-supplied fake transport or a
            # future requests version is not guaranteed to only raise
            # RequestException, and this fetch must never abort a poll
            # cycle. Logs the exception type only, never `exc` itself or
            # the URL — see this function's own docstring.
            print(
                "calendar_rules: fetch_ics() transport call failed: %s"
                % type(exc).__name__,
                file=sys.stderr,
            )
            return None

        if getattr(response, "is_redirect", False):
            location = response.headers.get("Location")
            response.close()
            if not location:
                return None
            current_url = urljoin(current_url, location)
            continue

        if response.status_code != 200:
            response.close()
            return None

        chunks = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                total += len(chunk)
                if total > max_bytes:
                    response.close()
                    return None
                chunks.append(chunk)
                if clock() > deadline:
                    raise http_fetch.DeadlineExceeded(
                        "fetch_ics: total deadline exceeded while reading the response")
        except Exception as exc:
            # Deliberately broad - see the transport-call catch above.
            print(
                "calendar_rules: fetch_ics() reading the response body failed: %s"
                % type(exc).__name__,
                file=sys.stderr,
            )
            response.close()
            return None
        response.close()
        return b"".join(chunks).decode("utf-8", errors="replace")

    # Too many redirect hops - give up rather than loop.
    return None


# --- Once-per-cycle throttle, fetch, parse, window and persist step ---------
#
# The single function poll_loop.py calls once per cycle. Performs no
# network I/O when the feature is unconfigured or the throttle has not
# elapsed, since the fetch must never delay a render.


def refresh_calendar_registry(state_dir, now, transport=None, min_interval_s=None):
    """Throttle, fetch, parse, window and persist the calendar registry
    for this poll cycle. Returns `(result_code, registry)`, always a
    usable dict. Never raises.

    No transport call when unconfigured, or when the throttle has not
    elapsed (the dominant case — the poll timer fires every 30s against a
    much longer interval). `min_interval_s=0` lets the Settings save
    bypass the throttle for one attempt, so connecting a calendar is not
    silently delayed up to half an hour.

    Three steps, each under its own brief lock acquisition — the network
    fetch itself runs with NO lock held, so a companion save or disconnect
    never waits behind it: (1) under the lock, load the registry, decide
    unconfigured/throttled/due, and — only when due — record the attempt
    (`last_attempt_at = now`) before releasing; (2) without the lock, fetch
    and parse; (3) under the lock again, reload the registry and re-read
    the configured URL. If it no longer matches the URL this attempt
    fetched (a companion save or disconnect landed while the fetch was in
    flight), the stale result is discarded entirely — nothing is written,
    and `FETCH_SUPERSEDED` is returned with the reloaded (newer) registry;
    the newer URL always wins over this cycle's own fetch. Otherwise a
    failed fetch re-persists the previous entries unchanged (the attempt
    was already recorded in step 1), and a successful one persists the
    windowed parse with `last_synced_at` derived from `now` — the
    injected clock, never the wall clock.

    `last_attempt_at` updates on every attempt that runs; `last_synced_at`
    only after a body was fetched, parsed, and found to still match the
    configured URL. An empty result on genuine success is a legitimate
    empty window, distinguishable from a broken feed only by
    `last_synced_at` having moved.

    Prints nothing on the throttled/unconfigured paths (near-every-cycle
    volume); at most one line, never the URL, once step 3 has a verdict.
    The same `now` threads through every registry call here, so a
    re-persist stays correctly windowed and byte-equal to disk.
    """
    # Wrapped so nothing escapes: every callee is already never-raising,
    # but this function must never gain a new failure mode from a future
    # change to a callee. Also absorbs TimeoutError from
    # _calendar_registry_lock() below — a stuck holder degrades this
    # cycle to FETCH_FAILED rather than wedging the poll loop.
    try:
        with _calendar_registry_lock(state_dir):
            registry = load_calendar_registry(state_dir, now)

            url = configured_calendar_url(state_dir)
            if url is None:
                # Not a failing feed - a feature that is simply off.
                # Leaving last_attempt_at untouched means the first fetch
                # after configuring runs immediately.
                return FETCH_SKIPPED_UNCONFIGURED, registry

            if not calendar_fetch_is_due(registry["last_attempt_at"], now, min_interval_s):
                return FETCH_SKIPPED_THROTTLED, registry

            # Record the attempt now, before the lock is released and the
            # fetch begins: a second refresh starting while this one's
            # fetch is still in flight must see the throttle correctly
            # (the normal 30s-cycle-against-30-minute-interval case),
            # rather than racing this same fetch.
            write_calendar_registry(
                state_dir, registry["entries"], now, registry["last_synced_at"], now=now)

        # Outside the lock: the network fetch never blocks a companion
        # save or disconnect (see this function's own docstring).
        body = fetch_ics(url, transport=transport)
        windowed = select_window_entries(parse_ics_events(body), now) if body is not None else None

        with _calendar_registry_lock(state_dir):
            reloaded = load_calendar_registry(state_dir, now)
            current_url = configured_calendar_url(state_dir)

            if current_url != url:
                # The configured URL changed or was cleared while this
                # fetch was in flight - the newer URL always wins, so
                # this cycle's own result (success or failure) is
                # discarded rather than persisted.
                print(
                    "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                    % (FETCH_SUPERSEDED, len(reloaded["entries"])),
                    file=sys.stderr,
                )
                return FETCH_SUPERSEDED, reloaded

            if windowed is None:
                # A transient blip must not erase an otherwise-valid
                # window before its natural expiry - the attempt was
                # already recorded above, nothing else changes.
                print(
                    "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                    % (FETCH_FAILED, len(reloaded["entries"])),
                    file=sys.stderr,
                )
                return FETCH_FAILED, reloaded

            # An empty windowed result here is still success -
            # distinguishable from a broken feed only by last_synced_at
            # having moved.
            last_synced_at = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")
            wrote_ok = write_calendar_registry(state_dir, windowed, now, last_synced_at, now=now)
            result_registry = {
                "entries": windowed,
                "last_attempt_at": now,
                "last_synced_at": last_synced_at,
            }
            result_code = FETCH_OK if wrote_ok else FETCH_FAILED
            print(
                "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                % (result_code, len(result_registry["entries"])),
                file=sys.stderr,
            )
            return result_code, result_registry
    except Exception:
        # Defence in depth only - see the comment above. Fall back to
        # whatever is durably on disk rather than propagate.
        return FETCH_FAILED, load_calendar_registry(state_dir, now)


# --- Matching -----------------------------------------------------------
#
# The pure function poll_loop.py calls at both of
# colour_rules.resolve_effective_theme_id()'s call sites, comparing a
# detected, enriched flight against the loaded registry and the
# operator's chosen theme.

# This module's own copies of runway_config.py's two confirmed
# render-state strings — duplicated rather than imported, to keep this
# module a leaf.
DEPARTING_STATE = "departing"
ARRIVING_STATE = "arriving"


def _airline_iata_from_route(route):
    """Derive the detected flight's 2-letter IATA airline code from
    `route["callsign_iata"]`'s leading two characters, or `None`.

    No lookup table needed: `callsign_iata`'s prefix already carries the
    IATA code alongside the 3-letter ICAO prefix `enrich.py` keys on — do
    not reintroduce a static ICAO-to-IATA mapping table here.

    Requires a string `callsign_iata`; the candidate must pass
    `_AIRLINE_IATA_RE`. Never raises.
    """
    if not isinstance(route, dict):
        return None
    callsign_iata = route.get("callsign_iata")
    if not isinstance(callsign_iata, str):
        return None
    candidate = callsign_iata.strip().upper()[:2]
    if _AIRLINE_IATA_RE.match(candidate):
        return candidate
    return None


def _far_end_iata(route, render_state):
    """The detected flight's "far end" airport for this direction: the
    destination for a departure, the origin for an arrival. `None` for a
    non-dict `route` or an unrecognised `render_state`.

    Paired with `_entry_far_end_iata()` below so the match is always
    destination-against-destination or origin-against-origin, never
    crossed.
    """
    if not isinstance(route, dict):
        return None
    if render_state == DEPARTING_STATE:
        return route.get("destination_iata")
    if render_state == ARRIVING_STATE:
        return route.get("origin_iata")
    return None


def _entry_far_end_iata(entry, render_state):
    """`_far_end_iata()`'s mirror for a registry entry: `destination_iata`
    for a departure, `origin_iata` for an arrival. `None` otherwise.
    """
    if not isinstance(entry, dict):
        return None
    if render_state == DEPARTING_STATE:
        return entry.get("destination_iata")
    if render_state == ARRIVING_STATE:
        return entry.get("origin_iata")
    return None


def _reference_time(entry, render_state):
    """The moment a calendar entry is measured against for this
    direction: `start_at` for a departure (near off-blocks), `end_at` for
    an arrival (near on-blocks). `None` otherwise.
    """
    if not isinstance(entry, dict):
        return None
    if render_state == DEPARTING_STATE:
        return entry.get("start_at")
    if render_state == ARRIVING_STATE:
        return entry.get("end_at")
    return None


def match_calendar_theme(registry, route, render_state, device_cfg, now):
    """Return the operator's configured calendar theme id when the
    detected, enriched `route` and `render_state` match at least one
    candidate entry in `registry` on airline, far-end airport and time;
    `None` otherwise. Never raises.

    Excludes the raw flight dict and the enrichment-provenance label:
    the match key never depends on the raw callsign — only 11% of Orly's
    dominant carrier's flights carry a commercial-looking IATA number,
    while `origin_iata`/`destination_iata` are populated on every
    enriched detection.

    Resolves the configured theme first (a string member of
    `device_config.THEMES`); requires a recognised `render_state`;
    requires `route` to carry non-empty origin/destination/callsign IATA
    (true only for a fresh or cached detection); derives the detected
    airline and far end; walks the registry, re-validating every entry
    from scratch (the file is operator-inspectable, so a previous
    writer's validation is never trusted); keeps entries matching on
    airline, far-end airport and a time within
    `CALENDAR_MATCH_TOLERANCE_S`; returns the theme when at least one
    candidate survives. A tie breaks deterministically so the result
    never depends on iteration order.

    The whole body is guarded: a malformed registry, route, config or
    clock returns `None` rather than raising — this runs inside the poll
    cycle and must never become a new way for a render to fail.
    """
    try:
        theme_id = device_cfg.get("calendar_theme_id") if isinstance(device_cfg, dict) else None
        if not isinstance(theme_id, str) or theme_id not in device_config.THEMES:
            return None

        if render_state not in (DEPARTING_STATE, ARRIVING_STATE):
            return None

        if not isinstance(route, dict):
            return None
        origin_iata = route.get("origin_iata")
        destination_iata = route.get("destination_iata")
        callsign_iata = route.get("callsign_iata")
        if not isinstance(origin_iata, str) or not origin_iata:
            return None
        if not isinstance(destination_iata, str) or not destination_iata:
            return None
        if not isinstance(callsign_iata, str) or not callsign_iata:
            return None
        if not _AIRPORT_IATA_RE.match(origin_iata) or not _AIRPORT_IATA_RE.match(destination_iata):
            return None

        detected_airline = _airline_iata_from_route(route)
        detected_far_end = _far_end_iata(route, render_state)
        if detected_airline is None or detected_far_end is None:
            return None

        if isinstance(now, bool) or not isinstance(now, (int, float)):
            return None

        raw_entries = registry.get("entries") if isinstance(registry, dict) else None
        if not isinstance(raw_entries, list):
            return None

        best = None  # (abs_diff, reference_time, tie_key) - smallest wins
        for raw_entry in raw_entries:
            normalised = _normalise_calendar_entry(raw_entry)
            if normalised is None:
                continue
            if normalised["airline_iata"] != detected_airline:
                continue
            if _entry_far_end_iata(normalised, render_state) != detected_far_end:
                continue
            reference_time = _reference_time(normalised, render_state)
            if reference_time is None:
                continue
            diff = abs(now - reference_time)
            if diff > CALENDAR_MATCH_TOLERANCE_S:
                continue
            tie_key = (
                normalised["airline_iata"], normalised["origin_iata"],
                normalised["destination_iata"], normalised["start_at"],
                normalised["end_at"],
            )
            candidate = (diff, reference_time, tie_key)
            if best is None or candidate < best:
                best = candidate

        if best is None:
            return None
        return theme_id
    except Exception:
        # Defence in depth - see docstring.
        return None
