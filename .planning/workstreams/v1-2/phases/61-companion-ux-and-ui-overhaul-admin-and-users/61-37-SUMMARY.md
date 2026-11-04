# Phase 61 Plan 37: Frame tile strip Summary

Owner decision D30 and W17 (mockup F2): the frame chip and card sheet are replaced by a strip of frame tiles, and the phone gear toggle is relabelled.

- **Strip (`ul.frame-tiles`, `companion/ui_shell.py`):** shown above the page title of device-scoped pages when the scope lists two or more frames (one frame still renders nothing, global pages none). One plain link per frame (no script, no dialog) to the same page of that frame under its `/devices/<id>` prefix (`device_scope.target_path`). Each tile: a CSS-drawn frame (bezel and screen tokens, no colour literals), the name, the status dot (single `frame_status` resolver) in the corner and the last-seen word ("Seen 2m ago" / "Vu il y a 2 min", "Not seen yet" / "Pas encore vu"), plus a muted note line only for co-managed or foreign-owned frames (owner email, kept for Console pages). Active tile: `aria-current="true"`, 2px accent outline with a faint wash. Tiles are 132px wide, at least 44px in both axes.
- **Add a screen tile:** dashed, last in the strip, links to `/fleet?pair=1` (the Fleet page with its pairing dialog open, the existing pairing flow). Shown to an administrator only (pairing is administrator-only in the access matrix), hidden for users and co-managers.
- **Layout:** horizontal scroller below 700px, wraps from 700px; both themes, 360px without page overflow.
- **Strings:** new `nav.frame_strip_aria`, `nav.frame_tile_seen`, `nav.frame_tile_add` in `companion/i18n_fr/nav.py`; removed the sheet strings (title, "Manage my frames", "Current", chip aria).
- **Gear toggle:** kept (it holds Sign out) but relabelled "Account menu" / "Menu du compte" (`nav.account_menu`, was "Account and preferences").
- **Tests (adapted in place, none weakened):** `test_frame_switcher.py`, `test_frame_sheet.py`, `test_device_selector.py`, `test_browser_device_selector.py`, `test_browser_frame_sheet.py` (strip markup, outline colour equals the accent, 44px, scroll on phone and wrap on desktop, Add tile for admin and absent for users, keyboard, scripts blocked, EN/FR, both themes at 360 and 1280); `test_device_links.py`, `test_device_routes.py` (links outside the strip), `test_co_manager_access.py`, `test_airline_editor.py`, `test_user_view_http.py`, `test_browser_airline_editor.py`, `test_browser_home_state_card.py`, `test_browser_overhaul_sweep.py` (frame sheet dialog case removed, it no longer exists), `test_browser_overhaul_steps.py` (S2 and U2 several now 1 tap), `test_status_pages_07.py` (toggle label). `render_baseline.json` regenerated, `test_sign_in_surfaces.py` shell and error-page digests regenerated deliberately.
- **Docs:** `61-UI-SPEC.md` section 1.5, strings table, journey rows and `61-STEP-COUNTS.md` updated.

## Deviations from Plan

- The class is `frame-tiles` (not `frame-strip`): `.frame-strip` already names the Home control strip.
- The tile does not show the hardware label the old cards showed (not in the mockup); owner email notes are kept.

## Self-Check: PASSED (see report for gate results)
