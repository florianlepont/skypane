# Phase 61 Plan 102: Rename returns to the page of origin Summary

W168: the Home pencil, the Fleet header Rename and the Account Manage access link now carry a safe `return_to`, and the dedicated rename page sends Back, Cancel and Save to that page (Home for the pencil), never to a console settings page unless the origin was the console.

## Scope change

The owner dropped the in-place dialog during execution: a dedicated rename page is fine. No modal, JS or CSS was added; the pencil and links stay plain links.

## What changed

- `companion/pages/frame_name_page.py`: `device_route(id, return_to)` builds the link; the form carries a hidden `return_to`; the page uses the common page-mode Cancel/Save bar (Cancel is a link to the origin) and the Back link points to the origin.
- `companion/frame_rename.py`: `return_to` is validated with the sign-in `next` check (allow-listed page routes, strict query), the rename page itself is refused, and console pages are refused for non-administrators. Absent or hostile values fall back to the old defaults. Save answers a 303 to `return_to` (console toast cookie for an administrator returning to a console page, `?flash=` otherwise). The page is drawn in the console chrome only for an administrator who came from a console page; everyone else gets the personal chrome. Authorisation, CSRF and the `device.rename` audit row are unchanged.
- Links: `home_title.py` (return to the frame's Home), `fleet_page.py` (`/fleet?frame=<id>`), `co_managers_card.py` (the sheet's own return path).
- Render baseline regenerated. No stylesheet/script change (digests and goldens untouched, guards green).

## Tests

Updated in place (link hrefs, page-mode bar): test_home_title, test_console_fleet_page, test_frame_rename_and_users_switch, test_audit3_fixes, test_browser_fleet_page, test_browser_fleet_users_fixes, test_browser_components_page. New: server tests for safe/hostile `return_to`, refusal keeping the origin, console origin only for admins; browser tests (Home 390/1280) for Cancel, Back link, Save ending on Home with the new name, browser Back landing on Home, empty name error keeping the way back, hostile `return_to` ignored, no-JS pencil/Save/Cancel, admin from Fleet ending on Fleet.

## Deviations / notes

- Browser Back after a Save lands on the rename page (a Save is a normal navigation), not on the page before Home; from the rename page Back lands on Home. No console page is ever in the history.
- Owners in the test fleets are administrators, so default (no `return_to`) Back/Save for them still goes to Fleet settings as before.
- Screenshot: scratchpad/shots102/rename-from-home-390.png.

## Known Stubs

None.
