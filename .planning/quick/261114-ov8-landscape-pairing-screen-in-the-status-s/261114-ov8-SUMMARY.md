---
quick_id: 261114-ov8
status: complete
---
# Summary

- `server/plane/render/giant/status.py`: `build_pairing(size, code, flat=False)` (label PAIRING CODE, lead word PAIR, the code as the second giant line, the two instruction lines bottom-left, dithered dark field with white ink). `build_status` still refuses "pairing".
- `server/plane/render/giant/icons.py`: a "pairing" glyph (the existing link icon, sized by its loop height so the mask matches the other status icons).
- `server/pairing_image.py`: every profile gets the new composition at its own size, portrait (13.3 inch, 1200x1600) and landscape (7.3 inch, 800x480) alike; the old serif hold composition and its scaling are gone.
- The earlier decision that the calm status restyle must not touch the pairing screen is lifted on the owner's request. The pinned golden hash of the legacy profile's pairing screen is re-pinned on purpose; the retired screen's hash is unchanged.
- The tests that asserted the old structure are replaced by tests of the new composition at both sizes, including the widest possible code in the margins.
- Audit of every status screen as served (default layout) at 1200x1600 and 800x480: watching, quiet hours, display off, battery empty, retired and the two firmware screens (no connection, updating) already follow the charter; pairing was the only outlier. Regenerating the four firmware masks from the server renderer leaves the committed headers unchanged. A frame whose owner chose the classic layout keeps the legacy hold screens by design. 4310 tests pass, including the freeze tests of the live frame; ruff, mypy, the function-size gate and the comment-history guard pass.
- The code line is height-limited, not width-limited: it spans about half the width, and the instruction lines are wider than it. On glass the code is about 8 mm tall at 7.3 inches; the owner judges it on the real panel.
