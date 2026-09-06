# Phase 14: Resolve an unidentified flight from the gallery lightbox - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
**Areas discussed:** The gap card, Where the gaps live, What becomes of the table, The JavaScript posture

---

## Pre-discussion scout

Read before offering any option, and it changed what was worth asking:

- A gallery card is a `<button class="airline-card__zoom">` carrying three `data-view-panel-*` attributes, wrapping the image.
- `panel-lookup.js` (134 lines, ES5, no `closest()`, no network call, shared with History) listens for delegated clicks on `[data-view-panel-src]`, copies those attributes into the shared `<dialog>`, rewrites the replace form's `action`, and calls `showModal()`.
- **Consequence neither the developer nor the assistant had anticipated:** the attribute the script triggers on is the *image source*. A gap card has no image, so the dialog must learn to open without one — and that script is shared with History.

---

## The gap card

| Option | Description | Selected |
|--------|-------------|----------|
| Callsign in front, scope in the dialog | Card shows `XQZ411`; the dialog states that naming dresses every flight of the prefix. Honesty where it matters. | ✓ |
| Prefix in front, callsign as support | Card can never mislead — but a bare ICAO prefix is drier on a page built for a visual sweep. | |
| Both at equal weight | Avoids choosing, at the cost of scannability. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Empty frame drawn in CSS | No image, no asset, no request; reads immediately as a hole. Requires teaching the script an imageless open. | ✓ |
| The generic fallback illustration | Literally what the frame renders today — the grid would tell the exact truth — but it looks like an ordinary card. | |
| The fallback, dimmed | Compromise; invents a visual treatment absent from the design system. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Two forms in the shared dialog, script toggles | Extends the "optional element, gracefully absent" pattern already used for the replace form. | ✓ |
| A second dedicated dialog | Cleaner on paper; in practice two ids and a handler that must choose — more script logic, not less. | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Card changes state, click it again | Two deliberate clicks; the script never opens on load. | ✓ **(later withdrawn — see the reconciliation below)** |
| The redirect reopens the dialog | Smoother; the script gains a load-time open. | |
| You decide | | |

---

## Where the gaps live

| Option | Description | Selected |
|--------|-------------|----------|
| Same grid, capped | Gaps among the art — the idea's visual force — but bounded. Health stays the exhaustive registry. | ✓ |
| Dedicated sub-section | Safe on volume, filter bar untouched; loses the contrast between art and absence. | |
| Same grid, show everything | The literal phrasing; one bad traffic week drowns 43 illustrations. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Gap block at the head, sorted by sightings | What needs action comes first; the page is a work surface before a gallery. | ✓ |
| At the tail | Gentler; but you must scroll past 43 cards to learn there is work to do. | |
| You decide | | |

*Alphabetical interleaving was deliberately not offered: a gap has no airline name, only a prefix, so there is nothing to sort it against.*

| Option | Description | Selected |
|--------|-------------|----------|
| Threshold AND hard cap (≥3 sightings, ≤12 cards) | One-off sightings never clutter; a recurring gap always surfaces; the gallery stays legible. | ✓ |
| Hard cap only — 12 cards | Simpler to spec and test; a quiet week fills the grid with single sightings that probably don't merit art. | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| A line below the block | Count plus a link to Health, in the caption register the page already uses. | ✓ |
| A "+N more" card | More in the grid's spirit; one more card variant to spec, style and test. | |
| Nothing | Smallest — and the grid would then imply it shows every gap. | |

---

## What becomes of the table

| Option | Description | Selected |
|--------|-------------|----------|
| A chip on the card | Reuses `.airline-card__chip`; state reads in the grid without a click. Zero new component. | ✓ |
| A distinct visual treatment | Stronger signal; invents a treatment absent from the design system, to hold in both themes. | |
| Nothing on the card, all behind the click | Purest grid; empties Phase 13's D-06 of its meaning, since a superseded entry becomes invisible. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Delete lives in the dialog | Grid stays legible; explicit intent without a confirmation box. | ✓ |
| Delete on the card | Faster; a destructive control in a dense grid whose neighbouring click is "enlarge". | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| A superseded card shows what the frame really renders | The gallery never lies about current state; the dialog explains the orphaned upload. | ✓ |
| The orphaned upload, dimmed | More expressive of the loss; asserts something false about what the frame renders now. | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| A summary line survives | "4 manual resolutions, 1 superseded", clickable to filter — what makes a superseded entry noticeable among ~55 cards. | ✓ |
| Nothing, the filter suffices | Zero new UI; but you must know to type the word, and nothing announces a superseded entry. | |
| You decide | | |

---

## The JavaScript posture

| Option | Description | Selected |
|--------|-------------|----------|
| Progressive enhancement | `<a href="/airlines?resolve=XQZ">` carrying the trigger attribute; JS intercepts, no-JS navigates to Phase 13's section, kept as fallback. Cheap because the script's delegation never required a `<button>`. | ✓ |
| Simply inherit the dependency | One rendering path, section genuinely deleted, consistent with replacement which already needs JS — but resolving becomes impossible without JS. | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| The dialog opens on arrival | Health > Resolve lands straight in the pop-up — the developer's original expectation. | ✓ |
| Link lands on the card, you click it | Two clicks; the script keeps its no-load-time-open contract. | |
| Health no longer points at an action | Most coherent conceptually; loses the shortcut from where the gap is noticed. | |

**This question was asked twice at the developer's request** ("non repose la question"), the second time with the D-04 contract restated in the prompt.

### The reconciliation

Selecting the load-time open contradicted the earlier "click it again" answer: Phase 13's redirect already carries `?resolve={prefix}` when artwork is still missing (verified in `13-UAT.md`, test 8), so a load-time open on that parameter necessarily fires after naming too. The conflict was surfaced rather than resolved silently, and the developer asked for D-04 to be restated before choosing.

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-open everywhere; the earlier answer falls | One simple rule: `?resolve=` opens the dialog, wherever you came from. After naming it reopens itself on the upload step. | ✓ |
| Auto-open reserved to Health | A distinct marker on Health's link only; both intentions preserved, at the cost of a finer two-case rule. | |
| You decide | | |

---

## Claude's Discretion

- One rendering function for the resolve form, emitted both inside the dialog and inside the no-JS fallback, so the two cannot drift. Discretion covers *how* it is factored, not *whether*.
- All copy: the dialog's scope sentence, chip labels, the overflow line, the summary line, the superseded explanation.
- Exact threshold and cap values behind the locked threshold-and-cap shape.
- How the script distinguishes a gap trigger from an art trigger and opens without an image, while staying backward-compatible with History.

## Deferred Ideas

- A "+N more" overflow card, if the grid later gains other variants.
- Phase 13's G-01 (a rejected name reported as empty) — copy in the surface this phase rewrites; should be fixed here.
- A distinct visual treatment for manual cards, if the chip proves too quiet.
- Retiring the no-JS fallback, if the second rendering path proves a real burden once built.
