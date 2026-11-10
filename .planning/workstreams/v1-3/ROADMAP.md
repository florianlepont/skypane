# Roadmap: SkyPane

## Milestones

- [x] **v1.0 — MVP** — shipped and archived on 2026-09-30 (see the root `.planning/milestones/`).
- [ ] **v1.1 — Battery and Companion!** — Phases 44–47, tracked in the root `.planning/ROADMAP.md`. Phases 47, 47.1 and 47.2 (battery measurement on the live frame) are not touched by this roadmap.
- [ ] **v1.2 — Fleet platform** — Phases 48–63, tracked in the `v1-2` workstream.
- [ ] **v1.3 — Photo display mode** — Phases 64–68 (this workstream, `v1-3`). A frame can show the owner's own photos instead of the flight screen, with per-frame mode and rotation.

## Overview

V1.3 adds a second display mode, "photos", next to "plane". The frame stays dumb: the server prepares a dithered image and the frame downloads it, exactly as today. The work is a separate photo render path (strict upload normalisation, crop, contrast and saturation boost, 6-colour dithering), private per-frame storage with quotas and real deletion, a per-frame mode and rotation served by the existing BYOS, and the companion screens to manage it. There is no new runtime dependency and no new daemon. Provided collections (COLL-01, COLL-02) are v1.3.x and are not in any phase here.

## Coordination

- **Battery measurement (Phases 47, 47.1, 47.2):** Phase 68 (MODE-04, wake interval follows the rotation interval) changes the device wake policy shared with the energy-measurement work. It must not start until Phases 47, 47.1 and 47.2 are finished, or the owner explicitly releases it. Phases 64–67 do not touch the wake policy and may proceed now.
- **Plane rendering is never modified.** The plane screen render path and `server/fixtures/golden` stay untouched in every phase (MODE-05). Photo mode is a separate render path; any change that would alter a golden fixture is a defect, not an update.
- **Production deploys:** every merge to `main` deploys to production by CI. The owner decides when to merge, so the owner decides when each phase reaches production. Each phase must be safe to deploy on its own: forward-only, expand-only, with the live frame's plane-mode behaviour unchanged (no frame is in photo mode until the owner sets it).
- **Privacy:** the admin never sees user photos, in any phase. No admin view of photos is built, and admin routes and the backup/health pages must not expose photo content or names.

## Phases

**Phase Numbering:**

- Integer phases are planned milestone work, continuing from v1.2 (Phase 63).
- Decimal phases are urgent insertions created only when needed.

- [x] **Phase 64: Photo Pipeline (Server Only)** - An uploaded photo is validated, reduced to one stored copy, and rendered for either panel profile with crop, boost and dithering, with skin-tone results recorded.
- [ ] **Phase 65: Photo Storage, Privacy and Quotas** - Photos are stored per frame, visible only to the owner and co-managers, really deleted, and bounded by quotas.
- [ ] **Phase 66: Frame Mode, Rotation and Waiting Screen** - Each frame has one display mode and a rotation, and the server serves the current photo or a waiting screen, with plane mode unchanged.
- [ ] **Phase 67: Companion Photo Management and Settings** - Owners and co-managers upload, preview, list and delete photos and set mode and rotation, in English and French.
- [ ] **Phase 68: Photo-Mode Wake Interval** - In photo mode the frame wakes once per rotation interval. Gated on the battery measurement phases.

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

**Plans**: TBD

### Phase 66: Frame Mode, Rotation and Waiting Screen

**Goal**: Each frame has exactly one display mode and, in photo mode, the server serves the right photo for the rotation, while plane mode stays byte-for-byte as it is.
**Depends on**: Phase 64, Phase 65
**Requirements**: MODE-01, MODE-02, MODE-03, MODE-05
**Success Criteria** (what must be TRUE):

  1. A frame has exactly one mode, plane or photos, stored per device and defaulting to plane; the mode can be changed through the server and companion data layer (the companion screen comes in Phase 67).
  2. A photo-mode frame is served the current photo for its rotation interval (hourly, 6 h, 12 h or daily, default daily) in the chosen order; random order never repeats a photo before all have been shown, and upload order follows upload time.
  3. A photo-mode frame with no photo is served a defined waiting screen in both panel sizes, and the frame's image hash stays unchanged between rotations so no redraw is triggered.
  4. Plane-mode output is unchanged: the `server/fixtures/golden` fixtures and plane render tests pass without modification, and the live frame's responses are identical before and after.

**Plans**: TBD

### Phase 67: Companion Photo Management and Settings

**Goal**: A frame owner or co-manager can manage the frame's photos and its mode and rotation entirely from the companion, in English and French.
**Depends on**: Phase 66
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):

  1. The owner or a co-manager can upload a photo, see the frame's photo list, and delete a photo, and a user with no management right on the frame cannot see or reach any of it.
  2. Before saving an upload, the user sees the dithered result for the frame's panel and can move the crop or choose crop-to-fill or bands; what is saved matches what was shown.
  3. The owner or a co-manager can set the frame's mode (plane or photos), rotation interval and order, and the next image the frame fetches reflects the change.
  4. Every new screen and message is available in English and French, and works on a phone and a desktop.

**Plans**: TBD
**UI hint**: yes

### Phase 68: Photo-Mode Wake Interval

**Goal**: A photo-mode frame wakes only about once per rotation interval, so it lasts much longer on battery than in plane mode, without changing plane-mode cadence.
**Depends on**: Phase 66; Phases 47, 47.1 and 47.2 (battery measurement) finished or explicitly released by the owner
**Requirements**: MODE-04
**Success Criteria** (what must be TRUE):

  1. A photo-mode frame is told to wake at its rotation interval (hourly, 6 h, 12 h or daily), and the interval changes when the rotation setting changes.
  2. A plane-mode frame, including the live frame, receives exactly the same wake interval as before the change, proven by a test on the wake policy.
  3. The change lands only after the battery measurement phases are finished or released by the owner, and the battery numbers it relies on (`hardware/BATTERY-MODEL.md`) are marked as measured or still derived.

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 64. Photo Pipeline (Server Only) | 5/5 | Complete (closed 2026-11-10 with one open point: how real skin looks was never judged) | 2026-11-10 |
| 65. Photo Storage, Privacy and Quotas | 0/0 | Not started | - |
| 66. Frame Mode, Rotation and Waiting Screen | 0/0 | Not started | - |
| 67. Companion Photo Management and Settings | 0/0 | Not started | - |
| 68. Photo-Mode Wake Interval | 0/0 | Not started (gated on Phases 47, 47.1, 47.2) | - |
