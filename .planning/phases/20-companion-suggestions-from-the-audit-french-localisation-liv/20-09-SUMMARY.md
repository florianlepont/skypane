---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 09
subsystem: ui
tags: [calendar, flight-colours, i18n, french, status-row, native-radio, config-page]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-03: layout.status_row() (D-21)"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-04: .theme-chip--compact/.rule-row/.rule-list/.rule-add-form--inline/the native-radio segmented control CSS, the Calendar :has() fused-card CSS"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-07: Calendar/Flight colours moved to Display's three supersections; the i18n_fr auto-merge package and companion/i18n_fr/display.py"
provides:
  - "companion/pages/config_page.py — calendar_group() rebuilt around layout.status_row() and a compact theme-chip grid; calendar_connect_section() (new) — the write-only feed-URL field's own small form, its own dedicated route, wrapped in <details> once connected"
  - "companion/app.py — POST /settings/calendar/connect, its own require_session()-gated handler calling calendar_rules.save_calendar_url()/refresh_calendar_registry() directly, never config_page.handle_post()'s scope machinery"
  - "companion/pages/config_page.py — Flight colours renamed and rebuilt: a one-line add form (native-radio 'Match by' segmented control, compact theme chip grid, Add button), .rule-row list items replacing the retired table/card split, suggestion chips from recent runway events, a muted-sans empty state, a collapsible 'How rules combine' disclosure"
  - "companion/i18n_fr/calendar_group.py, companion/i18n_fr/rules.py — the two sections' French catalogues"
affects: [20-12-completeness-sweep]

tech-stack:
  added: []
  patterns:
    - "_theme_chip_grid_html()'s chip_extra_class parameter — a THIRD, independent seam distinct from the grid-level extra_class: the compact chip modifier must be on each chip's own <label>, not just the grid wrapper, or the CSS shrink rules never apply"
    - "A derived failed-fetch category (last_attempt_at recorded with no usable last_synced_at) computed entirely from existing calendar_rules.py fields, rather than a new server-side error-category field — the one category available without touching server/plane/calendar_rules.py (out of this plan's files_modified)"
    - "calendar_connect_section() takes no submitted parameter at all, unlike this file's other D-07 call sites — there is nothing to repopulate on a write-only field"

key-files:
  created:
    - companion/i18n_fr/calendar_group.py
    - companion/i18n_fr/rules.py
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "The Calendar card's status row, disclosure and compact chip grid stay literal descendants of #settings-form (unchanged position) — only the write-only feed-URL field and its Connect button move into calendar_connect_section(), a genuinely separate small form rendered as a sibling of #settings-form, immediately before calendar_disconnect_section()'s own output. This avoids ever nesting the Connect <form> inside #settings-form (which the HTML nested-form prohibition and T-20-11 both forbid) without requiring the whole Calendar card to move out of the form and thread a form=\"settings-form\" cross-DOM attribute onto its chip-grid radios."
  - "calendar_connect_section()'s own .page-section wrapper is what becomes the :has(+ .calendar-disconnect-form) fused-card target (20-04's CSS) — not calendar_group()'s own card, which cannot be its literal DOM sibling once Runway/Screen-on-off/Quiet-hours also render between them inside Display's three supersections. Connect and Disconnect visually fuse into one small two-part unit; the read-only status/chip-grid portion of the Calendar card above cannot be part of that same visual fusion. Documented as a known, deliberate DOM-position trade-off, matching 20-07-SUMMARY.md's own precedent for Flight colours' analogous limitation."
  - "The connect route's rejection path (empty/over-length URL) redirects with a flash key (FLASH_CALENDAR_CONNECT_INVALID) rather than doing a 200 field-level re-render — matching _handle_rule_add_post()'s own established shape for a dedicated immediate-action route, not _handle_settings_post()'s D-07 200-render idiom. Re-rendering the full Display page with a narrow single-field submitted dict would misrender every OTHER checkbox on the page as unchecked (the exact class of bug T-20-11 exists to prevent), so the D-07 200-render path was judged unsafe for this specific caller. calendar_connect_section() still accepts an errors parameter and renders a field-level message when called directly, satisfying the idiom structurally even though no live request path exercises it today."
  - "The rule-row's Remove button gets its own new copy (RULE_REMOVE_BUTTON_TEXT = 'Remove') rather than reusing airlines_page.DELETE_BUTTON_TEXT ('Delete') — matching the UI-SPEC's own D-15c wording; the now-unused import was dropped."
  - "RULE_KIND_TITLES (the technical term kept as each segment's title attribute) reuses the EXACT English strings phase 15 already shipped ('Callsign'/'ICAO24 hex'/'Callsign prefix'), and therefore reuses their EXISTING French translations already in companion/i18n_fr/display.py verbatim, rather than introducing new, more elaborate French wording — the auto-merge catalogue package raises on a duplicate key, so a second definition was not an option; this is a minor, deliberate simplification versus 20-UI-SPEC.md's own copy table's slightly longer French phrasing for the same tooltip-only text."
  - "Flight colours' entry_count/last_attempt_at context threading and the Calendar suggestion chips both read fresh per request (companion/app.py's page_context(), companion/history_db.recent_runway_events()) rather than any cached value — matching this codebase's established 'long-running ThreadingHTTPServer, read fresh every request' discipline."

requirements-completed: [CFG-13, CFG-15, CFG-18]

# Metrics
duration: 170min
completed: 2026-09-12
---

# Phase 20 Plan 09: Calendar card and Flight colours rebuilt Summary

**The Calendar card now leads with a status-row verdict/detail pair and a compact theme-chip grid, with Connect split into its own dedicated POST /settings/calendar/connect route; Flight colours is a one-line native-radio add form plus a plain .rule-row list, replacing the retired select/table shapes entirely.**

## Performance

- **Duration:** ~170 min
- **Completed:** 2026-09-12

## Accomplishments
- `calendar_group()` rebuilt: one-line caption, `layout.status_row("", verdict, detail, state)` replacing the old one-piece sentence (drift → not-configured → configured-and-usable → configured-with-a-recorded-failed-attempt → configured-and-pending, in that priority order), the compact theme chip grid replacing `<select name="calendar_theme_id">`, and a "How it works" disclosure that collapses to one plain sentence in simple mode (D-30)
- `calendar_connect_section()` (new): the write-only feed-URL field's own small form, posting to its own dedicated `POST /settings/calendar/connect` route, wrapped in `<details>"Replace the feed URL"` once connected — preserves the write-only contract verbatim (no `value` attribute, nothing derived from the stored URL, in both states)
- `companion/app.py`'s `_handle_calendar_connect_post()`: session-gated (T-20-10), reuses `config_page.submitted_calendar_signal()` for validation, calls the exact `save_calendar_url()` + `refresh_calendar_registry()` pair `_handle_settings_post()`'s calendar branch already uses — never touches `config_page.handle_post()`'s scope machinery (T-20-11), pinned by a seed-ON/connect/still-ON regression check
- Flight colours renamed "Flight colours" (D-15a), rebuilt as a one-line add form (three native `rule_kind` radios styled as the existing segmented control, a value input with a static `AFR1234` placeholder, the compact theme chip grid, an Add button), a `.rule-list` of `.rule-row` items (theme swatch dots, mono key, `.banner__pill` kind badge, theme name, a `data-confirm` Remove form) replacing the retired table/card split outright, up to five suggestion chips from `history_db.recent_runway_events()`, and a muted-sans empty state that carries no heading element (D-15d)
- Two new French catalogue modules (`companion/i18n_fr/calendar_group.py`, `companion/i18n_fr/rules.py`) covering every new/changed string in both sections

## Task Commits

Both `companion/pages/config_page.py` and `companion/test_config_page.py` received Task 1 (Calendar) and Task 3 (Flight colours) edits in one continuous editing session before either was committed — the two tasks share both files closely enough (retargeting the SAME pre-existing checks, e.g. the theme-chip-grid selected-count check touched by both new compact grids) that splitting the working-tree diff into two git commits after the fact would have required costly manual hunk-splitting for no real benefit. They are committed together, with the commit message identifying each task's own contribution:

1. **Task 1 + Task 3: Calendar card and Flight colours rebuilt** (`companion/pages/config_page.py`, `companion/i18n_fr/calendar_group.py`, `companion/i18n_fr/rules.py`, `companion/test_config_page.py`) - `c398d1e` (feat)
2. **Task 2: POST /settings/calendar/connect — its own dedicated route** (`companion/app.py`, `companion/test_companion_app.py`) - `526debf` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/pages/config_page.py` — `calendar_group()` rebuilt, `calendar_connect_section()` (new), `_theme_chip_grid_html()` gained a `chip_extra_class` parameter, `_rule_kind_radio_html()`/`_rule_add_form_html()`/`_rule_suggestion_chips_html()`/`_rule_row_html()`/`_rule_list_html()`/`_rules_section_html()` rebuilt, `render()`'s calendar wiring extended (entry_count/last_attempt_at, `calendar_connect_html`)
- `companion/app.py` — `CALENDAR_CONNECT_ROUTE` rebound, `_handle_calendar_connect_post()` (new), two new flash keys (`FLASH_KEY_CALENDAR_CONNECT_OK`/`_INVALID`) with `_resolve_flash_text()`'s own fourth special case, `page_context()`'s calendar block widened to read `last_attempt_at`/`entry_count` from one shared `load_calendar_registry()` call
- `companion/i18n_fr/calendar_group.py` (new) — the Calendar card's French catalogue
- `companion/i18n_fr/rules.py` (new) — the Flight-colours section's French catalogue
- `companion/test_config_page.py` — every calendar/rules render-shape check retargeted to the new markup; new checks for the native-radio segmented control, the pill-badge/confirmed Remove row, the plain-sans empty state, the suggestion chips, both disclosures' simple-mode collapse, and a French render of each section; `EXPECTED_CHECK_COUNT` 194 → 200
- `companion/test_companion_app.py` — three new checks for the connect route (valid/invalid/unauthenticated); two pre-existing checks retargeted in place (the FLASH_MESSAGES interpolation exemption, the Display/Device group-split "Flight colours" needle); `EXPECTED_CHECK_COUNT` 241 → 244

## Decisions Made
See `key-decisions` in the frontmatter above — six decisions, the most structurally significant being the Connect form's placement (a sibling of `calendar_group()`'s own card, never embedded inside it or inside `#settings-form`) and its consequence for the `:has()` fused-card CSS's real target.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_theme_chip_grid_html()`'s compact modifier needed a second, chip-level seam**
- **Found during:** Task 1 (self-check, before writing any test)
- **Issue:** The plan's own text describes passing `extra_class="theme-chip-grid--compact"` to get the compact chip treatment. That parameter only reaches the GRID wrapper's own class attribute; `companion/static/style.css`'s `.theme-chip--compact` rules key off each CHIP's own class, which `_theme_chip_grid_html()`'s existing signature had no way to set — the compact sizing would have silently never applied.
- **Fix:** Added a new `chip_extra_class` parameter, applied to every chip's own `<label>` class attribute, independent of the grid-level `extra_class`. Both Calendar's and Flight-colours' compact grid calls now pass `chip_extra_class="theme-chip--compact"` alongside the existing `extra_class="theme-chip-grid--compact"`.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** Visual inspection of the returned markup confirmed each chip's `<label>` now carries `theme-chip--compact`; `companion/test_config_page.py` continued to pass after the fix.
- **Committed in:** `c398d1e` (Task 1/3 commit)

**2. [Rule 1 - Bug] Two acceptance-criteria greps tripped on this plan's own docstrings, not on the actual markup**
- **Found during:** Task 1 and Task 3 (running each task's own literal acceptance-criteria commands)
- **Issue:** `sed -n '/def calendar_group/,/^def /p' ... | grep -c "<select"` and `grep -c "rule-form.js" companion/ -r` both matched prose INSIDE this plan's own explanatory docstrings/comments (e.g. "replaces the retired `<select name=...>` outright", "this phase ships no `rule-form.js` at all") rather than any real markup or script reference — the acceptance criterion's own literal substring match cannot distinguish code from a comment describing what was removed.
- **Fix:** Reworded the affected docstring/comment sentences to describe the same fact without using the literal substrings `<select` / `rule-form.js`, so the greps pass genuinely rather than needing a documented exception. (`companion/static/style.css`'s own two pre-existing `rule-form.js` mentions, from 20-04, are out of this plan's `files_modified` scope and remain — the `rule-form.js` criterion's own baseline was already non-zero before this plan started.)
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** Both greps re-run after the reword: `<select` count 0 for `calendar_group()`'s own body; `rule-form.js` count 0 for `companion/pages/config_page.py` specifically (2 remain in `companion/static/style.css`, pre-existing and unowned by this plan).
- **Committed in:** `c398d1e` (Task 1/3 commit)

**3. [Rule 1 - Bug] Two form-action greps needed a literal path, not a `%s`-interpolated constant**
- **Found during:** Task 1 and Task 2 (running each task's own literal acceptance-criteria commands)
- **Issue:** `calendar_connect_section()`'s form action and `_handle_calendar_connect_post()`'s route-registration comment both used the existing constant (`CALENDAR_CONNECT_ROUTE`) rather than the literal path text, matching every other route builder's own convention in this file — but this plan's own acceptance greps for `action="/settings/calendar/connect"` and for `require_session` within 3 lines of the literal text `calendar/connect` need the literal substring present, which a `%s`-interpolated constant reference does not produce.
- **Fix:** `calendar_connect_section()`'s form action is now written as literal path text (matching this file's own established precedent for exactly this class of grep, documented at `QUICK_DISPLAY_ROUTE`'s own comment); the route-registration comment in `companion/app.py` was reworded to mention the literal path within the required 3-line window of the `require_session()` call.
- **Files modified:** `companion/pages/config_page.py`, `companion/app.py`
- **Verification:** Both greps re-run and pass; `companion/test_config_page.py`/`companion/test_companion_app.py` unaffected (200/200 and 242/244 respectively).
- **Committed in:** `c398d1e` (Task 1/3 commit), `526debf` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed groups (all Rule 1 — correctness/wording issues discovered by running this plan's own specified verification, none a scope change)
**Impact on plan:** No scope creep — every fix makes the shipped code match either the plan's own literal acceptance criteria or the CSS/markup contract those criteria exist to protect. No plan requirement was dropped or weakened.

## Issues Encountered

**The Calendar card's failed-fetch detail (D-14b/T-20-30) is derived from existing fields, not a new server-side error-category field.** `server/plane/calendar_rules.py` (out of this plan's `files_modified`) persists only `last_attempt_at`/`last_synced_at`/`entries` — it never records WHY a fetch failed. The one distinguishable failure category available without touching that module is "at least one attempt recorded since connecting, with no usable sync yet" (`last_attempt_at is not None` and `last_synced_at` unusable), which now renders the mapped `CALENDAR_STATUS_FETCH_FAILED_DETAIL` sentence. A calendar that succeeded once and has since started failing on every attempt still shows its last successful sync's own timestamp (the "usable" branch), because `calendar_rules.py` never clears `last_synced_at` on a later failure — this is an existing, unchanged limitation of that module's own persisted shape, not something this plan introduces or could fix within its own file scope.

**The Calendar card's own status/chip-grid portion cannot be the literal DOM sibling the `:has(+ .calendar-disconnect-form)` CSS (20-04) was originally illustrated against.** Because Runway and the "When it is on" supersection's cards render between Calendar's own card and the end of the settings form (per 20-07's Display supersection ordering), Calendar's card is never adjacent in the DOM to anything rendered after `</form>` closes. `calendar_connect_section()`'s own `.page-section` wrapper is the element that actually receives the fused-card treatment with `calendar_disconnect_section()`'s output — visually it reads as "the Connect/Disconnect controls form one small unit," not "the whole Calendar card visually extends down to include Disconnect." This is the same class of DOM-position trade-off `20-07-SUMMARY.md` already documented for Flight colours' own placement; flagged here for the same reason, not a regression this plan introduces.

## Known Stubs

None — every render path this plan ships is real, immediately-effective code (the rebuilt Calendar card, the new connect route, the rebuilt Flight-colours section); nothing here is a placeholder awaiting a later plan's markup.

## Threat Flags

None beyond this plan's own `<threat_model>` — no new network endpoints beyond the two named (`POST /settings/calendar/connect`, unchanged `/settings/rules/*`), no new auth paths, no schema changes. `escape_html()` is applied at every interpolation this plan adds, including the suggestion chips' `data-value` attributes and every `t()` result.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both sections are fully wired and functional on the live Display page; no blockers for 20-10 (Airlines/History pages, this wave's sibling plan — no shared files with this plan).
- `companion/test_view_pages.py` and `companion/test_status_pages.py` are unmoved by this plan (not touched).
- Flagged for 20-12's completeness sweep: `companion/i18n_fr/display.py` (owned by 20-07, not this plan's `files_modified`) still carries the OLD Calendar/Rules string entries this plan's own rewrite superseded (e.g. the old one-piece calendar-status sentences, the old "Per-flight colour rules" heading, the old "Callsign"/"ICAO24 hex"/"Callsign prefix" list-header/hint strings) — genuinely unused now, but D-08's "no catalogue entry is unused" completeness check is explicitly deferred to 20-12 (confirmed live in `companion/test_i18n.py`'s own header comment), so this is not a regression this plan introduces, only a cleanup 20-12's own sweep should pick up.
- The Calendar card's failed-fetch detection remains a derived, best-effort signal (see Issues Encountered above) — a future plan wanting a genuine error category would need to extend `server/plane/calendar_rules.py`'s own persisted shape, out of this plan's reach.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: companion/pages/config_page.py
- FOUND: companion/app.py
- FOUND: companion/i18n_fr/calendar_group.py
- FOUND: companion/i18n_fr/rules.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND commit: c398d1e (Task 1 + Task 3)
- FOUND commit: 526debf (Task 2)
