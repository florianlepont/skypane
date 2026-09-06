---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 04
subsystem: ui
tags: [python, stdlib-only, server-rendered-html, coverage-gaps, page-composition]

# Dependency graph
requires:
  - phase: "14-02"
    provides: "the Phase 14 attribute/copy vocabulary (_VIEW_PANEL_*_ATTR constants, mode/manual value vocabularies, RESOLVE_HEADING/RESOLVE_CAPTION_TEMPLATE/GAP_CARD_ARIA_TEMPLATE/MANUAL_OVERFLOW_*), the shared rendering functions, and the extended _lightbox_html()/attribute-complete _airline_card_html() trigger this plan's gap cards reuse"
  - phase: "14-03"
    provides: "a.airline-card, .airline-card__placeholder and the [data-filter-set] list-filter.js hook every gap card's markup renders into"
provides:
  - "companion/pages/airlines_page.py: GAP_BLOCK_THRESHOLD (3), GAP_BLOCK_CAP (12), _gap_rows_for_grid(state_dir), _gap_card_html(index, row), _gap_overflow_html(overflow_count)"
  - "companion/pages/airlines_page.py: _gallery_grid_html(pairs, state_dir=None, gap_cards_html='') widened to prepend gap cards inside the same .illustration-grid wrapper"
  - "companion/pages/airlines_page.py: render()'s composition reordered — filter_bar, [14-06's reserved manual-summary insertion point], gap-overflow, grid (gap + art), lightbox, the still-present manual-resolutions management list, then the resolve section moved to the true bottom of the page"
  - "companion/test_status_pages.py: _resolve_slice() retargeted to isolate everything after the shared dialog's closing tag; a new _page_composition_order_matches_ui_spec() check pins the top-to-bottom order directly"
affects: [14-05, 14-06, 14-07, 14-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A page-order helper (_resolve_slice()) anchored on a stable structural marker (the shared dialog's own id + universal closing tag) rather than a hardcoded index into a specific neighboring section's literal — survives any future reordering of everything except the dialog itself"
    - "A grid-composition function's own insertion-point contract stated as an explicit code comment above the return statement, naming the specific future plan by number, so a later editor does not need to re-derive UI-SPEC's binding order from scratch"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/test_status_pages.py

key-decisions:
  - "The management table (_manual_resolutions_section_html()) is still rendered by render() in this plan — 14-06 replaces it with a one-line summary, not this plan. Since 14-06's own reserved insertion point (the bare \"\" placeholder between filter_html and overflow_html) is reserved for that future summary line, not the current table, this plan places the still-full-size manual_section_html directly ahead of resolve_html so the resolve section — moved to the bottom by this same plan — stays the true last element render() emits, exactly as this plan's own must_haves truth requires."
  - "_gap_rows_for_grid() short-circuits to ([], 0) on a falsy state_dir, mirroring _illustration_cache_buster()'s own no-state_dir guard — the plan's action text didn't call this out explicitly, but the function is now called unconditionally by render() (unlike unresolved_row_for_prefix(), which stays gated behind a truthy resolve_prefix), and poll_loop.load_poll_state(None) raises TypeError uncaught by that function's own try/except (which only catches OSError/ValueError)."
  - "_resolve_slice() (test_status_pages.py) was retargeted to anchor on the shared dialog's own id + </dialog> marker as part of Task 1's commit, not deferred to Task 2 as the plan's own task split implied — Task 1's own reorder of render() (moving resolve_html to the end) is what breaks the old filter-bar-anchored slice, and Task 1's own acceptance criteria demand a fully green 157/157 suite, so the retarget could not wait for Task 2's commit without leaving Task 1's tree red."

patterns-established:
  - "A gap card's data-filter-group value is always string-prefixed (\"gap0\"..\"gap11\"), never a bare integer, so it can never collide with the curated grid's own enumerate() sequence sharing the same attribute name — the pattern any future non-integer filter-group source in this file should follow."

requirements-completed: []

coverage:
  - id: D1
    description: "A coverage gap seen at least 3 times renders as an empty, imageless card at the head of the gallery grid, labelled with its example callsign, sorted by sighting count descending, capped at 12 with an overflow line naming what the cap hides and linking to Health"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — 158/158 (5 new Task-1 checks: threshold/sort/cap/overflow, gap-card markup shape, filter-group format/no-collision, overflow-line templating, hostile-callsign escaping)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A gap card's data-filter-group value can never collide with an existing airline card's raw enumerate() index (RESEARCH.md Pitfall 4)"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — _gap_card_filter_group_never_collides_with_curated_integer_groups"
        status: pass
    human_judgment: false
  - id: D3
    description: "The no-JS fallback resolve section now renders as the last element on the page, after the shared dialog, and every existing test that isolates its markup keeps passing against the new position"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — the four pre-existing _resolve_slice()-consuming checks pass unmodified against the retargeted helper; _page_composition_order_matches_ui_spec() pins the order directly (158/158)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A hostile example callsign reaching a gap card is escaped exactly once, matching the discipline already proven for airline names and resolve-section values"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — _gap_card_escapes_hostile_example_callsign"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 04: Gap-Card Rendering and Page-Order Reversal Summary

**Coverage gaps now render as empty, dashed-placeholder cards at the head of the Airlines gallery grid — sorted by sighting count, thresholded at 3, capped at 12 with an overflow line — and the no-JS resolve section moved from the top of the page to the true bottom, behind the shared dialog.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-06T13:19:00Z (approx.)
- **Completed:** 2026-09-06T14:04:33Z
- **Tasks:** 2 completed
- **Files modified:** 2 (`companion/pages/airlines_page.py`, `companion/test_status_pages.py`)

## Accomplishments
- Added `GAP_BLOCK_THRESHOLD = 3` and `GAP_BLOCK_CAP = 12` (D-06's locked numeric values) plus `_gap_rows_for_grid(state_dir)`, which duplicates `health_page.unresolved_rows()`'s own malformed-entry-skip discipline and `(-count, prefix)` sort key over the live unresolved-prefix registry, returning `(shown, overflow_count)`
- Added `_gap_card_html(index, row)`: a real `<a class="airline-card" href="/airlines?resolve={prefix}">` trigger with zero `<img>` tags and no nested `.airline-card__zoom` button, carrying the full `data-view-panel-*` vocabulary (empty `src`/`manual`, populated `caption`/`heading`/`mode`/`scope`/`resolve-prefix`/`first-seen`/`last-seen`/`count`), a string-prefixed `data-filter-group="gap{i}"`, and an `aria-label` naming both the prefix and the callsign
- Added `_gap_overflow_html(overflow_count)` — the empty string when the cap doesn't bite, otherwise D-07's templated line with `<a href="/health">` wrapping only `MANUAL_OVERFLOW_LINK_TEXT`
- Widened `_gallery_grid_html()` to prepend gap cards inside the same `.illustration-grid` wrapper (default `gap_cards_html=""` keeps every existing call site byte-identical)
- Reordered `render()`'s composition to filter_bar → [a reserved `""` placeholder for plan 14-06's future manual-summary line] → gap-overflow → grid (gap + art) → lightbox → the still-present manual-resolutions management list → resolve section (now the true last element on the page)
- Retargeted `test_status_pages.py`'s `_resolve_slice()` to anchor on the shared dialog's own id + `</dialog>` marker instead of the now-relocated filter bar, and added `_page_composition_order_matches_ui_spec()` — a direct, permanent proof of the new top-to-bottom order via five strictly-increasing `rendered.index()` markers
- 6 new checks total (5 in Task 1, 1 in Task 2); `EXPECTED_CHECK_COUNT` moved 152 → 158

## Task Commits

Each task was committed atomically:

1. **Task 1: Gap-card rendering and the gap block (D-01, D-02, D-04, D-05, D-06, D-07)** - `308fe04` (feat)
2. **Task 2: Move the resolve section to the bottom of the page and retarget its test isolation helper** - `0038170` (test)
3. **Follow-up fix (Task 2 acceptance-criteria compliance)** - `34068ba` (fix)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

## Files Created/Modified
- `companion/pages/airlines_page.py` - `GAP_BLOCK_THRESHOLD`/`GAP_BLOCK_CAP`, `_gap_rows_for_grid()`, `_gap_card_html()`, `_gap_overflow_html()`, widened `_gallery_grid_html()`, reordered `render()`
- `companion/test_status_pages.py` - 6 new checks, `_resolve_slice()` retargeted in place, `EXPECTED_CHECK_COUNT` 152 → 158

## Decisions Made
- Kept `_manual_resolutions_section_html(ctx)`'s call and full output in `render()`, positioned directly ahead of `resolve_html` — the plan's own literal reorder formula didn't name this still-existing section, but dropping it would have regressed a currently-shipped, currently-tested feature (four existing `_manual_section_slice()`-based checks) that plan 14-06, not this plan, is scoped to replace. Placing it immediately before `resolve_html` is the only position consistent with both "the management list keeps working unchanged" and "the resolve section is the page's true last element."
- Guarded `_gap_rows_for_grid()` against a falsy `state_dir` (returns `([], 0)` immediately) since it — unlike `unresolved_row_for_prefix()` — is now called unconditionally by `render()`, and `poll_loop.load_poll_state(None)` raises an uncaught `TypeError`
- Retargeted `_resolve_slice()` during Task 1's own commit rather than waiting for Task 2, since Task 1's reorder is what breaks it and Task 1's own acceptance criteria require a fully green 157/157 suite at that commit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_gap_rows_for_grid()` crashed on a falsy `state_dir`**
- **Found during:** Task 1, immediately after wiring `_gap_rows_for_grid()` into `render()`'s unconditional call path
- **Issue:** Two pre-existing checks that call `airlines_page.render({})` (no `state_dir` key at all) started raising `TypeError('expected str, bytes or os.PathLike object, not NoneType')` — `poll_loop.load_poll_state(None)`'s own `_poll_state_path(None)` call raises `TypeError`, which that function's `try/except (OSError, ValueError)` does not catch. This path was previously unreachable with a falsy `state_dir`, since the only other caller of the registry, `unresolved_row_for_prefix()`, is gated behind a truthy `resolve_prefix` that itself implies a real render context.
- **Fix:** Added an explicit `if not state_dir: return [], 0` guard at the top of `_gap_rows_for_grid()`, mirroring `_illustration_cache_buster()`'s own no-`state_dir` short-circuit.
- **Files modified:** `companion/pages/airlines_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` — 157/157 (Task 1); the two previously-failing checks (cache-buster, hostile-airline-name) pass again
- **Committed in:** `308fe04` (Task 1 commit)

**2. [Rule 1 - Bug] Moving `resolve_html` to the end of `render()`'s composition broke `_resolve_slice()` and three of its four consumers**
- **Found during:** Task 1, after completing the render() reorder specified in Task 1's own action text
- **Issue:** `_resolve_slice(rendered)` isolated the resolve section via `rendered[:rendered.index("filter-bar")]` — correct only while the resolve section rendered first. Task 1's own action text explicitly reorders the final concatenation to end with `resolve_html`, which immediately broke three of the four checks that call `_resolve_slice()` (`_resolve_section_four_states_render_correctly`, `_resolve_section_datalist_contract`, `_resolve_section_step_b_reachable_after_gap_cleared`), plus Task 1's own stated acceptance criterion of a fully green 157/157 suite.
- **Fix:** Retargeted `_resolve_slice()` to anchor on the shared dialog's own id + the next `</dialog>` marker, returning everything after it — the exact fix Task 2's own action text specifies, applied one task earlier than the plan's task split implied, since Task 1's own acceptance criteria required it.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` — 157/157 (Task 1)
- **Committed in:** `308fe04` (Task 1 commit)

**3. [Rule 1 - Bug] `_resolve_slice()`'s retargeted docstring still quoted the literal `"filter-bar"` substring Task 2's own acceptance criterion greps for**
- **Found during:** Post-Task-2 acceptance-criteria verification (`sed -n '/def _resolve_slice/,/return/p' ... | grep -c '"filter-bar"'` expected `0`)
- **Issue:** The retargeted docstring's own explanatory prose described the old boundary as `rendered[:rendered.index("filter-bar")]`, which contains the literal quoted substring the acceptance criterion's blunt grep scans for — failing that criterion even though the actual code boundary was already correct.
- **Fix:** Reworded the docstring's historical description without changing its meaning, removing the quoted literal.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** the sed/grep acceptance criterion now returns `0`; `server/.venv/bin/python3 companion/test_status_pages.py` — 158/158
- **Committed in:** `34068ba` (follow-up fix commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — direct, foreseeable consequences of this plan's own render()-reorder and page-composition changes, plus one acceptance-criteria wording fix)
**Impact on plan:** Zero behavioral scope creep. All three fixes make already-intended behavior actually correct/green; no new feature surface was added beyond what the plan specifies.

## Issues Encountered
None beyond the three auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Every gap card's markup carries `data-view-panel-resolve-prefix` on a real `<a>` trigger for plan 14-05's script to auto-open against (D-13/D-14)
- `_gallery_grid_html()`'s widened signature (`gap_cards_html` parameter) and `render()`'s reserved `""` insertion point (between `filter_html` and `overflow_html`) are both in place for plan 14-06's `manual_info_by_name` threading and `_manual_summary_html()` call
- The management table (`_manual_resolutions_section_html()`) is unchanged and still renders in full — plan 14-06 is the one that replaces it with the one-line summary and deletes its six now-orphaned rendering functions
- `companion/pages/airlines_page.py` and `companion/test_status_pages.py` remain this wave's shared-with-nobody claim within this plan's own scope; plans 14-05 (panel-lookup.js) and 14-07 (app.py) touch different files in the same wave
- No file under `server/` was modified, no new dependency was added — the phase's stdlib-only-server boundary and no-new-dependency constraint both hold

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/pages/airlines_page.py
- FOUND: companion/test_status_pages.py
- FOUND commit: 308fe04
- FOUND commit: 0038170
- FOUND commit: 34068ba
