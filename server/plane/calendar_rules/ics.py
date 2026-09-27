"""RFC 5545 subset parser: turns an untrusted iCal feed body into a
bounded, validated list of match-candidate entries.

Leaf submodule: stdlib only, no `server` import, no import of this
package's own `registry` or sibling modules — kept a pure text-parsing
unit so `parse_ics_events()`'s allowlists (`_AIRLINE_IATA_RE`,
`_AIRPORT_IATA_RE`) can be shared by `registry` and `match` without
either importing the other.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone

# The one CATEGORIES value that marks a VEVENT as a flight rather than
# duty-roster noise.
CATEGORY_FLIGHT = "FLT"

# STATUS value carried by cancelled/placeholder junk events; filtered
# before their (deliberately invalid) dates are ever parsed.
STATUS_CANCELLED = "CANCELLED"

# Ceiling on how many raw candidates (VEVENT blocks here, raw registry
# entries in registry.py's _rebuild_capped_entries()) are examined before
# CALENDAR_MAX_ENTRIES is applied — and applied only to what survives the
# retention window, never to raw feed/file order. A cap applied in raw
# order before windowing can discard every future flight when a feed
# lists history first; this bound only guards against pathological feed
# size.
CALENDAR_MAX_RAW_EXAMINED = 5000

# --- Compiled positive allowlists -------------------------------------------
#
# Each allowlist validates one untrusted feed value before it can reach a
# parsed entry. Shared with registry.py (_normalise_calendar_entry) and
# match.py (matching a detected flight's airline/airport codes), so both
# import these rather than each keeping its own copy.

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


def unfold_ics_lines(raw_text: object) -> list[str]:
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


def split_property(line: object) -> tuple[str | None, str | None, str | None]:
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


def parse_ics_datetime(value: object) -> float | None:
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


def _build_entry(props: dict) -> tuple[dict | None, str | None]:
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


def parse_ics_events(raw_text: object) -> list[dict]:
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
