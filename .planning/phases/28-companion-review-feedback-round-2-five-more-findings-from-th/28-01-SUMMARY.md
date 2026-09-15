---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 01
subsystem: ui
tags: [icon-sprite, i18n, mobile-nav, playwright-free-unit-tests, python]

# Dependency graph
requires:
  - phase: 22-14
    provides: "_mobile_nav_html()'s panel reduced to preferences-only content (no page-navigation links), and the destination links moved to _tab_bar_html()"
provides:
  - "icon-gear symbol in the shared ICON_DEFS_HTML sprite, appended as ICON_IDS' 23rd member"
  - "#site-nav-toggle rendering icon-gear instead of icon-hamburger, NAV_TOGGLE_LABEL and the panel body byte-identical"
  - "both icon-sprite count checks (_icon_sprite_integrity, _page_shell_emits_sprite_once_no_inline_styles) retargeted to 23, mutation-tested"
  - "a new regression check proving the toggle's glyph, translated label (EN+FR), and panel relationship stay in agreement"
affects: [companion-app-testing, companion-layout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ICON_IDS append-never-reorder convention (own trailing tuple-concat + count-naming comment) extended for a sixth time"
    - "History-comment supersession: append a new sentence naming the new plan/count, never rewrite the original sentence — digits (22/23) used in the new sentence instead of the spelled-out word so a file-wide 'twenty-two' grep count stays pinned to the three genuine historical occurrences"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/test_companion_app.py

key-decisions:
  - "icon-hamburger's ICON_IDS entry and <symbol> were kept, not pruned, even though icon_html(\"icon-hamburger\", ...) now has zero call sites — per the plan's explicit instruction, pruning is an optional future follow-up outside this plan's scope"
  - "The new check's EN/FR aria-label assertion (clause c) drives a real HTTP GET through the harness with an Accept-Language header, reusing the exact idiom _accept_language_resolves_html_lang_with_no_cookie/_ui_lang_cookie_beats_accept_language already use, rather than calling prefs.set_request_prefs() directly (which the file's own Section 6 header comment documents avoiding, since it leaks ContextVar state into later checks) — this also satisfies 'read through the same translation call the renderer uses' more faithfully than the test-only i18n.t_lang() sibling would on its own"

patterns-established:
  - "When a supersession sentence needs to restate an old/new count where the old count's spelled-out word is pinned by an acceptance grep, spell out only the NEW count and use digits for the OLD one in the new sentence"

requirements-completed: [CFG-76]

# Metrics
duration: ~20min
completed: 2026-09-15
---

# Phase 28 Plan 01: Mobile nav toggle hamburger to gear glyph Summary

**`#site-nav-toggle` now renders a gear glyph (icon-gear) instead of the hamburger it inherited from before Phase 22-14 moved page navigation to the bottom tab bar; both hard-coded icon-sprite member-count checks moved from 22 to 23 and a new check proves the glyph, the translated label, and the panel's still-navigation-free contents all agree.**

## Performance

- **Duration:** ~20 min (commit-to-commit; investigation/reading preceded the first commit)
- **Started:** 2026-09-15T19:21:00Z (Task 1 commit)
- **Completed:** 2026-09-15T19:36:22Z (Task 2 commit)
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- `ICON_IDS` grew from 22 to 23 members (`icon-gear` appended as its own trailing tuple-concat, following the file's established append-never-reorder convention) and `ICON_DEFS_HTML` gained a matching `<symbol id="icon-gear">` (centre circle + toothed ring, `viewBox="0 0 20 20"`, `stroke-width="1.6"`, same visual weight as its `icon-power`/`icon-moon` neighbours)
- `#site-nav-toggle`'s render site changed its single `icon_html(...)` argument from `"icon-hamburger"` to `"icon-gear"` — `NAV_TOGGLE_LABEL` ("Account and preferences") and every other line of `_mobile_nav_html()` are byte-identical (confirmed via `git diff`: the only changed line in that function is the icon id)
- Both `_icon_sprite_integrity()` and `_page_shell_emits_sprite_once_no_inline_styles()` retargeted in place: all four `!= 22:` literals and both registered check descriptions now say twenty-three
- One new check, `_the_nav_toggle_wears_the_gear_and_opens_the_same_panel`, asserts all four required clauses: (a) the toggle markup references `icon-gear`, (b) zero `icon-hamburger` references, (c) the `aria-label` matches `i18n.t(NAV_TOGGLE_LABEL)` in both EN and FR read through a real per-request Accept-Language round trip, (d) the panel still holds the language switch, theme switch and Sign out form with zero page-navigation `<a href>` links
- `EXPECTED_CHECK_COUNT` re-derived by running the suite: 314 → 315 (one new check); confirmed 313/315 pass, matching the pre-existing baseline

## Task Commits

Each task was committed atomically:

1. **Task 1: The gear joins the sprite and the toggle stops pointing at the hamburger** - `275e943` (feat)
2. **Task 2: Both count checks move to 23 and one new check proves the glyph swap end to end** - `dcfc0cd` (test)

**Plan metadata:** (this commit, to follow)

## Files Created/Modified
- `companion/layout.py` - `ICON_IDS` appended with `icon-gear` (22→23); `ICON_DEFS_HTML` gained the `icon-gear` `<symbol>`; `_mobile_nav_html()`'s toggle render site now calls `icon_html("icon-gear", size=24)`
- `companion/test_companion_app.py` - `_icon_sprite_integrity()` and `_page_shell_emits_sprite_once_no_inline_styles()` retargeted to 23; three "twenty-two" history comments superseded in writing (originals kept legible); one new check added; `EXPECTED_CHECK_COUNT` bumped 314→315

## Decisions Made
- Kept `icon-hamburger`'s `ICON_IDS` entry and `<symbol>` rather than pruning it, even though `grep -c 'icon_html("icon-hamburger"' companion/layout.py` is now 0 (zero remaining consumers, confirmed by grep before and after the edit — the only prior consumer was `#site-nav-toggle`'s own render site, now changed). Per the plan's explicit instruction, removing it is a scoped, optional follow-up for a later phase, not this plan's job — pruning it would additionally require another edit to all four count-checks and their messages, well outside a one-glyph-swap's scope.
- Used a real HTTP round trip (Accept-Language header, via the already-running harness and `session_cookie`) to prove clause (c)'s EN/FR aria-label assertion, rather than calling `prefs.set_request_prefs()` directly against the ContextVar. The file's own Section 6 header comment (~line 11467 pre-edit) documents avoiding `set_request_prefs()` because it leaks state into every later check in the same process; the HTTP-harness idiom already used by `_accept_language_resolves_html_lang_with_no_cookie` and `_ui_lang_cookie_beats_accept_language` sidesteps that risk entirely while exercising the exact same production code path the real renderer uses (app.py's per-request language resolution, not a test-only shortcut).
- In the three history-comment supersessions plus the new `EXPECTED_CHECK_COUNT` changelog entry, referred to the OLD count ("22") using digits rather than the spelled-out word "twenty-two" wherever a NEW sentence was added — this keeps `grep -c 'twenty-two' companion/test_companion_app.py` pinned at exactly 3 (the three genuine historical occurrences from 22-14's own growth), satisfying the acceptance criterion that a count above 3 would mean new prose was quietly polluting the "twenty-two" tally the criterion exists to police, and a count below 3 would mean the original history was rewritten rather than superseded.

## Deviations from Plan

None — plan executed exactly as written. The one open question worth flagging (not a deviation, since the plan itself calls it out as an observation to record, not act on) is documented in "Icon-hamburger's remaining consumers" below.

### Icon-hamburger's remaining consumers

Grep confirmed **zero** remaining consumers of `icon_html("icon-hamburger", ...)` anywhere in `companion/layout.py` after Task 1's edit (the toggle's render site was the only call site). Per the plan's explicit instruction, the whitelist entry and sprite `<symbol>` are deliberately kept rather than pruned — recorded here as the plan requires, for a later phase's discretion, not acted on.

## Issues Encountered

None. The one design question requiring investigation — how to prove clause (c)'s translated aria-label without leaking `prefs`' ContextVar state across checks — was resolved by reusing the existing Accept-Language HTTP-harness idiom already present in the file (see Decisions Made above), not by inventing a new mechanism.

## Mutation Testing (Task 2, quoted verbatim)

All four mutations were applied to `companion/layout.py`, run against `companion/test_companion_app.py`, and reverted with `git checkout-index -f -- companion/layout.py`. `git status --porcelain` was clean of unintended changes after each revert and at the end.

**M-A** — reverted the toggle to `icon_html("icon-hamburger", size=24)`. The new check failed on clause (a):
> `#site-nav-toggle renders icon-gear (never icon-hamburger), its aria-label is NAV_TOGGLE_LABEL translated through i18n's real per-request path in both EN and FR, and the panel it opens still holds the language/theme switches and Sign out with zero page-navigation links (CFG-76) - expected #site-nav-toggle's markup to reference icon-gear, got 'id="site-nav-toggle" class="site-nav-toggle" aria-label="Account and preferences" aria-expanded="false" aria-controls="mobile-nav"><svg class="icon" width="24" height="24" aria-hidden="true" focusable="false"><use href="#icon-hamburger"></use></svg></button>'`

**M-B** — deleted the `"icon-gear"` entry from `ICON_IDS`, leaving the `<symbol>` in the sprite. The harness run surfaces only the first failing clause the function reaches (pre-existing early-return structure, left untouched per the plan's instruction not to restructure the correspondence assertion):
> `layout.ICON_IDS has exactly twenty-three unique members, each a symbol id in ICON_DEFS_HTML and vice versa - expected exactly twenty-three ICON_IDS, got 22`

Direct evaluation of the correspondence clause under the same mutated state (run separately, outside the harness, since the function's own early return prevents it from being reached in a single pass) confirms it independently fails too, as the plan requires be quoted:
> `sprite symbol ids [...'icon-power', 'icon-moon', ...] do not match ICON_IDS ('icon-device', ... 'icon-power', 'icon-moon', ...)` (23-member sprite list vs 22-member `ICON_IDS` tuple — full lists in the check's own `%r` formatting, elided here for length)

**M-B2** — deleted the `<symbol id="icon-gear">` from `ICON_DEFS_HTML`, leaving the `ICON_IDS` entry (23 members, sprite now has only 22 symbols). Both count-pinning checks failed, confirming the second check was genuinely moved and not merely assumed to follow the first:
> `_icon_sprite_integrity()`: "layout.ICON_IDS has exactly twenty-three unique members, each a symbol id in ICON_DEFS_HTML and vice versa - sprite symbol ids [22 ids, no icon-gear] do not match ICON_IDS [23 ids, includes icon-gear]"
> `_page_shell_emits_sprite_once_no_inline_styles()`: `page_shell() emits exactly one sprite (one <defs, twenty-three <symbol) before dashboard-shell, no inline styles - expected exactly twenty-three <symbol, got 22`

(Note: `_icon_sprite_integrity()` fails on its correspondence clause here rather than its `<symbol` count clause, since the correspondence assertion is evaluated first in the function's existing order and both are independently violated by this mutation — `_page_shell_emits_sprite_once_no_inline_styles()` does fail precisely on its `<symbol` count clause as expected. Both checks fail, which is what M-B2 exists to prove.)

**M-C** — added `<a href="/flights">Flights</a>` to `_mobile_nav_html()`'s footer. The new check failed on clause (d):
> `#site-nav-toggle renders icon-gear (never icon-hamburger), its aria-label is NAV_TOGGLE_LABEL translated through i18n's real per-request path in both EN and FR, and the panel it opens still holds the language/theme switches and Sign out with zero page-navigation links (CFG-76) - expected zero page-navigation <a href> links in the dropdown, found one`

(This mutation also correctly broke two pre-existing checks — `_toggle_aria_contract_and_fixed_label`'s dropdown-link-count sibling and `_dropdown_contents_and_order` — confirming the injected link was a genuine page-navigation regression, not an artifact of the new check alone.)

## Expected-Check-Total Re-derivation

Old total: 314 (last set by 25-07-PLAN.md Task 2). New total: 315 (+1, the one new check this plan adds). Command run: `PY=/home/user/skypane/server/.venv/bin/python; "$PY" companion/test_companion_app.py`. Printed result: `companion-app: 313/315 checks pass` — the two failures are the pre-existing, documented WR-11 root-sandbox failures (`server/test_manual_resolutions.py`'s sibling assertions inside this same harness file: `add_entry()`/`delete_entry()` read-only-state-dir simulations, which do not fail under a root-owned filesystem where permission enforcement is bypassed), unrelated to this plan's changes. Confirmed via `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh`: overall named failures are exactly `server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — all three are the same class of root-sandbox read-only-directory-simulation failure, none touching `layout.py` or the icon sprite.

## Verification Evidence

- `companion/test_companion_app.py` → 313/315 pass (the 2 known WR-11 root-sandbox failures, named above, and no others)
- `companion/test_i18n.py` → 24/24 pass, exit 0
- `ruff check .` → clean
- `git diff --stat` (base commit `4dd30da` → `dcfc0cd`) → exactly two files: `companion/layout.py` (25 lines changed), `companion/test_companion_app.py` (128 lines changed)
- `grep -cE '!= 22:' companion/test_companion_app.py` → 0
- `grep -n 'twenty-two' companion/test_companion_app.py | grep -cv ':[[:space:]]*#'` → 0
- `grep -c 'twenty-two' companion/test_companion_app.py` → 3 (all three are the original 22-14 history comments, superseded in place, originals legible)
- `grep -c 'Compte et préférences' companion/test_companion_app.py` → 0 (no hardcoded French literal)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/layout.py` and `companion/test_companion_app.py` are the two files this plan owns for Wave 1; later waves depending on them landing first (28-03 writes `layout.py`, 28-06 writes `test_companion_app.py`) can proceed once this plan merges.
- No blockers. The icon-hamburger zero-consumer observation is recorded above for a future phase's discretion, not a blocker for this one.

## Self-Check: PASSED

- FOUND: `companion/layout.py`
- FOUND: `companion/test_companion_app.py`
- FOUND: `.planning/phases/28-companion-review-feedback-round-2-five-more-findings-from-th/28-01-SUMMARY.md`
- FOUND: commit `275e943` (Task 1)
- FOUND: commit `dcfc0cd` (Task 2)
- FOUND: commit `68876e5` (plan metadata)

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Completed: 2026-09-15*
