---
quick_id: 261115-qy5
status: complete
---

# Quick 261115-qy5: shorter landscape source-fault caption

The landscape top-right source-fault badge now reads "Check the companion page" (new
`LANDSCAPE_SOURCE_FAULT_TEXT` in `server/plane/render/landscape_card.py`). `style.SOURCE_FAULT_TEXT`
is unchanged, so portrait and legacy renders and goldens are untouched.

Tests: `server/test_giant_status_marks_landscape.py` measures the short caption, asserts the badge is
narrower than the long text, and spies the drawn caption string.

Verification: full suite 15740 passed, 8 skipped (root permission skips); ruff, mypy, function-size
(1120 scanned) and comment-history gates pass.

PNGs: /tmp/claude-0/-home-user-skypane/5f9e9599-d097-5503-9fb4-dbc6712aa735/scratchpad/marks-after2/

Concern: on the dithered (non-flat) dark screens the small caption text is hard to read in the PNG
preview (thin serif glyphs over a dither pattern).
