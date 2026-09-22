---
status: testing
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
source: [29-VERIFICATION.md]
started: 2026-09-22T00:00:00Z
updated: 2026-09-22T00:00:00Z
---

## Current Test

number: 1
name: CFG-80's 24h-twin hides only on a strict 24h locale determination
expected: |
  On a real device with the OS region forced to a 12h locale (e.g. macOS/iOS set to
  United States), open /display and observe each quiet-hours time field's 24h twin
  (data-normalised-time). The twin must NOT be hidden — value-controls.js's load-time
  pass only hides it on a strict Intl.DateTimeFormat(...).resolvedOptions().hour12 ===
  false. Any other resolved value must leave it visible.
awaiting: user response

## Tests

### 1. CFG-80's 24h-twin hides only on a strict 24h locale determination
expected: The twin must NOT be hidden on a forced-12h-locale device; only a strict `hour12 === false` determination hides it.
result: [pending]

### 2. CFG-81's illustration dialog click behavior in a real browser
expected: |
  On Compagnies, open a known airline's illustration dialog with no query string in the
  URL: Replace renders, the resolve-context block (prefix/first-seen/last-seen/count/
  example callsign) does not. Repeat for a manually resolved entry: Delete also appears.
result: [pending]

### 3. CFG-82's tab-bar fit at 360px and 390px in a real browser
expected: |
  At 360px and 390px, in French and English, the mobile tab bar renders "Compagnies"
  whole with no ellipsis (no `.tab-bar__label` has `scrollWidth > clientWidth`), and
  Compagnies' filter + first gallery row are visible without scrolling past the
  unidentified-prefix list.
result: [pending]

### 4. CFG-83's live page height, refresh-survival, and no-JS reveal
expected: |
  At 390px with the realistic 36-flight fixture, Vols' rendered page height measures
  materially below half the 2026-09-17 audit's 6,710px baseline (~3,355px). Opening
  "Afficher plus", then waiting one 45-second freshness.js refresh cycle, the list
  stays expanded with the link now offering the next page. With JavaScript disabled,
  the Show-more link still reveals more flights.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
