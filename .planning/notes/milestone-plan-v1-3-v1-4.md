# Plan of milestones v1.3 and v1.4

Decided by the owner on 2026-11-15, after the v1.2 phases were set. **Order
swapped by the owner on 2026-11-24**: "Ready to give" now comes first and takes
the number v1.3; "Photo" comes second and takes the number v1.4. Milestones open
only once v1.1 and v1.2 are finished. Seeds hold the detail; this note holds the
split.

**Old numbering.** Documents written before 2026-11-24 (phase documents under
`.planning/workstreams/v1-2/phases/`, `.planning/STATE.md`, quick summaries) use
the old numbers: their "v1.3" means today's v1.4 "Photo", and their "v1.4" means
today's v1.3 "Ready to give". Seeds, the v1-2 roadmap, requirements and state, and
the photo concept note were updated. Firmware release tags such as `fw-v1.3.0`
are firmware versions and have nothing to do with milestones.

## v1.3 "Ready to give": a frame someone else can use (first)

Theme: prepare a frame, hand it over, and run a small fleet of frames in other
homes.

- SEED-013, items 4 and 6: the getting-started wizard and the simplified Wi-Fi
  setup.
- SEED-014: the administrator tool for initial setup and flashing (the physical
  enclosure of the 7.3 inch frame is Phase 69 of v1.2, an owner-driven parallel
  track; the enclosure of the 13.3 inch frame is SEED-022).
- SEED-017: remote diagnostic telemetry.
- SEED-018: the firmware update policy (automatic by default, "ask me",
  administrator override, all frames together).
- SEED-019: battery discharge and curve validation for both frames.
- SEED-011 and SEED-012 are no longer in this milestone: both are done (see
  below).

Reason for the grouping: telemetry and the update policy only matter once frames
leave the owner's home; the Wi-Fi setup and the wizard are part of the same
hand-over journey as the flashing tool; all of them change the firmware or the
pairing flow and are better released together.

## v1.4 "Photo": the second mode (second)

Theme: the frame can show photos, not only planes.

- SEED-013, items 1, 2, 3 and 5: messages with pictures, portrait and landscape
  for both frame types, plane or photo per frame, photo collections (public
  domain or CC0, and partnerships).
- SEED-016: a power-saving mode chosen by the user (it follows the wake interval
  per mode of photo mode; needs the Phase 47.1 measurements).
- SEED-023 (last step of v1.4, moved from v1.2 Phase 70.1 on 2026-11-27): the owner makes the
  repository private himself, after the pre-flip gate, and the post-switch checks
  are run. Until then the repository stays public with CI on hosted runners.
- The screens added by photo mode follow the design system (the console's visual
  work is Phase 68 and Phase 68.1 of v1.2).

## Already done (found on 2026-11-24)

- **SEED-012** (the administrator's invitation creates the Auth0 account):
  delivered by Phase 68, plan 28 (PR #506): `companion/auth0_management.py` creates
  the Auth0 user and a password-change ticket, the Users page shows the
  invitation message to copy and paste, and a `user.invitation` audit row records
  the outcome. The application does not itself send an e-mail.
- **SEED-011** (a distinct sign-in message when the Auth0 e-mail is not
  verified): delivered by Phase 61 (`unverified_email_page` in
  `companion/login_page.py`, used by `companion/sign_in.py`).

## Later

- SEED-015: business plan and technical feasibility of a market launch (after
  the two milestones above, or earlier for the "decide early" items).
- Without a milestone: the AeroDataBox destination lookup, the local
  RTL-SDR backup, the presence-adaptive polling.
