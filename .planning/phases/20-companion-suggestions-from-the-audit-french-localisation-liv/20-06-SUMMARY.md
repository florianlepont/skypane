---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 06
subsystem: ui
tags: [home-page, status-row, i18n, french, illustrations, wake-headline]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/i18n.py (t()), companion/i18n_fr/ auto-merging catalogue package, companion/prefs.py, ctx[\"lang\"]/ctx[\"simple_mode\"], companion/layout.py's QUICK_STATE_FIELD/ON/OFF"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-03: layout.status_row(label, verdict, detail, state), health_page.compute_health_state()'s verdict-free device_detail_html field, language-aware layout.local_clock_text()/relative_age_text()"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-04: every new CSS class this plan's markup depends on (.home-hero, .preview-frame*, .status-card*, .recent-flight__thumb*), including the measured warn-on-card contrast fallback"
provides:
  - "companion/pages/home_page.py rebuilt as a hero row (picture + one status_row()-based status card headlined by the next update) plus full-width recent flights with artwork thumbnails — no Quick actions card, no duplicated Frame verdict"
  - "companion/i18n_fr/home.py — Home's full French catalogue"
  - "the D-16 quick-action-route relocation's app.py half: QUICK_DISPLAY_ROUTE/QUICK_QUIET_HOURS_ROUTE now literal in companion/app.py instead of read off home_page.py"
affects: [20-07-display-regroup, 20-08-live-theme-preview, 20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_plain_text_from_markup(): strip tags + reverse HTML-entity escaping on a pre-built, already-escaped markup fragment before handing it to a primitive (status_row()) that escapes whatever it is given — the general reconciliation for any future caller that needs a health-state markup field's own visible text inside an already-escaping component"
    - "one _recent_flights() query result reused for both the hero's 'current flight' one-liner and the recent-flights list (row 0), never a second query for the same data (D-20)"
    - "a resolved illustration key always renders the <img> unconditionally, trusting /illustration/{key}.png's own not-found behaviour, rather than a per-row filesystem stat"

key-files:
  created:
    - companion/i18n_fr/home.py
  modified:
    - companion/pages/home_page.py
    - companion/test_view_pages.py
    - companion/app.py

key-decisions:
  - "layout.status_row()'s `detail` parameter escapes whatever it is given (20-03's own contract), but health_page.compute_health_state()'s device_detail_html/pipeline_html fields are raw, already-escaped markup fragments meant to be embedded verbatim — passing them straight through would have status_row() escape their own <span>/<p> tags into visible tag text. Added _plain_text_from_markup() (strip tags to a space, reverse the fragment's own HTML-entity escaping) so status_row()'s own escaping re-encodes the resulting plain text exactly once, not twice. This reconciles the plan's own literal instruction to read device_detail_html with status_row()'s escaping contract; applied identically to pipeline_html for the same reason on the Flight-data row, which the plan's own text did not separately call out but which the same escaping contract equally requires."
  - "The Battery row's verdict is now BATTERY_STATE_TEXT[state] (or 'No reading yet'), matching the UI-SPEC's copy table; its detail is '≈ NN% · NNNN mV' with no timestamp — the OLD code's verdict slot (the percentage) and detail slot (state text + mV + timestamp) are reshuffled to fit status_row()'s label/verdict/detail contract without introducing a second timestamp-markup-escaping case."
  - "The hero's flight one-liner includes the direction word (translated), matching this plan's own Task 2 action text ('callsign, then airline, then the route, then the direction') even though 20-UI-SPEC.md's own illustrative markup snippet omits it — the action text is the more specific, task-authored instruction and reuses the exact join-and-skip-empty convention the recent-flights list already established for the same fields."
  - "companion/i18n_fr/home.py deliberately omits 'Checking in normally'/'Has not checked in for a while'/'Has not checked in for a long time' and 'Home' — the first three are byte-identical to health_page.DEVICE_STATE_TEXT's own values (20-RESEARCH.md Pitfall 3) and 'Home' is nav.py's own nav-label key; companion/i18n_fr/__init__.py raises ValueError on a duplicate key across sibling modules, so these reuse the one shared catalogue entry rather than redefining it."

requirements-completed: [CFG-13, CFG-14, CFG-18]

# Metrics
duration: 70min
completed: 2026-09-11
---

# Phase 20 Plan 06: Home rebuilt — hero row, one status card, artwork thumbnails, no quick actions Summary

**Home's Quick-actions card is gone (D-16), its status card is three `layout.status_row()` rows headlined by "Next update ≈ HH:MM"/"Expected since HH:MM" with the Frame verdict appearing exactly once (fixing the confirmed duplicated-verdict defect), and the recent flights show an artwork thumbnail or dashed placeholder per row — all in French and English.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-11 (session start)
- **Completed:** 2026-09-11
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Deleted `_quick_actions_html()`/`_toggle_form_html()` and every quick-action constant from `companion/pages/home_page.py`; rebuilt the status card on three `layout.status_row()` calls with a headline that never presents a past next-wake time as still upcoming (D-16/D-17)
- Fixed the confirmed duplicated-verdict defect (20-RESEARCH.md Pitfall 3): the Frame row's verdict comes from `FRAME_STATE_TEXT` alone; its detail is the health state's own verdict-free timestamp field, reduced to plain text so it can safely pass through `status_row()`'s own escaping
- Rebuilt the hero as `.preview-frame` (picture + "Rendered HH:MM" caption + a callsign/airline/route/direction one-liner when the current flight is known) beside the status card, reusing the SAME recent-flights query result for both (D-20 — no new query)
- Every recent-flight row now renders a lazily-loaded 40×40 `/illustration/{key}.png` thumbnail when the airline resolves, or the dashed placeholder with no `<img>` at all otherwise (D-17.2)
- `companion/i18n_fr/home.py`: Home's full French catalogue; a fully-seeded Home render under `lang="fr"` proves the page title, section headings, status-row labels and headline all translate with no English leaking in, while callsign/airline data stays untranslated

## Task Commits

1. **Task 1: Delete the Quick actions card and rebuild the status card on status_row()** - `0fdbd9b` (feat)
2. **Task 2: the hero row and the recent-flights thumbnails** - `ef8ce7a` (feat)
3. **Task 3: Home's French catalogue and a French end-to-end render check** - `af6467b` (test)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/pages/home_page.py` - full rebuild: `_status_card_html()` (was `_status_tiles_html()`), `_hero_figure_html()` (was `_now_showing_html()`), `_recent_flights_html()`/`_recent_flight_thumb_html()`, `_flight_secondary_text()`, `_plain_text_from_markup()`; every quick-action builder/constant deleted
- `companion/i18n_fr/home.py` (new) - Home's full French catalogue (~40 entries), per 20-UI-SPEC.md's Copywriting Contract Section A
- `companion/test_view_pages.py` - retargeted the seeded-render and empty-ctx Home checks off the deleted markup; added 9 new checks (no-quick-action/status-row-count/Frame-sentence-once, the headline's three states, the Health link's simple_mode gating, the thumbnail's resolved-vs-placeholder rendering, the hero's document-order and flight-one-liner presence, a French headings/alt-text check, a full French end-to-end render, and the catalogue-merge-key proof); `EXPECTED_CHECK_COUNT` 85 → 87 → 90 → 92
- `companion/app.py` - `QUICK_DISPLAY_ROUTE`/`QUICK_QUIET_HOURS_ROUTE` now literal (D-16's own deletion of home_page.py's copies broke app.py's module-level cross-reference; see Deviations)

## Decisions Made
See `key-decisions` in the frontmatter above — the `_plain_text_from_markup()` reconciliation (applied to both the Frame and Flight-data rows), the Battery row's verdict/detail reshuffle, the flight one-liner's direction word, and the deliberate catalogue-key omissions to avoid the auto-merge package's duplicate-key error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `layout.status_row()`'s escaping contract conflicts with the plan's literal instruction to embed `device_detail_html`/`pipeline_html` directly**
- **Found during:** Task 1
- **Issue:** 20-03-PLAN.md's `status_row(label, verdict, detail, state)` escapes its own `detail` parameter unconditionally (`escape_html(detail)`), documented as expecting already-resolved plain display text. `health_page.compute_health_state()`'s `device_detail_html` and `pipeline_html` fields are the OPPOSITE: raw, already-escaped markup fragments (`<span class="mono" title="...">...</span>` etc.) meant to be embedded verbatim, exactly like `layout.concise_timestamp_html()`'s own documented contract ("callers interpolate the return value verbatim — never re-escape it"). Passing either field straight through as `status_row()`'s `detail` would have that escaping turn the fragment's own tags into visible tag text on the page — a real rendering defect, not a cosmetic one, and one this plan's own literal instruction ("The Frame row's detail is `ctx["health_state"]["device_detail_html"]`") would otherwise have shipped.
- **Fix:** Added `_plain_text_from_markup()`: strips tags (each becomes a space, so two adjacent paragraphs read as two separated words) and reverses the fragment's own HTML-entity escaping via `html.unescape()`, so `status_row()`'s own escaping re-encodes the resulting plain text exactly once. Applied to both `device_detail_html` (Frame row) and `pipeline_html` (Flight-data row) — the plan's own text only named the Frame row, but the identical escaping-contract mismatch applies equally to the Flight-data row, which also used to embed `pipeline_html` as a second markup paragraph in the OLD code.
- **Files modified:** `companion/pages/home_page.py`
- **Verification:** `companion/test_view_pages.py`'s seeded-render check renders both rows correctly with no visible tag text; the plan's own acceptance-criteria greps (`device_detail_html` appears exactly once, `device_html` appears zero times) still pass.
- **Committed in:** `0fdbd9b` (Task 1 commit)

**2. [Rule 3 - Blocking] `companion/app.py` failed to import after `home_page.py`'s D-16 deletion removed the constants it read**
- **Found during:** Task 1, running `companion/test_view_pages.py`'s end-to-end HTTP subprocess check
- **Issue:** `companion/app.py` (owned by 20-08, not in this plan's declared file scope) read `QUICK_DISPLAY_ROUTE`/`QUICK_QUIET_HOURS_ROUTE` directly off `home_page.py` at module level (`QUICK_DISPLAY_ROUTE = home_page.QUICK_DISPLAY_ROUTE`) and asserted `POLL_ROUTE == home_page.POLL_ROUTE` — the exact avoiding-a-circular-import idiom this codebase already uses elsewhere. Deleting these constants from `home_page.py`, exactly as this plan's Task 1 explicitly instructs, made `companion.app` raise `AttributeError` at import time, which breaks the ENTIRE companion HTTP server (every subprocess-backed test harness in the suite, not only this plan's own), not merely Home's own markup.
- **Fix:** Gave `QUICK_DISPLAY_ROUTE`/`QUICK_QUIET_HOURS_ROUTE` their own literal values in `companion/app.py` (byte-identical to the values `home_page.py` used to define), mirroring how `POLL_ROUTE` already has its own independent literal there; removed the now-meaningless assert.
- **Files modified:** `companion/app.py`
- **Verification:** `companion/test_view_pages.py` (92/92), `companion/test_status_pages.py` (210/211, the one documented root-sandbox FAIL), `companion/test_config_page.py` (181/181) and the full `scripts/run-all-tests.sh` sweep all confirm no import-time regression; `python3 -m compileall -q companion server` passes.
- **Committed in:** `0fdbd9b` (Task 1 commit)
- **Boundary note:** `companion/app.py` is declared owned by 20-08 in this worktree's `project_specifics`, not in this plan's own `files_modified`. Fixed inline rather than deferred — a direct, mechanical, unavoidable consequence of this plan's own required deletion (D-16), and leaving it broken would fail every subprocess-backed test in the whole suite, not just this plan's own. The change is a pure relocation of three string literals with byte-identical values; it does not touch any route handler, flash key or redirect target 20-08 owns.

**3. [Rule 3 - Blocking] `companion/i18n_fr/home.py`'s own catalogue tripped the auto-merge package's duplicate-key guard**
- **Found during:** Task 2 (pulled forward from Task 3 — see below)
- **Issue:** `FRAME_STATE_TEXT`'s three values are byte-identical to `health_page.DEVICE_STATE_TEXT`'s own three values (20-RESEARCH.md Pitfall 3's own finding), and `companion/i18n_fr/health.py` (20-03) already owns those three keys in the shared catalogue; a first draft of `home.py`'s own `CATALOG` redefined them, tripping `companion/i18n_fr/__init__.py`'s duplicate-key `ValueError` at import time.
- **Fix:** Removed the three colliding keys from `companion/i18n_fr/home.py`, with a comment explaining the reuse — `i18n.t()` resolves them from the one shared catalogue entry regardless of which page calls it.
- **Files modified:** `companion/i18n_fr/home.py`
- **Verification:** `python3 -c "import companion.i18n_fr"` succeeds; `companion/test_i18n.py` (11/11).
- **Committed in:** `ef8ce7a` (Task 2 commit)

**4. [Process] `companion/i18n_fr/home.py` (Task 3's own deliverable) pulled forward into Task 2's commit**
- **Issue:** Task 2's own plan-mandated French-render check (headings/alt-text translating) needs at least Home's own catalogue entries to exist for that commit to be independently buildable and passing on its own — the same "every commit stays independently buildable" precedent 20-01-SUMMARY.md documents for its own Task 2/Task 3 split.
- **Fix:** Created the full `companion/i18n_fr/home.py` catalogue (all of Home's French strings, not only the Task 2-relevant subset) in Task 2's commit; Task 3's own commit adds only the broader end-to-end French sweep check and the catalogue-merge-completeness check on top, with zero further changes to the catalogue file itself.
- **Committed in:** `ef8ce7a` (Task 2 commit)

---

**Total deviations:** 4 (2 Rule 1/bug-shaped escaping-contract fixes, 1 Rule 3/blocking import fix crossing a nominal file-ownership boundary, 1 process note on commit sequencing)
**Impact on plan:** No scope creep and no plan requirement dropped or weakened. Every fix is a same-effect correction (a relocation of literal values, a mechanical duplicate-key removal, or an escaping reconciliation) required for this plan's own acceptance criteria and verification to actually pass, not a new feature or a different design.

## Issues Encountered

**`companion/test_companion_app.py`'s `_home_page_renders_widgets()` check now fails, beyond the two documented root-sandbox FAILs.** This check (owned by 20-08 per this worktree's file-ownership map, and explicitly scheduled for retargeting by 20-12-PLAN.md's own `files_modified` list) does a real end-to-end HTTP `GET /` and asserts the OLD Quick-actions markup and "On the frame now" heading — both deliberately removed by this plan's D-16/D-17 rebuild. `companion/test_companion_app.py` is not in this plan's declared file scope and 20-12 (a later, dependent plan in this same phase) explicitly owns retargeting it as part of its own completeness sweep; this is the phase's own designed wave sequencing, not a regression this plan introduced carelessly. Confirmed via `scripts/run-all-tests.sh`: `companion-app: 224/227` (the 2 documented root-sandbox FAILs plus this one expected, temporary FAIL) — no other harness in the full suite shows any new failure.

No other issues — every task's own `<verify>` command passed as specified, and `scripts/run-all-tests.sh` shows exactly the three known FAILED harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`), identical in shape to `main` apart from the one expected, documented addition above.

## Known Stubs

None — every function this plan ships is real, immediately-effective code; nothing here is a placeholder awaiting a later plan's markup.

## Threat Flags

None beyond the phase's own `<threat_model>` register. The `_plain_text_from_markup()` deviation (see above) changes HOW the existing `device_detail_html`/`pipeline_html` → Home-markup data flow is handled (strip-and-re-escape instead of the threat model's described "pass through unchanged"), but does not introduce any new surface: the same trust boundary (health-state dict → Home markup, T-20-25) is crossed exactly once, and the new mechanism produces a strictly single-escaped result rather than the threat model's assumed zero-escaping passthrough — a neutral-to-positive change from a correctness/XSS standpoint, not a new risk.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `companion/pages/home_page.py`'s rebuild is complete and self-contained; 20-07 (Display) and 20-08 (live theme preview / app.py) can proceed without any further change to Home.
- `companion/i18n_fr/home.py` demonstrates the same full-page translation pattern 20-03's `health.py` established (constants stay English, `i18n.t()` wraps at the render site, `%`-templates translate before formatting) and deliberately reuses `health.py`'s/`nav.py`'s own catalogue entries rather than redefining them.
- `companion/test_view_pages.py` (92/92) and `companion/test_i18n.py` (11/11) both exit 0. `companion/test_status_pages.py` (210/211) and `companion/test_config_page.py` (181/181) are confirmed unmoved by this plan's own scope.
- **Blocker for 20-12:** `companion/test_companion_app.py`'s `_home_page_renders_widgets()` check needs retargeting to the new Home markup (drop the Quick-actions/"On the frame now" needles, assert the new hero/status-card shape instead) — already scheduled in 20-12-PLAN.md's own `files_modified` list, not a surprise, but flagged here so 20-12's own executor sees it confirmed rather than rediscovering it.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*
