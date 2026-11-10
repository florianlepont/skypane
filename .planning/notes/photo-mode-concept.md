# Photo mode: concept brief (v1.3 candidate)

Status: exploration, decided with the owner in a discussion session on
2026-11-10. No production code was changed. Trial images and scripts live
outside the repository.

## Idea

Add a second display mode, "photos", next to the current "plane" mode. A frame
in photo mode shows still pictures instead of the flight screen. The frame
stays "dumb": the server prepares the image, the frame downloads and displays
it.

## Decisions taken

| # | Topic | Decision |
|---|-------|----------|
| 1 | Photo source | The user's own photos first (uploaded from the companion). Provided collections right after, as v1.3.x. External albums/services are out of scope. |
| 2 | Mode selection | One mode per frame, plane or photos, set in the companion. No automatic switch when no plane is around, no time-of-day schedule (both are later ideas). |
| 3 | Scope of v1.3 | Simple: upload, per-frame mode, rotation. Collections come in v1.3.x. No schedule. |
| 4 | Privacy | Photos are visible only to the frame owner and co-managers. **The admin never sees user photos**, and no admin view of them is to be built. Only a reduced, normalised copy is stored (no original). Deleting a photo removes the file from disk; deleting an account removes all its photos. Quota to settle in planning (starting point: 20 photos per frame, about 1 MB each at most). |
| 5 | Fitting a photo to the panel | Crop to fill by default, with a per-photo setting (crop or bands) and a way to move the crop in the companion. The same stored photo must serve both the portrait (1200x1600) and the landscape (800x480) panels. |
| 6 | Rotation | Per frame: hourly, every 6 h, every 12 h or daily (default daily). Order: random without repeats, or upload order. In photo mode the frame's wake interval follows the rotation interval. |
| 7 | Collection licences | Public domain / CC0 only (old paintings, museum open-access programmes, NASA). No CC-BY or CC-BY-SA at first, since they require showing the author on the frame. Every image is recorded with source, author and licence in a tracking file. |
| 8 | Artist collection | One collection comes from an artist (the owner's contact, "Atelier Jacqueline Suzanne") who agreed to have the work shown. This is not public domain: keep the written agreement, record the credit in the tracking file, and keep the ability to withdraw the images. |
| 9 | Language | This brief and the seed are in English, like the repository files. |

## What was checked in the code

- 6-colour dithering exists: `server/plane/dither.py` (Floyd-Steinberg against
  the panel palette in `server/panel_format.py`), with tests in
  `server/test_dither.py`.
- Image upload with normalisation exists for illustrations
  (`companion/illustration_normalize.py`, `server/plane/illustrations.py`). It
  is built for aircraft art, so photos need their own, stricter path.
- The server serves images content-addressed by SHA-256
  (`stub-server/byos_server.py`), and the frame already skips the redraw when
  the hash is unchanged. A photo that does not change therefore costs almost
  nothing on the panel.
- Per-device detection modes already exist (`server/detection.py`), so a
  per-device display mode has a natural place to sit.
- Panels: 1200x1600 portrait today; 800x480 landscape under study
  (`hardware/SECOND-HARDWARE.md`).

## Visual trials (outside the repository)

Public-domain and openly licensed images were run through the existing
dithering, portrait and landscape.

- The current dithering alone works, but the result is dull and greyish.
- Raising contrast (auto-contrast) and colour saturation **before** dithering
  gives clearly better results: clean skies, readable detail, strong blue and
  yellow.
- Not tested yet: skin tones. Portraits of people are the likely weak spot and
  must be tried before the design is frozen.
- Fitting a portrait photo to the landscape panel: cropping looks best, bands
  waste a third of the screen, a blurred background is attractive but busy.

## Battery

Based on `hardware/BATTERY-MODEL.md` (derived figures, battery capacity rated
and not measured): one wake costs about 0.34 mAh, and an unchanged image skips
the redraw. In photo mode the main lever is the wake interval, not the
refresh. A frame that wakes once per rotation interval should last much longer
than in plane mode. The panel refresh is about 20-25 s. Real measurements are
needed on a real frame before stating an autonomy figure.

## Risks

1. **Privacy and legal.** Photos of people stored on the owner's server. Mitigated by the visibility
   rule, reduced copies only, real deletion, and account-deletion cleanup.
   Uploads need the same hardening as the illustration upload (size limit,
   strict image validation, no trusted filename).
2. **Storage.** Small, but unbounded without a quota. Per-frame quota and a
   server-wide ceiling to set; add storage to the backup scope or decide
   explicitly that photos are not backed up.
3. **Quality.** Six colours make faces and gradients hard. Needs the
   pre-processing step above, a preview in the companion showing the dithered
   result before saving, and honest expectations (a "dithered look" is part of
   the product).
4. **Collections and licences.** Wrong licence metadata is a legal risk.
   Keep the tracking file and review each image. The artist collection needs
   a written agreement.
5. **Production deploy.** Every merge into `main` deploys. Plane-mode
   rendering and its golden fixtures (`server/fixtures/golden`) must stay
   untouched; photo mode must be a separate render path.
6. **Frame wake logic.** Changing the wake interval per mode touches the
   device policy shared with the energy-measurement work. Do it only after the
   current battery measurement phases are finished.
7. **Fleet complexity.** Per-device mode multiplies test cases (two panel
   sizes, two modes, owner vs co-manager vs admin views).

## Possible phases

1. **Photo pipeline (server only).** Normalise an uploaded photo into a stored,
   reduced copy; render it for a given panel profile (crop, pre-processing,
   dithering); tests including both panel sizes and skin-tone samples. No
   companion change yet.
2. **Storage, privacy and quotas.** Per-frame storage, owner and co-manager
   access only, real deletion, quota, account-deletion cleanup, backup decision.
3. **Frame mode and rotation.** Per-device display mode (plane or photos),
   rotation interval and order, serving the current photo, wake interval
   following the rotation.
4. **Companion UI.** Upload, photo list, delete, per-photo crop or bands with
   movable crop, dithered preview, mode and rotation settings. English and
   French strings.
5. **(v1.3.x) Provided collections.** Public-domain sets with the tracking
   file, plus the artist collection with its agreement; a way for a user to
   add a collection to a frame.

## Open points for planning

- Exact quota, and whether photos are included in the backup.
- Smart crop (detect the subject) or manual crop only.
- Whether the preview in the companion is rendered by the server or in the
  browser.
- What the frame shows if a photo-mode frame has no photo yet.
- Exact moment to touch the wake-interval policy relative to the battery
  measurement work.
