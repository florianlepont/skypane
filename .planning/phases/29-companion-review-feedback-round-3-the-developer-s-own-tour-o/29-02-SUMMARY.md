---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 02
subsystem: ui
tags: [companion, airlines-page, css, tab-bar, page-order, python-stdlib-http]

requires:
  - phase: 29-01
    provides: "confirmation that the page-wide editing toggle is already gone, so CFG-82's 'any remaining editing affordance' has nothing left above the gallery to relocate"
provides:
  - "Compagnies' render() returns page_header, filter_html, the gallery grid, gap_strip_html, lightbox_html, resolve_html — filter and gallery are the first two things under the title, the unidentified-prefix strip is a secondary section below the gallery"
  - "companion/static/style.css's .tab-bar__pill horizontal margin at 2px (calc(var(--space-xs) / 2)), so the longest tab-bar label fits its resolved pill box without shrinking the 78x56px tap area"
affects: [29-03, 29-04, 29-05, 29-06]

tech-stack:
  added: []
  patterns:
    - "A page-order regression is asserted as a chain of rendered.index() relationships across five stable literals, never as a literal string offset — the same idiom quick task 260921-n2n's CFG-70 hit-target check already established for CSS-derived numbers, applied here to HTML section order."

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/static/style.css
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "Resolved A2 (CFG-82's 'any remaining editing affordance moves to a secondary section') by inspection rather than by moving anything: 29-01 already deleted the one page-wide editing toggle; the manual-resolutions summary button lives inside the filter bar as a filter control (22-11's own framing), and the resolve flow's controls render only under ?resolve=..., never on the default view — neither is 'above the gallery' on the page this reorder actually renders, so neither moved. Recorded in render()'s own docstring as a SUPERSEDED-in-place paragraph, following this file's established convention."
  - "The tab-bar fit check's per-character advance (6.5px at 11px font-size) is MEASURED from the audit's own real-browser figure (65px / 10 characters for 'Compagnies'), not modelled from font metrics — per the plan's own instruction that a measured number beats a modelled one. The audit's 65px is additionally kept as an explicit floor so a future formula tweak cannot silently lower the bar below the one real number this defect was built on."
  - "The tab-bar fit check computes 'available width' at the app's own 360px contract floor (design_direction's stated minimum supported viewport), not at the audit's own 390px device — 360px is the tighter, worst-case cell width (72px vs 78px), so passing at 360px is a stronger guarantee than reproducing the audit's exact 62px figure would have been."

requirements-completed: [CFG-82]

coverage:
  - id: D1
    description: "On Compagnies the filter bar and the known-airline gallery are the first two things under the page title, with the unidentified-prefix strip rendering as a secondary section below the gallery, still carrying its own heading/body announcement"
    requirement: CFG-82
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox"
        status: pass
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder"
        status: pass
    human_judgment: true
    rationale: "Visual reading order and scroll position on a real phone cannot be proven by a Python-only harness (no playwright in this sandbox) — see Human Follow-ups."
  - id: D2
    description: "The existing no-chrome-with-no-data gate (no filter bar, no lightbox when there is nothing to filter) survives the reorder unchanged"
    requirement: CFG-82
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py#_airlines_no_chrome_gate_survives_the_reorder"
        status: pass
    human_judgment: false
  - id: D3
    description: "The mobile tab bar renders the word Compagnies whole at 360px and 390px — the label's own resolved box fits inside the pill, with the 78x56px tap area unaffected"
    requirement: CFG-82
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit"
        status: pass
    human_judgment: true
    rationale: "No playwright is installed in this sandbox, so the real-browser scrollWidth confirmation the audit itself used cannot be reproduced here; the check proves the fit arithmetically from the stylesheet's own tokens and the audit's own measured advance factor instead — see Human Follow-ups."

# Metrics
duration: 22min
completed: 2026-09-21
status: complete
---

# Phase 29 Plan 02: Compagnies Reads Gallery-First, Tab Label Stops Truncating Summary

**Reordered `airlines_page.render()` so the filter bar and gallery lead the page with the unidentified-prefix strip demoted below them, and halved `.tab-bar__pill`'s horizontal margin (8px → 2px) so "Compagnies" fits its 78px-wide mobile tab cell without shrinking the tap area.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-09-21T19:42:00Z
- **Completed:** 2026-09-21T20:04:07Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `render()`'s return expression is now `page_header + filter_html + gallery_grid + gap_strip_html + lightbox_html + resolve_html` — a provable permutation of the same six already-built strings; `total`, `filter_html`'s gate and `lightbox_html`'s gate are byte-identical to before the reorder
- `render()`'s own docstring and the comment block above the return expression both gained a SUPERSEDED-in-place paragraph naming CFG-82, marking Phase 19's D-21 "gap strip first" ordering superseded, and recording the A2 decision (no editing affordance needed relocating — 29-01 already deleted the one that would have)
- `.tab-bar__pill`'s horizontal margin dropped from `var(--space-sm)` (8px) to `calc(var(--space-xs) / 2)` (2px); the vertical component is untouched
- Two new relationship checks in `test_view_pages.py` (a five-literal section-order chain, and a no-chrome-gate survival check with a monkeypatched empty-catalog fixture) plus one retargeted-in-place existing check (`_airlines_gap_strip_renders_before_filter_bar_...` → `_airlines_gap_strip_renders_after_the_gallery_...`)
- One new relationship check in `test_status_pages.py` proving the tab label fits its resolved pill box at the app's 360px contract floor, with the 78x56px cell's height and flex width-basis asserted unchanged as an independent, separately-mutable assertion

## Task Commits

Each task was committed atomically:

1. **Task 1: reorder render() so the filter and the gallery come first, and the unidentified strip second** - `e7895f2` (fix)
2. **Task 2: the tab bar's Compagnies label renders whole at 360px and 390px** - `7016d7d` (fix)

**Plan metadata:** (this commit) — `docs(29-02): complete Compagnies gallery-first + tab label plan`

## Harness Counts (re-derived by running)

| Harness | Before | After | Delta |
|---|---|---|---|
| `test_view_pages.py` | 162/162 | 164/164 | +2 |
| `test_status_pages.py` | 311/311 | 312/312 | +1 |
| `test_config_page.py` | 266/266 | 266/266 | 0 (unchanged, confirmed unaffected) |
| `test_i18n.py` | 24/24 | 24/24 | 0 (no copy changed in this plan) |
| `test_browser_ux.py` | SKIP | SKIP | n/a (no playwright in this sandbox) |
| Full suite (`scripts/run-all-tests.sh`) | — | PASS, all 22 harnesses green | — |

`test_view_pages.py`'s +2: one existing check retargeted in place (net 0, the gap-strip-order check now asserts "after the gallery" instead of "before the filter bar"), one new section-order chain check, one new no-chrome-gate survival check.

`test_status_pages.py`'s +1: one new tab-bar-pill-fit relationship check.

## Mutation Proofs

**1. Task 1's section-order chain check** — swapped `filter_html` and the gallery grid term in `render()`'s return expression (`filter_html + gallery` → `gallery + filter_html`), ran `test_view_pages.py`, quoted the real failure verbatim, then restored the correct order with a matching `Edit` (nothing was staged for this file yet at mutation time, so `git checkout-index -f` had nothing to restore from; the resulting diff was confirmed byte-identical to the pre-mutation state before committing):

```
FAIL on a render with both an eligible gap and at least one curated gallery card, the page's own sections chain title < filter bar < gallery grid < "Unidentified airlines" strip < the lightbox dialog, each literal occurring exactly once (CFG-82, 29-02-PLAN.md) - expected filter before gallery, but got indices title=25 filter=24734 gallery=201 gapstrip=25597 lightbox=26489 (CFG-82, 29-02-PLAN.md)
view-pages: 163/164 checks pass
```

`test_view_pages.py` returned to 164/164 after the revert.

**2. Task 2's fit assertion (Mutation A)** — restored `.tab-bar__pill`'s margin to `var(--space-xs) var(--space-sm)`, ran `test_status_pages.py`, quoted the real failure verbatim, then reverted with a matching `Edit` back to `calc(var(--space-xs) / 2)` (the CSS fix was not yet committed at this point, so nothing was staged for `git checkout-index -f` to restore from):

```
FAIL the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured 6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82, 29-02-PLAN.md) - expected the available label width (56.0px = 72.0px cell [360px viewport / 5 cells] - 2x8.0px margin) to be at least 65.0px (the longest label 'Compagnies''s own requirement, floored at the audit's measured 65px) but it was not (CFG-82, 29-02-PLAN.md)
status-pages: 311/312 checks pass
```

**3. Task 2's tap-area assertion (Mutation B)**, proving it fails independently of the fit assertion — reduced `.tab-bar__link`'s `height` from `56px` to `50px`, ran `test_status_pages.py`, quoted the real failures verbatim (both the new check AND the pre-existing `_tab_bar_css_geometry_surface_and_active_idiom` check caught it independently), then reverted with a matching `Edit` back to `56px`:

```
FAIL the tab bar is display:none until the 959.98px boundary, then fixed to the viewport bottom at 56px plus the safe-area inset on the nav surface with a top hairline, the resting overlay shadow and NO border radius (it is edge-anchored); its cells are `flex: 1 1 0`; its active state reuses the app's one 12%-accent-wash pill idiom byte-for-byte with a :not()-scoped hover placed after it; its label is 11px regular with no label voice; and .has-tab-bar clears the bar at the page foot (X9/D-10, 22-14-PLAN.md Task 1) - expected 'height: 56px' in .tab-bar__link
FAIL the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured 6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82, 29-02-PLAN.md) - expected .tab-bar__link's own resolved height to stay 56px (the 78x56px cell, unchanged by the pill's margin edit), got '.tab-bar__link {\n    flex: 1 1 0;\n    min-width: 0;\n    height: 50px;\n    display: flex;\n    color: var(--color-text);\n    text-decoration: none;\n    font-family: var(--font-ui);\n  }'
status-pages: 310/312 checks pass
```

`companion/static/style.css`'s content was confirmed byte-identical to the pre-mutation, correct version after both reverts (diffed against the pending working-tree change before it was staged); `test_status_pages.py` returned to 312/312.

## Files Created/Modified
- `companion/pages/airlines_page.py` - `render()`'s return expression reordered to page_header/filter/gallery/gap-strip/lightbox/resolve; docstring and the comment block above the return expression both gained a SUPERSEDED-in-place paragraph naming CFG-82 and recording the A2 decision
- `companion/static/style.css` - `.tab-bar__pill`'s horizontal margin changed from `var(--space-sm)` to `calc(var(--space-xs) / 2)`, with a comment recording the audit date, the measured cause and why the tap area is unaffected
- `companion/test_view_pages.py` - one existing check retargeted in place to the new order; two new checks added (the five-literal order chain, the no-chrome-gate survival proof)
- `companion/test_status_pages.py` - added `import companion.i18n_fr.nav as i18n_fr_nav`; one new check added (the tab-bar-pill fit relationship, with an independent tap-area-unchanged assertion)

## Decisions Made
See `key-decisions` in the frontmatter above: the A2 resolution (nothing needed relocating), the measured-not-modelled per-character advance for the tab-label fit check, and the choice of the app's 360px contract floor (rather than the audit's own 390px device) as the check's reference viewport — a stricter, not merely equivalent, guarantee.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retargeted an existing test_view_pages.py check broken by the reorder itself**
- **Found during:** Task 1
- **Issue:** `_airlines_gap_strip_renders_before_filter_bar_with_heading_and_no_grid_placeholder` asserted the OLD order (gap strip before the filter bar) — a direct, mechanical consequence of this task's own `render()` change, since the gap strip now renders after the filter bar and the gallery grid instead.
- **Fix:** Renamed the check to `_airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder` and rewrote its assertions to require the strip index to exceed both the filter bar's and the gallery grid's indices, keeping the "no gap card ever leaks into the curated grid" property the original check proved.
- **Files modified:** companion/test_view_pages.py
- **Verification:** `test_view_pages.py` 164/164
- **Committed in:** e7895f2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — genuine test breakage directly caused by this plan's own production-code change, within the file this plan already owns)
**Impact on plan:** The retarget was necessary for the harness to pass at all after the reorder; it stayed inside `test_view_pages.py`, already in `files_modified`. No scope creep.

## Issues Encountered
All three mutation proofs (Task 1's order-check mutation, and Task 2's two margin/height mutations) were reverted with a matching `Edit` call rather than `git checkout-index -f`, because in every case the file's correct, un-mutated edit was still only on disk — nothing had been `git add`-ed for that file yet at the point each mutation ran, so `git checkout-index -f` would have had nothing to restore from. The property the plan's instruction protects (never lose the correct edit) was preserved regardless: each revert was verified by re-running the harness back to its full pass count, and Task 2's CSS diff was confirmed to be exactly one declaration plus its comment before either task was committed.

## Known Stubs
None.

## Threat Flags
None — this plan permutes already-built strings in `render()` (T-29-02-03: no-chrome gate explicitly re-verified untouched) and changes one CSS margin declaration (T-29-02-01: the 78x56px tap area independently re-verified unchanged). No new network endpoint, auth path, file-access pattern, or schema change was introduced. See the plan's own threat register (T-29-02-01/02/03/SC) for the full disposition table — all four are "already-covered, re-verified" arguments, not new surface.

## Human Follow-ups
Carried from the plan (not blocking — no playwright in this sandbox):
1. On a 360px and a 390px viewport, in French and in English, confirm the tab bar renders `Compagnies` whole with no ellipsis, and that each tab is still comfortable to hit. In the console: `[...document.querySelectorAll('.tab-bar__label')].map(e => [e.textContent, e.scrollWidth, e.clientWidth])` — no label may have `scrollWidth > clientWidth`.
2. On Compagnies at 390px, confirm the filter field and the first gallery row are visible without scrolling past an unidentified-prefix list.

## Next Phase Readiness
Plan 29-02 is complete and unblocks 29-03 through 29-06. No blockers.

## Self-Check: PASSED

All 4 files in `files_modified` confirmed present on disk; both task commit hashes (`e7895f2`, `7016d7d`) confirmed present in `git log`.

---
*Phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o*
*Plan: 02*
*Completed: 2026-09-21*
