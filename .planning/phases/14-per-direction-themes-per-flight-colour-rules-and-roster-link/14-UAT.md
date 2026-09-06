---
status: testing
phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link
source: [14-VERIFICATION.md]
started: 2026-09-06T16:35:00Z
updated: 2026-09-06T16:35:00Z
---

## Current Test

number: 1
name: End-of-phase no-JS browser confirmation of the arrivals grid and the rules editor
expected: |
  With JavaScript disabled in a real browser, on the companion Settings page:
  1. The arrivals theme grid is present in the page and reachable.
  2. Ticking "use a different theme for arrivals" reveals the second chip grid; unticking hides it.
  3. A theme can be selected in the arrivals grid and saved through the normal Save button.
  4. Saving with the checkbox unticked genuinely clears a previously-set arrivals theme.
  5. A colour rule can be added, an existing key re-added (reporting "replaced", not "added"), and deleted.
  6. Adding or deleting a rule never makes the "Unsaved changes" bar appear — those are immediate actions outside the main form.
  Keyboard tab order through both grids and the rules form is sensible, and focus is visible throughout.
awaiting: user response

## Tests

### 1. End-of-phase no-JS browser confirmation of the arrivals grid and the rules editor
expected: All six behaviours above hold in a real browser with scripting disabled. The automated tests already prove the raw HTTP POST semantics and the emitted markup, but they cannot observe real browser rendering, the CSS-only reveal in practice, keyboard focus order, or focus visibility. This project has a standing lesson that computed-style checks alone once missed a real mobile navigation defect, which is why this is verified by a human rather than asserted in a harness.
result: [pending]

### 2. Security pass over the two new rules routes and the rules registry
expected: `/gsd-secure-phase 14` confirms the STRIDE threat registers recorded across the five plans are honestly mitigated in the shipped code. The surface is the two new POST routes, add and delete, plus the `colour_rules.json` registry in the state directory. Particular attention to the positive allowlist applied per key kind at write and again on every read, the theme id membership test against the registry, the entry-count cap, and the fact that no filesystem path is ever constructed from a rule value.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
