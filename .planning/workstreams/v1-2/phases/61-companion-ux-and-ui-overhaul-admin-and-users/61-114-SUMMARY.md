# Phase 61 Plan 114: Primary pair-link button invisible text (audit finding X01) Summary

**The primary "Add your frame" button is readable again: its variant rules now sit beside the base rule in the admin sheet, and a guard test catches any modifier rule that loads before its base.**

## Cause

After the stylesheet split, `a.pair-link` (colour accent) lived in `style-admin.css`, loaded after `style.css`, where `a.pair-link--primary` (colour on-accent over an accent fill) was declared. Equal specificity, later sheet wins: accent text on an accent fill, 1.00:1.

## Fix

- Moved `a.pair-link--primary` and `a.pair-link--primary:hover` from `companion/static/style.css` into `companion/static/style-admin.css`, directly after `a.pair-link`. Each selector is still declared once.
- Render baseline regenerated (CSS bytes changed).

## Other base/modifier pairs split across sheets

Audited the served sheets two ways: BEM modifier (`--x`) selectors whose base rule sits in a later sheet, and any selector declared in more than one sheet. Only `a.pair-link--primary` (and its `:hover`) was affected. No selector is declared in two sheets. Cross-sheet prefix matches that remain are descendant or child selectors on different elements, or hover/active/attribute variants of higher specificity (for example `.btn.btn--primary:hover` in core over `.btn.btn--primary` in c-console), so load order does not decide them.

## Tests added

- `companion/test_stylesheet_load_order.py`: for every page family (each route in `page_styles`, a device-scoped display route and an unknown route), fetches the served sheets in link order and fails when a modifier rule (`--` suffix) is in a sheet before a same-specificity base rule that sets a shared property; includes a self-test of the detector.
- `companion/test_browser_user_pairing.py`: contrast of the "Add your frame" button text against its fill is at least 4.5:1, EN and FR, light and dark.

## Deviations

None to the plan. Process note: one accidental `git stash` / `git stash pop` in the worktree (restored in full, stash list empty afterwards).
