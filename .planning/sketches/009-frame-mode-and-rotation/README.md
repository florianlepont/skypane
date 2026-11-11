---
sketch: 009
name: frame-mode-and-rotation
question: "How should per-frame mode (planes or photos), rotation interval and order be grouped, and how are the wake-interval consequence, the 'no photo yet' state and the privacy rule shown?"
winner: null
tags: [photos, settings, mode, rotation, control-density, mobile, desktop, i18n, v1.3]
---

# Sketch 009: Frame mode and rotation

## Design Question
Each frame has exactly one mode (planes or photos). In photo mode: a rotation interval (hourly, 6 h, 12 h, daily; default daily) and an order (random without repeats, or upload order), and the frame's wake interval follows the rotation. Which grouping (segmented controls, cards, accordion) reads best, and how do we state what changes?

## How to View
open .planning/sketches/009-frame-mode-and-rotation/index.html

Params: `?v=a|b|c&mode=planes|photos&interval=1h|6h|12h|24h&order=random|upload&photos=some|none&saved=planes|photos&lang=fr&theme=dark&chrome=0`.
State controls flip the saved mode and the photo count. The card is placed on the Device page (placement is an open question).

## Variants
- **A: Segmented controls** — one card: Mode segmented control; in photo mode a sub-section with the rotation segmented control (Hourly / 6 h / 12 h / Daily), the order segmented control and a photo strip with "Manage photos". Follows the app's one segmented contract (solid accent pill).
- **B: Cards** — mode as two selectable cards with small drawings; rotation and order as radio lists in a second card (rotation rows show "24 a day" ... "1 a day"; order rows carry a sentence each).
- **C: Accordion** — summary rows "Mode: Photos", "Change the photo: Daily", "Order: Random, no repeats" that expand one at a time (the accepted pattern of sketch 006); rotation and order rows only exist in photo mode.

## Common
- Honest consequences below the controls: in photo mode the frame wakes once per rotation (not every 2 minutes) so changes, new photos and a switch back to planes can take up to one interval to reach it; no battery estimate for photo mode yet (needs measurement); a warning when switching back from photo mode that the sleeping frame may take that long to learn it.
- "No photo yet" state: warning message that the frame shows a waiting screen until a photo is added, with an Add photos action.
- Privacy line with a lock: only the owner and co-managers see photos, the admin does not.
- Floating Cancel / Save bar and a "saved, reaches the frame at its next wake" (pending tone) toast.

## What to Look For
- Which grouping makes "one mode, and these two settings only apply in photo mode" clearest on a phone?
- Is the wake-interval consequence understood without reading a paragraph?
- Does the cost of B's extra height and C's extra taps buy anything over A?
- Open: Device page vs a Photos page for these controls; whether random order should state "no repeats" in the label itself.
