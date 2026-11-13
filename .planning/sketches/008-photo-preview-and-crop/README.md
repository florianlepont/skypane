---
sketch: 008
name: photo-preview-and-crop
question: "How does a person choose crop-to-fill or bands, move the crop, and judge the 6-colour dithered result for the portrait and landscape panels?"
winner: null
tags: [photos, crop, preview, dithering, accessibility, mobile, desktop, i18n, v1.3]
---

# Sketch 008: Photo preview and crop

## Design Question
One stored photo serves a 1200x1600 portrait panel and an 800x480 landscape panel. The person picks fit (`fill` = crop to fill, `bands` = whole photo with white bands), moves the crop (`pos_x`, `pos_y` in 0..1) and sees the dithered result before saving. How should preview and controls be arranged, and how do we say honestly that only six colours exist?

## How to View
open .planning/sketches/008-photo-preview-and-crop/index.html

Params: `?v=a|b|c&fit=fill|bands&px=0.2&py=0.8&panel=portrait|landscape&show=frame|photo&lang=fr&theme=dark&chrome=0`.

The picture is a procedural scene drawn in code (no photo, nothing external). The preview approximates the server pipeline in the browser: crop or fit, auto-contrast (1 % cutoff, strength 0.8), saturation 1.2 (the `DEFAULT_PREP` values of `docs/PHOTO-RENDERING.md`), then Floyd-Steinberg against the real Spectra 6 palette. It is not byte-identical to the server render.

## Variants
- **A: Preview first** — one big dithered preview with a Portrait / Landscape switch; controls beside it on desktop (sticky preview), below on a phone. Drag the picture, use arrow keys (Shift = bigger steps), or the two sliders. The slider for the axis with no slack on the shown panel is disabled with a reason.
- **B: Both screens** — portrait and landscape previews side by side, always visible; sliders plus a 3x3 arrow pad for precise nudging and a centre button; fit and preview-mode controls next to it.
- **C: Source view** — the whole photo with the two crop windows drawn on it (solid = portrait, dashed = landscape), dragged as one; small dithered previews of both panels below. Shows why one position serves two shapes (portrait only slides sideways, landscape only up and down).

## Common
- Fit segmented control (Fill the screen / Whole photo). In bands mode the position controls are disabled and explained.
- Preview toggle "Frame look / Original photo" and an "Actual pixels" zoom (A) to see the dots.
- Honest card "Only six colours" with the six real inks, and a line that the preview is close but not identical.
- Floating Cancel / Save bar appears on change; Save shows a success toast.
- Keyboard: preview surfaces are focusable and take arrow keys; sliders and pad buttons have names; targets are 44 px.

## What to Look For
- Does the dithered preview read as "this is what the frame will do" or does it scare the person?
- Is dragging discoverable on a phone, and are the sliders enough as a fallback?
- Is seeing both panels at once (B, C) clearer than switching (A), given a frame has only one panel?
- Is C's source view understandable, or too abstract?
- Open: render the preview on the server (exact) or in the browser (instant, approximate).
