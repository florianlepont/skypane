#!/usr/bin/env python3
"""Phase 16's calendar-sourced theme input: the operator's connected iCal
feed, parsed into a bounded list of match candidates.

Across this phase this module owns four things: the throttled, hardened
fetch of an operator-supplied iCal URL (plan 16-04), the hand-rolled RFC
5545 subset parser below (this plan, 16-01), a rolling-window registry
persisted at `{state_dir}/calendar_rules.json` (plan 16-03), and a pure
match function comparing a detected, enriched flight against that registry
(plan 16-06). This plan lands only the parser half: `unfold_ics_lines()`,
`split_property()`, `parse_ics_datetime()` and `parse_ics_events()`, plus
every constant and compiled allowlist the rest of the phase's plans share.

**Leaf-import contract (copied, adapted, from `server/plane/colour_rules.py`'s
own docstring):** this module imports stdlib only today (`re`, `sys`,
`datetime`/`timezone`); plan 16-03 adds `os`, `json` and `threading` for
the registry file contract, and plan 16-04 adds `requests` for the fetch.
It must NEVER import `server.plane.colour_rules`, `server.plane.enrich`,
`server.plane.detect`, `server.plane.illustrations`,
`server.plane.manual_resolutions`, or `server.plane.render`.

The `colour_rules` direction specifically is forbidden for a reason beyond
the general leaf-layering discipline every other name in that list already
carries: D-02's precedence between a calendar match and a manual rule is
wired the OTHER way round — `poll_loop.py` computes a `calendar_theme_id`
by calling this module's (future) match function, then passes that value
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
same way `colour_rules.json`/`manual_resolutions.json`/`device_config.json`
already do.

**Privacy clause:** this module's eventual persisted output describes a
named person's near-term work schedule (D-03's own framing) sitting on a
VPS. A persisted or in-memory record therefore carries the minimum the
matcher needs and nothing else — see `parse_ics_events()`'s five-key
entry shape below, which never carries a flight number, a UID, a summary
or a description. D-03's rolling window (plan 16-03) is what bounds how
long that minimum is retained; this plan's job is to make sure the minimum
itself is never exceeded even before a registry exists to expire it from.
"""
import re
import sys
from datetime import datetime, timezone

# --- Constants -------------------------------------------------------------

# The registry's on-disk filename, mirroring COLOUR_RULES_FILENAME /
# MANUAL_RESOLUTIONS_FILENAME's naming convention. Not read by any code
# until plan 16-03 adds the load/save functions.
CALENDAR_RULES_FILENAME = "calendar_rules.json"

# This phase's first runtime secret outside companion/auth.py. Its VALUE
# never leaves this module and never reaches a log line, a page, or
# state_dir (T-16-SECRET) — only its presence is ever surfaced elsewhere
# (companion/app.py's env_wake_interval_default()-style fail-open check).
CALENDAR_URL_ENV_VAR = "SKYPANE_CALENDAR_ICS_URL"

# Mirrors colour_rules.COLOUR_RULE_MAX_ENTRIES's role: a hard bound against
# a hostile/malformed feed, not a plausible one — a real 48h roster window
# measured well under ten events (16-CONTEXT.md finding 1).
CALENDAR_MAX_ENTRIES = 200

# Minimum seconds between fetch *attempts* (plan 16-04's throttle). A crew
# roster is republished at most a few times a day; 30 minutes tracks that
# cadence without hammering the operator's host every 30s poll cycle.
CALENDAR_FETCH_INTERVAL_S = 1800

# Per-request timeout (plan 16-04). Generous for a small iCal feed, short
# enough that a hung upstream never meaningfully delays the 30s oneshot.
CALENDAR_FETCH_TIMEOUT_S = 10.0

# Hard response-size cap enforced by streaming, never by trusting a
# Content-Length header (plan 16-04, T-16-DOS). 2 MiB comfortably exceeds
# any plausible multi-month roster export.
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

    Accumulation stops the instant `CALENDAR_MAX_ENTRIES` surviving
    entries have been collected; nothing past that point is parsed at
    all. Rejections are counted in two separate, mutually exclusive
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
                continue

            if name == "END":
                if value_upper == "VEVENT" and in_event and current is not None:
                    entry, reason = _build_entry(current)
                    if entry is not None:
                        entries.append(entry)
                    elif reason == "date_form":
                        rejected_date_form += 1
                    elif reason == "other":
                        rejected_other += 1
                in_event = False
                current = None
                if len(entries) >= CALENDAR_MAX_ENTRIES:
                    break
                continue

            if in_event and current is not None and name in _TRACKED_PROPERTIES:
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
