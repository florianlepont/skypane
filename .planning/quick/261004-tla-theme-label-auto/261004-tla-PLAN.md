---
quick_id: 261004-tla
type: quick
autonomous: true
branch: claude/theme-label-auto
---

# 261004-tla: Theme switch label no longer collides in French

## Objective

In the French UI the theme switch showed "Automatique" spilling out of its segment into
"Clair". Shorten the label to "Auto" and fix the overflow itself so no label can run into
its neighbour at any width.

## Tasks

1. Reproduce in Playwright (FR/EN, light/dark, 320-1280 px); save before screenshots.
2. FR `nav.auto` becomes "Auto"; the segment keeps a full accessible name (`nav.auto_full`).
3. `.theme-option`: clip inside the segment (overflow hidden + ellipsis) and tighter padding.
4. Browser regression test (`companion/test_browser_theme_switch.py`), render baseline.
