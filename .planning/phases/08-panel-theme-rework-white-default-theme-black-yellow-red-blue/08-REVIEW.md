---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
reviewed: 2026-08-31T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - companion/test_config_page.py
  - hardware/BRINGUP-LOG.md
  - server/assets/fonts/VENDOR.md
  - server/device_config.py
  - server/plane/enrich.py
  - server/plane/render.py
  - server/test_config_history.py
  - server/test_enrich.py
  - server/test_pipeline_e2e.py
  - server/test_poll_loop.py
  - server/test_render.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-08-31T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 8 widens `server/device_config.py`'s `THEMES` registry to 11 entries, decouples PT Serif font weight and background dithering into per-theme registry fields, rewrites the flight-identifier line as a four-tier content ladder, and removes the text-backing-plate mechanism. The production code (`device_config.py`, `enrich.py`, `render.py`) is generally careful: every registry-lookup boundary is guarded by an explicit membership test before use, `save_device_config()` validates-before-write with a correct tmp-write-then-`os.replace()` idiom, and `enrich.py`'s cache/registry-bounding functions (`trim_cache`/`trim_unresolved_prefixes`) are actually wired into the poll loop, not dead code. The large test suite (`test_render.py`, `test_poll_loop.py`, `test_enrich.py`, `companion/test_config_page.py`) closely tracks the production contracts it exercises, including a registry-driven per-theme weight/dithered check that would catch most drift.

That per-theme weight check, however, has a blind spot: it never exercises `draw_source_fault_badge()`, and that function turns out to bypass the phase's own weight-resolution contract entirely (see WR-01). A second, independently-discovered rendering bug affects the same function's exclamation-mark glyph (WR-02). Neither is exercised by the existing 99-check `test_render.py` suite, which is why both survived to this review despite the suite's density elsewhere.

One file in the review scope, `hardware/BRINGUP-LOG.md`, could not be read for its own content beyond what is quoted below — see IN-02.

## Warnings

### WR-01: Source-fault badge caption ignores the theme's declared font weight

**File:** `server/plane/render.py:525`
**Issue:** Every other active-state text role in this phase was deliberately rewritten to resolve its PT Serif weight from the active theme via `_role_font()`/`_role_fit_text_size()` (see the module's own comments at lines 409-445 and the `weight` parameter threaded through `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()`). `draw_source_fault_badge()` was not updated to match: it calls `_font(TOP_TAG_FONT)` directly (line 525), which always resolves to `PT_SERIF_BOLD` regardless of `theme_id`, and the function's signature (`draw_source_fault_badge(canvas, ink_idx)`) doesn't even accept a `weight` argument to thread through.

This directly contradicts the phase's own on-glass finding recorded in `hardware/BRINGUP-LOG.md` ("Step B"): uniform Bold read "très agressif" on real ink, "most visible on the White default" — which is exactly the theme (the new `DEFAULT_THEME_ID = "white"`) under which the source-fault badge will now unconditionally render Bold. Because White's declared weight is `"regular"` (`device_config.THEMES["white"]["weight"]`), the badge's caption is the one piece of active-state text left contradicting the theme's own declared weight — on the default theme, in production.

This is untested: `server/test_render.py`'s `_spy_requested_font_paths()` / `_every_theme_uses_only_its_declared_weight()` checks (lines 777-841) call `render.build_canvas(..., theme_id=theme_id)` without `source_fault=True`, so `draw_source_fault_badge()` is never invoked inside that spy and the weight mismatch is never observed by the suite. Confirmed by reading the badge's only two call sites (`_build_empty_canvas` and `_build_active_canvas`), neither of which passes anything to override the hardcoded path.

**Fix:**
```python
def draw_source_fault_badge(canvas, ink_idx, weight="bold"):
    ...
    caption_font = _role_font(TOP_TAG_FONT, weight)
```
and thread the active theme's `weight` through from both call sites (`_build_empty_canvas` can keep passing `"bold"` explicitly since the empty state is deliberately not theme-dependent; `_build_active_canvas` should pass the `weight` it already computed at line 1380).

### WR-02: Source-fault badge's exclamation-mark dot is drawn as a single pixel, not a visible dot

**File:** `server/plane/render.py:564-567`
**Issue:** The exclamation mark's dot is drawn with:
```python
draw.line(
    [(stroke_x, top + glyph_size * 0.8), (stroke_x, top + glyph_size * 0.8)],
    fill=ink_idx, width=2,
)
```
Both endpoints are identical, i.e. this is a zero-length line. Verified empirically against the project's own Pillow installation: `ImageDraw.line([(25,25),(25,25)], fill=255, width=2)` on a fresh canvas paints exactly **one** pixel (`img.getbbox()` returns a 1x1 box), not a filled 2px-wide dot — Pillow does not expand a degenerate (zero-length) line segment by its `width` the way it does a real multi-pixel line. The result is that the badge's exclamation mark renders as a stroke with an all-but-invisible single-pixel dot underneath it, on a 1200x1600 e-ink panel, rather than the intended small solid dot the code's own visual design implies.

**Fix:** Use an ellipse (or a single `point`-based small filled rectangle) for the dot instead of a degenerate line:
```python
dot_r = 1  # radius in px, tune to taste
dot_y = top + glyph_size * 0.8
draw.ellipse(
    [(stroke_x - dot_r, dot_y - dot_r), (stroke_x + dot_r, dot_y + dot_r)],
    fill=ink_idx,
)
```

## Info

### IN-01: `_illustration_over_pixel_cap()` and `_load_illustration_safely()` open the same file twice on the reject path

**File:** `server/plane/render.py:679-755`
**Issue:** `_illustration_over_pixel_cap(candidate)` (called at line 730) already opens `candidate` with `Image.open()` to read its header and compute `width * height`. When the cap is exceeded, `_load_illustration_safely()`'s error-reporting branch (lines 731-745) opens the *same file* a second time solely to recompute `pixel_count` for the log message. This is out of scope as a performance concern per the review brief, but it is a minor duplication that a future refactor could collapse by having `_illustration_over_pixel_cap()` return the measured pixel count (or `None` on unreadable) instead of a bare bool, avoiding the second `Image.open()` call entirely.

**Fix:** Have the cap-check helper return `(over_cap: bool, pixel_count: int | None)` so the caller never needs to re-open the file to log the count it already computed.

### IN-02: `hardware/BRINGUP-LOG.md`'s Phase 8 summary table implies broader active-state coverage than the code delivers

**File:** `hardware/BRINGUP-LOG.md`
**Issue:** This narrative hardware bring-up log documents genuine on-glass findings (e.g., the Phase 8 "Step B" font-weight correction cited in WR-01 above) that are load-bearing context for judging whether `render.py`'s current state matches what was actually verified on real hardware. Its "Every correction applied in session" table states the font-weight rule as "Per-theme `weight` registry field: Regular on every flat theme, Bold on every dithered theme except Yellow Light" with no scoping caveat — read at face value this implies every piece of active-state text follows the rule, which is true for every draw function except `draw_source_fault_badge()` (WR-01). The log's own prose is accurate about the specific roles it says it tested (`STATE_LABEL_FONT`, `TOP_TAG_FONT` inside `draw_top_labels()`, the main/previous text blocks) — it never claims to have exercised the source-fault badge — but the summary table's wording is broad enough to read as a stronger guarantee than the code actually provides.

**Fix:** None required for this file itself; noted for completeness since it was in the mandatory reading scope. Consider adding a line to the bring-up log's "Open items carried forward" section once WR-01 is fixed and re-verified on glass, since the badge's font weight was never part of the Step B on-glass check.

---

_Reviewed: 2026-08-31T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
