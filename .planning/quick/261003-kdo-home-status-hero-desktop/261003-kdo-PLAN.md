---
quick_id: 261003-kdo
slug: home-status-hero-desktop
date: 2026-10-03
branch: claude/home-status-hero
---

# Quick 261003-kdo: Home status header as the "Frame signal" hero (Direction A)

## Goal

Rebuild Home's status header after the approved Direction A mockup
(`scratchpad/sketches/direction-A.html`): one hero card with a subtle
state-tinted glow, a "Frame state" micro-label, a large serif headline with a
haloed dot, the next-update line with a clock or warning icon, the cadence
disclosure and a "See Health" pill when long overdue; a 270-degree battery
arc gauge (percentage in the middle, "Battery" label, Low / Very low pill);
the two switches as compact pills with leading icons in a recessed panel.

Owner update mid-task: Direction A also applies on mobile (390/360, tablet).
One shared component, mobile-first, wider arrangement from 840 px up; no
duplicated markup.

## Tasks

1. **Markup + i18n + drawing** (`companion/pages/home_page.py`,
   `companion/draw.py`, `companion/ui_base.py`, `companion/i18n_fr/home.py`):
   - Headline split into a short title plus a muted detail line (new EN/FR ids)
     so the serif display size fits every state.
   - Visible eyebrow heading, clock/warning icons (new `icon-warning`,
     `icon-chevron-right` sprite symbols), Health link moved beside the
     cadence as a pill.
   - `draw.arc_gauge()`: inline SVG 270-degree arc using presentation
     attributes (`stroke-dasharray`, `transform`) only, never `style=""`.
   - Battery block keeps its role="img" accessible name and level thresholds.
   - Switch rows gain leading icons; forms, ARIA and posts unchanged.
2. **Styles** (`companion/static/style.css`): hero glow scoped by a state
   modifier, gauge, pills, recessed panel; container-query arrangement
   (stacked, then status|gauge with controls below, then three columns); a
   `--color-switch-thumb` token fixing the dark-theme off thumb globally.
3. **Tests**: retarget `test_home_state_card.py`,
   `test_browser_home_state_card.py` and any other breakage; add arc gauge
   behaviour tests (name, thresholds, no style attributes), switch semantics,
   layout at 1280/1024/840/600/390/360 with no overflow and 44 px targets.
   Regenerate `companion/testdata/render_baseline.json` after inspecting the
   diff.
4. Visual verification with Playwright screenshots (scratchpad `shots4/`),
   full suite with `SKYPANE_REQUIRE_BROWSER=1`, ruff, mypy, comment-history
   and function-size gates; push.
