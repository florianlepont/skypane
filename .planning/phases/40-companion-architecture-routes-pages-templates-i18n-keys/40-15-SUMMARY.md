---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 15
subsystem: i18n
tags: [i18n, translation, python, stdlib]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: companion.i18n.Message/msg()/REGISTRY, companion.i18n_fr.BY_ID, every catalogue module migrated except registry.py's 19-entry residual CATALOG and display.py's 4 dead entries (40-12/13/14)
provides:
  - companion.i18n_fr.registry.py fully converted to MESSAGES (its 19 residual entries — 18 theme names + the screen label)
  - companion/i18n_fr/display.py's 4 permanently-dead action-wording entries deleted (no call site anywhere)
  - Both legacy fallbacks removed from companion/i18n.py and the CATALOG merge removed from companion/i18n_fr/__init__.py — t()/t_lang() now raise TypeError on any non-Message argument
  - companion/test_i18n.py rewritten around the runtime REGISTRY/BY_ID objects — completeness (no missing/orphan id), stable-shape, rewording-keeps-french, and plain-string-refused tests, plus a self-consistency sweep
  - Every companion test call site converted from a plain-string i18n.t()/t_lang() argument to the production Message constant it stood for
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "t()/t_lang() validate their argument's type FIRST (isinstance(text, Message)), before touching prefs.current_lang() or lang — so a TypeError fires regardless of which language branch would have run"
    - "A completeness test that needs REGISTRY/BY_ID fully populated imports every companion production module once via pkgutil.walk_packages(companion.__path__, prefix='companion.'), skipping test_*/conftest names, wired as a session-scoped autouse fixture so every other test in the file benefits without re-importing"
    - "A registry-label lookup that defends against an unrecognised id (e.g. _RUNWAY_LABEL_MESSAGES.get(label, label), _THEME_LABEL_MESSAGES.get(label, label)) must check membership explicitly (message = TABLE.get(key); i18n.t(message) if message is not None else key) rather than defaulting .get()'s fallback to the raw key — a dict .get(key, key) default is never a Message, so passing it straight to i18n.t() is exactly the case the removed legacy fallback used to paper over"
    - "A test that supplies a config_page.render()/settings-group errors={} dict is exercising the SAME i18n.t() call site companion/settings/form.py's _field_error_html() uses in production — its error text must be a real form_post.ERROR_* Message, not an arbitrary literal, once the legacy fallback is gone"

key-files:
  created: []
  modified:
    - companion/i18n.py
    - companion/i18n_fr/__init__.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/health.py
    - companion/i18n_fr/registry.py
    - companion/pages/airlines_page.py
    - companion/pages/config_page.py
    - companion/pages/health_page.py
    - companion/pages/history_page.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/settings/runway_led.py
    - companion/settings/theme.py
    - companion/test_i18n.py
    - companion/theme_preview.py
    - companion/ui_nav.py
    - companion/test_companion_app_04.py
    - companion/test_companion_app_05.py
    - companion/test_config_page_01.py
    - companion/test_config_page_02.py
    - companion/test_config_page_03.py
    - companion/test_config_page_05.py
    - companion/test_status_pages_03.py
    - companion/test_status_pages_07.py
    - companion/test_view_pages_03.py

key-decisions:
  - "registry.py's 18 theme-name ids and its 1 screen-label id convert to MESSAGES using EXACTLY the ids 40-14 already assigned at their display sites (companion/settings/theme.py's _THEME_LABEL_MESSAGES, config_page.py's _SCREEN_LABEL_MESSAGES) — no new id derivation needed, matching 40-14's own closing note"
  - "display.py's 4 dead entries (Switch on/off, Turn on/off) are DELETED, not preserved as a documented residual — ui_base.py's own QUICK_ACTION_SWITCH_*/QUICK_ACTION_QUIET_TURN_* constants (out of this plan's file scope) reach no i18n.t() call site anywhere, so there is nowhere to declare a Message for them; re-introducing one of these actions means a fresh msg() declaration and a fresh MESSAGES entry, not restoring these"
  - "Two genuinely untranslated strings (display.next_wake_approx's '≈ %s' symbolic template, and a newly-hoisted theme-preview alt-text template) get a French BY_ID entry IDENTICAL to their English source, added to test_i18n.py's _UNCHANGED_IN_FRENCH cognate list, rather than a real French translation — this satisfies the completeness must-have (every id has both an English text and a French translation) while keeping test_render_baseline.py's byte-identical guarantee intact; a real French alt text is a follow-up, not a rendered-output change this refactor-only migration may make"
  - "history_page.py's _confirmed_state_label()/_corroboration_title_text() and three registry-label lookups (theme.py's _theme_label_message(), runway_led.py's render call, rules.py's _rule_kind_label_text()) all had a `.get(key, key)`/`.get(key, DEFAULT_TEXT['warn'])`-then-i18n.t() shape where the miss branch fell back to a raw, non-Message string — every one rewritten to check membership explicitly and skip i18n.t() entirely on the raw-fallback branch, since that branch's text was never in any catalogue to begin with"
  - "config_page.py's _SCREEN_LABEL_MESSAGES.get(raw_label, raw_label) and airlines_page.py's always-empty LIGHTBOX_NOTE, and ui_nav.py's always-empty NAV_GROUPS heading label, are the same class of bug: a value that could reach i18n.t() without ever being a Message. Fixed the same way (skip translation when there is no Message to translate)"
  - "health_page.py's inline i18n.t('This appears once the frame has recorded at least one flight.') literal (missed by 40-13's own migration) is hoisted to a proper _APPEARS_ONCE_RECORDED_TEXT Message using the id (health.this_appears_once_the_frame_has_recorded_at) 40-13's French catalogue had already assigned it — the orphan BY_ID entry test_every_message_id_has_english_and_french's completeness check caught is now a real, declared id"
  - "Test-authored errors={'field': 'literal text'} fixtures across test_config_page_02/03/05.py are replaced with the real companion.settings.form_post.ERROR_* Message constants — companion/settings/form.py's _field_error_html() calls i18n.t() on whatever a caller puts in the errors dict, so a test-authored plain string hits the exact same strict-Message enforcement production code does"

patterns-established:
  - "A dict-lookup-with-fallback-to-the-raw-key pattern (`TABLE.get(key, key)`) is a latent i18n bug the moment its result reaches i18n.t()/t_lang() — the fallback branch is, by construction, never a registered Message. Once t()/t_lang() are Message-only, every such site must split into 'look the Message up, translate only if found' rather than defaulting the lookup itself"

requirements-completed: [CMP-09]

# Metrics
duration: unknown (single session, no reliable start timestamp captured)
completed: 2026-09-27
---

# Phase 40 Plan 15: Stable message IDs (i18n, part 4 of 4) Summary

**Finished the CMP-09 migration by converting `i18n_fr/registry.py`'s last 19 legacy entries to stable ids, deleting `display.py`'s 4 dead entries, removing both legacy-catalogue fallbacks from `companion/i18n.py`/`i18n_fr/__init__.py` so `t()`/`t_lang()` now raise `TypeError` on any non-Message argument, and fixing every real call site — production and test — that strict enforcement exposed.**

## Performance

- **Duration:** unknown — single session, no reliable start timestamp captured
- **Completed:** 2026-09-27
- **Tasks:** 2/2
- **Files modified:** 25 (16 in Task 1 including 10 Rule-1 production-bug fixes beyond the plan's own `<files>` list, 9 in Task 2 including 1 test file outside the plan's own list)

## Accomplishments

- `companion/i18n_fr/registry.py` fully converted to `MESSAGES` (18 theme names + 1 screen label), using exactly the ids 40-13/40-14 already assigned at their display sites — zero residual `CATALOG` left anywhere in `companion/i18n_fr/`
- `companion/i18n_fr/display.py`'s 4 permanently-dead entries (`Switch on`/`Switch off`/`Turn on`/`Turn off`) deleted outright, since no call site anywhere declares a Message for them
- `companion/i18n.py`: `_derived_english_to_french()` and both legacy-`CATALOG` fallbacks removed; `t()`/`t_lang()` now call `_require_message()` first and raise `TypeError("i18n.t() takes a Message declared with i18n.msg(), got <type>: <value!r>")` for any non-Message argument, in either language branch
- `companion/i18n_fr/__init__.py`: the `CATALOG` merge removed entirely — the package now builds and exports only `BY_ID`
- `companion/test_i18n.py` rewritten around the runtime objects: `test_every_message_id_has_english_and_french` (completeness, naming missing/orphan ids separately), `test_every_message_id_has_the_stable_shape`, `test_rewording_the_english_keeps_the_french`, `test_plain_strings_are_refused`, and a self-consistency sweep over every `(REGISTRY[id], BY_ID[id])` pair — all gated behind a session-scoped autouse fixture that imports every companion production module via `pkgutil.walk_packages()` first, so `REGISTRY`/`BY_ID` are fully populated before any test body runs
- Ten real production call sites fixed, all direct casualties of the stricter enforcement (see Deviations): an inline un-hoisted literal in `health_page.py`, an always-empty `LIGHTBOX_NOTE` in `airlines_page.py`, an always-empty nav-group heading in `ui_nav.py`, a plain-str theme-preview alt template in `theme_preview.py`, a bare `"%s — %s"` join in `health_page.py`, and five "translate unless the id is unrecognised" registry-label lookups (`history_page.py`'s runway label, `theme.py`'s theme label, `runway_led.py`'s render call, `rules.py`'s rule-kind label, `config_page.py`'s screen caption)
- Every test call site across 9 test files converted from a plain-string `i18n.t()`/`t_lang()` argument (or a test-authored `errors={...}` literal reaching the same production call site) to the real Message constant, including `test_companion_app_04.py` — outside this plan's own file list but broken by the same enforcement
- `test_status_pages_07.py`'s "Open menu" check (proving a retired translation was deleted, not superseded) rewritten to assert `TypeError`, since the plain-string degrade-to-English path it exercised no longer exists
- Full suite green with `SKYPANE_REQUIRE_BROWSER=1`: 1874 passed, 3 skipped (pre-existing root/euid skips); `ruff check companion` and `scripts/check_comment_history.py check` both clean
- Mutation check performed live (not committed): deleting `i18n_fr.BY_ID["nav.home"]` makes `test_every_message_id_has_english_and_french` fail, naming `nav.home` explicitly

## Task Commits

1. **Task 1: Strict ID-only lookup and the completeness tests** - `c193774` (feat)
2. **Task 2: Move test call sites onto Message constants** - `6ff628e` (test)

**Plan metadata:** _pending — this commit_

## Files Created/Modified

- `companion/i18n.py` - both legacy fallbacks removed; `_require_message()` enforces Message-only, raising the exact `TypeError` text the plan's acceptance criteria specify
- `companion/i18n_fr/__init__.py` - `CATALOG` merge removed; package now builds/exports `BY_ID` only
- `companion/i18n_fr/registry.py` - fully converted to `MESSAGES` (19 entries: 18 theme names, 1 screen label), joining its pre-existing 3 runway-label `MESSAGES`
- `companion/i18n_fr/display.py` - the 4 dead `CATALOG` entries deleted; docstring updated to record why
- `companion/i18n_fr/health.py` - two new entries: `health.this_appears_once_the_frame_has_recorded_at` (a real translation, for a hoisted literal) and `health.day_dash_verdict` (identical-to-English, a punctuation-only template)
- `companion/pages/health_page.py` - `_APPEARS_ONCE_RECORDED_TEXT` Message added and used in place of an inline literal; `CHECK_IN_CELL_TITLE_NONE` hoisted from a plain str to a Message
- `companion/pages/airlines_page.py` - `LIGHTBOX_NOTE` (always `""`) no longer passed to `i18n.t()`
- `companion/pages/history_page.py` - `_confirmed_state_label()`, `_corroboration_title_text()` (new helper replacing an inline `.get(..., "")` + `i18n.t()`), and `_runway_label()` all skip translation on their raw-fallback branch
- `companion/pages/config_page.py` - `_screen_caption_html()`'s screen-label lookup skips translation when the raw label is unrecognised
- `companion/theme_preview.py` - `THEME_PREVIEW_ALT_TEMPLATE` hoisted from a plain str to `i18n.msg("display.sample_panel_rendered_in_the_theme", ...)`
- `companion/ui_nav.py` - `_nav_groups()` skips `i18n.t()` for the empty-string "no heading" sentinel
- `companion/settings/theme.py` - `_theme_label_message()` now returns already-translated text (or the raw fallback), so its 7 call sites no longer wrap it in `i18n.t()`
- `companion/settings/calendar.py`, `companion/settings/rules.py` - their own `_theme_label_message(...)` call sites un-wrapped to match; `rules.py` also gains `_rule_kind_label_text()` for `RULE_KIND_LABELS`' raw-fallback branch
- `companion/settings/runway_led.py` - its runway-label render call skips translation on an unrecognised label
- `companion/test_i18n.py` - rewritten: completeness/shape/rewording/plain-string-refused tests, a `pkgutil.walk_packages()`-based session-scoped import fixture, and the self-consistency sweep switched from `i18n_fr.CATALOG` to `(REGISTRY, BY_ID)` pairs
- `companion/test_companion_app_04.py` - "Show password"/"Hide password" fixture switched to `login_page.LOGIN_REVEAL_SHOW_LABEL`/`_HIDE_LABEL`
- `companion/test_companion_app_05.py` - the flash/title/nav/theme round-trip tests switched to `login_page._NOT_FOUND_TAB_TITLE_TEXT`, `ui_shell._LOGIN_TITLE_TEXT`, `ui_nav._PRIMARY_NAVIGATION_TEXT`, `ui_nav._THEME_LABEL_TEXT[...]`
- `companion/test_config_page_01.py`, `test_config_page_03.py` - `device_config.theme_label(...)` no longer wrapped in `i18n.t()` (the assertion only ever checked the English render)
- `companion/test_config_page_02.py`, `test_config_page_03.py`, `test_config_page_05.py` - literal `errors={"field": "some text"}` fixtures switched to `form_post.ERROR_*` Message constants
- `companion/test_status_pages_03.py` - "Flight data is stale."/"More details"/"Last 3 months, daily average"/"Latest %d readings" literals switched to `health_signals`/`health_page`'s own Message constants
- `companion/test_status_pages_07.py` - the "Open menu" degrade-to-English check rewritten as a `pytest.raises(TypeError)` assertion
- `companion/test_view_pages_03.py` - `"Today"` literal switched to `history_page._DAY_TODAY_LABEL`

## Decisions Made

See `key-decisions` in the frontmatter above for the full list. In short: registry.py's residual entries convert onto 40-14's already-assigned ids with no new derivation; display.py's 4 dead entries are deleted, not preserved; two genuinely-never-translated strings get an identical-to-English BY_ID entry (cognate-listed) rather than real French, to satisfy completeness without changing rendered output; every `.get(key, key)`-then-`i18n.t()` shape is rewritten to check membership first and skip translation on the raw-fallback branch; and test-authored `errors={}` literals are replaced with real `form_post.ERROR_*` Messages since `_field_error_html()` enforces the same contract in production.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ui_nav.py`'s `_nav_groups()` called `i18n.t()` on the empty-string "no heading" sentinel**
- **Found during:** Task 1's own verify step (`test_i18n.py`'s French page-render checks)
- **Issue:** `NAV_GROUPS`'s first entry uses `""` as a "no heading" sentinel, never a Message; `i18n.t("")` now raises `TypeError` on every page render.
- **Fix:** Skip `i18n.t()` entirely when `group_label` is falsy.
- **Files modified:** companion/ui_nav.py
- **Verification:** `test_i18n.py`'s French render checks pass
- **Committed in:** c193774 (Task 1 commit)

**2. [Rule 1 - Bug] `companion/theme_preview.py`'s `THEME_PREVIEW_ALT_TEMPLATE` was a plain str, never hoisted**
- **Found during:** Task 1's own verify step
- **Issue:** The Display page's theme chip grid's per-chip alt text was a bare module constant, passed to `i18n.t()` at its call site in `theme.py`.
- **Fix:** Hoisted to `i18n.msg("display.sample_panel_rendered_in_the_theme", ...)`; French BY_ID entry set identical to the English (never translated before this id existed either), cognate-listed in `test_i18n.py`, preserving byte-identical rendered output.
- **Files modified:** companion/theme_preview.py, companion/i18n_fr/display.py, companion/test_i18n.py
- **Verification:** `test_render_baseline.py` passes (byte-identical in both languages)
- **Committed in:** c193774 (Task 1 commit)

**3. [Rule 1 - Bug] `airlines_page.py`'s always-empty `LIGHTBOX_NOTE` reached `i18n.t()`**
- **Found during:** Task 1's own verify step
- **Issue:** `LIGHTBOX_NOTE = ""` is a real, always-present placeholder element (filled client-side by `panel-lookup.js`), passed to `i18n.t()` at its one call site.
- **Fix:** Removed the `i18n.t()` wrapper — `escape_html("")` is already `""`.
- **Files modified:** companion/pages/airlines_page.py
- **Verification:** `test_render_baseline.py` passes
- **Committed in:** c193774 (Task 1 commit)

**4. [Rule 1 - Bug] `health_page.py`'s `CHECK_IN_CELL_TITLE_NONE` was a plain `"%s — %s"` str**
- **Found during:** Task 1's own verify step
- **Issue:** 40-13 deliberately left this bare punctuation-only join as a plain str ("never carried translatable words of its own"), but it still reached `i18n.t()`.
- **Fix:** Hoisted to `i18n.msg("health.day_dash_verdict", "%s — %s")` with an identical French BY_ID entry, cognate-listed.
- **Files modified:** companion/pages/health_page.py, companion/i18n_fr/health.py, companion/test_i18n.py
- **Verification:** `test_render_baseline.py` passes
- **Committed in:** c193774 (Task 1 commit)

**5. [Rule 1 - Bug] `health_page.py`'s corroboration empty state carried an un-hoisted inline literal**
- **Found during:** Task 1's own verify step
- **Issue:** `i18n.t("This appears once the frame has recorded at least one flight.")` — a plain-string literal 40-13's own migration missed. `i18n_fr/health.py`'s French catalogue already carried an orphaned entry for this exact id, discovered independently by the new completeness test.
- **Fix:** Declared `_APPEARS_ONCE_RECORDED_TEXT = i18n.msg("health.this_appears_once_the_frame_has_recorded_at", ...)` (the id the orphaned French entry already used) and used it at the call site.
- **Files modified:** companion/pages/health_page.py
- **Verification:** `test_every_message_id_has_english_and_french` passes with zero orphans; `test_render_baseline.py` passes
- **Committed in:** c193774 (Task 1 commit)

**6. [Rule 1 - Bug] `history_page.py`'s `_confirmed_state_label()` could return a raw, data-dependent fallback string to `i18n.t()`**
- **Found during:** Task 1's own verify step (`test_render_baseline.py`, seeded with an intentionally-unrecognised `confirmed_state` value)
- **Issue:** An unrecognised `confirmed_state` value degrades to a title-cased rendering of the raw value itself (data-dependent, never a fixed catalogue entry) — `i18n.t()` was called on this raw fallback unconditionally.
- **Fix:** `i18n.t()` now runs only inside the recognised-value branch; the raw fallback returns unchanged, exactly as it always rendered pre-migration (never found in any catalogue).
- **Files modified:** companion/pages/history_page.py
- **Verification:** `test_render_baseline.py` passes
- **Committed in:** c193774 (Task 1 commit)

**7. [Rule 1 - Bug] `history_page.py`'s corroboration-tooltip lookup had the same `.get(key, "")`-then-`i18n.t()` shape**
- **Found during:** Task 1's own verify step
- **Issue:** `i18n.t(_CORROBORATION_TITLES.get(row.get("corroborated"), ""))` calls `i18n.t("")` for the True/False states, which need no tooltip.
- **Fix:** New `_corroboration_title_text()` helper checks membership explicitly, translating only when a Message is found.
- **Files modified:** companion/pages/history_page.py
- **Verification:** `test_render_baseline.py` passes
- **Committed in:** c193774 (Task 1 commit)

**8. [Rule 1 - Bug] Five "translate unless the id is unrecognised" registry-label lookups defaulted their `.get()` fallback to the raw key**
- **Found during:** Task 1's own verify step (theme.py's chip-grid render, and static review of the same shape elsewhere)
- **Issue:** `history_page._runway_label()`, `theme._theme_label_message()`, `runway_led.py`'s render call, and `rules.py`'s `RULE_KIND_LABELS.get(kind, kind)` all pass a `.get(key, key)`-style default straight to `i18n.t()`; the default is never a Message.
- **Fix:** Each rewritten to look the Message up, translate only if found, otherwise return the raw key/label unchanged — matching how these unrecognised-value branches always rendered before this migration.
- **Files modified:** companion/pages/history_page.py, companion/settings/theme.py, companion/settings/calendar.py, companion/settings/rules.py, companion/settings/runway_led.py, companion/pages/config_page.py
- **Verification:** `test_render_baseline.py` and the full non-browser suite pass
- **Committed in:** c193774 (Task 1 commit)

**9. [Rule 1 - Bug] `test_companion_app_04.py`, outside this plan's own file list, broke on the same enforcement**
- **Found during:** a full-suite run beyond Task 1's own required verify scope, performed proactively before committing
- **Issue:** `test_login_reveal_toggle_is_server_hidden_and_named` called `i18n_module.t_lang("Show password", "fr")`/`"Hide password"` as plain-string fixtures.
- **Fix:** Switched to `login_page.LOGIN_REVEAL_SHOW_LABEL`/`_HIDE_LABEL`.
- **Files modified:** companion/test_companion_app_04.py
- **Verification:** full suite green
- **Committed in:** 6ff628e (Task 2 commit, bundled since it is the same class of test-call-site fix Task 2 performs)

**10. [Rule 1 - Bug] `companion/settings/form.py`'s `_field_error_html()` enforces the Message contract on whatever a caller's `errors` dict holds**
- **Found during:** the full-suite run after Task 1's commit
- **Issue:** Several tests (`test_config_page_02/03/05.py`) supplied `errors={"field": "some literal text"}` fixtures standing in for "some error message" — production error messages are always `form_post.ERROR_*` Messages, so the literal now raises `TypeError` at the exact same call site production code uses.
- **Fix:** Every such fixture switched to the real `form_post.ERROR_*` constant the field's own validator actually raises (`ERROR_QUIET_HOURS_TIME_SHAPE`, `ERROR_WAKE_INTERVAL_RANGE`, `ERROR_CALENDAR_URL_INVALID`, `ERROR_UNEXPECTED_SWITCH_VALUE`); assertions checking for the literal text switched to check for the Message's own English text instead.
- **Files modified:** companion/test_config_page_02.py, companion/test_config_page_03.py, companion/test_config_page_05.py
- **Verification:** full suite green
- **Committed in:** 6ff628e (Task 2 commit)

---

**Total deviations:** 10 auto-fixed (all Rule 1 — bugs directly caused by this plan's own stricter enforcement, none out of scope)
**Impact on plan:** All ten were necessary to keep every real page render and the full test suite working under Message-only lookups; none changed rendered output (verified against `test_render_baseline.py` after every fix) beyond the two identical-to-English cognate additions, which by construction render nothing differently.

## Issues Encountered

- Two silent Unicode corruptions were caught and fixed during Task 1's own verify loop: a needle in the newly-written `test_i18n.py` ("Déconnecter le calendrier ?") lost its non-breaking space when re-typed through the Write tool, exactly the failure mode 40-13's SUMMARY had already flagged as a known risk for hand-retyped French text — fixed with a byte-level Python replace rather than another manual edit, and verified byte-for-byte against `git show HEAD:companion/test_i18n.py`.
- The completeness test's design (importing every production module before checking `REGISTRY`/`BY_ID`) surfaced one genuine orphan (`health.this_appears_once_the_frame_has_recorded_at`, an inline literal 40-13 missed) and one genuine gap (`display.next_wake_approx`, a Message with deliberately no BY_ID entry per 40-14) on its very first run — both resolved as documented above, proving the test does what it claims before any mutation test was needed.

## Known Cross-Area IDs

None — this was the last plan in the CMP-09 migration; no ids remain deferred to a future plan.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CMP-09 is complete: every `companion/i18n_fr/` module exports only `MESSAGES`; `companion/i18n.py`'s `t()`/`t_lang()` accept only a `Message` and raise `TypeError` otherwise; `test_i18n.py` proves completeness (no missing/orphan id), stable shape, and that rewording an English string cannot drop its French translation.
- The full suite (1874 tests, browser included via `SKYPANE_REQUIRE_BROWSER=1`) is green; `ruff check companion` and the comment-history guard are both clean.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 25 files listed under Files Created/Modified confirmed present on disk; both task
commits (c193774, 6ff628e) confirmed in `git log`.
