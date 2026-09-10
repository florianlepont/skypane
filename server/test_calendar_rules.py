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
import json
import os
import re
import socket
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
# Phase 16 plan 04 raised it to 55, adding the fetch-hardening,
# secret-leak-containment and refresh-orchestration checks below. Phase 16
# plan 06 raised it to 74, adding match_calendar_theme()'s truth table,
# direction-symmetry, runtime-derived-airline, route-shape-narrowing,
# fixture-driven ambiguity and never-raises checks. Quick task 260908-asr
# (T-16-PRIV) raised it to 80, adding the on-disk-retention-across-failing-
# cycles regression check the original goal verification missed, plus three
# anti-drift checks covering the loader's on-read window, the writer's
# refusal to persist what the loader would drop, and a behavioural
# equivalence guard against a second window implementation ever appearing.
# Phase 17 plan 01 raised it to 94, adding 14 checks for save_calendar_url()'s
# 0600 writer (T-17-MODE - os.open()'s own mode argument at creation time, a
# never-calls-os.chmod() check, both umasks, the pre-existing-destination
# case), calendar_secret_mode_is_unsafe()'s guard including its negative check
# (T-17-DRIFT) and absent-file case, and the registry-erase-on-every-change
# behaviour (D-04/D-05) plus the rejected-value, stripped-content,
# no-leftover-tmp-file and sentinel-identity checks.
# Phase 17 plan 02 raised it to 101, rewriting every environment-mutating
# fixture (38 references) to write the secret file via the shared
# _write_calendar_secret() helper instead, and adding 7 checks for the
# read-path swap: the value comes from the file, the retired environment
# read is provably inert (D-03), a drifted file refuses without ever being
# opened (D-02/T-17-DRIFT), a file written through the ordinary
# umask-inheriting idiom is refused end to end, the bool contract holds by
# identity across all three states (D-08), a hand-written trailing newline
# is stripped on read, and min_interval_s bypasses the throttle while the
# default preserves it (D-06).
# 17-REVIEW.md CR-02 fix (2026-09-10) raised it to 102, adding a regression
# for save_calendar_url(CLEAR_CALENDAR_URL): it must return False, not True,
# when os.remove() fails for a reason other than the file already being
# absent.
# 17-REVIEW.md CR-01 fix (2026-09-10) raised it to 103, adding a two-thread
# regression proving the new cross-process registry lock closes the race
# between a companion disconnect and a concurrent, simulated poll-cycle
# refresh (skypane-poll.service versus skypane-companion.service).
# 17-REVIEW.md WR-01 fix (2026-09-10) raised it to 104, adding a regression
# proving that replacing a connected calendar's URL leaves that calendar's
# already-fetched flights untouched when the new secret's write fails
# before ever reaching the registry erase.
# 17-REVIEW.md UAT fix (2026-09-10) raised it to 110, adding six checks for
# the webcal:// scheme defect (Apple Calendar's own share-link scheme was
# refused outright): _normalise_calendar_url()'s own rewrite-only-webcal
# contract, fetch_ics() accepting a webcal:// URL and the transport
# observing an https:// request, three address-gate non-weakening cases
# (private, loopback/"localhost", cloud metadata) still refused through a
# webcal:// URL, http:// still refused (no downgrade path), a redirect
# discovered from a normalised webcal:// URL still re-validated per hop,
# and save_calendar_url() storing the normalised https:// form rather than
# the raw webcal:// string.
# 17-REVIEW.md UAT-02 fix (2026-09-10) raised it to 113, adding three checks
# for the cap-before-window BLOCKER a real Apple Calendar feed exposed:
# parse_ics_events() + select_window_entries() still surfacing a small
# number of in-window entries from a feed listing more than
# CALENDAR_MAX_ENTRIES history entries first (the exact real-world failure,
# reproduced in a fixture), the same regression at the
# load_calendar_registry()/_rebuild_capped_entries() registry layer, and
# _resolve_retention_now()'s UF-16-05 closure - None, a bool, a non-numeric
# value, NaN/+-Infinity, and a finite-but-absurd 1e300 all now resolve to a
# real convertible clock rather than erasing a populated registry. One
# pre-existing check (parse_ics_events()'s own bound) was renamed and
# re-targeted at the new, much larger CALENDAR_MAX_RAW_EXAMINED ceiling
# rather than removed, so it is not counted as one of the three additions.
EXPECTED_CHECK_COUNT = 113

# A real public unicast IPv4 address (no DNS lookup needed - urlparse()
# already sees a literal IP as the hostname, and socket.getaddrinfo()
# resolves a dotted-decimal literal without ever touching the network).
# Only its RANGE classification matters to _address_is_public() here, not
# whether anything is actually listening on it - this is never actually
# connected to, since every check below injects its own fake transport.
PUBLIC_IP = "93.184.216.34"


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


def _mid_fixture_now():
    """A fixed `now` timestamp (plan 16-04) that places every one of the
    committed fixture's four valid events inside select_window_entries()'s
    window - today's UTC day-start through +48h. All four fixture events
    are on 2026-09-01, the earliest starting at 05:00Z and the latest
    ending at 15:25Z; 06:00Z that same day sits after the day-start edge
    and comfortably before the +48h forward edge for all of them.
    """
    from datetime import datetime, timezone
    return datetime(2026, 9, 1, 6, 0, 0, tzinfo=timezone.utc).timestamp()


class _FakeCalendarResponse:
    """A hermetic stand-in for `requests.Response`, built from fixed fields
    rather than a live call, in `server/test_enrich.py`'s `make_transport()`
    shape - so no check in the plan 16-04 group below ever makes a real
    network call.
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
    """The single fixture path for "this test has a calendar configured"
    (phase 17 plan 02, D-03), mirroring how the checks above already seed
    calendar_rules.json directly via write_calendar_registry() rather than
    going through a public write API for setup.

    Calls the real cr.save_calendar_url(state_dir, url) and asserts the
    return is True, so a fixture that silently fails to configure the
    calendar fails loudly here rather than producing a mystifying
    downstream FAIL several lines away. Replaces every environment-variable
    save/set/restore dance this file used before the secret moved to a
    per-test temporary state directory - there is no process-global state
    left to leak between tests, so there is nothing to restore either.
    """
    import server.plane.calendar_rules as cr
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
    #     than CALENDAR_MAX_RAW_EXAMINED returns exactly
    #     CALENDAR_MAX_RAW_EXAMINED entries - UAT-02's fix moved
    #     parse_ics_events()'s own bound off the SMALLER CALENDAR_MAX_ENTRIES
    #     (which used to discard every future flight in a real feed listing
    #     history first - see check 19b below) onto this much larger,
    #     DoS-only ceiling; CALENDAR_MAX_ENTRIES itself is enforced
    #     downstream by select_window_entries(), after the window, never
    #     here.
    def _bounded_output_at_max_raw_examined():
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
            return False, "expected exactly %d entries, got %d" % (cr.CALENDAR_MAX_RAW_EXAMINED, len(entries))
        return True, ""
    check("parse_ics_events() on a body with more VEVENT blocks than CALENDAR_MAX_RAW_EXAMINED returns exactly CALENDAR_MAX_RAW_EXAMINED entries", _bounded_output_at_max_raw_examined)

    # 19b. UAT-02's decisive regression, reproduced at the parse_ics_events()
    #      + select_window_entries() layer exactly as it happens in
    #      refresh_calendar_registry(): a feed listing more than
    #      CALENDAR_MAX_ENTRIES historical VEVENTs BEFORE a handful of
    #      in-window ones must still surface the in-window ones. Before
    #      UAT-02's fix, parse_ics_events() itself capped at
    #      CALENDAR_MAX_ENTRIES in raw feed order, so the surviving 200 were
    #      always the oldest 200 and select_window_entries() then had
    #      nothing future left to keep - reproducing "0 of 8 survive" against
    #      the developer's own real feed. This is the exact real-world
    #      failure, reproduced in a fixture.
    def _feed_history_before_window_still_surfaces_window_entries():
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
            return False, (
                "expected all %d in-window future entries to survive a feed listing "
                "%d historical entries first, got %d survivors (windowed total %d)"
                % (future_count, history_count, len(future_survivors), len(windowed))
            )
        return True, ""
    check(
        "UAT-02: a feed listing more than CALENDAR_MAX_ENTRIES historical VEVENTs before a "
        "small number of in-window ones still surfaces every in-window entry through "
        "parse_ics_events() + select_window_entries() - the exact real-world failure reproduced",
        _feed_history_before_window_still_surfaces_window_entries)

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
        # This check's subject is whole-file replacement vs. merge, not
        # retention - a fixed `now` bracketing both sentinel entry lists
        # (epoch 1-6) keeps them in-window without touching the fixtures
        # themselves.
        now = 6.0
        with tempfile.TemporaryDirectory() as tmp:
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
                return False, ("expected only entries_b's entry to survive (no merge with "
                                "entries_a), got %r" % (origins,))
        return True, ""
    check("write_calendar_registry() replaces the whole file - a shorter second write leaves only that list, never a merge with the earlier one", _d03_whole_file_rewrite_never_merges)

    # 23. A successful fetch that legitimately returns nothing empties the
    #     window rather than leaving yesterday's flights behind, and both
    #     timestamps are still readable afterwards.
    def _d03_empty_write_empties_the_window():
        import tempfile
        # An explicit `now` bracketing the sentinel entry (epoch 1-2) so the
        # first write is genuinely in-window - otherwise the window would
        # already have emptied it before the empty-write step ever ran,
        # making this check's own assertion vacuous.
        now = 2.0
        with tempfile.TemporaryDirectory() as tmp:
            cr.write_calendar_registry(
                tmp, [_entry("XX", "AAA", "ORY", 1.0, 2.0)], 100.0, "2026-09-07T00:00:00+00:00",
                now=now)
            seeded = cr.load_calendar_registry(tmp, now)
            if seeded["entries"] == []:
                return False, "test setup failure: the seeded entry should be in-window, got []"
            cr.write_calendar_registry(tmp, [], 200.0, "2026-09-07T01:00:00+00:00", now=now)
            loaded = cr.load_calendar_registry(tmp, now)
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

    # 26. A file holding more than CALENDAR_MAX_ENTRIES well-formed,
    #     ALL-IN-WINDOW entries loads capped, with a drop-count warning
    #     captured from stderr - the cap is still fully enforced after
    #     UAT-02's window-first reorder, it just now bounds the windowed
    #     survivors rather than raw file order (see check 26b below for the
    #     order-sensitive regression that pins the reorder itself).
    def _load_caps_at_max_entries_with_a_warning():
        import json
        import tempfile
        # An explicit `now` bracketing the whole 0..CALENDAR_MAX_ENTRIES+49
        # sentinel range so every one of these entries is in-window
        # regardless of order - this check's subject is the cap, not the
        # reorder.
        now = float(cr.CALENDAR_MAX_ENTRIES + 49)
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
                loaded = cr.load_calendar_registry(tmp, now)
            finally:
                sys.stderr = old_stderr
            if len(loaded["entries"]) != cr.CALENDAR_MAX_ENTRIES:
                return False, "expected exactly CALENDAR_MAX_ENTRIES entries, got %d" % (len(loaded["entries"]),)
            if "dropped" not in buf.getvalue():
                return False, "expected a drop-count warning on stderr, got %r" % (buf.getvalue(),)
        return True, ""
    check("load_calendar_registry() on a file holding more than CALENDAR_MAX_ENTRIES well-formed entries returns exactly CALENDAR_MAX_ENTRIES of them and prints a drop-count warning on stderr", _load_caps_at_max_entries_with_a_warning)

    # 26b. UAT-02's decisive regression at the registry layer: a hand-edited
    #      (or pre-fix-written) calendar_rules.json listing more than
    #      CALENDAR_MAX_ENTRIES entries OUTSIDE the window before a small
    #      number INSIDE it must still surface the in-window ones on load.
    #      Before the fix, _rebuild_capped_entries() capped raw_entries in
    #      LIST ORDER before ever windowing, so the historical entries
    #      (listed first) filled the cap and the in-window entries (listed
    #      last) were discarded before select_window_entries() ever ran -
    #      reproducing exactly the developer's real-feed failure
    #      ("0 of 8 survive"). Without the fix this returns zero.
    def _registry_history_before_window_still_surfaces_window_entries():
        import json
        import tempfile
        now = _mid_fixture_now()
        history_count = cr.CALENDAR_MAX_ENTRIES + 50
        future_count = 8
        raw_entries = (
            [_entry("XX", "AAA", "ORY", float(i), float(i) + 1) for i in range(history_count)]
            + [_entry("BA", "CDG", "ORY", now + i * 60, now + i * 60 + 60) for i in range(future_count)]
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(cr.calendar_rules_path(tmp), "w") as fh:
                json.dump({"entries": raw_entries, "last_attempt_at": None, "last_synced_at": None}, fh)
            loaded = cr.load_calendar_registry(tmp, now)
            future_survivors = [e for e in loaded["entries"] if e["airline_iata"] == "BA"]
            if len(future_survivors) != future_count:
                return False, (
                    "expected all %d in-window entries to survive a raw list holding %d "
                    "out-of-window entries first, got %d survivors (total %d)"
                    % (future_count, history_count, len(future_survivors), len(loaded["entries"]))
                )
        return True, ""
    check(
        "UAT-02: load_calendar_registry() on a raw entries list holding more than CALENDAR_MAX_ENTRIES "
        "out-of-window entries before a small number of in-window ones still surfaces every in-window "
        "entry - the exact real-world failure reproduced at the registry layer",
        _registry_history_before_window_still_surfaces_window_entries)

    # 26c. _resolve_retention_now()'s guard, including UF-16-05's closure:
    #      None, a bool, a non-numeric value, NaN, +-Infinity, AND a finite
    #      but absurd value (1e300, which overflows datetime.fromtimestamp()
    #      despite being entirely finite) must all resolve to a real,
    #      convertible clock rather than reaching select_window_entries()
    #      as-is and erasing a populated registry.
    def _resolve_retention_now_never_erases_a_populated_registry():
        import tempfile
        import time
        # The genuine wall clock, not the fixture's fixed 2026-09-01 `now` -
        # every bad value below is expected to resolve to time.time(), so
        # the seeded entry must actually be in-window relative to REAL
        # current time for that resolution to be provably correct.
        real_now = time.time()
        seeded = [_entry("BA", "CDG", "ORY", real_now, real_now + 60)]
        bad_values = (None, True, False, "not-a-number", float("nan"),
                      float("inf"), float("-inf"), 1e300, -1e300)
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.write_calendar_registry(tmp, seeded, real_now, None, now=real_now):
                return False, "test fixture failure: write_calendar_registry() returned False"
            for bad in bad_values:
                loaded = cr.load_calendar_registry(tmp, bad)
                if len(loaded["entries"]) != 1:
                    return False, (
                        "_resolve_retention_now(%r) let an absurd now erase a populated "
                        "registry - expected 1 surviving entry, got %d"
                        % (bad, len(loaded["entries"]))
                    )
        return True, ""
    check(
        "UF-16-05 closure: _resolve_retention_now() resolves None, a bool, a non-numeric value, "
        "NaN/+-Infinity, and a finite-but-absurd value (1e300) all to a real convertible clock, "
        "so none of them can erase a populated registry through load_calendar_registry()",
        _resolve_retention_now_never_erases_a_populated_registry)

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

    # 31. A distinctive token set in the calendar secret file appears
    #     nowhere in the persisted registry file's bytes, nowhere in the
    #     loaded dict's JSON serialisation, and nowhere in anything the
    #     module printed to stderr during a round trip.
    def _secret_never_reaches_the_file_or_the_log():
        import json
        import tempfile
        token = "SEKRIT-TOKEN-CONTAINMENT-CHECK"
        with tempfile.TemporaryDirectory() as tmp:
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
                return False, "the calendar URL token leaked into calendar_rules.json"
            if token in serialised:
                return False, "the calendar URL token leaked into the loaded dict's serialisation"
            if token in captured_stderr:
                return False, "the calendar URL token leaked into stderr"
        return True, ""
    check("a distinctive token set in the calendar secret file appears in neither calendar_rules.json's bytes, the loaded dict's serialisation, nor anything printed to stderr during a round trip", _secret_never_reaches_the_file_or_the_log)

    # --- Phase 16 plan 04: fetch-hardening, secret-leak-containment and
    #     refresh-orchestration checks, added below the plan 16-03 checks
    #     above. No check below ever makes a live network call - IP
    #     literals resolve locally without DNS, and every hostname-based
    #     scenario monkeypatches socket.getaddrinfo, restored in a
    #     finally exactly like test_colour_rules.py does for its own
    #     process-global cache. ---

    # 32. A non-https scheme is refused, for four distinct shapes.
    def _scheme_gate_refuses_non_https():
        for bad in ("http://%s/a.ics" % PUBLIC_IP, "ftp://%s/a.ics" % PUBLIC_IP,
                    "file:///etc/passwd", "not-a-url"):
            if cr._url_is_safe(bad) is not False:
                return False, "expected _url_is_safe(%r) to be False" % (bad,)
        return True, ""
    check("_url_is_safe() refuses a non-https scheme (http, ftp, file, and a schemeless string)", _scheme_gate_refuses_non_https)

    # 33. A URL with no hostname at all is refused.
    def _no_hostname_refused():
        if cr._url_is_safe("https:///a.ics") is not False:
            return False, "expected a hostless https URL to be refused"
        return True, ""
    check("_url_is_safe() refuses a URL with no hostname", _no_hostname_refused)

    # 34. Loopback (v4 and v6), three private ranges, the link-local
    #     metadata address, and a reserved address are all refused - none
    #     of these require a DNS lookup, since urlparse() already sees a
    #     literal IP as the hostname.
    def _address_gate_refuses_every_unsafe_range():
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
                return False, "expected _url_is_safe(%r) to be False" % (url,)
        return True, ""
    check("_url_is_safe() refuses loopback (v4/v6), three private ranges, the link-local metadata address, and a reserved address", _address_gate_refuses_every_unsafe_range)

    # 35. A hostname that fails to resolve at all is refused - ".invalid"
    #     is reserved by RFC 2606 to always fail to resolve, so this needs
    #     no monkeypatch.
    def _unresolvable_hostname_refused():
        if cr._url_is_safe("https://this-genuinely-does-not-resolve.invalid/a.ics") is not False:
            return False, "expected an unresolvable hostname to be refused"
        return True, ""
    check("_url_is_safe() refuses a hostname that fails to resolve at all", _unresolvable_hostname_refused)

    # 36. DNS-rebinding headline proof: a hostname that resolves to a MIX
    #     of one public and one private address is refused, not accepted
    #     on the strength of the public one - a hostname-only
    #     implementation would pass this hostname on the strength of its
    #     *string* alone and never notice the private answer.
    def _mixed_address_answer_refused():
        real_getaddrinfo = socket.getaddrinfo
        try:
            socket.getaddrinfo = lambda host, port=None, *a, **k: [
                (2, 1, 6, "", (PUBLIC_IP, 443)),
                (2, 1, 6, "", ("10.1.2.3", 443)),
            ]
            if cr._url_is_safe("https://public-looking-name.example/a.ics") is not False:
                return False, "a hostname resolving to one private address among public ones must be refused"
        finally:
            socket.getaddrinfo = real_getaddrinfo
        return True, ""
    check("_url_is_safe() refuses a hostname whose resolved addresses are a MIX of public and private - the DNS-rebinding case a hostname-only check would miss", _mixed_address_answer_refused)

    # 37. The same hostname, monkeypatched to resolve to only public
    #     addresses, is accepted - proving check 36 isn't vacuously always
    #     False.
    def _all_public_answer_accepted():
        real_getaddrinfo = socket.getaddrinfo
        try:
            socket.getaddrinfo = lambda host, port=None, *a, **k: [
                (2, 1, 6, "", (PUBLIC_IP, 443)),
            ]
            if cr._url_is_safe("https://public-looking-name.example/a.ics") is not True:
                return False, "a hostname resolving to only public addresses should be accepted"
        finally:
            socket.getaddrinfo = real_getaddrinfo
        return True, ""
    check("_url_is_safe() accepts the same hostname when every resolved address is public", _all_public_answer_accepted)

    # 38. A redirect Location pointing at a loopback address is refused -
    #     proving the gate is re-applied per hop, not only to the
    #     configured URL.
    def _redirect_to_loopback_refused():
        calls = []
        transport = make_calendar_transport(
            status_code=302, headers={"Location": "https://127.0.0.1/a.ics"},
            is_redirect=True, calls=calls)
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None when a redirect targets a loopback address"
        if calls != ["https://%s/a.ics" % PUBLIC_IP]:
            return False, "expected exactly one transport call (the redirect target must never be fetched): %r" % (calls,)
        return True, ""
    check("fetch_ics() refuses a redirect whose Location targets a loopback address, without ever fetching it", _redirect_to_loopback_refused)

    # 39. A redirect response with no Location header returns nothing.
    def _redirect_without_location_returns_none():
        transport = make_calendar_transport(status_code=302, headers={}, is_redirect=True)
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None for a redirect with no Location header"
        return True, ""
    check("fetch_ics() returns nothing for a redirect response with no Location header", _redirect_without_location_returns_none)

    # 40. A relative Location is resolved against the current URL and then
    #     re-validated (accepted here, since the resolved target stays
    #     within the same safe host).
    def _relative_redirect_resolved_and_refetched():
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
            return False, "expected the relative redirect to be followed to its resolved target, got %r" % (result,)
        if calls != ["https://%s/a.ics" % PUBLIC_IP, "https://%s/moved.ics" % PUBLIC_IP]:
            return False, "expected the relative Location resolved against the current URL: %r" % (calls,)
        return True, ""
    check("fetch_ics() resolves a relative Location against the current URL and re-validates it before following it", _relative_redirect_resolved_and_refetched)

    # 41. A redirect chain longer than CALENDAR_MAX_REDIRECTS returns
    #     nothing, counted by the fake's own invocation count.
    def _redirect_chain_bounded():
        calls = []
        transport = make_calendar_transport(
            status_code=302, headers={"Location": "https://%s/next.ics" % PUBLIC_IP},
            is_redirect=True, calls=calls)
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None for a redirect chain longer than CALENDAR_MAX_REDIRECTS"
        if len(calls) != cr.CALENDAR_MAX_REDIRECTS + 1:
            return False, "expected exactly CALENDAR_MAX_REDIRECTS + 1 transport calls, got %d" % (len(calls),)
        return True, ""
    check("fetch_ics() gives up after CALENDAR_MAX_REDIRECTS + 1 transport calls rather than looping forever", _redirect_chain_bounded)

    # 42. A body one byte over CALENDAR_MAX_RESPONSE_BYTES returns nothing.
    def _oversized_body_refused():
        body = b"x" * (cr.CALENDAR_MAX_RESPONSE_BYTES + 1)
        transport = make_calendar_transport(status_code=200, body=body)
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None for a body one byte over the cap"
        return True, ""
    check("fetch_ics() refuses a body one byte over CALENDAR_MAX_RESPONSE_BYTES", _oversized_body_refused)

    # 43. The same oversized body, declaring a Content-Length of 1, is
    #     still refused - the cap is on what was streamed, not on what
    #     was claimed.
    def _oversized_body_with_lying_content_length_refused():
        body = b"x" * (cr.CALENDAR_MAX_RESPONSE_BYTES + 1)
        transport = make_calendar_transport(status_code=200, body=body, headers={"Content-Length": "1"})
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None even though the declared Content-Length was only 1 byte"
        return True, ""
    check("fetch_ics() refuses an oversized body even when it declares a Content-Length of 1 - the cap is on streamed bytes, never the declared length", _oversized_body_with_lying_content_length_refused)

    # 44. A body exactly at the cap is accepted.
    def _body_exactly_at_cap_accepted():
        body = b"x" * cr.CALENDAR_MAX_RESPONSE_BYTES
        transport = make_calendar_transport(status_code=200, body=body)
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result != body.decode("utf-8"):
            return False, "expected a body exactly at CALENDAR_MAX_RESPONSE_BYTES to be accepted"
        return True, ""
    check("fetch_ics() accepts a body exactly at CALENDAR_MAX_RESPONSE_BYTES", _body_exactly_at_cap_accepted)

    # 45. A non-200 final status returns nothing.
    def _non_200_status_refused():
        transport = make_calendar_transport(status_code=500, body=b"error")
        result = cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None for a non-200 final status"
        return True, ""
    check("fetch_ics() returns nothing for a non-200 final status", _non_200_status_refused)

    # 46. The transport is invoked with a timeout argument equal to
    #     CALENDAR_FETCH_TIMEOUT_S when none is supplied.
    def _default_timeout_passed_to_transport():
        timeouts = []
        transport = make_calendar_transport(status_code=200, body=b"ok", timeouts=timeouts)
        cr.fetch_ics("https://%s/a.ics" % PUBLIC_IP, transport=transport)
        if timeouts != [cr.CALENDAR_FETCH_TIMEOUT_S]:
            return False, "expected the transport's timeout argument to be CALENDAR_FETCH_TIMEOUT_S, got %r" % (timeouts,)
        return True, ""
    check("fetch_ics() invokes the transport with CALENDAR_FETCH_TIMEOUT_S as the timeout argument by default", _default_timeout_passed_to_transport)

    # 47. Secret containment - the group this plan exists for. A
    #     distinctive token, hostname, path and query-parameter name set
    #     in the calendar URL environment variable must appear in none of
    #     the seven distinct failure paths' captured stderr, including a
    #     transport exception whose message IS the full secret URL - the
    #     exact shape several requests.exceptions.* subclasses take by
    #     default.
    def _secret_never_reaches_stderr_across_seven_failure_paths():
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

        socket.getaddrinfo = fake_getaddrinfo
        try:
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
                old_stderr = sys.stderr
                sys.stderr = buf
                try:
                    result = run()
                finally:
                    sys.stderr = old_stderr
                if result is not None:
                    return False, "scenario %r unexpectedly succeeded: %r" % (label, result)
                captured = buf.getvalue()
                for leak in forbidden:
                    if leak in captured:
                        return False, "scenario %r leaked %r into stderr: %r" % (label, leak, captured)
            return True, ""
        finally:
            socket.getaddrinfo = real_getaddrinfo
    check("across seven distinct fetch_ics() failure paths - including a transport exception whose message is the full secret URL - neither the token, the host, the path, nor the query-parameter name reaches stderr", _secret_never_reaches_stderr_across_seven_failure_paths)

    # 48. The same four substrings are absent from the persisted
    #     calendar_rules.json after a full successful
    #     refresh_calendar_registry() cycle.
    def _secret_absent_from_persisted_registry_after_success():
        import tempfile
        real_getaddrinfo = socket.getaddrinfo
        token = "SEKRIT-REGISTRY-CONTAINMENT"
        host = "calendar-secret-registry-test.invalid"
        secret_url = "https://%s/private-roster.ics?token=%s" % (host, token)
        forbidden = (token, host, "private-roster.ics", "token=")
        fixture_text = load_fixture_text(FIXTURE_ICS)

        def fake_getaddrinfo(hostname, port=None, *a, **k):
            if hostname == host:
                return [(2, 1, 6, "", (PUBLIC_IP, 443))]
            return real_getaddrinfo(hostname, port, *a, **k)

        socket.getaddrinfo = fake_getaddrinfo
        try:
            now = _mid_fixture_now()
            with tempfile.TemporaryDirectory() as tmp:
                _write_calendar_secret(tmp, secret_url)
                transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
                code, _reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
                if code != cr.FETCH_OK:
                    return False, "test setup failure: expected FETCH_OK, got %r" % (code,)
                with open(cr.calendar_rules_path(tmp)) as fh:
                    file_bytes = fh.read()
                for leak in forbidden:
                    if leak in file_bytes:
                        return False, "the persisted registry leaked %r" % (leak,)
            return True, ""
        finally:
            socket.getaddrinfo = real_getaddrinfo
    check("neither the calendar URL's token, host, path, nor query-parameter name appears in calendar_rules.json after a full successful refresh_calendar_registry() cycle", _secret_absent_from_persisted_registry_after_success)

    # 49. The unconfigured path performs no transport call and writes no
    #     timestamp.
    def _refresh_unconfigured_makes_no_call_and_writes_nothing():
        import tempfile
        # No secret file is written - a fresh temporary state dir is
        # "unconfigured" by construction, with nothing to arrange or
        # restore (D-03).
        calls = []
        transport = make_calendar_transport(status_code=200, body=b"unused", calls=calls)
        with tempfile.TemporaryDirectory() as tmp:
            code, reg = cr.refresh_calendar_registry(tmp, 1000.0, transport=transport)
            if code != cr.FETCH_SKIPPED_UNCONFIGURED:
                return False, "expected FETCH_SKIPPED_UNCONFIGURED, got %r" % (code,)
            if calls:
                return False, "expected no transport call when unconfigured, got %r" % (calls,)
            if reg["last_attempt_at"] is not None:
                return False, "expected last_attempt_at to stay None when unconfigured, got %r" % (reg,)
        return True, ""
    check("refresh_calendar_registry() makes no transport call and writes no last_attempt_at when the feature is unconfigured", _refresh_unconfigured_makes_no_call_and_writes_nothing)

    # 50. The throttled path performs no transport call and prints
    #     nothing, across twenty throttled cycles.
    def _refresh_throttled_path_is_silent():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
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
                        return False, "expected FETCH_SKIPPED_THROTTLED at cycle %d, got %r" % (i, code)
            finally:
                sys.stderr = old_stderr
            if calls:
                return False, "expected no transport call while throttled, got %r" % (calls,)
            if buf.getvalue() != "":
                return False, "expected silent stderr on the throttled path, got %r" % (buf.getvalue(),)
        return True, ""
    check("refresh_calendar_registry() makes no transport call and prints nothing across twenty throttled cycles", _refresh_throttled_path_is_silent)

    # 51. Eleven calls across simulated 30-second cycles perform exactly
    #     one transport call - the throttle genuinely prevents a
    #     per-cycle fetch.
    def _refresh_throttle_holds_across_eleven_cycles():
        import tempfile
        calls = []
        transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR\nEND:VCALENDAR", calls=calls)
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            for i in range(11):
                cr.refresh_calendar_registry(tmp, 30.0 * i, transport=transport)
            if len(calls) != 1:
                return False, "expected exactly one transport call across eleven 30s-spaced cycles, got %d" % (len(calls),)
        return True, ""
    check("eleven refresh_calendar_registry() calls spaced 30 seconds apart perform exactly one transport call", _refresh_throttle_holds_across_eleven_cycles)

    # 52. A failure after a success moves last_attempt_at, leaves
    #     last_synced_at, and leaves the persisted entries unchanged.
    def _refresh_failure_after_success_preserves_the_window():
        import tempfile
        fixture_text = load_fixture_text(FIXTURE_ICS)
        now = _mid_fixture_now()
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            ok_transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
            code, reg = cr.refresh_calendar_registry(tmp, now, transport=ok_transport)
            if code != cr.FETCH_OK or not reg["entries"]:
                return False, "test setup failure: expected a successful fetch with entries, got %r" % ((code, reg),)
            synced_at = reg["last_synced_at"]
            entries_before = list(reg["entries"])

            later = now + cr.CALENDAR_FETCH_INTERVAL_S + 1
            failing_transport = make_calendar_transport(status_code=500)
            code2, reg2 = cr.refresh_calendar_registry(tmp, later, transport=failing_transport)
            if code2 != cr.FETCH_FAILED:
                return False, "expected FETCH_FAILED, got %r" % (code2,)
            if reg2["last_attempt_at"] != later:
                return False, "expected last_attempt_at to move to %r, got %r" % (later, reg2)
            if reg2["last_synced_at"] != synced_at:
                return False, "expected last_synced_at to stay at %r, got %r" % (synced_at, reg2["last_synced_at"])
            # Load with the same `later` clock the failed refresh cycle
            # itself used, so this check's own read is not silently
            # re-windowed against the wall clock instead of the cycle
            # under test.
            on_disk = cr.load_calendar_registry(tmp, later)
            if on_disk["entries"] != entries_before:
                return False, "a failed fetch changed the persisted entries"
        return True, ""
    check("a failed refresh_calendar_registry() after a success moves last_attempt_at, leaves last_synced_at, and leaves the persisted entries unchanged", _refresh_failure_after_success_preserves_the_window)

    # 53. A success writes a windowed parse of the committed fixture.
    def _refresh_success_writes_the_fixtures_windowed_parse():
        import tempfile
        fixture_text = load_fixture_text(FIXTURE_ICS)
        now = _mid_fixture_now()
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            transport = make_calendar_transport(status_code=200, body=fixture_text.encode())
            code, reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
            if code != cr.FETCH_OK:
                return False, "expected FETCH_OK, got %r" % (code,)
            if len(reg["entries"]) != FIXTURE_EXPECTED_ENTRIES:
                return False, "expected %d windowed entries from the fixture, got %d: %r" % (
                    FIXTURE_EXPECTED_ENTRIES, len(reg["entries"]), reg["entries"])
            # Load with the same `now` this refresh cycle used, so this
            # check's own read is not silently re-windowed against the
            # wall clock instead of the cycle under test.
            on_disk = cr.load_calendar_registry(tmp, now)
            if on_disk["entries"] != reg["entries"]:
                return False, "the persisted entries did not match the returned registry"
        return True, ""
    check("a successful refresh_calendar_registry() cycle writes a windowed parse of the committed fixture, matching what is then readable on disk", _refresh_success_writes_the_fixtures_windowed_parse)

    # 54. A successful fetch of a feed with nothing in the window is
    #     reported as success with an empty entry list, distinguishable
    #     from a failure only by last_synced_at having moved.
    def _empty_window_success_distinguished_only_by_last_synced_at():
        import tempfile
        empty_body = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        transport = make_calendar_transport(status_code=200, body=empty_body.encode())
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            code, reg = cr.refresh_calendar_registry(tmp, 5000.0, transport=transport)
            if code != cr.FETCH_OK:
                return False, "expected FETCH_OK even for a legitimately empty window, got %r" % (code,)
            if reg["entries"] != []:
                return False, "expected an empty entries list, got %r" % (reg["entries"],)
            if reg["last_synced_at"] is None:
                return False, "expected last_synced_at to have moved on a genuine success, got None"
        return True, ""
    check("a successful fetch of a feed with nothing in the window reports FETCH_OK with an empty entry list, distinguished from a failure only by last_synced_at having moved", _empty_window_success_distinguished_only_by_last_synced_at)

    # 55. refresh_calendar_registry() never raises: an unwritable state
    #     dir, a body of random punctuation, a transport that raises, and
    #     a transport that redirects forever, each return a result code
    #     rather than propagating.
    def _refresh_never_raises():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
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
                return False, "expected a result code (string) for an unwritable registry path, got %r" % (code,)

            punctuation_transport = make_calendar_transport(status_code=200, body="!!!@#$%^&*()<<<>>>".encode())
            code2, _reg2 = cr.refresh_calendar_registry(tmp, 5000.0, transport=punctuation_transport)
            if not isinstance(code2, str):
                return False, "expected a result code for a punctuation body, got %r" % (code2,)

            raising_transport = make_calendar_transport(raise_exc=Exception("simulated transport failure"))
            code3, _reg3 = cr.refresh_calendar_registry(tmp, 10000.0, transport=raising_transport)
            if not isinstance(code3, str):
                return False, "expected a result code for a raising transport, got %r" % (code3,)

            looping_transport = make_calendar_transport(
                status_code=302, is_redirect=True, headers={"Location": "https://%s/next.ics" % PUBLIC_IP})
            code4, _reg4 = cr.refresh_calendar_registry(tmp, 15000.0, transport=looping_transport)
            if not isinstance(code4, str):
                return False, "expected a result code for a redirect-looping transport, got %r" % (code4,)
        return True, ""
    check("refresh_calendar_registry() never raises - an unwritable registry path, a punctuation body, a raising transport, and a redirect-looping transport all return a result code", _refresh_never_raises)

    # --- Plan 16-06: match_calendar_theme() (D-04 / CORRECTION 1) -----------

    import server.device_config as device_config

    CAL_THEME = device_config.THEME_IDS[-1]
    CAL_CFG = {"theme": device_config.DEFAULT_THEME_ID, "calendar_theme_id": CAL_THEME}
    MATCH_NOW = 1789000000.0

    def _route(airline_name, origin_iata, destination_iata, callsign_iata):
        """A route dict in `enrich._parse_route()`'s exact six-key shape,
        for the matcher checks below.
        """
        return {
            "airline_name": airline_name,
            "origin_iata": origin_iata,
            "origin_city": None,
            "destination_iata": destination_iata,
            "destination_city": None,
            "callsign_iata": callsign_iata,
        }

    # 56. The correct triple on a departure matches.
    def _match_truth_table_departure():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "XX1001")
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result != CAL_THEME:
            return False, "expected a departure match to return %r, got %r" % (CAL_THEME, result)
        return True, ""
    check("match_calendar_theme() matches a departing detection whose route destination, airline and time all agree with an entry", _match_truth_table_departure)

    # 57. The correct triple on an arrival matches.
    def _match_truth_table_arrival():
        entries = [_entry("XX", "BBB", "ORY", MATCH_NOW - 7200, MATCH_NOW)]
        route = _route("Some Airline", "BBB", "ORY", "XX2001")
        result = cr.match_calendar_theme({"entries": entries}, route, cr.ARRIVING_STATE, CAL_CFG, MATCH_NOW)
        if result != CAL_THEME:
            return False, "expected an arrival match to return %r, got %r" % (CAL_THEME, result)
        return True, ""
    check("match_calendar_theme() matches an arriving detection whose route origin, airline and time all agree with an entry", _match_truth_table_arrival)

    # 58. Same airline and time, a different far end - no match.
    def _match_truth_table_different_far_end():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "ZZZ", "XX1001")
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "expected no match with a different far-end airport, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() does not match when only the far-end airport differs", _match_truth_table_different_far_end)

    # 59. Same far end and time, a different airline - no match.
    def _match_truth_table_different_airline():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "YY1001")
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "expected no match with a different airline, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() does not match when only the airline differs", _match_truth_table_different_airline)

    # 60. Same airline and far end, time outside the tolerance - no match.
    def _match_truth_table_time_outside_tolerance():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "XX1001")
        outside = MATCH_NOW + cr.CALENDAR_MATCH_TOLERANCE_S + 1
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, outside)
        if result is not None:
            return False, "expected no match just outside the tolerance, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() does not match when the time is just outside CALENDAR_MATCH_TOLERANCE_S", _match_truth_table_time_outside_tolerance)

    # 61. Same airline and far end, time just inside the tolerance - matches.
    def _match_truth_table_time_inside_tolerance():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "XX1001")
        inside = MATCH_NOW + cr.CALENDAR_MATCH_TOLERANCE_S - 1
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, inside)
        if result != CAL_THEME:
            return False, "expected a match just inside the tolerance, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() matches when the time is just inside CALENDAR_MATCH_TOLERANCE_S", _match_truth_table_time_inside_tolerance)

    # 62. Direction symmetry: an arriving detection is never matched
    #     against an entry's DEPARTURE-side far end. Crafted so the
    #     documented mutation (make _entry_far_end_iata() return the
    #     destination for both states) would flip this to a match.
    def _direction_symmetry_arrival_rejects_departure_side_far_end():
        entries = [_entry("XX", "CCC", "DDD", MATCH_NOW, MATCH_NOW + 7200)]
        # route's origin equals the entry's DESTINATION ("DDD") - the wrong
        # field for an arrival, whose correct far end is the entry's ORIGIN.
        route = _route("Some Airline", "DDD", "ZZZ", "XX1234")
        result = cr.match_calendar_theme(
            {"entries": entries}, route, cr.ARRIVING_STATE, CAL_CFG, MATCH_NOW + 7200)
        if result is not None:
            return False, "expected no match: an arrival must compare against the entry's origin, not its destination, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() direction symmetry: an arriving detection is never matched against an entry's departure-side far end", _direction_symmetry_arrival_rejects_departure_side_far_end)

    # 63. Direction symmetry mirror: a departing detection is never
    #     matched against an entry's ARRIVAL-side far end.
    def _direction_symmetry_departure_rejects_arrival_side_far_end():
        entries = [_entry("XX", "EEE", "FFF", MATCH_NOW, MATCH_NOW + 7200)]
        # route's destination equals the entry's ORIGIN ("EEE") - the wrong
        # field for a departure, whose correct far end is the entry's
        # DESTINATION.
        route = _route("Some Airline", "GGG", "EEE", "XX5678")
        result = cr.match_calendar_theme(
            {"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "expected no match: a departure must compare against the entry's destination, not its origin, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() direction symmetry: a departing detection is never matched against an entry's arrival-side far end", _direction_symmetry_departure_rejects_arrival_side_far_end)

    # 64. The airline half is derived at runtime, not tabulated
    #     (CORRECTION 1): a two-letter designator this codebase's own
    #     static tables have never seen still matches. A failure here
    #     means someone reintroduced a static airline table.
    def _airline_derived_not_tabulated():
        entries = [_entry("ZQ", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("An Unheard-Of Airline", "ORY", "AAA", "ZQ9999")
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result != CAL_THEME:
            return False, "expected a match on a designator ('ZQ') no static table could contain, got %r - did someone reintroduce a static airline table?" % (result,)
        return True, ""
    check("match_calendar_theme() derives the airline from callsign_iata at runtime - a designator no static table could contain still matches (CORRECTION 1)", _airline_derived_not_tabulated)

    # 65. The production bug this narrowing prevents: an airline_only-shaped
    #     route (all three IATA fields None) never matches, however perfect
    #     the entries and time.
    def _airline_only_shaped_route_never_matches():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        airline_only_route = {
            "airline_name": "Some Airline", "origin_iata": None, "origin_city": None,
            "destination_iata": None, "destination_city": None, "callsign_iata": None,
        }
        result = cr.match_calendar_theme({"entries": entries}, airline_only_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "an airline_only-shaped route must never match, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() never matches an airline_only-shaped route (the production bug the field-presence test prevents)", _airline_only_shaped_route_never_matches)

    # 66. The same shape, a different provenance (a "manual" enrichment
    #     result) - assert both, since the point is that the SHAPE is what
    #     matters, not the source label.
    def _manual_shaped_route_never_matches():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        manual_route = {
            "airline_name": "Some Airline (manually resolved)", "origin_iata": None,
            "origin_city": None, "destination_iata": None, "destination_city": None,
            "callsign_iata": None,
        }
        result = cr.match_calendar_theme({"entries": entries}, manual_route, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "a manual-shaped route must never match, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() never matches a manual-shaped route - the same shape as airline_only, a different provenance", _manual_shaped_route_never_matches)

    # 67. The miss case: a None route never matches.
    def _none_route_never_matches():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        result = cr.match_calendar_theme({"entries": entries}, None, cr.DEPARTING_STATE, CAL_CFG, MATCH_NOW)
        if result is not None:
            return False, "a None route (a miss) must never match, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() never matches a None route (the miss case)", _none_route_never_matches)

    # 68-71. Ambiguity (16-VALIDATION matcher row 3), using the committed
    #        fixture's own same-route pair (XX2001/XX2002, both BBB-ORY
    #        arrivals roughly 8.5h apart) parsed through parse_ics_events()
    #        - never a hand-built pair.
    fixture_entries = cr.parse_ics_events(load_fixture_text(FIXTURE_ICS))
    bbb_ory_entries = [
        e for e in fixture_entries
        if e["origin_iata"] == "BBB" and e["destination_iata"] == "ORY"
    ]
    if len(bbb_ory_entries) != 2:
        check("FIXTURE_ICS setup: exactly two BBB-ORY entries exist for the ambiguity checks", lambda: (False, "expected 2, found %d: %r" % (len(bbb_ory_entries), bbb_ory_entries)))
    else:
        bbb_ory_entries.sort(key=lambda e: e["end_at"])
        near_entry, far_entry = bbb_ory_entries[0], bbb_ory_entries[1]
        ambiguity_route = _route("Some Airline", "BBB", "ORY", "XX9999")

        def _ambiguity_near_first():
            now = near_entry["end_at"] + 1000
            result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
            if result != CAL_THEME:
                return False, "expected a match near the fixture's first same-route entry, got %r" % (result,)
            return True, ""
        check("match_calendar_theme() matches a detection near the fixture's own first same-route (BBB-ORY) entry", _ambiguity_near_first)

        def _ambiguity_near_second():
            now = far_entry["end_at"] - 1000
            result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
            if result != CAL_THEME:
                return False, "expected a match near the fixture's second same-route entry, got %r" % (result,)
            return True, ""
        check("match_calendar_theme() matches a detection near the fixture's own second same-route (BBB-ORY) entry", _ambiguity_near_second)

        def _ambiguity_midway_matches_neither():
            midpoint = (near_entry["end_at"] + far_entry["end_at"]) / 2.0
            if abs(midpoint - near_entry["end_at"]) <= cr.CALENDAR_MATCH_TOLERANCE_S or \
                    abs(midpoint - far_entry["end_at"]) <= cr.CALENDAR_MATCH_TOLERANCE_S:
                return False, "test setup failure: the fixture's pair is not far enough apart for a clean midpoint (gap=%r)" % (far_entry["end_at"] - near_entry["end_at"],)
            result = cr.match_calendar_theme({"entries": bbb_ory_entries}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, midpoint)
            if result is not None:
                return False, "expected no match midway between the fixture's pair, outside both tolerances, got %r" % (result,)
            return True, ""
        check("match_calendar_theme() matches neither of the fixture's own same-route entries when the detection sits midway, outside both tolerances", _ambiguity_midway_matches_neither)

        def _ambiguity_deterministic_regardless_of_list_order():
            now = near_entry["end_at"] + 1000
            forward = cr.match_calendar_theme({"entries": [near_entry, far_entry]}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
            reversed_order = cr.match_calendar_theme({"entries": [far_entry, near_entry]}, ambiguity_route, cr.ARRIVING_STATE, CAL_CFG, now)
            if forward != reversed_order:
                return False, "expected the same result regardless of entry list order, got %r vs %r" % (forward, reversed_order)
            if forward != CAL_THEME:
                return False, "test setup failure: expected a match in the forward-order case, got %r" % (forward,)
            return True, ""
        check("match_calendar_theme() returns the identical result whether the fixture's same-route entries are listed forward or reversed (determinism, not iteration order)", _ambiguity_deterministic_regardless_of_list_order)

    # 72. No calendar_theme_id saved in device_cfg - no match.
    def _no_calendar_theme_id_saved_yields_no_match():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "XX1001")
        cfg = {"theme": device_config.DEFAULT_THEME_ID}
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, cfg, MATCH_NOW)
        if result is not None:
            return False, "expected no match with no calendar_theme_id saved, got %r" % (result,)
        return True, ""
    check("match_calendar_theme() returns no match when device_cfg carries no calendar_theme_id", _no_calendar_theme_id_saved_yields_no_match)

    # 73. A calendar_theme_id that is not a member of device_config.THEMES
    #     yields no match - this tier's share of T-16-TAMPER. Assert
    #     explicitly that the unregistered value is never returned.
    def _tampered_calendar_theme_id_never_returned():
        entries = [_entry("XX", "ORY", "AAA", MATCH_NOW, MATCH_NOW + 7200)]
        route = _route("Some Airline", "ORY", "AAA", "XX1001")
        cfg = {"theme": device_config.DEFAULT_THEME_ID, "calendar_theme_id": "not-a-real-theme"}
        result = cr.match_calendar_theme({"entries": entries}, route, cr.DEPARTING_STATE, cfg, MATCH_NOW)
        if result is not None:
            return False, "expected the unregistered calendar_theme_id to never be returned, got %r" % (result,)
        if "not-a-real-theme" in device_config.THEMES:
            return False, "test setup invalid: 'not-a-real-theme' is somehow a real theme id"
        return True, ""
    check("match_calendar_theme() never returns a calendar_theme_id that is not a member of device_config.THEMES (T-16-TAMPER)", _tampered_calendar_theme_id_never_returned)

    # 74. Never raises: a non-dict registry, a non-list entries, entries
    #     containing a non-dict and a partially-shaped dict, a non-dict
    #     route, a non-dict device_cfg, a non-numeric now, and a render
    #     state that is neither confirmed state - each returns None and
    #     raises nothing.
    def _matcher_never_raises():
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
                return False, "case %r unexpectedly returned %r instead of None" % (
                    (registry, route, render_state, device_cfg, now), result)
        return True, ""
    check("match_calendar_theme() never raises for a non-dict registry, non-list entries, malformed entries, a non-dict route, a non-dict device_cfg, a non-numeric now, or an unconfirmed render state", _matcher_never_raises)

    # --- Phase 16 code-review regressions (CR-01, CR-02) -----------------
    # Both were reproduced against the shipped module by the phase's code
    # review, and neither was covered by any existing check here — which is
    # precisely why they survived a 13/13 goal verification and a 12-threat
    # security audit. These two checks are the regression net.

    # CR-01: an RFC 5545-legal component nested inside a VEVENT (VALARM being
    # the common one — Apple Calendar attaches one to any event with an alert)
    # must not end the event. The pre-fix parser treated ANY `END:` as the
    # VEVENT's own, dropping a valid flight silently, without incrementing
    # either rejection counter, so nothing was ever logged either.
    def _nested_component_does_not_drop_the_event():
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
            return False, "expected the flight to survive a nested VALARM, got %d entr(ies)" % (len(got),)
        entry = got[0]
        expected = {"airline_iata": "ZQ", "origin_iata": "MPL", "destination_iata": "ORY"}
        actual = {k: entry.get(k) for k in expected}
        if actual != expected:
            return False, "expected %r, got %r" % (expected, actual)
        return True, ""
    check("parse_ics_events() keeps a flight whose VEVENT contains a nested VALARM, and the nested component's properties never reach the parent entry (CR-01)", _nested_component_does_not_drop_the_event)

    # CR-02: json.loads() accepts NaN/Infinity by default, isinstance(nan,
    # float) is True, and EVERY comparison against NaN is False — so a
    # NaN-timestamped entry slipped past the ordering guard, then past D-03's
    # window and D-04's tolerance, becoming a permanent unconditional match.
    def _non_finite_timestamps_rejected():
        for literal in ("NaN", "Infinity", "-Infinity"):
            entry = json.loads(
                '{"airline_iata":"ZQ","origin_iata":"MPL","destination_iata":"ORY",'
                '"start_at":%s,"end_at":%s}' % (literal, literal))
            if cr._normalise_calendar_entry(entry) is not None:
                return False, "%s timestamps were accepted" % (literal,)
        # a finite entry of the same shape must still be accepted, so the
        # check cannot pass by rejecting everything
        ok_entry = {"airline_iata": "ZQ", "origin_iata": "MPL",
                    "destination_iata": "ORY", "start_at": 1.0, "end_at": 2.0}
        if cr._normalise_calendar_entry(ok_entry) is None:
            return False, "a finite entry was rejected — the check would pass vacuously"
        return True, ""
    check("_normalise_calendar_entry() rejects NaN/Infinity timestamps while still accepting a finite entry (CR-02)", _non_finite_timestamps_rejected)

    # --- Quick task 260908-asr (T-16-PRIV): the regression check the
    #     original goal verification missed, plus three anti-drift checks
    #     (D-01/D-02/D-03/D-04). -----------------------------------------

    # Check A: the required regression check. This is the verification the
    # original goal check missed - the reason T-16-PRIV shipped. A feed
    # that fails for three consecutive cycles must not leave a stale entry
    # on disk indefinitely.
    def _failing_refresh_trims_the_raw_file_across_consecutive_cycles():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            # Seed the realistic way: a legitimate write at a seed_now
            # where the entry is genuinely in-window - this reproduces
            # the real production sequence (one successful fetch, then
            # a feed that breaks), not a hand-edited file.
            seed_now = 1_780_000_000.0
            stale = _entry("XX", "AAA", "ORY", seed_now, seed_now + 7200.0)
            if not cr.write_calendar_registry(
                    tmp, [stale], seed_now, "2026-01-01T00:00:00+00:00", now=seed_now):
                return False, "test setup failure: seed write failed"
            seeded_raw = json.load(open(cr.calendar_rules_path(tmp)))
            if len(seeded_raw["entries"]) != 1:
                return False, ("test setup failure: the seeded entry should be in-window at "
                                "seed_now, got %r" % (seeded_raw["entries"],))

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
                    return False, "cycle %d: expected FETCH_FAILED, got %r - a check that " \
                        "silently took the throttled path would prove nothing" % (cycle, code)
                # Read the RAW file, never through load_calendar_registry() -
                # the loader now windows on read, so it would return a
                # trimmed list even from an untrimmed file, masking
                # exactly the on-disk state this check exists to observe.
                raw = json.load(open(cr.calendar_rules_path(tmp)))
                if raw["entries"] != []:
                    return False, "cycle %d: the stale entry survives on disk: %r" % (cycle, raw["entries"])
                if reg["entries"] != raw["entries"]:
                    return False, "cycle %d: the returned registry != the on-disk entries (D-04)" % (cycle,)
                if raw["last_attempt_at"] != now:
                    return False, "cycle %d: last_attempt_at did not move" % (cycle,)
                if raw["last_synced_at"] != "2026-01-01T00:00:00+00:00":
                    return False, "cycle %d: a failing feed must not read as freshly synced" % (cycle,)
        return True, ""
    check(
        "T-16-PRIV's own reproduction: an entry that ended ~10 days ago is absent from the RAW on-disk file "
        "after every one of three consecutive FAILING refresh_calendar_registry() cycles, and the returned "
        "registry matches the raw file on every cycle (D-04) - the verification the original goal check "
        "missed",
        _failing_refresh_trims_the_raw_file_across_consecutive_cycles)

    # Check B: the loader applies the window on read - a hand-written file
    # mixing one out-of-window and one in-window entry loads to the
    # in-window entry only, and the read does not rewrite the file.
    def _loader_applies_the_window_on_read_without_rewriting():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        out_of_window = _entry("XX", "AAA", "ORY", now - 90000.0, now - 86400.0)  # ended yesterday
        in_window = _entry("XX", "BBB", "ORY", now + 3600.0, now + 7200.0)
        with tempfile.TemporaryDirectory() as tmp:
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
                return False, "expected only the in-window entry, got %r" % (loaded["entries"],)
            if before_bytes != after_bytes:
                return False, "load_calendar_registry() rewrote the file on a plain read"
        return True, ""
    check(
        "a hand-written file mixing one out-of-window and one in-window entry loads to the in-window entry "
        "only, and the read does not rewrite the file (D-01/D-02)",
        _loader_applies_the_window_on_read_without_rewriting)

    # Check C: the writer refuses to persist what the loader would drop -
    # the extended form of write_calendar_registry()'s own documented
    # invariant, now covering the window and not just shape and the cap.
    def _writer_refuses_to_persist_what_the_window_would_drop():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        stale = _entry("XX", "AAA", "ORY", now - 90000.0, now - 86400.0)
        current = _entry("XX", "BBB", "ORY", now + 3600.0, now + 7200.0)
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.write_calendar_registry(
                    tmp, [stale, current], 1.0, "2026-09-07T00:00:00+00:00", now=now):
                return False, "test setup failure: write failed"
            raw = json.load(open(cr.calendar_rules_path(tmp)))
            if [e["origin_iata"] for e in raw["entries"]] != ["BBB"]:
                return False, "expected only the current entry in the raw file, got %r" % (raw["entries"],)
        return True, ""
    check(
        "a write containing a stale entry and a current entry puts only the current entry in the raw file "
        "(D-01/D-03)",
        _writer_refuses_to_persist_what_the_window_would_drop)

    # Check D: the anti-drift guard (D-02) - a behavioural equivalence
    # assertion, not a source grep. Goes red the moment a second window
    # implementation appears anywhere on the load path and starts
    # disagreeing with the sole implementation, select_window_entries().
    def _loader_output_is_exactly_select_window_entries():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        mixed = [
            _entry("XX", "AAA", "ORY", now - 200000.0, now - 190000.0),  # ended yesterday
            _entry("XX", "BBB", "ORY", now - 8 * 3600.0, now - 7 * 3600.0),  # landed earlier today
            _entry("XX", "CCC", "ORY", now + 2 * 3600.0, now + 3 * 3600.0),  # later today
            _entry("XX", "DDD", "ORY", now + 47 * 3600.0, now + 48 * 3600.0),  # 47h ahead
            _entry("XX", "EEE", "ORY", now + 49 * 3600.0, now + 50 * 3600.0),  # 49h ahead - out
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_rules_path(tmp)
            os.makedirs(tmp, exist_ok=True)
            with open(path, "w") as fh:
                json.dump({"entries": mixed, "last_attempt_at": None, "last_synced_at": None}, fh)
            loaded = cr.load_calendar_registry(tmp, now)
            expected = cr.select_window_entries(mixed, now)
            if loaded["entries"] != expected:
                return False, ("load_calendar_registry()'s entries diverged from "
                                "select_window_entries(list, now): got %r, expected %r"
                                % (loaded["entries"], expected))
        return True, ""
    check(
        "for any list and any now, the loader's entries are exactly select_window_entries(list, now) - the "
        "anti-drift guard that goes red if a second window implementation ever appears (D-02)",
        _loader_output_is_exactly_select_window_entries)

    # --- Phase 17 plan 01: save_calendar_url()'s 0600 writer, the mode
    # guard, and the registry erase-on-every-change behaviour. Every
    # permission assertion below reads stat.S_IMODE(os.stat(path).st_mode)
    # against an explicit octal literal - never an owner-relative
    # readability test, which would pass identically at 0600 and 0644 and
    # prove nothing, since this harness always runs as the file's owner.

    # E1. The temporary file's mode is an ARGUMENT to the call that
    # CREATES it - proved by spying on os.open() itself and recording the
    # `mode` argument it was called with, not merely inspecting the
    # file's mode at some later point. A check that only re-stats the
    # file right before the rename (as an os.replace() wrapper would)
    # cannot distinguish "created at 0600" from "created at 0644, then
    # os.chmod()'ed to 0600 before the rename" - both leave the file at
    # 0600 by the time os.replace() runs. Spying on os.open()'s mode
    # argument is the only way to see whether a permission-widening
    # window ever existed, which is D-01's actual requirement.
    def _tmp_file_mode_is_0600_at_creation_time():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
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

            cr.os.open = _spy_open
            cr.os.replace = _spy_replace
            try:
                ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
            finally:
                cr.os.open = real_open
                cr.os.replace = real_replace
            if not ok:
                return False, "test setup failure: save_calendar_url() returned False"
            if "open_mode" not in recorded:
                return False, (
                    "os.open() was never called to create the secret file's temporary file - the mode "
                    "must be an argument to the creating call, not a plain builtin open()")
            if recorded["open_mode"] != 0o600:
                return False, "os.open()'s own mode argument was %r, expected 0o600" % (recorded["open_mode"],)
            if recorded.get("replace_mode") != 0o600:
                return False, (
                    "temporary file's mode at rename time was %r, expected 0o600" % (recorded.get("replace_mode"),))
        return True, ""
    check(
        "save_calendar_url() passes 0o600 as os.open()'s own mode argument when creating its temporary "
        "file - not merely a file that happens to read 0o600 later - and the mode still reads 0o600 at "
        "the moment of the atomic rename (T-17-MODE)",
        _tmp_file_mode_is_0600_at_creation_time)

    # E1b. The direct statement of the prohibition: save_calendar_url()
    # never calls os.chmod() at all. A post-write "fix up the mode"
    # os.chmod() call is the exact anti-pattern D-01 forbids - it leaves
    # a window in which the file exists at the wider bits - and this
    # check catches it even in the (structurally impossible, given E1
    # above) case where a chmod happened to land on 0600 before the
    # rename ran.
    def _writer_never_calls_chmod():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            real_chmod = cr.os.chmod

            def _spy_chmod(path, mode, *args, **kwargs):
                calls.append((path, mode))
                return real_chmod(path, mode, *args, **kwargs)

            cr.os.chmod = _spy_chmod
            try:
                ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
            finally:
                cr.os.chmod = real_chmod
            if not ok:
                return False, "test setup failure: save_calendar_url() returned False"
            if calls:
                return False, "save_calendar_url() called os.chmod(%r) - the mode must never be a follow-up call" % (calls,)
        return True, ""
    check(
        "save_calendar_url() never calls os.chmod() at all - the mode is set once, at file-creation time, "
        "never as a follow-up permission change (T-17-MODE)",
        _writer_never_calls_chmod)

    # E2/E3. Final mode survives two different process umasks. Both
    # restore the previous umask in a finally, since it is process-global
    # and every later check in this harness inherits it.
    def _final_mode_is_0600_under_umask_022():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            old_umask = os.umask(0o022)
            try:
                ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
            finally:
                os.umask(old_umask)
            if not ok:
                return False, "test setup failure: save_calendar_url() returned False"
            mode = stat_mod.S_IMODE(os.stat(cr.calendar_secret_path(tmp)).st_mode)
            if mode != 0o600:
                return False, "expected 0o600 under umask 022, got %o" % (mode,)
        return True, ""
    check("save_calendar_url() writes mode 0600 under a process umask of 022", _final_mode_is_0600_under_umask_022)

    def _final_mode_is_0600_under_umask_027():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            old_umask = os.umask(0o027)
            try:
                ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
            finally:
                os.umask(old_umask)
            if not ok:
                return False, "test setup failure: save_calendar_url() returned False"
            mode = stat_mod.S_IMODE(os.stat(cr.calendar_secret_path(tmp)).st_mode)
            if mode != 0o600:
                return False, "expected 0o600 under umask 027, got %o" % (mode,)
        return True, ""
    check("save_calendar_url() writes mode 0600 under a process umask of 027", _final_mode_is_0600_under_umask_027)

    # E4. os.replace() preserves the SOURCE file's mode and discards the
    # destination's - proved by landing the rename on a pre-existing
    # group-readable file and confirming the result is still 0600.
    def _rename_does_not_inherit_destination_mode():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_secret_path(tmp)
            old_umask = os.umask(0o022)
            try:
                with open(path, "w") as fh:
                    fh.write("stale")
            finally:
                os.umask(old_umask)
            pre_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
            if pre_mode == 0o600:
                return False, "test setup failure: destination already 0600 before the call"
            ok = cr.save_calendar_url(tmp, "https://example.invalid/feed.ics")
            if not ok:
                return False, "test setup failure: save_calendar_url() returned False"
            post_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
            if post_mode != 0o600:
                return False, (
                    "expected 0o600 after replacing a pre-existing group-readable file, got %o" % (post_mode,))
        return True, ""
    check(
        "save_calendar_url() leaves the destination at 0600 even when the rename lands on a pre-existing "
        "group-readable file (T-17-MODE)",
        _rename_does_not_inherit_destination_mode)

    # E5. The negative guard check (T-17-DRIFT): a file created through
    # this codebase's ordinary house idiom - a plain builtin open, no
    # explicit mode - must be flagged unsafe. A suite that only ever
    # exercises the correct writer proves nothing about whether the guard
    # fires.
    def _guard_flags_files_created_through_the_house_idiom():
        import tempfile
        unsafe_modes = (0o644, 0o640, 0o604, 0o660)
        safe_modes = (0o600, 0o400)
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_secret_path(tmp)
            for mode in unsafe_modes:
                with open(path, "w") as fh:
                    fh.write("x")
                os.chmod(path, mode)
                if cr.calendar_secret_mode_is_unsafe(tmp) is not True:
                    return False, "mode 0o%o (the ordinary house idiom's 0o644 among them) was not flagged unsafe" % (mode,)
            for mode in safe_modes:
                os.chmod(path, mode)
                if cr.calendar_secret_mode_is_unsafe(tmp) is not False:
                    return False, "mode 0o%o was incorrectly flagged unsafe" % (mode,)
            os.remove(path)
        return True, ""
    check(
        "calendar_secret_mode_is_unsafe() reports True for a file created through this codebase's ordinary "
        "umask-inheriting house idiom (0o644) and for 0o640/0o604/0o660, and False for 0o600/0o400 - the "
        "negative check proving the guard actually fires, not merely that the correct writer is correct "
        "(T-17-DRIFT)",
        _guard_flags_files_created_through_the_house_idiom)

    # E6. Absent file is not a permission problem, and the answer is a
    # genuine bool.
    def _guard_is_false_and_a_genuine_bool_when_absent():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = cr.calendar_secret_mode_is_unsafe(tmp)
            if result is not False:
                return False, "expected a genuine False for an absent secret file, got %r" % (result,)
        return True, ""
    check(
        "calendar_secret_mode_is_unsafe() is a genuine bool False (is False, not merely falsy, never None) "
        "on a state dir with no secret file",
        _guard_is_false_and_a_genuine_bool_when_absent)

    # E7. The clear branch: removes the file, returns True, and tolerates
    # being called again with the file already gone.
    def _clear_branch_removes_the_file_and_is_idempotent():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
                return False, "test setup failure: initial write failed"
            path = cr.calendar_secret_path(tmp)
            if stat_mod.S_IMODE(os.stat(path).st_mode) != 0o600:
                return False, "test setup failure: initial write was not 0o600"
            if cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL) is not True:
                return False, "clear did not return True"
            if os.path.exists(path):
                return False, "secret file still exists after clear"
            if cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL) is not True:
                return False, "clearing an already-absent file did not return True"
        return True, ""
    check(
        "save_calendar_url(CLEAR_CALENDAR_URL) removes the secret file, returns True, and returns True again "
        "when called a second time with the file already gone",
        _clear_branch_removes_the_file_and_is_idempotent)

    # E8. Erase on set/replace (D-05): seed real-shaped entries and a
    # sync timestamp, then set a URL, and confirm both are gone.
    def _erase_on_set_or_replace_d05():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
                return False, "test setup failure: seed write failed"
            if not cr.save_calendar_url(tmp, "https://example.invalid/new-feed.ics", now=now):
                return False, "save_calendar_url() returned False"
            loaded = cr.load_calendar_registry(tmp, now)
            if loaded["entries"] != []:
                return False, "expected zero entries after setting a URL, got %r" % (loaded["entries"],)
            if loaded["last_attempt_at"] is not None or loaded["last_synced_at"] is not None:
                return False, (
                    "expected both timestamps None after setting a URL, got %r/%r"
                    % (loaded["last_attempt_at"], loaded["last_synced_at"]))
        return True, ""
    check(
        "save_calendar_url() erases the fetched registry - zero entries and both timestamps None - on "
        "setting a URL for the first time or replacing one with a different URL (D-05)",
        _erase_on_set_or_replace_d05)

    # E9. Erase on clear (D-04): same seed, then the sentinel; both the
    # registry and the secret file must be gone.
    def _erase_on_clear_d04():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
                return False, "test setup failure: seed write failed"
            if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics", now=now):
                return False, "test setup failure: initial save failed"
            if not cr.save_calendar_url(tmp, cr.CLEAR_CALENDAR_URL, now=now):
                return False, "clear returned False"
            loaded = cr.load_calendar_registry(tmp, now)
            if loaded["entries"] != []:
                return False, "expected zero entries after clearing, got %r" % (loaded["entries"],)
            if loaded["last_attempt_at"] is not None or loaded["last_synced_at"] is not None:
                return False, "expected both timestamps None after clearing"
            if os.path.exists(cr.calendar_secret_path(tmp)):
                return False, "secret file still present after clearing"
        return True, ""
    check(
        "save_calendar_url(CLEAR_CALENDAR_URL) erases the fetched registry and removes the secret file in "
        "the same call (D-04)",
        _erase_on_clear_d04)

    # E10. Rejected values change nothing: an existing secret file's
    # bytes and mode, and a seeded registry, are all untouched.
    def _rejected_values_change_nothing():
        import stat as stat_mod
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics", now=now):
                return False, "test setup failure: initial save failed"
            if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
                return False, "test setup failure: re-seed failed"
            path = cr.calendar_secret_path(tmp)
            with open(path, "rb") as fh:
                before_bytes = fh.read()
            before_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
            for rejected in (None, "", "   ", 17):
                if cr.save_calendar_url(tmp, rejected, now=now) is not False:
                    return False, "expected False for rejected value %r" % (rejected,)
                with open(path, "rb") as fh:
                    after_bytes = fh.read()
                if after_bytes != before_bytes:
                    return False, "secret file content changed after rejected value %r" % (rejected,)
                after_mode = stat_mod.S_IMODE(os.stat(path).st_mode)
                if after_mode != before_mode:
                    return False, "secret file mode changed after rejected value %r" % (rejected,)
                loaded = cr.load_calendar_registry(tmp, now)
                if [e["origin_iata"] for e in loaded["entries"]] != ["ORY"]:
                    return False, "registry entries changed after rejected value %r" % (rejected,)
        return True, ""
    check(
        "save_calendar_url() returns False and leaves an existing secret file's bytes and mode, and a "
        "seeded registry, untouched for None, an empty string, a whitespace-only string and a non-string "
        "value",
        _rejected_values_change_nothing)

    # E11. Content round-trips stripped, with an explicit mode check
    # alongside it.
    def _content_round_trips_stripped():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "  https://example.invalid/feed.ics?t=abc  \n"):
                return False, "test setup failure: save_calendar_url() returned False"
            path = cr.calendar_secret_path(tmp)
            with open(path, "rb") as fh:
                raw = fh.read()
            if raw != b"https://example.invalid/feed.ics?t=abc":
                return False, "expected the bare stripped URL with no trailing newline, got %r" % (raw,)
            if stat_mod.S_IMODE(os.stat(path).st_mode) != 0o600:
                return False, "expected the round-tripped file to still be 0o600"
        return True, ""
    check(
        "save_calendar_url() strips leading/trailing whitespace and a trailing newline, writing the bare "
        "URL with no trailing newline byte, at mode 0600",
        _content_round_trips_stripped)

    # E12. No temporary file survives a successful write or a rejected
    # call.
    def _no_temp_file_survives():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
                return False, "test setup failure: successful write failed"
            if cr.save_calendar_url(tmp, "") is not False:
                return False, "test setup failure: rejected call did not return False"
            for name in os.listdir(tmp):
                if name.endswith(".tmp"):
                    return False, "a temporary file survived: %r" % (name,)
        return True, ""
    check(
        "no file matching the temporary-name shape remains in state_dir after a successful write or a "
        "rejected call",
        _no_temp_file_survives)

    # E13. The sentinel is identity-only: the literal string equal to the
    # sentinel's conventional name takes the write branch, not the clear
    # branch.
    def _sentinel_is_identity_only():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "CLEAR_CALENDAR_URL"):
                return False, "test setup failure: the literal string 'CLEAR_CALENDAR_URL' was rejected"
            path = cr.calendar_secret_path(tmp)
            if not os.path.exists(path):
                return False, "the literal string took the clear branch instead of the write branch"
            with open(path, "rb") as fh:
                raw = fh.read()
            if raw != b"CLEAR_CALENDAR_URL":
                return False, "expected the literal string written to the file, got %r" % (raw,)
        return True, ""
    check(
        "passing the literal string 'CLEAR_CALENDAR_URL' takes the ordinary write branch, not the "
        "sentinel's clear branch (identity comparison only)",
        _sentinel_is_identity_only)

    # --- Phase 17 plan 02: the read-path swap from the environment to the
    #     secret file (D-02, D-03, D-06, D-08). ------------------------------

    # F1. The value comes from the file.
    def _accessor_reads_the_secret_file():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
            url = cr.configured_calendar_url(tmp)
            if url != "https://example.invalid/feed.ics":
                return False, "expected the file's exact value, got %r" % (url,)
            if cr.calendar_is_configured(tmp) is not True:
                return False, "expected calendar_is_configured() to be True (identity)"
        return True, ""
    check(
        "configured_calendar_url() returns exactly the value written through save_calendar_url(), and "
        "calendar_is_configured() is True (identity) for the same state_dir (D-03)",
        _accessor_reads_the_secret_file)

    # F2. The retired environment variable is inert - proved by spying on
    #     os.environ.get() itself (the exact call shape the retired
    #     accessors used) rather than by naming the retired variable, which
    #     the zero-occurrence gate in the next task forbids writing anywhere
    #     in this file. Spying on the access method rather than one specific
    #     name is also the stronger guarantee: it would catch a resurrected
    #     read under ANY name, not merely the one this project happened to
    #     retire.
    def _environment_is_never_consulted():
        import tempfile
        with tempfile.TemporaryDirectory() as configured_tmp:
            _write_calendar_secret(configured_tmp, "https://example.invalid/feed.ics")
            with tempfile.TemporaryDirectory() as unconfigured_tmp:
                real_get = os.environ.get
                calls = []

                def spy_get(key, default=None):
                    calls.append(key)
                    return real_get(key, default)

                os.environ.get = spy_get
                try:
                    url = cr.configured_calendar_url(configured_tmp)
                    configured = cr.calendar_is_configured(configured_tmp)
                    url2 = cr.configured_calendar_url(unconfigured_tmp)
                    configured2 = cr.calendar_is_configured(unconfigured_tmp)
                finally:
                    os.environ.get = real_get
                if calls:
                    return False, (
                        "os.environ.get() was called %d time(s) during accessor calls - a "
                        "resurrected environment read: %r" % (len(calls), calls))
                if url != "https://example.invalid/feed.ics":
                    return False, "expected the secret file's value, got %r" % (url,)
                if configured is not True:
                    return False, "expected calendar_is_configured() to be True with a secret file present"
                if url2 is not None:
                    return False, "expected None with no secret file present, got %r" % (url2,)
                if configured2 is not False:
                    return False, "expected calendar_is_configured() to be False with no secret file present"
        return True, ""
    check(
        "neither configured_calendar_url() nor calendar_is_configured() ever calls os.environ.get() - "
        "the check that would catch a resurrected environment read, with and without a secret file "
        "present (D-03)",
        _environment_is_never_consulted)

    # F3. A drifted file refuses, and the value is never read - proved by
    #     observing the file was never opened, not merely by observing the
    #     return value (D-02, T-17-DRIFT).
    def _drifted_file_refuses_without_being_opened():
        import builtins
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
            path = cr.calendar_secret_path(tmp)
            os.chmod(path, 0o644)
            if not (stat_mod.S_IMODE(os.stat(path).st_mode) & (stat_mod.S_IRWXG | stat_mod.S_IRWXO)):
                return False, "test setup failure: chmod(0o644) did not produce a group/other-readable file"
            real_open = builtins.open
            opened_paths = []

            def spy_open(file, *a, **k):
                opened_paths.append(file)
                return real_open(file, *a, **k)

            builtins.open = spy_open
            try:
                url = cr.configured_calendar_url(tmp)
            finally:
                builtins.open = real_open
            if url is not None:
                return False, "expected None for a drifted-permission file, got %r" % (url,)
            if path in opened_paths:
                return False, (
                    "the secret file's path was opened even though its permissions were drifted - "
                    "the value may have been read into memory: %r" % (opened_paths,))
        return True, ""
    check(
        "configured_calendar_url() refuses a secret file whose permissions have drifted, and never "
        "opens it at all - proved by observing the file was not opened, not merely by observing the "
        "return value (D-02, T-17-DRIFT)",
        _drifted_file_refuses_without_being_opened)

    # F4. A file written through the ordinary house idiom (not
    #     save_calendar_url()'s explicit 0600) is refused end to end - the
    #     negative counterpart to F1, going through the accessor rather than
    #     calendar_secret_mode_is_unsafe() alone.
    def _ordinary_umask_file_refused_end_to_end():
        import stat as stat_mod
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_secret_path(tmp)
            with open(path, "w") as fh:
                fh.write("https://example.invalid/feed.ics")
            mode = stat_mod.S_IMODE(os.stat(path).st_mode)
            if not (mode & (stat_mod.S_IRWXG | stat_mod.S_IRWXO)):
                return False, (
                    "test setup failure: the process umask produced an owner-only file (%o) - this "
                    "check needs a group/other-readable file to be meaningful" % (mode,))
            url = cr.configured_calendar_url(tmp)
            if url is not None:
                return False, (
                    "expected None for a file written through the ordinary umask-inheriting idiom, "
                    "got %r" % (url,))
            if cr.calendar_is_configured(tmp) is not False:
                return False, "expected calendar_is_configured() to be False for the same file"
        return True, ""
    check(
        "a secret file written through this codebase's ordinary umask-inheriting house idiom (plain "
        "open(path, 'w'), not save_calendar_url()'s explicit 0600) is refused end to end by "
        "configured_calendar_url() and calendar_is_configured() - the negative counterpart to F1, "
        "going through the accessor rather than the mode predicate alone",
        _ordinary_umask_file_refused_end_to_end)

    # F5. The boolean contract holds in all three states, by identity
    #     comparison (D-08).
    def _boolean_contract_in_three_states():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if cr.calendar_is_configured(tmp) is not False:
                return False, "expected False (identity) for an absent secret file"
            _write_calendar_secret(tmp, "https://example.invalid/feed.ics")
            if cr.calendar_is_configured(tmp) is not True:
                return False, "expected True (identity) for a configured secret file"
            path = cr.calendar_secret_path(tmp)
            os.chmod(path, 0o644)
            if cr.calendar_is_configured(tmp) is not False:
                return False, "expected False (identity) for a drifted-permission secret file"
        return True, ""
    check(
        "calendar_is_configured() returns a genuine bool - is True, is False, is False - across "
        "absent, configured, and permission-drifted secret files, never a truthy status string (D-08)",
        _boolean_contract_in_three_states)

    # F6. A hand-written file's trailing newline is stripped by the reader,
    #     not merely by the writer.
    def _accessor_strips_hand_written_trailing_newline():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = cr.calendar_secret_path(tmp)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write("https://example.invalid/feed.ics\n")
            url = cr.configured_calendar_url(tmp)
            if url != "https://example.invalid/feed.ics":
                return False, "expected the trailing newline stripped, got %r" % (url,)
        return True, ""
    check(
        "configured_calendar_url() strips a trailing newline from a hand-written secret file, "
        "returning the bare URL",
        _accessor_strips_hand_written_trailing_newline)

    # F7. min_interval_s bypasses the throttle; the default preserves it
    #     (D-06).
    def _min_interval_s_bypasses_the_throttle():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _write_calendar_secret(tmp, "https://%s/a.ics" % PUBLIC_IP)
            seed_now = 1_800_000_000.0
            if not cr.write_calendar_registry(tmp, [], seed_now, None, now=seed_now):
                return False, "test setup failure: seed write failed"
            now = seed_now + 60.0  # well inside CALENDAR_FETCH_INTERVAL_S (1800s)

            calls = []
            transport = make_calendar_transport(
                status_code=200, body=b"BEGIN:VCALENDAR\nEND:VCALENDAR", calls=calls)

            code, _reg = cr.refresh_calendar_registry(tmp, now, transport=transport)
            if code != cr.FETCH_SKIPPED_THROTTLED:
                return False, "expected FETCH_SKIPPED_THROTTLED with no interval override, got %r" % (code,)
            if calls:
                return False, "expected no transport call with the default (None) interval, got %r" % (calls,)

            code2, _reg2 = cr.refresh_calendar_registry(tmp, now, transport=transport, min_interval_s=0)
            if code2 != cr.FETCH_OK:
                return False, "expected FETCH_OK when min_interval_s=0 bypasses the throttle, got %r" % (code2,)
            if len(calls) != 1:
                return False, "expected exactly one transport call once the throttle was bypassed, got %d" % (len(calls),)
        return True, ""
    check(
        "refresh_calendar_registry(min_interval_s=0) bypasses the throttle and reaches the transport "
        "even when the recorded last attempt is well inside the standard interval, while the default "
        "(no interval argument) still honours the throttle (D-06)",
        _min_interval_s_bypasses_the_throttle)

    # --- 17-REVIEW.md CR-02 fix ---------------------------------------------

    # G1 (CR-02 regression). A genuine removal failure - anything other
    # than the file already being absent - must be reported as False, not
    # silently swallowed into a reported success. Reproduced portably by
    # making os.remove() raise PermissionError for the secret path only,
    # the same class of failure `chflags uchg`/`chattr +i`/a read-only
    # remount produces on the real OS. Fails against the pre-fix
    # `except OSError: pass; return True` (which reports True here), and
    # passes once FileNotFoundError and every other OSError are handled
    # separately.
    def _clear_branch_reports_failure_when_removal_actually_fails():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "https://example.invalid/feed.ics"):
                return False, "test setup failure: initial save failed"
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
                return False, (
                    "expected False when the secret file could not actually be removed, got %r" % (result,))
            if not os.path.exists(path):
                return False, "test setup failure: the file should still exist since removal was blocked"
            if cr.calendar_is_configured(tmp) is not True:
                return False, (
                    "calendar_is_configured() should still report True - the file genuinely was not removed")
        return True, ""
    check(
        "save_calendar_url(CLEAR_CALENDAR_URL) returns False, not True, when os.remove() fails for a "
        "reason other than the file already being absent - a permission/immutable-flag/read-only-"
        "filesystem failure must never be reported as a successful disconnect (CR-02)",
        _clear_branch_reports_failure_when_removal_actually_fails)

    # --- 17-REVIEW.md CR-01 fix ---------------------------------------------

    # G2 (CR-01 regression). Two threads stand in for the two real,
    # separate OS processes (skypane-poll.service and
    # skypane-companion.service) racing the SAME registry: thread P
    # simulates a poll cycle's refresh_calendar_registry(), blocked
    # mid-fetch (the network read) via a transport that waits on an
    # Event; this thread simulates a companion disconnect request
    # arriving while P is still "in flight". Without the cross-process
    # lock, P's write-after-fetch lands after the disconnect's erase and
    # resurrects the just-disconnected calendar's flights - this check
    # asserts the erase (the chronologically LAST completed operation)
    # is what the final on-disk state reflects. Note on what this
    # simulates: two threads in one process cannot literally reproduce
    # two OS processes, but the lock this exercises,
    # `cr._calendar_registry_lock()`, is implemented with
    # `fcntl.flock()` - a kernel-level primitive keyed on the lock FILE,
    # not on anything in either caller's memory - so its behaviour here
    # (excluding a second concurrent acquirer until the first releases)
    # is identical regardless of whether the two acquirers are two
    # threads or two processes. This check deliberately never touches
    # `_WRITE_LOCK` or `_POLL_LOCK` (both plain `threading.Lock`s,
    # invisible across processes) - only the lock that actually closes
    # this race.
    def _cross_process_lock_closes_the_disconnect_race():
        import tempfile
        import threading
        import time
        now = _mid_fixture_now()
        with tempfile.TemporaryDirectory() as tmp:
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
                return False, "test setup failure: the simulated poll cycle's fetch never started"

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
                return False, "test setup failure: a thread did not finish within its timeout"
            if not disconnect_result.get("ok"):
                return False, "test setup failure: the disconnect call returned False"

            loaded = cr.load_calendar_registry(tmp, now)
            if loaded["entries"] != []:
                return False, (
                    "the disconnect's erase was overwritten by the concurrently-running poll cycle's "
                    "write - registry has %r entries after an explicit disconnect (CR-01)"
                    % (loaded["entries"],))
            if cr.calendar_is_configured(tmp):
                return False, "expected calendar_is_configured() to be False after the disconnect"
        return True, ""
    check(
        "a companion disconnect arriving while a (simulated) concurrent poll cycle is mid-fetch cannot "
        "have its registry erase overwritten by that poll cycle's later write - the cross-process "
        "registry lock, not either in-process threading.Lock, is what is exercised here (CR-01; "
        "simulates two OS processes with two threads racing the real fcntl-based lock - see comment "
        "above)",
        _cross_process_lock_closes_the_disconnect_race)

    # --- 17-REVIEW.md WR-01 fix ---------------------------------------------

    # G3 (WR-01 regression). Replacing an already-connected calendar's URL
    # must not cost that calendar its already-fetched flights when the
    # NEW secret's write fails before it ever reaches the registry erase.
    # Reproduced by making the tmp file's own write (os.fdopen/the content
    # write, standing in for "disk full" or a briefly unwritable
    # state_dir) fail. Fails against the pre-fix erase-before-write
    # ordering (which erases the seeded entries unconditionally before
    # ever attempting the secret write), and passes once the write is
    # verified before the erase runs.
    def _write_failure_before_erase_preserves_the_previous_calendars_flights():
        import tempfile
        from datetime import datetime, timezone
        now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        seeded = [_entry("AF", "ORY", "JFK", now + 3600.0, now + 7200.0)]
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "https://example.invalid/old-feed.ics", now=now):
                return False, "test setup failure: initial save failed"
            if not cr.write_calendar_registry(tmp, seeded, now, "2026-09-07T00:00:00+00:00", now=now):
                return False, "test setup failure: seeding fetched entries failed"

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
                return False, "expected False when the secret's temp-file write fails, got %r" % (result,)
            loaded = cr.load_calendar_registry(tmp, now)
            if [e["origin_iata"] for e in loaded["entries"]] != ["ORY"]:
                return False, (
                    "the previous calendar's already-fetched flights were erased despite the secret "
                    "write never succeeding - expected them untouched, got %r" % (loaded["entries"],))
            if cr.configured_calendar_url(tmp) != "https://example.invalid/old-feed.ics":
                return False, "expected the OLD url to still be configured after a failed replace"
        return True, ""
    check(
        "save_calendar_url() replacing a connected calendar's URL leaves the previous calendar's "
        "already-fetched flights untouched when the new secret's write fails before ever reaching the "
        "registry erase (WR-01)",
        _write_failure_before_erase_preserves_the_previous_calendars_flights)

    # --- 17-REVIEW.md UAT fix (webcal:// scheme) ------------------------------
    #
    # UAT-discovered defect (filed 2026-09-10): the companion refused every
    # `webcal://` calendar feed URL - the exact scheme Apple Calendar's own
    # "Public Calendar" share links use - because `_url_is_safe()` only ever
    # accepted `https`. Fixed by `_normalise_calendar_url()`, a scheme
    # REWRITE applied upstream of the (unchanged) gate. The checks below
    # prove the rewrite works, is applied on both paths that reach
    # `fetch_ics()` (via `save_calendar_url()`'s stored form and via
    # `fetch_ics()`'s own defensive re-normalisation), and weakens none of
    # the gate's existing refusals.

    # G4 (UAT regression). _normalise_calendar_url() itself: rewrites a
    # webcal scheme (any case) to https, leaves every other scheme - and
    # anything urlparse() cannot make sense of, including None - completely
    # unchanged, and never raises.
    def _normalise_calendar_url_rewrites_only_webcal():
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
                return False, "expected _normalise_calendar_url(%r) == %r, got %r" % (given, expected, got)
        if cr._normalise_calendar_url(None) is not None:
            return False, "expected _normalise_calendar_url(None) to return None without raising"
        return True, ""
    check(
        "_normalise_calendar_url() rewrites a webcal scheme (any case) to https, leaves every other "
        "scheme and an unparseable value unchanged, and never raises on None (UAT)",
        _normalise_calendar_url_rewrites_only_webcal)

    # G5 (UAT regression). fetch_ics() accepts a webcal:// URL - the exact
    # scheme Apple Calendar's own share links use - and the transport
    # observes an https:// request, never a webcal:// one. Fails against
    # the pre-fix gate (which refused webcal outright before any transport
    # call was ever made).
    def _fetch_ics_accepts_webcal_as_https():
        calls = []
        transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR", calls=calls)
        result = cr.fetch_ics("webcal://%s/feed.ics" % PUBLIC_IP, transport=transport)
        if result != "BEGIN:VCALENDAR":
            return False, "expected a webcal:// URL to be fetched successfully, got %r" % (result,)
        if calls != ["https://%s/feed.ics" % PUBLIC_IP]:
            return False, "expected the transport to observe an https:// request, got %r" % (calls,)
        return True, ""
    check(
        "fetch_ics() accepts a webcal:// URL - Apple Calendar's own share-link scheme - and the "
        "transport observes an https:// request (UAT)",
        _fetch_ics_accepts_webcal_as_https)

    # G6 (UAT regression). The webcal rewrite must not weaken
    # _url_is_safe()'s own address checks: a webcal:// URL pointing at a
    # private address, at loopback via the literal IP AND the "localhost"
    # name, and at the cloud metadata address are all still refused.
    def _webcal_does_not_weaken_the_address_gate():
        real_getaddrinfo = socket.getaddrinfo
        try:
            socket.getaddrinfo = lambda host, port=None, *a, **k: (
                [(2, 1, 6, "", ("127.0.0.1", 443))] if host == "localhost"
                else real_getaddrinfo(host, port, *a, **k))
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
                    return False, "expected fetch_ics(%r) to be refused, got %r" % (url, result)
            return True, ""
        finally:
            socket.getaddrinfo = real_getaddrinfo
    check(
        "the webcal:// rewrite does not weaken the address gate - fetch_ics() still refuses a "
        "webcal:// URL pointing at a private address, at loopback (literal IP and \"localhost\"), and "
        "at the cloud metadata address (UAT)",
        _webcal_does_not_weaken_the_address_gate)

    # G7 (UAT regression). There is no webcal -> http downgrade path: a
    # plain http:// URL is still refused by fetch_ics(), exactly as before
    # this fix - _normalise_calendar_url() only ever recognises webcal.
    def _http_still_refused_no_downgrade_path():
        transport = make_calendar_transport(status_code=200, body=b"BEGIN:VCALENDAR")
        result = cr.fetch_ics("http://%s/feed.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected http:// to still be refused, got %r" % (result,)
        return True, ""
    check(
        "fetch_ics() still refuses a plain http:// URL - there is no webcal -> http downgrade path "
        "(UAT)",
        _http_still_refused_no_downgrade_path)

    # G8 (UAT regression). A redirect discovered while fetching an
    # originally-webcal:// URL is still re-validated per hop, exactly like
    # an ordinary https:// URL's own redirect (check 38 above) - refused
    # when the Location targets a loopback address, and never fetched.
    def _redirect_from_normalised_webcal_still_revalidated():
        calls = []
        transport = make_calendar_transport(
            status_code=302, headers={"Location": "https://127.0.0.1/a.ics"},
            is_redirect=True, calls=calls)
        result = cr.fetch_ics("webcal://%s/a.ics" % PUBLIC_IP, transport=transport)
        if result is not None:
            return False, "expected None when a webcal:// URL's redirect targets a loopback address"
        if calls != ["https://%s/a.ics" % PUBLIC_IP]:
            return False, "expected exactly one transport call (the redirect target must never be fetched): %r" % (calls,)
        return True, ""
    check(
        "a redirect discovered while fetching a webcal:// URL (normalised to https:// first) is still "
        "re-validated per hop, refusing a Location that targets a loopback address (UAT)",
        _redirect_from_normalised_webcal_still_revalidated)

    # G9 (UAT regression). save_calendar_url() stores a webcal:// value
    # already rewritten to its https:// form - the secret file itself
    # never holds a webcal:// string, and configured_calendar_url() (the
    # sole accessor) returns the same normalised form back.
    def _save_calendar_url_stores_the_normalised_form():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            if not cr.save_calendar_url(tmp, "webcal://example.invalid/feed.ics"):
                return False, "test setup failure: save_calendar_url() returned False"
            path = cr.calendar_secret_path(tmp)
            with open(path, "rb") as fh:
                raw = fh.read()
            if raw != b"https://example.invalid/feed.ics":
                return False, "expected the stored secret to be the normalised https:// form, got %r" % (raw,)
            if cr.configured_calendar_url(tmp) != "https://example.invalid/feed.ics":
                return False, "expected configured_calendar_url() to return the normalised https:// form"
        return True, ""
    check(
        "save_calendar_url() stores a webcal:// value already rewritten to its https:// form, so the "
        "secret file never holds a webcal:// string (UAT)",
        _save_calendar_url_stores_the_normalised_form)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("calendar_rules: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
