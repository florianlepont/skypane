# Phase 27: Companion review feedback — the defects and the noise the developer found on the real app - Context

**Gathered:** 2026-09-14
**Status:** Ready for planning
**Source:** Roadmap brief express path (ROADMAP.md §Phase 27, committed `f3f89d5`) — the developer
reviewed phases 23/24/25 on the DEPLOYED app. No `/gsd-discuss-phase` session was run; the roadmap
entry plus the launching brief carry the developer's own words and are treated as the locked
decision source. Where the developer's wording carries the judgement it is quoted verbatim.

<domain>
## Phase Boundary

This phase fixes **one real defect** and **six product corrections** found by the developer on the
real, deployed app after phases 23 (Alive), 24 (Drawn) and 25 (Controls) shipped. **It adds no new
capability.** Every item is a removal, a correction, or a relationship that was never asserted.

**In scope:**

1. The quiet-hours dial defect (D17): the arc and the caption do not follow the handles.
2. Correction 1 — no save button at all; auto-save with a transient status.
3. Correction 2 — one title form everywhere.
4. Correction 3 — remove D16's runway map; CFG-47 retired.
5. Correction 4 — cut the explanatory text (wake slider, its gauges, Quiet hours paragraph).
6. Correction 5 — extend the carousel to the other colour grids; "Voir tous les thèmes" below the strip.
7. Correction 6 — link the Frame strip's Quiet hours switch to the schedule fields.
8. Two findings carried in from earlier phases (the Departures·Arrivals legend; `.copy-btn`'s hit area).

**Out of scope, deliberately:** the "règles par vol" view. See `<deferred>`.

**The lesson this phase exists to carry, and which must appear as a stated convention in every plan:**
the dial's arc was asserted correct *server-side for the saved value*, the handles were asserted to
*move*, and the value was asserted to *persist to disk*. Three correct halves. **Nothing ever asserted
that the arc agrees with the handles after an interaction.** An arc showing 23:00→07:00 while the
fields say 08:00→18:00 is worse than no arc: it actively lies. **Assert relationships, not just
endpoints.**

</domain>

<decisions>
## Implementation Decisions

### The defect — D17's quiet-hours dial

- **D-01**: The arc and the caption are driven by **the pair of values**, not by one value per wrapper.
  The cause is already diagnosed and must NOT be re-derived: `companion/static/value-controls.js`
  models ONE value per wrapper, and `paint()` writes a per-handle CSS custom property (the fraction).
  An arc and a span sentence are functions of BOTH values and nothing in the script models the pair.
  Measured on the developer's screen recording: fields read `08:00`/`18:00`, both handles sit at 8 and
  18, the arc still draws 23:00→07:00, the caption still reads `23:00 → 07:00 · 8 h`.
- **D-02**: **Prefer the shape that keeps the server-rendered arc authoritative for the saved value**,
  because that is what survives with scripts blocked. Weigh at minimum: (a) a CSS-only representation
  both handles can feed — two custom properties on a shared ancestor driving a conic-gradient or a
  dual-property SVG; versus (b) the script recomputing the SVG geometry. Record the trade-off and the
  choice in the plan; do not silently pick one.
- **D-03**: Whichever shape is chosen, the phase carries **ONE executable check that the arc agrees
  with the handles AND with the caption after an interaction** — a single relationship assertion, not
  three separate checks that each half is right. Three passing halves are exactly what shipped this
  defect.

### Correction 1 — no save button at all

- **D-04**: No save button on the settings pages. The developer's words: *"je veux aucun bouton ça sert
  à rien. Si tu veux une confirmation visuelle, un 'sauvegarde…' et 'sauvegardé' suffit."* Settings
  save automatically with a transient **"Sauvegarde…" → "Sauvegardé"**.
- **D-05**: The native submit exists **ONLY when scripts are blocked**, hidden by the `.js` gate that
  25-01 built (`.js` is added unconditionally to `<html>` by `nav-dropdown.js`'s first statement).
- **D-06**: **This retires the dirty save bar** that Phases 22 and 23 invested heavily in, including
  B1/P0's `[data-static-save-fallback]` visibility contract whose rule
  `.dirty-ready.dirty-shown [data-static-save-fallback]` (`companion/static/style.css:1568`) is exactly
  why a large accented "Enregistrer les réglages" button greets every fresh page load.
- **D-07**: That superseded contract is **amended in writing, not deleted** — the comment block that
  carries it states what replaced it and why, so a reader of the stylesheet finds the history rather
  than a hole.
- **D-08**: **What an auto-save that FAILS does is settled, not assumed.** Reuse the app's existing
  failure vocabulary: the optimistic rollback the `role="switch"` controls already perform plus the
  translated generic toast. **Do not invent a second failure vocabulary.**
- **D-09**: **What auto-save does to the three `role="switch"` controls that already save instantly is
  settled, not assumed.** The page must not end up with two save models. Name the single model.
- **D-10**: **How the leave-guard and the Cancel ("Annuler") affordance are retired or replaced is
  settled, not assumed** — "Annuler" only means something against a pending edit, and with auto-save
  there is no pending edit.
- **D-11**: **The no-JS floor (D-09, absolute) is kept BY CONSTRUCTION, not by a visibility rule.** The
  native submit is present in the response body unconditionally; script presence only hides it.
  Proven by **saving to disk** through 25-02's `_operate_submit_persist()` — never by rendering.
  This is the most dangerous change in the phase against the floor.

### Correction 2 — one title form everywhere

- **D-12**: Titles currently sit **inside** the setting tile on some cards and **above** it on others.
  **Inventory both shapes across every settings card FIRST; the plan names the count of each before
  choosing.** Then pick one and apply it everywhere.

### Correction 3 — remove D16's runway map

- **D-13**: Remove the runway map. The developer's words: *"Je comprends pas l'intérêt de ces cartes
  des pistes, elles représentent la même chose que mes schémas."* It cost a whole wave in Phase 25 and
  teaches the developer nothing. **The three native radios return to being the control.**
- **D-14**: The three `runway-*.png` photographs **stay served** — they were never deleted, keep their
  slot, their route and their files.
- **D-15**: **CFG-47 is RETIRED IN PLACE with a stated reason — never silently deleted** from a ticked
  row. The retirement is recorded in the requirements ledger alongside the tick it supersedes.
- **D-16**: Standing checks that assert the map's classes and geometry **come out too**. The plan
  **names which checks are removed**, and `EXPECTED_CHECK_COUNT` for every harness touched is
  **re-derived by RUNNING**, never by arithmetic.

### Correction 4 — cut the explanatory text

- **D-17**: Cut the explanatory text on the **wake-interval slider** (*"beaucoup trop de texte
  d'explication"*), **its gauges**, and the **Quiet hours card's paragraph**.
- **D-18**: Some of that text carries an **honesty contract**: D18's battery gauge must never state a
  figure the data cannot support. **Shorten without weakening what it refuses to claim.** A shorter
  sentence that starts claiming a number is a regression, not a cut.

### Correction 5 — extend the carousel, and Display's height

- **D-19**: Extend the carousel to the **other colour grids** — arrivals, departures, calendar flights
  — matching the pattern already shipped for the first grid.
- **D-20**: Move **"Voir tous les thèmes" BELOW the strip**.
- **D-21**: This is also what is left of Display's page height. 25-06 measured **3743 px at 390 px**
  against X6's **2600 px** target and recorded that the remainder is **four more cards, not a grid**.
  **The plan predicts the height it expects to reach and states that number**, so the closing plan can
  report the real measurement against a stated expectation rather than against nothing.

### Correction 6 — the Frame strip's Quiet hours link

- **D-22**: Add a link from the **Frame strip's Quiet hours switch to the schedule fields**. The card
  already names where the switch is; the reverse does not exist.
- **D-23**: The Frame strip is a **shared component rendered on more than one page — it must NOT be
  forked.** One component, one change, correct on every page that renders it.

### Carried in from earlier phases' own findings

- **D-24**: `departing_index == arriving_index` for **18 of 18 themes**, so the shipped
  "Departures · Arrivals" legend names two swatches that are never different. **Decide whether this
  belongs in this phase and say why either way.** Provisional recommendation: **IN** — it is the same
  class of defect as correction 4 (text claiming a distinction the data does not carry), it sits in
  the colour grids correction 5 already touches, and it is cheap.
- **D-25**: `.copy-btn`'s measured **34×26** hit area in a Flights detail row, against the project's
  44 px floor. **Decide whether this belongs in this phase and say why either way.** Provisional
  recommendation: **IN** — it is an already-measured defect against a standing floor, it is a
  correction rather than a new capability, and the hit-target instrumentation already exists.

### Standing constraints every plan must respect AND state

- **D-26**: CSP is `script-src 'self'`; there is **no catch-all `/static/` handler**, so any new script
  needs its own route and moves the deferred-script pin (currently **15**). **This phase should need
  NO new script — every plan states so explicitly, and a plan that wants one must justify it and pay
  the route + pin tax.**
- **D-27**: Minimum viewport **360 px**, **no horizontal body scroll**. Hit targets measured with
  `_assert_hit_target()` **in their own container** — a declared 44 is not a resolved 44. Three
  separate proofs exist as precedent: `.copy-btn` 34×26, a handle 43×43, a pager 30×45.
- **D-28**: **Both themes are load-bearing** and measurable via `_set_ui_theme()`.
- **D-29**: **Motion tokens only**; exactly **4** `@keyframes`; exactly **1**
  `@supports selector(:has(*))` block, **brace-anchored** (a bare grep returns 6 because comments
  quote the at-rule); `interpolate-size` and `calc-size(` **banned**; `style.css` at **zero** stray
  comment terminators.
- **D-30**: **`test_config_page.py` locates rules by the FIRST occurrence of a literal in
  `style.css`** — **never quote another rule's selector in a new comment.**
- **D-31**: Every check **mutation-tested with the failure message quoted**; every check must survive
  the vacuity question. `EXPECTED_CHECK_COUNT` **re-derived by RUNNING**. The sandbox baseline is
  exactly **5 failing checks, verified by NAME**.
- **D-32**: **Assert relationships, not just endpoints** — this phase's own lesson, and it appears in
  every plan as a stated convention.
- **D-33**: Design authority is the `sketch-findings-skypane` skill, which now carries **five
  contracts** (motion, colour, spacing, drawing, controls). **Two standing refusals must not reappear:
  the overlay drawer and sticky day headers.**

### Requirements

- **D-34**: `.planning/REQUIREMENTS.md` runs to **CFG-61** (phase 26's plans hold CFG-53…61 and are NOT
  executed). Phase 27's requirements are appended from **CFG-62**, all unticked.

### Claude's Discretion

- The exact plan split, wave assignment and plan count.
- The specific CSS/SVG mechanism chosen for D-01/D-02, provided the trade-off is recorded and the
  server-rendered arc stays authoritative for the saved value.
- Which title form (inside-tile or above-tile) wins in D-12, provided the inventory count is stated
  before the choice.
- Exact wording of the shortened texts in D-17, provided D-18's refusal is preserved.
- The predicted height figure in D-21, provided it is stated before measurement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The defect
- `companion/static/value-controls.js` — one value per wrapper; `paint()` at ~L491; `paintReadouts()`
  at ~L468; `repaintAll()` at ~L750. The structural cause of the dial defect.
- `companion/layout.py` — the server-rendered quiet-hours dial SVG (arc + caption), and the Frame strip.
- `companion/static/style.css` — the `.js` gate (~L1109), `[data-static-save-fallback]` contract (~L1552–1568).

### Correction 1
- `companion/static/dirty-state.js` — the dirty save bar being retired (598 lines).
- `companion/static/submit-guard.js`, `companion/static/confirm-submit.js` — the leave-guard / confirm surface.
- `companion/test_browser_ux.py` — `_operate_submit_persist()` (25-02), the save-to-disk proof; `_assert_hit_target()`; `_set_ui_theme()`.

### Correction 3
- `.planning/REQUIREMENTS.md` — CFG-47 row (L73) and its ledger entry (L199); the D16 section (L568).
- `.planning/phases/25-companion-dynamism-iii-controls-the-modern-controls-that-rep/25-03-PLAN.md` — the map as built.
- `companion/static/RUNWAY-IMAGES.md`, `companion/static/runway-*.png` — the photographs that stay.

### Phase history
- `.planning/ROADMAP.md` §Phase 27 (L1252+) — the brief itself.
- `.planning/phases/25-.../25-08-SUMMARY.md` — Phase 25's closing gate, CFG-47's tick, Display's 3743 px.
- `.planning/phases/26-.../` — CFG-53…61, planned and NOT executed. Do not disturb.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the design authority, five contracts.

</canonical_refs>

<specifics>
## Specific Ideas

- Measured evidence for the dial defect: fields `08:00`/`18:00`, handles at 8 and 18, arc drawing
  23:00→07:00, caption `23:00 → 07:00 · 8 h`.
- The offending CSS rule for the save bar: `.dirty-ready.dirty-shown [data-static-save-fallback]`.
- Display height: 3743 px measured at 390 px; target 2600 px (X6); remainder is four cards, not a grid.
- Deferred-script pin: currently **15**.
- Sandbox baseline: exactly **5** failing checks, verified by NAME.
- `@keyframes` count: **4**. `@supports selector(:has(*))` blocks: **1**, brace-anchored.

</specifics>

<deferred>
## Deferred Ideas

- **The "règles par vol" view.** The developer's brief — *"pas propre, manque de simplicité, trop de
  texte"* — is too vague to plan against and needs a conversation first. **Explicitly NOT planned in
  this phase.** Record it as deferred; it is scoped separately.

</deferred>

---

*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Context gathered: 2026-09-14 via roadmap-brief express path*
