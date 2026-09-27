---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 12
subsystem: i18n
tags: [i18n, translation, python, stdlib]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: typed PageContext, split ui_base/ui_time/ui_nav/ui_components/ui_shell modules (40-11 and earlier)
provides:
  - companion.i18n.Message/msg()/REGISTRY — the stable message-ID mechanism
  - companion.i18n_fr.BY_ID — the ID-keyed French catalogue, merged alongside the legacy CATALOG
  - test-support/i18n_ids.py — the shared English-to-slug rule for plans 40-13/40-14
  - Fully ID-migrated common.py and nav.py catalogues; frame_state.py's own 3-entry catalogue migrated
  - Every shared (non-page) module's i18n.t()/t_lang() call sites converted to Message constants
affects: [40-13, 40-14, 40-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Message(str) subclass carrying .msg_id; msg(id, english) registers it in REGISTRY and is idempotent on a repeat (id, english) pair, raises on a reworded duplicate id"
    - "i18n_fr submodule exports MESSAGES (id -> french) alongside or instead of the legacy CATALOG (english -> french); a module may carry both during migration"
    - "t()/t_lang() lookup order for a Message: BY_ID[msg_id] first, then legacy CATALOG by English text, so the source and catalogue halves of one entry can migrate in different plans without breaking a render"
    - "an id assigned to a constant whose catalogue lives in another, not-yet-migrated module still resolves correctly via the same legacy-CATALOG fallback"

key-files:
  created:
    - test-support/i18n_ids.py
    - test-support/test_i18n_ids.py
  modified:
    - companion/i18n.py
    - companion/i18n_fr/__init__.py
    - companion/i18n_fr/common.py
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/frame_state.py
    - companion/ui_base.py
    - companion/ui_time.py
    - companion/ui_nav.py
    - companion/ui_shell.py
    - companion/frame_state.py
    - companion/flash.py
    - companion/login_page.py
    - companion/app.py
    - companion/test_i18n.py
    - companion/test_status_pages_07.py

key-decisions:
  - "ID scheme: '<area>.<slug>', area = the i18n_fr module owning the French text, slug = i18n_ids.slug_for(english) (lowercase, non-[a-z0-9] runs collapse to '_', trailing '_' stripped, truncated to 48 chars at a '_' boundary); collisions append '_2'/'_3' via i18n_ids.ids_for_area()"
  - "A Message declared in a shared module (ui_base.py/ui_nav.py/frame_state.py) whose French lives in another, not-yet-migrated i18n_fr module (health/display/home/notifications) still gets its id now — it resolves through the legacy-CATALOG fallback until that module's own migration plan runs"
  - "common.py and nav.py fully converted to MESSAGES this plan (not partially, as the plan's own wording first suggested) since every one of their entries is consumed by a module this plan touches (ui_base/ui_time/ui_nav/ui_shell in Task 2, app/flash/login_page in Task 3) — there is no leftover page-owned entry to defer"
  - "companion/app.py's _PAGE_TITLES now derives from layout.NAV_TABS instead of re-declaring the same six English titles, so the nav labels' Messages are declared exactly once"
  - "companion/post_actions.py, companion/wake.py and companion/screens.py needed no code change: none of the three ever calls i18n.t()/t_lang() directly; screens.py's one candidate string ('Plane frame') is used only by config_page.py (a page module, 40-13/40-14 territory)"

patterns-established:
  - "Pattern: migration tooling that must be shared across plans and never imported by production code lives in test-support/, not companion/"
  - "Pattern: a catalogue module mid-migration exports both MESSAGES (converted entries) and CATALOG (the rest) simultaneously; _build_catalogs() merges both, raising ValueError on a duplicate key/id across sibling modules exactly as the pre-existing CATALOG merge did"

requirements-completed: [CMP-09]

# Metrics
duration: unknown (resumed after a mid-task container restart; no reliable start timestamp for the full session)
completed: 2026-09-27
---

# Phase 40 Plan 12: Stable message IDs (i18n, part 1 of 4) Summary

**Introduced `companion.i18n.Message`/`msg()`/`REGISTRY` and `companion.i18n_fr.BY_ID`, then migrated every shared (non-page) companion module — shell, nav, time formatting, components, flash, login, app, frame-state — onto ID-keyed translation lookups, with `common.py` and `nav.py` fully converted and `frame_state.py`'s own three-entry catalogue migrated alongside them.**

## Performance

- **Duration:** unknown — a prior attempt at Task 1 was killed mid-task by a container restart; this session resumed from that point (verified the WIP, fixed two comment-history violations, then continued)
- **Completed:** 2026-09-27
- **Tasks:** 3/3
- **Files modified:** 17 (2 created, 15 modified)

## Accomplishments
- `Message(str)` subclass with a stable `.msg_id`; `msg()` registers it in `REGISTRY`, idempotent on a repeat declaration, raising `ValueError` on a reworded duplicate id
- `companion.i18n_fr.BY_ID`, merged from each submodule's `MESSAGES` dict alongside the pre-existing `CATALOG` merge, with the same duplicate-key/id fail-fast
- `t()`/`t_lang()` resolve a Message via `BY_ID` first, falling back to the legacy English-keyed `CATALOG` (directly, or via a `REGISTRY`+`BY_ID`-derived English→French view) — the mechanism that lets a call site and its catalogue migrate in different plans without ever breaking a render
- `test-support/i18n_ids.py`: `slug_for()`/`ids_for_area()`, the one deterministic English-to-slug rule plans 40-12/13/14 share, unit-tested against the plan's own three worked examples plus a collision case
- `common.py` (54 entries) and `nav.py` (21 entries) fully migrated to `MESSAGES` — neither has a legacy `CATALOG` left
- `companion/i18n_fr/frame_state.py`'s own three entries (the held headline, both delay sentences it owns outright) migrated
- Every `i18n.t()`/`i18n.t_lang()` call site across `ui_base.py`, `ui_time.py`, `ui_nav.py`, `ui_shell.py`, `frame_state.py`, `flash.py`, `login_page.py`, `app.py` now passes a Message constant — zero inline string literals remain
- `test_i18n.py`'s self-consistency sweep (non-empty, placeholder parity, no-identical-to-English) now covers migrated `(REGISTRY id, BY_ID translation)` pairs alongside the legacy `CATALOG`, plus a new `t_lang()` round-trip check over every migrated id
- Rendered output stays byte-identical in both languages (`test_render_baseline.py`); full suite green (1738 passed, 3 skipped — pre-existing root/euid skips, unrelated)

## Task Commits

1. **Task 1: Message IDs, registry and ID-keyed lookup** - `708761e` (feat) — resumed from a prior session's uncommitted WIP; verified correct against the task spec, fixed two comment-history violations (a bare plan-id and two "CMP-09" references in comments), then committed
2. **Task 2: Migrate the shell/nav/time/component modules and the common + nav catalogues** - `5cb9fa4` (refactor)
3. **Task 3: Migrate app, flash, login, post actions, frame-state/wake/screens and the frame_state catalogue** - `c9d4c1a` (refactor)

**Plan metadata:** _pending — this commit_

## Files Created/Modified

- `companion/i18n.py` - Message/msg()/REGISTRY, ID-aware t()/t_lang() with the two-level legacy fallback
- `companion/i18n_fr/__init__.py` - merges each submodule's MESSAGES into BY_ID alongside the CATALOG merge
- `companion/i18n_fr/common.py` - fully migrated to MESSAGES (54 entries)
- `companion/i18n_fr/nav.py` - fully migrated to MESSAGES (21 entries)
- `companion/i18n_fr/frame_state.py` - migrated to MESSAGES (3 entries)
- `companion/ui_base.py` - NAV_GROUPS labels, ADVANCED_GROUP_LABEL, NAV_TOGGLE_LABEL, HEALTH_ALERT_SUFFIX_TEXT, QUICK_ACTION_*, the six _FRAME_*_TEXT constants declared as Messages
- `companion/ui_time.py` - the four relative-age wordings, the eight ticker bucket wordings, REFRESH_PILL_TEXT, FRESHNESS_PREFIX_TEXT declared as Messages
- `companion/ui_nav.py` - NAV_SCREEN_*/NAV_QUIET_*/NAV_STATUS_ARIA_LABEL_TEXT/TAB_BAR_MORE_LABEL/REFRESH_PAUSED_TEXT/REFRESH_RECONNECTING_TEXT and every remaining inline literal (Primary navigation, Theme, Language, Sign out, the three theme-picker labels) hoisted to Messages
- `companion/ui_shell.py` - the login `<title>` literal hoisted to a Message
- `companion/frame_state.py` - HEADLINE_DUE/HELD/LATE and DELAY_DUE/HELD/UNKNOWN declared as Messages
- `companion/flash.py` - every FLASH_MESSAGES value declared as a Message
- `companion/login_page.py` - every module constant and remaining inline literal declared as a Message
- `companion/app.py` - _PAGE_TITLES reuses layout.NAV_TABS's own Messages; the login-failure literal hoisted
- `companion/test_i18n.py` - Task 1's unit tests; the self-consistency sweep and round-trip check extended to migrated ids; three test fixture strings moved off "Home" (now migrated) onto "Status" (still legacy)
- `companion/test_status_pages_07.py` - the tab-bar label-width test reads the French label via `i18n.t_lang()` instead of the now-removed `i18n_fr.nav.CATALOG`
- `test-support/i18n_ids.py` (new) - `slug_for()`/`ids_for_area()`, the shared migration codemod rule
- `test-support/test_i18n_ids.py` (new) - unit tests for the slug rule

## Decisions Made

- **ID scheme:** `<area>.<slug>` where `area` is the `i18n_fr` module that owns the French text and `slug` is `i18n_ids.slug_for(english)` — deterministic, so plans 40-13/40-14 converting other areas' catalogues independently arrive at the same id a shared module already assumed. Verified against the plan's own worked examples ("Home" → `nav.home`, "just now" → `health.just_now`, "%s ago" → `health.ago`).
- **A Message can name an id in an area whose catalogue this plan never touches.** `ui_base.py`'s `QUICK_ACTION_SCREEN_LABEL`, for example, is `i18n.msg("health.screen", "Screen")` even though `health.py` stays a legacy `CATALOG` until plan 40-13 — the Message-with-no-`BY_ID`-entry fallback resolves it through that legacy `CATALOG` meanwhile, exactly as the plan's objective describes.
- **`common.py`/`nav.py` converted fully, not partially.** The plan's Task 2 wording anticipated some common/nav entries staying English-keyed as "owned by a page module." In practice every one of their entries is consumed by a module this plan touches directly (Task 2's ui_\*/ui_shell.py, or Task 3's app.py/flash.py/login_page.py) — there was no leftover to defer, so both catalogues ended the plan holding `MESSAGES` only.
- **`_PAGE_TITLES = dict(layout.NAV_TABS)`** rather than re-declaring the same six route→label pairs a second time in `app.py` — avoids a second `msg()` call for an id `ui_base.py` already owns (the plan's own "never declared twice" rule).
- **`post_actions.py`/`wake.py`/`screens.py` needed no change.** None calls `i18n.t()`/`t_lang()` directly; `screens.py`'s `"Plane frame"` label is read only by `config_page.py` (a page module), so it is out of this plan's non-page scope entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two comment-history violations in Task 1's resumed WIP**
- **Found during:** Task 1 (verifying the pre-existing uncommitted work from the interrupted prior session)
- **Issue:** `companion/i18n.py`, `companion/i18n_fr/__init__.py` and `companion/test_i18n.py` carried a bare `plan 40-13` reference and two `CMP-09` mentions in comments, violating CLAUDE.md's "no plan/ticket/phase IDs in comments" rule. `test-support/i18n_ids.py`/`test_i18n_ids.py` (new, untracked files) carried the same pattern, uncaught by `scripts/check_comment_history.py` since it only scans tracked files.
- **Fix:** Reworded all five comments to describe the mechanism without a plan/ticket reference.
- **Files modified:** companion/i18n.py, companion/i18n_fr/__init__.py, companion/test_i18n.py, test-support/i18n_ids.py, test-support/test_i18n_ids.py
- **Verification:** `scripts/check_comment_history.py check` clean; self-checked the two new untracked files by eye since the tool does not scan them
- **Committed in:** 708761e (Task 1 commit)

**2. [Rule 1 - Bug] `test_status_pages_07.py` reached into `i18n_fr.nav.CATALOG` directly**
- **Found during:** Task 2 (full-suite run after migrating `nav.py` to `MESSAGES`)
- **Issue:** `test_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit` computed the longest rendered nav label by reading `i18n_fr_nav.CATALOG.get(label, label)` — an `AttributeError` once `nav.py` no longer exports `CATALOG` at all.
- **Fix:** Switched to `i18n.t_lang(label, "fr")`, the real translation path, instead of reaching into catalogue internals.
- **Files modified:** companion/test_status_pages_07.py
- **Verification:** full suite green (1737 passed) after the fix
- **Committed in:** 5cb9fa4 (Task 2 commit)

**3. [Rule 1 - Bug] Two `test_i18n.py` completeness checks broke on `nav.py`'s CATALOG removal**
- **Found during:** Task 2's own verify step, immediately after converting `nav.py` fully to `MESSAGES`
- **Issue:** `test_catalog_contains_every_key_defined_in_nav` accessed `i18n_fr_nav.CATALOG`, which no longer exists once `nav.py` exports only `MESSAGES`.
- **Fix:** Guarded both catalogue-completeness checks with `getattr(..., "CATALOG", {})`, and added their `BY_ID`/`MESSAGES` counterparts for symmetry.
- **Files modified:** companion/test_i18n.py
- **Verification:** `pytest companion/test_i18n.py` green
- **Committed in:** 5cb9fa4 (Task 2 commit)

**4. [Rule 1 - Bug] Test fixtures using "Home"/"Password" broke once those strings migrated onto stable ids**
- **Found during:** Task 2 and Task 3's own verify steps
- **Issue:** Several `test_i18n.py` tests called `i18n.t_lang("Home", "fr")` (a plain string) as a stand-in for "any known translated string." Once `"Home"` moved fully onto `nav.home` (`MESSAGES`, not `CATALOG`), a plain-string call site only translates via the `REGISTRY`+`BY_ID`-derived view, which is empty until whatever module declares `nav.home` (`companion/ui_base.py`) has actually been imported — a real dependency in production (`app.py` imports `layout`, which imports `ui_base`, at process start) but not one `test_i18n.py` itself creates, by design (its own import-boundary test proves `companion.i18n`/`companion.prefs` never reach into `companion.pages` or `companion.layout`). A second test's "Password" fixture broke the same way once Task 3 migrated it.
- **Fix:** Moved the affected fixture strings onto ones that stay legacy-`CATALOG` throughout this entire plan ("Status" → "Statut" from `home.py`; "Screen" → "Écran" from `health.py`), which need no other module's import to translate correctly.
- **Files modified:** companion/test_i18n.py
- **Verification:** full suite green after each fix
- **Committed in:** 5cb9fa4, c9d4c1a

---

**Total deviations:** 4 auto-fixed (all Rule 1 — bugs directly caused by this plan's own migration, none out of scope)
**Impact on plan:** All four were necessary to keep the test suite green through the migration; none changed rendered output or scope beyond fixing what the migration itself broke.

## Issues Encountered

- A prior execution attempt was killed mid-Task-1 by a container restart, leaving uncommitted work in the tree. Per the resume instructions, that work was verified against Task 1's spec (behavior, IDs, fallback semantics all matched), fixed for two comment-history violations, then committed as Task 1 rather than redone from scratch.
- The plan's Task 2 wording anticipated some `common.py`/`nav.py` entries staying English-keyed as page-owned; in practice both catalogues fully converted (see Decisions above), so the "list these entries in the SUMMARY" instruction has nothing to list for `common.py`/`nav.py` specifically — the still-legacy entries all belong to `health.py`/`display.py`/`home.py`/`notifications.py`/`registry.py`, out of this plan's file scope, and are enumerated in the next section.

## Known Cross-Area IDs (for plans 40-13/40-14/40-15)

These ids were assigned this plan, at a shared module's Message declaration site, but their owning `i18n_fr` catalogue module stays legacy `CATALOG` until its own migration plan runs. Each resolves correctly today via the Message-with-no-`BY_ID`-entry legacy fallback.

| ID | English | Owning catalogue (unmigrated) |
|----|---------|-------------------------------|
| `health.screen` | "Screen" | health.py |
| `health.just_now` | "just now" | health.py |
| `health.ago` | "%s ago" | health.py |
| `health.in_a_moment` | "in a moment" | health.py |
| `health.in` | "in %s" | health.py |
| `health.s_ago`/`m_ago`/`h_ago`/`d_ago` | "#s ago" etc. | health.py |
| `health.in_s`/`in_m`/`in_h`/`in_d` | "in #s" etc. | health.py |
| `health.waiting` | "waiting…" | health.py |
| `health.updating` | "Updating…" | health.py |
| `health.updated` | "Updated " | health.py |
| `display.on` | "On" | display.py |
| `display.off` | "Off" | display.py |
| `display.quiet_hours` | "Quiet hours" | display.py |
| `display.on_to` | "On — %s to %s" | display.py |
| `display.applies_the_next_time_the_frame_wakes_up` | "Applies the next time the frame wakes up." | display.py |
| `display.poll_triggered_recently_try_again_in_n_s` | "Poll triggered recently — try again in {n}s." | display.py |
| `home.frame` | "Frame" | home.py |
| `home.next_update` | "Next update ≈ %s" | home.py |
| `home.expected_since` | "Expected since %s" | home.py |
| `home.change_the_schedule` | "Change the schedule" | home.py |
| `notifications.test_notification_sent` | "Test notification sent." | notifications.py |
| `notifications.couldn_t_reach_that_topic_check_the_url` | "Couldn't reach that topic — check the URL." | notifications.py |

Plans 40-13/40-14 must derive the SAME ids for these English strings when they migrate `health.py`/`display.py`/`home.py`/`notifications.py` themselves (`test-support/i18n_ids.slug_for()` is deterministic, so this is automatic as long as that plan uses the same tool) — never declare a second, different id for the same English text in those catalogues, or the duplicate-id `ValueError` fires.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The ID mechanism (`Message`/`msg()`/`REGISTRY`/`BY_ID`) is proven (survives rewording, survives a plain-str/Message split across two migration plans) and every shared module is fully migrated.
- Plans 40-13/40-14 can migrate `airlines.py`/`flights.py`/`health.py`/`home.py`/`registry.py` and `display.py`/`calendar_group.py`/`notifications.py`/`rules.py` respectively, using `test-support/i18n_ids.slug_for()` for every new id — the cross-area table above tells them exactly which ids a shared module already assumed for their catalogue's entries.
- Plan 40-15 removes both legacy fallbacks (plain str → TypeError; Message-with-no-BY_ID → fails the completeness test) once every catalogue module is migrated — not before 40-13/40-14 land.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 17 files listed under Files Created/Modified confirmed present on disk; all three task commits (708761e, 5cb9fa4, c9d4c1a) confirmed in `git log`.
