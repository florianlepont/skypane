# Phase 61 — visual audit notes (pre-walkthrough)

Source: 68 full-page captures of the current companion on fake data
(admin / user / login, 360 px and 1280 px, EN and FR). Script: scratchpad
`shoot.py` (provisioned_fleet fixture, loopback server, no network).

## Observed before any walkthrough (to confirm with the owner)

- **User view is one page.** A plain user gets 404 on `/`, `/display`,
  `/device`; the only page is `/account`, yet the phone tab bar shows
  Home / Flights / Display / Health / Account to them (tabs that lead to 404).
- **Fleet desktop table is clipped**: the Hardware column is cut and the
  actions column is off-screen (horizontal scroll inside the card).
- **Fleet phone cards**: Open / Reassign / Retire stacked per frame, long;
  the console section tabs (Fleet/Users/Locations/Audit/Releases) wrap onto
  two lines at 360 px.
- **Phone nav**: the admin console hides behind one "Admin" tab plus a
  "More" tab; admin concepts (Admin) sit beside everyday tabs.
- **Users phone**: email breaks mid-word, badge "INVITED" on already
  signed-in users, role select + "Save role" take a full row per user.
- **Pair a frame / Register a frame**: two forms always open, the rarely
  used raw MAC/secret form has the same weight as the pairing one.
- Fixed tab bar overlaps content in full-page captures (artefact of the
  capture, to be re-checked in a real viewport).
