---
id: 261005-cri
slug: calendar-row-inline-manage
---
# Quick task: calendar status row keeps Manage on the right

Owner feedback: on desktop the Display page's calendar status row dropped the "Manage" button under the text, making the row taller.

Tasks:
1. style.css: remove the >=960px rule that turned the row into a grid with the button on a second line; the flex row (tile, text, button) applies at every width. The text side flexes (`flex: 1 1 0; min-width: 0`), the provider name ellipsizes on one line, the detail wraps; the button keeps its 44px height and never shrinks.
2. New browser test `companion/test_browser_calendar_row.py`: button right of the text, centred, inside the row, row no taller than its content, no overflow, >=44px on phones; 360/390/1280, EN/FR, light/dark, every state, plus scripts blocked.
3. Verify: stability loops, render baseline, full suite, ruff, mypy, function-size and comment-history gates.
