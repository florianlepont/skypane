---
phase: quick/260904-bbi
plan: 01
subsystem: ui
tags: [css, has-selector, radio-group, accessibility, settings-page, companion]

requires:
  - phase: 06.6.4.1.1-06
    provides: "the .runway-card--selected / .theme-chip--selected border+wash+check-glyph selected-state treatment this plan re-keys"
provides:
  - "Strong selected-card treatment (border + wash + check glyph) driven by live :has(input:checked) state on .theme-chip and .runway-card"
  - "@supports selector(:has(*)) fallback block preserving today's server-class-driven behaviour verbatim for non-supporting browsers"
  - "Quiet accent-free 'Current' marker (dashed 70%-muted ring + English ::after tag) for a saved-but-no-longer-live card"
  - "control-density.md's Selected-card treatment entry superseded in place with the live-state contract"
affects: [settings-page, companion-static-css, sketch-findings-skypane-skill]

tech-stack:
  added: []
  patterns:
    - "Live-state CSS re-key: pair a server-rendered class with a :has()-keyed live selector inside @supports, demoting the class to a no-:has() fallback plus an honest quiet marker, rather than dropping the server class"
    - "Positive hover-restore rule (not a re-scoped :not() guard) to answer a specificity trap without invalidating a selector list in non-supporting browsers"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_config_page.py
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/SKILL.md

key-decisions:
  - "DP-1: strong treatment re-keyed to :has(input:checked)"
  - "DP-2: server --selected class kept, demoted to a quiet 'Current' marker"
  - "DP-3: @supports selector(:has(*)) fallback preserves prior behaviour verbatim"
  - "DP-4: two new harness checks, EXPECTED_CHECK_COUNT re-derived by running (70 -> 72)"
  - "DP-5: control-density.md's Selected-card treatment entry superseded in place"
  - "DP-6: real-browser verification, light+dark x 1440px+375px, fresh scratch state dir"

patterns-established:
  - "CSS defect discovered by real-browser measurement (a bounding-rect collision invisible to the eye) fixed in the same task, with the original measurement recorded rather than silently repositioned"

requirements-completed: []

duration: ~65min
completed: 2026-09-04
status: complete
---

# Quick Task 260904-bbi: Selected state follows the live choice, not the saved config — Summary

**Re-keyed the theme-chip/runway-card selected-card highlight from a server-rendered `--selected` class to live `:has(input:checked)` state inside one `@supports` block, so clicking a different card moves the strong highlight immediately instead of leaving the stale saved card looking selected.**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-04
- **Tasks:** 3/3 completed
- **Files modified:** 4 (`companion/static/style.css`, `companion/test_config_page.py`, `.claude/skills/sketch-findings-skypane/references/control-density.md`, `.claude/skills/sketch-findings-skypane/SKILL.md`)

## Accomplishments

- Fixed the defect the developer found at the 06.6.4.1.1-06 checkpoint follow-up: clicking a theme chip (or runway card) while a different value was saved left the SAVED card painted as selected (border + 12% wash + check glyph) and the clicked card unstyled, with only the dirty bar changing.
- Added one `@supports selector(:has(*))` block to `style.css` re-keying the strong treatment of both `.theme-chip` and `.runway-card` to live `:has(input:checked)` state, with a positive hover-restore rule answering the D-03a specificity trap (documented inline with the full arithmetic).
- Demoted the server-rendered `--selected` class to two honest jobs: the no-`:has()` fallback (byte-for-byte unchanged, painting today's exact treatment in non-supporting browsers) and, when it no longer matches the live choice, a quiet accent-free dashed 70%-muted ring plus an English `"Current"` `::after` tag.
- Real-browser verification (raw CDP, cached Playwright Chromium, legacy `--headless`) proved click, arrow-key nav, hover, Cancel, and Save+reload all move the strong highlight correctly across light+dark x 1440px+375px x {theme chip, runway card} — 68/68 assertions passed.
- A real, previously-invisible defect surfaced by that verification (a `.theme-chip__swatches` bounding-rect collision with the new "Current" tag) was fixed in the same task and re-verified.
- `control-density.md`'s "Selected-card treatment" entry superseded in place with the live-state contract, the specificity arithmetic, the marker-slot asymmetry, and the pseudo-element decision; `SKILL.md` updated to match.

## Task Commits

1. **Task 1: Re-key both selectable-card components to live :checked state (RED)** - `c23b7e5` (test)
2. **Task 1: Re-key both selectable-card components to live :checked state (GREEN)** - `d66f128` (fix)
3. **Task 2: Real-browser verification — measured overlap fix** - `badcfe4` (fix)
4. **Task 3: Supersede control-density.md's Selected-card treatment entry** - `f697f44` (docs)

_No metadata commit yet — the orchestrator handles the docs commit (STATE.md/SUMMARY.md) per this plan's constraints._

## Files Created/Modified

- `companion/static/style.css` — one `@supports selector(:has(*))` block re-keying `.theme-chip`/`.runway-card`'s strong selected treatment to `:has(input:checked)`; rewrote the now-falsified `:has()`-claim comments in both component groups; extended the header accent-reservation list; added `.theme-chip__swatches { width: fit-content; }` to clear a real-browser-measured overlap.
- `companion/test_config_page.py` — two new CSS-contract checks (`_strong_selected_treatment_is_keyed_to_the_live_checked_radio`, `_saved_but_unchecked_card_degrades_to_a_quiet_current_marker`); `EXPECTED_CHECK_COUNT` re-derived by running: 70 → 72.
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — "Selected-card treatment" entry superseded in place; CSS Patterns snippet extended with the live-state layer; three new "What to Avoid" bullets; Origin line updated.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — accent-reservation sentence, selected-state bullets, and Folded-In Work list updated to describe the live-state re-key.

## Decisions Made

- **DP-1 through DP-6** as pinned in the plan frontmatter — all followed without deviation (live-state re-key, server class kept as fallback+quiet marker, `@supports` fallback, harness re-derivation, skill doc supersession, real-browser verification).
- **Task 2 in-task fix (not a new decision, an execution of DP-6's own instruction):** when real-browser measurement found the `"Current"` tag's bounding box geometrically intersecting `.theme-chip__swatches`' own bounding box (even though no visible pixel collided, since the swatches row's block-level flex container defaults to filling the full available width while its two dots render flush-left), the plan's own instruction ("adjust the tag's inset or slot in style.css within this task, and re-run — do not ship a measured collision") was followed: `width: fit-content` was added to `.theme-chip__swatches`, shrinking its box to its actual rendered content with zero visual change, and the full 68-assertion suite was re-run to confirm the fix.

## RED/GREEN Discipline (Task 1)

- **RED (recorded before any CSS was written):** `70/72` checks pass — both new checks failed for the expected reason (`expected exactly one '@supports selector(:has(*)) {' block, got 0`; `expected style.css to declare '.theme-chip--selected:not(:has(input:checked)) {'`).
- **GREEN (after the CSS):** `72/72` checks pass.
- One self-caught comment/grep collision during GREEN: an explanatory comment inside the new `@supports` block's own header literally contained the string `.theme-chip:has(input:checked):hover,` — the exact selector the new harness check searches for — and since `source.index()` finds the FIRST occurrence, this made the check report the (correct) rule as living BEFORE the `@supports` opening. Fixed per the plan's own harness-hazards convention: reworded the comment prose (never weakened the check) to describe the mechanism without repeating the literal selector.
- `EXPECTED_CHECK_COUNT` re-derived by running the harness, per DP-4: `70 -> 72`.

## Task 2: Real-Browser Verification

**Method:** the cached Playwright Chromium at `~/Library/Caches/ms-playwright/chromium-1228`, launched with the LEGACY `--headless` flag (never `--headless=new`) plus `--remote-debugging-port`, driven over raw CDP using a hand-rolled minimal WebSocket client (no external deps), matching the established recipe from `06.6.4.1.1-06-SUMMARY.md` and quick task `260903-peo`. Authentication was a real `POST /login` (via `urllib`, server-side), with the server-issued `sp_session` cookie handed to the new page target via CDP `Network.setCookie` — never a UI-driven form login.

**Environment:** a fresh companion instance against a brand-new scratch state dir under the session scratchpad (`.../260904-bbi-verify/state`), never `/tmp/skypane-prod-state` or any production snapshot, on port 8830. Stopped cleanly after verification.

**Methodology correction (not a code bug, documented for future re-runs):** the theme-picker grid (16 chips) at 375px pushes the runway cards well past any fixed device-metrics height guess (1400px was not enough) — CDP mouse coordinates are relative to the current viewport, not the full scrollable document, so a click at a computed center point beyond the override height silently misses. Fixed by querying `document.documentElement.scrollHeight` after each navigation and re-overriding the viewport height to match (plus a margin), eliminating the need for any real scrolling.

**Full matrix run: {light, dark} x {1440px, 375px} x {theme picker, runway picker} = 8 runs, 68 assertions, all passing.**

| Run | Accent (resolved) | S1: saved is sole strong selection | S2: click moves strong highlight; saved degrades to quiet marker (count=1) | Overlap: tag vs swatches/preview or number | S3: hover keeps accent border, no hover shadow | S4: ArrowDown moves highlight; marker stays on saved | S5: Cancel → sole strong, 0 markers | S6: Save+reload → sole strong, 0 markers, server class agrees |
|---|---|---|---|---|---|---|---|---|
| theme/light/1440px | rgb(177,63,22) | PASS (yellow_light, solid, accent, check shown) | PASS (red solid+accent+check; yellow_light dashed+muted+"Current") | PASS / PASS | PASS (red stays accent, boxShadow none) | PASS (moved to red_light idx 6; marker stayed on idx 4) | PASS (checked=[4] strong=[4] count=0) | PASS (strong=[5] selected-class=[5] count=0) |
| runway/light/1440px | rgb(177,63,22) | PASS (02-20, solid, accent, check shown) | PASS ("3" solid+accent+check; 02-20 dashed+muted+"Current") | PASS (n/a) | PASS ("3" stays accent, boxShadow none) | PASS (moved to idx 1; marker stayed on idx 2) | PASS (checked=[2] strong=[2] count=0) | PASS (strong=[0] selected-class=[0] count=0) |
| theme/light/375px | rgb(177,63,22) | PASS (red, solid, accent, check shown) | PASS (red_light solid+accent+check; red dashed+muted+"Current") | PASS / PASS | PASS (red_light stays accent, boxShadow none) | PASS (moved to idx 7; marker stayed on idx 5) | PASS (checked=[5] strong=[5] count=0) | PASS (strong=[6] selected-class=[6] count=0) |
| runway/light/375px | rgb(177,63,22) | PASS (3, solid, accent, check shown) | PASS (06-24 solid+accent+check; 3 dashed+muted+"Current") | PASS (n/a) | PASS (06-24 stays accent, boxShadow none) | PASS (moved to idx 2; marker stayed on idx 0) | PASS (checked=[0] strong=[0] count=0) | PASS (strong=[1] selected-class=[1] count=0) |
| theme/dark/1440px | rgb(255,138,92) | PASS (red_light, solid, accent, check shown) | PASS (green solid+accent+check; red_light dashed+muted+"Current") | PASS / PASS | PASS (green stays accent, boxShadow none) | PASS (moved to idx 8; marker stayed on idx 6) | PASS (checked=[6] strong=[6] count=0) | PASS (strong=[7] selected-class=[7] count=0) |
| runway/dark/1440px | rgb(255,138,92) | PASS (06-24, solid, accent, check shown) | PASS (02-20 solid+accent+check; 06-24 dashed+muted+"Current") | PASS (n/a) | PASS (02-20 stays accent, boxShadow none) | PASS (moved to idx 0; marker stayed on idx 1) | PASS (checked=[1] strong=[1] count=0) | PASS (strong=[2] selected-class=[2] count=0) |
| theme/dark/375px | rgb(255,138,92) | PASS (green, solid, accent, check shown) | PASS (green_light solid+accent+check; green dashed+muted+"Current") | PASS / PASS | PASS (green_light stays accent, boxShadow none) | PASS (moved to idx 9; marker stayed on idx 7) | PASS (checked=[7] strong=[7] count=0) | PASS (strong=[8] selected-class=[8] count=0) |
| runway/dark/375px | rgb(255,138,92) | PASS (02-20, solid, accent, check shown) | PASS (3 solid+accent+check; 02-20 dashed+muted+"Current") | PASS (n/a) | PASS (3 stays accent, boxShadow none) | PASS (moved to idx 1; marker stayed on idx 2) | PASS (checked=[2] strong=[2] count=0) | PASS (strong=[0] selected-class=[0] count=0) |

Raw per-run computed-style readings (borderStyle/borderColor/boxShadow/bodyBg/checkDisplay/afterContent, plus every card's rect and the tag's derived pseudo-rect) are preserved at `/private/tmp/claude-501/.../scratchpad/260904-bbi-verify/measurements.json` (session-scratch, not committed).

**Note on `checkDisplay` values:** the raw JSON records `"flex"`, not `"inline-flex"`, for a shown check glyph. This is expected browser behaviour, not a defect: `.theme-chip__check`/`.runway-card__check` are `position: absolute`, and CSS blockification maps `display: inline-flex` to its used value `flex` for any absolutely-positioned box (same computed-style behaviour the pre-existing `--selected`-keyed rule already had). The stylesheet's own declared value is still `display: inline-flex;`, exactly as `test_config_page.py`'s static source-literal checks require.

**Chromium launch:** legacy `--headless` flag only; `--headless=new` never used anywhere in the driver, per the plan's own environment note.

**Evidence screenshots — environment limitation (documented, not silently skipped):** the plan additionally asked for one screenshot per {theme, width} at the S2 state. `Page.captureScreenshot` (both via CDP and via Chrome's own `--screenshot` CLI mode) hung indefinitely (0% CPU, no response ever received) in this execution's sandboxed environment, reproduced across four independent Chromium launches with different flag combinations (default, `--disable-gpu`, without it, `--use-angle=swiftshader --enable-unsafe-swiftshader`) and confirmed as a genuine browser-side stall (not a client parsing bug — every other CDP call, including `Page.getLayoutMetrics` and dozens of `Runtime.evaluate`/`Input.dispatch*` calls in the same session, round-tripped normally). This appears to be a screenshot-pipeline limitation specific to this sandbox's graphics stack, separate from the documented `--headless=new` navigation hang. All `getComputedStyle`-based assertions — the load-bearing verification for every `must_haves.truths` entry — completed successfully and do not depend on screenshot capture.

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired data sources were introduced by this task.

## Threat Flags

None beyond what this plan's own `<threat_model>` already covers (T-bbi-01 through T-bbi-04, T-bbi-SC) — no new route, no new parameter, no dependency installed, and the `"Current"` tag's text is a static CSS literal, never interpolated from any request value.

## Open Items — Developer Human-Check (relay verbatim, not resolved here)

Per the plan's `<human-check>`: the developer should open Settings in light and dark, click a different theme chip, and confirm the new choice reads as clearly the selected one while the saved one reads as a quiet "this is what's saved" marker rather than a second selection, then Cancel and confirm it snaps back. The measured evidence is in the table above; **this check is about whether the "strong-new, quiet-old" balance actually feels right at 16-chip density** — specifically whether the dashed muted ring is discreet enough not to compete, and legible enough to be worth having at all. **If the marker reads as noise, the documented fallback position is to drop the dashed ring and keep the "Current" tag alone.**

## Self-Check: PASSED

- `companion/static/style.css` — FOUND (modified, verified via `grep`/harness above)
- `companion/test_config_page.py` — FOUND (modified, 72/72 checks pass)
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — FOUND
- `.claude/skills/sketch-findings-skypane/SKILL.md` — FOUND
- Commit `c23b7e5` — FOUND in `git log --oneline`
- Commit `d66f128` — FOUND in `git log --oneline`
- Commit `badcfe4` — FOUND in `git log --oneline`
- Commit `f697f44` — FOUND in `git log --oneline`
- `git rev-parse --abbrev-ref HEAD` — `claude/sketch-theme-typography-direction` (confirmed at start and end; no branch created)
- `scripts/run-all-tests.sh` — all 16 harnesses green, 851 total checks, coverage 92%
- `server/.venv/bin/ruff check .` — clean
