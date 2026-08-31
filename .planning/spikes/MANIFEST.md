# Spike Manifest

## Idea

Explore panel background colour and text-legibility treatment for the
SkyPane e-ink display before committing to a plan: candidate plain-white
default background, keeping Blue/Green as optional selectable themes, and
replacing the current solid text-backing-plate rectangle (found ugly by
the developer) with a box-free legibility technique.

## Requirements

Design decisions confirmed by the developer during spiking (spike 001).
Non-negotiable for the real build:

- White becomes the new default theme (`DEFAULT_THEME_ID`) — both
  DEPARTING and ARRIVING share one flat white field; the two states are
  distinguished by the existing label text alone ("DEPARTING"/"ARRIVING"
  + "to"/"from" phrasing), not by colour.
- Blue/Green ("sky") remain available as an optional, user-selectable
  theme via the existing CFG-01 companion theme picker — not removed.
- The solid text-backing-plate rectangle (`_paint_text_backing()`) is
  removed entirely, for every theme, not just the coloured ones.
- **Font weight, not a visual trick, is what replaces it**: every text
  role switches from `PTSerif-Regular.ttf` to the already-vendored
  `PTSerif-Bold.ttf`, across ALL themes (white included) for visual
  consistency — confirmed to stay legible over the Blue/Green dithered
  background with no box, outline, or shadow needed. Outline/shadow
  variants were explored and explicitly rejected by the developer as not
  attractive enough, even though they tested as legible.
- Any future background colour must be one of the 6 real Spectra 6
  palette entries (or a dithered blend toward White of one) — no
  arbitrary RGB.

### Round 2 — flight-identifier text content (confirmed)

- **The raw ADS-B ICAO callsign (e.g. "AFR1234", "TVF16VB") is never
  displayed anywhere on the panel again.** Where an IATA-style flight
  identifier is available (`adsbdb`'s `callsign_iata` field, e.g.
  "AF1234" — currently fetched but discarded by
  `enrich._parse_route()`), show that instead. This is a genuine data
  fix, not just cosmetic: for legacy/full-service carriers the ICAO and
  IATA callsigns denote the exact same real published flight number
  (`.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md`); for
  rotating-callsign carriers (Transavia et al., ~10% adsbdb hit rate)
  neither form reliably maps to a stable flight number — this is a
  structural limitation of a callsign-keyed crowdsourced source, not a
  code gap, and a real fix would need a live schedule/FIDS API
  (AeroDataBox, never integrated) as a new, separate data source — out
  of scope for this round.
- Main-line (line 1) fallback ladder, poorest-information case last:
  1. IATA id + city known → `"{iata_id} to|from {city}"` (e.g. "AF1234
     to New York").
  2. City known, no IATA id → `"{To|From} {city}"` (e.g. "To New
     York") — no callsign shown.
  3. Only the airline is known (adsbdb miss, ICAO-prefix fallback) →
     line 1 is **omitted entirely**; the card shows only its secondary
     line ("{airline} · {type}"), promoted up to where line 1 would
     have started. Confirmed on both the main and previous card slots.
  4. Nothing resolved at all → `"Departing"`/`"Arriving"` on line 1,
     `"Route unavailable"` on line 2 (existing fallback text, unchanged).
- The previous-flight card's secondary line
  (`PREVIOUS_LINE2_FONT`) grows from 16px to **20px**.
- The previous-flight card's text block is intentionally right-shifted
  **20px left** of the illustration's measured opaque-pixel right edge
  (`prev_placement.content[2]`) — an optical, not mathematical,
  alignment correction: direct pixel measurement confirmed the
  unshifted text lands exactly on that edge (delta 0px), but the
  aircraft's rightmost pixel sits on a thin, raked tail-fin tip, not the
  visual "mass" of the aircraft body — the eye anchors on the latter,
  reading the mathematically-exact version as shifted right. This is a
  fixed pixel offset added at the existing anchor point, not a change to
  which pixel is measured.

Not yet decided / open for the planning phase:
- Whether `PTSerif-Regular.ttf` stays vendored-but-unused (matching the
  Zilla Slab/Inter "retained for provenance" precedent in
  `server/assets/fonts/VENDOR.md`) or is removed outright.
- Real Spectra 6 glass has not yet confirmed Bold's legibility — only
  on-screen preview PNGs (same caveat Phase 7's own history carries for
  every colour/legibility judgment made off real glass).
- Additional background colour candidates (Black/Yellow/Red flat fills)
  were rendered and shown (`renders/colours/`) but never explicitly
  confirmed or rejected by the developer — still open.
- Whether the main card's line 1 needs the same 20px-style optical
  nudge (it doesn't today: line 1/2 are centre-anchored there, which
  doesn't exhibit this failure mode the same way right-anchored text
  does) — flagged only so a future reader doesn't assume it was
  overlooked.
- The 20px previous-card nudge and the callsign_iata fallback ladder
  were validated only against the Air France/Vueling preview fixture
  illustrations — not checked against the full 43-file illustration set
  for outliers.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | panel-theme-colours | comparison | White vs. Blue/Green backgrounds, box-free text-legibility techniques, flight-identifier text content, and previous-card text sizing/alignment | VALIDATED — see Requirements above for the full confirmed decision set | render, theme, palette, legibility, e-ink, typography |
