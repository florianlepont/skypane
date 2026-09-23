---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
verified: 2026-09-22T22:20:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 2
overrides:
  - must_have: "ASPECT_CAPTION_EXEMPTIONS empties to zero this phase (30-UI-SPEC.md's original prediction)"
    reason: "Developer-approved deviation, documented before verification: DISPLAY_LOOK_INTRO and CALENDAR_URL_HINT are permanent, out-of-scope exemptions; the tuple correctly narrows from 4 to 2, never to 0. Confirmed live: len(ASPECT_CAPTION_EXEMPTIONS) == 2."
    accepted_by: "developer (pre-verification instruction)"
    accepted_at: "2026-09-22"
  - must_have: "CFG-85's literal text \"every row open with scripts blocked\""
    reason: "Developer-approved substitution: the accordion (grouped <details name=\"aspect-rows\">) is mutually exclusive by browser construction, making literal simultaneous multi-open impossible without a script, which would violate the UI-SPEC's own no-script floor. The stronger substituted property (closed rows' radios stay in the DOM and submit; <summary> stays natively activatable; preview stays server-rendered for the saved theme) is proven instead by _the_accordion_is_operable_and_saves_with_scripts_blocked, at 360px, both languages, verdict read back from disk."
    accepted_by: "developer (pre-verification instruction)"
    accepted_at: "2026-09-22"
re_verification: null
---

# Phase 30: Aspect rebuilt — one tile, three rows, one palette, the calendar absorbed, sketch first — Verification Report

**Phase Goal:** Replace the "Frame colours" card (live preview + four-row `colour_usage` radiogroup + three scroll-snap carousels with pagers/dots/disclosures) and the separate "Calendar" card with ONE tile: a live preview, three usage rows (Départs/Arrivées/Vols du calendrier) each showing one swatch and the theme name, a wrapping palette grid of the 18 themes under the open row, the calendar's connection folded under its own row, and "Règles par vol" as a secondary disclosure row — then measure and report Display's page-height delta (CFG-86) honestly, whether or not X6's target is met.

**Verified:** 2026-09-22T22:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Display's Look supersection renders ONE tile "Aspect" (no caption) absorbing both the former Frame-colours card and the separate Calendar card | ✓ VERIFIED | `_aspect_card_html()` defined at `companion/pages/config_page.py:2100`, called once from `render()`'s Display branch (line ~5628); `_frame_colours_card_html` and `calendar_group` have **no surviving `def`** anywhere in the file (`grep -n "^def _frame_colours_card_html\|^def calendar_group"` → no matches). Live render confirms `<h2 class="text-heading" id="aspect-heading">Aspect</h2>` with no `<p class="text-label section-caption">` directly after it. |
| 2 | Three usage rows (Départs/Arrivées/Vols du calendrier) each show ONE swatch + the theme name, opening onto a wrapping 18-theme palette grid — no strip, no scrollbar, no pagers, no dot row, no disclosure-wrapping-the-grid | ✓ VERIFIED | `_usage_row_summary_html()` + `_palette_grid_html()` (config_page.py) render exactly this; `_theme_carousel_html()` has no surviving `def`; CSS confirms no live `.theme-carousel`/`.frame-colours` rule exists (only 3 historical comment mentions remain, zero live selectors — `grep -c "frame-colours\|theme-carousel" companion/static/style.css` → 3, all inside `/* ... */` comment blocks). Palette grid CSS: `display: grid; grid-template-columns: repeat(auto-fill, minmax(64px, 1fr))` (`style.css:10247`), matching the no-strip/no-scrollbar contract. |
| 3 | The calendar's connection status/URL/Disconnect/How-it-works live directly inside the Calendar row (not a separate card, not a further "Gérer" wrapper) | ✓ VERIFIED | `_calendar_connection_html()` is called inside `_aspect_card_html()` and its output is concatenated directly into the Calendar row's body (`calendar_row = _usage_row_html(COLOUR_USAGE_CALENDAR, ..., ... + calendar_connection_row_html)`, config_page.py:2205-2226) — no extra `<details>` wrapper, matching 30-UI-SPEC.md §6's resolved discrepancy. |
| 4 | "Règles par vol" is a fourth, secondary row disclosing the existing rule list/empty-state, a nested "Add rule" disclosure holding the unchanged add-form, and the unchanged How-rules-combine disclosure | ✓ VERIFIED | `rules_row` built at config_page.py:2277-2296 with `extra_class="usage-row--secondary"`, containing `rules_caption_html + rules_list_html + rule_add_html + rules_how_combine_html` in that order, matching the locked structural contract. |
| 5 | The no-JS control contract holds: every palette selection is a native radio cross-submitting via `form="settings-form"`; the preview is server-rendered for the saved theme; a closed row's controls remain reachable and submit with scripts blocked | ✓ VERIFIED | `_the_accordion_is_operable_and_saves_with_scripts_blocked` (companion/test_browser_ux.py) proves the value read back from disk after an operate-submit round trip with scripts blocked at 360px in both languages — this is the CFG-85-approved substitution for the literal "every row open" text (see override above). Independently re-run: PASS (part of 92/95 browser-ux total). |
| 6 | The CSP is untouched, no new script file, no new custom property/colour literal/family/size without an argued exception | ✓ VERIFIED | `ls companion/static/*.js \| wc -l` → 17 (unchanged); `theme-preview.js` is edited in place, not replaced; the one argued exception (10px palette-chip caption, widening the existing sub-scale tier) is documented at the stylesheet header per 30-UI-SPEC.md's own escape hatch. |
| 7 | Every retired carousel CSS rule/Python builder/JS function is grepped for a surviving consumer before deletion | ✓ VERIFIED | Pre-delete consumer counts recorded in 30-04-SUMMARY.md (0 surviving consumers for all 4 retired builders); 30-03-SUMMARY.md records per-constant grep counts for the retired JS selector block; live `grep` today confirms zero live code references to `theme-carousel`/`frame-colours`/`colour_usage`/`usage-panel` (only 3 historical comment mentions in style.css, explaining what used to exist there). |
| 8 | CFG-86: Display's page height at 390px is measured before and after with the same registered instrument, and the delta/verdict is reported honestly without restating the target | ✓ VERIFIED | `30-BASELINE.md` records a genuine same-instrument before/after pair: 3486px → 3266px at 390px (−220px/−6.31%), 3505px → 3454px at 360px (−51px/−1.46%), both via `_display_page_height()`. Verdict stated plainly: "The target is NOT met: 3266px at 390px, 666px over the 2600px target" — this is the developer-pre-approved, expected outcome (CFG-86 is a measurement-and-report requirement, not a target-hitting one), and the report does not narrow the target to fit. |
| 9 | Touch targets are measured (not declared) for every new/changed control, in both themes, at 360px | ✓ VERIFIED | `_the_palette_meets_its_floors_at_360px_in_both_themes` (test_browser_ux.py) prints real hit-tested boxes; independently re-run values confirm ≥44px on every control in both themes (e.g. `theme=dark chip_first: hit=(88, 105)`, `theme=light rule_add_summary: hit=(281, 44)`). |

**Score:** 9/9 truths verified (2 carried as accepted overrides per pre-verification developer instruction; 0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `companion/pages/config_page.py :: _aspect_card_html()` | The merged tile builder | ✓ VERIFIED | Exists (line 2100), called once from `render()`, produces all locked markup (verified directly against source) |
| `companion/pages/config_page.py :: _palette_swatch_html/_palette_chip_html/_palette_grid_html/_usage_row_summary_html/_usage_row_html` | Palette + row renderers | ✓ VERIFIED | All present, called from `_aspect_card_html()` |
| `companion/pages/config_page.py :: _frame_colours_card_html, calendar_group, _theme_carousel_html` | Must be RETIRED | ✓ VERIFIED | No `def` for any of the three exists anywhere in the file |
| `companion/static/theme-preview.js` | Re-scoped to `.aspect-card`, carousel half deleted, hover/focus added | ✓ VERIFIED | `document.querySelector(".aspect-card")` guard present; `openRow()`/`refreshFromCurrentState()` present; `window.SkyPaneLivePreview.refresh()` intact; `mouseover`/`focusin`/`mouseout`/`focusout` hover-follow listeners present (30-08 addition); zero dead carousel functions found in live code |
| `companion/static/style.css` | New `.aspect-card`/`.usage-row`/`.palette`/`.palette-chip`/`.leading-option`/`.rule-add` rules; retired carousel rules gone | ✓ VERIFIED | All new selectors present with rules; zero live `.frame-colours`/`.theme-carousel` selectors remain (3 historical comment-only mentions) |
| `.planning/phases/30-.../30-BASELINE.md` | Genuine before/after CFG-86 reading | ✓ VERIFIED | Present, complete with SHA provenance for both readings, delta table, and honest verdict |
| `companion/test_config_page.py :: _ASPECT_REPIN_LEDGER` + guard | Coverage-gap ledger, fully repaid | ✓ VERIFIED | 19 rows, all `owed_by=""` (repaid in-file), every named replacement function confirmed to exist by direct source inspection |
| `companion/test_browser_ux.py :: _ASPECT_REPIN_LEDGER` + guard | Same, browser harness | ✓ VERIFIED | 6 rows, all `owed_by=""`, every replacement confirmed to exist |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `render()` (Display scope) | `_aspect_card_html()` | direct call, `screens.GROUP_THEME in groups` gate | ✓ WIRED | Confirmed at config_page.py ~line 5628 |
| Palette-chip `<label>` | `theme-preview.js` | `data-preview-src` attribute | ✓ WIRED | Present on every chip; `checkedChipSrc()` reads it off the changed radio's `parentNode` |
| Palette radios | `POST /settings` | `form="settings-form"` cross-submission | ✓ WIRED | Confirmed in rendered markup and proven end-to-end by the scripts-blocked save checks (values reach disk) |
| `dirty-state.js` Cancel handler | `theme-preview.js` | `window.SkyPaneLivePreview.refresh()` | ✓ WIRED | Global preserved under its exact name; re-proven by `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom` (re-pointed to `.palette-chip` by 30-08) |
| `_ASPECT_REPIN_LEDGER` rows (both files) | their named replacement checks | `def` presence, checked by the guard | ✓ WIRED | Independently confirmed by direct source inspection: all 19 + 6 = 25 rows have a live, existing replacement `def`; zero rows still `owed_by` a plan number |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `companion/test_config_page.py` full suite | `server/.venv/bin/python3 companion/test_config_page.py` | `config-page: 276/276 checks pass` | ✓ PASS (independently run) |
| `companion/test_companion_app.py` full suite | `server/.venv/bin/python3 companion/test_companion_app.py` | `companion-app: 317/317 checks pass` | ✓ PASS (independently run) |
| `companion/test_browser_ux.py` full suite | `server/.venv/bin/python3 companion/test_browser_ux.py` | `browser-ux: 92/95 checks pass` | ✓ PASS (independently run; matches orchestrator-confirmed figure and the 3 documented pre-existing, phase-unrelated failures: leave-guard-armed-before-commit, fallback-Save-click-timeout, wake-interval-echo) |
| Ledger repayment (config_page.py, 19 rows) | source-level script resolving each `replacement` name against `def` presence | all 19 present | ✓ PASS |
| Ledger repayment (browser_ux.py, 6 rows) | same | all 6 present | ✓ PASS |
| Live registry swatch-drawing facts (5 banded / 13 solid of 18 themes) | code inspection of `_palette_swatch_html()` reading only `departing_index`/`band_index` | consistent with 30-02-SUMMARY.md's proven mutation-tested check | ✓ PASS (via existing non-vacuous unit check, re-confirmed present) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CFG-85 | 30-01 through 30-08 | Aspect is one tile: preview, three usage rows, wrapping palette, calendar folded in, rules as secondary row, no-JS control contract, CSP untouched, no new script/property | ✓ SATISFIED | All observable truths above verified against live code; two developer-pre-approved deviations documented and carried as overrides |
| CFG-86 | 30-01, 30-08 | Display's page height at 390px measured before/after with the registered instrument, delta and target-met verdict reported honestly | ✓ SATISFIED | `30-BASELINE.md` before/after pair complete with honest verdict ("target NOT met, 666px over") — this is the expected, developer-acknowledged outcome per the task brief, not a gap |

No orphaned requirements: REQUIREMENTS.md maps only CFG-85/CFG-86 to Phase 30, and both are claimed by these plans' frontmatter.

### Anti-Patterns Found

None blocking. Scanned all phase-modified files (`companion/pages/config_page.py`, `companion/static/theme-preview.js`, `companion/static/style.css`, `companion/i18n_fr/display.py`, all three test harnesses) for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers and stub patterns:

- No unresolved `TBD`/`FIXME`/`XXX` markers in any phase-modified production file. The only `TBD` in the phase's own artifacts is `30-BASELINE.md`'s deliberate, plan-scoped placeholder ("After: TBD — filled by 30-08"), which was filled by 30-08 as designed — confirmed the "After" section is now populated with real figures, not left as a dangling TBD.
- No hardcoded-empty-return stubs in any new renderer (`_palette_swatch_html`, `_palette_chip_html`, `_palette_grid_html`, `_usage_row_summary_html`, `_aspect_card_html` all produce substantive, registry-derived output, confirmed by direct execution above).
- No dead carousel/colour_usage functions left in `theme-preview.js` (confirmed by grep of comment-stripped source, matching plan 30-04's own verify script).

### Human Verification Required

None. Every must-have truth resolved to VERIFIED via direct code inspection and independently re-run automated tests (not merely accepted from SUMMARY.md narrative). The two deviations from literal requirement/spec text were pre-approved by the developer before this verification began (per the task's own `<known_developer_approved_deviations>` block) and are recorded as overrides above, not as gaps or human-verification items.

### Gaps Summary

No gaps. All observable truths, artifacts, and key links verified directly against the current codebase:

- `_aspect_card_html()` is live, wired into `render()`, and produces the full locked markup contract (one tile, no caption, four grouped `<details name="aspect-rows">` rows, three 18-entry CSS-drawn palettes, calendar connection folded into its own row, rules as a secondary disclosure row).
- `_frame_colours_card_html()`, `calendar_group()`, and `_theme_carousel_html()` are fully retired (zero surviving `def`s).
- All three test harnesses are green when independently re-run: `config-page: 276/276`, `companion-app: 317/317`, `browser-ux: 92/95` (matching the orchestrator's independently-confirmed figures exactly, including the 3 pre-existing, phase-unrelated floor failures).
- Both coverage-gap ledgers (`_ASPECT_REPIN_LEDGER` in `test_config_page.py` and `test_browser_ux.py`) are fully repaid — every row's `owed_by` is empty and every named replacement check exists live in the file, confirmed by direct source inspection rather than trusting the ledger's own self-report.
- CFG-86 is closed with a genuine, same-instrument before/after measurement and an honest verdict that the target was not met — exactly the outcome flagged as expected and non-blocking in the task brief.
- The two literal-requirement-text deviations (`ASPECT_CAPTION_EXEMPTIONS` not emptying to zero; the accordion's stronger substitute for "every row open with scripts blocked") match their developer-pre-approved descriptions exactly, confirmed against the live code (`len(ASPECT_CAPTION_EXEMPTIONS) == 2`, holding `DISPLAY_LOOK_INTRO` and `CALENDAR_URL_HINT`).

The phase's own SUMMARY.md files document an unusually high number of self-found bugs, escalated red-check inventories, and honest verdicts (particularly 30-03's and 30-04's transparent handling of an under-scoped coverage ledger, and 30-08's transparent CFG-86 closing verdict) — this pattern is evidence of rigor, not risk, and every escalation was independently confirmed to have been resolved by a later plan in this same phase.

---

*Verified: 2026-09-22T22:20:00Z*
*Verifier: Claude (gsd-verifier)*
