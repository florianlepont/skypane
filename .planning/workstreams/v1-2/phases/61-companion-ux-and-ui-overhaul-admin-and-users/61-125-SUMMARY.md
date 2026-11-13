# Phase 61 Plan 125: Unsaved-changes dialog for every save bar Summary

**Leaving any page that has a save bar through an in-app link, with anything unsaved, now opens the app's own Save and continue / Discard / Stay here question — the bottom tab bar included, which is how the owner lost a colour change.**

## Root cause of the owner's report

Not a device defect. The owner's case was reproduced headless on an
iPhone-shaped context (390x844, has_touch, iPhone user agent, touch taps) on
every Style view: the dialog from the previous plan opened for a layout change
on the Style sub-tabs, by tap and by click, on all four views. It never opened
for the owner because of scope:

1. the guard asked only `current.layout !== snapshot.layout`, so a colour,
   pairing or special-look change was invisible to it;
2. it only intercepted `[data-pers-view]` links — **the owner changed pages
   with the bottom tab bar**, which was not guarded at all.

No caching, view-transition, capture-phase or iOS event-path problem was
found: static URLs are versioned, HTML is `no-store`, and motion.js's tab-bar
handler never calls preventDefault (it already returns the pill when another
handler cancels the navigation).

## What changed

Two commits.

**`b1c14c1e` — Style:** the predicate became `countDifferences() > 0` (the
Save bar's own count, carried values included) and the guard matched any
in-app link. Neutral wording and the rename from `layout_leave_*` to style
names.

**`0e0032cf` — every save bar:** the question belongs to the bar, not to one
page.

- `ui_save_bar.leave_dialog_html()` holds the dialog and its strings
  (`display.leave_*`, French in `companion/i18n_fr/display.py`).
  `ui_shell.page_shell()` renders it once on any page whose body contains a
  save bar, so no page can forget it and none carries two; the Components
  catalogue renders its own copy as the sample and the shell steps aside.
- `dirty-state.js`: one `installLeaveGuard(isDirty, form, saveButton, bar,
  disarm)` used by both bar kinds — the tracked bar (`countDifferences`) and
  the form-page bar (its own comparison). One guard per page.
- Links guarded: every same-origin `<a href>` — sub-tabs, bottom tab bar, More
  sheet, sidebar, frame menu, back and brand links. Not guarded: the page's
  own save bar and dialogs, `data-modal-open`/`-close`, `data-detection-nav`,
  same-page hash links, `target`/`download`, other origins.
- Posts of **another** form on the page (theme, language, sign out) ask too
  when the count is above zero; Discard re-posts through the submitter the
  person pressed, so a switch keeps its own name and value. The page's own
  form, `data-quick-switch` and `data-detection-nav` are never intercepted.
- `return_to`: the bar carries `data-leave-returns` (the page's own allow-list,
  device-scoped). Save and continue names the tapped address only when it is
  listed; otherwise the save goes where that page's save always goes.
- `config_page.submitted_return_route()` now tests against
  `personalisation_cards.LEAVE_RETURN_ROUTES` (Style views, Device, the
  navigation tabs) — still a byte-for-byte membership test, so a crafted value
  still falls back to `/display`.

## Per page: what Save and continue does

| Page family | Save and continue |
|---|---|
| Style (`/display*`, tracked bar) | saves and lands on the tapped address when it is one of the Style views, Device or a navigation tab; otherwise saves and returns to the Style page |
| Device / Fleet settings (same settings form) | same allow-list; the Console's own destinations (`/users`, `/audit`, the frame tabs) are not in it, so the save lands where a Fleet settings save always lands (the frame's settings tab) |
| Location and detection (`/detection`) | its handler always redirects to its own page with the saved flash: saves and stays |
| Style form pages (new/edit special look, Calendar connect, the calendar look) | their save returns to their own parent view: saves and goes there, not to the tapped address |
| Frame rename (`/frame/name`) | its save honours its own `return_to`: saves and goes there |
| Components catalogue | the sample bar; the dialog is the catalogue entry |

Discard and Stay here behave identically everywhere.

## Decisions

- **Theme / language / sign-out posts** are intercepted only while the count is
  above zero. Save and continue there saves and stays (the switch is dropped);
  Discard applies the switch. Stated here as asked.
- **Destinations the server does not list** still ask; only the landing differs.
- **The "carried" Save-bar case** exists on the Location page, not on Style;
  the predicate is the carried-aware `countDifferences()` itself and the Place
  carried tests pass unchanged.
- **The French text uses "tu"**, as the owner dictated; the rest of the French
  UI uses "vous".

## Tests

- `companion/test_browser_style_leave.py` (renamed from
  `test_browser_layout_leave.py`), 23 → 39 tests: layout, colour-only, clean
  page, bottom tab bar, More sheet link, sidebar, hash link not intercepted,
  Save and continue, Discard, Stay here, Escape, focus return, pill back on
  Style, no-script, 360/1280, EN/FR, both themes, taps and clicks.
- `companion/test_browser_leave_dialog_pages.py` (new, 60 tests): the five
  save-bar page families (Style, new special look, Calendar connect, Location,
  Fleet settings) × 360/1280 × EN/FR × tap/click for the question itself, plus
  clean page, Discard, Save and continue per family, the geometry/both-themes
  check on a form page, and the language-switch post.
- `companion/test_browser_detection.py`: the two tests that pinned the
  browser's prompt now pin the dialog (updated in place, not weakened).

Seen red first both times: the Style file 36/37 red with the code at HEAD, the
new pages file 55/60 red before the generalisation. The Style file was also run
three times in a row green.

## Tests run

ruff, mypy, `check_comment_history check`, `check_function_size check --max 80
server stub-server`, `stub-server/test_phase47_freeze.py`, render snapshot
`--write` (baseline committed with the markup change).
Python (1,252 passed): components_page, i18n, ui_modal, render_baseline,
sign_in_surfaces, config_page_01..05 + 04b, companion_app_01..05,
personalisation_layout/page/special_looks, view_pages_02,
stylesheet_structure, suite_guards, page_scripts, co_managers_page.
Browser (282 + 302 passed after the final code state): style_leave,
leave_dialog_pages, detection, save_bar, place_page, fleet_dirty_bar,
quiet_hours_modal, components_page, cancel_focus, personalisation,
personalisation_fixes, display_looks, ux_01, ux_02, overhaul_steps,
more_sheet, theme_switch, page_restore, round11, audit3. Earlier rounds also
covered ux_03/04, overhaul_sweep, surfaces, frame_menu, brand_logo,
navigation_assist, web_app_bar, page_opening, segment_centring,
personalisation_cards/layout/pairings/selector, tab_pill_transition (1,035 +
391 + 192 passed).
The full suite was not run locally (phase test cadence); CI runs it.

## File sizes

`companion/static/dirty-state.js` 850 of 1500; `companion/ui_save_bar.py` 116;
`companion/app.py` untouched at 1493.

## Deviations

- Two code commits instead of one per step: the owner's scope decision arrived
  mid-run, so the Style fix landed first and the generalisation second. Both
  are green states.
- `ui_modal.choice_dialog_html()` briefly gained an optional data attribute
  pair for the return list in the first commit; the list now lives on the bar,
  so the helper is back to its original signature.

## Self-Check: PASSED
