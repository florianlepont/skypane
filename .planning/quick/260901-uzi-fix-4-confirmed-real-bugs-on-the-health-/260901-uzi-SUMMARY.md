---
phase: quick-260901-uzi
plan: 260901-uzi
subsystem: companion-ui

tags: [companion, health-page, design-system, css, harness]

requires:
  - phase: 06.6.3-04
    provides: "UXA-06's `.dashboard-grid { align-items: start }` decision this task reverses"
  - phase: 06.6.4
    provides: "D-09's Display-role retirement and four-size type scale, the constraint finding 4's answer is built to respect"
  - phase: 06.6.4.1
    provides: "the migrated `.page-section` Unresolved-prefixes/Resolution-statistics cards this task adds a nested modifier to"
  - phase: quick-260901-tsa
    provides: "the battery readout's Emphasis-role promotion and reposition ahead of the chart, and the 'battery-trend.js not edited' non-goal this task deliberately reverses"
provides:
  - "Health page's Server & data tiles render at equal, stretched height instead of ragged intrinsic heights (finding 1)"
  - "Resolution-statistics table wraps its prose Description column instead of forcing horizontal overflow (finding 2)"
  - "layout.data_table()'s `prose` keyword — a reusable, default-inert opt-out from the shared `.data-table { min-width: max-content }` no-crop floor for any future table whose content is prose rather than short values"
  - "The battery readout's humanised `(value, when)` format reaches both the resting page AND every hover/tap/keyboard interaction, via a shared server-side helper and a new `data-when` DOM attribute battery-trend.js reads instead of reformatting (finding 3)"
  - "A `page-section--nested` modifier + Emphasis-role demotion rule for any future card nested inside a section heading, so the pattern doesn't need re-deriving next time this shape recurs (finding 4)"
  - "A written, source-grounded verdict on the readings-history disclosure header-clipping report (finding 5) — left open, not silently dropped"
affects: [companion-ui-implementation, 06.6.4.1-closing-checkpoint]

tech-stack:
  added: []
  patterns:
    - "Explicit reversal comments for decision reversals (UXA-06's align-items: start, and 260901-tsa's battery-trend.js non-goal) — state what the prior decision was, why it made sense at the time, and why it's being reversed now, so a future reader citing the old decision can see this task knew and chose"
    - "Table-level opt-out modifier class (data-table--prose) for a shared CSS floor, rather than weakening the floor itself — the floor stays correct for every other table; only the one table whose content violates its assumption opts out, with the source-order dependency pinned by a harness check rather than a comment alone"
    - "One server-side formatting helper feeding every human-facing rendering of the same value (title tooltip, aria-label, seeded text, and a new data-* attribute the client script reads) instead of two independently-maintained format implementations (server template + client JS) that can silently drift"
    - "A modifier class carried only by the elements it structurally applies to (page-section--nested on exactly the two nested cards), not a bare descendant/child selector on the shared base class — avoids silently resizing unrelated pages that share the base class"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/static/battery-trend.js
    - companion/static/style.css
    - companion/test_contrast_check.py
    - companion/test_status_pages.py
    - .planning/STATE.md

key-decisions:
  - "Finding 1 is a deliberate reversal of 06.6.3's UXA-06, not a bug fix — `.dashboard-grid`'s `align-items: start` was added on purpose so Health's shorter tiles would keep their own intrinsic height beside a taller Corroboration tile; the developer measured the shipped result live (107.7 / 261.8 / 140.4px in one row) and asked for the opposite. Recorded as a reversal, with its direction and Health-only blast radius, in the rule's own comment — not silently applied as if the original decision were a mistake."
  - "Finding 2's fix is a table-level opt-out (`data-table--prose`), never a weakened shared floor. `.data-table`'s `min-width: max-content` stays correct for History's wide table and the unresolved-prefix registry; only the Resolution-statistics table, whose Description column carries real prose sentences, opts out. No fixed pixel floor was added to the Description column even though the source sketch used one — a minimum wider than the narrowest container just re-creates the same overflow one breakpoint down."
  - "Finding 3 required editing `companion/static/battery-trend.js` — a deliberate reversal of quick task 260901-tsa's own explicit non-goal (\"battery-trend.js. Not edited.\"), which was correct for a pure reposition and stopped being correct once the readout's FORMAT changed, because that file builds the format itself in `reveal()`. A server-only fix would have been silently undone by the user's first hover. `textContent` remains the script's only content sink; the one new attribute write (`title`) is not an HTML sink, so 06.5-RESEARCH.md's ASVS V5 reasoning is unweakened."
  - "Finding 4's answer explicitly does NOT resize `.stat-tile__value` — 06.6.4 D-09 retired the Display role and moved that selector to the Emphasis role on purpose; introducing a fifth size to win one visual comparison would re-break the four-size-scale claim that retirement was made to restore. The real defect was two structural tiers (section headings and the cards nested inside them) rendering at the same visual tier; the fix demotes the nested tier via a scoped modifier class, not a bare `.page-section h2` selector that would have also resized Settings, History, and Health's own top-level source-fault block."
  - "Finding 5 (readings-history disclosure header clipping) is left explicitly OPEN. Two source-grounded candidates were confirmed present in style.css (`.data-table th`'s zero top padding under a sticky header; `.data-table-wrap th`'s page-canvas sticky background painted inside a card surface, which the file's own comment already flags as never live-validated) but neither has a safe, non-speculative fix from source alone — the first would re-space every table header in the app, the second would fix the in-card tables by breaking History's. No CSS change was shipped for this finding."
  - "Task 4's harness checks needed fixture changes beyond what the plan's own <verify> blocks probed: Section 3's real-HTTP fixture (`_both_tabs_ok_end_to_end`) only seeded one battery reading and no resolved runway events, so neither the readout/chart (needs >=2 numeric readings) nor the prose table (needs resolution_stats total > 0) would have rendered at all in that fixture — added a second battery reading and one resolved runway event so the in-place extension actually exercises the real markup it asserts on, rather than passing vacuously."

requirements-completed: [QUICK-260901-uzi]

coverage:
  - id: finding-1
    description: "Same-row Server & data stat tiles stretch to equal height (UXA-06 reversal), scoped to .dashboard-grid only; .dashboard-shell's separate align-items: start (D-21 sticky sidebar) is untouched"
    requirement: QUICK-260901-uzi
    verification:
      - kind: static
        ref: "companion/test_status_pages.py::_dashboard_grid_stretches_same_row_tiles (new)"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /static/style.css response confirmed to carry align-items: stretch by manual smoke test"
        status: pass
    human_judgment: true
    rationale: "Measured pixel heights in a real browser (desktop and narrow width) were not captured by this executor — no browser-automation tools were bound to this subagent. Handed to the orchestrating session's browser pass."
  - id: finding-2
    description: "layout.data_table()'s prose=False keyword adds a data-table--prose opt-out class, default-inert for every other caller; the Resolution-statistics table opts in and wraps instead of overflowing; .data-table's shared floor stays intact for every other table"
    requirement: QUICK-260901-uzi
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_prose_table_opts_out_alone (new)"
        status: pass
      - kind: static
        ref: "companion/test_status_pages.py::_prose_table_opts_out_alone (new) — pins .data-table--prose's source-order position after .data-table"
        status: pass
    human_judgment: true
    rationale: "The wrapper's real scrollWidth/clientWidth equality at desktop and ~375px widths was not measured in a real browser by this executor. Handed to the orchestrating session's browser pass."
  - id: finding-3
    description: "The battery readout renders a humanised (value, when) pair server-side, shared across the seeded readout, every chart point's tooltip/aria-label, and a new data-when attribute battery-trend.js reads instead of reformatting on hover/tap/arrow-key move; textContent remains the only DOM sink"
    requirement: QUICK-260901-uzi
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_humanised_readout_end_to_end (new)"
        status: pass
      - kind: static
        ref: "companion/test_status_pages.py::_readout_typographic_split_stylesheet_guard (new)"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /health response body carries both readout spans and no raw ISO in the readout's own slice"
        status: pass
    human_judgment: true
    rationale: "The interactive path (hover/tap/Left/Right/Home/End actually updating the readout in place, in the same two-tone form, without reverting to raw ISO) requires a real browser exercising battery-trend.js — not exercised by this executor. Handed to the orchestrating session's browser pass, which is explicitly named as the highest-risk regression point (arrow-key traversal)."
  - id: finding-4
    description: "The nested card-heading tier (Battery trend / Unresolved prefixes / Resolution statistics) is demoted to the Emphasis role via page-section--nested, so it no longer renders at the same visual tier as the D-10 section headings above it; .stat-tile__value is untouched"
    requirement: QUICK-260901-uzi
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_nested_heading_tier_demoted_to_emphasis_role (new)"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /health response body carries page-section--nested exactly twice"
        status: pass
    human_judgment: true
    rationale: "Whether the resulting hierarchy actually reads correctly to a person (section headings unambiguously on top, tile value and card heading reading as peers) is a visual judgment call, not a measurement. Handed to the orchestrating session's browser pass."
  - id: finding-5
    description: "The readings-history disclosure header-clipping report is investigated and left explicitly open, with a written verdict naming both candidates, their line references, and why neither is safely fixable from source alone"
    requirement: QUICK-260901-uzi
    verification:
      - kind: manual
        ref: "See 'Finding 5 Verdict' below"
        status: pass
    human_judgment: true
    rationale: "This finding is explicitly NOT closed by this task. The developer's next real-Safari pass should follow the reproduction steps in the verdict section below."

duration: ~55min
completed: 2026-09-01
status: complete
---

# Quick Task 260901-uzi: Fix 4 Confirmed Real Bugs on the Health Page Summary

**Fixed 4 confirmed, live-measured bugs on the shipped Health page found in real Safari immediately after quick task 260901-tsa landed — same-row stat tiles now stretch to equal height, the Resolution-statistics table wraps instead of overflowing, the battery readout is humanised end-to-end (including a deliberate `battery-trend.js` edit), and the page's nested card headings are demoted to the Emphasis role — and investigated a 5th (readings-history disclosure header clipping), left explicitly open with a written verdict rather than a guess.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-01T21:45Z
- **Tasks:** 4/4 completed
- **Files modified:** 7 (`companion/layout.py`, `companion/pages/health_page.py`, `companion/static/battery-trend.js`, `companion/static/style.css`, `companion/test_contrast_check.py`, `companion/test_status_pages.py`, `.planning/STATE.md`)

## Accomplishments

- **Finding 1 (ragged tile heights):** `.dashboard-grid`'s cross-axis alignment reversed from `align-items: start` (06.6.3's UXA-06, a deliberate choice) to an explicit `align-items: stretch`. The reversal, its direction (shorter tiles grow to the tallest sibling; the naturally-tallest Corroboration tile is never shrunk or clipped), and its verified Health-only blast radius (`dashboard-grid` is emitted from exactly two places, both in `health_page.py::render()`) are all written into the rule's own comment. `.dashboard-shell`'s separate `align-items: start` inside the `@media (min-width: 960px)` block — D-21's sticky sidebar — is untouched; it's the file's only remaining `align-items: start` declaration, now pinned by a harness check.
- **Finding 2 (table overflow):** `layout.data_table()` gained an optional `prose=False` keyword, default-inert (byte-identical output for every existing caller, proven by the verify gate). `_stats_table_html()` (the Resolution-statistics table, the only one whose Description column carries real prose sentences) opts in; the battery readings table and the hand-rolled unresolved-prefix registry table do not. `.data-table--prose { min-width: 0 }` sits after `.data-table` in style.css — the two rules have equal (0,1,0) specificity, so source order alone decides which wins, and that ordering is now pinned by a harness check rather than left to the rule's own comment.
- **Finding 3 (raw-ISO readout):** A new `_battery_reading_parts(mv, ts, now)` helper in `health_page.py` builds one shared plain-text `(value, when)` pair, feeding the seeded readout, each chart point's `<title>` tooltip, each point's `aria-label`, and a new per-point `data-when` attribute. `_battery_readout_block()` now renders two spans (`battery-readout__value mono` / `battery-readout__detail`, the raw ISO moved to the detail span's `title`) instead of one raw-ISO string. `battery-trend.js`'s `reveal()` now reads `data-when` and writes both spans, falling back to its original single-string composition when the attribute or either span is missing (the same one-wave-skew tolerance the file's early-return already documents). `textContent` remains the only content sink; the one new attribute write (`title`) is not an HTML sink.
- **Finding 4 (flattened hierarchy):** Health's two migrated cards (`Unresolved prefixes`, `Resolution statistics`) now carry an additive `page-section--nested` modifier; `_source_fault_block()` is deliberately excluded (it renders at the same structural level as the section headings themselves, not nested under one), with a comment recording that exclusion. A new stylesheet rule (`.page-section--nested > h2, .battery-trend-section > h2`) demotes exactly that tier to the Emphasis role (Body size + semibold, no new font family) — the same role `.stat-tile__value` already uses. `.stat-tile__value` itself is untouched; the comment cites 06.6.4 D-09's Display-role retirement and the design skill's four-size contract as the reason a fifth size was rejected.
- **Finding 5 (disclosure header clipping) — investigated, left OPEN:** See "Finding 5 Verdict" below.
- **Test harness:** 5 new checks added (one stylesheet guard per finding-1 and finding-4's stylesheet half, one markup+stylesheet check per finding-2 and finding-4's markup half, one markup+cross-file-JS check for finding-3), plus Section 3's `_both_tabs_ok_end_to_end()` extended in place (no count change) to assert the nested modifier twice, the prose modifier once, both readout spans, and no raw ISO in the readout's own slice against a real `/health` HTTP response. `EXPECTED_CHECK_COUNT` moved from the real on-disk baseline (77) to 82. Every new/extended check was independently mutated (one bogus literal each) and confirmed to fail — exactly those checks and no others — before being restored to green.
- **Real-service verification:** Started a real `companion/app.py` subprocess against a freshly seeded state directory, signed in over real HTTP, and fetched `/health`, `/static/style.css`, and `/static/battery-trend.js`. Confirmed in the real response bodies: `page-section--nested` appears exactly twice, `data-table--prose` exactly once, the readout renders as `4190 mV` (value span) plus ` — 21:39 UTC (12s ago)` (detail span, muted) with the full ISO only in the detail span's `title` attribute, `data-when=` appears twice (once per chart point), `align-items: stretch` is present in the served stylesheet, and `data-when` is referenced in the served script.

## Task Commits

1. **Task 1:** `ae8dace` — `fix(quick-260901-uzi): stretch same-row stat tiles and demote the nested heading tier` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`
2. **Task 2:** `5357a1c` — `fix(quick-260901-uzi): let the resolution-statistics description column wrap` — `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`
3. **Task 3:** `2b140ee` — `fix(quick-260901-uzi): humanize the battery readout in both the page and the script` — `companion/pages/health_page.py`, `companion/static/battery-trend.js`, `companion/static/style.css`, `companion/test_contrast_check.py`, `companion/test_status_pages.py`
4. **Task 4:** `49b8b30` — `test(quick-260901-uzi): pin the four Health fixes, EXPECTED_CHECK_COUNT +5` — `companion/test_status_pages.py`

## Files Created/Modified

- `companion/layout.py` — `data_table()` gained the optional `prose=False` keyword; docstring extended with the real 1172-in-831 measurement that prompted it
- `companion/pages/health_page.py` — `_battery_reading_parts()` (new shared helper); `battery_sparkline_svg()` gained an optional `now=` parameter; `_latest_numeric_battery_reading()` replaces `_latest_numeric_battery_label()`; `_battery_readout_block()` rewritten to two spans; `render()`'s two migrated cards gained `page-section--nested`; `_stats_table_html()` opts into `prose=True`
- `companion/static/battery-trend.js` — `reveal()` reads `data-when` and writes both readout spans, with the original composition kept as an explicit fallback; two new span lookups beside the existing readout lookup
- `companion/static/style.css` — `.dashboard-grid`'s alignment reversed with the UXA-06 reversal documented; `.data-table--prose` (new, after `.data-table`); `.page-section--nested > h2, .battery-trend-section > h2` (new, Emphasis role demotion); `.stat-tile__value .mono` extended to a two-selector list covering `.battery-readout .mono`; `.battery-readout__detail` (new)
- `companion/test_contrast_check.py` — the muted-detail-on-card-surface pair added to `live_pairs` (was not already pinned)
- `companion/test_status_pages.py` — 5 new checks, 1 in-place live-HTTP extension, several in-place retargets across Tasks 1-3, `EXPECTED_CHECK_COUNT` 77→82
- `.planning/STATE.md` — quick-task log row + frontmatter `stopped_at`/`last_updated`/`last_activity_desc`

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on both decision reversals (UXA-06, and 260901-tsa's "battery-trend.js not edited" non-goal), the table-level opt-out design, the deliberate non-resize of `.stat-tile__value`, finding 5's open verdict, and the Section 3 fixture gap this task found and fixed.

## Finding 5 Verdict — Readings-History Disclosure Header Clipping (OPEN)

**Reproduced in real Safari by the developer, NOT reproduced in the tooling available to this task.** The orchestrating session measured the disclosure's `.data-table-wrap` live in a Chromium-based tool and found no vertical clipping at all (`clientHeight` equal to `scrollHeight`), and found no `max-height`, `overflow`, or sticky mechanism on `.readings-disclosure` itself that could explain clipping mechanically. A fresh read of every rule named in the plan's `read_first` (`summary`, `summary::marker`, `summary::-webkit-details-marker`, `.readings-disclosure`, `.data-table-wrap`, `.data-table th`, `.data-table-wrap th`) confirms both candidates below are real, present-in-source facts — but neither has a safe, non-speculative fix reachable from source alone, and no third candidate was found.

- **Candidate (a):** `.data-table th` declares `padding: 0 var(--space-md) 10px` — zero top padding — while `.data-table-wrap th` makes header cells `position: sticky; top: 0`. A header stuck at the scroll container's exact top edge, with zero space above its own glyphs, means whether the ascenders visibly clip depends on font ascent metrics inside the line box — metrics that genuinely differ between WebKit (Safari) and Blink (Chromium), which is consistent with a defect that reproduces in Safari and not in a Chromium-based measurement tool. **Not applied**: adding top padding to `.data-table th` would re-space every table header in the app — History, the unresolved-prefix registry, and both battery/stats tables — including three surfaces nobody reported a problem on.
- **Candidate (b):** `.data-table-wrap th` paints its sticky background from `var(--color-canvas)` (the page background token) while the battery-readings table renders inside a card surface (`.stat-tile`/`.page-section`), not directly on the page. Style.css's own comment on this rule already pre-registers the token choice as "never live-validated" and names the card-surface token as the equally-valid alternative. **Not applied**: switching to the card-surface token would fix the in-card tables (Airlines, Health) but, per that same comment, would break History's table — the only one in the app long enough for the sticky state to reliably engage — which renders directly on the page background, not inside a card.

**Reproduction the developer's next Safari pass should run:** open the readings disclosure, scroll the table's own `.data-table-wrap` vertically (does the clipping track the scroll, or is it present at rest before any scroll?) and note whether it's present at the very top row (candidate a, sticky-header-adjacent) or persists throughout (would argue against both current candidates and for a third, not-yet-identified cause). If confirmed as candidate (a), the one-declaration fix is adding top padding to `.data-table th` and accepting the app-wide re-spacing. If confirmed as candidate (b), the one-declaration fix is switching `.data-table-wrap th`'s background token and accepting the styling risk to History's table, which should itself be re-verified live afterward.

No CSS change was shipped for this finding. It ships open, by design, per the plan's own instruction not to guess.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking issue] Section 3's real-HTTP fixture didn't seed enough data for the in-place extension to exercise the real markup**

- **Found during:** Task 4, writing the in-place extension to `_both_tabs_ok_end_to_end()`
- **Issue:** The existing Section 3 fixture seeded exactly one battery reading and no resolved runway events. `_battery_section()` only renders the readout/chart when at least two numeric battery rows exist, and `_stats_table_html()` only renders a table (and therefore the prose modifier) when `resolution_stats()`'s total is non-zero. Extending the check to assert on `data-table--prose` and both readout spans against this fixture, unchanged, would have made those assertions fail for a reason unrelated to whether the fixes work — or, worse, if written permissively, would have passed vacuously without ever exercising the real markup.
- **Fix:** Added a second battery reading and one resolved runway event (`route_source="fresh_hit"`) to the fixture, with a comment explaining why each is there.
- **Files modified:** `companion/test_status_pages.py`
- **Commit:** `49b8b30`

None of the plan's actual deliverable code (the 4 fixes) required a Rule 1/2/4 fix — Tasks 1 through 3's action text, followed exactly, produced correct output verified by each task's own automated gate before commit.

## Known Stubs

None. Every value introduced (the humanised battery-reading pair, the prose-table opt-out, the nested-heading modifier, the stretched grid) is wired to real render-time data or a real module-level constant — nothing renders empty/placeholder/mock data.

## Threat Flags

None. This task's `<threat_model>` (T-uzi-01 through T-uzi-06, all `mitigate`, plus T-uzi-SC `accept` for the zero-package-install non-goal) fully covers the surface this plan touches — the new `data-when` attribute crossing into `battery-trend.js`, the demoted heading tier's accessibility surface, the muted detail text's contrast, and `data_table()`'s new keyword reaching only its intended caller. No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary was introduced.

## Issues Encountered

- No package installs, no auth gates, no architectural questions.
- No computer-use/chrome-devtools MCP tools were bound to this subagent, matching quick task 260901-tsa's own precedent. Automated verification (harness checks plus a real `companion/app.py` subprocess/login/HTTP fetch) was completed to the fullest extent possible without those tools; genuine pixel-level visual confirmation is explicitly outstanding — see "Pixel-Level Items Outstanding" below.

## Pixel-Level Items Outstanding for the Orchestrating Session's Browser Pass

The live-HTTP half is automated and passing (Section 3's extended `_both_tabs_ok_end_to_end()`, plus the manual smoke test recorded above). These items genuinely cannot be settled from raw HTML/CSS text and require a real rendered browser:

1. The three Server & data tiles measure the same height in a real browser, with the Corroboration tile still setting that height and neither of the shorter two clipped or oddly hollow-looking at its new height (a judgment call, not a measurement).
2. The Resolution-statistics table no longer scrolls horizontally at desktop width (`scrollWidth` == `clientWidth`), and the Description column wraps to multiple lines instead of running off — re-measure at ~375px too, where the column is tightest.
3. The battery readout reads as one emphasised figure followed by muted, humanised detail, and hovering, tapping, and arrowing (Left/Right/Home/End) through the chart updates it in place, in that same two-tone form, without reverting to a raw timestamp and without the chart shifting. The arrow-key path is the one most likely to regress silently.
4. The two card headings ("Unresolved prefixes", "Resolution statistics") and the "Battery trend" heading now read as subordinate to "Screen"/"Server & data" above them, and the tile value no longer reads as the weakest thing on screen. If the developer still reads the tile value as under-weighted after this, the next lever is re-opening 06.6.4 D-09 as a design decision, not a quick-task size bump.
5. Finding 5, in real Safari: open the readings disclosure and report whether the header clipping reproduces, and whether it is present at rest or only once the table's own wrapper is scrolled — see the reproduction steps in "Finding 5 Verdict" above.

## User Setup Required

None to run the code. **Recommended before signing off this checkpoint item:** a real-browser visual pass on `/health` (desktop + ~375px, light + dark, real Safari for finding 5 specifically), since genuine screenshot/interaction verification could not be performed by this agent in this session.

## Next Phase Readiness

All 4 confirmed real-Safari Health-page bugs from this round are closed and pinned by harness checks; the 5th is investigated and left honestly open with a written, source-grounded verdict and a concrete reproduction the developer's next Safari pass should run. `companion/test_status_pages.py` 82/82; `companion/test_config_page.py` 61/61; `companion/test_view_pages.py` 43/43; `companion/test_companion_app.py` 105/105; `companion/test_contrast_check.py` 36/36; `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing `server/test_poll_loop.py` panel.bin digest mismatch (unrelated, already logged in prior STATE.md quick-task rows), with no coverage-gate shortfall. 06.6.4.1-09's closing checkpoint remains open on plan 09's Task 2 (28-item developer checklist, Group A only substantively walked through) — this task closes another reactive-fix-cycle batch of real gaps the developer found continuing that checklist; the pixel-level items above and finding 5's real-Safari reproduction should be folded into that same checklist pass.

---
*Phase: quick-260901-uzi*
*Completed: 2026-09-01*
