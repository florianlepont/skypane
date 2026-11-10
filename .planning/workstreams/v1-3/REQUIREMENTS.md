# Requirements: SkyPane

**Defined:** 2026-11-10
**Milestone:** v1.3 Photo display mode
**Core Value:** Glancing at the frame tells you, in real time, which plane is taking off or landing right now — while also being a satisfying ambient piece on the wall.

Runs in parallel with v1.1 (Phases 47 and 47.1, untouched) and v1.2. Phase numbering continues from 64. Source: seed SEED-013 and `.planning/notes/photo-mode-concept.md`; the decisions in that brief are taken and are not reopened here.

## v1.3 Requirements

### Photo Pipeline

- [ ] **PHOTO-01**: An uploaded photo is validated strictly (size limit, real image decoding, no trusted filename) and reduced to one stored, normalised copy; the original is never kept.
- [ ] **PHOTO-02**: A stored photo is rendered for a given panel profile (portrait 1200x1600 or landscape 800x480) through a render path separate from the plane screen: crop, contrast and saturation boost, then 6-colour dithering.
- [ ] **PHOTO-03**: Each photo can be set to crop-to-fill (default) or bands, and its crop can be moved; the same stored photo serves both panel sizes.
- [ ] **PHOTO-04**: The rendering is tried on skin-tone samples, and the result and any limit are recorded before the rendering is frozen.

### Storage and Privacy

- [ ] **PRIV-01**: Photos are visible only to the frame owner and its co-managers; the admin has no view of user photos and none is built.
- [ ] **PRIV-02**: Deleting a photo removes its file from disk; deleting an account removes all its photos.
- [ ] **PRIV-03**: A per-frame quota (starting point: 20 photos, about 1 MB each) and a server-wide ceiling bound the storage.
- [ ] **PRIV-04**: Whether photos are in the backup is decided explicitly and recorded.

### Frame Mode and Rotation

- [ ] **MODE-01**: Each frame has exactly one display mode, plane or photos, set in the companion.
- [ ] **MODE-02**: Each frame has a rotation interval (hourly, 6 h, 12 h, daily; default daily) and an order (random without repeats, or upload order); the server serves the current photo for it.
- [ ] **MODE-03**: A photo-mode frame with no photo yet shows a defined waiting screen.
- [ ] **MODE-04**: In photo mode the frame's wake interval follows the rotation interval, changed only after the battery-measurement phases are finished.
- [ ] **MODE-05**: Plane-mode rendering and `server/fixtures/golden` are unchanged.

### Companion

- [ ] **UI-01**: The owner or a co-manager can upload, list and delete photos for a frame.
- [ ] **UI-02**: The companion shows the dithered result before the photo is saved.
- [ ] **UI-03**: The owner or a co-manager can set the mode and the rotation, in English and French.

## Future Requirements

- **COLL-01** (v1.3.x): Provided collections, public domain or CC0 only, each image recorded with source, author and licence in a tracking file; a user can add a collection to a frame.
- **COLL-02** (v1.3.x): One artist collection under a written agreement, with the credit recorded and the ability to withdraw the images.
- **SCHED-01**: Automatic switch to photos when no plane is around, and time-of-day schedules.
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
| (filled by the roadmap) | | |
