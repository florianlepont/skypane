# Phase 14: Per-direction themes, per-flight colour rules and roster-linked highlighting - Research

**Researched:** 2026-09-06
**Domain:** Server-side configuration/resolution logic (Python stdlib), companion web-form plumbing — no new render code, no new external dependency, no on-glass surface
**Confidence:** HIGH (every claim below is grounded in a direct read of the actual code files named; no library research was needed because this phase adds zero new dependencies)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 14 = the resolution seam + per-direction theme + per-flight rules. The roster half is deferred, not dropped. It stays in SEED-003 as the explicitly deferred third step and is re-promoted as its own phase once export format and consent are in hand. A roster match will be a rule sourced automatically instead of typed.
- **D-02:** Nothing anticipatory is built for the roster half. Rules are purely manual; no reserved "origin"/"source" field, no dormant code path. The rule record's shape must stay *extensible* (documentation obligation on the store's module docstring, not a field).
- **D-03:** The developer's intent for the roster half was captured now, as notes (see Deferred Ideas), but none of it binds Phase 14.
- **D-04:** One theme plus an optional arrivals override — not two symmetric fields. `"theme"` keeps its meaning (frame's theme: departures, empty state, quiet-hours/display-off hold screens, Settings previews, anything not an arrival render). A second, optional key (name Claude's discretion, e.g. `theme_arriving`) holds the arrivals theme; unset means "same as `theme`". Consequences: existing `device_config.json` stays valid byte-for-byte with no migration; `load_device_config()` keeps returning every key; the new key joins `wake_interval_s` as the second key whose valid value set includes `None`; its `normalise_*` helper never raises and degrades an unrecognised id to `None` (= same as `theme`), NOT to `DEFAULT_THEME_ID`; `save_device_config()` gains the field with the same carry-forward-on-`None` contract, and — unlike `wake_interval_s` — this field **must** be clearable from the form (D-05), so an explicit "clear" path is needed, not only "carry forward".
- **D-05:** Settings: a checkbox under the Theme group reveals a second, identical chip grid. Locked-English module constants; wording Claude's discretion ("Use a different theme for arrivals"). Checked reveals a second `.theme-chip-grid` of the same 18 chips with the same rendered previews (`/theme-preview/{id}.png`, per theme id, not per direction). Unchecked at save time clears the override. The second grid is always present in HTML, hidden by the checkbox's state (no-JS-safe); checkbox follows existing `settings-checkbox` normalisation and absent-means-off semantics. Both values travel in the one existing Settings form/save bar.
- **D-06 (derived):** The override is the whole theme, for the whole panel, for arrival renders only. Empty/hold screens always use `theme`.
- **D-07:** A rule resolves to a registered theme id, never a raw colour. One of the 18 `THEMES` entries (band themes included).
- **D-08:** Three key kinds, each normalised the way the codebase already normalises it: exact callsign (`enrich.normalise_callsign()` output), ICAO24 hex (the `hex` the selection dict carries; case-folded, six hex characters), callsign prefix (three uppercase letters, same shape `manual_resolutions.normalise_prefix()` gates). Each kind gets a positive allowlist regex applied both before persisting and on every read (T-13-02 pattern). Registration (F-HBNA) is out — `detect._normalise_selection()` does not carry the aggregators' `r` field.
- **D-09:** Most specific wins: exact callsign > hex > prefix. One rule per key: store keyed on `(kind, value)`; adding a key that already exists replaces the previous entry. Derived: a matching rule beats the per-direction theme; rules are consulted only when a flight is displayed, never for the empty state or a hold screen.
- **D-10:** The editor lives on Settings, under the Theme group. Add form (key kind, value, target theme) + list with a delete control per row, mirroring Phase 13's manual-resolutions section. Add and delete are immediate actions on their own POST routes, outside the main Settings form and its dirty bar.
- **D-11:** The target theme is a native `<select>` of the 18 theme labels; each row shows a colour swatch (`_palette_hex(departing_index)`) plus the label. No third chip grid.
- **D-12 (derived):** The rule store is a dedicated JSON file in `state_dir`, following `manual_resolutions.py`'s contract exactly — never-raising load, per-field `normalise_*` gates, validate-before-write, tmp-write then `os.replace()`, stray-`.tmp` cleanup, a bounded entry count, a module-level write lock, companion writes / poll loop reads once per cycle. Not a growing list inside `device_config.json`. Cap is Claude's discretion (mirror `MANUAL_RESOLUTION_MAX_ENTRIES`).
- **D-13 (derived):** One resolution function, in a leaf module, applied to both render branches. Inputs: the displayed state, the displayed flight (`callsign`, `hex`), the once-per-cycle `device_cfg`, and the once-per-cycle rule registry; output: the effective theme id. Order: matching rule (D-09) → arrivals override when state is `"arriving"` (D-04) → `theme`. Runs after enrichment has settled the displayed flight and before `render.build_canvas()`; the same effective id must be used by the flight-detected branch AND the source-fault/battery re-render branch that draws the same flight again from `current_route`. The module must stay a leaf (`device_config.py` itself, or a sibling that imports only it), so `poll_loop` → resolver → `device_config` never cycles.

### Claude's Discretion

- Field and file names (`theme_arriving`, the rules file name, the rule record's field names), the rules cap, the hex normalisation details, and where exactly the resolver function lives (in `device_config.py` or a sibling leaf module).
- All user-facing copy for the new checkbox, the rules form, the list's empty state and the flash messages — locked-English constants (settled by 14-UI-SPEC.md already; see that file for the final copy deck).
- Whether the poll loop's log line and `run_once()`'s result dict report the effective theme id (recommended: yes) and whether History/Health surface that a rule fired (no requirement either way).
- Whether the second chip grid's previews reuse the on-disk cache as-is (recommended: yes).
- Test strategy, following the codebase's own harnesses (`server/test_config_history.py`-style device-config tests, `companion/test_config_page.py`, `server/test_poll_loop.py`, `server/test_pipeline_e2e.py`).

### Deferred Ideas (OUT OF SCOPE)

The roster half of SEED-003 (deferred by D-01; intent captured for a future phase — iCal subscription URL, theme-only rendering, flight-number+day match via `callsign_iata`, secret as an env var). Registration (tail number) as a rule key. A visible trace on History/Health that a rule/override fired. **None of this is to be researched, planned, or built in Phase 14.**
</user_constraints>

<phase_requirements>
## Phase Requirements

None. This is an unmapped phase promoted directly from a seed (`SEED-003`), matching Phases 10–13's precedent — confirmed against `.planning/REQUIREMENTS.md`'s Traceability table, which lists 17/17 v1 requirements mapped and contains no CFG-13+ or other ID reserved for this phase. `requirements.mark-complete` returning `not_found` for this phase's decisions (D-01…D-13) is expected, not an error, exactly as it was for Phases 10–13.

| ID | Description | Research Support |
|----|-------------|------------------|
| — | none | n/a |
</phase_requirements>

## Summary

This phase adds zero new dependencies and zero new render code. Its entire risk surface is server-side Python mechanics: (1) inserting one resolver call at the correct two points inside `server/poll_loop.py`'s `run_once()` — and *only* those two points — so a battery-icon repaint of an already-displayed flight can never silently change its theme; (2) extending `server/device_config.py`'s `device_config.json` contract with a field whose unset state is `None` (like `wake_interval_s`) but which, unlike `wake_interval_s`, must be explicitly clearable — a genuinely new requirement `save_device_config()`'s current "None always means carry-forward" contract cannot express without a new sentinel; and (3) a brand-new sibling registry module that copies `server/plane/manual_resolutions.py`'s file-safety contract (never-raising load, per-field validation, atomic write, write lock, bounded cap) but needs one behavioural extension `manual_resolutions.py` does not have: distinguishing "added" from "replaced" so the UI-SPEC's two distinct flash messages can fire correctly.

**Primary recommendation:** Build a new `server/plane/colour_rules.py` module (leaf-safe: imports only `server.device_config` + stdlib, never `enrich`/`detect`/`illustrations`/`manual_resolutions`) that owns the rules JSON file, its own three key-kind normalisers (callsign/hex/prefix — none of which can be borrowed from `enrich.py` or `manual_resolutions.py` without breaking the leaf constraint, so each is a small, deliberately duplicated primitive), and the resolver function itself. Wire exactly two call sites in `poll_loop.run_once()` (immediately before the flight-detected `build_canvas()` call and immediately before the held-branch re-render `build_canvas()` call when `confirmed_state is not None`) — the other four `build_canvas()` call sites in that function never display a flight and must keep using the bare `theme` id unchanged.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Effective-theme resolution (rule → arrivals override → base theme) | API/Backend (`server/poll_loop.py` + new `server/plane/colour_rules.py`) | — | Pure server-side decision logic; nothing here touches the panel's pixel composition, which stays `render.build_canvas()`'s job unchanged |
| Per-direction theme storage | API/Backend (`server/device_config.py`) | — | Same file/module that already owns `theme`, `tracked_runway`, etc. — this is a new key in an existing config store, not a new store |
| Per-flight rule storage | API/Backend (new `server/plane/colour_rules.py`, `state_dir` JSON) | — | Mirrors `manual_resolutions.py`'s precedent exactly: a runtime-writable registry the poll pipeline reads and the companion writes, never database-backed (this project has no general-purpose DB beyond `history_db.py`'s SQLite, which is CFG-06/08 history data, not config) |
| Settings UI (checkbox + second grid, rules add/delete forms) | Frontend Server (companion, `companion/pages/config_page.py`) | — | Already-settled by 14-UI-SPEC.md; server-rendered HTML, no client JS beyond the existing CSS `:has()` reveal |
| Rules add/delete routes | API/Backend (`companion/app.py`) | — | Immediate POST routes outside the dirty-bar form, mirroring Phase 13's `RESOLVE_ROUTE`/`MANUAL_DELETE_ROUTE_PREFIX` shape |
| Panel rendering | Database/Storage boundary N/A; Rendering tier (`server/plane/render.py`) | — | **Untouched.** `build_canvas(theme_id=...)` already accepts any registered theme id at every call site; this phase only changes *which* id is passed in, never the function's signature or body |

## Standard Stack

**No new libraries, no new packages, no new external services.** This phase is implemented entirely with the Python standard library (`json`, `os`, `re`, `threading`, `datetime`) — identical to every dependency `server/plane/manual_resolutions.py` and `server/device_config.py` already use. `server/requirements.txt` and `server/requirements-dev.txt` require zero edits.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `os`, `re`, `threading`, `datetime`) | 3.12 (project-pinned) | New rules registry file + resolver | Exactly what `manual_resolutions.py`/`device_config.py` already use for the identical class of problem — introducing a third-party JSON-schema or config library here would be the "don't hand-roll" mistake in reverse: this codebase's own established, security-reviewed pattern already solves this problem with zero dependencies |

### Supporting

None.

### Alternatives Considered

None — no library decision exists to weigh; the only "alternative" ever on the table (a database-backed rule store) was already rejected by D-12/13-CONTEXT.md's own precedent reasoning (Phase 13 D-05) before this research began.

**Installation:** none required.

## Package Legitimacy Audit

**Not applicable.** This phase installs no external packages in any ecosystem (Node/npm, Python/pip, Rust/cargo, or otherwise). `server/requirements.txt`/`server/requirements-dev.txt` are not touched. The Package Legitimacy Gate is skipped per its own trigger condition ("every phase that installs external packages").

## Architecture Patterns

### System Architecture Diagram

```
Companion (long-running ThreadingHTTPServer)
  POST /settings                 -> config_page.handle_post()
    - theme / theme_arriving_enabled / theme_arriving
    - (validated, then) device_config.save_device_config(..., theme_arriving=<id|CLEAR|None>)
  POST /settings/rules/add       -> new route in companion/app.py
    - rule_kind / rule_key / rule_theme_id
    - colour_rules.add_rule(state_dir, kind, key, theme_id) -> ADD_OK_NEW | ADD_OK_REPLACED | ADD_REJECTED_* | ADD_FAILED
  POST /settings/rules/{kind}/{value}/delete
    - colour_rules.delete_rule(state_dir, kind, value) -> True/False
  GET  /settings                 -> config_page.render(ctx)
    - ctx["colour_rules"] = colour_rules.load_colour_rules(state_dir)   (fresh per request, NEVER the cache)

                                        |
                                        v  (writes land in state_dir/*.json)

Poll oneshot (server/poll_loop.py, run_once(), fires every wake_interval_s)
  1. device_cfg = device_config.load_device_config(state_dir)      [theme, theme_arriving, ...]
  2. colour_rules.set_colour_rules_state_dir(state_dir)            [cache the registry, once per cycle]
     (beside the existing illustrations.set_override_state_dir() /
      manual_resolutions.set_manual_registry_state_dir() calls)
  3. ... hold-check early-return (unchanged; rules/override never apply here) ...
  4. ... detection, pacing/promotion, confirmed_state inference ...
  5. Flight-detected branch, confirmed_state is not None:
       effective_theme_id = colour_rules.resolve_effective_theme_id(
           render_state, current_flight, device_cfg)
       render.build_canvas(current_flight, render_state, theme_id=effective_theme_id, ...)
  6. Held/re-render branch, confirmed_state is not None:
       effective_theme_id = colour_rules.resolve_effective_theme_id(
           render_state, current_flight, device_cfg)   # SAME function, SAME inputs shape
       render.build_canvas(current_flight, render_state, route=current_route,
                            theme_id=effective_theme_id, ...)
  (all four other build_canvas() call sites — empty state x2, both hold screens —
   keep passing theme_id=theme_id, the bare base theme, UNCHANGED)
```

### Recommended Project Structure

```
server/
├── device_config.py          # +theme_arriving field, +normalise_theme_arriving(), +CLEAR sentinel
├── plane/
│   ├── colour_rules.py       # NEW — mirrors manual_resolutions.py's file contract + the resolver
│   ├── manual_resolutions.py # unchanged — reused only as a design template, never imported
│   └── enrich.py             # unchanged — normalise_callsign() is NOT imported by colour_rules.py (leaf rule); its shape is duplicated inline
├── test_colour_rules.py      # NEW — mirrors server/test_manual_resolutions.py's harness shape
└── poll_loop.py               # +2 call sites, +1 cache-priming call

companion/
├── app.py                    # +2 routes (rules add/delete), +ctx["colour_rules"]
├── pages/
│   └── config_page.py        # +checkbox+second grid in theme_fieldset(), +rules section, +handle_post() fields
└── test_config_page.py       # extended — new checks + repaired count-shaped assertions
```

### Pattern 1: The two-call-site resolver insertion (research target 1)

**What:** `run_once()` has exactly **six** `render.build_canvas()` call sites. Only **two** of them display a flight and therefore need the resolver; the other four never display a flight and must keep using the bare `theme` id.

| Line (approx.) | Branch | Displays a flight? | Resolver applies? |
|---|---|---|---|
| ~824 | Hold early-return (`quiet_hours`/`display_off`) | No | No — base `theme_id` |
| ~1027 | Flight-detected, `confirmed_state is None` → `"empty"` | No | No — base `theme_id` |
| **~1109** | **Flight-detected, `confirmed_state` resolved** | **Yes** | **Yes** |
| **~1188** | **Held/re-render branch, `confirmed_state is not None`** | **Yes** | **Yes** |
| ~1201 | Held/re-render branch, `confirmed_state is None` → `"empty"` | No | No — base `theme_id` |
| ~1235 | Nothing ever detected → `"empty"` | No | No — base `theme_id` |

**When to use:** Insert `effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)` as the single line immediately before each of the two flagged `build_canvas()` calls, then pass `theme_id=effective_theme_id` instead of `theme_id=theme_id` at those two call sites only.

**The ordering trap (analogous to Phase 10's hold-gate-placement pitfall — CONFIRMED to exist here too):** The naturally tempting insertion point is right beside the existing per-cycle reads at the top of `run_once()` — `device_cfg = device_config.load_device_config(state_dir); theme_id = device_cfg["theme"]` (~line 741-742) — by analogy with how `theme_id`/`tracked_runway_id` are read once, early, for the whole cycle. **This is wrong for the resolver.** `theme_id`/`tracked_runway_id` need no flight context at all, so hoisting them to the top is safe. The resolver's two required inputs — `render_state` (`"departing"`/`"arriving"`) and `current_flight` (the settled displayed aircraft) — are **not stable or even fully defined** until deep inside each of the two branches: `render_state` is not known until `runway_config.infer_from_flight()` returns a non-`None` `confirmed_state` (~line 1016, flight-detected branch) or until `current_confirmed_state` is read back from `poll_state` (~line 1147, held branch); `current_flight` itself is not finalised until after the pacing/promotion logic runs (~line 998-1003). A resolver call hoisted to the top of `run_once()` would either crash (`current_flight`/`render_state` not yet bound) or — worse, if written defensively with `.get()` fallbacks — silently resolve against stale or `None` values from the *previous* cycle. The registry-cache-priming call (`colour_rules.set_colour_rules_state_dir(state_dir)`) is the ONLY piece of this feature that is safe to hoist to the top, alongside the existing `illustrations.set_override_state_dir()`/`manual_resolutions.set_manual_registry_state_dir()` calls (~line 732-733) — loading a small JSON file unconditionally, even on cycles that never end up needing it, is cheap and matches the established per-cycle-cache-priming precedent exactly.

**Battery-icon-repaint invariant, verified safe by construction:** The held/re-render branch (line ~1188) reads `current_flight = poll_state.get("last_flight")` (~line 915) — the *exact same* dict the flight-detected branch wrote via `poll_state["last_flight"] = current_flight` on the cycle that first displayed it (~line 1125). Both branches therefore see the same `hex`/`callsign` for the same underlying displayed aircraft across cycles, and both read the same fresh `device_cfg`/rules-registry cache each cycle. As long as `resolve_effective_theme_id()` is a pure function of `(render_state, flight.hex, flight.callsign, device_cfg, rules_registry)` — with no cycle-local mutable state — the same flight cannot change theme between a "just detected" cycle and a later "battery icon repaint only" cycle, unless the operator actually edited a rule or the arrivals override in between (which is the correct, intended behaviour).

### Pattern 2: `device_config.py`'s clearable-field extension (research target 2)

**What `wake_interval_s` actually does today (verified by direct read, not assumption):** `save_device_config()`'s signature is `(state_dir, theme=None, tracked_runway=None, ..., wake_interval_s=None, display_enabled=None)` — every parameter defaults to `None`, and `None` universally means "not supplied, carry forward the current on-disk value" (`new_config["wake_interval_s"] = wake_interval_s if wake_interval_s is not None else current["wake_interval_s"]`). There is **no third state**. This is confirmed both in the source (`server/device_config.py:613-621, 631`) and in STATE.md's own record: *"save_device_config() has no way to clear an already-set wake_interval_s back to unset — an empty input means leave unchanged, resolving 11-RESEARCH.md Open Question 2"* [VERIFIED: server/device_config.py, cross-checked against STATE.md's Phase 11 decision log].

**Why `theme_arriving` cannot reuse this exact contract:** D-04/D-05 require the arrivals-override checkbox to genuinely **clear** the field back to `None` when unchecked — the opposite of `wake_interval_s`'s "empty input means leave unchanged" resolution. Since `theme_arriving=None` is already claimed as "caller didn't supply this parameter, carry forward," a second, distinct value is needed to mean "caller explicitly wants this cleared."

**Recommended pattern — a module-level sentinel, mirroring this codebase's own existing idiom:** `companion/pages/health_page.py` and `companion/pages/history_page.py` already use exactly this idiom for an unrelated purpose (`_DB_UNAVAILABLE = object()`, distinguishing "query raised" from "query returned nothing"). Reusing the same idiom in `device_config.py`:

```python
# server/device_config.py
CLEAR_THEME_ARRIVING = object()  # sentinel: "explicitly unset", distinct from
                                  # None ("caller didn't supply this parameter,
                                  # carry forward the current on-disk value" —
                                  # the meaning every OTHER save_device_config()
                                  # parameter already has and keeps having).

def normalise_theme_arriving(value):
    """Unlike normalise_theme_id() (which degrades an unrecognised value to
    DEFAULT_THEME_ID), this degrades to None — 'no override', i.e. 'same as
    theme' (D-04). Mirrors normalise_wake_interval_s()'s degrade-to-None
    shape, not normalise_theme_id()'s degrade-to-default shape."""
    if isinstance(value, str) and value in THEMES:
        return value
    return None

# inside save_device_config(...), new parameter theme_arriving=None:
if (theme_arriving is not None and theme_arriving is not CLEAR_THEME_ARRIVING
        and theme_arriving not in THEMES):
    raise ValueError("unknown theme_arriving id %r (expected one of %r or None)" % (theme_arriving, THEME_IDS))
...
new_config["theme_arriving"] = (
    None if theme_arriving is CLEAR_THEME_ARRIVING
    else theme_arriving if theme_arriving is not None
    else current["theme_arriving"]
)
```

`config_page.handle_post()` then decides which of the three values to pass based on the checkbox, not the grid's own submitted value — **critical**, because D-05 requires the second grid to be *always present* in the HTML (for no-JS correctness), meaning `form.get("theme_arriving")` will **always** carry a valid theme id string regardless of whether the checkbox is checked. The checkbox (`theme_arriving_enabled`), not the presence/absence of `theme_arriving` in the form, is the actual clear-vs-set signal:

```python
submitted_arriving_enabled = form.get("theme_arriving_enabled")
submitted_theme_arriving = form.get("theme_arriving")
if submitted_theme_arriving is not None and submitted_theme_arriving not in device_config.THEME_IDS:
    return FLASH_SAVE_FAILED
if submitted_arriving_enabled == ARRIVING_CHECKBOX_VALUE:
    theme_arriving = submitted_theme_arriving   # already membership-checked above
else:
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
...
device_config.save_device_config(..., theme_arriving=theme_arriving)
```

This is the ONLY place in the whole write path that needs to know the sentinel exists — `load_device_config()` never sees it (it only ever reads `None` or a valid theme id back off disk).

**Alternative considered (documented, not recommended):** add a second boolean parameter `clear_theme_arriving=False` to `save_device_config()` instead of a sentinel value. Functionally equivalent; rejected as the primary recommendation only because it adds an asymmetric extra parameter to a function whose other seven fields all follow the identical `None`-means-carry-forward shape, whereas the sentinel keeps every parameter's arity and default identical and only widens what `None`'s sibling values can mean for this one field — matching the "one exception, well-marked" precedent `wake_interval_s`'s own docstring already sets (*"a single deliberate exception to this module's otherwise-universal... contract"*). Either is viable; this is genuinely Claude's Discretion per CONTEXT.md, not a locked decision — flagged in the Assumptions Log below.

### Pattern 3: The rules registry — copying `manual_resolutions.py`'s contract, with one deliberate extension

**The checklist a sibling module must satisfy (from a full read of `server/plane/manual_resolutions.py`, D-12's named template):**

- [ ] Never-raising `load_*()`: a missing file, unreadable file, invalid JSON, or non-dict top level all degrade to `{}` (or the module's equivalent empty registry shape) — never raise.
- [ ] Every loaded entry is **rebuilt from scratch**, never the parsed dict reused directly — each field re-validated through its own `normalise_*()` gate; a value that fails any gate is dropped, not coerced.
- [ ] A hard entry-count cap (mirror `MANUAL_RESOLUTION_MAX_ENTRIES = 200`), enforced by `break`-ing the load loop once the cap is reached (never `continue`-scanning the remainder — that reopens the unbounded-render risk the cap exists to close).
- [ ] A printed (not raised) warning when the raw on-disk file holds more entries than survive validation, naming the drop count — so silent data loss is at least visible in the service log (`manual_resolutions.py`'s WR-03 fix).
- [ ] `add_*()` validates **every** field, in order, before touching the filesystem at all — the write is the last step, gated behind every check.
- [ ] Write path: `os.makedirs(state_dir, exist_ok=True)`, write to a temp file whose name embeds `os.getpid()` and `threading.get_ident()` (not a single fixed `path + ".tmp"` — two concurrent writers under `ThreadingHTTPServer` must never share one temp filename), then `os.replace(tmp, path)`.
- [ ] Any exception during the write is caught, the stray temp file is removed if present, and a **result code** is returned — never a re-raised exception (the caller is an HTTP route handler that needs a flash key, not a traceback).
- [ ] A single **module-level `threading.Lock()`** (`_WRITE_LOCK`) wraps the entire load-check-mutate-write sequence in both `add_*()` and `delete_*()` — not just the final `os.replace()` — closing the read-modify-write race two concurrent companion requests could otherwise hit (WR-02 fix).
- [ ] A process-scoped cache (`_cached_registry` module global) + `set_*_state_dir(state_dir)` setter, mirroring `illustrations.set_override_state_dir()` — for the **poll pipeline only**. The companion service (a long-running `ThreadingHTTPServer`) must **never** read through this cache; every companion request calls the fresh `load_*(state_dir)` directly, exactly as `page_context()` already does for `manual_resolutions.load_manual_resolutions(state_dir)`.
- [ ] `entry_rows(registry)`-style helper returning sorted, defensively-typed tuples for rendering — never raises on a malformed loaded entry.
- [ ] Result-code constants (`ADD_OK`, `ADD_REJECTED_*`, `ADD_FAILED`) that are **not** flash keys themselves — the HTTP layer maps them onto its own flash-key vocabulary, keeping the registry module ignorant of companion-specific presentation concerns.
- [ ] **The import-cycle rule, stated explicitly in `manual_resolutions.py`'s own module docstring:** it imports `server.plane.illustrations` (a dependency it needs) but documents that it must **never** import `server.plane.enrich` — that direction is reserved for `enrich` to import `manual_resolutions`; the reverse would be a cycle. **The equivalent rule for `colour_rules.py` (D-13):** it may import `server.device_config` (for `THEME_IDS` membership validation) but must **never** import `server.plane.enrich`, `server.plane.detect`, `server.plane.illustrations`, `server.plane.manual_resolutions`, or `server.plane.render` — `poll_loop.py` already imports all of those plus the new module, and none of them may import back into it, or `poll_loop → colour_rules → X → poll_loop` becomes a real cycle risk the moment any of those modules' own import graphs shift.

**The deliberate extension `manual_resolutions.py` does NOT have, that `colour_rules.py` DOES need:** Phase 13's `add_entry()` always returns `ADD_OK` on success — Phase 13's UI has no "this replaced something" flash message. Phase 14's UI-SPEC explicitly requires two distinct success flashes (`rule_added` vs `rule_replaced`, D-09's "make replaced legible" requirement). This means `add_rule()`'s result vocabulary must extend beyond a literal copy of `manual_resolutions.py`'s `ADD_*` constants — e.g. `ADD_OK_NEW` / `ADD_OK_REPLACED` instead of a single `ADD_OK`, computed by checking `(kind, value) in registry` **before** the mutation, inside the same `_WRITE_LOCK`-held critical section `manual_resolutions.add_entry()` already uses for its own pre-cap membership check. This is the single most important deviation from "copy the file exactly" — call it out explicitly in the plan so it is not lost as an unstated implementation detail.

**Registry shape recommendation (Claude's Discretion, not locked):** nest by kind rather than flattening `(kind, value)` into one string key, so "most specific wins" lookup is a simple three-step chain with no risk of cross-kind key collision:

```json
{
  "callsign": {"AFR1234": {"theme_id": "white", "created_at": "2026-09-06T12:00:00+00:00"}},
  "hex": {"3944F2": {"theme_id": "blue", "created_at": "..."}},
  "prefix": {"AFR": {"theme_id": "red", "created_at": "..."}}
}
```

### Pattern 4: Key normalisation for the three rule kinds (research target 4)

**Callsign:** `enrich.normalise_callsign()` (line ~114) is `raw.strip().upper() or None` — trivial, but **cannot be imported** by `colour_rules.py` without breaking the leaf constraint (`enrich.py` is not a leaf; it has its own substantial dependency graph including `requests`). Recommend duplicating the one-line primitive inline in `colour_rules.py`'s own `normalise_rule_callsign()`, plus a shape gate mirroring `enrich._CALLSIGN_SAFE_RE = re.compile(r"^[A-Z0-9]+$")` and `_AIRLINE_PREFIX_SHAPE_RE`'s documented real-world bound ("real callsigns are at most eight characters" — enrich.py's own comment near line 867) — e.g. `_CALLSIGN_RULE_RE = re.compile(r"^[A-Z0-9]{2,8}$")`. This is not a new pattern for this codebase: `stub-server/byos_server.py` already duplicates `seconds_until_quiet_hours_end()` byte-for-byte across a vendor boundary rather than import across it, for the identical structural reason (a layering rule the codebase has chosen not to cross).

**Callsign prefix:** `manual_resolutions.normalise_prefix()`'s exact shape — `^[A-Z]{3}$` after strip+upper. `colour_rules.py` should **not** import `manual_resolutions.py` either (same leaf-constraint reasoning) — duplicate the two-line regex+strip+upper primitive, exactly as `manual_resolutions.py` itself independently redefines constants other modules also define, rather than import across an unrelated module boundary. `enrich._AIRLINE_PREFIX_SHAPE_RE = re.compile(r"^[A-Z]{3}[A-Z0-9]+$")` is a *different* thing (a full-callsign shape gate used before deriving a prefix from it) and is not the right primitive to copy for a rule that is *itself* keyed on a bare 3-letter prefix.

**ICAO24 hex:** **No normaliser exists anywhere in this codebase today** — confirmed by an exhaustive grep of `server/` and `companion/` for `icao24`/`hex_re`/`HEX_RE`. The raw `hex` field flows through `detect._normalise_selection()` completely unvalidated (`"hex": winner.get("hex")`) and real fixture data shows it arrives as a **lowercase** 6-character hex string (e.g. `"39de4a"`, `"3985a7"` — confirmed in `server/fixtures/*.json`). D-08 says "case-folded, six hex characters" — this is new ground; recommend canonicalising to **uppercase** (matching the UI-SPEC's rendered example `3944F2` and the mono-cell "uppercase as stored" convention already used for the prefix column elsewhere): `_HEX_RULE_RE = re.compile(r"^[0-9A-F]{6}$")`, applied after `raw.strip().upper()`. At match time, `current_flight["hex"]` must be upper-cased the same way before the registry lookup, since the live value is lowercase.

**The T-13-02 threat pattern these answer:** a positive allowlist regex, applied both before persisting (`add_rule()`) and on every read (`load_colour_rules()`), so a hand-edited or corrupted registry file can never smuggle a value shaped to collide with something unintended into a live comparison. Note the risk profile here is narrower than Phase 13's original T-13-02 (which was about a value reaching *filesystem path construction* via `illustration_path_for_key()`) — rule values are only ever used as **JSON dict keys** and as operands in a **string equality/membership comparison** against `current_flight`'s fields, never joined into a path. The allowlist is still the correct control (ASVS V5, "never trust a value's shape before it's checked"), but the specific failure mode it prevents here is a malformed/hostile value causing an incorrect or crafted match, not path traversal.

### Pattern 5: Companion route/form plumbing (research target 5)

Confirmed from a direct read of `companion/app.py` (lines ~1330-1460) and `companion/pages/airlines_page.py`:

- **Route dispatch:** `Handler.do_POST()`'s flat `if path == X: return self._handle_Y()` chain (companion/app.py ~1707-1747). Phase 14 adds two more branches: `if path == RULES_ADD_ROUTE: return self._handle_rule_add()` and a prefix/suffix match exactly like the existing `if path.startswith(airlines_page.MANUAL_DELETE_ROUTE_PREFIX) and path.endswith(airlines_page.MANUAL_DELETE_ROUTE_SUFFIX):` pattern — except Phase 14's delete route needs **two** path segments (`{kind}/{value}`), not one, since the store key is a `(kind, value)` pair (D-09). Recommend a route shape of `/settings/rules/{kind}/{value}/delete` with a prefix of `/settings/rules/` and a suffix-check via `.endswith("/delete")`, then split the middle segment on `/` once (matching the UI-SPEC's own stated route shape).
- **Auth gate:** every state-changing POST route in this file is reached only after `require_session()` runs earlier in `do_POST()` — a single whole-site gate, not a per-route decorator. Phase 14's two new routes need no new gate; they fall under the same existing check.
- **Flash round-trip:** every add/delete route redirects with `?flash={key}` (occasionally `&resolve={value}` for Phase 13's specific case, not needed here), and `page_context()` resolves `flash_key` into `ctx["flash"]`/`ctx["flash_role"]` via `_resolve_flash_text()`/`FLASH_ROLES.get(flash_key, "status")` — Phase 14 needs 7 new entries in `FLASH_MESSAGES` and `FLASH_ROLES` (per 14-UI-SPEC.md's exact copy deck: `rule_added`, `rule_replaced`, `rule_key_invalid`, `rule_registry_full`, `rule_save_failed`, `rule_deleted`, `rule_delete_failed`).
- **`page_context()` plumbing:** exactly one new key, `ctx["colour_rules"] = colour_rules.load_colour_rules(state_dir)`, read **fresh per request** — never the poll-cycle cache — mirroring `ctx["manual_resolutions"] = manual_resolutions.load_manual_resolutions(state_dir)`'s own comment: *"Read fresh per request... never the process-scoped cache... This service is a long-running ThreadingHTTPServer."* `companion/pages/__init__.py`'s documented `ctx` contract docstring must be updated to name this new key (matching the discipline every prior key addition there followed).
- **No CSRF token needed:** this app's documented CSRF control is the session cookie's `SameSite=Strict` flag (companion/auth.py:132), applied uniformly to every state-changing POST — the two new rules routes inherit this for free, no new mechanism.

### Anti-Patterns to Avoid

- **Reading the rules registry through the poll-cycle cache from a companion request handler.** `manual_resolutions.py`'s own docstring flags this explicitly as a **caching warning**, not a hypothetical: the cache is for the once-per-cycle poll pipeline only; a companion page render must always call the fresh loader.
- **Applying the resolver to any of the four flight-less `build_canvas()` call sites.** D-09 is explicit: "rules are consulted only when a flight is displayed, never for the empty state or a hold screen." Applying it universally (e.g. by refactoring `theme_id = theme_id` into a blanket `theme_id = resolve(...)` reassignment near the top of `run_once()`) would violate this and — worse — would require `resolve_effective_theme_id()` to defensively handle a `None` flight, silently masking the "must never run before the flight is settled" ordering trap documented in Pattern 1.
- **Treating `theme_arriving`'s `None` the same way `wake_interval_s`'s `None` is treated inside `save_device_config()`.** They must diverge; see Pattern 2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic, corruption-safe JSON registry writes under a `ThreadingHTTPServer` | A custom locking/temp-file scheme | Copy `manual_resolutions.py`'s exact tmp-write-then-`os.replace()` + pid/thread-scoped temp filename + module-level `threading.Lock()` idiom | This exact problem (two concurrent companion requests writing the same small JSON file) was already solved, reviewed, and hardened in Phase 13 (WR-02/WR-03 fixes documented in that module's own docstring) — re-deriving it risks reintroducing a race already found and closed once |
| "Is this theme id still valid" gating | An ad-hoc string check inline at each call site | `theme_id in device_config.THEMES` / the existing `normalise_theme_id()` family's membership-test discipline | Every other place in this codebase that accepts a theme id (Settings' `handle_post()`, `theme_background_index()`, etc.) already does this identically; a rules-registry-local re-implementation would be the one place in the codebase that diverges |
| Distinguishing "added" from "replaced" on an upsert | A second read-before-write outside the lock (a TOCTOU race) | Check `(kind, value) in registry` **inside** the same `_WRITE_LOCK`-held critical section the existing cap-check already uses | `manual_resolutions.add_entry()`'s own cap check (`if normalised_prefix not in registry and len(registry) >= MANUAL_RESOLUTION_MAX_ENTRIES`) already demonstrates the correct pattern: membership-test the loaded registry inside the lock, before mutating |

**Key insight:** every mechanical problem this phase's server-side half poses (atomic writes, never-raising loaders, positive-allowlist validation, module-level locking, process-scoped per-cycle caching) was already solved once in this exact codebase, for the exact same class of file (a small, operator-editable, `state_dir`-resident JSON registry). The only genuinely new problems are (a) the clearable-field sentinel (Pattern 2) and (b) the added/replaced result-code distinction (Pattern 3) — everything else is disciplined copying, not invention.

## Common Pitfalls

### Pitfall 1: Hoisting the resolver call to the top of `run_once()`, by analogy with `theme_id`/`tracked_runway_id`
**What goes wrong:** `current_flight`/`render_state` are not yet defined (or are stale, from a prior cycle) at the point `theme_id = device_cfg["theme"]` is read.
**Why it happens:** The existing per-cycle-read pattern (`device_cfg` read once, early) looks like a template to extend for "yet another once-per-cycle value," but the resolver's dependency on the *settled displayed flight* — which is branch-dependent and only known deep inside two of the six `build_canvas()` branches — breaks that analogy.
**How to avoid:** Only hoist the **cache-priming** call (`colour_rules.set_colour_rules_state_dir(state_dir)`) to the top, beside the existing `illustrations`/`manual_resolutions` priming calls. Compute the resolver's actual *output* at exactly the two call sites identified in Pattern 1.
**Warning signs:** A plan or diff that adds a single `effective_theme_id = ...` line near line 741-742 rather than two lines near 1108 and 1187.

### Pitfall 2: Treating `theme_arriving=None` as "clear" instead of "carry forward" inside `save_device_config()`
**What goes wrong:** Every other field's contract breaks the moment `None` gains a second meaning for one field only, without a distinguishing sentinel — a caller that legitimately omits `theme_arriving` (e.g., a future script or test that only wants to update `theme`) would unexpectedly wipe out a previously-set arrivals override.
**Why it happens:** `wake_interval_s` already normalized "the checkbox/field is empty" to `None` at the `handle_post()` layer (11-RESEARCH.md Open Question 2) — but that resolution was for the *opposite* requirement (never clearable). Copying that resolution here inverts the intended behaviour.
**How to avoid:** Use the sentinel pattern in Pattern 2; keep `None` meaning "not supplied" for `theme_arriving` exactly like every other field.
**Warning signs:** `handle_post()` code that maps "checkbox unchecked" directly to `theme_arriving=None` and hands it straight to `save_device_config()`.

### Pitfall 3: Assuming the second theme-chip grid's submitted value signals "clear" by its absence
**What goes wrong:** Because D-05 requires the second grid to be *always rendered* in HTML (no-JS correctness), `form.get("theme_arriving")` is essentially always present with a valid theme id, checkbox state notwithstanding. Code that branches on `if "theme_arriving" not in form: clear` will never see that branch fire in a normal browser submission.
**How to avoid:** Branch on the checkbox field (`theme_arriving_enabled`) alone, as shown in Pattern 2 — never on the presence/absence of `theme_arriving` itself.

### Pitfall 4: Reusing `ADD_OK` for both "added" and "replaced" and trying to distinguish them at the HTTP layer instead
**What goes wrong:** By the time `companion/app.py`'s route handler gets a bare `ADD_OK` back, the pre-write registry state is gone — a second `load_colour_rules()` call to check "was it already there" would race against the write that just happened (TOCTOU), and could itself be defeated by a concurrent request.
**How to avoid:** Do the added-vs-replaced membership check inside `colour_rules.add_rule()`, inside the same lock, before mutating — return a result code that already encodes the answer.

### Pitfall 5: The pre-existing `test_poll_loop.py` digest-pin note
**What goes wrong (not a Phase 14 defect, but will be encountered):** `server/test_poll_loop.py` pins an expected SHA-256 digest of the rendered `panel.bin` for a fixed fixture, produced on Linux CI. Running the suite locally on macOS is documented, throughout this project's history, to produce a *different but expected* digest due to Pillow/FreeType font-rendering variance between platforms — the harness's own `_digest_verdict()` classifies this as a soft NOTE, not a hard FAIL, and `scripts/run-all-tests.sh` still reports overall `Result: PASS` when only this note fires.
**How to avoid blaming Phase 14 for it:** Confirm, before starting Phase 14 work, whether this note is already present on a clean checkout (it has been present intermittently since Phase 6.3 per STATE.md's own repeated documentation of it). If it is, it is pre-existing and environment-specific, not introduced by this phase's changes — do not attempt to "fix" it as part of this phase's verification.

## Code Examples

### Resolver function shape (illustrative — exact field names are Claude's Discretion)

```python
# server/plane/colour_rules.py — imports ONLY server.device_config + stdlib

def resolve_effective_theme_id(state, flight, device_cfg):
    """D-13's one resolution function. `state` is "departing"/"arriving";
    `flight` is the current_flight dict (has "callsign"/"hex", may lack
    either); `device_cfg` is this cycle's already-loaded
    device_config.load_device_config() dict. Reads the process-global
    rules cache set once per cycle by set_colour_rules_state_dir() — never
    touches disk itself. Never raises; always returns a THEME_IDS member.

    Order (D-09/D-04): exact callsign rule > hex rule > prefix rule >
    arrivals override (only when state == "arriving") > base theme.
    """
    callsign = _rule_callsign(flight.get("callsign") if isinstance(flight, dict) else None)
    hex_value = _rule_hex(flight.get("hex") if isinstance(flight, dict) else None)
    prefix = callsign[:3] if callsign and len(callsign) >= 3 else None

    rule_theme = None
    if callsign is not None:
        rule_theme = _cached_rules.get("callsign", {}).get(callsign, {}).get("theme_id")
    if rule_theme is None and hex_value is not None:
        rule_theme = _cached_rules.get("hex", {}).get(hex_value, {}).get("theme_id")
    if rule_theme is None and prefix is not None:
        rule_theme = _cached_rules.get("prefix", {}).get(prefix, {}).get("theme_id")
    if rule_theme is not None and rule_theme in device_config.THEMES:
        return rule_theme

    if state == "arriving":
        arriving = device_cfg.get("theme_arriving")
        if arriving is not None:
            return arriving

    return device_cfg["theme"]
```

### `run_once()` insertion (illustrative diff shape, not exact line numbers)

```python
# beside the existing cache-priming calls, near line 733:
colour_rules.set_colour_rules_state_dir(state_dir)

# immediately before the flight-detected build_canvas() call, ~line 1109:
effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)
canvas = render.build_canvas(
    current_flight, render_state, route=route, ...,
    theme_id=effective_theme_id, ...,
)

# immediately before the held-branch build_canvas() call, ~line 1188,
# inside `if confirmed_state is not None:`:
effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)
held_canvas = render.build_canvas(
    current_flight, render_state, route=current_route, ...,
    theme_id=effective_theme_id, ...,
)
```

## State of the Art

Not applicable in the usual "library X superseded library Y" sense — no library is involved. The one relevant "state of the art" fact is internal to this codebase: `save_device_config()`'s "None means carry forward" contract was deliberately chosen in Phase 11 as *permanent, not provisional* ("there is no way to clear... through this function... not an oversight," per that module's own docstring) — Phase 14 does not reopen or contradict that decision; it adds a second, independently-gated mechanism (the sentinel) that coexists with it for exactly one field.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A module-level sentinel (`CLEAR_THEME_ARRIVING = object()`) is the recommended way to give `save_device_config()` a genuine "clear" path for `theme_arriving`, over a second boolean parameter. | Pattern 2 | Low — both are functionally equivalent and entirely internal to `device_config.py`/`config_page.py`; the planner can pick either without affecting any other module. Flagged because it is a real design choice CONTEXT.md left to discretion, not because either option carries hidden risk. |
| A2 | The new rules module should live at `server/plane/colour_rules.py` (not inside `device_config.py` itself, and not `server/colour_rules.py`). | Pattern 3, Project Structure | Low — D-13 explicitly leaves the resolver's home to discretion ("in `device_config.py` or a sibling leaf module"); `server/plane/` is where `manual_resolutions.py` (its named template) already lives, so this is the more consistent placement, but the alternative is equally valid and low-blast-radius to change during planning. |
| A3 | The ICAO24 hex canonical form should be uppercase 6-char hex (`^[0-9A-F]{6}$`), matching the UI-SPEC's rendered example, even though the live ADS-B `hex` field itself arrives lowercase. | Pattern 4 | Medium if wrong: if the planner instead canonicalises to lowercase, every UI-SPEC copy example (`3944F2`) and the "uppercase as stored" mono-cell convention would need to change too — worth confirming once, early, rather than discovering a mismatch mid-implementation. No prior normaliser exists in this codebase to defer to, so this is a genuinely new convention being set, not a verified fact. |
| A4 | `add_rule()`'s result vocabulary needs a NEW `ADD_OK_NEW`/`ADD_OK_REPLACED` split beyond a literal copy of `manual_resolutions.py`'s `ADD_*` constants. | Pattern 3, Pitfall 4 | Medium if missed: without this, the UI-SPEC's `rule_replaced` flash message (D-09's explicit "make replaced legible" requirement) cannot be implemented without a second, race-prone registry read at the HTTP layer. |
| A5 | The registry JSON should nest by kind (`{"callsign": {...}, "hex": {...}, "prefix": {...}}`) rather than flatten `(kind, value)` into a single composite string key. | Pattern 3 | Low — a flattened-key design (e.g. `"callsign:AFR1234"`) would also work and is a smaller diff from `manual_resolutions.py`'s single-namespace shape; either satisfies D-09's `(kind, value)` keying requirement. Left as discretion, not locked. |

**If this table is empty:** N/A — see above; every item here is Claude's Discretion by CONTEXT.md's own explicit designation, not an unverified factual claim about the external world (no external library, API, or security-standard claim in this research was left unverified).

## Open Questions

1. **Should `colour_rules.py` re-export/duplicate `enrich.normalise_callsign()`'s exact regex, or define an intentionally slightly different one?**
   - What we know: `enrich.normalise_callsign()` itself does no shape validation at all (just strip+upper, returning `None` only for non-string/falsy input) — the shape gate (`_CALLSIGN_SAFE_RE`, `_AIRLINE_PREFIX_SHAPE_RE`) lives in separate, adjacent functions in `enrich.py`, not in `normalise_callsign()` itself.
   - What's unclear: whether a rule's exact-callsign key should be allowed to be shape-invalid (matching `normalise_callsign()`'s own permissiveness exactly, so "the same primitive every cache key... goes through" per D-08 is honoured literally) or should additionally gate on a callsign-shape regex (tighter, safer, but a deliberate divergence from D-08's literal wording).
   - Recommendation: gate on a shape regex (`^[A-Z0-9]{2,8}$`) in addition to strip+upper — D-08 says "the same primitive" for the *normalisation transform*, not necessarily "must accept everything `normalise_callsign()` alone accepts with no further check," and every other rule kind (hex, prefix) already gets its own strict shape gate; leaving callsign as the sole ungated kind would be an inconsistency the plan-checker would likely flag.

2. **Does the resolver need to run for `promoted is not None or refreshed` cycles where `confirmed_state` was just inferred (branch 1109), and separately for `elif current_flight is not None` cycles (branch 1188), even though both use the identically-shaped `current_flight` variable — or should the plan factor the two nearly-identical `resolve_effective_theme_id(...)` calls into one shared local helper inside `run_once()` to avoid a literal two-line duplication?**
   - What we know: the two branches are mutually exclusive per cycle (only one runs), so there's no risk of divergent results within a single cycle — this is purely a code-cleanliness question, not a correctness one.
   - What's unclear: whether the planner should introduce a tiny local closure/helper inside `run_once()` (e.g. `def _effective_theme(): return colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)`) to avoid the two-line duplication, or leave it as two explicit calls (matching this codebase's general preference for explicit, grep-able code over closures inside already-long functions like `run_once()`).
   - Recommendation: leave it as two explicit calls — `run_once()` already has several instances of near-identical code repeated across its branches (e.g. the `_record_history(...)` calls, the `save_poll_state()` calls), and this codebase's own established style favours explicit repetition over closures for readability in this specific function.

## Environment Availability

Skipped — this phase has no external tool, service, runtime, or CLI dependency beyond what is already running in production (the existing Python 3.12 venv, the existing companion/poll-loop systemd units). No new environment probe is needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Stdlib-only hand-rolled harness (`check(name, fn)` + `EXPECTED_CHECK_COUNT` ledger pattern), matching every existing `server/test_*.py`/`companion/test_*.py` file |
| Config file | none — `scripts/run-all-tests.sh`'s `HARNESSES` array is the single source of truth for which files run |
| Quick run command | `server/.venv/bin/python3 server/test_colour_rules.py` (new file) / `server/.venv/bin/python3 server/test_config_history.py` (extended) / `server/.venv/bin/python3 companion/test_config_page.py` (extended) / `server/.venv/bin/python3 server/test_poll_loop.py` (extended) |
| Full suite command | `scripts/run-all-tests.sh` (runs all 17 existing harnesses + the new one under `coverage`, enforces the `pyproject.toml` coverage floor) |

### Phase Requirements → Test Map

(No REQ-IDs exist for this phase; rows below trace to CONTEXT.md decisions instead, per this phase's own precedent.)

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|--------------------|--------------|
| D-04 | `theme_arriving` unset degrades to `None`, never `DEFAULT_THEME_ID`; round-trips through save/load | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ extend existing |
| D-04/Pattern 2 | Checkbox-unchecked save genuinely clears a previously-set `theme_arriving` (the sentinel path) | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ extend existing |
| D-13 | Effective-theme truth table: no rule + no override → base theme; no rule + arriving override set + state=arriving → override; no rule + arriving override set + state=departing → base theme; matching prefix rule + no override → rule wins; matching hex rule beats matching prefix rule; matching callsign rule beats matching hex rule; matching rule + arriving override both present → rule wins | unit | `server/.venv/bin/python3 server/test_colour_rules.py` (new) | ❌ Wave 0 |
| D-13 | Both-render-branches invariant: the identical flight, across two separate `run_once()` calls (one a fresh detection, one a battery-icon-only repaint), produces the identical effective theme id | integration | `server/.venv/bin/python3 server/test_poll_loop.py` (extend with a new check calling `run_once()` twice against the same fixture with only `battery_state.json` changed between calls) | ✅ extend existing |
| D-13 | The four flight-less `build_canvas()` call sites (both empty states, both hold screens) never consult a rule or the arrivals override, even when one is configured that would otherwise match | unit/integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ extend existing |
| D-08/T-13-02 pattern | Registry rejects hostile input for all three kinds: path-separator/parent-directory payloads, oversized strings, wrong-shape hex/callsign/prefix, a `theme_id` not in `THEME_IDS` | unit | `server/.venv/bin/python3 server/test_colour_rules.py` (new) | ❌ Wave 0 |
| D-09 | Adding a key that already exists replaces the entry and reports "replaced" (`ADD_OK_REPLACED`), not "added" | unit | `server/.venv/bin/python3 server/test_colour_rules.py` (new) | ❌ Wave 0 |
| D-10 | The no-JS path: submitting the Settings form / the rules add form / a delete form with no client-side script produces the correct persisted state (native HTML form semantics only) | manual (browser, no-JS) OR integration (raw HTTP POST body, bypassing any script) | `server/.venv/bin/python3 companion/test_config_page.py` for the raw-HTTP-POST equivalent; a `checkpoint:human-verify` step for genuine no-JS browser confirmation, matching this project's `human_verify_mode: end-of-phase` precedent (10-05/11-03/11-04's own deferred real-browser checks) | ✅ extend existing (automated half); Wave 0 gap: none, this always defers to the phase-level UAT pass per project convention |

### Sampling Rate
- **Per task commit:** run the specific new/extended harness (`server/test_colour_rules.py`, or whichever of `server/test_config_history.py`/`companion/test_config_page.py`/`server/test_poll_loop.py` that task touched) — matches this codebase's own per-task TDD RED/GREEN discipline documented throughout STATE.md.
- **Per wave merge:** `scripts/run-all-tests.sh` (full 18-harness suite, coverage floor enforced).
- **Phase gate:** Full suite green before `/gsd-verify-work`, with the one documented exception: the pre-existing macOS-vs-Linux `panel.bin` digest NOTE (Pitfall 5) is an accepted, environment-specific non-regression, not a gate failure, IF it is already present on a clean pre-Phase-14 checkout.

### Wave 0 Gaps
- [ ] `server/test_colour_rules.py` — new file, covers the registry's own contract (load/add/delete/cap/hostile-input rejection/added-vs-replaced) and the resolver's truth table, mirroring `server/test_manual_resolutions.py`'s structure and its `EXPECTED_CHECK_COUNT` ledger-comment discipline.
- [ ] No new shared fixtures needed — `tempfile.TemporaryDirectory()` per test, matching every existing harness in this codebase; no `conftest.py` exists in this project (it does not use pytest) and none should be introduced.
- [ ] Framework install: none — the harness pattern requires zero new packages.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unchanged — the existing companion session-cookie gate covers the two new routes with no new mechanism |
| V3 Session Management | No | Unchanged — `SameSite=Strict` cookie CSRF control already covers new state-changing POSTs, per this codebase's established posture |
| V4 Access Control | No | Single-operator app, no role model exists or is introduced |
| V5 Input Validation | **Yes** | Positive allowlist regex per rule kind (Pattern 4), applied both before persisting and on every read — mirrors `manual_resolutions.py`'s `_SAFE_KEY_RE`/`_PREFIX_RE`/`_HOSTILE_NAME_RE` discipline exactly; theme id values validated by membership against `device_config.THEME_IDS`, never trusted as a bare string |
| V6 Cryptography | No | No secret, token, or cryptographic material is introduced by this phase (the roster half's secret-handling design is explicitly out of scope per D-01/D-02) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Hostile/malformed rule key (callsign/hex/prefix) reaching a live dict-key comparison or a persisted registry | Tampering | Positive allowlist regex per kind, applied at write time AND at every read (T-13-02 pattern, re-applied for a narrower risk surface — see Pattern 4's note that no filesystem path is ever constructed from a rule value in this phase, unlike Phase 13's airline-name-to-filename case) |
| Unbounded registry growth (denial of service via disk/memory) | Denial of Service | Hard entry-count cap, reject-outright-at-cap policy (mirrors `MANUAL_RESOLUTION_MAX_ENTRIES`'s own documented rationale: this registry is authenticated-human-curated, one entry at a time, with no "weakest entry" eviction concept) |
| Concurrent companion requests racing on the same JSON file (lost update) | Tampering / Repudiation (silently-lost writes) | Module-level `threading.Lock()` wrapping the entire load-check-mutate-write sequence, pid/thread-scoped temp filenames (WR-02 fix precedent) |
| A crafted `rule_theme_id` or `rule_kind` not in the closed set reaching `render.build_canvas(theme_id=...)` | Tampering | Membership validation against `device_config.THEME_IDS` (theme id) and an explicit 3-member set (kind) before any write; the read path additionally re-validates on every load (defence in depth, matching `manual_resolutions.load_manual_resolutions()`'s own re-check-on-read precedent) |
| A rule silently applying to a hold/empty screen due to an ordering mistake (Pitfall 1) | Tampering (of displayed information) / a correctness bug with a security-adjacent flavour — could make the operator believe a rule/override is broken when it is actually working correctly, or vice versa | Enforced by construction: the resolver is only ever invoked at the two call sites identified in Pattern 1, never hoisted to a point where `current_flight`/`render_state` could be stale or `None` |

## Sources

### Primary (HIGH confidence — direct code read, this session)
- `server/poll_loop.py` (full `run_once()` body, lines 651-1260) — every `build_canvas()` call site, the hold early-return, the pacing/promotion logic, the enrichment call site, the held/re-render branch
- `server/device_config.py` (full file) — `THEMES`/`THEME_IDS`, every `normalise_*()` function, `load_device_config()`/`save_device_config()`'s exact carry-forward contract, the module's own leaf-import discipline
- `server/plane/manual_resolutions.py` (full file) — the file-safety contract template (D-12), the import-cycle rule, the `_WRITE_LOCK`/cache/result-code patterns
- `server/plane/enrich.py` (lines 95-250ish) — `normalise_callsign()`, `_AIRLINE_PREFIX_SHAPE_RE`, `_CALLSIGN_SAFE_RE`
- `server/plane/detect.py` (`_normalise_selection()`, lines 684-723) — confirms `hex`/`callsign` are the only relevant selection-dict fields, and that `hex` is unvalidated raw aggregator data
- `server/fixtures/*.json` — confirms real `hex` values are lowercase 6-character strings in production data
- `companion/app.py` (page_context(), the manual-resolve POST handler, the manual-delete handler, FLASH_MESSAGES/FLASH_ROLES dicts, the do_POST() dispatch chain)
- `companion/pages/config_page.py` (theme_fieldset(), led_group()/quiet_hours_group()/display_group(), handle_post(), the CHECKBOX_VALUE constants)
- `companion/pages/airlines_page.py` (route/flash-key constants, referenced by name)
- `companion/pages/__init__.py` (the documented `ctx` contract docstring)
- `server/plane/render.py` (`build_canvas()`'s signature, confirming `theme_id` is an ordinary keyword arg needing no signature change)
- `scripts/run-all-tests.sh` (the canonical 17→18-harness list, the venv/coverage invocation)
- `server/test_manual_resolutions.py` (the `check()`/`EXPECTED_CHECK_COUNT` harness pattern)
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (Phase 14 section + pre-discussion framing), `.planning/STATE.md` (Decisions log for Phases 10-13, the Blockers/Concerns section, the digest-mismatch documentation trail)
- `.planning/phases/14-.../14-CONTEXT.md`, `14-UI-SPEC.md` — this phase's own locked decisions and settled UI contract

### Secondary (MEDIUM confidence)
None — no web search or external documentation lookup was needed for this phase; every claim traces to a direct read of this repository's own code or planning documents.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external dependency exists to be uncertain about
- Architecture (resolver placement, both-branches invariant): HIGH — verified by reading every line of `run_once()` and tracing every `build_canvas()` call site by hand
- Rules-registry file contract: HIGH — direct line-by-line read of the named template module (`manual_resolutions.py`)
- Clearable-field sentinel design: MEDIUM — the *problem* is HIGH confidence (verified from source + STATE.md), the *recommended solution* (sentinel vs. extra boolean parameter) is a genuine open design choice correctly flagged as Claude's Discretion, not a verified fact
- ICAO24 hex canonical form: MEDIUM — no prior art exists in this codebase to confirm against; the recommendation is reasoned from the UI-SPEC's own rendered example, not verified against an existing implementation
- Pitfalls: HIGH — Pitfall 1 (ordering trap) and Pitfall 5 (digest note) are both directly evidenced in the code/STATE.md, not speculative

**Research date:** 2026-09-06
**Valid until:** No external time pressure — nothing here depends on a third-party API/library version that could drift. Valid until this codebase's own `device_config.py`/`manual_resolutions.py`/`poll_loop.py` contracts change materially (i.e., effectively indefinite for planning purposes, since this phase is next in the roadmap).
