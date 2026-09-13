---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 03
subsystem: ui
tags: [time, i18n, relative-time, layout, home, no-js-floor, harness]

requires:
  - phase: 20-03
    provides: "relative_age_text()'s language-aware s/m/h/d ladder and its French catalogue entries, which this plan wraps rather than copies"
  - phase: 22-06
    provides: "concise_timestamp_html()'s D-05/B4 no-raw-ISO rule, which forced the element's datetime attribute to carry a CONVERTED instant rather than the raw stored string"
  - phase: 22-07
    provides: "_recent_flight_time_html()'s C5 clock/age role split, which this plan wraps inside rather than undoes"
provides:
  - "layout.relative_time_html(ts, now_ts, fallback, lang): the app's ONE <time datetime data-relative> element, server-rendered text, both directions"
  - "layout.relative_future_text(seconds_ahead, lang): the same ladder read forwards, clamped at zero, for 23-06's countdown"
  - "layout._age_bucket(age_seconds): the three s/m/h/d boundaries with ONE site each (they had two, one per language branch)"
  - "layout._machine_instant(parsed): the Europe/Paris ISO the datetime attribute carries"
  - "'in a moment' / 'in %s' in companion/i18n_fr/health.py — the future form's French, server-side, so 23-05's ticker carries none"
  - "every surface reading through concise_timestamp_html() inherits the element with no page-module change: Health, Flights, Airlines, Home's caption"
affects: [23-05, 23-06, 23-08, 23-11]

tech-stack:
  added: []
  patterns:
    - "a semantic element wrapped AROUND an existing role span rather than replacing it — <time> carries meaning, .time-value carries presentation, and the two stack"
    - "one ladder read in two directions from one bucket function, so the past and future forms cannot disagree about where a bucket ends"
    - "a machine-readable attribute carrying a CONVERTED instant, because a page-wide 'no raw ISO' rule already shipped and an attribute is not an exemption from it"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/i18n_fr/health.py
    - companion/pages/home_page.py
    - companion/test_status_pages.py
    - companion/test_view_pages.py

key-decisions:
  - "The datetime attribute carries the Europe/Paris ISO instant, NOT the raw stored string the plan's <interfaces> implied ('the same value data-loaded-at carries'). Two shipped checks forbid the raw ISO surviving into concise_timestamp_html()'s output (test_status_pages.py's _timestamp_helpers_promoted_not_duplicated and _concise_timestamp_html_title_is_a_full_local_timestamp_not_raw_iso, both D-05/B4). Mutation M7 proves it: reverting to the raw string fails three checks. The offset is included, so the instant is unambiguous to 23-05's script."
  - "The ladder's boundaries were shared by extracting _age_bucket(), NOT by adding three module constants. The plan offered either; the helper gives each boundary exactly ONE site (grep -c 'if age_seconds < 60' is now 1, and was 2 before this plan, not 0 — the French and English branches each carried the whole ladder), which is strictly what the criterion asked for. relative_age_text()'s output is byte-identical for every input."
  - "The parentheses stay OUTSIDE the element. They are the format's punctuation, not part of the age, and putting them inside would force 23-05's ticker to reproduce them and would break the 'inner text EQUALS relative_age_text()' contract. Cost: three shipped assertions on the literal substring ' ago)' had to be retargeted in place, which the plan anticipated."
  - "The French future form gets its own sub-minute collapse ('in a moment' -> 'dans un instant') mirroring the past form's 'à l’instant', rather than a literal second count. English stays compact ('in 4m'), mirroring the past form's '4m ago' rather than the plan's prose example 'in 4 min' — which is what the FRENCH renders ('dans 4 min')."
  - "relative_time_html() takes a `fallback` keyword the plan's illustrative signature omitted, placed exactly where absolute_and_relative() and concise_timestamp_html() place theirs, so the three siblings are callable the same way."

requirements-completed: []

duration: ~2h
completed: 2026-09-13
---

# Phase 23 Plan 03: The `<time data-relative>` server convention Summary

**The app renders its first `<time>` element ever — server-rendered text, a
machine-readable Europe/Paris instant, and a future form sharing the one existing
ladder's own boundaries — and Home's two visible ages, Health, Flights and
Airlines all now carry something a script can find, while reading exactly as
they did before.**

## Performance

- **Duration:** ~2 h
- **Tasks:** 2/2
- **Files modified:** 5 (0 created)

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 (RED) | `9a29c75` | test(23-03): pin the `<time data-relative>` convention before it exists |
| 1 (GREEN) | `7156ab1` | feat(23-03): the `<time data-relative>` element, and the ladder read forwards |
| 1 (fix) | `e2dcbd0` | test(23-03): make the shared-boundary check non-vacuous |
| 2 | `a7d5ed5` | feat(23-03): Home's visible relative ages become elements |

## What landed

### Task 1 — the element, and the ladder read forwards

**`_age_bucket(age_seconds)`** — extracted out of `relative_age_text()`,
unchanged, returning `(value, unit_letter)`. This is now the only place the three
boundaries are written down. Before this plan each of them had **two** sites, not
one: `relative_age_text()`'s French and English branches each carried the whole
ladder. The unit letters are the English suffixes themselves, so the English
branch formats straight from the pair (`"%d%s ago"`) and the French branch maps
them through the existing `_AGE_UNIT_SUFFIX_FR`. Output is byte-identical for
every input in both languages, asserted by the two Section 1.8 checks that
already existed and by the new equality checks.

**`relative_future_text(seconds_ahead, lang=None)`** — the same buckets read
forwards. English `in 4m`; French `dans 4 min` with a real U+00A0, connector from
a catalogue entry. An already-elapsed instant resolves to the zero bucket through
`_age_bucket()`'s own clamp — never a negative, never a past-tense string. Its
docstring states, in the file, that it is formatting and never a verdict: it says
how long remains until an instant somebody else computed and never says "late",
"held" or "due". Those words stay `frame_state`'s.

**`relative_time_html(ts, now_ts, fallback="no reading yet", lang=None)`** — the
element. `<time datetime="<Paris ISO>" data-relative><ladder's own text></time>`.
Nothing else in the element: no class carrying meaning, no state word. It chooses
its direction from the sign of the age, so one function serves both and 23-06 has
nothing to add. It degrades to escaped plain text — never a raise, and never an
element carrying an empty or invented `datetime`, which would read as a correct
time to a script and is worse than no element. Its docstring carries the
raw-markup contract in the same words `concise_timestamp_html()`'s does, and says
explicitly that **this function's output IS the no-JS path**, not an enhancement
over one.

**`_machine_instant(parsed)`** — the attribute's value: the instant converted onto
Europe/Paris at seconds precision, offset included, naive taken as UTC the way
`local_clock_text()` takes it. See the deviation below for why this is not the
raw string the plan's `<interfaces>` implied.

**`concise_timestamp_html()`'s relative half** is now that element. Its outer
span, its class, its `title` and its absolute-first ordering are untouched, and
the diff is confined to the one interpolation argument. This is where most of the
plan's value landed: **Health, Flights, Airlines and Home's own caption inherited
the element without any of those page modules changing at all.**

**French** — `"in a moment": "dans un instant"` and `"in %s": "dans %s"` sit
beside `"just now"`/`"%s ago"` in `companion/i18n_fr/health.py`, read through
`i18n.t_lang()`. `test_i18n.py`'s Check 2 (every catalogue entry is read by some
scanned source) passes because `layout.py` is in the scanned set — the same shape
the past form already used.

### Task 2 — Home, and the inventory

`_recent_flight_time_html()`'s age half is now the element. C5's split is intact:
the clock keeps `.time-value`, the age keeps `.time-value__age`, the dot keeps
`.cell-inline-sep`, and the documented reason this cell does not reach for
`concise_timestamp_html()` still holds and is restated in the docstring. The
element sits **inside** the role span rather than replacing it — semantic and
presentational stack, they do not compete.

Home's rendered-picture caption **needed no page-module change at all**: Task 1
had already converted it. Its check was written anyway, and it is not redundant:
the caption reaches the page through an i18n template's own `%s`, so an escaping
mistake there would paint literal markup rather than remove an element. Mutation
M9 confirms it catches exactly that.

## The inventory (Task 2's real deliverable)

Every `relative_age_text(` / `absolute_and_relative(` call site in
`companion/pages/`, split three ways. Counts are `grep -rc` totals over
`companion/pages/*.py`, which include prose mentions in docstrings and comments —
the code call sites are listed by line individually.

| File | before | after |
|---|---|---|
| `airlines_page.py` | 1 | 1 |
| `config_page.py` | 3 | 3 |
| `health_page.py` | 6 | 6 |
| `history_page.py` | 6 | 6 |
| `home_page.py` | **1** | **0** |
| `__init__.py` | 0 | 0 |

### 1. CONVERTED HERE

| Site | What |
|---|---|
| `home_page.py:544` (was `:527`) | the recent-flight age — `relative_age_text()` → `relative_time_html()`. The one line that moves Home's count 1 → 0. |
| `layout.py` `concise_timestamp_html()` | the shared producer. Converting it converted, for free and with no page-module edit, **every** surface that reads through it: `health_page.py:2007, 2171, 2277, 2562, 3162, 3182`; `history_page.py:1324`; `airlines_page.py:712, 1642, 1643`; and `home_page.py:430` (Home's own caption). |

### 2. CONVERTED BY A LATER PLAN

| Site | Plan | Why not here |
|---|---|---|
| `health_page.py:3009` — the freshness line's own `escape_html(relative_age_text(age))` | **23-06** | `health_page.py` is not in this plan's `files_modified`; 23-06 owns it and its own plan text already says it promotes this freshness line into `layout.py` as one builder. Converting it here would collide with that promotion. |
| `health_page.py:1150` — `_full_local_timestamp_text(ts) + relative_age_text(age)`, the `when` text `battery-trend.js` copies into a `title` | **23-06** | This one is **plain text by contract on purpose**: `battery-trend.js` writes it into a `title` attribute with `setAttribute`, and a shipped check (`_battery_trend_js_has_no_client_side_date_math`) pins that it is pre-formatted text with no client-side date math. Markup in a `title` renders as literal angle brackets. If 23-06 wants this live it must change the JS's transport, not this string. |
| `history_page.py:1011` — the mobile card's relative-age secondary line | **23-08** | `history_page.py` is 23-08's file. Straightforward conversion; nothing blocks it. |
| `history_page.py:659` — `format_event_row()`'s `absolute_and_relative()` | **23-08**, if at all | See list 3 — this is the `data_table()`-cell case, and converting it is a different change with a different risk. |

### 3. NOT CONVERTED, with the reason

| Site | Reason |
|---|---|
| `history_page.py:659` — `absolute_and_relative(row["ts"], now, fallback="")` | `absolute_and_relative()` returns **plain, unescaped text by contract** (its own docstring says so), because its callers put the value in `data_table()` cells that escape every cell they are given. Converting it means widening the table builder's `raw_columns` set for that column — a different change, with a different blast radius (every other consumer of that builder), and it belongs to whichever plan owns the table builder, not to this one. |
| `config_page.py:2534, 2537` — the calendar-registry detail lines | `config_page.py` is not in this plan's `files_modified` and is owned by 23-06/23-07 in later waves. These are **status detail strings**, not a clock beside a time: "N entries, refreshed 3m ago". They are live-capable and nothing blocks them; they are simply not this plan's file. |
| `health_page.py:1150` | Listed above under 23-06, but the reason is structural rather than scheduling: it is consumed by a `title` attribute. Repeated here because this is the one site in the codebase that **cannot** become an element without changing a JS transport first. |
| `airlines_page.py:696` | Prose only — a docstring mentioning the pair. No call site. |
| `history_page.py:143`, `health_page.py:1112, 1126, 2966, 3043`, `config_page.py:2452`, `history_page.py:655, 663, 982` | Prose only — docstrings and comments naming the functions. They inflate the `grep -rc` totals above and are listed so the counts reconcile. |

## Acceptance criteria — every one run literally

**Task 1**

| Criterion | Expected | Got |
|---|---|---|
| `grep -c 'data-relative' companion/layout.py` | ≥ 1 (pre-task `0`) | **3** (pre-task `0` confirmed) |
| `grep -c '<time ' companion/layout.py` | ≥ 1 (pre-task `0`) | **2** (pre-task `0` confirmed) |
| `grep -rn '<time' companion/` | no matches at all, pre-task | confirmed: zero, across `.py`, `.js` and `.html` |
| harness asserts inner text EQUALS `relative_age_text()` for four buckets in both languages; breaking one bucket's wrapper produces exactly one failure | — | **exactly one** (272 → 271), message quoted below (M1) |
| `grep -c 'if age_seconds < 60' companion/layout.py` | `1` | **`1`** — but the pre-task value was **`2`**, not `0`. See deviation 2. |
| `grep -c 'age_seconds < 3600'` / `'age_seconds < 86400'` | `1` each | **`1`** each (pre-task `2` each) |
| `companion/test_i18n.py` exits 0 | — | **24/24** |
| `test_status_pages.py` / `test_view_pages.py` at their new pins | — | **272/273** (the documented `anomaly_active()` FAIL) and **144/144** at Task 1's pin |
| `ruff check .` | clean | `All checks passed!` |

**Task 2**

| Criterion | Expected | Got |
|---|---|---|
| a rendered Home page contains ≥ 1 `data-relative`, each with a non-empty `datetime`, asserted against a seeded fixture | — | asserted in both new checks, both languages; the recent-flight element's instant is proven to be the ROW's (mutation M11) |
| `grep -rc 'relative_age_text(\|absolute_and_relative(' companion/pages/*.py` before and after, every site in exactly one list | — | table above; `home_page.py` 1 → 0, every other file unchanged |
| no rendered string changed, in both languages | — | asserted by equality against `relative_age_text()` / `concise_timestamp_html()` themselves, never a hand-typed literal |
| `test_status_pages.py` at its new pin | — | **272/273**, the documented `anomaly_active()` FAIL only |
| `scripts/run-all-tests.sh`: no new failure, coverage ≥ 83 | — | **3 FAILED harnesses, exactly the documented 5-check root-sandbox baseline**; coverage **93%** |
| `ruff check .` | clean | `All checks passed!` |

## Mutation tests

Every new check was mutation-tested. Baseline: `status-pages 272/273`,
`view-pages 146/146`. Each mutation was applied, the harness run, then reverted;
the tree is clean and all harnesses are back at baseline.

| # | Mutation | Result | Failure message (verbatim, after the check name) |
|---|---|---|---|
| M1 | the hours bucket re-derived beside the ladder instead of from it | 272 → **271** (exactly one) | ``lang=fr age=7200s: expected the element's own text to EQUAL relative_age_text()'s output 'il y a 2\xa0h', got '2h ago' — a wrapping that changes the string is a second ladder, not a wrapping`` |
| M2 | the falsy-timestamp degrade path emits `<time datetime="">` | 272 → **271** | ``a falsy timestamp must NOT produce a <time> element — an element with an empty or invented instant is worse than no element, got '<time datetime="" data-relative>no reading yet</time>'`` |
| M3 | the future form given its own sub-minute boundary (120s) | **272 → 272 — VACUOUS.** See below. Re-run after the check was repaired: 272 → **271** | ``lang=en seconds=60: expected the future form to name the SAME bucket and the SAME number the past form names ('in 1m'), got 'in 60s' — a direction that picks its own boundary is a second ladder`` |
| M3b | the French future form loses its U+00A0 | 272 → **271** | ``lang=fr seconds=60: expected the future form to carry a quantity with a real U+00A0 the way the past form 'il y a 1\xa0min' does, got 'dans 1 min'`` |
| M3c | the French future form stops collapsing the sub-minute bucket | 272 → **271** | ``lang=fr seconds=0: the past form collapses the sub-minute bucket to a phrase with no number ('à l’instant') and the future form must collapse the same bucket, got 'dans 0\xa0s'`` |
| M4 | `relative_time_html()` drops its future branch (one direction only) | 272 → **271** | ``lang=en: expected a future instant's element to carry the future form 'in 4m', got '0s ago'`` |
| M5 | `concise_timestamp_html()` reverts its relative half to a bare escaped string | status 272 → **270**, view 146 → **144** | ``expected concise_timestamp_html()'s relative half to be a <time data-relative> element, got '<span class="mono" title="12 Sep 00:30">00:30 (13h ago)</span>'`` — plus **both retargeted checks**, which is the proof they were retargeted and not weakened |
| M6 | an ISO leak added OUTSIDE the exempted element shape (a `data-ts` on the mono span) | view 146 → **144** | ``expected zero ISO-8601 timestamps in the resolve fallback render, found ['2026-09-09T15:49', '2026-09-11T06:05']`` — the widened sweep still catches a real leak; a second, unrelated shipped check caught it too |
| M7 | `_machine_instant()` stops converting and carries the raw stored string | status 272 → **269** | ``expected zero occurrences of the RAW ISO string — the element's own instant is the Europe/Paris form, so D-05/B4's no-raw-ISO rule still holds (22-06 Task 3)`` — plus both pre-existing D-05/B4 checks |
| M8 | Home's age reverts to a bare escaped string | view 146 → **145** | ``lang=en: expected the age half to be a <time data-relative> element, got '10m ago'`` |
| M9 | the caption template escapes the element again | view 146 → **144** | ``lang=en: the caption... got 'Rendered &lt;span class=&quot;mono&quot;...&lt;time datetime=&quot;2026-08-27T13:50:00+02:00&quot; data-relative&gt;10m ago&lt;/time&gt;...'`` — and the recent-flight check's own ``found a double-escaped '&lt;time' — a raw-markup producer was escaped again by its caller`` |
| M10 | the caption's instant comes from the page's `now` instead of the picture's | view 146 → **145** | ``lang=en: expected the caption to be its unchanged wording around concise_timestamp_html()'s own output ... got 'Rendered <span class="mono" title="27 Aug 14:00">14:00 (<time datetime="2026-08-27T14:00:00+02:00" data-relative>0s ago</time>)</span>...'`` |
| M11 | Home's element carries the page's `now` instead of the row's instant | view 146 → **145** | ``lang=en: expected Home's recent-flight age to read exactly what it reads today ('10m ago'), got '0s ago'`` |

**M3 was vacuous and the check was repaired (commit `e2dcbd0`).** The
shared-boundary check asserted only that both directions were non-empty, carried
no minus sign and differed from each other — all of which a second, *disagreeing*
ladder satisfies. Its own comment claimed it compared the unit each direction
picks; it did not. It now compares the **quantity**: in English the past form
rearranged *is* the future form, which pins number and unit exactly; in French it
compares the number and unit for the three buckets that carry one and asserts the
sub-minute collapse for the one that does not. M3, M3b and M3c all now fail with
the defect named. **A vacuous check is why every new check here was mutated
rather than assumed.**

## `EXPECTED_CHECK_COUNT`

Both re-derived by **running** the harness, never by arithmetic, and appended as
new last assignments citing this plan:

| Harness | Before | After | Task |
|---|---|---|---|
| `companion/test_status_pages.py` | 268 | **273** (+5) | Task 1 |
| `companion/test_view_pages.py` | 143 | **144** (+1) | Task 1 |
| `companion/test_view_pages.py` | 144 | **146** (+2) | Task 2 |

No pre-existing check was deleted or excepted. Three were **retargeted in place**
(no count change), each with a comment saying so and why.

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_status_pages.py` | 267/268 | **272/273** | 1 × `anomaly_active()` (documented root-sandbox) |
| `companion/test_view_pages.py` | 143/143 | **146/146** | — |
| `companion/test_i18n.py` | 24/24 | **24/24** | — |
| `companion/test_companion_app.py` | 271/273 | 271/273 | 2 × WR-11 read-only (documented root-sandbox) |
| `companion/test_config_page.py` | 233/233 | 233/233 | — |
| `companion/test_contrast_check.py` | 43/43 | 43/43 | — |
| `companion/test_browser_ux.py` | 26/26 | 26/26 | — (this plan never opened the file) |
| `server/test_manual_resolutions.py` | 21/23 | 21/23 | 2 × WR-11 read-only (documented root-sandbox) |

`scripts/run-all-tests.sh` reports three FAILED harnesses carrying **exactly the
documented 5-failing-check root-sandbox baseline** (4 × WR-11, 1 ×
`anomaly_active()`). No new failure. Coverage **93%** (floor 83). `ruff check .`
clean. No test exception was added anywhere.

## Deviations from Plan

**1. [Rule 1 — Bug] The `datetime` attribute carries a CONVERTED instant, not the
raw ISO string.** The plan's `<interfaces>` says the attribute carries "the same
value `data-loaded-at` carries", which is the raw stored string. It cannot: two
shipped checks assert that the raw ISO does **not** survive into
`concise_timestamp_html()`'s output (`_timestamp_helpers_promoted_not_duplicated`
and `_concise_timestamp_html_title_is_a_full_local_timestamp_not_raw_iso`, both
D-05/B4 from 22-06). `_machine_instant()` therefore emits the same instant on
Europe/Paris with its offset — still machine-readable, still unambiguous to
23-05's `new Date()`, and still not the raw string. **Mutation M7 is the proof:
reverting to the raw string fails three checks at once.** Found during Task 1.
Commit `7156ab1`.

**2. [Rule 3 — Blocking] The boundary criterion's pre-task value was 2, not 0 or
1.** `grep -c 'if age_seconds < 60' companion/layout.py` returned **2** on the
untouched tree, because `relative_age_text()` carried the whole ladder twice —
once in the French branch, once in the English. The criterion as written ("outputs
`1`") did not hold *before* this plan either. The shape taken is the criterion's
own stated alternative, implemented tighter than it asked: rather than three
module constants referenced twice each, the boundaries live inside one
`_age_bucket()` helper, so each has exactly **one** site and the criterion now
literally outputs `1`. Recorded rather than adjusted; the code was not bent to fit
a number.

**3. [Rule 3 — Blocking] Task 2's Home checks went into `test_view_pages.py`, not
`test_status_pages.py`.** The plan's Task 2 `<files>` names
`companion/test_status_pages.py`, but Home is not rendered there at all —
`grep -c "home_page\." companion/test_status_pages.py` is **0** and
`companion/test_view_pages.py` is **42**. `test_view_pages.py` is already in this
plan's `files_modified` (Task 1), so there is no ownership conflict and
`test_browser_ux.py` was never opened. Task 2's `<verify>` block, which runs only
`test_status_pages.py`, was therefore supplemented with `test_view_pages.py`.

**4. [judgement] `relative_time_html()` takes a `fallback` keyword.** The plan's
action text writes the signature as `relative_time_html(ts, now_ts, lang=None)`
while its behaviour list requires "a plain fallback". `fallback="no reading yet"`
sits exactly where `absolute_and_relative()` and `concise_timestamp_html()` put
theirs, so the three siblings are callable identically and `lang` stays a trailing
keyword. Positional compatibility for `(ts, now_ts)` is unchanged.

**5. [judgement] English's future form is compact.** The plan's prose says
"in 4 min". That is what **French** renders (`dans 4 min`); English renders
`in 4m`, mirroring the past form's `4m ago` rather than introducing a second
English unit vocabulary. The plan's own binding constraint is that the two
directions share a ladder, and a compact/verbose split across directions would
have broken that in the only place a reader would notice.

**6. [process] Three shipped assertions on the literal substring `" ago)"` were
retargeted in place.** `test_status_pages.py:1173` and `test_view_pages.py:1459`
now match `\(<time datetime="..." data-relative>... ago</time>\)`, which asserts
strictly more than the substring did: the parentheses are still the format's own
punctuation outside the element, and the age between them is the element's text.
The plan anticipated this set ("this is the set that will move"). Neither check
was deleted, weakened or excepted; M5 fails both, which is the proof.

**7. [process] One shipped check's page-wide ISO sweep was given one
exact-shape exemption.** `_resolve_dialog_seen_attributes_carry_formatted_paris_local_text`
asserts that *nothing anywhere* in the Airlines render matches an ISO-8601 shape.
The element's `datetime` attribute matches it by construction. The exemption is a
literal `<time datetime="..." data-relative>` substitution before the sweep, so a
change to the element convention stops exempting anything and the check fails
loudly, and every other ISO on the page is still caught — **M6 proves that**. The
line drawn is the one `test_status_pages.py` already drew for the battery chart's
`data-ts` hit targets: "D-05 is about visible/tooltip text, not every attribute".

## Findings the plan did not anticipate

**1. `grep -c 'if age_seconds < 60'` was 2 before this plan.** See deviation 2.
Any downstream plan quoting "the ladder has one definition site" should know that
before today it had two, one per language branch, and they agreed only by
inspection.

**2. `git checkout -- <file>` destroyed an unstaged implementation mid-mutation.**
While mutation-testing Task 2, the restore step `git checkout -- companion/pages/home_page.py`
reverted the file to **HEAD**, not to the pre-mutation working state — because the
Task 2 edit had not been staged. The implementation was silently lost and two
mutation runs (M9/M10, first attempt) produced contaminated results before the
missing line was noticed. Re-applied, staged, and all mutations re-run against a
staged baseline. **Every mutation number in the table above is from a run with the
implementation present.** The lesson for later plans in this phase: stage the
implementation before mutating, or back the file up out-of-tree — never rely on
`git checkout --` to undo a mutation applied on top of unstaged work.

**3. Converting `concise_timestamp_html()` did most of the work.** Ten call sites
across four page modules inherited the element with no page-module edit at all.
That is why the plan's ordering (shared producer first, page second) matters, and
it is why Home's caption check passed the moment it was written — which the
`EXPECTED_CHECK_COUNT` comment records so nobody later reads it as a redundant
check.

**4. Home's `grep -rc` count goes to zero, and that is the honest signal.**
`companion/pages/home_page.py` now calls neither `relative_age_text()` nor
`absolute_and_relative()` directly. Every remaining nonzero count in the table is
either a later plan's file or prose.

**5. `test_browser_ux.py` was never opened, read or edited by this plan.** Plan
23-02 owns it exclusively; its commit `d716b04` landed in the shared tree during
this plan's execution and its harness still reports 26/26.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-07 | mitigate | The instant is server-computed (`_machine_instant()` over a parsed datetime) and passed through `escape_html()` at the interpolation site. No value reaching it comes from a request parameter. The degrade path escapes its input too — asserted with a `<script>` payload in the degrade check. |
| T-23-08 | accept | Unchanged, and narrowed: the attribute carries a Paris-local instant already visible as text on the same line. It names no user and no secret. |
| T-23-09 | mitigate | The docstring states the raw-markup contract in `concise_timestamp_html()`'s own words. Both new page-level checks assert rendered-output **equality** against the producing function and explicitly fail on a literal `&lt;time`. Mutation M9 (an added `escape_html()` at the caption's call site) fails two checks with the double-escape named. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. |

## Known Stubs

None. `relative_future_text()` has no call site on a rendered page yet — 23-06's
countdown is its first consumer — but it is not a stub: it is fully implemented,
fully translated and fully tested, and nothing on screen renders a placeholder
because of it. This plan's output renders identically to the page shipped before
it, which is the stated goal, not an unfinished state.

## Notes for later plans

- **23-05** must read the boundaries from **`layout._age_bucket()`**, not from
  `relative_age_text()`'s body — the plan text points at `layout.py:787-833` and
  "relative_age_text()'s three bucket boundaries", which no longer contains them.
  Any harness check comparing the script's literals to `layout.py`'s should
  `inspect.getsource(layout._age_bucket)`.
- **23-05**'s ticker reads `datetime` as a **Europe/Paris ISO with an offset**
  (e.g. `2026-08-27T13:50:00+02:00`), not a UTC/`Z` string. `new Date()` parses it
  correctly; do not assume UTC.
- **23-05** needs no French: `relative_future_text()` and `relative_age_text()`
  both resolve their copy server-side. If the script must re-render text
  client-side, the unit words and connectors have to come from attributes on
  `<body>`, exactly as `REFRESH_PAUSED_TEXT` already does.
- **23-06** gets its countdown for free: `relative_time_html()` already reads a
  future instant. It also owns `health_page.py:3009` and `:1150` — the second of
  those is consumed by `battery-trend.js` as a `title`, so it cannot become an
  element without changing that JS's transport.
- **23-08** owns `history_page.py:1011` (straightforward) and `:659` (the
  `data_table()`-cell case — needs `raw_columns` widened first, or leave it).
- **23-11**'s coverage ledger should take list 3 above verbatim; `CFG-34`'s box is
  deliberately left unticked, as instructed.
- **Anyone mutating in this tree:** stage first. See finding 2.

## Self-Check: PASSED
