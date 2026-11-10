---
phase: 62-plane-screen-redesign
plan: 03
subsystem: render
tags: [lettering, anton, text-splitting]
requires: [62-01]
provides: ["split_destination(name, orientation) -> Split(lines, shrink_block)", "normalise_destination()"]
affects: [giant lettering layouts]
tech-stack:
  added: []
  patterns: [metric-driven partition cost, no corrections table]
key-files:
  created:
    - server/plane/render/giant/split.py
    - server/test_giant_split.py
decisions:
  - "Stretch cost uses real Anton width over cap height against a 1120x1160 box with 14 px gaps; floor ln 0.6 and cut penalty 0.12 are named constants"
requirements-completed: [PSR-03]
completed: 2026-11-09
---

# Phase 62 Plan 03: Destination splitter Summary

Deterministic splitter that breaks a destination into 1-3 Anton lines by minimising the worst horizontal stretch from real font metrics, with no table of per-city corrections.

## What was built
- `normalise_destination`: NFC, dash variants to "-", collapsed whitespace, upper case, capped at 80 characters.
- `split_destination(text, orientation)` returns `Split(lines, shrink_block)`. Landscape and names of 3 letters or fewer give one line; multi-word names break only between words (2-3 lines, lines of 2 letters or fewer rejected unless unavoidable); single words use balanced legal syllable cuts (protected digraphs, vowel rule relaxed only when needed, e.g. Metz -> ME / TZ). `shrink_block` is set when the best split still squeezes a line below ln 0.6.
- Tests: 189 cases including the listed examples (all exact), an 80-name property suite (Marseille, Villefranche-sur-Saone, Compagnie Nationale Royale Air Maroc Express, Pau, Aix included), an invented-name rule check, and the worst-stretch bound (1.2; actual worst 1.07).

## Deviations from Plan
- Both tasks were implemented together and landed in one commit (66bd007) instead of one per task, since the syllable branch and property suite are one module. Task 1 and 2 behaviours are covered by separate test groups.
- Marseille splits as MARS / EILLE, as the research predicted; the tuning levers are `CUT_PENALTY` and `SQUEEZE_FLOOR`.

## Verification
pytest (189 passed), ruff, mypy (module is fully annotated and clean; not yet in the mypy list, per instructions), function-size gate (none over 80), comment-history check all clean.

## Self-Check: PASSED
