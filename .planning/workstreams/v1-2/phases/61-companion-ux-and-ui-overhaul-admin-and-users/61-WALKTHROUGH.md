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
