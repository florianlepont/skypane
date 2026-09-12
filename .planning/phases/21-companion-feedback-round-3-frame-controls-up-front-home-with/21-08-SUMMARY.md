---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 08
subsystem: docs
tags: [design-system-skill, headless-sweep, validation-gate, closing-plan]

# Dependency graph
requires: ["21-02", "21-03", "21-05", "21-06", "21-07"]
provides:
  - ".claude/skills/sketch-findings-skypane/SKILL.md — the Phase 21 entry in Folded-In Work and the corrected Navigation/Data-and-tables design-direction paragraphs, every superseded phase-20 statement marked SUPERSEDED in place"
  - ".claude/skills/sketch-findings-skypane/references/control-density.md — the small grey secondary button (.calendar-disconnect-btn, R-09), .frame-colours__row's directly-met 44px floor, the Flights row-toggle as an existing register entry"
  - ".claude/skills/sketch-findings-skypane/references/data-density.md — the Flights table's five-column shape, its scoped stacked-cell exception, the dot-only Corroboration column and the detail row's no-JS floor, with the 9→7 entry marked SUPERSEDED"
  - ".claude/skills/sketch-findings-skypane/references/mobile-navigation.md — the two-switch footer (SUPERSEDING Phase 20's three) and the new .nav-status reminder line in both renderers"
  - "21-VALIDATION.md — the filled Per-Task Verification Map (22 rows across plans 21-01..21-08), the answered Manual-Only table, and nyquist_compliant: true"
affects: []

tech-stack:
  added: []
  patterns:
    - "headless Playwright sweep (pinned Chromium executablePath, the real /ui-lang form control, a disposable state-dir copy) run against the executor's own worktree code on a dedicated port (8651), not the orchestrator's port (8643)"
    - "second-context javaScriptEnabled:false comparison to prove a no-JS floor's exact panel count, rather than reading the server-rendered HTML by eye"

key-files:
  created: []
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md
    - .claude/skills/sketch-findings-skypane/references/mobile-navigation.md
    - .planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-VALIDATION.md

key-decisions:
  - "Verified the skill's 'zero new custom properties, zero new colour literals, zero new accent consumers' claim directly against `git diff 614d41e..HEAD -- companion/static/style.css` before writing it, rather than restating the plan's own assertion unchecked — confirmed true."
  - "Left the mobile-navigation.md reference file's stale '4-tab set' claim untouched — it predates phase 21 (a Phase 18 staleness gap, not something this plan's own changes caused) and is out of this plan's stated scope (only the footer switch count and the nav-status placement were named for this file); documented here rather than silently fixed, per the SCOPE BOUNDARY rule."
  - "Ran every Manual-Only Verifications item that a real headless browser could exercise (Frame colours row/chip click, the Flights detail-row toggle, the strip's return_to redirect) rather than deferring them to 'not runnable' by default — a browser genuinely runs in this worktree, so 'not runnable' is reserved for the one item that is honestly blocked (the calendar-disconnect confirm(), since the seed has no connected calendar and connecting one would require a real external feed URL)."
  - "Found and fixed two false FAILs in my OWN sweep scripts during the sweep (a language-specific data-dirty-section selector that only matched English, and a chip-click test that picked a chip whose value happened to already match the displayed theme) — both were test-script bugs, not application defects, confirmed by rerunning with a corrected selector/a genuinely different chip value. Documented here so the zero-defects claim below is traceable to what was actually investigated, not merely asserted."

requirements-completed: [CFG-19, CFG-20, CFG-21, CFG-22, CFG-23, CFG-24]

# Metrics
duration: ~120min
completed: 2026-09-12
---

# Phase 21 Plan 08: Closing — design-system skill, FR/EN headless sweep, suite + ruff gate, validation map Summary

**Closes phase 21: the design-system skill now documents the Frame strip, the nav state reminder, the Frame colours card, the merged calendar tile, the compact Flights table and the small grey secondary button (with every superseded phase-20 statement marked SUPERSEDED in place, not deleted); a real headless Chromium sweep at 1280/390 px in EN/FR found zero overflow, zero inline script, zero 404s and zero UI-SPEC checklist failures; the full suite is green apart from the five documented root-sandbox failures, ruff is clean, and 21-VALIDATION.md's per-task map is filled with `nyquist_compliant: true`.**

## Performance

- **Duration:** ~120 min
- **Started:** 2026-09-12
- **Completed:** 2026-09-12
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Merged `claude/web-companion-audit-ux-refactor-bqx7si` (fast-forward, `614d41e` → `82e4897`) at start, per the launch instructions — confirmed both orchestrator polish commits (`d9e0338`: recent-flights keeps one three-column shape at every width, the strip's next-update headline uses the heading size; `82e4897`: the Frame colours usage panels sit in a full-width `.frame-colours__panels` cell under the preview/rows pair) were present and documented both in the skill.
- `SKILL.md`: updated the "Current as of" line to Phase 21; corrected the Navigation paragraph in place (three-switch footer → two, SUPERSEDED; the new `.nav-status` reminder and `.dot--off`); corrected the Data-and-tables paragraph in place (the 9→7 Flights merge → five columns plus a detail row, SUPERSEDED, with the scoped stacked-cell exception and the dot-only Corroboration column documented); appended one Phase 21 entry to Folded-In Work covering all six shipped areas plus both orchestrator polish commits; updated the `findings_index` table rows for Mobile Navigation and Data Density and the Control Density register note.
- `references/control-density.md`: added the small grey secondary button (`.calendar-disconnect-btn`, R-09 — the first named secondary-button treatment in a codebase with no `.btn` family), `.frame-colours__row`'s directly-met 44px row-as-label (not a trade), and the Flights row-toggle's 30px geometry as an existing register entry, not a new one; updated the Origin line.
- `references/data-density.md`: marked the 06.6.1-era 7-column Flights table SUPERSEDED in place; added a full "Flights table recompacted to five columns plus a detail row" section (the scoped stacked-cell exception, measured against the real 880px budget; the dot-only Corroboration column; the scoped 8px padding register; the detail row's own no-JS floor and its class-at-load collapse pattern); updated "What to Avoid" with the narrow stacking exception and updated the Origin line.
- `references/mobile-navigation.md`: marked the three-switch footer SUPERSEDED in place (back to two: language, theme, Sign out); added the `.nav-status` reminder's exact placement in both renderers, its dot vocabulary addition (`.dot--off`), its contrast pairing and its `page_shell(device_config=None)` degrade-to-nothing behaviour; updated the Origin line.
- Verified the "zero new custom properties, zero new colour literals, zero new accent consumers" claim directly against `git diff 614d41e..HEAD -- companion/static/style.css` (no `--custom-property` or bare hex literal additions found) before writing it into the skill, rather than restating the plan's own assertion unchecked.
- Ran the FR/EN headless sweep (see "Headless Sweep" below) — zero overflow, zero inline script/handler, zero 404s (including `/static/flight-rows.js`), and every line of 21-UI-SPEC.md's Verification Checklist answered from real DOM assertions and screenshots, not assumed.
- Ran the full local suite and ruff — exactly the five documented pre-existing root-sandbox failures, nothing else; ruff clean.
- Filled 21-VALIDATION.md's Per-Task Verification Map (22 rows, one per task across plans 21-01..21-08, each with a real `<automated>` command derived from that plan's own file), answered every Manual-Only row, ticked the Validation Sign-Off checklist, and set `nyquist_compliant: true`.

## Task Commits

1. **Task 1: Update the design-system skill to the shipped phase-21 contract** - `e960ec0` (docs)
2. **Task 2: The FR/EN headless sweep at 1280 px and 390 px** - `169acfa` (docs)
3. **Task 3: The phase gate — full suite, ruff, and the filled validation map** - `b3f40f6` (docs)

_This SUMMARY.md is committed separately as the final commit of this plan's own execution, per the launch instructions._

## Headless Sweep

**Service:** started from this worktree's own code, `companion.app --port 8651 --state-dir <a disposable copy of the scratchpad's seeded state>` (NOT port 8643, the orchestrator's port) — `SKYPANE_COMPANION_PASSWORD=test1234 SKYPANE_COMPANION_INSECURE_COOKIES=1 SKYPANE_SLEEP_S=600`.

**Commands run** (all from the scratchpad, against `http://127.0.0.1:8651`):
- `node sweep-21-08.js sweep21-08` — EN/FR × 1280/390 px × six pages (`/`, `/display`, `/device`, `/flights`, `/airlines`, `/health`); asserts no horizontal overflow, no inline `<script>`/handler attribute, no HTTP status ≥ 400 (including `/static/flight-rows.js`, which returned 200 in every combination); the Flights `.data-table-wrap` `scrollWidth`/`clientWidth` equality at 1280 px in both languages; the strip as the first element after `.page-header` on `/` and `/display`; the sidebar's `.nav-status` presence; a whole-page scan for `simple`/`ui-mode` strings and for a Health "Pause updates"/"Suspendre" button (none found); the Frame colours card's exactly-one-visible-panel-with-script vs. exactly-four-visible-panels-without-script contrast (a second `javaScriptEnabled: false` context).
- `node sweep-21-08-checklist.js` — targeted assertions against 21-UI-SPEC.md's own Verification Checklist rows not already covered above (Home's `.status-card`/`.home-hero` absence and three-tile count, Display's single quick-action pair and single Frame colours card, no arrivals checkbox, Calendar as exactly one page-section, FR header/row-label/nav-reminder text, no Health pause button, Airlines' unconditional upload affordance).
- `node sweep-21-08-interactive.js` — the Manual-Only items a real browser can exercise: Frame colours row-click → panel swap (no reload) → chip-click → preview-src change; the Flights "More" toggle's `aria-expanded`/class/text-swap sequence; both strip switches' `return_to` redirect back to the page they were pressed on (Home → `/`, Display → `/display`, both restored to their prior state afterward); a native `confirm()` check for Calendar Disconnect (not runnable — no calendar connected in the seed).

**Screenshots** (scratchpad, not committed — `/tmp/claude-0/-home-user-skypane/2394b3be-2435-5257-ae1a-ee5bff8ac6e0/scratchpad/sweep21-08/`): `{desk-en,desk-fr,mobile-en,mobile-fr}-{root,display,device,flights,airlines,health}.png`, plus `report.txt`, `findings.txt`, `checklist-final.txt`, `interactive.txt`.

**Result: zero FAILs across every automated assertion.** Two false FAILs surfaced and were traced to bugs in this executor's own sweep scripts (not the application) — see `key-decisions` above — and both were fixed and re-verified before being counted as PASS.

### Verification Checklist — per-line-item table

| UI-SPEC checklist line | Verdict | Evidence |
|---|---|---|
| Home order: header → strip (accent surface, next-update largest text) → 3 tiles → Health link → picture/flights ≈3:2 | PASS | `desk-en-root.png`/`desk-fr-root.png`; `strip-first-after-header=ok`; `.home-picture-row` grid-template-columns `513.594px 342.391px` (≈3:2) |
| No `.status-card`, no `.home-hero` anywhere in rendered HTML | PASS | checklist.js: `no .status-card class` / `no .home-hero class`, all 4 combos |
| No quick-action widget outside the strip | PASS | checklist.js: `quickActionCountOutsideStrip === 0`, all 4 combos |
| Home (390 px): one column, strip cells each on their own line, tiles stacked, picture above flights | PASS | `mobile-en-root.png`/`mobile-fr-root.png`; strip cell tops `[298, 421, 545]` (distinct lines); `.home-picture-row` columns `342px` (single column) |
| Display: strip renders identically above "Look" | PASS | `strip-first-after-header=ok` on `/display`, both languages |
| Exactly one `.quick-action--on`/`--off` pair on Display, inside the strip | PASS | `quickActionOutsideStrip === 0`, all 4 combos |
| Exactly one "Frame colours" card; row click swaps panel + preview | PASS | `frameColoursCards === 1`; interactive.js row-click/chip-click sequence, PASS |
| No "Use a different theme for arrivals" checkbox, no Calendar-card chip grid, no separate "Flight colours" card | PASS | `arrivingCheckbox === false`, all 4 combos |
| Calendar is one `.page-section`, no second card | PASS | `calendarPageSections === 1` (language-agnostic h2-text match), all 4 combos |
| Flights table: no horizontal scrollbar at 1280 px, either language | PASS | `.data-table-wrap` `scrollWidth===clientWidth===880` in EN and FR |
| Corroboration column shows a dot with no adjacent visible word | PASS | visual inspection, `desk-fr-flights.png` — dot-only, `Plus` toggle at row end |
| Nav reminder in both renderers, dot + word, link, no button/form | PASS | `.nav-status` present in sidebar at 1280 px (all 4 combos); mobile dropdown rendering shares the same `layout.nav_status_html()` body (verified by code inspection, 21-04-SUMMARY.md) |
| FR Flights headers: Quand/Vol/Trajet/Sens/Corroboration | PASS | `["Quand","Vol","Trajet","Sens","Corroboration","Détails"]` |
| FR Frame colours rows: Départs/Arrivées/Vols du calendrier/Règles par vol; unset → "Comme les départs" | PASS | exact match on all four row labels; "Comme les départs" found |
| FR nav reminder fully French, no stray English word | PASS | `"Écran allumé · Heures calmes désactivées"` — no "on"/"off" |
| No inline `<script>`, no 404 for any static asset, no `simple_mode`/`/ui-mode` string | PASS | 0 inline-script/handler matches and 0 HTTP ≥ 400 responses across all 24 page-loads (4 combos × 6 pages); 0 `simple`/`ui-mode` string matches |
| No "Pause updates" button on Health | PASS | 0 matches across all 4 combos |
| Airlines: naming a new prefix's Step B shows the upload zone without `?edit=1` | PASS | `/airlines?resolve=XYZ` (no `edit` param) rendered a real `input[type=file]` drop zone — confirmed by an end-to-end click-through (name "Totally New Test Airline XYZ", save, screenshot) |

## Harness Counts (before → after, this plan)

No `check(...)` call sites were added or removed by this plan (it owns no `companion/`/`server/` file) — the counts below are the phase-start baseline vs. the live values this plan's Task 3 confirmed, i.e. what plans 21-01..21-07 already shipped:

| Harness | Phase-start baseline (main, `614d41e`) | Live at 21-08 close | Real on-disk pass count |
|---|---|---|---|
| `companion/test_view_pages.py` | 107 | 114 | 114/114 |
| `companion/test_config_page.py` | 212 | 220 | 220/220 |
| `companion/test_companion_app.py` | 267 | 258 | 256/258 (2 documented WR-11 root-sandbox FAILs) |
| `companion/test_status_pages.py` | 213 | 218 | 217/218 (1 documented `anomaly_active()` FAIL) |
| `companion/test_contrast_check.py` | 39 | 41 | 41/41 |
| `companion/test_i18n.py` | 24 | 22 | 22/22 |

Full suite (`scripts/run-all-tests.sh`): exactly the five documented pre-existing root-sandbox failures (2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`'s `anomaly_active()`, 2 in `server/test_manual_resolutions.py`), nothing else. `ruff check .`: clean.

## Files Created/Modified

- `.claude/skills/sketch-findings-skypane/SKILL.md` — Phase 21 Folded-In Work entry; Navigation and Data-and-tables paragraphs corrected in place with SUPERSEDED annotations; findings_index rows updated
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — three new entries (small grey secondary button, `.frame-colours__row`'s directly-met floor, the row-toggle register entry); Origin line updated
- `.claude/skills/sketch-findings-skypane/references/data-density.md` — the 7-column entry marked SUPERSEDED; a new "Flights table recompacted to five columns plus a detail row" section; "What to Avoid" and Origin updated
- `.claude/skills/sketch-findings-skypane/references/mobile-navigation.md` — the three-switch footer marked SUPERSEDED (back to two); the `.nav-status` reminder's placement/contrast/degrade documented; Origin updated
- `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-VALIDATION.md` — Manual-Only Verifications table answered (Outcome column added); Per-Task Verification Map filled (22 rows); Validation Sign-Off ticked; frontmatter `status: complete`, `nyquist_compliant: true`

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Not Fixed — Flagged Instead

**1. `references/mobile-navigation.md`'s "Current tab set" paragraph still says "Four tabs, in order: Settings, Health, Airlines, History"**
- **Found during:** Task 1, while reading the file for the footer-switch-count edit
- **Issue:** The real tab set has been six tabs in two groups (Home/Display/Flights/Airlines, then Health/Device) since Phase 18 — this is a pre-existing staleness gap in the reference file, unrelated to anything phase 21 itself changed.
- **Why not fixed:** This plan's own `<interfaces>` section names exactly what `mobile-navigation.md` gains from phase 21 — "the footer's three→two switches and the new `.nav-status` line in both renderers" — and does not authorize a rewrite of the unrelated tab-count paragraph. Per the SCOPE BOUNDARY rule, a pre-existing condition unrelated to this plan's own changes is logged, not fixed.
- **Recommendation:** A future skill-maintenance pass (or the next phase's own closing plan) should correct this paragraph to the real 6-tab, two-group shape and cite Phase 18 as the origin.

---

**Total deviations:** 0 auto-fixed, 1 flagged/not-fixed (pre-existing reference-file staleness, out of this plan's own scope).
**Impact on plan:** None — no code, test or CSS file was touched by this plan, matching its own `files_owned` boundary; the one flagged item is a documentation gap this plan did not introduce and was not authorized to fix.

## Known Stubs

None.

## Threat Flags

None — this plan introduces no new network endpoint, auth path, file-access pattern or schema change. T-21-29 (sweep screenshots containing seeded data) is mitigated as specified: the sweep ran against a disposable copy of the scratchpad's synthetic seed (`state-21-08/`, never the original `state/` or any git-tracked directory), and all screenshots were written to the scratchpad, never committed — this SUMMARY records paths, not images. T-21-30 (claiming a checklist line passed without looking) is mitigated by the per-line-item table above, which names the exact evidence for every PASS and would have named "not runnable" for anything genuinely unverifiable (one Manual-Only item was). T-21-31 (fixing a defect in a closed plan's file from this closing plan) did not arise — the sweep found zero application defects; the two false FAILs traced to this plan's OWN sweep scripts (scratchpad files, not `companion/`/`server/`) and were fixed there, not in application code.

## Defects found — for the orchestrator

None. Every automated assertion across the sweep, the checklist script and the interactive script passed; every UI-SPEC Verification Checklist line has a recorded PASS (see the per-line-item table above); the full suite is green apart from the five documented pre-existing root-sandbox failures; ruff is clean.

## Issues Encountered

- Two false FAILs appeared during sweep development, both traced to bugs in this executor's own sweep scripts rather than the application: (1) a `[data-dirty-section="Calendar"]` selector only matches the English-language attribute value (`data-dirty-section`'s own value is translated per-request via `i18n.t(CALENDAR_SECTION_HEADING)`, so it reads "Calendrier" in French) — fixed by matching on the card's own `<h2>` text instead, language-agnostically; (2) the first "does clicking a chip update the preview" test picked chip index 1 ("white"), which happened to already be the effective (departures-inherited) theme showing for Arrivals before any click, so the assertion of "the src changed" was a same-value false negative — fixed by picking a chip with a genuinely different value ("black", index 2). Both are documented in `key-decisions` and did not require any change to `companion/`/`server/`.
- The scratchpad's seeded `device_config.json` has no calendar configured, so the native-`confirm()` Disconnect check could not be exercised — documented as "not runnable in this seed" in 21-VALIDATION.md's Manual-Only table rather than skipped silently.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The design-system skill (`SKILL.md` and its three touched reference files) now describes the app exactly as phase 21 leaves it: a two-switch nav with a state reminder, a five-column Flights table with a detail row, one Frame colours card, one calendar tile, and one named secondary button — every superseded phase-20 statement is marked SUPERSEDED in place, never deleted, so the next phase's own planner reads a current contract with full history intact.
- `21-VALIDATION.md` is a complete, filled record: 22 task rows, every Manual-Only item answered (5 verified in a real browser, 1 honestly not-runnable), `nyquist_compliant: true`.
- No file under `companion/` or `server/` was touched by this plan — the phase's own code is exactly as plans 21-01..21-07 left it, confirmed unmodified by `git diff --stat` at every task boundary in this plan.
- Phase 21 (D-01..D-20, R-01..R-14) is now closed from this executor's own worktree; the orchestrator's merge of this branch is the remaining step before `/gsd:verify-work` picks it up.

## Self-Check: PASSED

- FOUND: `.claude/skills/sketch-findings-skypane/SKILL.md` (contains "Phase 21")
- FOUND: `.claude/skills/sketch-findings-skypane/references/control-density.md` (contains "calendar-disconnect-btn")
- FOUND: `.claude/skills/sketch-findings-skypane/references/data-density.md` (contains "Flights table recompacted")
- FOUND: `.claude/skills/sketch-findings-skypane/references/mobile-navigation.md` (contains "nav-status")
- FOUND: `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-VALIDATION.md` (contains "nyquist_compliant: true")
- FOUND commit `e960ec0` (Task 1)
- FOUND commit `169acfa` (Task 2)
- FOUND commit `b3f40f6` (Task 3)

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*
