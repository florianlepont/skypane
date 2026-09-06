---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 04
subsystem: ui
tags: [python, stdlib-only, html, datalist, security, xss-escaping]

requires:
  - phase: 13-01
    provides: "server/plane/manual_resolutions.py's full public surface (load_manual_resolutions()/illustration_key_for_name()/entry_rows()/add_entry()/delete_entry(), the T-13-02 write-time allowlist)"
  - phase: 13-03
    provides: "server/plane/enrich.py's static_airline_name_for_prefix() — the D-06 supersession oracle this plan's management list reads"
provides:
  - "companion/pages/airlines_page.py's whole operator-facing resolve surface: unresolved_row_for_prefix() (public, D-11's single membership test), _resolve_section_html() (four server-derived states), _known_airlines_datalist_html() (D-13's native suggestion mechanism)"
  - "companion/pages/airlines_page.py's manual-resolutions management list: _manual_resolutions_section_html() and its table/card pair, always rendered, flagging D-06 supersession in words with a one-click D-08 delete"
  - "companion/static/style.css's .resolve-context/.resolve-name-field/.resolve-upload-zone (extends the existing .lightbox__replace-zone treatment) and .manual-resolution__status--superseded (a seventh label-voice consumer, by value)"
affects: [13-06]

tech-stack:
  added: []
  patterns:
    - "unresolved_row_for_prefix() mirrors _serve_illustration_image()'s validate-then-join shape over a closed, server-written set, applied here to the unresolved-prefix registry instead of the illustration-filename set"
    - "Cards-before-table DOM order for the management list, matching health_page._registry_section()'s own documented .data-cards ~ .data-table-wrap sibling-combinator toggle dependency"
    - "Selector-group extension (add a class as a second selector, change no declaration) reused a second time in this phase: .resolve-upload-zone joins .lightbox__replace-zone's six rules verbatim"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "The 'already resolved' fourth state (RESOLVE_ALREADY_DONE_TEMPLATE, a planner addition not in the UI-SPEC deck) reuses STEP_B_HEADING_TEMPLATE for its heading rather than inventing a fifth heading constant, since the Artifacts table enumerates no such constant and the plan's own action text describes this branch as a variant of the Step B presentation"
  - "The upload zone's 'Choose an image' label text is inlined rather than promoted to a module constant, since it interpolates nothing and the plan's own Artifacts table does not list it as an owned constant"
  - "Real U+2019 apostrophes and U+2014 em dashes used throughout phase-13 copy per the plan's explicit instruction, even though 13-UI-SPEC.md's own Full Copy Deck source text uses plain ASCII apostrophes — the codebase's own established convention (71+ existing em dashes, zero existing apostrophes of either kind in copy constants) supports em dashes; U+2019 is the plan's own explicit typographic call"

requirements-completed: []

coverage:
  - id: D1
    description: "The resolve section renders exactly one of four server-derived states from /airlines?resolve={prefix}, with the sighting context read fresh from the registry (never from the query string) and gated by a single shared D-11 membership test"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_resolve_section_four_states_render_correctly"
        status: pass
    human_judgment: false
  - id: D2
    description: "The name field is backed by a native <datalist> offering all 27 airlines that already have artwork, each option escaped exactly once"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_resolve_section_datalist_contract"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every interpolated hostile value (stored airline name, example callsign) renders fully escaped everywhere it appears, including inside attributes; a resolve_prefix differing in case/padding from the stored registry key never matches (D-12)"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_resolve_section_escapes_hostile_values_and_distrusts_query_string"
        status: pass
    human_judgment: false
  - id: D4
    description: "The manual-resolutions management list is always rendered with its own empty state, and with entries covers the same prefixes in the same order across both the desktop table and the mobile card list"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_manual_section_empty_and_populated_states"
        status: pass
    human_judgment: false
  - id: D5
    description: "An entry whose prefix the static table has since learned renders the Superseded marker with its title explanation and exactly one trailing caption; an entry that has not is unmarked, and the caption is absent when nothing is superseded (D-06)"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_manual_section_supersession_contract"
        status: pass
    human_judgment: false
  - id: D6
    description: "Each row's delete control is a real submit button inside its own form posting to /airlines/manual-resolutions/{prefix}/delete, the list emits no filter-bar/filter-group markup of its own, and the new CSS selector's label-voice values are pinned identical to .data-card__label's"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_manual_section_delete_control_and_design_system_contract"
        status: pass
    human_judgment: false
  - id: D7
    description: "The page still ships zero JavaScript — no <script> element, no inline event-handler attribute — across both new sections"
    verification:
      - kind: unit
        ref: "grep -c '<script' companion/pages/airlines_page.py (0); grep -c ' onclick=| onchange=| onsubmit=' companion/pages/airlines_page.py (0)"
        status: pass
    human_judgment: false
  - id: D8
    description: "D-09 standing gate: server/plane/illustrations.py remains byte-for-byte unchanged and its 58-check harness still passes"
    verification:
      - kind: unit
        ref: "git diff --stat -- server/plane/illustrations.py (empty); server/test_illustrations.py (58/58)"
        status: pass
    human_judgment: false

duration: 31min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 04: Airlines resolve section + manual-resolutions management list Summary

**Airlines gains a four-state, server-derived "resolve an unidentified flight" surface with a native `<datalist>` over the 27 known airlines, plus an always-present manual-resolutions management list flagging D-06 supersession in words with a one-click delete — zero JavaScript, one escaping choke point, keys always recomputed server-side.**

## Performance

- **Duration:** ~31 min
- **Started:** 2026-09-06T01:36Z (context load, following 13-03's completion)
- **Completed:** 2026-09-06T02:10Z
- **Tasks:** 2/2
- **Files modified:** 3 (`companion/pages/airlines_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`)

## Accomplishments

- `unresolved_row_for_prefix(state_dir, prefix)` added as a **public** function — D-11's single membership test, validate-then-join over the live `unresolved_prefixes` registry, the same shape `illustrations._serve_illustration_image()` already uses against a closed set. `companion/app.py`'s POST handler (plan 13-06) will import and re-run this exact function rather than re-implementing the check.
- `_resolve_section_html(ctx)` renders exactly one of four server-derived states from `?resolve={prefix}`: stale (prefix not a live registry member), Step A (name form + native datalist), Step B (conditional upload, reusing the existing `/illustration/{key}.png` route unchanged), and already-resolved (a planner addition covering the fourth reachable state the UI-SPEC deck didn't enumerate). Every displayed value comes from the validated tuple, never the raw query string (D-12).
- `_known_airlines_datalist_html()` offers all 27 `illustrations.target_airline_names()` entries as native `<option>`s — D-13's whole mechanism, no script involved.
- `_manual_resolutions_section_html(ctx)` is always rendered (own `layout.empty_state()` when empty), pairing a desktop table with a mobile card list (cards first in DOM order, matching `health_page._registry_section()`'s own sibling-combinator toggle dependency — caught and fixed before it shipped, see Deviations). `_manual_resolution_rows()` flags D-06 supersession via `enrich.static_airline_name_for_prefix()`; each row's delete form posts to `/airlines/manual-resolutions/{prefix}/delete` with no confirmation dialog (D-08's recoverability).
- CSS: `.resolve-context`/`.resolve-name-field` (new, token-only rules), `.resolve-upload-zone` (added as a second selector to all six existing `.lightbox__replace-zone` rules, no declaration changed), and `.manual-resolution__status--superseded` (a seventh consumer of the shared 12px label voice, declared by value per `sketch-findings-skypane` SKILL.md's own rule).
- `companion/test_status_pages.py` grew from 140 to 146 checks (3 per task), covering the four-state state machine, the datalist contract, hostile-value escaping + D-12 query-string distrust, empty/populated management-list states, the supersession contract, and the delete-control/design-system contract (pinning the new CSS selector's five declared values against `.data-card__label`'s, so the two can never drift).
- D-09 standing gate held throughout: `server/plane/illustrations.py` untouched, `server/test_illustrations.py` still 58/58.

## Task Commits

Each task was committed atomically:

1. **Task 1: The resolve section — server-side prefix validation, sighting context, datalist name form, conditional upload step (D-03, D-11, D-12, D-13)** — `9d2f410` (feat)
2. **Task 2: The manual-resolutions management list — list, status, delete (D-06, D-07, D-08)** — `15296ac` (feat)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified

- `companion/pages/airlines_page.py` — the resolve section (Task 1) and the manual-resolutions management list (Task 2); module docstring updated to document phase 13's narrow, deliberate supersession of 06.6.4.1's own D-17 "reads no poll state" non-goal
- `companion/static/style.css` — four additions: `.resolve-context`, `.resolve-name-field`, `.resolve-upload-zone` (extends the shared `.lightbox__replace-zone` selector group), `.manual-resolution__status--superseded`
- `companion/test_status_pages.py` — 6 new checks (140 → 146); updated one pre-existing D-17 import guard to reflect the deliberate `poll_loop` import phase 13 adds

## Decisions Made

- The "already resolved" fourth state reuses `STEP_B_HEADING_TEMPLATE` for its heading rather than a new constant — the plan's own Artifacts table lists no fifth heading constant, and the action text frames this branch as a variant of the Step B presentation.
- The upload zone's "Choose an image" label text is inlined (not promoted to a module constant) since it interpolates nothing and isn't in the plan's owned-constants list.
- Real U+2019 apostrophes / U+2014 em dashes used throughout the new copy, per the plan's explicit instruction — even though `13-UI-SPEC.md`'s own source text for those same strings uses plain ASCII apostrophes. Verified against the codebase's actual convention (em dashes: 71+ existing uses; apostrophes: zero pre-existing copy-constant uses either way) before deciding U+2019 was the plan's own typographic call, not a fabricated one.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Management list's cards/table DOM order would have broken the mobile/desktop toggle**
- **Found during:** Task 2, while cross-referencing `health_page._registry_section()`'s own documented CSS dependency before wiring `_manual_resolutions_section_html()`.
- **Issue:** The plan's action text says "the table plus the card list" (table first). `companion/static/style.css`'s `.data-cards ~ .data-table-wrap { display: none; }` sibling-combinator rule (and its inverse at `>=960px`) only works when `.data-cards` precedes `.data-table-wrap` in the DOM — the exact same mechanism `health_page._registry_section()`'s own comment documents and depends on ("Cards render before the table ... do not reorder these two calls"). Emitting them in the plan's literal order would have rendered both the table and the card list simultaneously at every breakpoint.
- **Fix:** Emit `_manual_resolution_cards_html()` before `_manual_resolution_table_html()` in `_manual_resolutions_section_html()`'s return value, with a comment recording the dependency (mirroring `health_page.py`'s own comment verbatim in spirit).
- **Files modified:** `companion/pages/airlines_page.py`.
- **Verification:** `companion/test_status_pages.py#_manual_section_empty_and_populated_states` asserts the `.data-cards` list's start index precedes the `<table`'s start index.
- **Committed in:** `15296ac` (Task 2 commit).

**2. [Documented plan-spec inconsistency, no code change] Two acceptance-criteria greps are unsatisfiable against pre-existing, unrelated, correct code**
- **Found during:** Task 1 and Task 2 acceptance-criteria verification.
- **Issue (Task 1):** `grep -cE "^ *(from|import).*normalise_airline_key|illustrations\.normalise_airline_key" companion/pages/airlines_page.py` is specified to return `0`, but the pre-existing gallery function `_airline_card_html()` (shipped by an earlier phase, unrelated to this plan) already calls `illustrations.normalise_airline_key(airline_name)` to build each card's image key from the static curated target list — a legitimate, pre-existing, correct use with no operator-input threat surface. This plan's own new code (the resolve section) never calls this function directly, always going through `manual_resolutions.illustration_key_for_name()` as instructed.
- **Issue (Task 2):** `grep -c 'data-filter-group="' companion/pages/airlines_page.py` is specified to return `0`, but the pre-existing gallery card template (`_airline_card_html()`) already emits `data-filter-group="%d"` for its own, unrelated filter mechanism. This plan's new management-list code emits no `data-filter-group` attribute anywhere, as instructed (confirmed: the only occurrence of the literal `data-filter-group="` in the file is the pre-existing gallery line).
- **Resolution:** Followed the substantive intent of both criteria (the *new* code added by this plan) rather than the literal whole-file grep, since the literal grep counts pre-existing, correct, unrelated code this plan does not touch and should not touch. No code change was needed or made. Matches the precedent already recorded in `13-01-SUMMARY.md`'s own deviation #2 (a literal acceptance-criteria grep conflicting with legitimate pre-existing file content).
- **Files modified:** none.
- **Committed in:** n/a (documentation only).

---

**Total deviations:** 1 auto-fixed (Rule 1, a real cross-CSS-dependency bug caught before shipping), 1 documented plan-spec inconsistency (no code impact, two acceptance-criteria greps).
**Impact on plan:** The Rule 1 fix is necessary for correctness — without it the management list's mobile/desktop toggle would have been visibly broken (both representations shown at every viewport width). No scope creep beyond what the plan's own cross-references (to `health_page.py`'s documented CSS dependency) already implied.

## Issues Encountered

An unrelated, pre-existing intermittent flake was discovered in `companion/test_status_pages.py`'s Health-section check `"the battery readout carries its id, role=\"status\" ..."` (`quick task 260901-uzi finding 3, Check 4`): it occasionally fails with `expected one data-when attribute per chart hit target, got 2`. Confirmed **not caused by this plan**: reproduced identically with this plan's Task 2 changes stashed (only Task 1's already-committed changes present), and the affected code (`companion/pages/health_page.py`'s battery-trend chart) is untouched by this plan. Logged to `.planning/phases/13-add-an-illustration-for-an-unidentified-flight-from-the-comp/deferred-items.md` per the scope-boundary rule; not fixed here. Both tasks' own full test runs (`test_status_pages.py` at 143/143 after Task 1, 146/146 after Task 2, repeated several times) pass in the large majority of runs — this flake is intermittent, not deterministic, and unrelated to any file this plan modifies.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `unresolved_row_for_prefix()` is ready for plan 13-06's POST handler to import and re-run as its own D-11 membership check, exactly as scoped in "Artifacts this phase produces."
- `ctx["resolve_prefix"]`, `ctx["manual_resolutions"]`, and `ctx["now"]` are the three ctx keys plan 13-06 needs to thread from `companion/app.py`'s `page_context()`/POST handlers; every read in this plan already uses `ctx.get()`, so the page renders correctly the moment 13-06 starts supplying them and continues to degrade gracefully (empty resolve section, empty-state management list) until then.
- `FLASH_MANUAL_*` keys (8 total) are defined and ready for plan 13-06 to rebind under `FLASH_KEY_MANUAL_*` names with their `FLASH_MESSAGES`/`FLASH_ROLES` entries, mirroring the existing `FLASH_ILLUSTRATION_*` pattern.
- No blockers. `server/plane/illustrations.py` is untouched; the D-09 standing gate (58/58 `test_illustrations.py` checks, byte-identical file) holds and should continue to be checked by plan 13-06 (the phase's remaining plan).
- One unrelated, pre-existing intermittent test flake logged to `deferred-items.md` (see Issues Encountered) — not blocking, not caused by this plan.

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Plan: 04*
*Completed: 2026-09-06*

## Self-Check: PASSED

All modified files (`companion/pages/airlines_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`), the deferred-items.md artifact, and both task commit hashes (`9d2f410`, `15296ac`) verified present on disk / in git log.
