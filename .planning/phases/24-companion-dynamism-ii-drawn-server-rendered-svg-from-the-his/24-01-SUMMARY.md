---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 01
subsystem: ui
tags: [svg, server-rendered, geometry, battery-estimate, theme-tokens, contract-test]

requires:
  - phase: 19-01
    provides: "companion/battery.py — the shared, stdlib-only battery estimate created so home_page.py and health_page.py could share one number without importing each other. Extended here, never replaced."
  - phase: 06.5 / 260902-ep7 / 260902-l0b
    provides: "health_page.battery_sparkline_svg()'s no-viewBox percentage scheme, its filled-rect axis chrome, its n-1 line segments and its pair-before-filter technique — the code draw.py generalises"
  - phase: 23-01
    provides: "the motion budget (two tokens, four keyframes, one @supports selector(:has(*)) block) this plan spends nothing from"
provides:
  - "companion/battery.py extended: battery_fraction() (the 0..1 a gauge needs) and LOW_BATTERY_DISPLAY_MV, both derived from the same ratio battery_percent() returns"
  - "companion/draw.py — stdlib-only geometry and emission primitives; two separately-named coordinate schemes, one escaping helper, one single-pass pair filter, shape emitters that refuse to emit unclassed or coloured"
  - "the .drawing* CSS vocabulary beside .sparkline*, painting only through currentColor and existing tokens, with a size route per scheme"
  - "eight harness checks (Section 2.8 of companion/test_companion_app.py) that make the drawing contract executable"
affects: [24-04, 24-05, 24-06, 24-07, 24-08, 24-09]

tech-stack:
  added: []
  patterns:
    - "Two coordinate schemes as two separately-named helper families (percent_* / unit_*), never one helper with a use_viewbox= flag — a flag is how the two get mixed inside one drawing"
    - "Two canvas classes, one per scheme: .drawing__canvas declares a size, .drawing__figure deliberately declares none so intrinsic viewBox attributes survive"
    - "A class-resolution check matched on a SELECTOR BOUNDARY, because .drawing-axis is a substring of .drawing-axis-label"
    - "Source scans read the AST where possible and a comment/docstring-stripped token stream otherwise — this phase's own prose quotes the tokens being measured"
    - "An allow-list of exactly two, each with its own written justification, instead of a blanket 'one home' claim the tree cannot support"

key-files:
  created:
    - companion/draw.py
  modified:
    - companion/battery.py
    - companion/static/style.css
    - companion/test_companion_app.py

key-decisions:
  - "The exclusivity check allow-lists server/poll_loop.py's private battery copy by name rather than failing on it — the plan's 'exactly one module' premise was wrong about server/, and the copy is architecturally required (the server package may never import the web-app package, D-27)."
  - "health_page.battery_sparkline_svg() was NOT rewired. The plan's files_owned forbids touching companion/pages/*.py and the frontmatter excludes it; equivalence is proven instead by a check that reads the shipped chart's own emitted coordinates back and compares them to draw.percent_y(). Adoption is 24-05's, which edits that function anyway."
  - "LOW_BATTERY_DISPLAY_MV is derived (3300 + 20% of the span = 3480), not typed, so the line a chart draws and the percentage printed beside it can never tell two different stories."
  - "draw.py does not import companion/battery.py even though it may — geometry does not need to know what it is plotting."
  - "The ring gauge's arc is a dashed circle, not an arc <path>: a full-sweep arc is degenerate in SVG and draws nothing, so an arc-path gauge reads 100% as empty."
  - "_attrs() refuses paint and loading attributes but ESCAPES everything else — refusing a text value would turn a page render into an exception for a value the app cannot control."

patterns-established:
  - "Every primitive carries the REASON it is shaped that way in its own docstring, not just the arithmetic — a primitive without its reason gets re-derived wrongly by the next reader"
  - "Mutation-test the check, then mutate the check's own weakest assumption (here: prove a plain substring test would have passed where the boundary regex fails)"

requirements-completed: []

duration: 75min
completed: 2026-09-14
---

# Phase 24 Plan 01: Drawn — the shared foundation

**One battery estimate, one geometry module with two deliberately separate coordinate schemes, one CSS paint vocabulary, and eight machine checks that fail on a colour literal, an unpainted shape, an unresolved class, a duplicated constant or a forbidden import — every one of them proven by mutation.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 4/4
- **Files modified:** 4 (1 created)
- **Commits:** `c2fed18`, `0daf7a6`, `d4d322f`, `feb5882`

## The decision that mattered most

**The exclusivity claim had to be narrowed before it could be true, and narrowing it honestly was worth more than making it pass.**

The plan's premise — "no other module in `companion/` or `server/` re-derives a percentage from a raw millivolt value" — is false in this tree and cannot be made true. `server/poll_loop.py:433-451` carries `_NOTIFY_BATTERY_FULL_MV`/`_NOTIFY_BATTERY_EMPTY_MV` and `_battery_percent_estimate()`, a deliberate private copy whose own comment explains it: the server package must never import the web-app package (D-27, the constraint `server/wake.py`'s docstring also states), so the poll oneshot genuinely cannot call `companion/battery.py`.

Three ways out were available. Delete the copy and import across the boundary — rejected, it breaks a standing architectural rule for a cosmetic win. Scope the check to `companion/` only — rejected, because that silently stops watching the one place a *third* copy is most likely to appear next. What shipped instead: an **allow-list of exactly two entries, each with its own written justification in the check's own comment**, so a third definition anywhere under `companion/` or `server/` fails, and the two that exist are visibly deliberate rather than merely tolerated.

The same instinct produced the check's third net. The first two nets watch for the constant *names* and for a second `battery_percent`/`battery_fraction` *definition* — both of which a copy could evade simply by renaming. The third watches for the two millivolt endpoints `4200` and `3300` appearing **together** in one module, which is the signature of a copied estimate whatever the copy calls itself. `4200` alone is innocent: `health_page.SPARKLINE_Y_MAX_MV` is legitimately the same number, being the same battery's full charge. Verified against the tree: only `companion/battery.py` and `server/poll_loop.py` name both today.

## Mutations, with the message each produced

Eleven mutations plus one negative control. Every one produced **exactly one** additional failure beyond the 5-check sandbox baseline, and each named the offending file, symbol or class.

| # | Mutation | Failure message (quoted) |
|---|----------|--------------------------|
| a | a second `BATTERY_FULL_MV` in `companion/pages/home_page.py` | `companion/pages/home_page.py defines BATTERY_FULL_MV — the companion's battery millivolt constants have exactly one home (companion/battery.py), plus server/poll_loop.py's documented private copy that exists only because the server package may never import the web-app package. A third copy is how two surfaces come to show two different percentages for one reading.` |
| b | `fill="#123456"` added to one emitter | `companion/draw.py:479 emits the colour '#123456' — a colour decided in Python is correct in ONE theme. Every drawn shape takes its colour from a class bound to a theme token, which is redefined under the dark theme so the shape follows for free. A literal is also invisible to companion/test_contrast_check.py.` |
| c | a `<rect>` emitted with neither class nor fill | `companion/draw.py:454 emits a <rect> with neither a class nor an explicit fill/stroke — it takes the SVG default fill, which is black: correct against a light card, invisible against a dark one, and invisible to the contrast harness too` |
| d | `DRAWING_MARK_CLASS` renamed to `"drawing-marker"` | `companion/draw.py can emit class 'drawing-marker' and companion/static/style.css carries no selector for it — a class that exists in Python and nowhere in CSS paints NOTHING at all, and nothing else in this codebase would notice` |
| e | `from companion.pages import home_page` added to draw.py | `companion/draw.py imports the page module 'companion.pages.home_page' — draw.py exists so pages can share geometry WITHOUT any page-to-page dependency; importing one here inverts that` |
| e′ | `import companion.pages.home_page` (the dotted form) | identical message — the AST scan resolves both import forms to the same full name |
| g | `import server.wake` added to draw.py | `companion/draw.py imports 'server.wake' — a geometry module must not depend on the server package` |
| h | `escape()` switched to `quote=False` | `draw.escape() left '"' unescaped: '&lt;img src=x&gt;&amp;"\''` |
| i | `percent_y()`'s clamp removed | `percent_y() below the domain floor must pin at exactly the floor` |
| j | `usable_pairs()` made to index its labels separately from its values | `a dropped row must drop its own label — the last pair's label source is 'a-bool-is-not-a-reading'` |
| k | `href` removed from `REFUSED_ATTRIBUTES` | `companion/draw.py accepted a loaded reference ({'href': '/static/x.svg'}) instead of refusing it` |
| l | the paint-attribute keyword restriction disabled | `companion/draw.py accepted an external reference ({'fill': 'url(#gradient)'}) instead of refusing it` |
| m | `.drawing-mark` renamed in style.css | `companion/draw.py can emit class 'drawing-mark' and companion/static/style.css carries no selector for it …` |
| n | `.drawing-axis` renamed to `.drawing-axis-tick` in style.css | `companion/draw.py can emit class 'drawing-axis' and companion/static/style.css carries no selector for it …` — see the vacuity section below |
| **f** | **negative control:** `fill="#ff0000"` inside a Python *comment* in draw.py | **zero additional failures — the harness stayed green**, proving the comment strip |

## Checks that failed the vacuity question

**1. The class-resolution check, as first written, would have been vacuous.** `.drawing-axis` is a **substring** of `.drawing-axis-label`, and `.drawing` is a substring of both plus `.drawing__canvas`. A plain `".%s" in css` test reports every one of them resolved on the strength of one unrelated selector. Measured directly, with `.drawing-axis` renamed away (mutation n):

```
plain `.drawing-axis in css` -> True   (would have passed)
boundary regex              -> False  (fails, correctly)
```

The shipped check matches `\.<class>(?![-\w])`. This is the grep trap the standing constraints warn about — "a new selector that *ends in* an existing one silently redirects a shipped check" — met from the other direction: a new selector that *starts with* an existing class name silently satisfies it.

**2. The "deferred-script count is unchanged" behaviour was at risk of being a vacuous duplicate.** `_fourteen_deferred_scripts_before_closing_body` already pins that number and this phase does not move it; a second check counting the same thing would have added a number without adding a net. What shipped instead is a check with a different subject: **`draw.py`'s own emitters** return complete markup with no script tag, no external reference and no inline style, and *refuse* an attribute carrying one. The existing pin is cited in that check's comment. Verified independently: `layout.page_shell()` still emits exactly 14 deferred scripts.

**3. A raw-source scan of `companion/pages/health_page.py` would have failed on prose, not code.** That file's docstrings contain `<line class="sparkline-` and three separate mentions of `<polyline>` carrying no class at all. A shape-fill scan over raw source reports three unpainted polylines that do not exist. Every scan in Section 2.8 strips comments and docstrings first, and the section's banner comment says why.

## Deviations from plan

### [Rule 1 - Bug] `_attrs()` raised on a legitimate text value instead of escaping it

- **Found during:** Task 4, while proving the escaping check non-vacuous.
- **Issue:** Task 2's `_attrs()` refused **any** attribute value containing `<`. `draw.percent_canvas(label='<img src=x>&"\'')` raised `ValueError` rather than escaping. Real consequence: an airline name or firmware string out of `history.db` carrying an angle bracket would have taken down a page render — a *worse* outcome than the escaping that already makes it safe, and a direct breach of the module's own "never raises" contract.
- **Fix:** the refusals are now narrow and principled. Paint attributes (`fill`/`stroke`/`stop-color`) may carry only a paint keyword, loading attributes (`href`, `xlink:href`, `src`, `style`, `filter`, `mask`, `clip-path`, anything starting `on`) are refused by name whatever they carry, and **everything else is text, which is escaped, never refused**. The boundary between refuse and escape is now written out in `_attrs()`'s docstring.
- **Files modified:** `companion/draw.py`
- **Commit:** `d4d322f`

### [Rule 1 - Bug] the import scan misnamed the module it caught

- **Found during:** Task 4 mutation (e). The token-stream scan reported `from companion.pages import home_page` as importing `'home_page'` — a newline-joined token stream splits a dotted name into `companion`, `.`, `pages`. The check still failed (correctly), but on the wrong symbol, and `import companion.pages.home_page` fell through to the generic "unexpected imports \['companion'\]" message.
- **Fix:** the import check now reads `draw.py`'s **abstract syntax tree**. An AST carries no comment and no docstring by construction — a stronger statement of the comment-strip claim than stripping them — and dotted names survive intact. Both import forms now name `companion.pages.home_page`. The check's own name was corrected to say AST rather than "comment-stripped source".
- **Files modified:** `companion/test_companion_app.py`
- **Commit:** `feb5882`

### [Rule 2 - Missing critical] a second canvas class, `.drawing__figure`

- **Found during:** Task 3, writing the size route.
- **Issue:** one `.drawing__canvas` rule cannot serve both schemes. It declares `width: 100%` and a height, which is exactly right for a percentage-scheme canvas and exactly wrong for a `viewBox` one — it would override `unit_canvas()`'s intrinsic attributes, stretch the box and letterbox the aspect-locked shape inside it. A ring gauge (24-04) borrowing this class would have looked *fine* in review and wrong on screen.
- **Fix:** `DRAWING_FIGURE_CLASS` / `.drawing__figure`, which declares `display: block` and deliberately no size, with the reasoning recorded in both files. Two schemes, two canvas classes — the same reason the two scale families are separately named.
- **Files modified:** `companion/draw.py`, `companion/static/style.css`
- **Commit:** `0daf7a6`

### [Process] the four task commits are four, but not one-per-task

`c2fed18` carries Tasks 1 **and** 2. Task 1's staged `companion/battery.py` was swept into a sibling agent's commit while three plans executed against one shared git index; that history was subsequently rewritten by the sibling, and battery.py landed in my next commit instead. The content is correct and `git log -- companion/battery.py` shows exactly one Phase-24 commit for it (`c2fed18`). **Lesson applied for the rest of the plan:** `git add … && git commit …` in a single shell invocation, never as two, and `git show --name-only` after each. Every later commit carries exactly its own files.

## Plan assumptions that turned out wrong

1. **"the millivolt constants are defined in exactly one module … in `companion/` or `server/`."** False, deliberately and permanently — see *The decision that mattered most*. The check allow-lists two homes with two justifications.
2. **`companion/static/style.css:311-317` is the global reduced-motion block.** Stale line numbers; it is at `:344` (and `:1097` for the `.js .mobile-nav` case). Both untouched.
3. **Task 1's acceptance table is called a "twelve-input table" but lists thirteen** (`None, "", "abc", True, False, -1, 0, 3300, 3299, 3750, 4200, 4201, 99999`). All thirteen were asserted.
4. **"The new fraction helper returns a float in [0.0, 1.0] for every numeric input and None for every non-numeric one."** These two clauses conflict with the plan's own harder requirement that `int(round(fraction * 100)) == battery_percent()` for every input in the table: `-1` and `0` are numeric and `battery_percent()` returns `None` for both. The one-computation requirement wins, because it is the one that is *asserted*. `battery_fraction()` refuses exactly `battery_percent()`'s domain — non-numeric **or** non-positive — and its docstring says why: a reading of 0 mV is a broken sensor, not a flat battery, and a gauge drawing an honest empty ring beside text printing nothing is the two disagreeing again.
5. **Task 2 asks for `health_page.battery_sparkline_svg()` to be rewired if byte-identical; `<files_owned>` forbids touching `companion/pages/*.py` and the frontmatter excludes it.** Resolved on the side of files_owned — see below.

## The existing chart: provably untouched, and provably reproducible

`companion/pages/health_page.py` was not modified. Byte-identity is therefore trivial, but the *useful* half of the claim was still proven: `draw.percent_y()` reproduces the shipped chart's arithmetic **exactly**, measured by rendering `battery_sparkline_svg()` against a seeded five-point series (including an out-of-range 4300 mV and a below-floor 2900 mV), reading the `cy` percentages back out of the emitted markup, and comparing to `draw.percent_y(mv, SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV, 3.75)` rounded to the chart's own two decimals. Exact equality on all five points, out-of-range values included.

That is what 24-05 inherits: adoption is a mechanical substitution whose result is already known, not an experiment.

## battery_percent() before/after — byte-identical

| input | before | after | | input | before | after |
|---|---|---|---|---|---|---|
| `None` | `None` | `None` | | `3300` | `0` | `0` |
| `""` | `None` | `None` | | `3299` | `0` | `0` |
| `"abc"` | `None` | `None` | | `3750` | `50` | `50` |
| `True` | `0` | `0` | | `4200` | `100` | `100` |
| `False` | `None` | `None` | | `4201` | `100` | `100` |
| `-1` | `None` | `None` | | `99999` | `100` | `100` |
| `0` | `None` | `None` | | | | |

`int(round(battery_fraction(v) * 100)) == battery_percent(v)` holds for all thirteen. `battery_fraction(BATTERY_EMPTY_MV) == 0.0` and `battery_fraction(BATTERY_FULL_MV) == 1.0` exactly, asserted at the boundary. `LOW_BATTERY_DISPLAY_MV == 3480` and `battery_percent(3480) == 20`, which is its derivation read back.

## Check counts, re-derived by RUNNING

| harness | before | after |
|---|---|---|
| `companion-app` | 291 | **299** (+8) |
| `status-pages` | 287 | 287 |
| `config-page` | 240 | 240 |
| `view-pages` | 153 | 153 |
| `i18n` | 24 | 24 |
| `contrast` | 43 | 43 |
| deferred-script pin | 14 | 14 |

`EXPECTED_CHECK_COUNT = 299` is appended as a new last assignment at `companion/test_companion_app.py:669`, commented `24-01-PLAN.md Task 4`, with the note that it was re-derived by running. No pre-existing check was retargeted.

## Stylesheet baselines, before and after

| grep | before | after |
|---|---|---|
| `var(--color-accent)` | 70 | **70** |
| `@supports selector(:has(*)) {` | 1 | **1** |
| `@keyframes` | 4 | **4** |
| `prefers-reduced-motion` (plan's non-comment grep) | 3 | **3** |
| stray comment terminators | 0 | **0** (harness check green) |

The new block adds no colour value, no colour pair, no accent use, no transition and no animation. Every rule that sets `stroke` sets `fill` explicitly — verified by parsing the new block back and listing each selector's `stroke`/`fill` presence; only `.drawing-line` sets a stroke, and it declares `fill: none`.

## Verification

- `./scripts/run-all-tests.sh` → the failing set is **exactly the 5 documented sandbox baseline names**, verified by name: 4 × WR-11 read-only (`add_entry()`, `delete_entry()`, and the two `/airlines` route redirects) + 1 × `anomaly_active()`. No sixth failure.
- `ruff check .` → clean.
- `companion/test_contrast_check.py` → 43/43, no new pair.
- No `<human-check>`: this plan renders no drawing and changes nothing a user can see. The phase's visual sweep is 24-09's.

## Known stubs

None. Every primitive shipped here is complete and called by its own tests; the four drawings that will consume them are later plans' work by design.

## Not done, deliberately

- **`companion/pages/health_page.py` is untouched** — files_owned, and 24-05 owns that function.
- **No battery-life-remaining estimate.** Phase 25's D18 wants one; it needs a discharge model this phase has no data to justify. Recorded in `battery.py`'s own docstring so the next reader does not add one absent-mindedly.
- **`.planning/REQUIREMENTS.md` is untouched.** CFG-39 is **not** ticked — it belongs to phase 24's closing plan, which verifies and ticks with evidence per clause.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` are untouched.** Three plans executed concurrently against one working tree and one git index this wave; a write to either shared file from inside a wave member would have collided with a sibling. The orchestrator owns them.

## Self-Check: PASSED

- `companion/draw.py` — FOUND (634 lines)
- `companion/battery.py` — FOUND (119 lines)
- `companion/static/style.css` — FOUND, `.drawing*` block present at the `.sparkline*` block
- `companion/test_companion_app.py` — FOUND, Section 2.8 present, `EXPECTED_CHECK_COUNT = 299`
- `c2fed18` — FOUND (`feat(24-01): companion/draw.py — one geometry vocabulary for five drawings`)
- `0daf7a6` — FOUND (`feat(24-01): the shared drawing CSS vocabulary, beside the block it generalises`)
- `d4d322f` — FOUND (`test(24-01): the drawing contract becomes a test`)
- `feb5882` — FOUND (`test(24-01): the import scan reads the syntax tree, not the token stream`)
