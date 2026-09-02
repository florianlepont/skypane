---
phase: quick-260902-chc
plan: 260902-chc
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/pages/health_page.py
  - companion/static/style.css
  - companion/static/freshness.js
  - companion/test_status_pages.py
  - .planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md
autonomous: true
requirements: [QUICK-260902-chc]

must_haves:
  truths:
    - "This task REVERSES a standing decision that is written down in three places and enforced nowhere. 06.6.3-CONTEXT.md's D-12 says Health/Preview get 'an explicit Refresh action plus a stale-view warning ... no automatic background polling ... avoids new steady-state request volume'. `companion/static/freshness.js`'s own header restates it as a standing constraint in the imperative ('this file must never poll ... At most one deferred setTimeout, scheduled once'). `health_page.py`'s `_STALE_VIEW_BANNER_HTML` comment names freshness.js as the banner's sole consumer. A source read confirms NO harness gate enforces the no-timer rule on this file — the sibling ES5/forbidden-sink guards are scoped to nav-dropdown.js (test_companion_app.py), panel-lookup.js (test_companion_app.py) and dirty-state.js (test_config_page.py) by name, and freshness.js appears in the harnesses only as a served static route. So the reversal costs nothing mechanically and everything in legibility: the ONLY thing stopping the next reader from treating the new interval as a violation is the written reversal note this task ships."
    - "The reversal is partial and the boundary is the point. D-12's request-volume half is reversed for Health alone, at the developer's explicit choice after living with the manual-refresh pattern in real use. D-12's other half — 'keeps authoritative health severity server-computed only' — is NOT reversed and is in fact strengthened: the chosen mechanism regenerates the whole page server-side, so no severity is ever recomputed client-side, and freshness.js still computes no health verdict of any kind."
    - "Mechanism (a) — a Page-Visibility-gated `location.reload()` — is chosen over mechanism (b) — a fetch-and-patch soft refresh — on four source-grounded grounds, not on ease. (1) `health_page.py`'s own docstrings claim it is 'structurally impossible for the nav dot and the banner to disagree'; the nav dot is emitted by `layout.page_shell()`, OUTSIDE `render()`'s output, so any in-page patch would leave a stale nav dot beside a freshly-patched banner and break that invariant on screen, while a reload preserves it for free. (2) `battery-trend.js` captures `readout`, `readoutValue`, `readoutDetail` and `points` ONCE inside its IIFE with no re-init hook and no MutationObserver — replacing the battery section's DOM would leave a permanently dead chart (no hover, no tap, no arrow keys), a silent regression far worse than a stale chart. `list-filter.js` has the same shape over the registry rows, and would additionally discard the user's in-progress filter query. (3) A patch needs an HTML-writing sink; `innerHTML`/`fetch(`/`XMLHttpRequest` are banned by three separate existing harness guards in this repo, so (b) means writing a repo-first exception to a discipline that is currently absolute. (4) (b) is ~100 lines of new machinery in a codebase whose every other JS file is DOM-toggling only; (a) is ~40."
    - "Mechanism (a)'s real costs are named, mitigated where they can be, and accepted in writing where they cannot. `<details>` open state is NOT restored across a reload, so an open readings-history disclosure or an open Corroboration 'More details' would be slammed shut on every cycle — mitigated by an interaction-skip guard that suppresses the tick entirely while any `details[open]` exists on the page. Keyboard focus is destroyed by a reload — mitigated by the same guard covering a focused chart hit target, a focused `<summary>`, and a focused form field (the registry's filter input). Scroll position is restored by the browser on `location.reload()` (session-history scroll restoration), unlike a fresh navigation — recorded as a claim the live-browser pass must confirm per browser, not asserted. A screen-reader user's virtual cursor IS returned to the document start by a reload that fires while they are reading with focus on `<body>`; this is the one cost the guard cannot cover, and it is written into the code comment and handed to a live screen-reader pass rather than hidden."
    - "The interval is a named constant in the developer's own stated 30-60s band, justified against two real numbers already in this codebase: `server/poll_loop.py`'s `POLL_INTERVAL_S` is 30 (so a cadence at or below 30s can be guaranteed-redundant against the pipeline's own writes) and `health_page.py`'s `STALE_PIPELINE_WARN_S` is 180 (so the chosen cadence notices a newly-warn pipeline well inside a quarter of its own warn threshold)."
    - "The pill replaces the banner AND the Refresh link, and does so Health-only by construction. `layout.page_header(title, purpose, freshness_html, action_html)` carries a LITERAL CONTRACT paragraph in its own docstring pinning that signature — the parameter is NOT removed. A source read confirms `freshness_html=` has exactly one call site in the whole codebase (`health_page.py`); Settings, Airlines and History pass none. So changing only what Health passes into that slot is the Health-scoped removal, and `layout.py` is not edited at all."
    - "The pill is hidden-by-default via the native `hidden` attribute, and its stylesheet rule must carry an explicit `[hidden]` override or it renders permanently visible — the exact collision class `.dirty-bar[hidden]`'s own comment already documents in this file ('the author-stylesheet display above always beats the user-agent [hidden] rule regardless of source order'). This task's override deliberately hides by VISIBILITY rather than by display, so the pill's line box is reserved and revealing it causes no layout shift in the page header — the same reserved-space reasoning `.battery-readout`'s own min-height comment already established, applied to an element that now reveals itself every cycle rather than once."
    - "The pill carries no live-region role, and the reason is written down rather than left as an omission: an ARIA live region announces on CONTENT mutation, not on a visibility change, so a `role=\"status\"` pill whose text never changes would be silent anyway — and the page load the pill precedes is itself announced by every screen reader, making a second announcement redundant."
    - "The reveal is deferred by one short named timer before the reload, and that timer is load-bearing rather than theatre: a visibility change followed synchronously by `location.reload()` can begin navigation before the reveal is ever painted, so without the deferral the pill may never appear at all. What this delivers honestly is a pre-navigation indicator, not a fetch-duration indicator; the dwell-time version is mechanism (b), and the SUMMARY says so rather than letting the developer infer parity with the sketch."
    - "freshness.js reads the active element's class through `getAttribute(\"class\")`, never the property form — an SVG element's `className` is an `SVGAnimatedString`, not a string, which is the same class of reason `battery-trend.js`'s own comment gives for preferring `getAttribute()` over `dataset` on SVG. That same fact makes `battery-trend.js`'s `_toggleActive()` (which uses the property form on `.sparkline-hit` circles) worth INVESTIGATING and recording — but not fixing here; it is outside this task's stated scope boundary."
    - "`data-loaded-at` survives the reversal rather than being deleted, and gains a second job: it is the page's own load instant, so a tab returning to visible after a long hidden stretch can decide whether it owes an immediate catch-up refresh instead of waiting a full interval to stop showing a minutes-old page. freshness.js keeps its existing defensive parse-or-noop around it verbatim."
    - "`companion/static/freshness.js`'s header claim that 'today only Health/Preview' carry a `[data-loaded-at]` element is corrected in the same edit: Preview was retired in Phase 06.6.4.1 (merged into History, its route 404s by design per D-22/D-26), and `history_page.py`'s own comment already records that Preview's freshness apparatus was deliberately not ported."
    - "`companion/test_status_pages.py` passes with `EXPECTED_CHECK_COUNT` at its real on-disk baseline plus exactly 5, every check the reversal breaks retargeted IN PLACE, and Section 3's `_both_tabs_ok_end_to_end()` extended in place with a real HTTP fetch of the served freshness.js proving the running process hands a browser the new loop — not only that the on-disk file says so."
    - "`scripts/run-all-tests.sh` reports exactly one failing harness, `server/test_poll_loop.py` (the known, pre-existing, unrelated digest mismatch). No harness that passed before this task fails after it."
    - "The SUMMARY enumerates, separately and explicitly, the interactive behaviours that structurally cannot be settled by a source or HTTP-body assertion — the interval actually firing, the pause actually pausing, the catch-up actually catching up, the pill actually painting, the skip guard actually skipping, scroll actually surviving, and the screen-reader cost — because this is a polling loop and a visibility listener, not the markup/CSS surface the previous three Health quick tasks verified."
  artifacts:
    - path: "companion/pages/health_page.py"
      provides: "the `Updating…` pill constant and its markup in the page-header freshness slot, the retired stale-view banner constant removed with the reversal recorded at the removal site"
      contains: "data-refresh-pill"
    - path: "companion/static/style.css"
      provides: "`.refresh-pill`, its load-bearing `[hidden]` override hiding by visibility for a reserved line box, and the pill-scoped icon size override"
      contains: ".refresh-pill[hidden]"
    - path: "companion/static/freshness.js"
      provides: "the visibility-gated auto-refresh loop, the interaction-skip guard, the catch-up-on-return branch, the written D-12 reversal, and the corrected Preview reference"
      contains: "AUTO_REFRESH_INTERVAL_MS"
    - path: ".planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md"
      provides: "an appended SUPERSEDED note on D-12's own entry naming what replaced it, why, and what half of it still stands"
      contains: "260902-chc"
    - path: "companion/test_status_pages.py"
      provides: "5 new checks, the in-place retargets the reversal forces, the in-place live-HTTP extension, and EXPECTED_CHECK_COUNT at on-disk-baseline + 5"
      contains: "data-refresh-pill"
  key_links:
    - from: "style.css's `.refresh-pill[hidden]` rule"
      to: "`.refresh-pill`'s own display declaration — without the override the author stylesheet beats the user-agent `[hidden]` rule and the pill renders visible on every single page load, permanently. `.dirty-bar[hidden]`'s comment in this same file already documents this exact collision; Check 4 pins it rather than leaving it to the comment"
    - from: "freshness.js's interaction-skip literals (the disclosure element name, the form-field tag names, the chart hit-target class)"
      to: "`health_page.SPARKLINE_HIT_CLASS` and the `<details>`/`<input>` elements Health actually renders — the guard fails SILENTLY when it stops matching: nothing errors, the page just starts reloading out from under a user mid-interaction. Check 5 is the only thing that would notice"
    - from: "freshness.js's `[data-refresh-pill]` guard"
      to: "`health_page.py`'s pill markup — this script is one cached static asset served to every page, so the guard is what keeps the scope boundary structural rather than aspirational. Lose the attribute and Health silently stops refreshing; loosen the guard and every page starts"
    - from: "the written reversal in freshness.js and in 06.6.3-CONTEXT.md's D-12"
      to: "the absence of any harness gate on this file's no-timer rule — the constraint lives only in prose, so prose is the only place the reversal can be recorded, and an unrecorded reversal reads to the next reader as a violation of a rule still presented as current"
---

<objective>
Replace the Health page's manual Refresh link and "this view may be out of date" stale banner with a genuine light auto-refresh — a named-interval reload while the browser tab is visible, fully paused when backgrounded, showing a brief "Updating…" pill during each refresh. This is Option B from the validated Health Auto-Refresh Sketch, chosen by the developer over Option A.

| # | Change | Why |
|---|--------|-----|
| 1 | Health's header Refresh link → a hidden-by-default `Updating…` pill | The sketch's own affordance; the pill is what the refresh announces itself with, now that the refresh is not the user's own click |
| 2 | The stale-view banner (and its inline Refresh link) → removed | Its entire job was telling the reader the page had gone stale. A page that refreshes itself cannot go stale, so the banner would only ever be a lie |
| 3 | `freshness.js`'s deferred one-shot reveal → a visibility-gated refresh loop | The mechanism itself, with an interaction-skip guard and a catch-up-on-return branch |
| 4 | The D-12 reversal, recorded in three places | The constraint exists only in prose, so prose is the only place the reversal can live |
| 5 | `freshness.js`'s stale "today only Health/Preview" header claim | Preview was retired in 06.6.4.1 (D-22/D-26); corrected while editing this exact comment |

Purpose: give the developer the genuinely live monitoring page they asked for, and leave the next reader able to see that the standing decision was knowingly reversed rather than quietly broken.

Output: one new pill constant and markup plus one retired banner constant in `health_page.py`, two new stylesheet rules, a rewritten `freshness.js` loop, one appended SUPERSEDED note on 06.6.3-CONTEXT.md's D-12 entry, 5 new harness checks plus in-place retargets, and a SUMMARY that separates what the harness proved from what only a real browser can.

**Approach note — this is a deliberate reversal, and the whole value of doing it well is in the writing-down.** 06.6.3's D-12 chose the restrained pattern for a stated reason ("avoids new steady-state request volume"). That reasoning was not wrong; the developer has now lived with its result and wants the other side of that trade for Health specifically. `freshness.js`'s own header goes further than D-12 and states the no-polling rule as a standing constraint in the imperative voice, addressed to future editors. Reversing a rule written in that voice without answering it in the same voice, in the same file, is how a codebase's comments stop being trustworthy. Follow this session's established discipline — the `sketch-findings-skypane` skill marks every superseded value with an explicit `SUPERSEDED` token naming what replaced it and why — and apply it here, at the point of reversal.

**Mechanism decision, made from a real source read, with the losing option's genuine advantages stated.** Mechanism (a), a Page-Visibility-gated `location.reload()`, is chosen. Mechanism (b), a `fetch()`-based soft refresh that patches content in place, genuinely wins on two things and they are real: it can show a pill for the actual duration of the fetch, and it preserves scroll, disclosure and focus state by construction. It loses on four things this specific codebase makes decisive — the nav-dot/banner severity invariant `health_page.py` claims in writing and that only a whole-page regeneration preserves; `battery-trend.js` and `list-filter.js` both capturing their DOM once in a closure with no re-init hook, so any replacement of their regions leaves them permanently dead; the repo-wide, three-guard ban on the HTML-writing and network sinks a patch requires; and roughly 100 lines of new machinery against 40, in a codebase where every other script is DOM-toggling only. Task 2 records this decision, with (b)'s two genuine advantages named, inside `freshness.js` itself.

**Non-goals — verified, deliberately NOT touched.**
- **`layout.page_header()`.** Its docstring carries an explicit LITERAL CONTRACT paragraph pinning `(title, purpose, freshness_html, action_html)`. The `freshness_html` parameter stays; only what Health passes into it changes. A source read confirms Health is the sole call site passing it — `airlines_page.py`, `config_page.py` and `history_page.py` pass none — so this is already Health-scoped without touching the shared builder.
- **Every page other than Health.** freshness.js is one cached static asset served to all six routes; the new loop is gated on an attribute only Health emits. `test_view_pages.py` already asserts History carries no `data-loaded-at` and no stale-banner element — that check must still pass untouched, and is the proof the boundary held.
- **History's own freshness behaviour.** `history_page.py`'s comment already records that Preview's page-level freshness apparatus was deliberately not ported when Preview merged into History. That decision stands; nothing in History changes.
- **`companion/static/battery-trend.js` and `companion/static/list-filter.js`.** Not edited. Their closure-captured DOM is precisely the argument against mechanism (b), and the interaction-skip guard is what protects their state under mechanism (a) instead. Task 2 investigates one suspected pre-existing defect in `battery-trend.js` and ships no fix for it.
- **The battery chart, the readings disclosure, the registry card and the stats table as refresh targets.** Under a whole-page reload they all update for free; there is no per-region patch list to maintain and therefore no region that can silently fall off it.
- **`companion/layout.py` and `companion/app.py`.** No new script route, no new constant, no new icon. `icon-refresh` and `FRESHNESS_SCRIPT_ROUTE` both stay exactly as they are.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md

@companion/pages/health_page.py
@companion/static/freshness.js
@companion/static/style.css
@companion/test_status_pages.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Retire Health's manual Refresh affordance in favour of an updating pill</name>
  <files>companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py</files>
  <read_first>
    - `health_page.py`'s `_STALE_VIEW_BANNER_HTML` constant and the whole D-12/UXA-13 comment block above it, and `render()`'s `freshness_html` construction with its own comment. Read what both claim before removing either — this task reverses a stated decision, and the replacement comments have to say so honestly rather than reading as though the banner had been an accident.
    - `layout.page_header()` in full, including the LITERAL CONTRACT paragraph and the quick-task-260901-tsa paragraph describing the order the three optional blocks are concatenated in. Confirm for yourself that the freshness block is emitted before the purpose sentence, and that this function needs no edit at all for the pill to land where the Refresh link did.
    - Grep the whole `companion/` tree for `freshness_html` and satisfy yourself that Health is the only caller passing it. The Health-only scoping claim rests on that, not on the parameter being Health-specific — it is a shared parameter with one user today.
    - style.css's `.banner__pill` rule and the whole comment above it (which explicitly invites a third call site of the same visual primitive), plus `.airline-card__chip` further down the file. The pill's own declarations come from here rather than being invented.
    - style.css's `.dirty-bar` and `.dirty-bar[hidden]` rules and the comment between them IN FULL. It names the exact collision this task's pill re-creates, and names the two sibling cases in this file. Read it before writing the pill's own `[hidden]` rule — that comment is the precedent the new one has to answer, because this task deliberately hides by a different property and must say why.
    - style.css's `.icon` rule (a 20px square base) and the two `svg` collision comments near `.stat-tile svg` / `.battery-trend-section svg:not(.icon)`. They are the precedent for scoping an icon-size override to one component.
    - style.css's `.battery-readout` rule and its reserved-height comment — the no-layout-jump reasoning the pill's `[hidden]` treatment reuses.
    - `layout.ICON_IDS` and every use of `icon-refresh` across `companion/`. Then grep the harnesses for any check asserting that every `ICON_IDS` member is rendered somewhere. The pill keeps the refresh icon (which is why the existing five-`<use>` count check needs no retarget) — confirm that count against a real render rather than trusting this sentence.
    - The three harness checks this task will break or move, all in `companion/test_status_pages.py`: `_health_freshness_refresh_and_stale_banner_present()`, the page-purpose ordering check that does `rendered.index("freshness-refresh")`, and the four-icons check whose comment names the Refresh action as the fifth `<use>`. Grep as well for `data-stale-banner`, `freshness-refresh` and `out of date` across every harness in `companion/` so you find anything those three greps miss — `companion/test_view_pages.py` has its own History-side assertions that must keep passing unchanged.
  </read_first>
  <action>
**A. `health_page.py` — the pill constant and its markup.** Add a module-level constant holding the pill's visible copy, as a named constant rather than a literal in `render()`, so the harness can assert against the module's own value instead of re-typing the string. The copy is the English half of the sketch's bilingual label: this whole app renders `<html lang="en">` and a grep of `companion/` finds not one word of French anywhere, so the English label is the one that matches the shipped product. Record that reasoning beside the constant, so the sketch's other label reads as a considered choice rather than a dropped requirement. Use a single-character ellipsis, not three periods.

Rewrite `render()`'s `freshness_html` construction to emit the pill in place of the Refresh anchor. One element, an inline-level `<span>` (not a `<p>` — this sits inside `page_header()`'s `<div>` alongside an `<h1>` and a `<p>`, and an inline element is what an inline-flex pill wants), carrying, in this order: the class the stylesheet keys on, a bare marker attribute spelled exactly `data-refresh-pill` (freshness.js and Task 3's checks both key on that literal), the existing `data-loaded-at` attribute with `escape_html(now)` exactly as today, and the bare `hidden` attribute. Its content is `layout.icon_html("icon-refresh")` followed by the pill copy constant.

Keep `escape_html()` on `now` and only on `now`: it is real, request-scoped data. The pill copy is a static module constant and needs none, the same distinction the retired banner constant's own comment already drew.

Give the pill NO ARIA role, and write the reason down rather than leaving it as an omission: a live region announces on content mutation, not on a visibility change, so a status-role pill whose text never changes would be silent anyway — and the page load this pill precedes is itself announced as a navigation by every screen reader, making a second announcement redundant. In the same comment, name the real accessibility cost this mechanism carries and does not solve: a reload that fires while a screen-reader user is reading returns their virtual cursor to the top of the document, and the interaction-skip guard Task 2 adds cannot detect that state. Say that it is accepted, that the lever if it bites is the interval rather than the announcement, and that a live screen-reader pass is named in the SUMMARY.

**B. `health_page.py` — retire the stale-view banner.** Delete the `_STALE_VIEW_BANNER_HTML` constant and its concatenation in `render()`'s return expression. This removes the banner's own inline Refresh link along with it, which is the sketch's intent.

Do not delete the D-12 comment block that sat above the constant — replace it with the reversal record, at exactly the same place, so a reader who greps for D-12 in this file still lands on something. It has to say five things: what D-12 decided and the reason it gave; that the developer chose the opposite for Health after living with the manual pattern in real use; that the banner is retired because its whole job was reporting staleness and a self-refreshing page cannot go stale, so it could only ever have become a lie; that the request-volume half of D-12 is what was traded away, bounded by the tab-visibility gate so a backgrounded or closed tab costs nothing; and that D-12's OTHER half — authoritative severity stays server-computed — is not reversed but strengthened, because a whole-page reload regenerates every verdict server-side and freshness.js still computes no health state of any kind. Name `companion/static/freshness.js` as the place the mechanism and the fuller reversal record live.

**C. `style.css` — the pill's two rules.** Add `.refresh-pill` immediately after `.banner__pill`, so the two call sites of the same visual primitive sit together and the existing comment's "a future consolidation into one shared class is a mechanical edit" claim stays true rather than being quietly falsified by a third copy elsewhere in the file. Its declarations come from `.banner__pill`: the same inline-level flex box, the same centred alignment, the same height, horizontal padding, fully-rounded corners, small size, regular weight, and the same three `color-mix` background/border/foreground values. Add one declaration `.banner__pill` does not have — a small gap between the icon and the text — and drop `flex: none`, which exists there only because that pill is a flex child of a banner row and this one is not.

Then add `.refresh-pill[hidden]`, and hide it by VISIBILITY rather than by display. Comment it against `.dirty-bar[hidden]`'s own comment, which this deliberately diverges from: that comment is right that a higher-specificity `[hidden]` selector is REQUIRED whenever a component's base rule sets a display value — without it the author stylesheet beats the user-agent rule regardless of source order and the pill renders permanently visible on every page load. This rule satisfies that requirement and then makes one further choice: hiding by visibility keeps the pill's line box reserved, so revealing it shifts nothing in the page header. Say why that matters more here than for `.dirty-bar`: the dirty bar reveals at most once per editing session in response to the user's own keystroke, whereas this pill reveals itself on a repeating cycle with no user action, so a layout shift on reveal would be a recurring twitch in the header rather than a one-off. Name `.battery-readout`'s reserved-min-height comment as the same reasoning already shipped on this page. Note that visibility-hidden removes the element from the accessibility tree exactly as display-none does, so nothing about the no-role decision in part A changes.

Add one more rule scoping the icon's size inside the pill: `.icon`'s 20px square base equals the pill's whole height, so an unscoped icon would overflow its own container. Size it to fit and comment it as the same collision class the two `svg` comments elsewhere in this file already document — a component whose child inherits a base size the component cannot accommodate.

**D. Retarget the checks A and B break, IN PLACE.** No `EXPECTED_CHECK_COUNT` movement in this task.
- `_health_freshness_refresh_and_stale_banner_present()` is the D-12 check being reversed. Rewrite it in place as the reversal's own guard, and rename it accordingly. Keep what still holds: exactly one `data-loaded-at` page-wide, carrying the real request-scoped now value, and `page_header()` called exactly once. Replace what no longer holds with the negative half of the reversal, asserted against the RENDERED output rather than against the module source — assert the rendered page carries no stale-banner marker attribute, none of the retired banner's copy, and no Refresh-link class. Derive both retired literals from the pre-edit file (git will still have them) rather than re-typing them from this plan, and assert additionally that `health_page` no longer defines the retired banner constant at all. Update the check's description to state that it now pins a reversal.
- The page-purpose ordering check locates the header's Refresh affordance by the old class literal. Retarget that one lookup onto the pill's marker attribute and leave every other assertion in that check exactly as it is — the ordering property it tests (the header's action row precedes the purpose sentence) is unchanged by this task and must keep being tested.
- The four-icons check's five-`<use>` count: run it. It should still pass unchanged because the pill keeps the refresh icon. Update only its comment, which currently names the fifth `<use>` as the Refresh action, so it names the pill instead. If the count moved, find out why before changing the number.
- Fix anything else the `read_first` greps surfaced, in place, the same way.

After each of A through D, run `server/.venv/bin/python3 companion/test_status_pages.py` before moving to the next.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from companion.pages import health_page as h
from companion import layout
assert not hasattr(h, '_STALE_VIEW_BANNER_HTML'), 'the retired banner constant must be gone'
d = tempfile.mkdtemp(); r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
assert r.count('data-refresh-pill') == 1, 'exactly one pill, got %d' % r.count('data-refresh-pill')
assert r.count('data-loaded-at') == 1, 'exactly one data-loaded-at survives'
assert 'data-stale-banner' not in r, 'the stale-view banner must be gone from the rendered page'
assert 'freshness-refresh' not in r, 'the manual Refresh link must be gone from the rendered page'
start = r.index('data-refresh-pill')
tag = r[r.rindex('<', 0, start):r.index('>', start) + 1]
assert tag.startswith('<span'), 'the pill must be an inline element, got %r' % tag[:40]
assert ' hidden' in tag, 'the pill must carry the bare hidden attribute by default'
hdr = r[r.index('<div class=\"page-header\">'):]
hdr = hdr[:hdr.index('</div>') + 6]
assert 'data-refresh-pill' in hdr, 'the pill must sit inside the .page-header div'
assert r.count('<use') == 5, 'expected five icon uses (four Health signals + the pill), got %d' % r.count('<use')
assert r.index('data-refresh-pill') < r.index(layout.escape_html(h.PAGE_PURPOSE_TEXT)), 'pill precedes the purpose sentence'
print('markup ok')
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
base = s.index('.refresh-pill {')
pill = s[base:s.index('}', base)]
assert 'display: inline-flex' in pill, 'the pill is an inline-level flex box'
hid = s.index('.refresh-pill[hidden] {')
body = s[hid:s.index('}', hid)]
assert 'visibility: hidden' in body, 'the [hidden] override must hide by visibility to reserve the line box'
assert 'display' not in body, 'the [hidden] rule must not set display — that would collapse the reserved box'
assert s.index('.banner__pill {') < base, 'the pill joins .banner__pill, it does not precede it'
assert '.refresh-pill .icon' in s, 'the pill must scope the icon size — .icon is 20px, the pill is 20px tall'
print('css ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_companion_app.py</automated>
  </verify>
  <done>
Health's header carries one hidden-by-default `Updating…` pill in the slot the manual Refresh link occupied, keeping `data-loaded-at` and the refresh icon; the stale-view banner and its inline Refresh link are gone, with the D-12 reversal, the reason the banner could only have become a lie, and the untouched server-computed-severity half all recorded at the removal site. `layout.page_header()` is not edited and no other page's render changes. The stylesheet carries `.refresh-pill` beside `.banner__pill`, an `[hidden]` override that reserves the line box and explains why it diverges from `.dirty-bar[hidden]`, and a pill-scoped icon size. Every check the reversal broke is retargeted in place and all four companion harnesses pass at their unchanged `EXPECTED_CHECK_COUNT`s.
  </done>
</task>

<task type="auto">
  <name>Task 2: Turn freshness.js into a visibility-gated refresh loop, and write the reversal down</name>
  <files>companion/static/freshness.js, .planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md</files>
  <read_first>
    - `companion/static/freshness.js` in full, header comment included, before changing a byte of it. Four things in that header are load-bearing for this task and each has to be handled deliberately rather than overwritten: the D-12/UXA-13 attribution; the standing no-polling constraint stated in the imperative to future editors; the "authoritative severity stays server-side" constraint (which this task does NOT reverse); and the "today only Health/Preview" claim (which is stale and is corrected here).
    - The D-12 entry in `.planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md`, around line 38, in full. Note that D-12 makes two distinct claims joined by an "and" — one about polling and request volume, one about where severity is computed — and that only the first is reversed. The note you append has to be that precise, or it reads as reversing more than was reversed.
    - `.claude/skills/sketch-findings-skypane/SKILL.md` — find how it marks a superseded value and copy that shape exactly (the explicit token, what replaced it, why). That is the house format for this, established across this whole session, and the note should be recognisable as the same idiom rather than a fresh invention.
    - `companion/static/battery-trend.js` in full: its header charter, its closure-captured `readout`/`readoutValue`/`readoutDetail`/`points`, and `_toggleActive()`. The captured-once-with-no-re-init-hook shape is the concrete argument against mechanism (b) and belongs in the decision comment. `_toggleActive()` separately needs the investigation in part E.
    - `companion/static/list-filter.js` in full — the second closure-captured region, and the one that additionally holds user-typed state a soft refresh would discard.
    - `companion/static/dirty-state.js` and `companion/static/nav-dropdown.js` headers, for this codebase's established comment voice, its "standing constraints, not just a description of this version" idiom, and its ES5-safe subset rules. The rewritten header should read as a sibling of these, not as a different author.
    - `companion/static/copy-button.js`, the one existing timer user in this directory, for how a deferred timer is written and commented here.
    - `server/poll_loop.py`'s `POLL_INTERVAL_S` and `health_page.py`'s `STALE_PIPELINE_WARN_S` / `STALE_DEVICE_WARN_S`. The interval constant's justification is anchored to these real numbers, not to a round figure that felt right.
    - `health_page.py`'s `SPARKLINE_HIT_CLASS` value, `_registry_filter_bar_html()`'s search input, `_battery_section()`'s readings disclosure and `_corroboration_details_html()`'s disclosure. These four are exactly what the interaction-skip guard has to recognise; read them so the guard's selectors come from the real markup rather than from this plan's description of it.
    - The forbidden-sink and ES5-subset token lists this repo already maintains, by name rather than from memory: `companion/test_config_page.py`'s `_FORBIDDEN_SCRIPT_SINKS` tuple, and the `banned` tuple inside `companion/test_companion_app.py`'s nav-dropdown and panel-lookup guards. Task 3 asserts freshness.js against them, so read the real lists before writing any comment — a comment that spells one of those tokens verbatim will trip the guard that bans it.
  </read_first>
  <action>
**A. Rewrite the header comment as a reversal record.** Keep the file's identity paragraph (no build step, no bundler, no framework, ES5-safe subset, served by `companion/app.py`'s route) verbatim — none of that changed.

Replace the two standing-constraint paragraphs and the trailing page-list paragraph with, in this order:

*The reversal.* Name this quick task and use the same explicit superseded token the design skill uses. State what D-12 decided and the reason it gave. State that this file's own prior header went further, restating it as a standing constraint addressed to future editors, and that nothing in any harness ever enforced it — which is exactly why the reversal has to be legible here, in prose, since prose was the only enforcement. State that the developer chose the opposite for Health specifically, after living with the manual-refresh pattern in real use, accepting the request-volume trade for a genuinely live monitoring page.

*What was NOT reversed.* D-12's severity claim stands and is strengthened: the mechanism regenerates the whole page server-side, so no verdict is ever recomputed client-side and this file still computes no health state of any kind. The scope stands too: Health alone. The gate that makes that structural is the pill attribute this file requires before doing anything, not a promise.

*The mechanism decision, with the losing option's real advantages named.* Both candidates were considered against this codebase. State (b)'s two genuine wins first — a pill visible for the actual duration of a fetch, and scroll/disclosure/focus preserved by construction — so the record does not read as a strawman. Then state the four reasons (a) won: `health_page.py`'s own claim that the nav dot and the page banner cannot disagree, where the nav dot is emitted outside `render()` by `layout.page_shell()` and only a whole-page regeneration keeps them in step; `battery-trend.js` and `list-filter.js` each capturing their DOM once inside an IIFE with no re-init hook, so replacing either region leaves a dead chart or a dead filter with nothing failing; the HTML-writing and network sinks a patch requires being banned by three separate existing harness guards in this repo; and the size difference in a codebase whose every other script is DOM-toggling only.

*The accepted costs of (a), named rather than glossed.* Open disclosures do not survive a reload and keyboard focus is destroyed by one — both mitigated by the interaction-skip guard below, which suppresses a tick entirely rather than trying to restore state afterwards. Browsers restore scroll position on a reload through session-history scroll restoration, unlike a fresh navigation — record this as the expectation the live-browser pass confirms per browser, not as an established fact. And the one cost nothing here mitigates: a reload that fires while a screen-reader user reads with focus on the document body returns their virtual cursor to the top; the lever if that bites is the interval, and it is named in the SUMMARY for a live screen-reader pass.

*The corrected page list.* The guard below is still load-bearing because most pages carry no such element — but Preview no longer exists. It was retired in Phase 06.6.4.1 (merged into History, its old route 404s by design per D-22/D-26), and `history_page.py`'s own comment records that Preview's freshness apparatus was deliberately not ported. Health is the only page today.

**B. The constants.** Replace the retired threshold constant with two named constants, each with the same "a named constant, not a magic number" treatment the retired one had.

The refresh interval, in milliseconds, inside the developer's stated 30-60 second band. Justify the exact figure against two real numbers you read in `read_first`: `server/poll_loop.py`'s fixed 30-second pipeline cadence (a refresh at or below that can be guaranteed-redundant against the pipeline's own writes) and `health_page.py`'s 180-second pipeline warn threshold (so the page notices a newly-warn pipeline well inside a quarter of the threshold that defines it). Record the resulting steady-state cost in plain terms — at most one authenticated page render per interval per open, visible Health tab, and exactly zero from a backgrounded or closed one — since that number is the thing D-12 was protecting and a reader deserves to see it quantified rather than dismissed.

The pre-navigation reveal delay, also in milliseconds, small. Its comment must say why it is load-bearing rather than cosmetic: revealing the pill and calling reload synchronously can begin navigation before the reveal is ever painted, so without this deferral the pill may never appear at all. Say plainly what it does and does not deliver — a pre-navigation indicator, not a fetch-duration indicator; the old document stays painted for the length of the request, so on a fast local response the pill's total visible time is short, and the dwell-time version is mechanism (b).

**C. The guard, the loop, and the visibility gate.** Keep the file's existing shape: the IIFE, strict mode, the query for the loaded-at element, the defensive parse-or-noop around its value with its "no access to `parse_iso()`" comment kept verbatim. Change what it looks for: the second required element is now the pill, found by its marker attribute; when either is missing the file returns and does nothing, exactly as before. Keep that early return's existing load-bearing-not-defensive-noise comment and update only which elements it names.

Then add, keeping every construct inside the ES5-safe subset and using only DOM APIs already used in this directory:

*An interaction check* returning true when the user is mid-interaction with something a reload would destroy. Two conditions, both cheap. First, any open disclosure anywhere on the page — a reader with the readings history or Corroboration's details open is reading, and a reload would slam it shut. Second, the active element being a form field or a disclosure summary or a chart hit target, which covers a half-typed registry filter query, keyboard disclosure use, and arrow-key traversal of the battery chart. Read the active element's class through `getAttribute("class")`, never the property form, and comment why: an SVG element's class property is an `SVGAnimatedString` rather than a string, the same class of reason `battery-trend.js`'s own comment gives for preferring `getAttribute()` over `dataset` on SVG elements. Take the chart's class value from `health_page.SPARKLINE_HIT_CLASS`'s literal — Task 3 pins that cross-file literal, the same way an existing check already pins this literal for `battery-trend.js`.

Comment the guard with the consequence of it silently ceasing to match, because that is its whole failure mode: nothing errors, the page simply starts reloading out from under a user mid-interaction, and only the cross-file check would notice.

*A refresh action* that reveals the pill by clearing its hidden property and then reloads after the reveal delay. Reload with the no-argument form only. Comment that constraint explicitly and as a security property, not a style preference: the navigation target must never be readable from the DOM, so no URL-taking navigation form appears in this file at all and Task 3 asserts their absence — describe those forms by concept in the comment rather than spelling them, so the check that bans them cannot be tripped by the comment that explains them.

*Start and stop functions* over a single interval handle held in one variable, initialised to a null-ish sentinel. Starting must be a no-op when a handle already exists; comment that this is what stops repeated visibility toggles from stacking two or three intervals onto one page, which would show up as multiple reloads per cycle rather than as an error.

*The tick*: stop and return when the document is hidden (belt and braces — the visibility listener already stops it, and an interval that somehow survives must not fire in a background tab); return without refreshing when the interaction check says so, leaving the interval running so the next tick tries again; otherwise refresh.

*The visibility listener*: on becoming hidden, stop. On becoming visible, start, and then — only when the elapsed time since the page's own loaded-at instant already exceeds one interval, and the interaction check permits — refresh immediately rather than waiting a full interval. Comment why the catch-up branch exists: a tab returning after a long hidden stretch would otherwise sit showing minutes-old data for a full interval, which is precisely the failure the retired stale banner was invented to report, and it would be perverse to remove the banner and then reproduce its trigger condition.

*The initial start*, guarded on the document not already being hidden, so a page that loads in a background tab starts fully paused.

Keep the closing "no DOMContentLoaded wrapper is needed" comment verbatim — the deferred script tag reasoning is unchanged.

**D. Append the SUPERSEDED note to D-12 in `06.6.3-CONTEXT.md`.** Leave D-12's original sentence byte-identical; append the note after it, in the design skill's own superseded idiom. It must name this quick task, state that the no-automatic-polling half is superseded for Health only and what replaced it, state that the developer's own explicit choice after real use is the reason, and state that the severity half of the same decision is NOT superseded and still stands. Point at `companion/static/freshness.js` for the mechanism decision and its reasoning. Do not edit any other decision entry, and do not restructure the document.

**E. Investigate one adjacent suspicion; ship no fix for it.** While reading `battery-trend.js`'s `_toggleActive()`, notice that it reads and writes `el.className` on `.sparkline-hit` elements, which are SVG circles. Determine from the real source, and from a live check if you have any means to run one, whether that path actually works or whether the SVG class property makes it a no-op or a throw under this file's strict mode. Change nothing in that file — it is outside this task's stated scope boundary. Record the verdict in the SUMMARY as its own named finding: what you checked, what you concluded, the one-line change it would need if confirmed, and the fact that the chart's active-point highlight is the only visible symptom. If you conclude it is fine, say that plainly too. Do not manufacture a finding to look thorough, and do not fix it to look complete.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys, re; sys.path.insert(0, '.')
sys.path.insert(0, '.')
from companion.pages import health_page as h
js = open('companion/static/freshness.js').read()
assert js.count('\"use strict\"') == 1, 'exactly one strict-mode directive'
assert '260902-chc' in js, 'the reversal must name this quick task'
assert 'SUPERSEDED' in js, 'the reversal must use the house superseded token'
assert 'D-12' in js, 'the reversal must name the decision it reverses'
assert '06.6.4.1' in js, 'the stale Preview claim must be corrected with its retirement citation, not deleted'
assert 'D-26' in js, 'the Preview correction must cite the decision that retired it'
m = re.search(r'AUTO_REFRESH_INTERVAL_MS\s*=\s*(\d+)', js)
assert m, 'the interval must be a named constant'
ms = int(m.group(1))
assert 30000 <= ms <= 60000, 'interval %d ms is outside the chosen 30-60s band' % ms
for token in ('setInterval', 'clearInterval', 'visibilitychange', 'document.hidden',
              'location.reload', 'data-refresh-pill', 'data-loaded-at',
              'details[open]', 'getAttribute(\"class\")', h.SPARKLINE_HIT_CLASS):
    assert token in js, 'freshness.js must reference %r' % token
print('freshness.js contract ok (interval %d ms)' % ms)
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
js = open('companion/static/freshness.js').read()
for sink in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval(', 'fetch(', 'XMLHttpRequest'):
    assert sink not in js, 'forbidden sink reintroduced into freshness.js: %r' % sink
for nav in ('location.href =', 'location.assign', 'location.replace'):
    assert nav not in js, 'no URL-taking navigation form may appear in this file: %r' % nav
for es6 in ('let ', 'const ', '=>', '\`'):
    assert es6 not in js, 'ES5-safe subset broken by %r' % es6
print('sink + navigation + subset discipline ok')
" && server/.venv/bin/python3 -c "
ctx = open('.planning/phases/06.6.3-companion-per-page-redesign-config-health-history-airlines-p/06.6.3-CONTEXT.md').read()
i = ctx.index('- **D-12:**')
entry = ctx[i:ctx.index('\n\n', i)]
assert 'SUPERSEDED' in entry, 'D-12 must carry an explicit superseded marker'
assert '260902-chc' in entry, 'the note must name the quick task that reversed it'
assert 'no automatic background polling' in entry, 'the original wording must survive unedited'
print('CONTEXT note ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_companion_app.py && server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>
  <done>
`freshness.js` runs a named-interval refresh loop gated on the pill attribute and on document visibility, pauses by clearing its interval when the tab is hidden, refuses to fire while a disclosure is open or a form field, summary or chart point holds focus, catches up immediately on returning to a tab that has been hidden longer than one interval, and reveals the pill before navigating with the no-argument reload form only. Its header records the D-12 reversal with the house superseded token, names both mechanisms with the losing one's genuine advantages, lists (a)'s accepted costs including the one it cannot mitigate, and no longer names the retired Preview page. 06.6.3-CONTEXT.md's D-12 carries an appended note reversing exactly its polling half and explicitly not its severity half, with its original wording intact. No forbidden sink and no ES6 syntax entered the file. `battery-trend.js`'s SVG class-property suspicion is investigated with a written verdict and no code change.
  </done>
</task>

<task type="auto">
  <name>Task 3: Pin the auto-refresh contract, and hand off what only a browser can settle</name>
  <files>companion/test_status_pages.py</files>
  <read_first>
    - `companion/test_status_pages.py`'s `EXPECTED_CHECK_COUNT` and the whole provenance comment block above it — read the REAL on-disk value at execution time; this plan deliberately names no number.
    - The `check(name, fn)` helper at the top of `main()` for its return-tuple contract, and `_mkstate` / `_ctx` / `_iso` / `_now` / `_seed_device_health` / `_seed_meta` / `_seed_unresolved_prefixes` / `_seed_runway_events`.
    - The existing cross-file source guards this task's new checks extend: the one asserting `battery-trend.js` still references `BATTERY_READOUT_ID` and `SPARKLINE_HIT_CLASS`, and the CSS DOM-contract guards that locate a rule by its selector and assert declarations inside the sliced rule body. Both idioms are reused below; match their error-message style.
    - Section 3's `Harness` block and `_both_tabs_ok_end_to_end()` in full, including its existing in-place extensions and its real `STYLE_ROUTE` fetch. This task extends that same check again rather than adding a second live one, and the stylesheet fetch is the exact precedent for the script fetch added below.
    - `companion/app.py`'s `FRESHNESS_SCRIPT_ROUTE` and the pre-auth static-script handler, so the new fetch in Section 3 targets the real served route rather than reading the file a second time.
  </read_first>
  <action>
**Add exactly five checks, extend one in place, and bump the count.**

**Check 1 — the reversal is written down, in both places.** Read `companion/static/freshness.js` and the D-12 entry in `06.6.3-CONTEXT.md`. Assert, positively only: freshness.js names this quick task, carries the house superseded token, and names D-12; and the D-12 entry carries the same token and names this quick task while its original decision wording survives verbatim. Do not add any negative grep over prose in either file — a check that bans a phrase from a file whose comments discuss that phrase is a trap, and the honest assertion here is that the reversal is present, not that the old wording is absent. Fail with a message saying in words that an unrecorded reversal reads to the next reader as a violation of a rule still presented as current, which is the specific failure this check exists to prevent.

**Check 2 — the loop's own contract, from freshness.js's shipped source.** Assert the interval is a named constant, parse its numeric value out of the source, and assert it falls inside the 30-60 second band the developer chose — pin the band, not one magic figure, so a later tuning inside the band is not a false failure while a jump outside it is a real one. Assert the pause half is present (an interval is both set and cleared), the visibility half is present (a `visibilitychange` listener and a read of the document's hidden flag), the double-start guard is present, and the navigation is the no-argument reload form. Then assert the discipline that did NOT change: none of the forbidden sinks this repo already enumerates appear in this file, no URL-taking navigation form appears in it, and the ES5-safe subset still holds. Both existing token lists are function-locals inside their own harnesses (`companion/test_config_page.py`'s sink tuple and the ES5 token tuple inside `companion/test_companion_app.py`'s nav-dropdown guard), so they cannot be imported — copy each list from the real source you read in `read_first` rather than from this plan's prose, and note in the check's own comment which file each came from so a future edit to either can find its second copy.

Note the deliberate asymmetry, and say so in the check's comment: this file's timer ban is lifted, so `setInterval` and `setTimeout` must NOT appear in the banned list here even though the sibling nav-dropdown and panel-lookup guards ban them. That single difference is the whole reversal, and spelling it out is what stops someone re-adding them to this list for consistency. Fail with a message naming which half failed — the timer ban is the ONLY thing this task lifted, and everything else in that discipline is still in force.

**Check 3 — the pill's markup contract on a real render.** Render Health and assert: exactly one pill marker attribute; the pill is an inline element carrying the bare hidden attribute; it carries `data-loaded-at` with the real request-scoped now, exactly once page-wide; it carries the module's own pill-copy constant (referenced through the module, never re-typed); it sits inside the `.page-header` div; and it precedes the purpose sentence. Then assert the same page renders correctly in the state where the pill matters least and is most likely to be dropped — a fresh state directory with no readings at all — so the pill is proven unconditional rather than accidentally coupled to the battery chart's own render branch.

**Check 4 — the pill's stylesheet contract.** A stylesheet guard beside the existing CSS DOM-contract checks. Locate `.refresh-pill`'s rule body and assert it declares an inline-level flex display. Locate `.refresh-pill[hidden]`'s rule body, slicing strictly between its own braces so the comment above it cannot satisfy the assertion, and assert it hides by visibility and declares no display at all. Assert the pill-scoped icon size rule exists. Assert `.banner__pill` still precedes `.refresh-pill` in the file. Fail with a message stating in words that without the `[hidden]` rule the pill's own display declaration beats the user-agent hidden rule and the pill renders permanently visible on every page load — the exact collision `.dirty-bar[hidden]`'s comment already documents — and that a display declaration inside that rule would collapse the reserved line box and reintroduce the layout shift it exists to prevent.

**Check 5 — the cross-file DOM contract the skip guard depends on.** Seed a fixture rich enough that all three interaction surfaces actually render: at least two battery readings (so a chart and its hit targets exist), at least one unresolved prefix (so the filter input exists), and corroboration data (so its disclosure exists). Assert on that render that a disclosure element, a form input and the chart hit-target class are all genuinely present. Then assert that freshness.js's shipped source references each of the corresponding literals, including `health_page.SPARKLINE_HIT_CLASS`'s value read from the module rather than typed. Fail with a message saying explicitly that this guard's failure mode is silence: when the skip guard stops matching, nothing errors and no other check moves — the page simply begins reloading out from under a user mid-interaction.

**In-place extension — the live-HTTP check.** Extend Section 3's existing `_both_tabs_ok_end_to_end()` rather than adding a new one (no count change). For the `/health` response body only, assert the pill appears once carrying its hidden attribute and that the retired stale-banner marker appears zero times — the automated half of "the running service really serves the reversal", a real subprocess, a real login, a real seeded database, a real HTTP response. Then, beside the existing `STYLE_ROUTE` fetch and following its exact pattern, fetch `companion/app.py`'s freshness-script route from the same running service and assert the served body carries the interval constant's name and the visibility listener registration — proving the process hands a browser the new loop, not only that the on-disk file says so. Update the `check(...)` description to say what it now proves.

**Falsifiability pass.** Before finalising, mutate all five new checks at once so each asserts on a name that does not exist in the source it reads, run the harness, and confirm the output reports exactly those five as FAIL and nothing else. Then restore them. A check that cannot be observed failing is not a check.

**Count bump.** Read the current on-disk `EXPECTED_CHECK_COUNT` and set it to that value plus exactly 5. Do not carry a number over from this plan text. Extend the provenance comment block above it with one new entry in that block's own established format: name this quick task, list the five checks added, and record that Tasks 1 and 2's retargets and this task's live-HTTP extension were all in place with no count change.

**Full suite.** Run `scripts/run-all-tests.sh`. The only harness in its FAILED list must be `server/test_poll_loop.py` — the known, pre-existing, unrelated digest mismatch. If any other harness fails, or the coverage gate reports a new shortfall, stop and fix it before finishing; do not record a green result over a new failure.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py && test "$(server/.venv/bin/python3 companion/test_status_pages.py | tail -1 | sed 's#.*: \([0-9]*\)/\([0-9]*\).*#\1-\2#')" = "$(grep '^EXPECTED_CHECK_COUNT = ' companion/test_status_pages.py | sed 's/.*= //' | awk '{print $1"-"$1}')" && scripts/run-all-tests.sh > /tmp/skypane-chc-run-all-tests.log 2>&1; test "$(sed -n '/FAILED harnesses/,$p' /tmp/skypane-chc-run-all-tests.log | grep -c '^    - ')" = 1 && sed -n '/FAILED harnesses/,$p' /tmp/skypane-chc-run-all-tests.log | grep -q 'server/test_poll_loop.py'</automated>
    <human-check>
REQUIRED, not optional, and a LARGER surface than the previous three Health quick tasks. Those were markup and CSS changes whose rendered result an HTTP body assertion could largely settle. This one ships a polling loop, a visibility listener and a transient reveal — behaviour that by construction leaves no trace in any response body, because every single thing it does happens after the response has been served. Assume, as with quick tasks 260901-tsa, 260901-uzi and 260902-bl2, that this task's executor has no browser-automation tooling bound to it and that this pass is handed to the orchestrating session. Do NOT block plan completion on it.

The automated halves are already covered and are NOT optional: Check 2 pins the loop's shape in the shipped source, Check 5 pins the cross-file literals its skip guard depends on, and Section 3's extension proves a real running service serves both the pill markup and the new script body over real HTTP. Read those assertions when they pass and record in the SUMMARY what the served response and the served script actually contained.

The behaviours a source or HTTP-body assertion structurally cannot settle, all of which the SUMMARY must list as outstanding, with the browser's own network panel open throughout:
1. The interval actually fires. Leave `/health` open and focused and confirm the page really does reload on the chosen cadence — that a request appears in the network panel roughly once per interval, not never, not twice.
2. Backgrounding actually pauses it. Switch to another tab for several minutes and confirm ZERO requests for `/health` during that time. This is the whole request-volume argument the reversal rests on; if it is wrong, the reversal is a worse trade than it was sold as.
3. Returning actually catches up. Come back to the tab after longer than one interval and confirm a refresh happens immediately rather than after a further full interval.
4. No stacking. Toggle away and back five or six times in a row, then watch one full interval and confirm exactly ONE reload happens, not three. A stacked interval is the specific failure the double-start guard exists to prevent and the only way to see it is to count.
5. The pill actually paints. Watch the header across a refresh and confirm the pill visibly appears before the page changes. Also confirm the header does not shift when it appears — the reserved line box is the reason for the visibility-based hiding and is the thing most likely to be wrong.
6. The pill is hidden at rest. On a freshly loaded page, confirm no flash of visible pill and no pill visible while idle.
7. The skip guard actually skips, in all three of its cases, each observed for at least one full interval: with the readings-history disclosure open; with Corroboration's "More details" open; with text typed into the registry's filter input; and with keyboard focus on a battery-chart point after arrowing to it. In each case, confirm no reload happens — then close/blur and confirm refreshing resumes.
8. Scroll survives. Scroll well down the page, wait for a refresh, and report whether the position is preserved. Do this in BOTH Safari and a Chromium browser: the plan records browser scroll restoration as an expectation, not a fact, and this is where it is settled.
9. The nav dot stays in step. This is the invariant that decided the mechanism. Watch the sidebar Health tab's notification dot across a refresh where severity changes and confirm it moves with the page's own banner and tile borders.
10. A screen-reader pass. With VoiceOver or equivalent, read partway down the page, let a refresh fire, and report where the cursor lands and how disruptive it is. This is the one accepted cost the guard cannot cover, and the developer's judgement on it decides whether the interval needs lengthening.
11. No console errors across several cycles, and no unexpected logout — a reload against an expired session correctly lands on the login page, which is fail-closed and right, but should be seen rather than assumed.
12. Perceptual: does a page that replaces itself on this cadence read as calm and live, or as twitchy? This is a judgement the developer owns, and the lever is the interval constant, which is a one-line change.

Record what was actually observed rather than restating this list as if performed, and stop any service started for the pass and delete its tmpdir afterwards.
    </human-check>
  </verify>
  <done>
`companion/test_status_pages.py` passes with every check green, its printed total equals the new `EXPECTED_CHECK_COUNT`, and that value is the real on-disk baseline plus exactly 5. The provenance block records this task's five additions and the in-place retargets and live-HTTP extension as no-count-change edits. Each new check was observed failing under mutation before being restored. `scripts/run-all-tests.sh` lists exactly one failing harness, `server/test_poll_loop.py`. A real `companion/app.py` process served a `GET /health` carrying the hidden pill and no stale-banner marker, and a real fetch of the freshness-script route carrying the new loop. The SUMMARY records both what those responses contained and the full, explicit list of interactive behaviours still outstanding for the orchestrating session's browser pass — plus the `battery-trend.js` SVG class-property verdict from Task 2, recorded as its own finding.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> `GET /health` | Server-rendered HTML reaching an authenticated operator's browser. The one new dynamic value in this task's markup is `now`, interpolated into `data-loaded-at` through `escape_html()` exactly as it was on the retired Refresh link. The pill's copy is a static module constant. |
| `freshness.js` -> the network | New: this file now originates requests on a timer. Every request is a same-document reload of the already-authenticated page the user is looking at; the navigation takes no argument and no URL is ever read from the DOM. |
| browser tab lifecycle -> the refresh loop | New: the Page Visibility API is the gate that bounds request volume. A backgrounded or closed tab must produce zero requests, which is the property the reversal's cost argument rests on. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-chc-01 | Denial of Service | The new refresh loop's steady-state request volume — the exact cost 06.6.3's D-12 was written to avoid | medium | mitigate | Bounded on three axes and each is pinned. The cadence is a named constant Check 2 asserts inside the developer's own 30-60s band, so a later edit cannot silently make it 1s. The visibility gate means a backgrounded or closed tab costs zero, and the loop is stopped (interval cleared) rather than merely skipped. The scope gate is the pill attribute only Health emits, so the loop cannot spread to five other routes. Worst case is one authenticated page render per interval per open, visible Health tab, on a single-household service; Task 2 requires that figure be written into the file rather than left for a reader to compute. The live-browser pass verifies the pause empirically, since a gate that does not actually gate turns this from medium into the thing D-12 feared. |
| T-chc-02 | Elevation of Privilege / Tampering | The reload's navigation target | low | mitigate | The reload uses the no-argument form only. Task 2 forbids any URL-taking navigation form in this file and Check 2 asserts their absence, so no DOM-supplied string — including anything an attacker could influence into an attribute — can ever become a navigation target. This is a DOM-based open-redirect class that a `location.href = someAttribute` implementation would have opened; the plan closes it by construction rather than by review. |
| T-chc-03 | Tampering (XSS) | The pill markup and the retired banner | low | mitigate | No HTML-writing sink is introduced anywhere. `freshness.js` still writes no content at all — it toggles one boolean property and calls one no-argument method. Check 2 asserts the whole forbidden-sink family this repo already enumerates is still absent from the file, so 06.5-RESEARCH.md's ASVS V5 reasoning ("this file needs no escaping function at all") holds unweakened. The pill's only dynamic value is `now`, escaped at interpolation exactly as the affordance it replaces did. |
| T-chc-04 | Denial of Service | Interval stacking across repeated visibility toggles | low | mitigate | One handle, one null-ish sentinel, a start that is a no-op when a handle exists, and a stop that clears and resets it. Check 2 pins the guard structurally; the live pass counts reloads after six toggles, which is the only way a stacked interval is actually observable. |
| T-chc-05 | Denial of Service | Accessibility and interaction regressions caused by a page replacing itself | medium | mitigate | The interaction-skip guard suppresses a tick entirely while any disclosure is open or while a form field, summary or chart point holds focus — covering the readings history, Corroboration's details, a half-typed registry filter, and arrow-key chart traversal. Check 5 pins the cross-file literals the guard depends on, because its failure mode is silence rather than an error. The one case the guard cannot detect — a screen-reader user reading with focus on the document body — is named in the code comment as an accepted cost with the interval as its lever, and is item 10 of the live pass rather than being left undiscovered. |
| T-chc-06 | Information Disclosure | A pill that renders permanently visible because its `[hidden]` override is missing or later removed | low | mitigate | Not a data-disclosure risk, an integrity-of-the-UI one: the page would claim to be updating at all times. This repo has already shipped this exact collision once (`.dirty-bar[hidden]`, with a comment saying so). Check 4 pins both halves — that the override exists, and that it declares no display value, which would collapse the reserved line box and reintroduce the header shift it exists to prevent. |
| T-chc-07 | Repudiation | A standing constraint reversed without a record | medium | mitigate | The no-polling rule is enforced by prose alone — a source read confirms no harness gates it — so prose is the only place the reversal can be recorded, and an unrecorded reversal is indistinguishable from a violation. The reversal is written at all three points where the old rule is stated (`freshness.js`'s header, `health_page.py`'s removal site, and 06.6.3-CONTEXT.md's D-12 entry) using the house superseded idiom, and Check 1 asserts two of the three are present so a later refactor cannot quietly drop them. |
| T-chc-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install of any kind. This task edits one Python module, one stylesheet, one JavaScript file, one harness and one planning document — all stdlib-only, no dependency change. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 companion/test_status_pages.py` — all checks pass; the printed total equals the new `EXPECTED_CHECK_COUNT`, which is the real on-disk baseline plus exactly 5.
2. `companion/test_view_pages.py`, `companion/test_config_page.py` and `companion/test_companion_app.py` — all pass at their own unchanged `EXPECTED_CHECK_COUNT`s. `test_view_pages.py` in particular still asserts History carries no loaded-at attribute and no stale-banner element, which is the proof the Health-only boundary held.
3. `scripts/run-all-tests.sh` — exactly one harness in the FAILED list, `server/test_poll_loop.py` (known pre-existing digest mismatch). Coverage gate reports no new shortfall.
4. `git diff --stat` touches only `companion/pages/health_page.py`, `companion/static/style.css`, `companion/static/freshness.js`, `companion/test_status_pages.py` and `06.6.3-CONTEXT.md`. `companion/layout.py`, `companion/app.py`, `companion/static/battery-trend.js` and `companion/static/list-filter.js` do not appear, and no page module other than Health does.
5. `git diff companion/static/style.css` shows exactly three added rules — `.refresh-pill` after `.banner__pill`, its `[hidden]` override, and the pill-scoped icon size — with no other rule's declarations changed and no new custom property or token introduced.
6. `git diff companion/static/freshness.js` shows a rewritten header carrying the reversal, two named constants replacing one, the new guard/loop/listener, and no forbidden sink, no URL-taking navigation form and no ES6 syntax anywhere.
7. `git diff .planning/phases/06.6.3-.../06.6.3-CONTEXT.md` touches D-12's entry only, appends rather than rewrites, and leaves the original decision wording byte-identical.
8. Section 3's extended `_both_tabs_ok_end_to_end()` passed — a real `companion/app.py` subprocess, a real login, a real seeded database, a real `/health` response carrying the hidden pill and zero stale-banner markers, and a real fetch of the freshness-script route carrying the new loop — and what those responses actually contained is written into the SUMMARY.
9. The SUMMARY names, explicitly and separately, the twelve interactive behaviours the harness cannot settle, and records the `battery-trend.js` SVG class-property investigation as its own finding with a verdict and no code change.
</verification>

<success_criteria>
- Health refreshes itself on a named interval while its tab is visible, does nothing at all while it is backgrounded, catches up on return, and shows a brief `Updating…` pill in place of the retired manual Refresh link and stale-view banner.
- The reversal of 06.6.3's D-12 is recorded in the house superseded idiom at all three points where the old rule is stated, is precise about reversing the polling half and not the severity half, and is scoped in writing to Health alone.
- The mechanism decision is recorded with the losing option's genuine advantages stated, and the four source-grounded reasons the chosen one won — including the two closure-captured scripts and the nav-dot invariant that make an in-place patch actively dangerous in this codebase.
- Mechanism (a)'s real costs are named rather than glossed: disclosures, focus and the screen-reader cursor, with the first two mitigated by the interaction-skip guard and the third accepted in writing with its lever named.
- `layout.page_header()`'s literal contract is untouched, `battery-trend.js` and `list-filter.js` are not edited, and no page other than Health gains any refresh behaviour.
- The pill's `[hidden]` override exists, hides by visibility so the header does not shift on a repeating reveal, and is pinned by a check rather than by a comment.
- The only discipline this task lifts on `freshness.js` is the timer ban; the forbidden-sink family, the no-URL-taking-navigation rule and the ES5-safe subset are all still in force and all still asserted.
- Every check the reversal breaks is retargeted in place; none is deleted.
- `EXPECTED_CHECK_COUNT` moved to the real on-disk baseline plus exactly 5, with the retargets and the live-HTTP extension recorded as no-count-change edits.
- `scripts/run-all-tests.sh` shows only the pre-existing `server/test_poll_loop.py` failure.
- `freshness.js`'s header no longer names the retired Preview page as a live consumer.
- The `battery-trend.js` SVG class-property suspicion is investigated and left OPEN with a written verdict and no speculative fix — not quietly closed and not quietly dropped.
</success_criteria>

<commits>
Focused and atomic, matching this session's established style (`git log --oneline -10`), referencing the quick task id rather than a phase-plan number:
- `feat(quick-260902-chc): replace Health's manual Refresh with an updating pill`
- `feat(quick-260902-chc): auto-refresh Health while its tab is visible`
- `test(quick-260902-chc): pin the Health auto-refresh contract, EXPECTED_CHECK_COUNT +5`
- `docs(quick-260902-chc): record the D-12 reversal and the live-browser items`
</commits>

<output>
Create `.planning/quick/260902-chc-implement-option-b-from-the-validated-he/260902-chc-SUMMARY.md` when done.
</output>
