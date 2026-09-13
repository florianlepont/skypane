---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 08
subsystem: ui
tags: [javascript, refresh, registry, progressive-enhancement, no-js-floor, motion, grid-template-rows, starting-style, disclosure, accessibility, playwright, harness]

requires:
  - phase: 23-01
    provides: "--motion-fast (the detail row's reveal and the chevron), --motion-slow (the new-row highlight), and the guard that rejects a bare animation duration, a duplicate keyframes name and the two Chromium-only sizing primitives"
  - phase: 23-02
    provides: "_no_js_page(viewport=...) and VIEWPORT_MIN_SUPPORTED — the phone card's scripts-blocked proof runs through both — and the finding about quick task 260913-cz6's check, which this plan acts on"
  - phase: 23-06
    provides: "REFRESH_SWAP_SELECTORS_BY_PAGE, REFRESH_PAGE_ATTR, freshness_line_html(), the three swap skips and _force_refresh()/_count_document_requests()/REFRESH_SETTLE_MS in the browser harness — Flights joins all of it by adding one key on each side"
  - phase: 22-09
    provides: "the phone card's artwork thumbnail and airline name (X5), re-scoped here rather than re-implemented, and the .row-toggle rule whose own comment named D3 as the plan that would give its chevron a transition"
provides:
  - "layout.REFRESH_PAGE_FLIGHTS and the Flights registry entry: the card list, the desktop table, the live count and the freshness line, with every element list-filter.js captures at load excluded BY NAME and the reason in the registry's own comment"
  - "layout.REFRESH_ROW_ID_ATTR / REFRESH_NEW_ROW_CLASS: the two cross-file literals the new-row highlight is built on"
  - "history_page._row_identity(): the runway_events row's own INTEGER PRIMARY KEY as a stable EVENT identity, on all three row elements, with a documented degrade"
  - "freshness.js's collectRowIds()/markNewRows(): a one-shot highlight applied only to identities absent from the set known before the swap"
  - "freshness.js's announceSwap() and the skypane-regions-swapped document event — the re-init hook the registry's own exclusions had been an argument for"
  - "flight-rows.js rebuilt on delegation plus a post-swap re-derive keyed by event identity, so a refresh neither unfolds the table nor closes the row you opened"
  - "list-filter.js: the count looked up fresh (which is what lets it be a swap region), the one applyFilter() re-run after a swap, and the count's ELEMENT animated on a real change"
  - "style.css: @keyframes skypane-row-arrive + .is-new-row; .flight-rows-live .flight-detail-row__reveal + its @starting-style entry; the .row-toggle__glyph transition; the .history-card__summary face"
  - "test_browser_ux.py +5 checks, and quick task 260913-cz6's Health check given the reduced-motion context 23-02 recorded as a finding for this plan"
affects: [23-09, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "a re-init HOOK rather than a permanent exclusion: the loop announces that it swapped and says nothing about what to do, and each script re-derives only what it owns — which is what let the Flights list become a swap region at all"
    - "identity before position: a row's DB primary key rendered as its own attribute, beside (never instead of) the render-local index the two representations are paired by, because the index renumbers the instant a detection lands"
    - "a height animation that is one-directional on purpose: opening animates through grid-template-rows 0fr->1fr entered by @starting-style, closing is an instant display:none, because that is the only end state that leaves neither the tab order nor the accessibility tree holding a row nobody can see"
    - "an animation gated on a class the owning script adds to <html>, so the entry animation is structurally unavailable to the reader whose scripts are blocked and for whom the content is already open"
    - "a card's own face promoted to be the <summary> of the <details> it already contained — a restructure of what opens it, not a new mechanism, and therefore free with no script"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/pages/history_page.py
    - companion/static/freshness.js
    - companion/static/flight-rows.js
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/test_view_pages.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "The row identity is runway_events.id, rendered as `e{id}`, NOT the loop index. flight-detail-{n} and data-filter-group={n} survive unchanged because they do a different job — they pair one render's two representations — and both renumber when a detection arrives at the top. A highlight or an open-row record keyed to either would light up, or reopen, whichever row inherited the number. Both failure modes are mutation-proven in a browser."
  - "The collapsed detail row keeps `display: none` and only the OPENING direction animates. The allow-discrete alternative was considered and declined in writing: for the whole of that transition, and on every browser without the property, a closed row's links and copy buttons are still focusable and still announced. A row that shuts instantly is a smaller loss than a row that is secretly still there."
  - "The height animation and its @starting-style entry are scoped to a class flight-rows.js adds to <html>. Unscoped, a scripts-blocked page — where every detail row is rendered open, by D-15's locked floor — would run the entry animation on up to fifty rows at first paint, unfolding the whole page in front of someone who has touched nothing."
  - "freshness.js now DISPATCHES a document event after a successful swap. Every exclusion in the swap registry is the same sentence — a script captured DOM at load and there is no re-init hook — and that is an argument FOR a hook, not against one. Flights is the page where the alternative ran out: its list IS the thing that must be replaced. The loop announces; it commands nothing and knows nothing about its listeners."
  - "The highlight's known set is populated from the page AS FIRST RENDERED, never empty. An empty set makes the first refresh announce the entire list, which is the same as announcing nothing. Mutation-proven: `var knownRowIds = {}` highlights 108 elements on a refresh that brought nothing new."
  - "The highlight spends --motion-slow, the AMBIENT token. Nobody pressed anything; the page ran it on its own to report something that happened elsewhere. A 180ms flash on a row the reader was not looking at is over before their eye reaches it."
  - "The highlight's keyframes fade to a transparent form of their OWN colour rather than to the `transparent` keyword, so the last animated frame and the first un-animated one are the same pixels on a row that has a background of its own."
  - "The one-hop resolve link moved OUT of the phone card's summary and onto the card face beside it. Inside a <summary> it would join the disclosure's accessible name — the card would announce itself as '... Name this airline' — and compete with the disclosure for the same activation. The phone card keeps every affordance the desktop row has, which is the X5 property 22-09 established."
  - "The filter count animates its ELEMENT, never its number: the text is written first and the class second, so the displayed value is correct at every instant, and it fires only when the rendered sentence actually differs."
  - "quick task 260913-cz6's Health check was given a reduced-motion context. 23-08's own animations provably cannot reach it — every one is scoped to a Flights-only selector and /health renders none of them — so this is prophylaxis, taken because it costs one argument and 23-10 owns the rest of D3's motion."
  - "Sticky day headers are NOT built. The developer settled it on 2026-09-13 on evidence from a rendered sketch; it is recorded as a settled decision with a revisit condition, not a deferral."

patterns-established:
  - "Announce-and-re-derive: a script that swaps regions dispatches one document event and carries no knowledge of its listeners; a script that owns state about those regions listens and re-derives its own. Both Flights scripts do; nothing else has to."
  - "Any list joining the refresh loop must answer three questions before its region list is written: what did each script on this page capture at load, what state does it hold that the server does not render, and what does the server render that would overwrite an applied client state."
  - "An entry animation on content that is visible without scripts must be gated on a class its own script adds, or it runs on the reader who has no script and no reason to see it."

requirements-completed: []

duration: ~2h
completed: 2026-09-13
---

# Phase 23 Plan 08: D7 — the live flights list Summary

**Flights is now the fourth page on the one refresh loop: a detection recorded
while the page is open arrives at the top with a wash that drains once and
never fires on a row that was already there, the detail row opens with real
height through a grid track rather than a Chromium-only primitive, the phone
card answers a tap anywhere through the disclosure it already contained, and a
refresh neither unfolds the table, nor closes the row you opened, nor undoes
the query you typed.**

## Performance

- **Duration:** ~2 h
- **Tasks:** 3/3
- **Files:** 0 created, 9 modified
- **Harness runtime:** `test_browser_ux.py` 130.7s → 138.2s (five new checks, four
  of which drive real forced-refresh cycles with a 1.2s settle each)

## Commits, in order

| # | Commit | Message |
|---|---|---|
| 1 (RED) | `4aeb0c6` | test(23-08): pin a stable event identity and a one-shot new-row diff before they exist |
| 2 (GREEN) | `6c14871` | **feat(23-08): Flights refreshes itself, and a row nobody had seen says so once** |
| 3 (RED) | `251d088` | test(23-08): pin the height, the chevron, the card's own face and the count before they move |
| 4 (GREEN) | `b6ac6bc` | **feat(23-08): the detail row opens with height, the card answers a tap, the count moves** |
| 5 | `ff8c13e` | test(23-08): a browser proves the list is live, the filter survives it, and a closed row is unreachable |

TDD gate sequence present and in order for Tasks 1 and 2 (`test(...)` then
`feat(...)`); Task 3 is test-only and has one `test(...)` commit. Both RED
commits were proven red **by running**: commit 1 reports view-pages **146/148**
and status-pages **284/287**; commit 3 reports view-pages **148/152** with all
four new checks named in the output. `git show --name-only` was run after every
commit and each carries exactly the files its message claims. No `git stash`,
no `git clean`, no blanket `git checkout --` over unstaged work.

---

## The cz6 check — the decision the brief asked for, and why

**Fixed.** `_health_tables_fit_their_wraps_with_every_disclosure_open()` (quick
task 260913-cz6) now runs in a `reduced_motion="reduce"` context, the one-line
change 23-02 recorded as a finding addressed to this plan. **The file's
reduce-requesting context count goes from 2 to 3** (`grep -c
'reduced_motion="reduce"'` → 3; the accompanying comment deliberately avoids the
literal so the grep keeps counting contexts rather than prose about them, which
is 23-01's own lesson).

**But the honest half first: this plan's animations provably cannot reach that
check today**, and the SUMMARY says so rather than claiming a fix for a defect
it did not introduce. Every surface 23-08 animates is scoped to a selector only
Flights renders —

| new animated surface | selector | rendered by |
|---|---|---|
| the detail row's height | `.flight-rows-live .flight-detail-row__reveal` | `history_page._flight_detail_row_html()` |
| the chevron | `.row-toggle__glyph` | `history_page._history_table_html()` |
| the card face's chevron position | `.history-card__summary::before` | `history_page._history_cards_html()` |
| the new-row wash | `.is-new-row` | applied by `freshness.js` only to `[data-flight-id]` |

— and `/health` renders none of them. The one shared surface is
`[data-filter-count]`'s reuse of `.is-fading-in`, which Health's registry card
also carries; it fires on a filter keystroke, and cz6 types nothing.

**So why fix it.** The exposure is structural, not incidental: the check sets
`details.open = true` and measures in the same task, Health carries four
disclosures, and a box measured mid-transition is narrower than its final box.
The cost of the fix is one argument. The cost of leaving it is an
intermittently red check that will be *harder* to diagnose than its sibling's
version of the same fault precisely because the sibling is green — and 23-10
owns the remainder of D3's motion and will animate more. Leaving a known
landmine for the next plan because today's blast radius happens to be zero is
the shape this phase keeps catching in other forms.

**It weakens nothing.** Reduced motion makes the final state the immediate
state through the app's *own* global override; the widths cz6 measures are not
a function of motion, so the same geometry is asserted, deterministically. The
check still passes (47/47 overall).

---

## Task 1 — Flights on the loop, and identity before position

**Four regions, and the exclusion is the interesting half.** Flights declares
`.page-header__freshness`, `ul.history-cards`, `.data-table-wrap` and
`[data-filter-count]`. Both renderings of the list, not whichever the current
breakpoint shows: the CSS sibling toggle decides which is *visible*, both are
always in the DOM, and swapping one would leave the other showing an older list
the moment a window was resized.

`list-filter.js` resolves four elements exactly once at load — the input, Clear,
the empty-state block and the set hooks — and every one of them is out, by
name, with the reason in the registry's own comment. `[data-filter-count]` is in
**because it stepped out of that category**: it is now looked up fresh inside
`applyFilter()`, which is the change that makes it swappable at all.

**The identity is the event's, never the row's position.** `runway_events.id` is
an `INTEGER PRIMARY KEY` assigned when the detection was recorded; it is
rendered as `e{id}` on the summary `<tr>`, its sibling detail `<tr>` and the
phone card `<li>`. `flight-detail-{n}` and `data-filter-group={n}` are untouched
and still the loop index, because they do a different job — they pair one
render's two representations — and **both renumber the instant a detection
arrives at the top**. A highlight keyed to either would announce every row below
the insertion; an open-row record keyed to either would reopen whichever row
inherited the number. Both are mutation-proven below.

The degrade is documented and one-directional: a row reaching `_row_identity()`
without an integer id falls back to its timestamp and hex, and if even those are
empty several rows share one value — the consequence of which is a highlight
**suppressed**, never one invented, because a shared identity reads as
already-known.

**The highlight.** `collectRowIds()` at load, `markNewRows()` after each swap,
`Object.prototype.hasOwnProperty` because the identities arrive as markup. The
class is added and never removed and nothing needs to remove it: the node it
lands on was itself just inserted, its background is its ordinary one before and
after, and the next swap replaces the node entirely. A removal path would only be
a way to fire the same arrival twice.

## The unplanned half of Task 1, and why it could not wait for Task 2

The plan puts the loop in Task 1 and the two Flights scripts in Task 2. That
split would have left one commit in history where **Flights refreshed and every
swap unfolded the entire table with every toggle dead** — the server renders
each detail row visible (D-15, locked) and carries no open/closed state at all,
so a swapped-in list arrives fully expanded, and `flight-rows.js` bound its
listeners to nodes that no longer exist.

So the swap-safety of both scripts landed in Task 1's GREEN commit (Rule 3 —
blocking; recorded under Deviations):

- **`flight-rows.js` rebuilt on delegation.** One `click` listener on `document`
  walking up from the target, answering "was this a toggle" and "which row is it
  inside" in a single pass. The walk keeps T-22-32's early return for an
  interactive target and keeps the "a click on the toggle toggles exactly once"
  property structurally — the toggle branch returns before the whole-row branch
  is reached.
- **A post-swap re-derive**, from an in-memory `openRows` record keyed by event
  identity, re-applying the collapsed class, `aria-expanded` and the accessible
  name in one function so they cannot drift.
- **`list-filter.js` re-runs its one `applyFilter()`** on the same announcement,
  because the server renders the list *unfiltered* and a swap that is not
  followed by a re-filter silently hands back every row under a typed query.

**The hook itself is the notable thing.** `freshness.js` now dispatches
`skypane-regions-swapped` on `document` after a successful swap. Every exclusion
in that registry, since 19-09, has been the same sentence — a script captured
DOM at load and there is no re-init hook — and that is an argument *for* a hook,
not against one. Flights is where the alternative ran out. The loop announces
and commands nothing; it knows nothing about its listeners, and a page with
neither script is unaffected.

## Task 2 — height, a chevron, a card face, a count

**The wrapper, and why there is one.** `<tr>` is `display: table-row`, so it is
not a grid container and has no track to grow; and `display` is a *discrete*
property, so it jumps regardless. The animation therefore lives one level down,
on a two-element wrapper inside the `<td>`: an outer single-track grid
transitioning `grid-template-rows` `0fr → 1fr`, an inner element carrying
`overflow: hidden` and `min-height: 0` (load-bearing — a grid item's automatic
minimum size is its content's, so without it the track never reaches `0fr` at
all and the row simply appears with a pointless transition attached).

**`interpolate-size` / `calc-size()` were not reached for.** They are
Chromium-only, 23-01's guard bans them by name, and the failure mode is the one
this phase cares about: an animation that runs for some visitors and silently
does nothing for the rest.

**The closing direction is instant, deliberately.** `display: none` stays the
collapsed end state. The `transition-behavior: allow-discrete` alternative D3
allows was considered and declined *in the stylesheet, in writing*: for the
whole of that transition — and on every browser without the property — a closed
row's copy buttons and links are still in the tab order and still in the
accessibility tree. A keyboard user tabbing past a "closed" row would land
inside it. That is the property the harness asserts, and the mutation below
shows what it costs.

**`@starting-style`, scoped.** A row going from `display: none` to displayed has
no previous computed value to transition from, so the entry value has to be
declared. Both the transition and the `@starting-style` block are scoped to
`.flight-rows-live`, the class `flight-rows.js` adds to `<html>` — because with
scripts blocked every detail row is rendered open, and an unscoped entry
animation would unfold up to fifty rows at first paint in front of a reader who
has touched nothing. Where `@starting-style` is unsupported the row simply
appears, which is exactly what it did before this plan: the animation is
additive and degrades to today.

**The chevron** takes `transition: transform var(--motion-fast) ease` —
`transform` by name rather than `all`, so a future declaration added to that rule
is not animated by accident — with **no per-rule reduced-motion block**, which
`references/control-density.md:78` pre-approved and pre-refused in advance.
22-09's own comment naming D3 as the plan that would add it has been replaced by
the record of its having been added.

**The card's face IS its summary.** The `<details class="history-card__details">`
the card already contained now opens from the card's own primary line, secondary
line and airline line — thumbnail and airline name exactly where 22-09 put them,
not rebuilt. The negative margin is the "anywhere" part: `.history-card` carries
`padding: var(--space-md)`, and without pulling the summary out by exactly that
padding a tap on the card's rim would land on the `<li>` and do nothing, which
reads as a broken control rather than as a boundary. `color: inherit` keeps the
flight's own data out of the accent colour (the chevron keeps it); `order: 1` on
the shared `summary::before` moves that chevron to the trailing edge rather than
indenting three stacked lines behind it. The shared chevron is **reused, not
redrawn** — a clause asserting that was added to the shipped T3 check.

**The count animates its element, never its number.** `list-filter.js` writes
the text first and the class second, removes-reflows-re-adds so a second change
restarts it, and fires only when the rendered sentence actually differs. It
spends the stylesheet's existing `.is-fading-in` — whose own comment says it
names the motion rather than the component so the next thing that changes under
the reader spends it — so no fourth keyframes block was declared.

---

## FINDING: sticky day headers are NOT built

Recorded as the plan requires, in its own four parts, and noted as a **settled
decision rather than a deferral**:

1. **D7 asks for sticky day headers.** Phase 22's T4 removed the app's previous
   sticky claim outright on a structural ground: a `position: sticky` `th` inside
   `.data-table-wrap` — a wrapper with `overflow-x: auto` and no height — has no
   vertical scrollport to stick within, so the declaration was inert from the day
   it shipped. **That ground has not changed.**
2. **Making it engage means giving the Flights table a bounded-height scroll
   region of its own.** That is a layout decision with a measured width and
   density budget behind it (`references/data-density.md`), and it interacts with
   the phone card list, which is a different rendering entirely.
3. **`references/data-density.md`'s entry is marked SUPERSEDED**, and the design
   system's own standing rule for reversing a recorded verdict is a new argument
   and a new decision, not a silent rewrite — the same bar
   `references/mobile-navigation.md:126` sets for its own rejected patterns.
4. **Therefore: not built here.** It is a developer decision, not a planner's.

**And it has since been made.** The developer settled it on 2026-09-13 as
option A, on evidence from both variants rendered on the real page with seeded
data and scrolled to the same offset: **every flight row already carries its own
date** (`1 août 21:41`), so a pinned title would repeat what is already on every
line — and the sticky variant shrinks the list to a ~7-row box inside a
half-empty page with a clipped row peeking under the header. It is recorded on
the Phase 23 ROADMAP entry and in `references/data-density.md` with its revisit
condition: **only if the per-row date is ever removed**, for phone density say,
which would make the title non-redundant.

**Nothing sticky was added.** `grep -cE 'position: *sticky'
companion/static/style.css` → **3**, its pre-plan value, of which two are prose.

---

## Mutation testing

Seven mutations, each reverted and the tree verified clean afterwards.

| # | mutation | result | message (quoted from the run) |
|---|---|---|---|
| M1 | `var knownRowIds = collectRowIds()` → `= {}` | browser 47 → **46** | `a refresh that brought nothing new highlighted 108 element(s) — a list that announces itself every cycle has told the reader nothing, and is how they learn to ignore it` |
| M2 | `markNewRows()` removed from `applySwap()` | browser 47 → **46** | `expected exactly the arrived row ['e37'] to carry the highlight, got [] — a highlight on a row that was already there is a claim that it just landed, which is false` |
| M3 | the collapsed row held present at zero height (`display: table-row` plus `grid-template-rows: 0fr`) | browser 47 → **46** (exactly one), view-pages 152 → **151** | `a COLLAPSED detail row let 4 of its 4 controls take focus (['BUTTON.copy-btn', 'BUTTON.copy-btn', 'BUTTON.copy-btn', 'BUTTON.calendar-disconnect-btn']) — a row held present at zero height is still in the tab order and still in the accessibility tree, so a keyboard user walks into a row nobody can see (T-23-32)` |
| M4 | `list-filter.js`'s post-swap re-run removed | browser 47 → **46** | `a refresh handed back 38 visible rows under a query that matches one — the server renders the list unfiltered, so a swap that is not followed by a re-filter silently undoes what the reader asked for` |
| M5 | `flight-rows.js`'s post-swap re-derive removed | browser 47 → **46** | `after a refresh 38 of 38 detail rows are open ([…]), expected exactly the one that was opened ('e37'). Every row open is the server's own markup arriving un-collapsed; the WRONG row open is a record keyed to a position that just renumbered` |
| M6 | the open-row record keyed by `detail.id` (position) instead of the event identity | browser 47 → **46** | `after a refresh 1 of 38 detail rows are open (['e38']), expected exactly the one that was opened ('e37')` — the wrong row, which is the failure a position key produces and a count-only assertion would miss |
| M7 | `.history-card__summary`'s negative margin and padding removed | browser 47 → **46** | `the card's summary is 278px wide inside a 312px card — a tap on the rim between them lands on nothing, which reads as a broken control rather than as a boundary` |

M3 produces **exactly one** browser failure, as the criterion predicted; the
second failure is the source-level view-pages clause asserting the same
property, which is the intended belt-and-braces.

## Did any of my own checks fail the vacuity question?

Asked of every new check: *what would a wrong implementation do?* **Three
failed it, all caught before landing.**

1. **"A new row is highlighted" is satisfied by a script that highlights
   everything** — and highlighting everything is both the likelier bug and the
   more damaging one, because the reader learns the movement means nothing. The
   check therefore asserts the marked set **equals** the arrived set, in both
   renderings, and carries a first-load clause and a nothing-changed clause. M1
   and M2 exercise both directions.
2. **"A refresh does not close the row you opened" is vacuous with focus still
   on the toggle.** A click leaves focus on the button, and `freshness.js`'s
   focus skip (22-15's, not this plan's) would have left the whole region alone
   for a reason having nothing to do with the re-derive — the check would have
   passed against a script that re-derives nothing at all. Fixed by blurring
   before forcing the refresh, and M5 confirms the fix.
3. **"A collapsed row is unreachable" is satisfied by a page with no detail row
   at all.** The check now opens the row in a control phase and requires the
   *same* controls to become reachable, so the assertion is about the row being
   closed rather than about the page being empty.

A fourth was caught by the harness rather than by the question, and is the same
substring-collision class 23-07 hit: `.history-card__summary::before` **ends in**
`summary::before {`, and 22-15's shipped T3 marker check looked up the first
occurrence of that needle in the file — so it silently started reading the
card's positioning override instead of the global chevron. The needle was
anchored and the check gained a clause asserting the card **reuses** the shared
chevron rather than redrawing it. The check was right to go red.

## Criteria that did not evaluate as predicted

Two. Both recorded rather than adjusted away, per the standing constraint.

**1. `grep -c 'data-filter-input' companion/layout.py companion/static/freshness.js | grep -v ':0' | wc -l` outputs `1`, not `0`.**
The single occurrence is `companion/layout.py:1848` — inside the registry
**comment** the same task's `<action>` instructed me to write ("Say it in the
registry comment rather than leaving the next reader to rediscover it"). The
plan's two instructions are in direct tension: name the excluded element in
prose, and grep the raw file for zero occurrences of its name. Neither the code
nor the criterion was changed. **The property the criterion is about is
enforced by two live checks**: the shipped
`_19_09_freshness_swap_selectors_pinned_both_directions` clause (`if
"[data-filter-input]" in js` — freshness.js carries **0**, as the grep's own
per-file output shows) and this plan's new status-pages check, which iterates
the registry tuple itself and fails on any selector naming the input, Clear, the
empty state or the set hooks.

**2. `grep -c 'interpolate-size\|calc-size(' companion/static/style.css` outputs `1`, not `0`.**
Same shape. The occurrence is my own stylesheet comment explaining *why* the
mechanism is `grid-template-rows` and not those two. 23-01's SUMMARY recorded
this exact decision in advance — the ban is measured on **comment-stripped**
source "so a future plan may still write down WHY they are banned without
failing the ban" — and both live guards do strip comments: 23-01's own motion
guard (`companion/test_companion_app.py`, green) and this plan's new view-pages
check. Measured the way those guards measure it, the answer is **0**:

```
raw grep                       -> 1   (one comment)
comment-stripped               -> 0   (no declaration)
```

This is the "beware criteria your own prose trips" trap, hit for the fourteenth
time in this project and twice in one plan.

## Other acceptance greps, run literally

```
grep -c '@keyframes' companion/static/style.css              -> 3   (was 2; +1 argued for below)
grep -v '^ *[*/]' style.css | grep -c 'prefers-reduced-motion: reduce'
                                                             -> 2   (unchanged)
grep -v '^ *[*/]' style.css | grep -c 'prefers-reduced-motion'
                                                             -> 3   (its recorded pre-task value)
grep -c 'grid-template-rows: 0fr' companion/static/style.css -> 1   (criterion: >= 1)
grep -cE 'position: *sticky' companion/static/style.css      -> 3   (pre-plan value)
grep -c 'reduced_motion="reduce"' companion/test_browser_ux.py -> 3 (2 -> 3, deliberately)
ruff check .                                                 -> All checks passed!
```

**The third `@keyframes` block is argued rather than asserted**, as 23-01
required and 23-06 precedented. The two existing blocks are both about opacity:
one cycles it forever, one ramps it once from nothing. A newly-arrived table row
needs neither — fading a line of text in from zero opacity makes it materialise
out of the page background, and the pulse would leave it flashing forever. What
says "this one just landed" is a wash of colour that drains away. It fades to a
transparent form of its **own** colour rather than to the `transparent` keyword,
so the last animated frame and the first un-animated one are the same pixels on
a row with a background of its own.

**`git diff` on `companion/static/list-filter.js`** over the whole plan: 80
insertions, 2 deletions; **14 added and 2 removed lines of actual code**, the
rest comment. The count's text production is untouched —
`getAttribute("data-filter-count-template")` and both
`.replace("%d", String(...))` calls are byte-identical; the only change to that
statement is that its result goes to a local before being written to
`textContent`, so the value can be compared before it is assigned.

## The no-JS floor

Three floors, each asserted rather than assumed, and all three now proven in a
real scripts-blocked Chromium at the 360px contract floor in the same check:

1. **The detail row.** `document.querySelectorAll('.flight-detail-row--collapsed').length`
   is **0** with scripts blocked — the collapsing class has exactly one writer
   and it cannot run there — so every detail is on screen, exactly as before this
   plan.
2. **The animation is structurally unavailable to that reader.**
   `document.documentElement.className` does not contain `flight-rows-live`, and
   both the transition and the `@starting-style` entry are scoped to it, so the
   page declares no transition at all rather than declaring one that happens not
   to fire.
3. **The whole-card tap.** The scripts-blocked card starts closed, is clicked on
   its secondary line — away from every control — and **opens**. It is the same
   native `<details>` the card already contained; the change is which element is
   the `<summary>`, not what opens it.

The filter and the list are unchanged enhancements over a fully-rendered,
unfiltered, complete server-rendered list, and the highlight exists only as a
consequence of a swap, of which there are none with no script. **Nothing this
plan adds renders a control that does nothing.**

## Checks retargeted in place — four, none weakened

1. **`_history_timestamps_carry_a_relative_time_element` (23-03).** A bare
   `re.search` over the whole page found the header's new freshness clock first
   and measured the page's render instant instead of the row's age. Its subject
   has always been the timestamp cell, so it measures inside the row list now —
   and asserts in the same breath that the header's element **is** present and
   **is not** in the list, so the narrowing is honest rather than a dodge.
2. **`_now_showing_no_preview_freshness_apparatus` (D-18).** A real reversal, so
   it is written down rather than dropped: the check forbade `data-loaded-at` on
   this page outright, and D7/CFG-37 now requires it (no marker, no loop). It
   now requires **exactly one**, read back from `layout.freshness_line_html()`
   rather than pinned as a literal, while still forbidding both halves of what
   D-18 actually retired — the `data-stale-banner` and a Refresh **link**.
   `history_page.render()`'s own "deliberately NOT (re)introduced … do not
   restore it later as an oversight" paragraph is marked SUPERSEDED in place
   with the same reasoning.
3. **`_23_06_the_page_key_is_server_rendered_and_gates_the_loop`.** Its "a page
   with no registry entry" clause used `"flights"` as the example, and Flights
   now declares four regions — so the example stopped being an example while the
   assertion went on passing. It is `"airlines"` now, **plus a new guard** that
   fails if that key ever gains an entry too, so the next plan cannot repeat the
   drift silently.
4. **`_every_disclosure_has_a_marker_and_no_header_claims_to_stick` (T3/T4).**
   The needle anchored, with a new clause proving the card summary reuses the
   shared chevron rather than redrawing it (see the vacuity section).

**The disclosure sweep's Flights minimum is UNCHANGED at 37** — the card
restructure moves what the `<summary>` *is*, not how many `<details>` the page
renders. `("/flights", 37)` stands, and the sweep passes at all three widths in
both languages.

**No test exception was added anywhere; the suite still carries none.**

## `EXPECTED_CHECK_COUNT`

Every one re-derived by **running**, appended as a new last assignment citing
this plan.

| Harness | Before | After | Task |
|---|---|---|---|
| `companion/test_view_pages.py` | 146 | **152** (+2 Task 1, +4 Task 2) | 1, 2 |
| `companion/test_status_pages.py` | 285 | **287** (+2) | 1 |
| `companion/test_browser_ux.py` | 42 | **47** (+5) | 3 |
| `companion/test_companion_app.py` | 290 | 290 (untouched) | — |
| `companion/test_i18n.py` | 24 | 24 (untouched) | — |

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_view_pages.py` | 146/146 | **152/152** | — |
| `companion/test_status_pages.py` | 284/285 | **286/287** | 1 × `anomaly_active()` (documented) |
| `companion/test_browser_ux.py` | 42/42 | **47/47** | — |
| `companion/test_companion_app.py` | 288/290 | **288/290** | 2 × WR-11 read-only (documented) |
| `companion/test_config_page.py` | 237/237 | **237/237** | — |
| `companion/test_i18n.py` | 24/24 | **24/24** | — |
| `companion/test_contrast_check.py` | 43/43 | **43/43** | — |
| `server/test_manual_resolutions.py` | 21/23 | **21/23** | 2 × WR-11 read-only (documented) |

`bash scripts/run-all-tests.sh` → three FAILED harnesses carrying **exactly the
documented 5-failing-check root-sandbox baseline**, verified by NAME:
`add_entry()`/`delete_entry()` in `server/test_manual_resolutions.py`, their two
end-to-end counterparts in `companion/test_companion_app.py`, and
`anomaly_active()` in `companion/test_status_pages.py`. **No new failure.**
Coverage `TOTAL 6926 490 93%`, floor 83.

**On the non-reproducing extra `test_companion_app.py` failure the brief
warned about: it did not recur.** A full-suite baseline run was taken before any
edit (288/290, the two WR-11 checks and nothing else) and the full suite was run
again at the end with the identical result, plus four standalone runs of that
harness in between. Five observations, no third failure. Reported either way, as
asked.

## Deviations from Plan

**1. [Rule 3 — Blocking] `flight-rows.js` and `list-filter.js` were made
swap-safe in Task 1's GREEN commit, not in Task 2.** The plan's file lists put
both scripts in Task 2, but the loop cannot correctly land without them: the
intermediate commit would have refreshed Flights while every swap unfolded the
whole table and left every toggle dead. Both files are in the plan's
`files_modified`; only the task attribution moved. Documented in full above.

**2. [Rule 3 — Blocking] `freshness.js` gained a post-swap announcement, which
the plan did not anticipate.** The plan's `<action>` says to exclude "anything
`list-filter.js` captured at load" while also including the count that script
captured, and says nothing about `flight-rows.js`, which captures at load too.
Both tensions resolve the same way: one document event, two listeners, each
re-deriving only what it owns. The alternative — excluding the list — would have
deleted D7's entire subject.

**3. [judgement] The count element stopped being captured at load.** This is
what makes the plan's own "include the filter count" instruction consistent with
its "exclude anything captured at load" instruction. One line moved into
`applyFilter()`.

**4. [judgement] `flight-rows.js` adds a class to `<html>`.** The plan did not
anticipate needing one. It is the animation's scope and nothing else — its own
header records that the per-row class-at-load contract is unchanged and that the
reason for the narrow, per-script pattern (a CSP that blocks this one script)
still holds, because this class is added by this file too.

**5. [judgement] `COUNT_SELECTOR` is built by concatenation from `COUNT_ATTR`.**
Written out as `"[data-filter-count]"` it tripped `test_i18n.py`'s Check 6,
which reads a bracketed lowercase string in an ALL-CAPS JS constant as
untranslated copy — 23-07's finding 3, recurring. The fix is this codebase's own
idiom (`PENDING_ATTR`/`PENDING_SELECTOR`, `FADE_IMAGE_CLASS`/`FADE_IMAGE_SELECTOR`),
not a scanner exception. **No test exception was added.**

**6. [judgement] The one-hop resolve link moved out of the card's `<details>`**
rather than riding inside the summary with the airline name. Reasoning in the
key decisions above; the harness asserts both halves (it is still on the card,
and it is not in the summary).

**7. [scope] `companion/i18n_fr/flights.py` is in `files_modified` and was NOT
modified.** This plan adds **no new user-facing string**: the card's summary
keeps the existing, already-translated "More details" as its visually-hidden
trailing label, so there is no new French entry to add and no orphaned key to
remove (`health_page.py` produces that key too). `test_i18n.py` is 24/24.

**8. [scope] `REQUIREMENTS.md` was not touched.** CFG-37 exists and its row
already records this; per standing instruction, **23-11 closes it**. CFG-32's
box is not ticked here either — 23-09 and 23-10 still owe D3 work.

## Things the plan assumed that turned out otherwise

1. **`list-filter.js` is not the only script that captures Flights' DOM at
   load.** `flight-rows.js` binds one listener per toggle and one per row and
   adds a class per detail row, all at load. The plan's exclusion reasoning names
   only the filter; applied literally it would have produced a page whose
   toggles die on the first refresh.
2. **A swap does not only lose script state, it loses APPLIED state.** The
   server renders the list unfiltered and un-collapsed, so a refresh actively
   *undoes* a typed query and an opened row. Standing down the tick while the
   caret is in the box (22-15's focus rule) covers the moment of typing and
   nothing after it.
3. **The plan's "include the filter count" and "exclude anything list-filter.js
   captured at load" cannot both be true of the shipped script.** One of them had
   to move; the count did.
4. **The header's freshness line collides with a shipped check that scans for
   the FIRST `<time data-relative>` on the page.** Any page joining this loop
   gains an element of that shape above its content; 23-06's own finding 1
   generalises here ("any element whose text is a function of `now` will trip a
   render-comparison check somewhere in this suite").
5. **`_flight_detail_row_html()`'s `<td>` needs TWO wrappers, not one.** The
   plan says "a grid wrapper … with the wrapper clipping its overflow"; the
   0fr/1fr technique needs the clipping and the `min-height: 0` on the grid's
   *child*, or the track never reaches zero.
6. **A selector ending in `summary::before` collides with the global disclosure
   marker's own check.** Same class as 23-07's `data-quick-switch-control`.
7. **D-18's "no page-level freshness apparatus on this page" was a recorded
   decision this plan reverses**, not merely an absent feature. It had a check
   and a code comment defending it, both of which had to be retargeted with the
   reversal written down.

## Known Stubs

**None.** Every surface this plan claims is live IS live: Flights refreshes from
the same loop, a genuinely new detection is highlighted once and only once, the
detail row's height really animates (the computed `transitionProperty` is
asserted, not the declaration), the card really opens from a tap on its face
with and without scripts, and the count really moves on a real change. The one
element with no consumer of its own is the `skypane-regions-swapped` event on
pages other than Flights — which is not a stub but a listener-free dispatch, and
it is what makes the hook general rather than Flights-specific.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-29 | mitigate | The swap mechanism is unchanged (`DOMParser` + `importNode` + `replaceChild`). The highlight is a `classList.add` on a node the swap already inserted, asserted by a source scan that no markup-writing sink appears in its body. The new document event carries no payload at all. |
| T-23-30 | mitigate | The diff is over server-rendered row identity, applied only against a set known from the page as first rendered, and asserted in **both** directions in a browser against a real inserted detection (M1, M2). |
| T-23-31 | mitigate | Same 45s cadence, same visibility gate, same retry ladder, same in-flight guard — Flights adds one registry key and no code path. The dirty-form and focus stand-downs apply unchanged, and the filter check proves zero requests while the caret is in the box, against a control. |
| T-23-32 | mitigate | The collapsed row is kept out of the tab order and the accessibility tree by `display: none`, asserted as the keyboard question directly (every focusable descendant asked to take focus and required to fail), against a control phase proving the same controls are reachable once open. M3 reddens it. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. No new route, no auth path, no schema change, no new
file access pattern, no new server-rendered value that does not cross
`escape_html()` at its own site (`data-flight-id` is a database integer and is
escaped anyway).

## Notes for later plans

- **23-09 / 23-10** now have a re-init hook available: `freshness.js` dispatches
  `skypane-regions-swapped` on `document` after every successful swap. Any script
  that holds state about a swapped region should listen and re-derive rather than
  have its region excluded from the registry. The event carries no payload by
  design — a listener re-derives from the live DOM, it is not told what changed.
- **23-10** owns the rest of D3. `@starting-style` is now in the stylesheet once,
  with its reasoning; `@keyframes skypane-row-arrive` and `.is-new-row` join
  `.is-breathing` and `.is-fading-in` as motions named for what they do, and a
  plan wanting "a value just changed" should spend `.is-fading-in` rather than
  declare a fourth block. The reduce-block count is still 2 and the guard still
  fails a move.
- **23-10** should also know that quick task 260913-cz6's check is now
  motion-proof, so animating a Health disclosure is safe from that direction. Its
  sibling (260913-eab) was already done by 23-02. Both are covered; there is no
  third.
- **23-11** owns: ticking CFG-37 and CFG-32 and rewriting their traceability
  rows; recording in `SKILL.md` the third keyframes block, the detail row's
  one-directional height animation and its stated reason, the card-face summary
  (which joins `references/control-density.md`'s touch-target register as a
  met-directly entry — a whole card at 360px is 312×~120px), and the
  announce-and-re-derive pattern; carrying the sticky finding above forward as
  **already decided** rather than as an open question; and the human sweep —
  leave Flights open until a detection lands and confirm the new row is obvious
  once and then settles, open and close a detail row and a phone card on a 360px
  window, and type in the filter while the page is live and confirm nothing moves
  under the cursor.
- **Flights' header now carries a freshness line**, like Health's, Home's and
  Display's. That is a real visual change to a page whose header previously held
  only a title and a purpose sentence, and the "Updating…" pill shares
  `.page-header`'s top-right corner — unoccupied on this page today, and worth a
  glance in the wave-9 sweep.

## Self-Check: PASSED

```
FOUND: companion/layout.py
FOUND: companion/pages/history_page.py
FOUND: companion/static/freshness.js
FOUND: companion/static/flight-rows.js
FOUND: companion/static/list-filter.js
FOUND: companion/static/style.css
FOUND: companion/test_view_pages.py
FOUND: companion/test_status_pages.py
FOUND: companion/test_browser_ux.py
FOUND: .planning/phases/23-.../23-08-SUMMARY.md
FOUND: 4aeb0c6  FOUND: 6c14871  FOUND: 251d088  FOUND: b6ac6bc  FOUND: ff8c13e
```

Working tree clean after every mutation: `git status --short` empty and every
mutated file restored from its committed state, verified with `git diff --stat`
after each.
