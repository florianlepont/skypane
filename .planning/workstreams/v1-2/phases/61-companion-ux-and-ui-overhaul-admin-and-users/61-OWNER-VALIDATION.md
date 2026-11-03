# Phase 61 — owner validation on the deployed companion (plan 61-13)

Deployed: PR #287 merged 2026-11-03, CI green, production deploy green.
Verdict so far: first pass by the owner, as administrator, FR (screenshot of
the frame switcher). Not approved yet: issues below.

## Issues raised (priority proposed by the assistant, to confirm)

Most shocking for the owner (V0, structural, P0):
- V0 The administrator's view of a frame differs from the view a user has of
  the same frame. It must be the same. Only the Console / personal-space
  switch should tell an admin from a user. (V3 and V5 are consequences.)

Small, fixable in this phase:
- V1 "Mes vues" is unclear as a label for the personal space.
- V2 The Console / My views switch is not visible enough.
- V3 "All frames (Fleet)" must not appear in the frame switcher: an admin's
  personal view must not differ from any user's; only the Console/personal
  switch differs.
- V4 "Flights" should be named "Flight history" ("Historique des vols").
- V5 Health and Device should be tabs reachable only from the admin Console.

Larger redesigns (new design work, owner decision on scope):
- V6 The frame switcher is a drop-down; the owner expected something nicer.
- V7 "Location and detection" should have its own tab with a much more
  modern, polished UI (a map was suggested). The owner does not see why
  saved locations exist: they would just state the place each time.
- V8 Quiet hours and their settings should leave the Display page and
  appear as a modal opened by clicking the schedule on Home.
- V9 Display becomes a "Personalisation" tab with much more room to manage
  the displays clearly.
- V10 "Airlines" becomes a more gamified page of airlines observed; users
  must not be able to edit pictures or airline information: those options
  only for the administrator through a dedicated view.

## Decisions after the first pass (2026-11-03)
- D16 (owner) V0 confirmed: the personal space has the same pages for an
  administrator and a user on a frame (Home, Flights, Display, Account);
  Health, Device, airline editing, Fleet, Users, Locations, Audit and
  Releases live in the Console.
- D17 (owner) All of V1-V10 is done in this phase (not a separate phase).
  This needs an updated design contract and new plans before execution.
- D18 (owner) The "Location and detection" tab uses a real OpenStreetMap map
  (option A). This lifts the no-external-content rule for map tiles: the
  CSP img-src needs the tile host, and a map script must be vendored
  (first-party static file, no CDN). Attribution required. To specify in
  the updated UI-SPEC.
