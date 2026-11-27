---
phase: 67-project-and-code-optimisation
plan: 08
subsystem: companion
tags: [refactor, dedup, escaping]
requirements: [QUAL-01]
key-files:
  modified:
    - companion/ui_base.py
    - companion/console_lifecycle.py
    - companion/pages/audit_page.py
    - companion/pages/fleet_page.py
    - companion/pages/users_page.py
    - companion/test_companion_app_02.py
metrics:
  completed: 2026-11-27
---

# Phase 67 Plan 08: Companion duplicate helpers Summary

Merged the AST-identical companion helpers (escape, owner_choice, `_ui`, `_routes`) by import with names preserved; `_safe_query` was left alone because its copies are not equivalent.

## Merged

| Helper | Result |
|--------|--------|
| `draw.escape` / `ui_base.escape_html` | Bodies identical once the docstring is set aside. Definition stays in `companion/draw.py` (stdlib-only; a draw -> ui_base import would break that boundary). `ui_base` re-exports it as `escape_html` (`ui_base.escape_html is draw.escape`). New test `test_the_page_shell_escaper_and_the_drawing_escaper_agree_on_hostile_input` pins both names to the same output over hostile markup, quotes, entities, None and non-strings. |
| `console_lifecycle._owner_choice` / `console_pairing.owner_choice` | ast.dump identical. Defined once in console_pairing; lifecycle imports it as `_owner_choice`. No import cycle. |
| `_ui` in audit_page, fleet_page, users_page | ast.dump identical (3 of 3). Now `ui_base.lazy_ui_components`, imported as `_ui`. |
| `_routes` in fleet_page, users_page | ast.dump identical (2 of 2). Now `ui_base.lazy_console_routes`, imported as `_routes`. |

## Left unmerged

- `_safe_query` in `health_signals`, `pages/history_page`, `pages/home_page`:
  - `history_page` has the same code as `health_signals` (only the docstring differs), but each module resolves `_DB_UNAVAILABLE` to its own sentinel object (`history_page` defines a separate `object()`). Merging would make `history_page` return the health sentinel and change its `is _DB_UNAVAILABLE` checks, so it is not the same behaviour.
  - `home_page` catches `Exception` and returns `None`, a different body.
  - `health_page` already aliases `health_signals._safe_query`.

## Deviations

- The escape definition stays in `draw.py`, not `ui_base.py` as the plan artifact said, to keep `draw` stdlib-only and avoid a boundary break. `ui_base.escape_html` is still the name every page uses.
- The first commit also contains the `lazy_*` helpers added to `ui_base`; the second commit wires them into the pages.

## Checks

- Collected test ids before vs after: `comm -23 before after` empty (17602 before, 17603 after; one added test).
- `pytest companion test-support stub-server -k "not browser"`: 8039 passed, 4 skipped (root permission skips, pre-existing). Includes `test_render_baseline.py` and the suite guards; render baseline files untouched.
- ruff, mypy (51 files), function-size gate, comment-history guard: clean.
- Browser tests not run here; they rely on CI.

## Self-Check: PASSED
