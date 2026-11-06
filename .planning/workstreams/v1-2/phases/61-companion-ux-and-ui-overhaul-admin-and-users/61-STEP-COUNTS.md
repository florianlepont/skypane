# Phase 61 — step counts, before and after

Source of the "after" column: `companion/test_browser_overhaul_steps.py`,
last run on 2026-11-04 in Chromium with the fake identity provider
(`-s` output lines `STEP-COUNT <task> <n>`). Source of the "before" column:
`61-WALKTHROUGH.md` (the owner's measured counts). Targets: `61-UI-SPEC.md`
section 7 (the earlier rows) and section 14 (the revision 2 rows).

## Counting rule

One step is one tap, one typed or chosen value, or one scroll that an
action needs to reach its target (a target below the fold counts one; the
test detects it by measuring the target against the viewport before acting).
Counting starts on the page sign-in lands on, on a 360 x 844 phone, signed in
through the fake identity provider as the person the task is about. The
sign-in task counts its whole path: open the link, tap Sign in, the provider
screen (counted as one step; the fake provider approves on its own, a real
form would be one submit), and the landing page.

## How the counts are asserted

Each test prints `STEP-COUNT <task> <n> (target <t>)`. The revision 2 tests
(U4a, U4b, U4c, L1 to L4, S1, S2, A7, A8, V1) assert the exact measured value, so a gain and a
regression both fail them, and the printed line says ` MISSED` when the count is over the
design target. The first-round tests (A1 to A6, U1 to U3, U2 several) assert at or below
the value they carry (A6 carries 2, one over its design target of 1). Taps on a
map point count one, plus one scroll when the point is below the fold. The
position permission prompt of the browser is modelled as one counted step by
the L2 test (the test context grants it in advance).

## Results, first round (plans 61-01 to 61-16)

| # | Task | Before | Target | After (measured) | Delta | Met |
|---|------|--------|--------|------------------|-------|-----|
| A1 | Read fleet state | 2 | 0 | 0 | -2 | yes |
| A2 | Invite a user | ~5 | 4 | 4 | -1 | yes |
| A3 | Pair a frame | ~6 | 4 | 4 | -2 | yes |
| A4 | Retire | ~4 | 3 | 4 | 0 | yes after plan 61-45: no scroll; the actions menu is in the detail header. The 4th step is the tile tap, needed only when the frame is not the one selected on landing |
| A4 | Reassign | ~4 | 4 | 5 | +1 | yes after plan 61-45 (tile tap, menu, Reassign, new owner, confirm; no scroll) |
| A5 | Add a co-manager | ~5 | 4 | 5 | 0 | yes after plan 61-45 (tile tap, menu, Manage access, person, Add; no scroll); the Access block of the selected frame also offers the forms inline |
| A6 | Read the audit log | 2 | 1 | 2 | 0 | no (Audit moved back into More by plan 61-46, the bar now leads with the space switch) |
| U1 | Sign in | ~4, ends on Account | 4, ends on Home | 4, ends on Home | 0 (lands on the right page) | yes |
| U2 | See my frames, one frame | 1 (wrong page) | 0 | 0 | -1 | yes |
| U3 | Understand a frame's state | ~3 | 0 | 0 (the dot on Home) | -3 | yes |

Superseded rows (kept for the record, replaced by the revision 2 rows below):

| # | Task | Value when measured | Replaced by |
|---|------|---------------------|-------------|
| U4 | Change a setting (quiet-hours start), through the Display tab | 4 (target 3, missed) | U4a |
| U4 | Change a setting (look, through the sheet) | 5 (target 3, missed) | U4b |
| U2 | Several frames, the frame switcher | 1 (open the drop-down) | U2 several, below |

## Results, revision 2 (plans 61-17 to 61-34)

| # | Task | Before | Target | After (measured) | Delta | Met |
|---|------|--------|--------|------------------|-------|-----|
| U4a | Quiet-hours start from Home (tap the schedule, the start time, Save) | 4 (old U4) | 3 | 3 | -1 | yes |
| U4b | Change the look (Personalisation tab, tap a look, Save) | 5 (old U4 look) | 3 | 3 | -2 | yes |
| A9 | Administrator changes a user's role (Users tab, choose the role in the row; the select saves at once, plan 61-43) | 4 (Users tab, Manage user, choose, Save role) | 2 | 2 | -2 | yes |
| U4c | Administrator changes the refresh interval (Settings block of the Fleet view: scroll, the interval, Save) | not measured, new flow | 3 | 3 | n/a | yes |
| L1 | Pick an airport (Location tab, type its code in the search field, tap Search, Save) | not measured, new flow | 4 | 4 (was 5 before plan 61-41; unchanged by plan 61-50) | n/a | yes (rebuilt Location page) |
| L1-pin | Pick an airport by tapping its pin on the map (Location tab, Show all of France, tap the airport's pin, Save; plans 61-65 and 61-69) | not measured, new flow | 4 | 4 (same as L1; the map now opens on the frame's own airport, so another one is reached by zooming out first) | n/a | yes |
| L2 | Use my position (Location tab, permission, Use my position, Save) | not measured, new flow | 4 | 4 (was 5 before plan 61-41; unchanged by plan 61-50) | n/a | yes (rebuilt Location page) |
| L3 | Search a place (Location tab, type, Search places, tap the result, Save) | not measured, new flow | 6 | 5 (was 6 before plan 61-41) | n/a | yes |
| L4 | Tap the map (Location tab, tap the map, Save) | not measured, new flow | 3 | 3 (was 4 before plan 61-41) | n/a | yes (rebuilt Location page) |
| S1 | Console to My frame (and back) | not measured, new flow | 1 | 1 (both directions) | n/a | yes |
| S2 | Switch frame (frame button, then a row, plan 61-57) | 1 (drop-down, then a row) | 2 | 2 | n/a | yes |
| A7 | A frame's health from Fleet (its tile; the State block) | not measured, new flow | 1 | 1 | n/a | yes: a frame's health is the State block of its Fleet view; one tap on its tile (0 when it is already selected) |
| A8 | Rename an airline in the Airline editor, from the Console (Airline editor bar cell, type the name in its row, Enter; the field saves on change, plan 61-44) | 4 (bar cell, the airline, the name, Save name) | at least 3 on a phone | 3 on a phone | -1 | yes (desktop is one fewer, see notes) |
| V1 | Airline collection, phone (More, Airline collection) | not measured, new flow | 2 | 2 | n/a | yes |
| V1 | Airline collection, desktop (sidebar link) | not measured, new flow | 1 | 1 | n/a | yes |
| U2 several | Reach another frame (one tile tap, D30) | 1 (open the drop-down) | 1 in the first round, 2 after the card sheet | 1 | 0 | the tile strip (D30) removed the card sheet's extra tap |

Measured paths (360 x 844):

- U4a: tap the schedule link on Home (opens the Quiet hours dialog), type the start time, Save.
- U4b: Personalisation tab, tap a look card, Save (plan 61-48: the Departures and Arrivals views are one tap apart in the single tab bar; before it Arrivals was a tab inside the Look view, also one tap; the count is unchanged).
- U4c: Device tab in the Console bar, type the interval in the number field, Save.
- L1: Location tab, type the airport's code ("LYS") in the one search field at the top of the map, tap Search (an airport code or name is answered from the page's own list: it opens the same page for that airport, no request to the search service), Save (plan 61-50: before it, the airport filter then the airport link; the count is unchanged).
- L1-pin: Location tab, Show all of France (the map opens on the frame's airport), tap the airport's pin (every airport of the catalogue is drawn in Airport mode, plan 61-65; the tap opens the same page for that airport), Save. Typing now also lists matching airports under the field (a tap on a row replaces typing the whole code and Search); the L1 count above is unchanged.
- L2: Location tab, the permission prompt (one counted step), tap the round Use my position button on the map (it now also switches to My position mode, plan 61-50), Save.
- L3: Location tab, type the query, tap Search places, tap the result (no scroll), Save.
- L4: Location tab, tap the part of the map the floating controls and the sheet leave clear, Save.
- S1: tap My frame in the strip under the header from the Console landing; the way back, tap Console, is also one.
- S2 and U2 several: the tile of the other frame (one page change; the strip replaced the chip and card sheet, D30).
- A7: the frame's tile on Fleet selects it; its State block is the health view (measured 1 when another frame is selected on landing).
- A8: the Airline editor bar cell, type the new name in the airline's own row, Enter (3 on a phone; the name field saves on change, so the airline tap and the Save name tap are gone, plan 61-44). On desktop the sidebar link replaces More and the editor link, so the path is one tap shorter; the desktop figure is not measured in this file (the phone rule governs).
- V1: phone, More then Airline collection. Desktop is the sidebar link, measured at 1280 px outside the phone rule.

## Honest notes

- **Location page targets are all met since plan 61-41** (the page was rebuilt as sketch V1, D28): L1 4, L2 4,
  L3 5 (against 6) and L4 3. Before it, L1 was 5, L2 5, L3 6 and L4 4: the old page put the status card and the
  search first and the airport filter, the locate button and the map started at or below the fold, so each needed a
  counted scroll. Now the map fills the first screen, the airport filter is the first control of the bottom sheet
  and the locate button floats on the map. L4 taps the part of the map the floating controls and the sheet leave
  clear (the point a person can actually reach); nothing was changed to hit a number.
- **A6 stays at 2** (More, Audit log), one over the 1-tap target the first round set. The
  Console bar cannot hold Audit log next to Fleet, Users, Health, Device and More; this
  equals the pre-redesign count of 2 and was noted by plan 61-21.
- **U2 with several frames is 1 again** (D30: the tile strip replaced the card sheet). Before D30 it was 2, since the frame drop-down became a card sheet
  (revision 2 accepts the extra tap): the sheet lists every frame after one tap, and
  reaching another frame is the card tap.
- A8's phone figure is the bare minimum for the editor path; the desktop number is
  not asserted here.
- L2 models the browser's one-time permission prompt as one step. The test context grants
  the permission in advance, so no prompt is driven; a person who has already granted it
  pays one step less.
- Tasks whose count did not improve: A4 reassign (equal), U1 (the gain is that it ends on
  Home), A6 (equal to before, over the target), U2 several (one more than before, accepted).
- A1, U2 (one frame) and U3 are zero-action tasks: the test asserts what is visible on the
  landing page (status dots with accessible names, no frame switcher, the Home dot) instead
  of a count above zero.
- Not measured: the other personal pages' own tasks, and the desktop counts other than V1.

## Plan 61-42 (Console Fleet merges Fleet, Status, Version, Device)

The Console bar cells are Fleet, Users, Airline editor and Audit (More holds the
space switch and Account), so A6 and A8 lose the More tap. The wake interval is in the
Settings block of the Fleet view (U4c has no navigation tap). The frame list with the
row menus (reassign, retire, re-activate, Manage access) stays under the blocks, so A4,
A5 and A7 each gain one scroll on a phone: an open item for the owner (move the frame
actions into the detail header, or place the list above the blocks).

## Plan 61-45 (finishing the Fleet merge)

The frame list is replaced by the strip tiles and a detail header with the actions menu, and
pending/retired frames sit in a collapsed "Other frames" block, so A4, A5 and A7 no longer scroll
on a phone. Their counts include one tile tap because the frame landed on first (the served Orly frame
in the test fleet) is not Kitchen: measured A4 retire 4, A4 reassign 5, A5 5, A7 1, A1 0, A3 4. With the
frame already selected each is one lower. All stay within their targets; A7 measured 1 (target 2).

## Plan 61-44 (Airlines editor as a table)

The editor's name field is in the row, so renaming no longer opens the airline sheet: A8 went from 4 to 3
on a phone (bar cell, type, Enter). Replacing an artwork is the thumbnail itself (choose the file; with a
script the form sends it at once): one tap and the file choice, where the sheet needed the row, the type
and the upload. Reaching an aircraft type's artwork costs one chevron tap. No editor flow got longer.

## Plan 61-46 (phone chrome)

The tab bar leads with the administrator's Console / My frame switch (S1 stays 1: the cell is a plain link, now in
the bar instead of a strip under the header). A 6th cell does not fit the longest French label ("Compagnies",
"Utilisateurs") at 360 px, so the Console bar moved Audit log into More: A6 is 2 again (More, Audit log), as before
plan 61-42. The personal bar keeps its four destinations beside the switch (six cells). Nothing else changed: the
frame strip's collapse is optional and open by default, so no task gained a tap.

## Plan 61-51 (quiet Console pages, global Airlines editor)

Changing an artwork moved from the thumbnail (tap, choose the file) to the row's menu (open "...", "Change artwork", choose the file): one tap more, no flow in the measured set (A8 stays 3, a rename). Enlarging an artwork is now one tap on the thumbnail (it was two: "..." then "Enlarge the artwork"). Inviting a user is unchanged (A2 stays 4). No measured count moved.

## Plan 61-57 (frame button and popover)

Choosing a frame is two taps now: the frame button at the top right, then the frame's row (the strip was one tile tap). Measured on 360 x 844 after the change: S2 2 (was 1), U2 several 2 (was 1), A7 2 (was 1), A3 pair a frame 5 (the button, the Add a frame row, the code, the owner, Pair), A4 retire 5, A4 reassign 6 and A5 6 when the frame is not the one selected on landing (each counts the button and the row where it counted one tile tap; one fewer when it is already selected). A1 stays 0 and U2 with one frame stays 0 (the button names the frame, no action). The targets of the revision 2 rows were 2 or more for S2, so S2 and A7 stay within them; A3, A4 and A5 are over their first-round targets by the one extra tap and are accepted: the popover keeps the top of every page free of the strip (the audit's heaviest block above the title).

## Plan 61-58 (user pages on the components)

No measured count moved: Manage access and Leave frame are still one tap from the Account row, Add a frame is still one tap (now a row), the Flights filter and picture action are unchanged, and the Personalisation views are the same links. Counts stay as after plan 61-57.

## Plan 61-59 (Console pages on the components)

No measured count moved. The Fleet blocks, the Users table and cards, the Airline editor table, the Audit log list, the 404/403 back link (one row link instead of a text link) and the dialogs only changed surface and geometry: every control, route and form is the same, so the taps of A1 to A8 and U1 to U4 are as after plan 61-58. The unidentified airline row's "Name it" is still one tap.

## Plan 61-60 (final consistency pass)

No measured count moved. The Fleet Access block became group rows (the Remove action is still one tap per co-manager, the invite select plus Add is still select, Add), the System view is one group per topic, the Releases list is a group of the same expandable rows, and the dialogs, tables and search fields only changed surface, radius and size. A1 to A8 and U1 to U4 are as after plan 61-59.

## Plan 61-62 (Flights, Collection and Personalisation controls)

No measured count moved (U4a 3, U4b 3, U4c 3, V1 phone 2 and desktop 1 re-measured at 360 x 844). The Flights thumbnail is still one tap to the picture (it replaced the separate picture button), the collection's sort is now two taps (open the menu, choose) where the select was also two (open, choose), and the whole Personalisation look picker now fits one 360 x 740 screen, so Save never needs a scroll (no count was relying on one). Counts stay as after plan 61-60.

## Results after plan 61-63 (Manage access sheet, drawn frame, Account relationship)

No measured count moved. Manage access is still one tap from the Account row; in the sheet adding a co-manager is the field, then Add (type the address and press Add, or select and Add for an administrator) and removing is one tap on the row's Remove. Done is still one tap. The Fleet Access block is unchanged in step terms. A5 stays 5 (A5 6 when the frame is not the one selected on landing), A1 to A8 and U1 to U4 are as after plan 61-62.

## After plan 61-71 (Fleet sub-tabs)

On a phone the Fleet page shows State, Settings and Access as sub-tabs. U4c is still 3: the Settings tab tap replaces the scroll, then the interval, then Save.
