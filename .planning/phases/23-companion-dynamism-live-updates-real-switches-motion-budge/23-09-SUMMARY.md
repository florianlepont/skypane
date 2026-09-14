---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 09
subsystem: ui
tags: [css, keyframes, motion, accessibility, live-region, progressive-enhancement, no-js-floor, i18n, form-submission, playwright, harness]

requires:
  - phase: 23-01
    provides: "--motion-fast, and the guard that fails a bare animation duration, a duplicate keyframes name and a moved reduce-block count — every one of which this plan's fourth block and its one declaration pass unaided"
  - phase: 23-02
    provides: "_no_js_page(viewport=...) and VIEWPORT_MIN_SUPPORTED — B1's floor is re-asserted through both"
  - phase: 23-08
    provides: ".is-fading-in named as the rule 'the next thing that changes under the reader' should spend, and the write-text-then-class ordering for an animated count; this plan is that next thing"
  - phase: 22-15
    provides: "T14's deliberate deferral of the in-flight label to D3, and submit-guard.js's own name/value-after-the-listeners analysis, which this plan had to redo for a relabel"
  - phase: 22-01
    provides: "B1/D-01's two-marker fallback-hide gate, untouched here and re-asserted in a scripts-blocked browser at 360px"
provides:
  - "@keyframes skypane-bar-arrive + the one animation declaration on .dirty-bar: the save bar's entrance, transform and opacity only, at var(--motion-fast), with no fill mode"
  - "dirty-state.js setCountText(): the count's ONE write site, gated on the sentence genuinely differing, spending .is-fading-in on the element and never tweening the number"
  - "config_page.DIRTY_SAVING_TEXT + data-dirty-saving: the bar's sixth translated word, with its byte-identical English fallback in dirty-state.js"
  - "dirty-state.js relabelSubmitter(): the in-flight label, safe by the control's own shape (a <button> with no name contributes no form-data entry), with a bfcache restore"
  - "the first executable guard the .dirty-bar[hidden] override has ever had, in two places: a source clause and a real computed-display assertion on both a scripted and a scripts-blocked page"
  - "test_browser_ux.py +3 checks, and T14's own no-label clause retargeted on its due date"
affects: [23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "an entrance built as an ANIMATION rather than a transition out of display:none, because the transition form needs an @starting-style entry and would therefore move for some visitors and silently do nothing for the rest"
    - "a relabel made safe by a property of the CONTROL (a <button> with no name contributes no entry to the form data set) rather than by the timing dance a disable needs — the same question submit-guard.js asks, with a different and stronger answer"
    - "a live region's announcements measured with a MutationObserver installed BEFORE the first change, so what is asserted is the sequence a screen reader would hear rather than the end state"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/static/submit-guard.js
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_browser_ux.py

key-decisions:
  - "The entrance is an ANIMATION, not a transition with an @starting-style entry. 23-08 used the transition form for the Flights detail row and was right to; it is wrong here. @starting-style is newer than this component's audience, so a transition would animate for some visitors and do nothing for the rest — the exact failure shape 23-01's interpolate-size ban exists to stop, and not a smaller one because the property is Baseline-newer rather than Chromium-only. An animation runs everywhere, and an element at display:none runs none of it, so the scripts-blocked reader is reached by nothing either way."
  - "No fill mode, deliberately and asserted. An animation that holds its final frame keeps overriding the element's own computed style, which is how a bar gets stranded — and a stranded save bar is a blocked save, which this app has shipped once. With no fill the element is handed back to its own style the instant the animation ends."
  - "The count animates its ELEMENT and the text is written exactly once per genuinely different sentence. Four write sites became one, gated. This is not only a motion decision: the bar is role=\"status\" and updateBar() runs on every keystroke, so the previous code re-wrote identical text into a live region repeatedly. The animation forced the question and the answer improved the announcement."
  - "There is NO 'Saved ✓' on the bar and its absence is a decision recorded in config_page.py itself. The save is a full form POST that replaces the document: the bar showing the in-flight word does not exist when the save completes. Carrying a flag across that navigation means browser storage, and this app holds none. The completed state is app.py's existing FLASH_KEY_SAVED confirmation, on the page the browser lands on — asserted in both languages."
  - "The relabel is safe by the CONTROL'S SHAPE, not by timing. submit-guard.js defers its disable because a submitter's name/value joins the form data set after the listeners return. Both Save controls are <button type=\"submit\"> with NO name, so they contribute no entry at all and a label cannot displace anything — re-checked on the live control, so a later plan that names either Save makes the relabel stand down rather than quietly rewrite a payload. <input type=\"submit\"> is excluded by the same clause for the sharper reason: its label IS its submitted value."
  - "The order against submit-guard.js is fixed, not lucky: this listener is on the FORM and that file's is on document, so the event reaches this one first and synchronously, while that one only queues a zero-delay task. Relabel, then disable, every time, by propagation order — and neither writes the other's property."
  - "The relabel is undone on a bfcache restore, mirroring submit-guard.js's own pageshow handler. Without it a back-navigation lands on a Save button still reading the in-flight word for a request that finished a navigation ago."
  - "The French word goes in companion/i18n_fr/display.py, NOT common.py as the plan's read_first says. display.py is where the bar's other six strings live, and the package raises ValueError on a duplicate key across sibling modules, so there is exactly one correct home."
  - "T14's browser clause asserting the label carries no progress word was RETARGETED rather than deleted. Its own failure message named 'D3, Phase 23' as the plan that would change it; this is that plan, so asserted literally it would have been testing for the absence of the feature the phase ships. The property it was about — the shared guard writes no label — keeps its home in test_companion_app.py's served-body check, which fails submit-guard.js for containing the word at all."

patterns-established:
  - "When an animation forces you to ask 'did this value actually change?', answer it for the ANNOUNCEMENT too: a live region that is rewritten with identical text says the same thing twice, and the gate that stops a pointless animation is the same gate that stops a pointless announcement."
  - "A payload-equality assertion needs a control proving the thing that could have changed it really ran; two identical bodies are also what a script that does nothing produces."

requirements-completed: []

duration: ~2h15m
completed: 2026-09-13
---

# Phase 23 Plan 09: D3's save bar Summary

**The app's most-iterated component — four design iterations, a P0, a z-index
reversal and a clearance measured at both breakpoints — now slides into place
instead of appearing, moves its count only when the number genuinely changes and
announces each change exactly once, and tells you it is saving in your own
language without moving a byte of what it posts; and the fallback Save that B1
killed is proven visible, boxed and saving in a scripts-blocked browser at 360 px
in both languages.**

## Performance

- **Duration:** ~2 h 15 m
- **Tasks:** 3/3
- **Files:** 0 created, 8 modified
- **Harness runtime:** `test_browser_ux.py` 138.2 s → 144.0 s (three new checks,
  one of which drives six POSTs across two languages)

## Commits, in order

| # | Commit | Message |
|---|---|---|
| 1 (RED) | `1273a66` | test(23-09): pin the save bar's entrance and a count that announces once, before either exists |
| 2 (GREEN) | `26fd99a` | **feat(23-09): the save bar arrives, and its count moves only when the number does** |
| 3 (RED) | `99ae977` | test(23-09): pin the in-flight word and what makes relabelling a submitter safe, before it exists |
| 4 (GREEN) | `6dea46a` | **feat(23-09): the Save control says what it is doing, and the app still holds no client state** |
| 5 | `9578d57` | test(23-09): a browser proves the bar arrives, the count announces once, and the fallback still saves |

TDD gate sequence present and in order for Tasks 1 and 2 (`test(...)` then
`feat(...)`); Task 3 is test-only and has one `test(...)` commit. Both RED
commits were proven red **by running**: commit 1 reports config-page **237/238**
and companion-app **288/291**; commit 3 reports config-page **238/239**.
`git show --name-only` was run after every commit and each carries exactly the
files its message claims. No `git stash`, no `git clean`, no blanket
`git checkout --` over unstaged work.

---

## The before state, recorded before anything moved

A motion change to this component is a regression risk before it is a feature, so
the whole browser harness was run and captured to disk **before the first edit**:
**47/47**, with every save-bar check green by name —

```
PASS Display: a theme chip, a runway card and a quiet-hours time field each reveal the save bar…
PASS the fallback Save button stays reachable and functional until the bar has actually been shown once, then hides (D-01…)
PASS Cancel restores the form value AND the live theme preview (T8), and a subsequent edit re-arms the leave-guard (T1)
PASS activating a Frame strip switch with unsaved Display edits present applies over fetch WITHOUT navigating, leaves the leave-guard ARMED…
PASS at 390x844 on Display … the save bar and the bottom tab bar … do not intersect … the save bar wins on stacking order at the ONE value it declares at both breakpoints
PASS a second click on the save bar's Save produces NO second POST…
PASS a Display page whose save bar reports unsaved edits issues ZERO requests…
PASS with scripts blocked at 360px, in BOTH languages, a Display setting still saves through the fallback Save and persists to disk…
```

**After this plan every one of them is green again**, at **50/50**. One of them —
the T14 double-submit check — was retargeted in place, on its own stated due
date; see below.

---

## Task 1 — the bar arrives, and the count moves only when the number does

### The entrance, and the decision that is actually interesting

`@keyframes skypane-bar-arrive` is the app's **fourth** keyframes block, argued
in the stylesheet the way the second (23-06) and third (23-08) were. The three
existing blocks are an opacity cycle, an opacity ramp and a background wash —
**none of them moves anything**, and D3 asks for a bar that arrives rather than
one that fades up out of the page background.

**Why an animation and not a transition.** 23-08 animated a height out of
`display: none` with `grid-template-rows: 0fr → 1fr` entered via
`@starting-style`, and that was right there. It is wrong here. A transition has
no previous computed value to start from across a `display` change, so it needs
that entry block — and `@starting-style` is newer than this component's audience.
A transition would therefore move for some visitors and **silently do nothing for
the rest**, which is precisely the failure shape 23-01's `interpolate-size` ban
exists to stop; it is not a smaller failure because the property involved is
Baseline-newer rather than Chromium-only. An animation runs for everyone, and an
element at `display: none` runs none of it — so the scripts-blocked reader, for
whom this bar never appears at all, is reached by nothing either way.

**Transform and opacity, and nothing else**, with the ban asserted on the
keyframes body itself rather than only on the component. `height`, `max-height`,
`grid-template-rows`, `width`, `display`, `visibility`, `padding` and `margin` are
all forbidden inside the block. A bar stranded at an intermediate size is a
blocked save, and `.js .mobile-nav`'s `transition: none` is this file's own
recorded precedent for a size-interpolating transition stranding a computed value
at 0.01 ms.

**No fill mode**, asserted. An animation holding its final frame keeps overriding
the element's own computed style, which is the other way a bar gets stranded.
With no fill the element is handed straight back to its own style the instant the
animation ends — the whole reason an animation was chosen over a size
interpolation in the first place.

The travel is `var(--space-md)` **upward into place**: the bar is pinned to the
bottom of the viewport at both breakpoints, so it arrives from the direction a
physical object would, and never crosses the content it is about to sit over.
The declaration is on the **base** rule, so the component has one arrival at both
widths — the same discipline its own `z-index` comment argues for.

### Nothing else moved, proven mechanically

`git diff` on `style.css` for the whole plan: **88 insertions, 0 deletions.** The
bar's geometry, stacking, width, clearance and resting shadow are **byte-identical**,
which is the four-iteration history left closed rather than inspected and
declared unchanged. The declarations the plan asked to be quoted, all unedited:

```css
  z-index: 30;                                            /* both breakpoints */
  width: fit-content;
  max-width: calc(min(1440px, 100%) - var(--space-md) * 2);
  box-shadow: var(--shadow-card-hover), 0 12px 32px rgba(18, 21, 27, 0.16);
  left: calc(240px + var(--space-xl) + var(--space-md));
  bottom: calc(var(--space-md) + 56px + env(safe-area-inset-bottom, 0px));
.dirty-ready .dashboard-main { padding-bottom: calc(var(--space-2xl) + 88px); }
.dirty-ready .page-content  { padding-bottom: calc(
      var(--space-2xl) + 56px + 144px + env(safe-area-inset-bottom, 0px)); }
```

Both MEASURED clearance figures (88 px desktop, 144 px phone, the second measured
in both languages because English wraps taller there) are pinned by the new check,
so a later plan cannot drift past them.

### The count, and the half the plan did not ask for

`setCountText()` is the count's **one** write site, replacing four — one per
branch of `updateBar()`. Nothing is written at all unless the sentence genuinely
differs; the text is written first and the class second; the class is removed,
a layout property is read, and it is re-added, so a second change in a row
restarts the animation rather than being coalesced into nothing.

**The gate is an accessibility fix as much as a motion one, and that was not in
the plan's behaviour list.** The bar is `role="status"` and `updateBar()` runs on
every `change` *and* every `input` event — which is every keystroke in the
wake-interval and quiet-hours fields. The previous code re-assigned `textContent`
on every one of those, replacing the live region's child nodes with identical
text. The animation forced the question "did this value actually change?", and
answering it improved the announcement. The browser check measures exactly this:
a MutationObserver installed **before** the first edit records the sequence of
values the region ever holds, and mutation M10 shows what the ungated version
produces — `['Frame colours changed', 'Frame colours and Runway changed',
'Frame colours and Runway changed']`.

**The count spends `.is-fading-in`, not a fifth keyframes block**, which is
exactly what 23-08's notes-for-later-plans hands to this one by name.

### What the accessible value of the count is during the tween

**The real one, at every instant, because the number is never tweened.** What
animates is the element's opacity; the text is a single assignment of the final
string, made *before* the class is added, so the first animated frame already
shows the true value. The check asserts three separate things about this: the
region never holds the empty string, the displayed value equals the last value
announced, and the total number of writes equals the number of genuinely
different sentences. An animation that had required rewriting the text
mid-transition would have been the wrong animation — not a reason to accept a
partial announcement.

---

## Task 2 — Saving…, and the confirmation that lands where the document does

### The question submit-guard.js asks, answered for this control

`submit-guard.js` defers its disable to a zero-delay timer because **a submitter's
name/value pair joins the form data set after the submit event's listeners
return**, and a disabled control is skipped when that set is built — an inline
disable would have made every theme and language switch a silent no-op.

A relabel has the same timing question and a **different, stronger answer**: it is
a property of the control, not of the timing.

- `.dirty-bar__save` and the bottom `[data-static-save-fallback]` are both
  `<button type="submit">` carrying **no `name` attribute**. A submitter with no
  name contributes **no entry at all** to the form data set, so there is nothing a
  label could displace, whenever the relabel runs.
- The code **re-checks that on the live control** rather than trusting it. If a
  later plan gives either Save a name, the relabel stands down on its own instead
  of quietly rewriting a payload.
- `<input type="submit">` is excluded by the same clause for the sharper reason:
  that element has no text content, so **its label IS its submitted value** —
  relabelling one genuinely does change what is posted.

**The finding, stated as the plan required:** `.dirty-bar__save` does **not**
contribute a name/value to the form data set. The relabel may therefore run
inline, and it does. That reasoning is written into the code comment, in the
register `submit-guard.js`'s header established.

**The order between the two files is fixed, not lucky.** This listener is on the
**form**; `submit-guard.js`'s is on **document**. A submit event dispatched at the
form reaches the form's own listeners before it reaches document, so the relabel
runs first and synchronously; `submit-guard.js` then only *schedules* its write,
which cannot run until the dispatch has finished. Relabel, then disable, every
time — by propagation order plus a queued task, not by either file knowing about
the other. Neither writes the other's property: this file writes text content and
never `disabled`, that file writes `disabled` and never text. **No second disable
was added**; `grep -c 'disabled' companion/static/dirty-state.js` is still `0`.

**A bfcache restore undoes the relabel.** A page restored from the back/forward
cache comes back with the DOM exactly as it was left — including a Save button
still reading the in-flight word for a request that finished, or never finished, a
navigation ago. `submit-guard.js` restores the controls it wrote on the same
event and for the same reason; this is that pattern applied to the property this
file writes, and only to a control this file wrote it on. **The plan did not ask
for this; it is a defect the relabel would otherwise have introduced (Rule 2).**

### Why there is no "Saved ✓" on the bar

Recorded in `config_page.py` itself, beside the constant, rather than only here:
the save is a **full form POST that replaces the document**, so the bar that shows
the in-flight word does not exist when the save completes. Reporting the finished
state on it would mean carrying a flag across that navigation, which would mean
browser storage — and this app holds **no client state at all**, deliberately. A
second source of truth beside the server is the one thing its whole discipline
excludes. The completed state is `app.py`'s existing `FLASH_KEY_SAVED`
confirmation, `"Saved — %s"` / `"Enregistré — %s"`, on the page the browser
actually lands on, which is where the reader's eyes are.

**That flash already reads as a confirmation of this action**, so its copy was not
touched. The browser check asserts it on the landing page in both languages.

### The word

`config_page.DIRTY_SAVING_TEXT = "Saving…"` — the **sixth** translated word on
the same `.dirty-bar` element the five connector words already ride on, rendered
as `data-dirty-saving` and read by `dirty-state.js` with a **byte-identical**
English fallback. Single U+2026, matching this module's own `"Polling…"` and
`layout.py`'s `"Reconnecting…"`. French: **`"Enregistrement…"`**, the progressive
form of the same verb `"Enregistrer les réglages"` already uses, so the control
reads as the same action continuing rather than a new one.

---

## Task 3 — a browser proves it

Three new checks, plus one shipped clause retargeted. Details in the commit; the
properties are: the bar's entrance **resolves to the stylesheet's own block**
(not merely declared in a file); a hidden bar still **computes `display: none`**
with that entrance on it, on a scripted page *and* on a scripts-blocked one; the
count's announcement sequence measured by MutationObserver; the posted body
captured **on the wire** twice and compared; and B1's floor at 360 px in both
languages.

### How the fallback Save and the bar's appearance were proven still to hold

Four independent measurements, not one:

1. **The shipped D-01 check** (`the fallback Save button stays reachable and
   functional until the bar has actually been shown once, then hides`) — green
   before and after, unmodified.
2. **The shipped scripts-blocked save** (23-06's, at 360 px, both languages,
   asserted against the config on **disk**) — green before and after, unmodified.
3. **A new scripts-blocked check** asserting what neither of those does: neither
   `dirty-ready` nor `dirty-shown` is on `<html>` (both have exactly one writer
   and it cannot run there), the bar **computes `display: none`** with this
   plan's entrance declared on it, and the fallback Save is **`is_visible()` with
   a non-zero bounding box** — not merely rendered, which is precisely the shape
   B1 took. Then it saves, and the value is read back from disk.
4. **The bar's appearance** is asserted in the scripted check by `is_hidden()`
   going false on the first edit *and* by the computed `animationName` resolving
   to `skypane-bar-arrive`.

Mutation M8 (the fallback hidden unconditionally — a faithful reproduction of
B1's second half) reddens all of 1, 2 and 3.

---

## Mutation testing

Eleven mutations, each reverted, the tree verified clean afterwards
(`git status --short` empty, `git diff --stat` showing only the intended file).

| # | mutation | result | message (quoted from the run) |
|---|---|---|---|
| M1 | `.dirty-bar[hidden]`'s `display: none` → `opacity: 1` | config-page 238 → **237** | `expected .dirty-bar[hidden] to hide by display: none — without it the base rule's own display beats the user-agent [hidden] rule and the save bar renders permanently visible on every page load, including a scripts-blocked one. This is B1's own collision class` |
| M2 | the entrance declaration removed from the base rule | config-page 238 → **237** | `expected the base .dirty-bar rule to declare its entrance from var(--motion-fast) — a save bar's arrival is something the user is waiting on, and a bare duration literal fails 23-01's motion guard outright` |
| M3 | the changed-text gate removed | companion-app 289 → **288** | `expected the count's write to be gated on the text having actually changed — an unrelated re-render must write nothing at all, not the same string again` |
| M4 | the class added BEFORE the text is written | companion-app 289 → **288** | `expected the count's text to be written BEFORE the animation class is added, so the displayed number is the real one from the first frame` |
| M5 | the name guard removed from the relabel | config-page 239 → **238** | `expected the relabel to stand down for a NAMED submitter: a named control's name/value pair is part of the form data set, and companion/layout.py's theme and language pickers are exactly that shape` |
| M6 | the relabel writes `value` instead of text content | config-page 239 → **238** | `expected the relabel to write only textContent — writing \`value\` on a submitter is writing the form data set itself` |
| M7 | the relabel removed outright | browser 50 → **48** | `lang=en: expected the Save control to read 'Saving…' while its POST is in flight, got 'Save settings' — and without that the payload comparison below would prove nothing` (+ the retargeted T14 clause, by design) |
| M8 | the fallback Save hidden unconditionally | browser 50 → **46** | `lang=en: the fallback Save is rendered but not visible — which is precisely the shape B1 took, and a check that only asked whether it EXISTS would have passed through it` |
| M9 | `.dirty-bar[hidden]` weakened, measured in a browser | config-page **237**, browser 50 → **48** | scripted page: `a hidden save bar computes display 'flex' — the [hidden] override has stopped winning, and a bar that is visible before any edit is the same class of defect as one that never appears (B1)`; scripts-blocked page: `the save bar computes display 'flex' on a page with no script — nothing can ever reveal it here, so a visible bar would be a Save button that does nothing` |
| M10 | the changed-text gate removed, measured in a browser | browser 50 → **49** (exactly one) | `a re-render that changed no number still wrote to the count: ['Frame colours changed', 'Frame colours and Runway changed'] became ['Frame colours changed', 'Frame colours and Runway changed', 'Frame colours and Runway changed']. Re-writing identical text into a role="status" region is how the same number gets announced twice` |
| M11 | the entrance declaration removed, measured in a browser | browser 50 → **49** (exactly one) | `the revealed bar's animation resolves to 'none' — an entrance that names a block the stylesheet does not define renders as no entrance at all, and no browser reports it` |

---

## Did any of my own checks fail the vacuity question?

Asked of every new check: *what would a wrong implementation do?* **Three failed
it, all caught before landing.**

1. **"The count did not change on a no-op re-render" is vacuous if the no-op
   never reached the script.** The first version dispatched a synthesised `input`
   event at `quiet_hours_start`. If that event had silently failed to reach
   `updateBar()` — a plausible failure, since this form's fields are cross-DOM
   `form=`-attached and the listener is a filtered document delegation — the
   clause would have passed by nothing having happened, against any
   implementation at all. It is now a **real edit**: a third theme value inside
   the already-dirty Frame colours section, which changes the form and runs the
   same delegated listener clause 1 proved works, while leaving the rendered
   sentence identical. The edit's landing is asserted before the clause is read.
   M10 confirms the fixed version reddens.

2. **"The posted body is unchanged by the relabel" is satisfied by a script that
   never relabels anything.** Two identical bodies are exactly what the absence
   of the feature produces. The check now reads the control's label between the
   two captures and requires it to be the translated in-flight word — so the
   equality is asserted *against a relabel that provably ran*. M7 shows the check
   going red on that control clause, not on the comparison.

3. **"The fallback Save is reachable with scripts blocked" is satisfied by a
   control that is present but invisible** — which is not a hypothetical, it is
   the exact shape B1 took, and the shipped sibling check uses `query_selector`
   plus `.click()`, so it fails by a 30-second Playwright timeout rather than by
   saying so. The new check asserts `is_visible()` and a non-zero bounding box
   first, then clicks, then reads the value back off disk.

**A fourth was caught by the harness, and it is the same substring-collision class
23-08 hit.** My own source check counted the count's write sites with
`src.count("countEl.textContent =")` — which **also matches the gate's own
`=== ` comparison** one line above it. The check therefore read one write site
too many and failed the very implementation it exists to require. Fixed with a
negative lookahead (`countEl\.textContent =(?!=)`), and the reason is written into
the check beside it. The check was right to go red.

---

## Criteria that did not evaluate as predicted

Three. All recorded rather than adjusted away, per the standing constraint.

**1. `grep -cE 'sessionStorage|localStorage' companion/static/*.js` does not
output `0` across every file — `companion/static/flight-rows.js` outputs `1`.**
The single occurrence is 23-08's own comment paragraph (`flight-rows.js:85`)
explaining that the file holds no state "about storage that outlives the page
(cookies, localStorage, …)". It is prose, not a declaration. Neither the criterion
nor the code was changed. **Measured the way this plan's new guard measures it —
on comment-stripped source, which is 23-01's own recorded standard for exactly
this trap — the answer is `0` across all sixteen scripts**, and that stripped form
is now executable in `test_config_page.py`. This is the "beware criteria your own
prose trips" trap, hit for the fifteenth time in this project, and for the first
time on *another plan's* prose rather than this plan's.

**2. Removing the `[hidden]` override produces THREE failures across two
harnesses, not "exactly one" (M9).** One source-level clause in `test_config_page.py`,
and two browser failures — a **scripted** page where the bar is visible before any
edit, and a **scripts-blocked** page where it is visible and can never be
dismissed. Those are three genuinely different configurations of the same defect
and none is redundant; 23-08 recorded the same shape ("the second failure is the
source-level clause asserting the same property, which is the intended
belt-and-braces"). The criterion's *number* did not hold. Its subject did, three
times over.

**3. `grep -c 'disabled' companion/static/dirty-state.js` equals its pre-task
value only because the prose was written around it.** The pre-task value is `0`,
so the criterion demands the word appear nowhere in the file — including in the
comment that explains why this file adds no second disable. The first draft of
that comment used the word four times and failed the criterion honestly. The
prose was rewritten to say "the property that makes a control unusable" and "the
shared guard" instead; the criterion was designed around, not discovered by a
failure the second time. Same family as 23-01's decision to keep the literal
`@keyframes` out of its own keyframes comment.

**A fourth constraint, not a criterion, tripped the same way and did produce a
failure: the standing "no backtick in a `companion/static/*.js` comment" rule.**
Both new comment blocks used backticks for code identifiers, matching the *Python*
files' house style; four shipped checks went red at once. Both files are
backtick-free now (`grep -c '`'` → `0` on each).

## Other acceptance greps, run literally

```
size props restricted to the four .dirty-bar rules              -> 0
    (restriction made by an anchored regex over
     ^(\s*)\.dirty-bar(\[hidden\])? \{ … ^\1\}, which matched
     exactly 4 rules: the base rule, its [hidden] override and
     the two media-query rules; the joined bodies were then
     grepped for ^\s*(height|max-height|grid-template-rows):)
grep -v '^ *[*/]' style.css | grep -c 'prefers-reduced-motion: reduce'   -> 2  (unchanged)
grep -v '^ *[*/]' style.css | grep -c 'prefers-reduced-motion: no-preference' -> 1  (unchanged, 23-04's)
grep -c '@keyframes' companion/static/style.css                 -> 4  (was 3; +1 argued for, named skypane-bar-arrive)
git diff --numstat companion/static/style.css                   -> 88 insertions, 0 deletions
grep -c 'data-dirty-saving|data-dirty-pending' config_page.py   -> 1  (data-dirty-saving)
grep -c 'disabled' companion/static/dirty-state.js              -> 0  (its pre-task value)
companion/test_i18n.py                                          -> exit 0, 24/24
ruff check .                                                    -> All checks passed!
```

**The fourth `@keyframes` block is argued rather than asserted**, as 23-01
requires and 23-06/23-08 precedented. The argument is in the stylesheet, above the
block: the three existing blocks are an opacity cycle, an opacity ramp and a
background wash, and **none of them moves anything**; a save bar that fades up
from nothing materialises out of the page background rather than arriving.
23-01's guard accepts it unaided — the name is defined once, the reference
resolves, and the duration comes from `var(--motion-fast)`.

---

## The no-JS floor

Unchanged, and re-asserted rather than trusted:

1. **Nothing this plan adds is reachable without scripts.** The entrance is
   declared on an element that is server-rendered `hidden`, so it computes
   `display: none` and runs no animation at all — asserted on a real
   scripts-blocked page, not reasoned about. The in-flight label is written by a
   script that never runs. The count's gate is in the same script.
2. **Neither hiding marker can be written.** `dirty-ready` and `dirty-shown` have
   exactly one writer each, and it is `dirty-state.js`. Asserted absent from
   `<html>` in both languages at 360 px.
3. **The fallback Save is visible, has a real box, and saves.** Read back from the
   config on disk, in both languages, at the 360 px contract floor.
4. **B1's gate was not touched.** `.dirty-ready.dirty-shown [data-static-save-fallback]`
   is byte-identical, and `updateBar()`'s `bar.hidden = false` branch — where the
   second marker is written — is byte-identical apart from the count's write
   becoming a call.

**Nothing this plan adds renders a control that does nothing.**

---

## Deviations from Plan

**1. [scope] The French word went to `companion/i18n_fr/display.py`, not
`common.py`.** The plan's `files_modified` and its `read_first` both name
`common.py` as "the catalogue this bar's copy already uses"; that is factually
wrong on this tree. All seven of the bar's strings — `"Unsaved changes"`,
`"Save settings"`, `"Cancel"` and the five connectors — live in `display.py`.
The package's `_build_catalog()` raises `ValueError` on a duplicate key across
sibling modules, so there is exactly one correct home and it is not the one
named. `common.py` was not modified.

**2. [scope] `companion/test_i18n.py` is in the plan's `files_modified` and was
NOT modified.** No change was needed: Check 6 already scans every
`companion/static/*.js` for `|| "..."` fallback literals and demands each be a
catalogue key, so it demanded the French entry for `"Saving…"` on its own and went
green once the entry existed. Adding a bespoke clause would have been a second,
weaker copy of a general rule. 24/24 throughout.

**3. [Rule 2 — missing critical functionality] The relabel is undone on a bfcache
restore.** Not in the plan. Without it a back-navigation after a save lands on a
Save button permanently reading the in-flight word, because the restored DOM is
the DOM as it was left. `submit-guard.js` already handles the same hazard for the
property it writes, on the same event; this mirrors it, and only for a control
this file wrote on.

**4. [Rule 3 — blocking] `companion/static/submit-guard.js`'s own documented
three-handler analysis said `dirty-state.js`'s submit listeners "do exactly one
thing", which this change made false.** That header is the register the plan told
me to write into, so leaving it stating a falsehood was not an option. Restated in
place, with the unchanged conclusion and its reason (propagation order), and with
a note under its own "the label does NOT change" section recording that D3 has
landed *elsewhere* and must not be moved here. Comment-only; the file's code is
byte-identical.

**5. [judgement] T14's browser clause forbidding a progress word was retargeted
rather than deleted.** Its own failure message named "D3, Phase 23" as the plan
that would change it. Asserted literally it would now be testing for the absence
of this plan's feature. The property it was about keeps its home in
`test_companion_app.py`'s served-body check on `submit-guard.js`, which fails that
file for containing the word at all and is green; the browser clause now asserts
the two mechanisms **coexist** — the control is disabled *and* wears the word.
Strictly stronger, and M7 reddens it.

**6. [judgement] The `[hidden]` assertion landed in TWO places, not one.** The
plan's criterion expects one failure on mutation. A source clause catches a
stylesheet edit; a computed-style assertion catches what a source scan cannot see,
which is the entire reason the browser harness exists (B1's own lesson). Both
were kept. See criterion 2 above.

**7. [judgement] The count's gate was made an announcement fix as well as a motion
gate.** The plan asked only that the count not animate when the number is
unchanged. The same gate stops `updateBar()` re-writing identical text into a
`role="status"` region on every keystroke, which was live behaviour before this
plan. Recorded rather than left as a silent side effect.

---

## Things the plan assumed that turned out otherwise

1. **`companion/i18n_fr/common.py` is not the bar's catalogue.** `display.py` is.
   See deviation 1.
2. **`.dirty-bar[hidden]` had NO executable guard of any kind before this plan** —
   while all three components that later copied the idiom (`.refresh-pill`,
   `.login-reveal`, `.banner__pill`) do, and `.dirty-bar` is the one every one of
   their comments cites as the precedent. The app's worst-history component was
   the only unguarded consumer of its own pattern. This plan closes that, which is
   the "fix a known landmine" standard applied to a landmine that had been sitting
   under the very rule it named.
3. **An `@starting-style` transition is not the right mechanism here**, even
   though 23-08 established it in this stylesheet nine hours earlier and the
   plan's own `<action>` points at transform/opacity without saying how. The
   support surface is the deciding argument, not the property list.
4. **`evt.submitter` is the only honest way to identify the control.**
   `submit-guard.js` carries a fallback that walks `form.elements` for the first
   enabled submit control; copying it here would risk relabelling a control the
   user did not press. A missing `submitter` means no relabel, which degrades to
   exactly what the control did before this plan.
5. **`form.requestSubmit()` with no submitter is a genuine control for the payload
   comparison** — it fires a real submit event with `evt.submitter` null, so the
   relabel stands down by its own first clause and the captured body is the
   payload as it was before this plan. The plan asked for "before and after the
   change" without saying how to obtain the "before" on one tree.
6. **Two shipped scripts-blocked checks fail by a 30-second timeout rather than a
   message when the fallback Save is hidden.** Logged to `deferred-items.md` for
   23-11; they do go red, which is the property that matters.
7. **A theme/runway index cannot be hardcoded in a new browser check.** The
   save-bar checks above persist their own edits, so `THEME_IDS[1]` is frequently
   the value already stored by the time a later check runs — and clicking the chip
   that is already selected is not an edit, which makes every assertion below it
   vacuous rather than red. Found by the check failing on its first run. Both
   targets are now derived from what the page is actually showing.

---

## `EXPECTED_CHECK_COUNT`

Every one re-derived by **running**, appended as a new last assignment citing this
plan.

| Harness | Before | After | Task |
|---|---|---|---|
| `companion/test_config_page.py` | 237 | **239** (+1 Task 1, +1 Task 2) | 1, 2 |
| `companion/test_companion_app.py` | 290 | **291** (+1) | 1 |
| `companion/test_browser_ux.py` | 47 | **50** (+3) | 3 |
| `companion/test_i18n.py` | 24 | 24 (untouched) | — |
| `companion/test_status_pages.py` | 287 | 287 (untouched) | — |
| `companion/test_view_pages.py` | 152 | 152 (untouched) | — |
| `companion/test_contrast_check.py` | 43 | 43 (untouched) | — |
| deferred-script pin | 14 | **14** (no script added or removed) | — |

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_browser_ux.py` | 47/47 | **50/50** | — |
| `companion/test_config_page.py` | 237/237 | **239/239** | — |
| `companion/test_companion_app.py` | 288/290 | **289/291** | 2 × WR-11 read-only (documented) |
| `companion/test_status_pages.py` | 286/287 | **286/287** | 1 × `anomaly_active()` (documented) |
| `companion/test_view_pages.py` | 152/152 | **152/152** | — |
| `companion/test_i18n.py` | 24/24 | **24/24** | — |
| `companion/test_contrast_check.py` | 43/43 | **43/43** | — |
| `server/test_manual_resolutions.py` | 21/23 | **21/23** | 2 × WR-11 read-only (documented) |

`PYTHON=… bash scripts/run-all-tests.sh` → three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline**, verified by
NAME: `add_entry()`/`delete_entry()` in `server/test_manual_resolutions.py`, their
two end-to-end counterparts in `companion/test_companion_app.py`, and
`anomaly_active()` in `companion/test_status_pages.py`. **No new failure, and no
sixth.** Coverage `TOTAL 6927 490 93%`, floor 83. `ruff check .` clean. **No test
exception was added anywhere; the suite still carries none.**

---

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-33 | mitigate | The posted body is captured **on the wire** and compared byte for byte between the same edit posted with and without the relabel, in both languages, against a control proving the relabel ran (M7 reddens that control). No size-interpolating property is animated on this component — banned inside the keyframes body and in every `.dirty-bar` rule, at both breakpoints — and the entrance carries no fill mode, so the bar cannot be stranded. The `[hidden]` override is re-asserted in three configurations (M1, M9). |
| T-23-34 | mitigate | B1/D-01's two-marker gate is byte-identical and was not read or written by this plan. The fallback Save is re-asserted with scripts blocked at 360 px in both languages — **visible, boxed, clicked, and the value read back off disk** — plus both markers asserted absent from `<html>` and the bar asserted to compute `display: none` there. M8 reddens it. |
| T-23-35 | accept | Unchanged. The in-flight label is one fixed translated word from the catalogue, carrying no status, no URL and no server text. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. No new route, no auth path, no schema change, no new file
access pattern. The one new server-rendered value crosses `escape_html()` at its
own site, in the same expression as the five that preceded it.

## Known Stubs

**None.** Every surface this plan claims is live IS live, and each is asserted by
behaviour rather than by declaration: the entrance's computed `animationName`
resolves to the stylesheet's own block; the count's announcements are read out of
a MutationObserver rather than inferred; the in-flight label is read off the
control after a real POST went out, in both languages; the completed state is read
off the landing page's own text; and the scripts-blocked save is read back from
the config on disk.

## Notes for later plans

- **23-10** owns the rest of D3. The stylesheet now carries **four** keyframes
  blocks — `skypane-pulse` (ambient cycle), `skypane-fade-in` (one-shot ramp,
  reused by `.is-fading-in`), `skypane-row-arrive` (background wash) and
  `skypane-bar-arrive` (a translate-plus-opacity entrance). A plan that wants "a
  value just changed" spends `.is-fading-in`; a plan that wants "this arrived"
  should consider whether `skypane-bar-arrive` fits before declaring a fifth. The
  reduce-block count is still **2** and 23-01's guard still fails a move.
- **23-10** should also know that **an entrance out of `display: none` does not
  need `@starting-style`**: an animation declared on the component runs when its
  `display` changes away from `none`, for every browser, with no entry block and
  no support caveat. `@starting-style` remains the right tool where the *previous
  value* genuinely matters (23-08's height), not merely where an element becomes
  visible.
- **23-11** owns: ticking CFG-32 (this plan does **not**; D3's remainder is
  23-10's) and rewriting its traceability row; recording in `SKILL.md` the fourth
  keyframes block, the save bar's entrance and its stated reason for being an
  animation, the in-flight label as a new copy register entry in both languages,
  and the "animate the element, write the number once" rule now shared by the
  filter count and the save bar; and the human sweep — change one setting and
  watch the bar arrive and the count move, change a second and watch the count
  move again, press Save and read the in-flight word and then the confirmation,
  and do the whole thing again with scripts off using the fallback Save.
- **Anything that later gives either Save control a `name` attribute** must know
  that the relabel stands down for it automatically, by design — the label will
  simply stop changing rather than silently rewrite a payload. That is the safe
  failure, but it is a silent one, so say so in the plan that does it.
- **`deferred-items.md`** gained one entry: two shipped scripts-blocked checks
  fail by a 30-second Playwright timeout rather than a message when the fallback
  Save is hidden. Cheap to fix; the message to reuse is in this plan's own check.

## Self-Check: PASSED

```
FOUND: companion/static/style.css
FOUND: companion/static/dirty-state.js
FOUND: companion/static/submit-guard.js
FOUND: companion/pages/config_page.py
FOUND: companion/i18n_fr/display.py
FOUND: companion/test_config_page.py
FOUND: companion/test_companion_app.py
FOUND: companion/test_browser_ux.py
FOUND: .planning/phases/23-.../23-09-SUMMARY.md
FOUND: 1273a66  FOUND: 26fd99a  FOUND: 99ae977  FOUND: 6dea46a  FOUND: 9578d57
```

Working tree clean after every mutation: `git status --short` empty of source
changes and every mutated file restored from its committed state, verified with
`git diff --stat` after each.
