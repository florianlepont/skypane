---
phase: 03-visual-polish-on-real-glass
verified: 2026-08-27T08:10:15Z
status: gaps_found
score: 7/8 must-haves verified (1 roadmap success criterion + 7 plan-level truths that survived documented supersession)
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A missing, corrupt or oversized illustration file degrades to the fallback (and does not crash the render pipeline) — an explicit must-have of 03-03-PLAN.md, and the claimed mitigation for STRIDE threat T-03-03-02 in the same plan."
    status: failed
    reason: "The 'missing file' case is genuinely handled (select_illustration() checks os.path.isfile() at every fallback tier and returns None if even the universal fallback is absent, in which case _build_active_canvas() simply skips drawing an illustration). But the 'corrupt file' case is not handled at all: _resize_illustration() calls Image.open(path).convert('RGBA') with no try/except anywhere in the call chain (_build_active_canvas -> _resize_illustration -> draw_illustration). Reproduced live in this verification: pointing select_illustration() at a byte-garbage file with a .png extension raises an uncaught PIL.UnidentifiedImageError out of render_panel(). The architecture that would have caught this (03-03's 'fall back to generic, then to the retired flat silhouette, inside a broad try/except') was superseded by the D-25/D-26 two-flight redesign and the retired-silhouette fallback function (draw_silhouette()) no longer exists anywhere in server/plane/render.py — nothing replaced the try/except it used to provide. validate_illustration_file() (which does check format/decodability) exists but is only invoked by illustrations.py's own `--validate` CLI at hand-off time, never inside the render path."
      artifacts:
        - path: "server/plane/render.py"
          issue: "_build_active_canvas() (around line 560-585) and draw_illustration()/_resize_illustration() have no exception handling around Image.open()/convert()/resize() for the per-airline or previous-flight illustration path. A corrupt or truncated PNG that passes os.path.isfile() propagates PIL.UnidentifiedImageError (or a similar decode error) straight out of render_panel()."
      missing:
        - "Wrap the Image.open()/.convert('RGBA') calls in _resize_illustration() (or the call site in _build_active_canvas()) in a try/except that falls back to illustrations.generic_fallback_path() on any decode failure, and skips drawing the illustration entirely (matching the already-working 'directory missing' degradation path) if even the fallback fails to decode."
        - "A regression test exercising a corrupt-but-present illustration file (analogous to the existing 'illustration directory renamed aside' style of test) so this degradation path cannot silently regress again."
  - truth: "Missing/corrupt/oversized illustration guard: validate_illustration_file()'s decompression-bomb cap (ILLUSTRATION_MAX_PIXELS) actually protects the render path, not only the offline --validate CLI."
    status: failed
    reason: "Same root cause as the corrupt-file gap above: validate_illustration_file() is never called from server/plane/render.py or server/poll_loop.py's render call chain. An oversized/decompression-bomb PNG already vendored on disk (e.g. via disk corruption, a bad file swap, or a future hand-off mistake that slips past a one-time --validate run) would be decoded unguarded by draw_illustration()'s Image.open()/.convert()/.resize() chain at render time, with no header-only size pre-check in that path. This is the same threat T-03-03-01 claims is mitigated 'again at render time inside draw_dithered_illustration()'s try/except' - that function and its try/except no longer exist under this name in the shipped code."
      artifacts:
        - path: "server/plane/render.py"
          issue: "No pre-decode size check (header-only pixel-count guard) exists in the render-time illustration path, unlike the vendor-time validate_illustration_file() path."
      missing:
        - "Either call validate_illustration_file() (or at least its pixel-count/format checks) before Image.open().convert() in the render path, or fold the same try/except recommended for the corrupt-file gap around the whole illustration-loading sequence so an oversized file also degrades instead of raising/hanging."
deferred:
  - truth: "Hardware-verified legibility of the shipped typography, background, composition, and illustration on real Spectra 6 glass (the original phase goal's 'not a rendered-PNG preview' clause, and the original 03-04 on-glass plan)."
    addressed_in: "Phase 6: Final On-Glass Verification"
    evidence: "ROADMAP.md Phase 3 section, 'Note on the on-glass verification plan (2026-08-26)': 'This phase's original fourth plan (03-04, the on-glass verification battery) was moved to Phase 6 ... at the user's explicit request ... The four on-glass success criteria that used to live here ... moved with it — they are not duplicated below.' Phase 6's ROADMAP entry explicitly restates 'Requirements: PLANE-01, PLANE-02 (the hardware-verified-legibility half of both — closing what Phase 3 could not close without the physical device).'"
human_verification: []
---

# Phase 3: Visual Polish on Real Glass Verification Report

**Phase Goal (as scoped by the current ROADMAP.md, which explicitly narrowed the original phase goal — see Deferred section):** Each detected flight renders a dithered, per-airline-generated aircraft illustration for airlines covered by the generated set, with a single dithered generic illustration as the fallback for uncovered airlines and the "Route unavailable" state, never mirrored by state (D-24) — verified by the automated suite, not by eye. Hardware-verified legibility of the resulting typography/background/composition was explicitly moved to Phase 6 and is not this phase's criterion (see Deferred section).

**Verified:** 2026-08-27T08:10:15Z
**Status:** gaps_found
**Re-verification:** No — initial verification (retroactive; this is the first time this phase has been run through goal-backward verification, per the orchestrator's framing)

## Important context: this phase's design changed materially, live, mid-execution

Before Wave 3 (03-03) finished, the user reviewed real rendered mockups and made a sequence of locked decisions recorded in `03-CONTEXT.md` as **D-20 through D-27**, which supersede large parts of what `03-01-PLAN.md`, `03-02-PLAN.md`, and `03-03-PLAN.md` originally specified:

- **D-21** reverted 03-02's dithered mood-gradient background back to a **flat single-color field** (lighter Blue/Green than D-13's interim values) — the dithered-background work in `server/plane/dither.py`'s `build_mood_background()` was later fully retired (confirmed: `server.plane.dither.build_mood_background` no longer exists, per `server/test_dither.py`'s own regression check).
- **D-24** dropped state-based mirroring of the aircraft illustration entirely (every illustration renders nose-left in both states).
- **D-25/D-26** replaced the whole single-flight zone layout with a two-flight "poster" composition (current + previous flight, each with its own real illustration and text block), a thin frame, and top-corner labels — none of which existed in the original `02-UI-SPEC.md`/`03-UI-SPEC.md` zone layout.
- **D-27** replaced the Zilla Slab typography vendored in 03-01 with **PT Serif Regular** for every text role.
- The spatially-scoped `_assert_palette_contract()` guard rail (03-02's contribution) was replaced by a simpler `_assert_legal_palette()` (legal-index-set + background-dominance only, no spatial scoping), because a full-color illustration can no longer be confined to "only inside its own bbox" under the new layout.

**This verification checks the actual, currently-shipped codebase against these superseding decisions, not against the original plan text.** Where a plan-level must-have was superseded by a later, explicitly-recorded decision in the same phase's own `03-CONTEXT.md`, it is treated as resolved-by-supersession, not as a gap — this mirrors `03-03-PLAN.md`'s own "Reconciliation Note," which the executing agent wrote for exactly this reason. Where a plan-level must-have was **not** superseded by any recorded decision and simply doesn't hold in the current code, it is reported as a real gap below.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (ROADMAP SC) | Each detected flight renders a dithered per-airline illustration for covered airlines; uncovered airlines and Route-unavailable both render a single dithered generic illustration; never mirrored by state (D-24) | ✓ VERIFIED | `server/plane/illustrations.py::select_illustration()` implements the (now four-tier, extended by Phase 3.1) selection with `os.path.isfile()` guards at every tier, ending in `generic_fallback_path()`. `server/plane/render.py::draw_illustration()` composites via `dither.dither_to_full_panel_palette()` (Floyd-Steinberg, full 6-color palette, no remap) — confirmed still dithered, not flat, in the current code (`grep` + read). No `Image.FLIP_LEFT_RIGHT`/mirror call exists anywhere in `render.py` (`grep -n "FLIP_LEFT_RIGHT\|mirror"` finds only comments/docstrings referencing the *removal* of mirroring). Live-run `server/test_render.py` (35/35 pass) includes "the main illustration's opaque pixels are byte-identical between departing and arriving renders (D-24: never mirrored by state)" and "a route whose airline_name has no vendored file falls back to generic-fallback.png and renders different bytes than a route with real art." Live-run `server/test_illustrations.py` (42/42 pass) directly exercises all four selection tiers. |
| 2 (03-01) | A genuinely long destination/origin city name and long airline name shrink to fit rather than clipping or crossing the safe margin | ✓ VERIFIED | `server/test_render.py`: "a genuinely long destination/origin city name (Santiago de Compostela) shrinks via fit_text_size() without crashing, drawn in full" — re-run, pass. `_flight_line2_text()`'s battery of hostile-route/type combinations plus the "longest real airline name combined with the longest type label still renders without tripping `_assert_within_canvas`" check both re-run and pass. |
| 3 (03-01/03-02) | Rendering the same flight (and route) twice is byte-identical, so the device is never woken for a redundant refresh | ✓ VERIFIED | `server/test_render.py`: "rendering the same flight+route twice produces byte-identical output (determinism)" — re-run, pass. `dither.dither_to_full_panel_palette()` and the flat-fill background path (`pf.new_canvas(bg_idx)`) are both pure/deterministic; no randomness anywhere in the current render path (the seeded-noise `MOOD_NOISE_SEED` machinery from 03-02 was removed along with `build_mood_background()`). |
| 4 (03-02, mechanism superseded by D-21/D-24) | Departing and arriving remain unambiguously distinguishable, reinforced by the state label | ✓ VERIFIED (mechanism changed, intent preserved) | 03-02's original mechanism (two dithered background moods + mirroring) was explicitly dropped by D-21 (flat background) and D-24 (no mirroring) — this is a *documented* supersession, not a silent regression. The current mechanism is a flat Blue vs. flat Green background field plus the "DEPARTING"/"ARRIVING" state-label text, which `server/test_render.py`'s "departing render's dominant nibble is 0x5 (Blue)" / "arriving render's dominant nibble is 0x6 (Green)" and "departing render draws the top-left 'DEPARTING' label" checks confirm — re-run, pass. |
| 5 (03-02, contract superseded by D-25/D-26's illustration layout) | The whole panel outside the illustration contains only legal palette indices, and the state color is provably dominant | ✓ VERIFIED (contract widened, not weakened, per the recorded reasoning) | `server/plane/render.py::_assert_legal_palette()` replaces 03-02's spatially-scoped `_assert_palette_contract()` (a documented, in-code-commented supersession — the docstring explains why the spatial scoping is no longer meaningful once a real multi-color illustration can legitimately sit anywhere in the new two-flight layout). Live-run `server/test_render.py`: "departing render's nibble set is a subset of the 6 legal Spectra 6 codes" — pass. Directly confirmed by reading `_assert_legal_palette()`: asserts `idx_set - _LEGAL_PANEL_INDICES` is empty and `bg_count >= other_max`. |
| 6 (03-03) | A missing, corrupt, or oversized illustration file degrades to the fallback and never raises or blanks the panel | ✗ FAILED | See gap #1/#2 in frontmatter. "Missing" is genuinely handled (verified live: renaming the whole `server/assets/icons/illustrations/` directory aside still returns a 960,000-byte panel with no exception). "Corrupt" is **not** handled: a byte-garbage file with a `.png` extension, injected via a monkeypatched `select_illustration()` return value, produces an uncaught `PIL.UnidentifiedImageError` straight out of `render_panel()`, reproduced live in this verification session. `draw_silhouette()` — the "retired flat silhouette" 03-03 specified as the last-resort degradation target — no longer exists anywhere in `server/plane/render.py`; nothing replaced its enclosing try/except. |
| 7 (03-01/02/03) | No debt-marker comments (TBD/FIXME/XXX/TODO/HACK/placeholder) in the phase's modified files | ✓ VERIFIED | `grep -nE "TBD\|FIXME\|XXX"` and a case-insensitive `TODO\|HACK\|placeholder\|not yet implemented\|coming soon` scan of `server/plane/render.py`, `server/plane/dither.py`, `server/plane/illustrations.py`, and `server/panel_format.py` all return zero matches. |
| 8 (traceability) | PLANE-01/PLANE-02, the requirement IDs declared by all three 03-0X plans, are present and accounted for in REQUIREMENTS.md with no orphans | ✓ VERIFIED | `REQUIREMENTS.md` lists both as `[x]` complete under "Plane (Runway 3)"; the Traceability table maps them to Phase 2 (their original delivery phase) and ROADMAP.md's Phase 3 section separately re-declares them as the phase's own requirement IDs for the hardware-legibility-closure-plus-illustration work. No requirement ID appears in any 03-0X plan's `requirements:` frontmatter that is absent from REQUIREMENTS.md. (Note: `server/test_render.py` line 435 references a bare `PLANE-04` in a check-name comment that does not exist in REQUIREMENTS.md or any plan frontmatter — flagged as an informational discrepancy below, not a Phase 3 gap, since no 03-0X plan declares PLANE-04.) |

**Score:** 7/8 truths verified (0 present, behavior-unverified)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Hardware-verified legibility of typography, background, composition and illustration on real Spectra 6 glass — the "not a rendered-PNG preview" half of the original phase goal | Phase 6: Final On-Glass Verification | ROADMAP.md Phase 3's "Note on the on-glass verification plan (2026-08-26)" and Phase 6's own section explicitly restating "PLANE-01, PLANE-02 (the hardware-verified-legibility half of both — closing what Phase 3 could not close without the physical device)" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/plane/illustrations.py` | Illustration selection module (03-03) | ✓ VERIFIED | Exists, 580 lines (extended well beyond 03-03's original scope by Phase 3.1's two-key selection); `select_illustration()`, `normalise_airline_key()`, `validate_illustration_file()`, `illustration_path_for_key()` all present and exercised by 42/42 passing checks in `server/test_illustrations.py`. |
| `server/test_illustrations.py` | Test harness for the selection module | ✓ VERIFIED | Exists (659 lines); the gap this phase's own `03-03-PLAN.md` Reconciliation Note flagged as open ("that exact file does not exist anywhere in this repository") was closed by the later `03-03-SUMMARY.md` session (commit `0fd8da8`) and further extended by Phase 3.1. 42/42 checks pass live. |
| `server/assets/icons/illustrations/HANDOFF.md` | Developer-facing hand-off spec | ✓ VERIFIED | Exists, contains required filenames per `required_filenames()`. |
| `server/assets/icons/illustrations/VENDOR.md` | Per-file provenance record | ✓ VERIFIED | Exists (closed by the same `0fd8da8` commit); per-file sha256/dimensions/airline/aircraft-type table confirmed present. |
| `server/assets/icons/illustrations/generic-fallback.png` + per-airline PNGs | Vendored illustration set | ✓ VERIFIED | 30+ PNGs present in `server/assets/icons/illustrations/` (extended by Phase 3.1's two-key shape set); `illustrations.py --validate`-equivalent checks pass in `test_illustrations.py`. An `_unresolved/` subdirectory holding unused candidate art also exists but is not part of the glob the render path reads from and does not affect selection. |
| `server/plane/dither.py` | Palette quantization module (03-02) | ✓ VERIFIED, but its 03-02-era `build_mood_background()` no longer exists | Module retained as the home of `dither_to_full_panel_palette()` (the illustration path's no-remap quantizer) and `write_calibration_preview()`. `build_mood_background()` was deliberately retired (D-21); `server/test_dither.py` explicitly regression-tests its absence: "PASS `build_mood_background()` no longer exists on server.plane.dither (D-21 retirement)." |
| `server/assets/fonts/ZillaSlab-{SemiBold,Bold}.ttf` | Vendored typeface (03-01) | ✓ VERIFIED to exist, but superseded as the active render font | Files exist with full OFL provenance in `VENDOR.md` (03-01's own deliverable). However, `server/plane/render.py` no longer references them at all — D-27 replaced Zilla Slab with PT Serif Regular for every text role (`PT_SERIF_REGULAR`/`PT_SERIF_BOLD` constants, confirmed by direct read of `render.py` lines 93-98). This is a documented, in-CONTEXT.md-recorded pivot, not a silent regression — flagged here for visibility since it means 03-01's headline typography deliverable is not what ships today. |
| `server/panel_format.py` | Palette/wire-format bridge | ✓ VERIFIED | `PALETTE_RGB`, `padded_palette()`, `INDEX_TO_NIBBLE` intact; `server/test_pipeline_e2e.py` and the full `scripts/run-all-tests.sh` run confirm no wire-format regression. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_build_active_canvas()` | `illustrations.select_illustration()` | direct call, passing `route` and `flight.get("aircraft_type")` | ✓ WIRED | Confirmed by direct read (`render.py` line ~562) and by `server/test_render.py`'s "rendering with a main flight carrying a type calls `select_illustration()` with that exact type" check (re-run, pass). |
| `draw_illustration()` | `dither.dither_to_full_panel_palette()` | direct call, no `.point()` remap | ✓ WIRED | Confirmed by direct read (`render.py` line ~300) — the no-remap discipline from 03-02/03-03's planning is intact. |
| `_resize_illustration()` / `draw_illustration()` | error handling for a decode failure | **none** | ✗ NOT_WIRED | This is gap #1 above — no `try`/`except` anywhere between `select_illustration()`'s returned path and the pixel data reaching `canvas.paste()`. |
| `illustrations.validate_illustration_file()` | the render-time illustration-loading path | **none** | ✗ NOT_WIRED | `validate_illustration_file()` is called only from `illustrations.py`'s own `main()` (`--validate`), never from `render.py` or `poll_loop.py`. This is gap #2 above. |
| `poll_loop.py::main()` | a failed render cycle | broad `except Exception` around `run_once()` | ✓ WIRED (system-level safety net, but changes the failure mode) | Confirmed: `poll_loop.py` lines 310-312 catch any exception from `run_once()`, log it, and return exit code 1 without crash-looping or blanking the previously served panel. This means gap #1/#2 do **not** blank the device's display or crash the service — but they do mean a single corrupt illustration file silently freezes *all* future panel updates (not just that one flight/airline) until the file is fixed, which is a materially different (and worse) failure mode than the "degrade to a fallback illustration and keep serving fresh flights" behavior 03-03's threat model explicitly claimed. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| PLANE-01 | 03-01, 03-02, 03-03 | Flight number, airline, destination for the next departing flight | ✓ SATISFIED | Confirmed present in the current two-flight layout's main-flight text block (`_flight_line1_text()`/`_flight_line2_text()`), re-tested live. |
| PLANE-02 | 03-01, 03-02, 03-03 | Flight number, airline, origin for the next landing flight | ✓ SATISFIED | Confirmed present symmetrically for the arriving state, re-tested live. Both requirements' *hardware-verified-legibility* half is explicitly deferred to Phase 6 per ROADMAP.md (see Deferred section) — this is documented scope narrowing, not an unaddressed requirement. |

No orphaned requirements: REQUIREMENTS.md's Traceability table lists exactly PLANE-01/02/03, DEVICE-03/04/05 for v1, and every ID any 03-0X plan declares (PLANE-01, PLANE-02) is accounted for.

**Informational, not a gap:** `server/test_render.py` line 435 labels a check "(D-26/PLANE-04)" — `PLANE-04` does not exist in `REQUIREMENTS.md` or in any Phase 3 plan's `requirements:` frontmatter. This looks like a requirement ID coined ad hoc during the live D-25/D-26 redesign session that was never formally added to REQUIREMENTS.md. It doesn't block this verification (no 03-0X plan claims PLANE-04), but is worth a housekeeping fix — either formalize PLANE-04 in REQUIREMENTS.md or rename the comment to reference an existing requirement.

### Anti-Patterns Found

None. `grep`-based scans for `TBD`/`FIXME`/`XXX`, `TODO`/`HACK`/`placeholder`/"not yet implemented"/"coming soon" across `server/plane/render.py`, `server/plane/dither.py`, `server/plane/illustrations.py`, and `server/panel_format.py` all returned zero matches.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Corrupt illustration file degrades gracefully | Monkeypatched `select_illustration()` to return a byte-garbage `.png` path, called `render_panel()` | `CRASHED: UnidentifiedImageError cannot identify image file '...'` | ✗ FAIL |
| Missing illustration directory degrades gracefully | Renamed `server/assets/icons/illustrations/` aside, called `render_panel()` | `NO CRASH, len=960000` | ✓ PASS |
| Full automated suite | `bash scripts/run-all-tests.sh` | `==> Result: PASS` (all 9 harnesses, coverage threshold met) | ✓ PASS |
| `server/test_render.py` | `server/.venv/bin/python3 server/test_render.py` | `render: 35/35 checks pass` | ✓ PASS |
| `server/test_illustrations.py` | `server/.venv/bin/python3 server/test_illustrations.py` | `illustrations: 42/42 checks pass` | ✓ PASS |
| `server/test_dither.py` | `server/.venv/bin/python3 server/test_dither.py` | `dither: 6/6 checks pass` | ✓ PASS |

### Human Verification Required

None. This phase's remaining on-glass/visual-judgment items are Phase 6's explicit responsibility, not this phase's (see Deferred section) — nothing in this phase's current, narrowed scope requires human judgment beyond what the automated suite already covers.

### Gaps Summary

One root cause produces two related gaps: **the render-time illustration path has no error handling for a decodable-but-corrupt or oversized file, because the "retired flat silhouette" fallback function (`draw_silhouette()`) and its enclosing try/except — which 03-03's plan and threat model both relied on as the last-resort degradation mechanism — were removed when the D-25/D-26 two-flight redesign replaced the whole illustration-compositing path, and nothing replaced that safety net.**

- The "missing file" case still degrades correctly (`select_illustration()`'s `os.path.isfile()` guards at every tier, falling through to `None` and skipping the illustration draw entirely).
- The "corrupt file" case does not: reproduced live, a byte-garbage file with a `.png` extension crashes `render_panel()` with an uncaught `PIL.UnidentifiedImageError`.
- The "oversized file" case is architecturally the same gap: `validate_illustration_file()`'s pixel-count cap exists but is wired only into the offline `--validate` CLI, never into the render path.

`poll_loop.py`'s outer `except Exception` around `run_once()` prevents this from crash-looping the service or blanking the device's display — but it means a single corrupt or oversized illustration file (of the 30+ now vendored, spanning two hand-off rounds across Phase 3 and Phase 3.1) silently freezes *all* future panel updates until someone notices and fixes the file, rather than degrading gracefully to a fallback for just that one airline as the original design promised and as `test_illustrations.py`/`test_render.py`'s test suite (42/35 checks) does not currently exercise.

This is reported as a gap rather than deferred, because no later phase (checked: Phase 3.1, Phase 6) addresses it, and it is a directly falsifiable, reproduced failure of an explicit must-have this phase's own plan and threat model committed to.

---

_Verified: 2026-08-27T08:10:15Z_
_Verifier: Claude (gsd-verifier)_
