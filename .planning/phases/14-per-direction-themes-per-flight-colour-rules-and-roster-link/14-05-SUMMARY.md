---
phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link
plan: 05
subsystem: ui
tags: [companion, http-server, forms, colour-rules, settings-page, no-js]

# Dependency graph
requires:
  - phase: 14-01
    provides: "server/plane/colour_rules.py — the registry (add_rule/delete_rule/rule_rows/load_colour_rules), COLOUR_RULE_MAX_ENTRIES, and the ADD_* result vocabulary this plan's routes map onto flash keys"
  - phase: 14-04
    provides: "companion/pages/config_page.py and companion/static/style.css as extended for the arrivals-theme checkbox/second chip grid, which this plan re-enters and extends further"
provides:
  - "The per-flight colour-rules editor on Settings: an add form (kind/value/theme) and a cards-then-table list with a plain per-row Delete button, rendered between the settings </form> and the Poll section"
  - "Two authenticated immediate POST routes, /settings/rules/add and /settings/rules/{kind}/{value}/delete, outside the settings form's dirty-bar tracking"
  - "Seven rule-editor flash messages (added/replaced/key-invalid/registry-full/save-failed/deleted/delete-failed) with role assignment and D-09's replaced-vs-added legibility"
  - "ctx['colour_rules'], read fresh per request via colour_rules.load_colour_rules(state_dir), documented in companion/pages/__init__.py"
affects: [phase-14-secure-phase, phase-14-close-out]

tech-stack:
  added: []
  patterns:
    - "Rules section rendered immediately after </form> closes (not nested inside <form id=settings-form>) since the add form and each delete row are real <form> elements — Poll moves one slot later, every other group's DOM nesting stays byte-identical"
    - "The rules add/delete routes reuse the existing require_session() + SameSite=Strict CSRF posture rather than inventing a new mechanism"
    - "Delete-route path segments are re-normalised through colour_rules.normalise_rule_kind()/normalise_rule_value() before any registry lookup — an unrecognised kind or malformed value 404s, never a lookup against a request string"
    - "The replaced flash's echoed {key} is re-validated through colour_rules.normalise_rule_callsign() (the broadest of the three per-kind allowlists) before interpolation, falling back to the generic added copy on failure"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/app.py
    - companion/pages/__init__.py
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "Confirmed 14-UI-SPEC.md's Open Question 1 recommended option: the rules <section> takes the slot Poll used to occupy, immediately after </form> closes, rather than restructuring every settings group to submit via a form= attribute"
  - "The rule=<value> query parameter's kind is not carried in the redirect (only the already-normalised value is), so the replaced flash's echo validation uses the callsign normaliser's charset ([A-Z0-9]{2,8}) as a superset check covering all three kinds, rather than threading the kind through the URL too"
  - "Deleting an already-absent (kind, value) redirects with no flash at all, matching the manual-resolutions delete precedent, rather than reusing the 'deleted' flash for a no-op"

requirements-completed: []

coverage:
  - id: D1
    description: "Rules section renders on Settings between the form and Poll, with an add form, empty state, and cards-then-table list carrying a plain per-row Delete button"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_rules_section_renders_between_form_and_poll_section"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_rules_section_empty_state_then_list_once_a_rule_exists"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_rules_list_cards_precede_table_in_dom_order"
        status: pass
    human_judgment: false
  - id: D2
    description: "Add and delete are immediate authenticated POSTs on their own routes, outside the settings form and its dirty bar"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_add_and_delete_forms_sit_outside_settings_form"
        status: pass
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_routes_require_auth_and_write_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "Adding a key that already exists reports 'replaced' rather than 'added', echoing the key back"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_add_route_no_js_added_then_replaced"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every request-supplied kind, value and theme id is validated before use, at write, on delete lookup, and before any echo into a flash message"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_add_route_rejection_paths"
        status: pass
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_delete_route_full_contract"
        status: pass
    human_judgment: false
  - id: D5
    description: "The rules registry reaches Settings fresh per request, never through the poll-cycle cache"
    verification:
      - kind: integration
        ref: "companion/test_companion_app.py#_rules_page_context_reads_fresh_per_request"
        status: pass
    human_judgment: false
  - id: D6
    description: "No-JS browser confirmation of the rules editor and the arrivals reveal (real browser, JavaScript disabled) — end-of-phase manual verification per human_verify_mode: end-of-phase"
    verification: []
    human_judgment: true
    rationale: "Requires a real browser with scripting disabled to confirm CSS reveal, focus order and screen-reader announcement — the automated HTTP-level checks above cover the raw POST semantics but not real-browser rendering/interaction, and this project has a standing lesson that computed-style checks alone missed a real mobile nav bug"

duration: ~55min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 05: Per-Flight Colour Rules Editor Summary

**Per-flight colour-rules editor on Settings (add form + cards-then-table list) backed by two immediate authenticated POST routes, with D-09's replace-on-add legibility and T-14-01's re-validate-on-every-boundary discipline.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-06T16:11:21Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Rendered the per-flight colour-rules editor on the Settings page: an add form (kind/value/theme selects), an empty state, and a cards-then-table list with a plain per-row Delete button — inserted immediately after the settings `</form>` closes (Poll moved one slot later) since the add form and every delete row are real `<form>` elements that cannot nest inside another `<form>`.
- Added `POST /settings/rules/add` and `POST /settings/rules/{kind}/{value}/delete`, both authenticated immediate actions outside the settings form's dirty-bar tracking, with seven flash messages (added/replaced/key-invalid/registry-full/save-failed/deleted/delete-failed) matching 14-UI-SPEC.md's Copywriting Contract byte for byte.
- Threaded `colour_rules.load_colour_rules(state_dir)` into `page_context()` as `ctx["colour_rules"]`, read fresh on every request (never the poll-cycle's process-scoped cache), and documented the new ctx key in `companion/pages/__init__.py`.
- Extended both companion harnesses with 8 new checks in `test_config_page.py` (101 → 109) and 6 new checks in `test_companion_app.py` (159 → 165); full suite is 18/18 harnesses green at 93% coverage (`config_page.py` alone rose from 91% to 99%).

## Task Commits

1. **Task 1: Render the rules section on Settings — add form, list, delete rows, and its CSS (D-10, D-11)** - `2581200` (feat)
2. **Task 2: Add the two immediate POST routes, their flash vocabulary and the ctx key (D-10)** - `7ea3c3f` (feat)
3. **Task 3: Extend both companion harnesses with the rules-editor checks (14-VALIDATION.md rows 10 and 11)** - `9f14b97` (test)

## Files Created/Modified

- `companion/pages/config_page.py` - Route/copy/flash-key constants, the add-form renderer, the row/table/card-list renderers, the section assembler, and `render()`'s new placement of the rules section between the form and Poll.
- `companion/static/style.css` - `.rule-add-form`/`.rule-add-form__field` (column-stack layout, `--space-md` gap, zero new tokens/colours/accent reservations).
- `companion/app.py` - The seven `FLASH_KEY_RULE_*` aliases plus their `FLASH_MESSAGES`/`FLASH_ROLES` entries; `_resolve_flash_text()`'s second interpolated key (`rule_replaced`'s `{key}`, re-normalised via `colour_rules.normalise_rule_callsign()` before interpolation); `Handler._handle_rule_add_post()`/`_handle_rule_delete()` and their `do_POST()` dispatch branches; `page_context()`'s new `colour_rules` key and `rule=` query read.
- `companion/pages/__init__.py` - Documented the new `colour_rules` ctx key.
- `companion/test_config_page.py` - 8 new checks covering the rules section's placement, empty-state/list transition, DOM order, copy, shared kind-label mapping, computed swatch, no-dirty-section, and the locked heading pin.
- `companion/test_companion_app.py` - 6 new checks covering auth-gating, the form-isolation contract, the no-JS added-then-replaced round trip, rejection paths, the delete route's full contract, and fresh-per-request reads.

## Decisions Made

- Confirmed 14-UI-SPEC.md's Open Question 1 recommended option (Rules section takes Poll's old slot, immediately after `</form>` closes) rather than the alternative of threading `form=` attributes through every existing settings group.
- Since the `rule=` redirect query parameter carries only the already-normalised value (not its kind), the replaced-flash echo is validated through `colour_rules.normalise_rule_callsign()` — the broadest of the three per-kind allowlists (`[A-Z0-9]{2,8}`, a strict superset of the hex and prefix charsets) — rather than threading the kind through the URL as well. This still guarantees only safe uppercase-alphanumeric text can ever reach the interpolated flash string (T-14-14).
- Deleting an already-absent `(kind, value)` redirects with no flash at all, mirroring the manual-resolutions delete route's own idempotent-no-flash precedent, rather than reusing the "deleted" flash for a no-op.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Widened a pre-existing "no runtime interpolation in flash copy" guard**
- **Found during:** Task 2 (adding the seven rule flash messages)
- **Issue:** `test_companion_app.py` already carried a check asserting no `FLASH_MESSAGES` value contains `{`/`%` except the pre-existing `FLASH_KEY_POLL_COOLDOWN` — the new `rule_replaced` template (`"Updated the rule for {key} — ..."`) is deliberately templated per D-09, so this check would false-fail against the plan's own required behavior.
- **Fix:** Widened the check's exemption tuple to also cover `FLASH_KEY_RULE_REPLACED`, updating the check's own docstring/name to state the widening explicitly rather than silently loosening the assertion.
- **Files modified:** companion/test_companion_app.py
- **Verification:** `companion/test_companion_app.py` 159/159 (pre-widen baseline, after Task 2's other changes) → confirmed the fix restores green; later folded into Task 3's own count update.
- **Committed in:** `7ea3c3f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary to keep an existing regression guard both correct and green after adding the one deliberately-templated flash message D-09 requires. No scope creep.

## Issues Encountered

- An early draft of the "fresh-per-request" harness check used a 10-character callsign fixture (`FRESHREAD1`), which the callsign normaliser's own `{2,8}` length bound rejects — caught immediately by the check itself (`add_rule()` returned `rejected_key`), fixed by shortening the fixture to 8 characters (`FRESHRD1`) before the check was finalized. No production code was affected; this was a test-fixture-only mistake caught before commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- This is the phase's closing plan. All three of this plan's tasks are committed, and the full `scripts/run-all-tests.sh` suite passes 18/18 harnesses at 93% coverage with zero `server/` changes (D-07's render.py/test_render.py standing gate holds; the D-01/D-02/D-03 scope-fence grep over this plan's own diff finds no roster/iCal/crew content).
- **Open item, deliberately deferred to end-of-phase per `human_verify_mode: end-of-phase`:** the no-JS real-browser confirmation (14-VALIDATION.md's Manual-Only Verifications: arrivals-grid reveal/hide, unsaved-changes-bar non-interference, rule add/replace/delete via native form submission, and keyboard tab order through the Theme card into the revealed grid). The plan's own `<verification>` section also names the phase close-out step `/gsd-secure-phase 14` over the two new rules routes and the registry — both are phase-level closing actions, not plan-level ones, and are recorded here as the phase's one remaining obligation before it can close.
- No on-glass verification is in scope for this plan (D-07): every rule and override resolves to an already-registered theme id, so nothing new reaches the physical panel.

---
*Phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/pages/config_page.py
- FOUND: companion/static/style.css
- FOUND: companion/app.py
- FOUND: companion/pages/__init__.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND commit: 2581200
- FOUND commit: 7ea3c3f
- FOUND commit: 9f14b97
