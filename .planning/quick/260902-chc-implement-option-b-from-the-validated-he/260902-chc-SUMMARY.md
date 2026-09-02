---
phase: quick-260902-chc
plan: 260902-chc
subsystem: companion-ui

tags: [companion, health-page, javascript, freshness, design-system, harness]

requires:
  - phase: 06.6.3
    provides: "D-12's original manual-Refresh/stale-banner pattern (health_page.py's _STALE_VIEW_BANNER_HTML, freshness.js's one-shot deferred-setTimeout reveal) — this task reverses it for Health only"
  - phase: 06.6.4.1
    provides: "Preview's retirement (merged into History; freshness.js's stale 'today only Health/Preview' claim, corrected here, referenced this)"
provides:
  - "A genuine light auto-refresh for Health: a named-interval (45s), Page-Visibility-gated location.reload() loop in freshness.js, replacing the manual Refresh link and the stale-view banner"
  - "REFRESH_PILL_TEXT / a hidden-by-default `<span data-refresh-pill>` in health_page.py's page-header freshness slot, revealed just before each reload"
  - "An interaction-skip guard (open <details>, focused INPUT/TEXTAREA/SELECT/SUMMARY, or a focused .sparkline-hit chart point) that suppresses a tick entirely rather than trying to restore state afterwards"
  - "A catch-up-on-return branch: a tab hidden longer than one interval refreshes immediately on becoming visible again, rather than waiting a full interval"
  - "The D-12 reversal recorded in the house SUPERSEDED idiom at both prose sites a harness can pin (freshness.js's header, 06.6.3-CONTEXT.md's D-12 entry) plus a third, harness-unpinned site (health_page.py's removal-site comment) — precise about reversing only the no-polling half, not the severity-stays-server-computed half"
  - "A written, unfixed verdict on battery-trend.js's _toggleActive() SVG className defect, investigated and left open per this task's explicit scope boundary"
affects: [companion-ui-implementation, health-page-freshness]

tech-stack:
  added: []
  patterns:
    - "Page-Visibility-gated location.reload() as the auto-refresh mechanism, chosen over a fetch-based soft-patch — the first genuinely timer-driven client-side loop in this codebase's static-asset JS files, deliberately reversing a standing 'no timer, no network call' constraint that used to apply file-wide"
    - "A reveal-then-defer-then-reload pattern (PILL_REVEAL_DELAY_MS) for a pre-navigation indicator, distinct from and explicitly NOT claiming parity with a fetch-duration indicator"
    - "SUPERSEDED-marker discipline (from this session's sketch-findings-skypane skill) applied to a standing architectural decision (D-12), not just a design-token value — recorded at the decision's own CONTEXT.md entry, the mechanism file's header, and the code removal site, each stating what was decided, what replaced it, and why"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/static/freshness.js
    - companion/test_status_pages.py
    - .planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md

key-decisions:
  - "Mechanism (a), Page-Visibility-gated location.reload(), was chosen over mechanism (b), a fetch-based soft-patch, for four source-grounded reasons recorded in freshness.js's own header: health_page.py's nav-dot/banner 'structurally impossible to disagree' claim only holds under a whole-page regeneration (the nav dot is emitted outside render(), by layout.page_shell()); battery-trend.js and list-filter.js each capture their DOM once in an IIFE with no re-init hook, so a patch would leave a permanently dead chart or filter; a patch needs an HTML-writing sink and a network sink, both banned by three existing harness guards in this repo; and (a) is roughly 40 lines against roughly 100 for (b). Mechanism (b)'s two genuine wins (a pill visible for the actual fetch duration; scroll/disclosure/focus preserved by construction) are named in the same comment, not hidden."
  - "The reversal is deliberately partial and the boundary is exact: only D-12's no-automatic-polling half is superseded, and only for Health. D-12's other half — authoritative severity stays server-computed only — is explicitly NOT reversed; it is strengthened, since a whole-page reload regenerates every verdict server-side and freshness.js still computes no health state of any kind. This precision is enforced by test_status_pages.py's own Check 1, which reads D-12's CONTEXT.md entry as a single block and asserts the original wording ('no automatic background polling') survives byte-identical beside the new SUPERSEDED note."
  - "The refresh interval (45000ms) sits inside the developer's own stated 30-60s band, anchored to two real numbers already in this codebase rather than a round figure: server/poll_loop.py's POLL_INTERVAL_S (30s, so a cadence at or below that is guaranteed-redundant against the pipeline's own writes) and health_page.py's STALE_PIPELINE_WARN_S (180s, so this cadence notices a newly-warn pipeline well inside a quarter of the threshold that defines it)."
  - "The pill hides by `visibility: hidden`, not `display: none`, deliberately diverging from `.dirty-bar[hidden]`'s own precedent in the same file — the dirty bar reveals at most once per editing session in response to a keystroke, while this pill reveals itself on a repeating timer with no user action, so a layout shift on reveal would read as a recurring header twitch rather than a one-off. Both approaches remove the element from the accessibility tree identically, so the no-ARIA-role decision is unaffected by the choice."
  - "The pill carries no ARIA role. A live region announces on content mutation, not on a visibility change, so a role=\"status\" pill whose text never changes would announce nothing anyway, and the page load it precedes is itself announced as a navigation by every screen reader. The one accessibility cost this mechanism cannot mitigate — a reload returning a screen-reader user's virtual cursor to the top of the document while they read with focus on the document body — is named in writing in both health_page.py's and freshness.js's comments, with the refresh interval as its only lever, and handed to a live screen-reader pass rather than hidden."
  - "battery-trend.js's _toggleActive() is investigated (Task 2, part E) but NOT fixed — outside this task's explicit scope boundary. See 'battery-trend.js SVG className Investigation' below for the full verdict."
  - "REFRESH_PILL_TEXT ('Updating…') is English-only, not the sketch's own bilingual label: this app renders every page `<html lang=\"en\">` and a grep of companion/ finds no French text anywhere, so the English half matches the shipped product. The single-character ellipsis follows this file's own sibling precedent, config_page.py's POLL_SUBMIT_PENDING_TEXT = 'Polling…'."

requirements-completed: [QUICK-260902-chc]

coverage:
  - id: health-auto-refresh
    description: "Health's manual Refresh link and stale-view banner are replaced by a visibility-gated, named-interval location.reload() loop with a hidden-by-default 'Updating…' pill, an interaction-skip guard, and a catch-up-on-return branch"
    requirement: QUICK-260902-chc
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_pill_markup_contract (new) — pill markup on a real render, both seeded and on a fresh state directory with no readings"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_pill_stylesheet_contract (new) — the [hidden] override hides by visibility, no display value, reserved line box"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_loop_contract_guard (new) — freshness.js's shipped source: interval band, pause+visibility halves, double-start guard, no-arg reload, every pre-existing sink/nav/ES5 discipline except the deliberately-lifted timer ban"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_skip_guard_cross_file_contract (new) — a fixture rendering a disclosure/filter input/chart hit target, and freshness.js's source still referencing each literal"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py::_both_tabs_ok_end_to_end (extended in place) — real /health response carries the hidden pill and zero stale-banner markers; real fetch of FRESHNESS_SCRIPT_ROUTE carries AUTO_REFRESH_INTERVAL_MS and the visibilitychange listener"
        status: pass
    human_judgment: true
    rationale: "This is a polling loop, a visibility listener, and a transient reveal — behaviour that by construction leaves no trace in any HTTP response body, since everything it does happens after the response is served. Whether the interval actually fires, whether backgrounding actually pauses it, whether the pill actually paints without a layout shift, whether the skip guard actually skips, whether scroll survives, and the screen-reader cost are all outstanding for a live-browser pass. See 'Live-Browser Handoff' below for the full 12-item list."
  - id: d12-reversal-recorded
    description: "The D-12 reversal is recorded in the house SUPERSEDED idiom, precise about which half is reversed, at all three points the old rule was stated"
    requirement: QUICK-260902-chc
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_reversal_recorded_in_both_places (new) — freshness.js's header and 06.6.3-CONTEXT.md's D-12 entry, positive assertions only, original wording intact"
        status: pass
    human_judgment: false
    rationale: "Fully verifiable from source — no rendering or runtime behaviour involved. health_page.py's own removal-site comment is a third recorded site (per the plan's truths) but is not separately harness-pinned, since Check 1 was scoped by the plan to the two prose files (freshness.js, CONTEXT.md)."

duration: ~50min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-chc: Implement Option B from the Validated Health Auto-Refresh Sketch Summary

**Health's manual Refresh link and "this view may be out of date" stale banner are replaced with a genuine light auto-refresh — a visibility-gated `location.reload()` loop on a 45-second interval, with a hidden-by-default "Updating…" pill, an interaction-skip guard protecting open disclosures/focused controls, and a catch-up branch on tab return — deliberately reversing 06.6.3's D-12 (no automatic background polling) for Health alone, with the reversal written down at every point the old rule was stated.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Files modified:** 5 (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/static/freshness.js`, `companion/test_status_pages.py`, `06.6.3-CONTEXT.md`)

## Accomplishments

- **Task 1 — the pill replaces the Refresh link and the stale banner:** `health_page.py` gained `REFRESH_PILL_TEXT = "Updating…"` (English-only, matching `config_page.py`'s `POLL_SUBMIT_PENDING_TEXT` precedent) and `render()`'s `freshness_html` now emits a hidden-by-default `<span class="refresh-pill" data-refresh-pill data-loaded-at="..." hidden>` in place of the manual `<a href="/health" class="freshness-refresh">`. `_STALE_VIEW_BANNER_HTML` is deleted outright, its D-12/UXA-13 comment block replaced at the same location with the reversal record (what D-12 decided, why the developer reversed it for Health after real use, why the banner could only have become a lie, and that the severity-stays-server-side half is explicitly NOT reversed). `style.css` gained `.refresh-pill` (a second `.banner__pill` call site), the load-bearing `.refresh-pill[hidden]` override (hides by `visibility`, not `display`, answering the exact `.dirty-bar[hidden]` collision its own comment documents), and a pill-scoped icon-size override. Three existing harness checks were retargeted in place (the D-12 refresh/stale-banner check rewritten as the reversal's own rendered-output guard; the page-purpose ordering check's lookup moved onto the pill's marker attribute; the five-icon check's comment/message updated). `layout.page_header()` was not touched — Health is its sole `freshness_html` caller, confirmed by a repo-wide grep.
- **Task 2 — the refresh loop and the written reversal:** `freshness.js` was rewritten from a one-shot deferred-`setTimeout` banner reveal into a named-interval (`AUTO_REFRESH_INTERVAL_MS = 45000`), Page-Visibility-gated `location.reload()` loop, gated on the pill attribute instead of the retired banner. An interaction-skip guard suppresses a tick while any `<details open>` exists or while the active element is an `INPUT`/`TEXTAREA`/`SELECT`/`SUMMARY`, or carries the `sparkline-hit` class (read via `getAttribute("class")`, never the `.className` property, since SVG's `className` is an `SVGAnimatedString`). A tab-visibility listener stops the interval on hide and, on return, refreshes immediately if more than one interval has elapsed since the page's own `data-loaded-at` instant. `location.reload()` uses the no-argument form only — no URL-taking navigation form appears anywhere in the file, asserted directly. The rewritten header records the D-12 reversal in the house SUPERSEDED idiom, names both candidate mechanisms with the losing one's genuine advantages, lists mechanism (a)'s accepted costs (including the one it cannot mitigate — a screen reader's virtual-cursor reset on reload), and corrects the stale "today only Health/Preview" claim now that Preview is retired (06.6.4.1, D-22/D-26). `06.6.3-CONTEXT.md`'s D-12 entry gained an appended SUPERSEDED note, scoped precisely to the no-polling half and to Health only, with the original decision sentence left byte-identical.
- **Task 3 — the contract pinned, the browser handoff written:** 5 new checks added to `test_status_pages.py` (`EXPECTED_CHECK_COUNT` 84 → 89): the D-12 reversal recorded in both prose files (positive assertions only, no ban on old wording — both files legitimately discuss the old rule while explaining why it changed); the loop's own contract from freshness.js's shipped source (interval band, pause+visibility halves, double-start guard, no-arg reload, and every pre-existing sink/navigation/ES5 discipline still holding except the deliberately-lifted timer ban, with the asymmetry stated explicitly in the check's own comment); the pill's markup contract on a real render, both seeded and on a fresh state directory with zero readings (proving the pill unconditional, not coupled to the battery chart's own render branch); the pill's stylesheet contract; and the interaction-skip guard's cross-file DOM contract (a fixture rich enough to actually render a disclosure, a filter input and a chart hit target, with freshness.js's source still referencing each literal — this guard's failure mode is silence, so this is the only thing that would notice a drift). Section 3's `_both_tabs_ok_end_to_end()` was extended in place (no count change): the real `/health` response now asserted to carry the hidden pill exactly once and zero stale-banner markers, and a new real fetch of `companion/app.py`'s `FRESHNESS_SCRIPT_ROUTE` proves the served script — not just the on-disk file — carries `AUTO_REFRESH_INTERVAL_MS` and the `visibilitychange` registration. All 5 new checks were independently mutated (one bogus literal each, via a temporary file copy) and confirmed to fail — exactly those five and no others (84/89) — before being restored to the real, green source.
- **battery-trend.js investigation (Task 2, part E) — verdict recorded, no fix shipped:** see "battery-trend.js SVG className Investigation" below.

## Task Commits

1. **Task 1:** `0c3a4de` — `feat(quick-260902-chc): replace Health's manual Refresh with an updating pill` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`
2. **Task 2:** `f5e34d2` — `feat(quick-260902-chc): auto-refresh Health while its tab is visible` — `companion/static/freshness.js`, `.planning/phases/06.6.3-.../06.6.3-CONTEXT.md`
3. **Task 3:** `1b3414b` — `test(quick-260902-chc): pin the Health auto-refresh contract, EXPECTED_CHECK_COUNT +5` — `companion/test_status_pages.py`

## Files Created/Modified

- `companion/pages/health_page.py` — `REFRESH_PILL_TEXT` constant added; `_STALE_VIEW_BANNER_HTML` deleted, its comment block replaced with the D-12 reversal record; `render()`'s `freshness_html` rebuilt as the hidden-by-default pill; the ARIA-role decision (and its one accepted cost) recorded in a comment at the pill's construction site
- `companion/static/style.css` — `.refresh-pill` (after `.banner__pill`), `.refresh-pill[hidden]` (hides by visibility, answering `.dirty-bar[hidden]`'s own documented collision), `.refresh-pill .icon` (scoped icon size)
- `companion/static/freshness.js` — rewritten in full: header now records the D-12 reversal and the mechanism decision; two named constants (`AUTO_REFRESH_INTERVAL_MS`, `PILL_REVEAL_DELAY_MS`) replace the retired `STALE_VIEW_THRESHOLD_MS`; the interaction-skip guard, the start/stop/tick functions, the visibility listener with its catch-up branch, and the initial guarded start are new
- `companion/test_status_pages.py` — 5 new checks; 3 in-place retargets (Task 1); 1 in-place live-HTTP extension (Task 3); `EXPECTED_CHECK_COUNT` 84 → 89
- `.planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md` — D-12's entry gained an appended SUPERSEDED note; original wording untouched

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on the mechanism choice (with mechanism (b)'s genuine advantages named), the precise scope of the D-12 reversal, the interval's numeric justification, the visibility-vs-display hiding choice, the no-ARIA-role decision and its one unmitigated cost, and the battery-trend.js scope boundary.

## battery-trend.js SVG className Investigation

**What was checked:** `battery-trend.js`'s `_toggleActive(el, isActive)` (lines 104-115) reads and writes `el.className` as a plain string — `el.className = el.className + cls` (add) and a `.split("...").join("...")` rebuild (remove) — on `.sparkline-hit` elements, which are `<circle>` SVG elements (`SVGCircleElement`, an `SVGElement`). This file's own `"use strict";` directive (line 24) is in effect for the whole IIFE, including this function.

**What was concluded (source/spec-based; no live browser check was available in this environment — see "Issues Encountered" below):** `SVGElement.className` (as distinct from `HTMLElement.className`) is specified as a read-only accessor returning an `SVGAnimatedString`, not a writable plain-string property — this is exactly the same fact `reveal()`'s own comment in this file already cites as the reason it uses `getAttribute()` rather than `dataset`/property access on SVG elements. Under strict mode, an assignment to an accessor property with no setter throws `TypeError` (browsers commonly phrase this as "Cannot set property className of [object SVGCircleElement] which has only a getter" or equivalent). If this holds as specified, `_toggleActive()`'s `el.className = ...` line throws the first time a point transitions active/inactive — which happens inside a `click`/`mouseenter`/`focus` event listener with no surrounding `try`/`catch`, so the browser logs an uncaught exception for that specific listener invocation and the remainder of that call aborts. Because `reveal()` writes the readout's `textContent` (the value/detail spans) *before* the loop that calls `_toggleActive()`, the readout text itself would keep working correctly even if this throws — only the `sparkline-hit--active` visual highlight on the chart point would silently fail to toggle, on every hover/tap/keyboard move, for every chart on every Health page load.

**The one-line change it would need, if confirmed live:** replace the two `el.className = ...` assignments with `el.setAttribute("class", ...)` / read via `el.getAttribute("class")` instead — mirroring `reveal()`'s own already-established getAttribute-not-property discipline for SVG elements in this same file.

**Not fixed here, deliberately:** this is outside 260902-chc's stated scope boundary (Task 2, part E: "Change nothing in that file — it is outside this task's stated scope boundary"). Recorded as its own open finding for a future task, not silently closed and not silently dropped.

## Known Stubs

None. Every value the pill/loop touches is real: `data-loaded-at` carries the real request-scoped `now`; `REFRESH_PILL_TEXT` is a real static constant rendered verbatim; the interval and reveal-delay constants are real, named, and referenced by the harness against the shipped source; the interaction-skip guard's literals (`SPARKLINE_HIT_CLASS`, the disclosure/form-field tag names) are asserted against the real markup `health_page.py` renders, not invented.

## Threat Flags

None beyond what this task's own `<threat_model>` (T-chc-01 through T-chc-07, all `mitigate`, plus T-chc-SC `accept` for the zero-package-install non-goal) already covers — the new request-volume surface (bounded by the visibility gate and the pill-attribute scope gate), the reload's navigation target (no-argument form only, asserted), the pill markup's own escaping (only `now` is dynamic, escaped exactly as the retired Refresh link's own `data-loaded-at` was), interval-stacking (the double-start guard), the interaction-skip guard's own silent-failure mode, the `[hidden]` override's integrity, and the standing-constraint reversal itself (T-chc-07, mitigated by the written record this task ships). No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary was introduced — the reload is a same-document navigation of the already-authenticated page the user is looking at.

## Issues Encountered

- No package installs, no auth gates, no architectural questions (Rule 4 was never triggered — this task's own plan already made and recorded the mechanism decision).
- No computer-use/chrome-devtools MCP tools were bound to this subagent, matching the three immediately-prior Health quick tasks' (260901-tsa, 260901-uzi, 260902-bl2) own precedent — and this task's own untestable-from-harness surface is explicitly larger than any of theirs (see "Live-Browser Handoff" below).
- The `battery-trend.js` `_toggleActive()` investigation above is spec/documentation-based, not an empirical live-browser or `jsdom` check: no Node `jsdom`/browser-automation tooling was available in this environment without installing a new package, and installing a new dependency to investigate a file this task is scoped NOT to fix would itself be scope creep. The verdict is stated with that caveat rather than asserted as directly observed.

## Live-Browser Handoff — 12 Items Outstanding

This task's harness (automated: freshness.js's shipped source contract, the pill's markup/stylesheet contract, the interaction-skip guard's cross-file literals, and a real HTTP fetch proving both the pill markup and the new script body are actually served) covers everything that can be proven from source or an HTTP response body. It structurally CANNOT settle behaviour that only exists after the response has been served — a polling loop, a visibility listener, and a transient reveal. The orchestrating session's live-browser pass, with the network panel open throughout, must confirm all twelve, and record what was actually observed rather than restating this list as if performed:

1. **The interval actually fires.** Leave `/health` open and focused; confirm a request appears roughly once per 45s — not never, not twice.
2. **Backgrounding actually pauses it.** Switch tabs for several minutes; confirm ZERO `/health` requests during that time — this is the whole request-volume argument the reversal rests on.
3. **Returning actually catches up.** Come back after longer than one interval; confirm an immediate refresh, not a wait for a further full interval.
4. **No stacking.** Toggle tab visibility five or six times in a row, then watch one full interval; confirm exactly ONE reload, not three — the double-start guard's whole reason to exist.
5. **The pill actually paints, with no layout shift.** Watch the header across a refresh; confirm the pill visibly appears before the page changes, and the header does not shift when it appears (the reserved line box is the point of the visibility-based hiding).
6. **The pill is hidden at rest.** On a freshly loaded page, confirm no flash of visible pill and no pill visible while idle.
7. **The skip guard actually skips**, in all three cases, each observed for at least one full interval: the readings-history disclosure open; Corroboration's "More details" open; text typed into the registry filter input; keyboard focus on a battery-chart point after arrowing to it. Confirm no reload in each case, then confirm refreshing resumes after closing/blurring.
8. **Scroll survives** — in BOTH Safari and a Chromium browser. Scroll down, wait for a refresh, report whether position is preserved (recorded here as an expectation per the browser's own session-history scroll restoration, not asserted as fact).
9. **The nav dot stays in step** with the page's own banner/tile borders across a refresh where severity changes — the invariant that decided the mechanism in the first place.
10. **A screen-reader pass** (VoiceOver or equivalent): read partway down the page, let a refresh fire, report where the cursor lands and how disruptive it is — the one accepted cost the guard cannot cover; the developer's judgement on it decides whether the interval needs lengthening.
11. **No console errors across several cycles, and no unexpected logout** — a reload against an expired session should land on `/login` (fail-closed, correct), but should be observed, not assumed.
12. **Perceptual read: calm and live, or twitchy?** A judgement the developer owns; the lever is `AUTO_REFRESH_INTERVAL_MS`, a one-line change.

Additionally, per the battery-trend.js investigation above: confirm (or refute) in a real browser console whether `_toggleActive()`'s `el.className = ...` assignment actually throws on `.sparkline-hit` circles, and whether the active-point highlight visibly fails to toggle as a result — this was not independently re-verified here.

## User Setup Required

None to run the code. **Recommended before signing off:** the 12-item live-browser pass above, on `/health`, covering both Safari and a Chromium browser (item 8 specifically needs both), plus a screen-reader pass (item 10) and, if time allows, a real-console check of the battery-trend.js finding.

## Next Phase Readiness

Health's auto-refresh mechanism (Option B) is fully implemented and pinned by harness: `companion/test_status_pages.py` 89/89; `companion/test_companion_app.py` 105/105; `companion/test_view_pages.py` 43/43; `companion/test_config_page.py` 61/61. `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing, unrelated `server/test_poll_loop.py` panel.bin digest mismatch, with no coverage-gate shortfall. The D-12 reversal is recorded at all three prose sites the old rule was stated (freshness.js's header, health_page.py's removal-site comment, 06.6.3-CONTEXT.md's D-12 entry), precise about which half is reversed. The 12-item live-browser handoff above — plus the battery-trend.js SVG className finding — are the concrete next actions for the orchestrating session before this can be considered visually/behaviourally verified, not just source-verified.

---
*Phase: quick-260902-chc*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 5 modified files (companion/pages/health_page.py, companion/static/style.css, companion/static/freshness.js, companion/test_status_pages.py, .planning/phases/06.6.3-.../06.6.3-CONTEXT.md) confirmed present on disk. All 3 task commit hashes (0c3a4de, f5e34d2, 1b3414b) confirmed present in git log.
