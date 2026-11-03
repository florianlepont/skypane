---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 03
subsystem: companion
tags: [list, row-menu, css]
requires: [61-02]
provides:
  - companion/ui_entity_list.py (entity_list_html, count_line_html, entity_row_html, row_menu_html)
  - entity-list and row-menu CSS
affects: [61-06, 61-08]
key-files:
  created:
    - companion/ui_entity_list.py
    - companion/test_ui_entity_list.py
  modified:
    - companion/static/style.css
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 03: Shared entity list Summary

One list component for Fleet, Users and My frames: `ul.entity-list` rows of an optional dot, a wrapping text block and one action, with a script-free `details.row-menu` whose dialog items are `data-modal-open` hash links.

## Tasks

1. Helpers (commit 9ab0610): `entity_row_html(dot_html, title, subtitle, pills_html, action_html, href=None)`, `entity_list_html(rows_html, count_line_html)`, `count_line_html(text)`, `row_menu_html(aria_label, items)` with items `(label, target, destructive)`. A lowercase-slug target is a dialog id (modal trigger); anything else is a path. Title, subtitle, labels, hrefs escaped; hostile strings tested; no table is emitted.
2. CSS and served-stylesheet test (second commit): grid `auto minmax(0,1fr) auto` (no-dot variant `minmax(0,1fr) auto`), hairline separators, `overflow-wrap: anywhere`, no monospace or ellipsis; from 960px `minmax(0,2fr) minmax(0,2fr) auto` (Users variant `3fr 2fr auto`) with the text block as a subgrid so the owner sits in its own column and the dot sits in the row padding; 44px toggle and items, `--shadow-pop` panel, destructive item in the error colour.

## Verification

ruff, mypy (28 files), comment-history, function-size clean. Full `-n auto` run over `companion` and `test-support` plus `stub-server/test_phase47_freeze.py`: 5739 passed, 3 skipped (root-ignores-permission-bits, pre-existing). Render baseline and digest pins did not move (no page adopts the list yet). Browser assertions on a real page remain with plans 61-06 and 61-08, as planned.

## Deviations from Plan

- `entity_row_html` takes `title` and `subtitle` as plain text (escaped in the helper) plus an `href` argument, rather than `title_html`/`subtitle_html`; this matches the plan's "escape everything" and the link-title requirement. The dot is wrapped in `span.entity-row__dot`.
- The CSS test was added in the CSS commit rather than the helper commit, to keep every commit green.

## Known Stubs

None.

## Threat Flags

None. T-61-03-01 (escaping, hostile-string tests) and T-61-03-02 (hrefs come only from the caller) are mitigated.

## Self-Check: PASSED
