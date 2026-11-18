# Phase 68 Plan 18 Fix: Remove SKYPANE word from the retired screen

Only the retired screen carried the word "SKYPANE" under the power icon (label
in `server/plane/render/giant/status.py`). The label is now empty and not drawn;
the icon stays. Other status screens keep their own labels (WATCHING, SLEEPING,
SWITCHED OFF, CHARGE ME, OFFLINE, INSTALLING, PAIRING CODE), none of which is
the SKYPANE word, so they are unchanged (verified byte-identical before/after).

## Goldens
- Changed (status-specific only): `status_retired_portrait` / `status_retired_landscape`
  in `giant_render_baseline.json`; `RETIRED_GOLDEN_SHA256` and
  `RETIRED_LANDSCAPE_GOLDEN_SHA256` in `test_pairing_image.py`.
- Unchanged: legacy flight render goldens, `render_baseline.json`, pairing golden,
  `stub-server/test_phase47_freeze.py` (green).
- `RETIRED_SCREEN_REVISION` 2 -> 3 so cached `retired-r3.bin` is regenerated.
  Pairing panels are not revision-cached (rendered per issue), so no bump.

## Layout
Icon top 120 / giants at 380 (portrait); the removed label leaves the same
icon-to-headline gap used by calm screens without a label; nothing off-centre.

## Design-system divergences
None
