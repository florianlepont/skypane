---
phase: 49-per-hardware-ota-registry
plan: 02
subsystem: ota
tags: [firmware, signing, decision, documentation]
status: complete
requires: []
provides:
  - "firmware/SIGNING.md Decision record (OTA-03): option S recorded"
affects: [49-10]
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - firmware/SIGNING.md
decisions:
  - "OTA signing: option S, one signing key for all hardware types (status quo), decided 2026-10-29 by Florian Lepont (project owner). No combination with P, M or N. No new key created."
  - "No cable flash for the live frame (xiao-ee02-13in3-spectra6). The future second board's first cable flash is signed with the existing key."
  - "Revisitable (for example to per-type keys, option P) before the second board is first cable-flashed (Phase 58), since the first image on a new board is chosen at its cable flash."
metrics:
  tasks: 3
  completed: 2026-10-29
requirements: [OTA-03]
---

# Phase 49 Plan 02: OTA signing decision record Summary

The owner chose option S (one signing key for all hardware types, status quo) on 2026-10-29. The choice is recorded in the "Decision record (OTA-03)" section of firmware/SIGNING.md with date, decider, cable-flash note and key custody (by reference to the existing key-generation procedure). This is a real decision, not a deferral.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 Options and decision record scaffold | e6af5d89 | Pending record with S/P/M/N matrix |
| 2 Owner decision checkpoint | n/a | Owner answered: option S |
| 3 Record the decision | 68dff1f8 | Status, owner fields, consequences for the build |

## Decision

- Option: S only.
- Cable flash: none for the live frame; the second board's first cable flash uses the existing key.
- Custody: no new key; the existing `firmware-signing` environment secret and the developer's offline backup, per the document's procedure.
- Consequences for the build: pin the existing public key for the artifact-key check; no per-type keys or per-type key paths.

## Requirement status

OTA-03 is NOT complete. This plan only records the decision. Device-side verification (the running firmware rejecting wrongly signed or unsigned OTA images, result-token round trip, wrong-hardware rollback) remains for plan 49-10 and needs a bench unit. OTA-03 was deliberately not marked complete in REQUIREMENTS.md.

## Deviations from Plan

- The plan said to commit SIGNING.md together with the SUMMARY; per the orchestrator's instruction they are two separate commits.
- The decision text was reworded slightly in the record (no plan or decision IDs) to respect the comment-history rule.

## Verification (run)

- `! grep -v '^#' firmware/SIGNING.md | grep -q "PENDING OWNER DECISION"`: exit 0.
- `sh firmware/tests/check_production_config.sh static`: PASS.
- `python3 scripts/check_comment_history.py check`: no output (no violations reported).
- Not run: pytest suites, firmware host tests (documentation-only change).

## Self-Check: PASSED

firmware/SIGNING.md modified and committed (68dff1f8); no pending marker remains.
