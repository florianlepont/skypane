---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 01
subsystem: companion-harness
tags: [browser-harness, playwright, svg-geometry, agreement, vacuity]
requires:
  - "companion/test_browser_ux.py::_persist_without_js (25-02)"
  - "companion/test_browser_ux.py::_assert_hit_target (25-02)"
  - "companion/test_browser_ux.py::_operate_with_keyboard (25-02)"
  - "companion/test_browser_ux.py::_set_ui_theme (24-02)"
  - "companion/pages/config_page.py::QUIET_DIAL_RADIUS, QUIET_DIAL_ARC_CLASS (25-04)"
  - "companion/draw.py::unit_circle_dash_array (24-xx)"
provides:
  - "companion/test_browser_ux.py::_assert_surfaces_agree"
  - "companion/test_browser_ux.py::_canonical_surface_value"
  - "companion/test_browser_ux.py::_surface_reading_report"
  - "companion/test_browser_ux.py::_resolved_property"
  - "companion/test_browser_ux.py::_quiet_arc_minutes"
  - "companion/test_browser_ux.py::_fraction_pair_minutes"
  - "companion/test_browser_ux.py::_fraction_to_minute"
  - "companion/test_browser_ux.py::_region_text"
  - "companion/test_browser_ux.py::_assert_shorter_and_still_refuses"
  - "companion/test_browser_ux.py::_markup_inventory"
  - "companion/test_browser_ux.py::MINUTES_PER_DAY, _QUIET_ARC_SELECTOR"
affects:
  - "27-02 (the ONE dial-agreement check runs entirely on these)"
  - "27-06 (the three copy baselines and the title inventory measured here)"
  - "27-09 (the phase gate)"
tech-stack:
  added: []
  patterns:
    - "assert the SET of decoded surfaces, never one check per surface"
    - "agreement is three assertions: disagreement, the wrong value, the unchanged value"
    - "read RESOLVED geometry, never the declared attribute"
    - "decoders raise rather than default — an absent surface must never agree"
    - "'shorter' and 'still refuses' are proven about ONE read of ONE rendering"
key-files:
  created: []
  modified:
    - companion/test_browser_ux.py
decisions:
  - "the canonical unit for a quiet window is the MINUTE-OF-DAY, because the two handles already publish aria-valuenow in minutes — three of the four surfaces speak it natively"
  - "the arc is decoded from resolved stroke-dasharray + transform (SVG user units), NOT from getBoundingClientRect — so no scale() correction and no clientWidth rounding is ever involved"
  - "the radius and the quarter-turn are read from config_page's own constants (QUIET_DIAL_RADIUS, _QUIET_DIAL_TWELVE_OCLOCK_DEG), never retyped"
  - "_fraction_pair_minutes()'s second property is the SWEEP, not the end — the two stop being the same arithmetic exactly at a wrapping window"
  - "_markup_inventory() asserts nothing, so the count 27-06 decides on is derived by running"
metrics:
  duration: ~1h 20m
  completed: 2026-09-15
  checks_added: 0
  browser_harness: "81/81, 0 SKIP, 4m59.5s standalone (305.5s inside the suite)"
requirements-completed: []
---

# Phase 27 Plan 01: the agreement helper, the rendered-geometry decoder, the shortening and inventory helpers — Summary

**The relationship D17 shipped unmeasured is now readable in one call, and the arc is a number for the first time: pointed at the live tree, the new helper reproduces the shipped dial defect on demand and names both surfaces that lied.**

## Performance

- **Duration:** ~1h 20m
- **Tasks:** 3 of 3
- **Files modified:** 1 (`companion/test_browser_ux.py`)
- **Net checks added:** 0

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `41be709` | the surface-agreement helper — one value, N surfaces, one set |
| 2 | `3514aee` | read the quiet arc back as a NUMBER, from RESOLVED geometry |
| 3 | `950e82f` | shorter AND still refusing, proven about ONE read; plus inventory |

## The decision that mattered most

**The canonical unit is the minute-of-day, and it was not chosen — it was discovered by probing the page before writing a line of the decoder.**

The obvious design for a geometry decoder is to return fractions, because fractions are what
`draw.unit_circle_dash_array()` and `quiet_window_span()` speak. A probe of the live page first
showed that the two handles already publish `aria-valuenow="1380"` and `"420"` — minutes-of-day —
and that the caption prints `23:00 → 07:00`, which parses to minutes exactly. So three of the four
surfaces already speak minutes natively and only the arc speaks fractions.

Had the decoder returned fractions, `_assert_surfaces_agree()` would have had to compare
`0.9583333…` against whatever a caption parsed to, and every caller would have invented its own
tolerance — which is a mechanism for hiding disagreements inside the one helper whose entire subject
is disagreement. Rounding a fraction to the nearest minute is canonicalisation to a unit the page
itself uses; a tolerance on a float comparison is not. A surface that is a whole minute out still
reads as a different number and still fails.

The same probe-before-writing produced the second half of that decision: the resolved
`stroke-dasharray` comes back in **SVG user units**, the same units `QUIET_DIAL_RADIUS` is in. That
is why this decoder goes nowhere near `getBoundingClientRect()` and needs no correction for a
`scale()` in force, and why `clientWidth`'s integer rounding (54.41 in a "53.00" box) cannot reach
it. The brief's warning about box measurement is real; the answer here was to not measure a box.

## What was built

### 1. `_assert_surfaces_agree(page, surfaces, requested, before, where)`

Takes an ordered mapping of a surface **label** to a zero-argument **decoder**, not a fixed pair of
arguments. Decodes every surface, builds the set, and makes **three separate assertions with three
distinct messages**:

1. the decoded set has more than one member — the surfaces **disagree**;
2. the single member is not what the interaction **requested** — the page froze together;
3. the single member is what was there **before** — the interaction was a no-op.

Every message prints the **full** `surface -> value` mapping. A fourth guard refuses a call with
fewer than two surfaces, because agreement between one surface and nothing is the endpoint check
this helper exists to replace.

`_canonical_surface_value()` makes a tuple and a list the same reading (a false FAIL is as damaging
as a false PASS) and **raises** on anything unhashable rather than falling back to `repr()`, which
would make every unhashable value agree with itself by accident.

### 2. `_resolved_property()`, `_quiet_arc_minutes()`, `_fraction_pair_minutes()`

`_resolved_property(page, selector, property, where)` reads one property — custom **or** standard,
through the same `getPropertyValue` call — off the **one** element a selector matches. It raises on
any other match count, on a selector the browser rejects, and on a value that resolves to nothing.
It never defaults.

`_quiet_arc_minutes()` inverts `draw.unit_circle_dash_array()` (drawn dash over circumference is the
sweep) and `quiet_dial_svg()`'s quarter turn, dividing by `config_page.QUIET_DIAL_RADIUS` and undoing
`config_page._QUIET_DIAL_TWELVE_OCLOCK_DEG` — both read, neither retyped. It waits for nothing:
sampling at the right instant is the caller's job and must be done by hooking the event the browser
emits, not by a sleep buried inside an instrument.

`_fraction_pair_minutes()` decodes the same window from a start fraction and a **sweep** fraction
published as custom properties on the shared ancestor — the second place the geometry will live
after 27-02, so "the ancestor moved and the paint did not follow" becomes assertable.

### 3. `_region_text()`, `_assert_shorter_and_still_refuses()`, `_markup_inventory()`

One read, whitespace-normalised, joined across every matching element (two of 27-06's three regions
are genuinely plural). Two assertions against that one string, with two messages. `_markup_inventory()`
returns `{label: count}` and asserts nothing at all.

## The defect each helper was shown catching

### The agreement helper catches the SHIPPED dial defect — on this tree, today

Driven against `/display` at 360 px: record the four surfaces at rest, press the **Work day
(08:00–18:00)** preset, wait on the observable condition (`wait_for_function` on the start field's
own value, never a guessed instant), then re-decode.

```
AT REST:          fields (1380, 420)  handles (1380, 420)  arc (1380, 420)  caption (1380, 420)
AFTER THE PRESET: fields (480, 1080)  handles (480, 1080)  arc (1380, 420)  caption (1380, 420)
```

That is the developer's screen recording, reproduced by a machine: the fields read 08:00/18:00, both
handles followed, and the arc and the caption are still drawing 23:00 → 07:00. Verbatim:

```
_assert_surfaces_agree: the quiet-hours dial after the Work day preset — the 4 surfaces describing
this value DISAGREE on http://127.0.0.1:48951/display. They read: the two time inputs -> (480, 1080);
the two handles (aria-valuenow) -> (480, 1080); the arc, as PAINTED -> (1380, 420); the caption ->
(1380, 420). The interaction asked for (480, 1080). A surface that did not follow is a surface that
is now lying to the visitor about a value the page beside it shows correctly
```

**No mutation was needed to produce this.** The defect is live, and the message names which two
surfaces dissented and what each read — the sentence a two-value message could not have produced.

### The agreement helper, all four clauses, on a control whose answer is already known

Control: the wake-interval number input and its native range mirror on `/device`, which 25-05 keeps
in sync. Interaction: one `ArrowRight` on the range through `_operate_with_keyboard()`.

**(a) the positive direction — real numbers**

```
BEFORE number='300' range='300'
AFTER  number='360' range='360'  (keyboard reported '360')
DEMO-A PASS decoded={'the wake-interval number input': '360', 'its native range mirror': '360'}
```

**(b) one decoder replaced by a constant that cannot be right**

```
_assert_surfaces_agree: the wake-interval pair after one ArrowRight — the 2 surfaces describing this
value DISAGREE on http://127.0.0.1:32833/device. They read: the wake-interval number input -> '360';
its native range mirror -> '86400'. The interaction asked for '360'. A surface that did not follow is
a surface that is now lying to the visitor about a value the page beside it shows correctly
```

**(c) clause 2 — agreement on the wrong value (a page frozen together)**

```
_assert_surfaces_agree: the wake-interval pair after one ArrowRight — all 2 surfaces on
http://127.0.0.1:32833/device agree on '360', but the interaction asked for '900'. They read: the
wake-interval number input -> '360'; its native range mirror -> '360'. Agreement on the wrong value
is what a page that froze every surface together looks like from outside, which is why agreement
alone is not the assertion
```

**(d) clause 3 — a no-op**

```
_assert_surfaces_agree: the wake-interval pair after one ArrowRight — all 2 surfaces on
http://127.0.0.1:32833/device agree on '360', which is exactly what was there BEFORE the interaction.
They read: the wake-interval number input -> '360'; its native range mirror -> '360'. The interaction
changed nothing, so this reading proves nothing: a no-op is the cheapest way to make every surface on
a page agree
```

**T-27-01-A honoured:** the demonstration's last act was one `ArrowLeft` through the same keyboard
path, and the control was re-read at `number='300' range='300'`. The demonstration ran against its
own `Harness()` and its own temp state directory, so no shared fixture was ever touched.

### The geometry decoder, positive direction — the numbers

Against `/display` with the seeded 23:00 → 07:00 window:

```
RADIUS used (config_page.QUIET_DIAL_RADIUS) : 78
resolved stroke-dasharray                   : '163.363px, 326.726px'
resolved transform                          : 'matrix(-0.258819, -0.965926, 0.965926, -0.258819, 25.7746, 195.778)'
decoded arc minutes                         : (1380, 420)
the two <input type="time"> values          : '23:00' -> '07:00'
the inputs as minutes                       : (1380, 420)
MATCH                                       : True
```

### The geometry decoder, negative direction — quoted

A selector that does not exist:

```
_resolved_property: the missing-subject demonstration — '.quiet-dial__no-such-arc' matches 0
element(s) on http://127.0.0.1:47941/display, and the resolved value of 'stroke-dasharray' is only
defined for exactly one. A decoder that defaulted here would make an ABSENT arc agree with every
other surface on the page
```

A property nothing publishes yet (which is also `_fraction_pair_minutes()`'s state before 27-02):

```
_resolved_property: the not-yet-published pair demonstration — '--quiet-start-fraction' resolves to
nothing at all on '.quiet-dial' on http://127.0.0.1:47941/display. Read as absent rather than as a
default, because a default here is a number nobody measured
```

### The shortening helper, both directions

Positive: passes against a baseline one character longer than today (`255`), measuring `254`.

Negative 1 — the cut never happened (baseline = today's own 254):

```
_assert_shorter_and_still_refuses: the gauges against TODAY's own length (an uncut region) —
'.wake-gauge' renders 254 character(s) across 2 element(s) on http://127.0.0.1:37567/device, against
a recorded baseline of 254. The copy was not cut. It reads 'A plane reaches the frame at most 5 min
after it passes. Not enough battery history yet to say how long a charge lasts — this frame has never
measured what one wake costs. While the screen is off the frame wakes every 5m instead, whatever this
is set to.'
```

Negative 2 — the refusal was weakened (forbidden pattern deliberately set to one the honest copy
does contain):

```
_assert_shorter_and_still_refuses: the gauges against a pattern the honest copy DOES contain —
'.wake-gauge' did get shorter (254 character(s), under the 255 baseline) but now matches
'battery|batterie' at 'battery'. A shorter sentence that starts claiming a figure this frame's own
history cannot support is a regression, not a cut. …
```

An absent region:

```
_region_text: a region that is not there — '#no-such-region' matches nothing on
http://127.0.0.1:37567/device. A region that is absent is not a region that was shortened, and zero
is the shortest length there is
```

### The inventory helper

Returns `0` for a shape nothing matches (`{'nothing at all': 0}`) and raises, naming the label and
the selector, for a selector the browser rejects.

## The numbers 27-06 inherits — MEASURED, not asserted

### The three copy baselines (360 px, seeded fixture, both routes signed in)

| Region | Selector | Route | Elements | **Baseline chars** |
|---|---|---|---|---|
| The wake-interval caption | `#wake-interval-caption` | `/device` | 1 | **220** |
| The two wake gauges | `.wake-gauge` | `/device` | 2 | **254** |
| The Quiet hours paragraph | `#quiet-hours-caption` | `/display` | 1 | **188** |

Today's rendered text, verbatim, so 27-06 cuts from a recorded starting point:

- wake-interval caption (220): *"How often the frame wakes to poll for updates. Shorter means fresher
  info and more battery drain; longer means more battery life and staler info at a glance. Applies on
  the next scheduled poll. (next wake ≈ 31 Jul 08:05)"*
- the two gauges (254): *"A plane reaches the frame at most 5 min after it passes. Not enough battery
  history yet to say how long a charge lasts — this frame has never measured what one wake costs.
  While the screen is off the frame wakes every 5m instead, whatever this is set to."*
- Quiet hours paragraph (188): *"Pauses the frame's wake, poll and display cycle during the schedule
  below — the Frame strip's Quiet hours switch is what turns it on and off. Applies at the next wake,
  around 31 Jul 08:05."*

### The title inventory — and it corrects 27-RESEARCH.md §3

| Form | Selector | `/device` | `/display` | Total rendered |
|---|---|---|---|---|
| A — title INSIDE the card | `[data-dirty-section] > h2.text-heading` | 3 | 4 | **7** |
| B — title ABOVE the card | `.section-intro > h2.text-heading` | 0 | 3 | **3** |
| all `h2.text-heading` | `h2.text-heading` | 4 | 8 | **12** |
| unclassified (12 − 7 − 3) | — | 1 | 1 | **2** |

27-RESEARCH.md §3 predicted **8 / 3 / 2** from a grep of `config_page.py` and said so provisionally.
The executable inventory measures **7 / 3 / 2 as rendered across the two settings routes**. The grep
counted a form-A call site that these two routes do not render; the research document's own sentence —
"the regex matches a formatting convention, not a grammar" — is what came true. 27-06 should decide
on 7, not 8, or first establish where the eighth renders.

## Deviations from Plan

None. No Rule 1–4 deviation was triggered. The only surprises were measurement findings (below), not
code changes.

## Anything that did not evaluate as predicted

1. **`grep -n 'java_script_enabled' companion/test_browser_ux.py` does not return one line — it
   returns six**, and it returned six on the base commit too (five of them are prose in comments).
   The invariant that actually holds, and that this plan held, is the **call-site** count:
   `grep -c 'new_context(java_script_enabled'` is **1** on the base commit and **1** now. Later plans
   should pin the call site, not the word.

2. **The quiet dial does not render on `/device`.** `GROUP_QUIET_HOURS` is an *everyday* group, so it
   renders on `/display`. The first geometry probe returned `{"error": "none"}` against `/device`.
   27-02 must drive `/display`.

3. **`QUIET_DIAL_RADIUS` is 78, not 54.** Its own comment above the constant says *"Chosen so the
   arithmetic below lands on whole numbers: 64 − 7 − 3 = 54"*, but the expression is
   `176 // 2 − 14 // 2 − 3 = 78`. The comment is stale; the arithmetic is fine. This is exactly why
   the decoder reads the constant rather than the comment. Flagged, not fixed — it is outside this
   plan's owned file, and correcting it belongs to whichever later plan touches `config_page.py`.

4. **A days-figure forbidden pattern must be scoped to the gauges, never applied page-wide.** The
   wake-interval caption legitimately renders *"(next wake ≈ 31 Jul 08:05)"*, so the obvious pattern
   `≈\s*\d` matches it. Confirmed by running:

   ```
   _assert_shorter_and_still_refuses: the wake-interval caption against the days-figure pattern —
   '#wake-interval-caption' did get shorter (220 character(s), under the 999 baseline) but now matches
   '≈\s*\d' at '≈ 3'. …
   ```

   27-06's forbidden pattern needs to name the days claim itself (the `≈ N day(s) of battery left`
   shape), not the `≈` glyph.

5. **CSS `mod()` resolves in the harness Chromium** — `CSS.supports('width', 'calc(mod(1,1) * 1px)')`
   returned **`true`**. 27-RESEARCH.md §1.4 made sub-option 1 conditional on exactly this run. The
   condition is satisfied; the choice is 27-02's.

6. **`transform` resolves to a matrix and `rotate` resolves to `"none"`.** The rotation has to come
   back through `atan2` off the matrix; reading the `rotate` property returns nothing usable. The
   resolved dash is also comma-separated, `px`-suffixed and carries three decimals where the emitted
   attribute carries four — so nothing string-compares against the server's output.

7. **The next-slowest harness is now `companion/test_companion_app.py` at 39.8 s**, not the 31.7 s the
   brief recorded. Not caused by this plan (that file is untouched), but the critical-path margin is
   smaller than the brief assumes.

## How zero-net was PROVEN

Following 23-02's precedent, repeated by 24-02 and 25-02 — measured, never argued.

1. **AST comparison of every `check(...)` first argument** against the base commit `839489a`, using a
   throwaway comparator that walks both ASTs, `literal_eval`s each first argument, and compares the
   ordered lists:

   ```
   base call sites: 81
   head call sites: 81
   same count      : True
   identical+order : True
   ```

   Re-run after **each** of the three commits, identical result every time.

2. **`git diff --numstat 839489a -- companion/test_browser_ux.py` → `564  0`.** 564 lines added,
   **0 removed**, so the removed-line list is empty. 156 + 256 + 152 = 564 across the three commits.
   `git diff --name-only 839489a` names exactly one file: `companion/test_browser_ux.py`. `STATE.md`,
   `ROADMAP.md` and `REQUIREMENTS.md` are untouched, and no requirement was ticked.

3. **`EXPECTED_CHECK_COUNT` re-derived by RUNNING, not by reading.** `81` on the base commit, `81`
   now, and the harness's own final line — which is computed from the registered results, not from
   the constant — printed `browser-ux: 81/81 checks pass` after every task.

4. **Runtime measured, not argued** (below).

## Verification — re-derived by running

| Measure | Result |
|---|---|
| `companion/test_browser_ux.py` standalone | **81/81 pass, exit 0** |
| `grep -c SKIP` on its output | **0** — the harness really ran |
| Real wall clock, standalone | **4m 59.5s** (task 1: 4m 55.5s; task 2: 4m 57.6s; pre-plan baseline on this machine: 5m 24.2s) |
| `EXPECTED_CHECK_COUNT` | **81**, unchanged |
| `ruff check .` | **All checks passed!** after every task |
| scripts-blocked call sites | **1** (base: 1) |
| `./scripts/run-all-tests.sh` | **305.5s total, JOBS=4**; `test_browser_ux.py` 305.5s is the critical path |
| `grep -c SKIP` across the whole suite | **0** |

### The failing set is exactly the 5 baseline names

Verified **by name**, never by failing-file count:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key …` (WR-11,
   `companion/test_companion_app.py`)
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash
   key …` (WR-11, `companion/test_companion_app.py`)
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created …` (WR-11,
   `server/test_manual_resolutions.py`)
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write …`
   (WR-11, `server/test_manual_resolutions.py`)
5. `anomaly_active() runs on every page render and must never raise …`
   (`companion/test_status_pages.py`)

Total failing checks: **5**. No sixth.

## Notes on discipline

- **No new script and no new route** (D-26). One file was touched. The deferred-script pin stays at
  15, CSP is untouched, and nothing was added under `companion/static/`.
- **No source mutation was needed to demonstrate any helper.** Every negative direction was produced
  by substituting a *decoder* or a *baseline* at the call site — the dial defect is live on the tree,
  the uncut region is genuinely uncut, and the absent selector is genuinely absent. So the "a mutation
  that mutates a comment proves nothing" trap never arose, and no mutate/revert cycle ran, so no
  `__pycache__` clearing was required.
- All three demonstration scripts live in the session scratchpad and are **not** in the repository.
  Nothing this plan added is executed by the harness's own run — the helpers are called by zero
  registered checks today and by 27-02/27-06 tomorrow, which is what "zero net checks" means here.
- `git show --name-only` was run after each of the three commits; each names exactly one file.

## Self-Check: PASSED

- `companion/test_browser_ux.py` — FOUND, and all ten new callables resolve by name on import.
- `.planning/phases/27-.../27-01-SUMMARY.md` — FOUND.
- Commits `41be709`, `3514aee`, `950e82f` — all FOUND in `git log`.
