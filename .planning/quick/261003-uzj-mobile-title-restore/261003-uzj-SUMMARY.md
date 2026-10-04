# Quick 261003-uzj Summary

Restored the visible page title on every page and width, and tightened the phone top spacing instead.

- Removed `page_header(..., tabbed=)`, the `page-header--tabbed` class and its CSS, the call-site arguments and the served-HTML tabbed test.
- Spacing (< 960px): `.site-header` margin-bottom `--space-xl` (32) -> `--space-md` (16); `.page-content` padding-top `--space-xl` (32) -> `--space-md` (16). App bar to title: 64 -> 32px. Title to first block (header margin-bottom `--space-lg`, 24) and the tab-bar bottom padding are unchanged. Desktop (>= 960px) unchanged; no new off-scale sizes.
- `companion/test_browser_page_title_phone.py` retargeted: title visible on all seven pages at 360/390/1280, light/dark, EN/FR; phone gap <= 32 (bounding boxes); no overflow.
- `render_baseline.json` regenerated; diff inspected: exactly 20 occurrences of `page-header page-header--tabbed` -> `page-header`.
- Screenshots: `/tmp/claude-0/-home-user-skypane/d89080dc-5e3d-5e46-9cec-c090cb9715bb/scratchpad/shots-uzj/{before,after}/sheet-{390,360}-{light,dark}-{en,fr}.png` plus metrics.json.
- Verification: full `./scripts/run-all-tests.sh` 3738 passed, 8 skipped (root-permission/openssl skips); ruff, mypy, comment-history, function-size all green.

Deviations: none.
