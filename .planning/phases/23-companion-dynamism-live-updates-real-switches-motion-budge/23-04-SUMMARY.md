---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 04
subsystem: ui
tags: [css, view-transitions, prefers-reduced-motion, accessibility, no-js, playwright, cssom]

requires:
  - phase: 23-01
    provides: "the global reduce block's gap note this plan closes in place, and EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, the constant it was written to let this plan move from 0 to 1"
  - phase: 23-02
    provides: "test_browser_ux.py's check()/EXPECTED_CHECK_COUNT convention, its _login() helper and the precedent of a reduced_motion='reduce' context"
provides:
  - "one @media (prefers-reduced-motion: no-preference)-wrapped navigation at-rule: cross-document view transitions, zero script, zero markup change"
  - "three view-transition names — skypane-sidebar (.dashboard-sidebar), skypane-title (.page-title), skypane-picture (.preview-frame__image) — each in a rule of its own"
  - "VIEW_TRANSITION_NAMES / VIEW_TRANSITION_ROUTES in test_browser_ux.py: the declared-name set and the routes each must resolve on, both asserted against the real browser"
  - "two browser checks: per-route COMPUTED-value uniqueness, and the opt-out read off the at-rule's own parent rule in the CSSOM"
  - "the corrected navigation-landmark count: TWO per authenticated document since 22-14, not the three 23-RESEARCH.md and every Phase 23 plan states"
affects: [23-05, 23-08, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "a conditional group rule used as an accessibility opt-out that PREVENTS SETUP, rather than an override that zeroes a duration after setup — the shape the global `*, *::before, *::after` block structurally cannot provide for a pseudo-element tree"
    - "asserting a media condition by reading conditionText OFF THE GUARDED RULE'S OWN PARENT, never by calling matchMedia() with a literal — the literal form passes with the rule unwrapped, which is the entire defect"
    - "counting COMPUTED values across every element of a rendered route to prove a selector matches once, where a source scan can only prove a declaration appears once"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_companion_app.py
    - companion/test_browser_ux.py

key-decisions:
  - "Task 1 adds NO new check to test_companion_app.py, only the constant move. The plan's own acceptance criterion ('deleting the @media wrapper produces EXACTLY ONE failure') forbids a second one: any new check asserting the nesting would also go red on that mutation and make it two. The nesting is asserted instead by Task 2, in a browser, where it can also be distinguished from a wrapper around some other rule."
  - "Each of the three names is declared in a rule of its own, never on the four-selector rule .preview-frame__image already shares. That shared rule also carries img.recent-flight__thumb and img.history-card__thumb, which render once PER ROW — a name there would collide 36 times on /flights. This is the read_first question the plan asked to be answered explicitly."
  - "The opt-out check reads the media condition from the at-rule's parentRule and evaluates THAT string, rather than calling matchMedia('(prefers-reduced-motion: no-preference)'). The literal form is the vacuous version: it is false under a reduce context no matter what the stylesheet says, so it would pass with the at-rule sitting unwrapped at the top level."
  - "The plan's (and 23-RESEARCH.md's) 'THREE nav copies render simultaneously' is out of date and was corrected in both files rather than repeated. 22-14 Task 2 REMOVED the preferences panel's <nav>; the live count is two. The hazard is unchanged in kind and was measured, not reasoned about."

requirements-completed: []

duration: ~70min
completed: 2026-09-13
---

# Phase 23 Plan 04: D10 — native cross-document view transitions Summary

**One media-wrapped at-rule and three names give every navigation in the app a native cross-fade with no script, no framework, no fallback branch and no markup change — and two browser checks make the feature's only two silent-failure modes loud, both proven against mutations that leave every source-level scan in the repository green.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 2/2
- **Files modified:** 3 (0 created), +212 lines, −20
- **Harness runtime:** `test_browser_ux.py` 51s → 60s (the two new checks cost ~9s: 6 route loads plus 2 signed-in contexts)

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 (RED) | `cea044f` | test(23-04): raise the no-preference wrapper pin from zero to one |
| 1 (GREEN) | `193c04c` | feat(23-04): cross-document view transitions, media-wrapped and uniquely named |
| 1 (fix) | `7aee6dc` | docs(23-04): the document carries two navigation landmarks, not three |
| 2 | `0b7e4bd` | test(23-04): a browser proves the names are unique and the opt-out real |

TDD gate sequence present and in order: `test(cea044f)` red at 270/273 before any CSS existed → `feat(193c04c)` green at 271/273 → the Task 2 test commit. No `git stash`, no `git clean`, no model name in any message.

## What landed

### Task 1 — the at-rule, its wrapper, three names

Placed immediately after 23-01's gap note, so a reader meets the global
override, the gap it cannot reach and the one feature that escapes it in a
single region of the file rather than seven thousand lines apart:

```
@media (prefers-reduced-motion: no-preference) {
  @view-transition {
    navigation: auto;
  }
}

.dashboard-sidebar    { view-transition-name: skypane-sidebar; }
.page-title           { view-transition-name: skypane-title; }
.preview-frame__image { view-transition-name: skypane-picture; }
```

(shown compressed here; each is an expanded rule in the file, house style).

**23-01's gap comment was updated in place**, not left describing a future: its
closing paragraph now reads "That gap is CLOSED, by the rule immediately below"
and cites this plan. The global reduce block itself is byte-identical and its
live count is still 2.

The new comment records, with sources: the CSS View Transitions Level 2 §8.3.1
permission to nest the at-rule in a conditional group rule; that this exact
nested form was verified to parse **and be retained in the CSSOM** in the
project's own harness Chromium 151.0.7922.34 (re-verified this session, not
carried from the research — see "Interfaces re-verified" below); that the
wrapper is preferred over zeroing the pseudo-elements' durations because it
prevents the transition being SET UP at all; that transitions are same-origin
only by spec and nothing here navigates off-origin; and the name-uniqueness
constraint with the structural reason behind each of the three selectors.

**No `animation: none` second belt was added** anywhere, per the plan's
instruction and `accessibility-contrast.md`'s dead-code-not-a-safety-net
verdict.

**No markup change was needed** — the `<files_owned>` clause asked for a finding
if one were. All three classes already exist and already render at the right
cardinality. No Python module and no script was opened for writing.

### Task 1's test half — one line, as anticipated

`EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS` 0 → 1. The guard's assertion
bodies and failure messages are byte-identical; only the constant and its own
preamble comment changed, the comment because leaving "it starts at ZERO because
the gap it exists for is not yet closed" beside a value of 1 would be the same
defect the plan forbids in style.css. No other assertion in the guard needed
relaxing — the signal the plan said to stop and record had one turned up.

### Task 2 — the two silent failures, made loud

**Check A — per-route name uniqueness, from COMPUTED values.** Visits all six
authenticated routes in one signed-in context and, on each, reads
`getComputedStyle(el).viewTransitionName` for **every element** in the document,
plus the set of names the **served** stylesheet declares (walked out of
`document.styleSheets`). Four assertions:

1. the declared set must equal `VIEW_TRANSITION_NAMES`'s keys;
2. no computed name may resolve to more than one element — over *every* name,
   not only the declared three, so the browser's own `root` name on the document
   element is covered and a plan that ever declares `root` collides with the UA
   rule on the same line;
3. each name must resolve to **exactly one** element on each route its entry
   lists (zero is a failure);
4. and to zero elements on the routes it does not.

Assertions 1, 3 and 4 exist because "no name appears twice" is trivially
satisfied by a page that declares no names at all — the vacuity shape 23-03 found
in its own work. Both are mutation-proven below.

**Check B — the opt-out, from the CSSOM.** Runs in two contexts, default and
`reduced_motion="reduce"`. Walks the author stylesheets for
`CSSViewTransitionRule` and asserts: exactly one exists; it declares
`navigation: auto`; its `parentRule` is a `CSSMediaRule`; that rule's
`conditionText` mentions `prefers-reduced-motion`; and **that condition string,
evaluated through `matchMedia`, is false under reduce and true by default.**

The last clause is the whole design. `matchMedia('(prefers-reduced-motion:
no-preference)')` on its own is a statement about Chromium, not about this app —
it is false in a reduce context whether the at-rule is wrapped, unwrapped or
absent. Reading the condition off the guarded rule's own parent is what makes an
unwrapped at-rule, an inverted `reduce` wrapper, a wrapper around some *other*
rule, and a wrapper narrowed so it never matches all four fail. Three of those
four were mutation-run.

## Acceptance criteria — every one run literally

**Task 1** — all seven ran and returned exactly what the plan predicted; nothing
was adjusted to fit. Pre-task values re-measured on the live tree first.

| Criterion | Expected | Got (pre-task) |
|---|---|---|
| `grep -c '@view-transition' style.css` | `1` | **`1`** (pre `0`) |
| `grep -v '^ *[*/]' \| grep -c 'prefers-reduced-motion: no-preference'` | `1` | **`1`** (pre `0`) |
| `grep -v '^ *[*/]' \| grep -c 'prefers-reduced-motion: reduce'` | `2`, unchanged | **`2`** (pre `2`) |
| `grep -cE '^\s*view-transition-name:' style.css` | `3` | **`3`** (pre `0`) |
| `grep -oE 'view-transition-name: *[a-z-]+' \| sort -u \| wc -l` | `3` | **`3`** — `skypane-picture`, `skypane-sidebar`, `skypane-title` |
| `grep 'view-transition-name' style.css \| grep -c 'nav'` | `0` | **`0`** |
| `grep -c 'startViewTransition' style.css static/*.js \| grep -v ':0' \| wc -l` | `0` | **`0`** |
| `test_companion_app.py`, only documented root-sandbox FAILs | — | **`271/273`**, both WR-11 read-only |
| wrapper-deletion mutation → exactly one failure naming it | — | **`270/273`**, message quoted below |
| `ruff check .` | clean | `All checks passed!` |

All seven greps were re-run **after** the comment correction in `7aee6dc` and
returned the same values.

**Task 2** — all five ran; four returned what the plan predicted and one did not.

| Criterion | Expected | Got |
|---|---|---|
| `test_browser_ux.py` at its new pin, re-derived BY RUNNING | 28 | **`browser-ux: 28/28 checks pass`** — run output, not arithmetic |
| nav-class mutation → exactly one additional failure naming the name and the route | — | **`27/28`**, message quoted below |
| unwrapped-at-rule mutation → exactly one additional failure naming the reduced-motion context | — | **`27/28`**, message quoted below |
| `scripts/run-all-tests.sh` no new failure | — | **exactly the 5-check root-sandbox baseline** |
| coverage ≥ 83 | — | **`TOTAL 6834 490 93%`** |
| `ruff check .` | clean | `All checks passed!` |

**The one criterion that did not evaluate as predicted** is the pin's arithmetic
gloss: the plan writes it as "28 (26 + 2 …)". 26 + 2 is indeed 28, so the number
is right — but the *mutation* criteria beside it predict "exactly one additional
failure", i.e. 27/28, whereas the plan's own Task-1 wording for the equivalent
mutation says "exactly one failure". Both mutations produced exactly one
**additional** failure over a 28/28 baseline. Recorded because the two phrasings
differ and only one of them is measurable.

## Mutation tests — four, all quoted, none vacuous

Every mutation was applied to `style.css` **after the implementation was staged**
(23-03's lesson, followed: `git add` first, plus an out-of-tree backup copy;
restoration was from the backup, never from `git checkout --`). `git diff` against
the committed state is empty after each. Baselines: `browser-ux` 28/28,
`companion-app` 271/273.

Every mutation was chosen to leave `test_companion_app.py`'s source-level motion
guard **GREEN at 271/273**, so each browser check is proven to do the work
unaided rather than merely going red alongside something else — the isolation
discipline quick task 260913-cz6's own note in this file established.

| # | Mutation | Harness result | Failure message (verbatim, after the check name) |
|---|---|---|---|
| M1 | the `@media` wrapper deleted, a bare at-rule left (Task 1's own criterion) | `companion-app` **270/273** | ``companion/static/style.css carries 0 live `@media (prefers-reduced-motion: no-preference)` wrapper(s), expected 1 (EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS). 23-04 is the one plan permitted to raise this to 1, for the view-transition at-rule the global reduce block genuinely cannot reach; any other change here needs its own argument first`` |
| M2 | `.dashboard-sidebar` "simplified" to the bare `nav` element selector | `browser-ux` **27/28**, `companion-app` green | ``the view-transition name 'skypane-sidebar' resolves to 2 elements on / (['nav.sidebar-nav', 'nav.tab-bar']) — names must be unique per rendered document or the browser drops the transition silently; if this is a navigation class, note that three navigation copies are in the DOM of every authenticated page at once`` (message since corrected — see Findings 1) |
| M3 | the at-rule moved OUT of the wrapper to the top level, **a `no-preference` wrapper left in the file** around an unrelated rule | `browser-ux` **27/28**, `companion-app` green | ``the view-transition at-rule sits at the top level of the stylesheet in a reduced_motion='reduce' context (parent rule None) rather than inside a media rule — so it is LIVE UNDER REDUCED MOTION: style.css's global `*, *::before, *::after` override matches ELEMENTS and never reaches the ::view-transition pseudo-element tree, which is why this wrapper is the opt-out and not a duplicate of it`` |
| M4 | the wrapper narrowed to `… and (min-width: 99999px)` so it can never match | `browser-ux` **27/28**, `companion-app` green | ``the media condition guarding the view-transition at-rule (`(prefers-reduced-motion: no-preference) and (min-width: 99999px)`) evaluates to False in a default (no-preference) context, expected True — under reduced motion the transition must never be set up, and under no-preference it must be, or the feature is wrapped into something nobody ever sees`` |
| M5 | the `.page-title` name declaration deleted outright | `browser-ux` **27/28**, `companion-app` green | ``the stylesheet served to / declares the view-transition names ['skypane-picture', 'skypane-sidebar'], but this file pins ['skypane-picture', 'skypane-sidebar', 'skypane-title'] (VIEW_TRANSITION_NAMES) — a name added, renamed or dropped in companion/static/style.css must be a deliberate edit here too, because every assertion below is empty for a name nobody declares`` |

**M3 and M4 exist specifically because of the vacuity instruction.** M3 is the
plan's mutation but strengthened: rather than deleting the wrapper (which also
reddens the source guard, so "both went red" would not prove this check did
anything), it moves the at-rule out while leaving a `no-preference` wrapper in
the file — the source guard cannot tell the difference and stays green, and only
the CSSOM check sees it. M4 and M5 are mine, added by asking the required
question — *what would a **wrong** implementation do?* — of each half of each
check:

- Check B's "false under reduce" half alone is satisfied by a wrapper that
  matches nothing at all, shipping a feature no visitor ever sees. **M4 proves
  the "true by default" half is load-bearing.**
- Check A's "no name resolves twice" half alone is satisfied by a stylesheet that
  declares no names at all — the precise vacuity shape 23-03 caught. **M5 proves
  the declared-set and exactly-one halves are load-bearing.**

**Were any of my own checks vacuous?** One draft was, and it never shipped: the
first design of Check B asserted `matchMedia('(prefers-reduced-motion:
no-preference)').matches` directly. That is a statement about the browser, not
about this app — it returns False in a reduce context whether the at-rule is
wrapped, unwrapped, or absent, so the mutation the plan mandates (M3) would have
**passed** it. It was replaced with the parentRule read before being written to
disk, and the reason is recorded in the check's own comment so it cannot be
"simplified" back. No shipped check was found vacuous after the fact.

## Findings the plan did not anticipate

**1. There are TWO navigation landmarks per authenticated document, not three —
the plan's and 23-RESEARCH.md's central structural fact is out of date.** The
plan's `<interfaces>` states "THREE nav renderings exist simultaneously in every
authenticated document — the sidebar, the `.mobile-nav` preferences panel and
the `.tab-bar`", and the research's Risk 3 says the same. **22-14 Task 2 REMOVED
`<nav class="mobile-nav__nav">` rather than emptying it** (`layout.py:1821`, its
own comment says so: "an empty navigation landmark would still be announced").
M2 measured the consequence: a bare `nav` selector resolves to **two** elements,
`nav.sidebar-nav` and `nav.tab-bar`, not three.

The hazard is unchanged in kind — two is still a collision, and the plan's
prescription (`.dashboard-sidebar`, never a shared class) is still exactly right
— so this changed no code. It changed two comments: `style.css`'s new note and
`test_browser_ux.py`'s, both of which had faithfully repeated "three". A comment
that describes a tree which does not exist is worse than no comment, so both were
corrected in place, in their own commit (`7aee6dc`), each stating that the brief
said three, that 22-14 is why it is two, and that it would be three again the
moment a panel-level landmark returns. The M2 failure message quoted above is the
pre-correction text; the shipped message now says "more than one navigation
landmark is in the DOM of every authenticated page at once, hidden from each
other only by a media query".

**2. The plan's own selector list disagrees with the research's, and the plan is
right.** `23-RESEARCH.md:669-671` proposes `.page-header__title` and
`.preview-frame img`; neither exists as written. The rendered classes are
`.page-title` (`layout.py:2837`, `app.py:1700`) and `.preview-frame__image`
(`home_page.py:444`). The plan's list was verified against the live tree before
editing and used unchanged.

**3. `.preview-frame__image`'s shared rule is a genuine trap, and the answer to
the `read_first` question is yes.** Its white-backing/hairline/radius
declarations live on a **four**-selector rule (`style.css:6353-6356`) shared with
`.now-showing__image`, `img.recent-flight__thumb` and `img.history-card__thumb`.
The last two render **once per row** — 36 rows on `/flights` from the harness
seed. A name placed on that shared rule would therefore collide dozens of times
on a page the picture is not even on. Each of the three names is consequently in
a rule of its own, and the reason is written into the stylesheet comment.
(`.now-showing__image` additionally has **no render site left** anywhere in the
app — `grep` across `companion/**.py` returns only the CSS and a test — so the
shared rule is already carrying one dead selector; noted for 23-11's sweep, not
touched here.)

**4. Chromium gives the document element a `view-transition-name` of `root` for
free**, from the UA stylesheet — so a per-route computed-value census sees four
names, not three. This is not noise: it means Check A's duplicate rule
automatically covers a future plan declaring `root` and colliding with the UA
rule. It also means the declared-set assertion had to be sourced from
`document.styleSheets` (author sheets only) rather than from the census, or the
two could never agree.

**5. `CSSViewTransitionRule` is retained in the CSSOM even inside a media block
that does not match.** Verified in both context modes this session: under
`reduced_motion="reduce"` the rule is still enumerable, with
`parentRule.conditionText` intact and `matchMedia(conditionText).matches ===
false`. This is what makes Check B possible at all — a browser that dropped
non-matching rules from the CSSOM would have forced the visual timing assertion
the plan (rightly) rejects.

**6. Task 1 deliberately ships no new source-level check, and the plan's own
criterion is what forces that.** "Deleting the `@media` wrapper produces exactly
one failure" cannot hold if a second check also asserts the nesting. The nesting
is asserted in Task 2 instead, where a browser can also distinguish "wrapped" from
"a wrapper exists somewhere in the file" — which M3 shows a source scan cannot.

## Deviations from Plan

**1. [Rule 1 — Bug] The "three nav copies" fact was corrected, not repeated.**
See Finding 1. Two comments, one commit, no behaviour change. Documenting a
structure that was dismantled two phases ago would have actively misled the next
reader — and this plan's whole thesis is that the next reader is the risk.

**2. [judgement] 23-01's constant comment was rewritten, not just its value.**
The plan says "move the guard's no-preference constant from zero to one, and
nothing else about the guard". The assertion bodies and every failure message are
byte-identical; only the constant's own preamble prose changed, from "it starts
at ZERO because the gap it exists for is not yet closed" to a record that 23-04
moved it and that the licence is now spent. The plan's *other* instruction — "Do
not leave a comment describing work that has now happened" — governs, and the two
would otherwise contradict each other. The guard's behaviour is unchanged, proven
by M1 reproducing 23-01's own recorded message verbatim.

**3. [judgement] Two mutations beyond the plan's two.** M4 and M5 were added by
applying the standing vacuity instruction to each half of each new check. Both
found the checks sound; neither changed code.

**5. [Rule 1 — Bug] Two commits were re-scoped after being made.** Staging
`test_browser_ux.py` before mutating (23-03's lesson) left it in the index, so the
follow-up `git add style.css && git commit` swept the whole of Task 2's new code
into the comment-correction commit, and the later Task 2 commit then carried only
a prose tweak. Both commit MESSAGES were accurate about intent and wrong about
contents — the opposite of atomic. Corrected with `git reset --mixed` back to
`193c04c` (index only; the working tree was byte-identical before and after,
proven by `md5sum -c`) and re-committed one file each. All four commits were
unpushed, this is a plain checkout and not a worktree, and no `--hard`, `clean`,
`stash` or `checkout --` was involved. **The lesson stacks on 23-03's rather than
replacing it: stage before mutating, but stage the file you are about to commit
and check `git show --name-only` afterwards — a pre-staged file is invisible to
`git add <one-file> && git commit`.**

**4. [scope] `REQUIREMENTS.md` was not touched at all.** The orchestrator's
instruction is not to tick CFG-32 or CFG-33 (23-11 closes both), and the plan's
`<files_owned>` names three files, none of them `REQUIREMENTS.md`. The CFG-33 row
therefore still reads "Planned — 23-04, closed by 23-11", which is now stale in
its first word. Left for 23-11 rather than edited from outside this plan's
ownership; logged to `deferred-items.md`.

## The no-JS floor, and what each browser actually sees

**A scripts-blocked visitor gets the cross-fade in full.** This is the one
enhancement in Phase 23 that survives the no-JS floor intact, and it is not an
argument from principle: the feature is a CSS at-rule parsed by the CSS engine
and honoured by the navigation machinery. No script participates at any point,
this plan added no `.js` file and touched none, `grep -c 'startViewTransition'`
across `style.css` and every static script is **0**, and no markup, class or
attribute changed anywhere — so there is no control that renders and does
nothing, because there is no control. `companion/static/` is not consulted for
this feature at runtime beyond the stylesheet itself.

**A Firefox visitor sees exactly today's behaviour: an instant navigation.**
How that was verified, rather than asserted:

- The support picture was re-read from the Web Platform Status API during
  `23-RESEARCH.md` (`cross-document-view-transitions`: Baseline **limited**,
  Chrome/Edge 126+, Safari/iOS 18.2+, Firefox WPT stable score 0.05 — i.e. not
  implemented), and its stated validity runs to 2026-11-13.
- The *degradation mechanism* is what matters and it was verified directly here:
  an unsupported engine does not parse `@view-transition` into any rule, so the
  at-rule contributes nothing; there is no feature detection, no
  `@supports` branch, no script fork and no alternative code path in the
  stylesheet for it to take. The three `view-transition-name` declarations are
  likewise unknown properties, dropped at parse time by CSS's own
  error-handling rules, and they affect no other property — they are not
  shorthands, they set no layout, paint or containment behaviour.
- Which is why **the mutation evidence doubles as the degradation evidence**:
  M1/M3/M4 each changed only whether the at-rule is set up, and in every one the
  app rendered and navigated normally in the harness browser, with all 26
  pre-existing browser checks (geometry, overflow, focus, disclosures, at 360/390/
  1280px in both languages) green throughout. Nothing in this app's layout,
  spacing, focus order or scroll behaviour depends on the at-rule existing.

Firefox itself is not installed in this container and was not launched; the human
sweep folded into 23-11 covers the visual confirmation on all three engines, and
this plan's `<verification>` says so.

## Interfaces re-verified before editing

Every line reference the plan supplied was re-measured on the live tree. Two had
drifted — as 23-02 found for its own plan — and one fact was wrong (Finding 1).

| Plan said | Live | Note |
|---|---|---|
| `style.css:311-317` global reduce block | **`:344-350`** | drifted by 33 lines (23-01's own additions); block itself exactly as described and left byte-identical |
| `layout.py:1944` `<aside class="dashboard-sidebar">` | **`:2100`** | drifted |
| `layout.py:1905-1977` three nav renderings | **two** (`:1440` `.sidebar-nav`, `:1621` `.tab-bar`) | Finding 1 |
| `layout.py:2681` `<h1 class="page-title">` | **`:2837`** | drifted; plus a second render site at `app.py:1700`, the login shell's brand mark — a page that renders no `page_header()`, so still one per document |
| `home_page.py:444` `.preview-frame__image` | **`:444`** | exact; still the only render site in the app |
| `style.css:527 / :1109 / :6262 / :6773` | **`:619 / :1201 / :6354 / :6874`** | all four drifted; every fact they point at was otherwise exactly as described |
| the nested at-rule parses and is retained in the CSSOM | **confirmed** | re-run this session in Chromium 151.0.7922.34, in both context modes |

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_browser_ux.py` | 26/26 | **28/28** | — |
| `companion/test_companion_app.py` | 271/273 | **271/273** | 2 × WR-11 read-only (documented) |
| `companion/test_config_page.py` | 233/233 | 233/233 | — |
| `companion/test_status_pages.py` | 272/273 | 272/273 | 1 × `anomaly_active()` (documented) |
| `companion/test_view_pages.py` | 146/146 | 146/146 | — |
| `companion/test_contrast_check.py` | 43/43 | 43/43 | — |
| `server/test_manual_resolutions.py` | 21/23 | 21/23 | 2 × WR-11 read-only (documented) |

`PYTHON=… bash scripts/run-all-tests.sh` → three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline** (4 × WR-11
read-only, 1 × `anomaly_active()`), verified by NAME, not by file count. No new
failure. Coverage `TOTAL 6834 490 93%`, ≥ 83. `ruff check .` clean. **No test
exception was added anywhere** — the suite still carries none.

`EXPECTED_CHECK_COUNT` re-derived by **running** the harness (`browser-ux: 28/28
checks pass`), never by arithmetic, and appended as a new last assignment
commented `23-04-PLAN.md Task 2` in this file's own format, including how each
new check was mutation-tested.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-10 | mitigate | The at-rule is nested in `@media (prefers-reduced-motion: no-preference)` and the nesting is asserted in a real browser **in both context modes**, from the at-rule's own parent rule rather than from a bare `matchMedia()` call. M3 (unwrapped, wrapper still in the file) and M4 (wrapper that never matches) both go red; the source-level guard sees neither. A vestibular-sensitive visitor never has the transition SET UP. |
| T-23-11 | accept | Unchanged and re-confirmed by inspection: transitions are same-origin by spec, the snapshot is in-process, never persisted, and shows the user the content they were already looking at. No app page links off-origin from a page carrying the at-rule; the stylesheet comment now says so rather than leaving it unstated. |
| T-23-12 | mitigate | Computed-value counting on all six authenticated routes, over every element and every name including the UA's own `root`, with the declared set pinned. M2 (a bare `nav` selector) and M5 (a dropped declaration) both go red while every source scan stays green. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. This plan adds no endpoint, no auth path, no file access
and no schema change; it adds nine CSS declarations and two harness checks.

## Known Stubs

None. The feature is complete and live on every navigation between the six
authenticated routes on a supporting browser; nothing is placeholdered, and
nothing waits on a later plan to be wired.

## Notes for later plans

- **Any plan touching navigation markup** must keep `.dashboard-sidebar`,
  `.page-title` and `.preview-frame__image` at one element per document.
  `VIEW_TRANSITION_NAMES` in `test_browser_ux.py` is the contract, and widening a
  named selector is a deliberate edit in that map, not a side effect.
- **`EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS` is frozen again at 1.** 23-01
  licensed exactly one move and this plan spent it. A plan wanting 2 must argue
  it in its own SUMMARY the way `.js .mobile-nav` argued the reduce side.
- **23-05/23-08/23-10** must not add an `animation: none` override on the
  `::view-transition-*` pseudo-elements as a "second belt". It is strictly
  weaker than the wrapper (it runs the transition at a zeroed duration instead of
  preventing setup) and is the dead-code-not-a-safety-net pattern.
- **23-11** owns: ticking CFG-32 and CFG-33 and refreshing their traceability
  rows (this plan deliberately touched neither — see deviation 4); the human
  sweep across Chrome, Safari and Firefox with the OS reduce-motion setting both
  ways; recording the view-transition names in SKILL.md's register; and, if it
  wants, the dead `.now-showing__image` selector noted in Finding 3.
- **Anyone quoting 23-RESEARCH.md's Risk 3 or this phase's plans on "three nav
  copies":** it is two, and has been since 22-14. See Finding 1.

## Self-Check: PASSED

- `companion/static/style.css`, `companion/test_companion_app.py` and
  `companion/test_browser_ux.py` all exist on disk and are the only three files
  this plan modified (`git show --name-only` on each of the four commits).
- All four commit hashes resolve in `git log`: `cea044f`, `193c04c`, `7aee6dc`,
  `0b7e4bd`. Every one is a single-file commit whose contents match its message,
  re-verified with `git show --name-only` after the re-scoping in deviation 5.
- `.planning/phases/23-companion-dynamism-live-updates-real-switches-motion-budge/23-04-SUMMARY.md` exists.
- The working tree is clean after every mutation: `git diff` on `style.css`
  against the committed state is empty.
