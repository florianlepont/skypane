---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 09
subsystem: companion
tags: [frame-switcher, home, status-dot]
requires: [61-01, 61-04]
provides: [ui_shell.frame_switcher_html, device_scope.switcher_entries, Home status dot from frame_status]
key-files:
  created:
    - companion/test_frame_switcher.py
  modified:
    - companion/ui_shell.py
    - companion/device_scope.py
    - companion/device_dispatch.py
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/static/nav-dropdown.js
    - companion/i18n_fr/nav.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 09: Frame switcher and Home Summary

A `details.frame-switcher` replaces the frame select on every device-scoped page, and Home reads the frame state from one dot that uses the same words as the Fleet list.

## Commits

- e7f6bf4: frame switcher (task 1)
- 328b4cc: Home rework (task 2)
- 4bc7ea3: browser checks (task 3)

## What changed

- `ui_shell.frame_switcher_html` replaces `device_selector_html` in the same shell slot: summary with dot, name and chevron (accessible name "Switch frame, current: %s"), one 44px link row per frame to `device_scope.target_path(page, device)` (the page is kept), `aria-current` on the current frame, footer "My frames" (`/account#account-frames`) and, for admins, "All frames (Fleet)". Rendered only with two or more listed frames and on device-scoped pages. Works without script; `modal.js` already closes it.
- `device_scope.switcher_entries()` builds the list from the request scope. A user's list is their scope (owned and co-managed). An admin's scope is every frame, so it is cut to frames they own or co-manage plus the one being viewed. Co-managed rows read "Shared · owner email"; an admin viewing someone else's frame sees the owner email on that row. Emails are read only for those rows.
- `set_request_scope` gained optional `viewer_id` and `root` arguments (backward compatible); `device_dispatch` passes the principal's user id and the state root.
- The `?device=` GET redirect (`switch_target`) is kept so old bookmarks still work. The select form, its CSS and its arming code in `nav-dropdown.js` are removed; the unused selector messages and FR keys are replaced by four switcher keys.
- Home: the dot comes from `frame_status` (row built from the page context: offline, last check-in, battery percent, `frame_state`, screen off; a battery-empty hold counts as a low battery). The dot is a `role="img"` with the state word. The existing headline sentences stay. "See Health" shows only when the dot is amber or red. A plain user's Home has no battery tile (the status card layout adapts) and no attention bar. The admin Home keeps both.
- CSS: `.frame-switcher*`, `.home-state--error` tone, `.home-state--no-battery` layout.

## Deviations from Plan

1. **[Rule 3] Files outside the frontmatter:** `companion/device_dispatch.py` (pass viewer id and root into the scope), `companion/test_co_manager_access.py` and `companion/test_user_view_http.py` (assertions on the removed `<option>` markup; one new user Home test added).
2. **Co-managers card on Home left in place.** `home_page.render` still accepts `co_managers_html` and `routes.py` still passes it. The removal is owned by plan 61-07 (Task 2 there), which has not run yet; removing it here would break that plan's tests and the Manage access dialog is not available yet. 61-07 must delete the argument and the `co_managers.card_html` call.
3. **Behaviour change in Home dot:** a frame two wake intervals past its expected wake (`STATE_LATE`) now shows the amber "Overdue" dot with the Health link (it stayed green until three intervals before). This is the spec 3.1 rule. The Fleet list does not feed `state` to the resolver, so it shows "Up to date" for such a frame until it goes offline; the two words differ only in that window.
4. **Pinned outputs moved deliberately:** `render_baseline.json` regenerated (the four Home bodies only). Existing Home tests were updated in place for the overdue dot and the user view; the browser 16-minute case now expects the amber dot and link.
5. **Test admin is not the fleet owner.** `test_device_selector.py` now signs in as the fleet owner (an administrator who owns all frames) so the admin list holds more than the viewed frame.

## Known Stubs

None.

## Threat Flags

None. T-61-09-01: links are built from the request scope's own frame list, no request text; access checks unchanged. T-61-09-02: owner email only on rows the viewer co-manages, or on the viewed foreign frame for an administrator (test_frame_switcher covers both and the escaping).

## Gates

ruff, mypy (28 modules), comment history and function size (922 functions, none over 80) clean. Companion plus test-support plus Phase 47 freeze suite with `-n auto`: 5883 passed, 3 skipped (root-permission tests, no browser skips).

## Self-Check: PASSED
