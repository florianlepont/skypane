---
phase: quick-260902-gjj
plan: 260902-gjj
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/pages/health_page.py
  - companion/layout.py
  - companion/static/style.css
  - companion/test_status_pages.py
  - companion/test_companion_app.py
  - .planning/phases/06.6.1-companion-visual-polish-pass-logo-branding-mobile-hamburger-/06.6.1-UI-SPEC.md
  - .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md
autonomous: true
requirements: [QUICK-260902-gjj]
tags: [companion, health-page, css, design-system, accessibility, harness, status]

must_haves:
  truths:
    - "Both subtitle-role text fragments on Health — the battery heading's trailing `— Latest N readings` span and the Unresolved-prefixes read-only note — render in this file's single existing 70%-muted strength, by carrying `.section-caption` composed with the sizing class each already had, never by a second muted value invented for either one."
    - "The battery-trend card and the Unresolved-prefixes card each carry a status-coloured 3px top border driven by the SAME `battery_status()` / `coverage_status()` values that drove their dots, reusing the `--color-status-ok/warn/error` tokens the stat tiles already use — no new colour value, no new status vocabulary, no recomputed verdict."
    - "That status border survives `:hover` and `:focus-within` on both cards — a non-negotiable property, because `.battery-trend-section:focus-within` fires every time a keyboard user focuses a chart point, and a status signal that vanishes while the user is reading it is not a status signal."
    - "The two `status_dot()` badges those cards carried are removed entirely, and the removal is justified by a source-level finding — `status_dot()` emits an EMPTY, unlabelled `<span class=\"dot dot--ok\">` plus a label naming the SUBJECT, so it carries zero screen-reader-accessible state today and there is nothing a border-top cannot replicate. `status_dot()` itself, and its three surviving Corroboration + two History call sites, are untouched."
    - "The Resolution-statistics card is confirmed from its real markup to carry no status signal, gets no modifier, and keeps its neutral hairline — and is NOT given a 3px accent border to `complete the pattern`, which would be a second broadening of style.css's exhaustive accent-reservation list for no reported problem."
    - "Two prior decisions this task reverses (06.5-CONTEXT D-01's `status_dot()` battery badge, and `.battery-trend-section`'s CSS comment claiming it `carries no ok/warn/error verdict of its own`) are recorded AT the removal site as reversals, in the same shape 260902-chc's own D-12 reversal record already establishes in this file — never silently deleted."
    - "`companion/test_status_pages.py` and `companion/test_companion_app.py` are both green at their own bumped `EXPECTED_CHECK_COUNT` values, read live from disk; `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch."
  artifacts:
    - "companion/pages/health_page.py — `.section-caption` added to two fragments; `_battery_badge_block()` and `BATTERY_STATUS_LABEL` retired; `_battery_trend_section_html()` takes a state and composes the modifier; `render()` composes the registry card's modifier from `coverage_status()`"
    - "companion/layout.py — `card_status_class()`, the one status→card-modifier mapping, living beside `_STATUS_DOT_CLASSES`/`_STAT_TILE_BORDER_CLASSES` so the vocabulary has exactly one home"
    - "companion/static/style.css — three shared status-modifier rules covering both card components; `.stat-tile`'s four modifiers rewritten in their doubled form; the false `border-top is unaffected by hover` claim corrected; `.battery-trend-section`'s stale `carries no verdict` comment reversed"
    - "companion/test_status_pages.py + companion/test_companion_app.py — new checks for the caption pair, the card-modifier mapping, the rendered class lists, the scoped dot removal and the hover-survival source order; every literal-open-tag and dot-count check retargeted in place"
    - ".planning/phases/06.6.1-.../06.6.1-UI-SPEC.md and .planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md — the retired battery badge and the widened status-token use recorded where each file's own contract requires"
  key_links:
    - "`.stat-tile:hover` is (0,2,0) and `.stat-tile--ok` is (0,1,0), and `border-color: transparent` is a SHORTHAND that includes `border-top-color`. The status top border therefore already vanishes on hover today, and the CSS comment claiming otherwise is false. Any new card-status rule built on that same shape inherits the same defect — which is why the new rules use the doubled (0,2,0) form AND are placed after the hover rules, with a harness check pinning both halves."
    - "`rendered.index('<section class=\"battery-trend-section\">')` and `rendered.count(BATTERY_SECTION_CLASS) != 1` are exact-literal lookups in the harness that BOTH break the moment a modifier class joins that attribute — the second one silently (the substring appears twice in one attribute), which is the dangerous kind. Same for `'<section class=\"page-section page-section--nested\">'`."
    - "Two harness assertions are NEGATIVE on the dot classes (`dot--error not in markup`). Once both dots are gone they pass vacuously and stop protecting anything, so retargeting them onto the new modifier is mandatory, not cosmetic."
    - "The abnormal-drop copy `A battery reading shows an abnormal drop.` is asserted ABSENT from the rendered page by an existing check backed by a UI-SPEC contract. Any state sentence added to the battery card must not reuse that string — which is one of the reasons this task adds no state sentence at all (see Task 2's written rejection)."
---

<objective>
Fix two live-confirmed Health-page issues the developer reproduced in real Safari after six earlier fix rounds today: two subtitle-role text fragments rendering at full-strength ink instead of muted, and two small status-dot indicators the developer finds confusing and wants replaced by a status-coloured accent on the card itself.

Purpose: issue 1 is two missing class tokens with an already-diagnosed root cause — `.text-label` supplies a size but not the muted colour, and the muted colour lives in a separate class this file already pairs with it everywhere else. Issue 2 is the real work: it extends the stat tiles' status-border mechanism to two full-width cards, and it requires a real, documented decision about whether the dot's text label survives — a decision that cannot be made without first establishing what accessibility contract `status_dot()` actually carries. This plan makes that finding, states the decision, and records the two prior decisions the change reverses.

Output: two correctly muted captions; two cards whose status reads at a glance from their own top edge in the same visual language the Device/Pipeline/Resolution tiles already speak; two redundant dot indicators gone with their removal justified rather than asserted; and a latent hover defect in the pattern being extended, found and fixed rather than inherited.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260902-ep7-fix-4-more-confirmed-real-bugs-on-the-he/260902-ep7-SUMMARY.md

That SUMMARY is the immediately-prior quick task on this exact page, executed within the last hour; its code is what these two issues were found in. Read its "Pixel-Level Items Outstanding" list before writing this task's own — several of its items (dark theme, 375px, real Safari) are still open and this task must not re-claim them.

`Skill("sketch-findings-skypane")` is the authoritative design-system reference for this app. Load it before Task 1 (the muted-caption role and the 70% strength) and before Task 2 (the status-token register and the accent-reservation contract).

**Source facts established during planning by reading the real files. Treat these as given — do NOT re-derive them from scratch — but DO re-confirm any of them you are about to depend on, since two of them are claims that a prior task's comment got wrong.**

Issue 1:
- `health_page.py::_battery_trend_section_html()` (~L1245) emits `'<h2 class="text-heading">%s%s<span class="text-label">— Latest %d readings</span></h2>'`. The span carries `text-label` only.
- `health_page.py::_registry_section()` (~L1605) emits `note_html = '<p class="text-body">%s</p>' % escape_html(_READ_ONLY_NOTE)`. That paragraph carries `text-body` only.
- `.text-label` (style.css ~L248) declares `font-size`, `font-weight: var(--weight-regular)` and `line-height` — no colour. `.text-body` (~L254) declares the same three, no colour. `.section-caption` (~L281) declares EXACTLY ONE property, `color: color-mix(in srgb, var(--color-text) 70%, transparent)`, and its own comment states that composing rather than restating is deliberate.
- This file's own established pairing for this role is `class="text-label section-caption"` — used by `_section_intro_html()` (~L1074) for both Health section descriptions, and established for Settings by quick task 260901-re6. Reuse it; do not invent a second muted value or a second class.
- Because `.text-label`/`.text-body` each declare `font-weight: var(--weight-regular)` themselves, neither fragment inherits the nested `<h2>`'s semibold weight. There is no weight side-effect to reason about — the missing colour really is the whole defect.

Issue 2 — the existing mechanism:
- `layout.py` L99-104: `_STAT_TILE_BORDER_CLASSES = {"ok": "stat-tile--ok", "warn": "stat-tile--warn", "error": "stat-tile--error"}` and `_DEFAULT_STAT_TILE_CLASS = "stat-tile--accent"`. `stat_tile()` (L978) does `.get(status, _DEFAULT_STAT_TILE_CLASS)` — a whitelist with a safe fallback, so an unrecognised status can never become an attacker-influenceable class name. That discipline is the thing to copy.
- `.stat-tile` (style.css L2088) declares `border-top: 3px solid var(--color-accent)` on the BASE; the four modifiers (L2110-2124) change only `border-top-color`.
- `.battery-trend-section` (L2314) and `.page-section` (L2529) each declare `border: 1px solid var(--color-border)` and no status modifier of any kind. Their only status signal today is the in-body dot.

Issue 2 — the two status functions to reuse, unchanged:
- `battery_status(rows)` (L715) returns `"error"` or `"ok"` only — never `"warn"`.
- `coverage_status(rows)` (L1451) returns `"ok"` when the registry is empty, `"warn"` otherwise — never `"error"`.
- Both values already flow to `render()`: `battery_state` is unpacked at L1735 from `ctx["health_state"]`; `registry_rows` is computed at L1752, so `coverage_status(registry_rows)` is available at the call site that builds the registry card's class list (L1838).

Issue 2 — what `status_dot()` actually is (read it yourself at `layout.py` L965-975 before relying on this):
- It returns `'<span class="dot %s"></span><span class="dot-label">%s</span>'`. The dot span is EMPTY — no text, no `role`, no `aria-label`, no `title`. The state lives ONLY in the CSS class, which maps to a `background` colour.
- The label span holds `"Battery readings"` / `"Coverage"` — nouns naming WHAT is measured. Neither says anything about state.
- Its docstring names one contract only (the whitelist-with-warn-fallback, for injection safety). It states no accessibility contract.
- `BATTERY_STATUS_LABEL`'s own comment (`health_page.py` L180-184) says the wording was chosen to differ from `BATTERY_SECTION_HEADING` so harness substring assertions stay unambiguous — a test-disambiguation reason, not a reader-value reason.

Issue 2 — two prior decisions this task reverses (both must be recorded, not silently deleted):
- `06.5-CONTEXT.md` D-01: "Add a persistent status badge next to the Battery Trend section heading, reusing the exact `status_dot()` pattern the Device and Pipeline sections already render." That same D-01's own reference note ALSO says "06.3's 3px top-border-by-status treatment should apply to the Battery tile too" — so a status-coloured top border on this card was the original intent, lost only when 06.6.1-03 moved the chart out of `.stat-tile`. This task restores it; frame it that way.
- `style.css` L2309-2311, inside `.battery-trend-section`'s own comment: "The other omission this comment used to list, no border-top status accent, is unrelated to this plan and still correct (this is not a status tile — it carries no ok/warn/error verdict of its own)." That claim is FALSE as written: `_battery_section()` computes a real `battery_status()` verdict and renders it inside that very section. Correct it at the site.
- `06.6.1-UI-SPEC.md` L181 also states the `status_dot()` badge is "unchanged in mechanism" — stale once the badge is retired.

Do NOT touch, in any task:
- `layout.py::status_dot()` itself, or any of its five surviving call sites (three Corroboration rows in `health_page.py::_corroboration_section()`, two in `history_page.py`). Only the two Health call sites named below are removed.
- `battery_status()` / `coverage_status()` / `corroboration_status()` / `overall_severity()` / `collect_anomalies()` — no verdict logic changes anywhere in this task. The cards consume the same values the dots consumed.
- `.dot` / `.dot--ok` / `.dot--warn` / `.dot--error` / `.dot-label` CSS rules — still used by Corroboration and History.
- `companion/static/battery-trend.js`, `companion/static/freshness.js`, `companion/static/list-filter.js`. Reading them is fine; editing any is out of scope.
- Everything 260902-ep7 landed hours ago: the out-of-flow refresh pill, `.dashboard-grid`'s retargeted margin, the `summary` accent, the viewBox-free chart and its axis chrome.
- The `sketch-findings-skypane` skill file. Six consecutive Health quick tasks have now deferred updating it; folding seven tasks' worth of deltas into that skill is its own piece of work, not a rider on this one. Say so in the SUMMARY rather than letting the deferral go unrecorded a seventh time.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Mute the two subtitle-role fragments by composing this file's existing caption class (ISSUE 1)</name>
  <files>companion/pages/health_page.py, companion/test_status_pages.py</files>

  <read_first>
    - `companion/pages/health_page.py` L1220-1254 (`_battery_trend_section_html()` in full, including the 06.6.1-04 D-02 icon paragraph) and L1590-1613 (`_registry_section()` in full, including its 260902-bl2 considered-rejection comment about the sketch's caption-row dot placement — that comment is about to become partly obsolete, and Task 2 owns it; do not edit it here).
    - `companion/pages/health_page.py` L1049-1076 (`_section_intro_html()`), whose docstring states the `text-label section-caption` pairing and warns that a second class for the same role "would reopen the second-muted-strength defect this stylesheet's own comments record having fixed twice". That is the precedent this task follows.
    - `companion/static/style.css` L246-258 (`.text-label`, `.text-body`) and L266-283 (`.section-caption` plus its full comment).
    - `companion/test_status_pages.py` — grep for `section-caption` and for `Latest %d readings` / `_READ_ONLY_NOTE` to find any check that already pins either fragment's class attribute before you change it.
  </read_first>

  <behavior>
    - `_battery_trend_section_html()`'s trailing span carries both its existing sizing class and the shared caption class.
    - `_registry_section()`'s read-only note paragraph carries both its existing sizing class and the shared caption class.
    - `.section-caption` still declares exactly one property, and that property is still the file's single 70% muted mix — the fix adds a class to markup, it does not add a value to CSS.
    - Every other element that already carried `section-caption` still carries it, unchanged.
  </behavior>

  <action>
Two markup edits, one commit.

Step 1 — apply the class. In `_battery_trend_section_html()`, change the trailing span's class attribute to carry `section-caption` alongside the sizing class it already has. In `_registry_section()`, do the same to the `note_html` paragraph. Match this file's own attribute-value ordering convention (sizing class first, then the caption class) so the result is byte-comparable with `_section_intro_html()`'s existing pair.

Step 2 — do not "improve" either fragment while you are in there. Specifically:
  - Do NOT change the read-only note from `text-body` to `text-label`. The reported defect is colour; the note is a full sentence of prose sitting at Body size, and dropping it to Label size is a size change nobody asked for that would also make it disagree with the sibling prose in the same card region.
  - Do NOT add any declaration to `.section-caption`. Its own comment states that its lack of a margin declaration is a decision and that it composes rather than restates — both fragments already get their size and their regular weight from the class they carry, so `.section-caption` has nothing left to supply beyond colour.
  - Do NOT touch `_section_intro_html()` or any Settings caption. They are already correct and are the precedent being followed, not a target.

Step 3 — record the reasoning in a short comment at ONE of the two sites (the `_battery_trend_section_html()` docstring is the better home, since that function's markup is otherwise undocumented at the class level) and cross-reference it from the other. State: `.text-label` and `.text-body` each supply a size and a weight but no colour, so an element carrying only one of them inherits full-strength `--color-text`; the muted strength for a subtitle/caption role lives in `.section-caption` and is composed onto the sizing class, never restated. Name `_section_intro_html()` as the in-file precedent so a future reader finds the pair rather than re-deriving it.

Step 4 — add ONE harness check pinning the pair AND the strength together. It must assert:
  (a) the rendered Health page's battery `<h2>` contains a span whose class attribute carries BOTH the sizing class and `section-caption` (locate it by slicing from the `BATTERY_SECTION_HEADING` occurrence to the closing `</h2>`, not by a document-wide substring search);
  (b) the rendered read-only note paragraph's own tag carries both classes (locate it by finding `_READ_ONLY_NOTE`'s text and walking back to its opening `<p`);
  (c) `style.css`'s `.section-caption` rule body still declares exactly one property and that property's value is the same 70% `color-mix` string, so a future edit cannot satisfy (a)/(b) while quietly forking a second muted strength.
  Parse the CSS with this file's established `index()`-plus-window-slicing idiom (see `_quick_260901_tsa_css_dom_contract_guard()`), never a regex CSS parser.

Step 5 — read the current on-disk `EXPECTED_CHECK_COUNT` in `companion/test_status_pages.py` (95 at planning time — verify, do not assume), bump it by exactly one, and extend the running arithmetic comment above it in the file's established style.

Step 6 — mutation-test before committing: temporarily remove `section-caption` from ONE of the two fragments, confirm exactly this new check fails and no other, restore. Then do the same for the CSS half by temporarily adding a second declaration to `.section-caption`.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 -c "
from companion.pages import health_page as h
m = h._battery_trend_section_html('<p>x</p>') if h._battery_trend_section_html.__code__.co_argcount == 1 else h._battery_trend_section_html('<p>x</p>', 'ok')
head = m[m.index('<h2'):m.index('</h2>')]
assert 'section-caption' in head, 'battery heading caption span must carry section-caption'
assert 'text-label' in head, 'battery heading caption span must keep its sizing class'
n = h._registry_section([], '2024-01-01T00:00:00')
at = n.index(h._READ_ONLY_NOTE)
tag = n[n.rindex('<p', 0, at):at]
assert 'section-caption' in tag and 'text-body' in tag, 'read-only note must compose section-caption with text-body, got %r' % tag
css = open('companion/static/style.css').read()
i = css.index('.section-caption {')
body = css[i:css.index('}', i)]
assert body.count(';') == 1 and 'color-mix(in srgb, var(--color-text) 70%, transparent)' in body, 'section-caption must stay a single 70%-muted colour declaration'
print('OK')"</automated>
    <automated>server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>

  <done>
    Both fragments carry `section-caption` composed with the sizing class each already had; `.section-caption` is unchanged and still declares exactly one property; `_section_intro_html()` and every Settings caption are untouched; one new harness check pins the markup pair and the single muted strength together, mutation-tested both ways, with `EXPECTED_CHECK_COUNT` bumped from its real on-disk value; the status-pages and view-pages harnesses are green; one atomic commit.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Move the two Health status signals from in-body dots onto the cards' own top edge (ISSUE 2)</name>
  <files>companion/layout.py, companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py, companion/test_companion_app.py, .planning/phases/06.6.1-companion-visual-polish-pass-logo-branding-mobile-hamburger-/06.6.1-UI-SPEC.md, .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md</files>

  <read_first>
    - `companion/layout.py` L92-104 (`_STATUS_DOT_CLASSES`, `_STAT_TILE_BORDER_CLASSES`, `_DEFAULT_STAT_TILE_CLASS`) and L965-1016 (`status_dot()` and `stat_tile()` in full, both docstrings included). Read `status_dot()`'s output string character by character — the accessibility finding this task turns on is that its first span is empty.
    - `companion/pages/health_page.py` L178-184 (`BATTERY_STATUS_LABEL` and its harness-disambiguation comment), L1128-1133 (`_battery_badge_block()`), L1220-1254 (`_battery_trend_section_html()`), L1256-1337 (`_battery_section()` in full, both call sites of the badge block), L1590-1613 (`_registry_section()`), L1616-1660 (`_stats_table_html()` and `_resolution_rate_tile_html()` — read these to CONFIRM from source that the Resolution-statistics card genuinely computes no verdict, rather than assuming it), and L1718-1851 (`render()` in full, especially the L1758 comment about `battery_state` no longer painting a border and the two `page-section page-section--nested` emissions at L1838/L1840).
    - `companion/static/style.css` L2081-2124 (the `.stat-tile` comment block, the base rule, the hover rule and the four modifiers) and L2302-2328 (`.battery-trend-section`'s comment, base rule and hover rule) and L2521-2553 (`.page-section`'s comment, base rule and hover rule). The comment at L2309-2311 makes a claim this task disproves.
    - `.planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md` L86-90 — the Color table rows that enumerate where each `--color-status-*` token is allowed to appear ("error stat-tile top border, error status dots" / "ok status dots/tiles" / "warn status dots/tiles/banners"). This task widens those uses.
    - `.planning/phases/06.6.1-.../06.6.1-UI-SPEC.md` L177-181 — the Battery-trend section contract, whose last bullet says the `status_dot()` badge is "unchanged in mechanism".
    - `companion/test_status_pages.py`: grep for `BATTERY_SECTION_CLASS`, `page-section--nested`, `dot--ok`, `dot--warn`, `dot--error`, `dot-label` and `BATTERY_STATUS_LABEL` and read EVERY hit before editing anything. Planning found the breaking ones at roughly L495-503, L951, L960-965, L995-997, L1012, L1042, L1795-1801, L1930, L1944, L2100-2120, L2145, L2734 — re-derive that list with your own grep; the line numbers will have moved by one commit already.
    - `companion/test_companion_app.py` L65 (`EXPECTED_CHECK_COUNT`) and L676-695 (the existing `stat_tile()` mapping check — the shape the new `layout.py` helper's own check should follow).
  </read_first>

  <behavior>
    - `layout.card_status_class(base_class, status)` returns `base_class + "--ok" | "--warn" | "--error"` for the three whitelisted states and the empty string for `None` or anything unrecognised.
    - The rendered battery-trend `<section>`'s class attribute carries `battery-trend-section` plus exactly one status modifier matching `battery_status()`'s own return value for the same rows.
    - The rendered Unresolved-prefixes `<section>`'s class attribute carries `page-section page-section--nested` plus exactly one status modifier matching `coverage_status()`'s own return value for the same rows.
    - The rendered Resolution-statistics `<section>`'s class attribute carries `page-section page-section--nested` and NO status modifier.
    - Each modifier's CSS rule declares a 3px top border in the matching `--color-status-*` token and nothing else.
    - Neither of those two cards renders any `dot`/`dot-label` markup; the three Corroboration rows still do.
    - `health_page` no longer defines `BATTERY_STATUS_LABEL` or `_battery_badge_block`.
    - Nothing on the page renders the string `collect_anomalies()` appends for a battery drop — the existing absence assertion still holds unweakened.
  </behavior>

  <action>
Ship this as TWO atomic commits, in this order, each leaving both harnesses green on its own.

--- Decision record: what happens to the dot's LABEL, and the accessibility contract check ---

Write this reasoning into the SUMMARY and, in condensed form, into the removal-site comment. It is the substance of the task, not preamble.

The mandated check first: read `status_dot()` and establish what accessibility contract it actually carries. It emits `<span class="dot dot--ok"></span><span class="dot-label">Battery readings</span>`. The first span is EMPTY — no text node, no `role`, no `aria-label`, no `title`. Its state lives entirely in a CSS class that maps to a `background` colour. The second span holds a noun naming the SUBJECT being measured, never the state: "Battery readings" and "Coverage" are equally true when the signal is healthy and when it is failing. So a screen-reader user gets, today, the word "Coverage" and nothing else. **`status_dot()` provides no screen-reader-accessible state announcement, and therefore a `border-top` colour has nothing it fails to replicate.** Removing the dot loses no accessible information. Confirm this yourself from the source before writing it down — the whole decision rests on it.

Decision: remove the dot AND its label at both sites. Three reasons, in order of strength:
  1. Both labels are redundant with their own card's heading. "Coverage" sits under a heading reading "Unresolved prefixes"; "Battery readings" sits under one reading "Battery trend". `BATTERY_STATUS_LABEL`'s own comment concedes the wording was picked to differ from the heading so harness substring assertions stay unambiguous — a test-disambiguation reason. A label whose only remaining justification is test disambiguation, once its dot is gone, is a bare noun with no function.
  2. This is the third application of a call this codebase has already made twice. Quick task 260901-tsa (finding C) removed exactly this shape of redundancy from the Device and Pipeline tiles — "the tile printed its own name twice" — and explicitly considered and rejected keeping the dot while dropping only its text, because `status_dot()` always emits the pair. The same reasoning, and the same rejected half-measure, apply here.
  3. The developer's own words describe a replacement, not an addition.

Per-card verification that the removal is safe, done from source rather than assumed:
  - **Unresolved prefixes:** its own visible content already states the state in BOTH branches — `empty_state("No coverage gaps.", "No unresolved callsign prefixes — airline coverage looks complete.")` when `coverage_status()` is "ok", and a filter bar reading "N of N shown" over a table of N rows when it is "warn". Nothing is lost, visually or programmatically. Confirm both branches in `_registry_section()`.
  - **Battery trend:** its visible content does NOT state the verdict; the drop signal is named only in the page-level anomaly banner, which deliberately says "check the tiles below" without naming which. So this card's state was colour-only before this task and is colour-only after it — a like-for-like swap, not a regression, but say so plainly rather than implying an improvement.

Considered and REJECTED, in writing, so a later reader does not mistake it for an oversight: adding a `visually-hidden` state sentence to the battery card. Four reasons: (a) it is announced to screen readers but invisible to sighted colour-blind users, so it closes the smaller half of the gap while creating the impression the whole gap is handled; (b) every user-facing string in this codebase has a Copywriting-Contract home or a recorded provenance, and this would be new copy with neither; (c) the one existing string that fits ("A battery reading shows an abnormal drop.") is asserted ABSENT from the rendered page by a live harness check backed by 06.6.1-UI-SPEC's "Anomaly detail list (removed)" row — rendering it would reverse a different phase's decision as a rider on this one; (d) it would land on two of six colour-only status sites, leaving a half-measure.

What to escalate instead, as a named follow-up in the SUMMARY with its sites enumerated: this page conveys WHICH signal is unhealthy by colour alone at six places — the four stat tiles, and now these two cards — while the anomaly banner deliberately carries only a count and "check the tiles below". That is a pre-existing WCAG 1.4.1 (Use of Color, Level A) gap that this task neither introduces nor closes. Closing it properly means one coordinated change across the banner and all six cards, and is its own task. Name it; do not half-do it here.

--- Commit A: the mechanism — cards carry the status colour, dots still present ---

Step A1 — `companion/layout.py`. Add `card_status_class(base_class, status)` immediately after `stat_tile()`, backed by a module-level `_CARD_STATUS_SUFFIXES = {"ok": "--ok", "warn": "--warn", "error": "--error"}` declared beside `_STAT_TILE_BORDER_CLASSES`. It returns `base_class + suffix` for a whitelisted status and `""` otherwise. This lives in `layout.py`, not in `health_page.py`, because `layout.py` already owns the status→class vocabulary in two dicts and a third copy in a page module would be a second place that vocabulary could drift.

Its docstring must state two things explicitly:
  - The same whitelist-with-safe-fallback discipline `status_dot()` and `stat_tile()` document: an unrecognised status can never become an arbitrary, attacker-influenceable class name. Here the fallback is the empty string rather than a default class.
  - WHY the fallback differs from `stat_tile()`'s. `stat_tile()` falls back to `stat-tile--accent` because `.stat-tile`'s base rule already declares a 3px top border that has to be *some* colour. A page-level card's base rule declares a plain 1px hairline, so "no status" correctly means "no modifier at all, keep the neutral edge" — the absence of a coloured edge is itself the signal that the card carries no verdict. Getting this backwards (defaulting to an accent modifier) would put a 3px accent border on the Resolution-statistics card and would require broadening style.css's exhaustive accent-reservation list a second time in two days, for no reported problem.

Step A2 — `companion/static/style.css`. Add ONE block of three rules, placed immediately AFTER `.page-section:hover, .page-section:focus-within` (which is itself after `.battery-trend-section`'s hover rule). One rule per status; each rule's selector is a two-selector list pairing the battery component's doubled form (`.battery-trend-section` immediately followed by `.battery-trend-section--ok`, no space) with the page-section component's doubled form (`.page-section` immediately followed by `.page-section--ok`, no space); each rule declares exactly one property, a 3px solid top border in that status's own token — `var(--color-status-ok)`, `var(--color-status-warn)`, `var(--color-status-error)`. Use the exact token names; introduce no new colour value and no `color-mix`.

Two properties of that selector are load-bearing and must both be stated in the comment:
  - **The doubled form is deliberate.** `.page-section` declares a `border` SHORTHAND, which resets `border-top-color` and `border-top-width`. A single-class modifier is (0,1,0) and would tie it, leaving the outcome to source order — the exact cascade hazard `.page-section.banner--anomaly` a few hundred lines below already documents and solves the same way. The doubled form is (0,2,0) and wins deterministically over the base rule.
  - **The placement after the hover rules is also load-bearing, and is the part a future edit will break.** `.page-section:hover` is ALSO (0,2,0) and declares `border-color: transparent` — a shorthand that includes `border-top-color`. At equal specificity the later rule wins, so this block must stay after both hover rules or the status colour vanishes the moment the card is hovered. That is not a hypothetical: `.battery-trend-section:focus-within` fires every time a keyboard user focuses one of the chart's hit targets, so a status border that loses to hover would blink out during ordinary chart traversal. A harness check pins the source order (Step A5).

Step A3 — `companion/pages/health_page.py`, the markup. Widen `_battery_trend_section_html(battery_html)` to `_battery_trend_section_html(battery_html, state)` and compose the section's class attribute from `BATTERY_SECTION_CLASS` plus `layout.card_status_class(BATTERY_SECTION_CLASS, state)`, joining with a single space and emitting no trailing space when the modifier is empty. Update its call in `render()` (L1821) to pass the `battery_state` already unpacked at L1735. Note in the docstring that this is a deliberate signature widening and that, unlike `_battery_section()`'s own single-argument call site, nothing pins this one — confirm that with a grep before relying on it.

At `render()`'s registry-card emission (L1838), compose the same way from the literal `"page-section"` base plus `layout.card_status_class("page-section", coverage_status(registry_rows))`, preserving the existing `page-section--nested` modifier and the existing class ORDER (base, then nested, then status) so the two literal-attribute harness lookups have a stable shape to be retargeted onto.

Leave the Resolution-statistics emission at L1840 exactly as it is. Record in a one-line comment beside it that this is a verified conclusion, not an omission: `_stats_table_html()` computes no verdict (it returns either the empty string or a plain `data_table`), `resolution_stats()` returns counts and a percentage with no status field, and no status function exists for this card anywhere in the module — its neutral hairline is the correct signal that it carries no pass/fail state.

Also update `render()`'s L1758 comment, which currently says `battery_state` "no longer paints a stat-tile border, since the battery-trend chart is a page section, not a tile (D-02)". After this change it paints a page-section-level border instead — a different mechanism reaching the same original intent. Say so.

Step A4 — `companion/static/style.css`, correct the false claim. Rewrite `.battery-trend-section`'s comment passage at L2309-2311. It currently asserts the absent status border is "still correct (this is not a status tile — it carries no ok/warn/error verdict of its own)". That was wrong when written: `_battery_section()` computes a real `battery_status()` verdict and renders it inside that very section. Replace it with the honest record — the card always carried a verdict, the verdict was drawn as an in-body dot instead of a card edge, and 06.5-CONTEXT D-01's own reference note already expected "06.3's 3px top-border-by-status treatment" to apply to this content before 06.6.1-03 moved it out of `.stat-tile`. Frame this as restoring an intent that was lost in a container move, not as a new idea. Keep the OTHER omission in that same comment (no hover lift/transform, because the card holds an interactive chart) intact and still correct.

Step A5 — the harness, Commit A's share.

Retarget IN PLACE, no count change, every check that reads either card's class attribute as an exact literal. Planning found these categories; grep for all of them yourself, because a missed one fails silently rather than loudly:
  - `rendered.index('<section class="%s">' % health_page.BATTERY_SECTION_CLASS)` — three sites. The trailing `">` no longer matches.
  - `rendered.count(health_page.BATTERY_SECTION_CLASS) != 1` — **the dangerous one.** After this change the substring `battery-trend-section` appears TWICE inside one class attribute, so this check fails for a reason that has nothing to do with what it means to protect. Retarget it onto the section's opening-tag prefix so it still counts sections, not substrings.
  - `'<section class="page-section page-section--nested">'` used as both a count target and an index target — the registry card no longer matches it; the stats card still does. Retarget to a prefix match plus an explicit per-card class-list assertion, so the check gets STRONGER (it now knows which of the two cards it found) rather than merely surviving.

Add TWO new checks:
  - In `companion/test_status_pages.py`: one check asserting, against a real rendered page with a seeded battery drop and a seeded non-empty registry, that (i) the battery section's own tag carries the modifier `card_status_class()` returns for `battery_status()`'s value on the same rows, (ii) the registry card's tag carries the modifier for `coverage_status()`'s value on the same rows, (iii) the stats card's tag carries `page-section--nested` and NO status modifier, and (iv) `style.css` declares all three status rules with the doubled selector form. Locate each section by its own heading constant and slice to its opening tag — never a document-wide substring search.
  - In `companion/test_companion_app.py`: one check for `card_status_class()` itself, following the existing `stat_tile()` check's shape — the three whitelisted mappings, the empty string for `None`, and the empty string for an unrecognised state.

Add ONE more check in `companion/test_status_pages.py` pinning the hover-survival source order: for `.battery-trend-section` and `.page-section`, the index of that component's status-modifier rule in `style.css` must be GREATER than the index of its own `:hover`/`:focus-within` rule. This is the check that stops a future "tidy the modifiers up next to their base rule" edit from silently deleting the status colour on hover. Parse with the `index()`-plus-slicing idiom.

Read both harnesses' current on-disk `EXPECTED_CHECK_COUNT` values (95 and 105 at planning time — verify, do not assume), bump each by the number of checks you actually added to it, and extend each file's running arithmetic comment in its own established style. Mutation-test every new check and every retargeted check individually.

--- Commit B: remove the two dot badges ---

Step B1 — `companion/pages/health_page.py`. Delete `_battery_badge_block()` and `BATTERY_STATUS_LABEL` outright. In `_battery_section()`, drop both badge-block calls: the empty-history branch returns `layout.empty_state(...)` alone, and the main branch returns `chart_block + disclosure_html`. In `_registry_section()`, drop the `status_html` line and collapse `header_html` to the note paragraph alone.

Step B2 — record the reversal AT the removal site, in the shape this file already uses. `health_page.py` L1689 carries a `--- 260902-chc: D-12 reversal, recorded at the removal site ---` block; follow it exactly. State: 06.5-CONTEXT D-01 asked for a persistent `status_dot()` badge next to the Battery Trend heading; that badge is retired here in favour of the card-level status edge D-01's own reference note already expected this content to carry, and the accessibility check that licensed the removal (the dot span is empty; the label names the subject, never the state) with its conclusion. Do the same, more briefly, in `_registry_section()`, where the existing 260902-bl2 comment about the sketch's caption-row dot placement is now partly obsolete — that comment argued against MOVING the dot into the card-title row; the dot is now gone entirely, so update it rather than leaving a rejection standing for a thing that no longer exists.

Step B3 — the two UI-SPEC edits, both mandatory, both in this commit:
  - `06.6.1-UI-SPEC.md` L181: the bullet claiming the `status_dot()` badge is "unchanged in mechanism" is now stale. Record that the badge is retired and that the section's status is carried by a status-coloured top border instead, referencing this quick task id. Change nothing else in that file.
  - `06.6.4.1-UI-SPEC.md` L86-90: the Color table enumerates where each status token may appear ("error stat-tile top border, error status dots" / "ok status dots/tiles" / "warn status dots/tiles/banners"). Append the battery-trend and nested-page-section top borders to all three rows so the table stays an accurate enumeration, referencing this quick task id. This is the same discipline 260902-ep7 followed for the accent-reservation list — an enumerated contract is widened in writing or not at all. Change nothing else in that file.

Step B4 — the harness, Commit B's share.

Retarget IN PLACE, no count change:
  - Every `BATTERY_STATUS_LABEL` presence assertion (planning found three). Each should now assert the card's status modifier instead — the same thing the check meant, read from where the signal now lives.
  - Every `rendered.count("dot--ok") != 2` style count. Re-derive each fixture's real remaining dot count from the fixture's own seeded data rather than adjusting the number by two: after this change the surviving dots on Health come only from `_corroboration_section()`, and several of these fixtures seed no corroboration rows at all.
  - `if "dot--error" not in rendered` on the battery-drop fixture — this one BREAKS loudly, which is correct. Retarget it onto the battery card's error modifier.
  - **The two NEGATIVE dot assertions** (`if "dot--error" in markup or "dot--warn" in markup` on `_battery_section([])`, and the single-reading page-level one). These now pass vacuously and protect nothing. Retargeting them onto the new modifier is mandatory; leaving them is silently gutting two regression guards.

Add ONE new check asserting the removal is SCOPED, not global: slice the rendered page to the battery section's own boundaries and to the registry card's own boundaries and assert neither slice contains `dot-label`; then assert the Corroboration tile's slice still DOES, on a fixture that seeds corroboration rows. Without that third assertion the first two would pass even if `status_dot()` had been broken everywhere. In the same check, assert `hasattr(health_page, "BATTERY_STATUS_LABEL")` and `hasattr(health_page, "_battery_badge_block")` are both false.

**Use `hasattr`, never a source-text grep, for those two.** The reversal comment Step B2 requires will name both retired symbols in prose, so a `"BATTERY_STATUS_LABEL" not in source` check would fail against the very comment this task requires you to write. The existing `_STALE_VIEW_BANNER_HTML` guard (~L930) is the precedent.

Also confirm, and keep passing unweakened, the existing assertion that the abnormal-drop copy is absent from the rendered page — nothing added by this task renders it.

Bump both counts again by exactly what you added, extend the arithmetic comments, and mutation-test every new and every retargeted check individually.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 companion/test_companion_app.py</automated>
    <automated>server/.venv/bin/python3 companion/test_view_pages.py</automated>
    <automated>server/.venv/bin/python3 companion/test_contrast_check.py</automated>
    <automated>server/.venv/bin/python3 -c "
import companion.layout as layout
for s, sfx in (('ok','--ok'), ('warn','--warn'), ('error','--error')):
    assert layout.card_status_class('page-section', s) == 'page-section' + sfx, s
assert layout.card_status_class('page-section', None) == '', 'None must yield no modifier'
assert layout.card_status_class('page-section', 'nope') == '', 'unknown status must yield no modifier'
css = open('companion/static/style.css').read()
for comp, hover in (('battery-trend-section', '.battery-trend-section:hover'), ('page-section', '.page-section:hover')):
    for s in ('ok', 'warn', 'error'):
        sel = '.%s.%s--%s' % (comp, comp, s)
        assert sel in css, 'missing doubled-form selector %s' % sel
        assert css.index(sel) > css.index(hover), '%s must come after %s or hover erases it' % (sel, hover)
for s in ('ok', 'warn', 'error'):
    i = css.index('.page-section.page-section--%s' % s)
    body = css[css.index('{', i):css.index('}', i)]
    assert 'var(--color-status-%s)' % s in body and '3px' in body, 'status rule %s must be a 3px border in its own token' % s
print('OK')"</automated>
    <automated>server/.venv/bin/python3 -c "
import shutil, tempfile, sys
sys.path.insert(0, '.')
from companion.pages import health_page as h
import companion.layout as layout
rows = [{'ts': '2024-01-01T00:0%d:00' % i, 'battery_mv': 4200 - i * 150} for i in range(3)]
assert h.battery_status(rows) == 'error', 'fixture must produce an error verdict'
m, st = h._battery_section(rows)
assert 'dot-label' not in m and 'class=\"dot ' not in m, 'battery card must render no status dot'
sec = h._battery_trend_section_html(m, st)
tag = sec[:sec.index('>')]
assert layout.card_status_class(h.BATTERY_SECTION_CLASS, st) in tag, 'battery section tag must carry its status modifier, got %r' % tag
reg = h._registry_section([('AAA', 2, '', '', '')], '2024-01-01T00:00:00')
assert 'dot-label' not in reg and 'class=\"dot ' not in reg, 'registry card must render no status dot'
assert h.coverage_status([('AAA', 2, '', '', '')]) == 'warn'
assert not hasattr(h, 'BATTERY_STATUS_LABEL'), 'retired constant must be gone'
assert not hasattr(h, '_battery_badge_block'), 'retired helper must be gone'
assert 'dot-label' in h._corroboration_section({'True': 1, 'None': 0, 'False': 0})[0], 'corroboration dots must survive'
print('OK')"</automated>
  </verify>

  <done>
    `layout.card_status_class()` exists with a whitelist-and-empty-string fallback whose divergence from `stat_tile()`'s accent fallback is justified in its docstring; three shared CSS rules give both card components a 3px status top border in the existing `--color-status-*` tokens, written in the doubled (0,2,0) form and placed after both hover rules so the colour survives `:hover` and `:focus-within`; the battery-trend and Unresolved-prefixes sections carry modifiers derived from the unchanged `battery_status()`/`coverage_status()` values; the Resolution-statistics card is confirmed verdict-free from source and left untouched with a one-line record of that verification; both `status_dot()` badges and the `BATTERY_STATUS_LABEL`/`_battery_badge_block` symbols are gone, with the 06.5 D-01 reversal and the accessibility finding recorded at the removal site; `status_dot()` and its five surviving call sites are untouched; the false `.battery-trend-section` comment claim is corrected; both UI-SPECs record the retired badge and the widened status-token use; every literal-open-tag, dot-count and negative dot assertion in the harness is retargeted in place with no count change, four new checks are added across two harnesses with both `EXPECTED_CHECK_COUNT` values bumped from their real on-disk figures, and every new and retargeted check is individually mutation-tested; two atomic commits.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Fix the latent hover defect in the stat-tile status border this task's pattern is built on</name>
  <files>companion/static/style.css, companion/test_status_pages.py</files>

  <read_first>
    - `companion/static/style.css` L2081-2124 again, this time reading the comment's claim and the rules' specificity against each other rather than reading the comment as fact. The claim under test is at L2085-2087: "The status-coloured top border is unaffected either way: it draws from a different property (border-top) than the general border, so the two always coexist without fighting each other."
    - Task 2's own new status-modifier block and its source-order comment — this task applies the same fix to the component that block was modelled on.
  </read_first>

  <behavior>
    - Each `.stat-tile` status modifier's selector out-specifies or later-beats `.stat-tile:hover, .stat-tile:focus-within`, so a hovered or focus-containing tile keeps its status-coloured top border while its hairline still clears to transparent.
    - The tiles' hover treatment is otherwise unchanged: the shadow still appears, the 1px lift still happens, the other three edges still clear.
    - No status colour, no border width and no modifier class name changes.
  </behavior>

  <action>
Step 1 — establish the defect from source before changing anything, and record the arithmetic. `.stat-tile:hover` is one class plus one pseudo-class = specificity (0,2,0). `.stat-tile--ok` is one class = (0,1,0). `border-color` is a SHORTHAND that expands to all four `border-*-color` longhands, including `border-top-color` — so on hover, and on `:focus-within`, the tile's status-coloured top border resolves to `transparent`. The comment at L2085-2087 asserts the opposite and is factually wrong; `border-top` and `border-color` are not "different properties" in the sense that comment means, they overlap on `border-top-color`.

This is a pre-existing defect, not one this task introduces, and it is worth fixing here for three specific reasons rather than deferring:
  - Task 2 cites that exact comment's mechanism as the precedent it extends. Shipping a plan that quotes a false claim as its own justification, and leaves the claim standing, is not acceptable.
  - `:focus-within` is in the same selector. Health's tiles contain focusable children, so this is not only a pointer-hover cosmetic issue.
  - The fix is mechanically identical to the one Task 2 just wrote for the two card components, in the same file, forty lines away. Leaving three tiles broken and two cards fixed produces an inconsistency worse than either state.

Step 2 — apply it. Rewrite the four `.stat-tile` status modifiers (`--ok`, `--warn`, `--error`, `--accent`) into their doubled form (`.stat-tile.stat-tile--ok` and so on), which raises each to (0,2,0). They already sit after the hover rule in source order, so at equal specificity they now win. Change nothing else about them: same property (`border-top-color`), same tokens, same values.

Do NOT instead narrow the hover rule's `border-color: transparent` into per-side longhands. That would touch the hover treatment of six card components at once (`.stat-tile`, `.page-section`, `.battery-trend-section`, `.runway-card`, `.history-card`, `.login-card`, plus `.airline-card` and `.theme-status`) for a fix only two of them need, and it would change how the hairline clears rather than how the status border survives. Record that rejection.

Step 3 — rewrite the false comment passage at L2085-2087 into an accurate one: the status top border and the hover treatment DO collide, on `border-top-color`, because `border-color` is a shorthand; the doubled modifier selectors are what make the status border win; and the modifiers must therefore stay after the hover rule in source order. Reference this quick task id and cross-reference Task 2's card-level block, which solves the identical problem for the two page-level cards.

Step 4 — extend the source-order harness check Task 2 added rather than writing a second one: add `.stat-tile` to the same component list it already walks, so one check covers all three components' modifier-after-hover ordering and their doubled-selector form. That is an in-place strengthening with no count change — say so in the commit body.

Step 5 — mutation-test: temporarily revert one `.stat-tile` modifier to its single-class form, confirm exactly the extended check fails and no other, restore.

Step 6 — this task's visible effect is only observable in a browser, on hover. It is the single most important item on this plan's live-browser handoff list, because the harness can prove the selector shape and the source order but cannot prove the rendered colour survives the pointer.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py</automated>
    <automated>server/.venv/bin/python3 -c "
css = open('companion/static/style.css').read()
hover = css.index('.stat-tile:hover')
for s in ('ok', 'warn', 'error', 'accent'):
    sel = '.stat-tile.stat-tile--%s' % s
    assert sel in css, 'expected the doubled form %s' % sel
    assert css.index(sel) > hover, '%s must come after .stat-tile:hover' % sel
    body = css[css.index('{', css.index(sel)):css.index('}', css.index(sel))]
    assert 'border-top-color' in body, '%s must still declare only border-top-color' % sel
print('OK')"</automated>
    <automated>server/.venv/bin/python3 companion/test_companion_app.py</automated>
    <automated>server/.venv/bin/python3 companion/test_view_pages.py</automated>
    <automated>scripts/run-all-tests.sh</automated>
  </verify>

  <done>
    All four `.stat-tile` status modifiers are written in their doubled (0,2,0) form and sit after the hover rule, so a hovered or focus-containing tile keeps its status-coloured top border; the false "unaffected either way" comment is replaced with the real shorthand-collision explanation and the source-order dependency it creates; the alternative of narrowing the hover shorthand across eight components is rejected in writing; Task 2's source-order check is extended in place to cover all three components with no count change and is mutation-tested; `scripts/run-all-tests.sh` reports exactly one failing harness, the pre-existing `server/test_poll_loop.py` `panel.bin` digest mismatch, with no coverage-gate shortfall; one atomic commit.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| history DB / poll-state JSON → server-rendered class attributes | `battery_mv` and registry rows reach `battery_status()`/`coverage_status()`, whose return values now select a CSS class name |
| stylesheet → every page | the `.page-section` status modifiers reach Settings, Preview and Health; the `.stat-tile` modifier rewrite reaches every tile in the app |
| page module → shared component | `layout.card_status_class()` becomes a new shared builder consumed by a page module |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-gjj-01 | Tampering (injection) | `layout.card_status_class()` — device/registry data selects a class name | high | mitigate | The status argument is looked up in a fixed three-key whitelist and anything else returns the empty string, so no attacker-influenced value can reach the class attribute — the identical discipline `status_dot()` and `stat_tile()` already document, and Task 2's verify asserts both the `None` and the unrecognised-state paths. `base_class` comes only from module constants (`BATTERY_SECTION_CLASS`) or a literal at the call site, never from data. |
| T-gjj-02 | Information disclosure | removing the two status dots | medium | mitigate | The removal is licensed by a source-level finding (the dot span is empty; the label names the subject, not the state), so no programmatically-available state is dropped. Task 2 additionally requires per-card confirmation that the registry card's own visible content states its state in both branches, and an honest record that the battery card's state was and remains colour-only. The pre-existing page-wide WCAG 1.4.1 gap is escalated by name rather than silently absorbed. |
| T-gjj-03 | Tampering | the `.page-section` status modifiers reaching Settings/Preview | low | accept | Those pages never call `card_status_class()`, so their sections emit no modifier and match no new rule. The blast radius is the two Health cards only; Task 2's new render-level check asserts the third Health card carries no modifier, and `companion/test_view_pages.py` and `companion/test_config_page.py` both run as a regression guard on the other pages. |
| T-gjj-04 | Repudiation | two reversed prior decisions (06.5 D-01's badge, the `.battery-trend-section` comment claim) | medium | mitigate | Task 2 requires both to be recorded at the removal site in the shape 260902-chc's own D-12 reversal record establishes, plus matching edits to both UI-SPECs in the same commit — so no contract and its implementation can drift apart silently. |
| T-gjj-05 | Denial of service | rendered element count | low | accept | The change is net-negative: two `<span>` pairs removed, zero elements added. Nothing attacker-controllable scales. |
| T-gjj-06 | Elevation of privilege (UI redress) | 3px status border on full-width cards | low | accept | A border draws inside the card's own box and intercepts no pointer events. No element is repositioned, no stacking context is created, nothing becomes clickable that was not. |
| T-gjj-SC | Tampering (supply chain) | npm/pip/cargo installs | high | accept | Zero package installs in this task — CSS declarations, Python markup/helper changes, harness checks and two spec-doc edits only. No `## Package Legitimacy Audit` is required because no install task exists. |
</threat_model>

<source_audit>
Quick-task mode: the sources are the developer's task brief plus 260902-ep7's PLAN and SUMMARY, not ROADMAP/REQUIREMENTS/RESEARCH/CONTEXT artifacts.

| # | Source item | Covered by | Status |
|---|-------------|-----------|--------|
| BRIEF-01 | Read 260902-ep7's PLAN and SUMMARY in full first | Done during planning; its still-open live-browser items are quoted in the plan's context block and excluded from this task's own handoff list | COVERED |
| BRIEF-02 | ISSUE 1(a): the battery heading's trailing `text-label` span computes to full ink | Task 1 Step 1 | COVERED |
| BRIEF-03 | ISSUE 1(b): the read-only note paragraph, `text-body` only, same defect | Task 1 Step 1 | COVERED |
| BRIEF-04 | ISSUE 1: read the whole file fresh; add `.section-caption` composed with the existing sizing class; do not invent a new muted value or class | Task 1 read_first + Steps 1-2 + the harness check's CSS half, which pins `.section-caption` to a single declaration so a forked value fails a test | COVERED |
| BRIEF-05 | ISSUE 2: read `stat_tile()` and its status→class mapping in full to understand the existing border-top mechanism precisely | Task 2 read_first + Task 3, which is what "precisely" turned up — the mechanism has a hover defect the comment denies | COVERED |
| BRIEF-06 | ISSUE 2: design and implement the analogous treatment for both cards, with a status-driven modifier reusing ok/warn/error and the same status tokens | Task 2 Commit A Steps A1-A3 | COVERED |
| BRIEF-07 | ISSUE 2: reuse the existing `battery_status()`/`coverage_status()`; do not recompute or rename | Task 2 Step A3 + the context block's do-not-touch list + the verify step asserting the rendered modifier equals `card_status_class()` of the function's own return | COVERED |
| BRIEF-08 | ISSUE 2: make a real decision on whether the dot+label is removed or the label survives, with reasoning documented | Task 2's "Decision record" — removal, with three ranked reasons and per-card safety verification | COVERED |
| BRIEF-09 | ISSUE 2: mandatory accessibility-contract check on `status_dot()` before removing anything; preserve any screen-reader state announcement a border cannot replicate | Task 2's Decision record, first paragraph — the finding is that the dot span is empty and the label names the subject, so there is no announcement to preserve; the executor is required to re-confirm it from source before writing it down | COVERED |
| BRIEF-10 | ISSUE 2: treat the a11y question with real seriousness rather than waving it through | Task 2 additionally records a rejected `visually-hidden` alternative with four reasons, and escalates the pre-existing six-site WCAG 1.4.1 gap by name as a scoped follow-up | COVERED |
| BRIEF-11 | ISSUE 2: third-card check — confirm from real markup that Resolution statistics genuinely has no status signal | Task 2 read_first (reads `_stats_table_html()` and `_resolution_rate_tile_html()`) + Step A3's required one-line record + a rendered-page assertion that it carries no modifier | COVERED |
| BRIEF-12 | Run `companion/test_status_pages.py` after each change; compute `EXPECTED_CHECK_COUNT` live from the on-disk baseline | Every task's verify + the explicit "verify, do not assume 95/105" instruction in Tasks 1 and 2 | COVERED |
| BRIEF-13 | Run `scripts/run-all-tests.sh` at the end; only the known `server/test_poll_loop.py` digest mismatch remains | Task 3 verify + done + verification item 5 | COVERED |
| BRIEF-14 | Same division of labour as the last six Health quick tasks (executor: source + harness; orchestrator: live browser); write the human-check step clearly but do not block on it | the verification block's two-part split and its preamble | COVERED |
| BRIEF-15 | Live-check specifics: border colour against the card's own content, dot removal in both themes, whether any a11y preservation actually works under a screen reader | verification live items 1, 4, 5, 6 and 8 | COVERED |
| BRIEF-16 | Focused atomic commits matching the existing style, referencing 260902-gjj rather than a phase-plan number | the commits block — four commits across three tasks | COVERED |

No unplanned items.
</source_audit>

<verification>
## Automated — this executor, required

1. `server/.venv/bin/python3 companion/test_status_pages.py` after every task, green at its own bumped `EXPECTED_CHECK_COUNT`.
2. `server/.venv/bin/python3 companion/test_companion_app.py` after Task 2, green at its own bumped count.
3. `companion/test_view_pages.py` after every task (the `.page-section` modifiers and the `.stat-tile` rewrite are shared with History and Preview) and `companion/test_config_page.py` after Task 2 (Settings is the largest `.page-section` consumer outside Health).
4. `companion/test_contrast_check.py` after Task 2 — no token value changes, but the status colours gain a new 3px-border use and that file already pins the non-text-graphic contrast bar for exactly that treatment. Confirm green rather than assuming.
5. `scripts/run-all-tests.sh` at the end — exactly one failing harness, the pre-existing and unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch, and no coverage-gate shortfall.
6. Every new check AND every retargeted/rewritten check mutation-tested individually (one deliberate defect each, confirmed to fail alone, then restored) before the commit that carries it.
7. Recommended, matching every preceding Health quick task's precedent: start a real `companion/app.py` subprocess against a seeded state dir, sign in over HTTP, and fetch `/health` and `/static/style.css` to confirm the SERVED bodies really carry the two `section-caption` fragments, both cards' status modifiers, the three doubled-form status rules, and no `dot-label` inside either card's own markup. This rules out a gap between source-level checks and what the server emits; it is not a substitute for the live-browser pass below.

## Live browser — the orchestrating session's job, NOT this executor's

No browser-automation tools are bound to this subagent, matching all six preceding Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng, 260902-ep7), each of which handed pixel-level confirmation back to the orchestrating session, which performed it successfully every time. Do not claim any of the following as verified.

Provable from source and already covered by the harness, so do NOT re-verify by eye: the presence of both `section-caption` classes, the modifier class each card carries, the three status rules' selectors/tokens/widths, the source order relative to the hover rules, the absence of `dot-label` inside the two cards, the survival of the Corroboration dots, and the retirement of the two symbols.

Needs a real browser:

1. **The two captions.** Confirm the battery heading's trailing `— Latest 20 readings` span and the Unresolved-prefixes read-only note both compute to the muted colour rather than `rgb(23, 25, 31)`, and that both match the computed colour of Health's own section-intro descriptions exactly — the point is one muted strength, not two. Check both themes.
2. **Caption legibility at the muted strength.** The read-only note is a full sentence of Body-size prose; confirm 70%-muted Body prose still reads comfortably against `--color-dominant` in dark theme, where the mix composites differently.
3. **Does the card border read.** Seed or find a state where the registry is non-empty (`coverage_status()` → warn) and confirm the Unresolved-prefixes card shows a visible amber top edge, and that it reads as belonging to that card rather than as a divider between it and the card above.
4. **Does it read clearly against the card's own content** — the brief's explicit question. Compare the 3px status edge on a full-width ~846px card against the same treatment on a ~240-400px stat tile: a colour that reads as punctuation at tile width may read as a heavy rule at card width. Human judgment. If it reads too heavy, the recorded lever is the border WIDTH, not a new colour token.
5. **Both themes, both removals.** Confirm the dot+label really are gone from both cards in light AND dark theme, that neither card now opens with an awkward gap where the badge paragraph used to sit, and that the Corroboration tile's three dots are visibly untouched.
6. **THE HIGHEST-RISK ITEM — hover and focus survival (Task 3's whole point).** Hover each of the three Health stat tiles and confirm the status-coloured top border STAYS while the hairline clears and the shadow appears. Then hover the battery-trend card and the Unresolved-prefixes card and confirm the same. Then Tab into the battery chart and arrow across its points, watching the battery card's top edge — `:focus-within` fires on every point, and this is the case that would have blinked the status colour out on every keystroke before Task 3. Capture computed `border-top-color` before and during hover and diff it; do not judge this one by eye alone.
7. **The stat-tile blast radius.** Task 3 changes four selectors used by every tile in the app. Spot-check Health's tiles in all three status states plus a neutral (`stat-tile--accent`) tile, and confirm nothing else about the hover treatment moved — the shadow, the 1px lift and the other three edges clearing are all unchanged.
8. **Screen-reader pass on the removal, the brief's explicit ask.** With VoiceOver, traverse the battery-trend card and the Unresolved-prefixes card and confirm what is announced is exactly what was announced before minus the two subject nouns — i.e. that no state information was lost, which is what the source-level finding predicts. Also confirm the registry card still announces "No coverage gaps." (or the filter count and table) so its state genuinely does survive in text.
9. **Still outstanding from prior rounds, unchanged by this task:** a full dark-theme pass over the whole Health page, a 375px pass, real Safari confirmation of 260902-dng's table-header padding fix, and 260902-ep7's own item 10 (the chart's keyboard interaction path, still INCONCLUSIVE from the last round — item 6 above exercises the same keys and is a good opportunity to settle it).
</verification>

<commits>
Four focused commits across three tasks, matching this session's established style (`git log --oneline -10`), each referencing the quick task id rather than a phase-plan number, each leaving every harness green on its own:

1. `fix(quick-260902-gjj): mute the battery-heading and read-only-note captions`
2. `feat(quick-260902-gjj): carry Health's card status on the card's own top edge`
3. `refactor(quick-260902-gjj): retire the two redundant Health status dots`
4. `fix(quick-260902-gjj): keep a stat tile's status border through hover and focus`

Harness edits ride with the change they pin, matching 260902-bl2's, 260902-chc's, 260902-dng's and 260902-ep7's pattern rather than a separate test commit. Where a check was retargeted or strengthened in place with no count change, say so in the commit body. Where either `EXPECTED_CHECK_COUNT` moved, put the before/after and the reason in the commit body. Commit 3 carries both UI-SPEC edits.
</commits>

<success_criteria>
- Both subtitle-role fragments carry `section-caption` composed with the sizing class each already had, and `.section-caption` still declares exactly one property at the file's single 70% muted strength.
- `layout.card_status_class()` is the one status→card-modifier mapping, whitelisted, with an empty-string fallback whose divergence from `stat_tile()`'s accent fallback is justified in writing.
- The battery-trend card and the Unresolved-prefixes card each carry a 3px status top border driven by the unchanged `battery_status()`/`coverage_status()` values, in the existing `--color-status-*` tokens, with no new colour value anywhere.
- That border survives `:hover` and `:focus-within` on both cards and on all four `.stat-tile` modifiers, by doubled-form selectors placed after the hover rules, with the source order pinned by a harness check.
- The Resolution-statistics card is confirmed verdict-free from its real markup, carries no modifier, and is explicitly NOT given an accent border to complete the pattern.
- Both `status_dot()` badges are removed with the accessibility finding (empty dot span, subject-naming label, no state announcement) established from source and recorded; `status_dot()` and its five surviving call sites are untouched.
- The `visually-hidden` state-sentence alternative is rejected in writing with reasons, and the pre-existing six-site WCAG 1.4.1 gap is escalated by name rather than half-fixed or ignored.
- 06.5-CONTEXT D-01's badge decision and `.battery-trend-section`'s false "carries no verdict" comment are both recorded as reversals at the site, and both UI-SPECs are updated in the same commit as the change they describe.
- Every exact-literal open-tag lookup, every dot-count assertion and both negative dot assertions in the harness are retargeted in place; four new checks are added across two harnesses; both `EXPECTED_CHECK_COUNT` values are bumped from their real on-disk figures; every new and retargeted check is individually mutation-tested.
- `companion/test_status_pages.py`, `companion/test_companion_app.py`, `companion/test_view_pages.py`, `companion/test_config_page.py` and `companion/test_contrast_check.py` are all green; `scripts/run-all-tests.sh` shows only the known `server/test_poll_loop.py` failure with no coverage-gate shortfall.
- Four atomic commits referencing 260902-gjj.
</success_criteria>

<output>
Create `.planning/quick/260902-gjj-fix-2-more-confirmed-real-issues-on-the-/260902-gjj-SUMMARY.md` when done.

Beyond the standard sections it must contain:
- **"What `status_dot()` actually announces"** — the source-level finding in full (the empty dot span, the subject-naming label, the absent accessibility contract in its docstring), stated as the thing that licensed the removal, with the per-card check of whether each card's own visible content already states its state.
- **"Why no `visually-hidden` state sentence"** — the rejected alternative with its four reasons, including the collision with the existing absent-abnormal-drop-copy assertion.
- **"The WCAG 1.4.1 gap this task did not close"** — the six colour-only status sites enumerated, the anomaly banner's role in the gap, and why closing it is one coordinated task rather than a rider on this one.
- **"Two reversals, recorded"** — 06.5-CONTEXT D-01's status badge and the `.battery-trend-section` comment's false "carries no verdict" claim, each with where the reversal was written down.
- **"The hover defect found in the pattern being extended"** — the specificity arithmetic, the shorthand overlap, why the comment was wrong, and the rejected alternative of narrowing the hover shorthand across eight components.
- A **"Pixel-Level Items Outstanding"** section reproducing the nine-item live-browser list above for the orchestrating session's pass, with item 6 (hover/focus survival) flagged as the highest-risk item and item 4 (does the 3px edge read right at full card width) flagged as the one most likely to need a follow-up tuning pass.
- An explicit note that `Skill("sketch-findings-skypane")` has now gone seven consecutive Health quick tasks without an update, and that folding those deltas in is a real outstanding piece of work rather than a forgotten one.
</output>
