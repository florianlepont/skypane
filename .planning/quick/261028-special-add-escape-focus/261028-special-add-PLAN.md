---
quick_id: 261028-special-add
slug: special-add-escape-focus
date: 2026-10-28
type: quick
---

# Quick 261028-special-add: Escape is pressed only once focus is inside the add dialog

`test_add_a_special_look_is_a_dialog_that_posts_a_rule[chromium]` failed once in CI (run
40738903785) with `assert not True` on `.special-add` `d.open` right after
`page.keyboard.press("Escape")`, and passed on the re-run with no code change.

## Task

Decide whether the immediate read is a test race or a product defect. If a test race, make the
test wait on the real preconditions (focus inside the panel before Escape, closed state after)
with auto-retrying `wait_for_function`, with no sleep and no change to what is asserted. If a
product defect, stop and report without changing product code.

## Verification

Repeated runs of the test under CPU load, a deterministic reproduction of the late `toggle`
task, the whole display-looks browser file, ruff, comment-history guard, suite guards.
