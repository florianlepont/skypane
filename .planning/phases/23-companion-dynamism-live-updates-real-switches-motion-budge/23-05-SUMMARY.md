---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 05
subsystem: ui
tags: [javascript, time, relative-time, i18n, motion, freshness, no-js-floor, playwright, harness]

requires:
  - phase: 23-01
    provides: "@keyframes skypane-pulse and --motion-slow, which the breathing rule spends; and the guard that rejects a bare duration literal"
  - phase: 23-02
    provides: "test_browser_ux.py's check()/EXPECTED_CHECK_COUNT convention and VIEWPORT_MIN_SUPPORTED, used by the no-JS half at 360px"
  - phase: 23-03
    provides: "<time datetime data-relative>, relative_age_text()/relative_future_text() and _age_bucket() — the elements this plan ticks and the ladder it mirrors"
  - phase: 22-15
    provides: "freshness.js's retry ladder, in-flight guard, targeted swap and neutral Paused/Reconnecting badge — extended by four call sites and otherwise byte-identical"
provides:
  - "companion/static/relative-time.js: the thirteenth deferred script on the authenticated shell — every <time data-relative> rewritten once a second, nothing at all in a hidden tab"
  - "layout.RELATIVE_TIME_SCRIPT_SRC / app.RELATIVE_TIME_SCRIPT_ROUTE: the fourteenth static script route"
  - "layout.relative_copy_attrs(lang): the ticker's nine wordings as (attribute, translated text) pairs, rendered onto <body> by page_shell()"
  - "layout.relative_time_html(..., countdown=True): a countdown that reads a neutral, translated 'waiting…' once its instant has passed, never an age"
  - "style.css .is-breathing: the one consumer of the app's one keyframes block, at --motion-slow"
  - "health_page.REFRESH_LIVE_DOT_ATTR and the freshness line's neutral dot, toggled by freshness.js's own derived state"
  - "Health's freshness line as a LIVE age over the same instant data-loaded-at carries, with the absolute timestamp in its tooltip"
affects: [23-06, 23-07, 23-08, 23-11]

tech-stack:
  added: []
  patterns:
    - "a client-side formatter carrying ZERO language logic: one complete wording per bucket per direction, so a language that collapses a whole bucket into a numberless phrase is DATA (a wording with no place to substitute into) rather than a branch"
    - "a placeholder chosen against a harness rather than against habit — '#' and not '%s', because test_i18n.py's Check 3 scans every French render for a stray format artefact and is right to"
    - "a visual claim DERIVED from the state machine that already owns it, in one function called from the four places that state changes, rather than tracked in a second variable beside it"
    - "an anti-vacuity CONTROL inside a 'nothing happened' browser check: prove the same value does move under the opposite condition, in the same check, or the assertion passes on a dead element"

key-files:
  created:
    - companion/static/relative-time.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/static/style.css
    - companion/static/freshness.js
    - companion/test_companion_app.py
    - companion/test_status_pages.py
    - companion/test_i18n.py
    - companion/test_browser_ux.py

key-decisions:
  - "The ticker's copy is NINE complete wordings (four past buckets, four future, one waiting phrase), not a connector plus a unit word plus a separator plus a collapse flag. The alternative needed empty-string attributes — which break the `value || fallback` idiom Check 6 scans, because an empty string is falsy — and a language-dependent collapse flag, which is language logic in a file that must carry none. Nine wordings make the script a substitution engine with no branches."
  - "The quantity placeholder is `#`, not `%s`. These wordings reach the browser as attribute values on every rendered page, and test_i18n.py's Check 3 scans every French render for a stray `%s`/`%d`/`{}` — a `%s` here would have failed it on all six checked routes. `{n}` would have slipped past the regex, which is worse: evading a guard rather than not needing one. `#` is not a Python format artefact and cannot be mistaken for one."
  - "The nine wordings cannot drift from the ladder because a harness check fills each one with the quantity _age_bucket() picks and asserts equality against relative_age_text()/relative_future_text(), in both languages, for every bucket. They are the ladder's own output with the number lifted out, and that is asserted rather than intended."
  - "The countdown is a SERVER-rendered marker (relative_time_html(countdown=True) adds data-relative-countdown), not a client-side memory of 'this was in the future when I first saw it'. A marker survives freshness.js's swaps, is inspectable, is testable without a browser, and — decisively — lets the SERVER render the same waiting wording, so the no-JS rendering of an expired countdown is already correct instead of reading '0s ago'."
  - "The breathing class is DERIVED inside one syncLiveDot() from freshness.js's own intervalHandle and currentState, called from setState/clearState/startLoop/stopLoop. The plan asked for three places; four is what the loop actually has, because tick()'s belt-and-braces stopLoop() in a background tab would otherwise leave a stopped loop breathing."
  - "The class is `.is-breathing`, not a dot modifier. relative-time.js puts the same class on a <time> element whose countdown has run out, so it has to name the motion rather than the component — one rule, one animation block, two consumers."

requirements-completed: []

duration: ~3h
completed: 2026-09-13
---

# Phase 23 Plan 05: The thirteenth script, the breathing dot, and D22's remainder Summary

**Every relative age in the app now moves — one deferred script, one second, zero
work in a background tab — and Health's freshness line stopped claiming a moment
and started reporting now, beside a neutral dot that breathes only while the loop
is genuinely listening.**

## Performance

- **Duration:** ~3 h
- **Tasks:** 3/3
- **Files:** 1 created, 10 modified
- **Harness runtime:** `test_browser_ux.py` 60s → 80s (the four new checks cost
  ~20s, almost all of it real waits — three 2.2s settles per check, by design:
  the contract is "the user sees it change")

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 (RED) | `befabd0` | test(23-05): pin the thirteenth script, its ladder and its wording before it exists |
| 1 (GREEN) | `aa96eb0` | feat(23-05): the one-second ticker, its route, its registration and its French |
| 2 (RED) | `ed9927c` | test(23-05): pin the breathing dot and the ticking age before they exist |
| 2 (GREEN) | `cc24ae0` | feat(23-05): the live indicator tells the truth — a breathing dot and a ticking age |
| 3 | `fb4722b` | test(23-05): a browser proves it ticks, and proves a hidden tab does nothing |
| — | `b2750c0` | docs(23-05): two findings outside this plan's files, logged for 23-11 and 23-06 |

**TDD gate sequence present and in order for both implementing tasks**, and both
RED commits were proven red by running the harness against a `git archive` of the
commit itself rather than asserted: Task 1's test commit reports **270/281**
(nine reds — the retargeted script count, five registration checks, the ladder,
the wording and the countdown pins), Task 2's reports **271/276** (five reds).
Each `test(...)` is followed by its `feat(...)`. No `git stash`, no `git clean`,
no `git checkout --` over unstaged work, and `git show --name-only` was run after
every commit (23-04's lesson) — every one carries exactly the files its message
claims.

## What landed

### Task 1 — the thirteenth script

**`companion/static/relative-time.js`**, 16 065 bytes served. An ES5-subset IIFE
that returns before registering anything on a page with no `[data-relative]`
element, and otherwise rewrites every one of them once a second from that
element's own `datetime`, with `textContent` and nothing else.

**The ladder is mirrored, not invented.** `var BUCKET_BOUNDARIES = [60, 3600,
86400]` is the only place those three numbers appear in the file, and
`bucketIndex()`/`bucketQuantity()` are `_age_bucket()`'s three comparisons and its
floor divisions, read out of that array. The file's header states, in the file,
that this is a deliberate SECOND implementation of one arithmetic — the only way
to tick a counter in a browser — that Python remains the definition site, and
that a cross-file check pins the two equal. **That check exists rather than being
promised**, which is 23-RESEARCH.md's Pitfall 4 mitigated.

Following **23-03-SUMMARY.md's own note**, it reads
`inspect.getsource(layout._age_bucket)`, not `relative_age_text()`, which no
longer contains the numbers.

**The wording is data, and it carries no language logic at all.** Nine complete
wordings — `#s ago`/`#m ago`/`#h ago`/`#d ago`, `in #s`/`in #m`/`in #h`/`in #d`,
and `waiting…` — are rendered onto `<body>` by `page_shell()` through the new
`layout.relative_copy_attrs()`, translated server-side, and read back with
`getAttribute()`. The script substitutes a quantity into a wording; a wording with
no `#` in it takes none, which is how French collapsing its whole sub-minute
bucket into `à l’instant` / `dans un instant` stays DATA rather than becoming a
branch. There is not one word of French in the file.

`<body>`, not the element, for exactly the reason `REFRESH_PAUSED_ATTR`'s own
comment gives: several of these elements sit inside `freshness.js`'s swap targets
and an attribute there would be replaced out from under the script. The rendered
tag now reads:

```
<body data-refresh-paused-text="Paused" data-refresh-reconnecting-text="Reconnecting…"
      data-relative-past-s="#s ago" … data-relative-waiting="waiting…">
```

**A hidden tab costs nothing.** The interval is stopped on `visibilitychange` and
restarted on return — `freshness.js`'s own policy, in its shape, with its
double-start guard — and on return the elements are repainted IMMEDIATELY, before
the interval is re-armed. `tick()` carries the same belt-and-braces
`document.hidden` stop that file carries.

**The three taxes, paid in the same commit.** The route registered in `app.py`
(constant, `_JS_PATH`, a `_serve_relative_time_script()` delegate and its own
branch — there is no catch-all `/static/` handler); the `_SCRIPT_SRC` registered
in `layout.py` and emitted on the authenticated shell; the twelve-script check
retargeted IN PLACE to thirteen in its own comment format, stating what the
thirteenth is and why it is served everywhere; the French catalogue entries added;
and the served-route plus banned-token scan added.

**`relative_time_html(countdown=True)`** — `data-relative-countdown` on the
element, and the translated waiting wording once the instant has passed rather
than an age. No page renders a countdown yet (23-06's next-wake line is its first
consumer), but it is not a stub: it is fully implemented, fully translated,
pinned by a Python check and exercised in a browser, and the default rendering is
byte-identical to the element 23-03 shipped.

### Task 2 — the live indicator tells the truth

**`.is-breathing`**, one rule, the first and only consumer of 23-01's one
keyframes block, at `var(--motion-slow)`. No new colour, no new dot class, no
per-rule reduced-motion block — the global override reaches it for free and the
stylesheet's live `reduce` count is still 2.

**`freshness.js` gained 59 lines and lost none.** `git diff` reports
**59 insertions, 0 deletions**, which is 22-15's retry ladder, `RETRY_CEILING_MS`,
the in-flight guard, the targeted swap and the badge copy proven byte-identical
mechanically rather than by inspection. The whole change is one
`syncLiveDot()` — which DERIVES the class from `intervalHandle !== null &&
currentState === null`, the loop's own two state variables — plus four calls to
it from `setState`, `clearState`, `startLoop` and `stopLoop`, and their comments.
There is no second state machine and no second timer.

**Health's freshness line** now reads a live age over the same instant
`data-loaded-at` carries, with the full Europe/Paris local timestamp still on the
span's `title` (22-16's own D-05/CFG-28 conversion, untouched), beside a neutral
`aria-hidden` dot the server renders STILL:

```
Updated 0s ago          →  Updated 3m ago      (English, ticking)
Mis à jour à l’instant  →  Mis à jour il y a 3 min   (French, ticking)
```

The prefix copy needed no change in either language — the sentence reads
correctly with an age — so the catalogue was not touched for it.

### Task 3 — a browser proves it

Four checks, each asserting on element TEXT read twice with a real wait between
the reads, never on a timer internal.

## Acceptance criteria — every one run literally

**Task 1** — all eight ran. Seven returned exactly what the plan predicted.

| Criterion | Expected | Got |
|---|---|---|
| `grep -cE '=>\|\blet \|\bconst \|innerHTML\|insertAdjacentHTML\|document\.write\|eval\(\|` ' relative-time.js | `0` | **`0`** (see deviation 1 — it was `1` first) |
| `grep -c 'textContent'` ≥ 1 / `grep -cE '\.innerHTML\|outerHTML'` = 0 | — | **`4`** and **`0`** |
| `grep -c '60\b'` / `'3600'` / `'86400'` each ≥ 1 | — | **`1`, `1`, `1`** — exactly one each, which the harness also pins |
| deleting a boundary from the script → exactly one failure naming it | — | **279 → 278**, message quoted (M1) |
| `GET /static/relative-time.js` → `200`, asserted by the served-route check | `200` | **`200`**, `text/javascript`, `public, max-age=300`, 16 065 bytes |
| a rendered authenticated page has exactly 13 `<script src=`; `LOGIN_CARD_SCRIPT_SRC` absent; login shell emits one | — | **13**, absent, **1** |
| `grep -cE 'warn\|late\|held\|overdue'` | `0` | **`0`** (see finding 1 — this shaped the file's whole vocabulary) |
| `companion/test_i18n.py` exits 0 | — | **24/24** |
| `ruff check .` | clean | `All checks passed!` |

**Task 2** — all seven ran and returned exactly what the plan predicted.

| Criterion | Expected | Got |
|---|---|---|
| `grep -c 'skypane-pulse' style.css` | `2` | **`2`** |
| `grep -c '@keyframes' style.css` | `1` | **`1`** |
| comment-stripped `prefers-reduced-motion: reduce` | `2` | **`2`** |
| `grep -cE 'dot--warn\|dot--error\|status-warn' freshness.js` | `0` | **`0`** |
| one `data-loaded-at`, one `data-refresh-pill`, ≥ 1 `data-relative` inside `.page-header__freshness` | — | **1, 1, exactly 1** (pinned at exactly one, which is stricter) |
| `git diff freshness.js` touches only the toggles and their comments | — | **59 insertions, 0 deletions** |
| `ruff check .` | clean | `All checks passed!` |

**Task 3** — all six ran. Five returned what the plan predicted; **one did not**
(see below).

| Criterion | Expected | Got |
|---|---|---|
| `test_browser_ux.py` at its new pin, re-derived BY RUNNING | — | **`browser-ux: 32/32 checks pass`** — run output, not arithmetic |
| disabling the interval → **exactly one** additional failure | 1 | **THREE** (29/32). See "the one criterion that did not evaluate as predicted". |
| removing the visibility gate → exactly one additional failure | 1 | **31/32**, exactly one, message quoted (M15) |
| the no-JS check asserts presence AND non-change, at 360px in both languages | — | both asserted, both languages, `VIEWPORT_MIN_SUPPORTED` |
| `run-all-tests.sh` no new failure, coverage ≥ 83 | — | **exactly the 5-check root-sandbox baseline**; `TOTAL 6866 490 93%` |
| `ruff check .` | clean | `All checks passed!` |

### The one criterion that did not evaluate as predicted

**"Disabling the script's interval produces exactly one additional failure, the
ticking check."** It produces **three** (29/32): the ticking check, the
hidden-tab check, and the countdown check. Recorded rather than fixed, because
every one of the three is red for a correct reason and the only way to make the
number one would be to reintroduce the vacuity the standing constraints forbid:

- the ticking check fails as predicted, naming both equal texts;
- the hidden-tab check fails on its own **CONTROL** — "the age did not move in a
  VISIBLE tab ('0s ago' twice), so the hidden-tab assertion below would measure
  nothing." That control is the anti-vacuity device; without it, "the text did
  not change while hidden" passes on an element that never changes at all;
- the countdown check fails because the seeded element never gets repainted —
  which is the same defect seen from a third angle.

The plan's prediction assumes one check per behaviour with no shared dependency.
Three of these four checks genuinely depend on the ticker running, and saying so
is more useful than engineering the number down.

## Mutation tests — sixteen, all quoted, none vacuous

Every mutation was applied **after the implementation was committed** (23-03's
lesson, followed: the restore is `git checkout --` against a committed file, plus
an out-of-tree backup for the script), and `git status --short` was clean after
each. Baselines: `companion-app` **279/281**, `status-pages` **275/276**,
`browser-ux` **32/32**.

| # | Mutation | Result | Failure message (verbatim, after the check name) |
|---|---|---|---|
| M1 | the hours boundary deleted from the script's array | 279 → **278** | `relative-time.js's ladder is [60, 86400] but layout._age_bucket()'s is [60, 3600, 86400] — the script mirrors the Python and must never lead it; a boundary added, removed or reordered in one is a deliberate edit in both` |
| M2 | a SECOND, hard-coded ladder beside the array (`Math.floor(seconds / 3600)`) | 279 → **278** | `the boundary 3600 appears 2 time(s) in relative-time.js's own code (comments stripped), expected exactly 1 — the array is the single site, and a second occurrence is a second ladder` |
| M3 | the hours wording re-worded (`#hr ago`) | 279 → **278** | `lang=en past hours bucket: the wording on data-relative-past-h fills to '2hr ago' but layout.relative_age_text() renders '2h ago' — the ticker's copy is the ladder's own output with the number lifted out, never a second wording` |
| M4 | a `<body>` attribute renamed in `layout.py` only | 279 → **278** | `layout.py renders the 'data-relative-future-hour' attribute but relative-time.js never names it — a rename on one side alone degrades the page to English with no error anywhere` |
| M5 | an expired countdown falls back to an age, SERVER-side | 279 → **278** | `lang=en: an expired countdown must read the waiting wording 'waiting…', got '<time datetime="…" data-relative data-relative-countdown>2m ago</time>'` |
| M6 | the boundaries inlined at each use site, array left agreeing | 279 → **278** | `the boundary 60 appears 3 time(s) in relative-time.js's own code (comments stripped), expected exactly 1 …` |
| M7 | the array left agreeing but never consumed at all | 279 → **278** | `BUCKET_BOUNDARIES is declared in relative-time.js but never read — an array that agrees with the Python and is not consumed proves nothing` |
| M8 | the dot derived from the interval handle ALONE (`currentState` half dropped) | status 275 → **274** | `expected the breathing class to be DERIVED from the loop's own interval handle AND its own state badge — either half alone lets the dot breathe while the page is paused or failing (T-23-15)` |
| M9 | `syncLiveDot()` dropped from `stopLoop()` | status 275 → **274** | `expected syncLiveDot() to be called from function stopLoop() { — the breathing class must change where the loop's own state changes, never from a second state machine beside it` |
| M10 | the server renders the dot already breathing | status 275 → **274** | `expected the live dot to be the app's own NEUTRAL dot and nothing else … got '<span class="dot dot--off is-breathing" data-refresh-live-dot aria-hidden="true">'` |
| M11 | the age reverts to a FROZEN string | status 275 → **273** (two) | `expected every relative age inside .page-header__freshness to be a live <time data-relative> element — a frozen age here is A-20's own defect ('(0s ago)' was structurally always zero), got …` — **plus** the new ticking check. Two reds is the proof the A-20 retarget was strengthened and not weakened. |
| M12 | the live dot given a status colour (`dot--ok`) | status 275 → **272** (three) | `expected the live dot to be the app's own NEUTRAL dot and nothing else … got '<span class="dot dot--ok" …>'` — plus two PRE-EXISTING status-dot count checks, which is a welcome surprise: the codebase already guards per-page dot arithmetic. |
| M13 | the pulse given a bare `400ms` | app 279 → **278** | ``animation: skypane-pulse 400ms ease-in-out infinite`` takes its duration from the bare literal '400ms' …` — 23-01's guard reproducing its own recorded message verbatim |
| M14 | the ticker's interval effectively stopped | browser 32 → **29** (three) | `expected the freshness age to ADVANCE within 2200ms in a visible tab, read '0s ago' then '0s ago' — a page that says 'Updated 14:32' is telling the truth about a moment and saying nothing about now (D14/D22)` (plus the control and the countdown — see above) |
| M15 | the visibility gate removed from the listener AND `tick()` | browser 32 → **31** (exactly one) | `expected the age NOT to change while the page reports itself hidden, read '2s ago' then '4s ago' over 2200ms — a once-a-second timer in every background tab forever is the one real cost this file carries (T-23-14)` |
| M16 | an expired countdown falls back to an age, CLIENT-side | browser 32 → **31** (exactly one) | `lang=en: expected a countdown whose instant has passed to read the server's own waiting wording 'waiting…', got '2m ago'` |

**M15 and M16 were isolated deliberately.** Both left `companion-app` at
**279/281** and `status-pages` at **275/276**, verified by running all three
harnesses under the mutation — so each browser check is proven to do the work
unaided rather than merely going red alongside a source scan. M15 in particular
leaves `grep -c 'document.hidden'` at 1 and `visibilitychange` present, so the
Python required-token scan sees nothing wrong.

### Did any of my own checks fail the "what would a *wrong* implementation do?" test?

**Two did, and both were caught and repaired before or at first run.**

**1. The ladder check, as first drafted, was vacuous.** Comparing
`BUCKET_BOUNDARIES` against `_age_bucket()`'s numbers proves only that a
particular array agrees with the Python. A wrong implementation — an agreeing
array sitting beside a second, hard-coded ladder that does the actual work, or an
agreeing array nobody reads at all — satisfies it completely. Two further clauses
were added before the check shipped: each boundary must appear **exactly once** in
the script's comment-stripped code, and `BUCKET_BOUNDARIES` must be referenced at
least twice. **M2, M6 and M7 exist to prove those two clauses are load-bearing**,
and each of them leaves the original comparison green.

**2. The hidden-tab browser check, as first drafted, was vacuous in the same
shape 23-03 found.** "The text is unchanged over 2.2 s while hidden" passes on a
page where the text never changes for any reason — a broken selector, a detached
element, a script that never ran. The **control phase** (assert the same age DOES
move over the same stretch while visible, immediately before hiding) was added
before the check was written to disk, and M14 is what proves it is real: with the
ticker stopped, the control is the clause that goes red, not the hidden-tab
assertion.

A third draft was discarded for a different reason: asserting `document.hidden`
after the override would have been a statement about `Object.defineProperty`, not
about this app. The check reads the ELEMENT's text instead, which is the contract.

## The no-JS floor — what a scripts-blocked visitor actually sees

**Proven, not asserted:** a `java_script_enabled=False` context at 360px, in both
languages, signed in, on `/health`.

- **Exactly one `<time data-relative>`** in the freshness line, carrying the
  server's own ladder output — asserted to EQUAL `layout.relative_age_text(0,
  lang=lang)`, so `0s ago` in English and `à l’instant` in French.
- **It does not change** over 2.2 s. This half is the point: a presence-only
  assertion would pass on a page where the enhancement had quietly taken over in
  a context that is supposed to have none.
- **No raw `#` reaches the page.** Asserted in every browser check.
- **The dot renders, still and neutral.** It is `.dot--off` with no modifier; the
  motion is a class `freshness.js` adds, and with no script there is no class and
  no motion. A harness check fails if the SERVER ever renders it breathing — a dot
  breathing on a page with no loop running at all is exactly the lie D22 exists to
  remove.
- **Nothing here is a control.** No button, no switch, no affordance that renders
  and does nothing. The failure mode Phase 22's audit found is structurally
  unavailable to a file whose only write is `textContent` on an element the server
  already filled in.
- **`relative-time.js` itself returns before registering anything** on a page with
  no `[data-relative]` element, so a page without one pays nothing even with
  scripts on.

**One honest cost, and the plan assumed otherwise — see finding 2:** for the
scripts-blocked reader of `/health` specifically, the visible value changed from
an absolute clock (`Updated 18:46`, true forever) to a frozen relative age
(`Updated 0s ago`, true only at load). The absolute instant is not lost — it is on
the element's `title` — but it is demoted from visible text to a tooltip for that
one reader.

## `EXPECTED_CHECK_COUNT`

Every one re-derived by **running** the harness, never by arithmetic, and appended
as a new last assignment citing this plan — except `test_i18n.py`, which did not
move and says so in place (23-02's own precedent, quoted in the comment).

| Harness | Before | After | Task |
|---|---|---|---|
| `companion/test_companion_app.py` | 273 | **281** (+8) | Task 1 |
| `companion/test_status_pages.py` | 273 | **276** (+3) | Task 2 |
| `companion/test_browser_ux.py` | 28 | **32** (+4) | Task 3 |
| `companion/test_i18n.py` | 24 | **24** (net 0, recorded in place) | Task 1 |

**Two pre-existing checks were retargeted in place**, neither deleted, weakened
nor excepted:

1. **the deferred-script count, twelve → THIRTEEN** — the pin the standing
   constraints name, moved deliberately, in the comment format the check has now
   used three times, stating what the thirteenth is and why it is served
   everywhere rather than per page. It additionally now pins that the login shell
   emits exactly **one** deferred script, which it did not assert numerically
   before.
2. **19-09/A-20's "no relative age inside `.page-header__freshness`" ban** —
   retargeted to "every age here must be inside a live `<time data-relative>`
   element", which is strictly stronger: it still fails on A-20's own defect (a
   bare frozen `(0s ago)`), **and** on an age that has stopped moving. **M11 fails
   it**, which is the proof.

**No test exception was added anywhere.** The suite still carries none.

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_companion_app.py` | 271/273 | **279/281** | 2 × WR-11 read-only (documented) |
| `companion/test_status_pages.py` | 272/273 | **275/276** | 1 × `anomaly_active()` (documented) |
| `companion/test_browser_ux.py` | 28/28 | **32/32** | — |
| `companion/test_i18n.py` | 24/24 | **24/24** | — |
| `companion/test_view_pages.py` | 146/146 | 146/146 | — |
| `companion/test_config_page.py` | 233/233 | 233/233 | — |
| `companion/test_contrast_check.py` | 43/43 | 43/43 | — |
| `server/test_manual_resolutions.py` | 21/23 | 21/23 | 2 × WR-11 read-only (documented) |

`PYTHON=… bash scripts/run-all-tests.sh` → three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline**, verified by
NAME: two `add_entry()`/`delete_entry()` WR-11 read-only failures in
`server/test_manual_resolutions.py`, their two end-to-end counterparts in
`companion/test_companion_app.py`, and `anomaly_active()` in
`companion/test_status_pages.py`. No new failure. Coverage
`TOTAL 6866 490 93%`, floor 83. `ruff check .` clean.

## D22's orange-reconnecting clause — superseded, not dropped

`22-AUDIT.md`'s D22 asks for an ORANGE reconnecting state. **It is deliberately
not implemented as worded, and this is a shipped decision reversing an audit row
rather than an omission.**

22-15 shipped that state NEUTRAL, on an argued ground the design system now
records: a browser that lost its connection is not a device fault, and painting it
as one is the same class of error as the nightly false alarm Phase 22's X2
removed. `.dot--off` is the app's own word for a state that is not a problem, and
`freshness.js`'s own comment states the argument in the file. This plan extends
that decision rather than reverting it — the breathing dot IS `.dot--off`, in
every state, and `grep -cE 'dot--warn|dot--error|status-warn'` over `freshness.js`
is **0**, pinned. The same reasoning governs the expired countdown, which reads a
neutral `waiting…` and carries a breathing class rather than a warn one.

Two further D22 clauses were already shipped by 22-15 and are **not
re-implemented**: the grey Paused state in background tabs and the Reconnecting
state with backoff. A harness check now asserts `RETRY_BASE_MS`,
`RETRY_CEILING_MS = 600000`, `failAndRetry()`, `inFlight` and `isEqualNode` all
still present in `freshness.js`, so re-implementing them would fail rather than
pass silently.

## Deviations from Plan

**1. [Rule 3 — Blocking] A backtick in a comment, caught by this file's own
acceptance grep before it reached a commit.** The first draft wrote
`` the server's own wording for `attr` `` in a comment, which made
`grep -cE '…|`'` return `1` instead of `0`. Three plans have done this; this one
did too, and the grep caught it in the same minute. Reworded, re-run, `0`.

**2. [Rule 3 — Blocking] `test_i18n.py`'s Check 6 demanded a French translation
for `"[data-relative]"`, and then for my own comment.** Two separate hits, both
the "prose trips a check" trap from a harness the plan did not name in this
context:
   - `var HOOK_SELECTOR = "[data-relative]"` is an upper-case string constant, and
     Check 6's allowlist — which its own comment says excludes "a bare selector" —
     has no rule that matches a BRACKETED attribute selector. Fixed in the code,
     not in the harness: the attribute NAME gets its own constant (excluded as a
     hyphenated identifier) and the selector is built from it, which is
     independently better because the name then has exactly one site. The same fix
     was needed for `freshness.js`'s new `[data-refresh-live-dot]`.
   - The comment explaining that fix originally contained the literal
     `var ALL_CAPS = "literal"`, which Check 6's regex matched, demanding a French
     entry for the word `literal`. Reworded.
   Widening the harness's exclusion list was rejected as a test exception; the gap
   is logged to `deferred-items.md` for whichever plan next edits that file.

**3. [Rule 3 — Blocking] A shipped `grep -c 'dot--'` pin, tripped by my CSS
comment.** `test_status_pages.py` pins the RAW `dot--` occurrence count in
`style.css` at 9 ("this plan adds no dot class"). My new comment named `.dot--off`
three times in prose and took it to 12. This plan genuinely adds no dot class, so
the comment was rewritten to describe the rule without spelling the modifier out —
**the shipped pin was left untouched at 9**, which is strictly better than
retargeting another plan's number for prose. The comment now says so, in place, so
the next writer does not reintroduce it.

**4. [judgement] Four toggle sites, not three.** The plan says "pin that the pulse
class is toggled in the same three places the state is". The loop has **four**
functions that change its state, and `syncLiveDot()` is called from all of them —
`setState`, `clearState`, `startLoop` and `stopLoop`. The fourth is load-bearing:
`tick()`'s belt-and-braces `stopLoop()` in a background tab would otherwise leave
a stopped loop breathing. **M9 proves it** — dropping that one call reddens the
check. This is not a second state machine: the class is DERIVED inside one
function from the loop's own two variables, which is what the plan's real
instruction ("the loop already knows") asks for.

**5. [judgement] The countdown is a server-rendered marker, not a client-side
memory.** The plan's behaviour list ("a countdown that reaches zero reads the
translated waiting…") does not say how the script knows an element is a countdown,
and 23-03's element carries no direction. A client-side "it was in the future when
I first saw it" memory was rejected: it dies with every `freshness.js` swap, it is
untestable without a browser, and — decisively — it leaves the SERVER rendering
`0s ago` for an expired countdown, so the no-JS floor would be wrong.
`relative_time_html(countdown=True)` adds `data-relative-countdown` and renders
the waiting wording itself; the script reads the same marker and makes the same
choice, so the two cannot disagree. `countdown=False` is the default and produces
the byte-identical element 23-03 shipped, pinned by a check.

**6. [judgement] The quantity placeholder is `#` and the copy is nine complete
wordings.** The plan says only "Carry the words as English fallback literals read
from `<body>` attributes". The shape was forced by two harness facts found while
designing it: `test_i18n.py`'s Check 3 scans every French render for a stray
`%s`/`%d`/`{}` (so a `%s` in an attribute would have failed six routes), and
`getAttribute(x) || fallback` treats an empty string as absent (so a
prefix/suffix split, which needs empty values in one language or the other, would
have silently taken the English fallback). See the key decisions above. `{n}` was
considered and rejected as evasion: it slips past Check 3's regex, which is worse
than not needing to.

**7. [scope] `REQUIREMENTS.md` was not touched.** CFG-32 and CFG-34 both exist;
the standing instruction is not to tick either, and 23-11 closes both and owns the
coverage ledger. No row was edited from outside this plan's ownership.

## Findings the plan did not anticipate

**1. `grep -cE 'warn|late|held|overdue'` = 0 bans far more English than it looks
like.** `late` is a substring of **`translated`**, `related`, `later`, `latest`,
`calculate` and — the one that mattered most — **`template`**. The script's whole
vocabulary was designed around this: it says "wording" where it wanted "template",
"the catalogue's own copy" where it wanted "translated", and "one tick further on"
where it wanted "later". Worth knowing for 23-06 and 23-08, which inherit the same
ban if they extend this file. The criterion is a good one and the cost is real;
both are recorded rather than one of them quietly dropped.

**2. The plan's `<no_js_floor>` claim does not hold for the one element Task 2
converts.** It says "With scripts blocked the page shows the same ages it shows
today, at the same wording … which is exactly today's behaviour." That is true for
every element 23-03 shipped, which were already ages. It is **not** true for
Health's freshness line, which today shows a CLOCK. After this plan, a
scripts-blocked reader of `/health` sees `Updated 0s ago` frozen at load instead
of `Updated 18:46`, which is true forever. The absolute instant survives on the
element's `title` and nothing is lost, but for that reader the visible value moved
from a fact to a claim that goes stale. The plan's Task 2 action text is explicit
("render it with plan 23-03's `relative_time_html()` … and keep the full local
timestamp on the element's `title`"), so it was followed rather than bent —
**recorded here for the human sweep folded into 23-11**, which should decide
whether the visible half should read `Updated 18:46 (3m ago)` instead. That shape
would satisfy both readers and is a one-line change to one f-string.

**3. The freshness wrapper now differs from its fetched counterpart on every
cycle.** `freshness.js`'s "the region did not change" skip (`isEqualNode`) can no
longer apply to `.page-header__freshness`, because the live age has advanced while
the freshly-fetched one reads zero. That is correct rather than a regression — the
age really did change and the swap resets it to the truth — but it means one of
the five swap targets is now always replaced. Written into `health_page.py`'s own
comment so the next reader does not read it as a bug.

**4. Neither real way to hide a page works in this harness, and both were tried.**
`page2.bring_to_front()` in the same context leaves the first page's
`document.visibilityState` at `"visible"` in headless Chromium; CDP's
`Emulation.setPageVisibilityOverride` returns `'Emulation.setPageVisibilityOverride'
wasn't found`. The check therefore overrides the page's own visibility state
in-page and dispatches a real `visibilitychange` `Event` on `document`. **What is
simulated is the BROWSER'S REPORT; what is exercised is the shipped script's own
listener and its own `document.hidden` reads, unmodified.** It is weaker than a
genuinely backgrounded tab and stronger than "a listener is registered": M15
proves a script that ignores `document.hidden` fails it. Both the limitation and
the two rejected mechanisms are written into the check's own comment and its
`EXPECTED_CHECK_COUNT` note.

**5. `app.py`'s script numbering and the shell's script count are different
numbers, and both are right.** `app.py` calls `submit-guard.js` "the thirteenth
static script" while the shell emitted twelve — because `battery-trend.js` has a
route but is registered by `health_page.py`, and `login-card.js` has a route but is
emitted by `login_shell()`. `relative-time.js` is therefore the **fourteenth**
static script route and the **thirteenth** deferred script on the authenticated
shell. Both numbers are stated where they belong.

**6. A status colour on the new dot reddens three checks, not one.** M12 also
trips two PRE-EXISTING per-page status-dot count assertions. The codebase already
guards dot arithmetic on Health more tightly than this plan knew; worth knowing
before any later plan adds a dot to that page.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-13 | mitigate | `textContent` is the only write in the new file (4 sites). `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`document.write`/`eval(`/`fetch(`/`XMLHttpRequest`/`setTimeout(` are all banned by name for this file in `test_companion_app.py`, asserted twice — once against the source and once against the SERVED body — and by the acceptance grep, which returns 0. |
| T-23-14 | mitigate | The `visibilitychange` gate is `freshness.js`'s own policy in its own shape, plus a belt-and-braces `document.hidden` check inside `tick()`. Proven in a browser: a page reporting itself hidden produces byte-identical text across 2.2 s, against a control proving the same age does move while visible. **M15** (the gate removed) is the proof, and it leaves every source scan green. |
| T-23-15 | mitigate | The breathing class is DERIVED from `freshness.js`'s own `intervalHandle` and `currentState` inside one function, called from the four places that state already changes and nowhere else — pinned by source scan, including an exact call-site count so a fifth caller fails. **M8** (one half of the derivation dropped) and **M9** (one call site dropped) both go red. There is no second timer and no second variable. |
| T-23-16 | mitigate | Parse-or-noop, the discipline `freshness.js` applies to its own `data-loaded-at`: an absent or `NaN` `datetime` leaves the element exactly as the server rendered it, which is already correct. Every `datetime` is server-computed by `layout._machine_instant()` and escaped at the interpolation site; nothing reaching it comes from a request parameter. |
| T-23-17 | mitigate | `script-src 'self'` unchanged, asserted by the shipped CSP check. No inline script, no nonce, no vendored library. The file is served by its own route, pre-auth like its thirteen siblings, carrying no session data of any kind; the served-route check asserts the real 200, its content type and its `public, max-age=300`. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. This plan adds one static, session-free GET route whose
body is a file on disk, served by the same `_serve_script_file()` delegate its
thirteen siblings use. No auth path, no schema change, no new file access pattern.

## Known Stubs

**None.** `relative_time_html(countdown=True)` has no render site on any page yet —
23-06's next-wake line is its first consumer — but it is not a stub: it is fully
implemented, fully translated, pinned by a Python check and exercised in a real
browser, and nothing on screen renders a placeholder because of it. `waiting…`
likewise appears on `<body>` on every page as inert copy, which is this shell's
established convention for the two refresh-state strings 22-15 put there.

Every surface this plan claims is live IS live: Health's freshness line ticks and
its dot breathes, and every `<time data-relative>` the app already rendered —
Health, Flights, Airlines, Home's caption and Home's recent-flight age — now moves
without any page module changing.

## Notes for later plans

- **23-06** inherits a freshness line that is ALREADY a `<time data-relative>`
  element; its own plan text may still describe a conversion. It also gets its
  countdown for free — `relative_time_html(ts, now, countdown=True)` renders the
  marker, the future form and the expired `waiting…`, and the script does the rest.
  `health_page.py:1150` is still plain text by contract (`battery-trend.js` writes
  it into a `title`) and still cannot become an element without changing that
  script's transport.
- **Any plan adding a script to `companion/static/`** should give an attribute
  NAME its own constant and build a bracketed selector from it, not write the
  selector out as an upper-case string constant — `test_i18n.py`'s Check 6 will
  demand a French translation for the brackets otherwise. Logged in
  `deferred-items.md`.
- **Any plan extending `relative-time.js`** inherits `grep -cE 'warn|late|held|
  overdue'` = 0, which bans `template`, `translated`, `later` and `related` in
  prose. See finding 1.
- **Any plan adding motion** spends `.is-breathing` or writes its own rule with
  `var(--motion-fast)`/`var(--motion-slow)`; the keyframes block is at one and
  23-01's guard fails a second. The reduce-block count stays at **2** and the
  no-preference count at **1** — this plan moved neither and needed no third block,
  because the global override reaches a real element's animation for free.
- **23-11** owns: ticking CFG-32 and CFG-34 and rewriting their traceability rows;
  recording `.is-breathing` in `SKILL.md` as the fifth consumer of the neutral dot
  rule and the one consumer of the app's one animation; the human sweep (watch the
  freshness line advance for ten seconds, stop the server and see the dot stop with
  the neutral Reconnecting badge, and switch the OS to reduce motion and confirm
  the dot is static while the age still ticks); and **the decision in finding 2** —
  whether a scripts-blocked reader of `/health` should get
  `Updated 18:46 (3m ago)` rather than a frozen `Updated 0s ago`.

## Self-Check: PASSED

- `companion/static/relative-time.js` exists on disk (16 065 bytes served over a
  real HTTP GET returning 200).
- All ten modified files exist and are exactly the files the six commits name,
  re-verified with `git show --name-only` on each.
- All six commit hashes resolve in `git log`: `befabd0`, `aa96eb0`, `ed9927c`,
  `cc24ae0`, `fb4722b`, `b2750c0`.
- `.planning/phases/23-companion-dynamism-live-updates-real-switches-motion-budge/23-05-SUMMARY.md`
  exists.
- The working tree is clean after every mutation: `git status --short` empty and
  `git diff --stat` empty against the committed state for every mutated file.
