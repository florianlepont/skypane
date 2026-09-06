---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 05
subsystem: ui
tags: [javascript, es5, vanilla-js, dialog, dom-contract, progressive-enhancement]

# Dependency graph
requires:
  - phase: "14-02"
    provides: "the Phase 14 attribute/copy vocabulary (11 new _VIEW_PANEL_*_ATTR constants, mode/manual value vocabularies, the four/six new dialog classes including RESOLVE_CONTEXT_DD_CLASSES) and the extended _lightbox_html() this script now drives"
provides:
  - "companion/static/panel-lookup.js: an imageless-open branch (image.hidden/removeAttribute, never src=\"\"), six new optional-element lookups (resolve-name form, resolve-upload zone, delete form, heading, manual-note, resolve-context), a mode/manual visibility-toggle branch matching UI-SPEC's two toggle tables, evt.preventDefault() once a trigger is confirmed, and a factored openFromTrigger(trigger) function called from both the click listener and a location.search-driven init-time lookup (D-13/D-14)"
  - "companion/static/panel-lookup.js: (Rule 2 addition beyond the plan's literal task text) the resolve-name form's hidden prefix input and the resolve-context block's five per-field <dd> hooks (resolve-context__prefix/-first-seen/-last-seen/-count/-callsign) are populated on every open, matching 14-UI-SPEC.md's own stated JS-hook contract for those elements"
  - "companion/test_view_pages.py: _LIGHTBOX_RENDER_ONLY_TOKENS emptied to () with every staged token promoted into _LIGHTBOX_AIRLINES_ONLY_TOKENS; 8 new source-content checks pinning the script's contract without a live DOM; EXPECTED_CHECK_COUNT 55 -> 63"
affects: [14-06, 14-07, 14-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared populate-and-open function (openFromTrigger(trigger)), one definition reachable from two entry points (a click event and a location.search-driven init-time lookup) — the file's first non-click entry point since it shipped"
    - "ES5-safe, dependency-free query-string parsing (no URLSearchParams) mirroring the file's own hand-rolled style, with the one location.search read placed after the click listener is wired and the resulting querySelector wrapped in try/catch so a malformed or non-matching value degrades to a silent no-op rather than breaking the rest of the script"

key-files:
  created: []
  modified:
    - companion/static/panel-lookup.js
    - companion/test_view_pages.py
    - companion/test_companion_app.py

key-decisions:
  - "Populated the resolve-name form's hidden prefix input and the resolve-context block's five per-field <dd> classes even though the plan's own Task 1 action text only lists six element lookups (not these two) — 14-UI-SPEC.md's Component Inventory explicitly names plan 14-05 as the consumer of both (\"JS fills the hidden prefix input's .value at click time\"; \"each <dd> additionally carries one of five new classes ... so the dialog's copy has stable JS hooks (plan 14-05)\"), and without this, Step A's dialog submit would always post an empty prefix and the sighting-context block would stay permanently blank regardless of which card was clicked"
  - "Read (but do not write anywhere) data-view-panel-scope on every open — 14-UI-SPEC.md's Copy Deck names .lightbox__resolve-scope as this value's destination, but no page module (14-02/14-04) actually renders that element; since this plan owns no file that could add it, the value is read for the correctness rule's sake and left with nowhere to go, documented inline for whichever future plan adds the element"
  - "Wrapped the load-time auto-open's querySelector([data-view-panel-resolve-prefix=...]) call in try/catch, and placed the whole location.search-driven block after the click listener is already registered — an operator-editable query value could otherwise contain a character (a stray quote) that makes the constructed attribute-selector string syntactically invalid, and an uncaught exception at that point in the IIFE would have silently prevented the click listener from ever being wired"

patterns-established:
  - "A script's one function reachable from a click stays the single population/open mechanism; any new entry point (load-time, future keyboard shortcut, etc.) must call that same function rather than growing a second copy of the same logic"

requirements-completed: []

coverage:
  - id: D1
    description: "panel-lookup.js opens the shared dialog with no image and no network request when a trigger carries an empty data-view-panel-src (D-02) — image.hidden/removeAttribute, never image.src=\"\""
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py::_panel_lookup_never_sets_image_src_to_empty_string, _panel_lookup_remove_attribute_src_is_conditional"
        status: pass
      - kind: manual_procedural
        ref: "14-08-PLAN.md Task 2 step 1 (Network-panel confirmation of zero requests) — not yet run"
        status: unknown
    human_judgment: true
    rationale: "Whether removeAttribute genuinely suppresses the browser's own network request can only be confirmed against a real browser's Network panel — the stdlib harness can only pin the source shape, not the runtime request behavior (RESEARCH.md's Validation Architecture)."
  - id: D2
    description: "Every trigger shows exactly the right optional form(s) for its mode/manual state and hides every other one, using the existing hidden-toggle idiom, with hidden set before showModal() runs"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py::_panel_lookup_mode_hidden_toggles_before_showmodal"
        status: pass
      - kind: manual_procedural
        ref: "14-08-PLAN.md Task 2 step 2 — not yet run"
        status: unknown
    human_judgment: true
    rationale: "Actual hidden-toggling and showModal()'s native autofocus placement require a JS engine against a live DOM; this project's harness has no headless browser."
  - id: D3
    description: "The dialog can open from page load against a URL-carried ?resolve={prefix}, using the identical population logic a click would run, locating its trigger by data-view-panel-resolve-prefix"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py::_panel_lookup_shared_populate_function_two_call_sites, _panel_lookup_location_search_read_once_outside_click_only_function"
        status: pass
      - kind: manual_procedural
        ref: "14-08-PLAN.md Task 3 (load-time auto-open) — not yet run"
        status: unknown
    human_judgment: true
    rationale: "Load-time showModal() firing and the resulting dialog content require a real browser session; the stdlib harness proves the source-level factoring and the exact selector contract only."
  - id: D4
    description: "Every data-view-panel-* attribute is copied on every open using the attr || \"\" idiom, never conditionally skipped, so no click can leak a previous click's content onto the next card"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py::_panel_lookup_eleven_new_attrs_present_in_source, _lightbox_dom_contract_three_file_guard, _view_panel_attr_constants_all_classified"
        status: pass
    human_judgment: false
  - id: D5
    description: "An <a>-shaped trigger (gap/manual/needs-artwork cards) never navigates the browser away — evt.preventDefault() runs unconditionally once a trigger is confirmed"
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py::_panel_lookup_prevent_default_once_correctly_positioned"
        status: pass
    human_judgment: false

# Metrics
duration: 23min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 05: panel-lookup.js — Imageless Open, Form Toggling, and Load-Time Auto-Open Summary

**Extended the one shared `panel-lookup.js` script to open the dialog imagelessly for a gap card, show exactly the right optional form per trigger's mode/manual state, intercept `<a>`-shaped trigger navigation, and auto-open itself at page load against a URL-carried resolve prefix — all through one factored `openFromTrigger()` function shared by the click listener and the new load-time entry point.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-09-06T16:14:26+02:00 (approx., prior commit's timestamp)
- **Completed:** 2026-09-06T16:37:32+02:00
- **Tasks:** 2 completed
- **Files modified:** 3 (`companion/static/panel-lookup.js`, `companion/test_view_pages.py`, `companion/test_companion_app.py`)

## Accomplishments
- Replaced the unconditional `image.src = src` with a branch: an empty `data-view-panel-src` now yields `image.hidden = true` plus `removeAttribute("src")`/`("alt")` — never `image.src = ""`, the documented cross-browser spurious-request bug (D-02, RESEARCH.md Pitfall 1)
- Added six new optional dialog-element lookups (`resolveNameForm`, `resolveUploadZone`, `deleteForm`, `heading`, `manualNote`, `resolveContext`), each guarded independently at its point of use, mirroring the existing `replaceForm` idiom exactly
- Added the mode-governed visibility toggle (`resolveNameForm`/`resolveUploadZone`/`replaceForm` per UI-SPEC's mode table) and the orthogonal manual-governed toggle (`deleteForm`/`manualNote`), every `hidden` assignment set before `dialog.showModal()` runs (RESEARCH.md Pitfall 3)
- Added `evt.preventDefault()` unconditionally once a trigger is confirmed non-null, making an `<a>`-shaped gap/manual/needs-artwork trigger's click never navigate the browser (D-12)
- Copied every one of the eleven new `data-view-panel-*` attributes on every open via the existing `attr || ""` idiom, including (Rule 2 addition) the resolve-name form's hidden prefix field and the resolve-context block's five per-field `<dd>` hooks 14-02 built specifically for this consumer
- Factored the entire populate-and-open body into one `openFromTrigger(trigger)` function (RESEARCH.md Pitfall 2's mandatory factoring), called from the click listener and from a new `location.search`-driven init-time lookup satisfying D-13/D-14 with one mechanism
- Added an ES5-safe, dependency-free `location.search` parser and wrapped its `querySelector([data-view-panel-resolve-prefix=...])` lookup in try/catch, placed after the click listener is already wired, so a malformed or non-matching URL value degrades to a silent no-op rather than an uncaught exception
- `test_view_pages.py`: promoted every `_LIGHTBOX_RENDER_ONLY_TOKENS` member into `_LIGHTBOX_AIRLINES_ONLY_TOKENS` (now empty tuple staged), added 8 new source-content checks pinning the script's contract without a live DOM; `EXPECTED_CHECK_COUNT` 55 → 63

## Task Commits

Each task was committed atomically:

1. **Task 1: Imageless open, the three new optional forms, mode/manual toggling, and `<a>` interception** - `57f89e1` (feat)
2. **Task 2: Load-time auto-open (D-13/D-14), source-content checks, and token promotion** - `e8ff3af` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

## Files Created/Modified
- `companion/static/panel-lookup.js` - imageless-open branch, six new optional lookups, mode/manual visibility toggle, `<a>` interception, factored `openFromTrigger()`, ES5-safe `location.search` parsing and load-time auto-open
- `companion/test_view_pages.py` - token promotion (`_LIGHTBOX_RENDER_ONLY_TOKENS` → `()`), 8 new source-content checks, `EXPECTED_CHECK_COUNT` 55 → 63
- `companion/test_companion_app.py` - one pre-existing assertion's expected count widened in place (see Deviations below)

## Decisions Made
- Populated the resolve-name form's hidden prefix input and the resolve-context block's five `<dd>` hooks even though the plan's own Task 1 action text enumerates only six element lookups — 14-UI-SPEC.md's Component Inventory explicitly names this plan as the intended consumer of both, and omitting them would leave Step A's dialog submit posting an empty prefix and the sighting-context block permanently blank (see Deviations, Rule 2)
- Left `data-view-panel-scope` read-only (no write target) since `.lightbox__resolve-scope` — the element UI-SPEC's Copy Deck names as its destination — was never actually rendered by 14-02/14-04, and adding it would require touching `airlines_page.py`, outside this plan's declared file scope
- Wrapped the load-time auto-open's `querySelector` call in try/catch and positioned the whole block after the click listener registration, so a malformed `?resolve=` value can never prevent the rest of the script (including every other click on the page) from working

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `companion/test_companion_app.py`'s hardcoded `setAttribute("action"` count assertion broke**
- **Found during:** Task 1, immediately after adding the resolve-upload and delete forms' own `setAttribute("action", ...)` writes
- **Issue:** A pre-existing quick-task-260903-btu check (`_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard`) asserted `src.count('setAttribute("action"') == 1`, true only while the replace form was the sole such write. This task's own two new writes (the resolve-upload zone's nested `<form>`, and the delete form) legitimately raise that count to 3.
- **Fix:** Widened the assertion in place to `== 3`, with an explanatory comment naming all three writes and this plan by number — the same retarget-in-place pattern 14-02's own SUMMARY documents for an identical class of collision.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `server/.venv/bin/python3 companion/test_companion_app.py` — 159/159
- **Committed in:** `57f89e1` (Task 1 commit)
- **Note on plan-scope deviation:** the plan's own `files_modified` frontmatter and `<verification>` section's `git diff --name-only` claim name only `companion/static/panel-lookup.js` and `companion/test_view_pages.py`; this fix required touching `companion/test_companion_app.py` as well. Keeping the full test suite green took priority over the narrower stated file scope — a one-file scope expansion, purely to an existing test assertion, no production code outside `panel-lookup.js` touched.

**2. [Rule 2 - Missing critical functionality] The resolve-name form's hidden prefix input and the resolve-context block's five `<dd>` hooks were never populated by the plan's own literal task text**
- **Found during:** Task 1, while cross-referencing 14-UI-SPEC.md's Component Inventory table against the plan's enumerated six element lookups
- **Issue:** 14-UI-SPEC.md states, for `_resolve_name_form_html()`: "JS fills the hidden prefix input's `.value` at click time," and for `_resolve_context_html()`: "each `<dd>` additionally carries one of five new classes ... so the dialog's copy has stable JS hooks (plan 14-05)" — both statements name this plan as the consumer. 14-02 built the hidden `<input name="prefix">` and the five `resolve-context__*` classes specifically for this purpose, but the plan's own Task 1 action text lists only six lookups (`resolveNameForm`, `resolveUploadZone`, `deleteForm`, `heading`, `manualNote`, `resolveContext`) and never mentions these two. Left unaddressed, the dialog's own Step A "Save airline name" submit would always post an empty `prefix` (the hidden input's server-rendered value is `""` for the dialog's own call), and the sighting-context block would render five permanently empty values regardless of which card was clicked — undermining D-01's "the dialog states that scope... at the moment of acting."
- **Fix:** Added `resolvePrefixInput` (looked up via `resolveNameForm.querySelector('input[name="prefix"]')`) and five `resolve-context__*` lookups, all populated inside `openFromTrigger()` from `data-view-panel-resolve-prefix`/`-first-seen`/`-last-seen`/`-count`/`-caption`, in the same optional-lookup style as everything else in the file.
- **Files modified:** `companion/static/panel-lookup.js`
- **Verification:** `server/.venv/bin/python3 companion/test_view_pages.py` — 63/63; manual confirmation deferred to 14-08 (no headless browser in this project's toolchain)
- **Committed in:** `57f89e1` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 — a direct, foreseeable consequence of this task's own new `setAttribute` writes; 1 Rule 2 — a genuine functionality gap in the plan's own literal task text, contradicted by the approved UI-SPEC's explicit statement naming this plan as the consumer)
**Impact on plan:** Zero behavioral scope creep beyond what UI-SPEC itself specifies for this plan. Both fixes make already-intended, already-approved behavior actually work; no new feature surface was invented.

## Known Limitations

- `data-view-panel-scope`'s value is read on every open (satisfying the correctness rule's "read every one of these" half) but has no DOM element to write into — `.lightbox__resolve-scope`, the element 14-UI-SPEC.md's Copy Deck names as its destination, was never rendered by 14-02/14-04's actual implementation of `_resolve_name_form_html()`. Fixing this requires a change to `companion/pages/airlines_page.py`, outside this plan's declared file scope (`panel-lookup.js` and `test_view_pages.py` only). Not tracked as a stub in the "flows to UI" sense — nothing renders a blank placeholder in its place, the scope sentence simply never appears in the dialog copy. A future plan adding `.lightbox__resolve-scope` needs only one more `if (element) { element.textContent = scope; }` line in `openFromTrigger()`.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `panel-lookup.js` is now feature-complete per 14-UI-SPEC.md's Interaction Contract; this plan is the phase's only touch of this file, and no other plan in the phase modifies it
- Every manual-only browser verification 14-08 requires (imageless open confirmed via Network panel, per-trigger form visibility, in-dialog delete, keyboard focus, load-time auto-open) is now exercisable against a real running service — none of it was verifiable by this stdlib-only harness, exactly as RESEARCH.md's Validation Architecture predicted
- `companion/static/panel-lookup.js` and `companion/test_view_pages.py` remain this wave's own claim; `companion/test_companion_app.py`'s one retargeted assertion is a narrow, test-only change with no production-code implication for 14-06/14-07 (same wave) or 14-08 (next wave)
- No file under `server/` was modified, no new dependency was added, no build step introduced — the phase's stdlib-only-server boundary, no-new-dependency constraint, and ES5-safe-subset constraint all hold

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/static/panel-lookup.js
- FOUND: companion/test_view_pages.py
- FOUND: companion/test_companion_app.py
- FOUND commit: 57f89e1
- FOUND commit: e8ff3af
