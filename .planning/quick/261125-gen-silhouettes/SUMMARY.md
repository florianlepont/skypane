# Quick 261125-gen: summary

The 18 placeholder generics from quick 261124-fam are replaced by the owner's real silhouettes, used
exactly as delivered (no pixel changes).

- Files: 18 PNGs, 575 KB to 1 MB each (all under 1.5 MB, no recompression).
- `--validate --strict-targets`: all PASS, 0 outstanding targets.
- `VENDOR.md` rows carry the real sha256 and pixel dimensions.
- `companion/testdata/render_baseline.json` needed no regeneration (test_render_baseline passes).

## Helicopter in the giant layout
The helicopter's rotor and skids make both halves tall, so in the giant layout the nose and rear halves
overlapped vertically while sharing columns (`test_halves_have_the_validated_extent_for_every_illustration`).
The owner ruled out retouching, and transparent padding cannot help because the layout crops to the painted
pixels. Fix: `aircraft.halves_for` shrinks both planes together (3 % steps) only while the halves'
rectangles overlap; art that already clears keeps its size, so no other picture and no render baseline
changed. The test's half builder now goes through the same function; its assertions are unchanged.
