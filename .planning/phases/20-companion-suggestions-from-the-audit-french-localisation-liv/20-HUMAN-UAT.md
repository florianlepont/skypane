---
status: partial
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
source: [20-VERIFICATION.md]
started: 2026-09-12T04:38:39+00:00
updated: 2026-09-12T04:38:39+00:00
---

## Current Test

[awaiting human testing]

## Tests

### 1. Push a real battery-low/frame-silent transition end to end with a real ntfy topic pasted into Device -> Notifications, and confirm the phone receives the two paired pushes (D-25..D-28)
expected: A push arrives at the phone with the documented Title/body pair for each of the four transition states, and 'Send a test' reaches the same phone
result: [pending]

### 2. Select each theme chip on Display and confirm the live preview above the grid swaps to that theme rendered with the last real flight, then reload with JavaScript disabled and confirm the preview still shows the saved theme rendered with the last real flight
expected: The .theme-live-preview image src changes on chip click without a page reload; with no JS, the server-rendered image for the currently-saved theme is shown
result: [pending]

### 3. Trigger the calendar-disconnect confirmation and the rule Remove buttons and confirm the native confirm() dialog text is in the current language
expected: A native browser confirm() dialog appears with translated copy before the destructive POST fires
result: [pending]

### 4. With a screen reader, navigate Home's status card and Display's supersections and confirm status_row()'s dot/verdict/detail structure and section_intro_html()'s headings announce sensibly, and that the beforeunload guard's native browser dialog appears when leaving Display with unsaved edits
expected: Each status row announces as one coherent unit (label, verdict, detail); leaving a dirty settings form triggers the browser's own unsaved-changes prompt
result: [pending]

### 5. Confirm the FR/EN switch, the Simple/Full switch and the theme switch each survive across a real browser tab close/reopen (cookie persistence) and across the two different pages of the household (two different browsers/profiles show two different languages at once)
expected: Each browser/profile keeps its own independent language/mode/theme after restart, matching the 'each person in their own language' requirement
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
