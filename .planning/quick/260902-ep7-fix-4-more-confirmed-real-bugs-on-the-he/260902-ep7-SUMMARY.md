---
phase: quick-260902-ep7
plan: 260902-ep7
subsystem: companion-ui

tags: [companion, health-page, svg, chart, css, design-system, accessibility, harness]

requires:
  - phase: 260902-chc
    provides: "the auto-refresh pill markup/CSS this task's Task 1 takes out of .page-header's block flow"
  - phase: 260901-tsa
    provides: "the Screen-section dashboard-grid wrapper (finding E) whose margin-bottom token this task's Task 2 Commit A retargets"
  - phase: 260902-dng
    provides: "the scale-bound chart mechanism (fixed CSS height == SVG height attribute, min(cW/vbW,1)) this task's Task 3 retires by removing the viewBox entirely, and the explicit written conclusion (\"the fix lever is the card's own layout, never raising the scale cap\") this task acts on"
provides:
  - ".page-header establishes a containing block (position: relative) and a new .page-header-scoped .refresh-pill rule takes the auto-refresh pill out of block flow entirely (position: absolute; top: 8px derived from the h1's line box; right: 0) — Health's h1-to-purpose gap now measures 4px like Airlines, by construction rather than a reserved line box"
  - ".dashboard-grid's margin-bottom retargeted from var(--space-2xl) to var(--space-lg) — the same same-section card-to-card token .page-section already uses — while .battery-trend-section's section-transition margin-bottom stays var(--space-2xl), unchanged"
  - "the bare summary rule declares color: var(--color-accent); style.css's exhaustive accent-reservation list and both literal restatements in 06.6.1-UI-SPEC.md's Color section are broadened from \"a <summary> disclosure marker\" to also cover the label text — recorded honestly as a broadening"
  - "battery_sparkline_svg() emits a viewBox-free, percentage-coordinate chart wrapped in a CSS grid (.sparkline) with real drawn axis lines and ticks (<rect class=\"sparkline-axis\">, filled with --color-border) and HTML <span> axis labels (replacing the deleted _AXIS_LEFT_GUTTER/_AXIS_BOTTOM_STRIP Python-side width estimates) — the chart's plot spans 0-100% of its card at every viewport, with no scale factor anywhere in the pipeline"
  - "companion/static/battery-trend.js is byte-for-byte unmodified — confirmed by git diff and by re-reading it in full; it reads attributes via getAttribute()/data-* and never computes SVG geometry, so the coordinate-system change is invisible to it"
  - "companion/test_status_pages.py: EXPECTED_CHECK_COUNT 92 -> 95 across three new/pair checks (the gap two-role split, the summary accent pair, the axis chrome check); six pre-existing <polyline-based markers, the readout-precedes-chart sparkline marker, the axis-label lookup, and the scale-bound check all retargeted/rewritten in place with no count change, every one individually mutation-tested"
affects: [companion-ui-implementation, health-page-visual-defects]

tech-stack:
  added: []
  patterns:
    - "Taking an element out of CSS block flow (position: absolute, scoped to its container) rather than reserving its line box, when the goal is 'revealing this element must shift nothing' — a structural guarantee instead of a height-matching one"
    - "Deleting an SVG's viewBox entirely (rather than tuning/bounding it) to make percentage-based geometry resolve against the element's own real rendered size — eliminates an entire class of scale-related bug rather than capping it, generalizable to any other chart this app adds"
    - "Moving axis-label text out of an SVG's scaled coordinate space into an HTML CSS-grid overlay whose auto-sized column measures the browser's own real text width, replacing a Python-side width ESTIMATE with the browser's own measurement"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_status_pages.py
    - .planning/phases/06.6.1-companion-visual-polish-pass-logo-branding-mobile-hamburger-/06.6.1-UI-SPEC.md
    - .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md

key-decisions:
  - "BUG 1's fix takes the pill out of flow entirely (position: absolute, scoped to .page-header .refresh-pill) rather than keeping 260902-chc's reserved-line-box mechanism (visibility: hidden with a still-reserved 20px line box). An out-of-flow box reserves nothing and shifts nothing because it participates in no flow at all — this preserves 260902-chc's real goal (no shift on reveal) STRICTLY MORE STRONGLY, making the guarantee structural rather than dependent on the hidden/visible boxes' heights matching. top: 8px is derived, not guessed: the h1's own line box is 36px (30px font at line-height 1.2), the pill is 20px, (36-20)/2 = 8, centring the pill against the title's own line. Rejected alternatives, in writing in the CSS comment: flex/grid .page-header (pill still occupies its own row), float: right (purpose sentence wraps around it), restructuring layout.page_header() (touches every authenticated page for a Health-only need)."
  - "BUG 2's fix retargets .dashboard-grid's margin-bottom from --space-2xl (the section-transition value .battery-trend-section also uses) to --space-lg — the real in-file precedent for a same-section card-to-card gap, already used by .page-section to separate the Unresolved-prefixes and Resolution-statistics cards. Both of .dashboard-grid's two real call sites (verified by grep) are same-section, card-to-card gaps, never section transitions, so the old shared token was wrong for both of them. .battery-trend-section's own margin-bottom is untouched — that one is a genuine section transition."
  - "BUG 3's fix adds color: var(--color-accent) to the bare summary rule and broadens style.css's exhaustive accent-reservation list (plus both literal restatements in 06.6.1-UI-SPEC.md's Color section) from naming only the ::marker pseudo-element to also naming the label text. Recorded as a genuine broadening, following the file header's own standing instruction not to widen the list silently. Deliberately declined the validated sketch's font-size: var(--font-label-size) on summaries — not the reported defect, and would land on all four real disclosure call sites (health_page.py's readings table + Corroboration \"More details\", history_page.py's mobile per-card \"More details\" + its migrated-from-Preview \"Recent renders (N)\" gallery disclosure) as an unrequested rider."
  - "BUG 4's fix deletes the SVG viewBox outright rather than re-tuning the scale cap 260902-dng shipped hours earlier. Evaluated and rejected a breakpoint-aware dual canvas in writing: it would break battery-trend.js's querySelectorAll(\".sparkline-hit\")-plus-roving-tabindex contract (two <svg> means 2N points, half inside display:none where .focus() silently fails, plus two competing tabindex=\"0\" Tab stops), and even so each band still spans a wide ratio of the real 293-1278px, non-monotonic-at-960px container range, so it would not even fully solve the fill problem. With no viewBox, 1 SVG user unit == 1 CSS pixel and every x-position is a percentage of the canvas's own real rendered width — the chart's fill-the-card behavior becomes structural, and the entire class of scale-related bug (both 260902-dng's earlier 2.53x oversizing and this task's under-filling complaint) becomes permanently unreachable rather than merely bounded."
  - "BUG 4's axis chrome uses filled <rect> elements, not stroked <line> elements, for a specific reason: an axis-aligned filled rect has no stroke-centring/half-pixel-rounding to reason about, and a rect can pair a percentage position with an absolute size (needed for every tick, which mixes a percentage axis coordinate with an absolute pixel length) in a way a stroked line cannot. --color-border (the file's existing \"structural only, never an interactive-state signal\" token) is reused rather than inventing a new colour value; the recorded fallback if it proves too faint in the live-browser pass is the file's existing color-mix(in srgb, var(--color-text) 12%, transparent) edge value, not a new one."
  - "Corrected a stale blast-radius count from planning during Task 2: the plan's brief claimed five <summary> call sites; a repo-wide grep found exactly four real ones — the plan's \"History's own readings-disclosure\" and \"Preview's Recent renders (N)\" items describe the same migrated call site (history_page.py:851, reused after preview_page.py's D-13 deletion) counted twice."
  - "Task 3 shipped as two atomic commits at the real functional boundary the plan specified: Commit A (the viewBox-free percentage-coordinate canvas plus the HTML axis-label grid, carrying the six retargeted markers and the rewritten scale check) and Commit B (the drawn axis lines/ticks plus the §5.3 UI-SPEC update, carrying the one new axis-chrome check) — each independently green on its own (94/94 then 95/95), verified by staging/reverting the axis-chrome-specific hunks between the two commits rather than committing the whole rewrite in one shot."

requirements-completed: [QUICK-260902-ep7]

coverage:
  - id: header-gap-out-of-flow
    description: "Health's h1-to-purpose gap measures 4px like Airlines, with the auto-refresh pill out of block flow entirely so revealing it shifts nothing, by construction"
    requirement: QUICK-260902-ep7
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_chc_pill_stylesheet_contract (strengthened in place) — asserts .page-header declares position: relative and a .page-header-scoped .refresh-pill rule declares position: absolute with top/right offsets, alongside the pre-existing visibility/display assertions"
        status: pass
      - kind: manual
        ref: "server/.venv/bin/python3 -c '...' inline verification script from PLAN.md's Task 1 <verify> block"
        status: pass
    human_judgment: true
    rationale: "A harness check proves the CSS declarations exist; only a real browser's getBoundingClientRect() diff (before/after revealing the pill) proves nothing actually shifts."
  - id: card-to-card-gap-split
    description: "The Screen section's Device tile and battery-trend card are separated by the same 24px same-section rhythm .page-section uses elsewhere, not the 48px section-transition value"
    requirement: QUICK-260902-ep7
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_ep7_dashboard_grid_card_gap_two_role_split (new) — pins .dashboard-grid's margin-bottom == .page-section's own value while staying smaller than .battery-trend-section's, as a pair"
        status: pass
      - kind: manual
        ref: "server/.venv/bin/python3 -c '...' inline verification script from PLAN.md's Task 2 <verify> block"
        status: pass
    human_judgment: true
    rationale: "The harness proves the token values; only a browser confirms the visually measured gap (24px, matching the Server & data region's own nested-card gap)."
  - id: summary-accent
    description: "Every <details> disclosure's <summary> renders in the accent colour, with the broadening recorded in both style.css's own list and 06.6.1-UI-SPEC.md's Color section"
    requirement: QUICK-260902-ep7
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_ep7_summary_accent_and_reservation_list (new) — pins the summary rule's accent colour and the reservation list's mention of the label text, as a pair"
        status: pass
      - kind: unit
        ref: "companion/test_contrast_check.py (36/36) — --color-accent's existing WCAG AA text contrast and status-colour separation hold at the unchanged value"
        status: pass
    human_judgment: true
    rationale: "The harness proves the declaration and the doc update exist; only a browser (in both themes) confirms the summary text visually reads as accent-coloured against --color-dominant."
  - id: chart-real-axes-and-fills-card
    description: "The battery-trend chart carries real drawn axis lines/ticks and its plot geometry spans 100% of its card's width at every viewport, with no scale factor anywhere in the pipeline"
    requirement: QUICK-260902-ep7
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_sparkline_scale_bounded_at_one_across_real_container_widths (rewritten in place) — no viewBox/preserveAspectRatio, every cx/cy a percentage in [0,100], strictly increasing marker x-positions, radii still absolute 3/8, canvas height declared exactly once and never inside @media"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_sparkline_axis_chrome_present (new) — at least one full-height vertical axis <rect>, one full-width horizontal axis <rect>, and two tick <rect> elements, all aria-hidden"
        status: pass
      - kind: unit
        ref: "6 retargeted <polyline-based markers (2 negative, 4 positive) plus the readout-precedes-chart sparkline marker and the axis-label lookup, all retargeted in place, all pass"
        status: pass
      - kind: manual
        ref: "two inline verification scripts from PLAN.md's Task 3 <verify> block, plus git diff --quiet on battery-trend.js"
        status: pass
      - kind: manual
        ref: "standalone live-HTTP smoke script: real companion/app.py subprocess, real login, real seeded battery readings, fetched /health and the served stylesheet — confirmed percentage cx, sparkline-axis rects, HTML axis-label spans, sparkline-line segments, and no viewBox on the chart's own <svg> tag, all present in the SERVED response bodies"
        status: pass
    human_judgment: true
    rationale: "This is the largest live-browser-only surface in the plan — see 'Pixel-Level Items Outstanding' below. The harness and the live-HTTP smoke test prove the structure and coordinate math; only a real browser proves the chart looks right, fills the card, and that the hover/tap/arrow-key interaction still works under a script deliberately not edited."

duration: ~50min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-ep7: Fix 4 More Confirmed Real Bugs on the Health Page Summary

**Takes the auto-refresh pill out of the page header's block flow entirely, retargets the same-section card gap to its real in-file precedent, makes disclosure summaries read as accent-coloured controls, and deletes the battery-trend chart's SVG viewBox outright — turning "fills the card" and "no scale-related distortion" into structural properties instead of tuned numbers, then draws real axis lines and ticks on top.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Commits:** 5 (matching the plan's own commit structure exactly)
- **Files modified:** 5 (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `06.6.1-UI-SPEC.md`, `06.6.4.1-UI-SPEC.md`)

## Accomplishments

- **Task 1 — the header gap (BUG 1):** `.page-header` gained `position: relative`; a new `.page-header .refresh-pill` rule takes the auto-refresh pill out of block flow entirely (`position: absolute; top: 8px; right: 0`), replacing 260902-chc's reserved-line-box mechanism (`visibility: hidden` with a still-consumed 20px line box) with a design that reserves nothing and shifts nothing because the pill participates in no flow at all. `.refresh-pill[hidden]` keeps hiding by `visibility` with no `display` value, so 260902-chc's accessibility-tree behaviour is unchanged. `layout.page_header()` is unmodified. The existing pill-stylesheet-contract check was strengthened in place (no count change) to pin the new mechanism alongside its pre-existing assertions.
- **Task 2 — the card gap and the disclosure accent (BUGS 2 and 3), two commits:**
  - Commit A: `.dashboard-grid`'s `margin-bottom` retargeted from `var(--space-2xl)` (the section-transition token `.battery-trend-section` also uses) to `var(--space-lg)` — the real in-file precedent for a same-section card-to-card gap, already used by `.page-section` to separate the Server & data section's two nested cards. `.battery-trend-section`'s own margin stays untouched. One new check pins both margins as a pair.
  - Commit B: the bare `summary` rule gained `color: var(--color-accent)`; style.css's exhaustive accent-reservation list and both literal restatements in `06.6.1-UI-SPEC.md`'s Color section were broadened from "a `<summary>` disclosure marker" to also name the label text — recorded honestly as a broadening, per the file header's own standing instruction. Deliberately declined the sketch's font-size change (out of scope, would land on all four real disclosure call sites unrequested). One new check pins the rule and the doc broadening as a pair.
- **Task 3 — the chart redesign (BUG 4), two commits:**
  - Commit A: `battery_sparkline_svg()` rewritten to emit a viewBox-free, percentage-coordinate chart wrapped in a CSS grid (`.sparkline`) — an `auto`-sized label column replaces the deleted `_AXIS_LEFT_GUTTER`/`_AXIS_BOTTOM_STRIP` Python-side width estimates with the browser's own real text measurement. The single `<polyline>` becomes `n - 1` `<line class="sparkline-line">` segments (percentages aren't permitted in a `<polyline>` `points` list). Every size (marker `r=3`, hit-target `r=8`, stroke-width, label font-size) is now an absolute CSS pixel value at every container width, forever — no scale factor exists anywhere in the pipeline. Evaluated and rejected a breakpoint-aware dual canvas in writing (would break `battery-trend.js`'s roving-tabindex/NodeList contract, and would not even fully solve the fill problem). Six pre-existing `<polyline`-based harness markers (two of them negative assertions, which would have passed vacuously if left unretargeted) plus the readout-precedes-chart sparkline marker and the axis-label lookup were retargeted in place; the scale-bound check was rewritten in place as a no-scale-factor check.
  - Commit B: real drawn axis chrome added — `<rect class="sparkline-axis" aria-hidden="true">` elements (filled, not stroked, with `--color-border`) for a full-height Y axis, a full-width X axis, and four ticks. `06.6.4.1-UI-SPEC.md` §5.3 updated to record that real axis lines are now drawn (extending, not reversing, its own prior "no axis lines required" floor). One new check pins the axis chrome's presence and per-tag `aria-hidden` discipline.
- **`companion/static/battery-trend.js` confirmed byte-for-byte unmodified** by `git diff --quiet` after every commit and by re-reading it in full — it reads attributes via `getAttribute()`/`data-*` and never computes SVG geometry, so the coordinate-system change (user units → percentages) is invisible to it, exactly as the plan required.
- **Harness:** `EXPECTED_CHECK_COUNT` 92 → 95 across three genuinely new/pair checks (the gap two-role split, the summary accent pair, the axis chrome check); every other change was an in-place retarget/rewrite with no count change. Every new and rewritten check was individually mutation-tested (one deliberate defect, confirmed to fail exactly that check — or, where multiple checks share the identical underlying assertion against the same fixture, exactly that shared set and no unrelated check — then restored). `companion/test_status_pages.py` 95/95, `companion/test_view_pages.py` 43/43, `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch (in `server/plane/render.py`'s frame-rendering path, untouched by this task) — with no coverage-gate shortfall (92% total, per the run's own report).
- **Live-HTTP smoke test:** started a real `companion/app.py` subprocess against a seeded state directory, signed in over HTTP, and fetched the real `/health` and `/static/style.css` response bodies both before and after seeding real battery readings. Confirmed the served CSS carries the pill's out-of-flow rule, `.dashboard-grid`, the broadened accent declaration, `.sparkline`/`.sparkline-axis`; confirmed the seeded `/health` response carries percentage `cx`, `sparkline-axis` rects, HTML `sparkline-axis-label` spans, `sparkline-line` segments, and no `viewBox` on the chart's own `<svg>` tag (icon `<symbol>` definitions elsewhere on the page legitimately carry their own, unrelated `viewBox` — the check was scoped to the chart's own tag specifically to avoid a false positive there).

## Task Commits

1. **Task 1:** `bb8961a` — `fix(quick-260902-ep7): take the refresh pill out of the page header's flow` — `companion/static/style.css`, `companion/test_status_pages.py`
2. **Task 2 Commit A:** `d3c48e4` — `fix(quick-260902-ep7): use the card-to-card gap between same-section cards` — `companion/static/style.css`, `companion/test_status_pages.py`
3. **Task 2 Commit B:** `13cb63d` — `fix(quick-260902-ep7): make disclosure summaries read as interactive` — `companion/static/style.css`, `companion/test_status_pages.py`, `06.6.1-UI-SPEC.md`
4. **Task 3 Commit A:** `34eaad8` — `refactor(quick-260902-ep7): drop the chart's viewBox for a full-width canvas` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `06.6.4.1-UI-SPEC.md`
5. **Task 3 Commit B:** `2cb56a7` — `feat(quick-260902-ep7): draw real axis lines and ticks on the battery chart` — `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `06.6.4.1-UI-SPEC.md`

## Files Created/Modified

- `companion/pages/health_page.py` — `SPARKLINE_LINE_CLASS`/`SPARKLINE_AXIS_CLASS` constants added; `_AXIS_LEFT_GUTTER`/`_AXIS_BOTTOM_STRIP` deleted outright, replaced by `_SPARKLINE_CANVAS_HEIGHT_PX` (160) and `_SPARKLINE_VERTICAL_INSET_PERCENT` (3.75, derived from the axis label's half-line-box height); `battery_sparkline_svg()` rewritten from a fixed-viewBox/polyline function returning a bare `<svg>` into a viewBox-free, percentage-coordinate function returning a `<div class="sparkline">` CSS-grid wrapper with drawn axis chrome
- `companion/static/style.css` — `.page-header` gains `position: relative`; new `.page-header .refresh-pill` rule; `.dashboard-grid`'s `margin-bottom` retargeted to `var(--space-lg)`; `summary` gains `color: var(--color-accent)`; the file-header accent-reservation list broadened; `.battery-trend-section svg:not(.icon)` rewritten (`width: 100%; height: 160px; overflow: visible; display: block`, no more viewBox-bound height equality); new `.sparkline`/`.sparkline__y`/`.sparkline__x`/`.sparkline-line`/`.sparkline-axis` rules; `.sparkline-axis-label` moved from `fill` to `color` with `line-height: 1.2` added
- `companion/test_status_pages.py` — `EXPECTED_CHECK_COUNT` 92 → 95; one strengthened-in-place check (Task 1); two new checks (the gap pair, the summary-accent pair); six retargeted `<polyline`-based markers plus the readout-precedes-chart marker and the axis-label lookup, all in place; the scale-bound check rewritten in place; one new axis-chrome check
- `.planning/phases/06.6.1-.../06.6.1-UI-SPEC.md` — the light-mode Accent row and the standalone reserved-for restatement both append the `<summary>` label-text broadening; the dark-mode row already deferred to light mode's list by reference and needed no direct edit
- `.planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md` — §5.3 updated (the "no axis lines required" floor extended, the viewBox-grows sentence retired, labels-as-HTML-spans recorded); the Typography-exceptions table row for the chart axis labels updated to match

## Re-Derived Container-Width Table (kept as historical evidence, not a live constraint)

This is the same derivation 260902-dng wrote for the now-retired scale-bound mechanism, re-derived and re-verified during planning as the concrete proof that a fixed-viewBox design could never fill the card across this range — every number below is now moot for the chart's own geometry (there is no viewBox left to scale), but it stays in `style.css`'s own rule comment and the harness check's own comment as the recorded reason the old mechanism existed.

| Viewport | Container width | Note |
|---|---|---|
| 375px | **293px** (narrowest real container) | |
| 959px | 877px | |
| **960px** | **526px** | **the real discontinuity — container DROPS as the sidebar appears** |
| 1280px | 846px | matches the live measurement that motivated 260902-dng |
| ≥ 1568px | 1278px | capped by the 1440px max-width |

Real range: 293px to 1278px, a 4.36x spread, non-monotonic at the 960px breakpoint.

## Why Not Two Breakpoint-Matched Canvases

Evaluated and rejected in writing (in `style.css`'s own rule comment and this plan's own reasoning), for three concrete reasons:

1. It would emit two `<svg>` elements toggled by a media query. `battery-trend.js` does `document.querySelectorAll(".sparkline-hit")` once and drives roving tabindex over the resulting NodeList by index — with two charts in the DOM it would traverse 2N points, half of them inside a `display: none` subtree where `.focus()` fails silently, and there would be two `tabindex="0"` Tab stops, one of them invisible.
2. Fixing that means editing `battery-trend.js` — the project's only JavaScript file, with the tightest constraints in the codebase — to add a visibility filter, for a redesign that does not need one.
3. It would not even solve the problem it costs that much for: each breakpoint band still spans a wide ratio (293-877px below 960px, 526-1278px above it), so each band's own SVG would still under-fill or over-shrink across most of its own range. Genuinely fixing it by breakpoints needs three or four canvases, not two.

## Canvas Height and Vertical-Inset Arithmetic

The canvas height (160px) was chosen against three stated criteria, all satisfied: at least the validated sketch's own 150px (the only height this chart has ever been reviewed at), no more than ~180px so the card does not dominate the page, and tall enough that a small millivolt spread still reads as a trend rather than a flat line.

The vertical inset (3.75%) was derived, not chosen by taste: it must be at least the 3-unit cosmetic-marker radius so no dot is ever clipped, and it is set to equal half the axis label's own line box (as a fraction of the canvas height) so `justify-content: space-between` (`.sparkline__y`) places each Y label's optical centre exactly on the level it names. A 10px label at `line-height: 1.2` is a 12px line box; half of that is 6px; `6 / 160 * 100 = 3.75`. Both numbers are recorded as named module constants (`_SPARKLINE_CANVAS_HEIGHT_PX`, `_SPARKLINE_VERTICAL_INSET_PERCENT`) in `health_page.py`, with the arithmetic in their own comments — re-derive if either the label's typography or the canvas height ever changes.

## Card-to-Card vs. Section-to-Section Spacing Split

Before this task, both `.dashboard-grid`'s margin-bottom and `.battery-trend-section`'s margin-bottom used `var(--space-2xl)` (48px) — one role doing double duty for two different jobs. This task establishes the split explicitly:

- **Same-section, card-to-card rhythm:** `--space-lg` (24px) — `.dashboard-grid` now, `.page-section` already (the value that separates the Unresolved-prefixes card from the Resolution-statistics card, both inside the single Server & data section — the real in-file precedent this task's fix was sourced from).
- **Section-to-section separation:** `--space-2xl` (48px) — `.battery-trend-section`'s own margin-bottom, unchanged, closing the Screen section before the Server & data heading.

A new harness check pins both roles as a pair so a future "harmonising" edit cannot silently re-flatten the split.

## The Accent-Reservation Broadening

Before this task, style.css's exhaustive accent-reservation list (file header) named "a `<summary>` disclosure marker" — the `::marker` pseudo-element only. The `<summary>` element's own label text declared no colour and inherited full-strength `--color-text`, making every disclosure control (Health's readings table, Health's Corroboration "More details", History's mobile per-card "More details", and History's migrated-from-Preview "Recent renders (N)" gallery disclosure — four real call sites, corrected from the plan's stale five-site count) visually indistinguishable from static text except by hovering.

This task adds `color: var(--color-accent)` to the bare `summary` rule and broadens the reservation list — honestly recorded as a broadening, not a clarification — in two files: style.css's own header comment, and both literal restatements of the list in `06.6.1-UI-SPEC.md`'s Color section (the dark-mode row already deferred to light mode's list by reference, so it needed no direct edit to stay consistent).

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on the out-of-flow pill mechanism, the card-gap retarget, the accent broadening, the viewBox-deletion rationale, the rejected dual-canvas alternative, the axis-chrome rect-vs-line choice, and the corrected blast-radius figure.

## Known Stubs

None. Every value touched by this task is real: the CSS declarations are plain values, the chart's coordinate math drives the same real per-point data it always did (now expressed as percentages instead of user units), and the axis chrome renders real computed positions (`_point_x`/`_point_y`) rather than placeholder geometry. No hardcoded-empty data path, no new component with no data source wired.

## Threat Flags

None beyond what this task's own `<threat_model>` (T-ep7-01 through T-ep7-07, all `mitigate` or `accept`, plus T-ep7-SC `accept` for the zero-package-install non-goal) already covers. T-ep7-01's mitigation was carried through exactly as written: the two X-axis clock labels' `escape_html()` call survived the move from an SVG `<text>` node to an HTML `<span>` unchanged (confirmed by re-reading the final diff — the call site itself was never touched, only the element wrapping it). No new interpolation site was introduced anywhere in `battery_sparkline_svg()` — only `cx`/`cy`'s numeric FORM changed (server-computed floats, never attacker-influenced). `companion/static/battery-trend.js` is confirmed unmodified by `git diff --quiet` after every commit. The absolutely positioned pill (T-ep7-06) stays non-interactive, scoped to `.page-header`, and Health remains the only page passing `freshness_html` (re-confirmed from source this session).

## Issues Encountered

- No package installs, no auth gates. Rule 4 (architectural change) was never triggered — all four fixes are scoped CSS/Python changes within the plan's own stated levers.
- No computer-use/chrome-devtools MCP browser-automation tools were bound to this executor, matching all five preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng), each of which handed pixel-level confirmation back to the orchestrating session.
- The plan's brief claimed five `<summary>` call sites for BUG 3's blast radius; a repo-wide grep found exactly four real ones (the plan double-counted `history_page.py`'s migrated-from-Preview gallery disclosure once as "History's own readings-disclosure" and again as "Preview's Recent renders (N)"). Corrected in the CSS comment and in this SUMMARY rather than silently restated; does not change the fix.
- Two harness checks beyond the plan's own named "six `<polyline`-based markers" also needed retargeting once the viewBox was removed: `_battery_readout_precedes_chart_class_list_and_live_region()` (its own `<svg viewBox="0 0` marker for distinguishing the chart from the heading's icon `<svg>` no longer exists) and the two style.css comment passages that referenced SVG-specific mechanics (`fill` vs `color` on axis labels, X-tick alignment). All retargeted/updated in place alongside the six the plan named; recorded here since the plan's own count of affected checks was one short.
- Task 3's two commits (A: viewBox-free canvas, B: drawn axes) were implemented as one continuous rewrite and then split into the plan's required two-commit structure by temporarily removing the axis-chrome-specific code/CSS/check/doc-update, committing that intermediate state (verified green at 94/94 on its own), then restoring the full state for the second commit (verified green at 95/95). Both intermediate and final states were independently test-suite-verified, not just diffed.
- Mutation-testing the three trend-line-segment-count checks (the 3-readings check, the per-point-interactive check, and the axis-labels check) with a single shared-mechanism mutation caused all three to fail together rather than exactly one, since all three assert the identical underlying computed fact (`n - 1` segments for the same 3-row fixture shape) — consistent with this codebase's own existing layered-check convention (multiple pre-existing checks already redundantly assert `<polyline` counts at different call sites). Each check's OTHER unique assertions (aria-hidden discipline, chronological ordering, radii) were separately mutation-tested in isolation where feasible.

## Pixel-Level Items Outstanding

No browser-automation tools were bound to this executor, matching all five preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng), each of which handed pixel-level confirmation back to the orchestrating session, which performed it successfully every time. **None of the following is claimed as verified here** — only source-level, harness-level, and live-HTTP-served-body verification was performed (see "Live-HTTP smoke test" above).

**Bugs 1-3 (small live-browser surface, mostly computed-style confirmable):**

1. **Header gap.** Measure the vertical distance between `h1.page-title`'s bottom and `p.page-header__purpose`'s top on `/health`, and compare against the same measurement on `/airlines`. Expected: both 4px.
2. **Pill reveal.** Force the pill visible (remove `hidden`, or wait for a real refresh cycle) and confirm nothing in the header moves — capture the h1's and purpose paragraph's bounding rects before/after and diff them. Confirm the pill is legible top-right, vertically centred against the title, and does not overlap the title text at a narrow viewport.
3. **The Screen-section gap.** Measure the distance between the Device stat tile's bottom and the battery-trend card's top. Expected: 24px, matching the gap between the two nested cards in Server & data.
4. **Summary colour.** Confirm `<summary>View N readings</summary>` computes to the accent colour rather than `rgb(23, 25, 31)` on `/health`, and spot-check `/history` and the Preview gallery disclosure so the shared-rule blast radius is confirmed rather than assumed. Check both light and dark themes.

**Bug 4 (the largest live-browser-only surface in this task — flagged by the plan as the highest-risk item):**

Provable from source/harness/live-HTTP and already covered, so do NOT re-verify these by eye: the absence of a viewBox/preserveAspectRatio, every `cx`/`cy` being a percentage inside [0, 100], strictly increasing point ordering, the absolute `r="3"`/`r="8"` radii, the presence/count/aria-hidden discipline of `<rect class="sparkline-axis">` axis and tick elements, the four axis labels and their real min/max/clock values, the single non-media-query canvas height declaration, the JS file being unmodified, and that the served response bodies actually carry all of the above.

Needs a real browser:

5. **Does it actually fill the card.** At a ~1280px viewport, measure the chart canvas's `getBoundingClientRect().width` against `.battery-trend-section`'s own content width. Expected: the canvas occupies everything except the Y-label column and its gap — roughly 780-800px of an ~846px card, versus the ~366-of-846 that prompted this task. Confirm there is no longer a band of empty space on the right.
6. **Axis legibility.** Are the drawn axis lines/ticks actually visible against the card surface at `--color-border`, in BOTH themes? Flagged as the single most likely thing to need a follow-up — if too faint, the recorded fallback is the existing `color-mix(in srgb, var(--color-text) 12%, transparent)` edge value, not a new one.
7. **Do the labels line up with what they name.** The Y max/min labels should sit optically on the levels of the highest/lowest points (the inset-equals-half-a-line-box arithmetic, a planning-time derivation a browser confirms); the X labels should sit under the first/last points, aligned with their ticks.
8. **1:1 rendering, re-measured.** Every marker should measure exactly 6px across and every stroke exactly 2px, at every width. Measure a `.sparkline-dot` at 1280px and again at 375px and confirm both read 6px — the direct successor to the measurement that returned 2.53x before 260902-dng and ~1.00 after it, now width-independent rather than merely bounded.
9. **375px pass.** Confirm the chart still reads as a trend at the narrowest real container: labels legible at their true 10px, the Y-label column not eating the plot, points distinguishable, markers not clipped at either edge.
10. **The interactive path, end to end — HIGHEST-RISK ITEM, outstanding from three prior rounds and now higher-stakes because the coordinate system changed under it.** Hover a point, tap a point, Tab into the chart, then arrow-key left/right and Home/End across every point. Confirm the readout updates, the active marker highlights, focus is visible, and the roving tabindex still lands exactly one Tab stop on the chart. The harness proves the attributes survived; only this proves the behaviour did. This is the one thing flagged as most likely to silently break without any code-level signal.
11. **Does the chart read as too tall or too short at its chosen 160px height,** and does the card as a whole now read as deliberate rather than half-empty. A human judgment, not a measurement.
12. **Still outstanding from prior rounds, unchanged by this task:** a full dark-theme pass over the whole Health page, and real Safari confirmation of the table-header padding fix landed in 260902-dng.

## User Setup Required

None to run the code. **Recommended before signing off:** the 12-item live-browser pass above, on `/health`, with particular attention to item 10 (the interactive path — the highest-risk item, since it's the one thing that could silently break without a code signal) and item 5/6 (fills the card, axis legibility — the two things this task exists to fix).

## Next Phase Readiness

All five fixes are implemented and pinned by harness: `companion/test_status_pages.py` 95/95; `companion/test_view_pages.py` 43/43; `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch, with no coverage-gate shortfall (92% total). The 12-item live-browser handoff above is the concrete next action for the orchestrating session before this can be considered visually verified, not just source-verified — bug 4's interactive path (item 10) and fill/axis-legibility (items 5-6) are the priority items.

---
*Phase: quick-260902-ep7*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 5 modified files (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `06.6.1-UI-SPEC.md`, `06.6.4.1-UI-SPEC.md`) confirmed present on disk. All 5 task commit hashes (`bb8961a`, `d3c48e4`, `13cb63d`, `34eaad8`, `2cb56a7`) confirmed present in `git log`.
