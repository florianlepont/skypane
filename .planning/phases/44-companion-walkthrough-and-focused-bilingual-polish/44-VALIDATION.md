---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
status: validated (owner confirmation, 2026-10-04)
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
| 44-12 | Full focused browser aggregate, full suite, owner verification | Aggregate 338 passed, full suite 3481 passed; owner verification pending. |

## Automated Results

Run 2026-10-03 on the Phase 44 working tree (base `0d05a73a` plus the
retired-test cleanup in the closing commit), Chromium required.

- [x] Focused browser aggregate passed with Chromium required.
  `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py companion/test_browser_ux_01.py companion/test_browser_ux_02.py companion/test_browser_ux_03.py companion/test_browser_ux_04.py companion/test_browser_ux_health_drawings.py companion/test_browser_update.py companion/test_i18n.py companion/test_route_table.py companion/test_page_context.py companion/test_stylesheet_structure.py companion/test_health_signals.py companion/test_update_page.py`
  gave **338 passed**. This includes the 42-case English/French 1280/390/360
  route matrix, keyboard/focus, scripts-blocked settings, image, chart and
  update flows.
- [x] Affected served-page, i18n, route, page-context, stylesheet, health, and
  update tests passed (same 338-test run).
- [x] Full `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`: **3481
  passed, 8 skipped**, coverage 95.12% (floor 93.0%). The 8 skips are
  environment-only (root ignores permission bits: 6; local openssl cannot
  backdate a certificate: 1; root ignores directory permission bits: 1). No
  retired-contract skip remains.
- [x] `ruff check .`, `mypy`, `scripts/check_comment_history.py check`, and
  `scripts/check_function_size.py check --max 80 server stub-server` all green.
- Browser tests ran against a scratch `PLAYWRIGHT_BROWSERS_PATH`; no browser
  install was performed by this plan.

## Retired-contract test cleanup

41 skipped tests for retired Home, Display, Flights and Health contracts
were deleted from `test_config_page_04b.py` (19), `test_browser_ux_03.py` (9),
`test_view_pages_04.py` (7), `test_browser_ux_01.py` (3) and
`test_view_pages_03.py` (3), together with their now-unused helpers. Dead Home
code (`_status_tiles_html`, `_hero_html`, their copy constants, and orphaned
French catalogue entries) was removed. Delivered behaviour is covered by the
Direction B, Display, Flights, Health and Update tests listed in the map above.
The Frame strip component, `quick-switch.js` and `/quick/display` were left in
place and are recorded as an open decision in 44-WALKTHROUGH.md.

## Owner Visual Verification

Owner visual verification status: **validated by the owner on 2026-10-04**.

On 2026-10-04 the owner stated that they had tested the deployed companion
themselves before this closing step ("tu peux la valider, j'ai testé avant")
and asked for Phase 44 to be marked validated. That statement is the only
evidence for this section: no per-item notes, screenshots or recordings of the
owner's session exist, and none are claimed here.

The checklist below was written on 2026-10-03 for the Phase 44 working tree.
Later companion redesigns (Flights boarding-pass cards and filter chips, Home
recent-flight tiles, Airlines tiles, toasts and the Display look card) have
since changed several of the screens it names, so it no longer describes the
deployed result item by item. The owner validated the deployed result, not
this checklist. The boxes are therefore ticked on the strength of that
statement alone, not as separate observations.

- [x] Owner reviewed the final authenticated companion in French and English at desktop and phone widths (owner statement, 2026-10-04).
- [x] Owner confirmed Direction B Home, Display, Flights, Airlines, Health, Device, Updates, and navigation are understandable (owner statement, 2026-10-04).
- [x] Owner completed keyboard/focus checks or recorded reproducible follow-up findings (owner statement, 2026-10-04; no follow-up findings were supplied).

Original checklist for the owner (kept for the record; do not install production firmware for this review):

1. Log in in French, then switch to English; repeat at desktop and 360-390 px.
2. Home: frame signal and recent flights are the first useful reading; open a row image.
3. Display: change an appearance and Quiet hours, save; preview, swatches and saved result are clear.
4. Flights and Airlines: direct "View picture" action, aircraft-type selector (Transavia shows both types), "From SkyPane" versus "Your changes", artwork action wording.
5. Health: healthy result reads stronger than detail text, Percentage/Voltage switch, unidentified airlines do not look like an alarm, plain section title wording.
6. Device and Updates: Wake interval, Diagnostic LED, Refresh now feedback; installed-version summary and release list hierarchy.
7. Tab through every changed action: visible focus indicator, reachable.
8. Decide the open items listed in 44-WALKTHROUGH.md.

Item 8 is not covered by the owner's statement: the open decisions listed in
44-WALKTHROUGH.md (navigation labels, Airlines metadata editor, shared
freshness indicator, update-cadence explanation, and the unrendered Frame
strip / quick-switch / `/quick/display`) stay open and are carried forward, not
decided by this closing.

## Final Disposition

**Status:** Validated on the owner's confirmation of 2026-10-04. Phase 44 is
closed: 12/12 plans, automated evidence above, owner validation as described.
`nyquist_compliant` stays `false`: the owner step is a single statement, not a
per-requirement observation record.
