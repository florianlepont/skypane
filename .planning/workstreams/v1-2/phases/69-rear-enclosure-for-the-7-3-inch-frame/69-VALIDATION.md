---
phase: 69
slug: rear-enclosure-for-the-7-3-inch-frame
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-19
---

# Phase 69 — Validation Strategy

> Per-phase validation contract. Owner-driven physical phase: no code is touched, so acceptance is by owner-reported, dated rows in `hardware/*.md`. Source: `69-RESEARCH.md`, section "Validation Architecture".

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None for this phase; project pytest/ruff gates are unaffected |
| **Config file** | none |
| **Quick run command** | `git diff --stat -- hardware/` (docs only) |
| **Full suite command** | `./scripts/run-all-tests.sh` (unchanged, must stay green) |

## Sampling Rate

- **After every task:** populated-row check on the table the task fills (rows with a date and "reported by the owner"); empty templates are checked to hold zero dated rows so the later checks are not vacuous
- **After every print round:** the owner fills the clearance table before the next print (gates in the test-print log)
- **Before `/gsd-verify-work`:** every acceptance row is pass, fail or not done, with a date; the verifier reads owner-reported rows only
- **Rule:** a "pass" cell without a date in the same row counts as not done

## Per-Task Verification Map

| Plan | Requirement | Behaviour | Test Type | Automated Command | Status |
|------|-------------|-----------|-----------|-------------------|--------|
| 02 closeout | ENC-01 | Records agree; decisions and open questions recorded | doc check + owner reply | wood/glass filter, table-column awk check, dated rows for the calliper and mat recheck, anchored no-ID guard | pending |
| 03 log, survey, round A | ENC-01 | Shim and coupon fit; five frames surveyed | manual (owner, calliper) | empty-template check (zero dated rows), then populated survey and clearance rows with `value; fit; verdict; date` | pending |
| 04 rounds B and C, battery gate | ENC-01 | Tray, lid, stand fit; screw reuse; battery connected last | manual (owner) | populated Print record rows B and C, go or no-go rows, BAT rows with pass or fail, date, owner phrase | pending |
| 05 Wi-Fi protocol and baseline | ENC-01 | Protocol written; baseline A1 before any enclosure | manual + exported rssi values | empty-template check, dated A1 row, raw readings present, no MAC pattern | pending |
| 06 validation and Wi-Fi verdict | ENC-01 | Hangs, stands, reachable controls, Wi-Fi not degraded | manual (owner) + throwaway computation on recorded readings | 16 rows V1 to V16, dated pass or fail rows, V8 not pass without V6 and V7, verdict bullets with a number and a dated acceptance | pending |
| 07 final files and docs | ENC-01 | Files stored, assembly note, BOM, seed | doc check | `ls` of export folder, headings, no mat-cut or printer line, seed heading and five pointers | pending |

## Wave 0 Requirements

- [x] Vacuous `grep 'pass'` and `grep 'fits|tight|loose'` checks replaced by populated-row checks (in plans 03 to 07)
- [x] Rule that a pass cell carries a date enforced by the verify lines

## Manual-Only Verifications

Every acceptance behaviour of this phase is manual: the owner measures, prints, fits and reports. Claude records only what the owner reports.

## Validation Sign-Off

- [x] All tasks have a populated-row check or an owner-report checkpoint
- [x] No pass without a date
- [x] `nyquist_compliant: true` set after the plans were rewritten

**Approval:** planner, 2026-11-19, revision 1 (checker re-run pending)
