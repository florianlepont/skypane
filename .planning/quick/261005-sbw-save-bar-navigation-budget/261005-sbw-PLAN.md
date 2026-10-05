---
quick_id: 261005-sbw
type: quick
autonomous: true
branch: claude/fix-save-bar-wait
---

# 261005-sbw: the save-bar helper no longer times out on a busy machine

## Objective

`test_browser_ux_01.py::test_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves`
kept failing when browser test files ran in parallel (and once on unmodified main). The trace
points at `_save_via_bar()`: `expect_navigation(timeout=5000)` expires although the save
happened, because the redirected /display page's `load` event waits for the server-rendered look
previews, which take longer than 5 s on a busy machine ("domcontentloaded" is already logged).

## Tasks

1. Raise the helper's default navigation budget from 5 s to 15 s and say why in a comment.
   No assertion changes; the navigation is still awaited.
