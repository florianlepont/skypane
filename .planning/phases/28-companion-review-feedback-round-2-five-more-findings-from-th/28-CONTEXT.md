# Phase 28: Companion review feedback round 2 — Context

**Gathered:** 2026-09-15
**Status:** Ready for planning
**Source:** Developer hands-on review of the deployed Phase 27 app, investigated live before scoping (Explore agents, direct Playwright interaction against a real running instance), plus two rounds of developer follow-up that escalated two of the five items, plus two AskUserQuestion decisions (carousel behavior; how to handle the unconfirmed Safari save failure).

<domain>
## Phase Boundary

Five findings from the developer's hands-on review of the deployed app, five items in scope after two escalations:
- CFG-72 (titles): confirmed defect, straightforward fix.
- CFG-73 (dial): confirmed defect, TWO distinct bugs in the same control (readout format + handle position), both root-caused precisely.
- CFG-74 (save reliability): escalated from "not reproduced" to the most severe item in the phase — CONFIRMED, total auto-save failure in real Safari (iPhone and Mac, all settings pages), root cause NOT confirmable remotely. Scope is resilience (always-visible status, real retry-on-failure), not a claimed root-cause fix — do not let this get planned or reported as "the Safari bug is fixed."
- CFG-75 (carousel): confirmed-as-designed, product decision made (preview follows scroll).
- CFG-76 (icon): confirmed defect, developer proposed the fix.

No unrelated refactor.

</domain>

<decisions>
## Implementation Decisions

### Titles (CFG-72)
- Device-page settings cards (Diagnostic LED, Wake interval, Notifications) must be wrapped in the same "nested supersection" style Display-page cards already use (`_nested_wrapper_html()`, `companion/pages/config_page.py`), so the resulting `<h2>`/card title renders identically: 16px / weight 600 / sans, per `companion/static/style.css:5703-5705` (`.page-section--nested > h2`).
- This may require introducing supersection groupings on the Device page if none exist yet — check current Device page structure before designing the grouping; do not invent groupings that don't reflect real relatedness between cards.
- Verification must render BOTH pages and read `getComputedStyle` (font-size, weight, family) on every such title, asserting equality — a markup-only/class-name check is insufficient; that is exactly how 27-06 missed this the first time.
- Re-verify CFG-65 and CFG-47's retirement note stay intact (unrelated code, but same file region).

### Quiet-hours dial — two bugs (CFG-73)
- Do NOT touch the cross-surface agreement logic from 27-02 (arc/handles/caption agreeing on the SAME value) — verified still correct, out of scope.
- **Bug A — readout format:** `quiet_dial_readout_html()` (`companion/pages/config_page.py:3050-3099`) and the JS-side substitution seam (`companion/static/value-controls.js`) must format both endpoints as HH:MM and compute+display a live, correct duration on every interaction (drag, keyboard, typed field edit, preset click) — not just at initial server-rendered load. Verification reads the caption's actual displayed text after each interaction KIND and asserts it matches computed HH:MM + duration, byte-for-byte identical in form to the server-rendered initial state.
- **Bug B — handle collapses to centre during a press.** Root cause CONFIRMED by live measurement (not the angle/pointer math, which is fine in every scenario tried): `.quiet-dial__handle` is a real `<button>` (`companion/pages/config_page.py:2980`), and the global `button:active { transform: translateY(1px); }` rule (`companion/static/style.css:2624-2626`, specificity 0,0,1,1) beats the handle's own single-class positioning rule (`companion/static/style.css:1519-1526`, specificity 0,0,1,0) while pressed, and `transition: transform .15s ease` (the base `button` rule, `style.css:2559-2583`) animates the handle visibly sliding toward the dial's centre for the ~150-300ms the press lasts, dropping the handle's own `translate(-50%,-50%)` centring term along with it (CSS `transform` replaces wholesale, never composes). Measured: 78px from dial centre (correct, on the 78px ring) at press → 14-16px (the centre) by 90-150ms → back to 78px ~200ms after release. Reproduces on a plain press-and-hold, no drag needed — every "drag" repro just happened to hold the button long enough to show it. Fix direction: give `.quiet-dial__handle`'s own `:active` state precedence over the generic `button:active` rule (same specificity family, ordered to win, or exclude via `:not(.value-control__handle)`), and reconsider whether `transition: transform` should apply to this element at all — its polar position should track the pointer/value instantly, not lerp through the chord. **Apply the identical fix to the wake-interval slider's handle** — same shared `.value-control__handle`/`button` base, same collision, confirmed by the investigating agent as a live risk there too. Verification must SAMPLE the handle's resolved position (`getBoundingClientRect` distance from dial/slider-track centre) throughout a held press, not only before and after — a check that only reads start/end state would pass on the current broken code, since the position IS correct at rest.

### Save reliability — escalated, most severe item in this phase (CFG-74)
- **This started as "runway auto-save, not reproduced" and became a confirmed, severe, cross-page, cross-device failure.** Timeline: (1) initial investigation found runway auto-save works fine in Chromium; (2) developer reported nothing saves on iPhone Safari, for anything, not just runway; (3) a dedicated deep-dive investigation (full read of `dirty-state.js`, `value-controls.js`, script load order, CSP, fetch options, every Safari-incompatible-API/syntax class checked) found **no JS incompatibility, no syntax error, no obvious CSS collision on the toast** — ruled out `requestIdleCallback` and every other Safari-gap API (absent from the codebase entirely), `keepalive` (not used), top-level `await` in a classic script (not present), shadow DOM, `FormData`, `sendBeacon`. The one genuine, separately-real defect found along the way: the leave-guard relies solely on `beforeunload`, which iOS Safari does not reliably fire — worth a small mention but NOT the cause of "nothing saves," since no unload-time flush exists to fail in the first place; (4) developer confirmed on the iPhone that a quiet-hours preset button DOES visibly update the time fields (so the JS runs and `form.elements` does resolve the cross-tree `form=`-associated fields correctly, at least for that direct write) but no error toast ever appears; Device page (all controls natively nested, zero `form=` indirection) ALSO fails to save on the same iPhone — ruling out the leading "clipped-radio/form= architecture" theory as the sole cause, since Device has neither; (5) developer then tested on Mac Safari with a real mouse — same result, no save confirmation for ANY setting tested, no error toast; (6) a second close reading of `dirty-state.js` end-to-end and the toast's own CSS (`.quick-toast`, `companion/static/style.css:8364-8386`, `position:fixed`, rendered as a direct `<body>` child with no transformed ancestor found) turned up no further leads.
- **Conclusion: root cause NOT CONFIRMED.** Real, tethered WebKit devtools (Mac + cable, or Mac Safari's own Web Inspector) would settle this definitively but the developer isn't available to run that for several hours. Do not plan or claim a root-cause fix that hasn't been verified working end-to-end against a real failure reproduction — this codebase's own discipline (never claim more than the evidence supports) applies directly here.
- **Decision, taken with the developer 2026-09-15: build resilience instead of guessing.** Required, regardless of cause:
  1. The save status indicator (`[data-save-status]`) must be visible independent of scroll position — currently implied to sit near the page header; make it fixed/sticky so it survives scrolling. (Distinct element from the `.quick-toast` failure toast, which is already `position:fixed` and doesn't need this — but re-verify the toast is genuinely reachable/visible too, since the report of "no popup ever" spans both.)
  2. Any save failure (non-204 response, opaque redirect from an expired session, a thrown exception, or a save that never resolves within a bounded timeout — pick a reasonable timeout, e.g. a few seconds) surfaces a REAL, actionable "Réessayer" (retry) affordance. It must appear ONLY on genuine failure and be completely absent otherwise — this is the one case where a visible interactive element doesn't violate the developer's "zero boutons" stance, because it's conditional and load-bearing, not a permanent fixture.
  3. Add whatever diagnostic capture is possible without a new network call or new stored-data surface (e.g., distinguishing the exact failure kind — non-204 vs. opaque-redirect vs. network-error vs. timeout — in what's shown/logged) so a recurrence is diagnosable without a tethered debugger.
  4. The runway `form=`-attribute path still gets its own regression-proof check (unchanged from the original, narrower ask) — proving it produces the same pass/fail contract as every other control.
  5. **If, while building 1-3, live Chromium testing turns up an actual, reproducible bug in the save pipeline** (not just the resilience wrapper), fix it and name it plainly as a real root-cause fix — do not fold a genuine find into "resilience" framing, and do not claim the Safari-specific failure is fixed unless it's been verified against an actual reproduction of it.
- Do not touch `dirty-state.js`'s core save-triggering logic (the `change` listener, `countDifferences()`, `snapshotValues()`) without a specific, evidenced reason — it read as structurally sound in review; the changes here are additive (visibility, failure surfacing, timeout) unless investigation during implementation finds otherwise.

### Theme carousel — preview follows scroll (CFG-75)
- **Product decision, made via AskUserQuestion on 2026-09-15: "Aperçu suit le scroll (recommandé)."** While scrolling/swiping the carousel strip, the live preview `<img>` must update to match whichever theme chip is currently centered in the strip — this is a PREVIEW state, distinct from SELECTION. No radio state changes and no setting persists from scroll alone; an actual click or keyboard-select is still required to commit the theme choice.
- Apply to every carousel instance (departures, arrivals, calendar — extended in Phase 27). Preserve 27-07's discipline: `strip_id` is a required per-instance parameter specifically to prevent shared-state collisions between carousel instances; whatever new preview-tracking state is added (e.g., an `IntersectionObserver` per strip, or scroll-position-to-nearest-chip mapping) must follow the same per-instance isolation, never a single shared observer/id across all carousels.
- Respect existing CSP constraints: `script-src 'self'` (no inline script), `img-src 'self' data:` (blob: URLs are blocked — do not use `URL.createObjectURL()` for any preview-image mechanism; the preview swap should just update `<img src>` to point at the already-available theme preview image, same as click-selection already does).
- Verification must assert the preview `<img src>` actually changes to match the geometrically centered chip during a real scroll (dispatch real scroll events across several intermediate positions, not a jump to the end) — not merely that a scroll listener is attached.

### Mobile hamburger → gear icon (CFG-76)
- `#site-nav-toggle` (`companion/layout.py`) currently renders `icon-hamburger`. Replace with a gear icon glyph for this control only.
- Keep `aria-label="Account and preferences"` (`NAV_TOGGLE_LABEL`, `companion/layout.py:147`) and the panel contents (`_mobile_nav_html()`) completely unchanged — only the visual glyph changes, since the label is already accurate for what the panel actually contains (language switch, theme switch, sign-out — no page-navigation links, since those moved to the bottom tab bar in Phase 22-14).
- Check the existing icon system's pattern (how `ICON_IDS` entries are defined — inline SVG symbol, sprite reference, etc.) before adding a new icon, and follow that same pattern. Confirmed via investigation: no gear/settings icon exists anywhere else in the app (0 hits for "gear", "settings-icon", "⚙" app-wide), so this introduces no collision or duplicate-meaning risk.

### Claude's Discretion
- Exact supersection grouping labels/structure for the Device page (if new groupings are needed for CFG-72) — pick names consistent with the existing Display-page supersection labels ("Look", "What it watches", "When it is on") in tone, but accurate to Device's own cards.
- Exact IntersectionObserver threshold/rootMargin tuning for CFG-75's "centered" determination — any reasonable, testable definition of "centered" is acceptable as long as it's deterministic and provably matches what a real scroll produces.
- Exact gear icon SVG path/artwork for CFG-76 — any clean, recognizable gear glyph consistent with the existing icon system's visual weight/stroke style.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase's own investigation
- No standalone RESEARCH.md — this phase's investigation was performed live against the running app (Explore agent, Playwright) rather than through documentation research. Root causes and file:line pointers are recorded directly in `.planning/ROADMAP.md`'s Phase 28 entry and in the decisions above; treat those as verified findings, not hypotheses to re-derive.

### Prior phase precedent (same files, same discipline)
- `.planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/` — the immediately preceding phase, same review-feedback shape, same files (`config_page.py`, `style.css`, `value-controls.js`, `dirty-state.js`, `layout.py`, `test_browser_ux.py`, `test_config_page.py`). 27-02 (dial pair-seam model), 27-06 (title investigation — what it got WRONG is exactly this phase's item 1), 27-07 (carousel `strip_id` per-instance discipline — MUST be preserved by CFG-75's new preview state).
- `.claude/skills/sketch-findings-skypane/SKILL.md` — design system authority, 6 standing contracts, especially "assert relationships, not just endpoints" (the central discipline for CFG-73 and CFG-75's verification).

### App architecture constraints (apply to all tasks)
- CSP: `script-src 'self'` (no inline script — new script logic goes in an existing static JS file, not inline); `img-src 'self' data:` (blob: URLs blocked).
- No catch-all `/static/` handler — any genuinely new script file needs its own route; strongly prefer extending an existing script (`value-controls.js`, `theme-preview.js`, `dirty-state.js`) over adding a new one, since the deferred-script pin count is tracked and moving it has a real cost recorded in prior phases.

</canonical_refs>

<specifics>
## Specific Ideas

- CFG-72's fix is structural (wrap Device cards in the existing nested style), not a new style — reuse `_nested_wrapper_html()` verbatim rather than inventing a second nested-style mechanism.
- CFG-73's fix must reuse whatever HH:MM formatting logic already exists server-side for the initial render (do not hand-roll a second minute-to-HH:MM converter in JS if one can be shared/ported cleanly).
- CFG-75's "preview" state must be visually obvious but must NOT alter the persisted/selected theme — a page reload without clicking must show the previously SELECTED theme, not whatever was last scrolled past.

</specifics>

<deferred>
## Deferred Ideas

None — this phase's scope is exactly the 4 confirmed items (CFG-72, 73, 75, 76) plus CFG-74's optional regression check. Item 3 (runway) has no deferred work; it simply isn't a defect.

</deferred>

---

*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Context gathered: 2026-09-15 via live investigation + developer AskUserQuestion decision*
