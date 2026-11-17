# Phase 61 Plan 116: Audit 5, lot B (workflow fixes) Summary

**Four audit-5 workflow findings closed, plus one residual of lot A: a place-saved toast that names what was saved, a confirmation before any role change, a Save bar that follows a choice the browser restored on Back, and a translated 500 page instead of a dropped connection. Each has a behaviour or browser test that was seen red without the fix. X03 is not addressed.**

Owner decision D56 (treat all audit-5 findings, in lots). This is the second lot. There was no PLAN.md: the orchestrator's brief was the plan. The branch was one commit behind `origin/main`; it was merged first (clean, no conflict).

## What is fixed, per finding

| Id | Fix | Commit |
|----|-----|--------|
| W5-02 | The toast is built from the stored setting, not from the label field. A runway setting names its airport; My position reads "the area within N km of" the place, with the coordinates when the place has no name of its own. A My position save drops a label that is the name of an airport the pin is no longer on. The Location status line stops naming the airport once My position is chosen. | `7ad7ef78` |
| W5-04 | A changed role select, or the no-script Save role button, lands on the Users page with a confirmation dialog open (`/users?role_change=N&role=...`). Only the dialog's button writes the role. Promotion and demotion both ask, in English and French; the focus is on the way out, so Enter never confirms. | `59555c61` |
| W5-01 | On `pageshow`, when the form differs from what the page loaded with, the Save bar, the Layout card's summary and the value controls are brought in line with the form. | `02469970` |
| W5-06 | The one dispatch is guarded (`companion/server_error.py`). An unexpected exception is logged once (method, path without its query, traceback) and answered with a 500 page in the app's chrome, in English or French, with a link back. | `956396b8` |
| X02 (residual of 61-115) | On a narrow phone the person row keeps 4px instead of 8px before its action, so `admin@example.test` shows whole at 360px in French. The layout is unchanged, so the pinning test in `test_browser_remaining_audit_fixes.py` was not touched. | `2970f062` |

## Tests added or changed

New:

- `companion/test_place_save.py`: a pin moved off an airport drops the airport's name from the stored place and the toast (EN and FR); a pin left on the airport keeps it; the runway toast names the saved airport, not a typed label.
- `companion/test_browser_place_pins.py`: the whole journey in a browser, EN and FR (pick an airport, choose My position, tap the map, save).
- `companion/test_console_users.py`: a role change redirects to the asking address and writes nothing; the dialog's words in both languages and both directions; an address that asks nothing real opens no dialog.
- `companion/test_browser_users_page.py`: the role is saved only after the confirmation (360 and 1280); backing out changes nothing and the address forgets the question; the 500 page at 360px in both languages and themes.
- `companion/test_browser_save_bar.py`: Back to Style with an unsaved layout shows the bar and a matching summary at 390 and 1280; Cancel returns to the stored layout.
- `companion/test_server_error_page.py`: the 500 page on a GET and a POST, for a visitor without a session, and when the chrome itself cannot be built; one traceback per failure; the server keeps answering.

Updated in place because their subject changed:

- `test_place_save.py`, `test_place_page.py`, `test_browser_detection.py`: the My position toast now reads "the area within N km of ...".
- `test_console_users.py`: `test_promotion_needs_no_confirm_...` became `test_a_confirmed_promotion_is_audited_...`; role posts that are meant to take effect carry `confirmed=1`.
- `test_browser_users_page.py`: the no-script flow confirms the role in the dialog.
- `test_browser_overhaul_steps.py`: task A9 takes one more tap; its measured count goes from 2 to 3.
- `test_browser_french_fit.py`: the owner's address must be whole at 360px too.

## Tests run

- Before each commit: ruff, mypy, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_render_baseline.py`, `test_sign_in_surfaces.py`, `test_suite_guards.py`, `test_i18n.py`, and the test files of the touched pages. Each new browser test was run in four parallel processes without a failure.
- After the last code commit (`2970f062`): `companion`, `test-support` and `stub-server` without the browser tests, `-n 8`: 7503 passed, 4 skipped. The browser files of the touched areas (Location, Users, the step counts, the Save bar, the Fleet dialogs, French fit), `-n 6`: 381 passed.
- The four skips need a non-root user (`test_companion_app_01.py:664` and `:704`, `test_freshness_token.py:348`, `stub-server/test_byos_hardening.py:528`). They cover file permission bits, which this plan does not touch.
- Not run: the other browser files and `./scripts/run-all-tests.sh` (coverage gate), per the test cadence.

## What falls short

- **X03 (Users table, desktop) is not addressed.** At 1280px the table is 864px wide. Keeping "Jamais connecté" on one line needs 33px more in its column, and the only place to take them is the address column, where `admin2@example.test` already wraps. Even row heights need a design choice (one-line addresses with an ellipsis, shorter wording, or a narrower role column), not a small CSS change.
- **W5-04 contradicts two earlier records.** `61-UI-SPEC.md` (line 232) lists Save role as non-destructive and saved on change, and task A9 has a target of 2 actions; it now measures 3 and the test prints `MISSED` against that target. The measured value in the test was updated; the spec was not edited.
- **W5-04: the guards run after the confirmation.** A hand-made request to demote oneself or the last administrator gets the dialog first and the refusal after confirming. The page itself offers no select on those rows.
- **W5-01 relies on `pageshow`.** The snapshot is still taken when the script starts. In Chromium the browser restores the fields after that, so the bar shows. A browser that restores them before deferred scripts run would take the restored values as the baseline: no bar and no leave prompt. Not tested outside Chromium.
- **W5-01: the form pages were only probed, not tested.** New special look and Calendar connect do not get their values restored on Back in Chromium, so they have nothing to reconcile; no test pins that.
- **W5-06: a failure after the response started is not tested.** The connection is then closed, as before. The 500 page shows the navigation of the scope the failed request had set, which can differ from the 404 page's navigation for the same person.
- **W5-02: a place saved without a name is still stored as "Frame position"** (in English), as before. The toast shows its coordinates instead, but Home's Detection card still reads "within N km of Frame position".

## Deviations

- **Commit trailer.** The executor rules ask for a `Claude Sonnet 5.5` co-author line; the brief asks for the model doing the work, so the commits carry `Claude Fable 5.2`.
- **Role confirmation is a server round trip**, not a script-opened dialog: the select submits as before and the next page opens on the dialog. It works the same without scripts, and nothing is written until the dialog's own post. `modal.js` gained one hook (`data-modal-return`) so that closing the dialog in place also clears the asking address.
- **The W5-02 browser test lives in `test_browser_place_pins.py`**: a separate file importing that file's helpers tripped the suite guard against test modules importing each other.
- **No `/components` change.** The role dialog is the catalogue's existing confirmation dialog and the 500 page is the existing error-page pattern; no new component was introduced.
- `companion/app.py` is at 1492 lines (ceiling 1500).

## Self-Check: PASSED

All five commits exist on `milestone/v1.2-phase-61-companion-ux`; `companion/server_error.py` and `companion/test_server_error_page.py` exist; nothing was pushed; the two untracked `.whl` files in the repo root were not touched; ROADMAP, STATE and REQUIREMENTS were not edited.
