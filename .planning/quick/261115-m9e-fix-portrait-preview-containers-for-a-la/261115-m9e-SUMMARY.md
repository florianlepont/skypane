---
quick_id: 261115-m9e
status: complete
commits: [8f723aa4, 4bf6b22f, 448f9c76, 192ea08f]
---

# Quick task 261115-m9e: picture containers follow the frame's shape

## Root cause

The pictures already followed the frame's profile (800x480 renders), but the CSS boxes around them
hard-coded the portrait shape: `aspect-ratio: 3 / 4` on `.look-frame__image`, `.look-pick__preview`,
`.preview-frame__image` and `.preview-empty`, fixed 48x64 and 44x58 boxes for `.special-row__image` and
`.layout-card__thumb`, and the Home picture markup carried `width="600" height="800"`. `object-fit:
contain` then letterboxed the landscape picture inside a portrait box (grey bands, portrait bezel).

## Change

- `companion/device_scope.py`: `frame_shape_attr(profile)` and `current_frame_shape_attr()` return
  ` data-frame-shape="landscape"` when the profile's width exceeds its height, and nothing otherwise
  (driven by the profile's dimensions, not a hard-coded type).
- Markup carries the attribute: `settings/theme.py` (look picture on Departures/Arrivals, pairing-card
  noscript pictures), `settings/layout_picker.py` (layout tiles and layout card thumbnail),
  `settings/calendar.py` (special looks row picture), `pages/home_page.py` (Home picture and empty state;
  the picture's width/height attributes follow the profile for a landscape frame).
- CSS (`style.css`, `style-home.css`, `style-display.css`): `[data-frame-shape="landscape"]` rules use
  `aspect-ratio: 5 / 3` for the Home picture, the empty state, the look picture (its bezel wraps it, so
  it follows) and the picker tiles; the special-row picture is 80x48 and the phone layout thumbnail 72x43.
  The `3 / 4` rules are unchanged.
- Portrait frames emit exactly the same markup as before (no attribute), except the Home picture now
  writes its width/height through the same `600`/`800` values.

## Containers

Changed (landscape frames only): Home picture and empty state, Departures and Arrivals look picture and
bezel, layout picker tiles, layout card thumbnail (phone), pairing tiles, Special looks row picture.

Still portrait on purpose: `.frame-row__pic` (frame menu glyph, 28x38), `.account-frame__pic` (Account
glyph, 40x52) and the splash frame. They are generic frame pictograms, not previews of the frame's
picture. The theme chip (`theme_preview` chip, 8:3 crop) is no longer used by any companion page, so it
needed no change. The calendar look page uses the same `look-pick__preview` / look picture classes and
is covered by the same rules; it is not separately measured.

## Tests

- New `companion/test_browser_frame_preview_shape.py` (136 cases): the 800x480 frame and the live frame,
  default and classic layouts, Home / Departures / Arrivals / Special looks, phone and desktop, English
  and French, light and dark, plus the Home empty state. It asserts the container is wider than tall (or
  taller than wide for the live frame) and the picture's box matches its natural ratio (no bands).
- Before the fix: 52 failed (all landscape), 52 passed (all live frame) on the first 104 cases; after
  adding the Special looks row, those 16 cases also failed with the row rule removed. After: 136 passed.
- Full non-browser companion suite: 6997 passed, 3 skipped (root permission tests), 1 failed before the
  baseline refresh (`test_render_baseline`), 2 passed after.
- Every browser file whose source mentions previews, tiles, the frame page, themes, the layout picker or Home
  (about 50 files, 2267
  tests, `-n0 --no-cov`): all passed.
- ruff, mypy, function-size gate (1118 functions, none over 80) and comment-history guard are clean.

## Baseline and goldens

The stylesheet hash changed, so `companion/testdata/render_baseline.json` was regenerated. With every
`?v=<12 hex>` normalised the old and new files are identical: only the stylesheet version hash differs
(31 distinct hashes before and after, 68 lines). No theme preview golden changed (no code path that
renders the pictures was touched).
