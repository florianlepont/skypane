---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - companion/app.py
  - companion/pages/airlines_page.py
  - companion/static/list-filter.js
  - companion/static/panel-lookup.js
  - companion/static/style.css
  - companion/test_companion_app.py
  - companion/test_status_pages.py
  - companion/test_view_pages.py
  - .gitignore
findings:
  critical: 1
  warning: 4
  info: 0
  total: 5
status: resolved
resolved: 2026-09-06
resolution_commits:
  - "0963ccb — CR-01: .lightbox__image scoped with :not([hidden])"
  - "ac6a9f6 — WR-01: ?resolve= escaped with CSS.escape() before use in a selector"
  - "ad186c7 — WR-02/WR-03: single manual-registry read per render; type-safe example_callsign"
  - "739fbea — WR-04: manual-card injection guarded against a future unkeyable name (kept as defence in depth after tracing the scenario as unreachable via the one real loader today)"
---

# Phase 14: Code Review Report

**Reviewed:** 2026-09-06
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found, all 5 resolved same-day (see `resolution_commits` above)

## Summary

Reviewed the folding of Phase 13's standalone resolve-flow page into the Airlines gallery's shared lightbox, at diff base `f12ab47`. Confirmed `server/` is untouched (`git diff --stat f12ab47..HEAD -- server/` is empty), so the phase's stated server-side non-goal holds.

The two on-glass fixes the phase context asked me to re-derive (the `:not([hidden])` CSS-specificity fix, and the manual-registry exclusion in `_gap_rows_for_grid()`) are both real and correctly reasoned as far as they go, but neither is complete:

- The CSS-specificity fix scoped `.lightbox__replace`, `.lightbox__resolve-name`, `.lightbox__delete`, `.lightbox__replace-zone`, and `.resolve-upload-zone` to `:not([hidden])`, but **missed `.lightbox__image` itself** — the exact element `panel-lightbox.js`'s new gap-mode `image.hidden = true` branch (introduced by this same phase) depends on. This is the identical bug class, on the identical mechanism, left unfixed on one more element. See CR-01.
- The manual-registry exclusion in `_gap_rows_for_grid()` correctly stops the *stale-poll-state* dual-render case it was written for, but the render path still has two other ways a prefix can become invisible or re-duplicate: a narrow read/read race between `page_context()`'s and `_gap_rows_for_grid()`'s independent loads of `manual_resolutions.json` (WR-02), and a card-injection path with no defence against a manual entry whose name no longer slugs to a valid illustration key (WR-04) — the same "corrupt/drifted state" class `_resolve_section_html()` already explicitly guards against, but that guard was not carried into `render()`'s injection loop.

Escaping discipline (`escape_html()` exactly once, at the point of interpolation) was checked across every new/changed function in `airlines_page.py` (`_gap_rows_for_grid`, `_gap_card_html`, `_gap_overflow_html`, `_resolve_context_html`, `_resolve_name_form_html`, `_resolve_upload_form_html`, `_manual_delete_form_html`, `_lightbox_html`, `_airline_card_html`) and found compliant — no double-escaping, no un-escaped interpolation of live-traffic or operator-typed data.

`panel-lookup.js`'s no-network-call invariant holds (`image.src = ""` does not appear; every `src` write is gated on a truthy value, with `removeAttribute` used otherwise). The shared-render-function contract (one definition, two call sites, no drift) holds for the resolve-name, resolve-upload, and delete forms. `data-filter-group` namespacing between gap cards (`"gap%d"`) and curated/injected cards (`"%d"`) is collision-safe. The `[data-filter-set]` hook is only ever emitted with the fixed literal `"manual"`. The `.gitignore` addition is correctly scoped (`/server/.venv`, no trailing slash, root-anchored) and touches nothing else. The `?resolve=` auto-open path performs no server round-trip and changes no state, so the `SameSite=Strict` CSRF posture is unweakened.

One WARNING (WR-01) is a real, if low-impact, DOM-selector-injection bug: `panel-lookup.js`'s load-time auto-open builds a `document.querySelector()` attribute-selector string by direct concatenation of the unsanitized `?resolve=` query value.

## Critical Issues

### CR-01: `.lightbox__image` is not scoped to `:not([hidden])`, so the gap-mode dialog fails to hide its (empty) image

**File:** `companion/static/style.css:4340` (rule), consumed from `companion/static/panel-lookup.js:152-162`

**Issue:** This phase's own `14-08 on-glass fix` commit found and fixed exactly this bug class for `.lightbox__replace`, `.lightbox__resolve-name`, `.lightbox__delete` (style.css:4483-4485) and for `.lightbox__replace-zone`/`.resolve-upload-zone` (style.css:4522-4523): an unscoped `display: block`/`display: flex` author rule beats the user-agent stylesheet's `[hidden] { display: none }` regardless of specificity (author-origin normal declarations always outrank user-agent-origin normal declarations in the cascade — this is not a specificity tie broken by source order, it's an origin-precedence rule, which is why simply reordering rules could never have fixed it either). The fix's own comments describe this mechanism accurately and were applied consistently to every element `panel-lookup.js` toggles `.hidden` on — **except one**.

`companion/static/panel-lookup.js`'s `openFromTrigger()` (new in this phase, replacing the old unconditional `image.src = src; image.alt = captionText;`) now does:

```js
if (src) {
  image.hidden = false;
  image.src = src;
  image.alt = captionText;
} else {
  image.hidden = true;
  image.removeAttribute("src");
  image.removeAttribute("alt");
}
```

`image` is `dialog.querySelector(".lightbox__image")`. `.lightbox__image`'s rule in `style.css:4340` is:

```css
.lightbox__image {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-control);
  margin-bottom: var(--space-sm);
}
```

This selector was never touched by the 14-08 fix and still declares `display: block` unconditionally. By the exact mechanism the fix's own comments describe for the sibling forms, this `display: block` wins over `[hidden] { display: none }` — so `image.hidden = true` (the gap-mode branch, D-02/RESEARCH.md Pitfall 1's own documented requirement that "a gap card carries no image at all") does not actually hide the `<img>` element. The element stays laid out at `width: 100%; height: auto` with no `src`/`alt` attribute, i.e. an empty/broken-looking image box appears in the dialog for every gap-mode and needs-artwork-with-no-context open, which is precisely the visual regression class the 14-08 fix was written to eliminate elsewhere.

Confirmed this wasn't just missed by inspection but also by the test suite: `test_status_pages.py`'s own harness check for the 14-08 fix (around line 7442) only asserts the three-way `.lightbox__replace`/`.lightbox__resolve-name`/`.lightbox__delete` group and the `.lightbox__replace-zone`/`.resolve-upload-zone` group carry `:not([hidden])` — it never asserts anything about `.lightbox__image`, so this gap has no test coverage either.

**Fix:**
```css
.lightbox__image:not([hidden]) {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-control);
  margin-bottom: var(--space-sm);
}
```
(and, symmetrically, add `[hidden].lightbox__image { display: none; }` if `:not()` scoping alone is judged insufficient for the `.lightbox--wide .lightbox__image` override rule at style.css:4424, which also sets no explicit `[hidden]`-aware behavior of its own but only applies additional sizing, not `display`, so scoping the base rule should be sufficient).

## Warnings

### WR-01: Unsanitized `?resolve=` value is concatenated directly into a `document.querySelector()` attribute selector

**File:** `companion/static/panel-lookup.js:299-340`

**Issue:** The new load-time auto-open reads the raw `resolve` query-string value and builds a CSS attribute selector by string concatenation:

```js
var resolveValue = resolveParamFromSearch(location.search); // decodeURIComponent, no further validation
if (resolveValue) {
  var autoTrigger = null;
  try {
    autoTrigger = document.querySelector(
      '[data-view-panel-resolve-prefix="' + resolveValue + '"]');
  } catch (err) {
    autoTrigger = null;
  }
  if (autoTrigger) {
    openFromTrigger(autoTrigger);
  }
}
```

`resolveValue` is never validated against the ICAO-prefix shape (the comment at line ~325 explicitly says "Never re-validates the prefix itself ... a non-matching value ... is silently ignored"), and it is inserted into the selector string with no quote-escaping. A value containing a `"` character breaks out of the attribute-value string and can append arbitrary selector syntax, e.g. `?resolve=x"],img,["y` builds the selector `[data-view-panel-resolve-prefix="x"],img,["y"]` — a valid selector *list* whose second branch (`img`) matches the first `<img>` element in the document regardless of whether it's a real resolve trigger. `document.querySelector()` returns that element, and `openFromTrigger()` is then called on it, reading `data-view-panel-*` attributes that don't exist on it (all fall back to `""` via the `attr || ""` idiom) and unconditionally calling `dialog.showModal()`.

The impact here is limited — no code execution, no data exfiltration, nothing sent over the network — but it is a genuine unsanitized-input-into-a-DOM-selector defect that a crafted link can use to force an unwanted, possibly confusingly-blank modal open on a victim's page load, and it is worth closing on the same "validate before use" principle the rest of this module documents extensively for its server-side counterpart (`unresolved_row_for_prefix()`'s own `normalise_prefix()` gate).

**Fix:** Validate `resolveValue` against the same ICAO-prefix shape the server enforces before using it in a selector (a simple regex like `/^[A-Za-z0-9]{1,8}$/` would already reject the injection payload), or use an attribute-value escape (`CSS.escape(resolveValue)` — supported in all browsers this codebase already targets for `<dialog>`/`showModal()`) instead of raw concatenation:
```js
autoTrigger = document.querySelector(
  '[data-view-panel-resolve-prefix="' + CSS.escape(resolveValue) + '"]');
```

### WR-02: `manual_resolutions.json` is read twice, non-atomically, within a single `render()` call — a narrow race can reintroduce the exact dual-state bug the 14-08 fix targeted

**File:** `companion/pages/airlines_page.py:837-918` (`_gap_rows_for_grid`) and `companion/pages/airlines_page.py:1637-1746` (`render`)

**Issue:** `companion/app.py`'s `page_context()` loads `manual_resolutions` once per request (`"manual_resolutions": manual_resolutions.load_manual_resolutions(state_dir)`) and passes it through `ctx`. `render()` prefers `ctx.get("manual_resolutions")` for building `manual_rows`/`manual_info_by_name`/`injected_pairs`. But `_gap_rows_for_grid(state_dir)`, called from inside the same `render()` invocation, performs its **own, independent** `manual_resolutions.load_manual_resolutions(state_dir)` call to build its exclusion set — a second read of the same mutable JSON file.

`companion/app.py`'s docstring is explicit that this is a `ThreadingHTTPServer` (multiple worker threads, no lock around `manual_resolutions.json` reads/writes other than `_POLL_LOCK`, which guards an unrelated resource). If a `POST /airlines/resolve` or `POST /airlines/manual-resolutions/{prefix}/delete` from a second session commits between `page_context()`'s read (first) and `_gap_rows_for_grid()`'s read (second, later in the same request), the two reads can observe different registry states for the same request:

- `ctx["manual_resolutions"]` (old, pre-write) does not yet contain the new entry, so `render()`'s manual-card injection logic does not produce a card for it.
- `_gap_rows_for_grid()`'s own fresh read (new, post-write) does contain the entry, so the prefix is excluded from the gap block.

Net effect for that one request: the prefix appears in **neither** the gap block nor the manual/curated grid — transiently reproducing the "invisible prefix" failure mode the 14-08 fix's own commit message says it was closing, just via a race window instead of the original poll-state/manual-state staleness. The window is narrow (it requires a POST from another session landing inside one render's few-millisecond gap between two reads) and self-corrects on the next page load, so this is not as severe as the original bug, but it is a live TOCTOU inconsistency introduced by having two independent, non-synchronized reads of the same file within one logical render.

**Fix:** Have `_gap_rows_for_grid()` accept the already-loaded manual registry as a parameter (mirroring how `render()` already threads `manual_rows` into `_gallery_grid_html()` rather than recomputing it), so both the gap-exclusion set and the manual-card injection within one `render()` call are guaranteed to observe the same snapshot of `manual_resolutions.json`:
```python
def _gap_rows_for_grid(state_dir, manual_registry):
    ...
    if not state_dir:
        return [], 0
    ...
    for prefix, entry in registry.items():
        if prefix in manual_registry:
            continue
        ...
```
and in `render()`, compute `registry` once (as it already does) and pass it into `_gap_rows_for_grid(state_dir, registry)` instead of letting that function reload it.

### WR-03: `_gap_card_html()`'s `filter_text` construction can raise `AttributeError` on a malformed `poll_state.json` entry, contradicting `_gap_rows_for_grid()`'s own "Never raises" docstring claim

**File:** `companion/pages/airlines_page.py:898-914` (`_gap_rows_for_grid`) and `companion/pages/airlines_page.py:955-958` (`_gap_card_html`)

**Issue:** `_gap_rows_for_grid()` builds its eligible-rows tuples with:
```python
eligible.append((
    prefix,
    count,
    entry.get("first_seen") or "",
    entry.get("last_seen") or "",
    entry.get("example_callsign") or "",
))
```
The `or ""` idiom only substitutes an empty string when the source value is falsy. It does **not** guarantee the value is a `str`: if `entry["example_callsign"]` (or `first_seen`/`last_seen`) is present but holds a non-string truthy JSON value — a number, a list, a dict, `true` — from a hand-edited or otherwise corrupted `poll_state.json`, that non-string value passes through unchanged into the tuple.

`_gap_card_html()` then does:
```python
prefix, count, first_seen, last_seen, example_callsign = row
...
filter_text = escape_html("%s %s" % (example_callsign.lower(), prefix.lower()))
```
`example_callsign.lower()` raises `AttributeError` if `example_callsign` is not a `str`. This call is made unconditionally for every shown gap row from `render()`, with no `try`/`except` — a single malformed registry entry would crash the entire `/airlines` page render (a 500, or an unhandled exception surfacing however the WSGI/handler layer degrades) for every visitor, not just fail to render that one card.

This directly undercuts `_gap_rows_for_grid()`'s own docstring claim ("Never raises ... a missing/unreadable poll state both yield `([], 0)` rather than crashing a page render") — that guarantee only covers `_gap_rows_for_grid()` itself, not the downstream consumer it was written to feed, and the module's own established discipline elsewhere (e.g. `_resolve_section_html()`'s explicit "corrupt-file case that must not render a form" guards) treats this exact class of hand-edited/malformed state as something to defend against, not assume away.

Under normal operation `example_callsign` is always a truncated string slice (`server/plane/enrich.py`'s `normalised[:UNRESOLVED_EXAMPLE_MAX_LEN]`), so this is not reachable via the app's own write path — it requires a corrupted or hand-edited `poll_state.json` — but this codebase treats "hand-edited state file" as an explicitly anticipated threat elsewhere in this same module, so the omission here is inconsistent with its own established defensive posture.

**Fix:** Guard the type at the same point `_gap_rows_for_grid()` already normalizes falsy values, so the tuple's contract is genuinely "five strings," not "three strings and two possibly-non-string leftovers":
```python
def _str_field(entry, key):
    value = entry.get(key)
    return value if isinstance(value, str) else ""

eligible.append((
    prefix,
    count,
    _str_field(entry, "first_seen"),
    _str_field(entry, "last_seen"),
    _str_field(entry, "example_callsign"),
))
```

### WR-04: A manual entry whose stored name no longer slugs to a usable illustration key can be excluded from the gap block without ever producing a replacement card

**File:** `companion/pages/airlines_page.py:1697-1726` (`render()`'s injection loop) vs. `companion/pages/airlines_page.py:1523-1529` (`_resolve_section_html()`'s equivalent guard)

**Issue:** `_gap_rows_for_grid()` unconditionally excludes any prefix present in the manual registry, regardless of whether that registry entry can still be turned into a renderable card. `render()`'s own injection loop then does:
```python
for prefix, airline_name, _created_at, superseded, needs_artwork in manual_rows:
    display_name = (
        enrich.static_airline_name_for_prefix(prefix) if superseded else airline_name)
    if display_name and display_name not in manual_info_by_name:
        manual_info_by_name[display_name] = (prefix, superseded, needs_artwork)
    if (not superseded and airline_name not in curated_names
            and airline_name not in injected_names):
        injected_pairs.append((airline_name, []))
        injected_names.add(airline_name)
```
This injects `(airline_name, [])` into `pairs` whenever the name isn't already curated, with no check on whether `illustrations.normalise_airline_key(airline_name)` (equivalently `manual_resolutions.illustration_key_for_name(airline_name)`) would actually resolve to a usable key. `_airline_card_html()` silently returns `""` (skips the card entirely) when the key comes back falsy — a documented, deliberate behavior for that function in isolation, but here it means the card that was supposed to replace the now-excluded gap card simply never appears.

Under the app's own write path this can't happen at the moment of writing (`manual_resolutions.add_entry()` already requires `illustration_key_for_name()` to succeed before persisting, per its own validation ladder), but it **can** happen later purely from a code-side change: if a future deploy of `illustrations.py` changes `normalise_airline_key()`'s reserved-name list or slugging rules (exactly the scenario `_resolve_section_html()` already anticipates and calls out by name: *"A stored entry whose name no longer slugs is a corrupt-file case that must not render a form"*), an existing, previously-valid manual entry can silently stop producing a card on the very next `/airlines` render — while `_gap_rows_for_grid()` still excludes its prefix from the gap block because the entry is present in the manual registry. The result is exactly the failure mode this phase's own 14-08 fix commit message describes wanting to prevent ("the prefix becomes truly invisible"), just triggered by key-derivation drift instead of poll-state staleness.

**Fix:** Mirror `_resolve_section_html()`'s own guard in the injection loop — skip injecting (and skip excluding the gap block entry for) a manual row whose name doesn't currently produce a usable key, or at minimum fall back to *not* excluding such a prefix from `_gap_rows_for_grid()`'s eligible set so it stays visible as a gap card rather than disappearing from both surfaces:
```python
if (not superseded and airline_name not in curated_names
        and airline_name not in injected_names
        and illustrations.normalise_airline_key(airline_name)):
    injected_pairs.append((airline_name, []))
    injected_names.add(airline_name)
```
(and thread the same key-validity check into `_gap_rows_for_grid()`'s own exclusion condition, so the two functions' notions of "this prefix is manually handled" can never diverge).

---

_Reviewed: 2026-09-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
