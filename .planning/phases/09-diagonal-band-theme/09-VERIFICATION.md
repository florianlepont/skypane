---
phase: 09-diagonal-band-theme
verified: 2026-09-02T09:23:46Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 9: Diagonal Band Theme Verification Report

**Phase Goal:** Implement spike `.planning/spikes/003-diagonal-band-theme/`'s validated findings — a new dedicated theme (additive to Phase 8's existing 11, which stay untouched) adding a diagonal decorative band behind the aircraft illustration, per the 8 numbered scope clauses (PHASE9-1..8) in ROADMAP.md.
**Verified:** 2026-09-02T09:23:46Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Must-haves derived from ROADMAP.md's Phase 9 Goal (8 numbered clauses, PHASE9-1..8 — no CONTEXT.md/REQUIREMENTS.md mapping exists for this phase, confirmed intentional) merged with each plan's own frontmatter `must_haves`.

| # | Truth (PHASE9 clause) | Status | Evidence |
|---|---|---|---|
| 1 | PHASE9-1: Diagonal TRAPEZOID band primitive, exact measured geometry, drawn behind the illustration | ✓ VERIFIED | `server/plane/render.py:394-398` defines `BAND_TOP_LEFT_FRAC=0.5818`, `BAND_TOP_RIGHT_FRAC=0.8523`, `BAND_BOT_LEFT_FRAC=0.0742`, `BAND_BOT_RIGHT_FRAC=0.4772` matching the Goal's quoted fractions exactly. `draw_diagonal_band()` (line 401) builds the 4-point polygon and is called from `_build_active_canvas()` (line 1876) immediately after the background fill, before `draw_top_labels()`/illustrations/text — confirmed by reading the call order. `server/test_render.py` check "draw_diagonal_band() paints only {IDX_WHITE, band_idx} on a fresh White canvas, flat and dithered" passes (118/118 run). |
| 2 | PHASE9-2: 5 band colour/treatment candidates registered, each passing `_assert_legal_palette()` unmodified | ✓ VERIFIED | `server/device_config.py:206-255` — `band_blue`/`band_blue_light`/`band_green_light`/`band_red`/`band_black`, each with White's own base-canvas fields (departing/arriving=IDX_WHITE, ink=IDX_BLACK, dithered=False, weight="regular") and its own `band_index`/`band_dithered`. `THEMES` now has 16 entries (confirmed live: `python3 -c "from server import device_config as dc; print(len(dc.THEMES))"` → 16). `server/test_render.py`'s full palette-legality sweep check ("every registered band theme's full two-flight composition ... stays `_assert_legal_palette()`-legal across both active states") passes. |
| 3 | PHASE9-3: Top-label split, real `runway_tag_text()` output partitioned on " · ", never hardcoded | ✓ VERIFIED | `server/plane/render.py:813-887` `draw_top_labels(..., band_theme=False)` — `full_tag = runway_tag_text(runway_id)`; `airport_code, _sep, runway_part = full_tag.partition(" · ")` (line 861). `_build_active_canvas()` threads `band_theme=is_band_theme` (line 1890). `test_render.py` confirms both the split (band) and unsplit (default) paths reconstruct the correct text via `_TextSpy` glyph reconstruction. |
| 4 | PHASE9-4: Main-card three-tier hierarchy, centred INSIDE the band, ONE computed centre-x for the whole block | ✓ VERIFIED | `draw_main_text_block(..., band_idx=None)` (line 1385) — band branch (line 1452+) calls `_flight_line1_text()`/`_flight_line2_text()` verbatim (never re-derived), classifies into number/tracked/plain per the spike's 3-way split, computes `center_x = _band_center_x(...)` **once** (line 1515) before any line is drawn/measured, reuses it for all three lines. `test_render.py`'s centring-once check ("all share exactly one x-coordinate ... round-15 fix") passes, and was demonstrated live during 09-03 to catch the round-12 regression (per SUMMARY, spot-checked then reverted). |
| 5 | PHASE9-5: Band-aware ink — white specifically for Black, unchanged elsewhere | ✓ VERIFIED (with a since-widened, developer-confirmed extension, not a regression) | As registered by plan 09-03, `effective_ink = IDX_WHITE if band_idx == IDX_BLACK else ink_idx`. During plan 09-04's real on-glass session, real ink showed black text also illegible on Blue and Green bands (not just Black), so the rule was **widened to unconditional white ink for every band theme** — `server/plane/render.py:1462` `effective_ink = IDX_WHITE` (comment explains the widening and its real-glass justification). This is a real, developer-confirmed, in-scope correction to the original screen-preview-only rule (matches the plan's own "bounded correction" allowance and PHASE9-8's purpose — catching exactly this kind of screen-preview vs. real-ink mismatch). `test_render.py`'s ink-swap check now covers all 5 band ids and passes. |
| 6 | PHASE9-6: Previous-card identical hierarchy, right-aligned, ~57% scale, unchanged position, never colliding, never ink-swapped | ✓ VERIFIED | `draw_previous_text_block(..., band_idx=None)` band branch (line 1666) always draws in `ink_idx`, never overrides to white (confirmed by code inspection — no `effective_ink` variable in this function at all). `BAND_PREV_*_FONT` constants use the ~57%-scaled sizes (32/16/14 vs. main's 56/22/20). `test_render.py`'s clearance check ("previous card's drawn text bboxes never overlap the diagonal band's own rightmost extent, at any of the 5 band themes") passes. `hardware/BRINGUP-LOG.md` Step C records an explicit real-glass clearance verdict across all 5 colours ("no overlap"). |
| 7 | PHASE9-7: PT Serif stays Regular, no italic, for every new text role | ✓ VERIFIED | All `BAND_MAIN_*_FONT`/`BAND_PREV_*_FONT` tuples use `PT_SERIF_REGULAR` (route/airline roles) or resolve weight via `_role_font()` from the theme's own `weight` field, which is `"regular"` for all 5 band THEMES entries (confirmed in device_config.py). No italic font file referenced anywhere in the diff. |
| 8 | PHASE9-8: Required blocking on-glass verification pass, real Spectra 6 glass, all 5 colours/both states, all 4 content tiers, previous-card clearance, content-aware centring | ✓ VERIFIED | `hardware/BRINGUP-LOG.md:479-619` — dated Phase 9 entry under `## Panel Observations`, driven interactively over SSH against the live production VPS with the poll timer stopped/restarted (confirmed: `is-active` → `active`, a real post-restart poll cycle in the journal). Records, in the developer's own words: all 5 colours' true-to-preview/legibility verdicts in both/one state per the developer's own later-session simplification (recorded explicitly, not silently dropped); the split label's legibility; the black-band (and later widened blue/green) ink verdict; all 4 content-ladder tiers "approved" with no raw callsign; explicit previous-card clearance across all 5 colours; the at-distance composition judgment (with an honest note that mounting state was not asked, flagged as an open gap rather than assumed). Two real, in-session-found bugs (illegible ink on non-black bands, band-width text overflow) were fixed and re-confirmed on glass before the session closed. |

**Score:** 8/8 truths verified (0 present-but-behaviour-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `server/device_config.py` | 5 new THEMES entries + 3 accessors | ✓ VERIFIED | 16 total THEMES entries confirmed live; `theme_is_band()`/`theme_band_index()`/`theme_band_dithered()` present (lines 455-476), each matching the documented never-raises/`.get()`-safe contract. |
| `server/plane/render.py` | Band primitive, geometry constants, band-aware labels/text blocks, completed wiring | ✓ VERIFIED | `draw_diagonal_band()`, `_band_edges()`, `_band_center_x()`, `BAND_*_FRAC` constants, band-conditional `draw_top_labels()`/`draw_main_text_block()`/`draw_previous_text_block()`, and `_build_active_canvas()`'s full `band_idx=` threading into both text-block calls — all present and wired (line references above). |
| `server/plane/enrich.py` | Not originally in scope for this phase — added under explicit, recorded developer instruction during plan 09-04's on-glass session | ✓ VERIFIED, deviation documented | `_primary_city_name()` (line 138) present, wired into `_parse_route()` for both `origin_city` and `destination_city` (lines 228/230). The extension beyond plan 09-04's declared `files_modified` is explicitly recorded in `09-04-SUMMARY.md`'s "Deviations from Plan" section (quoting the developer's own instruction, "maintenant et dans le projet") and again in `hardware/BRINGUP-LOG.md`'s correction table — not silently missing from the trail, matching the task's own instruction on how to treat this. |
| `hardware/BRINGUP-LOG.md` | Dated Phase 9 entry under Panel Observations | ✓ VERIFIED | Present at line 479, follows the Phase 7/8 entries' structure and honesty standard (method limits stated, open items carried forward explicitly, `git diff` on this file is insertions-only per plan 09-04's own acceptance criteria). |
| `server/test_config_history.py`, `server/test_render.py`, `server/test_enrich.py` | Coverage for all of the above | ✓ VERIFIED | All three run green: `config-history: 29/29`, `render: 118/118`, `enrich: 52/52` (executed directly during this verification, not taken from SUMMARY claims). |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `device_config.THEMES["band_*"]["band_index"/"band_dithered"]` | `render._build_active_canvas()`'s band dispatch | `theme_is_band()`/`theme_band_index()`/`theme_band_dithered()` accessor calls | ✓ WIRED | `render.py:1854-1856` calls all three accessors immediately after theme resolution, never indexes `THEMES` directly. |
| `render.draw_diagonal_band(canvas, band_idx, dithered=...)` | canvas returned by `pf.new_canvas()`/`dither.dithered_state_background()` | called once, directly after canvas creation, before `draw_top_labels()` | ✓ WIRED | `render.py:1868-1876` — canvas built, then `if is_band_theme: draw_diagonal_band(...)` immediately before the top-labels call at line 1890. |
| `render._flight_line1_text()`/`_flight_line2_text()` | band branches of `draw_main_text_block()`/`draw_previous_text_block()` | called verbatim, same as the non-band path | ✓ WIRED | Confirmed identical call shape in both band branches (lines 1464-1465, 1670-1671). |
| `render._band_center_x(y, WIDTH)` | every line drawn in `draw_main_text_block()`'s band branch | computed once before the first line is measured/drawn, reused for all three | ✓ WIRED | `center_x` computed once at line 1515, reused at lines 1531/1550/1560 — no recomputation. |
| `_build_active_canvas()` | `draw_main_text_block()`/`draw_previous_text_block()` | `band_idx=band_idx` kwarg | ✓ WIRED | `render.py:1912` and `render.py:1945` both pass `band_idx=band_idx`. |

### Data-Flow Trace (Level 4)

Not applicable in the usual web-app sense — this phase is a rendering pipeline (Pillow draw calls onto an in-memory canvas), not a data-fetch/UI-binding path. The equivalent "does the drawn content reflect real data" check is covered by the tier-split content-reuse checks in `test_render.py` (verified above: `route["callsign_iata"]`/`_flight_line1_text()`/`_flight_line2_text()`'s real output, never re-derived or hardcoded) and by the real-glass session rendering actual flight/route fixtures.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `server/device_config.py`'s THEMES/accessor contract | `server/.venv/bin/python3 server/test_config_history.py` | `config-history: 29/29 checks pass` | ✓ PASS |
| `server/plane/render.py`'s band composition (primitive, labels, both text blocks, ink rule, palette legality) | `server/.venv/bin/python3 server/test_render.py` | `render: 118/118 checks pass` | ✓ PASS |
| `server/plane/enrich.py`'s `_primary_city_name()` fix | `server/.venv/bin/python3 server/test_enrich.py` | `enrich: 52/52 checks pass` | ✓ PASS |
| Full aggregate suite (run once) | `scripts/run-all-tests.sh` | 14/15 harnesses pass; `server/test_poll_loop.py` fails on its own pinned CI-Linux digest check | ⚠️ Pre-existing, documented, unrelated to Phase 9 (see below) |
| `companion/pages/config_page.py`'s theme picker | `companion/test_config_page.py` (run as part of the aggregate suite) | Passes, radio count derives from `len(device_config.THEMES)` — 16, automatically | ✓ PASS |

**`server/test_poll_loop.py` digest failure detail:** the file's own header (lines 98-134) states the pinned digest is re-verified from a real Linux CI container run, not a local value, and documents this exact local-macOS-vs-CI-Linux Pillow font-rendering mismatch as a known, standing platform quirk — independently confirmed by both `09-03-SUMMARY.md` and `09-04-SUMMARY.md` ("not re-pinned, per that file's own standing rule"). Re-ran directly during this verification: the single failing check is exactly the pinned-digest comparison (`panel.bin digest ... != pinned ...`), nothing else in that harness fails. This is not a Phase 9 regression.

### Requirements Coverage

Not applicable — ROADMAP.md explicitly states Phase 9 has no REQUIREMENTS.md mapping (`Requirements: TBD`, confirmed unmapped at phase-add time), and no `09-CONTEXT.md` exists (developer skipped `/gsd-discuss-phase`/`/gsd-research-phase` for this phase). Each plan instead cites `PHASE9-1` through `PHASE9-8`, minted from the Goal's own 8 numbered clauses — verified individually in the Observable Truths table above. No orphaned REQUIREMENTS.md entries exist for Phase 9 (`grep -n "Phase 9" .planning/REQUIREMENTS.md` returns nothing).

### Anti-Patterns Found

None. Scanned every file modified across all 4 plans (`server/device_config.py`, `server/plane/render.py`, `server/plane/enrich.py`, `server/test_config_history.py`, `server/test_render.py`, `server/test_enrich.py`, `hardware/BRINGUP-LOG.md`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` (case-insensitive) and empty-implementation patterns. The only matches were benign: SQL "placeholders" (parameterized-query terminology), a fake `"XXX"` IATA test fixture value, and prose referencing "the check that proves the todo's actual goal" — none are debt markers.

### Human Verification Required

None outstanding. The phase's one inherently-human-judgment requirement (PHASE9-8, the on-glass verification pass) was already executed as a live, interactive `checkpoint:human-verify` session during plan 09-04's execution — not deferred to this verification pass. The developer's verbatim findings are recorded in `hardware/BRINGUP-LOG.md`'s Phase 9 entry (read and cross-checked above), including honestly-flagged open items (frame mounting state not asked; band-edge-aware fit spot-checked on one colour/position, not all 5 with long names; `_primary_city_name()` checked against 2 real airports, not exhaustively) that are informational carry-forwards, not gaps in this phase's own goal.

### Gaps Summary

None. All 8 PHASE9-1..8 scope clauses are implemented, wired end-to-end, covered by passing automated tests (118/118 render, 29/29 config-history, 52/52 enrich, executed directly during this verification — not taken on SUMMARY.md's word), and closed by a real, documented on-glass verification session. The one out-of-declared-scope file touch (`server/plane/enrich.py`/`server/test_enrich.py`) was explicit, developer-instructed, and is traceable in both `09-04-SUMMARY.md`'s "Deviations from Plan" section and `hardware/BRINGUP-LOG.md`'s correction table — not a silently-introduced gap. The single full-suite failure (`server/test_poll_loop.py`'s pinned digest) is a pre-existing, independently-documented macOS/CI-Linux Pillow font-rendering platform quirk unrelated to any Phase 9 change, confirmed by inspecting the failing check in isolation.

---

_Verified: 2026-09-02T09:23:46Z_
_Verifier: Claude (gsd-verifier)_
