# Phase 64: owner walk-through of a second-type frame (criterion 9, plus the visual checks of criterion 6)

Frame: the EE04 (`seeed-ee04-7in3-spectra6`, 800x480) enrolled and paired in production,
MAC 84:c7:bb:70:b2:7c. Companion: the deployed production companion.

Rules: a cell holds `pass`, `fail` or `open` and comes only from the owner's own report. A
failure becomes a gap item in "Gaps found", not a silent edit. Battery percentages are
provisional: no battery value was measured (Phase 58 closed without a valid discharge sample),
so the percentage uses a profile copied from the live frame and only the mechanics are checked.

Columns: A = administrator, U = invited user (non-admin owner or co-manager); EN = English UI,
FR = French UI. FR cells also check strings, accents and clipped text on the second-type pages.

| # | Step | Expected result | A EN | A FR | U EN | U FR | Notes |
|---|------|-----------------|------|------|------|------|-------|
| 1 | Pair | The code on the panel is accepted, the frame appears under the chosen owner | pass (language not stated) | open | n/a | n/a | Done 2026-11-15 by the owner: registered with `fleet_cli register-pending`, then paired with the panel code. Language not stated |
| 2 | Assign | The frame can be assigned to another owner, and its page follows | open | pass | n/a | n/a | Owner-reported 2026-11-15: done in French as administrator |
| 3 | Change the layout | The layout picker and its previews have the frame's landscape shape; the saved layout shows on the panel | open | pass | open | open | Owner-reported 2026-11-15: done in French as administrator |
| 4 | Display on or off | Off: the panel shows the off screen at its next wake; on: it draws again | open | pass (off screen) | open | open | Owner-reported 2026-11-15: in French as administrator, the off screen shows on the panel after switching off; switched back on, the redraw at the next wake was not yet reported |
| 5 | Quiet hours | Saved hours take effect; the hold screen shows | open | pass | open | open | Owner-reported 2026-11-15: done in French as administrator and in the personal view of the owner's own frame (the owner is also its administrator; this is not the invited-user case, which needs a non-admin account) |
| 6 | Detection mode | The chosen mode saves and the next image follows it | open | pass | open | open | Owner-reported 2026-11-15: "détection: fait" in French as administrator; the mode chosen and the image that followed were not described |
| 7 | Health | Connection, battery and flight data rows show the frame's own state | open | pass | open | open | Owner-reported 2026-11-15: "santé et batterie: fait" in French as administrator; the screenshots seen earlier showed connection, battery and flight data rows in a normal state for the second-type frame |
| 8 | Battery | A percentage and a voltage show; the percentage uses the frame's own curve | open | pass | open | open | Provisional values. Owner-reported 2026-11-15 in French as administrator; an earlier screenshot showed 99 % and 4106 mV with "probablement en charge" while plugged in |
| 9 | Schedule an update | The Update card lists this frame's own releases only (no other type tab) and installs | pass (language not stated) | open | n/a | n/a | Done 2026-11-15: fw-v1.2.1 installed, see `64-OWNER-VALIDATION.md` section C |
| 10 | Retire | The frame shows the retired image and leaves the active list | open | open | n/a | n/a | |
| 11 | Re-activate | The frame is wiped of its previous owner's data and shows a new code | open | open | n/a | n/a | |
| 12 | Theme and frame previews | Previews have the frame's shape and the landscape chip crop (the crop is a design choice to be confirmed by eye) | open | open | open | open | Owner to confirm the crop |
| 13 | Landscape hold marks | The classic layout's landscape hold screens carry the battery-low and the source-fault marks | open | open | open | open | Needs a frame at a low battery or a source fault, or the preview |
| 14 | Sign-in and console percentages | The account page and the console rows show the battery percentage of the frame's own curve | open | open | open | open | Provisional values |

## Gaps found

(To be listed from the owner's reports.)
