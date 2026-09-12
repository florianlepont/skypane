---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 02
subsystem: ui
tags: [freshness-loop, es5, i18n, removal, health-page]

# Dependency graph
requires: ["21-01"]
provides:
  - "companion/pages/health_page.py — Health's freshness line is prefix + clock + pill only, no button, no replacement control"
  - "companion/static/freshness.js — the freshness loop runs unconditionally whenever the tab is visible; the tab-visibility mechanism (stopLoop/startLoop/intervalHandle, tick()'s document.hidden guard, the visibilitychange registration) is byte-for-byte unchanged"
  - "companion/test_status_pages.py — two checks retargeted in place to pin the removal (zero data-refresh-toggle/data-pause-text/data-resume-text, zero occurrences of data-pause-text/wireToggle in the real served script bytes) against silent reintroduction"
affects: []

tech-stack:
  added: []
  patterns:
    - "EXPECTED_CHECK_COUNT re-derivation by running the harness and appending a new last assignment, never by arithmetic on the old comment (this codebase's established convention, followed for the one touched harness)"
    - "opposite-direction regression pin: when a served-bytes needle proving a feature's presence is retired, a new needle proving its absence replaces it in the same check, rather than deleting the assertion outright"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/static/freshness.js
    - companion/test_status_pages.py

key-decisions:
  - "Rewrote the two pinned test_status_pages.py checks in place rather than deleting and re-adding them (Task 1's zero-<form>/one-<button> literal count, and the persistent-freshness-note structural check) — the freshness wrapper's shape still needs to be pinned, just without the button, matching the plan's own explicit instruction not to delete the checks."
  - "Reworded two of my own added header comments in freshness.js (the D-18 SUPERSEDED note and the AUTO_REFRESH_INTERVAL_MS comment) to avoid the literal word 'paused' inside a backtick-quoted span, and to avoid a bare backtick character, since a literal match would have tripped the plan's own acceptance-criteria grep for the deleted mechanism's identifiers and for the ES5-floor backtick check — mirroring the same care 21-01-SUMMARY.md's Deviations documented for the identical class of self-inflicted grep trip."
  - "Left one pre-existing, unrelated ES5-floor grep hit in place (see Deviations) rather than editing line 7 of freshness.js, since it predates this plan and editing it would be an out-of-scope change to a file:line this plan did not otherwise touch for that purpose."

requirements-completed: [CFG-23]

# Metrics
duration: ~35min
completed: 2026-09-12
---

# Phase 21 Plan 02: Health "Pause updates" button and freshness.js's pause branch removed Summary

**Deletes the Health page's Pause/Resume button (health_page.py, i18n_fr/health.py) and freshness.js's entire pause mechanism (the `paused` flag, `setToggleVisual()`, `wireToggle()`, both `if (paused)` guards), leaving the freshness loop unconditional and the tab-visibility mechanism byte-for-byte unchanged, with the served-script and served-HTML test pins retargeted to prove the removal rather than deleted.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-12 (approx.)
- **Completed:** 2026-09-12
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `companion/pages/health_page.py`: `REFRESH_PAUSE_TEXT`/`REFRESH_RESUME_TEXT` and the comment block explaining the data-pause-text/data-resume-text idiom deleted; `toggle_html`'s construction and its slot in `freshness_html`'s `%`-format tuple deleted — the freshness line shrinks from `{prefix} {clock} {pill} {button}` to `{prefix} {clock} {pill}`, no replacement control
- `companion/i18n_fr/health.py`: `"Pause updates"`/`"Resume updates"` French catalogue entries deleted in the same commit as their English constants
- `companion/static/freshness.js`: the module-level `paused` variable, `setToggleVisual()`, `wireToggle()`, both call sites (inside `applySwap()` and at the bottom of the file), the `if (paused)` guard inside `tick()`, and the `if (paused)` guard inside the `visibilitychange` listener (with its comment) all deleted; the header comment updated to name D-18 and state the loop is now unconditional
- Left completely untouched, byte-for-byte, per the plan's DO-NOT-TOUCH list: `AUTO_REFRESH_INTERVAL_MS`'s value, `stopLoop()`, `startLoop()`, `intervalHandle`, `tick()`'s `if (document.hidden) { stopLoop(); return; }` guard, the `visibilitychange` registration itself, every `[data-loaded-at]`/`[data-refresh-pill]` hook, and every `REFRESH_SWAP_SELECTORS` consumer
- `companion/test_status_pages.py`: two checks rewritten in place —
  - the zero-`<form>`/button-literal-count check now expects exactly one `<button` (the pre-existing D-16 docstring mention only, was two)
  - the persistent-freshness-note structural check's toggle assertions (aria-pressed, both label attributes, non-empty accessible label) replaced with zero-occurrence assertions for `data-refresh-toggle`/`data-pause-text`/`data-resume-text`/`<button` inside the wrapper, and the substring-ordering assertion drops the toggle position
  - `_both_tabs_ok_end_to_end`'s served-bytes needle tuple drops `("[data-refresh-toggle]", ...)` and gains an opposite-direction regression pin: the real served `freshness.js` bytes must carry zero occurrences of `data-pause-text`/`wireToggle`
- `EXPECTED_CHECK_COUNT` re-derived by running the harness after each task: 213 → 213 (net 0 both times — three checks rewritten in place, none added or removed)
- `ruff check .` clean; `companion/test_i18n.py` 22/22; `companion/test_status_pages.py` 212/213 (the one documented pre-existing root-sandbox `anomaly_active()` FAIL); `companion/test_view_pages.py` 105/105 (untouched by this plan, confirmed still green)

## Task Commits

1. **Task 1: Remove the Pause updates button from the Health page** - `e855ae4` (feat)
2. **Task 2: Delete the pause branch from freshness.js and retarget the served-script contract** - `627be3f` (feat)

_No separate plan-metadata commit at execution time — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete._

## Harness Counts (before → after)

| Harness | Before | After | Notes |
|---|---|---|---|
| `companion/test_status_pages.py` | 213 | 213 | net 0 — three checks rewritten in place across two tasks (Task 1: two checks, Task 2: one check), none added or removed |
| `companion/test_i18n.py` | 22 | 22 | unaffected — this plan's deletions were both-sides-of-the-commit (English constant + French entry together), so the dead-translation check needed no retargeting |
| `companion/test_view_pages.py` | 105 | 105 | unaffected — not in this plan's `files_modified`, confirmed still green |

Every harness's real on-disk pass count at execution time: `test_status_pages.py` 212/213 (the one documented pre-existing root-sandbox `anomaly_active()` FAIL), `test_i18n.py` 22/22, `test_view_pages.py` 105/105.

## Files Created/Modified
- `companion/pages/health_page.py` — deleted `REFRESH_PAUSE_TEXT`/`REFRESH_RESUME_TEXT` and their explanatory comment block; deleted `toggle_html`'s construction and its slot in `freshness_html`'s format tuple; updated the surrounding comment block to describe the smaller freshness line
- `companion/i18n_fr/health.py` — deleted `"Pause updates"`/`"Resume updates"` entries
- `companion/static/freshness.js` — deleted the `paused` variable, `setToggleVisual()`, `wireToggle()`, both call sites, both `if (paused)` guards; updated the header comment (new "SUPERSEDED (21-02-PLAN.md, D-18)" section) and the `AUTO_REFRESH_INTERVAL_MS`/background-tab-start comments to remove now-false claims about a pause state
- `companion/test_status_pages.py` — two checks rewritten in place (Task 1), one check rewritten in place (Task 2); `EXPECTED_CHECK_COUNT` 213→213 (Task 1) then 213→213 (Task 2), both net 0

## Decisions Made
- Rewrote checks in place rather than delete-and-replace, per the plan's own explicit instruction ("Do not delete the check — the freshness wrapper still needs its shape pinned").
- Reworded two of my own newly-added freshness.js comments to avoid literal `paused` (inside backticks) and a bare backtick character, since both would have tripped this same plan's own acceptance-criteria greps (`grep -c "paused\|..."` and the ES5-floor backtick grep) — see Deviations.

## Deviations from Plan

### Environment/setup deviation (not a code deviation)

**0. Worktree branch was forked before wave 1 (21-01) had merged**
- **Found during:** Startup, before Task 1
- **Issue:** This worktree's branch (`worktree-agent-a1d37857a45d878c8`) was created at `614d41e` (the tip of `main` before phase 21 began), not at `11b3fff` (the wave-1-merged tip of `claude/web-companion-audit-ux-refactor-bqx7si`) as the launch instructions described. The phase 21 planning directory and 21-01's simple-mode removal were therefore entirely absent from the worktree at start.
- **Fix:** Ran `git merge --ff-only claude/web-companion-audit-ux-refactor-bqx7si` from within the worktree, which fast-forwarded cleanly (no divergent commits) to `11b3fff`, bringing in the phase 21 planning docs and 21-01's merged changes. No `git stash`, `rebase`, or destructive operation was used.
- **Verification:** `git log --oneline -1` showed `11b3fff` before any file edit began.
- **Impact:** None on the plan's own scope — this was purely a worktree-setup correction, not a deviation from D-18 or the plan's tasks.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Own added comments would have tripped this plan's own acceptance-criteria greps**
- **Found during:** Task 2, immediately after writing the new D-18 header-comment section and the `AUTO_REFRESH_INTERVAL_MS` comment update
- **Issue:** My first draft of the new "SUPERSEDED (21-02-PLAN.md, D-18)" header note used the phrase `` a `paused` flag `` (literal word "paused" inside backticks). Task 1's acceptance criterion `grep -c "REFRESH_PAUSE_TEXT\|REFRESH_RESUME_TEXT\|data-refresh-toggle\|data-pause-text\|data-resume-text" companion/pages/health_page.py` doesn't cover this file, but Task 2's own acceptance criterion `grep -c "paused\|wireToggle\|setToggleVisual\|data-refresh-toggle" companion/static/freshness.js` outputs `0` would have failed on my own explanatory prose, and the backtick character would also have tripped the ES5-floor grep (`` \` ``) in the same acceptance criterion.
- **Fix:** Reworded to "a boolean state flag" (no literal "paused", no backticks) before running the grep checks.
- **Files modified:** `companion/static/freshness.js` (comment text only, no behavioral change)
- **Verification:** `grep -c "paused\|wireToggle\|setToggleVisual\|data-refresh-toggle" companion/static/freshness.js` → `0`.
- **Committed in:** `627be3f` (Task 2)

### Not Fixed — Flagged Instead

**2. One pre-existing, unrelated ES5-floor grep hit survives at freshness.js line 7**
- **Found during:** Task 2's own acceptance-criteria verification (`grep -cE "\b(let|const)\b|=>|\`" companion/static/freshness.js` — the ES5-floor check)
- **Issue:** This grep returns `1`, not `0`. The one hit is the file's own pre-existing top-of-file documentation line: `` * (no let/const/arrow functions/template literals/backticks) so no `` — a prose description of the ES5 constraint itself, using the words "let"/"const" as vocabulary, not as actual JavaScript syntax. Confirmed via `git show 11b3fff:companion/static/freshness.js` that this exact line predates this plan by many phases and this plan's diff never touched it.
- **Why not fixed:** This line is unrelated to D-18's removal (it documents the file's general ES5 constraint, not anything about the pause mechanism), and editing it was outside this task's actual scope (no acceptance criterion or interface note named line 7 for editing). Per the SCOPE BOUNDARY rule, pre-existing conditions unrelated to the current task's own changes are logged, not fixed.
- **Verification:** `grep -cE "\b(let|const)\b|=>|\`" companion/static/freshness.js` → `1`, and the same grep against the pre-plan commit (`11b3fff`) also returns `1` — proving this task introduced zero new hits.
- **Recommendation:** A future plan that touches this file's header comment for an unrelated reason could reword line 7 to avoid the literal words "let"/"const" (e.g., "no ES6+ binding keywords/arrow functions/template literals") if a byte-exact `0` on this specific grep is ever required by a future acceptance criterion.

**3. The DO-NOT-TOUCH proxy grep (`document.hidden\|visibilitychange\|stopLoop\|startLoop`) decreased from 16 to 13 lines matched, even though the actual DO-NOT-TOUCH function bodies are byte-identical**
- **Found during:** Task 2's own acceptance-criteria verification
- **Issue:** The plan's acceptance criterion says this grep's line-count should be "unchanged from before this task." It dropped by 3. Root cause, confirmed by reading the diff directly: the decrease comes entirely from deleting the `paused` variable's own explanatory comment (which mentioned "startLoop/stopLoop" in prose while describing the now-deleted interaction between the pause gate and the visibility gate) and from deleting `wireToggle()`'s click handler (which called `stopLoop()`/`startLoop()` as part of the now-deleted toggle behavior, not as part of the surviving visibility mechanism).
- **Why not "fixed":** There is nothing to fix — the actual `stopLoop()`, `startLoop()`, `intervalHandle`, `tick()`'s `if (document.hidden) { stopLoop(); return; }` guard, and the `visibilitychange` registration are all confirmed byte-identical to the pre-plan version (verified by direct line-range reads before and after editing, not just the proxy grep). The literal-count acceptance criterion is a mechanical proxy that happens to also catch legitimate, plan-authorized prose deletion inside the now-removed pause mechanism's own comments and call sites.
- **Verification:** Direct `Read` of `companion/static/freshness.js` lines covering `stopLoop()`, `startLoop()`, `tick()`, and the `visibilitychange` listener registration, compared against the same functions' bodies before this task's edits — identical apart from the authorized deletions inside the pause mechanism itself.
- **Recommendation:** None needed — this is expected friction from a mechanical proxy check, not a real regression.

---

**Total deviations:** 1 environment/setup correction (worktree fast-forward), 1 auto-fixed (Rule 3, own-comment grep self-trip), 2 flagged/not-fixed (1 pre-existing unrelated grep hit, 1 mechanical-proxy-grep friction with confirmed-intact actual code).
**Impact on plan:** No scope creep — every fix stayed within this plan's own D-18 removal; both flagged items are false positives against the plan's own mechanical proxy checks, with the actual DO-NOT-TOUCH code confirmed byte-identical by direct inspection.

## Known Stubs
None.

## Threat Flags
None — every threat this plan's own STRIDE register named (T-21-05 tampering/XSS, T-21-06 self-inflicted DoS, T-21-07 information disclosure) was mitigated/accepted exactly as the plan's threat model specified. No new sink was introduced (`applySwap()` still writes only into `REFRESH_SWAP_SELECTORS` targets from server-rendered bytes via `DOMParser`/`importNode`/`replaceChild` — no `innerHTML`, no inline handler, no `eval`), no new network-facing surface, and no schema change.

## Issues Encountered
- The plan's own acceptance-criteria grep commands scan raw file text, not parsed code — my own explanatory comments describing what was deleted and why tripped these greps purely by mentioning the deleted identifiers' literal spellings (same class of friction 21-01-SUMMARY.md documented). Resolved by rewording every avoidable occurrence into prose that doesn't spell out the literal token, while keeping the genuinely load-bearing literal matches the actual regression tests need (the new opposite-direction needle in `test_status_pages.py`, which must say `data-pause-text`/`wireToggle` verbatim to prove their absence).
- The worktree this plan launched in was forked before wave 1 had merged (see Deviation 0) — resolved by a clean fast-forward merge before any file edit began, verified via `git log --oneline -1` showing `11b3fff`.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Health's freshness line is now `{prefix} {clock} {pill}` with zero occurrences of the deleted Pause/Resume mechanism anywhere in `companion/pages/health_page.py`, `companion/i18n_fr/health.py`, or `companion/static/freshness.js`.
- The freshness loop runs unconditionally whenever a Health tab is visible; the tab-visibility mechanism (stopLoop/startLoop/intervalHandle, `tick()`'s `document.hidden` guard, the `visibilitychange` registration) is confirmed byte-for-byte unchanged.
- `companion/test_status_pages.py`'s pin is re-derived twice (once per task), both net 0, with a new opposite-direction regression check pinning that the pause branch cannot come back through the served `freshness.js` bytes undetected.
- Plan 21-03 (running concurrently in this wave on disjoint files: `history_page.py`, `flight-rows.js`, `list-filter.js`, `app.py`, `layout.py`, `style.css`, `i18n_fr/flights.py`, `test_view_pages.py`, `test_companion_app.py`) was never touched by this plan.
- `companion/test_i18n.py`, run by both plans and edited by neither in this wave, stayed at 22/22 throughout — no check was added or deleted there by this plan, matching the plan's own `files_owned` contract.

## Self-Check: PASSED

All claimed files exist on disk (`companion/pages/health_page.py`, `companion/static/freshness.js`, `companion/i18n_fr/health.py`, `companion/test_status_pages.py`, this SUMMARY.md) and both task commits (`e855ae4`, `627be3f`) are present in `git log --oneline --all`.

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*
