---
phase: quick-260902-req
plan: 02
subsystem: ui
tags: [pillow, image-processing, companion-web, illustration-gallery, python-stdlib-http]

requires:
  - phase: quick-260902-req (plan 01)
    provides: server.plane.render's ILLUSTRATION_ALPHA_THRESHOLD / _threshold_alpha() / _opaque_bbox() — the panel-side opaque-bbox measurement this plan imports rather than reimplements
provides:
  - companion/illustration_normalize.py — normalized_png_bytes()/cached_normalized_png_bytes(), tight-cropping each vendored illustration to its painted bbox and re-centring it into one shared 900x263 output frame
  - Handler._serve_illustration_image() now serves normalized bytes, with a malformed-asset-degrades-to-404 defensive wrapper
  - Explicit width/height on every .airline-card__image plus a matching CSS aspect-ratio/object-fit:contain rule, so the gallery grid does not reflow on a cold-cache load
affects: [companion-airlines-gallery, illustration-normalization]

tech-stack:
  added: []
  patterns:
    - "Import, never reimplement, a proven measurement across a module boundary (server.plane.render._opaque_bbox()/_threshold_alpha() imported into companion/illustration_normalize.py, matching companion/pages/history_page.py's existing panel_render import precedent)"
    - "Resize-then-measure, never crop-then-resize, when a bbox will be re-measured after a resize — cropping tight to a bbox before a LANCZOS resize starves the resample of edge context and shifts the re-measured bbox asymmetrically by up to ~2px"

key-files:
  created:
    - companion/illustration_normalize.py
  modified:
    - companion/app.py
    - companion/pages/airlines_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "Target output box chosen at the measured median painted aspect ratio (3.42:1, rounded to 900x263px) rather than the widest ratio — since every crop is scaled fit-inside (never crop-to-fill), the target ratio can never cause clipping, only how the letterbox dead-space is distributed; the median spreads it evenly across the 2.97:1-4.98:1 range instead of concentrating it on the narrower files."
  - "normalized_png_bytes() resizes the whole source image first (matching panel_render._resize_illustration()'s own shape) and only crops to the re-measured opaque bbox afterward, not before — this was a mid-Task-1 correction after the original crop-then-resize order broke the '1px centring' contract on air-europa.png and similar files."

requirements-completed: [REQ-260902-req-WEB]

coverage:
  - id: D1
    description: "companion/illustration_normalize.py normalizes all 43 vendored illustrations to identical pixel dimensions, painted content centred within 1px on both axes, never clipped, importing the panel's own opaque-bbox/alpha-threshold logic rather than reimplementing it"
    requirement: "REQ-260902-req-WEB"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py — Section 1.5 (4 checks: identical dimensions, centred+unclipped across all 43 files, None-bbox fallback, no companion/ module redefines the alpha threshold)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Handler._serve_illustration_image() serves normalized bytes (membership test still strictly first, unknown-key/malformed-asset 404s indistinguishable), and the gallery card markup/CSS carry matching intrinsic dimensions so the grid does not reflow"
    requirement: "REQ-260902-req-WEB"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py — card markup width/height check"
        status: pass
      - kind: e2e
        ref: "companion/test_status_pages.py — GET /illustration/{key}.png against a real running service check"
        status: pass
    human_judgment: false
  - id: D3
    description: "Visual sign-off: every gallery card frames its aircraft at the same optical centre and size band, nothing clipped, on both desktop and a real phone, with a cold-cache load producing no grid reflow"
    verification: []
    human_judgment: true
    rationale: "The plan's own checkpoint (gate=blocking) requires the developer's explicit visual sign-off, including a real-device phone check this execution environment has no tool to perform. Automated/visual evidence gathered in lieu of that sign-off is recorded below (server-rendered contact sheets of the four named extreme files plus an 8-card mock gallery grid, and real curl-verified HTTP responses against a locally running companion/app.py instance), but the checkpoint itself was not resolved — see 'Checkpoint Pending' below."

duration: ~50min
completed: 2026-09-02
status: incomplete
---

# Quick Task 260902-req-02: Companion Airlines gallery illustration normalization Summary

**Server-side aircraft-illustration normalization for the companion Airlines gallery, cropping each vendored PNG to its opaque bbox (imported from `server/plane/render.py`, not reimplemented) and re-centring it into a shared 900x263 frame, with the two `type="auto"` tasks committed and the plan's blocking `checkpoint:human-verify` still open.**

## Performance

- **Duration:** ~50 min
- **Completed (auto tasks):** 2026-09-02T18:27:11Z
- **Tasks:** 2 of 2 `type="auto"` tasks complete; 1 `type="checkpoint:human-verify"` task pending
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- New `companion/illustration_normalize.py`: `normalized_png_bytes(path)` tight-crops to the opaque (painted) bbox — via `server.plane.render._opaque_bbox()`/`_threshold_alpha()`, imported directly, never re-derived — then scales to fit inside a shared 900x263 target box (LANCZOS, matching `_resize_illustration()`) and pastes centred onto a fully transparent canvas of that exact size. `cached_normalized_png_bytes(path)` wraps it in an `lru_cache` keyed on path + mtime.
- `Handler._serve_illustration_image()` (`companion/app.py`) now serves the normalized bytes instead of the raw file, with the existing validate-then-join membership test kept strictly first and a new defensive wrapper so any normalization failure joins the same 404 branch as a missing file, never a 500.
- `companion/pages/airlines_page.py`'s `<img>` tags now carry explicit `width="900" height="263"` (imported from `illustration_normalize`'s module constants), and `companion/static/style.css`'s `.airline-card__image` reserves the matching `aspect-ratio: 900 / 263` box with `object-fit: contain`.
- `companion/test_status_pages.py` grew from 106 to 112 checks: 4 covering the normalization helper directly (identical output dimensions across all 43 vendored files, 1px-centred and unclipped painted content, the None-bbox fallback via a synthetic fixture, and a scan proving no module under `companion/` redefines the alpha threshold), plus 2 covering the route wiring and card markup (real-running-service HTTP round trip proving the served bytes differ from raw and decode to the target size and that an unknown key still 404s, and an in-process render() check that every card's `<img>` carries the matching intrinsic dimensions).

## Task Commits

Each `type="auto"` task was committed atomically:

1. **Task 1: Shared illustration-normalization helper** - `3b6323f` (feat)
2. **Task 2: Serve normalized images and stabilize the gallery card** - `ee25db7` (feat)

**Plan metadata:** not yet committed — the orchestrator handles the docs commit after this SUMMARY lands.

## Files Created/Modified

- `companion/illustration_normalize.py` (new) - shared opaque-bbox normalization helper, imports `server.plane.render`'s bbox/threshold logic
- `companion/app.py` - `_serve_illustration_image()` now serves normalized bytes with a malformed-asset 404 fallback
- `companion/pages/airlines_page.py` - `<img>` tags carry explicit width/height; module docstring updated to describe the new route behavior
- `companion/static/style.css` - `.airline-card__image` reserves the normalized aspect-ratio box, `object-fit: contain`
- `companion/test_status_pages.py` - 6 new checks (106 → 112), `EXPECTED_CHECK_COUNT` updated; Pillow added to the harness's own dependency footnote

## Decisions Made

- **Target box: 900x263px (3.4221:1), derived at the measured median.** Measured live across all 43 vendored files (2026-09-02) via `server.plane.render._opaque_bbox()`: painted aspect ratios span 2.97:1 (`chalair-aviation.png`) to 4.98:1 (`amelia-embraer.png`), median 3.42:1. Because every crop is scaled to fit inside the target box (never crop-to-fill), the target ratio choice can never cause clipping — it only decides how much transparent letterbox space each file's card carries. A target near the widest ratio would letterbox every narrower file with dead horizontal space on both sides; the median instead spreads that dead space evenly across the whole distribution. Documented as a module-level constant with its derivation in `companion/illustration_normalize.py`'s own comment.
- **Resize the whole source image first, crop to the re-measured bbox second — not the reverse.** The first implementation cropped to the opaque bbox at full resolution, then resized that crop. This broke the "painted content centred within 1px" done-criterion on `air-europa.png` (measured 1.5px off) and likely others: cropping tight to the bbox before a LANCZOS resize starves the resample of surrounding context exactly at the painted edge, asymmetrically shrinking the re-measured post-resize bbox by up to ~2px on one side. Reordering to resize-the-whole-image-first (mirroring `panel_render._resize_illustration()`'s own shape exactly) and only crop to the bbox after that resize eliminated the discrepancy: the crop-then-paste-then-remeasure round trip became lossless (no further resizing), leaving only the ≤0.5px/axis integer-division rounding of the centring offset. Verified: all 43 files now measure within 1px on both axes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a resize-order bug that broke the 1px-centring contract**
- **Found during:** Task 1 (writing the "centred within 1px" behaviour check against the real vendored files)
- **Issue:** The first implementation cropped to the opaque bbox at full resolution before resizing, which is what the plan's `<action>` text literally describes ("open as RGBA, compute the opaque bbox, crop to it ... scale the crop to fit inside a module-level target box"). Running the new test against all 43 real files caught `air-europa.png` measuring 1.5px off-centre — LANCZOS resampling of a tightly pre-cropped image loses edge context asymmetrically.
- **Fix:** Reordered to resize the whole source image first (matching `panel_render._resize_illustration()`'s own shape), then re-measure/crop the opaque bbox on the resized image, then paste (a lossless crop+paste, no further resizing).
- **Files modified:** `companion/illustration_normalize.py`
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` — all 43 files now measure within 1px on both axes; full suite green.
- **Committed in:** `3b6323f` (Task 1 commit — the fix landed before the task's own commit, so no separate fix commit was needed)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix changes *how* the crop/resize/threshold pipeline is ordered internally; it does not change the module's public contract (`normalized_png_bytes(path)` / `cached_normalized_png_bytes(path)`, the 900x263 target size, or the import-not-reimplement discipline the plan required). No scope creep.

## Issues Encountered

None beyond the resize-order bug documented above (handled as a Rule 1 auto-fix during Task 1, before that task's commit).

## Checkpoint Pending

The plan's third task is `type="checkpoint:human-verify" gate="blocking"` and has **not** been resolved — this execution stopped there per the "pause at checkpoints" contract. It requires the developer's own explicit sign-off (resume-signal: `"approved"`, or a description of which cards still look off), and its verification steps explicitly ask for a real-device phone check, which this execution environment has no tool to perform.

**What was verified in lieu of that sign-off, to reduce the remaining check to a quick visual confirmation:**

1. **Automated suite:** `server/.venv/bin/python3 companion/test_status_pages.py` → 112/112 pass. `server/.venv/bin/ruff check .` → clean. `./scripts/run-all-tests.sh` → full 16-harness suite `Result: PASS`, including the panel.bin digest check, which reported its expected non-Linux informational `NOTE` (pre-existing from the sibling plan 01, not touched by this plan) rather than a hard failure.
2. **`server/` untouched:** `git diff --stat server/` is empty on both task commits — plan 01's panel.bin digest is provably unaffected by this plan.
3. **Real running-service check** (`server/.venv/bin/python3 companion/app.py --state-dir <tmp> --port 8743`, logged in with a real session cookie):
   - `GET /airlines` → every `<img class="airline-card__image">` tag carries `width="900" height="263"`.
   - `GET /illustration/air-france.png` → 200, decodes to `(900, 263)` via Pillow (confirmed live, not just asserted from source).
   - `GET /illustration/not-a-real-key.png` → 404.
   - `GET /static/style.css` → the served stylesheet carries the new `.airline-card__image { aspect-ratio: 900 / 263; object-fit: contain; ... }` rule.
4. **Visual confirmation (rendered locally with Pillow, viewed directly):** a before/after contact sheet of the four files the plan's checkpoint names by name — `chalair-aviation` (2.97:1, narrowest), `amelia-embraer` (4.98:1, widest), `air-france` (near edge-to-edge, minimal padding), `lot-polish-airlines` (heavy padding on all sides) — showing each file's raw source next to its normalized output. All four now share the same optical size and centring; none are clipped. A second 8-card mock gallery grid (adding `easyjet`, `tunisair`, `air-caraibes-a350-1000`, `french-bee`) confirms the same consistency holds when several cards are viewed side by side, as the real CSS grid would present them.
   - **What this does not cover:** an actual browser render of the real `/airlines` page (no browser/screenshot tool was available in this execution environment — only Pillow-rendered mockups of the served image bytes and CSS rule), and any real mobile-device check at all. Both remain genuinely open for the developer.

**To resolve:** follow the plan's own `how-to-verify` steps (`./scripts/run-local-verify.sh`, open the Airlines tab, check the four named files plus a phone view for reflow), then reply `"approved"` or describe which cards still look off.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both `type="auto"` tasks are complete, committed, and independently verified (automated suite + real running-service HTTP checks + visual mockups); `server/` is untouched and plan 01's panel.bin digest is unaffected.
- Blocked only on the plan's own blocking human-verify checkpoint (visual sign-off, including a real-device phone check this environment cannot perform). No code changes are expected to be needed unless the developer finds a card that still looks off.

---
*Phase: quick-260902-req*
*Completed (auto tasks): 2026-09-02*

## Self-Check: PASSED

- FOUND: companion/illustration_normalize.py
- FOUND: 3b6323f (Task 1 commit)
- FOUND: ee25db7 (Task 2 commit)
- FOUND: .planning/quick/260902-req-fix-inconsistent-aircraft-centering-acro/260902-req-02-SUMMARY.md
