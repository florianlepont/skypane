# Phase 14: Per-direction themes, per-flight colour rules and roster-linked highlighting - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Something more specific than "the one active theme" decides what the frame looks like for a given render. Phase 14 delivers the first two of SEED-003's three escalating levels, plus the seam they share:

1. **A resolution step ahead of the theme lookup** in `server/poll_loop.py`'s `run_once()` — one function, one documented order, applied identically to every render of a displayed flight.
2. **A theme per direction** — the operator can give arrivals a different theme from the rest of the frame.
3. **Per-flight rules** — a rule keyed on an exact callsign, an ICAO24 hex, or a 3-letter callsign prefix imposes one of the 18 registered themes whenever that flight, airframe, or carrier is the displayed flight; managed from the companion Settings page.

Promoted from `.planning/seeds/SEED-003-theme-direction-scope-color-rules-calendar-highlighting.md` (the roadmap entry records the pre-discussion framing and three corrections to the seed, established by reading the code before promotion).

**What this phase is NOT.** It does not ship the seed's third level — roster-linked highlighting of the flights K Stewart works as crew. That half was **deliberately deferred by the split decision below** (D-01): it stays in SEED-003, and the developer's intent for it is recorded under `<deferred>` for the future phase, not as decisions of this one. This phase also does not introduce any new colour, ink/weight pairing, render state, or on-glass element: every rule and every direction override resolves to a theme id that already exists in `server/device_config.py`'s `THEMES`, so nothing new reaches the glass. It does not add registration (tail-number) matching, does not touch the Airlines or Health pages, and does not change how the panel is composed.

</domain>

<decisions>
## Implementation Decisions

### Split and scope

- **D-01:** **Phase 14 = the resolution seam + per-direction theme + per-flight rules. The roster half is deferred, not dropped.** Chosen over "one phase, all three sub-ideas" (which could not close until two questions only K Stewart can answer — export format and consent — are answered) and over "three phases, one per sub-idea" (sub-ideas 1 and 2 share the seam and the Settings work too closely; separating them would build the seam twice). The roster half stays in SEED-003 as its explicitly deferred third step and is re-promoted as its own phase once the export format and the consent are in hand. A roster match will be *a rule sourced automatically instead of typed*, so the rule store this phase builds is what that future phase writes into.

- **D-02:** **Nothing anticipatory is built for the roster half.** Rules are purely manual; no reserved "origin"/"source" field, no dormant code path. The one constraint this leaves for the planner: the rule record's shape must stay *extensible* (a future entry will carry an origin other than "manual"), which is a documentation obligation on the store's module docstring, not a field.

- **D-03 [informational]:** **The developer's intent for the roster half was captured now, as notes** (see `<deferred>`), so the future phase starts from a design conversation rather than from a cold seed — but none of it binds Phase 14. Tagged `[informational]` on 2026-09-06 at the plan-phase decision-coverage gate: this decision governs what this document records, not what any plan builds, so it is deliberately not trackable to a plan. Its one buildable consequence is D-02, which is covered.

### Per-direction theme

- **D-04:** **One theme plus an optional arrivals override — not two symmetric fields.** The existing `"theme"` key keeps its meaning and stays *the frame's theme*: departures, the empty state, the quiet-hours and display-off hold screens, the Settings previews, and anything else that is not an arrival render. A second, optional key (name is Claude's discretion — e.g. `theme_arriving`) holds the arrivals theme; unset means "same as `theme`". Consequences the planner must honour: an existing `device_config.json` on the deployed host stays valid byte-for-byte with no migration; `load_device_config()` keeps returning every key, and the new key joins `wake_interval_s` as the second key whose valid value set includes `None` (never-explicitly-set); its `normalise_*` helper never raises and degrades an unrecognised id to `None` (= same as `theme`), not to `DEFAULT_THEME_ID`; `save_device_config()` gains the field with the same carry-forward-on-`None` contract, and — unlike `wake_interval_s` — this field **must** be clearable from the form (D-05), so the planner needs an explicit "clear" path rather than only "carry forward".

  Rejected: **two full `theme_departing` / `theme_arriving` fields** — more explicit, but forces a key migration and a decision about which theme dresses the empty state and the Settings previews, for no capability the override does not give.

- **D-05:** **Settings: a checkbox under the Theme group reveals a second, identical chip grid.** Copy is locked-English module constants (Phase 12 D-04 precedent); wording is Claude's discretion, in the spirit of "Use a different theme for arrivals". Checked, the page reveals a second `.theme-chip-grid` of the same 18 chips with the same rendered previews (the existing `/theme-preview/{id}.png` route — previews are per theme id and are **not** re-rendered per direction; a single-colour theme looks the same either way). Unchecked at save time means the override is cleared. The second grid is always present in the HTML and hidden by the checkbox's state, so the page keeps working without JavaScript; the checkbox follows the existing `settings-checkbox` normalisation and the absent-means-off submission semantics `quiet_hours_enabled` already uses. Both values travel in the one existing Settings form and its unified save bar — they are ordinary settings, saved together, taking effect on the frame's next scheduled poll (Phase 06 D-06/D-07's confirmation copy applies unchanged).

  Rejected: **two always-visible grids** (36 preview chips on a page that is already long — a control-density regression `sketch-findings-skypane` would flag) and **a segmented direction switch above one grid** (compact, but hides the other direction's state and still has to carry both values without JS).

- **D-06 (derived, not user-stated):** **The override is the whole theme, for the whole panel, for arrival renders only.** When the displayed state is `"arriving"` the arrivals theme supplies background, ink, weight, dither and band together — never a partial mix of two themes. The panel is one theme: the previous-flight card follows the current state's theme, as it does today. Empty and hold screens always use `theme` (they have no direction).

### Per-flight rules

- **D-07:** **A rule resolves to a registered theme id, never to a raw colour.** The rule's target is one of the 18 `THEMES` entries (band themes included). This reuses every ink/weight/dither/band pairing confirmed on real Spectra 6 glass in Phases 8 and 9 and quick task 260905-e04, needs no new render code (`render.build_canvas()` already takes `theme_id` at every call site), and lets the editor reuse the theme labels and `_palette_hex()` swatches as-is.

  Rejected: **a palette index per rule** — "more direct", but it mints background/ink combinations nobody has seen on glass, pulls an on-glass verification into every rule, and needs new render code.

- **D-08:** **Three key kinds, each normalised the way the codebase already normalises it:** an **exact callsign** (`enrich.normalise_callsign()` output — the same primitive every cache key and request URL goes through), an **ICAO24 hex** (the `hex` the selection dict already carries; case-folded, six hex characters), and a **callsign prefix** (three uppercase letters — the same shape `manual_resolutions.normalise_prefix()` gates). Each kind gets a positive allowlist regex applied both before persisting and on every read (the `T-13-02` pattern). **Registration (F-HBNA) is out**: `detect._normalise_selection()` does not carry the aggregators' `r` field and this phase does not add it.

- **D-09:** **Most specific wins: exact callsign > hex > prefix.** A fixed order by key kind, narrow to broad; a rule on the precise flight beats a rule on the airframe, which beats a rule on the carrier. **One rule per key**: the store is keyed on `(kind, value)` and adding a key that already exists replaces the previous entry — there is never an ordering control in the editor. Derived corollaries: a matching rule beats the per-direction theme (the rule is the operator's explicit instruction about *this* flight); rules are consulted only when a flight is displayed, never for the empty state or a hold screen.

  Rejected: **hex > callsign > prefix** ("the airframe first") and **"first matching rule in the list wins"** (needs a reorder control this codebase has no precedent for).

- **D-10:** **The editor lives on Settings, under the Theme group** — beside the thing rules override. An add form (key kind, value, target theme) and a list with a delete control per row, mirroring Phase 13's manual-resolutions section (D-07 there: list + delete, no in-place editing — correcting a rule means re-adding its key, which D-09's replace-on-add makes a one-step act). **Add and delete are immediate actions on their own POST routes**, outside the main Settings form and its "Unsaved changes" bar — the same shape as Airlines' resolve/delete routes — so a rule never sits half-saved behind the dirty bar, and the Theme/Runway/… form's all-or-nothing `save_device_config()` contract is untouched.

  Rejected: **Airlines beside the manual resolutions** (one page for "lists I created", but far from the theme a rule names) and **a new "Rules" tab** (reopens the four-tab navigation consolidated in 06.6.4.1).

- **D-11:** **The target theme is a native `<select>` of the 18 theme labels**; each row of the rules list shows a colour swatch (`_palette_hex(departing_index)`) plus the label next to the key. No third chip grid.

- **D-12 (derived):** **The rule store is a dedicated JSON file in `state_dir`, following `server/plane/manual_resolutions.py`'s contract exactly** — never-raising load, per-field `normalise_*` gates, validate-before-write, tmp-write then `os.replace()`, stray-`.tmp` cleanup, a bounded entry count, a module-level write lock, companion writes / poll loop reads once per cycle. Not a growing list inside `device_config.json`'s bounded scalars (Phase 13 D-05's reasoning applies verbatim). The cap is Claude's discretion (mirror `MANUAL_RESOLUTION_MAX_ENTRIES`).

- **D-13 (derived):** **One resolution function, in a leaf module, applied to both render branches.** Inputs: the displayed state, the displayed flight (`callsign`, `hex`), the once-per-cycle `device_cfg`, and the once-per-cycle rule registry; output: the effective theme id. Order: matching rule (D-09) → arrivals override when the state is `"arriving"` (D-04) → `theme`. It runs **after** enrichment has settled the displayed flight and **before** `render.build_canvas()`, and the same effective id must be used by the flight-detected branch *and* by the source-fault/battery re-render branch that draws the same flight again from `current_route` — an override applied in one branch and not the other would flip the panel's theme on a battery-icon repaint. The module must stay a leaf (`server/device_config.py` itself, or a sibling that imports only it), so `poll_loop` → resolver → `device_config` never cycles.

### Claude's Discretion

- Field and file names (`theme_arriving`, the rules file name, the rule record's field names), the rules cap, the hex normalisation details, and where exactly the resolver function lives (in `device_config.py` or a sibling leaf module).
- All user-facing copy for the new checkbox, the rules form, the list's empty state and the flash messages — locked-English constants, one caption per section per `sketch-findings-skypane`'s Settings pattern.
- Whether the poll loop's log line and `run_once()`'s result dict report the *effective* theme id (recommended: yes, it is what the panel shows) and whether History/Health surface that a rule fired (no requirement either way — not discussed, do not build a new page section for it).
- Whether the second chip grid's previews reuse the on-disk cache as-is (recommended) — the developer did not ask for direction-specific previews.
- Test strategy, following the codebase's own harnesses (`server/test_config_history.py`-style device-config tests, `companion/test_config_page.py`, `server/test_poll_loop.py`, `server/test_pipeline_e2e.py`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Origin and pre-discussion framing
- `.planning/seeds/SEED-003-theme-direction-scope-color-rules-calendar-highlighting.md` — the seed; sub-ideas 1 and 2 are this phase, sub-idea 3 stays here (D-01) with the intent notes in `<deferred>` below
- `.planning/ROADMAP.md` §"Phase 14" — the promotion entry: the three corrections to the seed (no departing/arriving pair mechanism left to reconcile; rules resolve to theme ids; hex not registration), the security flags for `/gsd-secure-phase 14`, and the expected surface

### Theme model this phase extends
- `.planning/phases/08-panel-theme-rework-white-default-theme-black-yellow-red-blue/08-CONTEXT.md` — D-01/D-02 (every theme is one flat colour), D-04 (theme labels), D-09 (`callsign_iata` as the tier-1 identifier — the future roster phase's match key), D-13 (nothing is trusted until seen on glass — why D-07 matters)
- `.planning/phases/08-panel-theme-rework-white-default-theme-black-yellow-red-blue/08-06-SUMMARY.md` — "Sky" (the only two-tone theme) retired on the developer's explicit instruction
- `.planning/phases/06.6.4.1.1-settings-theme-picker-and-typography-spacing-direction-pass/06.6.4.1.1-CONTEXT.md` — D-01…D-08: the chip grid, hidden-radio selectable-card idiom, real rendered previews cached on disk, the `.theme-status` card wrapper — the second grid (D-05) is a second consumer of exactly this, not a new idiom

### Companion configuration contracts
- `.planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-CONTEXT.md` — D-06/D-07 (a setting takes effect on the frame's next scheduled poll; explicit confirmation copy), D-10 (CFG-01's theme picker is a registry picker, never a free colour picker — D-07 here is the same principle applied to rules)
- `.planning/phases/13-add-an-illustration-for-an-unidentified-flight-from-the-comp/13-CONTEXT.md` — D-05 (the `state_dir` registry file contract the rules store copies), D-07 (list + delete management surface), D-11/D-12 (validate-then-join: nothing displayed or used as a key comes from the request unvalidated), and the `T-13-02` positive-allowlist threat answer
- `.planning/phases/12-remote-display-on-off-toggle/12-CONTEXT.md` — D-04 (locked-English module constants for copy), D-05 (precedence between two mechanisms is one explicit rule, never emergent from call-site order — D-09/D-13 here)
- `.planning/phases/10-scheduled-quiet-hours/10-CONTEXT.md` — the hold-screen model and the early-return gate placement in `run_once()` (why rules and the override never apply to hold screens)

### Design system
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the companion's current design contract; auto-loaded during UI work
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` — one caption per section, the floating save bar's mechanics (D-05 rides in it; D-10's add/delete deliberately do not)
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — the sobriety register D-05 and D-11 were chosen under

### For the deferred roster phase only
- `.planning/seeds/aerodatabox-destination-lookup-rotating-callsigns.md` — why a roster's IATA flight number may not equal the detected ICAO callsign

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/device_config.py` — `THEMES` (18 entries, all with `departing_index == arriving_index`), `THEME_IDS`, `normalise_theme_id()`, `theme_background_index(state, theme_id)`, the `theme_*` accessors, `load_device_config()` / `save_device_config()` with their never-raising, carry-forward-on-`None` contract; `wake_interval_s` is the precedent for a key whose valid values include `None` (D-04)
- `server/plane/manual_resolutions.py` — the runtime-registry file contract to copy for the rules store (D-12): `_SAFE_KEY_RE` / `_PREFIX_RE` allowlists, `load_manual_resolutions()`, `add_entry()` / `delete_entry()` result codes, `entry_rows()`, `set_manual_registry_state_dir()`, `_WRITE_LOCK`, `MANUAL_RESOLUTION_MAX_ENTRIES`
- `companion/pages/config_page.py` — `theme_fieldset()` (the chip grid to instantiate a second time), `_palette_hex()` (rule-row swatches), `quiet_hours_group()` / `display_group()` (the `settings-checkbox` idiom and absent-means-off POST semantics), `handle_post()` (membership validation against `THEME_IDS`), `render()`'s section order (Theme, Runway, Diagnostic LED, Quiet hours, Wake interval, Display, Poll)
- `companion/pages/airlines_page.py` + `companion/app.py` — the manual-resolutions section: add form with native `<datalist>`, management list with per-row delete, `RESOLVE_ROUTE` / `MANUAL_DELETE_ROUTE_PREFIX` as immediate POST routes outside the settings form, and their flash keys — the shape D-10 copies
- `companion/theme_preview.py` — `/theme-preview/{id}.png` per theme id, cached in `state_dir`; reused unchanged by the second grid
- `server/plane/enrich.py` — `normalise_callsign()` (~line 114), `_AIRLINE_PREFIX_SHAPE_RE`; `server/plane/detect.py` — `_normalise_selection()` (the displayed flight carries `hex` and `callsign`, not `r`)

### Established Patterns
- Once-per-cycle config read in `run_once()` (`device_cfg = load_device_config(state_dir)`, then `theme_id = device_cfg["theme"]`) — the rules registry must be loaded in the same place, once, for the same reason (a mid-cycle write must never split one panel across two configurations)
- Never-raising `normalise_*` helpers; explicit membership tests before any value is used as a dict key or path (T-06-01-01)
- Validate-then-join for anything arriving in a request; positive allowlist regexes re-applied on read (T-13-02)
- tmp-write then `os.replace()` for every `state_dir` file; companion writes, server reads
- Locked-English copy as module constants; one caption per Settings section; no `<fieldset>`/`<legend>` on Settings (all groups are `<h2 class="text-heading">` cards)
- Four-tab navigation; nothing in this phase adds a tab

### Integration Points
- `server/poll_loop.py` `run_once()`: the config read (`theme_id = device_cfg["theme"]`, ~line 742), the enrichment settling the displayed flight (`route, route_source = enrich.resolve_route(...)`, ~line 1057), the flight-detected `render.build_canvas(...)` call (~line 1109) and the hold-exit / source-fault / battery re-render `held_canvas = render.build_canvas(...)` (~line 1188) — the resolver (D-13) is inserted after the enrichment and feeds both `build_canvas()` calls with the same effective id; the empty-state and hold-screen calls keep `theme`
- `render.build_canvas(..., theme_id=...)` — unchanged signature; the effective id flows through it
- `companion/app.py` — two new POST routes for rule add/delete (D-10), gated by the existing auth decorator; `page_context()` gains the rules rows for Settings
- `deploy/deploy.sh` rsyncs `server/` with `--delete` excluding `state` — the rules file lives at `{state_dir}/…json` and survives a redeploy like `manual_resolutions.json`
- Tests: `server/test_poll_loop.py` / `server/test_pipeline_e2e.py` (effective theme on both render branches), `companion/test_config_page.py` (second grid, checkbox semantics, rules form/list), a new `server/test_<rules>.py` mirroring `server/test_manual_resolutions.py`

</code_context>

<specifics>
## Specific Ideas

- The developer chose the *sober* option every time a denser one was offered: an optional override rather than two symmetric fields, a checkbox-revealed second grid rather than two grids or a switch, a native `<select>` rather than a third chip grid, and Settings rather than a new tab. Plan and build in that register.
- "One rule per key, adding replaces" is the developer's chosen answer to both precedence-within-a-kind and editing: there is no edit affordance and no ordering affordance by design.
- Every option that would have put something new on the glass was rejected (raw colours, a named marker for the roster phase): the phase's on-glass footprint is zero by construction, and `Closes with` in the roadmap should be updated accordingly at plan time (no on-glass verification; a `/gsd-secure-phase 14` pass over the rules routes and store).

</specifics>

<deferred>
## Deferred Ideas

### The roster half of SEED-003 — deferred by D-01, intent captured 2026-09-06 for its own future phase

Not decisions of Phase 14. Recorded so the future phase starts from what the developer actually wants:

- **Source: an iCal subscription URL to K Stewart's crew roster**, re-read periodically by the server. Chosen over weekly manual entry (a chore, and no longer "automatic") and over uploading an exported `.ics` each roster publication. Conditional on the roster app actually exposing such a URL and on what a duty event carries (plain flight number vs internal duty code) — **the single blocking unknown; ask K Stewart first.**
- **Rendering: a dedicated theme only.** A roster match behaves as an automatic rule imposing one of the 18 registered themes the developer will choose — nothing new on the glass. A named marker on the panel (initial, first name, pictogram) was considered and rejected for now: a new render element to verify on glass, and a first name displayed on a wall.
- **Match: flight number + day.** The displayed flight's `route["callsign_iata"]` (adsbdb, Phase 8 D-09 — so matching runs *after* enrichment, never on the raw callsign) equals the number of a roster duty dated the same day. Chosen over "flight number alone" (would highlight the days K Stewart does not fly that service). The rotating-callsign carriers in `aerodatabox-destination-lookup-rotating-callsigns.md` remain a known gap.
- **Secret: an environment variable in `skypane.env`, the same class as `SKYPANE_COMPANION_PASSWORD`** — entered once over SSH, never written to `state_dir`, never shown by a page; Settings would only show "roster configured / not configured". Chosen over a Settings field stored in a dedicated file (which would have been the project's first runtime-written secret).
- **Prerequisites before that phase can be discussed for real:** (1) the export format, from K Stewart; (2) their explicit agreement to their work schedule being stored and polled on the VPS — a prerequisite, not a courtesy; (3) the fetch cadence and failure behaviour (the server has no long-running process — `deploy/skypane-poll.timer` fires a 30 s oneshot — so a throttled fetch inside the oneshot, persisted to `state_dir`, never delaying the render on a slow upstream, is the expected shape); (4) the outbound-egress gate for an operator-controlled URL (HTTPS only, no private ranges, bounded size and timeout).
- **Registration (tail number) as a rule key** — out of Phase 14 (D-08); would need `detect._normalise_selection()` to carry the aggregators' `r` field. Revisit only if hex proves too opaque in daily use.
- **A visible trace on History/Health that a rule or the arrivals override fired** — offered as a possible extra area, not selected; not in scope.

### Reviewed Todos (not folded)
None — `todo.match-phase 14` returned zero matches.

</deferred>

---

*Phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link*
*Context gathered: 2026-09-06*
