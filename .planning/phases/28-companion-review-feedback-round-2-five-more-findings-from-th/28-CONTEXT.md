# Phase 28: Companion review feedback round 2 — Context

**Gathered:** 2026-09-15
**Status:** Ready for planning
**Source:** Developer hands-on review of the deployed Phase 27 app, investigated live before scoping (Explore agent, direct Playwright interaction against a real running instance), plus one AskUserQuestion decision.

<domain>
## Phase Boundary

Five findings from the developer's hands-on review of the deployed app. Four are real and in scope; one (runway auto-save) did not reproduce and is explicitly OUT of implementation scope — at most a regression-proof check. No new capability beyond the carousel's decided preview behavior. No unrelated refactor.

</domain>

<decisions>
## Implementation Decisions

### Titles (CFG-72)
- Device-page settings cards (Diagnostic LED, Wake interval, Notifications) must be wrapped in the same "nested supersection" style Display-page cards already use (`_nested_wrapper_html()`, `companion/pages/config_page.py`), so the resulting `<h2>`/card title renders identically: 16px / weight 600 / sans, per `companion/static/style.css:5703-5705` (`.page-section--nested > h2`).
- This may require introducing supersection groupings on the Device page if none exist yet — check current Device page structure before designing the grouping; do not invent groupings that don't reflect real relatedness between cards.
- Verification must render BOTH pages and read `getComputedStyle` (font-size, weight, family) on every such title, asserting equality — a markup-only/class-name check is insufficient; that is exactly how 27-06 missed this the first time.
- Re-verify CFG-65 and CFG-47's retirement note stay intact (unrelated code, but same file region).

### Quiet-hours dial readout (CFG-73)
- Do NOT touch the cross-surface agreement logic from 27-02 (arc/handles/caption agreeing on the SAME value) — verified still correct, out of scope.
- Fix only the readout's TEXT FORMAT: `quiet_dial_readout_html()` (`companion/pages/config_page.py:3050-3099`) and the JS-side substitution seam (`companion/static/value-controls.js`) must format both endpoints as HH:MM and compute+display a live, correct duration on every interaction (drag, keyboard, typed field edit, preset click) — not just at initial server-rendered load.
- Verification must read the caption's actual displayed text after each interaction KIND and assert it matches computed HH:MM + duration, byte-for-byte identical in form to the server-rendered initial state.

### Runway auto-save (CFG-74)
- NOT REPRODUCED. No implementation change.
- Optional: one regression-proof check that runway radios (wired via the `form="settings-form"` attribute idiom, not DOM nesting) trigger the same auto-save "Sauvegardé" status and on-disk persistence as every other control — this wiring path is real and distinct (delegated document-level `change` listener filtered on `e.target.form === form`) but wasn't specifically covered by an existing check.
- Do not touch `dirty-state.js`'s core logic — it already works correctly for this control.

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
