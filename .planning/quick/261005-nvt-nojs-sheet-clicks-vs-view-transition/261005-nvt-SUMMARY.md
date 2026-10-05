---
quick_id: 261005-nvt
status: complete
---

# 261005-nvt summary

- Root cause: the app's cross-document view transition (installed only under
  `prefers-reduced-motion: no-preference`) overlays the page right after a navigation, so a
  coordinate click can hit `<html>`. Reproduced in isolation with two static pages.
- `companion/test_browser_ux_helpers.py`: `_no_js_page(..., reduced_motion=None)`; unchanged by
  default.
- `companion/test_browser_airline_sheet.py`: its three scripts-blocked tests pass
  `reduced_motion="reduce"`. No assertion changed.
- Not changed: tests that assert motion (toasts and others) keep the default.
