#!/usr/bin/env python3
"""Contract tests for server/plane/calendar_rules.py - phase 16's hand-rolled
RFC 5545 subset parser, its JSON registry, fetch hardening (SSRF/redirect/
size/secret-leak guards), refresh orchestration, calendar-theme matching and
the 0600 secret-file writer/accessor pair (phase 17).

The only fixture beyond an in-memory tempdir is the committed redacted
fixture server/fixtures/calendar_crewwebplus_redacted.ics - every calendar
feed fetch is exercised through an injected fake transport
(make_calendar_transport()), never a live network call.
"""
import io
import json
import os
import re
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FIXTURE_ICS = "calendar_crewwebplus_redacted.ics"

# Mirrors the fixture's own committed X-SKYPANE-FIXTURE-EXPECTED-ENTRIES
# property - test_fixture_ledger_agrees_with_harness_constant() below asserts
# the two agree, so the fixture and this file can never silently drift apart.
FIXTURE_EXPECTED_ENTRIES = 4

# A real public unicast IPv4 address (no DNS lookup needed - urlparse()
# already sees a literal IP as the hostname, and socket.getaddrinfo()
# resolves a dotted-decimal literal without ever touching the network).
# Only its RANGE classification matters to _address_is_public() here, not
# whether anything is actually listening on it - this is never actually
# connected to, since every test below injects its own fake transport.
PUBLIC_IP = "93.184.216.34"

import server.plane.calendar_rules as cr  # noqa: E402
import server.device_config as device_config  # noqa: E402


def load_fixture_text(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return fh.read()


def _entry(airline_iata, origin_iata, destination_iata, start_at, end_at):
    """Build one well-shaped CALENDAR_REGISTRY_KEYS entry for the registry,
    window and throttle tests below - the same five-key shape
    parse_ics_events() emits.
    """
    return {
        "airline_iata": airline_iata,
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
        "start_at": start_at,
        "end_at": end_at,
    }


def _mid_fixture_now():
    """A fixed `now` timestamp that places every one of the committed
    fixture's four valid events inside select_window_entries()'s window -
    today's UTC day-start through +48h. All four fixture events are on
    2026-09-01, the earliest starting at 05:00Z and the latest ending at
    15:25Z; 06:00Z that same day sits after the day-start edge and
    comfortably before the +48h forward edge for all of them.
    """
    from datetime import datetime, timezone
    return datetime(2026, 9, 1, 6, 0, 0, tzinfo=timezone.utc).timestamp()


class _FakeCalendarResponse:
    """A hermetic stand-in for `requests.Response`, built from fixed fields
    rather than a live call, in `server/test_enrich.py`'s `make_transport()`
    shape - so no test in this file ever makes a real network call.
    """

    def __init__(self, status_code=200, body=b"", headers=None, is_redirect=False):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.is_redirect = is_redirect
        self.closed = False

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        self.closed = True


def _write_calendar_secret(state_dir, url):
    """The single fixture path for "this test has a calendar configured",
    mirroring how the tests above already seed calendar_rules.json directly
    via write_calendar_registry() rather than going through a public write
    API for setup.

    Calls the real cr.save_calendar_url(state_dir, url) and asserts the
    return is True, so a fixture that silently fails to configure the
    calendar fails loudly here rather than producing a mystifying
    downstream failure several lines away.
    """
    assert cr.save_calendar_url(state_dir, url) is True, (
        "test fixture failure: save_calendar_url(%r, %r) returned False" % (state_dir, url))


def make_calendar_transport(status_code=200, body=b"", headers=None, is_redirect=False,
                             raise_exc=None, calls=None, timeouts=None):
    """Build a fake transport matching `fetch_ics()`'s injectable
    `transport(url, timeout)` contract - `test_enrich.make_transport()`'s
    exact shape, adapted for `_FakeCalendarResponse`. Records every URL
    (and, if `timeouts` is given, every timeout) it was invoked with, or
    raises `raise_exc` instead of returning, simulating a transport
    failure without ever touching a real socket.
    """
    def transport(url, timeout):
        if calls is not None:
            calls.append(url)
        if timeouts is not None:
            timeouts.append(timeout)
        if raise_exc is not None:
            raise raise_exc
        return _FakeCalendarResponse(status_code, body, headers, is_redirect)
    return transport


def _route(airline_name, origin_iata, destination_iata, callsign_iata):
    """A route dict in `enrich._parse_route()`'s exact six-key shape, for
    the matcher tests below.
    """
    return {
        "airline_name": airline_name,
        "origin_iata": origin_iata,
        "origin_city": None,
        "destination_iata": destination_iata,
        "destination_city": None,
        "callsign_iata": callsign_iata,
    }


fixture_text = load_fixture_text(FIXTURE_ICS)

CAL_THEME = device_config.THEME_IDS[-1]
CAL_CFG = {"theme": device_config.DEFAULT_THEME_ID, "calendar_theme_id": CAL_THEME}
MATCH_NOW = 1789000000.0

# Ambiguity fixture (16-VALIDATION matcher row 3): the committed fixture's
# own same-route pair (XX2001/XX2002, both BBB-ORY arrivals roughly 8.5h
# apart), parsed through parse_ics_events() - never a hand-built pair.
# Asserted at import time so a fixture edit that breaks this precondition
# fails loudly instead of silently changing what the four tests below
# exercise.
_fixture_entries = cr.parse_ics_events(fixture_text)
bbb_ory_entries = sorted(
    (e for e in _fixture_entries if e["origin_iata"] == "BBB" and e["destination_iata"] == "ORY"),
    key=lambda e: e["end_at"],
)
assert len(bbb_ory_entries) == 2, (
    "expected 2, found %d: %r" % (len(bbb_ory_entries), bbb_ory_entries))
near_entry, far_entry = bbb_ory_entries[0], bbb_ory_entries[1]
ambiguity_route = _route("Some Airline", "BBB", "ORY", "XX9999")


def test_unfold_space_continuation():
    """unfold_ics_lines() rejoins a SPACE continuation with the marker removed and nothing else lost"""
    raw = "SUMMARY:hello wo\n rld"
    result = cr.unfold_ics_lines(raw)
    if result != ["SUMMARY:hello world"]:
        pytest.fail("expected ['SUMMARY:hello world'], got %r" % (result,))


def test_unfold_htab_continuation():
    """unfold_ics_lines() rejoins a HTAB continuation with the marker removed and nothing else lost"""
    raw = "SUMMARY:hello wo\n\trld"
    result = cr.unfold_ics_lines(raw)
    if result != ["SUMMARY:hello world"]:
        pytest.fail("expected ['SUMMARY:hello world'], got %r" % (result,))


def test_unfold_three_physical_lines():
    """unfold_ics_lines() folds three physical lines (a continuation of a continuation) into one logical line"""
    raw = "SUMMARY:one\n two\n\tthree"
    result = cr.unfold_ics_lines(raw)
    if result != ["SUMMARY:onetwothree"]:
        pytest.fail("expected ['SUMMARY:onetwothree'], got %r" % (result,))


def test_unfold_long_summary_round_trips():
    """unfold_ics_lines() round-trips a synthetic SUMMARY over 75 octets folded across two physical lines to its exact original value"""
    original = "SUMMARY:" + "This is a deliberately long synthetic summary value exceeding the fold threshold."
    if len(original) <= 75:
        pytest.fail("test setup failure: original value is not over 75 octets")
    split_at = 60
    folded = original[:split_at] + "\n " + original[split_at:]
    result = cr.unfold_ics_lines(folded)
    if result != [original]:
        pytest.fail("expected exact round-trip %r, got %r" % (original, result))


def test_unfold_leading_continuation_does_not_raise():
    """unfold_ics_lines() on text whose very first line is a continuation does not raise and keeps that line as its own"""
    raw = " orphan continuation\nSUMMARY:XX"
    result = cr.unfold_ics_lines(raw)
    if result != [" orphan continuation", "SUMMARY:XX"]:
        pytest.fail("expected the orphan line kept as-is, got %r" % (result,))


def test_unfold_crlf_matches_lf():
    """unfold_ics_lines() unfolds the fixture's CRLF form to the identical list as its committed LF form"""
    crlf_text = fixture_text.replace("\n", "\r\n")
    if cr.unfold_ics_lines(fixture_text) != cr.unfold_ics_lines(crlf_text):
        pytest.fail("CRLF form unfolded to a different list than the LF form")


def test_unfold_non_string_input():
    """unfold_ics_lines() returns an empty list for non-string input (None, an int) without raising"""
    if cr.unfold_ics_lines(None) != []:
        pytest.fail("unfold_ics_lines(None) did not return []")
    if cr.unfold_ics_lines(42) != []:
        pytest.fail("unfold_ics_lines(42) did not return []")


def test_split_property_strips_parameters():
    """split_property() on a parameter-bearing line yields the bare uppercased name and a value with no parameter residue"""
    name, params, value = cr.split_property("DTSTART;VALUE=DATE-TIME:20260901T060000Z")
    if name != "DTSTART":
        pytest.fail("expected name 'DTSTART', got %r" % (name,))
    if value != "20260901T060000Z":
        pytest.fail("expected value '20260901T060000Z' with no parameter residue, got %r" % (value,))
    if params != "VALUE=DATE-TIME":
        pytest.fail("expected params 'VALUE=DATE-TIME', got %r" % (params,))


def test_split_property_value_with_colon():
    """split_property() partitions on the FIRST colon only, keeping a value's own embedded colon intact"""
    name, _params, value = cr.split_property("X-CUSTOM:http://example.invalid/a:b")
    if name != "X-CUSTOM":
        pytest.fail("expected name 'X-CUSTOM', got %r" % (name,))
    if value != "http://example.invalid/a:b":
        pytest.fail("expected the whole value with its own colon intact, got %r" % (value,))


def test_split_property_no_colon():
    """split_property() on a line with no colon at all returns (None, None, None) rather than raising"""
    name, params, value = cr.split_property("no-colon-here")
    if name is not None or params is not None or value is not None:
        pytest.fail("expected (None, None, None), got %r" % ((name, params, value),))


def test_fixture_ledger_agrees_with_harness_constant():
    """the fixture's own X-SKYPANE-FIXTURE-EXPECTED-ENTRIES property agrees with this harness's FIXTURE_EXPECTED_ENTRIES constant"""
    match = re.search(r"X-SKYPANE-FIXTURE-EXPECTED-ENTRIES:(\d+)", fixture_text)
    if match is None:
        pytest.fail("fixture is missing the X-SKYPANE-FIXTURE-EXPECTED-ENTRIES property")
    fixture_value = int(match.group(1))
    if fixture_value != FIXTURE_EXPECTED_ENTRIES:
        pytest.fail("fixture says %d, harness constant says %d" % (fixture_value, FIXTURE_EXPECTED_ENTRIES))


def test_fixture_parses_to_expected_count():
    """parse_ics_events() on the committed fixture returns exactly FIXTURE_EXPECTED_ENTRIES entries"""
    entries = cr.parse_ics_events(fixture_text)
    if len(entries) != FIXTURE_EXPECTED_ENTRIES:
        pytest.fail("expected %d entries, got %d: %r" % (FIXTURE_EXPECTED_ENTRIES, len(entries), entries))


def test_no_nineteenth_century_entries():
    """no entry parsed from the fixture carries a 19th-century timestamp - the two STATUS:CANCELLED placeholder events were dropped"""
    entries = cr.parse_ics_events(fixture_text)
    # Any real Unix epoch second for the year 1899 is a large negative
    # number; every surviving entry's start_at must be positive and
    # plausibly in this fixture's 2026 window.
    for entry in entries:
        if entry["start_at"] <= 0 or entry["end_at"] <= 0:
            pytest.fail("found an entry with a non-positive epoch timestamp (19th-century junk survived): %r" % (entry,))


def test_no_entries_from_non_flight_categories():
    """no entry derives from the OFFD, CAHC or CPBL blocks - every route matches one of the four flight events and the count is exactly four"""
    entries = cr.parse_ics_events(fixture_text)
    expected_routes = {("ORY", "AAA"), ("AAA", "ORY"), ("BBB", "ORY")}
    for entry in entries:
        route = (entry["origin_iata"], entry["destination_iata"])
        if route not in expected_routes:
            pytest.fail("entry with unexpected route %r - it may derive from an OFFD/CAHC/CPBL block: %r" % (route, entry))
    if len(entries) != 4:
        pytest.fail("expected exactly 4 entries, got %d" % (len(entries),))


def test_parse_ics_datetime_accepts_bare_utc():
    """parse_ics_datetime() returns a float epoch for the bare-UTC form"""
    result = cr.parse_ics_datetime("20260901T060000Z")
    if not isinstance(result, float):
        pytest.fail("expected a float, got %r" % (result,))


def test_parse_ics_datetime_rejection_sweep():
    """parse_ics_datetime() returns None for a VALUE=DATE value, a TZID-qualified value, a lowercase-z value, an empty string, a non-string, and a calendrically impossible value"""
    hostile_values = [
        "20260903",              # VALUE=DATE all-day value, no time component
        "20260901T180000",       # TZID-qualified local value, no trailing Z
        "20260901T060000z",      # lowercase trailing z
        "",                      # empty string
        None,                    # non-string
        42,                      # non-string
        "20261332T999999Z",      # syntactically shaped, calendrically impossible
    ]
    for value in hostile_values:
        result = cr.parse_ics_datetime(value)
        if result is not None:
            pytest.fail("parse_ics_datetime(%r) returned %r, expected None" % (value, result))


def test_tzid_tripwire_rejected_loudly_without_leaking_a_date():
    """the TZID tripwire is rejected loudly (a non-zero date-form rejection count on stderr) while the entry count stays four and no eight-digit date leaks"""
    buf = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = buf
    try:
        entries = cr.parse_ics_events(fixture_text)
    finally:
        sys.stderr = old_stderr
    captured = buf.getvalue()
    if len(entries) != FIXTURE_EXPECTED_ENTRIES:
        pytest.fail("expected %d entries even with the TZID tripwire rejected, got %d" % (FIXTURE_EXPECTED_ENTRIES, len(entries)))
    if not re.search(r"\brejected for an unrecognised date form\b", captured):
        pytest.fail("expected a date-form rejection line on stderr, got %r" % (captured,))
    date_form_match = re.search(r"(\d+) rejected for an unrecognised date form", captured)
    if date_form_match is None or int(date_form_match.group(1)) < 1:
        pytest.fail("expected a non-zero date-form rejection count, got %r" % (captured,))
    if re.search(r"\d{8}", captured):
        pytest.fail("stderr must never contain an eight-digit date string, got %r" % (captured,))


def test_parse_ics_events_never_raises():
    """parse_ics_events() never raises and returns an empty list for seven hostile bodies (empty, None, non-string, unterminated block, punctuation, no-colon lines, decoded random bytes)"""
    hostile_bodies = [
        "",
        None,
        42,
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:X\nCATEGORIES:FLT\n",  # never closed
        "!!!@#$%^&*()<<<>>>",
        "no colon anywhere\nsecond line also none\nthird line neither",
        bytes(range(256)).decode("utf-8", errors="replace"),
    ]
    for body in hostile_bodies:
        result = cr.parse_ics_events(body)
        if result != []:
            pytest.fail("parse_ics_events(%r) returned %r, expected []" % (body, result))


def test_bounded_output_at_max_raw_examined():
    """parse_ics_events() on a body with more VEVENT blocks than CALENDAR_MAX_RAW_EXAMINED returns exactly CALENDAR_MAX_RAW_EXAMINED entries"""
    one_event = (
        "BEGIN:VEVENT\n"
        "UID:cap-test-%d@skypane.invalid\n"
        "DTSTAMP:20260901T000000Z\n"
        "SUMMARY:XX1001 ORY-AAA(+0200)\n"
        "CATEGORIES:FLT\n"
        "DTSTART;VALUE=DATE-TIME:20260901T060000Z\n"
        "DTEND;VALUE=DATE-TIME:20260901T081500Z\n"
        "END:VEVENT\n"
    )
    repeat_count = cr.CALENDAR_MAX_RAW_EXAMINED + 200
    body = "BEGIN:VCALENDAR\nPRODID:-//test//test//EN\n" + "".join(
        one_event % i for i in range(repeat_count)
    ) + "END:VCALENDAR\n"
    entries = cr.parse_ics_events(body)
    if len(entries) != cr.CALENDAR_MAX_RAW_EXAMINED:
        pytest.fail("expected exactly %d entries, got %d" % (cr.CALENDAR_MAX_RAW_EXAMINED, len(entries)))


def test_feed_history_before_window_still_surfaces_window_entries():
    """UAT-02: a feed listing more than CALENDAR_MAX_ENTRIES historical VEVENTs before a small number of in-window ones still surfaces every in-window entry through parse_ics_events() + select_window_entries() - the exact real-world failure reproduced"""
    from datetime import datetime, timedelta, timezone

    def vevent(dtstart, dtend, flight):
        fmt = "%Y%m%dT%H%M%SZ"
        return (
            "BEGIN:VEVENT\n"
            "SUMMARY:%s CDG-ORY\n" % flight +
            "CATEGORIES:FLT\n"
            "DTSTART:%s\n" % dtstart.strftime(fmt) +
            "DTEND:%s\n" % dtend.strftime(fmt) +
            "END:VEVENT\n"
        )

    now = _mid_fixture_now()
    now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
    hist_base = datetime(2020, 1, 1, tzinfo=timezone.utc)

    lines = ["BEGIN:VCALENDAR\n"]
    history_count = cr.CALENDAR_MAX_ENTRIES + 50
    for i in range(history_count):
        d = hist_base + timedelta(days=i)
        lines.append(vevent(d, d + timedelta(hours=2), "AF%03d" % (i % 1000)))
    future_count = 8
    for i in range(future_count):
        d = now_dt + timedelta(hours=i * 2)
        lines.append(vevent(d, d + timedelta(hours=1), "BA%03d" % i))
    lines.append("END:VCALENDAR\n")
    body = "".join(lines)

    parsed = cr.parse_ics_events(body)
    windowed = cr.select_window_entries(parsed, now)
    future_survivors = [e for e in windowed if e["airline_iata"] == "BA"]
    if len(future_survivors) != future_count:
        pytest.fail((
            "expected all %d in-window future entries to survive a feed listing "
            "%d historical entries first, got %d survivors (windowed total %d)"
            % (future_count, history_count, len(future_survivors), len(windowed))
        ))


def test_record_shape_carries_no_schedule_text():
    """every returned entry has exactly the five expected keys, and the serialised list carries no flight number, UID, or description text"""
    import json
    entries = cr.parse_ics_events(fixture_text)
    expected_keys = {"airline_iata", "origin_iata", "destination_iata", "start_at", "end_at"}
    for entry in entries:
        if set(entry) != expected_keys:
            pytest.fail("expected exactly %r, got %r" % (expected_keys, set(entry)))
    blob = json.dumps(entries)
    forbidden_substrings = ["XX1001", "XX1002", "XX2001", "XX2002", "fixture-000", "DESCRIPTION", "Aircraft type"]
    for forbidden in forbidden_substrings:
        if forbidden in blob:
            pytest.fail("serialised entries leak schedule text %r: %r" % (forbidden, blob))


def test_d01_calendar_never_touches_colour_rules(tmp_path):
    """D-01: writing and re-writing the calendar registry never touches colour_rules.json's content or bytes, and the two registries are distinct files"""
    import hashlib
    import server.plane.colour_rules as colour_rules
    tmp = tmp_path
    colour_rules.add_rule(tmp, "prefix", "AFR", "white")
    before_registry = colour_rules.load_colour_rules(tmp)
    with open(colour_rules.colour_rules_path(tmp), "rb") as fh:
        before_hash = hashlib.sha256(fh.read()).hexdigest()

    # This check's subject is calendar/colour registry isolation, not
    # retention - an explicit `now` bracketing the sentinels keeps
    # the write path exercised the same way regardless of the wall
    # clock.
    now = 6.0
    entries_a = [_entry("XX", "AAA", "ORY", 1.0, 2.0)]
    entries_b = [
        _entry("XX", "BBB", "ORY", 3.0, 4.0),
        _entry("XX", "CCC", "ORY", 5.0, 6.0),
    ]
    cr.write_calendar_registry(tmp, entries_a, 10.0, None, now=now)
    cr.write_calendar_registry(tmp, entries_b, 20.0, "2026-09-07T00:00:00+00:00", now=now)

    after_registry = colour_rules.load_colour_rules(tmp)
    with open(colour_rules.colour_rules_path(tmp), "rb") as fh:
        after_hash = hashlib.sha256(fh.read()).hexdigest()

    if after_registry != before_registry:
        pytest.fail(("colour_rules.load_colour_rules() output changed after a "
                        "calendar registry write: an automatic source touched the "
                        "operator's hand-written rules"))
    if after_hash != before_hash:
        pytest.fail("colour_rules.json's bytes changed after a calendar registry write")
    if not os.path.exists(cr.calendar_rules_path(tmp)):
        pytest.fail("calendar_rules.json was not written")
    if cr.calendar_rules_path(tmp) == colour_rules.colour_rules_path(tmp):
        pytest.fail("calendar_rules.json and colour_rules.json resolved to the same path")


def test_d03_whole_file_rewrite_never_merges(tmp_path):
    """write_calendar_registry() replaces the whole file - a shorter second write leaves only that list, never a merge with the earlier one"""
    # This check's subject is whole-file replacement vs. merge, not
    # retention - a fixed `now` bracketing both sentinel entry lists
    # (epoch 1-6) keeps them in-window without touching the fixtures
    # themselves.
    now = 6.0
    tmp = tmp_path
    entries_a = [
        _entry("XX", "AAA", "ORY", 1.0, 2.0),
        _entry("XX", "BBB", "ORY", 3.0, 4.0),
    ]
    entries_b = [_entry("XX", "CCC", "ORY", 5.0, 6.0)]
    cr.write_calendar_registry(tmp, entries_a, 100.0, "2026-09-07T00:00:00+00:00", now=now)
    cr.write_calendar_registry(tmp, entries_b, 200.0, "2026-09-07T01:00:00+00:00", now=now)
    loaded = cr.load_calendar_registry(tmp, now)
    origins = sorted(e["origin_iata"] for e in loaded["entries"])
    if origins != ["CCC"]:
        pytest.fail(("expected only entries_b's entry to survive (no merge with "
                        "entries_a), got %r" % (origins,)))


def test_d03_empty_write_empties_the_window(tmp_path):
    """write_calendar_registry([]) empties the registry rather than leaving the previous entries behind, with both timestamps still readable"""
    # An explicit `now` bracketing the sentinel entry (epoch 1-2) so the
    # first write is genuinely in-window - otherwise the window would
    # already have emptied it before the empty-write step ever ran,
    # making this check's own assertion vacuous.
    now = 2.0
    tmp = tmp_path
    cr.write_calendar_registry(
        tmp, [_entry("XX", "AAA", "ORY", 1.0, 2.0)], 100.0, "2026-09-07T00:00:00+00:00",
        now=now)
    seeded = cr.load_calendar_registry(tmp, now)
    if seeded["entries"] == []:
        pytest.fail("test setup failure: the seeded entry should be in-window, got []")
    cr.write_calendar_registry(tmp, [], 200.0, "2026-09-07T01:00:00+00:00", now=now)
    loaded = cr.load_calendar_registry(tmp, now)
    if loaded["entries"] != []:
        pytest.fail("expected an empty entries list after an empty write, got %r" % (loaded["entries"],))
    if loaded["last_attempt_at"] != 200.0 or loaded["last_synced_at"] != "2026-09-07T01:00:00+00:00":
        pytest.fail("timestamps did not survive an empty write: %r" % (loaded,))


def test_rolling_window_keeps_and_drops_the_expected_entries():
    """select_window_entries() keeps an already-landed-earlier-today entry, a later-today entry and a 47h-ahead entry, drops one ended yesterday and one 49h ahead, sorted ascending, without mutating its input"""
    import copy
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()

    def offset_entry(start_offset_h, duration_h=2):
        start = now + start_offset_h * 3600
        return _entry("XX", "AAA", "ORY", start, start + duration_h * 3600)

    ended_yesterday = offset_entry(-30)
    landed_earlier_today = offset_entry(-8)
    later_today = offset_entry(2)
    forty_seven_ahead = offset_entry(47)
    forty_nine_ahead = offset_entry(49)
    source = [ended_yesterday, landed_earlier_today, later_today, forty_seven_ahead, forty_nine_ahead]
    frozen = copy.deepcopy(source)

    kept = cr.select_window_entries(source, now)

    if source != frozen:
        pytest.fail("select_window_entries() mutated its input list")
    kept_starts = [e["start_at"] for e in kept]
    expected_starts = sorted(
        e["start_at"] for e in (landed_earlier_today, later_today, forty_seven_ahead))
    if sorted(kept_starts) != expected_starts:
        pytest.fail(("expected exactly the earlier-today, later-today and 47h-ahead "
                        "entries, got start_at values %r" % (kept_starts,)))
    if kept_starts != sorted(kept_starts):
        pytest.fail("select_window_entries() did not return entries sorted ascending by start_at")


def test_rolling_window_excludes_nineteenth_century_junk():
    """select_window_entries() excludes an entry carrying a 19th-century timestamp for a present-day now"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    junk_start = datetime(1899, 12, 30, tzinfo=timezone.utc).timestamp()
    junk_entry = _entry("XX", "AAA", "ORY", junk_start, junk_start + 3600)
    kept = cr.select_window_entries([junk_entry], now)
    if kept != []:
        pytest.fail("expected the 19th-century entry to be excluded, got %r" % (kept,))


def test_load_caps_at_max_entries_with_a_warning(tmp_path):
    """load_calendar_registry() on a file holding more than CALENDAR_MAX_ENTRIES well-formed entries returns exactly CALENDAR_MAX_ENTRIES of them and prints a drop-count warning on stderr"""
    import json
    # An explicit `now` bracketing the whole 0..CALENDAR_MAX_ENTRIES+49
    # sentinel range so every one of these entries is in-window
    # regardless of order - this check's subject is the cap, not the
    # reorder.
    now = float(cr.CALENDAR_MAX_ENTRIES + 49)
    tmp = tmp_path
    oversized = [
        _entry("XX", "AAA", "ORY", float(i), float(i) + 1)
        for i in range(cr.CALENDAR_MAX_ENTRIES + 50)
    ]
    with open(cr.calendar_rules_path(tmp), "w") as fh:
        json.dump({"entries": oversized, "last_attempt_at": None, "last_synced_at": None}, fh)
    buf = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = buf
    try:
        loaded = cr.load_calendar_registry(tmp, now)
    finally:
        sys.stderr = old_stderr
    if len(loaded["entries"]) != cr.CALENDAR_MAX_ENTRIES:
        pytest.fail("expected exactly CALENDAR_MAX_ENTRIES entries, got %d" % (len(loaded["entries"]),))
    if "dropped" not in buf.getvalue():
        pytest.fail("expected a drop-count warning on stderr, got %r" % (buf.getvalue(),))


def test_registry_history_before_window_still_surfaces_window_entries(tmp_path):
    """UAT-02: load_calendar_registry() on a raw entries list holding more than CALENDAR_MAX_ENTRIES out-of-window entries before a small number of in-window ones still surfaces every in-window entry - the exact real-world failure reproduced at the registry layer"""
    import json
    now = _mid_fixture_now()
    history_count = cr.CALENDAR_MAX_ENTRIES + 50
    future_count = 8
    raw_entries = (
        [_entry("XX", "AAA", "ORY", float(i), float(i) + 1) for i in range(history_count)]
        + [_entry("BA", "CDG", "ORY", now + i * 60, now + i * 60 + 60) for i in range(future_count)]
    )
    tmp = tmp_path
    with open(cr.calendar_rules_path(tmp), "w") as fh:
        json.dump({"entries": raw_entries, "last_attempt_at": None, "last_synced_at": None}, fh)
    loaded = cr.load_calendar_registry(tmp, now)
    future_survivors = [e for e in loaded["entries"] if e["airline_iata"] == "BA"]
    if len(future_survivors) != future_count:
        pytest.fail((
            "expected all %d in-window entries to survive a raw list holding %d "
            "out-of-window entries first, got %d survivors (total %d)"
            % (future_count, history_count, len(future_survivors), len(loaded["entries"]))
        ))


def test_resolve_retention_now_never_erases_a_populated_registry(tmp_path):
    """UF-16-05 closure: _resolve_retention_now() resolves None, a bool, a non-numeric value, NaN/+-Infinity, and a finite-but-absurd value (1e300) all to a real convertible clock, so none of them can erase a populated registry through load_calendar_registry()"""
    import time
    # The genuine wall clock, not the fixture's fixed 2026-09-01 `now` -
    # every bad value below is expected to resolve to time.time(), so
    # the seeded entry must actually be in-window relative to REAL
    # current time for that resolution to be provably correct.
    real_now = time.time()
    seeded = [_entry("BA", "CDG", "ORY", real_now, real_now + 60)]
    bad_values = (None, True, False, "not-a-number", float("nan"),
                  float("inf"), float("-inf"), 1e300, -1e300)
    tmp = tmp_path
    if not cr.write_calendar_registry(tmp, seeded, real_now, None, now=real_now):
        pytest.fail("test fixture failure: write_calendar_registry() returned False")
    for bad in bad_values:
        loaded = cr.load_calendar_registry(tmp, bad)
        if len(loaded["entries"]) != 1:
            pytest.fail((
                "_resolve_retention_now(%r) let an absurd now erase a populated "
                "registry - expected 1 surviving entry, got %d"
                % (bad, len(loaded["entries"]))
            ))


def test_load_drops_every_hostile_entry_shape(tmp_path):
    """load_calendar_registry() drops every one of eight hostile entry shapes (non-dict, short, over-long, lowercase airport, 3-char airline, string timestamp, boolean timestamp, inverted time pair) and raises nothing"""
    import json
    hostile_entries = [
        "not-a-dict",
        {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY"},
        {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": 1.0, "end_at": 2.0, "extra": "x"},
        {"airline_iata": "XX", "origin_iata": "aaa", "destination_iata": "ORY",
         "start_at": 1.0, "end_at": 2.0},
        {"airline_iata": "XXX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": 1.0, "end_at": 2.0},
        {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": "1.0", "end_at": 2.0},
        {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": True, "end_at": 2.0},
        {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": 5.0, "end_at": 1.0},
    ]
    tmp = tmp_path
    with open(cr.calendar_rules_path(tmp), "w") as fh:
        json.dump({"entries": hostile_entries, "last_attempt_at": None, "last_synced_at": None}, fh)
    loaded = cr.load_calendar_registry(tmp)
    if loaded["entries"] != []:
        pytest.fail("expected zero survivors from eight hostile entry shapes, got %r" % (loaded["entries"],))


def test_load_degrades_to_empty_shape_for_hostile_files(tmp_path):
    """load_calendar_registry() degrades non-JSON bytes, a JSON array, a JSON string, and a dict whose entries is an integer all to the documented empty shape"""
    import json
    empty_shape = {"entries": [], "last_attempt_at": None, "last_synced_at": None}
    hostile_bodies = [
        "not json at all",
        json.dumps([1, 2, 3]),
        json.dumps("just a string"),
        json.dumps({"entries": 5}),
    ]
    tmp = tmp_path
    path = cr.calendar_rules_path(tmp)
    for body in hostile_bodies:
        with open(path, "w") as fh:
            fh.write(body)
        loaded = cr.load_calendar_registry(tmp)
        if loaded != empty_shape:
            pytest.fail("load_calendar_registry() on %r returned %r, expected the empty shape" % (body, loaded))


def test_throttle_exact_verdicts():
    """calendar_fetch_is_due() returns the exact expected verdict for never-fetched, just-fetched, one-second-before/-after the interval, a future timestamp, a string, and a boolean - a broken feed must never be contacted on every 30-second cycle"""
    now = 1000000.0
    cases = [
        (None, True, "never fetched"),
        (now, False, "just fetched"),
        (now - (cr.CALENDAR_FETCH_INTERVAL_S - 1), False, "one second before the interval elapses"),
        (now - (cr.CALENDAR_FETCH_INTERVAL_S + 1), True, "one second after the interval elapses"),
        (now + 500, True, "a future last_attempt_at (clock stepped backwards)"),
        ("not-a-number", True, "a string last_attempt_at"),
        (True, True, "a boolean last_attempt_at"),
    ]
    for last_attempt_at, expected, label in cases:
        actual = cr.calendar_fetch_is_due(last_attempt_at, now)
        if actual is not expected:
            pytest.fail(("calendar_fetch_is_due(%r, now) for case %r returned %r, "
                            "expected %r - a broken feed would be contacted on every "
                            "30-second cycle" % (last_attempt_at, label, actual, expected)))


def test_two_timestamps_are_distinct_in_type_and_role(tmp_path):
    """the two persisted timestamps survive a round trip with distinct types (a number and an ISO string), and calendar_fetch_is_due() consults only last_attempt_at - changing last_synced_at alone never changes its verdict, changing last_attempt_at does"""
    tmp = tmp_path
    cr.write_calendar_registry(tmp, [], 500.0, "2020-01-01T00:00:00+00:00")
    loaded = cr.load_calendar_registry(tmp)
    if not isinstance(loaded["last_attempt_at"], float):
        pytest.fail("last_attempt_at did not survive the round trip as a float: %r" % (loaded,))
    if not isinstance(loaded["last_synced_at"], str):
        pytest.fail("last_synced_at did not survive the round trip as a str: %r" % (loaded,))

    now = 100000.0
    due_before = cr.calendar_fetch_is_due(loaded["last_attempt_at"], now)

    # Change ONLY last_synced_at - the throttle's verdict must not move.
    cr.write_calendar_registry(tmp, [], loaded["last_attempt_at"], "2026-09-07T00:00:00+00:00")
    after_sync_change = cr.load_calendar_registry(tmp)
    due_after_sync_change = cr.calendar_fetch_is_due(after_sync_change["last_attempt_at"], now)
    if due_after_sync_change != due_before:
        pytest.fail("calendar_fetch_is_due()'s verdict changed when only last_synced_at changed")

    # Change ONLY last_attempt_at (to `now` itself) - the verdict MUST move.
    cr.write_calendar_registry(tmp, [], now, "2026-09-07T00:00:00+00:00")
    after_attempt_change = cr.load_calendar_registry(tmp)
    due_after_attempt_change = cr.calendar_fetch_is_due(after_attempt_change["last_attempt_at"], now)
    if due_after_attempt_change is not False:
        pytest.fail("expected calendar_fetch_is_due() to report not-due immediately after last_attempt_at was set to now")
    if due_before is not True:
        pytest.fail("test setup failure: due_before should have been True (elapsed far exceeds the interval)")


def test_secret_never_reaches_the_file_or_the_log(tmp_path):
    """a distinctive token set in the calendar secret file appears in neither calendar_rules.json's bytes, the loaded dict's serialisation, nor anything printed to stderr during a round trip"""
    import json
    token = "SEKRIT-TOKEN-CONTAINMENT-CHECK"
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://example.invalid/feed.ics?token=%s" % token)
    # This check's subject is secret containment, not retention -
    # an explicit `now` bracketing the sentinel range keeps the
    # persist/load round trip exercised the same way regardless
    # of the wall clock.
    now = float(cr.CALENDAR_MAX_ENTRIES + 4)
    oversized = [
        _entry("XX", "AAA", "ORY", float(i), float(i) + 1)
        for i in range(cr.CALENDAR_MAX_ENTRIES + 5)
    ]
    buf = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = buf
    try:
        cr.write_calendar_registry(tmp, oversized, 1.0, "2026-09-07T00:00:00+00:00", now=now)
        loaded = cr.load_calendar_registry(tmp, now)
    finally:
        sys.stderr = old_stderr
    captured_stderr = buf.getvalue()
    with open(cr.calendar_rules_path(tmp)) as fh:
        file_bytes = fh.read()
    serialised = json.dumps(loaded)
    if token in file_bytes:
        pytest.fail("the calendar URL token leaked into calendar_rules.json")
    if token in serialised:
        pytest.fail("the calendar URL token leaked into the loaded dict's serialisation")
    if token in captured_stderr:
        pytest.fail("the calendar URL token leaked into stderr")


def test_scheme_gate_refuses_non_https():
    """_url_is_safe() refuses a non-https scheme (http, ftp, file, and a schemeless string)"""
    for bad in ("http://%s/a.ics" % PUBLIC_IP, "ftp://%s/a.ics" % PUBLIC_IP,
                "file:///etc/passwd", "not-a-url"):
        if cr._url_is_safe(bad) is not False:
            pytest.fail("expected _url_is_safe(%r) to be False" % (bad,))


def test_no_hostname_refused():
    """_url_is_safe() refuses a URL with no hostname"""
    if cr._url_is_safe("https:///a.ics") is not False:
        pytest.fail("expected a hostless https URL to be refused")


def test_address_gate_refuses_every_unsafe_range():
    """_url_is_safe() refuses loopback (v4/v6), three private ranges, the link-local metadata address, and a reserved address"""
    unsafe = (
        "https://127.0.0.1/a.ics",        # loopback v4
        "https://[::1]/a.ics",             # loopback v6
        "https://10.0.0.5/a.ics",          # private (RFC 1918)
        "https://172.16.0.1/a.ics",        # private (RFC 1918)
        "https://192.168.1.1/a.ics",       # private (RFC 1918)
        "https://169.254.169.254/a.ics",   # link-local (cloud metadata)
        "https://240.0.0.1/a.ics",         # reserved (Class E)
    )
    for url in unsafe:
        if cr._url_is_safe(url) is not False:
            pytest.fail("expected _url_is_safe(%r) to be False" % (url,))


def test_unresolvable_hostname_refused(monkeypatch):
    """_url_is_safe() refuses a hostname that fails to resolve at all"""
    # ".invalid" is reserved by RFC 2606 to always fail to resolve, but the
    # non-loopback DNS guard (conftest.py) now blocks the lookup before the
    # real resolver would ever get to report that failure itself - stub the
    # lookup to raise the exact exception a genuine resolution failure would
    # (socket.gaierror), which is what _url_is_safe() itself catches,
    # rather than bypassing the guard.
    def fake_getaddrinfo(host, *a, **k):
        raise socket.gaierror("simulated resolution failure for %r" % (host,))

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    if cr._url_is_safe("https://this-genuinely-does-not-resolve.invalid/a.ics") is not False:
        pytest.fail("expected an unresolvable hostname to be refused")


def test_mixed_address_answer_refused(monkeypatch):
    """_url_is_safe() refuses a hostname whose resolved addresses are a MIX of public and private - the DNS-rebinding case a hostname-only check would miss"""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: [
        (2, 1, 6, "", (PUBLIC_IP, 443)),
        (2, 1, 6, "", ("10.1.2.3", 443)),
    ])
    if cr._url_is_safe("https://public-looking-name.example/a.ics") is not False:
        pytest.fail("a hostname resolving to one private address among public ones must be refused")


def test_all_public_answer_accepted(monkeypatch):
    """_url_is_safe() accepts the same hostname when every resolved address is public"""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: [
        (2, 1, 6, "", (PUBLIC_IP, 443)),
    ])
    if cr._url_is_safe("https://public-looking-name.example/a.ics") is not True:
        pytest.fail("a hostname resolving to only public addresses should be accepted")


def test_redirect_to_loopback_refused():
    """fetch_ics() refuses a redirect whose Location targets a loopback address, without ever fetching it"""
    calls = []
    transport = make_calendar_transport(
        status_code=302, headers={"Location": "https://127.0.0.1/a.ics"},
        is_redirect=True, calls=calls)
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None when a redirect targets a loopback address")
    if calls != ["https://%s/a.ics" % PUBLIC_IP]:
        pytest.fail("expected exactly one transport call (the redirect target must never be fetched): %r" % (calls,))


def test_redirect_without_location_returns_none():
    """fetch_ics() returns nothing for a redirect response with no Location header"""
    transport = make_calendar_transport(status_code=302, headers={}, is_redirect=True)
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None for a redirect with no Location header")


def test_relative_redirect_resolved_and_refetched():
    """fetch_ics() resolves a relative Location against the current URL and re-validates it before following it"""
    calls = []
    responses = [
        _FakeCalendarResponse(302, headers={"Location": "/moved.ics"}, is_redirect=True),
        _FakeCalendarResponse(200, body=b"BEGIN:VCALENDAR"),
    ]

    def transport(url, timeout):
        calls.append(url)
        return responses[len(calls) - 1]

    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result != "BEGIN:VCALENDAR":
        pytest.fail("expected the relative redirect to be followed to its resolved target, got %r" % (result,))
    if calls != ["https://%s/a.ics" % PUBLIC_IP, "https://%s/moved.ics" % PUBLIC_IP]:
        pytest.fail("expected the relative Location resolved against the current URL: %r" % (calls,))


def test_redirect_chain_bounded():
    """fetch_ics() gives up after CALENDAR_MAX_REDIRECTS + 1 transport calls rather than looping forever"""
    calls = []
    transport = make_calendar_transport(
        status_code=302, headers={"Location": "https://%s/next.ics" % PUBLIC_IP},
        is_redirect=True, calls=calls)
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None for a redirect chain longer than CALENDAR_MAX_REDIRECTS")
    if len(calls) != cr.CALENDAR_MAX_REDIRECTS + 1:
        pytest.fail("expected exactly CALENDAR_MAX_REDIRECTS + 1 transport calls, got %d" % (len(calls),))


def test_oversized_body_refused():
    """fetch_ics() refuses a body one byte over CALENDAR_MAX_RESPONSE_BYTES"""
    body = b"x" * (cr.CALENDAR_MAX_RESPONSE_BYTES + 1)
    transport = make_calendar_transport(status_code=200, body=body)
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None for a body one byte over the cap")


def test_oversized_body_with_lying_content_length_refused():
    """fetch_ics() refuses an oversized body even when it declares a Content-Length of 1 - the cap is on streamed bytes, never the declared length"""
    body = b"x" * (cr.CALENDAR_MAX_RESPONSE_BYTES + 1)
    transport = make_calendar_transport(status_code=200, body=body, headers={"Content-Length": "1"})
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None even though the declared Content-Length was only 1 byte")


def test_body_exactly_at_cap_accepted():
    """fetch_ics() accepts a body exactly at CALENDAR_MAX_RESPONSE_BYTES"""
    body = b"x" * cr.CALENDAR_MAX_RESPONSE_BYTES
    transport = make_calendar_transport(status_code=200, body=body)
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result != body.decode("utf-8"):
        pytest.fail("expected a body exactly at CALENDAR_MAX_RESPONSE_BYTES to be accepted")


def test_non_200_status_refused():
    """fetch_ics() returns nothing for a non-200 final status"""
    transport = make_calendar_transport(status_code=500, body=b"error")
    result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None for a non-200 final status")


def test_default_timeout_passed_to_transport():
    """fetch_ics() invokes the transport with CALENDAR_FETCH_TIMEOUT_S as the timeout argument by default"""
    timeouts = []
    transport = make_calendar_transport(status_code=200, body=b"ok", timeouts=timeouts)
    cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
    if timeouts != [cr.CALENDAR_FETCH_TIMEOUT_S]:
        pytest.fail("expected the transport's timeout argument to be CALENDAR_FETCH_TIMEOUT_S, got %r" % (timeouts,))


def test_secret_never_reaches_stderr_across_seven_failure_paths(monkeypatch):
    """across seven distinct fetch_ics() failure paths - including a transport exception whose message is the full secret URL - neither the token, the host, the path, nor the query-parameter name reaches stderr"""
    import requests
    real_getaddrinfo = socket.getaddrinfo
    token = "SEKRIT-FETCH-CONTAINMENT"
    host = "calendar-secret-fetch-test.invalid"
    secret_url = "https://%s/private-roster.ics?token=%s" % (host, token)
    forbidden = (token, host, "private-roster.ics", "token=")

    def fake_getaddrinfo(hostname, port=None, *a, **k):
        if hostname == host:
            return [(2, 1, 6, "", (PUBLIC_IP, 443))]
        return real_getaddrinfo(hostname, port, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    scenarios = {
        "refused scheme": lambda: cr.fetch_ics(
            secret_url.replace("https://", "http://")),
        "refused address": lambda: cr.fetch_ics(
            secret_url.replace(host, "127.0.0.1")),
        "refused redirect target": lambda: cr.fetch_ics(
            secret_url, transport=make_calendar_transport(
                status_code=302, is_redirect=True,
                headers={"Location": "https://127.0.0.1/x"})),
        "hop-limit exhaustion": lambda: cr.fetch_ics(
            secret_url, transport=make_calendar_transport(
                status_code=302, is_redirect=True,
                headers={"Location": secret_url})),
        "oversized body": lambda: cr.fetch_ics(
            secret_url, transport=make_calendar_transport(
                status_code=200, body=b"x" * (cr.CALENDAR_MAX_RESPONSE_BYTES + 1))),
        "non-200 status": lambda: cr.fetch_ics(
            secret_url, transport=make_calendar_transport(status_code=404)),
        "transport exception carrying the full URL": lambda: cr.fetch_ics(
            secret_url, transport=make_calendar_transport(
                raise_exc=requests.RequestException(secret_url))),
    }
    for label, run in scenarios.items():
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)
        result = run()
        if result is not None:
            pytest.fail("scenario %r unexpectedly succeeded: %r" % (label, result))
        captured = buf.getvalue()
        for leak in forbidden:
            if leak in captured:
                pytest.fail("scenario %r leaked %r into stderr: %r" % (label, leak, captured))


def test_secret_absent_from_persisted_registry_after_success(monkeypatch, tmp_path):
    """neither the calendar URL's token, host, path, nor query-parameter name appears in calendar_rules.json after a full successful refresh_calendar_registry() cycle"""
    real_getaddrinfo = socket.getaddrinfo
    token = "SEKRIT-REGISTRY-CONTAINMENT"
    host = "calendar-secret-registry-test.invalid"
    secret_url = "https://%s/private-roster.ics?token=%s" % (host, token)
    forbidden = (token, host, "private-roster.ics", "token=")

    def fake_getaddrinfo(hostname, port=None, *a, **k):
        if hostname == host:
            return [(2, 1, 6, "", (PUBLIC_IP, 443))]
        return real_getaddrinfo(hostname, port, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    now = _mid_fixture_now()
    tmp = tmp_path
    _write_calendar_secret(tmp, secret_url)
    transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
    code, _reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
    if code != cr.FETCH_OK:
        pytest.fail("test setup failure: expected FETCH_OK, got %r" % (code,))
    with open(cr.calendar_rules_path(tmp)) as fh:
        file_bytes = fh.read()
    for leak in forbidden:
        if leak in file_bytes:
            pytest.fail("the persisted registry leaked %r" % (leak,))


def test_refresh_unconfigured_makes_no_call_and_writes_nothing(tmp_path):
    """refresh_calendar_registry() makes no transport call and writes no last_attempt_at when the feature is unconfigured"""
    # No secret file is written - a fresh temporary state dir is
    # "unconfigured" by construction, with nothing to arrange or
    # restore (D-03).
    calls = []
    transport = make_calendar_transport(status_code=200, body=b"unused", calls=calls)
    tmp = tmp_path
    code, reg = cr.refresh_calendar_registry(tmp, 1000.0, transport=transport)
    if code != cr.FETCH_SKIPPED_UNCONFIGURED:
        pytest.fail("expected FETCH_SKIPPED_UNCONFIGURED, got %r" % (code,))
    if calls:
        pytest.fail("expected no transport call when unconfigured, got %r" % (calls,))
    if reg["last_attempt_at"] is not None:
        pytest.fail("expected last_attempt_at to stay None when unconfigured, got %r" % (reg,))


def test_refresh_throttled_path_is_silent(tmp_path):
    """refresh_calendar_registry() makes no transport call and prints nothing across twenty throttled cycles"""
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    first_transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR\nEND:VCALENDAR")
    cr.refresh_calendar_registry(tmp, 0.0, transport=first_transport)
    calls = []
    never_called = make_calendar_transport(status_code=200, body=b"unused", calls=calls)
    buf = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = buf
    try:
        for i in range(20):
            code, _reg = cr.refresh_calendar_registry(tmp, float(i), transport=never_called)
            if code != cr.FETCH_SKIPPED_THROTTLED:
                pytest.fail("expected FETCH_SKIPPED_THROTTLED at cycle %d, got %r" % (i, code))
    finally:
        sys.stderr = old_stderr
    if calls:
        pytest.fail("expected no transport call while throttled, got %r" % (calls,))
    if buf.getvalue() != "":
        pytest.fail("expected silent stderr on the throttled path, got %r" % (buf.getvalue(),))


def test_refresh_throttle_holds_across_eleven_cycles(tmp_path):
    """eleven refresh_calendar_registry() calls spaced 30 seconds apart perform exactly one transport call"""
    calls = []
    transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR\nEND:VCALENDAR", calls=calls)
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    for i in range(11):
        cr.refresh_calendar_registry(tmp, 30.0 * i, transport=transport)
    if len(calls) != 1:
        pytest.fail("expected exactly one transport call across eleven 30s-spaced cycles, got %d" % (len(calls),))


def test_refresh_failure_after_success_preserves_the_window(tmp_path):
    """a failed refresh_calendar_registry() after a success moves last_attempt_at, leaves last_synced_at, and leaves the persisted entries unchanged"""
    fixture_text = load_fixture_text(FIXTURE_ICS)
    now = _mid_fixture_now()
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    ok_transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
    code, reg = cr.refresh_calendar_registry(tmp, now, transport=ok_transport)
    if code != cr.FETCH_OK or not reg["entries"]:
        pytest.fail("test setup failure: expected a successful fetch with entries, got %r" % ((code, reg),))
    synced_at = reg["last_synced_at"]
    entries_before = list(reg["entries"])

    later = now + cr.CALENDAR_FETCH_INTERVAL_S + 1
    failing_transport = make_calendar_transport(status_code=500)
    code2, reg2 = cr.refresh_calendar_registry(tmp, later, transport=failing_transport)
    if code2 != cr.FETCH_FAILED:
        pytest.fail("expected FETCH_FAILED, got %r" % (code2,))
    if reg2["last_attempt_at"] != later:
        pytest.fail("expected last_attempt_at to move to %r, got %r" % (later, reg2))
    if reg2["last_synced_at"] != synced_at:
        pytest.fail("expected last_synced_at to stay at %r, got %r" % (synced_at, reg2["last_synced_at"]))
    # Load with the same `later` clock the failed refresh cycle
    # itself used, so this check's own read is not silently
    # re-windowed against the wall clock instead of the cycle
    # under test.
    on_disk = cr.load_calendar_registry(tmp, later)
    if on_disk["entries"] != entries_before:
        pytest.fail("a failed fetch changed the persisted entries")


def test_refresh_success_writes_the_fixtures_windowed_parse(tmp_path):
    """a successful refresh_calendar_registry() cycle writes a windowed parse of the committed fixture, matching what is then readable on disk"""
    fixture_text = load_fixture_text(FIXTURE_ICS)
    now = _mid_fixture_now()
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
    code, reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
    if code != cr.FETCH_OK:
        pytest.fail("expected FETCH_OK, got %r" % (code,))
    if len(reg["entries"]) != FIXTURE_EXPECTED_ENTRIES:
        pytest.fail("expected %d windowed entries from the fixture, got %d: %r" % (
            FIXTURE_EXPECTED_ENTRIES, len(reg["entries"]), reg["entries"]))
    # Load with the same `now` this refresh cycle used, so this
    # check's own read is not silently re-windowed against the
    # wall clock instead of the cycle under test.
    on_disk = cr.load_calendar_registry(tmp, now)
    if on_disk["entries"] != reg["entries"]:
        pytest.fail("the persisted entries did not match the returned registry")


def test_empty_window_success_distinguished_only_by_last_synced_at(tmp_path):
    """a successful fetch of a feed with nothing in the window reports FETCH_OK with an empty entry list, distinguished from a failure only by last_synced_at having moved"""
    empty_body = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
    transport = make_calendar_transport(status_code=200, body=empty_body.encode())
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    code, reg = cr.refresh_calendar_registry(tmp, 5000.0, transport=transport)
    if code != cr.FETCH_OK:
        pytest.fail("expected FETCH_OK even for a legitimately empty window, got %r" % (code,))
    if reg["entries"] != []:
        pytest.fail("expected an empty entries list, got %r" % (reg["entries"],))
    if reg["last_synced_at"] is None:
        pytest.fail("expected last_synced_at to have moved on a genuine success, got None")


def test_refresh_never_raises(tmp_path):
    """refresh_calendar_registry() never raises - an unwritable registry path, a punctuation body, a raising transport, and a redirect-looping transport all return a result code"""
    tmp = tmp_path
        # The URL now lives inside the same state_dir the registry
        # itself is written to (D-03), so a nonexistent/unwritable
        # state_dir no longer reaches the write path at all - the
        # secret file's own stat() fails first, and
        # configured_calendar_url() reports the feature as simply
        # unconfigured, never touching a transport. To exercise this
        # function's actual write-failure never-raises guarantee, the
        # state_dir itself must exist and be readable (so the secret
        # is genuinely configured) while the SPECIFIC registry write
        # deterministically fails regardless of who runs the test:
        # calendar_rules.json itself is made a directory, so
        # write_calendar_registry()'s open()/os.replace() hit a type
        # mismatch (IsADirectoryError) rather than a permission bit a
        # root-run test would simply ignore.
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    # save_calendar_url() above already created calendar_rules.json
    # as an ordinary (empty) file via its own registry-erase step -
    # remove it before replacing it with a directory of the same
    # name.
    os.remove(cr.calendar_rules_path(tmp))
    os.makedirs(cr.calendar_rules_path(tmp))

    code, _reg = cr.refresh_calendar_registry(
        tmp, 1.0, transport=make_calendar_transport(status_code=200, body=b"x"))
    if not isinstance(code, str):
        pytest.fail("expected a result code (string) for an unwritable registry path, got %r" % (code,))

    punctuation_transport = make_calendar_transport(status_code=200, body="!!!@#$%^&*()<<<>>>".encode())
    code2, _reg2 = cr.refresh_calendar_registry(tmp, 5000.0, transport=punctuation_transport)
    if not isinstance(code2, str):
        pytest.fail("expected a result code for a punctuation body, got %r" % (code2,))

    raising_transport = make_calendar_transport(raise_exc=Exception("simulated transport failure"))
    code3, _reg3 = cr.refresh_calendar_registry(tmp, 10000.0, transport=raising_transport)
    if not isinstance(code3, str):
        pytest.fail("expected a result code for a raising transport, got %r" % (code3,))

    looping_transport = make_calendar_transport(
        status_code=302, is_redirect=True, headers={"Location": "https://%s/next.ics" % PUBLIC_IP})
    code4, _reg4 = cr.refresh_calendar_registry(tmp, 15000.0, transport=looping_transport)
    if not isinstance(code4, str):
        pytest.fail("expected a result code for a redirect-looping transport, got %r" % (code4,))


def test_match_truth_table_departure():
    """match_calendar_theme() matches a departing detection whose route destination, airline and time all agree with an entry"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "XX1001")
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result != CAL_THEME:
        pytest.fail("expected a departure match to return %r, got %r" % (CAL_THEME, result))


def test_match_truth_table_arrival():
    """match_calendar_theme() matches an arriving detection whose route origin, airline and time all agree with an entry"""
    entries = [_entry("XX", "BBB", "ORY", MATCH_NOW - 7200, MATCH_NOW)]
    route = _route("Some Airline", "BBB", "ORY", "XX2001")
    result = cr.match_calendar_theme({"entries": entries}, route, cr.ARRIVING_STATE, CAL_CFG, MATCH_NOW)
    if result != CAL_THEME:
        pytest.fail("expected an arrival match to return %r, got %r" % (CAL_THEME, result))


def test_match_truth_table_different_far_end():
    """match_calendar_theme() does not match when only the far-end airport differs"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "ZZZ", "XX1001")
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("expected no match with a different far-end airport, got %r" % (result,))


def test_match_truth_table_different_airline():
    """match_calendar_theme() does not match when only the airline differs"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "YY1001")
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("expected no match with a different airline, got %r" % (result,))


def test_match_truth_table_time_outside_tolerance():
    """match_calendar_theme() does not match when the time is just outside CALENDAR_MATCH_TOLERANCE_S"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "XX1001")
    outside = MATCH_NOW + cr.CALENDAR_MATCH_TOLERANCE_S + 1
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, outside)
    if result is not None:
        pytest.fail("expected no match just outside the tolerance, got %r" % (result,))


def test_match_truth_table_time_inside_tolerance():
    """match_calendar_theme() matches when the time is just inside CALENDAR_MATCH_TOLERANCE_S"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "XX1001")
    inside = MATCH_NOW + cr.CALENDAR_MATCH_TOLERANCE_S - 1
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, inside)
    if result != CAL_THEME:
        pytest.fail("expected a match just inside the tolerance, got %r" % (result,))


def test_direction_symmetry_arrival_rejects_departure_side_far_end():
    """match_calendar_theme() direction symmetry: an arriving detection is never matched against an entry's departure-side far end"""
    entries = [_entry("XX", "CCC", "DDD", MATCH_NOW, MATCH_NOW + 7200)]
    # route's origin equals the entry's DESTINATION ("DDD") - the wrong
    # field for an arrival, whose correct far end is the entry's ORIGIN.
    route = _route("Some Airline", "DDD", "ZZZ", "XX1234")
    result = cr.match_calendar_theme(
        {"entries": entries}, route, cr.ARRIVING_STATE, CAL_CFG, MATCH_NOW + 7200)
    if result is not None:
        pytest.fail("expected no match: an arrival must compare against the entry's origin, not its destination, got %r" % (result,))


def test_direction_symmetry_departure_rejects_arrival_side_far_end():
    """match_calendar_theme() direction symmetry: a departing detection is never matched against an entry's arrival-side far end"""
    entries = [_entry("XX", "EEE", "FFF", MATCH_NOW, MATCH_NOW + 7200)]
    # route's destination equals the entry's ORIGIN ("EEE") - the wrong
    # field for a departure, whose correct far end is the entry's
    # DESTINATION.
    route = _route("Some Airline", "GGG", "EEE", "XX5678")
    result = cr.match_calendar_theme(
        {"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("expected no match: a departure must compare against the entry's destination, not its origin, got %r" % (result,))


def test_airline_derived_not_tabulated():
    """match_calendar_theme() derives the airline from callsign_iata at runtime - a designator no static table could contain still matches (CORRECTION 1)"""
    entries = [_entry("ZQ", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("An Unheard-Of Airline", "ORY", "AAA", "ZQ9999")
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result != CAL_THEME:
        pytest.fail("expected a match on a designator ('ZQ') no static table could contain, got %r - did someone reintroduce a static airline table?" % (result,))


def test_airline_only_shaped_route_never_matches():
    """match_calendar_theme() never matches an airline_only-shaped route (the production bug the field-presence test prevents)"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    airline_only_route = {
        "airline_name": "Some Airline", "origin_iata": None, "origin_city": None,
        "destination_iata": None, "destination_city": None, "callsign_iata": None,
    }
    result = cr.match_calendar_theme({"entries": entries}, airline_only_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("an airline_only-shaped route must never match, got %r" % (result,))


def test_manual_shaped_route_never_matches():
    """match_calendar_theme() never matches a manual-shaped route - the same shape as airline_only, a different provenance"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    manual_route = {
        "airline_name": "Some Airline (manually resolved)", "origin_iata": None,
        "origin_city": None, "destination_iata": None, "destination_city": None,
        "callsign_iata": None,
    }
    result = cr.match_calendar_theme({"entries": entries}, manual_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("a manual-shaped route must never match, got %r" % (result,))


def test_none_route_never_matches():
    """match_calendar_theme() never matches a None route (the miss case)"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    result = cr.match_calendar_theme({"entries": entries}, None, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
    if result is not None:
        pytest.fail("a None route (a miss) must never match, got %r" % (result,))


def test_ambiguity_near_first():
    """match_calendar_theme() matches a detection near the fixture's own first same-route (BBB-ORY) entry"""
    now = near_entry["end_at"] + 1000
    result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
    if result != CAL_THEME:
        pytest.fail("expected a match near the fixture's first same-route entry, got %r" % (result,))


def test_ambiguity_near_second():
    """match_calendar_theme() matches a detection near the fixture's own second same-route (BBB-ORY) entry"""
    now = far_entry["end_at"] - 1000
    result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
    if result != CAL_THEME:
        pytest.fail("expected a match near the fixture's second same-route entry, got %r" % (result,))


def test_ambiguity_midway_matches_neither():
    """match_calendar_theme() matches neither of the fixture's own same-route entries when the detection sits midway, outside both tolerances"""
    midpoint = (near_entry["end_at"] + far_entry["end_at"]) / 2.0
    if abs(midpoint - near_entry["end_at"]) <= cr.CALENDAR_MATCH_TOLERANCE_S or \
            abs(midpoint - far_entry["end_at"]) <= cr.CALENDAR_MATCH_TOLERANCE_S:
        pytest.fail("test setup failure: the fixture's pair is not far enough apart for a clean midpoint (gap=%r)" % (far_entry["end_at"] - near_entry["end_at"],))
    result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, midpoint)
    if result is not None:
        pytest.fail("expected no match midway between the fixture's pair, outside both tolerances, got %r" % (result,))


def test_ambiguity_deterministic_regardless_of_list_order():
    """match_calendar_theme() returns the identical result whether the fixture's same-route entries are listed forward or reversed (determinism, not iteration order)"""
    now = near_entry["end_at"] + 1000
    forward = cr.match_calendar_theme({"entries": [near_entry, far_entry]}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
    reversed_order = cr.match_calendar_theme({"entries": [far_entry, near_entry]}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
    if forward != reversed_order:
        pytest.fail("expected the same result regardless of entry list order, got %r vs %r" % (forward, reversed_order))
    if forward != CAL_THEME:
        pytest.fail("test setup failure: expected a match in the forward-order case, got %r" % (forward,))


def test_no_calendar_theme_id_saved_yields_no_match():
    """match_calendar_theme() returns no match when device_cfg carries no calendar_theme_id"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "XX1001")
    cfg = {"theme": device_config.DEFAULT_THEME_ID}
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, cfg, MATCH_NOW)
    if result is not None:
        pytest.fail("expected no match with no calendar_theme_id saved, got %r" % (result,))


def test_tampered_calendar_theme_id_never_returned():
    """match_calendar_theme() never returns a calendar_theme_id that is not a member of device_config.THEMES (T-16-TAMPER)"""
    entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    route = _route("Some Airline", "ORY", "AAA", "XX1001")
    cfg = {"theme": device_config.DEFAULT_THEME_ID, "calendar_theme_id": "not-a-real-theme"}
    result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, cfg, MATCH_NOW)
    if result is not None:
        pytest.fail("expected the unregistered calendar_theme_id to never be returned, got %r" % (result,))
    if "not-a-real-theme" in device_config.THEMES:
        pytest.fail("test setup invalid: 'not-a-real-theme' is somehow a real theme id")


def test_matcher_never_raises():
    """match_calendar_theme() never raises for a non-dict registry, non-list entries, malformed entries, a non-dict route, a non-dict device_cfg, a non-numeric now, or an unconfirmed render state"""
    good_route = _route("Some Airline", "ORY", "AAA", "XX1001")
    good_entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
    cases = [
        (None, good_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ([], good_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ({"entries": None}, good_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ({"entries": "not a list"}, good_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ({"entries": [None, {}, {"airline_iata": 1}]}, good_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ({"entries": good_entries}, "not a dict", cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW),
        ({"entries": good_entries}, good_route, cr.DEPARTING_STATE, "not a dict", MATCH_NOW),
        ({"entries": good_entries}, good_route, cr.DEPARTING_STATE, CAL_CFG, "not-a-time"),
        ({"entries": good_entries}, good_route, "boarding", CAL_CFG, MATCH_NOW),
    ]
    for registry, route, render_state, device_cfg, now in cases:
        result = cr.match_calendar_theme(registry, route, render_state, device_cfg, now)
        if result is not None:
            pytest.fail("case %r unexpectedly returned %r instead of None" % (
                (registry, route, render_state, device_cfg, now), result))


def test_nested_component_does_not_drop_the_event():
    """parse_ics_events() keeps a flight whose VEVENT contains a nested VALARM, and the nested component's properties never reach the parent entry (CR-01)"""
    ics = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "BEGIN:VEVENT",
        "UID:nested-1",
        "DTSTART;VALUE=DATE-TIME:20260904T091500Z",
        "DTEND;VALUE=DATE-TIME:20260904T104500Z",
        "STATUS:CONFIRMED", "CATEGORIES:FLT",
        "SUMMARY:ZQ7061 MPL-ORY(+0200)",
        "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT30M",
        "DESCRIPTION:alarm text that must not reach the parent event",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ])
    got = cr.parse_ics_events(ics)
    if len(got) != 1:
        pytest.fail("expected the flight to survive a nested VALARM, got %d entr(ies)" % (len(got),))
    entry = got[0]
    expected = {"airline_iata": "ZQ", "origin_iata": "MPL", "destination_iata": "ORY"}
    actual = {k: entry.get(k) for k in expected}
    if actual != expected:
        pytest.fail("expected %r, got %r" % (expected, actual))


def test_non_finite_timestamps_rejected():
    """_normalise_calendar_entry() rejects NaN/Infinity timestamps while still accepting a finite entry (CR-02)"""
    for literal in ("NaN", "Infinity", "-Infinity"):
        entry = json.loads(
            '{"airline_iata":"ZQ","origin_iata":"MPL","destination_iata":"ORY",'
            '"start_at":%s,"end_at":%s}' % (literal, literal))
        if cr._normalise_calendar_entry(entry) is not None:
            pytest.fail("%s timestamps were accepted" % (literal,))
    # a finite entry of the same shape must still be accepted, so the
    # check cannot pass by rejecting everything
    ok_entry = {"airline_iata": "ZQ", "origin_iata": "MPL",
                "destination_iata": "ORY", "start_at": 1.0, "end_at": 2.0}
    if cr._normalise_calendar_entry(ok_entry) is None:
        pytest.fail("a finite entry was rejected — the check would pass vacuously")


def test_failing_refresh_trims_the_raw_file_across_consecutive_cycles(tmp_path):
    """T-16-PRIV's own reproduction: an entry that ended ~10 days ago is absent from the RAW on-disk file after every one of three consecutive FAILING refresh_calendar_registry() cycles, and the returned registry matches the raw file on every cycle (D-04) - the verification the original goal check missed"""
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    # Seed the realistic way: a legitimate write at a seed_now
    # where the entry is genuinely in-window - this reproduces
    # the real production sequence (one successful fetch, then
    # a feed that breaks), not a hand-edited file.
    seed_now = 1_780_000_000.0
    stale = _entry("XX", "AAA", "ORY", seed_now, seed_now + 7200.0)
    if not cr.write_calendar_registry(
            tmp, [stale], seed_now, "2026-01-01T00:00:00+00:00", now=seed_now):
        pytest.fail("test setup failure: seed write failed")
    seeded_raw = json.load(open(cr.calendar_rules_path(tmp)))
    if len(seeded_raw["entries"]) != 1:
        pytest.fail(("test setup failure: the seeded entry should be in-window at "
                        "seed_now, got %r" % (seeded_raw["entries"],)))

    # 10 days later, the entry is stale. Drive three consecutive
    # FAILING refresh cycles, advancing `now` by more than
    # CALENDAR_FETCH_INTERVAL_S each time so the throttle
    # genuinely lets each attempt through.
    later = seed_now + 10 * 86400.0
    failing_transport = make_calendar_transport(status_code=500)
    for cycle in range(3):
        now = later + cycle * (cr.CALENDAR_FETCH_INTERVAL_S + 1.0)
        code, reg = cr.refresh_calendar_registry(tmp, now, transport=failing_transport)
        if code != cr.FETCH_FAILED:
            pytest.fail("cycle %d: expected FETCH_FAILED, got %r - a check that " \
                "silently took the throttled path would prove nothing" % (cycle, code))
        # Read the RAW file, never through load_calendar_registry() -
        # the loader now windows on read, so it would return a
        # trimmed list even from an untrimmed file, masking
        # exactly the on-disk state this check exists to observe.
        raw = json.load(open(cr.calendar_rules_path(tmp)))
        if raw["entries"] != []:
            pytest.fail("cycle %d: the stale entry survives on disk: %r" % (cycle, raw["entries"]))
        if reg["entries"] != raw["entries"]:
            pytest.fail("cycle %d: the returned registry != the on-disk entries (D-04)" % (cycle,))
        if raw["last_attempt_at"] != now:
            pytest.fail("cycle %d: last_attempt_at did not move" % (cycle,))
        if raw["last_synced_at"] != "2026-01-01T00:00:00+00:00":
            pytest.fail("cycle %d: a failing feed must not read as freshly synced" % (cycle,))


def test_loader_applies_the_window_on_read_without_rewriting(tmp_path):
    """a hand-written file mixing one out-of-window and one in-window entry loads to the in-window entry only, and the read does not rewrite the file (D-01/D-02)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    out_of_window = _entry("XX", "AAA", "ORY", now - 90000.0, now - 86400.0)  # ended yesterday
    in_window = _entry("XX", "BBB", "ORY", now + 3600.0, now + 7200.0)
    tmp = tmp_path
    path = cr.calendar_rules_path(tmp)
    os.makedirs(tmp, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({
            "entries": [out_of_window, in_window],
            "last_attempt_at": None, "last_synced_at": None,
        }, fh)
    with open(path, "rb") as fh:
        before_bytes = fh.read()
    loaded = cr.load_calendar_registry(tmp, now)
    with open(path, "rb") as fh:
        after_bytes = fh.read()
    if [e["origin_iata"] for e in loaded["entries"]] != ["BBB"]:
        pytest.fail("expected only the in-window entry, got %r" % (loaded["entries"],))
    if before_bytes != after_bytes:
        pytest.fail("load_calendar_registry() rewrote the file on a plain read")


def test_writer_refuses_to_persist_what_the_window_would_drop(tmp_path):
    """a write containing a stale entry and a current entry puts only the current entry in the raw file (D-01/D-03)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    stale = _entry("XX", "AAA", "ORY", now - 90000.0, now - 86400.0)
    current = _entry("XX", "BBB", "ORY", now + 3600.0, now + 7200.0)
    tmp = tmp_path
    if not cr.write_calendar_registry(
            tmp, [stale, current], 1.0, "2026-09-07T00:00:00+00:00", now=now):
        pytest.fail("test setup failure: write failed")
    raw = json.load(open(cr.calendar_rules_path(tmp)))
    if [e["origin_iata"] for e in raw["entries"]] != ["BBB"]:
        pytest.fail("expected only the current entry in the raw file, got %r" % (raw["entries"],))


def test_loader_output_is_exactly_select_window_entries(tmp_path):
    """for any list and any now, the loader's entries are exactly select_window_entries(list, now) - the anti-drift guard that goes red if a second window implementation ever appears (D-02)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    mixed = [
        _entry("XX", "AAA", "ORY", now - 200000.0, now - 190000.0),  # ended yesterday
        _entry("XX", "BBB", "ORY", now - 8 * 3600.0, now - 7 * 3600.0),  # landed earlier today
        _entry("XX", "CCC", "ORY", now + 2 * 3600.0, now + 3 * 3600.0),  # later today
        _entry("XX", "DDD", "ORY", now + 47 * 3600.0, now + 48 * 3600.0),  # 47h ahead
        _entry("XX", "EEE", "ORY", now + 49 * 3600.0, now + 50 * 3600.0),  # 49h ahead - out
    ]
    tmp = tmp_path
    path = cr.calendar_rules_path(tmp)
    os.makedirs(tmp, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"entries": mixed, "last_attempt_at": None, "last_synced_at": None}, fh)
    loaded = cr.load_calendar_registry(tmp, now)
    expected = cr.select_window_entries(mixed, now)
    if loaded["entries"] != expected:
        pytest.fail(("load_calendar_registry()'s entries diverged from "
                        "select_window_entries(list, now): got %r, expected %r"
                        % (loaded["entries"], expected)))


def test_tmp_file_mode_is_0600_at_creation_time(monkeypatch, tmp_path):
    """save_calendar_url() passes 0o600 as os.open()'s own mode argument when creating its temporary file - not merely a file that happens to read 0o600 later - and the mode still reads 0o600 at the moment of the atomic rename (T-17-MODE)"""
    import stat as stat_mod
    tmp = tmp_path
    secret_path = cr.calendar_secret_path(tmp)
    recorded = {}
    real_open = cr.os.open
    real_replace = cr.os.replace

    def _spy_open(path, flags, mode=0o777, *args, **kwargs):
        if path.startswith(secret_path):
            recorded["open_mode"] = mode
        return real_open(path, flags, mode, *args, **kwargs)

    def _spy_replace(src, dst):
        if dst == secret_path:
            try:
                recorded["replace_mode"] = stat_mod.S_IMODE(os.stat(src).st_mode)
            except OSError:
                recorded["replace_mode"] = None
        return real_replace(src, dst)

    monkeypatch.setattr(cr.os, "open", _spy_open)
    monkeypatch.setattr(cr.os, "replace", _spy_replace)
    ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
    if not ok:
        pytest.fail("test setup failure: save_calendar_url() returned False")
    if "open_mode" not in recorded:
        pytest.fail(
            "os.open() was never called to create the secret file's temporary file - the mode "
            "must be an argument to the creating call, not a plain builtin open()")
    if recorded["open_mode"] != 0o600:
        pytest.fail("os.open()'s own mode argument was %r, expected 0o600" % (recorded["open_mode"],))
    if recorded.get("replace_mode") != 0o600:
        pytest.fail(
            "temporary file's mode at rename time was %r, expected 0o600" % (recorded.get("replace_mode"),))


def test_writer_never_calls_chmod(monkeypatch, tmp_path):
    """save_calendar_url() never calls os.chmod() at all - the mode is set once, at file-creation time, never as a follow-up permission change (T-17-MODE)"""
    tmp = tmp_path
    calls = []
    real_chmod = cr.os.chmod

    def _spy_chmod(path, mode, *args, **kwargs):
        calls.append((path, mode))
        return real_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(cr.os, "chmod", _spy_chmod)
    ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
    if not ok:
        pytest.fail("test setup failure: save_calendar_url() returned False")
    if calls:
        pytest.fail("save_calendar_url() called os.chmod(%r) - the mode must never be a follow-up call" % (calls,))


def test_final_mode_is_0600_under_umask_022(tmp_path):
    """save_calendar_url() writes mode 0600 under a process umask of 022"""
    import stat as stat_mod
    tmp = tmp_path
    old_umask = os.umask(0o022)
    try:
        ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
    finally:
        os.umask(old_umask)
    if not ok:
        pytest.fail("test setup failure: save_calendar_url() returned False")
    mode = stat_mod.S_IMODE(os.stat(cr.calendar_secret_path(tmp)).st_mode)
    if mode != 0o600:
        pytest.fail("expected 0o600 under umask 022, got %o" % (mode,))


def test_final_mode_is_0600_under_umask_027(tmp_path):
    """save_calendar_url() writes mode 0600 under a process umask of 027"""
    import stat as stat_mod
    tmp = tmp_path
    old_umask = os.umask(0o027)
    try:
        ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
    finally:
        os.umask(old_umask)
    if not ok:
        pytest.fail("test setup failure: save_calendar_url() returned False")
    mode = stat_mod.S_IMODE(os.stat(cr.calendar_secret_path(tmp)).st_mode)
    if mode != 0o600:
        pytest.fail("expected 0o600 under umask 027, got %o" % (mode,))


def test_rename_does_not_inherit_destination_mode(tmp_path):
    """save_calendar_url() leaves the destination at 0600 even when the rename lands on a pre-existing group-readable file (T-17-MODE)"""
    import stat as stat_mod
    tmp = tmp_path
    path = cr.calendar_secret_path(tmp)
    old_umask = os.umask(0o022)
    try:
        with open(path, "w") as fh:
            fh.write("stale")
    finally:
        os.umask(old_umask)
    pre_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
    if pre_mode == 0o600:
        pytest.fail("test setup failure: destination already 0600 before the call")
    ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
    if not ok:
        pytest.fail("test setup failure: save_calendar_url() returned False")
    post_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
    if post_mode != 0o600:
        pytest.fail((
            "expected 0o600 after replacing a pre-existing group-readable file, got %o" % (post_mode,)))


def test_guard_flags_files_created_through_the_house_idiom(tmp_path):
    """calendar_secret_mode_is_unsafe() reports True for a file created through this codebase's ordinary umask-inheriting house idiom (0o644) and for 0o640/0o604/0o660, and False for 0o600/0o400 - the negative check proving the guard actually fires, not merely that the correct writer is correct (T-17-DRIFT)"""
    unsafe_modes = (0o644, 0o640, 0o604, 0o660)
    safe_modes = (0o600, 0o400)
    tmp = tmp_path
    path = cr.calendar_secret_path(tmp)
    for mode in unsafe_modes:
        with open(path, "w") as fh:
            fh.write("x")
        os.chmod(path, mode)
        if cr.calendar_secret_mode_is_unsafe(tmp) is not True:
            pytest.fail("mode 0o%o (the ordinary house idiom's 0o644 among them) was not flagged unsafe" % (mode,))
    for mode in safe_modes:
        os.chmod(path, mode)
        if cr.calendar_secret_mode_is_unsafe(tmp) is not False:
            pytest.fail("mode 0o%o was incorrectly flagged unsafe" % (mode,))
    os.remove(path)


def test_guard_is_false_and_a_genuine_bool_when_absent(tmp_path):
    """calendar_secret_mode_is_unsafe() is a genuine bool False (is False, not merely falsy, never None) on a state dir with no secret file"""
    tmp = tmp_path
    result = cr.calendar_secret_mode_is_unsafe(tmp)
    if result is not False:
        pytest.fail("expected a genuine False for an absent secret file, got %r" % (result,))


def test_clear_branch_removes_the_file_and_is_idempotent(tmp_path):
    """save_calendar_url(CLEAR_CALENDAR_URL) removes the secret file, returns True, and returns True again when called a second time with the file already gone"""
    import stat as stat_mod
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
        pytest.fail("test setup failure: initial write failed")
    path = cr.calendar_secret_path(tmp)
    if stat_mod.S_IMODE(os.stat(path).st_mode) != 0o600:
        pytest.fail("test setup failure: initial write was not 0o600")
    if cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL) is not True:
        pytest.fail("clear did not return True")
    if os.path.exists(path):
        pytest.fail("secret file still exists after clear")
    if cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL) is not True:
        pytest.fail("clearing an already-absent file did not return True")


def test_erase_on_set_or_replace_d05(tmp_path):
    """save_calendar_url() erases the fetched registry - zero entries and both timestamps None - on setting a URL for the first time or replacing one with a different URL (D-05)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
    tmp = tmp_path
    if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
        pytest.fail("test setup failure: seed write failed")
    if not cr.save_calendar_url(tmp, "https://example.invalid/new-feed.ics", now=now):
        pytest.fail("save_calendar_url() returned False")
    loaded = cr.load_calendar_registry(tmp, now)
    if loaded["entries"] != []:
        pytest.fail("expected zero entries after setting a URL, got %r" % (loaded["entries"],))
    if loaded["last_attempt_at"] is not None or loaded["last_synced_at"] is not None:
        pytest.fail((
            "expected both timestamps None after setting a URL, got %r/%r"
            % (loaded["last_attempt_at"], loaded["last_synced_at"])))


def test_erase_on_clear_d04(tmp_path):
    """save_calendar_url(CLEAR_CALENDAR_URL) erases the fetched registry and removes the secret file in the same call (D-04)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
    tmp = tmp_path
    if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
        pytest.fail("test setup failure: seed write failed")
    if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics", now=now):
        pytest.fail("test setup failure: initial save failed")
    if not cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL, now=now):
        pytest.fail("clear returned False")
    loaded = cr.load_calendar_registry(tmp, now)
    if loaded["entries"] != []:
        pytest.fail("expected zero entries after clearing, got %r" % (loaded["entries"],))
    if loaded["last_attempt_at"] is not None or loaded["last_synced_at"] is not None:
        pytest.fail("expected both timestamps None after clearing")
    if os.path.exists(cr.calendar_secret_path(tmp)):
        pytest.fail("secret file still present after clearing")


def test_rejected_values_change_nothing(tmp_path):
    """save_calendar_url() returns False and leaves an existing secret file's bytes and mode, and a seeded registry, untouched for None, an empty string, a whitespace-only string and a non-string value"""
    import stat as stat_mod
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics", now=now):
        pytest.fail("test setup failure: initial save failed")
    if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
        pytest.fail("test setup failure: re-seed failed")
    path = cr.calendar_secret_path(tmp)
    with open(path, "rb") as fh:
        before_bytes = fh.read()
    before_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
    for rejected in (None, "", "   ", 17):
        if cr.save_calendar_url(tmp, rejected, now=now) is not False:
            pytest.fail("expected False for rejected value %r" % (rejected,))
        with open(path, "rb") as fh:
            after_bytes = fh.read()
        if after_bytes != before_bytes:
            pytest.fail("secret file content changed after rejected value %r" % (rejected,))
        after_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
        if after_mode != before_mode:
            pytest.fail("secret file mode changed after rejected value %r" % (rejected,))
        loaded = cr.load_calendar_registry(tmp, now)
        if [e["origin_iata"] for e in loaded["entries"]] != ["ORY"]:
            pytest.fail("registry entries changed after rejected value %r" % (rejected,))


def test_content_round_trips_stripped(tmp_path):
    """save_calendar_url() strips leading/trailing whitespace and a trailing newline, writing the bare URL with no trailing newline byte, at mode 0600"""
    import stat as stat_mod
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "  https://example.invalid/feed.ics?t=abc  \n"):
        pytest.fail("test setup failure: save_calendar_url() returned False")
    path = cr.calendar_secret_path(tmp)
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw != b"https://example.invalid/feed.ics?t=abc":
        pytest.fail("expected the bare stripped URL with no trailing newline, got %r" % (raw,))
    if stat_mod.S_IMODE(os.stat(path).st_mode) != 0o600:
        pytest.fail("expected the round-tripped file to still be 0o600")


def test_no_temp_file_survives(tmp_path):
    """no file matching the temporary-name shape remains in state_dir after a successful write or a rejected call"""
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
        pytest.fail("test setup failure: successful write failed")
    if cr.save_calendar_url(tmp, "") is not False:
        pytest.fail("test setup failure: rejected call did not return False")
    for name in os.listdir(tmp):
        if name.endswith(".tmp"):
            pytest.fail("a temporary file survived: %r" % (name,))


def test_sentinel_is_identity_only(tmp_path):
    """passing the literal string 'CLEAR_CALENDAR_URL' takes the ordinary write branch, not the sentinel's clear branch (identity comparison only)"""
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "CLEAR_CALENDAR_URL"):
        pytest.fail("test setup failure: the literal string 'CLEAR_CALENDAR_URL' was rejected")
    path = cr.calendar_secret_path(tmp)
    if not os.path.exists(path):
        pytest.fail("the literal string took the clear branch instead of the write branch")
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw != b"CLEAR_CALENDAR_URL":
        pytest.fail("expected the literal string written to the file, got %r" % (raw,))


def test_accessor_reads_the_secret_file(tmp_path):
    """configured_calendar_url() returns exactly the value written through save_calendar_url(), and calendar_is_configured() is True (identity) for the same state_dir (D-03)"""
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
    url = cr.configured_calendar_url(tmp)
    if url != "https://example.invalid/feed.ics":
        pytest.fail("expected the file's exact value, got %r" % (url,))
    if cr.calendar_is_configured(tmp) is not True:
        pytest.fail("expected calendar_is_configured() to be True (identity)")


def test_environment_is_never_consulted(monkeypatch, tmp_path_factory):
    """neither configured_calendar_url() nor calendar_is_configured() ever calls os.environ.get() - the check that would catch a resurrected environment read, with and without a secret file present (D-03)"""
    configured_tmp = tmp_path_factory.mktemp("configured")
    _write_calendar_secret(configured_tmp, "https://example.invalid/feed.ics")
    unconfigured_tmp = tmp_path_factory.mktemp("unconfigured")
    real_get = os.environ.get
    calls = []

    def spy_get(key, default=None):
        calls.append(key)
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", spy_get)
    url = cr.configured_calendar_url(configured_tmp)
    configured = cr.calendar_is_configured(configured_tmp)
    url2 = cr.configured_calendar_url(unconfigured_tmp)
    configured2 = cr.calendar_is_configured(unconfigured_tmp)
    if calls:
        pytest.fail(
            "os.environ.get() was called %d time(s) during accessor calls - a "
            "resurrected environment read: %r" % (len(calls), calls))
    if url != "https://example.invalid/feed.ics":
        pytest.fail("expected the secret file's value, got %r" % (url,))
    if configured is not True:
        pytest.fail("expected calendar_is_configured() to be True with a secret file present")
    if url2 is not None:
        pytest.fail("expected None with no secret file present, got %r" % (url2,))
    if configured2 is not False:
        pytest.fail("expected calendar_is_configured() to be False with no secret file present")


def test_drifted_file_refuses_without_being_opened(monkeypatch, tmp_path):
    """configured_calendar_url() refuses a secret file whose permissions have drifted, and never opens it at all - proved by observing the file was not opened, not merely by observing the return value (D-02, T-17-DRIFT)"""
    import builtins
    import stat as stat_mod
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
    path = cr.calendar_secret_path(tmp)
    os.chmod(path, 0o644)
    if not (stat_mod.S_IMODE(os.stat(path).st_mode) & (stat_mod.S_IRWXG | stat_mod.S_IRWXO)):
        pytest.fail("test setup failure: chmod(0o644) did not produce a group/other-readable file")
    real_open = builtins.open
    opened_paths = []

    def spy_open(file, *a, **k):
        opened_paths.append(file)
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    url = cr.configured_calendar_url(tmp)
    if url is not None:
        pytest.fail("expected None for a drifted-permission file, got %r" % (url,))
    if path in opened_paths:
        pytest.fail(
            "the secret file's path was opened even though its permissions were drifted - "
            "the value may have been read into memory: %r" % (opened_paths,))


def test_ordinary_umask_file_refused_end_to_end(tmp_path):
    """a secret file written through this codebase's ordinary umask-inheriting house idiom (plain open(path, 'w'), not save_calendar_url()'s explicit 0600) is refused end to end by configured_calendar_url() and calendar_is_configured() - the negative counterpart to F1, going through the accessor rather than the mode predicate alone"""
    import stat as stat_mod
    tmp = tmp_path
    path = cr.calendar_secret_path(tmp)
    with open(path, "w") as fh:
        fh.write("https://example.invalid/feed.ics")
    mode = stat_mod.S_IMODE(os.stat(path).st_mode)
    if not (mode & (stat_mod.S_IRWXG | stat_mod.S_IRWXO)):
        pytest.fail((
            "test setup failure: the process umask produced an owner-only file (%o) - this "
            "check needs a group/other-readable file to be meaningful" % (mode,)))
    url = cr.configured_calendar_url(tmp)
    if url is not None:
        pytest.fail((
            "expected None for a file written through the ordinary umask-inheriting idiom, "
            "got %r" % (url,)))
    if cr.calendar_is_configured(tmp) is not False:
        pytest.fail("expected calendar_is_configured() to be False for the same file")


def test_boolean_contract_in_three_states(tmp_path):
    """calendar_is_configured() returns a genuine bool - is True, is False, is False - across absent, configured, and permission-drifted secret files, never a truthy status string (D-08)"""
    tmp = tmp_path
    if cr.calendar_is_configured(tmp) is not False:
        pytest.fail("expected False (identity) for an absent secret file")
    _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
    if cr.calendar_is_configured(tmp) is not True:
        pytest.fail("expected True (identity) for a configured secret file")
    path = cr.calendar_secret_path(tmp)
    os.chmod(path, 0o644)
    if cr.calendar_is_configured(tmp) is not False:
        pytest.fail("expected False (identity) for a drifted-permission secret file")


def test_accessor_strips_hand_written_trailing_newline(tmp_path):
    """configured_calendar_url() strips a trailing newline from a hand-written secret file, returning the bare URL"""
    tmp = tmp_path
    path = cr.calendar_secret_path(tmp)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("https://example.invalid/feed.ics\n")
    url = cr.configured_calendar_url(tmp)
    if url != "https://example.invalid/feed.ics":
        pytest.fail("expected the trailing newline stripped, got %r" % (url,))


def test_min_interval_s_bypasses_the_throttle(tmp_path):
    """refresh_calendar_registry(min_interval_s=0) bypasses the throttle and reaches the transport even when the recorded last attempt is well inside the standard interval, while the default (no interval argument) still honours the throttle (D-06)"""
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
    seed_now = 1_800_000_000.0
    if not cr.write_calendar_registry(tmp, [], seed_now, None, now=seed_now):
        pytest.fail("test setup failure: seed write failed")
    now = seed_now + 60.0  # well inside CALENDAR_FETCH_INTERVAL_S (1800s)

    calls = []
    transport = make_calendar_transport(
        status_code=200, body=b"BEGIN:VCALENDAR\nEND:VCALENDAR", calls=calls)

    code, _reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
    if code != cr.FETCH_SKIPPED_THROTTLED:
        pytest.fail("expected FETCH_SKIPPED_THROTTLED with no interval override, got %r" % (code,))
    if calls:
        pytest.fail("expected no transport call with the default (None) interval, got %r" % (calls,))

    code2, _reg2 = cr.refresh_calendar_registry(tmp, now, transport=transport, min_interval_s=0)
    if code2 != cr.FETCH_OK:
        pytest.fail("expected FETCH_OK when min_interval_s=0 bypasses the throttle, got %r" % (code2,))
    if len(calls) != 1:
        pytest.fail("expected exactly one transport call once the throttle was bypassed, got %d" % (len(calls),))


def test_clear_branch_reports_failure_when_removal_actually_fails(tmp_path):
    """save_calendar_url(CLEAR_CALENDAR_URL) returns False, not True, when os.remove() fails for a reason other than the file already being absent - a permission/immutable-flag/read-only-filesystem failure must never be reported as a successful disconnect (CR-02)"""
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
        pytest.fail("test setup failure: initial save failed")
    path = cr.calendar_secret_path(tmp)
    real_remove = cr.os.remove

    def _spy_remove(target, *args, **kwargs):
        if target == path:
            raise PermissionError(13, "Permission denied")
        return real_remove(target, *args, **kwargs)

    cr.os.remove = _spy_remove
    try:
        result = cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL)
    finally:
        cr.os.remove = real_remove

    if result is not False:
        pytest.fail((
            "expected False when the secret file could not actually be removed, got %r" % (result,)))
    if not os.path.exists(path):
        pytest.fail("test setup failure: the file should still exist since removal was blocked")
    if cr.calendar_is_configured(tmp) is not True:
        pytest.fail((
            "calendar_is_configured() should still report True - the file genuinely was not removed"))


def test_cross_process_lock_closes_the_disconnect_race(tmp_path):
    """a companion disconnect arriving while a (simulated) concurrent poll cycle is mid-fetch cannot have its registry erase overwritten by that poll cycle's later write - the cross-process registry lock, not either in-process threading.Lock, is what is exercised here (CR-01; simulates two OS processes with two threads racing the real fcntl-based lock - see comment above)"""
    import threading
    import time
    now = _mid_fixture_now()
    tmp = tmp_path
    _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)

    started = threading.Event()
    release = threading.Event()

    def _slow_transport(url, timeout):
        started.set()
        release.wait(timeout=10)
        return _FakeCalendarResponse(200, fixture_text.encode())

    poll_result = {}

    def _poll_thread_body():
        poll_result["code"], poll_result["registry"] = cr.refresh_calendar_registry(
            tmp, now, transport=_slow_transport)

    disconnect_result = {}

    def _disconnect_thread_body():
        disconnect_result["ok"] = cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL, now=now)

    t_poll = threading.Thread(target=_poll_thread_body)
    t_poll.start()
    if not started.wait(timeout=5):
        t_poll.join(timeout=1)
        pytest.fail("test setup failure: the simulated poll cycle's fetch never started")

    t_disconnect = threading.Thread(target=_disconnect_thread_body)
    t_disconnect.start()
    # Best-effort: give the disconnect thread a moment to actually
    # reach and start blocking on the lock, so the interleaving is
    # deterministic rather than accidentally already-serial. Not
    # required for correctness - only for making the race
    # reliably exercised rather than reliably avoided.
    time.sleep(0.2)

    release.set()
    t_poll.join(timeout=10)
    t_disconnect.join(timeout=10)

    if t_poll.is_alive() or t_disconnect.is_alive():
        pytest.fail("test setup failure: a thread did not finish within its timeout")
    if not disconnect_result.get("ok"):
        pytest.fail("test setup failure: the disconnect call returned False")

    loaded = cr.load_calendar_registry(tmp, now)
    if loaded["entries"] != []:
        pytest.fail((
            "the disconnect's erase was overwritten by the concurrently-running poll cycle's "
            "write - registry has %r entries after an explicit disconnect (CR-01)"
            % (loaded["entries"],)))
    if cr.calendar_is_configured(tmp):
        pytest.fail("expected calendar_is_configured() to be False after the disconnect")


def test_write_failure_before_erase_preserves_the_previous_calendars_flights(tmp_path):
    """save_calendar_url() replacing a connected calendar's URL leaves the previous calendar's already-fetched flights untouched when the new secret's write fails before ever reaching the registry erase (WR-01)"""
    from datetime import datetime, timezone
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "https://example.invalid/old-feed.ics", now=now):
        pytest.fail("test setup failure: initial save failed")
    if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
        pytest.fail("test setup failure: seeding fetched entries failed")

    real_fdopen = cr.os.fdopen

    def _failing_fdopen(fd, *args, **kwargs):
        os.close(fd)
        raise OSError(28, "No space left on device")

    cr.os.fdopen = _failing_fdopen
    try:
        result = cr.save_calendar_url(tmp, "https://example.invalid/new-feed.ics", now=now)
    finally:
        cr.os.fdopen = real_fdopen

    if result is not False:
        pytest.fail("expected False when the secret's temp-file write fails, got %r" % (result,))
    loaded = cr.load_calendar_registry(tmp, now)
    if [e["origin_iata"] for e in loaded["entries"]] != ["ORY"]:
        pytest.fail((
            "the previous calendar's already-fetched flights were erased despite the secret "
            "write never succeeding - expected them untouched, got %r" % (loaded["entries"],)))
    if cr.configured_calendar_url(tmp) != "https://example.invalid/old-feed.ics":
        pytest.fail("expected the OLD url to still be configured after a failed replace")


def test_normalise_calendar_url_rewrites_only_webcal():
    """_normalise_calendar_url() rewrites a webcal scheme (any case) to https, leaves every other scheme and an unparseable value unchanged, and never raises on None (UAT)"""
    cases = [
        ("webcal://example.invalid/feed.ics", "https://example.invalid/feed.ics"),
        ("WEBCAL://example.invalid/feed.ics", "https://example.invalid/feed.ics"),
        ("https://example.invalid/feed.ics", "https://example.invalid/feed.ics"),
        ("http://example.invalid/feed.ics", "http://example.invalid/feed.ics"),
        ("ftp://example.invalid/feed.ics", "ftp://example.invalid/feed.ics"),
        ("not-a-url", "not-a-url"),
    ]
    for given, expected in cases:
        got = cr._normalise_calendar_url(given)
        if got != expected:
            pytest.fail("expected _normalise_calendar_url(%r) == %r, got %r" % (given, expected, got))
    if cr._normalise_calendar_url(None) is not None:
        pytest.fail("expected _normalise_calendar_url(None) to return None without raising")


def test_fetch_ics_accepts_webcal_as_https():
    """fetch_ics() accepts a webcal:// URL - Apple Calendar's own share-link scheme - and the transport observes an https:// request (UAT)"""
    calls = []
    transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR", calls=calls)
    result = cr.fetch_ics("webcal://%s/feed.ics" % PUBLIC_IP, transport=transport)
    if result != "BEGIN:VCALENDAR":
        pytest.fail("expected a webcal:// URL to be fetched successfully, got %r" % (result,))
    if calls != ["https://%s/feed.ics" % PUBLIC_IP]:
        pytest.fail("expected the transport to observe an https:// request, got %r" % (calls,))


def test_webcal_does_not_weaken_the_address_gate(monkeypatch):
    """the webcal:// rewrite does not weaken the address gate - fetch_ics() still refuses a webcal:// URL pointing at a private address, at loopback (literal IP and "localhost"), and at the cloud metadata address (UAT)"""
    real_getaddrinfo = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: (
        [(2, 1, 6, "", ("127.0.0.1", 443))] if host == "localhost"
        else real_getaddrinfo(host, port, *a, **k)))
    unsafe = (
        "webcal://10.0.0.5/feed.ics",         # private (RFC 1918)
        "webcal://127.0.0.1/feed.ics",        # loopback, literal IP
        "webcal://localhost/feed.ics",        # loopback, hostname
        "webcal://169.254.169.254/feed.ics",  # cloud metadata (link-local)
    )
    for url in unsafe:
        transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR")
        result = cr.fetch_ics(url, transport=transport)
        if result is not None:
            pytest.fail("expected fetch_ics(%r) to be refused, got %r" % (url, result))


def test_http_still_refused_no_downgrade_path():
    """fetch_ics() still refuses a plain http:// URL - there is no webcal -> http downgrade path (UAT)"""
    transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR")
    result = cr.fetch_ics("http://%s/feed.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected http:// to still be refused, got %r" % (result,))


def test_redirect_from_normalised_webcal_still_revalidated():
    """a redirect discovered while fetching a webcal:// URL (normalised to https:// first) is still re-validated per hop, refusing a Location that targets a loopback address (UAT)"""
    calls = []
    transport = make_calendar_transport(
        status_code=302, headers={"Location": "https://127.0.0.1/a.ics"},
        is_redirect=True, calls=calls)
    result = cr.fetch_ics("webcal://%s/a.ics" % PUBLIC_IP, transport=transport)
    if result is not None:
        pytest.fail("expected None when a webcal:// URL's redirect targets a loopback address")
    if calls != ["https://%s/a.ics" % PUBLIC_IP]:
        pytest.fail("expected exactly one transport call (the redirect target must never be fetched): %r" % (calls,))


def test_save_calendar_url_stores_the_normalised_form(tmp_path):
    """save_calendar_url() stores a webcal:// value already rewritten to its https:// form, so the secret file never holds a webcal:// string (UAT)"""
    tmp = tmp_path
    if not cr.save_calendar_url(tmp, "webcal://example.invalid/feed.ics"):
        pytest.fail("test setup failure: save_calendar_url() returned False")
    path = cr.calendar_secret_path(tmp)
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw != b"https://example.invalid/feed.ics":
        pytest.fail("expected the stored secret to be the normalised https:// form, got %r" % (raw,))
    if cr.configured_calendar_url(tmp) != "https://example.invalid/feed.ics":
        pytest.fail("expected configured_calendar_url() to return the normalised https:// form")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
