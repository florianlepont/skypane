# Quick 261125-gen: summary

The 18 placeholder generics from quick 261124-fam are replaced by the owner's real silhouettes, used
exactly as delivered (no pixel changes).

- Files: 18 PNGs, 575 KB to 1 MB each (all under 1.5 MB, no recompression).
- `--validate --strict-targets`: all PASS, 0 outstanding targets.
- `VENDOR.md` rows carry the real sha256 and pixel dimensions.
- `companion/testdata/render_baseline.json` needed no regeneration (test_render_baseline passes).

## Open finding
`server/test_giant_aircraft.py::test_halves_have_the_validated_extent_for_every_illustration[generic-helicopter.png]`
fails: the painted helicopter (rotor and skids) is 2.8:1 versus about 3:1 for the other generics, so in
the giant layout the nose and rear halves overlap vertically while sharing columns. Needs a layout
decision (helicopter cut/scale) or a redrawn, flatter helicopter; not fixed here.
