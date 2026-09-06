# Phase 13: Add an illustration for an unidentified flight from the companion web interface - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

From the two companion pages that already surface a coverage gap — Health's unresolved-prefix registry and the Airlines gallery — the operator can close that gap without leaving the web interface for the manual coverage-gap runbook. Closing it means giving an unrecognised ICAO callsign prefix an airline name, and, when that name has no existing artwork, an illustration to go with it.

Promoted from `.planning/seeds/SEED-005-upload-illustration-for-unidentified-flights-from-the-web-ui.md`.

**What this phase is NOT.** It is not an airline-data editor, not a CRUD surface over the illustration set, and not a retroactive repair of already-recorded history. It resolves *future* detections of a prefix the device has actually seen.

</domain>

<decisions>
## Implementation Decisions

### Two corrections to the seed, established before any decision was taken

The seed's own scope analysis was derived by reading shipped code, not from a design conversation, and two of its load-bearing claims did not survive verification. Both were established before the discussion and both changed the shape of the phase. Downstream agents should treat the seed's Gap-1/Gap-2 framing as superseded by this file.

- **The seed names the wrong table for its option (a).** It states that resolving an airline would add an entry to `enrich.py`'s `_AIRLINE_NAME_CORRECTIONS` (`server/plane/enrich.py:272`). That table is keyed `(prefix, existing_airline_name) → corrected_name` and `correct_airline_name()` returns its `airline_name` argument unchanged whenever that argument is falsy or non-string. A prefix nobody has resolved carries **no** name, so this table can never fire for this use case. The table that would actually need the entry is `_ICAO_AIRLINE_PREFIXES` (`enrich.py:461`) — and it carries a drift guard: `test_enrich.py` asserts every value is a member of `illustrations.target_airline_names()`, itself derived from the static `_ILLUSTRATION_TARGETS` list. So the seed's "(a) adds a row to a correction table" is really "(a) adds an airline to two git-tracked Python tables, under a test that couples them" — something a web UI cannot do at runtime at all.

- **The seed missed the clean answer to its own Gap 1.** It frames the membership gate on `_handle_illustration_replace()` as the crux, on the reasoning that lifting it would let a key originate in user input. But the unresolved-prefix registry **is already validated server-side state**: `note_unresolved_prefix()` (`enrich.py:754`) records a prefix only when the callsign passed `_AIRLINE_PREFIX_SHAPE_RE` *and* `airline_from_callsign()` returned `None`, and it is written by production code from genuinely detected traffic. Testing membership against that registry has exactly the same shape as the existing `_ILLUSTRATION_FILENAMES` test — a closed, server-controlled set — so threat `T-v26-02-01`'s validate-then-join property is re-established rather than relaxed. **The gate is not the hard part of this phase.**

**What the hard part actually is.** The project today holds **no runtime-mutable identity state**. `illustration_overrides/{key}.png` replaces the *source* of an existing tier; it never creates a key, and every name→art relationship lives in static Python under a drift guard. This phase introduces the project's first runtime-writable identity namespace. That, not the upload path, is where its risk sits.

### What a manual resolution is

- **D-01:** **A manual resolution carries a name AND (when needed) an image, keyed on the 3-letter ICAO prefix, in a runtime registry** — consulted by `airline_from_callsign()` *after* the static `_ICAO_AIRLINE_PREFIXES` table. One new concept rather than a bridge between two static tables; `_ICAO_AIRLINE_PREFIXES`, `_ILLUSTRATION_TARGETS` and the drift guard coupling them are left completely untouched.

  Rejected: **image only, keyed on the prefix** (the seed's option b) — smaller, but the flight stays captioned as unidentified: a new picture under a name the frame still cannot say. Rejected: **editing the git-tracked tables** — faithful to the current design and to the drift guard, but nothing reaches the frame before a commit and a redeploy, which is precisely the runbook this phase exists to replace.

- **D-02:** **A manual resolution is a fifth `resolve_route()` source, `"manual"`** — not folded into `"airline_only"`. `resolve_route()` currently classifies into `fresh_hit` / `cache_hit` / `airline_only` / `miss`, and Health renders that breakdown (CFG-08) with an explicit gloss: *"adsbdb had no route, but the callsign's ICAO prefix identified the airline **from the static prefix table**."* Folding manual resolutions into that bucket would make that sentence false. A distinct category keeps the resolution rate honest and lets the operator see their own contribution grow.

  Cost, accepted: one more entry in `_SOURCE_ROWS`, and the history/statistics path must tolerate the new value.

- **D-03:** **Name first; the image is requested only when no artwork already exists under that name.** Once a prefix carries a name, the existing fallback ladder does the rest on its own — if the named airline is already one of the 27 illustration targets, Tiers 1 and 2 find its art with no upload at all. Asking for a file whose result the ladder would discard is work the operator should never be made to do.

- **D-04:** **An uploaded image is the airline's default (Tier 2), keyed on the normalised name alone** — it serves every aircraft type for that carrier. This is the existing Tier 2 semantics, whose own comment records the reasoning: brand identity beats exact type precision on a frame that is glanced at. `_ILLUSTRATION_TARGETS` already admits shape-less entries, so this needs no new shape concept.

  Rejected: **letting the operator pick a shape bucket** (reaching Tier 1) — more precise, but it requires knowing the observed aircraft's type and multiplies uploads per carrier.

### Where the entry lives

- **D-05:** **A dedicated JSON file in `state_dir`, following `device_config.json`'s contract exactly** — tmp-write-then-`os.replace()`, never-raising `normalise_*` helpers, all-or-nothing rejection, companion writes / server reads. It survives a redeploy for the same documented reason overrides do: `deploy/deploy.sh` rsyncs `server/` with `--delete` and excludes only `state`.

  Rejected: **a ninth key inside `device_config.json`** — zero new files and the existing all-or-nothing save for free, but it mixes an unbounded growing dictionary into seven bounded scalar fields. Rejected: **inside `poll_state.json`, next to `unresolved_prefixes`** — the gap data already lives there, but that file is owned and rewritten wholesale each cycle by `poll_loop.py`; the companion only ever reads it (verified: `save_poll_state()` has no caller in `companion/` outside tests). Writing there would be this codebase's first cross-process write race.

- **D-06:** **When the static table later learns a prefix that was resolved by hand, the static table wins — and the manual entry is flagged as superseded in the UI.** Not silently: the override is keyed on the *operator's* normalised name, so a static entry naming the same carrier even slightly differently produces a different key and the uploaded art would vanish from the frame with nothing to explain it. Flagging makes the supersession visible and repairable.

  Note this collision only ever involves the static prefix table. adsbdb wins by construction and needs no rule: `resolve_route()` calls `lookup_route()` first, and `airline_from_callsign()` is only reached when that returned `None`.

  Rejected: **manual always wins** — the operator's art never disappears, but an upstream correction can then never reach that prefix. Rejected: **static wins silently** — smallest to build, and exactly the kind of mute drift this project has repeatedly paid to eliminate.

- **D-07:** **A management surface limited to list + delete**, showing each manual entry's state (active / superseded). No in-place editing — correcting an entry means deleting it and re-adding, which the add form already does. D-06 requires *some* surface (a flag nobody can see is not a flag); this is the smallest one that makes D-06 mean something.

  Rejected: **list only** — smallest, but repairing a superseded entry or a typo falls back to hand-editing JSON, i.e. back to the runbook. Rejected: **full editing** — a complete CRUD over a brand-new namespace, well beyond "add an illustration".

- **D-08:** **Deleting a manual resolution deletes the entry, never the uploaded image.** The override is keyed on the *airline name*, so it is shareable: two prefixes resolved to the same carrier share one file, and the existing Airlines flow can have written that same key by an entirely different path. Never delete a file from a path that does not own it. Accepted cost: orphaned PNGs accumulate in `state_dir` with no garbage collection.

  Rejected: **delete the image when unreferenced and not a vendored target** — tidier, but it introduces reference counting and an irreversible file deletion over a namespace that has existed for one phase.

### The fifth fallback tier — dissolved, not decided

- **D-09:** **No fifth tier. `select_illustration()` is not modified at all.** This was a selected discussion area that dissolved under verification rather than being chosen away, and the planner must not reinstate it.

  `resolved_illustration_path()` (`server/plane/illustrations.py:668`) is the single seam every tier goes through: it returns the override path when that file exists, else the vendored path, else `None` — and it does **not** require the key to be a known target. So once D-01's registry translates the prefix into a name, `airline_only_route(name)` produces a route whose `airline_name` flows into the existing ladder, Tier 1 misses, and **Tier 2 resolves `{normalised-name}` straight to the uploaded override**. The namespace bridge is the prefix→name registry; the art namespace needs no bridge at all.

  What remains is one narrow change, and it is in the companion, not the renderer: `_ILLUSTRATION_FILENAMES` (`companion/app.py`) is a `frozenset(illustrations.target_filenames())` computed once at import, and a newly-named carrier's key is not in it. It must be widened to admit keys minted from server-side state — per the correction above, from the unresolved registry, never from the request.

### The affordance

- **D-10:** **The form lives on Airlines; Health gets a per-row deep link to it.** Health keeps its word: `_READ_ONLY_NOTE` (`companion/pages/health_page.py:352`) is **re-worded**, not broken — the list stays read-only and now says where resolution happens. Decision D-11/D-12 from `06.6.4.1-04` therefore stands rather than being reopened, and Health does not acquire its first `<form>`/`<button>`. One code path owns the action.

  Rejected: **the form on Health** — the gap and the flight's own context are already on screen there, but it reopens D-11/D-12 head-on. Rejected: **Airlines only, no link** — smallest, but the operator must hand-copy a prefix read on another page, which is the round trip the seed exists to remove.

- **D-11:** **The prefix travels in the URL and is membership-tested against the server-side registry** — the same validate-then-join shape the existing route uses, and the direct application of the Gap-1 correction above.

- **D-12:** **The flight's context is re-read server-side from the registry**, keyed by the validated prefix: first seen, last seen, sighting count, example callsign. Nothing displayed is taken from the query string. No new data source — `unresolved_rows()` already returns exactly this tuple.

  Rejected: **also deep-linking into History's filter** — richer context without duplicating it, but it adds a dependency on History's filter and one more round trip. Rejected: **showing the prefix alone** — the operator would name the carrier blind.

- **D-13:** **A free-text name field with a native `<datalist>`** offering the 27 airlines that already have artwork. This is what makes D-03 actually pay: `normalise_airline_key()` slugs the name (`"Air Algérie"` → `air-algerie`), so "Volotea Airlines" instead of "Volotea" mints a key that does not exist and silently misses art the project already ships. Choosing a suggestion guarantees the attachment; typing something else stays available for a genuinely new carrier. `<datalist>` is native — no JavaScript, matching the site's posture.

  Rejected: **free text alone** — simplest, and silently wrong on any name variant. Rejected: **two explicit paths** (dropdown for known carriers, free field for new ones) — clearest about what will happen, but two forms and two code paths on a page that has one.

- **D-14:** **The poll loop removes a now-covered prefix from the gap registry on its next cycle.** `note_unresolved_prefix()` stops *recording* a resolved prefix on its own (it only records when `airline_from_callsign()` returns `None`), but the entry already in `poll_state.json` would otherwise persist and Health would keep listing a resolved prefix as a gap — `coverage_status()` included. D-05 establishes that the companion never writes that file, so the cleanup belongs to its owner. The gap disappears at the next wake, the same latency as everything else in this product.

  Rejected: **Health filtering it out at render time** — immediate and needs no server change, but stored data and displayed data diverge and `coverage_status()` must be patched separately to stop lying. Rejected: **both** — best experience, two mechanisms to keep consistent for a discrepancy lasting at most one wake.

### Claude's Discretion

- All copy: the re-worded `_READ_ONLY_NOTE`, the form's labels and hints, the success/rejection flashes, and the superseded-entry marker. Constraint from the Phase 12 precedent (D-02/D-04 there): the confirmation must not imply the frame changes instantly — a manual resolution reaches the glass at the next wake, up to `wake_interval_s` (60-3600s) away.
- The registry's exact on-disk shape, its entry cap (`UNRESOLVED_PREFIX_MAX_ENTRIES = 200` is the natural reference), and how `airline_from_callsign()` is threaded to consult it without breaking its documented purity/never-raises property — note that function is currently pure with no I/O, and D-01 changes that; how the read is cached or injected is planning work.
- Whether the new POST route reuses `_handle_illustration_replace()` or sits alongside it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Origin
- `.planning/seeds/SEED-005-upload-illustration-for-unidentified-flights-from-the-web-ui.md` — the seed this phase was promoted from. **Read it with this file's two corrections in hand**: its `_AIRLINE_NAME_CORRECTIONS` claim is wrong, and its Gap-1 framing is superseded by D-11.

### The security posture this phase extends
- `.planning/quick/260902-v26-*` — the hardened upload path: validate-then-join, the strict single-part multipart parse, write-to-temp-then-validate, and the rule that only server-produced Pillow bytes are ever stored. Threat IDs `T-v26-02-*`; `T-v26-02-01` is the one D-11 re-establishes.
- `.planning/quick/260903-df3-*` — the framed action-area restyle of that form, the control surface D-10 extends.

### The decision this phase deliberately does NOT reopen
- `.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-CONTEXT.md` — D-11/D-12, the read-only-by-design registry. D-10 re-words the note rather than breaking the decision; confirm that reading before touching `health_page.py`.

### Precedent for the storage contract and the latency honesty
- `.planning/phases/12-remote-display-on-off-toggle/12-CONTEXT.md` — D-08/D-09 (the never-raising registry field pattern) and D-02 (telling the operator the truth about when a change reaches the glass).
- `.planning/phases/10-scheduled-quiet-hours/10-CONTEXT.md` — the companion-writes/server-reads seam D-05 mirrors.

### Project-level constraints
- `.claude/CLAUDE.md` — GSD workflow enforcement; the stdlib-only server posture.
- `.planning/PROJECT.md` — the poll-only device architecture that makes D-14's next-cycle latency unavoidable.

No external specs or ADRs beyond the above — every requirement for this phase is captured in the decisions here.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `companion/app.py` — `_handle_illustration_replace()` (line 1082) and `parse_single_uploaded_file()` (line 464), bounded by `MAX_ILLUSTRATION_UPLOAD_BYTES` (line 83, 4 MB). Reuse whole. Its docstring enumerates the ordered security steps and states that the ordering *is* the security property; read it before changing anything there.
- `companion/pages/airlines_page.py` — `_lightbox_replace_form_html()` (line 270): a native multipart POST with no JavaScript submit logic, `accept="image/png"` as a picker hint only. The form D-10 extends.
- `companion/pages/health_page.py` — `unresolved_rows()` (line 1843) already returns exactly `(prefix, count, first_seen, last_seen, example_callsign)`, which is D-12's entire display payload. No new data access needed.
- `server/device_config.py` — `load_device_config()` / `save_device_config()` (lines 524/560) and the `normalise_*` family: the exact contract D-05 copies, including the tmp-write/`os.replace`/stray-tmp-cleanup idiom at lines 637-645.
- `server/plane/enrich.py` — `airline_only_route()` (line 639) builds the airline-only route shape every downstream consumer already handles unchanged. A manual resolution produces this same shape; do not invent a second one.

### Established Patterns
- **Validate-then-join, never sanitise-then-join**, over a closed server-controlled set. Both `_serve_illustration_image()` and `_handle_illustration_replace()` test membership before any path exists. D-11 keeps this property with a different set.
- **Never-raises normalisation.** `normalise_airline_key()`, `classify_aircraft_type()`, `airline_from_callsign()` and the `device_config` family all degrade to `None`/unchanged for any hostile or malformed input, and several document that the only strings they can return come from a fixed table. **D-01 changes that property for `airline_from_callsign()`** — its returnable set becomes operator-supplied. That is the single most security-relevant consequence of this phase and it must be handled deliberately: every consumer that relied on "table values or `None`" needs re-examining, `illustrations.py`'s path construction first (`_UNSAFE_KEY_RE`, `illustration_path_for_key()`, `override_path_for_key()` are the boundaries that must now carry the weight).
- **`SameSite=Strict` is this site's whole CSRF control** (`companion/auth.py:132`); no route carries a token. A new state-changing POST follows that posture rather than inventing a second mechanism.
- **JS-free degradation is designed, not accidental** — `panel-lookup.js`'s `action=""` placeholder degrades to a harmless 404. A deep link plus a native `<datalist>` (D-13) keeps this phase inside that posture with no new JavaScript.
- **`poll_state.json` belongs to `poll_loop.py`.** Verified: no `save_poll_state()` caller in `companion/` outside tests. D-05 and D-14 both rest on this.

### Integration Points
- `server/plane/enrich.py` — `airline_from_callsign()` (registry consulted after the static table, D-01/D-06) and `resolve_route()` (the fifth `"manual"` source, D-02).
- `server/poll_loop.py` — the gap-registry cleanup, D-14, inside the cycle that already rewrites `poll_state`.
- `companion/app.py` — the widened `_ILLUSTRATION_FILENAMES` membership source (D-09) and the new POST route (D-10/D-11).
- `companion/pages/airlines_page.py` — the resolve form, its `<datalist>`, and the manual-entry list with its delete control (D-07/D-13).
- `companion/pages/health_page.py` — the re-worded `_READ_ONLY_NOTE` and the per-row deep link (D-10). No form, no button.
- `server/plane/illustrations.py` — **read-only for this phase.** `select_illustration()` is not modified (D-09).

</code_context>

<specifics>
## Specific Ideas

- The developer opened the session by challenging the seed inventory rather than accepting the list offered — *"tu es bien synchro avc main ? il manque des seeds"*. Verified and answered: `.planning/` is byte-identical to `origin/main`, all ten seed files match, no seed file exists on any other remote branch, and no seed has ever been deleted (the `260902-ipj` convention closes a seed with a `status` field and a dated addendum instead). Recorded because the same reflex is worth keeping: this phase's own two seed corrections came from the same instinct to verify rather than inherit.
- Every decision in this discussion where a cheaper option existed went to the more honest one: D-02 (a fifth source rather than a convenient lie in Health's gloss), D-06 (flagging a superseded entry rather than letting art vanish silently), D-14 (real cleanup rather than a display-time filter that would make `coverage_status()` misreport). The planner should treat "the operator is never silently misled" as this phase's governing constraint when a trade-off surfaces that this file did not anticipate.

</specifics>

<deferred>
## Deferred Ideas

- **Retroactivity over History.** Resolving `XYZ` today does not rewrite History rows already classified `miss`, so the screen and the measured resolution rate diverge for past flights. Raised and deliberately left open rather than decided quietly — leaving history alone preserves the integrity of a measurement the project has cited since Phase 2 (~52.6% real traffic), which is the strongest argument against touching it. Settle at plan time if it proves cheap; otherwise it is its own small phase.
- **Garbage collection for orphaned overrides.** D-08 accepts that deleted entries leave their PNGs behind. A sweep — or a "storage" view listing overrides with no referencing entry — is a natural follow-up once the namespace has real contents.
- **In-place editing of manual resolutions.** Rejected under D-07 as a full CRUD beyond this phase's boundary. Worth revisiting only if delete-and-re-add proves genuinely annoying in use.
- **A shape-specific (Tier 1) upload.** Rejected under D-04. Would become interesting only if a single carrier's fleet mix made one silhouette visibly wrong on the glass.

</deferred>

---

*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Context gathered: 2026-09-05*
