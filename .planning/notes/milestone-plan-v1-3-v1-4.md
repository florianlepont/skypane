# Plan of milestones v1.3 and v1.4

Decided by the owner on 2026-11-15, after the v1.2 phases were set. Milestones
open only once v1.1 and v1.2 are finished. Seeds hold the detail; this note holds
the split.

## v1.3 "Photo": the second mode

Theme: the frame can show photos, not only planes.

- SEED-013, items 1, 2, 3 and 5: messages with pictures, portrait and landscape
  for both frame types, plane or photo per frame, photo collections (public
  domain or CC0, and partnerships).
- SEED-016: a power-saving mode chosen by the user (it follows the wake interval
  per mode of photo mode; needs the Phase 47.1 measurements).
- SEED-020 (moved to v1.2 as Phase 68 on 2026-11-16): the visual improvements of
  the console. The screens added by photo mode follow the same design system.

## v1.4 "Ready to give": a frame someone else can use

Theme: prepare a frame, hand it over, and run a small fleet of frames in other
homes.

- SEED-013, items 4 and 6: the getting-started wizard and the simplified Wi-Fi
  setup.
- SEED-012: the administrator's invitation creates the Auth0 account.
- SEED-014: the enclosure for the back of the frame, and the administrator tool
  for initial setup and flashing.
- SEED-017: remote diagnostic telemetry.
- SEED-018: the firmware update policy (automatic by default, "ask me",
  administrator override, all frames together).
- SEED-019: battery discharge and curve validation for both frames.

Reason for the move: telemetry and the update policy only matter once frames
leave the owner's home; the Wi-Fi setup and the wizard are part of the same
hand-over journey as the enclosure and the flashing tool; all of them change the
firmware or the pairing flow and are better released together.

## Later

- SEED-015: business plan and technical feasibility of a market launch (after
  v1.4, or earlier for the "decide early" items).
- Without a milestone: SEED-011, the AeroDataBox destination lookup, the local
  RTL-SDR backup, the presence-adaptive polling.
