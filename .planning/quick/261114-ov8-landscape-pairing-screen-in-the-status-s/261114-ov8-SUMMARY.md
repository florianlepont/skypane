---
quick_id: 261114-ov8
status: complete
---
# Summary

- `server/plane/render/giant/status.py`: `build_pairing(size, code, flat=False)` (label PAIRING CODE, lead word PAIR, the code as the second giant line, the two instruction lines bottom-left, dithered dark field with white ink). `build_status` still refuses "pairing".
- `server/plane/render/giant/icons.py`: a "pairing" glyph (the existing link icon, sized by its loop height so the mask matches the other status icons).
- `server/pairing_image.py`: a landscape profile gets the new composition; a portrait profile is byte-identical (the pinned golden hash for the legacy profile still passes).
- The earlier decision that the calm status restyle must not touch the pairing screen is kept for portrait (the live frame) and lifted for landscape on the owner's request.
- Existing test that asserted the scaled composition for the simulated landscape profile is replaced by tests of the new one. 4310 tests pass, including the freeze tests of the live frame; ruff, mypy, the function-size gate and the comment-history guard pass.
- The code line is height-limited, not width-limited: it spans about half the width, and the instruction lines are wider than it. On glass the code is about 8 mm tall at 7.3 inches; the owner judges it on the real panel.
