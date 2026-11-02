---
phase: quick-261102-p1c
plan: 01
status: complete
completed: 2026-11-02
commits: [4f99afcd, df6c09c3]
---

# Quick 261102-p1c: lists invisible at desktop width Summary

Two table-less `.data-cards` lists (Co-managers card, Account "Your frames") now stay visible at >= 960 px via a `data-cards--standalone` modifier and one higher-specificity CSS rule.

## Changes

- `companion/static/style.css`: `.data-cards.data-cards--standalone { display: block; }` after the base `.data-cards` rules; no new colours, tokens or media blocks.
- `companion/pages/co_managers_card.py`, `companion/pages/account_page.py`: `<ul class="data-cards data-cards--standalone">`.
- `companion/test_browser_co_managers.py`: 7 real-browser tests (Co-managers list and rows at 1000/700/360; Account frames list and row at 1000/700/360; Shared row for a co-manager at 1000). The 1000 px cases and the Shared test fail without the CSS rule.

## Touches Phase 55 code

`companion/pages/account_page.py` (`_frames_card`) is Phase 55 code. Only the class attribute on the `<ul>` changed; row markup, ordering, empty state and i18n are untouched.

## Verification

- Browser, status-page and Co-managers page modules: 1142 passed.
- ruff, mypy, comment-history, function-size (922 scanned, none over 80): clean; `stub-server/test_phase47_freeze.py`: 21 passed (unedited).
- `./scripts/run-all-tests.sh` (no arguments): 8699 passed, 8 skipped (root permission-bit and openssl skips), exit 0.

## Deviations

None.
