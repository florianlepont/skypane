---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
reviewed: 2026-09-08T00:00:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - server/plane/calendar_rules.py
  - server/plane/colour_rules.py
  - server/poll_loop.py
  - server/device_config.py
  - companion/pages/config_page.py
  - companion/app.py
  - server/fixtures/calendar_crewwebplus_redacted.ics
  - deploy/skypane.env.example
  - scripts/run-all-tests.sh
findings:
  critical: 2
  warning: 1
  info: 1
  total: 4
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-09-08
**Depth:** deep
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This review covers the diff between `f7260584f8342702b2c908206558985fb02db85b`
and `HEAD` on `claude/seed-3-roster-highlight` for Phase 16. `16-VERIFICATION.md`
(13/13 truths) and `16-SECURITY.md` (11/12 closed, one documented open medium,
`T-16-PRIV`) have already run and are treated as ground truth for what they
cover — this review does not re-litigate D-01/D-02/D-04 wiring, the SSRF/DoS/
secret-handling controls, or the known fetch-failure retention gap.

The wiring across `poll_loop.py`, `colour_rules.py`, `device_config.py`,
`config_page.py` and `app.py` is careful and matches the documented D-02/D-13
both-branches invariant exactly — no defects found there. The two findings
below are both in the newest, least battle-tested code: the hand-rolled RFC
5545 parser and the registry's numeric-input validation. Both are real,
reproduced against the shipped module (not theoretical), and both sit
squarely in the areas this review was asked to prioritize (parser edge cases
and the tamper surface of a hand-editable `state_dir` file). Neither raises
an exception — both degrade "successfully" into wrong behavior, which is
arguably worse for an unattended 30-second oneshot: nothing crashes, nothing
is logged, and the operator has no signal that anything is wrong.

## Critical Issues

### CR-01: A VEVENT containing any nested component (e.g. `VALARM`) is silently and invisibly dropped

**File:** `server/plane/calendar_rules.py:427-440`
**Issue:**

`parse_ics_events()`'s block-accumulation loop treats **any** `END:` line as
the end of the currently-open `VEVENT`, not just `END:VEVENT`:

```python
if name == "END":
    if value_upper == "VEVENT" and in_event and current is not None:
        entry, reason = _build_entry(current)
        ...
    in_event = False
    current = None
    ...
```

`VALARM` (a reminder/alarm sub-component) is a completely standard, RFC
5545-legal component nested *inside* a `VEVENT` — produced by many real-world
calendar tools (Outlook, Google Calendar exports, and plausibly a future
CrewWebPlus export revision; nothing in the measured findings rules it out,
only that the *sample analysed* didn't have one). When a `BEGIN:VALARM` /
`END:VALARM` pair appears inside a `VEVENT`, the `END:VALARM` line matches
`name == "END"`, fails the `value_upper == "VEVENT"` check (so no entry is
built), but then unconditionally executes `in_event = False; current = None`
— discarding every property accumulated for that event so far. When the
*real* `END:VEVENT` line for that event is reached afterward, `in_event` is
already `False` and `current` is already `None`, so the outer condition
`in_event and current is not None` is false: the entire event silently
vanishes.

Worse, this vanishing is **invisible**: it does not flow through either of
`parse_ics_events()`'s own rejection counters (`rejected_date_form` /
`rejected_other`), so the one-line stderr warning the module prints when
something was dropped never fires. A flight that should have been in the
registry — and colored on the panel — simply isn't, with zero operator
signal.

Reproduced directly against the shipped module:

```python
>>> from server.plane import calendar_rules as cr
>>> ics = """BEGIN:VCALENDAR
... BEGIN:VEVENT
... SUMMARY:XX1001 ORY-AAA(+0200)
... CATEGORIES:FLT
... DTSTART;VALUE=DATE-TIME:20260901T060000Z
... DTEND;VALUE=DATE-TIME:20260901T081500Z
... BEGIN:VALARM
... TRIGGER:-PT15M
... ACTION:DISPLAY
... END:VALARM
... END:VEVENT
... END:VCALENDAR
... """
>>> cr.parse_ics_events(ics)
[]
```

An otherwise perfectly well-formed, matching flight event is dropped with no
trace. This is squarely the "BEGIN/END nesting" edge case the parser's own
module docstring and this review's brief both flag as the area needing the
most scrutiny — and the committed fixture (`server/fixtures/calendar_crewwebplus_redacted.ics`)
and `server/test_calendar_rules.py` contain no `VALARM`/nested-component case
at all, so this gap has no test coverage in either direction.

**Fix:** Track nesting with a depth counter (or a small component-name stack)
instead of a flat boolean, so only the `END:` that matches the `VEVENT`'s own
`BEGIN:VEVENT` closes the block; any nested `BEGIN:X`/`END:X` pair should be
ignored rather than treated as ending the outer event. Minimal fix:

```python
if name == "BEGIN":
    if value_upper == "VEVENT" and not in_event:
        in_event = True
        current = {}
    continue

if name == "END":
    if value_upper == "VEVENT" and in_event and current is not None:
        entry, reason = _build_entry(current)
        ...
        in_event = False
        current = None
        if len(entries) >= CALENDAR_MAX_ENTRIES:
            break
    # any other END (nested component) is simply ignored — it does not
    # reset in_event/current, so the outer VEVENT keeps accumulating.
    continue
```
(A `BEGIN:VEVENT` while `in_event` is already true — a malformed nested
`VEVENT` — should probably also be ignored rather than resetting `current`,
though that shape is far less likely to occur from a real producer than a
`VALARM`.)

---

### CR-02: `NaN`/`Infinity` timestamps in a hand-edited `calendar_rules.json` bypass both the retention window and the match time-window, producing a permanent, unconditional match

**File:** `server/plane/calendar_rules.py:519-566` (`_normalise_calendar_entry`), also affects `select_window_entries()` (`:770-818`) and `match_calendar_theme()` (`:1394-1416`)
**Issue:**

`_normalise_calendar_entry()` — the single validation gate the module's own
docstring calls "T-16-INPUT's defence" against `calendar_rules.json` being
"an operator-inspectable file" and "this tier's tamper vector" — accepts
`start_at`/`end_at` whenever they satisfy `isinstance(x, (int, float))` and
are not `bool`:

```python
if isinstance(start_at, bool) or not isinstance(start_at, (int, float)):
    return None
if isinstance(end_at, bool) or not isinstance(end_at, (int, float)):
    return None
...
if end_at < start_at:
    return None
```

Python's `float('nan')` passes `isinstance(x, (int, float))`, and Python's
`json` module (used unconditionally by `load_calendar_registry()`) parses the
bare JSON extensions `NaN`/`Infinity`/`-Infinity` by default — confirmed:
`json.loads('{"a": NaN}')` returns `{'a': nan}` with no error. A `NaN` value
also silently survives the `end_at < start_at` order check, because every
comparison against `NaN` evaluates to `False`.

The consequence cascades through the two controls this field is supposed to
enforce:

1. **`select_window_entries()`'s D-03 retention window never expires it.**
   Both of its bounding comparisons (`normalised["end_at"] < day_start` and
   `normalised["start_at"] > forward_edge`) are `False` for `NaN`, so the
   entry is never dropped by the rolling window — it is retained and
   re-persisted forever, the exact failure mode `T-16-PRIV` already
   documents for the fetch-failure path, but here with no expiry condition
   at all, ever.
2. **`match_calendar_theme()`'s D-04 time-window tolerance never excludes
   it.** `diff = abs(now - reference_time)` is `NaN` when `reference_time`
   is `NaN`, and `diff > CALENDAR_MATCH_TOLERANCE_S` is `False` for any
   `NaN` diff — so the entry is never filtered out by the 90-minute
   tolerance. It becomes `best` on the first iteration (`best is None` is
   `True`), and no later real, correctly-timed candidate can ever displace
   it, because `candidate < best` is also always `False` once `best`'s
   `diff` is `NaN`.

Net effect: one entry with `"start_at": NaN, "end_at": NaN` for a given
`airline_iata`/`origin_iata`/`destination_iata` triple becomes a permanent,
unconditional match for that airline+route — active on every cycle,
forever, regardless of the real clock — completely defeating both D-03's
"rewritten whole, past entries expire" guarantee and D-04's "time window"
requirement. Reproduced directly against the shipped module:

```python
>>> import server.device_config as dc
>>> from server.plane import calendar_rules as cr
>>> registry = {"entries": [{"airline_iata": "TO", "origin_iata": "ORY",
...              "destination_iata": "AAA", "start_at": float("nan"),
...              "end_at": float("nan")}]}
>>> route = {"origin_iata": "ORY", "destination_iata": "AAA", "callsign_iata": "TO1234"}
>>> cr.match_calendar_theme(registry, route, cr.DEPARTING_STATE,
...                          {"calendar_theme_id": "green"}, now=1893456000.0)
'green'
```

`now` here is an arbitrary timestamp far outside any plausible flight window
— it still matches. This bug requires write access to `state_dir` to inject
(the file cannot receive a `NaN` via the fetch/parse path, since
`parse_ics_datetime()` only ever produces a value via `strptime()` on the
bare-UTC regex), which is the same trust boundary `T-16-INPUT`/`T-16-TAMPER`
already treat as in-scope and closed — this finding shows the validation
those threats rely on has a gap for this specific input class. Neither
`server/test_calendar_rules.py` nor `16-SECURITY.md` exercises `NaN`/
`Infinity` anywhere.

**Fix:** Reject non-finite numbers explicitly in `_normalise_calendar_entry()`:

```python
import math
...
if isinstance(start_at, bool) or not isinstance(start_at, (int, float)) or not math.isfinite(start_at):
    return None
if isinstance(end_at, bool) or not isinstance(end_at, (int, float)) or not math.isfinite(end_at):
    return None
```
The same `math.isfinite()` guard should also be applied to `last_attempt_at`
in `load_calendar_registry()`/`write_calendar_registry()`, which has the
identical `isinstance(x, (int, float))`-without-finiteness-check shape.

## Warnings

### WR-01: `_far_end_iata`/entry-matching narrowing on optional `callsign_iata` is undocumented as *possibly absent even on a genuine hit*

**File:** `server/plane/calendar_rules.py:1187-1227` (`_airline_iata_from_route`), `server/plane/enrich.py:195-234` (`_parse_route`)
**Issue:** `match_calendar_theme()`'s docstring (and `16-VERIFICATION.md` truth
#3/#4) states the three fields it requires "exist only on a `fresh_hit` or a
`cache_hit`" and treats field-presence as "exactly equivalent to the
`fresh_hit`/`cache_hit` restriction." This is not quite accurate:
`enrich.py`'s own `_parse_route()` docstring documents `callsign_iata` as
**optional even within a `fresh_hit`/`cache_hit`** result — "a route with a
real airline and real cities but no IATA identifier is still fully
displayable," degrading `callsign_iata` to `None` rather than downgrading the
whole result. This means a flight can be a genuine `fresh_hit`/`cache_hit`
(real `origin_iata`/`destination_iata`) yet still silently fail
`match_calendar_theme()`'s field-presence gate at step 3 (`callsign_iata`
missing), and the calendar feature will never fire for that flight even
though it is fully displayable and enrichment succeeded. The code itself
degrades safely (returns `None`, no crash), but the docstring's certainty
("these three fields exist only on...") overstates what is actually
guaranteed, which could mislead a future maintainer investigating "why didn't
this obviously-matching flight get coloured."
**Fix:** Adjust the docstring to note that `callsign_iata` is itself optional
within `fresh_hit`/`cache_hit` (per `enrich._parse_route()`), so the
practical match rate for calendar-linked flights is narrower than "every
`fresh_hit`/`cache_hit`" implies. No code change required — this is a
documentation-accuracy issue, but one worth fixing given how heavily this
module's comments are relied on as the source of truth for future changes.

## Info

### IN-01: `unfold_ics_lines()` does not handle bare-CR (`\r`-only) line endings

**File:** `server/plane/calendar_rules.py:236-245`
**Issue:** `unfold_ics_lines()` normalises `\r\n` to `\n` but does not handle
a feed using bare `\r` line endings (legacy Mac-style), which would cause
`normalised.split("\n")` to treat the entire body as a single logical line.
This degrades gracefully (the single "line" would fail every property/regex
match, yielding zero entries and one `"other"`-bucketed rejection at most,
never a crash), and CORRECTION 2 confirms the real producer is LF-only, so
this is unlikely to matter in practice. Noted for completeness since the
review brief specifically asked about "what happens on input shapes the
fixture does not contain."
**Fix:** Optional — normalise `\r` (not followed by `\n`) to `\n` as well if
broader producer compatibility is ever desired. Not worth doing pre-emptively
given the measured, single, LF-only real producer.

---

_Reviewed: 2026-09-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
