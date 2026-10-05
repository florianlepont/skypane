---
quick_id: 261004-sfl
type: quick
autonomous: true
branch: claude/fix-sheet-nojs-flake
---

# 261004-sfl: the scripts-blocked airline sheet click no longer flakes

## Objective

CI on main failed `test_a_taken_name_without_scripts_focuses_the_in_page_name_field`: the
click on the in-page "Save name" button was intercepted by the fixed bottom tab bar.
Decide whether the page layout or only the test is at fault, and make the sheet tests
robust without loosening any assertion.

## Tasks

1. Measure where the Save button sits after the pencil's anchor jump and after a refusal, at
   390 px wide and several heights, scripts blocked.
2. Test helper `_click_centred()` centres the target before clicking; every in-page sheet
   click (pencil, Save, reset) in `test_browser_airline_sheet.py` uses it and waits for load.
3. A measuring test pins that Save is inside the viewport and above the tab bar.
