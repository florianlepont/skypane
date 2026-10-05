---
quick_id: 261005-sbw
status: complete
---

# 261005-sbw summary

- Root cause: a 5 s navigation budget in `_save_via_bar()` that the redirected /display page's
  `load` event can exceed under load (its look previews are rendered server side).
- `companion/test_browser_ux_helpers.py`: default `timeout` 5000 -> 15000, with a comment. Used
  by 19 call sites: 15 inherit the new budget, 4 (display looks, ux_03) already pass 30 s for the
  same reason.
- No assertion changed and nothing skipped.
