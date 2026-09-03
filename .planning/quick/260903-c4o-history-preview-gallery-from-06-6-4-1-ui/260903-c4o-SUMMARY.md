---
phase: quick-260903-c4o
plan: 260903-c4o
subsystem: ui
tags: [history-page, gallery, css, dead-code-retirement, companion-app]

# Dependency graph
requires:
  - phase: 06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi
    provides: 06.6.4.1-UI-REVIEW.md's UIR-09 finding (the Now-showing frame measured at 1,325px tall, pushing History's flight list ~1,400px down the page, showing a 600px nearest-neighbour thumbnail stretched to 956px)
  - phase: quick-260902-w4t
    provides: History's current content-fix baseline (UIR-04/05/06) and the Browser Measurement table format / Playwright-against-a-state-copy method this task's own verification follows
provides:
  - "History's newest render is no longer a separate, enlarged, low-resolution frame — it is the first tile in the same always-visible render gallery every other historical render uses, at full /gallery/{name}.png resolution, in a box identical to its siblings"
  - "The /preview.png route, its two constants, its handler, its do_GET dispatch branch, and its two CSS rules (.preview-frame, .preview-image) are retired outright"
  - "server/panel_preview.py is kept on disk (11-check harness untouched) with one docstring sentence recording it now has no production caller"
  - "Nine harness checks rewritten/retargeted across companion/test_view_pages.py (49->50) and companion/test_companion_app.py (108->107), including a pinned contract change: unauthenticated GET /preview.png now 404s instead of 303-redirecting to /login"
affects: [sketch-findings-skypane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Real-browser verification without an MCP browser tool: launched the cached Playwright Chromium binary (~/Library/Caches/ms-playwright/chromium-1228) directly via `--headless` (legacy mode — `--headless=new` hung indefinitely on Page.captureScreenshot in this environment) and drove it over raw Chrome DevTools Protocol using Node 22's built-in WebSocket/fetch globals — no playwright npm package installed, no MCP tool available this session."
    - "A before/after production-state comparison for a plan that skipped its own Task-1-Step-0 baseline capture recovers via the plan's own documented fallback: `git archive origin/main | tar -x` into a scratch tree, run the OLD code from that tree against a copy of production-shaped state with the current venv interpreter, to get honest historical numbers instead of quoting the audit's own figures verbatim."

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/test_view_pages.py
    - companion/app.py
    - companion/static/style.css
    - companion/test_companion_app.py
    - server/panel_preview.py

key-decisions:
  - "/tmp/skypane-prod-state (the literal path the plan and CLAUDE.md context named) did not exist on disk at execution time — already cleaned up since quick task 260902-w4t's own session. Used the freshest full production-shaped snapshot already present in this session's scratchpad (a prior `cp -R` of that same path, made earlier in this multi-task session) as the substitute source for both the before and after scratch copies, and recorded this substitution here rather than silently treating a different directory as the original."
  - "Task 1's own Step 0 (capture a live BEFORE baseline before editing) was missed during execution — code edits proceeded directly. Recovered per the plan's own documented fallback: `git archive origin/main` (the branch's real, unedited base) checked out into a scratch tree, run with `server/.venv/bin/python3` against a copy of the production-shaped snapshot, to produce genuine before numbers rather than quoting 06.6.4.1-UI-REVIEW.md's own figures. The recovered numbers corroborate the audit almost exactly (1440px preview-frame height 1324.66px vs the audit's own ~1325px; 956px rendered vs the audit's own 956px), which is independent confirmation the recovery was faithful."
  - "No MCP browser/Playwright tool was available in this session despite the constraint expecting one (ToolSearch reported disabled). Substituted a hand-driven CDP session against the repo's already-cached Playwright Chromium binary — same real-Chromium rendering engine and DOM/CSSOM the MCP tool would have used, just driven directly over the DevTools Protocol instead of through the plugin."
  - "The always-visible render gallery genuinely INCREASES page height at 375px (scrollHeight 8423 -> 13450, flight-list offsetTop 975 -> 6002) even though it decreases height at 1280/1440px (-133px / -392px) — a real, previously-unmeasured consequence of retiring the collapsed Recent-renders <details> wrapper the plan's own must_haves explicitly forbid re-adding. On mobile, 12 full-size gallery tiles now stack in what is effectively a 1-2-column grid before the flight list, versus the old collapsed disclosure contributing near-zero height. This is not a bug introduced by this task — it is the literal, developer-specified consequence of 'no special treatment, no disclosure wrapper' — but it is flagged here as an honest finding rather than omitted, since it is the opposite direction from the desktop improvement the audit's own headline number described."

requirements-completed: [QUICK-260903-c4o]

coverage:
  - id: D1
    description: "History's live panel folded into the render gallery: preview_section() and its dead constants deleted, RENDER_GALLERY_HEADING/RENDER_GALLERY_CAPTION_TEMPLATE supersede the old two-heading scheme, one always-visible <section> replaces the Now-showing frame + collapsed disclosure"
    requirement: QUICK-260903-c4o
    verification:
      - kind: unit
        ref: "companion/test_view_pages.py — 5 replacement checks (non-empty structure, no preview apparatus even with a real panel.bin, empty state, not-a-disclosure, display-limit/newest-first); 50/50 total"
        status: pass
      - kind: automated_ui
        ref: "real browser (CDP against Chromium): sectionHTML_sequence = [H2, caption, caveat, gallery-grid] with zero readingsDisclosureCount, at 1440/1280/375px in both themes"
        status: pass
    human_judgment: false
  - id: D2
    description: "The /preview.png route, its constants, handler and CSS rules retired; server/panel_preview.py kept with an informational docstring note; nine harness checks retargeted (test_view_pages.py 49->50, test_companion_app.py 108->107)"
    requirement: QUICK-260903-c4o
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py 107/107 (including the new pre-auth-404-not-redirect and authenticated-404-with-real-panel checks); server/test_panel_preview.py 11/11 with zero functional diff"
        status: pass
      - kind: automated_ui
        ref: "real browser: 0 of 24 /preview.png network requests (6 viewport/theme combinations x 4 page loads each verified), 0 .preview-frame/.preview-image elements"
        status: pass
    human_judgment: false
  - id: D3
    description: "The newest render is genuinely full-resolution and uniform with its siblings, not a special-cased thumbnail — visually confirmed against production data, not just asserted structurally"
    verification:
      - kind: automated_ui
        ref: "real browser: first gallery tile naturalWidth/Height 1200x1600 (was 600x800), downscale factor 0.157-0.244 (was upscale 1.33-1.59x); first three tiles' getBoundingClientRect() sub-pixel-identical at every viewport; screenshots captured at 1440/375px in both themes"
        status: pass
    human_judgment: true
    rationale: "Whether the gallery genuinely 'looks' uniform and crisp on real device glass (vs. just passing numeric assertions) is a visual judgment call, matching quick task 260902-w4t's own precedent for its scroll-edge-affordance deliverable — the screenshots and measurements here establish the mechanism is correct, but a human eye confirming the visual result reads as intended is the appropriate final check."

duration: single session, ~70 min (includes CDP-driven browser tooling setup after ToolSearch/MCP unavailability was discovered)
completed: 2026-09-03
status: complete
---

# Quick Task 260903-c4o: History Render-Gallery Consolidation Summary

**The newest panel render is no longer a separate, enlarged, low-resolution "Now showing" frame — it is simply the first tile in History's existing always-visible render gallery, at full `/gallery/{name}.png` resolution, in a box identical to every other tile; the `/preview.png` route and its two dead CSS rules are retired outright.**

## Performance

- **Duration:** single session, ~70 min
- **Tasks:** 3 (2 code tasks + 1 verification task)
- **Files modified:** 6 (`companion/pages/history_page.py`, `companion/test_view_pages.py`, `companion/app.py`, `companion/static/style.css`, `companion/test_companion_app.py`, `server/panel_preview.py`)

## Accomplishments

- **Task 1** — `preview_section()` and its two dead constants (`_NO_PANEL_CAPTION`, `_PREVIEW_IMAGE_ROUTE`) deleted from `companion/pages/history_page.py`; the `from server import panel_preview` import dropped (its only consumer was the deleted function). `NOW_SHOWING_HEADING`/`RECENT_RENDERS_SUMMARY_TEMPLATE` superseded by `RENDER_GALLERY_HEADING = "Recent renders"` and `RENDER_GALLERY_CAPTION_TEMPLATE = "Newest first — the newest render is what the panel is showing now. Showing %d."`. `render()` now emits one always-visible `<section class="page-section">`: one `<h2>`, then (only when the gallery is non-empty) a `.section-caption` count paragraph and the colour caveat, then `gallery_tiles(ctx)` directly in page flow — no `<details>` wrapper anywhere. `gallery_tiles()`, `nearest_gallery_entry()`, the View-panel button, and the shared lightbox are byte-identical (confirmed via `git diff`).
- **Task 2** — `companion/app.py` lost `PREVIEW_THUMB_WIDTH`, `PREVIEW_IMAGE_ROUTE`, `_serve_preview_image()`, and the `do_GET` dispatch branch that called it; `PREVIEW_PAGE_ROUTE` (the `/preview` -> `/history` redirect) is untouched. `style.css` lost `.preview-image` and `.preview-frame` with their own comments; `.readings-disclosure`/`.gallery-grid` untouched. `server/panel_preview.py` gained one informational docstring sentence noting it has no production caller any more, with zero functional change (its 11-check harness is byte-for-byte unmodified). `companion/test_companion_app.py` and `companion/test_view_pages.py` were retargeted to pin the new contract: an unauthenticated `GET /preview.png` now 404s (the session-gated branch is gone, so the request falls through to `do_GET`'s deliberately-ungated unknown-path handler) instead of 303-redirecting to `/login`; an authenticated request with a real 960,000-byte `panel.bin` present also 404s (the route is gone, not empty).
- **Task 3** — Full suite green across all 16 harnesses (92% coverage, above the 83% `fail_under` threshold). Real-browser verification against a scratch copy of production-shaped state confirmed: zero `/preview.png` network requests, zero `.preview-frame`/`.preview-image` elements, zero `readings-disclosure` wrappers, the colour caveat exactly once, one `<h2>`, and the newest render's tile at full 1200x1600 native resolution rendered in a box identical to its siblings, at 1440/1280/375px in both light and dark themes.

## Task Commits

1. **Task 1: fold the live panel into the render gallery** — `ee74386` (refactor)
2. **Task 2: retire the /preview.png route, its stylesheet rules, and their harness checks** — `460d911` (refactor)
3. **Task 3: real-browser verification + SUMMARY** — this SUMMARY.md (no code commit; per this task's own constraints, docs artifacts are left for the orchestrator's final commit)

## Files Created/Modified

- `companion/pages/history_page.py` — `preview_section()`, `_NO_PANEL_CAPTION`, `_PREVIEW_IMAGE_ROUTE` deleted; `RENDER_GALLERY_HEADING`/`RENDER_GALLERY_CAPTION_TEMPLATE` new; `render()`'s section rewritten to one always-visible block
- `companion/test_view_pages.py` — 4 obsolete Section 1b checks replaced with 5 new ones; Section 3's end-to-end check retargeted (`/preview.png` now asserts 404, a new `/gallery/{name}.png` assertion added); `EXPECTED_CHECK_COUNT` 49 -> 50
- `companion/app.py` — `PREVIEW_THUMB_WIDTH`, `PREVIEW_IMAGE_ROUTE`, `_serve_preview_image()`, and its `do_GET` dispatch branch deleted; `panel_preview` import dropped
- `companion/static/style.css` — `.preview-image` and `.preview-frame` rules deleted with their own comments
- `companion/test_companion_app.py` — the unauthenticated-redirect-loop `/preview.png` entry, `_preview_missing`, and `_preview_real_panel` replaced with two checks pinning the new 404-in-both-auth-states contract; `EXPECTED_CHECK_COUNT` 108 -> 107
- `server/panel_preview.py` — one informational docstring sentence added; zero functional change

## Decisions Made

- Substituted the freshest already-present full production-shaped state snapshot in this session's scratchpad for `/tmp/skypane-prod-state`, since the latter no longer existed on disk at execution time (see key-decisions in frontmatter for full detail).
- Recovered Task 1's missed Step-0 BEFORE baseline via `git archive origin/main` into a scratch tree, run under `server/.venv/bin/python3` — the plan's own documented fallback for exactly this situation. The recovered numbers independently corroborate 06.6.4.1-UI-REVIEW.md's own figures (1440px frame height 1324.66px vs. the audit's ~1325px; 956px rendered image width, exact match), which is strong evidence the recovery reflects real pre-edit behaviour rather than a re-derived approximation.
- No MCP Playwright tool was available this session (`ToolSearch` reported disabled, and no `mcp__plugin_playwright_playwright__*`-named tools were reachable). Drove the repository's already-cached Playwright Chromium binary directly over the Chrome DevTools Protocol via a small Node script instead — the same rendering engine, just without the plugin layer. `--headless=new` (Chromium's newer headless mode) hung indefinitely on `Page.captureScreenshot` in this environment; switching to legacy `--headless` resolved it.
- Flagged, rather than silently accepted, a real UX side effect the plan's own must_haves did not anticipate measuring: the render gallery being always-visible (no collapsed disclosure) increases total page height substantially at 375px (scrollHeight +5027px, flight-list offsetTop pushed down by +5027px) even though it decreases height at 1280/1440px. This is the literal, correct consequence of the developer's explicit "no special treatment, no disclosure" decision — not a defect in this task's implementation — but it is a new, previously-unmeasured mobile-specific finding worth carrying into any future backlog discussion about the render gallery's mobile column count or display limit.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1/2/3 auto-fixes were needed. Both code tasks (history_page.py restructure, /preview.png retirement) matched the plan's own action steps exactly, and the anticipated harness-check retargets were exactly the surviving references the plan predicted.

**Process deviations (not code deviations), both already covered above and in the frontmatter's key-decisions:**
1. Task 1's Step 0 (capture a real BEFORE baseline before editing) was skipped during execution and recovered afterward via the plan's own documented `git archive origin/main` fallback.
2. `/tmp/skypane-prod-state` did not exist on disk; a pre-existing scratchpad copy of the same original snapshot was used instead, with the substitution recorded rather than hidden.
3. The `mcp__plugin_playwright_playwright__browser_run_code_unsafe` tool named in this task's constraints was not available in this session; a hand-rolled CDP driver against the same cached Chromium binary was used instead, following the same "real browser, real production-shaped data, scratch copy only" method the constraint specified.

None of these affected the *code* delivered — all verification numbers are genuine measurements from a real, running instance of both the old and new code against the same production-shaped data.

## Issues Encountered

- **Headless Chrome screenshot hang.** `Page.captureScreenshot` over CDP hung indefinitely under Chromium's `--headless=new` mode in this environment (reproduced twice, isolated via a minimal debug script). Switching the launch flag to legacy `--headless` resolved it immediately with no other changes. Documented here in case a future session hits the same issue.
- **`.history-cards`/`.data-table-wrap` offsetTop measurement.** An early version of the measurement script always picked `.history-cards` (present in the DOM at every viewport width, just CSS-hidden above 960px) for the "flight list" offsetTop, which returned 0 at desktop widths since a `display: none` element's `getBoundingClientRect()` is always zero. Fixed by picking whichever of the two candidates actually has non-zero rendered dimensions before reading its offset.

## User Setup Required

None — no external service configuration required.

## Browser Measurement (before/after)

Method: a hand-driven Chrome DevTools Protocol session (see Decisions Made) against `companion/app.py` — the OLD code checked out from `origin/main` via `git archive` for "before", the current branch's code for "after" — both pointed at fresh `cp -R` copies of the same production-shaped state snapshot (never the shared original), at 1280px/1440px/375px, both themes. Dark-theme numbers were confirmed structurally identical to light at every viewport (theme only changes colour, never layout), so the table below reports light-theme numbers plus the two deltas that matter.

| Measurement | Viewport | Before (git-archived origin/main, this branch's true base) | After (this branch, 2026-09-03) |
|---|---|---|---|
| `/preview.png` network requests per `/history` load | any | 1 (the live-preview `<img>` always requested it) | 0 of 24 requests (6 viewport/theme combinations, both structural and screenshot passes) |
| `.preview-frame` / `.preview-image` element count | any | 2 (one frame, one image) | 0 |
| `<details class="readings-disclosure">` count on History | any | 1 (always present, closed by default) | 0 |
| `<h2>` count in the render section | any | 1 | 1 (unchanged — always exactly one) |
| Colour caveat occurrence count | any | 1 | 1 (unchanged — always exactly once when non-empty) |
| `.preview-frame` rendered height | 1440px | 1324.66px (matches 06.6.4.1-UI-REVIEW.md's own ~1325px figure) | n/a — element retired |
| `.preview-image` natural vs. rendered size | 1440px | 600x800 native, rendered 956x1274.66 (1.59x **upscale**) | n/a — element retired |
| `.preview-image` natural vs. rendered size | 1280px | 600x800 native, rendered 796x1061.33 (1.33x upscale) | n/a |
| `.preview-image` natural vs. rendered size | 375px | 600x800 native, rendered 243x324 (0.41x downscale — mobile was already downscaling) | n/a |
| First gallery tile's `<img>` natural vs. rendered size | 1440px | n/a (tile existed but was inside a closed `<details>`; `loading="lazy"` deferred its fetch, `naturalWidth`/`naturalHeight` = 0) | 1200x1600 native (the panel's real resolution), rendered 188.39x251.19 (0.157x **downscale**) |
| First gallery tile's `<img>` natural vs. rendered size | 1280px | n/a (see above) | 1200x1600 native, rendered 199.5x266 (0.166x downscale) |
| First gallery tile's `<img>` natural vs. rendered size | 375px | n/a (see above) | 1200x1600 native, rendered 293x390.66 (0.244x downscale) |
| First three gallery tiles' rendered box uniformity | 1440px | n/a (tile 1 uncomparable — see above) | 188.39x251.19 / 188.41x251.20 / 188.39x251.19 — sub-pixel-identical (CSS grid track rounding only) |
| First three gallery tiles' rendered box uniformity | 1280px / 375px | n/a | Byte-identical at both widths (199.5x266 x3; 293x390.66 x3) |
| Page `scrollHeight` | 1440px | 4419px | 4027px (**-392px**) |
| Page `scrollHeight` | 1280px | 4205px | 4072px (**-133px**) |
| Page `scrollHeight` | 375px | 8423px | 13450px (**+5027px** — see Decisions Made: the always-visible 12-tile gallery now stacks in ~1-2 columns on mobile, versus the old collapsed disclosure contributing near-zero height) |
| Flight list `offsetTop` (the audit's own headline complaint) | 1440px | 1734.25px | 1342.77px (**-391.48px**) |
| Flight list `offsetTop` | 1280px | 1520.92px | 1387.16px (**-133.77px**) |
| Flight list `offsetTop` | 375px | 975.19px | 6001.78px (**+5026.59px** — same mobile finding as above) |
| History's own `details.history-card__details` count | 375px | 50 | 50 (unchanged — the mobile card disclosures this task must not touch) |

**Grep sweep result:** no unanticipated survivor. The repo-wide sweep for `preview\.png|PREVIEW_IMAGE_ROUTE|PREVIEW_THUMB_WIDTH|preview-frame|preview-image` found exactly the four anticipated test sites (all retargeted in Task 2) plus two harmless false positives, both left untouched and out of this task's `files_modified` scope: `server/plane/render.py`'s own `--preview` CLI flag docstring examples (a substring match on an unrelated flag name, `--preview /tmp/panel.preview.png`, nothing to do with the companion HTTP route), and one stale prose mention of "the preview-image error pages" in `companion/layout.py`'s `page_shell()` docstring (referring to the now-deleted route's former 404/503 error pages — a real staleness, but `companion/layout.py` is not in this plan's `files_modified` list, so it was left as-is rather than edited out of scope).

**Accepted edge case (restated per the plan's own instruction):** a hand-placed `panel.bin` with no corresponding gallery entry now shows the `gallery_tiles()` no-renders empty state instead of a lone enlarged image — this is deliberate, not engineered around, and is exactly what the plan's must_haves specified.

**`server/panel_preview.py` deliberately not deleted:** it is kept as tested infrastructure (`server/test_panel_preview.py`, 11/11, zero diff) with one new docstring sentence recording that it currently has no production caller — the companion route that used to serve its output was removed by this task in favour of the render gallery's existing full-resolution `/gallery/{name}.png` route.

## Test Harness Results

All 16 canonical harnesses, `scripts/run-all-tests.sh`, final run on the completed tree:

| # | Harness | Result |
|---|---|---|
| 1 | `server/test_config_history.py` | 30/30 |
| 2 | `server/test_dither.py` | 6/6 |
| 3 | `server/test_enrich.py` | 52/52 |
| 4 | `server/test_illustrations.py` | 52/52 |
| 5 | `server/test_panel_preview.py` | 11/11 (zero diff to this harness) |
| 6 | `server/test_pipeline_e2e.py` | 6/6 |
| 7 | `server/test_plane_detection.py` | 47/47 |
| 8 | `server/test_poll_loop.py` | 44/44 |
| 9 | `server/test_render.py` | 119/119 |
| 10 | `server/test_runway_config.py` | 14/14 |
| 11 | `stub-server/test_poll_cycle.py` | 23/23 |
| 12 | `companion/test_companion_app.py` | 107/107 (was 108/108) |
| 13 | `companion/test_config_page.py` | 64/64 |
| 14 | `companion/test_contrast_check.py` | 36/36 |
| 15 | `companion/test_status_pages.py` | 117/117 |
| 16 | `companion/test_view_pages.py` | 50/50 (was 49/49) |

**Coverage:** 92% (threshold `fail_under = 83` in `pyproject.toml`). `server/panel_preview.py` itself sits at 85% — `panel_file_mtime_iso()` lost its only caller and has zero coverage of its own in `server/test_panel_preview.py` (grep-verified during planning), which is the expected, small, measured dip this plan called out in advance rather than assuming away.

**Overall verdict: PASS** — all 16 harnesses green, coverage above threshold, zero unexpected `git diff` surface (`companion/pages/health_page.py`, `companion/static/list-filter.js`, `companion/static/panel-lookup.js`, and `server/test_panel_preview.py` all carry zero diff from this task).

## Next Phase Readiness

- History's render gallery is now the single source of truth for both the newest render and its history — no future plan should need to re-introduce a "current panel" special case anywhere on this page.
- The mobile page-height finding above (scrollHeight +5027px at 375px) is new information, not a defect in this task — flagged for whoever next revisits History's mobile layout or the render gallery's display density/column count, since it is the opposite direction from the desktop improvement the original audit finding described.
- `sketch-findings-skypane`'s `--radius-card` reserved-consumer list currently still names `.preview-frame`, which no longer exists after this task — `affects: [sketch-findings-skypane]` above flags this for the skill's next maintenance pass.
- No blockers for other in-flight work; `git diff origin/main --stat` confirms this task's diff is exactly the six `files_modified` files plus its own PLAN.md — no `server/` change beyond `panel_preview.py`'s one docstring sentence, and zero diff to `server/test_panel_preview.py`, `companion/pages/health_page.py`, `companion/static/list-filter.js`, or `companion/static/panel-lookup.js`.

## Self-Check: PASSED

- FOUND: `companion/pages/history_page.py`
- FOUND: `companion/test_view_pages.py`
- FOUND: `companion/app.py`
- FOUND: `companion/static/style.css`
- FOUND: `companion/test_companion_app.py`
- FOUND: `server/panel_preview.py`
- FOUND commit `ee74386` (Task 1)
- FOUND commit `460d911` (Task 2)
- FOUND `status: complete` in this file's frontmatter
- CONFIRMED: full suite (`scripts/run-all-tests.sh`) PASS, all 16 harnesses green, 92% coverage

---
*Phase: quick-260903-c4o*
*Completed: 2026-09-03*
