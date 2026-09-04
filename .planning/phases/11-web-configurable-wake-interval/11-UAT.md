---
status: testing
phase: 11-web-configurable-wake-interval
source: [11-VERIFICATION.md]
started: 2026-09-04T06:50:00Z
updated: 2026-09-04T06:50:00Z
---

## Current Test

number: 1
name: Wake interval field — real-browser visual/interaction check
expected: |
  At 375px and >=960px viewports, in both light and dark mode: the Wake
  interval group renders last (below Quiet hours) with the same card
  treatment as its siblings; the number input's spinner is legible and
  doesn't overflow at 375px; the tap target is >=44px tall; an unsaved
  field shows the "Uses server default" placeholder, not a number; editing
  it raises the floating save bar naming "Wake interval"; the focus ring
  matches every other input's accent outline.
awaiting: user response

## Tests

### 1. Wake interval field — real-browser visual/interaction check
expected: |
  All six checks from 11-VERIFICATION.md's human_verification entry pass
  against 11-UI-SPEC.md's locked Interaction Contract, with no visual
  regression to the four existing settings groups:
  (1) group renders last, below Quiet hours, same card surface/heading/
  caption treatment as its siblings;
  (2) native number input's stepper/spinner is legible and doesn't
  overflow or crowd the card at 375px;
  (3) the field's tap target is comfortably >=44px tall;
  (4) with nothing saved, the placeholder reads "Uses server default" in
  the browser's muted placeholder tone, not a number;
  (5) editing the field raises the floating save bar exactly as editing
  any other group does, and the bar's section count names Wake interval;
  (6) the focus ring matches every other input's accent outline.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
