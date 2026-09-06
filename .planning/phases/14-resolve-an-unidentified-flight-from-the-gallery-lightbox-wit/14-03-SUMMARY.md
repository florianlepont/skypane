---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 03
subsystem: ui
tags: [javascript, css, stdlib-only, static-assets, no-build-step]

# Dependency graph
requires:
  - phase: "14-01"
    provides: "the classified lightbox token vocabulary and the coverage checks this plan's new selectors/attributes stay outside of (this plan touches no data-view-panel-* attribute)"
provides:
  - "companion/static/list-filter.js: an optional, guarded [data-filter-set] querySelectorAll lookup whose click handler sets the filter input's value from the clicked element's own attribute and calls the file's one existing applyFilter() — D-11's clickable manual-resolution summary line now has a real mechanism to drive"
  - "companion/static/style.css: a.airline-card, .airline-card__placeholder, .lightbox__heading:empty, .lightbox__manual-note:empty, .manual-summary (+ :hover), and .lightbox__replace's selector extended to a three-way group with .lightbox__resolve-name/.lightbox__delete"
  - "companion/test_status_pages.py: two new source-assertion checks (151, 152) pinning both files' new contracts"
affects: [14-04, 14-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "list-filter.js's [data-filter-clear]-mirroring shape (querySelector[All] an optional attribute, attach a listener that mutates input.value and calls the one applyFilter()) is now used twice, establishing it as this file's own extension idiom for any future optional filter-driving control"
    - "style.css's 'extend a selector list, never duplicate the declaration block' convention (.lightbox__replace-zone, .resolve-upload-zone) applied a second time to .lightbox__replace, .lightbox__resolve-name, .lightbox__delete"

key-files:
  created: []
  modified:
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/test_status_pages.py
    - companion/test_view_pages.py

key-decisions:
  - "The [data-filter-set] click handler uses a closure-capturing IIFE per matched element (for (var si...) { (function(setBtn){...})(setButtons[si]); }) rather than a shared named handler reading a data attribute off evt.currentTarget — both are ES5-safe, this shape mirrors the file's existing per-element closure pattern most directly and needed no new lookup idiom"
  - "Wrote test_status_pages.py's [data-filter-text] single-query assertion against the bracketed-selector form ([data-filter-text], count 1) rather than a bare substring count (data-filter-text, count 2 — one query plus one unrelated getAttribute read inside applyFilter) — the plan's own acceptance-criteria grep literal counts the bare substring and would return 2 both before and after this plan's change (pre-existing, unrelated to Task 1); the bracketed form is what the task's <action>/<behavior> text actually specifies as 'the single-filtering-implementation property'"

patterns-established:
  - "A new unscoped CSS class (.manual-summary) declared with a property list byte-identical to an existing scoped one (.filter-bar [data-filter-clear]) when the new element sits outside the scoping ancestor but needs the identical visual treatment — avoids either duplicating the scoped selector's ancestor or loosening it"

requirements-completed: []

coverage:
  - id: D1
    description: "list-filter.js gains an optional [data-filter-set] lookup mirroring [data-filter-clear]'s shape; clicking a matched element sets the filter input's value and calls the file's one applyFilter(); the file stays ES5-safe with exactly one [data-filter-text] query and no network call/timer; a page without the attribute (History) is unaffected"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — 151/151 then 152/152 (new check: companion/static/list-filter.js gains an optional, guarded [data-filter-set] lookup...)"
        status: pass
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_view_pages.py — 55/55 (History's shared-script behaviour proven unchanged)"
        status: pass
    human_judgment: false
  - id: D2
    description: "style.css declares exactly the five new/extended selectors UI-SPEC's Component Inventory enumerates (a.airline-card, .airline-card__placeholder, .lightbox__heading:empty, .lightbox__manual-note:empty, .manual-summary + :hover), .airline-card__placeholder's aspect-ratio string-equals .airline-card__image's, .lightbox__replace is extended to a three-way group in one declaration block, zero new accent uses, zero new custom properties, and .manual-resolution__status--superseded survives for plan 14-06"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 companion/test_status_pages.py — 152/152 (new check: style.css declares exactly the five new/extended selectors...)"
        status: pass
      - kind: unit
        ref: "git diff companion/static/style.css | grep '^+' | grep -c 'var(--color-accent)' -> 0; grep -c -E '^\\+\\s+--[a-z-]+:' -> 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/run-all-tests.sh exits 0 with all 17 harnesses green at 93% coverage; git diff --name-only touches only static assets and test harnesses, zero files under server/, zero Python page modules"
    verification:
      - kind: unit
        ref: "scripts/run-all-tests.sh — Result: PASS"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 03: list-filter.js Hook + New CSS Selectors Summary

**Added the missing `[data-filter-set]` programmatic-filter hook to `list-filter.js` (D-11's mechanism) and every new/extended CSS selector UI-SPEC's Component Inventory names — no dependency on the Python rendering work, so plans 14-04/14-06 render into styling and script hooks that already exist.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-09-06T15:20:44+02:00 (approx., prior plan's completion commit)
- **Completed:** 2026-09-06T15:41:57+02:00
- **Tasks:** 2 completed
- **Files modified:** 4 (`companion/static/list-filter.js`, `companion/static/style.css`, `companion/test_status_pages.py`, `companion/test_view_pages.py`)

## Accomplishments
- `list-filter.js` gained one optional, guarded `querySelectorAll("[data-filter-set]")` lookup mirroring `[data-filter-clear]`'s existing shape; each matched element's click sets the filter input's value from its own `data-filter-set` attribute and calls the file's one existing `applyFilter()` — no second filtering implementation, ES5-safe, no network call/timer, degrades to a no-op on any page without the attribute (History)
- `style.css` gained `a.airline-card` (D-12's `<a>`-based gap card needs the block layout + link reset a `<div>` got for free), `.airline-card__placeholder` (D-02's reserved-box gap slot — dashed border, `var(--color-canvas)` fill one level down inside the card's own `var(--color-dominant)` surface, `aspect-ratio` string-identical to `.airline-card__image`'s), `.lightbox__heading:empty`/`.lightbox__manual-note:empty` (copy `.lightbox__note:empty`'s idiom exactly), and `.manual-summary` + `:hover` (D-11's clickable summary line, declared with `.filter-bar [data-filter-clear]`'s identical property list)
- `.lightbox__replace`'s selector was extended to a three-way group (`.lightbox__replace, .lightbox__resolve-name, .lightbox__delete`) in one declaration block, matching this file's own `.lightbox__replace-zone, .resolve-upload-zone` precedent rather than duplicating the rule
- Zero new colour tokens, zero new accent consumers, `.manual-resolution__status--superseded` deliberately left in place for plan 14-06 to retire
- Two new source-assertion checks added to `test_status_pages.py` (`EXPECTED_CHECK_COUNT` 150 → 151 → 152)

## Task Commits

Each task was committed atomically:

1. **Task 1: `list-filter.js` gains a programmatic `[data-filter-set]` hook (D-11's mechanism)** - `077b174` (feat)
2. **Task 2: Every new CSS selector UI-SPEC enumerates, and no more** - `00f588e` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

## Files Created/Modified
- `companion/static/list-filter.js` - new `[data-filter-set]` lookup + click handler, header comment extended to document the new attribute and its degrade-on-absence behaviour
- `companion/static/style.css` - five new/extended selectors from UI-SPEC's exhaustive Component Inventory list, placed beside their own analogs
- `companion/test_status_pages.py` - two new source-assertion checks, `EXPECTED_CHECK_COUNT` 150 → 152
- `companion/test_view_pages.py` - one existing check's regex retargeted in place (see Deviations)

## Decisions Made
- Used a per-element closure (IIFE) for the `[data-filter-set]` click handlers, since `querySelectorAll` can match more than one element (unlike the single `clearBtn`) and each needs its own captured attribute value
- Wrote the `[data-filter-text]` single-query assertion against the bracketed-selector form (`"[data-filter-text]"`, expected count 1) rather than a bare substring count — the plan's own literal acceptance-criteria grep (`grep -c 'data-filter-text'`, no brackets) returns 2 both before and after this plan's change, since `applyFilter()`'s existing `row.getAttribute("data-filter-text")` read is a second, pre-existing, unrelated substring occurrence, not a second query. The bracketed form is what the task's own `<action>`/`<behavior>` text specifies as "the single-filtering-implementation property," and is what actually changes (or doesn't) if a second filtering path were ever introduced.
- `.manual-summary` is declared as a new, unscoped class (not nested under `.filter-bar`) since the summary line sits below the filter bar in the page composition (UI-SPEC Autonomous Decision 4), reusing `.filter-bar [data-filter-clear]`'s property list byte-for-byte rather than loosening that scoped selector

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `.lightbox__replace`'s selector extension broke an existing `test_view_pages.py` exact-selector regression check**
- **Found during:** Task 2, after extending `.lightbox__replace {` to the three-way group `.lightbox__replace,\n.lightbox__resolve-name,\n.lightbox__delete {`
- **Issue:** `test_view_pages.py`'s `_replace_lightbox_names_appear_in_three_files_never_in_history()` built `exact_selector = "." + airlines_page.LIGHTBOX_REPLACE_FORM_CLASS + " {"` (i.e. the literal `.lightbox__replace {`) and asserted membership in `style.css`'s source, to distinguish the real rule from the `.lightbox__replace-zone` prefix-collision quick task 260903-df3 already guarded against. Once `.lightbox__replace`'s own selector line ends in `,` (head of the new three-way group) rather than always ` {`, that literal no longer appears anywhere in the file — the check failed (54/55) both standalone and under `scripts/run-all-tests.sh`.
- **Fix:** Retargeted the assertion in place: replaced the hardcoded `" {"` suffix with a compiled regex (`r'\.' + re.escape(LIGHTBOX_REPLACE_FORM_CLASS) + r'(?=[\s,{])'`) using a lookahead for whitespace, comma or brace immediately after the class name — still excludes the `-zone` hyphen continuation (the original check's whole purpose), now also accepts the selector's new grouped form. No new check added; same property (a real, distinct `.lightbox__replace` rule exists, not merely a `-zone` substring match) verified the same way.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `server/.venv/bin/python3 companion/test_view_pages.py` — 55/55; `scripts/run-all-tests.sh` — Result: PASS
- **Committed in:** `00f588e` (Task 2 commit)
- **Note on plan-scope deviation:** the plan's own `<verification>` section's literal `git diff --name-only` claim names only `companion/static/list-filter.js`, `companion/static/style.css` and `companion/test_status_pages.py`; this fix required touching `companion/test_view_pages.py` as well — a one-file scope expansion, purely to an existing test assertion's regex, following 14-02's own precedent for this exact situation (a widened/reshaped selector breaking a substring-based test written before the reshape existed). No file under `server/` was touched and no Python page module was touched, so the phase's own stdlib-only-server and no-page-module-drift boundaries both hold.

---

**Total deviations:** 1 auto-fixed (Rule 1 — one existing test assertion's regex retargeted in place, a direct, anticipated-in-substance consequence of Task 2's own selector-list extension)
**Impact on plan:** Zero behavioral scope creep. The retargeted assertion verifies the identical property it always did (a real `.lightbox__replace` rule exists in `style.css`, distinct from the `-zone` prefix collision) — it is simply no longer confused by the selector's new three-way grouped shape, which Task 2 legitimately introduces per UI-SPEC's own binding instruction.

## Issues Encountered
None beyond the one auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `list-filter.js`'s `[data-filter-set]` hook is ready for plan 14-06's `<button type="button" class="manual-summary" data-filter-set="manual">` markup to drive without any further script change
- Every new CSS selector plan 14-04 and 14-06's markup depends on (`a.airline-card`, `.airline-card__placeholder`, `.lightbox__heading:empty`, `.lightbox__manual-note:empty`, `.manual-summary`, the extended `.lightbox__replace` group) already exists, so those plans render into real styling rather than shipping unstyled markup for a wave
- `.resolve-context`, `.resolve-name-field`, `.resolve-upload-zone`/`.lightbox__replace-zone`, `.airline-card__chip` and `.airline-card__zoom` were deliberately left untouched (UI-SPEC's own "zero CSS change" list) — no scope drift
- `.manual-resolution__status--superseded` is left in place for plan 14-06 to retire alongside the management table's rendering functions
- No file under `server/` was modified, no new dependency was added — the phase's stdlib-only-server boundary and no-new-dependency constraint both hold

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/static/list-filter.js
- FOUND: companion/static/style.css
- FOUND: companion/test_status_pages.py
- FOUND: companion/test_view_pages.py
- FOUND commit: 077b174
- FOUND commit: 00f588e
