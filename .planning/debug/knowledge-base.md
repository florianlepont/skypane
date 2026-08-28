# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at
the start of new investigations. A match here is a hypothesis candidate to test first,
never a confirmed diagnosis.

---

## illustration-crop-text-margin — aircraft-to-text gap and centering varied per airline illustration
- **Date:** 2026-08-28
- **Error patterns:** margin, gap, spacing, varies per file, illustration, alpha, transparent padding, getbbox, bbox, crop, centering, alignment, layout drift, render, e-ink panel, no error message, visual only
- **Root cause:** Layout anchored to the illustration's full source rectangle while the renderer hard-thresholds alpha at `> 127` before `paste()`. Every vendored PNG carries a soft drop-shadow band (alpha 1..127) that is therefore never painted, so the rectangle's edges sit 37-174px (bottom) / 3-32px (sides) away from the aircraft's real visible edges, by a per-file amount. The design constant had been "verified" with `Image.getbbox()`, which counts the sub-threshold shadow as content — and the two files checked at design time both happened to report a naive bottom padding of exactly 0.
- **Fix:** `draw_illustration()` returns an `IllustrationPlacement` carrying both `.rect` (full placement, for containment guards and stable sizing) and `.content` (the tight bbox of pixels actually painted, measured with the same named threshold the paste uses). All *position* anchors read `.content`: both text blocks' vertical gaps, the main illustration's horizontal centering, and the previous card's right-alignment and vertical centering. Gap/centre constants were re-derived from the developer-confirmed reference render so the approved look was reproduced rather than redesigned. *Sizing* deliberately still reads `.rect`, to avoid making one card's size depend on another file's padding.
- **Files changed:** server/plane/render.py, server/test_render.py, .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md, server/assets/icons/illustrations/HANDOFF.md
- **Transferable lesson:** When code both *measures* and *renders* an asset, make the two share one named threshold/expression. A "verified" measurement that used a different predicate than the renderer is indistinguishable from a correct one until something drifts. Also: a spot-check on one or two files was recorded as a fact about all files — the wording ("this specific illustration file") was the tell.
---
