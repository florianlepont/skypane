---
phase: 03-visual-polish-on-real-glass
verified: 2026-08-27T09:05:00Z
status: passed
score: 8/8 must-haves verified (1 roadmap success criterion + 7 plan-level truths that survived documented supersession, including the gap-closure truth now fixed by 03-04)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:
    - "A missing, corrupt or oversized illustration file degrades to the fallback (and does not crash the render pipeline) — an explicit must-have of 03-03-PLAN.md, and the claimed mitigation for STRIDE threat T-03-03-02 in the same plan."
    - "Missing/corrupt/oversized illustration guard: validate_illustration_file()'s decompression-bomb cap (ILLUSTRATION_MAX_PIXELS) actually protects the render path, not only the offline --validate CLI."
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "Hardware-verified legibility of the shipped typography, background, composition, and illustration on real Spectra 6 glass (the original phase goal's 'not a rendered-PNG preview' clause, and the original 03-04 on-glass plan)."
    addressed_in: "Phase 6: Final On-Glass Verification"
    evidence: "ROADMAP.md Phase 3 section, 'Note on the on-glass verification plan (2026-08-26)': 'This phase's original fourth plan (03-04, the on-glass verification battery) was moved to Phase 6 ... at the user's explicit request ... The four on-glass success criteria that used to live here ... moved with it — they are not duplicated below.' Phase 6's ROADMAP entry explicitly restates 'Requirements: PLANE-01, PLANE-02 (the hardware-verified-legibility half of both — closing what Phase 3 could not close without the physical device).'"
human_verification: []
---

# Phase 3: Visual Polish on Real Glass Verification Report

**Phase Goal (as scoped by the current ROADMAP.md, which explicitly narrowed the original phase goal — see Deferred section):** Each detected flight renders a dithered, per-airline-generated aircraft illustration for airlines covered by the generated set, with a single dithered generic illustration as the fallback for uncovered airlines and the "Route unavailable" state, never mirrored by state (D-24) — verified by the automated suite, not by eye. Hardware-verified legibility of the resulting typography/background/composition was explicitly moved to Phase 6 and is not this phase's criterion (see Deferred section).

**Verified:** 2026-08-27T09:05:00Z
**Status:** passed
**Re-verification:** Yes — after gap-closure plan 03-04

## Re-verification scope

This is a re-run following 03-04-PLAN.md, a gap-closure plan targeting the single gap the prior `03-VERIFICATION.md` (2026-08-27T08:10:15Z, score 7/8) found: the live render path had no error handling around Pillow decoding a vendored illustration, so a corrupt or oversized `.png` could raise `PIL.UnidentifiedImageError` out of `render_panel()`, silently freezing all future panel updates via `poll_loop.py`'s outer exception handler.

Per the re-verification protocol: the previously-failed truth (#6, the missing/corrupt/oversized-illustration degradation) got full three-level (exists/substantive/wired) verification plus an independent live reproduction, run by this verifier directly (not taken from `03-04-SUMMARY.md`'s claims). The seven previously-passed truths got a regression check via the full test suite re-run.

**Independent verification performed in this session (not trusting SUMMARY.md):**

```
$ server/.venv/bin/python3 server/test_render.py       -> render: 38/38 checks pass
$ server/.venv/bin/python3 server/test_illustrations.py -> illustrations: 42/42 checks pass
$ bash scripts/run-all-tests.sh                          -> ==> Result: PASS (9/9 harnesses, 79% coverage, floor 75%)
$ server/.venv/bin/python3 -m ruff check server/plane/render.py server/test_render.py -> All checks passed!
$ git status --porcelain server/plane/illustrations.py server/poll_loop.py -> (empty — neither modified)
```

Live repro of the exact crash 03-VERIFICATION.md reproduced (a byte-garbage `.png` forced through `select_illustration()`), re-run independently in this session:

```
render: skipping illustration /var/folders/.../tmphy981kko.png - header unreadable (UnidentifiedImageError)
960000
```

`render_panel()` returns exactly `960000` bytes (a full valid panel) instead of raising — confirmed live, not from the SUMMARY's transcript.

Both call sites confirmed wired, independently:

```
$ python3 -c "...s=inspect.getsource(r._build_active_canvas); print(s.count('_resize_illustration'), s.count('_load_illustration_safely'))"
0 2
$ python3 -c "...print(r._illustration_over_pixel_cap('/nonexistent/nope.png'), r._illustration_over_pixel_cap(i.generic_fallback_path()))"
True False
```

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (ROADMAP SC) | Each detected flight renders a dithered per-airline illustration for covered airlines; uncovered airlines and Route-unavailable both render a single dithered generic illustration; never mirrored by state (D-24) | ✓ VERIFIED | Unchanged since prior verification — `select_illustration()`'s four-tier ladder, `draw_illustration()`'s dithered (not flat) compositing, no mirror call anywhere in `render.py`. Re-run live: `test_render.py` 38/38, `test_illustrations.py` 42/42. |
| 2 (03-01) | A genuinely long destination/origin city name and long airline name shrink to fit rather than clipping or crossing the safe margin | ✓ VERIFIED (regression check) | Re-run live as part of the 38/38 pass; no change to the underlying `fit_text_size()` path in this gap-closure plan. |
| 3 (03-01/02/03) | Rendering the same flight (and route) twice is byte-identical, so the device is never woken for a redundant refresh | ✓ VERIFIED (regression check) | Re-run live; `_load_illustration_safely()` and `_resize_illustration()` are both pure/deterministic (no randomness introduced by 03-04). |
| 4 (03-02, mechanism superseded by D-21/D-24) | Departing and arriving remain unambiguously distinguishable, reinforced by the state label | ✓ VERIFIED (regression check) | Re-run live; unaffected by 03-04's scope (illustration-decode guard only). |
| 5 (03-02, contract superseded by D-25/D-26's illustration layout) | The whole panel outside the illustration contains only legal palette indices, and the state color is provably dominant | ✓ VERIFIED (regression check) | Re-run live; `_assert_legal_palette()` untouched by 03-04. |
| 6 (03-03, closed by 03-04) | A missing, corrupt, or oversized illustration file degrades to the fallback and never raises or blanks the panel | ✓ VERIFIED | Independently reproduced in this session (see above): a byte-garbage `.png` forced through `select_illustration()` now degrades to `generic-fallback.png` (`render_panel()` returns exactly 960,000 bytes, one `stderr` diagnostic, no exception) instead of raising `PIL.UnidentifiedImageError`. `_illustration_over_pixel_cap()` confirmed to reject an unreadable/oversized header (`True`) and pass a real vendored file (`False`), read via header only (`Image.open().size`, no decode) — confirmed by reading `server/plane/render.py` lines 268-290. `_load_illustration_safely()`'s candidate ladder (`path` → `generic_fallback_path()` → `None`) confirmed by direct read (lines 293-344) and by three passing regression checks (36, 37, 38) that feed a real byte-garbage file and a real, genuinely-decodable 42-million-pixel PNG through the actual `render_panel()` code path — re-run live, all pass. Both `_build_active_canvas()` call sites (main card and previous card) confirmed rewired through the guarded loader (`0` direct `_resize_illustration` calls, `2` `_load_illustration_safely` calls, confirmed by live introspection, not by reading the plan's claim). |
| 7 (03-01/02/03) | No debt-marker comments (TBD/FIXME/XXX/TODO/HACK/placeholder) in the phase's modified files | ✓ VERIFIED | Re-run live: `grep -nE "TBD|FIXME|XXX"` and a case-insensitive `TODO|HACK|placeholder|not yet implemented|coming soon` scan of `server/plane/render.py` and `server/test_render.py` (this plan's two changed files) return zero matches, except one comment string describing behavior ("not drawn empty/placeholder") which is prose, not a debt marker. |
| 8 (traceability) | PLANE-01/PLANE-02, the requirement IDs declared by all four 03-0X plans (03-01 through 03-04), are present and accounted for in REQUIREMENTS.md with no orphans | ✓ VERIFIED | `03-04-PLAN.md`'s `requirements:` frontmatter also declares `[PLANE-01, PLANE-02]` — no new ID introduced. `REQUIREMENTS.md` lists both as `[x]` complete; no orphaned ID. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Hardware-verified legibility of typography, background, composition and illustration on real Spectra 6 glass — the "not a rendered-PNG preview" half of the original phase goal | Phase 6: Final On-Glass Verification | ROADMAP.md Phase 3's "Note on the on-glass verification plan (2026-08-26)" and Phase 6's own section explicitly restating "PLANE-01, PLANE-02 (the hardware-verified-legibility half of both — closing what Phase 3 could not close without the physical device)" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/plane/render.py` | Guarded illustration loader (03-04) | ✓ VERIFIED | `_illustration_over_pixel_cap()` (line 268) and `_load_illustration_safely()` (line 293) present, both call sites of `_build_active_canvas()` rewired (lines 643, 656). Confirmed by direct read and live introspection. |
| `server/test_render.py` | Three new regression checks (36-38) | ✓ VERIFIED | `EXPECTED_CHECK_COUNT = 38` confirmed; all three checks re-run live and pass. |
| `server/plane/illustrations.py` | Unchanged (per plan's explicit constraint) | ✓ VERIFIED | `git status --porcelain server/plane/illustrations.py` empty; `test_illustrations.py` 42/42 unchanged. |
| `server/poll_loop.py` | Unchanged (outer safety net stays as-is) | ✓ VERIFIED | `git status --porcelain server/poll_loop.py` empty. |
| (all artifacts from the prior verification's table) | Unchanged | ✓ VERIFIED (regression) | No file outside `server/plane/render.py`/`server/test_render.py` was touched by 03-04; prior verification's artifact table stands unchanged. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_build_active_canvas()` (main card) | `_load_illustration_safely()` | direct call, `main_path`/`main_w` | ✓ WIRED | Confirmed live: `render.py` line 643. |
| `_build_active_canvas()` (previous card) | `_load_illustration_safely()` | direct call, `prev_path`/`prev_w` | ✓ WIRED | Confirmed live: `render.py` line 656. Both sites needed rewiring — confirmed both are, not just one. |
| `_load_illustration_safely()` | `illustrations.generic_fallback_path()` | ladder fallback, deduped | ✓ WIRED | Confirmed by direct read (lines 312-316) and by check 36/38 passing live. |
| `_illustration_over_pixel_cap()` | `illustrations.ILLUSTRATION_MAX_PIXELS` | imported constant, not restated | ✓ WIRED | Confirmed by direct read (line 288) — no duplicated numeric literal. |
| `poll_loop.py::main()` | a failed render cycle | broad `except Exception` around `run_once()` | ✓ WIRED (now a true last resort, not the primary degradation path) | Unchanged from prior verification; now backstops genuinely unanticipated failures only, since the illustration-decode failure mode that used to reach it is intercepted earlier by `_load_illustration_safely()`. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| PLANE-01 | 03-01, 03-02, 03-03, 03-04 | Flight number, airline, destination for the next departing flight | ✓ SATISFIED | Present in the two-flight layout's main-flight text block; 03-04 additionally ensures a corrupt/oversized illustration no longer freezes future updates to this data. Hardware-verified-legibility half deferred to Phase 6 (documented scope narrowing). |
| PLANE-02 | 03-01, 03-02, 03-03, 03-04 | Flight number, airline, origin for the next landing flight | ✓ SATISFIED | Same call path, both states; same deferral applies. |

No orphaned requirements: `REQUIREMENTS.md`'s Traceability table lists exactly PLANE-01/02/03, DEVICE-03/04/05 for v1; every ID any 03-0X plan (01 through 04) declares is PLANE-01/PLANE-02, both accounted for.

### Anti-Patterns Found

None (blocking). `grep`-based scans for `TBD`/`FIXME`/`XXX`, `TODO`/`HACK`/`placeholder`/"not yet implemented"/"coming soon" across the two files this plan modified (`server/plane/render.py`, `server/test_render.py`) return zero debt markers.

### Behavioral Spot-Checks (re-run independently in this session)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Corrupt illustration file degrades gracefully | Monkeypatched `select_illustration()` to return a byte-garbage `.png` path, called `render_panel()` | `render: skipping illustration ... - header unreadable (UnidentifiedImageError)` then `960000` bytes returned, no exception | ✓ PASS (previously ✗ FAIL — now closed) |
| Non-string `airline_name` and undecodable illustration text-drop (CR-01/CR-02, see below) | Advisory only — see Code Review Findings section | — | Not scored (outside phase 03's stated must-haves) |
| `server/test_render.py` | `server/.venv/bin/python3 server/test_render.py` | `render: 38/38 checks pass` | ✓ PASS |
| `server/test_illustrations.py` | `server/.venv/bin/python3 server/test_illustrations.py` | `illustrations: 42/42 checks pass` | ✓ PASS |
| Full automated suite | `bash scripts/run-all-tests.sh` | `==> Result: PASS` (9/9 harnesses, 79% coverage, floor 75%) | ✓ PASS |
| `ruff check` on both changed files | `server/.venv/bin/python3 -m ruff check server/plane/render.py server/test_render.py` | `All checks passed!` | ✓ PASS |

### Human Verification Required

None. All Phase 3 (as narrowed by ROADMAP.md) must-haves are code-verifiable and were verified live in this session. This phase's remaining on-glass/visual-judgment items are Phase 6's explicit responsibility (see Deferred section).

## Code Review Findings — Advisory, Not Scored as Gaps

A code review (`03-REVIEW.md`, 2026-08-27) ran against this phase's changed files and found 2 Critical findings. Both were independently reproduced live in this session (not taken on the review's word):

- **CR-01** (`server/plane/render.py:641-663`): when illustration loading exhausts its ladder entirely (both the selected illustration *and* `generic-fallback.png` are undecodable), `_build_active_canvas()` skips `draw_main_text_block()`/`draw_previous_text_block()` too, because both are gated on `main_bbox is not None`. Reproduced live in this session: forcing both `select_illustration()` and `generic_fallback_path()` to the same garbage file leaves only `['DEPARTING', 'ORY · RWY 3']` drawn — no callsign, destination, or airline text.
- **CR-02** (`server/plane/render.py:477-488`): `_flight_line2_text()` treats a truthy non-string `airline_name` (e.g. `12345` or `['x','y']`) as a hit rather than a miss, and renders its raw Python repr onto the panel instead of falling back to `"Route unavailable"`. Reproduced live: `_flight_line2_text({'airline_name': 12345}, 'A320')` returns `'12345 · A320'`.

**Why these are not scored as gaps for this phase's re-verification:**

1. **CR-01 pre-dates 03-04 and pre-dates this phase's gap.** `git show 73a6eb2:server/plane/render.py` (the D-25/D-26 two-flight redesign commit, well before the gap-closure plan) shows the identical `main_bbox is not None` text-gating structure already in place. 03-04 did not introduce, worsen, or claim to fix this — its own must-have language (`03-04-PLAN.md` frontmatter, truth 3) is scoped narrowly to "the render skips the illustration entirely and still returns a valid 960,000-byte panel," which is satisfied (confirmed: check 38 passes, and the live repro above returns a full-length buffer without raising). The plan never asserted the text block would remain drawn — only that the render would not crash.
2. **Neither CR-01 nor CR-02 falsifies ROADMAP Phase 3's stated success criterion**, which is scoped to "the selection and compositing mechanism" of the illustration itself, not the text-rendering path or non-string route-payload handling.
3. **CR-01 only triggers under a compound failure** (both the per-airline/generic illustration AND the universal fallback are simultaneously undecodable) — an even narrower edge case than the single-file corruption 03-04 targeted, and one that already existed (with the same behavior) in the "illustration directory renamed aside" scenario the prior verification scored as correctly degrading.

**These are real, reproduced bugs and are not being dismissed** — they directly touch PLANE-01/PLANE-02 in specific edge cases (a compound illustration failure for CR-01; any malformed non-string `airline_name` for CR-02, independent of illustration state). Recommend a follow-up plan (or a note carried into Phase 6's on-glass pass, since CR-02 in particular would show a visibly broken raw-repr string on real hardware) to fix both, using the code review's own suggested patches. This recommendation does not block Phase 3 completion because neither finding falsifies a must-have this phase (or its 03-01/02/03/04 plans) actually committed to.

### Gaps Summary

No gaps. Both gaps from the prior verification (2026-08-27T08:10:15Z, score 7/8) are closed:

- **Gap #1 (corrupt file crashes render)**: closed by `_load_illustration_safely()`'s try/except-per-candidate degradation ladder, verified live via independent reproduction of the exact crash scenario the prior verification recorded — it now degrades instead of raising.
- **Gap #2 (oversized file bypasses the pixel cap in the render path)**: closed by `_illustration_over_pixel_cap()`, which reads the PNG header only (no decode) and is wired into the loader's ladder before any `_resize_illustration()` call — verified live against a genuinely valid, genuinely oversized (42M-pixel) fixture, which a bare try/except could not have satisfied.

Two Critical findings from an independent code review (CR-01, CR-02) were investigated, reproduced live, and found to be pre-existing issues outside this phase's committed must-haves (see "Code Review Findings" section above) — not scored as gaps, but flagged for follow-up work, ideally before Phase 6's on-glass sign-off.

---

_Verified: 2026-08-27T09:05:00Z_
_Verifier: Claude (gsd-verifier)_
