# Phase 68 Plan 26: Correction 2 (owner decisions of 2026-11-19) Summary

Follows `68-26-SUMMARY.md` and `68-26-CI-FIX-SUMMARY.md`. Applies the four owner decisions on the Fleet list and switch. Out of scope and untouched: tiles, Health and Versions pages, State / Settings / Access sections (plan 35), the suggestions plan, STATE.md, CON-01, the plan count in ROADMAP (plan 26 stays counted 29/36).

## Per-change table

| # | Owner decision | Change | Where | Commit |
| --- | --- | --- | --- | --- |
| 1 | Row detail stays status first ("Online · owner") | Kept as built; nothing changed. | `pages/fleet_frames_list.py` | none |
| 2 | System moves out of the list into the console navigation | One nav table: `CONSOLE_NAV_ENTRIES` gets a `system` entry (path `/fleet?view=system`, label `nav.system`, existing pulse glyph, no sprite change). Sidebar: after Audit log in the second group. Phone: a row in the More sheet between Account and the space switch (drawn like the Account row). The entry is marked current on its own view and Fleet is not (the request query is now kept beside the path in `prefs`). The System row and its two ids leave the list. EN "System", FR "Système". `/fleet?view=system` and the access rules (only an administrator has the Console navigation; a plain user still gets the unknown page) are unchanged. | `console_routes.py`, `ui_nav.py`, `prefs.py`, `app.py` (same line count), `i18n_fr/admin_shell.py`, `i18n_fr/admin_fleet.py`, `pages/fleet_frames_list.py`, `console_fleet_view.py` | 16170bd6 |
| 3 | Retired row says "Retired 12 Oct", pending row says "Code shown 5 min ago" | Retired row: `owner · Retired 12 Oct` (year added only when it is not the current one, Paris clock); FR `Retiré le 12 oct.`. Pending row: `Code shown 5m ago` (the shared age ladder, same as "Seen 2m ago"); FR `Code affiché il y a 5 min`. A row without the stored moment keeps "Formerly owner" / "Waiting for pairing". Everything goes through the escaping row helper. No new route, access matrix unchanged. | `console_pairing.py`, `pages/fleet_page.py` (two optional `FleetRow` fields), `pages/fleet_frames_list.py`, `i18n_fr/admin_fleet.py` | 3b11b9f3 |
| 4 | Desktop: full-height column attached to the sidebar | From 1200px the list is a 350px glass panel with the sidebar's top, height, radius, fill and shadow, 16px from it, with a fixed header (title, Add, search) and a body that scrolls on its own; it stays put while the frame column scrolls the page. The selected frame fills the rest (max 760px of content, 32px left / 48px right padding). The page column drops its cap and padding on this page so the panel touches the sidebar at 1200, 1440 and 1920px. Below 1200px the phone layout is unchanged. The unsaved-changes bar docks under the frame column. One visible `h1` at every width, opening animation and motion pins unchanged and green. | `static/style-admin.css` | 370886c1 |
| - | Tests and baseline | See below. | tests, `testdata/render_baseline.json` | see Commits |

Commits (all on `phase-68-visual-improvements-3`, not pushed): 16170bd6 (System in navigation), 3b11b9f3 (retirement day and code age), 370886c1 (full-height list column), then two follow-up test commits (navigation tests, page tests and the single-`align-items: start` rule) and the render baseline regenerated once at the end.

## Tests

New behaviour, written as served-HTML or browser tests (no source-text assertions):

- Navigation: System in the sidebar and in the More sheet, EN and FR, current on its own view only, Fleet current everywhere else; absent from a user's navigation (`ADMIN_WORDS`); the list has no System row.
- Rows: retired date in EN and FR (with and without the year), fallback to "Formerly" when no date is stored, pending code age in EN and FR, fallback to "Waiting for pairing" when no code is stored.
- Layout (browser, 1200 / 1440 / 1920px): list 350px wide, same top and height as the sidebar, at most 24px from it, frame column after it and inside the viewport, header fixed while the body scrolls, list unmoved when the page scrolls, no overflow, one visible `h1`; at 1199px the list is not a column; the unsaved-changes bar sits under the frame column and clear of the list.

Existing tests updated to the approved behaviour (none skipped or loosened): the sidebar and More sheet link lists (System added), the shell digest (only the three Console-space pages moved; personal pages byte-identical, checked by hashing each case before and after), the More sheet link counts, the dirty-bar docking at 1280px (under the frame column, 560px minimum instead of 600px of the old centred bar), the save-bar sameness test (the Fleet bar differs in width and position on a wide screen only, other pages are compared with each other), the System cards column edge (inside the frame column's padding), and page tests of the list rows.

Results (`SKYPANE_REQUIRE_BROWSER=1`, `server/.venv/bin/python`):

- Browser files touching the Fleet page or the navigation (100 files, two chunks): 1373 + 1862 passed, 4 + 46 failed; every failure was a test to update (listed above) except `test_browser_motion_unlock` (an unrelated personal page, timing under load), which passes alone. All re-run green.
- Non-browser (companion, server, stub-server, test-support, scripts, deploy, hardware): 12111 passed, 8 skipped, 6 failed (all updated tests above, re-run green).
- After the baseline write: render baseline, phase 47 freeze, suite guards, access matrix, user-view and co-manager access, page and stylesheet structure, motion budget: 2299 + 390 passed.
- Gates: ruff, mypy (46 files), function size (1140 functions, none over 80), comment history, `companion/app.py` 1491 lines, largest JS 1227 lines.

## Deviations from Plan

- **[Decision 3, no schema change]** The owner asked for stored data. Both moments are already stored: `pending_devices.retired_at` (written by `park_retired`) and `code_expires_at`; the code was issued at the expiry minus the fixed code lifetime (`pairing_code.CODE_TTL_S`). A new column would have raised `PRAGMA user_version` to 5, which an older release refuses to open (`schema newer than supported`), and would have touched the frozen field-validation path. Rows without a date (a NULL `retired_at`, a pending row with no code) fall back to the previous wording. If the code lifetime ever changes, the age of a code issued earlier is off by the difference; say so if a stored issue time is still wanted.
- **[Decision 4, the number]** The brief says "about 600 px at 1440 (mock)". The mock's real numbers are a 240px sidebar, a 350px list panel and the frame area starting at 590px (sidebar plus list), with a 760px content maximum and 44px padding. The 600 is the offset of the frame area, not the list width, so the list is 350px (sidebar plus list is 622px at 1440 because the real sidebar floats 16px from the edge).
- **[Rule 3]** `prefs.set_request_path` takes the query string as a second argument (the navigation has to know `view=system`; `app.py` changes one line, not its length).

## Design-system divergences

Still differing from `68-MOCKUP-frame-list.html`:

- The sidebar and the list are two separate rounded glass panels 16px apart (the real shell floats its sidebar; the mock draws a flush sidebar with a border). The list copies the sidebar's top, height, radius, fill and shadow, but it is not drawn flush against it.
- The list is 350px as in the mock, but the frame area starts at 622px (not 590px) at 1440 for the same reason, and the frame content is 722px wide at 1440 (the mock reaches its 760px maximum); at 1200px it is about 498px.
- The mock's whole page is one absolutely positioned scene with the frame column scrolling by itself; here the frame column scrolls with the page and the list is sticky, so the page scrollbar belongs to the whole window.
- The selected row is highlighted but is not scrolled into view when it is below the fold of a long list (30 frames); the mock has the first frame selected at the top. Not requested; left for a decision.
- The pending age uses the app's shared age ladder, so it reads "Code shown 5m ago" (EN) rather than "Code shown 5 min ago"; French reads "il y a 5 min" as in the mock.
- The retired row reads "owner · Retired 12 Oct" with the Paris-clock day; a retired frame's header still says "Retired · Formerly owner" (the header was not part of the decision).
- Row detail is status first ("Online · owner"), as decided, where the mock reads owner first; status words are the app's own (Online, Resting, No contact, Not seen yet, Overdue, Low battery) rather than the mock's Online / Sleeping / Offline.
- The "All frames" chip has no grid icon and the personal view button uses the existing device icon (no sprite additions); header icon buttons are 44px squares with the 14px control radius, not round.
- The System entry uses the existing pulse glyph; on a phone it is a row of the More sheet (not a tab, the bar already holds four tabs and More).
- The mock's State / Settings / Access sections and tiles are plan 35 (not done here).
- The wide landing still renders the list heading twice (phone and wide variants, one hidden by CSS) so the shared heading-size rule holds; one `h1` is visible at every width.

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/fix2/`: list, frame, retired and System at 1440, 1200 and 390px in light and dark, the dirty bar at 1280px and the phone More sheet.

## Self-Check: PASSED
