# Phase 16: Calendar-linked flight highlighting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-07
**Phase:** 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
**Areas offered:** Where the match lands, Tolerance and ambiguity, Configuration surface, Fetch cadence and failure
**Areas selected:** Where the match lands (only) — the other three were left to Claude's discretion and are recorded as reasoned defaults in CONTEXT.md

---

## Pre-discussion findings

Three measurements were taken against a real supplied iCal export and real production data BEFORE the discussion, and were presented as settled rather than offered as questions. Two of them overturned the seed's own assumptions, and the third changed what the feature can honestly promise. See CONTEXT.md `<measured_findings>`.

The third finding was put to the developer as a fork — the chosen design (a colour rule that fires only when the flight is on screen) versus a calendar-driven view (which would show the flight regardless of detection). They chose the colour rule.

---

## Where a calendar match lands

| Option | Description | Selected |
|--------|-------------|----------|
| Separate registry, consulted at the same seam | Manual rules stay purely operator-authored; the resolver consults both sources; expiry is a file rewrite | ✓ |
| Write into Phase 15's registry | Visible and deletable in the existing editor, nothing new in the resolver — but one store shared between human and automaton | |
| No storage, match off the cached feed | Nothing to expire, but nothing inspectable either | |

**User's choice:** Separate registry.

| Option | Description | Selected |
|--------|-------------|----------|
| The manual rule wins | Explicit human instruction beats an automatic source, mirroring Phase 15's own precedence logic | |
| The calendar wins | A calendar match names one flight on one date; the point is that these stand out | ✓ |
| Most specific of the two wins | Conceptually cleanest, harder to explain and test | |

**User's choice:** The calendar wins.
**Notes:** The consequence was raised before the choice — this also overrides a hand-typed exact-callsign rule, the narrowest thing the operator can write. Chosen anyway.

| Option | Description | Selected |
|--------|-------------|----------|
| Short rolling window, rewritten each fetch | Tiny file, automatic expiry, minimal privacy footprint | ✓ |
| Mirror the whole feed | Simpler, truly inspectable — but persists a person's schedule indefinitely | |

**User's choice:** Short rolling window.

---

## Closing check

"Prêt pour le CONTEXT" chosen over further questions on the registry area (what happens when the calendar is emptied or disconnected, and whether a match should leave an inspectable trace, were offered).

## Claude's Discretion

Time-window width and ambiguity handling; the configuration surface including whether to offer a connection test or a preview of parsed flights; fetch cadence and stale-feed behaviour; field/file names, record shape, module placement, all copy, and test strategy. Reasoned defaults for each are recorded in CONTEXT.md rather than left blank.

## Deferred Ideas

- A calendar-driven view (offered and explicitly not chosen)
- Multiple calendars or per-calendar themes
- A visible trace that a calendar match fired
- Registration (tail number) matching
