---
phase: 60-device-co-management
plan: 08
subsystem: companion-ui
tags: [co-management, browser-tests, playwright, css]
requires: [60-06]
provides:
  - Real-browser verification of the Co-managers card at 360 px (EN/FR, both themes), the leave/add/remove flows and Home refresh survival
key-files:
  created:
    - companion/test_browser_co_managers.py
  modified:
    - companion/static/style.css
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 08: Co-managers card browser verification Summary

19 Playwright tests drive the card in real Chromium at 360 px and found one real layout defect (the administrator's picker widened past the card), fixed with one additive rule.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Layout, tap-target, overflow tests at 360 px | 53044d6 | companion/test_browser_co_managers.py, companion/static/style.css |
| 2 Leave, add, remove and freshness flows | 53044d6 | companion/test_browser_co_managers.py |

Both tasks landed in one commit because the module was written and run as a whole.

## Touches Phase 55 code: companion/static/style.css

One rule appended directly after the `.co-manager__remove` rule (no other rule changed):

```
#co-manager-person { max-width: 100%; }
```

- Defect: with a 50-character invited address the admin `<select>` measured 484 px wide starting at x=41 at 360 px, running far past the viewport. After the rule it fits within the card and the page has no sideways scroll.
- No colour literal, keyframes, custom property or media block; no per-card height override. Nothing else in `style.css` was touched. The Leave summary and submit need no CSS: `.fleet-confirm` has no rule and the global `summary { min-height: 44px }` applies, measured at or above 44 px in the card at 360 px.

## Browser environment

The venv's Playwright (1.64.1) looks for chromium-1248 and the container has chromium-1243 at `/opt/pw-browsers`. I made a scratch directory outside the repo with symlinks named `chromium-1248` and `chromium_headless_shell-1248` pointing at the 1243 builds, and set `PLAYWRIGHT_BROWSERS_PATH` to it. No install was run and nothing in the repo changed for this. Every run used `SKYPANE_REQUIRE_BROWSER=1`.

## Test results (real browser, none skipped)

- `companion/test_browser_co_managers.py`: 19 passed, 0 skipped, 0 failed.
- Related browser modules (fleet page, console, console shell, home recent tiles, home state card, charging pill, phase44 walkthrough, device selector, toasts, plus the new module): 216 passed, 0 skipped, 0 failed.
- `test_browser_ux_01..04` (includes freshness): 103 passed, 0 skipped, 0 failed.
- `test_suite_guards`, `test_co_managers_page`, stylesheet/contrast/css tests: 362 passed. `stub-server/test_phase47_freeze.py`: 21 passed, unedited.
- ruff, mypy (28 files), `check_function_size.py check --max 80 server stub-server` (921 functions, none over 80), `check_comment_history.py`: clean.

## Coverage

- Containment at 360 px with 45 to 49 character addresses, EN and FR, light and dark: page `scrollWidth` equals 360, no inner scroll, address text inside its span, span inside row, row inside card.
- Add field and Add submit at least 44 px and stacked; Remove wraps beneath with the `--space-sm` gap and has the accessible name "Remove <email> from this frame".
- Co-manager view: no Add form or Remove buttons, "You" pill, Leave `<details>` closed with a summary of at least 44 px, opening it shows consequence, Leave submit (at least 44 px) and "Stay on this frame" in document order.
- Admin select stays inside the page; scripts-blocked context: details open and leaving works end to end; Account shows the Shared pill and the 40+ character owner line without overflow (EN, FR).
- Flows: leave lands on `/account` with the toast, frame gone, frame URL 404; stay changes nothing; add shows the toast and row; refusal shows one toast, empty field, no address in the URL or page; remove drops the row with the toast.
- Freshness: the page's own refresh fetch is answered with the real document plus a marker inside `.home-facts` (test-side route, no production hook); after the virtual clock advances the marker appears while the card keeps its sentinel `data-` property (same node), the typed text and the open Leave state.

## Deviations from Plan

- **[Rule 1 - Bug]** Admin select overflow fixed as above.
- The two tasks share one commit.
- The warning toast of a refused add has `role="alert"`, so that test selects the flash region's toast without the role filter.
- Pill text is read with `text_content` because CSS upper-cases it.
- No production files besides the single CSS rule changed; `home_page.py` placement needed no change.

## Known Stubs

None.

## Self-Check: PASSED (commit 53044d6, companion/test_browser_co_managers.py and this file exist)
