---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 14
subsystem: i18n
tags: [i18n, translation, python, stdlib]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: companion.i18n.Message/msg()/REGISTRY, companion.i18n_fr.BY_ID, test-support/i18n_ids.py (40-12); Home/Flights/Airlines/Health migrated, cross-area ids for display.delete/runway/callsign/rules.flight/rules.aircraft, registry.py's runway labels (40-13)
provides:
  - config_page.py and every companion/settings/*.py module fully migrated onto companion.i18n.Message stable ids
  - companion/i18n_fr/display.py 101/105 entries converted to MESSAGES (4 residual, dead literals with no call site anywhere — see Decisions)
  - companion/i18n_fr/calendar_group.py, notifications.py, rules.py fully converted to id-keyed MESSAGES (zero residual CATALOG)
  - Every theme-name and screen-label display site (companion/settings/theme.py, runway_led.py, config_page.py) declares the Message companion/i18n_fr/registry.py's own still-legacy CATALOG will resolve through
affects: [40-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A catalogue module mid-migration (CATALOG some entries, MESSAGES the rest) is a normal, test-passing intermediate state within one plan's own two tasks, not just across plans — Task 1 left 51 of display.py's 105 entries as legacy CATALOG specifically because their only declaring call site (config_page.py, notifications.py, calendar.py, rules.py) was Task 2's own file scope; converting an entry's catalogue value before its call site declares the Message would have broken the byte-identical render baseline mid-plan"
    - "Before converting a catalogue's remaining entries, check whether some of them are already resolvable via a Message declared in an unrelated, always-imported module (companion/app.py's own eager page-module imports mean every companion.pages.*.py Message is registered before any request is served) — three of display.py's original 58 Task-2-owned entries (on/off/on_to) and four more (callsign/delete/applies_the_next_time_the_frame_wakes_up/poll_triggered_recently_try_again_in_n_s) turned out to already be safely convertible within Task 1 itself, discovered by running `python3 -c 'import companion.app; ...; k in i18n.REGISTRY'` rather than assuming"
    - "A handful of retired constants that no longer reach any i18n.t() call site (companion/ui_base.py's QUICK_ACTION_SWITCH_ON_BUTTON/OFF_BUTTON/QUIET_TURN_ON_BUTTON/OFF_BUTTON, kept only as plain-str names a test asserts are no longer rendered) have nowhere left to declare a Message — their catalogue entries stay legacy CATALOG permanently, not as a residual to finish later"

key-files:
  created: []
  modified:
    - companion/settings/form.py
    - companion/settings/form_post.py
    - companion/settings/theme.py
    - companion/settings/runway_led.py
    - companion/settings/quiet_hours.py
    - companion/settings/wake_interval.py
    - companion/settings/notifications.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/pages/config_page.py
    - companion/ui_time.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/calendar_group.py
    - companion/i18n_fr/notifications.py
    - companion/i18n_fr/rules.py
    - companion/test_i18n.py
    - companion/test_config_page_02.py
    - companion/test_config_page_04b.py
    - companion/test_config_page_05.py

key-decisions:
  - "Task 1 converted only the 47 of display.py's 105 entries its own six modules (form.py, form_post.py, theme.py, runway_led.py, quiet_hours.py, wake_interval.py) could declare, plus 7 more already safely registered by an earlier plan's always-imported module (ui_base.py's display.on/off/on_to and display.applies_the_next_time_the_frame_wakes_up, flash.py's display.poll_triggered_recently_try_again_in_n_s, history_page.py's display.callsign, airlines_page.py's display.delete) — verified against the real REGISTRY via `import companion.app` before trusting it, not assumed. The other 51 entries stayed legacy CATALOG through Task 1's own commit, converted only once Task 2 declared their call sites"
  - "companion/ui_time.py's four duration-ladder wordings (DURATION_SECONDS_TEXT/_MINUTES_TEXT/_HOURS_TEXT/_DAYS_TEXT, read only by quiet_hours.py's live readout) were declared as Messages even though ui_time.py sits outside this plan's own files_modified list — the only way to finish migrating quiet_hours.py's own call site, since the constants' declaring module and their one reader are different files"
  - "Shared per-theme/per-runway/per-screen label lookups (companion/settings/theme.py's _theme_label_message()/_THEME_LABEL_MESSAGES, runway_led.py's own _RUNWAY_LABEL_MESSAGES, config_page.py's _SCREEN_LABEL_MESSAGES) wrap server.device_config.theme_label()/runway_label() and companion.screens.py's screen-label lookups at their display sites, following history_page.py's own established _RUNWAY_LABEL_MESSAGES pattern from 40-13. companion/i18n_fr/registry.py itself is untouched (not in this plan's own file scope, matching its own docstring's explicit deferral) — its eighteen theme names and one screen-label entry stay legacy CATALOG, resolved by the newly-declared Messages' legacy-CATALOG fallback"
  - "'Theme' (nav.theme) and 'Runway'/'Selected' (display.runway/display.selected) are redeclared with the SAME (id, English) pair at their settings-module call sites, rather than imported from ui_nav.py/history_page.py's own private constants — msg() is idempotent for a repeat declaration, and a settings module importing a page module's private name would be worse coupling than a one-line redeclaration"
  - "One brand-new id, display.next_wake_approx, for config_page.py's NEXT_WAKE_HEADER_VALUE_TEMPLATE ('≈ %s') — this string was never in display.py's own CATALOG to begin with (a pre-existing, out-of-scope gap: it never translated even before this migration), and test-support/i18n_ids.slug_for() reduces the two-character '≈ %s' to an empty slug, so no derived id was possible. Declared with no MESSAGES/BY_ID entry, exactly preserving its pre-migration always-English rendering"

patterns-established:
  - "Mid-plan catalogue partial-conversion: when a plan's own tasks split a settings area's call sites across two commits, the shared catalogue module the Task N+1 files will finish converting stays a real mid-migration CATALOG+MESSAGES split at the end of Task N's own commit — verified by running that task's full verify command (including the render-baseline test) before committing, not assumed safe from the acceptance criteria's residual-entries allowance alone"

requirements-completed: [CMP-09]

# Metrics
duration: unknown (long single session)
completed: 2026-09-27
---

# Phase 40 Plan 14: Stable message IDs (i18n, part 3 of 4) Summary

**Migrated `companion/pages/config_page.py` and every `companion/settings/*.py` module onto `companion.i18n.Message` stable ids across two tasks, converting the display, calendar_group, notifications and rules French catalogues to ID-keyed `MESSAGES` (101/105, 11/11, 13/13 and 11/11 entries respectively) while keeping every intermediate and final render byte-identical to the pre-migration baseline.**

## Performance

- **Duration:** unknown — long single session, no reliable start timestamp
- **Completed:** 2026-09-27
- **Tasks:** 2/2
- **Files modified:** 19 (12 in Task 1 including 4 test-file Rule-1 fixes, 9 in Task 2 including 1 test-file Rule-1 fix, `companion/test_i18n.py` touched in both)

## Accomplishments

- `companion/settings/form.py`, `form_post.py`, `theme.py`, `runway_led.py`, `quiet_hours.py`, `wake_interval.py` (Task 1) and `notifications.py`, `calendar.py`, `rules.py`, `companion/pages/config_page.py` (Task 2): every module constant and every inline `i18n.t("literal")` call site hoisted to a named `i18n.msg(id, english)` Message
- `companion/i18n_fr/display.py` (105 entries), `calendar_group.py` (11), `notifications.py` (13), `rules.py` (11) converted from `CATALOG` to ID-keyed `MESSAGES` — display.py ends at 101/105 (the 4 residual entries are permanently unreachable dead literals, not a future-plan TODO; see Decisions), the other three fully convert with zero residual `CATALOG`
- Shared theme/runway/screen-label lookups (`_theme_label_message()`, `_RUNWAY_LABEL_MESSAGES`, `_SCREEN_LABEL_MESSAGES`) declare the Messages `companion/i18n_fr/registry.py`'s own still-legacy 19-entry `CATALOG` will resolve through, following 40-13's own `history_page.py` precedent
- Every cross-area id 40-12/40-13 already assumed for a display.py/rules.py string this plan's catalogues own (`display.delete`, `display.runway`, `display.callsign`, `rules.flight`, `rules.aircraft`, plus `nav.theme`, `display.on`/`off`/`on_to`, `display.applies_the_next_time_the_frame_wakes_up`, `display.poll_triggered_recently_try_again_in_n_s`) derived the identical id via `test-support/i18n_ids.slug_for()` and redeclared idempotently — never a second id for the same English text
- `companion/ui_time.py`'s four duration-ladder wordings declared as Messages, outside this plan's own file list but required to finish migrating `quiet_hours.py`'s own call site
- Full test suite green: 1877 passed, 3 skipped (pre-existing root-euid skips, unrelated) after both tasks; `test_render_baseline.py` (byte-identical HTML in both languages, every page) passes after each task's own commit
- The one pre-existing, out-of-scope `server.poll_loop`/browser-test failure logged in `deferred-items.md` by 40-13 no longer reproduces (fixed upstream by the standalone `6264c71` commit before this plan started, per the coordination note)

## Task Commits

1. **Task 1: Theme, runway/LED, quiet hours, wake, form helpers and the display catalogue** - `cc2142f` (refactor)
2. **Task 2: Notifications, calendar, rules, config_page and their catalogues** - `73712d9` (refactor)

**Plan metadata:** _pending — this commit_

## Files Created/Modified

- `companion/settings/form.py` - `CURRENT_BADGE_LABEL`, `CALENDAR_HOW_IT_WORKS_SUMMARY`, `NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE` declared as Messages; new shared `SELECTED_LABEL` constant added for theme.py/runway_led.py's three duplicate "Selected" call sites
- `companion/settings/form_post.py` - the five `ERROR_*` validation-message constants declared as Messages
- `companion/settings/theme.py` - every module constant declared as a Message; new `_THEME_LABEL_MESSAGES`/`_theme_label_message()` wrapping `device_config.theme_label()`'s registry text, reused by calendar.py/rules.py
- `companion/settings/runway_led.py` - every module constant declared as a Message; new `_RUNWAY_LABEL_MESSAGES` (same ids as `history_page.py`'s own table) and `RUNWAY_HEADING_TEXT` replacing two inline `i18n.t("Runway")` calls
- `companion/settings/quiet_hours.py` - every module constant declared as a Message; new `QUIET_HOURS_START_FIELD_LABEL`/`QUIET_HOURS_END_FIELD_LABEL` replacing inline `i18n.t("Start")`/`i18n.t("End")` calls
- `companion/settings/wake_interval.py` - every module constant declared as a Message; new `WAKE_INTERVAL_INPUT_LABEL` replacing an inline `i18n.t("Wake interval (seconds)")` call
- `companion/settings/notifications.py` - every module constant declared as a Message (`ERROR_NOTIFICATIONS_URL_TOO_LONG` reuses display.py's `display.that_link_is_too_long`)
- `companion/settings/calendar.py` - every module constant declared as a Message; the four confirmation-page strings and the URL field label/hint reuse display.py ids; `_theme_label_message()` imported from theme.py replacing an inline `device_config.theme_label()` call
- `companion/settings/rules.py` - every module constant declared as a Message; new `POLL_TRIGGER_BUTTON_TEXT`/`RULE_THEME_FIELD_LABEL` replacing inline `i18n.t("Trigger poll now")`/`i18n.t("Theme")` calls; `_theme_label_message()` imported from theme.py
- `companion/pages/config_page.py` - every module constant declared as a Message, including `DISPLAY_PAGE_TITLE`/`DEVICE_PAGE_TITLE` (redeclaring ui_base.py's own `nav.display`/`nav.device` ids) and new `_SCREEN_LABEL_MESSAGES`, `SCOPE_ALL_PAGE_TITLE`, `SAVE_BUTTON_TEXT`, `CANCEL_BUTTON_TEXT` replacing inline literals; new `display.next_wake_approx` id for a template with no prior catalogue entry
- `companion/ui_time.py` - `DURATION_SECONDS_TEXT`/`_MINUTES_TEXT`/`_HOURS_TEXT`/`_DAYS_TEXT` declared as Messages (`display.s`/`m`/`h`/`d`)
- `companion/i18n_fr/display.py` - converted in two steps: Task 1 left 51/105 entries as legacy `CATALOG` (Task 2's own territory) and migrated 54 to `MESSAGES`; Task 2 finished 47 more (101/105 total), leaving 4 permanently-dead literals in `CATALOG`
- `companion/i18n_fr/calendar_group.py`, `notifications.py`, `rules.py` - fully migrated to `MESSAGES` via the AST byte-span codemod, every French value verified byte-for-byte against the pre-migration catalogue
- `companion/test_i18n.py` - four fixtures moved off now-migrated strings ("Cancel"→"Plane frame", "Settings"→"White") onto strings that stay legacy `CATALOG` through this entire plan; `_UNCHANGED_IN_FRENCH` cognate allowlist updated for `display.aspect` and `notifications.notifications`
- `companion/test_config_page_02.py`, `test_config_page_05.py` - two tests reaching `i18n_fr.CATALOG.get()` directly for a now-migrated Message switched to `i18n.t_lang()`
- `companion/test_config_page_04b.py` - the display.py catalogue-completeness test guarded with `getattr(..., "CATALOG"/"MESSAGES", {})` plus a `BY_ID` counterpart

## Decisions Made

- **Task 1/Task 2 split respected display.py's own catalogue, not just the settings modules' file boundary.** Converting an entry to `MESSAGES` before its declaring call site exists breaks `t()`'s fallback (a plain-English lookup no longer finds it in `CATALOG`, and nothing has registered the id in `REGISTRY` yet) — discovered live when Task 1's first full `display.py` conversion attempt failed `test_render_baseline.py` on the Device page. Fixed by computing exactly which of the 105 entries each Task 1 module's own `i18n.msg()` declarations already covered (47), checking which of the remaining 58 were *already* resolvable via an earlier plan's always-imported module (7 more, verified against the live `i18n.REGISTRY` after `import companion.app`), and reverting the other 51 to legacy `CATALOG` for Task 1's own commit.
- **Four `display.py` entries (`Switch on`/`Switch off`/`Turn on`/`Turn off`) never converted.** `companion/ui_base.py`'s own `QUICK_ACTION_SWITCH_ON_BUTTON`/`_OFF_BUTTON`/`QUICK_ACTION_QUIET_TURN_ON_BUTTON`/`_OFF_BUTTON` documents these as retired action wordings kept only as plain-str names a test asserts are no longer rendered — no `i18n.t()` call site exists anywhere for them, so there is nowhere to declare a Message. Left in `display.py`'s `CATALOG` rather than deleted, in case a future UI reintroduces one of these actions.
- **`registry.py` itself stays untouched**, per its own docstring's explicit deferral and this plan's `<interfaces>` note ("registry [catalogue is 40-13's]" — 40-13's actual own summary instead deferred it here or to 40-15; declaring the display-site Messages without touching the catalogue module keeps this plan inside its own declared `files_modified`).
- **`display.next_wake_approx` is a genuinely new id**, not a migration of an existing catalogue entry — `config_page.py`'s `NEXT_WAKE_HEADER_VALUE_TEMPLATE` ("≈ %s") was never translatable before this plan (absent from `display.py`'s pre-migration `CATALOG`), so registering it with no `MESSAGES`/`BY_ID` entry exactly preserves its always-English rendering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `companion/ui_time.py` needed its own Message declarations to finish migrating `quiet_hours.py`**
- **Found during:** Task 1, converting `quiet_hours.py`'s live-duration-readout call site
- **Issue:** `quiet_hours.py`'s `_QUIET_DIAL_DURATION_TEXTS` tuple reads `layout.DURATION_SECONDS_TEXT`/`_MINUTES_TEXT`/`_HOURS_TEXT`/`_DAYS_TEXT`, plain `str` constants declared in `companion/ui_time.py` (not this plan's file list) and re-exported through `companion/layout.py`. Converting `quiet_hours.py`'s own call site to a Message without also converting the constant's declaring module would leave a `str`-not-`Message` argument reaching `i18n.t()`.
- **Fix:** Declared the four constants as Messages (`display.s`/`m`/`h`/`d`) in `ui_time.py` — the only consumer calling `i18n.t()` on them is `quiet_hours.py` (confirmed via grep), so this was safe and necessary.
- **Files modified:** companion/ui_time.py
- **Verification:** Task 1's full verify suite green; `test_render_baseline.py` passes
- **Committed in:** cc2142f (Task 1 commit)

**2. [Rule 1 - Bug] Four `test_i18n.py` fixtures/allowlist entries broke as `display.py`/`notifications.py` migrated**
- **Found during:** Task 1 and Task 2's own verify steps
- **Issue:** `test_t_lang_fr_translates_a_known_key`/`test_t_lang_en_returns_the_english_source`/`test_t_follows_set_request_prefs_and_back`/`test_t_lang_plain_str_still_translates_through_the_legacy_catalog` used "Cancel" (display.py, previously legacy) as a dependency-free translatable fixture; `test_t_lang_message_with_no_by_id_entry_falls_back_to_legacy_catalog` used "Settings" (display.py) for the same reason. Both fully migrated during this plan's own two tasks. Separately, `_UNCHANGED_IN_FRENCH`'s "Aspect"/"Notifications" English-keyed cognate entries broke once `display.py`/`notifications.py` migrated those specific strings to ids.
- **Fix:** Moved the "Cancel"/"Settings" fixtures to "Plane frame"/"White" (both `companion/i18n_fr/registry.py`, still fully legacy since registry.py is out of this plan's own scope); replaced "Aspect"/"Notifications" with `display.aspect`/`notifications.notifications` in the allowlist.
- **Files modified:** companion/test_i18n.py
- **Verification:** full suite green after each fix
- **Committed in:** cc2142f (Task 1), 73712d9 (Task 2)

**3. [Rule 1 - Bug] Three tests reached `i18n_fr.display.CATALOG`/`i18n_fr.CATALOG` directly for a now-migrated entry**
- **Found during:** Task 1's own verify step
- **Issue:** `test_config_page_02.py`'s handle-accessible-name check and `test_config_page_05.py`'s wake-battery-template check both looked up a Message's French sibling via `i18n_fr.CATALOG.get(label)`/`assert template in i18n_fr.CATALOG`, which no longer finds a migrated entry. `test_config_page_04b.py`'s `test_every_display_catalogue_key_is_a_key_of_the_merged_catalog` accessed `i18n_fr_display.CATALOG` directly, assuming it was always fully populated.
- **Fix:** Switched the first two to `i18n.t_lang(label/template, "fr")`, the real translation path; guarded the third with `getattr(..., "CATALOG"/"MESSAGES", {})` plus a `BY_ID` counterpart, matching 40-12/40-13's own precedent for this exact failure shape.
- **Files modified:** companion/test_config_page_02.py, companion/test_config_page_05.py, companion/test_config_page_04b.py
- **Verification:** full Task 1 verify suite green (198 passed)
- **Committed in:** cc2142f (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 3 blocking-issue fix, 2 Rule 1 bugs — all directly caused by this plan's own migration, none out of scope)
**Impact on plan:** All three were necessary to keep the test suite green and the render byte-identical through the migration; none changed rendered output or scope beyond fixing what the migration itself required or broke.

## Issues Encountered

None beyond the deviations above. No new pre-existing/out-of-scope failures found (the one 40-13 had logged in `deferred-items.md` no longer reproduces, fixed upstream before this plan started).

## Known Cross-Area IDs (for plan 40-15)

`companion/i18n_fr/registry.py` still exports a legacy `CATALOG` for its eighteen theme-name entries (White/Black/Grey/.../Band Red Field) and its one screen-label entry ("Plane frame"). Every one of their Messages is now declared at a display site this plan owns:

| ID | English | Declared in |
|----|---------|-------------|
| `registry.white` … `registry.band_red_field` (18 ids) | theme names | companion/settings/theme.py's `_THEME_LABEL_MESSAGES` |
| `registry.runway_3_07_25`/`_4_06_24`/`_2_02_20` | runway labels | companion/settings/runway_led.py's `_RUNWAY_LABEL_MESSAGES` (same ids history_page.py already declared, 40-13) |
| `registry.plane_frame` | "Plane frame" | companion/pages/config_page.py's `_SCREEN_LABEL_MESSAGES` |

Plan 40-15 (or whichever plan finishes `registry.py`) can convert its `CATALOG` to `MESSAGES` directly using these ids — no new id derivation needed, and no other module needs touching. 40-15 also removes both legacy fallbacks (plain str → `TypeError`; Message-with-no-`BY_ID` → fails the completeness test) once `registry.py`'s conversion and `display.py`'s four permanently-dead entries are resolved (the dead entries can either stay as a documented, permanent exception, or be deleted outright if 40-15 also removes the underlying dead constants from `ui_base.py`).

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The settings area (Display and Device pages) is fully migrated onto stable message ids, joining Home/Flights/Airlines/Health (40-13) and every shared module (40-12).
- Only `companion/i18n_fr/registry.py`'s 19-entry residual `CATALOG` and `display.py`'s 4 permanently-dead entries remain anywhere in the whole `i18n_fr` package — both fully scoped and low-risk for 40-15.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 19 files listed under Files Created/Modified confirmed present on disk; both task
commits (cc2142f, 73712d9) confirmed in `git log`.
