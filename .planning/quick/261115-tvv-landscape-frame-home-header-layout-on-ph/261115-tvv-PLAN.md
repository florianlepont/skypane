---
quick_id: 261115-tvv
description: Landscape frame home header laid out for phone widths
---

# Quick 261115-tvv - landscape frame header on the home page (phone)

Owner screenshot: /root/.claude/uploads/5f9e9599-d097-5503-9fb4-dbc6712aa735/162314e8-image.png
(French UI, ~430px wide, 7.3 inch landscape frame).

## Problem
The small landscape preview sits left of a narrow text column: the name wraps on 2 lines,
"Prochain rafraichissement dans 4 min" wraps on 3 lines, the (i) button and the pencil float far right.

## Task 1 (test first)
Browser test (pytest-playwright, model on companion/test_browser_frame_preview_shape.py) at
390x844 for a landscape frame: preview wider than the text block, frame name on one line
where it fits, refresh line at most 2 lines, no horizontal scroll. Same page for a portrait
frame: the side-by-side layout is unchanged (preview left of the text).

## Task 2
CSS only if possible (companion/static/style-home.css, style.css if needed), keyed on the
existing frame-shape attribute (companion/device_scope.py). Landscape on phone width: preview
full width on top (landscape shape kept), then name + pencil, online badge, refresh line with
the info button aligned with it. Portrait and desktop unchanged. Follow
Skill("sketch-findings-skypane"). Bilingual strings untouched.

## Verify
FULL suites (./scripts/run-all-tests.sh, browser with -n0 --no-cov if needed), ruff, mypy
(server/.venv python -m mypy), function-size and comment-history gates. Regenerate
companion/testdata/render_baseline.json if the stylesheet hash changes
(test-support/companion_render_snapshot.py --write) and confirm it is a hash-only difference.
Before/after screenshots (390x844, deviceScaleFactor 2) of the landscape frame home page to
/tmp/claude-0/-home-user-skypane/5f9e9599-d097-5503-9fb4-dbc6712aa735/scratchpad/home-header/.
Commit atomically on gsd/quick-landscape-home-header, push, no PR, no merge.
