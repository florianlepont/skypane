---
phase: quick-260902-dng
plan: 260902-dng
subsystem: companion-ui

tags: [companion, health-page, svg, chart, css, design-system, harness]

requires:
  - phase: 06.6.1
    provides: "battery_sparkline_svg()'s canvas constants and the .battery-trend-section svg:not(.icon) CSS override this task resizes/rebounds"
  - phase: 260901-uzi
    provides: "Finding 5's diagnosis (opaque sticky background starting at the glyph tops) — this task ships candidate (a), the fix that quick task declined to apply blind"
  - phase: 260901-uzi
    provides: "Finding 4's demotion of .page-section--nested > h2 to the Emphasis role — the change whose 24-hour-old side effect Task 3 investigates and resolves"
provides:
  - "battery_sparkline_svg() emits a 366x120 viewBox (was 334x74) with matching width/height attributes and an explicit preserveAspectRatio=\"xMinYMid meet\""
  - ".battery-trend-section svg:not(.icon) declares a fixed 120px height (was height: auto) — the CSS/SVG height equality that bounds the chart's real scale factor at min(containerWidth/viewBoxWidth, 1), never above 1.00, at every real container width from 293px to 1278px"
  - ".data-table th declares padding: 10px var(--space-md) (was 0 var(--space-md) 10px) — real top padding above every table header's glyphs in all four data-table instances (History, Health readings, Resolution statistics, unresolved-prefix registry)"
  - ".stat-tile__caption declares font-weight: var(--weight-semibold) (was inherited regular) — resolves the recurring stat-tile/nested-card type-hierarchy complaint by matching the caption's weight to its structural peer, the nested card title, without introducing a fifth size"
  - "Three new harness checks in companion/test_status_pages.py, each mutation-tested: the chart's cross-file scale-bound equality and coordinate-inside-viewBox guarantee; the table-header padding symmetry/non-zero guarantee; the four-text-role type-scale coherence guarantee"
affects: [companion-ui-implementation, health-page-visual-defects]

tech-stack:
  added: []
  patterns:
    - "Bounding an SVG's responsive scale at 1.0 by pairing a fixed CSS height equal to the SVG's own emitted height attribute, rather than height: auto — turns an unbounded containerWidth/viewBoxWidth scale into min(containerWidth/viewBoxWidth, 1), a pattern generalizable to any other fixed-viewBox inline SVG this app ever adds"
    - "Deriving a responsive container-width range algebraically from the CSS cascade (each padding/gap/max-width layer subtracted in turn) rather than trusting a single live-measured number, so a harness check can assert a scale bound across the whole real range instead of one observed width"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "Bug 1's fix bounds the CSS-declared height, not the viewBox's own aspect ratio: `.battery-trend-section svg:not(.icon)` keeps `width: 100%` but replaces `height: auto` with a fixed `120px` equal to the SVG's own emitted `height` attribute. This makes the effective scale `min(containerWidth/viewBoxWidth, cssHeight/viewBoxHeight)`, and with cssHeight == the SVG's height attribute, the second term is always exactly 1.0, capping the whole expression at 1.0 by construction at every container width, not just the one width (846px) the developer happened to measure."
  - "The validated Merged Health Sketch's own preserveAspectRatio=\"none\" + fixed-height strategy was evaluated with real numbers and rejected in writing (in the CSS comment): it holds the vertical scale at 1.0 but lets the horizontal scale run independently at containerWidth/viewBoxWidth, which is 0.33x at a 375px viewport against a 900-wide viewBox — squashing axis-label glyphs to a third width and the D-02 r=8 keyboard hit targets to ~2.6px slivers, breaking the mobile tap-target floor. Uniform scaling with a 1.0 cap (this task's approach) avoids that distortion at every width."
  - "The canvas constants were resized alongside the CSS fix, not left alone: _AXIS_LEFT_GUTTER 34->44, plot_width 300->322, plot_height 60->106, giving a 366x120 viewBox. This keeps the 1.0-capped chart legible (rather than shrunk to a stale 334x74 box) while staying within the 366px ceiling the narrowest real container (293px) needs to stay at >= 0.80 scale. The gutter grew because 34 user units under-measured a \"4200 mV\"-shaped 10px label (7 chars * ~6px + 2px inset = 44) — an error invisible while the whole chart was blown up 2.53x and visible for the first time at true 1:1."
  - "Bug 2's fix mirrors the existing bottom padding value (10px) rather than reaching for a --space-* token, keeping the header's relationship to its own border-bottom hairline byte-identical and avoiding an unrelated value change on four tables at once as a rider on an unrelated fix."
  - "Task 3's verdict is hypothesis (ii), not (i): the tile value/nested-title collision (i) is real (both 16px semibold now) but is not this caption's problem — .stat-tile__value's own weight is Finding 4's deliberate Emphasis-role placement and stays untouched. The actual defect is that the tile caption and the nested card title are both this file's 'name of a card' role, and they disagreed on weight (14 regular vs 16 semibold) despite being structural peers. Weight, not size, was the only D-09-compliant lever — Option A (promote the caption to semibold, keep 14px/serif) was chosen over Option B (colour/letter-spacing, treats only the caption's own weakness, leaves the peer disagreement unresolved) and Option C (touch the nested title instead, which Finding 4 already deliberately set)."
  - "Corrects a factual overstatement in PLAN.md's own blast-radius estimate for Task 3: the plan states layout.stat_tile() has '11 call sites — 10 in health_page.py and 1 in history_page.py'. A repo-wide grep during execution found exactly 4 real call sites, all in health_page.py (Device, Pipeline, Corroboration, Resolution-rate) — 0 in history_page.py, which currently renders no stat tiles at all. This does not change the fix (a CSS class rule, unconditionally applied wherever .stat-tile__caption is rendered), only the accuracy of the recorded blast radius."

requirements-completed: [QUICK-260902-dng]

coverage:
  - id: chart-scale-bounded
    description: "The battery-trend chart's effective SVG scale factor is bounded at [0.80, 1.00] across the real 293-1278px container-width range, by construction, provable from source"
    requirement: QUICK-260902-dng
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_sparkline_scale_bounded_at_one_across_real_container_widths (new) — viewBox/width/height/preserveAspectRatio parsed from a real battery_sparkline_svg() return; CSS declared height parsed from style.css and asserted equal to the SVG height attribute; min(cW/vbW, 1) computed at 5 derived widths, asserted in [0.80, 1.00]; every emitted coordinate asserted inside the viewBox"
        status: pass
      - kind: manual
        ref: "server/.venv/bin/python3 -c '...' inline verification script from PLAN.md's own <verify> block"
        status: pass
    human_judgment: true
    rationale: "A harness check proves the arithmetic is internally consistent; only a real browser's getBoundingClientRect() proves the arithmetic describes the real rendered box. See 'Pixel-Level Items Outstanding' below."
  - id: table-header-padding
    description: "Every data-table header's glyph ascenders have real opaque background above them in every browser, regardless of font-ascent metrics"
    requirement: QUICK-260902-dng
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_data_table_th_has_symmetric_nonzero_padding (new) — parses .data-table th's padding shorthand, asserts non-zero top and (by two-value-shorthand construction) top/bottom symmetry"
        status: pass
      - kind: unit
        ref: "companion/test_view_pages.py (full suite, 43/43) — History's data-table renders through the same shared rule"
        status: pass
    human_judgment: true
    rationale: "The defect was WebKit-specific (font-ascent-metric-dependent) and only reproduced in the developer's real Safari — a Chromium-based measurement tool did not show it. Real Safari confirmation is the only way to close this out visually."
  - id: type-hierarchy-verdict
    description: "A written, source-grounded verdict on the stat-tile-caption/nested-card-title type-hierarchy question, with a shipped CSS change (not a third deferral)"
    requirement: QUICK-260902-dng
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_stat_tile_caption_weight_and_four_role_type_scale_hold (new) — pins .stat-tile__caption's new declaration and the four text roles' relative size/weight ordering as a set, against real token values"
        status: pass
    human_judgment: true
    rationale: "Whether the region now reads with a clear hierarchy is a human judgment (see item 7 in 'Pixel-Level Items Outstanding'), not a measurement the harness can make."

duration: ~55min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-dng: Fix 2 Confirmed-Severe Real Bugs on the Health Page, Plus a Real Design-Question Resolution Summary

**Bounds the battery-trend chart's runaway 2.53x scale-up at 1.0 by construction (fixed CSS height equal to the SVG's own emitted height, paired with a resized 366x120 viewBox), fixes the WebKit-reproducing table-header clipping defect with real top padding, and resolves — for real, not a third deferral — the recurring stat-tile-caption/nested-card-title hierarchy complaint by promoting the caption to the same weight tier as its structural peer.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Files modified:** 3 (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`)

## Accomplishments

- **Task 1 — the battery-trend chart's scale bound (BUG 1):** `.battery-trend-section svg:not(.icon)` replaced `height: auto` with a fixed `height: 120px`, equal to `battery_sparkline_svg()`'s own emitted `height` attribute — the equality that makes the effective scale `min(containerWidth/viewBoxWidth, 1)`, capped at 1.0 by construction at every container width instead of the previous unbounded `containerWidth/viewBoxWidth` (measured live at 2.53x, 846px against a 334-wide viewBox). The canvas constants grew alongside it (`_AXIS_LEFT_GUTTER` 34→44, `plot_width` 300→322, `plot_height` 60→106, giving a 366x120 viewBox) so the 1.0-capped chart stays legible rather than shrunk, while the narrowest real container (293px, derived from the CSS cascade, not just the observed 846px) still renders at ≥ 0.80 scale. An explicit `preserveAspectRatio="xMinYMid meet"` left-aligns the chart within its now-fixed-height container at wide viewports. `companion/static/battery-trend.js` is byte-for-byte unmodified, as required — confirmed by re-reading it in full: it reads `data-mv`/`data-ts`/`data-when` via `getAttribute()` and recomputes no geometry.
- **Task 2 — real top padding on table headers (BUG 2, closes 260901-uzi Finding 5 candidate (a)):** `.data-table th`'s `padding: 0 var(--space-md) 10px` became `padding: 10px var(--space-md)`. The real mechanism, named in the rule's own comment: sticky positioning never clips text — `.data-table-wrap th`'s opaque background paints over this rule's own padding box, and with zero top padding that opaque box began exactly at the glyph tops, so a scrolling row reached the ascenders before any background covered them. Whether that reads as visible clipping depends on a font's ascent metric inside its own line box, which genuinely differs between WebKit and Blink — exactly why 260901-uzi's Finding 5 reproduced in the developer's real Safari and not in a Chromium-based tool, and why that task declined to fix it blind. Real top padding fixes this in every engine. The blast radius (History, Health readings, Resolution statistics, unresolved-prefix registry — all four re-space together by 10px of header height) is intended, recorded in the comment, and confirmed correct by running the full `test_view_pages.py` suite (43/43, unaffected).
- **Task 3 — the stat-tile-caption weight resolution:** `.stat-tile__caption` gained `font-weight: var(--weight-semibold)`, keeping its 14px size and named serif exception unchanged. See "Task 3 Verdict — The Type-Hierarchy Question" below for the full source-grounded reasoning; in short, this closes hypothesis (ii) (the tile caption and the nested card title are structural peers — both this file's "name of a card" role — but disagreed on weight) without touching `.stat-tile__value`'s own weight, which stays Finding 4's deliberate placement, and without introducing a fifth size (D-09's four-size scale — 14/16/20/30 — stays intact).
- **Harness:** 3 new checks added to `companion/test_status_pages.py` (`EXPECTED_CHECK_COUNT` 89 → 92), one per task, each independently mutation-tested (a single deliberate defect introduced, confirmed to fail exactly that one check and no others, then restored) before being committed. All other harnesses (`test_view_pages.py` 43/43, `test_companion_app.py` 105/105, `test_config_page.py` 61/61, `test_contrast_check.py` 36/36) run unmodified and green. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch — with no coverage-gate shortfall.
- **Live-HTTP smoke test (optional, per PLAN.md's verification section):** started a real `companion/app.py` subprocess against a seeded state directory, signed in over HTTP, and fetched the real `/health` and `/static/style.css` response bodies. Confirmed all seven expected literal values are actually served: `viewBox="0 0 366 120"`, `preserveAspectRatio="xMinYMid meet"`, `height="120"` on the SVG; `height: 120px;` and no `height: auto` on `.battery-trend-section svg:not(.icon)` in the served stylesheet; `padding: 10px var(--space-md);` on `.data-table th`; and `font-weight: var(--weight-semibold)` on `.stat-tile__caption`. This is not a substitute for a real-browser rendering pass (see below) but does rule out any typo or caching gap between the source-level harness checks and what the server actually serves.

## Task Commits

1. **Task 1:** `af875d5` — `fix(quick-260902-dng): bound the battery-trend chart at 1:1 scale` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`
2. **Task 2:** `c9711c7` — `fix(quick-260902-dng): give table headers real top padding` — `companion/static/style.css`, `companion/test_status_pages.py`
3. **Task 3:** `ed8244e` — `fix(quick-260902-dng): promote stat-tile captions to card-title weight` — `companion/static/style.css`, `companion/test_status_pages.py`

## Files Created/Modified

- `companion/pages/health_page.py` — `_AXIS_LEFT_GUTTER` 34→44 (with the "4200 mV"-label under-measure explained), `plot_width`/`plot_height` 300/60→322/106, the module-level canvas-constant comment rewritten to record the 260902-dng resize and point at style.css's own derivation comment, `preserveAspectRatio="xMinYMid meet"` added to the emitted `<svg>` tag
- `companion/static/style.css` — `.battery-trend-section svg:not(.icon)` height rewritten to a fixed `120px` with a long comment recording the 2.53x defect, the full 293-1278px container-width derivation, the `min(cW/vbW, 1)` bound, and the `preserveAspectRatio="none"` rejection; `.data-table th`'s padding rewritten to `10px var(--space-md)` with the opaque-background mechanism, the four-table blast radius, and the Finding-5-candidate-(a)/(b) split recorded; `.stat-tile__caption` gained `font-weight: var(--weight-semibold)` with the full hypothesis-(i)-vs-(ii) reasoning and the Option A/B/C comparison recorded
- `companion/test_status_pages.py` — 3 new checks (one per task), each mutation-tested; `EXPECTED_CHECK_COUNT` 89 → 92 with the running arithmetic comment extended at each step

## Derived Container-Width Table and Resulting Scale Factors

Derived algebraically from this file's own CSS chain (not from the single 846px measurement alone), reproduced in both `style.css`'s rule comment and the new harness check's own comment so the two never silently diverge:

- **≥ 960px:** `.dashboard-shell` is `240px minmax(0, 1fr)` with a `--space-xl` (32px) column-gap → main column = `viewport - 272`. `.dashboard-main` caps at `min(1440px, 100%)` and adds `--space-2xl`/`--space-3xl` (48/64px) padding → content = `min(1440, column) - 128`. `.battery-trend-section`'s own `--space-md` (16px) padding plus its 1px border on each side subtracts 34 more → SVG container = `content - 34`.
- **< 960px:** `.page-content`'s `--space-xl`/`--space-lg` (32/24px) padding → content = `viewport - 48` → SVG container = `viewport - 82`.

| Viewport | Container width | scale = min(cW / 366, 1) |
|---|---|---|
| 375px | **293px** (narrowest real container) | **0.8005** |
| 959px | 877px | 1.0000 |
| 960px | 526px | 1.0000 |
| 1280px | **846px** (matches the live 846px measurement exactly — the proof the derivation is right) | 1.0000 |
| ≥ 1568px | **1278px** (capped by the 1440px max-width) | 1.0000 |

Real range: **293px to 1278px**, a 4.36x spread, with scale bounded to **[0.8005, 1.0000]** across the whole range — never above 1.00 at any width, present or future, and never below the 0.80 floor that protects today's correctly-measured 375px rendering.

## Canvas Constants Chosen and Why

| Constant | Old | New | Criterion satisfied |
|---|---|---|---|
| `_AXIS_LEFT_GUTTER` | 34 | 44 | Corrects a genuine under-measure for a "4200 mV"-shaped 10px label (7 chars × ~6px/char + 2px inset ≈ 44), invisible while the chart rendered 2.53x oversized |
| `plot_width` | 300 | 322 | Combined with the gutter, gives `viewBoxW = 366` — at the ceiling that still keeps the narrowest real container (293px) at ≥ 0.80 scale (293/366 = 0.8005) |
| `plot_height` | 60 | 106 | Combined with `_AXIS_BOTTOM_STRIP` (unchanged, 14), gives `viewBoxH = 120` — the value the CSS's fixed height must equal; kept the rendered chart height comfortably under ~160px |
| `padding`, `_AXIS_BOTTOM_STRIP` | 4, 14 | unchanged | No criterion required changing these |

The chosen 366-wide viewBox lands exactly at the 0.80 floor (293/366 = 0.8005, not comfortably above it) — a deliberate choice to maximize the chart's on-screen size at every wider viewport rather than leaving headroom nobody asked for; if a future accessibility audit wants more margin above 0.80 at 375px, the lever is `plot_width`/`_AXIS_LEFT_GUTTER` (shrinking `viewBoxW`), not the CSS height.

## The `preserveAspectRatio="none"` Rejection

The validated Merged Health Sketch pairs `preserveAspectRatio="none"` with a fixed CSS height, which does hold the **vertical** scale at exactly 1.0 — but it lets the **horizontal** scale run independently at `containerWidth / viewBoxWidth`. Evaluated against this file's real 293-1278px container range against the sketch's own 900-wide viewBox: at a 375px viewport, horizontal scale = 293/900 = **0.33x**. At 0.33x:
- The four axis labels' glyphs would render at roughly a third of their natural width — illegible, overlapping.
- The D-02 r=8 keyboard hit targets would render as ~2.6px-wide slivers, breaking the tap-target floor phase 06.5 validated.

The sketch's 900-wide viewBox is only ever near 1:1 around a 900px container — the one width it was ever viewed at. This task's approach (uniform scaling, `preserveAspectRatio="xMinYMid meet"`, a 1.0-capped scale via the CSS-height/SVG-height equality) keeps glyphs and hit targets undistorted at every width instead, at the cost of the chart reading as narrower than the sketch's own vision at desktop widths (see "Pixel-Level Items Outstanding" item 3 below).

## Task 3 Verdict — The Type-Hierarchy Question

**Step 1 — the four roles, confirmed from source (not assumed):**

| Role | Selector | Size | Weight | Family |
|---|---|---|---|---|
| Section heading | `h2.text-heading` | 20px (`--font-heading-size`) | regular (400) | serif |
| Stat-tile caption | `p.text-label.stat-tile__caption` | 14px (`--font-label-size`, inherited from `.text-label`) | **semibold (600)** — this task's change (was regular) | serif (named exception) |
| Stat-tile value | `p.stat-tile__value` | 16px (`--font-body-size`) | semibold (600) | sans (`--font-ui`, inherited from `body`) |
| Nested card title | `.page-section--nested > h2` | 16px (`--font-body-size`) | semibold (600) | serif (inherited from the `h1,h2,h3,legend,.text-heading` rule; the demotion rule sets no family of its own) |

**Step 2 — judging (i) vs (ii):**

- **(i) — tile value vs. nested card title, identical in size AND weight, differing only in family:** confirmed TRUE from source (both 16px/semibold; 260901-uzi Finding 4's demotion made the nested title semibold, not just 16px). But this collision is not the stat-tile caption's problem to fix — `.stat-tile__value`'s weight is Finding 4's own deliberate Emphasis-role placement, made to fix the *previous* inversion (tile value reading less prominent than a section heading). Reopening that decision here, a third time, on a different pretext, would re-litigate a settled question rather than answer the one this task was asked to answer.
- **(ii) — tile caption vs. nested card title, both the "name of a card" role, at two different tiers:** judged TRUE, and this is the real defect. A stat tile's caption (e.g. "Pipeline", "Corroboration") names what the tile contains, exactly the same job the nested card's `<h2>` (e.g. "Battery trend", "Resolution statistics") does for its own card. Until this task, one rendered at 14px **regular** and the other at 16px **semibold** — two peers, two different weight tiers, in the same "Server & data" region. The developer's complaint — a tile's caption reading smaller/weaker than other headings nearby — is literally this: the caption sat one full weight tier below its structural peer, and that gap opened specifically in the last 24 hours, when Finding 4 promoted the nested title's weight without anyone revisiting the caption's.

**Step 3 — the fix:** Option A — promote `.stat-tile__caption` to `--weight-semibold`, unchanged 14px/serif. Rejected alternatives, in writing:
- *Option B (colour/letter-spacing differentiation):* treats only the caption's own weakness in isolation; leaves the caption/nested-title weight disagreement — the actual peer-role collision — untouched.
- *Option C (adjust the nested title instead):* Finding 4 already placed it deliberately at 16px semibold to fix the previous inversion; moving it again re-opens that decision for no new reason, and its only legal moves within D-09's four-size scale are weight/family, both of which Finding 4 already chose correctly for its own purpose.
- *A fifth size (15px, or something between 14 and 20):* explicitly prohibited by D-09's four-size-scale contract (14/16/20/30). Not considered.

The caption stays strictly below `.stat-tile__value` in size (14 vs 16) and now shares its weight tier (semibold) rather than sitting one tier below it — the datum inside a tile is still the loudest thing in that tile, preserving the property Finding 4 protected. The caption and the nested title now agree on weight, the property that actually signals "this names something" at a glance, while the unchanged 14/16 size gap still correctly signals that a tile is subordinate to a section-level card.

**What the developer should look for in the next Safari pass:** whether the "Server & data" region's three stat-tile captions ("Pipeline", "Corroboration", "Resolution rate") now read as confidently-labelled as the two nested card titles beside them ("Unresolved prefixes", "Resolution statistics"), rather than as the visually weakest text in the region — see item 7 in "Pixel-Level Items Outstanding" below.

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on the CSS-height-bound mechanism, the `preserveAspectRatio="none"` rejection, the canvas-constant choices, the padding-mirroring decision, the Task 3 hypothesis-(ii) verdict, and the corrected blast-radius figure.

## Known Stubs

None. Every value touched by this task is real: the resized canvas constants drive the same real coordinate math that already existed; the table-header padding change is a plain CSS value; the caption weight change is a plain CSS value. No placeholder text, no hardcoded-empty data path, no new component with no data source wired.

## Threat Flags

None beyond what this task's own `<threat_model>` (T-dng-01 through T-dng-05, all `mitigate` or `accept`, plus T-dng-SC `accept` for the zero-package-install non-goal) already covers. No new interpolation site was introduced in `battery_sparkline_svg()` (only numeric canvas constants and one static `preserveAspectRatio` literal changed; every attacker-influenced value keeps its existing `escape_html()` call). `companion/static/battery-trend.js` is unmodified. The `.data-table th` padding change extends an opaque background strictly earlier, never exposing content that was previously covered. Task 3's verdict is written down in this SUMMARY regardless of outcome, closing the repudiation risk a third silent deferral would have posed.

## Issues Encountered

- No package installs, no auth gates. Rule 4 (architectural change) was never triggered — all three fixes are scoped CSS/constant changes within the plan's own stated levers.
- No computer-use/chrome-devtools MCP tools were bound to this subagent, matching the four immediately-prior Health quick tasks' (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc) own precedent for this session.
- PLAN.md's own blast-radius estimate for Task 3 ("11 call sites — 10 Health, 1 History") did not match a repo-wide grep of `layout.stat_tile(` call sites (4 real call sites, all in `health_page.py`, 0 in `history_page.py`). Recorded accurately above and in the Task 3 commit message rather than silently restated; does not change the fix itself, since `.stat-tile__caption` is a CSS rule applied unconditionally wherever the class is rendered.

## Pixel-Level Items Outstanding

No browser-automation tools were bound to this executor, matching all four preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc), each of which handed pixel-level confirmation back to the orchestrating session. **None of the following is claimed as verified here** — only source-level and live-HTTP-served-body verification was performed (see "Live-HTTP smoke test" above).

1. **The chart's real rendered scale ratio is now ~1.0, not just arithmetically bounded.** Measure the SVG's `getBoundingClientRect().width` divided by its `viewBox` width in the real browser. Expected: ~1.00 at a 1280px viewport (the same measurement that previously returned 2.53), and never above 1.00 at any width. **This is the single most important confirmation in this task** — the harness proves the arithmetic; only a browser proves the arithmetic describes the real rendered box.
2. **The chart still looks right at 1:1.** Axis labels legible at their true 10px, not colliding with the plot's left edge (the `_AXIS_LEFT_GUTTER` change is a planning-time-derived estimate of the "4200 mV" label's real width — a browser is what confirms it); the polyline reads as a trend, not a hairline; markers and hit targets visibly circular.
3. **The chart does not read as under-filled.** At 1:1 the chart occupies roughly 366 of a ~846px card at 1280px, left-aligned under the readout. If that reads as an empty card rather than a deliberate chart column, that is a real finding and the next lever is the card's own layout, not raising the scale cap above 1.0.
4. **375px re-check.** The chart should render at ~0.80 scale with everything still legible — no regression from the pre-existing 0.88 measurement (the new floor, 0.8005, is 6 points lower; confirm this is still visually acceptable, not just numerically inside the [0.80, 1.00] band).
5. **Real Safari, the readings disclosure.** Open it and confirm the header clipping is gone — the confirmation 260901-uzi's Finding 5 verdict explicitly asked for and could not obtain.
6. **All four tables re-spaced acceptably.** History, Health's readings table, Resolution statistics, and the unresolved-prefix registry each gain 10px of header height — confirm none now reads as loose.
7. **The type-hierarchy verdict, judged by eye.** Confirm the stat-tile captions no longer read as the weakest text in the "Server & data" region while `.stat-tile__value` stays the loudest thing in its own tile — see "Task 3 Verdict" above for exactly what changed and why.
8. **Still outstanding from prior rounds, unchanged by this task:** the chart's hover/tap/arrow-key interactive readout path, and a dark-theme pass.

## User Setup Required

None to run the code. **Recommended before signing off:** the 8-item live-browser pass above, on `/health`, with particular attention to item 1 (the real measured scale ratio — the one number this whole task exists to bound) and item 7 (the type-hierarchy verdict, which is a human judgment the harness cannot make).

## Next Phase Readiness

All three fixes are implemented and pinned by harness: `companion/test_status_pages.py` 92/92; `companion/test_view_pages.py` 43/43; `companion/test_companion_app.py` 105/105; `companion/test_config_page.py` 61/61; `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch, with no coverage-gate shortfall. The 8-item live-browser handoff above is the concrete next action for the orchestrating session before this can be considered visually verified, not just source-verified.

## Post-execution: real-browser visual pass (orchestrating session)

Performed against the restarted local instance with real production data, at 1280×1100.

1. **Chart scale ratio — CONFIRMED FIXED, and the concern about `scaleRatioW` was a red herring.** Direct measurement: `getBoundingClientRect()` on the chart returns `846×120` against `viewBox="0 0 366 120"` — width ratio computes to 2.31, height ratio to exactly 1.00. This looked alarming until checked against the actual content: `<text font-size:10px>` measures `12px` visual bounding-box height (normal for 10px text with typical line-height — i.e. genuinely unscaled) and a `.sparkline-dot` with `r="3"` measures exactly `6px` diameter (2×3, also genuinely unscaled). With `preserveAspectRatio="xMinYMid meet"`, the SVG scales *uniformly* by `min(scaleW, scaleH) = min(2.31, 1.00) = 1.00` and left-anchors the content — the wider "box" than "content" just means unused space to the right, not stretched content. Confirmed correct.
2. **Visual result: dramatic improvement, confirmed by screenshot.** Axis labels ("3882 mV", "3854 mV", "21:35", "21:47") now render as small, legible, properly muted text — no longer the oversized wall of text from before. Line and dots read as a normal, thin trend line, not a thick blob. This directly resolves the "catastrophique"/"trop gras"/"énorme" complaint.
3. **Item 3 confirmed as a real, visible trade-off, not a false alarm.** The chart now occupies roughly the left half of its card, with genuine empty space to the right at this viewport width — exactly as the plan's own risk note predicted. This is the deliberate cost of capping the scale at 1.0 rather than letting it stretch (which was the whole bug). Worth a separate conversation with the developer about whether to accept the whitespace, redesign the card's layout around it, or widen the plot's own canvas — not something to silently "fix" by re-introducing the scale-up.
4. **Table header padding (item 5/6): confirmed via computed style.** `.data-table th` now computes to `padding: 10px 16px` (was `0 16px 10px`) — symmetric, engine-independent, no longer WebKit-specific.
5. **Type-hierarchy fix (item 7): confirmed via computed style and screenshot.** `.stat-tile__caption` now computes to `font-weight: 600` (was 400), matching `.stat-tile__value` and the nested-card `<h2>`'s weight. Screenshot confirms "ADS-B pipeline last ran", "Corroboration", "Resolution rate" now read with clear, confident visual weight next to "Unresolved prefixes"/"Resolution statistics" — no longer the visually weakest text in the region.
6. **Content/structure integrity:** `get_page_text` confirms the full page (both sections, all three tiles, both tables, the registry rows) renders correctly with real data — no regression from the CSS/markup changes.

**Not performed:** 375px re-check (item 4), real Safari confirmation of the header-clipping fix (item 5, WebKit-specific — needs the developer's own browser), the chart's hover/tap/arrow-key interactive path, and dark theme. This session's screenshot capture had another round of intermittent failures partway through this pass (content/computed-style checks stayed reliable throughout and are what the findings above rest on).

---
*Phase: quick-260902-dng*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 3 modified files (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`) confirmed present on disk. All 3 task commit hashes (`af875d5`, `c9711c7`, `ed8244e`) confirmed present in `git log`.
