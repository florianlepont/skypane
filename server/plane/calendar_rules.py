#!/usr/bin/env python3
"""Phase 16's calendar-sourced theme input: the operator's connected iCal
feed, parsed into a bounded list of match candidates.

Across this phase this module owns four things: the throttled, hardened
fetch of an operator-supplied iCal URL (plan 16-04), the hand-rolled RFC
5545 subset parser below (this plan, 16-01), a rolling-window registry
persisted at `{state_dir}/calendar_rules.json` (plan 16-03), and a pure
match function comparing a detected, enriched flight against that registry
(plan 16-06, `match_calendar_theme()`). This plan lands only the parser
half: `unfold_ics_lines()`, `split_property()`, `parse_ics_datetime()` and
`parse_ics_events()`, plus every constant and compiled allowlist the rest
of the phase's plans share.

**Leaf-import contract (copied, adapted, from `server/plane/colour_rules.py`'s
own docstring):** this module imports stdlib only (`re`, `sys`, `os`,
`json`, `threading`, `ipaddress`, `socket`, `urllib.parse`,
`datetime`/`timezone`) plus `requests` — already a pinned dependency used
by `detect.py` and `enrich.py`, so this plan's fetch step adds no new
entry to `server/requirements.txt` — plus, as of plan 16-06,
`server.device_config`, for the one membership test
`match_calendar_theme()` needs against `device_config.THEMES` (the exact
same single-module exception `colour_rules.py` itself carries, since
`device_config.py` is itself a leaf that imports neither this module nor
`colour_rules.py`). It must NEVER import `server.plane.colour_rules`,
`server.plane.enrich`, `server.plane.detect`,
`server.plane.illustrations`, `server.plane.manual_resolutions`, or
`server.plane.render`.

The `colour_rules` direction specifically is forbidden for a reason beyond
the general leaf-layering discipline every other name in that list already
carries: D-02's precedence between a calendar match and a manual rule is
wired the OTHER way round — `poll_loop.py` computes a `calendar_theme_id`
by calling this module's `match_calendar_theme()`, then passes that value
into `colour_rules.resolve_effective_theme_id()` as a plain keyword
argument. `colour_rules.py` never needs to know this module exists. If
this module ever imported `colour_rules` back, `poll_loop -> calendar_rules
-> colour_rules -> poll_loop` would be a real import cycle the moment
`poll_loop.py` also imports `calendar_rules` directly (it does, from plan
16-04 onward) — exactly the shape `colour_rules.py`'s own docstring already
warns against for its own five forbidden imports.

**Redeploy note (mirrors `colour_rules.py`/`manual_resolutions.py`):** once
plan 16-03 lands, the registry this module writes lives at
`{state_dir}/calendar_rules.json` — outside the git-tracked tree
`deploy/deploy.sh` rsyncs with `--delete`, so it survives a redeploy the
same way phase 15's colour-rule registry, `manual_resolutions.json`, and
`device_config.json` already do.

**Privacy clause:** this module's eventual persisted output describes a
named person's near-term work schedule (D-03's own framing) sitting on a
VPS. A persisted or in-memory record therefore carries the minimum the
matcher needs and nothing else — see `parse_ics_events()`'s five-key
entry shape below, which never carries a flight number, a UID, a summary
or a description. D-03's rolling window (plan 16-03) is what bounds how
long that minimum is retained; this plan's job is to make sure the minimum
itself is never exceeded even before a registry exists to expire it from.
"""
import contextlib
import errno
import ipaddress
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

import requests

from server import device_config

# CR-01 fix: `fcntl.flock()` is the cross-process lock `_calendar_registry_
# lock()` below is built on. POSIX-only — present on both of this project's
# real targets (Linux in production, macOS in development) but absent on
# Windows, which this project does not target. Imported defensively rather
# than assumed, so a future port to an unsupported platform degrades (see
# `_calendar_registry_lock()`'s own comment) instead of failing at import
# time.
try:
    import fcntl
except ImportError:  # pragma: no cover - not exercised on this project's targets
    fcntl = None

# --- Constants -------------------------------------------------------------

# Self-identification for the one outbound call this module makes, in
# detect.py's/enrich.py's own shape (detect.py:72-76, enrich.py's
# USER_AGENT). A calendar provider is not a rate-limited public service
# the way the ADS-B aggregators are, but naming this traffic honestly
# costs nothing and matches the codebase's one existing convention for
# every outbound request.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 16 calendar-linked flight highlighting; "
    "see server/README.md for what this traffic is)"
)

# The registry's on-disk filename, mirroring COLOUR_RULES_FILENAME /
# MANUAL_RESOLUTIONS_FILENAME's naming convention. Not read by any code
# until plan 16-03 adds the load/save functions.
CALENDAR_RULES_FILENAME = "calendar_rules.json"

# Phase 17's on-disk home for this secret (D-01/D-03). The environment
# variable that used to carry this value is retired outright, name and
# all — this file is now the only source, and nothing in this module
# reads the process environment for it under any name. Holds a
# subscription credential — the operator's calendar feed URL — so
# it lives inside `state_dir` like every other piece of durable state:
# neither `deploy/skypane-companion.service` nor `deploy/skypane-poll.service`
# needs a new `ReadWritePaths=` entry, both already declare this path. And
# because `deploy/deploy.sh` rsyncs `server/` with `--delete` while
# excluding the state directory, this file survives a redeploy the same
# way `calendar_rules.json`, `manual_resolutions.json` and
# `device_config.json` already do. See `save_calendar_url()` below for why
# this is the one file in this module whose mode is not a umask default.
CALENDAR_SECRET_FILENAME = "calendar_url.secret"

# CR-01 fix: the dedicated file `_calendar_registry_lock()` below takes an
# `fcntl.flock()` on. Deliberately a THIRD name, distinct from both
# CALENDAR_RULES_FILENAME and CALENDAR_SECRET_FILENAME — it holds no data
# of its own (its content, if any, is never read), so its mode does not
# need to match the secret's 0600, but it must never collide with either
# real path or a lock taken on one file would silently also gate the
# other.
CALENDAR_REGISTRY_LOCK_FILENAME = "calendar_rules.lock"

# Identity-compared clear sentinel (D-05), copied from
# `device_config.CLEAR_THEME_ARRIVING`'s shape verbatim: "clear the stored
# value" cannot be expressed by `None`, since `None` already means
# "not supplied, carry forward" everywhere on this write path. Consumed
# only by `save_calendar_url()`'s branch below, compared by `is` and never
# by equality, never parsed, never persisted, and never returned to any
# caller — so no value a crafted request could carry can ever collide
# with it.
CLEAR_CALENDAR_URL = object()

# Mirrors colour_rules.COLOUR_RULE_MAX_ENTRIES's role: a hard bound against
# a hostile/malformed feed, not a plausible one — a real 48h roster window
# measured well under ten events (16-CONTEXT.md finding 1). This bounds
# what may SURVIVE D-03's rolling retention window — see
# select_window_entries() and _rebuild_capped_entries() below — never raw
# feed/file order. Applying it before the window was UAT-02's bug: see
# CALENDAR_MAX_RAW_EXAMINED immediately below for the distinct bound that
# now guards the pre-window stage instead.
CALENDAR_MAX_ENTRIES = 200

# UAT-02 fix: a generous ceiling on how many raw candidates (VEVENT blocks
# in parse_ics_events(), raw registry-file entries in
# _rebuild_capped_entries()) are ever examined BEFORE CALENDAR_MAX_ENTRIES
# above is applied — and applied only to what survives D-03's retention
# window, never to raw feed/file order. This is a distinct, DoS-only bound
# from CALENDAR_MAX_ENTRIES: the fix for UAT-02 was discovering that a real
# feed listing history before future events made the OLD cap-in-raw-order
# behaviour discard every future flight, because the 200-entry cap filled
# up on historical events before the window ever got a chance to run. The
# developer's own subscription feed (16-CONTEXT.md's real-data
# measurement) carried 1074 real candidate entries across 1958 VEVENTs —
# comfortably inside this ceiling, so a legitimate feed/file is now
# examined in full; a pathological one (parsing note: "1e6 would not be
# fine") is still bounded.
CALENDAR_MAX_RAW_EXAMINED = 5000

# Minimum seconds between fetch *attempts* (plan 16-04's throttle). A crew
# roster is republished at most a few times a day; 30 minutes tracks that
# cadence without hammering the operator's host every 30s poll cycle.
CALENDAR_FETCH_INTERVAL_S = 1800

# Per-request timeout (plan 16-04). Generous for a small iCal feed, short
# enough that a hung upstream never meaningfully delays the 30s oneshot.
CALENDAR_FETCH_TIMEOUT_S = 10.0

# Hard response-size cap enforced by streaming, never by trusting a
# response's own declared-length header (plan 16-04, T-16-DOS) - a
# hostile or misconfigured server can omit, understate or exceed it.
# 2 MiB comfortably exceeds any plausible multi-month roster export.
CALENDAR_MAX_RESPONSE_BYTES = 2 * 1024 * 1024

# Bounded redirect-following (plan 16-04); each hop is re-validated against
# the same SSRF gate as the original URL, never trusted transitively.
CALENDAR_MAX_REDIRECTS = 5

# D-03's rolling-window retention width in seconds: today plus 48h forward
# (plan 16-03). The upper end of D-03's stated "24 to 48h" range.
CALENDAR_WINDOW_FORWARD_S = 172800

# Per-match tolerance in seconds around a calendar entry's DTSTART/DTEND
# (plan 16-06): generous enough to absorb ordinary delay (90 minutes),
# tight enough that the measured ~8h-apart NCE-ORY rotation pair is never
# ambiguously close.
CALENDAR_MATCH_TOLERANCE_S = 5400

# The one CATEGORIES value that marks a VEVENT as a flight rather than
# OFFD/CAHC/CPBL duty-roster noise (16-CONTEXT.md finding 1).
CATEGORY_FLIGHT = "FLT"

# The STATUS value the real export's two 1899-placeholder junk events
# carry; filtered before their (deliberately invalid) dates are ever
# parsed.
STATUS_CANCELLED = "CANCELLED"

# --- Registry file contract (plan 16-03) ------------------------------------
#
# calendar_rules.json's shape, D-01's separation from phase 15's rule
# store, and D-03's whole-file-rewrite rolling window. See
# calendar_rules_path(), load_calendar_registry() and
# write_calendar_registry() below.
# CALENDAR_RULES_FILENAME (D-01: deliberately not the filename phase 15's
# colour-rule registry uses — an automatic source must never overwrite,
# replace or delete a rule the operator typed by hand) is already
# declared above.

# The exact five-key shape parse_ics_events() emits, declared once so the
# loader's key-set validation and this harness's fixtures share a single
# definition of "a well-shaped entry" rather than two that could drift.
CALENDAR_REGISTRY_KEYS = (
    "airline_iata", "origin_iata", "destination_iata", "start_at", "end_at",
)

# Result constants for poll_loop.py's (plan 16-04) fetch outcome. These are
# NOT flash keys, mirroring colour_rules.py's own ADD_* comment: nothing
# about a flash exists at this tier, and companion/ never sees these.
FETCH_OK = "fetch_ok"
FETCH_SKIPPED_UNCONFIGURED = "fetch_skipped_unconfigured"
FETCH_SKIPPED_THROTTLED = "fetch_skipped_throttled"
FETCH_REJECTED_URL = "fetch_rejected_url"
FETCH_FAILED = "fetch_failed"

# WR-02-style fix (T-15-02's precedent, colour_rules.py:107-114), applied
# here as defence in depth even though it is not load-bearing the way it is
# for colour_rules.py's ThreadingHTTPServer writers: this file has a single
# writer — the poll oneshot's fetch step — never companion/'s concurrent
# request threads. The lock still wraps the entire load-check-mutate-write
# sequence, not just the final atomic replace, so a future second writer
# can never appear without this module already being race-safe against it.
#
# IN-01 (Phase 17 review): that "single writer" framing is about
# in-process request threads only — it does NOT mean this lock serializes
# against this module's actual second writer, which has existed since
# this file was written: `skypane-poll.service`'s own, separate OS
# process calling `refresh_calendar_registry()` versus
# `skypane-companion.service`'s own, separate OS process calling
# `save_calendar_url()`. A `threading.Lock` cannot ever be visible across
# two processes, no matter how it is reused or renamed — this lock only
# ever protects the final tmp-write against a same-process caller. The
# lock that actually closes the cross-process race (CR-01) is
# `_calendar_registry_lock()` immediately below, acquired around the
# ENTIRE read-modify-write sequence in both `refresh_calendar_registry()`
# and `save_calendar_url()`, not just the final replace.
_WRITE_LOCK = threading.Lock()

# CR-01 fix: bounded wait for `_calendar_registry_lock()` below. Set
# comfortably above `CALENDAR_FETCH_TIMEOUT_S` (10.0s) — the longest a
# legitimate holder should ever keep the lock is one `fetch_ics()` call
# plus a small JSON write — so a save arriving mid-poll-cycle almost
# always succeeds once the poll cycle's own fetch finishes, rather than
# failing on a lock that would have come free moments later.
CALENDAR_REGISTRY_LOCK_TIMEOUT_S = 15.0
CALENDAR_REGISTRY_LOCK_POLL_S = 0.05


def _calendar_registry_lock_path(state_dir):
    return os.path.join(state_dir, CALENDAR_REGISTRY_LOCK_FILENAME)


@contextlib.contextmanager
def _calendar_registry_lock(state_dir):
    """Cross-process advisory lock over calendar_rules.json's ENTIRE
    read-modify-write sequence (CR-01 fix).

    Why `_WRITE_LOCK` above cannot do this job: `skypane-poll.service`
    (`server/poll_loop.py`, a oneshot fired every 30s by its own systemd
    timer) and `skypane-companion.service` (`companion/app.py`, a
    long-running `ThreadingHTTPServer`) are two separate OS processes,
    each with its own Python interpreter and its own, unrelated copy of
    every module-level `threading.Lock()` in this file. A
    `threading.Lock` can only ever exclude other THREADS inside the SAME
    process's memory; it is invisible to a second process entirely, no
    matter how it is named, reused, or how confidently a docstring
    elsewhere claims otherwise (see the corrected comment on `_WRITE_LOCK`
    above, and D-09's corrected comment in `companion/app.py`).
    `fcntl.flock()` is a kernel-level primitive keyed on the lock file
    itself, so it is one of the few primitives genuinely shared by both
    services — both already run as the same `skypane` user against the
    same `state_dir` (`deploy/skypane-companion.service` and
    `deploy/skypane-poll.service`'s shared `ReadWritePaths=`).

    POSIX-only (`fcntl` is not available on Windows — see the import
    guard at the top of this module). Fine for this project's two real
    targets, Linux in production and macOS in development; a Windows
    port would need a different primitive (e.g. `msvcrt.locking`). On a
    platform without `fcntl` this degrades to no locking at all rather
    than raising at import time — a known, accepted gap for a platform
    this project does not ship to, not a silent guarantee that the race
    is closed there too.

    Acquisition is bounded, never blocking forever: polls for the lock
    every `CALENDAR_REGISTRY_LOCK_POLL_S` up to
    `CALENDAR_REGISTRY_LOCK_TIMEOUT_S`, then raises `TimeoutError` rather
    than proceeding unlocked — proceeding unlocked on timeout would
    silently reopen the exact race this lock exists to close. Both call
    sites (`refresh_calendar_registry()` and `save_calendar_url()`) catch
    this and degrade to their own existing failure contract (neither
    function ever raises out to its caller) instead of letting it escape.
    A stuck holder therefore costs the OTHER side at most
    `CALENDAR_REGISTRY_LOCK_TIMEOUT_S` seconds — it can never wedge the
    poll loop or an HTTP request indefinitely.

    Released in a `finally`, on every path including an exception raised
    by the caller's own body inside the `with` block.
    """
    if fcntl is None:
        # No cross-process primitive on this platform. Fall through
        # unlocked — a documented gap (see docstring above), not a crash.
        yield
        return

    os.makedirs(state_dir, exist_ok=True)
    path = _calendar_registry_lock_path(state_dir)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        deadline = time.monotonic() + CALENDAR_REGISTRY_LOCK_TIMEOUT_S
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "calendar_rules: timed out waiting for the cross-process "
                        "registry lock at %r" % (path,)
                    )
                time.sleep(CALENDAR_REGISTRY_LOCK_POLL_S)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)

# --- Compiled positive allowlists ------------------------------------------
#
# Styled exactly like colour_rules.py's own compiled-regex block: each
# allowlist is this module's share of the defence against an untrusted
# feed body smuggling a crafted value into a parsed entry (T-16-INPUT).

# A whole, stripped SUMMARY as "{flight token} {origin}-{destination}",
# with an optional trailing parenthesised signed four-digit UTC-offset
# suffix. The flight token's own charset ([A-Z0-9]{2,8}) mirrors
# colour_rules._CALLSIGN_RULE_RE's same eight-character real-world bound.
# The `offset` group is captured but never used for matching: it is the
# far end's *local* UTC offset, informational only in this producer — the
# authoritative times are DTSTART/DTEND, already UTC (CORRECTION 2).
_SUMMARY_ROUTE_RE = re.compile(
    r"^(?P<flight>[A-Z0-9]{2,8})\s+(?P<origin>[A-Z]{3})-(?P<destination>[A-Z]{3})"
    r"(?:\((?P<offset>[+-]\d{4})\))?$"
)

# Exactly two characters from [A-Z0-9], with a lookahead requiring at
# least one letter, so an all-digit pair (never a real IATA airline code)
# is not mistaken for one.
_AIRLINE_IATA_RE = re.compile(r"^(?=.*[A-Z])[A-Z0-9]{2}$")

# Exactly three uppercase letters, matching every real IATA airport code.
_AIRPORT_IATA_RE = re.compile(r"^[A-Z]{3}$")

# Exactly eight digits, the letter T, six digits and a trailing Z — this
# producer's one and only DTSTART/DTEND shape (CORRECTION 2: measured
# 63/63 real events, zero TZID). Anything else is rejected, never guessed.
_ICAL_UTC_RE = re.compile(r"^\d{8}T\d{6}Z$")

# Properties this parser records per VEVENT block; every other property,
# including any unrecognised X- extension, is read and silently ignored.
_TRACKED_PROPERTIES = ("SUMMARY", "CATEGORIES", "STATUS", "DTSTART", "DTEND")


def unfold_ics_lines(raw_text):
    """RFC 5545 section 3.1 unfolding: rejoin a content line folded across
    multiple physical lines into one logical line, BEFORE any property is
    ever split out of it.

    This must run first. Reversing the order — splitting into properties
    off the raw physical lines — silently corrupts exactly the long
    SUMMARY/DESCRIPTION values the rest of this module depends on: a
    folded continuation line looks like a new, malformed property instead
    of the tail of the previous one (16-RESEARCH.md Pitfall 1).

    Normalises CRLF to LF first (this producer's own export is LF-only,
    but a CRLF-terminated feed must unfold identically). Walks the
    resulting lines; whenever a line's first character is a SPACE or a
    HTAB *and* at least one logical line has already been started, that
    one leading marker character is stripped and the remainder is
    appended onto the previous logical line — never onto a new one.
    A continuation-shaped line at the very start of the text (no previous
    logical line to join onto) is kept as its own line rather than
    raising an IndexError.

    Non-string input returns an empty list. Never raises.
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

    Partitions on the FIRST colon only: everything before it is the
    name-and-parameters segment, everything after is the value. The bare
    property name is everything in that segment before its first
    semicolon, uppercased and stripped — so
    `DTSTART;VALUE=DATE-TIME:20260901T060000Z` yields the name `DTSTART`,
    the raw parameter segment `VALUE=DATE-TIME`, and the value
    `20260901T060000Z` with the value's own colons (if any) left intact
    (16-RESEARCH.md Pitfall 2).

    A line with no colon at all returns `(None, None, None)` — this
    producer is not known to ever emit a colon inside a quoted parameter
    value (a real, if rare, RFC 5545 possibility), so that shape is
    treated as explicitly out of the accepted subset: skipped by the
    caller, never guessed at.
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
    `YYYYMMDDTHHMMSSZ` — into a float epoch. Return `None` for anything
    else.

    CORRECTION 2 measured 63/63 real events in this shape with zero
    `TZID` parameters, so this function implements no second format, no
    `TZID` branch, and imports no timezone database (`zoneinfo`/`pytz`).
    A future producer change that starts emitting a `TZID`-qualified or
    `VALUE=DATE` value must fail loudly here — every caller counts and
    logs this rejection class separately (see `parse_ics_events()`) — not
    be silently mistimed by a guessed fallback format.

    `strptime()`'s own call is wrapped so a syntactically-shaped but
    calendrically impossible value (e.g. month 13) returns `None` rather
    than raising. Never raises.
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
    five-key entry, or reject it. Returns `(entry_or_None, reason)` where
    `reason` is `"date_form"` (the event was otherwise valid but its
    DTSTART/DTEND was not the bare-UTC form `parse_ics_datetime()`
    accepts — CORRECTION 2's tripwire), `"other"` (any other rejection
    reason: wrong category, cancelled, shape-invalid summary, invalid
    airline/airport code, or an end time before its start), or `None`
    (the event was accepted).

    Gate order is load-bearing and intentionally NOT reorderable: category
    first, then STATUS, then the SUMMARY shape, and only then the dates.
    Running the date parser before the category filter would make the
    fixture's all-day OFFD event (a VALUE=DATE value the date parser is
    required to reject) inflate the rejection count on a perfectly
    healthy feed — the category gate must dispose of it first, before the
    date parser is ever consulted (16-VALIDATION.md's own framing of this
    exact case).
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

    # Only now — after category, status and summary shape have all
    # already passed — does the date parser ever see this event.
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
    match-candidate entries. Never raises, regardless of input.

    Unfolds first (`unfold_ics_lines()`), then walks the logical lines,
    accumulating one property dict per `BEGIN:VEVENT` .. `END:VEVENT`
    block — recording only the last-seen value for each of
    `SUMMARY`/`CATEGORIES`/`STATUS`/`DTSTART`/`DTEND` and ignoring every
    other property, including unknown `X-` ones. A block that is opened
    but never closed before the text ends is discarded, never buffered to
    EOF as a live block (T-16-DOS).

    Each closed block goes through `_build_entry()`'s three ordered gates
    (category, status, summary shape) before its dates are ever parsed.
    A surviving entry is rebuilt from scratch as a five-key dict —
    `airline_iata`, `origin_iata`, `destination_iata`, `start_at`,
    `end_at` — never by reusing the accumulated property dict, so no
    unvalidated key, no flight number, no UID and no summary/description
    text can ever reach the returned list (T-16-INPUT, D-03's privacy
    reasoning).

    Accumulation stops the instant `CALENDAR_MAX_RAW_EXAMINED` surviving
    entries have been collected; nothing past that point is parsed at
    all. This is a DoS-only bound, deliberately far above any plausible
    feed size (UAT-02) — capping this loop at the SMALLER
    `CALENDAR_MAX_ENTRIES` was the bug a real Apple Calendar feed exposed:
    a real feed lists history before future events, so a 200-entry cap
    applied here, before this function's caller ever windows the result
    (`select_window_entries()`), silently discarded every future flight.
    `CALENDAR_MAX_ENTRIES` is still enforced — just downstream, by
    `select_window_entries()`, and only against what survives D-03's
    retention window rather than raw feed order. Rejections are counted
    in two separate, mutually exclusive
    buckets — `"date_form"` (CORRECTION 2's tripwire class) and `"other"`
    (everything else) — and when either count is non-zero, exactly one
    line naming both counts (never a rejected value, never a DTSTART,
    never a summary) is printed to stderr: a rejected flight time is a
    named person's schedule, and `journalctl` is readable by anyone with
    VPS access.

    Returns entries sorted ascending by `start_at`.
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
    # Depth of any component nested INSIDE the open VEVENT (VALARM being the
    # common one — Apple Calendar attaches one to any event carrying an
    # alert). RFC 5545 allows this, and two bugs live here if it is ignored:
    #
    #   1. Treating any `END:` as the VEVENT's own end closes the event early
    #      and discards it WITHOUT incrementing either rejection counter, so
    #      a perfectly valid flight vanishes and nothing is ever logged.
    #   2. Collecting properties while inside the nested component lets it
    #      overwrite the parent's — a VALARM's own DESCRIPTION would land on
    #      the flight.
    #
    # Both are avoided by tracking depth and only closing on `END:VEVENT`.
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
                    # Closing a nested component (or a stray END outside any
                    # event). Never ends the VEVENT, never discards `current`.
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

            # `nested_depth == 0` keeps a nested component's properties out of
            # the parent event — see the comment above.
            if in_event and current is not None and nested_depth == 0 and name in _TRACKED_PROPERTIES:
                current[name] = value
    except Exception:
        # Defence in depth: every branch above is already guarded, but a
        # hostile/malformed feed must never abort the poll cycle no
        # matter what (T-16-DOS) — degrade to whatever survived so far
        # rather than propagate.
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


# --- Registry file contract (plan 16-03, D-01/D-03) -------------------------


def calendar_rules_path(state_dir):
    """Join `state_dir` and `CALENDAR_RULES_FILENAME`.

    Mirrors `colour_rules.colour_rules_path()`. This file survives a
    redeploy because `deploy/deploy.sh` rsyncs `server/` with `--delete`
    while excluding the state directory, the same reason phase 15's
    colour-rule registry, `manual_resolutions.json`, and
    `device_config.json` already survive one.
    """
    return os.path.join(state_dir, CALENDAR_RULES_FILENAME)


def calendar_secret_path(state_dir):
    """Join `state_dir` and `CALENDAR_SECRET_FILENAME`.

    The filename is a module constant, declared once above, and is never
    derived from any caller-supplied value — a path-traversal payload
    embedded in a submitted calendar URL is therefore structurally
    impossible here, regardless of what content validation any caller of
    `save_calendar_url()` performs upstream. Mirrors `calendar_rules_path()`.
    """
    return os.path.join(state_dir, CALENDAR_SECRET_FILENAME)


def calendar_is_configured(state_dir):
    """Return whether a calendar URL is on file at
    `calendar_secret_path(state_dir)`, as a genuine `bool` — never the
    value itself, never a richer status.

    `return configured_calendar_url(state_dir) is not None` — the
    explicit identity comparison, not a truthiness test on the return,
    is what keeps this a genuine `bool` in all three reachable states:
    configured, absent, and permission-drifted (D-08). A drifted file
    resolves to the same `False` a genuinely absent one does — the
    feature is off either way, which is true — because widening this
    return into a status string would make every existing truthiness
    test at every existing call site silently read a permission-drift
    status as "configured". The one caller that needs to tell "off" from
    "off *because* the mode drifted" apart is the Settings status line,
    and it consults the separate, narrowly-scoped
    `calendar_secret_mode_is_unsafe()` predicate for that, never this
    one.

    This function exists precisely so a caller that only needs to render
    a configured-or-not status (companion/'s Settings status line, plan
    16-05) never touches the secret value: it must never be reimplemented
    as a truthiness test on `configured_calendar_url()`'s return inside a
    caller's own scope.

    An absent calendar is a designed, legitimate empty state (the
    feature is simply off), not an auth failure — the same fail-open
    register `configured_calendar_url()` below documents in full.
    """
    return configured_calendar_url(state_dir) is not None


def configured_calendar_url(state_dir):
    """Return the stripped calendar URL read from
    `calendar_secret_path(state_dir)`, or `None`. The sole accessor of
    the value.

    Reads the file on every call; nothing captured at import time and no
    module-level cache — a mid-session change to the file, or to its
    permissions, is visible on the very next call. Consults
    `_calendar_secret_mode_is_safe()` FIRST, before the file is ever
    opened, and returns `None` unless it is exactly `True` — the
    `is not True` shape, so both the absent case (`None` from the guard)
    and the drifted case (`False` from the guard) refuse through the
    same branch without a second one. This ordering is load-bearing, not
    incidental (D-02, T-17-DRIFT): checking the mode after opening the
    file would mean the value was already read into the process's memory
    by the time a drifted mode was noticed, which is exactly the outcome
    the guard exists to prevent.

    Only once the guard passes is the file opened, inside a `try`
    catching `OSError` so a race between the guard and the open (the file
    removed in between, say) fails the same way an absent file does. The
    read content is stripped before being returned — not cosmetic: a
    value read back from a file a human may later hand-edit routinely
    picks up a trailing newline in a way an environment variable never
    did, and an unstripped URL fails the fetch in a way that looks like a
    bad feed rather than a formatting artifact.

    The return value is this project's first on-disk secret outside
    `companion/auth.py` (T-16-SECRET, T-17-SECRET): it must never be
    logged, never interpolated into an exception message, and never
    written anywhere else in `state_dir`. It is no longer true that this
    value is "never returned to `companion/`" — that claim was true of
    `companion/`'s own module code and false of the companion's process
    even before this phase: `POST /poll-now` calls the poll cycle
    in-process, and that cycle refreshes the calendar, which reads this
    value. No process boundary ever existed here — all three systemd
    units run as the same user and load the same environment file. The
    honest property, carried forward from before this phase and true
    after it, is narrower and does not depend on a process boundary: no
    rendering, logging or flash call site anywhere under `companion/`
    ever touches this value, even though the companion process now
    legitimately both writes it (`save_calendar_url()`, plan 17-01) and
    reads it (this function, via the in-process poll trigger).
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
    """Rebuild one candidate registry entry from scratch, returning a
    fresh well-shaped dict or `None`. Never raises.

    Re-applies, on every call, the exact allowlists `parse_ics_events()`
    already applied at parse time: the key set must be exactly
    `CALENDAR_REGISTRY_KEYS` (not a subset, not a superset), both airport
    codes must match `_AIRPORT_IATA_RE`, the airline code must match
    `_AIRLINE_IATA_RE`, both timestamps must be real numbers with `bool`
    rejected explicitly (`bool` is an `int` subclass — the same guard
    `poll_loop._as_timestamp()` already applies), and `end_at` must not
    precede `start_at`. This is T-16-INPUT's defence: `calendar_rules.json`
    is operator-inspectable on the VPS, and a hand-edited entry is this
    tier's tamper vector, so every read re-validates rather than trusting
    what a previous write already checked.
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
    # NaN and +/-Infinity must be rejected explicitly. Python's json module
    # parses them by default, `isinstance(nan, float)` is True, and EVERY
    # comparison against NaN is False — so the `end_at < start_at` ordering
    # guard below silently passes them, and so does the D-03 window filter and
    # the D-04 match tolerance downstream. A single NaN-timestamped entry in a
    # hand-edited calendar_rules.json would therefore become a permanent,
    # unconditional match for its airline and route, immune to the clock.
    # That is exactly the tamper vector T-16-INPUT exists to close.
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
    `time.time()` for `None`, a `bool`, any non-`int`/`float` value, a
    non-finite (`NaN`/`+-Infinity`) value, or a finite value that still
    cannot be converted to a UTC datetime; otherwise return `float(now)`.

    This guard exists because `select_window_entries()` itself returns
    `[]` for any `now` it cannot convert to a UTC datetime (an unparseable
    value, an overflowing timestamp, `NaN`, `+-Infinity`). Without this
    resolver sitting in front of it, a hostile or simply absent `now`
    reaching `_rebuild_capped_entries()` would silently ERASE a
    perfectly valid registry instead of merely trimming it to the current
    window — turning a retention fix into a data-loss bug. Reuses
    `_normalise_calendar_entry()`'s own bool-reject-then-finite-check
    discipline verbatim, for the identical reason that function already
    documents at its own `start_at`/`end_at` guard.

    UF-16-05 closure (UAT-02): `math.isfinite()` alone is not enough. A
    value like `1e300` is entirely finite yet still overflows
    `datetime.fromtimestamp()` inside `select_window_entries()` — the
    exact same silent-erasure failure mode as `NaN` or `+-Infinity`, just
    reached through a different exception (`OverflowError` there, not the
    `isfinite()` check here). This function is the one call site that
    exists specifically to keep an absurd `now` from ever reaching that
    conversion, so it now proves convertibility directly — with the same
    `datetime.fromtimestamp(now, tz=timezone.utc)` call
    `_window_filtered_entries()` uses — rather than trusting `isfinite()`
    as a proxy for it.
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
    """Rebuild every entry in `raw_entries` from scratch via
    `_normalise_calendar_entry()`, apply D-03's rolling window via
    `_window_filtered_entries()` — the same edge-computation
    `select_window_entries()` itself uses, never recomputed here — and
    THEN cap the windowed survivors at `CALENDAR_MAX_ENTRIES`, printing
    — never raising — a one-line warning naming `context` and the drop
    count when anything genuinely anomalous was dropped (mirroring
    `load_colour_rules()`'s own `capped_remainder`-accounted warning).
    `now` is a REQUIRED third positional argument (not defaulted) so a
    future caller can never silently skip the window; a hostile, absent,
    or merely-absurd value is resolved to real current time by
    `_resolve_retention_now()` before it ever reaches
    `_window_filtered_entries()`.

    **UAT-02 fix — order: window first, then cap.** Before this fix, the
    cap was applied to `raw_entries` in raw file order BEFORE the window
    ever ran: the loop stopped the instant `CALENDAR_MAX_ENTRIES`
    survivors had accumulated, in whatever order `raw_entries` happened
    to list them. Proven against the developer's own real Apple Calendar
    subscription feed (1074 real candidate entries, spanning 2025-04 to
    2026-09): a real feed lists history before future events, so the
    surviving 200 were always the OLDEST 200 — every future flight sat
    beyond the cap boundary and was discarded before the window (which
    would have kept them) ever ran. The feature was structurally
    incapable of ever surfacing a flight. The fix reorders this: every
    examined raw entry that normalises cleanly is windowed FIRST, and
    `CALENDAR_MAX_ENTRIES` is applied only to what survives the window —
    the set that is actually relevant. **The cap is still fully
    enforced** — a file with more than `CALENDAR_MAX_ENTRIES` entries
    genuinely INSIDE the window is still truncated to the cap; only the
    window's edges (never raw file position) decide which survive.

    **Bounding raw examination is a separate concern from the cap.**
    Normalising every one of `raw_entries` before windowing is unbounded
    work in the one case this helper exists to defend against: an
    operator hand-edited `calendar_rules.json` (T-16-INPUT). Rather than
    resurrect the window-blind entry-cap this fix just removed, raw
    examination is bounded generously above any plausible legitimate
    registry size by `CALENDAR_MAX_RAW_EXAMINED` — only the first that
    many raw entries are ever normalised, regardless of validity or
    window membership. 1074 real entries is unremarkable and comfortably
    inside that ceiling; a file with orders of magnitude more (the
    hostile case) is still bounded.

    Three behaviours worth being explicit about, because each is a real
    consequence a future reader would otherwise trip over:

    - **The drop-count warning now covers three genuinely anomalous
      cases, and only those.** Malformed/unsafe entries, raw entries
      beyond the `CALENDAR_MAX_RAW_EXAMINED` examination ceiling, and
      well-formed IN-WINDOW entries that were still cut by the
      `CALENDAR_MAX_ENTRIES` cap — the last of these is `len()`-derived
      from `_window_filtered_entries()`'s own uncapped return, never a
      recomputed edge. Being outside the window is deliberately NOT
      folded into this count. That is this feature's designed steady
      state, and `load_calendar_registry()` runs on every companion page
      render — folding routine expiry into the same warning would flood
      the journal on every read of a file more than a day old and
      misclassify normal retention as a fault. This is what "truthful"
      means here: a calendar simply containing history must never print
      a scary warning; a hand-edited file with too many raw entries, or
      one that still overflows the cap after windowing, should.
    - **Sort.** `_window_filtered_entries()` (via `select_window_entries()`
      -equivalent ordering) returns its result sorted ascending by
      `start_at`, so both this helper's return value and (via
      `write_calendar_registry()`) the persisted file are always sorted.
    - **UF-16-05 closure.** `_resolve_retention_now()` now proves `now`
      is actually convertible to a UTC datetime, not merely finite — see
      that function's own docstring. A `None`, non-finite, OR
      finite-but-absurd (`1e300`) `now` all resolve to real current time
      before reaching the window, so none of them can erase a populated
      registry; they can only ever trim it.

    A non-list `raw_entries` (a hand-edited file whose `entries` key is
    not a list) returns an empty list without printing, since there is
    nothing to count as dropped versus what was never a candidate list to
    begin with. Never raises regardless of `raw_entries`'s or `now`'s
    shape.
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
    """Read `{state_dir}/calendar_rules.json`; never raises.

    A missing file, an unreadable file, invalid JSON, a JSON array, a
    JSON string, or a dict whose `entries` is not a list all yield the
    documented empty shape — a dict with `entries` mapping to `[]`,
    `last_attempt_at` mapping to `None`, and `last_synced_at` mapping to
    `None` — so every caller can index without a `.get()` dance.

    Every surviving entry is rebuilt from scratch by
    `_rebuild_capped_entries()` / `_normalise_calendar_entry()` — never
    the parsed dict reused directly — re-applying the same allowlists
    `parse_ics_events()` applied at parse time, because this file is
    operator-inspectable on the VPS and a hand-edited entry is this
    tier's tamper vector (T-16-INPUT). Raw examination stops at
    `CALENDAR_MAX_RAW_EXAMINED` entries (a DoS-only bound); the window is
    applied to what survives THAT, and only the windowed result is capped
    at `CALENDAR_MAX_ENTRIES` (UAT-02) — printing (never raising) a
    one-line drop-count warning when anything genuinely anomalous was
    dropped.

    `now` is D-03's retention clock, threaded through to
    `_rebuild_capped_entries()`, which applies D-03's rolling window
    (`select_window_entries()`) to the surviving entries before returning
    them — so a stale, out-of-window entry sitting on disk is never
    handed back to a caller, no matter how it got there. `None` (the
    default, and every existing call site's current shape) resolves to
    real current time. This is the loader half of the invariant this
    module's docstring already states: `load_calendar_registry()` and
    `write_calendar_registry()` agree on the window by construction,
    because both route every entry list through this one shared helper.

    Two timestamps, two domains, deliberately not interchangeable:
    `last_attempt_at` is normalised to a `float` epoch-seconds value (or
    `None`) because `calendar_fetch_is_due()` does arithmetic over it on
    every poll cycle, the same domain `poll_loop.now_s()` already uses.
    `last_synced_at` is normalised to a `str` (or `None`) because its
    only consumer, `companion/layout.py`'s `concise_timestamp_html()`,
    parses an ISO-8601 string the way `history_db.utc_now_iso()` already
    produces one. `last_attempt_at` updates on every fetch attempt and is
    the only thing the throttle consults; `last_synced_at` updates only
    on a successful parse and is the only thing the companion's status
    copy reads — conflating them either hammers a broken feed every 30
    seconds forever or hides a persistently failing feed's staleness
    from the operator.
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
    """Replace `{state_dir}/calendar_rules.json` WHOLE with `entries`,
    `last_attempt_at` and `last_synced_at`. Returns `True` on success,
    `False` on any failure; never raises.

    D-03 in one sentence: this function **replaces** the whole file, it
    never merges, appends to, or diffs against what was there before —
    that is what makes a past flight expire by replacement rather than by
    a cleanup pass, and a merge would resurrect exactly the entries the
    rolling window exists to drop.

    Under `_WRITE_LOCK` (this file's single writer today is the poll
    oneshot's fetch step, not `ThreadingHTTPServer`'s concurrent request
    threads — the lock here is defence in depth, not the load-bearing
    correctness property T-15-02 needed for phase 15's rule store): the
    incoming `entries` are rebuilt through the identical per-field gates
    `load_calendar_registry()` applies, via the shared
    `_rebuild_capped_entries()` helper — including D-03's rolling window,
    not merely the shape/cap gates — so a caller can never persist what
    the loader would only drop again on the next read. Then the
    tmp-write block is `colour_rules.py`'s shape verbatim — the state
    directory is created, the JSON is written to a temp filename
    embedding the process id and the thread id, dumped with an indent of
    one, atomically replaced onto the real path, and on any failure the
    temp file is removed (tolerating a failure to remove it) rather than
    raising.

    `now` is D-03's RETENTION clock, threaded into `_rebuild_capped_entries()`
    exactly like `load_calendar_registry()`'s own `now`. It is
    deliberately NOT the same thing as `last_attempt_at`, which is the
    THROTTLE clock recorded verbatim in the persisted file and may
    legitimately be `None` or a past value (`calendar_fetch_is_due()`
    reads it, unrelated to windowing) — conflating the two would tie this
    file's retention to the throttle's own pacing rather than to real
    time. `None` (the default) resolves to real current time.
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
        tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(tmp, "w") as fh:
                json.dump(registry, fh, indent=1)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            return False

    return True


def save_calendar_url(state_dir, value, now=None):
    """Write, replace, or clear the calendar subscription URL held at
    `calendar_secret_path(state_dir)`. Returns a genuine `True`/`False`;
    never raises — matching `write_calendar_registry()`'s own contract.

    `value is CLEAR_CALENDAR_URL` (identity only — never a truthiness or
    equality test, so the literal string `"CLEAR_CALENDAR_URL"` takes the
    ordinary write branch, not this one) takes the clear branch and
    removes the file, tolerating ONLY its own absence
    (`FileNotFoundError`) — CR-02 fix: every other `OSError` (permission
    denied, an immutable/read-only filesystem, ...) is a genuine removal
    failure and must be reported as `False`, never silently converted
    into a reported success the way a bare `except OSError: pass` did
    before this fix. Any other value must be a `str` whose `.strip()` is
    non-empty, or this function returns `False` immediately, having done
    nothing at all — no registry erase, no file write, no attempt.

    On the CLEAR branch, the fetched calendar registry is erased FIRST
    (`write_calendar_registry(state_dir, [], None, None, now=now)`),
    before the secret file is removed at all. This ordering is
    load-bearing, not incidental: "disconnected" has to mean nothing of a
    named person's schedule remains on the server (D-04), and doing the
    erase afterwards would let a failure to remove the file leave a
    disconnected calendar's flights on disk, exactly what D-04 forbids.
    If the erase call itself returns `False`, this function returns
    `False` without ever touching the secret file.

    On the SET/replace branch, the order is reversed from the clear
    branch on purpose (WR-01 fix): the NEW secret is written to a temp
    file and that write is verified to succeed FIRST; only once it has,
    the registry erase runs; only once THAT has succeeded does the final
    `os.replace()` make the new URL live. Before this fix the erase ran
    unconditionally before the secret write was even attempted, so a
    local write failure (disk full, `state_dir` briefly unwritable) left
    an already-working, still-connected calendar's just-erased flights
    gone for no reason the operator could act on, while the URL itself
    was untouched. Building and verifying the temp file first means a
    failure there touches neither the old secret nor the old registry —
    the call returns `False` having done nothing observable at all,
    matching every other rejected/failed path in this function. D-05's
    guarantee (no window with a new calendar's URL configured beside the
    previous calendar's flights) still holds: the erase still happens
    before the atomic rename that makes the new URL live, and for the
    whole duration of this function the cross-process registry lock
    below excludes any other reader or writer from observing an
    intermediate state at all.

    Acquires `_calendar_registry_lock()` (CR-01 fix) around the entire
    erase-then-write/write-then-erase sequence above — a cross-process,
    `fcntl`-based lock, NOT `_WRITE_LOCK`. `write_calendar_registry()`
    already acquires
    `_WRITE_LOCK` itself for its own final tmp-write, and that lock is
    non-reentrant, so taking it a second time here would deadlock the
    process on the first save; `_calendar_registry_lock()` is a
    different, dedicated lock file for exactly this reason, in addition
    to being the one primitive that is visible to
    `skypane-poll.service`'s own separate process — the actual second
    writer this function has always had to share the registry with. If
    the lock cannot be acquired within `CALENDAR_REGISTRY_LOCK_TIMEOUT_S`,
    the resulting `TimeoutError` is caught below and this function
    returns `False` rather than let it escape — never blocking an HTTP
    request indefinitely, matching this function's own never-raises
    contract. The temporary secret filename still embeds the process id
    and thread id, so two same-process concurrent callers never collide
    on it even though the registry lock already serializes them.

    The value itself must never be printed, logged, interpolated into an
    exception message, or included in any string this module emits to
    stderr — this function never does so, and the `except Exception`
    branch below deliberately discards the exception rather than
    formatting it.

    UAT-discovered defect fix (17-REVIEW.md, filed 2026-09-10): the
    SET/replace branch stores `_normalise_calendar_url(value.strip())`,
    not the raw stripped input — a `webcal://` URL is written to disk
    already rewritten to `https://`. Storing the normalised form (rather
    than what the operator pasted) is deliberate: `calendar_group()`
    (companion/pages/config_page.py) documents this field as write-only —
    the stored value is never rendered back to the operator in any of its
    four status states — so there is no UI cost to the two differing, and
    the upside is real: every reader of `configured_calendar_url()`
    (`fetch_ics()` via `refresh_calendar_registry()`, today, and any
    future caller) sees a single canonical scheme rather than needing its
    own copy of the `webcal` rewrite. `fetch_ics()` normalises again on
    its own input regardless — seeded specifically for a
    `calendar_rules.json`-adjacent secret file a human hand-edited
    directly on the VPS (state_dir is operator-inspectable), which never
    passed through this function at all.
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
                    # Already absent - the one tolerated case the
                    # docstring promises. Every OTHER OSError
                    # (permission denied, an immutable/read-only
                    # filesystem, ...) is a genuine failure and falls
                    # through to the `except OSError: return False`
                    # below rather than being swallowed here (CR-02 fix).
                    pass
                except OSError:
                    return False
                return True

            # set/replace: build and VERIFY the new secret in a temp file
            # BEFORE the registry erase runs (WR-01 fix - see docstring).
            tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
            try:
                os.makedirs(state_dir, exist_ok=True)
                # COPY THIS SHAPE VERBATIM (tmp-naming, makedirs,
                # os.replace, cleanup-on-exception) — but the file-open
                # call is NOT `open(tmp, "w")` like every other state
                # write in this codebase. Every other state write in
                # this file inherits the process umask (0644 in
                # practice). deploy/provision.sh puts `caddy` — the
                # internet-facing reverse proxy's own account — in this
                # file's group and sets setgid on the state directory,
                # so a umask-created file here would be readable by that
                # account. The mode is an argument to THIS call, the one
                # that creates the file, rather than a follow-up
                # os.chmod(), because applying it afterwards leaves a
                # window in which the file exists at the wider bits.
                # os.replace() below preserves the SOURCE file's mode
                # and silently discards the destination's, so the
                # temporary file's mode set here is the only one that
                # matters — getting it wrong produces no visible symptom
                # at all.
                # _normalise_calendar_url() rewrites only a `webcal://`
                # scheme to `https://` (see its own docstring) - every
                # other value, including an already-`https://` one,
                # round-trips through it completely unchanged. See this
                # function's own docstring for why the NORMALISED form is
                # what gets stored.
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as fh:
                    fh.write(_normalise_calendar_url(value.strip()))
            except Exception:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                return False

            # The new secret is verified-written and durable at `tmp` -
            # only now does the previous calendar's registry get erased
            # (WR-01 fix).
            if not write_calendar_registry(state_dir, [], None, None, now=now):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                return False

            try:
                os.replace(tmp, path)
            except OSError:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                return False

            return True
    except TimeoutError:
        # The cross-process registry lock could not be acquired within
        # CALENDAR_REGISTRY_LOCK_TIMEOUT_S - report the honest failure
        # rather than let TimeoutError escape this function's
        # never-raises contract, and never proceed unlocked.
        return False


def _calendar_secret_mode_is_safe(path):
    """Read `path`'s permission bits without ever opening its contents.

    Returns one of three distinguishable values, not a plain bool:
    `None` when `os.stat()` raises `OSError` — the file is simply absent,
    which is not a permission problem at all; `True` when
    `stat.S_IMODE(os.stat(path).st_mode)` shares no bit with
    `stat.S_IRWXG | stat.S_IRWXO` (owner-only); `False` otherwise (any
    group or other bit set).

    The absent case is kept as a distinct third value, not folded into
    either boolean, because a caller reporting status to the operator
    (plan 17-02's read path, and `calendar_secret_mode_is_unsafe()` below)
    has to be able to tell "the feature is off" apart from "the feature
    is off *because* something on the server changed" — collapsing the
    two here would make that distinction impossible one level up.
    """
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None
    return not (mode & (stat.S_IRWXG | stat.S_IRWXO))


def calendar_secret_mode_is_unsafe(state_dir):
    """`True` only when the secret file exists AND its permission bits
    carry any group or other bit. `False` both when the file is
    owner-only and when it does not exist at all (D-02, D-08).

    The `is False` comparison against `_calendar_secret_mode_is_safe()`'s
    three-valued result is deliberate and must never be relaxed to a bare
    negation: `not None` is `True` in Python, so negating the helper's
    result would report an absent file as a permission problem, which is
    exactly wrong.

    This predicate deliberately stays narrow rather than becoming a
    second way to answer "is the calendar configured?". Widening
    `calendar_is_configured()` from a bool into a status string would
    make every existing truthiness test at every existing call site
    silently read a permission-drift status as "configured" — a
    non-empty string is truthy — which is the exact failure D-02 exists
    to prevent. So `calendar_is_configured()` keeps its boolean contract
    and answers `False` for a drifted file (the feature genuinely is
    off, which is true), and this second, deliberately narrow predicate
    exists to answer one further question for one caller — the Settings
    status line: "off *because* of drift?" It must not acquire additional
    callers or additional return shapes.

    Deliberately does NOT repair the mode. A silent re-tightening would
    destroy the only evidence that the secret was ever exposed, and the
    value may already have been read by whoever widened it — the
    operator has to be told, not quietly rescued.
    """
    return _calendar_secret_mode_is_safe(calendar_secret_path(state_dir)) is False


# --- Rolling window and throttle (plan 16-03, D-03) -------------------------


def calendar_fetch_is_due(last_attempt_at, now, min_interval_s=None):
    """May the throttled calendar fetch run on this cycle?

    Written to `poll_loop.advance_is_due()`'s exact shape, because it
    answers the identical structural question — durable state, not a
    process timer: `deploy/skypane-poll.service` is `Type=oneshot`, fired
    fresh by `deploy/skypane-poll.timer` every 30 seconds, so there is no
    in-process scheduler to hold a next-fetch-due moment across cycles.
    Every pacing decision in this codebase is therefore arithmetic over a
    persisted timestamp, and this function is that arithmetic for the
    calendar fetch.

    Reads only `last_attempt_at`, which updates on **every** fetch
    attempt whether it succeeded or not — so a permanently unreachable
    feed is contacted at most once per `min_interval_s` rather than every
    30 seconds forever. It deliberately does **not** read
    `last_synced_at`, which updates only on a successful parse and exists
    solely so the companion's status copy can tell the operator when the
    feed last actually worked.

    `min_interval_s` defaults to `CALENDAR_FETCH_INTERVAL_S`. Returns
    `True` when `last_attempt_at` is `None`, is a `bool`, or is not a
    real number (a fresh or hand-edited state always fetches). Returns
    `True` when the elapsed time is negative — a clock step backwards
    must not wedge the feature into never fetching again. THIS FUNCTION
    defines no clock of its own: `now` is always passed in by its caller,
    keeping `poll_loop.now_s()` the codebase's one replaceable clock seam
    for the throttle decision. (This module as a whole is no longer
    clock-free: `_resolve_retention_now()` gives the retention window a
    default real-time seam of its own, used only by
    `_rebuild_capped_entries()` — a distinct clock for a distinct
    purpose, never consulted here.)
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
    """Shared window-filter-and-sort core behind `select_window_entries()`
    below: the start of the current UTC day through
    `now + CALENDAR_WINDOW_FORWARD_S`, sorted ascending by `start_at`.
    Deliberately NOT capped at `CALENDAR_MAX_ENTRIES` — callers apply that
    themselves, `select_window_entries()` by slicing its return, and
    `_rebuild_capped_entries()` by both slicing AND counting how much the
    slice cut, for its truthful drop-count warning (UAT-02). Splitting
    this out is what keeps `select_window_entries()` "the sole
    implementation of the window's two edges" true in fact as well as in
    name: `_rebuild_capped_entries()` needs the pre-cap count, but must
    never recompute the day-start edge, the forward edge, or
    `CALENDAR_WINDOW_FORWARD_S` itself to get it.

    Never mutates `entries`. Never raises — a malformed entry is skipped,
    not propagated.
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
    """Reduce `entries` to D-03's rolling window: the start of the current
    UTC day through `now + CALENDAR_WINDOW_FORWARD_S`. Returns a new
    list, sorted ascending by `start_at`, capped at `CALENDAR_MAX_ENTRIES`;
    never mutates `entries`. Never raises — a malformed entry is skipped,
    not propagated.

    The window width is this phase's resolution of a Claude's-Discretion
    point: D-03 specifies today plus 24 to 48 hours forward and leaves
    the exact width open. `CALENDAR_WINDOW_FORWARD_S` (48h) is that
    range's stated upper bound, which is what makes a roster published
    the evening before a two-sector day still useful. The back edge is
    the literal start of the current UTC day rather than an invented
    look-back, so the rule matches D-03's own words exactly.

    Safety property that makes the back edge correct rather than merely
    literal: the day-start edge is always further back than
    `CALENDAR_MATCH_TOLERANCE_S` (a UTC day is at least 23 hours; the
    match tolerance is 90 minutes), so no entry is ever dropped from the
    window while `match_calendar_theme()` (plan 16-06) would still
    consider it in range.

    Privacy clause: a narrower window is strictly better here, because
    this file holds a named person's near-term work schedule on a VPS,
    and D-03 rejected mirroring the whole feed for exactly that reason.

    This function's own contract (signature, ordering, sort guarantee) is
    unchanged by UAT-02's fix — only its internal edge-computation moved
    into the shared `_window_filtered_entries()` helper above, so every
    existing caller (`refresh_calendar_registry()`,
    `_rebuild_capped_entries()`, every test) sees byte-identical behaviour
    for the same input.
    """
    return _window_filtered_entries(entries, now)[:CALENDAR_MAX_ENTRIES]


# --- Bounded, SSRF-hardened fetch (plan 16-04, T-16-SSRF/T-16-DOS/T-16-SECRET) ----
#
# This is the project's first outbound request to a host the operator (not
# the developer) chose, and the calendar URL it fetches is this project's
# first runtime secret held outside companion/auth.py. Four independent
# bounds apply together, none sufficient alone: the resolved address must
# be public (checked on every redirect hop, not only the configured URL),
# the response body is capped while it is streamed, the request carries a
# hard timeout, and the redirect hop count is bounded. See
# 16-RESEARCH.md's "Bounded, IP-validated fetch skeleton" for the vetted
# shape this implements, and Pitfall 4 there for why this module's own
# exception-logging discipline deliberately diverges from detect.py's
# neighbouring caller-catch idiom (detect.py:950-958's
# "%s: %s" % (type(exc).__name__, exc) interpolates the exception object
# itself - several requests.exceptions.* subclasses embed the request URL,
# which here carries the calendar subscription token, in their default
# __str__()).


def _address_is_public(ip_text):
    """Return `True` when `ip_text` parses as a public unicast address,
    `False` otherwise - including when it fails to parse at all.

    Deliberately delegates range classification to the standard library
    (`ipaddress`) rather than hand-rolling CIDR arithmetic (16-RESEARCH.md's
    own "Don't Hand-Roll" guidance): `ipaddress.ip_address()` covers both
    IPv4 and IPv6 through the same call, and its `is_private`/`is_loopback`/
    `is_link_local`/`is_reserved`/`is_multicast`/`is_unspecified` properties
    are the audited, spec-following source of truth this project has no
    reason to reimplement. Returns `False` rather than raising on an
    unparseable value - an address this function cannot classify is treated
    as unsafe, never as safe-by-default.
    """
    try:
        address = ipaddress.ip_address(ip_text)
    except (ValueError, TypeError):
        return False
    if (address.is_private or address.is_loopback or address.is_link_local
            or address.is_reserved or address.is_multicast
            or address.is_unspecified):
        return False
    return True


def _host_is_safe(hostname, port=None):
    """Return `True` only when EVERY address `hostname` resolves to is a
    public unicast address; `False` on a resolution failure or if even one
    resolved address is not public.

    This function exists in this exact shape - resolve first, then check
    every returned address - because checking the hostname *string* against
    a blocklist and stopping there is defeated by DNS rebinding: the
    hostname can resolve to a public address at validation time and a
    private one at connection time, since nothing pins the two moments to
    the same answer. The addresses the resolver actually returns are
    therefore what must be checked, and a single private answer among
    several public ones is enough to refuse the whole hostname - accepting
    it on the strength of the public ones would let an attacker publish one
    good answer and one bad one and rely on the caller connecting to
    whichever happened to be tried.

    Never raises: a resolution failure (`socket.gaierror`), an unparseable
    hostname, or any other resolver error all return `False`.
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
    """Rewrite a `webcal://` scheme to `https://`, leaving every other URL
    (including one `urlparse()` cannot make sense of) completely
    unchanged. Never raises.

    UAT-discovered defect fix (17-REVIEW.md, filed 2026-09-10):
    `webcal://` is not a distinct transport - it is the de-facto
    convention Apple Calendar's own "Public Calendar" share links use to
    mean "subscribe to this iCal feed"; the actual fetch behind it is an
    ordinary HTTPS request. Before this fix, an operator pasting exactly
    the URL Apple Calendar hands them failed `_url_is_safe()`'s
    `parsed.scheme != "https"` check and got the generic sync-failure
    message, with no indication the URL itself was fine.

    This function is the ONLY place `webcal` is ever recognised, and it
    runs strictly BEFORE `_url_is_safe()` - the gate itself is untouched
    (still `parsed.scheme != "https"`, nothing added to that comparison).
    Normalising upstream, rather than teaching the gate a second
    acceptable scheme, keeps `_url_is_safe()` as the single, unweakened
    arbiter of what is safe to fetch: every rule it already enforces
    (https-only, a resolvable hostname, no private/link-local/reserved
    address, re-applied per redirect hop) applies identically to a
    `webcal://` URL once it reaches the gate as an ordinary `https://`
    one.

    Never maps `webcal` to plain `http`: `webcal://` implies TLS in
    every calendar client that emits it, and the URL frequently carries
    an access token in its query string, so silently downgrading it
    would leak that token over an unencrypted connection. There is no
    caller-facing way to ask for that downgrade - it is simply not a
    mapping this function knows.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return url
    if parsed.scheme.lower() != "webcal":
        return url
    return urlunparse(parsed._replace(scheme="https"))


def _url_is_safe(url):
    """Return `True` only when `url`'s scheme is exactly `https`, it has a
    hostname, and `_host_is_safe()` accepts every address that hostname
    resolves to. Never raises - a URL `urlparse()` itself cannot make sense
    of is refused, not guessed at.

    Deliberately does NOT recognise `webcal` itself (or any scheme other
    than `https`) - see `_normalise_calendar_url()` immediately above,
    which every caller reaching this gate (`fetch_ics()`, and
    `save_calendar_url()`'s stored-form choice) already runs first. This
    function staying a single, narrow `== "https"` comparison is what
    keeps it the one place "acceptable scheme" is defined, rather than
    letting that definition drift across two call sites.
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
    """Thin `requests.get()` wrapper, `enrich.default_transport()`'s exact
    shape: GET `url` with the module's `USER_AGENT`, `timeout`, streaming
    enabled and automatic redirect following disabled, returning the
    response object unread.

    `fetch_ics()`'s injectable `transport` parameter exists specifically so
    tests can replace this with a hermetic fake that replays a scripted
    response instead of making a live network call - see
    server/test_calendar_rules.py. Redirects are disabled here, not left to
    `requests`, because `fetch_ics()` must re-validate each `Location`
    target through `_url_is_safe()` before ever following it (T-16-SSRF) -
    something `requests`'s own automatic redirect handling has no hook for.
    """
    return requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        stream=True,
        allow_redirects=False,
    )


def fetch_ics(url, timeout=None, transport=None, max_redirects=None, max_bytes=None):
    """Fetch `url` and return its decoded body text, or `None` on any
    refusal or failure. Never raises.

    Four independent bounds are applied together, each insufficient alone:
    the scheme must be `https` and every resolved address must be public
    (checked via `_url_is_safe()`, re-applied to `url` on every redirect
    hop, not only the first); the response is read in chunks with a
    running byte count, aborting the instant it exceeds `max_bytes` -
    never by trusting a response's own declared-length header, which a
    hostile or misconfigured server can omit, understate or exceed; the
    request carries `timeout` seconds; and following at most
    `max_redirects` redirect hops, past
    which this function gives up rather than looping. All four default
    from this module's own constants (`CALENDAR_FETCH_TIMEOUT_S`,
    `CALENDAR_MAX_REDIRECTS`, `CALENDAR_MAX_RESPONSE_BYTES`) when not
    supplied.

    Redirects are never followed automatically (`default_calendar_transport()`
    disables it): a redirect response's `Location` target becomes the next
    loop iteration's URL, sent back through the identical `_url_is_safe()`
    gate before it is ever requested - a target that fails it is refused,
    exactly like the original URL. A relative `Location` is resolved
    against the current URL first. A redirect with no `Location` header, a
    non-200 final status, and an oversized streamed body all return `None`.

    Logging discipline (T-16-SECRET, this task's headline acceptance
    criterion): the only failure path in this function that logs at all is
    the transport-exception catch below, and it logs `type(exc).__name__`
    plus a fixed, hand-written description - never `exc` itself
    interpolated, because several `requests.exceptions.*` subclasses embed
    the request URL (which carries the calendar's access token) in their
    default string form, and `journalctl -u skypane-poll` is readable by
    anyone with VPS access. Nothing printed on any path in this function -
    including the success path - ever contains the URL, its host, its
    path, or its query. This continues a rule this project already states
    for its one other runtime secret (`poll_loop.py`'s own docstring:
    never log a bearer token or the BYOS setup secret), not a new one.

    UAT-discovered defect fix (17-REVIEW.md, filed 2026-09-10): `url` is
    run through `_normalise_calendar_url()` exactly once, here, before
    the redirect loop below ever starts - rewriting a `webcal://` scheme
    to `https://` so `_url_is_safe()`'s own gate (unchanged, still
    https-only) accepts it. This is the ONE choke point both callers that
    can reach this function - the companion's save-time sync and
    `poll_loop.py`'s regular cycle - already share via
    `refresh_calendar_registry()`, so normalising here covers both
    without either caller needing its own copy of this logic.
    `save_calendar_url()` ALSO normalises before writing (so the common
    case never round-trips a `webcal://` string through the state
    directory at all); normalising again here is what still converts a
    hand-edited `calendar_rules.json` secret file (state_dir is
    operator-inspectable on the VPS) that was never written through
    `save_calendar_url()`. Redirect targets discovered inside the loop
    below are NOT separately normalised - a `Location` header is a live
    HTTP response naming its own next hop, never a calendar-client
    convention, so there is no legitimate `webcal://` shape to expect
    there.
    """
    if timeout is None:
        timeout = CALENDAR_FETCH_TIMEOUT_S
    if max_redirects is None:
        max_redirects = CALENDAR_MAX_REDIRECTS
    if max_bytes is None:
        max_bytes = CALENDAR_MAX_RESPONSE_BYTES
    if transport is None:
        transport = default_calendar_transport

    current_url = _normalise_calendar_url(url)
    for _ in range(max_redirects + 1):
        if not _url_is_safe(current_url):
            return None

        try:
            response = transport(current_url, timeout)
        except Exception as exc:
            # Deliberately broad (not just requests.RequestException): "any
            # exception raised by the transport returns nothing rather than
            # propagating" (this function's own behaviour contract) - a
            # caller-supplied fake transport, or a future requests version,
            # is not guaranteed to only ever raise a RequestException
            # subclass, and this fetch must never abort a poll cycle no
            # matter what raised.
            #
            # Deliberate divergence from detect.py:950-958's caller-catch
            # idiom, which does "%s: %s" % (type(exc).__name__, exc) - see
            # this function's own docstring and Pitfall 4 in
            # 16-RESEARCH.md. Log the exception TYPE only, never `exc`
            # itself, and never the URL.
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
        except Exception as exc:
            # Deliberately broad - see the transport-call catch above.
            print(
                "calendar_rules: fetch_ics() reading the response body failed: %s"
                % type(exc).__name__,
                file=sys.stderr,
            )
            return None
        response.close()
        return b"".join(chunks).decode("utf-8", errors="replace")

    # Too many redirect hops - give up rather than loop.
    return None


# --- Once-per-cycle throttle, fetch, parse, window and persist step --------
#
# The single function poll_loop.py (plan 16-07) calls once per cycle. It
# performs no network I/O at all when the feature is unconfigured or the
# throttle has not elapsed, since 16-CONTEXT.md requires the fetch never
# delay a render and the 30-second poll oneshot's whole budget is short.


def refresh_calendar_registry(state_dir, now, transport=None, min_interval_s=None):
    """Throttle, fetch, parse, window and persist the calendar registry for
    this poll cycle. Returns `(result_code, registry)`, where `registry` is
    always the dict the caller should use for this cycle - so a skipped or
    failed cycle still hands back a usable rolling window without a second
    read of the file. Never raises, for any combination of a missing state
    dir, an unwritable state dir, a hostile body and a failing transport.

    Three no-network guarantees, in order: no transport call at all when
    `configured_calendar_url()` is `None` (the feature is off); no
    transport call when `calendar_fetch_is_due()` says the throttle has not
    elapsed - this is the branch that dominates in production, since the
    poll timer fires every 30 seconds and the interval is
    `CALENDAR_FETCH_INTERVAL_S`, so all but roughly one cycle in sixty stops
    here; and at most one bounded `fetch_ics()` call otherwise.

    `min_interval_s` is passed straight through to `calendar_fetch_is_due()`,
    which already resolves `None` to `CALENDAR_FETCH_INTERVAL_S` on its own -
    `None` is this function's default precisely so it preserves that
    resolution rather than choosing a second, competing default. `server/
    poll_loop.py`'s call passes nothing and therefore gets the standard
    interval, byte-for-byte the same pacing it had before this parameter
    existed. The only caller expected to pass anything else is the
    Settings save (D-06): connecting a calendar shortly after an unrelated
    poll cycle must not silently do nothing for up to half an hour, so
    that one call site passes `min_interval_s=0` to bypass the throttle for
    that single attempt. The poll loop's own throttle is otherwise
    untouched.

    `last_attempt_at` updates on every attempt that actually happens
    (throttled-through and unconfigured cycles leave it untouched);
    `last_synced_at` moves only after a body was fetched AND parsed, so a
    permanently failing feed is neither retried every cycle nor displayed
    as fresh. On a refused URL, a transport failure, or a body that parses
    to nothing usable, the previously persisted entries are re-persisted
    unchanged alongside the new `last_attempt_at` - overwriting them with
    an empty list on a transient error would erase an otherwise-valid
    rolling window before its natural expiry; the panel's designed
    degradation is "no matches" only once the window genuinely ages out.
    An empty result on a genuine success is still success: a roster with
    nothing in the next 48 hours is a correct, legitimately empty window,
    distinguishable from a broken feed only by `last_synced_at` having
    moved - which is exactly why the two timestamps are tracked
    separately.

    Prints nothing on the throttled or unconfigured paths - the throttled
    path runs on almost every cycle and would otherwise flood the journal.
    On a completed attempt (success or failure) prints at most one line
    naming this module, the result code and the entry count; never the URL,
    never the result code paired with the URL, never anything derived from
    the body.

    D-04, this function's whole reason for threading `now` into all four
    of its registry calls: the top-of-function `load_calendar_registry()`,
    both `write_calendar_registry()` calls, and the `except` fallback's
    `load_calendar_registry()` all receive the SAME `now`. Because the
    top-of-function load is now itself windowed (`load_calendar_registry()`
    routes through `_rebuild_capped_entries()`), the failure path's
    re-persist of `registry["entries"]` is correct WITHOUT gaining a trim
    call of its own - the list it re-persists was already windowed against
    this cycle's `now` by that load. One place owns the window invariant;
    the failure path inherits it for free. This is also what makes
    `result_registry["entries"]` byte-equal to what lands on disk on BOTH
    the success and the failure path: the same `now` windows both, so
    there is never a second, silently-diverging implementation and never
    a re-read of the file to reconcile the two.
    """
    # Wrapped so nothing escapes: every callee below is already
    # never-raising on its own, but this function's contract is that
    # poll_loop.run_once() (plan 16-07) can call it unconditionally and
    # never gain a new failure mode from this tier - defence in depth
    # against a future change to any callee above breaking that contract.
    # This same `except Exception` is also what absorbs `TimeoutError`
    # from `_calendar_registry_lock()` below (CR-01 fix) when the lock
    # cannot be acquired within CALENDAR_REGISTRY_LOCK_TIMEOUT_S - a stuck
    # holder degrades this cycle to FETCH_FAILED against whatever is
    # durably on disk, exactly like any other failure this function
    # already tolerates, rather than wedging the poll loop.
    try:
        # CR-01 fix: the ENTIRE load-throttle-fetch-write sequence runs
        # under the cross-process registry lock, not just the final
        # write - a lock that only covered write_calendar_registry()'s
        # own call would still let a concurrent save's erase land between
        # this function's `load` and its own `write`, which is exactly
        # the interleaving CR-01 found.
        with _calendar_registry_lock(state_dir):
            registry = load_calendar_registry(state_dir, now)

            url = configured_calendar_url(state_dir)
            if url is None:
                # Not a failing feed - a feature that is simply off. Leaving
                # last_attempt_at untouched means the first fetch after the
                # operator configures the feature runs immediately rather
                # than waiting out a full throttle interval.
                return FETCH_SKIPPED_UNCONFIGURED, registry

            if not calendar_fetch_is_due(registry["last_attempt_at"], now, min_interval_s):
                return FETCH_SKIPPED_THROTTLED, registry

            body = fetch_ics(url, transport=transport)

            if body is None:
                # A transient blip must not erase an otherwise-valid rolling
                # window before its natural expiry - persist the EXISTING
                # (already-windowed, per D-04 above) entries and
                # last_synced_at unchanged, moving only last_attempt_at.
                write_calendar_registry(
                    state_dir, registry["entries"], now, registry["last_synced_at"], now=now)
                result_registry = {
                    "entries": registry["entries"],
                    "last_attempt_at": now,
                    "last_synced_at": registry["last_synced_at"],
                }
                print(
                    "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                    % (FETCH_FAILED, len(result_registry["entries"])),
                    file=sys.stderr,
                )
                return FETCH_FAILED, result_registry

            parsed = parse_ics_events(body)
            windowed = select_window_entries(parsed, now)
            # An empty windowed result here is still success: a roster with
            # nothing in the next 48 hours is a correct, legitimately empty
            # window - distinguishable from a broken feed only by
            # last_synced_at having moved.
            last_synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
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


# --- Matching (plan 16-06, D-04) --------------------------------------------
#
# The pure function poll_loop.py (plan 16-07) calls at BOTH of
# colour_rules.resolve_effective_theme_id()'s call sites (D-13's
# both-branches invariant), comparing a detected, enriched flight against
# the loaded registry and the operator's chosen theme. Nothing above this
# section depends on it; everything below is new in this plan.

# This module's own copies of the two confirmed render-state strings
# (runway_config.py's STATE_DEPARTING/STATE_ARRIVING), following the exact
# comment colour_rules.py already carries for its own ARRIVING_STATE: the
# primitive is deliberately duplicated rather than imported, because
# importing runway_config would start eroding the leaf contract for a
# two-character saving.
DEPARTING_STATE = "departing"
ARRIVING_STATE = "arriving"


def _airline_iata_from_route(route):
    """Derive the detected flight's 2-letter IATA airline code from
    `route["callsign_iata"]`, or `None`.

    **CORRECTION 1 (16-RESEARCH.md, applied 2026-09-07) — read this before
    touching this function.** This research originally flagged, as its
    single most important open question, that the calendar encodes the
    airline as a 2-letter IATA prefix (e.g. `TO`) while `enrich.py`'s
    `_ICAO_AIRLINE_PREFIXES` is keyed on the 3-letter ICAO prefix (e.g.
    `TVF`) the detector actually sees, with nothing in this codebase
    bridging the two — and it recommended building a new static table to
    close that gap.

    **That table is unnecessary, and MUST NOT be built, here or anywhere.**
    The bridge already exists at runtime, in the same route dict this
    matcher already holds: `route["callsign_iata"]`'s leading two
    characters ARE the IATA airline code, sitting beside `airline_name`.
    Verified across 300 real cached flights spanning ten carriers (TVF/TO
    Transavia France, VLG/VY Vueling, EJU/EC easyJet Europe, CRL/SS
    Corsairfly, TAP/TP TAP Portugal, CCM/XK CCM Airlines, FWI/TX Air
    Caraïbes, RAM/AT Royal Air Maroc, DAH/AH Air Algerie, AFR/AF Air
    France) — every pair derives cleanly with no lookup. A static table
    would be a standing maintenance burden and a drift risk against
    `enrich._ICAO_AIRLINE_PREFIXES` for a lookup that is already free at
    runtime; do not reintroduce one.

    Requires `callsign_iata` to be a string; strips and uppercases it,
    takes its first two characters, and returns them only when they pass
    `_AIRLINE_IATA_RE` (at least one letter, no all-digit pair). Returns
    `None` for a non-dict `route`, a missing/non-string `callsign_iata`,
    or a leading pair that fails the allowlist. Never raises.
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
    non-dict `route` or any render state other than the two confirmed
    ones.

    Kept as a symmetric pair with `_entry_far_end_iata()` below, rather
    than inlined at each call site, so the direction symmetry the D-04
    match key requires is checkable at a glance: the comparison this
    module makes is always destination-against-destination or
    origin-against-origin, never destination-against-origin, so a leg
    flown the other way never matches an entry for the outbound.
    """
    if not isinstance(route, dict):
        return None
    if render_state == DEPARTING_STATE:
        return route.get("destination_iata")
    if render_state == ARRIVING_STATE:
        return route.get("origin_iata")
    return None


def _entry_far_end_iata(entry, render_state):
    """`_far_end_iata()`'s mirror for a calendar registry entry rather
    than a detected route: the entry's `destination_iata` for a
    departure, its `origin_iata` for an arrival. `None` for a non-dict
    `entry` or any render state other than the two confirmed ones.
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
    direction: `start_at` for a departure (the aircraft leaves near
    off-blocks), `end_at` for an arrival (it lands near on-blocks). `None`
    for a non-dict `entry` or any render state other than the two
    confirmed ones.
    """
    if not isinstance(entry, dict):
        return None
    if render_state == DEPARTING_STATE:
        return entry.get("start_at")
    if render_state == ARRIVING_STATE:
        return entry.get("end_at")
    return None


def match_calendar_theme(registry, route, render_state, device_cfg, now):
    """D-04's pure matcher: return the operator's configured calendar
    theme id when — and only when — the detected, enriched `route` and
    `render_state` agree with at least one candidate entry in `registry`
    on airline, far-end airport and time. Returns `None` otherwise. Never
    raises, for any combination of a non-dict `registry`, a non-list
    `entries` value, a malformed entry, a non-dict `route`, a non-dict
    `device_cfg` and a non-numeric `now`.

    Deliberately excludes both the flight dict and `resolve_route()`'s
    enrichment-provenance label from its parameter list. The flight dict
    is excluded because nothing in D-04's key comes from it — the airline
    comes from the enriched `route` and the direction from `render_state`
    — and an unused parameter would invite a future change to start
    matching on the raw callsign, which 16-CONTEXT.md's measured finding 2
    rules out: only 11% of the dominant Orly carrier's flights carry a
    commercial-looking IATA number, while `origin_iata`/`destination_iata`
    are populated on 100% of enriched detections. The provenance label is
    excluded because it is not meaningful at `poll_loop.py`'s second call
    site — the held/repaint branch reports the value `"held"` there — so a
    test against that label would silently disable the feature on every
    repaint, while the field-presence test in step 3 below is exactly
    equivalent to the `fresh_hit`/`cache_hit` restriction (CORRECTION 1)
    and works identically at both sites.

    Sequence:

    1. Resolve the operator's chosen theme first: read
       `device_cfg["calendar_theme_id"]`, require a string that is a
       member of `device_config.THEMES`, and return `None` immediately
       otherwise. Doing this first means an unconfigured or tampered
       theme costs no comparison work at all — this module's own share of
       T-16-TAMPER.
    2. Require `render_state` to be one of the two confirmed flight
       states.
    3. Require `route` to be a dict carrying all three of `origin_iata`,
       `destination_iata` and `callsign_iata` as non-empty strings, with
       both airport codes passing `_AIRPORT_IATA_RE`. This is
       CORRECTION 1's narrowing, encoded as a field-presence test: these
       three fields exist only on a `fresh_hit` or a `cache_hit` — see
       `enrich.airline_only_route()`, which sets all three to `None` for
       an `airline_only`/`manual` result — so this test is exactly the
       enrichment-provenance restriction, expressed in a form that is
       still true at the held call site.
    4. Derive the detected airline through `_airline_iata_from_route()`
       and the detected far end through `_far_end_iata()`; return `None`
       if either is missing.
    5. Walk the registry's entries, re-validating each one from scratch
       through `_normalise_calendar_entry()` (T-16-INPUT: a hand-edited
       `calendar_rules.json` is this tier's tamper vector, so this
       function never trusts that a previous writer already validated
       what it is reading) — skipping any entry that is not a dict or
       whose fields fail the same allowlists the loader applies. Keep an
       entry as a candidate when its `airline_iata` equals the detected
       airline, its own far end for this direction
       (`_entry_far_end_iata()`) equals the detected far end, and the
       absolute difference between `now` and its reference time
       (`_reference_time()`) is at most `CALENDAR_MATCH_TOLERANCE_S`.
    6. Return the configured theme when at least one candidate survives,
       choosing the candidate with the smallest absolute time difference.
       An exact tie breaks deterministically — by the earlier reference
       time, then by the entry's own field ordering — so the result never
       depends on iteration order. A single winner matters even though
       every candidate yields the same theme id today: it keeps this
       function honest about the physical fact that a flight is one
       aircraft, and it is what a future per-entry theme would need.
       `CALENDAR_MATCH_TOLERANCE_S` (90 minutes) is this phase's
       resolution of a Claude's-Discretion point: generous enough to
       absorb an ordinary delay, and far tighter than the roughly eight
       hours separating the measured twice-daily same-route rotations
       (16-CONTEXT.md finding 2), so a same-route collision is never
       ambiguously close.

    The whole body is guarded so a malformed registry, route, config or
    clock returns `None` rather than raising — this function runs inside
    the poll cycle and must never become a new way for a render to fail.
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
        # Defence in depth only - every branch above is already guarded,
        # but this function runs inside the poll cycle and must never
        # become a new way for a render to fail.
        return None
