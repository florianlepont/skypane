# Phase 24: Companion dynamism II — "Drawn" — Research

**Phase:** 24 — Companion dynamism II — "Drawn": server-rendered SVG from the history
**Researched:** 2026-09-13
**Depends on:** Phase 23 (in progress — 23-10 and 23-11 outstanding at the time of writing)
**Requirements:** CFG-39, CFG-40, CFG-41, CFG-42, CFG-43, CFG-44, CFG-45

---

## Summary

This phase draws five pictures out of data the app already stores. Three findings
shape every plan below, and all three were established by reading this tree rather
than by reasoning from the roadmap text:

1. **The shared battery estimator already exists and is already shared.**
   `companion/battery.py` (38 lines, stdlib-only, created by 19-01 for exactly this
   reason: "let home_page.py and health_page.py share one estimate without either
   importing the other") is the phase's named estimator artifact. The failure the
   roadmap fears — five independent estimators that disagree — is prevented by
   *extending this module and forbidding a second copy*, not by creating a new one.
   Any drawing that needs a percentage, a threshold or a gauge fraction gets it from
   here, and a harness check proves no page module recomputes `4200`/`3300` itself.

2. **This app already server-renders an SVG chart, and its coordinate scheme is the
   opposite of the one the brief's chart guidance assumes.**
   `health_page.battery_sparkline_svg()` emits an `<svg>` with **no `viewBox` and no
   `preserveAspectRatio`**, so 1 user unit == 1 CSS pixel; every horizontal position
   is a **percentage** and every size (radius, stroke, tick) is an absolute pixel at
   every container width. Axis labels are **HTML `<span>` elements outside the SVG**
   in a CSS-grid wrapper (`.sparkline` / `.sparkline__y` / `.sparkline__x`), never
   SVG `<text>`. This was arrived at deliberately over three quick tasks
   (260902-ep7, 260902-l0b) and it is *why* the chart survives 360 px without a
   scrollbar and why no scale factor exists anywhere to go wrong. The brief's rule
   "the viewBox must leave room for the outermost labels" therefore binds only the
   drawings that genuinely need a `viewBox` (the ring gauge and the punctuality
   grid, which are intrinsically aspect-locked); for the time-series drawings the
   stronger rule is **keep labels out of the SVG entirely**, which makes the
   viewBox-overflow defect unreachable by construction.

3. **D20's blocker is real, and it is worse than "the expected interval is not
   stored" — but it also has a clean, migration-free answer.** See
   *Risk 1* below. Short version: `device_health` rows are Caddy access-log entries
   for the device's display fetch, so they are genuine per-wake check-ins, but a
   *log rotation the ingest missed* produces a gap that is indistinguishable from a
   missed wake, and the expected interval is not merely unstored — it is not even a
   constant (it switches with `display_enabled` and is held by quiet hours). No
   schema change can recover the past. **Recommendation: change the metric** (plot
   observed check-in gaps judged against the cadence in force, named honestly), and
   *additionally* start accruing true interval epochs in a **new table**, which this
   project's `CREATE TABLE IF NOT EXISTS` schema bootstrap already supports with no
   migration mechanism at all.

Everything in this phase is server-rendered HTML+SVG. That is not a stylistic
preference: **D-09's no-JS floor is absolute**, and an SVG emitted by Python arrives
complete in the first response, paints with scripts blocked, and needs no client
library, no canvas, and no measurement pass. This is the single strongest reason
server-rendered SVG was chosen over any client-side charting approach, and every
plan below states it.

---

## Project Constraints (from CLAUDE.md and the standing engineering rules)

These are binding on every plan in this phase and each plan restates the ones it
can violate:

- **CSP is `script-src 'self'`** (`companion/app.py:143`) — no inline script, no
  nonce. Every new static script needs **its own route** in `companion/app.py`
  (there is deliberately no catch-all `/static/` handler) and moves the
  deferred-script pin count in `companion/test_companion_app.py`. The current count
  is **fourteen** (`_fourteen_deferred_scripts_before_closing_body`,
  `companion/test_companion_app.py:4398-4477`) — re-read it before editing, because
  Phase 23's outstanding plans may move it again.
  **This phase should add zero scripts.** A server-rendered drawing that needs a
  script to be correct has failed the no-JS floor; a script may only *decorate* one
  (Pattern 2 below), and none of the five D-items needs decoration to be correct.
- **No-JS floor (D-09) is absolute.** Server-rendered SVG suits this phase
  precisely: the drawing is data, not behaviour.
- **Minimum supported viewport 360 px**, no horizontal scrollbar on the page body.
- **Motion tokens** `--motion-fast` (180 ms) / `--motion-slow` (2 s) only;
  `interpolate-size` and `calc-size(` are banned (Chromium-only); the global
  `prefers-reduced-motion: reduce` block at `style.css:311-317` covers every
  transition and animation and must not be duplicated per rule.
- **`style.css` is guarded at zero stray comment terminators** by
  `companion/test_status_pages.py` — every new comment goes *inside* a block
  comment.
- **Every check must be mutation-tested** and must survive the vacuity question
  ("what would a *wrong* implementation do?"). `EXPECTED_CHECK_COUNT` is re-derived
  by **running** the harness, never by arithmetic, and appended as a new last
  assignment citing the plan and task.
- **Sandbox baseline is exactly 5 failing checks** (4 × WR-11 read-only, 1 ×
  `anomaly_active()`), verified by check **NAME**, never by failing-file count.
- **A page module may never import another page module**
  (`companion/pages/__init__.py`). Anything two pages need lives in
  `companion/battery.py`, `companion/layout.py`, `companion/frame_state.py` — or,
  as this phase proposes, `companion/draw.py`.
- **French parity** — `companion/i18n_fr/` carries a module per page; every new
  user-visible string needs its French sibling and `companion/test_i18n.py`
  enforces it across `app.py`, HTML attribute literals and JS fallbacks.
- **The design authority is the `sketch-findings-skypane` skill**, not this file.
  Where the two disagree, the skill wins and this file is wrong.

---

## User Constraints

### No CONTEXT.md exists for this phase

`/gsd-discuss-phase 24` was not run. The developer is unavailable for this planning
run, so **every decision that would have been an `AskUserQuestion` is recorded
below with its real trade-offs and a recommendation, and is marked PROVISIONAL**.
Plans proceed on the recommended option, clearly flagged, so the work is not
blocked — but each is a genuine open question for the morning. Phase 23 set the
precedent for this shape: it also ran with no CONTEXT.md, and its ROADMAP entry
carries the developer's decisions as prose after the fact.

### Locked — from `sketch-findings-skypane` (design system, authority)

- **The battery-trend card contract**: full-width, out of the stat-tile dashboard
  grid, hairline-at-rest not shadow-at-rest, serif `<h2>` with **no glyph** (the
  glyph-in-`<h2>` was placed by 06.6.1-04 and removed by 260902-j8w at the
  developer's explicit instruction — do not put one back).
- **The chart plots a 90-day daily-average series** by default (260902-l0b, the
  developer's own request: *"ce qui m'intéresse, c'est globalement l'évolution sur
  plusieurs jours"*), with a raw-readings fallback for a device younger than two
  Paris calendar days. The latest *computed* reading above the chart stays the
  latest **raw** reading, never the daily average.
- **`.sparkline-axis-label` is 10 px** and lives in the documented sub-scale
  exception tier of the type scale. A new chart label size would be a new tier and
  needs an argument, not a value.
- **Accent reservation**: the accent colour is reserved; status uses the
  status-ok/warn/error tokens. `.quick-action` uses status-ok for its "on" edge and
  **no accent** — the same restraint binds a gauge's "good" arc.
- **Icons are a tile/control affordance**; headings carry none.
- **Timestamps are Europe/Paris local** (`layout.local_clock_text()`); raw ISO
  survives only behind a `.copy-btn`. Every tooltip carries a **full local**
  timestamp. Daily buckets are **Europe/Paris** calendar days computed in Python
  (`history_db._paris_day_or_none`), never UTC ones.

### Claude's Discretion (in the absence of a CONTEXT.md)

Emitter naming, module layout, the exact geometry of each drawing, the guard's
implementation, and the wave split — subject to the contracts stated here.

### Deferred / Out of scope

- Any client-side charting library, canvas rendering, or measurement-dependent
  layout — excluded by the no-JS floor and by `script-src 'self'`.
- Animating the drawings (a growing ring, a drawing-in line). The motion budget is
  two tokens and one keyframes; an SVG path-length animation would be a third
  vocabulary. **Not built in this phase**; if wanted, it is a Phase 25+ question.
- D16's Orly runway map, D17's quiet-hours dial, D18's wake-interval gauges — these
  are **Phase 25 controls**, not Phase 24 drawings, even though D18's "battery-life
  gauge" will want CFG-39's estimator. Phase 24 must leave that estimator in a
  shape Phase 25 can call; it must not build D18's gauge.

---

## Phase Requirements

| ID | Requirement (abridged) | Served by |
|----|------------------------|-----------|
| CFG-39 | One shared battery estimator + one SVG drawing contract, machine-enforced | 24-01, closed by 24-09 |
| CFG-40 | D21 ring gauge — one emitter, two sizes (Health + Home tile) | 24-04 |
| CFG-41 | D8 battery chart — area, marked last point, low-battery threshold | 24-05 |
| CFG-42 | D13 Home day timeline | 24-06 |
| CFG-43 | D20 — reported only as far as the stored data can prove it | 24-03 (data + settlement), 24-07 (the grid) |
| CFG-44 | D4 Home hero, fed by the other emitters | 24-08 |
| CFG-45 | The regression floor: no-JS, 360 px, both themes, motion budget, design system in step | 24-02, asserted by every plan, closed by 24-09 |

---

## Architectural Responsibility Map

| Concern | Owner today | Owner after this phase |
|---------|-------------|------------------------|
| Battery % from millivolts | `companion/battery.py` | unchanged — **extended** with the threshold and the gauge fraction |
| Low-battery millivolt thresholds | `server/poll_loop.py` (device-side warning) | unchanged for the device; the companion's *display* threshold is derived in `companion/battery.py` and **named as an estimate**, never presented as the device's own rule |
| SVG geometry, escaping, scales, label placement | nothing — inlined in `health_page.battery_sparkline_svg()` | **`companion/draw.py`** (new, stdlib-only, imports no page module and no server module) |
| The battery sparkline emitter | `companion/pages/health_page.py` | unchanged location, rewritten to call `companion/draw.py` |
| The ring gauge | — | `companion/draw.py` (reused twice: Health + Home tile) |
| The day timeline | — | `companion/pages/home_page.py`, geometry from `draw.py` |
| The punctuality grid | — | `companion/pages/health_page.py`, geometry from `draw.py` |
| Check-in gap analysis over `device_health` | — | `server/history_db.py` (reader only, beside `daily_battery_averages()`) |
| Chart CSS classes and their theme tokens | `style.css` `.sparkline*` block | extended with one shared `.drawing*` vocabulary |
| The chart contract, enforced | nothing | a source-scan check in `companion/test_companion_app.py` |

**Why `companion/draw.py` and not `companion/layout.py`:** `layout.py` is already
3 828 lines and owns the page shell, nav, tiles, timestamps and the icon `<use>`
helper. A drawing module is a different concern with a different test surface, and
`companion/battery.py` is the precedent for "a small shared module beside layout.py
rather than another section of it". `draw.py` must stay stdlib-only and import
neither a page module nor anything from `server/` — the same rule
`companion/battery.py`'s own docstring states and for the same reason.

---

## What already exists (read this before drawing anything)

### The existing chart, in detail

`companion/pages/health_page.py`, `battery_sparkline_svg(rows, now=None, daily=False)`:

- Returns `""` when fewer than two rows carry a numeric `battery_mv` — a single
  point cannot show a trend.
- Pairs `(battery_mv, ts, reading_count)` **before** filtering, so a dropped row
  drops its own timestamp; the same filtered pairs drive the points *and* the axis
  labels, so a label can never describe a point that is not there. **This is the
  "every label names a value the chart actually reaches" rule, already solved once
  in this codebase. Copy the technique, do not re-derive it.**
- `_point_x(i) = i / (n-1) * 100` — "the chart fills its card" is a property of the
  formula, not a tuned margin.
- `_point_y(v)` clamps into a **fixed** `[SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV]`
  range before positioning, so an out-of-range reading pins at the edge rather than
  silently rescaling the axis (D-04/A-22). The y axis is inverted for SVG's
  top-down direction, and `_SPARKLINE_VERTICAL_INSET_PERCENT` keeps a marker's
  radius inside the canvas.
- Axis chrome is **filled `<rect>`**, never stroked `<line>`: an axis-aligned
  integer-width filled rect has no stroke-centring or half-pixel rounding to reason
  about, and a rect can pair a percentage position with an absolute size.
- The line is `n-1` `<line class="sparkline-line">` segments, because percentages
  are not permitted inside a `<polyline points>` list.
- Cosmetic `<circle class="sparkline-dot">` plus a larger `<circle
  class="sparkline-hit">` hit target carrying `tabindex` (a roving-tabindex
  keyboard path) and a `<title>`/`aria-label` with the humanised reading; dots are
  suppressed above `_SPARKLINE_DENSE_POINT_THRESHOLD` (39, derived from a real
  Chrome `getBoundingClientRect()` measurement).
- Every axis label is `aria-hidden` because each point already announces its own
  reading — duplicating it would make a screen reader read the extremes twice.
- The function deliberately emits **no script tag and no external reference**, and
  `companion/test_status_pages.py` asserts that directly against its return value.

### Colour: how an SVG shape gets its fill here

Every `.sparkline-*` shape takes its paint from a **CSS class** in `style.css`
(`.sparkline-line`, `.sparkline-axis` at `--color-border`, `.sparkline-dot`,
`.sparkline-hit`, `.sparkline-axis-label`), never from an SVG presentation
attribute. That is what makes the chart correct in both themes for free: the token
is redefined under the dark theme and the shape follows.

**This is the project's answer to the brief's "every drawn shape needs an explicit
fill" rule, and the plans must state the reconciliation explicitly**: "explicit
fill" here means *a shape whose fill is set by a class bound to a theme token* —
never the SVG default (`fill: black`, invisible in dark mode against dark ink, and
the exact "correct only in light mode" defect), and never a literal
`fill="#1a1a1a"` (correct in one theme, wrong in the other, and invisible to the
contrast harness). A drawn shape with **no** class and **no** fill is the defect;
the guard in 24-01 must fail on it.

### The icon SVG convention (a different thing, do not confuse them)

`layout.icon_html()` emits `<svg class=… width=… height=… aria-hidden focusable="false"><use href="#id"></use></svg>`
against one `ICON_DEFS_HTML` sprite. Its docstring records the trap: **an `<svg>`
with neither an attribute nor a CSS size renders at the SVG default 300×150 and
blows the layout apart.** Every new drawing must therefore carry an explicit size
route — a CSS rule on its own class (the sparkline's approach) or intrinsic
`width`/`height` attributes. A drawing with neither is a layout bomb.

### Routes, CSP and the harness

- `companion/app.py:143` — `style-src 'self' 'unsafe-inline'; script-src 'self';`
- Each static asset has a named route constant and a thin handler; there is no
  catch-all. **This phase adds no static asset**, so it touches none of this — but
  a plan that finds itself wanting one has left the no-JS floor.
- `companion/test_browser_ux.py` (5 689 lines) drives a real Chromium at 320/360/
  390/768/1280 px, in both languages, **with scripts blocked and with scripts on**;
  360 px is a named constant used at nine call sites. This is where "no horizontal
  scrollbar at 360 px" and "legible in both themes" become executable.
- `companion/test_status_pages.py` (13 795 lines) owns Health's server-side
  assertions and the `style.css` comment-terminator guard.
- `companion/test_view_pages.py` owns Home's.

---

## The drawing contract (what CFG-39 makes executable)

Derived from the brief's chart failure mode, reconciled with what this codebase
already proves. A plan may only deviate with a written reason in its own SUMMARY.

1. **One scale places marks, ticks and labels.** A drawing computes its scale once
   (a function in `draw.py` taking the domain and returning positions) and every
   mark, tick and label reads from that one call. Two scales — one for the line and
   one for the labels — is the defect this rule exists to prevent, and it is how a
   label ends up naming a value the chart does not reach.
2. **Every axis label names a value the drawing actually reaches.** Labels are
   derived from the *same filtered series* the marks are derived from (the existing
   sparkline's pairing technique), never from the unfiltered input and never from a
   constant.
3. **Colour comes from a theme token via a class.** No literal colour in emitted
   SVG. Text inside or beside a drawing uses the same label token the rest of the
   app uses, so it reads in both themes. A drawing that is only correct in light
   mode is a **defect**, not a polish item — and `companion/test_contrast_check.py`
   already exists to make that assertable.
4. **Every drawn shape has an explicit fill route** (a class, or `fill="none"` +
   a stroked class where a shape is deliberately unfilled). No shape may rely on
   the SVG default.
5. **Where a `viewBox` exists, it contains the outermost label.** The preferred
   escape is to have no labels inside the SVG at all (the existing `<span>`-outside
   scheme). A drawing that genuinely needs SVG `<text>` (the punctuality grid's
   day letters are the likely case) must prove the viewBox contains the text's own
   bounding box — and the practical way to prove it in this codebase is a real
   browser measurement in `test_browser_ux.py`, not arithmetic.
6. **A drawing fits 360 px with no horizontal scrollbar on the page body**, and is
   measured there in a real browser.
7. **A drawing renders with scripts blocked**, and that is measured too.

---

## Risk 1 — D20: the expected-interval blocker, settled

### What is actually stored

`device_health(id, ts, battery_mv, fw_version, boot_reason, rssi, UNIQUE(ts, battery_mv))`,
populated **only** by `history_db.ingest_caddy_battery_log()`, which tails Caddy's
JSON access log and keeps every entry whose request URI is `DEVICE_DISPLAY_URI`.

So a row **is** a real check-in — one per device display fetch — not merely a
battery reading. That is better than the roadmap entry implies, and it is what
makes an honest punctuality metric possible at all. But four properties bound what
can be claimed:

- **A row can carry `battery_mv = None`** (the header was absent or unparseable).
  A gap metric must therefore read **all** rows, not the `battery_mv`-filtered
  subset the chart uses. Using the chart's filtered series would invent missed
  wakes out of missing headers.
- **`UNIQUE(ts, battery_mv)` can collapse two genuine check-ins** into one — but
  only if they share a second *and* a millivolt reading. `WAKE_INTERVAL_MIN_S` is
  60, so at any configurable cadence this cannot lose a real wake. That is a
  provable statement, and it belongs in the caption's honesty note.
- **A missed log range is not a missed wake.** `ingest_caddy_battery_log()` resets
  its offset to 0 when the file is *shorter* than the stored offset (a rotation),
  which recovers a rotate-in-place. It cannot recover a rotation that *moved the
  old file away* between two ingests: that range is gone, and the resulting hole in
  `device_health` is indistinguishable from a device that did not wake.
  **No schema change fixes this**, which is decisive: a metric literally named
  "honoured-wake rate" would be asserting something the data cannot support even
  with a new column.
- **`meta.caddy_log_offset` is the only ingest state.** There is no record of when
  ingestion ran, so "no rows in this window" cannot be distinguished from "ingest
  did not run in this window" either.

### Why "expected interval" is not merely unstored

`server/wake.effective_wake_interval_s(device_cfg)` resolves the cadence in force
with this precedence: `display_enabled is False` → `DISPLAY_OFF_SLEEP_S`; else a
positive int `wake_interval_s`; else `env_sleep_s()`; else `None`. So the expected
interval is **a function of mutable config**, and it switches whenever the screen is
turned off — a control the user can flip from Home. On top of that, an active
quiet-hours window puts the frame in `wake.HOLD_QUIET_HOURS`, changing what a
"missed" wake even means during that window.

And the config itself has **no history**: `device_config.json` is a
current-state file, and this project's established, repeatedly-pinned convention
for it is **no migration and no rewrite** — an absent key resolves to a default and
the file on disk is left untouched (`server/device_config.py:695-750`, proven by
three separate named checks in `server/test_config_history.py` at :985, :1404,
:1456). There is no change log to mine. Nothing about the past is recoverable.

### Option A — grow the schema (add `expected_interval_s` to `device_health`)

- **Cost:** this project has **no SQLite migration mechanism at all.**
  `history_db.init_schema()` is three `CREATE TABLE IF NOT EXISTS` statements plus
  two indexes; there is no `PRAGMA user_version`, and `ALTER TABLE` appears nowhere
  in the tree. Adding a **column to an existing table** would require inventing that
  mechanism, and getting it right for a database **two processes open concurrently
  under WAL** (the `Type=oneshot` poll unit on a 30 s timer, and the long-lived
  companion) — a first-of-its-kind change in the riskiest place.
- **What it can honestly claim:** nothing about any row already stored. Every
  existing `device_health` row has no expected interval and never will. The metric
  would be blank on day one and would stay thin for days or weeks depending on
  cadence.
- **It still does not fix the rotation hole**, so even the future rows could not
  support the words "honoured-wake rate" without a caveat.

### Option B — change the metric (RECOMMENDED for what the grid draws)

Plot **observed gaps between consecutive check-ins**, judged against the cadence
**currently** in force, reusing `wake.device_staleness_thresholds()`'s existing
warn/error multipliers (`MISSED_WAKES_WARN`/`MISSED_WAKES_ERROR` with the 5/20-minute
floors) so the grid and the Frame tile can never disagree about what "late" means.

- Renders truthfully **on day one**, over all history already stored.
- Costs **zero** schema change and zero new mechanism.
- Names itself honestly: *check-in regularity*, never *honoured-wake rate*; the
  caption states that the cadence it is judged against is today's, and that a
  missing range in the log is not proof of a missed wake.
- **What it cannot claim:** that a gap was the device's fault, or that the cadence
  in force at the time was the cadence it is being judged against.

### Option C — start recording epochs in a NEW table (recommended as a cheap add-on)

The key observation that makes this cheap: **the project's zero-migration path
already covers a brand-new table.** `init_schema()` runs `CREATE TABLE IF NOT
EXISTS` on **every** connection from **both** processes, so adding a fourth table
costs no migration mechanism, no version stamp and no `ALTER TABLE` — it simply
exists on the next connect. Write one row from `server/poll_loop.py` **only when
the effective interval changes** (dedupe against the last row), giving true
expected-interval epochs from ship day forward.

- **Cost:** one table, one guarded write in the poll oneshot, tests. Small.
- **Benefit:** a later phase can upgrade D20's metric from "observed regularity" to
  a genuine honoured-wake rate over the window the epochs cover — without this
  phase's chart ever having claimed it.
- **Risk if mis-sold:** if any plan lets the *grid* read this table, the grid goes
  back to being blank-until-it-accrues. **No plan in this phase may read it.**

### Verdict

**Option B is what the grid draws. Option C lands alongside it as data accrual
only.** A is rejected: it buys nothing B does not already have, costs the project's
first SQLite migration in its most concurrency-sensitive file, and still cannot
support the phrase it exists to support.

**PROVISIONAL — the developer may drop Option C** and keep the phase to B alone.
Option C is speculative work whose consumer is a future phase; it is recommended
because it is cheap and because the honest metric is otherwise permanently capped,
but nothing in this phase depends on it. If dropped, plan 24-03 loses one task and
plan 24-07 is unaffected.

**PROVISIONAL — the grid's name.** "Wake punctuality" overstates Option B. The
recommendation is to title it *Check-in regularity* (FR: *Régularité des
relevés*) and let the caption carry the rest. The roadmap's D20 wording is
preserved in the requirement text so the lineage is traceable.

---

## Risk 2 — the coordinate scheme: percentages vs `viewBox`

Two schemes are now in play and mixing them silently is the predictable defect.

| | No `viewBox` (percentage x, absolute px sizes) | `viewBox` (user units, uniform scale) |
|---|---|---|
| Used by | the existing battery sparkline | nothing yet in this app |
| Width behaviour | fills its container at every width; no scale factor exists | scales uniformly, including stroke widths and text |
| Stroke/label size | constant in CSS px at every width — always legible | shrinks with the box — can become illegible at 360 px |
| Label placement | HTML `<span>`s outside, in a CSS grid | SVG `<text>` inside, must fit the viewBox |
| Right for | time-series that must fill a card (D8, D13) | intrinsically aspect-locked marks (D21's ring, D20's grid cells) |

**Rule for this phase:** D8 and D13 keep the no-`viewBox` percentage scheme and put
every label outside the SVG. D21's ring gauge and D20's grid use a `viewBox`
because they are aspect-locked shapes whose proportions must not stretch — and each
must then obey contract rule 5 (the viewBox contains its outermost label) and must
declare an explicit size route so it cannot fall back to 300×150.

A single drawing must never mix the two. `draw.py` should make this hard to get
wrong by exposing the two scales as separate, differently-named helpers rather than
one helper with a flag.

---

## Risk 3 — "correct in light mode only"

The mechanism that prevents it already exists (class + token, Risk section above),
but nothing today *enforces* it, and this phase adds four new drawings at once.

Concretely, three defects are reachable and each has a cheap machine check:

1. A shape with no class and no `fill` → paints SVG-default black; invisible in
   dark mode. **Check:** scan every emitted `<rect|circle|path|line|polygon>` in the
   drawing emitters' output for a `class=` or an explicit `fill`/`stroke`.
2. A literal colour in emitted SVG (`fill="#..."`, `stroke="rgb(...)"`) → correct in
   one theme. **Check:** assert no colour literal appears in any drawing emitter's
   return value.
3. A class that exists in the emitter but **not** in `style.css` → no paint at all.
   **Check:** every class name emitted by a drawing resolves to a selector in
   `style.css`. This one is the most valuable of the three and the least obvious;
   it is also exactly the defect the app's own `.sparkline*` history shows is
   possible (a rule silently dropped for four plans by a stray comment terminator).

`companion/test_contrast_check.py` already computes contrast for this app's tokens
and is the right place to extend if a drawing introduces a colour *pair* (e.g. a
status-coloured grid cell against the card background) rather than reusing one.

---

## Risk 4 — the phase touches files a parallel agent is editing

At the time of writing, plan **23-10** is executing in this same working tree and
owns `companion/static/style.css`, `companion/static/theme-preview.js`,
`companion/pages/{config,home,history,airlines}_page.py` and three companion test
files. Phase 24 cannot begin until Phase 23 closes (its own `Depends on`), so this
is not a merge risk for execution — but it **is** a staleness risk for every line
number and `grep -c` baseline quoted in a plan. Every plan below therefore states
its `<interfaces>` baselines as **commands to re-run**, not as facts, exactly as
23-01 did.

---

## The D-item dossier

### D21 — battery ring gauge, reused small in Home's tile

- **Data:** `history_db.latest_device_health()` → `battery_mv` →
  `battery.battery_percent()`. Both consumers already fetch this row today
  (`home_page._latest_battery`, health's battery section).
- **Shape:** two concentric arcs (track + value) on a `viewBox`, the value arc's
  length set by the fraction. An arc is a `<path>` with an explicit
  `fill="none"` and a stroked class — contract rule 4's "deliberately unfilled"
  case, which the plan must state rather than leave implied.
- **The one-emitter rule (CFG-40):** one function, a size parameter, two call
  sites. Two similar functions is the failure; so is a CSS-only "small variant"
  that changes stroke width without changing the geometry it was derived from.
- **Honesty:** the readout is already labelled `≈`. The gauge must not look more
  precise than the estimate is — no tick marks implying calibration.
- **Accessibility:** the gauge is decorative *if* the percentage is already in
  text beside it (it is, in both places). Then `aria-hidden` is correct and a
  `role="img"` + label would make a screen reader say it twice — the same reasoning
  the sparkline's axis labels already use.

### D8 — battery chart: gradient area, marked last point, low-battery threshold

- **Data:** unchanged — `daily_battery_averages()` (90-day primary) with the
  `recent_device_health()` raw fallback. **Do not change what it plots.**
- **Gradient area:** a `<path>`/`<polygon>` closing the line down to the baseline.
  Note the existing scheme's constraint: **percentages are not permitted in a
  `<polyline points>` list** — which is why the line is `n-1` `<line>` segments.
  The same constraint applies to a `<polygon>`, so the area must be built as a
  `<path>` with a `d` that can carry percentage-free user units *or* the drawing
  must place the area with `<rect>`s. **This is the plan's first real design
  question and it must be resolved by experiment in the plan, not assumed.**
  A defensible fallback that keeps the whole scheme intact: render the area as one
  `<rect>` per segment clipped by… no — simpler and honest: give the area its own
  nested `<svg>` with a `viewBox` sized to the point count, so the `d` can use
  plain user units while the outer canvas keeps its percentage scheme. Either
  resolution is acceptable; silently switching the whole chart to a `viewBox` is
  not, because it would shrink every stroke and every hit target at 360 px.
  *(A "gradient" here should be a token-derived opacity fade, not a new colour: a
  `<linearGradient>` whose stops are `currentColor` at two opacities keeps the
  theme binding intact.)*
- **Marked last point:** a distinct class on the final `<circle>`. It must be
  derived from the same filtered pair list as every other point (contract rule 2),
  or it will mark the wrong reading whenever the newest row lacks `battery_mv`.
- **Low-battery threshold:** a horizontal rule at the threshold's y, plus a label
  outside the SVG. The threshold value belongs in `companion/battery.py` (CFG-39),
  **not** re-typed in `health_page.py`, and it must be documented as the
  *companion's display threshold*, distinct from the device's own millivolt
  warning in `server/poll_loop.py`. Two numbers presented as one rule is the
  predictable confusion here.

### D13 — Home's day timeline

- **Data:** `device_health` rows for the last 24 h (check-ins), the quiet-hours
  window from `device_config` via `wake.quiet_hours_status()`/
  `seconds_until_quiet_hours_end()`, and optionally `runway_events` for detections.
- **Shape:** a horizontal 24 h band with a tick per check-in and a shaded
  quiet-hours span; the only drawing in this phase whose x axis is *time*, not
  index, so its scale helper is genuinely different from the sparkline's.
- **The trap:** a 24 h band at 360 px is ~330 px wide; ticks one minute apart are
  sub-pixel. The plan must decide and state the minimum tick spacing and what
  happens when several check-ins collapse into one — and the caption must not
  claim a count the drawing does not show.
- **Paris days:** the band is a *Paris* day (`_paris_day_or_none`'s convention),
  not a UTC one, or it will disagree with every other date on the page.

### D20 — the grid

See Risk 1. Built on Option B. Cells are Paris days × hour buckets (or day ×
observed-gap, the plan decides and states which), each cell coloured on the
existing status tokens, each cell's `<title>` naming the real observed gap in local
time.

### D4 — the Home hero the others feed

- **Constraint:** "fed by" must mean *calls the same emitters*, never *contains a
  second copy*. The harness check for CFG-44 is therefore structural: the hero's
  ring must be the same function D21 defines, proven by mutating that function and
  seeing the hero change.
- Home's current top is: header → Frame strip → three stat tiles → picture/recent-
  flights row (`home_page.render()`). The hero must be composed **without**
  reintroducing the phase-20 status-card builder that 21-04 deleted, and without
  a second copy of the Frame verdict — Home renders that verdict exactly once
  today and `_status_tiles_html()`'s docstring records that as a fixed bug.

---

## Validation Architecture

**What must be validated, and by what instrument:**

| Dimension | Instrument | Where |
|-----------|-----------|-------|
| The drawing contract holds for every emitter | source scan over emitter output (no colour literal, every shape has a fill route, every emitted class resolves in `style.css`) | `companion/test_companion_app.py` |
| One estimator, no second copy | source scan: the millivolt constants appear in `companion/battery.py` only | `companion/test_companion_app.py` |
| Labels name reachable values | direct unit assertions on each emitter's return against a seeded series, including a series with a `None` newest reading | `companion/test_status_pages.py`, `companion/test_view_pages.py` |
| Renders with scripts blocked | real Chromium, scripts blocked | `companion/test_browser_ux.py` |
| 360 px, no horizontal body scrollbar | real Chromium, measured `document.body.scrollWidth` vs `clientWidth` | `companion/test_browser_ux.py` |
| Legible in both themes | real Chromium in each theme, computed paint of each drawing's shapes is not the default black and differs between themes where the token does | `companion/test_browser_ux.py` |
| viewBox contains its outermost label | real Chromium `getBBox()` against the viewBox | `companion/test_browser_ux.py` |
| Motion budget unmoved | the existing 24-01-era guard from 23-01 | `companion/test_companion_app.py` |
| French parity | existing i18n sweep | `companion/test_i18n.py` |

**Sampling adequacy (the Nyquist question):** each drawing must be asserted at
**at least** these series shapes, because each is a real state of this deployment —
empty (no rows), one row (below the "two points" floor), two rows, a series whose
newest row lacks `battery_mv`, a series with an out-of-range value, and a dense
series past the density threshold. A check that only exercises the happy series is
vacuous for four of the six states this app actually reaches.

---

## Recommended plan shape

Nine plans, seven waves. Wave 1 is parallel (three plans, disjoint files); the rest
are serial because `companion/static/style.css`, `health_page.py` and `home_page.py`
are each written by several plans and this project's rule is **one writer per file
per wave** (Phase 23 ran 11 plans across 9 waves for the same reason).

| Plan | Wave | Owns | Depends on |
|------|------|------|-----------|
| 24-01 | 1 | `companion/battery.py`, `companion/draw.py` (new), `style.css` (drawing foundation), `test_companion_app.py` | — |
| 24-02 | 1 | `companion/test_browser_ux.py` (harness helpers, zero net checks) | — |
| 24-03 | 1 | `server/history_db.py`, `server/poll_loop.py`, `server/test_poll_loop.py`, a new server-side reader test | — |
| 24-04 | 2 | `draw.py` (ring), `style.css`, `health_page.py`, `home_page.py`, `test_status_pages.py`, `test_view_pages.py`, both i18n modules | 24-01, 24-02 |
| 24-05 | 3 | `health_page.py`, `style.css`, `test_status_pages.py` | 24-01, 24-04 |
| 24-06 | 4 | `home_page.py`, `style.css`, `test_view_pages.py` | 24-01, 24-04 |
| 24-07 | 5 | `health_page.py`, `style.css`, `test_status_pages.py` | 24-03, 24-05 |
| 24-08 | 6 | `home_page.py`, `style.css`, `test_view_pages.py` | 24-04, 24-06 |
| 24-09 | 7 | `sketch-findings-skypane/**`, the coverage ledger, the phase gate | all |

---

## Open decisions recorded for the developer (all PROVISIONAL)

1. **D20's metric** — Option B (observed check-in regularity) recommended over
   Option A (schema growth). See Risk 1. *Plans proceed on B.*
2. **D20's forward-looking data (Option C)** — a new `wake_epochs` table written by
   the poll oneshot, read by nothing in this phase. Recommended because it is cheap
   and migration-free; droppable without affecting any drawing. *Plans include it,
   isolated in 24-03 Task 3 so it can be cut whole.*
3. **The grid's name** — "Check-in regularity", not "wake punctuality". *Plans
   proceed on the honest name.*
4. **D8's area geometry** — nested `viewBox` for the area vs `<rect>` segments vs
   a user-unit `<path>`. Resolved by experiment inside 24-05, with the outer
   canvas's percentage scheme non-negotiable. *No developer input needed unless the
   experiment fails, in which case the fallback is "no area, keep the line".*
5. **Whether the day timeline (D13) plots detections as well as check-ins** —
   recommended: check-ins and the quiet-hours span only, because a detection tick
   and a check-in tick on one band at 360 px is two vocabularies in ~330 px.
   *Plans proceed on check-ins + quiet hours; detections deferred.*
6. **Motion on the drawings** — none in this phase. See *Deferred*.
7. **No CONTEXT.md** — this phase was planned without `/gsd-discuss-phase`. Every
   decision above would normally have been the developer's.

---

*Research completed: 2026-09-13*
*Method: direct reading of this tree (no web research was needed — every question
this phase raises is answered by code already in the repository)*
