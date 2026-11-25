# Quick 261125-gen: real generic silhouettes

The owner delivered 18 AI-generated generic aircraft silhouettes (transparent RGBA PNG, nose left,
neutral white livery with slate tail). They replace the placeholder copies of the same names in
`server/assets/icons/illustrations/`.

## Tasks
1. Copy the 18 PNGs by name over the placeholders (a220, a300, a380, b747, b757, b767, b777, b787,
   bizjet, bizjetlarge, crj, erj145, falcon, gahigh, helicopter, kingair, other, pc12).
2. `server/plane/illustrations.py --validate --strict-targets` passes; no image is edited.
3. `server/assets/icons/illustrations/VENDOR.md`: real per-file provenance (sha256, dimensions).
4. Note the replacement in `.planning/quick/261124-fam-aircraft-families/SUMMARY.md`.
5. Run the illustration, companion airline, render baseline and structure tests.
