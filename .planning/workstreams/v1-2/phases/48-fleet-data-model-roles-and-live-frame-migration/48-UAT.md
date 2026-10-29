---
status: testing
phase: 48-fleet-data-model-roles-and-live-frame-migration
source: [48-VERIFICATION.md, 48-07-SUMMARY.md, 48-08-SUMMARY.md, 261029-f10-SUMMARY.md]
started: 2026-10-29T12:00:00Z
updated: 2026-10-29T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 3
name: Production deploy migrates the live frame with no visible change
expected: |
  After the next deploy, deploy/activate.sh runs the backup, the dry-run and the real
  migration without stopping, and the frame's next poll still gets the same image and
  the same sleep interval as before. `fleet_cli devices list` on the VPS shows
  94:a9:90:cf:80:08 owned by florian.lepont@yahoo.fr.
awaiting: user response

## Tests

### 1. Dry-run on a copy of the real production state
expected: Exit 0; one device (94:a9:90:cf:80:08) would be added; orphan tokens reported as skipped.
result: pass
evidence: User ran fleet_migrate --dry-run on a fresh copy of devices.json and byos_state.json from the VPS: exit 0, "would add device 94:a9:90:cf:80:08", "skipped 1 token(s) for unregistered device(s)" (the upper-case test MAC DE:AD:BE:EF:00:01).

### 2. Companion browser tests for the Health fleet-fallback signal
expected: Pass in an environment with a Playwright browser.
result: pass
evidence: Full companion suite in the cloud container with SKYPANE_REQUIRE_BROWSER=1 and the installed Chromium: 2610 passed, 3 skipped (non-root permission tests). Health tests: 49 passed, 0 skipped.

### 3. Production deploy migrates the live frame with no visible change
expected: After the next deploy, deploy/activate.sh runs the backup, the dry-run and the real migration without stopping, and the frame's next poll still gets the same image and sleep interval. `fleet_cli devices list` on the VPS shows 94:a9:90:cf:80:08 owned by florian.lepont@yahoo.fr.
result: [pending]

## Summary

total: 3
passed: 2
issues: 0
pending: 1
skipped: 0

## Gaps

[none yet]
