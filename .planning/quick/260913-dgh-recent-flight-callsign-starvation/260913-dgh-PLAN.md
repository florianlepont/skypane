---
phase: quick/260913-dgh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
  - companion/test_browser_ux.py
  - companion/test_view_pages.py
  - .claude/skills/sketch-findings-skypane/references/data-density.md
autonomous: true
requirements: []          # Decision-point-tracked quick task, the precedent every 06.x/quick plan
                          # in this repo follows. Traceability is via `decisions` below.
closes: none              # Not an audit finding. A fourth, independent site of the content-sized-track
                          # cause `references/data-density.md` has now recorded three times, found by
                          # the developer on Accueil after 260913-bjy closed B11 on the same component.

decisions:
  - D-01  # The cause is confirmed and sharpened: `.recent-flight`'s `minmax(0, 1fr)` callsign track
          # is the ONLY yielding track in the row, and its explicit 0 floor lets it yield to nothing.
          # The starved element never leaves its row or the viewport, so every existing overflow
          # assertion in this repo — including 260913-bjy's own row-box sweep — is blind to it.
  - D-02  # The brief's framing is REFUTED in two places, on measurements, not on taste. (a) It is not
          # a clip: nothing declares overflow:hidden, the box collapses and the TEXT paints over the
          # time beside it. (b) It is not a phone-only defect: the 1280px row is 292.4px with 7.5px of
          # slack, and with the age grown to "il y a 365 j" the desktop starves too.
  - D-03  # REJECT the container query, after measuring that it works. Its threshold is a fixed number
          # and the content it must clear has no ceiling (layout.relative_age_text()'s day bucket).
          # Any threshold covering the 292.4px desktop row charges the second line at 1280px forever.
  - D-04  # TAKE a wrapping flex line on `.recent-flight` — a THIRD distinct remedy for this cause,
          # neither the stacked-cell exception nor the floor-release. Flex line breaking runs on the
          # items' own content widths, so it asks "does this fit" instead of naming a width.
  - D-05  # REJECT `minmax(min-content, 1fr)`: measured, it trades the starvation for Home's horizontal
          # scrollbar at 320px (doc.scrollWidth 343 FR / 335 EN) — the exact B11 defect 260913-bjy closed.
  - D-06  # REJECT releasing the time's one-line contract: measured, it changes the resolved tracks by
          # literally nothing, because a grid `auto` track never consults min-content. It ships inert.
  - D-07  # NO markup change to home_page.py, and no new user-facing string. CFG-29/CFG-30 cannot regress.
  - D-08  # The new browser check measures the callsign box against its OWN text via a Range, at 320,
          # 360, 390, 768 AND 1280px in both languages — the first check in this repo to measure a box
          # against its content rather than against a container.

must_haves:
  truths:
    - "`.recent-flight__callsign`'s box is never narrower than its own text at 320, 360, 390, 768 or 1280px, in BOTH languages"
    - "Home still never scrolls sideways at any of those widths — the fix must not buy the callsign's width from the page"
    - "At 768px, where the row is 686px, the callsign and the time still share ONE line"
    - "The detail line still starts at the callsign's own left edge, never back under the thumbnail"
    - "The time is still right-aligned to the row, on one line or two"
    - "B18's one-line contract on the clock/age pair is preserved verbatim and still pinned by its own check"
    - "The new browser check is proven non-vacuous by reverting the CSS and watching only it go red, at 320px AND at 360px"
    - "EXPECTED_CHECK_COUNT re-derived by RUNNING the harness, never by arithmetic"
    - "companion/static/style.css still carries zero stray comment terminators"
    - "No test exception is added anywhere; scripts/run-all-tests.sh matches the documented sandbox baseline"
  artifacts:
    - "companion/static/style.css — `.recent-flight` becomes a wrapping flex line; `.recent-flight__detail` and `.recent-flight__time` re-express their grid placement in the new mechanism, with this task's own numbers in the comment"
    - "companion/test_browser_ux.py — one new check, +1, and a re-derived EXPECTED_CHECK_COUNT"
    - "companion/test_view_pages.py — the B18 nowrap guard's ANCHOR retargeted (it anchored on the grid-only self-alignment this task removes); the assertion itself unchanged"
    - ".claude/skills/sketch-findings-skypane/references/data-density.md — records this as the cause's FOURTH site and a THIRD distinct remedy, with the container query's rejection argued on its numbers"
  key_links:
    - "A rigid `auto` track beside a `minmax(0, 1fr)` track -> the flexible one absorbs every shortfall and is floored at zero. Grid has nowhere to put what does not fit; a wrapping flex line does."

deliberate_acts:
  - "This introduces the FIRST container-query consideration in this codebase — and deliberately does
     NOT ship one. The brief proposed it as the honest instrument, and it IS the right instinct: the
     row width is 238/278/308/686/292.4px at 320/360/390/768/1280px viewports, so no media query can
     express the condition. The container query was therefore built and measured rather than waved
     away. It was rejected because its threshold is a constant and the content it must clear grows
     without bound. If a future task does introduce one, that will still be its first use here."
  - "`.recent-flight` changes layout MECHANISM, grid to flex. That is a bigger move than a declaration
     tweak and is called out as such. It is justified only by the measurement that grid cannot express
     the fix: every grid remedy measured either starved the callsign, overflowed the page, shipped
     inert, or charged 23.6px of row height at a width with 686px of room."
---

<objective>
On Accueil, `.recent-flight__callsign` is starved to nothing by the time column at
narrow row widths. Measured in a real Chromium against the seeded fixture: a 10.9px
(FR) / 18.6px (EN) box for 57.8px of content at a 320px viewport, and 50.9px (FR)
at 360px — a common Android width.

Fix it at the cause, measure every candidate treatment at 320/360/390/768/1280 in
both languages before choosing, and add the browser-harness check that measures the
box against its own CONTENT — a quantity nothing in this repo has measured before.
</objective>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/references/data-density.md
@companion/static/style.css
@companion/pages/home_page.py
@companion/test_browser_ux.py
@companion/test_view_pages.py
</context>

<measurement>
Reproduced before changing anything, with a real Chromium tab against a real
`companion/app.py` subprocess, at 320/360/390/768/1280 x two languages. Baseline —
every number in the brief confirmed, and two it did not have:

  vw    lang  row w    grid-template-columns          callsign box / content
  320   FR    238      40px 10.89px 155.11px          10.89 / 57.80   STARVED
  320   EN    238      40px 18.64px 147.36px          18.64 / 57.80   STARVED
  360   FR    278      40px 50.89px 155.11px          50.89 / 57.80   STARVED
  360   EN    278      40px 58.64px 147.36px          58.64 / 57.80   ok
  390   FR    308      40px 80.89px 155.11px          80.89 / 57.80   ok
  390   EN    308      40px 88.64px 147.36px          88.64 / 57.80   ok
  768   FR    686      40px 458.89px 155.11px        458.89 / 57.80   ok
  768   EN    686      40px 466.64px 147.36px        466.64 / 57.80   ok
  1280  FR    292.39   40px 65.28px 155.11px          65.28 / 57.80   ok, 7.5px of slack
  1280  EN    292.39   40px 73.03px 147.36px          73.03 / 57.80   ok

Two corrections to the brief, both measured:

1. **It is not a clip.** Nothing here declares `overflow: hidden`. The BOX collapses
   and the TEXT paints out of it, over the time beside it. At 320px the rendered row
   reads `AFR135ût 00:31` — two strings overprinting, glyph for glyph.
2. **It is not phone-only.** The 1280px row is 292.4px and the callsign track has
   7.5px of slack. `layout.relative_age_text()`'s day bucket has no ceiling, so the
   age string only ever grows. Re-measured with the age forced to "il y a 365 j",
   the 1280px FR track falls to **57.5px for 57.80px of content** — the desktop
   starves too. It was always about one character away.

Six candidate treatments were then measured, not argued. "starve" = worst callsign
box deficit against its own content, FR unless stated; "rowH" = row height:

  treatment                       320    360    390   768   1280   page overflow   rowH 768
  (baseline)                      -46.9  -6.9    ok    ok    ok     none            87.59
  (A) minmax(min-content, 1fr)     ok     ok     ok    ok    ok     YES at 320px    87.59
  (B) container query @300px       ok     ok     ok    ok    ok     none            87.59
  (C) container query @340px       ok     ok     ok    ok    ok     none            87.59
  (D) release nowrap under (B)    -46.9  -6.9    ok    ok    ok     none            87.59
  (E) wrapping flex line           ok     ok     ok    ok    ok     none            87.59
  (F) time always on its own line  ok     ok     ok    ok    ok     none           111.19

  (A) REJECTED. It stops the starvation and immediately reintroduces Home's
      horizontal scrollbar at 320px: the row grows to 284.91px inside a 238px column
      and documentElement.scrollWidth goes to 343 (FR) / 335 (EN) against 320. That
      is the exact B11 defect quick task 260913-bjy closed six hours ago. A grid row
      has nowhere to put what does not fit, so widening the floor only moves the
      overflow onto the page.
  (B) REJECTED, though it works. See the threshold argument below.
  (C) REJECTED. Same as (B), and it additionally costs the second line at 390px,
      where the row is 308px and the content needs 284.91px.
  (D) REJECTED as INERT. It changed the resolved tracks by literally nothing — the
      measured template is byte-identical to the baseline at every width. A grid
      `auto` track is sized from max-content and never consults the min-content that
      releasing `white-space: nowrap` lowers. This is the same dead-declaration class
      the design-system notes retired the sticky header for, caught before shipping.
  (F) REJECTED. Fits everywhere, and charges every row 23.6px of extra height at
      768px, where there are 686px of room and nothing to fix.
  (E) CHOSEN.

**Why the container query loses, measured rather than asserted.** It is the right
instinct: the viewport genuinely does not predict the row width (238/278/308/686/
292.4px at 320/360/390/768/1280), so a media query cannot express this condition. It
was therefore built and measured, not waved away. It loses on one property: a
container query needs a hard-coded px threshold, and the content that threshold must
clear has no upper bound. Any threshold that covers the 292.4px desktop row — and it
must, since the desktop starves once the age grows — pays the second line at 1280px
unconditionally, in both languages, forever. Measured directly:

  age string          treatment   1280/FR                  1280/EN
  "il y a 42 j"       (B) @300px  two lines (111.19)       two lines (111.19)
  "il y a 42 j"       (E) flex    ONE line (87.59)         ONE line (87.59)
  "il y a 365 j"      (B) @300px  two lines (111.19)       two lines (111.19)
  "il y a 365 j"      (E) flex    two lines (111.19)       ONE line (87.59)

The last row is the whole argument. Flex line breaking runs on the items' own content
widths, so it wraps in French and does not wrap in English, at the same viewport, for
the same fixture — a per-language, per-content answer no fixed threshold can give.
`.status-row` in this same stylesheet already ships flex + wrap + baseline, so this
joins an existing pattern rather than inventing one.

**Post-fix, both languages, callsign box against callsign content:** 57.80 for 57.80
at 320, 360, 390, 768 and 1280 — starved at no width in either language. The second
line appears only at 320px (both languages) and 360px in French. Geometry is
otherwise byte-for-byte the old grid placement: the detail line still starts at
row.left + 56px, the time's right edge is still row.right.
</measurement>

<tasks>

<task type="auto">
  <name>Task 1: Give the row somewhere to put the overflow, and pin it with a check that measures a box against its own content</name>

  <action>
  1. `companion/static/style.css`, `.recent-flight`: replace `display: grid` +
     `grid-template-columns: 40px minmax(0, 1fr) auto` with `display: flex` +
     `flex-wrap: wrap`. Gap, baseline alignment, padding and border are unchanged.
     Carry this task's own numbers in the comment, including the three rejected
     treatments and the container query's rejection reason. Do NOT write `*`
     followed by `/` anywhere inside that comment, and put no `{` in it either —
     `test_view_pages.py`'s nowrap guard walks backwards to the nearest brace.
  2. `.recent-flight__detail`: re-express `grid-column: 2 / -1; grid-row: 2` in the
     new mechanism — `order: 1` (it is the THIRD child, the time is the fourth, so
     without the bump flex paints them the other way round), `flex: 1 1 100%`, and
     `margin-inline-start: calc(40px + var(--space-md))` to reproduce the old
     column-2 start exactly.
  3. `.recent-flight__time`: replace the grid-only `justify-self` with an auto
     inline-start margin. `white-space: nowrap` is untouched — B18's contract stands.
     Append the correction to that rule's existing comment INSIDE the block, noting
     that the rejected wrapping-flex experiment recorded there was a flex container
     INSIDE this item and is a different thing from the row wrapping around it.
  4. `companion/test_view_pages.py`: the B18 nowrap guard anchors on the declaration
     step 3 removes, and asserts it is unique. Retarget the anchor to the auto
     inline-start margin, re-verified unique. The assertion itself must not change,
     and the anchor must stay a DIFFERENT declaration from the assertion.
  5. `companion/test_browser_ux.py`: one new check — at 320, 360, 390, 768 and
     1280px, in BOTH languages, on Accueil, assert every `.recent-flight__callsign`
     box is at least as wide as a `Range` over its own contents. Not `scrollWidth`,
     which rounds to an integer and reports 81 for an 80.89px box. Also assert
     `documentElement.scrollWidth <= viewport` (so the fix cannot be bought from the
     page, guarding treatment A), and at 768px only, that the callsign and the time
     still share one line (guarding treatment F). Same-line means their boxes OVERLAP
     VERTICALLY, never equal tops — the row is baseline-aligned and the time renders
     at the smaller label size, so two items on the same line differ by 3px at the top.
     Assert a non-zero row count and one callsign per row so it cannot pass vacuously.
  6. Re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness.
  7. Mutation-test: revert the three CSS rules, confirm the new check FAILS naming the
     starved callsign with its box and content widths, at 320px AND (widths list
     temporarily narrowed) at 360px, then restore and confirm byte-identity and a pass.
  8. `.claude/skills/sketch-findings-skypane/references/data-density.md`: record this
     as the cause's FOURTH site and a THIRD distinct remedy — explicitly NOT the
     stacked-cell exception (consumer count stays at two) and NOT the floor-release.
  </action>

  <verify>
  `./scripts/run-all-tests.sh` matches the documented sandbox baseline of exactly 5
  failing checks (4 x WR-11 read-only, 1 x `anomaly_active()`), by NAME.
  </verify>

  <done>
  The callsign is never narrower than its own text at any of the five widths in either
  language, Home still never scrolls sideways, the time still shares the first line
  wherever there is room for it, and a check exists that goes red the moment either
  property stops holding.
  </done>
</task>

</tasks>

<hard_constraints>
- Do NOT release B18's one-line contract on the clock/age pair.
- Do NOT ship a container query. It was measured, it works, and it is rejected above.
- Do NOT change `companion/pages/home_page.py`. No markup change, no new string.
- Never add a test exception. The suite carries none.
- `companion/static/style.css` must keep zero stray comment terminators.
- No new user-facing string, so no new French catalogue entry — CFG-29/CFG-30 must not regress.
- Do NOT touch ROADMAP.md. Update STATE.md's "Quick Tasks Completed" table only, and
  do not reintroduce a second YAML frontmatter block or delete the quoted historical one.
- Do NOT settle whether 320px is a supported width. State what the fix does and does
  not achieve there and leave the decision to the developer.
</hard_constraints>
