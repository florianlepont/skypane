---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 02
subsystem: testing
tags: [playwright, browser-harness, dark-mode, getComputedStyle, svg, overflow, css-custom-properties]

requires:
  - phase: 23-companion-dynamism-i
    provides: "`_no_js_page()` (23-02), the VIEWPORT_* constant set with its 360px floor and its recorded reason the 320px rung stays (23-02), the `_assert_clean` return-a-finished-message idiom (260913-eab), and the two page-level overflow checks the new helper had to agree with rather than contradict"
provides:
  - "`_set_ui_theme(page, theme)` — the first thing in this repository that has ever switched theme in a real browser, verifying the page actually repainted rather than trusting that it did"
  - "`_computed_paint(page, selector, props)` — the browser's own resolved fill/stroke/color, with the SVG-default case named for the caller"
  - "`_assert_no_page_overflow(page, where, expected_width)` — one page-body overflow assertion five drawing plans share instead of five slightly different ones"
  - "`UI_THEMES_EXPLICIT` / `SVG_DEFAULT_PAINT` — the two named constants those helpers measure against"
affects: [24-04, 24-05, 24-06, 24-07, 24-08]

tech-stack:
  added: []
  patterns:
    - "A harness helper is accepted only once it has been made to fail on a deliberately injected defect — a helper with no demonstration is a promise, not a measurement"
    - "Proofs run OUTSIDE the harness file, so no temporary check, injected element or stripped class can survive by being forgotten"
    - "getComputedStyle is the wait: a resolved read forces a style flush, so no sleep, timeout or transitionend listener is needed to know a theme switch landed"

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "The theme helper refuses to return unless BOTH inverting tokens differ between the two explicit themes — the difference between a helper that measures dark mode and one that lets four later plans compare a value to itself"
  - "Drive the explicit html[data-ui-theme] attribute, never emulate_media(prefers-color-scheme): the explicit override is what the app's own picker sets and what style.css declares specifically to outrank the OS preference"
  - "Assert the property the two override blocks exist to produce, not the hex values they currently hold — hardcoding #F7F4EF/#0C0F14 would duplicate style.css into a harness and fail on a palette change that is not a defect"
  - "documentElement, matching both existing page-level overflow checks — a third convention in the same file is how three checks come to disagree about what 'the page' means"
  - "The escaped-element list is diagnostic only, never an independent failure condition: CFG-45's wording is 'no horizontal scrollbar on the page body', and a helper must not do more than its name says to four calling plans"
  - "The two existing overflow checks were NOT retrofitted onto the new helper, despite the plan inviting generalisation — retrofitting would have changed existing check bodies, which the plan's own binding constraints forbid"

patterns-established:
  - "Helper self-verification as anti-vacuity: a measurement helper asserts that the mechanism it drives is live before returning a reading taken through it"
  - "`svg_default` reports INDISTINGUISHABLE FROM THE INITIAL VALUE, not a verdict — the caller asserts on the property it expects to carry the token"

requirements-completed: []

duration: 78min
completed: 2026-09-14
---

# Phase 24 Plan 02: Browser-Harness Helpers Summary

**The suite's only rendering harness gains the ability to ask "is this correct in dark mode too?" for the first time in twenty-three phases — a theme switch that verifies the page really repainted, a resolved-paint reader that can tell a token-painted shape from an SVG-default one, and one shared page-body overflow assertion — at exactly zero net checks, 54 before and 54 after, re-derived by running.**

## Performance

- **Duration:** ~78 min
- **Tasks:** 2/2
- **Files modified:** 1 (`companion/test_browser_ux.py`)
- **Lines:** +335 / −0

| # | Commit | Message |
|---|---|---|
| 1 | `7d65919` | `test(24-02): a theme helper, and the first dark-mode measurement this harness has ever made` |
| 2 | `75e9504` | `test(24-02): a computed-paint reader and a body-overflow assertion, still zero net checks` |

## The decision that mattered most

**The theme helper samples both explicit themes on every call and refuses to
return unless the two genuinely differ.**

Everything else in this plan was a choice between two reasonable options. This
one was the difference between a helper and a decoration. The obvious
implementation is three lines — set `data-ui-theme`, flush, return — and it
would have been accepted by every acceptance criterion in the plan. It would
also have been **vacuous**, and silently so: if the `html[data-ui-theme="dark"]`
override were ever renamed, dropped, or outranked, both themes would resolve to
the same paint, and the four drawing plans' "this shape's colour differs between
themes" assertions would each be comparing a value to itself while printing
PASS. Eight consecutive plans in this project have caught vacuous checks of their
own; the way to not become the ninth is to make the vacuous state unreachable
rather than unlikely.

So `_set_ui_theme()` reads `--color-canvas` and `--color-text` in **both**
explicit themes on every call, and raises if either pair matches. The
verification is deliberately **not** a literal-value assertion — hardcoding
`#F7F4EF` / `#0C0F14` would copy style.css into a harness and start failing on a
palette change that is not a defect. What is asserted is the *property the two
override blocks exist to produce*: that they invert.

This cost the helper two extra forced style recalculations per call
(sub-millisecond) and bought the only thing that makes the rest of Phase 24
checkable.

## What was built

### `_set_ui_theme(page, theme)` → `{"theme", "canvas", "text"}`

Puts an already-loaded page into a named theme and returns the resolved paint
that theme produces.

- **The explicit attribute, not `emulate_media`.** The next reader's instinct
  will be `color_scheme="dark"`, and the helper's comment says why that is the
  weaker test here: `html[data-ui-theme]` is what this app's own theme picker
  sets (`app.py`'s theme form → `layout.page_shell()`'s `<html>` attribute), and
  style.css declares those two blocks specifically so they **take precedence
  over** `prefers-color-scheme`. Driving the OS preference would exercise a path
  the app deliberately lets the user override, *and* would leave the measurement
  at the mercy of the host's setting. The attribute is both the faithful test
  and the deterministic one; the comment records both halves, because either one
  alone reads as a preference.
- **The vocabulary is the app's own.** `UI_THEMES_EXPLICIT` is derived from
  `layout.UI_THEME_CHOICES`, not restated, so a renamed choice fails here rather
  than silently measuring nothing. `"auto"` is refused **with its reason**: it
  declares no override rule of its own (style.css's CFG-09 paragraph says so in
  as many words), so it resolves to whatever the host OS prefers — the one thing
  a measurement must not depend on.
- **The read is the wait.** Every value goes through `getComputedStyle`, which
  is a forced style flush: the browser must resolve every pending recalculation
  before it can answer. There is no sleep, no timeout and no `transitionend`
  listener anywhere in this helper, for the reason 23-02 recorded when it put
  the disclosure sweep under reduced motion — a timing wait is a flakiness
  generator on the slowest file in the suite, and an intermittently red check is
  worse than no check.
- **`<body>` is the witness** because style.css's own `body` rule is where both
  inverting tokens are actually *spent* (`background: var(--color-canvas)`,
  `color: var(--color-text)`). A `getPropertyValue('--color-canvas')` would
  return the token's declared text even if nothing on the page ever used it;
  this reads real paint.

### `_computed_paint(page, selector, props=("fill", "stroke", "color"))`

The browser's resolved paint for the first match — never the attribute, never
the class.

What it buys over 24-01's source scans, which is the only reason it is worth the
browser it costs: `getComputedStyle` has already run the cascade, resolved
`currentColor` against the inherited `color`, and substituted the theme token.
It is the only thing in the repository that can tell a shape painted by a token
from one that fell through to the SVG default.

`svg_default` names, for the caller, every requested property whose resolved
value is **indistinguishable from that property's SVG initial value** — so four
plans do not each have to recognise the defect and each get the sentinel
slightly different. The comment is explicit that this is an observation and not
a verdict: a shape that legitimately declares `stroke: none` reports `stroke`
here too, and a caller asserting "this must be token-painted" should assert on
the property it expects to carry the token.

An unmatched selector **raises** rather than returning a sentinel. This file
guards against measuring an empty page everywhere it can ("with none, this check
measures nothing"); a returned `None` is a guard each of four call sites has to
*remember*, an exception is one they cannot forget, and `check()` turns it into a
named FAIL rather than a swallowed pass.

### `_assert_no_page_overflow(page, where, expected_width=None)` → `""` or a message

Returns `""` when the page does not scroll horizontally, and a finished failure
sentence naming **both** measurements when it does — the `_assert_clean` idiom
this file already uses for exactly this job, so callers write
`msg = ...; if msg: return False, msg` and every drawing plan's overflow failure
reads the same.

**Which box means "the page": `documentElement`.** Matching
`_home_paints_nothing_outside_the_viewport_or_its_cards` and
`_every_disclosure_on_every_page_opens_without_overflow`, both of which already
compare `documentElement.scrollWidth`. This was *measured before choosing*, not
assumed — see "Did not evaluate as predicted" below.

**A deliberately-scrollable wrap is not a page overflow**, and the helper gets
that right by construction rather than by a special case. 260913-cz6 recorded
that a `.data-table-wrap` overflowing its own box leaves
`documentElement.scrollWidth` exactly unmoved; that was re-measured here.
`_health_tables_fit_their_wraps_with_every_disclosure_open` owns the wrap-level
question, and this helper does not contradict it.

## Every helper, shown catching a real defect

Each proof injected a defect at runtime, showed the helper failing with its own
message, **restored** the defect, and showed the helper clean again. All proofs
ran in `/tmp/.../prove_helpers.py`, which imports the three helpers and drives
its own `Harness` — see "Zero net checks" for why that placement matters.

### 1. Theme helper — the `html[data-ui-theme="dark"]` override deleted from the live CSSOM

The most faithful form of the defect the helper exists to prevent: the override
rule stops reaching the page. Deleted rule:
`html[data-ui-theme="dark"] { --color-canvas: #0C0F14; --color-dominant...`

> ```
> _set_ui_theme: setting html[data-ui-theme] did not repaint the page — canvas
> resolved to 'rgb(247, 244, 239)' in BOTH 'light' and 'dark', so the explicit
> CFG-09 override is not reaching <body> and every dark-mode assertion built on
> this helper would be comparing a value to itself (style.css's
> html[data-ui-theme="light"] / html[data-ui-theme="dark"] blocks)
> ```

Restored → `{'theme': 'dark', 'canvas': 'rgb(12, 15, 20)', 'text': 'rgb(241, 243, 246)'}`.

**The two resolved colour values, one per theme** (identical with scripts
enabled and with `java_script_enabled=False` — the flag `_no_js_page()` itself
composes):

| theme | `--color-canvas` → `body` background | `--color-text` → `body` color |
|---|---|---|
| light | `rgb(247, 244, 239)` | `rgb(23, 25, 31)` |
| dark | `rgb(12, 15, 20)` | `rgb(241, 243, 246)` |

Dark mode does not depend on a script.

### 2. Paint reader — the class stripped off a real `.sparkline-line`

`.sparkline-line`'s rule is `stroke: currentColor`, so it is a real existing
shape whose paint the cascade has to resolve. Three distinct readings, the third
being the default:

| state | `fill` | `stroke` | `color` | `svg_default` |
|---|---|---|---|---|
| light, token-painted | `none` | `rgb(23, 25, 31)` | `rgb(23, 25, 31)` | `()` |
| dark, token-painted | `none` | `rgb(241, 243, 246)` | `rgb(241, 243, 246)` | `()` |
| class stripped (light) | `rgb(0, 0, 0)` | `none` | `rgb(23, 25, 31)` | `('fill', 'stroke')` |
| class stripped (dark) | `rgb(0, 0, 0)` | `none` | `rgb(241, 243, 246)` | `('fill', 'stroke')` |

Restored readings were byte-identical to the pre-strip ones in both themes
(`identical: True`). No source scan distinguishes these three states.

The unmatched-selector guard:

> ```
> _computed_paint: no element matched '.no-such-shape-24-02' on
> http://127.0.0.1:50367/health — with none, this measures nothing
> ```

### 3. Overflow helper — a 2000px element on `<body>`, and the same element inside a wrap

Measured on `/health` with every `<details>` forced open, at all three rungs of
`VIEWPORT_WIDTHS_RESPONSIVE` (widths taken from the existing `VIEWPORT_*` dicts,
not restated).

| width | clean | 2000px **inside** a `.data-table-wrap` | 2000px on `<body>` |
|---|---|---|---|
| 360 | `''` | wrap 278 → 2000, helper `''` | **fails** |
| 390 | `''` | wrap 308 → 2000, helper `''` | **fails** |
| 1280 | `''` | wrap 830 → 2000, helper `''` | **fails** |

The failure message, naming both numbers:

> ```
> Health scrolls sideways at 360px: documentElement.scrollWidth 2000 against a
> client width of 360, painted past the right edge by ['DIV'] (CFG-45's
> page-body floor)
> ```

And the `expected_width` guard, which is what stops a context that silently came
up at another size from producing a green measurement:

> ```
> Health: expected the measurement to be taken at 361px, the document reports a
> client width of 360
> ```

**The wrap column is the criterion that mattered.** A wrap taken from 278px to
2000px of content — its own horizontal scrollbar, exactly the state 260913-cz6
recorded — leaves this helper reporting clean at every width, because the page
itself never moved. The new helper cannot start disagreeing with
`_health_tables_fit_their_wraps_with_every_disclosure_open`.

## How zero-net was proven

Not asserted — measured, by 23-02's method.

**1. AST comparison against the pre-plan HEAD.** A walk over both
`git show HEAD:companion/test_browser_ux.py` and the worktree file extracts every
`check(...)` call's first argument and compares the lists element-by-element.
Nothing is inferred from the diff.

```
check(...) call sites — HEAD: 54   worktree: 54
descriptions identical: True
```

**2. The `EXPECTED_CHECK_COUNT` ladder, byte-identical.** Every module-level
assignment in the file, both sides:

```
HEAD: [6, 6, 7, 8, 9, 10, 11, 12, 14, 17, 19, 20, 21, 22, 23, 24, 25, 26, 28, 32, 42, 47, 50, 51, 53, 54]
work: [6, 6, 7, 8, 9, 10, 11, 12, 14, 17, 19, 20, 21, 22, 23, 24, 25, 26, 28, 32, 42, 47, 50, 51, 53, 54]
final — HEAD 54 / worktree 54 / unchanged: True
```

Not one rung was added, and the constant was not bumped.

**3. Additions only.** `git diff --numstat` against the pre-plan HEAD:
`335  0  companion/test_browser_ux.py`. The script enumerates removed lines
explicitly; the list is **empty**. No existing check's name or body changed, no
320px assertion was weakened, moved or deleted.

**4. Re-derived by RUNNING, never by arithmetic.** The harness printed
`browser-ux: 54/54 checks pass`.

**5. `grep -c SKIP` on the output is 0** — because a green suite alone never
proves this file ran. Both runs executed all 54 checks against a real Chromium
(151.0.7922.34); neither skip gate fired.

| run | result | `FAIL` | `SKIP` | wall clock |
|---|---|---|---|---|
| pre-plan baseline, standalone | 54/54 | 0 | 0 | **2m45.043s (165.0s)** |
| post-plan, standalone | 54/54 | 0 | 0 | **2m34.459s (154.5s)** |
| post-plan, inside `run-all-tests.sh` (JOBS=4) | 54/54 | 0 | 0 | 161.2s |

The 10.6s difference is noise on a 4-way-parallel machine shared with two
sibling agents, and runs in the *opposite* direction to any cost: the plan added
zero standing checks, so it added zero runtime. 154.5s matches the ~154s
recorded at the end of Phase 23.

**6. No proof artefact survives.**
`grep -c '24-02-proof\|proof-wide\|proof-in-wrap' companion/test_browser_ux.py`
→ **0**. See below for why that is structural rather than remembered.

## Acceptance criteria — every one run literally

Nothing was adjusted to make a criterion pass, and no criterion was edited.

### Task 1

| Criterion | Expected | Got | |
|---|---|---|---|
| `companion/test_browser_ux.py` | 54/54 | **54/54**, 0 SKIP | PASS |
| `grep -c 'data-ui-theme'` | non-zero (pre `0`) | pre-task **0** → post-plan **9** | PASS |
| two resolved colours recorded, one per theme, differing | — | light `rgb(247, 244, 239)` / dark `rgb(12, 15, 20)`; text `rgb(23, 25, 31)` / `rgb(241, 243, 246)` | PASS |
| the same proof through a scripts-blocked context, still differing | — | byte-identical values with `java_script_enabled=False` | PASS |
| `EXPECTED_CHECK_COUNT` unchanged, re-derived by running | 54 | **54** | PASS |
| `git diff` shows additions only | — | 161 / 0 in this commit, 335 / 0 across both | PASS |
| `ruff check .` | clean | `All checks passed!` | PASS |

`grep -c "data-theme\|prefers-color-scheme\|emulate_media\|color_scheme"` over
this file went **0 → 4** (all four inside the new helper's own comment and
constant block, explaining why `emulate_media` was *not* used).

### Task 2

| Criterion | Expected | Got | |
|---|---|---|---|
| `.sparkline-line` in both themes and class-stripped — three distinct values, third the default | — | table above; stripped reports `fill rgb(0, 0, 0)`, `stroke none` | PASS |
| overflow helper's two numbers, clean and injected, second failing | — | 360/360 clean; 2000 vs 360 fails, at all three widths | PASS |
| PASS for a page whose only wide element is inside a deliberately-scrollable wrap | PASS | wrap 278→2000 (and 308→2000, 830→2000), helper `''` | PASS |
| `EXPECTED_CHECK_COUNT` unchanged, re-derived by running | 54 | **54** | PASS |
| no temporary proof check, injected element or stripped class survives | `grep` → nothing | **0** | PASS |
| `ruff check .` | clean | `All checks passed!` | PASS |

### Plan-level

| Criterion | Got | |
|---|---|---|
| every 320px assertion still present | `VIEWPORT_WIDTH_NARROW = 320` (:601) and its use in `VIEWPORT_WIDTHS_ALL` (:610), which the callsign check still walks at :3821 — and 0 removed lines proves nothing was deleted | PASS |
| helpers use the existing `VIEWPORT_*` dicts, widths not restated | proofs drove `VIEWPORT_MIN_SUPPORTED` / `VIEWPORT_PHONE` / `VIEWPORT_DESKTOP`; the overflow helper reads its width from the document rather than taking a literal | PASS |
| one commit per task, no model identifier in any artifact | 2 commits, attribution trailers only | PASS |

## Did not evaluate as predicted

**1. `document.body` is not clipped by its own `overflow-x: hidden`.**
The plan asked me to decide between `document.body` and
`document.documentElement` and state why. I predicted the choice would be forced
by measurement: style.css's `body` rule carries `overflow-x: hidden` (UXA-01's
guaranteed fix), so I expected `document.body.scrollWidth` to be clamped and
therefore blind to the defect by construction. **It is not.** Measured on
`/health` at 360px with every disclosure open:

```
clean            : docSW 360  docCW 360  bodySW 360  bodyCW 360
wide-inside-wrap : docSW 360  docCW 360  bodySW 360  bodyCW 360   (wrap 278 → 2000)
wide-on-body     : docSW 2000 docCW 360  bodySW 2000 bodyCW 360
```

The two boxes agree exactly, because CSS *propagates* a body overflow to the
viewport when `<html>`'s own overflow is `visible`, leaving body's used value
`visible`. So the choice was **not** settled by a measured difference — it is
settled by consistency with the file's two existing page-level checks, and the
helper's comment now records the measurement rather than the argument I expected
to be able to make.

**2. The helper's own self-verification caught a bug in the helper, on its first
run.** The in-page probe sampled both themes and then reset the document to
`themes[0]` instead of to the theme the caller asked for, so
`_set_ui_theme(page, "dark")` left the page on `light` while returning dark's
values — a helper that lies about the state it leaves the page in, which is
precisely the vacuity mode the four drawing plans would have inherited. The
settle assertion I had written for a *different* failure mode caught it
immediately:

> ```
> _set_ui_theme: asked for 'dark', the document element reports 'light' after
> the switch
> ```

Fixed by giving the probe an explicit `settle` argument (Rule 1). This is the
strongest single piece of evidence that the self-verification was worth its
cost: it found a real defect before any caller existed.

**3. No temporary proof check was ever added, so none had to be deleted.**
The plan anticipated registering temporary checks and deleting them before the
final commit, and made "no injection marker survives" an acceptance criterion.
Both proofs instead ran from a scratch script that *imports* the three helpers
and drives its own `Harness`. That is strictly stronger: the criterion becomes
**structurally true** rather than checked, because nothing temporary was ever in
the committed file to forget. The `git diff` bears it out — 335 added lines, 0
removed, so there is no add-then-delete round trip to audit.

**4. `svg_default` reports two properties for a stripped `.sparkline-line`, not
one.** The plan's criterion phrased the stripped reading as "the third being the
default", singular. Stripping the class flips `fill` from `none` → `rgb(0, 0, 0)`
*and* `stroke` from the token → `none`, because the rule sets both. Both are
genuine SVG initial values, the helper reports `('fill', 'stroke')`, and that is
more informative than a single verdict would have been — which is why the helper
returns per-property findings rather than a boolean.

## Findings

**The two existing overflow checks were deliberately not retrofitted.** The plan
invited generalisation ("if it can be generalised rather than duplicated, do
that"). I did not, and the reason is that the same plan's binding constraints
forbid the consequence: retrofitting `_home_paints_nothing_outside_the_viewport_
or_its_cards` or `_every_disclosure_on_every_page_opens_without_overflow` onto
the new helper would have changed those checks' bodies, which "do not weaken,
retarget or delete any existing check" rules out, and would have put a refactor
of two of the file's most load-bearing assertions in the same commit as a new
helper with no callers. They are also not straight duplicates: `_home_...`
additionally measures every recent-flight descendant against its own row box,
which the new helper deliberately does not do. **Neither existing check is made
redundant by this plan** — the new helper is a strict subset of each one's
page-level half, and the right time to consider collapsing them is after the
four drawing plans have exercised the helper, not before.

**No application code was touched.** The plan flagged that a helper which cannot
be written without changing a page or the stylesheet is a finding, not a licence.
None was needed: every helper works against the app exactly as it stands.

## Sandbox baseline — verified by failing check NAMES

`./scripts/run-all-tests.sh` → 8 failing checks across 4 harnesses. The
five baseline names are all present and accounted for:

| # | Failing check | Baseline reason |
|---|---|---|
| 1 | `POST /airlines/resolve redirects with the manual_save_failed flash key … read-only` | WR-11 |
| 2 | `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … read-only (WR-11)` | WR-11 |
| 3 | `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created … (WR-11)` | WR-11 |
| 4 | `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)` | WR-11 |
| 5 | `anomaly_active() runs on every page render and must never raise …` | sandbox |

The **three extra failures are not mine**, and that is established by name and by
authorship, not by file count. All three are in `server/test_config_history.py`
and are named after `wake_epochs` / `record_wake_epoch()` — symbols in
`server/history_db.py`, a file plan **24-03** owns and is mid-TDD on. They
arrived with sibling commit `cdb3d00 test(24-03): failing checks for the
forward-looking epoch table`, which landed during my run:

- `every CREATE TABLE in history_db.py is guarded by IF NOT EXISTS and there are exactly four — the fourth (wake_epochs) …`
- `a history.db created BEFORE wake_epochs existed opens cleanly …`
- `record_wake_epoch() inserts only when the effective interval differs … AttributeError("module '…")` ← a RED-phase failure by construction

My two commits touched exactly one file (`companion/test_browser_ux.py`,
+161 and +174, nothing else), which is in none of those three harnesses'
dependency sets, and that harness reports `==> PASS companion/test_browser_ux.py
(161.2s)` / `browser-ux: 54/54 checks pass` inside the same suite run.

**No sixth failure is mine.**

## What this hands the drawing plans

`24-04` through `24-08` can now write, for the first time:

```python
for theme in UI_THEMES_EXPLICIT:
    paint = _set_ui_theme(page, theme)          # raises if the theme is a no-op
    shape = _computed_paint(page, ".some-drawing-line")
    if shape["svg_default"]:                    # painted black by accident
        return False, "..."
    msg = _assert_no_page_overflow(page, "/health", VIEWPORT_MIN_SUPPORTED["width"])
    if msg:
        return False, msg
```

…and the same call composes over a page obtained through `_no_js_page()`, which
is the combination — dark mode, scripts blocked — most likely to be wrong.

## Requirements

**CFG-45 is NOT ticked.** This plan delivers only its measurement half; the
drawings it exists to make checkable are 24-04 to 24-08, and the standing
constraint for this phase is that no requirement is ticked from an execution
plan. `requirements-completed` is deliberately empty.

## Self-Check: PASSED

- `companion/test_browser_ux.py` exists, 6660 lines, helpers at :871 / :990 / :1096 — FOUND
- `.planning/phases/24-…/24-02-SUMMARY.md` — FOUND
- commit `7d65919` — FOUND
- commit `75e9504` — FOUND
