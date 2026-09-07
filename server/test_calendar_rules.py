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

# Initial value for this file, introduced by phase 16 plan 01. Re-derived
# by RUNNING the harness (not by arithmetic), per this repo's own
# documented discipline (see server/test_colour_rules.py's own
# EXPECTED_CHECK_COUNT comment). Later plans in this phase raise it as
# they add checks.
EXPECTED_CHECK_COUNT = 20


def load_fixture_text(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return fh.read()


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

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("calendar_rules: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
