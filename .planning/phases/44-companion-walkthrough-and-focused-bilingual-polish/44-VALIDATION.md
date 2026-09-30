---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
status: planned
nyquist_compliant: false
created: 2026-09-30
---

# Phase 44 Validation Ledger

## Source Audit

| Source | Item | Coverage | Plan or Evidence |
|---|---|---|---|
| GOAL | Owner completes the daily companion flows with walkthrough-proven usability fixes in English and French. | Covered | 44-01 records the route matrix; 44-02 through 44-11 implement bounded approved findings; 44-12 reruns the matrix and obtains owner review. |
| REQ | CMP-01 recorded walkthrough across seven routes, two locales, and three viewports. | Covered | 44-01, 44-12. |
| REQ | CMP-02 every issue has trigger, impact, evidence, and disposition. | Covered | 44-01, 44-12. |
| REQ | CMP-03 changed flows retain bilingual, responsive, semantic, focus, and feedback behaviour. | Covered | 44-02 through 44-11, verified by 44-12. |
| REQ | CMP-04 high-value findings use existing route, page, static, and i18n seams. | Covered | 44-02 through 44-11, audited by 44-12. |
| RESEARCH | Real authentication, isolated production-shaped fixtures, browser rendering, no-JavaScript settings paths, no new packages, and existing architecture seams. | Covered | Every plan retains the existing server/browser test harnesses and no plan installs a dependency. |
| CONTEXT | D-01 through D-03 evidence-first walkthrough and disposition log. | Covered | 44-01 completed; 44-12 finalizes outcomes. |
| CONTEXT | D-04 through D-08 focused high-value scope, existing seams, bilingual/mobile/keyboard proof. | Covered | 44-02 through 44-11, 44-12. |
| CONTEXT | D-09 owner selects fixes before production changes. | Covered | Owner feedback and Direction B were captured before 44-02 onward planning. |
| CONTEXT | D-10 non-technical clarity and D-11 owner feedback/design proposal. | Covered | 44-02 through 44-11 implement the recorded findings; Direction B is in 44-03. |
| CONTEXT | D-12 approved Display flow. | Covered | 44-04 and 44-05 retain the ordered display, appearance, override, and Quiet-hours flow. |
| CONTEXT | D-13 approved Airlines type selector and source/owner distinction. | Covered | 44-07 proves native selection, selected-type content, keyboard operation, and the no-JavaScript fallback. |

## Intentional Deferrals

- Navigation labels, including the proposed General, Status, Advanced settings, and Updates names, remain unchanged until the owner explicitly selects them.
- A new Airlines metadata editor remains out of scope until the owner selects that capability.
- Battery policy, battery-pack decisions, and cadence policy remain Phase 46 work.
- Comment-history guard work remains deferred.

## Per-Plan Verification Map

| Plan | Primary evidence | Required result |
|---|---|---|
| 44-01 | `test_browser_phase44_walkthrough.py` and 44-WALKTHROUGH.md | Complete route matrix and owner-review record. |
| 44-02 | Navigation browser checks at 360/390 px | No redundant nav state; all theme choices fit and operate. |
| 44-03 | Home browser matrix | Direction B reading order and action access at 1280/390/360 px. |
| 44-04 | Display served-page and i18n tests | One preview and understandable configuration hierarchy. |
| 44-05 | Display browser/no-JavaScript tests | Faithful preview and native Quiet hours control. |
| 44-06 | Flights browser action tests | Direct image action works in desktop/mobile with keyboard. |
| 44-07 | Airlines served and browser artwork tests | Types, source/owner distinction, and artwork operations are clear. |
| 44-08 | Health signal and served-page tests | Unidentified airlines are informational and status copy is outcome-first. |
| 44-09 | Status drawing/browser tests | Percentage/Voltage switch and activity band behave responsively. |
| 44-10 | Device settings and poll browser tests | Native persistence and truthful Refresh now feedback. |
| 44-11 | Update served/browser tests | Bench builds absent from offers; confirmation/cancellation retained. |
| 44-12 | Full focused browser aggregate, full suite, owner verification | Phase evidence and visible product judgement are complete. |

## Automated Results

- [ ] Focused browser aggregate passed with Chromium required.
- [ ] Affected served-page, i18n, route, page-context, stylesheet, health, and update tests passed.
- [ ] Full `./scripts/run-all-tests.sh` passed, or an independently reproduced non-phase exception is recorded here.

## Owner Visual Verification

- [ ] Owner reviewed the final authenticated companion in French and English at desktop and phone widths.
- [ ] Owner confirmed Direction B Home, Display, Flights, Airlines, Health, Device, Updates, and navigation are understandable.
- [ ] Owner completed keyboard/focus checks or recorded reproducible follow-up findings.

## Final Disposition

**Status:** Pending execution and owner verification.
