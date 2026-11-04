---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 31
subsystem: companion
tags: [airline-editor, console, administrator-only, confirm-dialog]
requires: [61-17, 61-30]
provides: [Airline editor titled and framed in the Console, manual resolutions list with a named-dismiss delete dialog, R26 tests]
key-files:
  created:
    - companion/pages/airline_resolutions.py
    - companion/test_airline_editor.py
    - companion/test_browser_airline_editor.py
  modified:
    - companion/pages/airlines_page.py
    - companion/post_actions.py
    - companion/i18n_fr/airlines.py
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 31: Airline editor

`/airlines/manage` is the administrator-only Airline editor: titled "Airline editor" / "Éditeur de compagnies", in the Console chrome with the frame chip, and a new "Manual resolutions" list whose Delete link opens a confirm dialog "Delete this resolution?" with the destructive "Delete resolution" and the safe dismiss "Keep resolution" that takes the initial focus.

## What changed

- **Links and redirects.** Plan 61-30 had already moved every self-link, the five POST redirects, `resolve_dialog.return_route` and Health's Resolve link to `/airlines/manage`, and plan 61-17 made the page and the five POSTs administrator-only. Nothing was left to repoint; this plan only corrected a stale docstring in `post_actions.py`. The Health tests and `RESOLVE_LINK_HREF_TEMPLATE` already pinned the manage route.
- **Title.** The page header uses the existing `nav.airline_editor` message (EN/FR already present); the unused `_NAV_AIRLINES_TEXT` constant is gone.
- **Manual resolutions list** (`companion/pages/airline_resolutions.py`, new module so `airlines_page.py` stays near its size). One `special-row` per entry of the manual registry (prefix tag, airline name, Delete link). The Delete link is a hash link (`ui_modal.trigger_html`) to a per-row `ui_modal.dialog_html(..., destructive=True, confirm_only=True)` posting to the existing delete route with the page's token. Dialog ids are `delete-resolution-<10 hex of sha256(prefix)>`, so stored text never reaches an id or fragment; the action uses the URL-quoted prefix. Existing classes only (`special-list`, `special-row*`, `calendar-disconnect-btn`): no CSS change. Seven EN/FR strings under `airlines.*`.
- No change to handlers, validation, size limits, messages, `manual_resolutions` code or `panel-lookup.js`. The lightbox's own delete form ("Delete my name") is unchanged.

## Tests

- `test_airline_editor.py` (14, HTTP, real server, fleet with a co-manager): administrator rename, rename refusals (empty, too long, stale) reopening the sheet, rename reset, resolve in both steps plus empty and stale refusals, picture replace and bad-file refusal, delete, each redirecting to the editor on the chosen frame with its flash; the delete dialog markup (title, destructive submit, safe dismiss with autofocus, token); owner and co-manager get the unknown-path 404 for the page and for all five POSTs on both URL forms, with every stored file byte-identical afterwards; anonymous callers go to sign-in; Console chrome (current Console segment) and frame chip; no chip with a single frame; the Account page carries no editor link for owner or administrator. The other personal pages are already covered by `test_personal_space_parity.py` (forbidden "Airline editor" label and `/airlines/manage` path).
- `test_browser_airline_editor.py` (11, Chromium, not skipped): 360 and 1280 px x EN/FR x both themes (title, Console segment, chip, no overflow, 44 px hit targets); More then Airline editor on a phone (2 taps from the Console) and the sidebar link on desktop; the delete dialog (focus on Keep resolution, Tab and Shift+Tab never reach the page behind, Escape returns the focus to the Delete link); keeping leaves both rows, confirming removes one; scripts blocked (hash link shows the dialog, the POST works); rename end to end.
- **Measured A8** (change an airline's name, phone, from the Console landing): 5 actions (More, Airline editor, the airline row, the name field, Save name), as the plan expects (at least 5); desktop is one fewer (the sidebar link replaces More + link: 4). Asserted on the phone only.
- Stress: the new browser module run 4 times in parallel processes, 0 failures.
- Existing airline/Health browser tests and the pinned render baseline needed no change: `render_baseline.json` regenerated with no diff (no baseline page renders the editor with a manual resolution; sign-in digests unchanged).

## Deviations from Plan

1. **[Rule 2 - missing functionality] The editor had no manual resolutions list.** UI-SPEC 12.2 and dialog 13 assume "Delete on a manual resolution" in a list, but the page only offered the delete form inside the shared lightbox and the resolve fallback (its action is set by `panel-lookup.js`). The plan's fallback (keep the lightbox as the confirmation surface) would have left no "Delete this resolution?" dialog and no "Keep resolution" dismiss, which the plan's truths and Task 3 require. A compact list section with per-row dialogs was added instead; the lightbox delete form is untouched. If the owner prefers no list, the section can be dropped without touching the handlers.
2. The success path of a delete redirects to the editor with no flash (existing behaviour, unchanged), so the browser test checks the row disappearing, not a flash. Flash messages are removed from the URL by `flash-cleanup.js`, so the rename test waits for the toast text.
3. Task grouping: the plan asked for one commit; done as one commit plus this summary.
4. **[Rule 1 - pinned tests] Pins of the old page title moved in place.** The page title change broke `test_i18n` (the French `nav.airlines` entry lost its only declaring constant, so it was removed from `i18n_fr/nav.py`), `test_status_pages_05b` and two `test_view_pages_02` tests (they pinned the "Airlines"/"Compagnies" heading; now "Airline editor"/"Éditeur de compagnies"), and the French dialog title needed a non-breaking space before the question mark. `test_browser_ux_01`'s page-height ceiling at 390 px went from 3900 to 4100 px because the manual resolutions list adds about 120 px for the seeded registry (deliberate, as that test's docstring prescribes).

## State found at resume

The previous executor was interrupted with its work uncommitted: the page change, the new resolutions module, the French strings, the docstring fix, both new test modules and this summary were in the working tree. The code matched the plan and both new test modules passed; what was missing was the repair of the five pinned tests in item 4 (found by the full suite), the verification runs, and the commit.

## Known Stubs

None.

## Gates

ruff, mypy, comment-history, function-size (931 functions, none over 80) and the Phase 47 freeze test are clean. The new modules passed 3 runs in a row and 4 parallel processes of the browser module with 0 failures. The full companion + test-support + stub-server suite with `-n auto` ran after the last code edit (7378 passed, 4 skipped for root permission bits).
