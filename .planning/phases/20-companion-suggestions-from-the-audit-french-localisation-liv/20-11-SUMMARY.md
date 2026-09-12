---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 11
subsystem: ui
tags: [notifications, ntfy, theme-preview, i18n, french, data-attributes, config-page]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    plan: 02
    provides: "server/notify.py's send_notification()/body_for_lang()/TEST_NOTIFICATION_TITLE/BODY, and server/device_config.py's notifications config group (DEFAULT_NOTIFICATIONS/normalise_notifications())"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    plan: 08
    provides: "companion/theme_preview.py's ?live=1 render/cache path and companion/static/theme-preview.js's chip-selection swap, both already wired and waiting for markup"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    plan: 09
    provides: "the calendar_connect_section()/status_row() write-only-URL and disclosure idioms this plan's Notifications group mirrors"
provides:
  - "companion/screens.py — GROUP_NOTIFICATIONS, joined to the plane frame's advanced_groups and to scope_groups()'s legacy SCOPE_ALL tuple"
  - "companion/pages/config_page.py — notifications_group()/notifications_test_section() (the Device-page Notifications card and its standalone 'Send a test' form), handle_post()'s notifications field resolution (D-26/D-28), and theme_fieldset()'s new live-preview figure plus every chip's data-preview-src attribute"
  - "companion/app.py — POST /settings/notifications/test (_handle_notifications_test_post()), session-gated, reading the topic URL from stored config only"
  - "companion/i18n_fr/notifications.py — the Notifications group's French catalogue"
  - "companion/static/copy-button.js/dirty-state.js/list-filter.js — screen-bound English literals moved to server-rendered, translated data-* attributes"
affects: [20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "notifications_group()'s in-form card is split from notifications_test_section()'s own standalone form, mirroring calendar_group()/calendar_connect_section()'s split — an immediate-POST form can never nest inside <form id=settings-form>"
    - "handle_post() reads the CURRENT on-disk notifications sub-dict via device_config.load_device_config() (never trusting ctx) before building the full replacement dict, because save_device_config(notifications=...) replaces the whole sub-dict rather than merging it per sub-key like every scalar field"
    - "data-*-template + %d-token client-side substitution (list-filter.js's data-filter-count-template, mirroring poll-cooldown.js's data-cooldown-template/data-cooldown-token idiom) for a two-placeholder translated sentence a script must re-render on every keystroke"

key-files:
  created:
    - companion/i18n_fr/notifications.py
  modified:
    - companion/screens.py
    - companion/pages/config_page.py
    - companion/app.py
    - companion/pages/history_page.py
    - companion/static/copy-button.js
    - companion/static/dirty-state.js
    - companion/static/list-filter.js
    - companion/i18n_fr/display.py
    - companion/i18n_fr/flights.py
    - companion/test_i18n.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_view_pages.py

key-decisions:
  - "GROUP_NOTIFICATIONS joins scope_groups()'s legacy SCOPE_ALL tuple (in addition to the Device screen's own advanced_groups), because a pinned test asserts the union of Display's and Device's own groups equals that legacy tuple's set exactly — four pre-existing checks retargeted in place for the resulting eighth data-dirty-section/theme-status group and the notifications sub-dict's now-in-scope checkbox resolution on an unscoped legacy post."
  - "The D-06 orchestrator addendum (list-filter.js's 'X of Y shown' template) is scoped to companion/pages/history_page.py only, matching this plan's own files_modified list — airlines_page.py/health_page.py render the identical shared filter bar but are out of scope here; the script's own hardcoded fallback keeps their count text exactly as it was before this change (no regression), flagged for whichever plan next touches those two files to extend the same attribute."
  - "'Notifications' is a genuine French/English cognate (identical spelling and pronunciation), added to companion/test_i18n.py's _UNCHANGED_IN_FRENCH exemption set per this project's own established precedent (Corroboration/Source/Description) rather than manufacturing an artificial French synonym."
  - "The live theme preview's initial <img src> uses current_theme_id (the SAVED value), never effective_theme_id (a rejected save's own submitted/pending selection) — D-24's no-JS floor is 'the preview shows the saved theme', which must hold even while the chip grid's own selection is being redisplayed from a failed submission."
  - "The two new flash messages (notifications_test_ok/failed) are English-only, matching the established, pre-existing pattern for every other flash key in companion/app.py (calendar_connect_ok/invalid included) — flash-message translation has no wiring anywhere in this codebase yet (FLASH_MESSAGES/_resolve_flash_text() are never passed through i18n.t()), a pre-existing gap this plan does not expand or fix, deferred to 20-12."

requirements-completed: [CFG-13, CFG-16, CFG-17]

# Metrics
duration: ~100min
completed: 2026-09-12
---

# Phase 20 Plan 11: Notifications group, the live theme preview markup, and the last D-06 script literals Summary

**A Notifications group on Device (write-only topic URL, two checkboxes, an immediate "Send a test" route reading the stored config only), a large live theme preview above Display's chip grid sourced from the last real flight, and copy-button.js/dirty-state.js/list-filter.js's remaining English literals moved to server-rendered, translated `data-*` attributes**

## Performance

- **Duration:** ~100 min (approx.)
- **Completed:** 2026-09-12
- **Tasks:** 3
- **Files modified:** 14 (1 created, 13 modified)

## Accomplishments
- `notifications_group()` (D-26/D-28): a `.theme-status` card on Device with a `status_row()` reporting only Configured/Not configured (never the URL, never a masked fragment — T-20-12), the topic-URL field inside a "Replace the URL" `<details>` once configured, and two `settings-checkbox` inputs — all three wait on the page-wide Save. `notifications_test_section()` renders "Send a test" as its own immediate-POST form, a sibling of `#settings-form`, positioned right after the Notifications card and before Manual refresh.
- `_handle_notifications_test_post()` (`POST /settings/notifications/test`): session-gated, reads the topic URL from `device_config.load_device_config(state_dir)["notifications"]` only — a submitted `topic_url` field is never read at all (T-20-13) — and calls `notify.send_notification()` with the fixed test title/body translated into the stored `lang` via `notify.body_for_lang()`.
- `handle_post()`'s notifications resolution: the two checkboxes follow the same in-scope-absent-means-False rule every sibling checkbox uses; an empty (stripped) topic-URL submission carries the current on-disk URL forward (never clears it); `lang` is written silently from `ctx["lang"]` at save time — there is no language-picking control anywhere in the group.
- `theme_fieldset()`'s multi-theme branch gains a `<figure class="theme-live-preview">` directly above the chip grid: `src="{prefix}{current_theme_id}.png?live=1"`, `loading="eager"`, explicit `width`/`height` from `theme_preview.THEME_PREVIEW_SIZE`, captioned with the most recent runway event's callsign or the sample-flight wording. Every chip's own `<label>` (in `_theme_chip_grid_html()`, applied additively to every grid this function renders) gains `data-preview-src` ending in `.png?live=1`; the chips' own `<img>` sources are unchanged — still the fixed fictional scene, still `loading="lazy"`.
- `copy-button.js`'s `FEEDBACK_TEXT` and `dirty-state.js`'s five connector-word literals (the "changed" suffix, the two-item "and", the three-plus-item ", and", and the singular/plural unsaved-change sentence) now read from `data-copied-text` (`history_page._copy_button_html()`) and five `data-dirty-*` attributes (`config_page.py`'s `dirty_bar_html`) respectively — each with a short, documented English fallback for an un-updated caller. `freshness.js`/`confirm-submit.js`/`poll-cooldown.js` were re-verified by direct grep to already read every screen-bound string from `data-*` attributes; confirmed byte-unchanged (`git diff --stat` empty).
- Orchestrator addendum (D-06): `list-filter.js`'s hardcoded `"X of Y shown"` template now reads `data-filter-count-template` (`history_page._filter_bar_html()`), scoped to the History page only per this plan's own `files_modified` list — the pre-existing French translation (`companion/i18n_fr/health.py`'s `"%d of %d shown": "%d sur %d affichés"`) needed no new catalogue entry.

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: The Notifications group, its save path, "Send a test", and the live theme preview markup** - `8d20b9d` (feat)
2. **Task 3: copy-button.js/dirty-state.js/list-filter.js's remaining English literals move to data-* attributes** - `3545734` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

**Task 1/Task 2 committed together:** both tasks edit `companion/pages/config_page.py` and `companion/test_config_page.py` in ways that were interleaved in one continuous editing session before either was committed (the identical situation 20-09-SUMMARY.md documents and resolves the same way) — splitting the working-tree diff into two commits after the fact would have required costly manual hunk-splitting for no real benefit. `companion/screens.py`, `companion/app.py`, `companion/i18n_fr/notifications.py` and `companion/test_companion_app.py` are Task 1's alone; `companion/i18n_fr/display.py`'s new live-preview French entries are Task 2's alone.

## Files Created/Modified
- `companion/screens.py` — `GROUP_NOTIFICATIONS`, joined to the plane frame's `advanced_groups` (after `GROUP_WAKE_INTERVAL`, per D-10's order) and to the module's own documentation-only `ADVANCED_GROUPS` tuple
- `companion/pages/config_page.py` — `notifications_group()`/`notifications_test_section()` (new), `_theme_live_preview_html()` (new), `theme_fieldset()`'s live-preview wiring, `_theme_chip_grid_html()`'s new `data-preview-src` attribute, `scope_groups()`'s legacy `SCOPE_ALL` tuple extended with `GROUP_NOTIFICATIONS`, `render()`'s builders dict/`notifications_test_html` wiring, `handle_post()`'s notifications field resolution, the `dirty_bar_html`'s five new `data-dirty-*` attributes, and a dozen new module-level constants (routes, flash keys, copy)
- `companion/app.py` — `NOTIFICATIONS_TEST_ROUTE` rebinding, `FLASH_KEY_NOTIFICATIONS_TEST_OK`/`_FAILED` rebinding + `FLASH_MESSAGES`/`FLASH_ROLES` entries, `_handle_notifications_test_post()` (new), the `do_POST()` dispatch line, and `notify` added to the `server` import
- `companion/i18n_fr/notifications.py` (new) — the Notifications group's French catalogue (heading/caption, status verdicts, topic-URL field/hint, checkboxes, "Send a test" and its two flash strings — the latter defined but not yet wired, see Decisions)
- `companion/i18n_fr/display.py` — the live theme preview's alt/caption strings and the dirty bar's five connector words, both new
- `companion/pages/history_page.py` — `_copy_button_html()`'s new `data-copied-text` attribute, `_filter_bar_html()`'s new `data-filter-count-template` attribute
- `companion/i18n_fr/flights.py` — `"Copied": "Copié"` (new)
- `companion/static/copy-button.js` — `FEEDBACK_TEXT` replaced by `copiedText(button)` reading `data-copied-text`, with a documented `FALLBACK_FEEDBACK_TEXT`
- `companion/static/dirty-state.js` — `updateBar()`'s five hardcoded connector words replaced by five `data-dirty-*` reads off the dirty-bar element, each with a documented fallback
- `companion/static/list-filter.js` — the "X of Y shown" template replaced by a `data-filter-count-template` read with `.replace("%d", ...)` substitution
- `companion/test_i18n.py` — `"Notifications"` added to `_UNCHANGED_IN_FRENCH` (a genuine cognate, no count change)
- `companion/test_config_page.py` — 4 pre-existing legacy-scope checks retargeted in place (the seven-vs-eight `.theme-status`/`data-dirty-section` group counts, the full-dict-equality post-a-legacy-save check); 9 new checks (5 for Task 1's Notifications group, 4 for Task 2's live preview); `EXPECTED_CHECK_COUNT` 200 → 205 → 209
- `companion/test_companion_app.py` — 5 new checks for the test route (session-gated, unconfigured-fails, configured-succeeds, sender-returning-False, submitted-topic_url-ignored); 2 new ES5-safe/banned-sink checks for copy-button.js/dirty-state.js; `EXPECTED_CHECK_COUNT` 244 → 249 → 251
- `companion/test_view_pages.py` — 1 pre-existing check's substring match widened with a negative-lookahead regex (the new `data-filter-count-template` sibling attribute); 2 new checks (`data-copied-text` EN/FR, `data-filter-count-template` EN/FR); `EXPECTED_CHECK_COUNT` 103 → 104 → 105

## Decisions Made
See `key-decisions` in the frontmatter above — five decisions, the most structurally significant being the legacy `SCOPE_ALL` tuple extension (required by a pre-existing union-equality invariant) and the deliberate scoping of the D-06 filter-count fix to History alone.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `scope_groups()`'s legacy `SCOPE_ALL` tuple needed `GROUP_NOTIFICATIONS` too**
- **Found during:** Task 1, first full test run after adding the group to `advanced_groups`
- **Issue:** `companion/test_config_page.py`'s own `_scope_groups_follow_the_screen_registry()` pins the invariant that `scope_groups(SCOPE_ALL)`'s set equals the union of Display's and Device's own groups. Adding `GROUP_NOTIFICATIONS` to Device's `advanced_groups` without adding it to the legacy tuple broke that union-equality check (199/200).
- **Fix:** Added `screens.GROUP_NOTIFICATIONS` as the eighth and last member of `scope_groups()`'s legacy `SCOPE_ALL` tuple, mirroring every other group's presence there.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `companion/test_config_page.py` returned to 200/200 immediately, then climbed with each task's own new checks
- **Committed in:** `8d20b9d` (Task 1/2 commit)

**2. [Rule 1 - Bug] Four pre-existing legacy-scope checks retargeted for the eighth group**
- **Found during:** Task 1, same test run
- **Issue:** With `GROUP_NOTIFICATIONS` now in the legacy `SCOPE_ALL` tuple, `render(ctx)`'s unscoped legacy render gained an eighth `.theme-status`/`data-dirty-section` group and, on an unscoped `handle_post()` call, the notifications sub-dict's two checkboxes now resolve in-scope (absent-means-False) rather than carrying `DEFAULT_NOTIFICATIONS`'s True/True forward. Four checks had hardcoded the old six/seven-group counts and the old True/True expectation.
- **Fix:** Retargeted each in place: two count checks (six→seven `.theme-status` occurrences; seven→eight `data-dirty-section` occurrences and document-order list, both gaining "Notifications" at the end), and the full-dict-equality post-a-legacy-save check's expected `notifications` sub-dict (`battery_low`/`frame_silent` False, not `DEFAULT_NOTIFICATIONS`'s True/True, since the fields are now genuinely in scope for that unscoped post).
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` → 200/200 immediately after the retarget
- **Committed in:** `8d20b9d` (Task 1/2 commit)

**3. [Rule 1 - Bug] Missing French translations for the live-preview strings broke the completeness expectation**
- **Found during:** Task 2, the new French-render check
- **Issue:** `THEME_LIVE_PREVIEW_ALT_TEMPLATE`/`THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE`/`THEME_LIVE_PREVIEW_CAPTION_SAMPLE` had no catalogue entries at all — a French render of the live preview still showed the English caption verbatim.
- **Fix:** Added all three to `companion/i18n_fr/display.py` (the Display/Device pages' own catalogue module), including the D-09-correct non-breaking space before the colon in "Aperçu avec votre dernier vol : ".
- **Files modified:** `companion/i18n_fr/display.py`
- **Verification:** the new French-render check passed after the addition
- **Committed in:** `8d20b9d` (Task 1/2 commit)

**4. [Rule 1 - Bug] Self-referential grep false positives in this plan's own docstrings (Task 2's acceptance criteria)**
- **Found during:** Task 2, running the plan's own literal acceptance-criteria greps
- **Issue:** `grep -c "data-preview-src"` (expected `1`), `grep -c 'loading="eager"'` (expected `1`), and `grep -c "notifications_lang"` (expected `0`) all initially failed because this plan's own explanatory docstring prose repeated the exact literal substrings being described — the same class of false positive 20-08-SUMMARY.md/20-09-SUMMARY.md already document for their own acceptance greps.
- **Fix:** Reworded the affected docstring sentences to describe the same facts without repeating the literal substrings (e.g. "eagerly loaded" instead of quoting `loading="eager"`; "no language-picking control" instead of quoting `<select name="notifications_lang">`).
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** all three greps re-run and pass exactly as worded
- **Committed in:** `8d20b9d` (Task 1/2 commit)

**5. [Rule 1 - Bug] `"Notifications"` tripped the completeness harness's cognate check**
- **Found during:** Task 1, the first full-suite run after adding `companion/i18n_fr/notifications.py`
- **Issue:** `companion/test_i18n.py`'s `_check_every_catalog_value_is_str_and_differs_from_key()` failed: `"Notifications": "Notifications"` is byte-identical in both languages, which that check treats as a likely missed translation unless the key is in the documented cognate exemption set.
- **Fix:** Added `"Notifications"` to `_UNCHANGED_IN_FRENCH`, following the exact precedent this frozenset already documents for `"Corroboration"`/`"Source"`/`"Description"` — a genuine, spelling-identical French/English loanword, not a missed translation. Explicitly authorized for this plan by the wave's own `project_specifics` ("companion/test_i18n.py's exemption set only for a genuine cognate").
- **Files modified:** `companion/test_i18n.py`
- **Verification:** `companion/test_i18n.py` → 11/11
- **Committed in:** `8d20b9d` (Task 1/2 commit)

**6. [Rule 1 - Bug] Extending `list-filter.js`'s attribute to Airlines/Health broke a file outside this plan's scope**
- **Found during:** Task 3 (orchestrator addendum), first full test run after touching `airlines_page.py`/`health_page.py`
- **Issue:** Initially added the same `data-filter-count-template` attribute to `airlines_page.py`'s and `health_page.py`'s own `_filter_bar_html()`/`_registry_filter_bar_html()` for consistency across the shared script's three consumers. This broke two pre-existing checks — one in `companion/test_view_pages.py` (mine) and one in `companion/test_status_pages.py` (NOT mine, owned by another plan) — both asserting `rendered.count("data-filter-count") == 1`, now `2` because the new sibling attribute name `data-filter-count-template` contains the old marker as a literal prefix.
- **Fix:** Reverted `airlines_page.py`/`health_page.py` entirely (`git checkout --`), scoping this task to `history_page.py` only — safely within this plan's own `files_modified` list, and `list-filter.js`'s own fallback keeps Airlines/Health's count text exactly as it was before this change (still hardcoded English, matching the pre-existing state, not a new regression). Retargeted the one check I do own (`test_view_pages.py`) with a negative-lookahead regex (`r"%s(?!-template)" % re.escape(marker)`) so it correctly counts the boolean marker once regardless of the new sibling attribute's name.
- **Files modified:** `companion/test_view_pages.py` (retarget); `companion/pages/airlines_page.py`/`companion/pages/health_page.py` (reverted, zero net change)
- **Verification:** `companion/test_view_pages.py` → 105/105; `companion/test_status_pages.py` returned to its baseline 210/211 (the one documented root-sandbox FAIL)
- **Committed in:** `3545734` (Task 3 commit) — the revert left no trace in the final diff

---

**Total deviations:** 6 auto-fixed (all Rule 1 — direct, mechanical consequences of this plan's own additions, discovered by running each task's own specified verification)
**Impact on plan:** No scope creep — every fix keeps the shipped code correct against either a pre-existing pinned invariant or this plan's own acceptance criteria. Deviation 6 is the most consequential: it corrected an over-reach (touching two files outside this plan's `files_modified` list) back to the plan's actual scope, rather than leaving the over-reach in place and fixing a third file I do not own.

## Issues Encountered

**One of this plan's own literal acceptance-criteria greps cannot be satisfied exactly as worded, for a reason unrelated to this plan's diff** — noted here rather than silently "passed", following the exact precedent 20-04-SUMMARY.md/20-08-SUMMARY.md document for their own stale greps:

`grep -c "<script\|onclick=\|onchange=" companion/pages/config_page.py` is expected to output `0`; it outputs `1`. Confirmed via `git show dfc503a94:companion/pages/config_page.py | grep -c "<script\|onclick=\|onchange="` that this single occurrence is pre-existing (a docstring sentence inside `poll_trigger_section()`, "this function emits ZERO `<script>` elements", predating this plan entirely) — this plan's own diff contributes zero new occurrences. The substantive requirement the criterion exists to protect — no real `<script>`/`onclick=`/`onchange=` markup anywhere in this plan's own additions — is independently confirmed: the live-preview `<figure>`/`<img>`/`<figcaption>` and the Notifications group's markup carry neither.

No other issues — every task's own `<verify>` command and acceptance criterion (once the docstring-wording deviations above were fixed) passed as specified, and the full local suite (`scripts/run-all-tests.sh`) shows exactly the three documented root-sandbox failures (2 in `companion/test_companion_app.py`'s WR-11 read-only-directory cases, 1 in `companion/test_status_pages.py`'s `anomaly_active()` case) — identical to the baseline before this plan, and identical to `main`.

## Known Stubs

None — every function, route and script this plan ships is real, immediately-effective code. The two flash strings in `companion/i18n_fr/notifications.py` for "Test notification sent."/"Couldn't reach that topic — check the URL." are defined but not yet wired into `_resolve_flash_text()` (see Decisions above, and the Threat Flags/Next Phase Readiness notes below) — this is a documented, deliberate scope boundary matching every other flash key in this codebase today, not an unfinished feature of this plan's own.

## Threat Flags

None beyond this plan's own `<threat_model>` — no new network endpoints beyond the one named (`POST /settings/notifications/test`), no new auth paths, no schema changes. `escape_html()` is applied at every interpolation this plan adds, including the live-preview caption's callsign and every `data-*` attribute value; the test route reads the topic URL exclusively from stored config, never the request body (T-20-13, pinned by a dedicated check); the write-only URL contract is preserved verbatim (T-20-12, pinned by a substring-absence check against a seeded URL).

## User Setup Required

None — no external service configuration required for this plan's own scope. The end-to-end human check (pasting a real ntfy topic URL, saving, and pressing "Send a test" to confirm delivery to a phone) is deferred to end-of-phase per this plan's own `<verification>` block; it is not a gap in this plan's scope, since a real device and a real topic are the only proof of delivery.

## Next Phase Readiness
- The Notifications group, the live theme preview markup, and the last two `data-*`-driven scripts are all fully wired and functional — no blockers for 20-12's completeness sweep.
- Flagged for 20-12: `companion/i18n_fr/notifications.py`'s two flash-message French entries ("Test notification sent."/"Couldn't reach that topic — check the URL.") are defined but currently unreachable, since flash-message translation has no wiring anywhere in `companion/app.py` yet (a pre-existing gap this plan did not create or expand — every other flash key, including this phase's own calendar-connect keys, has the identical gap). Whichever plan first wires `FLASH_MESSAGES`/`_resolve_flash_text()` through `i18n.t()` will make these two entries live with no further catalogue work.
- Flagged for whichever plan next touches `companion/pages/airlines_page.py`/`companion/pages/health_page.py`: both render the identical shared filter bar `list-filter.js` now expects a `data-filter-count-template` attribute from; today they fall back to the script's own hardcoded English default (unchanged from before this plan). Extending the same one-line attribute this plan added to `history_page.py`'s `_filter_bar_html()` would complete D-06 for all three consumers.
- `companion/test_view_pages.py` (105/105) and `companion/test_config_page.py` (209/209) are confirmed green; `companion/test_status_pages.py` (210/211, the one documented root-sandbox FAIL) and `server/test_config_history.py` (69/69) are confirmed unmoved by this plan.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: companion/screens.py
- FOUND: companion/pages/config_page.py
- FOUND: companion/app.py
- FOUND: companion/i18n_fr/notifications.py
- FOUND: companion/i18n_fr/display.py
- FOUND: companion/pages/history_page.py
- FOUND: companion/i18n_fr/flights.py
- FOUND: companion/static/copy-button.js
- FOUND: companion/static/dirty-state.js
- FOUND: companion/static/list-filter.js
- FOUND: companion/test_i18n.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND: companion/test_view_pages.py
- FOUND commit: 8d20b9d (Task 1 + Task 2)
- FOUND commit: 3545734 (Task 3)
