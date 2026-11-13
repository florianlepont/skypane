> Superseded on 2026-11-13 by photo-frame-types.md for the mode switch and the menu. Kept as history.

# Photo mode: companion navigation (decisions of 2026-11-11)

Input for the companion phase of milestone v1.3. The mockups are in
`.planning/sketches/007-009`.

## Decisions

- A new **Photos** page in the personal space (the pages a frame's owner and
  co-managers see). It holds the photo list and upload, the crop or bands
  choice and the preview, and the mode and rotation settings. The
  "planes / photos" choice sits at the top of this page.
- In **photo mode** the plane pages (Flights, Detection, Airlines) are
  **hidden** from the menu. They come back when the frame returns to plane
  mode. Home stays.
- In **plane mode** the Photos page stays visible, empty, with a clear
  action to switch the frame to photo mode.
- Switching the mode takes effect at the frame's next wake. Photos are kept
  when the frame returns to plane mode.

## Correction to the mockups

The mockups place the mode and rotation settings on the Device page. In the
code that page is a Console page (administration), so an ordinary owner
cannot open it. These settings belong on the Photos page, which the owner
can open. The admin never sees user photos.

## Still to settle when the screens are built

- Which variant of each mockup to build (recommended: 007 A, 008 A with the
  crop-window explanation of 008 C as a help view, 009 A).
- The exact menu position and label of the Photos page, on the phone bar and
  in the More sheet.
- Hiding rule for a frame whose mode changes while the page is open.
