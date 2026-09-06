# Phase 14: Resolve an unidentified flight from the gallery lightbox, with coverage gaps as empty cards - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fold Phase 13's resolve flow into the interaction pattern the Airlines gallery already uses. A coverage gap becomes an empty card in the grid, alongside the art that does exist; clicking it opens the same shared `<dialog>` every other card opens, and the naming/upload happens there. The standalone "Manually resolved prefixes" table is absorbed into the cards.

**This is a presentation-layer phase.** Every server-side piece it consumes shipped in Phase 13 and is not touched: `server/plane/manual_resolutions.py`, `server/plane/enrich.py`, `server/poll_loop.py`, and the two POST routes in `companion/app.py`. A plan proposing to modify any of them is a signal the scope drifted.

**Origin.** Raised by the developer within minutes of Phase 13 shipping, on seeing the real page: *"ce tableau ne sert à rien. Quand je clique dans health > resolve > je m'attendais à voir une pop up plutôt. Pour les vols inconnus, j'imaginais des cases vides avec juste les callsign d'écrit dans la page airline. Un clic dessus ouvre également la pop up."*

</domain>

<decisions>
## Implementation Decisions

### The gap card

- **D-01:** **The card's primary label is the example callsign** (`XQZ411`), not the prefix — concrete and recognisable at a glance in a grid, which is the developer's own framing. Because resolution is per **3-letter prefix**, naming it dresses *every* flight of that prefix; **the dialog states that scope at the moment of acting**. The honesty lands where it matters rather than making the grid arid.

  Rejected: **prefix in front, callsign as support** — the card could then never mislead, but a bare ICAO prefix is drier than a real callsign on a page whose value is a quick visual sweep. Rejected: **both at equal weight** — avoids choosing, at the cost of the scannability the whole idea rests on.

- **D-02:** **A gap card's emptiness is drawn in CSS — no image at all.** No asset, no network request, and it reads immediately as "something is missing here", which is exactly the developer's "cases vides".

  **This has a mechanical consequence the planner must handle:** `panel-lookup.js` triggers on `data-view-panel-src` and copies that `src` into the dialog's `<img>`. A gap has no image, so **the script must learn to open the dialog without one** — and that script is shared with History, so the change must stay backward-compatible there.

  Rejected: **`generic-fallback.png`** — literally what the frame renders for that flight today, so the grid would tell the exact truth about the current state; rejected because it looks like an ordinary card rather than a hole. Rejected: **the fallback, dimmed** — a compromise that invents a visual treatment absent from the design system.

- **D-03:** **Both forms live in the one shared dialog; the script shows the right one** based on the clicked card's data attributes. This extends the "optional element, gracefully absent" pattern already established for the replace form — `panel-lookup.js` already looks up `.lightbox__replace` outside its guard precisely because History never renders it.

  Rejected: **a second dedicated `<dialog>`** — cleaner separation of roles on paper, but two elements and two ids mean the delegated click handler must now choose which to open: *more* script logic, not less.

### Where the gaps live

- **D-04:** **Gap cards live in the gallery grid itself, among the art, but bounded.** The visual force of the idea is seeing the holes *among* the art; Health remains by construction the exhaustive registry.

  Rejected: **a dedicated sub-section** — safe on volume and leaves the filter bar untouched, but loses the contrast between the art and its absences. Rejected: **the same grid with everything shown** — the developer's literal phrasing, but one bad traffic week drowns 43 illustrations under empty cards.

- **D-05:** **The gap block sits at the head of the grid, sorted by sighting count descending** — what needs action comes first, the most-seen flight is the first empty card, and the art follows. The page becomes a work surface before it is a gallery.

  Note for the planner: **interleaving gaps alphabetically among the airlines is incoherent** and was not offered — a gap has no airline name yet, only a prefix, so there is nothing to sort it against.

- **D-06:** **Two bounds together: a threshold and a hard cap** — show only prefixes seen **at least 3 times**, and never more than **12 cards**. One-off sightings (a diverted flight, a rare visitor) never clutter the grid, a genuinely recurring gap always surfaces, and the gallery stays legible even in a heavy week. Exact values are a UI-SPEC matter; the *shape* — threshold AND cap, not one or the other — is locked.

- **D-07:** **A line below the block names what the cap hides**, with the count and a link to Health — *"7 other unresolved prefixes — see the full list"* — in the caption register the page already uses. Without it the grid would imply it shows every gap, which is false the moment the cap bites, and Phase 13's governing constraint was that the operator is never silently misled.

  Rejected: **a "+N more" card** — more in the spirit of a grid that expresses everything including its own limits, but one more card variant to spec, style and test. Rejected: **nothing at all** — smallest, and quietly wrong.

### What becomes of the management table

- **D-08:** **A manual origin is marked with a chip on the card**, reusing `.airline-card__chip` — already in place for fleet variants. `"resolved by hand"`, and `"superseded"` when the static table has taken over. Zero new component, and the state reads in the grid without a click.

  This is what makes the absorption safe: if a manually-resolved airline became an indistinguishable ordinary card, a superseded entry would be invisible — and Phase 13's D-06 exists precisely so the operator's art never disappears without explanation.

  Rejected: **a distinct visual treatment** (border/wash) — a stronger signal, but invents a treatment absent from the design system that would need validating in both themes. Rejected: **nothing on the card, everything behind the click** — the purest grid, but it empties Phase 13's D-06 of its meaning.

- **D-09:** **Delete lives in the dialog**, not on the card. The grid stays legible and the destructive action requires an explicit intent, without needing a confirmation box — Phase 13's D-08 already makes deletion non-destructive to the uploaded image, and that reasoning holds wherever the control sits.

  Rejected: **delete on the card** — faster, but puts a destructive control in a dense grid whose neighbouring click is "enlarge", multiplying risky targets.

- **D-10:** **A superseded card shows what the frame actually renders** under the new name — often the generic fallback. The chip says "superseded" and the dialog explains that the operator's uploaded image is now orphaned (it was keyed on *their* name) and offers to re-place it under the correct one. **The gallery never lies about the current state** — that contract is what makes the grid trustworthy.

  Rejected: **showing the orphaned upload, dimmed** — more immediately expressive of what was lost, but the gallery would then assert something false about what the frame renders right now.

- **D-11:** **The table disappears, but a summary line remains** — *"4 manual resolutions, 1 superseded"* — clickable to filter the grid down to them. The chip alone would leave a superseded entry easy to miss among ~55 cards; this line is what makes it noticeable.

  Note: the page's existing filter bar (`data-filter-text` / `list-filter.js`) is the mechanism, so this costs no new machinery — put the chip's label into each card's `data-filter-text`.

  Rejected: **nothing at all, the filter suffices** — zero new UI, but the operator must know to type the word, and nothing announces a superseded entry.

### The JavaScript posture

- **D-12:** **Progressive enhancement.** A gap card's trigger is a real `<a href="/airlines?resolve=XQZ">` carrying the trigger attribute; with JS the script intercepts it and opens the dialog, without JS it navigates to Phase 13's page section, **which stays in place as the fallback**. Nothing is lost relative to Phase 13, and it matches the site's own designed-degradation ethos.

  This is cheap because `panel-lookup.js`'s delegation walks ancestors looking for the attribute — it never requires the trigger to be a `<button>`. An `<a>` needs only `preventDefault()`.

  Accepted cost: **a second rendering path to maintain and test.**

  Rejected: **simply inheriting the dependency** (a `<button>`, nothing opens without JS) — one rendering path, the Phase 13 section genuinely deleted, and consistent with illustration replacement which already requires JS. Rejected because resolving would become impossible without JS, a real regression from Phase 13.

- **D-13:** **`?resolve={prefix}` in the URL opens the dialog on page load, wherever the navigation came from.** Clicking *Resolve* on Health therefore lands the operator straight in the pop-up — the developer's original expectation, answered directly.

- **D-14 (supersedes an earlier answer in this same discussion — recorded, not hidden):** **After naming an airline, the dialog reopens by itself on the upload step.**

  Earlier in this discussion the developer chose the opposite: the card would change state and a second, deliberate click would reopen the dialog, keeping the script's contract that it *never* opens on load. D-13 then broke that contract, and the two could not both stand — Phase 13's redirect already carries `?resolve={prefix}` when artwork is still missing (verified live in `13-UAT.md`, test 8), so a load-time open on that parameter necessarily fires after naming too.

  Put back to the developer explicitly, they chose the single simple rule over the finer two-case one: **auto-open everywhere, the earlier answer withdrawn.** The planner must not reintroduce the "second click" behaviour thinking it was overlooked.

### Claude's Discretion

- **One rendering function for the resolve form, emitted in both places** (inside the dialog and inside the no-JS fallback section), so the two can never drift apart. This is discretion only in *how* it is factored — that they must not be two independent copies is not optional.
- All copy: the dialog's scope sentence required by D-01, the chip labels, the overflow line of D-07, the summary line of D-11, and the superseded explanation of D-10.
- Exact threshold and cap values behind D-06's locked shape.
- How the script distinguishes a gap trigger from an art trigger, and how it opens the dialog without an image (D-02) while staying backward-compatible with History.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The phase this one re-presents
- `.planning/phases/13-add-an-illustration-for-an-unidentified-flight-from-the-comp/13-CONTEXT.md` — the 14 locked decisions D-01..D-14 of Phase 13. **Still binding.** In particular its D-01 (resolution is per prefix), D-06 (static table wins, manual entry flagged), D-08 (delete never removes the image) and D-09 (`select_illustration()` untouched) constrain this phase.
- `.planning/phases/13-.../13-UAT.md` — the live-run evidence for how the flow actually behaves today, including the redirect that carries `?resolve=` (test 8) which D-14 above turns on. **Its two open gaps, G-01 and G-02, live in exactly this surface and this phase closes them.**
- `.planning/phases/13-.../13-REVIEW.md` — 11 non-blocking warnings still open; check whether any lands in the files this phase touches before adding new ones.

### The interaction pattern being joined
- `.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-CONTEXT.md` — D-20 and UI-SPEC §8.3, which chose a native `<dialog>` over a hand-rolled overlay and established the shared lightbox.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the living design system. Binding: chips, card treatment, spacing tokens, label voice, the data-table/data-cards pairing.

### Project-level constraints
- `.claude/CLAUDE.md` — GSD workflow enforcement; the stdlib-only server posture (no new dependency, and this phase should add no server code at all).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `companion/pages/airlines_page.py` — `_airline_card_html()` (line 494) emits `<div class="airline-card" data-filter-text=… data-filter-group=…>` wrapping a `<button class="airline-card__zoom">` that carries `data-view-panel-src`, `data-view-panel-caption` and `data-view-panel-replace-action`. **A gap card is this shape with a different trigger element (D-12), no image (D-02), and different attributes.**
- `companion/pages/airlines_page.py` — `_lightbox_html()` (line 601): one shared `<dialog class="lightbox lightbox--wide" id="panel-lookup-dialog">` holding, in order, image → caption → note → replace form → Close. D-03 adds the resolve form to that list.
- `companion/pages/airlines_page.py` — `_resolve_section_html()` (line 809) and `_known_airlines_datalist_html()` (line 793): Phase 13's server-derived Step A / Step B / already-done states. **D-12 keeps this alive as the no-JS fallback**, and its form should be the same rendering function the dialog uses.
- `companion/pages/airlines_page.py` — `_manual_resolution_*` (lines 956-1165): the table being absorbed. Its row-state logic (superseded, needs-artwork) is what moves onto the cards; do not re-derive it.
- `companion/static/panel-lookup.js` (134 lines) — ES5, no `Element.closest()`, no network call, delegated click on `[data-view-panel-src]`, `defer`-loaded so no `DOMContentLoaded` wrapper. Shared with History.
- `companion/static/list-filter.js` — the `[data-filter-input]`/`[data-filter-count]`/`[data-filter-clear]`/`[data-filter-empty]` contract D-11's summary line reuses.

### Established Patterns
- **Escape once, at the point of interpolation** (`T-06.6.4.1-05`) — every interpolated value in a card goes through `escape_html()` exactly once. Gap cards carry operator-adjacent data (a prefix and a callsign from live traffic); the same discipline applies.
- **Optional element, gracefully absent** — `panel-lookup.js` looks up `.lightbox__replace` *outside* its guard because History legitimately never renders it. D-03's second form joins that pattern rather than inventing one.
- **The script makes no network call, ever** — stated in its own header. Any design requiring the dialog to fetch its content is out of bounds.
- **Native `<dialog>` semantics are not re-implemented** — Escape-to-close, backdrop and focus trap come free, and the script's comment forbids adding a redundant handler. Do not add focus management.
- **`data-filter-group` counts distinct groups, not elements** — a gap card needs its own group to remain filterable.

### Integration Points
- `companion/pages/airlines_page.py` — gap-card rendering, the grid's head block, the chip and summary line, the dialog's second form, and the management-table removal.
- `companion/static/panel-lookup.js` — imageless open (D-02), form toggling (D-03), `<a>` interception (D-12), load-time open on `?resolve=` (D-13/D-14).
- `companion/pages/health_page.py` — the Resolve link's target; **no `<form>`, no `<button>`** on Health still holds from Phase 13's D-10.
- `companion/static/style.css` — the empty-card treatment and the chip variants.
- **`server/`** — untouched. This phase adds no server code.

</code_context>

<specifics>
## Specific Ideas

- The developer's reaction came from *seeing the page*, not from reading an artifact — and it identified an inconsistency that Phase 13's own UI-SPEC, its checker, and its verifier all passed over: the page already had the dialog, and already put the upload form inside it. **A UI contract for a page with an established interaction pattern should be checked against that pattern explicitly**, which `gsd-ui-checker` currently does not do. Worth fixing in the checker, not just in this phase.
- Twice during this discussion the developer asked for a question to be re-asked rather than accepting the first framing, and once asked for a decision to be restated before reconciling it. The conflicting pair (D-13 vs the earlier second-click answer) was surfaced rather than silently resolved. Keep that posture downstream: where this file records a supersession, it is deliberate.

</specifics>

<deferred>
## Deferred Ideas

- **A "+N more" overflow card** in the grid (rejected under D-07 in favour of a text line) — worth revisiting if the grid gains other card variants and one more stops feeling expensive.
- **Phase 13's G-01** — a rejected airline name reported to the operator as an empty one. It is copy in the surface this phase rewrites, so it should be fixed here rather than deferred again; recorded so it is not lost if the plan scopes it out.
- **A distinct visual treatment for manual cards** beyond the chip (rejected under D-08) — only if the chip proves too quiet in real use.
- **Retiring the no-JS fallback path** (kept by D-12) — if the second rendering path proves a genuine maintenance burden once built, dropping it is a one-line change and a later decision, not a silent one.

</deferred>

---

*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Context gathered: 2026-09-06*
