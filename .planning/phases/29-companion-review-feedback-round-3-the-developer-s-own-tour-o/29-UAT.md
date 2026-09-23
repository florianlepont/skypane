---
status: resolved
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
source: [29-VERIFICATION.md]
started: 2026-09-22T00:00:00Z
updated: 2026-09-22T00:00:00Z
---

## Tests

### 1. CFG-80's 24h-twin hides only on a strict 24h locale determination
expected: The twin must NOT be hidden on a forced-12h-locale device; only a strict `hour12 === false` determination hides it.
result: pass — confirmed by the developer on the deployed app (PR #76, merged and deployed 2026-09-22)

### 2. CFG-81's illustration dialog click behavior in a real browser
expected: |
  On Compagnies, open a known airline's illustration dialog with no query string in the
  URL: Replace renders, the resolve-context block (prefix/first-seen/last-seen/count/
  example callsign) does not. Repeat for a manually resolved entry: Delete also appears.
result: pass — confirmed by the developer on the deployed app (PR #76, merged and deployed 2026-09-22)

### 3. CFG-82's tab-bar fit at 360px and 390px in a real browser
expected: |
  At 360px and 390px, in French and English, the mobile tab bar renders "Compagnies"
  whole with no ellipsis (no `.tab-bar__label` has `scrollWidth > clientWidth`), and
  Compagnies' filter + first gallery row are visible without scrolling past the
  unidentified-prefix list.
result: pass — confirmed by the developer on the deployed app (PR #76, merged and deployed 2026-09-22)

### 4. CFG-83's live page height, refresh-survival, and no-JS reveal
expected: |
  At 390px with the realistic 36-flight fixture, Vols' rendered page height measures
  materially below half the 2026-09-17 audit's 6,710px baseline (~3,355px). Opening
  "Afficher plus", then waiting one 45-second freshness.js refresh cycle, the list
  stays expanded with the link now offering the next page. With JavaScript disabled,
  the Show-more link still reveals more flights.
result: pass — confirmed by the developer on the deployed app (PR #76, merged and deployed 2026-09-22)

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None. All four human-verification items from 29-VERIFICATION.md confirmed passing by the developer directly on the deployed app, after PR #76 merged (squash commit `5961ab7`) and the GitHub production deployment gate was approved and completed successfully. Phase 29 is fully closed.
