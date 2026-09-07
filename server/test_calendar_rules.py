#!/usr/bin/env python3
"""Contract harness for server/plane/calendar_rules.py - phase 16's
hand-rolled RFC 5545 subset parser (16-VALIDATION.md's Wave 0 harness
requirement).

Stdlib-only, plus the module under test (server.plane.calendar_rules) and
the committed redacted fixture (server/fixtures/calendar_crewwebplus_redacted.ics).
Every fixture directory this harness needs beyond that one committed .ics
file is a tempfile.TemporaryDirectory(), never a shared/real state dir.
Exits 0 only when every check below passes; any failure (or exception -
none is ever swallowed into a pass) exits 1.

Later plans in phase 16 (16-03's registry, 16-04's fetch hardening, 16-06's
matcher) extend this same harness with their own checks rather than
introducing a second file - see each plan's own <files> list.

Usage:
    server/.venv/bin/python3 server/test_calendar_rules.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FIXTURE_ICS = "calendar_crewwebplus_redacted.ics"

# Mirrors the fixture's own committed X-SKYPANE-FIXTURE-EXPECTED-ENTRIES
# property. Check 11 below asserts the two agree, so the fixture and this
# harness can never silently drift apart.
FIXTURE_EXPECTED_ENTRIES = 4

# Initial value for this file, introduced by phase 16 plan 01 (20 checks,
# the parser). Re-derived by RUNNING the harness (not by arithmetic), per
# this repo's own documented discipline (see server/test_colour_rules.py's
# own EXPECTED_CHECK_COUNT comment). Phase 16 plan 03 raised it to 31,
# adding the registry (D-01), rolling window and throttle (D-03) checks.
# Later plans in this phase raise it further as they add checks.
EXPECTED_CHECK_COUNT = 31


def load_fixture_text(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return fh.read()


def _entry(airline_iata, origin_iata, destination_iata, start_at, end_at):
    """Build one well-shaped CALENDAR_REGISTRY_KEYS entry for the registry,
    window and throttle checks below (plan 16-03) - the same five-key
    shape parse_ics_events() emits.
    """
    return {
        "airline_iata": airline_iata,
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
        "start_at": start_at,
        "end_at": end_at,
    }


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.plane.calendar_rules as cr
    except ImportError as exc:
        print("FAIL import server.plane.calendar_rules - %r" % (exc,))
        print("calendar_rules: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    fixture_text = load_fixture_text(FIXTURE_ICS)

    # 1. A SPACE continuation is rejoined with the marker removed and
    #    nothing else lost.
    def _unfold_space_continuation():
        raw = "SUMMARY:hello wo\n rld"
        result = cr.unfold_ics_lines(raw)
        if result != ["SUMMARY:hello world"]:
            return False, "expected ['SUMMARY:hello world'], got %r" % (result,)
        return True, ""
    check("unfold_ics_lines() rejoins a SPACE continuation with the marker removed and nothing else lost", _unfold_space_continuation)

    # 2. A HTAB continuation is rejoined the same way.
    def _unfold_htab_continuation():
        raw = "SUMMARY:hello wo\n\trld"
        result = cr.unfold_ics_lines(raw)
        if result != ["SUMMARY:hello world"]:
            return False, "expected ['SUMMARY:hello world'], got %r" % (result,)
        return True, ""
    check("unfold_ics_lines() rejoins a HTAB continuation with the marker removed and nothing else lost", _unfold_htab_continuation)

    # 3. Three physical lines fold into one logical line (a continuation
    #    of a continuation).
    def _unfold_three_physical_lines():
        raw = "SUMMARY:one\n two\n\tthree"
        result = cr.unfold_ics_lines(raw)
        if result != ["SUMMARY:onetwothree"]:
            return False, "expected ['SUMMARY:onetwothree'], got %r" % (result,)
        return True, ""
    check("unfold_ics_lines() folds three physical lines (a continuation of a continuation) into one logical line", _unfold_three_physical_lines)

    # 4. A synthetic SUMMARY longer than 75 octets, folded across two
    #    physical lines with a SPACE marker, round-trips to its exact
    #    original value.
    def _unfold_long_summary_round_trips():
        original = "SUMMARY:" + "This is a deliberately long synthetic summary value exceeding the fold threshold."
        if len(original) <= 75:
            return False, "test setup failure: original value is not over 75 octets"
        split_at = 60
        folded = original[:split_at] + "\n " + original[split_at:]
        result = cr.unfold_ics_lines(folded)
        if result != [original]:
            return False, "expected exact round-trip %r, got %r" % (original, result)
        return True, ""
    check("unfold_ics_lines() round-trips a synthetic SUMMARY over 75 octets folded across two physical lines to its exact original value", _unfold_long_summary_round_trips)

    # 5. A continuation-shaped line at the very start of the text (no
    #    previous logical line to join onto) does not raise and is kept
    #    as its own line.
    def _unfold_leading_continuation_does_not_raise():
        raw = " orphan continuation\nSUMMARY:XX"
        result = cr.unfold_ics_lines(raw)
        if result != [" orphan continuation", "SUMMARY:XX"]:
            return False, "expected the orphan line kept as-is, got %r" % (result,)
        return True, ""
    check("unfold_ics_lines() on text whose very first line is a continuation does not raise and keeps that line as its own", _unfold_leading_continuation_does_not_raise)

    # 6. The CRLF form of the committed fixture unfolds to the identical
    #    list as the LF form.
    def _unfold_crlf_matches_lf():
        crlf_text = fixture_text.replace("\n", "\r\n")
        if cr.unfold_ics_lines(fixture_text) != cr.unfold_ics_lines(crlf_text):
            return False, "CRLF form unfolded to a different list than the LF form"
        return True, ""
    check("unfold_ics_lines() unfolds the fixture's CRLF form to the identical list as its committed LF form", _unfold_crlf_matches_lf)

    # 7. Non-string input to unfold_ics_lines() returns an empty list
    #    without raising.
    def _unfold_non_string_input():
        if cr.unfold_ics_lines(None) != []:
            return False, "unfold_ics_lines(None) did not return []"
        if cr.unfold_ics_lines(42) != []:
            return False, "unfold_ics_lines(42) did not return []"
        return True, ""
    check("unfold_ics_lines() returns an empty list for non-string input (None, an int) without raising", _unfold_non_string_input)

    # 8. split_property() on a parameter-bearing line yields the bare
    #    name and the value with no parameter residue.
    def _split_property_strips_parameters():
        name, params, value = cr.split_property("DTSTART;VALUE=DATE-TIME:20260901T060000Z")
        if name != "DTSTART":
            return False, "expected name 'DTSTART', got %r" % (name,)
        if value != "20260901T060000Z":
            return False, "expected value '20260901T060000Z' with no parameter residue, got %r" % (value,)
        if params != "VALUE=DATE-TIME":
            return False, "expected params 'VALUE=DATE-TIME', got %r" % (params,)
        return True, ""
    check("split_property() on a parameter-bearing line yields the bare uppercased name and a value with no parameter residue", _split_property_strips_parameters)

    # 9. split_property() on a line whose value itself contains a colon
    #    keeps the whole value intact.
    def _split_property_value_with_colon():
        name, _params, value = cr.split_property("X-CUSTOM:http://example.invalid/a:b")
        if name != "X-CUSTOM":
            return False, "expected name 'X-CUSTOM', got %r" % (name,)
        if value != "http://example.invalid/a:b":
            return False, "expected the whole value with its own colon intact, got %r" % (value,)
        return True, ""
    check("split_property() partitions on the FIRST colon only, keeping a value's own embedded colon intact", _split_property_value_with_colon)

    # 10. split_property() on a line with no colon at all returns no name
    #     rather than raising.
    def _split_property_no_colon():
        name, params, value = cr.split_property("no-colon-here")
        if name is not None or params is not None or value is not None:
            return False, "expected (None, None, None), got %r" % ((name, params, value),)
        return True, ""
    check("split_property() on a line with no colon at all returns (None, None, None) rather than raising", _split_property_no_colon)

    # 11. The fixture's own X-SKYPANE-FIXTURE-EXPECTED-ENTRIES property
    #     agrees with this harness's FIXTURE_EXPECTED_ENTRIES constant, so
    #     the fixture and the harness cannot silently drift apart.
    def _fixture_ledger_agrees_with_harness_constant():
        match = re.search(r"X-SKYPANE-FIXTURE-EXPECTED-ENTRIES:(\d+)", fixture_text)
        if match is None:
            return False, "fixture is missing the X-SKYPANE-FIXTURE-EXPECTED-ENTRIES property"
        fixture_value = int(match.group(1))
        if fixture_value != FIXTURE_EXPECTED_ENTRIES:
            return False, "fixture says %d, harness constant says %d" % (fixture_value, FIXTURE_EXPECTED_ENTRIES)
        return True, ""
    check("the fixture's own X-SKYPANE-FIXTURE-EXPECTED-ENTRIES property agrees with this harness's FIXTURE_EXPECTED_ENTRIES constant", _fixture_ledger_agrees_with_harness_constant)

    # 12. Parsing the committed fixture yields exactly
    #     FIXTURE_EXPECTED_ENTRIES entries.
    def _fixture_parses_to_expected_count():
        entries = cr.parse_ics_events(fixture_text)
        if len(entries) != FIXTURE_EXPECTED_ENTRIES:
            return False, "expected %d entries, got %d: %r" % (FIXTURE_EXPECTED_ENTRIES, len(entries), entries)
        return True, ""
    check("parse_ics_events() on the committed fixture returns exactly FIXTURE_EXPECTED_ENTRIES entries", _fixture_parses_to_expected_count)

    # 13. No surviving entry's timestamp falls in the 19th century -
    #     proving the two STATUS:CANCELLED 1899-placeholder events were
    #     dropped before their dates ever mattered.
    def _no_nineteenth_century_entries():
        entries = cr.parse_ics_events(fixture_text)
        # Any real Unix epoch second for the year 1899 is a large negative
        # number; every surviving entry's start_at must be positive and
        # plausibly in this fixture's 2026 window.
        for entry in entries:
            if entry["start_at"] <= 0 or entry["end_at"] <= 0:
                return False, "found an entry with a non-positive epoch timestamp (19th-century junk survived): %r" % (entry,)
        return True, ""
    check("no entry parsed from the fixture carries a 19th-century timestamp - the two STATUS:CANCELLED placeholder events were dropped", _no_nineteenth_century_entries)

    # 14. No entry derives from the OFFD, CAHC or CPBL blocks - asserted
    #     positively by checking every returned entry's route matches one
    #     of the four flight events' routes, and the total count is
    #     exactly four so an extra non-flight entry would fail on the
    #     count alone.
    def _no_entries_from_non_flight_categories():
        entries = cr.parse_ics_events(fixture_text)
        expected_routes = {("ORY", "AAA"), ("AAA", "ORY"), ("BBB", "ORY")}
        for entry in entries:
            route = (entry["origin_iata"], entry["destination_iata"])
            if route not in expected_routes:
                return False, "entry with unexpected route %r - it may derive from an OFFD/CAHC/CPBL block: %r" % (route, entry)
        if len(entries) != 4:
            return False, "expected exactly 4 entries, got %d" % (len(entries),)
        return True, ""
    check("no entry derives from the OFFD, CAHC or CPBL blocks - every route matches one of the four flight events and the count is exactly four", _no_entries_from_non_flight_categories)

    # 15. parse_ics_datetime() returns a float for the bare-UTC form.
    def _parse_ics_datetime_accepts_bare_utc():
        result = cr.parse_ics_datetime("20260901T060000Z")
        if not isinstance(result, float):
            return False, "expected a float, got %r" % (result,)
        return True, ""
    check("parse_ics_datetime() returns a float epoch for the bare-UTC form", _parse_ics_datetime_accepts_bare_utc)

    # 16. parse_ics_datetime() returns None for every unrecognised or
    #     invalid date shape - CORRECTION 2's rejection sweep.
    def _parse_ics_datetime_rejection_sweep():
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
                return False, "parse_ics_datetime(%r) returned %r, expected None" % (value, result)
        return True, ""
    check("parse_ics_datetime() returns None for a VALUE=DATE value, a TZID-qualified value, a lowercase-z value, an empty string, a non-string, and a calendrically impossible value", _parse_ics_datetime_rejection_sweep)

    # 17. The TZID tripwire is rejected loudly: parsing the fixture with
    #     stderr captured emits a line naming a non-zero date-form
    #     rejection count, the entry count stays four, and the captured
    #     stderr never contains an eight-digit date string (never leaking
    #     a rejected value).
    def _tzid_tripwire_rejected_loudly_without_leaking_a_date():
        buf = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = buf
        try:
            entries = cr.parse_ics_events(fixture_text)
        finally:
            sys.stderr = old_stderr
        captured = buf.getvalue()
        if len(entries) != FIXTURE_EXPECTED_ENTRIES:
            return False, "expected %d entries even with the TZID tripwire rejected, got %d" % (FIXTURE_EXPECTED_ENTRIES, len(entries))
        if not re.search(r"\brejected for an unrecognised date form\b", captured):
            return False, "expected a date-form rejection line on stderr, got %r" % (captured,)
        date_form_match = re.search(r"(\d+) rejected for an unrecognised date form", captured)
        if date_form_match is None or int(date_form_match.group(1)) < 1:
            return False, "expected a non-zero date-form rejection count, got %r" % (captured,)
        if re.search(r"\d{8}", captured):
            return False, "stderr must never contain an eight-digit date string, got %r" % (captured,)
        return True, ""
    check("the TZID tripwire is rejected loudly (a non-zero date-form rejection count on stderr) while the entry count stays four and no eight-digit date leaks", _tzid_tripwire_rejected_loudly_without_leaking_a_date)

    # 18. parse_ics_events() never raises on any of seven hostile bodies,
    #     degrading to an empty list every time.
    def _parse_ics_events_never_raises():
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
                return False, "parse_ics_events(%r) returned %r, expected []" % (body, result)
        return True, ""
    check("parse_ics_events() never raises and returns an empty list for seven hostile bodies (empty, None, non-string, unterminated block, punctuation, no-colon lines, decoded random bytes)", _parse_ics_events_never_raises)

    # 19. A synthetic body repeating one valid flight event more times
    #     than CALENDAR_MAX_ENTRIES returns exactly CALENDAR_MAX_ENTRIES
    #     entries.
    def _bounded_output_at_max_entries():
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
        repeat_count = cr.CALENDAR_MAX_ENTRIES + 200
        body = "BEGIN:VCALENDAR\nPRODID:-//test//test//EN\n" + "".join(
            one_event % i for i in range(repeat_count)
        ) + "END:VCALENDAR\n"
        entries = cr.parse_ics_events(body)
        if len(entries) != cr.CALENDAR_MAX_ENTRIES:
            return False, "expected exactly %d entries, got %d" % (cr.CALENDAR_MAX_ENTRIES, len(entries))
        return True, ""
    check("parse_ics_events() on a body with more VEVENT blocks than CALENDAR_MAX_ENTRIES returns exactly CALENDAR_MAX_ENTRIES entries", _bounded_output_at_max_entries)

    # 20. Every returned entry has exactly the five expected keys, and
    #     serialising the whole list to JSON contains none of the
    #     fixture's flight-number tokens, UID tokens, or description text.
    def _record_shape_carries_no_schedule_text():
        import json
        entries = cr.parse_ics_events(fixture_text)
        expected_keys = {"airline_iata", "origin_iata", "destination_iata", "start_at", "end_at"}
        for entry in entries:
            if set(entry) != expected_keys:
                return False, "expected exactly %r, got %r" % (expected_keys, set(entry))
        blob = json.dumps(entries)
        forbidden_substrings = ["XX1001", "XX1002", "XX2001", "XX2002", "fixture-000", "DESCRIPTION", "Aircraft type"]
        for forbidden in forbidden_substrings:
            if forbidden in blob:
                return False, "serialised entries leak schedule text %r: %r" % (forbidden, blob)
        return True, ""
    check("every returned entry has exactly the five expected keys, and the serialised list carries no flight number, UID, or description text", _record_shape_carries_no_schedule_text)

    # --- Phase 16 plan 03: registry (D-01), rolling window and throttle
    #     (D-03) checks, added below the plan 16-01 parser checks above. ---

    # 21. D-01's headline proof: writing and re-writing a populated
    #     calendar registry never touches colour_rules.json - not its
    #     parsed content, not its bytes on disk - and the two registries
    #     are two distinct files that coexist in the same state dir.
    def _d01_calendar_never_touches_colour_rules():
        import hashlib
        import tempfile
        import server.plane.colour_rules as colour_rules
        with tempfile.TemporaryDirectory() as tmp:
            colour_rules.add_rule(tmp, "prefix", "AFR", "white")
            before_registry = colour_rules.load_colour_rules(tmp)
            with open(colour_rules.colour_rules_path(tmp), "rb") as fh:
                before_hash = hashlib.sha256(fh.read()).hexdigest()

            entries_a = [_entry("XX", "AAA", "ORY", 1.0, 2.0)]
            entries_b = [
                _entry("XX", "BBB", "ORY", 3.0, 4.0),
                _entry("XX", "CCC", "ORY", 5.0, 6.0),
            ]
            cr.write_calendar_registry(tmp, entries_a, 10.0, None)
            cr.write_calendar_registry(tmp, entries_b, 20.0, "2026-09-07T00:00:00+00:00")

            after_registry = colour_rules.load_colour_rules(tmp)
            with open(colour_rules.colour_rules_path(tmp), "rb") as fh:
                after_hash = hashlib.sha256(fh.read()).hexdigest()

            if after_registry != before_registry:
                return False, ("colour_rules.load_colour_rules() output changed after a "
                                "calendar registry write: an automatic source touched the "
                                "operator's hand-written rules")
            if after_hash != before_hash:
                return False, "colour_rules.json's bytes changed after a calendar registry write"
            if not os.path.exists(cr.calendar_rules_path(tmp)):
                return False, "calendar_rules.json was not written"
            if cr.calendar_rules_path(tmp) == colour_rules.colour_rules_path(tmp):
                return False, "calendar_rules.json and colour_rules.json resolved to the same path"
        return True, ""
    check("D-01: writing and re-writing the calendar registry never touches colour_rules.json's content or bytes, and the two registries are distinct files", _d01_calendar_never_touches_colour_rules)

    # 22. D-03's whole-file rewrite: a second write with a different,
    #     shorter entry list leaves ONLY that list on disk - never a merge
    #     with the earlier one.
    def _d03_whole_file_rewrite_never_merges():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            entries_a = [
                _entry("XX", "AAA", "ORY", 1.0, 2.0),
                _entry("XX", "BBB", "ORY", 3.0, 4.0),
            ]
            entries_b = [_entry("XX", "CCC", "ORY", 5.0, 6.0)]
            cr.write_calendar_registry(tmp, entries_a, 100.0, "2026-09-07T00:00:00+00:00")
            cr.write_calendar_registry(tmp, entries_b, 200.0, "2026-09-07T01:00:00+00:00")
            loaded = cr.load_calendar_registry(tmp)
            origins = sorted(e["origin_iata"] for e in loaded["entries"])
            if origins != ["CCC"]:
                return False, ("expected only entries_b's entry to survive (no merge with "
                                "entries_a), got %r" % (origins,))
        return True, ""
    check("write_calendar_registry() replaces the whole file - a shorter second write leaves only that list, never a merge with the earlier one", _d03_whole_file_rewrite_never_merges)

    # 23. A successful fetch that legitimately returns nothing empties the
    #     window rather than leaving yesterday's flights behind, and both
    #     timestamps are still readable afterwards.
    def _d03_empty_write_empties_the_window():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cr.write_calendar_registry(
                tmp, [_entry("XX", "AAA", "ORY", 1.0, 2.0)], 100.0, "2026-09-07T00:00:00+00:00")
            cr.write_calendar_registry(tmp, [], 200.0, "2026-09-07T01:00:00+00:00")
            loaded = cr.load_calendar_registry(tmp)
            if loaded["entries"] != []:
                return False, "expected an empty entries list after an empty write, got %r" % (loaded["entries"],)
            if loaded["last_attempt_at"] != 200.0 or loaded["last_synced_at"] != "2026-09-07T01:00:00+00:00":
                return False, "timestamps did not survive an empty write: %r" % (loaded,)
        return True, ""
    check("write_calendar_registry([]) empties the registry rather than leaving the previous entries behind, with both timestamps still readable", _d03_empty_write_empties_the_window)

    # 24. select_window_entries() keeps an already-landed-earlier-today
    #     entry, a later-today entry and a 47h-ahead entry; drops one
    #     ended yesterday and one 49h ahead; returns sorted ascending;
    #     never mutates its input.
    def _rolling_window_keeps_and_drops_the_expected_entries():
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
            return False, "select_window_entries() mutated its input list"
        kept_starts = [e["start_at"] for e in kept]
        expected_starts = sorted(
            e["start_at"] for e in (landed_earlier_today, later_today, forty_seven_ahead))
        if sorted(kept_starts) != expected_starts:
            return False, ("expected exactly the earlier-today, later-today and 47h-ahead "
                            "entries, got start_at values %r" % (kept_starts,))
        if kept_starts != sorted(kept_starts):
            return False, "select_window_entries() did not return entries sorted ascending by start_at"
        return True, ""
    check("select_window_entries() keeps an already-landed-earlier-today entry, a later-today entry and a 47h-ahead entry, drops one ended yesterday and one 49h ahead, sorted ascending, without mutating its input", _rolling_window_keeps_and_drops_the_expected_entries)

    # 25. select_window_entries() excludes a 19th-century junk timestamp
    #     for any plausible present-day now.
    def _rolling_window_excludes_nineteenth_century_junk():
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        junk_start = datetime(1899, 12, 30, tzinfo=timezone.utc).timestamp()
        junk_entry = _entry("XX", "AAA", "ORY", junk_start, junk_start + 3600)
        kept = cr.select_window_entries([junk_entry], now)
        if kept != []:
            return False, "expected the 19th-century entry to be excluded, got %r" % (kept,)
        return True, ""
    check("select_window_entries() excludes an entry carrying a 19th-century timestamp for a present-day now", _rolling_window_excludes_nineteenth_century_junk)

    # 26. A file holding more than CALENDAR_MAX_ENTRIES well-formed
    #     entries loads capped, with a drop-count warning captured from
    #     stderr.
    def _load_caps_at_max_entries_with_a_warning():
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
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
                loaded = cr.load_calendar_registry(tmp)
            finally:
                sys.stderr = old_stderr
            if len(loaded["entries"]) != cr.CALENDAR_MAX_ENTRIES:
                return False, "expected exactly CALENDAR_MAX_ENTRIES entries, got %d" % (len(loaded["entries"]),)
            if "dropped" not in buf.getvalue():
                return False, "expected a drop-count warning on stderr, got %r" % (buf.getvalue(),)
        return True, ""
    check("load_calendar_registry() on a file holding more than CALENDAR_MAX_ENTRIES well-formed entries returns exactly CALENDAR_MAX_ENTRIES of them and prints a drop-count warning on stderr", _load_caps_at_max_entries_with_a_warning)

    # 27. Every hostile entry shape is dropped: a non-dict, a short dict,
    #     an over-long dict, a lowercase airport code, a three-character
    #     airline code, a string timestamp, a boolean timestamp, and an
    #     inverted time pair all load with zero survivors, raising
    #     nothing.
    def _load_drops_every_hostile_entry_shape():
        import json
        import tempfile
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
        with tempfile.TemporaryDirectory() as tmp:
            with open(cr.calendar_rules_path(tmp), "w") as fh:
                json.dump({"entries": hostile_entries, "last_attempt_at": None, "last_synced_at": None}, fh)
            loaded = cr.load_calendar_registry(tmp)
        if loaded["entries"] != []:
            return False, "expected zero survivors from eight hostile entry shapes, got %r" % (loaded["entries"],)
        return True, ""
    check("load_calendar_registry() drops every one of eight hostile entry shapes (non-dict, short, over-long, lowercase airport, 3-char airline, string timestamp, boolean timestamp, inverted time pair) and raises nothing", _load_drops_every_hostile_entry_shape)

    # 28. Non-JSON bytes, a JSON array, a JSON string, and a dict whose
    #     entries is an integer all load to the documented empty shape.
    def _load_degrades_to_empty_shape_for_hostile_files():
        import json
        import tempfile
        empty_shape = {"entries": [], "last_attempt_at": None, "last_synced_at": None}
        hostile_bodies = [
            "not json at all",
            json.dumps([1, 2, 3]),
            json.dumps("just a string"),
            json.dumps({"entries": 5}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_rules_path(tmp)
            for body in hostile_bodies:
                with open(path, "w") as fh:
                    fh.write(body)
                loaded = cr.load_calendar_registry(tmp)
                if loaded != empty_shape:
                    return False, "load_calendar_registry() on %r returned %r, expected the empty shape" % (body, loaded)
        return True, ""
    check("load_calendar_registry() degrades non-JSON bytes, a JSON array, a JSON string, and a dict whose entries is an integer all to the documented empty shape", _load_degrades_to_empty_shape_for_hostile_files)

    # 29. calendar_fetch_is_due() returns the exact expected verdict
    #     across seven cases: never fetched, just fetched, one second
    #     before the interval elapses, one second after, a future
    #     timestamp, a string, and a boolean.
    def _throttle_exact_verdicts():
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
                return False, ("calendar_fetch_is_due(%r, now) for case %r returned %r, "
                                "expected %r - a broken feed would be contacted on every "
                                "30-second cycle" % (last_attempt_at, label, actual, expected))
        return True, ""
    check("calendar_fetch_is_due() returns the exact expected verdict for never-fetched, just-fetched, one-second-before/-after the interval, a future timestamp, a string, and a boolean - a broken feed must never be contacted on every 30-second cycle", _throttle_exact_verdicts)

    # 30. The two persisted timestamps survive a round trip with their
    #     distinct types (a number and an ISO string), and
    #     calendar_fetch_is_due() consults only last_attempt_at: changing
    #     last_synced_at alone never changes its verdict, changing
    #     last_attempt_at alone does.
    def _two_timestamps_are_distinct_in_type_and_role():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cr.write_calendar_registry(tmp, [], 500.0, "2020-01-01T00:00:00+00:00")
            loaded = cr.load_calendar_registry(tmp)
            if not isinstance(loaded["last_attempt_at"], float):
                return False, "last_attempt_at did not survive the round trip as a float: %r" % (loaded,)
            if not isinstance(loaded["last_synced_at"], str):
                return False, "last_synced_at did not survive the round trip as a str: %r" % (loaded,)

            now = 100000.0
            due_before = cr.calendar_fetch_is_due(loaded["last_attempt_at"], now)

            # Change ONLY last_synced_at - the throttle's verdict must not move.
            cr.write_calendar_registry(tmp, [], loaded["last_attempt_at"], "2026-09-07T00:00:00+00:00")
            after_sync_change = cr.load_calendar_registry(tmp)
            due_after_sync_change = cr.calendar_fetch_is_due(after_sync_change["last_attempt_at"], now)
            if due_after_sync_change != due_before:
                return False, "calendar_fetch_is_due()'s verdict changed when only last_synced_at changed"

            # Change ONLY last_attempt_at (to `now` itself) - the verdict MUST move.
            cr.write_calendar_registry(tmp, [], now, "2026-09-07T00:00:00+00:00")
            after_attempt_change = cr.load_calendar_registry(tmp)
            due_after_attempt_change = cr.calendar_fetch_is_due(after_attempt_change["last_attempt_at"], now)
            if due_after_attempt_change is not False:
                return False, "expected calendar_fetch_is_due() to report not-due immediately after last_attempt_at was set to now"
            if due_before is not True:
                return False, "test setup failure: due_before should have been True (elapsed far exceeds the interval)"
        return True, ""
    check("the two persisted timestamps survive a round trip with distinct types (a number and an ISO string), and calendar_fetch_is_due() consults only last_attempt_at - changing last_synced_at alone never changes its verdict, changing last_attempt_at does", _two_timestamps_are_distinct_in_type_and_role)

    # 31. A distinctive token set in the calendar URL environment
    #     variable appears nowhere in the persisted file's bytes, nowhere
    #     in the loaded dict's JSON serialisation, and nowhere in
    #     anything the module printed to stderr during a round trip.
    def _secret_never_reaches_the_file_or_the_log():
        import json
        import tempfile
        token = "SEKRIT-TOKEN-CONTAINMENT-CHECK"
        old_value = os.environ.get(cr.CALENDAR_URL_ENV_VAR)
        os.environ[cr.CALENDAR_URL_ENV_VAR] = "https://example.invalid/feed.ics?token=%s" % token
        try:
            with tempfile.TemporaryDirectory() as tmp:
                oversized = [
                    _entry("XX", "AAA", "ORY", float(i), float(i) + 1)
                    for i in range(cr.CALENDAR_MAX_ENTRIES + 5)
                ]
                buf = io.StringIO()
                old_stderr = sys.stderr
                sys.stderr = buf
                try:
                    cr.write_calendar_registry(tmp, oversized, 1.0, "2026-09-07T00:00:00+00:00")
                    loaded = cr.load_calendar_registry(tmp)
                finally:
                    sys.stderr = old_stderr
                captured_stderr = buf.getvalue()
                with open(cr.calendar_rules_path(tmp)) as fh:
                    file_bytes = fh.read()
                serialised = json.dumps(loaded)
                if token in file_bytes:
                    return False, "the calendar URL token leaked into calendar_rules.json"
                if token in serialised:
                    return False, "the calendar URL token leaked into the loaded dict's serialisation"
                if token in captured_stderr:
                    return False, "the calendar URL token leaked into stderr"
            return True, ""
        finally:
            if old_value is None:
                os.environ.pop(cr.CALENDAR_URL_ENV_VAR, None)
            else:
                os.environ[cr.CALENDAR_URL_ENV_VAR] = old_value
    check("a distinctive token set in the calendar URL environment variable appears in neither calendar_rules.json's bytes, the loaded dict's serialisation, nor anything printed to stderr during a round trip", _secret_never_reaches_the_file_or_the_log)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("calendar_rules: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
