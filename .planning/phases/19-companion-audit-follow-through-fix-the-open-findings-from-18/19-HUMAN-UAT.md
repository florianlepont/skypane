---
status: partial
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
source: [19-VERIFICATION.md]
started: 2026-09-11T17:12:08+00:00
updated: 2026-09-11T17:12:08+00:00
---

## Current Test

[awaiting human testing]

## Tests

### 1. Health live fetch-and-swap refresh (D-02/A-20)
expected: Open Health and leave it for two minutes: the page never navigates, 'Updated HH:MM' advances, an open 'More details' disclosure stays open across an update, keyboard focus is not lost, the sparkline still responds to hover/arrow-keys after an update, a typed registry filter query survives an update, the nav Health dot matches the on-page banner, Pause stops updates and Resume restarts them, and the browser console shows no CSP violation.
result: [pending]

### 2. Flights table responsive/keyboard behaviour (D-19/D-20)
expected: At 1280px the table fits without horizontal scroll, or scrolls with a visible focus ring when tabbed to; a copy button shows 'Copied' beside the icon for ~1.5s and announces the row's callsign.
result: [pending]

### 3. Poll-cooldown countdown and CSP (D-18/A-35)
expected: Loading Device during a poll cooldown, the countdown ticks down and re-enables the button with no CSP console violation; triggering poll on a zero-cooldown page still disables the button and reads 'Polling…'; every Display theme chip still shows its colour swatch.
result: [pending]

### 4. Sparkline fixed y-range and Device tile staleness colour (D-04/D-05)
expected: With 40 days of battery history, the sparkline y-axis reads 3000 mV / 4200 mV and a near-flat series draws near-flat; a device that checked in minutes ago shows the Device tile green at a 30s cadence and amber past five minutes.
result: [pending]

### 5. Health plain-language read-aloud (D-06/A-24)
expected: Reading the whole Health page aloud as a household member, no sentence should require the source code to parse; hovering each tile label reveals its technical term.
result: [pending]

### 6. Settings field-level error repopulation (D-07/A-25)
expected: On Display, change the theme, clear the quiet-hours Start field, and save: the page returns with the new theme still selected, an error under the Start field, no generic banner, and nothing saved.
result: [pending]

### 7. Airlines gap strip and edit-gated lightbox (D-21/D-22)
expected: /airlines with seeded unresolved prefixes shows the strip first with its sentence, curated cards only below; a card's lightbox shows no replace/upload/delete controls; /airlines?edit=1 shows all three; a gap card's back link returns to Airlines.
result: [pending]

### 8. Quiet-hours presets, unload guard, no-JS fallback (D-09/D-10/D-14)
expected: Tapping 'Work day' fills both time inputs and shows the save bar; tapping 'Always on' unticks the enable checkbox and keeps the times; triggering poll with unsaved edits prompts a browser confirmation; Save does not prompt; with JS disabled the bottom Save button is visible and works.
result: [pending]

### 9. Calendar disconnect confirmation and radiogroup screen-reader semantics (D-08/D-12)
expected: With a calendar connected, Device shows a standalone Disconnect button (no checkbox); clicking raises a native confirm; declining changes nothing, accepting disconnects and flashes; with JS disabled it lands on a confirmation page; with a screen reader, theme chips and runway cards announce as named radio groups with their hints read.
result: [pending]

### 10. Runway labels, next-wake caption agreement, Edit-artwork link, screen selector absence (D-11/D-13/D-22/D-23)
expected: Runway cards read 'Runway 3 (07/25)' etc.; Home shows 'Next wake ≈ HH:MM' in Paris local time (nothing when never checked in); Device's 'Applies on the next scheduled poll' captions carry the same figure; Device's 'Edit artwork' link opens Airlines with artwork forms available; no screen selector is visible with one registered screen type.
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0
blocked: 0

## Gaps
