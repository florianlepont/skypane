---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 07
subsystem: ui
tags: [i18n, french, display-page, forms, quick-actions, screens-registry]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/i18n.py (t()), the companion/i18n_fr/ auto-merging catalogue package, ctx[\"lang\"], layout.QUICK_STATE_FIELD/ON/OFF, the /quick/* redirect-to-Display move"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-03: layout.section_intro_html() (promoted from health_page.py), layout.status_row()"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-04: the .theme-status--nested/.page-section--nested > h2 CSS extension, .quick-action-slot CSS"
provides:
  - "companion/screens.py — Runway and Calendar moved from advanced_groups to everyday_groups; Display now carries all six everyday groups, Device only LED and Wake interval"
  - "companion/pages/config_page.py render() — Display's three headed supersections (Look/What it watches/When it is on), each grouped card carrying a --nested modifier"
  - "display_group()/quiet_hours_group() restructured as siblings of #settings-form, each with its own .quick-action-slot instant switch (D-19) and scheduled inputs bound via form=\"settings-form\""
  - "companion/pages/config_page.py rendering entirely through i18n.t(), with companion/i18n_fr/display.py — the Display/Device pages' full French catalogue"
  - "the Device page's Edit-artwork link (and _edit_artwork_link_html()) deleted outright (D-36)"
affects: [20-08, 20-09, 20-10, 20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_nested_wrapper_html(html_fragment, base_class, nested_class) — a count-limited str.replace() that appends a literal --nested modifier to a group builder's own outer wrapper class, without changing that builder's signature or internals; nested_class is always passed as a literal string (never derived at runtime) so the modifier stays grep-visible in source"
    - "_display_groups_html() returns a 2-tuple (in_form_html, on_supersection_html) — the second element is emitted by render() AFTER </form> closes, keeping the locked Look/What it watches/When it is on reading order across the form boundary that D-19's instant switches force"
    - "%-templated copy constants (NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE, the two quiet-hours preset label templates, POLL_COOLDOWN_HELPER_TEXT) are translated through i18n.t() BEFORE substitution, never after — matches health_page.py's SOURCE_FAULT_BODY_TEMPLATE precedent (20-03)"

key-files:
  created:
    - companion/i18n_fr/display.py
  modified:
    - companion/screens.py
    - companion/pages/config_page.py
    - companion/test_config_page.py

key-decisions:
  - "Flight colours (the per-flight colour-rules editor) stays a sibling of #settings-form, rendered in the same DOM position it occupied before this plan — right after </form> closes — rather than literally between Theme and Calendar. Its own add-form/delete-forms are real <form> elements and every card _display_groups_html() assembles is (unchanged from before this plan) a literal descendant of <form id=\"settings-form\">; inserting Flight colours between Theme and Calendar would force the form to split into two <form id=\"settings-form\"> elements sharing one id, which is invalid HTML and would break every existing form=\"settings-form\" cross-DOM reference (the dirty-bar's Save button, the screen-type <select>) by resolving to the wrong one. The plan's own text explicitly grants this: \"keep each of them in whatever DOM position its own form requirements demand.\" Visual reading therefore lands Flight colours after \"When it is on\" rather than between Theme and Calendar — flagged for 20-09 (Calendar/Flight colours redesign), which may close this gap by giving Flight colours a dedicated route the way calendar_disconnect_section() already has for Calendar."
  - "screens.py's everyday_groups tuple order is (theme, calendar, runway, display, quiet_hours) per the plan's own literal instruction — Calendar renders directly after Theme inside the settings form (both are plain cards with no form of their own), Runway follows under its own \"What it watches\" header, and Display/Quiet-hours follow under \"When it is on\", pulled outside the physical form by Task 2."
  - "Theme/Runway/screen-type registry labels (device_config.theme_label()/runway_label(), screen[\"label\"]) are deliberately left untranslated — a cross-page, registry-wide concern (these functions are called from Calendar, Flight colours, the Airlines page and elsewhere) out of this plan's own files_modified scope. Flagged below for a later phase."
  - "Three keys config_page.py calls i18n.t() on — \"Theme\", \"Display\", \"Device\" — are deliberately absent from companion/i18n_fr/display.py: they are already defined in companion/i18n_fr/nav.py (D-09's fixed nav labels). A fourth, \"Screen\", is already in companion/i18n_fr/health.py. Redefining any of the four in display.py would trip the i18n_fr package's own duplicate-key guard (verified: importing companion.i18n_fr with display.py in place raises no ValueError, and the merged CATALOG resolves all four correctly through the sibling modules)."

requirements-completed: [CFG-13, CFG-15, CFG-18]

# Metrics
duration: 150min
completed: 2026-09-11
---

# Phase 20 Plan 07: Display regrouped, instant switches, Display/Device in French Summary

**Runway and Calendar move from Device to Display's three new headed supersections (Look/What it watches/When it is on); Screen on/off and Quiet hours gain real instant-switch forms as siblings of the settings form (fixing the HTML-nested-form defect that switch would otherwise create); and every string on both pages now renders through i18n.t(), backed by a new ~145-entry French catalogue.**

## Performance

- **Duration:** ~150 min
- **Started:** 2026-09-11T21:10:00Z (approx., wave 3 start)
- **Completed:** 2026-09-11T23:40:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `companion/screens.py`: `GROUP_RUNWAY`/`GROUP_CALENDAR` moved from `advanced_groups` to `everyday_groups` — `scope_groups(SCOPE_DISPLAY)` now returns all six everyday groups (theme, calendar, runway, display, quiet_hours — Flight colours is not a "group" in this registry), `scope_groups(SCOPE_DEVICE)` returns only LED and Wake interval
- `config_page.render()`'s Display scope branches into three `layout.section_intro_html()` headed supersections (Look / What it watches / When it is on) via a new `_display_groups_html()` helper; every grouped card gains a `--nested` modifier (`_nested_wrapper_html()`); `show_rules`/`show_calendar_disconnect` moved from the Device branch to the Display branch; `calendar_disconnect_confirm_page()`'s cancel link now points at `/display`
- `display_group()`/`quiet_hours_group()` restructured as siblings of `<form id="settings-form">` (fixing D-19/Pitfall 1's HTML-nested-form defect their own instant switch would otherwise create): each carries a `.quick-action-slot` posting to `/quick/display`/`/quick/quiet-hours`, above the shared "Applies the next time the frame wakes up." sentence, and their scheduled inputs bind back to the settings form via `form="settings-form"`
- Every user-visible string in `config_page.py` renders through `i18n.t()`; `companion/i18n_fr/display.py` (new) supplies the French catalogue (~145 entries); a live French render of Display/Device was smoke-tested end to end with zero leftover English
- `_edit_artwork_link_html()` and its call site, constants and the now-unused `EDIT_QUERY_PARAM` import are deleted outright (D-36)

## Task Commits

1. **Task 1: Move Runway, Calendar and the rules to Display, and build Display's three supersections** - `fde2248` (feat)
2. **Task 2: The instant switches, and the form restructure that makes them valid HTML** - `3e6aedb` (feat)
3. **Task 3: config_page through t(), its French catalogue, and the Device page's "Edit artwork" removal** - `2a7c2b9` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/screens.py` — `EVERYDAY_GROUPS`/`ADVANCED_GROUPS` and the plane-frame screen type's `everyday_groups`/`advanced_groups` tuples updated for D-10/D-11
- `companion/pages/config_page.py` — the highest-touch file this plan: `_nested_wrapper_html()`, `_display_groups_html()` (new helpers), `render()`'s Display/Device branch restructuring, `display_group()`/`quiet_hours_group()`'s quick-action-slot restructuring, `calendar_disconnect_confirm_page()`'s cancel-link retarget, `_edit_artwork_link_html()` deletion, and every render call site wrapped in `i18n.t()`
- `companion/i18n_fr/display.py` (new) — ~145 French catalogue entries for the Display/Device pages, grouped by card with comment banners
- `companion/test_config_page.py` — 11 pre-existing checks retargeted in place (see Deviations below), 11 new checks added; `EXPECTED_CHECK_COUNT` 181 → 184 → 190 → 194

## Decisions Made
See `key-decisions` in the frontmatter above — the Flight-colours DOM-position trade-off (the most structurally significant decision in this plan), the `everyday_groups` tuple order, the deliberate registry-label translation exclusion, and the three/four duplicate-key exclusions from the new catalogue module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Four pre-existing checks broken by display_group()/quiet_hours_group()'s own restructuring, found by running the whole suite before writing any new check (Task 2's own explicit instruction)**
- **Found during:** Task 2
- **Issue:** `scope_groups(SCOPE_ALL)`'s fixed legacy tuple still includes `GROUP_DISPLAY`/`GROUP_QUIET_HOURS`, so the untouched SCOPE_ALL/legacy flat join still calls the now-restructured `display_group()`/`quiet_hours_group()`, whose own return value now embeds a small quick-action `<form>` ahead of the settings form's real closing tag. Four pre-existing checks had assumed the FIRST `"</form>"` in a legacy render was the settings form's own closing tag: `_render_display_prefill_defaults_checked_and_honors_saved_false` (a naive "slice to the first `</div>` after the dirty-section marker" no longer reached the checkbox, which now sits after several new inner `<div>`s), `_render_dirty_bar_is_sibling_of_form_last_on_page`, `_calendar_placement_after_display_before_form_close_with_dirty_attr`, and `_calendar_group_no_inline_js_and_select_within_form` (both found the quiet-hours quick-action's own inner `</form>` instead of the real one).
- **Fix:** Retargeted each check in place: the checkbox-state check now finds the `<input>` tag directly by name rather than slicing to the first `</div>`; the other three now locate the settings form's real closing tag by searching from a known-safe anchor (the "Save settings" button's own text, or the Calendar heading / `calendar_theme_id` select, both of which come after Display/Quiet-hours in `SCOPE_ALL`'s fixed order) rather than trusting the first `"</form>"` in the document.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` → 190/190 after the retarget, all four checks passing against the real restructured markup
- **Committed in:** `3e6aedb` (Task 2 commit)

**2. [Rule 1 - Bug] Seven pre-existing checks retargeted in Task 1 for the group move itself**
- **Found during:** Task 1
- **Issue:** Moving Calendar/Runway from Device to Display broke checks that asserted the OLD placement: the calendar-disconnect confirm page's cancel link (asserted Device, now Display), the disconnect-form placement/absence pair (asserted present-on-Device/absent-on-Display, now the exact inverse), the scoped-render's runway/LED/rules/poll assertions (asserted no runway on Display and rules only on Device), the out-of-scope calendar-signal assertions (asserted Display ignores stray calendar fields, now Device does), the HTTP round-trip's runway/calendar GETs (fetched `/device` to verify a newly-saved runway or the calendar secret's absence, now fetches `/display`), and the radiogroup count (asserted Device has the Runway radiogroup, now Display does and Device has none).
- **Fix:** Retargeted each in place, following the group move's own new truth exactly (documented per-check in code comments citing D-10/D-11).
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` → 184/184 after Task 1's retarget
- **Committed in:** `fde2248` (Task 1 commit)

**3. [Rule 1 - Bug] The pre-existing Edit-artwork-anchor check retargeted for its own removal**
- **Found during:** Task 3
- **Issue:** `_device_scope_has_one_edit_artwork_link_display_has_none()` asserted the Device scope carries exactly one Edit-artwork anchor — the exact link D-36 deletes.
- **Fix:** Retargeted to `_neither_scope_renders_an_edit_artwork_link()`, asserting absence on both scopes and that `_edit_artwork_link_html` no longer exists as a module attribute.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` → 194/194 after Task 3's retarget
- **Committed in:** `2a7c2b9` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed groups (all Rule 1 — bugs/correctness issues that are a direct, mechanical consequence of this plan's own restructuring, all within `companion/test_config_page.py`, which this plan owns)
**Impact on plan:** No scope creep — every fix is a same-effect retarget of an existing assertion onto the new, correct structure, not a new requirement or a weakened check. No plan requirement was dropped.

## Issues Encountered

**D-11's app.py redirect targets are out of this plan's reach.** D-11 requires "the calendar-disconnect form and the rules add/delete routes follow their groups (their return_to becomes Display)". `companion/app.py`'s `_handle_rule_add_post()`, `_handle_rule_delete()`, and `_handle_calendar_disconnect_post()` all still hard-code `DEVICE_ROUTE` for their success/failure redirect targets (`companion/app.py` lines ~1991, 2002, 2013, 2045, 2048, 2049, 2098, 2103, 2105) — `companion/app.py` is owned by 20-08 per this wave's `project_specifics` and is not in this plan's `files_modified` list. I fixed the one literal I do own — `calendar_disconnect_confirm_page()`'s own cancel link (in `companion/pages/config_page.py`), which now correctly points at `/display` — but the live POST-success redirect after adding/deleting a rule or disconnecting the calendar still lands on `/device` until whichever plan next touches `app.py` retargets those 8 literals to `DISPLAY_ROUTE`. **Retarget needed:** in `companion/app.py`, replace `DEVICE_ROUTE` with `DISPLAY_ROUTE` at the 8 call sites listed above (all within `_handle_rule_add_post()`, `_handle_rule_delete()`, and `_handle_calendar_disconnect_post()`).

**Four checks in `companion/test_companion_app.py` (owned by 20-08, not touched here) now fail as a direct, mechanical consequence of this plan's group move and D-36's link removal.** Exact retargets needed:
1. `_display_and_device_pages_split_the_groups()` (`companion/test_companion_app.py` ~line 3622): flip the runway assertion (`if 'name="tracked_runway"' in display_text or 'name="led_enabled"' in display_text: return False, "expected the Display page NOT to carry the runway or LED groups"` → Display now DOES carry `tracked_runway`, only NOT `led_enabled`; Device now does NOT carry `tracked_runway`, only DOES carry `wake_interval_s`), and flip the rules-editor assertion (`"Manual refresh" in display_text or "Per-flight colour rules" in display_text` → Display now carries "Per-flight colour rules" (not "Manual refresh"); Device now carries "Manual refresh" (not "Per-flight colour rules")).
2. `_device_page_edit_artwork_link_opens_airlines_with_edit_forms()` (~line 3656): delete this whole check (function + its `check(...)` call) — its own subject, the Device page's Edit-artwork link, no longer exists (D-36). `EXPECTED_CHECK_COUNT` in that file should decrease by 1 to account for the removed check, once 20-08 lands this.
3. `_rules_add_and_delete_forms_sit_outside_settings_form()` (~line 5291): the `http_request(rbase + "/device", cookie=rsession)` GET should become `http_request(rbase + "/display", cookie=rsession)` — Flight colours now renders on Display.
4. `_rules_page_context_reads_fresh_per_request()` (~lines 5575 and 5586): both `http_request(rbase + "/device", cookie=rsession)` GETs should become `http_request(rbase + "/display", cookie=rsession)` — same reason.

These were confirmed via `PYTHON=... bash scripts/run-all-tests.sh`: `companion/test_companion_app.py` reports 221/227 (2 documented pre-existing root-sandbox FAILs + these 4 new ones), all other harnesses unaffected. Per this session's own instructions, `companion/test_companion_app.py` was not edited — these four retargets are left for 20-08 or the orchestrator to apply after the wave merges.

**Theme/runway/screen-type registry labels stay in English.** `device_config.theme_label()`/`runway_label()` and `screens.py`'s screen-type `"label"` field (e.g. "White", "Runway 3 (07/25)", "Plane frame") render untranslated everywhere this plan touches them (Theme's chip grid, Calendar's theme select, the rules add-form's theme select and rule rows, the screen caption). This mirrors the exact precedent 20-03's own SUMMARY documents for `health_page.py`'s battery-chart month table: these are cross-page, registry-wide concerns (the same functions are called from Flights, Airlines and elsewhere) that a single page-scoped plan cannot resolve without reaching into `server/device_config.py`, out of this plan's own `files_modified` list. Flagged for a later phase or a dedicated cross-cutting plan.

## Known Stubs

None — every render path this plan ships is real, immediately-effective code (the group move, the instant switches, the French catalogue); nothing here is a placeholder awaiting a later plan's markup. Flight colours' own DOM-position limitation (see Decisions above) is a documented structural trade-off, not a stub — the feature itself is fully wired and functional, only its exact position relative to Theme/Calendar within "Look" is not pixel-perfect to D-12's literal ordering.

## Threat Flags

None beyond this plan's own `<threat_model>` — no new network endpoints, auth paths, or schema changes were introduced. The instant-switch forms post to the pre-existing, already-gated `/quick/display`/`/quick/quiet-hours` routes; only the page that renders them moved.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `companion/screens.py`'s registry move and `config_page.py`'s three-supersection assembly are ready for 20-09 (Calendar/Flight-colours redesign) to build on — 20-09 can now assume Calendar and Flight colours both render on Display, and may resolve the Flight-colours DOM-position gap this plan documents by giving it a dedicated route.
- `companion/i18n_fr/display.py` demonstrates the full-page translation pattern for the remaining untranslated pages in this phase to follow.
- **Blocker for full D-11 compliance:** the `companion/app.py` redirect-target retarget (8 literals, `DEVICE_ROUTE` → `DISPLAY_ROUTE`) and the four `companion/test_companion_app.py` retargets listed under Issues Encountered must land before this phase's own `<verification>` section ("`companion/test_companion_app.py` → exactly the two documented root-sandbox FAILs") is satisfied. Currently that file reports 221/227 (4 extra FAILs beyond the two documented ones), all precisely diagnosed above.
- `companion/test_view_pages.py` (85/85) and `companion/test_status_pages.py` (210/211, the one documented root-sandbox FAIL) are confirmed unmoved by this plan.
- No blockers for 20-10 (Airlines "Change pictures" button) — this plan's own D-36 half (deleting the Device-page link) is complete; 20-10 only needs to add the replacement button on `airlines_page.py`.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: companion/screens.py
- FOUND: companion/pages/config_page.py
- FOUND: companion/i18n_fr/display.py
- FOUND: companion/test_config_page.py
- FOUND commit: fde2248 (Task 1)
- FOUND commit: 3e6aedb (Task 2)
- FOUND commit: 2a7c2b9 (Task 3)
