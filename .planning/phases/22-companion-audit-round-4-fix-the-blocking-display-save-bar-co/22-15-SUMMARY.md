---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 15
subsystem: ui
tags: [css, cascade, specificity, box-model, focus-visible, has-selector, exponential-backoff, fetch, i18n, forms, playwright]

requires:
  - phase: 22-10
    provides: "the T6 border allowance recorded in test_browser_ux.py, naming this plan as the one that deletes it"
  - phase: 22-14
    provides: "the bottom tab bar (whose More summary T3's chevron reaches), the stray-comment-terminator guard, and the single 320px dropdown max-height"
  - phase: 22-04
    provides: "the equal-specificity-plus-source-order precedent (.frame-strip__cell button) T2 reuses"
provides:
  - "T2: the destructive Disconnect control renders in its own grey secondary treatment again"
  - "T3: an explicit summary::before chevron, rotating on [open], restoring the disclosure marker display:flex killed"
  - "T4: the false sticky table-header claim removed outright"
  - "T6: a constant 1px border on every selectable surface, with selection carried by an inset accent ring"
  - "T15: a focus ring on a selected chip or card, and summary added to the global focus-visible floor"
  - "T13: freshness.js retries with bounded exponential backoff behind a neutral Paused/Reconnecting badge, with an in-flight guard and targeted swaps"
  - "T14: companion/static/submit-guard.js — one shared disable-on-submit guard for every form"
affects: [22-16, phase-23]

tech-stack:
  added: []
  patterns:
    - "box-shadow: inset as a zero-layout-cost selection ring, replacing a border-width change"
    - "box-shadow: inherit on an overlay pseudo-element, so a ring survives a full-bleed child image without duplicating any rule"
    - "a deferred (setTimeout 0) disable-on-submit, so the submitter's own name/value still reaches the form data set"
    - "Playwright's clock API to drive a 45s cadence and a 45s retry rung at zero wall-clock cost"

key-files:
  created:
    - companion/static/submit-guard.js
  modified:
    - companion/static/style.css
    - companion/static/freshness.js
    - companion/layout.py
    - companion/app.py
    - companion/i18n_fr/common.py
    - companion/test_config_page.py
    - companion/test_status_pages.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py
    - companion/test_view_pages.py

key-decisions:
  - "T3's chevron DOES reach the tab bar's More summary, but absolutely positioned out of flow, so a 6px marker cannot narrow a 78x56px cell's centred icon-and-label stack — and with an INVERTED rotation, because that sheet opens upward"
  - "T6 converts every 2px selected-state border in the file, including both dashed saved-state markers: a 2px dashed ring against 1px siblings is the same layout shift wearing a different dash pattern"
  - "T6's ring is drawn a second time on a .theme-chip::before overlay carrying box-shadow: inherit, because an inset shadow paints beneath the chip's full-bleed preview image"
  - "T13's Paused state means the tab is hidden — the only deliberate idling this loop has left since D-18 retired the Pause control"
  - "T13's retry ladder starts AT the normal 45s cadence, never below it, and the interval is left running as a heartbeat rather than torn down, so a recovered page is never left with no schedule"
  - "T14 disables from a zero-delay timer, not inline: layout.py's theme and language pickers are named submit buttons whose name/value IS the request, and an inline disable would have made every theme and language switch a silent no-op"
  - "22-10's T6 border allowance in test_browser_ux.py is DELETED — outer widths and border totals now assert plain equality, confirmed in a real browser"

patterns-established:
  - "A retargeted check states, in place, what its own premise used to be and why the replacement is strictly narrower"
  - "A new script's route is proven by a real HTTP GET, not only by its registration — a registration whose route 404s is a guard that does not exist"

requirements-completed: []

duration: ~95min
completed: 2026-09-13
---

# Phase 22 Plan 15: CSS/JS defects (T2, T3, T4, T6, T13, T14, T15) Summary

**Seven defects that were visible only to someone reading the source are now visible to a test: a destructive button wearing the primary accent, every disclosure with no marker, a sticky header that could never stick, a 2px selection layout shift, an invisible focus state on the one card that matters, a refresh loop that stopped dead and said nothing, and every form in the app accepting a repeat POST.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3/3
- **Files modified:** 10 modified, 1 created

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `0de6af1` | fix(22-15): five stylesheet defects a reader could see and no test could |
| 2 | `733cfec` | fix(22-15): a refresh that cannot reach the server says so, and keeps trying |
| 3 | `528082d` | feat(22-15): one disable-on-submit guard for every form, not one |

## What landed

### T2 — Disconnect is secondary again

`.calendar-disconnect-btn` was `(0,1,0)`; `button[type="submit"]` is `(0,1,1)`. The
primary accent fill won outright, so the one **destructive** action on the page
rendered as the page's primary CTA and the whole grey rule block was dead code.
Fixed by element-qualifying the selector to `button.calendar-disconnect-btn`
`(0,1,1)` and relying on source order — the mechanism `.logout-form button`,
`.dirty-bar__cancel`, `.frame-strip__cell button` and
`.config-form input[name="wake_interval_s"]` already use. The hover/focus rule
was raised the same way to `(0,2,1)`, matching `button[type="submit"]:hover`.
`box-shadow: none` was added for the same reason its three siblings carry it.

**Was any other control relying on the accidental fill?** No. The class has three
consumers: Config's Disconnect (`type="submit"` — the only one the bug could
reach), Airlines' per-card Replace and History's picture control, both
`type="button"` and therefore always grey. That is why the defect was invisible on
two of three call sites. `.airline-card .calendar-disconnect-btn` declares
display/width/margin only and is unaffected.

The stylesheet header comment's claim that "06.6.4.1-04 already removed the
Disconnect button's accent fill as a specificity BUG fix" was **stale** — the
fill was still live. Left as-is (it is 22-16's territory), but flagged below.

### T3 — every disclosure has a marker again

`summary { display: flex }` generates no `::marker` at all, so both marker rules
beneath it had been dead since they were written and every `<details>` in the app
had no open/closed indicator. Replaced with a pure-geometry `summary::before`
chevron (two 2px borders on an empty box, rotated) and a
`details[open] > summary::before` rotation. Deliberately not a text glyph —
a `content` string is the hard-coded-English hazard T10 had to unpick.

**The tab bar decision, made deliberately.** `.tab-bar__link` is also the More
`<summary>`, so the global rule reaches it — and §3.1 and §5 contract 3 both
require that it does. In flow it would be a flex item beside `.tab-bar__pill`
inside a 78×56px cell, visibly narrowing the fifth tab's icon-and-label stack
against the other four. It is therefore **absolutely positioned** against
`.tab-bar__more`'s already-declared `position: relative`, costing the layout
nothing, and its rotation is **inverted** (up when closed, down when open)
because that sheet opens upward and the global convention would point the marker
away from the panel it controls. `.mobile-nav__link`'s 44px floor was not touched.

No per-rule reduced-motion block was added; the block count is unchanged at 2.

### T4 — the false sticky claim removed

`.data-table-wrap th` is deleted, rule and all. The wrapper declares
`overflow-x: auto` with no height, so there was never a vertical scrollport to
stick inside; the header always scrolled away with its table. Giving the wrapper
a `max-height` would have put a second nested vertical scrollbar into four tables
as a rider on a defect report that asked for nothing of the sort. Sticky day
headers are Phase 23's D7.

Its `background: var(--color-canvas)` went with it, which makes quick task
260901-uzi's **finding 5 candidate (b) moot, not deferred** — there is no stuck
header for any token to paint. The deferral paragraph two rules above was
rewritten in place to say so.

### T6 — selection no longer shifts layout

`box-sizing: border-box` keeps an element's *content* box stable when its border
thickens; it does **not** keep the outer box stable when the width comes from
distributed free space. `.runway-card` is `flex: 1 1 0`, so the saved card
measured **98.67px against its siblings' 96.66/96.67px at 390px**. `.theme-chip`
is a fixed 160px, so it instead ate 1px per side and its preview band and body
rendered 2px narrower than its neighbours'. `.frame-colours__row` is in a column
flex list, so a checked row was 2px *taller* and nudged every row below it.

Every selected-state border is now a constant 1px that only recolours, with the
2px signal moved to `box-shadow: inset 0 0 0 2px var(--color-accent)`, which
occupies no layout space at all. **Eight rules converted**, including both dashed
saved-state markers (2px dashed against 1px siblings is the same defect wearing a
different dash pattern) — each of which gained an explicit `box-shadow: none`,
because a `border` shorthand cannot reach a box-shadow.

**Both `:has(input:checked):hover` positive-restore rules were reconciled in the
same commit.** They declared `box-shadow: none`, whose only job was to suppress
the hover elevation. Once selection *is* a box-shadow, `none` stops being a
suppression and becomes an erasure — the ring would have vanished the instant a
pointer crossed a selected card. They restate the ring instead, which suppresses
the elevation just as completely (box-shadow is one property).

**One chip-specific addition:** an inset shadow paints beneath its element's
children, and `.theme-chip__preview` is a full-bleed `width: 100%` image over the
chip's top 56px — the ring would have been hidden along the whole preview band.
`.theme-chip::before` is one unconditional overlay carrying `box-shadow: inherit`,
so it redraws whatever the chip itself computes, above the image, in every state,
with no rule duplicated and no possibility of drift. The chip's own
`overflow: hidden` clips the overlay, which is what stops an inherited *outer*
hover shadow painting a second smaller copy of itself.

### T15 — a selected card can be seen to have focus

`.runway-card:has(input:focus-visible), .theme-chip:has(input:focus-visible)`
takes the **global focus-visible floor's own values** (`outline: 2px solid
var(--color-accent); outline-offset: 2px`), inside the **single existing**
`@supports selector(:has(*))` block — the count is still exactly 1. An `outline`
rather than a second box-shadow, deliberately, so focus and T6's selection ring
cannot collide on one property. `summary` joined the global focus-visible
selector list.

### T13 — the refresh loop says when it cannot reach the server

Any non-OK response (including the opaque redirect an expired session produces)
and any network error called `stopLoop()`, and the loop never ran again for the
life of the page. A frozen Health page and a live one looked identical.

- **Bounded exponential backoff.** Starts **at** the normal 45s cadence and
  doubles to a 10-minute ceiling, so a failing server sees a strictly
  *decreasing* request rate (T-22-56's mitigation). The interval is deliberately
  left running as a heartbeat and its tick stands down while a retry is pending,
  so there is no state in which a recovered page has no schedule at all.
- **A visible NEUTRAL badge.** `Reconnecting…` while retrying, `Paused` while the
  tab is hidden. `.banner__pill` + `.dot--off`, no warn token anywhere — a
  browser that lost its connection is not a device fault. Exactly one pill is
  ever visible: `revealPill()` stands down while a state is showing.
- **First success resets the backoff** and clears the badge.
- **In-flight guard.** A slow response plus a visibilitychange catch-up could put
  two fetches in the air, and the *last* to resolve won the swap — a stale
  response could overwrite a fresher one.
- **Targeted swaps.** A region whose content did not change (`isEqualNode`, never
  a serialized-markup comparison — that stays banned in this file) and a region
  containing the focused element are both left alone.
- The interaction-skip guard, the visibility gating and the 45s cadence are
  untouched, and pinned as untouched.

### T14 — one disable-on-submit guard for every form

`companion/static/submit-guard.js`: one ES5-safe IIFE, one delegated
document-level `submit` listener, one registration on the authenticated shell.
No build step, no vendored library, no inline script, no CSP change.

The disable runs from a **zero-delay timer**, and that is the correctness
argument rather than defensive padding: a submit button's own name/value joins
the form data set *after* the listeners return, and `layout.py`'s theme and
language pickers are segmented controls built from
`<button type="submit" name="ui_theme"/"ui_lang">` — the button's name/value *is*
the request. An inline disable would have made every theme and language switch a
silent no-op. It also stands down if another listener cancelled the submission.

No label change in either language (that is D3, Phase 23); the appearance is the
existing `button:disabled` rule, and the check pins that there is still exactly
one of them, still ordered after `button:active`. The poll button is skipped via
poll-cooldown.js's own `data-submit-pending` handshake, so it is neither
double-disabled nor re-enabled. A bfcache restore re-enables only controls this
file disabled.

## Deviations from plan

### 1. `[Rule 3 — Blocking]` `companion/app.py` was edited, which `<files_owned>` excludes

- **Found during:** Task 3.
- **Issue:** the plan requires `companion/static/submit-guard.js` as an artifact
  and "one registration on the authenticated shell" in `layout.py`. But every
  static script in this app is reachable only through an **explicit** route in
  `app.py` (route constant, path constant, thin `_serve_*` delegate, `do_GET`
  dispatch line — twelve times over). There is no catch-all `/static/` handler.
  Registering in `layout.py` alone would have shipped a `<script src>` pointing
  at a 404: a dead guard, a per-page cost, and an acceptance criterion (the
  browser double-click check) that could not pass.
- **Fix:** four mechanical additions to `app.py`, each the thirteenth instance of
  a pattern already repeated verbatim twelve times, changing no behaviour of its
  own. No architectural change, so Rule 3 rather than Rule 4.
- **Files modified:** `companion/app.py` (+18 lines, all boilerplate).
- **Commit:** `528082d`.
- **For the record:** `<files_owned>`'s stated rationale — "a CSS defect that
  cannot be fixed in CSS is a finding, not a licence" — is aimed at page-module
  markup. This is not a markup change; it is the plumbing without which the
  plan's own named artifact cannot run. Flagging it explicitly rather than
  absorbing it.

### 2. Two of Task 1's edits landed in files listed under other tasks

- `companion/test_browser_ux.py` (Task 2/3's file list) was edited in Task 1's
  commit, because deleting 22-10's T6 border allowance belongs with T6.
- `companion/test_companion_app.py` (Task 3's file list) was edited in Task 2's
  commit, because `<body>` gaining the two refresh-state attributes broke that
  file's tab-bar body-marker literal in Task 2, not Task 3.
- Every file involved is inside the plan's own `files_modified` set; only the
  task boundary moved.

### 3. `companion/test_view_pages.py` retargeted — a file this plan does not list

T2's new `button.calendar-disconnect-btn` selector broke an anchored regex
(`^\.calendar-disconnect-btn \{`) asserting "exactly one base rule block".
Retargeted **strictly narrower**: it now pins the element-qualified form (which
the bare class never had) *and* additionally forbids the bare class returning.
No test exception added; the check got stronger.

## Acceptance criteria — every one run literally

### Task 1

| Criterion | Result |
|---|---|
| `grep -c '@supports selector(:has(\*)) {' style.css` = `1` | **1** ✅ |
| `grep -c ':where(button\[type="submit"\])' style.css` = `0` | **0** ✅ (see note below) |
| `grep -c "position: *sticky"` = pre-value − declarations removed | pre **4**, post **3**, delta **−1** ✅ (see note) |
| non-comment `prefers-reduced-motion` count unchanged, pre = `2` | pre **2**, post **2** ✅ |
| selected-state rules declare one border width + an inset ring | ✅ — `grep -c "border: 2px"` is **0** file-wide, pinned by a new check |
| `:has(input:checked):hover` no longer clears the shadow | ✅ both rules, pinned in both directions |
| `summary` appears in the focus-visible selector list | ✅ |
| both harnesses M/M at their new pins | config-page **233/233**, status-pages **267/268** (documented `anomaly_active()`) ✅ |
| `ruff check .` clean | ✅ |

**Two criteria were tripped by my own new prose and fixed by rewording the prose,
never the criterion:**

1. The T2 comment originally wrote the banned construct out verbatim to say it
   was banned, which made `grep -c ':where(button[type="submit"])'` return **1**.
   Reworded to "a `:where()` wrapper around the primary rule's own selector".
2. The T4 comment originally wrote `position: sticky` in prose, which held the
   sticky line count at **4** after the declaration was removed. Reworded to
   "Sticky positioning resolves against…".

Both were caught by running the criteria, not by inspection.

### Task 2

| Criterion | Result |
|---|---|
| `grep -c "stopLoop" freshness.js` = `0`, **or** definition + deliberate teardowns only | **7 lines**: 4 in comments, and in code exactly **3** — the definition plus **two** deliberate background-tab teardowns (`tick()`'s `document.hidden` guard, the `visibilitychange` hidden branch). **Neither failure path calls it.** A new check pins the code count at exactly 3. |
| the pill's markup carries the neutral dot and no warn token | ✅ `.dot--off`; the badge builder's own body is scanned for `warn`/`error`/`danger`/`alert`/`status-` |
| `grep -c "=>" freshness.js` = `0` | **0** ✅ |
| the browser check shows the pill appearing on failure and clearing on recovery | ✅ — real fetch failure, real retry, real recovery |
| `companion/test_i18n.py` exits 0 | ✅ 24/24 |
| `ruff check .` clean | ✅ |

### Task 3

| Criterion | Result |
|---|---|
| `grep -rc "Saving\|Enregistrement…" submit-guard.js` = `0` | **0** ✅ (see note) |
| `grep -c "=>" submit-guard.js` = `0` | **0** ✅ |
| browser check: repeat click → no second request; save bar and strip switches still work | ✅ all three in one check |
| `grep -c "unsafe-inline\|nonce-" app.py` unchanged | **3 → 3** ✅ |
| `run-all-tests.sh`: no new failure, coverage ≥ 83 | 3 failing harnesses = the documented baseline exactly; coverage **93%** ✅ |
| `ruff check .` clean | ✅ |

**One more self-trip, same class:** the guard's header comment originally quoted
`"Saving…"` while saying the label must not change, and separately used backticks
for code quoting, which its own ES5 template-literal ban forbids. Both reworded;
all backticks removed from the file.

## Test exceptions added or removed

**REMOVED — 22-10's T6 border allowance in `companion/test_browser_ux.py`, as
instructed.** It asserted `borders in ([2.0], [2.0, 4.0])` and deliberately did
*not* compare outer widths, because the saved card carried a 2px border against
its siblings' 1px. It now asserts:

- border-excluded widths equal within 1px (unchanged),
- **outer** widths equal within 1px (new),
- border totals **exactly `[2.0]`**, no second value permitted (narrowed from a
  two-value allowance).

Verified in a real browser: `browser-ux` passes 22/22 with the tightened
assertions, so the three cards genuinely measure equal now.

**No exception was added anywhere in this plan.** Six pre-existing checks were
retargeted in place, each strictly narrower and each stating its old premise:

| File | Check | Retarget |
|---|---|---|
| `test_config_page.py` | selected-card wash | `border: 2px solid` → constant border + inset ring, **plus** a new clause forbidding `border: 2px` |
| `test_config_page.py` | `:has()` gate (×2 border clauses) | same, via a shared helper |
| `test_config_page.py` | `:has()` gate (×2 hover clauses) | `box-shadow: none` required → **forbidden**, ring required instead |
| `test_view_pages.py` | one `.calendar-disconnect-btn` base rule | bare class → element-qualified, **plus** a clause forbidding the bare class |
| `test_companion_app.py` | tab-bar `<body>` marker | exact `<body class="...">` literal → class still **first** on the tag, **plus** both T13 attributes on both shells |
| `test_companion_app.py` | eleven deferred scripts | → twelve, **plus** a new clause that the login shell does **not** get the guard |

## Harness pins — old and new

| Harness | Before | After | New checks |
|---|---|---|---|
| `test_config_page.py` | 232 | **233** | +1 (T2/T6/T15 structural scan) |
| `test_status_pages.py` | 266 | **268** | +2 (T3/T4; T13 server side) |
| `test_companion_app.py` | 271 | **272** | +1 (T14 route over real HTTP) |
| `test_browser_ux.py` | 20 | **22** | +2 (T13 pill; T14 double click) |
| `test_view_pages.py` | 143 | 143 | 0 (one retarget) |
| `test_contrast_check.py` | 43 | 43 | 0 |
| `test_i18n.py` | 24 | 24 | 0 |

Every pin was re-derived by **running** the harness and reading its own printed
count, never by arithmetic. Each new assignment carries a comment citing
`22-15-PLAN.md` and its task.

Sandbox baseline is unchanged at exactly **5 failing checks**:
`manual_resolutions` 21/23 (2 × WR-11), `companion-app` 270/272 (2 × WR-11),
`status-pages` 267/268 (1 × `anomaly_active()`). All pass in CI.

## Requirements

**CFG-31 NOT ticked.** `grep -l "CFG-31" *-PLAN.md` returns 22-01, 22-04, 22-10,
22-12, 22-14, 22-15 **and 22-16** — the closing design-system sweep still owes the
whole of D-08's "`sketch-findings-skypane` is the authority and must be updated in
step" half, which is the requirement's own framing. After this plan **T1–T15 are
all landed** (T1/T8 in 22-01, T9 in 22-04, T5/T7/T11 in 22-14, T10/T12 in 22-10,
T2/T3/T4/T6/T13/T14/T15 here); T16 is optional and none was taken. `REQUIREMENTS.md`'s
traceability row is updated to record that; the checkbox is for 22-16.

**CFG-28 remains un-ticked** and untouched — `health_page.py:3628` is 22-16's.
**CFG-29 and CFG-30 are not regressed:** `test_i18n.py` passes 24/24 with two new
CATALOG entries, and no page module was edited.

## Notes for 22-16's closing design-system sweep

Everything below is a §4 row this plan either satisfies, changes, or newly
requires. Read all of it before starting.

1. **T4 → `references/data-density.md`.** Mark the sticky-header entry
   **SUPERSEDED**. The reason is not "we chose not to" — it is that
   `.data-table-wrap` has no height, so the claim could never engage. **Also
   retire quick task 260901-uzi's finding 5 candidate (b)** (the
   `--color-canvas`-vs-card-surface question for the stuck header's background):
   it is **moot**, not deferred, because the background declaration went with the
   rule. The stylesheet comment two rules above already says so; the skill should
   agree.

2. **T6 → `references/control-density.md`.** The selected-card treatment's border
   width is now **constant at 1px** and the 2px accent signal is
   `box-shadow: inset 0 0 0 2px`. Record that *both* `:has(input:checked):hover`
   positive-restore rules had to move with it, or hovering a selected card erases
   its ring. The 12% wash and the check glyph are unchanged. **Two things the §4
   row does not yet mention and should:** (a) the conversion also covers the two
   **dashed saved-state markers** and `input:checked + .frame-colours__row`, so
   it is *three* selectable surfaces, not two; (b) `.theme-chip` additionally
   carries a `::before` overlay with `box-shadow: inherit`, because an inset ring
   paints beneath its full-bleed preview image — worth recording as the general
   rule for any future card with an edge-to-edge child.

3. **T3 → the accent-reservation list and `references/accessibility-contrast.md`.**
   The `<summary>` disclosure-marker entry is **restored, not added** — the list
   does not change. Record that the marker is now an explicit `::before` because
   `display: flex` suppresses `::marker`, and that the rotation needs **no**
   per-rule reduced-motion block.

4. **T3 → `references/mobile-navigation.md` (the tab bar section).** The More
   summary's chevron is **out of flow** (absolute, against `.tab-bar__more`'s own
   `position: relative`) and its rotation is **inverted** against the global
   convention, because that sheet opens upward. Both are deliberate and both
   should be recorded, or the next editor will "fix" them back.

5. **T2 → the `style.css` header comment (C2's row).** That comment currently
   claims "06.6.4.1-04 already removed the Disconnect button's accent fill as a
   specificity BUG fix". **That claim was false until this plan.** The fill was
   still live; the rule was `(0,1,0)` against `(0,1,1)`. The arithmetic sentence
   that follows it ("this task's own removal is the first of the two genuine
   losses") is therefore built on a wrong premise. Correct it in place. I did not
   touch it because the header comment is C2's row and 22-16's to own.

6. **T13/X2/X8 → the `.dot--off` widening row.** All **three** consumers now
   exist in code: the frame's **held** state (`layout.py`'s
   `_FRAME_DOT_CLASS_BY_STATE`), Health's **"Only one saw it"**
   (`_STATUS_DOT_CLASSES["off"]`), and **T13's paused/reconnecting badge**, built
   client-side by `freshness.js`. Record all three and the rule they share.

7. **A fourth `[hidden]`-vs-`display` consumer exists now.** The class had three
   (`.dirty-bar[hidden]`, `.refresh-pill[hidden]`, `.login-reveal[hidden]`); it
   now has `.banner__pill[hidden]` too. Note the deliberate divergence:
   `.refresh-pill[hidden]` hides by `visibility` (it is absolutely positioned and
   must reserve nothing), the new one by `display` (it is an in-flow inline child
   of the freshness line).

8. **T15 → `references/accessibility-contrast.md` §5 contracts 1 and 2** are both
   satisfied exactly as written: the global floor's own values, inside the one
   feature-query block, and `summary` in the global rule.

9. **The `:has()` block count is still exactly ONE.** `settings-page-patterns.md:47`
   still says "exactly two" — that correction is a **required** §4 row and is
   still owed. Its single surviving block is the live-selection-state one, which
   this plan extended (never duplicated) with T6's and T15's rules.

10. **The authenticated shell now emits TWELVE deferred scripts, not eleven.**
    `submit-guard.js` is the thirteenth static script and the twelfth on the
    shell; `login-card.js` remains login-only, and the guard is deliberately
    **not** on the login shell. If any skill text states the script count, it
    needs updating.

11. **`.calendar-disconnect-btn`'s base rule is now `button.calendar-disconnect-btn`.**
    The X7 §4 row records its second consumer; add that the selector is
    element-qualified and *why* (equal specificity to `button[type="submit"]`,
    beaten by source order), because a future reader simplifying it back to the
    bare class would silently restore T2.

12. **T14 → any "what to avoid" entry on disable-on-submit.** Record that the
    disable must be **deferred**, not inline: the submitter's name/value joins the
    form data set after the listeners return, and the theme and language pickers
    are named submit buttons whose name/value is the entire request.

13. **T16: none taken.** No debt item rode along. No rule this plan edited
    contained one that was safely separable, and the plan forbids opening a
    stylesheet-wide refactor. The file's 2px-border literals are now all gone,
    which is a small incidental reduction in off-scale literals.

14. **Regression floor for 22-16's own closing check:** the browser harness ran
    (22/22, not skipped) in this sandbox, and coverage is **93%**.

## Self-Check: PASSED

- `companion/static/submit-guard.js` — FOUND
- `companion/static/freshness.js` — FOUND
- `companion/static/style.css` — FOUND
- `.planning/phases/22-.../22-15-SUMMARY.md` — FOUND
- Commit `0de6af1` — FOUND
- Commit `733cfec` — FOUND
- Commit `528082d` — FOUND
