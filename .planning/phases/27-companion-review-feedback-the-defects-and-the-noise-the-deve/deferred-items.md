# Deferred items — phase 27

Out-of-scope discoveries and open PROVISIONAL decisions logged rather than
resolved, per the executor's scope-boundary rule and per this plan's own
instruction to record every open PROVISIONAL decision the developer has not
yet ruled on. Nothing here was fixed by the plan that found it, and nothing
here is a defect — each is a decision only the developer can make.

---

## The "règles par vol" view — deliberately out of scope for the WHOLE phase

**Source:** `.planning/ROADMAP.md`'s own Phase 27 entry, stated before any
plan in this phase was written.

**The developer's own words:** *"pas propre, manque de simplicité, trop de
texte"* — about the rule-add form / rule list on the calendar rules page.

**Why it was not planned:** the brief is too vague to plan against and needs
a conversation first — unlike the six corrections this phase DID plan
(each backed by a specific developer sentence naming a specific defect), this
one names a feeling about a whole view, not a specific, actionable fault. A
plan written against "not clean, lacks simplicity, too much text" without
a design conversation first would be guessing at what the developer actually
wants, which is the opposite of what a review-feedback phase should do.

**Status:** not started. Needs a `/gsd-discuss-phase` (or equivalent
conversation) before it can be planned at all.

## The rule-add form's colour grid, left unwrapped by 27-07 for the same reason

**Source:** 27-07-SUMMARY.md, Decision 2 and "Next Phase Readiness".

**What shipped:** `_theme_carousel_html()` now wraps departures, arrivals and
calendar — three carousels, not four. The rule-add form's own colour grid
(inside the calendar-rules page, the same page the "règles par vol" view
above lives on) was deliberately left as a plain, un-carouselled grid.

**Why it was not folded in:** it lives inside the SAME deferred view above —
converting it now, ahead of that view's own redesign conversation, risks
doing the wrong thing twice (once now, again after the conversation settles
what the view should actually look like). Recorded together with the view
it is deferred alongside, per this plan's own instruction, so the two
decisions are findable in one place rather than scattered across two
SUMMARYs.

**For whoever picks up "règles par vol":** folding this grid in is
mechanically cheap once the view's own shape is settled — one more call to
`_theme_carousel_html()` with one more id (the trap that requires an id per
carousel is now closed structurally, so this fourth call cannot accidentally
collide with the other three).

## `DIRTY_SECTION_ATTR` (`data-dirty-section`) — emitted in markup, read by nothing

**Source:** 27-04-SUMMARY.md, "Next Phase Readiness".

**What shipped:** 27-04 retired the dirty save bar outright, including its
reader for this attribute (`dirtySectionLabels()`, deleted with the bar). The
attribute itself — `data-dirty-section`, marking which settings card a field
belongs to — is still emitted at all seven of its call sites in
`config_page.py`, because retiring those seven emission sites was explicitly
out of 27-04's own scope.

**Consequence today:** the attribute is inert markup. It still marks the same
visual grouping a sighted reader already sees from the card boundaries
themselves, so nothing is broken — it simply has no reader any more.

**For whoever next touches `config_page.py`'s settings-card builders:**
either give it a new reader (if a future feature needs to know which card a
field belongs to from script) or remove the seven emission sites as dead
markup. Neither is urgent; this is housekeeping, not a defect.

---

## Open PROVISIONAL decisions — not yet ruled on by the developer

Each of these shipped as the best available choice at plan time, explicitly
marked PROVISIONAL in its own SUMMARY, with a recorded fallback if the
developer prefers it. None has been put to the developer for a ruling yet.

### 1. The quiet-hours dial's caption BLANKS its duration during a drag, rather than showing a stale or computed one (27-02, CFG-62)

**What shipped:** the caption's duration segment carries an EMPTY
`data-value-readout-text` template. The moment the pair moves away from what
the server rendered, the duration span goes blank and stays blank until the
next server render (a save, or a reload) — it never shows a live-computed
duration during the drag itself.

**Why:** the shipped `paintReadouts()` base-equality rule blanks a readout
when the CURRENT value equals its base — built for a delta sentence that is
noise when nothing changed. A duration needs the OPPOSITE polarity (blank the
moment something DOES change, since a live duration computation would need
new script logic this file does not have). An empty template makes both of
that rule's branches resolve to the same safe `""`, at the cost of the
duration visibly disappearing for the whole of a drag.

**The recorded fallback**, if the developer finds the disappearing duration
unacceptable on a real phone: C2 from `27-RESEARCH.md` — server-emitted
per-unit duration templates, keyed to the ladder's own thresholds, computed
client-side from the pair the same way the two endpoint spans already are.

**Status:** shipped as the PROVISIONAL choice; not yet reviewed on a real
device. This is one of the items named in the phase gate's own human-sweep
list (`.planning/REQUIREMENTS.md`'s Phase 27 coverage ledger).

### 2. Auto-save fires on `change`, never on `input` (27-04, CFG-63)

**What shipped:** a field commits (and saves) on `change` — a blur, a radio
click, a keyboard commit — never on every keystroke. The developer's own
binding decision (`.planning/ROADMAP.md`, "Developer decisions") confirmed
the leave-guard stays alive specifically BECAUSE of this choice (a keystroke
that never fires `change` still needs protecting), but the choice of
`change`-over-`input` itself was never separately put to the developer as its
own question — it was 27-04's own design decision, marked PROVISIONAL in its
own frontmatter (`dirty-state.js`'s header comment).

**Why:** "a keystroke is not a decision" — saving mid-typing (e.g., after
every character of a partially-typed calendar URL) would fire far more writes
than necessary and could save a value the user is still in the middle of
correcting.

**Status:** shipped as the PROVISIONAL choice; functionally sound (the
leave-guard's own re-verification, CFG-63's coverage-ledger row, confirms no
edit is lost even under this model) but never explicitly confirmed as the
developer's own preference over an alternative (e.g., a debounced `input`
listener).

### 3. No per-field error delivery on a rejected auto-save (27-04, CFG-63)

**What shipped:** a rejected value (e.g., a wake interval below its floor)
raises the app's ONE existing generic translated toast — the same sentence
the `role="switch"` controls already use on failure — rather than a
field-specific error message next to the offending control.

**Why, and the developer's own binding decision on this one specifically**
(`.planning/ROADMAP.md`, "Developer decisions", second bullet): *"Per-field
errors are NOT built now: returning a JSON error map is a real mechanism and
parsing returned HTML is a forbidden sink here. Acceptable because most
fields are now controls that cannot produce an invalid value."* This one WAS
put to the developer and answered — recorded here for completeness, not as an
open question, since 27-04's own SUMMARY still marks the surrounding decision
PROVISIONAL in its frontmatter alongside the `change`-vs-`input` choice above.

**The recorded fallback**, if the developer later wants field-specific
errors: a JSON error map from `POST /settings`, parsed client-side into a
per-field message — explicitly NOT parsing returned HTML, which this
project's own security posture forbids as a sink.

**Status:** answered by the developer (kept as generic toast); listed here
only so the fallback stays findable beside the decision it belongs to.

---

## Not a deferred item — recorded here only to close the loop

**CFG-57's "omit the href when already there" alternative (27-08) was NOT
borrowed, and this is not a gap.** 27-08's own PROVISIONAL note explains why:
that pattern belongs to Phase 26, which is planned but not yet executed. The
Quiet hours schedule link this phase built is ALWAYS a real `<a href>`,
including on `/display` itself (a working same-page fragment jump), which is
simpler and correct on its own terms — CFG-57's pattern was never available
to borrow from, not rejected on its merits. Nothing for the developer to
decide here; recorded only so a future reader does not go looking for a
missing cross-reference.
