---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
verified: 2026-08-31T14:12:24Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 8: Panel theme rework Verification Report

**Phase Goal:** Glancing at the frame shows a clean white panel whose flight text is legible on real Spectra 6 ink with no box behind it, naming a real IATA flight number rather than a raw ADS-B callsign — with Black, Yellow, Red and the existing Sky theme selectable from the CFG-01 picker. Full scope, rationale, and the complete rendered decision trail are recorded in the spike this phase implements. A required, blocking on-glass verification pass closes the phase.

**Verified:** 2026-08-31T14:12:24Z
**Status:** passed
**Re-verification:** No — initial verification

## Note on the ROADMAP goal text vs. the actual shipped outcome

The ROADMAP goal text ("...with Black, Yellow, Red and the existing Sky theme selectable...") is **stale relative to the phase's own legitimate, developer-directed final state**, not a sign of drift or an unmet must-have. Plan 08-06's blocking on-glass session (D-13, the phase's own required closing gate) found on real Spectra 6 ink that:

1. Uniform PT Serif Bold read "très agressif," reopening D-06 with an explicit developer instruction — resolved with a per-theme `weight` registry field (Regular on flat themes, Bold on dithered themes, Yellow Light the sole exception).
2. Sky (Blue departing / Green arriving, two-tone) was retired outright on explicit developer instruction ("Pas de sky, parles de bleu clair, vert clair" / "thèmes séparés") once Blue and Green were independently validated as standalone single-colour themes.
3. The registry was widened from 5 to 11 entries (white, black, grey, yellow, yellow_light, red, red_light, green, green_light, blue, blue_light) — every Spectra 6 ink as both a pure and a dithered-light variant, individually confirmed on real glass — well past D-13's stated minimum of "at least one of Black/Yellow/Red."

`08-CONTEXT.md`'s own Claude's-Discretion clause explicitly permits widening the coloured-theme on-glass check at the developer's call, and `08-06-PLAN.md`/`08-06-SUMMARY.md` both document this as a developer-directed, developer-confirmed in-session reopening — not an executor's unilateral scope decision. The verified codebase truth is: CFG-01 offers 11 selectable, single-colour, individually on-glass-validated themes; no id named `"sky"` remains (a stale on-disk `"theme": "sky"` value degrades safely to the White default via `normalise_theme_id()`, confirmed live). This exceeds, not fails, the roadmap's literal goal text. **Recommend the orchestrator update ROADMAP.md's Phase 8 goal text and Phase 7 success-criterion-7 status to reflect this outcome** (08-06-SUMMARY.md's own "Next Phase Readiness" section already flags this).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | White is the new default theme; departing/arriving remain distinguishable by label alone | ✓ VERIFIED | `server/device_config.py`: `DEFAULT_THEME_ID = "white"`, `THEMES["white"]` both indices `IDX_WHITE`/ink `IDX_BLACK`. On-glass Step A: "confirmed clean white with no visible cast... distinguishable at a glance by the DEPARTING/ARRIVING label... the developer confirmed this explicitly" (`hardware/BRINGUP-LOG.md` line 333-338). `server/test_config_history.py` (26/26), `server/test_render.py` (99/99) pass live. |
| 2 | Flight text is legible on real Spectra 6 ink with no box behind it | ✓ VERIFIED | `_paint_text_backing()` and all 6 call sites deleted (`server/plane/render.py` line 131 comment confirms removal; `grep` finds zero live references). On-glass Step B: initial uniform Bold read "très agressif," reopened and resolved via per-theme `weight` field (code: `_role_weight_path()`/`_role_font()`/`_role_fit_text_size()` at `server/plane/render.py:408-440`, verified wired into `draw_top_labels()`/`draw_main_text_block()`/`draw_previous_text_block()`). Direct developer confirmation the plate is not missed: "ah non pas du tout" (`hardware/BRINGUP-LOG.md` line 358-359). |
| 3 | Panel names a real IATA flight number rather than a raw ADS-B callsign, never displaying the raw callsign at any tier | ✓ VERIFIED | `server/plane/enrich.py`: `callsign_iata` threaded through `_parse_route()`/`_route_from_entry()`/`airline_only_route()` (all confirmed via code read, lines 205-235, 613-633). `server/plane/render.py:_flight_line1_text()` (4-tier ladder) never reads `flight.get("callsign")`; only CLI arg metadata uses it, never a draw path (grep confirmed). `server/test_enrich.py` (50/50) and `server/test_render.py` (99/99) both pass, including explicit D-08 structural-absence and CLI-level guard checks. On-glass Step F: "No raw ADS-B callsign appeared on any of the four tiers" (`hardware/BRINGUP-LOG.md` line 417-418). |
| 4 | CFG-01 picker offers a genuine set of coloured themes beyond the prior single default, each real-glass validated | ✓ VERIFIED (exceeds literal roadmap wording — see note above) | `companion/pages/config_page.theme_fieldset()` executed live: returns exactly 11 theme ids matching `device_config.THEME_IDS`, zero code change to `config_page.py`/`app.py` (confirmed by `git diff --stat` claims in 08-01-SUMMARY.md and independently re-derived by running the function). All 11 individually judged on real glass in `hardware/BRINGUP-LOG.md`'s Step E (9 direct comparison renders + 2 re-confirmed against the final committed registry; the remaining themes covered by the standing `test_render.py` palette-legality regression suite). A real dithering bug (flat Black rendering grey) was caught and fixed live via a per-theme `dithered` registry bool. |
| 5 | Previous-flight-card text sizing/alignment fix applied and holds across diverse illustrations | ✓ VERIFIED | `PREVIOUS_LINE2_FONT` = `(PT_SERIF_BOLD, 20, 700)` role tuple confirmed at `server/plane/render.py:159` (size resolved to the theme's actual weight at draw time). `PREVIOUS_TEXT_LEFT_OFFSET_PX = 20` confirmed at line 328, applied in `draw_previous_text_block()` at line 1231. Six-airframe spot-check (`server/test_render.py`, narrowbody x2/turboprop/small twin/regional jet/widebody) passes live with a 5-12px padding spread, no outlier. On-glass Step D: "Tout est bon." |
| 6 | A blocking on-glass verification pass was actually conducted (not merely claimed) before the phase closed | ✓ VERIFIED | `hardware/BRINGUP-LOG.md` carries a genuinely detailed, dated `### Phase 8 On-Glass Verification (2026-08-31, plan 08-06)` section (lines 318-477) with verbatim developer quotes in French, a before/after/reason corrections table, specific real bugs found and fixed live (dithering bug, font-weight reopening), and a teardown confirmation (poll timer restarted, live poll cycle observed in the journal with real detected data: `hex=39de41, callsign=TVF36VX, theme=white`). This is qualitatively consistent with Phase 7's own precedent on-glass entry, not a rubber-stamped placeholder. |

**Score:** 6/6 truths verified (0 present-but-behaviour-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/device_config.py` | 11-entry `THEMES` registry, White default, `dithered`/`weight` fields, no `"sky"` id | ✓ VERIFIED | Read in full; confirmed live via `normalise_theme_id('sky') == 'white'` |
| `server/plane/render.py` | Backing plate removed; `_role_weight_path`/`_role_font`/`_role_fit_text_size` per-theme weight resolution; 4-tier `_flight_line1_text()`; `PREVIOUS_TEXT_LEFT_OFFSET_PX`; tier-4 `"Unknown flight"` | ✓ VERIFIED | Read in full; all call sites confirmed wired |
| `server/plane/enrich.py` | `callsign_iata` threaded through 3-point chain, optional, never route-fatal | ✓ VERIFIED | Read in full; `server/test_enrich.py` 50/50 live |
| `companion/pages/config_page.py` | CFG-01 picker renders all registered themes with zero call-site change | ✓ VERIFIED | Executed live; 11 ids returned; file untouched per SUMMARYs |
| `server/assets/fonts/VENDOR.md` | Supersession note documenting the Bold switch | ⚠️ STALE (non-blocking) | Present and accurate as of 08-03, but not updated after 08-06 reopened D-06 to a per-theme weight — the note still states "PTSerif-Regular.ttf is no longer referenced by any active-state font-role constant," which is no longer true (Regular is now the active weight for White/Black/Yellow/Red/Green/Blue/Yellow-Light). See Gaps/Notes below. |
| `hardware/BRINGUP-LOG.md` | Dated Phase 8 on-glass entry, D-13 | ✓ VERIFIED | Read in full; substantive, detailed, consistent with SUMMARY claims |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `device_config.THEMES` | `render.py` `STATE_BACKGROUND`/`STATE_INK` | module-level derivation at import time | WIRED | Confirmed via code read (`theme_background_index`/`theme_ink_index` calls at render.py:196-237) |
| `device_config.theme_weight()`/`theme_dithered()` | `render.py` `_build_active_canvas()` | explicit per-theme lookup, threaded into draw calls | WIRED | Confirmed at render.py:1379-1392 and threaded into `draw_top_labels`/`draw_main_text_block`/`draw_previous_text_block` signatures |
| `enrich.py callsign_iata` | `render.py _flight_line1_text()` tier 1 | `route["callsign_iata"]` read | WIRED | Confirmed via code read at render.py `_flight_line1_text()` |
| `device_config.THEME_IDS` | `companion/pages/config_page.theme_fieldset()` | generic iteration, no companion code change | WIRED | Confirmed live — 11 ids returned, config_page.py unmodified per SUMMARYs and untouched in this phase's git history |

### Requirements Coverage (D-01 through D-13, via 08-CONTEXT.md)

| Decision | Plan | Status | Evidence |
|----------|------|--------|----------|
| D-01 (White default) | 08-01 | ✓ SATISFIED | Code + tests confirmed live |
| D-02 (Black/Yellow/Red single-colour) | 08-01 | ✓ SATISFIED | Code + tests confirmed live |
| D-03 (Sky retained, unchanged) | 08-01 | SUPERSEDED (08-06) | Sky retired on-glass, developer-directed; see note above |
| D-04 (theme labels) | 08-01 | ✓ SATISFIED | Plain labels confirmed in registry |
| D-05 (backing plate removed) | 08-03 | ✓ SATISFIED | Confirmed removed, no replacement, on-glass confirmed not missed |
| D-06 (Bold everywhere) | 08-03 | SUPERSEDED (08-06) | Reopened on-glass to per-theme weight; functional intent (legibility without a box) fully preserved and re-confirmed on real ink |
| D-07 (font provenance) | 08-03 | ⚠️ PARTIALLY STALE | Supersession note in VENDOR.md not updated after D-06's 08-06 reopening (see Gaps/Notes) |
| D-08 (raw callsign never shown) | 08-04 | ✓ SATISFIED | Code + tests + on-glass all confirm |
| D-09 (callsign_iata threaded) | 08-02 | ✓ SATISFIED | Code + tests confirmed live |
| D-10 (4-tier ladder) | 08-04 | ✓ SATISFIED, tier 4 text later revised on-glass (08-06) to "Unknown flight" | Code + tests + on-glass confirm |
| D-11 (PREVIOUS_LINE2_FONT 20px) | 08-03 | ✓ SATISFIED | Confirmed in registry constant |
| D-12 (previous-card 20px offset) | 08-04/08-05 | ✓ SATISFIED | Confirmed wired, 6-airframe spot-check passes |
| D-13 (blocking on-glass gate) | 08-06 | ✓ SATISFIED | `hardware/BRINGUP-LOG.md` entry substantive and dated |

No orphaned requirements — REQUIREMENTS.md confirmed to carry no REQ-ID mapped to Phase 8 (grep found no "Phase 8" row in the requirements table); the phase is correctly traced against 08-CONTEXT.md's D-IDs instead, matching the Phase 06.4 precedent cited in ROADMAP.md.

### Anti-Patterns Found

Scanned `server/device_config.py`, `server/plane/render.py`, `server/plane/enrich.py`, `server/test_render.py`, `server/test_config_history.py`, `server/test_enrich.py`, `server/test_poll_loop.py`, `server/assets/fonts/VENDOR.md`, `hardware/BRINGUP-LOG.md` for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER. No debt markers found (one incidental `"XXX"` match is a test fixture's placeholder IATA airport code, not a marker).

**ℹ️ Info — two stale-but-non-blocking documentation items, both pre-existing "deferred" notes never closed across the phase's 6 plans:**
1. `server/assets/fonts/VENDOR.md`'s Phase 8 Supersession note (D-07) states Regular is "no longer referenced by any active-state font-role constant" — no longer accurate after 08-06's on-glass reopening made weight per-theme (Regular is now actively used by 7 of 11 themes). Functionally harmless (the code itself is correct and tested); the prose documentation just wasn't reconciled back after the on-glass session's scope reopening.
2. `companion/pages/config_page.py`'s `THEME_HELPER_TEXT` still reads "More themes will be added once Phase 7 validates additional color options on real hardware." — stale since Phase 7 completed and Phase 8 added 10 more themes. Flagged as a deferred item in 08-01-SUMMARY.md and never revisited in any later plan (08-02 through 08-06 all explicitly kept `config_page.py`/`app.py` untouched).

Neither item blocks the phase goal (both are prose/copy accuracy, not functional behavior), but both are worth a follow-up one-line fix.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Stale `"sky"` on-disk value degrades safely to White | `device_config.normalise_theme_id('sky')` | `'white'` | ✓ PASS |
| CFG-01 picker renders 11 themes with zero companion code change | `theme_fieldset('white')` executed live | 11 ids, matches `THEME_IDS` exactly | ✓ PASS |
| No draw path reads raw `flight["callsign"]` | `grep -n "callsign\b" server/plane/render.py` (excluding CLI/docstrings) | Only CLI arg passthrough (`flight = {"hex":..., "callsign": args.callsign}`), never read by `_flight_line1_text()` | ✓ PASS |
| Per-theme weight correctly resolved at draw time (not the bare always-Bold tuple path) | Read `_role_font()`/`_role_weight_path()` and both call sites in `draw_top_labels()` | Confirmed: `_role_font(STATE_LABEL_FONT, weight)` resolves via `weight`, ignoring the tuple's bare path | ✓ PASS |
| `server/test_render.py` full suite | `server/.venv/bin/python3 server/test_render.py` | `render: 99/99 checks pass` | ✓ PASS |
| `server/test_config_history.py` full suite | `server/.venv/bin/python3 server/test_config_history.py` | `config-history: 26/26 checks pass` | ✓ PASS |
| `server/plane/enrich.py` test suite | `server/.venv/bin/python3 server/test_enrich.py` | `enrich: 50/50 checks pass` | ✓ PASS |
| `companion/test_config_page.py` | `server/.venv/bin/python3 companion/test_config_page.py` | `config-page: 39/39 checks pass` | ✓ PASS |
| `server/test_poll_loop.py` (known cross-platform digest exception) | `server/.venv/bin/python3 server/test_poll_loop.py` | `poll-loop: 42/43 checks pass` — sole failure is the documented macOS-local-vs-Linux-CI font-digest mismatch, matches SUMMARY claims exactly | ✓ PASS (expected exception) |
| All 20 commits referenced across the 6 SUMMARYs exist in git history | `git cat-file -e <hash>` for each | All 20 present | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention found in this repo, and no PLAN/SUMMARY declares a probe-based verification mechanism for this phase. Step 7c: SKIPPED (no declared or conventional probes; this phase's runnable verification is its pytest-style harnesses, exercised above).

### Human Verification Required

None. D-13's real-glass judgment was already discharged within the phase itself (plan 08-06's blocking on-glass session, documented in `hardware/BRINGUP-LOG.md` with specific developer quotes, corrections, and re-confirmations) — this is not a deferred human-verification item but a completed one, verified above by reading the actual BRINGUP-LOG.md entry rather than trusting the SUMMARY's characterization of it.

### Gaps Summary

No blocking gaps. All 6 derived observable truths for the phase goal are verified against the real codebase (not just SUMMARY claims): the registry, rendering pipeline, enrichment threading, companion picker, and on-glass verification record were all independently read and, where testable, executed live with passing results (99/99, 26/26, 50/50, 39/39, 42/43-with-documented-exception).

Two non-blocking documentation-accuracy items are noted for a future cleanup pass (not filed as gaps since they don't affect the phase goal's functional truths):
- `server/assets/fonts/VENDOR.md`'s D-07 Supersession note is stale after 08-06's on-glass weight reopening.
- `companion/pages/config_page.py`'s `THEME_HELPER_TEXT` copy is stale (references "Phase 7 validates additional color options," written before either Phase 7 or Phase 8's on-glass sessions existed).

The ROADMAP.md goal text itself is stale relative to the phase's own legitimate on-glass outcome (Sky retired, 11 themes shipped instead of Black/Yellow/Red/Sky) — recommend the orchestrator update ROADMAP.md's Phase 8 goal wording and Phase 7's success-criterion-7 status per 08-06-SUMMARY.md's own "Next Phase Readiness" note, as part of this phase's closure.

---

_Verified: 2026-08-31T14:12:24Z_
_Verifier: Claude (gsd-verifier)_
