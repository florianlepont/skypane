---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 07
subsystem: ui
tags: [javascript, switch, aria, fetch, optimistic-ui, rollback, progressive-enhancement, no-js-floor, absent-field-semantics, playwright, harness]

requires:
  - phase: 23-01
    provides: "--motion-fast, spent by the switch's two transitions and the toast's — a switch's in-flight state is the definition of motion somebody is waiting on"
  - phase: 23-02
    provides: "test_browser_ux.py's _no_js_page(viewport=...) helper and VIEWPORT_MIN_SUPPORTED; this plan is the first caller of the viewport parameter"
  - phase: 23-06
    provides: "layout.REFRESH_PENDING_ATTR and freshness.js's swap skip for a region carrying or containing it — shipped and proven from both directions before this plan had a marker to set"
  - phase: 22-05
    provides: "the absent-field regression guard for display_enabled/quiet_hours_enabled, EXTENDED here to led_enabled rather than duplicated, and the data-quick-switch handshake dirty-state.js keys on"
provides:
  - "layout.quick_switch_html(): the ONE write site for all three role=switch controls — server-rendered aria-checked, the posted state always its inverse, named by the setting through aria-labelledby, optionally cross-DOM through form="
  - "layout.quick_switch_state_html(): both state wordings server-rendered and translated with exactly one hidden — the mechanism that keeps quick-switch.js free of user-facing copy"
  - "layout.QUICK_SWITCH_CONTROL_ATTR / QUICK_SWITCH_REGION_ATTR / QUICK_STATE_ON_ATTR / QUICK_STATE_OFF_ATTR / QUICK_TOAST_ATTR / QUICK_SWITCH_FAILED_ATTR / QUICK_SWITCH_FAILED_TEXT"
  - "companion/static/quick-switch.js: the fourteenth script — capture-phase submit interception, optimistic flip, pending marker, rollback on both terminal branches, transient translated toast"
  - "app.py's content-negotiated /quick/* (303-with-flash for a form post, 204 for a fetch), send_no_content(), _wants_no_content(), and _handle_quick_toggle()'s per-route return_to whitelist"
  - "app.QUICK_LED_ROUTE + FLASH_KEY_LED_ON/OFF: the third quick route, one explicit led_enabled keyword, never a partial POST /settings"
  - "config_page.quick_led_form_html() / QUICK_LED_FORM_ID / QUICK_LED_LABEL_ID / QUICK_LED_STATE_ID"
  - "handle_post(): led_enabled absent -> None (unchanged), completing the symmetry across all three flags"
  - "style.css .switch/.switch__track/.switch__thumb, .settings-switch-row, .quick-toast"
affects: [23-08, 23-09, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "content negotiation on the REQUEST'S OWN header rather than a second route: the no-JS redirect stays byte-identical because a browser form post never sends the header that selects the other branch"
    - "the no-JS floor made STRUCTURAL rather than additive — the enhanced control IS the shipped form, and the script intercepts a submit that already works, so deleting the script is a working app rather than a dead control"
    - "both state wordings server-rendered with one hidden, so an optimistic flip and its rollback are a pure attribute change over already-translated text and a script carries no user-facing copy at all"
    - "semantics before control, in that commit order, so no commit in history has a control absent from a form while an absent field still means False"
    - "holding a fetch open from the harness (wrapping window.fetch in a promise released by hand) to make 'before the answer' a real moment with no sleep and no timing assumption"
    - "a per-route return_to whitelist PARAMETERISED rather than widened — a shared tuple would have let a crafted value on one route redirect somewhere that route has never redirected to"

key-files:
  created:
    - companion/static/quick-switch.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/i18n_fr/common.py
    - companion/i18n_fr/display.py
    - companion/test_companion_app.py
    - companion/test_config_page.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "The state span SURVIVES, visible and in the accessibility tree, as the switch's aria-describedby rather than as a second name or a second state claim. Quiet hours' state text carries the window (On - 23:00 to 07:00), which is real information a screen-reader user would lose to aria-hidden; the state itself has exactly one home, aria-checked; and the retired action wordings (Switch off / Eteindre) are gone from the markup entirely, because a role=switch named by an action announces an action and a state contradicting each other."
  - "Both state wordings are server-rendered with exactly one hidden, rather than the script rewriting text on flip. That is what makes quick-switch.js carry no user-facing copy and no second French wording, and it makes the rollback exactly symmetric with the flip - the same function with a different boolean."
  - "quick-switch.js listens in the CAPTURE phase on document and calls stopPropagation() on the one submit it takes over. dirty-state.js's own delegated listener disarms the unsaved-edits leave-guard for any [data-quick-switch] submit, which was correct while the switch navigated; with no navigation it would leave the guard down, and a form that was ALREADY dirty emits no further change event to re-arm it. Skipping the listener is the only fix available from this plan's files."
  - "A 204 and nothing else confirms. A 2xx that is not the negotiated no-content answer, a 4xx/5xx and the opaque redirect that redirect:\"manual\" produces all fall to the same rollback, because none of them is the server saying it saved."
  - "A rejected state value is never answered with a 204, even for a fetch. The client reads 204 as confirmation and would leave its optimistic flip standing, showing a state the frame is not in."
  - "The LED's return_to whitelist is its own single-member tuple (/device), not the strip's pair extended. Widening the shared tuple would silently let a crafted return_to=/device on /quick/display redirect somewhere that route has never redirected to."
  - "The toast is anchored at the TOP of the viewport. The bottom edge already carries two position:fixed components (.tab-bar z-index 20, .dirty-bar z-index 30) and stacking a third there would mean re-deriving their geometry; z-index 40 continues the declared order upward."
  - "The toast element is rendered empty on every page and is never hidden. A live region added to the accessibility tree at announce time is one screen readers routinely miss; opacity 0 plus pointer-events none keeps it invisible while leaving it in the tree, which visibility:hidden and display:none would not."
  - "D2's 300ms spinner clause is implemented as a pending state with NO fixed delay. A deliberate wait on a local request makes a fast action feel slow, and the pending marker is what the refresh loop actually needs."
  - "The fourth switch (notifications) is NOT built. Recorded as a finding below, per the developer's option-A decision on the ROADMAP and D-10's own stop-and-say-so precedent."

requirements-completed: []

duration: ~5h
completed: 2026-09-13
---

# Phase 23 Plan 07: D2 — three real switches Summary

**Screen, Quiet hours and the Diagnostic LED are now real `role="switch"`
controls that flip under the finger, post over `fetch`, hold their own region
still while the answer is outstanding and roll back visibly on a bad status, an
opaque redirect or a network failure alike — over the same `<form>`s the server
has always acted on, with `led_enabled`'s absent-field semantics fixed in the
commit before its control moved.**

## Performance

- **Duration:** ~5 h
- **Tasks:** 3/3
- **Files:** 1 created, 10 modified
- **Harness runtime:** `test_browser_ux.py` 109s → 127s (four new checks; the
  slowest is the scripts-blocked one, which drives six real navigations)

## Commits, in order

| # | Commit | Message |
|---|---|---|
| 1 (RED) | `2d8410e` | test(23-07): pin two real switches, a 204 for fetch and a translated toast before they exist |
| 2 (GREEN) | `a10b265` | feat(23-07): the strip's two switches flip under the finger and roll back when they cannot |
| 3 (RED) | `49576b1` | test(23-07): the absent-field regression guard now covers all three flags |
| 4 (GREEN) | `9d5fd06` | **fix(23-07): led_enabled resolves an absent field to unchanged, before its control moves** |
| 5 (RED) | `a19efd9` | test(23-07): pin the third switch and its route before the checkbox goes |
| 6 (GREEN) | `ab41dc5` | **feat(23-07): the Diagnostic LED is the third real switch, on its own route** |
| 7 | `53cf124` | test(23-07): a browser proves the flip lands early, comes back, and is not repainted |

**The semantics-before-control order is visible in the log**: commit 4 changes
`handle_post()`'s resolution and touches no markup; commit 6 removes the
checkbox. Between them the repository is in the only safe intermediate state —
a checkbox still rendered, and an absent field already meaning "unchanged",
which is harmless in that direction. The reverse order would have left a commit
where every unrelated settings save switched the physical LED off.

`git show --name-only` was run after every commit and each carries exactly the
files its message claims. No `git stash`, no `git clean`, no blanket
`git checkout --` over unstaged work.

---

## The three switches

**The markup, from one builder.** `layout.quick_switch_html()` is the single
write site for all three. It renders the `<form>` that already shipped (method,
action, the hidden `state` and `return_to` fields, `data-quick-switch`) with a
`<button type="submit" class="switch" role="switch" aria-checked="…">` inside
it, named by the setting through `aria-labelledby` and described by its state
text through `aria-describedby`. `aria-checked` and the posted `state` are both
derived from the SAVED value and are always each other's inverse — a switch
whose posted state did not invert would, with scripts blocked, re-assert the
state it is already in.

**The accessible name is the setting, never the action.** The four action
wordings (`Switch on`/`Switch off`/`Turn on`/`Turn off`, French `Allumer`/
`Éteindre`/`Activer`/`Désactiver`) used to be the button's visible text. A
`role="switch"` named that way announces "Éteindre, switch, on" — an action and
a state contradicting each other about one control. They are gone from the
markup, and `test_status_pages.py` asserts they are gone, so a later plan that
reintroduces one has to delete the check that forbids it. The constants survive
in `layout.py` with a comment saying exactly that.

**The state span survives, visible, as a DESCRIPTION.** Asked explicitly by the
plan, and answered in both languages: Screen reads `On`/`Off` (`Activé`/
`Désactivé` is not what it says — the catalogue's own `On`/`Off` entries are
used unchanged), Quiet hours reads `On — 23:00 to 07:00`/`Off`. The Quiet-hours
wording carries the WINDOW, which is real information; `aria-hidden` would have
cost a screen-reader user that window to avoid a mild verbosity, which is the
wrong trade. So the state has exactly one home (`aria-checked`) and the visible
wording elaborates rather than repeats.

**Both wordings are server-rendered, one hidden.** This is the decision that
keeps `quick-switch.js` free of user-facing copy entirely. The flip and the
rollback are then the same function with a different boolean, over text the
server already translated: there is no second wording living in a script to
drift, and no French reader watching a control fall back to English the moment
it is pressed. `hidden` is honoured with or without scripts, so a
scripts-blocked reader still sees exactly one state word.

## The server: content negotiation, not a second route

`_handle_quick_toggle()` gained exactly one branch. A request whose
`X-Requested-With` equals `quick-switch` gets `send_no_content()` — 204, no
body, no `Location`, `Cache-Control: no-store` and the full hardening-header
set. Everything else gets today's 303-and-flash, byte-identical. A browser form
post never sends that header, so the no-JS path cannot be taken away by this
branch existing.

Three properties are deliberate rather than incidental, and each has its own
assertion:

- **No `Location` on the 204.** `fetch()` follows a same-origin redirect
  silently by default and reports the final status; a 303 answered to a fetch
  would read as success to a client whose session had just expired. The client
  sets `redirect: "manual"` as well — both ends of that contract are
  deliberate.
- **A rejected `state` is never a 204.** The client reads 204 as confirmation
  and would leave its optimistic flip standing.
- **A failed save is never a 204 either.** It still redirects, so the client
  sees a non-OK status and rolls back.

The `return_to` whitelist, the `state` validation and the single explicit
keyword to `save_device_config()` are untouched: each is a recorded fix, and the
write happens identically in both shapes.

## `led_enabled`: the correctness trap, fixed first

`config_page.py`'s `handle_post()` resolved an absent `led_enabled` to `False`.
That was correct only while its checkbox was rendered. The plan ordered the fix
before the control moved, and the commit log shows it.

**Before → after, as recorded:**

| measure | before | after |
|---|---|---|
| `grep -c 'led_enabled' companion/pages/config_page.py` | 22 | 24 |
| the resolution branch | `if GROUP_LED not in in_scope: None / elif submitted is None: False / elif == LED_CHECKBOX_VALUE: True / else reject` | `if submitted is None: None / elif == LED_CHECKBOX_VALUE: True / else reject` |
| the docstring at the old `:3954-3958` | states the asymmetry verbatim | corrected in place: all three flags symmetric, and the two notification checkboxes named as the only fields that keep in-scope-absent-means-False, because their checkboxes are still rendered |

**The scope test went with it,** and that is a decision rather than a tidy-up: it
was load-bearing only while the absent branch resolved to `False`. With absent
meaning "unchanged" it can never change an answer, and a condition that cannot
change an answer is exactly the shape a later reader mistakes for a live rule.

**The existing check was EXTENDED, not duplicated.** 22-05's own
four-combination guard became an eight-combination guard over three flags: one
check, one place, three flags. It went RED with **exactly one failure**, quoted
from the run:

```
REGRESSION (T-22-16/T-23-25): a theme-only save flipped led_enabled from True
to False — the LED's control is a /quick/led switch now, so its absence from a
settings body means 'this form never had a way to change it', not 'the user
unticked a box' (D-12.1, 23-07-PLAN.md Task 2)
```

**The LED group holds nothing else.** Read before assuming, as the plan
required: `led_group()` is a heading, a caption, one checkbox and an error slot.
No second field needs Save, so Task 3's stop-and-record treatment did not apply
here.

**`scope_groups()`'s `SCOPE_ALL` and the screen registry are untouched.**
`GROUP_LED` still renders a group; it simply no longer submits through the
settings form. `_scope_groups_follow_the_screen_registry` passes unmodified.

## `/quick/led`, and the whitelist that was parameterised rather than widened

The LED switch lives on `/device`, which is not a member of
`_handle_quick_toggle()`'s `(HOME_ROUTE, DISPLAY_ROUTE)` pair. **Adding it to
that shared tuple would have silently let a crafted `return_to=/device` on
`/quick/display` redirect somewhere that route has never redirected to.** The
handler therefore takes its whitelist and its fallback as parameters, `None`
preserving the two existing routes exactly; `/quick/led` passes a single-member
tuple. The SHAPE — a small tuple, a membership test, a known-safe fallback,
never a prefix and never a URL parse (T-21-12/T-23-24) — is identical for all
three, and that is the part that must not be reinvented.

`do_POST()` gates it beside every other state change (T-23-23), and the harness
asserts a `GET /quick/led?state=on` 404s and writes nothing — `SameSite=Strict`
is this app's only CSRF control, so a GET-reachable write would have no defence
at all.

**The cross-DOM form.** `led_group()` renders inside `<form id="settings-form">`
and a `<form>` can never nest inside another — a browser silently drops the
inner one and the switch would submit `/settings` instead, which is precisely
the partial settings save T-23-25 is about. So `quick_led_form_html()` is an
EMPTY form rendered as a sibling after `</form>` closes, and the button reaches
it through `form="quick-led"` — the same idiom the save bar and the Send-a-test
button already use. A harness check asserts the position, not just the markup.

## `quick-switch.js`, and the two listeners it had to be checked against

Read before writing, the way `submit-guard.js`'s own header does it, and stated
in the new file's header:

1. **`dirty-state.js`** has a delegated document-level submit listener that
   disarms its unsaved-edits leave-guard for any `[data-quick-switch]` form —
   correct while the switch navigated, because the strip was itself applying the
   change the dialog would have warned about. With no navigation it would leave
   the guard down, and `updateBar()` only re-arms on the NEXT edit, so a form
   that was already dirty when the switch was pressed has nothing to re-arm it.
   **`quick-switch.js` therefore listens in the CAPTURE phase on document and
   calls `stopPropagation()` on the one submit it takes over.** `dirty-state.js`
   is not in this plan's `files_modified` and was not touched; this is the only
   fix available from this plan's own files, and it is the right one — neither
   listener has anything legitimate to do for a submission that is not
   happening.
2. **`submit-guard.js`** disables the submitting control from a zero-delay timer
   and already returns early when the submission was cancelled, so it would be a
   no-op here anyway. It is skipped for the stronger reason: with no navigation
   to replace the page, a disabled switch stays disabled forever. The in-flight
   guard is this file's own (the pending marker doubles as it) and clears in
   both terminal branches.
3. **`poll-cooldown.js`** owns one button on one page and never sees a
   `[data-quick-switch]` form.

**The pending marker is the whole of this plan's share of 23-06's contract.**
`var PENDING_ATTR = "data-pending";` — set on the region before the fetch,
removed in BOTH terminal branches. A harness check pins `quick-switch.js`'s
constant, `freshness.js`'s constant and `layout.REFRESH_PENDING_ATTR` equal in
one place, so a rename on any one side fails rather than silently disabling the
rule. `freshness.js` was not edited, and the swap worked exactly as 23-06 left
it.

**The rollback is pinned by shape as well as by behaviour.** The bracket form
`promise["catch"](…)` is required by a source check (a `.then()` with no catch
is 23-RESEARCH.md's Pitfall 5 by shape, and `catch` is reserved in ES3), and a
second clause requires at least three references to `rollBack(` — one
definition and BOTH call sites — because a rollback wired to only one terminal
branch is the optimistic switch that lies.

## How the scripts-blocked path was proven to SAVE

Not by rendering assertions. In a real Chromium context with
`java_script_enabled=False`, at the 360 px contract floor, in **both**
languages, for **all three** switches:

1. the control renders at all (a missing control is the first failure mode);
2. its `aria-checked` EQUALS the value on disk — the accessible state is
   server-rendered, so `role="switch"` is a description of what the button does
   rather than a promise the script keeps;
3. its bounding box clears 44 px in BOTH axes at 360 px;
4. it is clicked, a real navigation is awaited, and **`device_config.load_device_config()` is read from disk** and must differ from the
   value before the click;
5. the toast region still renders, inert and empty — there is no script, so
   there is nothing for it to announce, and the server's own flash is what tells
   this reader it worked.

The mutation that demotes the switch from `type="submit"` to `type="button"` —
literally "a control that renders and does nothing with scripts blocked", the
Phase 22 login-page defect — fails this check (and six others).

## The rollback proof and its control phase

An assertion that a switch *came back* is worthless against a switch that never
moves. So the rollback check opens with a **control phase** on a working
request: the same switch is clicked, must have moved, and the toast must still
be EMPTY (it announces failures only). Only then is the route broken.

Both terminal branches are exercised, in English and in French:

- **a 500** (`route.fulfill(status=500)`), and
- **a network-level failure** (`route.abort()`).

Each must restore `aria-checked` to the pre-click value, clear the pending
marker, leave the stored value alone, put the TRANSLATED generic sentence in the
toast, and make that toast actually visible (`getComputedStyle(el).opacity`
is not `"0"` — a live region nobody can see is half an announcement). The copy
is asserted to contain no `500`, no `http`, no `/quick/`, no `TypeError`
(V7/T-23-27).

## The race, asserted from the D2 side

23-06 proved its swap skips a `[data-pending]` region using a marker the harness
injected by hand. This is the same rule measured against the marker the SHIPPED
script sets — the half 23-06 could not reach.

A POST is held open, the switch flips, **focus is deliberately blurred off the
strip** (`freshness.js` ALSO skips the region holding the active element, and
with focus still on the button this check would have passed on a loop with no
pending rule at all), a refresh is forced, and:

- a control proves another region really was swapped in the same cycle;
- the strip's node identity survives, by expando;
- the optimistic `aria-checked` survives;
- then the held request is released, the marker is proven to clear, the strip is
  dirtied the same way, and a second refresh MUST now replace it.

This check is also anti-vacuous by construction in a second way: while the POST
is held the server still holds the OLD state, so the fetched strip genuinely
differs from the live one and `isEqualNode` cannot be what leaves it alone.

## Mutation testing

| # | mutation | result | message (quoted from the run) |
|---|---|---|---|
| M1 | the optimistic flip moved from before the fetch into the 204 branch | 42 → **40** | `aria-checked was still 'true' while the request had no answer — the flip is not optimistic, it is waiting for the server, which is the whole of what D2 asks for (23-07-PLAN.md Task 3)` (plus the race check's own control: `control: the switch did not flip, so nothing is pending`) |
| M2 | `rollBack(...)` deleted from the `["catch"]` branch | 42 → **41** | `lang=en, a network-level failure: aria-checked stayed at 'false' instead of rolling back to 'true' — an optimistic switch that keeps a state the server never accepted is a switch that lies (T-23-26)` |
| M3 | `region.setAttribute(PENDING_ATTR, "")` removed | 42 → **40** | `the strip was REPLACED while a flip was unconfirmed — the fetched document still carries the server's older state, so the switch would bounce back under the user's finger (T-23-26, the D1-races-D2 rule)` and `expected exactly one pending-marked region while the request is in flight, found 0 — this is the marker 23-06's swap skips and the only thing this plan owes that contract` |
| M4 | the switch demoted from `type="submit"` to `type="button"` | 42 → **35** | the scripts-blocked check fails with `TimeoutError … waiting for navigation until 'load'` — the control renders and does nothing, which is exactly the defect |
| M5 | `led_enabled`'s absent branch reverted to `False` (the RED run of commit 3) | config-page 235 → **234**, exactly one failure | `REGRESSION (T-22-16/T-23-25): a theme-only save flipped led_enabled from True to False` |

## Did any of my own checks fail the vacuity question?

Asked of every new check: *what would a wrong implementation do?* **Two failed
it, and both were caught before they landed** — not by review, by asking:

1. **The race check would have been vacuous with focus still on the switch.**
   After `page.click(switch)` the button holds focus, and `freshness.js`'s
   FOCUS skip (22-15's, not this plan's) would have left the strip alone for a
   reason that has nothing to do with `data-pending`. The check would have
   passed against a script that never set the marker at all. Fixed by blurring
   before forcing the refresh — and M3 confirms the fix: with the marker
   removed, the check now fails.
2. **"The flip already happened" is satisfied by a script that never fetches.**
   A control that flips its own attribute and talks to nobody would pass an
   order assertion perfectly, and it is a worse bug than the one the check is
   about. The check therefore asserts a request was genuinely issued
   (`window.__skypaneHeld` exists) AND that the stored value has not moved at
   that instant, before it reads `aria-checked`. M1 exercises both halves.

A third, smaller one was caught by the harness rather than by the question:
`data-quick-switch-control` **contains** `data-quick-switch` as a substring, and
a shipped check counting occurrences of the latter went from 2 to 4. The
attribute was renamed to `data-quick-control` rather than the check retargeted —
the check was right.

## Criteria that did not evaluate as predicted

Four, all recorded rather than adjusted away:

**1. `grep -c 'catch' companion/static/quick-switch.js` returns `3`, not `1`.**
The criterion says "at least 1", so it passes — noted because two of the three
are prose in comments explaining why the bracket form exists. The bracket-form
criterion (`grep -cE '\["catch"\]'`) returns exactly `1`, as predicted.

**2. Two shipped BROWSER checks asserted the switch NAVIGATES** — which is
precisely what D2 removes. `_strip_switch_navigates_without_the_leave_guard…`
(22-05/D-04) and T14's closing clause both timed out waiting for a navigation.
Retargeted in place, and the first is now **strictly stronger**: it asserts the
leave-guard is still ARMED after a switch applies on a page that still holds an
unsaved edit, which is the real hazard the conversion introduced and which the
original could not reach. It is also the check that proves the capture-phase
`stopPropagation()` is doing its job.

**3. Nine shipped string-harness pins encoded the pre-conversion markup or the
pre-conversion semantics.** Each retargeted in place with its reason recorded
beside it: the three-cell wrapper regex (the cells gained an attribute after
their class), the `data-quick-switch` occurrence count (the substring collision
above), `led_group()`'s `settings-checkbox`/input-sequence pin, the
section-caption position table's control marker, the LED heading's id (the
existing `heading_ids` map already had the shape), the hint-then-error
`aria-describedby` pin (now three ids, hint still before error, plus a new
no-error control clause), the whole-dict expectation for a theme+runway save,
the empty-form LED persistence pin (made two-directional — asserting only the
False direction would pass on a handler that hard-codes False), the scoped-save
carry-forward pin (plus a new clause proving an EXPLICIT value is still
honoured, which is what makes the other clause a statement about ABSENCE), and
the Device B1 browser round trip (the LED can no longer witness a save-bar
cycle; the wake-interval field does).

**4. `i18n` Check 2 found an orphan.** `"Enable diagnostic LED"` — the retired
checkbox's label — became a catalogue key no module produces. Deleted from
`companion/i18n_fr/display.py` with a comment saying why. The criterion list did
not predict this; the harness did.

## Deviations from Plan

**1. [Rule 3 — Blocking] `test_browser_ux.py` edited in Task 1, not only in
Task 3.** Task 1's conversion is what broke the two navigation-asserting browser
checks, so they were retargeted in the same commit that caused it rather than
left red across two commits. The file is in `files_modified`; only the task
attribution moved.

**2. [judgement] The `X-Requested-With` header NAME is not a module constant.**
It was one at first, and `i18n` Check 1 scanned it as untranslated user-facing
copy (`'X-Requested-With' (from app.py:constant:QUICK_FETCH_HEADER)`). Only
ALL-CAPS module-level assignments are scanned, so a rename would have dodged the
check — which is not a fix. The honest resolution is that **no HTTP header name
in `app.py` is a module constant** (`_send_hardening_headers()`'s four are all
written at their use site), so a lone exception was the drift. Only
`QUICK_FETCH_HEADER_VALUE` survives as a constant, and the harness asserts the
literal wire header, which is the stronger test anyway. **No test exception was
added.**

**3. [judgement] `var STATE_ON = "on"` was removed from `quick-switch.js`.** The
same scanner (Check 6) reads a bare lowercase word in an ALL-CAPS JS constant as
untranslated copy. These are wire values, not copy; they are written at their
two use sites with a comment saying exactly that.

**4. [judgement] `quick_switch_html()` gained a `form_id` keyword.** The plan did
not anticipate that one of the three switches cannot contain its own form. Given
a form id it renders the BUTTON only, cross-DOM through `form=`, and the caller
renders the matching empty `<form>` as a sibling — the established idiom, not a
new one.

**5. [judgement] `aria-describedby` takes an id LIST.** The LED switch passes its
state span AND the group's own caption, so converting that group did not cost it
the hint its checkbox carried through `_field_error_attrs(hint_id=…)`. With an
error present the anchor id joins as a third, hint still before error.

**6. [scope] `REQUIREMENTS.md` was not touched.** CFG-36 exists and its row
already records that the fourth switch is deliberately not built. Per standing
instruction, 23-11 closes it.

---

## FINDING: the fourth switch (notifications) is NOT built

D2 asks for four switches. This plan builds three and **stops** at the fourth,
following D-10's own precedent — *"if a plan finds [the named mechanism]
unworkable for a reason this context does not anticipate, it must say so and
stop rather than fall back to the rejected pattern."* The developer recorded the
same conclusion as option A on the Phase 23 ROADMAP entry (2026-09-13). In the
plan's own terms:

- **The mechanism is available.** A `/quick/notifications` route could
  read-modify-write the notifications dict, since `save_device_config()` takes
  `notifications` as a WHOLE-DICT replacement rather than a field-level merge
  (`server/device_config.py`). Nothing technical blocks it.
- **What is missing is a DECISION, not a mechanism.** The two checkboxes
  (`notifications_battery`, `notifications_silent`) share one card with the
  `notifications_topic_url` text field, which is saved through the settings form
  and governed by the save bar. Converting only the checkboxes produces a card
  where two controls apply instantly and one needs Save — a pattern no locked
  source covers, and `references/settings-page-patterns.md`'s
  one-caption-per-section and save-bar contracts do not anticipate it.
- **Converting the URL field too** would mean an instant-apply text input, which
  the save bar exists to avoid.
- **Leaving the checkboxes in the form AND adding switches** would be two
  controls for one setting — the exact defect X1/D-04 was written to remove.

`notifications_group()` is untouched: `git diff 52be571..HEAD --
companion/pages/config_page.py | grep notifications_group` returns nothing, and
`grep -c 'quick/notifications' companion/app.py` returns `0`. The two
notification checkboxes keep in-scope-absent-means-`False` **because their
checkboxes are still rendered** — which is exactly the condition that made that
resolution correct for `led_enabled` until this plan, and `handle_post()`'s
docstring now says so in those words.

Plan 23-11's coverage ledger carries this forward to the developer as an open
decision. **CFG-36's box is deliberately not ticked here.**

---

## Known Stubs

**None.** Every surface this plan claims is live IS live: all three switches
flip, post, confirm, roll back and persist — with scripts on and with scripts
blocked, proven in a real browser in both languages at 360 px. The toast is
rendered empty on every page by design and is not a stub: it is a live region
that must exist before it has anything to say.

## Threat Flags

None. Every trust boundary this plan crosses is in the plan's own threat
register (T-23-23 through T-23-28), and each has an assertion: the new
state-changing route is POST-only and session-gated with a GET-404 check; its
`return_to` is membership-tested against a single-member whitelist with six
hostile values exercised; the partial-write hazard is the eight-combination
absent-field guard; the optimistic-state hazard is the rollback and race checks;
the failure-message disclosure surface is asserted in both languages against
four internals; and the fourteenth script is same-origin with the CSP equality
check still green and no inline script, nonce or vendored library anywhere.

## Verification

| harness | result |
|---|---|
| `companion/test_companion_app.py` | **288/290** (281 → 288 new pin; the two documented WR-11 root-sandbox FAILs) |
| `companion/test_config_page.py` | **237/237** (235 → 237) |
| `companion/test_status_pages.py` | **284/285** (283 → 285; the documented `anomaly_active()` FAIL) |
| `companion/test_view_pages.py` | **146/146** (unchanged) |
| `companion/test_i18n.py` | **24/24** (unchanged) |
| `companion/test_contrast_check.py` | **43/43** (unchanged) |
| `companion/test_browser_ux.py` | **42/42** (38 → 42) |
| `scripts/run-all-tests.sh` | 3 failing harnesses, **exactly the documented baseline 5 checks** (4 × WR-11: two in `companion/test_companion_app.py`, two in `server/test_manual_resolutions.py`; 1 × `anomaly_active()` in `companion/test_status_pages.py`). Coverage **93%** (≥ 83) |
| `ruff check .` | clean |

Every `EXPECTED_CHECK_COUNT` was re-derived by RUNNING, not by arithmetic. **No
test exception was added anywhere.** The script count pin moved from 13 to 14 by
a deliberate in-place edit with a stated reason, and the new route is registered
in `companion/app.py` with its own constant, its own serve method and its own
`do_GET()` branch (there is no catch-all), proven by a real HTTP GET.

Acceptance greps, run literally:

```
grep -cE '=>|\blet |\bconst |innerHTML|insertAdjacentHTML|document\.write|eval\(' \
    companion/static/quick-switch.js   -> 0
grep -c 'catch' companion/static/quick-switch.js          -> 3   (criterion: >= 1)
grep -cE '\["catch"\]' companion/static/quick-switch.js   -> 1   (criterion: >= 1)
grep -c 'unsafe-inline\|nonce-' companion/app.py          -> 3   (unchanged)
grep -c 'quick/notifications' companion/app.py            -> 0
grep -c "'" companion/static/quick-switch.js  (backticks) -> 0
```

## Things the plan assumed that turned out otherwise

1. **`data-quick-switch-control` collides with `data-quick-switch`.** The plan's
   own `<key_links>` names `data-pending` and `data-quick-switch`; a child
   attribute built on the latter's name inflates a shipped occurrence count. The
   attribute is `data-quick-control`.
2. **The LED switch cannot contain its own form.** The plan says "the LED switch
   inherits the identical shape: a real form". It inherits the identical
   CONTRACT, but the form must be a cross-DOM sibling, because `led_group()`
   renders inside `<form id="settings-form">`.
3. **`_handle_quick_toggle()`'s fallback is not the first member of its
   whitelist.** The plan's "extend the whitelist by membership" reads naturally
   as widening the shared tuple; doing so would have changed `/quick/display`'s
   behaviour for a crafted value. The whitelist and the fallback are separate
   parameters.
4. **`dirty-state.js`'s leave-guard is a live hazard, not a coexistence
   footnote.** The plan's `<interfaces>` flags it correctly ("the guard must not
   re-arm for a change the switch is itself applying") but the harder half is
   the reverse: it must not stay DISARMED. Capture-phase `stopPropagation()` is
   the answer, and there is now a browser check for it.
5. **Holding a fetch from the harness must hold POSTs only.** Wrapping
   `window.fetch` wholesale also holds `freshness.js`'s refresh GET, which is
   the very refresh the race check has to land. Found by that check timing out.
6. **The fixed bottom tab bar intercepts a click on a switch at 360 px.** The
   scripts-blocked check centres each control before pressing it — which is also
   what a real thumb would do.

## Notes for later plans

- **23-08/23-09/23-10** may reuse `layout.quick_switch_html()` for any new
  instant-apply boolean. Two rules come with it: the control must BE a real
  form's submitter (a `form=` attachment counts), and the region holding it must
  carry `layout.QUICK_SWITCH_REGION_ATTR` or `quick-switch.js` returns without
  intercepting. Both are asserted.
- **23-10** owns the remaining D3 motion. `.switch__track`/`.switch__thumb` and
  `.quick-toast` already spend `var(--motion-fast)` through `transition`, not
  `animation`, so they add nothing to the keyframes budget and 23-01's guard
  does not see them — a plan that wants to animate a switch should extend those
  transitions rather than declare a keyframes block.
- **23-11** owns: ticking CFG-36 and rewriting its traceability row; recording
  the switch component, the toast and `.settings-switch-row` in `SKILL.md`
  (`references/control-density.md`'s touch-target register gains a
  met-directly 44×44 entry); carrying the notifications finding above to the
  developer as an open decision; and the human sweep — flip each of the three
  switches on a phone-sized window and watch the state change under the finger,
  stop the server and flip one and watch it come back and say so, and turn
  scripts off and flip all three confirming each still persists.
- **The toast's top-of-viewport anchor** is unoccupied today. A later plan that
  puts anything at the top centre of the viewport at `z-index >= 40` needs to
  check the collision.

## Self-Check: PASSED

```
FOUND: companion/static/quick-switch.js
FOUND: .planning/phases/23-.../23-07-SUMMARY.md
FOUND: 2d8410e  FOUND: a10b265  FOUND: 49576b1  FOUND: 9d5fd06
FOUND: a19efd9  FOUND: ab41dc5  FOUND: 53cf124
```
