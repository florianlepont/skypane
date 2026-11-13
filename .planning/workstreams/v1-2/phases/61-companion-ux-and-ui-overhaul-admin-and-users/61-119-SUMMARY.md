# Phase 61 Plan 119: Audit 5, lot E (the remaining low findings) Summary

**Thirteen of the sixteen findings 61-118 did not attempt are fixed in fourteen commits (A5-14 in part); three are skipped with a reason (W5-18, W5-23, A5-21). Each fix has a behaviour or browser test seen red first, except the nested-entrance half of A5-12 (see below).**

Owner decision D56 (treat all audit-5 findings, in lots). There was no PLAN.md: the orchestrator's brief was the plan. Work is on top of the tip of `milestone/v1.2-phase-61-companion-ux` (lot D included) in a worktree; nothing was pushed. Commits carry `Claude Sonnet 5.5`.

## Per finding

| Id | What changed | Test (red first) | Commit |
|----|--------------|------------------|--------|
| W5-19 | `HEAD` answers like `GET` with the same headers and no body. `PUT`, `DELETE`, `PATCH`, `OPTIONS` answer 405 with an `Allow` header and the app's own page (English or French), never the standard library's English page. | `companion/test_http_methods.py` (new) | `b5588e65` |
| W5-10 | The "request refused, page expired" page links to the GET of the page the form came from ("Open the page again" / "Rouvrir la page") next to Back to Home, when that path is a page; never carries the query. Text no longer says "Reload" (a reload re-sends the stale POST). | `companion/test_csrf_reopen.py` (new) | `8f263852` |
| W5-14 | The Home quiet-hours dialog refuses equal start and end when the window is switched on, with a field error on the end time (EN/FR). A switched-off window keeps whatever times it has. | `test_quiet_hours_modal.py` (three tests) | `801d79e0` |
| W5-16 | A sign-in cancelled at the provider answers 303 to `/login?error=cancelled[&next=]` (closed set of codes), so reload and Back show the same calm "Sign-in was cancelled" page. Other failure kinds keep their pages. | `test_sign_in_cancelled.py` (new); `test_auth0_login.py`, `test_auth0_cookies.py`, `test_sign_in_messages.py` updated in place (status 400 became 303 plus the followed page) | `73f007d5` |
| W5-24 | An upload refusal names its rule: not a PNG, too large (size cap and pixel cap), not transparent, too small or portrait. Four new flash keys, EN/FR. The generic key stays for an unreadable body. | `test_airline_editor.py` (seven refusal cases plus French); `test_companion_app_05.py` updated in place | `c752d4a5` |
| W5-20 | Home's hidden "Frame state" h2 now follows the h1; the sign-in document has a `<main>`; the repeated "Special looks" h3 under its card h2 is removed (with its CSS); each Style page has its own title ("Special looks - Style - Kitchen - SkyPane", all eight distinct); the rename page title names the frame. | `test_page_structure.py` (new); `test_config_page_03.py` updated in place | `4fd57311` |
| W5-21 | After Cancel in the save bar focus returns to the control last changed. In the Flights and Airlines sort menus an arrow key keeps the menu open on the choice; a pointer choice still closes it. | `test_browser_cancel_focus.py` (new); two sort tests in `test_browser_flights_search_more.py` | `07c681d8` |
| W5-11 | The first live search gets a history entry of its own, so Back returns to the unfiltered list instead of leaving Flights. | `test_browser_flights_search_more.py`; `test_browser_audit3_fixes.py` updated in place (the two tests that pinned "the first search rewrites the opening entry") | `07c681d8` |
| W5-09 | The Users Active switch confirms each change with the same toast the no-script path shows ("User disabled", "User enabled", EN/FR). The fetch answer is a 200 carrying the toast and an `X-Quick-Switch-Result: toast` header; the script parses it with `DOMParser` (no markup sink) and arms its auto-hide. | `test_browser_users_page.py` (EN and FR); `test_frame_rename_and_users_switch.py` updated in place (204 became 200 plus toast) | `30f5ecc9` |
| X07 | The upload and delete buttons of the resolve step and the gap row's Validate and Ignore are the shared buttons (44px, bordered Ignore); the custom `.airlines-resolve__ok/__skip` rules are gone. | `test_browser_resolve_buttons.py` (new, 360 and 1280, EN and FR, with and without scripts); `test_status_pages_06.py` and `test_browser_airline_table.py` updated in place | `d23cf698`, `f186c636` |
| X17 | In the Components catalogue the open menu specimens open under their toggle inside the window, and the save-bar specimen buttons hold their French labels. | `test_browser_components_page.py` (two tests across 16 combinations) | `e0b95dcf` |
| A5-12 | The pull spinner turns 9 times (6.3 s, matching the 6 s give-up) instead of forever. | `test_browser_motion_live.py` | `0b8bab5f` |
| A5-14 (part) | `--motion-picture` (480 ms) and `--motion-unlock` (560 ms) tokens; the picture transition, the unlock flip (also on `--motion-spring`) and the glint and sparks (on `--motion-reveal` and `--ease-out`) read them. | `test_browser_motion_unlock.py` (overrides the tokens and reads the real durations) | `0b8bab5f` |

Updated in place because they pinned the old behaviour: `test_companion_app_04.py` (the motion token list), `test_config_page_03.py` (the reset handler's timer window), `test_export_battery_history.py` (HEAD on the export now answers headers with no rows, with a new test) in `e2b1b669`.

## Skipped or not fully done

| Id | Reason |
|----|--------|
| W5-18 | Two designs (carry the unsaved layout in the address of the next Style page, or an app dialog with Save and Discard) and either one changes how every Style view is rendered. Needs the owner's choice. |
| W5-23 | Moving the anti-forgery token out of the upload address means the strict one-file-part upload parser accepts a second part and every upload test changes. The token is a hash of the session, and the referrer policy is same-origin. Better as its own plan. |
| A5-21 | The 0.146 shift is the Load more block moving down as rows are inserted above it, which is the intended result; the observer counts it because the tap and the insertion are more than 500 ms apart. Anchoring it differently would reverse the tested "land on the first new row". |
| A5-12 (nested entrance) | Not reproduced: after a pull that swaps a changed list only the new row's arrival and the card stagger play, no page-opening entrance on the group (lot D closed it with A5-09 and A5-17). The test guards it and passes without a change. |
| A5-14 (splash, Leaflet, strip thumb) | The splash is one authored sequence (eight phases) that nothing else shares; eight new tokens would serve nothing. Leaflet's 250 ms is inside the vendored library. The strip thumb already glides in the view transition since lot D. |

## Tests run

- Before each commit: ruff, mypy, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_stylesheet_structure.py`, `test_components_page.py`, `test_browser_ux_02.py`, `test_render_baseline.py`, `test_sign_in_surfaces.py`, `test_suite_guards.py`, `test_i18n.py`, and the files of the area touched (largest run: 2,014 tests around Home, Style and sign-in).
- New browser tests were run three times in a row (four processes for the Flights and Users ones).
- After the last code commit: every non-browser test of `companion`, `test-support`, `stub-server` and `server` with `-n 8`: 11,134 passed, 7 skipped (root cannot test permission bits), 3 failed; the three were the tests listed above, fixed in `e2b1b669` and re-run green. Not run: `./scripts/run-all-tests.sh` (coverage gate) and the browser files of untouched areas, per the test cadence.

## Deviations

- Commit `d23cf698` went in with `test_status_pages_06.py::test_upload_forms_native_controls_are_unchanged_by_the_drop_zone` red (its fix is `f186c636`, next commit): do not push between those two.
- The earlier commits `b5588e65`, `07c681d8` and `0b8bab5f` each left one pinned test red (the export HEAD test, the reset-handler timer window, the motion token list); `e2b1b669` fixes all three. Do not push before that commit.
- `companion/app.py` is at 1,497 of 1,500 lines (it was 1,493); `list-filter.js` 975 and `motion.js` 1,082.

## For the orchestrator

- `HEAD` now works on every GET route, including the bearer-token export (headers only, never rows).
- The `/login` page now has a closed-set `?error=` parameter (only `cancelled`).
- The design-system skill (`sketch-findings-skypane`) was not edited: it does not yet mention the two new motion tokens or the page-title rule for Style pages.

## Self-Check: PASSED

All fourteen commits exist on the worktree branch above `milestone/v1.2-phase-61-companion-ux`; the new test files (`test_http_methods.py`, `test_csrf_reopen.py`, `test_sign_in_cancelled.py`, `test_page_structure.py`, `test_browser_cancel_focus.py`, `test_browser_resolve_buttons.py`) exist; ROADMAP, STATE and REQUIREMENTS, `hardware/`, `deploy/` and the frame protocol were not touched; nothing was pushed.
