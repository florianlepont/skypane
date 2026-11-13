# Photo frames: a frame has a type (planes or photos)

Status: decision of the owner, 2026-11-13. Replaces the "Planes | Photos switch" design.

## Decision

SkyPane photo mode is a second product on the same hardware and stack. Each frame has a type, "planes" or "photos". Only an administrator sets it, from the Console. The owner and co-managers never do.

- No user-facing mode switch, no pending state, no banner, no fallback from photos to planes.
- A user with several frames switches between them with the existing frame picker. The menu follows the selected frame's type.

### Menus

- Plane frame: today's menu, unchanged: Home, Flight history, Location and detection, Style, Airlines. No Photos entry. The earlier idea of removing the Flight history tab is dropped (it was only needed to make room for Photos).
- Photo frame: Home, Photos, Style, Account. No plane pages.
- The Photos entry is hidden from anyone who cannot open it (an administrator who is not a manager of the frame).

### Photo frame screens

- Home: a neutral "Showing your photos" card with the next-photo time, battery and last check-in. No photo image on Home (v1.3 cut, kept for privacy and simplicity).
- Photos page: photo list, upload, quota, rotation interval (Hourly, 6 h, 12 h, Daily; default Daily), per-photo adjust (Fill the screen | Whole photo + three positions; one form with Update preview and Save; no drag), delete, privacy line.
- Order is always shuffled without repeats. The order option stays cut.
- A photo frame with no photo shows the defined waiting screen (this comes back; the "fall back to planes" idea is dropped).
- Quiet hours stay active: the photo stays on the glass and the frame sleeps through the hours.

### Console

The administrator changes a frame's type in the frame settings, with a clear confirmation. It takes effect at the frame's next wake, and the Console says "type changes at the next wake". Changing the type of a frame that holds photos asks for explicit confirmation: the photos are kept, they are not shown while the type is planes, and they stay visible only to the owner and co-managers, never to the admin.

## Why

- Promise: a plane frame is a plane frame. It never shows something else by accident, and the live frame never changes.
- Wake cadence and battery: a photo frame has no reason to wake every 30 s-class cycles; it wakes hourly. A switch would make one frame need both cadences and a pending state to explain the gap.
- Privacy obligations: photos are visible only to owner and co-managers. An admin-only type keeps the admin out of photos, and the Photos entry is hidden when the viewer cannot open it.
- Complexity that disappears: the mode switch, the pending state with a clock time, the banner on plane pages, the fallback to planes, and the Flight history removal.
- Reversibility: opening a user-facing switch later is easy (the type is plain data). Removing one later is hard. So v1.3 ships admin-only.

## What it replaces

`photo-mode-workflow.md`, `photo-mode-simplification.md`, `photo-companion-navigation.md` and sketches 010 and 011, for the mode switch and the menu. They stay as history. Brief decision 6 (wake follows rotation) is challenged: the rotation interval and the wake interval are separate (photo frames wake hourly whatever the rotation).

## Consequences by phase

- Phase 64 (built): stays valid, no change.
- Phase 65 (built): stays valid. The MANAGER_DEVICE route kind (owner or co-manager) is what the Photos routes need.
- Phase 66 (server): registry key for the type in device_config (a proper registered key, not an unregistered one that a later save would erase); rotation; serving the photo of the moment or the waiting screen; photo frames skipped for the ADS-B fetch (lowest-priority hold kind, heartbeat kept); photo renders never go through the gallery or publish_canvas path (the admin can open the gallery); the "around HH:MM" next-wake time uses the interval the frame is actually sleeping on; plane rendering and golden fixtures unchanged.
- Phase 67 (companion): menu by frame type, Photos page, Home card, Console type control with confirmations, EN/FR, phone and desktop.
- Phase 68 (wake): photo frames wake hourly. Gated on Phases 47, 47.1 and 47.2. Needs mode-aware health thresholds: "No contact" = 2x the wake interval, with a ceiling of 3600 s.

## Companion prototype consequences

Sketches 010 and 011 no longer describe the design. A new prototype for frame types is needed (plane menu unchanged, photo menu, Home card, Photos page, Console type control). See the maintenance rule below.

## Open points

- Whether users with a photo frame can create or pair one themselves is out of scope (the admin pairs frames today).
- v1.3 cuts kept: one shuffled order, Fill/Whole plus three positions, no photo on Home.

## Companion prototype (maintenance rule) - PENDING

Rule: any phase that changes a companion screen updates the prototype under `docs/prototype/`, or states "prototype unchanged" with the reason. The phase verification checks it.

PENDING: the rule is not yet in force, and the move of the prototype to `docs/prototype/` is not yet done. Both are decided later by the owner.
