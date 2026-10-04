---
quick_id: 261003-se6
completed: 2026-10-03
commits: [d233e6e1]
---

# Quick 261003-se6: Pending toasts auto-hide after 12 s

Pending toasts now carry `data-toast-autohide="long"` and the timer hairline; toast.js reads `--motion-toast-dwell-long` (12s) for them and `--motion-toast-dwell` (6s) for success/info, with the same hover/focus/hidden-document pause. Warning and error never auto-hide; docked surfaces and the no-JS flow are unchanged; reduced motion unchanged.

The motion-budget exception now covers two tokens, each spent by exactly one armed hairline rule. Tests added: served HTML (EN/FR), browser timing (6 s still present, gone after 12 s), hover/focus pause, warning/error never hide. Render baseline regenerated after review: only the 8 `flash=saved` pages changed, by the attribute value and the timer span.

Verification: full run-all-tests 3715 passed, 8 skipped; ruff, mypy, comment-history, function-size clean.

Deviations: none.
