---
sketch: 003
name: history-table-density
question: "Does merging Callsign+Hex and Type+Airline make the table fit a 13-inch laptop without horizontal scroll?"
winner: "B"
tags: [data-density, table]
---

# Sketch 003: History Table Density

## Design Question
The real History table has 9 columns (Timestamp, Callsign, Hex, Aircraft type, Airline, Route, State, Corroboration, Runway) and doesn't fit a 13" MacBook without horizontal scroll. 06.6.1-CONTEXT.md's locked decision is to merge Callsign+Hex and Type+Airline into combined cells (7 columns) — this sketch shows that treatment with real-shaped data at real MacBook width (1280px) to validate it actually reads well, and explores two ways to execute the merge.

## How to View
```
open .planning/sketches/003-history-table-density/index.html
```

## Variants
- **A: Stacked cells** — Callsign (bold, mono) on top, Hex (grey, smaller) directly below in the same cell. Same pattern for Type/Airline. Clear visual hierarchy (primary vs. secondary info), but each row is a bit taller.
- **B: Inline compact** — Callsign · Hex on one line (separated by a middle dot), same for Type · Airline. Rows stay the same height as today, but two different data types share one visual line.
- **C: Max density** — Goes further than the locked decision: also merges State into the Route column ("ORY → TLS · DEPARTING"), landing at 6 columns with visible room to spare at 1280px. Included as a reference point for "how far could we push it," not a proposal — the locked decision only covers Callsign+Hex and Type+Airline.

## What to Look For
- A vs. B: does the extra row height in A (stacked) feel more readable, or does B's compactness matter more for scanning many rows quickly?
- Does the secondary info (Hex, Airline) feel appropriately de-emphasized (smaller/grey) without becoming illegible?
- C is explicitly out of scope for this phase's locked decision — look at it only to judge whether there's appetite to extend the merge further in a future pass, not to adopt now.
- All three assume 06.6's upcoming relative-timestamp format ("3m ago") rather than the current full ISO string — that phase hasn't shipped yet, so this is a preview of how the two phases compound.
