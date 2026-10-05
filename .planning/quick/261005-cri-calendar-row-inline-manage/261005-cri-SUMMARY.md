---
id: 261005-cri
slug: calendar-row-inline-manage
---
# Summary

- `companion/static/style.css`: deleted the `@media (min-width: 960px)` block that moved "Gérer"/"Manage" under the text; `.calendar-status__main` is `flex: 1 1 0`, the provider name is a single ellipsized line, the button is `white-space: nowrap` with 10px side padding, row gap 12px. No markup, server or sheet change; no new strings.
- Tight column (about 300px at 1280px): the text side shrinks, the provider name ellipsizes, the pill and detail wrap; the button never moves down.
- `companion/test_browser_calendar_row.py` (new): geometry assertions across 360/390/1280 x EN/FR x light/dark x seven states, an iCloud-row check (one-line title, detail at most two lines) and a scripts-blocked check using `reduced_motion="reduce"`. Verified to fail against the old CSS.
- Render baseline regenerated: no change.
