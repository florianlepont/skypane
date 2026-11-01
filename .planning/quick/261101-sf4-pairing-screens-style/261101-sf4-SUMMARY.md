---
phase: quick-261101-sf4
plan: 01
status: complete
requirements: [AUTH-04]
key-files:
  modified:
    - server/pairing_image.py
    - server/test_pairing_image.py
    - server/plane/render/glyphs.py
    - server/plane/render/hold_screens.py
    - server/plane/render/style.py
---

# Quick 261101-sf4: pairing and retired screens in the status-screen style

The pairing and retired e-ink screens now use the shared hold composition (glyph, tracked PT Serif Bold label, short rule, text), English only, with no red band, French block or Inter font.

## Tasks

1. Chain-link glyph and both screens: commit 5a0d8e73
   - `glyphs.draw_link_icon` (two interlocking rounded loops, 76 px band).
   - `_build_hold_canvas` gained an optional `code_text` line (PT Serif Bold 150 px, 14 px tracking, stepped down by 8 to a floor of 110 to fit the safe box); constants live in `style.py`. Other hold screens are unchanged (full suite and goldens green).
   - `pairing_image` renders the reference canvas, then scales (nearest neighbour) and centres it on a matching field for non-reference profiles.
2. Tests and golden hashes: commit fcb49f2a

## Deviations from Plan

The code-line helper functions were extracted in `hold_screens.py` to keep `_build_hold_canvas` under the 80-line gate. Retired-screen spacing differs from the mock-up by about 4 px (rule and body positions) because it uses the stock dimmed composition unchanged.

## Results

- ruff, mypy, comment-history and function-size gates clean.
- Full non-browser suite: 7420 passed, 8 skipped.
- Non-root run: 407 passed, 4 skipped.
- `companion/test_browser_console.py`: 23 passed.

## Golden hashes (legacy profile, code ABCD2345)

- pairing: 3e5d41f52f68dc506fa4f3e983b597f9382d2c183e8e9bdd47c93a8d55ba7ba0
- retired: 315a0852353acdd9849c6cfd1e2fbffe6bbfc792a9df53907e3868a0c5290c05

## Self-Check: PASSED
