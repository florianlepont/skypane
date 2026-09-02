---
phase: quick-260902-bl2
plan: 260902-bl2
subsystem: companion-ui

tags: [companion, health-page, design-system, css, harness]

requires:
  - phase: quick-260901-uzi
    provides: "the `page-section--nested`/`.battery-trend-section` demotion rule this task adds a margin-bottom declaration to, and the `.data-table--prose` opt-out this task's `desc_columns` change is applied alongside"
  - phase: 06.6.4.1
    provides: "the migrated `.page-section` Unresolved-prefixes/Resolution-statistics cards whose heading-to-content gap this task fixes"
provides:
  - "layout.data_table()'s `desc_columns` keyword — `mono_columns`' direct sibling — the missing column-role class hook that lets a caller mute a prose column"
  - "`.data-table td.desc`, muting the Resolution-statistics table's Description column at this file's existing 70% color-mix strength (bug 1)"
  - "One heading-to-content rhythm across all three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics), built from the validated sketch's own two margin values rather than a value chosen to split the difference (bug 2)"
  - "A written, source-derived verdict on the developer's 40px live measurement for the Unresolved-prefixes gap, which this task's own arithmetic does not reproduce — recorded as an open discrepancy, not papered over"
affects: [companion-ui-implementation, 06.6.4.1-closing-checkpoint]

tech-stack:
  added: []
  patterns:
    - "Column-role class hook on a shared table builder (desc_columns, mono_columns's sibling) instead of a one-off selector hack in the page module — the class is the scope, emitted only where a caller opts in"
    - "The heading in a heading/prose pair owns the gap below it (margin-bottom on the heading), and the prose owns zero above itself — so the total gap is deterministic regardless of which element type follows, rather than being the composition of one stated rule and one unstated UA default"
    - "A markup allowlist harness check as the replacement for a catch-all zero-margin rule — pins today's true statement ('nothing that follows carries a top margin') so a future element that breaks it fails loudly instead of silently reintroducing the inconsistency"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "Bug 1's fix carries only the colour half of the sketch's own `td.desc` rule, not its `min-width: 220px`. 260901-uzi's own `.data-table--prose` comment, six lines above where the new rule lands, already argues a fixed floor on this exact column re-creates the horizontal overflow that modifier was written to remove, one breakpoint down. The declined half is written down in the CSS comment, not left as an apparent omission."
  - "Bug 1 reuses this file's single existing 70% `color-mix` muted strength rather than the sketch's own `--color-text-muted` token. `.cell-primary`'s comment already states in writing that no such token exists in this file and none is introduced here. `color`, not `opacity`, is used specifically because `.data-table td` declares its own `border-bottom` hairline that `opacity` would fade along with the text."
  - "Bug 2's fix adopts the sketch's own two values verbatim — the card-title role's `margin-bottom: var(--space-md)` (16px) and the intervening-prose role's `margin: 0 0 var(--space-sm)` (0 above, 8px below) — rather than a value chosen to split the difference between the two cards' pre-fix gaps. The heading owns the whole gap; the prose owns none of it; the result is deterministic regardless of which element type follows."
  - "Bug 2 declines the sketch's structural move of the status dot into the card-title row (`.wide-card__caption`'s space-between flex pair). The developer's finding was about spacing, the spacing is now the sketch's; moving the dot would restructure three cards and retarget several harness checks for a change nobody asked for. Recorded as a considered rejection in `health_page.py`'s `_registry_section()`/`_battery_badge_block()` comments, with the sketch's role name, not left as an apparent omission."
  - "The developer's own live-measured 40px gap for Unresolved-prefixes' heading-to-first-paragraph is NOT reproduced by this task's cascade arithmetic (see 'Gap Arithmetic Discrepancy' below, which derives 16px from source before the fix). Per the plan's own instruction, no rule was invented to hit 40px — the fix targets the mechanism this task can prove from source (the demotion rule's margin-bottom + the new prose rhythm rule), and the discrepancy is recorded here for the orchestrating session's live-browser pass rather than silently resolved either way."
  - "No `EXPECTED_CHECK_COUNT` in-place retargeting was needed for either bug — no pre-existing check keyed on a bare Description `<td>` or on the pre-fix heading-to-content gap, so both new checks (Task 3) are purely additive, +2, with the live-HTTP extension done in place as usual."

requirements-completed: [QUICK-260902-bl2]

coverage:
  - id: bug-1
    description: "The Resolution-statistics Description column renders in this file's existing 70% muted strength instead of full-strength body text, via a new desc_columns column-role hook on layout.data_table(); History's table, the unresolved-prefix registry, and the battery readings table are unaffected"
    requirement: QUICK-260902-bl2
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_desc_column_muted_end_to_end (new) — markup + builder + stylesheet halves"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /health response body carries the desc-class cells at the expected count, after the Resolution-statistics heading; real /static/style.css response carries the .data-table td.desc rule"
        status: pass
    human_judgment: true
    rationale: "Whether the muted colour actually reads as comfortably legible next to full-strength Source/Count text, in both themes, on real hardware/browser rendering, is a visual judgment this executor's automated harness cannot make. Handed to the orchestrating session's browser pass."
  - id: bug-2
    description: "All three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics) show one heading-to-content rhythm — the card heading owns a 16px bottom margin (the sketch's card-title value) and every direct-child p.text-body under it owns 0 above / 8px below (the sketch's intervening-prose value) — in both the empty and seeded state"
    requirement: QUICK-260902-bl2
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_nested_card_heading_rhythm_end_to_end (new) — markup allowlist across both states + stylesheet halves"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /static/style.css response carries the demotion rule's new margin-bottom and the prose rhythm rule's selector"
        status: pass
    human_judgment: true
    rationale: "The developer's own live 40px measurement for Unresolved-prefixes is not reproduced by this task's static-cascade arithmetic (derived: 16px). This task fixed the mechanism it can prove from source and recorded the discrepancy rather than guessing a rule to match 40px — the orchestrating session's live-browser pass must re-measure and either confirm the fix closed the gap to 16px or identify a still-unaccounted-for factor."

duration: ~35min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-bl2: Fix 2 More Confirmed Real Bugs on the Health Page Summary

**Fixed 2 more confirmed, live-measured bugs on the shipped Health page found in a second real-Safari pass, immediately after quick task 260901-uzi landed — the Resolution-statistics Description column now renders muted (a new `desc_columns` column-role hook on `layout.data_table()`), and all three nested Health cards now share one heading-to-content rhythm built from the validated sketch's own two margin values — while explicitly recording a gap-arithmetic discrepancy this task's own source-derived math could not reconcile with the developer's live 40px measurement.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-02T06:47Z
- **Tasks:** 3/3 completed
- **Files modified:** 4 (`companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`)

## Accomplishments

- **Bug 1 (unmuted Description column):** `layout.data_table()` gained an optional `desc_columns=()` keyword, `mono_columns`' direct sibling — the cell-class construction changed from a single-class ternary to a joined role list (`mono` first, then `desc`), so a mono-only cell's output stays byte-identical (proven by assertion) and one cell can carry both roles. `_stats_table_html()` (the Resolution-statistics table) opts its Description column in via `desc_columns=(1,)`; every other `data_table()` caller is untouched. `.data-table td.desc` sits immediately after `.data-table td` in style.css, declaring only `color: color-mix(in srgb, var(--color-text) 70%, transparent)` — this file's single existing muted strength, not the sketch's own `--color-text-muted` token (`.cell-primary`'s comment already forbids introducing one), and `color` rather than `opacity` specifically because `.data-table td`'s own `border-bottom` hairline would otherwise fade along with the text. The sketch's own `min-width: 220px` half of this rule is deliberately not carried — `.data-table--prose`'s comment already argues a fixed floor here re-creates the overflow 260901-uzi just removed, one breakpoint down.
- **Bug 2 (inconsistent heading-to-content spacing):** The `.page-section--nested > h2, .battery-trend-section > h2` demotion rule (260901-uzi) gained a longhand `margin-bottom: var(--space-md)` (16px, the sketch's `.wide-card__caption` value) — the heading-rhythm rule above it still owns the zeroed top/sides. A new rule, `.page-section--nested > p.text-body, .battery-trend-section > p.text-body { margin: 0 0 var(--space-sm) }` (the sketch's `.read-only-note` value), gives every direct-child prose paragraph under these three headings zero margin above and 8px below. Together these make the heading own the whole gap regardless of what follows it — a paragraph, a table wrapper, a filter bar, or an empty state all now produce the same 16px gap. `.battery-readout` (a direct-child `<p>` of the battery card, carrying no `text-body` class and already owning its own margin) is untouched by construction — the selector's class qualifier is load-bearing. No catch-all `> *` rule was added; a markup-allowlist harness check (Task 3) pins today's true statement that every other element type reachable at that position carries no top margin, so a future violation fails loudly.
- **Gap arithmetic discrepancy — recorded, not resolved:** See "Gap Arithmetic Discrepancy" below. This task's own cascade math, run against the real pre-fix source, derives an 8px Resolution-statistics gap (matches the developer's report) but a 16px Unresolved-prefixes gap (does NOT match the developer's live-measured 40px). Per the plan's explicit instruction, no rule was invented to hit 40px; the fix targets what this task can prove from source, and the mismatch is handed to the orchestrating session's browser pass rather than guessed away.
- **Sketch structural move declined (both bugs' shared non-goal):** Neither fix moves the Coverage/Battery-readings status dot into the card-title row, even though the sketch's `.wide-card__caption` places it there as a space-between flex pair. Recorded as a considered rejection in `health_page.py`'s `_registry_section()` (full reasoning) and `_battery_badge_block()` (cross-reference), with the sketch's role name, so a later "finish matching the sketch" edit finds a written decision rather than an apparent omission.
- **Test harness:** 2 new checks added (Check 1: the Description column is the only muted column, end to end — markup + builder + stylesheet; Check 2: all three nested cards show one heading-to-content rhythm, in both the empty and seeded state — markup + stylesheet), plus Section 3's `_both_tabs_ok_end_to_end()` extended in place (no count change) to assert the desc-class cell count/position against a real `/health` HTTP response and to fetch `companion/app.py`'s pre-auth `STYLE_ROUTE` from the same running service, confirming the served stylesheet actually carries all three rule changes. `EXPECTED_CHECK_COUNT` moved from the real on-disk baseline (82) to 84. Both new checks and the live-HTTP stylesheet fetch were each independently mutated (one bogus literal/route each) and confirmed to fail — exactly those checks and no others — before being restored to green.
- **Real-service verification:** Started a real `companion/app.py` subprocess against a freshly seeded state directory, signed in over real HTTP, and fetched both `/health` and `/static/style.css`. Confirmed in the real response bodies: exactly 4 `<td class="desc">` cells (one per `_SOURCE_ROWS` entry) after the Resolution-statistics heading; the served stylesheet carries `.data-table td.desc {`, `margin-bottom: var(--space-md)` (inside the demotion rule), and the `.page-section--nested > p.text-body` selector.

## Task Commits

1. **Task 1:** `f27042a` — `fix(quick-260902-bl2): mute the resolution-statistics description column` — `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`
2. **Task 2:** `5ae4548` — `fix(quick-260902-bl2): give every nested Health card one heading-to-content rhythm` — `companion/pages/health_page.py`, `companion/static/style.css`
3. **Task 3:** `b0e19d5` — `test(quick-260902-bl2): pin both Health fixes, EXPECTED_CHECK_COUNT +2` — `companion/test_status_pages.py`

## Files Created/Modified

- `companion/layout.py` — `data_table()` gained the optional `desc_columns=()` keyword; the cell-class ternary became a joined role list (mono first, then desc); docstring extended with a new paragraph beside `raw_columns`'s
- `companion/pages/health_page.py` — `_stats_table_html()` passes `desc_columns=(1,)`, with a docstring paragraph explaining why; `_registry_section()`/`_battery_badge_block()` each record the declined status-dot-in-caption-row structural move
- `companion/static/style.css` — `.data-table td.desc` (new, after `.data-table td`); the `.page-section--nested > h2, .battery-trend-section > h2` demotion rule gained `margin-bottom: var(--space-md)`; `.page-section--nested > p.text-body, .battery-trend-section > p.text-body` (new, after the demotion rule)
- `companion/test_status_pages.py` — 2 new checks (`_desc_column_muted_end_to_end`, `_nested_card_heading_rhythm_end_to_end`), 1 in-place live-HTTP extension, `EXPECTED_CHECK_COUNT` 82→84

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on both declined sketch fragments (the `min-width` half of `td.desc`, and the status-dot-in-caption-row move), the muted-strength/colour-not-opacity choice, the deterministic heading-owns-the-gap design, and the gap-arithmetic discrepancy this task recorded rather than resolved.

## Gap Arithmetic Discrepancy — Recorded for the Orchestrating Session's Browser Pass

**Pre-fix cascade, derived from the real source (verified against the actual rendered markup, not assumed):**

- **Resolution-statistics:** `<h2>` (margin-bottom: `var(--space-sm)` = 8px, the heading-rhythm rule) directly followed by `<div class="data-table-wrap">` (no margin at all). Gap = **8px**. This matches the developer's reported 8px exactly.
- **Unresolved-prefixes:** `<h2>` (margin-bottom: 8px) directly followed by `<p class="text-body">` (the Coverage status-dot line). `.text-body` declares no margin of its own — its comment states this is a deliberate decision, not an omission, so it falls through to the UA default `margin-block: 1em`, computed against `.text-body`'s own `--font-body-size` (16px) = 16px top margin. Adjoining sibling block margins collapse (max, not sum): max(8px, 16px) = **16px derived**.

**The developer's live measurement for this same gap was 40px** (this session's own instruction, distinct from the plan's own "8px vs 56px total" framing of the pre-fix state — a different measurement taken at a different point). This task's arithmetic, run directly against the real pre-fix source, does **not** reproduce 40px — it reproduces 16px. Per the plan's explicit instruction, no rule was invented to force a 40px-shaped result; the fix instead makes the *mechanism* deterministic (the heading owns 16px below it, unconditionally, regardless of which element type follows) and ships that.

**What the orchestrating session's live-browser pass needs to check:** with the fix applied, does Unresolved-prefixes' heading-to-first-paragraph gap now measure 16px (matching this task's derivation and Resolution-statistics' own gap)? If the real measurement is still meaningfully above 16px, the 40px figure was likely capturing something this static-CSS read cannot see from source alone (a browser-specific UA-stylesheet difference, a measurement that included more than the immediate heading-to-paragraph gap, or a rendering quirk) — worth a fresh, careful re-measurement rather than assuming either number is simply wrong.

## Known Stubs

None. Every value introduced (the desc-class cells, the two margin declarations) is wired to real render-time data and real stylesheet tokens — nothing renders empty/placeholder/mock data.

## Threat Flags

None. This task's `<threat_model>` (T-bl2-01 through T-bl2-05, all `mitigate`, plus T-bl2-SC `accept` for the zero-package-install non-goal) fully covers the surface this plan touches — `desc_columns`' escaping/scoping boundary, the muted colour's contrast (already pinned by `test_contrast_check.py`'s existing `live_pairs`), and the spacing change's accessibility non-impact (no element/role/heading-level/live-region change). No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary was introduced.

## Issues Encountered

- No package installs, no auth gates, no architectural questions.
- No computer-use/chrome-devtools MCP tools were bound to this subagent, matching both immediately-prior Health quick tasks' (260901-tsa, 260901-uzi) own precedent. Automated verification (harness checks plus a real `companion/app.py` subprocess/login/HTTP fetch, including a real fetch of the served stylesheet) was completed to the fullest extent possible without those tools; genuine pixel-level visual confirmation, and the gap-arithmetic discrepancy above, are explicitly outstanding — see "Pixel-Level Items Outstanding" below.

## Pixel-Level Items Outstanding for the Orchestrating Session's Browser Pass

The live-HTTP half is automated and passing (Section 3's extended `_both_tabs_ok_end_to_end()`, confirmed to carry the desc-class cells and all three new/changed stylesheet rules against a real running service). These items genuinely cannot be settled from raw HTML/CSS text and require a real rendered browser:

1. The Resolution-statistics Description column now reads as muted secondary text beside full-strength Source labels and Counts, in BOTH themes, and is still comfortably legible at the dark theme's card surface. (`test_contrast_check.py`'s existing "muted detail text on card surface" pairs already pin the underlying colour math in both themes — this item is about how it actually reads, not whether it passes a contrast ratio.)
2. The three nested cards ("Battery trend", "Unresolved prefixes", "Resolution statistics") now show the same gap between their heading and the first thing under it, measured live rather than derived — and the Unresolved-prefixes card's total pre-table stack is visibly tighter than the 56px figure the plan's own framing referenced.
3. **Whether the derived gap arithmetic above (16px) matches the live measurement.** If the reported 40px between Unresolved-prefixes' heading and its first paragraph is still there after this fix, the cause is something not visible in the source read and must be measured, not guessed — see "Gap Arithmetic Discrepancy" above for the full reasoning and what to check.
4. Nothing else on the page moved: Settings, History and Health's own source-fault block keep their previous heading rhythm, and History's and the registry table's cells keep full-strength text.
5. Still open from 260901-uzi and not touched here: the Safari readings-disclosure header clipping (finding 5), with both candidates and their trade-offs as recorded in that task's own SUMMARY.

## User Setup Required

None to run the code. **Recommended before signing off this checkpoint item:** a real-browser visual pass on `/health` (desktop + narrow width, light + dark, real Safari for the gap-arithmetic discrepancy specifically), since genuine screenshot/interaction verification could not be performed by this agent in this session.

## Next Phase Readiness

Both confirmed real-Safari Health-page bugs from this round are closed and pinned by harness checks, with one gap-arithmetic discrepancy explicitly recorded (not silently resolved) for the orchestrating session's own live-browser pass. `companion/test_status_pages.py` 84/84; `companion/test_config_page.py` 61/61; `companion/test_view_pages.py` 43/43; `companion/test_companion_app.py` 105/105 (one transient network-timing-dependent failure on `/poll-now` observed and reproduced as pre-existing/unrelated — passes cleanly on rerun with zero code changes, confirmed against the pre-task commit too); `companion/test_contrast_check.py` 36/36; `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing `server/test_poll_loop.py` panel.bin digest mismatch (unrelated, already logged in prior STATE.md quick-task rows), with no coverage-gate shortfall. 06.6.4.1-09's closing checkpoint remains open on plan 09's Task 2 (28-item developer checklist) — this task closes another reactive-fix-cycle batch of real gaps the developer found continuing that checklist; the pixel-level items above, and the gap-arithmetic discrepancy specifically, should be folded into that same checklist pass.

---
*Phase: quick-260902-bl2*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 5 files (companion/layout.py, companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py, this SUMMARY) confirmed present on disk. All 3 task commit hashes (f27042a, 5ae4548, b0e19d5) confirmed present in git log.
