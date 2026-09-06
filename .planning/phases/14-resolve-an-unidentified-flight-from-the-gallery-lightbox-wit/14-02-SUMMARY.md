---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 02
subsystem: ui
tags: [python, stdlib-only, server-rendered-html, dialog, dom-contract]

# Dependency graph
requires:
  - phase: "14-01"
    provides: "the three classified lightbox token tuples and the reflection-driven _view_panel_attr_constants_all_classified() coverage check that this plan's new attributes must classify into"
provides:
  - "companion/pages/airlines_page.py: 11 new _VIEW_PANEL_*_ATTR constants (15 total), 5 mode/manual value constants, 4 dialog class constants, RESOLVE_CONTEXT_DD_CLASSES, and the Phase 14 Full Copy Deck constants (GAP_CARD_ARIA_TEMPLATE, MANUAL_CHIP_ACTIVE_TEXT, MANUAL_DELETE_CAPTION, MANUAL_SUPERSEDED_NOTE_TEMPLATE, MANUAL_OVERFLOW_TEMPLATE/LINK_TEXT, MANUAL_SUMMARY_TEMPLATE/_NONE), plus FLASH_MANUAL_NAME_UNUSABLE (declared, wired by plan 14-07)"
  - "companion/pages/airlines_page.py: four one-definition/two-call-sites shared rendering functions — _resolve_name_form_html(prefix_value, id_suffix), _resolve_upload_form_html(action, id_suffix), _manual_delete_form_html(action), and an extended _resolve_context_html(row, now, id_suffix='')"
  - "companion/pages/airlines_page.py: an extended _lightbox_html() carrying heading/manual-note/resolve-context/resolve-name/resolve-upload/delete before Close, and an attribute-complete _airline_card_html() trigger (all 15 data-view-panel-* names, empties included)"
  - "companion/pages/airlines_page.py: _resolve_section_html() renders the shared delete form in its two entry-bearing branches (Step B, already-resolved) — D-09 amendment, the no-JS delete capability D-12 promised would survive"
  - "companion/test_view_pages.py: _LIGHTBOX_RENDER_ONLY_TOKENS populated with the 11 new attribute values, 4 new/promoted dialog classes, and resolve-context/resolve-upload-zone"
affects: [14-03, 14-04, 14-05, 14-06, 14-07, 14-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One-definition/two-call-sites shared rendering functions for form markup that must appear identically in both a no-JS fallback section and a JS dialog's static copy, differentiated only by an id_suffix parameter (or, for the id-less delete form, no suffix at all since it names no id)"
    - "Attribute-complete triggers: every optional data-view-panel-* attribute is emitted present-but-empty on a card that doesn't use it, never omitted, so a client script's blanket attr-copy-on-every-open idiom can never leak a stale value from the previous click"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "LIGHTBOX_RESOLVE_NAME_CLASS and LIGHTBOX_DELETE_CLASS are applied to the outer <form> tag in both call sites (no-JS fallback and dialog) since a shared function cannot render two different wrapper tags for the same output — the no-JS fallback simply carries a spacing class style.css only ever selects from inside .lightbox"
  - "_resolve_context_html() gained an id_suffix parameter for call-shape parity with the other three shared functions, but the parameter has no effect on its own output today since this <dl> emits no id-bearing child in either mode"
  - "_manual_delete_form_html() deliberately has no id_suffix parameter — its output names no id at all, so two copies (dialog + fallback) coexist with zero collision risk, exactly as 14-UI-SPEC.md's Component Inventory states"

patterns-established:
  - "Shared rendering functions accept an id_suffix parameter appended to every id-bearing child's id/list/for attributes, so a fallback call (id_suffix='') stays byte-identical to the pre-existing markup while a dialog call (id_suffix='-dialog') never collides with it when both render on the same page"

requirements-completed: []

coverage:
  - id: D1
    description: "The Phase 14 copy deck, trigger attribute vocabulary (11 new data-view-panel-* constants, 15 total), value vocabularies, dialog class constants and RESOLVE_CONTEXT_DD_CLASSES exist as named module constants with no duplicated literals, and G-01's flash key is declared"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — 150/150 (unchanged count)"
        status: pass
      - kind: unit
        ref: "grep -c constants/concatenation checks per Task 1's acceptance criteria (attr count 15, resolve-context/resolve-upload-zone literal counts 1, FLASH_MANUAL_NAME_UNUSABLE present, MANUAL_OVERFLOW concatenation, RESOLVE_CONTEXT_DD_CLASSES length)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Four shared rendering functions (_resolve_name_form_html, _resolve_upload_form_html, _manual_delete_form_html, extended _resolve_context_html), one definition each; _resolve_section_html() calls all four and renders the delete form in exactly its two entry-bearing branches; every Phase 13 element id is unchanged on the id_suffix='' path"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — 150/150 (every Phase 13 check passes unmodified) and companion/test_companion_app.py — 159/159 (POST routes untouched)"
        status: pass
      - kind: unit
        ref: "behavioural REPL check against a seeded state dir: Step A/stale render 0 delete forms, Step B/already-resolved render 1 each; id_suffix='' vs '-dialog' id byte-identity confirmed for both suffixable forms"
        status: pass
    human_judgment: false
  - id: D3
    description: "The shared dialog carries every element the three view modes need in UI-SPEC's binding order with Close last, every trigger carries the complete 15-name attribute vocabulary (empties included), there are no duplicate DOM ids when the dialog and the no-JS fallback coexist, and the new tokens are classified into _LIGHTBOX_RENDER_ONLY_TOKENS"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_view_pages.py — 55/55; server/.venv/bin/python3 companion/test_status_pages.py — 150/150; scripts/run-all-tests.sh — Result: PASS, 93% coverage"
        status: pass
      - kind: unit
        ref: "programmatic checks: exactly one <dialog>, dialog element order (image/caption/note/heading/manual-note/resolve-context/resolve-name/resolve-upload/replace/delete/close), zero duplicate ids with a live gap + resolve_prefix seeded simultaneously, every _LIGHTBOX_RENDER_ONLY_TOKENS member absent from panel-lookup.js"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 02: Shared Rendering Machinery Summary

**Extracted the resolve-name, resolve-upload and manual-delete forms plus the sighting-context block into four one-definition/two-call-sites functions the no-JS fallback and the shared dialog both call, widened every gallery card's trigger to carry the full 15-attribute data-view-panel-* vocabulary, and restored the no-JS delete capability (D-09 amendment) in the resolve section's two entry-bearing branches.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-06T12:17:00Z (approx.)
- **Completed:** 2026-09-06T13:12:55Z
- **Tasks:** 3 completed
- **Files modified:** 3 (`companion/pages/airlines_page.py`, `companion/test_view_pages.py`, `companion/test_status_pages.py`)

## Accomplishments
- `airlines_page.py` gained the full Phase 14 attribute vocabulary (11 new `_VIEW_PANEL_*_ATTR` constants, 15 total), value vocabularies, dialog class constants, `RESOLVE_CONTEXT_DD_CLASSES`, and the Full Copy Deck — every string a single module constant, no duplicated literal
- Four shared rendering functions now exist with exactly one definition and two call sites each: `_resolve_name_form_html()`, `_resolve_upload_form_html()`, `_manual_delete_form_html()`, and an extended `_resolve_context_html(row, now, id_suffix="")` that accepts `row=None` for the dialog's five-empty-`<dd>` placeholder copy
- `_resolve_section_html()` (the no-JS fallback) now renders the shared delete form in its two entry-bearing branches (Step B, already-resolved) and in neither entry-less branch — the D-09 amendment (2026-09-06) restoring the no-JS delete capability D-12 originally promised would survive
- `_lightbox_html()` is extended with heading, manual-note, resolve-context, resolve-name form, resolve-upload zone and delete form — in UI-SPEC's exact binding order, Close still last — all built through the same shared functions with `id_suffix="-dialog"`
- Every `.airline-card__zoom` trigger now carries all fifteen `data-view-panel-*` attributes; a plain curated art card sets `mode="art"` and leaves the other ten present-but-empty rather than omitted
- `test_view_pages.py`'s `_LIGHTBOX_RENDER_ONLY_TOKENS` is populated with the eleven new attribute values plus four new/promoted dialog classes plus `resolve-context`/`resolve-upload-zone`, closing plan 14-01's staging tuple

## Task Commits

Each task was committed atomically:

1. **Task 1: The Phase 14 copy deck and trigger attribute vocabulary** - `e867563` (feat)
2. **Task 2: Four shared rendering functions, and the no-JS fallback's delete form (D-09 amendment)** - `7f8e5f0` (feat)
3. **Task 3: Extend the shared dialog and complete every trigger's attribute vocabulary** - `9ad018f` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

_Note: both Task 2 and Task 3 were `tdd="true"`; each was verified test-first against a throwaway REPL (a deliberately unexercised input path — e.g. Step A rendering zero delete forms before the D-09 amendment landed — confirmed to fail as expected) and then brought to a fully green working tree before committing, matching plan 14-01's own precedent: no separate RED-phase commit exists because the plan's own harness-exact-count gates require every commit to be green._

## Files Created/Modified
- `companion/pages/airlines_page.py` - the full Phase 14 constant vocabulary, four shared rendering functions, the D-09 amendment in `_resolve_section_html()`, the extended `_lightbox_html()`, and the attribute-complete `_airline_card_html()` trigger
- `companion/test_view_pages.py` - `_LIGHTBOX_RENDER_ONLY_TOKENS` populated (was seeded empty by plan 14-01)
- `companion/test_status_pages.py` - three assertions retargeted in place (see Deviations below); no `EXPECTED_CHECK_COUNT` change (stays 150)

## Decisions Made
- Applied `LIGHTBOX_RESOLVE_NAME_CLASS`/`LIGHTBOX_DELETE_CLASS` directly on the shared forms' own `<form>` tags in both call sites, rather than only inside the dialog — a shared function cannot emit two different wrapper shapes for the same output, and the no-JS fallback's copy simply carries a spacing class `style.css` (plan 14-03) only ever selects from inside `.lightbox`
- Kept `_resolve_context_html()`'s `id_suffix` parameter even though it has no effect on this particular function's output today, for call-shape parity with the other three shared functions and to leave room for a future id-bearing child without a signature change
- `_manual_delete_form_html()` intentionally has no `id_suffix` parameter (per 14-UI-SPEC.md's own explicit reasoning) — documented in its docstring so a future editor does not "fix" the asymmetry

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 3's widened attribute vocabulary broke three existing `companion/test_status_pages.py` assertions that counted bare substrings across the whole rendered page**
- **Found during:** Task 3, after widening every trigger's attribute vocabulary and extending `_lightbox_html()`
- **Issue:** Three Phase-13-era checks assumed a single occurrence of a substring that the new markup legitimately multiplies or which the widened vocabulary makes ambiguous:
  - `body_text.count('action=""')` expected `1` (the replace form); the eleven-attribute widening adds `data-view-panel-upload-action=""` and `data-view-panel-delete-action=""` to every one of the 27 curated cards (each containing the literal substring `action=""` without being a real HTML `action` attribute at all), and the dialog now legitimately has three real empty-action forms (replace, resolve-upload, delete), inflating the naive count to 57.
  - `re.findall(r'<input type="file" id="([^"]+)"', rendered)` expected exactly one match; the dialog now also renders the resolve-upload form's own file input (`manual-illustration-input-dialog`), making two.
  - `rendered.count('<use href="#icon-upload"')` expected exactly one; the dialog's resolve-upload form reuses the identical icon glyph, making two.
  - `_resolve_section_datalist_contract()` counted `<option value=` across the *whole page* (expected 27); the dialog now unconditionally renders its own 27-option datalist copy too, doubling the naive count to 54.
- **Fix:** Retargeted all four assertions in place, with an explanatory comment at each site: the `action=""` check now uses a space-prefixed substring (`' action=""'`) to exclude the hyphenated `data-*-action=""` false matches and expects `3`; the file-input and icon-upload counts are updated to `2`; the datalist check is re-scoped onto the existing `_resolve_slice()` helper (already used by every sibling resolve-section check) so it inspects only the no-JS fallback's own datalist, not the dialog's. No `EXPECTED_CHECK_COUNT` change — these are the same four checks, re-scoped, not new ones.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` — 150/150; `scripts/run-all-tests.sh` — Result: PASS
- **Committed in:** `9ad018f` (Task 3 commit)
- **Note on plan-scope deviation:** the plan's own frontmatter `files_modified` and Task 3's `<files>` list only name `companion/pages/airlines_page.py` and `companion/test_view_pages.py`; this fix required touching `companion/test_status_pages.py` as well, which the plan's `<verification>` section's literal `git diff --name-only` claim does not anticipate. Keeping the full test suite green (an explicit, non-negotiable requirement of both this task and the phase) took priority over the narrower stated file scope. This is a one-file scope expansion, purely to existing test assertions — no production code outside `airlines_page.py` was touched.

---

**Total deviations:** 1 auto-fixed (Rule 1 — four related test-assertion retargets in one file, all a direct, anticipated-in-substance consequence of Task 3's own widened vocabulary)
**Impact on plan:** Zero behavioral scope creep in production code. The retargeted assertions verify the identical properties they always did (a real, present empty-action placeholder; the replace form's own file input uniqueness; the icon glyph's shared-sprite provenance; the no-JS fallback's own datalist completeness) — they are simply no longer confused by the new markup this plan's own Task 3 legitimately adds.

## Issues Encountered
None beyond the one auto-fixed deviation above (and the docstring-substring self-collisions caught and fixed against Task 2's own strict grep acceptance criteria before committing — not tracked as a formal deviation since they were caught and corrected before any commit, never landing in the tree).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four shared rendering functions are ready for plan 14-04 (page composition) and plan 14-05 (the JS attribute-copy wiring) to build on — `_LIGHTBOX_RENDER_ONLY_TOKENS` is the explicit staging tuple plan 14-05 is expected to empty once `panel-lookup.js` learns to read this vocabulary
- Every trigger's attribute-complete markup is in place for plan 14-06 (gap/manual card injection) to set real, non-empty values on gap and manual-resolution cards without any further markup-shape change to `_airline_card_html()`
- `companion/pages/airlines_page.py` remains this wave's exclusive claim; no other plan in this wave touched it
- No file under `server/` was modified, no new dependency was added, and `companion/app.py` remains untouched — the phase's stdlib-only-server boundary and no-new-dependency constraint both hold

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/pages/airlines_page.py
- FOUND: companion/test_view_pages.py
- FOUND: companion/test_status_pages.py
- FOUND commit: e867563
- FOUND commit: 7f8e5f0
- FOUND commit: 9ad018f
