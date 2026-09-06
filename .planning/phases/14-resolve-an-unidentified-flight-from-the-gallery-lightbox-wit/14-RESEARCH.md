# Phase 14: Resolve an unidentified flight from the gallery lightbox, with coverage gaps as empty cards - Research

**Researched:** 2026-09-06
**Domain:** Server-rendered HTML (Python stdlib), vanilla ES5 progressive-enhancement JS, native `<dialog>` — no framework, no build step, no new dependency
**Confidence:** HIGH (this phase touches only this repository's own code; every mechanic below was read directly from the shipped files, not inferred)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The card's primary label is the example callsign (`XQZ411`), not the prefix — concrete and recognisable at a glance in a grid. Resolution is per 3-letter prefix; the dialog states that scope at the moment of acting. Rejected: prefix-first, both-at-equal-weight.
- **D-02:** A gap card's emptiness is drawn in CSS — no image at all. No asset, no network request. Mechanical consequence: `panel-lookup.js` triggers on `data-view-panel-src` and copies that `src` into the dialog's `<img>` — the script must learn to open the dialog without one, staying backward-compatible with History. Rejected: `generic-fallback.png`; the fallback, dimmed.
- **D-03:** Both forms live in the one shared dialog; the script shows the right one based on the clicked card's data attributes — extends the "optional element, gracefully absent" pattern already established for `.lightbox__replace`. Rejected: a second dedicated `<dialog>`.
- **D-04:** Gap cards live in the gallery grid itself, among the art, but bounded. Rejected: a dedicated sub-section; the same grid with everything shown.
- **D-05:** The gap block sits at the head of the grid, sorted by sighting count descending. Interleaving gaps alphabetically among airlines is incoherent and was not offered — a gap has no airline name yet.
- **D-06:** Two bounds together — a threshold (seen at least 3 times) and a hard cap (never more than 12 cards). Exact values are a UI-SPEC matter; the shape (threshold AND cap) is locked.
- **D-07:** A line below the block names what the cap hides, with the count and a link to Health — in the caption register the page already uses. Rejected: a "+N more" card; nothing at all.
- **D-08:** A manual origin is marked with a chip on the card, reusing `.airline-card__chip` — "resolved by hand", and "superseded" when the static table has taken over. Zero new component. Rejected: a distinct visual treatment; nothing on the card.
- **D-09:** Delete lives in the dialog, not on the card. Rejected: delete on the card.
- **D-10:** A superseded card shows what the frame actually renders under the new name — often the generic fallback. The chip says "superseded"; the dialog explains the orphaned upload and offers to re-place it. The gallery never lies about the current state. Rejected: showing the orphaned upload, dimmed.
- **D-11:** The table disappears, but a summary line remains ("4 manual resolutions, 1 superseded") — clickable to filter the grid down to them. Mechanism: the page's existing filter bar (`data-filter-text`/`list-filter.js`) — put the chip's label into each card's `data-filter-text`. Rejected: nothing at all, the filter suffices.
- **D-12:** Progressive enhancement. A gap card's trigger is a real `<a href="/airlines?resolve=XQZ">` carrying the trigger attribute; with JS the script intercepts it and opens the dialog, without JS it navigates to Phase 13's page section, which stays in place as the fallback. `panel-lookup.js`'s delegation already walks ancestors looking for the attribute — an `<a>` needs only `preventDefault()`. Accepted cost: a second rendering path to maintain and test. Rejected: simply inheriting the dependency (a `<button>`, nothing opens without JS).
- **D-13:** `?resolve={prefix}` in the URL opens the dialog on page load, wherever the navigation came from.
- **D-14 (supersedes an earlier answer in this same discussion):** After naming an airline, the dialog reopens by itself on the upload step. The planner must not reintroduce the "second click" behaviour thinking it was overlooked.

### Claude's Discretion

- One rendering function for the resolve form, emitted in both places (inside the dialog and inside the no-JS fallback section) — discretion only in *how* it is factored; that they must not be two independent copies is not optional.
- All copy: the dialog's scope sentence required by D-01, the chip labels, the overflow line of D-07, the summary line of D-11, and the superseded explanation of D-10.
- Exact threshold and cap values behind D-06's locked shape.
- How the script distinguishes a gap trigger from an art trigger, and how it opens the dialog without an image (D-02) while staying backward-compatible with History.

### Deferred Ideas (OUT OF SCOPE)

- A "+N more" overflow card in the grid (rejected under D-07 in favour of a text line) — worth revisiting if the grid gains other card variants.
- Phase 13's G-01 (a rejected airline name reported to the operator as an empty one) — copy in the surface this phase rewrites, so it should be fixed here rather than deferred again; recorded so it is not lost if the plan scopes it out.
- A distinct visual treatment for manual cards beyond the chip (rejected under D-08) — only if the chip proves too quiet in real use.
- Retiring the no-JS fallback path (kept by D-12) — if it proves a genuine maintenance burden once built, dropping it is a one-line change and a later decision, not a silent one.
</user_constraints>

## Summary

This is a pure absorption phase: Phase 13 built every piece of server-side machinery (the manual-resolution registry, the two POST routes, the fallback ladder) and this phase re-skins how the operator reaches it. Nothing in `server/` changes. The entire phase lives in three files — `companion/pages/airlines_page.py` (new gap-card rendering, dialog content, management-table removal), `companion/static/panel-lookup.js` (imageless open, form toggling, `<a>` interception, load-time open), and `companion/static/style.css` (the empty-card and chip treatment) — plus a small, load-bearing extension to `companion/static/list-filter.js` for D-11's clickable summary line that CONTEXT.md's Integration Points section does not call out explicitly (see Pitfall 5).

The riskiest single line of code in this phase is `image.src = src` in `panel-lookup.js`. A gap card has no image, and setting `<img src="">` is a documented browser gotcha (Safari/Chrome/pre-3.5-Firefox/IE all issue a spurious request — to the current page's own URL — when `src` is the empty string) that would violate the script's own "never a network call" header comment. The fix is a `removeAttribute("src")` (or leaving the attribute off entirely and toggling `hidden`) — not the pattern the script already uses for the image case that does have a value.

The second real risk is that `?resolve={prefix}` opening the dialog on page load (D-13/D-14) is a genuinely new trigger path — the existing code only ever opens the dialog from a click. `showModal()` on a native `<dialog>` still gives Escape-to-close, backdrop, and a focus trap for free regardless of what triggered the open, so the "do not add a redundant handler" comment in `panel-lookup.js` still holds — but the script must locate the right trigger element from the URL (not an event target) and must handle the case where no matching element exists in the DOM at all (the prefix already fully resolved, or capped out of the gap block by D-06). All of `_resolve_section_html()`'s server-derived state logic (Step A / Step B / already-done / stale) is reusable as-is; nothing about D-13/D-14 requires touching it.

**Primary recommendation:** Extend `panel-lookup.js`'s existing "optional element, gracefully absent" pattern (already used for `.lightbox__replace`) three more times — once for imagelessness (a presence check on the trigger's `data-view-panel-src` value, not just the attribute), once for the resolve/upload form pair (two more optional lookups, toggled via a data attribute on the trigger rather than by swapping DOM), and once for the delete control D-09 moves into the dialog. Do not invent a second dialog, a second script, or a second click-delegation mechanism — every one of D-02/D-03/D-09/D-12/D-13's needs fits the shape already established by quick tasks 260902-tli and 260903-btu.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gap-card rendering (label, chip, sort, cap, overflow line) | API/Backend (companion, server-rendered HTML) | — | `airlines_page.py` already owns every card in this grid; gap cards are the same tier, same file |
| Dialog content selection (which form(s) show for which trigger) | Browser/Client (`panel-lookup.js`) | API/Backend (server emits the data attributes and both forms' markup) | The toggle decision must happen client-side (one shared dialog, D-03) but the server is the only source of truth for *which* state a given prefix/airline is in — it renders the attributes, JS only reads them |
| Imageless dialog open (D-02) | Browser/Client (`panel-lookup.js`) | — | Purely a DOM-manipulation decision at click/load time; no new data crosses the wire |
| No-JS fallback form (D-12) | API/Backend (`_resolve_section_html()`, unchanged) | — | Already fully server-rendered; this phase's only obligation is to not let it drift from the dialog's copy of the same form |
| Load-time auto-open on `?resolve=` (D-13/D-14) | Browser/Client (`panel-lookup.js`, reads `location.search`) | API/Backend (server still decides Step A vs Step B vs already-done and puts that into the trigger's data attributes) | The URL is already server-validated once (`unresolved_row_for_prefix()` / `manual_resolutions` lookups inside `render()`); JS never re-validates, it only locates the DOM node the server already rendered for that prefix |
| Manual-resolution state (superseded / needs-artwork / active) | API/Backend (`_manual_resolution_rows()`, unchanged) | — | Pure server-side derivation already shipped in Phase 13; this phase only changes *where* it's displayed (chip + dialog instead of a table row) |
| Filter/summary interaction (D-11) | Browser/Client (`list-filter.js`, extended) | API/Backend (`data-filter-text` values) | Filtering itself is already client-side; making the summary line *drive* the filter input is a new client-side capability (see Pitfall 5) |
| Delete control (D-09) | API/Backend (existing POST route, unchanged) | Browser/Client (dialog must expose it) | The route (`MANUAL_DELETE_ROUTE_PREFIX`/`SUFFIX`) is untouched; only its entry point moves into the dialog |

## Package Legitimacy Audit

Not applicable. This phase adds no dependency of any kind — no `pip install`, no `npm install`, no new vendored library. Every file touched (`airlines_page.py`, `panel-lookup.js`, `list-filter.js`, `style.css`) is first-party code already in the repository. `companion/CLAUDE.md`'s stdlib-only posture is unaffected by construction; there is nothing for `gsd-tools query package-legitimacy check` to evaluate.

## Architecture Patterns

### System Architecture Diagram

```
GET /airlines?resolve=XQZ  (or plain GET /airlines)
        │
        ▼
companion/app.py: page_context()
  - resolve_prefix = raw query value (unvalidated)
  - manual_resolutions = load_manual_resolutions(state_dir)   [runtime JSON]
  - state_dir, now
        │
        ▼
airlines_page.render(ctx)
  ├─ unresolved_row_for_prefix(state_dir, prefix)   ──►  poll_state.json (unresolved_prefixes)
  ├─ unresolved_rows(state_dir)  [reused from health_page, already sorted count-desc]
  │        │
  │        ▼
  │   NEW: _gap_card_html() × up to 12, prepended to .illustration-grid
  │        each carries: data-view-panel-src="" (or absent-image sentinel),
  │        data-view-panel-caption=<callsign>, a resolve-state data attribute,
  │        and (D-12) a real <a href="/airlines?resolve={prefix}">
  │
  ├─ _manual_resolution_rows(state_dir, registry)   ──►  manual_resolutions.json
  │        │
  │        ▼
  │   EXISTING airline cards gain: chip ("resolved by hand" / "superseded"),
  │        data-filter-text including the chip label (D-11)
  │
  ├─ _lightbox_html()  — ONE shared <dialog>, now carrying:
  │        image (existing) │ caption (existing) │ note (existing)
  │        │ replace form (existing, art-card path)
  │        │ NEW: resolve-name form (Step A) — same render fn as _resolve_section_html()
  │        │ NEW: resolve-upload form (Step B) — same render fn as _resolve_section_html()
  │        │ NEW: delete form (D-09, manual-entry path)
  │        │ Close (existing)
  │
  └─ _resolve_section_html(ctx)  — UNCHANGED, stays the no-JS fallback (D-12)
        │
        ▼
Browser: companion/static/panel-lookup.js (defer-loaded on every page)
  - click on [data-view-panel-src] ancestor → existing delegation, EXTENDED:
        · imageless: image.removeAttribute("src") instead of image.src = ""
        · form toggle: show/hide the dialog's resolve-name / resolve-upload /
          delete forms based on the trigger's own data attributes
        · <a> trigger: preventDefault() before showModal() (D-12)
  - NEW: on script init, read location.search for `resolve=` — if a matching
    trigger element exists in the DOM, run the identical open logic that a
    click would have run; if none exists, do nothing (page's own rendered
    fallback section already tells the honest story)
```

### Recommended Project Structure

No new files. Every change lands inside the three existing files already named in CONTEXT.md's Integration Points, plus `companion/static/list-filter.js` (see Pitfall 5):

```
companion/
├── pages/
│   └── airlines_page.py     # gap-card rendering, dialog forms, chip/summary, table removal
├── static/
│   ├── panel-lookup.js      # imageless open, form toggle, <a> interception, load-time open
│   ├── list-filter.js       # NEW: external "set the filter query" hook for D-11's summary line
│   └── style.css            # empty-card visual, chip variants, dialog form-toggle CSS hooks
```

### Pattern 1: Optional element, gracefully absent (extend, don't reinvent)

**What:** `panel-lookup.js` already looks up `.lightbox__replace` *outside* its three-element mandatory guard (`image`/`caption`/`note`), precisely because History's own dialog never renders that form. Quick task 260903-btu's own comment states the rule explicitly: an optional lookup must never be folded into the mandatory guard's condition, or the whole script becomes a no-op on the page that legitimately lacks the element.

**When to use:** For every one of this phase's new dialog contents — the resolve-name form, the resolve-upload form, and D-09's delete form all belong in this same "optional, looked up once, used if present" bucket. History never renders any of them; Airlines renders zero, one, or (transiently, mid-navigation) two of the three depending on which card was clicked.

**Example (the exact precedent to extend):**
```javascript
// Source: companion/static/panel-lookup.js, lines 71-75 (existing)
// Quick task 260903-btu: optional, looked up once like the three
// above, but excluded from their guard on purpose — History's page
// never renders this form, and that is a legitimate, expected state,
// not a missing-element error.
var replaceForm = dialog.querySelector(".lightbox__replace");
```
The same shape, repeated for each new optional element (`.lightbox__resolve-name`, `.lightbox__resolve-upload`, `.lightbox__delete` or similar), each guarded independently at the point of use — never inside the mandatory `if (!image || !caption || !note)` check.

### Pattern 2: Attribute-copy, never markup-swap (the script's actual mechanism)

**What:** `panel-lookup.js` never re-renders content; it copies literal attribute values from the clicked trigger into pre-existing DOM slots (`image.src = src`, `caption.textContent = captionText`, `replaceForm.setAttribute("action", ...)`). This is deliberate — the script's own header states it "writes to element content only via textContent/src/alt/an attribute value — never via a raw-markup DOM sink of any kind."

**When to use:** D-03's "the script shows the right one" must be implemented as a *visibility toggle driven by a copied/read attribute*, not as injected HTML. Concretely: each trigger (gap card, art card, manual-entry card) carries a data attribute naming which of the (up to three) dialog forms is relevant — e.g. `data-view-panel-mode="resolve-name"` / `"resolve-upload"` / `"replace"` / `"none"` — and the click handler sets `hidden` on the non-matching forms and clears `hidden` on the matching one. No new markup is ever written into the dialog; the three forms are all rendered server-side, once, and the script only shows/hides pre-existing nodes exactly as it already does with the image element itself under Pitfall 1's fix.

**Example (the toggle this phase needs to add, following the existing idiom):**
```javascript
// Illustrative shape only — not existing code. Mirrors the existing
// replaceForm lookup/usage pattern above.
var resolveNameForm = dialog.querySelector(".lightbox__resolve-name");
var resolveUploadForm = dialog.querySelector(".lightbox__resolve-upload");
// ... inside the click handler, after the existing image/caption/replaceForm lines:
var mode = trigger.getAttribute("data-view-panel-mode") || "";
if (resolveNameForm) { resolveNameForm.hidden = (mode !== "resolve-name"); }
if (resolveUploadForm) { resolveUploadForm.hidden = (mode !== "resolve-upload"); }
```

### Pattern 3: Validate-then-join over server-derived state, never over the query string

**What:** Every existing seam in this codebase that touches operator-controlled input (`unresolved_row_for_prefix()`, `_serve_illustration_image()`, `_handle_manual_resolve_post()`) validates against a closed, server-controlled set and only then proceeds — never sanitizes-then-uses. `_resolve_section_html()` already re-derives Step A/B/already-done/stale purely from server state (`unresolved_row_for_prefix()`, `manual_resolutions.load_manual_resolutions()`, `illustrations.resolved_illustration_path()`), never from the raw `resolve_prefix` value past the first membership check.

**When to use:** The dialog's auto-open (D-13) must not re-implement this validation client-side. `location.search`'s `resolve=` value is used **only** to find a DOM element the server already rendered (i.e., `document.querySelector('[data-resolve-prefix="' + value + '"]')` or equivalent) — if no such element exists, the script does nothing, and the page's own already-rendered fallback section (server-validated) is what the operator sees. The script never itself decides whether a prefix is live, resolved, or stale — that determination is baked into whether a matching trigger element exists in the DOM at all.

### Anti-Patterns to Avoid

- **A second `<dialog>` for gap cards.** Rejected explicitly by D-03. Two dialog ids means the delegated click handler must choose which one to open — strictly more logic, and the whole "shared lightbox" premise the developer's own feedback is built on evaporates.
- **`image.src = ""` for the imageless case.** A documented cross-browser bug class (Safari, Chrome, IE, and Firefox <3.5 all issue a request when `<img src="">` is set — see Pitfall 1) that would put a network call into a script whose own header comment forbids one.
- **Injecting HTML into the dialog at click time.** `panel-lookup.js`'s header comment is explicit that it "writes to element content only via textContent/src/alt/an attribute value — never via a raw-markup DOM sink of any kind" — this is a standing constraint, not a style preference, and any design requiring `innerHTML` here is out of bounds.
- **Client-side re-validation of the resolve prefix.** Threat `T-v26-02-01`'s validate-then-join property (Phase 13's central security concern) is a server-side property. JS must never decide "is this prefix real" — it only decides "does a matching, server-rendered element exist on this page."
- **Duplicating the resolve-form markup between the dialog and the no-JS section.** Explicitly locked in Claude's Discretion: "One rendering function for the resolve form, emitted in both places... this is discretion only in *how* it is factored — that they must not be two independent copies is not optional."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal focus trap / Escape-to-close | A custom keydown handler or focus-trap library | Native `<dialog>` + `showModal()` (already in place) | `panel-lookup.js`'s own comment forbids adding a redundant handler — the browser already does this for every dialog, regardless of what triggered the open (click or load-time) |
| CSRF protection on the delete/resolve POSTs | A hidden CSRF token field | `SameSite=Strict` session cookie (already this site's whole CSRF control, `companion/auth.py:132`) | Locked precedent from Phase 13's own canonical refs; a new state-changing form in the dialog follows the same posture, not a second mechanism |
| Filtering/search-count logic for the gap+chip cards | A second filter script or a per-page reimplementation | `list-filter.js`'s existing `data-filter-text`/`data-filter-group` contract, extended (not replaced) for D-11 | The distinct-group counting already exists and already handles heterogeneous card shapes on one page (History's paired `<tr>`/`<li>`); gap cards are just another group |
| Sorting the gap block by sighting count descending | A new sort function in `airlines_page.py` | `health_page.unresolved_rows()`'s existing sort (`rows.sort(key=lambda row: (-row[1], row[0]))`) — reuse or duplicate the identical key, don't invent a new order | Already exactly what D-05 asks for: count descending, prefix ascending as the tiebreak |

**Key insight:** Every mechanism this phase needs already exists in the codebase in a slightly narrower form (one optional dialog form, one non-image trigger case does not yet exist, one filter-bar contract). The work is extension, not invention — and every extension has a named, load-bearing precedent to copy from (quick tasks 260902-tli and 260903-btu specifically), which is why the CONTEXT.md's own governing note calls this "cheap."

## Common Pitfalls

### Pitfall 1: `image.src = ""` for a gap card silently reintroduces a network call

**What goes wrong:** The existing click handler unconditionally does `image.src = src;` where `src = trigger.getAttribute("data-view-panel-src") || ""`. If a gap card's trigger carries `data-view-panel-src=""` (empty but present, which the click-delegation's `hasAttribute()` check requires it to be, to remain a valid trigger at all), this line sets the `<img>`'s `src` attribute to the empty string.

**Why it happens:** `<img src="">` is not "no image" to a browser — per MDN and multiple independent write-ups, Safari and Chrome resolve the empty string against the current document URL and issue a GET request for the page itself; Internet Explorer requests the containing directory; only Opera and Firefox ≥3.5 no-op. This is exactly the kind of request the script's own header comment ("this file must never introduce a network call... of any kind") forbids, and it would happen silently, once per gap-card open, with no visible symptom beyond wasted server load and a possibly-broken-image icon.

**How to avoid:** Branch on whether the trigger actually carries a non-empty `data-view-panel-src`. When it doesn't: `image.hidden = true; image.removeAttribute("src"); image.removeAttribute("alt");` (removing the attribute, not setting it to `""`, is what avoids the request — MDN's own image-loading conditions list "when the src or srcset attributes are empty" as a display-only failure state, but the *request* behavior is specifically triggered by the empty-string *value*, not by the attribute's absence). When it does carry a value, restore `image.hidden = false;` before setting `src`/`alt` as today. `.lightbox__image[hidden]` needs no new CSS rule — `style.css` never overrides `[hidden]` for a bare element selector (only `.dirty-bar[hidden]` and `.refresh-pill[hidden]` get bespoke treatment), so the UA default `display: none` applies unmodified.

**Warning signs:** A server access log showing repeated `GET /airlines?resolve=...` or `GET /airlines` hits with no corresponding page-view pattern (i.e., the same client re-requesting the page it's already on) right after a gap-card click.

### Pitfall 2: Auto-opening on load races the dialog against a form the operator hasn't seen change

**What goes wrong:** D-13/D-14 mean `showModal()` can fire with no user gesture at all — straight off a server redirect after Step A's POST. If the click-handler logic that sets up the dialog's contents (image/caption/form-toggle) is only ever wired to a `click` listener, the load-time path has nothing to read a "trigger" from, because there was no click event.

**Why it happens:** The existing script has exactly one path into "populate the dialog and open it": `document.addEventListener("click", ...)`. D-13 needs a second entry point that performs the *identical* population logic against a trigger discovered from `location.search` instead of `evt.target`.

**How to avoid:** Factor the "populate dialog from a trigger element, then `showModal()`" logic into one function taking a trigger node as its only argument; call it from the click handler (`findTriggerAncestor(evt.target)`) and, once at script init, from a `location.search`-derived lookup — never duplicate the population logic itself. Guard the second call: if `location.search` carries no `resolve` param, or no element in the DOM matches it, do nothing (this covers the "already fully resolved, card gone" fourth state `_resolve_section_html()`'s own docstring already documents as reachable).

**Warning signs:** The dialog opens but shows a stale or empty caption/image, or the wrong form is visible, specifically only on the load-triggered path (a manual click on the same card works fine) — a sign the two code paths drifted apart.

### Pitfall 3: `autofocus` inside a form that starts `hidden` does nothing useful

**What goes wrong:** The existing Step A form's name input carries a literal `autofocus` attribute (`_resolve_section_html()`, line ~881). If both the resolve-name and resolve-upload forms are always present in the dialog's DOM and only toggled via `hidden`, and the dialog opens on the upload step (D-14's reopen-on-upload-step case), the browser's native `showModal()` focus algorithm — first element carrying `autofocus`, else first focusable element — would still look for `autofocus` inside a form that's `hidden`. A `hidden`/`display:none` element cannot receive focus, so the browser will correctly skip it and fall through to the next focusable element instead (verified: MDN's dialog documentation states the fallback is "the first nested focusable element", and a non-rendered element is definitionally not focusable) — but only if the intended target (the upload `<input type="file">`) is the *next* focusable thing in DOM order once the hidden form is skipped.

**Why it happens:** Autofocus interacts with the DOM tree, not with "the form the developer currently cares about." If a future edit reorders the three optional forms, or leaves both forms' `autofocus`-worthy controls simultaneously visible, the wrong control gets focus and D-14's polish ("the dialog reopens by itself on the upload step") reads as one visible field getting focus while a different one shows the cursor blinking, or as focus landing on Close instead.

**How to avoid:** Give each optional form's own primary control an `autofocus` attribute, and ensure the toggle logic sets `hidden` before `showModal()` runs (never after) so the browser's one-time focus placement, which happens synchronously during `showModal()`, sees the final visible state. Do not rely on `autofocus` working correctly if a form is un-hidden after `showModal()` already ran.

**Warning signs:** Keyboard-only testing (Tab from a fresh open) lands somewhere other than the field the developer expects; visually the correct form is showing but the browser's focus ring is elsewhere or absent.

### Pitfall 4: Gap-card `data-filter-group` colliding with airline-card indices

**What goes wrong:** `_gallery_grid_html()` currently assigns `data-filter-group` via `enumerate(pairs)` — plain integers `0..len(pairs)-1`. If gap cards are prepended using the same integer sequence (or their own `0..11`), `list-filter.js`'s group-counting (`group = "g" + (group === null ? "i" + i : group)`) will treat a gap card and an unrelated airline card as the *same* group whenever their raw index values collide, silently under-counting the "N of M shown" total and potentially hiding one card's visibility toggle behind the other's.

**Why it happens:** `data-filter-group`'s value is just a string key from the script's point of view — nothing enforces uniqueness across heterogeneous card types on the same page today because, until this phase, only one card type (`_airline_card_html()`) has ever populated this attribute on the Airlines page.

**How to avoid:** Give gap cards their own distinct group-value namespace, e.g. a string prefix (`"gap0"`, `"gap1"`, ...) rather than reusing the airline cards' raw integer sequence — `data-filter-group` accepts any string, and the script's `"g" + group` concatenation never assumes it is numeric.

**Warning signs:** The filter-bar's "N of M shown" count is off by exactly the number of gap cards present, or clicking a gap card affects an unrelated airline card's visibility.

### Pitfall 5: D-11's "clickable to filter" summary line has no existing hook to drive

**What goes wrong:** D-11 requires a summary line ("4 manual resolutions, 1 superseded") that is "clickable to filter the grid down to them." `list-filter.js` today exposes exactly four attributes — `[data-filter-input]`, `[data-filter-count]`, `[data-filter-clear]`, `[data-filter-empty]` — and no mechanism for an element *elsewhere on the page* to programmatically set the filter input's value and re-run `applyFilter()`. CONTEXT.md's Integration Points section does not list `list-filter.js` as a file this phase touches, but D-11's own locked wording cannot be satisfied without either modifying it or settling for a materially weaker interpretation (e.g., a plain scroll-to/focus link with no actual filtering).

**Why it happens:** `list-filter.js` was built for exactly one interaction — typing into `[data-filter-input]` — and has never needed an externally-driven "set this filter and apply it" entry point before, because no page has previously wanted a link elsewhere to pre-fill the search.

**How to avoid:** This needs a small, explicit extension mirroring the file's own existing conventions — e.g. a `[data-filter-set]` attribute on the summary line's clickable element, read once at script init the same way `[data-filter-clear]` is, wired to set `input.value` and call `applyFilter()` on click. This is shared with History (same script, same guard-on-`[data-filter-input]`-absence pattern), so the change must degrade identically to every other optional lookup in this file: a page without `[data-filter-set]` present is unaffected. Flag this explicitly to the planner — it is a real `list-filter.js` edit that CONTEXT.md's own Integration Points list does not name, alongside the two files it does.

**Warning signs:** The summary line renders and is clickable but nothing happens on click, or (if implemented as a plain link into `?filter=...`) the filter input never reflects a value that survived a page reload — `list-filter.js` reads no query string today.

### Pitfall 6: `_manual_resolution_rows()`'s `needs_artwork` derivation must stay the single source for both the chip and the dialog's Step B decision

**What goes wrong:** Today `_manual_resolution_rows()` computes `superseded`/`needs_artwork` once, server-side, and both `_manual_resolution_row_html()` (desktop) and `_manual_resolution_cards_html()` (mobile) consume the identical tuple. If the gap-card/chip rendering path recomputes "does this airline need artwork" independently (e.g. by re-calling `illustrations.resolved_illustration_path()` at a different call site with slightly different arguments), a future edit to one call site and not the other reintroduces exactly the kind of drift `_manual_resolution_rows()`'s own docstring was written to prevent.

**How to avoid:** Thread the same `(prefix, airline_name, created_at, superseded, needs_artwork)` tuples this function already returns into the new card-chip renderer, rather than re-deriving any of the three booleans a second time.

## Code Examples

### Existing delegated-click contract (extend this, verbatim shape)
```javascript
// Source: companion/static/panel-lookup.js (existing, lines 92-115)
document.addEventListener("click", function (evt) {
  var trigger = findTriggerAncestor(evt.target);
  if (!trigger) {
    return;
  }
  var src = trigger.getAttribute("data-view-panel-src") || "";
  var captionText = trigger.getAttribute("data-view-panel-caption") || "";
  image.src = src;
  image.alt = captionText;
  caption.textContent = captionText;
  if (replaceForm) {
    var replaceAction = trigger.getAttribute("data-view-panel-replace-action") || "";
    replaceForm.setAttribute("action", replaceAction);
  }
  dialog.showModal();
});
```

### Existing server-side sort this phase's D-05 should reuse (already exists, do not reinvent)
```python
# Source: companion/pages/health_page.py, unresolved_rows() (existing)
rows.sort(key=lambda row: (-row[1], row[0]))
return rows
```

### Existing "optional element, gracefully absent" pattern (the template for D-03/D-09's new forms)
```javascript
// Source: companion/static/panel-lookup.js, lines 71-75 (existing)
var replaceForm = dialog.querySelector(".lightbox__replace");
```

### Existing server-derived Step A/B/already-done/stale branching (unchanged, reused by the dialog)
```python
# Source: companion/pages/airlines_page.py, _resolve_section_html() (existing)
# Reads row = unresolved_row_for_prefix(state_dir, prefix_raw); falls through
# to manual_resolutions.load_manual_resolutions(state_dir) when the live gap
# is already gone (CR-02 fix) — this whole derivation is untouched by D-13,
# only WHERE its output is displayed changes.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Standalone "Manually resolved prefixes" management table (`_manual_resolutions_section_html()`, desktop table + mobile card list) | Absorbed into `.airline-card__chip` chips plus one summary line, delete moved into the shared dialog | This phase (D-08/D-09/D-11) | The table's row-state logic (`_manual_resolution_rows()`) is preserved verbatim; only its display surface changes |
| Coverage-gap resolution reached only via Health's per-row `Resolve` deep link, landing on a page-section (Phase 13) | Also reachable as an empty card directly in the Airlines grid, opening the shared lightbox (this phase, D-01 through D-07) | This phase | Health's deep link (`/airlines?resolve={prefix}`) is unchanged and still works — it is now also the URL a load-time auto-open (D-13) fires from |
| `panel-lookup.js` opens the dialog only from a `click` event | Also opens from a `location.search`-derived lookup at script init (D-13) | This phase | First non-click entry point into this script since it shipped; the population logic must be factored so both paths share it (Pitfall 2) |

**Deprecated/outdated:** The standalone management table's HTML structure (`_manual_resolution_table_html()`, `_manual_resolution_cards_html()`, `_manual_resolution_row_html()`) becomes dead code once the chip/summary-line/dialog-delete replacement ships — the row-state derivation function (`_manual_resolution_rows()`) survives, only its two rendering functions are retired.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `<img src="">` triggers a spurious request in Safari/Chrome/IE and is a no-op only in Opera and Firefox ≥3.5 | Pitfall 1 | If the target browser set behaves differently than these sources report, the severity of the fix (removeAttribute vs. leaving src empty) may be overstated — but `removeAttribute("src")` is strictly safer regardless, so the recommendation holds even if the risk model is imprecise. Sourced from MDN plus two independent technical write-ups (Human Who Codes, Ben Nadel) — [CITED] |
| A2 | `showModal()`'s focus algorithm skips a `hidden`/non-rendered element even if it carries `autofocus`, falling through to the next focusable element | Pitfall 3 | If a browser instead focuses nothing at all (or throws), D-14's reopen-on-upload-step polish could silently fail to focus the file input; low risk since this is standard, long-shipped `<dialog>` behavior, but not independently verified against every real browser in this session — [CITED: MDN dialog docs] |
| A3 | `data-filter-group`'s value can be any string (not required to be numeric) without breaking `list-filter.js`'s existing counting logic | Pitfall 4 | Directly read from the script's own source (`"g" + (group === null ? "i" + i : group)"` — a string concatenation, never parsed as a number) — [VERIFIED: companion/static/list-filter.js read directly] |
| A4 | D-11's "clickable to filter" requires a genuine `list-filter.js` extension rather than being satisfiable with existing attributes alone | Pitfall 5 | If the planner instead settles for a weaker interpretation (a plain anchor with no live filtering), this assumption is moot but the locked decision's own wording ("clickable to filter the grid down to them") reads as requiring the stronger behavior — [VERIFIED: list-filter.js's four-attribute contract read directly, no fifth hook exists] |

## Open Questions

1. **Exact shape of the trigger's "mode" attribute for D-03's form toggle**
   - What we know: the toggle must be driven by a data attribute the server renders per-card (gap-name vs. gap-upload vs. art-card vs. manual-entry-with-delete), read by the script at click/load time, mirroring the existing `data-view-panel-replace-action` precedent.
   - What's unclear: the exact attribute name(s) and value vocabulary — this is explicitly listed under CONTEXT.md's Claude's Discretion ("How the script distinguishes a gap trigger from an art trigger").
   - Recommendation: name it plainly (e.g. `data-view-panel-mode` with values `"art"` / `"resolve-name"` / `"resolve-upload"` / `"manual"`) and drive every visibility toggle off that single attribute rather than inferring mode from the presence/absence of other attributes — keeps the script's logic a single, readable branch.

2. **Whether the gap-card's `<a href>` and the dialog's resolve forms need a distinct `data-resolve-prefix` attribute, or reuse `data-view-panel-caption`**
   - What we know: the caption attribute today carries display text (e.g., an alt-text-shaped string like `"Air France illustration"`), not a raw prefix value suitable for a `location.search` lookup key.
   - What's unclear: whether load-time auto-open (D-13) should match on the prefix directly (a new attribute) or derive it from the existing `href`/`action` values already present on the trigger.
   - Recommendation: add a dedicated `data-resolve-prefix` (or similar) attribute for exact-match lookup against `location.search`'s `resolve` value — deriving a prefix by parsing another attribute's URL is more fragile and duplicates the query-param name in two unrelated string shapes.

3. **Does the dialog need a `data-filter-group`-free, drift-guard-equivalent cross-file pin the way `LIGHTBOX_DIALOG_ID`/`_VIEW_PANEL_*_ATTR` already are pinned between `airlines_page.py`/`history_page.py`/`panel-lookup.js`?**
   - What we know: the existing three cross-file guards (`_airlines_lightbox_constants_match_history()`, `_lightbox_dom_contract_three_file_guard()`) exist specifically because a drift here fails silently otherwise.
   - What's unclear: whether this phase's new attribute names need the identical treatment (likely yes, given the project's own established discipline), and whether History's own dialog needs an explicit "never gains this" pairs-tuple exclusion the way `LIGHTBOX_REPLACE_FORM_CLASS` already has one.
   - Recommendation: plan a parallel guard test for every new constant this phase introduces, following the exact shape of `test_view_pages.py`'s existing `_lightbox_dom_contract_three_file_guard()`.

## Environment Availability

Skipped — this phase has no external dependency beyond the project's own already-running companion service. No new tool, service, runtime, or CLI is introduced; every file touched already exists and is already served by the running `companion/app.py` process.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python stdlib `unittest`-style harness with a local `check(name, fn)` runner (no pytest, no third-party test framework) — see `companion/test_view_pages.py`/`companion/test_status_pages.py` |
| Config file | none — plain `python -m companion.test_view_pages` / aggregated via `scripts/run-all-tests.sh` |
| Quick run command | `python -m companion.test_view_pages` (renders `airlines_page.render(ctx)` against fixtures, asserts on the returned HTML string) |
| Full suite command | `scripts/run-all-tests.sh` (the project's one aggregate 9+-harness runner, per Phase 4's D-09) |

### Phase Requirements → Test Map

This phase has `requirements: []` (unmapped presentation follow-up, matching the Phase 10-13 precedent) — the map below traces to CONTEXT.md's locked decisions (D-01..D-14) instead of REQ-IDs, mirroring how `06.6.4.1-CONTEXT.md`'s own decimal-phase decisions were traced.

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01/D-02 | Gap card renders callsign label, no `<img>` markup, a real `<a href>` trigger | render-string assertion | `python -m companion.test_view_pages` (new `check()` case) | ❌ Wave 0 |
| D-05/D-06 | Gap block sorted count-desc, capped at N, threshold applied | render-string assertion over a seeded `poll_state.json` fixture | same harness | ❌ Wave 0 |
| D-07 | Overflow line renders exact count + Health link when cap bites | render-string assertion | same harness | ❌ Wave 0 |
| D-08/D-10 | Chip renders "resolved by hand"/"superseded" per `_manual_resolution_rows()`'s existing booleans | render-string assertion, reusing existing fixture-seeding helpers | same harness | ❌ Wave 0 |
| D-11 | Summary line count matches registry; `data-filter-text` includes chip label | render-string assertion | same harness | ❌ Wave 0 |
| Cross-file dialog contract (new attributes) | Every new `data-view-panel-*`/class token appears in both `panel-lookup.js`'s source and the rendered page | source+render string assertion, mirroring `_lightbox_dom_contract_three_file_guard()` | same harness | ❌ Wave 0 (new guard, template exists) |
| D-02 imageless open, D-03 form toggle, D-09 delete-in-dialog, D-13/D-14 load-time auto-open, focus placement | actual browser behavior — click delegation firing, `hidden` toggling, `showModal()` timing, `location.search` parsing, keyboard focus | manual-only | none — no headless browser in this project's toolchain | N/A — genuinely unautomatable with the current harness |

**What the stdlib `check()` harness genuinely can assert:** the exact HTML string `render(ctx)` produces (element counts, attribute values, class names, text content) and the exact text of the raw `.js`/`.css` source files (token presence via substring/regex search, as `_lightbox_dom_contract_three_file_guard()` already does for `panel-lookup.js`). This is real, valuable coverage for every server-rendered piece of this phase (D-01, D-02's markup half, D-05 through D-11).

**What it cannot assert, at all:** anything that requires a JavaScript engine actually executing `panel-lookup.js` against a live DOM — the click delegation firing, `image.hidden`/`removeAttribute` actually suppressing a request, the dialog's native focus placement, `showModal()` actually opening on page load, or `list-filter.js`'s new external-set hook actually re-filtering the grid. Phase 13's own `13-UAT.md` hit this exact wall for its `<datalist>` popup (G-02, still open) — this phase inherits the identical limitation, now for a materially larger surface (every D-02/D-03/D-09/D-13/D-14 behavior lives entirely in the browser). Treat every one of those as manual-only with no escape hatch, exactly as Phase 13's VALIDATION.md already precedents for the one row it had.

### Sampling Rate
- **Per task commit:** `python -m companion.test_view_pages` (fast, targets the one module this phase touches most)
- **Per wave merge:** `scripts/run-all-tests.sh`
- **Phase gate:** Full suite green before `/gsd-verify-work`, **plus** a mandatory manual/browser pass covering every row in the "manual-only" table above before the phase can be considered done — this is not optional given how much of this phase's actual behavior (D-02/D-03/D-09/D-13/D-14) is unautomatable by construction.

### Wave 0 Gaps
- [ ] New `check()` cases in `companion/test_view_pages.py` for D-01/D-02/D-05/D-06/D-07/D-08/D-10/D-11's render-string assertions
- [ ] A new cross-file dialog-contract guard (mirroring `_lightbox_dom_contract_three_file_guard()`) for every new `data-view-panel-*` attribute and `lightbox__*` class this phase introduces
- [ ] No framework install needed — the existing harness pattern covers everything server-rendered; the gap is entirely in what a browser must confirm, not in tooling

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged — this phase adds no new authentication surface; every route it touches already sits behind the existing session gate |
| V3 Session Management | no | `SameSite=Strict` cookie, unchanged |
| V4 Access Control | no | No new role/permission concept; same single-operator session model as every other companion route |
| V5 Input Validation | yes | The dialog's resolve-name/resolve-upload/delete forms POST to the *identical, unmodified* routes Phase 13 already hardened (`RESOLVE_ROUTE`, `MANUAL_DELETE_ROUTE_PREFIX/SUFFIX`, `_handle_illustration_replace()`'s membership gate) — this phase changes nothing about validation, only the click path that reaches the same `<form>` markup |
| V6 Cryptography | no | Unaffected |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A prefix or key reaching `illustrations.py`'s path-construction functions from an unvalidated source | Tampering | Already fully mitigated by Phase 13's D-11 validate-then-join (`unresolved_row_for_prefix()`); this phase must not introduce a *new* path into those functions — the dialog's forms POST to the same routes, with the same server-side re-validation, regardless of which UI element triggered the submit |
| A gap-card trigger's `data-view-panel-src`/`data-resolve-prefix` attribute being treated as trusted by the script and echoed into a form action without escaping | Tampering (client-side) | Not a real risk here specifically because the value is server-rendered (already passed through `escape_html()` once at the point of interpolation, per this codebase's T-06.6.4.1-05 discipline) before it ever reaches the DOM attribute the script reads — the script only ever copies an already-escaped, already-server-controlled string between DOM slots, never accepts operator-typed input directly |
| Spurious/unintended HTTP requests from client-side markup (the `<img src="">` gotcha) | Denial of Service (minor, self-inflicted) | See Pitfall 1 — `removeAttribute("src")` rather than `src = ""` |
| Load-time `showModal()` firing on a page an operator did not intend to auto-act on (a shared/bookmarked `?resolve=` URL) | Tampering / social-engineering surface, low severity | The dialog's forms still require an explicit submit — auto-*opening* the dialog is not auto-*submitting* anything, so this is a UX consideration (surprise), not a security one; no mitigation beyond what already exists (session-gated page, POST-only state changes) |

## Sources

### Primary (HIGH confidence)
- `companion/pages/airlines_page.py` (read in full, 1220 lines) — every server-side rendering function this phase extends or retires
- `companion/static/panel-lookup.js` (read in full, 134 lines) — the exact click-delegation contract and its own standing-constraint comments
- `companion/static/list-filter.js` (read in full, 101 lines) — the exact filter-bar contract and its four-attribute surface
- `companion/pages/health_page.py` (relevant sections read) — `unresolved_rows()`'s existing sort, the Resolve deep-link constants, `_READ_ONLY_NOTE`
- `server/plane/manual_resolutions.py` (read in full) — `entry_rows()`, `normalise_prefix()`, the registry's own validation posture
- `server/plane/enrich.py`, `server/plane/illustrations.py` (relevant functions read) — `static_airline_name_for_prefix()`, `resolved_illustration_path()`, `target_airline_names()`
- `companion/app.py` (relevant sections read) — `page_context()`'s `resolve_prefix`/`manual_resolutions` wiring, the POST dispatch table
- `companion/static/style.css` (relevant sections read) — `.airline-card`, `.lightbox`/`.lightbox--wide`, `.airline-card__chip`, `.manual-resolution__status--superseded`, `[hidden]` usage audit
- `companion/test_view_pages.py` (relevant sections read) — the exact `check()`/cross-file-guard test idiom this phase's own tests must follow
- `.planning/phases/14-.../14-CONTEXT.md` — the 14 locked decisions this research is scoped against
- `.planning/phases/13-.../13-CONTEXT.md`, `13-UAT.md` — the still-binding Phase 13 decisions and live-run evidence (including gaps G-01/G-02)
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the current design-system contract (cards, chips, label voice, spacing tokens)

### Secondary (MEDIUM confidence)
- MDN, `<dialog>` element / `autofocus` global attribute — `showModal()`'s focus-placement algorithm (used for Pitfall 3)
- MDN, `<img>` element — the documented display-failure conditions for an empty `src`
- Human Who Codes ("Empty image src can destroy your site") and Ben Nadel ("Empty SRC And URL() Values Can Cause Duplicate Page Requests") — cross-browser corroboration of the empty-`src` request behavior (used for Pitfall 1)

### Tertiary (LOW confidence)
- None — every claim in this document is either read directly from this repository's own source or corroborated by an official/authoritative external reference (MDN).

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new stack, this is a pure extension of existing first-party code
- Architecture: HIGH — every pattern cited was read directly from the shipped files, not inferred from documentation
- Pitfalls: HIGH for the code-mechanics pitfalls (1, 2, 4, 6 — read directly from source); MEDIUM for the two browser-platform pitfalls (3, and the `<img src="">` behavior in Pitfall 1) since they rest on external documentation rather than an in-session browser test

**Research date:** 2026-09-06
**Valid until:** No expiry driver — this phase touches only first-party code with no version-drift risk; re-research only if the underlying `panel-lookup.js`/`airlines_page.py` shapes change before this phase is planned/executed
