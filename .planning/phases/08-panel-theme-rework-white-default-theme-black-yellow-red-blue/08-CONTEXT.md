# Phase 8: Panel theme rework - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase changes how the e-ink panel (`server/plane/render.py`) looks and
what text it shows, based on an extended interactive spike
(`.planning/spikes/001-panel-theme-colours/`) where the developer reacted to
dozens of real rendered comparisons before locking each decision. It does
NOT touch the companion web app's own light/dark theme (CFG-09, a separate,
unrelated setting) — only the CFG-01 panel-colour picker and the physical
panel's rendering pipeline. In scope: the `THEMES` registry
(`server/device_config.py`), the text-legibility mechanism and font choice
(`server/plane/render.py`), the flight-identifier text content
(`server/plane/enrich.py` + `render.py`), and one previous-flight-card
sizing/alignment fix. A blocking on-glass verification pass closes the
phase — nothing here is done until re-checked on the real Spectra 6 panel,
not just on-screen.

</domain>

<decisions>
## Implementation Decisions

### Theme registry (`server/device_config.py`)

- **D-01:** `THEMES` gains a `"white"` entry and becomes the new
  `DEFAULT_THEME_ID` (currently `"sky"`). `departing_index` =
  `arriving_index` = `IDX_WHITE`, `ink_index` = `IDX_BLACK`. DEPARTING vs.
  ARRIVING is distinguished by the existing label text alone
  ("DEPARTING"/"ARRIVING" + "to"/"from" phrasing) when the background is
  white for both states — same pattern already used and confirmed for the
  existing empty state.
- **D-02:** `THEMES` also gains `"black"`, `"yellow"`, `"red"` entries.
  **Confirmed structure (discuss-phase, not yet in the spike): each is a
  single flat colour, matching the White pattern** —
  `departing_index == arriving_index` == that colour's index
  (`IDX_BLACK`/`IDX_YELLOW`/`IDX_RED`), not a two-tone departing/arriving
  pair like the existing "sky" theme. `ink_index`: black text on
  yellow (`IDX_BLACK`), white text on black/red (`IDX_WHITE`) — same
  contrast logic already used for white-bg/black-ink and
  coloured-bg/white-ink.
- **D-03:** The existing `"sky"` theme (Blue departing / Green arriving)
  is kept unchanged and stays available, no longer the default.
- **D-04 (theme labels, discuss-phase):** Simple descriptive names, not
  evocative ones — `"White"`, `"Black"`, `"Yellow"`, `"Red"`, and rename
  the existing `"sky"` entry's label from `"Sky (default)"` to `"Sky"`
  (it's no longer the default). Matches the plain, literal style already
  used elsewhere in the registry (`RUNWAYS`' labels are equally literal:
  `"Runway 3 (07/25)"`).
- All five theme ids use only real Spectra 6 palette indices
  (`panel_format.IDX_BLACK/WHITE/YELLOW/RED/BLUE/GREEN`) — no arbitrary
  RGB, matching this registry's existing discipline (never write a bare
  palette integer here — always reference `panel_format`'s named `IDX_*`
  constants).

### Text legibility (`server/plane/render.py`)

- **D-05:** `_paint_text_backing()`'s solid backing-plate rectangle is
  removed entirely, for every theme (not just the coloured ones) — no
  replacement box, outline, or shadow. Outline (1/2/3px stroke) and
  drop-shadow were both spiked and explicitly rejected by the developer on
  visual grounds, even though both tested as legible.
- **D-06:** Every text role switches from `PTSerif-Regular.ttf` to the
  already-vendored `PTSerif-Bold.ttf`, universally — this is what actually
  replaces the backing plate's legibility job against the dithered
  background. Confirmed legible at every font size on the panel, including
  the smallest (16px, the previous-flight card's secondary caption)
  without any visual treatment.
- **D-07 (discuss-phase):** `PTSerif-Regular.ttf` is no longer referenced
  by any active render-path code after D-06, but stays vendored,
  unreferenced, in `server/assets/fonts/` — same "retained for
  provenance, marked superseded" treatment `server/assets/fonts/VENDOR.md`
  already gives the Zilla Slab and Inter entries (both replaced in
  earlier phases, both still on disk). Add a "Supersession" note to
  `VENDOR.md`'s `PTSerif-Regular.ttf` / `PTSerif-Bold.ttf` entry mirroring
  the Zilla Slab entry's own Supersession note, rather than deleting the
  file or the VENDOR.md entry.
- Zilla Slab (`ZillaSlab-SemiBold.ttf`/`ZillaSlab-Bold.ttf`, already
  vendored, already inactive) was spiked as an alternative to PT Serif
  Bold and explicitly NOT chosen — developer kept PT Serif for
  typographic consistency with the rest of the panel. No change to Zilla
  Slab's existing vendored-but-unused status.

### Flight-identifier text content (`server/plane/enrich.py` + `render.py`)

- **D-08:** The raw ADS-B ICAO callsign (e.g. `"AFR1234"`, `"TVF16VB"`) is
  never displayed anywhere on the panel again — neither the main card nor
  the previous-flight card, at any fallback tier.
- **D-09:** `adsbdb`'s `callsign_iata` field (e.g. `"AF1234"`) — present
  in every adsbdb route hit (`server/fixtures/adsbdb_hit_*.json` both
  carry it) but currently parsed out and discarded by
  `enrich._parse_route()` — must be threaded through: `_parse_route()`'s
  returned dict, the cache entry written by `lookup_route()`, and
  `_route_from_entry()`'s cache-hit reconstruction. This is a genuine data
  fix: for legacy/full-service carriers (Air France, TAP, etc.) the ICAO
  and IATA callsigns denote the exact same real published flight number
  (`.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md`); for
  rotating-callsign carriers (Transavia et al., ~10% adsbdb hit rate)
  neither form reliably maps to a stable flight number — a structural
  limitation of any callsign-keyed source, not a code gap. A real fix for
  that carrier class would need a live schedule/FIDS API (AeroDataBox,
  never integrated) as a new, separate data source — explicitly out of
  scope for this phase.
- **D-10:** `_flight_line1_text(flight, state, route)` (used by both
  `draw_main_text_block()` and `draw_previous_text_block()`) is rewritten
  to a 4-tier content ladder, poorest-information case last, and must
  never re-introduce the raw callsign at any tier:
  1. IATA id present AND city known → `"{iata_id} to|from {city}"` (e.g.
     `"AF1234 to New York"`).
  2. City known, no IATA id → `"{To|From} {city}"` (e.g. `"To New
     York"`) — no flight identifier shown at all.
  3. Only the airline is known (adsbdb miss, ICAO-prefix `_ICAO_AIRLINE_
     PREFIXES` fallback — `route.get("airline_name")` truthy, no city, no
     IATA id) → **line 1 is omitted entirely.** `draw_main_text_block()`
     and `draw_previous_text_block()` must both handle an empty/None line
     1 by positioning line 2 (the existing `"{airline} · {type}"` text)
     at the y-coordinate line 1 would otherwise have started at
     (`main_placement.content[3] + MAIN_TEXT_GAP_PX` /
     `prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX`) — confirmed
     working in the spike on both the main and previous card slots.
  4. Nothing resolves at all (`route is None` or has no airline either)
     → `"Departing"`/`"Arriving"` on line 1 (title case, not the top
     label's all-caps), existing `ROUTE_FALLBACK_TEXT` ("Route
     unavailable") stays on line 2, unchanged.
- Rendered, developer-confirmed proof for every tier lives in
  `.planning/spikes/001-panel-theme-colours/renders/90-*.png` through
  `94-*.png` — the planner/executor should treat these as the literal
  target output, not just a description.

### Previous-flight-card sizing/alignment (`server/plane/render.py`)

- **D-11:** `PREVIOUS_LINE2_FONT`'s size constant changes from `16` to
  `20` (path and weight unchanged — still routes through D-06's Bold
  switch).
- **D-12:** `draw_previous_text_block()`'s text-anchor x-coordinate
  becomes `prev_placement.content[2] - 20` instead of
  `prev_placement.content[2]` (applies to both of that card's lines,
  which share one right-aligned anchor). This is a **fixed, intentional
  optical correction on top of an already-correct measurement** — direct
  pixel instrumentation confirmed the unshifted anchor lands exactly on
  `prev_placement.content[2]` (the illustration's own measured opaque
  right edge), delta 0px. The offset compensates for a human-perception
  effect (the aircraft's rightmost pixel sits on a thin, raked tail-fin
  tip, not the visual mass of the fuselage the eye anchors on), confirmed
  against a rendered guide line and iterated live (15px → "a tiny bit
  more" → 20px, confirmed) — do not "fix" this by changing which edge is
  measured; the measurement was already correct.
- Only the previous card gets this offset. The main card's line 1/2 are
  centre-anchored (`anchor="ma"`), which doesn't exhibit the same
  raked-edge failure mode a single right-anchored edge does — no
  equivalent nudge was requested or should be applied there.
- Validated only against the Air France (main) / Vueling (previous)
  preview fixture illustrations — not the full ~43-file vendored
  illustration set. The plan should include a spot-check across a small
  sample of other illustration files (different tail shapes/rake angles)
  before treating the 20px value as final, or accept it with a note that
  it may need re-tuning per-file in a future pass if an outlier is found
  on real glass.

### On-glass verification (blocking gate)

- **D-13:** Every judgment above (colours, font weight, text content, the
  previous-card nudge) was made from on-screen preview PNGs only. The
  developer was explicit that none of it counts as validated until
  re-checked on the real deployed Spectra 6 panel — this repeats Phase
  7's own precedent (`hardware/BRINGUP-LOG.md`), where monitor-preview
  colour/legibility calls were overturned by real ink twice (the
  Blue/Green hue, and the backing-plate legibility fix itself — both
  mid-session on-glass corrections to something the screen had said was
  fine). **The plan MUST include a real on-glass verification pass as a
  blocking step before this phase can be marked complete** — not a
  "nice to have Later" follow-up. At minimum: the new White default, at
  least one of Black/Yellow/Red, the kept Sky theme, PT Serif Bold
  legibility at the smallest caption size, the flight-identifier content
  ladder's tiers, and the previous-card nudge should all be checked live.

### Claude's Discretion

- Exact wording/order of the `THEMES` dict's new entries in
  `server/device_config.py` (e.g. whether `"white"` is inserted first in
  source order to mirror its new default status) — no functional effect,
  `THEME_IDS = tuple(THEMES)` derives automatically either way.
- Whether the CFG-01 companion picker's rendered option order follows
  `THEME_IDS`'s dict order or needs an explicit display order — check
  `companion/pages/config_page.py`'s `theme_fieldset()` for how it
  currently iterates `THEME_IDS` before deciding if any change is needed
  there at all (it may already work unmodified since it iterates the
  registry generically).
- Whether `server/plane/render.py`'s module-level `EMPTY_INK`/empty-state
  behaviour needs any change — spike decisions only ever touched
  departing/arriving. The existing empty state is explicitly documented
  as always White/Black regardless of theme (CFG-01 doesn't apply to it)
  and should stay that way; the new White theme's departing/arriving
  colours simply now coincide with it (D-01), which is expected, not a
  conflict to resolve.
- Whether to widen the on-glass check to all 5 theme colours in one pass
  or spread it across sessions — matches the developer's own scoping
  call at execution time; D-13 states the required minimum, not a cap.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spike — the primary source for this phase's scope and decisions
- `.planning/spikes/001-panel-theme-colours/README.md` — full investigation
  trail (16 numbered steps across two rounds) with the rationale behind
  every decision above, including the outline/shadow techniques that were
  tried and rejected and why.
- `.planning/spikes/MANIFEST.md` — the condensed Requirements section
  this CONTEXT.md's `<decisions>` block is a superset of; also lists what
  is still explicitly open (Black/Yellow/Red never got an on-screen
  aesthetic reaction beyond structure/naming — still needs the on-glass
  pass per D-13).
- `.planning/spikes/001-panel-theme-colours/explore.py` and
  `explore_colours.py` — the throwaway scripts that produced every
  rendered comparison; not production code, but show exactly which
  `render.py` functions were monkeypatched and how (`_paint_text_backing`,
  `_font`, `draw_main_text_block`, `draw_previous_text_block`), useful as
  an implementation reference even though the real code should be edited
  directly rather than reusing these scripts' monkeypatch approach.
- `.planning/spikes/001-panel-theme-colours/renders/**/*.png` — the
  rendered proof for every decision; the `9x-*.png` series specifically
  documents the flight-identifier content-ladder tiers (D-10).

### Font/typography provenance
- `server/assets/fonts/VENDOR.md` — documents PT Serif Regular's known
  e-ink hairline-legibility risk (flagged, never checked on real glass
  before this phase forces the question), the prior Zilla Slab
  supersession precedent D-07 should mirror, and the Regular→Bold
  fallback this phase is now exercising for the first time.

### Data-source limitation (informs D-09's scope boundary)
- `.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md` — why
  `callsign_iata` is reliable for legacy carriers and not for
  rotating-callsign carriers, and why a real fix for the latter needs a
  different (out-of-scope) data source.
- `server/fixtures/adsbdb_hit_TVF16VB.json`,
  `server/fixtures/adsbdb_hit_AIA6412.json` — real adsbdb response shapes
  showing `callsign_iata` is present alongside `callsign_icao` on every
  hit.

### On-glass precedent (informs D-13)
- `hardware/BRINGUP-LOG.md` — Phase 7's "Final On-Glass Verification"
  entry: the exact two prior cases where a monitor-preview colour/
  legibility judgment was overturned by real Spectra 6 ink, which is why
  D-13 is a blocking gate and not a formality.
- `.planning/phases/07-final-on-glass-verification/07-01-PLAN.md` — the
  task structure Phase 7 used for its own on-glass session (CLI forcing
  flags, step-by-step verification protocol) — a reusable pattern for
  this phase's own on-glass task, even though its content (RGB
  calibration, bezel clipping, etc.) is not being re-run.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/plane/render.py`'s CLI (`build_parser()`/`main()`, `--theme`,
  `--preview`, `--previous-callsign`) already supports forcing any
  registered theme id and writing a PNG preview — no new CLI surface is
  needed to exercise the new theme entries once registered.
- `companion/pages/config_page.py`'s `theme_fieldset()` and
  `companion/app.py`'s theme-save handling already iterate
  `device_config.THEME_IDS` generically (CFG-01 was built to add themes
  by registry entry alone, per `device_config.py`'s own module
  docstring: "No structural change to this module and no call-site
  change anywhere else is required") — the companion picker should pick
  up the 4 new theme ids automatically once they exist in `THEMES`,
  without any companion-side code change. Confirm this holds during
  planning/execution rather than assuming it.

### Established Patterns
- `device_config.py`'s `THEMES` dict shape
  (`departing_index`/`arriving_index`/`ink_index`/`label`) is the
  contract every new entry must match exactly — `normalise_theme_id()`
  and every presentation accessor (`theme_background_index()`,
  `theme_ink_index()`) derive from the dict itself, so no other code
  needs to change to support new entries structurally.
- `render.py`'s `_font_cache` (keyed by `(path, size)`) means swapping
  `PTSerif-Regular.ttf` for `PTSerif-Bold.ttf` at the role-constant level
  (`STATE_LABEL_FONT`, `TOP_TAG_FONT`, `MAIN_LINE1_FONT`,
  `MAIN_LINE2_FONT`, `PREVIOUS_LINE1_FONT`, `PREVIOUS_LINE2_FONT`) is a
  single-path-string change per constant, not a structural change — same
  for the two `fit_text_size(PT_SERIF_REGULAR, ...)` call sites inside
  `draw_main_text_block()`/`draw_previous_text_block()`, which read the
  module-level `PT_SERIF_REGULAR` constant directly rather than a role
  tuple.
- `_assert_legal_palette()`'s background-dominance guard rail
  (`bg_count >= other_max`) already runs on every active-state render and
  will apply unchanged to the four new single-colour themes — no new
  assertion logic needed, but worth confirming it still holds for Black/
  Yellow/Red during execution (a much larger illustration livery area
  relative to a flat black/yellow/red field, vs. the already-proven
  white/blue/green cases, is unlikely to flip dominance but hasn't been
  measured).

### Integration Points
- `enrich._parse_route()` → `lookup_route()`'s cache write (`cache_entry
  = dict(route); cache_entry["found"] = True`) → `_route_from_entry()`'s
  cache-hit reconstruction is the exact three-point chain `callsign_iata`
  must be threaded through (D-09) — missing any one of the three means a
  cache round-trip silently drops the field even if the live-fetch path
  works.
- `render.py`'s `draw_main_text_block()`/`draw_previous_text_block()`
  both independently call `_flight_line1_text()` then position line 2
  relative to line 1 — D-10's "line 1 omitted" tier must be handled in
  both call sites (confirmed identical in spike testing, but they are
  two separate functions with separate positioning math, not a shared
  helper).

</code_context>

<specifics>
## Specific Ideas

- Every numeric value in the Decisions section above (20px offset, 20px
  font size, the exact 4-tier text ladder) came from live iteration with
  the developer reacting to real renders, not a design guess — treat
  them as locked pixel-exact values, not starting points to re-tune.
- The developer's own words on the "line 1 omitted" tier: "il retire la
  ligne principale et affiche simplement la sous-ligne avec le nom de la
  compagnie et le type d'avion" — confirms line 2's existing `"{airline}
  · {type}"` format is unchanged; only its vertical position moves up
  when line 1 is absent.

</specifics>

<deferred>
## Deferred Ideas

- A live schedule/FIDS API (e.g. AeroDataBox) as a genuine fix for
  rotating-callsign carriers' flight-number resolution — explicitly out
  of scope for this phase (D-09); would be a new external data-source
  integration, not a rendering change.
- Additional background colour candidates beyond the six real Spectra 6
  palette entries — none exist; the palette is exhaustively covered by
  this phase (White/Black/Yellow/Red/Blue/Green).
- Re-tuning the previous-card's 20px optical offset per-illustration-file
  if a real-glass or wider-illustration-set check finds an outlier
  (D-12's caveat) — not a known problem, just an unclosed risk to watch
  for during on-glass verification, not a task to schedule now.

### Reviewed Todos (not folded)
None — no matching todos found (`todo.match-phase 8` returned empty).

</deferred>

---

*Phase: 08-panel-theme-rework*
*Context gathered: 2026-08-31*
