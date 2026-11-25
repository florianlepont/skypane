# Quick 261124-pl6 Summary: Plan 56 mobile fixes

Five owner findings fixed, one commit each (see `git log phase-68-plan-56-mobile-fixes`).

1. Anchor bar: strip only while stuck (`data-stuck`); bar and strip paint the page gradient slice (`--anchors-page-h`, `--anchors-y`). The existing "sticky bar is solid" test now waits for `data-stuck`.
2. Sheets: `dialog.modal::after` fixed strip, `--keyboard-inset` tall, `background: inherit`; mobile sheets lose their bottom border so no seam shows.
3. Airline card: first/last group and first row take `--radius-card - 1px`.
4. Add a frame: outer `page-section` removed, form carries `reveal`.
5. Background: second `<html>` layer, 200 px of `--sky-bottom` hanging below the box.

## Verification
- New Playwright tests for each fix; each failed against pristine origin/main (fix 3 only for the first row opened) and pass now.
- Affected browser tests (32 files, 884 tests), `test_companion_app_04`, `test_stylesheet_structure`, `test_i18n`, `test_suite_guards`, non-browser tests naming the changed modules: pass. ruff, mypy, function size and comment history pass.

## Not verified
- Real iOS Safari: the keyboard (fix 2) and the retracted toolbar window (fix 5) are emulated in Chromium (visual viewport height override; `<html>` forced shorter than the window).
- Fix 5 does not change the strip beyond 200 px of difference.
- Full suite not run.
