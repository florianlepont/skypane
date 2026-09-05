# Phase 13: Add an illustration for an unidentified flight from the companion web interface - Research

**Researched:** 2026-09-05
**Domain:** Internal architecture extension — runtime-mutable identity state layered onto an existing stdlib-only Python companion service and its enrichment/illustration pipeline. No new external technology.
**Confidence:** HIGH (every finding below is grounded in a direct read of the exact files this phase touches; no external library research was needed because this phase introduces zero new dependencies)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** A manual resolution carries a name AND (when needed) an image, keyed on the 3-letter ICAO prefix, in a runtime registry — consulted by `airline_from_callsign()` *after* the static `_ICAO_AIRLINE_PREFIXES` table. One new concept rather than a bridge between two static tables; `_ICAO_AIRLINE_PREFIXES`, `_ILLUSTRATION_TARGETS` and the drift guard coupling them are left completely untouched.
- **D-02:** A manual resolution is a fifth `resolve_route()` source, `"manual"` — not folded into `"airline_only"`.
- **D-03:** Name first; the image is requested only when no artwork already exists under that name.
- **D-04:** An uploaded image is the airline's default (Tier 2), keyed on the normalised name alone — it serves every aircraft type for that carrier.
- **D-05:** A dedicated JSON file in `state_dir`, following `device_config.json`'s contract exactly — tmp-write-then-`os.replace()`, never-raising `normalise_*` helpers, all-or-nothing rejection, companion writes / server reads.
- **D-06:** When the static table later learns a prefix that was resolved by hand, the static table wins — and the manual entry is flagged as superseded in the UI. Note this collision only ever involves the static prefix table; adsbdb wins by construction and needs no rule.
- **D-07:** A management surface limited to list + delete, showing each manual entry's state (active / superseded). No in-place editing.
- **D-08:** Deleting a manual resolution deletes the entry, never the uploaded image (the override is keyed on the airline name, shareable across prefixes and with the existing Airlines flow). Accepted cost: orphaned PNGs accumulate with no garbage collection.
- **D-09:** No fifth fallback tier. `select_illustration()` is not modified at all. `resolved_illustration_path()` already consults the override before the vendored file at every tier without requiring a known key — the namespace bridge is the prefix→name registry; the art namespace needs no bridge. The one narrow change is that `_ILLUSTRATION_FILENAMES` (`companion/app.py`) must be widened to admit keys minted from server-side state (never from the request).
- **D-10:** The form lives on Airlines; Health gets a per-row deep link to it. `_READ_ONLY_NOTE` is re-worded, not broken. Health does not acquire its first `<form>`/`<button>`.
- **D-11:** The prefix travels in the URL and is membership-tested against the server-side registry — the same validate-then-join shape the existing illustration route uses.
- **D-12:** The flight's context is re-read server-side from the registry, keyed by the validated prefix (first seen, last seen, sighting count, example callsign). Nothing displayed is taken from the query string.
- **D-13:** A free-text name field with a native `<datalist>` offering the airlines that already have artwork. `<datalist>` is native — no JavaScript, matching the site's posture.
- **D-14:** The poll loop removes a now-covered prefix from the gap registry on its next cycle. The companion never writes `poll_state.json` (D-05 establishes this), so the cleanup belongs to `poll_loop.py`.

### Claude's Discretion

- All copy: the re-worded `_READ_ONLY_NOTE`, the form's labels and hints, the success/rejection flashes, and the superseded-entry marker. Constraint from the Phase 12 precedent: the confirmation must not imply the frame changes instantly — a manual resolution reaches the glass at the next wake, up to `wake_interval_s` (60-3600s) away.
- The registry's exact on-disk shape, its entry cap (`UNRESOLVED_PREFIX_MAX_ENTRIES = 200` is the natural reference), and how `airline_from_callsign()` is threaded to consult it without breaking its documented purity/never-raises property.
- Whether the new POST route reuses `_handle_illustration_replace()` or sits alongside it.

### Deferred Ideas (OUT OF SCOPE)

- **Retroactivity over History.** Resolving a prefix today does not rewrite History rows already classified `miss`. Settle at plan time only if cheap; otherwise its own small phase.
- **Garbage collection for orphaned overrides.** D-08 accepts leaked PNGs. A future sweep/"storage" view is a natural follow-up, not this phase.
- **In-place editing of manual resolutions.** Rejected under D-07.
- **A shape-specific (Tier 1) upload.** Rejected under D-04.
</user_constraints>

## Project Constraints (from CLAUDE.md / project skills)

- **stdlib-only server posture.** `companion/` and `server/` ship no third-party JS, no build step, no new Python dependency beyond what's already pinned (`requests`, `Pillow`). This phase must not introduce one. Confirmed no new package is needed anywhere in this design — see Standard Stack below.
- **GSD workflow enforcement.** All file-changing work must flow through a GSD command (`/gsd-plan-phase` → `/gsd-execute-phase`); no direct repo edits.
- **JS-free degradation is a designed property**, not an accident (`panel-lookup.js`'s `action=""` placeholder degrading to a harmless 404; `list-filter.js`'s early-return guard). Any new control this phase adds (the resolve form, the `<datalist>`, the management list's delete control) must degrade to a working, ordinary HTML form/link with JavaScript absent.
- **`companion/pages/__init__.py`'s page-module boundary:** no page module (`airlines_page.py`, `health_page.py`, `config_page.py`, `history_page.py`) may import another page module. Every page receives its data through the single `ctx` dict `companion/app.py`'s `Handler.page_context()` builds, or reads server-side (non-page) modules directly (both `airlines_page.py` and `health_page.py` already independently import `server.poll_loop`/`server.plane.illustrations`/`server.history_db` — that is the sanctioned crossing point, not a page-to-page import).
- **One escaping choke point.** Every dynamic value any page module renders passes through `companion.layout.escape_html()` (directly or via a layout component). No new ad hoc escaping.
- **`SameSite=Strict` is this site's whole CSRF control** (`companion/auth.py:132`) — no route carries a token; every new state-changing POST this phase adds follows that same posture.
- **sketch-findings-skypane skill (design system):** any new form/list control must use the shipped tokens/patterns — `.filter-bar` for a filter control, `.data-table`/`.data-cards` pairing for the management list (mirroring History's/Health's existing two-representation pattern), `<dialog>`/`.lightbox` conventions if a modal-style confirmation is used, `layout.card_status_class()` for the superseded/active status edge, `.page-section` cards, the 12px uppercase label voice for any new status pill, and the existing button/touch-target density register (30px/36px buttons, no new geometry invented). No `<button>`-as-link fakery; use `<a>` for navigation, `<button type="submit">` for form actions, matching every existing page.

## Summary

This phase has no REQUIREMENTS.md ID (unmapped, matching Phases 10-12's precedent) and no external technology decision to make — it is 100% an internal architecture-extension problem inside a codebase that has never before had runtime-mutable identity state. Every one of the six research priorities named in scope has a concrete, evidence-backed answer below, derived directly from the current source (not assumed):

1. **The purity break** in `airline_from_callsign()` is real and load-bearing, but it is containable: keep `airline_from_callsign(callsign) -> name_or_None`'s existing public signature exactly as-is (so its ~10 existing call sites and 15+ existing tests never change), and add a new, more specific function that also reports *which* table answered (static vs. manual) for `resolve_route()`'s D-02 fifth-source need. The registry itself should be loaded **once per poll cycle** — mirroring `device_config.load_device_config(state_dir)`'s own existing "read once, thread through the whole cycle" rule at `poll_loop.py:725` — via a process-scoped setter that mirrors `illustrations.set_override_state_dir()`'s already-shipped pattern, called once at the top of `run_once()`.
2. **The membership set** (`companion/app.py`'s `_ILLUSTRATION_FILENAMES`) cannot stay a frozenset computed once at import — it must become a per-request union of the static `target_filenames()` and the current manual-resolutions registry's own keys, exactly as `runway_images_available()`/`gallery_entries()` are already computed fresh per request. This only matters for the **read** path (`GET /illustration/{key}.png`, so an operator can preview their own newly-registered art); the **write** path for a brand-new key should not go through this frozenset at all (see #3).
3. **The upload key can't be "validated" against a pre-existing closed set, because it doesn't exist yet.** The resolution is a two-step flow, not one combined multipart form: Step A (`POST` with just the airline name, plain urlencoded, reusing `read_form()`) validates the *prefix* against the unresolved-prefix registry and persists `(prefix -> name)` into the new manual-resolutions registry; only once that name is durably recorded server-side does its derived key become legitimate. Step B (a follow-up `POST /illustration/{key}.png`, only reached when Step A found no existing art) can then **reuse `_handle_illustration_replace()` verbatim** once its membership check is widened per #2 — because by the time Step B runs, the key is no longer "from the request," it is server-recorded state the request is merely referencing.
4. **The "manual" `resolve_route()` source** doesn't require a schema migration — `runway_events.route_source` is an unconstrained `TEXT` column with no CHECK constraint — but it does require `health_page.py`'s `_SOURCE_ROWS` tuple and `enrich.py`'s `resolve_route()` docstring/branching to be updated together, and a drift-check that `route_source_counts()`'s consumer never assumes exactly four values.
5. **The registry file contract** is a straight lift of `device_config.py`'s `load_*`/`save_*`/tmp-write-then-`os.replace()` idiom, applied to an unbounded dict rather than fixed scalar fields — the natural new home is `server/plane/manual_resolutions.py`, a sibling to `enrich.py`/`illustrations.py`, imported by both `companion/app.py` (writes) and `server/plane/enrich.py` (reads).
6. **D-14's poll-loop cleanup** slots in next to the *existing* `unresolved_prefixes` block in `run_once()` (`poll_loop.py:1045-1051`) — but it must NOT rely on `route_source != "miss"` for the current cycle's flight (that only tells you about *this* callsign, and only when adsbdb didn't answer first). It needs its own explicit check: for the callsign detected this cycle, does `airline_from_callsign()` now resolve its prefix at all? If yes and the prefix is still sitting in the registry, remove it — independent of what `resolve_route()`'s branch returned for adsbdb.

**Primary recommendation:** Build a new `server/plane/manual_resolutions.py` module owning the JSON contract (D-05); thread it into `enrich.py` via a `set_manual_registry_state_dir()`-style setter called once per `run_once()` cycle (mirroring `illustrations.set_override_state_dir()`); keep `airline_from_callsign()`'s signature unchanged and add a new `airline_source_from_callsign()` for `resolve_route()`'s D-02 need; implement the resolve form on Airlines as a two-step, JS-free, redirect-driven flow (name POST, then conditional image POST reusing the existing upload handler with its membership gate widened); and place D-14's cleanup as an explicit, independent check right beside the existing unresolved-prefix bookkeeping in `poll_loop.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Manual-resolution registry read (name lookup during enrichment) | API/Backend (`server/plane/enrich.py`) | Database/Storage (JSON file) | `airline_from_callsign()` runs inside the poll cycle, server-side, once per detected flight |
| Manual-resolution registry write (form submit, delete) | Frontend Server / SSR (`companion/app.py`, new route) | Database/Storage (JSON file) | Companion is the only process an authenticated human ever talks to; mirrors D-05's "companion writes, server reads" split, itself mirroring the existing illustration-override contract |
| Manual-resolution registry storage | Database/Storage (`{state_dir}/manual_resolutions.json`) | — | Same tier as `device_config.json`/`poll_state.json`; survives redeploy per `deploy.sh`'s `state/` exclusion |
| Illustration override bytes (upload) | Frontend Server / SSR (`companion/app.py`'s upload handler) | Database/Storage (`{state_dir}/illustration_overrides/`) | Unchanged from the existing v26 upload path; this phase reuses it, does not re-architect it |
| Illustration selection at render time | API/Backend (`server/plane/illustrations.py`, `server/plane/render.py`) | — | Untouched by this phase (D-09) — `resolved_illustration_path()` already bridges the art namespace |
| Coverage-gap registry (unresolved prefixes) | API/Backend (`server/plane/enrich.py` writer, `server/poll_loop.py` caller) | Database/Storage (`poll_state.json`) | Unchanged ownership; this phase only adds a removal path, never a new writer of unresolved entries |
| Resolve-form UI + `<datalist>` + management list | Frontend Server / SSR (`companion/pages/airlines_page.py`) | — | Server-rendered HTML, no client JS; matches every other control on this page |
| Health deep link (re-worded read-only note + per-row link) | Frontend Server / SSR (`companion/pages/health_page.py`) | — | Presentation-only change; no new data access (D-12's tuple already exists) |
| Resolution-rate statistics (`"manual"` bucket) | Database/Storage (`history_db.py`, SQLite) | Frontend Server / SSR (`health_page.py`'s `_SOURCE_ROWS`) | Storage already supports an arbitrary `route_source` string; only the display-layer enumeration needs a new row |

## Standard Stack

### Core

No new library is required anywhere in this phase. Everything needed already ships in this repo:

| Library | Version | Purpose | Why Standard (here) |
|---------|---------|---------|--------------------|
| Python stdlib `json`, `os`, `re` | 3.11 (pinned venv) | New registry file's load/save contract | Identical toolset `server/device_config.py` already uses for the exact same tmp-write-then-`os.replace()` idiom |
| `Pillow` (already a pinned dependency) | already pinned | Re-validating/re-encoding an uploaded image | Step B of the resolve flow reuses the existing `illustrations.validate_illustration_file()` + `Image.open(...).convert("RGBA")` pipeline verbatim — no new image library needed |

### Supporting

None. No HTTP client, no template engine, no CSS framework, no JS bundler is introduced.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A native `<datalist>` (D-13, locked) | A client-side JS autocomplete widget | Would violate the JS-free posture for a form that native HTML already handles adequately; correctly rejected in discussion |
| A dedicated `server/plane/manual_resolutions.py` module | Folding the registry into `device_config.py` | Rejected in discussion (D-05) — mixes an unbounded dict into seven bounded scalar fields |

**Installation:** none — no new packages.

**Version verification:** not applicable — no new package is introduced by this phase.

## Package Legitimacy Audit

**Not applicable.** This phase installs no external packages (npm, pip, or otherwise). The Package Legitimacy Gate protocol is skipped per its own trigger condition ("every phase that installs external packages"). No entries to audit; no packages removed or flagged.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────────────────────┐
                     │              Companion web service (companion/)          │
                     │                                                           │
  Operator's         │  GET /health ──► health_page.render()                    │
  browser            │     │   reads: poll_loop.load_poll_state()               │
     │               │     │   (unresolved_prefixes registry — read only)       │
     │  click deep    │     └──► per-row <a href="/airlines?resolve={prefix}">  │
     │  link          │                                                          │
     ▼               │  GET /airlines?resolve={prefix}                          │
  [Health page]       │     │                                                    │
     │               │     ├─ validate prefix against unresolved_prefixes ──┐   │
     │               │     │  (D-11 validate-then-join)                    │   │
     │               │     ├─ re-read (count, first_seen, last_seen,       │   │
     │               │     │   example_callsign) for that prefix (D-12)    │   │
     │               │     └─ render resolve form + <datalist> of known    │   │
     │               │        airline names (illustrations.target_        │   │
     │               │        airline_names())                            │   │
     │               │                                                     │   │
     │  submit name   │  POST /airlines/resolve  (Step A — urlencoded)     │   │
     ▼               │     │                                               │   │
  [Resolve form]      │     ├─ validate prefix (same registry, D-11)        │   │
     │               │     ├─ normalise + bound the submitted name          │   │
     │               │     ├─ manual_resolutions.add(state_dir, prefix,    │   │
     │               │     │   name)  ──────────────────────► writes ─────►│ manual_resolutions.json
     │               │     └─ resolved_illustration_path(key) exists?      │   │  {state_dir}
     │               │          │ yes → redirect w/ success flash          │   │
     │               │          │ no  → redirect to upload step            │   │
     │               │                                                     │   │
     │  (if no art)   │  POST /illustration/{key}.png  (Step B — reuses    │   │
     ▼               │     the EXISTING _handle_illustration_replace()     │   │
  [Upload form]       │     pipeline, membership gate widened per D-09)    │   │
                     │     └─ writes ──────────────────────────────────────┼──►│ illustration_overrides/{key}.png
                     │                                                      │   │
                     │  GET /airlines  (management list, D-07)             │   │
                     │     └─ list + delete manual_resolutions entries;    │   │
                     │        "superseded" flag = prefix now also in       │   │
                     │        enrich._ICAO_AIRLINE_PREFIXES                │   │
                     └──────────────────────────────────────────────────────┘  │
                                                                                 │
                     ┌─────────────────────────────────────────────────────────┤
                     │         Poll cycle (server/poll_loop.py, run_once())     │
                     │                                                          │
  ADS-B aggregator ─►│  detect flight → resolve_route(callsign, cache)         │
                     │     │                                                    │
                     │     ├─ adsbdb hit? → "fresh_hit"/"cache_hit"            │
                     │     ├─ else: airline_source_from_callsign(callsign)     │
                     │     │     reads manual_resolutions ◄──────── reads ──────┤
                     │     │     ├─ static table hit → "airline_only"          │
                     │     │     └─ manual registry hit → "manual" (D-02)      │
                     │     └─ else → "miss" → note_unresolved_prefix()         │
                     │                                                          │
                     │  D-14 cleanup: is this callsign's prefix now resolved   │
                     │  by EITHER table, and still present in                  │
                     │  unresolved_prefixes? → pop it (poll_state.json)        │
                     │                                                          │
                     │  record_runway_event(route_source=...) ──► history.db   │
                     └──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
server/
├── plane/
│   ├── enrich.py                # airline_from_callsign() gains a registry
│   │                             # consult; new airline_source_from_callsign()
│   │                             # for resolve_route()'s D-02 need; new
│   │                             # clear_resolved_unresolved_prefix() for D-14
│   ├── manual_resolutions.py    # NEW — D-05's JSON contract (load/save/add/
│   │                             # delete/bounded-entries), mirrors
│   │                             # device_config.py's shape exactly
│   └── illustrations.py         # UNCHANGED (D-09) — resolved_illustration_path()
│                                 # already does the work
├── poll_loop.py                  # run_once(): one new setter call near the
│                                 # existing illustrations.set_override_state_dir()
│                                 # call; D-14's cleanup beside the existing
│                                 # unresolved_prefixes block
├── history_db.py                 # UNCHANGED schema; route_source is already
│                                 # an unconstrained TEXT column
└── test_manual_resolutions.py    # NEW — same check()/EXPECTED_CHECK_COUNT
                                  # harness style as test_enrich.py

companion/
├── app.py                        # new POST routes (resolve step A, delete);
│                                 # _illustration_filenames() widened to a
│                                 # per-request union (D-09); flash keys added
│                                 # the same way FLASH_KEY_ILLUSTRATION_* were
├── pages/
│   ├── airlines_page.py          # the resolve form + <datalist> + management
│                                 # list (D-07/D-10/D-13); a new local
│                                 # unresolved_rows(state_dir)-style single-
│                                 # entry lookup mirroring health_page.py's
│   └── health_page.py            # _READ_ONLY_NOTE re-worded (D-10); per-row
│                                 # deep link added to _registry_row_html()/
│                                 # _registry_cards_html(); _SOURCE_ROWS gains
│                                 # the "manual" tuple (D-02)
└── test_companion_app.py         # new route/handler checks
    test_status_pages.py          # new render() checks for both pages
```

### Pattern 1: The purity break — keep the public function pure-shaped, add a source-aware sibling

**What:** `airline_from_callsign(callsign)` is documented (`enrich.py:615-636`) as pure, no I/O, returning only fixed-table values or `None` — a property `note_unresolved_prefix()` (`enrich.py:796`) and every test in `test_enrich.py`'s "260827-hyy" battery (`test_enrich.py:380-413`) directly depend on. D-01 requires it to also consult a runtime registry. Breaking its signature (e.g. adding a required `registry=` parameter) would touch every call site and every existing test.

**Recommendation:** keep `airline_from_callsign(callsign) -> str|None` exactly as-is in signature and behavior (it now also returns manually-resolved names — this is additive, not breaking, for every existing caller: `note_unresolved_prefix()`'s contract, "stops recording once this returns non-None," is *already correct* for the manual case with zero code change there). Add a new function that exposes provenance for the one caller that needs it:

```python
# server/plane/enrich.py
def airline_source_from_callsign(callsign):
    """Return (airline_name, source) where source is "static" or "manual",
    or (None, None) when neither table resolves the prefix. The static
    table is checked first and always wins (D-06) - a prefix present in
    both tables reports "static" only.
    """
    normalised = normalise_callsign(callsign)
    if normalised is None or not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None, None
    prefix = normalised[:3]
    static_name = _ICAO_AIRLINE_PREFIXES.get(prefix)
    if static_name:
        return static_name, "static"
    manual_name = _manual_registry_airline_name(prefix)  # see Pattern 5
    if manual_name:
        return manual_name, "manual"
    return None, None


def airline_from_callsign(callsign):
    """Unchanged public contract - now also reachable via a manually
    resolved prefix (D-01), transparently, with zero change for any
    existing caller."""
    name, _source = airline_source_from_callsign(callsign)
    return name
```

`resolve_route()` (`enrich.py:663-695`) switches its fallback branch from calling `airline_from_callsign()` to calling `airline_source_from_callsign()`, mapping `"static"` to the existing `"airline_only"` source string and `"manual"` to the new `"manual"` source string (D-02). No other caller of `airline_from_callsign()` needs to change.

**When to use:** whenever an existing "pure lookup" function needs to gain provenance-awareness for exactly one caller — add a sibling, don't widen the original's contract.

### Pattern 2: Threading the registry read into the poll cycle — mirror `illustrations.set_override_state_dir()`, not a new parameter chain

**What:** `enrich.airline_from_callsign()`/`airline_source_from_callsign()` are called from deep inside `resolve_route()`, which is called from `poll_loop.run_once()` — but also from `note_unresolved_prefix()`'s own gate and (per D-14) from the new cleanup check, all within the same cycle. `poll_loop.py:717-748` already documents and enforces a "read once per cycle" rule for `device_config.load_device_config()`, specifically so a save landing mid-cycle can't split one cycle across two configurations.

**Recommendation:** give `server/plane/manual_resolutions.py` the exact same process-scoped-default pattern `illustrations.py:606-635` already ships for `_override_state_dir`/`set_override_state_dir()` — but caching the **loaded dict**, not just a directory path, and reloading it explicitly once per cycle:

```python
# server/plane/manual_resolutions.py
_cached_registry = None

def set_manual_registry_state_dir(state_dir):
    """Call once per poll cycle (run_once(), beside the existing
    illustrations.set_override_state_dir() call) - reloads the registry
    fresh from disk so a companion-side save made between cycles is
    picked up on the very next wake, matching D-14's own next-wake
    latency framing. Passing None clears the cache (module-default
    behaviour: no manual resolutions apply)."""
    global _cached_registry
    _cached_registry = load_manual_resolutions(state_dir) if state_dir else {}

def airline_name_for_prefix(prefix):
    """Read-only accessor enrich.py consults - never touches disk itself,
    always reads the cache set_manual_registry_state_dir() populated this
    cycle."""
    entry = (_cached_registry or {}).get(prefix)
    return entry.get("airline_name") if isinstance(entry, dict) else None
```

`poll_loop.run_once()` gains one line beside its existing `illustrations.set_override_state_dir(state_dir)` call (`poll_loop.py:717`):

```python
manual_resolutions.set_manual_registry_state_dir(state_dir)
```

This satisfies "single read per cycle" for exactly the same reason the `device_cfg` read does, keeps `airline_from_callsign()` callable with a single argument everywhere (tests included — a test that never calls the setter sees an empty registry, i.e. today's exact behaviour), and needs no change to `resolve_route()`'s or `note_unresolved_prefix()`'s call signatures.

**Companion-side reads are different and must NOT use this cache.** `companion/app.py` is a long-running `ThreadingHTTPServer`; every authenticated page render (Airlines' management list, the resolve form's registry-membership check) must see the *current* on-disk registry, not a snapshot fixed at process start. Companion code calls `manual_resolutions.load_manual_resolutions(state_dir)` directly, per request — exactly how `device_config.load_device_config(state_dir)` is already called fresh inside `page_context()` (`companion/app.py:738`) on every single request, with no caching.

**Why not thread a parameter instead:** `resolve_route(callsign, cache, transport=None, timeout=...)` already has four parameters and 15+ direct test call sites (`server/test_enrich.py`) that construct it positionally/by-keyword; adding a fifth `manual_registry=` parameter is possible but touches every one of them for no behavioural gain over the setter, which is already the codebase's own precedent for "a deep call chain needs deployment-scoped state it doesn't otherwise carry."

### Pattern 3: The two-step resolve flow — name first, upload only when needed, and why they must be separate requests

**What:** `parse_single_uploaded_file()` (`companion/app.py:464-542`) is deliberately, by its own docstring, "NOT a general multipart parser" — it rejects any multipart body that isn't *exactly* one part. A combined "name + optional file" form in one submission would need a genuinely new multipart parser capable of an optional second field, a materially bigger and riskier scope addition than this phase's stated boundary ("not a CRUD surface," "not the manual runbook").

**Recommendation:** implement D-03 ("name first; image only when needed") as two literal HTTP round-trips, both plain, JS-free, redirect-driven forms — the same shape every other state change in this app already uses:

- **Step A — `POST /airlines/resolve`** (new route, plain `application/x-www-form-urlencoded`, reuses `Handler.read_form()` byte-for-byte): body carries `prefix` (hidden field, the value D-11 already validated when the page was rendered) and `airline_name` (the `<datalist>`-backed free-text field, D-13). Handler validates `prefix` against the unresolved-prefix registry (again — never trust a hidden field alone, matching this codebase's existing "validate on write too" discipline, e.g. `save_device_config()` re-validating every field regardless of what the form claims), normalises/bounds `airline_name`, calls `manual_resolutions.add_entry(state_dir, prefix, airline_name)`, then branches:
  - `illustrations.resolved_illustration_path(key, state_dir) is not None` → redirect to `/airlines?flash=manual_resolved` (D-03: no upload needed, an existing target or a previous override already covers this name).
  - Else → redirect to `/airlines?resolve={prefix}&awaiting_image={key}` (or an equally explicit signal) so the page renders the upload prompt for that specific, now-legitimately-registered key.
- **Step B — `POST /illustration/{key}.png`** (the *existing* route and the *existing* `_handle_illustration_replace()` handler, `companion/app.py:1082-1198`, unmodified in logic) — reached only because Step A already persisted `key` into the manual-resolutions registry, so by the time this request arrives the key is server-recorded state, not request-supplied state. This is exactly why Pattern 2 in the "membership set" discussion below only needs the **read** path widened, not the **write** path's existing validate-then-join logic reopened.

**When to use:** whenever a feature wants "ask for X, and only ask for Y if X didn't already satisfy the need" over a JS-free multipart boundary — split into two requests rather than inventing a richer parser.

### Pattern 4: Widening `_ILLUSTRATION_FILENAMES` from an import-time constant to a per-request union

**What:** `companion/app.py:450-461` computes `_ILLUSTRATION_FILENAMES` once, at import time, from `illustrations.target_filenames()` — a pure, static-table-derived function with no I/O. A manually-resolved airline's key is, by definition, not a member of that static list.

**Recommendation:**

```python
def _illustration_filenames(state_dir=None):
    """The known-safe membership set, now a per-request union of the
    static target set and the current manual-resolutions registry's own
    keys - both are server-side state (never the request), preserving
    T-v26-02-01's validate-then-join property (D-09)."""
    names = set(illustrations.target_filenames())
    if state_dir:
        for entry in manual_resolutions.load_manual_resolutions(state_dir).values():
            key = illustrations.normalise_airline_key(entry.get("airline_name"))
            if key:
                names.add(key + ".png")
    return frozenset(names)
```

Every call site that currently reads the module-level `_ILLUSTRATION_FILENAMES` constant (`_serve_illustration_image()` at `app.py:1011`, `_handle_illustration_replace()` at `app.py:1136`) instead calls `_illustration_filenames(self.args.state_dir)` per request. The cost is one extra small JSON read per authenticated illustration-image request — the same order of magnitude as `load_device_config()`'s already-unconditional per-request read in `page_context()`, and this codebase already accepts that cost everywhere else (`gallery_entries()`, `runway_images_available()`).

**Anti-pattern to avoid:** do not keep the frozenset as a module-level cache invalidated by mtime or similar — this codebase has zero precedent for that pattern and it adds a staleness window for no measurable benefit at this traffic volume (a handful of authenticated requests from one operator).

### Pattern 5: The registry file itself — a direct `device_config.py` lift

**What:** D-05 explicitly requires copying `device_config.json`'s contract "exactly." `server/device_config.py:524-648` is the reference: `load_*()` never raises (missing/corrupt/non-dict file all degrade to `{}`), every field goes through a `normalise_*()` gate, `save_*()` validates before writing anything, and the write itself is `tmp-write, then os.replace(), with a stray-tmp cleanup in the except branch`.

**Recommendation** (`server/plane/manual_resolutions.py`, new file):

```python
MANUAL_RESOLUTIONS_FILENAME = "manual_resolutions.json"
MANUAL_RESOLUTION_MAX_ENTRIES = 200  # mirrors UNRESOLVED_PREFIX_MAX_ENTRIES's
                                      # order of magnitude - this registry is
                                      # authenticated-human-written only, so
                                      # the realistic population is far
                                      # smaller, but the cap still bounds a
                                      # compromised-session worst case.
MANUAL_AIRLINE_NAME_MAX_LEN = 100    # a generous bound on a free-text field
                                      # with no other length limit.

def manual_resolutions_path(state_dir):
    return os.path.join(state_dir, MANUAL_RESOLUTIONS_FILENAME)

def load_manual_resolutions(state_dir):
    """Missing/unreadable/malformed file -> {}. Every entry not shaped
    like {"airline_name": str, "created_at": str} is dropped rather than
    trusted - mirrors note_unresolved_prefix()'s own defensive-entry
    discipline. Never raises."""
    ...

def add_entry(state_dir, prefix, airline_name, now=None):
    """Validates prefix shape (reuse enrich._AIRLINE_PREFIX_SHAPE_RE's
    3-letter contract) and airline_name (non-empty after strip, <=
    MANUAL_AIRLINE_NAME_MAX_LEN, normalise_airline_key() must not return
    None) BEFORE touching the file - same all-or-nothing discipline as
    save_device_config(). Enforces MANUAL_RESOLUTION_MAX_ENTRIES by
    rejecting a new prefix once the cap is hit (this registry has no
    "weakest entry" concept the way trim_unresolved_prefixes() does - it
    is small and human-curated, so a hard reject at the cap, surfaced as
    a flash, is the right shape rather than silent eviction)."""
    ...

def delete_entry(state_dir, prefix):
    """Removes the registry entry ONLY (D-08) - never touches
    illustration_overrides/. No-op, not an error, if the prefix is
    already absent (idempotent delete, matching this codebase's existing
    tolerance for double-submission)."""
    ...
```

Both `load_manual_resolutions()` and the tmp-write-then-`os.replace()` body should be copied structurally from `load_device_config()`/`save_device_config()` (`device_config.py:524-648`), not re-derived — this is explicitly what D-05 asks for.

### Pattern 6: D-14's poll-loop cleanup — an explicit, independent check, not a byproduct of `route_source`

**What:** `poll_loop.py:1017-1051` is where `resolve_route()` is called and where the existing `unresolved_prefixes` bookkeeping already lives. It would be tempting to gate cleanup on `route_source in ("airline_only", "manual")`, but that is wrong: `route_source` describes **this cycle's specific callsign's outcome**, and a `"fresh_hit"`/`"cache_hit"` (adsbdb answered) tells you nothing about whether `airline_from_callsign()` would *also* now resolve that prefix — the registry could theoretically still contain a stale, already-covered prefix from a callsign that this cycle's adsbdb hit bypassed entirely. The correct check is independent of `route_source` and directly mirrors `note_unresolved_prefix()`'s own gating expression.

**Recommendation** — a new, narrowly-scoped enrich.py function, tested exactly like `note_unresolved_prefix()`/`trim_unresolved_prefixes()`:

```python
# server/plane/enrich.py
def clear_resolved_unresolved_prefix(callsign, registry):
    """The inverse of note_unresolved_prefix(): if callsign's prefix is
    present in `registry` AND airline_from_callsign(callsign) now
    resolves (via either table, D-01), remove that entry and return the
    prefix; otherwise return None and change nothing. Same shape-gate,
    same never-raises discipline, same defensive "not a dict" handling
    as note_unresolved_prefix(). This is D-14's whole implementation -
    note_unresolved_prefix() already stops RECORDING a resolved prefix
    on its own; this function is what RETROACTIVELY removes an entry
    that predates the resolution."""
    if not isinstance(registry, dict):
        return None
    normalised = normalise_callsign(callsign)
    if normalised is None or not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    prefix = normalised[:3]
    if prefix not in registry:
        return None
    if airline_from_callsign(callsign) is None:
        return None
    del registry[prefix]
    return prefix
```

Called in `poll_loop.py` right beside the existing block (around `poll_loop.py:1045-1051`), unconditionally (cheap - a dict `in` check plus, only on a hit, one more `airline_from_callsign()` call already computed once this cycle at line 1034's `resolve_route()` for the "miss" case, or freshly here for the hit case):

```python
enrich.clear_resolved_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
if route_source == "miss":
    enrich.note_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
enrich.trim_unresolved_prefixes(unresolved_prefixes)
poll_state["unresolved_prefixes"] = unresolved_prefixes
```

Ordering matters only in that both must run before `trim_unresolved_prefixes()` and the `poll_state["unresolved_prefixes"] = unresolved_prefixes` write-back — which the code above already preserves.

### Pattern 7: The `<datalist>` and the reserved-key collision it must guard against

**What:** No `<datalist>` element exists anywhere in this codebase today (verified: zero matches across `companion/`). It is a plain, well-supported native HTML element requiring no JS and no CSS beyond what the existing `text` input already has.

```html
<label for="manual-airline-name">Airline name</label>
<input type="text" id="manual-airline-name" name="airline_name"
       list="known-airlines" maxlength="100" required autocomplete="off">
<datalist id="known-airlines">
  <!-- one <option value="..."> per illustrations.target_airline_names(),
       each escaped through layout.escape_html() exactly once -->
</datalist>
```

**Pitfall this pattern must guard against:** `normalise_airline_key()` slugs *any* string, including one that collides with a reserved key. If an operator free-types e.g. `"Generic Fallback"` or `"Generic A320"`, the derived key (`"generic-fallback"`, `"generic-a320"`) matches an *existing vendored file* — `illustrations.resolved_illustration_path()` would happily resolve it (D-03's "no artwork exists" check would find one and skip the upload step), and the panel would then caption a real flight with the literal string `"Generic Fallback"`. This is a corner an operator would have to intentionally or accidentally hit (typing exactly a reserved-looking name), but it is real and easy to guard cheaply: `add_entry()` should reject (with a clear flash) any submitted name whose normalised key starts with `"generic-"` or equals `GENERIC_FALLBACK_FILENAME`'s stem, since no real ICAO-registered airline is plausibly named that. See Common Pitfalls below.

### Anti-Patterns to Avoid

- **Reopening `select_illustration()` or adding a fifth fallback tier.** D-09 is explicit and verified against the actual code: `resolved_illustration_path()` already bridges override-before-vendored at every existing tier. Touching `illustrations.py` at all for this phase is a signal something has gone off the rails.
- **Editing `_AIRLINE_NAME_CORRECTIONS` or `_ICAO_AIRLINE_PREFIXES` at runtime.** Both are git-tracked Python literals with a machine-checked drift guard (`test_enrich.py`'s check asserting every `_ICAO_AIRLINE_PREFIXES` value is a member of `illustrations.target_airline_names()`) — they are correctly out of scope per this phase's own two seed corrections.
- **Trusting the hidden `prefix` field on Step A's POST without re-validating server-side.** Every other stateful form in this codebase re-validates on write regardless of what was rendered (`save_device_config()` re-checks every field against its registry even though the form only ever submits legal values) — the resolve form must do the same.
- **A combined name+file multipart form on one POST.** See Pattern 3 — `parse_single_uploaded_file()`'s single-part contract makes this materially harder than it looks; don't widen that parser for this feature.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Validating an uploaded illustration is really a usable PNG | A new image-inspection routine | `illustrations.validate_illustration_file()` (already handles decompression-bomb defense, landscape/alpha/minimum-width checks) | Exact same rules must apply to a manually-resolved airline's art as to every existing vendored/overridden one — D-04 explicitly reuses Tier 2 semantics |
| Parsing the multipart upload body | A general multipart parser | `parse_single_uploaded_file()`, called a second time from Step B, unmodified | Already hardened (T-v26-02-*), single-part-only by design; reuse rather than duplicate |
| Atomic JSON persistence | A new file-locking or write scheme | `device_config.py`'s tmp-write-then-`os.replace()` idiom, copied structurally | Already proven correct under this exact deployment model (rsync excludes `state/`, single-writer-per-file discipline) |
| CSRF protection for the two new POST routes | A per-form token | The existing `SameSite=Strict` session cookie posture | This site has exactly one CSRF mechanism, applied uniformly; inventing a second one for this feature alone would be inconsistent and unnecessary |
| Deep-link prefix validation | A new regex-only shape check | Membership test against the actual current unresolved-prefix registry (D-11) | Shape alone (`_AIRLINE_PREFIX_SHAPE_RE`) would accept a syntactically valid but never-actually-detected prefix; membership against the live registry is the same validate-then-join discipline every other closed-set route in this app already uses |

**Key insight:** every mechanism this phase needs to layer runtime-mutable identity state onto this codebase for the first time already has a structurally identical precedent shipped somewhere else in the same repo (`device_config.py` for the file contract, `illustrations.py`'s override resolver for the art-namespace bridge, the existing upload handler for the byte-validation pipeline, `set_override_state_dir()` for the deep-call-chain state-injection problem). The work is disciplined reuse and careful sequencing, not new mechanism design.

## Common Pitfalls

### Pitfall 1: Assuming `note_unresolved_prefix()`'s "stops recording" also means "retroactively clears"

**What goes wrong:** A planner reads D-01/D-14 and assumes that once `airline_from_callsign()` can resolve a manually-added prefix, the existing `note_unresolved_prefix()` gate (`enrich.py:796`, `if airline_from_callsign(callsign) is not None: return None`) automatically makes the stale registry entry disappear.
**Why it happens:** The gate really is sufficient to stop *future* increments — but a dict entry, once written, persists until something explicitly deletes it. `note_unresolved_prefix()` has no delete path at all.
**How to avoid:** Implement Pattern 6 (`clear_resolved_unresolved_prefix()`) as its own explicit step. Verify with a test that a prefix count frozen before resolution, with no further sightings, is still removed on the very next cycle that happens to see *any* flight with that prefix.
**Warning signs:** A Health-page manual test where a prefix is resolved but the registry row keeps showing its last `count`/`last_seen` unchanged forever (only cleared if a fresh sighting of the exact same prefix happens to occur, which may never happen for a rare carrier).

### Pitfall 2: Gating D-14's cleanup on `route_source`

**What goes wrong:** Cleanup implemented as `if route_source in ("airline_only", "manual"): unresolved_prefixes.pop(prefix, None)` inside the existing branch — this looks natural but is scoped to the wrong condition (see Pattern 6's explanation).
**Why it happens:** `route_source` is right there, already computed, at the exact point in `run_once()` where the cleanup logically wants to live — the reuse looks free.
**How to avoid:** Use `airline_from_callsign(callsign) is not None` (or the new `clear_resolved_unresolved_prefix()` helper) as the actual condition, independent of what `resolve_route()` returned for adsbdb this cycle.
**Warning signs:** A test where the ONLY resolved event this cycle is a `fresh_hit` (adsbdb answered) still fails to clean up an unrelated, already-resolvable-by-registry prefix — because that code path never ran the `airline_from_callsign()` check at all when gated on `route_source`.

### Pitfall 3: Widening `_ILLUSTRATION_FILENAMES`'s *write* path instead of only its *read* path

**What goes wrong:** "Widen the membership set" gets implemented by making `_handle_illustration_replace()` accept any key whose normalised form the manual registry happens to contain **at request time**, reopening exactly the T-v26-02-01 concern the phase's own corrections warn about (a key effectively originating from the current request rather than from already-persisted server state, if the widening check races the registry write).
**Why it happens:** It seems simpler to have one shared membership function reused by both the GET preview route and the write route.
**How to avoid:** Follow Pattern 3's two-step design — Step A persists the entry (server-side, validated) *before* Step B's upload ever runs, so by the time `_handle_illustration_replace()`'s (widened) membership check runs, the key is unambiguously already-persisted state, not a same-request inference.
**Warning signs:** A test that POSTs an upload for a key that was never previously registered, in a single request with no prior Step A call, and the upload succeeds — this should be impossible.

### Pitfall 4: Reserved-key name collision (`"Generic Fallback"`, `"Generic A320"`, etc.)

**What goes wrong:** An operator's free-typed name normalises to a key that collides with `generic-fallback.png` or a `generic-{shape}.png` file, and the panel silently renders that literal string as an airline caption for every uncovered-shape flight from then on (D-03 finds "existing art" and skips the upload prompt, masking the problem at write time).
**Why it happens:** `normalise_airline_key()` is a total function over any string; nothing currently stops it from producing a reserved-looking slug.
**How to avoid:** `add_entry()` rejects (with a clear, actionable flash) any submitted name whose normalised key equals `GENERIC_FALLBACK_FILENAME`'s stem or starts with `"generic-"`. See Pattern 7.
**Warning signs:** Manual QA: typing "Generic Fallback" into the resolve form succeeds silently instead of being rejected.

### Pitfall 5: Forgetting the drift guard's blast radius when adding the "manual" source row

**What goes wrong:** `health_page.py`'s `_SOURCE_ROWS` (`health_page.py:368-380`) is iterated by both `resolution_stats()` (to sum `total`) and the two render functions; adding a fifth tuple without also checking `history_db.route_source_counts()`'s SQL (`GROUP BY route_source`, no CHECK constraint — confirmed no schema change needed) means the only real risk is a **display-layer** omission, not a storage-layer one. But a test elsewhere (e.g. any harness that asserts `len(_SOURCE_ROWS) == 4` or enumerates the four historical values by name) would need updating.
**Why it happens:** The four-source enumeration is copied by value into several docstrings (`enrich.py:667-676`, `health_page.py:365-367`) that read naturally as exhaustive.
**How to avoid:** Grep for `"fresh_hit"`, `"cache_hit"`, `"airline_only"`, `"miss"` as a literal set before considering the change complete — every docstring/comment enumerating exactly these four values needs its own edit alongside the code change.
**Warning signs:** `EXPECTED_CHECK_COUNT` mismatches in `test_enrich.py`/`companion/test_status_pages.py` are actually a *safety net* here (the harness fails loudly if a new check is added without bumping the constant) — treat any such failure as "did I forget to declare a new check," not as a bug to suppress.

### Pitfall 6: `note_unresolved_prefix()`'s own docstring going stale

**What goes wrong:** `note_unresolved_prefix()`'s docstring (`enrich.py:754-787`) currently says recording happens "when `airline_from_callsign(callsign)` returns None (the prefix is genuinely absent from `_ICAO_AIRLINE_PREFIXES`, not just a differently-shaped string)" — this sentence becomes inaccurate the moment D-01 ships (the prefix might now be absent from *both* tables, not just the static one). Small, but exactly the kind of stale claim this codebase's own review discipline (the seed corrections that opened this phase) exists to catch.
**How to avoid:** Update this docstring, `airline_from_callsign()`'s own docstring (drop "Pure, no I/O, no network" or qualify it precisely — Pattern 1's split keeps the *public function* behaviorally simple but it is no longer literally I/O-free once the registry cache is populated), and the T-hyy-01/T-hyy-02 threat-note cross-references in the same edit.

## Code Examples

### The existing override-resolution seam this phase's art namespace relies on entirely unchanged (D-09)

```python
# Source: server/plane/illustrations.py:668-680 (verified via direct read)
def resolved_illustration_path(key, state_dir=None):
    """The single seam every tier of select_illustration() goes through:
    return the override path for `key` when it exists as a real file, else
    the vendored illustration_path_for_key(key) path when THAT exists as a
    real file, else None. Never raises."""
    override_path = override_path_for_key(key, state_dir)
    if override_path is not None and os.path.isfile(override_path):
        return override_path
    vendored_path = illustration_path_for_key(key)
    if vendored_path is not None and os.path.isfile(vendored_path):
        return vendored_path
    return None
```

### The existing "read once per cycle" precedent Pattern 2 mirrors

```python
# Source: server/poll_loop.py:717-725 (verified via direct read)
illustrations.set_override_state_dir(state_dir)

# CFG-01/CFG-12: read the user's saved theme + tracked runway ONCE per
# cycle, not once per call site - a mid-cycle save landing between two
# separate reads is exactly how a panel could end up rendered half in
# one theme/runway and half in another.
device_cfg = device_config.load_device_config(state_dir)
```

### The existing device_config.py tmp-write-then-replace idiom this phase's new registry file copies verbatim

```python
# Source: server/device_config.py:635-648 (verified via direct read)
os.makedirs(state_dir, exist_ok=True)
path = device_config_path(state_dir)
tmp = path + ".tmp"
try:
    with open(tmp, "w") as fh:
        json.dump(new_config, fh, indent=1)
    os.replace(tmp, path)
except Exception:
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    raise
```

### The existing `handle_post(form, ctx) -> flash_key` page-module contract this phase's new resolve/delete handlers should match

```python
# Source: companion/pages/__init__.py's documented contract (verified via direct read)
#   handle_post(form, ctx) -> str
#       Only modules that accept a form additionally expose this. `form` is
#       the plain {field: value} dict Handler.read_form() builds. The
#       return value is a flash key drawn from companion/app.py's fixed
#       FLASH_MESSAGES allowlist - never an arbitrary string rendered
#       later without going through that lookup.
```

## State of the Art

| Old Approach (this codebase, pre-Phase-13) | Current/New Approach (this phase) | When Changed | Impact |
|--------------------------------------------|-----------------------------------|---------------|--------|
| Every airline name→identity mapping lives in git-tracked Python literals (`_ICAO_AIRLINE_PREFIXES`, `_ILLUSTRATION_TARGETS`), reachable only by a commit+redeploy | A runtime-mutable JSON registry (`manual_resolutions.json`), reachable from the authenticated web UI, consulted *after* the static tables | This phase | First runtime-mutable identity namespace in the project (explicitly called out in `13-CONTEXT.md`'s own framing as "the hard part") |
| `airline_from_callsign()` is documented pure/no-I/O | Still pure-*shaped* in its public signature, but backed by a per-cycle-refreshed cache read | This phase | Every docstring/threat-note claiming "fixed table values or None" needs a precise re-statement, not a blanket "still true" |
| `resolve_route()` has exactly four source values, enumerated in several places | Five values; `"manual"` added | This phase | `health_page.py`'s `_SOURCE_ROWS`, any test enumerating the four values by name, and `enrich.py`'s own docstring all need the matching edit |
| `_ILLUSTRATION_FILENAMES` is a frozenset fixed at import time | A per-request union of static + manual-registry-derived keys | This phase | One more small JSON read per authenticated illustration-image request — consistent with this codebase's existing per-request-freshness cost elsewhere |

**Deprecated/outdated:** nothing from this phase deprecates any existing mechanism — D-09 is explicit that the illustration-selection ladder itself is untouched.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `server/plane/manual_resolutions.py` is the best new-module location (vs. e.g. a top-level `server/manual_resolutions.py` beside `device_config.py`) | Architecture Patterns / Recommended Project Structure | Low — either location works structurally; `server/plane/` was chosen because `enrich.py` (the primary reader) already lives there and imports its package-sibling `runway_config` the same way (`from server.plane import runway_config`, `enrich.py:58`). This is a naming/placement preference, not a functional risk; easy to relocate at plan time if the planner disagrees. [ASSUMED] |
| A2 | A hard cap-reject (rather than weakest-entry eviction, unlike `trim_unresolved_prefixes()`) is the right behavior for `manual_resolutions.py` hitting `MANUAL_RESOLUTION_MAX_ENTRIES` | Pattern 5 | Low-medium — this registry is authenticated-human-written, so hitting 200 entries organically is implausible; the choice only matters for a hypothetical compromised-session abuse case, and either eviction strategy is defensible. Needs no user confirmation but the planner should pick one explicitly rather than leaving it implicit. [ASSUMED] |
| A3 | `MANUAL_AIRLINE_NAME_MAX_LEN = 100` is a reasonable bound for a free-text airline name field | Pattern 5 | Low — no real airline name approaches 100 characters; this is a defensive bound, not a product decision, and any reasonable value (50-200) is equally safe. [ASSUMED] |
| A4 | Rejecting `"generic-"`-prefixed normalised keys (Pitfall 4) is worth doing at `add_entry()` time rather than leaving it as an accepted, documented edge case like D-08's orphaned-PNG cost | Common Pitfalls / Pattern 7 | Low — if the planner judges this not worth the extra validation branch, the fallback is simply documenting it as an accepted risk (same posture as D-08); it is not a security issue, only a cosmetic-caption risk requiring deliberate operator action to trigger. [ASSUMED] |

**If this table is empty:** N/A — see entries above. All four assumptions are low-risk implementation-detail judgment calls the planner can accept, adjust, or explicitly re-decide without needing developer sign-off; none touches a locked decision (D-01 through D-14) or a security-relevant boundary beyond what's already flagged as a Pitfall.

## Open Questions

1. **Does the resolve form's Step A route live at a new path (`POST /airlines/resolve`) or reuse `POST /airlines` itself, dispatched by a hidden `action` field?**
   - What we know: every existing companion route is a single fixed literal path per action (`POST /settings`, `POST /poll-now`, `POST /illustration/{key}.png`) — there is no existing precedent for one path handling multiple distinct form actions by a hidden discriminator field.
   - What's unclear: whether the planner prefers a new dedicated path (matching the one-path-per-action precedent) or folding it into `POST /airlines` for route-table brevity.
   - Recommendation: use a new dedicated path (`POST /airlines/resolve`, `POST /airlines/manual-resolutions/{prefix}/delete`) — it matches every existing route's shape and keeps `do_POST()`'s dispatch table a flat list of exact-path checks, consistent with the rest of `companion/app.py`.

2. **Where exactly does the D-07 management list (list + delete, active/superseded) render on the Airlines page relative to the gallery grid and the (conditional) resolve form?**
   - What we know: the Airlines page today is a single filter bar + gallery grid + shared lightbox (`airlines_page.py:544-575`); Health's own migrated registry/stats sections (`06.6.4.1-04`) are the closest precedent for "a second distinct list-shaped section on an otherwise single-purpose page."
   - What's unclear: exact placement/visual treatment is a UI-SPEC-level decision, not a research one — this belongs to whatever UI-SPEC step this phase's plan produces, informed by the `sketch-findings-skypane` skill's existing card/data-table/filter-bar patterns.
   - Recommendation: treat this as a planning/UI-SPEC task, not a research gap — the component vocabulary (`.page-section`, `.data-table`/`.data-cards` pairing, `layout.card_status_class()`) already exists and is directly reusable.

## Environment Availability

Skipped — this phase adds no new external dependency, service, or CLI tool. Every capability it needs (Python stdlib, the already-pinned `Pillow`) is already verified present and in active use by the exact code paths this phase extends.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | A custom, stdlib-only `check()`/`main()` harness per file (not pytest/unittest) — every test file defines `EXPECTED_CHECK_COUNT` and exits non-zero if the actual pass count doesn't exactly match it, self-guarding against a silently-forgotten new check |
| Config file | none — `scripts/run-all-tests.sh` is the single source of truth for the file list (currently 16 harnesses) |
| Quick run command | `server/.venv/bin/python3 server/test_enrich.py` (or any single harness file directly) |
| Full suite command | `scripts/run-all-tests.sh` |

### Phase Requirements → Test Map

This phase has no REQUIREMENTS.md ID (unmapped, matching Phases 10-12's precedent); the map below is keyed to this phase's own locked decisions instead.

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 | `airline_from_callsign()` resolves a manually-registered prefix after checking the static table; static wins on collision (D-06) | unit | `server/.venv/bin/python3 server/test_enrich.py` | ✅ existing file, new checks needed |
| D-02 | `resolve_route()` returns `"manual"` (not `"airline_only"`) when the manual registry, not the static table, resolved the prefix | unit | `server/.venv/bin/python3 server/test_enrich.py` | ✅ existing file, new checks needed |
| D-05 | New registry file load/save: never raises, tmp-write-then-replace, all-or-nothing rejection, bounded entries | unit | `server/.venv/bin/python3 server/test_manual_resolutions.py` | ❌ Wave 0 — new file |
| D-06 | A prefix resolved by hand, then later added to the static table, is reported "superseded" and the static name wins at runtime | unit | `server/.venv/bin/python3 server/test_enrich.py` + `companion/test_status_pages.py` | ✅ existing files, new checks needed |
| D-08 | Deleting a manual entry never deletes `illustration_overrides/{key}.png` | unit | `server/.venv/bin/python3 server/test_manual_resolutions.py` | ❌ Wave 0 — new file |
| D-09 | `select_illustration()`/`resolved_illustration_path()` behavior is byte-for-byte unchanged | regression | `server/.venv/bin/python3 server/test_illustrations.py` | ✅ existing file — this is a "must NOT change" check, i.e. the existing `EXPECTED_CHECK_COUNT` should hold with zero new checks needed here |
| D-11/D-12 | `?resolve={prefix}` is membership-tested against the live registry; displayed context is server-re-read, never taken from the query string | unit + integration | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ existing file, new checks needed |
| D-13 | The `<datalist>` offers exactly `illustrations.target_airline_names()`, escaped once | unit | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ existing file, new checks needed |
| D-14 | A resolved prefix is removed from `unresolved_prefixes` on the next `run_once()` cycle that observes it, independent of `route_source` | unit | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ existing file, new checks needed |
| Route/threat parity (T-v26-02-01) | `_ILLUSTRATION_FILENAMES` widening never admits a request-derived key, only server-persisted ones | integration | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ existing file, new checks needed |

### Sampling Rate

- **Per task commit:** the single most relevant harness for the file just touched (e.g. `server/test_enrich.py` after an `enrich.py` edit)
- **Per wave merge:** `scripts/run-all-tests.sh` (full suite)
- **Phase gate:** full suite green before `/gsd-verify-work`, plus the pyproject.toml coverage threshold `run-all-tests.sh` already enforces

### Wave 0 Gaps

- [ ] `server/test_manual_resolutions.py` — new harness file, same `check()`/`EXPECTED_CHECK_COUNT`/`main()` shape as `server/test_enrich.py`, covering the new `manual_resolutions.py` module's load/save/add/delete/cap contract (D-05, D-08)
- [ ] `scripts/run-all-tests.sh`'s canonical file-list array needs the new harness added (the script's own header comment documents this as "the single source of truth CI and README" — a new test file that isn't added here silently never runs in CI)
- [ ] No framework install needed — the existing venv/harness style covers this phase entirely

## Security Domain

`security_asvs_level: 1`, `security_block_on: "high"` per `.planning/config.json` — enforced below.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (existing, unchanged) | The two new POST routes sit behind the existing `require_session()` gate — no new authentication mechanism |
| V3 Session Management | yes (existing, unchanged) | `SameSite=Strict` session cookie is this app's whole CSRF control (`companion/auth.py:132`); the two new state-changing POSTs follow the same posture, no new token |
| V4 Access Control | yes (existing, unchanged) | Single-operator, single-role app — no new authorization tier needed |
| V5 Input Validation | yes — this phase's primary new surface | Prefix: validate-then-join against the live unresolved-prefix registry (D-11), never regex-shape-only. Airline name: length-bound (`MANUAL_AIRLINE_NAME_MAX_LEN`), then run through the existing total, safe `normalise_airline_key()` transform (never a new ad hoc sanitiser) — see Pitfall 4 for the one gap (reserved-key collision) worth an explicit guard. Uploaded image bytes: reuse `illustrations.validate_illustration_file()` and the existing Pillow re-encode pipeline verbatim (no new validation logic) |
| V6 Cryptography | no | Nothing in this phase touches cryptography, secrets, or tokens |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via a user-influenced filesystem key | Tampering | `normalise_airline_key()`'s total ASCII-slug transform (already relied on for adsbdb-sourced names) plus `_UNSAFE_KEY_RE`'s defense-in-depth check inside `illustration_path_for_key()`/`override_path_for_key()` — both unchanged by this phase, both still the sole path-construction boundary |
| Request-key impersonation of server-controlled state (the T-v26-02-01 concern named explicitly in `13-CONTEXT.md`) | Spoofing / Tampering | Pattern 3's two-step flow: a key only becomes writable/servable once it is durably persisted server-side by an already-authenticated, already-validated Step A request — Step B never trusts a key that didn't already pass through that gate |
| Registry file corruption / partial write | Tampering / DoS (self-inflicted) | The `device_config.py`-style tmp-write-then-`os.replace()` idiom (Pattern 5), copied structurally, never re-derived |
| Unbounded registry growth (authenticated-abuse or bug) | DoS | `MANUAL_RESOLUTION_MAX_ENTRIES` hard cap in `add_entry()`, mirroring `UNRESOLVED_PREFIX_MAX_ENTRIES`'s existing precedent |
| Decompression-bomb / malformed image upload | DoS | Unchanged — `illustrations.validate_illustration_file()`'s header-only pre-check runs before any pixel decode, exactly as it does for the existing gallery-replace path |
| Reflected/stored injection via the airline-name field reaching rendered HTML (Health's deep link display, the `<datalist>`, the management list) | Tampering (stored XSS) | Single escaping choke point — every interpolation of the stored `airline_name` goes through `companion.layout.escape_html()`, matching this codebase's existing, exhaustive convention (no new escaping mechanism needed, but every new render call site must actually use it — a checklist item for code review, not a new mitigation to design) |

## Sources

### Primary (HIGH confidence — direct read of the exact files this phase modifies)

- `server/plane/enrich.py` (full file, 858 lines) — `airline_from_callsign()`, `resolve_route()`, `note_unresolved_prefix()`, `trim_unresolved_prefixes()`, `_ICAO_AIRLINE_PREFIXES`, `_AIRLINE_NAME_CORRECTIONS`, `UNRESOLVED_PREFIX_MAX_ENTRIES`
- `server/plane/illustrations.py` (full file, 1012 lines) — `resolved_illustration_path()`, `override_path_for_key()`, `illustration_path_for_key()`, `_UNSAFE_KEY_RE`, `normalise_airline_key()`, `select_illustration()`, `target_filenames()`, `target_airline_names()`, `target_variants_by_airline()`
- `server/device_config.py` (lines 421-833) — `load_device_config()`/`save_device_config()`'s exact tmp-write-then-`os.replace()` contract, the `normalise_*` family
- `server/poll_loop.py` (lines 650-1213, `run_once()`) — the once-per-cycle `device_cfg`/`illustrations.set_override_state_dir()` precedent, the existing `unresolved_prefixes` bookkeeping block, the hold-state early-return placement precedent
- `server/history_db.py` (full file, 349 lines) — `runway_events` schema (confirmed `route_source TEXT`, no CHECK constraint), `route_source_counts()`
- `companion/app.py` (targeted reads: lines 440-1198, 1370-1488) — `_ILLUSTRATION_FILENAMES`, `parse_single_uploaded_file()`, `_serve_illustration_image()`, `_handle_illustration_replace()`, `page_context()`, `do_GET()`/`do_POST()` dispatch, `FLASH_MESSAGES`/`FLASH_ROLES` wiring pattern
- `companion/pages/airlines_page.py` (full file, 575 lines) — the existing lightbox/replace-form pattern, `_illustration_cache_buster()`, `render(ctx)`'s current shape
- `companion/pages/health_page.py` (targeted reads: lines 340-460, 1830-2145) — `_READ_ONLY_NOTE`, `_SOURCE_ROWS`, `unresolved_rows()`, `coverage_status()`, `resolution_stats()`, the registry table/card row builders
- `companion/pages/__init__.py` (full file) — the page-module boundary contract, the `ctx` dict shape
- `companion/auth.py` (lines 120-138) — `SameSite=Strict` CSRF posture
- `server/test_enrich.py` (targeted reads: lines 1-55, 370-800) — the existing `airline_from_callsign()`/`resolve_route()` test battery this phase's changes must not break
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`, all search-provider flags `false` (no external doc lookup available or needed)
- `.claude/CLAUDE.md` — stdlib-only posture, GSD workflow enforcement
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the companion app's live design-system reference

### Secondary (MEDIUM confidence — phase-context documents, treated as authoritative for decisions, not independently re-verified against code where they cite it)

- `.planning/phases/13-add-an-illustration-for-an-unidentified-flight-from-the-comp/13-CONTEXT.md` — the phase's locked decisions (D-01 through D-14), verified consistent with the code read above at every cross-reference checked
- `.planning/ROADMAP.md`'s Phase 13 entry — scope framing, confirmed consistent with 13-CONTEXT.md
- `.planning/REQUIREMENTS.md` — confirmed no REQ-ID exists for this phase (unmapped, matching precedent)

### Tertiary (LOW confidence)

None used — no web search was performed (all search-provider flags are `false` in `.planning/config.json`, and this phase introduces no new external technology to research).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new library; every existing dependency use was directly confirmed in the current codebase.
- Architecture: HIGH — every recommended pattern is grounded in an already-shipped structural precedent in this exact repo (`device_config.py`'s file contract, `illustrations.set_override_state_dir()`'s injection pattern, the existing upload handler's validation pipeline), not invented from general web-development knowledge.
- Pitfalls: HIGH — every pitfall traces to a specific, cited line range in the actual source, not a generic security-checklist item.

**A note on provenance tagging for this research:** every substantive claim above was verified by directly reading the file and line range cited, not recalled from training data or fetched from an external source (no external source exists for "what does this specific repository's code currently do"). Per this agent's tagging convention, such claims are marked `[VERIFIED: codebase read, <path>]` implicitly throughout the Architecture Patterns/Common Pitfalls sections via inline `Source:` citations, rather than repeating the tag on every sentence. The four items in the Assumptions Log are the only claims in this document that are genuinely `[ASSUMED]` (implementation-preference judgment calls, not verified facts) — none of them touches a locked decision or a security boundary.

**Research date:** 2026-09-05
**Valid until:** effectively indefinite for the architectural findings (they describe the current, static state of an internal codebase, not a fast-moving external ecosystem) — re-verify only if another phase modifies `enrich.py`, `illustrations.py`, `poll_loop.py`, or `companion/app.py` before this phase is planned/executed.
