# Phase 44: Companion Walkthrough and Focused Bilingual Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-30
**Phase:** 44-companion-walkthrough-and-focused-bilingual-polish
**Mode:** Autonomous discussion, authorized by the developer.
**Areas discussed:** walkthrough coverage, polish scope, visual continuity, verification

---

## Walkthrough Coverage

| Option | Description | Selected |
|---|---|---|
| Route sampling | Inspect only the routes likely to change. | |
| Complete owner journey | Cover all authenticated routes in both locales and target viewports. | ✓ |

**Choice:** Complete owner journey.
**Notes:** The milestone seed explicitly requires a fresh walkthrough rather
than an assumed defect list. The established 360 px contract and existing
320 px assertions remain in force.

---

## Polish Scope

| Option | Description | Selected |
|---|---|---|
| Visual redesign | Rework the companion's overall presentation. | |
| Focused repairs | Fix walkthrough-proven friction through the existing architecture. | ✓ |

**Choice:** Focused repairs.
**Notes:** The phase is product finish. New capabilities, framework work, and
battery-policy changes are out of scope.

---

## Verification

| Option | Description | Selected |
|---|---|---|
| Source-only review | Judge changes from implementation structure. | |
| Delivered-behaviour checks | Verify affected served output and browser behaviour in English and French. | ✓ |

**Choice:** Delivered-behaviour checks.
**Notes:** This matches the repository's companion test-suite guard and the
phase requirements for responsive and keyboard use.

---

## Claude's Discretion

- Choose the concrete walkthrough fixture, finding-log format, and order of
  narrow repairs from observed companion behaviour.

## Deferred Ideas

- Comment-history guard residue is unrelated tooling work and remains deferred.
- Battery cadence and pack presentation wait for Phase 46 evidence.
