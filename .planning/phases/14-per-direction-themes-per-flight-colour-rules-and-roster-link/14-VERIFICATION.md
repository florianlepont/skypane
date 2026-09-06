---
phase: 14-per-direction-themes-per-flight-colour-rules-and-roster-link
verified: 2026-09-06T16:29:53Z
status: human_needed
score: 27/27 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "End-of-phase no-JS browser confirmation (14-VALIDATION.md Manual-Only Verifications; human_verify_mode: end-of-phase). Load Settings with JavaScript disabled and confirm: (1) the arrivals grid is reachable/selectable and the checkbox reveals/hides it; (2) saving with the box unchecked clears a previously-set arrivals theme; (3) a rule can be added, and adding the same key again reports it replaced the previous one; (4) a rule can be deleted; (5) the unsaved-changes bar never claims unsaved changes because of a rule add/delete; (6) tabbing through the Theme card reaches the checkbox then, once checked, the revealed grid's radios in document order."
    expected: "All six behaviours hold in a real browser with scripting disabled; the automated HTTP-level tests below already prove the raw POST/markup semantics but cannot see CSS reveal timing, focus order, or screen-reader announcement."
    why_human: "Computed-style/markup assertions cannot observe real browser rendering, keyboard focus order, or a real `:has()` CSS reveal in practice — this project has a standing lesson (feedback_real_device_ui_verification) that computed-style checks alone missed a real mobile nav bug."
  - test: "Run `/gsd-secure-phase 14` over the two new rules routes (`/settings/rules/add`, `/settings/rules/{kind}/{value}/delete`) and the `colour_rules.json` registry, per the roadmap's revised 'Closes with' line for this phase."
    expected: "A retroactive security pass confirms the STRIDE threat registers recorded in each plan (T-14-01, T-14-02, T-14-04, T-14-05, T-14-06 through T-14-14) are honestly mitigated in the shipped code, not just documented in the plan."
    why_human: "This is a standing phase-closing gate this project runs as a separate workflow step, not something this verifier substitutes for."
---

# Phase 14: Per-direction themes, per-flight colour rules and roster-linked highlighting Verification Report

**Phase Goal:** Something more specific than "the one active theme" can decide what the frame looks like for a given render, at three escalating levels of automation. This phase delivers the first two levels plus the shared seam (D-01): (1) a resolution step ahead of the theme lookup in `run_once()`, applied identically to every render of a displayed flight; (2) a theme per direction; (3) per-flight rules keyed on callsign/hex/prefix imposing one of the 18 registered themes, managed from Settings. The roster half is deliberately deferred and its absence is correct, not a gap.

**Verified:** 2026-09-06T16:29:53Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths below are drawn from the five plans' `must_haves.truths` blocks (there is no REQUIREMENTS.md mapping for this unmapped, seed-promoted phase; verification instead traces to `14-CONTEXT.md`'s D-01…D-13). Every row was independently re-derived against the live codebase — running the cited functions/routes directly, not reading the SUMMARY narrative.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A per-flight colour rule survives a process restart (state_dir JSON, D-12) | ✓ VERIFIED | `server/plane/colour_rules.py` writes to `{state_dir}/colour_rules.json` via tmp-write-then-`os.replace()`; `add_rule()`/`load_colour_rules()` round-trip confirmed live (`ok_new`→`ok_replaced`, then `load_colour_rules()` returns the persisted value) |
| 2 | One resolver, fixed order callsign > hex > prefix > arrivals override (arriving only) > base theme (D-09/D-04/D-13) | ✓ VERIFIED | `resolve_effective_theme_id()` (colour_rules.py:466-509); all 7 truth-table rows independently pass (`server/test_colour_rules.py`, 27/27); behavioral, not just presence — each row is a live function call with a real result assertion |
| 3 | Adding an existing `(kind, value)` REPLACES and reports `ADD_OK_REPLACED` (D-09) | ✓ VERIFIED | Live-run: `add_rule(d,'callsign','AFR123','white')`→`ok_new`, then `add_rule(d,'callsign','AFR123','black')`→`ok_replaced`; computed inside `_WRITE_LOCK` before mutation (no TOCTOU) |
| 4 | Malformed/oversized/unreadable rules file degrades to empty registry, never raises | ✓ VERIFIED | `load_colour_rules()` catches `(OSError, ValueError)`, non-dict top level, and caps accumulation at `COLOUR_RULE_MAX_ENTRIES`; test harness covers nonexistent file, invalid JSON, non-dict, non-dict kind value |
| 5 | Hostile rule value rejected at write AND dropped on read, all 3 kinds (T-14-01) | ✓ VERIFIED | Live-run: path-traversal, slash, empty, 400-char strings all return `rejected_*` per kind; `server/test_colour_rules.py`'s hostile-input sweep (check present, passing) covers write- and read-side for all 3 kinds |
| 6 | Resolver never returns a theme id outside `device_config.THEMES` (T-14-05) | ✓ VERIFIED | `resolve_effective_theme_id()` re-checks `rule_theme in device_config.THEMES` before returning; test row 9 injects a tampered cache entry and confirms it is ignored |
| 7 | `theme_arriving` unset is `None` (never `DEFAULT_THEME_ID`), no migration for pre-existing `device_config.json` (D-04) | ✓ VERIFIED | Live-run: a hand-written pre-Phase-14 `device_config.json` (`{"theme":"black"}`) loads with `theme_arriving is None`, file untouched |
| 8 | `save_device_config()` genuinely CLEARS `theme_arriving` via a distinct sentinel (D-04/D-05) | ✓ VERIFIED | `CLEAR_THEME_ARRIVING = object()`, compared by `is`/`is not` in both validation and write branches (`server/device_config.py:663,694`); live-run three-state round trip (set→carry-forward-on-omission→clear) passes |
| 9 | Hostile/stale on-disk `theme_arriving` degrades to `None` on read | ✓ VERIFIED | `normalise_theme_arriving()` returns `None` for non-member/non-string/bool values; live-run confirms `'chartreuse'`, `42`, `True` all → `None` |
| 10 | Invalid `theme_arriving` argument raises `ValueError` before any write (all-or-nothing) | ✓ VERIFIED | `server/device_config.py:663-664`; the pre-existing-file-untouched-after-raise contract is exercised in `server/test_config_history.py` (54/54 pass) |
| 11 | ONE effective-theme computation feeds both flight-displaying `build_canvas()` sites; battery-icon repaint never flips theme (D-13) | ✓ VERIFIED — behavioral | `server/poll_loop.py`: exactly 2 `theme_id=effective_theme_id` sites (lines 1160, 1245), exactly 4 `theme_id=theme_id` sites; `server/test_poll_loop.py`'s both-branches check spies on the real `render.build_canvas()` call (not just the returned dict) across two real `run_once()` calls differing only in battery state — passes; a deliberate-break of one call site was verified (by the executor, recorded in 14-03-SUMMARY.md) to fail exactly this check |
| 12 | The 4 flight-less `build_canvas()` sites never consult a rule/override, even when one would match (D-09) | ✓ VERIFIED | 3 dedicated checks in `server/test_poll_loop.py` (nothing-detected, held-with-no-confirmed-state, hold early-return) all assert `effective_theme == base theme` with a matching rule AND override configured; all pass live |
| 13 | Rules registry loaded exactly once per cycle | ✓ VERIFIED | `colour_rules.set_colour_rules_state_dir(state_dir)` appears exactly once in `poll_loop.py` (line 749), before the resolver calls (line 1152, 1237); per-cycle-priming test confirms a rule added between two `run_once()` calls is picked up by the next cycle only |
| 14 | Resolver never called before `render_state`/`current_flight` are settled | ✓ VERIFIED | `effective_theme_id = theme_id` (line 773) is a documented default, not a resolution; both real resolver calls sit >200 lines later, immediately before their respective `build_canvas()` calls |
| 15 | A checkbox reveals a second identical 18-chip grid; unchecking genuinely clears the override (D-05) | ✓ VERIFIED | `theme_fieldset()` renders both grids via a shared `_theme_chip_grid_html()` helper (byte-identical markup apart from name/class/attr); `handle_post()` branches on `theme_arriving_enabled` alone (never `theme_arriving`'s presence), passing `CLEAR_THEME_ARRIVING` when unchecked — live-run clearable-contract round trip passes |
| 16 | Both grids always present in HTML; reveal is CSS-only, works with JS disabled (D-05) | ✓ VERIFIED | `@supports selector(:has(*))` block in `style.css` (lines 1995-2003, 2127-2130) scoped to `.theme-status:has(#theme-arriving-toggle):not(:has(#theme-arriving-toggle:checked))`; a browser without `:has()` renders both grids unconditionally per the accompanying comment |
| 17 | Both values travel in the one Settings form/save bar; all-or-nothing contract untouched (D-05) | ✓ VERIFIED | `handle_post()`'s single `save_device_config()` call gains one extra kwarg; `grep -c "save_device_config("` in `config_page.py` unchanged at 1 call site |
| 18 | Second grid reuses `/theme-preview/{id}.png` unchanged, no per-direction preview (D-05) | ✓ VERIFIED | Live-run: `theme_fieldset('white', None)` contains `2 * len(THEME_IDS)` `/theme-preview/` occurrences — same route, twice |
| 19 | `handle_post()` branches on the checkbox field, never `theme_arriving`'s presence (Pitfall 3) | ✓ VERIFIED | Source inspection of `config_page.py:1564-1568` confirms the branch keys on `submitted_theme_arriving_enabled` |
| 20 | Settings carries a rules editor: add form (kind/value/theme) + list with per-row delete (D-10) | ✓ VERIFIED | Live-run: rendered Settings page contains "Per-flight colour rules", the add form, `RULES_ADD_ROUTE`, and (empty-state) "No rules yet" |
| 21 | Add/delete are immediate POSTs outside the settings form/dirty bar (D-10) | ✓ VERIFIED | Rules `<section>` renders after `</form>` closes (live-run: `h.index('</form>') < h.index('Per-flight colour rules') < h.index('>Poll<')`); `companion/test_companion_app.py`'s form-isolation check confirms neither the add form nor delete forms reference the settings form |
| 22 | Target theme is a native `<select>` of 18 labels; swatch + label per row; no third chip grid (D-11) | ✓ VERIFIED | `config_page.py`'s rules row renderer uses `_palette_hex()` + `theme_label()`, no chip-grid markup in the rules section |
| 23 | Adding an existing key reports "replaced" not "added" (D-09) | ✓ VERIFIED | `companion/app.py`'s `_handle_rule_add_post()` maps `ADD_OK_REPLACED`→`FLASH_KEY_RULE_REPLACED` distinctly from `ADD_OK_NEW`; live HTTP integration test (`test_companion_app.py`) exercises added-then-replaced |
| 24 | Every rule value validated at write, on read, and before echo into a flash (T-14-01) | ✓ VERIFIED | Delete route re-normalises both path segments (404 on failure, `companion/app.py:1647-1650`); replaced-flash echo re-validated via `normalise_rule_callsign()` before interpolation (`app.py:461`) |
| 25 | Whole editor works with JS disabled (native forms, server-side validation only) | ✓ VERIFIED | No `pattern=` attribute on the value input (server is sole validator); no client script anywhere in the diff; raw-POST no-JS integration tests pass |
| 26 | No roster/iCal/crew code or config key ships in this phase (D-01, prohibition) | ✓ VERIFIED (prohibition, resolved) | `git grep -n "roster\|ical\|\.ics\|crew"` over the phase's diff (`git diff c99fd3a`) returns exactly one hit: the required D-02 documentation sentence in `colour_rules.py`'s module docstring ("a roster link, for instance") — no code, field, or route |
| 27 | Rule record reserves no "origin"/"source" field for the roster half (D-02, prohibition) | ✓ VERIFIED (prohibition, resolved) | `grep -n "\"origin\"\|'origin'\|\"source\"\|'source'"` against `colour_rules.py` returns nothing; the module docstring states extensibility exists but no such field is defined or read |

**Score:** 27/27 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/plane/colour_rules.py` | Registry + D-13 resolver, leaf module | ✓ VERIFIED | 509 lines; imports only stdlib + `server.device_config` (confirmed by grep — 0 forbidden sibling imports) |
| `server/test_colour_rules.py` | Contract harness | ✓ VERIFIED | 27/27 checks pass live |
| `server/device_config.py` | `theme_arriving` + `CLEAR_THEME_ARRIVING` | ✓ VERIFIED | Additive only; `theme`'s own handling untouched |
| `server/test_config_history.py` | Extended harness | ✓ VERIFIED | 54/54 checks pass live |
| `server/poll_loop.py` | Resolver wiring at 2 of 6 `build_canvas()` sites | ✓ VERIFIED | Exact call-site counts confirmed via grep; `render.py` byte-for-byte unchanged |
| `server/test_poll_loop.py` | Both-branches invariant + flight-less-site checks | ✓ VERIFIED | 70/70 checks pass live, including a spy on the real `build_canvas()` call |
| `companion/pages/config_page.py` | Arrivals checkbox/grid + rules editor | ✓ VERIFIED | Rendered live; both grids, checkbox, rules section all present and correctly ordered |
| `companion/static/style.css` | `.theme-direction-label`, `:has()` reveal, `.rule-add-form` | ✓ VERIFIED | All three present; zero new accent-reservation entries (`git diff` shows only a comment, not the list) |
| `companion/app.py` | Two new POST routes, 7 flash keys | ✓ VERIFIED | Both routes gated by `require_session()`; `set_colour_rules_state_dir` never called here (fresh-per-request confirmed) |
| `companion/test_config_page.py` | Extended harness | ✓ VERIFIED | 109/109 checks pass live |
| `companion/test_companion_app.py` | Extended harness | ✓ VERIFIED | 165/165 checks pass live, including a real HTTP-server integration test for the delete route's 404/idempotent-delete contract |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/run-all-tests.sh` | `server/test_colour_rules.py` | `HARNESSES` array | ✓ WIRED | Registered right after `server/test_config_history.py`; header/comment updated 17→18 |
| `colour_rules.py` | `server.device_config` only | leaf-module import discipline | ✓ WIRED | `grep -cE "^(from server\.plane import\|import server\.plane\.)(enrich\|detect\|illustrations\|manual_resolutions\|render)"` returns 0 |
| `run_once()` | `colour_rules.resolve_effective_theme_id()` | 2 call sites, both immediately pre-`build_canvas()` | ✓ WIRED | Confirmed by line-position check: priming (749) < both resolver calls (1152, 1237), each >200 lines after the top-of-cycle default |
| `config_page.handle_post()` | `device_config.CLEAR_THEME_ARRIVING` | checkbox-keyed branch | ✓ WIRED | Live-run round trip confirms the clear path actually reaches disk |
| `companion/app.py` | `colour_rules.load_colour_rules(state_dir)` | `page_context()`, fresh per request | ✓ WIRED | `grep -c "set_colour_rules_state_dir" companion/app.py` = 0 (never uses the poll-cycle cache) |
| rules add/delete routes | `require_session()` | auth gate | ✓ WIRED | Both branches behind the session check in `do_POST()`'s dispatch chain; unauthenticated-POST test asserts no state mutation |
| delete route path segments | `colour_rules.normalise_rule_kind()`/`normalise_rule_value()` | re-normalisation before lookup | ✓ WIRED | Live HTTP integration test confirms a malformed kind and a malformed value each 404 without touching an unrelated existing entry |

### Data-Flow Trace (Level 4)

Not applicable in the traditional dashboard-hollow-prop sense — this phase's "data" is operator-entered config/rules, not an upstream API feed. The relevant flow (Settings form → `save_device_config()`/`add_rule()` → `state_dir` file → `load_device_config()`/`load_colour_rules()` → `resolve_effective_theme_id()` → `render.build_canvas()`) was traced end-to-end above via live function calls at every hop, not just markup presence.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Resolver truth table (all 7 rows) | `server/.venv/bin/python3 server/test_colour_rules.py` | 27/27 pass | ✓ PASS |
| Clearable contract round trip | one-liner from 14-04-PLAN.md's own acceptance criterion, run directly | `CLEARABLE CONTRACT VERIFIED` | ✓ PASS |
| No-migration proof | one-liner, hand-written pre-Phase-14 config file | `no-migration OK` | ✓ PASS |
| Degrade-to-None proof | one-liner | `degrade OK` | ✓ PASS |
| Hostile rule-value rejection, per kind | one-liner (corrected per-kind after an initial test-authoring mistake on my part, noted below) | all rejected as expected | ✓ PASS |
| Both-branches invariant (battery-icon repaint) | `server/.venv/bin/python3 server/test_poll_loop.py` | 70/70 pass, including the spy-based check | ✓ PASS |
| Settings page render (rules section placement, both grids) | one-liner via `config_page.render()` | `ALL SPOT CHECKS PASS` | ✓ PASS |
| Delete route 404/idempotent-delete contract | `server/.venv/bin/python3 companion/test_companion_app.py` | 165/165 pass (real HTTP server integration test) | ✓ PASS |
| Full suite | `scripts/run-all-tests.sh` | 18/18 harnesses, `Result: PASS`, 93% coverage | ✓ PASS |
| D-07 standing gate (`render.py` untouched) | `git diff c99fd3a --stat -- server/plane/render.py` + `server/test_render.py` | empty diff; 134/134 pass, `EXPECTED_CHECK_COUNT` unedited | ✓ PASS |

*Note on my own process:* one of my ad hoc hostile-input spot-checks initially failed because I passed a 4-letter prefix-shaped value (`AFRX`) to `add_rule()` under `kind="callsign"` rather than `kind="prefix"` — `AFRX` is in fact a *valid* callsign shape (2-8 alphanumerics). This was a mistake in my test construction, not a defect in `colour_rules.py`; re-run with the correct per-kind values passed, all rejections behaved exactly as specified.

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` probes; verification runs through the project's standard `check()`/`EXPECTED_CHECK_COUNT` harness discipline instead, which was exercised directly above.

### Requirements Coverage

None — this is an unmapped phase promoted from a seed (SEED-003), matching the Phase 10/11/12/13 precedent explicitly called out in the phase brief. No REQUIREMENTS.md IDs are declared or expected. This is not itself a finding.

### Anti-Patterns Found

None. Swept all ten phase-touched files (`server/plane/colour_rules.py`, `server/device_config.py`, `server/poll_loop.py`, `companion/pages/config_page.py`, `companion/app.py`, and their five test harnesses) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero matches. No stub return patterns, no hardcoded-empty props, no debt markers.

### Human Verification Required

#### 1. End-of-phase no-JS browser confirmation

**Test:** Load Settings with JavaScript disabled. Confirm: (1) the arrivals grid is reachable/selectable and the checkbox reveals/hides it; (2) saving with the box unchecked clears a previously-set arrivals theme; (3) a rule can be added, and adding the same key again reports it replaced the previous one; (4) a rule can be deleted; (5) the unsaved-changes bar never claims unsaved changes because of a rule add/delete; (6) tabbing through the Theme card reaches the checkbox then, once checked, the revealed grid's radios in document order.
**Expected:** All six hold in a real browser with scripting disabled.
**Why human:** This project's `human_verify_mode: end-of-phase` deliberately defers this exact check (recorded verbatim in `14-05-PLAN.md`'s `<human-check>` block and `14-VALIDATION.md`'s Manual-Only Verifications table) rather than running it per-task. Computed-style/markup assertions cannot observe real `:has()` CSS timing, keyboard focus order, or screen-reader announcement — and this project has a standing lesson (`feedback_real_device_ui_verification`) that such checks alone missed a real mobile nav bug.

#### 2. `/gsd-secure-phase 14` pass

**Test:** Run the retroactive security workflow over `/settings/rules/add`, `/settings/rules/{kind}/{value}/delete`, and `colour_rules.json`.
**Expected:** Confirms the STRIDE mitigations recorded in each plan's threat register (T-14-01 through T-14-14) hold in the shipped code.
**Why human/process:** This is the phase's own documented closing gate (ROADMAP's "Closes with (revised)" line and every plan's `<verification>` section), a separate workflow this verifier does not substitute for.

### Gaps Summary

No gaps found. All 27 must-have truths across the five plans were independently re-derived against the live codebase (not read from SUMMARY.md prose) and hold. The D-13 both-branches invariant — this phase's highest-risk correctness property — is proven by a test that spies on the real `render.build_canvas()` call site, not merely on `run_once()`'s returned metadata, closing exactly the failure class (metadata correct, wrong colour painted) a weaker test would miss. The D-04/D-05 clearable-override contract is proven by a real save→load round trip, not a source-code inference. The scope fence (D-01/D-02/D-03) is clean: the phase's diff contains no roster, iCal, or crew code, and the one "roster" string match is the required D-02 documentation sentence stating extensibility exists with no field defined. `server/plane/render.py`, `enrich.py`, and `manual_resolutions.py` are byte-for-byte unchanged, confirming the phase's zero-on-glass-footprint claim by construction. The full 18-harness suite passes at 93% coverage.

The phase is functionally and behaviorally complete. It is marked `human_needed` rather than `passed` solely because two items this project's own workflow deliberately defers to phase close-out — the no-JS real-browser confirmation and the `/gsd-secure-phase 14` pass — have not yet been run (no `14-UAT.md` or `14-SECURE.md`/security-pass artifact exists in the phase directory). These are correctly-scoped remaining obligations, not implementation gaps.

---

*Verified: 2026-09-06T16:29:53Z*
*Verifier: Claude (gsd-verifier)*
