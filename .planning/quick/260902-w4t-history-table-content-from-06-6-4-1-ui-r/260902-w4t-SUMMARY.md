---
phase: quick-260902-w4t
plan: 260902-w4t
subsystem: ui
tags: [history-page, layout, css, corroboration, copy-buttons]

# Dependency graph
requires:
  - phase: 06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi
    provides: 06.6.4.1-UI-REVIEW.md's 19-finding audit, including UIR-04, UIR-05, UIR-06
  - phase: quick-260902-v2v
    provides: the five one-line fixes (UIR-03/07/12/13/15), already merged into origin/main before this branch was created
provides:
  - "History's unresolved-airline fallback is its own text ('Airline unknown'), never shared with the route column's 'Route unavailable'"
  - "The 'View unresolved prefixes' link is visibly separated from the text it follows, on both desktop and mobile"
  - "A callsign-less row promotes its hex to the primary slot with a muted 'no callsign' note and exactly one copy button, on both the desktop cell and the mobile card"
  - "History's Corroboration column shows the short 'Single-source' label with the long form in a title attribute; layout.status_dot() gained a backward-compatible optional title parameter"
  - "Every .data-table-wrap (History, Airlines, Health) has a CSS-only, pointer-inert, theme-aware scroll-edge affordance that only becomes visible when a table's content genuinely overflows its wrap"
affects: [sketch-findings-skypane]

tech-stack:
  added: []
  patterns:
    - "A nested test-helper function used by an early check must be defined before that check's check() call — Python resolves a closure's free variables at CALL time against the enclosing scope, not at parse time, so a helper defined later in the same function body raises 'cannot access free variable' if an earlier-registered check invokes it first."
    - "A CSS-only scroll-edge affordance via layered background-attachment (opaque 'local' covers over 'scroll' shadow gradients) is geometry-driven, not media-query-driven: it is provably invisible on content that already fits, with no JS measurement and no pseudo-element to intercept pointer events."

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/static/style.css
    - companion/layout.py
    - companion/test_view_pages.py

key-decisions:
  - "UIR-05's new AIRLINE_FALLBACK_TEXT constant is separate from panel_render.ROUTE_FALLBACK_TEXT, which stays untouched in server/plane/render.py — confirmed via grep that its four in-module callers and server/test_render.py's six assertions were never at risk, since this task's diff surface is entirely companion/."
  - "UIR-06 deliberately does NOT extend the no-copy-for-empty-value rule into the mobile card's <details> disclosure — its Callsign <dt>/<dd> pair still shows an empty value with a (dead) copy button, exactly as the plan's must_haves specify, because no production row reaches that disclosure state in a way the audit flagged. A callsign-less row's full mobile <li> therefore shows 4 copy buttons total (1 on the promoted-hex primary line + 3 inside the disclosure: callsign/hex/timestamp), which is by design, not a residual bug."
  - "layout.status_dot()'s title parameter is optional and defaults to None — every pre-existing 2-arg call site (history_page.py x2, health_page.py x1, test_companion_app.py x3) produces byte-identical markup, verified by a dedicated harness check rather than assumed from the diff."
  - "The corroboration cross-page drift guard in test_view_pages.py was restated, not weakened, after this task deliberately made History's 'None' label diverge from Health's: it still asserts status agreement for all three keys, visible-label agreement for True/False, and that History's new tooltip text equals Health's own full label exactly — so a future edit to Health's copy still fails this check loudly instead of letting History's tooltip go stale silently."
  - "The scroll-edge affordance uses the background-attachment (local cover / scroll shadow) technique instead of a mask-image fade, because .data-table declares width:100%/min-width:max-content — an unconditional mask would fade the last column of a table that already fits, which is exactly the regression this fix has to avoid. A second override rule matches the cover colour to --color-dominant for the one case (Health's registry/readings/stats tables) where a wrap sits inside a .page-section/.battery-trend-section card instead of directly on the page background."

requirements-completed: [QUICK-260902-w4t]

coverage:
  - id: D1
    description: "UIR-05: airline fallback is its own text, distinct from the route fallback; the unresolved-prefixes link is visibly separated"
    requirement: QUICK-260902-w4t
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct strings in two distinct columns, link spacing class present"
        status: pass
      - kind: automated_ui
        ref: "real browser: zero rows show 'Route unavailable' twice (0/50 production rows); .cell-unresolved-link computed margin-left = 8px on desktop and mobile"
        status: pass
    human_judgment: false
  - id: D2
    description: "UIR-06: a hex-only row promotes the hex to primary with a 'no callsign' secondary and exactly one copy button, desktop and mobile"
    requirement: QUICK-260902-w4t
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — hex-only, callsign+hex, and both-empty branches all covered, zero copy buttons on the both-empty case"
        status: pass
      - kind: automated_ui
        ref: "real browser at 1440px and 375px: production row (hex 06a3d5) shows primary='06a3d5', secondary='no callsign', 1 copy button in the desktop cell"
        status: pass
    human_judgment: false
  - id: D3
    description: "UIR-04: Corroboration column shows the short 'Single-source' label with the long form as a tooltip, in both renderings, in both themes"
    requirement: QUICK-260902-w4t
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — status_dot() backward-compatibility + escaping, and the None-row short-label-with-tooltip check in both the desktop <td> and mobile <dd>"
        status: pass
      - kind: automated_ui
        ref: "real browser, light and dark: dot-label text is exactly 'Single-source', title attribute is 'Single-source (uncorroborated)', no visible parenthetical anywhere"
        status: pass
    human_judgment: false
  - id: D4
    description: "UIR-04: a CSS-only, pointer-inert, theme-aware scroll-edge affordance on every .data-table-wrap; the unscrolled fit at 1280/1440px is re-verified and recorded, not silently assumed"
    requirement: QUICK-260902-w4t
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — .data-table-wrap declares both background-attachment values, no pointer-events anywhere in the stylesheet's data-table-wrap rules"
        status: pass
      - kind: automated_ui
        ref: "real browser: History's .data-table-wrap still overflows at both 1280px (scrollWidth 1347 vs clientWidth 880) and 1440px (1347 vs 1040) even after UIR-05/UIR-04's copy shortening — an accepted, documented outcome per the plan's own instruction not to invent column-hiding to force a fit; Health's three .data-table-wraps measured scrollWidth === clientWidth (no overflow) in the same pass, confirming the affordance's geometry-based invisibility on tables that already fit"
        status: pass
    human_judgment: true
    rationale: "The scroll-edge fade's visual appearance (a subtle 12-24px gradient at a genuinely-overflowing edge, invisible elsewhere) is a judgment call best confirmed by a human eye in both themes on a real device, alongside the still-overflowing History table at 1440px, which the plan explicitly accepted as a documented outcome rather than a defect to force-fix."

duration: resumed after a session interruption; ~55min total across two sessions
completed: 2026-09-03
status: complete
---

# Quick Task 260902-w4t: History Table Content from 06.6.4.1-UI-REVIEW Summary

**Three content fixes from the audit shipped: UIR-05 gives the airline fallback its own text (no more doubled "Route unavailable") with visible spacing before the unresolved-prefixes link; UIR-06 promotes a callsign-less row's hex into the primary slot instead of showing a dead copy button and an orphan separator; UIR-04 shortens History's overlong corroboration label to "Single-source" (long form in a tooltip) and adds a CSS-only scroll-edge affordance to every data table in the app.**

## Performance

- **Tasks:** 4 (3 code tasks + 1 verification task)
- **Files modified:** 4 (`companion/pages/history_page.py`, `companion/static/style.css`, `companion/layout.py`, `companion/test_view_pages.py`)
- **Session note:** execution was interrupted mid-Task-3 by a session rate limit after Tasks 1–2 were committed and Task 3's code/tests were written but uncommitted. Resumed in a new session: found one self-inflicted bug in the uncommitted Task 3 test code (see Issues Encountered), fixed it, ran the full suite green, committed Task 3, then ran Task 4's browser verification.

## Accomplishments

- **UIR-05** — `history_page.py` gained `AIRLINE_FALLBACK_TEXT = "Airline unknown"`, used only for a missing airline; `panel_render.ROUTE_FALLBACK_TEXT` (server/plane/render.py) is completely untouched and still means "route unresolved." `_type_airline_cell()`'s and `_history_cards_html()`'s unresolved-link comparisons were repointed at the new constant, and the anchor gained a `cell-unresolved-link` class with `margin-left: var(--space-sm)` (8px) — verified live: 8px gap on both desktop and mobile.
- **UIR-06** — `_callsign_hex_cell()` and `_history_cards_html()`'s primary-line builder both gained a hex-only branch: the hex becomes the bold-mono primary value with one copy button (reusing the existing `_copy_button_html()` call, not a new one), followed by a muted "no callsign" note with no copy button of its own. The callsign-present branch and the both-empty branch are unchanged. Verified live against the production snapshot's callsign-less rows.
- **UIR-04** — `_CORROBORATION_LABELS["None"]`'s visible label shortened from "Single-source (uncorroborated)" to "Single-source"; the long form moved into a new `_CORROBORATION_TITLES["None"]` dict, rendered via a new optional `title` parameter on `layout.status_dot()` (backward-compatible: every pre-existing 2-arg call site is byte-identical, proven by a dedicated harness check, not just the diff). Both the desktop `<td>` and the mobile `<dd>` carry the tooltip.
- **UIR-04 (scroll-edge affordance)** — `.data-table-wrap` gained a four-layer `background-attachment` gradient stack (opaque "local" covers over "scroll" shadow gradients) that is geometrically invisible when a table already fits its wrap and only reveals a shadow at whichever edge still has more content once it doesn't. A second rule (`.page-section .data-table-wrap, .battery-trend-section .data-table-wrap`) matches the cover colour to `--color-dominant` for the one case a wrap sits inside a card instead of directly on the page background (Health's own tables). No pseudo-element, no JS, no pointer-events declaration anywhere.
- The corroboration cross-page drift guard in `test_view_pages.py` was restated (not weakened) to keep asserting status agreement for all three keys, visible-label agreement for True/False, and that History's new tooltip text equals Health's own full label exactly.

## Task Commits

1. **Task 1: UIR-05 — airline fallback constant, comparison sites, link spacing** — `09d44b0` (fix)
2. **Task 2: UIR-06 — hex-primary promotion, desktop + mobile** — `a8cc897` (fix)
3. **Task 3: UIR-04 — corroboration label shortening + status_dot() title + scroll-edge CSS** — `a76201f` (fix, includes the `_row_block` ordering bugfix found before commit)
4. **Task 4: real-browser verification + SUMMARY** — this SUMMARY.md (no code commit)

## Files Created/Modified

- `companion/pages/history_page.py` — `AIRLINE_FALLBACK_TEXT`, `_CORROBORATION_TITLES`, `NO_CALLSIGN_NOTE_TEXT` new constants; `format_event_row()`, `_callsign_hex_cell()`, `_type_airline_cell()`, `_history_table_html()`, `_history_cards_html()` all touched
- `companion/static/style.css` — `.cell-unresolved-link` (link spacing), `.data-table-wrap`'s scroll-edge gradient stack, `.page-section .data-table-wrap, .battery-trend-section .data-table-wrap` surface-colour override
- `companion/layout.py` — `status_dot()` gains optional third `title` parameter
- `companion/test_view_pages.py` — `EXPECTED_CHECK_COUNT` 46 → 49; three new checks (status_dot title contract, None-row short-label-with-tooltip, data-table-wrap CSS contract); the corroboration cross-page guard restated; `_row_block()` helper relocated earlier in the file (bugfix, see below)

## Issues Encountered

**Session interruption, then a self-inflicted test-ordering bug found on resume.** The original execution was cut off by a session rate limit partway through Task 3, after the code and test changes were written to disk but before the harness had been run or the commit made. On resume, running `companion/test_view_pages.py` surfaced `NameError: cannot access free variable '_row_block'` in the new None-row check. Root cause: the new check (registered via `check()`, which invokes it immediately) referenced the shared `_row_block()` test helper, but that helper's `def` statement lived later in the same enclosing function — Python resolves a nested function's free variables against the enclosing scope at *call* time, not parse time, so the earlier `check()` invocation ran before `_row_block` existed as a local name. Fixed by relocating `_row_block()`'s single definition to immediately before its new first use; every one of its eight later call sites in the file is unaffected. `view-pages` went from 48/49 to 49/49 after the fix.

## User Setup Required

None — no external service configuration required.

## Browser Measurement (before/after)

Method matches quick task 260902-v2v's own SUMMARY: Playwright (headless Chromium) against `companion/app.py` running from this branch, state-dir pointed at a fresh `cp -R` copy of `/tmp/skypane-prod-state` (the original was never started against or written to), at 1280px/1440px/375px, both themes.

| Measurement | Viewport | Before (from 06.6.4.1-UI-REVIEW.md) | After (this branch, 2026-09-03) |
|---|---|---|---|
| Rows showing "Route unavailable" twice | any | UIR-05: every unresolved row (airline column borrowed the route fallback) | 0 of 50 production rows |
| "View unresolved prefixes" link, gap from preceding text | desktop + mobile | 0px (glued: "Route unavailableView unresolved prefixes") | 8px (`margin-left: var(--space-sm)`), identical on desktop and mobile |
| Hex-only row (production hex `06a3d5`), desktop cell | 1440px | empty `.cell-primary`, a dead "Copy callsign" button copying `""`, orphan leading "·" | `.cell-primary` = "06a3d5" (bold mono), `.cell-secondary` = "no callsign", exactly 1 copy button |
| Same row, mobile card primary line | 375px | blank primary line | `.cell-primary` = "06a3d5" + "no callsign" note; card renders normally (page `scrollWidth` 375, no overflow) |
| Corroboration "None" state, visible label | any | "Single-source (uncorroborated)" (253px column contributor) | "Single-source", with `title="Single-source (uncorroborated)"` — confirmed in both light and dark themes |
| History `.data-table-wrap` scrollWidth vs clientWidth | 1280px | 1472 vs 1040 (audit's 1440px figure) | 1347 vs 880 — still overflows; expected and documented (06.6.1-UI-SPEC.md's own deferred re-verification; the content fixes shrank the table but did not eliminate the overflow) |
| History `.data-table-wrap` scrollWidth vs clientWidth | 1440px | 1472 vs 1040 | 1347 vs 1040 — still overflows, by 307px (down from 432px before this task's content fixes) |
| Health's three `.data-table-wrap` elements (registry/readings/stats) | 1440px | not previously measured for overflow | scrollWidth === clientWidth (1006 === 1006) on all three — no overflow, confirming the scroll-edge affordance's cover gradients fully occlude the shadow layer geometrically, with no visible artifact, on tables that already fit |
| `.data-table-wrap` CSS contract | n/a | no scroll-edge affordance existed | `background-attachment: local, local, scroll, scroll` present on the base rule; a `--color-dominant`-matched override exists for `.page-section`/`.battery-trend-section` wraps; zero `pointer-events` declarations anywhere near either rule |

**Human judgment flagged (D4):** the scroll-edge fade's actual visual appearance — a subtle gradient at History's still-overflowing right edge, confirmed absent on Health's non-overflowing tables — is best signed off by a human eye in both themes, the same way quick task 260902-v2v's real-phone check closed out its own visual findings. The measurements above establish the mechanism is correct (geometry-driven, theme-matched, pointer-inert); a screenshot-based visual pass at the mid-scroll position on a real display would close the loop the way the prior task's phone check did.

## Next Phase Readiness

- All three UIR findings (UIR-04, UIR-05, UIR-06) from `06.6.4.1-UI-REVIEW.md` are shipped and covered by automated regression checks (`view-pages` 49/49) plus real-browser measurement against production data.
- Outstanding from the audit, unchanged by this task: the Settings theme picker (UIR-01/02), the preview thumbnail (UIR-09), Health's own mobile tables (UIR-10/11), and the UIR-20..26 typography/spacing direction items — none of this task's diff touches any of those surfaces.
- History's desktop table still overflows its wrap at both 1280px and 1440px (see Browser Measurement above) — this is the plan's own accepted, documented outcome, with the new scroll-edge affordance as the safety net; no further column-hiding or truncation mechanism was invented to force an unscrolled fit.
- No blockers for other in-flight work; `git diff --stat` against `origin/main` confirms `server/` and `companion/pages/health_page.py` carry zero diff from this task.

## Self-Check: PASSED

- FOUND: `companion/pages/history_page.py`
- FOUND: `companion/static/style.css`
- FOUND: `companion/layout.py`
- FOUND: `companion/test_view_pages.py`
- FOUND commit `09d44b0` (Task 1)
- FOUND commit `a8cc897` (Task 2)
- FOUND commit `a76201f` (Task 3)
- FOUND `status: complete` in this file's frontmatter
- CONFIRMED: full suite (`scripts/run-all-tests.sh`) PASS, all 16 harnesses green, 92% coverage

---
*Phase: quick-260902-w4t*
*Completed: 2026-09-03*
