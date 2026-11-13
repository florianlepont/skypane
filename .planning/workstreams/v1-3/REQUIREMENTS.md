# Requirements: SkyPane

**Defined:** 2026-11-10
**Milestone:** v1.3 Photo display mode
**Core Value:** Glancing at the frame tells you, in real time, which plane is taking off or landing right now — while also being a satisfying ambient piece on the wall.

Runs in parallel with v1.1 (Phases 47 and 47.1, untouched) and v1.2. Phase numbering continues from 64. Source: seed SEED-013, `.planning/notes/photo-mode-concept.md` and, for the frame type, `.planning/notes/photo-frame-types.md` (2026-11-13, which replaces the mode switch and challenges brief decision 6).

## v1.3 Requirements

### Photo Pipeline

- [x] **PHOTO-01**: An uploaded photo is validated strictly (size limit, real image decoding, no trusted filename) and reduced to one stored, normalised copy; the original is never kept.
- [x] **PHOTO-02**: A stored photo is rendered for a given panel profile (portrait 1200x1600 or landscape 800x480) through a render path separate from the plane screen: crop, contrast and saturation boost, then 6-colour dithering.
- [x] **PHOTO-03**: Each photo can be set to crop-to-fill (default) or bands, and its crop can be moved; the same stored photo serves both panel sizes.
- [x] **PHOTO-04**: The rendering is tried on skin-tone samples, and the result and any limit are recorded before the rendering is frozen.

### Storage and Privacy

- [x] **PRIV-01**: Photos are visible only to the frame owner and its co-managers; the admin has no view of user photos and none is built.
- [x] **PRIV-02**: Deleting a photo removes its file from disk; deleting an account removes all its photos.
- [x] **PRIV-03**: A per-frame quota (starting point: 20 photos, about 1 MB each) and a server-wide ceiling bound the storage.
- [x] **PRIV-04**: Whether photos are in the backup is decided explicitly and recorded.

### Frame Type and Rotation

- [ ] **MODE-01**: A frame has a type, planes or photos (default planes), set only by an administrator; the owner and co-managers cannot change it.
- [ ] **MODE-02**: A photo frame has a rotation interval (hourly, 6 h, 12 h, daily; default daily); photos are shuffled without repeats and the server serves the photo of the moment.
- [ ] **MODE-03**: A photo frame with no photo shows a defined waiting screen.
- [ ] **MODE-04**: Photo frames wake every hour whatever the rotation interval, changed only after the battery-measurement phases are finished, with health thresholds that follow the frame's wake interval.
- [ ] **MODE-05**: Plane rendering and `server/fixtures/golden` are unchanged.

### Server

- [ ] **SRV-01**: Photo frames are not fetched for ADS-B, and photo renders never reach the gallery.

### Companion

- [ ] **UI-01**: The owner or a co-manager can upload, list and delete photos for a photo frame.
- [ ] **UI-02**: The owner or a co-manager can adjust a photo (Fill the screen, or Whole photo with three positions) and see the dithered preview before saving.
- [ ] **UI-03**: The owner or a co-manager can set the rotation interval, in English and French.
- [ ] **UI-04**: The menu follows the selected frame's type: a plane frame keeps today's menu with no Photos entry; a photo frame has Home, Photos, Style, Account. The Photos entry is shown only to people who can open it.
- [ ] **UI-05**: An administrator changes a frame's type in the Console with a confirmation (extra confirmation if the frame holds photos); it takes effect at the frame's next wake.

## Future Requirements

- **COLL-01** (v1.3.x): Provided collections, public domain or CC0 only, each image recorded with source, author and licence in a tracking file; a user can add a collection to a frame.
- **COLL-02** (v1.3.x): One artist collection under a written agreement, with the credit recorded and the ability to withdraw the images.
- **SCHED-01**: Automatic switch to photos when no plane is around, and time-of-day schedules.
- **TYPE-01**: A user-facing frame type switch (v1.3 ships admin-only).
- **ORDER-01**: An order option (upload order) for photo rotation.
- **CROP-02**: Drag to crop.
- **HOME-01**: The current photo shown on Home.
- **CROP-01**: Smart crop that detects the subject.

## Out of Scope

| Feature | Reason |
|---|---|
| External albums or photo services | Decided in the concept brief |
| CC-BY and CC-BY-SA collections | They require showing the author on the frame |
| Admin view of user photos | Privacy rule |
| Keeping original uploads | Reduced copy only |

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| PHOTO-01 | Phase 64 | Complete |
| PHOTO-02 | Phase 64 | Complete |
| PHOTO-03 | Phase 64 | Complete |
| PHOTO-04 | Phase 64 | Complete |
| PRIV-01 | Phase 65 | Complete |
| PRIV-02 | Phase 65 | Complete |
| PRIV-03 | Phase 65 | Complete |
| PRIV-04 | Phase 65 | Complete |
| MODE-01 | Phase 66 | Pending |
| MODE-02 | Phase 66 | Pending |
| MODE-03 | Phase 66 | Pending |
| MODE-05 | Phase 66 | Pending |
| SRV-01 | Phase 66 | Pending |
| UI-01 | Phase 67 | Pending |
| UI-02 | Phase 67 | Pending |
| UI-03 | Phase 67 | Pending |
| UI-04 | Phase 67 | Pending |
| UI-05 | Phase 67 | Pending |
| MODE-04 | Phase 68 | Pending |

**Coverage:** 19/19 v1.3 requirements mapped (PHOTO 4, PRIV 4, MODE 5, SRV 1, UI 5), each to exactly one phase.
