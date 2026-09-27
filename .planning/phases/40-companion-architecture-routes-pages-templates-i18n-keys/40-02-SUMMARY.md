---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 02
subsystem: ui
tags: [css, stylesheet, playwright, pytest, computed-style, design-tokens]

# Dependency graph
requires:
  - phase: 40-01
    provides: companion_render_snapshot.seed_snapshot_state()/frozen_clock(), the render-baseline capture this plan's own computed-style probe reuses for a deterministic seeded state
provides:
  - A deduplicated, tokenised companion/static/style.css (zero duplicated selector per at-rule context, zero colour literal outside a token)
  - test-support/computed_style_snapshot.py: a reusable real-browser computed-style probe (every element + ::before/::after, both explicit themes, 360/1280px, all NAV_TABS routes + /login)
  - companion/test_stylesheet_structure.py: a permanent parser-based guard against both regressions
affects: [40-03, 40-04, any future companion/static/style.css edit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Theme-independent custom properties declared once in :root only (not repeated in the dark-mode/explicit-theme blocks), matching the existing --radius-card/--space-*/--motion-* convention"
    - "A real-browser before/after computed-style diff as the equivalence proof for a CSS refactor, instead of re-reading the stylesheet"
    - "document.getAnimations() freeze (finish() or pause()+currentTime=0) inside the SAME evaluate() call as the measurement, to remove the wall clock from a computed-style capture"

key-files:
  created:
    - test-support/computed_style_snapshot.py
    - companion/test_stylesheet_structure.py
  modified:
    - companion/static/style.css
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - companion/test_view_pages_03.py
    - companion/test_view_pages_04.py

key-decisions:
  - "Custom properties (--*) excluded from the computed-style probe's captured property list: Chromium's indexed CSSStyleDeclaration enumeration lists every custom property declared on :root, so adding a token would otherwise always register as a 'computed style changed' false positive"
  - "New tokens declared once in :root only, not repeated in the three theme-override blocks, since every one of them held the exact same value in every theme before it was a token"
  - "InProcessAppServer + companion_render_snapshot.frozen_clock() used for the probe's own server (not the subprocess AppServer) so seed time and render-time 'now' are identical across two independent captures"

requirements-completed: [CMP-08]

# Metrics
duration: 90min
completed: 2026-09-27
---

# Phase 40 Plan 02: Deduplicate and tokenise companion/static/style.css Summary

**Merged all 19 duplicated CSS selectors to one rule per at-rule context and replaced all 10 colour literals with 9 role-named tokens, proved equivalent with a byte-identical real-browser computed-style diff across 28 route/width/theme captures.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-09-27T07:07:00Z (approx.)
- **Completed:** 2026-09-27T08:34:00Z
- **Tasks:** 2
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- `companion/static/style.css` now has zero duplicated selector within any one at-rule context (was 19: `.preview-frame__image` x4, `.text-heading` x3, and 17 others x2) and zero colour literal outside a custom-property definition (was 10 `rgba()`/`#hex` declarations across 8 rules).
- Nine new role-named tokens (`--color-image-backdrop`, `--color-scrim`, `--color-overlay-icon`, `--color-overlay-text`, `--color-control-wash`, `--color-control-border-subtle`, `--shadow-control`, `--shadow-control-hover`, `--color-shadow-strong`), each declared once in `:root` since every one held an identical value in every theme.
- `test-support/computed_style_snapshot.py`: a standalone Playwright instrument that logs into a seeded `companion/app.py`, visits the six `NAV_TABS` routes plus `/login` at 360px/1280px in both explicit UI themes, and serialises every element's (and its `::before`/`::after`) resolved style into one JSON document — the "before" and "after" captures are byte-identical.
- `companion/test_stylesheet_structure.py`: a permanent parser-based guard (`css_rules()`-based, never a raw-text scan — satisfies guard G11) that fails the build if either regression class ever reappears.
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` updated with a dated entry naming every new token, its value and its role.

## Task Commits

Each task was committed atomically:

1. **Task 1: Computed-style probe and the "before" capture** - `4678c98` (test)
2. **Task 2: Deduplicate selectors, tokenise colour literals** - `e26ed2e` (test, RED) + `27b7484` (feat, GREEN)

_TDD task: RED (`e26ed2e`, confirmed failing — 19 duplicates, 10 colour literals) then GREEN (`27b7484`, confirmed passing, byte-identical computed-style diff)._

## Files Created/Modified
- `test-support/computed_style_snapshot.py` - Real-browser computed-style probe: `snapshot(base_url, cookie)` + `capture(out_path)` CLI, animation-frozen, custom-properties-excluded, InProcessAppServer + frozen_clock for full determinism.
- `companion/test_stylesheet_structure.py` - Two parser-based guards: no duplicated selector per context, no colour literal outside a token.
- `companion/static/style.css` - 19 duplicated selectors merged to one rule each; 10 colour literals replaced with 9 new tokens.
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` - Dated entry documenting the 9 new tokens and the verification method.
- `companion/test_view_pages_03.py`, `companion/test_view_pages_04.py` - Two pre-existing assertions updated from "shared selector-list membership in one rule" to "equal resolved declarations across each selector's own rule" (see Deviations).

## Decisions Made
- Custom properties (`--*`) are excluded from the computed-style probe's per-element property walk — see Deviations below, this was a bug found and fixed mid-plan, not a plan decision, but it does shape how any future consumer of this probe should read its output (declared tokens are not part of the comparison, only their effects via `var()` are).
- Every new colour token lives in `:root` only, never repeated in the `@media (prefers-color-scheme: dark)` / `html[data-ui-theme="light"]` / `html[data-ui-theme="dark"]` blocks, matching the file's own existing convention for theme-independent tokens (`--radius-card`, `--space-*`, `--motion-*`).
- Where a duplicated selector's declarations came from more than one source rule with different specificities/cascade positions (e.g. `.preview-frame__image`'s four sites: a view-transition-name stub, a four-selector base-box group, an aspect-ratio/object-fit pair, and a background-image group shared with `.theme-chip__preview`), the consolidated rule was built by simulating the ORIGINAL cascade result property-by-property (later-same-specificity wins; a `background` shorthand followed by a `background-image` longhand reproduces the sub-property override the two-rule form relied on) rather than by naively concatenating declarations — verified correct by the byte-identical computed-style diff, not just by inspection.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Computed-style probe counted custom properties as part of "computed style"**
- **Found during:** Task 2's own re-run-and-diff step (action item c)
- **Issue:** `test-support/computed_style_snapshot.py`'s `_CAPTURE_JS` walked every indexed entry of `getComputedStyle()`, and Chromium's `CSSStyleDeclaration` indexed enumeration includes every custom property (`--*`) declared on `:root` (inherited onto every element). Adding the 9 new tokens this plan's own goal requires therefore made every single element on every page report 9 "changed" properties between the before and after captures — a false positive that would have made CMP-08's own stated deliverable (add tokens) permanently indistinguishable from a real regression under this probe.
- **Fix:** `serialise()` now skips any property name starting with `--`, mirroring the exact boundary `test_no_colour_literal_outside_the_token_definitions` already draws ("a declaration whose property does not start with `--`"). A custom property is inert storage — only a `var()` reference to it can paint anything — so excluding it from the equivalence check is correct, not a weakening of the proof.
- **Files modified:** `test-support/computed_style_snapshot.py`
- **Verification:** Re-captured "before" (against the unmodified stylesheet) and "after" (against the edited one) with the fixed probe: `cmp` exits 0, byte-identical across all 28 keys.
- **Committed in:** `27b7484` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] Two pre-existing tests asserted the dissolved shared-selector-group structure directly**
- **Found during:** Full companion test suite run after Task 2's CSS edit
- **Issue:** `test_view_pages_03.py::test_phone_cards_carry_the_airline_name_and_artwork_thumbnail` and `test_view_pages_04.py::test_recent_flight_thumbnails_share_the_shipped_treatments` asserted "the shared white-backing/hairline/radius rule" by checking that `img.history-card__thumb` / `img.recent-flight__thumb` appeared in the SAME `Rule` object's `.selectors` tuple as `.now-showing__image`/`.preview-frame__image` — a structural proxy for "these render identically" that CMP-08's own merge necessarily breaks (each selector now has its own single rule, by design, with no shared-group site left for any of them).
- **Fix:** Rewrote both assertions to compare the resolved `declarations_for()` values of `border`/`border-radius`/`background` across the now-separate rules directly, which is the property the original assertion was actually protecting and is unaffected by the selector-list restructuring.
- **Files modified:** `companion/test_view_pages_03.py`, `companion/test_view_pages_04.py`
- **Verification:** Both tests pass; full `companion/ test-support/` suite (1967 passed, 3 skipped) confirms no other regression.
- **Committed in:** `27b7484` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs found and fixed during this plan's own verification work)
**Impact on plan:** Both fixes were necessary for the plan's own acceptance criteria to be meaningful (an uncorrected probe would have made "computed styles unchanged" un-provable for any token addition) and for correctness (the pre-existing tests were asserting an incidental structural detail, not the actual visual guarantee). No scope creep — no new behaviour, no new surface.

## Issues Encountered
- The computed-style probe's naive implementation (return the full nested object graph from `page.evaluate()`) took 45+ seconds and ~3GB of memory for a single page capture, because Playwright's own object-by-object marshalling protocol is far slower than JSON serialisation for a large structure. Fixed by having the in-page script `JSON.stringify()` the result and return one string (2.3s, 11MB for the same page) — recorded in the probe's own comments so a future reader does not reintroduce the slow form.
- A new stylesheet comment (`--radius-card/--space-*/--motion-* above`) accidentally embedded a literal `*/` inside its own `/* ... */` block, prematurely closing the comment and leaving the next real `*/` as a stray terminator — caught immediately by `test_status_pages_07.py::test_style_css_carries_no_stray_comment_terminator`, fixed by rewording to avoid the substring (no `Auto-fixed Issues` entry needed since this was introduced and caught within the same uncommitted edit, never reaching a commit).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `companion/static/style.css` now satisfies ROADMAP success criterion 3 in full ("No duplicated CSS selector; no hard-coded colour outside tokens"), permanently enforced by `companion/test_stylesheet_structure.py`.
- `test-support/computed_style_snapshot.py` is available as a reusable before/after equivalence instrument for any future companion/ CSS or layout-affecting refactor in this phase (CMP-01 through CMP-07, CMP-09) — the same technique (real-browser computed-style diff, custom properties excluded, animations frozen) generalises beyond this one plan.
- No blockers for the remaining Phase 40 plans.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*
