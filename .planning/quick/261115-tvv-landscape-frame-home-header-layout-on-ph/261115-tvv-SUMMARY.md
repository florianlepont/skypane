---
quick_id: 261115-tvv
---

# Quick 261115-tvv: landscape frame home header on phones

On phone widths (max 699.98px) a landscape frame's Home header now stacks: full-width
picture, then name with pencil, online badge, and the next-refresh line with its info
button level with it. Portrait frames and desktop are unchanged.

- CSS only: `companion/static/style-home.css`, keyed on `.preview-frame__image[data-frame-shape="landscape"]`.
- New browser test: `companion/test_browser_home_header_landscape.py` (390px, en/fr, landscape stacked, portrait side by side).
- `companion/testdata/render_baseline.json`: hash-only change (the style-home.css version query, 8 lines).
- Full suite: 15743 passed after the fix; ruff, mypy, function-size, comment-history clean.
- Deviation: a first draft added a second `align-items: start`, which `test_dashboard_grid_stretches_same_row_tiles` rejected; removed.
- Screenshots: /tmp/claude-0/-home-user-skypane/5f9e9599-d097-5503-9fb4-dbc6712aa735/scratchpad/home-header/ (before/after, en/fr).
