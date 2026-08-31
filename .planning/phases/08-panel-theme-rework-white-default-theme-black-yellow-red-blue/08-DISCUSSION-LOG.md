# Phase 8: Panel theme rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-31
**Phase:** 08-panel-theme-rework
**Areas discussed:** Theme structure for new colours, Unused PT Serif Regular font, Theme picker naming

Most of this phase's substance was already decided before this discuss-phase
session ran, during an extended interactive spike
(`.planning/spikes/001-panel-theme-colours/`) with dozens of rendered
comparisons reacted to live. This session's job was narrower: resolve the
handful of implementation-level gray areas the spike left open, rather than
re-litigate anything already confirmed there. See
`.planning/spikes/001-panel-theme-colours/README.md` for the full spike
investigation trail (colours, font weight, flight-identifier text content,
previous-card sizing/alignment).

---

## Theme structure for Black/Yellow/Red

| Option | Description | Selected |
|--------|-------------|----------|
| Couleur unique (comme Blanc) | Same background for DEPARTING and ARRIVING (e.g. all-black, all-yellow, all-red) — state distinguished only by label text, matching the already-confirmed White theme pattern | ✓ |
| Paires bicolores (comme Sky) | Each theme gets two different colours for DEPARTING/ARRIVING (e.g. Yellow=departing, Red=arriving) — more combinations to name and validate on glass | |

**User's choice:** Couleur unique (comme Blanc).
**Notes:** Matches the pattern already established and confirmed acceptable
for the White theme in the spike conversation ("avec un thème blanc,
DEPARTING et ARRIVING ne se distinguent plus que par le texte"). Extending
the same simple structure to Black/Yellow/Red avoids inventing new
colour-pairing semantics with no basis in the spike's findings.

---

## Unused PT Serif Regular font

| Option | Description | Selected |
|--------|-------------|----------|
| Garder vendored, inactif (Recommandé) | Same treatment as Zilla Slab/Inter in VENDOR.md — kept for provenance/traceability, marked "superseded", no longer referenced by active code | ✓ |
| Supprimer complètement | Remove the .ttf file and its VENDOR.md entry — nothing unused left in the repo | |

**User's choice:** Garder vendored, inactif.
**Notes:** Matches this project's own established precedent — VENDOR.md
already keeps two prior superseded typefaces (Inter, Zilla Slab) on disk
with a "Supersession" note rather than deleting them.

---

## Theme picker naming

| Option | Description | Selected |
|--------|-------------|----------|
| Descriptifs simples | "White", "Black", "Yellow", "Red", "Sky" — direct colour names, consistent with the existing "Sky" entry | ✓ |
| Évocateurs | "Paper", "Night", "Sun", "Ember", "Sky" — more personality, less literal | |

**User's choice:** Descriptifs simples.
**Notes:** Consistent with the plain, literal labelling style already used
elsewhere in `device_config.py`'s registries (e.g. `RUNWAYS`' labels like
"Runway 3 (07/25)").

---

## Claude's Discretion

- Source-order placement of the new `THEMES` entries in `device_config.py`.
- Whether the companion CFG-01 picker needs any code change at all to pick
  up the new theme ids (likely not, since it iterates the registry
  generically — to be confirmed during planning/execution).
- Empty-state rendering: confirmed out of scope, stays White/Black
  regardless of theme, unchanged by this phase.
- Whether the on-glass verification pass checks all 5 themes in one
  session or spreads across sessions — developer's call at execution
  time; only a minimum coverage bar is fixed in CONTEXT.md.

## Deferred Ideas

- A live schedule/FIDS API (e.g. AeroDataBox) to reliably resolve flight
  numbers for rotating-callsign carriers — out of scope, would be a new
  external data-source integration.
- Re-tuning the previous-card's 20px optical alignment offset per
  illustration file, if a wider check ever finds an outlier — not a known
  problem today, just a flagged risk to watch for on real glass.
