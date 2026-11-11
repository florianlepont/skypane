---
phase: 64-photo-pipeline-server-only
verified: 2026-11-10T00:00:00Z
status: human_needed
score: 4/4 success criteria verified in code (PHOTO-04 verified on the literal wording only)
overrides_applied: 0
gaps: []
human_verification:
  - test: "Render a real portrait with `python -m server.photo --in <portrait.jpg> --out <dir outside repo>` in fill and bands, both panel sizes, and look at it (ideally on the physical frame)"
    expected: "Faces are recognisable and acceptable at the default parameters (cutoff 1.0, strength 0.8, saturation 1.2), or the defaults are changed and re-recorded"
    why_human: "The owner answered 'I don't know' on synthetic sheets and no real face was ever rendered; the test is about how skin looks, which no assertion can decide"
  - test: "Decide whether the unexplained 8.8 degree hue drift on landscape fill (tones II to IV) matters, or investigate it"
    expected: "A cause or an accepted limit written in docs/PHOTO-RENDERING.md"
    why_human: "Cause not investigated; whether it is visible is a judgement"
---

# Phase 64: Photo Pipeline (Server Only) Verification Report

**Phase Goal:** A photo handed to the server can be safely reduced to one stored copy and rendered as a 6-colour image for either panel size, with the quality limits known before the rendering is frozen.
**Branch:** `phase/64-photo-pipeline` (HEAD e234376)
**Status:** human_needed (no code gaps; one honest unproven area)
**Re-verification:** No, initial verification

## Success criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Bad uploads rejected; one reduced copy, original not kept | VERIFIED | Ran `normalize_upload` myself (in memory). Rejected with stable codes: empty -> `empty`; 13 MiB -> `too_large`; plain text, HTML-prefixed PNG, SVG, GIF, BMP, TIFF, PDF -> `not_an_image`; PNG truncated -> `corrupt`; 9000x9000 PNG -> `too_many_pixels`; 50x50 -> `too_small`; animated WebP and APNG -> `animated`. A valid 3.7 MB JPEG with EXIF description and rotation tag came out as one 1365x2048 JPEG, 920 KB, orientation applied, EXIF dropped (the description string is absent, no orientation tag). The function takes only bytes (no filename or content type), does no file I/O, and returns a frozen `StoredPhoto(jpeg, width, height)`, so the original is unreachable. Decoder allowlist JPEG/PNG/WebP only; header-only size check before decode. |
| 2 | One stored photo -> 1200x1600 and 800x480, palette-only, path separate from plane | VERIFIED | `render_photo` returned mode "P" images of exactly (1200,1600) and (800,480), pixel indices only within 0..5, for fill (centre, corners) and bands. Deterministic (identical bytes on repeat). `server/photo/render.py` reuses only `panel_format` and `plane.dither` helpers; it does not call the plane screen renderer. `server/test_photo_render.py` also covers packing length and the sim landscape profile. Junk or PNG as a stored copy raises a fixed-message ValueError. |
| 3 | Fill (default) vs bands; crop position changes result | VERIFIED | `FitSetting()` defaults to fill, 0.5/0.5. Portrait panel: pos_x 0 vs 1 gives different pixels. Landscape: pos_y 0 vs 1 gives different pixels (my first probe used a gradient that varied on the wrong axis and showed no change; with a vertical gradient it differs, which is correct since only the slack axis matters). Bands: corners are palette index 1 (white), the photo is centred and whole, and tests assert bands ignore crop position. Bad positions (NaN, 2, -1, True, "a") raise ValueError. |
| 4 | Skin-tone samples tried in both sizes; result and limits recorded before freeze | VERIFIED on literal wording, weak on substance | `docs/PHOTO-RENDERING.md` records a 390-cell synthetic grid (6 tones x full/dull x both panel sizes x fill/bands x 8 parameter sets), per-tone/size measures, the owner outcome, known limits, a "Not tried" list, and states the defaults are kept but "not a verified-good result". Trial tooling exists (`server/photo/trial.py`, `python -m server.photo`) and refuses an output dir inside the repo. A test pins `DEFAULT_PREP` literals. |

## PHOTO-04: is "tried on synthetic samples, result and limits recorded" a fair reading?

The requirement text says "tried on skin-tone samples, and the result and any limit are recorded before the rendering is frozen". Read literally, it is met: samples were rendered in both sizes, measured, and the outcome and limits are written down before any later phase builds on the defaults. The wording does not say the result must be good, nor that real faces must be used.

What it does not give you, and the document says so plainly rather than hiding it:
- No human judged any skin rendering. The owner's answer was "I don't know"; the record states no verdict is claimed.
- No real face (screen or physical frame) was rendered. Every skin statement is about procedural ellipses.
- Fidelity and hue numbers measure dither closeness to the boosted image, not whether a face looks right. Nothing was measured with a colorimeter.
- The parameter set is therefore the starting default, untuned. "Frozen" here means "pinned by a test and documented", not "validated".

I judge this an honest and acceptable reading for a server-only phase, provided the project carries the caveat forward (it is in the doc's status line and Known limits). It would be an overreach to call the skin rendering verified. That residual is why the status is human_needed and not passed.

## Hue drift on landscape fill (8.8 degrees)

Recorded in the doc's results summary (landscape fill, tones II to IV, up to 8.8 degrees, versus at most 2.8 in portrait and landscape bands), with the cause "not investigated". It is unproven whether this is visible or merely an artefact of how the measure is taken (a smaller face region in 800x480 fill means fewer dithered pixels in the mean; that is a guess, not tested). Two small inconsistencies: the 64-04 SUMMARY says it is "listed as a follow-up in the rendering document", but the document's "Follow-ups" section does not mention it (only the results summary and Known limits context do); and the owner was initially told the drift was under 4 degrees, which the summary corrects. Neither blocks the phase; I suggest adding one line to the follow-ups.

## Protected paths and repository hygiene

| Check | Result |
|-------|--------|
| `git diff origin/explore/photo-mode-v1-3..HEAD` on `server/plane`, `server/fixtures/golden`, `server/panel_format.py`, `hardware`, `firmware`, root `.planning/STATE.md`, root `.planning/ROADMAP.md` | Empty |
| Phase 47/47.1 files touched | None (no path containing 47 in the diff) |
| Added files | 24: docs, `server/photo/*`, five `server/test_photo_*.py`, two `test-support/photo_*.py`, five SUMMARYs; modified: `pyproject.toml` (mypy module list only) and three workstream files (REQUIREMENTS, ROADMAP, STATE under `.planning/workstreams/v1-3`) |
| Image or binary files added | None (diff contains only .py, .md, .toml) |
| Plan/phase IDs in code comments | grep for phase/plan/PHOTO-0x/NN-NN in `server/photo`, `test-support/photo_*.py`, `server/test_photo_*.py`: no hits; `scripts/check_comment_history.py check` rc 0 |
| Tests | `pytest server/test_photo_*.py --no-cov`: 116 passed |
| Lint/type/size | ruff clean; mypy on `server/photo`: no issues (mypy notes unused pre-existing sections, unrelated); function-size gate: none over 80 |

## Requirements coverage

| Req | Status | Note |
|-----|--------|------|
| PHOTO-01 | SATISFIED | criterion 1 |
| PHOTO-02 | SATISFIED | criterion 2; order crop, boost, dither in `render.py` |
| PHOTO-03 | SATISFIED | criterion 3; same stored copy serves both sizes |
| PHOTO-04 | SATISFIED on literal wording, substance unproven | see above |

No orphaned requirements.

## Anti-patterns

None blocking. No TBD/FIXME/XXX markers in the phase's code. Not wired into any route or companion by design (Phase 64 is server-only; consumers come in 65 to 67), so nothing is orphaned by mistake.

## Non-blocking observations

- ROADMAP.md (workstream) still shows plan 64-04 unchecked and the phase line unchecked while REQUIREMENTS marks PHOTO-01..04 Complete; update at phase close.
- Follow-ups in the doc (bounded concurrent normalisation, body cap applied while reading, server-side preview, HEIC message) are real requirements for Phase 65/67 and must not be lost.

## Gaps Summary

No code gaps. The goal (safe reduction to one stored copy, 6-colour render for both sizes, limits recorded) is achieved. What remains unproven is how real skin looks and whether the 8.8 degree landscape-fill drift matters; both are routed to human verification above.

_Verified: 2026-11-10_
_Verifier: Claude (gsd-verifier)_
