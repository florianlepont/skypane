---
quick_id: 261003-jmq
description: Home status header - clear overdue wording, compact battery-first layout
branch: claude/home-status-bar
---

# Quick 261003-jmq: Home status - late wording and compact battery-first panel

## Tasks

1. Late wording (shared `frame_state` headline, EN/FR): "Update overdue · expected at HH:MM"
   (date only when not today), no countdown once overdue. Short delay keeps the existing
   due wording (late starts at next wake + 2 intervals, unchanged). Long delay (more than
   3 intervals past the expected wake): amber dot plus a "See Health" link to /health.
   Health thresholds and wake policy untouched.
2. Compact, battery-first: cadence sentence becomes "Updates about every N min" in a
   no-JS `<details>` whose body holds the short why; battery block gets a larger glyph,
   larger percentage and a clear level bar; panel gets shorter. Desktop three zones,
   mobile stacked.
3. Tests (three late states, EN/FR, cadence, battery names, no overflow at 1280/390/360),
   retarget old "Expected since" assertions, regenerate render baseline after inspecting
   the diff, screenshots at 1280/390/360 light and dark.
4. Full gates: run-all-tests (browser required), ruff, mypy, comment-history, function-size.
