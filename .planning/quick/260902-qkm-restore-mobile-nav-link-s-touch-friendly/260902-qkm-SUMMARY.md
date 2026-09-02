---
phase: quick-260902-qkm
plan: 260902-qkm
subsystem: companion-web-ui
tags: [css, mobile-navigation, accessibility, touch-target, regression-fix]
dependency-graph:
  requires: []
  provides:
    - "mobile-nav__link-44px-restored"
    - "nav-geometry-divergence-regression-guard"
  affects:
    - companion/static/style.css
    - companion/test_companion_app.py
    - .claude/skills/sketch-findings-skypane
tech-stack:
  added: []
  patterns:
    - "Two nav renderers (.sidebar-link desktop-only, .mobile-nav__link mobile-only) now deliberately diverge in touch-target size, pinned apart by a single regression check that fails in both directions"
key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_companion_app.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/mobile-navigation.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
decisions:
  - "Reverted only the two declarations D-05 mistakenly changed on .mobile-nav__link (height->min-height, Label-size->Body-size); left border-radius (D-05a's single-signal active pill) untouched since that part of D-05 was correct"
  - "Did not touch .sidebar-link — its D-05 compaction is correct because .dashboard-sidebar is display:none below 960px, so it never reaches a phone"
  - "Added one regression check (not two) that asserts all four facts (mobile min-height, mobile font-size, sidebar height, sidebar font-size) together, since slicing by rule block is what keeps the two selectors' assertions from cross-contaminating"
metrics:
  duration: "~35 minutes (Tasks 1-3; checkpoint pending)"
  completed: "2026-09-02"
status: complete
---

# Quick Task 260902-qkm: Restore mobile-nav__link's touch-friendly size Summary

Reverted a mistaken side effect of the 06.6.4-04 D-05 desktop-compactness pass: `.mobile-nav__link` (the mobile hamburger dropdown's nav links) had been shrunk from `min-height: 44px` at Body size (16px) to a fixed `height: 32px` at Label size (14px) — a change that was only supposed to apply to `.sidebar-link` (the desktop sidebar, which is `display: none` below 960px and therefore never reaches a phone).

## What Was Built

**Task 1 (commit `ce4133d`):** Changed exactly two declarations inside `.mobile-nav__link`: `height: 32px` → `min-height: 44px`, and `font-size: var(--font-label-size)` → `font-size: var(--font-body-size)`. Left `border-radius: var(--radius-control)` (D-05a's single-signal active-pill treatment) untouched — that part of D-05 is correct and shared with `.sidebar-link--active`. Rewrote the rule's head comment to record why D-05's trade never belonged on this selector, and corrected the stylesheet's 44px touch-target floor register (previously naming both nav selectors together) to name only `.sidebar-link` in the traded-away list and add `.mobile-nav__link` to the kept-the-floor list. `.sidebar-link` itself, the active modifier, the `:not()`-scoped hover rule, and the WR-01 colour pair were all confirmed byte-identical after the edit (verified by diff — no line touching `mobile-nav__link--active` was added or removed).

**Task 2 (commit `e026574`):** Added one new regression check to `companion/test_companion_app.py` (`_nav_link_geometries_stay_diverged`), slicing the `.mobile-nav__link` and `.sidebar-link` rule blocks independently and asserting all four facts together: mobile link has `min-height: 44px` and `font-size: var(--font-body-size)`; sidebar link still has `height: 32px` and `font-size: var(--font-label-size)`. `EXPECTED_CHECK_COUNT` moved 107 → 108. Manually confirmed the guard fails in both directions by temporarily breaking each side and restoring (see Verification below) — the working tree was byte-identical to the committed state after each restore. Corrected three copies of the same stale floor-register claim in the `sketch-findings-skypane` design skill (`SKILL.md`, `references/mobile-navigation.md`'s Link geometry paragraph and CSS excerpt, `references/accessibility-contrast.md`), rephrasing so no single line anywhere under the skill directory co-locates `.mobile-nav__link` with the `32px` figure (confirmed by grep). `references/control-density.md` was left untouched (its two `.mobile-nav__link` mentions are about hover/active wash percentages, still accurate).

**Task 3:** Live-measured the fix in a real running `companion/app.py` instance via the Chrome DevTools CLI, with a cache-busted stylesheet request confirmed to serve the updated CSS before measuring.

### 375px measurement table (mobile dropdown open)

| Link | Rect height | Rect width | Computed font-size | Computed min-height | Computed height |
|------|------------|-----------|---------------------|----------------------|-------------------|
| Settings (active) | 44px | 311px | 16px | 44px | 44px |
| Health (dot present) | 44px | 311px | 16px | 44px | 44px |
| Airlines | 44px | 311px | 16px | 44px | 44px |
| History | 44px | 311px | 16px | 44px | 44px |

Panel (`#mobile-nav`): computed `max-height: 420px`; rendered `getBoundingClientRect().height`: 281px; `scrollHeight`: 281px — no clipping (scrollHeight == rendered height, well inside the 420px ceiling). Footer region (theme picker + Sign out) confirmed fully inside the panel's visible box (`footerRect.bottom` 373 <= `panelRect.bottom` 373; `signOutRect.bottom` 365 <= 373).

Visual confirmations at 375px (individually checked):
- All four labels (Settings, Health, Airlines, History) render on one line each, no wrap or truncation — confirmed by the accessibility-tree snapshot text and the screenshot.
- The active link's (Settings) tinted pill spans the full row height with no gap or overlap against its neighbours — confirmed in the screenshot.
- The Health notification dot sits inline after its label ("Health — attention needed" in the a11y tree, red dot immediately after the text in the screenshot), not floating.
- No link overflows the panel's horizontal edge — confirmed programmatically (`overflowsRight`/`overflowsLeft` both `false` for all four links).

Screenshot: `.planning/quick/260902-qkm-restore-mobile-nav-link-s-touch-friendly/verification/375px-dropdown-open.png`

### 1280px measurement table (desktop sidebar, untouched)

| Link | Rect height | Computed font-size |
|------|------------|---------------------|
| Settings (active) | 32px | 14px |
| Health (dot present) | 32px | 14px |
| Airlines | 32px | 14px |
| History | 32px | 14px |

`.site-header` computed `display: none`; `#mobile-nav` computed `display: none` — the mobile header and dropdown are not rendered at 1280px, confirming the `>=960px` breakpoint hides them as designed.

Screenshot: `.planning/quick/260902-qkm-restore-mobile-nav-link-s-touch-friendly/verification/1280px-sidebar.png`

### Full-suite result

`scripts/run-all-tests.sh` → `==> Result: PASS`, zero failing harnesses (11 server/companion/stub-server harnesses ran, coverage at 92% total, same threshold as before this task). `companion/test_companion_app.py` alone: 108/108 checks pass.

## Deviations from Plan

None — plan executed exactly as written. All `<done>` and `<verify>` criteria for Tasks 1-3 were met on the first pass; no Rule 1/2/3 auto-fixes were needed.

## Checkpoint Status

**Task 4 (checkpoint:human-verify, gate="blocking") has NOT been completed.** This quick task requires the developer to confirm the restored tap target on their own physical phone before the plan can be considered fully closed — headless/computed-style measurement already escaped this exact bug class once on this project, so Task 3's automated numbers above are necessary but not sufficient proof. `status: complete` above reflects that all autonomous tasks (1-3) finished cleanly and the full test suite is green; it does not mean the plan's `<verification>` and `<success_criteria>` are fully satisfied — those require the developer's real-phone sign-off, which is still pending.

See the checkpoint return message in this session's own output for the exact verification steps to relay to the developer.

## Self-Check: PASSED

- `companion/static/style.css` — FOUND, contains `min-height: 44px` inside `.mobile-nav__link` (confirmed by automated verify command in Task 1).
- `companion/test_companion_app.py` — FOUND, `EXPECTED_CHECK_COUNT = 108` present, 108/108 checks pass.
- `.claude/skills/sketch-findings-skypane/references/mobile-navigation.md` — FOUND, restored `min-height: 44px` in CSS excerpt, no `--font-label-size` in that block.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — FOUND, floor register corrected.
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` — FOUND, floor register corrected.
- Commit `ce4133d` — FOUND in `git log --oneline`.
- Commit `e026574` — FOUND in `git log --oneline`.
- `.planning/quick/260902-qkm-restore-mobile-nav-link-s-touch-friendly/verification/375px-dropdown-open.png` — FOUND.
- `.planning/quick/260902-qkm-restore-mobile-nav-link-s-touch-friendly/verification/1280px-sidebar.png` — FOUND.
