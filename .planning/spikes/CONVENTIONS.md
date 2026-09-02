# Spike Conventions

Patterns and stack choices established across spike sessions on the
SkyPane e-ink panel renderer. New spikes follow these unless the
question requires otherwise.

## Stack

- **Python + Pillow (PIL)**, matching the real production renderer
  (`server/plane/render.py`) exactly — no separate spike-only rendering
  stack. Run via `server/.venv/bin/python3`, the project's own venv.
- Spike scripts live in `.planning/spikes/NNN-name/`, output PNGs to a
  `renders/` subdirectory inside that same spike directory.

## Structure

- One `README.md` per spike (or per closely-related pair sharing one
  directory — see spike 002) with YAML frontmatter (`spike`, `name`,
  `type`, `validates`, `verdict`, `related`, `tags`), a `## Research`
  section citing any git-history prior art found, an
  `## Investigation Trail`, and a `## Results` section recording the
  developer's own words, not a paraphrase.
- Comparison renders that need a side-by-side view get a stitched
  `contact_sheet*.png` (labelled rows/columns) rather than making the
  developer flip between many separate files one at a time.

## Patterns

- **Never edit `server/plane/render.py` (or any production file) during
  a spike.** Explore by monkeypatching the real module's functions
  (`render.draw_top_labels`, `render._font`, `dither.dithered_state_background`,
  etc.) for the duration of a throwaway script, then restoring the
  original in a `finally` block. This lets a spike call the real
  `render.build_canvas()` pipeline — so every element the spike isn't
  actively testing (illustration, other text roles, layout) is
  pixel-faithful to production — while the one thing under test is
  swapped out. Production code changes happen only in the plan that
  follows a VALIDATED spike, never during the spike itself.
- **Check git history for prior art before building anything new.**
  `git log -S"<distinctive string>" -- server/plane/render.py` has twice
  now surfaced a working, previously-shipped implementation that was
  removed for reasons unrelated to whether it worked (a layout redesign,
  not a legibility failure) — reuse it rather than reinventing. Note
  explicitly whether the resurrected technique was ever verified on real
  Spectra 6 glass; assume not unless `hardware/BRINGUP-LOG.md` says so.
- **On-glass verification is required before any spike finding ships**,
  regardless of how confident a screen-preview comparison looks — this
  project's own history (Phase 7, Phase 8) has repeatedly overturned
  monitor-only judgments on real ink. Every spike's Results section
  should say plainly that this is still open.
- **A spike question can come back negative, and that's a valid,
  useful result** — record it as an invalidated hypothesis with the
  developer's own reaction, not as an incomplete investigation. Not
  every "what if X" needs to become a code change.

## Tools & Libraries

- `PIL.Image`/`PIL.ImageDraw`/`PIL.ImageFont` — no other imaging
  library. Pillow has no native small-caps or letter-spacing/tracking
  support for TrueType rendering; both are hand-rolled (see
  `draw_tracked_text()`/`_tracked_text_width()` in spike 002, resurrected
  from git history rather than written fresh).
