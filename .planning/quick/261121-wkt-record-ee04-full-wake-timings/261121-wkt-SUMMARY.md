---
quick_id: 261121-wkt
date: 2026-11-21
status: complete
---

# Quick 261121-wkt: EE04 full-wake timings and item 7 decision

From the frame's battery-history export (fw-v1.2.1, 2026-11-18 09:00 UTC to 2026-11-21
07:20 UTC, 1752 wakes, 387 redraws): draw 31.185 / 31.195 / 59.213 s and whole wake with a
redraw 32.406 / 33.436 / 61.604 s (min / median / max). The maximum is far below the 190 s
blit stage and the 700 s wake budget; limits and firmware are unchanged. One 59.213 s draw
(2026-11-18 12:12:47 UTC, cause unknown, not investigated) is an observation close to the
60 s `BUSY_TIMEOUT_MS`. `FP_MIN_REFRESH_SPACING_S` is still not set.

Item 7 (ADC enable pin, GPIO6): owner decision of 2026-11-21 to keep indirect evidence only;
recorded as a decision, not a measurement; row 7 has no `measured` status.

Criterion 7 stays OPEN: battery levels 2 and 3 of item 6, discharge profile, currents,
`FP_MIN_REFRESH_SPACING_S` and the 59.2 s draw remain.

Files: `hardware/SECOND-HARDWARE-MEASUREMENTS.md`, `64-VERIFICATION.md` (criterion 7, open
points 2 and 3). Docs only.
