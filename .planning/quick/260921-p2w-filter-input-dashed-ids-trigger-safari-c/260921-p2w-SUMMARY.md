---
phase: quick-260921-p2w
plan: 01
subsystem: ui
tags: [companion, safari, webkit, autofill, ast, static-analysis, testing]

requires:
  - phase: quick-260921-n2n
    provides: "autocomplete=off/spellcheck=false/autocapitalize=characters on all three filter inputs (Lot A Task 1/4)"
provides:
  - "Three filter-input ids (history_filter_input, airlines_gallery_filter_input, airlines_filter_input) with the hyphen removed — the documented WebKit/Safari contacts-autofill trigger"
  - "A standing ast-based invariant in test_status_pages.py that no *_FILTER_INPUT_ID constant value and no hardcoded <input type=\"search\"> id literal, anywhere in companion/pages/*.py or companion/app.py, contains a hyphen"
affects: [companion-filter-bars, safari-compat]

tech-stack:
  added: []
  patterns:
    - "Source-level ast scans (never import/render) for id-shaped invariants, matching test_i18n.py's own methodology"
    - "Vacuity floors (>= N) on any ast-based 'absence of X' check, so deleting the guarded construct cannot make the check pass trivially"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/pages/health_page.py
    - companion/test_status_pages.py

key-decisions:
  - "Renamed hyphenated ids to their underscore form rather than any other shape — the documented Safari trigger is specifically the hyphen character in a name-less input's id, and underscores are valid in both HTML5 id values and CSS/fragment identifiers"
  - "Health's _FILTER_INPUT_ID keeps its airlines- (now airlines_) prefix — it is Health's own unresolved-prefix registry filter, and renaming its scope was explicitly out of this task's business"
  - "Did not edit the archived 06.6.4.1-UI-SPEC.md; reworded the test's own check name/message instead to cite this quick task as the current authority, with a pointer to the now-superseded spec row"
  - "New check reads constant VALUES via ast, never raw file text, so Task 1's own provenance comments (which legitimately name the old hyphenated values) remain legal"
  - "No attempt was made at a Chrome fix — no mechanism connects a single code change to the reported password-save prompt (field is type=\"search\", not inside a <form>, no type=\"password\" field on any of these pages)"

requirements-completed: [QUICK-260921-p2w]

coverage:
  - id: D1
    description: "All three filter-input ids (history, Compagnies gallery, Health prefix registry) are hyphen-free, distinct, and semantically unchanged; Lot A's three autofill-suppression attributes remain intact and un-duplicated"
    requirement: QUICK-260921-p2w
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py — full suite (311/311)"
        status: pass
      - kind: unit
        ref: "Task 1 inline verify script — hyphen-free/distinct/attribute-intact assertions"
        status: pass
    human_judgment: true
    rationale: "The documented WebKit trigger (hyphen in a name-less input's id) is removed and machine-verified, but whether the Safari contacts-autofill dropdown itself stops appearing can only be confirmed by a live re-test on real Safari hardware — no playwright/browser automation is available in this sandbox."
  - id: D2
    description: "Standing ast-based invariant check added to test_status_pages.py enforcing hyphen-free filter-input ids across companion/pages/*.py + app.py, with a >=3 vacuity floor, mutation-proven three ways"
    requirement: QUICK-260921-p2w
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py — _no_filter_input_id_anywhere_in_the_app_contains_a_hyphen (311/311)"
        status: pass
      - kind: other
        ref: "Mutation proof 1 (Part A): hyphen reintroduced in health_page.py, harness run, failure message quoted below, reverted via git checkout-index -f"
        status: pass
      - kind: other
        ref: "Mutation proof 2 (floor): scratch fixture at scratchpad/floor-proof with zero *_FILTER_INPUT_ID constants, failure message quoted below"
        status: pass
      - kind: other
        ref: "Mutation proof 3 (Part B): scratch fixture at scratchpad/partb-proof with a hardcoded hyphenated <input type=\"search\"> id, failure message quoted below"
        status: pass
    human_judgment: false

duration: ~7min (commit-span; wall-clock including verification longer)
completed: 2026-09-21
status: complete
---

# Quick Task 260921-p2w: Remove the hyphen from all three filter-input ids Summary

**Renamed history-filter-input / airlines-gallery-filter-input / airlines-filter-input to their underscore forms (the documented WebKit/Safari trigger for the contacts-autofill dropdown), and added an ast-based standing invariant in test_status_pages.py so no filter-input id can go hyphenated again.**

## Performance

- **Duration:** ~7 min (commit timestamps 18:13:48 → 18:20:35 CEST)
- **Tasks:** 2/2 completed
- **Files modified:** 4 (`companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/pages/health_page.py`, `companion/test_status_pages.py`)

## Accomplishments

- All three `_FILTER_INPUT_ID` values are now hyphen-free: `history_filter_input`, `airlines_gallery_filter_input`, `airlines_filter_input` — distinct, semantically unchanged, Health's `airlines` scope prefix preserved
- `test_status_pages.py:10916`'s hardcoded old literal retargeted to `"airlines_gallery_filter_input"`; the check's "UI-SPEC-pinned" claim reworded to cite this quick task, pointing at the now-superseded `06.6.4.1-UI-SPEC.md` §7.2 row (that archived file itself was NOT edited)
- One new standing check (`_no_filter_input_id_anywhere_in_the_app_contains_a_hyphen`) makes "no filter-input id contains a hyphen" a machine-enforced, ast-derived property of the whole app — Part A scans every `*_FILTER_INPUT_ID` constant value, Part B forward-guards against a future filter bar that inlines a hardcoded id instead of using a constant
- Mutation-proven three ways (see below), each with the real failure message quoted and each mutation reverted cleanly

## Task Commits

1. **Task 1: remove the hyphen from all three filter-input ids, and retarget the one test literal** - `c8adf39` (fix)
2. **Task 2: make "no filter-input id contains a hyphen" a standing, machine-enforced invariant** - `96fb2c9` (fix)

_No docs/plan-metadata commit — the orchestrator owns `.planning/STATE.md` and the docs commit per this task's constraints._

## Files Created/Modified

- `companion/pages/history_page.py` - `_FILTER_INPUT_ID` renamed `"history-filter-input"` → `"history_filter_input"`, with the full provenance comment explaining the WebKit/Safari mechanism
- `companion/pages/airlines_page.py` - `_FILTER_INPUT_ID` renamed `"airlines-gallery-filter-input"` → `"airlines_gallery_filter_input"`, short comment pointing back to history_page.py's explanation
- `companion/pages/health_page.py` - `_FILTER_INPUT_ID` renamed `"airlines-filter-input"` → `"airlines_filter_input"`; stale "byte-identical to airlines_page.py" comment reworded to state the true, current scope
- `companion/test_status_pages.py` - retargeted the one hardcoded old literal at (former) line 10916, reworded that check's claim/name; added Task 2's new `_no_filter_input_id_anywhere_in_the_app_contains_a_hyphen` check immediately after Lot A's sibling scan; bumped `EXPECTED_CHECK_COUNT` 310 → 311

## Decisions Made

- Underscore form chosen as the minimal faithful fix — the cited WebKit/Safari sources locate the defect in the hyphen character specifically, not in underscores, and underscores are valid in both HTML5 `id` values and CSS/fragment identifiers
- Health's constant keeps its `airlines` prefix (now `airlines_filter_input`) — it is Health's own unresolved-prefix registry filter; renaming its semantic scope was explicitly excluded by the plan
- The archived `06.6.4.1-UI-SPEC.md` was left untouched (historical record); the test's own check name/message was reworded instead to carry the current authority
- The new invariant check reads constant VALUES through `ast`, never raw file text, so Task 1's provenance comments (which legitimately name the old hyphenated values) remain legal
- No Chrome fix was attempted — no mechanism connects a single code change to the reported password-save prompt

## Deviations from Plan

None - plan executed exactly as written, including the mutation-proof scratch-file route the plan explicitly permitted for the floor (mutation 2) and Part B (mutation 3), since directly mutating the `%`-tuple-fed `id="%s"` template in a real page module would have broken that module's `render()` for every other check in the same harness run rather than isolating the new check's own failure mode.

## Mutation Proofs (verbatim)

**1. Part A — real regression in `companion/pages/health_page.py`** (hyphen put back into `_FILTER_INPUT_ID`, harness run, then `git checkout-index -f -- companion/pages/health_page.py`):

```
FAIL no *_FILTER_INPUT_ID constant value and no hardcoded <input type="search"> id literal, across companion/pages/*.py and companion/app.py (enumerated from disk, 3 constants found at plan time, a >= 3 vacuity floor so deleting the constants cannot make this pass trivially), contains a hyphen — the documented WebKit/Safari trigger that offers the user's own Contacts phone numbers on a name-less type="search" field even with autocomplete="off" set (quick task 260921-p2w Task 2, closing the gap Task 1's three hand-fixed values left open) - WebKit/Safari renders a contacts icon inside a text input and offers phone numbers from the user's OWN Contacts card when the field's name — or, absent a name, its id — contains a hyphen, and Safari ignores autocomplete="off" in that case, which is why quick task 260921-n2n's attribute fix alone left the dropdown showing on the deployed app (the developer's 2026-09-21 report) — a hyphenated *_FILTER_INPUT_ID constant reintroduces exactly that defect: pages/health_page.py: _FILTER_INPUT_ID = 'airlines-filter-input'
```

**2. The `>= 3` vacuity floor** (proven via a scratch fixture under the scratchpad directory — zero `*_FILTER_INPUT_ID` constants anywhere on the simulated "app", no repository file touched):

```
FAIL expected at least 3 *_FILTER_INPUT_ID constant assignments across companion/pages/*.py and companion/app.py (the floor known at plan time — airlines_page.py, health_page.py, history_page.py), found only 0 — this would let the check pass vacuously if every filter constant were deleted
```

**3. Part B — the inlined-id forward guard** (proven via a scratch fixture under the scratchpad directory simulating a future filter bar with a hardcoded hyphenated id instead of the `%s` template form — no repository file touched, since mutating a real page module's `id="%s"` in place would have broken that module's `render()` for every OTHER check in the same harness run):

```
FAIL a hardcoded (non-template) id= on a rendered <input type="search"> tag reintroduces exactly that defect, bypassing the *_FILTER_INPUT_ID constant scan entirely: pages/future_filter_page.py: '<input type="search" id="future-filter-input" autocomplete="off" spellcheck="false" autocapitalize="characters" data-filter-input>' has hardcoded id 'future-filter-input'
```

## Issues Encountered

None.

## Verification Run

- `companion/test_status_pages.py` → **311/311** (310 after Task 1, +1 after Task 2, both re-derived by running)
- `companion/test_view_pages.py` → **166/166** (unchanged)
- `companion/test_config_page.py` → **266/266** (unchanged)
- `companion/test_i18n.py` → **24/24** (unchanged)
- `scripts/run-all-tests.sh` (full 21-harness suite) → **all PASS**, 0 failures to classify; `companion/test_browser_ux.py` printed `SKIP companion/test_browser_ux.py — playwright not installed` and exited 0
- `git diff --name-only 77f9aaa..HEAD -- . ':!.planning'` → exactly `companion/pages/airlines_page.py`, `companion/pages/health_page.py`, `companion/pages/history_page.py`, `companion/test_status_pages.py` — no stylesheet, no script, no translation catalogue, no `app.py`, no other id
- `git log --oneline 77f9aaa..HEAD` → exactly two `fix(quick-260921-p2w): ...` commits, one per task, each ending `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
- No unexpected file deletions in either commit

## Human / Live-Browser Follow-Ups

**1. Safari re-test — the only real confirmation of this task.** This task removes the documented trigger (a hyphen in a name-less `type="search"` input's `id`) and machine-proves it cannot silently come back. It does **not** prove the Safari symptom itself is gone. On the iPhone/iPad where the contacts dropdown was photographed: hard-reload the deployed Flights page (Safari caches aggressively — pull-to-refresh, or close and reopen the tab), tap the filter field, and report whether the contacts icon and phone-number list ("09 51 90 38 96 – domicile" / "06 15 82 72 84 – iPhone") still appear. Repeat on Compagnies, and on Health's unresolved-prefix filter if it is showing. Expect: no contacts icon, no phone numbers, keyboard still opens shifted, typing still filters the list identically. **If the dropdown still appears after this deploy, the hyphen was not the (only) trigger** — the next step is a Safari Web Inspector session on the live field, not another blind attribute or id change.

**2. The Chrome "save password" prompt is still OPEN — no fix was attempted here, deliberately.** No mechanism could be identified: the filter field is `type="search"`, it is not inside any `<form>`, and no `type="password"` field exists on any of these pages, while Chromium documents that its password-manager heuristic deliberately ignores `autocomplete="off"`. Before any further code change, a clearer repro is needed: **which page exactly**, and **what action immediately preceded the prompt** — typing in the filter alone, or a save/login/upload submission elsewhere on the page around the same moment (the Display page's save, or the Compagnies illustration upload, are the plausible confounders). Without that, any "fix" here would be a guess.

## Next Phase Readiness

No blockers. The rename is complete and machine-guarded; the only open item is the developer's live Safari re-test (item 1 above) and, separately, a clearer Chrome repro (item 2 above) before any further code change is justified.

---
*Quick task: 260921-p2w*
*Completed: 2026-09-21*

## Self-Check: PASSED

All 4 modified files and the SUMMARY.md itself found on disk; both task commits (`c8adf39`, `96fb2c9`) found in git log.
