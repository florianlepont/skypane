---
phase: 69
slug: rear-enclosure-for-the-7-3-inch-frame
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-19
---

# Phase 69 — Validation Strategy

> Per-phase validation contract. This is an owner-driven physical phase: no code is touched, so acceptance is by owner-reported, dated rows in `hardware/*.md`. Source: `69-RESEARCH.md`, section "Validation Architecture".

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None for this phase; project pytest/ruff gates are unaffected |
| **Config file** | none |
| **Quick run command** | `git diff --stat -- hardware/` (docs only) |
| **Full suite command** | `./scripts/run-all-tests.sh` (unchanged, must stay green) |
| **Estimated runtime** | not applicable to the phase's own checks |

## Sampling Rate

- **After every task commit:** populated-row check on the table the task fills (rows with a date and "reported by the owner")
- **After every print round:** the owner fills the clearance table before the next print
- **Before `/gsd-verify-work`:** every acceptance row is pass, fail or not done, with a date; the verifier reads owner-reported rows only
- **Rule:** a "pass" cell without a date in the same row counts as not done

## Per-Task Verification Map

| Requirement | Behaviour | Test Type | Automated Command | File Exists | Status |
|-------------|-----------|-----------|-------------------|-------------|--------|
| ENC-01 | Parts fit frame, screws, magnets, battery bay | manual (owner, calliper) | populated-row grep on `hardware/ENCLOSURE-TEST-PRINT-LOG.md` | ❌ W0 (plan 03) | ⬜ pending |
| ENC-01 | Hangs on wall hooks, stand holds | manual (owner, tilt and load test) | none | ❌ W0 (plan 04) | ⬜ pending |
| ENC-01 | USB-C, switch, RESET and buttons reachable | manual | none | ❌ W0 (plan 04) | ⬜ pending |
| ENC-01 | Wi-Fi not degraded | manual + exported RSSI rows (throwaway script, not committed) | none committed | ❌ W0 (plan 04) | ⬜ pending |
| ENC-01 | Documented, BOM, SEED-014 | doc check | `test -f` and heading `grep` | ❌ W0 (plan 05) | ⬜ pending |

## Wave 0 Requirements

- [ ] Replace the vacuous `grep 'pass'` and `grep 'fits|tight|loose'` checks (already present in empty templates) with populated-row checks
- [ ] Enforce the rule that a pass cell carries a date

## Manual-Only Verifications

Every acceptance behaviour of this phase is manual: the owner measures, prints, fits and reports. Claude records only what the owner reports (D-01).

## Validation Sign-Off

- [ ] All tasks have a populated-row check or an owner-report checkpoint
- [ ] No pass without a date
- [ ] `nyquist_compliant: true` set after plans are checked

**Approval:** pending
