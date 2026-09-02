---
phase: quick-260902-iag
plan: 260902-iag
subsystem: companion-ui

tags: [companion, health-page, css, design-system, harness, reversal, typography]

requires:
  - phase: 260901-uzi
    provides: "finding 4's 16px-semibold nested-heading demotion — the decision this task reverses, at the developer's own explicit same-day instruction"
  - phase: 260902-dng
    provides: "the .stat-tile__caption semibold promotion (Task 3) — re-adjudicated and reverted here once its own stated premise inverted"
  - phase: 260902-bl2
    provides: "the retained margin-bottom: var(--space-md) spacing fix on the nested-heading rule — independently justified, verified UNCHANGED by this task"
provides:
  - "Health's three nested card headings (Battery trend, Unresolved prefixes, Resolution statistics) back on the plain 20px .text-heading treatment, matching Settings' own section headings byte-for-byte"
  - ".stat-tile__caption reverted to .text-label's inherited regular weight, its only stated reason for promotion having evaporated"
  - "One new harness check pinning the layout mechanism (containment, spacing order, adjacency) that now carries Health's two-tier hierarchy in font-size's place"
  - "The design-system skill's typography reference corrected: the caption's weight round trip and the nested-title tier's full 20px -> 16px-semibold -> 20px round trip, both in the file's own SUPERSEDED voice"
affects: [companion-ui-implementation, health-page-visual-hierarchy, stat-tile-caption-weight, design-system-reference]

tech-stack:
  added: []
  patterns:
    - "A same-day reversal recorded as SUPERSEDED in place at the rule it reverses — old reasoning stays readable, new decision and its reason sit beside it, never a silent delete-and-replace"
    - "Re-adjudicating a downstream fix (the caption weight) when its only stated justification (the nested-title weight) is itself reverted, rather than leaving it unexamined because no test happened to fail"
    - "Verifying a layout-carried hierarchy (containment/spacing/adjacency) by rendering the real DOM and reading the real cascade, not asserting it from precedent (Settings' single-level structure does not, by itself, prove a two-level structure reads apart)"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md

key-decisions:
  - "Task 1: `.page-section--nested > h2, .battery-trend-section > h2` reduced to its one retained declaration (`margin-bottom: var(--space-md)`, 260902-bl2's independently-justified spacing fix). The developer's own screenshot comparison (Settings' 20px `Runway` heading vs. Health's 16px `Unresolved prefixes` heading) and explicit choice to revert to 20px is the reason; 260901-uzi finding 4's original reasoning stays readable in the rule's SUPERSEDED comment, alongside the sketch's own declined 14px-uppercase-eyebrow alternative (`.wide-card__caption`)."
  - "Task 2: `.stat-tile__caption`'s semibold promotion (260902-dng) reverted. Its only stated justification was weight-agreement with the nested card title; with that title back to 20px regular, a semibold caption no longer restores agreement — it recreates the disagreement in the opposite direction. Both the premise test and the inversion test point to reverting (see 'Task 2 Adjudication' below); no fresh justification independent of the reverted 16px tier survives the inversion test."
  - "Task 3: the two-tier hierarchy (D-10 section headings vs. the cards nested inside them) was inspected against the real rendered DOM and real cascade rather than assumed from Settings' precedent (which is single-level and therefore does not transfer). All three signals — containment, spacing ordering, adjacency — hold. One new harness check pins all three; no non-font-size remedy was needed because the layout inspection found the distinction already holds."
  - "EXPECTED_CHECK_COUNT moved from the real on-disk 99 to 100 (one new check). Both stale checks were retargeted in place (never deleted): the demotion check inverted to assert the reversal plus a positive .text-heading/:root token guard, and the caption/four-role check's entire contract rewritten to match the post-reversal, post-readjudication state."

requirements-completed: [QUICK-260902-iag]

coverage:
  - id: nested-heading-reversal
    description: "All three nested Health card headings render at the same 20px serif regular treatment as Settings' own section headings, with no font-size/font-weight declaration of their own"
    requirement: QUICK-260902-iag
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_nested_heading_tier_reverted_to_standard_heading_role — markup half unchanged from the original demotion check (page-section--nested count, source-fault exclusion, section-intro headings), stylesheet half inverted (no font-size/font-weight/font-family, retained margin-bottom) plus a positive .text-heading/:root token guard; mutation-tested"
        status: pass
      - kind: manual
        ref: "inline verification script from PLAN.md Task 1 <verify> block — css ok / markup ok"
        status: pass
    human_judgment: true
    rationale: "The harness proves the rule's declaration set and that the markup wires the modifier correctly; only a real browser proves the three nested headings and Settings' own headings are visually indistinguishable, the developer's own stated bar for this task."
  - id: caption-readjudication
    description: ".stat-tile__caption's semibold promotion re-adjudicated against 260902-dng's own quoted justification, with both the premise test and the inversion test run and recorded, and reverted"
    requirement: QUICK-260902-iag
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_stat_tile_caption_weight_reverted_and_four_role_scale_hold — full contract rewrite in place: caption declares no font-weight/font-size (keeps its serif exception), .stat-tile__value's own Emphasis-role size/weight untouched, nested title and section heading both inherit regular with no override, four :root token values confirmed; mutation-tested"
        status: pass
      - kind: manual
        ref: "inline verification scripts from PLAN.md Task 2 <verify> block — caption verdict recorded: semibold=False / scope ok"
        status: pass
    human_judgment: true
    rationale: "The harness proves the shipped declaration and its reasoning trail; only a real browser proves the caption does not now read as weak or lost beside the restored 20px card titles (Pixel-Level Item 3 below)."
  - id: layout-hierarchy-verified-and-pinned
    description: "The two-tier hierarchy still reads apart with no font-size/font-weight distinction, verified by real layout inspection (containment, spacing, adjacency) and pinned by one new harness check"
    requirement: QUICK-260902-iag
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_two_tier_hierarchy_carried_by_layout_not_type — markup half (every level-2 heading inside a bordered card <section>, both level-1 headings inside the plain .section-intro row, a .dashboard-grid always intervening) in both empty and seeded state, stylesheet half (four spacing tiers strictly ordered against real :root tokens); mutation-tested, both halves independently"
        status: pass
      - kind: manual
        ref: "inline verification script from PLAN.md Task 3 <verify> block — layout hierarchy ok: 48 > 24 > 16"
        status: pass
    human_judgment: true
    rationale: "The harness proves containment/adjacency/spacing-ordering hold in the real DOM and cascade; only a real browser proves a human actually perceives the two tiers as distinct at a glance (Pixel-Level Item 1 below) — the developer's own accepted trade this whole task rests on."

duration: ~50min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-iag: Revert the Health Nested-Card Heading Demotion Summary

**Reverses 260901-uzi finding 4's 16px-semibold nested-card-heading demotion back to the plain 20px `.text-heading` treatment, at the developer's own explicit same-day instruction; re-adjudicates and reverts `.stat-tile__caption`'s semibold promotion (260902-dng) once its only stated reason inverted; and verifies by real layout inspection — not by Settings' single-level precedent alone — that the resulting two-tier hierarchy still reads apart via containment, spacing and adjacency.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Commits:** 5 (4 code/test/docs commits, this SUMMARY commit)
- **Files modified:** 5 (`companion/static/style.css`, `companion/pages/health_page.py`, `companion/test_status_pages.py`, `.claude/skills/sketch-findings-skypane/SKILL.md`, `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md`)

## Accomplishments

- **Task 1 — nested heading reversal:** `.page-section--nested > h2, .battery-trend-section > h2` reduced to its one retained declaration, `margin-bottom: var(--space-md)` (260902-bl2's independently-justified spacing fix, verified UNCHANGED). The rule's comment is rewritten as a SUPERSEDED reversal record: what 260901-uzi finding 4 did and why, that the developer compared the demoted heading against Settings' own 20px heading and chose to revert, that each card's own border/surface/padding now carries the grouping signal font-size briefly carried, and that the sketch's own 14px-uppercase-eyebrow treatment (`.wide-card__caption`) was a considered, declined third option. `health_page.py`'s three stale comments claiming a type demotion (`render()`'s Server & data block, `_registry_section()`, `_source_fault_block()`) are corrected. Both harness checks that asserted the demoted values are retargeted in place.
- **Task 2 — caption re-adjudication:** `.stat-tile__caption`'s semibold promotion (260902-dng Task 3) is reverted. Its only stated reason — weight-agreement with the nested card title's 16px-semibold tier — inverted rather than merely weakened once that tier reverted to 20px regular (see "Task 2 Adjudication" below). The caption's comment records the re-adjudication in the SUPERSEDED voice, keeping 260902-dng's original reasoning readable. The harness check's whole contract (not just its assertions) is rewritten in place to match.
- **Task 3 — hierarchy verified, pinned, and design-system record corrected:** the two-tier hierarchy (D-10's section headings vs. the cards nested inside them) is checked against the real rendered DOM and cascade rather than assumed from Settings' own single-level precedent. All three signals — containment, spacing ordering, adjacency — hold (see "Task 3 Hierarchy Verdict" below); no non-font-size remedy was needed. One new harness check pins both halves (markup + stylesheet), mutation-tested. `EXPECTED_CHECK_COUNT` moves from the real on-disk 99 to 100. The design-system skill's typography reference is corrected: the caption's weight round trip and a new "Nested card title tier" entry recording the full 20px → 16px-semibold → 20px round trip, both under the file's own SUPERSEDED convention; `SKILL.md`'s changelog gets one new entry and its stale "Current as of" line is bumped.
- **Harness:** `companion/test_status_pages.py` 99/99 → 100/100 (both retargets done in place, one net-new check). `companion/test_config_page.py` 61/61, `companion/test_view_pages.py` 43/43, `companion/test_companion_app.py` 106/106, `companion/test_contrast_check.py` 36/36 — all unmodified and green, proving the reversal reached no other page. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch (`44fe835e... != pinned 49b8ba45...`) — with no coverage-gate shortfall (92% total).

## Post-Revert Four-Role Type Table

Read from the real cascade after both Task 1 and Task 2, not from memory:

| Role | Selector | Size | Weight | Family |
|---|---|---|---|---|
| Section heading | `h2.text-heading` (inside `.section-intro`) | 20px (`--font-heading-size`) | regular (400) | serif (`h1,h2,h3,legend,.text-heading`) |
| Nested card title | `.page-section--nested > h2, .battery-trend-section > h2` | 20px (`--font-heading-size`, inherited — no override) | regular (400, inherited — no override) | serif (inherited) |
| Stat-tile caption | `p.text-label.stat-tile__caption` | 14px (`--font-label-size`, inherited from `.text-label`) | regular (400, inherited from `.text-label` — 260902-dng's promotion reverted) | serif (named exception) |
| Stat-tile value | `p.stat-tile__value` | 16px (`--font-body-size`) | semibold (600) — D-09 Emphasis role, untouched | sans (`--font-ui`, inherited from `body`) |

The section heading and the nested card title are now byte-identical in size/weight/family — the developer's explicitly chosen outcome. The caption is back to the plain Label role it held before 260902-dng. The tile value is the only semibold role in the region, unchanged and untouched by either adjudication.

## Task 2 Adjudication — Both Tests, Verdict

**Step 1 — 260902-dng's stated justification, quoted:** the promotion's comment names hypothesis (ii) as the reason acted on — the tile caption and the nested card title are both this file's "name of a card" role, and until the promotion they rendered at two different weights (14px regular serif vs. 16px semibold serif); promoting the caption made the two "card name" roles agree on weight.

**Premise test — does hypothesis (ii)'s premise survive the Task 1 reversal? NO.** It asserted the two "card name" roles disagreed on weight and should agree. After the revert, the nested card title is 20px regular. A semibold caption does not restore agreement — it recreates the disagreement in the opposite direction, with the smaller role (14px) now the bolder one beside the larger role (20px) that stays regular.

**Inversion test — which roles in the Server & data region would carry semibold if the promotion were kept? Only the two smallest.** The 14px caption (if kept) and `.stat-tile__value`'s 16px (D-09's Emphasis role, untouched, non-goal). Both 20px roles — the section heading and the reverted nested card title — stay regular. Weight would increase as size decreases across the region: the same class of inverted hierarchy 260901-uzi finding 4 itself existed to fix, one structural level up.

**Verdict: REVERTED.** Both tests point the same way. No fresh justification independent of the reverted 16px tier was found that survives the inversion test — the validated Merged Health Sketch's own `.stat-tile__caption` rule (14px muted uppercase, no weight promotion) is a corroborating data point, not the deciding one. `.stat-tile__caption` declares no `font-weight` again, inheriting `.text-label`'s regular weight.

## Task 3 Hierarchy Verdict — All Three Signals

Verified against a real `health_page.render()` output (both empty and seeded state) and the real stylesheet, not asserted from Settings' own precedent (which is single-level — four sibling `.page-section` cards, no section heading above them — and therefore proves only "a 20px heading inside a bordered card reads fine," not "two levels at 20px read as distinct").

**Containment — HOLDS.** A level-1 heading (`Screen`, `Server & data`) sits inside `<div class="section-intro">` directly on the page canvas — confirmed from a real render: `<div class="section-intro"><h2 id="screen" class="text-heading">Screen</h2><p class="text-label section-caption">...</p></div>`, no border, no padding, no card class. A level-2 heading (`Battery trend`, `Unresolved prefixes`, `Resolution statistics`) is always the first child of a bordered `--color-dominant` card (`<section class="page-section page-section--nested ...">` or `<section class="battery-trend-section ...">`).

**Spacing ordering — HOLDS, strictly.** Read from the real rules and `:root`'s real token values: `.battery-trend-section`'s section-transition `margin-bottom` = 48px (`--space-2xl`) > `.page-section`/`.dashboard-grid`'s shared same-section card-to-card `margin-bottom` = 24px (`--space-lg`) > the reverted nested-heading rule's retained heading-to-content `margin-bottom` = 16px (`--space-md`) > the heading-rhythm rule's own `margin: 0 0 var(--space-sm)` = 8px. 48 > 24 > 16 > 8, confirmed by the same arithmetic the new harness check runs at execution time.

**Adjacency — HOLDS.** In both the Screen and Server & data sections, a `<div class="dashboard-grid">` (the Device tile; the Pipeline/Corroboration/Resolution-rate tiles) always sits between the level-1 `.section-intro` heading and the first level-2 nested card — confirmed byte-for-byte from a real render for both sections. A level-1 heading is never immediately followed by a level-2 card heading.

**Which signal does most of the work:** containment. It is the one binary, immediately perceptible distinction (bare canvas text vs. the first line of a bordered, filled, padded card) — a viewer registers "this is not inside a box" vs. "this is the title of a box" far faster than they register a spacing delta. Spacing ordering and adjacency both reinforce the same grouping but are more subtle; a viewer does not consciously measure 48px against 24px against 16px against 8px, though the strict ordering means nothing in the layout accidentally works against containment's own signal.

**Remedy needed: none.** All three signals hold in the real render/cascade, so no non-font-size remedy (spacing, indentation, surface, or otherwise) was proposed or implemented. No font-size or font-weight distinction between the two tiers was reintroduced anywhere.

## Design-System Skill: Grep Finding

Grepped `.claude/skills/sketch-findings-skypane/` for `page-section--nested`, `battery-trend-section > h2`, `nested card`, `nested-heading`, and `16px semibold` before this task — **zero hits**. The skill never documented the 16px nested-heading tier at all; `260901-t00` (which last consolidated the skill) predates `260901-uzi`'s demotion. There was therefore no "reverted decision described as current" to correct on that front — only `references/visual-direction-typography.md`'s `.stat-tile__caption` declaration enumeration, which had gone stale when `260902-dng` added the weight and now needed correcting again for the weight's own reversal. Both facts are now recorded: the caption's weight round trip, and a new "Nested card title tier" entry covering the full 20px → 16px-semibold → 20px round trip this task closes, both in the file's own SUPERSEDED convention.

## App-Wide Heading-Rhythm Inconsistency — Handed Forward, Not Resolved

Real, app-wide, found during this task's own reading, explicitly NOT this task's to fix: the validated Merged Health Sketch's own `h2.text-heading, .section-heading` rule declares `margin: 0 0 var(--space-md)` (16px) below **every** heading. This stylesheet's own heading-rhythm rule (`h1, h2, h3, .text-heading { margin: 0 0 var(--space-sm); }`) declares 8px universally, with the three Health nested cards as the only exception (via their own retained `margin-bottom: var(--space-md)`, independently justified by 260902-bl2, not by this app-wide question). This 8px-vs-16px inconsistency between the sketch's own vision and what shipped everywhere else (Settings' four groups, the two `.section-intro` headings, `.page-title`, etc.) is real and predates this task. Not widened, not quietly closed here — a future item for whoever next touches app-wide heading rhythm.

## Task Commits

1. **Task 1:** `641feba` — `fix(quick-260902-iag): restore the standard 20px heading on Health's nested cards` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`
2. **Task 2:** `a1f12f5` — `refactor(quick-260902-iag): return the stat-tile caption to its inherited regular weight` — `companion/static/style.css`, `companion/test_status_pages.py`
3. **Task 3 (harness):** `6c26b35` — `test(quick-260902-iag): pin the layout-carried hierarchy, EXPECTED_CHECK_COUNT +1` — `companion/test_status_pages.py`
4. **Task 3 (docs):** `be10e50` — `docs(quick-260902-iag): correct the design-system record for the reverted heading tier` — `.claude/skills/sketch-findings-skypane/SKILL.md`, `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md`

## Files Created/Modified

- `companion/static/style.css` — `.page-section--nested > h2, .battery-trend-section > h2` reduced to its retained `margin-bottom` declaration, with a full SUPERSEDED reversal record above the selector; `.stat-tile__caption`'s `font-weight` declaration removed, with the re-adjudication recorded alongside 260902-dng's original reasoning
- `companion/pages/health_page.py` — three comments correcting stale "demoted to the Emphasis role" claims (`render()`'s Server & data block, `_registry_section()`, `_source_fault_block()`), all referencing this quick task
- `companion/test_status_pages.py` — `_nested_heading_tier_reverted_to_standard_heading_role` (renamed, inverted, positive `.text-heading`/`:root` guard added), `_stat_tile_caption_weight_reverted_and_four_role_scale_hold` (renamed, full contract rewrite), `_two_tier_hierarchy_carried_by_layout_not_type` (new), `EXPECTED_CHECK_COUNT` 99 → 100
- `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md` — `.stat-tile__caption`'s weight round trip recorded; new "Nested card title tier" entry recording the full 20px → 16px-semibold → 20px round trip
- `.claude/skills/sketch-findings-skypane/SKILL.md` — "Current as of" line bumped, one new Folded-In Work entry for this quick task

## Decisions Made

See `key-decisions` in the frontmatter above for the Task 1 reversal scope, the Task 2 adjudication verdict, and the Task 3 hierarchy verification/pinning summary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The plan's own verify script locates the caption-check function by the literal substring `def _stat_tile_caption`**
- **Found during:** Task 2, after renaming the harness function to fully describe its post-reversal contract
- **Issue:** The plan's own inline `<verify>` script for Task 2 does `t.index('def _stat_tile_caption')` to locate and inspect the function body. An initial rename to `_four_role_type_scale_after_reversal_and_readjudication` (which drops the `_stat_tile_caption` prefix entirely) would have made that lookup raise `ValueError: substring not found`, failing the plan's own verification step even though the check's logic was correct.
- **Fix:** renamed to `_stat_tile_caption_weight_reverted_and_four_role_scale_hold` — keeps the `_stat_tile_caption` prefix the verify script depends on while still describing the new, reverted contract accurately.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** re-ran the plan's exact inline verify script; `caption verdict recorded: semibold=False` printed with no error.
- **Committed in:** `a1f12f5` (Task 2)

**2. [Rule 1 - Bug] The new hierarchy check's spacing-token extraction regex did not match the heading-rhythm rule's shorthand form**
- **Found during:** Task 3, first run of the new `_two_tier_hierarchy_carried_by_layout_not_type` check
- **Issue:** The heading-rhythm rule declares `margin: 0 0 var(--space-sm);` (a shorthand with leading zero values before the `var()`), not a bare `margin: var(--space-sm);`. The check's initial `_decl_px()` helper regex (`r"%s:\s*var\(--([a-z0-9-]+)\);"`) only matched a `var()` immediately following the colon, so it returned `None` for this rule's token and the check failed with a "expected all four spacing rules... to resolve to real px token values" error before any of the layout logic could run.
- **Fix:** widened the regex to `r"%s:\s*[^;]*?var\(--([a-z0-9-]+)\)[^;]*;"`, which matches the last `var()` in a declaration regardless of leading shorthand values, and documented why in a comment.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** re-ran the check; all four spacing tokens resolved correctly (`layout hierarchy ok: 48 > 24 > 16` in the standalone verify script; the harness check itself passed with the full 8px intro value included).
- **Committed in:** `6c26b35` (Task 3)

---

**Total deviations:** 2 (1 Rule-3 blocking fix to satisfy the plan's own hardcoded verify-script lookup; 1 Rule-1 bug fix in the new check's own token-extraction regex)
**Impact on plan:** Both were necessary for the plan's own stated verification to succeed as written. No scope creep — neither touched production code, only the harness.

## Issues Encountered

- No package installs, no auth gates. Rule 4 (architectural change) was never triggered — every fix in this task is a scoped CSS/comment/harness change within the plan's own stated levers.
- No computer-use/chrome-devtools MCP browser-automation tools were bound to this executor, matching every preceding Health quick task today (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng, 260902-ep7, 260902-gjj), each of which handed pixel-level confirmation back to the orchestrating session, which performed it successfully every time.

## Pixel-Level Items Outstanding

No browser-automation tools were bound to this executor. **None of the following is claimed as verified here** — only source-level and harness-level verification was performed.

Provable from source/harness and already covered, so do NOT re-verify these by eye: that the nested-heading rule declares no font-size/font-weight/font-family, that `.text-heading` and `:root`'s `--font-heading-size` token are unchanged at 20px/regular, that `.stat-tile__caption` declares no font-weight, that `.stat-tile__value` is untouched, that the four spacing tiers are strictly ordered against real token values, and that every level-2 heading sits inside a bordered card while every level-1 heading sits inside the plain `.section-intro` row with a `.dashboard-grid` always intervening.

Needs a real browser:

1. **[MOST IMPORTANT — the developer's own accepted trade] Does the page read with a coherent hierarchy now, and does nothing look randomly oversized.** With `Battery trend`, `Unresolved prefixes` and `Resolution statistics` back at 20px, confirm they still read as subordinate to `Screen` and `Server & data` rather than as peers — this task's harness proves the containment/spacing/adjacency mechanism exists, not that a human eye reads it as intended.
2. **The direct comparison that started this task.** Settings' `Runway` heading beside Health's `Unresolved prefixes` heading — confirm they are now visually indistinguishable in treatment. If not, the reversal is incomplete and the difference must be measured, not guessed.
3. **The caption's own legibility beside the restored 20px titles.** Confirm the stat-tile captions ("Pipeline", "Corroboration", "Resolution rate") do not now read as weak or lost beside the tile value and beside the restored 20px card titles, now that the semibold promotion is reverted.
4. **Both themes, and a narrow viewport.** Neither was re-checked after 260902-bl2 (the orchestrating session's tooling failed on those passes at the time), so they are doubly overdue for this specific region.
5. **Nothing else moved.** Settings, History, Preview and Health's own top-level source-fault block keep their previous heading treatment; the 16px heading-to-content rhythm inside all three nested cards is unchanged from the 260902-bl2 pass already confirmed live.
6. **Still open and not touched here:** the Safari readings-disclosure header clipping (260901-uzi finding 5), and the app-wide 8px-vs-16px heading-rhythm inconsistency this task identified but deliberately did not resolve (see above).

## User Setup Required

None to run the code. **Recommended before signing off:** the six-item live-browser pass above, on `/health`, with item 1 (does the two-tier hierarchy still read as intended without the type-scale distinction) and item 2 (the direct Settings-vs-Health comparison that started this task) as the priority items — they are the developer's own stated bar for this reversal.

## Next Phase Readiness

All three fixes are implemented and pinned by harness: `companion/test_status_pages.py` 100/100; `companion/test_config_page.py` 61/61; `companion/test_view_pages.py` 43/43; `companion/test_companion_app.py` 106/106; `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch — with no coverage-gate shortfall (92% total). The six-item live-browser handoff above is the concrete next action for the orchestrating session before this reversal can be considered visually verified, not just source-verified.

## Post-execution: real-browser visual pass (orchestrating session)

Performed against the restarted local instance with real production data, at 1280×1000.

1. **Item 1 (coherent hierarchy) and item 2 (direct Settings comparison): CONFIRMED.** All three nested headings ("Battery trend", "Unresolved prefixes", "Resolution statistics") measure `font-size: 20px`, `font-weight: 400`, `font-family: Georgia` — byte-identical to Settings' own `h2.text-heading` (e.g. "Runway"), closing the exact gap the developer's screenshot comparison identified. Screenshot confirms "Battery trend" reads with proper weight, and the card's white/bordered boundary clearly signals the nesting without needing a smaller font — the hierarchy reads coherently, "Screen"/"Server & data" still clearly read as the outer grouping.
2. **Item 3 (caption legibility): CONFIRMED.** `.stat-tile__caption` measures `font-weight: 400` (reverted from 600), `font-size: 14px` — not weak or lost against the restored 20px card titles in the screenshot.

**Not performed:** dark theme, 375px width (item 4 — the plan itself notes these were never successfully re-checked after the original 260902-bl2 pass either, so this is now doubly overdue), and a genuine visual A/B against the Settings page side-by-side in the same viewport (I compared computed styles directly rather than two simultaneous screenshots, which gives equally strong evidence for the numeric claim but not a literal side-by-side image).

---
*Phase: quick-260902-iag*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 5 modified files (`companion/static/style.css`, `companion/pages/health_page.py`, `companion/test_status_pages.py`, `.claude/skills/sketch-findings-skypane/SKILL.md`, `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md`) confirmed present on disk. All 4 task commit hashes (`641feba`, `a1f12f5`, `6c26b35`, `be10e50`) confirmed present in `git log`.
