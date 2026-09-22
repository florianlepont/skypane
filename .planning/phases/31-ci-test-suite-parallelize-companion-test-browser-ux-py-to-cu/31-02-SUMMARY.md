---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
plan: 02
subsystem: testing
tags: [playwright, pytest-free-harness, ruff, docker, ci-parity, drawings]

requires:
  - phase: 31-01
    provides: "companion/test_browser_ux_helpers.py shared module, 31-BASELINE-CHECKS.txt pre-split transcript"
provides:
  - "companion/test_browser_ux_health_drawings.py — the 24-04/24-06/24-07/24-08 drawings series (11 checks) as its own standalone, independently-runnable harness"
  - "companion/test_browser_ux.py reduced to 85/85, EXPECTED_CHECK_COUNT changelog appended"
  - "Empirical confirmation of RESEARCH.md Assumption A3 (no hidden cross-check order dependency across the split)"
affects: [31-03, 31-04, 31-05]

tech-stack:
  added: []
  patterns:
    - "Verbatim block relocation (zero rewording, zero reindentation) preserving comment provenance"
    - "AST-derived import list (free-variable analysis against the finished file) instead of by-eye import guessing, to keep ruff F401-clean on the first pass"
    - "Three-way PASS-name-set comparison (baseline ∪ new ∪ reduced) as the authoritative verdict-preservation proof, run as a script rather than eyeballed diffs"
    - "Cross-architecture Docker verification (linux/amd64 via --platform, matching the real CI runner) as the correctness oracle, continuing 31-01's established recipe"

key-files:
  created:
    - companion/test_browser_ux_health_drawings.py
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "Widened the extraction boundary beyond RESEARCH.md's 9-check estimate to the full 11-check 24-04/24-06/24-07/24-08 series, because _band_harness() has two call sites (the 24-08 hero checks) outside RESEARCH.md's narrower range — cutting at RESEARCH.md's own boundary would have stranded the hero checks with a NameError."
  - "Dropped TEST_PASSWORD from the new file's import list despite the plan's own read_first hint naming it — AST analysis of the finished file showed zero references to it inside the moved block; importing it anyway would have been an unused-import ruff failure."

requirements-completed: [D-04, D-07]

coverage:
  - id: D1
    description: "companion/test_browser_ux_health_drawings.py created: the complete 24-04/24-06/24-07/24-08 drawings series (11 checks) moved verbatim, zero reindentation, into its own harness with its own main()/Harness()/two-gate skip preamble naming itself, EXPECTED_CHECK_COUNT=11 re-derived by running under linux/amd64 Docker (matching CI's ubuntu-latest runner)"
    requirement: "D-04"
    verification:
      - kind: automated_ui
        ref: "server/.venv/bin/python3 companion/test_browser_ux_health_drawings.py (Playwright, linux/amd64 Docker) → 11/11 PASS, 0 FAIL, exit 0"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check companion/test_browser_ux_health_drawings.py"
        status: pass
      - kind: other
        ref: "skip-path exercised via PLAYWRIGHT_BROWSERS_PATH pointed at an empty dir → SKIP line naming this file, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "companion/test_browser_ux.py reduced by deleting the exact moved span, 12 now-unused imports dropped (no promotion needed — every helper's only call site left with the block), EXPECTED_CHECK_COUNT changelog appended with 85, re-derived by running rather than subtracted on paper; 11 + 85 = 96 conserved"
    requirement: "D-04"
    verification:
      - kind: automated_ui
        ref: "server/.venv/bin/python3 companion/test_browser_ux.py (Playwright, linux/amd64 Docker) → 85/85 PASS, 0 FAIL, exit 0"
        status: pass
      - kind: unit
        ref: "python3 -c AST assertion: EXPECTED_CHECK_COUNT(test_browser_ux.py) + EXPECTED_CHECK_COUNT(test_browser_ux_health_drawings.py) == 96"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check . (whole repo)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Verdict-preservation empirically proven per RESEARCH.md Pitfall 2/Assumption A3: three-way PASS-name-set comparison against 31-BASELINE-CHECKS.txt (base == new ∪ reduced, new ∩ reduced == ∅, zero FAIL lines anywhere), plus both files run concurrently in the same container to confirm no ephemeral-port/temp-dir collision"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "python3 compare.py (three-way PASS-name-set diff against 31-BASELINE-CHECKS.txt) → PITFALL-2-CLEAN: 96 == 11 + 85, names conserved, all PASS, concurrent run green"
        status: pass
      - kind: other
        ref: "concurrent docker exec of both files in the same linux/amd64 container → concurrent-exits=0/0"
        status: pass
    human_judgment: false

duration: ~1h10m
completed: 2026-09-22
status: complete
---

# Phase 31 Plan 02: Drawings Scenario Group Extraction Summary

**Moved the complete 24-04/24-06/24-07/24-08 SVG-drawings scenario group (11 checks — battery ring, battery chart, day band, regularity grid, Home hero) out of `companion/test_browser_ux.py` into a new standalone `companion/test_browser_ux_health_drawings.py` harness, with an empirical three-way transcript comparison proving every verdict is unchanged.**

## Performance

- **Duration:** ~1h10m (most of it spent provisioning and re-provisioning a `linux/amd64` Docker container — venv, requirements, Chromium-with-deps — and waiting out the QEMU-emulated wall time of the 85-check parent harness, twice)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed
- **Files modified:** 2 (1 created harness, 1 reduced harness)

## Accomplishments

- Created `companion/test_browser_ux_health_drawings.py`: the 11-check drawings series moved byte-for-byte (zero reindentation) into its own `main()`, with its own two-gate Playwright skip preamble naming this file, its own `Harness()`/`seed_state_dir()` trio, and an import list derived from an AST free-variable scan of the finished file rather than guessed by eye — first `ruff check` pass was clean. Corrected RESEARCH.md's boundary estimate live: the real group is 11 checks, not 9, because `_band_harness()` has two call sites inside the 24-08 hero checks that RESEARCH.md's narrower range would have stranded.
- Reduced `companion/test_browser_ux.py` by deleting the exact 1,962-line span now living in the new file, dropped the 12 imports whose only call sites left with it, and appended a new `EXPECTED_CHECK_COUNT = 85` changelog entry following the file's own append-only convention — re-derived by running the reduced file, not by subtracting 11 from 96 on paper.
- Proved the split verdict-preserving: a three-way comparison of PASS check-name sets (the pre-split 96-name baseline vs. the new file's 11 vs. the reduced file's 85) showed exact set equality with zero overlap and zero FAIL lines anywhere, and both files were run concurrently in the same container to confirm no ephemeral-port or temp-dir collision under real contention.

## Task Commits

1. **Task 1: Create companion/test_browser_ux_health_drawings.py with the 11 drawings checks moved verbatim** - `bda94ff` (feat)
2. **Task 2: Remove the 11 moved checks from companion/test_browser_ux.py and re-derive its counter by running** - `60c51fc` (refactor)
3. **Task 3: Prove no moved check changed verdict** - (this commit)

**Plan metadata:** (final commit)

## Files Created/Modified

- `companion/test_browser_ux_health_drawings.py` - New standalone harness: the 24-04/24-06/24-07/24-08 drawings series (battery ring, battery chart, day band, regularity grid, Home hero), 11/11 checks, `EXPECTED_CHECK_COUNT = 11`
- `companion/test_browser_ux.py` - The moved span deleted (1,962 lines), 12 now-unused imports dropped, a new `EXPECTED_CHECK_COUNT = 85` changelog entry appended

## Decisions Made

- **Widened the extraction boundary to 11 checks, correcting RESEARCH.md's 9-check estimate.** `_band_harness()` is defined inside the day-band block and called from four sites — two of RESEARCH.md's own 9-check range, and two inside the 24-08 hero checks RESEARCH.md left behind. Cutting at RESEARCH.md's own line would have stranded the hero checks with a `NameError`. Verified live against the file (not just reasoned about): the widened 11-check block has exactly zero references to its own constants/helpers (`_band_harness`, `_grid_harness`, `BAND_SEED_PARIS_HOURS`, `RING_PAGES`, `RING_VALUE`, `RING_TRACK`, `_band_rgba`) outside itself.
- **Derived the import list from AST free-variable analysis, not by eye — and it caught a stale hint.** The plan's own `read_first` guidance suggested importing `TEST_PASSWORD` "at minimum," but a mechanical scan of the finished file's free names (Load-context `Name` nodes minus Store-context ones, minus builtins) found zero references to it inside the moved block. Importing it anyway would have failed `ruff`'s F401 on the very first check. The same analysis surfaced that `home_page` is imported locally inside two of the moved check bodies (not at module level) and therefore needs no module-level import either.
- **Used a persistent `linux/amd64` Docker container across all three tasks rather than a fresh container per task.** Provisioning (venv + requirements + `playwright install --with-deps chromium`) takes several minutes under QEMU emulation on this arm64 host; reusing one running container for tasks 1-3 avoided paying that cost three times, continuing 31-01's own established cross-architecture verification recipe.

## Deviations from Plan

None - plan executed exactly as written. The 9→11 boundary correction was explicitly called for by the plan's own objective text (not a deviation from it), and the `TEST_PASSWORD` import omission followed the plan's own explicit instruction to derive the import list from the AST "rather than by eye."

## Issues Encountered

- **Local arm64 Chromium is not a valid correctness oracle for this file (inherited finding from 31-01, re-confirmed here).** This host is Apple Silicon (arm64); 31-01 already root-caused that native/emulated arm64 Chromium disagrees with CI's `ubuntu-latest` (amd64) runner on unrelated environmental grounds. Continued 31-01's `--platform linux/amd64` Docker recipe rather than trusting a native run's PASS/FAIL outcome. No test or application code was touched to work around this — it is a verification-environment choice only, as it was in 31-01.
- **The compound bash timeout auto-backgrounded the full 85-check parent run three times** (task 2's verification, task 3's concurrent run, task 3's timing run), each taking 4.5-8.5 minutes under QEMU emulation. Waited each out via a host-PID `kill -0` poll loop rather than a fixed sleep, since the container's `python:3.12-slim` base has neither `ps` nor `pgrep` installed (first attempt at a `pgrep`-based wait loop returned a false "finished" immediately because `pgrep` itself was missing, not because the process had exited).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can follow the same pattern (verbatim block relocation, AST-derived imports, three-way transcript comparison) for its own extraction target, importing shared helpers from `companion.test_browser_ux_helpers` exactly as this plan did.
- The 96-check total is conserved and empirically proven verdict-preserving across the split: `companion/test_browser_ux.py` at 85/85 and `companion/test_browser_ux_health_drawings.py` at 11/11, with RESEARCH.md's highest-risk assumption (A3 — no hidden cross-check order dependency) settled PASS by evidence, not argument.
- Both files were confirmed to run concurrently without a port or temp-dir collision, which is the exact concurrency plan 04's worker-pool registration will create — no port-allocation surprises expected there.
- Standalone wall times recorded below for plan 04's own before/after accounting, measured under this host's `linux/amd64` Docker emulation (not directly comparable to 31-TIMINGS.md's native `JOBS=4` numbers, but internally consistent — solo vs. concurrent shows negligible contention overhead, itself evidence supporting the concurrency-safety finding):
  - `companion/test_browser_ux_health_drawings.py`: solo 48.6s, concurrent-with-parent 54.0s
  - `companion/test_browser_ux.py` (reduced, 85 checks): solo 8m27.4s, concurrent-with-new-file 8m33.7s
- No open blockers.

## RESEARCH.md Pitfall 2 / Assumption A3 — Empirical Verdict

**PASS.** RESEARCH.md's Assumption A3 ("no check outside the two recommended groups reads or depends on state left behind by a check inside them") holds for this extraction.

Evidence:
- Three-way PASS-name-set comparison: `set(31-BASELINE-CHECKS.txt's 96 PASS names) == set(new file's 11 PASS names) | set(reduced file's 85 PASS names)`, with the two post-split sets disjoint. Printed `PITFALL-2-CLEAN: 96 == 11 + 85, names conserved, all PASS, concurrent run green`.
- Zero `FAIL ` lines in either post-split file's output.
- Both files run concurrently in the same container exited 0/0 — no ephemeral-port or temp-dir collision under real contention (`Harness._pick_free_port()`'s `bind(("127.0.0.1", 0))` argument confirmed empirically, not just reasoned about).

### The 11 moved check names (verbatim, matched by full text against the baseline)

1. the battery ring's value arc resolves to a real theme token on BOTH pages in BOTH themes — never the SVG default fill or stroke, never the same paint as its own track, and never the same value in light and dark (CFG-40, 24-02's theme and computed-paint helpers)
2. the battery ring's viewBox contains its own STROKED geometry on both pages — each arc's browser-reported bounding box, expanded by half its resolved stroke width on every side, lies inside the box the emitter declared (CFG-45, contract rule 5)
3. at the 360px floor the ring costs nothing it must not: neither page's body scrolls sideways, Home's Battery tile stays exactly as tall as the Frame tile beside it (measured against a neighbour, because 'all three equal' is false at 360px and vacuous at 1280px), and both rings still render — and still paint a dark-mode token — with scripts blocked through `_no_js_page()` (CFG-45, D-09)
4. the battery chart's area, line, mark and threshold each resolve to a real theme token in BOTH themes — never the SVG default, the area/line/mark sharing one currentColor ink while the threshold deliberately does not, the legend's swatch equal to the drawn threshold, and the area's COMPOSITE over the card clearing a 1.20:1 floor so it is visible and not merely painted (CFG-41/CFG-45, 24-05-PLAN.md Task 3)
5. at the 360px floor the battery chart's additions cost nothing they must not: the page body does not scroll sideways in EITHER language, the threshold's legend overlaps none of the four axis labels and stays inside its card at the 10px micro-label tier, its swatch measures a real 12x1 box (which an inline `<span>` could not), the canvas keeps its share of the grid rather than being squeezed by a legend that claimed the Y-label column, the mark's edge-hung ink stays inside the card, and the area, mark, threshold and legend all still render — and still paint dark-mode tokens — with scripts blocked (CFG-45, D-09, 24-05-PLAN.md Task 3)
6. the day band's frame, shaded span and check-in marks each resolve to a real theme token in BOTH themes and never the SVG default, all three move when the theme does, the span clears a 1.15:1 floor against the band's own surface (they are one token at two strengths, so 'not the default' says nothing about whether they can be told apart), the frame clears 1.05:1 against its card so an empty day is not literally nothing, and a mark crossing the span — which is where a night's check-ins land, and the fixture is asserted to produce one — clears 4.5:1 over it (CFG-42, 24-06-PLAN.md Task 3)
7. at the 360px floor the day band is a real drawing in BOTH languages: the page body does not scroll sideways, every mark renders at least the 2px `draw.py` declares (a mark emitted in absolute pixels into a CSS-sized canvas has nothing in the markup guaranteeing it survives to paint), every mark and span stays inside the canvas, the minimum mark spacing re-derived from the canvas's MEASURED width still buys the 4px its comment claims, the three hour labels sit at the band's own left edge, midpoint and right edge, the canvas is the same width in both languages, and the whole band plus its two shaded spans still render and still paint dark-mode tokens with scripts blocked (CFG-42, D-09, 24-06-PLAN.md Task 3)
8. all FOUR of the regularity grid's cell states paint a real theme token in BOTH themes and never the SVG default, all four move when the theme does, each key swatch composites to exactly the colour of the cell it explains (one `color` declaration, an SVG fill and an HTML background), the three verdicts clear WCAG AA's 3:1 non-text bar against their card while the no-observation state clears its own lower, deliberate 1.25:1 floor, and every one of the six pairs stays past the app's own `MIN_SIGNAL_PERCEPTUAL_DISTANCE` — four states that read as three in dark mode is a defect no source scan can see (CFG-43, CFG-45, 24-07-PLAN.md Task 3)
9. the regularity grid is a real drawing at the 360px floor in BOTH languages: the page body does not scroll sideways, a Health card's content box still measures the width `draw.CARD_DRAWING_WIDTH_PX` records, all 30 cells render as one square at or above the 24px floor the bucket count is supposed to come down for, every cell inks inside the viewBox, the wrapper is exactly as wide as the canvas so the two date labels sit on the first and last columns, the four key swatches keep their declared 12px box inside the card, the geometry is identical in both languages, the whole grid still paints dark-mode tokens with scripts blocked, and at 1280px and 320px the wrapper and the canvas still agree with no page overflow and no stretched cell (CFG-43, CFG-45, D-09, T-24-07-D, 24-07-PLAN.md Task 3)
10. at the 360px floor D4's hero STACKS rather than shrinks, in both languages: its three parts share one column with exactly the 16px one `--space-md` declares between them and 24px below the group (bound tighter than it is separated, asserted as equalities because a 40px gap is what parts keeping their own margins render and passes every 'at least'), the battery ring still renders at the 36px `home_page.BATTERY_RING_SIZE` declares and the day band's canvas at the 278px `draw.py`'s mark spacing was derived from, all five seeded check-ins still draw, the page body does not scroll sideways, the hero is the same width in both languages, and the ring and the band paint real inverting tokens in BOTH themes through selectors scoped INSIDE the hero (CFG-44, CFG-45, 24-08-PLAN.md Task 3)
11. the hero's grouping is the same composition at 360px and at 1280px — one column with the same 16px inside and 24px below at both, no page overflow at either — while the three status tiles inside it stack at the floor and share one row on the desktop, so the stack is a FLOOR behaviour rather than the only one; the band gets MORE room as the viewport grows, never less; every one of Home's declared refresh-swap selectors still matches a real element through the browser's own selector engine (a stale one stops the live refresh silently); and with scripts blocked the hero's children keep their lefts, widths and gaps and both drawings keep their boxes (CFG-44, CFG-45, D-09, 24-08-PLAN.md Task 3)

---
*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Completed: 2026-09-22*
