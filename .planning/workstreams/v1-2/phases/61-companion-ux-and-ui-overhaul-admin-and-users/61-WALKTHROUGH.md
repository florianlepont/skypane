# Phase 61 — task walkthrough (UX-01), owner's frictions

Ranking: P0 blocks the task, P1 slows or confuses it, P2 polish.
Steps = current number of taps/screens from sign-in on a phone.

## Admin 1. Read the fleet state (current steps: 2 — Admin tab, then Fleet)
- F1 (P1) FR page/nav label "Cadres" for the fleet is confusing: "cadre"
  is also the owner's word for the screen/display. Needs another name.
- F2 (P0, structure) The admin console is one tab of the everyday app.
  Owner expects an admin to land on a 100% admin space, with a way to reach
  their own frame views (their personal display) from it.
- F3 (P0) The fleet table is unreadable (clipped columns on desktop, long
  stacked cards on phone, big monospace names).
- Decision D1 (owner): option A. An admin signs in on a 100% admin space
  (fleet, users, ...) with a link to their own personal views (Home,
  Display, Flights). No "Admin" tab inside the everyday app.
- Decision D2 (owner): the fleet list shows name, owner and ONE status dot.
  No separate state column, no firmware, no battery, no location. (Last
  image not mentioned: to confirm.)

## Admin 2. Invite a user (current steps: ~5 — Admin tab, Users tab, scroll
## past the user list, type email, choose role, Send)
- F4 (P1) Emails (and frame names) are set in large monospace: they take
  too much room and are out of scale with the rest of the page.
- F5 (P1) The invite form is a separate section at the bottom of the page.
  Owner wants it as a "+" action opening a modal, or a new row in the table.
- Decision D3 (owner): creation forms (invite now; pairing, locations to
  confirm) open from a "+" button in a modal, not as a section at the page
  bottom.

## Admin 3. Pair a frame (current steps: ~6 — Admin, Fleet, scroll past the
## frame list, type pairing code, choose owner, Pair)
- F6 (P1) The "Register a frame" (MAC + secret hash) form is never used by
  the owner (pairing by code only) but is always open on the page.
- F7 (P1) Pairing should be an "Add a screen" button (modal, per D3),
  not a section under the list. Owner's own word here: "écran".
- Open question for the naming decision: the owner says "écran" for the
  physical device in this sentence; the UI says "cadre/frame".

## Admin 4. Retire / reassign (current steps: ~4 — Admin, Fleet, find the
## frame card, open Reassign or Retire disclosure, pick owner/confirm)
- Decision D4 (owner): the physical device is called "cadre" (frame), not
  "écran". The button reads "Ajouter un cadre". The fleet page's own name
  (F1) must differ from it: to settle.
- F8 (P1) Retire / Reassign / Re-activate open as inline disclosure
  toggles under each frame; owner wants a modal (consistent with D3).

## Admin 5. Add a co-manager (current steps: ~5 — Home as the admin, pick
## the frame in the Frame picker, scroll to the Co-managers card, choose a
## person, Add)
- F9 (P0, structure) The Co-managers card sits on Home (the personal view)
  and the owner does not understand why it is there. Co-management is an
  admin/owner action on a frame, not a Home widget.
- Decision D5 (owner): co-management moves out of Home to a per-frame
  "Manage access" action opening a modal. For a user: the owner of a frame
  can already add/remove co-managers (server rule), a co-manager can leave;
  so the same modal is offered on the user's own frame page, only for
  frames they own.

## Admin 6. Read the audit log (current steps: 2 — Admin, Audit log tab;
## filter chips on a second wrapped row)
- F10 (P1) Same objection for a user: a Co-managers card on the frame's
  Home page is the wrong place (D5 wording revised: not on the frame page
  body). Placement for users to settle.
- Decision D6 (owner): for a user, "Manage access" is an action on the
  "My frames" list (owned frames only), opening the modal. Not on the
  frame page.
- No friction reported on the audit log itself (only the global wrapped
  console tabs, already covered by D1).

## User 1. Sign in (current steps: ~4 — open the link, Sign in, Auth0 form,
## land on Account; an unverified Auth0 email ends on "No invitation found")
- No friction reported by the owner on his test accounts. The unverified
  email message (UX-04, SEED-011) stays in scope from the requirement, not
  from observed friction.

## User 2. See my frames (current steps: 1 — land on Account, "Your frames"
## list: serif name + hardware model, last contact, "Open")
- F11 (P0, structure) Landing on the Account page after sign-in is odd.
  The owner wants the frame switch either at the start on Home, or in the
  navigation.
- Decision D7 (owner): a user lands on the Home of their frame. With
  several frames a frame switcher stays at the top of every page; with one
  there is nothing to choose. "My frames" (with Manage access, D6) lives in
  that switcher or under Account.

## User 3. Understand a frame's state (current steps: ~3 — Account, Open a
## frame, Home status card; the state needs reading, no at-a-glance signal)
- Decision D8 (owner): a user reads a frame's state from ONE status dot
  (same vocabulary as the fleet list, D2); no battery or detail cards for
  users.

## User 4. Change a setting (current steps: ~4 — Account, Open a frame,
## Display tab, change the setting, Save bar; Display page is ~3500 px tall
## on a phone)
- Decision D9 (owner): all display settings stay useful for a user; the
  "location" and "detection" cards are merged into one.

## Walkthrough complete: 6 admin tasks, 4 user tasks.
