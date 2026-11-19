---
phase: 68-console-and-companion-visual-improvements
plan: 26
subsystem: companion
tags: [fleet-list, frame-switch, retired-frames, french-compagnies, render-baseline]
requires: ["68-25", "68-02"]
provides:
  - "List of frames on /fleet (live, pending, retired, System), search from 8 frames (R13)"
  - "Pending and retired frames only in the list; each opens its own page with its one action (R15, D-04)"
  - "Frame header with the frame name, state and icon buttons; phone chip row starting with All frames"
  - "French Compagnies instead of Airlines in the remaining French strings (owner decision, separate commit)"
key-files:
  created:
    - companion/pages/fleet_frames_list.py
  modified:
    - companion/console_fleet_view.py
    - companion/pages/fleet_page.py
    - companion/frame_menu.py
    - companion/app.py
    - companion/console_pairing.py
    - companion/ui_filter.py
    - companion/static/style-admin.css
    - companion/static/style.css
    - companion/i18n_fr/admin_fleet.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/common.py
    - companion/testdata/render_baseline.json
decisions:
  - "No new route: the list is /fleet without a frame; /fleet?frame=<id> opens a live, pending or retired row; the access matrix is unchanged."
  - "Landing: a phone shows the list, a wide screen shows the list column and the first frame of the list (problems first)."
  - "The Fleet page has no frame button in the top bar; the console popover (console_menu_html, stash) is removed. The personal frame menu is untouched."
  - "The list title is the page h1 on a phone; on a wide screen the frame name is the h1 and the list title an h2 (the shared heading-size rule holds)."
metrics:
  completed: 2026-11-19
---

# Phase 68 Plan 26: Frame list, frame switch and retired frames Summary

The Fleet page now opens on the list of frames, a pending or retired frame is reachable only from that list, and the frame selector scales to 30 frames (bounded chip row on a phone, list column on a wide screen), built from the owner-approved `68-MOCKUP-frame-list.html`. Plan 35 does the State, Settings and Access sections (R11, R14); they are left as they are here (including the phone State / Settings / Access segmented control).

## What was built

- `companion/pages/fleet_frames_list.py` (new): list panel (title, Add a frame, search from 8 frames, groups Live / Waiting to be paired / Retired with counts, a System row), rows built with the shared grouped-list row (dot, name, status and owner, last seen, chevron; whole row is a link; selected row marked `aria-current`), the chip switch (`All frames (N)`, the frame in view first, at most 8 live frames, no pending or retired), the frame header (`h1` name, state line, personal view and Rename 44 px icon buttons with names for assistive technology) and the page of a pending or retired frame (Re-activate with the wake and Reset sentence, or Pair frame).
- `console_fleet_view.py`: `selection()` no longer falls back to the first frame; `page_html` builds the four views (list, frame, other, system) in one `fleet-split` container; the Other frames block is gone; an unknown `?frame=` id shows the list with "That frame was not found." (the old "Showing X instead" text no longer applies).
- `frame_menu.py`: console popover and its stash removed (only the personal menu remains). `app.py` (+2 lines, 1491 total): `_console_page(omit_title)` so the list owns its own heading.
- CSS: one dedicated block at the end of `style-admin.css` (list, rows, chips, header, buttons, split layout); `style.css` only renames one selector in the reveal list (`.fleet-detail-head` to `.fleet-head`). Tokens only, no durations.
- French: Cadres / Tous les cadres (N) / En service / Retirés / Rechercher parmi N cadres / Aucun cadre trouvé and the approved Réactiver sentence; orphan ids removed (Autres cadres, Actions pour %s, add-a-frame first line).
- Part B (commit b3f6868b): `airlines.back_to_airlines` "← Retour aux compagnies", `airlines.collection_count` and its template "Compagnies : %d", the two "page Compagnies" sentences; `airlines.table_caption` was already "Compagnies" (its stale same-as-English exemption removed); a catalogue test refuses the English word in any French value.

## Phase 64-owned files touched

`companion/static/style-admin.css` (appended block, two obsolete fleet rules removed: Other frames group and detail head), `fleet_page.py` (others block, row menu and detail header removed, public aliases added). `ui_modal.py` untouched. Open pull requests were not re-checked online (the branch was cut from main after #483 merged).

## Tests (behaviour-over-source, browser)

Replaced assertions: popover/dropdown selection, "5 blocks with Other frames", the Other frames row menu and its reachability, the old "Open personal view / Rename" row-action header, the frame-button-based step counts (A3, A4, A5, A7, U4c, the first-frame-on-landing assumption), and the Fleet h1 "Fleet / Flotte" (now Frames / Cadres, with Fleet / Flotte still the nav item and tab title). New: 30-frame list and switch at 360 and 1280 px in EN and FR, one-line centred 44 px chips, search filtering with the empty note, list/frame/other views on phone and desktop, retired and pending pages, dot and last-seen in the same place on every row, contrast of the list text and the retired action. `U4c` measured 4 taps (one more: open a frame from the list); `A7` is now 1 tap (was 2).

## Verification

SKYPANE_REQUIRE_BROWSER=1, server/.venv python: browser set (fleet view, page, sections, tabs, dialogs, frame menu, device selector, row-menu reach, personal scope, contrast edges, console groups, console, French fit, small fit, one toast, access sheet, audit3, overhaul steps and sweep, round 8, web app bar, airline collection) 1130 passed. Non-browser (companion, server, stub-server, test-support, scripts, deploy, hardware, adsb-test, render baseline excluded) 12111 passed, 8 skipped, 2 stale assertions fixed and re-run green. After the baseline write: render baseline, phase 47 freeze, golden hashes, access matrix, co-manager access, structure and suite guards, stylesheet structure 2439 passed. Gates: ruff, mypy (46 files), function size (1140 functions, none over 80), comment history, app.py 1491 lines, largest JS 1227. The matrix file is unchanged.

## Deviations from Plan

- Plan says the baseline is regenerated by plan 35; per the owner's instruction it is regenerated here as the last task (only the `/fleet` captures and stylesheet hashes changed: 68 entries touched).
- [Rule 3] `app.py`, `console_pairing.py`, `ui_filter.py` (public `search_field_html`, exempted on the Components page), `components_page.py` and `test-support/fleet_console_support.py` (`add_frames`) touched; not in the plan file list.
- [Rule 1] A legacy single frame without a database row still renders its page on the landing (header omitted).
- STATE.md not updated by command (owner rule: no state.* commands).

## Design-system divergences

- Desktop: the list is a sticky column inside the page content (not a full-height glass column attached to the sidebar); at 1280 px the frame column is about 500 px wide (the mock has about 600 at 1440 for 760 max), so the old 640 px section-width test floor became 480.
- Row detail reads status first, then owner ("Online · owner") where the mock reads owner then status, so a long address is what gets truncated (ellipsis), never the status word. Status words are the app's own vocabulary (Online, Resting, No contact, Not seen yet, Overdue, Low battery) rather than the mock's Online / Sleeping / Offline.
- A "System" row closes the list (mock has none) so the System view stays reachable now the dropdown is gone; the Fleet page has no frame button.
- The retired row says "Formerly owner" (no retirement date is stored; the mock shows "Retired 12 Oct"); a pending row says "Waiting for pairing" (no code age is exposed).
- The "All frames" chip has no grid icon and the personal view button uses the existing device icon (no sprite additions); the frame state line adds "Seen ..." only when the frame is not simply online.
- Header icon buttons are 44 px squares with the 14 px control radius as drawn (not round).
- The mock's State / Settings / Access sections and tiles are plan 35 (not done here).
- Wide landing renders the list h1 twice (phone and wide variants, one hidden by CSS) so the shared heading-size rule holds; only one is visible at a time.

## Open decisions for the owner

1. Status-first versus owner-first in the row detail (above).
2. Whether the System view should stay a row at the foot of the list or move (e.g. into the console navigation).
3. Retirement date and code age would need new stored data to match the mock's "Retired 12 Oct" and "Code shown 5 min ago".
4. French left in English on purpose: none found in `i18n_fr` after Part B (searched for the word Airlines in every French value; the English constants, class names and the "Airlines" title in English UI are unchanged).

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p26/`: `mock_{list,frame}_ph_*` and `mock_{live,retired}_dk_*`, `before_*` and `after_*` of list, frame, frameswitch (phone chips scrolled), retired, pending, system, personal (+ personalswitch) at phone 390 (`ph`) and desktop 1280 (`dk`), EN and FR, light and dark, with 34 frames (28 live, 2 pending, 4 retired). Compared side by side; fixed: chip row overflow (an absolutely positioned hidden label escaped the scroller), empty page header gap above the chips, row names bold and single line, heading sizes, System title spacing.

## Self-Check: PASSED
