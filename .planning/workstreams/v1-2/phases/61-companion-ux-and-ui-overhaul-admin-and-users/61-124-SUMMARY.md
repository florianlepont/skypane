# Phase 61 Plan 124: Pairing code cookie and upload token out of the address Summary

Two security-minded form findings: a refused pairing code is kept for one showing of the form in a two-minute cookie (W5-15, owner option A), and the anti-forgery token of the airline artwork upload moves from the address into the request body (W5-23).

## Commits

| Finding | Commit | What |
|---------|--------|------|
| W5-23 | f883306d | Upload token as a leading `csrf_token` text part; new `companion/upload_form.py` |
| W5-15 | faec2010 | `companion/pair_code_cookie.py`, wired in `companion/user_pairing.py` |

## W5-23

- All four upload forms (change artwork, lightbox replace form, resolve-step upload, dialog form) carry a hidden `csrf_token` field before the file input; no action URL carries the token. `ui_components.csrf_query` is removed.
- `upload_form.read_upload` reads the first 512 bytes of the body, extracts the token (strict: first part, field name exactly `csrf_token`, no filename, `[A-Za-z0-9_-]{1,128}`), then reads the rest under the same 4 MB cap. The dispatcher checks the token before the handler runs, so an oversized upload with a good token still gets the "too large" refusal, and one with a bad token gets the expired-page 403.
- The strict parser (`parse_single_uploaded_file`, now in `upload_form`) accepts exactly one file part, optionally preceded by that one token part. Two file parts, a token after the file, a token with a filename, another field name, an oversized or odd token are refused. No new file parts.
- Old URLs: a token in the query string is ignored (never read); without the body part the upload is refused as an expired page (403, existing message). The 61-119 refusal messages are unchanged.
- app.py: 1493 lines (net down 4).

## W5-15

- Cookie `sp_pair_code`: HttpOnly, SameSite=Strict, Secure via `auth.secure_cookie_flag()` like every app cookie, `Path=/pair-frame`, `Max-Age=120`. Value is `<16-hex session key>.<code>`; the code is upper-cased, spaces removed, cut to 12 characters (the field's maxlength) and must match `[A-Z0-9-]`, otherwise nothing is stored.
- Set only on a refused code (on the existing 303 to `/pair-frame?refused=1`; Location unchanged). On the next GET of the form the code is put back in the field and the cookie is ended (`Max-Age=0`). A cookie from another session is not reflected, but is also ended. Output goes through the existing escaping; the value is re-validated on read.
- The administrator Fleet add dialog already re-renders in place with the code, so it needed no change. Access log prints method and path only, so the code never reaches it.

## Tests

Updated in place: every upload test (`test_csrf`, `test_companion_app_02/04b/05`, `test_airline_editor`, `test_airline_sheet`, `test_device_actions`, `test_access_matrix`, `test_health_resolve_dialog`, `test_browser_airline_table`; helper `with_csrf_part` replaces `csrf_url` in test-support), `test_user_pairing` and `test_browser_user_pairing` (field now prefilled). New: parser token cases, strict token part, old-URL refusal, oversized with good/bad token, served forms carry the field and not the address, browser upload sends no token in any request URL; pairing: prefilled once, attributes, long/odd values, another session, no code in Location/logs/database, with and without scripts.

## Deviations

- Tests were written together with the code rather than run red first; the old-URL, Set-Cookie and prefill assertions cannot pass on the previous code (they read a header or field that did not exist).
- Hyphen is kept in the stored code (field is `KKKK-2222` as typed).

## Verification run

ruff, mypy, check_comment_history, check_function_size, stub-server/test_phase47_freeze.py: green. Render snapshot regenerated: no change. Tests run (`-n 4/6 --no-cov`): test_csrf, test_companion_app_02/04b/05, test_airline_editor, test_airline_sheet, test_device_actions, test_access_matrix, test_health_resolve_dialog, test_airline_manage_routes, test_device_routes, test_status_pages_05b/06, test_browser_airline_table, test_browser_ux_04, test_browser_resolve_buttons, test_stylesheet_structure, test_components_page, test_http_methods, test_sign_in_surfaces, test_suite_guards, test_account_page, test_frame_sheet, test_frame_switcher, test_route_table, test_console_pairing, test_user_pairing, test_browser_user_pairing (3 runs), test_browser_personalisation_pairings, test_browser_frame_menu, test_browser_device_selector, test_browser_round8_fixes. Full suite not run locally (cadence).

## Self-Check: PASSED
