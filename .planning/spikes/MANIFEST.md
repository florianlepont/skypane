# Spike Manifest

## Idea

Explore panel background colour and text-legibility treatment for the
SkyPane e-ink display before committing to a plan: candidate plain-white
default background, keeping Blue/Green as optional selectable themes, and
replacing the current solid text-backing-plate rectangle (found ugly by
the developer) with a box-free legibility technique.

**Continuation (spike 002, 2026-08-31, after Phase 8 shipped):** two
smaller polish ideas Claude itself surfaced mid-session when asked what
else could make the panel "read as a real, beautiful board" —
letter-spacing on the two smallest top labels, and re-checking the
illustration-to-text vertical spacing now that White's final render is
real and deployed. See `002-small-labels-and-white-rhythm/README.md`.

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

- **Black/Yellow/Red are approved as additional candidate optional
  themes**, alongside White (default) and Blue/Green — developer
  confirmed interest in the full 6-colour set, not just White/Blue/Green.

### On-glass verification is a required gate, not optional (developer, explicit)

Every judgment recorded in this spike — colours, font weight, text
content, the previous-card nudge — was made from on-screen preview PNGs
only. The developer explicitly does not consider any of it finally
validated until it is re-checked on the real Spectra 6 panel, regardless
of how confident the on-screen result looks. This is not a new rule
invented for this spike: it repeats Phase 7's own precedent
(`hardware/BRINGUP-LOG.md`), where monitor-preview colour/legibility
calls were overturned by real ink twice (Blue/Green hue, and the
backing-plate legibility fix itself, both mid-session on-glass
corrections to something the screen had said was fine). **Whatever plan
implements this spike's decisions must include a real on-glass
verification pass as a blocking step before the milestone can be
considered done** — not a "nice to have Later" follow-up.

Not yet decided / open for the planning phase:
- Whether `PTSerif-Regular.ttf` stays vendored-but-unused (matching the
  Zilla Slab/Inter "retained for provenance" precedent in
  `server/assets/fonts/VENDOR.md`) or is removed outright.
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
| 002a | small-caps-labels | standard | Letter-spacing (tracking) treatment for the top-left state label and top-right runway tag, on both a flat and a dithered theme | PENDING — checkpoint presented, awaiting developer reaction | render, typography, tracking, letter-spacing, e-ink |
| 002b | white-vertical-rhythm | standard | Whether the illustration-to-text empty space reads differently on the White default than it did on the previously-shipped dithered colour fields | PENDING — checkpoint presented, awaiting developer reaction | render, layout, white-theme, e-ink |
