# Roadmap: SkyPane

## Milestones

- [x] **v1.0 — MVP** — shipped and archived on 2026-09-30 (see the root `.planning/milestones/`).
- [ ] **v1.1 — Battery and Companion!** — Phases 44–47, tracked in the root `.planning/ROADMAP.md`. Phases 47, 47.1 and 47.2 (battery measurement on the live frame) are not touched by this roadmap.
- [ ] **v1.2 — Fleet platform** — Phases 48–63, tracked in the `v1-2` workstream.
- [ ] **v1.3 — Photo display mode** — Phases 64–68 (this workstream, `v1-3`). A frame has a type, planes or photos, set by an administrator; a photo frame shows the owner's own photos with a rotation interval.

## Overview

V1.3 adds a second frame type, "photos", next to "planes" (see `.planning/notes/photo-frame-types.md`). Photo mode is treated as a second product on the same hardware and stack. The frame stays dumb: the server prepares a dithered image and the frame downloads it, exactly as today. The work is a separate photo render path (strict upload normalisation, crop, contrast and saturation boost, 6-colour dithering), private per-frame storage with quotas and real deletion, a per-frame type (set only by an administrator) and rotation served by the existing BYOS, and the companion screens to manage it. There is no user-facing mode switch. There is no new runtime dependency and no new daemon. Provided collections (COLL-01, COLL-02) are v1.3.x and are not in any phase here.

## Coordination

- **Battery measurement (Phases 47, 47.1, 47.2):** Phase 68 (MODE-04, photo frames wake every hour) changes the device wake policy shared with the energy-measurement work. It must not start until Phases 47, 47.1 and 47.2 are finished, or the owner explicitly releases it. Phases 64–67 do not touch the wake policy and may proceed now.
- **Plane rendering is never modified.** The plane screen render path and `server/fixtures/golden` stay untouched in every phase (MODE-05). Photo rendering is a separate render path and never goes through the gallery or `publish_canvas` path (SRV-01); any change that would alter a golden fixture is a defect, not an update.
- **Production deploys:** every merge to `main` deploys to production by CI. The owner decides when to merge, so the owner decides when each phase reaches production. Each phase must be safe to deploy on its own: forward-only, expand-only, with the live frame's plane behaviour unchanged (every frame is a plane frame until an administrator sets it otherwise).
- **Privacy:** the admin never sees user photos, in any phase. No admin view of photos is built, admin routes and the backup/health pages must not expose photo content or names, and the Photos entry is hidden from an administrator who is not a manager of the frame.
- **Companion prototype:** the maintenance rule in `photo-frame-types.md` (update `docs/prototype/` or state "prototype unchanged") is PENDING; once in force, Phase 67 verification checks it.

## Phases

**Phase Numbering:**

- Integer phases are planned milestone work, continuing from v1.2 (Phase 63).
- Decimal phases are urgent insertions created only when needed.

- [x] **Phase 64: Photo Pipeline (Server Only)** - An uploaded photo is validated, reduced to one stored copy, and rendered for either panel profile with crop, boost and dithering, with skin-tone results recorded.
- [x] **Phase 65: Photo Storage, Privacy and Quotas** - Photos are stored per frame, visible only to the owner and co-managers, really deleted, and bounded by quotas.
- [ ] **Phase 66: Frame Type, Rotation and Waiting Screen** - A frame has a type (planes or photos) stored as a registered setting; the server serves the photo of the moment or a waiting screen to photo frames, skips them for ADS-B, and keeps plane output unchanged.
- [ ] **Phase 67: Companion Photo Frames** - The menu follows the frame type, owners and co-managers manage photos and rotation, and an administrator sets the type in the Console, in English and French.
- [ ] **Phase 68: Photo-Frame Wake Interval** - Photo frames wake every hour with mode-aware health thresholds. Gated on the battery measurement phases.

## Phase Details

### Phase 64: Photo Pipeline (Server Only)

**Goal**: A photo handed to the server can be safely reduced to one stored copy and rendered as a 6-colour image for either panel size, with the quality limits known before the rendering is frozen.
**Depends on**: Nothing in v1.3 (no companion change, no production behaviour change)
**Requirements**: PHOTO-01, PHOTO-02, PHOTO-03, PHOTO-04
**Success Criteria** (what must be TRUE):

  1. A file that is oversized, not a real decodable image, or carries a misleading name or type is rejected; a valid upload yields exactly one reduced, normalised stored copy and the original bytes are not kept anywhere.
  2. The same stored photo renders to a 1200x1600 portrait image and an 800x480 landscape image, each using only the panel palette, through a render path separate from the plane screen.
  3. A photo set to crop-to-fill (default) fills the panel with the chosen crop position, and one set to bands shows the whole photo with bands; changing the crop position changes the rendered result.
  4. Rendering skin-tone samples in both panel sizes has been tried, and the result and any limit are written down before the rendering parameters are frozen.

**Plans**: 5 plans

Plans:
- [x] 64-01-PLAN.md - strict upload validation and one reduced stored copy (PHOTO-01)
- [x] 64-02-PLAN.md - crop or bands, pre-processing and render for both panel profiles (PHOTO-02, PHOTO-03)
- [x] 64-03-PLAN.md - skin-tone trial tooling and the rendering document skeleton (PHOTO-04)
- [x] 64-04-PLAN.md - owner review of the skin-tone contact sheets, blocking checkpoint (PHOTO-04); the owner could not judge them, defaults kept
- [x] 64-05-PLAN.md - freeze the rendering parameters, complete the document, phase gate (PHOTO-04)

### Phase 65: Photo Storage, Privacy and Quotas

**Goal**: Photos live in private per-frame storage that only the frame's owner and co-managers can reach, that is bounded, and that really forgets what is deleted.
**Depends on**: Phase 64
**Requirements**: PRIV-01, PRIV-02, PRIV-03, PRIV-04
**Success Criteria** (what must be TRUE):

  1. The owner and a co-manager of a frame can read its photos; another user, an anonymous visitor and an admin who is not a manager of that frame get a refusal, and no admin page, health page or listing exposes a user photo or its name.
  2. Deleting a photo removes its file from disk, and deleting an account removes all of that account's photos, both checked on the filesystem.
  3. Uploading past the per-frame quota (starting point: 20 photos, about 1 MB each) or past the server-wide ceiling is refused with a clear reason and stores nothing.
  4. The decision on whether photos are in the backup is recorded in the repository docs, and the backup and restore behave as decided.

**Plans**: 8 plans

Plans:
- [x] 65-01-PLAN.md - photo table (expand-only migration) and row helpers, purge hooks (PRIV-02, PRIV-03)
- [x] 65-02-PLAN.md - private per-frame photo store with quota checks, owner and co-manager gate (PRIV-01, PRIV-03)
- [x] 65-03-PLAN.md - file purge and orphan sweep (PRIV-02)
- [x] 65-04-PLAN.md - purge on retire, reassign and account deletion (PRIV-02)
- [x] 65-05-PLAN.md - sweep command and start-up sweep (PRIV-02)
- [x] 65-06-PLAN.md - owner-or-co-manager route access kind and the guard (PRIV-01)
- [x] 65-07-PLAN.md - photos excluded from the backup, documented and tested (PRIV-04, PRIV-01, PRIV-03)
- [x] 65-08-PLAN.md - admin-leak test and phase gate (PRIV-01)

### Phase 66: Frame Type, Rotation and Waiting Screen

**Goal**: A frame has a type, and a photo frame is served the right photo for its rotation (or a waiting screen) without touching plane output or the gallery.
**Depends on**: Phase 64, Phase 65
**Requirements**: MODE-01, MODE-02, MODE-03, MODE-05, SRV-01
**Success Criteria** (what must be TRUE):

  1. A frame has exactly one type, planes or photos, stored as a registered `device_config` key (a later save does not erase it), defaulting to planes; it can be changed only through an administrator path, never by the owner or a co-manager.
  2. A photo frame is served the photo of the moment for its rotation interval (hourly, 6 h, 12 h or daily, default daily), shuffled without repeats before all photos have been shown.
  3. A photo frame with no photo is served a defined waiting screen in both panel sizes, and the image hash stays unchanged between rotations so no redraw is triggered; quiet hours still apply; the "around HH:MM" next-wake time uses the interval the frame is actually sleeping on.
  4. Photo frames are skipped for the ADS-B fetch (lowest-priority hold kind, heartbeat kept), and a photo render never goes through the gallery or `publish_canvas` path.
  5. Plane output is unchanged: the `server/fixtures/golden` fixtures and plane render tests pass without modification, and the live frame's responses are identical before and after.

**Plans**: TBD

### Phase 67: Companion Photo Frames

**Goal**: Each frame type has its own companion menu, owners and co-managers manage a photo frame's photos and rotation, and an administrator sets the frame type in the Console, in English and French.
**Depends on**: Phase 66
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):

  1. A plane frame keeps today's menu (Home, Flight history, Location and detection, Style, Airlines) with no Photos entry; a photo frame shows Home, Photos, Style, Account and no plane pages; the menu follows the frame chosen in the frame picker.
  2. The owner or a co-manager can upload, list and delete photos and set the rotation interval; a user who cannot manage the frame cannot see or reach any of it, and the Photos entry is hidden from an administrator who is not a manager.
  3. Before saving, the user sees the dithered preview for the frame's panel and can choose Fill the screen or Whole photo with one of three positions (one form, Update preview and Save); what is saved matches what was shown.
  4. A photo frame's Home shows a neutral "Showing your photos" card with the next-photo time, battery and last check-in, and no photo image.
  5. An administrator changes a frame's type in the Console frame settings with a confirmation, extra when the frame holds photos (they are kept, not shown while planes, never visible to the admin); the Console shows "type changes at the next wake" and the change lands at the next wake.
  6. Every new screen and message is available in English and French, and works on a phone and a desktop.

**Plans**: TBD
**UI hint**: yes

### Phase 68: Photo-Frame Wake Interval

**Goal**: A photo frame wakes about once an hour whatever its rotation interval, so it lasts much longer on battery than a plane frame, without changing plane-frame cadence.
**Depends on**: Phase 66; Phases 47, 47.1 and 47.2 (battery measurement) finished or explicitly released by the owner
**Requirements**: MODE-04
**Success Criteria** (what must be TRUE):

  1. A photo frame is told to wake every hour, independent of its rotation interval.
  2. A plane frame, including the live frame, receives exactly the same wake interval as before, proven by a test on the wake policy.
  3. Health thresholds are mode-aware: "No contact" is 2x the frame's wake interval with a ceiling of 3600 s, so an hourly photo frame is not shown as lost.
  4. The change lands only after the battery measurement phases are finished or released by the owner, and the battery numbers it relies on (`hardware/BATTERY-MODEL.md`) are marked as measured or still derived.

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 64. Photo Pipeline (Server Only) | 5/5 | Complete (closed 2026-11-10 with one open point: how real skin looks was never judged) | 2026-11-10 |
| 65. Photo Storage, Privacy and Quotas | 8/8 | Complete (verified 2026-11-11) | 2026-11-11 |
| 66. Frame Type, Rotation and Waiting Screen | 0/0 | Not started | - |
| 67. Companion Photo Frames | 0/0 | Not started | - |
| 68. Photo-Frame Wake Interval | 0/0 | Not started (gated on Phases 47, 47.1, 47.2) | - |
