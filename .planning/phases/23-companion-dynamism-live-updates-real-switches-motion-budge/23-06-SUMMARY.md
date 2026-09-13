---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 06
subsystem: ui
tags: [javascript, freshness, refresh, registry, progressive-enhancement, motion, no-js-floor, playwright, harness]

requires:
  - phase: 22-15
    provides: "freshness.js's retry ladder, in-flight guard, visibility gate and focus-preserving targeted swap — extended by a registry, a page key and two skips, and otherwise untouched"
  - phase: 23-01
    provides: "--motion-fast, whose own comment names this plan's fades, and the guard that rejects a bare duration literal"
  - phase: 23-02
    provides: "test_browser_ux.py's _no_js_page() helper and VIEWPORT_MIN_SUPPORTED, used by the Display no-JS save check"
  - phase: 23-03
    provides: "relative_time_html() and the one ladder — the element the countdown and the freshness line both are"
  - phase: 23-05
    provides: "relative-time.js (the ticker that upgrades the freshness clock), relative_time_html(countdown=True) (the countdown's first consumer is here), the breathing dot, and the recorded no-JS finding this plan fixes"
provides:
  - "layout.REFRESH_SWAP_SELECTORS_BY_PAGE: the per-page swap registry, one definition site, keyed by nav_slug()'s own values"
  - "layout.REFRESH_PAGE_ATTR: the page key page_shell() renders on <body>, selecting one selector list"
  - "layout.REFRESH_PENDING_ATTR: the marker 23-07 sets on an unconfirmed optimistic control and this plan's swap already skips"
  - "layout.freshness_line_html(now): the freshness line — dot, prefix, clock element, pill — with three call sites (Health, Home, the Display scope)"
  - "layout.full_local_timestamp_text(): promoted out of health_page.py so three page modules can reach it"
  - "layout.relative_time_html(static_text=...): the server renders a value true independent of now; the ticker upgrades it"
  - "frame_strip_html()'s ticking next-wake countdown, formatting only — never a verdict"
  - "style.css .is-fading-in + @keyframes skypane-fade-in: the app's second animation, spent by a picture that actually changed"
  - "freshness.js's three skip rules: focus (22-15's), pending (new), dirty form (new)"
affects: [23-07, 23-08, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "a per-page REGISTRY selected by a server-rendered page key, replacing one hard-coded list, with the two key sets pinned EQUAL in both directions — the drift a one-tuple pin structurally cannot see"
    - "progressive enhancement as the answer to a no-JS regression: the server renders the value that stays true and the script replaces it with the live one, so neither reader is handed a frozen claim"
    - "a browser check that asserts something did NOT happen first MAKES the region differ, so the 'unchanged region' skip cannot be what satisfies it, and then proves the same changed region IS replaced once the rule's own condition is removed"
    - "counting REQUESTS rather than reading the DOM for any claim about request volume — a page that fetched and then declined to swap is a different and worse behaviour"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/static/freshness.js
    - companion/static/style.css
    - companion/pages/home_page.py
    - companion/pages/config_page.py
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - companion/test_config_page.py
    - companion/test_browser_ux.py

key-decisions:
  - "The registry keys are nav_slug()'s own values, not a new vocabulary. page_shell() already receives exactly that string as `active`, so the key set has one definition site too and a page cannot be given a key that disagrees with its route."
  - "The page key is rendered on EVERY page, including the ones that declare no regions, and the guard lives in the script. That matches the convention the two refresh copy attributes and the thirteen deferred scripts already follow, and it means the attribute is not a second, silent gate to keep in sync."
  - "The script resolves the key with Object.prototype.hasOwnProperty. The key arrives as markup, so a bare lookup would resolve 'constructor' or 'toString' to an inherited function — a strange crash rather than the no-op that is correct."
  - "The pending skip is per REGION and the dirty-form stand-down is per TICK. One unconfirmed control must not stand down the refresh of the whole page; a form mid-edit must, because every region the fetched document would bring in describes a page the user has already moved on from."
  - "The dirty-form gate requires dirty-state.js's dirty-ready marker AND the bar's current visibility. Neither alone: presence-without-liveness is 22-01/B1's defect of record, and a bar that merely exists, hidden, reports nothing. A user typing is already covered by userIsInteracting(), so a dead dirty-state.js can neither disable this loop nor expose a half-edited form."
  - "Display declares the strip and the freshness line and nothing else, and the registry's comment says so in as many words, because the obvious later 'completion' of that list is the defect: everything else on that page is a form."
  - "The countdown lives in the update cell's CAPTION row, beside the headline and never inside it, so the state word frame_state.resolve_state() produced is textually untouched by anything this plan added."
  - "The app's second @keyframes block is argued rather than asserted: skypane-pulse is an infinite 1..0.35 cycle and a fade needs a one-shot 0..1 ramp. Reusing the pulse would start the picture at a third of its weight and misuse a block whose own comment says it is the AMBIENT loop."
  - "Health's freshness line server-renders the CLOCK inside its <time data-relative> element and the ticker replaces it with the live age. 23-05's shape was true only with scripts on; this one is true for both readers."

patterns-established:
  - "One registry, one page key: a later page joins the loop by declaring its regions in layout.py and adding the same key to the script's object literal. Nothing else changes, and the harness fails if only one side moves."
  - "relative_time_html(static_text=...) is the sanctioned way to keep a no-JS floor honest under a live element: the caller asserts its text is true independent of now."
  - "Anti-vacuity by construction in browser checks: dirty the region first, then remove the rule's own condition and prove the opposite outcome in the same check."

requirements-completed: []

duration: ~4h
completed: 2026-09-13
---

# Phase 23 Plan 06: D1 — Home and the Frame strip refresh themselves Summary

**One loop now serves three pages from one Python registry selected by a
server-rendered page key, refusing to repaint a region the user is inside, a
region holding an unconfirmed control, or any region at all while a settings
form has unsaved edits — and Health's freshness line stopped lying to the reader
who has no scripts.**

## Performance

- **Duration:** ~4 h
- **Tasks:** 3/3, plus the unplanned no-JS fix that came with the plan
- **Files:** 0 created, 9 modified
- **Harness runtime:** `test_browser_ux.py` 80s → 109s (six new checks, almost
  all of it real waits: each forced refresh is a real HTTP round trip plus a
  1.2s settle, and two of the six run two full cycles each by design)

## Commits

| Task | Commit | Message |
|---|---|---|
| extra (RED) | `924b06f` | test(23-06): pin the freshness line honest with scripts blocked, before it is |
| extra (GREEN) | `aace4ca` | fix(23-06): the freshness line is true for a reader with no scripts too |
| 1 (RED) | `848fc52` | test(23-06): pin one registry, one page key and three skips before they exist |
| 1 (GREEN) | `d52715e` | feat(23-06): one registry, one page key, three things the loop must not repaint |
| 1 (repair) | `0665958` | test(23-06): repair a vacuous clause in the dirty-form gate's own check |
| 2 (RED) | `5f827f3` | test(23-06): pin Home, Display, the countdown and the fade before they land |
| 2 (GREEN) | `b0a22f0` | feat(23-06): Home and the Frame strip refresh themselves, and the picture fades when it changed |
| 3 | `be282dc` | test(23-06): a browser proves the three skips, the zero and the fade |

**TDD gate sequence present and in order** for the extra task and for Tasks 1
and 2 (`test(...)` then `fix(...)`/`feat(...)`); Task 3 is a test-only task and
has one `test(...)` commit. Every RED commit was proven red **by running**, not
asserted: the extra task's reports **status-pages 273/276** and **browser-ux
31/32**; Task 1's reports **274/279**; Task 2's reports **278/283** and
**config-page 233/235**. `git show --name-only` was run after every commit and
each carries exactly the files its message claims. No `git stash`, no
`git clean`, no blanket `git checkout --` over unstaged work.

---

## The no-JS freshness fix — what it is and how it was proven

**The defect, as 23-05 recorded it (its own finding 2).** 23-05 converted
Health's freshness line from a clock to a live `<time data-relative>` reading
`0s ago`, which `relative-time.js` then advances each second. With scripts on
that is strictly better and is the whole of D22. With scripts blocked the
element renders `0s ago` server-side and *nothing ever advances it* — a
permanently frozen "Updated 0s ago", which is exactly the frozen-zero defect
19-09 (D-02/A-20) removed, reintroduced for that one reader.

**The shape, verified against the mechanism before being taken.**
`relative-time.js` rewrites `textContent` on every `[data-relative]` element
from that element's own `datetime`; it has no opinion whatsoever about what the
server put inside it. So the ordinary progressive-enhancement split works with
**no change to that file at all** (which matters: `relative-time.js` is not in
this plan's `files_modified`):

- `layout.relative_time_html()` gains `static_text`. The element, its
  machine-readable `datetime` and its `data-relative` hook are untouched; only
  the text the SERVER writes inside it changes. The keyword documents its one
  legitimate use and says in as many words that **the caller is asserting its
  text is true independent of now** — pass a clock, never a duration.
- Health's freshness line passes `local_clock_text()`'s same-day branch over the
  same instant `data-loaded-at` carries — i.e. exactly what this line rendered
  from 19-09 until 23-05.

```
scripts blocked:  Updated 14:32              (true forever)
scripts on:       Updated 14:32  ->  Updated 3m ago  ->  Updated 3m ago …
```

**How it is proven** — four assertions, two of them retargeted from 23-05's own:

1. **scripts-blocked, in a real browser, at 360 px, in both languages**
   (`test_browser_ux.py`): the element's text must EQUAL the clock **derived
   from the element's own `datetime` attribute** (so the assertion cannot flake
   across a minute boundary), must NOT equal `relative_age_text(0, lang)`, must
   contain no ` ago`/`il y a` — **and 23-05's non-change assertion over 2.2 s is
   kept verbatim**, not weakened. The RED run quoted the reversal exactly:
   `lang=en: expected the scripts-blocked page to read the server's own clock
   '19:27' … got '0s ago'`.
2. **scripts-on, in the same browser**: 23-05's ticking check gains the other
   half — after the settle the text must NO LONGER be the clock the element's
   own `datetime` resolves to. The first read is deliberately not pinned to the
   clock, because the ticker's first repaint lands one second after load and
   this harness cannot promise to read faster than that; pinning it would have
   been a flake, and the scripts-blocked check is the honest home for the "the
   server rendered the clock" claim.
3. **19-09/A-20's ban gained its positive half** (`test_status_pages.py`).
   Stripping the `<time>` element out and finding no age left is a clause a page
   rendering no age at all satisfies for free — which is precisely what this fix
   would have made it. The check now also asserts the element's OWN text: not
   the zero bucket in either language, and not an age at all.
4. **The 23-05 freshness check** now expects `relative_time_html(…,
   static_text=clock)`'s output and asserts the text equals the clock.

**One honest cost, stated rather than found later.** After a successful swap the
freshness line briefly shows the server's clock again before the ticker's next
pass (at most one second, every 45 s). Both strings are true at that instant —
the fetched document was generated just then — so this is a formatting wobble,
not a false claim. The alternative (a cross-script repaint hook) would mean
editing `relative-time.js`, which this plan does not own, for a sub-second
cosmetic gain. Logged for the wave-9 human sweep.

---

## What landed

### Task 1 — one registry, one page key, three skip rules

**`layout.REFRESH_SWAP_SELECTORS_BY_PAGE`** is now the single definition site.
`health_page.REFRESH_SWAP_SELECTORS` survives as a NAME resolving from it — and
the harness asserts it *is* that object, not a copy, because a copy is a second
definition site with extra steps. The tuple's entire comment moved with it
unabridged: the deliberate exclusions (sparkline, registry card, filter bar,
every `<details>`) and the `a[href="/health"]`-not-a-dot reasoning, which is the
most valuable paragraph in that block.

**The page key** is `nav_slug()`'s own value, rendered on `<body>` by
`page_shell()` beside the two refresh copy attributes that live there for the
same reason (several swap targets would otherwise carry an attribute the script
reads, and the first swap would replace it). It is emitted for every page; the
guard is in the script, which resolves it with `hasOwnProperty` because the key
arrives as markup.

**The cross-file pin was generalised, not replaced.** It iterates every key, and
a new check compares the two key sets in BOTH directions by parsing the keys out
of the script's own registry block. It is also anti-vacuous by construction:
each selector must appear in the comment-stripped script exactly as many times
as the registry carries it, and `SWAP_SELECTORS_BY_PAGE` must actually be read.

**Two new skips, beside the two that existed:**

- **pending** (`swapNodes`, per region): the region, or anything inside it,
  carrying `data-pending` is left alone entirely. Its comment states the harm
  (an optimistic flip repainted with the server's older answer bounces back
  under the user's finger) and the accepted cost (a control whose confirmation
  never arrives holds its own region stale). **This file only reads the marker;
  23-07 sets it.**
- **dirty form** (`tick`, per cycle, and on the visibility catch-up path too):
  no fetch at all while the save bar reports unsaved edits.

The interval, ladder, ceiling, in-flight guard, visibility policy,
`redirect: "manual"` and badge copy are asserted unmoved.

### Task 2 — Home and the strip go live

**`layout.freshness_line_html()`** is the promoted builder; Health's rendered
page is **byte-identical across the move**, proven mechanically rather than by
inspection: the whole document rendered from a `git archive` of the previous
commit and from the working tree compare equal at 4208 bytes.
`layout.full_local_timestamp_text()` and the three copy constants moved with it;
`health_page` keeps every name as a delegate because shipped pins use them.

**Home** declares the strip, the status tiles, the picture, the recent-flights
section and its freshness line. The flights SECTION rather than its `<ul>` is
the target so the empty-state↔list transition is covered. No entry contains
another, so no swap can detach a node another entry is about to replace.
**Display** declares the strip and the freshness line and nothing else.

**The countdown** renders in the update cell's caption row:

```
Next update ≈ 14:10
in 10m                 <- <time datetime="…" data-relative data-relative-countdown>
```

It is `relative_time_html(countdown=True)`'s first consumer (23-05 shipped it
fully implemented with no render site). It counts toward `wake.next_wake_status()`'s
own resolved instant and decides nothing; a late frame reads
`Expected since 14:32 / waiting…` rather than an age, which would be a second,
quieter lateness claim beside the headline's.

**The picture fade** is `@keyframes skypane-fade-in` + `.is-fading-in` at
`var(--motion-fast)`, applied by `freshness.js` only after comparing the image's
own `src` — read through `getAttribute()` and not the `.src` property, because
the property resolves against each document's own base and these two nodes come
from two different documents.

### Task 3 — a browser proves it

Six checks, each carrying its own control. The two node-identity checks
**dirty the region first**, so the "unchanged region" skip cannot be what
satisfies them, and each runs a **second phase** proving the same changed region
IS replaced once focus leaves it / once the marker is removed. That second phase
is what makes them statements about the rules rather than about those regions —
and the first draft of the focus check went red on its own control for exactly
the reason it should have (see "checks that failed the vacuity question").

---

## Acceptance criteria — every one run literally

**Task 1** — all six ran. Five returned exactly what the plan predicted; one
returned a different number in one of its two directions.

| Criterion | Expected | Got |
|---|---|---|
| `grep -c 'REFRESH_SWAP_SELECTORS = (' health_page.py` / `grep -c 'REFRESH_SWAP_SELECTORS'` | `0` / ≥1 | **`0`** / **`4`** |
| key-set equality; a key on one side alone → exactly one failure naming it | 1 | **script-only key: exactly one** (277/279), message below. **Python-only key: TWO** — see "criteria that did not evaluate as predicted" |
| `grep -c 'data-pending' freshness.js` ≥1, plus a harness driving a synthetic marker | — | **`1`**, and the browser check drives one (both phases) |
| `grep -cE 'AUTO_REFRESH_INTERVAL_MS = 45000\|RETRY_CEILING_MS = 600000'` | `2` | **`2`** |
| Health: one `data-loaded-at`, one `data-refresh-pill`, five regions in order; pre-existing checks unmodified | — | **1, 1, the same five in the same order.** The Health-specific checks pass unmodified; two OTHER pre-existing checks were retargeted in place and both are documented below |
| `ruff check .` | clean | `All checks passed!` |

**Task 2** — all seven ran and returned exactly what the plan predicted.

| Criterion | Expected | Got |
|---|---|---|
| Home, Display, Health each: one `data-loaded-at`, one `data-refresh-pill` | — | **1/1 on all three** (asserted per page, in two harnesses) |
| `grep -c 'page-header__freshness' health_page.py` / `layout.py` | `0` / ≥1 | **`0`** / **`5`** |
| comment-stripped `prefers-reduced-motion: reduce` | `2` | **`2`** |
| `grep -c '@keyframes' style.css` | 1 or 2 | **`2`** — declared, named and justified; see the note below on 23-01's guard |
| state word from `resolve_state()`; `grep -rcE 'resolve_state\|HEADLINE_LATE\|HEADLINE_HELD' static/*.js` | `0` each | **`0` for all fifteen script files**, and a harness check asserts it per file |
| `test_config_page.py` M/M at its new pin | — | **`config-page: 235/235 checks pass`** |
| `ruff check .` | clean | `All checks passed!` |

**On 23-01's guard and the second `@keyframes`.** The criterion says the guard
"must be updated in the same commit rather than worked around". **It needed no
update, and that is a reading of the guard rather than a decision to skip it:**
`_motion_budget_is_enforced_in_the_stylesheet()` does not cap the NUMBER of
keyframes blocks. It asserts (1) every name is defined exactly once — the
failure it names in its own message is "two near-identical keyframe blocks",
i.e. a *duplicate definition of one name*, not a second animation; (2) every
`animation` reference resolves to a block in the same file; (3) every duration
comes from a `--motion-*` token. All three hold with two named blocks, and
`companion-app` stays at its 279/281 baseline. Nothing was worked around: no
exception, no exemption, no edit to the guard. The second block is argued in the
stylesheet itself, where the next reader will look.

**Task 3** — all seven ran. Six returned what the plan predicted; one did not.

| Criterion | Expected | Got |
|---|---|---|
| `test_browser_ux.py` at its new pin, re-derived BY RUNNING | — | **`browser-ux: 38/38 checks pass`** — run output, not arithmetic |
| removing the pending skip → exactly one additional failure | 1 | **exactly one** (37/38), quoted (M12) |
| removing the dirty-form stand-down → exactly one, reporting a non-zero request count | 1 | **exactly one** (37/38), `counted 1` (M13) |
| removing the visibility gate → exactly one, non-zero background count | 1 | **exactly one** (37/38), `/ issued 1 request(s)` (M14) |
| the no-JS Display check passes at 360px in both languages; removing the fallback Save → exactly one failure | 1 | **passes; the mutation produces THREE** — see below (M16) |
| `run-all-tests.sh` no new failure, coverage ≥ 83 | — | **exactly the documented 5-check root-sandbox baseline**; `TOTAL 6889 488 93%` |
| `ruff check .` | clean | `All checks passed!` |

### The criteria that did not evaluate as predicted

**1. "A key on only one side produces exactly one failure naming the key."** It
does in one direction and not the other.

- A key the SCRIPT has and Python does not → **exactly one** failure, naming
  both sets and both differences (M1).
- A key PYTHON has and the script does not → **two** (M2): the key-set check
  fires, and so does the generalised 19-09 cross-file pin, because that key's
  selectors are by definition absent from the script. Both are red for the right
  reason and the second is the older, broader contract doing its job. Making the
  number one would mean narrowing the 19-09 pin to "keys the script already
  has", which is the drift it exists to catch.

**2. "Removing the fallback Save produces exactly one failure."** It produces
**three**: this plan's new no-JS Display check, 22-01's own
"the fallback Save stays reachable until proven live" check, and 22-10's
scripts-blocked settings check, which also saves through that button. The
codebase already guards this control from two other angles; mine is the third,
and it is the only one of the three that measures it at 360 px in both
languages with the value read back from disk. Recorded rather than engineered
down.

---

## Mutation tests — sixteen, all quoted

Every mutation was applied **after** its implementation was committed (23-03's
lesson), restored with `git checkout --` against the committed file, and
`git status --short` was verified empty afterwards. Baselines: `status-pages`
**282/283**, `browser-ux` **38/38**.

| # | Mutation | Result | Failure message (verbatim, after the check name) |
|---|---|---|---|
| M1 | a key in the script that Python does not have | 282 → **281** | `freshness.js's registry keys ['flights', 'health'] and layout.REFRESH_SWAP_SELECTORS_BY_PAGE's ['health'] are not the same set — only in Python: []; only in the script: ['flights']. A key on one side alone is a page that silently never refreshes, or a script list nothing renders` |
| M2 | a key in Python that the script does not have | 282 → **280** (two) | the key-set message above, plus `expected layout.REFRESH_SWAP_SELECTORS_BY_PAGE[…] entry … verbatim in freshness.js` |
| M3 | the pending skip deleted from `swapNodes()` | 282 → **281** | `expected swapNodes() to skip a region marked pending — plan 23-07 marks its own optimistic control and this is the reconciliation rule that reads the mark (T-23-21)` |
| M4 | the dirty-form stand-down deleted from `tick()` | 282 → **281** | `expected tick() itself to stand the whole cycle down while the settings form has unsaved edits — a page mid-edit should not be fetching and diffing itself at all (T-23-20/T-23-21)` |
| M5 | the registry agrees but a second hard-coded list does the work | 282 → **281** | `the selector '.dashboard-grid' appears 2 time(s) in freshness.js's own code (comments stripped), expected 1 — one per registry entry that carries it, because the registry is the single site and a second occurrence is a second list` |
| M6 | the dirty gate keyed on the bar's PRESENCE (B1's own defect) | **first run: GREEN** → after the repair, 282 → **281** | `expected the gate to read the BAR'S OWN current visibility — a bar that exists and is hidden reports no unsaved edits, and taking its mere presence for an answer is 22-01/B1's defect exactly` |
| M7 | the `dirty-ready` half of the gate dropped | 282 → **281** | `expected the gate to read dirty-state.js's own liveness marker, got 'function unsavedEdits() { var bar = document.querySelector(DIRTY_BAR_SELECTOR); return !!(bar && !bar.hidden);'` |
| M8 | the fade fires on every swap (src comparison dropped) | 282 → **281** | `expected the fade to compare the picture's own src — the honest signal for 'this is a NEW render' — got 'function markPictureFade(existing, replacement) {…` |
| M9 | Home declares a class the page does not render | 282 → **281** | `Home declares regions it does not render: [('.home-status-tiles', 'home-status-tiles')] — a selector that matches nothing is a region that silently never refreshes, and nothing else in this codebase would notice` |
| M10 | the countdown left unmarked (`countdown=False`) | 282 → **280** (two) | `expected the countdown to be marked as one ('data-relative-countdown') — an unmarked element turns itself into an age the moment its instant passes, which is a different claim halfway through its own life` — plus the retargeted grace-window check |
| M11 | Home builds its own freshness line instead of calling the builder | 282 → **281** | `expected Home's freshness line to be layout.freshness_line_html()'s own output verbatim — one definition site, three call sites, the same contract frame_strip_html() and sidebar_nav() already state` |
| M12 | the pending skip removed (browser) | 38 → **37** | `a region holding an element marked data-pending was replaced — that repaints an optimistic control with the server's older answer and makes it bounce back under the user's finger (T-23-21, the D1-races-D2 rule plan 23-07 depends on)` |
| M13 | the dirty-form stand-down removed (browser) | 38 → **37** | `expected ZERO requests while the settings form has unsaved edits, counted 1 — a page mid-edit should not be fetching and diffing itself at all, and a swap landing on a half-edited form is B1 with a new cause` |
| M14 | the visibility gate removed from the listener AND `tick()` | 38 → **37** | `/ issued 1 request(s) while reporting itself hidden — zero from a backgrounded tab is the number D-12 was written to protect, and three pages polling instead of one is only acceptable because of it (T-23-20)` |
| M15 | the focus skip removed from `swapNodes()` | 38 → **37** | `the region holding keyboard focus was REPLACED — a refresh that silently moves focus to the top of the document while someone is tabbing through a card is A-20's own harm, smaller (D1)` |
| M16 | the fallback Save turned into a hidden span | 38 → **35** (three) | `lang=en: the fallback Save is the ONLY way to save this page with scripts blocked, and it is not rendered`, plus 22-01's and 22-10's own fallback-Save checks |

**M12–M15 were isolated deliberately**, one at a time, so each browser check is
proven to do its work unaided rather than merely going red alongside a source
scan.

### Did any of my own checks fail the "what would a *wrong* implementation do?" test?

**Two did. One was caught by mutation after it had shipped in a commit; one was
caught by its own control on first run, before it was ever green.**

**1. The dirty-form gate's source clause was vacuous, and mutation is what
found it.** The check asserted `".hidden" in code` — anywhere in
`freshness.js`. That file carries `document.hidden` and `pill.hidden` for
unrelated reasons, so **M6 (replacing the whole gate body with a presence-only
`!!document.querySelector(bar)` — 22-01/B1's own defect, the exact thing the
clause claims to forbid) left the harness GREEN.** The repair slices
`unsavedEdits()`'s own body and requires both halves *there*; M6 and M7 now cost
one red apiece. Committed separately (`0665958`) so the failure and its repair
are both legible, and the check's own comment records that it is
mutation-tested.

**2. The focus browser check's first control was wrong in a way that would have
made the check vacuous, and it said so on its first run.** The control marked
`.home-status-grid` and expected it to be replaced — but on a page where nothing
has changed in a second, `isEqualNode()` correctly skips that region, so the
control failed (`control: no region was swapped at all…`). That failure exposed
the deeper problem: the *focused* region was also unchanged, so the focus skip
was never being exercised and "the region survived" would have been true of a
loop with no focus rule at all. Both node-identity checks were rebuilt around
this: **dirty the region first** (so only the rule under test can save it), use
the freshness line as the witness that a swap happened (it differs on every
cycle by construction, because its pill carries a new `data-loaded-at`), and add
a **second phase** proving the same changed region IS replaced once the rule's
condition is removed. M12 and M15 are what prove the rebuilt versions real.

---

## Checks retargeted in place — two, both strengthened, neither weakened

1. **19-09/A-20's "no relative age inside `.page-header__freshness`" ban** gained
   its positive half (see the no-JS section). It still fails on A-20's own
   defect, and now also on a server-rendered age of any kind.
2. **22-UI-SPEC §3.3 rule 3's grace-window check** compared the WHOLE update
   cell byte for byte between two values of `now`. That was the same thing as
   "the grace window is invisible" only while the cell held nothing but a clock:
   a countdown is a duration and differs between any two instants by
   construction ("in 5m" at 11:10 and "in 1m" at 11:14 are one state reported
   twice, not two states). The check now compares the cell **with the countdown
   element removed** — byte-identical, as before — and adds three clauses that
   did not exist: the countdown must be present and marked in BOTH renderings
   (an element that disappears once its instant passes is itself a visible grace
   window), both must point at the SAME instant (the wake does not move inside
   its own grace window), and **neither rendering may carry a `warn`, `late`,
   `overdue` or `Expected since` token anywhere**. M10 reddens it.

Both carry the retarget and its reasoning in their own comments. **No test
exception was added anywhere; the suite still carries none.**

---

## `EXPECTED_CHECK_COUNT`

Every one re-derived by **running** the harness and appended as a new last
assignment citing this plan.

| Harness | Before | After | Task |
|---|---|---|---|
| `companion/test_status_pages.py` | 276 | **283** (+3 Task 1, +4 Task 2) | 1, 2 |
| `companion/test_config_page.py` | 233 | **235** (+2) | 2 |
| `companion/test_browser_ux.py` | 32 | **38** (+6) | 3 |
| `companion/test_companion_app.py` | 281 | 281 (untouched) | — |
| `companion/test_i18n.py` | 24 | 24 (untouched) | — |

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_status_pages.py` | 275/276 | **282/283** | 1 × `anomaly_active()` (documented) |
| `companion/test_config_page.py` | 233/233 | **235/235** | — |
| `companion/test_browser_ux.py` | 32/32 | **38/38** | — |
| `companion/test_companion_app.py` | 279/281 | **279/281** | 2 × WR-11 read-only (documented) |
| `companion/test_view_pages.py` | 146/146 | **146/146** | — |
| `companion/test_i18n.py` | 24/24 | **24/24** | — |
| `companion/test_contrast_check.py` | 43/43 | **43/43** | — |
| `server/test_manual_resolutions.py` | 21/23 | **21/23** | 2 × WR-11 read-only (documented) |

`PYTHON=… bash scripts/run-all-tests.sh` → three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline**, verified by
NAME: `add_entry()`/`delete_entry()` in `server/test_manual_resolutions.py`,
their two end-to-end counterparts in `companion/test_companion_app.py`, and
`anomaly_active()` in `companion/test_status_pages.py`. No new failure.
Coverage `TOTAL 6889 488 93%`, floor 83. `ruff check .` clean.

---

## The no-JS floor

Unchanged and asserted, not assumed.

- **Nothing this plan adds is a control.** No button, no switch, nothing that
  renders and does nothing. The registry, the page key, the skips and the fade
  are all properties of a loop that does not exist without scripts.
- **Every swapped region is server-rendered correctly on a normal load**; the
  loop replaces server markup with server markup from a second fetch of the same
  URL.
- **Display still saves**, proven in a scripts-blocked context at **360 px in
  both languages**, through the fallback Save, with the value read back from
  `device_config.load_device_config()` on disk — not from the DOM. This is the
  one assertion in the plan that would catch the Phase 22 P0 recurring, and it
  is at this plan's own commit for that reason.
- **The freshness line now reads a clock rather than a frozen zero** for that
  reader (above), which is a repair to the floor rather than a defence of it.
- **The countdown's expired form is already correct with no scripts**: the
  server renders the translated `waiting…` itself (23-05's `countdown=True`), so
  a late frame's cell never shows a frozen age.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-18 | mitigate | `redirect: "manual"` untouched and asserted present by name; the 303 an expired session produces is still an opaque non-ok response that takes the retry branch and swaps nothing. Two more pages inherit it rather than reimplementing it. |
| T-23-19 | mitigate | The swap mechanism is unchanged — `DOMParser` + `importNode` + `replaceChild`. No markup-writing sink was added; the per-file ban list check passes, and the new fade writes one class through `classList.add`. |
| T-23-20 | mitigate | Same 45s cadence, same ladder, same ceiling. **Zero requests from a hidden tab proven by COUNTING requests on all three pages**, each against a control proving the same page and trigger do fetch while visible (M14 reddens it). The dirty-form stand-down makes Display strictly quieter than the cadence alone. |
| T-23-21 | mitigate | The pending-region skip and the dirty-form stand-down, both proven in a browser with two phases each (M12, M13). |
| T-23-22 | accept | Unchanged: Display's refetch is same-origin, same-session, `no-store`, and returns the page the user is already looking at. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. No new route, no auth path, no schema change, no new file
access pattern. The one new server-rendered attribute (`data-refresh-page`)
carries `nav_slug()`'s own output and crosses `escape_html()`.

## Known Stubs

**None.** Every surface this plan claims is live IS live: Home, Display and
Health all refresh themselves, the countdown ticks, the fade fires on a genuinely
new picture and on nothing else. `data-pending` has no production writer yet —
**by design, and it is not a stub**: the skip is fully implemented, proven in a
browser from both directions, and 23-07's only remaining job is to set the
attribute on its own control.

## Deviations from Plan

**1. [scope] An extra task the plan did not carry: 23-05's no-JS regression on
Health's freshness line, fixed here.** Directed by the phase brief and executed
first, so Task 2's promotion of that line into `layout.py` carried the repair to
all three pages for free. Documented in full above.

**2. [Rule 3 — Blocking] A backtick in a `companion/static/*.js` comment, for
the fourth time in this phase.** ``the picture's own `src` `` in my new fade
comment broke the ES5-subset guard (`ES5-safe subset broken: '`' found in
freshness.js`). Caught by the harness in the same minute, reworded, re-run clean.
The trap is real and recurring: the file's own prose wants to quote identifiers
and the only safe quoting here is none.

**3. [judgement] The pending skip is inlined in `swapNodes()` rather than sitting
in a helper, and the Task 1 RED check was adjusted to match in the GREEN
commit.** The RED check demanded the literal `data-pending` inside
`swapNodes()`'s body; the first implementation put it in an `isPending()` helper
one line away. Rather than pin a helper name, the skip was inlined beside the two
skips it joins — which reads better against the three-item comment above it — and
the check now pins two things that are stronger than a literal in a body: that
the script's `PENDING_ATTR` constant equals `layout.REFRESH_PENDING_ATTR`
verbatim (a cross-file rename on one side alone is a skip that silently never
fires), and that the swap references it while `tick()` does not. **The contract
was not relaxed; the mechanism named by the check was.** M3 and M12 prove the
result.

**4. [judgement] `freshness_line_html()` returns "" when it has no render
instant.** The plan did not say what a caller with no `now` should get. An
element carrying an empty or invented instant reads as a correct time to a
script, which is worse than no element — the same argument
`relative_time_html()`'s own docstring makes, and the same degrade
`frame_strip_html()` applies to a missing next wake. The practical effect is that
Display's ~230 existing harness checks, which build a ctx with no `now`, see no
freshness line and did not have to change; `companion/app.py`'s `page_context()`
sets `now` on every real request. Pinned by its own clause in the config-page
check.

**5. [judgement] Home's recent-flights SECTION is the swap target, not its
`<ul>`.** The plan says "the recent-flights list". The `<ul>` does not exist when
the list is empty, and an index present on only one side is never swapped, so a
`<ul>` target would make the empty→first-flight transition the one thing this
page cannot show without a reload. The section is always rendered and contains no
other swap target.

**6. [judgement] The countdown sits in the update cell's caption row.** The plan
says "beside the existing clock". Inside the headline was tried first on paper
and rejected: two of the three headline templates carry trailing text after their
`%s` (`· quiet hours`), so a countdown spliced in there would read
"Next wake around 14:35 · in 3m · quiet hours". The caption row is the cell's
existing third slot, empty until now, and it puts the duration on its own line
under the state word — which is also what keeps the state word textually
untouched.

**7. [scope] `REQUIREMENTS.md` was not touched.** CFG-34 and CFG-35 both exist;
the standing instruction is not to tick either, and 23-11 closes both and owns
the coverage ledger.

## Findings the plan did not anticipate

**1. A countdown in the strip breaks a shipped byte-identity check, and the
check was right to notice.** See "checks retargeted in place" above. Worth
knowing generally: **any element whose text is a function of `now` will trip a
render-comparison check somewhere in this suite**, and the honest repair is to
compare everything except that element and then add clauses about the element
itself — not to drop the comparison.

**2. `isEqualNode` makes "nothing happened" browser checks vacuous by default.**
On a page where nothing has changed in the last second, every region is skipped
for the *unchanged* reason, so an assertion that a region survived proves
nothing about focus, pending, or anything else. Any later plan asserting a swap
skip must dirty the region first. Written into the checks' own comments and into
`EXPECTED_CHECK_COUNT`'s note.

**3. The freshness line is the only region that reliably differs between cycles**,
because its pill carries `data-loaded-at` at seconds precision. That makes it the
natural witness for "a swap really happened" in every browser check here — and it
is also why 23-05's finding 3 (that region is now always replaced) is load-bearing
rather than incidental.

**4. `page_shell(active=…)` already carried a per-page key**, so the registry
needed no new vocabulary. `nav_slug()`'s six values are exactly the right key
space, and `app.py` computes them in one place for every authenticated page —
which is why this plan needed no route change, as its `<files_owned>` predicted.

**5. Display's header now shows a freshness line above the screen caption.** A
real visual change on a settings page, not just plumbing. It renders in the
header's `freshness_html` slot, ahead of `action_html`, so the line sits between
the title and the caption row. The absolutely-positioned "Updating…" pill shares
`.page-header`'s top-right corner, which is unoccupied on that page today
(`_screen_selector_html()` renders "" with a single-member registry) — **but a
later plan that puts a control there will need to check the collision.** Named
for the wave-9 human sweep.

## Notes for later plans

- **23-07** sets `data-pending` and nothing else: the skip is shipped, proven
  from both directions in a browser, and `layout.REFRESH_PENDING_ATTR` is the
  name to render (the script's own constant is pinned equal to it). Mark the
  REGION that must not be repainted, or any element inside it — both work.
- **23-08** joins Flights to the loop by adding one key to
  `layout.REFRESH_SWAP_SELECTORS_BY_PAGE` and the same key to
  `SWAP_SELECTORS_BY_PAGE` in `freshness.js`. The key is `nav_slug("/flights")`,
  i.e. `"flights"`. Nothing else changes — and the harness fails if only one side
  moves. Flights also needs `layout.freshness_line_html(now)` in its header if it
  wants the loop to run at all: no `[data-loaded-at]`, no loop.
- **23-10** owns the "preview crossfade". `.is-fading-in` and
  `@keyframes skypane-fade-in` already exist and already fire on a genuinely new
  picture; that plan should spend them rather than declare a third block, and
  23-01's guard will fail a second definition of the same name.
- **23-11** owns: ticking CFG-34 and CFG-35 and rewriting their traceability
  rows; recording `.is-fading-in` and the second keyframes block in `SKILL.md`;
  and the human sweep — leave Home open for two minutes and watch the countdown
  fall and the tiles update without the page jumping, start editing a setting on
  Display and confirm nothing swaps under the cursor, and look at Display's
  header at 360 px now that it carries a freshness line above the screen caption.
- **Any plan editing `companion/static/*.js`**: the backtick ban is absolute and
  four plans have now tripped it in prose.

## Self-Check: PASSED

- All nine modified files exist on disk and are exactly the files the eight
  commits name, re-verified with `git show --name-only` on each.
- All eight commit hashes resolve in `git log`: `924b06f`, `aace4ca`, `848fc52`,
  `d52715e`, `0665958`, `5f827f3`, `b0a22f0`, `be282dc`.
- `.planning/phases/23-companion-dynamism-live-updates-real-switches-motion-budge/23-06-SUMMARY.md`
  exists.
- The working tree is clean after every mutation: `git status --short` empty and
  every mutated file restored from its committed state.
