---
phase: quick-260902-dng
plan: 260902-dng
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/pages/health_page.py
  - companion/static/style.css
  - companion/test_status_pages.py
autonomous: true
requirements: [QUICK-260902-dng]
tags: [companion, health-page, svg, chart, css, design-system, harness]

must_haves:
  truths:
    - "The battery-trend chart's effective SVG scale factor is <= 1.00 at every real container width the responsive chain can produce (293px at a 375px viewport through 1278px at the 1440px cap), so 10px axis labels never render at 25px and stroke-width 2 never renders at 5px again."
    - "The chart's scale factor is also >= 0.80 at the narrowest real container, so fixing desktop does not regress the 375px mobile rendering that measures correctly today (0.88)."
    - "Every table header's glyph ascenders have real opaque background above them, in every browser, regardless of font-ascent metrics — the sticky `top: 0` boundary no longer sits on the glyph tops."
    - "The Server & data region's four text roles (section heading, tile caption, tile value, nested card title) are enumerated from source and a written, source-grounded verdict resolves whether their current relationship is the developer's recurring complaint — with a shipped CSS change or a precise negative finding, never a fourth deferral."
    - "companion/test_status_pages.py stays green at its own EXPECTED_CHECK_COUNT, and scripts/run-all-tests.sh reports exactly one failing harness (the pre-existing, unrelated server/test_poll_loop.py panel.bin digest mismatch)."
  artifacts:
    - "companion/pages/health_page.py — battery_sparkline_svg()'s canvas constants resized and an explicit preserveAspectRatio emitted"
    - "companion/static/style.css — .battery-trend-section svg:not(.icon) height rule rewritten; .data-table th gains real top padding"
    - "companion/test_status_pages.py — new checks pinning the scale bound, the header padding, and (conditionally) the type-role verdict"
  key_links:
    - "The CSS declared height on `.battery-trend-section svg:not(.icon)` MUST equal the `height` attribute battery_sparkline_svg() emits — that equality is the entire mechanism bounding the scale at 1.0, and it lives in two files, so a harness check must pin it."
    - "battery_sparkline_svg()'s point/label/hit-target coordinates all derive from plot_width/plot_height/padding/_AXIS_LEFT_GUTTER/_AXIS_BOTTOM_STRIP — only those constants change; the formulas do not."
    - "companion/static/battery-trend.js reads data-mv/data-ts/data-when off the DOM and never recomputes geometry (verified in full during planning) — it needs no edit and must not receive one."
    - "`.data-table th` is shared by History's table, the Health readings table, the Resolution-statistics table and the hand-rolled unresolved-prefix registry table — all four re-space together, deliberately."
---

<objective>
Fix two confirmed-severe, live-measured Health-page defects the developer reproduced in real Safari after today's four earlier quick tasks landed, and reach a real resolution on a recurring type-hierarchy complaint that two prior investigation rounds left unanswered.

Purpose: BUG 1 is the developer's "vraiment moche" — the battery-trend chart renders at 2.53x its designed scale, blowing 10px axis labels up to ~25px and 2px strokes to ~5px. BUG 2 is quick task 260901-uzi's own Finding 5, which that task diagnosed correctly and then declined to fix blind, citing WebKit-vs-Blink font-ascent differences; the developer's own Safari screenshot has now confirmed it is real. The design question has been raised in three separate messages this session and deferred twice — this task must land on an answer.

Output: a chart whose scale factor is bounded at 1.00 by construction at every real container width, table headers with genuine breathing room above their glyphs, a written verdict (with or without a CSS change) on the type-role question, and harness checks that make each of those provable from source.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260901-uzi-fix-4-confirmed-real-bugs-on-the-health-/260901-uzi-SUMMARY.md

Read the "Finding 5 Verdict" section of that SUMMARY in full before Task 2 — BUG 2 below is that finding's candidate (a), now confirmed by the developer's own Safari testing and needing an actual fix rather than a third deferral.

Skill("sketch-findings-skypane") is the authoritative design-system reference for this app. Load it before Task 3; the four-size scale, the sub-scale exception tier and the named `.stat-tile__caption` serif exception are all recorded there.

Measurements taken live by the orchestrating session before this plan was written, against the real rendered page — treat these as given, do not re-derive them from scratch:
- The chart SVG carries `viewBox="0 0 334 74"` and renders at `846x187` CSS px in its real full-width card at a 1280px viewport → a **2.53x** uniform scale-up (846/334).
- The three Server & data stat tiles measure 272px wide with exactly equal 32px gaps — NOT a bug, do not touch.
- Health's `h1.page-title` (30px Georgia) and its top-level `h2.text-heading` section headings (20px Georgia) are byte-identical in computed style to Settings' own — page-level heading treatment is NOT inconsistent between the two pages. Do not touch either page's h1/h2 CSS.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Bound the battery-trend chart's scale factor at 1:1 (BUG 1)</name>
  <files>companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py</files>

  <read_first>
    - `companion/pages/health_page.py` lines ~390-590: `_AXIS_LEFT_GUTTER`, `_AXIS_BOTTOM_STRIP`, and `battery_sparkline_svg()` in full — every coordinate in it derives from `plot_width`/`plot_height`/`padding` plus those two gutter constants.
    - `companion/static/style.css`: the `.battery-trend-section` rule and the `.battery-trend-section svg:not(.icon)` rule immediately after it; `.sparkline-axis-label` (10px, the documented sub-scale tier); `.page-content`; the `@media (min-width: 960px)` block's `.dashboard-shell` and `.dashboard-main` rules; the `--space-*` token block.
    - `companion/test_status_pages.py`: the existing sparkline checks (`_sparkline_has_no_external_reference`, `_sparkline_svg_has_per_point_interactive_markup`, `_sparkline_axis_labels_present_with_real_min_max`) — confirmed during planning to pin no coordinate literals, so a constant change should not break them; if one does, retarget it in place (no count change) and say so in the commit body.
    - Do NOT open `companion/static/battery-trend.js` to change it. It was read in full during planning: it reads `data-mv`, `data-ts` and `data-when` via `getAttribute()` and recomputes no geometry whatsoever, so it is unaffected by any canvas resize. Reading it to confirm is fine; editing it is out of scope for this task.
  </read_first>

  <behavior>
    - Given the SVG's emitted `viewBox` w/h and the CSS declared height for `.battery-trend-section svg:not(.icon)`, the effective uniform scale at container width cW is `min(cW / viewBoxW, cssHeight / viewBoxH)`.
    - That scale must be `<= 1.00` for every cW in the real container range, and `>= 0.80` at the narrowest.
    - The SVG's `width`/`height` attributes must stay equal to the viewBox's w/h (they already derive from the same constants).
    - The CSS declared height must equal the SVG's `height` attribute exactly — that equality is what makes the height term of the `min()` exactly 1.0.
    - Every emitted coordinate (polyline points, marker `cx`/`cy`, hit-target `cx`/`cy`, axis-label `x`/`y`) must fall inside the viewBox after the constants change.
  </behavior>

  <action>
Step 1 — derive the real container-width range from the CSS chain and record the arithmetic in a comment (do not rely on the single observed 846px number).

At >= 960px: `.dashboard-shell` is `grid-template-columns: 240px minmax(0, 1fr)` with `column-gap: var(--space-xl)` (32px), so the main column is `viewport - 272`. `.dashboard-main` then applies `max-width: min(1440px, 100%)` and `padding: var(--space-2xl) var(--space-3xl)` (48px / 64px), giving a content width of `min(1440, column) - 128`. `.battery-trend-section` adds `padding: var(--space-md)` (16px each side) plus its 1px border each side, so the SVG's containing block is `content - 34`.

Below 960px: `.page-content` applies `padding: var(--space-xl) var(--space-lg)`, so content is `viewport - 48` and the SVG container is `viewport - 82`.

Evaluated: 375px viewport → **293px**; 959px → 877px; 960px → 526px; 1280px → **846px** (this reproduces the orchestrating session's live 846px measurement exactly, which is the proof the derivation is right); >= 1568px → **1278px** (the 1440px `max-width` caps it — the range is genuinely bounded above). Real range: **293px … 1278px**, a 4.36x spread.

Step 2 — fix the mechanism, not the number. The defect is `.battery-trend-section svg:not(.icon) { width: 100%; height: auto; }`: with `width: 100%` and an auto height, the default `xMidYMid meet` uniform scale is `containerW / viewBoxW`, unbounded above, so every SVG-user-unit value (the 10px axis-label font size, `stroke-width: 2`, the r=3 markers, the r=8 hit targets) is multiplied by it. Replace the auto height with an explicit fixed pixel height equal to the SVG's own emitted `height` attribute. The scale then becomes `min(containerW / viewBoxW, 1)` — bounded at 1.00 by construction at every container width, present and future. Also emit an explicit `preserveAspectRatio="xMinYMid meet"` on the `<svg>` element so the spare horizontal room at wide widths lands to the right and the chart's left edge aligns with the card's text column, rather than being split by the `xMid` default. Fixed height has a second, free benefit: the card's height stops changing with viewport width.

Step 3 — reject the sketch's own strategy explicitly, in writing, in the CSS comment. The Merged Health Sketch pairs `preserveAspectRatio="none"` with a fixed CSS height, which does hold the vertical scale at exactly 1.0 — but it makes the horizontal scale `containerW / viewBoxW` independently, and over a 293-to-1278px container range that is 0.33x at a 375px viewport with a 900-wide viewBox. At 0.33x horizontal, the four axis labels' glyphs are squashed to a third of their natural width (illegible, overlapping) and the r=8 hit targets become 2.6px-wide slivers, breaking the D-02 tap targets phase 06.5 validated. The sketch's 900-wide viewBox is only ever near 1:1 around 900px, which is the only width it was ever viewed at. Uniform scaling with a 1.0 cap keeps glyphs and circles undistorted at every width; that is why it wins here.

Step 4 — choose the canvas constants against these criteria, and write the criteria into the comment beside them:
  (a) `viewBoxW <= 366`, so the narrowest real container (293px) still renders at >= 0.80 scale — this is what protects the 375px rendering, which measures 0.88 today and looks correct.
  (b) The CSS height must equal the emitted `height` attribute exactly.
  (c) The rendered chart height should stay under ~160px so the card does not dominate the page.
Recommended values, all of which satisfy the above: `_AXIS_LEFT_GUTTER` 34 → 44, `plot_width` 300 → 322 (giving `viewBoxW` 366), `plot_height` 60 → 106 (giving `viewBoxH` 120); leave `padding` at 4 and `_AXIS_BOTTOM_STRIP` at 14. The gutter change is its own small correction: 34 user units was sized for a "4200 mV"-shaped label at the 10px `.sparkline-axis-label` size, but seven characters at roughly 0.6em each plus the label's own `x="2"` inset needs about 44 — an under-measure that was invisible while everything was blown up 2.53x uniformly and will be visible for the first time at true 1:1. If you compute a different width for that label, use your number and record how you got it.

Step 5 — change ONLY the constants and the `<svg>` open tag. Every x/y/cx/cy in the function already derives from those constants; do not restate or re-tune any coordinate formula. Update `battery_sparkline_svg()`'s docstring where it describes the canvas, and update the `_AXIS_LEFT_GUTTER`/`_AXIS_BOTTOM_STRIP` block comment (it currently says "grown around the original 300x60 plot area", which stops being true).

Step 6 — rewrite the CSS rule's comment to record: the measured 846-in-a-334-viewBox 2.53x defect and where it came from (the canvas was calibrated when this chart lived inside a narrow `.stat-tile`, before 06.6.1's plan 03 moved it into its own full-width card, and was never recalibrated); the derived 293-1278px container range and its arithmetic; the `min(cW/vbW, 1)` bound; that the declared height MUST stay equal to the SVG's emitted height attribute or the bound silently breaks, and that a harness check pins that cross-file equality; and the `preserveAspectRatio="none"` rejection from Step 3. Keep the existing `:not(.icon)` reasoning intact — that exclusion is still load-bearing.

Step 7 — add ONE new harness check to `companion/test_status_pages.py`, in the section where the other sparkline checks live, that proves the whole bound from source: parse `viewBox`, `width`, `height` and `preserveAspectRatio` off a real `battery_sparkline_svg()` return value; assert the width/height attributes equal the viewBox dimensions; read `companion/static/style.css`, locate the `.battery-trend-section svg:not(.icon)` rule and parse its declared height in px; assert it equals the SVG's height attribute; then compute `min(cW/viewBoxW, cssH/viewBoxH)` for the derived container widths [293, 526, 846, 877, 1278] and assert every result is within [0.80, 1.00]; and finally assert every emitted coordinate (each polyline point pair, each `cx`/`cy`, each axis-label `x`/`y`) lies inside the viewBox box. Put the container-width derivation in the check's own comment so the numbers are not bare magic. Read the current on-disk `EXPECTED_CHECK_COUNT` and add exactly the number of checks you added, extending the running arithmetic comment above it in the file's established style.

Step 8 — mutation-test the new check before committing: temporarily make the CSS height disagree with the SVG height attribute by one pixel, confirm exactly this check fails and no other, then restore.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 -c "import re; from companion.pages import health_page as h; rows=[{'ts':'2024-01-01T0%d:00:00'%i,'battery_mv':4000+i*40} for i in range(5)]; s=h.battery_sparkline_svg(rows); m=re.search(r'viewBox=\"0 0 (\d+) (\d+)\"',s); w,ht=int(m.group(1)),int(m.group(2)); print('viewBox',w,ht); sc=[min(c/w,1.0) for c in (293,526,846,877,1278)]; print('scales',[round(x,3) for x in sc]); assert 366 >= w, 'viewBox too wide for the 293px container floor'; assert min(sc) >= 0.80 and 1.00 >= max(sc), 'scale outside [0.80, 1.00]'; assert 'preserveAspectRatio=' in s, 'expected an explicit preserveAspectRatio'; print('OK')"</automated>
  </verify>

  <done>
    `battery_sparkline_svg()` emits a viewBox no wider than 366 user units with matching width/height attributes and an explicit `preserveAspectRatio="xMinYMid meet"`; `.battery-trend-section svg:not(.icon)` declares a fixed pixel height equal to that height attribute; the computed scale factor is within [0.80, 1.00] at all five derived container widths; every emitted coordinate lies inside the viewBox; `companion/static/battery-trend.js` is unmodified; the status-pages harness is green at its bumped EXPECTED_CHECK_COUNT.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Give table headers real top padding (BUG 2 — 260901-uzi Finding 5, candidate a)</name>
  <files>companion/static/style.css, companion/test_status_pages.py</files>

  <read_first>
    - The "Finding 5 Verdict" section of `.planning/quick/260901-uzi-fix-4-confirmed-real-bugs-on-the-health-/260901-uzi-SUMMARY.md` — it names this exact mechanism and explains why that task declined to apply it blind. The developer's real Safari screenshot has now settled the question that task could not settle.
    - `companion/static/style.css`: the `.data-table th` rule (`padding: 0 var(--space-md) 10px` — literally zero top padding), the `.data-table-wrap th` rule immediately after it (`position: sticky; top: 0; background: var(--color-canvas); z-index: 1`) and the paired comment above them stating the two rules must always be edited together, and `.data-table td` (`padding: 13px var(--space-md)`) for the surrounding rhythm.
  </read_first>

  <behavior>
    - The `.data-table th` rule declares a non-zero top padding.
    - The bottom padding keeps its existing value, so the header's optical relationship to its own bottom hairline is unchanged.
    - Both header padding values are symmetric, so the header's text sits centred in its own band.
  </behavior>

  <action>
Apply candidate (a) from 260901-uzi's verdict: add real top padding to `.data-table th`. Mirror the existing bottom value rather than inventing a new one — `padding: 10px var(--space-md);` — which adds breathing room above the glyphs while leaving the existing 10px bottom (and therefore the header's relationship to its own `border-bottom` hairline) byte-identical. Prefer this over a `--space-*` token substitution: the bottom value is already a bare 10px in this rule, and swapping the bottom to 8px or 16px to "use a token" would change a value nobody reported a problem with, on four tables at once.

Name the real mechanism in the rule's comment, because it is not "sticky positioning clips text" — sticky never clips. `.data-table-wrap th` paints an opaque background over the header's padding box; with zero top padding, that opaque box begins exactly at the glyph tops, so rows scrolling underneath a stuck header reach the ascenders before any background covers them, and whether that reads as clipping depends on where the font's ascent sits inside the line box — metrics that genuinely differ between WebKit and Blink, which is exactly why the developer reproduced this in Safari while a Chromium-based measurement tool did not. Real top padding extends the opaque background above the glyphs, so the fix does not depend on any font's ascent metric in any engine. Record that this closes 260901-uzi's Finding 5 candidate (a), and that candidate (b) — the sticky background token — is deliberately NOT changed here: it remains open, still correctly reasoned in its own comment, and is a separate one-declaration decision with its own risk to History's table.

Record the blast radius in the comment: this rule is shared by History's table, the Health battery-readings table, the Resolution-statistics table and the hand-rolled unresolved-prefix registry table (which emits `<table class="data-table">` directly). All four re-space together by 10px of header height. That is intended — a uniform improvement, not a Health-only patch — and it is why the change belongs on the shared rule rather than on a Health-scoped override.

Add ONE harness check pinning both halves of the contract: that `.data-table th` declares a non-zero top padding, and that its top and bottom padding values are equal (so a future edit cannot silently return the top to zero or drift the two apart). Parse the declaration from `companion/static/style.css` rather than string-matching a whole literal rule body, so the check survives an unrelated reformat. Bump `EXPECTED_CHECK_COUNT` from its current on-disk value and extend the running arithmetic comment. Mutation-test it (temporarily restore a zero top padding, confirm only this check fails) before committing.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 -c "import re; css=open('companion/static/style.css').read(); m=re.search(r'\.data-table th \{[^}]*padding:\s*([^;]+);',css); v=m.group(1).split(); print('padding:',v); assert len(v)==2, 'expected a symmetric two-value padding shorthand'; assert v[0].rstrip('px').isdigit() and int(v[0].rstrip('px'))>0, 'top padding must be a non-zero px value'; print('OK')"</automated>
    <automated>server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>

  <done>
    `.data-table th` declares a symmetric, non-zero vertical padding; the rule's comment names the opaque-background mechanism, the four-table blast radius, and that this closes 260901-uzi Finding 5 candidate (a) while leaving candidate (b) explicitly open; a harness check pins both the non-zero top and the top/bottom equality; the status-pages and view-pages harnesses are green.
  </done>
</task>

<task type="auto">
  <name>Task 3: Resolve the recurring stat-tile type-hierarchy complaint, for real</name>
  <files>companion/static/style.css, companion/test_status_pages.py</files>

  <read_first>
    - `Skill("sketch-findings-skypane")` — the four-size scale (14 / 16 / 20 / 30), the Emphasis role ("existing size made bold", 16px + `--weight-semibold`), the documented sub-scale exception tier, and the named `.stat-tile__caption` serif exception which "declares no font-size of its own (inherits `.text-label`'s 14px)" after the source sketch's 15px was superseded.
    - `companion/static/style.css`: `.stat-tile__caption`, `.stat-tile__value`, `.page-section--nested > h2, .battery-trend-section > h2` and its long comment, `.text-heading`, `.text-label`, and the `h1, h2, h3, .text-heading` serif rule.
    - `companion/pages/health_page.py`'s `render()` tail (the `server_data_section_html` composition) and `companion/layout.py`'s `stat_tile()` (the caption is emitted as `<p class="text-label stat-tile__caption">`).
    - The "Finding 4" key-decision in 260901-uzi's SUMMARY (why `.stat-tile__value` was deliberately not resized).
  </read_first>

  <action>
Two prior rounds (260901-uzi finding 4, 260902-bl2) concluded the type-scale math was correct per D-09 and left this alone. That answer is not available a third time. Something concrete changed yesterday and today, and the investigation must engage with it.

Step 1 — enumerate, from source, the exact current treatment of every text role stacked in the "Server & data" region, and write the table into the SUMMARY:
  - section heading (`h2.text-heading` via `_section_intro_html`): 20px, regular, serif
  - stat-tile caption (`p.text-label.stat-tile__caption`): 14px, regular, serif (the named Label-role serif exception)
  - stat-tile value (`p.stat-tile__value`): 16px, semibold, sans (`--font-ui`, inherited)
  - nested card title (`.page-section--nested > h2`): 16px, semibold, serif — demoted here from 20px regular by 260901-uzi's finding 4, i.e. within the last 24 hours
Confirm each of those four from the actual rules rather than from this list.

Step 2 — the leading hypothesis to accept or refute, stated concretely so it cannot be answered by restating D-09:
  (i) The tile value (16 semibold sans) and the nested card title (16 semibold serif) are now IDENTICAL in both size and weight, separated only by font family, and they sit adjacent in one region — three tiles beside two nested cards. Note the collision is stronger than "same size": the demotion also made the nested title semibold.
  (ii) Two elements playing the SAME structural role — the title of a card — now render at two different tiers: 14px regular serif for a stat tile, 16px semibold serif for a nested card. The developer's complaint is literally that a tile's caption/title reads smaller and less prominent than other headings on the page. That is now measurably true of two things that are structurally peers, and it became true when the nested tier moved.
Judge whether (i), (ii), both, or neither is the real defect.

Step 3 — if you conclude a change is warranted, choose from these levers only. D-09 retired the Display role and restored a four-size scale; introducing a fifth size, or a new token, is prohibited. Weight, family, colour, letter-spacing and spacing are all available, and the design skill's own sub-scale exception tier is a documented precedent for going below the scale, never above it.
  - Option A (the strongest candidate): promote `.stat-tile__caption` to `--weight-semibold`, keeping 14px and serif. The caption gains card-title weight and stops reading as the weakest thing in the region, while staying below both the nested card title (16 semibold) and the tile's own value (16 semibold), so the datum remains the loudest thing in the tile. One declaration, no new size, no new token. Blast radius, already measured during planning: `layout.stat_tile()` has exactly 11 call sites — 10 in `health_page.py` and 1 in `history_page.py` — so this touches Health's tiles and one History tile and nothing else.
  - Option B: differentiate the tile value from the nested card title without a size change (colour or letter-spacing on one of them). Weaker: it treats the symptom of (i) and leaves (ii) untouched.
  - Option C: adjust the nested card title's own treatment instead — but note it may only move within the existing scale, so its only real moves are weight and family, not "somewhere between 14 and 20".
  - Option D: no change. Permitted ONLY with the written verdict Step 4 requires.
Whatever you choose, write into the rule's comment: which of (i)/(ii) it addresses, why the alternatives were rejected, and that no fifth size was introduced.

Step 4 — a verdict is mandatory either way, in the SUMMARY, under a heading a reader can find. If you ship a change, state which hypothesis it addresses and what the developer should look for in the next Safari pass. If you ship nothing, you must name the alternative hypothesis with source evidence, explain specifically why (i) and (ii) are not the defect despite what changed yesterday, and pose the one concrete question the developer should answer to settle it. "D-09's math is correct" on its own is not a verdict — that answer has already been given twice and did not resolve the complaint.

Step 5 — if a CSS change ships, pin it with ONE harness check (assert the declared value on the rule you changed, and assert the four roles' relative sizes/weights still hold as a set, so a future edit cannot silently flatten them again). Bump `EXPECTED_CHECK_COUNT` from its current on-disk value and extend the running arithmetic comment. Mutation-test it before committing. If nothing ships, add no check and say so explicitly in the count comment's arithmetic, exactly as 260901-uzi did for its own finding 5.

Step 6 — run the full suite and confirm the only failure is the known one.

Non-goal: do not update the `sketch-findings-skypane` skill file in this task. The four preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc) all deferred that, and folding five tasks' worth of design-system deltas into the skill is its own piece of work, not a rider on this one.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 companion/test_contrast_check.py</automated>
    <automated>scripts/run-all-tests.sh</automated>
  </verify>

  <done>
    The four Server & data text roles are enumerated from source; a written verdict on hypotheses (i) and (ii) exists in the SUMMARY under a findable heading; either a CSS change shipped (within the four-size scale, no new token, pinned by a harness check and explained in its rule comment) or a precise negative finding was recorded naming the alternative hypothesis and the one question that would settle it; `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing `server/test_poll_loop.py` panel.bin digest mismatch, with no coverage-gate shortfall.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| device/attacker → history DB → server-rendered SVG | `battery_mv` and `ts` values reach `battery_sparkline_svg()` and are interpolated into SVG attributes and text nodes |
| server-rendered DOM → battery-trend.js | `data-mv` / `data-ts` / `data-when` attributes cross into client script |
| stylesheet → every page | `.data-table th` is shared by four tables across three pages |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-dng-01 | Tampering (injection) | `battery_sparkline_svg()` attribute/text interpolation | high | mitigate | Only numeric canvas constants and one static `preserveAspectRatio` literal change; every attacker-influenced value (`ts`, the axis clock labels, the humanised `when`) keeps its existing `escape_html()` call at the point of interpolation. No new interpolation site is introduced. |
| T-dng-02 | Tampering | `companion/static/battery-trend.js` | medium | accept | The file is not edited. It was read in full during planning and recomputes no geometry, so the canvas resize cannot desynchronise it; `textContent` remains its only content sink and 06.5-RESEARCH.md's ASVS V5 reasoning is untouched. |
| T-dng-03 | Denial of service | SVG element count | low | accept | Point count is bounded by `BATTERY_TREND_LIMIT`, unchanged by this task; the canvas resize changes coordinate values, never element counts. |
| T-dng-04 | Information disclosure | `.data-table th` opaque background | low | mitigate | Adding top padding extends the header's own opaque background upward; it reveals no additional data and cannot expose a row that was previously covered. Row content scrolling under a stuck header is covered strictly earlier than before, not later. |
| T-dng-05 | Repudiation | design-question verdict | medium | mitigate | Task 3 mandates a written verdict in the SUMMARY whether or not code ships, so a third silent deferral is not a reachable outcome. |
| T-dng-SC | Tampering (supply chain) | npm/pip/cargo installs | high | accept | Zero package installs in this task — CSS declarations, Python integer constants and harness checks only. No `## Package Legitimacy Audit` is required because no install task exists. |
</threat_model>

<source_audit>
Quick-task mode: the sources are the developer's task brief and 260901-uzi's SUMMARY, not ROADMAP/REQUIREMENTS/RESEARCH/CONTEXT artifacts.

| # | Source item | Covered by | Status |
|---|-------------|-----------|--------|
| BRIEF-01 | BUG 1: chart renders ~2.5x oversized | Task 1 | COVERED |
| BRIEF-02 | Read `battery_sparkline_svg()` in full; find real `_AXIS_*` values | Task 1 read_first (done during planning: 34 / 14) | COVERED |
| BRIEF-03 | Read the real responsive container-width range from `.page-content`/`.dashboard-main`, not one observed number | Task 1 Step 1 (293-1278px derived) | COVERED |
| BRIEF-04 | Consider the sketch's `preserveAspectRatio="none"` + fixed-height strategy | Task 1 Step 3 — evaluated with real numbers and rejected in writing, with the mobile 0.33x distortion as the reason | COVERED |
| BRIEF-05 | Keep coordinate math / axis labels / hit-target `cx`,`cy` internally consistent | Task 1 Steps 5 + 7 (coordinates-inside-viewBox assertion) | COVERED |
| BRIEF-06 | Read `battery-trend.js` in full; confirm no hardcoded geometry | Done during planning — confirmed attribute-only, no edit needed | COVERED |
| BRIEF-07 | BUG 2: table headers clip at the top; add real top padding | Task 2 | COVERED |
| BRIEF-08 | Confirm the shared-rule blast radius before changing it | Task 2 (four tables enumerated: History, readings, stats, registry) | COVERED |
| BRIEF-09 | Design question: investigate the 16px collision hypothesis concretely | Task 3 Steps 1-2 (both hypothesis (i) and the stronger (ii)) | COVERED |
| BRIEF-10 | Reach a real resolution — change or precise negative finding, not a fourth deferral | Task 3 Step 4 (mandatory verdict) + T-dng-05 | COVERED |
| BRIEF-11 | Do not touch: tile gaps, Health/Settings h1/h2 | `<context>` do-not-touch list; no task modifies `.dashboard-grid` gaps, `.page-title` or `.text-heading` | COVERED |
| BRIEF-12 | Harness stays green; `EXPECTED_CHECK_COUNT` computed live from the on-disk baseline | Every task's verify + explicit "read the current on-disk value" instruction | COVERED |
| BRIEF-13 | Run `scripts/run-all-tests.sh`; only the known `server/test_poll_loop.py` failure remains | Task 3 verify + done | COVERED |
| BRIEF-14 | Automated verification of the new SVG geometry, not just non-empty output | Task 1 Step 7 (scale-ratio assertion across five widths + coordinate bounds) | COVERED |
| BRIEF-15 | Be explicit about what still needs a live browser | `<verification>` below | COVERED |
| BRIEF-16 | Atomic commits in the existing style, referencing 260902-dng | `<commits>` below | COVERED |

No unplanned items.
</source_audit>

<verification>
## Automated (this executor, required)

1. `server/.venv/bin/python3 companion/test_status_pages.py` after every task — green at its own bumped `EXPECTED_CHECK_COUNT`.
2. Each new check mutation-tested (one bogus literal each) and confirmed to fail alone before being restored.
3. `scripts/run-all-tests.sh` at the end — exactly one failing harness, the pre-existing and unrelated `server/test_poll_loop.py` panel.bin digest mismatch, and no coverage-gate shortfall.
4. Optional but recommended, matching 260901-uzi's precedent: start a real `companion/app.py` subprocess against a seeded state dir, sign in over HTTP, and fetch `/health` and `/static/style.css` to confirm the served bodies actually carry the new viewBox, the new `preserveAspectRatio`, the fixed SVG height and the new header padding.

## Live browser — the orchestrating session's job, NOT this executor's

No browser-automation tools are bound to this subagent, matching all four preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc), each of which handed pixel-level confirmation back to the orchestrating session, which performed it successfully. Do not claim any of the following as verified.

1. **The chart's real rendered scale ratio is now ~1.0, not just arithmetically bounded.** Measure the SVG's `getBoundingClientRect().width` and divide by its `viewBox` width. Expected: ~1.00 at a 1280px viewport (the same measurement that returned 2.53 before this task), and never above 1.00 at any width. This is the single most important confirmation in this task — the harness proves the arithmetic, only a browser proves the arithmetic describes the real rendered box.
2. **The chart still looks right at 1:1.** Axis labels legible at their true 10px and not colliding with the plot's left edge (the `_AXIS_LEFT_GUTTER` change is a planning-time estimate of the "4200 mV" label's real width — a browser is what confirms it); the polyline reading as a trend rather than a hairline; markers and hit targets visibly circular.
3. **The chart does not read as under-filled.** At 1:1 the chart occupies roughly 366 of a ~846px card at 1280px, left-aligned under the readout. If that reads as an empty card rather than a deliberate chart column, that is a real finding and the next lever is the card's own layout — not raising the scale cap above 1.0, which is what caused this bug.
4. **375px re-check.** The chart should render at ~0.80 scale with everything still legible, i.e. no regression from today's 0.88.
5. **Real Safari, the readings disclosure.** Open it and confirm the header clipping is gone. This is the confirmation 260901-uzi's Finding 5 verdict explicitly asked for and could not obtain.
6. **All four tables re-spaced acceptably.** History, Airlines, and Health's three tables each gain 10px of header height — confirm none of them now reads as loose.
7. **The type-hierarchy verdict, judged by eye.** Whether the region now reads with a clear hierarchy is a human judgment, not a measurement. If Task 3 shipped a change, confirm the tile caption no longer reads as the weakest heading while the tile's value stays the loudest thing in its tile.
8. **Still outstanding from prior rounds, unchanged by this task:** the chart's hover/tap/arrow-key interactive readout path, and a dark-theme pass.
</verification>

<commits>
One focused commit per task, matching the session's established style (`git log --oneline -10`), referencing the quick task id rather than a phase-plan number:

1. `fix(quick-260902-dng): bound the battery-trend chart at 1:1 scale`
2. `fix(quick-260902-dng): give table headers real top padding`
3. `fix(quick-260902-dng): <the Task 3 change>` — or, if Task 3 ships no CSS change, `docs(quick-260902-dng): resolve the stat-tile type-hierarchy question` for the verdict alone.

Harness edits ride with the change they pin (each commit leaves the suite green at its own count), matching 260902-bl2's and 260902-chc's pattern rather than uzi's separate test task.
</commits>

<success_criteria>
- The battery-trend chart's effective scale factor is within [0.80, 1.00] across the derived 293-1278px container range, proven by a harness check that reads both the SVG attributes and the CSS declaration.
- The cross-file equality between the CSS declared height and the SVG's emitted height attribute is pinned by a test, so the bound cannot silently break.
- `companion/static/battery-trend.js` is unmodified.
- `.data-table th` declares a symmetric, non-zero vertical padding, with the opaque-background mechanism and the four-table blast radius recorded in its comment.
- 260901-uzi's Finding 5 is explicitly closed for candidate (a) and explicitly left open for candidate (b).
- A written verdict on the type-hierarchy question exists, engaging with the 16px size-and-weight collision that appeared yesterday rather than restating D-09.
- `companion/test_status_pages.py` green at its bumped count; `scripts/run-all-tests.sh` shows only the known `server/test_poll_loop.py` failure.
- Three atomic commits referencing 260902-dng.
</success_criteria>

<output>
Create `.planning/quick/260902-dng-fix-2-confirmed-severe-real-bugs-on-the-/260902-dng-SUMMARY.md` when done.

It must contain, beyond the standard sections: the derived container-width table and the resulting scale factors; the canvas constants chosen and why; the `preserveAspectRatio="none"` rejection; the Task 3 verdict under its own findable heading; and a "Pixel-Level Items Outstanding" section reproducing the live-browser list above for the orchestrating session's pass.
</output>
</content>
</invoke>
