---
status: testing
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
source: [42-VERIFICATION.md]
started: 2026-09-29T18:00:57Z
updated: 2026-09-29T18:03:26Z
---

## Current Test

number: 1
name: UPDATING screen is drawn on the glass while the display is off
expected: |
  With the display switched off in the companion, installing a release makes the
  frame show the UPDATING hold screen during the OTA wake. After the update, it
  returns to the display-off screen.
awaiting: user response

## Tests

### 1. UPDATING screen is drawn on the glass while the display is off
expected: The display is off. Install any release other than the running one (for example fw-v1.0.0, then fw-v1.0.1 again). The glass shows UPDATING during the OTA wake. H42-11 proved that the OTA itself runs with the display off, but nobody looked at the glass.
result: [pending]

### 2. The "update failed" push reaches the phone
expected: The phone's notification history holds "Échec de la mise à jour, retour à fw-v1.0.1" (or the English form) from 2026-09-29, sent when the unsigned, tampered, wrong-key and crash bench releases reached Failed. The poll journal shows no send error.
result: pass
reported: "C'est bon, je vois l'ensemble des notifications" (developer, 2026-09-29). All the failure pushes are in the phone's notification history.

## Summary

total: 2
passed: 1
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
