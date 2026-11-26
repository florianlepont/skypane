---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 08
status: complete
completed: 2026-11-26
requirements: [ENC-01]
---

# Plan 69-08 summary: EE04 image reframed to the visible window of the mat

## What was done

1. The owner read the visible window on the assembled frame with a calibration
   image and confirmed the values on 2026-11-26. Readings and window:
   `hardware/ENCLOSURE-VISIBLE-WINDOW.md` (x 48, y 30, 702 x 448 pixels of the
   800 x 480 panel).
2. The server draws each EE04 screen at the window size and pastes it into the
   800 x 480 image, with edge replication under the mat (PR 614). The window is
   a field of the EE04 hardware profile only; the 13.3 inch frame has none.
3. PR 614 was merged, CI was green on Linux (the 13.3 inch golden images are
   unchanged) and it was deployed to production on 2026-11-26 (deploy run
   45899235327).
4. The owner tested the assembled frame after the deploy and reported that
   everything is good, reported by the owner; which screens were looked at was
   not detailed.

## Not done or not verified

- Nothing was measured by the assistant on the assembled frame.
- The local macOS test run shows font-related golden failures that are identical
  on main; the Linux CI is the proof for the unchanged 13.3 inch images.
