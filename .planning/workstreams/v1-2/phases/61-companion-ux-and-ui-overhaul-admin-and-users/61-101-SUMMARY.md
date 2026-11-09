# Phase 61 Plan 101: Owner round 13 Summary

Quiet Home rename pencil (W166), padded Fleet State card with actions under the title (W165), and a tight focus ring on the quiet-hours link that no longer appears after a pointer-closed dialog (W167).

## What changed

- **W166** `companion/static/style.css`: `.title-action` now uses a `--title-size` variable (48/28/24px). The rename pencil is a 20px glyph (18px under 380px) in the muted text colour with no disc or border at rest and a light halo on hover/focus. The 44x44 hit area stays, centred on the title's first line (calc margin), above the pill (z-index) so the hit reach stays 44. Catalogue entry updated; /components picks up the new look through the shared CSS.
- **W165** same file: the compact empty state in a flush Fleet section card gets the standard 16px inner padding (it was 0, so text sat on the card edge and was clipped by the card's rounded overflow). `.fleet-detail-head` actions are left-aligned directly under the title instead of a floating right-aligned row. Checked State, Settings, Access, Device/Versions and System at 1280 and 360, both themes, EN/FR: no other flush text found.
- **W167** the quiet-hours window link (and the timezone-note link) had a 44px box made of padding plus negative margin, so the 2px ring with 2px offset wrapped a 44px-tall pill. The box is now the text and the 44px target is a `::after`; the ring hugs the text. `modal.js` returns focus after a dialog closes with `focus({focusVisible:false})` unless the last input was the keyboard (Escape/Enter keep the ring).
- Tests: the old bounding-box 44px checks on that link became hit-reach checks (quiet-hours modal probe, Home state card). New: geometry of the pencil (glyph size, hit >= 44, first-line alignment, no overlap, no disc, hover halo), Fleet text inset (>= 16px) on every tab plus System, actions aligned under the title, ring tight for keyboard and absent after a pointer close.
- Render baseline regenerated.

## Deviations / notes

- Header actions are directly under the title (allowed alternative), not on the title row: the frame picker is absolutely positioned at the right of that row.
- Info-tip button (44px circle around an 18px glyph) has the same large-ring shape; not changed (out of the reported scope).
- Screenshots: scratchpad/shots101/ (before/after Fleet at 1280/360, light/dark, FR; System before). Home hero after-screenshots not taken; geometry is asserted by tests.

## Known Stubs

None.
