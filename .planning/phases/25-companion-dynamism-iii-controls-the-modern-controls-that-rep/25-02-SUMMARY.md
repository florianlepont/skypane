---
phase: 25-companion-dynamism-iii-controls-the-modern-controls-that-rep
plan: 02
subsystem: companion-harness
tags: [browser-harness, no-js-floor, accessibility, touch-targets, playwright]
requires:
  - "companion/test_browser_ux.py::_no_js_page (22-10)"
  - "companion/test_browser_ux.py::_set_ui_theme (24-02)"
  - "companion/test_browser_ux.py::_assert_no_page_overflow (24-02)"
  - "companion/test_browser_ux.py::_click_control (22-01)"
provides:
  - "companion/test_browser_ux.py::_persist_without_js"
  - "companion/test_browser_ux.py::_operate_with_keyboard"
  - "companion/test_browser_ux.py::_hit_area"
  - "companion/test_browser_ux.py::_assert_hit_target"
  - "companion/test_browser_ux.py::_assert_js_gate"
  - "companion/test_browser_ux.py::_in_both_themes"
  - "companion/test_browser_ux.py::MIN_HIT_TARGET_PX"
  - "companion/test_browser_ux.py::_no_js_page(cookies=...)"
affects:
  - "25-03 … 25-07 (the five control plans each call these)"
  - "25-08 (the phase gate)"
tech-stack:
  added: []
  patterns:
    - "helpers RAISE rather than return a verdict string (_set_ui_theme's shape)"
    - "instruments prove themselves before their result is trusted"
    - "hit areas are resolved through document.elementFromPoint, never a rect"
key-files:
  created: []
  modified:
    - companion/test_browser_ux.py
decisions:
  - "the persist verdict is the value read back FROM DISK; the reloaded DOM is corroboration and is optional"
  - "a click is not a pointer event — provenance (detail/pointerType), not the event name, is the discriminator"
  - "the hit area is counted in whole pixels sampled at their own centres, through elementFromPoint"
  - "_no_js_page() grew a cookies parameter so the file has ONE scripts-blocked call site again"
metrics:
  duration: ~3h
  completed: 2026-09-14
  checks_added: 0
  browser_harness: "65/65, 0 SKIP, 2m56.0s"
---

# Phase 25 Plan 02: Controls — the browser-harness control contract Summary

Four helpers that turn "this control is usable without scripts, from the
keyboard, at 360 px, in both themes" from four sentences the next five plans
would each have retyped into four calls they share — with the first of them
reading the saved value back off disk, because a control that renders
perfectly and saves nothing is the defect Phase 22 actually found.

**Zero net checks.** `EXPECTED_CHECK_COUNT` is 65 before and after; all 65
`check(...)` descriptions are AST-identical to the pre-plan commit.

---

## The decision that mattered most

**The persist helper's verdict is the value read back from disk, and the
reloaded DOM is a separate, optional clause.**

Three weaker sequences all look right and all pass against a broken control,
and the third one is the trap:

- *"the input is present with scripts blocked"* — passes against a control
  that saves nothing. This is the Phase 22 shape exactly.
- *"the page navigated after submit"* — passes against a POST the server
  rejected and redirected straight back from.
- *"the reloaded page shows the value"* — passes against a server that
  **deliberately** echoes a rejected submission back into the field. This app
  does that on purpose: `wake_interval_group()`'s own docstring records D-07
  requiring the raw submitted string be shown back to the user, bypassing the
  in-range guard. A DOM-only check would have read `900` back off a page that
  had stored nothing.

So `read_back()` — a caller-supplied reader going through the app's own
loader to the real state directory — is the verdict, and the DOM read is
corroboration. Making the DOM clause optional (`shows_back=False`) rather
than unconditional fell straight out of measuring it: `notifications_topic_url`
is write-only by design (T-20-12) and stores correctly while rendering empty
forever, so an always-on DOM clause would have been wrong for one of the five
fields the phase touches.

The second decision, made for the same reason: **the helpers raise rather than
return a verdict string.** `_assert_no_page_overflow()` returns a sentence
because its callers use the `_assert_clean` idiom; these four do not, and a
returned guard is one that five call sites each have to remember. `check()`
already turns a raised `AssertionError` into a named FAIL. `_set_ui_theme()`
is the precedent and this follows it.

---

## How zero-net was proved, not asserted

Following 23-02's and 24-02's precedent:

```
$ server/.venv/bin/python3 zeronet.py 123b103      # the pre-plan commit
check(...) call sites  HEAD=65  NOW=65
EXPECTED_CHECK_COUNT   HEAD=65  NOW=65
descriptions identical: True

$ git diff --numstat 123b103 HEAD -- companion/test_browser_ux.py
933	15	companion/test_browser_ux.py
```

The comparison walks both files' ASTs, collects every `check(...)` call's first
argument, and compares the two lists including order. Same count, same
descriptions, same order.

**All 15 removed lines, in full** — there is no assertion among them:

```
def _no_js_page(browser, base_url, route, viewport=None, sign_in=True):
context = browser.new_context(
java_script_enabled=False, viewport=VIEWPORT_MIN_SUPPORTED)
try:
context.add_cookies([{ "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
page = context.new_page()
page.goto(base_url + "/login")
page.fill("#password", TEST_PASSWORD)
page.click('button[type="submit"]')
page.wait_for_load_state("load")
page.goto(base_url + "/health")
finally:
context.close()
```

One signature line (it grew a parameter) and one hand-written scripts-blocked
context (it became a `_no_js_page()` call). Nothing else was deleted.

**Re-derived by running, not by arithmetic:**

| | before (123b103) | after |
|---|---|---|
| `EXPECTED_CHECK_COUNT` | 65 | 65 |
| checks run | 65/65 pass | 65/65 pass |
| `grep -c SKIP` | 0 | 0 |
| real wall clock, standalone | 3m16.8s | **2m56.0s** |

The helpers register no check, so they cost the suite nothing; the ~20s
difference is run-to-run noise on a shared machine (three separate runs of the
final file and its baseline landed at 3m16.8s, 2m58.6s and 2m56.0s).

Full suite: `./scripts/run-all-tests.sh` → **exactly the 5 sandbox baseline
failures, verified by NAME**, `browser-ux: 65/65 checks pass`:

1. `POST /airlines/resolve` … `manual_save_failed` flash key … read-only (WR-11)
2. `POST /airlines/manual-resolutions/{prefix}/delete` … `manual_delete_failed` … read-only (WR-11)
3. `add_entry() returns ADD_FAILED … parent directory is read-only` (WR-11)
4. `delete_entry() returns False … state dir goes read-only mid-write` (WR-11)
5. `anomaly_active() runs on every page render and must never raise`

4 × WR-11 read-only + 1 × `anomaly_active()`. No sixth.

---

## What each helper was shown catching

Every demonstration below was run against the real app through a real Chromium.
None of them is registered as a check.

### 1. `_persist_without_js()` — operate, submit, persist

**Positive, a number input.** `wake_interval_s` on `/device` at 360 px,
scripts blocked. On disk before: `300`.

```
{'field': 'wake_interval_s', 'set': '900', 'held': '900',
 'submitted_via': 'submitter', 'visible_submits': 1,
 'reloaded': '900', 'stored': 900, 'before': 300, 'restored': 300}
on-disk wake_interval_s after restore: 300
```

Set to **900**, submitted through the visible fallback Save, reloaded, read
back off disk as **900**, and restored to **300** as the helper's last act
(T-25-02-A — the fixture is shared with every other check in the file).

**Positive, a radio group.** `tracked_runway` on `/display`, same sequence,
the operator dispatched to `el.click()` on the value's own radio:

```
{'field': 'tracked_runway', 'set': '02-20', 'held': '02-20',
 'reloaded': '02-20', 'stored': '02-20', 'before': '3', 'restored': '3'}
```

**Negative, a field name that does not exist** (`wake_interval_seconds`):

> `_persist_without_js: no form control posts under name 'wake_interval_seconds' on /device with scripts blocked — with none, this helper measures nothing. The names that page does post are ['scope', 'return_to', 'wake_interval_s', 'notifications_topic_url', 'notifications_battery', 'notifications_silent', 'state']`

**Negative, a control that saves nothing** — simulated by reading back the
wrong key, which is byte-for-byte what a control whose POST never reaches
storage looks like from outside:

> `_persist_without_js: 'wake_interval_s' did NOT persist with scripts blocked — it was set to '900' and submitted (via the submitter), and the stored value still reads back as 'white' (the reloaded page shows '900'). A control that renders without scripts and saves nothing is the D-09 defect this helper exists to catch`

Note the parenthetical: **the reloaded page shows '900'** while nothing was
stored. That line is the decision above, printed.

**A real, current defect class, no mutation needed.** `wake_interval_group()`'s
own docstring records a live risk: an out-of-range value blocks submission of
the *entire* settings form, and `deploy/skypane.env.example` still ships
`SKYPANE_SLEEP_S=30`, under the 60 s floor. Asked to persist `7`:

> `_persist_without_js: '/settings' cannot be submitted with '7' in 'wake_interval_s' — native constraint validation rejects ['wake_interval_s: Value must be greater than or equal to 60.'], and a browser silently refuses to submit an invalid form rather than reporting an error`

`wake_interval_s` on disk: still `300`. Without that pre-check the browser
would have silently done nothing and the helper would have hung until
`expect_navigation()` timed out; instead the failure is instant and quotes
Chromium's own message.

**The write-only exception, measured in both directions.**
`notifications_topic_url` with the default:

> `_persist_without_js: 'notifications_topic_url' stored 'https://ntfy.sh/skypane-demo' but the reloaded /device does not show it back — the field reads '' with scripts blocked, so the saved setting is invisible to the visitor who made it`

and with `shows_back=False`, the same call passes on the disk verdict:
`{'reloaded': '', 'stored': 'https://ntfy.sh/skypane-demo2'}`.

### 2. `_operate_with_keyboard()` — keyboard only, pointer-freedom measured

**The load-bearing positive: arrow keys move selection in the existing runway
radiogroup with ZERO pointer events.** This is the native behaviour D16's
runway map and D5's carousel both inherit for free, so measuring it now is not
decorative:

```
{'selector': 'input[name="tracked_runway"][value="3"]', 'keys': ['ArrowDown'],
 'group': '06-24', 'active': '06-24', 'active_name': 'tracked_runway',
 'pointer_events': [], 'recorder_proved': 1}
```

Selection moved `3` → `06-24`; `pointer_events` empty; `recorder_proved: 1`
means the recorder caught its own verification event, so the empty list is a
measurement rather than a listener that was never alive. `['ArrowDown',
'ArrowDown', 'ArrowUp']` lands back on `06-24`, as a radiogroup should.

**The mutation the plan asked for: a click deliberately introduced.**
`_FOCUS_PROBE` was patched in-process so the helper focuses by pointing at the
control's centre first — the "happens to focus by clicking" defect:

> `_operate_with_keyboard: '#wake-interval-s' was driven with ['ArrowUp'] and 1 pointer event(s) fired during the sequence — ['mousedown:wake-interval-s(detail=0,pointerType=)']. A keyboard proof that a pointer took part proves nothing about a keyboard-only visitor`

Reverted, the identical call passes: `{'value': '302', 'pointer_events': [],
'recorder_proved': 1}`.

*The mutation was an in-process monkeypatch of the module constant rather than
an on-disk edit, deliberately: a sibling agent is executing 25-01 in this same
working tree, and a mutate/revert cycle on disk risks its `git commit` sweeping
a mutated file. The patch changes exactly the line an on-disk mutation would
have changed.*

**The instrument, proved in both directions against real trusted input.** Same
recorder, a real Playwright `locator.click()`:

```
['pointermove:…(detail=0,pointerType=mouse)', 'mousemove:…',
 'pointerdown:…(detail=0,pointerType=mouse)', 'mousedown:…(detail=1,pointerType=)',
 'pointerup:…', 'mouseup:…(detail=1,pointerType=)',
 'click:wake-interval-s(detail=1,pointerType=mouse)']
```

and immediately after, a keyboard `ArrowUp`: `[]`.

### 3. `_hit_area()` / `_assert_hit_target()` — the hit-tested element

**The ::before synthesis, measured rather than read off a CSS value.**
`[data-row-toggle]` on `/flights` at 1280 px — a 22 × 22 visual box whose
`::before` carries `inset: -11px`:

```
{'visual': (22, 22), 'hit': (45, 45), 'reach': (23, 21, 22, 22)}
```

**45 × 45, not 22 × 22** — the helper is measuring what the browser hit-tests,
not the rectangle. (On the +1: see "did not evaluate as predicted" below.)

**`exempt-by-delegation`'s precondition, both halves.** The bare runway radio
(`input.visually-hidden`, `clip-path: inset(50%)`) at 360 px:

> `_hit_area: 'input[name="tracked_runway"][value="3"]' measures [1.01, 1.01] but its own centre point hit-tests to 'runway-card runway-card--selected' instead — the control is not reachable by pointer where it is drawn …`

and its wrapping label, which is the precondition `control-density.md` records:

```
.runway-card  visual (88.26, 136.45)  hit (88, 138)  → clears 44 in both axes
```

**Negatives.** A selector matching nothing:

> `_hit_area: no element matched '.no-such-control' on http://…/flights — with none, this measures nothing`

A control inside a collapsed disclosure — a rect that is perfectly intact and a
control nobody can press:

> `_hit_area: '.copy-btn' measures [22, 22] but its own centre point hit-tests to 'mono' instead …`

`_assert_hit_target()` against a real under-floor measurement:

> `the Flights copy button: '#flight-detail-0 .copy-btn''s hit area measures 34x26 at 1280px, under the 44px floor in both axes (its visual box is 22.0x22.0 and it reaches (12, 21, 23, 2) pixels left/right/up/down of its own centre)`

### 4. `_assert_js_gate()` — both directions

**Against 25-01's own `.js-gate` rule**, with `prepare` rendering a wrapper
carrying that class into both pages so the stylesheet's rule is what gets
measured:

```
blocked: {'boxes': [[0, 0]], 'candidates': 1,
          'tab_steps': 24, 'tabbable_on_page': 45}
enabled: {'boxes': [[1280, 30]], 'revealed': 1, 'candidates': 1}
```

Zero height and **zero focusable descendants reached in a 24-step walk of the
real tab order** with scripts blocked (the wrapper holds 1 focusable candidate,
so the walk ran rather than short-circuiting); a real box with scripts on.

**Against `.dirty-bar`**, the live precedent for the same shape (hidden at
rest, revealed by dirty-state.js once the form is dirty), using `arm`:

```
blocked: {'boxes': [[0, 0]], 'candidates': 2, 'tab_steps': 24}
enabled: {'boxes': [[404.16, 64]], 'revealed': 1}
```

**Negative — the stuck gate, which a one-direction check passes on.** The same
call with no `arm`, so nothing ever reveals it:

> `_assert_js_gate: '.dirty-bar' never reveals on /device — every one of the 1 wrapper(s) still measures zero height WITH scripts running ([[0, 0]]). A gate asserted in the blocked direction alone passes against exactly this: an affordance hidden from everybody`

**Negative — an ungated wrapper.** The identical injected wrapper without the
class:

> `_assert_js_gate: '#demo-gate' occupies space with scripts blocked on /device — 1 of the 1 wrapper(s) measured [[1280, 30]]. The gate must hide by default and REVEAL under .js, never the reverse …`

**Negative — nothing matched:**

> `_assert_js_gate: no element matched '.no-such-gate' on /device with scripts blocked — the gated wrapper must be RENDERED and merely collapsed, so with none this helper measures nothing`

### Themes and overflow

The theme switch is **24-02's `_set_ui_theme()`**, not a new one.
`_in_both_themes()` is a generator that loops over it and adds nothing else, so
"assert this in both themes" is one `for` line. Measured on `/display` at
360 px:

```
[('light', 'rgb(247, 244, 239)', 'rgb(23, 25, 31)'),
 ('dark',  'rgb(12, 15, 20)',    'rgb(241, 243, 246)')]
```

The 360 px body-overflow measurement is **24-02's `_assert_no_page_overflow()`**
and this plan adds nothing beside it — a comment in the block records that it
is the call to use and why a second one would be a third convention about what
"the page" means.

---

## Things that did not evaluate as predicted

**1. A `click` is not a pointer event, and the first recorder was wrong about
the one behaviour this phase is built on.** Pressing ArrowDown inside a native
radiogroup moves the selection and, as part of the newly-selected radio's
*activation behaviour*, fires a real `click`. Logging `click` unconditionally
produced:

> `_operate_with_keyboard: 'input[name="tracked_runway"][value="3"]' was driven with ['ArrowDown'] and 1 pointer event(s) fired during the sequence — ['click:INPUT']`

That verdict is wrong, and a helper returning it would have taught this phase
to stop using the keyboard behaviour D16 and D5 depend on. The discriminator is
provenance, not the event's name: `click`/`dblclick`/`contextmenu` are logged
only when `detail > 0` or `pointerType` is non-empty; every genuinely
pointer-only event is logged unconditionally. Verified in both directions (see
the instrument proof above).

**2. Listeners registered through `page.evaluate` never fire in a
scripts-blocked context.** `window.__skypanePointerLog` is created, persists and
reads back — as `[]`, while a Tab walk really moves focus and an `el.click()`
really activates. `getComputedStyle` and CSS recalculation are not gated on
scripts (which is why 24-02's `_set_ui_theme()` works there), but listener
callbacks are. So the keyboard helper's self-test fails in that context and it
raises rather than returning a pointer-free verdict it cannot back up. This is
recorded in the helper's own docstring; scripts-blocked operability is
`_persist_without_js()`'s job.

**3. This file already had TWO `java_script_enabled=False` call sites, not
one.** `_no_js_page()`'s docstring claims the flag is kept to a single call
site so that "a scripts-blocked proof that quietly ran with scripts enabled
would pass while proving nothing" is *unavailable rather than merely unlikely*.
23-05's freshness check had opened a second one by hand, because it needs the
UI-language cookie set before the first navigation and the helper had no way to
take one. `_no_js_page()` grew a `cookies` parameter and that check was
converted back. `grep -n 'new_context(java_script_enabled'` now returns exactly
one line (863). *Four textual mentions of the token remain — three are prose in
docstrings and comments, so `grep -c` is 4; the call-site grep above is the one
that means anything.*

**4. `.copy-btn`'s real hit area is 34 × 26 in the Flights detail row, not
44 × 44.** The plan predicted ~44 × 44. Measured with the row expanded and
hovered (so `pointer-events: none`-at-rest is not the cause): the `::before` IS
reaching the hit test — every axis exceeds the 22 px visual box — but
neighbours inside `.flight-detail-row__grid` cover 12 of the 22 px available on
the left and 20 of the 22 below. The same class in the row toggle's position
measures 45 × 45, so the rule is fine and the placement is what eats it. Logged
to `deferred-items.md`; not fixed here (it is in `style.css` /
`history_page.py`, neither of which this plan owns, and it is pre-existing).

**5. The hit-area probe was wrong twice before it was right.** A fractional
binary search inflated every answer by ~1 px (a 312.0 px `<h1>` reported
312.97), which on a 44 px floor is the difference between passing a 43 px
target and failing it. Integer coordinates then over-reported by another pixel
on some boundaries. Sampling each pixel at its own centre is the version that
ships. It still reports up to ~1 px more than the CSS box where a box's edges
land off the pixel grid — **and that is the browser, not the probe**: those
pixels really do route a pointer to the control. The docstring says plainly not
to trust the last pixel, and to trust the difference between 22 and 44, which
is what the measurement exists to tell apart.

**6. The tab walk's first cycle detector stopped 24 stops into a 44-candidate
page** because it compared a name string and two different controls shared a
class. It marks the element now, which is identity.

**7. `.copy-btn` on `/flights` is `pointer-events: none` at rest on desktop**
(revealed on `tr:hover`/`tr:focus-within`, quick task 260903-peo). The helper
correctly reported it unhittable, and Playwright's own `locator.click()` times
out there too — so this is the app behaving as designed, not a defect, and the
occlusion message now names it as one of the three causes to check.

**8. The sibling agent's in-flight `companion/layout.py` 500'd every
authenticated page** for part of this execution (`TypeError: not all arguments
converted during string formatting` in `page_shell`). The demonstrations were
therefore run against an isolated `git archive` of the commit under
execution plus this plan's own file, which is the right subject anyway. The
final harness runs and the full-suite run were taken on the real tree after the
sibling's work had landed.

---

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 — missing critical functionality] `_no_js_page()` had a second
call site, breaking the invariant this plan is built on**

- **Found during:** Task 1, while checking the plan's own acceptance criterion
  (`grep -n 'java_script_enabled' … returns exactly one line`).
- **Issue:** the criterion could not hold — 23-05's freshness check opened a
  second `java_script_enabled=False` context by hand. The plan's binding
  constraint ("Compose with it; never open a second …") was already untrue at
  HEAD.
- **Fix:** `_no_js_page()` grew an optional `cookies` parameter applied before
  the sign-in navigation (the only order that works for a cookie the first
  rendered document must honour), and the check was converted back onto it —
  same viewport, same cookie, same sign-in, same landing route.
- **Files modified:** `companion/test_browser_ux.py`
- **Commit:** `78ec57c`

**2. [Rule 1 — bug] the pointer recorder rejected correct keyboard operation**

- **Found during:** Task 2, demonstrating against the runway radiogroup.
- **Issue:** a keyboard-activated radio fires a real `click`; logging it
  unconditionally reported the existing radiogroup as pointer-driven.
- **Fix:** provenance discriminator (`detail`/`pointerType`) on
  `click`/`dblclick`/`contextmenu`; every pointer-only event still logged
  unconditionally. Verified in both directions.
- **Commit:** `5c6739b`

**3. [Rule 1 — bug] the hit-area measurement was systematically inflated**

- **Found during:** Task 2. Fractional bisection reported 312.97 for a 312.0 px
  box; a +1 systematic bias on a 44 px floor is a check that passes a 43 px
  target.
- **Fix:** integer pixel counting, sampled at pixel centres, outward from the
  centre; plus `scrollIntoView({block: 'center'})` first, after
  `#wake-interval-s` was found reporting an occlusion by `tab-bar__pill` that
  depended purely on scroll position — an intermittently-red check is worse
  than no check.
- **Commit:** `5c6739b`

**4. [Rule 1 — bug] the tab walk stopped early on a name collision**

- **Found during:** Task 3. Identity marking replaced name comparison.
- **Commit:** `ec6f4ff`

### Additions beyond the written plan

**`prepare` hook on `_assert_js_gate()`** — runs on BOTH pages before
measuring. Added so the gate could be demonstrated against 25-01's real
`.js-gate` rule (which had landed as CSS, with no page rendering one yet),
satisfying that plan's own acceptance criterion that the rule be "re-asserted
in a real browser by 25-02's helper". It is also what a control plan will need
to open the disclosure a gated wrapper lives inside. Folded into the Task 3
commit.

**`shows_back` parameter on `_persist_without_js()`** — the DOM-corroboration
clause is wrong for `notifications_topic_url`, which is write-only by design.
The disk verdict is never optional.

### Nothing was ticked

CFG-46 … CFG-52 remain unticked; they belong to 25-08.

---

## Threat model

| Threat ID | Disposition | What was done |
|---|---|---|
| T-25-02-A | mitigate | `_persist_without_js()` restores the prior value as its last act, through the identical operate-submit sequence rather than a direct write to the state directory. Demonstrated: `wake_interval_s` 300 → 900 → **300**, `tracked_runway` '3' → '02-20' → **'3'**. Every helper runs in its own context; the file's per-check isolation is unchanged. |
| T-25-02-B | accept | `TEST_PASSWORD` unchanged, dev-only, never deployed. |
| T-25-02-SC | n/a | Zero packages installed. Playwright was already pinned in `server/requirements-dev.txt`. |

No new security surface: this plan touches one dev-only harness file and ships
no user-visible change.

---

## Commits

| Task | Commit | What |
|---|---|---|
| 1 | `78ec57c` | `_persist_without_js()`, `_persist_once()`, the three operate/submit/read probes; `_no_js_page(cookies=…)` and the second-call-site conversion |
| 2 | `5c6739b` | `_operate_with_keyboard()`, the self-proving pointer recorder, `_hit_area()`, `_assert_hit_target()`, `MIN_HIT_TARGET_PX` |
| 3 | `ec6f4ff` | `_assert_js_gate()` with `prepare`/`arm`, the tab-order walk, `_in_both_themes()`, the recorded pointer to 24-02's overflow helper |

`git diff --numstat 123b103 HEAD -- companion/test_browser_ux.py` → `933  15`.

---

## Known Stubs

None. Every helper is implemented and demonstrated against a live subject.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change.

## Self-Check: PASSED

- `companion/test_browser_ux.py` — FOUND
- `.planning/phases/25-.../25-02-SUMMARY.md` — FOUND
- `.planning/phases/25-.../deferred-items.md` — FOUND
- commit `78ec57c` — FOUND
- commit `5c6739b` — FOUND
- commit `ec6f4ff` — FOUND
- `ruff check .` — clean
- `companion/test_browser_ux.py` — 65/65, 0 FAIL, 0 SKIP, 2m56.0s
- `./scripts/run-all-tests.sh` — exactly the 5 baseline failures, by name
