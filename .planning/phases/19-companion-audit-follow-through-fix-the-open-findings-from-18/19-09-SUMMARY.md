---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 09
subsystem: ui
tags: [companion, health-page, freshness, fetch-and-swap, accessibility, dom-security]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "19-01 (wave 1): the widget-verdict/stat-tile idiom; 19-04 (wave 2): the CSP (script-src 'self') this rewrite's fetch()/DOMParser mechanism must stay compatible with, and the poll-cooldown.js data-* attribute contract this plan's own data-pause-text/data-resume-text attributes follow; 19-05 (wave 2)/19-06 (wave 3): health_page.py's render() freshness assembly this plan edits in place"
provides:
  - "companion/pages/health_page.py — FRESHNESS_PREFIX_TEXT ('Updated '), REFRESH_PAUSE_TEXT/REFRESH_RESUME_TEXT, and REFRESH_SWAP_SELECTORS (the single greppable swap-target definition)"
  - "an honest 'Updated HH:MM' freshness line (full ISO in a title attribute, no relative-age suffix) plus a visible Pause/Resume button, both inside the existing .page-header__freshness wrapper with no new CSS"
  - "companion/static/freshness.js rewritten as a fetch-and-swap refresh: no location.reload anywhere, DOMParser/replaceChild/importNode swap only the documented targets (including the nav severity dot's whole link in both nav renderings), the sparkline/registry/filter/every <details> are excluded, the battery readout's two spans update via textContent only"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fetch(window.location.href, {redirect: 'manual'}) as the same-document, non-URL-taking refresh target, with an opaque-redirect response folded into the existing non-OK-status failure branch rather than a separate code path"
    - "index-paired querySelectorAll swap: for a fixed selector list, replace document A's node[i] with an importNode() clone of document B's node[i] only when the index exists on both sides — a conditionally-rendered region (a banner, a nav dot) that appears/disappears between polls is left untouched rather than erroring"
    - "re-query-on-every-call DOM lookups (revealPill()/hidePill()/wireToggle()) instead of a module-level cached reference, because the referenced element sits inside a region this same file swaps out from under itself"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/freshness.js
    - companion/test_status_pages.py
    - companion/test_companion_app.py

key-decisions:
  - "D-02/A-20: FRESHNESS_PREFIX_TEXT ('Updated ') replaces PERSISTENT_FRESHNESS_PREFIX_TEXT ('Live — refreshed '); the timestamp itself is now layout.local_clock_text(parsed, now_parsed=parsed) — passing the same parsed value as both arguments always takes the 'same local day' branch, so the line is always a bare clock time, never a relative-age suffix, while the full ISO instant survives in the span's title"
  - "REFRESH_SWAP_SELECTORS' nav-severity target is the whole Health nav link (a[href=\"/health\"]), not a dot-only selector — the dot only exists in the DOM for warn/error severity, so a dot-only selector would have nothing to replace on the far more common transition where severity newly clears; swapping the whole link handles every transition uniformly"
  - "The anomaly-banner/source-fault-block selectors are div.banner--anomaly, div.banner--warn and section.banner (not a bare .banner) specifically to avoid colliding with layout.flash_banner()'s own div.banner.banner--flash, which could in principle render on the same page shell"
  - "revealPill()/hidePill()/wireToggle() re-query [data-refresh-pill]/[data-refresh-toggle] on every call rather than caching a reference at load time — both elements live inside .page-header__freshness, one of this file's own swap targets, so a cached reference goes stale (detached, inert) the moment the first successful swap replaces that wrapper; this was not spelled out in the plan's action text and is documented as a Rule 1 fix below"
  - "T-19-34 mitigation: fetch() is called with redirect: 'manual' (not the plan text's literal example options alone) so a same-origin 303 (an expired session) resolves to an opaque response with ok=false instead of being silently followed to the login page's 200 body — folded into the existing 'non-OK status' branch with no separate code path, closing the exact threat the plan's own threat_model marks 'mitigate'"
  - "The two swap-target-adjacent pinned checks the freshness.js rewrite legitimately broke (the loop's own contract requiring the retired reload form; the interaction-skip guard requiring the retired details[open] clause) were retargeted in place rather than left failing — both are direct, foreseeable consequences of Task 2's own instructed changes"

requirements-completed: [CFG-03]

# Metrics
duration: 14min
completed: 2026-09-11
---

# Phase 19 Plan 09: Health freshness fetch-and-swap refresh Summary

**Health's freshness line now reads an honest "Updated HH:MM" (no more structurally-always-zero "(0s ago)"), a visible Pause/Resume button stops and restarts polling, and the retired 45-second location.reload() is replaced by a DOMParser-based fetch-and-swap that only ever replaces the documented dashboard-grid/banner/freshness-line/nav-link regions — never the sparkline, the registry, its filter, or any open disclosure.**

## Performance

- **Duration:** 14 min (2026-09-11T08:29:06Z first task commit → 2026-09-11T08:43:16Z last task commit)
- **Started:** 2026-09-11T08:29:06Z
- **Completed:** 2026-09-11T08:43:16Z
- **Tasks:** 3/3 complete
- **Files modified:** 4

## Accomplishments

- Closed A-20 (D-02): Health no longer reloads itself every 45 seconds. `companion/static/freshness.js` fetches its own page (`credentials: "same-origin"`, `redirect: "manual"`), parses the response with `DOMParser` (never an HTML-writing sink), and swaps only `health_page.REFRESH_SWAP_SELECTORS`' own documented targets — the two `.dashboard-grid` regions, the anomaly banner, the source-fault block, the freshness line, and the nav severity dot's whole link in both nav renderings — plus updates the battery readout's two spans via `textContent` on the existing nodes (skipped while a chart point is actively revealed).
- The freshness line now reads "Updated HH:MM" with the full ISO instant in a `title` attribute — no relative-age suffix, ever. A visible `data-refresh-toggle` Pause/Resume button lives inside the same wrapper, reusing the bare `button` element's existing quiet-button styling with zero new CSS.
- An open `<details>` disclosure, a mid-typed registry filter query, and the battery sparkline's hover/focus state all survive a refresh cycle unconditionally, because none of those regions is ever a swap target — not because of a suspended-polling guard (that guard, and the silent suspension it caused, is deleted outright).
- A non-OK or opaque-redirect fetch response (an expired session's 303, correctly surfaced via `redirect: "manual"` rather than silently followed) hides the pill and stops the loop, leaving the stale page visible rather than risking a partial swap or mistaking a login page for fresh data.
- `fetch(`/`setTimeout`/`setInterval` are now `freshness.js`'s own single, named, reviewed exception to the sibling static scripts' forbidden-sink/timer ban — pinned by name in `test_companion_app.py`, with the standing HTML-writing-sink ban (no `innerHTML`/`insertAdjacentHTML`/`document.write`/`eval(`) still absolute for this file too.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make the freshness line honest and add a Pause/Resume control (D-02, server half)** - `e70b808` (feat)
2. **Task 2: Rewrite freshness.js as a fetch-and-swap refresh with no HTML-writing sink (D-02)** - `85541ed` (feat)
3. **Task 3: Pin the new freshness contract and its one reviewed sink exception** - `bf969b9` (test)

_No plan-metadata commit yet — SUMMARY.md and this plan's metadata commit follow this file's own creation, per worktree-mode instructions._

## Files Created/Modified

- `companion/pages/health_page.py` — `PERSISTENT_FRESHNESS_PREFIX_TEXT` retired (kept as a SUPERSEDED comment record); `FRESHNESS_PREFIX_TEXT`/`REFRESH_PAUSE_TEXT`/`REFRESH_RESUME_TEXT`/`REFRESH_SWAP_SELECTORS` added; `render()`'s freshness assembly now emits a clock-only `data-refresh-clock` span and a `data-refresh-toggle` button inside the existing `.page-header__freshness` wrapper
- `companion/static/freshness.js` — full rewrite: the `260902-chc` mechanism decision marked SUPERSEDED in place with each of its four original reasons answered; `location.reload` deleted entirely; a fetch-and-swap mechanism (`swapNodes()`, `swapBatteryReadout()`, `updateLoadedAt()`, `wireToggle()`) replaces it, index-paired against `SWAP_SELECTORS` (duplicated verbatim from `health_page.REFRESH_SWAP_SELECTORS`); `userIsInteracting()`'s `details[open]` clause deleted; a `paused` flag gates both the tick loop and the visibilitychange catch-up branch
- `companion/test_status_pages.py` — the persistent-freshness-note check retargeted in place for the new copy/clock/toggle contract; the "exactly one `<button` literal" no-state-changing-control check retargeted to two (the docstring mention plus the new formless toggle); the loop's-own-contract and interaction-skip-guard cross-file checks retargeted in place for the rewrite; the real-running-service served-script check extended with the three new attribute-hook needles plus every `REFRESH_SWAP_SELECTORS` entry; one new check added (both-directions swap-selector-contract, including the excluded-selector absence assertions); `EXPECTED_CHECK_COUNT` 190 → 191
- `companion/test_companion_app.py` — two new checks added: `freshness.js`'s own named ES5/sink guard (with the `fetch`/timer exception stated in its own body) and a URL-taking-navigation-form absence check; `EXPECTED_CHECK_COUNT` 211 → 213

## Decisions Made

- `REFRESH_SWAP_SELECTORS`' nav-severity target is the whole `a[href="/health"]` link, not a dot-only selector — see key-decisions above for why a dot-only selector would fail on the far more common "severity just cleared" transition.
- The anomaly-banner/source-fault-block swap selectors are `div.banner--anomaly, div.banner--warn` and `section.banner`, deliberately more specific than a bare `.banner`, to avoid an ambiguous match against `layout.flash_banner()`'s own `div.banner.banner--flash` (which theoretically could render on the same page shell via a stale flash cookie, even though Health has no POST route of its own that sets one).
- `redirect: "manual"` was added to the `fetch()` call beyond the plan's literal example options, closing T-19-34 (session-expiry redirect silently treated as fresh data) as an explicit `response.ok === false` case rather than leaving `fetch()`'s default redirect-following behavior in place.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pill/toggle DOM references re-queried on every call instead of cached**
- **Found during:** Task 2, while implementing the swap mechanism
- **Issue:** The plan's Task 1 places the pill and the new toggle button inside `.page-header__freshness`, and Task 2 lists that same selector as a SWAP target. A cached `pill`/`toggle` variable (the original file's own pattern) would go stale — detached from the live document — the moment the first successful swap replaced that wrapper, silently breaking `revealPill()`/`hidePill()` after exactly one refresh cycle and leaving the Pause/Resume button permanently unresponsive after the same event.
- **Fix:** `revealPill()`/`hidePill()` now call `document.querySelector("[data-refresh-pill]")` fresh on every invocation; `wireToggle()` is called once at startup and again after every successful swap, re-attaching its click listener to the freshly swapped-in button node.
- **Files modified:** companion/static/freshness.js
- **Verification:** `python3 -m companion.test_status_pages` (190/191, the one documented pre-existing failure) and `python3 -m companion.test_companion_app` (211/213, the two documented pre-existing failures) both pass; manual code trace confirms `wireToggle()` runs post-swap.
- **Committed in:** `85541ed` (Task 2 commit)

**2. [Rule 1 - Bug] Comment text tripped the very forbidden-sink checks it was explaining**
- **Found during:** Task 2 verification and Task 3 harness runs
- **Issue:** `freshness.js`'s own header/inline comments literally spelled out banned tokens while explaining that they are absent (`innerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `location.reload`, a bare backtick, and the exact substring `location.href =`) — the same false-positive class 19-04-SUMMARY.md already documented for `poll-cooldown.js`'s header. Both this plan's own Task 2 verification script and several pinned harness checks (in `test_status_pages.py` and, once added, `test_companion_app.py`) treat comments and code identically.
- **Fix:** Reworded every affected comment to describe the same constraints without using the literal banned substrings (e.g. "the standing markup-writing-sink ban" instead of naming the four sinks; "an assignment to the page's own location, or a call to assign/replace/open" instead of the literal `location.href =` form; prose descriptions instead of backtick-wrapped code spans).
- **Files modified:** companion/static/freshness.js
- **Verification:** `grep -c '\`' companion/static/freshness.js` → 0; Task 2's own verification one-liner reports no forbidden tokens; `python3 -m companion.test_status_pages` and `python3 -m companion.test_companion_app` both pass at their documented pre-existing-failure counts.
- **Committed in:** `bf969b9` (Task 3 commit, alongside the harness that caught it)

**3. [Rule 1 - Bug] Two pre-existing pinned checks retargeted for the freshness.js rewrite's own direct, foreseeable consequences**
- **Found during:** Task 3, running `test_status_pages.py` after Task 2's rewrite
- **Issue:** `_quick_260902_chc_loop_contract_guard` asserted `location.reload()` MUST be present and `fetch(`/`XMLHttpRequest` MUST be absent — both now backwards after the D-02 rewrite. `_quick_260902_chc_skip_guard_cross_file_contract` asserted `details[open]` MUST be present — also now backwards, since D-02 deletes that clause by name. Both checks are direct consequences of Task 2's own instructed action text, not incidental breakage.
- **Fix:** Retargeted both checks in place (same function/check name, same overall shape): the loop-contract check now requires the reload form absent and `fetch(`/`DOMParser`/`replaceChild`/`importNode` present, with `fetch(` removed from its own forbidden-sink list; the skip-guard check now requires `details[open]` absent instead of present.
- **Files modified:** companion/test_status_pages.py
- **Verification:** `python3 -m companion.test_status_pages` — 189/190 before the Task 3 addition, 190/191 after (only the one documented pre-existing failure both times).
- **Committed in:** `bf969b9` (Task 3 commit)

**4. [Rule 1 - Bug] A pre-existing "Health has no state-changing control" check retargeted for the new Pause/Resume button**
- **Found during:** Task 1, running `test_status_pages.py` after adding the toggle button
- **Issue:** `_health_still_has_no_form_and_exactly_one_button_literal` (phase 13, T-13-13) asserted exactly one `<button` substring occurrence in `health_page.py`'s own source (a pre-existing docstring mention) and zero `<form` occurrences. The new Pause/Resume button is a second real `<button` occurrence.
- **Fix:** Retargeted the check in place to require exactly two `<button` occurrences, with a comment explaining that the new button is still compatible with T-13-13's own promise: it is bare, formless, and submits nothing anywhere — not a state-changing control in the sense the check polices. The zero-`<form>` half is unchanged and still the check's real teeth.
- **Files modified:** companion/test_status_pages.py
- **Verification:** `python3 -m companion.test_status_pages` — passes after the retarget.
- **Committed in:** `e70b808` (Task 1 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 — bugs/false-positives/pinned-check drift directly caused by this plan's own instructed changes)
**Impact on plan:** All four fixes were necessary to keep the harness accurate and green at the plan's own stated verification target (exactly one/two documented pre-existing root-sandbox failures per file). None changes the plan's intent or scope.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

**Outstanding for end-of-phase closure (not this plan's own responsibility to run):** the plan's `<verification>` section names a required `<human-check>` — with the service running, open Health in a real browser and confirm the page never navigates, "Updated HH:MM" advances, an open disclosure survives an update, keyboard focus is not lost, the sparkline still responds to hover/arrow-keys after an update, a typed registry filter query survives an update, the nav Health dot matches the on-page banner, Pause/Resume actually stops/restarts updates, and the browser console shows no CSP violation. This requires a running browser session this execution environment does not have; it is named here so the phase's end-of-wave closer does not skip it.

## Next Phase Readiness

- `health_page.REFRESH_SWAP_SELECTORS` is the single, pinned, greppable definition any future edit to Health's freshness mechanism must keep in agreement with `freshness.js`'s own `SWAP_SELECTORS` array — `companion/test_status_pages.py`'s new both-directions check will catch a drift immediately.
- `freshness.js`'s `fetch(`/timer exception is documented and pinned by name (`test_companion_app.py`); a future static script that also needs a network read should get its own explicit, reviewed exception rather than silently copying this one's ban-list carve-out.
- `scripts/run-all-tests.sh` run in full: the same 3 pre-existing-failure harnesses as an untouched checkout (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — all root-sandbox read-only-directory/`anomaly_active()` artifacts), zero new failures. No blockers for the rest of this wave (19-08 owns `airlines_page.py`/`app.py`/`test_view_pages.py`; 19-10 owns `static/dirty-state.js`/`style.css`/`config_page.py`/`test_config_page.py` — neither file set overlaps this plan's).

## Self-Check: PASSED

- FOUND: companion/pages/health_page.py
- FOUND: companion/static/freshness.js
- FOUND: companion/test_status_pages.py
- FOUND: companion/test_companion_app.py
- FOUND commit e70b808
- FOUND commit 85541ed
- FOUND commit bf969b9

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 09*
*Completed: 2026-09-11*
