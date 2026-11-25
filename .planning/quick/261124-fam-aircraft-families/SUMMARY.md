# Quick 261124-fam: summary

Result: 17 new families (erj145, b787, a220, b777, b747, b767, b757, a380, a300, crj, falcon,
bizjetlarge, bizjet, kingair, pc12, helicopter, gahigh) plus the catch-all `other` slot; 25 slugs in
`SHAPE_SLUGS`. Every code of FAMILIES.md maps to its family (`_FAMILY_CODES`); the 43 production
codes all have a family slot.

## Behaviour
- `illustrations.slot_slug(code)`: family/variant slot, else `other` for any non-empty designator.
  The editor's type rows upload to it, so every type row has an upload control. Unmapped codes are
  one row "Other"/"Autre" per airline (designators seen listed after it, family name in the cell title).
- `select_illustration`: an unmapped type uses `{airline}-other.png`, then the airline default
  picture, then `generic-other.png`, then the universal fallback; a missing type never uses `other`.
- `classify_aircraft_type` / `type_slug` stay strict (None for unmapped), so `same_type` does not
  merge unrelated unmapped codes in the default-type logic.
- Curated legacy labels that are no ICAO code (A330, A350, ATR72, B1900D, B747, B777, B787, EC145)
  resolve to their family (`_LABEL_ALIASES`): the B747/B787/B777/EC145 legacy pictures now count as
  the family's type picture (same row as B744/B788/B77W/EC45 when seen), which is what the row showed
  before for A330/ATR72.
- Slugs are suffix-unambiguous (`airline_key_of_artwork`); a test checks no built-in airline key ends
  in a slug.

## Data effects
- BE9L appears only in `illustrations.py`, `render/text.py` and `server/test_illustrations.py`: no
  fixture or test uses it with a picture. Moving it to `kingair` can orphan a picture only if an owner
  uploaded `{airline}-beechcraft1900d.png` for a BE9L-only airline in production; not checkable from
  the repo. Such a file stays on disk and still serves B190 / the "B1900D" row; nothing is deleted.
- Amelia's curated E145 picture was `amelia-embraer.png`; E145 now has its own slot, so the file was
  renamed `amelia-erj145.png` (git mv) and its target/label entry became `("Amelia", "erj145")`.
  A production override uploaded as `amelia-embraer.png` would stay in the E-Jet slot.
- Stored default types and uploads keyed by existing slots are unchanged.
- E135/E145 pictures previously drawn with the `embraer` slot now use `erj145`: an airline with an
  uploaded `{airline}-embraer.png` falls back to its default picture for E145 until it uploads there.

## Placeholder generics (replace by dropping a file of the same name; no code change)

Update 2026-11-25: all 18 placeholders below were replaced by real generic silhouettes (see `.planning/quick/261125-gen-silhouettes/SUMMARY.md`); the list is kept as originally written.
- `generic-erj145.png`  (copy of `generic-embraer.png`)
- `generic-b787.png`  (copy of `generic-a350.png`)
- `generic-a220.png`  (copy of `generic-a320.png`)
- `generic-b777.png`  (copy of `generic-a350.png`)
- `generic-b747.png`  (copy of `generic-a330.png`)
- `generic-b767.png`  (copy of `generic-a330.png`)
- `generic-b757.png`  (copy of `generic-b737.png`)
- `generic-a380.png`  (copy of `generic-a330.png`)
- `generic-a300.png`  (copy of `generic-a330.png`)
- `generic-crj.png`  (copy of `generic-embraer.png`)
- `generic-falcon.png`  (copy of `generic-embraer.png`)
- `generic-bizjetlarge.png`  (copy of `generic-embraer.png`)
- `generic-bizjet.png`  (copy of `generic-embraer.png`)
- `generic-kingair.png`  (copy of `generic-atr72.png`)
- `generic-pc12.png`  (copy of `generic-atr72.png`)
- `generic-helicopter.png`  (copy of `generic-fallback.png`)
- `generic-gahigh.png`  (copy of `generic-atr72.png`)
- `generic-other.png`  (copy of `generic-fallback.png`)

Also listed in `server/assets/icons/illustrations/VENDOR.md`.

## Verification
ruff, mypy, function-size gate, comment-history guard: clean; `companion/app.py` 1443 lines.
`pytest server` plus the airline/illustration companion tests, test_companion_app_04,
test_stylesheet_structure, test_i18n*, test_suite_guards, test_render_baseline: all pass (one browser
test failed once under load and passed alone). `render_baseline.json` regenerated: unchanged.
