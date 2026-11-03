# Phase 61: Owner decisions ledger

Source: the "Open for owner validation" list at the end of `61-UI-SPEC.md`.

## Rule

A dependent plan checks its row here before it starts. An owner answer
replaces the spec default and is applied by that plan; whoever records the
answer also updates the row (status "owner answered", with the answer in the
Notes column). This is a non-blocking gate: with no answer, the plan proceeds
on the default. The run is non-interactive, so no question is asked; every
row below starts as "default applies".

## Open items (14)

The second list, "Revision 2 open items (16)", follows below.

| # | Item | Spec default | Status | Depending plan | Notes |
|---|------|--------------|--------|----------------|-------|
| 1 | Fleet page name | EN "Fleet", FR "Flotte" | default applies | 61-06 | D11 already fixes the name |
| 2 | Last image in the fleet list | Not shown | default applies | 61-06 | D12 already fixes this |
| 3 | Raw "Register a frame" (MAC + secret) form | Removed from every page; `/fleet/register` route and tests stay | default applies | 61-06 | |
| 4 | Users page actions as a "Manage user" dialog | One dialog per user | default applies | 61-08 | |
| 5 | Health for users | Out of the user tab bar and sidebar, reached from the Home status card | default applies | 61-04 | D14 already fixes this |
| 6 | Admin "My views" tabs | Home, Display, Flights; Health in the bar, Airlines/Device in More/sidebar | default applies | 61-04 | |
| 7 | "Use another account" on the not-invited page | Adds `prompt=login` to the Auth0 start | default applies | 61-11 | |
| 8 | First-visit hint wording | No mention of Auth0 sign-up (spec section 5 wording) | default applies | 61-11 | |
| 9 | Welcome toast on the first identity link | Included (small "first link" flag) | default applies | 61-11 | |
| 10 | User redirect from un-prefixed pages | 303 to the user's own frame | default applies | 61-05 | D13 already fixes this |
| 11 | Invite button wording | "Invite user" replaces "Send invitation" | default applies | 61-08 | |
| 12 | Pending frames in the Fleet list | Stay in the main list (hollow dot, after active frames) | default applies | 61-06 | |
| 13 | Landing frame for a multi-frame user | First by name | default applies | 61-05 | |
| 14 | Manage access reopens after each add/remove | Reopens via `?access=<id>` | default applies | 61-07 | |

## Revision 2 open items (16)


Source: the "Open for owner validation (revision 2)" list at the end of `61-UI-SPEC.md`, plus R2-17 and R2-18 raised by the planner. The rule above applies unchanged.


| # | Item | Spec default | Status | Depending plan | Notes |
|---|------|--------------|--------|----------------|-------|
| R2-1 | Name of the personal space (V1) | EN "My frame", FR "Mon cadre" | default applies | 61-21 |  |
| R2-2 | Space switch form (V2) | Two segments always visible, full-width strip under the header on phone, top of the sidebar on desktop, current segment accent-filled | default applies | 61-22 |  |
| R2-3 | Frame switcher form (V6) | Frame chip opening a card sheet (bottom sheet on phone, centred dialog on desktop); one frame renders nothing | default applies | 61-23 |  |
| R2-4 | Pin interaction (V7/D19) | Tap or click drops a draggable pin; the map pans freely | default applies | 61-26 |  |
| R2-5 | Where the frame's own position is stored (D20) | A private `locations` row per frame, created on the first map save, copy-on-write when an old row is shared (no schema change) | default applies | 61-18 |  |
| R2-6 | Leaflet version (D18) | Leaflet 1.9.4 | default applies | 61-24 |  |
| R2-7 | Tile provider | Public OpenStreetMap tile server under its usage policy; Nominatim for search (submit only, 1 request per second) | default applies | 61-24 |  |
| R2-8 | Search scope | `countrycodes=fr`; the free-pin box check stays metropolitan France and Corsica, a catalogue airport is accepted anywhere | default applies | 61-20 and 61-26 |  |
| R2-9 | Administrator without any frame of their own | Personal Home shows the same empty state as a user; the served frame is reached from Fleet ("Open personal view") and the Console | default applies | 61-19 |  |
| R2-10 | Health for users (D14 superseded by D16) | No Health entry or link for a user or for the administrator's personal space; Console only | owner answered (D21) | 61-17, 61-19 and 61-34 | A user has no Health page, the status dot on Home is enough, and when the dot is amber (warn state) a notification on Home gives more information and offers to contact an administrator by a mailto link addressed to the administrator's email, with no server-side sending (D21, D22). Plan 61-34 builds the notification; plan 61-17 only removes the Health link. |
| R2-11 | Console frame pages | Health, Device and Airline editor show one frame at a time with a frame chip listing every frame; Fleet's name link goes to Health | default applies | 61-19 and 61-23 |  |
| R2-12 | Airline collection rarity and badges (V10) | Regular (10 or more sightings), Occasional (3-9), Rare (1-2) from this frame's own history; five badges (1, 5, 10, 25, 50 airlines); dimmed not-yet-seen cards; no points or streaks | default applies | 61-30 |  |
| R2-13 | Airline collection name and place | "Airline collection" / "Collection de compagnies", personal space, read-only for everyone including administrators | default applies | 61-30 |  |
| R2-14 | Quiet-hours write path (V8) | New `POST /quick/quiet-hours/window` writing only the three quiet-hours keys | default applies | 61-27 |  |
| R2-15 | Personalisation phone-bar label | "Style" / "Style" in the bar, "Personalisation" / "Personnalisation" everywhere else | default applies | 61-21 |  |
| R2-16 | Locations POST routes | Kept with no UI (expand-only) | default applies | 61-17 |  |
| R2-17 | Name this airline link in Flight history | UI-SPEC 1.1 says no personal page shows it to anyone, 12.2 says an administrator sees it; default follows 1.1 and R1 (no link for anyone) | default applies | 61-22 and 61-31 | raised by the planner |
| R2-18 | A live frame with a fleet row is addressed by /devices/<id>/ for everyone | Applies | default applies | 61-19 | raised by the planner |

## Audit items brought into scope

The owner answered "yes, in scope" on 2026-11-03 for the three small items
from `61-VISUAL-AUDIT-NOTES.md` that had no owning plan. Plan 61-15
implements the three.

| Row | Item | Source line in 61-VISUAL-AUDIT-NOTES.md | Owning plan | Status |
|-----|------|------------------------------------------|-------------|--------|
| A | Device page: the Diagnostic LED switch is drawn with an orange box around it | line 61 | 61-15 | in scope (owner, 2026-11-03) |
| B | Health page: the Frame connection row says "Has not checked in" three ways | line 62 | 61-15 | in scope (owner, 2026-11-03) |
| C | Empty states are large serif blocks (Current frame card empty, other empty states) | lines 58-59 | 61-15 | in scope (owner, 2026-11-03) |
