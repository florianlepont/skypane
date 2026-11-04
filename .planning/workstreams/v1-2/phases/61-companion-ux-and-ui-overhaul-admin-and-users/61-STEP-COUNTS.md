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
| A6 | Read the audit log | 2 | 1 | 1 | -1 | yes (Audit is a Console bar cell since plan 61-42) |
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
| L1 | Pick an airport from the list (Location tab, type in the filter, tap the airport, Save) | not measured, new flow | 4 | 4 (was 5 before plan 61-41) | n/a | yes (rebuilt Location page) |
| L2 | Use my position (Location tab, permission, Use my position, Save) | not measured, new flow | 4 | 4 (was 5 before plan 61-41) | n/a | yes (rebuilt Location page) |
| L3 | Search a place (Location tab, type, Search places, tap the result, Save) | not measured, new flow | 6 | 5 (was 6 before plan 61-41) | n/a | yes |
| L4 | Tap the map (Location tab, tap the map, Save) | not measured, new flow | 3 | 3 (was 4 before plan 61-41) | n/a | yes (rebuilt Location page) |
| S1 | Console to My frame (and back) | not measured, new flow | 1 | 1 (both directions) | n/a | yes |
| S2 | Switch frame (one tile tap, D30) | 1 (drop-down, then a row) | 2 | 1 | n/a | yes |
| A7 | A frame's health from Fleet (its tile; the State block) | not measured, new flow | 1 | 1 | n/a | yes: a frame's health is the State block of its Fleet view; one tap on its tile (0 when it is already selected) |
| A8 | Rename an airline in the Airline editor, from the Console (Airline editor bar cell, type the name in its row, Enter; the field saves on change, plan 61-44) | 4 (bar cell, the airline, the name, Save name) | at least 3 on a phone | 3 on a phone | -1 | yes (desktop is one fewer, see notes) |
| V1 | Airline collection, phone (More, Airline collection) | not measured, new flow | 2 | 2 | n/a | yes |
| V1 | Airline collection, desktop (sidebar link) | not measured, new flow | 1 | 1 | n/a | yes |
| U2 several | Reach another frame (one tile tap, D30) | 1 (open the drop-down) | 1 in the first round, 2 after the card sheet | 1 | 0 | the tile strip (D30) removed the card sheet's extra tap |

Measured paths (360 x 844):

- U4a: tap the schedule link on Home (opens the Quiet hours dialog), type the start time, Save.
- U4b: Personalisation tab, tap a look card, Save.
- U4c: Device tab in the Console bar, type the interval in the number field, Save.
- L1: Location tab, type "Lyon" in the airport filter (the first control of the sheet), tap the airport (it opens the same page for that airport), Save.
- L2: Location tab, the permission prompt (one counted step), tap the round Use my position button on the map, Save.
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
